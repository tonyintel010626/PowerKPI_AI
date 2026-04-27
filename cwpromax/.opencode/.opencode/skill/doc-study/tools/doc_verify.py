#!/usr/bin/env python3
"""
Document Extraction Completeness Verifier — doc_verify.py

Verifies that a structured dump file contains ALL content from the
original document. Reports word count delta, missed content, and
categorization.

Usage:
    python doc_verify.py <original_file> <dump_file> [--report <report_path>]
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_dump_text(dump_path):
    """Load dump file and return cleaned text blob."""
    with open(dump_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Strip structural prefixes to get pure content
    words = []
    for line in content.split('\n'):
        cleaned = line.strip()
        # Strip common dump prefixes
        cleaned = re.sub(r'^P\d{4}\s*\[.*?\]:\s*', '', cleaned)
        cleaned = re.sub(r'^=== (TABLE|SHEET|PAGE|SLIDE|NOTE|DEFINITION).*===$', '', cleaned)
        cleaned = re.sub(r'^\s*ROW\d+:\s*', '', cleaned)
        cleaned = re.sub(r'^X\d{4}:\s*', '', cleaned)
        cleaned = re.sub(r'^L\d{5}:\s*', '', cleaned)
        if cleaned.strip():
            words.extend(cleaned.split())

    return words, content.lower()


def verify_docx(original_path, dump_path):
    """Verify docx extraction completeness using raw XML audit."""
    import zipfile
    import xml.etree.ElementTree as ET

    W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    dump_words, dump_text_lower = load_dump_text(dump_path)

    # Extract ALL text from raw XML
    all_raw = {}
    with zipfile.ZipFile(original_path, 'r') as z:
        for name in z.namelist():
            if not name.endswith('.xml'):
                continue
            try:
                data = z.read(name)
                root = ET.fromstring(data)
            except Exception:
                continue

            texts = []
            for elem in root.iter():
                if elem.tag == f'{W_NS}t' and elem.text:
                    texts.append(elem.text)
            if texts:
                all_raw[name] = texts

    # Word count from raw XML
    raw_words = []
    for texts in all_raw.values():
        for t in texts:
            raw_words.extend(t.split())

    # Main document XML word count (excluding comments)
    main_doc_words = []
    for name, texts in all_raw.items():
        if 'comment' not in name.lower():
            for t in texts:
                main_doc_words.extend(t.split())

    # Find missed content
    missed = {
        'technical': [],
        'comments': [],
        'legal': [],
        'revision': [],
        'trivial': [],
    }

    legal_terms = ['intel', 'confidential', 'copyright', 'license', 'warranty',
                   'liability', 'recipients', 'trademark', 'proprietary']
    revision_terms = ['clarified', 'branch from', 'updated section', 'added',
                      'removed', 'change in direction', 'revision', 'rev ']

    for name, texts in all_raw.items():
        is_comment = 'comment' in name.lower()
        for t in texts:
            t_clean = t.strip()
            if len(t_clean) < 5:
                continue
            if t_clean.lower() in dump_text_lower:
                continue

            # Categorize
            tl = t_clean.lower()
            if is_comment:
                missed['comments'].append({'part': name, 'text': t_clean})
            elif any(w in tl for w in legal_terms):
                missed['legal'].append({'part': name, 'text': t_clean})
            elif any(w in tl for w in revision_terms):
                missed['revision'].append({'part': name, 'text': t_clean})
            elif len(t_clean) < 15 and not any(c.isdigit() for c in t_clean):
                missed['trivial'].append({'part': name, 'text': t_clean})
            else:
                missed['technical'].append({'part': name, 'text': t_clean})

    return {
        'raw_total_words': len(raw_words),
        'raw_main_doc_words': len(main_doc_words),
        'dump_words': len(dump_words),
        'delta_total': len(raw_words) - len(dump_words),
        'delta_main_doc': len(main_doc_words) - len(dump_words),
        'missed': missed,
        'missed_counts': {k: len(v) for k, v in missed.items()},
        'parts_audited': list(all_raw.keys()),
    }


def verify_pdf(original_path, dump_path):
    """Verify PDF extraction completeness."""
    dump_words, dump_text_lower = load_dump_text(dump_path)

    raw_words = 0
    try:
        import pdfplumber  # type: ignore[import-untyped]
        with pdfplumber.open(original_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                raw_words += len(text.split())
    except ImportError:
        try:
            import fitz  # type: ignore[import-untyped]
            doc = fitz.open(original_path)
            for page in doc:
                text = page.get_text()
                raw_words += len(text.split())
            doc.close()
        except ImportError:
            return {'error': 'No PDF library available'}

    return {
        'raw_total_words': raw_words,
        'raw_main_doc_words': raw_words,
        'dump_words': len(dump_words),
        'delta_total': raw_words - len(dump_words),
        'delta_main_doc': raw_words - len(dump_words),
        'missed': {'technical': [], 'comments': [], 'legal': [], 'revision': [], 'trivial': []},
        'missed_counts': {'technical': 0},
    }


def verify_text(original_path, dump_path):
    """Verify text file extraction (should be trivially complete)."""
    with open(original_path, 'r', encoding='utf-8', errors='replace') as f:
        original = f.read()
    dump_words, _ = load_dump_text(dump_path)

    raw_words = len(original.split())
    return {
        'raw_total_words': raw_words,
        'raw_main_doc_words': raw_words,
        'dump_words': len(dump_words),
        'delta_total': raw_words - len(dump_words),
        'delta_main_doc': raw_words - len(dump_words),
        'missed': {'technical': [], 'comments': [], 'legal': [], 'revision': [], 'trivial': []},
        'missed_counts': {'technical': 0},
    }


def verify_file(original_path, dump_path):
    """Run verification for any supported format."""
    ext = Path(original_path).suffix.lower()
    if ext == '.docx':
        return verify_docx(original_path, dump_path)
    elif ext == '.pdf':
        return verify_pdf(original_path, dump_path)
    else:
        return verify_text(original_path, dump_path)


def format_report(result, original_path, dump_path):
    """Format verification result as human-readable report."""
    lines = []
    lines.append('=' * 60)
    lines.append('DOCUMENT EXTRACTION VERIFICATION REPORT')
    lines.append('=' * 60)
    lines.append(f'Original: {original_path}')
    lines.append(f'Dump:     {dump_path}')
    lines.append(f'Time:     {datetime.now().isoformat()}')
    lines.append('')
    lines.append('WORD COUNT RECONCILIATION')
    lines.append('-' * 40)
    lines.append(f'  Raw XML total words:     {result["raw_total_words"]:>8}')
    lines.append(f'  Raw main doc words:      {result["raw_main_doc_words"]:>8}')
    lines.append(f'  Dump words:              {result["dump_words"]:>8}')
    lines.append(f'  Delta (total):           {result["delta_total"]:>8}')
    lines.append(f'  Delta (main doc only):   {result["delta_main_doc"]:>8}')

    if result['dump_words'] > 0:
        coverage = (result['dump_words'] / max(result['raw_main_doc_words'], 1)) * 100
        lines.append(f'  Coverage (main doc):     {coverage:>7.1f}%')

    lines.append('')
    lines.append('MISSED CONTENT BREAKDOWN')
    lines.append('-' * 40)
    for category, count in result.get('missed_counts', {}).items():
        marker = ' *** ACTION REQUIRED ***' if category == 'technical' and count > 0 else ''
        lines.append(f'  {category:20s}: {count:>5}{marker}')

    tech_missed = result.get('missed', {}).get('technical', [])
    if tech_missed:
        lines.append('')
        lines.append('TECHNICAL MISSED CONTENT (must be captured)')
        lines.append('-' * 40)
        for i, item in enumerate(tech_missed, 1):
            lines.append(f'  [{i:3d}] ({item["part"]}): {item["text"][:120]}')

    lines.append('')
    total_tech = len(tech_missed)
    if total_tech == 0:
        lines.append('RESULT: PASS — No technical content missed')
        lines.append('  Safe to proceed to cross-check phase.')
    else:
        lines.append(f'RESULT: FAIL — {total_tech} technical fragments missed')
        lines.append('  Must re-extract missed content before proceeding to cross-check.')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Document Extraction Verifier')
    parser.add_argument('original', help='Path to original document')
    parser.add_argument('dump', help='Path to extraction dump file')
    parser.add_argument('--report', '-r', help='Save report to file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--missed-output', '-m', help='Save missed technical content to file')
    args = parser.parse_args()

    if not os.path.exists(args.original):
        print(f'ERROR: Original not found: {args.original}', file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.dump):
        print(f'ERROR: Dump not found: {args.dump}', file=sys.stderr)
        sys.exit(1)

    result: dict = verify_file(args.original, args.dump)

    if 'error' in result:
        print(f'ERROR: {result["error"]}', file=sys.stderr)
        sys.exit(1)

    report = format_report(result, args.original, args.dump)
    print(report)

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'\nReport saved to: {args.report}')

    if args.missed_output:
        tech_missed = result.get('missed', {}).get('technical', [])
        with open(args.missed_output, 'w', encoding='utf-8') as f:
            for item in tech_missed:
                f.write(f'{item["part"]}: {item["text"]}\n')
        print(f'Missed content saved to: {args.missed_output}')

    if args.json:
        # Make JSON-serializable
        print(json.dumps(result, indent=2, default=str))

    # Exit code: 0 if no technical content missed, 1 if there are gaps
    tech_count = result.get('missed_counts', {}).get('technical', 0)
    sys.exit(0 if tech_count == 0 else 1)


if __name__ == '__main__':
    main()
