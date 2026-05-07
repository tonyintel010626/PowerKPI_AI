import json
import sys
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('C:/PowerKPI_AI/hsdes_status.json') as f:
    data = json.load(f)

# Filter NVL sightings only
nvl = [s for s in data if 'NVL' in (s.get('title') or '').upper() or 'NVL' in (s.get('description') or '').upper()]

print(f'Total NVL sightings: {len(nvl)}')

# Sort by updated_date desc
nvl_sorted = sorted(nvl, key=lambda x: x.get('updated_date',''), reverse=True)

print()
print('=== NVL SIGHTINGS DETAIL ===')
print()
for s in nvl_sorted:
    sid      = s.get('id','N/A')
    title    = s.get('title','N/A')
    status   = s.get('status','N/A')
    owner    = s.get('owner','N/A')
    upd_by   = s.get('updated_by','N/A')
    upd_date = s.get('updated_date','N/A')
    comments = s.get('comments') or ''
    desc     = s.get('description') or ''
    summary  = comments if comments else desc
    if len(summary) > 400:
        summary = summary[:397] + '...'
    print(f'ID          : {sid}')
    print(f'Title       : {title}')
    print(f'Status      : {status}')
    print(f'Owner       : {owner}')
    print(f'Updated By  : {upd_by}')
    print(f'Updated Date: {upd_date}')
    print(f'Summary     : {summary}')
    print('-' * 100)
