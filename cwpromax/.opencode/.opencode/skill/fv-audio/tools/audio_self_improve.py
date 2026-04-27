#!/usr/bin/env python3
"""
audio_self_improve.py — FV-AUDIO Self-Improvement Orchestrator

Chains all self-improvement stages:
  Check → Study → Learn → Verify → Propose → (Approve) → Apply

Adapted from FV-THC thc_self_improve.py for the audio validation domain.

Usage:
    python audio_self_improve.py [--stage STAGE] [--skip STAGE] [--auto-apply]
                                  [--dry-run] [--json] [--save] [-v]
"""
from __future__ import annotations

__author__ = "huiyingt (Tan Hui Ying)"

import argparse
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sibling imports
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

try:
    from audio_self_common import (
        Finding, Report, find_repo_root, load_config,
        resolve_path, get_skill_path, read_skill,
        setup_logging, save_last_run_timestamp,
    )
except ImportError:
    print("ERROR: audio_self_common.py not found — run from tools/ directory", file=sys.stderr)
    sys.exit(2)

logger = logging.getLogger("audio.self_improve")

# ---------------------------------------------------------------------------
# Stage runners — import sibling modules on demand
# ---------------------------------------------------------------------------

def _run_check(config: dict, repo_root: Path, **kw) -> Report:
    """Run structural checks via audio_self_check."""
    try:
        from audio_self_check import run_all_checks
        return run_all_checks(config)
    except ImportError:
        r = Report("check")
        r.add(Finding("import", "SKIP", "audio_self_check.py not available"))
        return r
    except Exception as exc:
        r = Report("check")
        r.add(Finding("check_error", "ERROR", str(exc)))
        return r


def _run_study(config: dict, repo_root: Path, since: Optional[str] = None, **kw) -> Report:
    """Run external-source monitoring via audio_self_study."""
    try:
        from audio_self_study import run_all_studies
        return run_all_studies(config, since=since)
    except ImportError:
        r = Report("study")
        r.add(Finding("import", "SKIP", "audio_self_study.py not available"))
        return r
    except Exception as exc:
        r = Report("study")
        r.add(Finding("study_error", "ERROR", str(exc)))
        return r


def _run_learn(config: dict, repo_root: Path, **kw) -> Report:
    """Run knowledge-gap detection via audio_self_learn."""
    try:
        from audio_self_learn import run_learn
        return run_learn(config)
    except ImportError:
        r = Report("learn")
        r.add(Finding("import", "SKIP", "audio_self_learn.py not available"))
        return r
    except Exception as exc:
        r = Report("learn")
        r.add(Finding("learn_error", "ERROR", str(exc)))
        return r


def _run_verify(config: dict, repo_root: Path, **kw) -> Report:
    """Run eval-based verification via audio_self_verify."""
    try:
        from audio_self_verify import run_all_tests
        return run_all_tests(config)
    except ImportError:
        r = Report("verify")
        r.add(Finding("import", "SKIP", "audio_self_verify.py not available"))
        return r
    except Exception as exc:
        r = Report("verify")
        r.add(Finding("verify_error", "ERROR", str(exc)))
        return r


# ---------------------------------------------------------------------------
# Important term patterns — audio domain
# ---------------------------------------------------------------------------

_IMPORTANT_TERM_PATTERNS: List[Tuple[str, str]] = [
    # Architecture
    (r"\bACE\s*4\.?[0x]?\b", "ace_architecture"),
    (r"\bPCI\s*0[:.]31[:.]3\b", "pci_bdf"),
    (r"\bPCD-[HS]\b", "pcd_variant"),
    (r"\bDSP\b", "dsp_core"),
    (r"\bSRAM\b", "sram_management"),
    # Protocols
    (r"\bHDA\b", "hda_protocol"),
    (r"\bSoundWire\b", "soundwire_protocol"),
    (r"\bSDW\b", "soundwire_protocol"),
    (r"\bDMIC\b", "dmic_interface"),
    (r"\bSSP\b", "ssp_i2s"),
    (r"\bI2S\b", "ssp_i2s"),
    (r"\bUAOL\b", "usb_audio_offload"),
    # Power
    (r"\bD0i3\b", "d0i3_power"),
    (r"\bD3\b", "d3_power"),
    (r"\bS0ix\b", "s0ix_integration"),
    (r"\bCGPG\b", "clock_power_gating"),
    (r"\bLTR\b", "ltr_latency"),
    (r"\bCPPM\b", "cppm"),
    # Codecs / Devices
    (r"\bALC\d+\b", "realtek_codec"),
    (r"\bRealtek\b", "realtek_codec"),
    (r"\bAIo?C\b", "aioc_codec"),
    (r"\bALC712\b", "alc712"),
    (r"\bALC1320\b", "alc1320"),
    # Features
    (r"\bWoV\b", "wake_on_voice"),
    (r"\bCRO\b", "clock_ring_oscillator"),
    (r"\bMicrophone\s*Privacy\b", "mic_privacy"),
    (r"\bJack\s*Detect\b", "jack_detection"),
    (r"\bDisplay\s*Audio\b", "display_audio"),
    (r"\biDisp\b", "display_audio"),
    (r"\bBT\s*(?:Audio\s*)?Offload\b", "bt_audio_offload"),
    (r"\bBCLK\b", "bclk_config"),
    # Platform
    (r"\bNVL\b", "novalake_platform"),
    (r"\bNovalake\b", "novalake_platform"),
    (r"\bPTL\b", "panther_lake"),
]

# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------

class Proposal:
    """A single improvement proposal."""
    __slots__ = (
        "id", "priority", "category", "target_file",
        "action", "description", "rationale", "source_findings", "status",
    )

    def __init__(self, **kw):
        self.id: str = kw.get("id", uuid.uuid4().hex[:8])
        self.priority: str = kw.get("priority", "medium")
        self.category: str = kw.get("category", "unknown")
        self.target_file: str = kw.get("target_file", "")
        self.action: str = kw.get("action", "review")
        self.description: str = kw.get("description", "")
        self.rationale: str = kw.get("rationale", "")
        self.source_findings: list = kw.get("source_findings", [])
        self.status: str = kw.get("status", "proposed")

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ---------------------------------------------------------------------------
# Coverage gap detection
# ---------------------------------------------------------------------------

def _detect_coverage_gaps(
    config: dict, repo_root: Path
) -> List[Finding]:
    """Check that important domain terms appear in skill content."""
    findings: List[Finding] = []
    skill_base = resolve_path(config.get("paths", {}).get("skill_base", ".opencode/skill/fv-audio"), repo_root)
    if not skill_base.is_dir():
        findings.append(Finding("coverage_gap", "ERROR", f"Skill base not found: {skill_base}"))
        return findings

    # Gather all skill text
    all_text = ""
    for skill_name in config.get("skills", []):
        sp = get_skill_path(skill_name, config)
        if sp and sp.exists():
            all_text += read_skill(skill_name, config) or ""

    # Also read agent definition
    agent_path = resolve_path(config.get("paths", {}).get("agent_def", ".opencode/agent/FV/FV-AUDIO.md"), repo_root)
    if agent_path.exists():
        all_text += agent_path.read_text(encoding="utf-8", errors="replace")

    # Check each important term
    for pattern, category in _IMPORTANT_TERM_PATTERNS:
        if not re.search(pattern, all_text, re.IGNORECASE):
            findings.append(Finding(
                f"coverage_gap.{category}",
                "WARN",
                f"Important term pattern '{pattern}' ({category}) not found in any skill content",
            ))

    if not findings:
        findings.append(Finding("coverage_gaps", "PASS", "All important audio terms covered in skill content"))

    return findings


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------

def _map_source_to_skill(source_name: str) -> str:
    """Map source repo/file name to a target skill file."""
    mapping = {
        "linux_sof": "dsp/SKILL.md",
        "linux_hda": "hda/SKILL.md",
        "linux_soundwire": "soundwire/SKILL.md",
        "linux_dmic": "dmic/SKILL.md",
        "linux_ssp": "bt-offload/SKILL.md",
        "windows_audio": "SKILL.md",
        "has_document": "SKILL.md",
        "bwg_document": "SKILL.md",
    }
    return mapping.get(source_name, "SKILL.md")


def _generate_proposals(
    stage_reports: Dict[str, Report], config: dict, repo_root: Path,
) -> List[Proposal]:
    """Map findings from all stages into improvement proposals."""
    proposals: List[Proposal] = []
    max_proposals = config.get("self_improve", {}).get("max_proposals_per_run", 20)

    for stage_name, report in stage_reports.items():
        for f in report.findings:
            if f.severity == "PASS":
                continue

            proposal = None

            if stage_name == "check" and f.severity == "FAIL":
                proposal = Proposal(
                    priority="high",
                    category="structural",
                    target_file=f.detail.split(":")[-1].strip() if ":" in f.detail else "",
                    action="fix",
                    description=f"Structural check failed: {f.check_id}",
                    rationale=f.detail,
                    source_findings=[f.to_dict()],
                )
            elif stage_name == "study" and f.severity == "CHANGE":
                target = _map_source_to_skill(f.check_id.replace("source.", ""))
                proposal = Proposal(
                    priority="medium",
                    category="content_update",
                    target_file=target,
                    action="update",
                    description=f"External source changed: {f.check_id}",
                    rationale=f.detail,
                    source_findings=[f.to_dict()],
                )
            elif stage_name == "learn" and "coverage_gap" in f.check_id and f.severity == "WARN":
                proposal = Proposal(
                    priority="medium",
                    category="coverage",
                    action="add",
                    description=f"Coverage gap: {f.check_id}",
                    rationale=f.detail,
                    source_findings=[f.to_dict()],
                )
            elif stage_name == "learn" and "feedback" in f.check_id:
                proposal = Proposal(
                    priority="high" if f.severity == "FAIL" else "medium",
                    category="feedback",
                    action="review",
                    description=f"User feedback: {f.check_id}",
                    rationale=f.detail,
                    source_findings=[f.to_dict()],
                )
            elif stage_name == "verify" and f.severity == "FAIL":
                proposal = Proposal(
                    priority="high",
                    category="accuracy",
                    action="fix",
                    description=f"Verification failed: {f.check_id}",
                    rationale=f.detail,
                    source_findings=[f.to_dict()],
                )

            if proposal:
                proposals.append(proposal)
                if len(proposals) >= max_proposals:
                    break

        if len(proposals) >= max_proposals:
            break

    return proposals


# ---------------------------------------------------------------------------
# Proposal persistence
# ---------------------------------------------------------------------------

def _save_proposals(proposals: List[Proposal], config: dict, repo_root: Path) -> Path:
    """Save proposals to JSON file."""
    reports_dir = repo_root / config["paths"]["skill_base"] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    proposal_file = config.get("self_improve", {}).get(
        "proposal_file", "reports/improvement_proposals.json"
    )
    out_path = repo_root / config["paths"]["skill_base"] / proposal_file
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "proposal_count": len(proposals),
        "proposals": [p.to_dict() for p in proposals],
    }
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved %d proposals to %s", len(proposals), out_path)
    return out_path


def _update_changelog(proposals: List[Proposal], config: dict, repo_root: Path) -> Path:
    """Append an entry to the improvement changelog."""
    changelog_file = config.get("self_improve", {}).get(
        "changelog_file", "reports/improvement_changelog.md"
    )
    out_path = repo_root / config["paths"]["skill_base"] / changelog_file
    out_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"\n## Run: {timestamp}\n\n",
        f"**Proposals generated**: {len(proposals)}\n\n",
    ]
    if proposals:
        lines.append("| ID | Priority | Category | Action | Description |\n")
        lines.append("|-----|----------|----------|--------|-------------|\n")
        for p in proposals:
            lines.append(
                f"| {p.id} | {p.priority} | {p.category} | {p.action} | {p.description} |\n"
            )
    else:
        lines.append("No proposals generated — all checks passed.\n")
    lines.append("\n")

    with open(out_path, "a", encoding="utf-8") as fh:
        fh.writelines(lines)

    logger.info("Updated changelog: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

ALL_STAGES = ["check", "study", "learn", "verify", "coverage"]

_STAGE_RUNNERS = {
    "check": _run_check,
    "study": _run_study,
    "learn": _run_learn,
    "verify": _run_verify,
}


def run_improve(
    stages: Optional[List[str]] = None,
    skip: Optional[List[str]] = None,
    since: Optional[str] = None,
    auto_apply: bool = False,
    dry_run: bool = False,
    save: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run the full self-improvement pipeline.

    Returns a dict with stage reports, proposals, and overall summary.
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    repo_root = find_repo_root()
    config = load_config()

    active_stages = stages or list(ALL_STAGES)
    if skip:
        active_stages = [s for s in active_stages if s not in skip]

    logger.info("=== FV-AUDIO Self-Improvement Pipeline ===")
    logger.info("Active stages: %s", ", ".join(active_stages))

    stage_reports: Dict[str, Report] = {}

    # Run each stage
    for stage in active_stages:
        if stage == "coverage":
            # Coverage is a special in-process stage, not a separate module
            continue
        runner = _STAGE_RUNNERS.get(stage)
        if not runner:
            logger.warning("Unknown stage: %s — skipping", stage)
            continue
        logger.info("--- Stage: %s ---", stage)
        kw = {}
        if stage == "study" and since:
            kw["since"] = since
        stage_reports[stage] = runner(config, repo_root, **kw)
        report = stage_reports[stage]
        # Report.summary is a @property (returns dict with UPPERCASE keys),
        # not a method — never call it as report.summary().
        if isinstance(report, Report):
            summary = report.summary
        elif isinstance(report, dict):
            summary = report
        else:
            summary = {}
        total = sum(summary.values()) if summary else 0
        logger.info(
            "  %s: %d findings (PASS=%d FAIL=%d WARN=%d ERROR=%d SKIP=%d)",
            stage,
            total,
            summary.get("PASS", 0), summary.get("FAIL", 0), summary.get("WARN", 0),
            summary.get("ERROR", 0), summary.get("SKIP", 0),
        )

    # Coverage gap detection (in-process)
    if "coverage" in active_stages:
        logger.info("--- Stage: coverage ---")
        cov_report = Report("coverage")
        for f in _detect_coverage_gaps(config, repo_root):
            cov_report.add(f)
        stage_reports["coverage"] = cov_report
        cs = cov_report.summary
        cs_total = sum(cs.values()) if cs else 0
        logger.info("  coverage: %d findings (PASS=%d WARN=%d)", cs_total, cs.get("PASS", 0), cs.get("WARN", 0))

    # Generate proposals
    logger.info("--- Generating proposals ---")
    proposals = _generate_proposals(stage_reports, config, repo_root)
    logger.info("Generated %d proposals", len(proposals))

    # Save
    if save and not dry_run:
        _save_proposals(proposals, config, repo_root)
        _update_changelog(proposals, config, repo_root)
        save_last_run_timestamp()

    # Build result
    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages_run": active_stages,
        "stage_summaries": {},
        "proposals": [p.to_dict() for p in proposals],
        "proposal_count": len(proposals),
    }
    total_fail = 0
    for sname, report in stage_reports.items():
        # Report.summary is a @property (returns dict with UPPERCASE keys)
        if isinstance(report, Report):
            s = report.summary
        elif isinstance(report, dict):
            s = report
        else:
            s = {}
        result["stage_summaries"][sname] = s
        total_fail += s.get("FAIL", s.get("fail", 0))

    result["overall"] = "FAIL" if (total_fail > 0 or len(proposals) > 0) else "PASS"

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="FV-AUDIO Self-Improvement Orchestrator"
    )
    parser.add_argument(
        "--stage", action="append", dest="stages",
        help="Run only specific stage(s). Repeat for multiple.",
    )
    parser.add_argument(
        "--skip", action="append", dest="skip",
        help="Skip specific stage(s). Repeat for multiple.",
    )
    parser.add_argument(
        "--since",
        help="ISO date for study stage lookback (default: use config interval)",
    )
    parser.add_argument("--auto-apply", action="store_true", help="Auto-apply proposals (use with caution)")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without saving results")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--save", action="store_true", default=True, help="Save proposals and changelog (default)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    result = run_improve(
        stages=args.stages,
        skip=args.skip,
        since=args.since,
        auto_apply=args.auto_apply,
        dry_run=args.dry_run,
        save=args.save,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"FV-AUDIO Self-Improvement — {result['overall']}")
        print(f"{'='*60}")
        print(f"Stages run: {', '.join(result['stages_run'])}")
        print()
        for sname, s in result["stage_summaries"].items():
            print(f"  {sname:12s}  PASS={s.get('PASS',0)}  FAIL={s.get('FAIL',0)}  WARN={s.get('WARN',0)}  "
                  f"ERROR={s.get('ERROR',0)}  SKIP={s.get('SKIP',0)}")
        print()
        print(f"Proposals: {result['proposal_count']}")
        for p in result["proposals"]:
            print(f"  [{p['priority']:6s}] {p['category']:16s}  {p['action']:8s}  {p['description']}")
        print(f"\nOverall: {result['overall']}")

    return 1 if result["overall"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
