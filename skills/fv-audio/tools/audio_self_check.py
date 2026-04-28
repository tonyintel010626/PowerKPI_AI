#!/usr/bin/env python3
"""
FV-AUDIO Self-Check — Structural integrity checks for the audio skill tree.

Runs 11 checks:
  1. skill_files_exist      — every configured sub-skill has a SKILL.md
  2. owner_headers           — SKILL.md files contain the expected owner tag
  3. subskill_count          — number of sub-skills matches config expectation
  4. cross_refs              — key cross-references exist where expected
  5. doc_files_exist         — all configured doc files are present
  6. eval_files_exist        — eval test file is present (WARN if missing)
  7. stale_refs              — no references to removed/renamed skills
  8. frontmatter             — SKILL.md files have required header sections
  9. delegation_table        — agent def has a delegation/routing table
 10. version_consistency     — agent def version tag is consistent
 11. delegation_consistency  — delegation table lists all configured skills

Usage:
    python audio_self_check.py [--json] [-v]

Adapted from FV-THC thc_self_check.py.
Owner: huiyingt (Tan Hui Ying)
"""

import argparse
import re
import sys
import time
from pathlib import Path

# Sibling import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_self_common import (
    Finding,
    Report,
    Severity,
    find_repo_root,
    get_all_skill_paths,
    get_skill_path,
    load_config,
    read_agent_def,
    read_skill,
    resolve_path,
    setup_logging,
)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def check_skill_files_exist(cfg: dict, report: Report) -> None:
    """C01: Every configured sub-skill directory has a SKILL.md."""
    cid = "C01_skill_files_exist"
    missing = []
    for name, path in get_all_skill_paths(cfg):
        if not path.exists():
            missing.append(name)
    if missing:
        report.fail(cid, f"{len(missing)} sub-skill SKILL.md files missing",
                     detail=", ".join(missing))
    else:
        report.pass_(cid, f"All {len(cfg['skills'])} sub-skill SKILL.md files present")


def check_owner_headers(cfg: dict, report: Report) -> None:
    """C02: SKILL.md files reference the expected owner."""
    cid = "C02_owner_headers"
    owner_tag = cfg.get("self_check", {}).get("required_owner_tag", "huiyingt")
    missing_owner = []
    for name, path in get_all_skill_paths(cfg):
        content = read_skill(name, cfg)
        if content is None:
            continue  # already flagged by C01
        if owner_tag not in content.lower() and owner_tag not in content:
            missing_owner.append(name)
    if missing_owner:
        report.warn(cid, f"{len(missing_owner)} skills missing owner tag '{owner_tag}'",
                     detail=", ".join(missing_owner))
    else:
        report.pass_(cid, f"All present skills reference owner '{owner_tag}'")


def check_subskill_count(cfg: dict, report: Report) -> None:
    """C03: Number of configured sub-skills matches expectation."""
    cid = "C03_subskill_count"
    expected = cfg.get("self_check", {}).get("expected_skill_count", 17)
    actual = len(cfg.get("skills", []))
    if actual != expected:
        report.fail(cid, f"Expected {expected} sub-skills, config has {actual}")
    else:
        report.pass_(cid, f"Sub-skill count matches expectation ({actual})")


def check_cross_refs(cfg: dict, report: Report) -> None:
    """C04: Key cross-references exist between skills."""
    cid = "C04_cross_refs"
    rules = cfg.get("self_check", {}).get("cross_ref_rules", {})
    issues = []
    for rule_key, target_skills in rules.items():
        if not rule_key.endswith("_expected_in"):
            continue
        source_skill = rule_key.replace("_expected_in", "")
        for target in target_skills:
            content = read_skill(target, cfg)
            if content is None:
                continue
            # Check if source skill is mentioned (case-insensitive)
            search_term = source_skill.replace("-", "[-_ ]?")
            if not re.search(search_term, content, re.IGNORECASE):
                issues.append(f"'{source_skill}' not referenced in '{target}'")

    for rule_key, excluded_skills in rules.items():
        if not rule_key.endswith("_excluded_from"):
            continue
        source_skill = rule_key.replace("_excluded_from", "")
        # Exclusion checks are informational only — skip for now

    if issues:
        report.warn(cid, f"{len(issues)} cross-reference gaps found",
                     detail="\n".join(issues))
    else:
        report.pass_(cid, "All expected cross-references present")


def check_doc_files_exist(cfg: dict, report: Report) -> None:
    """C05: All configured doc files exist."""
    cid = "C05_doc_files_exist"
    base = resolve_path(cfg["paths"]["skill_base"])
    docs_dir = base / cfg["paths"]["docs_dir"]
    missing = []
    for doc in cfg.get("docs", []):
        if not (docs_dir / doc).exists():
            missing.append(doc)
    if missing:
        report.fail(cid, f"{len(missing)} doc files missing",
                     detail=", ".join(missing))
    else:
        report.pass_(cid, f"All {len(cfg['docs'])} doc files present")


def check_eval_files_exist(cfg: dict, report: Report) -> None:
    """C06: Eval test file exists (WARN if missing, not FAIL)."""
    cid = "C06_eval_files_exist"
    verify_cfg = cfg.get("self_verify", {})
    eval_file = verify_cfg.get("eval_tests_file", "")
    if not eval_file:
        report.skip(cid, "No eval_tests_file configured")
        return
    base = resolve_path(cfg["paths"]["skill_base"])
    path = base / eval_file
    if not path.exists():
        report.warn(cid, f"Eval test file not found: {eval_file}",
                     detail="Self-verify will run in structural-only mode")
    else:
        report.pass_(cid, f"Eval test file present: {eval_file}")


def check_stale_refs(cfg: dict, report: Report) -> None:
    """C07: No references to non-existent skills in agent def or skills."""
    cid = "C07_stale_refs"
    agent_text = read_agent_def(cfg)
    if agent_text is None:
        report.skip(cid, "Agent definition file not found")
        return

    # Scan for skill-directory-like references in agent def
    base = resolve_path(cfg["paths"]["skill_base"])
    configured = set(cfg.get("skills", []))
    stale = []

    # Check for fv-audio/<something>/SKILL.md patterns
    refs = re.findall(r'fv-audio/([a-z][-a-z0-9]*)/SKILL\.md', agent_text)
    for ref in refs:
        if ref not in configured and not (base / ref / "SKILL.md").exists():
            stale.append(ref)

    if stale:
        report.warn(cid, f"{len(stale)} potentially stale skill references",
                     detail=", ".join(set(stale)))
    else:
        report.pass_(cid, "No stale skill references detected")


def check_frontmatter(cfg: dict, report: Report) -> None:
    """C08: SKILL.md files have required header sections."""
    cid = "C08_frontmatter"
    required_sections = ["##", "owner", "platform"]
    issues = []
    for name, path in get_all_skill_paths(cfg):
        content = read_skill(name, cfg)
        if content is None:
            continue
        lower = content.lower()
        for section in required_sections:
            if section.lower() not in lower:
                issues.append(f"'{name}' missing '{section}'")

    if issues:
        report.warn(cid, f"{len(issues)} frontmatter issues",
                     detail="\n".join(issues[:10]))
    else:
        report.pass_(cid, "All skills have required frontmatter elements")


def check_delegation_table(cfg: dict, report: Report) -> None:
    """C09: Agent definition has a delegation/routing table."""
    cid = "C09_delegation_table"
    agent_text = read_agent_def(cfg)
    if agent_text is None:
        report.skip(cid, "Agent definition file not found")
        return

    # Look for a markdown table with skill routing
    has_table = bool(re.search(r'\|.*\|.*\|', agent_text))
    has_delegation = any(
        kw in agent_text.lower()
        for kw in ["delegation", "routing", "sub-skill", "subskill", "sub-agent"]
    )
    if has_table and has_delegation:
        report.pass_(cid, "Delegation/routing table found in agent definition")
    elif has_table:
        report.warn(cid, "Tables found but no explicit delegation/routing section")
    else:
        report.fail(cid, "No delegation table found in agent definition")


def check_version_consistency(cfg: dict, report: Report) -> None:
    """C10: Agent definition has a version tag."""
    cid = "C10_version_consistency"
    agent_text = read_agent_def(cfg)
    if agent_text is None:
        report.skip(cid, "Agent definition file not found")
        return

    version_match = re.search(r'[Vv]ersion[:\s]*(\d+\.\d+)', agent_text)
    rev_match = re.search(r'[Rr]ev\.?\s*(\d+\.\d+)', agent_text)
    match = version_match or rev_match
    if match:
        report.pass_(cid, f"Version tag found: {match.group(0).strip()}")
    else:
        report.warn(cid, "No version tag found in agent definition")


def check_delegation_consistency(cfg: dict, report: Report) -> None:
    """C11: Delegation table lists all configured skills."""
    cid = "C11_delegation_consistency"
    agent_text = read_agent_def(cfg)
    if agent_text is None:
        report.skip(cid, "Agent definition file not found")
        return

    agent_lower = agent_text.lower()
    configured = cfg.get("skills", [])
    not_mentioned = []
    for skill in configured:
        # Normalize: "display-audio" → check both "display-audio" and "display audio"
        variants = [skill.lower(), skill.replace("-", " ").lower(), skill.replace("-", "_").lower()]
        if not any(v in agent_lower for v in variants):
            not_mentioned.append(skill)

    if not_mentioned:
        report.warn(cid, f"{len(not_mentioned)} skills not mentioned in agent def",
                     detail=", ".join(not_mentioned))
    else:
        report.pass_(cid, f"All {len(configured)} skills referenced in agent definition")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_CHECKS = [
    check_skill_files_exist,
    check_owner_headers,
    check_subskill_count,
    check_cross_refs,
    check_doc_files_exist,
    check_eval_files_exist,
    check_stale_refs,
    check_frontmatter,
    check_delegation_table,
    check_version_consistency,
    check_delegation_consistency,
]


def run_all_checks(cfg: dict | None = None) -> Report:
    """Execute every structural check and return the aggregated report."""
    t0 = time.time()
    cfg = cfg or load_config()
    report = Report(stage="self-check")
    for check_fn in ALL_CHECKS:
        try:
            check_fn(cfg, report)
        except Exception as exc:
            report.error(
                check_fn.__name__,
                f"Unhandled exception: {exc}",
                detail=str(exc),
            )
    report.finalize(t0)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="FV-AUDIO structural self-check")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    report = run_all_checks()
    if args.json:
        print(report.to_json())
    else:
        report.print_text()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
