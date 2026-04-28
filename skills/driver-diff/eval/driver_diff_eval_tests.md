# Driver Diff Methodology — Eval Tests

> **Owner**: Chin, William Willy (`willychi`)
>
> Evaluation tests for the `driver-diff` skill — cross-comparison of Windows vs Linux driver implementations.
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

## Methodology (DD-MTH)

### DD-MTH-001: Diff Scope Definition
**Prompt**: "How do I define the scope of a driver diff?"
**Expected**: Agent explains: identify the IP/subsystem, locate both driver source trees, define comparison axes (register access, power management, error handling, feature flags, workarounds).
**Pass Criteria**: Scope definition process described; comparison axes listed.

### DD-MTH-002: Source Tree Mapping
**Prompt**: "How do I map files between Windows and Linux driver trees for the same IP?"
**Expected**: Agent explains functional mapping (not 1:1 file mapping): identify equivalent functions by purpose (init, probe, suspend, resume, interrupt handler, register access). Provides example mapping table.
**Pass Criteria**: Functional mapping approach described; example table provided.

### DD-MTH-003: Comparison Axes
**Prompt**: "What are the key axes to compare between Windows and Linux drivers?"
**Expected**: Agent lists: (1) Register access patterns, (2) Power state transitions, (3) Error handling/recovery, (4) Workarounds/quirks, (5) Feature flags/capabilities, (6) Timing/delays, (7) ACPI/firmware interaction, (8) Device ID tables.
**Pass Criteria**: At least 6 comparison axes listed with descriptions.

## Analysis (DD-ANL)

### DD-ANL-001: Register Access Diff
**Prompt**: "Compare register access patterns between Windows and Linux drivers."
**Expected**: Agent identifies: which registers are accessed by both, which are unique to one OS, any different access sequences for the same register, and any different bit field interpretations.
**Pass Criteria**: Four categories of register differences identified.

### DD-ANL-002: Workaround Detection
**Prompt**: "How do I identify OS-specific workarounds?"
**Expected**: Agent explains: search for conditional code guarded by device IDs, platform checks, or version checks. Look for comments containing "workaround", "quirk", "errata", "WA", "HACK". Cross-reference with HSDES sightings.
**Pass Criteria**: Search patterns listed; HSDES cross-reference mentioned.

### DD-ANL-003: Timing Difference Detection
**Prompt**: "How do I find timing differences between drivers?"
**Expected**: Agent explains: search for sleep/delay calls (msleep, udelay, usleep_range on Linux; KeStallExecutionProcessor, KeDelayExecutionThread on Windows), compare durations for equivalent operations.
**Pass Criteria**: OS-specific delay function names listed; comparison methodology described.

### DD-ANL-004: Feature Parity Check
**Prompt**: "How do I determine if a feature exists in one driver but not the other?"
**Expected**: Agent explains: enumerate features from spec/HAS, check implementation in both trees, categorize as: both, Linux-only, Windows-only, neither.
**Pass Criteria**: Feature enumeration from spec; 4-way categorization.

## Reporting (DD-RPT)

### DD-RPT-001: Diff Report Format
**Prompt**: "What does a driver diff report look like?"
**Expected**: Report includes: header (IP name, driver versions, date), summary table (categories × match/differ/missing), detailed findings per category, recommendations, and HSDES references.
**Pass Criteria**: Report format described; all sections listed.

### DD-RPT-002: Discrepancy Classification
**Prompt**: "How are discrepancies classified?"
**Expected**: Agent classifies as: (1) INTENTIONAL — different OS requires different approach, (2) BUG — one driver has a defect, (3) MISSING — feature not implemented in one OS, (4) DIVERGED — same intent but different implementation that may cause behavioral differences.
**Pass Criteria**: 4 categories described with examples.

### DD-RPT-003: Actionable ECOs
**Prompt**: "How are Engineering Change Orders generated from a driver diff?"
**Expected**: Agent explains that each discrepancy rated as BUG or MISSING generates an ECO with: ID, severity, affected driver, description, evidence (code snippets from both), and recommended fix.
**Pass Criteria**: ECO format described; BUG/MISSING trigger conditions clear.

## Platform Specifics (DD-PLAT)

### DD-PLAT-001: Device ID Table Diff
**Prompt**: "Compare device ID tables between Windows and Linux drivers."
**Expected**: Agent extracts DID tables from both sources, aligns by platform/stepping, and reports: matched DIDs, Linux-only DIDs, Windows-only DIDs.
**Pass Criteria**: Three categories reported; DIDs in hex format.

### DD-PLAT-002: ACPI Method Diff
**Prompt**: "Compare ACPI method usage between drivers."
**Expected**: Agent identifies ACPI methods used by each driver (_DSM, _RST, _S0W, _CRS, etc.), compares GUIDs, function indices, and parameter handling.
**Pass Criteria**: ACPI methods listed per driver; differences highlighted.

### DD-PLAT-003: Power Management Diff
**Prompt**: "Compare power management implementations."
**Expected**: Agent compares: D-state transitions, runtime PM, S0ix support, wake configuration, LTR values, and D3 entry/exit sequences.
**Pass Criteria**: At least 4 PM aspects compared; behavioral differences noted.

## Integration (DD-INT)

### DD-INT-001: Skill File Updates
**Prompt**: "How do driver diff findings feed back into skill files?"
**Expected**: Agent explains that discrepancies classified as BUG or DIVERGED should be documented in the relevant skill files (e.g., driver/SKILL.md, platform/SKILL.md). MISSING features get added to test gap analysis.
**Pass Criteria**: Feedback path described; target skill files identified per finding type.

### DD-INT-002: HSDES Cross-Reference
**Prompt**: "How do I cross-reference driver diff findings with HSDES sightings?"
**Expected**: Agent explains: search HSDES for the register/feature keyword, check if a sighting already exists, link existing sightings to the finding, or recommend filing a new sighting if none exists.
**Pass Criteria**: Search methodology described; link-or-file decision process clear.
