#!/usr/bin/env python3
"""NVU Delegation Check — validates FV-NVU.md agent definition consistency.

Checks 7 locations for consistency:
  L1: Disk sub-skill directories (*/SKILL.md)
  L2: Agent definition delegation table (FV-NVU.md)
  L3: Agent definition count claims ("N on-demand sub-skills")
  L4: Config skills[] array
  L5: Config expected_skill_count
  L6: Sub-agent delegation warnings (missing/stale references)
  L7: Eval tests coverage

Ported from THC thc_delegation_check.py, adapted for NVU domain.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NON_SKILL_DIRS = {"docs", "eval", "tools", "reports", "archive", "__pycache__"}

AGENT_DEF_PATH = ".opencode/agent/FV/FV-NVU.md"
SKILL_ROOT = ".opencode/skill/fv-nvu"
CONFIG_PATH = ".opencode/skill/fv-nvu/tools/self_improvement_config.json"
EVAL_TESTS_PATH = ".opencode/skill/fv-nvu/eval/nvu_skill_eval_tests.md"

# Patterns to extract delegation references from agent definition
DELEGATION_SKILL_PATTERN = re.compile(
    r"""\|\s*`(?:fv-nvu[/\\]|/skill\s+fv-nvu/)"""
    r"""([\w-]+)`\s*\|""",
    re.IGNORECASE,
)
# Pattern for "/skill fv-nvu/xxx" load commands
SKILL_LOAD_PATTERN = re.compile(
    r"""/skill\s+fv-nvu/([\w-]+)""",
    re.IGNORECASE,
)
# Count claim pattern: "N on-demand sub-skills" or "N sub-skills"
# Must NOT match phrases like "3-tier structure" near "sub-skill"
COUNT_CLAIM_PATTERN = re.compile(
    r"(\d{2,})\s+(?:on-demand\s+)?sub-skills?"  # 2+ digit counts (10, 11, ...)
    r"|(\d+)\s+on-demand\s+sub-skills?"  # or explicit "N on-demand sub-skills"
    r"|(?:^|\|)\s*(\d+)\s+sub-skills?\s*(?:\||\n|$)",  # or "N sub-skills" at table/line boundary
    re.IGNORECASE | re.MULTILINE,
)

logger = logging.getLogger("nvu_delegation_check")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single check finding."""

    check_id: str
    status: str  # PASS, FAIL, WARN, INFO
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    message: str
    details: Optional[str] = None


@dataclass
class Report:
    """Aggregated report of all findings."""

    tool: str = "nvu_delegation_check"
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def summary(self) -> dict:
        counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
        for f in self.findings:
            counts[f.status] = counts.get(f.status, 0) + 1
        counts["total"] = len(self.findings)
        return counts

    def to_json(self) -> str:
        return json.dumps(
            {
                "tool": self.tool,
                "summary": self.summary,
                "findings": [asdict(f) for f in self.findings],
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_repo_root() -> Path:
    """Walk up from this file to find the repo root (.git directory)."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def discover_disk_skills(repo_root: Path) -> set[str]:
    """Find sub-skill directories on disk (those with SKILL.md)."""
    skill_root = repo_root / SKILL_ROOT
    skills = set()
    if not skill_root.is_dir():
        return skills
    for child in skill_root.iterdir():
        if child.is_dir() and child.name not in NON_SKILL_DIRS:
            if (child / "SKILL.md").exists():
                skills.add(child.name)
    return skills


def read_file(path: Path) -> str:
    """Read file content, return empty string if not found."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, PermissionError):
        return ""


def extract_delegation_skills(agent_text: str) -> set[str]:
    """Extract skill names referenced in delegation tables."""
    skills = set()
    # Match table entries like `fv-nvu/registers`
    for m in DELEGATION_SKILL_PATTERN.finditer(agent_text):
        skills.add(m.group(1).lower())
    # Match /skill fv-nvu/xxx load commands
    for m in SKILL_LOAD_PATTERN.finditer(agent_text):
        skills.add(m.group(1).lower())
    return skills


def extract_count_claims(agent_text: str) -> list[int]:
    """Extract all count claims from agent definition."""
    counts = []
    for m in COUNT_CLAIM_PATTERN.finditer(agent_text):
        # Pick the first non-None group (multi-alternative regex)
        val = next((g for g in m.groups() if g is not None), None)
        if val is not None:
            counts.append(int(val))
    return counts


def load_config(repo_root: Path) -> dict:
    """Load self-improvement config."""
    config_path = repo_root / CONFIG_PATH
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def extract_eval_test_skills(eval_text: str) -> set[str]:
    """Extract skill names referenced in eval test section headers."""
    skills = set()
    # Match section headers like "## 1. Registers Sub-Skill" or "NVU-REG-"
    skill_map = {
        "REG": "registers",
        "INF": "inference",
        "DMA": "dma",
        "PWR": "power",
        "DRV": "driver",
        "PLT": "platform",
        "DBG": "debug",
        "CAM": "camera",
        "FW": "firmware",
        "BIOS": "bios",
        "SIM": "simics",
    }
    for prefix, skill in skill_map.items():
        if f"NVU-{prefix}-" in eval_text:
            skills.add(skill)
    return skills


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_disk_vs_delegation(
    disk_skills: set[str],
    delegation_skills: set[str],
    report: Report,
) -> None:
    """Check L1 (disk) vs L2 (delegation table)."""
    check_id = "DELEG-001"

    on_disk_only = disk_skills - delegation_skills
    in_table_only = delegation_skills - disk_skills

    if not on_disk_only and not in_table_only:
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"Disk skills ({len(disk_skills)}) match delegation table ({len(delegation_skills)})",
            )
        )
    else:
        if on_disk_only:
            report.add(
                Finding(
                    check_id=f"{check_id}a",
                    status="FAIL",
                    severity="HIGH",
                    message=f"Skills on disk but NOT in delegation table: {sorted(on_disk_only)}",
                    details="Add these to the FV-NVU.md delegation table",
                )
            )
        if in_table_only:
            report.add(
                Finding(
                    check_id=f"{check_id}b",
                    status="WARN",
                    severity="MEDIUM",
                    message=f"Skills in delegation table but NOT on disk: {sorted(in_table_only)}",
                    details="These may be planned but not yet created",
                )
            )


def check_disk_vs_config(
    disk_skills: set[str],
    config: dict,
    report: Report,
) -> None:
    """Check L1 (disk) vs L4 (config skills[])."""
    check_id = "DELEG-002"
    config_skills = set(config.get("skills", []))

    on_disk_only = disk_skills - config_skills
    in_config_only = config_skills - disk_skills

    if not on_disk_only and not in_config_only:
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"Disk skills ({len(disk_skills)}) match config skills[] ({len(config_skills)})",
            )
        )
    else:
        if on_disk_only:
            report.add(
                Finding(
                    check_id=f"{check_id}a",
                    status="FAIL",
                    severity="HIGH",
                    message=f"Skills on disk but NOT in config: {sorted(on_disk_only)}",
                    details="Add to self_improvement_config.json skills[]",
                )
            )
        if in_config_only:
            report.add(
                Finding(
                    check_id=f"{check_id}b",
                    status="WARN",
                    severity="MEDIUM",
                    message=f"Skills in config but NOT on disk: {sorted(in_config_only)}",
                    details="Remove from config or create the sub-skill directory",
                )
            )


def check_count_consistency(
    disk_skills: set[str],
    agent_text: str,
    config: dict,
    report: Report,
) -> None:
    """Check L3 (count claims) vs L1 (disk) vs L5 (config count)."""
    check_id = "DELEG-003"
    actual_count = len(disk_skills)
    config_count = config.get("self_check", {}).get("expected_skill_count", 0)
    claimed_counts = extract_count_claims(agent_text)

    all_match = True

    # Check config expected_skill_count
    if config_count == actual_count:
        report.add(
            Finding(
                check_id=f"{check_id}a",
                status="PASS",
                severity="INFO",
                message=f"Config expected_skill_count ({config_count}) matches disk ({actual_count})",
            )
        )
    else:
        all_match = False
        report.add(
            Finding(
                check_id=f"{check_id}a",
                status="FAIL",
                severity="HIGH",
                message=f"Config expected_skill_count ({config_count}) != disk count ({actual_count})",
                details="Update self_improvement_config.json self_check.expected_skill_count",
            )
        )

    # Check agent definition count claims
    if claimed_counts:
        for i, claimed in enumerate(claimed_counts):
            if claimed == actual_count:
                report.add(
                    Finding(
                        check_id=f"{check_id}b{i}",
                        status="PASS",
                        severity="INFO",
                        message=f"Agent def count claim #{i + 1} ({claimed}) matches disk ({actual_count})",
                    )
                )
            else:
                all_match = False
                report.add(
                    Finding(
                        check_id=f"{check_id}b{i}",
                        status="WARN",
                        severity="MEDIUM",
                        message=f"Agent def count claim #{i + 1} ({claimed}) != disk ({actual_count})",
                        details="Update FV-NVU.md sub-skill count claim",
                    )
                )
    else:
        report.add(
            Finding(
                check_id=f"{check_id}c",
                status="INFO",
                severity="LOW",
                message="No count claims found in agent definition",
            )
        )


def check_delegation_completeness(
    delegation_skills: set[str],
    agent_text: str,
    report: Report,
) -> None:
    """Check that delegation table has load commands for each skill."""
    check_id = "DELEG-004"
    # Check that each delegated skill has a /skill load command
    load_skills = set()
    for m in SKILL_LOAD_PATTERN.finditer(agent_text):
        load_skills.add(m.group(1).lower())

    missing_load = delegation_skills - load_skills
    if not missing_load:
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"All {len(delegation_skills)} delegated skills have /skill load commands",
            )
        )
    else:
        report.add(
            Finding(
                check_id=check_id,
                status="WARN",
                severity="LOW",
                message=f"Skills in delegation table without /skill load command: {sorted(missing_load)}",
                details="These skills are referenced but may not have explicit load instructions",
            )
        )


def check_eval_coverage(
    disk_skills: set[str],
    eval_text: str,
    report: Report,
) -> None:
    """Check L7 (eval tests) coverage of disk skills."""
    check_id = "DELEG-005"
    eval_skills = extract_eval_test_skills(eval_text)

    missing = disk_skills - eval_skills
    if not missing:
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"Eval tests cover all {len(disk_skills)} disk skills",
            )
        )
    else:
        report.add(
            Finding(
                check_id=check_id,
                status="WARN",
                severity="MEDIUM",
                message=f"Skills without eval test coverage: {sorted(missing)}",
                details="Add test cases to nvu_skill_eval_tests.md",
            )
        )


def check_subagent_references(
    agent_text: str,
    report: Report,
) -> None:
    """Check for common delegation issues in agent definition."""
    check_id = "DELEG-006"
    issues = []

    # Check for phantom self-references (fv-nvu/SKILL.md pointing to itself)
    if re.search(r"fv-nvu/SKILL\.md", agent_text):
        issues.append("Self-reference to fv-nvu/SKILL.md (should be 'parent SKILL.md')")

    # Check for broken sub-skill references (fv-nvu/xxx where xxx doesn't exist)
    # This is covered by check_disk_vs_delegation, so just check format issues
    bad_refs = re.findall(r"`fv-nvu/([^`\s]+)`", agent_text)
    for ref in bad_refs:
        if "/" in ref and not ref.endswith(".md"):
            issues.append(
                f"Nested reference fv-nvu/{ref} — should be a direct sub-skill name"
            )

    if not issues:
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message="No delegation reference issues found",
            )
        )
    else:
        for i, issue in enumerate(issues):
            report.add(
                Finding(
                    check_id=f"{check_id}{chr(97 + i)}",
                    status="WARN",
                    severity="MEDIUM",
                    message=issue,
                )
            )


def check_config_skills_order(
    config: dict,
    report: Report,
) -> None:
    """Check that config skills[] is sorted (consistency convention)."""
    check_id = "DELEG-007"
    skills = config.get("skills", [])
    if skills == sorted(skills):
        report.add(
            Finding(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"Config skills[] is sorted alphabetically ({len(skills)} entries)",
            )
        )
    else:
        report.add(
            Finding(
                check_id=check_id,
                status="INFO",
                severity="LOW",
                message=f"Config skills[] is not sorted: {skills}",
                details=f"Suggested order: {sorted(skills)}",
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_all_checks(repo_root: Path) -> Report:
    """Run all delegation consistency checks."""
    report = Report()

    # Gather data from all sources
    disk_skills = discover_disk_skills(repo_root)
    agent_text = read_file(repo_root / AGENT_DEF_PATH)
    config = load_config(repo_root)
    eval_text = read_file(repo_root / EVAL_TESTS_PATH)

    if not agent_text:
        report.add(
            Finding(
                check_id="DELEG-000",
                status="FAIL",
                severity="CRITICAL",
                message=f"Agent definition not found: {AGENT_DEF_PATH}",
            )
        )
        return report

    delegation_skills = extract_delegation_skills(agent_text)

    logger.info("Disk skills: %s", sorted(disk_skills))
    logger.info("Delegation skills: %s", sorted(delegation_skills))
    logger.info("Config skills: %s", config.get("skills", []))

    # Run all checks
    check_disk_vs_delegation(disk_skills, delegation_skills, report)
    check_disk_vs_config(disk_skills, config, report)
    check_count_consistency(disk_skills, agent_text, config, report)
    check_delegation_completeness(delegation_skills, agent_text, report)
    check_eval_coverage(disk_skills, eval_text, report)
    check_subagent_references(agent_text, report)
    check_config_skills_order(config, report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVU Delegation Check — validate FV-NVU.md agent definition consistency",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--save", metavar="PATH", help="Save report to file")
    args = parser.parse_args()

    log_level = "WARNING" if args.json else ("DEBUG" if args.verbose else "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(levelname)s: %(message)s",
    )

    repo_root = find_repo_root()
    report = run_all_checks(repo_root)
    summary = report.summary

    if args.json:
        print(report.to_json())
    else:
        # Human-readable output
        print(f"\n{'=' * 60}")
        print(f"  NVU Delegation Check")
        print(f"{'=' * 60}\n")

        for f in report.findings:
            icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "ℹ"}.get(
                f.status, "?"
            )
            print(f"  {icon} [{f.check_id}] {f.message}")
            if f.details and f.status in ("FAIL", "WARN"):
                print(f"    → {f.details}")

        print(
            f"\n  Summary: {summary['PASS']} PASS, {summary['FAIL']} FAIL, "
            f"{summary['WARN']} WARN, {summary.get('INFO', 0)} INFO"
        )
        print(f"{'=' * 60}\n")

    if args.save:
        Path(args.save).write_text(report.to_json(), encoding="utf-8")
        logger.info("Report saved to %s", args.save)

    # Exit 1 only if there are FAIL findings with HIGH+ severity
    has_critical = any(
        f.status == "FAIL" and f.severity in ("CRITICAL", "HIGH")
        for f in report.findings
    )
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(main())
