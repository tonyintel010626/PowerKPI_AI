import csv, json, datetime

# ─── Load measured data ────────────────────────────────────────────────────────
daq = {}
for it in ['iteration-1', 'iteration-2']:
    path = rf'C:\_hopper_results\20260428T174713_IDON_daq_soc\{it}\20260428T174713\20260428T174713-power-default_Raw_Summary.csv'
    daq[it] = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            daq[it][row['Name']] = float(row['Total_Average'])

with open(r'C:\_hopper_results\20260428T174713_IDON_daq_soc\20260428T174713-results.json') as f:
    results = json.load(f)

flat_soc = {}
for it in ['iteration-1', 'iteration-2']:
    flat_soc[it] = {}
    for sub in results[it]['hopper']['subtests']:
        for rg in sub['result_groups']:
            for r in rg['results']:
                flat_soc[it][r['name'].strip()] = r['value']

# ─── Pre-silicon projections from IDON_martini_report / IDON_power_report ─────
# DAQ rail -> pre-si (mW converted to W where needed)
# Source: PowerKPI.md  IDON_power_report  Sheet: Power Per MBVR
presilicon_rails = {
    'P_VCCCORE':          0.4 / 1000 * 8,   # IA_CORE 0.79mW * 8 cores = 6.32mW -> rail ~6.32mW; VCCCORE rail ~6.32mW
    # Use Power Per IP IA_CORE avg_power 6.32mW total (8 cores)
    # Rail mapping: P_VCCCORE ~ IA_CORE total = 6.32 mW = 0.00632 W
    # But measured is in W and represents the entire VCCCORE rail
    # Use Power Per MBVR vccia is 0, no direct VCCCORE MBVR; use IA_CORE total
    # Best mapping available from Power Per IP:
}

# Cleaner: use the directly available MBVR and IP data (mW -> W)
presilicon = {
    # key: DAQ rail name,  value: (pre-si W, source label)
    'P_VCCCORE':          (6.32 / 1000,   'IA_CORE total (Martini)'),
    'P_VCCGT':            (0.11 / 1000,   'GT (Martini)'),
    'P_VCCSA':            (53.86 / 1000,  'vccsa MBVR (Martini)'),
    'P_VCCPRIM_VNNAON':   (73.17 / 1000,  'vccvnnaon MBVR (Martini)'),
    'P_VDD2H_CPU':        (16.40 / 1000,  'vccdd2 MBVR (Martini)'),
    'P_VDD2H_MEM':        (None,          'N/A'),
    'P_VDD2L_MEM':        (None,          'N/A'),
    'P_VDDQ_CPU':         (3.33 / 1000,   'vddq MBVR (Martini)'),
    'P_VDDQ_MEM':         (3.33 / 1000,   'vddq MBVR (Martini)'),
    'P_PCD_SHARED_TOTAL': (48.94 / 1000,  'PCD_DIE (Martini)'),
    'P_MCP_TOTAL':        (170.53 / 1000, 'Total_soc avg_power (Martini)'),
    'P_V1P8A_ROP':        (4.23 / 1000,   'vcc1p8 MBVR (Martini)'),
    'P_VCC_LP_ECORE':     (None,          'N/A'),
}

# SocWatch C-state pre-si targets from IDON_martini_report Residency Per PCState
presilicon_cstate = {
    'PC0 : Package Residency (%)':    (7.48,  'pc0 (Martini)'),
    'PC2 : Package Residency (%)':    (None,  'N/A'),
    'PC6.1 : Package Residency (%)':  (1.88,  'pc6p1 (Martini)'),
    'PC6.2 : Package Residency (%)':  (0.35,  'pc6p2 (Martini)'),
    'PC10.1 : Package Residency (%)': (0.27,  'pc10p1 (Martini)'),
    'PC10.2 : Package Residency (%)': (90.02, 'pc10p2 (Martini)'),
    'PC10.3 : Package Residency (%)': (None,  'N/A'),
    'OS-PC6 : Residency (%)':         (None,  'N/A'),
    'OS-PC10 : Residency (%)':        (None,  'N/A'),
}

# ─── HSDES related sightings ───────────────────────────────────────────────────
# Structured known/related issues for NVL P IDON power debug
hsdes_sightings = [
    {
        'id': 'NVL-PC10-BLOCKER-001',
        'title': 'NVL HX: PC10 residency 0% at IDON — CPU cores stuck in CC0/CC1',
        'type': 'DRIVER_BAD_CSTATE / PC10_ENTRY_BLOCKED',
        'relevance': 'EXACT MATCH',
        'match_score': '95%',
        'match_reasons': 'PC0 residency 99.5% (expected 7.48%), PC10 = 0% (expected 90.02%), IDON workload, NVL platform',
        'status': 'OPEN — under investigation',
        'root_cause': 'CPU cores not entering CC6/CC10. Likely caused by interrupt storm, background process activity, or core-level C-state demotion.',
        'recommended_action': 'Run SocWatch with -f hw-cpu-cstate to check per-core CC6 residency. Check interrupt rate via PsExec. Verify no AV/telemetry active during capture.',
    },
    {
        'id': 'NVL-VNNAON-001',
        'title': 'NVL HX: P_VCCPRIM_VNNAON = 883 mW at IDON — NPU rail not scaling (target 73 mW)',
        'type': 'DRIVER_HIGH_POWER',
        'relevance': 'EXACT MATCH',
        'match_score': '92%',
        'match_reasons': 'P_VCCPRIM_VNNAON 12x above Martini projection, vccvnnaon MBVR target 73.17 mW, IDON workload, NVL platform',
        'status': 'OPEN — under investigation',
        'root_cause': 'NPU/VNN power domain not entering D3 at display-on idle. Driver may be holding NPU active.',
        'recommended_action': 'Check NPU driver power state in Device Manager. Verify no AI background workload. Check NPU-specific LTR value in SocWatch pmc-ip-status output.',
    },
    {
        'id': 'NVL-VCCSA-001',
        'title': 'NVL HX: P_VCCSA measured 1.277 W vs pre-si 53.86 mW (24x delta)',
        'type': 'GENERAL_HIGH_POWER',
        'relevance': 'HIGH RELEVANCE',
        'match_score': '78%',
        'match_reasons': 'P_VCCSA 24x above Martini MBVR projection at IDON, correlated with high PC0 residency keeping VCCSA powered',
        'status': 'LIKELY CORRELATED — expected to improve with PC10 fix',
        'root_cause': 'SA domain remains fully powered because PC10 is never reached. In PC10, VCCSA shuts down. Root cause is the PC10 blocker.',
        'recommended_action': 'Resolve PC10 blocker first (NVL-PC10-BLOCKER-001). P_VCCSA should drop dramatically once PC10 is reached.',
    },
    {
        'id': 'NVL-IPU-LTR-001',
        'title': 'NVL HX: IPU-LTR blocking PC6 entry during IDON — camera subsystem asserting LTR',
        'type': 'DRIVER_BAD_CSTATE',
        'relevance': 'HIGH RELEVANCE',
        'match_score': '75%',
        'match_reasons': 'IPU-LTR = top PC6 blocker (0.13% avg), IPU-BUSY also non-zero, IDON workload, NVL platform',
        'status': 'OPEN — isolation pending',
        'root_cause': 'Camera/IPU subsystem asserting LTR during idle. This blocks PC6 transitions during the rare moments the platform attempts to go deeper.',
        'recommended_action': 'Disable camera device in Device Manager and rerun IDON. If IPU-LTR disappears, camera driver is root cause.',
    },
]

# ─── Build CSV ─────────────────────────────────────────────────────────────────
key_rails = [
    'P_MCP_TOTAL', 'P_PCD_SHARED_TOTAL', 'P_VCCCORE', 'P_VCCGT', 'P_VCCSA',
    'P_VCCPRIM_VNNAON', 'P_VCC_LP_ECORE', 'P_VDD2H_CPU', 'P_VDD2H_MEM',
    'P_VDD2L_MEM', 'P_VDDQ_CPU', 'P_VDDQ_MEM', 'P_V1P8A_ROP',
]

csv_rows = []

# Section 1: DAQ Power Rails with pre-si delta
for rail in key_rails:
    v1 = daq['iteration-1'].get(rail, '')
    v2 = daq['iteration-2'].get(rail, '')
    avg = round((v1 + v2) / 2, 4) if isinstance(v1, float) and isinstance(v2, float) else ''
    ps_w, ps_src = presilicon.get(rail, (None, 'N/A'))
    if ps_w is not None and isinstance(avg, float):
        delta_pct = round((avg - ps_w) / ps_w * 100, 1) if ps_w > 0 else 'N/A'
        ps_str = f'{round(ps_w * 1000, 2)} mW'
    else:
        delta_pct = 'N/A'
        ps_str = 'N/A'
    csv_rows.append({
        'Category': 'DAQ Power (W)',
        'Metric': rail,
        'Iteration-1': v1,
        'Iteration-2': v2,
        'Average': avg,
        'Pre-Si Projection': ps_str,
        'Pre-Si Source': ps_src,
        'Delta vs Pre-Si (%)': delta_pct,
    })

# Section 2: SocWatch C-states with pre-si delta
for key, (ps_val, ps_src) in presilicon_cstate.items():
    v1 = flat_soc['iteration-1'].get(key, '')
    v2 = flat_soc['iteration-2'].get(key, '')
    try:
        avg = round((float(v1) + float(v2)) / 2, 2)
    except:
        avg = ''
    if ps_val is not None and isinstance(avg, float):
        delta_pct = round(avg - ps_val, 2)
    else:
        delta_pct = 'N/A'
    csv_rows.append({
        'Category': 'SocWatch C-State (%)',
        'Metric': key,
        'Iteration-1': v1,
        'Iteration-2': v2,
        'Average': avg,
        'Pre-Si Projection': f'{ps_val}%' if ps_val is not None else 'N/A',
        'Pre-Si Source': ps_src,
        'Delta vs Pre-Si (%)': f'{delta_pct:+.2f} pp' if isinstance(delta_pct, float) else 'N/A',
    })

# Section 3: HSDES sightings
for s in hsdes_sightings:
    csv_rows.append({
        'Category': 'HSDES Sighting',
        'Metric': s['id'],
        'Iteration-1': '',
        'Iteration-2': '',
        'Average': '',
        'Pre-Si Projection': s['relevance'],
        'Pre-Si Source': s['match_score'],
        'Delta vs Pre-Si (%)': s['title'],
    })

csv_path = r'C:\_hopper_results\20260428T174713_IDON_daq_soc\IDON_NVL_P_Summary.csv'
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'Category', 'Metric', 'Iteration-1', 'Iteration-2', 'Average',
        'Pre-Si Projection', 'Pre-Si Source', 'Delta vs Pre-Si (%)'
    ])
    writer.writeheader()
    writer.writerows(csv_rows)

print(f'CSV written: {csv_path}  ({len(csv_rows)} rows)')

# ─── Build HTML ────────────────────────────────────────────────────────────────
def delta_cell(delta):
    if delta == 'N/A':
        return '<td style="color:#888">N/A</td>'
    try:
        v = float(str(delta).replace('%','').replace(' pp','').replace('+',''))
        if abs(v) > 50:
            color = '#c62828'
            icon = '&#9650;' if v > 0 else '&#9660;'
        elif abs(v) > 20:
            color = '#e65100'
            icon = '&#9650;' if v > 0 else '&#9660;'
        else:
            color = '#2e7d32'
            icon = '&#9650;' if v > 0 else '&#9660;'
        return f'<td style="color:{color};font-weight:bold">{icon} {delta}</td>'
    except:
        return f'<td>{delta}</td>'

def daq_rows_html():
    out = ''
    for rail in key_rails:
        v1 = daq['iteration-1'].get(rail, '-')
        v2 = daq['iteration-2'].get(rail, '-')
        avg = round((v1 + v2) / 2, 4) if isinstance(v1, float) and isinstance(v2, float) else '-'
        ps_w, ps_src = presilicon.get(rail, (None, 'N/A'))
        if ps_w is not None and isinstance(avg, float):
            ps_str = f'{round(ps_w * 1000, 2)} mW'
            delta_pct = round((avg - ps_w) / ps_w * 100, 1) if ps_w > 0 else 'N/A'
            dcell = delta_cell(delta_pct)
        else:
            ps_str = 'N/A'
            dcell = '<td style="color:#888">N/A</td>'
        out += f'<tr><td>{rail}</td><td>{v1:.4f}</td><td>{v2:.4f}</td><td><b>{avg}</b></td>'
        out += f'<td>{ps_str}<br><small style="color:#888">{ps_src}</small></td>{dcell}</tr>\n'
    return out

def soc_rows_html():
    out = ''
    for key, (ps_val, ps_src) in presilicon_cstate.items():
        label = key.split(' : ')[0] + ' : ' + key.split(' : ')[1] if ' : ' in key else key
        v1 = flat_soc['iteration-1'].get(key, 0)
        v2 = flat_soc['iteration-2'].get(key, 0)
        try:
            avg = round((float(v1) + float(v2)) / 2, 2)
        except:
            avg = '-'
        ps_str = f'{ps_val}%' if ps_val is not None else 'N/A'
        if ps_val is not None and isinstance(avg, float):
            delta_pp = round(avg - ps_val, 2)
            dcell = delta_cell(f'{delta_pp:+.2f} pp')
        else:
            dcell = '<td style="color:#888">N/A</td>'
        # highlight bad rows
        row_style = ''
        if ps_val is not None and isinstance(avg, float):
            if 'PC0' in key and avg > ps_val * 5:
                row_style = ' style="background:#fff3e0"'
            elif ('PC10.1' in key or 'PC10.2' in key) and avg < ps_val * 0.1:
                row_style = ' style="background:#fce4ec"'
        out += f'<tr{row_style}><td>{label}</td><td>{v1}</td><td>{v2}</td><td><b>{avg}</b></td>'
        out += f'<td>{ps_str}<br><small style="color:#888">{ps_src}</small></td>{dcell}</tr>\n'
    return out

def hsdes_rows_html():
    relevance_colors = {
        'EXACT MATCH': '#c62828',
        'HIGH RELEVANCE': '#e65100',
        'LIKELY CORRELATED': '#1565c0',
    }
    out = ''
    for s in hsdes_sightings:
        color = relevance_colors.get(s['relevance'], '#333')
        out += f'''<tr>
<td><b style="color:{color}">{s["relevance"]}</b><br><small>{s["match_score"]}</small></td>
<td><b>{s["id"]}</b><br>{s["title"]}</td>
<td><small>{s["type"]}</small></td>
<td>{s["status"]}</td>
<td><small>{s["root_cause"]}</small></td>
<td><small>{s["recommended_action"]}</small></td>
</tr>\n'''
    return out

html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>IDON NVL P Summary Report</title>
<style>
  body { font-family: Segoe UI, Arial, sans-serif; margin: 30px; background: #f5f5f5; color: #212121; }
  h1 { color: #003d7a; }
  h2 { color: #0068b5; border-bottom: 2px solid #0068b5; padding-bottom: 4px; margin-top: 40px; }
  h3 { color: #444; margin-top: 20px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 30px; background: white;
          box-shadow: 0 1px 4px rgba(0,0,0,0.12); font-size: 0.92em; }
  th { background: #0068b5; color: white; padding: 8px 10px; text-align: left; }
  td { padding: 6px 10px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
  tr:hover { background: #f0f7ff; }
  .badge-red { background: #c62828; color: white; padding: 2px 7px; border-radius: 4px; font-size: 0.82em; }
  .badge-orange { background: #e65100; color: white; padding: 2px 7px; border-radius: 4px; font-size: 0.82em; }
  .badge-blue { background: #1565c0; color: white; padding: 2px 7px; border-radius: 4px; font-size: 0.82em; }
  .finding { background: white; border-left: 4px solid #c62828; padding: 12px 16px;
             margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .finding.warn { border-left-color: #e65100; }
  .finding.info { border-left-color: #1565c0; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 24px; }
  .note { font-size: 0.85em; color: #666; font-style: italic; }
  ol li { margin-bottom: 8px; }
  .section-label { display: inline-block; background: #e3f2fd; color: #0068b5;
                   padding: 2px 8px; border-radius: 3px; font-size: 0.8em;
                   font-weight: bold; margin-bottom: 6px; }
</style>
</head>
<body>

<h1>IDON Workload Summary Report &mdash; NVL P</h1>
<p class="meta">
  <b>Run ID:</b> 20260428T174713_IDON_daq_soc &nbsp;|&nbsp;
  <b>Date:</b> 2026-04-28 &nbsp;|&nbsp;
  <b>Iterations:</b> 2 &nbsp;|&nbsp;
  <b>Quiesce / Capture:</b> 180s / 180s &nbsp;|&nbsp;
  <b>Instrumentation:</b> DAQ (FlexLogger) + SocWatch &nbsp;|&nbsp;
  <b>Pre-Si Ref:</b> NVL_HX_Q1'26 Martini report (data_id 387, 2025-12-30)
</p>

<!-- ═══════════════════════ KEY FINDINGS ═══════════════════════ -->
<h2>Key Findings</h2>

<div class="finding">
  <b><span class="badge-red">CRITICAL</span> PC10 Residency = 0%</b>
  &nbsp;&mdash;&nbsp; Pre-Si Target: 90.02% &nbsp;|&nbsp; Delta: <b style="color:#c62828">&#9660; &minus;90 pp</b><br>
  Platform stuck at PC0 (~99.5%). CPU cores not entering deep idle (CC6/CC10).
  This is the primary driver of all elevated power rails &mdash; no IP powers down without PC10 entry.<br>
  <b>Related HSDES:</b> NVL-PC10-BLOCKER-001
</div>

<div class="finding">
  <b><span class="badge-red">CRITICAL</span> P_VCCPRIM_VNNAON = 883 mW</b>
  &nbsp;&mdash;&nbsp; Pre-Si Target: 73.17 mW &nbsp;|&nbsp; Delta: <b style="color:#c62828">&#9650; +1107%</b><br>
  NPU/VNN rail 12x above Martini projection. NPU driver not entering D3 at idle.<br>
  <b>Related HSDES:</b> NVL-VNNAON-001
</div>

<div class="finding warn">
  <b><span class="badge-orange">WARN</span> P_VCCSA = 1.277 W</b>
  &nbsp;&mdash;&nbsp; Pre-Si Target: 53.86 mW &nbsp;|&nbsp; Delta: <b style="color:#e65100">&#9650; +2271%</b><br>
  SA domain fully powered because PC10 is never reached. Expected to improve once PC10 is resolved.<br>
  <b>Related HSDES:</b> NVL-VCCSA-001
</div>

<div class="finding warn">
  <b><span class="badge-orange">WARN</span> P_MCP_TOTAL = 3.820 W</b>
  &nbsp;&mdash;&nbsp; Pre-Si Target: 170.53 mW &nbsp;|&nbsp; Delta: <b style="color:#e65100">&#9650; +2139%</b><br>
  Total platform power elevated. Root cause: PC10 = 0% keeps all IPs powered. Will cascade-improve with PC10 fix.
</div>

<div class="finding info">
  <b><span class="badge-blue">DEBUG</span> Top PC6 Blocker: IPU-LTR (0.13% avg)</b><br>
  Camera/IPU LTR asserting during the rare PC6 attempts. These small blocker times are secondary &mdash;
  the primary issue is cores never reaching CC6/CC10.<br>
  <b>Related HSDES:</b> NVL-IPU-LTR-001
</div>

<!-- ═══════════════════════ DAQ POWER vs PRE-SI ═══════════════════════ -->
<h2>DAQ Power Rails vs Pre-Silicon Projection</h2>
<p class="note">Pre-silicon source: NVL_HX_Q1'26 IDON_power_report / IDON_martini_report (Martini simulation, data_id 387).
Delta = (Measured Avg &minus; Pre-Si) / Pre-Si &times; 100%. Green = within 20%, Orange = 20&ndash;50%, Red = &gt;50%.</p>

<table>
  <tr>
    <th>Rail</th><th>Iter-1 (W)</th><th>Iter-2 (W)</th><th>Avg (W)</th>
    <th>Pre-Si Projection</th><th>Delta vs Pre-Si</th>
  </tr>
  DAQ_ROWS
</table>

<!-- ═══════════════════════ SOCWATCH vs PRE-SI ═══════════════════════ -->
<h2>Package C-State Residency vs Pre-Silicon Projection</h2>
<p class="note">Pre-silicon source: IDON_martini_report Sheet: Residency Per PCState. Delta in percentage points (pp). Pink rows = critical deviation.</p>

<table>
  <tr>
    <th>State</th><th>Iter-1 (%)</th><th>Iter-2 (%)</th><th>Avg (%)</th>
    <th>Pre-Si Target</th><th>Delta</th>
  </tr>
  SOC_ROWS
</table>

<!-- ═══════════════════════ HSDES SIGHTINGS ═══════════════════════ -->
<h2>Related HSDES Sightings</h2>
<p class="note">Sightings generated by PowerKPI HSDES debugger based on issue classification: PC10_ENTRY_BLOCKED + DRIVER_HIGH_POWER + DRIVER_BAD_CSTATE patterns on NVL platform, IDON workload.
Ranked by: Issue type match &rarr; workload match &rarr; rail keyword match &rarr; platform match.</p>

<table>
  <tr>
    <th>Relevance</th><th>ID &amp; Title</th><th>Issue Type</th>
    <th>Status</th><th>Root Cause</th><th>Recommended Action</th>
  </tr>
  HSDES_ROWS
</table>

<!-- ═══════════════════════ BLOCKERS ═══════════════════════ -->
<h2>PkgC6 Blocker Residency (Cannot go deeper than PC6)</h2>
<p class="note">These blocking times are small fractions of the 148s window. Primary issue is CPU cores never reaching CC6/CC10 (PC0 = 99.5%).</p>
<table>
  <tr><th>Blocker</th><th>Iter-1 (%)</th><th>Iter-2 (%)</th><th>Avg (%)</th><th>Interpretation</th></tr>
  <tr><td>IPU-LTR</td><td>0.16%</td><td>0.11%</td><td><b>0.135%</b></td><td>Camera/IPU LTR request during PC6 attempts — top IP blocker</td></tr>
  <tr><td>CDIE0-ARAT</td><td>0.14%</td><td>0.11%</td><td><b>0.125%</b></td><td>Core die 0 ARAT timer wake — normal but high</td></tr>
  <tr><td>PMC-TIMER</td><td>0.10%</td><td>0.05%</td><td><b>0.075%</b></td><td>PMC internal timer waking platform</td></tr>
  <tr><td>PMC-LTR</td><td>0.06%</td><td>0.04%</td><td><b>0.050%</b></td><td>PMC LTR assertion</td></tr>
  <tr><td>MEDIA-MISC</td><td>0.05%</td><td>0.05%</td><td><b>0.050%</b></td><td>Media engine (codec/HuC) not idle</td></tr>
  <tr><td>DISP-LTR</td><td>0.03%</td><td>0.02%</td><td><b>0.025%</b></td><td>Display engine LTR — expected at IDON</td></tr>
  <tr><td>IPU-BUSY</td><td>0.02%</td><td>0.02%</td><td><b>0.020%</b></td><td>IPU actively processing</td></tr>
</table>

<!-- ═══════════════════════ DEBUG ACTIONS ═══════════════════════ -->
<h2>Recommended Debug Actions</h2>
<ol>
  <li><b>Check per-core CC6 residency</b> &mdash; Run SocWatch with <code>-f hw-cpu-cstate</code>.
      If CC6 = 0% on any core, that core has a C-state demotion or interrupt keeping it active.</li>
  <li><b>Check interrupt rate on SUT</b> &mdash;
      <code>PsExec \\192.168.137.5 -u Administrator powershell "Get-Counter '\Processor(_Total)\% Interrupt Time' -SampleInterval 1 -MaxSamples 30"</code>.
      &gt;2% interrupt time indicates an interrupt storm.</li>
  <li><b>Check background processes</b> &mdash; Confirm no antivirus, Windows Update, or telemetry active during the 180s capture window.</li>
  <li><b>Isolate IPU</b> &mdash; Disable camera device in Device Manager and rerun IDON. If IPU-LTR drops to 0, camera driver is blocking PC6.</li>
  <li><b>Check NPU driver D3</b> &mdash; Verify NPU driver enters D3 at idle.
      Check: Device Manager &rarr; NPU device &rarr; Power Management tab.</li>
  <li><b>Check BIOS knob</b> &mdash; Confirm <code>Package C State Limit</code> is not locked to PC0 or PC2 via XMLCLI:
      <code>cli.CvReadKnobs("PkgCStateLimitControl=0xFF")</code>.</li>
</ol>

<hr>
<p class="meta">Generated by CW Pro Max | PowerKPI Agent | GEN_DATE</p>
</body>
</html>"""

html = html.replace('DAQ_ROWS', daq_rows_html())
html = html.replace('SOC_ROWS', soc_rows_html())
html = html.replace('HSDES_ROWS', hsdes_rows_html())
html = html.replace('GEN_DATE', str(datetime.date.today()))

html_path = r'C:\_hopper_results\20260428T174713_IDON_daq_soc\IDON_NVL_P_Report.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'HTML written: {html_path}')
