from pysvtools import hsdes
import json

hsd_id = '15019278744'
ts = hsdes.config_by_id(hsd_id)
print(f"Detected tenant: {ts}")
hsdes.config(ts)
data = hsdes.search_id(hsd_id)
print(json.dumps(data[0] if data else {}, indent=2))
