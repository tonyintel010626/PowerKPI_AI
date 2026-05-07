from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')
results = hsdes.search("owner = 'zphan'", showFields='id,title,owner,status,updated_date')
print(f'Results for zphan: {len(results)}')
if results:
    print(json.dumps(results[:2], indent=2))
