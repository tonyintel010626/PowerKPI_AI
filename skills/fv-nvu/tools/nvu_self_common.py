#!/usr/bin/env python3
"""
NVU Self-Improvement Common Library
====================================
Shared utilities for the NVU self-improvement pipeline.
Provides data classes, config loading, path resolution, file reading,
git helpers, and pattern matching used by all other self-* tools.

Ported from THC self-improvement framework, adapted for NVU skill tree.

Owner: Chin, William Willy (willychi)
"""

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
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "self_improvement_config.json"
TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S"
REPORT_SEPARATOR = "=" * 72

# NVU-specific constants
NVU_SKILL_BASE = ".opencode/skill/fv-nvu"
NVU_AGENT_DEF = ".opencode/agent/FV/FV-NVU.md"
NVU_CROSS_REF_PATTERN = r"fv-nvu/(\w[\w-]*)"

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


class Finding:
    """A single finding from a self-improvement check or verification."""

    __slots__ = ("check", "target", "status", "message", "severity", "details")

    # Status constants
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    ERROR = "ERROR"
    SKIP = "SKIP"
    CHANGE = "CHANGE"

    # Severity constants
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    # Status → emoji mapping
    ICONS = {
        "PASS": "\u2705",  # ✅
        "FAIL": "\u274c",  # ❌
        "WARN": "\u26a0\ufe0f",  # ⚠️
        "ERROR": "\U0001f6d1",  # 🛑
        "SKIP": "\u23ed\ufe0f",  # ⏭️
        "CHANGE": "\U0001f504",  # 🔄
    }

    def __init__(
        self,
        check: str,
        target: str,
        status: str,
        message: str,
        severity: str = "info",
        details: Optional[str] = None,
    ):
        self.check = check
        self.target = target
        self.status = status
        self.message = message
        self.severity = severity
        self.details = details

    @property
    def effective_severity(self) -> str:
        """Map status to effective severity for sorting/filtering."""
        if self.status == self.FAIL:
            return self.severity if self.severity != self.INFO else self.MEDIUM
        if self.status == self.WARN:
            return self.LOW if self.severity == self.INFO else self.severity
        return self.severity

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "check": self.check,
            "target": self.target,
            "status": self.status,
            "message": self.message,
            "severity": self.severity,
        }
        if self.details:
            d["details"] = self.details
        return d

    def __str__(self) -> str:
        icon = self.ICONS.get(self.status, "?")
        sev = f" [{self.severity}]" if self.severity != self.INFO else ""
        return (
            f"{icon} [{self.status}]{sev} {self.check} | {self.target}: {self.message}"
        )


class Report:
    """Aggregated report from a self-improvement run."""

    def __init__(self, name: str = "NVU Self-Improvement", version: str = "1.0"):
        self.name = name
        self.version = version
        self.timestamp = datetime.now().strftime(TIMESTAMP_FMT)
        self.findings: List[Finding] = []

    # -- Aggregation helpers --

    def compute_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for f in self.findings:
            summary[f.status] = summary.get(f.status, 0) + 1
        summary["total"] = len(self.findings)
        return summary

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == Finding.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == Finding.FAIL)

    @property
    def has_failures(self) -> bool:
        return any(f.status == Finding.FAIL for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.status == Finding.WARN for f in self.findings)

    # -- Output methods --

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.compute_summary(),
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self) -> str:
        lines = [
            REPORT_SEPARATOR,
            f"  {self.name} Report v{self.version}",
            f"  Generated: {self.timestamp}",
            REPORT_SEPARATOR,
            "",
        ]
        summary = self.compute_summary()
        lines.append("Summary:")
        for status, count in sorted(summary.items()):
            if status != "total":
                icon = Finding.ICONS.get(status, "?")
                lines.append(f"  {icon} {status}: {count}")
        lines.append(f"  Total: {summary.get('total', 0)}")
        lines.append("")
        lines.append(REPORT_SEPARATOR)
        lines.append("Findings:")
        lines.append("")
        for f in self.findings:
            lines.append(str(f))
        lines.append("")
        lines.append(REPORT_SEPARATOR)
        return "\n".join(lines)

    def save(self, path: Path, fmt: str = "json"):
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            path.write_text(self.to_json(), encoding="utf-8")
        else:
            path.write_text(self.to_text(), encoding="utf-8")
        logging.info(f"Report saved to {path}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for self-improvement tools."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Repository & Path Helpers
# ---------------------------------------------------------------------------


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk up from *start* (default: this file's dir) to find the repo root (.git)."""
    p = start or Path(__file__).resolve().parent
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Could not find repository root (.git)")


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load self_improvement_config.json from the tools/ directory (or explicit path)."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent / CONFIG_FILENAME
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def resolve_path(
    config: Dict[str, Any], key: str, subkey: Optional[str] = None
) -> Path:
    """Resolve a path from config relative to the repository root."""
    root = find_repo_root()
    if subkey:
        raw = config.get(key, {}).get(subkey, "")
    else:
        raw = config.get(key, "")
    if not raw:
        raise ValueError(
            f"Config path not found: {key}.{subkey}"
            if subkey
            else f"Config path not found: {key}"
        )
    return root / raw


# ---------------------------------------------------------------------------
# Skill File Helpers
# ---------------------------------------------------------------------------


def get_skill_base(config: Optional[Dict[str, Any]] = None) -> Path:
    """Return the skill base directory."""
    root = find_repo_root()
    if config and "paths" in config:
        return root / config["paths"].get("skill_base", NVU_SKILL_BASE)
    return root / NVU_SKILL_BASE


def get_skill_path(skill_name: str, config: Optional[Dict[str, Any]] = None) -> Path:
    """Return the SKILL.md path for a given sub-skill name."""
    base = get_skill_base(config)
    return base / skill_name / "SKILL.md"


def get_all_skill_paths(config: Optional[Dict[str, Any]] = None) -> Dict[str, Path]:
    """Return {skill_name: Path} for all configured sub-skills."""
    if config is None:
        config = load_config()
    skills = config.get("skills", [])
    return {name: get_skill_path(name, config) for name in skills}


def read_skill(
    skill_name: str, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[str]]:
    """Read a sub-skill's SKILL.md and optional companion files.

    Returns:
        {"skill": content, "linux": content_or_None, "windows": content_or_None}
    """
    path = get_skill_path(skill_name, config)
    result: Dict[str, Optional[str]] = {"skill": None, "linux": None, "windows": None}

    if path.exists():
        result["skill"] = path.read_text(encoding="utf-8")
    else:
        logging.warning(f"SKILL.md not found for '{skill_name}': {path}")

    # Check for OS-specific companion files
    for companion in ("linux.md", "windows.md"):
        cpath = path.parent / companion
        key = companion.replace(".md", "")
        if cpath.exists():
            result[key] = cpath.read_text(encoding="utf-8")

    return result


def read_agent_def(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Read the FV-NVU agent definition file."""
    root = find_repo_root()
    if config and "paths" in config:
        agent_path = root / config["paths"].get("agent_def", NVU_AGENT_DEF)
    else:
        agent_path = root / NVU_AGENT_DEF
    if agent_path.exists():
        return agent_path.read_text(encoding="utf-8")
    logging.warning(f"Agent definition not found: {agent_path}")
    return None


def read_parent_skill(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Read the parent fv-nvu/SKILL.md file."""
    base = get_skill_base(config)
    parent_path = base / "SKILL.md"
    if parent_path.exists():
        return parent_path.read_text(encoding="utf-8")
    logging.warning(f"Parent SKILL.md not found: {parent_path}")
    return None


# ---------------------------------------------------------------------------
# Git Helpers
# ---------------------------------------------------------------------------


def _run_git(args: List[str], cwd: Optional[Path] = None) -> str:
    """Run a git command and return stdout (or empty string on error)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd or find_repo_root(),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def git_log(
    path: Optional[str] = None, n: int = 20, since: Optional[str] = None
) -> List[Dict[str, str]]:
    """Return recent git log entries as [{hash, date, author, subject}]."""
    args = ["log", f"-{n}", "--format=%H|%aI|%an|%s"]
    if since:
        args.append(f"--since={since}")
    if path:
        args.extend(["--", path])
    raw = _run_git(args)
    entries = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            entries.append(
                {
                    "hash": parts[0],
                    "date": parts[1],
                    "author": parts[2],
                    "subject": parts[3],
                }
            )
    return entries


def git_diff_stat(ref: str = "HEAD~1") -> str:
    """Return diffstat compared to *ref*."""
    return _run_git(["diff", "--stat", ref])


def file_modified_since(path: str, since: str) -> bool:
    """Check if a file has git commits since a given date/ref."""
    result = _run_git(["log", "-1", f"--since={since}", "--", path])
    return bool(result)


# ---------------------------------------------------------------------------
# Pattern Matching Helpers
# ---------------------------------------------------------------------------


def find_pattern_in_file(
    path: Path, pattern: str, flags: int = 0
) -> List[Tuple[int, str]]:
    """Search file for regex pattern, return [(line_number, line_text)]."""
    if not path.exists():
        return []
    matches = []
    regex = re.compile(pattern, flags)
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if regex.search(line):
                matches.append((i, line.rstrip()))
    return matches


def count_lines(path: Path) -> int:
    """Count lines in a file, return 0 if not found."""
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def extract_cross_references(content: str) -> List[str]:
    """Extract fv-nvu/<name> cross-references from content."""
    return sorted(set(re.findall(NVU_CROSS_REF_PATTERN, content)))


# ---------------------------------------------------------------------------
# Timestamp Persistence
# ---------------------------------------------------------------------------

_TS_FILE = ".self_improvement_timestamps.json"


def load_last_run_timestamp(tool_name: str) -> Optional[str]:
    """Load the last run timestamp for a given tool from the timestamps file."""
    ts_path = Path(__file__).resolve().parent / _TS_FILE
    if not ts_path.exists():
        return None
    try:
        data = json.loads(ts_path.read_text(encoding="utf-8"))
        return data.get(tool_name)
    except (json.JSONDecodeError, KeyError):
        return None


def save_last_run_timestamp(tool_name: str, timestamp: Optional[str] = None) -> None:
    """Save the current timestamp for a given tool."""
    ts_path = Path(__file__).resolve().parent / _TS_FILE
    data = {}
    if ts_path.exists():
        try:
            data = json.loads(ts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data[tool_name] = timestamp or datetime.now().strftime(TIMESTAMP_FMT)
    ts_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main (self-test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    setup_logging("DEBUG")
    logger = logging.getLogger("nvu_self_common")

    logger.info("Self-test: finding repo root...")
    root = find_repo_root()
    logger.info(f"  Repo root: {root}")

    logger.info("Self-test: loading config...")
    try:
        cfg = load_config()
        logger.info(f"  Skills: {cfg.get('skills', [])}")
    except FileNotFoundError as e:
        logger.error(f"  {e}")
        sys.exit(1)

    logger.info("Self-test: enumerating skill paths...")
    for name, path in get_all_skill_paths(cfg).items():
        exists = "EXISTS" if path.exists() else "MISSING"
        logger.info(f"  {name}: {path} [{exists}]")

    logger.info("Self-test: reading agent definition...")
    agent = read_agent_def(cfg)
    if agent:
        logger.info(f"  Agent def: {len(agent)} chars")
    else:
        logger.warning("  Agent def: NOT FOUND")

    logger.info("Self-test: checking cross-references in parent skill...")
    parent = read_parent_skill(cfg)
    if parent:
        xrefs = extract_cross_references(parent)
        logger.info(f"  Cross-refs found: {xrefs}")

    logger.info("Self-test: DONE")
