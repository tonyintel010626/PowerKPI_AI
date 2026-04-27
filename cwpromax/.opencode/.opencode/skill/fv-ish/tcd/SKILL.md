---
name: fv-ish/tcd
description: >
  TCD (Test Case Description) creation skill — reads existing TCDs from HSDES,
  applies a standardized template, generates new or amended TCDs from reference documents,
  and outputs local files with full source attribution. Domain-agnostic.
disable: false
license: MIT
---

# Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `fv-ish/tcd` |
| **Domain** | Domain-agnostic — TCD (Test Case Description) Creation & Standardization |
| **Owner** | Leem, Yi Jie (`yleem`) |
| **Last Updated** | 2026-04-07 (rev2.0 — TCD-only split from combined TCD/TC skill) |
| **Default Tenant** | User-configurable per session (no hardcoded default — always ask user) |

> **IMPORTANT**: This skill generates **local files only**. It does NOT write directly to HSDES.
> All generated TCDs are saved as local markdown files for user review before manual upload.

> **SCOPE**: This skill covers **TCD (Test Case Description) ONLY**.
> For Test Cases (TC), use the separate `fv-ish/tc` sub-skill.

---

# MANDATORY TEMPLATE

> **THE TCD TEMPLATE IS MANDATORY. ALL TCD OUTPUT MUST FOLLOW THIS TEMPLATE.**
>
> Template file: `templates/tcd_template.md`
>
> This template is based on **"TCD & TC Template Details.docx" Version 20 (12/17/2025)**.
> Reference: https://intel.sharepoint.com/:w:/r/sites/csve/Shared%20Documents/FV%20Domains%20alignment/Test%20Plan%20Methodologies/TCTCD%20new%20template.docx
>
> **Rules:**
> 1. Every TCD output file MUST use this template structure — no exceptions.
> 2. All 10 sections MUST be present in every TCD (optional sections may state "Not applicable" but MUST NOT be silently removed).
> 3. The Identification header and Sources & References footer are MANDATORY in every TCD.
> 4. If the user provides their own template, it replaces the default — but the replacement MUST still be used consistently for all output.
> 5. Never generate a TCD that deviates from the active template structure.

## TCD Template Structure (10 Sections)

| # | Section | Required? | Description |
|---|---------|-----------|-------------|
| — | **Identification** | MANDATORY | Header with metadata fields (title, HSDES ID, parent test plan, system, category, family, priority, owner, etc.) |
| 1 | **Description** | MANDATORY | What feature/behavior is being tested, scope, expected behavior |
| 2 | **Algorithm of Testing** | MANDATORY | Step-by-step test algorithm (setup, stimulus, observation, pass/fail, cleanup) |
| 3 | **Randomization** | MANDATORY | Randomization parameters, ranges, seeds — or "No randomization — deterministic test" |
| 4 | **Required Configuration and Dependencies** | MANDATORY | All prerequisites: platform, BIOS, FW, OS/driver, HW BOM, IP initial state, equipment |
| 5 | **Coverage** | Optional | Coverage model, parameter space, bins, target percentage |
| 6 | **Cross-Feature Interaction** | MANDATORY | Interactions with other features/IPs, shared resources, sensitivities |
| 7 | **DFx Requirements** | MANDATORY | Design-for-Test/Debug hooks, trace points, observability needs |
| 8 | **Negative Testing** | Optional | Error injection, invalid input, timeout, recovery scenarios |
| 9 | **PVT Aspects** | Optional | Post-silicon specific: stepping, fuse/config dependencies |
| 10 | **Performance / Bandwidth Testing** | Optional | Throughput, latency, bandwidth metrics and thresholds |
| — | **Sources & References** | MANDATORY | Source attribution table + notes (see Phase 5) |

## TCD vs TC — Scope Boundary

| Aspect | TCD (this skill) | TC (`fv-ish/tc` skill) |
|--------|-------------------|------------------------|
| **Purpose** | Strategic — WHAT to test | Tactical — HOW to execute |
| **Template** | 10 sections | 11 sections (different structure) |
| **HSDES tenant** | `sighting_central.test_case_definition` (default — user-configurable) | `sighting_central.test_case` (default — user-configurable) |
| **Relationship** | Parent of TCs, child of Test Plan | Child of TCD |
| **Unique sections** | Algorithm of Testing, Randomization, Coverage, Cross-Feature Interaction, DFx Requirements, Negative Testing | Test Steps, Pass/Fail Criteria & HW Errors, Intent Verify, Validation SW, Ecosystem SW, Test HW Requirements, Validation Automation Global Checkers, ISOC Validation |

---

# CAPABILITIES OVERVIEW

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **HSDES Read** | Query existing TCDs from HSDES (any tenant) as reference material |
| 2 | **Template Enforcement** | Apply the MANDATORY TCD template to all generated output; require user confirmation before amending existing TCDs |
| 3 | **Multi-Document Ingestion** | Access and extract content from multiple reference documents (HAS, specs, datasheets, etc.) to generate TCDs |
| 4 | **Source Attribution** | Every generated TCD includes a "Sources & References" section with document name + link at the end |
| 5 | **Word Export** | Convert generated TCD markdown files to Word (.docx) format |

### Out of Scope (by design)

- Direct write-back to HSDES (output is local files only)
- TC (Test Case) creation — use `fv-ish/tc` sub-skill
- NGA test suite/group mapping
- Test execution or automation

---

# HSDES ACCESS

## How This Skill Accesses HSDES

All access is **READ-ONLY**. No writes, no updates, no deletes.

Two access methods are available, chosen automatically based on environment:

### Method A: Browser-Based (Primary — always available)

Use `browsermcp` to navigate to HSDES web portal and extract record content.

```
URL pattern: https://hsdes.intel.com/appstore/article/#/<HSDES_ID>
```

**When to use**: Default method. Works in any environment. Best for:
- Fetching individual records by ID
- Reading full Description field content (TCD body)
- Discovering available fields visually

**How it works**:
1. Navigate to `https://hsdes.intel.com/appstore/article/#/<ID>`
2. Take a browser snapshot to capture all visible fields
3. Use JavaScript evaluation to extract Description field HTML content
4. Parse the structured content into TCD sections

### Method B: Python Script (When `pysvtools` is available)

Use `pysvtools.hsdes` for programmatic bulk queries via EQL.

```bash
python tools/hsdes_query.py --id <ID>
python tools/hsdes_query.py --tenant <tenant> --eql "<query>"
```

**When to use**: When Python + `pysvtools` is installed. Best for:
- EQL search queries (find multiple records by criteria)
- Bulk field extraction
- Automated pipelines

### Access Methods Summary

| Method | When to Use | Tenant Required? | Environment |
|--------|-------------|-----------------|-------------|
| **Browser by ID** | You have a specific HSDES article ID | No (auto-detected from URL) | Always available |
| **Script by ID** | Same, but need JSON output | No (auto-detected) | Needs `pysvtools` |
| **Script by EQL** | Find records matching criteria | **Yes** (must specify) | Needs `pysvtools` |
| **Browser field discovery** | See all fields on a record | No | Always available |
| **Script field discovery** | Get all fields as JSON | No | Needs `pysvtools` |

### Parameters

| Parameter | Required? | Default | Description |
|-----------|-----------|---------|-------------|
| `--id` | Option A | — | HSDES article ID (integer). Auto-detects tenant. |
| `--tenant` | For EQL; optional for ID | `None` | HSDES tenant string. See Common Tenants below. |
| `--eql` | Option B | — | EQL query string. Requires `--tenant`. |
| `--fields` | No | `id,title,description,owner,status` | Comma-separated field list to return. |
| `--discover-fields` | No | `false` | With `--id`: fetch all fields to discover available schema. |

### Common Tenants

> **IMPORTANT**: Always confirm the tenant with the user before querying. These are common examples — your team may use different tenants.

| Tenant | Description | Typical Use |
|--------|-------------|-------------|
| `sighting_central.test_case_definition` | TCD records in Sighting Central | TCD creation and reference |
| `sighting_central.test_case` | TC records in Sighting Central | TC reference lookup |
| `sighting_central` | Sighting Central (general) | Sighting queries |
| `heia_soc.test_case` | Test cases (PVIM/HEIA) | TC reference lookup |
| `heia_soc.sighting` | Domain sightings | Known issue cross-reference |

**First-time tenant selection prompt** — always ask the user:
> "Which HSDES tenant are your TCDs stored in? Common options:
> 1. `sighting_central.test_case_definition` — TCD records
> 2. Other — please specify
>
> (I'll remember your choice for this session)"

### EQL Query Rules

HSDES EQL has specific limitations:

| Supported | Not Supported |
|-----------|--------------|
| `=`, `!=`, `<`, `>`, `<=`, `>=` | `~` (tilde/contains) |
| `AND`, `OR`, `NOT` | Wildcards (`*`, `?`) |
| `LIKE '%term%'` (partial match) | `contains()` function |
| `IN ('a', 'b', 'c')` | `maxRows` parameter |
| Parentheses for grouping | |

### Usage Examples

```bash
# 1. Fetch a specific article by ID (auto-detects tenant)
python tools/hsdes_query.py --id 16021234567

# 2. Fetch from a specific tenant
python tools/hsdes_query.py --id 16021234567 --tenant sighting_central.test_case_definition

# 3. Discover all available fields for a record
python tools/hsdes_query.py --id 16021234567 --discover-fields

# 4. EQL search in sighting_central.test_case_definition
python tools/hsdes_query.py --tenant sighting_central.test_case_definition \
  --eql "title LIKE '%ISH%' AND status = 'open'"

# 5. EQL search with custom fields
python tools/hsdes_query.py --tenant sighting_central.test_case_definition \
  --eql "title LIKE '%HECI%'" \
  --fields "id,title,description,owner,status,priority"
```

---

# WORKFLOW

## Phase 1: REFERENCE — Gather Existing TCDs from HSDES

**Purpose**: Read existing TCDs from HSDES to understand current coverage and avoid duplication.

### Step 1.1: Determine Tenant and Query Strategy

Ask the user:
- **Tenant**: Which HSDES tenant? (present the Common Tenants list — never assume)
- **Search scope**: By ID, by keyword, by domain/forum, or by status?

### Step 1.2: Query HSDES for Existing Records

**Browser-based (primary):**
```
1. Navigate to: https://hsdes.intel.com/appstore/article/#/<HSDES_ID>
2. Take browser snapshot to capture all fields
3. Extract Description field content (contains the TCD body)
4. Parse metadata: title, system, category, family, owner, status, parent_id
```

**Script-based (when pysvtools available):**
```python
from pysvtools import hsdes

hsd = hsdes.HSDES()
hsd.config('<user_specified_tenant>')  # always use user's tenant
results = hsd.search(
    "title LIKE '%<keyword>%' AND status = 'open'",
    showFields="id,title,description,owner,status"
)
```

### Step 1.3: What to Collect

| Field | Purpose |
|-------|---------|
| `id` | HSDES ID for cross-reference |
| `title` | Record title — check naming conventions |
| `description` | Full description — identify TCD coverage |
| `owner` | Current owner |
| `status` | Record status (open, approved, closed, etc.) |
| *(additional fields)* | Tenant-specific — use `--discover-fields` to find |

---

## Phase 2: TEMPLATE — Load and Apply the MANDATORY TCD Template

**Purpose**: Enforce consistent TCD format across all generated output.

> **REMINDER**: The TCD template (`templates/tcd_template.md`) is **MANDATORY**.
> All TCD output MUST follow this 10-section structure.

### Template Priority

1. **User-provided template** — If user supplies a template file, use it exclusively (it becomes the new MANDATORY template for this session)
2. **Default template** — Use `templates/tcd_template.md` (MANDATORY — always loaded)

### Loading User Template

When the user provides a template:
1. Read the template file using the `Read` tool
2. Parse the template structure (sections, fields, formatting)
3. Store as the active template for all generation in this session
4. Confirm template loaded with user:
   > "Template loaded from `{path}`. It has {N} sections: {section_list}. This replaces the default template for this session. Shall I proceed?"

### Template Application Rules

| Scenario | Action |
|----------|--------|
| **New TCD** | Apply MANDATORY template directly — fill all sections from source documents |
| **Amend existing TCD** | Show diff between existing and template-compliant version; **REQUIRE user confirmation** before saving |
| **Missing info** | Mark section as `[TODO: <what's needed>]` — never leave blank, never fabricate |

### Amend Confirmation Protocol

When amending an existing TCD, ALWAYS follow this flow:

```
1. Show the EXISTING TCD content (from HSDES)
2. Show the PROPOSED amended version (template-applied)
3. Highlight CHANGES with clear markers:
   - [ADDED] — new content not in original
   - [MODIFIED] — changed from original
   - [REMOVED] — removed from original (rare — preserve original intent)
   - [REFORMATTED] — same content, template structure applied
4. ASK: "Do you want to proceed with these changes? (yes/no/edit)"
5. Only save if user confirms
```

---

## Phase 3: INGEST — Multi-Document Content Extraction

**Purpose**: Extract test-relevant content from multiple reference documents to generate comprehensive TCDs.

### Supported Document Sources

| Source Type | How to Access | What to Extract |
|-------------|--------------|-----------------|
| **IP HAS** | `fv-ish/has` skill or Co-De Sign | Register specs, protocol definitions, state machines, timing |
| **Specification docs** | User-provided doc | Feature specs, interface definitions |
| **Sensor/Device Datasheets** | User-provided doc | Device registers, data ranges, sampling rates |
| **Existing Test Plans** | User-provided doc | Coverage matrix, test strategy, priority |
| **BIOS/Platform Spec** | User-provided doc | BIOS knobs, ACPI tables, platform config |
| **HSDES Existing Records** | Phase 1 output | Current coverage, gaps, patterns |
| **Any other document** | User-provided | Extract test-relevant content |

### Document Ingestion Workflow

```
For each document provided by the user:
  1. IDENTIFY document type and relevance to TCD generation
  2. DELEGATE to `doc-study` skill (DOC-STUDY agent) for extraction:
     - Phase: INVENTORY -> EXTRACT -> VERIFY
     - Extract ALL test-relevant content: features, registers, protocols,
       state transitions, error conditions, boundary values
  3. ORGANIZE extracted content by test category
  4. CROSS-REFERENCE with Phase 1 HSDES data to identify:
     - Coverage gaps (features with no existing TCD)
     - Enhancement opportunities (existing TCDs missing scenarios)
     - Duplication (avoid re-creating existing coverage)
  5. RECORD source metadata for attribution (doc name, section, page/line)
```

### Content-to-TCD Mapping Rules

| Document Content | Maps To TCD Section |
|-----------------|-------------------|
| Feature description | Section 1: Description |
| Test algorithm / workflow | Section 2: Algorithm of Testing |
| Randomization strategy | Section 3: Randomization |
| Prerequisites / dependencies | Section 4: Required Configuration and Dependencies |
| Parameter space / coverage model | Section 5: Coverage |
| Feature interactions | Section 6: Cross-Feature Interaction |
| Debug hooks / observability | Section 7: DFx Requirements |
| Error conditions / boundary values | Section 8: Negative Testing |
| Silicon-specific behavior | Section 9: PVT Aspects |
| Performance / bandwidth metrics | Section 10: Performance / Bandwidth Testing |

---

## Phase 4: GENERATE — Create TCD Output Files

**Purpose**: Generate compliant, source-attributed TCD files as local markdown.

### Output File Convention

```
Output directory: ./tcd_output/    (or user-specified path)

File naming:
  NEW TCD:    TCD_<category>_<feature>_<YYYYMMDD>.md
  AMENDED:    TCD_<HSDES_ID>_amended_<YYYYMMDD>.md
  BATCH:      TCD_batch_<category>_<YYYYMMDD>/
                |- TCD_<feature1>.md
                |- TCD_<feature2>.md
                +- batch_index_<YYYYMMDD>.md
```

### Generation Rules

1. **Apply the MANDATORY template** — every TCD MUST follow `templates/tcd_template.md` (or user-provided replacement)
2. **Fill every template section** — use `[TODO: ...]` for missing info, never leave blank
3. **One TCD per file** — each test case description gets its own file
4. **Include HSDES cross-reference** — if an existing record was used as reference, note its ID
5. **Platform-specific notes** — mark platform differences with `[NVL]`, `[TTL]`, etc. if applicable
6. **Source attribution** — ALWAYS include Sources section (see Phase 5)

### Batch Generation

When generating multiple TCDs from a feature area:

```
1. Present a GENERATION PLAN to the user:
   "I will generate {N} TCDs for {category}:
    1. TCD_{name1} - {brief description}
    2. TCD_{name2} - {brief description}
    ...
   Proceed? (yes/no/edit)"

2. Only generate after user confirms the plan
3. Create a summary index file: batch_index_<YYYYMMDD>.md
```

### Word (.docx) Export

After generating TCD markdown files, convert to Word format using:

```bash
python tools/md_to_docx.py <input.md> <output.docx>
```

Or use the tool programmatically:

```python
from tools.md_to_docx import md_to_docx
md_to_docx("tcd_output/TCD_feature_20260407.md", "C:/Users/pgsvlab/Downloads/TCD_feature_20260407.docx")
```

---

## Phase 5: ATTRIBUTE — Source Documentation

**Purpose**: Every generated TCD MUST end with a Sources section documenting where the content came from.

### Source Attribution Format

Every generated TCD file MUST end with this section:

```markdown
---

## Sources & References

| # | Source Document | Section/Page | Link | Date Accessed |
|---|----------------|-------------|------|---------------|
| 1 | {Document Name} | {Section or Page reference} | {URL or file path} | {YYYY-MM-DD} |
| 2 | {Document Name} | {Section or Page reference} | {URL or file path} | {YYYY-MM-DD} |

### Source Notes
- **Primary**: {Which source was the main basis for this TCD}
- **Cross-referenced with**: HSDES #{id} - {existing record title} (if applicable)
- **Generated by**: TCD Skill v2.0 on {generation date}
```

### Attribution Rules

1. **NEVER omit the Sources section** — it is mandatory for every TCD
2. **Be specific** — reference the exact section/page/register, not just the doc name
3. **Multiple sources per TCD** — most TCDs will reference 2+ sources
4. **Mark unverified content** — if a source couldn't be verified, note it:
   `[UNVERIFIED — based on general knowledge, not confirmed against source]`

---

# SKILL INTEGRATION

## Required Skills (load before using this skill)

| Skill | Purpose | When |
|-------|---------|------|
| `hsdes` | Query existing TCDs from HSDES | Phase 1 — always |

## Optional Skills (load as needed)

| Skill | Purpose | When |
|-------|---------|------|
| `fv-ish/has` | ISH HAS document queries | Phase 3 — when generating ISH HW-level TCDs |
| `fv-ish/registers` | Register map details | Phase 3 — register-level test descriptions |
| `fv-ish/heci` | HECI protocol details | Phase 3 — HECI/ISHTP test descriptions |
| `fv-ish/sensors` | Sensor integration details | Phase 3 — sensor data test descriptions |
| `fv-ish/dma` | DMA architecture details | Phase 3 — DMA test descriptions |
| `fv-ish/power` | Power management details | Phase 3 — PM test descriptions |
| `fv-ish/debug` | Known issues, sightings | Phase 3 — negative/error test descriptions |
| `doc-study` | Multi-document extraction | Phase 3 — always for document ingestion |
| `codesign` | Co-De Sign API for live HAS queries | Phase 3 — live HAS access |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `fv-ish/tc` | **TC (Test Case) creation** — child records of TCDs. Use when you need to create executable test cases from a TCD. |

## Sub-Agent Delegation

| Task | Agent | When |
|------|-------|------|
| Heavy document extraction | `DOC-STUDY` | Large documents (>50 pages) |
| Codebase exploration | `explore` | Finding existing test patterns in repo |
| General research | `general` | Multi-step research across sources |

---

# INTERACTION PATTERNS

## Pattern 1: Create New TCD from Scratch

```
User: "Create a TCD for HECI connection establishment"

Agent workflow:
1. Load skills: fv-ish/tcd, hsdes
2. Ask: What tenant? What domain? (or use defaults)
3. Phase 1: Query HSDES for existing related records
4. Phase 2: Load MANDATORY TCD template
5. Phase 3: Gather content from available sources
6. Phase 4: Generate TCD file with all 10 sections filled
7. Phase 5: Add source attribution
8. Present to user for review
```

## Pattern 2: Create TCDs from Document

```
User: "Here's a spec document. Generate TCDs for the DMA chapter"

Agent workflow:
1. Load skills: fv-ish/tcd, doc-study, hsdes
2. Phase 1: Query HSDES for existing related records
3. Phase 2: Load MANDATORY TCD template
4. Phase 3: Delegate doc-study to extract chapter content
5. Phase 3: Map extracted features -> TCD candidates
6. Phase 3: Cross-reference with HSDES to find gaps
7. Phase 4: Present generation plan, get user confirmation
8. Phase 4: Generate batch TCD files (each following MANDATORY template)
9. Phase 5: Add source attribution to each
```

## Pattern 3: Amend Existing TCD to Template

```
User: "Bring HSDES #12345678 into compliance with our template"

Agent workflow:
1. Load skills: fv-ish/tcd, hsdes
2. Phase 1: Fetch record #12345678 from HSDES
3. Phase 2: Load MANDATORY TCD template
4. Phase 2: Generate template-compliant version
5. Phase 2: Show diff with [ADDED]/[MODIFIED]/[REFORMATTED] markers
6. Phase 2: WAIT for user confirmation
7. Phase 4: Save amended version as local file
8. Phase 5: Add source attribution (original HSDES + template)
```

## Pattern 4: Batch Generate from Feature Area

```
User: "Generate all missing TCDs for sensor enumeration"

Agent workflow:
1. Load skills: fv-ish/tcd, hsdes + relevant domain skills
2. Phase 1: Query all existing related records from HSDES
3. Phase 3: Gather feature-area content from sources
4. Phase 3: Identify coverage gaps
5. Phase 4: Present generation plan (list of N TCDs)
6. Phase 4: WAIT for user confirmation
7. Phase 4: Generate batch, create index file (each following MANDATORY template)
8. Phase 5: Source attribution on each file
```

---

# GUARDRAILS

## Must-Follow Rules

1. **MANDATORY TEMPLATE** — Every TCD output MUST follow `templates/tcd_template.md` (or user-provided replacement)
2. **NEVER write to HSDES** — output is local files only
3. **NEVER amend existing TCDs without user confirmation** — always show diff first
4. **NEVER omit the Sources section** — every TCD must have source attribution
5. **NEVER fabricate test steps or expected results** — use `[TODO]` if info unavailable
6. **NEVER generate without a plan** — for batch (>1 TCD), present plan and get confirmation
7. **ALWAYS apply the MANDATORY template** — user-provided replaces default but must be used consistently
8. **ALWAYS cross-reference HSDES** — check for existing coverage before generating new TCDs
9. **ALWAYS mark unverified content** — `[TODO]` or `[UNVERIFIED]` tags
10. **Tenant is configurable** — never assume a tenant, ask or use user's specified default
11. **This skill is TCD-only** — for TC (Test Case) creation, redirect to `fv-ish/tc`

## Quality Checks Before Output

Before saving any TCD file, verify:

- [ ] MANDATORY template structure followed (all 10 sections present)
- [ ] Identification header complete
- [ ] Test algorithm is actionable and specific (not vague)
- [ ] Randomization section addressed (even if "deterministic")
- [ ] Required Configuration section complete
- [ ] Sources & References section is present and populated
- [ ] No fabricated values — register addresses, bit fields, protocol values
- [ ] `[TODO]` markers for any unverified or missing content
- [ ] File naming follows convention

---

# TOOLS

## `tools/hsdes_query.py`

HSDES query script for reading existing TCD records. Tenant is always user-configurable.

```bash
# List known tenants
python tools/hsdes_query.py --list-tenants

# Fetch by ID (auto-detects tenant)
python tools/hsdes_query.py --id <HSDES_ID>

# Fetch by ID from explicit tenant
python tools/hsdes_query.py --id <HSDES_ID> --tenant sighting_central.test_case_definition

# Discover all fields for a record
python tools/hsdes_query.py --id <HSDES_ID> --discover-fields

# EQL search (requires tenant)
python tools/hsdes_query.py --tenant sighting_central.test_case_definition \
  --eql "title LIKE '%keyword%'"

# EQL search with custom fields
python tools/hsdes_query.py --tenant sighting_central.test_case_definition \
  --eql "title LIKE '%keyword%'" --fields "id,title,description,owner"
```

## `tools/tcd_generator.py`

TCD file generator — fills MANDATORY template and appends source attribution.

```bash
# Generate single TCD
python tools/tcd_generator.py --template templates/tcd_template.md \
  --output ./tcd_output/TCD_feature_test_20260403.md \
  --field TC_TITLE="My Test Case Description" \
  --field TEST_CATEGORY="Feature Area" \
  --source "Doc Name|Section 5.2|https://link|2026-04-03"

# Batch generate from JSON
python tools/tcd_generator.py --template templates/tcd_template.md \
  --json batch_spec.json --output-dir ./tcd_output/batch/

# Amend existing (requires --user-confirmed)
python tools/tcd_generator.py --template templates/tcd_template.md \
  --existing old_tcd.md --output amended_tcd.md \
  --mode amend --user-confirmed
```

## `tools/md_to_docx.py`

Markdown-to-Word converter for TCD output files.

```bash
# Convert a single TCD markdown file to Word
python tools/md_to_docx.py tcd_output/TCD_feature_20260407.md C:/Users/pgsvlab/Downloads/TCD_feature_20260407.docx
```

Features:
- Intel blue color scheme (headers: `#1F4E79`)
- Table formatting with blue header rows
- Calibri font, narrow margins
- Supports markdown tables, headings, lists, blockquotes, code blocks
