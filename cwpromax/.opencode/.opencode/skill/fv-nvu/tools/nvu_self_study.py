#!/usr/bin/env python3
"""NVU Self-Study: External source monitoring for NVU skill tree.

Monitors external sources (HAS documents, driver repos, skill files)
for changes since last run, flagging updates that may require
skill tree maintenance.

Ported from THC self-study framework, adapted for NVU IP domain.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from nvu_self_common import (
    Finding,
    Report,
    file_modified_since,
    find_pattern_in_file,
    find_repo_root,
    get_all_skill_paths,
    git_log,
    load_config,
    load_last_run_timestamp,
    save_last_run_timestamp,
    setup_logging,
)

logger = logging.getLogger(__name__)

# ── NVU-specific constants ──────────────────────────────────────────

# Keywords that indicate NVU-relevant changes in external sources
NVU_KEYWORDS = [
    "nvu",
    "neural vision",
    "npx6",
    "vpx2",
    "nna",
    "mipi",
    "csi2",
    "csi-2",
    "c-phy",
    "d-phy",
    "altek",
    "cv-isp",
    "isp",
    "usb camera",
    "camera offload",
    "vc9000",
    "mjpeg",
    "sram",
    "imr",
    "smmu",
    "dma",
    "axi dma",
    "designware",
    "iosf2axi",
    "iosf",
    "crpm",
    "ipapg",
    "power gating",
    "ipc",
    "nvu2host",
    "host2nvu",
    "ese",
    "secure boot",
    "boot rom",
    "dtf",
    "visa",
    "northpeak",
    "watchdog",
    "hpet",
    "rtc",
    "flexnoc",
    "arteris",
    "wake-on-face",
    "wof",
    "faceid",
]

# NVU Linux kernel paths (TBD — no upstream NVU driver yet)
LINUX_NVU_PATHS: List[str] = [
    # Placeholder — update when NVU Linux driver lands
    # "drivers/misc/intel-nvu/",
    # "include/linux/intel-nvu/",
]

# NVU Windows driver paths (TBD — no public driver repo path yet)
WINDOWS_NVU_PATHS: List[str] = [
    # Placeholder — update when NVU Windows driver repo is available
]


# ── Source monitor functions ────────────────────────────────────────


def study_linux_kernel(config: Dict, since: Optional[datetime] = None) -> List[Finding]:
    """Check Linux kernel for NVU-related changes."""
    findings: List[Finding] = []

    if not LINUX_NVU_PATHS:
        findings.append(
            Finding(
                check="study_linux_kernel",
                target="linux_kernel",
                status="SKIP",
                message="No Linux NVU driver paths configured yet (driver not upstream)",
                severity="info",
            )
        )
        return findings

    linux_cfg = config.get("sources", {}).get("linux_kernel", {})
    repo_path = linux_cfg.get("path", "")

    if not repo_path or not Path(repo_path).exists():
        findings.append(
            Finding(
                check="study_linux_kernel",
                target="linux_kernel",
                status="SKIP",
                message=f"Linux kernel repo not found at: {repo_path}",
                severity="info",
            )
        )
        return findings

    # Check git log for NVU-related commits
    since_str = since.strftime("%Y-%m-%d") if since else "4 weeks ago"
    for pf in LINUX_NVU_PATHS:
        commits = git_log(
            path=pf,
            n=50,
            since=since_str,
        )
        if commits:
            for commit in commits:
                subject_lower = commit.get("subject", "").lower()
                if any(kw in subject_lower for kw in NVU_KEYWORDS):
                    findings.append(
                        Finding(
                            check="study_linux_kernel",
                            target=f"linux:{pf}",
                            status="CHANGE",
                            message=f"NVU-relevant kernel commit: {commit.get('subject', '')}",
                            severity="moderate",
                            details=f"hash={commit.get('hash', '')}, date={commit.get('date', '')}, author={commit.get('author', '')}",
                        )
                    )

    if not any(f.status == "CHANGE" for f in findings):
        findings.append(
            Finding(
                check="study_linux_kernel",
                target="linux_kernel",
                status="PASS",
                message="No NVU-relevant Linux kernel changes detected",
                severity="info",
            )
        )

    return findings


def study_windows_driver(
    config: Dict, since: Optional[datetime] = None
) -> List[Finding]:
    """Check Windows driver repo for NVU-related changes."""
    findings: List[Finding] = []

    if not WINDOWS_NVU_PATHS:
        findings.append(
            Finding(
                check="study_windows_driver",
                target="windows_driver",
                status="SKIP",
                message="No Windows NVU driver paths configured yet",
                severity="info",
            )
        )
        return findings

    win_cfg = config.get("sources", {}).get("windows_driver", {})
    repo_path = win_cfg.get("path", "")

    if not repo_path or not Path(repo_path).exists():
        findings.append(
            Finding(
                check="study_windows_driver",
                target="windows_driver",
                status="SKIP",
                message=f"Windows driver repo not found at: {repo_path}",
                severity="info",
            )
        )
        return findings

    since_str = since.strftime("%Y-%m-%d") if since else "4 weeks ago"
    for pf in WINDOWS_NVU_PATHS:
        commits = git_log(
            path=pf,
            n=50,
            since=since_str,
        )
        if commits:
            for commit in commits:
                subject_lower = commit.get("subject", "").lower()
                if any(kw in subject_lower for kw in NVU_KEYWORDS):
                    findings.append(
                        Finding(
                            check="study_windows_driver",
                            target=f"windows:{pf}",
                            status="CHANGE",
                            message=f"NVU-relevant Windows driver commit: {commit.get('subject', '')}",
                            severity="moderate",
                            details=f"hash={commit.get('hash', '')}, date={commit.get('date', '')}, author={commit.get('author', '')}",
                        )
                    )

    if not any(f.status == "CHANGE" for f in findings):
        findings.append(
            Finding(
                check="study_windows_driver",
                target="windows_driver",
                status="PASS",
                message="No NVU-relevant Windows driver changes detected",
                severity="info",
            )
        )

    return findings


def study_has_document(config: Dict, since: Optional[datetime] = None) -> List[Finding]:
    """Check NVU HAS document for modifications."""
    findings: List[Finding] = []

    sources = config.get("sources", {})
    has_cfg = sources.get("has_document", {})
    has_path_str = has_cfg.get("path", "")

    if not has_path_str:
        findings.append(
            Finding(
                check="study_has_document",
                target="has_document",
                status="SKIP",
                message="No HAS document path configured",
                severity="info",
            )
        )
        return findings

    has_path = Path(has_path_str)
    if not has_path.exists():
        findings.append(
            Finding(
                check="study_has_document",
                target=str(has_path),
                status="WARN",
                message=f"HAS document not found: {has_path}",
                severity="moderate",
            )
        )
        return findings

    # Check modification time
    if since and file_modified_since(
        str(has_path),
        since.strftime("%Y-%m-%d") if isinstance(since, datetime) else str(since),
    ):
        mod_time = datetime.fromtimestamp(has_path.stat().st_mtime, tz=timezone.utc)
        findings.append(
            Finding(
                check="study_has_document",
                target=str(has_path.name),
                status="CHANGE",
                message=f"HAS document modified since last check: {mod_time.isoformat()}",
                severity="moderate",
                details=f"path={has_path}, size={has_path.stat().st_size} bytes",
            )
        )
    else:
        findings.append(
            Finding(
                check="study_has_document",
                target=str(has_path.name),
                status="PASS",
                message="HAS document unchanged since last check",
                severity="info",
            )
        )

    # Also check Integration HAS and E2E HAS
    for src_key, src_label in [
        ("integration_has", "Integration HAS"),
        ("e2e_has", "E2E HAS"),
    ]:
        src_cfg = sources.get(src_key, {})
        src_path_str = src_cfg.get("path", "")
        if not src_path_str:
            continue
        src_path = Path(src_path_str)
        if not src_path.exists():
            findings.append(
                Finding(
                    check="study_has_document",
                    target=src_label,
                    status="WARN",
                    message=f"{src_label} not found: {src_path}",
                    severity="info",
                )
            )
            continue

        if since and file_modified_since(
            str(src_path),
            since.strftime("%Y-%m-%d") if isinstance(since, datetime) else str(since),
        ):
            mod_time = datetime.fromtimestamp(src_path.stat().st_mtime, tz=timezone.utc)
            findings.append(
                Finding(
                    check="study_has_document",
                    target=src_label,
                    status="CHANGE",
                    message=f"{src_label} modified since last check: {mod_time.isoformat()}",
                    severity="moderate",
                    details=f"path={src_path}, size={src_path.stat().st_size} bytes",
                )
            )
        else:
            findings.append(
                Finding(
                    check="study_has_document",
                    target=src_label,
                    status="PASS",
                    message=f"{src_label} unchanged since last check",
                    severity="info",
                )
            )

    return findings


def study_excel_data(config: Dict, since: Optional[datetime] = None) -> List[Finding]:
    """Check NVU Excel HAS data for modifications."""
    findings: List[Finding] = []

    sources = config.get("sources", {})
    excel_cfg = sources.get("excel_data", {})
    excel_path_str = excel_cfg.get("path", "")

    if not excel_path_str:
        findings.append(
            Finding(
                check="study_excel_data",
                target="excel_data",
                status="SKIP",
                message="No Excel data path configured",
                severity="info",
            )
        )
        return findings

    excel_path = Path(excel_path_str)
    if not excel_path.exists():
        findings.append(
            Finding(
                check="study_excel_data",
                target=str(excel_path),
                status="WARN",
                message=f"Excel data file not found: {excel_path}",
                severity="moderate",
            )
        )
        return findings

    if since and file_modified_since(
        str(excel_path),
        since.strftime("%Y-%m-%d") if isinstance(since, datetime) else str(since),
    ):
        mod_time = datetime.fromtimestamp(excel_path.stat().st_mtime, tz=timezone.utc)
        findings.append(
            Finding(
                check="study_excel_data",
                target=str(excel_path.name),
                status="CHANGE",
                message=f"Excel HAS data modified since last check: {mod_time.isoformat()}",
                severity="moderate",
                details=f"path={excel_path}, size={excel_path.stat().st_size} bytes, sheets={excel_cfg.get('sheets', [])}",
            )
        )
    else:
        findings.append(
            Finding(
                check="study_excel_data",
                target=str(excel_path.name),
                status="PASS",
                message="Excel HAS data unchanged since last check",
                severity="info",
            )
        )

    return findings


def study_bios_requirements(
    config: Dict, since: Optional[datetime] = None
) -> List[Finding]:
    """Check BIOS requirements document for modifications."""
    findings: List[Finding] = []

    sources = config.get("sources", {})
    bios_cfg = sources.get("bios_requirements", {})
    bios_path_str = bios_cfg.get("path", "")

    if not bios_path_str:
        findings.append(
            Finding(
                check="study_bios_requirements",
                target="bios_requirements",
                status="SKIP",
                message="No BIOS requirements path configured",
                severity="info",
            )
        )
        return findings

    bios_path = Path(bios_path_str)
    if not bios_path.exists():
        findings.append(
            Finding(
                check="study_bios_requirements",
                target=str(bios_path),
                status="WARN",
                message=f"BIOS requirements document not found: {bios_path}",
                severity="moderate",
            )
        )
        return findings

    if since and file_modified_since(
        str(bios_path),
        since.strftime("%Y-%m-%d") if isinstance(since, datetime) else str(since),
    ):
        mod_time = datetime.fromtimestamp(bios_path.stat().st_mtime, tz=timezone.utc)
        findings.append(
            Finding(
                check="study_bios_requirements",
                target=str(bios_path.name),
                status="CHANGE",
                message=f"BIOS requirements modified since last check: {mod_time.isoformat()}",
                severity="moderate",
                details=f"path={bios_path}, size={bios_path.stat().st_size} bytes",
            )
        )
    else:
        findings.append(
            Finding(
                check="study_bios_requirements",
                target=str(bios_path.name),
                status="PASS",
                message="BIOS requirements unchanged since last check",
                severity="info",
            )
        )

    return findings


def study_skill_files(config: Dict, since: Optional[datetime] = None) -> List[Finding]:
    """Check all NVU skill files for recent modifications."""
    findings: List[Finding] = []

    skill_paths = get_all_skill_paths(config)
    if not skill_paths:
        findings.append(
            Finding(
                check="study_skill_files",
                target="skill_files",
                status="ERROR",
                message="No skill paths found",
                severity="critical",
            )
        )
        return findings

    modified_skills: List[str] = []
    for name, path in skill_paths.items():
        if (
            path.exists()
            and since
            and file_modified_since(
                str(path),
                since.strftime("%Y-%m-%d")
                if isinstance(since, datetime)
                else str(since),
            )
        ):
            modified_skills.append(name)
            mod_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            findings.append(
                Finding(
                    check="study_skill_files",
                    target=f"fv-nvu/{name}",
                    status="CHANGE",
                    message=f"Skill file modified: {name}/SKILL.md ({mod_time.isoformat()})",
                    severity="info",
                )
            )

    if not modified_skills:
        findings.append(
            Finding(
                check="study_skill_files",
                target="skill_files",
                status="PASS",
                message=f"No skill files modified since last check ({len(skill_paths)} checked)",
                severity="info",
            )
        )

    return findings


# ── Source registry ─────────────────────────────────────────────────

ALL_SOURCES: Dict[str, Callable] = {
    "linux_kernel": study_linux_kernel,
    "windows_driver": study_windows_driver,
    "has_document": study_has_document,
    "excel_data": study_excel_data,
    "bios_requirements": study_bios_requirements,
    "skill_files": study_skill_files,
}


# ── Time parsing ────────────────────────────────────────────────────


def parse_since(since_str: str) -> datetime:
    """Parse relative time string (7d, 2w, 1m) or ISO date to datetime."""
    since_str = since_str.strip().lower()

    # Relative time patterns
    match = re.match(r"^(\d+)([dwmh])$", since_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        now = datetime.now(tz=timezone.utc)
        if unit == "h":
            return now - timedelta(hours=value)
        elif unit == "d":
            return now - timedelta(days=value)
        elif unit == "w":
            return now - timedelta(weeks=value)
        elif unit == "m":
            return now - timedelta(days=value * 30)
        else:
            return now - timedelta(days=7)

    # Try ISO format
    try:
        return datetime.fromisoformat(since_str)
    except ValueError:
        pass

    # Default: 7 days ago
    logger.warning("Could not parse since='%s', defaulting to 7 days ago", since_str)
    return datetime.now(tz=timezone.utc) - timedelta(days=7)


# ── Orchestrator ────────────────────────────────────────────────────


def run_all_studies(
    config: Dict,
    since: Optional[datetime] = None,
    sources: Optional[List[str]] = None,
) -> Report:
    """Run all or selected source studies."""
    report = Report(name="NVU Self-Study", version="1.0")

    # Default since: 7 days ago
    if since is None:
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)

    # Filter sources
    if sources:
        selected = {k: v for k, v in ALL_SOURCES.items() if k in sources}
    else:
        selected = ALL_SOURCES

    logger.info(
        "Running %d source studies (since %s)", len(selected), since.isoformat()
    )

    for source_name, study_fn in selected.items():
        logger.info("Studying: %s", source_name)
        try:
            findings = study_fn(config, since)
            report.findings.extend(findings)
        except Exception as e:
            logger.error("Error studying %s: %s", source_name, e)
            report.findings.append(
                Finding(
                    check=f"study_{source_name}",
                    target=source_name,
                    status="ERROR",
                    message=f"Study failed: {e}",
                    severity="critical",
                )
            )

    return report


# ── CLI ─────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NVU Self-Study: Monitor external sources for changes"
    )
    parser.add_argument(
        "--source",
        "-s",
        choices=list(ALL_SOURCES.keys()),
        nargs="+",
        help="Specific sources to study (default: all)",
    )
    parser.add_argument(
        "--since",
        default="7d",
        help="Time window for change detection (e.g., 7d, 2w, 1m, ISO date)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", type=str, help="Save report to file")
    parser.add_argument(
        "--update-timestamp",
        action="store_true",
        help="Update last-run timestamp after study",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    setup_logging("DEBUG" if args.verbose else "INFO")

    config = load_config()
    if not config:
        print("ERROR: Could not load self_improvement_config.json", file=sys.stderr)
        return 2

    since = parse_since(args.since)
    report = run_all_studies(config, since=since, sources=args.source)

    # Output
    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    # Save
    if args.save:
        report.save(Path(args.save))
        logger.info("Report saved to %s", args.save)

    # Update timestamp
    if args.update_timestamp:
        save_last_run_timestamp("self_study")
        logger.info("Updated last-run timestamp for self_study")

    # Exit code: 0 = successful run (changes detected is a valid result, not an error)
    # Non-zero only for tool crashes / unrecoverable errors (handled by exception)
    return 0


if __name__ == "__main__":
    sys.exit(main())
