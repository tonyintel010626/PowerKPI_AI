from pysvtools import hsdes
import json

# sdbui found 1 open sighting in heia_soc - let's use that as a reference
# to understand what family values exist in this tenant
hsdes.config('heia_soc.sighting')

r = hsdes.search("status = 'open'", showFields='id,title,owner,status,family,release_affected,updated_date')
print(f"Total open sightings: {len(r)}")

# Show unique family values
families = set()
releases = set()
owners = set()
for item in r:
    if item.get('family'):
        families.add(item.get('family'))
    if item.get('release_affected'):
        releases.add(item.get('release_affected'))
    if item.get('owner'):
        owners.add(item.get('owner'))

print(f"\nUnique families ({len(families)}): {sorted(families)[:20]}")
print(f"\nUnique releases ({len(releases)}): {sorted(releases)[:20]}")
print(f"\nSample owners: {sorted(list(owners))[:30]}")
