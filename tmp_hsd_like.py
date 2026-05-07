from pysvtools import hsdes
import json

# Check what EQL operators are valid - test with known working data
hsdes.config('heia_soc.sighting')

# Try LIKE / CONTAINS syntax variants
tests = [
    "title LIKE '%S0ix%'",
    "title LIKE '%power%'",
    "title LIKE '%PC10%'",
    "title LIKE '%CMS%'",
]
for q in tests:
    try:
        r = hsdes.search(q, showFields='id,title,owner,status')
        print(f"[{q}]: {len(r)} results")
        for item in r[:2]:
            print(f"  {item.get('id')} | {item.get('title','')[:60]}")
    except Exception as e:
        print(f"[{q}]: ERROR {e}")
