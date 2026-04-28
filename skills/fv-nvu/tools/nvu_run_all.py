#!/usr/bin/env python3
"""NVU Self-Improvement Unified Runner.

Single-command execution of the full NVU self-improvement pipeline.
Runs all validators and advisory tools in the correct order, producing
a unified summary report.

Pipeline stages (in order):
  1. self-check    — structural integrity (10 checks)
  2. self-verify   — content assertions (81 checks)
  3. validate_bios — BIOS sub-skill validation (423 checks)
  4. validate_e2e  — end-to-end cross-skill validation (50 checks)
  5. self-learn    — knowledge gap detection (advisory)
  6. self-study    — external source monitoring (advisory)
  7. self-improve  — orchestrated improvement proposals (advisory)

Stages 1-4 are CORE validators (blocking — any failure = pipeline FAIL).
Stages 5-7 are ADVISORY (non-blocking — informational only).

Usage:
  python nvu_run_all.py              # Run core validators only
  python nvu_run_all.py --full       # Run core + advisory stages
  python nvu_run_all.py --quick      # Run self-check + self-verify only
  python nvu_run_all.py --json       # Output JSON report
  python nvu_run_all.py --iterations N  # Run N iterations (stability test)
  python nvu_run_all.py --stop-on-fail  # Stop at first failure

Owner: Chin, William Willy (willychi)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TOOLS_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]  # .opencode/skill/fv-nvu -> repo root
EVAL_DIR = SKILL_ROOT / "eval"
DOCS_DIR = SKILL_ROOT / "docs"


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""

    name: str
    script: Path
    args: list = field(default_factory=list)
    blocking: bool = True
    description: str = ""
    timeout: int = 120


CORE_STAGES = [
    StageConfig(
        name="self-check",
        script=TOOLS_DIR / "nvu_self_check.py",
        args=["--json"],
        blocking=True,
        description="Structural integrity (10 checks)",
        timeout=60,
    ),
    StageConfig(
        name="self-verify",
        script=TOOLS_DIR / "nvu_self_verify.py",
        args=["--json"],
        blocking=True,
        description="Content assertions (81 checks)",
        timeout=60,
    ),
    StageConfig(
        name="validate_bios",
        script=EVAL_DIR / "validate_bios.py",
        args=[],
        blocking=True,
        description="BIOS sub-skill validation (423 checks)",
        timeout=120,
    ),
    StageConfig(
        name="validate_e2e",
        script=DOCS_DIR / "validate_e2e.py",
        args=[],
        blocking=True,
        description="End-to-end cross-skill validation (50 checks)",
        timeout=60,
    ),
]

ADVISORY_STAGES = [
    StageConfig(
        name="self-learn",
        script=TOOLS_DIR / "nvu_self_learn.py",
        args=["--json"],
        blocking=False,
        description="Knowledge gap detection",
        timeout=60,
    ),
    StageConfig(
        name="self-study",
        script=TOOLS_DIR / "nvu_self_study.py",
        args=["--json"],
        blocking=False,
        description="External source monitoring",
        timeout=60,
    ),
    StageConfig(
        name="self-improve",
        script=TOOLS_DIR / "nvu_self_improve.py",
        args=["--json"],
        blocking=False,
        description="Improvement proposal generation",
        timeout=120,
    ),
]

QUICK_STAGES = CORE_STAGES[:2]  # self-check + self-verify only


# ---------------------------------------------------------------------------
# Stage Runner
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """Result from running a single pipeline stage."""

    name: str
    passed: bool
    returncode: int
    duration_ms: int
    pass_count: int = 0
    fail_count: int = 0
    warn_count: int = 0
    total_count: int = 0
    error: str = ""
    blocking: bool = True
    description: str = ""


def parse_json_output(output: str) -> dict:
    """Extract JSON object from mixed stdout output."""
    # Try to find JSON in the output (tools may print non-JSON before/after)
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    # Try the whole output as JSON
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}


def parse_text_counts(output: str, stage_name: str) -> tuple:
    """Parse pass/fail/warn counts from text output."""
    import re

    pass_count = 0
    fail_count = 0
    warn_count = 0

    if stage_name == "validate_bios":
        # Format: "RESULT: 100.0% pass rate (423/423)"
        m = re.search(r"\((\d+)/(\d+)\)", output)
        if m:
            pass_count = int(m.group(1))
            total = int(m.group(2))
            fail_count = total - pass_count
        # Check for actual failures (not "0 FAIL" summary)
        fail_lines = re.findall(r"[1-9]\d*\s+FAIL", output)
        if fail_lines:
            fail_count = max(fail_count, len(fail_lines))

    elif stage_name == "validate_e2e":
        # Format: "50/50 CONFIRMED"
        m = re.search(r"(\d+)/(\d+)\s*CONFIRMED", output)
        if m:
            pass_count = int(m.group(1))
            total = int(m.group(2))
            fail_count = total - pass_count
        # Check for MISMATCH
        if re.search(r"MISMATCH", output):
            fail_count = max(fail_count, 1)

    return pass_count, fail_count, warn_count


def run_stage(stage: StageConfig) -> StageResult:
    """Run a single pipeline stage and return results."""
    if not stage.script.exists():
        return StageResult(
            name=stage.name,
            passed=False,
            returncode=-1,
            duration_ms=0,
            error=f"Script not found: {stage.script}",
            blocking=stage.blocking,
            description=stage.description,
        )

    cmd = [sys.executable, str(stage.script)] + stage.args
    t0 = time.monotonic()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=stage.timeout,
            cwd=str(REPO_ROOT),
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return StageResult(
            name=stage.name,
            passed=False,
            returncode=-2,
            duration_ms=duration_ms,
            error=f"Timeout after {stage.timeout}s",
            blocking=stage.blocking,
            description=stage.description,
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return StageResult(
            name=stage.name,
            passed=False,
            returncode=-3,
            duration_ms=duration_ms,
            error=str(e),
            blocking=stage.blocking,
            description=stage.description,
        )

    output = result.stdout + result.stderr
    pass_count = 0
    fail_count = 0
    warn_count = 0
    error_msg = ""

    # Parse output based on whether stage uses --json
    if "--json" in stage.args:
        data = parse_json_output(result.stdout)
        summary = data.get("summary", {})
        # Normalize keys to lowercase
        norm = {k.lower(): v for k, v in summary.items()}
        pass_count = norm.get("pass", 0)
        fail_count = norm.get("fail", 0)
        warn_count = norm.get("warn", 0)
        if not summary:
            error_msg = "No JSON summary in output"
    else:
        pass_count, fail_count, warn_count = parse_text_counts(output, stage.name)
        if pass_count == 0 and fail_count == 0:
            error_msg = f"Could not parse counts from output (rc={result.returncode})"

    total_count = pass_count + fail_count + warn_count

    # Determine pass/fail
    if stage.blocking:
        stage_passed = result.returncode == 0 and fail_count == 0 and pass_count > 0
    else:
        # Advisory stages pass if they don't crash
        stage_passed = result.returncode == 0

    return StageResult(
        name=stage.name,
        passed=stage_passed,
        returncode=result.returncode,
        duration_ms=duration_ms,
        pass_count=pass_count,
        fail_count=fail_count,
        warn_count=warn_count,
        total_count=total_count,
        error=error_msg,
        blocking=stage.blocking,
        description=stage.description,
    )


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """Aggregated result from running the full pipeline."""

    passed: bool
    stages: list
    total_pass: int = 0
    total_fail: int = 0
    total_warn: int = 0
    total_checks: int = 0
    total_duration_ms: int = 0
    iteration: int = 1
    timestamp: str = ""


def run_pipeline(
    stages: list,
    stop_on_fail: bool = False,
    iteration: int = 1,
    quiet: bool = False,
) -> PipelineResult:
    """Run the full pipeline and return aggregated results."""
    results = []
    pipeline_passed = True
    total_duration = 0

    for stage in stages:
        if not quiet:
            status = "ADVISORY" if not stage.blocking else "CORE"
            print(
                f"  [{status}] {stage.name}: {stage.description} ...",
                end=" ",
                flush=True,
            )

        sr = run_stage(stage)
        results.append(sr)
        total_duration += sr.duration_ms

        if not quiet:
            icon = "✓" if sr.passed else ("⚠" if not sr.blocking else "✗")
            counts = f"{sr.pass_count}P"
            if sr.fail_count > 0:
                counts += f"/{sr.fail_count}F"
            if sr.warn_count > 0:
                counts += f"/{sr.warn_count}W"
            print(f"{icon} {counts} ({sr.duration_ms}ms)")

        if not sr.passed and sr.blocking:
            pipeline_passed = False
            if stop_on_fail:
                if not quiet:
                    print(f"  ⛔ Stopping: {stage.name} failed")
                break

    total_pass = sum(s.pass_count for s in results)
    total_fail = sum(s.fail_count for s in results if s.blocking)
    total_warn = sum(s.warn_count for s in results)
    total_checks = sum(s.total_count for s in results if s.blocking)

    return PipelineResult(
        passed=pipeline_passed,
        stages=results,
        total_pass=total_pass,
        total_fail=total_fail,
        total_warn=total_warn,
        total_checks=total_checks,
        total_duration_ms=total_duration,
        iteration=iteration,
        timestamp=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def format_report(result: PipelineResult) -> dict:
    """Format pipeline result as JSON-serializable dict."""
    return {
        "pipeline": "nvu-self-improvement",
        "version": "1.0",
        "timestamp": result.timestamp,
        "iteration": result.iteration,
        "passed": result.passed,
        "summary": {
            "pass": result.total_pass,
            "fail": result.total_fail,
            "warn": result.total_warn,
            "total_checks": result.total_checks,
            "duration_ms": result.total_duration_ms,
        },
        "stages": [
            {
                "name": s.name,
                "passed": s.passed,
                "blocking": s.blocking,
                "pass": s.pass_count,
                "fail": s.fail_count,
                "warn": s.warn_count,
                "duration_ms": s.duration_ms,
                "error": s.error if s.error else None,
            }
            for s in result.stages
        ],
    }


def print_summary(result: PipelineResult, iteration: int = 0, total_iters: int = 1):
    """Print human-readable summary."""
    gate = "PASS ✓" if result.passed else "FAIL ✗"
    print(f"\n{'=' * 60}")
    if total_iters > 1:
        print(f"  NVU Pipeline [{iteration}/{total_iters}]: {gate}")
    else:
        print(f"  NVU Pipeline: {gate}")
    print(
        f"  Checks: {result.total_pass} pass, {result.total_fail} fail, "
        f"{result.total_warn} warn ({result.total_checks} total)"
    )
    print(f"  Duration: {result.total_duration_ms}ms")
    print(f"{'=' * 60}")


def print_stability_summary(all_results: list):
    """Print summary for multi-iteration stability test."""
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    failed = total - passed
    durations = [r.total_duration_ms for r in all_results]
    avg_ms = sum(durations) // total if total > 0 else 0
    min_ms = min(durations) if durations else 0
    max_ms = max(durations) if durations else 0

    print(f"\n{'=' * 60}")
    print(f"  STABILITY TEST: {total} iterations")
    print(f"  Result: {passed}/{total} PASS ({100 * passed // total}%)")
    if failed > 0:
        print(f"  ⚠ {failed} iterations FAILED")
        for i, r in enumerate(all_results, 1):
            if not r.passed:
                fails = [s.name for s in r.stages if not s.passed and s.blocking]
                print(f"    Iteration {i}: {', '.join(fails)}")
    print(f"  Duration: avg={avg_ms}ms, min={min_ms}ms, max={max_ms}ms")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="NVU Self-Improvement Unified Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline modes:
  (default)     Run 4 core validators (self-check, self-verify, validate_bios, validate_e2e)
  --quick       Run 2 quick validators (self-check, self-verify)
  --full        Run all 7 stages including advisory (self-learn, self-study, self-improve)

Stability testing:
  --iterations N   Run N iterations (default: 1)
  --stop-on-fail   Stop at first failed iteration

Output:
  --json        Output JSON report (one per iteration)
  --quiet       Suppress progress output
        """,
    )
    parser.add_argument(
        "--full", action="store_true", help="Run all stages including advisory"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick validators only"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument(
        "--iterations", type=int, default=1, help="Number of iterations"
    )
    parser.add_argument(
        "--stop-on-fail", action="store_true", help="Stop on first failure"
    )
    args = parser.parse_args()

    # Select stages
    if args.quick:
        stages = QUICK_STAGES
        mode = "quick"
    elif args.full:
        stages = CORE_STAGES + ADVISORY_STAGES
        mode = "full"
    else:
        stages = CORE_STAGES
        mode = "core"

    if not args.quiet:
        print(
            f"NVU Self-Improvement Pipeline ({mode} mode, {args.iterations} iteration(s))"
        )
        print(f"  Repo: {REPO_ROOT}")
        print(f"  Skill: {SKILL_ROOT}")
        print(f"  Stages: {len(stages)}")
        print()

    # Run iterations
    all_results = []
    all_passed = True

    for i in range(1, args.iterations + 1):
        if not args.quiet and args.iterations > 1:
            print(f"--- Iteration {i}/{args.iterations} ---")

        result = run_pipeline(
            stages,
            stop_on_fail=args.stop_on_fail,
            iteration=i,
            quiet=args.quiet,
        )
        all_results.append(result)

        if args.json:
            print(json.dumps(format_report(result), indent=2))
        elif not args.quiet:
            print_summary(result, i, args.iterations)

        if not result.passed:
            all_passed = False
            if args.stop_on_fail:
                if not args.quiet:
                    print(f"⛔ Stopping after iteration {i}")
                break

    # Multi-iteration summary
    if args.iterations > 1 and not args.quiet:
        print_stability_summary(all_results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
