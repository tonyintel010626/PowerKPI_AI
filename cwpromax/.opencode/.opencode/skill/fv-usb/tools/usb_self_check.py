#!/usr/bin/env python3
"""
FV-USB Self-Check Script
Domain: USB Functional Validation
Owner: kvejaya
Version: 2.0.0

Structural integrity checks for the FV-USB skill tree.
Validates file presence, frontmatter format, cross-references,
owner tags, and stale patterns.

Usage:
    python usb_self_check.py [--config CONFIG_PATH] [--verbose]
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Default paths
REPO_ROOT = Path(__file__).resolve().parents[4]  # up from tools/ -> fv-usb/ -> skill/ -> .opencode/ -> repo
DEFAULT_CONFIG = REPO_ROOT / ".opencode" / "skill" / "fv-usb" / "tools" / "self_improvement_config.json"


def load_config(config_path: str = None) -> dict:
    """Load self-improvement configuration."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        print(f"ERROR: Config file not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file_exists(filepath: Path, desc: str) -> Tuple[bool, str]:
    """Check if a required file exists."""
    if filepath.exists():
        return True, f"PASS: {desc} exists — {filepath.name}"
    return False, f"FAIL: {desc} missing — {filepath}"


def check_frontmatter(filepath: Path) -> List[Tuple[bool, str]]:
    """Check YAML frontmatter format in SKILL.md files."""
    results = []
    if not filepath.exists():
        results.append((False, f"FAIL: File not found — {filepath}"))
        return results

    content = filepath.read_text(encoding="utf-8")

    # Check for frontmatter delimiters
    if content.startswith("---"):
        results.append((True, f"PASS: {filepath.name} has frontmatter"))
    else:
        results.append((False, f"FAIL: {filepath.name} missing frontmatter delimiters"))
        return results

    # Extract frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        results.append((False, f"FAIL: {filepath.name} frontmatter not properly closed"))
        return results

    fm = fm_match.group(1)

    # Check for correct key format (singular, not plural)
    if re.search(r"^\s*tools:", fm, re.MULTILINE):
        results.append((False, f"FAIL: {filepath.name} uses 'tools:' (should be 'tool:')"))
    if re.search(r"^\s*permissions:", fm, re.MULTILINE):
        results.append((False, f"FAIL: {filepath.name} uses 'permissions:' (should be 'permission:')"))

    # Check required fields
    for field in ["name", "version", "owner", "description"]:
        if re.search(rf"^\s*{field}:", fm, re.MULTILINE):
            results.append((True, f"PASS: {filepath.name} has '{field}' in frontmatter"))
        else:
            results.append((False, f"FAIL: {filepath.name} missing '{field}' in frontmatter"))

    return results


def check_owner_tag(filepath: Path, expected_owner: str) -> Tuple[bool, str]:
    """Check if file contains the expected owner tag."""
    if not filepath.exists():
        return False, f"FAIL: File not found — {filepath}"
    content = filepath.read_text(encoding="utf-8")
    if expected_owner in content:
        return True, f"PASS: {filepath.name} has owner tag '{expected_owner}'"
    return False, f"FAIL: {filepath.name} missing owner tag '{expected_owner}'"


def check_cross_references(skill_base: Path, cross_refs: Dict) -> List[Tuple[bool, str]]:
    """Check that cross-referenced skills exist."""
    results = []
    for skill, refs in cross_refs.items():
        skill_path = skill_base / skill / "SKILL.md"
        if not skill_path.exists():
            results.append((False, f"FAIL: Cross-ref source '{skill}' not found"))
            continue
        content = skill_path.read_text(encoding="utf-8")
        for ref in refs:
            if ref in content.lower() or ref in content:
                results.append((True, f"PASS: {skill}/SKILL.md references '{ref}'"))
            else:
                results.append((False, f"FAIL: {skill}/SKILL.md missing reference to '{ref}'"))
    return results


def check_stale_patterns(skill_base: Path, patterns: Dict) -> List[Tuple[bool, str]]:
    """Check for stale/deprecated patterns in SKILL.md files."""
    results = []
    for skill_file in skill_base.rglob("SKILL.md"):
        content = skill_file.read_text(encoding="utf-8")
        rel = skill_file.relative_to(skill_base)
        for name, pattern in patterns.items():
            if re.search(pattern, content, re.MULTILINE):
                results.append((False, f"FAIL: {rel} has stale pattern '{name}'"))
            else:
                results.append((True, f"PASS: {rel} clean of stale pattern '{name}'"))
    return results


def run_self_check(config_path: str = None, verbose: bool = False) -> Tuple[int, int, List[str]]:
    """
    Run all structural checks.

    Returns:
        (pass_count, fail_count, messages)
    """
    config = load_config(config_path)
    skill_base = REPO_ROOT / config["paths"]["skill_base"]
    messages = []
    passes = 0
    fails = 0

    def record(ok: bool, msg: str):
        nonlocal passes, fails
        if ok:
            passes += 1
        else:
            fails += 1
        messages.append(msg)
        if verbose or not ok:
            print(msg)

    # 1. Check all expected skill files exist
    print("\n=== File Existence Checks ===")
    for skill in config["skills"]:
        path = skill_base / skill / "SKILL.md"
        ok, msg = check_file_exists(path, f"Skill '{skill}'")
        record(ok, msg)

    # Check docs
    docs_dir = REPO_ROOT / config["paths"]["docs_dir"]
    for doc in config["docs"]:
        ok, msg = check_file_exists(docs_dir / doc, f"Doc '{doc}'")
        record(ok, msg)

    # Check eval and tools dirs
    for dir_key in ["eval_dir", "tools_dir", "reports_dir"]:
        dir_path = REPO_ROOT / config["paths"][dir_key]
        ok, msg = check_file_exists(dir_path, f"Directory '{dir_key}'")
        record(ok, msg)

    # 2. Check frontmatter in all SKILL.md files
    print("\n=== Frontmatter Checks ===")
    for skill_file in skill_base.rglob("SKILL.md"):
        for ok, msg in check_frontmatter(skill_file):
            record(ok, msg)

    # 3. Check owner tags
    print("\n=== Owner Tag Checks ===")
    owner_tag = config["self_check"]["owner_tag"]
    for skill_file in skill_base.rglob("SKILL.md"):
        ok, msg = check_owner_tag(skill_file, owner_tag)
        record(ok, msg)

    # Agent definition
    agent_path = REPO_ROOT / config["paths"]["agent_def"]
    if agent_path.exists():
        ok, msg = check_owner_tag(agent_path, owner_tag)
        record(ok, msg)

    # 4. Check cross-references
    print("\n=== Cross-Reference Checks ===")
    for ok, msg in check_cross_references(skill_base, config["self_check"]["cross_references"]):
        record(ok, msg)

    # 5. Check stale patterns
    print("\n=== Stale Pattern Checks ===")
    for ok, msg in check_stale_patterns(skill_base, config["self_check"]["stale_patterns"]):
        record(ok, msg)

    # 6. Check skill count matches expected
    print("\n=== Skill Count Check ===")
    actual_count = len(config["skills"])
    expected_count = config["self_check"]["expected_skill_count"]
    if actual_count == expected_count:
        record(True, f"PASS: Skill count matches expected ({actual_count})")
    else:
        record(False, f"FAIL: Skill count {actual_count} != expected {expected_count}")

    # Summary
    total = passes + fails
    print(f"\n{'='*60}")
    print(f"SELF-CHECK SUMMARY: {passes}/{total} passed, {fails} failed")
    print(f"{'='*60}")

    return passes, fails, messages


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV-USB Self-Check")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--verbose", action="store_true", help="Show all results")
    args = parser.parse_args()

    passes, fails, _ = run_self_check(args.config, args.verbose)
    sys.exit(0 if fails == 0 else 1)
