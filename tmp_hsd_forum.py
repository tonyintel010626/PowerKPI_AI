from pysvtools import hsdes
import json

# Discover correct EQL operators from a working record
# Use the known sighting 220641371 to understand field values
hsdes.config('heia_soc.sighting')

data = hsdes.search_id('220641371', showFields='id,title,owner,status,forum,sub_forum,project_release,family,release_affected')
print(json.dumps(data[0] if data else {}, indent=2))

# Also check valid EQL operators by querying with forum filter
r = hsdes.search("forum = 'power'", showFields='id,title,owner,status,forum')
print(f"\nforum=power: {len(r)}")
r2 = hsdes.search("forum = 'Power'", showFields='id,title,owner,status,forum')
print(f"forum=Power: {len(r2)}")
