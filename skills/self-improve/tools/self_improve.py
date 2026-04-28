#!/usr/bin/env python3
"""Generic Self-Improve Orchestrator: runs check -> verify -> propose pipeline.

Orchestrates the full self-improvement cycle:
1. Run structural checks (self_check.py)
2. Run content assertions (self_verify.py)
3. Generate improvement proposals from findings
4. Optionally apply proposals or save for human review

Usage:
    python self_improve.py <config.json>
    python self_improve.py <config.json> --stages check,verify
    python self_improve.py <config.json> --dry-run
    python self_improve.py <config.json> --json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from common module
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from self_improve_common import Finding, Report, Proposal, load_config


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

def run_check_stage(config: Dict[str, Any]) -> Report:
    """Run structural checks."""
    try:
        from self_check import run_all_checks
        return run_all_checks(config)
    except ImportError:
        report = Report(name="self-check")
        report.add(Finding(
            check="import", target="self_check",
            status="ERROR", message="self_check.py not found",
        ))
        return report


def run_verify_stage(config: Dict[str, Any]) -> Report:
    """Run content assertion tests."""
    try:
        from self_verify import run_all_tests
        return run_all_tests(config)
    except ImportError:
        report = Report(name="self-verify")
        report.add(Finding(
            check="import", target="self_verify",
            status="ERROR", message="self_verify.py not found",
        ))
        return report


STAGES = {
    "check": ("Structural Checks", run_check_stage),
    "verify": ("Content Assertions", run_verify_stage),
}


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------

def generate_proposals(stage_reports: Dict[str, Report],
                       config: Dict[str, Any]) -> List[Proposal]:
    """Generate improvement proposals from stage findings."""
    proposals: List[Proposal] = []
    proposal_id = 0

    max_proposals = config.get("self_improve", {}).get("max_proposals_per_run", 20)

    for stage_name, report in stage_reports.items():
        for finding in report.findings:
            if finding.status in ("FAIL", "ERROR", "WARN"):
                proposal_id += 1
                if proposal_id > max_proposals:
                    break

                # Determine priority from status
                if finding.status == "ERROR":
                    priority = "critical"
                elif finding.status == "FAIL":
                    priority = "high"
                else:
                    priority = "medium"

                proposals.append(Proposal(
                    id=f"P-{proposal_id:03d}",
                    priority=priority,
                    category=stage_name,
                    target_file=finding.target,
                    action="fix" if finding.status in ("FAIL", "ERROR") else "review",
                    description=finding.message,
                    rationale=f"Found by {stage_name} stage",
                    source_findings=[finding.to_dict()],
                    status="proposed",
                ))

    return proposals


# ---------------------------------------------------------------------------
# Proposal I/O
# ---------------------------------------------------------------------------

def save_proposals(proposals: List[Proposal], config: Dict[str, Any]) -> Path:
    """Save proposals to JSON."""
    proposals_path_str = config.get("self_improve", {}).get(
        "proposals_file", "proposals.json"
    )
    repo_root = config.get("_repo_root", Path.cwd())
    if isinstance(repo_root, str):
        repo_root = Path(repo_root)

    base = config.get("paths", {}).get("tools_dir", "")
    if base:
        out_path = repo_root / base / proposals_path_str
    else:
        out_path = Path(proposals_path_str)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(proposals),
        "proposals": [p.to_dict() for p in proposals],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return out_path


def update_changelog(proposals: List[Proposal],
                     stage_reports: Dict[str, Report],
                     config: Dict[str, Any]) -> Path:
    """Append a run summary to the changelog."""
    changelog_str = config.get("self_improve", {}).get(
        "changelog_file", "CHANGELOG.md"
    )
    repo_root = config.get("_repo_root", Path.cwd())
    if isinstance(repo_root, str):
        repo_root = Path(repo_root)

    base = config.get("paths", {}).get("tools_dir", "")
    if base:
        cl_path = repo_root / base / changelog_str
    else:
        cl_path = Path(changelog_str)

    cl_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"\n## Self-Improvement Run — {now}\n\n"]

    for stage_name, report in stage_reports.items():
        summary = report.compute_summary()
        lines.append(f"### {stage_name}\n")
        lines.append(f"- Pass: {summary.get('pass', 0)}, "
                      f"Fail: {summary.get('fail', 0)}, "
                      f"Warn: {summary.get('warn', 0)}, "
                      f"Error: {summary.get('error', 0)}\n")

    lines.append(f"\n**Proposals generated**: {len(proposals)}\n")

    if proposals:
        lines.append("\n| ID | Priority | Target | Action | Description |\n")
        lines.append("|---|---|---|---|---|\n")
        for p in proposals[:20]:
            desc = p.description[:60] + "..." if len(p.description) > 60 else p.description
            lines.append(f"| {p.id} | {p.priority} | {p.target_file} | {p.action} | {desc} |\n")

    # Append or create
    mode = "a" if cl_path.exists() else "w"
    if mode == "w":
        lines.insert(0, "# Self-Improvement Changelog\n\n")

    with open(cl_path, mode, encoding="utf-8") as f:
        f.writelines(lines)

    return cl_path


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_improve(config: Dict[str, Any],
                stages: Optional[List[str]] = None,
                dry_run: bool = False) -> Tuple[Report, List[Proposal]]:
    """Run the full self-improvement pipeline."""
    overall = Report(name="self-improve")
    stage_reports: Dict[str, Report] = {}

    # Determine which stages to run
    run_stages = stages or list(STAGES.keys())

    for stage_name in run_stages:
        if stage_name not in STAGES:
            overall.add(Finding(
                check="orchestrator", target=stage_name,
                status="WARN", message=f"Unknown stage: {stage_name}",
            ))
            continue

        label, runner = STAGES[stage_name]
        print(f"\n{'='*60}")
        print(f"  Stage: {label}")
        print(f"{'='*60}\n")

        report = runner(config)
        stage_reports[stage_name] = report

        # Merge findings into overall report
        for f in report.findings:
            overall.add(f)

        summary = report.compute_summary()
        print(f"  Results: {summary.get('pass', 0)} pass, "
              f"{summary.get('fail', 0)} fail, "
              f"{summary.get('warn', 0)} warn\n")

    # Generate proposals
    proposals = generate_proposals(stage_reports, config)

    if dry_run:
        print(f"\n[DRY RUN] Would generate {len(proposals)} proposals")
    else:
        if proposals:
            props_path = save_proposals(proposals, config)
            print(f"\nProposals saved to: {props_path}")

        cl_path = update_changelog(proposals, stage_reports, config)
        print(f"Changelog updated: {cl_path}")

    return overall, proposals


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generic self-improvement orchestrator"
    )
    parser.add_argument("config", help="Path to self-improvement config JSON")
    parser.add_argument("--stages", "-s", help="Comma-separated stages to run (check,verify)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write proposals/changelog")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", metavar="DIR", help="Save report to directory")
    args = parser.parse_args()

    config = load_config(Path(args.config))

    stages = args.stages.split(",") if args.stages else None

    report, proposals = run_improve(config, stages=stages, dry_run=args.dry_run)

    if args.json:
        output = {
            "report": report.to_dict(),
            "proposals": [p.to_dict() for p in proposals],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  OVERALL SUMMARY")
        print(f"{'='*60}")
        print(report.to_text())
        print(f"\nProposals: {len(proposals)}")

    if args.save:
        save_path = Path(args.save)
        report.save(save_path)

    return 0 if not report.has_failures else 1


if __name__ == "__main__":
    sys.exit(main())
