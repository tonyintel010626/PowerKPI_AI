import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('C:/PowerKPI_AI/hsdes_status.json') as f:
    data = json.load(f)

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']

# Keep only sightings where a PowerKPI member is owner, submitted_by, or updated_by
# AND title contains NVL
def is_member_involved(s):
    for role in ['owner', 'submitted_by', 'updated_by']:
        if s.get(role, '') in MEMBERS:
            return True
    return False

nvl_member = [
    s for s in data
    if is_member_involved(s) and 'NVL' in (s.get('title') or '').upper()
]

nvl_member_sorted = sorted(nvl_member, key=lambda x: x.get('updated_date', ''), reverse=True)

# Group by status
from collections import defaultdict
by_status = defaultdict(list)
for s in nvl_member_sorted:
    by_status[s.get('status', 'unknown')].append(s)

print(f'Total NVL sightings involving PowerKPI members: {len(nvl_member_sorted)}')
print()
for st in ['open', 'root_caused', 'complete', 'rejected']:
    print(f'  {st.upper()}: {len(by_status[st])}')

print()

def print_sighting(s):
    sid      = s.get('id', 'N/A')
    title    = s.get('title', 'N/A')
    status   = s.get('status', 'N/A')
    owner    = s.get('owner', 'N/A') or '(unassigned)'
    upd_by   = s.get('updated_by', 'N/A')
    upd_date = s.get('updated_date', 'N/A')
    sub_by   = s.get('submitted_by', 'N/A')
    comments = s.get('comments') or ''
    desc     = s.get('description') or ''
    raw      = comments if comments else desc
    # Strip HTML tags roughly
    import re
    clean = re.sub(r'<[^>]+>', ' ', raw)
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Take last meaningful comment block (after last ++++ marker)
    blocks = re.split(r'\+\+\+\+\S+\s+\S+', clean)
    summary = blocks[-1].strip() if blocks else clean
    if len(summary) > 350:
        summary = summary[:347] + '...'
    if not summary:
        summary = '(no summary available)'

    print(f'  ID          : {sid}')
    print(f'  Title       : {title}')
    print(f'  Status      : {status}')
    print(f'  Owner       : {owner}')
    print(f'  Submitted By: {sub_by}')
    print(f'  Updated By  : {upd_by}')
    print(f'  Updated Date: {upd_date}')
    print(f'  Latest Note : {summary}')
    print()

for st_label, st_key in [('OPEN', 'open'), ('ROOT CAUSED', 'root_caused'), ('COMPLETE', 'complete'), ('REJECTED', 'rejected')]:
    items = by_status[st_key]
    if not items:
        continue
    print('=' * 100)
    print(f'  [{st_label}] — {len(items)} sighting(s)')
    print('=' * 100)
    for s in items:
        print_sighting(s)
