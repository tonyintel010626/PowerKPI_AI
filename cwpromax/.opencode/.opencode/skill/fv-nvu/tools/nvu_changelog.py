#!/usr/bin/env python3
"""NVU CHANGELOG Auto-Generation Tool.

Generates CHANGELOG.md from git log + tool validation outputs.
Tracks what changed per commit for reviewers and auditors.

Usage:
    python nvu_changelog.py                  # Generate from git log
    python nvu_changelog.py --since v0.1     # Since a tag/commit
    python nvu_changelog.py --validate       # Also run validators and embed results
    python nvu_changelog.py --json           # JSON output
    python nvu_changelog.py --dry-run        # Preview without writing file
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CHANGELOG_PATH = SKILL_ROOT / "CHANGELOG.md"
TOOLS_DIR = SKILL_ROOT / "tools"
# Git commands need repo root, not skill root
REPO_ROOT = SKILL_ROOT.parent.parent.parent  # .opencode/skill/fv-nvu -> repo root

logger = logging.getLogger("nvu_changelog")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def run_git(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    """Run a git command and return (exit_code, stdout)."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(cwd or SKILL_ROOT),
        )
        return result.returncode, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


def get_nvu_commits(
    since: Optional[str] = None, max_count: int = 50
) -> List[Dict[str, str]]:
    """Get commits touching fv-nvu skill tree."""
    args = [
        "log",
        f"--max-count={max_count}",
        "--format=%H|%h|%an|%ae|%aI|%s",
        "--",
        ".opencode/skill/fv-nvu/",
        ".opencode/agent/FV/FV-NVU.md",
    ]
    if since:
        args.insert(
            1, f"--since={since}" if re.match(r"\d{4}-", since) else f"{since}..HEAD"
        )

    rc, output = run_git(args, cwd=REPO_ROOT)
    if rc != 0 or not output:
        return []

    commits = []
    for line in output.splitlines():
        parts = line.split("|", 5)
        if len(parts) == 6:
            commits.append(
                {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "email": parts[3],
                    "date": parts[4],
                    "subject": parts[5],
                }
            )
    return commits


def get_commit_stats(commit_hash: str) -> Dict[str, Any]:
    """Get file change stats for a commit."""
    rc, output = run_git(
        [
            "diff-tree",
            "--no-commit-id",
            "-r",
            "--numstat",
            commit_hash,
            "--",
            ".opencode/skill/fv-nvu/",
            ".opencode/agent/FV/FV-NVU.md",
        ]
    )
    if rc != 0:
        return {"files": 0, "additions": 0, "deletions": 0, "file_list": []}

    files = []
    total_add = 0
    total_del = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            add = int(parts[0]) if parts[0] != "-" else 0
            delete = int(parts[1]) if parts[1] != "-" else 0
            total_add += add
            total_del += delete
            files.append(
                {
                    "path": parts[2],
                    "additions": add,
                    "deletions": delete,
                }
            )

    return {
        "files": len(files),
        "additions": total_add,
        "deletions": total_del,
        "file_list": files,
    }


def categorize_commit(subject: str) -> str:
    """Categorize a commit by its subject line."""
    subject_lower = subject.lower()
    if any(w in subject_lower for w in ["fix", "bug", "patch", "hotfix"]):
        return "Bug Fix"
    if any(w in subject_lower for w in ["new", "add", "create", "port", "implement"]):
        return "New Feature"
    if any(
        w in subject_lower for w in ["refactor", "cleanup", "clean up", "reorganize"]
    ):
        return "Refactor"
    if any(w in subject_lower for w in ["doc", "readme", "changelog", "comment"]):
        return "Documentation"
    if any(w in subject_lower for w in ["test", "eval", "assert", "valid"]):
        return "Testing"
    if any(w in subject_lower for w in ["round", "improvement", "enhance", "update"]):
        return "Enhancement"
    return "Other"


# ---------------------------------------------------------------------------
# Validation snapshot
# ---------------------------------------------------------------------------
def run_validation_snapshot() -> Dict[str, Any]:
    """Run core validators and capture results."""
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "tools": {},
    }

    validators = [
        (
            "self_check",
            [sys.executable, str(TOOLS_DIR / "nvu_self_check.py"), "--json"],
        ),
        (
            "self_verify",
            [sys.executable, str(TOOLS_DIR / "nvu_self_verify.py"), "--json"],
        ),
        (
            "delegation_check",
            [sys.executable, str(TOOLS_DIR / "nvu_delegation_check.py")],
        ),
    ]

    for name, cmd in validators:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(SKILL_ROOT),
            )
            # Try to parse JSON output
            try:
                data = json.loads(result.stdout)
                passed = data.get("passed", data.get("pass", 0))
                failed = data.get("failed", data.get("fail", 0))
                warns = data.get("warnings", data.get("warn", 0))
            except (json.JSONDecodeError, ValueError):
                # Parse text output
                passed = len(re.findall(r"PASS", result.stdout))
                failed = len(re.findall(r"FAIL", result.stdout))
                warns = len(re.findall(r"WARN", result.stdout))

            snapshot["tools"][name] = {
                "exit_code": result.returncode,
                "passed": passed,
                "failed": failed,
                "warnings": warns,
                "status": "PASS" if result.returncode == 0 else "FAIL",
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            snapshot["tools"][name] = {
                "exit_code": -1,
                "status": "ERROR",
                "error": "timeout or not found",
            }

    return snapshot


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------
def generate_changelog(
    commits: List[Dict[str, str]],
    validation: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate CHANGELOG.md content."""
    lines = [
        "# NVU Skill Tree — CHANGELOG",
        "",
        "> Auto-generated by `nvu_changelog.py`",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Validation snapshot
    if validation:
        lines.append("## Current Validation Status")
        lines.append("")
        lines.append("| Tool | Status | Pass | Fail | Warn |")
        lines.append("|------|--------|------|------|------|")
        for name, data in validation.get("tools", {}).items():
            status = data.get("status", "?")
            emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            lines.append(
                f"| {name} | {emoji} {status} | "
                f"{data.get('passed', '?')} | {data.get('failed', '?')} | "
                f"{data.get('warnings', '?')} |"
            )
        lines.append("")

    # Group commits by date
    by_date: Dict[str, List[Dict[str, str]]] = {}
    for commit in commits:
        date_str = commit["date"][:10]  # YYYY-MM-DD
        by_date.setdefault(date_str, []).append(commit)

    lines.append("## Commit History")
    lines.append("")

    for date_str in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {date_str}")
        lines.append("")

        for commit in by_date[date_str]:
            stats = get_commit_stats(commit["hash"])
            category = categorize_commit(commit["subject"])
            short = commit["short_hash"]
            subj = commit["subject"]

            lines.append(f"- **[{short}]** [{category}] {subj}")
            if stats["files"] > 0:
                lines.append(
                    f"  - {stats['files']} files, "
                    f"+{stats['additions']}/-{stats['deletions']}"
                )
                # Show top 5 files
                top_files = sorted(
                    stats["file_list"],
                    key=lambda f: f["additions"] + f["deletions"],
                    reverse=True,
                )[:5]
                for f in top_files:
                    short_path = f["path"].replace(".opencode/skill/fv-nvu/", "")
                    lines.append(
                        f"  - `{short_path}` (+{f['additions']}/-{f['deletions']})"
                    )
                if len(stats["file_list"]) > 5:
                    lines.append(
                        f"  - ... and {len(stats['file_list']) - 5} more files"
                    )
            lines.append("")

    # Summary stats
    total_files = 0
    total_add = 0
    total_del = 0
    for commit in commits:
        stats = get_commit_stats(commit["hash"])
        total_files += stats["files"]
        total_add += stats["additions"]
        total_del += stats["deletions"]

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total commits**: {len(commits)}")
    lines.append(f"- **Total file changes**: {total_files}")
    lines.append(f"- **Total additions**: +{total_add}")
    lines.append(f"- **Total deletions**: -{total_del}")
    lines.append("")
    lines.append("---")
    lines.append(
        "*Generated by nvu_changelog.py — part of the NVU self-improvement toolchain*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------
def generate_json(
    commits: List[Dict[str, str]],
    validation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate JSON changelog data."""
    enriched = []
    for commit in commits:
        entry: Dict[str, Any] = dict(commit)
        entry["stats"] = get_commit_stats(commit["hash"])
        entry["category"] = categorize_commit(commit["subject"])
        enriched.append(entry)

    result: Dict[str, Any] = {
        "generated": datetime.now().isoformat(),
        "tool": "nvu_changelog.py",
        "commits": enriched,
        "total_commits": len(enriched),
    }
    if validation:
        result["validation"] = validation

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="NVU CHANGELOG auto-generation")
    parser.add_argument("--since", help="Generate since tag/date/commit")
    parser.add_argument("--max-count", type=int, default=50, help="Max commits")
    parser.add_argument("--validate", action="store_true", help="Run validators")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--output", help="Output file path (default: CHANGELOG.md)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.json else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Get commits
    commits = get_nvu_commits(since=args.since, max_count=args.max_count)
    if not commits:
        if args.json:
            print(
                json.dumps({"error": "No NVU commits found", "commits": []}, indent=2)
            )
        else:
            logger.warning("No NVU commits found in git log")
        return 0

    logger.info("Found %d NVU commits", len(commits))

    # Optional validation
    validation = None
    if args.validate:
        logger.info("Running validation snapshot...")
        validation = run_validation_snapshot()

    # Generate output
    if args.json:
        data = generate_json(commits, validation)
        print(json.dumps(data, indent=2))
    else:
        content = generate_changelog(commits, validation)
        if args.dry_run:
            print(content)
        else:
            out_path = Path(args.output) if args.output else CHANGELOG_PATH
            out_path.write_text(content, encoding="utf-8")
            logger.info(
                "Wrote CHANGELOG to %s (%d lines)", out_path, content.count("\n") + 1
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
