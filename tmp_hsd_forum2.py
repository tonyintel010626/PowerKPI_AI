from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

data = hsdes.search_id('220641371', showFields='id,title,owner,status,forum,project_release,family,release_affected')
print(json.dumps(data[0] if data else {}, indent=2))

# Try forum-based search  
r = hsdes.search("forum = 'power'", showFields='id,title,owner,status,forum,updated_date')
print(f"\nforum=power: {len(r)}")
for item in r[:3]:
    print(f"  {item.get('id')} | {item.get('title','')[:60]} | {item.get('status')}")
