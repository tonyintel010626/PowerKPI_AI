import json
from collections import defaultdict

with open('C:/PowerKPI_AI/hsdes_status.json') as f:
    data = json.load(f)

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']

by_member = defaultdict(lambda: defaultdict(int))
status_counts = defaultdict(int)

for s in data:
    status = s.get('status', 'unknown')
    status_counts[status] += 1
    for role in ['owner', 'submitted_by', 'updated_by']:
        m = s.get(role, '')
        if m in MEMBERS:
            by_member[m][status] += 1

print('=== OVERALL STATUS BREAKDOWN ===')
for st, cnt in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f'  {st:<25} {cnt}')

print()
print('=== PER MEMBER STATUS ===')
for member in MEMBERS:
    total = sum(by_member[member].values())
    print(f'  {member} (total involved: {total}):')
    for st, cnt in sorted(by_member[member].items(), key=lambda x: -x[1]):
        print(f'    {st:<25} {cnt}')

print()
print('=== TOP 20 RECENTLY UPDATED ===')
hdr = f"{'ID':<18} {'Status':<15} {'Updated':<22} {'By':<15} {'Title'}"
print(hdr)
print('-' * 100)
for s in data[:20]:
    sid     = s.get('id', 'N/A')
    status  = s.get('status', 'N/A')
    upd     = s.get('updated_date', 'N/A')
    upd_by  = s.get('updated_by', 'N/A')
    title   = (s.get('title') or 'N/A')[:44]
    print(f'{sid:<18} {status:<15} {upd:<22} {upd_by:<15} {title}')
