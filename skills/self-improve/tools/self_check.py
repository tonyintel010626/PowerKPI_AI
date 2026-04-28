#!/usr/bin/env python3
"""
Generic Skill Self-Check — Structural Validation

Domain-agnostic structural checks for any skill tree.
Validates file existence, frontmatter, owner headers, cross-references,
and config consistency.

Generalized from the THC-specific thc_self_check.py.

Usage:
    python self_check.py --config <config.json>
    python self_check.py --config <config.json> --check owner_headers
    python self_check.py --config <config.json> --json
    python self_check.py --config <config.json> --pre-commit
"""

import argparse
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Add parent to path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))
from self_improve_common import (
    Finding, Report, load_config, find_repo_root, resolve_path,
    get_skill_path, get_all_skill_paths, read_file, count_lines,
    find_pattern_in_file, extract_cross_references, setup_logging,
)

logger = setup_logging('self-check')


# ── Check Functions ──────────────────────────────────────────────────
# Each check function takes (config, repo_root) and returns List[Finding]

def check_skill_files_exist(config: Dict, repo_root: Path) -> List[Finding]:
    """Verify all expected skill files exist on disk."""
    findings: List[Finding] = []
    skill_base = config['paths']['skill_base']
    for name in config['skills']:
        path = get_skill_path(name, skill_base, repo_root)
        if path.exists():
            lines = count_lines(path)
            findings.append(Finding(
                check='skill_files_exist', target=name,
                status='PASS', message=f'{name}/SKILL.md exists ({lines} lines)',
            ))
        else:
            findings.append(Finding(
                check='skill_files_exist', target=name,
                status='FAIL', message=f'{name}/SKILL.md NOT FOUND',
                severity='critical',
            ))
    return findings


def check_owner_headers(config: Dict, repo_root: Path) -> List[Finding]:
    """Ensure owner tag is present in all skill and doc files."""
    findings: List[Finding] = []
    owner = config.get('owner', {})
    owner_idsid = owner.get('idsid', '')
    if not owner_idsid:
        findings.append(Finding(
            check='owner_headers', target='config',
            status='SKIP', message='No owner.idsid in config, skipping',
        ))
        return findings

    skill_base = config['paths']['skill_base']
    # Check skill files
    for name in config['skills']:
        path = get_skill_path(name, skill_base, repo_root)
        if not path.exists():
            continue
        content = read_file(path)
        # Check first 30 lines for owner tag (allows for YAML frontmatter)
        header = '\n'.join(content.split('\n')[:30])
        if owner_idsid in header:
            findings.append(Finding(
                check='owner_headers', target=f'{name}/SKILL.md',
                status='PASS', message=f'Owner tag ({owner_idsid}) present',
            ))
        else:
            findings.append(Finding(
                check='owner_headers', target=f'{name}/SKILL.md',
                status='FAIL', message=f'Owner tag ({owner_idsid}) missing from header',
                severity='medium',
            ))

    # Check doc files
    docs_dir = resolve_path(config['paths'].get('docs_dir', ''), repo_root)
    if docs_dir.is_dir():
        for doc_file in sorted(docs_dir.glob('*.md')):
            content = read_file(doc_file)
            header = '\n'.join(content.split('\n')[:30])
            if owner_idsid in header:
                findings.append(Finding(
                    check='owner_headers', target=doc_file.name,
                    status='PASS', message='Owner tag present',
                ))
            else:
                findings.append(Finding(
                    check='owner_headers', target=doc_file.name,
                    status='FAIL', message=f'Owner tag ({owner_idsid}) missing',
                    severity='low',
                ))
    return findings


def check_frontmatter(config: Dict, repo_root: Path) -> List[Finding]:
    """Validate YAML frontmatter in skill files."""
    findings: List[Finding] = []
    skill_base = config['paths']['skill_base']

    for name in config['skills']:
        path = get_skill_path(name, skill_base, repo_root)
        if not path.exists():
            continue
        content = read_file(path)
        if not content.startswith('---'):
            findings.append(Finding(
                check='frontmatter', target=f'{name}/SKILL.md',
                status='FAIL', message='No YAML frontmatter found',
                severity='medium',
            ))
            continue

        # Extract frontmatter
        fm_end = content.find('---', 3)
        if fm_end < 0:
            findings.append(Finding(
                check='frontmatter', target=f'{name}/SKILL.md',
                status='FAIL', message='Unclosed YAML frontmatter',
                severity='medium',
            ))
            continue

        fm_text = content[3:fm_end].strip()
        try:
            fm = yaml.safe_load(fm_text)
            if not isinstance(fm, dict):
                raise ValueError("Frontmatter is not a dict")
        except Exception as e:
            findings.append(Finding(
                check='frontmatter', target=f'{name}/SKILL.md',
                status='FAIL', message=f'Invalid YAML: {e}',
                severity='medium',
            ))
            continue

        # Check required fields
        for required_field in ['name', 'description']:
            if required_field in fm:
                findings.append(Finding(
                    check='frontmatter', target=f'{name}/SKILL.md',
                    status='PASS', message=f'Has {required_field} field',
                ))
            else:
                findings.append(Finding(
                    check='frontmatter', target=f'{name}/SKILL.md',
                    status='WARN', message=f'Missing {required_field} field in frontmatter',
                    severity='low',
                ))
    return findings


def check_subskill_count(config: Dict, repo_root: Path) -> List[Finding]:
    """Compare expected skill count vs actual directories."""
    findings: List[Finding] = []
    skill_base_path = resolve_path(config['paths']['skill_base'], repo_root)
    expected = set(config['skills'])

    if not skill_base_path.is_dir():
        findings.append(Finding(
            check='subskill_count', target='skill_base',
            status='ERROR', message=f'Skill base directory not found: {skill_base_path}',
            severity='critical',
        ))
        return findings

    # Find actual skill directories (those containing SKILL.md)
    actual = set()
    for d in skill_base_path.iterdir():
        if d.is_dir() and (d / 'SKILL.md').exists():
            actual.add(d.name)

    if expected == actual:
        findings.append(Finding(
            check='subskill_count', target='skills',
            status='PASS', message=f'Expected {len(expected)} skills, found {len(actual)} — match',
        ))
    else:
        missing = expected - actual
        extra = actual - expected
        if missing:
            findings.append(Finding(
                check='subskill_count', target='skills',
                status='FAIL', message=f'Missing skill dirs: {sorted(missing)}',
                severity='high',
            ))
        if extra:
            findings.append(Finding(
                check='subskill_count', target='skills',
                status='WARN', message=f'Unexpected skill dirs: {sorted(extra)}',
                severity='low',
            ))
    return findings


def check_doc_files_exist(config: Dict, repo_root: Path) -> List[Finding]:
    """Check for expected documentation files."""
    findings: List[Finding] = []
    docs = config.get('docs', [])
    if not docs:
        findings.append(Finding(
            check='doc_files_exist', target='config',
            status='SKIP', message='No docs list in config',
        ))
        return findings

    docs_dir = resolve_path(config['paths'].get('docs_dir', ''), repo_root)
    for doc_name in docs:
        path = docs_dir / doc_name
        if path.exists():
            findings.append(Finding(
                check='doc_files_exist', target=doc_name,
                status='PASS', message=f'{doc_name} exists ({count_lines(path)} lines)',
            ))
        else:
            findings.append(Finding(
                check='doc_files_exist', target=doc_name,
                status='FAIL', message=f'{doc_name} NOT FOUND in {docs_dir}',
                severity='medium',
            ))
    return findings


def check_eval_files(config: Dict, repo_root: Path) -> List[Finding]:
    """Verify eval test files exist and have reasonable content."""
    findings: List[Finding] = []
    eval_dir = resolve_path(config['paths'].get('eval_dir', ''), repo_root)

    if not eval_dir.is_dir():
        findings.append(Finding(
            check='eval_files', target='eval_dir',
            status='WARN', message=f'Eval directory not found: {eval_dir}',
            severity='low',
        ))
        return findings

    md_files = list(eval_dir.glob('*.md'))
    if not md_files:
        findings.append(Finding(
            check='eval_files', target='eval_dir',
            status='WARN', message='No .md eval test files found',
            severity='medium',
        ))
    else:
        for f in md_files:
            lines = count_lines(f)
            findings.append(Finding(
                check='eval_files', target=f.name,
                status='PASS' if lines > 10 else 'WARN',
                message=f'{f.name}: {lines} lines',
            ))
    return findings


def check_cross_references(config: Dict, repo_root: Path) -> List[Finding]:
    """Validate cross-references between skill files are bidirectional."""
    findings: List[Finding] = []
    skill_base = config['paths']['skill_base']
    xref_rules = config.get('self_check', {}).get('cross_references', {})

    if not xref_rules:
        # Auto-detect: scan for cross-references in all skill files
        skills = get_all_skill_paths(config['skills'], skill_base, repo_root)
        for name, path in skills.items():
            if not path.exists():
                continue
            content = read_file(path)
            # Look for references to sibling skills
            for other_name in config['skills']:
                if other_name == name:
                    continue
                if other_name in content:
                    findings.append(Finding(
                        check='cross_references', target=f'{name}->{other_name}',
                        status='PASS', message=f'{name} references {other_name}',
                    ))
        if not findings:
            findings.append(Finding(
                check='cross_references', target='all',
                status='SKIP', message='No cross-reference rules or detected references',
            ))
        return findings

    # Rule-based: check expected/excluded references
    for skill_name, rules in xref_rules.items():
        path = get_skill_path(skill_name, skill_base, repo_root)
        if not path.exists():
            continue
        content = read_file(path)
        for expected_ref in rules.get('expected', []):
            if expected_ref in content:
                findings.append(Finding(
                    check='cross_references', target=f'{skill_name}->{expected_ref}',
                    status='PASS', message=f'Expected reference to {expected_ref} found',
                ))
            else:
                findings.append(Finding(
                    check='cross_references', target=f'{skill_name}->{expected_ref}',
                    status='FAIL', message=f'Expected reference to {expected_ref} NOT found',
                    severity='medium',
                ))
        for excluded_ref in rules.get('excluded', []):
            if excluded_ref in content:
                findings.append(Finding(
                    check='cross_references', target=f'{skill_name}->{excluded_ref}',
                    status='WARN', message=f'Excluded reference to {excluded_ref} found',
                    severity='low',
                ))
    return findings


def check_stale_references(config: Dict, repo_root: Path) -> List[Finding]:
    """Scan for known outdated/stale values configured by the user."""
    findings: List[Finding] = []
    stale_patterns = config.get('self_check', {}).get('stale_patterns', [])

    if not stale_patterns:
        findings.append(Finding(
            check='stale_references', target='config',
            status='SKIP', message='No stale_patterns in config',
        ))
        return findings

    skill_base = config['paths']['skill_base']
    for pattern_def in stale_patterns:
        pattern = pattern_def.get('pattern', '')
        description = pattern_def.get('description', pattern)
        severity = pattern_def.get('severity', 'high')

        for name in config['skills']:
            path = get_skill_path(name, skill_base, repo_root)
            if not path.exists():
                continue
            matches = find_pattern_in_file(path, pattern)
            if matches:
                findings.append(Finding(
                    check='stale_references', target=f'{name}/SKILL.md',
                    status='FAIL',
                    message=f'Stale pattern found: {description}',
                    severity=severity,
                    details=f'Lines: {[m[0] for m in matches[:5]]}',
                ))
            else:
                findings.append(Finding(
                    check='stale_references', target=f'{name}/SKILL.md',
                    status='PASS', message=f'No stale pattern: {description}',
                ))
    return findings


def check_agent_definition(config: Dict, repo_root: Path) -> List[Finding]:
    """Validate the agent definition file exists and has proper structure."""
    findings: List[Finding] = []
    agent_path_str = config['paths'].get('agent_def', '')
    if not agent_path_str:
        findings.append(Finding(
            check='agent_definition', target='config',
            status='SKIP', message='No agent_def in config paths',
        ))
        return findings

    agent_path = resolve_path(agent_path_str, repo_root)
    if not agent_path.exists():
        findings.append(Finding(
            check='agent_definition', target=agent_path.name,
            status='FAIL', message='Agent definition file not found',
            severity='critical',
        ))
        return findings

    content = read_file(agent_path)
    lines = content.split('\n')

    # Check frontmatter
    if content.startswith('---'):
        findings.append(Finding(
            check='agent_definition', target=agent_path.name,
            status='PASS', message='Has YAML frontmatter',
        ))
    else:
        findings.append(Finding(
            check='agent_definition', target=agent_path.name,
            status='FAIL', message='Missing YAML frontmatter',
            severity='high',
        ))

    # Check it references skills
    skill_count = sum(1 for s in config['skills'] if s in content)
    if skill_count > 0:
        findings.append(Finding(
            check='agent_definition', target=agent_path.name,
            status='PASS', message=f'References {skill_count}/{len(config["skills"])} skills',
        ))
    else:
        findings.append(Finding(
            check='agent_definition', target=agent_path.name,
            status='WARN', message='Does not reference any configured skills',
            severity='medium',
        ))

    findings.append(Finding(
        check='agent_definition', target=agent_path.name,
        status='PASS', message=f'Agent def exists ({len(lines)} lines)',
    ))
    return findings


# ── Check Registry ───────────────────────────────────────────────────

ALL_CHECKS: List[Tuple[str, Callable]] = [
    ('skill_files_exist', check_skill_files_exist),
    ('owner_headers', check_owner_headers),
    ('frontmatter', check_frontmatter),
    ('subskill_count', check_subskill_count),
    ('doc_files_exist', check_doc_files_exist),
    ('eval_files', check_eval_files),
    ('cross_references', check_cross_references),
    ('stale_references', check_stale_references),
    ('agent_definition', check_agent_definition),
]

# Pre-commit runs a subset for speed
PRE_COMMIT_CHECKS = {
    'skill_files_exist', 'owner_headers', 'frontmatter', 'stale_references',
}


def run_all_checks(
    config: Dict[str, Any],
    repo_root: Optional[Path] = None,
    checks: Optional[List[str]] = None,
    pre_commit: bool = False,
) -> Report:
    """Run all (or selected) structural checks."""
    root = repo_root or find_repo_root()
    report = Report(name='self-check', version=config.get('_version', '1.0'))

    active_checks = ALL_CHECKS
    if pre_commit:
        active_checks = [(n, fn) for n, fn in ALL_CHECKS if n in PRE_COMMIT_CHECKS]
    elif checks:
        check_set = set(checks)
        active_checks = [(n, fn) for n, fn in ALL_CHECKS if n in check_set]

    for name, fn in active_checks:
        try:
            results = fn(config, root)
            for f in results:
                report.add(f)
        except Exception as e:
            report.add(Finding(
                check=name, target='runner',
                status='ERROR', message=f'Check crashed: {e}',
                severity='critical',
            ))

    return report


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description='Generic Skill Self-Check')
    parser.add_argument('--config', type=Path, required=True,
                        help='Path to self_improvement_config.json')
    parser.add_argument('--check', type=str, nargs='*',
                        help='Run only specific checks')
    parser.add_argument('--pre-commit', action='store_true',
                        help='Run reduced pre-commit subset')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--save', type=Path,
                        help='Save report to file or directory')
    args = parser.parse_args()

    config = load_config(args.config)
    report = run_all_checks(
        config,
        checks=args.check,
        pre_commit=args.pre_commit,
    )

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    if args.save:
        fmt = 'json' if args.json else 'text'
        saved = report.save(args.save, fmt)
        print(f"\nSaved to: {saved}", file=sys.stderr)

    summary = report.compute_summary()
    if summary.get('FAIL', 0) > 0 or summary.get('ERROR', 0) > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
