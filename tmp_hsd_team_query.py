import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pysvtools import hsdes
import json
import re

hsdes.config('sighting_central.sighting')

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']
fields = 'id,title,owner,submitted_by,updated_by,updated_date,status,comments'

all_sightings = {}

for member in MEMBERS:
    for field in ['owner', 'submitted_by', 'updated_by']:
        query = f"{field} = '{member}'"
        try:
            results = hsdes.search(query, showFields=fields)
            for s in results:
                sid = s.get('id')
                if sid and sid not in all_sightings:
                    all_sightings[sid] = s
        except Exception as e:
            print(f"ERROR [{field}={member}]: {e}")

unique = sorted(all_sightings.values(), key=lambda x: x.get('updated_date', ''), reverse=True)
print(f"Total unique sightings: {len(unique)}\n")

def clean(text):
    if not text:
        return 'N/A'
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\u200b','').replace('\xa0',' ').replace('\u2019',"'")
    return text.strip()

print(f"{'='*110}")
print(f"{'ID':<18} {'Title':<50} {'Status':<14} {'Updated Date':<22} {'Owner':<12}")
print(f"{'='*110}")
for s in unique:
    title = clean(s.get('title',''))[:48]
    print(f"{s.get('id',''):<18} {title:<50} {s.get('status',''):<14} {s.get('updated_date',''):<22} {s.get('owner',''):<12}")
print(f"{'='*110}\n")

print("=== Progress Summaries ===\n")
for s in unique:
    raw = s.get('comments') or 'No summary available.'
    summary = clean(raw)
    if len(summary) > 500:
        summary = summary[:497] + '...'
    title = clean(s.get('title',''))
    print(f"[{s.get('id')}] {title}")
    print(f"  Status      : {s.get('status', 'N/A')}")
    print(f"  Owner       : {s.get('owner', 'N/A')}")
    print(f"  Updated By  : {s.get('updated_by', 'N/A')}")
    print(f"  Updated Date: {s.get('updated_date', 'N/A')}")
    print(f"  Progress    : {summary}")
    print()
