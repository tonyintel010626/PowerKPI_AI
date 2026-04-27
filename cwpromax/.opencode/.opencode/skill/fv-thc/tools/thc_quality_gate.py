#!/usr/bin/env python3
"""THC Skill Quality Gate - CI/CD and pre-commit integration.

Runs thc_self_check.py and thc_self_verify.py, reports combined results.
Exit code 0 = all pass, 1 = failures detected, 2 = error.

Usage:
    python thc_quality_gate.py              # Run both checks
    python thc_quality_gate.py --check      # Run self-check only
    python thc_quality_gate.py --verify     # Run self-verify only
    python thc_quality_gate.py --json       # JSON output
    python thc_quality_gate.py --quick      # Self-check only (fast, ~2s)
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent


def run_stage(script_name: str, label: str) -> dict:
    """Run a pipeline stage script and capture results."""
    script = TOOLS_DIR / script_name
    if not script.exists():
        return {
            "stage": label,
            "status": "ERROR",
            "message": f"{script_name} not found",
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(TOOLS_DIR),
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "stage": label,
                "status": "ERROR",
                "message": f"Invalid JSON output from {script_name}",
                "stderr": result.stderr[:500] if result.stderr else "",
            }

        summary = data.get("summary", {})
        # Keys vary: self-check/verify use uppercase "PASS", "FAIL", "total"
        passed = summary.get("PASS", summary.get("passed", summary.get("pass", 0)))
        total = summary.get("total", 0)
        failed = summary.get("FAIL", summary.get("failed", summary.get("fail", 0)))
        # Only count explicit FAIL/ERROR as gate-blocking failures.
        # WARN and CHANGE are informational and should not block the gate.
        errors = summary.get("ERROR", summary.get("error", 0))
        failed = failed + errors

        status = "PASS" if failed == 0 and result.returncode == 0 else "FAIL"
        return {
            "stage": label,
            "status": status,
            "passed": passed,
            "failed": failed,
            "total": total,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stage": label, "status": "ERROR", "message": "Timeout (120s)"}
    except Exception as e:
        return {"stage": label, "status": "ERROR", "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="THC Skill Quality Gate")
    parser.add_argument("--check", action="store_true", help="Run self-check only")
    parser.add_argument("--verify", action="store_true", help="Run self-verify only")
    parser.add_argument("--quick", action="store_true", help="Self-check only (fast)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Determine which stages to run
    run_check = True
    run_verify = True
    if args.check or args.quick:
        run_verify = False
    if args.verify:
        run_check = False

    start = time.time()
    results = []

    if run_check:
        results.append(run_stage("thc_self_check.py", "self-check"))
    if run_verify:
        results.append(run_stage("thc_self_verify.py", "self-verify"))

    elapsed = round(time.time() - start, 1)

    all_pass = all(r["status"] == "PASS" for r in results)
    any_error = any(r["status"] == "ERROR" for r in results)

    gate_result = {
        "gate": "PASS" if all_pass else "FAIL",
        "elapsed_seconds": elapsed,
        "stages": results,
    }

    if args.json:
        print(json.dumps(gate_result, indent=2))
    else:
        print(f"\n{'=' * 50}")
        print(f"  THC Skill Quality Gate: {'PASS [OK]' if all_pass else 'FAIL [X]'}")
        print(f"{'=' * 50}")
        for r in results:
            icon = (
                "[OK]"
                if r["status"] == "PASS"
                else "[X]"
                if r["status"] == "FAIL"
                else "[!]"
            )
            detail = (
                f"{r.get('passed', '?')}/{r.get('total', '?')} passed"
                if "total" in r
                else r.get("message", "")
            )
            print(f"  {icon} {r['stage']}: {r['status']} ({detail})")
        print(f"  Time: {elapsed}s")
        print(f"{'=' * 50}\n")

    if any_error:
        sys.exit(2)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
