# Skill Audit Orchestrator — Eval Tests

> **Owner**: Chin, William Willy (`willychi`)
>
> Evaluation tests for the `skill-audit` skill — multi-document cross-check orchestration against skill trees.
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

## Audit Configuration (AUD-CFG)

### AUD-CFG-001: Config Validation
**Prompt**: "Validate an audit config JSON that has all required fields."
**Expected**: Agent confirms config has `audit_name`, `skill_dir`, `reference_documents`, `reference_hierarchy`, and `output_dir`.
**Pass Criteria**: All required fields listed; missing fields flagged as errors.

### AUD-CFG-002: Priority Hierarchy
**Prompt**: "Explain how reference document priority works in a skill audit."
**Expected**: Agent explains that higher-priority documents are authoritative when conflicts arise; findings from lower-priority docs are marked as `NEEDS_REVIEW` if they contradict higher-priority findings.
**Pass Criteria**: Priority conflict resolution logic described correctly.

### AUD-CFG-003: Config Template Generation
**Prompt**: "Generate a starter audit config for a skill tree at `.opencode/skill/my-domain`."
**Expected**: Agent produces valid JSON with all required fields, reasonable defaults, and placeholder entries for reference documents.
**Pass Criteria**: Valid JSON; all required fields present; comments/descriptions explain each field.

## Document Processing (AUD-DOC)

### AUD-DOC-001: Single Document Audit
**Prompt**: "Run a skill audit with one .docx reference document."
**Expected**: Agent follows the 5-phase pipeline: inventory → extract → verify → cross-check → report.
**Pass Criteria**: All 5 phases execute in order; extraction completeness verified before cross-check begins.

### AUD-DOC-002: Multi-Document Orchestration
**Prompt**: "Run a skill audit with 3 reference documents at different priorities."
**Expected**: Agent processes documents one at a time (not all at once), in priority order (highest first). Findings are merged with conflict resolution.
**Pass Criteria**: Documents processed sequentially by priority; conflicts resolved by priority ranking.

### AUD-DOC-003: Format Detection
**Prompt**: "Audit a skill tree against a .pdf, a .docx, and a .md reference."
**Expected**: Agent detects each format and applies the correct extractor (doc_extract.py or direct read for .md).
**Pass Criteria**: Each format handled appropriately; no format-related errors.

### AUD-DOC-004: Extraction Verification Gate
**Prompt**: "What happens if extraction completeness falls below 95%?"
**Expected**: Agent explains that the verification quality gate (G3) fails, audit pauses, and the user must investigate missed content before cross-checking proceeds.
**Pass Criteria**: Gate failure behavior described; no skip-ahead allowed.

## Cross-Check Merging (AUD-MRG)

### AUD-MRG-001: Finding Deduplication
**Prompt**: "How are duplicate findings from multiple documents handled?"
**Expected**: Agent explains that findings are deduplicated by (skill_file, fact_pattern) key. If the same fact is confirmed by multiple documents, it counts once with multiple source attributions.
**Pass Criteria**: Dedup logic described; multi-source attribution mentioned.

### AUD-MRG-002: Conflict Resolution
**Prompt**: "Document A (priority 1) says register X is 0x100. Document B (priority 2) says register X is 0x200. How is this resolved?"
**Expected**: Agent says Document A wins (higher priority). Document B's conflicting claim is flagged as `CONFLICT` with a note for human review.
**Pass Criteria**: Higher priority wins; conflict flagged for review; not silently discarded.

### AUD-MRG-003: Coverage Matrix
**Prompt**: "Generate a coverage matrix showing which skill files are covered by which reference documents."
**Expected**: Agent produces a matrix (skill file × document) showing CONFIRMED/MISSING/PARTIAL coverage status.
**Pass Criteria**: Matrix format correct; all skill files and all documents represented.

## Reporting (AUD-RPT)

### AUD-RPT-001: Summary Report
**Prompt**: "Show me the audit summary after processing all documents."
**Expected**: Report includes: total facts checked, confirmed count, missing count, wrong count, new count, per-document breakdown, per-skill breakdown, and overall health score.
**Pass Criteria**: All metric categories present; numbers consistent (sum of per-doc = total).

### AUD-RPT-002: Delta-to-Zero Tracking
**Prompt**: "How do I know when my skill files are fully aligned with all reference documents?"
**Expected**: Agent explains that delta-to-zero means MISSING=0 and WRONG=0 across all documents. The audit tool tracks this and reports the delta.
**Pass Criteria**: Delta-to-zero concept correctly explained; tracking mechanism described.

### AUD-RPT-003: Actionable Findings Export
**Prompt**: "Export findings as a JSON file for programmatic processing."
**Expected**: Agent produces JSON with structured findings: id, category, skill_file, source_document, priority, status, description, evidence.
**Pass Criteria**: Valid JSON; all required fields present per finding; parseable by downstream tools.

## Integration (AUD-INT)

### AUD-INT-001: Doc-Study Skill Integration
**Prompt**: "How does skill-audit use the doc-study skill?"
**Expected**: Agent explains that skill-audit delegates extraction and verification to doc-study tools (doc_extract.py, doc_verify.py, doc_crosscheck.py), then adds orchestration: multi-doc sequencing, finding merging, conflict resolution, and coverage tracking.
**Pass Criteria**: Clear delegation described; orchestration value-add explained.

### AUD-INT-002: Self-Improve Integration
**Prompt**: "How does skill-audit feed into self-improve?"
**Expected**: Agent explains that audit findings (MISSING/WRONG) can be converted into self-improve proposals for automated remediation, closing the feedback loop.
**Pass Criteria**: Finding-to-proposal conversion described; feedback loop concept mentioned.

### AUD-INT-003: Incremental Re-Audit
**Prompt**: "A reference document was updated. How do I re-audit just that document?"
**Expected**: Agent explains that the audit config supports per-document last-audited timestamps. Re-running with `--doc <name>` processes only that document and merges results with the existing audit state.
**Pass Criteria**: Incremental audit mechanism described; state preservation mentioned.
