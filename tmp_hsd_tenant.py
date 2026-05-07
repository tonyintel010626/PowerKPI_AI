from pysvtools import hsdes
import json

# Check what family/release values exist to narrow the tenant
# Also try to find the correct tenant for NVL/Novalake sightings

# Try different tenants
tenants_to_try = [
    'client_soc.sighting',
    'client.sighting',
    'server_platf.sighting',
]

for ts in tenants_to_try:
    try:
        hsdes.config(ts)
        r = hsdes.search("status = 'open'", showFields='id,title,owner,status')
        print(f"Tenant [{ts}]: {len(r)} open sightings")
    except Exception as e:
        print(f"Tenant [{ts}]: ERROR - {e}")

# Also try heia_soc with family filter for NVL
hsdes.config('heia_soc.sighting')
for fam in ['NVL', 'Novalake', 'Nova Lake', 'MTL', 'LNL']:
    try:
        r = hsdes.search(f"family = '{fam}'", showFields='id,title,owner,status,family')
        print(f"heia_soc family={fam}: {len(r)}")
    except Exception as e:
        print(f"heia_soc family={fam}: ERROR {e}")
