# > **Owner**: Chin, William Willy (`willychi`)
# THC Self-Check: Automated consistency verification for THC agent ecosystem
# Part of the THC Self-Improvement Framework
#
# Usage:
#   python thc_self_check.py                    # Full check, human-readable output
#   python thc_self_check.py --json             # JSON output for CI/CD
#   python thc_self_check.py --pre-commit       # Pre-commit mode (only staged files)
#   python thc_self_check.py --fix              # Auto-fix trivial issues
#
# Exit codes: 0 = all pass, 1 = issues found, 2 = error
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add tools directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thc_self_common import (
    find_repo_root,
    load_config,
    get_skill_path,
    read_skill,
    read_agent_def,
    find_pattern_in_file,
    count_lines,
    extract_cross_references,
    Finding,
    Report,
    setup_logging,
)

logger = setup_logging("thc_self_check")


# =============================================================================
# CHECK FUNCTIONS
# =============================================================================


def check_skill_files_exist(config: dict) -> list:
    """Check all expected SKILL.md files exist."""
    findings = []
    skills_cfg = config.get("skills", [])
    if isinstance(skills_cfg, list):
        expected_skills = skills_cfg
    elif isinstance(skills_cfg, dict):
        expected_skills = skills_cfg.get("expected_names", [])
    else:
        expected_skills = []
    if not expected_skills:
        expected_skills = [
            "registers",
            "hidspi",
            "hidi2c",
            "dma",
            "power",
            "driver",
            "platform",
            "debug",
            "wot",
        ]
    for skill_name in expected_skills:
        path = get_skill_path(skill_name)
        if path.exists():
            lines = count_lines(path)
            findings.append(
                Finding(
                    check="skill_exists",
                    target=f"fv-thc/{skill_name}",
                    status="PASS",
                    message=f"Exists ({lines} lines)",
                )
            )
        else:
            findings.append(
                Finding(
                    check="skill_exists",
                    target=f"fv-thc/{skill_name}",
                    status="FAIL",
                    message=f"MISSING: {path}",
                    severity="critical",
                )
            )
    return findings


def check_owner_headers(config: dict) -> list:
    """Check all skill files have the owner header."""
    findings = []
    owner_pattern = config.get("checks", {}).get("owner_pattern", "willychi")
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    # Check SKILL.md files
    for skill_dir in skill_base.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_file = skill_dir / "SKILL.md"
            content = skill_file.read_text(encoding="utf-8")
            # Check first 30 lines for owner (YAML frontmatter can push it down)
            first_lines = "\n".join(content.split("\n")[:30])
            if owner_pattern in first_lines:
                findings.append(
                    Finding(
                        check="owner_header",
                        target=str(skill_file.name),
                        status="PASS",
                        message=f"Owner header present in {skill_dir.name}/SKILL.md",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check="owner_header",
                        target=str(skill_file.name),
                        status="FAIL",
                        message=f"Missing owner header in {skill_dir.name}/SKILL.md",
                        severity="high",
                    )
                )

    # Check docs
    docs_dir = skill_base / "docs"
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            content = doc_file.read_text(encoding="utf-8")
            first_lines = "\n".join(content.split("\n")[:30])
            if owner_pattern in first_lines:
                findings.append(
                    Finding(
                        check="owner_header",
                        target=doc_file.name,
                        status="PASS",
                        message=f"Owner header present in docs/{doc_file.name}",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check="owner_header",
                        target=doc_file.name,
                        status="FAIL",
                        message=f"Missing owner header in docs/{doc_file.name}",
                        severity="medium",
                    )
                )

    # Check agent definition
    agent_file = root / ".opencode" / "agent" / "FV" / "FV-THC.md"
    if agent_file.exists():
        content = agent_file.read_text(encoding="utf-8")
        if owner_pattern in content[:500]:
            findings.append(
                Finding(
                    check="owner_header",
                    target="FV-THC.md",
                    status="PASS",
                    message="Owner header present in FV-THC.md",
                )
            )

    return findings


def check_subskill_count(config: dict) -> list:
    """Check sub-skill count consistency between FV-THC.md and actual files."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    # Count actual SKILL.md files
    actual_skills = []
    for skill_dir in skill_base.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            if skill_dir.name not in ("docs", "eval", "tools"):
                actual_skills.append(skill_dir.name)
    actual_count = len(actual_skills)

    # Check FV-THC.md references
    agent_content = read_agent_def()
    if agent_content:
        matches = re.findall(r"(\d+)\s+on-demand sub-skills", agent_content)
        for match in matches:
            claimed = int(match)
            if claimed == actual_count:
                findings.append(
                    Finding(
                        check="subskill_count",
                        target="FV-THC.md",
                        status="PASS",
                        message=f"Claims {claimed} sub-skills, found {actual_count}",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check="subskill_count",
                        target="FV-THC.md",
                        status="FAIL",
                        message=f"Claims {claimed} sub-skills but found {actual_count}: {sorted(actual_skills)}",
                        severity="high",
                    )
                )
    else:
        findings.append(
            Finding(
                check="subskill_count",
                target="FV-THC.md",
                status="SKIP",
                message="Could not read FV-THC.md",
            )
        )

    return findings


def check_cross_references(config: dict) -> list:
    """Check cross-references between skills are bidirectional."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    # Build cross-reference map
    xref_map = {}  # skill_name -> set of referenced skills
    skill_names = []

    for skill_dir in skill_base.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            if skill_dir.name not in ("docs", "eval", "tools"):
                skill_names.append(skill_dir.name)
                content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                refs = re.findall(r"`fv-thc/(\w+)`", content)
                # Remove self-references
                refs = [r for r in refs if r != skill_dir.name]
                xref_map[skill_dir.name] = set(refs)

    # Check bidirectionality for key relationships
    key_relationships = [
        ("power", "wot"),
        ("debug", "wot"),
        ("hidspi", "wot"),
        ("hidi2c", "wot"),
        ("driver", "wot"),
        ("platform", "wot"),
        ("power", "registers"),
        ("dma", "driver"),
        ("hidspi", "registers"),
        ("hidi2c", "registers"),
    ]

    for a, b in key_relationships:
        if a not in xref_map or b not in xref_map:
            continue
        a_refs_b = b in xref_map.get(a, set())
        b_refs_a = a in xref_map.get(b, set())

        if a_refs_b and b_refs_a:
            findings.append(
                Finding(
                    check="cross_reference",
                    target=f"{a} <-> {b}",
                    status="PASS",
                    message=f"Bidirectional: {a} <-> {b}",
                )
            )
        elif a_refs_b or b_refs_a:
            direction = f"{a} -> {b}" if a_refs_b else f"{b} -> {a}"
            missing = f"{b} -> {a}" if a_refs_b else f"{a} -> {b}"
            findings.append(
                Finding(
                    check="cross_reference",
                    target=f"{a} <-> {b}",
                    status="WARN",
                    message=f"One-way: {direction} exists, missing {missing}",
                    severity="low",
                )
            )
        else:
            findings.append(
                Finding(
                    check="cross_reference",
                    target=f"{a} <-> {b}",
                    status="WARN",
                    message=f"No cross-reference between {a} and {b}",
                    severity="low",
                )
            )

    return findings


def check_doc_files_exist(config: dict) -> list:
    """Check all expected documentation files exist."""
    findings = []
    root = find_repo_root()
    docs_dir = root / ".opencode" / "skill" / "fv-thc" / "docs"

    expected_docs = [
        "thc_has_4x_extraction.md",
        "thc_bwg_extraction.md",
        "thc_hidspi_hidi2c_kernel_study.md",
        "thc_known_issues.md",
        "thc_test_coverage_matrix.md",
        "thc_cheat_sheets.md",
        "thc_test_gap_analysis.md",
        "thc_windows_driver_diff.md",
        "thc_agent_workflows.md",
    ]

    for doc_name in expected_docs:
        path = docs_dir / doc_name
        if path.exists():
            size = path.stat().st_size
            findings.append(
                Finding(
                    check="doc_exists",
                    target=doc_name,
                    status="PASS",
                    message=f"Exists ({size:,} bytes)",
                )
            )
        else:
            findings.append(
                Finding(
                    check="doc_exists",
                    target=doc_name,
                    status="FAIL",
                    message=f"MISSING: {path}",
                    severity="medium",
                )
            )

    return findings


def check_eval_files(config: dict) -> list:
    """Check eval files exist and test count is consistent."""
    findings = []
    root = find_repo_root()
    eval_dir = root / ".opencode" / "skill" / "fv-thc" / "eval"

    # Check eval test definitions exist
    eval_file = eval_dir / "thc_skill_eval_tests.md"
    if eval_file.exists():
        content = eval_file.read_text(encoding="utf-8")
        test_ids = re.findall(r"### (\w+-\d+)", content)
        test_count = len(test_ids)

        # Check count matches FV-THC.md
        agent_content = read_agent_def()
        if agent_content:
            count_match = re.search(r"(\d+)\s+test cases", agent_content)
            if count_match:
                claimed = int(count_match.group(1))
                if claimed == test_count:
                    findings.append(
                        Finding(
                            check="eval_count",
                            target="thc_skill_eval_tests.md",
                            status="PASS",
                            message=f"Test count matches: {test_count}",
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            check="eval_count",
                            target="thc_skill_eval_tests.md",
                            status="FAIL",
                            message=f"FV-THC.md claims {claimed} tests but found {test_count}",
                            severity="medium",
                        )
                    )

        # Check category coverage
        categories = {}
        for tid in test_ids:
            cat = tid.rsplit("-", 1)[0]
            categories[cat] = categories.get(cat, 0) + 1

        findings.append(
            Finding(
                check="eval_coverage",
                target="thc_skill_eval_tests.md",
                status="PASS",
                message=f"{test_count} tests across {len(categories)} categories: {dict(categories)}",
            )
        )
    else:
        findings.append(
            Finding(
                check="eval_count",
                target="thc_skill_eval_tests.md",
                status="FAIL",
                message="Eval test file missing",
                severity="high",
            )
        )

    return findings


def check_stale_references(config: dict) -> list:
    """Check for stale/outdated references in skill files."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    stale_patterns = [
        (r"8\s+on-demand sub-skills", "Stale sub-skill count (should be 9)"),
        (r"8\s+sub-skills", "Stale sub-skill count (should be 9)"),
        (r"0x128\s*MHz", "Wrong SPI clock (should be 125 MHz) [DOC-001]"),
        (r"PIO.*opcode.*0x2\b", "Wrong PIO opcode (Read=0x4, Write=0x6) [DOC-003]"),
        (
            r"0x5749|0x574B|0x5748|0x574A",
            "Stale WCL Device IDs (should be 0x4D49/0x4D4B/0x4D48/0x4D4A)",
        ),
    ]

    for skill_dir in skill_base.iterdir():
        skill_file = skill_dir / "SKILL.md" if skill_dir.is_dir() else None
        if not skill_file or not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8")
        for pattern, description in stale_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                lines = []
                for m in matches:
                    line_num = content[: m.start()].count("\n") + 1
                    lines.append(line_num)
                findings.append(
                    Finding(
                        check="stale_reference",
                        target=f"{skill_dir.name}/SKILL.md",
                        status="FAIL",
                        message=f"{description} at line(s) {lines}",
                        severity="high",
                    )
                )

    # Check agent definition too
    agent_content = read_agent_def()
    if agent_content:
        for pattern, description in stale_patterns:
            if re.search(pattern, agent_content, re.IGNORECASE):
                findings.append(
                    Finding(
                        check="stale_reference",
                        target="FV-THC.md",
                        status="FAIL",
                        message=description,
                        severity="high",
                    )
                )

    if not any(f.status == "FAIL" for f in findings):
        findings.append(
            Finding(
                check="stale_reference",
                target="all_files",
                status="PASS",
                message="No stale references found",
            )
        )

    return findings


def check_frontmatter(config: dict) -> list:
    """Check SKILL.md files have valid YAML frontmatter."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    for skill_dir in skill_base.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        if skill_dir.name in ("docs", "eval", "tools"):
            continue

        content = skill_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Check frontmatter
        if lines[0].strip() == "---":
            # Find closing ---
            end_idx = None
            for i in range(1, min(10, len(lines))):
                if lines[i].strip() == "---":
                    end_idx = i
                    break

            if end_idx:
                frontmatter = "\n".join(lines[1:end_idx])
                has_name = "name:" in frontmatter
                has_desc = "description:" in frontmatter

                if has_name and has_desc:
                    # Extract name and verify it matches directory
                    name_match = re.search(r"name:\s*(.+)", frontmatter)
                    if name_match:
                        fm_name = name_match.group(1).strip().strip('"').strip("'")
                        expected = f"fv-thc/{skill_dir.name}"
                        if fm_name == expected:
                            findings.append(
                                Finding(
                                    check="frontmatter",
                                    target=f"{skill_dir.name}/SKILL.md",
                                    status="PASS",
                                    message=f"Valid frontmatter: name={fm_name}",
                                )
                            )
                        else:
                            findings.append(
                                Finding(
                                    check="frontmatter",
                                    target=f"{skill_dir.name}/SKILL.md",
                                    status="FAIL",
                                    message=f"Name mismatch: frontmatter says '{fm_name}', expected '{expected}'",
                                    severity="high",
                                )
                            )
                else:
                    missing = []
                    if not has_name:
                        missing.append("name")
                    if not has_desc:
                        missing.append("description")
                    findings.append(
                        Finding(
                            check="frontmatter",
                            target=f"{skill_dir.name}/SKILL.md",
                            status="FAIL",
                            message=f"Missing frontmatter fields: {missing}",
                            severity="high",
                        )
                    )
            else:
                findings.append(
                    Finding(
                        check="frontmatter",
                        target=f"{skill_dir.name}/SKILL.md",
                        status="FAIL",
                        message="Unclosed frontmatter block",
                        severity="high",
                    )
                )
        else:
            findings.append(
                Finding(
                    check="frontmatter",
                    target=f"{skill_dir.name}/SKILL.md",
                    status="FAIL",
                    message="No frontmatter found (must start with ---)",
                    severity="high",
                )
            )

    return findings


def check_delegation_table(config: dict) -> list:
    """Check FV-THC.md delegation table matches actual skills."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    # Get actual skills
    actual_skills = set()
    for skill_dir in skill_base.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            if skill_dir.name not in ("docs", "eval", "tools"):
                actual_skills.add(skill_dir.name)

    # Get skills mentioned in delegation table
    agent_content = read_agent_def()
    if not agent_content:
        findings.append(
            Finding(
                check="delegation_table",
                target="FV-THC.md",
                status="SKIP",
                message="Could not read FV-THC.md",
            )
        )
        return findings

    # Find delegation table skills
    delegated_skills = set(re.findall(r"`fv-thc/(\w+)`", agent_content))

    # Check for skills in files but not in delegation table
    missing_from_table = actual_skills - delegated_skills
    for s in missing_from_table:
        findings.append(
            Finding(
                check="delegation_table",
                target=f"fv-thc/{s}",
                status="FAIL",
                message=f"Skill '{s}' exists but NOT in FV-THC.md delegation table",
                severity="high",
            )
        )

    # Check for skills in table but not in files
    missing_from_files = delegated_skills - actual_skills
    for s in missing_from_files:
        findings.append(
            Finding(
                check="delegation_table",
                target=f"fv-thc/{s}",
                status="WARN",
                message=f"Skill '{s}' in delegation table but no SKILL.md found",
                severity="medium",
            )
        )

    if not missing_from_table and not missing_from_files:
        findings.append(
            Finding(
                check="delegation_table",
                target="FV-THC.md",
                status="PASS",
                message=f"All {len(actual_skills)} skills present in delegation table",
            )
        )

    return findings


def check_version_consistency(config: dict) -> list:
    """Check version references are consistent."""
    findings = []
    agent_content = read_agent_def()
    if not agent_content:
        return findings

    # Extract version from agent def
    ver_match = re.search(r"rev(\d+\.\d+)", agent_content[:500])
    if ver_match:
        version = ver_match.group(0)
        # Check it appears in Last Updated line too
        updated_match = re.search(r"Last Updated.*?(rev\d+\.\d+)", agent_content[:500])
        if updated_match:
            if updated_match.group(1) == version:
                findings.append(
                    Finding(
                        check="version",
                        target="FV-THC.md",
                        status="PASS",
                        message=f"Version consistent: {version}",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check="version",
                        target="FV-THC.md",
                        status="FAIL",
                        message=f"Version mismatch: header={version}, Last Updated={updated_match.group(1)}",
                        severity="medium",
                    )
                )

    return findings


def check_delegation_consistency(config: dict) -> list:
    """Comprehensive 6-location delegation consistency check.

    Delegates to thc_delegation_check.py which cross-checks:
      L1: On-disk SKILL.md files
      L2: FV-THC.md SUB-SKILL DELEGATION table
      L3: FV-THC.md sub-skill count claims
      L4: self_improvement_config.json skills[] array
      L5: self_improvement_config.json expected_skill_count
      L6: FV-THC.md sub-agent/skill delegation tables
    Plus repo diff detection for uncommitted delegation changes.
    """
    try:
        from thc_delegation_check import run_all_checks as run_delegation_checks

        report = run_delegation_checks(config)
        return report.findings
    except ImportError as e:
        return [
            Finding(
                check="delegation_consistency",
                target="thc_delegation_check.py",
                status="ERROR",
                message=f"Cannot import thc_delegation_check: {e}",
                severity="high",
            )
        ]
    except Exception as e:
        return [
            Finding(
                check="delegation_consistency",
                target="thc_delegation_check.py",
                status="ERROR",
                message=f"Delegation check failed: {e}",
                severity="medium",
            )
        ]


# =============================================================================
# MAIN
# =============================================================================

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
    ("delegation_consistency", check_delegation_consistency),
]


def run_all_checks(config: dict = None, checks: list = None) -> Report:
    """Run all checks and return a Report."""
    if config is None:
        config = load_config()
    report = Report(name="THC Self-Check", version="1.0.0")

    checks_to_run = checks or ALL_CHECKS
    for check_name, check_fn in checks_to_run:
        logger.info(f"Running check: {check_name}")
        try:
            findings = check_fn(config)
            report.findings.extend(findings)
        except Exception as e:
            report.findings.append(
                Finding(
                    check=check_name,
                    target="system",
                    status="ERROR",
                    message=f"Check failed: {e}",
                    severity="critical",
                )
            )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="THC Self-Check: Consistency verification"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="Pre-commit mode (only critical checks)",
    )
    parser.add_argument("--save", type=str, help="Save report to file")
    parser.add_argument("--check", type=str, nargs="+", help="Run specific checks only")
    args = parser.parse_args()

    config = load_config()

    # Select checks
    if args.pre_commit:
        selected = [
            c
            for c in ALL_CHECKS
            if c[0]
            in (
                "skill_files_exist",
                "owner_headers",
                "subskill_count",
                "stale_references",
                "frontmatter",
            )
        ]
    elif args.check:
        selected = [c for c in ALL_CHECKS if c[0] in args.check]
    else:
        selected = ALL_CHECKS

    report = run_all_checks(config, selected)

    # Output
    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    # Save if requested
    if args.save:
        report.save(args.save)
        logger.info(f"Report saved to {args.save}")

    # Exit code
    has_critical = any(
        f.status == "FAIL" and f.severity in ("critical", "high")
        for f in report.findings
    )
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
