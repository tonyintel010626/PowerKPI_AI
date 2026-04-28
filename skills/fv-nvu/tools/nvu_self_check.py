#!/usr/bin/env python3
"""NVU Self-Check — structural integrity checks for the FV-NVU skill tree.

Validates file existence, owner headers, sub-skill counts, cross-references,
documentation, eval files, stale references, frontmatter, delegation tables,
and version consistency.

Usage:
    python nvu_self_check.py [--json] [--pre-commit] [--save] [--check CHECK_NAME]
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from nvu_self_common import (
    Finding,
    Report,
    extract_cross_references,
    find_pattern_in_file,
    load_config,
    read_agent_def,
    read_skill,
    setup_logging,
)

logger = logging.getLogger("nvu_self_check")

# ── NVU skill list ──────────────────────────────────────────────────────────
NVU_SKILLS = [
    "registers",
    "inference",
    "dma",
    "power",
    "driver",
    "platform",
    "debug",
    "camera",
    "firmware",
    "bios",
]

# ── Key bidirectional relationships ─────────────────────────────────────────
KEY_RELATIONSHIPS = [
    ("camera", "driver"),
    ("firmware", "driver"),
    ("inference", "dma"),
    ("power", "platform"),
    ("firmware", "registers"),
    ("debug", "registers"),
    ("bios", "platform"),
    ("bios", "power"),
    ("camera", "platform"),
]

# ── NVU stale patterns ─────────────────────────────────────────────────────
DEFAULT_STALE_PATTERNS = [
    r"<!-- TODO -->",
    r"TBD -- not in HAS",
    r"TBD -- pending",
    r"PLACEHOLDER",
    r"FIXME",
    r"XXX\b",
]


# ═══════════════════════════════════════════════════════════════════════════
#  Individual Checks
# ═══════════════════════════════════════════════════════════════════════════


def check_skill_files_exist(config: dict) -> list:
    """Check that SKILL.md exists for every configured sub-skill."""
    findings = []
    skill_base = Path(config["paths"]["skill_base"])
    repo_root = Path(config.get("_repo_root", "."))
    base = repo_root / skill_base

    for skill_name in config.get("skills", NVU_SKILLS):
        skill_file = base / skill_name / "SKILL.md"
        if skill_file.exists():
            findings.append(
                Finding(
                    check="skill_files_exist",
                    target=str(skill_file.relative_to(repo_root)),
                    status="PASS",
                    message=f"SKILL.md exists for '{skill_name}'",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="skill_files_exist",
                    target=str(skill_file.relative_to(repo_root)),
                    status="FAIL",
                    message=f"SKILL.md missing for '{skill_name}'",
                    severity="high",
                )
            )

    # Also check parent SKILL.md
    parent_skill = base / "SKILL.md"
    if parent_skill.exists():
        findings.append(
            Finding(
                check="skill_files_exist",
                target=str(parent_skill.relative_to(repo_root)),
                status="PASS",
                message="Parent SKILL.md exists",
                severity="info",
            )
        )
    else:
        findings.append(
            Finding(
                check="skill_files_exist",
                target=str(parent_skill.relative_to(repo_root)),
                status="FAIL",
                message="Parent SKILL.md missing",
                severity="high",
            )
        )

    return findings


def check_owner_headers(config: dict) -> list:
    """Check that skill files contain owner/co-owner identification."""
    findings = []
    skill_base = Path(config["paths"]["skill_base"])
    repo_root = Path(config.get("_repo_root", "."))
    base = repo_root / skill_base

    owner_tag = config.get("self_check", {}).get("owner_tag", "willychi")
    owner_pattern = re.compile(
        rf"(?:Owner|Maintainer|Lead|Co-owner).*{re.escape(owner_tag)}",
        re.IGNORECASE,
    )

    # Check all skill files
    for skill_name in config.get("skills", NVU_SKILLS):
        skill_file = base / skill_name / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8", errors="replace")
        # Check first 30 lines
        first_lines = "\n".join(content.splitlines()[:30])
        if owner_pattern.search(first_lines):
            findings.append(
                Finding(
                    check="owner_headers",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="PASS",
                    message=f"Owner tag '{owner_tag}' found in header",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="owner_headers",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="WARN",
                    message=f"Owner tag '{owner_tag}' not found in first 30 lines",
                    severity="low",
                )
            )

    # Check agent definition
    agent_def_name = config["paths"].get("agent_def", "FV-NVU.md")
    agent_file = repo_root / ".opencode" / "agent" / "FV" / agent_def_name
    if agent_file.exists():
        content = agent_file.read_text(encoding="utf-8", errors="replace")
        first_lines = "\n".join(content.splitlines()[:30])
        if owner_pattern.search(first_lines):
            findings.append(
                Finding(
                    check="owner_headers",
                    target=agent_def_name,
                    status="PASS",
                    message=f"Owner tag '{owner_tag}' found in agent def",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="owner_headers",
                    target=agent_def_name,
                    status="WARN",
                    message=f"Owner tag '{owner_tag}' not found in agent def header",
                    severity="low",
                )
            )

    return findings


def check_subskill_count(config: dict) -> list:
    """Check that the agent definition's stated sub-skill count matches reality."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    # Count actual sub-skill directories (those with SKILL.md)
    actual_skills = []
    if skill_base.exists():
        for d in sorted(skill_base.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                actual_skills.append(d.name)

    expected_count = config.get("self_check", {}).get("expected_count", 10)

    if len(actual_skills) == expected_count:
        findings.append(
            Finding(
                check="subskill_count",
                target="fv-nvu",
                status="PASS",
                message=f"Sub-skill count matches: {len(actual_skills)} actual = {expected_count} expected",
                severity="info",
                details=json.dumps({"actual_skills": actual_skills}),
            )
        )
    else:
        findings.append(
            Finding(
                check="subskill_count",
                target="fv-nvu",
                status="WARN",
                message=f"Sub-skill count mismatch: {len(actual_skills)} actual vs {expected_count} expected",
                severity="medium",
                details=json.dumps(
                    {"actual_skills": actual_skills, "expected": expected_count}
                ),
            )
        )

    # Also check agent definition for stated count
    agent_def_name = config["paths"].get("agent_def", "FV-NVU.md")
    agent_file = repo_root / ".opencode" / "agent" / "FV" / agent_def_name
    if agent_file.exists():
        content = agent_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            r"(\d+)\s+(?:on-demand\s+)?sub-skills?", content, re.IGNORECASE
        )
        if match:
            stated = int(match.group(1))
            if stated == len(actual_skills):
                findings.append(
                    Finding(
                        check="subskill_count",
                        target=agent_def_name,
                        status="PASS",
                        message=f"Agent def states {stated} sub-skills, matches actual",
                        severity="info",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check="subskill_count",
                        target=agent_def_name,
                        status="WARN",
                        message=f"Agent def states {stated} sub-skills but {len(actual_skills)} exist",
                        severity="medium",
                    )
                )

    return findings


def check_cross_references(config: dict) -> list:
    """Check cross-reference consistency between skills."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    # Build cross-reference map: {skill_name: set of referenced skills}
    xref_map = {}
    for skill_name in config.get("skills", NVU_SKILLS):
        skill_data = read_skill(skill_name, config)
        skill_content = skill_data.get("skill") or ""
        if skill_content:
            refs = extract_cross_references(skill_content)
            xref_map[skill_name] = set(refs)
        else:
            xref_map[skill_name] = set()

    # Check bidirectional references for key relationships
    for skill_a, skill_b in KEY_RELATIONSHIPS:
        a_refs_b = skill_b in xref_map.get(skill_a, set())
        b_refs_a = skill_a in xref_map.get(skill_b, set())

        if a_refs_b and b_refs_a:
            findings.append(
                Finding(
                    check="cross_references",
                    target=f"{skill_a} <-> {skill_b}",
                    status="PASS",
                    message=f"Bidirectional reference OK: {skill_a} <-> {skill_b}",
                    severity="info",
                )
            )
        elif a_refs_b or b_refs_a:
            direction = f"{skill_a}->{skill_b}" if a_refs_b else f"{skill_b}->{skill_a}"
            missing = f"{skill_b}->{skill_a}" if a_refs_b else f"{skill_a}->{skill_b}"
            findings.append(
                Finding(
                    check="cross_references",
                    target=f"{skill_a} <-> {skill_b}",
                    status="WARN",
                    message=f"Unidirectional reference: {direction} exists but {missing} missing",
                    severity="low",
                )
            )
        else:
            findings.append(
                Finding(
                    check="cross_references",
                    target=f"{skill_a} <-> {skill_b}",
                    status="WARN",
                    message=f"No cross-references between {skill_a} and {skill_b}",
                    severity="medium",
                )
            )

    return findings


def check_doc_files_exist(config: dict) -> list:
    """Check that expected documentation files exist."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    expected_docs = config.get("docs", [])
    if not expected_docs:
        findings.append(
            Finding(
                check="doc_files_exist",
                target="fv-nvu/docs",
                status="WARN",
                message="No expected docs configured — docs list is empty",
                severity="low",
            )
        )
        return findings

    for doc_entry in expected_docs:
        doc_name = (
            doc_entry if isinstance(doc_entry, str) else doc_entry.get("file", "")
        )
        # Check in eval/, tools/, and docs/ directories
        found = False
        for subdir in ["eval", "tools", "docs"]:
            if (skill_base / subdir / doc_name).exists():
                found = True
                findings.append(
                    Finding(
                        check="doc_files_exist",
                        target=f"fv-nvu/{subdir}/{doc_name}",
                        status="PASS",
                        message=f"Doc file '{doc_name}' found in {subdir}/",
                        severity="info",
                    )
                )
                break

        if not found:
            findings.append(
                Finding(
                    check="doc_files_exist",
                    target=f"fv-nvu/docs/{doc_name}",
                    status="WARN",
                    message=f"Doc file '{doc_name}' not found in eval/, tools/, or docs/",
                    severity="low",
                )
            )

    return findings


def check_eval_files(config: dict) -> list:
    """Check that eval test files exist and have expected test count."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    # Check eval test file
    eval_dir = skill_base / "eval"
    eval_file = eval_dir / "nvu_skill_eval_tests.md"
    if eval_file.exists():
        content = eval_file.read_text(encoding="utf-8", errors="replace")
        # Count test entries (lines starting with | that have test IDs)
        test_lines = [
            line for line in content.splitlines() if re.match(r"\|\s*NVU[-_]", line)
        ]
        findings.append(
            Finding(
                check="eval_files",
                target="eval/nvu_skill_eval_tests.md",
                status="PASS",
                message=f"Eval test file exists with {len(test_lines)} test entries",
                severity="info",
                details=json.dumps({"test_count": len(test_lines)}),
            )
        )
    else:
        findings.append(
            Finding(
                check="eval_files",
                target="eval/nvu_skill_eval_tests.md",
                status="WARN",
                message="Eval test file not found",
                severity="medium",
            )
        )

    # Check validators
    validators = list(eval_dir.glob("validate_*.py")) if eval_dir.exists() else []
    if validators:
        findings.append(
            Finding(
                check="eval_files",
                target="eval/",
                status="PASS",
                message=f"Found {len(validators)} validator(s): {[v.name for v in validators]}",
                severity="info",
            )
        )
    else:
        findings.append(
            Finding(
                check="eval_files",
                target="eval/",
                status="WARN",
                message="No validator scripts (validate_*.py) found in eval/",
                severity="medium",
            )
        )

    return findings


def check_stale_references(config: dict) -> list:
    """Check for stale/placeholder patterns in skill files."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    stale_patterns = config.get("self_check", {}).get(
        "stale_patterns", DEFAULT_STALE_PATTERNS
    )

    for skill_name in config.get("skills", NVU_SKILLS):
        skill_file = skill_base / skill_name / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8", errors="replace")
        stale_found = []

        for pat_entry in stale_patterns:
            # Support both string patterns and dict {pattern, description, severity}
            if isinstance(pat_entry, dict):
                pattern = pat_entry.get("pattern", "")
            else:
                pattern = str(pat_entry)
            if not pattern:
                continue
            matches = re.findall(re.escape(pattern), content, re.IGNORECASE)
            if matches:
                stale_found.append((pattern, len(matches)))

        if stale_found:
            total = sum(c for _, c in stale_found)
            details = {p: c for p, c in stale_found}
            findings.append(
                Finding(
                    check="stale_references",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="WARN",
                    message=f"{total} stale/placeholder pattern(s) found",
                    severity="low",
                    details=json.dumps(details),
                )
            )
        else:
            findings.append(
                Finding(
                    check="stale_references",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="PASS",
                    message="No stale patterns found",
                    severity="info",
                )
            )

    return findings


def check_frontmatter(config: dict) -> list:
    """Check that skill files have proper metadata in their headers."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))
    skill_base = repo_root / Path(config["paths"]["skill_base"])

    for skill_name in config.get("skills", NVU_SKILLS):
        skill_file = skill_base / skill_name / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8", errors="replace")
        first_50 = "\n".join(content.splitlines()[:50])

        # Check for a title (# heading)
        has_title = bool(re.search(r"^#\s+.+", first_50, re.MULTILINE))
        # Check for description/overview section
        has_desc = bool(
            re.search(
                r"(?:overview|description|introduction|purpose)",
                first_50,
                re.IGNORECASE,
            )
        )
        # Check for version/revision
        has_version = bool(re.search(r"(?:rev|version|v\d)", first_50, re.IGNORECASE))

        issues = []
        if not has_title:
            issues.append("missing title heading")
        if not has_desc:
            issues.append("missing overview/description")
        if not has_version:
            issues.append("missing version/revision")

        if not issues:
            findings.append(
                Finding(
                    check="frontmatter",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="PASS",
                    message="Frontmatter OK (title, description, version present)",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="frontmatter",
                    target=f"fv-nvu/{skill_name}/SKILL.md",
                    status="WARN",
                    message=f"Frontmatter issues: {', '.join(issues)}",
                    severity="low",
                )
            )

    return findings


def check_delegation_table(config: dict) -> list:
    """Check that agent definition's delegation table matches actual skills."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))

    agent_content = read_agent_def(config)
    if not agent_content:
        findings.append(
            Finding(
                check="delegation_table",
                target="FV-NVU.md",
                status="ERROR",
                message="Cannot read agent definition",
                severity="high",
            )
        )
        return findings

    # Extract `fv-nvu/<name>` references from agent def
    refs = extract_cross_references(agent_content)
    actual_skills = set(config.get("skills", NVU_SKILLS))

    # Check that all actual skills are referenced in agent def
    for skill_name in actual_skills:
        if skill_name in refs:
            findings.append(
                Finding(
                    check="delegation_table",
                    target=f"FV-NVU.md -> fv-nvu/{skill_name}",
                    status="PASS",
                    message=f"Skill '{skill_name}' referenced in agent definition",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="delegation_table",
                    target=f"FV-NVU.md -> fv-nvu/{skill_name}",
                    status="WARN",
                    message=f"Skill '{skill_name}' not referenced in agent definition delegation table",
                    severity="medium",
                )
            )

    # Check for references to non-existent skills
    for ref_name in refs:
        if ref_name not in actual_skills:
            findings.append(
                Finding(
                    check="delegation_table",
                    target=f"FV-NVU.md -> fv-nvu/{ref_name}",
                    status="WARN",
                    message=f"Agent def references 'fv-nvu/{ref_name}' but no such skill directory exists",
                    severity="low",
                )
            )

    return findings


def check_version_consistency(config: dict) -> list:
    """Check that version strings are consistent across agent def and skills."""
    findings = []
    repo_root = Path(config.get("_repo_root", "."))

    agent_content = read_agent_def(config)
    if not agent_content:
        findings.append(
            Finding(
                check="version_consistency",
                target="FV-NVU.md",
                status="ERROR",
                message="Cannot read agent definition",
                severity="high",
            )
        )
        return findings

    # Extract version from agent def header
    version_pattern = re.compile(r"\(rev([\d.]+)\)", re.IGNORECASE)
    agent_versions = version_pattern.findall(agent_content)

    if agent_versions:
        # Check that all version references are the same
        unique_versions = set(agent_versions)
        if len(unique_versions) == 1:
            findings.append(
                Finding(
                    check="version_consistency",
                    target="FV-NVU.md",
                    status="PASS",
                    message=f"Agent definition version consistent: rev{agent_versions[0]}",
                    severity="info",
                )
            )
        else:
            findings.append(
                Finding(
                    check="version_consistency",
                    target="FV-NVU.md",
                    status="WARN",
                    message=f"Multiple versions in agent def: {sorted(unique_versions)}",
                    severity="medium",
                )
            )
    else:
        findings.append(
            Finding(
                check="version_consistency",
                target="FV-NVU.md",
                status="WARN",
                message="No version string found in agent definition",
                severity="low",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════════
#  Check Registry
# ═══════════════════════════════════════════════════════════════════════════

ALL_CHECKS = [
    ("skill_files_exist", check_skill_files_exist),
    ("owner_headers", check_owner_headers),
    ("subskill_count", check_subskill_count),
    ("cross_references", check_cross_references),
    ("doc_files_exist", check_doc_files_exist),
    ("eval_files", check_eval_files),
    ("stale_references", check_stale_references),
    ("frontmatter", check_frontmatter),
    ("delegation_table", check_delegation_table),
    ("version_consistency", check_version_consistency),
]


def run_all_checks(config: dict, checks: list | None = None) -> Report:
    """Run all (or specified) structural checks and return a Report."""
    report = Report(name="NVU Self-Check")

    for check_name, check_fn in ALL_CHECKS:
        if checks and check_name not in checks:
            continue

        logger.info("Running check: %s", check_name)
        try:
            findings = check_fn(config)
            report.findings.extend(findings)
        except Exception as e:
            logger.error("Check '%s' raised exception: %s", check_name, e)
            report.findings.append(
                Finding(
                    check=check_name,
                    target="<exception>",
                    status="ERROR",
                    message=str(e),
                    severity="high",
                )
            )

    return report


# ═══════════════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="NVU Self-Check — structural integrity checks"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="Run in pre-commit mode (exit 1 on FAIL)",
    )
    parser.add_argument("--save", type=str, metavar="PATH", help="Save report to file")
    parser.add_argument(
        "--check", type=str, action="append", help="Run only specified check(s)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Suppress logging to stderr when --json to keep stdout clean for JSON parsing
    if args.json:
        setup_logging("WARNING")
    else:
        setup_logging("DEBUG" if args.verbose else "INFO")
    config = load_config()

    report = run_all_checks(config, checks=args.check)

    if args.save:
        report.save(Path(args.save), fmt="json" if args.json else "text")
        logger.info("Report saved to %s", args.save)

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    summary = report.compute_summary()
    if args.pre_commit and report.has_failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
