#!/usr/bin/env python3
"""Generic Self-Verify: Data-driven content assertion framework for any skill tree.

Runs regex-based assertions against skill file content. Assertions are defined
declaratively in a JSON file, making them easy to generate and maintain.

Usage:
    python self_verify.py <config.json>
    python self_verify.py <config.json> --category REG
    python self_verify.py <config.json> --test REG-001
    python self_verify.py <config.json> --list
    python self_verify.py <config.json> --json
    python self_verify.py <config.json> --save <directory>
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from common module
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from self_improve_common import Finding, Report, load_config, resolve_path


# ---------------------------------------------------------------------------
# Assertion types
# ---------------------------------------------------------------------------

def assert_contains(content: str, pattern: str, skill_name: str,
                    description: str = "") -> Finding:
    """Assert that content matches a regex pattern."""
    try:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return Finding(
                check="verify",
                target=skill_name,
                status="PASS",
                message=description or f"Pattern found: {pattern[:60]}",
            )
        return Finding(
            check="verify",
            target=skill_name,
            status="FAIL",
            message=description or f"Pattern NOT found: {pattern[:60]}",
            details={"pattern": pattern},
        )
    except re.error as e:
        return Finding(
            check="verify",
            target=skill_name,
            status="ERROR",
            message=f"Invalid regex: {e}",
            details={"pattern": pattern},
        )


def assert_not_contains(content: str, pattern: str, skill_name: str,
                        description: str = "") -> Finding:
    """Assert that content does NOT match a regex pattern."""
    try:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return Finding(
                check="verify",
                target=skill_name,
                status="FAIL",
                message=description or f"Unwanted pattern found: {pattern[:60]}",
                details={"pattern": pattern},
            )
        return Finding(
            check="verify",
            target=skill_name,
            status="PASS",
            message=description or f"Correctly absent: {pattern[:60]}",
        )
    except re.error as e:
        return Finding(
            check="verify",
            target=skill_name,
            status="ERROR",
            message=f"Invalid regex: {e}",
            details={"pattern": pattern},
        )


def assert_value_match(content: str, field_pattern: str, expected_value: str,
                       skill_name: str, description: str = "",
                       context_chars: int = 300) -> Finding:
    """Assert that a field is present and its nearby context contains the expected value."""
    try:
        match = re.search(field_pattern, content, re.IGNORECASE | re.MULTILINE)
        if not match:
            return Finding(
                check="verify",
                target=skill_name,
                status="FAIL",
                message=description or f"Field not found: {field_pattern[:60]}",
                details={"field_pattern": field_pattern, "expected_value": expected_value},
            )
        start = max(0, match.start() - context_chars)
        end = min(len(content), match.end() + context_chars)
        context = content[start:end]
        if re.search(re.escape(expected_value), context, re.IGNORECASE):
            return Finding(
                check="verify",
                target=skill_name,
                status="PASS",
                message=description or f"Value confirmed: {expected_value[:60]}",
            )
        return Finding(
            check="verify",
            target=skill_name,
            status="FAIL",
            message=description or f"Value mismatch near {field_pattern[:40]}",
            details={
                "field_pattern": field_pattern,
                "expected_value": expected_value,
                "actual_context": context[:200],
            },
        )
    except re.error as e:
        return Finding(
            check="verify",
            target=skill_name,
            status="ERROR",
            message=f"Invalid regex: {e}",
        )


ASSERTION_DISPATCH = {
    "contains": assert_contains,
    "not_contains": assert_not_contains,
    "value_match": assert_value_match,
}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def load_assertions(config: Dict[str, Any]) -> Dict[str, Any]:
    """Load assertion definitions from the assertions file specified in config."""
    assertions_path_str = config.get("self_verify", {}).get("assertions_file")
    if not assertions_path_str:
        # Look for assertions.json next to config
        config_path = config.get("_config_path", "")
        if config_path:
            assertions_path = Path(config_path).parent / "assertions.json"
        else:
            assertions_path = _SCRIPT_DIR / "assertions.json"
    else:
        repo_root = Path(config["_repo_root"]) if "_repo_root" in config else None
        assertions_path = resolve_path(assertions_path_str, repo_root)

    if not assertions_path.exists():
        return {}

    with open(assertions_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_skill_content(skill_name: str, config: Dict[str, Any]) -> str:
    """Read skill file content by name."""
    skill_base = config.get("paths", {}).get("skill_base", "")
    if not skill_base:
        return ""
    repo_root = config.get("_repo_root", Path.cwd())
    if isinstance(repo_root, str):
        repo_root = Path(repo_root)
    skill_path = repo_root / skill_base / skill_name / "SKILL.md"
    if not skill_path.exists():
        # Try as direct file path
        skill_path = repo_root / skill_base / f"{skill_name}.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8", errors="replace")


def run_test(test_id: str, test_def: Dict[str, Any],
             config: Dict[str, Any]) -> List[Finding]:
    """Run a single test's assertions."""
    findings: List[Finding] = []
    skill_name = test_def.get("skill", "")

    # Cache skill content
    content = read_skill_content(skill_name, config)
    if not content:
        findings.append(Finding(
            check="verify",
            target=skill_name,
            status="ERROR",
            message=f"[{test_id}] Skill file not found or empty: {skill_name}",
        ))
        return findings

    for assertion in test_def.get("assertions", []):
        a_type = assertion.get("type", "contains")
        pattern = assertion.get("pattern", "")
        desc = assertion.get("description", "")
        desc_prefix = f"[{test_id}] {desc}" if desc else f"[{test_id}]"

        if a_type == "value_match":
            expected = assertion.get("expected_value", "")
            context_chars = assertion.get("context_chars", 300)
            finding = assert_value_match(
                content, pattern, expected, skill_name,
                description=desc_prefix, context_chars=context_chars,
            )
        elif a_type in ASSERTION_DISPATCH:
            finding = ASSERTION_DISPATCH[a_type](
                content, pattern, skill_name, description=desc_prefix,
            )
        else:
            finding = Finding(
                check="verify",
                target=skill_name,
                status="ERROR",
                message=f"[{test_id}] Unknown assertion type: {a_type}",
            )

        findings.append(finding)

    return findings


def run_all_tests(config: Dict[str, Any],
                  category: Optional[str] = None,
                  test_id: Optional[str] = None) -> Report:
    """Run all assertions, optionally filtered by category or test ID."""
    report = Report(name="self-verify")
    assertions_data = load_assertions(config)

    if not assertions_data:
        report.add(Finding(
            check="verify",
            target="assertions",
            status="WARN",
            message="No assertions file found. Create assertions.json with test definitions.",
        ))
        return report

    tests = assertions_data.get("tests", {})

    for tid, tdef in sorted(tests.items()):
        # Filter by test ID
        if test_id and tid != test_id:
            continue
        # Filter by category (prefix before hyphen)
        if category:
            test_cat = tid.split("-")[0] if "-" in tid else tid
            if test_cat.upper() != category.upper():
                continue

        findings = run_test(tid, tdef, config)
        for f in findings:
            report.add(f)

    return report


# ---------------------------------------------------------------------------
# Utility: list tests
# ---------------------------------------------------------------------------

def list_tests(config: Dict[str, Any]) -> None:
    """Print available test IDs and descriptions."""
    assertions_data = load_assertions(config)
    tests = assertions_data.get("tests", {})

    categories: Dict[str, List[str]] = {}
    for tid, tdef in sorted(tests.items()):
        cat = tid.split("-")[0] if "-" in tid else "OTHER"
        if cat not in categories:
            categories[cat] = []
        name = tdef.get("name", tid)
        n_assertions = len(tdef.get("assertions", []))
        categories[cat].append(f"  {tid}: {name} ({n_assertions} assertions)")

    total = 0
    for cat in sorted(categories):
        print(f"\n[{cat}]")
        for line in categories[cat]:
            print(line)
            total += 1
    print(f"\nTotal: {total} tests")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generic self-verify: run content assertions against skill files"
    )
    parser.add_argument("config", help="Path to self-improvement config JSON")
    parser.add_argument("--category", "-c", help="Run only tests in this category")
    parser.add_argument("--test", "-t", help="Run only this test ID")
    parser.add_argument("--list", "-l", action="store_true", help="List available tests")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", metavar="DIR", help="Save report to directory")
    args = parser.parse_args()

    config = load_config(Path(args.config))

    if args.list:
        list_tests(config)
        return 0

    report = run_all_tests(config, category=args.category, test_id=args.test)

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    if args.save:
        save_path = Path(args.save)
        report.save(save_path)
        print(f"\nReport saved to {save_path}")

    return 0 if not report.has_failures else 1


if __name__ == "__main__":
    sys.exit(main())
