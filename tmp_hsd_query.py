from pysvtools import hsdes
import json

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
    print(f"Querying for member: {member} ...")
    try:
        results = hsdes.search(query, showFields=fields)
        print(f"  -> Found {len(results)} records")
        all_sightings.extend(results)
    except Exception as e:
        print(f"  -> ERROR: {e}")

# Deduplicate by ID
seen_ids = set()
unique_sightings = []
for s in all_sightings:
    sid = s.get('id')
    if sid and sid not in seen_ids:
        seen_ids.add(sid)
        unique_sightings.append(s)

print(f"\nTotal unique sightings found: {len(unique_sightings)}")

# Sort by updated_date descending
sorted_sightings = sorted(
    unique_sightings,
    key=lambda x: x.get('updated_date', ''),
    reverse=True
)

print(f"\n{'='*95}")
print(f"{'ID':<18} {'Title':<40} {'Status':<12} {'Updated Date':<22} {'Owner':<15}")
print(f"{'='*95}")

for s in sorted_sightings:
    sid        = s.get('id', 'N/A')
    title      = (s.get('title') or 'N/A')[:38]
    status     = s.get('status', 'N/A')
    updated_on = s.get('updated_date', 'N/A')
    owner      = s.get('owner', 'N/A')
    print(f"{sid:<18} {title:<40} {status:<12} {updated_on:<22} {owner:<15}")

print(f"{'='*95}\n")

print("=== Progress Summaries ===\n")
for s in sorted_sightings:
    summary_text = (s.get('comments') or s.get('description') or 'No summary available.')
    if len(summary_text) > 400:
        summary_text = summary_text[:397] + '...'
    print(f"[{s.get('id')}] {s.get('title')}")
    print(f"  Status      : {s.get('status', 'N/A')}")
    print(f"  Owner       : {s.get('owner', 'N/A')}")
    print(f"  Updated By  : {s.get('updated_by', 'N/A')}")
    print(f"  Updated Date: {s.get('updated_date', 'N/A')}")
    print(f"  Progress    : {summary_text}")
    print()
