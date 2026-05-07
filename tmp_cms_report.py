import json

def get_power_rails(path):
    d = json.load(open(path))
    rails = {}
    for k, v in d.get('power', {}).items():
        if k.startswith('P_') and 'default' in v:
            try:
                mean = float(str(v['default'].get('mean', 0)).split()[0])
                mn   = float(str(v['default'].get('min',  0)).split()[0])
                mx   = float(str(v['default'].get('max',  0)).split()[0])
            except:
                mean = mn = mx = 0.0
            rails[k] = {'mean': mean, 'min': mn, 'max': mx}
    return rails

r1 = get_power_rails(r'C:\_hopper_results\20260429T093619_CMS_daq\20260429T093619-results.json')
r2 = get_power_rails(r'C:\_hopper_results\20260429T094653_CMS_daq\20260429T094653-results.json')

print("{:<35} {:>12} {:>12} {:>8}".format("Rail", "Run1 (mW)", "Run2 (mW)", "Delta%"))
print("-" * 70)
key_rails = ['P_MCP_TOTAL','P_PCD_SHARED_TOTAL','P_VCCPRIM_VNNAON','P_VCCPRIM_IO',
             'P_VDD2H_MEM','P_VDD1_MEM','P_VDD2H_CPU']
for r in key_rails:
    v1 = r1.get(r, {}).get('mean', 0) * 1000
    v2 = r2.get(r, {}).get('mean', 0) * 1000
    delta = ((v2 - v1) / v1 * 100) if v1 else 0
    print("{:<35} {:>12.2f} {:>12.2f} {:>7.1f}%".format(r, v1, v2, delta))

print("\nAll Power rails (mW):")
for k in sorted(r1.keys()):
    v1 = r1[k]['mean'] * 1000
    v2 = r2.get(k, {}).get('mean', 0) * 1000
    print("  {:<35} Run1={:8.2f}  Run2={:8.2f}".format(k, v1, v2))
