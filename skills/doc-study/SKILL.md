---
name: doc-study
description: >-
  Format-agnostic document study skill for extracting, verifying, and cross-checking
  reference documents against skill files. Guarantees 100% content extraction on the
  first pass through a verification-first pipeline.
disable: false
license: MIT
---

# Document Study Skill

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

A standardized, verification-first procedure for studying reference documents of any format.
Guarantees complete content extraction before any cross-checking begins. Eliminates the
need for repeated passes by building verification into every step.

---

## 1. Purpose

When studying a reference document (spec, SwAS, HAS, BWG, datasheet, etc.) to populate
or audit skill files, content extraction must be **provably complete** before cross-checking
begins. This skill encodes the correct procedure so that:

- Every text element is extracted regardless of document format
- Extraction completeness is mathematically verified (word count reconciliation, delta = 0)
- Missed content is automatically identified and categorized
- Cross-checking only begins after extraction is proven complete
- Results are reproducible across sessions with no institutional knowledge loss

---

## 2. Supported Formats

| Format | Parser | Completeness Method |
|--------|--------|-------------------|
| `.docx` | Raw ZIP/XML parsing (NOT python-docx alone) | XML text node audit + word count reconciliation |
| `.pdf` | `pdfplumber` (text + tables) or `PyMuPDF` | Page-by-page text extraction + page count verification |
| `.md` | Direct file read | Line count verification |
| `.txt` | Direct file read | Line count + byte count verification |
| `.html` | `BeautifulSoup` with all text nodes | Tag inventory + visible text extraction |
| `.xlsx` / `.csv` | `openpyxl` / `csv` module | Sheet inventory + cell count verification |
| `.pptx` | `python-pptx` + raw ZIP/XML | Slide inventory + text frame audit |
| `.rst` | Direct file read (reStructuredText) | Line count verification |
| `.xml` / `.json` | `xml.etree` / `json` module | Element/key count verification |
| `.c` / `.h` / `.py` | Direct file read (source code) | Line count + function/struct inventory |

---

## 3. The Five-Phase Pipeline

Every document study MUST follow these five phases in order. No phase may be skipped.

### Phase 1: INVENTORY

**Goal**: Understand what the document contains before extracting anything.

1. **Detect format** from file extension
2. **Inventory all content containers**:
   - `.docx`: List all ZIP parts (document.xml, headers, footers, footnotes, endnotes, comments, diagrams, charts)
   - `.pdf`: Count pages, detect tables, images with OCR text
   - `.xlsx`: List all sheets, named ranges, chart data
   - `.pptx`: List all slides, notes, master layouts
   - Other: Count lines, sections, headings
3. **Record the inventory** with counts for each container type
4. **Output**: Inventory report with expected content scope

```
INVENTORY REPORT
================
File: QuickSPI SwAS v1.0.docx
Format: docx
Parts found:
  - word/document.xml (main body)
  - word/header1.xml (header)
  - word/footer1.xml (footer)
  - word/comments.xml (207 review comments)
  - word/footnotes.xml (if present)
  - word/endnotes.xml (if present)
Tables: 6
Images: N (check for text-bearing images)
Expected word count: ~11,400
```

### Phase 2: EXTRACT

**Goal**: Extract ALL text from every container identified in Phase 1.

**Critical rule**: Use the format-specific FULL extraction method, not the convenient library default.

#### For `.docx` files (CRITICAL — most error-prone format):

```python
import zipfile
import xml.etree.ElementTree as ET

W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def extract_docx_complete(docx_path):
    """Extract ALL text from a .docx file — every XML part, every text node."""
    results = {
        'main_body': [],      # Paragraphs from document.xml
        'tables': [],          # Table cell content
        'headers': [],         # Header text
        'footers': [],         # Footer text
        'footnotes': [],       # Footnote text
        'endnotes': [],        # Endnote text
        'comments': [],        # Review comments (may contain technical decisions)
        'textboxes': [],       # Floating text boxes / shapes
        'other': [],           # Any other text-bearing parts
    }

    with zipfile.ZipFile(docx_path, 'r') as z:
        for name in z.namelist():
            if not name.endswith('.xml'):
                continue
            try:
                data = z.read(name)
                root = ET.fromstring(data)
            except:
                continue

            texts = []
            for elem in root.iter():
                if elem.tag == f'{W_NS}t' and elem.text:
                    texts.append(elem.text)

            if not texts:
                continue

            # Categorize by XML part
            if 'document.xml' in name:
                results['main_body'].extend(texts)
            elif 'header' in name.lower():
                results['headers'].extend(texts)
            elif 'footer' in name.lower():
                results['footers'].extend(texts)
            elif 'footnote' in name.lower():
                results['footnotes'].extend(texts)
            elif 'endnote' in name.lower():
                results['endnotes'].extend(texts)
            elif 'comment' in name.lower():
                results['comments'].extend(texts)
            else:
                results['other'].extend(texts)

    # ALSO extract via python-docx for structured paragraph + table output
    import docx
    doc = docx.Document(docx_path)
    structured_lines = []
    for i, p in enumerate(doc.paragraphs, 1):
        text = p.text.strip()
        if text:
            style = p.style.name if p.style else 'None'
            structured_lines.append(f'P{i:04d} [{style}]: {text}')

    for tidx, table in enumerate(doc.tables):
        structured_lines.append(f'=== TABLE {tidx+1} ===')
        for ridx, row in enumerate(table.rows):
            cells = [c.text.strip().replace('\n', ' | ') for c in row.cells]
            structured_lines.append(f'  ROW{ridx}: ' + ' || '.join(cells))

    results['structured_dump'] = structured_lines
    return results
```

#### For `.pdf` files:

```python
def extract_pdf_complete(pdf_path):
    """Extract ALL text from a PDF — every page, every table."""
    import pdfplumber  # pip install pdfplumber

    results = {'pages': [], 'tables': [], 'metadata': {}}

    with pdfplumber.open(pdf_path) as pdf:
        results['metadata'] = {
            'page_count': len(pdf.pages),
            'metadata': pdf.metadata,
        }
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            results['pages'].append({'page': i+1, 'text': text})
            tables = page.extract_tables()
            for t in tables:
                results['tables'].append({'page': i+1, 'table': t})

    return results
```

#### For `.xlsx` files:

```python
def extract_xlsx_complete(xlsx_path):
    """Extract ALL content from an Excel file — every sheet, every cell."""
    import openpyxl

    results = {'sheets': {}}
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        cells = []
        for row in ws.iter_rows():
            row_data = []
            for cell in row:
                if cell.value is not None:
                    row_data.append(str(cell.value))
            if row_data:
                cells.append(row_data)
        results['sheets'][sheet_name] = {
            'rows': len(cells),
            'data': cells,
        }

    return results
```

#### For `.pptx` files:

```python
def extract_pptx_complete(pptx_path):
    """Extract ALL text from a PowerPoint file — slides, notes, shapes."""
    import zipfile
    import xml.etree.ElementTree as ET

    A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    results = {'slides': [], 'notes': [], 'other': []}

    with zipfile.ZipFile(pptx_path, 'r') as z:
        for name in z.namelist():
            if not name.endswith('.xml'):
                continue
            try:
                data = z.read(name)
                root = ET.fromstring(data)
            except:
                continue

            texts = []
            for elem in root.iter():
                if elem.tag == f'{A_NS}t' and elem.text:
                    texts.append(elem.text)

            if texts:
                if 'slide' in name and 'note' not in name:
                    results['slides'].append({'part': name, 'texts': texts})
                elif 'note' in name:
                    results['notes'].append({'part': name, 'texts': texts})
                else:
                    results['other'].append({'part': name, 'texts': texts})

    return results
```

#### For text-based formats (`.md`, `.txt`, `.rst`, `.c`, `.h`, `.py`, `.html`):

```python
def extract_text_complete(file_path):
    """Extract all content from a text-based file."""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    return {
        'content': content,
        'line_count': len(lines),
        'word_count': len(content.split()),
        'byte_count': len(content.encode('utf-8')),
    }
```

### Phase 3: VERIFY

**Goal**: Mathematically prove that extraction is complete. Delta MUST be zero (or explained).

#### Verification checks:

1. **Word count reconciliation**: Compare raw XML/binary word count against structured dump word count
2. **Container coverage**: Every container from Phase 1 inventory MUST have extracted content (or be explicitly empty)
3. **Missed content scan**: Find text in raw extraction NOT present in structured dump
4. **Categorize any delta**:
   - `TECHNICAL` — Actionable content that affects skill files (MUST be captured)
   - `COMMENTS` — Review/editorial comments (capture if they contain technical decisions)
   - `LEGAL` — Boilerplate, copyright, confidentiality (skip)
   - `REVISION_HISTORY` — Change tracking (capture version-relevant items)
   - `TRIVIAL` — Formatting artifacts, single words, partial tokens (skip)

```
VERIFICATION REPORT
===================
Raw XML word count:  11,414
Structured dump:     11,106
Delta:               308 words

Container coverage:
  [x] main_body:    11,106 words extracted
  [x] headers:      3 words (confidentiality notice)
  [x] footers:      2 words (page number template)
  [x] comments:     207 comments, 1,892 words (review notes)
  [ ] footnotes:    0 (none present)
  [ ] endnotes:     0 (none present)

Delta breakdown:
  TECHNICAL:         34 fragments (MUST capture)
  COMMENTS:          207 fragments (review only — skip unless technical)
  LEGAL:             5 fragments (skip)
  TRIVIAL:           11 fragments (skip)

RESULT: 34 technical fragments require capture before cross-check
```

**If TECHNICAL delta > 0**: Go back to Phase 2 and extract the missed content. Do NOT proceed to Phase 4.

### Phase 4: CROSS-CHECK

**Goal**: Compare every extracted fact against target skill files.

Only begin this phase when Phase 3 verification shows TECHNICAL delta = 0.

#### Procedure:

1. **Read target skill files** completely (every line)
2. **For each technical fact in the extraction**:
   - Classify as: `CONFIRMED` (present and correct), `MISSING` (not present), `WRONG` (present but incorrect), `NEW` (novel concept not previously identified)
3. **Group findings by target file** for efficient editing
4. **Record source references** (paragraph numbers, table rows, page numbers) for traceability

```
CROSS-CHECK REPORT
==================
Document: QuickSPI SwAS v1.0
Target skill files: 7

Facts checked:     ~450
CONFIRMED:         438
MISSING:           10
WRONG:             1
NEW:               1

Findings by file:
  hidspi/SKILL.md:   5 MISSING, 1 WRONG
  dma/SKILL.md:      3 MISSING
  power/SKILL.md:    1 MISSING
  driver/SKILL.md:   1 MISSING, 1 NEW
```

### Phase 5: APPLY & VALIDATE

**Goal**: Apply all findings and prove the skill files are now complete.

1. **Apply edits** to skill files (MISSING → add, WRONG → correct)
2. **Run validation** (self-check, self-verify, eval tests if available)
3. **Regression check**: Re-run Phase 3 verification to confirm delta = 0 still holds
4. **Update extraction docs** if the original had content not in the extraction
5. **Commit and push** with descriptive message

---

## 4. Session Management

### Starting a new study session

When beginning a document study (new or re-study), always:

1. Load this skill: `/skill doc-study`
2. State the document path, format, and target skill files
3. Follow the five-phase pipeline from Phase 1

### Resuming an interrupted study

If a session was interrupted:

1. Check for existing dump files (e.g., `C:\<docname>_full_dump.txt`)
2. Check for existing verification reports
3. Resume from the last completed phase
4. Do NOT re-apply already-applied findings (check git log)

### Context management

- Use sub-agents for heavy reads (large documents)
- Extract findings into distilled knowledge before context fills
- One document per sub-agent session
- Split large documents into chapters/sections if needed

---

## 5. Quality Gates

These gates MUST pass before a document study is considered complete:

| Gate | Criterion | How to verify |
|------|-----------|---------------|
| G1: Inventory | All content containers identified | ZIP part list / page count matches |
| G2: Extraction | Structured dump created | Dump file exists with content |
| G3: Verification | Word count delta explained | TECHNICAL delta = 0 |
| G4: Cross-check | Every fact classified | Findings report with counts |
| G5: Application | All MISSING/WRONG items resolved | Self-check + self-verify PASS |
| G6: Regression | No new gaps after application | Re-run verification shows same delta |

---

## 6. Tools

The following tools are bundled with this skill:

### `doc_extract.py` — Universal document extractor

Usage:
```bash
python .opencode/skill/doc-study/tools/doc_extract.py <file_path> [--output <dump_path>]
```

Automatically detects format, runs full extraction, and produces a structured dump file.

### `doc_verify.py` — Extraction completeness verifier

Usage:
```bash
python .opencode/skill/doc-study/tools/doc_verify.py <file_path> <dump_path>
```

Runs word count reconciliation, finds missed content, categorizes delta, outputs verification report.

### `doc_crosscheck.py` — Skill file cross-checker

Usage:
```bash
python .opencode/skill/doc-study/tools/doc_crosscheck.py <dump_path> <skill_dir> [--exclude <previously_applied.json>]
```

Cross-checks every fact in the dump against skill files in the target directory. Outputs findings report.

---

## 7. Common Pitfalls (Lessons Learned)

These are real mistakes made during the THC audit that this skill prevents:

| Pitfall | What went wrong | How this skill prevents it |
|---------|----------------|--------------------------|
| **python-docx only** | Missed textboxes, comments, footnotes, header/footer text | Phase 2 uses raw ZIP/XML parsing as primary, python-docx as supplement |
| **No verification step** | Extracted content assumed complete without checking | Phase 3 REQUIRES word count reconciliation before proceeding |
| **"I found N issues" = done** | Conflated "stopped finding" with "nothing left" | Phase 3 delta must be zero or fully explained |
| **Context pressure → skimming** | Large documents cause shortcuts under context limits | Sub-agents for heavy reads, one doc per agent |
| **No regression test** | Edits could introduce new gaps | Phase 5 re-runs verification |
| **Ad-hoc extraction** | Different procedure each time, inconsistent results | This skill standardizes the procedure |
| **Format assumptions** | Only handled .docx, not other formats | Phase 2 has format-specific extractors for 10+ formats |

---

## 8. Example Workflow

```
User: Study C:\QuickSPI SwAS v1.0.docx against fv-thc skill files

Agent:
1. [Phase 1: INVENTORY]
   - Format: docx
   - ZIP parts: document.xml, header1.xml, footer1.xml, comments.xml
   - Tables: 6, Paragraphs: 1022
   
2. [Phase 2: EXTRACT]
   - Raw XML extraction: 11,414 words across all parts
   - python-docx structured dump: 819 lines → C:\quickspi_full_dump.txt
   - Comments extracted separately: 207 review comments
   
3. [Phase 3: VERIFY]
   - Word count: XML=11,414, Dump=11,106, Delta=308
   - Delta breakdown: 34 TECHNICAL, 207 COMMENTS, 5 LEGAL, 11 TRIVIAL
   - Capturing 34 technical fragments → appended to dump
   - Re-verify: TECHNICAL delta = 0 ✓
   
4. [Phase 4: CROSS-CHECK]
   - Reading 7 skill files...
   - 450 facts checked: 438 CONFIRMED, 10 MISSING, 1 WRONG, 1 NEW
   
5. [Phase 5: APPLY & VALIDATE]
   - Applied 12 edits across 4 files
   - Self-check: 64/64 PASS
   - Self-verify: 129/129 PASS
   - Regression: delta still 0 ✓
   - Committed and pushed
```

---

## 9. Extending This Skill

To add support for a new document format:

1. Add a parser function in `doc_extract.py` following the pattern of existing parsers
2. Add a verification method in `doc_verify.py` appropriate for the format
3. Update the format table in Section 2 of this SKILL.md
4. Test against a real document of that format

---


