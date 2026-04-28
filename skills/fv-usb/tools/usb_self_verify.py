#!/usr/bin/env python3
"""
FV-USB Self-Verify Script
Domain: USB Functional Validation
Owner: kvejaya
Version: 2.0.0

Content verification using eval/assertions.py test definitions.
Runs regex-based assertions against skill files and reports results.

Usage:
    python usb_self_verify.py [--config CONFIG_PATH] [--verbose] [--filter PATTERN]
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG = REPO_ROOT / ".opencode" / "skill" / "fv-usb" / "tools" / "self_improvement_config.json"


def load_config(config_path: str = None) -> dict:
    """Load self-improvement configuration."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_assertions(assertions_path: Path) -> dict:
    """Dynamically load EVAL_TESTS from assertions.py."""
    spec = importlib.util.spec_from_file_location("assertions", assertions_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EVAL_TESTS


def resolve_skill_path(skill_name: str, config: dict) -> Path:
    """Map skill name to file path."""
    skill_base = REPO_ROOT / config["paths"]["skill_base"]

    if skill_name == "root":
        return skill_base / "SKILL.md"
    elif skill_name == "agent":
        return REPO_ROOT / config["paths"]["agent_def"]
    elif skill_name.startswith("docs/") or skill_name.endswith(".md"):
        # docs references like "known_issues" -> docs/known_issues.md
        doc_name = skill_name.replace("docs/", "")
        if not doc_name.endswith(".md"):
            doc_name += ".md"
        return skill_base / "docs" / doc_name
    else:
        # Sub-skill name like "xhci" -> xhci/SKILL.md
        # Also handles nested like "debug/etl-decode" -> debug/etl-decode/SKILL.md
        return skill_base / skill_name / "SKILL.md"


def run_assertion(assertion: tuple, content: str) -> Tuple[bool, str]:
    """
    Run a single assertion against content.

    Returns:
        (passed, message)
    """
    atype = assertion[0]

    if atype == "contains":
        _, _skill, pattern, desc = assertion
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return True, f"  PASS: {desc}"
        return False, f"  FAIL: {desc} — pattern not found: {pattern}"

    elif atype == "not_contains":
        _, _skill, pattern, desc = assertion
        if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return True, f"  PASS: {desc}"
        return False, f"  FAIL: {desc} — unwanted pattern found: {pattern}"

    elif atype == "value_match":
        _, _skill, field_re, expected, desc = assertion
        match = re.search(field_re, content, re.IGNORECASE | re.MULTILINE)
        if match:
            # Check if expected value is nearby (within 200 chars)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 200)
            region = content[start:end]
            if re.search(re.escape(str(expected)), region):
                return True, f"  PASS: {desc}"
            return False, f"  FAIL: {desc} — field found but value '{expected}' not nearby"
        return False, f"  FAIL: {desc} — field not found: {field_re}"

    else:
        return False, f"  SKIP: Unknown assertion type '{atype}'"


def run_self_verify(config_path: str = None, verbose: bool = False,
                     filter_pattern: str = None) -> Tuple[int, int, int, List[str]]:
    """
    Run all content verification assertions.

    Returns:
        (pass_count, fail_count, skip_count, messages)
    """
    config = load_config(config_path)
    assertions_path = REPO_ROOT / config["self_verify"]["assertions_file"]
    eval_tests = load_assertions(assertions_path)

    passes = 0
    fails = 0
    skips = 0
    messages = []
    file_cache = {}

    for test_id, test in sorted(eval_tests.items()):
        # Apply filter if specified
        if filter_pattern and not re.search(filter_pattern, test_id, re.IGNORECASE):
            continue

        test_name = test["name"]
        print(f"\n[{test_id}] {test_name}")
        messages.append(f"[{test_id}] {test_name}")

        for assertion in test["assertions"]:
            skill_name = assertion[1]

            # Load file content (with caching)
            if skill_name not in file_cache:
                fpath = resolve_skill_path(skill_name, config)
                if fpath.exists():
                    file_cache[skill_name] = fpath.read_text(encoding="utf-8")
                else:
                    file_cache[skill_name] = None
                    print(f"  WARN: File not found for '{skill_name}': {fpath}")

            content = file_cache[skill_name]
            if content is None:
                skips += 1
                msg = f"  SKIP: File not found for skill '{skill_name}'"
                messages.append(msg)
                if verbose:
                    print(msg)
                continue

            ok, msg = run_assertion(assertion, content)
            if ok:
                passes += 1
            else:
                fails += 1
            messages.append(msg)
            if verbose or not ok:
                print(msg)

    # Summary
    total = passes + fails + skips
    pass_pct = (passes / max(total - skips, 1)) * 100
    threshold = config["self_verify"]["pass_threshold_pct"]

    print(f"\n{'='*60}")
    print(f"SELF-VERIFY SUMMARY: {passes} passed, {fails} failed, {skips} skipped")
    print(f"Pass rate: {pass_pct:.1f}% (threshold: {threshold}%)")
    print(f"{'='*60}")

    if pass_pct < threshold:
        print(f"BELOW THRESHOLD: {pass_pct:.1f}% < {threshold}%")

    # Write results to reports dir if it exists
    reports_dir = REPO_ROOT / config["self_verify"]["results_dir"]
    if reports_dir.exists():
        results = {
            "passes": passes,
            "fails": fails,
            "skips": skips,
            "pass_pct": round(pass_pct, 1),
            "threshold": threshold,
            "below_threshold": pass_pct < threshold,
            "messages": messages,
        }
        results_file = reports_dir / "self_verify_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to: {results_file}")

    return passes, fails, skips, messages


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV-USB Self-Verify")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--verbose", action="store_true", help="Show all results")
    parser.add_argument("--filter", type=str, default=None, help="Filter test IDs by regex")
    args = parser.parse_args()

    passes, fails, skips, _ = run_self_verify(args.config, args.verbose, args.filter)
    sys.exit(0 if fails == 0 else 1)
