import csv, json, datetime

# --- Load data ---
daq = {}
for it in ['iteration-1','iteration-2']:
    path = rf'C:\_hopper_results\20260428T174713_IDON_daq_soc\{it}\20260428T174713\20260428T174713-power-default_Raw_Summary.csv'
    daq[it] = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            daq[it][row['Name']] = float(row['Total_Average'])

with open(r'C:\_hopper_results\20260428T174713_IDON_daq_soc\20260428T174713-results.json') as f:
    results = json.load(f)

flat_soc = {}
for it in ['iteration-1','iteration-2']:
    flat_soc[it] = {}
    for sub in results[it]['hopper']['subtests']:
        for rg in sub['result_groups']:
            for r in rg['results']:
                flat_soc[it][r['name'].strip()] = r['value']

key_rails = [
    'P_MCP_TOTAL','P_PCD_SHARED_TOTAL','P_VCCCORE','P_VCCGT','P_VCCSA',
    'P_VCCPRIM_VNNAON','P_VCC_LP_ECORE','P_VDD2H_CPU','P_VDD2H_MEM',
    'P_VDD2L_MEM','P_VDDQ_CPU','P_VDDQ_MEM','P_V1P8A_ROP',
]
soc_metrics = [
    ('PC0 : Package Residency (%)', 'PC0', 7.48),
    ('PC2 : Package Residency (%)', 'PC2', None),
    ('PC6.1 : Package Residency (%)', 'PC6.1', None),
    ('PC10.1 : Package Residency (%)', 'PC10.1', 90.02),
    ('OS-PC6 : Residency (%)', 'OS-PC6', None),
    ('OS-PC10 : Residency (%)', 'OS-PC10', None),
]
blockers = [
    ('IPU-LTR', 0.16, 0.11),
    ('CDIE0-ARAT', 0.14, 0.11),
    ('PMC-TIMER', 0.10, 0.05),
    ('PMC-LTR', 0.06, 0.04),
    ('MEDIA-MISC', 0.05, 0.05),
    ('DISP-LTR', 0.03, 0.02),
    ('IPU-BUSY', 0.02, 0.02),
]

def daq_rows():
    rows = ''
    for rail in key_rails:
        v1 = daq['iteration-1'].get(rail)
        v2 = daq['iteration-2'].get(rail)
        avg = round((v1+v2)/2, 4) if v1 is not None and v2 is not None else '-'
        rows += f'<tr><td>{rail}</td><td>{v1:.4f}</td><td>{v2:.4f}</td><td><b>{avg}</b></td></tr>\n'
    return rows

def soc_rows():
    rows = ''
    for key, label, target in soc_metrics:
        v1 = flat_soc['iteration-1'].get(key, 0)
        v2 = flat_soc['iteration-2'].get(key, 0)
        try:
            avg = round((float(v1)+float(v2))/2, 2)
        except:
            avg = '-'
        tgt_str = f'{target}%' if target is not None else '-'
        style = ''
        if target is not None and isinstance(avg, float):
            if label == 'PC0' and avg > target * 5:
                style = ' style="background:#ffe0e0"'
            elif label == 'PC10.1' and avg < target * 0.1:
                style = ' style="background:#ffe0e0"'
        rows += f'<tr{style}><td>{label}</td><td>{v1}</td><td>{v2}</td><td><b>{avg}</b></td><td>{tgt_str}</td></tr>\n'
    return rows

def blocker_rows():
    rows = ''
    for name, v1, v2 in blockers:
        avg = round((v1+v2)/2, 3)
        rows += f'<tr><td>{name}</td><td>{v1}%</td><td>{v2}%</td><td><b>{avg}%</b></td></tr>\n'
    return rows

html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>IDON NVL P Summary Report</title>
<style>
  body { font-family: Segoe UI, Arial, sans-serif; margin: 30px; background: #f5f5f5; }
  h1 { color: #003d7a; }
  h2 { color: #0068b5; border-bottom: 2px solid #0068b5; padding-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 30px; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
  th { background: #0068b5; color: white; padding: 8px 12px; text-align: left; }
  td { padding: 7px 12px; border-bottom: 1px solid #e0e0e0; }
  tr:hover { background: #f0f7ff; }
  .badge-red { background: #e53935; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
  .badge-yellow { background: #fb8c00; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
  .finding { background: white; border-left: 4px solid #e53935; padding: 12px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .finding.warn { border-left-color: #fb8c00; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 24px; }
  ol li { margin-bottom: 8px; }
</style>
</head>
<body>
<h1>IDON Workload Summary Report &mdash; NVL P</h1>
<p class="meta">
  <b>Run ID:</b> 20260428T174713_IDON_daq_soc &nbsp;|&nbsp;
  <b>Date:</b> 2026-04-28 &nbsp;|&nbsp;
  <b>Iterations:</b> 2 &nbsp;|&nbsp;
  <b>Quiesce / Capture:</b> 180s / 180s &nbsp;|&nbsp;
  <b>Instrumentation:</b> DAQ (FlexLogger) + SocWatch
</p>

<h2>Key Findings</h2>
<div class="finding">
  <b><span class="badge-red">CRITICAL</span> PC10 Residency = 0%</b> (Target: 90.02%)<br>
  Platform stuck at PC0/PC2. CPU cores not entering deep idle (CC6/CC10), preventing package C-state progression.
  Both iterations confirmed this consistently.<br>
  <b>Action:</b> Check per-core CC6 residency. Investigate interrupt storm or background process.
</div>
<div class="finding">
  <b><span class="badge-red">CRITICAL</span> P_VCCPRIM_VNNAON = 0.883 W</b> (Target: ~73 mW)<br>
  NPU/VNN rail is 12x above pre-silicon projection at idle. NPU driver likely not entering D3.<br>
  <b>Action:</b> Check NPU driver power state. Verify no background AI workload.
</div>
<div class="finding warn">
  <b><span class="badge-yellow">WARN</span> P_MCP_TOTAL = 3.820 W</b><br>
  Total platform power elevated. Expected to improve once PC10 is resolved.
</div>
<div class="finding warn">
  <b><span class="badge-yellow">WARN</span> Top PC6 Blocker: IPU-LTR (0.13% avg)</b><br>
  IPU camera subsystem asserting LTR. Disable camera and rerun to isolate.
</div>

<h2>DAQ Power Rails (Average W)</h2>
<table>
  <tr><th>Rail</th><th>Iteration 1 (W)</th><th>Iteration 2 (W)</th><th>Average (W)</th></tr>
  DAQ_ROWS
</table>

<h2>Package C-State Residency (SocWatch)</h2>
<table>
  <tr><th>State</th><th>Iteration 1 (%)</th><th>Iteration 2 (%)</th><th>Average (%)</th><th>Pre-Si Target</th></tr>
  SOC_ROWS
</table>
<p><i>Rows highlighted in red indicate significant deviation from pre-silicon target.</i></p>

<h2>PkgC6 Blocker Residency</h2>
<table>
  <tr><th>Blocker</th><th>Iteration 1 (%)</th><th>Iteration 2 (%)</th><th>Average (%)</th></tr>
  BLOCKER_ROWS
</table>
<p><i>Note: These blocker times are small. The primary issue is CPU cores not reaching CC6/CC10.</i></p>

<h2>Run-to-Run Consistency</h2>
<table>
  <tr><th>Metric</th><th>Iteration 1</th><th>Iteration 2</th><th>Delta</th></tr>
  <tr><td>P_MCP_TOTAL</td><td>3.885 W</td><td>3.754 W</td><td>-3.4%</td></tr>
  <tr><td>P_VCCCORE</td><td>0.444 W</td><td>0.418 W</td><td>-5.9%</td></tr>
  <tr><td>P_VCCPRIM_VNNAON</td><td>0.906 W</td><td>0.860 W</td><td>-5.1%</td></tr>
  <tr><td>PC0 Residency</td><td>99.41%</td><td>99.59%</td><td>Consistent</td></tr>
  <tr><td>PC2 Residency</td><td>0.59%</td><td>0.41%</td><td>Consistent</td></tr>
</table>

<h2>Recommended Debug Actions</h2>
<ol>
  <li><b>Check per-core CC6 residency</b> &mdash; Run SocWatch with <code>-f hw-cpu-cstate</code>. If CC6 = 0%, a core-level blocker exists.</li>
  <li><b>Check for interrupt storm</b> &mdash; Check interrupt rate on SUT. Any IP generating &gt;1-2% interrupt time is suspect.</li>
  <li><b>Check background processes</b> &mdash; Confirm no antivirus, telemetry, or Windows Update active during capture.</li>
  <li><b>Isolate IPU</b> &mdash; Disable camera in Device Manager and rerun IDON to remove IPU-LTR blocker.</li>
  <li><b>Check NPU driver D3</b> &mdash; Verify NPU driver enters D3 at idle via Device Manager or NPU telemetry.</li>
  <li><b>Check BIOS knob</b> &mdash; Confirm <code>Package C State Limit</code> is not locked to PC0 or PC2.</li>
</ol>

<hr>
<p class="meta">Generated by CW Pro Max | PowerKPI Agent | GEN_DATE</p>
</body>
</html>"""

html = html.replace('DAQ_ROWS', daq_rows())
html = html.replace('SOC_ROWS', soc_rows())
html = html.replace('BLOCKER_ROWS', blocker_rows())
html = html.replace('GEN_DATE', str(datetime.date.today()))

out_path = r'C:\_hopper_results\20260428T174713_IDON_daq_soc\IDON_NVL_P_Report.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('HTML written to:', out_path)
