#!/usr/bin/env python3
"""THC Delegation Consistency Checker.

Cross-checks 6 locations where THC sub-skill and delegation information
is declared, and detects repo changes that may require delegation updates.

Locations checked:
  L1: On-disk SKILL.md files under fv-thc/*/SKILL.md
  L2: FV-THC.md SUB-SKILL DELEGATION table
  L3: FV-THC.md sub-skill count claims ("N on-demand sub-skills")
  L4: self_improvement_config.json skills[] array
  L5: self_improvement_config.json self_check.expected_skill_count
  L6: FV-THC.md Sub-Agent Delegation tables (cross-agent references)

Checks:
  1. disk_vs_table       — L1 <-> L2 (disk skills must appear in delegation table)
  2. disk_vs_config      — L1 <-> L4 (disk skills must match config skills[])
  3. count_consistency   — L1 count == L3 claims == L5 config count
  4. table_completeness  — L2 entries must have non-empty 'When to Load' guidance
  5. subagent_warnings   — L6 sub-agent refs flagged with availability warnings
  6. config_stale_count  — L4 length vs L5 expected_skill_count
  7. repo_diff           — git diff to detect uncommitted delegation-relevant changes

Usage:
  python thc_delegation_check.py [--json] [--save] [--verbose]
  python thc_delegation_check.py --check disk_vs_table
  python thc_delegation_check.py --fix-counts   # auto-fix count mismatches
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import shared utilities (same pattern as thc_self_check.py)
# ---------------------------------------------------------------------------
try:
    from thc_self_common import (
        Finding,
        Report,
        find_repo_root,
        load_config,
        read_agent_def,
        resolve_path,
        setup_logging,
        read_file,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from thc_self_common import (
        Finding,
        Report,
        find_repo_root,
        load_config,
        read_agent_def,
        resolve_path,
        setup_logging,
        read_file,
    )

CHECK_NAME = "delegation_consistency"
VERSION = "1.0.0"

# Directories under fv-thc/ that are NOT sub-skills
NON_SKILL_DIRS = {"docs", "eval", "tools", "reports", "archive", "__pycache__"}

logger = logging.getLogger(__name__)

# ===========================================================================
# Location scanners — one per location
# ===========================================================================


def scan_disk_skills(config: dict) -> set:
    """L1: Scan on-disk SKILL.md files under fv-thc/*/SKILL.md."""
    skill_base = resolve_path(config["paths"]["skill_base"])
    skills = set()
    if skill_base.is_dir():
        for child in sorted(skill_base.iterdir()):
            if child.is_dir() and child.name not in NON_SKILL_DIRS:
                if (child / "SKILL.md").exists():
                    skills.add(child.name)
    logger.debug("L1 disk skills: %s", sorted(skills))
    return skills


def scan_delegation_table(agent_text: str) -> set:
    """L2: Parse SUB-SKILL DELEGATION table rows from FV-THC.md.

    Matches rows like:  | ... | `fv-thc/registers` | ... |
    """
    pattern = r"\|\s*`fv-thc/([\w-]+)`\s*\|"
    skills = set(re.findall(pattern, agent_text))
    logger.debug("L2 delegation table skills: %s", sorted(skills))
    return skills


def scan_count_claims(agent_text: str) -> list:
    """L3: Find all 'N on-demand sub-skills' claims in FV-THC.md."""
    pattern = r"(\d+)\s+on-demand sub-skills?"
    counts = [int(n) for n in re.findall(pattern, agent_text)]
    logger.debug("L3 count claims: %s", counts)
    return counts


def scan_config_skills(config: dict) -> set:
    """L4: Read skills[] array from self_improvement_config.json."""
    skills = set(config.get("skills", []))
    logger.debug("L4 config skills[]: %s", sorted(skills))
    return skills


def scan_config_expected_count(config: dict):
    """L5: Read self_check.expected_skill_count from config."""
    count = config.get("self_check", {}).get("expected_skill_count", None)
    logger.debug("L5 config expected_skill_count: %s", count)
    return count


def scan_delegation_table_rows(agent_text: str) -> list:
    """L2 detail: Parse full delegation table rows (domain, skill, when)."""
    pattern = r"\|\s*([^|]+?)\s*\|\s*`fv-thc/([\w-]+)`\s*\|\s*([^|]*?)\s*\|"
    rows = re.findall(pattern, agent_text)
    logger.debug("L2 detail: %d rows parsed", len(rows))
    return rows


def scan_subagent_warnings(agent_text: str) -> list:
    r"""L6: Find sub-agent references flagged with \u26a0\ufe0f warnings."""
    # Pattern: AgentName ⚠️  (in table cells or text)
    pattern = r"([\w][\w/-]*?)\s*\u26a0\ufe0f"
    warned = re.findall(pattern, agent_text)
    logger.debug("L6 warned agents: %s", warned)
    return warned


# ===========================================================================
# Consistency checks — each returns list[Finding]
# ===========================================================================


def check_disk_vs_table(config: dict) -> list:
    """Check 1 — L1 <-> L2: disk skills match delegation table."""
    findings = []
    agent_text = read_agent_def(config)
    disk_skills = scan_disk_skills(config)
    table_skills = scan_delegation_table(agent_text)

    only_disk = disk_skills - table_skills
    only_table = table_skills - disk_skills

    for s in sorted(only_disk):
        findings.append(
            Finding(
                check=CHECK_NAME,
                target=f"fv-thc/{s}",
                status="FAIL",
                severity="HIGH",
                message=f"Skill 'fv-thc/{s}' exists on disk but NOT in SUB-SKILL DELEGATION table",
                details="Add a row to the SUB-SKILL DELEGATION table in FV-THC.md",
            )
        )
    for s in sorted(only_table):
        findings.append(
            Finding(
                check=CHECK_NAME,
                target=f"fv-thc/{s}",
                status="FAIL",
                severity="HIGH",
                message=f"Skill 'fv-thc/{s}' in delegation table but MISSING from disk",
                details="Remove from delegation table or create fv-thc/{}/SKILL.md".format(
                    s
                ),
            )
        )
    if not only_disk and not only_table:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L1<->L2",
                status="PASS",
                message=f"Disk skills ({len(disk_skills)}) match delegation table perfectly",
            )
        )
    return findings


def check_disk_vs_config(config: dict) -> list:
    """Check 2 — L1 <-> L4: disk skills match config skills[] array."""
    findings = []
    disk_skills = scan_disk_skills(config)
    config_skills = scan_config_skills(config)

    only_disk = disk_skills - config_skills
    only_config = config_skills - disk_skills

    for s in sorted(only_disk):
        findings.append(
            Finding(
                check=CHECK_NAME,
                target=f"config:skills/{s}",
                status="FAIL",
                severity="HIGH",
                message=f"Skill '{s}' exists on disk but NOT in config skills[] array",
                details="Add '{}' to self_improvement_config.json skills[]".format(s),
            )
        )
    for s in sorted(only_config):
        findings.append(
            Finding(
                check=CHECK_NAME,
                target=f"config:skills/{s}",
                status="FAIL",
                severity="MEDIUM",
                message=f"Skill '{s}' in config skills[] but MISSING from disk",
                details="Remove '{}' from config or create the sub-skill directory".format(
                    s
                ),
            )
        )
    if not only_disk and not only_config:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L1<->L4",
                status="PASS",
                message=f"Disk skills ({len(disk_skills)}) match config skills[] perfectly",
            )
        )
    return findings


def check_count_consistency(config: dict) -> list:
    """Check 3 — L1 count == L3 claims == L5 expected_skill_count."""
    findings = []
    agent_text = read_agent_def(config)
    disk_count = len(scan_disk_skills(config))
    count_claims = scan_count_claims(agent_text)
    config_count = scan_config_expected_count(config)

    # L3: count claims in FV-THC.md
    if count_claims:
        for claimed in count_claims:
            if claimed != disk_count:
                findings.append(
                    Finding(
                        check=CHECK_NAME,
                        target="L1<->L3",
                        status="FAIL",
                        severity="HIGH",
                        message=(
                            f"FV-THC.md claims '{claimed} on-demand sub-skills' "
                            f"but disk has {disk_count}"
                        ),
                        details=f"Update all occurrences of '{claimed} on-demand sub-skills' "
                        f"to '{disk_count} on-demand sub-skills' in FV-THC.md",
                    )
                )
            else:
                findings.append(
                    Finding(
                        check=CHECK_NAME,
                        target="L1<->L3",
                        status="PASS",
                        message=f"Count claim ({claimed}) matches disk ({disk_count})",
                    )
                )
    else:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L3",
                status="WARN",
                severity="LOW",
                message="No 'N on-demand sub-skills' claim found in FV-THC.md",
            )
        )

    # L5: config expected_skill_count
    if config_count is not None:
        if config_count != disk_count:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="L1<->L5",
                    status="FAIL",
                    severity="MEDIUM",
                    message=(
                        f"Config expected_skill_count={config_count} "
                        f"but disk has {disk_count}"
                    ),
                    details=(
                        f"Update self_check.expected_skill_count in "
                        f"self_improvement_config.json from {config_count} to {disk_count}"
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="L1<->L5",
                    status="PASS",
                    message=(
                        f"Config expected_skill_count ({config_count}) "
                        f"matches disk ({disk_count})"
                    ),
                )
            )

    return findings


def check_table_completeness(config: dict) -> list:
    """Check 4 — L2 delegation table entries have 'When to Load' guidance."""
    findings = []
    agent_text = read_agent_def(config)
    rows = scan_delegation_table_rows(agent_text)

    empty_count = 0
    for domain, skill, when_text in rows:
        when_stripped = when_text.strip()
        if not when_stripped or when_stripped in ("\u2014", "-", "TBD", "TODO"):
            empty_count += 1
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target=f"fv-thc/{skill}",
                    status="WARN",
                    severity="LOW",
                    message=(
                        f"Delegation table entry 'fv-thc/{skill}' has "
                        f"empty/placeholder 'When to Load' column"
                    ),
                    details="Add usage guidance for when this sub-skill should be loaded",
                )
            )

    if rows and empty_count == 0:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L2:completeness",
                status="PASS",
                message=(
                    f"All {len(rows)} delegation table entries have "
                    f"'When to Load' guidance"
                ),
            )
        )
    elif not rows:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L2:completeness",
                status="WARN",
                severity="MEDIUM",
                message="No delegation table rows found in FV-THC.md",
                details="Expected a table with | Domain | Sub-Skill | When to Load |",
            )
        )
    return findings


def check_subagent_warnings(config: dict) -> list:
    """Check 5 — L6 sub-agent references with availability warnings."""
    findings = []
    agent_text = read_agent_def(config)
    warned = scan_subagent_warnings(agent_text)

    for agent_name in warned:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target=f"subagent:{agent_name}",
                status="WARN",
                severity="LOW",
                message=(
                    f"Sub-agent '{agent_name}' has a \u26a0\ufe0f availability warning "
                    f"in FV-THC.md"
                ),
                details=(
                    "Agent may not be registered or is disabled. "
                    "Verify before delegation or remove the reference."
                ),
            )
        )

    if not warned:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="L6:subagents",
                status="PASS",
                message="No \u26a0\ufe0f availability warnings on sub-agent references",
            )
        )
    return findings


def check_config_stale_count(config: dict) -> list:
    """Check 6 — L4 length vs L5 expected_skill_count."""
    findings = []
    config_skills = scan_config_skills(config)
    config_count = scan_config_expected_count(config)

    if config_count is not None:
        actual_len = len(config_skills)
        if actual_len != config_count:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="L4<->L5",
                    status="FAIL",
                    severity="MEDIUM",
                    message=(
                        f"Config skills[] has {actual_len} entries but "
                        f"expected_skill_count={config_count}"
                    ),
                    details=(
                        f"Update self_check.expected_skill_count to {actual_len} "
                        f"or fix skills[] array"
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="L4<->L5",
                    status="PASS",
                    message=(
                        f"Config skills[] length ({actual_len}) matches "
                        f"expected_skill_count ({config_count})"
                    ),
                )
            )
    return findings


def check_repo_diff(config: dict) -> list:
    """Check 7 — Detect repo changes that affect delegation consistency."""
    findings = []
    skill_base = config["paths"]["skill_base"].replace("\\", "/")
    agent_def = config["paths"]["agent_def"].replace("\\", "/")

    try:
        repo_root = str(find_repo_root())

        # Combine: unstaged + staged + untracked
        changed_files = set()
        for cmd in [
            ["git", "diff", "--name-only", "HEAD"],
            ["git", "diff", "--name-only", "--cached"],
            ["git", "ls-files", "--others", "--exclude-standard"],
        ]:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=repo_root,
            )
            if result.returncode == 0 and result.stdout.strip():
                changed_files.update(result.stdout.strip().split("\n"))

        # Filter to delegation-relevant files
        delegation_files = [
            f
            for f in changed_files
            if (
                skill_base in f.replace("\\", "/")
                or agent_def in f.replace("\\", "/")
                or "self_improvement_config.json" in f
            )
        ]

        skill_changes = [f for f in delegation_files if "SKILL.md" in f]
        agent_changes = [
            f for f in delegation_files if agent_def in f.replace("\\", "/")
        ]
        config_changes = [
            f for f in delegation_files if "self_improvement_config.json" in f
        ]

        if skill_changes:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="repo:skill_dirs",
                    status="CHANGE",
                    severity="MEDIUM",
                    message=(
                        f"Uncommitted SKILL.md changes: {len(skill_changes)} file(s)"
                    ),
                    details="; ".join(sorted(skill_changes)[:5]),
                )
            )
        if agent_changes:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="repo:agent_def",
                    status="CHANGE",
                    severity="MEDIUM",
                    message="Uncommitted changes to FV-THC.md detected",
                    details="Verify delegation table consistency after editing",
                )
            )
        if config_changes:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="repo:config",
                    status="CHANGE",
                    severity="LOW",
                    message=(
                        "Uncommitted changes to self_improvement_config.json detected"
                    ),
                )
            )
        if not delegation_files:
            findings.append(
                Finding(
                    check=CHECK_NAME,
                    target="repo:diff",
                    status="PASS",
                    message="No uncommitted delegation-relevant changes",
                )
            )

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        findings.append(
            Finding(
                check=CHECK_NAME,
                target="repo:diff",
                status="SKIP",
                message=f"git diff unavailable: {exc}",
            )
        )

    return findings


# ===========================================================================
# Auto-fix helpers (optional --fix-counts)
# ===========================================================================


def fix_counts(config: dict) -> list:
    """Auto-fix count mismatches in FV-THC.md and config."""
    actions = []
    disk_count = len(scan_disk_skills(config))

    # Fix L3: FV-THC.md count claims
    agent_path = resolve_path(config["paths"]["agent_def"])
    agent_text = read_file(agent_path)
    count_claims = scan_count_claims(agent_text)

    for old_count in set(count_claims):
        if old_count != disk_count:
            old_pattern = f"{old_count} on-demand sub-skills"
            new_pattern = f"{disk_count} on-demand sub-skills"
            agent_text = agent_text.replace(old_pattern, new_pattern)
            actions.append(f"FV-THC.md: '{old_pattern}' -> '{new_pattern}'")

    if any(c != disk_count for c in count_claims):
        agent_path.write_text(agent_text, encoding="utf-8")

    # Fix L5: config expected_skill_count
    config_path = Path(__file__).parent / "self_improvement_config.json"
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        old_count = raw.get("self_check", {}).get("expected_skill_count")
        if old_count is not None and old_count != disk_count:
            raw["self_check"]["expected_skill_count"] = disk_count
            config_path.write_text(
                json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            actions.append(f"config: expected_skill_count {old_count} -> {disk_count}")

    return actions


# ===========================================================================
# Orchestration
# ===========================================================================

ALL_CHECKS = [
    ("disk_vs_table", check_disk_vs_table),  # L1 <-> L2
    ("disk_vs_config", check_disk_vs_config),  # L1 <-> L4
    ("count_consistency", check_count_consistency),  # L1 <-> L3 <-> L5
    ("table_completeness", check_table_completeness),  # L2 quality
    ("subagent_warnings", check_subagent_warnings),  # L6 quality
    ("config_stale_count", check_config_stale_count),  # L4 <-> L5
    ("repo_diff", check_repo_diff),  # git changes
]


def run_all_checks(config: dict, checks: list = None) -> Report:
    """Run delegation consistency checks and return a Report."""
    report = Report("thc_delegation_check", VERSION)

    targets = checks or ALL_CHECKS
    for name, func in targets:
        try:
            for finding in func(config):
                report.add(finding)
        except Exception as exc:
            report.add(
                Finding(
                    check=CHECK_NAME,
                    target=name,
                    status="ERROR",
                    severity="HIGH",
                    message=f"Check '{name}' raised: {exc}",
                )
            )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="THC Delegation Consistency Checker — "
        "cross-checks 6 locations for sub-skill/delegation sync",
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--save", action="store_true", help="Save report to reports/ directory"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging output"
    )
    parser.add_argument(
        "--check",
        type=str,
        default=None,
        help="Run a single check by name (e.g. disk_vs_table)",
    )
    parser.add_argument(
        "--fix-counts",
        action="store_true",
        help="Auto-fix count mismatches in FV-THC.md and config",
    )
    args = parser.parse_args()

    # Setup logging
    log = setup_logging("thc_delegation_check")
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config = load_config()

    # Auto-fix mode
    if args.fix_counts:
        actions = fix_counts(config)
        if actions:
            print("Fixed count mismatches:")
            for a in actions:
                print(f"  - {a}")
        else:
            print("No count mismatches to fix.")
        sys.exit(0)

    # Select checks
    if args.check:
        matched = [(n, f) for n, f in ALL_CHECKS if n == args.check]
        if not matched:
            valid = [n for n, _ in ALL_CHECKS]
            print(f"Unknown check '{args.check}'. Valid: {valid}")
            sys.exit(2)
        checks = matched
    else:
        checks = None  # run all

    # Run
    report = run_all_checks(config, checks)

    # Output
    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    # Save
    if args.save:
        report.save(resolve_path("reports"), "json" if args.json else "txt")

    # Exit code: 1 if any FAIL with HIGH/CRITICAL severity
    has_critical = any(
        f.status == "FAIL" and f.severity.lower() in ("high", "critical")
        for f in report.findings
    )
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
