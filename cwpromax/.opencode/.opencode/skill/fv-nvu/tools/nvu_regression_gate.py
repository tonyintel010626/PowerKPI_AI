#!/usr/bin/env python3
"""NVU Regression Gate — Pre-commit quality check.

Runs core validators before allowing commits to NVU skill tree files.
Can be used as a standalone check or integrated into git pre-commit hooks.

Usage:
    python nvu_regression_gate.py              # Full gate check
    python nvu_regression_gate.py --quick      # Quick mode (self-check only)
    python nvu_regression_gate.py --install     # Install git pre-commit hook
    python nvu_regression_gate.py --uninstall   # Remove git pre-commit hook
    python nvu_regression_gate.py --json        # JSON output
    python nvu_regression_gate.py --strict      # Fail on any WARN (not just FAIL)

Exit codes:
    0 = PASS (safe to commit)
    1 = FAIL (regressions detected — do not commit)
    2 = ERROR (tool failure)
"""

import argparse
import json
import logging
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT
# Walk up to find .git directory
_p = SKILL_ROOT
while _p != _p.parent:
    if (_p / ".git").exists():
        REPO_ROOT = _p
        break
    _p = _p.parent

HOOK_PATH = REPO_ROOT / ".git" / "hooks" / "pre-commit"
TOOLS_DIR = SKILL_ROOT / "tools"

logger = logging.getLogger("nvu_regression_gate")


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------
class Stage:
    """A validation stage to run."""

    def __init__(
        self,
        name: str,
        cmd: List[str],
        required: bool = True,
        timeout: int = 60,
        parse_json: bool = False,
    ):
        self.name = name
        self.cmd = cmd
        self.required = required
        self.timeout = timeout
        self.parse_json = parse_json


# Core stages — must all pass
CORE_STAGES = [
    Stage(
        "self_check",
        [sys.executable, str(TOOLS_DIR / "nvu_self_check.py"), "--json"],
        required=True,
        timeout=60,
        parse_json=True,
    ),
    Stage(
        "self_verify",
        [sys.executable, str(TOOLS_DIR / "nvu_self_verify.py"), "--json"],
        required=True,
        timeout=60,
        parse_json=True,
    ),
    Stage(
        "delegation_check",
        [sys.executable, str(TOOLS_DIR / "nvu_delegation_check.py")],
        required=True,
        timeout=60,
        parse_json=False,
    ),
]

# Quick stages — subset for fast feedback
QUICK_STAGES = [CORE_STAGES[0]]  # self_check only

# Extended stages — advisory, non-blocking
ADVISORY_STAGES = [
    Stage(
        "self_learn",
        [sys.executable, str(TOOLS_DIR / "nvu_self_learn.py"), "--json"],
        required=False,
        timeout=60,
        parse_json=True,
    ),
    Stage(
        "wiki_offline",
        [sys.executable, str(TOOLS_DIR / "nvu_self_wiki.py"), "--offline"],
        required=False,
        timeout=60,
        parse_json=False,
    ),
]


# ---------------------------------------------------------------------------
# Check if NVU files are staged
# ---------------------------------------------------------------------------
def has_staged_nvu_files() -> bool:
    """Check if any NVU skill tree files are staged for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return True  # Can't determine — run the gate anyway

        nvu_patterns = [
            ".opencode/skill/fv-nvu/",
            ".opencode/agent/FV/FV-NVU.md",
        ]
        for line in result.stdout.splitlines():
            if any(line.startswith(p) for p in nvu_patterns):
                return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True  # Can't determine — run the gate anyway


# ---------------------------------------------------------------------------
# Run stages
# ---------------------------------------------------------------------------
def run_stage(stage: Stage) -> Dict[str, Any]:
    """Run a validation stage and return results."""
    result_data: Dict[str, Any] = {
        "name": stage.name,
        "required": stage.required,
        "status": "UNKNOWN",
        "exit_code": -1,
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "duration_s": 0.0,
        "error": None,
    }

    start = time.time()
    try:
        proc = subprocess.run(
            stage.cmd,
            capture_output=True,
            text=True,
            timeout=stage.timeout,
            cwd=str(SKILL_ROOT),
        )
        result_data["exit_code"] = proc.returncode
        result_data["duration_s"] = round(time.time() - start, 2)

        # Parse output
        if stage.parse_json:
            try:
                data = json.loads(proc.stdout)
                result_data["passed"] = data.get("passed", data.get("pass", 0))
                result_data["failed"] = data.get("failed", data.get("fail", 0))
                result_data["warnings"] = data.get("warnings", data.get("warn", 0))
            except (json.JSONDecodeError, ValueError):
                _parse_text_output(proc.stdout, result_data)
        else:
            _parse_text_output(proc.stdout, result_data)

        # Determine status
        if proc.returncode == 0:
            result_data["status"] = "PASS"
        elif result_data["failed"] > 0:
            result_data["status"] = "FAIL"
        else:
            result_data["status"] = "WARN"

    except subprocess.TimeoutExpired:
        result_data["duration_s"] = round(time.time() - start, 2)
        result_data["status"] = "TIMEOUT"
        result_data["error"] = f"Timed out after {stage.timeout}s"
    except FileNotFoundError:
        result_data["status"] = "ERROR"
        result_data["error"] = "Tool not found"

    return result_data


def _parse_text_output(stdout: str, result_data: Dict[str, Any]) -> None:
    """Parse text output for pass/fail/warn counts."""
    # Look for summary line like "6 PASS, 0 FAIL, 0 WARN"
    summary_match = re.search(r"(\d+)\s+PASS.*?(\d+)\s+FAIL.*?(\d+)\s+WARN", stdout)
    if summary_match:
        result_data["passed"] = int(summary_match.group(1))
        result_data["failed"] = int(summary_match.group(2))
        result_data["warnings"] = int(summary_match.group(3))
    else:
        # Count individual lines
        result_data["passed"] = len(re.findall(r"^\s*PASS\b", stdout, re.MULTILINE))
        result_data["failed"] = len(re.findall(r"^\s*FAIL\b", stdout, re.MULTILINE))
        result_data["warnings"] = len(re.findall(r"^\s*WARN\b", stdout, re.MULTILINE))


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------
def run_gate(
    stages: List[Stage],
    strict: bool = False,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Run all stages and determine gate pass/fail.

    Returns (passed: bool, results: list).
    """
    results = []
    gate_passed = True

    for stage in stages:
        logger.info("Running %s...", stage.name)
        result = run_stage(stage)
        results.append(result)

        status_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "TIMEOUT": "⏰",
            "ERROR": "💥",
        }.get(result["status"], "❓")

        logger.info(
            "  %s %s: %dP/%dF/%dW (%.1fs)",
            status_icon,
            result["name"],
            result["passed"],
            result["failed"],
            result["warnings"],
            result["duration_s"],
        )

        # Gate logic
        if result["status"] == "FAIL" and stage.required:
            gate_passed = False
        if strict and result["warnings"] > 0 and stage.required:
            gate_passed = False
        if result["status"] in ("TIMEOUT", "ERROR") and stage.required:
            gate_passed = False

    return gate_passed, results


# ---------------------------------------------------------------------------
# Hook installation
# ---------------------------------------------------------------------------
HOOK_SCRIPT = r"""#!/bin/sh
# NVU Regression Gate — auto-installed pre-commit hook
# Checks NVU skill tree files before allowing commits.
# Remove with: python .opencode/skill/fv-nvu/tools/nvu_regression_gate.py --uninstall

# Only run if NVU files are staged
NVU_FILES=$(git diff --cached --name-only | grep -E "\.opencode/skill/fv-nvu/|\.opencode/agent/FV/FV-NVU\.md")
if [ -z "$NVU_FILES" ]; then
    exit 0
fi

echo "🔒 NVU Regression Gate: checking staged NVU files..."
python "{tool_path}" --quick
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ NVU Regression Gate FAILED. Fix issues before committing."
    echo "   Run: python {tool_path}"
    echo "   Skip: git commit --no-verify"
    exit 1
fi

echo "✅ NVU Regression Gate passed."
exit 0
"""


def install_hook() -> bool:
    """Install pre-commit hook."""
    hook_dir = HOOK_PATH.parent
    if not hook_dir.exists():
        logger.error("Git hooks directory not found: %s", hook_dir)
        return False

    # Check for existing hook
    if HOOK_PATH.exists():
        content = HOOK_PATH.read_text(encoding="utf-8", errors="replace")
        if "NVU Regression Gate" in content:
            logger.info("NVU pre-commit hook already installed at %s", HOOK_PATH)
            return True
        # Existing non-NVU hook — don't overwrite
        logger.warning(
            "Existing pre-commit hook found at %s. "
            "Please manually integrate NVU gate or remove existing hook first.",
            HOOK_PATH,
        )
        return False

    # Write hook
    tool_path = str(SCRIPT_DIR / "nvu_regression_gate.py").replace("\\", "/")
    content = HOOK_SCRIPT.replace("{tool_path}", tool_path)
    HOOK_PATH.write_text(content, encoding="utf-8")

    # Make executable (Unix)
    if os.name != "nt":
        HOOK_PATH.chmod(HOOK_PATH.stat().st_mode | stat.S_IEXEC)

    logger.info("Installed NVU pre-commit hook at %s", HOOK_PATH)
    return True


def uninstall_hook() -> bool:
    """Remove NVU pre-commit hook."""
    if not HOOK_PATH.exists():
        logger.info("No pre-commit hook found at %s", HOOK_PATH)
        return True

    content = HOOK_PATH.read_text(encoding="utf-8", errors="replace")
    if "NVU Regression Gate" not in content:
        logger.warning("Pre-commit hook at %s is not NVU — not removing.", HOOK_PATH)
        return False

    HOOK_PATH.unlink()
    logger.info("Removed NVU pre-commit hook from %s", HOOK_PATH)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="NVU Regression Gate")
    parser.add_argument(
        "--quick", action="store_true", help="Quick mode (self-check only)"
    )
    parser.add_argument("--strict", action="store_true", help="Fail on WARN too")
    parser.add_argument("--all", action="store_true", help="Include advisory stages")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--install", action="store_true", help="Install pre-commit hook"
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove pre-commit hook"
    )
    parser.add_argument(
        "--force", action="store_true", help="Run even if no NVU files staged"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.json else logging.INFO,
        format="%(message)s",
    )

    # Hook management
    if args.install:
        return 0 if install_hook() else 1
    if args.uninstall:
        return 0 if uninstall_hook() else 1

    # Check if NVU files are staged (skip check with --force)
    if not args.force and not has_staged_nvu_files():
        if args.json:
            print(json.dumps({"status": "SKIP", "reason": "No NVU files staged"}))
        else:
            logger.info("No NVU files staged — skipping regression gate")
        return 0

    # Select stages
    if args.quick:
        stages = QUICK_STAGES
    elif args.all:
        stages = CORE_STAGES + ADVISORY_STAGES
    else:
        stages = CORE_STAGES

    # Run gate
    start_time = time.time()
    gate_passed, results = run_gate(stages, strict=args.strict)
    total_time = round(time.time() - start_time, 2)

    # Summary
    total_p = sum(r["passed"] for r in results)
    total_f = sum(r["failed"] for r in results)
    total_w = sum(r["warnings"] for r in results)

    if args.json:
        output = {
            "gate": "PASS" if gate_passed else "FAIL",
            "total_passed": total_p,
            "total_failed": total_f,
            "total_warnings": total_w,
            "duration_s": total_time,
            "strict": args.strict,
            "stages": results,
        }
        print(json.dumps(output, indent=2))
    else:
        logger.info("")
        if gate_passed:
            logger.info(
                "🔓 GATE: PASS — %dP/%dF/%dW in %.1fs",
                total_p,
                total_f,
                total_w,
                total_time,
            )
        else:
            logger.info(
                "🔒 GATE: FAIL — %dP/%dF/%dW in %.1fs",
                total_p,
                total_f,
                total_w,
                total_time,
            )
            logger.info("   Fix failures before committing. Use --json for details.")

    return 0 if gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
