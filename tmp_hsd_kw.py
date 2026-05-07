from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

fields = 'id,title,owner,submitted_by,updated_by,updated_date,status,description'

# Search by PowerKPI-related keywords in title
queries = [
    "title contains 'power kpi'",
    "title contains 'PowerKPI'",
    "title contains 'IDON'",
    "title contains 'CMS' AND title contains 'power'",
    "title contains 'connected modern standby'",
    "title contains 'S0ix' AND status = 'open'",
    "title contains 'PC10' AND status = 'open'",
    "title contains 'VNNAON'",
    "title contains 'Novalake' AND title contains 'power'",
    "title contains 'NVL' AND title contains 'power'",
]

all_results = {}
for q in queries:
    try:
        r = hsdes.search(q, showFields=fields)
        print(f"Query [{q[:60]}]: {len(r)} results")
        for item in r:
            sid = item.get('id')
            if sid not in all_results:
                all_results[sid] = item
    except Exception as e:
        print(f"Query [{q[:60]}]: ERROR {e}")

print(f"\nTotal unique sightings: {len(all_results)}")
print(f"\n{'='*100}")
print(f"{'ID':<18} {'Title':<50} {'Status':<12} {'Owner':<15}")
print(f"{'='*100}")
for s in sorted(all_results.values(), key=lambda x: x.get('updated_date',''), reverse=True):
    print(f"{s.get('id',''):<18} {str(s.get('title',''))[:48]:<50} {s.get('status',''):<12} {s.get('owner',''):<15}")
