## Session: Startup Workflow Merge

- Date: 2026-04-28
- Area / File: C:\PowerKPI_AI\Workspace\General\Initial.md
- Trigger: Need to extend startup behavior without duplicating existing task lifecycle rules.
- Takeaway: Merge new startup requirements into the existing "Before Every Task" and "After Every Task" sections instead of adding separate duplicated sections.
- Added Behavior:
	- Read `C:\PowerKPI_AI\agents\core\PowerKPI.md` and `C:\PowerKPI_AI\agents\core\PowerKPI_debugger.md` at session start.
	- Inform the user after workload completion about work done, files updated, and new experience entries.
- Notes: Verified the actual debugger file path is `C:\PowerKPI_AI\agents\core\PowerKPI_debugger.md`.

## Session: Hopper FlexLogger Default Path

- Date: 2026-04-28
- Area / File: C:\PowerKPI_AI\skills\powerkpi\SKILL.md, C:\PowerKPI_AI\agents\core\PowerKPI.md
- Trigger: Hopper workload commands used a hardcoded old `-flex_cfg` path that should vary by project.
- Takeaway: Keep `SKILL.md` as the source of truth for Hopper commands, and default all `-flex_cfg` values to the NVL P FlexLogger project unless the user specifies another project.
- Added Behavior:
	- Updated Hopper DAQ command examples to use the default NVL P FlexLogger config path.
	- Added guidance that other projects should override only the `-flex_cfg` value.
	- Updated `PowerKPI.md` so workload execution defaults to the commands in `SKILL.md`.
- Notes: Use `-flex_cfg "your_path"` conceptually for project overrides, but default command blocks now point to the NVL P `.flxproj` path.

## Session: Data Compilation Workflow Section

- Date: 2026-04-28
- Area / File: C:\PowerKPI_AI\skills\powerkpi\SKILL.md
- Trigger: Need a clear post-run workflow to compile latest Hopper run summaries into report outputs.
- Takeaway: Add a dedicated "Compiling Data Section" with latest-run discovery under `C:\_hopper_results` and an explicit 4-step full capture flow.
- Added Behavior:
	- Defined how to locate latest run folders and summary CSV files.
	- Added full flow: specify task, specify run count, compile all runs to HTML+CSV, then generate insights using pre-silicon and related HSDES context.
	- Linked "Typical Workflow" step 5 to this new compilation flow to avoid duplicated guidance.
- Notes: User wording includes "HSED"; section preserves that context while also calling out HSDES-related inputs.

## Session: IDON x2 Execution and Summary for NVL P

- Date: 2026-04-28
- Area / File: C:\_hopper_results\20260428T174713_IDON_daq_soc
- Trigger: User requested idle workload run x2 for NVL P with summary generation.
- Takeaway: PsExec is located at `C:\Sysinternals\PsExec.exe` (not in system PATH). Always use full path. Run folder contains per-iteration sub-folders with DAQ summary CSV and SocWatch CSV. The consolidated results.json is at the root of the run folder.
- Added Behavior:
	- Use `C:\Sysinternals\PsExec.exe` when issuing proxy or SUT commands.
	- Power summary can be read from `<iteration-N>\<timestamp>\<timestamp>-power-default_Raw_Summary.csv`.
	- SocWatch C-state data extracted from the consolidated `<timestamp>-results.json` at the run root.
- Findings: NVL P IDON run showed PC10 = 0% (target 90%). P_VCCPRIM_VNNAON at 0.88 W (target 73 mW). PC10 blocker investigation required.
- Notes: Both runs consistent run-to-run (~5% variation). Platform stuck at PC0/PC2; C-state debug is the next action.

## Session: Per-Prompt Summary and Mandatory Report Outputs

- Date: 2026-04-28
- Area / File: C:\PowerKPI_AI\Workspace\General\Initial.md, C:\PowerKPI_AI\skills\powerkpi\SKILL.md
- Trigger: Need full context summary on every user prompt and stronger enforcement for workload reporting outputs.
- Takeaway: Context continuity should happen every prompt, not only before/after workload execution; reporting requirements must be explicit and mandatory.
- Added Behavior:
	- `Initial.md` now requires a full-context summary from `experience.md` on every user prompt.
	- `SKILL.md` now mandates HTML + CSV output for every workload run set.
	- HTML insights must include pre-silicon delta comparison, related HSDES (user wording: HSED) context, and explicit next-step recommendations.
- Notes: This closes ambiguity where report outputs could be interpreted as optional.

## Session: CMS x2 DAQ-only Execution and HTML Report — NVL P

- Date: 2026-04-29
- Area / File: C:\_hopper_results\20260429T093619_CMS_daq, C:\_hopper_results\20260429T094653_CMS_daq
- Trigger: User requested CMS DAQ-only capture x2 and power summary report.
- Takeaway: CMS DAQ-only (no SocWatch) runs complete cleanly. HTML report generated manually from results.json when generate_report.py is not applicable. Pre-silicon delta should always be included.
- Findings:
	- P_MCP_TOTAL = ~158 mW vs target 52.92 mW (+199%) — Platform stuck far above CMS target.
	- P_VCCPRIM_VNNAON = ~109.6 mW vs target 45.92 mW (+139%) — NPU/VNN not scaling down on screen-off. NPU driver D3 entry likely failing.
	- P_VCCPRIM_IO = ~24.4 mW vs pre-si ~1.76 mW — IO/PCH fabric not entering D3cold.
	- Run-to-run consistency: excellent (<1% variation between both runs).
	- No SocWatch collected — PC10/S0ix residency unknown; recommend follow-up CMS with SocWatch.
- Notes:
	- PXIe-4309 DevA at 56°C (threshold 50°C) — persistent warning, monitor for accuracy impact.
	- HTML report saved: C:\_hopper_results\CMS_DAQ_x2_Power_Report_20260429.html
	- Root cause still points to PC10 = 0% (same as IDON findings). Next debug: CMS + SocWatch to get PMC blocker list.

## Session: HSDES Tenant Discovery for NVL Sightings

- Date: 2026-04-29
- Area / File: pysvtools.hsdes, C:\PowerKPI_AI\skills\hsdes\SKILL.md
- Trigger: Attempted to query PowerKPI team sightings using `heia_soc.sighting` — returned 0 results for all members.
- Root Cause: `heia_soc.sighting` only contains legacy KBL/CNL/ICL era sightings (2017–2021). NVL/PTL/MTL sightings live in a different tenant.
- Fix: Use `sighting_central.sighting` as the tenant for all NVL/PTL/MTL/TGL generation sightings.
  - Auto-detect method: `ts = hsdes.config_by_id('15019278744')` → returns `sighting_central.sighting`
- Takeaway:
  - Always use `sighting_central.sighting` for current-gen (NVL/LNL/PTL/MTL) sighting queries.
  - `heia_soc.sighting` is a dead-end for any sighting newer than ~2021.
  - LIKE / CONTAINS / wildcard operators are NOT supported in EQL — use exact `=` operator only.
  - OR conditions in a single query cause timeout; split into individual queries per member per field.
  - Valid fields confirmed for `sighting_central.sighting`: id, title, owner, submitted_by, updated_by, updated_date, status, description, comments, priority, days_open, family, release_affected, forum.
- Notes: Queried 5 members × 3 fields = 15 individual queries; deduplicated by ID; found 310+ unique sightings.
