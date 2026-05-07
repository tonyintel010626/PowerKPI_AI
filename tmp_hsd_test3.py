from pysvtools import hsdes
import json

# Try test_case tenant to confirm connectivity
hsdes.config('heia_soc.test_case')
results = hsdes.search("owner = 'zphan'", showFields='id,title,owner,status')
print(f'test_case owner zphan: {len(results)}')

# Try sighting with a known open query
hsdes.config('heia_soc.sighting')
results2 = hsdes.search("status = 'open'", showFields='id,title,owner,status,updated_date')
print(f'open sightings (any): {len(results2)}')
if results2:
    print(json.dumps(results2[:2], indent=2))
