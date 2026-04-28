#!/usr/bin/env python3
"""
FV-AUDIO Self-Improvement Framework — Common Utilities

Shared helpers for all audio self-improvement tools:
  - Repository and config loading
  - Skill file I/O
  - Finding / Report data classes
  - Git log helpers
  - Logging setup

Adapted from FV-THC self-improvement framework.
Owner: huiyingt (Tan Hui Ying)
"""

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CFG_NAME = "self_improvement_config.json"
_TOOLS_DIR = Path(__file__).resolve().parent
_SKILL_BASE = _TOOLS_DIR.parent            # .opencode/skill/fv-audio
_TIMESTAMP_FILE = _TOOLS_DIR / ".last_run"

logger = logging.getLogger("audio_self")


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------
def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk up from *start* (default: this file) until a .git dir is found."""
    cur = (start or _TOOLS_DIR).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Could not locate repository root (.git not found)")


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load and return the self-improvement JSON config."""
    path = config_path or (_TOOLS_DIR / _CFG_NAME)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_path(relative: str, root: Optional[Path] = None) -> Path:
    """Resolve a repo-relative path to an absolute path."""
    base = root or find_repo_root()
    return (base / relative).resolve()


# ---------------------------------------------------------------------------
# Skill I/O
# ---------------------------------------------------------------------------
def get_skill_path(skill_name: str, cfg: Optional[dict] = None) -> Path:
    """Return the SKILL.md path for a named sub-skill."""
    cfg = cfg or load_config()
    base = resolve_path(cfg["paths"]["skill_base"])
    return base / skill_name / "SKILL.md"


def get_all_skill_paths(cfg: Optional[dict] = None) -> List[Tuple[str, Path]]:
    """Return [(skill_name, Path), ...] for every configured sub-skill."""
    cfg = cfg or load_config()
    return [(s, get_skill_path(s, cfg)) for s in cfg.get("skills", [])]


def read_skill(skill_name: str, cfg: Optional[dict] = None) -> Optional[str]:
    """Read and return the full text of a sub-skill's SKILL.md, or None."""
    p = get_skill_path(skill_name, cfg)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def read_agent_def(cfg: Optional[dict] = None) -> Optional[str]:
    """Read the agent definition markdown file."""
    cfg = cfg or load_config()
    p = resolve_path(cfg["paths"]["agent_def"])
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def git_log(
    path: str,
    since: Optional[str] = None,
    max_count: int = 50,
    repo_root: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """
    Return recent git commits touching *path* as a list of dicts
    with keys: hash, date, author, subject.
    """
    root = repo_root or find_repo_root()
    cmd = ["git", "log", f"--max-count={max_count}", "--format=%H|%aI|%an|%s"]
    if since:
        cmd.append(f"--since={since}")
    cmd.append("--")
    cmd.append(path)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(root), timeout=30
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {
                    "hash": parts[0],
                    "date": parts[1],
                    "author": parts[2],
                    "subject": parts[3],
                }
            )
    return commits


# ---------------------------------------------------------------------------
# Finding & Report
# ---------------------------------------------------------------------------
class Severity(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    ERROR = "ERROR"
    SKIP = "SKIP"
    CHANGE = "CHANGE"


@dataclass
class Finding:
    """A single check / test / study finding."""

    check_id: str
    severity: Severity
    message: str
    detail: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "message": self.message,
            "detail": self.detail,
            "source": self.source,
        }


@dataclass
class Report:
    """Aggregated report from a self-improvement stage."""

    stage: str
    findings: List[Finding] = field(default_factory=list)
    started: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished: Optional[str] = None
    elapsed_s: float = 0.0

    # -- helpers --
    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def pass_(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.PASS, msg, **kw))

    def fail(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.FAIL, msg, **kw))

    def warn(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.WARN, msg, **kw))

    def error(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.ERROR, msg, **kw))

    def skip(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.SKIP, msg, **kw))

    def change(self, check_id: str, msg: str, **kw) -> None:
        self.add(Finding(check_id, Severity.CHANGE, msg, **kw))

    def finalize(self, start_time: float) -> None:
        self.elapsed_s = round(time.time() - start_time, 3)
        self.finished = datetime.now(timezone.utc).isoformat()

    @property
    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            sev = f.severity.value if hasattr(f.severity, 'value') else f.severity
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    @property
    def passed(self) -> bool:
        return not any(
            f.severity in (Severity.FAIL, Severity.ERROR) for f in self.findings
        )

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "started": self.started,
            "finished": self.finished,
            "elapsed_s": self.elapsed_s,
            "summary": self.summary,
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def print_text(self, file=sys.stdout) -> None:
        """Pretty-print the report as human-readable text."""
        hdr = f"=== {self.stage} Report ==="
        print(hdr, file=file)
        for f in self.findings:
            tag = f"[{f.severity.value:6s}]"
            print(f"  {tag} {f.check_id}: {f.message}", file=file)
            if f.detail:
                for dl in f.detail.splitlines():
                    print(f"           {dl}", file=file)
        s = self.summary
        total = len(self.findings)
        status = "PASSED" if self.passed else "FAILED"
        print(
            f"  --- {status} | total={total} "
            + " ".join(f"{k}={v}" for k, v in sorted(s.items()))
            + f" | {self.elapsed_s:.1f}s",
            file=file,
        )


# ---------------------------------------------------------------------------
# Timestamp helpers (for study/learn incremental runs)
# ---------------------------------------------------------------------------
def get_last_run_timestamp() -> Optional[str]:
    """Return ISO timestamp of last run, or None."""
    if _TIMESTAMP_FILE.exists():
        return _TIMESTAMP_FILE.read_text().strip()
    return None


def save_last_run_timestamp() -> None:
    """Persist current UTC timestamp."""
    _TIMESTAMP_FILE.write_text(datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)
