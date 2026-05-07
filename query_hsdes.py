from pysvtools import hsdes
import json

hsdes.config('sighting_central.sighting')

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']
FIELDS = 'id,title,owner,submitted_by,updated_by,updated_date,status,comments,description'

all_sightings = []
for member in MEMBERS:
    for field in ['owner', 'submitted_by', 'updated_by']:
        try:
            query = f"{field} = '{member}'"
            results = hsdes.search(query, showFields=FIELDS)
            if results:
                all_sightings.extend(results)
                print(f'[OK] {field}={member}: {len(results)} results')
            else:
                print(f'[OK] {field}={member}: 0 results')
        except Exception as e:
            print(f'[ERR] {field}={member}: {e}')

seen_ids = set()
unique = []
for s in all_sightings:
    sid = s.get('id')
    if sid and sid not in seen_ids:
        seen_ids.add(sid)
        unique.append(s)

print(f'\nTotal unique sightings: {len(unique)}')

sorted_s = sorted(unique, key=lambda x: x.get('updated_date',''), reverse=True)
with open('C:/PowerKPI_AI/hsdes_status.json','w') as f:
    json.dump(sorted_s, f, indent=2)
print('Saved to C:/PowerKPI_AI/hsdes_status.json')
