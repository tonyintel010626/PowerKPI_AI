from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

# Try broader search - no filter, just check connectivity and field structure
results = hsdes.search("submitted_by = 'zphan'", showFields='id,title,owner,status,updated_date,submitted_by')
print(f'submitted_by zphan: {len(results)}')

results2 = hsdes.search("updated_by = 'zphan'", showFields='id,title,owner,status,updated_date,updated_by')
print(f'updated_by zphan: {len(results2)}')

# Try nhanif
results3 = hsdes.search("owner = 'nhanif'", showFields='id,title,owner,status,updated_date')
print(f'owner nhanif: {len(results3)}')

results4 = hsdes.search("submitted_by = 'nhanif'", showFields='id,title,owner,status,updated_date')
print(f'submitted_by nhanif: {len(results4)}')
