---
name: fv-ish/tc
description: >
  TC (Test Case) creation skill — reads existing TCs from HSDES,
  applies a standardized template, generates new or amended TCs from reference documents and parent TCDs,
  and outputs local files with full source attribution. Domain-agnostic.
disable: false
license: MIT
---

# Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `fv-ish/tc` |
| **Domain** | Domain-agnostic — TC (Test Case) Creation & Standardization |
| **Owner** | Leem, Yi Jie (`yleem`) |
| **Last Updated** | 2026-04-07 (rev1.0 — TC-only, split from combined TCD/TC skill) |
| **Default Tenant** | User-configurable per session (no hardcoded default — always ask user) |

> **IMPORTANT**: This skill generates **local files only**. It does NOT write directly to HSDES.
> All generated TCs are saved as local markdown files for user review before manual upload.

> **SCOPE**: This skill covers **TC (Test Case) ONLY**.
> For Test Case Descriptions (TCD), use the separate `fv-ish/tcd` sub-skill.

---

# MANDATORY TEMPLATE

> **THE TC TEMPLATE IS MANDATORY. ALL TC OUTPUT MUST FOLLOW THIS TEMPLATE.**
>
> Template file: `templates/tc_template.md`
>
> This template is based on **"TCD & TC Template Details.docx" Version 20 (12/17/2025)**.
> Reference: https://intel.sharepoint.com/:w:/r/sites/csve/Shared%20Documents/FV%20Domains%20alignment/Test%20Plan%20Methodologies/TCTCD%20new%20template.docx
>
> **Rules:**
> 1. Every TC output file MUST use this template structure — no exceptions.
> 2. All 11 sections MUST be present in every TC (optional sections may state "Not applicable" but MUST NOT be silently removed).
> 3. The Identification header and Sources & References footer are MANDATORY in every TC.
> 4. If the user provides their own template, it replaces the default — but the replacement MUST still be used consistently for all output.
> 5. Never generate a TC that deviates from the active template structure.
> 6. Every TC MUST reference its parent TCD (HSDES ID and title) in the Identification header.

## TC Template Structure (11 Sections)

| # | Section | Required? | Description |
|---|---------|-----------|-------------|
| — | **Identification** | MANDATORY | Header with metadata fields (title, HSDES ID, parent TCD, tenant, system, category, family, scope, owner, val_environment, val_framework, automation, free_tags, etc.) |
| 1 | **TC Description** | MANDATORY | What this specific test case validates, how it differs from parent TCD scope |
| 2 | **Test Steps** | MANDATORY | Detailed, numbered, executable test steps (setup, action, observation, cleanup) |
| 3 | **Pass/Fail Criteria & HW Errors** | MANDATORY | Exact pass/fail conditions, known HW errors/errata/sightings |
| 4 | **Intent Verify** | MANDATORY | Design intent being verified, HAS/spec requirement mapping |
| 5 | **Validation SW: Tool and Content Requirements** | MANDATORY | All software tools and content required to execute |
| 6 | **Ecosystem SW: Test Requirements** | MANDATORY | OS, driver, firmware, BIOS, ecosystem SW requirements |
| 7 | **Test HW Requirements and HW Configuration** | MANDATORY | Platform, BOM, external equipment, board config |
| 8 | **PVT** | Optional | Post-silicon specific: stepping, voltage/temp corners, fuse/CAPID |
| 9 | **Performance/BW** | Optional | Latency, throughput, bandwidth metrics and thresholds |
| 10 | **Validation Automation Global Checkers** | Optional | Global checker integration for automated validation |
| 11 | **ISOC Validation** | Optional | iSOC (In-Silicon Observability and Control) validation aspects |
| — | **Sources & References** | MANDATORY | Source attribution table + notes (see Phase 5) |

## TC vs TCD — Scope Boundary

| Aspect | TC (this skill) | TCD (`fv-ish/tcd` skill) |
|--------|-----------------|--------------------------|
| **Purpose** | Tactical — HOW to execute | Strategic — WHAT to test |
| **Template** | 11 sections | 10 sections (different structure) |
| **HSDES tenant** | `sighting_central.test_case` (default — user-configurable) | `sighting_central.test_case_definition` (default — user-configurable) |
| **Relationship** | Child of TCD | Parent of TCs, child of Test Plan |
| **Unique sections** | Test Steps, Pass/Fail Criteria & HW Errors, Intent Verify, Validation SW, Ecosystem SW, Test HW Requirements, Validation Automation Global Checkers, ISOC Validation | Algorithm of Testing, Randomization, Coverage, Cross-Feature Interaction, DFx Requirements, Negative Testing |
| **Key metadata** | val_environment, val_framework, automation, scope, free_tags | priority, origin_project |

## TC-Specific Metadata Fields

TCs have additional metadata fields not present in TCDs:

| Field | Description | Example Values |
|-------|-------------|----------------|
| **Parent TCD** | HSDES ID + title of parent TCD | `15019042073 — [VisionSS][NVU] NVU PM` |
| **HSDES Tenant** | Tenant where TC is stored | `sighting_central.test_case` |
| **Scope** | Test scope classification | `Silicon`, `Platform`, `System` |
| **Val Environment** | Validation environment | `PythonSV`, `UEFI Shell`, `Windows`, `Linux` |
| **Val Framework** | Validation framework | `PythonSV/NGA`, `WinHEC`, `Custom` |
| **Automation** | Automation status | `Automated`, `Manual`, `Semi-automated` |
| **Free Tag 1** | Custom tag field | Domain-specific tag |
| **Free Tag 3** | Custom tag field | Domain-specific tag |

---

# CAPABILITIES OVERVIEW

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **HSDES Read** | Query existing TCs and parent TCDs from HSDES (any tenant) as reference material |
| 2 | **Template Enforcement** | Apply the MANDATORY TC template to all generated output; require user confirmation before amending existing TCs |
| 3 | **Parent TCD Linkage** | Every TC is linked to a parent TCD — ensure parent reference is always present |
| 4 | **Multi-Document Ingestion** | Access and extract content from multiple reference documents to generate TCs |
| 5 | **Source Attribution** | Every generated TC includes a "Sources & References" section with document name + link |
| 6 | **Word Export** | Convert generated TC markdown files to Word (.docx) format |

### Out of Scope (by design)

- Direct write-back to HSDES (output is local files only)
- TCD (Test Case Description) creation — use `fv-ish/tcd` sub-skill
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
- Fetching individual TC records by ID
- Reading full Description field content (TC body)
- Fetching parent TCD records for context
- Discovering available fields visually

**How it works**:
1. Navigate to `https://hsdes.intel.com/appstore/article/#/<ID>`
2. Take a browser snapshot to capture all visible fields
3. Use JavaScript evaluation to extract Description field HTML content
4. Parse the structured content into TC sections

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

### Common Tenants

> **IMPORTANT**: Always confirm the tenant with the user before querying. These are common examples — your team may use different tenants.

| Tenant | Description | Typical Use |
|--------|-------------|-------------|
| `sighting_central.test_case` | TC records in Sighting Central | TC creation and reference |
| `sighting_central.test_case_definition` | TCD records in Sighting Central | Parent TCD lookup |
| `sighting_central` | Sighting Central (general) | Sighting queries |
| `heia_soc.test_case` | Test cases (PVIM/HEIA) | TC reference lookup |
| `heia_soc.sighting` | Domain sightings | Known issue cross-reference |

**First-time tenant selection prompt** — always ask the user:
> "Which HSDES tenant are your TCs stored in? Common options:
> 1. `sighting_central.test_case` — TC records in Sighting Central
> 2. `heia_soc.test_case` — PVIM test cases
> 3. Other — please specify
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

---

# WORKFLOW

## Phase 1: REFERENCE — Gather Parent TCD and Existing TCs from HSDES

**Purpose**: Read the parent TCD and any existing TCs from HSDES to understand scope and avoid duplication.

### Step 1.1: Identify Parent TCD

Every TC must have a parent TCD. Ask the user:
- **Parent TCD**: What is the HSDES ID of the parent TCD?
- **Tenant**: Which HSDES tenant for TCs? (present the Common Tenants list — never assume)
- **Search scope**: By ID, by keyword, by parent TCD, or by status?

### Step 1.2: Fetch Parent TCD Content

Always fetch the parent TCD first to understand the test scope:

**Browser-based (primary):**
```
1. Navigate to: https://hsdes.intel.com/appstore/article/#/<PARENT_TCD_ID>
2. Take browser snapshot to capture all fields
3. Extract Description field content (contains the TCD body)
4. Parse: test description, algorithm, configuration requirements, coverage model
```

This content informs what TCs need to be created to cover the parent TCD's scope.

### Step 1.3: Query Existing TCs Under This TCD

Check if TCs already exist for this parent TCD:

```bash
# Search for TCs linked to parent TCD
python tools/hsdes_query.py --tenant sighting_central.test_case \
  --eql "parent_id = '<PARENT_TCD_ID>'"
```

### Step 1.4: What to Collect

| Field | Purpose |
|-------|---------|
| `id` | HSDES ID for cross-reference |
| `title` | Record title — check naming conventions |
| `description` | Full description — identify TC coverage |
| `parent_id` | Link to parent TCD |
| `owner` | Current owner |
| `status` | Record status |
| `val_environment` | Validation environment |
| `val_framework` | Validation framework |
| `automation` | Automation status |

---

## Phase 2: TEMPLATE — Load and Apply the MANDATORY TC Template

**Purpose**: Enforce consistent TC format across all generated output.

> **REMINDER**: The TC template (`templates/tc_template.md`) is **MANDATORY**.
> All TC output MUST follow this 11-section structure.

### Template Priority

1. **User-provided template** — If user supplies a template file, use it exclusively (it becomes the new MANDATORY template for this session)
2. **Default template** — Use `templates/tc_template.md` (MANDATORY — always loaded)

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
| **New TC** | Apply MANDATORY template directly — fill all sections from parent TCD + source documents |
| **Amend existing TC** | Show diff between existing and template-compliant version; **REQUIRE user confirmation** before saving |
| **Missing info** | Mark section as `[TODO: <what's needed>]` — never leave blank, never fabricate |

### Amend Confirmation Protocol

When amending an existing TC, ALWAYS follow this flow:

```
1. Show the EXISTING TC content (from HSDES)
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

**Purpose**: Extract test-relevant content from multiple reference documents to generate comprehensive TCs.

### Primary Source: Parent TCD

The parent TCD is always the primary source for TC content:
- **TCD Description** -> TC Description (narrow scope to specific scenario)
- **TCD Algorithm of Testing** -> TC Test Steps (make concrete and executable)
- **TCD Configuration** -> TC Ecosystem SW + Test HW Requirements
- **TCD Negative Testing** -> TC Pass/Fail Criteria (error handling)
- **TCD DFx Requirements** -> TC Validation SW (tools needed)

### Additional Document Sources

| Source Type | How to Access | What to Extract |
|-------------|--------------|-----------------|
| **Parent TCD** | HSDES (Phase 1) | Test scope, algorithm, config requirements |
| **IP HAS** | `fv-ish/has` skill or Co-De Sign | Register details, protocol sequences, exact values for test steps |
| **Specification docs** | User-provided doc | Feature behavior details for test step specificity |
| **Sensor/Device Datasheets** | User-provided doc | Device registers, exact values, command sequences |
| **Existing Test Scripts** | User-provided or repo | Existing automation patterns, tool usage |
| **HSDES Existing Records** | Phase 1 output | Current coverage, gaps, patterns |

### Content-to-TC Mapping Rules

| Document Content | Maps To TC Section |
|-----------------|-------------------|
| Specific test scenario | Section 1: TC Description |
| Register read/write sequences | Section 2: Test Steps |
| Expected register values / status | Section 3: Pass/Fail Criteria & HW Errors |
| HAS/spec requirement reference | Section 4: Intent Verify |
| Required tools (PythonSV, analyzers) | Section 5: Validation SW |
| OS/driver/FW/BIOS requirements | Section 6: Ecosystem SW |
| Platform/BOM/equipment | Section 7: Test HW Requirements |
| Stepping-dependent behavior | Section 8: PVT |
| Performance metrics | Section 9: Performance/BW |
| Global checker config | Section 10: Validation Automation Global Checkers |
| iSOC features | Section 11: ISOC Validation |

---

## Phase 4: GENERATE — Create TC Output Files

**Purpose**: Generate compliant, source-attributed TC files as local markdown.

### Output File Convention

```
Output directory: ./tcd_output/    (or user-specified path)

File naming:
  NEW TC:     TC_<feature>_<scenario>_<YYYYMMDD>.md
  AMENDED:    TC_<HSDES_ID>_amended_<YYYYMMDD>.md
  BATCH:      TC_batch_<feature>_<YYYYMMDD>/
                |- TC_<scenario1>.md
                |- TC_<scenario2>.md
                +- batch_index_<YYYYMMDD>.md
```

### Generation Rules

1. **Apply the MANDATORY template** — every TC MUST follow `templates/tc_template.md` (or user-provided replacement)
2. **Fill every template section** — use `[TODO: ...]` for missing info, never leave blank
3. **One TC per file** — each test case gets its own file
4. **Link to parent TCD** — every TC MUST reference its parent TCD HSDES ID and title
5. **Include HSDES cross-reference** — if an existing record was used as reference, note its ID
6. **Platform-specific notes** — mark platform differences with `[NVL]`, `[TTL]`, etc. if applicable
7. **Source attribution** — ALWAYS include Sources section (see Phase 5)

### Batch Generation

When generating multiple TCs from a parent TCD:

```
1. Present a GENERATION PLAN to the user:
   "From parent TCD #{parent_id} ({parent_title}), I will generate {N} TCs:
    1. TC_{scenario1} - {brief description}
    2. TC_{scenario2} - {brief description}
    ...
   Proceed? (yes/no/edit)"

2. Only generate after user confirms the plan
3. Create a summary index file: batch_index_<YYYYMMDD>.md
```

### Word (.docx) Export

After generating TC markdown files, convert to Word format using:

```bash
python tools/md_to_docx.py <input.md> <output.docx>
```

Or use the tool programmatically:

```python
from tools.md_to_docx import md_to_docx
md_to_docx("tcd_output/TC_feature_20260407.md", "C:/Users/pgsvlab/Downloads/TC_feature_20260407.docx")
```

---

## Phase 5: ATTRIBUTE — Source Documentation

**Purpose**: Every generated TC MUST end with a Sources section documenting where the content came from.

### Source Attribution Format

Every generated TC file MUST end with this section:

```markdown
---

## Sources & References

| # | Source Document | Section/Page | Link | Date Accessed |
|---|----------------|-------------|------|---------------|
| 1 | {Document Name} | {Section or Page reference} | {URL or file path} | {YYYY-MM-DD} |
| 2 | {Document Name} | {Section or Page reference} | {URL or file path} | {YYYY-MM-DD} |

### Source Notes
- **Primary**: {Which source was the main basis for this TC}
- **Parent TCD**: HSDES #{parent_id} - {parent_title}
- **Cross-referenced with**: HSDES #{id} - {existing record title} (if applicable)
- **Generated by**: TC Skill v1.0 on {generation date}
```

### Attribution Rules

1. **NEVER omit the Sources section** — it is mandatory for every TC
2. **ALWAYS reference the parent TCD** — in both Identification header and Sources section
3. **Be specific** — reference the exact section/page/register, not just the doc name
4. **Multiple sources per TC** — most TCs will reference parent TCD + 1-2 additional sources
5. **Mark unverified content** — if a source couldn't be verified, note it:
   `[UNVERIFIED — based on general knowledge, not confirmed against source]`

---

# SKILL INTEGRATION

## Required Skills (load before using this skill)

| Skill | Purpose | When |
|-------|---------|------|
| `hsdes` | Query existing TCs and parent TCDs from HSDES | Phase 1 — always |

## Optional Skills (load as needed)

| Skill | Purpose | When |
|-------|---------|------|
| `fv-ish/has` | ISH HAS document queries | Phase 3 — when generating ISH HW-level TCs |
| `fv-ish/registers` | Register map details | Phase 3 — register-level test steps |
| `fv-ish/heci` | HECI protocol details | Phase 3 — HECI/ISHTP test steps |
| `fv-ish/sensors` | Sensor integration details | Phase 3 — sensor data test steps |
| `fv-ish/dma` | DMA architecture details | Phase 3 — DMA test steps |
| `fv-ish/power` | Power management details | Phase 3 — PM test steps |
| `fv-ish/debug` | Known issues, sightings | Phase 3 — HW errors in pass/fail criteria |
| `doc-study` | Multi-document extraction | Phase 3 — always for document ingestion |
| `codesign` | Co-De Sign API for live HAS queries | Phase 3 — live HAS access |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `fv-ish/tcd` | **TCD (Test Case Description) creation** — parent records of TCs. Use when you need to create the strategic test description that this TC implements. |

## Sub-Agent Delegation

| Task | Agent | When |
|------|-------|------|
| Heavy document extraction | `DOC-STUDY` | Large documents (>50 pages) |
| Codebase exploration | `explore` | Finding existing test patterns in repo |
| General research | `general` | Multi-step research across sources |

---

# INTERACTION PATTERNS

## Pattern 1: Create TC from Parent TCD

```
User: "Create a TC for D0i1 entry from TCD #15019042073"

Agent workflow:
1. Load skills: fv-ish/tc, hsdes
2. Ask: What tenant for TCs? (or use session default)
3. Phase 1: Fetch parent TCD #15019042073 from HSDES
4. Phase 1: Check for existing TCs under this TCD
5. Phase 2: Load MANDATORY TC template
6. Phase 3: Extract parent TCD content + additional sources
7. Phase 4: Generate TC file with all 11 sections filled, linked to parent TCD
8. Phase 5: Add source attribution (parent TCD + other sources)
9. Present to user for review
```

## Pattern 2: Create Multiple TCs from Parent TCD

```
User: "Generate all TCs needed for TCD #15019042073 (NVU PM)"

Agent workflow:
1. Load skills: fv-ish/tc, hsdes, doc-study
2. Phase 1: Fetch parent TCD to understand full scope
3. Phase 1: Check for existing TCs to avoid duplication
4. Phase 2: Load MANDATORY TC template
5. Phase 3: Analyze parent TCD Algorithm of Testing to identify distinct TC scenarios
6. Phase 4: Present generation plan (list of N TCs), get user confirmation
7. Phase 4: Generate batch TC files (each following MANDATORY template, each linked to parent TCD)
8. Phase 5: Add source attribution to each
```

## Pattern 3: Amend Existing TC to Template

```
User: "Bring HSDES TC #15019140578 into compliance with our template"

Agent workflow:
1. Load skills: fv-ish/tc, hsdes
2. Phase 1: Fetch TC #15019140578 from HSDES
3. Phase 1: Fetch its parent TCD for context
4. Phase 2: Load MANDATORY TC template
5. Phase 2: Generate template-compliant version
6. Phase 2: Show diff with [ADDED]/[MODIFIED]/[REFORMATTED] markers
7. Phase 2: WAIT for user confirmation
8. Phase 4: Save amended version as local file
9. Phase 5: Add source attribution (original HSDES + parent TCD + template)
```

## Pattern 4: Create TCs from Document + Parent TCD

```
User: "Here's the NVU HAS. Generate TCs for the D0i2 power state from TCD #22022171836"

Agent workflow:
1. Load skills: fv-ish/tc, doc-study, hsdes
2. Phase 1: Fetch parent TCD #22022171836
3. Phase 1: Check for existing TCs
4. Phase 2: Load MANDATORY TC template
5. Phase 3: Delegate doc-study to extract D0i2 content from HAS
6. Phase 3: Cross-reference parent TCD scope with HAS details
7. Phase 4: Present generation plan, get user confirmation
8. Phase 4: Generate TC files (each following MANDATORY template)
9. Phase 5: Add source attribution (parent TCD + HAS + other sources)
```

---

# GUARDRAILS

## Must-Follow Rules

1. **MANDATORY TEMPLATE** — Every TC output MUST follow `templates/tc_template.md` (or user-provided replacement)
2. **NEVER write to HSDES** — output is local files only
3. **NEVER amend existing TCs without user confirmation** — always show diff first
4. **NEVER omit the Sources section** — every TC must have source attribution
5. **NEVER omit parent TCD reference** — every TC must link to its parent TCD
6. **NEVER fabricate test steps, register values, or expected results** — use `[TODO]` if info unavailable
7. **NEVER generate without a plan** — for batch (>1 TC), present plan and get confirmation
8. **ALWAYS apply the MANDATORY template** — user-provided replaces default but must be used consistently
9. **ALWAYS cross-reference HSDES** — check for existing coverage before generating new TCs
10. **ALWAYS mark unverified content** — `[TODO]` or `[UNVERIFIED]` tags
11. **Tenant is configurable** — never assume a tenant, ask or use user's specified default
12. **This skill is TC-only** — for TCD (Test Case Description) creation, redirect to `fv-ish/tcd`

## Quality Checks Before Output

Before saving any TC file, verify:

- [ ] MANDATORY template structure followed (all 11 sections present)
- [ ] Identification header complete, including parent TCD reference
- [ ] Test steps are detailed, numbered, and executable by another engineer
- [ ] Pass/fail criteria are measurable and observable (specific register values, status flags)
- [ ] Intent Verify maps back to HAS/spec requirements
- [ ] Validation SW section lists all required tools with versions
- [ ] Ecosystem SW section lists OS/driver/FW/BIOS requirements
- [ ] Test HW Requirements section lists platform, BOM, equipment
- [ ] Sources & References section is present, populated, and includes parent TCD
- [ ] No fabricated values — register addresses, bit fields, protocol values
- [ ] `[TODO]` markers for any unverified or missing content
- [ ] File naming follows convention

---

# TOOLS

## `tools/hsdes_query.py`

HSDES query script for reading existing TC and parent TCD records. Tenant is always user-configurable.

```bash
# List known tenants
python tools/hsdes_query.py --list-tenants

# Fetch TC by ID (auto-detects tenant)
python tools/hsdes_query.py --id <HSDES_ID>

# Fetch TC by ID from explicit tenant
python tools/hsdes_query.py --id <HSDES_ID> --tenant sighting_central.test_case

# Fetch parent TCD
python tools/hsdes_query.py --id <PARENT_TCD_ID> --tenant sighting_central.test_case_definition

# Discover all fields for a record
python tools/hsdes_query.py --id <HSDES_ID> --discover-fields

# EQL search for TCs (requires tenant)
python tools/hsdes_query.py --tenant sighting_central.test_case \
  --eql "title LIKE '%keyword%'"

# Search TCs by parent TCD
python tools/hsdes_query.py --tenant sighting_central.test_case \
  --eql "parent_id = '<PARENT_TCD_ID>'"
```

## `tools/md_to_docx.py`

Markdown-to-Word converter for TC output files.

```bash
# Convert a single TC markdown file to Word
python tools/md_to_docx.py tcd_output/TC_feature_20260407.md C:/Users/pgsvlab/Downloads/TC_feature_20260407.docx
```

Features:
- Intel blue color scheme (headers: `#1F4E79`)
- Table formatting with blue header rows
- Calibri font, narrow margins
- Supports markdown tables, headings, lists, blockquotes, code blocks
