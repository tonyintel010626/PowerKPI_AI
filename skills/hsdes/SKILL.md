---
name: hsdes
description: HSDES query skill for searching across multiple tenants (test_case, sighting, bug, etc.)
license: MIT
---

# HSDES Query Skill

This skill provides the ability to query HSDES (High Speed Design Entry System) across multiple tenants. HSDES is Intel's centralized database for tracking sightings, test cases, bugs, and other validation artifacts.

## Quick Start

```python
from pysvtools import hsdes
import json

# Query by ID (auto-detects tenant from the record)
YOUR_HSD_ID = '15018601544'
ts = hsdes.config_by_id(YOUR_HSD_ID)
hsdes.config(ts)
data = hsdes.search_id(YOUR_HSD_ID)
print(json.dumps(data[0] if data else {}, indent=2))
```

---

## Understanding Tenants

HSDES organizes data into **tenants (ts)** - different record types with their own schemas and fields. You must configure the correct tenant before querying.

### Common Tenants

| Tenant | Description | Example Use Case |
|--------|-------------|------------------|
| `heia_soc.test_case` | Test case definitions | Query test case details, owners, validation teams |
| `heia_soc.test_result` | Test execution results | Get test pass/fail status, execution logs |
| `heia_soc.sighting` | Sightings/issues found | Track validation issues, root cause analysis |
| `heia_soc.bug` | Bug tracking | Software/hardware bug records |
| `heia_soc.feature` | Feature tracking | Feature specifications and status |

> **Note**: There are many other tenants available. The tenant format is typically `<namespace>.<record_type>`.

---

## Configuration Methods

### Method 1: Auto-detect tenant from ID

```python
from pysvtools import hsdes

YOUR_HSD_ID = '15018601544'
ts = hsdes.config_by_id(YOUR_HSD_ID)  # Auto-detects tenant from record
hsdes.config(ts)
```

### Method 2: Explicit tenant configuration

```python
from pysvtools import hsdes

# Configure for test_case tenant
hsdes.config('heia_soc.test_case')

# Or for sighting tenant
hsdes.config('heia_soc.sighting')

# Or for test_result tenant
hsdes.config('heia_soc.test_result')
```

---

## Query Operations

### Search by ID

```python
from pysvtools import hsdes
import json

YOUR_HSD_ID = '15018601544'
ts = hsdes.config_by_id(YOUR_HSD_ID)
hsdes.config(ts)

# Basic search
data = hsdes.search_id(YOUR_HSD_ID)
print(json.dumps(data[0] if data else {}, indent=2))
```

### Search by ID with Specific Fields

```python
from pysvtools import hsdes
import json

YOUR_HSD_ID = '15018601544'
ts = hsdes.config_by_id(YOUR_HSD_ID)
hsdes.config(ts)

# Request specific fields (comma-separated)
fields = ','.join([
    'subject',
    'forum',
    'id',
    'title',
    'owner',
    'priority',
    'days_open',
    'comments',
    'description',
    'submitted_by',
    'updated_date',
    'updated_by',
    'updated_reason',
    'status',
    'reason',
    'status_reason',
    'test_case.val_teams',
    'test_result.val_teams',
    'family',
    'release_affected',
    'family_affected',
    'submitted_date',
    'closed_date'
])

data = hsdes.search_id(YOUR_HSD_ID, showFields=fields)
print(json.dumps(data[0] if data else {}, indent=2))
```

### Search with EQL Query

```python
from pysvtools import hsdes
import json

# Configure tenant first
hsdes.config('heia_soc.test_case')

# Search using EQL (Entity Query Language)
query = "owner = 'username' AND status = 'open'"
data = hsdes.search(query, showFields='id,title,status,owner')
print(json.dumps(data, indent=2))
```

---

## Common Fields by Tenant

### Common Fields (Available across most tenants)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Record title |
| `owner` | Current owner |
| `status` | Current status |
| `forum` | Forum category (e.g., 'silicon_different', 'validation') |
| `sub_forum` | Sub-forum category (more specific classification) |
| `project_release` | Project release version |
| `subject` | Subject classification |
| `description` | Detailed description |
| `submitted_by` | Original submitter |
| `submitted_date` | Submission date |
| `updated_by` | Last updater |
| `updated_date` | Last update time |

### Test Case Fields (`heia_soc.test_case`)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Test case title |
| `owner` | Current owner |
| `status` | Current status |
| `forum` | Forum category |
| `sub_forum` | Sub-forum category |
| `project_release` | Associated project release |
| `test_case.val_teams` | Validation teams |
| `description` | Test description |
| `priority` | Priority level |

### Sighting Fields (`heia_soc.sighting`)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Sighting title |
| `owner` | Current owner |
| `status` | Current status (open/closed) |
| `forum` | Forum category |
| `sub_forum` | Sub-forum category |
| `project_release` | Associated project release |
| `family_affected` | Affected product family |
| `release_affected` | Affected release |
| `root_cause` | Root cause analysis — **may not exist in all sighting schemas; test with `search_id()` first** |
| `submitted_by` | Original submitter |
| `submitted_date` | Submission date |

### Test Result Fields (`heia_soc.test_result`)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Result title |
| `status` | Pass/Fail/Blocked |
| `forum` | Forum category |
| `sub_forum` | Sub-forum category |
| `project_release` | Associated project release |
| `test_result.val_teams` | Validation teams |
| `updated_date` | Last update time |

---

## PTL Product IDs Reference

For PTL (Product Test Line) queries, use these product IDs:

| Product | ID |
|---------|-----|
| PTL 12Xe | `15018623948` |
| PTL 4Xe | `15018623981` |
| PTL U | `15018623982` |

> **Note**: PTL is equivalent to PTL-PCD for this skill.

---

## Advanced Query Examples

### Query by Project Release with Different Forum/Sub-Forum

This example finds all records with the same `project_release` but groups them by different `forum` and `sub_forum` combinations:

```python
from pysvtools import hsdes
import json
from collections import defaultdict

# Configure for your tenant
hsdes.config('heia_soc.sighting')  # or 'heia_soc.test_case', etc.

# Define the project release to search
PROJECT_RELEASE = 'PTL-2024.1'  # Replace with your actual project release

# EQL query to find all records with the same project_release
query = f"project_release = '{PROJECT_RELEASE}'"

# Request key fields including forum and sub_forum
fields = ','.join([
    'id',
    'title',
    'project_release',
    'forum',
    'sub_forum',
    'owner',
    'status'
])

data = hsdes.search(query, showFields=fields)

# Group results by forum/sub_forum combination
grouped = defaultdict(list)
for record in data:
    key = (record.get('forum', 'N/A'), record.get('sub_forum', 'N/A'))
    grouped[key].append(record)

# Display different forum/sub_forum combinations
print(f"Project Release: {PROJECT_RELEASE}")
print(f"Found {len(grouped)} different forum/sub_forum combinations:\n")

for (forum, sub_forum), records in grouped.items():
    print(f"Forum: {forum} | Sub-Forum: {sub_forum} | Count: {len(records)}")
    for r in records[:3]:  # Show first 3 records per combination
        print(f"  - [{r.get('id')}] {r.get('title')}")
    print()
```

### Compare Forum/Sub-Forum Distribution Across Project Releases

```python
from pysvtools import hsdes
import json
from collections import defaultdict

hsdes.config('heia_soc.sighting')

# Query multiple project releases
releases = ['PTL-2024.1', 'PTL-2024.2']

for release in releases:
    query = f"project_release = '{release}'"
    fields = 'id,forum,sub_forum,project_release'
    data = hsdes.search(query, showFields=fields)
    
    # Count by forum/sub_forum
    counts = defaultdict(int)
    for record in data:
        key = f"{record.get('forum', 'N/A')}/{record.get('sub_forum', 'N/A')}"
        counts[key] += 1
    
    print(f"\n=== {release} ===")
    for combo, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {combo}: {count}")
```

---

## Complete Example

```python
from pysvtools import hsdes
import json

def query_hsdes_record(hsd_id, fields=None):
    """
    Query an HSDES record by ID.
    
    Args:
        hsd_id: The HSDES record ID
        fields: Optional comma-separated field list
    
    Returns:
        dict: The record data or empty dict if not found
    """
    ts = hsdes.config_by_id(hsd_id)
    hsdes.config(ts)
    
    if fields:
        data = hsdes.search_id(hsd_id, showFields=fields)
    else:
        data = hsdes.search_id(hsd_id)
    
    return data[0] if data else {}

# Usage
record = query_hsdes_record('15018601544')
print(f"Title: {record.get('title')}")
print(f"Status: {record.get('status')}")
print(f"Owner: {record.get('owner')}")
```

---

## Error Handling

```python
from pysvtools import hsdes
import json

try:
    YOUR_HSD_ID = '15018601544'
    ts = hsdes.config_by_id(YOUR_HSD_ID)
    hsdes.config(ts)
    data = hsdes.search_id(YOUR_HSD_ID)
    
    if data:
        print(json.dumps(data[0], indent=2))
    else:
        print(f"No record found for ID: {YOUR_HSD_ID}")
        
except Exception as e:
    print(f"HSDES query failed: {e}")
```

---

## Known Limitations

### Field Availability Varies by Tenant

Not all fields listed in this document are available in every tenant or schema version.
Fields that have been observed to **fail or return empty** in the `heia_soc.sighting` tenant:
- `root_cause` — Does not exist in many sighting schemas
- `exposure` — Not a standard sighting field
- `attachments` — Not queryable via `search_id()`
- `how_found`, `how_to_reproduce`, `steps_to_reproduce` — Not standard sighting fields
- `test_result.platform` — Not a valid cross-tenant field

**Recommendation:** When querying an unfamiliar tenant, first call `search_id()` with no `showFields` to see what fields are actually returned, then narrow down.

### EQL Syntax Limitations

The EQL query language has several undocumented restrictions:
- The `~` operator (regex/like) is **not supported** — use `=` for exact match
- The `contains` keyword is **not supported** for text search
- Wildcard syntax `*text*` does **not work** in string comparisons
- For partial text matching, use supported operators only (check HSDES API docs for current syntax)

### search() Parameter Restrictions

- `hsdes.search()` does **not** accept a `maxRows` parameter. Results are returned with a default limit. If you need to paginate, use the HSDES REST API directly.

### Debugging Tips

- Always test with a known ID first using `search_id()` before building complex EQL queries
- If a field query fails silently (returns empty), the field likely doesn't exist in that tenant
- Use `config_by_id()` to auto-detect the correct tenant rather than guessing

---

## Requirements

- `pysvtools.hsdes >= 0.0.0`

---

## Related Skills

- `sighting-info` - Specialized sighting queries
- `nga/failure` - NGA failure tracking integration

---

## HSD Updates

This section is for the **swimlane lead** to oversee and track updates across all relevant HSD sightings for the PowerKPI team.

### PowerKPI Team Members

| Username |
|----------|
| zphan |
| nhanif |
| nbmohdzaki |
| jleow |
| ratnameh |

---

### Sightings Update Workflow

When a **sightings update** is requested, retrieve all sightings where any of the PowerKPI team members appear as `owner`, `updated_by`, or `submitted_by`.

#### Step 1 — Query Sightings for All Members

```python
from pysvtools import hsdes
import json
from mcp_co_design import codesign  # codesign skill for data sorting

hsdes.config('heia_soc.sighting')

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']

fields = ','.join([
    'id',
    'title',
    'owner',
    'submitted_by',
    'updated_by',
    'updated_date',
    'status',
    'description',
    'comments'
])

all_sightings = []

for member in MEMBERS:
    query = (
        f"owner = '{member}' OR "
        f"updated_by = '{member}' OR "
        f"submitted_by = '{member}'"
    )
    results = hsdes.search(query, showFields=fields)
    all_sightings.extend(results)

# Deduplicate by ID
seen_ids = set()
unique_sightings = []
for s in all_sightings:
    sid = s.get('id')
    if sid and sid not in seen_ids:
        seen_ids.add(sid)
        unique_sightings.append(s)

print(f"Total unique sightings found: {len(unique_sightings)}")
print(json.dumps(unique_sightings, indent=2))
```

#### Step 2 — Sort and Summarize with Codesign Skill

After retrieving the raw sightings, use the **codesign skill** to sort and organize the data:

```python
# Use codesign skill to sort sightings by latest updated_date (most recent first)
# and generate a progress summary for each record

# Sort by updated_date descending
sorted_sightings = sorted(
    unique_sightings,
    key=lambda x: x.get('updated_date', ''),
    reverse=True
)

# Display formatted summary table
print(f"\n{'='*90}")
print(f"{'ID':<18} {'Title':<35} {'Updated Date':<22} {'Updated By':<15}")
print(f"{'='*90}")

for s in sorted_sightings:
    sid        = s.get('id', 'N/A')
    title      = (s.get('title') or 'N/A')[:33]
    updated_on = s.get('updated_date', 'N/A')
    updated_by = s.get('updated_by', 'N/A')
    print(f"{sid:<18} {title:<35} {updated_on:<22} {updated_by:<15}")

print(f"{'='*90}\n")

# Per-record progress summary
print("=== Progress Summaries ===\n")
for s in sorted_sightings:
    summary_text = (s.get('comments') or s.get('description') or 'No summary available.')
    # Truncate long summaries for readability
    if len(summary_text) > 300:
        summary_text = summary_text[:297] + '...'
    print(f"[{s.get('id')}] {s.get('title')}")
    print(f"  Status      : {s.get('status', 'N/A')}")
    print(f"  Owner       : {s.get('owner', 'N/A')}")
    print(f"  Updated By  : {s.get('updated_by', 'N/A')}")
    print(f"  Updated Date: {s.get('updated_date', 'N/A')}")
    print(f"  Progress    : {summary_text}")
    print()
```

---

### Output Data Fields

Each sighting reported in the update must include the following:

| Field | Description |
|-------|-------------|
| `id` | HSD sighting ID |
| `title` (Issue Name) | Short name/title of the sighting |
| `updated_date` | Latest update date |
| `updated_by` | Username who last updated the record |
| Progress Summary | Extracted from `comments` or `description` — summarized current status |

---

### Notes

- Results are deduplicated — a sighting owned **and** updated by the same member appears only once.
- Sort order is **latest updated first** to surface the most active sightings.
- Use the codesign skill (`mcp_co-design`) for any further data grouping, filtering, or export if needed.
- If `comments` field is unavailable in a tenant, fall back to `description` for the progress summary.
