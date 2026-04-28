# Self-Improvement Framework — Eval Tests

> **Owner**: Chin, William Willy (`willychi`)
>
> Evaluation tests for the `self-improve` skill — generic self-check/verify/improve framework for any skill tree.
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

## Configuration (SI-CFG)

### SI-CFG-001: Config Template Generation
**Prompt**: "Generate a self-improvement config for a skill tree at `.opencode/skill/my-domain` with 4 sub-skills."
**Expected**: Agent produces valid JSON with `paths`, `skills` array, `owner`, `self_check`, `self_verify`, and `self_improve` sections.
**Pass Criteria**: Valid JSON; all sections present; skill count matches (4).

### SI-CFG-002: Config Validation
**Prompt**: "Validate a config that's missing the `skills` array."
**Expected**: Agent flags `skills` as a required field and reports a validation error.
**Pass Criteria**: Missing field detected; clear error message.

### SI-CFG-003: Path Resolution
**Prompt**: "How does the config resolve relative paths?"
**Expected**: Agent explains that paths are relative to the repo root (found by walking up to `.git/`), and the `_repo_root` key is injected into the loaded config at runtime.
**Pass Criteria**: Repo root detection and path resolution mechanism described.

## Structural Checks (SI-CHK)

### SI-CHK-001: Skill File Existence
**Prompt**: "Run structural checks on a skill tree where one SKILL.md file is missing."
**Expected**: `self_check.py` reports a FAIL finding for the missing file, PASS for all others.
**Pass Criteria**: Missing file detected; exit code 1; other checks still run.

### SI-CHK-002: Owner Header Check
**Prompt**: "Verify that all skill files have the correct owner header."
**Expected**: `self_check.py` checks the first 10 lines of each SKILL.md for the configured owner pattern.
**Pass Criteria**: Files with owner header pass; files without it fail with specific message.

### SI-CHK-003: YAML Frontmatter Validation
**Prompt**: "Check frontmatter on a SKILL.md that has `name: wrong-name` but lives in `correct-name/SKILL.md`."
**Expected**: `self_check.py` reports a FAIL: frontmatter `name` doesn't match directory name.
**Pass Criteria**: Mismatch detected; expected vs actual values shown.

### SI-CHK-004: Cross-Reference Validation
**Prompt**: "Check cross-references between skill files."
**Expected**: `self_check.py` verifies that if skill A references skill B, skill B exists and optionally references back.
**Pass Criteria**: Broken references detected as FAIL; valid references as PASS.

### SI-CHK-005: Custom Check Registration
**Prompt**: "How do I add a domain-specific structural check?"
**Expected**: Agent explains the check function signature `(config: dict) -> List[Finding]` and shows how to register it in the assertions JSON or pass it to `run_all_checks`.
**Pass Criteria**: Function signature documented; registration mechanism clear.

### SI-CHK-006: Pre-Commit Mode
**Prompt**: "Run self-check in pre-commit mode."
**Expected**: `self_check.py --pre-commit` runs a fast subset of checks (file existence, frontmatter) and exits 0/1.
**Pass Criteria**: Reduced check set; fast execution; clean exit code.

## Content Assertions (SI-VER)

### SI-VER-001: Contains Assertion
**Prompt**: "Write a contains assertion that checks for 'DMA' in the `dma` skill file."
**Expected**: Assertion format: `{"type": "contains", "skill": "dma", "pattern": "DMA", "description": "DMA mentioned"}` — passes if regex matches anywhere in the file.
**Pass Criteria**: Assertion format correct; regex matching behavior described.

### SI-VER-002: Not-Contains Assertion
**Prompt**: "Write a not_contains assertion to ensure '0x57xx' never appears in any skill file."
**Expected**: Assertion with `"type": "not_contains"` — fails if the pattern is found.
**Pass Criteria**: Negative assertion format correct; failure on match behavior described.

### SI-VER-003: Value-Match Assertion
**Prompt**: "Write a value_match assertion that checks register BASE_ADDR near the pattern 'THC_BASE' equals '0x10D0'."
**Expected**: Assertion with `"type": "value_match"`, `"field_pattern": "THC_BASE"`, `"expected_value": "0x10D0"` — searches for field pattern, then checks nearby text (300 chars) for the expected value.
**Pass Criteria**: Proximity-based matching described; 300-char window documented.

### SI-VER-004: External Assertions File
**Prompt**: "Load assertions from a JSON file instead of hardcoding them."
**Expected**: Agent explains the assertions JSON format: `{"test_id": {"name": "...", "skill": "...", "assertions": [...]}}` and how `self_verify.py` loads it.
**Pass Criteria**: JSON format documented; file loading mechanism described.

### SI-VER-005: Category Filtering
**Prompt**: "Run only assertions in category 'SPI'."
**Expected**: `self_verify.py --category SPI` filters tests by ID prefix or explicit category field.
**Pass Criteria**: Filtering works; only matching tests run; others skipped.

### SI-VER-006: Assertion Coverage Gap Detection
**Prompt**: "Find important terms in skill files that have no assertion checking them."
**Expected**: The improve pipeline's coverage gap detector extracts important terms (register names, hex values, protocol keywords) and reports which ones lack any verify assertion.
**Pass Criteria**: Gap detection produces actionable list; terms categorized by importance.

## Improvement Pipeline (SI-IMP)

### SI-IMP-001: Full Pipeline Run
**Prompt**: "Run the full self-improvement pipeline."
**Expected**: Pipeline executes: Check → Verify → Propose → Report. Each stage's findings feed into proposal generation.
**Pass Criteria**: All stages execute in order; proposals generated from FAIL findings.

### SI-IMP-002: Dry Run Mode
**Prompt**: "Run self-improve in dry-run mode."
**Expected**: `self_improve.py --dry-run` runs all stages and generates proposals but does NOT apply any changes.
**Pass Criteria**: No files modified; proposals listed in output; `auto_apply` overridden to False.

### SI-IMP-003: Proposal Generation
**Prompt**: "How are proposals generated from findings?"
**Expected**: Agent explains that FAIL findings from check and verify stages are mapped to Proposal objects with: id, priority (from severity), category, target_file, action, description, rationale, source_findings.
**Pass Criteria**: Finding-to-proposal mapping described; all Proposal fields documented.

### SI-IMP-004: Human Approval Gate
**Prompt**: "Can proposals be auto-applied?"
**Expected**: Agent explains that `require_human_approval: true` (default) writes proposals to JSON for review. Setting `auto_apply: true` enables automatic application, but only for LOW severity proposals by default.
**Pass Criteria**: Approval gate behavior described; safety defaults documented.

### SI-IMP-005: Changelog Generation
**Prompt**: "Does self-improve maintain a changelog?"
**Expected**: Agent explains that each run appends a summary to a markdown changelog: timestamp, stages run, findings count, proposals generated, and applied changes.
**Pass Criteria**: Changelog format described; append-only behavior confirmed.

## Data Model (SI-MDL)

### SI-MDL-001: Finding Class
**Prompt**: "Describe the Finding data model."
**Expected**: Finding has: check (str), target (str), status (PASS/FAIL/WARN/ERROR/SKIP), message (str), severity (int 0-4, default 2), details (Any — str or dict).
**Pass Criteria**: All fields listed with types; severity scale documented (0=info, 4=critical).

### SI-MDL-002: Report Class
**Prompt**: "Describe the Report data model."
**Expected**: Report has: name (str), version (str), timestamp (str), findings (List[Finding]). Methods: add(), compute_summary(), to_dict(), to_json(), to_text(), save(). Properties: pass_count, fail_count, has_failures, has_warnings.
**Pass Criteria**: All fields, methods, and properties listed.

### SI-MDL-003: Proposal Class
**Prompt**: "Describe the Proposal data model."
**Expected**: Proposal has: id, priority, category, target_file, action (ADD/UPDATE/DELETE/FIX), description, rationale, source_findings, status (PENDING/APPLIED/REJECTED/DEFERRED).
**Pass Criteria**: All fields listed; action and status enums documented.

## Portability (SI-PORT)

### SI-PORT-001: New Domain Bootstrap
**Prompt**: "I have a new skill tree for 'usb-pd' with 3 sub-skills. Set up self-improvement."
**Expected**: Agent generates a config JSON, creates the assertions file structure, and runs an initial check to establish baseline.
**Pass Criteria**: Config generated; initial check runs; baseline report produced.

### SI-PORT-002: Migrate from THC-Specific
**Prompt**: "How does the generic self-improve framework differ from the THC-specific one?"
**Expected**: Agent explains: same pattern (check/verify/improve), but config-driven instead of hardcoded. Domain knowledge is in the assertions JSON and config, not in the tool code.
**Pass Criteria**: Key difference (config-driven vs hardcoded) clearly stated; migration path described.

### SI-PORT-003: Custom Check Functions
**Prompt**: "Can I add domain-specific checks beyond the built-in ones?"
**Expected**: Agent explains that custom checks follow the `(config: dict) -> List[Finding]` signature and can be registered by adding them to the check list in the orchestrator.
**Pass Criteria**: Extension mechanism documented; function signature specified.
