from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

# Get all fields from that record
data = hsdes.search_id('220641371')
print(json.dumps(data[0] if data else {}, indent=2))
