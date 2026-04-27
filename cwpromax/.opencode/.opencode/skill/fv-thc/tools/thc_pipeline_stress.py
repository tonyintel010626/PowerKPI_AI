#!/usr/bin/env python3
"""
THC Self-Improvement Pipeline Stress Test
Runs the full 5-stage pipeline for N iterations and reports results.

Usage:
    python thc_pipeline_stress.py --iterations 100
    python thc_pipeline_stress.py --iterations 100 --wiki-live --wiki-iters 5
    python thc_pipeline_stress.py --iterations 100 --parallel 10
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TOOLS_DIR = Path(__file__).parent.resolve()
REPORTS_DIR = TOOLS_DIR.parent / "reports"


# Stages where exit_code=1 means "changes detected", not failure
CHANGE_DETECTED_STAGES = {"study"}


@dataclass
class StageResult:
    """Result of a single stage execution."""

    stage: str
    iteration: int
    passed: int = 0
    failed: int = 0
    warned: int = 0
    skipped: int = 0
    changed: int = 0
    duration_ms: float = 0
    exit_code: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        # study returns exit=1 when changes detected (not a failure)
        if self.stage in CHANGE_DETECTED_STAGES:
            return self.exit_code in (0, 1) and self.failed == 0
        return self.exit_code == 0 and self.failed == 0


@dataclass
class IterationResult:
    """Result of one full pipeline iteration."""

    iteration: int
    stages: Dict[str, StageResult] = field(default_factory=dict)
    total_duration_ms: float = 0

    @property
    def all_ok(self) -> bool:
        return all(s.ok for s in self.stages.values())


def run_stage(
    stage_name: str, script: str, args: List[str], iteration: int
) -> StageResult:
    """Run a single pipeline stage and parse results."""
    result = StageResult(stage=stage_name, iteration=iteration)
    cmd = [sys.executable, str(TOOLS_DIR / script), "--json"] + args

    t0 = time.perf_counter()
    try:
        # Wiki stages need longer timeout (74 pages = network-bound)
        timeout = 1200 if "wiki" in stage_name else 600
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TOOLS_DIR),
        )
        result.exit_code = proc.returncode
        result.duration_ms = (time.perf_counter() - t0) * 1000

        # Parse JSON output
        stdout = proc.stdout.strip()
        if stdout:
            # Strip any non-JSON prefix (logging lines)
            for i, ch in enumerate(stdout):
                if ch == "{":
                    stdout = stdout[i:]
                    break
            try:
                data = json.loads(stdout)
                summary = data.get("summary", data)
                result.passed = summary.get("pass", summary.get("passed", 0))
                result.failed = summary.get("fail", summary.get("failed", 0))
                result.warned = summary.get("warn", summary.get("warned", 0))
                result.skipped = summary.get("skip", summary.get("skipped", 0))
                result.changed = summary.get("change", summary.get("changed", 0))
            except (json.JSONDecodeError, ValueError):
                # Non-JSON output — check exit code
                if result.exit_code != 0:
                    result.error = stdout[:200]
        if proc.stderr and result.exit_code != 0:
            result.error = proc.stderr[:200]

    except subprocess.TimeoutExpired:
        result.duration_ms = (time.perf_counter() - t0) * 1000
        result.exit_code = -1
        timeout_s = 1200 if "wiki" in stage_name else 600
        result.error = f"TIMEOUT ({timeout_s}s)"
    except Exception as e:
        result.duration_ms = (time.perf_counter() - t0) * 1000
        result.exit_code = -2
        result.error = str(e)[:200]

    return result


def run_iteration(
    iteration: int, wiki_live: bool = False, wiki_user: str = ""
) -> IterationResult:
    """Run one full pipeline iteration (all 5 stages)."""
    ir = IterationResult(iteration=iteration)
    t0 = time.perf_counter()

    # Stage 1: Check
    ir.stages["check"] = run_stage("check", "thc_self_check.py", [], iteration)

    # Stage 2: Study
    ir.stages["study"] = run_stage("study", "thc_self_study.py", [], iteration)

    # Stage 3: Learn
    ir.stages["learn"] = run_stage("learn", "thc_self_learn.py", [], iteration)

    # Stage 4: Verify
    ir.stages["verify"] = run_stage("verify", "thc_self_verify.py", [], iteration)

    # Stage 5a: Wiki (Simics) — only if live
    if wiki_live:
        ir.stages["wiki_simics"] = run_stage(
            "wiki_simics", "thc_wiki_verify.py", ["--live"], iteration
        )

    # Stage 5b: Wiki (FV) — only if live
    if wiki_live and wiki_user:
        ir.stages["wiki_fv"] = run_stage(
            "wiki_fv",
            "thc_self_wiki.py",
            ["--live", "--json", "--user", wiki_user],
            iteration,
        )

    ir.total_duration_ms = (time.perf_counter() - t0) * 1000
    return ir


def run_stress_test(
    iterations: int,
    parallel: int = 1,
    wiki_live: bool = False,
    wiki_user: str = "",
    wiki_iters: int = 0,
) -> List[IterationResult]:
    """Run the stress test with N iterations."""
    results: List[IterationResult] = []
    wiki_iterations = set(range(wiki_iters)) if wiki_iters > 0 else set()

    # Phase 1: Run all iterations WITHOUT wiki (parallelizable)
    print(f"  Phase 1: {iterations} offline iterations ({parallel} workers)...")
    if parallel <= 1:
        for i in range(iterations):
            print(f"\r  Iteration {i + 1}/{iterations}...", end="", flush=True)
            ir = run_iteration(i, wiki_live=False, wiki_user="")
            results.append(ir)
            status = "PASS" if ir.all_ok else "FAIL"
            stages_summary = " | ".join(
                f"{k}:{v.passed}P/{v.failed}F" for k, v in ir.stages.items()
            )
            print(
                f"\r  [{i + 1:3d}/{iterations}] {status} ({ir.total_duration_ms:.0f}ms) — {stages_summary}"
            )
    else:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {}
            for i in range(iterations):
                f = executor.submit(run_iteration, i, False, "")
                futures[f] = i

            completed = 0
            for future in as_completed(futures):
                completed += 1
                i = futures[future]
                try:
                    ir = future.result()
                    results.append(ir)
                    status = "PASS" if ir.all_ok else "FAIL"
                    print(
                        f"\r  [{completed:3d}/{iterations}] iter={i} {status} ({ir.total_duration_ms:.0f}ms)"
                    )
                except Exception as e:
                    print(f"\r  [{completed:3d}/{iterations}] iter={i} ERROR: {e}")

    # Sort by iteration number
    results.sort(key=lambda r: r.iteration)

    # Phase 2: Run wiki iterations SEQUENTIALLY (network-bound, avoid throttling)
    if wiki_live and wiki_iterations:
        print(f"\n  Phase 2: {len(wiki_iterations)} wiki iterations (sequential)...")
        for idx, i in enumerate(sorted(wiki_iterations)):
            print(
                f"\r  Wiki iteration {idx + 1}/{len(wiki_iterations)}...",
                end="",
                flush=True,
            )
            wiki_ir = run_iteration(1000 + i, wiki_live=True, wiki_user=wiki_user)
            # Merge wiki stages into the corresponding offline result
            if i < len(results):
                for stage_name, sr in wiki_ir.stages.items():
                    if "wiki" in stage_name:
                        results[i].stages[stage_name] = sr
            else:
                results.append(wiki_ir)
            wiki_status = all(
                sr.ok for name, sr in wiki_ir.stages.items() if "wiki" in name
            )
            print(
                f"\r  [wiki {idx + 1:3d}/{len(wiki_iterations)}] {'PASS' if wiki_status else 'FAIL'} ({wiki_ir.total_duration_ms:.0f}ms)"
            )

    return results


def print_report(results: List[IterationResult], total_time: float):
    """Print comprehensive results report."""
    n = len(results)
    print(f"\n{'=' * 80}")
    print(f"  THC PIPELINE STRESS TEST — {n} ITERATIONS")
    print(f"{'=' * 80}")

    # Overall pass rate
    all_pass = sum(1 for r in results if r.all_ok)
    print(
        f"\n  Overall: {all_pass}/{n} iterations fully passed ({100 * all_pass / n:.1f}%)"
    )
    print(f"  Total time: {total_time:.1f}s ({total_time / n:.2f}s/iteration avg)")

    # Per-stage statistics
    stage_names = set()
    for r in results:
        stage_names.update(r.stages.keys())

    print(
        f"\n  {'Stage':<15} {'Pass Rate':>10} {'Avg Pass':>10} {'Avg Fail':>10} {'Avg ms':>10} {'Min ms':>10} {'Max ms':>10}"
    )
    print(
        f"  {'-' * 15} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}"
    )

    for stage in sorted(stage_names):
        stage_results = [r.stages[stage] for r in results if stage in r.stages]
        if not stage_results:
            continue
        sn = len(stage_results)
        ok_count = sum(1 for s in stage_results if s.ok)
        avg_pass = sum(s.passed for s in stage_results) / sn
        avg_fail = sum(s.failed for s in stage_results) / sn
        avg_ms = sum(s.duration_ms for s in stage_results) / sn
        min_ms = min(s.duration_ms for s in stage_results)
        max_ms = max(s.duration_ms for s in stage_results)
        print(
            f"  {stage:<15} {ok_count:>4}/{sn:<4}  {avg_pass:>10.1f} {avg_fail:>10.1f} {avg_ms:>10.0f} {min_ms:>10.0f} {max_ms:>10.0f}"
        )

    # Failures detail
    failures = [
        (r.iteration, stage, sr)
        for r in results
        for stage, sr in r.stages.items()
        if not sr.ok
    ]

    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for iteration, stage, sr in failures[:20]:  # Show first 20
            print(
                f"    iter={iteration} stage={stage}: exit={sr.exit_code} fail={sr.failed} err={sr.error[:80]}"
            )
        if len(failures) > 20:
            print(f"    ... and {len(failures) - 20} more")
    else:
        print(f"\n  NO FAILURES — 100% clean across all {n} iterations!")

    # Timing distribution
    durations = [r.total_duration_ms for r in results]
    avg_dur = sum(durations) / n
    min_dur = min(durations)
    max_dur = max(durations)
    print(f"\n  Timing: avg={avg_dur:.0f}ms  min={min_dur:.0f}ms  max={max_dur:.0f}ms")
    print(f"{'=' * 80}")

    return all_pass == n


def save_report(results: List[IterationResult], total_time: float, filepath: Path):
    """Save JSON report to file."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "iterations": len(results),
        "total_time_s": round(total_time, 2),
        "all_pass": all(r.all_ok for r in results),
        "pass_rate": sum(1 for r in results if r.all_ok) / len(results),
        "results": [
            {
                "iteration": r.iteration,
                "all_ok": r.all_ok,
                "duration_ms": round(r.total_duration_ms, 1),
                "stages": {
                    name: {
                        "ok": sr.ok,
                        "passed": sr.passed,
                        "failed": sr.failed,
                        "warned": sr.warned,
                        "skipped": sr.skipped,
                        "changed": sr.changed,
                        "duration_ms": round(sr.duration_ms, 1),
                        "exit_code": sr.exit_code,
                        "error": sr.error,
                    }
                    for name, sr in r.stages.items()
                },
            }
            for r in results
        ],
    }
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="THC Pipeline Stress Test")
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=100,
        help="Number of iterations (default: 100)",
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=1,
        help="Parallel workers (default: 1 = sequential)",
    )
    parser.add_argument(
        "--wiki-live", action="store_true", help="Enable live wiki checks"
    )
    parser.add_argument(
        "--wiki-user", type=str, default="", help="Wiki user for FV wiki checks"
    )
    parser.add_argument(
        "--wiki-iters",
        type=int,
        default=0,
        help="Number of iterations to run wiki checks (0=none, -1=all)",
    )
    parser.add_argument(
        "--save", action="store_true", help="Save JSON report to reports/"
    )
    args = parser.parse_args()

    if args.wiki_iters == -1:
        args.wiki_iters = args.iterations

    print(f"\n  THC Pipeline Stress Test")
    print(f"  Iterations: {args.iterations}, Parallel: {args.parallel}")
    print(
        f"  Wiki: {'LIVE' if args.wiki_live else 'OFFLINE'} ({args.wiki_iters} wiki iterations)"
    )
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    t0 = time.perf_counter()
    results = run_stress_test(
        iterations=args.iterations,
        parallel=args.parallel,
        wiki_live=args.wiki_live,
        wiki_user=args.wiki_user,
        wiki_iters=args.wiki_iters,
    )
    total_time = time.perf_counter() - t0

    all_clean = print_report(results, total_time)

    if args.save:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_report(results, total_time, REPORTS_DIR / f"stress_test_{ts}.json")

    sys.exit(0 if all_clean else 1)


if __name__ == "__main__":
    main()
