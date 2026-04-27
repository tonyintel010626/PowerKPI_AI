#!/usr/bin/env python3
"""NVU Self-Wiki — cross-check NVU skill files against Confluence wiki pages.

Reads NVU-relevant Confluence wiki pages (using securewiki.py) and validates
that skill file content is consistent with wiki documentation.

STATUS: SCAFFOLD — NVU Confluence wiki pages are not yet established.
        This tool is ready to be activated once NVU team creates wiki pages.
        Update WIKI_PAGES below with real page IDs and assertions.

Ported from THC thc_self_wiki.py, adapted for NVU domain.

Usage:
  python nvu_self_wiki.py --live --user <IDSID>  # Live wiki check
  python nvu_self_wiki.py --offline              # Skill-only self-check
  python nvu_self_wiki.py --json                 # JSON output
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("nvu_self_wiki")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = SKILL_ROOT / ".wiki_cache"
SECUREWIKI_SCRIPT = SKILL_ROOT.parent.parent / "skill" / "securewiki" / "securewiki.py"

# NVU Sub-skills for cross-referencing
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

# ---------------------------------------------------------------------------
# Wiki Page Definitions — PLACEHOLDER: Update when NVU wiki pages exist
# ---------------------------------------------------------------------------
# Each entry defines:
#   id: Confluence page ID (numeric string)
#   title: Human-readable page title
#   space: Confluence space key
#   priority: P0=critical, P1=important, P2=nice-to-have
#   skill_targets: Which sub-skill SKILL.md files to cross-check
#   assertions: List of (pattern, target_skill, description)
#
# EXAMPLE (from THC — replace with real NVU pages):
# {
#     "id": "123456789",
#     "title": "NVU Debug BKM",
#     "space": "NVUVAL",
#     "priority": "P0",
#     "skill_targets": ["debug"],
#     "assertions": [
#         {
#             "pattern": r"HSDES\s+\d{10}",
#             "target_skill": "debug",
#             "description": "HSDES sighting IDs referenced in wiki",
#         },
#     ],
# }

WIKI_PAGES: list[dict[str, Any]] = [
    # ──────────────────────────────────────────────────────────────
    # TODO: Populate with real NVU Confluence page definitions
    # when the NVU validation team creates wiki documentation.
    #
    # Suggested pages to add:
    #   - NVU Debug BKM (debug procedures, known issues)
    #   - NVU Platform Config (BIOS knobs, strap settings)
    #   - NVU Power Management (D-state transitions, S0ix integration)
    #   - NVU Camera Pipeline (ISP config, sensor setup)
    #   - NVU FW Loading (firmware versions, IPC protocol)
    #   - NVU Test Execution Guide (NGA project, test suites)
    # ──────────────────────────────────────────────────────────────
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single wiki check finding."""

    check_id: str
    status: str  # PASS, FAIL, WARN, SKIP, INFO
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    message: str
    wiki_page: Optional[str] = None
    skill_target: Optional[str] = None
    details: Optional[str] = None


@dataclass
class Report:
    """Aggregated report of all findings."""

    tool: str = "nvu_self_wiki"
    mode: str = "offline"
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def summary(self) -> dict:
        counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0, "INFO": 0}
        for f in self.findings:
            counts[f.status] = counts.get(f.status, 0) + 1
        counts["total"] = len(self.findings)
        return counts

    def to_json(self) -> str:
        return json.dumps(
            {
                "tool": self.tool,
                "mode": self.mode,
                "summary": self.summary,
                "findings": [asdict(f) for f in self.findings],
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Wiki Access (via securewiki.py)
# ---------------------------------------------------------------------------


def find_securewiki() -> Optional[Path]:
    """Locate the securewiki.py script."""
    candidates = [
        SECUREWIKI_SCRIPT,
        SKILL_ROOT.parent / "securewiki" / "securewiki.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def read_wiki_page(
    page_id: str,
    user: str,
    securewiki_path: Path,
    use_cache: bool = True,
) -> Optional[str]:
    """Read a Confluence wiki page via securewiki.py."""
    # Check cache first
    cache_file = CACHE_DIR / f"page_{page_id}.txt"
    if use_cache and cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:  # Cache valid for 24 hours
            logger.debug("Using cached page %s (%.1fh old)", page_id, age_hours)
            return cache_file.read_text(encoding="utf-8", errors="replace")

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(securewiki_path),
                "read",
                "--page-id",
                page_id,
                "--user",
                user,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("Failed to read page %s: %s", page_id, result.stderr[:200])
            return None

        # Parse JSON response
        data = json.loads(result.stdout)
        content = data.get("body", data.get("content", ""))

        # Cache the result
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(content, encoding="utf-8")
        return content

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning("Error reading page %s: %s", page_id, e)
        return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def read_skill_file(skill_name: str) -> str:
    """Read a sub-skill SKILL.md file."""
    path = SKILL_ROOT / skill_name / "SKILL.md"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def check_skill_internal_consistency(report: Report) -> None:
    """Offline check: verify skill files are internally consistent."""
    check_base = "WIKI-OFFLINE"

    # Check 1: All skills exist
    for skill in NVU_SKILLS:
        skill_text = read_skill_file(skill)
        if skill_text:
            report.add(
                Finding(
                    check_id=f"{check_base}-EXISTS-{skill}",
                    status="PASS",
                    severity="INFO",
                    message=f"Skill file exists: {skill}/SKILL.md ({len(skill_text)} chars)",
                    skill_target=skill,
                )
            )
        else:
            report.add(
                Finding(
                    check_id=f"{check_base}-EXISTS-{skill}",
                    status="FAIL",
                    severity="HIGH",
                    message=f"Skill file missing: {skill}/SKILL.md",
                    skill_target=skill,
                )
            )

    # Check 2: Cross-references between skills
    for skill in NVU_SKILLS:
        skill_text = read_skill_file(skill)
        if not skill_text:
            continue
        # Check for at least one cross-reference to another skill
        has_xref = bool(re.search(r"fv-nvu/\w+", skill_text))
        if has_xref:
            report.add(
                Finding(
                    check_id=f"{check_base}-XREF-{skill}",
                    status="PASS",
                    severity="INFO",
                    message=f"Skill {skill} has cross-references to peer skills",
                    skill_target=skill,
                )
            )
        else:
            report.add(
                Finding(
                    check_id=f"{check_base}-XREF-{skill}",
                    status="WARN",
                    severity="LOW",
                    message=f"Skill {skill} has no cross-references to peer skills",
                    skill_target=skill,
                )
            )

    # Check 3: HAS reference presence
    for skill in NVU_SKILLS:
        skill_text = read_skill_file(skill)
        if not skill_text:
            continue
        has_ref = bool(
            re.search(r"(?:HAS|NVU.*HAS|Section\s+\d)", skill_text, re.IGNORECASE)
        )
        if has_ref:
            report.add(
                Finding(
                    check_id=f"{check_base}-HASREF-{skill}",
                    status="PASS",
                    severity="INFO",
                    message=f"Skill {skill} references HAS documentation",
                    skill_target=skill,
                )
            )
        else:
            report.add(
                Finding(
                    check_id=f"{check_base}-HASREF-{skill}",
                    status="INFO",
                    severity="LOW",
                    message=f"Skill {skill} has no HAS references (may be OK for high-level skills)",
                    skill_target=skill,
                )
            )


def check_wiki_assertions(
    wiki_content: str,
    page_config: dict,
    report: Report,
) -> None:
    """Run assertions for a wiki page against skill files."""
    page_title = page_config["title"]

    for assertion in page_config.get("assertions", []):
        pattern = assertion["pattern"]
        target_skill = assertion["target_skill"]
        description = assertion["description"]
        check_id = f"WIKI-{target_skill.upper()}-{description[:20].replace(' ', '_')}"

        # Find pattern in wiki
        wiki_matches = re.findall(pattern, wiki_content, re.IGNORECASE)
        if not wiki_matches:
            report.add(
                Finding(
                    check_id=check_id,
                    status="INFO",
                    severity="LOW",
                    message=f"Pattern not found in wiki: {description}",
                    wiki_page=page_title,
                    skill_target=target_skill,
                )
            )
            continue

        # Cross-check against skill file
        skill_text = read_skill_file(target_skill)
        if not skill_text:
            report.add(
                Finding(
                    check_id=check_id,
                    status="WARN",
                    severity="MEDIUM",
                    message=f"Cannot cross-check: {target_skill}/SKILL.md not found",
                    wiki_page=page_title,
                    skill_target=target_skill,
                )
            )
            continue

        # Check if concrete values from wiki exist in skill
        skill_matches = re.findall(pattern, skill_text, re.IGNORECASE)
        if skill_matches:
            report.add(
                Finding(
                    check_id=check_id,
                    status="PASS",
                    severity="INFO",
                    message=f"Wiki↔Skill match: {description} ({len(wiki_matches)} wiki, {len(skill_matches)} skill)",
                    wiki_page=page_title,
                    skill_target=target_skill,
                )
            )
        else:
            report.add(
                Finding(
                    check_id=check_id,
                    status="WARN",
                    severity="MEDIUM",
                    message=f"Wiki has {len(wiki_matches)} matches for '{description}' but skill has 0",
                    wiki_page=page_title,
                    skill_target=target_skill,
                    details=f"Skill {target_skill} may be missing information from wiki page '{page_title}'",
                )
            )


# ---------------------------------------------------------------------------
# Main execution modes
# ---------------------------------------------------------------------------


def run_live_check(user: str, use_cache: bool, report: Report) -> None:
    """Run live wiki checks (requires network + credentials)."""
    report.mode = "live"

    if not WIKI_PAGES:
        report.add(
            Finding(
                check_id="WIKI-SETUP",
                status="SKIP",
                severity="INFO",
                message="No NVU wiki pages configured — add page definitions to WIKI_PAGES in nvu_self_wiki.py",
                details="This tool is a scaffold awaiting NVU Confluence wiki page creation",
            )
        )
        # Still run offline checks
        check_skill_internal_consistency(report)
        return

    securewiki = find_securewiki()
    if not securewiki:
        report.add(
            Finding(
                check_id="WIKI-SETUP",
                status="FAIL",
                severity="HIGH",
                message="securewiki.py not found — cannot access Confluence",
            )
        )
        check_skill_internal_consistency(report)
        return

    # Read and check each wiki page
    for page_config in WIKI_PAGES:
        page_id = page_config["id"]
        page_title = page_config["title"]

        content = read_wiki_page(page_id, user, securewiki, use_cache)
        if content is None:
            report.add(
                Finding(
                    check_id=f"WIKI-READ-{page_id}",
                    status="FAIL",
                    severity="HIGH",
                    message=f"Failed to read wiki page: {page_title} (ID: {page_id})",
                )
            )
            continue

        report.add(
            Finding(
                check_id=f"WIKI-READ-{page_id}",
                status="PASS",
                severity="INFO",
                message=f"Successfully read wiki page: {page_title} ({len(content)} chars)",
            )
        )

        check_wiki_assertions(content, page_config, report)

    # Also run offline checks
    check_skill_internal_consistency(report)


def run_offline_check(report: Report) -> None:
    """Run offline checks (skill files only, no wiki access)."""
    report.mode = "offline"
    check_skill_internal_consistency(report)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVU Self-Wiki — cross-check skill files against Confluence wiki pages",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--live", action="store_true", help="Live wiki check (requires network)"
    )
    mode.add_argument(
        "--offline", action="store_true", help="Offline skill-only check (default)"
    )
    parser.add_argument("--user", metavar="IDSID", help="Intel IDSID for wiki access")
    parser.add_argument("--no-cache", action="store_true", help="Disable wiki cache")
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear wiki cache before running"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--save", metavar="PATH", help="Save report to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    log_level = "WARNING" if args.json else ("DEBUG" if args.verbose else "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(levelname)s: %(message)s",
    )

    if args.clear_cache and CACHE_DIR.exists():
        import shutil

        shutil.rmtree(CACHE_DIR)
        logger.info("Wiki cache cleared")

    report = Report()

    if args.live:
        if not args.user:
            logger.error("--user required for --live mode")
            return 1
        run_live_check(args.user, not args.no_cache, report)
    else:
        run_offline_check(report)

    summary = report.summary

    if args.json:
        print(report.to_json())
    else:
        print(f"\n{'=' * 60}")
        print(f"  NVU Self-Wiki ({report.mode} mode)")
        print(f"{'=' * 60}\n")

        for f in report.findings:
            icon = {
                "PASS": "✓",
                "FAIL": "✗",
                "WARN": "⚠",
                "SKIP": "⊘",
                "INFO": "ℹ",
            }.get(f.status, "?")
            print(f"  {icon} [{f.check_id}] {f.message}")
            if f.details and f.status in ("FAIL", "WARN"):
                print(f"    → {f.details}")

        print(
            f"\n  Summary: {summary.get('PASS', 0)} PASS, {summary.get('FAIL', 0)} FAIL, "
            f"{summary.get('WARN', 0)} WARN, {summary.get('SKIP', 0)} SKIP, "
            f"{summary.get('INFO', 0)} INFO"
        )
        print(f"{'=' * 60}\n")

    if args.save:
        Path(args.save).write_text(report.to_json(), encoding="utf-8")
        logger.info("Report saved to %s", args.save)

    # Exit 0 — wiki checks are advisory, not blocking
    return 0


if __name__ == "__main__":
    sys.exit(main())
