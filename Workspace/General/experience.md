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
