from pysvtools import hsdes
import json

# Probe all likely tenant candidates for NVL platform
candidates = [
    'server_platf.sighting',
    'server_soc.sighting',
    'client_plat.sighting',
    'client_soc.sighting',
    'lnl_soc.sighting',
    'lnl.sighting',
    'mtl.sighting',
    'mtl_soc.sighting',
    'ptl.sighting',
    'ptl_soc.sighting',
    'arl.sighting',
    'arl_soc.sighting',
]

for ts in candidates:
    try:
        hsdes.config(ts)
        # Just try to get 1 record - if no error, tenant is valid
        r = hsdes.search("status = 'open'", showFields='id,owner')
        print(f"[VALID ] {ts}: {len(r)} open records")
    except Exception as e:
        err = str(e)
        if 'does not exist' in err:
            print(f"[BADTS ] {ts}: tenant schema invalid")
        elif 'error' in err.lower():
            print(f"[ERR   ] {ts}: {err[:80]}")
        else:
            print(f"[UNKNWN] {ts}: {err[:80]}")
