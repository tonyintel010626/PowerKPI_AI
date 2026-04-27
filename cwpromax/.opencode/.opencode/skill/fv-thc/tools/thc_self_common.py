#!/usr/bin/env python3
"""
THC Agent Self-Improvement — Common Utilities
> **Owner**: Chin, William Willy (`willychi`)
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.

Shared utilities for all self-improvement scripts:
- Config loading, path resolution, skill file I/O
- Git log parsing, report formatting, logging setup
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_FILENAME = "self_improvement_config.json"
TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S"
REPORT_SEPARATOR = "=" * 70

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk up from *start* (default: this file's dir) until we find .git/."""
    p = start or Path(__file__).resolve().parent
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Cannot locate repository root (.git not found)")


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load self_improvement_config.json. Falls back to same directory as this file."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent / CONFIG_FILENAME
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(relative: str, repo_root: Optional[Path] = None) -> Path:
    """Resolve a config-relative path to an absolute path."""
    root = repo_root or find_repo_root()
    return (root / relative).resolve()


# ---------------------------------------------------------------------------
# Skill File I/O
# ---------------------------------------------------------------------------


def _ensure_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return config, auto-loading from default location if None."""
    if config is not None:
        return config
    return load_config()


def get_skill_path(
    skill_name: str,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> Path:
    """Return absolute path to a sub-skill's SKILL.md."""
    cfg = _ensure_config(config)
    base = resolve_path(cfg["paths"]["skill_base"], repo_root)
    return base / skill_name / "SKILL.md"


def get_all_skill_paths(
    config: Optional[Dict[str, Any]] = None, repo_root: Optional[Path] = None
) -> Dict[str, Path]:
    """Return {skill_name: Path} for every configured sub-skill."""
    cfg = _ensure_config(config)
    return {s: get_skill_path(s, cfg, repo_root) for s in cfg["skills"]}


def read_skill(
    skill_name: str,
    config: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> str:
    """Read a sub-skill SKILL.md and all companion .md files.

    Returns concatenated content from SKILL.md + all other *.md files
    in the same directory (linux.md, windows.md, models.md, etc.)
    so that assertions can search across the entire skill directory.
    """
    path = get_skill_path(skill_name, config, repo_root)
    parts = []
    with open(path, "r", encoding="utf-8") as f:
        parts.append(f.read())
    # Also read all companion .md files in the skill directory (e.g., linux.md,
    # windows.md, models.md, operations.md, advanced.md) so assertions can
    # search across the entire skill directory.
    skill_dir = path.parent
    for companion_path in sorted(skill_dir.glob("*.md")):
        if companion_path.name != "SKILL.md":
            with open(companion_path, "r", encoding="utf-8") as f:
                parts.append(f"\n\n--- {companion_path.name} ---\n\n" + f.read())
    return "\n".join(parts)


def read_file(path: Path) -> str:
    """Read any file, return content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_agent_def(
    config: Optional[Dict[str, Any]] = None, repo_root: Optional[Path] = None
) -> str:
    """Read the FV-THC.md agent definition."""
    cfg = _ensure_config(config)
    path = resolve_path(cfg["paths"]["agent_def"], repo_root)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Git Utilities
# ---------------------------------------------------------------------------


def git_log(
    repo_path: str,
    since: Optional[str] = None,
    path_filter: Optional[str] = None,
    max_count: int = 50,
) -> List[Dict[str, str]]:
    """
    Run `git log` on *repo_path* and return list of commit dicts.
    Each dict has: hash, date, author, subject.
    *since*: ISO date string (e.g. '2025-09-01').
    *path_filter*: restrict to changes under this path.
    """
    cmd = [
        "git",
        "log",
        f"--max-count={max_count}",
        "--format=%H|%aI|%an|%s",
    ]
    if since:
        cmd.append(f"--since={since}")
    if path_filter:
        cmd += ["--", path_filter]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=repo_path, timeout=30
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {
                    "hash": parts[0][:12],
                    "date": parts[1][:10],
                    "author": parts[2],
                    "subject": parts[3],
                }
            )
    return commits


def git_diff_stat(
    repo_path: str, since_hash: Optional[str] = None, path_filter: Optional[str] = None
) -> str:
    """Return `git diff --stat` output for recent changes."""
    cmd = ["git", "diff", "--stat"]
    if since_hash:
        cmd.append(f"{since_hash}..HEAD")
    if path_filter:
        cmd += ["--", path_filter]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=repo_path, timeout=30
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def file_modified_since(path: Path, since_date: str) -> bool:
    """Check if a file has been modified since *since_date* (ISO format)."""
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    threshold = datetime.fromisoformat(since_date).replace(tzinfo=timezone.utc)
    return mtime > threshold


# ---------------------------------------------------------------------------
# Content Analysis
# ---------------------------------------------------------------------------


def find_pattern_in_file(
    path: Path, pattern: str, case_sensitive: bool = True
) -> List[Tuple[int, str]]:
    """Return list of (line_number, line_text) matching *pattern*."""
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = re.compile(pattern, flags)
    matches = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if compiled.search(line):
                    matches.append((i, line.rstrip()))
    except (FileNotFoundError, OSError):
        pass
    return matches


def count_lines(path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except (FileNotFoundError, OSError):
        return 0


def extract_cross_references(content: str) -> List[str]:
    """Extract all `fv-thc/<name>` skill references from content."""
    return re.findall(r"`fv-thc/(\w+)`", content)


# ---------------------------------------------------------------------------
# Report Formatting
# ---------------------------------------------------------------------------


class Finding:
    """A single audit/verification/study finding.

    Parameters match the calling convention used by all self-* scripts:
        check  — which check/test produced this (e.g. 'skill_exists', 'REG-001')
        target — what was checked (e.g. 'fv-thc/registers', 'power/SKILL.md')
        status — outcome: PASS, FAIL, WARN, ERROR, SKIP, CHANGE
        message — human-readable description
        severity — optional severity override (CRITICAL, WARNING, INFO)
        details — optional extra context
    """

    __slots__ = ("check", "target", "status", "message", "severity", "details")

    def __init__(
        self,
        check: str = "",
        target: str = "",
        status: str = "INFO",
        message: str = "",
        severity: str = "",
        details: Union[str, List, Dict] = "",
    ):
        self.check = check
        self.target = target
        self.status = status  # PASS, FAIL, WARN, ERROR, SKIP, CHANGE
        self.message = message
        self.severity = severity  # optional override; inferred from status if empty
        self.details = details

    @property
    def effective_severity(self) -> str:
        """Return explicit severity, or infer from status."""
        if self.severity:
            return self.severity
        return {
            "FAIL": "CRITICAL",
            "ERROR": "CRITICAL",
            "WARN": "WARNING",
            "CHANGE": "WARNING",
            "PASS": "INFO",
            "SKIP": "INFO",
        }.get(self.status, "INFO")

    def to_dict(self) -> Dict[str, str]:
        d = {
            "check": self.check,
            "target": self.target,
            "status": self.status,
            "message": self.message,
        }
        if self.severity:
            d["severity"] = self.severity
        if self.details:
            d["details"] = (
                self.details
                if isinstance(self.details, str)
                else json.dumps(self.details)
            )
        return d

    def __str__(self) -> str:
        icon = {
            "PASS": "🟢",
            "FAIL": "🔴",
            "ERROR": "🔴",
            "WARN": "🟡",
            "CHANGE": "🔵",
            "SKIP": "⚪",
        }.get(self.status, "⚪")
        return f"  {icon} [{self.check}] {self.target}: {self.message}"


class Report:
    """Structured report from any self-improvement capability.

    Parameters match calling convention: Report(name="THC Self-Check", version="1.0.0")
    """

    def __init__(self, name: str = "THC Report", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
        self.findings: List[Finding] = []
        self.summary: Dict[str, int] = {}

    def add(self, finding: Finding):
        self.findings.append(finding)

    def compute_summary(self):
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.status] = counts.get(f.status, 0) + 1
        counts["total"] = len(self.findings)
        self.summary = counts

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status in ("FAIL", "ERROR"))

    @property
    def has_failures(self) -> bool:
        return any(f.status in ("FAIL", "ERROR") for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.status == "WARN" for f in self.findings)

    def to_dict(self) -> Dict[str, Any]:
        self.compute_summary()
        return {
            "name": self.name,
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self) -> str:
        self.compute_summary()
        total = self.summary.get("total", 0)
        passed = self.summary.get("PASS", 0)
        failed = self.summary.get("FAIL", 0) + self.summary.get("ERROR", 0)
        warned = self.summary.get("WARN", 0)
        lines = [
            REPORT_SEPARATOR,
            f"  {self.name} (v{self.version})",
            f"  Generated: {self.timestamp}",
            REPORT_SEPARATOR,
            "",
            f"  Summary: {total} findings "
            f"({passed} pass, {failed} fail, {warned} warn)",
            "",
        ]
        if self.findings:
            for f in self.findings:
                lines.append(str(f))
        else:
            lines.append("  No findings.")
        lines.extend(["", REPORT_SEPARATOR])
        return "\n".join(lines)

    def save(self, directory, fmt: str = "both"):
        """Save report to directory (or file path). *fmt* = 'json', 'text', or 'both'.

        If *directory* is a file path (has a suffix), save to that exact path.
        If *directory* is a directory, auto-generate filenames inside it.
        Accepts str or Path.
        """
        directory = Path(directory)
        # If caller passed a specific file path, save to that path directly
        if directory.suffix:
            directory.parent.mkdir(parents=True, exist_ok=True)
            out_fmt = "json" if directory.suffix == ".json" else "text"
            with open(directory, "w", encoding="utf-8") as f:
                f.write(self.to_json() if out_fmt == "json" else self.to_text())
            return
        # Otherwise treat as directory and auto-generate filenames
        directory.mkdir(parents=True, exist_ok=True)
        safe_name = self.name.lower().replace(" ", "_").replace("-", "_")
        base = f"{safe_name}_{self.timestamp[:10]}"
        if fmt in ("json", "both"):
            with open(directory / f"{base}.json", "w", encoding="utf-8") as f:
                f.write(self.to_json())
        if fmt in ("text", "both"):
            with open(directory / f"{base}.txt", "w", encoding="utf-8") as f:
                f.write(self.to_text())


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up a logger with console + optional file handler."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(name)s %(levelname)s: %(message)s", datefmt="%H:%M:%S"
        )
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Timestamp Persistence
# ---------------------------------------------------------------------------


def load_last_run_timestamp(capability: str, tools_dir: Path) -> Optional[str]:
    """Load the last run timestamp for a capability."""
    ts_file = tools_dir / ".self_improvement_timestamps.json"
    if not ts_file.exists():
        return None
    with open(ts_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(capability)


def save_last_run_timestamp(
    capability: str, tools_dir: Path, timestamp: Optional[str] = None
):
    """Save the current timestamp for a capability."""
    ts_file = tools_dir / ".self_improvement_timestamps.json"
    data = {}
    if ts_file.exists():
        with open(ts_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    data[capability] = timestamp or datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
    with open(ts_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
