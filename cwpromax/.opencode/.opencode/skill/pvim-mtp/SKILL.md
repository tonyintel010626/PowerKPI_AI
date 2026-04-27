---
name: pvim-mtp
description: >-
  HSDES PVIM Master Test Plan (MTP) hierarchy traversal — recursive parent-child
  tree walking, test plan structure export, and status aggregation via HSDES REST API.
  Reusable across all FV IP domains.
license: MIT
---

# PVIM-MTP: HSDES Master Test Plan Hierarchy Skill

> **Owner**: Chin, William Willy (`willychi`)
> **Version**: 1.2
> **Created**: 2026-03-29
> **Applicable To**: All FV IP domains — any HSDES PVIM Master Test Plan

## Purpose

Navigate, extract, and analyze HSDES PVIM Master Test Plan (MTP) hierarchies
using the HSDES REST API. Provides recursive parent-child tree traversal that
is **not available** in `pysvtools.hsdes` or any other existing skill.

### Why This Skill Exists

| Existing Tool | What It Does | What It CANNOT Do |
|--------------|-------------|-------------------|
| `pysvtools.hsdes` | EQL search, article field queries | Parent-child hierarchy traversal |
| `hsdes` skill | Wraps pysvtools for sighting/test_case search | MTP tree walking |
| `nga/pvimintegration` | NGA↔HSDES mapping, test cycle queries | HSDES article relationship navigation |
| **This skill** | **Recursive MTP hierarchy traversal** | — |

### Key Discovery

The HSDES REST API endpoint `/rest/article/{id}/links` returns parent-child
relationships — this is the **only working method** for hierarchy traversal.
The `/rest/article/{id}/children` endpoint returns 503 (broken/unsupported).

## CRITICAL SAFETY RULES

> **🚨 MANDATORY — ALL agents and scripts MUST follow these rules.**

1. **NEVER create ANY HSDES articles automatically.** This includes:
   - **TR** (Test Result)
   - **TC** (Test Case)
   - **TCD** (Test Case Definition)
   - **TPF** (Test Plan Feature)
   - **TP** (Test Plan)
2. **ALWAYS get explicit user approval** before ANY article creation via the HSDES REST API.
3. **ALWAYS run `--dry-run` first** to show what WOULD be created, then ask the user to confirm.
4. **NEVER pass `--yes` to bypass confirmation** unless the user explicitly instructs you to.
5. **READ-ONLY operations are always safe** — tree walking, export, stats, and spot-checks need no approval.

These rules exist because HSDES articles **cannot be deleted or reverted** via the REST API (PUT/PATCH returns 405). Any accidental creation is permanent.

## Quick Start

```bash
# From command line — export full MTP tree to markdown
python .opencode/skill/pvim-mtp/scripts/hsdes_mtp_tree.py --root <MTP_ROOT_ID> --depth 3

# Export to JSON for programmatic use
python .opencode/skill/pvim-mtp/scripts/hsdes_mtp_tree.py --root <MTP_ROOT_ID> --format json --output mtp.json

# Export summary stats only
python .opencode/skill/pvim-mtp/scripts/hsdes_mtp_tree.py --root <MTP_ROOT_ID> --stats-only

```

```python
# From Python — programmatic usage
from scripts.hsdes_mtp_tree import MTPTreeWalker

walker = MTPTreeWalker()
tree = walker.build_tree(root_id="<MTP_ROOT_ID>", max_depth=3)  # replace with your domain's root ID
walker.print_tree(tree)
stats = walker.get_stats(tree)
print(f"Total: {stats['total']}, Complete: {stats['complete']}, Rejected: {stats['rejected']}")
```

## HSDES REST API Reference

### Endpoint Discovery (Tested 2026-03-29)

| Endpoint | Status | Use Case |
|----------|--------|----------|
| `GET /rest/article/{id}` | ✅ 200 OK | Fetch article details (title, status, owner, fields) |
| `GET /rest/article/{id}/links` | ✅ 200 OK | **Get parent-child relationships** — key discovery |
| `GET /rest/article/{id}/children` | ❌ 503 Error | Broken/unsupported — do NOT use |
| `GET /rest/article/{id}/relationship` | ❌ 404 | Does not exist |
| `GET /rest/article/{id}/hierarchy` | ❌ 404 | Does not exist |

### Authentication

Three access methods tested (2026-03-29):

| Method | Base URL | Auth | Status | Best For |
|--------|----------|------|--------|----------|
| **Browser (Playwright)** | `https://hsdes.intel.com/rest/` | SSO cookies via `credentials: 'include'` | ✅ Works | Interactive use, browser-based agents |
| **Python + Kerberos** | `https://hsdes-api.intel.com/rest/` | `requests_kerberos.HTTPKerberosAuth(mutual_authentication=OPTIONAL)` | ✅ Works | **Recommended** for scripts, CI/CD, batch ops |
| **Python + pysvtools** | `https://hsdes-api.intel.com/rest/` | `pysvtools.hsdes.rest.client.Hsdes()._session` | ❌ 401 on `/links` | Does NOT work for hierarchy traversal |

**Kerberos setup** (the proven method):
```python
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

session = requests.Session()
session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
resp = session.get(f"https://hsdes-api.intel.com/rest/article/{article_id}/links")
```

> **Prerequisite**: `requests_kerberos` must be installed (`pip install requests-kerberos`).
> Already available on Intel lab machines with standard Python toolchain.
> The user must have a valid Kerberos ticket (automatic on domain-joined machines).

### Response Formats

#### Article Details (`GET /rest/article/{id}`)

```json
{
  "data": [{
    "id": 12345678901,
    "title": "MTP_FV_<DOMAIN> [Post-Si]",
    "status": "complete",
    "owner": "idsid",
    "tenant": "sighting_central.test_plan",
    "description": "...",
    "component": "...",
    "release": "...",
    "test_plan.parent_testplan": "..."
  }]
}
```

#### Article Links (`GET /rest/article/{id}/links`)

```json
// Example response (reference: THC domain, root 13013458151)
{
  "responses": [
    {
      "id": 13013458156,
      "title": "[MTP] [THC] HIDI2C Interface Enabling",
      "status": "complete",
      "owner": "willychi",
      "tenant": "sighting_central.test_plan",
      "relationship": "parent-child",
      "subject": "test_plan"
    },
    {
      "id": 13013458151,
      "title": "MTP_FV_THC [Post-Si]",
      "relationship": "child-parent",
      "subject": "test_plan"
    }
  ]
}
```

**Relationship field values:**
- `"parent-child"` → this article is the PARENT, the linked article is the CHILD
- `"child-parent"` → this article is the CHILD, the linked article is the PARENT

### Parallel Fetching Pattern (JavaScript — Browser Context)

For browser-based agents using Playwright, use `page.evaluate()` with `Promise.all`:

```javascript
// Inside playwright_browser_evaluate
async () => {
  // Replace with your domain's TPF IDs from the tree walk
  const ids = [/* TPF_ID_1, TPF_ID_2, ... */];

  const results = await Promise.all(ids.map(async (id) => {
    const resp = await fetch(`https://hsdes.intel.com/rest/article/${id}/links`, {
      credentials: 'include',
      headers: { 'Accept': 'application/json' }
    });
    const json = await resp.json();
    const children = json.responses.filter(r => r.relationship === 'parent-child');
    return { parentId: id, children };
  }));

  return JSON.stringify(results);
}
```

### Parallel Fetching Pattern (Python — Script Context)

For Python scripts, use `concurrent.futures.ThreadPoolExecutor`:

```python
import concurrent.futures
import requests

def get_children(session, article_id):
    resp = session.get(
        f"https://hsdes-api.intel.com/rest/article/{article_id}/links",
        headers={"Accept": "application/json"}
    )
    data = resp.json()
    return [r for r in data.get("responses", []) if r.get("relationship") == "parent-child"]

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(get_children, session, id): id for id in tpf_ids}
    for future in concurrent.futures.as_completed(futures):
        parent_id = futures[future]
        children = future.result()
```

## MTP Hierarchy Structure

HSDES PVIM Master Test Plans follow a consistent 3-4 level hierarchy:

```
Level 0:  MTP  (Master Test Plan)        — HSDES subject: test_plan
            ├── Level 1:  TPF  (Test Plan Feature)   — subject: test_plan
            │     ├── Level 2:  TCD  (Test Case Definition)  — subject: test_case_definition
            │     │     ├── Level 3:  TC  (Test Case)        — subject: test_case
            │     │     └── Level 3:  TC  (Test Case)
            │     └── Level 2:  TCD  (Test Case Definition)
            │           └── Level 3:  TC  (Test Case)
            └── Level 1:  TPF  (Test Plan Feature)
                  └── ...
```

> **Level 4 (TR / Test Result)**: Optional — created under TCs to record execution results.
> Not part of the initial MTP hierarchy; created on-demand via `hsdes_mtp_create_trs.py`.

### Common Test Matrix Patterns

These patterns appear across ALL FV domains:

| Pattern | Description | Example |
|---------|-------------|---------|
| **Port/Instance Duplication** | Same test repeated per HW instance | Sub-TPF → N children (one per port/controller) |
| **Protocol × Instance Matrix** | Every instance × protocol combination | N×M variants (e.g., 2 ports × 2 protocols = 4 TCs) |
| **Concurrency Matrix** | Single + multi-instance configs | Single-instance + all pairwise combos |
| **Speed/Mode Sweep** | Iterate over protocol speeds or modes | Speed tiers, IO width modes, clock configs |

### Status Values

| Status | Meaning |
|--------|---------|
| `open` | Not yet started or in progress |
| `complete` | Fully validated |
| `future` | Planned for future release |
| `rejected` | Descoped / not POR |

## Scripts Reference

### `hsdes_mtp_tree.py` — Recursive MTP Hierarchy Walker

```
Usage:
  python hsdes_mtp_tree.py --root <HSDES_ID> [options]

Required:
  --root ID         Root MTP article HSDES ID

Options:
  --depth N              Max recursion depth (default: 4)
  --format FMT           Output format: tree (default), json, markdown, csv
  --output FILE          Write to file (default: stdout)
  --stats-only           Print summary statistics only
  --parallel N           Max parallel requests (default: 8)
  --include-descriptions Fetch full descriptions for each article
  --include-results      Include Level 4 Test Results (TR) in traversal
  --include-rejected     Include rejected items (excluded by default in stats)
  --base-url URL         HSDES API base URL (default: https://hsdes-api.intel.com/rest)
  --verbose              Show progress during traversal
```

**Examples:**
```bash
# Full tree for any domain (replace with your MTP root ID)
python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --depth 3

# JSON export for programmatic use
python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --format json --output my_mtp.json

# Stats only — quick summary
python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --stats-only

# Include descriptions and test results
python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --include-descriptions --include-results

# Reference example (THC domain): python hsdes_mtp_tree.py --root 13013458151 --depth 3
```

### `hsdes_mtp_export.py` — MTP Export to Multiple Formats

```
Usage:
  python hsdes_mtp_export.py --root <HSDES_ID> [options]

Required:
  --root ID              Root MTP article HSDES ID

Options:
  --depth DEPTH          Max recursion depth (default: 4)
  --format FMT           Output format: markdown, json, csv, report (default: report)
  -o, --output FILE      Output file path
  --base-url URL         HSDES API base URL (default: https://hsdes-api.intel.com/rest)
  --parallel N           Max parallel requests
  --include-results      Include Level 4 Test Results (TR) in export
  -v, --verbose          Show progress during export
```

### `hsdes_mtp_descriptions.py` — MTP Description Extraction

Extracts descriptions for every record in an MTP hierarchy into a single
Markdown document. Uses the canonical `HTMLStripper` from `_html_utils.py`
to convert HSDES HTML descriptions to clean plain text.

```
Usage:
  python hsdes_mtp_descriptions.py [options]

Required:
  --root ID         Root MTP article HSDES ID (no default — each FV domain provides its own)

Options:
  -o, --output FILE Output markdown file path (default: reports/<root_id>_descriptions.md)
  --include-results Include Level 4 Test Results (TR) — excluded by default
  --html            Keep raw HTML descriptions instead of converting to text
```

**Examples:**
```bash
# Extract descriptions for any MTP (root ID required)
python hsdes_mtp_descriptions.py --root <MTP_ROOT_ID> -o descriptions.md

# Include test results (Level 4)
python hsdes_mtp_descriptions.py --root <MTP_ROOT_ID> --include-results

# Keep raw HTML (for debugging HTML conversion)
python hsdes_mtp_descriptions.py --root <MTP_ROOT_ID> --html

# Reference example (THC domain): python hsdes_mtp_descriptions.py --root 13013458151 -o thc_mtp_descriptions.md
```

### `hsdes_mtp_create_trs.py` — Batch Test Result Creator

> **🚨 CREATES HSDES ARTICLES** — requires explicit user approval.
> Always run `--dry-run` first. Has a mandatory interactive confirmation gate.

Creates Test Result (TR) articles under Test Case (TC) leaf nodes in the MTP
hierarchy. Includes a **mandatory confirmation prompt** that cannot be bypassed
programmatically (enforces the Critical Safety Rules above).

```
Usage:
  python hsdes_mtp_create_trs.py [options]

Required:
  --root ID           Root MTP article HSDES ID (no default — each FV domain provides its own)

Options:
  --dry-run              Show what WOULD be created without creating anything
  --cleanup ID [ID ...]  Delete specific previously created TRs by ID
  --skip-existing        Skip TCs that already have TRs
  -o, --output FILE      Save creation results to JSON file
  --base-url URL         HSDES API base URL (default: https://hsdes-api.intel.com/rest)
  -v, --verbose          Show detailed progress
  -y, --yes              Skip confirmation prompt (⚠️ NEVER use in automated scripts — see Safety Rules)
```

**Examples:**
```bash
# ALWAYS dry-run first (root ID required)
python hsdes_mtp_create_trs.py --root <MTP_ROOT_ID> --dry-run

# Create TRs with skip-existing safety
python hsdes_mtp_create_trs.py --root <MTP_ROOT_ID> --skip-existing --output tr_results.json

# Cleanup previously created TRs (also requires confirmation)
python hsdes_mtp_create_trs.py --root <MTP_ROOT_ID> --cleanup --dry-run

# Reference example (THC domain): python hsdes_mtp_create_trs.py --root 13013458151 --dry-run
```

### `_html_utils.py` — Shared HTML-to-Text Conversion Module

Internal utility module providing canonical `HTMLStripper` and `html_to_text()`
implementations. Used by `hsdes_mtp_descriptions.py` and domain-specific QA
scripts to ensure **identical HTML-to-text conversion** across all scripts
(eliminates prior inconsistency where multiple scripts had divergent copies).

```python
# Usage in other scripts
from _html_utils import HTMLStripper, html_to_text

# Convert HTML fragment to plain text
text = html_to_text("<p>Hello &amp; world</p>")
# → "Hello & world"
```

### Domain-Specific QA Scripts

Each FV domain should create **domain-specific QA scripts** adapted to their MTP
structure (expected record counts, hierarchy depth, level distribution). These
scripts live in the owning domain's skill tree (e.g., `.opencode/skill/fv-thc/tools/`),
NOT in `pvim-mtp/`.

> **Reference implementation**: See `FV-THC.md` for the THC domain QA scripts
> (`thc_mtp_verify_descriptions.py`, `thc_mtp_gap_analysis.py`, `thc_mtp_validate_e2e.py`)
> which serve as templates for other domains.

## Cross-References

| Resource | Description |
|----------|-------------|
| `hsdes` skill | EQL search and article queries (complements this skill) |
| `nga/pvimintegration` skill | NGA↔HSDES mapping for test execution tracking |
| `nga/planning` skill | NGA test planning (suites, steps, actions) |
| `sighting-info` skill | Test execution status by product ID |
| **`tcd-tc-writer` skill** | **TCD/TC content authoring — WHAT to write inside each TCD and TC article** |
