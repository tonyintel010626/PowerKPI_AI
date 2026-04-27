#!/usr/bin/env python3
"""Skill Audit Orchestrator — coordinates multi-document cross-check audits against a skill tree.

Usage:
    python skill_audit.py <audit_config.json> [--phase PHASE] [--doc DOC_ID] [--report DIR] [--json]

The audit config JSON defines:
- reference_hierarchy: ordered list of documents with priority, path, format, scope
- skill_tree: path to the skill directory to audit
- audit_state_file: path to persist audit progress

This tool orchestrates the doc-study pipeline (extract → verify → cross-check) for each
reference document in priority order, merges findings across documents, tracks delta-to-zero,
and produces a consolidated audit report.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Audit State Model
# ---------------------------------------------------------------------------

class AuditDocument:
    """Tracks audit state for a single reference document."""

    __slots__ = (
        'doc_id', 'path', 'priority', 'scope', 'format', 'status',
        'extract_path', 'extract_words', 'raw_words',
        'verify_coverage', 'verify_missed_technical',
        'crosscheck_confirmed', 'crosscheck_missing', 'crosscheck_wrong', 'crosscheck_new',
        'last_audited', 'notes',
    )

    def __init__(self, doc_id: str, path: str, priority: int = 1,
                 scope: str = '', fmt: str = 'auto', **kwargs: Any):
        self.doc_id = doc_id
        self.path = path
        self.priority = priority
        self.scope = scope
        self.format = fmt
        self.status = kwargs.get('status', 'pending')
        self.extract_path = kwargs.get('extract_path', '')
        self.extract_words: int = kwargs.get('extract_words', 0)
        self.raw_words: int = kwargs.get('raw_words', 0)
        self.verify_coverage: float = kwargs.get('verify_coverage', 0.0)
        self.verify_missed_technical: int = kwargs.get('verify_missed_technical', 0)
        self.crosscheck_confirmed: int = kwargs.get('crosscheck_confirmed', 0)
        self.crosscheck_missing: int = kwargs.get('crosscheck_missing', 0)
        self.crosscheck_wrong: int = kwargs.get('crosscheck_wrong', 0)
        self.crosscheck_new: int = kwargs.get('crosscheck_new', 0)
        self.last_audited = kwargs.get('last_audited', '')
        self.notes = kwargs.get('notes', '')

    def to_dict(self) -> Dict[str, Any]:
        return {s: getattr(self, s) for s in self.__slots__}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'AuditDocument':
        return cls(
            doc_id=d['doc_id'], path=d['path'], priority=d.get('priority', 1),
            scope=d.get('scope', ''), fmt=d.get('format', 'auto'),
            **{k: d[k] for k in d if k not in ('doc_id', 'path', 'priority', 'scope', 'format')}
        )

    @property
    def delta(self) -> int:
        """Total unresolved findings (MISSING + WRONG)."""
        return self.crosscheck_missing + self.crosscheck_wrong


class AuditState:
    """Persistent audit state across sessions."""

    def __init__(self, config_path: str, skill_tree: str,
                 documents: Optional[List[AuditDocument]] = None,
                 audit_runs: Optional[List[Dict[str, Any]]] = None):
        self.config_path = config_path
        self.skill_tree = skill_tree
        self.documents: List[AuditDocument] = documents or []
        self.audit_runs: List[Dict[str, Any]] = audit_runs or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'config_path': self.config_path,
            'skill_tree': self.skill_tree,
            'documents': [d.to_dict() for d in self.documents],
            'audit_runs': self.audit_runs,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'AuditState':
        docs = [AuditDocument.from_dict(dd) for dd in d.get('documents', [])]
        return cls(
            config_path=d['config_path'],
            skill_tree=d['skill_tree'],
            documents=docs,
            audit_runs=d.get('audit_runs', []),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path: Path) -> 'AuditState':
        return cls.from_dict(json.loads(path.read_text(encoding='utf-8')))

    def get_document(self, doc_id: str) -> Optional[AuditDocument]:
        for d in self.documents:
            if d.doc_id == doc_id:
                return d
        return None

    @property
    def total_delta(self) -> int:
        return sum(d.delta for d in self.documents)

    @property
    def total_confirmed(self) -> int:
        return sum(d.crosscheck_confirmed for d in self.documents)

    def summary_table(self) -> str:
        """Return a formatted summary table."""
        lines = []
        lines.append(f"{'Doc ID':<20} {'Pri':>3} {'Status':<12} {'Confirmed':>9} {'Missing':>7} {'Wrong':>5} {'New':>5} {'Delta':>5}")
        lines.append('-' * 80)
        for d in sorted(self.documents, key=lambda x: x.priority):
            lines.append(
                f"{d.doc_id:<20} {d.priority:>3} {d.status:<12} "
                f"{d.crosscheck_confirmed:>9} {d.crosscheck_missing:>7} "
                f"{d.crosscheck_wrong:>5} {d.crosscheck_new:>5} {d.delta:>5}"
            )
        lines.append('-' * 80)
        lines.append(
            f"{'TOTAL':<20} {'':>3} {'':12} "
            f"{self.total_confirmed:>9} {sum(d.crosscheck_missing for d in self.documents):>7} "
            f"{sum(d.crosscheck_wrong for d in self.documents):>5} "
            f"{sum(d.crosscheck_new for d in self.documents):>5} {self.total_delta:>5}"
        )
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Tool Locator
# ---------------------------------------------------------------------------

def _find_tool(name: str) -> Optional[Path]:
    """Locate a doc-study tool by name, searching sibling skill dirs."""
    here = Path(__file__).resolve().parent
    # Look in doc-study sibling skill
    candidates = [
        here.parent.parent / 'doc-study' / 'tools' / name,
        here / name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _run_tool(tool_path: Path, args: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    """Run a Python tool and capture output."""
    cmd = [sys.executable, str(tool_path)] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(tool_path.parent)
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 2, '', f'Tool timed out after {timeout}s'
    except Exception as e:
        return 2, '', str(e)


# ---------------------------------------------------------------------------
# Audit Phases
# ---------------------------------------------------------------------------

def phase_extract(doc: AuditDocument, output_dir: Path) -> Dict[str, Any]:
    """Phase 1: Extract document content using doc_extract.py."""
    tool = _find_tool('doc_extract.py')
    if not tool:
        return {'status': 'error', 'message': 'doc_extract.py not found'}

    output_path = output_dir / f"{doc.doc_id}_extract.txt"
    rc, stdout, stderr = _run_tool(tool, [doc.path, '--output', str(output_path)])

    if rc != 0:
        return {'status': 'error', 'message': stderr or stdout}

    # Parse output for word counts
    result: Dict[str, Any] = {'status': 'ok', 'output_path': str(output_path)}
    for line in stdout.split('\n'):
        if 'raw_word_count' in line or 'Raw words' in line:
            try:
                result['raw_words'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass
        if 'structured_word_count' in line or 'Structured words' in line:
            try:
                result['extract_words'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass

    doc.extract_path = str(output_path)
    doc.raw_words = result.get('raw_words', 0)
    doc.extract_words = result.get('extract_words', 0)
    doc.status = 'extracted'
    return result


def phase_verify(doc: AuditDocument, output_dir: Path) -> Dict[str, Any]:
    """Phase 2: Verify extraction completeness using doc_verify.py."""
    tool = _find_tool('doc_verify.py')
    if not tool:
        return {'status': 'error', 'message': 'doc_verify.py not found'}

    if not doc.extract_path:
        return {'status': 'error', 'message': 'No extraction output to verify'}

    report_path = output_dir / f"{doc.doc_id}_verify_report.txt"
    rc, stdout, stderr = _run_tool(tool, [doc.path, doc.extract_path, '--report', str(report_path)])

    result: Dict[str, Any] = {'status': 'ok', 'report_path': str(report_path)}
    for line in stdout.split('\n'):
        if 'Main-doc coverage' in line or 'coverage' in line.lower():
            try:
                pct = float(''.join(c for c in line.split(':')[-1].split('%')[0] if c.isdigit() or c == '.'))
                result['coverage'] = pct
            except ValueError:
                pass
        if 'TECHNICAL' in line and 'missed' in line.lower():
            try:
                result['missed_technical'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass

    doc.verify_coverage = result.get('coverage', 0.0)
    doc.verify_missed_technical = result.get('missed_technical', 0)
    doc.status = 'verified'
    return result


def phase_crosscheck(doc: AuditDocument, skill_tree: str, output_dir: Path,
                     exclude_json: Optional[str] = None) -> Dict[str, Any]:
    """Phase 3: Cross-check against skill tree using doc_crosscheck.py."""
    tool = _find_tool('doc_crosscheck.py')
    if not tool:
        return {'status': 'error', 'message': 'doc_crosscheck.py not found'}

    if not doc.extract_path:
        return {'status': 'error', 'message': 'No extraction output to cross-check'}

    report_path = output_dir / f"{doc.doc_id}_crosscheck_report.txt"
    args = [doc.extract_path, skill_tree, '--report', str(report_path)]
    if exclude_json:
        args += ['--exclude', exclude_json]

    rc, stdout, stderr = _run_tool(tool, args, timeout=600)

    result: Dict[str, Any] = {'status': 'ok', 'report_path': str(report_path)}
    for line in stdout.split('\n'):
        if 'CONFIRMED' in line:
            try:
                result['confirmed'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass
        if 'MISSING' in line and 'confirmed' not in line.lower():
            try:
                result['missing'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass
        if 'WRONG' in line:
            try:
                result['wrong'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass
        if 'NEW' in line:
            try:
                result['new'] = int(''.join(c for c in line.split(':')[-1] if c.isdigit()))
            except ValueError:
                pass

    doc.crosscheck_confirmed = result.get('confirmed', 0)
    doc.crosscheck_missing = result.get('missing', 0)
    doc.crosscheck_wrong = result.get('wrong', 0)
    doc.crosscheck_new = result.get('new', 0)
    doc.last_audited = datetime.now(timezone.utc).isoformat()
    doc.status = 'audited'
    return result


# ---------------------------------------------------------------------------
# Full Audit Pipeline
# ---------------------------------------------------------------------------

def run_audit(config_path: str, phase: Optional[str] = None,
              doc_id: Optional[str] = None, report_dir: Optional[str] = None,
              as_json: bool = False) -> int:
    """Run the full audit pipeline or a specific phase."""

    # Load config
    config_p = Path(config_path)
    if not config_p.is_file():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 2

    config = json.loads(config_p.read_text(encoding='utf-8'))
    skill_tree = config.get('skill_tree', '')
    state_file = Path(config.get('audit_state_file', config_p.stem + '_state.json'))

    # Load or initialize state
    if state_file.is_file():
        state = AuditState.load(state_file)
        print(f"Resumed audit state from {state_file}")
    else:
        docs = []
        for ref in config.get('reference_hierarchy', []):
            docs.append(AuditDocument(
                doc_id=ref['doc_id'],
                path=ref['path'],
                priority=ref.get('priority', 1),
                scope=ref.get('scope', ''),
                fmt=ref.get('format', 'auto'),
            ))
        state = AuditState(config_path=str(config_p), skill_tree=skill_tree, documents=docs)

    # Output directory
    out_dir = Path(report_dir) if report_dir else config_p.parent / 'audit_reports'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Filter documents if specific doc requested
    targets = state.documents
    if doc_id:
        targets = [d for d in targets if d.doc_id == doc_id]
        if not targets:
            print(f"ERROR: Document '{doc_id}' not found in config", file=sys.stderr)
            return 2

    # Sort by priority
    targets.sort(key=lambda d: d.priority)

    # Run phases
    phases_to_run = ['extract', 'verify', 'crosscheck'] if not phase else [phase]
    run_record: Dict[str, Any] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'phases': phases_to_run,
        'documents': [d.doc_id for d in targets],
        'results': {},
    }

    for doc in targets:
        doc_results: Dict[str, Any] = {}
        print(f"\n{'='*60}")
        print(f"Document: {doc.doc_id} (priority {doc.priority})")
        print(f"Path: {doc.path}")
        print(f"{'='*60}")

        for p in phases_to_run:
            print(f"\n--- Phase: {p} ---")
            if p == 'extract':
                r = phase_extract(doc, out_dir)
            elif p == 'verify':
                r = phase_verify(doc, out_dir)
            elif p == 'crosscheck':
                r = phase_crosscheck(doc, skill_tree, out_dir)
            else:
                print(f"Unknown phase: {p}", file=sys.stderr)
                continue

            doc_results[p] = r
            if r.get('status') == 'error':
                print(f"  ERROR: {r.get('message', 'unknown')}")
            else:
                print(f"  Status: {r.get('status', 'unknown')}")

        run_record['results'][doc.doc_id] = doc_results

    state.audit_runs.append(run_record)
    state.save(state_file)

    # Summary
    print(f"\n{'='*60}")
    print("AUDIT SUMMARY")
    print(f"{'='*60}\n")
    print(state.summary_table())
    print(f"\nTotal delta: {state.total_delta}")
    print(f"State saved to: {state_file}")

    if as_json:
        print(json.dumps(state.to_dict(), indent=2))

    return 0 if state.total_delta == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Skill Audit Orchestrator — multi-document cross-check audits'
    )
    parser.add_argument('config', help='Audit config JSON file')
    parser.add_argument('--phase', choices=['extract', 'verify', 'crosscheck'],
                        help='Run only a specific phase')
    parser.add_argument('--doc', dest='doc_id', help='Audit only a specific document')
    parser.add_argument('--report', dest='report_dir', help='Output directory for reports')
    parser.add_argument('--json', action='store_true', help='Output JSON summary')
    args = parser.parse_args()
    return run_audit(args.config, args.phase, args.doc_id, args.report_dir, args.json)


if __name__ == '__main__':
    sys.exit(main())
