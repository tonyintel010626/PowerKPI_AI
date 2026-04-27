---
name: skill-audit
description: Multi-document cross-check audit orchestrator for skill trees — manages reference hierarchies, runs doc-study per document, merges findings, and tracks delta-to-zero
disable: false
license: MIT
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# Skill Audit Orchestrator

## Purpose

This skill codifies the exhaustive cross-check audit methodology developed during the Intel THC (Touch Host Controller) skill tree audit. It orchestrates **multi-document, multi-pass audits** against a skill tree, ensuring every fact in every reference document is verified against the skill files — and every fact in the skill files traces back to a reference document.

The key insight: studying one document at a time (via `doc-study`) is necessary but insufficient. A complete audit requires:
1. **Reference hierarchy** — prioritized ordering of authoritative sources
2. **Multi-document orchestration** — running doc-study per document, accumulating findings
3. **Cross-document conflict resolution** — when Document A and Document B disagree
4. **Delta tracking** — measuring progress toward zero unresolved findings
5. **Regression prevention** — ensuring fixes don't introduce new errors

## When to Use This Skill

- Auditing a skill tree against multiple reference documents (specs, source code, design docs)
- Onboarding a new reference document into an existing audit
- Running regression checks after skill file edits
- Measuring audit completeness and coverage

## Reference Hierarchy Pattern

Every audit MUST define a reference hierarchy. Higher-priority sources override lower ones when conflicts arise, unless contradicted by actual behavior (e.g., hardware measurements, test results).

```
| Priority | Source Type              | Examples                           |
|----------|--------------------------|------------------------------------|
| 1 (Gold) | Hardware spec / HAS      | IP HAS, RTL documentation          |
| 1 (Gold) | Software Architecture    | SwAS, Design Spec                  |
| 2        | Implementation source    | Linux kernel, Windows driver       |
| 3        | Configuration guides     | BWG, BIOS guides                   |
| 4        | Test results / field data | NGA results, sighting reports      |
| 5        | Secondary documentation  | Wiki pages, presentations          |
```

**Conflict resolution rules:**
- Priority 1 vs Priority 1: Flag for human review. Do NOT auto-resolve.
- Priority 1 vs Priority 2+: Priority 1 wins unless implementation reveals undocumented behavior.
- Same priority: Cross-check against a third source. If no third source, flag for human review.
- Any source vs actual HW behavior: Actual behavior wins; document the discrepancy.

## The Audit Pipeline

### Phase 0: PLAN

Before any document is studied, define the audit scope.

**Inputs:**
- Skill tree path (e.g., `.opencode/skill/fv-thc/`)
- Reference document list with priorities
- Agent definition path (e.g., `.opencode/agent/FV/FV-THC.md`)

**Outputs:**
- `audit_plan.json` — structured plan with document order, expected coverage areas, schedule

**Steps:**
1. Inventory all skill files in the tree (count, line counts, key topics)
2. Inventory all reference documents (format, size, topic coverage)
3. Map documents to skill files (which doc covers which skill?)
4. Define audit order: highest-priority documents first, broadest-coverage documents first within same priority
5. Estimate effort per document (word count × complexity factor)
6. Write the plan

**Quality Gate G0:** Plan exists, all documents listed, all skill files mapped.

### Phase 1: STUDY (per document)

For each reference document, run the `doc-study` pipeline (5 phases: Inventory → Extract → Verify → Cross-check → Apply).

**Critical rules:**
- Study ONE document at a time to avoid context overflow
- Use sub-agents for heavy document reads
- Complete the full doc-study pipeline before moving to the next document
- Save findings to a persistent file after each document

**Per-document workflow:**
```
1. Load doc-study skill
2. Phase 1-2: Extract document content (format-specific)
3. Phase 3: Verify extraction completeness (word count reconciliation)
4. Phase 4: Cross-check against skill files
5. Categorize findings: CONFIRMED / MISSING / WRONG / NEW
6. Save findings to audit_findings_<doc_name>.json
7. Apply approved changes to skill files
8. Run regression (self-check + self-verify)
```

**Quality Gate G1 (per document):** Extraction verified (delta < 2%), all findings categorized, no WRONG items remaining.

### Phase 2: MERGE

After all documents are studied, merge findings across documents.

**Steps:**
1. Load all per-document finding files
2. Deduplicate: same fact confirmed by multiple documents → single CONFIRMED with multiple sources
3. Identify conflicts: Document A says X, Document B says Y → flag with both sources and priorities
4. Resolve conflicts using the reference hierarchy
5. Identify coverage gaps: skill file content not covered by ANY document
6. Generate merged findings report

**Conflict resolution process:**
```python
def resolve_conflict(finding_a, finding_b, hierarchy):
    """Resolve conflicting findings from two documents."""
    prio_a = hierarchy[finding_a.source_doc]
    prio_b = hierarchy[finding_b.source_doc]
    
    if prio_a < prio_b:  # Lower number = higher priority
        return finding_a, "higher_priority_source"
    elif prio_b < prio_a:
        return finding_b, "higher_priority_source"
    else:
        # Same priority — flag for human review
        return None, "human_review_required"
```

**Quality Gate G2:** All conflicts resolved or flagged, no orphan findings, merged report generated.

### Phase 3: COVERAGE ANALYSIS

Measure audit completeness from both directions:

**Forward coverage** (documents → skills): What percentage of document content is reflected in skill files?
- For each document, count CONFIRMED vs total facts
- Target: 100% of technical facts confirmed

**Reverse coverage** (skills → documents): What percentage of skill file content traces to a reference document?
- For each skill file, extract key technical terms/values
- Check if each term appears in at least one document extraction
- Uncovered terms = potential errors or undocumented tribal knowledge

**Coverage matrix:**
```
| Skill File    | Doc A | Doc B | Doc C | Uncovered |
|---------------|-------|-------|-------|-----------|
| registers     | 85%   | 10%   | 0%    | 5%        |
| hidspi        | 20%   | 75%   | 5%    | 0%        |
| ...           | ...   | ...   | ...   | ...       |
```

**Quality Gate G3:** Forward coverage ≥ 98% for all Priority 1 docs. Reverse coverage ≥ 95% for all skill files.

### Phase 4: REGRESSION & SIGN-OFF

Final validation pass.

**Steps:**
1. Run self-check (structural validation) — must be 100% PASS
2. Run self-verify (content assertions) — must meet threshold (default 95%)
3. Run cross-check tool against ALL documents one more time — delta must be 0
4. Generate final audit report with:
   - Total documents studied
   - Total findings (by category)
   - Coverage matrix
   - Unresolved items (with justification)
   - Sign-off checklist

**Quality Gate G4:** Self-check PASS, self-verify ≥ threshold, cross-check delta = 0.

## Audit State Management

### State File: `audit_state.json`

Persists audit progress across sessions:
```json
{
  "audit_id": "thc-audit-2026-03",
  "skill_tree": ".opencode/skill/fv-thc",
  "status": "in_progress",
  "phase": "STUDY",
  "documents": [
    {
      "name": "THC IP HAS 4.x",
      "path": "C:\\THC_HAS_4x.docx",
      "priority": 1,
      "status": "completed",
      "findings_file": "audit_findings_thc_has.json",
      "stats": {"confirmed": 112, "missing": 3, "wrong": 1, "new": 5}
    },
    {
      "name": "QuickSPI SwAS v1.0",
      "path": "C:\\QuickSPI SwAS v1.0.docx",
      "priority": 1,
      "status": "completed",
      "findings_file": "audit_findings_quickspi.json",
      "stats": {"confirmed": 741, "missing": 0, "wrong": 0, "new": 0}
    }
  ],
  "merged_findings_file": null,
  "coverage_matrix_file": null,
  "last_updated": "2026-03-07T10:00:00Z"
}
```

### Resuming an Interrupted Audit

1. Load `audit_state.json`
2. Identify the current phase and last completed document
3. Resume from the next incomplete document or phase
4. Do NOT re-study already-completed documents unless explicitly requested

## Session Management

### Context Overflow Prevention

- **One document per sub-agent session** — never study two documents in the same context
- **Extract/discard aggressively** — after applying findings from a document, extract key stats and discard raw content
- **Start fresh sessions** after 2-3 major documents to prevent "session too large" errors
- **Save state to disk** after every significant step — never rely solely on in-memory context

### Multi-Pass Strategy

Some audits require multiple passes:
- **Pass 1**: Study all documents, apply obvious fixes
- **Pass 2**: Re-study documents where extraction was incomplete (< 97% coverage)
- **Pass 3**: Targeted re-study of specific sections where conflicts were found
- **Final pass**: Full regression cross-check

Each pass should reduce the delta. If a pass finds 0 new issues, the audit is converged.

## Common Pitfalls

| # | Pitfall | Prevention |
|---|---------|------------|
| 1 | Studying documents out of priority order | Always start with Priority 1 (gold) sources |
| 2 | Not verifying extraction completeness before cross-checking | Use doc-study Phase 3 (VERIFY) — never skip |
| 3 | Auto-resolving Priority 1 vs Priority 1 conflicts | Always flag for human review |
| 4 | Forgetting reverse coverage (skills → docs) | Run Phase 3 coverage analysis both directions |
| 5 | Context overflow from studying multiple docs in one session | One doc per sub-agent, save state to disk |
| 6 | Not running regression after applying changes | Always run self-check + self-verify after edits |
| 7 | Treating implementation source as ground truth over spec | Spec (Priority 1) wins unless HW proves otherwise |
| 8 | Skipping multi-pass convergence | Keep running passes until delta = 0 |

## Integration with Other Skills

### Required Skills
- **`doc-study`** — Used for per-document extraction, verification, and cross-checking
- **`self-improve`** (optional) — Used for structural checks and content assertions during regression

### Dependency Flow
```
skill-audit (orchestrator)
  ├── doc-study (per-document pipeline)
  │     ├── doc_extract.py
  │     ├── doc_verify.py
  │     └── doc_crosscheck.py
  └── self-improve (regression validation)
        ├── self_check.py
        ├── self_verify.py
        └── self_improve.py
```

## Example: THC Skill Tree Audit

This is the actual audit that produced this skill:

```
Audit: Intel THC Touch Host Controller
Skill tree: .opencode/skill/fv-thc/ (9 sub-skills, ~7500 lines)
Documents studied (in order):
  1. THC IP HAS 4.x          [Priority 1] — 112 facts, all confirmed
  2. QuickSPI SwAS v1.0       [Priority 1] — 741 facts, all confirmed
  3. QuickI2C SwAS v1.0       [Priority 1] — 699 facts, all confirmed
  4. Linux kernel source       [Priority 2] — driver paths, DID tables
  5. Windows driver source     [Priority 2] — 28 ECOs, 9 discrepancies
  6. THC BWG                   [Priority 3] — BIOS configuration
  7. HIDSPI/HIDI2C specs       [Priority 3] — protocol compliance

Total passes: 4 (initial + 3 convergence passes)
Final state: 1552/1552 facts confirmed, 0 delta
Self-check: 64/64 PASS
Self-verify: 129/129 PASS
```

## Extending This Skill

To adapt this skill for a different domain:
1. Define your reference hierarchy (which documents are Priority 1?)
2. Create an `audit_plan.json` with your document list and skill tree path
3. Ensure `doc-study` skill is available for document extraction
4. Optionally set up `self-improve` for automated regression checks
5. Follow the 5-phase pipeline: PLAN → STUDY → MERGE → COVERAGE → REGRESSION



### Audit Progress Tracking
Session memory complements `audit_state.json` — use memory for human-readable decisions and context, use `audit_state.json` for machine-readable structured state.
