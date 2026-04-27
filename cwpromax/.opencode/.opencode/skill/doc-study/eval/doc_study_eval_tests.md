# Document Study Skill — Eval Tests

> **Owner**: Chin, William Willy (`willychi`)
>
> Evaluation tests for the `doc-study` skill. Tests cover all 5 phases of the
> verification-first pipeline, all 3 tools, format handling, and quality gates.
> Total: 45 tests.
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

---

## Phase 1: Inventory (INV)

### INV-001: Format Detection — DOCX

**Prompt**: Given a `.docx` file, what format does the doc-study pipeline identify it as?

**Expected**: The pipeline identifies `.docx` as format "docx" and selects the `python-docx` + raw ZIP/XML extraction path.

**Pass Criteria**: Format detected as "docx"; extraction plan includes both python-docx structured pass AND raw ZIP/XML completeness pass.

### INV-002: Format Detection — PDF

**Prompt**: Given a `.pdf` file, what format does the doc-study pipeline identify it as?

**Expected**: The pipeline identifies `.pdf` as format "pdf" and selects `pdfplumber` (primary) or `PyMuPDF/fitz` (fallback).

**Pass Criteria**: Format detected as "pdf"; extraction plan notes optional dependency availability.

### INV-003: Format Detection — Source Code

**Prompt**: Given a `.c` file, what format does the doc-study pipeline identify it as?

**Expected**: The pipeline identifies `.c` as format "source" and uses plain text line-by-line extraction.

**Pass Criteria**: Format detected as "source"; no binary parsing attempted.

### INV-004: Format Detection — Unknown Extension

**Prompt**: Given a file with extension `.xyz`, how does the pipeline handle it?

**Expected**: Falls back to plain text extraction with a warning about unknown format.

**Pass Criteria**: No crash; warning emitted; text extraction attempted.

### INV-005: Multi-Document Inventory

**Prompt**: Given a directory containing `.docx`, `.pdf`, `.md`, and `.c` files, list all documents with their detected formats.

**Expected**: Each file listed with correct format classification and extraction method.

**Pass Criteria**: All files detected; no files missed; correct format for each.

---

## Phase 2: Extract (EXT)

### EXT-001: DOCX Structured Extraction

**Prompt**: Run `doc_extract.py` on a `.docx` file. Does it produce structured output with paragraphs and tables?

**Expected**: Output contains numbered paragraphs (`[P001]`, `[P002]`, ...) and tables (`[TABLE]`), with heading hierarchy preserved.

**Pass Criteria**: All paragraphs and tables present; heading levels correct; no empty sections.

### EXT-002: DOCX Raw XML Extraction

**Prompt**: Run `doc_extract.py` on a `.docx` file with full XML parsing. Does it capture textboxes, headers, footers, and comments?

**Expected**: Raw XML pass captures content from `word/document.xml`, `word/header*.xml`, `word/footer*.xml`, `word/comments.xml`, and any embedded textbox elements.

**Pass Criteria**: Content from all XML parts extracted; no container type missed.

### EXT-003: DOCX Word Count Reconciliation

**Prompt**: After extracting a `.docx` file, does the tool report word count from both structured and raw passes?

**Expected**: Both `structured_word_count` and `raw_word_count` are reported, along with the delta.

**Pass Criteria**: Both counts present; delta calculated; delta < 5% for typical documents.

### EXT-004: Markdown Extraction

**Prompt**: Run `doc_extract.py` on a `.md` file. Does it preserve headings, code blocks, tables, and lists?

**Expected**: Markdown structure preserved verbatim. Headings detected by `#` prefix. Code blocks preserved with language tags.

**Pass Criteria**: Output matches input content; no markdown syntax consumed or lost.

### EXT-005: CSV Extraction

**Prompt**: Run `doc_extract.py` on a `.csv` file. Does it extract all rows and columns?

**Expected**: Each row extracted as a record. Column headers identified from first row.

**Pass Criteria**: Row count matches source; all columns present; delimiter correctly detected.

### EXT-006: JSON Extraction

**Prompt**: Run `doc_extract.py` on a `.json` file. Does it extract all keys and values?

**Expected**: JSON structure flattened into key-value pairs with dot-notation paths.

**Pass Criteria**: All leaf values extracted; nested structures correctly traversed.

### EXT-007: HTML Extraction

**Prompt**: Run `doc_extract.py` on an `.html` file. Does it extract text content and preserve structure?

**Expected**: HTML tags stripped; text content preserved; headings and tables detected from HTML elements.

**Pass Criteria**: No HTML tags in output; meaningful text content preserved; table data extracted.

### EXT-008: XLSX Extraction

**Prompt**: Run `doc_extract.py` on an `.xlsx` file with multiple sheets. Does it extract all sheets?

**Expected**: Each sheet extracted separately with sheet name as header. All cells including formulas (as values) extracted.

**Pass Criteria**: All sheets present; row/column counts match source; merged cells handled.

### EXT-009: Output File Generation

**Prompt**: Run `doc_extract.py` with `--output` flag. Is the output written to the specified file?

**Expected**: Output written to the specified path. File contains full extraction results.

**Pass Criteria**: File created at specified path; content matches stdout output.

### EXT-010: Empty Document Handling

**Prompt**: Run `doc_extract.py` on an empty `.docx` file (no paragraphs, no tables).

**Expected**: Tool completes without error. Reports 0 paragraphs, 0 tables, 0 word count.

**Pass Criteria**: No crash; zero counts reported; clean exit.

---

## Phase 3: Verify (VER)

### VER-001: Word Count Delta Calculation

**Prompt**: Run `doc_verify.py` on a `.docx` original and its extraction dump. Does it calculate the word count delta?

**Expected**: Reports original word count (from raw XML), dump word count, absolute delta, and percentage delta.

**Pass Criteria**: All four values present; delta percentage calculated correctly.

### VER-002: Missed Content Detection — Textboxes

**Prompt**: Given a `.docx` with content in textboxes, and a dump that missed them, does `doc_verify.py` detect the missed content?

**Expected**: Missed textbox content reported with category "TECHNICAL" or appropriate category.

**Pass Criteria**: Missed fragments listed; source container identified as textbox.

### VER-003: Missed Content Detection — Comments

**Prompt**: Given a `.docx` with review comments, does `doc_verify.py` detect if comments were missed?

**Expected**: Missed comments reported with category "COMMENTS".

**Pass Criteria**: Comment text listed as missed; categorized correctly.

### VER-004: Missed Content Categorization

**Prompt**: Does `doc_verify.py` categorize missed content into TECHNICAL, COMMENTS, LEGAL, REVISION, and TRIVIAL?

**Expected**: Each missed fragment assigned exactly one category based on content analysis.

**Pass Criteria**: All fragments categorized; no "UNKNOWN" category; technical terms correctly identified.

### VER-005: Pass/Fail Threshold

**Prompt**: What is the pass/fail threshold for verification? Does a delta > 5% cause a FAIL?

**Expected**: Quality gate G2 requires delta < 5% for PASS. Documents with delta >= 5% are flagged FAIL with recommendation to use raw XML extraction.

**Pass Criteria**: PASS for delta < 5%; FAIL for delta >= 5%; clear recommendation in FAIL case.

### VER-006: Container Coverage Report

**Prompt**: Does `doc_verify.py` report which XML containers were found and which were empty/missing?

**Expected**: Lists all standard containers (document.xml, header*.xml, footer*.xml, comments.xml, footnotes.xml, endnotes.xml) with word counts per container.

**Pass Criteria**: All containers listed; zero-word containers flagged; coverage percentage reported.

### VER-007: Verification of Non-DOCX Format

**Prompt**: Run `doc_verify.py` on a `.md` file and its dump. How does it handle non-DOCX formats?

**Expected**: Falls back to simple word count comparison (no XML container analysis). Still reports delta.

**Pass Criteria**: No crash on non-DOCX; word count delta reported; container analysis skipped gracefully.

### VER-008: Report Generation

**Prompt**: Run `doc_verify.py` with `--report` flag. Does it generate a structured report file?

**Expected**: Report file written with sections: Summary, Word Counts, Container Coverage, Missed Content (categorized), Pass/Fail verdict.

**Pass Criteria**: Report file created; all sections present; machine-parseable format.

---

## Phase 4: Cross-Check (XCK)

### XCK-001: CONFIRMED Classification

**Prompt**: Run `doc_crosscheck.py` on a dump and skill directory. Does it correctly identify facts present in both?

**Expected**: Facts found in both the dump and skill files are classified as CONFIRMED with file:line references.

**Pass Criteria**: CONFIRMED items have matching source (dump) and target (skill file) references.

### XCK-002: MISSING Classification

**Prompt**: Does `doc_crosscheck.py` identify facts in the dump that are NOT in any skill file?

**Expected**: Facts present in dump but absent from all skill files are classified as MISSING.

**Pass Criteria**: MISSING items list the dump location and the fact text; no false positives from trivial text.

### XCK-003: WRONG Classification

**Prompt**: Does `doc_crosscheck.py` detect contradictions between dump and skill files?

**Expected**: If a skill file states a value that contradicts the dump (e.g., wrong register offset, wrong bit field), it is classified as WRONG.

**Pass Criteria**: WRONG items show both the dump value and the skill file value; contradiction clearly stated.

### XCK-004: NEW Classification

**Prompt**: Does `doc_crosscheck.py` identify facts in skill files that are NOT in the dump?

**Expected**: Facts in skill files with no corresponding dump source are classified as NEW (added from other sources).

**Pass Criteria**: NEW items reference the skill file location; noted as potentially from other reference documents.

### XCK-005: Key Term Extraction

**Prompt**: Does `doc_crosscheck.py` extract meaningful technical terms from the dump for matching?

**Expected**: Extracts hex values, register names, bit fields, constants, function names, error codes, and other domain-specific terms.

**Pass Criteria**: Technical terms extracted; trivial words (a, the, is) excluded; minimum length threshold applied.

### XCK-006: Exclude Directories

**Prompt**: Run `doc_crosscheck.py` with `--exclude docs eval tools`. Are those directories excluded from cross-check?

**Expected**: Only SKILL.md files in non-excluded subdirectories are checked.

**Pass Criteria**: Excluded directories not scanned; no findings from excluded paths.

### XCK-007: Cross-Check Report

**Prompt**: Run `doc_crosscheck.py` with `--report` flag. Does it generate a structured findings report?

**Expected**: Report contains sections per category (CONFIRMED/MISSING/WRONG/NEW) with counts and details.

**Pass Criteria**: Report file created; all categories present; summary counts match detail counts.

### XCK-008: Multi-Skill Cross-Check

**Prompt**: Cross-check a dump against a skill directory with 5+ sub-skill files. Are findings attributed to specific files?

**Expected**: Each finding references the specific skill file and line number where the match/mismatch occurs.

**Pass Criteria**: File paths are specific (not just directory); line numbers present for each finding.

---

## Phase 5: Apply & Validate (APL)

### APL-001: Finding Application Workflow

**Prompt**: After cross-check identifies MISSING items, what is the correct apply workflow?

**Expected**: For each MISSING item: (1) verify against additional sources, (2) determine target skill file, (3) add to correct section, (4) re-run cross-check to confirm MISSING→CONFIRMED.

**Pass Criteria**: Workflow steps include verification, targeted placement, and re-validation.

### APL-002: WRONG Item Correction

**Prompt**: After cross-check identifies a WRONG item, what is the correction procedure?

**Expected**: (1) Verify which source is authoritative (reference hierarchy), (2) correct the skill file value, (3) add source attribution, (4) re-run cross-check.

**Pass Criteria**: Reference hierarchy consulted; correction applied; old value noted in commit message.

### APL-003: Re-Validation After Apply

**Prompt**: After applying findings, does re-running the pipeline show zero remaining MISSING/WRONG items?

**Expected**: Delta between dump and skill files should be zero for all applied items. New cross-check shows all previously MISSING items as CONFIRMED.

**Pass Criteria**: MISSING count decreased by number of applied items; no new WRONG items introduced.

---

## Quality Gates (QGT)

### QGT-001: Gate G1 — Inventory Complete

**Prompt**: What must be true before proceeding from Phase 1 to Phase 2?

**Expected**: All documents inventoried with format and extraction method identified. No unknown formats without fallback plan.

**Pass Criteria**: Inventory list complete; all formats have extraction path.

### QGT-002: Gate G2 — Extraction Verified

**Prompt**: What must be true before proceeding from Phase 3 to Phase 4?

**Expected**: Word count delta < 5%. All XML containers checked. Technical missed content = 0 (or documented exceptions).

**Pass Criteria**: Delta threshold met; container coverage 100%; technical gaps resolved.

### QGT-003: Gate G6 — Final Validation

**Prompt**: What constitutes a fully validated document study?

**Expected**: All 5 phases complete. Zero MISSING/WRONG items (or documented exceptions with justification). Self-check and self-verify pass.

**Pass Criteria**: Pipeline complete; findings at zero; validation tools pass.

---

## Tool Robustness (ROB)

### ROB-001: Missing Optional Dependency

**Prompt**: Run `doc_extract.py` on a `.pdf` when neither `pdfplumber` nor `fitz` is installed.

**Expected**: Clear error message stating which packages are needed. No traceback or crash.

**Pass Criteria**: ImportError caught; helpful message printed; non-zero exit code.

### ROB-002: Corrupted File Handling

**Prompt**: Run `doc_extract.py` on a corrupted `.docx` file (invalid ZIP).

**Expected**: Error caught gracefully. Reports file is unreadable with the specific error.

**Pass Criteria**: No traceback; error message includes file path and error type.

### ROB-003: Large File Handling

**Prompt**: Run `doc_extract.py` on a `.docx` with 500+ pages. Does it complete without memory issues?

**Expected**: Extraction completes, potentially with longer runtime. Progress indication for large files.

**Pass Criteria**: Completes without OOM; all content extracted; runtime proportional to file size.

### ROB-004: Unicode Content

**Prompt**: Run `doc_extract.py` on a document containing CJK characters, RTL text, and mathematical symbols.

**Expected**: All Unicode content preserved correctly in output. No encoding errors.

**Pass Criteria**: Unicode characters intact; no replacement characters (U+FFFD); correct byte counts.

### ROB-005: CLI Argument Validation

**Prompt**: Run `doc_extract.py` with no arguments, or with a non-existent file path.

**Expected**: Usage message printed for no arguments. Clear error for non-existent file.

**Pass Criteria**: Helpful usage/error messages; non-zero exit code; no traceback.
