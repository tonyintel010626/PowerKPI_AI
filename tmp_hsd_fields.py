from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

# List valid fields for this tenant
try:
    fields_info = hsdes.get_fields()
    print("Available fields:")
    for f in sorted(fields_info):
        print(f"  {f}")
except Exception as e:
    print(f"get_fields error: {e}")

# Try minimal fields
data = hsdes.search_id('220641371', showFields='id,title,owner,status,forum')
print(json.dumps(data[0] if data else {}, indent=2))
