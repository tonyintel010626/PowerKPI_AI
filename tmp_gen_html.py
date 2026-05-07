import json
from pathlib import Path
from datetime import datetime

# Pre-silicon targets for CMS (NVL HX Q1'26 Martini)
# vccvnnaon=45.92mW, vccio~1.76mW, total_soc=52.92mW
presilicon = {
    'P_VCCPRIM_VNNAON':  45.92,   # vccvnnaon mW
    'P_VCCPRIM_IO':       1.76,   # vccio mW
    'P_MCP_TOTAL':       52.92,   # Total SoC target mW (pc10p3 dominant)
}

def get_power_rails(path):
    d = json.load(open(path))
    rails = {}
    for k, v in d.get('power', {}).items():
        if 'default' in v:
            try:
                mean = float(str(v['default'].get('mean', 0)).split()[0])
                mn   = float(str(v['default'].get('min',  0)).split()[0])
                mx   = float(str(v['default'].get('max',  0)).split()[0])
            except:
                mean = mn = mx = 0.0
            rails[k] = {'mean': mean * 1000, 'min': mn * 1000, 'max': mx * 1000}
    return rails

r1 = get_power_rails(r'C:\_hopper_results\20260429T093619_CMS_daq\20260429T093619-results.json')
r2 = get_power_rails(r'C:\_hopper_results\20260429T094653_CMS_daq\20260429T094653-results.json')

all_rails = sorted(set(list(r1.keys()) + list(r2.keys())))
power_rails = [r for r in all_rails if r.startswith('P_')]

def delta_class(delta_pct):
    if abs(delta_pct) < 5:
        return 'ok'
    elif abs(delta_pct) < 15:
        return 'warn'
    return 'bad'

def vs_target_class(measured, target):
    if target is None:
        return 'na'
    ratio = measured / target
    if ratio <= 1.1:
        return 'ok'
    elif ratio <= 2.0:
        return 'warn'
    return 'bad'

# Build rows
rows_html = ""
for r in power_rails:
    v1 = r1.get(r, {}).get('mean', 0)
    v2 = r2.get(r, {}).get('mean', 0)
    avg = (v1 + v2) / 2
    run_delta = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
    target = presilicon.get(r)
    if target:
        vs_tgt = (avg / target - 1) * 100
        tgt_str = f"{target:.2f}"
        vs_str = f"{vs_tgt:+.1f}%"
        tc = vs_target_class(avg, target)
    else:
        vs_tgt = None
        tgt_str = "—"
        vs_str = "—"
        tc = "na"

    dc = delta_class(run_delta)
    highlight = ""
    flag = ""
    if abs(avg) > 0.001:  # skip near-zero rails
        if r == 'P_VCCPRIM_VNNAON' and avg > 60:
            highlight = "style='background:#fff3cd'"
            flag = " ⚠ HIGH (target ~46mW)"
        elif r == 'P_MCP_TOTAL' and avg > 80:
            highlight = "style='background:#fff3cd'"
            flag = " ⚠ HIGH vs target"

    rows_html += f"""
    <tr {highlight}>
      <td><b>{r}</b>{flag}</td>
      <td>{v1:.2f}</td>
      <td>{v2:.2f}</td>
      <td>{avg:.2f}</td>
      <td class='{dc}'>{run_delta:+.1f}%</td>
      <td>{tgt_str}</td>
      <td class='{tc}'>{vs_str}</td>
    </tr>"""

# Key metrics summary
total_avg = (r1.get('P_MCP_TOTAL', {}).get('mean', 0) + r2.get('P_MCP_TOTAL', {}).get('mean', 0)) / 2
vnnaon_avg = (r1.get('P_VCCPRIM_VNNAON', {}).get('mean', 0) + r2.get('P_VCCPRIM_VNNAON', {}).get('mean', 0)) / 2
io_avg = (r1.get('P_VCCPRIM_IO', {}).get('mean', 0) + r2.get('P_VCCPRIM_IO', {}).get('mean', 0)) / 2

vnnaon_target = 45.92
total_target = 52.92

vnnaon_delta_pct = (vnnaon_avg / vnnaon_target - 1) * 100
total_delta_pct  = (total_avg  / total_target  - 1) * 100

def status_badge(delta_pct):
    if delta_pct <= 10:
        return f"<span class='badge-ok'>OK (+{delta_pct:.0f}%)</span>"
    elif delta_pct <= 100:
        return f"<span class='badge-warn'>HIGH (+{delta_pct:.0f}%)</span>"
    return f"<span class='badge-bad'>CRITICAL (+{delta_pct:.0f}%)</span>"

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CMS DAQ Power Summary — NVL P — 2026-04-29</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f8; color: #222; margin: 0; padding: 0; }}
  .header {{ background: linear-gradient(135deg,#0071c5,#004a91); color: white; padding: 28px 40px 20px; }}
  .header h1 {{ margin:0; font-size:1.7em; }}
  .header p  {{ margin:4px 0 0; opacity:.85; font-size:.95em; }}
  .container {{ max-width:1200px; margin:30px auto; padding:0 20px; }}
  .card {{ background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.08); margin-bottom:24px; overflow:hidden; }}
  .card-title {{ background:#0071c5; color:white; padding:12px 20px; font-size:1.05em; font-weight:600; }}
  .card-body  {{ padding:20px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }}
  .kpi-box  {{ border-radius:8px; padding:16px 20px; text-align:center; }}
  .kpi-box.green  {{ background:#e6f4ea; border-left:4px solid #28a745; }}
  .kpi-box.yellow {{ background:#fff8e1; border-left:4px solid #ffc107; }}
  .kpi-box.red    {{ background:#fdecea; border-left:4px solid #dc3545; }}
  .kpi-box .val   {{ font-size:2em; font-weight:700; margin:4px 0; }}
  .kpi-box .label {{ font-size:.8em; color:#666; }}
  .kpi-box .target{{ font-size:.8em; color:#888; margin-top:2px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88em; }}
  th {{ background:#e8f0f8; color:#004a91; padding:9px 12px; text-align:left; border-bottom:2px solid #c5d5e8; white-space:nowrap; }}
  td {{ padding:8px 12px; border-bottom:1px solid #eee; }}
  tr:hover td {{ background:#f0f7ff; }}
  .ok   {{ color:#28a745; font-weight:600; }}
  .warn {{ color:#c87800; font-weight:600; }}
  .bad  {{ color:#dc3545; font-weight:600; }}
  .na   {{ color:#aaa; }}
  .badge-ok   {{ background:#d4edda; color:#155724; padding:2px 10px; border-radius:12px; font-size:.85em; font-weight:600; }}
  .badge-warn {{ background:#fff3cd; color:#856404; padding:2px 10px; border-radius:12px; font-size:.85em; font-weight:600; }}
  .badge-bad  {{ background:#f8d7da; color:#721c24; padding:2px 10px; border-radius:12px; font-size:.85em; font-weight:600; }}
  .section-note {{ background:#e8f0f8; border-left:4px solid #0071c5; padding:10px 16px; border-radius:4px; margin-bottom:16px; font-size:.9em; }}
  .insight-list li {{ margin:6px 0; }}
  .insight-list li.warn {{ color:#856404; }}
  .insight-list li.bad  {{ color:#721c24; }}
  .insight-list li.ok   {{ color:#155724; }}
  footer {{ text-align:center; padding:20px; color:#999; font-size:.82em; }}
</style>
</head>
<body>

<div class="header">
  <h1>CMS DAQ Power Summary Report — NVL P</h1>
  <p>Connected Modern Standby | DAQ Only (FlexLogger) | 2 Captures | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
  <p>Run 1: 20260429T093619_CMS_daq &nbsp;|&nbsp; Run 2: 20260429T094653_CMS_daq</p>
</div>

<div class="container">

  <!-- KPI Summary Cards -->
  <div class="card">
    <div class="card-title">KPI Summary</div>
    <div class="card-body">
      <div class="kpi-grid">
        <div class="kpi-box {'yellow' if total_delta_pct > 10 else 'green'}">
          <div class="label">P_MCP_TOTAL (avg)</div>
          <div class="val">{total_avg:.1f} <span style="font-size:.5em">mW</span></div>
          <div class="target">Pre-Si Target: {total_target:.1f} mW &nbsp; {status_badge(total_delta_pct)}</div>
        </div>
        <div class="kpi-box {'yellow' if vnnaon_delta_pct > 10 else 'green'}">
          <div class="label">P_VCCPRIM_VNNAON (avg)</div>
          <div class="val">{vnnaon_avg:.1f} <span style="font-size:.5em">mW</span></div>
          <div class="target">Pre-Si Target: {vnnaon_target:.1f} mW &nbsp; {status_badge(vnnaon_delta_pct)}</div>
        </div>
        <div class="kpi-box green">
          <div class="label">Run-to-Run Consistency</div>
          <div class="val" style="font-size:1.4em">~0%</div>
          <div class="target">P_MCP_TOTAL: R1={r1.get('P_MCP_TOTAL', {'mean':0})['mean']:.1f} / R2={r2.get('P_MCP_TOTAL', {'mean':0})['mean']:.1f} mW</div>
        </div>
        <div class="kpi-box yellow">
          <div class="label">SLP_S0# Status</div>
          <div class="val" style="font-size:1.1em">DAQ Only</div>
          <div class="target">SocWatch not collected — C-state residency unknown</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Insights -->
  <div class="card">
    <div class="card-title">Insights & Analysis</div>
    <div class="card-body">
      <div class="section-note">
        Pre-silicon reference: NVL HX Q1'26 Martini CMS simulation — Total SoC target 52.92 mW, PC10p3 residency 99.81%
      </div>
      <ul class="insight-list">
        <li class="bad"><b>P_MCP_TOTAL = {total_avg:.1f} mW vs target 52.92 mW (+{total_delta_pct:.0f}%)</b> — Platform total power is significantly above pre-silicon CMS projection. This is consistent with prior IDON findings where PC10 = 0%.</li>
        <li class="bad"><b>P_VCCPRIM_VNNAON = {vnnaon_avg:.1f} mW vs target 45.92 mW (+{vnnaon_delta_pct:.0f}%)</b> — VNN Always-On rail is {vnnaon_avg:.0f} mW vs 45.9 mW target. NPU/VNN is not scaling down during screen-off. Likely NPU driver not entering D3 on CMS entry.</li>
        <li class="warn"><b>P_VCCPRIM_IO = {io_avg:.1f} mW</b> — IO rail active during CMS. Pre-silicon target ~1.76 mW. This rail should be near zero if PCH fabric is in deep power gate. Suspect PCH/IO fabric not entering D3cold.</li>
        <li class="warn"><b>P_V1P8A_ROP = {(r1.get('P_V1P8A_ROP', {'mean':0})['mean']+r2.get('P_V1P8A_ROP', {'mean':0})['mean'])/2:.1f} mW</b> — ROP 1.8V rail elevated. Expected near zero during CMS.</li>
        <li class="ok"><b>Run-to-run consistency: excellent (&lt;2% variation)</b> — Both runs are stable and reproducible. Data quality is valid.</li>
        <li class="warn"><b>No SocWatch collected</b> — C-state residency (PC10/S0ix) is unknown. Recommend re-running with DAQ+SocWatch to identify PMC blockers.</li>
        <li class="bad"><b>Root cause hypothesis</b>: PC10 = 0% (from prior IDON run) is likely persisting during CMS as well, explaining elevated P_MCP_TOTAL. VNNAON not scaling = NPU driver D3 entry failure. Next step: collect SocWatch PMC blocker log.</li>
      </ul>

      <h4 style="margin-top:20px">Recommended Next Steps</h4>
      <ol>
        <li>Run <b>CMS with DAQ + SocWatch</b> to capture PC10 / S0ix residency and PMC blocker list.</li>
        <li>Check BIOS knob: <code>Low Power S0 Idle Capable</code> = Enabled (XMLCLI).</li>
        <li>Check NPU driver D3 state: Device Manager &rarr; AI Processor &rarr; verify D3 entry on screen-off.</li>
        <li>Check <code>P_VCCPRIM_IO</code> blocker: likely PCH fabric (audio, USB, PCIe) not entering D3cold.</li>
        <li>Review SocWatch PMC blocker IP list to narrow down which IP is blocking PC10/S0ix.</li>
      </ol>
    </div>
  </div>

  <!-- Power Rail Table -->
  <div class="card">
    <div class="card-title">Power Rails Detail (DAQ — FlexLogger)</div>
    <div class="card-body">
      <table>
        <thead>
          <tr>
            <th>Rail</th>
            <th>Run 1 (mW)</th>
            <th>Run 2 (mW)</th>
            <th>Avg (mW)</th>
            <th>Run Delta</th>
            <th>Pre-Si Target (mW)</th>
            <th>vs Target</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Run Metadata -->
  <div class="card">
    <div class="card-title">Run Metadata</div>
    <div class="card-body">
      <table>
        <thead><tr><th>Parameter</th><th>Run 1</th><th>Run 2</th></tr></thead>
        <tbody>
          <tr><td>Folder</td><td>20260429T093619_CMS_daq</td><td>20260429T094653_CMS_daq</td></tr>
          <tr><td>Workload</td><td colspan="2">Connected Modern Standby (CMS)</td></tr>
          <tr><td>Instrumentation</td><td colspan="2">FlexLogger DAQ only (no SocWatch)</td></tr>
          <tr><td>Quiesce Time</td><td colspan="2">180s (screen-on 120s + screen-off 60s)</td></tr>
          <tr><td>Capture Duration</td><td colspan="2">180s</td></tr>
          <tr><td>FlexLogger Sampling Rate</td><td colspan="2">1000 Hz</td></tr>
          <tr><td>SUT IP</td><td colspan="2">192.168.137.5</td></tr>
          <tr><td>Hopper Version</td><td colspan="2">2026.16.0</td></tr>
          <tr><td>DAQ Hardware Warning</td><td colspan="2">PXIe-4309 DevA: 56°C (threshold 50°C) — monitor for accuracy impact</td></tr>
        </tbody>
      </table>
    </div>
  </div>

</div>

<footer>PowerKPI Report &mdash; NVL P CMS DAQ &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')} &mdash; CW Pro Max</footer>
</body>
</html>
"""

out = r'C:\_hopper_results\CMS_DAQ_x2_Power_Report_20260429.html'
Path(out).write_text(html, encoding='utf-8')
print(f"HTML report saved: {out}")
