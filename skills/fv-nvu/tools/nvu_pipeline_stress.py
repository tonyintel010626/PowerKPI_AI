#!/usr/bin/env python3
"""NVU Pipeline Stress Test — stability testing for all self-improvement tools.

Runs N iterations of the self-improvement pipeline stages and reports
per-stage pass/fail statistics. Supports parallel execution.

Stages (in order):
  1. self-check    (structural checks)
  2. self-verify   (content assertions)
  3. validate_bios (BIOS skill validation)
  4. validate_e2e  (end-to-end cross-skill)
  5. self-learn    (knowledge gap detection)      [advisory]
  6. self-study    (external source monitoring)    [advisory]
  7. self-improve  (orchestrator)                  [advisory]

Ported from THC thc_pipeline_stress.py, adapted for NVU domain.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nvu_pipeline_stress")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
EVAL_DIR = TOOLS_DIR.parent / "eval"
DOCS_DIR = TOOLS_DIR.parent / "docs"

# Stages: (name, script_path, is_advisory)
CORE_STAGES = [
    ("self-check", TOOLS_DIR / "nvu_self_check.py", False),
    ("self-verify", TOOLS_DIR / "nvu_self_verify.py", False),
    ("validate_bios", EVAL_DIR / "validate_bios.py", False),
    ("validate_e2e", DOCS_DIR / "validate_e2e.py", False),
]
ADVISORY_STAGES = [
    ("self-learn", TOOLS_DIR / "nvu_self_learn.py", True),
    ("self-study", TOOLS_DIR / "nvu_self_study.py", True),
    ("self-improve", TOOLS_DIR / "nvu_self_improve.py", True),
]
ALL_STAGES = CORE_STAGES + ADVISORY_STAGES

# Stages where rc=0 with changes detected is still PASS
CHANGE_DETECTED_STAGES = {"self-study", "self-learn", "self-improve"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """Result of a single stage execution."""

    stage: str
    iteration: int
    exit_code: int
    duration_ms: float
    passed: bool
    error: Optional[str] = None


@dataclass
class StageStats:
    """Aggregated statistics for a stage across all iterations."""

    stage: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.total if self.total > 0 else 0.0

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0

    def record(self, result: StageResult) -> None:
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
            if result.error:
                self.errors.append(f"iter {result.iteration}: {result.error}")
        self.total_ms += result.duration_ms
        self.min_ms = min(self.min_ms, result.duration_ms)
        self.max_ms = max(self.max_ms, result.duration_ms)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def find_repo_root() -> Path:
    """Walk up to find repo root."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def run_stage(
    stage_name: str,
    script_path: Path,
    iteration: int,
    repo_root: Path,
    timeout: int = 60,
) -> StageResult:
    """Run a single stage and return the result."""
    if not script_path.exists():
        return StageResult(
            stage=stage_name,
            iteration=iteration,
            exit_code=-1,
            duration_ms=0.0,
            passed=False,
            error=f"Script not found: {script_path}",
        )

    start = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        passed = result.returncode == 0
        error = None
        if not passed:
            stderr_snippet = result.stderr[:200].strip() if result.stderr else ""
            error = f"rc={result.returncode}"
            if stderr_snippet:
                error += f" stderr={stderr_snippet}"

        return StageResult(
            stage=stage_name,
            iteration=iteration,
            exit_code=result.returncode,
            duration_ms=elapsed_ms,
            passed=passed,
            error=error,
        )
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageResult(
            stage=stage_name,
            iteration=iteration,
            exit_code=-2,
            duration_ms=elapsed_ms,
            passed=False,
            error=f"Timeout after {timeout}s",
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageResult(
            stage=stage_name,
            iteration=iteration,
            exit_code=-3,
            duration_ms=elapsed_ms,
            passed=False,
            error=str(e),
        )


def run_iteration(
    stages: list[tuple[str, Path, bool]],
    iteration: int,
    repo_root: Path,
    timeout: int = 60,
) -> list[StageResult]:
    """Run all stages for a single iteration."""
    results = []
    for stage_name, script_path, _advisory in stages:
        result = run_stage(stage_name, script_path, iteration, repo_root, timeout)
        results.append(result)
    return results


def run_stress_test(
    stages: list[tuple[str, Path, bool]],
    iterations: int,
    parallel: int,
    repo_root: Path,
    timeout: int = 60,
) -> dict[str, StageStats]:
    """Run stress test across N iterations, optionally in parallel."""
    stats: dict[str, StageStats] = {}
    for name, _, _ in stages:
        stats[name] = StageStats(stage=name)

    overall_start = time.perf_counter()

    if parallel <= 1:
        # Sequential execution
        for i in range(iterations):
            results = run_iteration(stages, i + 1, repo_root, timeout)
            for r in results:
                stats[r.stage].record(r)
            if (i + 1) % 10 == 0:
                logger.info("Completed %d/%d iterations", i + 1, iterations)
    else:
        # Parallel execution
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(run_iteration, stages, i + 1, repo_root, timeout): i + 1
                for i in range(iterations)
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                results = future.result()
                for r in results:
                    stats[r.stage].record(r)
                if completed % 10 == 0:
                    logger.info("Completed %d/%d iterations", completed, iterations)

    overall_ms = (time.perf_counter() - overall_start) * 1000
    logger.info("Total time: %.1fs", overall_ms / 1000)
    return stats


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(stats: dict[str, StageStats], iterations: int) -> None:
    """Print human-readable stress test report."""
    print(f"\n{'=' * 75}")
    print(f"  NVU Pipeline Stress Test — {iterations} iterations")
    print(f"{'=' * 75}\n")

    header = f"  {'Stage':<16} {'Pass':>6} {'Fail':>6} {'Rate':>7} {'Avg(ms)':>9} {'Min(ms)':>9} {'Max(ms)':>9}"
    print(header)
    print(f"  {'-' * 64}")

    all_pass = True
    for name, s in stats.items():
        icon = "✓" if s.failed == 0 else "✗"
        rate = f"{s.pass_rate:.1f}%"
        min_ms = f"{s.min_ms:.0f}" if s.min_ms != float("inf") else "N/A"
        print(
            f"  {icon} {name:<14} {s.passed:>6} {s.failed:>6} {rate:>7} "
            f"{s.avg_ms:>9.0f} {min_ms:>9} {s.max_ms:>9.0f}"
        )
        if s.failed > 0:
            all_pass = False

    total_pass = sum(s.passed for s in stats.values())
    total_fail = sum(s.failed for s in stats.values())
    total_runs = sum(s.total for s in stats.values())
    total_ms = sum(s.total_ms for s in stats.values())

    print(f"  {'-' * 64}")
    icon = "✓" if all_pass else "✗"
    rate = f"{total_pass / total_runs * 100:.1f}%" if total_runs > 0 else "N/A"
    print(
        f"  {icon} {'TOTAL':<14} {total_pass:>6} {total_fail:>6} {rate:>7} "
        f"{total_ms / max(total_runs, 1):>9.0f} {'':>9} {'':>9}"
    )

    # Show errors if any
    for name, s in stats.items():
        if s.errors:
            print(f"\n  Errors in {name} ({len(s.errors)}):")
            for e in s.errors[:5]:
                print(f"    • {e}")
            if len(s.errors) > 5:
                print(f"    ... and {len(s.errors) - 5} more")

    status = "PASS" if all_pass else "FAIL"
    print(f"\n  Result: {status}")
    print(f"{'=' * 75}\n")


def to_json_report(stats: dict[str, StageStats], iterations: int) -> str:
    """Generate JSON report."""
    stages = {}
    for name, s in stats.items():
        stages[name] = {
            "total": s.total,
            "passed": s.passed,
            "failed": s.failed,
            "pass_rate": round(s.pass_rate, 2),
            "avg_ms": round(s.avg_ms, 1),
            "min_ms": round(s.min_ms, 1) if s.min_ms != float("inf") else None,
            "max_ms": round(s.max_ms, 1),
            "errors": s.errors[:10],
        }
    total_pass = sum(s.passed for s in stats.values())
    total_fail = sum(s.failed for s in stats.values())
    return json.dumps(
        {
            "tool": "nvu_pipeline_stress",
            "iterations": iterations,
            "stages": stages,
            "summary": {
                "total_pass": total_pass,
                "total_fail": total_fail,
                "total_runs": total_pass + total_fail,
                "all_pass": total_fail == 0,
            },
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVU Pipeline Stress Test — stability testing for self-improvement tools",
    )
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations (default: 10)",
    )
    parser.add_argument(
        "-p",
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1, sequential)",
    )
    parser.add_argument(
        "--stages",
        choices=["core", "advisory", "all"],
        default="core",
        help="Which stages to run (default: core)",
    )
    parser.add_argument(
        "--stage",
        action="append",
        dest="specific_stages",
        help="Run specific stage(s) only (can be repeated)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--save", metavar="PATH", help="Save report to file")
    parser.add_argument(
        "--timeout", type=int, default=60, help="Per-stage timeout in seconds"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    log_level = "WARNING" if args.json else ("DEBUG" if args.verbose else "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(levelname)s: %(message)s",
    )

    repo_root = find_repo_root()

    # Select stages
    if args.specific_stages:
        stage_map = {name: (name, path, adv) for name, path, adv in ALL_STAGES}
        stages = []
        for s in args.specific_stages:
            if s in stage_map:
                stages.append(stage_map[s])
            else:
                logger.error(
                    "Unknown stage: %s (available: %s)", s, list(stage_map.keys())
                )
                return 1
    elif args.stages == "core":
        stages = CORE_STAGES
    elif args.stages == "advisory":
        stages = ADVISORY_STAGES
    elif args.stages == "all":
        stages = ALL_STAGES
    else:
        stages = CORE_STAGES

    logger.info(
        "Running %d iterations of %d stages (%d parallel workers)",
        args.iterations,
        len(stages),
        args.parallel,
    )

    stats = run_stress_test(
        stages=stages,
        iterations=args.iterations,
        parallel=args.parallel,
        repo_root=repo_root,
        timeout=args.timeout,
    )

    if args.json:
        report_json = to_json_report(stats, args.iterations)
        print(report_json)
    else:
        print_report(stats, args.iterations)

    if args.save:
        report_json = to_json_report(stats, args.iterations)
        Path(args.save).write_text(report_json, encoding="utf-8")
        logger.info("Report saved to %s", args.save)

    all_pass = all(s.failed == 0 for s in stats.values())
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
