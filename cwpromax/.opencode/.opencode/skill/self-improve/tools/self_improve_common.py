#!/usr/bin/env python3
"""
Generic Self-Improvement Common Utilities

Domain-agnostic Finding/Report/config utilities that any skill tree
can use for self-check, self-verify, and self-improve workflows.

Generalized from the THC-specific thc_self_common.py.

Usage:
    from self_improve_common import Finding, Report, load_config, read_skill
"""

import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Finding ──────────────────────────────────────────────────────────

VALID_STATUSES = {'PASS', 'FAIL', 'WARN', 'ERROR', 'SKIP', 'CHANGE'}
VALID_SEVERITIES = {'critical', 'high', 'medium', 'low', 'info', None}


@dataclass
class Finding:
    """A single check/verify result."""
    check: str
    target: str
    status: str  # PASS, FAIL, WARN, ERROR, SKIP, CHANGE
    message: str
    severity: Optional[str] = None  # critical, high, medium, low, info
    details: Any = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")
        if self.severity is not None and self.severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")

    @property
    def effective_severity(self) -> str:
        """Infer severity from status if not explicitly set."""
        if self.severity:
            return self.severity
        return {
            'FAIL': 'high', 'ERROR': 'critical', 'WARN': 'medium',
            'PASS': 'info', 'SKIP': 'info', 'CHANGE': 'medium',
        }.get(self.status, 'info')

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['effective_severity'] = self.effective_severity
        return d


# ── Report ───────────────────────────────────────────────────────────

STATUS_ICONS = {
    'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️',
    'ERROR': '💥', 'SKIP': '⏭️', 'CHANGE': '🔄',
}


@dataclass
class Report:
    """Aggregated findings from a check/verify/improve run."""
    name: str
    version: str = '1.0'
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings: List[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == 'PASS')

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == 'FAIL')

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.status == 'WARN')

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.status == 'ERROR')

    @property
    def has_failures(self) -> bool:
        return self.fail_count > 0

    @property
    def has_issues(self) -> bool:
        return self.fail_count > 0 or self.error_count > 0

    def compute_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for f in self.findings:
            summary[f.status] = summary.get(f.status, 0) + 1
        summary['total'] = len(self.findings)
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'timestamp': self.timestamp,
            'summary': self.compute_summary(),
            'findings': [f.to_dict() for f in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"  {self.name}",
            f"  {self.timestamp}",
            f"{'=' * 60}",
        ]
        summary = self.compute_summary()
        parts = [f"{STATUS_ICONS.get(k, '?')} {k}: {v}"
                 for k, v in summary.items() if k != 'total']
        lines.append(f"  Total: {summary.get('total', 0)}  |  " + '  '.join(parts))
        lines.append('')
        for f in self.findings:
            icon = STATUS_ICONS.get(f.status, '?')
            lines.append(f"  {icon} [{f.check}] {f.target}: {f.message}")
            if f.details:
                detail_str = json.dumps(f.details, indent=2) if isinstance(f.details, dict) else str(f.details)
                for detail_line in detail_str.split('\n'):
                    lines.append(f"      {detail_line}")
        lines.append(f"\n{'=' * 60}")
        return '\n'.join(lines)

    def save(self, path: Path, fmt: str = 'json') -> Path:
        """Save report to file. If path is a directory, auto-name the file."""
        path = Path(path)
        if path.is_dir():
            ext = 'json' if fmt == 'json' else 'txt'
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = path / f"{self.name}_{ts}.{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.to_json() if fmt == 'json' else self.to_text()
        path.write_text(content, encoding='utf-8')
        return path


# ── Config Loading ───────────────────────────────────────────────────

def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk up to find the git repository root."""
    current = Path(start or Path.cwd()).resolve()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    raise FileNotFoundError("No .git directory found in parent chain")


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load a self-improvement config JSON file.

    If no path given, searches for self_improvement_config.json
    in common locations relative to the repo root.
    """
    if config_path and config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['_config_path'] = str(config_path.resolve())
        config['_repo_root'] = str(find_repo_root(config_path.parent))
        return config

    root = find_repo_root()
    # Search common locations
    candidates = [
        root / 'self_improvement_config.json',
    ]
    # Also search all skill tool directories
    skill_root = root / '.opencode' / 'skill'
    if skill_root.is_dir():
        for skill_dir in skill_root.iterdir():
            tools_dir = skill_dir / 'tools'
            if tools_dir.is_dir():
                candidate = tools_dir / 'self_improvement_config.json'
                if candidate.exists():
                    candidates.append(candidate)

    for candidate in candidates:
        if candidate.exists():
            config = json.loads(candidate.read_text(encoding='utf-8'))
            config['_config_path'] = str(candidate.resolve())
            config['_repo_root'] = str(root)
            return config

    raise FileNotFoundError(
        f"No self_improvement_config.json found. Searched: {[str(c) for c in candidates]}"
    )


def resolve_path(relative: str, repo_root: Optional[Path] = None) -> Path:
    """Resolve a config-relative path to an absolute path."""
    root = repo_root or find_repo_root()
    return (root / relative).resolve()


# ── Skill I/O ────────────────────────────────────────────────────────

def get_skill_path(
    skill_name: str,
    skill_base: str,
    repo_root: Optional[Path] = None,
) -> Path:
    """Get path to a skill's SKILL.md file."""
    root = repo_root or find_repo_root()
    return root / skill_base / skill_name / 'SKILL.md'


def get_all_skill_paths(
    skill_names: List[str],
    skill_base: str,
    repo_root: Optional[Path] = None,
) -> Dict[str, Path]:
    """Get paths for all skills listed in config."""
    root = repo_root or find_repo_root()
    return {
        name: root / skill_base / name / 'SKILL.md'
        for name in skill_names
    }


def read_skill(
    skill_name: str,
    skill_base: str,
    repo_root: Optional[Path] = None,
) -> str:
    """Read a skill file's content."""
    path = get_skill_path(skill_name, skill_base, repo_root)
    return path.read_text(encoding='utf-8')


def read_file(path: Path) -> str:
    """Read any file's content."""
    return Path(path).read_text(encoding='utf-8')


# ── Git Utilities ────────────────────────────────────────────────────

def git_log(
    repo_path: Path,
    since: Optional[str] = None,
    path_filter: Optional[str] = None,
    max_count: int = 50,
) -> List[Dict[str, str]]:
    """Parse git log into structured dicts."""
    import subprocess
    cmd = [
        'git', '-C', str(repo_path), 'log',
        f'--max-count={max_count}',
        '--format=%H|%ai|%an|%s',
    ]
    if since:
        cmd.append(f'--since={since}')
    if path_filter:
        cmd.extend(['--', path_filter])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        entries = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|', 3)
                if len(parts) == 4:
                    entries.append({
                        'hash': parts[0],
                        'date': parts[1],
                        'author': parts[2],
                        'subject': parts[3],
                    })
        return entries
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def file_modified_since(path: Path, since_date: str) -> bool:
    """Check if a file was modified after a given date string (YYYY-MM-DD)."""
    try:
        mtime = path.stat().st_mtime
        threshold = datetime.strptime(since_date, '%Y-%m-%d').timestamp()
        return mtime > threshold
    except (OSError, ValueError):
        return False


# ── Content Analysis ─────────────────────────────────────────────────

def find_pattern_in_file(
    path: Path,
    pattern: str,
    case_sensitive: bool = True,
) -> List[Tuple[int, str]]:
    """Regex search returning (line_no, matched_text) tuples."""
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        content = path.read_text(encoding='utf-8')
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(pattern, line, flags):
                matches.append((i, line.strip()))
        return matches
    except (OSError, UnicodeDecodeError):
        return []


def count_lines(path: Path) -> int:
    """Count lines in a file."""
    try:
        return len(path.read_text(encoding='utf-8').split('\n'))
    except (OSError, UnicodeDecodeError):
        return 0


def extract_cross_references(content: str, ref_pattern: str = r'[a-z][\w-]+/[\w-]+') -> List[str]:
    """Extract skill cross-references from content.

    Args:
        content: File content to search
        ref_pattern: Regex for what a cross-reference looks like
    """
    return list(set(re.findall(ref_pattern, content)))


# ── Timestamp Persistence ────────────────────────────────────────────

def load_last_run_timestamp(
    capability: str,
    storage_path: Path,
) -> Optional[str]:
    """Load the last run timestamp for a given capability."""
    ts_file = storage_path / '.self_improvement_timestamps.json'
    if ts_file.exists():
        data = json.loads(ts_file.read_text(encoding='utf-8'))
        return data.get(capability)
    return None


def save_last_run_timestamp(
    capability: str,
    storage_path: Path,
    timestamp: Optional[str] = None,
) -> None:
    """Save a run timestamp for a given capability."""
    ts_file = storage_path / '.self_improvement_timestamps.json'
    data: Dict[str, str] = {}
    if ts_file.exists():
        data = json.loads(ts_file.read_text(encoding='utf-8'))
    data[capability] = timestamp or datetime.now(timezone.utc).isoformat()
    ts_file.write_text(json.dumps(data, indent=2), encoding='utf-8')


# ── Logging ──────────────────────────────────────────────────────────

def setup_logging(name: str = 'self-improve', level: int = logging.INFO) -> logging.Logger:
    """Set up a logger with console handler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S',
        ))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ── Proposal ─────────────────────────────────────────────────────────

@dataclass
class Proposal:
    """An actionable improvement proposal generated from findings."""
    id: str
    priority: str  # critical, high, medium, low
    category: str
    target_file: str
    action: str  # fix, review, add, remove
    description: str
    rationale: str
    source_findings: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "proposed"  # proposed, approved, applied, rejected

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
