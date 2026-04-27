#!/usr/bin/env python3
"""
FV-AUDIO Self-Study — External source monitoring for audio-related changes.

Monitors git repositories and external sources for changes that may affect
the audio skill tree, flagging content that needs review or update.

Sources monitored:
  S01  linux_sof         — Sound Open Firmware (SOF) Intel drivers
  S02  linux_hda         — Linux HDA/HD-Audio core drivers
  S03  linux_soundwire   — Linux SoundWire subsystem
  S04  ace_spec          — ACE 4.x EDS specification
  S05  soundwire_spec    — MIPI SoundWire specification
  S06  skill_tree        — Local skill tree file changes

Usage:
    python audio_self_study.py [--since YYYY-MM-DD] [--json] [-v]

Adapted from FV-THC thc_self_study.py.
Owner: huiyingt (Tan Hui Ying)
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_self_common import (
    Report,
    Severity,
    find_repo_root,
    get_all_skill_paths,
    get_last_run_timestamp,
    git_log,
    load_config,
    resolve_path,
    save_last_run_timestamp,
    setup_logging,
    logger,
)


# ---------------------------------------------------------------------------
# Source monitors
# ---------------------------------------------------------------------------

def study_git_source(
    source_name: str,
    source_cfg: dict,
    since: str,
    report: Report,
) -> None:
    """Check a git-based source for recent changes."""
    cid = f"S_{source_name}"
    local_paths = source_cfg.get("local_paths", [])
    remote_url = source_cfg.get("remote_url", "")
    path_filter = source_cfg.get("path_filter", "")

    if not local_paths:
        report.skip(cid, f"No local paths configured for '{source_name}'")
        return

    total_commits = []
    for lp in local_paths:
        try:
            root = find_repo_root()
            commits = git_log(lp, since=since, repo_root=root)
            total_commits.extend(commits)
        except Exception:
            pass  # Path may not exist in this repo — that's OK

    if total_commits:
        subjects = [c["subject"] for c in total_commits[:5]]
        detail = "\n".join(f"  - {s}" for s in subjects)
        if len(total_commits) > 5:
            detail += f"\n  ... and {len(total_commits) - 5} more"
        report.change(
            cid,
            f"{len(total_commits)} commits in '{source_name}' since {since}",
            detail=detail,
            source=remote_url or source_name,
        )
    else:
        report.pass_(cid, f"No changes in '{source_name}' since {since}")


def study_spec_source(
    source_name: str,
    source_cfg: dict,
    report: Report,
) -> None:
    """Check a specification document source (no git, just metadata)."""
    cid = f"S_{source_name}"
    source_doc = source_cfg.get("source_doc", source_cfg.get("source_url", "unknown"))
    last_date = source_cfg.get("last_known_date")
    local_path = source_cfg.get("local_path")

    if local_path:
        full_path = resolve_path(local_path) if not os.path.isabs(local_path) else Path(local_path)
        if full_path.exists():
            mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
            if last_date:
                try:
                    last_dt = datetime.fromisoformat(last_date)
                    if mtime > last_dt:
                        report.change(
                            cid,
                            f"Spec '{source_doc}' modified since last audit ({last_date})",
                            source=str(full_path),
                        )
                        return
                except ValueError:
                    pass
            report.pass_(cid, f"Spec '{source_doc}' unchanged (local copy present)")
        else:
            report.skip(cid, f"Spec '{source_doc}' local path not found: {local_path}")
    else:
        report.skip(cid, f"Spec '{source_doc}' — no local path configured, manual check needed")


def study_skill_tree(cfg: dict, since: str, report: Report) -> None:
    """Check for changes in the audio skill tree itself."""
    cid = "S_skill_tree"
    skill_base = cfg["paths"]["skill_base"]
    commits = git_log(skill_base, since=since)

    if commits:
        subjects = [c["subject"] for c in commits[:5]]
        detail = "\n".join(f"  - {s}" for s in subjects)
        report.change(
            cid,
            f"{len(commits)} commits in skill tree since {since}",
            detail=detail,
            source=skill_base,
        )
    else:
        report.pass_(cid, f"No skill tree changes since {since}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_studies(cfg: dict | None = None, since: str | None = None) -> Report:
    """Run all source monitors and return aggregated report."""
    t0 = time.time()
    cfg = cfg or load_config()
    report = Report(stage="self-study")

    # Determine 'since' date
    if not since:
        last_run = get_last_run_timestamp()
        if last_run:
            since = last_run[:10]  # YYYY-MM-DD
        else:
            since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    sources = cfg.get("sources", {})
    check_interval = sources.get("check_interval_hours", 24)

    # Git-based sources
    git_sources = ["linux_sof", "linux_hda", "linux_soundwire"]
    for src_name in git_sources:
        src_cfg = sources.get(src_name, {})
        if src_cfg and isinstance(src_cfg, dict) and "local_paths" in src_cfg:
            try:
                study_git_source(src_name, src_cfg, since, report)
            except Exception as exc:
                report.error(f"S_{src_name}", f"Failed: {exc}")

    # Spec sources
    spec_sources = ["ace_spec", "soundwire_spec"]
    for src_name in spec_sources:
        src_cfg = sources.get(src_name, {})
        if src_cfg and isinstance(src_cfg, dict):
            try:
                study_spec_source(src_name, src_cfg, report)
            except Exception as exc:
                report.error(f"S_{src_name}", f"Failed: {exc}")

    # Skill tree self-monitoring
    try:
        study_skill_tree(cfg, since, report)
    except Exception as exc:
        report.error("S_skill_tree", f"Failed: {exc}")

    save_last_run_timestamp()
    report.finalize(t0)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="FV-AUDIO external source monitor")
    parser.add_argument("--since", help="Check changes since date (YYYY-MM-DD)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    report = run_all_studies(since=args.since)
    if args.json:
        print(report.to_json())
    else:
        report.print_text()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
