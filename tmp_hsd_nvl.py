from pysvtools import hsdes
import json

MEMBERS = ['zphan', 'nhanif', 'nbmohdzaki', 'jleow', 'ratnameh']
fields = 'id,title,owner,submitted_by,updated_by,updated_date,status,description,comments'

for ts in ['nvl.sighting', 'nvl_soc.sighting']:
    try:
        hsdes.config(ts)
        r = hsdes.search("status = 'open'", showFields='id,title,owner,status')
        print(f"Tenant [{ts}]: {len(r)} open sightings - VALID")
        if r:
            print(f"  Sample owner: {r[0].get('owner')}")
        break
    except Exception as e:
        print(f"Tenant [{ts}]: ERROR - {str(e)[:120]}")

# Also try member query directly
for ts in ['nvl.sighting', 'nvl_soc.sighting']:
    try:
        hsdes.config(ts)
        r = hsdes.search(f"owner = 'zphan'", showFields='id,title,owner,status')
        print(f"  [{ts}] owner=zphan: {len(r)}")
    except Exception as e:
        pass
