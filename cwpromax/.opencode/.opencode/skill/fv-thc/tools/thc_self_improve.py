#!/usr/bin/env python3
# > **Owner**: Chin, William Willy (`willychi`)
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.
"""THC Self-Improve: Orchestrator that chains all self-improvement capabilities
and generates actionable improvement proposals with human approval gate.

Pipeline: Check → Study → Learn → Verify → Propose → (Approve) → Apply

Each stage feeds its findings into the next. The final output is a set of
improvement proposals that can be reviewed and applied.

Usage:
    python thc_self_improve.py                    # full pipeline, proposals only
    python thc_self_improve.py --stage check      # run single stage
    python thc_self_improve.py --skip learn       # skip a stage
    python thc_self_improve.py --auto-apply       # apply without approval (CAUTION)
    python thc_self_improve.py --dry-run          # show what would be proposed
    python thc_self_improve.py --json             # JSON output
    python thc_self_improve.py --save             # save report + proposals
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap: ensure tools/ is on sys.path for sibling imports
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from thc_self_common import (  # noqa: E402
    Finding,
    Report,
    find_repo_root,
    load_config,
    read_skill,
    read_agent_def,
    get_skill_path,
    get_all_skill_paths,
    setup_logging,
    save_last_run_timestamp,
)

logger = logging.getLogger("thc_self_improve")

# ---------------------------------------------------------------------------
# Stage Runners (import sibling modules)
# ---------------------------------------------------------------------------


def _run_check(config: Optional[Dict[str, Any]] = None) -> Report:
    """Run self-check stage."""
    try:
        from thc_self_check import run_all_checks  # type: ignore

        return run_all_checks(config=config)
    except ImportError as e:
        logger.error("Cannot import thc_self_check: %s", e)
        report = Report(name="THC Self-Check (import failed)", version="1.0.0")
        report.findings.append(
            Finding(
                check="import_check",
                target="thc_self_check",
                status="ERROR",
                message=f"Import failed: {e}",
            )
        )
        return report


def _run_study(
    config: Optional[Dict[str, Any]] = None, since: Optional[str] = None
) -> Report:
    """Run self-study stage."""
    try:
        from thc_self_study import run_all_studies  # type: ignore

        return run_all_studies(config=config, since=since, sources=None)
    except ImportError as e:
        logger.error("Cannot import thc_self_study: %s", e)
        report = Report(name="THC Self-Study (import failed)", version="1.0.0")
        report.findings.append(
            Finding(
                check="import_study",
                target="thc_self_study",
                status="ERROR",
                message=f"Import failed: {e}",
            )
        )
        return report


def _run_learn(
    config: Optional[Dict[str, Any]] = None, since: Optional[str] = None
) -> Report:
    """Run self-learn stage."""
    try:
        from thc_self_learn import run_learn  # type: ignore

        return run_learn(sources=None, since=since, config=config)
    except ImportError as e:
        logger.error("Cannot import thc_self_learn: %s", e)
        report = Report(name="THC Self-Learn (import failed)", version="1.0.0")
        report.findings.append(
            Finding(
                check="import_learn",
                target="thc_self_learn",
                status="ERROR",
                message=f"Import failed: {e}",
            )
        )
        return report


def _run_verify(
    config: Optional[Dict[str, Any]] = None, categories: Optional[List[str]] = None
) -> Report:
    """Run self-verify stage."""
    try:
        from thc_self_verify import run_all_tests  # type: ignore

        return run_all_tests(config=config, category=categories)
    except ImportError as e:
        logger.error("Cannot import thc_self_verify: %s", e)
        report = Report(name="THC Self-Verify (import failed)", version="1.0.0")
        report.findings.append(
            Finding(
                check="import_verify",
                target="thc_self_verify",
                status="ERROR",
                message=f"Import failed: {e}",
            )
        )
        return report


def _run_wiki(
    config: Optional[Dict[str, Any]] = None, live: bool = False, user: str = "willychi"
) -> Report:
    """Run wiki cross-check stage: verify skill files against Confluence wiki pages.

    Runs TWO wiki checks and merges results:
      1. Simics wiki (80 pages) — thc_wiki_verify.run_pipeline_check()
      2. FV wiki (5 pages)     — thc_self_wiki.run_wiki_check()
    """
    merged = Report(name="THC Wiki Cross-Check (Simics + FV)", version="1.0.0")

    # --- Part 1: Simics wiki (80 pages from SRESIMICS/THCipsv/PPA/VICESW) ---
    try:
        from thc_wiki_verify import run_pipeline_check  # type: ignore

        simics_findings = run_pipeline_check(live=live, user=user)
        for f in simics_findings:
            # Tag findings so we know which wiki source they came from
            f.details = f.details or {}
            f.details["wiki_source"] = "simics"
            merged.add(f)
        logger.info("Simics wiki: %d findings", len(simics_findings))
    except ImportError as e:
        logger.error("Cannot import thc_wiki_verify: %s", e)
        merged.add(
            Finding(
                check="import_simics_wiki",
                target="thc_wiki_verify",
                status="ERROR",
                message=f"Simics wiki import failed: {e}",
            )
        )
    except Exception as e:
        logger.error("Simics wiki check error: %s", e)
        merged.add(
            Finding(
                check="simics_wiki_error",
                target="thc_wiki_verify",
                status="ERROR",
                message=f"Simics wiki check failed: {e}",
            )
        )

    # --- Part 2: FV wiki (5 THC BKM/issues/BOM pages) ---
    try:
        from thc_self_wiki import run_wiki_check  # type: ignore

        fv_report, fv_actionable = run_wiki_check(config=config, live=live, user=user)
        for f in fv_report.findings:
            f.details = f.details or {}
            f.details["wiki_source"] = "fv"
            merged.add(f)
        logger.info("FV wiki: %d findings", len(fv_report.findings))
    except ImportError as e:
        logger.error("Cannot import thc_self_wiki: %s", e)
        merged.add(
            Finding(
                check="import_fv_wiki",
                target="thc_self_wiki",
                status="ERROR",
                message=f"FV wiki import failed: {e}",
            )
        )
    except Exception as e:
        logger.error("FV wiki check error: %s", e)
        merged.add(
            Finding(
                check="fv_wiki_error",
                target="thc_self_wiki",
                status="ERROR",
                message=f"FV wiki check failed: {e}",
            )
        )

    return merged


# ---------------------------------------------------------------------------
# Coverage Gap Detection (Task 5: auto-detect uncovered content)
# ---------------------------------------------------------------------------

# Important term patterns to extract from skill files for gap analysis
_IMPORTANT_TERM_PATTERNS = [
    (r"HSD?\s*#?\s*(\d{11,})", "HSD"),  # HSDES sighting IDs (11+ digits)
    (r"0x([0-9A-Fa-f]{4})", "DID"),  # Device IDs / register values
    (r"\b(THC_\w{3,})\b", "REG"),  # THC register names
    (r"\b(IC_\w{3,})\b", "REG"),  # I2C sub-IP register names
    (r"\b(RXDMA\d?|TXDMA|SWDMA)\b", "DMA"),  # DMA engine names
    (r"\b(D0i[23]|D3[Hh]ot|D3[Cc]old|S0ix|CGPG|LTR|WoT)\b", "PM"),  # Power states
    (r"\b(P\d{4})\b", "ECO"),  # ECO/problem IDs (P0582 etc.)
    (r"\b(HIDSPI|HIDI2C|QuickSPI|QuickI2C)\b", "PROTO"),  # Protocol names
]


def _run_coverage_gap(
    config: dict, mode: str = "full", diff_base: str = "HEAD~1"
) -> "Report":
    """Detect skill file content not covered by any self-verify assertion.

    Args:
        config: Pipeline configuration dict.
        mode: "full" scans all skill content; "diff" scans only git-changed lines.
        diff_base: Git ref for diff mode (default HEAD~1).

    Returns:
        Report with findings for each uncovered important term.
    """
    report = Report(name="THC Coverage Gap Detection", version="1.0.0")

    # --- Step 1: Collect all assertion regex patterns from self-verify ---
    assertion_patterns: list[str] = []
    try:
        from thc_self_verify import EVAL_TESTS

        for test_id, test_def in EVAL_TESTS.items():
            for assertion in test_def.get("assertions", []):
                if len(assertion) >= 3:
                    assertion_patterns.append(assertion[2])  # regex pattern
    except ImportError:
        report.findings.append(
            Finding(
                check="coverage_gap",
                target="thc_self_verify",
                status="ERROR",
                message="Cannot import EVAL_TESTS from thc_self_verify",
            )
        )
        return report

    combined_assertion_re = " ||| ".join(assertion_patterns)

    # --- Step 2: Collect content to analyze ---
    skill_content: dict[str, str] = {}
    skill_paths = get_all_skill_paths(config)

    if mode == "diff":
        # Use git diff to get only changed lines
        import subprocess

        for skill_name, path in skill_paths.items():
            try:
                result = subprocess.run(
                    ["git", "diff", diff_base, "--", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(find_repo_root()),
                )
                # Extract only added lines (start with +, not +++)
                added = "\n".join(
                    line[1:]
                    for line in result.stdout.splitlines()
                    if line.startswith("+") and not line.startswith("+++")
                )
                if added.strip():
                    skill_content[skill_name] = added
            except (subprocess.TimeoutExpired, FileNotFoundError):
                skill_content[skill_name] = read_skill(skill_name, config)
    else:
        for skill_name, _path in skill_paths.items():
            skill_content[skill_name] = read_skill(skill_name, config)

    # --- Step 3: Extract important terms from skill content ---
    import re

    uncovered_terms: list[
        tuple[str, str, str, str]
    ] = []  # (skill, term, category, context)

    for skill_name, content in skill_content.items():
        for pattern, category in _IMPORTANT_TERM_PATTERNS:
            for match in re.finditer(pattern, content):
                term = match.group(0)
                # Check if this term appears in ANY assertion pattern
                term_escaped = re.escape(term)
                covered = any(
                    re.search(re.escape(term)[:8], ap)  # Partial match (first 8 chars)
                    for ap in assertion_patterns
                )
                if not covered:
                    # Get surrounding context (up to 60 chars)
                    start = max(0, match.start() - 30)
                    end = min(len(content), match.end() + 30)
                    context = content[start:end].replace("\n", " ").strip()
                    uncovered_terms.append((skill_name, term, category, context))

    # --- Step 4: Deduplicate and prioritize ---
    seen: set[str] = set()
    unique_uncovered: list[tuple[str, str, str, str]] = []
    for skill, term, cat, ctx in uncovered_terms:
        key = f"{cat}:{term}"
        if key not in seen:
            seen.add(key)
            unique_uncovered.append((skill, term, cat, ctx))

    # --- Step 5: Generate findings ---
    # Suppress common false positives (generic hex values, common register prefixes)
    _SUPPRESS = {
        "0x0000",
        "0x0001",
        "0x0002",
        "0x0004",
        "0x0008",
        "0x00FF",
        "0xFFFF",
        "0x0100",
        "THC_M_",
        "THC_SS",
        "IC_CON",
    }

    for skill, term, cat, ctx in unique_uncovered:
        if term in _SUPPRESS or any(term.startswith(s) for s in _SUPPRESS):
            continue
        report.findings.append(
            Finding(
                check="coverage_gap",
                target=f"{skill}/{cat}",
                status="WARN",
                message=f"Term '{term}' ({cat}) in {skill} has no matching assertion. Context: ...{ctx}...",
            )
        )

    # Summary finding
    total_terms = len(seen)
    gap_count = len(report.findings)
    report.findings.insert(
        0,
        Finding(
            check="coverage_gap_summary",
            target="all_skills",
            status="PASS" if gap_count < 10 else "WARN",
            message=(
                f"Scanned {len(skill_content)} skill files ({mode} mode). "
                f"Found {total_terms} unique important terms, "
                f"{gap_count} potentially uncovered by assertions."
            ),
        ),
    )

    return report


# ---------------------------------------------------------------------------
# Improvement Proposal
# ---------------------------------------------------------------------------


class Proposal:
    """A single improvement proposal generated from pipeline findings."""

    __slots__ = (
        "id",
        "priority",
        "category",
        "target_file",
        "action",
        "description",
        "rationale",
        "source_findings",
        "status",
    )

    def __init__(
        self,
        proposal_id: str,
        priority: str,
        category: str,
        target_file: str,
        action: str,
        description: str,
        rationale: str,
        source_findings: Optional[List[str]] = None,
    ):
        self.id = proposal_id
        self.priority = priority  # high, medium, low
        self.category = category  # content, structure, coverage, accuracy
        self.target_file = target_file  # skill file or doc to modify
        self.action = action  # add, update, fix, remove
        self.description = description  # what to do
        self.rationale = rationale  # why
        self.source_findings = source_findings or []
        self.status = "proposed"  # proposed, approved, applied, rejected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "priority": self.priority,
            "category": self.category,
            "target_file": self.target_file,
            "action": self.action,
            "description": self.description,
            "rationale": self.rationale,
            "source_findings": self.source_findings,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Proposal Generator
# ---------------------------------------------------------------------------


def _generate_proposals(
    stage_reports: Dict[str, Report],
    config: Dict[str, Any],
) -> List[Proposal]:
    """Analyze all stage findings and generate improvement proposals.

    Maps common finding patterns to actionable proposals:
    - FAIL findings from check → structural fixes
    - CHANGE findings from study → content updates
    - WARN findings from learn → coverage additions
    - FAIL findings from verify → accuracy corrections
    """
    proposals: List[Proposal] = []
    max_proposals = config.get("self_improve", {}).get("max_proposals_per_run", 20)
    proposal_counter = 0

    # --- From Self-Check: structural issues ---
    check_report = stage_reports.get("check")
    if check_report:
        for f in check_report.findings:
            if f.status in ("FAIL", "ERROR"):
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                # Determine action based on check type
                action = "fix"
                category = "structure"
                target = f.target or "unknown"

                if "owner" in f.check.lower():
                    action = "add"
                    description = f"Add missing owner header to {target}"
                elif "stale" in f.check.lower():
                    action = "update"
                    description = f"Fix stale reference in {target}"
                elif "cross_ref" in f.check.lower():
                    action = "add"
                    category = "coverage"
                    description = f"Add missing cross-reference in {target}"
                elif "exist" in f.check.lower():
                    action = "add"
                    description = f"Create missing file: {target}"
                else:
                    description = f"Fix structural issue: {f.message}"

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority=f.effective_severity or "medium",
                        category=category,
                        target_file=target,
                        action=action,
                        description=description,
                        rationale=f"Self-Check: {f.message}",
                        source_findings=[f"check:{f.check}"],
                    )
                )

    # --- From Self-Study: source code changes detected ---
    study_report = stage_reports.get("study")
    if study_report:
        for f in study_report.findings:
            if f.status == "CHANGE":
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                # Parse details for specifics
                details = {}
                if f.details:
                    try:
                        details = json.loads(f.details)
                    except (json.JSONDecodeError, TypeError):
                        pass

                source = f.target or "unknown"
                commit_count = details.get(
                    "commit_count", details.get("commits", "unknown")
                )

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority="high" if "linux" in source.lower() else "medium",
                        category="content",
                        target_file=_map_source_to_skill(source),
                        action="update",
                        description=(
                            f"Review {commit_count} new change(s) in {source} "
                            f"and update skill content"
                        ),
                        rationale=f"Self-Study: {f.message}",
                        source_findings=[f"study:{f.check}"],
                    )
                )

    # --- From Self-Learn: coverage gaps ---
    learn_report = stage_reports.get("learn")
    if learn_report:
        for f in learn_report.findings:
            if f.check == "coverage_gap" and f.status == "WARN":
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                details = {}
                if f.details:
                    try:
                        details = json.loads(f.details)
                    except (json.JSONDecodeError, TypeError):
                        pass

                skill_name = details.get("skill", f.target or "unknown")
                uncovered = details.get("uncovered_count", 0)
                signals = details.get("uncovered_signals", [])

                # Build description from uncovered signals
                signal_summary = "; ".join(
                    s.get("signal", "")[:50] for s in signals[:3]
                )

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority="high" if uncovered >= 3 else "medium",
                        category="coverage",
                        target_file=f"fv-thc/{skill_name}/SKILL.md",
                        action="add",
                        description=(
                            f"Add coverage for {uncovered} uncovered signal(s): "
                            f"{signal_summary}"
                        ),
                        rationale=f"Self-Learn: {f.message}",
                        source_findings=[f"learn:{f.check}"],
                    )
                )

            elif f.check == "feedback_item" and f.status == "WARN":
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                details = {}
                if f.details:
                    try:
                        details = json.loads(f.details)
                    except (json.JSONDecodeError, TypeError):
                        pass

                fb_type = details.get("type", "suggestion")
                skill = details.get("skill", "")
                target = f"fv-thc/{skill}/SKILL.md" if skill else "unknown"

                action_map = {
                    "gap": "add",
                    "correction": "fix",
                    "suggestion": "update",
                    "sighting": "add",
                }

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority=details.get("priority", "medium"),
                        category="content" if fb_type == "correction" else "coverage",
                        target_file=target,
                        action=action_map.get(fb_type, "update"),
                        description=f"[{fb_type}] {details.get('full_message', f.message)[:150]}",
                        rationale=f"Manual feedback from {details.get('author', 'unknown')}",
                        source_findings=[
                            f"learn:feedback[{details.get('index', '?')}]"
                        ],
                    )
                )

    # --- From Self-Verify: accuracy issues ---
    verify_report = stage_reports.get("verify")
    if verify_report:
        for f in verify_report.findings:
            if f.status == "FAIL":
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority="high",  # verify failures are always high priority
                        category="accuracy",
                        target_file=f.target or "unknown",
                        action="fix",
                        description=f"Fix verification failure: {f.message[:150]}",
                        rationale=f"Self-Verify: assertion {f.check} failed",
                        source_findings=[f"verify:{f.check}"],
                    )
                )

    # --- From Wiki Cross-Check: drift between wiki and skill files ---
    wiki_report = stage_reports.get("wiki")
    if wiki_report:
        for f in wiki_report.findings:
            if f.status == "FAIL" and f.check not in (
                "wiki_summary",
                "wiki_read_error",
            ):
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                # Determine target skill file from finding target
                target_skill = f.target or "unknown"
                if "/" not in target_skill and not target_skill.endswith(".md"):
                    target_skill = f"fv-thc/{target_skill}/SKILL.md"

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority="medium",
                        category="content",
                        target_file=target_skill,
                        action="update",
                        description=f"Wiki drift: {f.message[:150]}",
                        rationale=f"Wiki Cross-Check: wiki page content not reflected in skill file",
                        source_findings=[f"wiki:{f.check}"],
                    )
                )
            elif f.status == "WARN" and "new_content" in (f.check or ""):
                proposal_counter += 1
                if proposal_counter > max_proposals:
                    break

                target_skill = f.target or "unknown"
                if "/" not in target_skill and not target_skill.endswith(".md"):
                    target_skill = f"fv-thc/{target_skill}/SKILL.md"

                proposals.append(
                    Proposal(
                        proposal_id=f"IMP-{proposal_counter:03d}",
                        priority="low",
                        category="coverage",
                        target_file=target_skill,
                        action="add",
                        description=f"New wiki content to review: {f.message[:150]}",
                        rationale=f"Wiki Cross-Check: wiki has content not yet in skill files",
                        source_findings=[f"wiki:{f.check}"],
                    )
                )

    # Sort by priority (high > medium > low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    proposals.sort(key=lambda p: priority_order.get(p.priority, 99))

    return proposals


def _map_source_to_skill(source: str) -> str:
    """Map a source repository/file to the most relevant skill file."""
    source_lower = source.lower()
    if "linux" in source_lower or "kernel" in source_lower:
        return "fv-thc/driver/SKILL.md"
    if "hspi" in source_lower or "hidspi" in source_lower:
        return "fv-thc/hidspi/SKILL.md"
    if "hid-i2c" in source_lower or "hidi2c" in source_lower:
        return "fv-thc/hidi2c/SKILL.md"
    if "has" in source_lower:
        return "fv-thc/registers/SKILL.md"
    if "bwg" in source_lower:
        return "fv-thc/platform/SKILL.md"
    return "fv-thc/SKILL.md (unknown mapping)"


# ---------------------------------------------------------------------------
# Proposal Application (with approval gate)
# ---------------------------------------------------------------------------


def _save_proposals(
    proposals: List[Proposal],
    config: Dict[str, Any],
) -> Path:
    """Save proposals to JSON file for human review."""
    repo_root = find_repo_root()
    proposal_rel = config.get("self_improve", {}).get(
        "proposal_file", "reports/improvement_proposals.json"
    )
    # Resolve relative to skill base
    skill_base = repo_root / config.get("paths", {}).get(
        "skill_base", ".opencode/skill/fv-thc"
    )
    proposal_path = skill_base / proposal_rel
    proposal_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generated": datetime.now().isoformat(),
        "total": len(proposals),
        "by_priority": {
            "high": sum(1 for p in proposals if p.priority == "high"),
            "medium": sum(1 for p in proposals if p.priority == "medium"),
            "low": sum(1 for p in proposals if p.priority == "low"),
        },
        "by_category": {},
        "proposals": [p.to_dict() for p in proposals],
    }

    # Count by category
    for p in proposals:
        data["by_category"][p.category] = data["by_category"].get(p.category, 0) + 1

    with open(proposal_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info("Saved %d proposals to %s", len(proposals), proposal_path)
    return proposal_path


def _update_changelog(
    proposals: List[Proposal],
    stage_reports: Dict[str, Report],
    config: Dict[str, Any],
) -> Path:
    """Append improvement run entry to changelog."""
    repo_root = find_repo_root()
    changelog_rel = config.get("self_improve", {}).get(
        "changelog_file", "reports/improvement_changelog.md"
    )
    skill_base = repo_root / config.get("paths", {}).get(
        "skill_base", ".opencode/skill/fv-thc"
    )
    changelog_path = skill_base / changelog_rel
    changelog_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_findings = sum(len(r.findings) for r in stage_reports.values())

    entry_lines = [
        f"\n## Run: {timestamp}\n",
        f"\n**Pipeline stages**: {', '.join(stage_reports.keys())}\n",
        f"**Total findings**: {total_findings}\n",
        f"**Proposals generated**: {len(proposals)}\n",
    ]

    # Per-stage summary
    for stage_name, report in stage_reports.items():
        pass_count = report.pass_count
        fail_count = report.fail_count
        warn_count = sum(1 for f in report.findings if f.status == "WARN")
        entry_lines.append(
            f"- **{stage_name}**: {pass_count} pass, {fail_count} fail, "
            f"{warn_count} warn\n"
        )

    # Proposal summary
    if proposals:
        entry_lines.append(f"\n### Proposals ({len(proposals)})\n\n")
        for p in proposals:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p.priority, "⚪")
            entry_lines.append(
                f"- {icon} **{p.id}** [{p.action}] {p.description[:100]}\n"
            )
    else:
        entry_lines.append("\nNo proposals generated — all checks passed.\n")

    entry_lines.append("\n---\n")

    # Append or create
    if changelog_path.exists():
        with open(changelog_path, "a", encoding="utf-8") as f:
            f.writelines(entry_lines)
    else:
        header = (
            "# THC Self-Improvement Changelog\n"
            "> **Owner**: Chin, William Willy (`willychi`)\n\n"
            "Auto-generated by `thc_self_improve.py`. Each entry records a\n"
            "pipeline run with findings and proposals.\n\n"
            "---\n"
        )
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.writelines(entry_lines)

    logger.info("Updated changelog at %s", changelog_path)
    return changelog_path


# ---------------------------------------------------------------------------
# Pipeline Orchestrator
# ---------------------------------------------------------------------------


def run_improve(
    stages: Optional[List[str]] = None,
    skip_stages: Optional[List[str]] = None,
    since: Optional[str] = None,
    auto_apply: bool = False,
    dry_run: bool = False,
    config: Optional[Dict[str, Any]] = None,
    live_wiki: bool = False,
    wiki_user: str = "willychi",
) -> Tuple[Report, List[Proposal]]:
    """Run the full self-improvement pipeline.

    Args:
        stages: Explicit list of stages to run. None = all.
        skip_stages: Stages to skip. Ignored if stages is set.
        since: ISO date for study/learn lookback.
        auto_apply: If True, apply proposals without approval (CAUTION).
        dry_run: If True, generate proposals but don't save/apply.
        config: Config dict. Auto-loaded if None.
        live_wiki: If True, read wiki pages live (slow). Default offline (assertions only).
        wiki_user: IDSID for wiki authentication.

    Returns:
        (master_report, proposals) tuple.
    """
    if config is None:
        config = load_config()
    assert config is not None, "Failed to load self-improvement config"

    all_stages = ["check", "study", "learn", "verify", "wiki"]
    if stages:
        active_stages = [s for s in all_stages if s in stages]
    elif skip_stages:
        active_stages = [s for s in all_stages if s not in skip_stages]
    else:
        active_stages = all_stages

    master_report = Report(name="THC Self-Improve", version="1.0.0")
    stage_reports: Dict[str, Report] = {}

    # ---- Stage 1: Check ----
    if "check" in active_stages:
        logger.info("=" * 60)
        logger.info("STAGE 1/5: Self-Check")
        logger.info("=" * 60)
        check_report = _run_check(config=config)
        stage_reports["check"] = check_report
        master_report.findings.append(
            Finding(
                check="stage_check",
                target="self_check",
                status="FAIL" if check_report.has_failures else "PASS",
                message=(
                    f"Self-Check: {check_report.pass_count} pass, "
                    f"{check_report.fail_count} fail"
                ),
            )
        )

    # ---- Stage 2: Study ----
    if "study" in active_stages:
        logger.info("=" * 60)
        logger.info("STAGE 2/5: Self-Study")
        logger.info("=" * 60)
        study_report = _run_study(config=config, since=since)
        stage_reports["study"] = study_report
        change_count = sum(1 for f in study_report.findings if f.status == "CHANGE")
        master_report.findings.append(
            Finding(
                check="stage_study",
                target="self_study",
                status="WARN" if change_count > 0 else "PASS",
                message=(
                    f"Self-Study: {change_count} source(s) changed, "
                    f"{study_report.pass_count} unchanged"
                ),
            )
        )

    # ---- Stage 3: Learn ----
    if "learn" in active_stages:
        logger.info("=" * 60)
        logger.info("STAGE 3/5: Self-Learn")
        logger.info("=" * 60)
        learn_report = _run_learn(config=config, since=since)
        stage_reports["learn"] = learn_report
        gap_count = sum(
            1
            for f in learn_report.findings
            if f.check == "coverage_gap" and f.status == "WARN"
        )
        master_report.findings.append(
            Finding(
                check="stage_learn",
                target="self_learn",
                status="WARN" if gap_count > 0 else "PASS",
                message=(f"Self-Learn: {gap_count} coverage gap(s) identified"),
            )
        )

    # ---- Stage 4: Verify ----
    if "verify" in active_stages:
        logger.info("=" * 60)
        logger.info("STAGE 4/5: Self-Verify")
        logger.info("=" * 60)
        verify_report = _run_verify(config=config)
        stage_reports["verify"] = verify_report
        master_report.findings.append(
            Finding(
                check="stage_verify",
                target="self_verify",
                status="FAIL" if verify_report.has_failures else "PASS",
                message=(
                    f"Self-Verify: {verify_report.pass_count} pass, "
                    f"{verify_report.fail_count} fail"
                ),
            )
        )

    # ---- Stage 5: Wiki Cross-Check ----
    if "wiki" in active_stages:
        logger.info("=" * 60)
        logger.info("STAGE 5/5: Wiki Cross-Check")
        logger.info("=" * 60)
        wiki_report = _run_wiki(config=config, live=live_wiki, user=wiki_user)
        stage_reports["wiki"] = wiki_report
        wiki_drift = sum(
            1
            for f in wiki_report.findings
            if f.status in ("FAIL", "WARN") and f.check != "wiki_summary"
        )
        master_report.findings.append(
            Finding(
                check="stage_wiki",
                target="self_wiki",
                status="WARN" if wiki_drift > 0 else "PASS",
                message=(
                    f"Wiki Cross-Check: {wiki_report.pass_count} pass, "
                    f"{wiki_report.fail_count} fail, {wiki_drift} drift(s)"
                ),
            )
        )

    # ---- Generate Proposals ----
    logger.info("=" * 60)
    logger.info("GENERATING IMPROVEMENT PROPOSALS")
    logger.info("=" * 60)
    proposals = _generate_proposals(stage_reports, config)

    master_report.findings.append(
        Finding(
            check="proposals",
            target="all_stages",
            status="WARN" if proposals else "PASS",
            message=f"Generated {len(proposals)} improvement proposal(s)",
            details=json.dumps(
                {
                    "total": len(proposals),
                    "high": sum(1 for p in proposals if p.priority == "high"),
                    "medium": sum(1 for p in proposals if p.priority == "medium"),
                    "low": sum(1 for p in proposals if p.priority == "low"),
                }
            ),
        )
    )

    # ---- Save / Apply ----
    if not dry_run:
        if proposals:
            _save_proposals(proposals, config)
        _update_changelog(proposals, stage_reports, config)

        if auto_apply and proposals:
            logger.warning(
                "AUTO-APPLY is enabled — proposals will be marked "
                "as approved (actual file edits require agent execution)"
            )
            for p in proposals:
                p.status = "approved"
            # Re-save with updated statuses
            _save_proposals(proposals, config)
            master_report.findings.append(
                Finding(
                    check="auto_apply",
                    target="proposals",
                    status="WARN",
                    message=(
                        f"Auto-approved {len(proposals)} proposal(s). "
                        f"File edits require agent execution."
                    ),
                    severity="high",
                )
            )
        elif proposals:
            master_report.findings.append(
                Finding(
                    check="approval_gate",
                    target="proposals",
                    status="INFO",
                    message=(
                        f"{len(proposals)} proposal(s) awaiting human review. "
                        f"Review reports/improvement_proposals.json"
                    ),
                )
            )

    return master_report, proposals


# ---------------------------------------------------------------------------
# Text Formatting
# ---------------------------------------------------------------------------


def _format_proposals_text(proposals: List[Proposal]) -> str:
    """Format proposals for human-readable text output."""
    if not proposals:
        return "\n  No improvement proposals generated — all checks passed!\n"

    lines = [f"\n  IMPROVEMENT PROPOSALS ({len(proposals)} total)\n"]
    lines.append("  " + "-" * 58 + "\n")

    for p in proposals:
        icon = {"high": "[!!!]", "medium": "[!! ]", "low": "[!  ]"}.get(
            p.priority, "[   ]"
        )
        lines.append(f"  {icon} {p.id} [{p.action.upper()}] {p.category}\n")
        lines.append(f"       Target: {p.target_file}\n")
        lines.append(f"       {p.description[:120]}\n")
        lines.append(f"       Rationale: {p.rationale[:100]}\n")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="THC Self-Improve: orchestrated improvement pipeline",
    )
    parser.add_argument(
        "--stage",
        choices=["check", "study", "learn", "verify", "wiki"],
        action="append",
        help="Run only specific stage(s) (repeat for multiple)",
    )
    parser.add_argument(
        "--skip",
        choices=["check", "study", "learn", "verify", "wiki"],
        action="append",
        help="Skip specific stage(s) (repeat for multiple)",
    )
    parser.add_argument(
        "--since",
        help="Lookback start date for study/learn (ISO format)",
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Auto-approve proposals (CAUTION: requires agent for file edits)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposals without saving/applying",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save master report to reports/ directory",
    )
    parser.add_argument(
        "--live-wiki",
        action="store_true",
        help="Enable live wiki reads during wiki stage (slow — reads all pages from Confluence)",
    )
    parser.add_argument(
        "--wiki-user",
        default="willychi",
        help="Confluence IDSID for wiki reads (default: willychi)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging("thc_self_improve", level)

    require_approval = not args.auto_apply
    if args.auto_apply:
        logger.warning("=" * 60)
        logger.warning("AUTO-APPLY ENABLED — proposals will be auto-approved")
        logger.warning("File edits still require agent execution")
        logger.warning("=" * 60)

    master_report, proposals = run_improve(
        stages=args.stage,
        skip_stages=args.skip,
        since=args.since,
        auto_apply=args.auto_apply,
        dry_run=args.dry_run,
        live_wiki=args.live_wiki,
        wiki_user=args.wiki_user,
    )

    # Output
    if args.json:
        output = master_report.to_dict()
        output["proposals"] = [p.to_dict() for p in proposals]
        print(json.dumps(output, indent=2))
    else:
        print(master_report.to_text())
        print(_format_proposals_text(proposals))

        if proposals and require_approval:
            print("\n  >> Review proposals in reports/improvement_proposals.json")
            print("  >> Re-run with --auto-apply to approve, or let the agent apply.\n")

    # Save
    if args.save:
        repo_root = find_repo_root()
        tools_dir = repo_root / ".opencode" / "skill" / "fv-thc" / "tools"
        reports_dir = repo_root / ".opencode" / "skill" / "fv-thc" / "reports"
        path = master_report.save(directory=str(reports_dir))
        logger.info("Master report saved to %s", path)

    # Update timestamp
    if not "tools_dir" in locals():
        repo_root = find_repo_root()
        tools_dir = repo_root / ".opencode" / "skill" / "fv-thc" / "tools"
    save_last_run_timestamp("self_improve", tools_dir)
    # Exit code
    has_issues = master_report.has_failures or len(proposals) > 0
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
