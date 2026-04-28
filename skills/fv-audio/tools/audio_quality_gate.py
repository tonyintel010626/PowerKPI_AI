#!/usr/bin/env python3
"""
audio_quality_gate.py — FV-AUDIO Quality Gate for CI/CD

Runs self-check and self-verify as subprocesses and reports combined
PASS/FAIL status suitable for CI pipeline integration.

Exit codes:
    0 = PASS (all checks passed)
    1 = FAIL (one or more checks failed)
    2 = ERROR (execution error)

Adapted from FV-THC thc_quality_gate.py for the audio validation domain.

Usage:
    python audio_quality_gate.py [--check] [--verify] [--quick] [--json]
"""
from __future__ import annotations

__author__ = "huiyingt (Tan Hui Ying)"

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent


def run_stage(script_name: str, extra_args: Optional[List[str]] = None, timeout: int = 120) -> Dict[str, Any]:
    """
    Run a self-improvement stage script as a subprocess.

    Returns dict with: name, status, elapsed, summary, raw_output.
    """
    script = _HERE / script_name
    if not script.exists():
        return {
            "name": script_name,
            "status": "ERROR",
            "elapsed": 0.0,
            "summary": {"error": f"Script not found: {script}"},
            "raw_output": "",
        }

    cmd = [sys.executable, str(script), "--json"]
    if extra_args:
        cmd.extend(extra_args)

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_HERE),
        )
        elapsed = time.time() - t0
        raw = proc.stdout.strip()

        # Try to parse JSON output
        try:
            data = json.loads(raw)
            summary = data.get("summary", data)
            fail_count = summary.get("fail", 0)
            error_count = summary.get("error", 0)
            if fail_count > 0:
                status = "FAIL"
            elif error_count > 0:
                status = "ERROR"
            else:
                status = "PASS"
        except (json.JSONDecodeError, KeyError):
            summary = {"raw": raw[:500]}
            status = "FAIL" if proc.returncode != 0 else "PASS"

        return {
            "name": script_name,
            "status": status,
            "elapsed": round(elapsed, 2),
            "summary": summary,
            "raw_output": raw[:2000],
        }

    except subprocess.TimeoutExpired:
        return {
            "name": script_name,
            "status": "ERROR",
            "elapsed": timeout,
            "summary": {"error": f"Timed out after {timeout}s"},
            "raw_output": "",
        }
    except Exception as exc:
        return {
            "name": script_name,
            "status": "ERROR",
            "elapsed": time.time() - t0,
            "summary": {"error": str(exc)},
            "raw_output": "",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="FV-AUDIO Quality Gate")
    parser.add_argument("--check", action="store_true", help="Run only self-check")
    parser.add_argument("--verify", action="store_true", help="Run only self-verify")
    parser.add_argument("--quick", action="store_true", help="Quick mode (check only)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    # Determine which stages to run
    stages: List[str] = []
    if args.quick or args.check:
        stages.append("audio_self_check.py")
    if args.verify and not args.quick:
        stages.append("audio_self_verify.py")
    if not stages:
        # Default: run both
        stages = ["audio_self_check.py", "audio_self_verify.py"]

    t0 = time.time()
    results: List[Dict[str, Any]] = []
    gate_status = "PASS"

    for stage_script in stages:
        result = run_stage(stage_script)
        results.append(result)
        if result["status"] == "FAIL":
            gate_status = "FAIL"
        elif result["status"] == "ERROR" and gate_status != "FAIL":
            gate_status = "ERROR"

    total_elapsed = round(time.time() - t0, 2)

    output = {
        "gate": gate_status,
        "elapsed": total_elapsed,
        "stages": results,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"  FV-AUDIO Quality Gate: {gate_status}")
        print(f"{'='*50}")
        for r in results:
            print(f"  {r['name']:30s}  {r['status']:6s}  ({r['elapsed']:.1f}s)")
        print(f"{'='*50}")
        print(f"  Total elapsed: {total_elapsed:.1f}s")
        print()

    if gate_status == "ERROR":
        return 2
    elif gate_status == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
