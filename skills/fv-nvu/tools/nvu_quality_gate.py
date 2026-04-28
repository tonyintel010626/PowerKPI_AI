#!/usr/bin/env python3
"""NVU Quality Gate — CI/CD gate for NVU skill tree quality.

Runs all validation stages (self-check, self-verify, bios, e2e),
reports pass/fail, and exits with appropriate code for CI integration.

Usage:
    python nvu_quality_gate.py                  # Run all 4 core validators
    python nvu_quality_gate.py --check          # Run self-check only
    python nvu_quality_gate.py --verify         # Run self-verify only
    python nvu_quality_gate.py --quick          # Run self-check only (alias)
    python nvu_quality_gate.py --full           # Run all 4 + learn/study/improve
    python nvu_quality_gate.py --json           # Output as JSON

Exit codes:
    0 = PASS (all stages passed)
    1 = FAIL (one or more stages failed)
    2 = ERROR (execution error)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _resolve_paths() -> tuple:
    """Resolve tools_dir, eval_dir, docs_dir, and repo_root."""
    tools_dir = Path(__file__).resolve().parent
    fv_nvu_dir = tools_dir.parent
    eval_dir = fv_nvu_dir / "eval"
    docs_dir = fv_nvu_dir / "docs"
    # Repo root: tools/ → fv-nvu/ → skill/ → .opencode/ → repo root
    repo_root = fv_nvu_dir.parent.parent.parent
    return tools_dir, eval_dir, docs_dir, repo_root


def run_json_stage(script_path: Path, repo_root: Path, timeout: int = 120) -> dict:
    """Run a stage that outputs JSON and parse its summary.

    Used for self-check, self-verify (which support --json flag).
    """
    stage_name = script_path.name

    if not script_path.exists():
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": f"Script not found: {script_path}",
        }

    cmd = [sys.executable, str(script_path), "--json"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(repo_root)
        )

        raw = result.stdout.strip()
        try:
            data = json.loads(raw)
            raw_summary = data.get("summary", {})
            summary = {k.lower(): v for k, v in raw_summary.items()}
            has_failures = summary.get("fail", 0) > 0 or summary.get("error", 0) > 0
            return {
                "stage": stage_name,
                "passed": not has_failures,
                "summary": summary,
                "error": None,
            }
        except json.JSONDecodeError:
            return {
                "stage": stage_name,
                "passed": result.returncode == 0,
                "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
                "error": f"Could not parse JSON output (exit code: {result.returncode})",
            }

    except subprocess.TimeoutExpired:
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": f"Timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": str(e),
        }


def run_text_stage(
    script_path: Path,
    repo_root: Path,
    pass_pattern: str,
    fail_pattern: str | None = None,
    timeout: int = 120,
) -> dict:
    """Run a stage that outputs text and parse pass/fail from regex patterns.

    Used for validate_bios.py, validate_e2e.py, and other text-output validators.

    Args:
        pass_pattern: regex to extract pass count (must have group(1) and group(2))
        fail_pattern: if present in output, stage fails
    """
    stage_name = script_path.name

    if not script_path.exists():
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": f"Script not found: {script_path}",
        }

    cmd = [sys.executable, str(script_path)]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(repo_root)
        )

        stdout = result.stdout
        match = re.search(pass_pattern, stdout)

        if match:
            passed_count = int(match.group(1))
            total_count = int(match.group(2))
            failed_count = total_count - passed_count
        else:
            passed_count = 0
            total_count = 0
            failed_count = 0

        has_fail_marker = False
        if fail_pattern and re.search(fail_pattern, stdout):
            has_fail_marker = True

        stage_passed = (
            result.returncode == 0
            and failed_count == 0
            and passed_count == total_count
            and total_count > 0
            and not has_fail_marker
        )

        return {
            "stage": stage_name,
            "passed": stage_passed,
            "summary": {
                "pass": passed_count,
                "fail": failed_count,
                "warn": 0,
                "total": total_count,
            },
            "error": None
            if stage_passed
            else f"rc={result.returncode}, {passed_count}/{total_count}",
        }

    except subprocess.TimeoutExpired:
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": f"Timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "stage": stage_name,
            "passed": False,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "total": 0},
            "error": str(e),
        }


def run_advisory_stage(script_path: Path, repo_root: Path, timeout: int = 120) -> dict:
    """Run an advisory stage (learn/study/improve) — does not block the gate.

    These stages are informational: they detect gaps and generate proposals
    but a non-zero exit code does NOT fail the gate.
    """
    stage_name = script_path.name

    if not script_path.exists():
        return {
            "stage": stage_name,
            "passed": True,  # Advisory — never blocks
            "advisory": True,
            "summary": {"pass": 0, "fail": 0, "warn": 0, "skip": 0, "total": 0},
            "error": f"Script not found: {script_path}",
        }

    cmd = [sys.executable, str(script_path)]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(repo_root)
        )

        # Count findings from text output
        changes = len(re.findall(r"CHANGE", result.stdout))
        skips = len(re.findall(r"SKIP", result.stdout))
        warns = len(re.findall(r"WARN", result.stdout))
        proposals = len(re.findall(r"proposal", result.stdout, re.IGNORECASE))

        return {
            "stage": stage_name,
            "passed": True,  # Advisory — always passes gate
            "advisory": True,
            "summary": {
                "change": changes,
                "warn": warns,
                "skip": skips,
                "proposals": proposals,
                "total": changes + warns + skips,
            },
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "stage": stage_name,
            "passed": True,  # Advisory — timeout doesn't block gate
            "advisory": True,
            "summary": {"change": 0, "warn": 0, "skip": 0, "proposals": 0, "total": 0},
            "error": f"Timed out after {timeout}s (advisory — not blocking)",
        }
    except Exception as e:
        return {
            "stage": stage_name,
            "passed": True,
            "advisory": True,
            "summary": {"change": 0, "warn": 0, "skip": 0, "proposals": 0, "total": 0},
            "error": f"{e} (advisory — not blocking)",
        }


def main():
    parser = argparse.ArgumentParser(description="NVU Quality Gate — CI/CD gate")
    parser.add_argument("--check", action="store_true", help="Run self-check only")
    parser.add_argument("--verify", action="store_true", help="Run self-verify only")
    parser.add_argument(
        "--quick", action="store_true", help="Run self-check only (alias)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all validators + advisory stages (learn/study/improve)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    tools_dir, eval_dir, docs_dir, repo_root = _resolve_paths()

    # Determine which stages to run
    selective = args.check or args.verify or args.quick
    run_check = args.check or args.quick or not selective
    run_verify = args.verify or not selective
    run_bios = not selective  # Always run in default/full mode
    run_e2e = not selective  # Always run in default/full mode
    run_advisory = args.full  # Only in --full mode

    stages: list[dict] = []
    all_passed = True

    # === CORE VALIDATORS (blocking — fail the gate) ===

    if run_check:
        result = run_json_stage(tools_dir / "nvu_self_check.py", repo_root)
        stages.append(result)
        if not result["passed"]:
            all_passed = False

    if run_verify:
        result = run_json_stage(tools_dir / "nvu_self_verify.py", repo_root)
        stages.append(result)
        if not result["passed"]:
            all_passed = False

    if run_bios:
        result = run_text_stage(
            eval_dir / "validate_bios.py",
            repo_root,
            pass_pattern=r"\((\d+)/(\d+)\)",
            fail_pattern=r"[1-9]\d*\s+FAIL",
        )
        stages.append(result)
        if not result["passed"]:
            all_passed = False

    if run_e2e:
        result = run_text_stage(
            docs_dir / "validate_e2e.py",
            repo_root,
            pass_pattern=r"(\d+)/(\d+)\s*CONFIRMED",
            fail_pattern=r"MISMATCH",
        )
        stages.append(result)
        if not result["passed"]:
            all_passed = False

    # === ADVISORY STAGES (non-blocking — informational only) ===

    if run_advisory:
        for script_name in [
            "nvu_self_learn.py",
            "nvu_self_study.py",
            "nvu_self_improve.py",
        ]:
            result = run_advisory_stage(tools_dir / script_name, repo_root, timeout=180)
            stages.append(result)

    # === AGGREGATE RESULTS ===

    core_stages = [s for s in stages if not s.get("advisory")]
    advisory_stages = [s for s in stages if s.get("advisory")]

    total_pass = sum(s["summary"].get("pass", 0) for s in core_stages)
    total_fail = sum(s["summary"].get("fail", 0) for s in core_stages)
    total_warn = sum(s["summary"].get("warn", 0) for s in core_stages)
    total_error = sum(1 for s in core_stages if s.get("error") and not s["passed"])

    gate_result = {
        "gate": "PASS" if all_passed else "FAIL",
        "core_stages": core_stages,
        "advisory_stages": advisory_stages,
        "aggregate": {
            "pass": total_pass,
            "fail": total_fail,
            "warn": total_warn,
            "error": total_error,
            "total": total_pass + total_fail + total_warn,
        },
    }

    if args.json:
        print(json.dumps(gate_result, indent=2))
    else:
        print("=" * 65)
        print("  NVU QUALITY GATE")
        print("=" * 65)

        # Core validators
        print("  CORE VALIDATORS (blocking):")
        for stage in core_stages:
            icon = "✅" if stage["passed"] else "❌"
            s = stage["summary"]
            print(
                f"    {icon} {stage['stage']:28s}: "
                f"{s.get('pass', 0)} pass, {s.get('fail', 0)} fail, "
                f"{s.get('warn', 0)} warn"
            )
            if stage.get("error") and not stage["passed"]:
                print(f"       Error: {stage['error']}")

        # Advisory stages
        if advisory_stages:
            print()
            print("  ADVISORY STAGES (non-blocking):")
            for stage in advisory_stages:
                s = stage["summary"]
                parts = []
                for key in ["change", "warn", "skip", "proposals"]:
                    val = s.get(key, 0)
                    if val:
                        parts.append(f"{val} {key}")
                detail = ", ".join(parts) if parts else "no findings"
                print(f"    ℹ️  {stage['stage']:28s}: {detail}")
                if stage.get("error"):
                    print(f"       Note: {stage['error']}")

        # Summary
        print("-" * 65)
        agg = gate_result["aggregate"]
        print(f"  TOTAL: {agg['pass']} pass, {agg['fail']} fail, {agg['warn']} warn")
        gate_str = "PASS" if all_passed else "FAIL"
        print(f"  QUALITY GATE: {gate_str}")
        print("=" * 65)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
