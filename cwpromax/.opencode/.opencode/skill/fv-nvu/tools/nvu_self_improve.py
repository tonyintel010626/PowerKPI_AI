#!/usr/bin/env python3
"""NVU Self-Improve: Orchestrator for NVU skill tree self-improvement pipeline.

Pipeline stages: Check → Study → Learn → Verify → Propose → Apply

Ported from THC self-improvement framework, adapted for NVU IP domain.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nvu_self_common import (
    Finding,
    Report,
    find_repo_root,
    get_all_skill_paths,
    load_config,
    load_last_run_timestamp,
    read_agent_def,
    read_skill,
    save_last_run_timestamp,
    setup_logging,
)

logger = logging.getLogger(__name__)

# ── NVU-specific important term patterns ────────────────────────────

_IMPORTANT_TERM_PATTERNS = [
    # HSD IDs
    (r"HSD\s*#?\s*(\d{8,})", "hsdes"),
    (r"(?:15|16|17|18|19|22)\d{9}", "hsdes"),
    # NVU register names
    (r"NVU2HOST_\w+", "registers"),
    (r"HOST2NVU_\w+", "registers"),
    (r"IPC_\w+", "registers"),
    (r"CRPM_\w+", "registers"),
    # Device IDs
    (r"0x[0-9A-Fa-f]{4}", "platform"),
    (r"DID\s*[:=]\s*0x[0-9A-Fa-f]+", "platform"),
    # NVU sub-IP components
    (r"VPX2\b", "inference"),
    (r"NPX6\b", "inference"),
    (r"NNA\b", "inference"),
    (r"Altek\b", "camera"),
    (r"CV-ISP\b", "camera"),
    (r"VC9000\b", "camera"),
    (r"MJPEG\b", "camera"),
    (r"FlexNoC\b", "platform"),
    (r"IOSF2AXI\b", "registers"),
    # DMA terms
    (r"AXI\s*DMA\b", "dma"),
    (r"DMA_CH\w+", "dma"),
    (r"boot\s*DMA\b", "dma"),
    # Power terms
    (r"D0i[0-3]\b", "power"),
    (r"D3\s*(?:hot|cold)\b", "power"),
    (r"IPAPG\b", "power"),
    (r"Lid[_-]?Closed\b", "power"),
    (r"clock\s*gat(?:e|ing)\b", "power"),
    (r"power\s*gat(?:e|ing)\b", "power"),
    (r"LTR\b", "power"),
    # Firmware terms
    (r"ESE\b", "firmware"),
    (r"boot\s*ROM\b", "firmware"),
    (r"BUP\b", "firmware"),
    (r"SVN\b", "firmware"),
    (r"IMR\b", "firmware"),
    # BIOS terms
    (r"BIOS\s*knob\b", "bios"),
    (r"Setup\s*Option\b", "bios"),
    (r"strap\b", "bios"),
    (r"fuse\b", "bios"),
    (r"BRP\b", "bios"),
    # Camera/MIPI terms
    (r"MIPI\b", "camera"),
    (r"CSI-?2\b", "camera"),
    (r"C-PHY\b", "camera"),
    (r"D-PHY\b", "camera"),
    (r"PHY\s*sharing\b", "camera"),
    # Debug terms
    (r"DTF\b", "debug"),
    (r"VISA\b", "debug"),
    (r"NorthPeak\b", "debug"),
    (r"SysT\b", "debug"),
    (r"watchdog\b", "debug"),
    (r"ECC\b", "debug"),
    # Driver terms
    (r"BAR0\b", "driver"),
    (r"PCI\s*config\b", "driver"),
    (r"MSI\b", "driver"),
    (r"ACPI\b", "driver"),
]


# ── Proposal class ──────────────────────────────────────────────────


class Proposal:
    """A proposed improvement to the NVU skill tree."""

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
        id: str,
        priority: str,
        category: str,
        target_file: str,
        action: str,
        description: str,
        rationale: str = "",
        source_findings: Optional[List[str]] = None,
        status: str = "proposed",
    ):
        self.id = id
        self.priority = priority
        self.category = category
        self.target_file = target_file
        self.action = action
        self.description = description
        self.rationale = rationale
        self.source_findings = source_findings or []
        self.status = status

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


# ── Stage runners ───────────────────────────────────────────────────


def _run_check(config: Dict) -> Report:
    """Run structural checks (delegates to nvu_self_check)."""
    try:
        from nvu_self_check import run_all_checks

        return run_all_checks(config)
    except ImportError as e:
        logger.error("Cannot import nvu_self_check: %s", e)
        report = Report(name="NVU Self-Check (import error)")
        report.findings.append(
            Finding(
                check="import",
                target="nvu_self_check",
                status="ERROR",
                message=str(e),
                severity="critical",
            )
        )
        return report


def _run_study(config: Dict, since: Optional[datetime] = None) -> Report:
    """Run external source study (delegates to nvu_self_study)."""
    try:
        from nvu_self_study import run_all_studies

        return run_all_studies(config, since=since)
    except ImportError as e:
        logger.error("Cannot import nvu_self_study: %s", e)
        report = Report(name="NVU Self-Study (import error)")
        report.findings.append(
            Finding(
                check="import",
                target="nvu_self_study",
                status="ERROR",
                message=str(e),
                severity="critical",
            )
        )
        return report


def _run_learn(config: Dict, since: Optional[datetime] = None) -> Report:
    """Run knowledge gap detection (delegates to nvu_self_learn)."""
    try:
        from nvu_self_learn import run_learn

        return run_learn(config=config, since=since)
    except ImportError as e:
        logger.error("Cannot import nvu_self_learn: %s", e)
        report = Report(name="NVU Self-Learn (import error)")
        report.findings.append(
            Finding(
                check="import",
                target="nvu_self_learn",
                status="ERROR",
                message=str(e),
                severity="critical",
            )
        )
        return report


def _run_verify(config: Dict) -> Report:
    """Run content assertions (delegates to nvu_self_verify)."""
    try:
        from nvu_self_verify import run_all_tests

        return run_all_tests(config)
    except ImportError as e:
        logger.error("Cannot import nvu_self_verify: %s", e)
        report = Report(name="NVU Self-Verify (import error)")
        report.findings.append(
            Finding(
                check="import",
                target="nvu_self_verify",
                status="ERROR",
                message=str(e),
                severity="critical",
            )
        )
        return report


# ── Coverage gap detection ──────────────────────────────────────────


def _run_coverage_gap(config: Dict) -> List[Finding]:
    """Scan skill files for coverage gaps using important term patterns."""
    findings: List[Finding] = []

    skill_paths = get_all_skill_paths(config)
    if not skill_paths:
        findings.append(
            Finding(
                check="coverage_gap",
                target="skill_files",
                status="ERROR",
                message="No skill paths found",
                severity="critical",
            )
        )
        return findings

    # Collect all skill content
    all_content = ""
    for name in skill_paths:
        content_dict = read_skill(name, config)
        skill_text = content_dict.get("skill")
        if skill_text:
            all_content += skill_text + "\n"

    # Also check agent definition
    agent_def = read_agent_def(config)
    if agent_def:
        all_content += agent_def + "\n"

    # Extract terms from important patterns
    term_coverage: Dict[str, Dict[str, Any]] = {}
    for pattern, category in _IMPORTANT_TERM_PATTERNS:
        matches = re.findall(pattern, all_content, re.IGNORECASE)
        if not matches:
            term_coverage[pattern] = {
                "category": category,
                "found": False,
                "count": 0,
            }

    # Report uncovered patterns (with deduplication)
    seen_categories: Dict[str, int] = {}
    for pattern, info in term_coverage.items():
        if not info["found"]:
            cat = info["category"]
            seen_categories[cat] = seen_categories.get(cat, 0) + 1

    for cat, count in seen_categories.items():
        if count > 3:
            # Only warn if significant number of terms missing from a category
            findings.append(
                Finding(
                    check="coverage_gap",
                    target=f"category:{cat}",
                    status="WARN",
                    message=f"Coverage gap in '{cat}': {count} important term patterns not found in any skill file",
                    severity="minor",
                    details=f"category={cat}, missing_patterns={count}",
                )
            )

    if not findings:
        findings.append(
            Finding(
                check="coverage_gap",
                target="all_skills",
                status="PASS",
                message="No significant coverage gaps detected",
                severity="info",
            )
        )

    return findings


# ── Proposal generation ─────────────────────────────────────────────


def _map_source_to_skill(source: str) -> str:
    """Map an external source name or skill path to the most relevant skill file.

    Handles both external source names (e.g. 'has_document') and direct skill
    paths (e.g. 'fv-nvu/registers', 'registers/SKILL.md').
    """
    # Direct skill path: fv-nvu/<skill> or fv-nvu/<skill>/SKILL.md
    if source.startswith("fv-nvu/"):
        parts = source.removeprefix("fv-nvu/").split("/")
        if parts and parts[0]:
            return parts[0]

    # Skill path without prefix: <skill>/SKILL.md
    nvu_skills = {
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
    }
    first_part = source.split("/")[0]
    if first_part in nvu_skills:
        return first_part

    # Named external source mapping
    mapping = {
        "has_document": "registers",
        "integration_has": "platform",
        "e2e_has": "camera",
        "excel_data": "registers",
        "bios_requirements": "bios",
        "linux_kernel": "driver",
        "windows_driver": "driver",
    }
    return mapping.get(source, "platform")


def _generate_proposals(
    check_report: Optional[Report],
    study_report: Optional[Report],
    learn_report: Optional[Report],
    verify_report: Optional[Report],
    coverage_findings: List[Finding],
    config: Dict,
    max_proposals: int = 20,
) -> List[Proposal]:
    """Generate improvement proposals from all pipeline findings."""
    proposals: List[Proposal] = []
    proposal_id = 0

    def next_id() -> str:
        nonlocal proposal_id
        proposal_id += 1
        return f"NVU-PROP-{proposal_id:03d}"

    # From check failures → structural fixes
    if check_report:
        for f in check_report.findings:
            if f.status == "FAIL":
                proposals.append(
                    Proposal(
                        id=next_id(),
                        priority="high" if f.severity == "critical" else "medium",
                        category="structural",
                        target_file=f.target,
                        action="fix_structure",
                        description=f"Fix structural issue: {f.message}",
                        rationale=f"Self-check '{f.check}' reported FAIL",
                        source_findings=[str(f)],
                    )
                )
            if len(proposals) >= max_proposals:
                return proposals

    # From study changes → content updates
    if study_report:
        for f in study_report.findings:
            if f.status == "CHANGE":
                skill = _map_source_to_skill(
                    f.target.split(":")[0] if ":" in f.target else f.target
                )
                proposals.append(
                    Proposal(
                        id=next_id(),
                        priority="medium",
                        category="content_update",
                        target_file=f"fv-nvu/{skill}/SKILL.md",
                        action="update_content",
                        description=f"Update skill with external source change: {f.message}",
                        rationale=f"External source '{f.target}' has changes",
                        source_findings=[str(f)],
                    )
                )
            if len(proposals) >= max_proposals:
                return proposals

    # From learn gaps → coverage additions
    if learn_report:
        for f in learn_report.findings:
            if f.status in ("FAIL", "WARN") and "gap" in f.check.lower():
                proposals.append(
                    Proposal(
                        id=next_id(),
                        priority="low",
                        category="coverage_add",
                        target_file=f.target,
                        action="add_coverage",
                        description=f"Add coverage for knowledge gap: {f.message}",
                        rationale=f"Self-learn detected gap in '{f.target}'",
                        source_findings=[str(f)],
                    )
                )
            if len(proposals) >= max_proposals:
                return proposals

    # From verify failures → accuracy fixes
    if verify_report:
        for f in verify_report.findings:
            if f.status == "FAIL":
                proposals.append(
                    Proposal(
                        id=next_id(),
                        priority="high",
                        category="accuracy_fix",
                        target_file=f.target,
                        action="fix_accuracy",
                        description=f"Fix content assertion failure: {f.message}",
                        rationale=f"Self-verify test '{f.check}' reported FAIL",
                        source_findings=[str(f)],
                    )
                )
            if len(proposals) >= max_proposals:
                return proposals

    # From coverage gaps → gap fixes
    for f in coverage_findings:
        if f.status == "WARN":
            proposals.append(
                Proposal(
                    id=next_id(),
                    priority="low",
                    category="coverage_gap",
                    target_file=f.target,
                    action="add_terms",
                    description=f"Address coverage gap: {f.message}",
                    rationale="Coverage gap analysis detected missing term patterns",
                    source_findings=[str(f)],
                )
            )
        if len(proposals) >= max_proposals:
            return proposals

    return proposals


def _save_proposals(proposals: List[Proposal], output_dir: Path) -> Path:
    """Save proposals to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"nvu_proposals_{timestamp}.json"

    data = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_proposals": len(proposals),
        "proposals": [p.to_dict() for p in proposals],
    }

    filepath.write_text(json.dumps(data, indent=2))
    logger.info("Saved %d proposals to %s", len(proposals), filepath)
    return filepath


def _update_changelog(proposals: List[Proposal], config: Dict) -> None:
    """Append summary entry to changelog file."""
    repo_root = find_repo_root()
    if not repo_root:
        return

    skill_base = config.get("paths", {}).get("skill_base", ".opencode/skill/fv-nvu")
    changelog_path = Path(repo_root) / skill_base / "CHANGELOG.md"

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n## Self-Improve Run — {timestamp}\n\n"
    entry += f"- **Proposals generated**: {len(proposals)}\n"

    by_category: Dict[str, int] = {}
    for p in proposals:
        by_category[p.category] = by_category.get(p.category, 0) + 1
    for cat, count in sorted(by_category.items()):
        entry += f"  - {cat}: {count}\n"

    by_priority: Dict[str, int] = {}
    for p in proposals:
        by_priority[p.priority] = by_priority.get(p.priority, 0) + 1
    entry += f"- **By priority**: {json.dumps(by_priority)}\n"

    try:
        if changelog_path.exists():
            existing = changelog_path.read_text(encoding="utf-8")
            changelog_path.write_text(existing + entry, encoding="utf-8")
        else:
            changelog_path.write_text(
                f"# NVU Skill Tree Changelog\n{entry}", encoding="utf-8"
            )
        logger.info("Updated changelog: %s", changelog_path)
    except Exception as e:
        logger.warning("Could not update changelog: %s", e)


# ── Main orchestrator ───────────────────────────────────────────────


def run_improve(
    config: Dict,
    stages: Optional[List[str]] = None,
    skip_stages: Optional[List[str]] = None,
    since: Optional[datetime] = None,
    auto_apply: bool = False,
    dry_run: bool = False,
    max_proposals: int = 20,
) -> Dict[str, Any]:
    """Run the full self-improvement pipeline.

    Returns dict with stage reports, proposals, and summary.
    """
    all_stages = ["check", "study", "learn", "verify", "coverage"]
    skip = set(skip_stages or [])

    if stages:
        active_stages = [s for s in stages if s in all_stages and s not in skip]
    else:
        active_stages = [s for s in all_stages if s not in skip]

    if since is None:
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)

    logger.info(
        "Running NVU Self-Improve pipeline: stages=%s, since=%s",
        active_stages,
        since.isoformat(),
    )

    # Run stages
    check_report: Optional[Report] = None
    study_report: Optional[Report] = None
    learn_report: Optional[Report] = None
    verify_report: Optional[Report] = None
    coverage_findings: List[Finding] = []

    stage_results: Dict[str, Any] = {}

    if "check" in active_stages:
        logger.info("=== Stage 1: CHECK ===")
        check_report = _run_check(config)
        stage_results["check"] = check_report.compute_summary()
        logger.info(
            "Check: %d findings (%d pass, %d fail)",
            len(check_report.findings),
            check_report.pass_count,
            check_report.fail_count,
        )

    if "study" in active_stages:
        logger.info("=== Stage 2: STUDY ===")
        study_report = _run_study(config, since)
        stage_results["study"] = study_report.compute_summary()
        changes = sum(1 for f in study_report.findings if f.status == "CHANGE")
        logger.info(
            "Study: %d findings (%d changes)", len(study_report.findings), changes
        )

    if "learn" in active_stages:
        logger.info("=== Stage 3: LEARN ===")
        learn_report = _run_learn(config, since)
        stage_results["learn"] = learn_report.compute_summary()
        logger.info("Learn: %d findings", len(learn_report.findings))

    if "verify" in active_stages:
        logger.info("=== Stage 4: VERIFY ===")
        verify_report = _run_verify(config)
        stage_results["verify"] = verify_report.compute_summary()
        logger.info(
            "Verify: %d findings (%d pass, %d fail)",
            len(verify_report.findings),
            verify_report.pass_count,
            verify_report.fail_count,
        )

    if "coverage" in active_stages:
        logger.info("=== Stage 5: COVERAGE GAP ===")
        coverage_findings = _run_coverage_gap(config)
        stage_results["coverage"] = {
            "total": len(coverage_findings),
            "gaps": sum(1 for f in coverage_findings if f.status == "WARN"),
        }
        logger.info("Coverage: %d findings", len(coverage_findings))

    # Generate proposals
    logger.info("=== Generating Proposals ===")
    proposals = _generate_proposals(
        check_report,
        study_report,
        learn_report,
        verify_report,
        coverage_findings,
        config,
        max_proposals,
    )
    logger.info("Generated %d proposals", len(proposals))

    # Save proposals (unless dry run)
    proposal_file: Optional[str] = None
    if proposals and not dry_run:
        repo_root = find_repo_root()
        if repo_root:
            skill_base = config.get("paths", {}).get(
                "skill_base", ".opencode/skill/fv-nvu"
            )
            reports_dir = Path(repo_root) / skill_base / "reports"
            proposal_path = _save_proposals(proposals, reports_dir)
            proposal_file = str(proposal_path)

            # Update changelog
            _update_changelog(proposals, config)

    # Build result summary
    result = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "stages_run": active_stages,
        "stage_results": stage_results,
        "proposals": {
            "total": len(proposals),
            "by_priority": {},
            "by_category": {},
            "items": [p.to_dict() for p in proposals],
        },
        "proposal_file": proposal_file,
        "dry_run": dry_run,
    }

    # Count by priority/category
    for p in proposals:
        result["proposals"]["by_priority"][p.priority] = (
            result["proposals"]["by_priority"].get(p.priority, 0) + 1
        )
        result["proposals"]["by_category"][p.category] = (
            result["proposals"]["by_category"].get(p.category, 0) + 1
        )

    return result


# ── CLI ─────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NVU Self-Improve: Full self-improvement pipeline orchestrator"
    )
    parser.add_argument(
        "--stage",
        "-s",
        choices=["check", "study", "learn", "verify", "coverage"],
        nargs="+",
        help="Specific stages to run (default: all)",
    )
    parser.add_argument(
        "--skip",
        choices=["check", "study", "learn", "verify", "coverage"],
        nargs="+",
        help="Stages to skip",
    )
    parser.add_argument(
        "--since",
        default="7d",
        help="Time window for study/learn (e.g., 7d, 2w, 1m)",
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Auto-apply proposals (not implemented)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate proposals without saving"
    )
    parser.add_argument(
        "--max-proposals", type=int, default=20, help="Maximum proposals to generate"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", type=str, help="Save full result to file")
    parser.add_argument(
        "--update-timestamp", action="store_true", help="Update last-run timestamp"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    setup_logging("DEBUG" if args.verbose else "INFO")

    config = load_config()
    if not config:
        print("ERROR: Could not load self_improvement_config.json", file=sys.stderr)
        return 2

    # Parse since
    from nvu_self_study import parse_since

    since = parse_since(args.since)

    # Run pipeline
    result = run_improve(
        config,
        stages=args.stage,
        skip_stages=args.skip,
        since=since,
        auto_apply=args.auto_apply,
        dry_run=args.dry_run,
        max_proposals=args.max_proposals,
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n" + "=" * 60)
        print("NVU SELF-IMPROVEMENT PIPELINE RESULTS")
        print("=" * 60)
        print(f"Timestamp: {result['timestamp']}")
        print(f"Stages run: {', '.join(result['stages_run'])}")
        print()

        for stage, summary in result.get("stage_results", {}).items():
            print(f"  [{stage.upper()}] {json.dumps(summary)}")

        print()
        proposals = result.get("proposals", {})
        print(f"Proposals: {proposals.get('total', 0)}")
        if proposals.get("by_priority"):
            print(f"  By priority: {json.dumps(proposals['by_priority'])}")
        if proposals.get("by_category"):
            print(f"  By category: {json.dumps(proposals['by_category'])}")

        if proposals.get("items"):
            print()
            for p in proposals["items"][:10]:  # Show top 10
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    p["priority"], "⚪"
                )
                print(f"  {icon} [{p['id']}] {p['description']}")
                print(f"       → {p['target_file']} ({p['action']})")

        if result.get("proposal_file"):
            print(f"\nProposals saved to: {result['proposal_file']}")
        print()

    # Save full result
    if args.save:
        Path(args.save).write_text(json.dumps(result, indent=2), encoding="utf-8")
        logger.info("Full result saved to %s", args.save)

    # Update timestamp
    if args.update_timestamp:
        save_last_run_timestamp("self_improve")
        logger.info("Updated last-run timestamp for self_improve")

    # Exit code: 0 if no high-priority proposals, 1 if any
    has_high = any(
        p["priority"] == "high" for p in result.get("proposals", {}).get("items", [])
    )
    return 1 if has_high else 0


if __name__ == "__main__":
    sys.exit(main())
