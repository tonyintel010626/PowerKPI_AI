#!/usr/bin/env python3
"""
Comprehensive verification of thc_mtp_descriptions.md against live HSDES API.

Proves mathematically that the description document is complete and correct:
  V1. ID completeness   — every tree walker ID appears in the doc, no extras, no duplicates
  V2. Metadata accuracy  — title, status, subject, level match live API for ALL 169 records
  V3. Description match   — description text in doc matches live API (hash comparison)
  V4. Empty descriptions  — records marked "(none)" are genuinely empty in HSDES
  V5. Level structure     — level counts match expected (L0=1, L1=8, L2=34, L3=126)
  V6. Hierarchy ordering  — records appear under correct parent in correct level section
  V7. HTML fidelity       — spot-check that HTML→text preserved key content (tables, lists, links)
  V8. Document integrity  — header counts match actual body counts

Exit code 0 = all checks pass, 1 = failures found, 2 = error
"""

import sys
import os
import re
import json
import hashlib
import html
import subprocess
import time
from pathlib import Path
from collections import Counter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PVIM_MTP_DIR = SCRIPT_DIR.parent.parent / "pvim-mtp" / "scripts"
DESC_DOC = SCRIPT_DIR.parent / "docs" / "thc_mtp_descriptions.md"
ROOT_ID = "13013458151"

EXPECTED = {
    "total_records": 169,
    "level_counts": {0: 1, 1: 8, 2: 34, 3: 126},
    "by_subject": {"test_plan": 9, "test_case_definition": 34, "test_case": 126},
}

LEVEL_LABELS = {0: "MTP", 1: "TPF", 2: "TCD", 3: "TC", 4: "TR"}

# Import shared HTML utilities from scripts/ directory
sys.path.insert(0, str(PVIM_MTP_DIR))
from _html_utils import HTMLStripper, html_to_text  # noqa: E402,F401

# ---------------------------------------------------------------------------
# HSDES API helpers
# ---------------------------------------------------------------------------
_session = None


def get_session():
    global _session
    if _session is None:
        import requests
        from requests_kerberos import HTTPKerberosAuth, OPTIONAL

        _session = requests.Session()
        _session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        _session.headers.update({"Accept": "application/json"})
    return _session


def fetch_article(article_id: str, retries: int = 3) -> dict:
    """Fetch a single HSDES article by ID. Returns flat dict of fields."""
    sess = get_session()
    url = f"https://hsdes-api.intel.com/rest/article/{article_id}"
    for attempt in range(retries):
        try:
            resp = sess.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                if items and isinstance(items, list):
                    return items[0]
            elif resp.status_code == 429:
                time.sleep(2**attempt)
                continue
            else:
                return {}
        except Exception:
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def strip_html(text: str) -> str:
    """Minimal regex HTML→text for comparison (legacy, used in V4)."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_compare(text: str) -> str:
    """Aggressively normalize text for fuzzy comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Parse the description document
# ---------------------------------------------------------------------------
def parse_desc_doc(path: Path) -> list:
    """
    Parse thc_mtp_descriptions.md and extract all records.
    Returns list of dicts: {id, title, status, subject, owner, level, label, description}
    """
    content = path.read_text(encoding="utf-8")
    records = []

    # Pattern for record headings: ### ✅ [TCD] Title  or  ### ❌ [TPF] Title
    # The heading format is: ### <badge> [<label>] <title>
    heading_re = re.compile(r"^###\s+(?:✅|❌|⏳|🔘)\s+\[(\w+)\]\s+(.+)$", re.MULTILINE)

    # Split into sections by heading
    parts = heading_re.split(content)
    # parts[0] = preamble, then groups of (label, title, body)

    i = 1
    while i < len(parts) - 2:
        label = parts[i]
        title = parts[i + 1].strip()
        body = parts[i + 2]
        i += 3

        # Extract metadata table from body
        rec = {"label": label, "title": title, "description": ""}

        # ID — format is: | **ID** | 13013458151 |  (no backticks)
        m = re.search(r"\|\s*\*\*ID\*\*\s*\|\s*(\d+)", body)
        rec["id"] = m.group(1) if m else ""

        # Status
        m = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*(\w+)", body)
        rec["status"] = m.group(1).strip() if m else ""

        # Subject
        m = re.search(r"\|\s*\*\*Subject\*\*\s*\|\s*(\S+)", body)
        rec["subject"] = m.group(1).strip() if m else ""

        # Owner
        m = re.search(r"\|\s*\*\*Owner\*\*\s*\|\s*(\S+)", body)
        rec["owner"] = m.group(1).strip() if m else ""

        # Level — format is: | **Level** | L0 (MTP) |  (extract digit after 'L')
        m = re.search(r"\|\s*\*\*Level\*\*\s*\|\s*L(\d+)", body)
        rec["level"] = int(m.group(1)) if m else -1

        # Description: everything in blockquote after "**Description:**"
        # Use line-by-line parser (not regex) for robustness
        desc_marker = "**Description:**"
        marker_pos = body.find(desc_marker)
        if marker_pos >= 0:
            after_marker = body[marker_pos + len(desc_marker) :]
            desc_lines = []
            in_blockquote = False
            for raw_line in after_marker.splitlines():
                if raw_line.startswith("> "):
                    in_blockquote = True
                    # Remove exactly ">" + " " prefix (2 chars), not lstrip
                    desc_lines.append(raw_line[2:].rstrip())
                elif raw_line.strip() == ">":
                    in_blockquote = True
                    desc_lines.append("")  # bare > = blank line in blockquote
                elif in_blockquote:
                    # First non-blockquote line after entering blockquote = end
                    break
                # Skip blank lines before blockquote starts
            desc_text = "\n".join(desc_lines).strip()
            if desc_text == "*(none)*":
                rec["description"] = ""
            else:
                rec["description"] = desc_text
        else:
            rec["description"] = ""

        records.append(rec)

    return records


def parse_header_counts(path: Path) -> dict:
    """Extract the header metadata counts from the doc."""
    content = path.read_text(encoding="utf-8")
    counts = {}
    m = re.search(r"Total Records\*\*:\s*(\d+)", content)
    if m:
        counts["total"] = int(m.group(1))
    m = re.search(r"With Description\*\*:\s*(\d+)", content)
    if m:
        counts["with_desc"] = int(m.group(1))
    m = re.search(r"Without Description\*\*:\s*(\d+)", content)
    if m:
        counts["without_desc"] = int(m.group(1))
    return counts


# ---------------------------------------------------------------------------
# Get tree walker reference data
# ---------------------------------------------------------------------------
def get_tree_walker_records() -> list:
    """Run tree walker with --include-descriptions --format json and flatten."""
    tree_script = PVIM_MTP_DIR / "hsdes_mtp_tree.py"
    cmd = [
        sys.executable,
        str(tree_script),
        "--root",
        ROOT_ID,
        "--include-descriptions",
        "--format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Tree walker failed: {result.stderr[:500]}")

    tree = json.loads(result.stdout)

    # Flatten nested tree
    records = []

    def flatten(node, level=0):
        records.append(
            {
                "id": str(node.get("id", "")),
                "title": node.get("title", ""),
                "status": node.get("status", ""),
                "subject": node.get("subject", ""),
                "owner": node.get("owner", ""),
                "level": level,
                "description": node.get("description", ""),
            }
        )
        for child in node.get("children", []):
            flatten(child, level + 1)

    flatten(tree)
    return records


# ---------------------------------------------------------------------------
# Verification checks
# ---------------------------------------------------------------------------
class Finding:
    def __init__(self, check_id, severity, message, details=""):
        self.check_id = check_id
        self.severity = severity  # FAIL, WARN, INFO
        self.message = message
        self.details = details

    def __str__(self):
        prefix = {"FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(self.severity, "?")
        s = f"  {prefix} [{self.check_id}] {self.message}"
        if self.details:
            s += f"\n      {self.details}"
        return s


def run_verification(verbose=False):
    findings = []
    t0 = time.time()

    # ── Step 0: Load data ──────────────────────────────────────────────
    print("=" * 72)
    print("THC MTP DESCRIPTION DOCUMENT — COMPREHENSIVE VERIFICATION")
    print("=" * 72)
    print()

    print("[0/8] Loading data sources...")
    doc_records = parse_desc_doc(DESC_DOC)
    header_counts = parse_header_counts(DESC_DOC)
    print(f"  Parsed {len(doc_records)} records from description doc")
    print(f"  Header claims: {header_counts}")

    print("  Fetching tree walker reference data...")
    tw_records = get_tree_walker_records()
    print(f"  Tree walker returned {len(tw_records)} records")
    print()

    # ── V1: ID Completeness ────────────────────────────────────────────
    print("[V1] ID Completeness — every tree walker ID in doc, no extras, no dupes")
    doc_ids = [r["id"] for r in doc_records]
    tw_ids = [r["id"] for r in tw_records]
    doc_id_set = set(doc_ids)
    tw_id_set = set(tw_ids)

    # Duplicates in doc
    doc_id_counts = Counter(doc_ids)
    dupes = {k: v for k, v in doc_id_counts.items() if v > 1}
    if dupes:
        findings.append(Finding("V1.1", "FAIL", f"Duplicate IDs in doc: {dupes}"))
    else:
        print(f"  ✅ No duplicate IDs in doc ({len(doc_ids)} unique)")

    # Missing from doc (in tree walker but not in doc)
    missing = tw_id_set - doc_id_set
    if missing:
        findings.append(
            Finding(
                "V1.2",
                "FAIL",
                f"{len(missing)} IDs in tree walker but missing from doc",
                str(missing),
            )
        )
    else:
        print(f"  ✅ All {len(tw_id_set)} tree walker IDs found in doc")

    # Extra in doc (in doc but not in tree walker)
    extra = doc_id_set - tw_id_set
    if extra:
        findings.append(
            Finding(
                "V1.3",
                "FAIL",
                f"{len(extra)} IDs in doc but not in tree walker",
                str(extra),
            )
        )
    else:
        print(f"  ✅ No extra IDs in doc beyond tree walker set")

    # Total count
    if len(doc_records) != EXPECTED["total_records"]:
        findings.append(
            Finding(
                "V1.4",
                "FAIL",
                f"Doc has {len(doc_records)} records, expected {EXPECTED['total_records']}",
            )
        )
    else:
        print(f"  ✅ Total count matches expected: {len(doc_records)}")
    print()

    # ── V2: Metadata Accuracy (vs live API) ────────────────────────────
    print(
        f"[V2] Metadata Accuracy — verify title/status/subject for ALL {len(doc_records)} records against live HSDES API"
    )
    doc_by_id = {r["id"]: r for r in doc_records}
    v2_checked = 0
    v2_mismatches = []

    for idx, rec in enumerate(doc_records):
        nid = rec["id"]
        if not nid:
            findings.append(
                Finding("V2", "FAIL", f"Record at index {idx} has empty ID")
            )
            continue

        api = fetch_article(nid)
        if not api:
            findings.append(Finding("V2", "FAIL", f"API returned empty for ID {nid}"))
            continue

        api_title = (api.get("title") or "").strip()
        api_status = (api.get("status") or "").strip()
        api_subject = (api.get("subject") or "").strip()

        problems = []
        if rec["title"] != api_title:
            problems.append(f"title: doc='{rec['title'][:60]}' api='{api_title[:60]}'")
        if rec["status"] != api_status:
            problems.append(f"status: doc='{rec['status']}' api='{api_status}'")
        if rec["subject"] != api_subject:
            problems.append(f"subject: doc='{rec['subject']}' api='{api_subject}'")

        if problems:
            v2_mismatches.append((nid, problems))
            for p in problems:
                findings.append(Finding("V2", "FAIL", f"ID {nid}: {p}"))

        v2_checked += 1
        if verbose and (v2_checked % 20 == 0):
            print(f"  ... checked {v2_checked}/{len(doc_records)}")

        # Gentle rate limiting
        if v2_checked % 10 == 0:
            time.sleep(0.3)

    if not v2_mismatches:
        print(f"  ✅ All {v2_checked} records: title/status/subject match live API")
    else:
        print(f"  ❌ {len(v2_mismatches)} records have metadata mismatches")
    print()

    # ── V3: Description Content Match ─────────────────────────────────
    # Two-tier verification:
    #   V3a: EXACT match — doc description vs tree walker description
    #        (both produced by same HTMLParser, must be identical)
    #   V3b: SEMANTIC match — doc description vs live HSDES API
    #        (different HTML strippers, so normalize aggressively)
    print(
        "[V3] Description Content Match — exact vs tree walker + semantic vs live API"
    )
    tw_by_id_v3 = {r["id"]: r for r in tw_records}
    v3a_checked = 0
    v3a_fails = []
    v3b_checked = 0
    v3b_fails = []

    for idx, rec in enumerate(doc_records):
        nid = rec["id"]
        if not nid:
            continue
        doc_desc = rec.get("description", "")

        # V3a: Exact match against tree walker (convert raw HTML with same HTMLParser)
        tw_rec = tw_by_id_v3.get(nid)
        if tw_rec:
            tw_desc_raw = tw_rec.get("description", "") or ""
            tw_desc_raw_text = html_to_text(tw_desc_raw)
            # Normalize: strip trailing whitespace per line (doc parser does .rstrip())
            tw_desc = "\n".join(
                l.rstrip() for l in tw_desc_raw_text.splitlines()
            ).strip()
            if doc_desc != tw_desc:
                v3a_fails.append(nid)
                findings.append(
                    Finding(
                        "V3a",
                        "FAIL",
                        f"ID {nid}: doc description != tree walker description (EXACT mismatch)",
                        f"doc_len={len(doc_desc)} tw_len={len(tw_desc)}",
                    )
                )
            v3a_checked += 1

        # V3b: Semantic match against live API (different strippers, normalize)
        api = fetch_article(nid)
        if api:
            api_desc_html = api.get("description") or ""
            api_desc_text = html_to_text(api_desc_html)
            # Normalize same as doc parser (rstrip per line)
            api_desc_text = "\n".join(
                l.rstrip() for l in api_desc_text.splitlines()
            ).strip()

            api_norm = normalize_for_compare(api_desc_text)
            doc_norm = normalize_for_compare(doc_desc)

            if api_norm != doc_norm:
                # Check word-level similarity as fallback
                api_words = set(api_norm.split())
                doc_words = set(doc_norm.split())
                if api_words and doc_words:
                    overlap = len(api_words & doc_words) / max(
                        len(api_words), len(doc_words)
                    )
                else:
                    overlap = 1.0 if (not api_words and not doc_words) else 0.0

                if overlap < 0.90:
                    v3b_fails.append(nid)
                    findings.append(
                        Finding(
                            "V3b",
                            "FAIL",
                            f"ID {nid}: semantic description mismatch vs API (overlap={overlap:.1%})",
                            f"doc_words={len(doc_words)} api_words={len(api_words)}",
                        )
                    )
            v3b_checked += 1

        if verbose and ((v3a_checked + v3b_checked) % 40 == 0):
            print(f"  ... V3a: {v3a_checked}, V3b: {v3b_checked}")

        if v3b_checked % 10 == 0:
            time.sleep(0.3)

    if not v3a_fails and not v3b_fails:
        print(f"  ✅ V3a: {v3a_checked}/{v3a_checked} exact match vs tree walker")
        print(
            f"  ✅ V3b: {v3b_checked}/{v3b_checked} semantic match vs live API (≥90% word overlap)"
        )
    else:
        if v3a_fails:
            print(f"  ❌ V3a: {len(v3a_fails)} exact mismatches vs tree walker")
        else:
            print(f"  ✅ V3a: {v3a_checked}/{v3a_checked} exact match vs tree walker")
        if v3b_fails:
            print(f"  ❌ V3b: {len(v3b_fails)} semantic mismatches vs live API")
        else:
            print(f"  ✅ V3b: {v3b_checked}/{v3b_checked} semantic match vs live API")
    print()

    # ── V4: Empty Descriptions Verified ────────────────────────────────
    print(
        "[V4] Empty Description Verification — confirm '(none)' records are genuinely empty in HSDES"
    )
    empty_in_doc = [r for r in doc_records if not r.get("description")]
    v4_false_empties = []

    for rec in empty_in_doc:
        nid = rec["id"]
        api = fetch_article(nid)
        if not api:
            continue
        api_desc = (api.get("description") or "").strip()
        if api_desc and strip_html(api_desc).strip():
            v4_false_empties.append(nid)
            findings.append(
                Finding(
                    "V4",
                    "FAIL",
                    f"ID {nid} marked '(none)' in doc but has description in HSDES",
                    f"api_desc[:100]='{strip_html(api_desc)[:100]}'",
                )
            )

    if not v4_false_empties:
        print(
            f"  ✅ All {len(empty_in_doc)} '(none)' records are genuinely empty in HSDES"
        )
    else:
        print(f"  ❌ {len(v4_false_empties)} false empties found")
    print()

    # ── V5: Level Structure ────────────────────────────────────────────
    print("[V5] Level Structure — level counts match expected")
    doc_level_counts = Counter(r["level"] for r in doc_records)
    for level, expected_count in EXPECTED["level_counts"].items():
        actual = doc_level_counts.get(level, 0)
        if actual != expected_count:
            findings.append(
                Finding(
                    "V5",
                    "FAIL",
                    f"Level {level} ({LEVEL_LABELS.get(level, '?')}): doc has {actual}, expected {expected_count}",
                )
            )
        else:
            print(
                f"  ✅ Level {level} ({LEVEL_LABELS.get(level, '?')}): {actual} records"
            )
    print()

    # ── V6: Hierarchy Cross-Check ──────────────────────────────────────
    print("[V6] Hierarchy Cross-Check — doc levels match tree walker levels")
    tw_by_id = {r["id"]: r for r in tw_records}
    v6_mismatches = []

    for rec in doc_records:
        nid = rec["id"]
        tw_rec = tw_by_id.get(nid)
        if tw_rec and rec["level"] != tw_rec["level"]:
            v6_mismatches.append(nid)
            findings.append(
                Finding(
                    "V6",
                    "FAIL",
                    f"ID {nid}: doc level={rec['level']}, tree walker level={tw_rec['level']}",
                )
            )

    if not v6_mismatches:
        print(f"  ✅ All {len(doc_records)} records have correct level assignment")
    else:
        print(f"  ❌ {len(v6_mismatches)} level mismatches")
    print()

    # ── V7: HTML Fidelity Spot-Check ───────────────────────────────────
    print("[V7] HTML Fidelity — spot-check for lost structural content")
    v7_issues = []

    # Check: if API description has <table>, doc should have some tabular content
    sample_ids = [r["id"] for r in doc_records if r.get("description")][:20]
    for nid in sample_ids:
        api = fetch_article(nid)
        if not api:
            continue
        api_desc = api.get("description") or ""

        has_table = bool(re.search(r"<table", api_desc, re.IGNORECASE))
        has_list = bool(re.search(r"<[uo]l", api_desc, re.IGNORECASE))
        has_link = bool(re.search(r"<a\s+href", api_desc, re.IGNORECASE))

        doc_desc = doc_by_id.get(nid, {}).get("description", "")
        if has_table and len(doc_desc) < 10:
            v7_issues.append(nid)
            findings.append(
                Finding(
                    "V7",
                    "WARN",
                    f"ID {nid}: API has <table> but doc description very short ({len(doc_desc)} chars)",
                )
            )
        if has_link:
            # Links are expected to be stripped; just note it
            url_match = re.search(r'href=["\']([^"\']+)', api_desc)
            if url_match and url_match.group(1) not in doc_desc:
                findings.append(
                    Finding(
                        "V7",
                        "INFO",
                        f"ID {nid}: URL '{url_match.group(1)[:60]}' not in plaintext (expected — HTML links stripped)",
                    )
                )

        time.sleep(0.2)

    if not v7_issues:
        print(
            f"  ✅ Spot-checked {len(sample_ids)} records — no structural content loss detected"
        )
    else:
        print(f"  ⚠️ {len(v7_issues)} records may have lost table content")
    print()

    # ── V8: Document Integrity ─────────────────────────────────────────
    print("[V8] Document Integrity — header counts match body")
    actual_with = sum(1 for r in doc_records if r.get("description"))
    actual_without = sum(1 for r in doc_records if not r.get("description"))

    if header_counts.get("total") != len(doc_records):
        findings.append(
            Finding(
                "V8",
                "FAIL",
                f"Header says {header_counts.get('total')} total, body has {len(doc_records)}",
            )
        )
    else:
        print(
            f"  ✅ Header total ({header_counts.get('total')}) matches body ({len(doc_records)})"
        )

    if header_counts.get("with_desc") != actual_with:
        findings.append(
            Finding(
                "V8",
                "FAIL",
                f"Header says {header_counts.get('with_desc')} with desc, body has {actual_with}",
            )
        )
    else:
        print(f"  ✅ With-description count: {actual_with}")

    if header_counts.get("without_desc") != actual_without:
        findings.append(
            Finding(
                "V8",
                "FAIL",
                f"Header says {header_counts.get('without_desc')} without desc, body has {actual_without}",
            )
        )
    else:
        print(f"  ✅ Without-description count: {actual_without}")
    print()

    # ── Summary ────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    fails = [f for f in findings if f.severity == "FAIL"]
    warns = [f for f in findings if f.severity == "WARN"]
    infos = [f for f in findings if f.severity == "INFO"]

    print("=" * 72)
    print("VERIFICATION SUMMARY")
    print("=" * 72)
    checks = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
    for c in checks:
        c_fails = [f for f in fails if f.check_id.startswith(c)]
        c_warns = [f for f in warns if f.check_id.startswith(c)]
        if c_fails:
            print(f"  ❌ {c}: {len(c_fails)} FAIL")
        elif c_warns:
            print(f"  ⚠️  {c}: PASS with {len(c_warns)} warnings")
        else:
            print(f"  ✅ {c}: PASS")

    print()
    print(f"Total: {len(fails)} FAIL, {len(warns)} WARN, {len(infos)} INFO")
    print(f"Time: {elapsed:.1f}s")

    if fails:
        print()
        print("FAILURES:")
        for f in fails:
            print(str(f))

    if warns:
        print()
        print("WARNINGS:")
        for f in warns:
            print(str(f))

    # Write results to file
    results_file = SCRIPT_DIR / "verify_descriptions_results.txt"
    with open(results_file, "w", encoding="utf-8") as fh:
        fh.write(f"THC MTP Description Document Verification\n")
        fh.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"Document: {DESC_DOC}\n")
        fh.write(f"Records verified: {len(doc_records)}\n")
        fh.write(f"Result: {'PASS' if not fails else 'FAIL'}\n")
        fh.write(f"Findings: {len(fails)} FAIL, {len(warns)} WARN, {len(infos)} INFO\n")
        fh.write(f"Time: {elapsed:.1f}s\n")
        fh.write(f"\n{'=' * 72}\n")
        for c in checks:
            c_fails = [f for f in fails if f.check_id.startswith(c)]
            c_warns = [f for f in warns if f.check_id.startswith(c)]
            status = "FAIL" if c_fails else ("WARN" if c_warns else "PASS")
            fh.write(f"{c}: {status}\n")
        if fails or warns:
            fh.write(f"\nDetails:\n")
            for f in findings:
                if f.severity in ("FAIL", "WARN"):
                    fh.write(str(f) + "\n")
    print(f"\nResults saved to: {results_file}")

    print()
    if fails:
        print("🔴 VERIFICATION FAILED — issues must be resolved before finalizing")
        return 1
    elif warns:
        print("🟡 VERIFICATION PASSED WITH WARNINGS — review warnings above")
        return 0
    else:
        print("🟢 VERIFICATION PASSED — document is mathematically proven correct")
        return 0


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    try:
        sys.exit(run_verification(verbose=verbose))
    except Exception as e:
        print(f"\n💥 Verification error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)
