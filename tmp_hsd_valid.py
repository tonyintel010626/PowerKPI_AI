from pysvtools import hsdes
import json

hsdes.config('heia_soc.sighting')

# Try different field names for owner/description
test_fields_list = [
    'id,title,owner,status,updated_date,submitted_by,updated_by,description,comments',
    'id,title,owner,status,updated_date',
    'id,title,status',
]

for tf in test_fields_list:
    try:
        data = hsdes.search_id('220641371', showFields=tf)
        print(f"Fields [{tf[:50]}]: OK")
        print(json.dumps(data[0] if data else {}, indent=2))
        break
    except AssertionError as e:
        bad = str(e).replace("Unknown field '","").replace("'","")
        print(f"Fields [{tf[:50]}]: FAILED - unknown field: {bad}")
        # Remove bad field and retry
        tf = ','.join([f for f in tf.split(',') if f.strip() != bad])

# Now do a keyword search using = operator on title (exact won't work, try partial via EQL)
# Try 'title contains' which we know works for the open status query
r = hsdes.search("status = 'open' AND owner = 'sdbui'", showFields='id,title,owner,status,updated_date')
print(f"\nowner=sdbui open: {len(r)}")

# Check what fields the API actually accepts by trying one at a time
candidate_fields = ['owner','submitted_by','updated_by','description','comments','updated_date',
                    'priority','days_open','family','release_affected','val_teams','forum','sub_forum']
valid_fields = []
for f in candidate_fields:
    try:
        hsdes.search_id('220641371', showFields=f'id,{f}')
        valid_fields.append(f)
    except AssertionError:
        pass
print(f"\nValid fields: {valid_fields}")
