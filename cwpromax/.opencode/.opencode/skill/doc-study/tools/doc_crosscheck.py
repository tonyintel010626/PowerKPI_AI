#!/usr/bin/env python3
"""
Document-to-Skill Cross-Checker — doc_crosscheck.py

Cross-checks every technical fact in a document extraction dump
against target skill files. Reports CONFIRMED, MISSING, WRONG, and
NEW findings.

Usage:
    python doc_crosscheck.py <dump_path> <skill_dir> [--exclude <file.json>] [--report <path>]
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_dump(dump_path):
    """Load structured dump and extract fact candidates."""
    with open(dump_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    facts = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip structural markers
        if re.match(r'^===\s', stripped):
            continue

        # Extract content after prefix
        content = stripped
        content = re.sub(r'^P\d{4}\s*\[.*?\]:\s*', '', content)
        content = re.sub(r'^\s*ROW\d+:\s*', '', content)
        content = re.sub(r'^X\d{4}:\s*', '', content)
        content = re.sub(r'^L\d{5}:\s*', '', content)

        if len(content.strip()) < 10:
            continue

        facts.append({
            'line': i,
            'raw': stripped,
            'content': content.strip(),
        })

    return facts


def load_skill_files(skill_dir):
    """Load all .md files in the skill directory (recursively)."""
    skills = {}
    skill_path = Path(skill_dir)

    for md_file in skill_path.rglob('*.md'):
        rel = str(md_file.relative_to(skill_path))
        with open(md_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        skills[rel] = {
            'path': str(md_file),
            'content': content,
            'content_lower': content.lower(),
        }

    return skills


def extract_key_terms(text):
    """Extract significant technical terms from a line of text."""
    terms = set()

    # Hex values
    for m in re.finditer(r'0x[0-9A-Fa-f]+', text):
        terms.add(m.group().lower())

    # Register names (UPPER_CASE_WORDS)
    for m in re.finditer(r'\b[A-Z][A-Z0-9_]{3,}\b', text):
        terms.add(m.group().lower())

    # Numeric constants with units
    for m in re.finditer(r'\b\d+\s*(MHz|kHz|ms|us|µs|ns|KB|MB|GB|bytes?|bits?)\b', text, re.I):
        terms.add(m.group().lower())

    # UUIDs
    for m in re.finditer(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', text):
        terms.add(m.group().lower())

    # Technical abbreviations
    for m in re.finditer(r'\b(DMA|PRD|SPI|I2C|THC|TIC|DSM|ACPI|GPIO|LTR|PIO|ISR|DPC|HCNT|LCNT|RXDMA|TXDMA|SWDMA)\b', text, re.I):
        terms.add(m.group().lower())

    return terms


def crosscheck_fact(fact, skills, threshold=0.6):
    """Check if a fact is present in any skill file.

    Returns (status, file, details) where status is:
    - CONFIRMED: fact found in a skill file
    - MISSING: fact not found in any skill file
    - PARTIAL: some terms found, but not the full fact
    """
    content = fact['content']
    content_lower = content.lower()
    key_terms = extract_key_terms(content)

    best_match = None
    best_score = 0

    for rel_path, skill in skills.items():
        # Exact substring match
        if content_lower in skill['content_lower']:
            return 'CONFIRMED', rel_path, 'Exact match'

        # Key term matching
        if key_terms:
            found_terms = sum(1 for t in key_terms if t in skill['content_lower'])
            score = found_terms / len(key_terms)
            if score > best_score:
                best_score = score
                best_match = rel_path

        # Significant phrase matching (3+ word sequences)
        words = content_lower.split()
        if len(words) >= 5:
            # Check 5-word windows
            for i in range(len(words) - 4):
                phrase = ' '.join(words[i:i+5])
                if phrase in skill['content_lower']:
                    return 'CONFIRMED', rel_path, f'Phrase match: "{phrase}"'

    if best_score >= threshold:
        return 'PARTIAL', best_match, f'Key terms {best_score:.0%} match'

    return 'MISSING', best_match or '(no match)', f'Best score: {best_score:.0%}'


def run_crosscheck(dump_path, skill_dir, exclude_file=None):
    """Run full cross-check of dump against skill files."""
    facts = load_dump(dump_path)
    skills = load_skill_files(skill_dir)

    # Load exclusions
    exclusions = set()
    if exclude_file and os.path.exists(exclude_file):
        with open(exclude_file, 'r') as f:
            exclusion_data = json.load(f)
        exclusions = set(exclusion_data.get('applied', []))

    results = {
        'CONFIRMED': [],
        'MISSING': [],
        'PARTIAL': [],
    }

    for fact in facts:
        # Skip if in exclusion list
        if any(exc in fact['content'] for exc in exclusions):
            continue

        status, file_match, details = crosscheck_fact(fact, skills)
        results[status].append({
            'line': fact['line'],
            'content': fact['content'][:200],
            'status': status,
            'matched_file': file_match,
            'details': details,
        })

    return {
        'dump_path': dump_path,
        'skill_dir': skill_dir,
        'total_facts': len(facts),
        'results': results,
        'counts': {k: len(v) for k, v in results.items()},
        'skill_files_checked': list(skills.keys()),
    }


def format_report(result):
    """Format cross-check results as a human-readable report."""
    lines = []
    lines.append('=' * 60)
    lines.append('DOCUMENT CROSS-CHECK REPORT')
    lines.append('=' * 60)
    lines.append(f'Dump:        {result["dump_path"]}')
    lines.append(f'Skill dir:   {result["skill_dir"]}')
    lines.append(f'Time:        {datetime.now().isoformat()}')
    lines.append(f'Total facts: {result["total_facts"]}')
    lines.append('')
    lines.append('SUMMARY')
    lines.append('-' * 40)
    for status, count in result['counts'].items():
        lines.append(f'  {status:12s}: {count:>5}')
    lines.append('')

    lines.append(f'Skill files checked ({len(result["skill_files_checked"])}):')
    for sf in result['skill_files_checked']:
        lines.append(f'  - {sf}')
    lines.append('')

    # MISSING findings (most important)
    missing = result['results'].get('MISSING', [])
    if missing:
        lines.append(f'MISSING FINDINGS ({len(missing)}) — require addition to skill files')
        lines.append('-' * 60)
        for i, item in enumerate(missing, 1):
            lines.append(f'  [{i:3d}] Line {item["line"]}: {item["content"][:120]}')
            lines.append(f'        Nearest file: {item["matched_file"]}')
        lines.append('')

    # PARTIAL findings
    partial = result['results'].get('PARTIAL', [])
    if partial:
        lines.append(f'PARTIAL FINDINGS ({len(partial)}) — may need review')
        lines.append('-' * 60)
        for i, item in enumerate(partial, 1):
            lines.append(f'  [{i:3d}] Line {item["line"]}: {item["content"][:120]}')
            lines.append(f'        File: {item["matched_file"]} ({item["details"]})')

    total_issues = len(missing) + len(partial)
    lines.append('')
    if total_issues == 0:
        lines.append('RESULT: PASS — All facts confirmed in skill files')
    else:
        lines.append(f'RESULT: {len(missing)} MISSING, {len(partial)} PARTIAL — review required')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Document-to-Skill Cross-Checker')
    parser.add_argument('dump', help='Path to extraction dump file')
    parser.add_argument('skill_dir', help='Path to skill directory to check against')
    parser.add_argument('--exclude', help='JSON file with previously applied findings to skip')
    parser.add_argument('--report', '-r', help='Save report to file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    if not os.path.exists(args.dump):
        print(f'ERROR: Dump not found: {args.dump}', file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.skill_dir):
        print(f'ERROR: Skill dir not found: {args.skill_dir}', file=sys.stderr)
        sys.exit(1)

    result = run_crosscheck(args.dump, args.skill_dir, args.exclude)
    report = format_report(result)
    print(report)

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'\nReport saved to: {args.report}')

    if args.json:
        print(json.dumps(result, indent=2, default=str))

    missing_count = result['counts'].get('MISSING', 0)
    sys.exit(0 if missing_count == 0 else 1)


if __name__ == '__main__':
    main()
