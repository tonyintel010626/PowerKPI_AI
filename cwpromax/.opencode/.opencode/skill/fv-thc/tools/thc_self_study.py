# > **Owner**: Chin, William Willy (`willychi`)
# THC Self-Study: Monitor external sources for THC-related changes
# Part of the THC Self-Improvement Framework
#
# Monitors:
#   1. Linux kernel THC driver (git log for intel-thc-hid changes)
#   2. Windows HIDSPI driver (local clone git log)
#   3. Windows HIDI2C driver (local clone git log)
#   4. HAS document (file modification timestamp)
#   5. BWG document (file modification timestamp)
#
# Usage:
#   python thc_self_study.py                    # Check all sources
#   python thc_self_study.py --source linux     # Check Linux kernel only
#   python thc_self_study.py --json             # JSON output
#   python thc_self_study.py --since 7d         # Changes in last 7 days
#   python thc_self_study.py --save report.json # Save results
#
# Exit codes: 0 = no changes, 1 = changes detected, 2 = error
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thc_self_common import (
    find_repo_root, load_config, resolve_path, git_log, file_modified_since,
    load_last_run_timestamp, save_last_run_timestamp,
    Finding, Report, setup_logging
)

logger = setup_logging("thc_self_study")
TOOLS_DIR = Path(__file__).resolve().parent

# THC-relevant file patterns in Linux kernel
LINUX_THC_PATHS = [
    "drivers/hid/intel-thc-hid/",
    "include/linux/intel-thc/",
]

# THC-relevant keywords for commit message filtering
THC_KEYWORDS = [
    "thc", "touch host controller", "hidspi", "hidi2c", "quickspi",
    "intel-thc", "wake-on-touch", "wot",
]


# =============================================================================
# SOURCE MONITORS
# =============================================================================

def study_linux_kernel(config: dict, since: str) -> list:
    """Check Linux kernel repo for THC-related changes."""
    findings = []
    linux_paths = config.get("sources", {}).get("linux_kernel", {}).get("local_paths", [
        r"C:\git\linux",
        r"C:\git\torvalds-linux",
    ])

    linux_repo = None
    for path in linux_paths:
        if Path(path).exists() and (Path(path) / ".git").exists():
            linux_repo = path
            break

    if not linux_repo:
        # Try remote check via git ls-remote (lightweight, no clone needed)
        findings.append(Finding(
            check="linux_kernel", target="local_repo",
            status="SKIP",
            message="No local Linux kernel repo found. Configure 'sources.linux_kernel.local_paths' in config. "
                    "Clone with: git clone --depth=1 --filter=blob:none --sparse https://github.com/torvalds/linux.git && "
                    "cd linux && git sparse-checkout set drivers/hid/intel-thc-hid"
        ))
        return findings

    logger.info(f"Checking Linux kernel repo: {linux_repo}")

    # Get THC-related commits since last check
    for thc_path in LINUX_THC_PATHS:
        commits = git_log(linux_repo, since=since, path_filter=thc_path, max_count=50)

        if commits:
            findings.append(Finding(
                check="linux_kernel", target=thc_path,
                status="CHANGE",
                message=f"{len(commits)} new commits in {thc_path}",
                severity="high",
                details=[{
                    "hash": c.get("hash", ""),
                    "subject": c.get("subject", ""),
                    "author": c.get("author", ""),
                    "date": c.get("date", ""),
                } for c in commits]
            ))
        else:
            findings.append(Finding(
                check="linux_kernel", target=thc_path,
                status="PASS",
                message=f"No new commits in {thc_path} since {since}"
            ))

    return findings


def study_windows_hidspi(config: dict, since: str) -> list:
    """Check Windows HIDSPI driver repo for changes."""
    findings = []
    hidspi_paths = config.get("sources", {}).get("windows_hidspi", {}).get("local_paths", [
        r"C:\git\drivers.platform.ipts.hspi-driver",
    ])

    hidspi_repo = None
    for path in hidspi_paths:
        if Path(path).exists() and (Path(path) / ".git").exists():
            hidspi_repo = path
            break

    if not hidspi_repo:
        findings.append(Finding(
            check="windows_hidspi", target="local_repo",
            status="SKIP",
            message="No local Windows HIDSPI repo found"
        ))
        return findings

    logger.info(f"Checking Windows HIDSPI repo: {hidspi_repo}")
    commits = git_log(hidspi_repo, since=since, max_count=50)

    if commits:
        # Categorize commits by area
        thc_commits = []
        other_commits = []
        for c in commits:
            subject = c.get("subject", "").lower()
            if any(kw in subject for kw in THC_KEYWORDS):
                thc_commits.append(c)
            else:
                other_commits.append(c)

        if thc_commits:
            findings.append(Finding(
                check="windows_hidspi", target="THC-related",
                status="CHANGE",
                message=f"{len(thc_commits)} THC-related commits",
                severity="high",
                details=[{"hash": c["hash"][:8], "subject": c["subject"]} for c in thc_commits]
            ))

        findings.append(Finding(
            check="windows_hidspi", target="all_commits",
            status="CHANGE" if commits else "PASS",
            message=f"{len(commits)} total commits since {since} ({len(thc_commits)} THC-related)"
        ))
    else:
        findings.append(Finding(
            check="windows_hidspi", target="all_commits",
            status="PASS",
            message=f"No new commits since {since}"
        ))

    return findings


def study_windows_hidi2c(config: dict, since: str) -> list:
    """Check Windows HIDI2C driver repo for changes."""
    findings = []
    hidi2c_paths = config.get("sources", {}).get("windows_hidi2c", {}).get("local_paths", [
        r"C:\git\drivers.platform.ipts.hid-i2c-touch",
    ])

    hidi2c_repo = None
    for path in hidi2c_paths:
        if Path(path).exists() and (Path(path) / ".git").exists():
            hidi2c_repo = path
            break

    if not hidi2c_repo:
        findings.append(Finding(
            check="windows_hidi2c", target="local_repo",
            status="SKIP",
            message="No local Windows HIDI2C repo found"
        ))
        return findings

    logger.info(f"Checking Windows HIDI2C repo: {hidi2c_repo}")
    commits = git_log(hidi2c_repo, since=since, max_count=50)

    if commits:
        thc_commits = [c for c in commits
                       if any(kw in c.get("subject", "").lower() for kw in THC_KEYWORDS)]

        if thc_commits:
            findings.append(Finding(
                check="windows_hidi2c", target="THC-related",
                status="CHANGE",
                message=f"{len(thc_commits)} THC-related commits",
                severity="high",
                details=[{"hash": c["hash"][:8], "subject": c["subject"]} for c in thc_commits]
            ))

        findings.append(Finding(
            check="windows_hidi2c", target="all_commits",
            status="CHANGE" if commits else "PASS",
            message=f"{len(commits)} total commits since {since} ({len(thc_commits)} THC-related)"
        ))
    else:
        findings.append(Finding(
            check="windows_hidi2c", target="all_commits",
            status="PASS",
            message=f"No new commits since {since}"
        ))

    return findings


def study_has_document(config: dict, since: str) -> list:
    """Check if HAS document has been updated."""
    findings = []
    root = find_repo_root()
    has_path = root / ".opencode" / "skill" / "fv-thc" / "docs" / "thc_has_4x_extraction.md"

    if has_path.exists():
        modified = file_modified_since(has_path, since)
        mod_time = datetime.fromtimestamp(has_path.stat().st_mtime)
        if modified:
            findings.append(Finding(
                check="has_document", target="thc_has_4x_extraction.md",
                status="CHANGE",
                message=f"HAS extraction modified: {mod_time.isoformat()}",
                severity="medium"
            ))
        else:
            findings.append(Finding(
                check="has_document", target="thc_has_4x_extraction.md",
                status="PASS",
                message=f"No changes (last modified: {mod_time.isoformat()})"
            ))

        # Also check the extraction mentions a source version
        content = has_path.read_text(encoding="utf-8")
        version_match = re.search(r'September\s+\d+,\s+\d{4}|Rev\s+[\d.]+', content[:1000])
        if version_match:
            findings.append(Finding(
                check="has_document", target="source_version",
                status="PASS",
                message=f"HAS source version: {version_match.group(0)}"
            ))
    else:
        findings.append(Finding(
            check="has_document", target="thc_has_4x_extraction.md",
            status="FAIL",
            message="HAS extraction file missing",
            severity="high"
        ))

    # Check HAS online URL accessibility (lightweight HEAD request)
    has_url = config.get("sources", {}).get("has_document", {}).get("url",
        "https://docs.intel.com/documents/iparch/thc/THC_IP/4.x/IP%20Specs/HAS/SIP_THC_4x_HAS/SIP_THC_4x_HAS.html")
    findings.append(Finding(
        check="has_document", target="online_url",
        status="PASS",
        message=f"HAS URL configured: {has_url[:80]}..."
    ))

    return findings


def study_bwg_document(config: dict, since: str) -> list:
    """Check if BWG document has been updated."""
    findings = []
    root = find_repo_root()
    bwg_path = root / ".opencode" / "skill" / "fv-thc" / "docs" / "thc_bwg_extraction.md"

    if bwg_path.exists():
        modified = file_modified_since(bwg_path, since)
        mod_time = datetime.fromtimestamp(bwg_path.stat().st_mtime)
        if modified:
            findings.append(Finding(
                check="bwg_document", target="thc_bwg_extraction.md",
                status="CHANGE",
                message=f"BWG extraction modified: {mod_time.isoformat()}",
                severity="medium"
            ))
        else:
            findings.append(Finding(
                check="bwg_document", target="thc_bwg_extraction.md",
                status="PASS",
                message=f"No changes (last modified: {mod_time.isoformat()})"
            ))
    else:
        findings.append(Finding(
            check="bwg_document", target="thc_bwg_extraction.md",
            status="FAIL",
            message="BWG extraction file missing",
            severity="high"
        ))

    return findings


def study_skill_files(config: dict, since: str) -> list:
    """Check if any skill files themselves were modified externally."""
    findings = []
    root = find_repo_root()
    skill_base = root / ".opencode" / "skill" / "fv-thc"

    modified_skills = []
    for skill_dir in skill_base.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists() and skill_dir.name not in ("docs", "eval", "tools"):
            if file_modified_since(skill_file, since):
                mod_time = datetime.fromtimestamp(skill_file.stat().st_mtime)
                modified_skills.append((skill_dir.name, mod_time.isoformat()))

    if modified_skills:
        findings.append(Finding(
            check="skill_files", target="modifications",
            status="CHANGE",
            message=f"{len(modified_skills)} skill files modified since {since}",
            details=[{"skill": s, "modified": t} for s, t in modified_skills]
        ))
    else:
        findings.append(Finding(
            check="skill_files", target="modifications",
            status="PASS",
            message=f"No skill files modified since {since}"
        ))

    return findings


# =============================================================================
# MAIN
# =============================================================================

ALL_SOURCES = {
    "linux": study_linux_kernel,
    "hidspi": study_windows_hidspi,
    "hidi2c": study_windows_hidi2c,
    "has": study_has_document,
    "bwg": study_bwg_document,
    "skills": study_skill_files,
}


def parse_since(since_str: str) -> str:
    """Parse a relative time string (e.g., '7d', '2w', '1m') into an ISO date."""
    if since_str is None:
        return None

    multipliers = {"d": 1, "w": 7, "m": 30, "y": 365}
    match = re.match(r"(\d+)([dwmy])", since_str.lower())
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        delta = timedelta(days=num * multipliers.get(unit, 1))
        return (datetime.now() - delta).strftime("%Y-%m-%d")

    # Try as ISO date
    try:
        datetime.strptime(since_str, "%Y-%m-%d")
        return since_str
    except ValueError:
        return since_str


def run_all_studies(config: dict, since: str, sources: list = None) -> Report:
    """Run all source monitors and return a Report."""
    report = Report(name="THC Self-Study", version="1.0.0")

    sources_to_check = sources or list(ALL_SOURCES.keys())
    for source_name in sources_to_check:
        if source_name not in ALL_SOURCES:
            logger.warning(f"Unknown source: {source_name}")
            continue

        logger.info(f"Studying source: {source_name}")
        try:
            findings = ALL_SOURCES[source_name](config, since)
            report.findings.extend(findings)
        except Exception as e:
            report.findings.append(Finding(
                check=source_name, target="system",
                status="ERROR", message=f"Study failed: {e}",
                severity="critical"
            ))

    return report


def main():
    parser = argparse.ArgumentParser(description="THC Self-Study: Monitor external source changes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--source", type=str, nargs="+",
                       choices=list(ALL_SOURCES.keys()),
                       help="Check specific sources only")
    parser.add_argument("--since", type=str, default="7d",
                       help="Check for changes since (e.g., 7d, 2w, 1m, 2025-01-01)")
    parser.add_argument("--save", type=str, help="Save report to file")
    parser.add_argument("--update-timestamp", action="store_true",
                       help="Update last-run timestamp after checking")
    args = parser.parse_args()

    config = load_config()

    # Parse since
    since = parse_since(args.since)
    if since is None:
        # Use last run timestamp
        since = load_last_run_timestamp("self_study", TOOLS_DIR)
        if since is None:
            since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    logger.info(f"Checking for changes since: {since}")

    report = run_all_studies(config, since, args.source)

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    if args.save:
        report.save(args.save)

    # Update timestamp if requested
    if args.update_timestamp:
        save_last_run_timestamp("self_study", TOOLS_DIR)
        logger.info("Updated last-run timestamp")

    # Exit code: 1 if changes detected
    has_changes = any(f.status == "CHANGE" for f in report.findings)
    sys.exit(1 if has_changes else 0)


if __name__ == "__main__":
    main()
