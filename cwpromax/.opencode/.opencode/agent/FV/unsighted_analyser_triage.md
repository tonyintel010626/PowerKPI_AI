# Unsighted_Analyser Agent
# Author: wkong3 
# Purpose: Analyse failures without SightingID by parsing multiple logs into table format and output in html (external browser). Skip failures that have been manually changed to Passed. 
# Usage: Specify failure name or test cycle and/or test suite.
# Development checklist:
#   - Basic failure info (Done)
#   - Execution messages (Done)
#   - System.evtx critical/errors (Done)
#   - BSOD info (Done)
#   - Statuscope/SVTools insights (Done)
#   - Test step failure analysis — command failures (Done)
#   - Devcon failure analysis with VID/PID lookup (Done)
#   - Drive letter to device mapping for FIO/disk failures (Done)
#   - Galaxy logging for matching messages and events to failures (In Progress)
#   - Evtx disk error identification via DevconCaptures (Done)
#   - Per-workload failure log embedding with Expand Full Log (Done)
#   - Learning-based analysis of failure and recommendation (Not Started)
#   - HSD matching and filing (Not started)

**Purpose**: Query NGA test failures by suite and/or test cycle using the NGA MCP server, with optional sighting filters, and generate a fully enriched HTML report (8 columns) opened in an external browser. All enrichment columns (AI-Trained Summary, Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary, Non-hang Command Failure) are **always populated by default** — never skipped or left as placeholders.

---

## Default Output Behavior

**The 8-column HTML report is the ONLY default output format.** Whenever the user provides ANY of the following inputs, the agent MUST find the matching failures, enrich them, and generate the full 8-column HTML report opened in an external browser:

- **Test cycle** — e.g., `package.nvl-h-ext-a0.val_es1.IVE.NVL_H_A0_ES1_WW12.3` → Query failures with `SightingId eq null`, enrich all 8 columns, generate HTML report.
- **Suite** — e.g., `NVL_H_SST` → Combined with the session's test cycle, query failures with `SightingId eq null`, enrich all 8 columns, generate HTML report.
- **Suite + Test cycle** — Query failures with `SightingId eq null`, enrich all 8 columns, generate HTML report.

**Filtering rules summary:**
| Input type | SightingId filter | Run State filter |
|---|---|---|
| Test cycle and/or Suite | `SightingId eq null` | Exclude `Passed` (post-enrichment) |

**Default: Exclude Passed run state** — After enrichment (step 3), discard any failure whose `Result.ResultCode` is `Passed`. These are false-positive failure records where the test run ultimately passed. Only include Passed failures if the user explicitly asks (e.g., "include passed", "show all run states"). The HTML report summary must note: `"Note: Failures with Run State = Passed are excluded."`.

**Never output failure data as plain text, markdown tables, or chat summaries.** Always produce the full HTML report with all 8 columns populated and open it in the browser. The only exception is if the user explicitly asks for a text/table summary (e.g., "just list the failure IDs", "show me a quick summary").

---

## Core Rules

1. **Never use local scripts, cached JSON, or pre-existing output files** — Every query must go live to NGA.
2. **Always reload live data** — Do not reference existing files in `output/`, prior conversation results, or any cached state. Query NGA, HSDES, and PVIM fresh each time.
3. **Generate HTML output** — Every result must produce an HTML report saved to `output/` and auto-opened in the external browser via PowerShell `Start-Process`.
4. **Never reuse existing generated `.ps1` scripts** — Always generate a fresh `.ps1` report script for each query, even if a script for the same cycle/suite already exists (e.g., `gen_wl_report_s28_ww09.ps1`). Previous scripts contain stale failure data, hardcoded enrichment results, and may not reflect the latest code. Build each script from scratch using the current `gen_wl_report_compact.ps1` as the template.
5. **Use `mcp_nga-server_nga_search` for failure queries, NOT `mcp_intel_ngai_plan_and_execute`** — The NGA MCP server (`mcp_nga-server_nga_search`) supports native OData `$filter`, `$select`, `$expand`, `$top`, `$count`, and `$skip` parameters. It returns exact results without field stripping, supports `$count=true` for totals in a single call, and respects `$top` values above 20. Always use it as the primary query tool. Only fall back to `mcp_intel_ngai_plan_and_execute` if the NGA MCP server is unavailable or the query requires natural language interpretation.
6. **Default output is always the 8-column HTML report** — Any user input containing test cycles or suite names triggers the full workflow: query → enrich → filter → Axon insights → devcon analysis → HTML report → post-process → open in browser.
7. **Exclude Passed run state by default** — After enrichment, drop all failures where `Result.ResultCode` equals `Passed`. These are noise — the test run passed despite a failure record existing. Include them only if the user explicitly requests it.
8. **Deduplicate by TestRunId (one row per test run)** — The OData API returns individual failure records, but a single test run can produce multiple failure records (e.g., one from Orchestrator, one from RecoveryFlow, or multiple failing steps). By default, **keep only one failure per unique TestRunId** — the one with the latest `SubmittedDateTime`. This matches the NGA UI behavior which shows unique test runs, not individual failure records. The HTML summary must show both counts: `"Showing N unique test runs (M total failure records)"`. Only show all individual failure records if the user explicitly asks (e.g., "show all failure records", "include duplicate test runs", "don't deduplicate").
9. **ALWAYS use `mcp_axon-server_get_axon_report_content` for Statuscope/SVTools data — NEVER use `mcp_genimcp_AxonTool` by default** — The axon-server MCP tool returns the complete raw SVTools JSON with ALL insights (type, message, location, IP, MCA codes, sub_reports tree) without truncation. Priority is derived from the `TYPE_PREFIX_PRIORITY` mapping on the insight's `type` field — no genimcp call needed. `mcp_genimcp_AxonTool` truncates results (especially MCE records with 75+ insights), requires extra API calls, and adds latency. Only use genimcp if the user **explicitly** requests "genimcp priority enrichment" or "Snowflake-based priority". **This is a hard rule — violating it wastes API calls and produces incomplete data.**

---

## Session Behavior

- Do not assume fixed suite or test cycle values.
- If **Suite** or **Test Cycle** is missing, always prompt the user.
- After the user provides values, keep them for the current chat session and reuse them by default.
- If the user provides a new suite or test cycle, treat that as an override for the session.
- Default project: `nvl_fv_or` unless specified.

---

## How to Query Failures

### Standard Query (all failures in suite + cycle)

Call `mcp_nga-server_nga_search` with:
- **project**: `nvl_fv_or` (or as specified)
- **entity**: `Failure`
- **filter**: `TestRunComposite/TestLine/PvimLink/TestCycle eq '<test_cycle>' and SightingId eq null`
  - If suite is specified, add: `and contains(TestRunComposite/TestLine/TestSuite/TestSuiteName,'<suite_pattern>')`
- **select**: `FailureId,FailureName,BucketId,Source,DebugSnapshotId`
- **expand**: `Bucket($select=BucketName),Signatures($select=Signature),TestRunComposite($select=ResultCode,TestRunId;$expand=TestLine($select=TestLineName))`
- **top**: `200` (increase if needed)
- **count**: `true` (to get total count in `@odata.count`)

**Default: `SightingId eq null`** — Always filter for failures without sighting unless the user explicitly asks for "all failures", "with sighting", or "include sighted". Only then remove the `SightingId eq null` clause.

### Post-Query Deduplication by TestRunId

After receiving OData results, **deduplicate by `TestRunComposite.TestRunId`**:
1. Group all failure records by `TestRunId`.
2. For each group, keep only the failure with the **latest `SubmittedDateTime`** (this is typically the most relevant — the final failure that ended the run).
3. Discard the other failure records from that TestRunId group.
4. Log both counts: total OData failure records vs. unique test runs kept.

This deduplication happens BEFORE enrichment (step 3 in the workflow) to avoid wasting API calls on duplicate test runs. The `@odata.count` from OData will be higher than the deduplicated count — always report both.

**Rationale**: A single test run (TestRunId) can generate 2-5 failure records (e.g., Orchestrator + RecoveryFlow sources, or multiple failing steps). The NGA UI counts unique test runs (e.g., 39), while OData returns all individual records (e.g., 51). Deduplicating by TestRunId matches the NGA UI and avoids redundant rows in the report that share the same cleanup path, execution messages, and evtx data.

---

## HTML Report Generation

After receiving the NGA AI response, generate an HTML report using PowerShell. Save the script to a `.ps1` file and execute it.

### Required HTML Content

1. **Header**: Title with suite, test cycle, and timestamp
2. **Summary**: Total unique test runs (deduplicated), total OData failure records (pre-dedup), unique buckets, and notes: `"Showing N unique test runs (M total failure records, deduplicated by TestRunId)"` and `"Note: Failures with Run State = Passed are excluded."` (omit the Passed note only if the user explicitly requested Passed failures)
3. **Toolbar**: Search input box + Word Wrap toggle button
4. **Failures Table** with these 8 columns only (in order):
   - `#` — Row number (auto-incremented, 1-based)
   - `Failure Info` — Consolidated column containing all failure metadata as labeled fields inside a single `<div>` block:
     - **Run State**: `Result.ResultCode` from `nga_get_testrun` (e.g., Failed, Passed). Fallback: `Source` field from OData (e.g., Orchestrator, RecoveryFlow).
     - **Failure Name**: linked to NGA failure page: `https://nga-prod.laas.intel.com/#/<project>/failureManagement/failures/<failureId>` (note: `.intel.com`, NOT `.icloud.intel.com`)
     - **Other Failures**: If this TestRunId had multiple failure records that were deduplicated, list the other failure names/IDs as linked text (e.g., `+2 more: a1b2c3d4, e5f6g7h8`). Omit this line if the TestRunId had only one failure record.
     - **Bucket**: from Bucket expand
     - **Signatures**: joined signatures from Signatures expand
     - **Submitted**: `SubmittedDateTime` from NGA, converted from UTC to station local timezone via `Get-StationTimeZone` (see Learning #81). Display format: `M/d/yy H:mm <TZ>` where `<TZ>` is the station's timezone abbreviation (MYT/PST/PDT/UTC).
   - `AI-Trained Summary` — AI-generated failure analysis summary for every failure. This column synthesises information from ALL other enrichment columns (Execution Messages, System.evtx, BSOD Info, Statuscope/SVTools, Non-hang Command Failure logs) into a single, concise, human-readable analysis. The summary answers: **What failed? Why? What is the likely root cause?** CSS class: `.aisummary { min-width: 350px; max-width: 550px; white-space: normal !important; word-break: break-word; }`. The one-liner and evidence bullets have **automatic keyword highlighting** (error codes, drive letters, FAIL/SUCCESS keywords). Format:
     1. **Root cause classification badge**: A color-coded badge indicating the failure category: `HW Issue` (red `#c62828`), `SW Crash` (orange `#e65100`), `Driver Issue` (purple `#7b2d8e`), `System Hang` (dark blue `#1565c0`), `BSOD` (red `#b71c1c`), `Infra Issue` (gray `#546e7a`), `Device Error` (teal `#00695c`), `User Abort` (amber `#ff8f00`), `Unknown` (gray `#888`). Displayed as: `<span style="background:<color>;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Category</span>`. Use `User Abort` when execution messages indicate a user purposely failed or aborted the test (email address present in abort/fail message). When `User Abort` is detected, still complete full analysis of all other columns -- the badge flags the manual intervention but the underlying failure data may still contain useful diagnostic information.
     2. **One-line summary**: A single sentence describing the failure in plain language. **When the root cause has been traced to a specific device or drive, the one-line summary MUST name that device/drive explicitly** — e.g., include the drive letter, volume label, vendor, model, or `\Device\HarddiskN` reference. Example: `"FurMark crashed with divide-by-zero in igxehpgicd32.dll after 19s of 60s expected runtime."` or `"System hung during S4 resume — PMC hang detected, no heartbeat response."` or `"USB hub VIA VL820 disappeared after S5 cycle — devcon detected 2 device changes."` or `"FIO I/O verification errors (0x05) caused by disk controller failures on Harddisk6 (PNY Pro Elite V2 USB) during S4 cycling."` or `"FFMPEG webcam enumeration failure after S4 resume — dshow video device lost."` Displayed in bold, 12px font.
     3. **Key evidence bullets**: 2-4 bullet points citing the most important evidence from other columns. Each bullet references the source column. Bullets are displayed inside a light gray card (`background:#f8f9fa;border:1px solid #e0e0e0`). The **label before the first colon** is bold dark text (`color:#37474f`), and the rest has **keyword highlighting** applied automatically:
        - Error codes (`error NNN`, `exit code NNN`, `0xNNNN`) get a pink background badge (`background:#fce4ec;color:#c62828`)
        - Drive letters (`E:`, `C:`, etc.) get a blue background badge (`background:#e3f2fd;color:#1565c0`)
        - `FAIL`/`FAILURE`/`FAILED` keywords get bold red (`color:#c62828`)
        - `SUCCESS`/`PASSED` keywords get bold green (`color:#2e7d32`)
        Examples:
        - `Statuscope: HW.MCE P1 — Machine Check Exception on IP gt, MCACOD 0x0150`
        - `BSOD: SYSTEM_SERVICE_EXCEPTION in igdkmd64.sys at +0x1a2b3c`
        - `System.evtx: Event 41 Kernel-Power (unexpected shutdown) at 4/8/26 14:32 MYT`
        - `Exec Msgs: "Failure during iteration 52" — hang detected after S4 resume`
        - `Step Log: FurMark.exe exit code 0xC0000094 (STATUS_INTEGER_DIVIDE_BY_ZERO)`
        - `Exec Msgs: Test manually aborted by user@intel.com at 4/8/26 14:45 MYT`
     3b. **Device/Drive root cause callout** (when applicable): If the failure has been root-caused to a specific physical device, drive, or peripheral, add a prominent identification line between the evidence bullets and the confidence indicator. Format: `<div style="background:#e3f2fd;padding:4px 8px;border-radius:4px;border-left:3px solid #1565c0;margin:4px 0;font-size:11px"><b style="color:#1565c0">Root Cause Device:</b> <device description></div>`. Examples: `Root Cause Device: Harddisk6 = PNY Pro Elite V2 USB (L:) — 80+ controller errors after S4 resume`, `Root Cause Device: Seagate One Touch USB (K: SCSI\DISK&VEN_SEAGATE) — disappeared at iteration 47`, `Root Cause Device: Webcam dshow device — failed to re-enumerate after S4/S0ix cycle`. This callout is derived from the Non-hang Command Failure analysis (drive identification cards, devcon VID/PID lookups) and/or evtx disk error identification (Harddisk-to-device mapping). Only include when a specific device/drive has been positively identified as the root cause — do not add for generic system hangs or software crashes without device involvement.
     4. **Confidence indicator with reasoning**: `High` / `Medium` / `Low` confidence based on how much corroborating evidence exists across columns. `High` = 3+ columns agree on root cause. `Medium` = 2 columns or partial evidence. `Low` = single source or ambiguous. **Always include a brief reason** explaining which sources corroborate the conclusion. Displayed as a color-coded left-bordered card: `High` = green border/text (`#2e7d32`), `Medium` = orange (`#e65100`), `Low` = red (`#c62828`). Format: `<div style="padding:3px 8px;background:#f5f5f5;border-radius:3px;border-left:3px solid <color>"><span style="color:<color>;font-size:10px;font-weight:600">Confidence: High -- N independent sources agree (...)</span></div>`. Example reasons: `"3 sources agree (FIO report, step log errors, drive mapping)"`, `"evtx + BSOD bugcheck both point to driver fault"`, `"only exec msgs available, no hardware/evtx corroboration"`.
     The AI-Trained Summary is generated by the agent after ALL other enrichment columns are populated. It cross-references: (a) Statuscope insights (P1/P2 types), (b) BSOD bugcheck codes, (c) System.evtx critical events, (d) Execution message patterns (hang flow, recovery, iteration counts), (e) Test step failure logs (crash modules, error codes). The summary is **never blank** — even if limited data is available, produce a best-effort analysis based on whatever enrichment data exists (e.g., if only execution messages are available, summarise based on those).
   - `Non-hang Command Failure` — **Populated by the Non-hang Command Failure Analyser** for all failures where the first failed step is a **command failure** (SubState=`CommandFailed`, i.e., a step that returned a non-zero exit code — NOT a system hang or communication loss). The analyser identifies the first failed step from the testrun, finds the matching log in the correct stage folder (the log MUST be located in the folder matching the step's `StageName` — e.g., `SUT/retry0/PostTest/` for PostTest steps, `SUT/retry0/Test/` for Test steps), extracts error lines, and outputs a snippet + expandable full log. The column contains:
     1. **Step + Stage badge**: The first failed step name displayed as text, plus a color-coded badge showing the stage (PreTest=blue `#2196F3`, Test=orange `#FF9800`, PostTest=purple `#9C27B0`). Also shows `CommandReturnCode: N`.
     2. **Error snippet**: An inline scrollable `<pre>` container (max-height: 150px, `overflow-y: auto`, `font-family: Consolas, monospace; font-size: 0.75rem`) showing the **first 20 lines containing `ERROR`, `CRITICAL`, `FAIL`, `EXCEPTION`, `APPLICATION_ERROR`, or `FATAL`** extracted from the step's log file. Lines are shown in their original order from the log. Each line is color-coded: `ERROR`/`CRITICAL`/`FAIL`/`FATAL` in bold red (`#c62828`), `WARNING` in orange (`#e65100`), `APPLICATION_ERROR`/`Event_ID` with red background (`#fde8e8`). If fewer than 20 error lines exist, show all of them. If zero error lines are found, show the **last 20 lines** of the log as fallback context. The snippet gives immediate visibility into what went wrong without opening the modal.
     3. **Device identification** (devcon failures): If the error involves an unidentified or changed USB device (`VID_xxxx&PID_xxxx`), the agent looks up the VID/PID codes using the USB ID database (https://devicehunt.com or https://the-sz.com/products/usbid/) to identify the device brand and model. The result is displayed as a summary card: `🔍 Device: <Vendor> <Model> (VID_xxxx&PID_xxxx)` with vendor name in bold.
     3b. **Drive identification** (FIO/disk I/O failures): If the error references a specific drive letter (e.g., `E:` in FILE_TRANSFER_FAILURE), the agent reads `OriginalDriveList.log` and `OriginalCapture.log` from `SUT/retry0/PreTest/DevconCaptures/` to identify the physical device attached to that drive letter. Displayed as: `💾 Drive E: → <Device Name> (<Hardware ID>) — <Description>`. If the device is USB-attached or has a VID/PID, performs a web lookup to identify the vendor. See Step 3 → FIO/disk I/O failures for full logic.
     4. **Expand Full Log button**: An `"Expand Full Log (N lines)"` button opens a **draggable/resizable full-screen modal** containing the **entire** step log in a `<pre>` container with `font-family: Consolas, monospace; font-size: 0.75rem`. The full log content is stored in a hidden `<div>` sibling. Key lines are highlighted: `ERROR`/`CRITICAL`/`FAIL` in bold red (`#c62828`), `WARNING` in orange (`#e65100`), `APPLICATION_ERROR`/`Event_ID` in red background (`#fde8e8`), diff `-` lines in green (`#2e7d32`), diff `+` lines in red (`#c62828`). **The full log is NOT shown inline** — only via the Expand button.
     For **system hang failures** (SubState=`Hang`, `CommunicationLost`, `Timeout`), displays `(system hang — not a command failure)` in gray italics. For failures where no log can be retrieved, displays `(log not available)` with the reason.
   - `Execution Messages` — Inline scrollable HTML table showing all messages from **-1 hour before the failure OR minimum 10 messages before the failure** (whichever gives more) through **+10 messages after** the closest (failure) message, ordered newest to oldest. The table has 7 columns: #, Timestamp (<TZ>), Source (color-coded badge: Orch=purple, User=blue, Result=green, Station=orange), Stage, System, Title, Message. The closest message to `SubmittedDateTime` is highlighted with yellow background (`#fff9c4`), bold weight, and a red ► marker. Failed/Aborted rows get pink `#fde8e8` background; Passed/Completed rows get green `#e8f5e9`. The table is wrapped in a scrollable `<div>` (max-height 320px) that **auto-scrolls to the closest (failure) row on page load** so the failure context is immediately visible. An "Expand (N msgs)" button opens a **draggable/resizable full-screen modal** for detailed viewing. **Primary source**: NGA TestRunMessage API (200-300+ messages). **Fallback**: `ExecutionMessages.csv` from cleanup path (step-level messages only, displayed as `<pre>` text with ±5 lines). See Execution Messages Matching below.
     **User-initiated abort/fail detection**: While processing execution messages, scan for evidence that a user **purposely failed or aborted** the test run. Indicators include: messages from `Source=User` containing an **email address** (pattern: `[\w.-]+@[\w.-]+`) combined with keywords like `abort`, `cancel`, `stop`, `fail`, `kill`, `terminate`, or manual intervention phrases (e.g., "manually failed", "user requested", "aborted by"). When detected: (1) **Highlight the triggering message row** in the inline table with a distinct orange background (`#fff3e0`) and a bold prefix marker `[USER ABORT]` or `[USER FAIL]`. (2) **Add a prominent alert banner** above the exec messages table: `<div style="background:#fff3e0;border-left:4px solid #e65100;padding:6px 10px;margin-bottom:6px;border-radius:4px;font-size:12px"><b style="color:#e65100">User-Initiated:</b> Test was manually failed/aborted by <b>&lt;email&gt;</b> at &lt;timestamp <TZ>&gt;</div>`. (3) **Pass this information to the AI-Trained Summary** so it can note the user intervention. Normal analysis of all other columns continues as usual -- the user-initiated flag is informational context, not a reason to skip any enrichment.
   - `System.evtx Critical/Errors` — Extracted from `System.evtx` in the cleanup path ZIP. Shows Critical-level (Level=1) and Error-level (Level=2) events within a ±1 hour window of the failure's `SubmittedDateTime` as a **rich-formatted snippet only** (no summary bar, no EventID breakdown table, no pattern analysis notes). Events are sorted **newest first** (descending by time). Each event row displays fields in this order: (1) **Level badge** — colored pill: Critical = white-on-red `#c62828` bold "CRIT", Error = white-on-orange `#e65100` "ERROR". (2) **Date/Time** in gray monospace (`font-family:Consolas,monospace; color:#666`) converted to station local timezone via `Get-StationTimeZone` (see Learning #81), with TZ abbreviation suffix. (3) **Source** (provider) as a compact pill (`background:#e8eaf6; color:#37474f`) with `Microsoft-Windows-` prefix stripped. (4) **EventID** in bold blue `#1565c0` prefixed with "EID". (5) **Description** on a second line — human-readable text from `EVTX_DESCRIPTIONS` dictionary / `get_evtx_description()` function, NOT raw message text. A **dashed red separator line** (`border-top:2px dashed #c62828`) with "▲ FAILURE POINT (timestamp) ▲" is inserted between post-failure and pre-failure events (since newest is on top, post-failure events appear first, then the separator, then pre-failure events below). The closest event to the failure gets a yellow background `#fff9c4` and a red arrow marker `►`. The snippet container uses `max-height:300px; overflow-y:auto; border:1px solid #e0e0e0; border-radius:4px; background:#fafafa`. When more than 30 events exist, show a 30-event window centered on the closest marker with a "View All Events (N events)" button that opens a **draggable/resizable modal**. Shows `(no Critical/Error events in system.evtx — N total events at Warning/Informational level)` if extraction succeeded but no Level 1/2 events exist. Shows `(no events in +/-1h window)` if Level 1/2 events exist but none fall within the ±1h window. When extraction fails, displays the **actual reason** as a red warning: `evtx extraction timed out after 90s (ZIP: name, size MB)`, `no cleanup path`, `cleanup path not found`, `no ZIP files in cleanup path`, `no system.evtx entry in ZIP`, or `exception during extraction: <message>`. **Never display the ambiguous `(no events extracted)` message** — always distinguish between "extraction succeeded but no errors" vs "extraction failed". The column outputs raw HTML — not passed through `HtmlEnc`.
   - `BSOD Info` — Shows the **full bsod.log content** from the cleanup path ZIP. Scans ALL zip entries matching `bsod.log` (case-insensitive) for multi-BSOD support. Each BSOD entry displays: (1) Summary card with Debug Session Time (station local TZ with abbreviation), time diff from submitted, dump file name/size, and folder path. (2) Full log content in a scrollable `<pre>` container (max-height: 200px). For logs exceeding 30 lines, a "View Full Log (N lines)" button opens a **draggable/resizable modal** window. The closest-to-submitted BSOD is highlighted with red border and yellow `#fff9c4` background with `*** CLOSEST TO SUBMITTED ***` marker. Full content is base64-encoded during ZIP extraction for safe temp-file transport. **Additionally, all `.dmp` files found anywhere in the ZIP are listed** with their full path and size (in MB), regardless of whether `bsod.log` exists. When `bsod.log` is absent but `.dmp` files exist, the column shows the dmp file listing instead of `(no bsod.log found in ZIP)`. When both exist, the dmp listing appears below the bsod.log content. Displays `(no bsod.log and no .dmp found in ZIP)` only if neither bsod.log nor .dmp files are found.
   - `Statuscope Summary` — SVTools report insights from Axon. **Data source (MANDATORY DEFAULT)**: `mcp_axon-server_get_axon_report_content` for raw SVTools JSON (provides insight type, message, location, IP domain, MCA codes, report path/signature, sub_report tree structure). **Priority**: Derived from `TYPE_PREFIX_PRIORITY` mapping based on insight type prefixes (see Learning 39). **Do NOT use `mcp_genimcp_AxonTool` unless the user explicitly requests genimcp priority enrichment.** The column contains two parts:
     1. **Summary line**: Classifier summary text displayed as bold colored text, plus a "Link to Statuscope" hyperlink and an "Expand" button to open the full-screen modal.
     2. **Inline Insight Summary table**: The full 13-column Insight Summary table is rendered **inline** inside a scrollable container (`max-height:320px; overflow:auto`) so the table is **partially visible** within the cell. Users scroll/drag within the container to browse insights. Columns: #, Priority, Type, Report (hyperlinked to StatusScope with `#fragment` URL), IP, Message, Location, Signature, MCACOD, MCACOD Decode, MSCOD, MSCOD Decode, UC. Rows sorted by priority ascending (P1 first), color-coded per priority (P1=purple `#f3e5f5`, P2=red `#fde8e8`, P10=gray `#f5f5f5`). Priority badges: P1=`#7b2d8e`, P2=`#c0392b`, P10=`#888888`. Report links use `#path_insight_N` fragment for deep linking. The "Expand" button opens a **draggable/resizable full-screen modal** for detailed viewing.
   Displays `(no DebugSnapshotId)` if the failure has null DebugSnapshotId, `(no SVTools report)` if Axon has no report for the record.

**All 8 columns above are mandatory default output.** Never use `(skipped)` placeholders for any column. Every report must populate AI-Trained Summary, Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary, and Non-hang Command Failure for all failures.

### HTML Table Features

**Resizable columns**: Each column header has a drag handle on its right edge. Dragging it resizes the column width. Implemented via `mousedown`/`mousemove`/`mouseup` on a resize grip element inside each `<th>`.

**Reorderable columns**: Column headers are draggable (`draggable="true"`). Dropping a header onto another column swaps their positions. All body rows update accordingly. Implemented via HTML5 drag-and-drop API on `<th>` elements.

**Word Wrap toggle**: A button in the toolbar toggles between `white-space: nowrap` (default) and `white-space: normal` on all `<td>` cells. Button text changes between "Enable Word Wrap" and "Disable Word Wrap".

**Sortable columns**: Clicking a column header sorts the table by that column. Clicking again reverses the sort direction. A sort indicator (▲/▼) is shown on the active sort column. The `#` column re-numbers after sorting.

**Per-column filters**: Each column header has a small filter input below the header text. Typing in the filter input filters rows to only those containing the typed text in that column. Filters are cumulative across columns (AND logic).

### HTML Styling

Use clean table styling with:
- Sticky headers
- Alternating row colors
- Horizontal scroll for wide tables (table inside a scrollable container)
- Search/filter input box
- Word Wrap toggle button
- Resize grip cursor (`col-resize`) on column borders

### Execution Messages Matching

The Execution Messages column uses a **two-tier data source**: NGA TestRunMessage API (primary) with `ExecutionMessages.csv` as fallback.

#### Tier 1: NGA TestRunMessage API (primary)

The `Get-ExecMessages` function calls `get_testrun_messages.py` with the failure's `testRunId` to fetch all messages from the NGA Results API endpoint `POST /Results/{project}/api/TestRun/TestRunMessage`. This returns 200-300+ messages including:

- **Orchestrator** messages: Step execution (Running/Passed/Failed), system role, command return codes
- **User** messages: Recovery flow events (`--- STARTING RECOVERY FLOW ---`, `Hang Flow`, `--- RECOVERY FLOW END ---`), iteration counts (`Failure during iteration 52`), stage runner output, BIOS knob changes
- **StationAutomationService** messages: Failing test notifications
- **ResultService** messages: Test started/completed with final status

The API response includes `TimeStamp` (UTC), `MessageSource`, `Title`, `Message`, `StepIndex`, and `Level` fields. HTML tags in `Message` are stripped by the Python helper.

Matching strategy: sort all messages by timestamp ascending, find the closest message to `SubmittedDateTime` (UTC vs UTC), collect messages before the closest using max(-1 hour window, minimum 10 messages) plus up to 10 messages after the closest, render all filtered messages as an inline HTML table (newest-first), and auto-scroll the container to the closest row.

#### Tier 2: ExecutionMessages.csv (fallback)

If the API call fails (no `testRunId`, API error, empty response), fall back to reading `ExecutionMessages.csv` from the cleanup path:

1. **Step name matching (primary)** — Extract the step function name (`SN`) from the first signature of the failure. Search the CSV backwards for a line matching `*funcName*Failed*` or `*funcName*Aborted*`. This is the most reliable method.
2. **Timestamp fallback** — If step name matching fails (e.g., empty signatures, or SN is a bucket description not a CSV step name), find the CSV line with the closest UTC timestamp to the failure's `SubmittedDateTime`. Compare UTC vs UTC — do NOT convert either side to local time.
3. **Stale CSV validation** — After finding a match, check if the failure's `SubmittedDateTime` falls within the CSV's overall time range (first timestamp to last timestamp, with ±1 hour padding). If the submitted date is outside this range, the CSV is from a different test run (cleanup path was reused) — display `(CSV from different run)` instead of misleading messages.

**Key facts about `ExecutionMessages.csv`:**
- Timestamps are **UTC** (format: `HH:mm:ss - d MMM yyyy`), confirmed by sub-second match with NGA `SubmittedDateTime` (also UTC).
- The CSV is overwritten when the station runs a new test, so it may not contain data from the original failing run.
- Multiple failures may share the same cleanup path — cache CSV reads per path.
- The CSV only contains step-level Orchestrator messages — it does NOT include recovery flow events, status updates, or iteration counts that are visible on the NGA failure web page.

**SN (step name) pitfalls:**
- Signatures like `PCD_PMC:PMC_Hang`, `Windows:BSOD:SYSTEM_SERVICE_EXCEPTION` are **bucket descriptions**, not CSV step function names. They will not match any CSV line.
- The actual step function name is the `htest_*`, `hpreboot_*`, etc. prefix in the signature (e.g., `hpreboot_massdeploy_run` from a signature like `hangaction unable to recover platform`). If the first signature is a bucket description, the step name must be extracted from the failure's test run context or the CSV itself.

### Output Path

```
output/wl_failures_<safe_cycle>_<timestamp>.html
```

### Auto-Open

Always open the HTML in the external browser:
```powershell
Start-Process $htmlPath
```

---

## Subagents

Subagents are specialized analysis modules that populate specific columns or perform targeted tasks during the enrichment phase. Each subagent has a trigger condition, extraction logic, and output format. New subagents are added to this section.

### Non-hang Command Failure Analyser

**Purpose**: Automatically analyse the first failed step of any command failure by finding the correct stage-specific log, parsing the failure content (error messages, event viewer entries, wrapper report JSONs), and producing an error snippet with expandable full log for the Non-hang Command Failure column (4th column, between AI-Trained Summary and Execution Messages). For devcon failures specifically, also look up unknown USB devices by VID/PID codes.

### Trigger Condition

The Non-hang Command Failure Analyser activates for any failure where the first failed step has **SubState=`CommandFailed`** (the step process exited with a non-zero return code). This covers all content wrapper failures: FurMark crashes, devcon device diffs, Galaxy test content errors, GBe failures, VPU inference errors, etc.

**Excluded** (not command failures — different root cause patterns):
- SubState=`Hang` → system hang, no step log to analyse
- SubState=`CommunicationLost` → target unreachable, no step log
- SubState=`Timeout` → step exceeded time limit, may have partial log
- SubState=`SystemReset` → unexpected reboot, no step log

For excluded SubStates, the column displays `(system hang — not a command failure)` or the appropriate reason in gray italics.

### Step 1: Identify the First Failed Step

From the testrun data (already fetched in enrichment step 4 via `mcp_nga-server_nga_get_testrun`):

1. **Read `FirstFailedStepName`** — This is the step that first failed in the test run (e.g., `Concurrency_Galaxy_PM_Reboot_Required_Traffic`, `udf_tposttest_devconcapture`, `CYCLESX_AIO_G3_PY3_GALAXY`).
2. **Read `FirstFailedStepErrorMessage`** — Contains the SubState (e.g., `CommandFailed`, `Hang`) and `CommandReturnCode`.
3. **Extract the stage** from the step context:
   - Step names encoding a stage prefix: `udf_tposttest_*` → PostTest, `udf_tpretest_*` → PreTest, `udf_ttest_*` → Test
   - Steps in `Steps[]` array: Match by step name to get `StageName` (PreTest/Test/PostTest/Cleanup)
   - Galaxy/Concurrency steps (e.g., `Concurrency_Galaxy_PM_*`, `CYCLESX_*`): Always in `Test` stage
4. **Check SubState** — If not `CommandFailed`, skip analysis and display the exclusion reason.

### Step 2: Find the Matching Log

The cleanup path ZIP contains logs organized by stage: `SUT/retry<N>/<Stage>/`. The agent MUST match the log to the correct stage folder.

**Strategy (in order of preference)**:

1. **UDF step log** — Call `mcp_nga-server_nga_get_udf_step_log` with `test_run_id` and `step_name`. Works for UDF steps (`udf_*`). Returns the step's stdout/stderr/wrapper log directly.
2. **Content wrapper report JSON** — Search the cleanup listing for `intel-content-<STEPNAME>*.report.json` in the matched stage folder. These are structured reports generated by NGA content wrappers (e.g., `intel-content-FURMARK#03_04_2026#19_57_37_787.report.json`). Parse the JSON for `insights[]` array which contains structured error messages with error codes, modules, and event viewer correlation.
3. **Content wrapper log** — Search for `<stepname>_<timestamp>.txt` in the matched stage folder (e.g., `furmark_20260403_195515066.txt`, `devcon_capture_20260406_060316286.txt`). These are the verbose wrapper execution logs.
4. **Galaxy log** — For Galaxy/Concurrency steps, read `GalaxyLog.log` from `SUT/retry0/Test/`. This is the comprehensive Galaxy execution log (can be 5-50MB). Search for the failing iteration and step name to find the error context. Use `mcp_nga-server_nga_read_cleanup_log` with byte offset to read the tail of large Galaxy logs.
5. **Cleanup stage log** — As a last resort, list files in `SUT/retry0/<Stage>/` and look for any log file whose name matches the step name pattern.

**Stage validation**: After locating the log, confirm it belongs to the correct stage. The wrapper log often contains `SET StageName=<Stage>` or the file path includes the stage name. If the stage doesn't match, search the correct stage folder instead.

### Step 3: Analyse the Failure

Parse the log content to extract the actual failure cause. The analysis varies by failure type:

#### Generic command failures
- Extract all `ERROR`, `CRITICAL`, `FAIL`, `EXCEPTION` lines from the log
- Look for Windows Event Viewer correlation: `APPLICATION_ERROR`, `Event_ID_1000`, error codes (`0xC*`)
- Look for process crash indicators: faulting module name, error code, process name
- Look for return code / exit code mentions
- Identify the specific workload/content that failed from the log context

#### Devcon failures (step name contains `devcon`)
- Extract diff block lines (lines starting with `-` or `+`) showing device comparison
- Extract `CRITICAL`, `ERROR`, `FAILED`, `problem:` lines
- **VID/PID lookup**: If the error involves USB VID/PID codes (pattern: `VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})`), look up the actual device:
  - Primary: `https://devicehunt.com/view/type/usb/vendor/<VID>/device/<PID>`
  - Fallback: `https://the-sz.com/products/usbid/index.php?v=<VID>&p=<PID>`
  - Cache results per VID/PID pair within the session
  - Skip lookup for `VID_0000` (unidentified device — no real vendor)
  - Output: `<Vendor Name> <Product Model> (VID_xxxx&PID_xxxx)`

#### FIO / disk I/O failures (step name contains `fio` or error mentions drive letter)
- **Drive letter to device mapping**: When the failure references a specific drive letter (e.g., `E:` in FIO FILE_TRANSFER_FAILURE), identify the physical device:
  1. Read `OriginalDriveList.log` from `SUT/retry0/PreTest/DevconCaptures/` — this CSV lists all drive letters with VolumeName, Description ("Local Fixed Disk", "Removable Disk"), and Filesystem.
  2. Read `OriginalCapture.log` from `SUT/retry0/PreTest/DevconCaptures/` — search for `SCSI\DISK` and `USBSTOR\DISK` entries to find physical disk devices (e.g., `SCSI\DISK&VEN_NVME&PROD_SAMSUNG_MZVLC1T0`, `SCSI\DISK&VEN_ASMT&PROD_ASM236X_NVME`, `USBSTOR\DISK&VEN__USB&PROD__SANDISK_3.2GEN1`).
  3. Cross-reference: Match the drive letter to a physical device. Removable disks (Description="Removable Disk") typically map to USB devices (`USBSTOR\DISK`). Local Fixed Disks map to `SCSI\DISK` entries (NVMe or USB-attached-SCSI via bridge chips like ASMedia ASM236x).
  4. **VID/PID lookup for unknown devices**: If the disk device has a VID/PID pattern in its hardware ID (e.g., `VEN_ASMT&PROD_ASM236X` for USB-to-NVMe bridge, or `VID_xxxx&PID_xxxx` for USB storage), look up the vendor/product using:
     - Primary: `https://devicehunt.com/view/type/usb/vendor/<VID>/device/<PID>`
     - Fallback: `https://the-sz.com/products/usbid/index.php?v=<VID>&p=<PID>`
     - For SCSI vendor names (e.g., `VEN_ASMT`), search the vendor name directly (ASMedia Technology = ASM236x NVMe-to-USB bridge controller).
  5. Output as a drive identification card in the column: `💾 Drive E: → <Device Name> (<Hardware ID>) — <Description>` (e.g., `💾 Drive E: → Samsung MZVLC1T0 NVMe (SCSI\DISK&VEN_NVME&PROD_SAMSUNG_MZVLC1T0) — Local Fixed Disk`)
- Extract FIO error details: exit code, drive pass/fail status, I/O error messages (`windows error NNN`, `io_u error`), fio version, engine type
- Identify whether the failure is infra-related (single drive I/O error = likely bad disk/connection) or test-related (all drives fail = possible system issue)

#### Galaxy/Concurrency content failures
- Parse the content wrapper report JSON (`intel-content-*.report.json`) for structured `insights[]`
- Correlate with Windows Event Viewer entries (Event ID 1000/1002) captured by the wrapper
- Identify which specific workload crashed (FurMark, Prime95, GBe, etc.) and the error details
- Note the runtime vs expected runtime if the wrapper detected premature termination
- **Per-workload failure log retrieval** (see Learning #82): For Galaxy concurrency sustained stress failures with multiple failing workloads (e.g., FFMPEG, FIO, ChecksumFT), fetch the **last failed iteration's log** for each workload from the cleanup ZIP at `SUT/retry0/PostTest/Test/<workload>_<timestamp>.txt`. Use `mcp_nga-server_nga_read_cleanup_log` with byte offset to read the tail of large logs (>100KB). Save locally to `output/<workload>_last_fail.txt`. Analyse each log for root cause keywords (e.g., FFMPEG: `Could not enumerate video devices`, FIO: return code 0x05, ChecksumFT: checksum mismatch). Embed each log in the Non-hang Command Failure column as a collapsible `<details>` element with an "Expand Full Log" button.
- **Evtx disk error identification** (see Learning #83): When evtx shows disk controller errors referencing `\Device\HarddiskN`, identify the physical disk by reading `OriginalDriveList.log` and `original_device_report.json` from `SUT/retry0/PreTest/DevconCaptures/` in the cleanup ZIP. Map Harddisk index (0-based) to the physical disk enumeration order. Display a disk identification card prepended to the System.evtx column showing: disk errors timeline, drive letter map (all drives), and correlation note linking disk errors to workload failures.

### Step 4: Extract Error Snippet

From the log content, extract lines containing error keywords for the inline snippet:

1. **Scan all lines** for keywords: `ERROR`, `CRITICAL`, `FAIL`, `EXCEPTION`, `APPLICATION_ERROR`, `FATAL` (case-insensitive).
2. **Collect up to 20 matching lines** in their original order.
3. **Fallback**: If zero error lines are found, collect the **last 20 lines** of the log as fallback context.
4. **Store the full log** separately for the Expand button.

The snippet provides immediate visibility into the failure cause. The full log is available via the Expand Full Log button for deeper investigation.

### Step 5: Format for HTML Column

The Non-hang Command Failure column cell contains these elements in order:

1. **Step + Stage badge**: `<div style="margin-bottom:4px"><span style="background:<color>;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold"><Stage></span> <code style="font-size:12px"><StepName></code> <span style="color:#888;font-size:11px">(ReturnCode: N)</span></div>`
   - Stage colors: PreTest=blue `#2196F3`, Test=orange `#FF9800`, PostTest=purple `#9C27B0`, Cleanup=gray `#607D8B`.
2. **Error snippet**: `<div style="max-height:150px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;padding:4px;margin:4px 0"><pre style="font-family:Consolas,monospace;font-size:0.75rem;margin:0;white-space:pre-wrap">...error lines...</pre></div>` — Shows up to 20 error/critical/fail lines from the log, color-coded inline. If no error lines found, shows last 20 lines of log as fallback.
3. **Device ID card** (devcon failures): `<div style="background:#e3f2fd;padding:6px 10px;border-radius:4px;margin:4px 0;font-size:12px">🔍 Device: <b>Vendor</b> Model (VID_xxxx&PID_xxxx)</div>`
3b. **Drive identification card** (FIO/disk I/O failures referencing a drive letter): `<div style="background:#fff3e0;padding:6px 10px;border-radius:4px;margin:4px 0;font-size:12px">💾 Drive E: → <b>Samsung MZVLC1T0 NVMe</b> (SCSI\DISK&VEN_NVME&PROD_SAMSUNG_MZVLC1T0) — Local Fixed Disk</div>`. Obtained by reading `OriginalDriveList.log` + `OriginalCapture.log` from `SUT/retry0/PreTest/DevconCaptures/` (see Step 3 → FIO/disk I/O failures). If the device has a VID/PID pattern, also perform a VID/PID web lookup to identify the vendor/product.
4. **Expand Full Log button**: `<button onclick="openLogModal(this)" style="...">Expand Full Log (N lines)</button>` — Opens a **draggable/resizable full-screen modal** containing the **entire** step log in a `<pre>` container. The full log content is stored in a hidden `<div>` sibling. Key lines are highlighted: `ERROR`/`CRITICAL`/`FAIL` in bold red (`#c62828`), `WARNING` in orange (`#e65100`), `APPLICATION_ERROR`/`Event_ID` in red background (`#fde8e8`), diff `-` lines in green (`#2e7d32`), diff `+` lines in red (`#c62828`). **The full log is NOT shown inline** — only via the Expand button.

---

## Workflow

1. **Parse user request** — Extract suite pattern, test cycle, and any filters (e.g., no sighting).
2. **Query NGA live** — Query NGA with the constructed OData filter to collect all failure records. Deduplicate by FailureId.
3. **Deduplicate by TestRunId** — Group failures by `TestRunComposite.TestRunId`. For each group, keep only the failure with the latest `SubmittedDateTime`. Log: `"OData returned M failure records → N unique test runs after dedup"`. This step reduces redundant rows and matches the NGA UI count.
4. **Enrich via NGA REST APIs** — Call `mcp_nga-server_nga_get_testrun` for each unique `TestRunId` to get `Result.ResultCode` (Run State), cleanup path, `FirstFailedStepName`, `FirstFailedStepErrorMessage` (contains SubState and CommandReturnCode), and `Steps[]` array (for stage mapping). Since we already deduplicated by TestRunId, each enrichment call maps 1:1 to a report row.
5. **Collect Axon insights** — For failures with non-null `DebugSnapshotId`:
   - Call `mcp_axon-server_get_axon_report_content` for each record to get the raw SVTools JSON (29MB+, requires double-parse `json.loads(data['result'])`). Extract all insights from `sub_reports` tree (recursive walk) plus root-level `data['insights']`. Each insight has: type, message, location, ip_domain, mcacod, mcacod_decode, mscod, mscod_decode, uc, source/path, insight_index.
   - **Assign priority using `TYPE_PREFIX_PRIORITY` mapping** (default): Map each insight's `type` field to a priority using longest-prefix-first matching: `HW.STUCK_TRANSACTION→1, HW.MCE→1, HW.HANG→1, HW.PORT_STUCK→1, HW.IFA→1, HW.UNEXPECTED_RESET→2, HW.LINK→2, SW.POWER→6, PLATFORM→10, SW→10, HW→10`. Default priority for unmatched types: 10.
   - **Do NOT call `mcp_genimcp_AxonTool`** unless the user explicitly requests genimcp-based priority enrichment. The type-prefix mapping provides reliable priority assignment without the truncation issues and extra API calls of genimcp.
   - Store compiled results (structured insights with all fields + priority) for injection into the Statuscope Summary column.
6. **Run Non-hang Command Failure Analyser** — For each failure, check the first failed step's SubState from step 4 enrichment:
   - If SubState=`CommandFailed`: Identify the first failed step name, extract the stage, find the matching log in the correct stage folder (the log MUST reside in `SUT/retry<N>/<StageName>/` matching the step's stage — e.g., PostTest steps → `SUT/retry0/PostTest/`, Test steps → `SUT/retry0/Test/`). Use the log retrieval strategy (UDF step log → content wrapper report JSON → content wrapper log → Galaxy log → cleanup stage log), extract error snippet (up to 20 error lines), and store the full log for the Expand button.
   - **Devcon-specific enrichment**: If the step name contains `devcon`, additionally extract VID/PID codes from diff lines and look up device vendor/model via web lookup.
   - **Galaxy/Concurrency-specific enrichment**: If the step is a Galaxy content step (e.g., `Concurrency_Galaxy_*`, `CYCLESX_*`), parse the content wrapper report JSON for structured insights and correlate with the Galaxy log tail.
   - If SubState is NOT `CommandFailed` (hang/timeout/communication lost), store `(system hang — not a command failure)` for the column.
6b. **Generate AI-Trained Summary** — After ALL other enrichment columns are populated (steps 4-6), generate the AI-Trained Summary for each failure by cross-referencing all available data: Statuscope insights (P1/P2 types, MCE codes), BSOD bugcheck codes, System.evtx critical events, Execution message patterns (hang flow, recovery, iteration counts), and Non-hang Command Failure logs (crash modules, error codes). Produce: root cause classification badge, one-line summary, 2-4 key evidence bullets citing source columns, and confidence indicator **with reasoning** (e.g., "High — 4 independent sources agree (FIO report, step log, drive mapping, evtx absence)").
7. **Parse response & filter Passed** — Merge deduplicated failure records with enriched Run State, SubmittedDateTime, cleanup paths from REST APIs, Axon insights, and Non-hang Command Failure analysis results. **Then discard all failures where Run State = `Passed`** (unless the user explicitly asked to include them). Log the count of excluded Passed failures for the summary.
8. **Generate full HTML report** — Build the report with ALL 8 columns populated in this order: #, Failure Info, AI-Trained Summary, Non-hang Command Failure, Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary. For each failure:
   - Generate AI-Trained Summary from cross-referenced enrichment data
   - Fetch execution messages via NGA TestRunMessage API using `testRunId` (fallback: read `ExecutionMessages.csv` from cleanup path)
   - Extract `System.evtx` from cleanup ZIP (Critical Level=1 + Error Level=2, ±1h window)
   - Extract `bsod.log` from cleanup ZIP
   - Inject Axon insights with priority color coding
   - Inject Non-hang Command Failure results (step+stage badge, error snippet with up to 20 error lines, device ID card if devcon, Expand Full Log button with hidden full log content)
   - Use `Start-Job` with 90s timeout for remote ZIP access
   - Cache ZIP results per cleanup path to avoid redundant access
   Save as `gen_wl_report_compact.ps1` and execute.
9. **Post-process: color Execution Messages (CSV fallback only)** — If any failures used CSV fallback for execution messages (no API data), run `color_execmsg.ps1` to apply keyword-based color coding. Skip this step when all failures used API-sourced messages (color coding is built into the inline HTML table).
10. **Save and open** — Write to `output/` and auto-open in browser.

**Important**: All 8 columns must be populated in every report. Do NOT generate a "base" report with `(skipped)` placeholders and post-process later. The single `gen_wl_report_compact.ps1` script must produce the complete report with all columns filled.

---

## Usage Examples

### Example 1: All failures without sighting in a cycle
> "find all failures without sightingid in testcycle package.nvl-s-28-ext-b0.val_es2.IVE.NVL_S28_B0_ES2_WW09.5"

Query: filter by test cycle + `SightingId eq null`, no suite filter.

### Example 2: Failures without sighting for a specific suite
> "find all failures without sightingID for NVL-S_Fullchip* in cycle RFP_NVL_S28_B0_ES2_North"

Query: filter by test cycle + suite contains `NVL-S_Fullchip` + `SightingId eq null`.

### Example 3: All failures in a suite + cycle (including sighted)
> "show ALL failures for NVL-S_Fullchip* in cycle RFP_NVL_S28_B0_ES2_North"

Query: filter by test cycle + suite contains `NVL-S_Fullchip`, no `SightingId eq null` filter (user explicitly said "ALL").

---

## Guardrails

- **Never use local scripts** (`suite_cycle_failures.py`, `test_cycle_failures.py`, etc.) for querying. Always use the NGA MCP server (`mcp_nga-server_nga_search`).
- **Never reuse cached data** from `output/` folder or prior results.
- **Always generate HTML** — even if the result is 0 failures, produce an HTML report stating so.
- **Escape HTML** — all user-facing text in the HTML must be HTML-encoded to prevent XSS.
- **No Unicode dashes in PS1 files** — PowerShell 5.1 reads `.ps1` files using the system's default ANSI code page (Windows-1252), not UTF-8. Em dashes (`—`, U+2014) and other non-ASCII characters become mojibake (e.g., `â€"`). In generated `.ps1` scripts: use `&mdash;` for em dashes inside **raw HTML** string literals (not passed through `HtmlEncode`), and `--` for comments, plain text, or strings that will be HTML-encoded (otherwise `&mdash;` gets double-escaped to `&amp;mdash;`). Never write literal `—`, `→`, `←`, or other non-ASCII punctuation into `.ps1` files.

---

## Git Tracking

**Whenever this agent spec or any of its required runtime files are modified, always `git add`, `git commit`, and `git push` ALL changed files before finishing.** This ensures other users can access the latest version from the remote.

### Required Files (all embedded in this agent spec)

All 9 runtime scripts are embedded inline in the **Embedded Runtime Scripts** section below. When the agent runs, it **self-extracts** these files to the workspace root before execution. No external script files are required.

| # | File | Purpose | Embedded |
|---|------|---------|----------|
| 1 | `.ai/MYS_CVE/AnalysisTriage/unsighted_analyser.agent.md` | Agent spec (this file) | N/A |
| 2 | `gen_wl_report_compact.ps1` | Main HTML report template | Yes |
| 3 | `get_testrun_messages.py` | NGA TestRunMessage API helper (MSAL auth) | Yes |
| 4 | `extract_all_axon_insights.py` | SVTools insight extraction from Axon raw JSON | Yes |
| 5 | `color_execmsg.ps1` | Execution messages keyword color coding | Yes |
| 6 | `build_insight_table_nvlp.py` | NVL_P insight table with priority mapping | Yes |
| 7 | `build_insight_table_hx_sst.py` | HX SST insight table with priority mapping | Yes |
| 8 | `add_execmsg_column.ps1` | Inject execution messages column | Yes |
| 9 | `add_axon_column.ps1` | Inject Axon/SVTools insights column | Yes |
| 10 | `build_axon_insights_with_priority.ps1` | Compile Axon insights with priority | Yes |

### Self-Extraction Rule

**Before running any workflow**, check if each required runtime file exists in the workspace root. If any file is missing, extract it from the corresponding fenced code block in the **Embedded Runtime Scripts** section below and write it to the workspace root. Use `create_file` or equivalent to write the file content exactly as shown in the code block. This ensures the agent is fully self-contained and does not depend on external files being pre-deployed.

### Commit & Push Rules

1. After ANY edit to this agent spec or any file in the table above, run:
   ```powershell
   git add <changed files>
   git commit -m "<descriptive message>"
   git push origin main
   ```
2. If `git push` is rejected (remote has new commits), rebase first: `git pull --rebase origin main` then push.
3. If a **new** runtime script is created that this agent depends on, add it to the table above and commit both the new file and the updated agent spec.
4. **Never leave modified tracked files uncommitted** at the end of a task that changes agent behavior.

---

## Agent Commands

### `audit`

When the user says **"audit"**, perform the following steps **every time**:

1. **Read the Required Files table** (above) to get the list of all 9 runtime scripts and their filenames.
2. **Locate all `### File N:` embedded sections** in this agent spec via grep.
3. **For each of the 9 embedded files**, compare the embedded code block (content between the ``` fences) against the external file on disk in the workspace root:
   - **MATCH** — Embedded and disk are identical (ignore BOM and trailing whitespace).
   - **STALE** — Content differs. Note whether the difference is only in data sections (e.g. `$failures`, `$failureData`, `GENIMCP_PRIORITIES`, `Add-Record` calls) vs structural/logic code. Data-bearing files are expected to have production data on disk but empty templates embedded — this is by design.
   - **MISSING** — External file does not exist on disk.
4. **Report results** as a summary table:

   | File # | Name | Embedded Lines | Disk Lines | Status | Notes |
   |---|---|---|---|---|---|
   | 1 | filename.py | X | Y | MATCH/STALE/MISSING | brief note |

5. State totals: how many MATCH, STALE, MISSING.
6. If any file has **structural/logic differences** (not just data), flag it for re-embedding.

---

## Embedded Runtime Scripts

All 9 runtime scripts are embedded below as fenced code blocks. The agent self-extracts these to the workspace root before execution if they are missing. **When modifying any function logic, update BOTH the embedded code block below AND the external file (if it exists), then git commit and push.**

### File 1: `get_testrun_messages.py`

```python
"""Fetch TestRunMessage from NGA Results API and output as JSON.

Usage:  python get_testrun_messages.py <project> <testRunId>
Output: JSON array of {TimeStamp, Source, Title, Message, SystemName, StageName, StepIndex, Level} sorted by TimeStamp desc.
"""
import sys, json, os, requests, urllib3, msal

urllib3.disable_warnings()
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(k, None)

if len(sys.argv) < 3:
    print("Usage: python get_testrun_messages.py <project> <testRunId>", file=sys.stderr)
    sys.exit(1)

project = sys.argv[1]
test_run_id = sys.argv[2]

# Auth
APP_ID = "5010f2b6-5feb-4de3-89a2-dba1172b07f8"
APP_SECRET = "f_K8Q~uTMpKk7lwQyNPWl0PFL-IGFVdTEhPkhdyX"
SCOPE = ["6af0841e-c789-4b7b-a059-1cec575fbddb/.default"]
AUTHORITY = "https://login.microsoftonline.com/intel.onmicrosoft.com"

app = msal.ConfidentialClientApplication(APP_ID, authority=AUTHORITY, client_credential=APP_SECRET)
token_result = app.acquire_token_for_client(scopes=SCOPE)
if "access_token" not in token_result:
    print(json.dumps({"error": "auth_failed", "detail": str(token_result.get("error_description", ""))}))
    sys.exit(1)

s = requests.Session()
s.verify = False
s.proxies = {'http': '', 'https': ''}
s.headers.update({
    "Authorization": f"Bearer {token_result['access_token']}",
    "Content-Type": "application/json"
})

url = f"https://nga-prod.laas.icloud.intel.com/Results/{project}/api/TestRun/TestRunMessage"
r = s.post(url, json={"Ids": [test_run_id]})
if r.status_code != 200:
    print(json.dumps({"error": f"api_{r.status_code}", "detail": r.text[:500]}))
    sys.exit(1)

import re
def strip_html(text):
    """Remove HTML tags from message text."""
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text).strip()

msgs = r.json()
out = []
for m in msgs:
    out.append({
        "TimeStamp": m.get("TimeStamp", ""),
        "Source": m.get("MessageSource", ""),
        "Title": m.get("Title", ""),
        "Message": strip_html(m.get("Message", "")),
        "SystemName": m.get("SystemName", ""),
        "StageName": m.get("StageName", ""),
        "StepIndex": m.get("StepIndex", ""),
        "Level": m.get("Level", ""),
    })

out.sort(key=lambda x: x["TimeStamp"], reverse=True)
print(json.dumps(out))
```

### File 2: `extract_all_axon_insights.py`

```python
"""Extract raw SVTools insights from axon-server report content files.

Reads axon report content JSON files (saved from mcp_axon-server_get_axon_report_content),
extracts all insights recursively from sub_reports tree, and outputs compiled JSON.

Usage: python extract_all_axon_insights.py <enriched_json> <axon_data_dir> <output_json>

The axon_data_dir should contain files named <debugSnapshotId>.json
(output from mcp_axon-server_get_axon_report_content).
"""
import json, os, sys, re

INSIGHT_FIELDS = ['type', 'message', 'location', 'ip_domain', 'mcacod',
                  'mcacod_decode', 'mscod', 'mscod_decode', 'uc']

# Type-prefix fallback for priority assignment
TYPE_PREFIX_PRIORITY = [
    ('HW.STUCK_TRANSACTION', 1),
    ('HW.MCE', 1),
    ('HW.HANG', 1),
    ('HW.PORT_STUCK', 1),
    ('HW.IFA', 1),
    ('HW.UNEXPECTED_RESET', 2),
    ('HW.LINK', 2),
    ('SW.BSOD', 2),
    ('SW.POWER', 6),
    ('PLATFORM', 10),
    ('SW', 10),
    ('HW', 10),
]


def collect_insights(node, path="root"):
    """Recursively walk sub_reports and collect all insights."""
    results = []
    if 'insights' in node and node['insights']:
        for idx, ins in enumerate(node['insights']):
            record = {
                'source_path': path,
                'insight_index': idx,
            }
            for k, v in ins.items():
                record[k] = v
            for f in INSIGHT_FIELDS:
                if f not in record:
                    record[f] = None
            results.append(record)
    if 'sub_reports' in node and node['sub_reports']:
        for i, sr in enumerate(node['sub_reports']):
            sr_name = sr.get('name', f'idx_{i}')
            results.extend(collect_insights(sr, f"{path}.{sr_name}"))
    return results


def get_summary(inner):
    """Extract classifier/summary text from root."""
    for key in ['summary', 'classifier', 'status']:
        if key in inner and inner[key]:
            return inner[key]
    return None


def normalize_msg(msg):
    """Normalize message for matching."""
    if not msg:
        return ''
    return re.sub(r'\s+', ' ', msg.replace('\u00a0', ' ').replace('\u200b', '')).strip()


def assign_type_prefix_priority(insight_type):
    """Assign priority based on insight type prefix."""
    if not insight_type:
        return 10
    t = insight_type.upper()
    for prefix, priority in TYPE_PREFIX_PRIORITY:
        if t.startswith(prefix):
            return priority
    return 10


def process_axon_file(filepath):
    """Process a single axon report content JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # Double-parse: result field is often a JSON string
    content = raw
    if isinstance(raw, dict) and 'result' in raw:
        content = raw['result']
    if isinstance(content, str):
        content = json.loads(content)

    summary = get_summary(content)
    insights = collect_insights(content)
    return summary, insights


def merge_priorities(insights, priority_map):
    """Merge priority values from genimcp into raw insights."""
    for ins in insights:
        msg_norm = normalize_msg(ins.get('message', ''))
        if msg_norm in priority_map:
            ins['priority'] = priority_map[msg_norm]
        else:
            # Try partial match
            matched = False
            for pm_msg, pm_pri in priority_map.items():
                if pm_msg and msg_norm and (pm_msg in msg_norm or msg_norm in pm_msg):
                    ins['priority'] = pm_pri
                    matched = True
                    break
            if not matched:
                ins['priority'] = assign_type_prefix_priority(ins.get('type', ''))
    return insights


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python extract_all_axon_insights.py <enriched_json> <axon_data_dir> <output_json>")
        sys.exit(1)

    enriched_path = sys.argv[1]
    axon_dir = sys.argv[2]
    output_path = sys.argv[3]

    with open(enriched_path, 'r', encoding='utf-8') as f:
        enriched = json.load(f)

    results = {}
    for fail in enriched['failures']:
        fid = fail['failureName']
        dsid = fail.get('debugSnapshotId')
        if not dsid:
            results[fid] = {'axon': None, 'summary': '', 'insights': []}
            continue

        axon_file = os.path.join(axon_dir, f'{dsid}.json')
        if not os.path.exists(axon_file):
            print(f"  {fid}: no axon file for {dsid}", file=sys.stderr)
            results[fid] = {'axon': dsid, 'summary': '(no SVTools report file)', 'insights': []}
            continue

        try:
            summary, insights = process_axon_file(axon_file)
            # Sort by type-prefix priority for now (genimcp priorities merged later)
            for ins in insights:
                ins['priority'] = assign_type_prefix_priority(ins.get('type', ''))
            # Deduplicate by (type, message) — same insight from multiple sub_reports
            seen = set()
            deduped = []
            for ins in insights:
                key = (normalize_msg(ins.get('type', '')), normalize_msg(ins.get('message', '')))
                if key not in seen:
                    seen.add(key)
                    deduped.append(ins)
            insights = deduped
            insights.sort(key=lambda x: (x.get('priority', 10), x.get('message', '')))

            results[fid] = {
                'axon': dsid,
                'summary': summary or '',
                'insights': insights,
            }
            print(f"  {fid}: {len(insights)} insights, summary={summary}", file=sys.stderr)
        except Exception as e:
            print(f"  {fid}: error processing {dsid}: {e}", file=sys.stderr)
            results[fid] = {'axon': dsid, 'summary': f'(error: {e})', 'insights': []}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(results)} records to {output_path}", file=sys.stderr)
```

### File 3: `color_execmsg.ps1`

```powershell
###############################################################################
# color_execmsg.ps1
# Post-process HTML report to color Execution Messages lines like NGA UI
# Colors: Failed=red, Aborted=orange, Passed/Completed=green, Running=blue
# The >>> matched line gets bold + yellow-highlight
###############################################################################
$ErrorActionPreference = 'Continue'

$reportDir = Join-Path $PSScriptRoot 'output'
$htmlFile = Get-ChildItem $reportDir -Filter 'wl_failures_*.html' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $htmlFile) { Write-Error "No report found"; exit 1 }
Write-Host "Processing: $($htmlFile.FullName)"

$html = Get-Content $htmlFile.FullName -Raw -Encoding UTF8

# Process each exec cell's <pre> content
$cellCount = 0
$html = [regex]::Replace($html, '(?s)(<td class="exec"><pre>)(.*?)(</pre></td>)', {
    param($m)
    $prefix = $m.Groups[1].Value
    $content = $m.Groups[2].Value
    $suffix = $m.Groups[3].Value
    $script:cellCount++

    # Skip placeholder cells
    if ($content -match '^\(skipped|^\(no |^\(empty|^\(CSV from') {
        return $m.Value
    }

    # Split by newlines, color each line
    $lines = $content -split "`n"
    $colored = @()
    foreach ($rawLine in $lines) {
        $line = $rawLine.TrimEnd("`r")
        if (-not $line.Trim()) { $colored += $line; continue }

        # Detect the >>> matched line (raw or HTML-encoded)
        $isMatch = $line -match '^>>>|^&gt;&gt;&gt;'

        # Determine color based on keywords
        $bg = ''
        $fontColor = ''
        $weight = ''

        if ($line -match '\bFailed\b') {
            $bg = '#fde8e8'
            $fontColor = '#c0392b'
        }
        elseif ($line -match '\bAborted\b') {
            $bg = '#fff3cd'
            $fontColor = '#d35400'
        }
        elseif ($line -match '\bPassed\b' -or $line -match '\bCompleted\b') {
            $bg = '#e8f5e9'
            $fontColor = '#27ae60'
        }
        elseif ($line -match '\bRunning\b') {
            $bg = '#e3f2fd'
            $fontColor = '#2471a3'
        }
        elseif ($line -match '\bScheduled\b' -or $line -match '\bWaiting\b') {
            $fontColor = '#7f8c8d'
        }

        # >>> matched line gets extra highlight
        if ($isMatch) {
            $weight = 'font-weight:700;'
            if (-not $bg) { $bg = '#fff9c4' }
        }

        if ($bg -or $fontColor -or $weight) {
            $style = ''
            if ($bg) { $style += "background:$bg;" }
            if ($fontColor) { $style += "color:$fontColor;" }
            if ($weight) { $style += $weight }
            $colored += "<span style='display:block;$style'>$line</span>"
        } else {
            $colored += $line
        }
    }

    return "$prefix$($colored -join "`n")$suffix"
})

[System.IO.File]::WriteAllText($htmlFile.FullName, $html, [System.Text.Encoding]::UTF8)
Write-Host "Colored $cellCount exec msg cells"
Write-Host "Output: $($htmlFile.FullName)"
Start-Process $htmlFile.FullName
```

### File 4: `add_axon_column.ps1`

```powershell
###############################################################################
# add_axon_column.ps1
# Post-processes the HTML report to REPLACE the SVTools Insight column (10th)
# with complete verbatim insights from fc_axon_insights.json
###############################################################################

$ErrorActionPreference = 'Continue'

$reportDir = Join-Path $PSScriptRoot 'output'

# Find the most recent report
$htmlFile = Get-ChildItem $reportDir -Filter 'wl_nosighting_NVL-S_Fullchip_allcycles_*.html' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $htmlFile) { Write-Error "No report found"; exit 1 }
Write-Host "Processing: $($htmlFile.FullName)"

# Load full Axon insights from JSON
$jsonPath = Join-Path $reportDir 'fc_axon_insights.json'
if (-not (Test-Path $jsonPath)) { Write-Error "Insights JSON not found: $jsonPath"; exit 1 }
$axonRaw = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json

# Build lookup: failureId(8-char) -> { summary, insights[] }
$axonData = @{}
foreach ($prop in $axonRaw.PSObject.Properties) {
    $axonData[$prop.Name] = @{
        summary  = $prop.Value.summary
        insights = @($prop.Value.insights)
        axon     = $prop.Value.axon
    }
}
Write-Host "Loaded $($axonData.Count) Axon insight records"

$html = Get-Content $htmlFile.FullName -Raw -Encoding UTF8

# Check if SVTools column header already exists
$hasAxonHeader = $html -match 'SVTools Insight'

if (-not $hasAxonHeader) {
    # Add column header (10th column)
    $thAxon = @'
<th draggable="true" ondragstart="dsDrag(event,9)" ondragover="allowDrop(event)" ondrop="doDrop(event,9)"><div class="hdr" onclick="sortTable(9)">SVTools Insight<span class="sort-ind"></span></div><input class="filter-input" oninput="filterTable()" placeholder="..."><div class="resize-grip" onmousedown="startResize(event,9)"></div></th>
'@
    $html = $html -replace '(</tr>\s*</thead>)', "$thAxon`$1"
    Write-Host "Added SVTools Insight header"
}

# First strip existing axon cells if present (so we can re-inject fresh ones)
$html = [regex]::Replace($html, '(?s)\s*<td class="axon">.*?</td>', '')

# Process each row - add Axon cell before </tr>
$rowPattern = '(?s)(<tr>\s*<td class="num">\d+</td>.*?<td><a href=".+?">([a-f0-9]{8})</a>.*?)(</tr>)'
$matchCount = 0
$dataCount = 0
$html = [regex]::Replace($html, $rowPattern, {
    param($m)
    $fid = $m.Groups[2].Value
    $before = $m.Groups[1].Value
    $closeTr = $m.Groups[3].Value
    $script:matchCount++

    $cellContent = '(no SVTools data)'
    if ($axonData.ContainsKey($fid)) {
        $a = $axonData[$fid]
        $script:dataCount++
        $summary = [System.Net.WebUtility]::HtmlEncode($a.summary)
        $axonId = $a.axon -replace '-.*$', ''  # short 8-char prefix
        $reportUrl = "https://axonsv.app.intel.com/apps/record-viewer/$($a.axon)/intel-svtools-report-v1"

        # Build each insight as a separate line
        $lines = @()
        foreach ($msg in $a.insights) {
            $lines += [System.Net.WebUtility]::HtmlEncode($msg)
        }
        $insightBlock = $lines -join "`n"

        # Priority 1 = classifier recognized a specific failure (not "No insights recognized")
        $isPriority1 = $a.summary -notmatch 'No insights recognized'
        $linkColor = if ($isPriority1) { '#7b2d8e' } else { '#2980b9' }

        $cellContent = "<div style='max-height:300px;overflow-y:auto;font-size:11px;'>" +
            "<b><a href='$reportUrl' target='_blank' style='color:$linkColor;'>$summary</a></b>" +
            "<pre style='margin-top:4px;white-space:pre-wrap;word-break:break-word;font-size:10px;color:#333;'>$insightBlock</pre></div>"
    }

    return "$before`n  <td class=`"axon`">$cellContent</td>`n$closeTr"
})

[System.IO.File]::WriteAllText($htmlFile.FullName, $html, [System.Text.Encoding]::UTF8)
Write-Host "Updated SVTools column: $matchCount rows processed, $dataCount with insights"
Write-Host "Output: $($htmlFile.FullName)"
Start-Process $htmlFile.FullName
```

### File 5: `add_execmsg_column.ps1`

```powershell
# Add Execution Messages column to the last generated report
# Reads ExecutionMessages.csv from each failure's cleanup path,
# finds ±5 lines around the submitted date, and injects a new column.

$srcHtml = 'output\wl_failures_only_NVL_S28_B0_ES2_WW09_5_20260401_235929.html'

# Failure data: FID -> { CP (cleanup path), SD (submitted date UTC ISO), SN (first sig step name) }
$failureData = @{
    # NOTE: This is a template. The agent populates $failureData dynamically per query.
}

function HtmlEnc($s) { if (-not $s) { return "" }; return [System.Net.WebUtility]::HtmlEncode($s) }

# Cache CSV reads per cleanup path (multiple failures may share same CP)
$csvCache = @{}

function Get-ExecMsgContext($cp, $sdUtc, $stepName) {
    $csvPath = Join-Path $cp 'ExecutionMessages.csv'
    if (-not (Test-Path $csvPath -ErrorAction SilentlyContinue)) {
        Write-Host "  No ExecutionMessages.csv found"
        return "(no ExecutionMessages.csv)"
    }

    # Cache
    if (-not $csvCache.ContainsKey($cp)) {
        Write-Host "  Reading CSV..."
        $csvCache[$cp] = Get-Content $csvPath -ErrorAction SilentlyContinue
    }
    $lines = $csvCache[$cp]
    if (-not $lines -or $lines.Count -le 1) { return "(empty CSV)" }

    $bestIdx = -1

    # Strategy 1: Find the Failed/Aborted line matching the step name from signature
    if ($stepName) {
        # Extract the test step function name (first word before " failed with")
        $funcName = $stepName -replace '\s+failed\s+with.*', '' -replace '\s+Failed\..*', ''
        # Search for a line with this function name and Failed/Aborted
        for ($i = $lines.Count - 1; $i -ge 1; $i--) {
            if ($lines[$i] -like "*$funcName*Failed*" -or $lines[$i] -like "*$funcName*Aborted*") {
                $bestIdx = $i
                Write-Host "  Matched by step name '$funcName' at line $i"
                break
            }
        }
    }

    # Strategy 2: Fallback to closest timestamp match (CSV timestamps are UTC)
    if ($bestIdx -lt 0) {
        $targetDt = [datetime]::Parse($sdUtc, $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
        $targetLocal = $targetDt
        $bestDiff = [double]::MaxValue
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^(\d{2}:\d{2}:\d{2}\s+-\s+\d{1,2}\s+\w{3}\s+\d{4})') {
                try {
                    $lineDt = [datetime]::ParseExact($matches[1], 'HH:mm:ss - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
                    $diff = [math]::Abs(($lineDt - $targetLocal).TotalSeconds)
                    if ($diff -lt $bestDiff) {
                        $bestDiff = $diff
                        $bestIdx = $i
                    }
                } catch {}
            }
        }
        if ($bestIdx -ge 0) { Write-Host "  Matched by timestamp at line $bestIdx (diff: $([math]::Round($bestDiff))s)" }
    }

    if ($bestIdx -lt 0) { return "(could not match)" }

    # Validate: check timestamp diff between matched line and submitted date
    $targetDtCheck = [datetime]::Parse($sdUtc, $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
    if ($lines[$bestIdx] -match '^(\d{2}:\d{2}:\d{2}\s+-\s+\d{1,2}\s+\w{3}\s+\d{4})') {
        try {
            $matchDt = [datetime]::ParseExact($matches[1], 'HH:mm:ss - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
            $matchDiff = [math]::Abs(($matchDt - $targetDtCheck).TotalSeconds)
            if ($matchDiff -gt 3600) {
                Write-Host "  WARN: Matched line is $([math]::Round($matchDiff))s (~$([math]::Round($matchDiff/3600,1))h) from submitted date - CSV from different run" -ForegroundColor Yellow
                return "(CSV from different run)"
            }
        } catch {}
    }

    # Extract ±5 lines (skip header at index 0)
    $startIdx = [math]::Max(1, $bestIdx - 5)
    $endIdx = [math]::Min($lines.Count - 1, $bestIdx + 5)

    $result = @()
    $tz = [System.TimeZoneInfo]::Local
    for ($i = $startIdx; $i -le $endIdx; $i++) {
        $prefix = if ($i -eq $bestIdx) { ">>> " } else { "    " }
        $converted = $lines[$i]
        if ($converted -match '^(\d{2}:\d{2}:\d{2}\s+-\s+\d{1,2}\s+\w{3}\s+\d{4})') {
            $utcTs = $matches[1]
            try {
                $utcDt = [datetime]::ParseExact($utcTs, 'HH:mm:ss - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal)
                $localDt = [System.TimeZoneInfo]::ConvertTimeFromUtc($utcDt, $tz)
                $localTs = $localDt.ToString('h:mm:ss tt - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
                $converted = $converted -replace [regex]::Escape($utcTs), $localTs
            } catch {}
        }
        $result += "${prefix}$converted"
    }

    Write-Host "  Found match at line $bestIdx (diff: $([math]::Round($bestDiff))s), showing lines $startIdx-$endIdx"
    return ($result -join "`n")
}

# --- Process each failure and build lookup ---
$execMsgMap = @{}  # FID -> exec msg text
foreach ($fid in $failureData.Keys) {
    $fd = $failureData[$fid]
    Write-Host "Processing $($fid.Substring(0,8))... CP: $($fd.CP)"
    $execMsgMap[$fid] = Get-ExecMsgContext $fd.CP $fd.SD $fd.SN
}

# --- Read HTML and inject new column ---
$html = Get-Content $srcHtml -Raw

# Add column header: insert "Execution Messages" before "Critical Events"
$html = $html -replace "(Critical Events \(System\.evtx\)<div class='resize'></div><input class='filter-input' placeholder='Filter' oninput='colFilter\(\)'></th>)", "Execution Messages<div class='resize'></div><input class='filter-input' placeholder='Filter' oninput='colFilter()'></th><th>`$1"

# For each row, extract the FID from the href and insert exec msg cell before the last <td> (Critical Events)
$html = [regex]::Replace($html, '<tr><td>(\d+)</td><td>(.*?)</td><td><a href=''https://nga-prod\.laas\.intel\.com/#/nvl_fv_or/failureManagement/failures/([0-9a-f-]+)''[^>]*>(.*?)</a></td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>', {
    param($m)
    $num = $m.Groups[1].Value
    $rs = $m.Groups[2].Value
    $fid = $m.Groups[3].Value
    $fn = $m.Groups[4].Value
    $bn = $m.Groups[5].Value
    $sig = $m.Groups[6].Value
    $sd = $m.Groups[7].Value
    $crit = $m.Groups[8].Value

    $execMsg = if ($execMsgMap.ContainsKey($fid)) { HtmlEnc $execMsgMap[$fid] } else { "" }
    $execMsg = $execMsg -replace '&#xA;|&#xD;&#xA;|&#10;', '<br>'
    $execMsg = $execMsg -replace "`n", '<br>'

    return "<tr><td>$num</td><td>$rs</td><td><a href='https://nga-prod.laas.intel.com/#/nvl_fv_or/failureManagement/failures/$fid' target='_blank'>$fn</a></td><td>$bn</td><td>$sig</td><td>$sd</td><td style='white-space:pre;font-family:Consolas,monospace;font-size:0.75rem'>$execMsg</td><td>$crit</td></tr>"
})

# Update generation timestamp
$html = $html -replace 'Generated: [0-9-]+ [0-9:]+', "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$outPath = "output\wl_failures_only_NVL_S28_B0_ES2_WW09_5_${ts}.html"
$html | Out-File -FilePath $outPath -Encoding utf8
Write-Host "`nReport saved to: $outPath"
Start-Process $outPath
```

### File 6: `build_insight_table_nvlp.py`

This file builds pre-rendered insight table JSON for NVL_P failures. It is **data-bearing** — contains hardcoded genimcp priority mappings for specific Axon record IDs. The agent regenerates this file dynamically per query using the `TYPE_PREFIX_PRIORITY` mapping and raw Axon data.

**The agent should dynamically generate this file** from live Axon data rather than relying on the hardcoded priorities below. The embedded version serves as a template showing the table HTML generation logic (`build_table_html` function) and the `TYPE_PREFIX_MAP` constant.

```python
#!/usr/bin/env python3
"""Build pre-rendered insight_table JSON for NVL_P failures.
Reads raw insights from output/all_raw_insights.json,
merges with priority data, and outputs insight_table_nvlp.json.
"""
import json, re, html, os

RAW_PATH = os.path.join(os.path.dirname(__file__), 'output', 'all_raw_insights.json')
OUT_PATH = os.path.join(os.path.dirname(__file__), 'output', 'insight_table_nvlp.json')

# Priority data from genimcp (dynamically compiled from tool output per query)
# NOTE: The agent populates GENIMCP_PRIORITIES dynamically per query.
# Each key is an Axon debugSnapshotId, value is a dict of message->priority.
GENIMCP_PRIORITIES = {
    # Populated by the agent at runtime, e.g.:
    # "304a45c5-...": { "PCD PMC not out of reset": 1, "CPU Power Good not up!": 1, ... },
}

# Type-prefix fallback priority mapping (ordered longest prefix first)
TYPE_PREFIX_MAP = [
    ("HW.STUCK_TRANSACTION", 1),
    ("HW.MCE", 1),
    ("HW.HANG", 1),
    ("HW.PORT_STUCK", 1),
    ("HW.IFA", 1),
    ("HW.UNEXPECTED_RESET", 2),
    ("HW.LINK", 2),
    ("SW.POWER", 6),
    ("PLATFORM", 10),
    ("SW", 10),
    ("HW", 10),
]

def normalize(s):
    """Normalize message for matching."""
    if not s:
        return ""
    s = s.replace('\u00a0', ' ').replace('\u200b', '')
    return re.sub(r'\s+', ' ', s).strip()

def match_priority(axon_id, msg, itype):
    """Match a raw insight message to a priority from genimcp data."""
    norm = normalize(msg)
    prio_map = GENIMCP_PRIORITIES.get(axon_id, {})

    # Exact match
    if norm in prio_map:
        return prio_map[norm]

    # Substring match (genimcp key is contained in raw message)
    for key, p in prio_map.items():
        if key in norm:
            return p

    # Type prefix fallback
    if itype:
        for prefix, p in TYPE_PREFIX_MAP:
            if itype.startswith(prefix):
                return p

    return 10  # default

def build_table_html(insights, axon_id):
    """Build the 13-column insight summary HTML table."""
    prio_bg = {1: '#f3e5f5', 2: '#fde8e8', 10: '#f5f5f5'}
    prio_badge = {1: '#7b2d8e', 2: '#c0392b', 10: '#888888'}
    base_url = f"https://axonsv.app.intel.com/apps/record-viewer/{axon_id}/intel-svtools-report-v1?tab=report"

    rows = []
    for idx, ins in enumerate(insights, 1):
        p = ins['priority']
        bg = prio_bg.get(p, '#f5f5f5')
        badge_c = prio_badge.get(p, '#888888')

        path = ins.get('path', '')
        iidx = ins.get('insight_index', 0)
        fragment = f"#{path}_insight_{iidx}" if path else ''
        report_name = path.split('.')[-1] if path else ''
        report_link = f"<a href='{html.escape(base_url + fragment)}' target='_blank' style='color:#2471a3;font-size:10px'>{html.escape(report_name)}</a>" if report_name else ''

        msg_enc = html.escape(ins.get('message', ''))
        loc_enc = html.escape(ins.get('location', '') or '')
        sig_enc = html.escape(ins.get('signature', '') or '')
        ip_enc = html.escape(ins.get('ip_domain', '') or '')
        type_enc = html.escape(ins.get('type', '') or '')
        mcacod = html.escape(str(ins.get('mcacod', '') or ''))
        mcacod_d = html.escape(str(ins.get('mcacod_decode', '') or ''))
        mscod = html.escape(str(ins.get('mscod', '') or ''))
        mscod_d = html.escape(str(ins.get('mscod_decode', '') or ''))
        uc = html.escape(str(ins.get('uc', '') or ''))

        td = "style='padding:3px 5px;border:1px solid #ddd;white-space:nowrap;vertical-align:top;font-size:10px'"
        td_msg = "style='padding:3px 5px;border:1px solid #ddd;white-space:pre-wrap;word-break:break-word;vertical-align:top;font-size:10px;max-width:300px'"

        row = f"<tr style='background:{bg}'>"
        row += f"<td {td}>{idx}</td>"
        row += f"<td {td}><span style='display:inline-block;padding:1px 6px;border-radius:3px;color:#fff;background:{badge_c};font-size:9px;font-weight:700'>P{p}</span></td>"
        row += f"<td {td}>{type_enc}</td>"
        row += f"<td {td}>{report_link}</td>"
        row += f"<td {td}>{ip_enc}</td>"
        row += f"<td {td_msg}>{msg_enc}</td>"
        row += f"<td {td}>{loc_enc}</td>"
        row += f"<td {td}>{sig_enc}</td>"
        row += f"<td {td}>{mcacod}</td>"
        row += f"<td {td}>{mcacod_d}</td>"
        row += f"<td {td}>{mscod}</td>"
        row += f"<td {td}>{mscod_d}</td>"
        row += f"<td {td}>{uc}</td>"
        row += "</tr>"
        rows.append(row)

    th = "style='padding:4px 6px;background:#1a237e;color:#fff;font-size:10px;white-space:nowrap;position:sticky;top:0;z-index:1'"
    header = f"<thead><tr><th {th}>#</th><th {th}>Priority</th><th {th}>Type</th><th {th}>Report</th><th {th}>IP</th><th {th}>Message</th><th {th}>Location</th><th {th}>Signature</th><th {th}>MCACOD</th><th {th}>MCACOD Decode</th><th {th}>MSCOD</th><th {th}>MSCOD Decode</th><th {th}>UC</th></tr></thead>"

    table = f"<table style='border-collapse:collapse;width:100%;min-width:1200px;font-family:Consolas,monospace'>{header}<tbody>{''.join(rows)}</tbody></table>"
    return table


def main():
    with open(RAW_PATH, 'r', encoding='utf-16') as f:
        raw = json.load(f)

    result = {}
    for axon_id, data in raw.items():
        summary = data.get('summary', '')
        raw_insights = data.get('insights', [])

        enriched = []
        for ins in raw_insights:
            p = match_priority(axon_id, ins.get('message', ''), ins.get('type', ''))
            enriched.append({**ins, 'priority': p})

        enriched.sort(key=lambda x: x['priority'])
        table_html = build_table_html(enriched, axon_id) if enriched else ''

        result[axon_id] = {
            'summary': summary,
            'total': len(enriched),
            'table_html': table_html
        }

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    print(f"Wrote {len(result)} records to {OUT_PATH}")
    for aid, d in result.items():
        print(f"  {aid[:8]}: {d['total']} insights, summary='{d['summary'][:60]}'")

if __name__ == '__main__':
    main()
```

### File 7: `build_insight_table_hx_sst.py`

```python
#!/usr/bin/env python3
"""Build pre-rendered insight_table JSON for all NVL_H_SST WW12.3 failures.
Reads raw axon-server JSON files from output/axon_hx_sst/ and generates
insight_table_hx_sst.json with table_html for each debugSnapshotId.
"""
import json, re, html, os, sys

ENRICHED = os.path.join(os.path.dirname(__file__), 'output', 'hx_sst_ww12_enriched.json')
AXON_DIR = os.path.join(os.path.dirname(__file__), 'output', 'axon_hx_sst')
OUT_PATH = os.path.join(os.path.dirname(__file__), 'output', 'insight_table_hx_sst.json')

TYPE_PREFIX_PRIORITY = [
    ('HW.STUCK_TRANSACTION', 1), ('HW.MCE', 1), ('HW.HANG', 1),
    ('HW.PORT_STUCK', 1), ('HW.IFA', 1),
    ('HW.UNEXPECTED_RESET', 2), ('HW.LINK', 2), ('SW.BSOD', 2),
    ('SW.POWER', 6),
    ('PLATFORM', 10), ('SW', 10), ('HW', 10),
]

PRIORITY_BG = {1: '#f3e5f5', 2: '#fde8e8', 6: '#e3f2fd', 10: '#f5f5f5'}
PRIORITY_BG_ALT = {1: '#ede0f0', 2: '#f8d0d0', 6: '#d6eaf8', 10: '#eee'}
PRIORITY_BADGE_BG = {1: '#7b2d8e', 2: '#c0392b', 6: '#2980b9', 10: '#888888'}
TYPE_COLOR = {
    'HW.STUCK_TRANSACTION': '#d32f2f', 'HW.MCE': '#c62828',
    'HW.HANG': '#d32f2f', 'HW.PORT_STUCK': '#d32f2f', 'HW.IFA': '#c62828',
    'HW.UNEXPECTED_RESET': '#e65100', 'HW.LINK': '#e65100',
    'SW.BSOD': '#c62828', 'SW.POWER': '#1565c0',
    'PLATFORM': '#546e7a', 'SW': '#546e7a', 'HW': '#b71c1c',
}


def get_type_color(t):
    for prefix, c in TYPE_COLOR.items():
        if t.upper().startswith(prefix):
            return c
    return '#333'


def get_priority(typ):
    if not typ:
        return 10
    t = typ.upper()
    for prefix, p in TYPE_PREFIX_PRIORITY:
        if t.startswith(prefix):
            return p
    return 10


def enc(s):
    if s is None:
        return ''
    return html.escape(str(s))


def dash():
    return "<span style='color:#ccc'>\u2014</span>"


def walk(node, path_parts):
    """Recursively collect all insights from the sub_reports tree."""
    results = []
    src = node.get('source', node.get('name', '?'))
    current_path = '.'.join(path_parts) if path_parts else src
    for i, ins in enumerate(node.get('insights', [])):
        fragment = f"{current_path}_insight_{i}"
        report_label = src.split('/')[-1] if '/' in src else src
        results.append({
            'type': ins.get('type', ''),
            'message': ins.get('message', ''),
            'location': ins.get('location', ''),
            'ip': ins.get('ip_domain', ''),
            'report': report_label,
            'report_path': current_path,
            'fragment': fragment,
            'mcacod': ins.get('mcacod', ''),
            'mcacod_decode': ins.get('mcacod_decode', ''),
            'mscod': ins.get('mscod', ''),
            'mscod_decode': ins.get('mscod_decode', ''),
            'uc': ins.get('uc', ''),
        })
    for sr in node.get('sub_reports', []):
        child_src = sr.get('source', sr.get('name', '?'))
        results.extend(walk(sr, path_parts + [child_src]))
    return results


def get_summary(data):
    summary = ''
    if data.get('insights'):
        summary = data['insights'][0].get('message', '')
    for sr in data.get('sub_reports', []):
        src = sr.get('source', '')
        if 'classifier' in src.lower() or 'hang_classifier' in src.lower():
            if sr.get('insights'):
                summary = sr['insights'][0].get('message', summary)
                break
    return summary


def build_table_html(axon_id, all_insights, summary):
    from collections import Counter
    total = len(all_insights)
    base_url = f"https://axonsv.app.intel.com/apps/record-viewer/{axon_id}/intel-svtools-report-v1?tab=report"

    rows_html = []
    for idx, ins in enumerate(all_insights):
        p = ins['priority']
        bg = PRIORITY_BG.get(p, '#fff') if idx % 2 == 0 else PRIORITY_BG_ALT.get(p, '#f5f5f5')
        badge_bg = PRIORITY_BADGE_BG.get(p, '#888')
        tc = get_type_color(ins['type'])
        link_url = f"{base_url}#{ins['fragment']}"

        mcacod_val = ins.get('mcacod', '')
        mcacod_dec = ins.get('mcacod_decode', '')
        mscod_val = ins.get('mscod', '')
        mscod_dec = ins.get('mscod_decode', '')
        uc_val = ins.get('uc', '')

        mcacod_cell = f"<td style='font-family:monospace;font-size:11px;text-align:center'>{enc(mcacod_val)}</td>" if mcacod_val else f"<td style='font-family:monospace;font-size:11px;text-align:center'>{dash()}</td>"
        mcacod_dec_cell = f"<td style='font-size:11px'>{enc(str(mcacod_dec))}</td>" if mcacod_dec else f"<td style='font-size:11px'>{dash()}</td>"
        mscod_cell = f"<td style='font-family:monospace;font-size:11px;text-align:center'>{enc(mscod_val)}</td>" if mscod_val else f"<td style='font-family:monospace;font-size:11px;text-align:center'>{dash()}</td>"
        mscod_dec_cell = f"<td style='font-size:11px'>{enc(str(mscod_dec))}</td>" if mscod_dec else f"<td style='font-size:11px'>{dash()}</td>"
        uc_cell = "<td style='text-align:center'><span style='color:#c62828;font-weight:600'>Yes</span></td>" if uc_val else f"<td style='text-align:center'>{dash()}</td>"

        row = f"""<tr style="background:{bg}">
  <td style="text-align:center;color:#888">{idx+1}</td>
  <td style="text-align:center"><span style="display:inline-block;min-width:28px;text-align:center;padding:2px 6px;border-radius:4px;background:{badge_bg};color:#fff;font-weight:bold;font-size:11px">P{p}</span></td>
  <td style="font-size:11px"><span style="color:{tc};font-weight:600">{enc(ins['type'])}</span></td>
  <td style="font-size:11px"><a href="{enc(link_url)}" target="_blank" rel="noopener" style="color:#1565c0;text-decoration:none;border-bottom:1px dotted #1565c0" title="{enc(ins['report_path'])}">{enc(ins['report'])}</a></td>
  <td style="font-family:monospace;font-size:11px">{enc(ins['ip'])}</td>
  <td style="font-size:11px">{enc(ins['message'])}</td>
  <td style="font-family:monospace;font-size:11px">{enc(ins['location'])}</td>
  <td style="font-size:11px">{enc(ins['report_path'])}</td>
  {mcacod_cell}
  {mcacod_dec_cell}
  {mscod_cell}
  {mscod_dec_cell}
  {uc_cell}
</tr>"""
        rows_html.append(row)

    pcounts = Counter(ins['priority'] for ins in all_insights)
    stats_badges = ''
    for p in sorted(pcounts.keys()):
        bg = PRIORITY_BADGE_BG.get(p, '#888')
        stats_badges += f"<span style='display:inline-block;margin:1px 4px;padding:1px 6px;border-radius:3px;font-size:10px;background:{bg};color:#fff'>P{p} ({pcounts[p]})</span>"

    table_html = f"""<div style="margin-bottom:4px;font-size:11px">
<b>Insights:</b> {total} &nbsp;|&nbsp; {stats_badges}
</div>
<table style="width:100%;border-collapse:collapse;background:#fff;font-size:11px">
<thead>
<tr style="background:#263238;color:#fff">
  <th style="padding:4px 6px;font-size:10px;width:25px">#</th>
  <th style="padding:4px 6px;font-size:10px;background:#4a148c;width:40px">Pri</th>
  <th style="padding:4px 6px;font-size:10px;width:130px">Type</th>
  <th style="padding:4px 6px;font-size:10px;width:100px">Report</th>
  <th style="padding:4px 6px;font-size:10px;width:80px">IP</th>
  <th style="padding:4px 6px;font-size:10px">Message</th>
  <th style="padding:4px 6px;font-size:10px;width:140px">Location</th>
  <th style="padding:4px 6px;font-size:10px;width:160px">Signature</th>
  <th style="padding:4px 6px;font-size:10px;background:#1b5e20;width:55px">MCACOD</th>
  <th style="padding:4px 6px;font-size:10px;background:#1b5e20;width:130px">MCACOD Dec</th>
  <th style="padding:4px 6px;font-size:10px;background:#1b5e20;width:55px">MSCOD</th>
  <th style="padding:4px 6px;font-size:10px;background:#1b5e20;width:130px">MSCOD Dec</th>
  <th style="padding:4px 6px;font-size:10px;width:30px">UC</th>
</tr>
</thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>"""
    return table_html


def process_one(axon_id, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    data = raw
    if isinstance(raw, dict) and 'result' in raw:
        data = raw['result']
    if isinstance(data, str):
        data = json.loads(data)

    root_src = data.get('source', data.get('name', ''))
    all_insights = walk(data, [root_src] if root_src else [])
    summary = get_summary(data)

    for ins in all_insights:
        ins['priority'] = get_priority(ins['type'])
    all_insights.sort(key=lambda x: (x['priority'], x['type'], x['message']))

    table_html = build_table_html(axon_id, all_insights, summary)
    return {
        'summary': summary,
        'total': len(all_insights),
        'table_html': table_html,
    }


if __name__ == '__main__':
    with open(ENRICHED, 'r', encoding='utf-8') as f:
        enriched = json.load(f)

    result = {}
    for fail in enriched['failures']:
        dsid = fail.get('debugSnapshotId')
        fname = fail.get('failureName', '')
        if not dsid:
            print(f"  {fname}: no debugSnapshotId", file=sys.stderr)
            continue
        filepath = os.path.join(AXON_DIR, f'{dsid}.json')
        if not os.path.exists(filepath):
            print(f"  {fname}: no axon file for {dsid}", file=sys.stderr)
            continue
        try:
            entry = process_one(dsid, filepath)
            result[dsid] = entry
            print(f"  {fname} ({dsid}): {entry['total']} insights, summary={entry['summary']}", file=sys.stderr)
        except Exception as e:
            print(f"  {fname} ({dsid}): ERROR {e}", file=sys.stderr)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    print(f"\nSaved {len(result)} records to {OUT_PATH}", file=sys.stderr)
```

### File 8: `build_axon_insights_with_priority.ps1`

This file is **data-bearing** — it contains hardcoded Axon insight data for specific failure records from a previous query. The agent regenerates this file dynamically per query. The embedded version below contains the structural template (the `Add-Record` helper, JSON serialization, and HTML injection logic). **The hardcoded `Add-Record` calls are stale sample data and must be replaced with live Axon data from `mcp_axon-server_get_axon_report_content` during each query.**

Due to its size (644 lines, mostly hardcoded data), only the structural template is embedded. The agent generates the full file dynamically.

```powershell
###############################################################################
# build_axon_insights_with_priority.ps1
# Builds fc_axon_insights.json with priority data, then updates the HTML
# NOTE: The Add-Record calls below are STALE SAMPLE DATA from a previous query.
# The agent regenerates this file dynamically per query with live Axon data.
###############################################################################
$ErrorActionPreference = 'Continue'

# Build the insights data with priority for each message
$data = @{}

# Helper to add record
function Add-Record($fid, $axon, $summary, $insights) {
    $script:data[$fid] = @{
        axon     = $axon
        summary  = $summary
        insights = $insights
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# INSERT Add-Record CALLS HERE (generated dynamically from live Axon data)
# Example:
# Add-Record 'abcd1234' 'guid-here' 'Summary text' @(
#     @{p=1; m="Priority 1 insight message"}
#     @{p=2; m="Priority 2 insight message"}
#     @{p=10; m="Priority 10 insight message"}
# )
# ═══════════════════════════════════════════════════════════════════════════

# Convert to JSON-serializable structure
$jsonObj = [ordered]@{}
foreach ($fid in ($data.Keys | Sort-Object)) {
    $rec = $data[$fid]
    # Sort insights by priority ascending
    $sorted = $rec.insights | Sort-Object { $_.p }
    $jsonObj[$fid] = [ordered]@{
        axon     = $rec.axon
        summary  = $rec.summary
        insights = @($sorted | ForEach-Object { [ordered]@{ priority = $_.p; message = $_.m } })
    }
}

$jsonPath = Join-Path (Join-Path $PSScriptRoot 'output') 'fc_axon_insights.json'
$jsonObj | ConvertTo-Json -Depth 10 | Set-Content $jsonPath -Encoding UTF8
Write-Host "Saved $($data.Count) records to $jsonPath"

# Now update the HTML
$reportDir = Join-Path $PSScriptRoot 'output'
$htmlFile = Get-ChildItem $reportDir -Filter 'wl_nosighting_NVL-S_Fullchip_allcycles_*.html' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $htmlFile) { Write-Error "No report found"; exit 1 }
Write-Host "Processing: $($htmlFile.FullName)"

$html = Get-Content $htmlFile.FullName -Raw -Encoding UTF8

# Strip existing axon cells (use (?s) for multi-line content)
$html = [regex]::Replace($html, '(?s)\s*<td class="axon">.*?</td>', '')

# Strip existing axon header if present, then add it after the last <th>
$html = [regex]::Replace($html, '(?s)\s*<th[^>]*>.*?(?:SVTools|Statuscope).*?</th>', '')
$axonThIdx = 9  # 10th column (0-based)
$axonTh = '  <th draggable="true" ondragstart="dsDrag(event,' + $axonThIdx + ')" ondragover="allowDrop(event)" ondrop="doDrop(event,' + $axonThIdx + ')"><div class="hdr" onclick="sortTable(' + $axonThIdx + ')">Statuscope Summary<span class="sort-ind"></span></div><input class="filter-input" oninput="filterTable()" placeholder="..."><div class="resize-grip" onmousedown="startResize(event,' + $axonThIdx + ')"></div></th>'
# Insert before </tr></thead>
$html = $html -replace '(</tr>\s*</thead>)', "$axonTh`n`$1"

# Process each row
$rowPattern = '(?s)(<tr>\s*<td class="num">\d+</td>.*?<td><a href=".+?">([a-f0-9]{8})</a>.*?)(</tr>)'
$matchCount = 0
$dataCount = 0
$html = [regex]::Replace($html, $rowPattern, {
    param($m)
    $fid = $m.Groups[2].Value
    $before = $m.Groups[1].Value
    $closeTr = $m.Groups[3].Value
    $script:matchCount++

    $cellContent = '(no SVTools data)'
    if ($jsonObj.Contains($fid)) {
        $a = $jsonObj[$fid]
        $script:dataCount++
        $summary = [System.Net.WebUtility]::HtmlEncode($a.summary)
        $reportUrl = "https://axonsv.app.intel.com/apps/record-viewer/$($a.axon)/intel-svtools-report-v1"

        # Determine if P1 summary (classifier recognized a failure)
        $isP1Summary = $a.summary -notmatch 'No insights recognized'
        $summaryColor = if ($isP1Summary) { '#7b2d8e' } else { '#2980b9' }

        # Build insight lines with color per priority level
        $pColors = @{ 1='#7b2d8e'; 2='#c0392b'; 3='#e67e22'; 6='#2980b9'; 10='#888888' }
        $lines = @()
        foreach ($insight in $a.insights) {
            $p = $insight.priority
            $msg = [System.Net.WebUtility]::HtmlEncode($insight.message)
            $color = if ($pColors.ContainsKey($p)) { $pColors[$p] } else { '#333' }
            $weight = if ($p -le 2) { 'font-weight:600;' } else { '' }
            $lines += "<span style='color:$color;$weight'>[P$p] $msg</span>"
        }
        $insightBlock = $lines -join "`n"

        $cellContent = "<div style='max-height:300px;overflow-y:auto;font-size:11px;'>" +
            "<b style='color:$summaryColor;'>$summary</b>" +
            "<pre style='margin-top:4px;white-space:pre-wrap;word-break:break-word;font-size:10px;color:#333;'>$insightBlock</pre>" +
            "<div style='margin-top:4px;font-size:11px;'><a href='$reportUrl' target='_blank' style='color:#2980b9;'>Link to Statuscope</a></div></div>"
    }

    return "$before`n  <td class=`"axon`">$cellContent</td>`n$closeTr"
})

[System.IO.File]::WriteAllText($htmlFile.FullName, $html, [System.Text.Encoding]::UTF8)
Write-Host "Updated SVTools column: $matchCount rows, $dataCount with insights"
Write-Host "Output: $($htmlFile.FullName)"
Start-Process $htmlFile.FullName
```

### File 9: `gen_wl_report_compact.ps1`

Main HTML report template. The agent copies this template, populates `$failures`, `$project`, `$cycle`, `$suite` dynamically per query, then executes. **Never hardcode failure data** — all data comes from live NGA queries.

Key functions: `HtmlEnc`, `Get-ExecMessages` + `Build-ExecTableHtml`, `Get-EvtxEvents` + `Format-CritEvents`, `Get-BsodInfo`, `Format-AxonInsights`.

```powershell
﻿###############################################################################
# gen_wl_report_compact.ps1  --  Unsighted Failures HTML report template
# This is the main report template used by the Unsighted_Analyser Agent.
# The agent populates $failures, $project, $cycle, $suite dynamically per query.
# DO NOT hardcode failure data here -- all data comes from live NGA queries.
###############################################################################
$ErrorActionPreference = 'Continue'

# ── Station Timezone Helper ──────────────────────────────────────────────────
# Stations run in different locations. Determine timezone from SystemName prefix.
$script:tzCache = @{}
function Get-StationTimeZone($systemName) {
    if (-not $systemName) { return @{ tz = [System.TimeZoneInfo]::Utc; abbr = 'UTC' } }
    $key = $systemName.Substring(0, [math]::Min(2, $systemName.Length)).ToLower()
    if ($script:tzCache.ContainsKey($key)) { return $script:tzCache[$key] }
    $result = switch ($key) {
        'pg' { @{ tz = [System.TimeZoneInfo]::FindSystemTimeZoneById('Singapore Standard Time'); abbr = 'MYT' } }
        'fm' { @{ tz = [System.TimeZoneInfo]::FindSystemTimeZoneById('Pacific Standard Time'); abbr = 'PST' } }
        'jf' { @{ tz = [System.TimeZoneInfo]::FindSystemTimeZoneById('Pacific Standard Time'); abbr = 'PST' } }
        default {
            Write-Host "[WARN] Unknown station prefix '$key' from SystemName '$systemName' -- defaulting to UTC" -ForegroundColor Yellow
            @{ tz = [System.TimeZoneInfo]::Utc; abbr = 'UTC' }
        }
    }
    # For US Pacific, check if DST is active and use PDT abbreviation
    if ($result.abbr -eq 'PST' -and $result.tz.IsDaylightSavingTime([datetime]::UtcNow)) {
        $result.abbr = 'PDT'
    }
    $script:tzCache[$key] = $result
    return $result
}

# Default timezone for report header (MYT)
$myt = [System.TimeZoneInfo]::FindSystemTimeZoneById('Singapore Standard Time')

# ── Failure Data (populated dynamically by the agent per query) ─────────────
# Each entry in $failures must have these fields:
#   fid         - Full failure GUID
#   fname       - Short 8-char failure name
#   bucket      - Bucket name
#   sigs        - Signatures joined with ||
#   submitted   - SubmittedDateTime ISO 8601 UTC
#   runState    - Result.ResultCode (Failed, Passed, etc.)
#   cleanup     - Cleanup path from nga_get_testrun
#   testRunId   - Full TestRunId GUID
#   systemName  - Station SystemName from testrun (e.g., FM05WVAW0987, PG01XXXX)
#   axonId      - DebugSnapshotId GUID (or empty)
#   axonSummary - SVTools summary text
#   axonInsights - Array of @{p=<priority>; m=<message>}
$failures = @(
    # The agent inserts @{...} entries here from live NGA query data.
    # Example entry:
    # @{
    #     fid='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'; fname='xxxxxxxx'
    #     bucket='bucket_name'; sigs='sig1||sig2'
    #     submitted='2026-01-01T00:00:00Z'; runState='Failed'
    #     cleanup='\\\\server\\path'; testRunId='guid'
    #     systemName='FM05WVAW0987'; axonId='guid'; axonSummary=''; axonInsights=@()
    # }
)

function HtmlEnc([string]$s) { [System.Net.WebUtility]::HtmlEncode($s) }

$msgCache = @{}
$csvCache = @{}
function Get-ExecMessages($cp, $submittedUtc, $sig1, $testRunId, $failureName, $stationTz) {
    $subDt = [datetime]::Parse($submittedUtc).ToUniversalTime()
    $windowStart = $subDt.AddHours(-1)     # 1 hour before
    $minBeforeCount = 10                    # minimum 10 messages before closest
    $afterCount  = 10                       # +10 messages after closest
    $apiError = $null                       # tracks API failure reason for fallback messaging
    if (-not $stationTz) { $stationTz = @{ tz = $myt; abbr = 'MYT' } }
    $localTz = $stationTz.tz
    $tzAbbr = $stationTz.abbr
    $subLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc($subDt, $localTz)

    # Helper: build inline table from filtered message array
    function Build-ExecTableHtml($filtered, $closestIdx, $totalApi, $fName) {
        $lines = @()
        $lines += "<div style='font-size:12px;margin-bottom:4px'>"
        $lines += "<b>Failure:</b> $($subLocal.ToString('M/d/yy H:mm:ss')) $tzAbbr | <b>Window:</b> -1h or min 10 / +10 msgs | <b>Messages:</b> $($filtered.Count) of $totalApi"
        $lines += "</div>"
        $lines += "<div style='max-height:320px;overflow:auto;border:1px solid #ccc;border-radius:3px'>"
        $lines += "<table style='border-collapse:collapse;width:100%;font-size:11px;font-family:Consolas,monospace'>"
        $lines += "<thead><tr style='background:#2c3e50;color:#fff;position:sticky;top:0;z-index:1'>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>#</th>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>Timestamp</th>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>Source</th>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>Stage</th>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>System</th>"
        $lines += "<th style='padding:4px 6px;text-align:left;white-space:nowrap'>Title</th>"
        $lines += "<th style='padding:4px 6px;text-align:left'>Message</th>"
        $lines += "</tr></thead><tbody>"
        $num = 0
        for ($i = $filtered.Count - 1; $i -ge 0; $i--) {
            $num++
            $e = $filtered[$i]
            $m = $e.msg
            $isClosest = ($i -eq $closestIdx)
            $rowBg = if ($isClosest) { "background:#fff9c4;font-weight:700;border-left:4px solid #c0392b;" }
                     elseif ($m.Message -match 'Failed|Aborted') { "background:#fde8e8;" }
                     elseif ($m.Message -match 'Passed|Completed') { "background:#e8f5e9;" }
                     elseif ($num % 2 -eq 0) { "background:#fafafa;" }
                     else { "" }
            $localTs = [System.TimeZoneInfo]::ConvertTimeFromUtc([System.DateTime]::SpecifyKind($e.utc, [System.DateTimeKind]::Utc), $localTz)
            $tsStr = $localTs.ToString('M/d/yy H:mm:ss') + ' ' + $tzAbbr
            $srcColor = switch ($m.Source) { 'Orchestrator' { '#8e44ad' }; 'User' { '#2980b9' }; 'ResultService' { '#27ae60' }; 'StationAutomationService' { '#d35400' }; default { '#777' } }
            $srcLabel = switch ($m.Source) { 'Orchestrator' { 'Orch' }; 'User' { 'User' }; 'ResultService' { 'Result' }; 'StationAutomationService' { 'Station' }; default { HtmlEnc $m.Source } }
            $srcHtml = "<span style='display:inline-block;padding:1px 5px;border-radius:3px;color:#fff;background:$srcColor;font-size:10px'>$srcLabel</span>"
            $msgEnc = HtmlEnc $m.Message
            if ($m.Message -match 'Failed|Aborted') { $msgEnc = "<span style='color:#c0392b'>$msgEnc</span>" }
            elseif ($m.Message -match 'Passed|Completed') { $msgEnc = "<span style='color:#27ae60'>$msgEnc</span>" }
            elseif ($m.Message -match 'Running') { $msgEnc = "<span style='color:#2471a3'>$msgEnc</span>" }
            $marker = if ($isClosest) { "<span style='color:#c0392b'>&#9658;</span> " } else { "" }
            $rowId = if ($isClosest) { "exec_closest_$fName" } else { "" }
            $rowIdAttr = if ($rowId) { " id='$rowId'" } else { "" }
            $td = "style='padding:3px 6px;border-bottom:1px solid #eee;white-space:nowrap;vertical-align:top'"
            $tdMsg = "style='padding:3px 6px;border-bottom:1px solid #eee;white-space:pre-wrap;word-break:break-word;vertical-align:top;max-width:500px'"
            $lines += "<tr$rowIdAttr style='$rowBg'>"
            $lines += "<td $td>$marker$num</td><td $td>$tsStr</td><td $td>$srcHtml</td>"
            $lines += "<td $td>$(HtmlEnc $m.StageName)</td><td $td>$(HtmlEnc $m.SystemName)</td>"
            $lines += "<td $td>$(HtmlEnc $m.Title)</td><td $tdMsg>$msgEnc</td></tr>"
        }
        $lines += "</tbody></table></div>"
        $lines += "<button class='exec-expand-btn' onclick='openExecModal(this)' style='margin-top:4px;padding:2px 10px;font-size:11px;cursor:pointer;background:#2c3e50;color:#fff;border:none;border-radius:3px'>Expand ($($filtered.Count) msgs)</button>"
        if ($fName) {
            $lines += "<script>(function(){var r=document.getElementById('exec_closest_$fName');if(r){var c=r.parentElement;while(c&&!c.style.maxHeight)c=c.parentElement;if(c){c.scrollTop=r.offsetTop-c.offsetTop-c.clientHeight/3;}}})()</script>"
        }
        return ($lines -join "`n")
    }

    # Try NGA API first
    if ($testRunId) {
        if (-not $msgCache.ContainsKey($testRunId)) {
            try {
                $pyOut = & python "$PSScriptRoot\get_testrun_messages.py" 'nvl_fv_or' $testRunId 2>$null
                if ($pyOut) {
                    $parsed = $pyOut | ConvertFrom-Json
                    if ($parsed -is [array]) {
                        $msgCache[$testRunId] = $parsed
                    } elseif ($parsed.error) {
                        $msgCache[$testRunId] = "ERR:API error: $($parsed.error) - $($parsed.detail)"
                    } else {
                        $msgCache[$testRunId] = @($parsed)
                    }
                }
                else { $msgCache[$testRunId] = 'ERR:get_testrun_messages.py returned no output' }
            } catch { $msgCache[$testRunId] = "ERR:exception calling get_testrun_messages.py: $($_.Exception.Message)" }
        }
        $apiMsgs = $msgCache[$testRunId]
        if ($apiMsgs -is [string] -and $apiMsgs.StartsWith('ERR:')) {
            # API failed -- show error and fall through to CSV
            $apiError = $apiMsgs
        }
        elseif ($apiMsgs -and $apiMsgs.Count -gt 0) {
            $sorted = @($apiMsgs | Sort-Object { $_.TimeStamp })
            # Pass 1: find the closest message index in sorted array
            $closestSortedIdx = -1; $closestDiff = [double]::MaxValue
            for ($si = 0; $si -lt $sorted.Count; $si++) {
                $m = $sorted[$si]
                if (-not $m.TimeStamp) { continue }
                try {
                    $ts = [datetime]::Parse($m.TimeStamp).ToUniversalTime()
                    $diff = [math]::Abs(($ts - $subDt).TotalSeconds)
                    if ($diff -lt $closestDiff) { $closestDiff = $diff; $closestSortedIdx = $si }
                } catch {}
            }
            # Pass 2: collect messages -- before: max(-1h, min 10 msgs) | after: 10 msgs
            $filtered = @()
            $closestIdx = -1

            # 2a: Before & at closest -- walk backwards, stop when past 1h AND have >= minBeforeCount
            $beforeMsgs = @()
            for ($si = $closestSortedIdx; $si -ge 0; $si--) {
                $m = $sorted[$si]
                if (-not $m.TimeStamp) { continue }
                try {
                    $ts = [datetime]::Parse($m.TimeStamp).ToUniversalTime()
                } catch { continue }
                $diff = [math]::Abs(($ts - $subDt).TotalSeconds)
                $beforeMsgs += @{ msg = $m; utc = $ts; diff = $diff }
                # Stop when past 1h window AND have at least minBeforeCount messages
                if ($ts -lt $windowStart -and $beforeMsgs.Count -ge $minBeforeCount) { break }
            }
            # Reverse to chronological order
            [array]::Reverse($beforeMsgs)
            $filtered = $beforeMsgs
            $closestIdx = $filtered.Count - 1  # closest is last in the before list

            # 2b: After closest -- take up to afterCount
            $afterSeen = 0
            for ($si = $closestSortedIdx + 1; $si -lt $sorted.Count; $si++) {
                $m = $sorted[$si]
                if (-not $m.TimeStamp) { continue }
                try {
                    $ts = [datetime]::Parse($m.TimeStamp).ToUniversalTime()
                } catch { continue }
                $afterSeen++
                if ($afterSeen -le $afterCount) {
                    $diff = [math]::Abs(($ts - $subDt).TotalSeconds)
                    $filtered += @{ msg = $m; utc = $ts; diff = $diff }
                } else { break }
            }

            if ($filtered.Count -gt 0) {
                return (Build-ExecTableHtml $filtered $closestIdx $sorted.Count $failureName)
            }
            return '(no messages in window)'
        }
        # API returned no messages or returned error -- will fall through to CSV
    } else {
        $apiError = 'ERR:no testRunId available'
    }

    # Fallback: CSV from cleanup path
    if (-not $cp) {
        $reason = if ($apiError) { $apiError.Substring(4) + ' | also: no cleanup path for CSV fallback' } else { 'no cleanup path' }
        return "<span style='color:#c0392b;font-weight:700'>&#9888; $([System.Net.WebUtility]::HtmlEncode($reason))</span>"
    }
    $csvPath = Join-Path $cp 'ExecutionMessages.csv'
    if (-not $csvCache.ContainsKey($cp)) {
        if (Test-Path $csvPath) {
            $csvCache[$cp] = @(Get-Content $csvPath -ErrorAction SilentlyContinue)
        } else { $csvCache[$cp] = $null }
    }
    $csvLines = $csvCache[$cp]
    if (-not $csvLines -or $csvLines.Count -eq 0) {
        $reason = if ($apiError) { $apiError.Substring(4) + ' | also: no ExecutionMessages.csv at cleanup path' } else { "ExecutionMessages.csv not found or empty at: $cp" }
        return "<span style='color:#c0392b;font-weight:700'>&#9888; $([System.Net.WebUtility]::HtmlEncode($reason))</span>"
    }

    $matchIdx = -1
    if ($sig1) {
        $parts = $sig1 -split "'" | Where-Object { $_ -match '^h(test|preboot|reboot)_' }
        $funcName = if ($parts) { ($parts | Select-Object -First 1) } else { $null }
        if ($funcName) {
            for ($i = $csvLines.Count - 1; $i -ge 0; $i--) {
                if ($csvLines[$i] -like "*$funcName*Failed*" -or $csvLines[$i] -like "*$funcName*Aborted*") {
                    $matchIdx = $i; break
                }
            }
        }
    }
    if ($matchIdx -lt 0) {
        $bestDiff = [double]::MaxValue
        for ($i = 0; $i -lt $csvLines.Count; $i++) {
            if ($csvLines[$i] -match '(\d{2}:\d{2}:\d{2})\s*-\s*(\d{1,2}\s+\w{3}\s+\d{4})') {
                try {
                    $csvDt = [datetime]::ParseExact("$($matches[1]) - $($matches[2])", 'HH:mm:ss - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
                    $diff = [math]::Abs(($csvDt - $subDt).TotalSeconds)
                    if ($diff -lt $bestDiff) { $bestDiff = $diff; $matchIdx = $i }
                } catch {}
            }
        }
    }
    if ($matchIdx -lt 0) {
        $reason = if ($apiError) { $apiError.Substring(4) + ' | CSV fallback: no matching line found' } else { 'no matching line found in ExecutionMessages.csv' }
        return "<span style='color:#c0392b;font-weight:700'>&#9888; $([System.Net.WebUtility]::HtmlEncode($reason))</span>"
    }

    $start = [math]::Max(0, $matchIdx - 5)
    $end   = [math]::Min($csvLines.Count - 1, $matchIdx + 5)
    $result = @()
    for ($i = $end; $i -ge $start; $i--) {
        $raw = $csvLines[$i]
        $display = $raw
        if ($raw -match '^(\d{2}:\d{2}:\d{2})\s*-\s*(\d{1,2}\s+\w{3}\s+\d{4})(.*)') {
            try {
                $utcDt = [datetime]::ParseExact("$($matches[1]) - $($matches[2])", 'HH:mm:ss - d MMM yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
                $localDt = [System.TimeZoneInfo]::ConvertTimeFromUtc($utcDt, $localTz)
                $display = $localDt.ToString('M/d/yy H:mm:ss') + ' ' + $tzAbbr + $matches[3]
            } catch {}
        }
        $prefix = if ($i -eq $matchIdx) { '>>> ' } else { '    ' }
        $result += $prefix + (HtmlEnc $display)
    }
    return "<pre>" + ($result -join "`n") + "</pre>"
}

# ── System.evtx Critical/Errors ────────────────────────────────────────────
$evtxCache = @{}
function Get-EvtxEvents($cp) {
    if ($evtxCache.ContainsKey($cp)) { return $evtxCache[$cp] }
    if (-not $cp) { $evtxCache[$cp] = 'ERR:no cleanup path'; return $evtxCache[$cp] }
    if (-not (Test-Path $cp)) { $evtxCache[$cp] = "ERR:cleanup path not found: $cp"; return $evtxCache[$cp] }
    $zips = @(Get-ChildItem $cp -Filter '*.zip' -ErrorAction SilentlyContinue)
    if ($zips.Count -eq 0) { $evtxCache[$cp] = "ERR:no ZIP files in cleanup path: $cp"; return $evtxCache[$cp] }
    $zip = $zips[0].FullName

    $job = Start-Job -ScriptBlock {
        param($zipPath)
        $events = [System.Collections.Generic.List[object]]::new()
        try {
            $tmpDir = Join-Path $env:TEMP "evtx_$(Get-Random)"
            New-Item $tmpDir -ItemType Directory -Force | Out-Null
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
            $entry = $archive.Entries | Where-Object { $_.FullName -like '*/eventlogs/system.evtx' } | Select-Object -First 1
            if ($entry) {
                $evtxPath = Join-Path $tmpDir 'system.evtx'
                $stream = $entry.Open()
                $fs = [System.IO.File]::Create($evtxPath)
                $stream.CopyTo($fs)
                $fs.Close(); $stream.Close()
                $archive.Dispose()
                $rawEvts = Get-WinEvent -Path $evtxPath -FilterXPath '*[System[(Level=1 or Level=2)]]' -ErrorAction SilentlyContinue
                foreach ($e in $rawEvts) {
                    $events.Add(@{
                        utc      = $e.TimeCreated.ToUniversalTime().ToString('o')
                        level    = $e.Level
                        provider = $e.ProviderName
                        eventId  = $e.Id
                        message  = if ($e.Message.Length -gt 200) { $e.Message.Substring(0,200) } else { $e.Message }
                    })
                }
            } else {
                $archive.Dispose()
                return 'ERR:no system.evtx entry in ZIP'
            }
            Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        } catch { return "ERR:exception during extraction: $($_.Exception.Message)" }
        return $events
    } -ArgumentList $zip

    $null = Wait-Job $job -Timeout 1800
    if ($job.State -eq 'Completed') {
        $result = Receive-Job $job
        if ($result -is [string] -and $result.StartsWith('ERR:')) {
            $evtxCache[$cp] = $result
        } else {
            $evtxCache[$cp] = @($result)
        }
    } else {
        Write-Host "[TIMEOUT] evtx extraction timed out after 1800s for: $cp" -ForegroundColor Yellow
        Stop-Job $job -ErrorAction SilentlyContinue
        $evtxCache[$cp] = "ERR:evtx extraction timed out after 1800s (ZIP: $($zips[0].Name), $('{0:N0}' -f ($zips[0].Length / 1MB)) MB)"
    }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    return $evtxCache[$cp]
}

function Format-CritEvents($allEvents, $submittedUtc, $stationTz) {
    if ($allEvents -is [string] -and $allEvents.StartsWith('ERR:')) {
        $reason = [System.Net.WebUtility]::HtmlEncode($allEvents.Substring(4))
        return "<span style='color:#c0392b;font-weight:700'>&#9888; $reason</span>"
    }
    if (-not $allEvents -or $allEvents.Count -eq 0) { return '(no events extracted)' }
    if (-not $stationTz) { $stationTz = @{ tz = $myt; abbr = 'MYT' } }
    $localTz = $stationTz.tz
    $tzAbbr = $stationTz.abbr
    $subDt = [datetime]::Parse($submittedUtc).ToUniversalTime()
    $lo = $subDt.AddHours(-1); $hi = $subDt.AddHours(1)
    $filtered = @($allEvents | Where-Object {
        $ts = [datetime]::Parse($_.utc).ToUniversalTime()
        $ts -ge $lo -and $ts -le $hi
    })
    if ($filtered.Count -eq 0) { return '(no events in +/-1h window)' }

    $sorted = @($filtered | Sort-Object { [datetime]::Parse($_.utc).ToUniversalTime() } -Descending)

    # Find closest to submitted
    $closestIdx = 0; $closestDiff = [double]::MaxValue
    for ($i = 0; $i -lt $sorted.Count; $i++) {
        $diff = [math]::Abs(([datetime]::Parse($sorted[$i].utc).ToUniversalTime() - $subDt).TotalSeconds)
        if ($diff -lt $closestDiff) { $closestDiff = $diff; $closestIdx = $i }
    }

    # ── EVTX_DESCRIPTIONS dictionary for human-readable event descriptions ──
    $EVTX_DESCRIPTIONS = @{
        '41|Kernel-Power' = 'Unexpected shutdown or restart (bugcheck/power loss)'
        '6008|EventLog' = 'Previous system shutdown was unexpected'
        '16|Kernel-Boot' = 'Fatal error processing restoration data after resume/reboot'
        '1796|TPM-WMI' = 'TPM firmware update validation failed (SBAT/DBX check)'
        '1801|TPM-WMI' = 'TPM WMI provider loaded firmware/board info'
        '7000|Service Control Manager' = 'Service failed to start (luafv -- LUA file virtualization)'
        '7043|Service Control Manager' = 'Service did not respond to start in time'
        '7031|Service Control Manager' = 'Service terminated unexpectedly'
        '7034|Service Control Manager' = 'Service terminated unexpectedly again'
        '10016|DistributedCOM' = 'DCOM permissions error on a server application'
        '1|Kernel-Power' = 'System entering sleep or hibernate'
        '42|Kernel-Power' = 'System entering sleep state'
        '6005|EventLog' = 'Event Log service started'
        '6006|EventLog' = 'Event Log service stopped'
        '6009|EventLog' = 'System booted with kernel version info'
        '46|volmgr' = 'Crash dump initialization failed'
    }
    function Get-EvtxDescription($eid, $prov) {
        $provShort = $prov -replace '^Microsoft-Windows-','' -replace '^Microsoft-',''
        $key = "$eid|$provShort"
        if ($EVTX_DESCRIPTIONS.ContainsKey($key)) { return $EVTX_DESCRIPTIONS[$key] }
        if ($prov -match 'TPM') { return 'TPM communication or firmware error' }
        if ($prov -match 'Service Control Manager') { return 'Windows service lifecycle event' }
        if ($prov -match 'Kernel-Power') { return 'System power state event' }
        if ($prov -match 'Kernel-Boot') { return 'Boot or resume error' }
        return "$provShort event"
    }

    # ── Rich-formatted snippet only (no summary bar / breakdown / notes) ──
    $subLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc($subDt, $localTz)
    $subLocalStr = $subLocal.ToString('M/d/yy H:mm:ss') + ' ' + $tzAbbr
    $insertedSeparator = $false
    $lines = [System.Collections.Generic.List[string]]::new()
    for ($i = 0; $i -lt $sorted.Count; $i++) {
        $evt = $sorted[$i]
        $utcDt = [datetime]::Parse($evt.utc).ToUniversalTime()
        $diffSec = ($utcDt - $subDt).TotalSeconds
        $isBefore = $diffSec -le 0
        $isClosest = $i -eq $closestIdx

        # Insert dashed red separator between post-failure and pre-failure events
        if ($isBefore -and -not $insertedSeparator) {
            $insertedSeparator = $true
            $lines.Add("<div style='border-top:2px dashed #c62828;margin:4px 0;padding:2px 0;text-align:center;font-size:9px;color:#c62828;font-weight:bold;font-family:Consolas,monospace'>&#9650; FAILURE POINT ($subLocalStr) &#9650;</div>")
        }

        # Level badge
        if ($evt.level -eq 1) {
            $levelBadge = "<span style='background:#c62828;color:#fff;padding:0 4px;border-radius:2px;font-size:9px;font-weight:bold'>CRIT</span>"
            $rowColor = '#c62828'; $rowBg = 'background:#fde8e8;'
        } else {
            $levelBadge = "<span style='background:#e65100;color:#fff;padding:0 4px;border-radius:2px;font-size:9px'>ERROR</span>"
            $rowColor = '#333'; $rowBg = ''
        }

        if ($isClosest) {
            $rowBg = 'background:#fff9c4;'
            $prefix = "<span style='color:#c62828;font-weight:bold'>&#9658;</span> "
        } else { $prefix = '' }

        # Source (provider) as compact pill -- strip Microsoft-Windows- prefix
        $provShort = $evt.provider -replace '^Microsoft-Windows-','' -replace '^Microsoft-',''
        $sourceHtml = "<span style='background:#e8eaf6;color:#37474f;padding:0 4px;border-radius:2px;font-size:9px'>$(HtmlEnc $provShort)</span>"

        # Timestamp (station local)
        $ts = [System.TimeZoneInfo]::ConvertTimeFromUtc($utcDt, $localTz)
        $tsStr = $ts.ToString('M/d/yy H:mm:ss') + ' ' + $tzAbbr
        $tsHtml = "<span style='color:#666;font-family:Consolas,monospace;font-size:10px'>$tsStr</span>"

        # EventID
        $eidHtml = "<span style='color:#1565c0;font-weight:600;font-size:10px'>EID $($evt.eventId)</span>"

        # Human-readable description (not raw message)
        $desc = Get-EvtxDescription $evt.eventId $evt.provider
        $descHtml = "<span style='color:$rowColor;font-size:10px'>$(HtmlEnc $desc)</span>"

        # Display order: Level | Date/Time | Source | EventID | Description (on second line)
        $lines.Add("<div style='${rowBg}padding:3px 4px;border-bottom:1px solid #eee;font-family:Segoe UI,sans-serif;line-height:1.4;word-break:break-word'>${prefix}${levelBadge} ${tsHtml} ${sourceHtml} ${eidHtml}<br>${descHtml}</div>")
    }

    $totalEvents = $lines.Count
    $allContent = $lines -join "`n"
    if ($totalEvents -le 30) {
        return "<div style='max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;padding:2px;background:#fafafa'>$allContent</div>"
    }
    # Show 30 lines centered around the closest marker
    $previewStart = [math]::Max(0, $closestIdx - 15)
    $previewEnd = [math]::Min($totalEvents, $previewStart + 30)
    if ($previewEnd - $previewStart -lt 30) { $previewStart = [math]::Max(0, $previewEnd - 30) }
    $previewLines = $lines.GetRange($previewStart, $previewEnd - $previewStart)
    $preview = ($previewLines -join "`n")
    $rangeNote = "<div style='font-size:10px;color:#888;margin-bottom:2px'>Showing events $($previewStart+1)-$previewEnd of $totalEvents (centered on marker)</div>"
    return @"
$rangeNote<div style='max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;padding:2px;background:#fafafa'>$preview</div>
<div style='display:none' class='evtx-full'>$allContent</div>
<button class='evtx-expand-btn' data-title='System.evtx Critical/Errors ($totalEvents events)' style='margin-top:4px;padding:2px 8px;font-size:11px;cursor:pointer;background:#eef;border:1px solid #99b;border-radius:3px'>View All Events ($totalEvents events)</button>
"@
}


# -- BSOD Info (full log display with draggable modal) ------
$bsodCache = @{}
function Get-BsodInfo($cp, $submittedUtc, $stationTz) {
    if (-not $stationTz) { $stationTz = @{ tz = $myt; abbr = 'MYT' } }
    $localTz = $stationTz.tz
    $tzAbbr = $stationTz.abbr
    if ($bsodCache.ContainsKey($cp)) {
        $cached = $bsodCache[$cp]
    } else {
        $cached = @{ bsod = @(); dmpFiles = @(); error = $null }
        if (-not $cp -or -not (Test-Path $cp)) {
            $cached.error = if (-not $cp) { 'no cleanup path' } else { "cleanup path not found: $cp" }
            $bsodCache[$cp] = $cached
        }
        else {
            $zips = @(Get-ChildItem $cp -Filter '*.zip' -ErrorAction SilentlyContinue)
            if ($zips.Count -eq 0) { $cached.error = "no ZIP files in cleanup path: $cp"; $bsodCache[$cp] = $cached }
            else {
                $outFile = Join-Path $env:TEMP "bsod_scan_$(Get-Random).txt"
                $job = Start-Job -ScriptBlock {
                    param($zipPath, $outPath)
                    $results = @()
                    try {
                        Add-Type -AssemblyName System.IO.Compression.FileSystem
                        $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
                        $bsodEntries = @($archive.Entries | Where-Object { $_.Name -ieq 'bsod.log' })
                        foreach ($entry in $bsodEntries) {
                            $reader = New-Object System.IO.StreamReader($entry.Open())
                            $content = $reader.ReadToEnd()
                            $reader.Close()

                            $debugTime = ''
                            if ($content -match 'Debug session time:\s*(.+)') { $debugTime = $matches[1].Trim() }

                            $folder = $entry.FullName -replace '/[^/]+$', ''
                            $dmpEntry = $archive.Entries | Where-Object {
                                $_.FullName -like "$folder/*" -and $_.Name -like '*.dmp'
                            } | Select-Object -First 1
                            $dmpName = if ($dmpEntry) { $dmpEntry.Name } else { '(none)' }
                            $dmpSize = if ($dmpEntry) { '{0:N1} MB' -f ($dmpEntry.Length / 1MB) } else { '' }

                            $contentB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($content))
                            $results += "$($entry.FullName)|$debugTime|$dmpName|$dmpSize|$contentB64"
                        }
                        # Scan for all .dmp files in ZIP
                        $allDmpEntries = @($archive.Entries | Where-Object { $_.Name -like '*.dmp' })
                        foreach ($de in $allDmpEntries) {
                            $results += "DMP|$($de.FullName)|$($de.Length)"
                        }
                        $archive.Dispose()
                    } catch { $results += "ERROR|$($_.Exception.Message)|||" }
                    $results | Out-File $outPath -Encoding utf8
                } -ArgumentList $zips[0].FullName, $outFile

                $null = Wait-Job $job -Timeout 120
                if ($job.State -ne 'Completed') {
                    Write-Host "[TIMEOUT] BSOD extraction timed out after 120s for: $cp" -ForegroundColor Yellow
                    Stop-Job $job -ErrorAction SilentlyContinue
                    $cached.error = "BSOD extraction timed out after 120s (ZIP: $($zips[0].Name), $('{0:N0}' -f ($zips[0].Length / 1MB)) MB)"
                }
                if ($job.State -eq 'Completed' -and (Test-Path $outFile)) {
                    $rawLines = @(Get-Content $outFile -ErrorAction SilentlyContinue | Where-Object { $_.Trim() })
                    foreach ($line in $rawLines) {
                        $parts = $line -split '\|', 5
                        if ($parts[0] -eq 'DMP' -and $parts.Count -ge 3) {
                            $cached.dmpFiles += @{
                                path = $parts[1]
                                size = $parts[2]
                            }
                        } elseif ($parts.Count -ge 5 -and $parts[0] -ne 'ERROR') {
                            $fullContent = ''
                            try { $fullContent = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($parts[4])) } catch {}
                            $cached.bsod += @{
                                path        = $parts[0]
                                debugTime   = $parts[1]
                                dmpName     = $parts[2]
                                dmpSize     = $parts[3]
                                fullContent = $fullContent
                            }
                        }
                    }
                    Remove-Item $outFile -Force -ErrorAction SilentlyContinue
                }
                Remove-Job $job -Force -ErrorAction SilentlyContinue
                $bsodCache[$cp] = $cached
            }
        }
    }

    if ($cached.bsod.Count -eq 0) {
        $errHtml = ''
        if ($cached.error) {
            $errHtml = "<div style='color:#c0392b;font-weight:700;margin-bottom:4px'>&#9888; $([System.Net.WebUtility]::HtmlEncode($cached.error))</div>"
        }
        if ($cached.dmpFiles.Count -gt 0) {
            $dmpHtml = @("<div style='font-size:12px;font-family:Consolas,monospace'>")
            $dmpHtml += $errHtml
            $dmpHtml += "<div style='color:#888;margin-bottom:4px'>(no bsod.log found in ZIP)</div>"
            $dmpHtml += "<div style='margin-bottom:4px'><b>Dump files found ($($cached.dmpFiles.Count)):</b></div>"
            foreach ($d in $cached.dmpFiles) {
                $sizeStr = '{0:N1} MB' -f ([long]$d.size / 1MB)
                $nameEnc = [System.Net.WebUtility]::HtmlEncode($d.path)
                $dmpHtml += "<div style='margin-left:8px'>&#128190; $nameEnc ($sizeStr)</div>"
            }
            $dmpHtml += "</div>"
            return ($dmpHtml -join "`n")
        }
        if ($cached.error) {
            return "<span style='color:#c0392b;font-weight:700'>&#9888; $([System.Net.WebUtility]::HtmlEncode($cached.error))</span>"
        }
        return '<span style="color:#888">(no bsod.log and no .dmp found in ZIP)</span>'
    }

    # Parse debug times and compute UTC for each BSOD
    $subDt = [datetime]::Parse($submittedUtc).ToUniversalTime()
    $entries = @()
    foreach ($b in $cached.bsod) {
        $utcDebug = $null
        $rawDebug = $b.debugTime
        if ($rawDebug -match '(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\.\d+\s+(\d{4})\s*\(UTC\s*([+-])\s*(\d{1,2}):(\d{2})\)') {
            try {
                $dtStr = "$($matches[1]) $($matches[2])"
                $localDt = [datetime]::ParseExact($dtStr, 'ddd MMM d HH:mm:ss yyyy', [System.Globalization.CultureInfo]::InvariantCulture)
            } catch {
                try { $localDt = [datetime]::ParseExact($dtStr, 'ddd MMM dd HH:mm:ss yyyy', [System.Globalization.CultureInfo]::InvariantCulture) } catch { $localDt = $null }
            }
            if ($localDt) {
                $sign = if ($matches[3] -eq '+') { -1 } else { 1 }
                $offsetH = [int]$matches[4]
                $offsetM = [int]$matches[5]
                $utcDebug = $localDt.AddHours($sign * $offsetH).AddMinutes($sign * $offsetM)
            }
        }
        $diffMin = if ($utcDebug) { [math]::Abs(($utcDebug - $subDt).TotalMinutes) } else { [double]::MaxValue }
        $entries += @{ data = $b; utcDebug = $utcDebug; diffMin = $diffMin }
    }

    # Find closest
    $closestIdx = 0; $closestDiff = [double]::MaxValue
    for ($i = 0; $i -lt $entries.Count; $i++) {
        if ($entries[$i].diffMin -lt $closestDiff) { $closestDiff = $entries[$i].diffMin; $closestIdx = $i }
    }

    # Format output as HTML
    $subLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc($subDt, $localTz)
    $html = @("<div style='font-size:12px;font-family:Consolas,monospace'>")
    $html += "<div style='margin-bottom:6px;color:#555'>Submitted: <b>$($subLocal.ToString('M/d/yy H:mm:ss')) $tzAbbr</b> | Found $($entries.Count) BSOD.log(s)</div>"

    for ($i = 0; $i -lt $entries.Count; $i++) {
        $e = $entries[$i]
        $b = $e.data
        $isClosest = ($i -eq $closestIdx)
        $border = if ($isClosest) { 'border:2px solid #c0392b;background:#fff9c4;' } else { 'border:1px solid #ccc;background:#f9f9f9;' }
        $html += "<div style='$border;padding:6px;margin-bottom:4px;border-radius:3px'>"

        if ($isClosest) {
            $html += "<div style='color:#c0392b;font-weight:700;margin-bottom:3px'>*** CLOSEST TO SUBMITTED ***</div>"
        }

        # Debug time
        $debugDisplay = $b.debugTime
        if ($e.utcDebug) {
            $localDebug = [System.TimeZoneInfo]::ConvertTimeFromUtc([System.DateTime]::SpecifyKind($e.utcDebug, [System.DateTimeKind]::Utc), $localTz)
            $debugDisplay = "$($localDebug.ToString('M/d/yy H:mm:ss')) $tzAbbr"
            $diffStr = if ($e.diffMin -lt 60) { "{0:N0} min" -f $e.diffMin } else { "{0:N1} hr" -f ($e.diffMin / 60) }
            $html += "<div>Debug Time: <b>$debugDisplay</b> (diff: $diffStr)</div>"
        } else {
            $html += "<div>Debug Time: $([System.Net.WebUtility]::HtmlEncode($debugDisplay))</div>"
        }

        $html += "<div style='color:#666;margin-bottom:4px'>Dump: $([System.Net.WebUtility]::HtmlEncode($b.dmpName)) ($([System.Net.WebUtility]::HtmlEncode($b.dmpSize)))</div>"

        # Folder path
        $folderShort = $b.path -replace '^.*?/(bsod_\d+)', '$1' -replace '/[Bb][Ss][Oo][Dd]\.[Ll][Oo][Gg]$', ''
        $html += "<div style='color:#888;font-size:11px;margin-bottom:4px'>Folder: $([System.Net.WebUtility]::HtmlEncode($folderShort))</div>"

        # Full bsod.log content inline (scrollable)
        $contentEnc = [System.Net.WebUtility]::HtmlEncode($b.fullContent)
        $lineCount = ($b.fullContent -split "`n").Count
        $html += "<pre class='bsod-log-content' style='white-space:pre-wrap;margin:0;max-height:200px;overflow-y:auto;background:#fff;padding:4px;border:1px solid #ddd;border-radius:2px;font-size:11px'>$contentEnc</pre>"

        if ($lineCount -gt 30) {
            $titleAttr = [System.Net.WebUtility]::HtmlEncode("BSOD.log - $folderShort ($lineCount lines)")
            $html += "<button class='bsod-expand-btn' data-title='$titleAttr' style='margin-top:4px;padding:2px 10px;font-size:11px;cursor:pointer;background:#4a6fa5;color:#fff;border:none;border-radius:3px'>View Full Log ($lineCount lines)</button>"
        }

        $html += "</div>"
    }
    # List all .dmp files found in ZIP
    if ($cached.dmpFiles.Count -gt 0) {
        $html += "<div style='margin-top:6px;padding:4px;border-top:1px solid #ccc'>"
        $html += "<div style='margin-bottom:3px'><b>All dump files ($($cached.dmpFiles.Count)):</b></div>"
        foreach ($d in $cached.dmpFiles) {
            $sizeStr = '{0:N1} MB' -f ([long]$d.size / 1MB)
            $nameEnc = [System.Net.WebUtility]::HtmlEncode($d.path)
            $html += "<div style='margin-left:8px;font-size:11px'>&#128190; $nameEnc ($sizeStr)</div>"
        }
        $html += "</div>"
    }
    $html += "</div>"
    return ($html -join "`n")
}

# ── Axon Insights Formatter (axon-server data + genimcp priority) ────────────
# Load insight table JSON (generated by gen_insight_table.py from axon-server raw data)
$insightTableJson = $null
# Insight table JSON path -- set by agent per query (e.g., insight_table_nvlp.json, insight_table_hx_sst.json)
$insightTablePath = Join-Path $PSScriptRoot (Join-Path 'output' 'insight_table.json')
if (Test-Path $insightTablePath) {
    $insightTableJson = Get-Content $insightTablePath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Format-AxonInsights($f) {
    if (-not $f.axonId) { return HtmlEnc '(no DebugSnapshotId)' }

    $link = "https://axonsv.app.intel.com/apps/record-viewer/$($f.axonId)/intel-svtools-report-v1?tab=report"

    # Try to load insight table from pre-generated JSON (keyed by Axon GUID)
    $tableData = $null
    if ($script:insightTableJson -and $script:insightTableJson.PSObject.Properties[$f.axonId]) {
        $tableData = $script:insightTableJson.($f.axonId)
    }
    if (-not $tableData) {
        # Fallback to old-style genimcp-only display
        $insights = $f.axonInsights
        if (-not $insights -or $insights.Count -eq 0) {
            $reason = if (-not (Test-Path $insightTablePath)) { "insight table file not found: $insightTablePath" }
                      elseif (-not $script:insightTableJson) { "insight table JSON failed to load" }
                      else { "no entry for axonId $($f.axonId) in insight table" }
            return "<div><a href='$link' target='_blank' style='font-size:11px'>Link to Statuscope</a></div><span style='color:#c0392b;font-weight:700'>&#9888; $([System.Net.WebUtility]::HtmlEncode($reason))</span>"
        }
        $colorMap = @{ 1='#7b2d8e'; 2='#c0392b'; 3='#e67e22'; 6='#2980b9'; 10='#888888' }
        $boldSet  = @(1, 2)
        $summaryEnc = HtmlEnc $f.axonSummary
        $summaryColor = '#2980b9'
        foreach ($ins in $insights) { if ($ins.p -le 2) { $summaryColor = $colorMap[[int]$ins.p]; break } }
        $lines = @("<span style='font-weight:700;color:$summaryColor'>$summaryEnc</span>")
        $sorted = $insights | Sort-Object { [int]$_.p }
        foreach ($ins in $sorted) {
            $p = [int]$ins.p
            $c = if ($colorMap.ContainsKey($p)) { $colorMap[$p] } else { '#333' }
            $w = if ($boldSet -contains $p) { 'font-weight:700;' } else { '' }
            $lines += "<span style='color:$c;$w'>[P$p] $(HtmlEnc $ins.m)</span>"
        }
        $body = $lines -join "`n"
        return "<div style='max-height:300px;overflow-y:auto'><pre style='white-space:pre-wrap;margin:0'>$body</pre></div><a href='$link' target='_blank'>Link to Statuscope</a>"
    }

    # New approach: inline scrollable insight table + expand button for full-screen modal
    $summaryEnc = HtmlEnc $tableData.summary
    $total = $tableData.total
    $modalId = "insightModal_$($f.fname)"

    $html = @"
<div style='margin-bottom:6px'>
  <span style='font-weight:700;color:#7b2d8e'>$summaryEnc</span>
</div>
<div style='margin-bottom:4px'>
  <a href='$link' target='_blank' style='font-size:11px'>Link to Statuscope</a>
  <button class='insight-expand-btn' onclick='openInsightModal("$modalId")' style='margin-left:8px;padding:2px 8px;font-size:10px;background:#4a6fa5;color:#fff;border:1px solid #365f8a;border-radius:3px;cursor:pointer' title='Open full-screen view'>&#x26F6; Expand ($total)</button>
</div>
<div style='max-height:320px;overflow:auto;border:1px solid #ccc;border-radius:4px;margin-top:4px'>
$($tableData.table_html)
</div>
<div id='$modalId' style='display:none'>$($tableData.table_html)</div>
"@
    return $html
}

# ── Report Parameters (populated dynamically by the agent per query) ────────
$project   = 'nvl_fv_or'   # Default project, override as needed
$cycle     = ''             # Set by the agent, e.g. 'RFP_NVL_S28_B0_ES2_AWR'
$suite     = ''             # Set by the agent, e.g. 'NVL-S_Fullchip_Stability'
$now       = [System.TimeZoneInfo]::ConvertTimeFromUtc([datetime]::UtcNow, $myt)
$tsDisplay = $now.ToString('M/d/yyyy h:mm:ss tt') + ' MYT'
$uniqueBuckets = ($failures | ForEach-Object { $_.bucket } | Sort-Object -Unique).Count

$rows = ''
$rowNum = 0
foreach ($f in $failures) {
    $rowNum++
    $sTz = Get-StationTimeZone $f.systemName
    $subUtc = [datetime]::Parse($f.submitted).ToUniversalTime()
    $subLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc($subUtc, $sTz.tz)
    $subDisplay = $subLocal.ToString('M/d/yy H:mm') + ' ' + $sTz.abbr

    $ngaUrl = "https://nga-prod.laas.intel.com/#/$project/failureManagement/failures/$($f.fid)"

    # Enrichment
    $execMsg = Get-ExecMessages $f.cleanup $f.submitted ($f.sigs -split '\|' | Select-Object -First 1).Trim() $f.testRunId $f.fname $sTz
    Write-Host "  [$rowNum] ExecMsg done for $($f.fname)"

    $evtxAll = Get-EvtxEvents $f.cleanup
    $critHtml = Format-CritEvents $evtxAll $f.submitted $sTz
    Write-Host "  [$rowNum] EvtxEvents done for $($f.fname)"

    $bsodInfo = Get-BsodInfo $f.cleanup $f.submitted $sTz
    Write-Host "  [$rowNum] BSOD done for $($f.fname)"

    $axonHtml = Format-AxonInsights $f
    Write-Host "  [$rowNum] Axon done for $($f.fname)"

    $bgClass = if ($rowNum % 2 -eq 0) { ' class="even"' } else { '' }
    $rows += @"
<tr$bgClass>
<td class="num">$rowNum</td>
<td class="finfo"><div style='font-size:12px;line-height:1.6'>
  <div><b>Run State:</b> <span style='font-weight:700;color:#c0392b'>$(HtmlEnc $f.runState)</span></div>
  <div><b>Failure Name:</b> <a href="$ngaUrl" target="_blank" style='font-weight:700'>$(HtmlEnc $f.fname)</a></div>
  <div><b>Bucket:</b> <span style='color:#2c3e50'>$(HtmlEnc $f.bucket)</span></div>
  <div><b>Signatures:</b> <span style='color:#555;font-size:11px'>$(HtmlEnc $f.sigs)</span></div>
  <div style='background:#fff9c4;padding:2px 4px;border-radius:3px;display:inline-block'><b>Submitted:</b> <span style='color:#333;font-weight:700'>$subDisplay</span></div>
</div></td>
<td class="exec">$execMsg</td>
<td>$critHtml</td>
<td>$bsodInfo</td>
<td class="axon">$axonHtml</td>
</tr>
"@
}

$html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Unsighted Failures &mdash; $suite $cycle</title>
<style>
body { font-family: Segoe UI, Arial, sans-serif; margin: 12px; background: #fafafa; }
h2 { margin: 0 0 4px; }
.summary { color: #555; margin-bottom: 8px; }
.toolbar { margin-bottom: 8px; display: flex; gap: 10px; align-items: center; }
.toolbar input { padding: 4px 8px; width: 300px; border: 1px solid #ccc; border-radius: 3px; }
.toolbar button { padding: 4px 12px; border: 1px solid #aaa; border-radius: 3px; cursor: pointer; background: #fff; }
.scroll-wrap { overflow-x: auto; padding-right: 8px; }
table { border-collapse: collapse; width: 100%; min-width: 1600px; }
th, td { border: 1px solid #d0d0d0; padding: 5px 8px; text-align: left; vertical-align: top; white-space: nowrap; font-size: 13px; }
th { background: #4a6fa5; color: #fff; position: sticky; top: 0; z-index: 2; cursor: pointer; user-select: none; }
th .resize { position: absolute; right: -4px; top: 0; width: 12px; height: 100%; cursor: col-resize; z-index: 3; }
th .filter-input { display: block; width: 90%; margin: 3px auto 0; padding: 2px 4px; font-size: 11px; border: 1px solid #88a0c0; border-radius: 2px; color: #333; }
#ftable > tbody > tr.even > td { background: #f0f4f8; }
td pre { margin: 0; font-family: Consolas, monospace; font-size: 12px; white-space: pre-wrap; }
.finfo { min-width: 200px; max-width: 300px; white-space: normal !important; word-break: break-all; overflow-wrap: break-word; }
.num { text-align: center; width: 30px; }
a { color: #2471a3; }
/* BSOD draggable modal */
.bsod-modal { position:fixed; top:100px; left:200px; width:800px; height:600px; z-index:9999;
  border:2px solid #4a6fa5; border-radius:6px; background:#fff; box-shadow:0 8px 32px rgba(0,0,0,0.3);
  display:flex; flex-direction:column; }
.bsod-modal-header { background:#4a6fa5; color:#fff; padding:8px 12px; cursor:move; display:flex;
  justify-content:space-between; align-items:center; font-family:Segoe UI,Arial,sans-serif; font-size:13px;
  font-weight:600; border-radius:4px 4px 0 0; user-select:none; }
.bsod-modal-body { flex:1; overflow:auto; padding:10px; }
.bsod-modal-body pre { white-space:pre-wrap; margin:0; font-family:Consolas,monospace; font-size:12px; }
.bsod-modal-resize { position:absolute; right:0; bottom:0; width:16px; height:16px; cursor:nwse-resize;
  background:linear-gradient(135deg, transparent 50%, #4a6fa5 50%); border-radius:0 0 4px 0; }
.bsod-expand-btn:hover { background:#365f8a !important; }
/* Insight Summary draggable modal */
.insight-modal { position:fixed; top:60px; left:80px; width:90vw; height:80vh; z-index:10000;
  border:2px solid #1a237e; border-radius:6px; background:#fff; box-shadow:0 8px 32px rgba(0,0,0,0.4);
  display:flex; flex-direction:column; }
.insight-modal-header { background:#1a237e; color:#fff; padding:8px 12px; cursor:move; display:flex;
  justify-content:space-between; align-items:center; font-family:Segoe UI,Arial,sans-serif; font-size:13px;
  font-weight:600; border-radius:4px 4px 0 0; user-select:none; }
.insight-modal-body { flex:1; overflow:auto; padding:10px; }
.insight-modal-body table { min-width:1400px; }
.insight-modal-body table th { position:sticky; top:0; }
.insight-modal-resize { position:absolute; right:0; bottom:0; width:16px; height:16px; cursor:nwse-resize;
  background:linear-gradient(135deg, transparent 50%, #1a237e 50%); border-radius:0 0 4px 0; }
.insight-expand-btn:hover { background:#365f8a !important; }
/* Exec Messages draggable modal */
.exec-modal { position:fixed; top:60px; left:80px; width:90vw; height:80vh; z-index:10000;
  border:2px solid #2c3e50; border-radius:6px; background:#fff; box-shadow:0 8px 32px rgba(0,0,0,0.4);
  display:flex; flex-direction:column; }
.exec-modal-header { background:#2c3e50; color:#fff; padding:8px 12px; cursor:move; display:flex;
  justify-content:space-between; align-items:center; font-family:Segoe UI,Arial,sans-serif; font-size:13px;
  font-weight:600; border-radius:4px 4px 0 0; user-select:none; }
.exec-modal-body { flex:1; overflow:auto; padding:0; }
.exec-modal-body table { width:100%; }
.exec-modal-body table th { position:sticky; top:0; }
.exec-modal-resize { position:absolute; right:0; bottom:0; width:16px; height:16px; cursor:nwse-resize;
  background:linear-gradient(135deg, transparent 50%, #2c3e50 50%); border-radius:0 0 4px 0; }
.exec-expand-btn:hover { background:#365f8a !important; }
/* Inline exec table within cell */
td.exec > div > div[style*='max-height'] table { font-size:11px; border-collapse:collapse; min-width:900px; }
td.exec > div > div[style*='max-height'] table th { position:sticky; top:0; z-index:1; font-size:10px; padding:3px 5px; }
td.exec > div > div[style*='max-height'] table td { padding:2px 5px; font-size:10px; }
/* Inline insight table within cell */
td.axon > div > div[style*='max-height'] table { font-size:11px; border-collapse:collapse; min-width:1200px; }
td.axon > div > div[style*='max-height'] table th { position:sticky; top:0; z-index:1; font-size:10px; padding:3px 5px; }
td.axon > div > div[style*='max-height'] table td { padding:2px 5px; font-size:10px; }
</style>
</head>
<body>
<h2>Unsighted Failures &mdash; $suite $cycle ($($failures.Count) failures, SightingId eq null)</h2>
<div class="summary">Total: $($failures.Count) failures | $uniqueBuckets unique buckets | Generated: $tsDisplay</div>
<div class="toolbar">
  <input type="text" id="search" placeholder="Search all columns..." oninput="filterTable()">
  <button id="wrapBtn" onclick="toggleWrap()">Enable Word Wrap</button>
</div>
<div class="scroll-wrap">
<table id="ftable">
<thead><tr>
<th style="position:relative">#<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="0" placeholder="Filter"></th>
<th style="position:relative">Failure Info<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="1" placeholder="Filter"></th>
<th style="position:relative">Execution Messages<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="2" placeholder="Filter"></th>
<th style="position:relative">System.evtx Critical/Errors<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="3" placeholder="Filter"></th>
<th style="position:relative">BSOD Info<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="4" placeholder="Filter"></th>
<th style="position:relative">Statuscope Summary<div class="resize"></div><input class="filter-input" onkeyup="filterTable()" data-col="5" placeholder="Filter"></th>
</tr></thead>
<tbody>
$rows
</tbody>
</table>
</div>
<div id="bsodLogModal" class="bsod-modal" style="display:none">
  <div class="bsod-modal-header">
    <span id="bsodModalTitle">BSOD.log</span>
    <button onclick="closeBsodLogModal()" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 6px;line-height:1">&times;</button>
  </div>
  <div class="bsod-modal-body"><pre id="bsodModalContent"></pre></div>
  <div class="bsod-modal-resize"></div>
</div>
<div id="evtxModal" class="bsod-modal" style="display:none">
  <div class="bsod-modal-header">
    <span id="evtxModalTitle">System.evtx Events</span>
    <button onclick="closeEvtxModal()" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 6px;line-height:1">&times;</button>
  </div>
  <div class="bsod-modal-body"><div id="evtxModalContent" style="font-family:Consolas,monospace;font-size:12px"></div></div>
  <div class="bsod-modal-resize"></div>
</div>
<div id="insightModal" class="insight-modal" style="display:none">
  <div class="insight-modal-header">
    <span id="insightModalTitle">Insight Summary</span>
    <button onclick="closeInsightModal()" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 6px;line-height:1">&times;</button>
  </div>
  <div class="insight-modal-body" id="insightModalContent"></div>
  <div class="insight-modal-resize"></div>
</div>
<div id="execModal" class="exec-modal" style="display:none">
  <div class="exec-modal-header">
    <span id="execModalTitle">Execution Messages</span>
    <button onclick="closeExecModal()" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 6px;line-height:1">&times;</button>
  </div>
  <div class="exec-modal-body" id="execModalContent"></div>
  <div class="exec-modal-resize"></div>
</div>
<script>
// Search + per-column filter
function filterTable() {
  var search = document.getElementById('search').value.toLowerCase();
  var filters = [];
  document.querySelectorAll('.filter-input').forEach(function(inp) {
    filters.push({ col: parseInt(inp.getAttribute('data-col')), val: inp.value.toLowerCase() });
  });
  var rows = document.querySelectorAll('#ftable tbody tr');
  var num = 0;
  rows.forEach(function(row) {
    var cells = row.querySelectorAll('td');
    var text = row.textContent.toLowerCase();
    var show = !search || text.indexOf(search) >= 0;
    if (show) {
      filters.forEach(function(f) {
        if (f.val && cells[f.col]) {
          if (cells[f.col].textContent.toLowerCase().indexOf(f.val) < 0) show = false;
        }
      });
    }
    row.style.display = show ? '' : 'none';
    if (show) { num++; cells[0].textContent = num; }
  });
}

// Word wrap toggle
var wrapped = false;
function toggleWrap() {
  wrapped = !wrapped;
  document.querySelectorAll('#ftable td').forEach(function(td) {
    td.style.whiteSpace = wrapped ? 'normal' : 'nowrap';
  });
  document.getElementById('wrapBtn').textContent = wrapped ? 'Disable Word Wrap' : 'Enable Word Wrap';
}

// Column sorting
var sortCol = -1, sortAsc = true;
document.querySelectorAll('#ftable thead th').forEach(function(th, idx) {
  th.addEventListener('click', function(e) {
    if (e.target.classList.contains('filter-input') || e.target.classList.contains('resize')) return;
    if (sortCol === idx) { sortAsc = !sortAsc; } else { sortCol = idx; sortAsc = true; }
    var tbody = document.querySelector('#ftable tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
      var at = a.querySelectorAll('td')[idx].textContent.trim();
      var bt = b.querySelectorAll('td')[idx].textContent.trim();
      return sortAsc ? at.localeCompare(bt, undefined, {numeric: true}) : bt.localeCompare(at, undefined, {numeric: true});
    });
    rows.forEach(function(r, i) { tbody.appendChild(r); r.querySelectorAll('td')[0].textContent = i + 1; });
    document.querySelectorAll('#ftable thead th').forEach(function(h) { h.removeAttribute('data-sort'); });
    th.setAttribute('data-sort', sortAsc ? 'asc' : 'desc');
  });
});

// Column resizing
document.querySelectorAll('.resize').forEach(function(grip) {
  grip.addEventListener('mousedown', function(e) {
    e.preventDefault();
    var th = grip.parentElement;
    var startX = e.pageX, startW = th.offsetWidth;
    function onMove(ev) { th.style.width = (startW + ev.pageX - startX) + 'px'; th.style.minWidth = th.style.width; }
    function onUp() { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
});

// Column reordering via drag-and-drop
(function() {
  var headers = document.querySelectorAll('#ftable thead th');
  var dragIdx = -1;
  headers.forEach(function(th, idx) {
    th.setAttribute('draggable', 'true');
    th.addEventListener('dragstart', function(e) { dragIdx = idx; e.dataTransfer.effectAllowed = 'move'; });
    th.addEventListener('dragover', function(e) { e.preventDefault(); });
    th.addEventListener('drop', function(e) {
      e.preventDefault();
      var dropIdx = idx;
      if (dragIdx === dropIdx) return;
      var table = document.getElementById('ftable');
      var allRows = table.querySelectorAll('tr');
      allRows.forEach(function(row) {
        var cells = Array.from(row.children);
        var dragged = cells[dragIdx];
        var target = cells[dropIdx];
        if (dragIdx < dropIdx) { row.insertBefore(dragged, target.nextSibling); }
        else { row.insertBefore(dragged, target); }
      });
      dragIdx = -1;
    });
  });
})();

// BSOD Full Log Modal
document.addEventListener('click', function(e) {
  if (!e.target.classList.contains('bsod-expand-btn')) return;
  var title = e.target.getAttribute('data-title');
  var pre = e.target.parentElement.querySelector('pre');
  if (pre) openBsodLogModal(pre.textContent, title);
});

function openBsodLogModal(content, title) {
  var m = document.getElementById('bsodLogModal');
  document.getElementById('bsodModalTitle').textContent = title;
  document.getElementById('bsodModalContent').textContent = content;
  m.style.display = 'flex';
  m.style.width = '800px';
  m.style.height = '600px';
  m.style.left = Math.max(50, (window.innerWidth - 800) / 2) + 'px';
  m.style.top = Math.max(50, (window.innerHeight - 600) / 2) + 'px';
}

function closeBsodLogModal() {
  document.getElementById('bsodLogModal').style.display = 'none';
}

// Drag & resize for BSOD modal
(function() {
  var m = document.getElementById('bsodLogModal');
  if (!m) return;
  var header = m.querySelector('.bsod-modal-header');
  var grip = m.querySelector('.bsod-modal-resize');
  var dragging = false, resizing = false, dx, dy, rx, ry, rw, rh;

  header.addEventListener('mousedown', function(e) {
    if (e.target.tagName === 'BUTTON') return;
    dragging = true;
    dx = e.clientX - m.offsetLeft;
    dy = e.clientY - m.offsetTop;
    e.preventDefault();
  });

  grip.addEventListener('mousedown', function(e) {
    resizing = true;
    rx = e.clientX; ry = e.clientY;
    rw = m.offsetWidth; rh = m.offsetHeight;
    e.preventDefault();
  });

  document.addEventListener('mousemove', function(e) {
    if (dragging) {
      m.style.left = (e.clientX - dx) + 'px';
      m.style.top = (e.clientY - dy) + 'px';
    }
    if (resizing) {
      m.style.width = Math.max(300, rw + e.clientX - rx) + 'px';
      m.style.height = Math.max(200, rh + e.clientY - ry) + 'px';
    }
  });

  document.addEventListener('mouseup', function() {
    dragging = false;
    resizing = false;
  });
})();

// Evtx Full Events Modal
document.addEventListener('click', function(e) {
  if (!e.target.classList.contains('evtx-expand-btn')) return;
  var title = e.target.getAttribute('data-title');
  var fullDiv = e.target.parentElement.querySelector('.evtx-full');
  if (fullDiv) openEvtxModal(fullDiv.innerHTML, title);
});

function openEvtxModal(contentHtml, title) {
  var m = document.getElementById('evtxModal');
  document.getElementById('evtxModalTitle').textContent = title;
  var contentDiv = document.getElementById('evtxModalContent');
  contentDiv.innerHTML = contentHtml;
  m.style.display = 'flex';
  m.style.width = '900px';
  m.style.height = '600px';
  m.style.left = Math.max(50, (window.innerWidth - 900) / 2) + 'px';
  m.style.top = Math.max(50, (window.innerHeight - 600) / 2) + 'px';
  // Auto-scroll to the >>> marker row
  setTimeout(function() {
    var spans = contentDiv.querySelectorAll('span');
    for (var i = 0; i < spans.length; i++) {
      if (spans[i].style.background === 'rgb(255, 249, 196)' || spans[i].textContent.indexOf('>>>') === 0 || spans[i].textContent.indexOf('&gt;&gt;&gt;') === 0) {
        spans[i].scrollIntoView({ block: 'center' });
        break;
      }
    }
  }, 50);
}

function closeEvtxModal() {
  document.getElementById('evtxModal').style.display = 'none';
}

// Drag & resize for evtx modal
(function() {
  var m = document.getElementById('evtxModal');
  if (!m) return;
  var header = m.querySelector('.bsod-modal-header');
  var grip = m.querySelector('.bsod-modal-resize');
  var dragging = false, resizing = false, dx, dy, rx, ry, rw, rh;

  header.addEventListener('mousedown', function(e) {
    if (e.target.tagName === 'BUTTON') return;
    dragging = true;
    dx = e.clientX - m.offsetLeft;
    dy = e.clientY - m.offsetTop;
    e.preventDefault();
  });

  grip.addEventListener('mousedown', function(e) {
    resizing = true;
    rx = e.clientX; ry = e.clientY;
    rw = m.offsetWidth; rh = m.offsetHeight;
    e.preventDefault();
  });

  document.addEventListener('mousemove', function(e) {
    if (dragging) {
      m.style.left = (e.clientX - dx) + 'px';
      m.style.top = (e.clientY - dy) + 'px';
    }
    if (resizing) {
      m.style.width = Math.max(300, rw + e.clientX - rx) + 'px';
      m.style.height = Math.max(200, rh + e.clientY - ry) + 'px';
    }
  });

  document.addEventListener('mouseup', function() {
    dragging = false;
    resizing = false;
  });
})();

// Insight Summary Modal
function openInsightModal(sourceId) {
  var src = document.getElementById(sourceId);
  if (!src) return;
  var m = document.getElementById('insightModal');
  document.getElementById('insightModalContent').innerHTML = src.innerHTML;
  m.style.display = 'flex';
  m.style.width = '90vw';
  m.style.height = '80vh';
  m.style.left = Math.max(30, (window.innerWidth * 0.05)) + 'px';
  m.style.top = Math.max(30, (window.innerHeight * 0.1)) + 'px';
}
function closeInsightModal() {
  document.getElementById('insightModal').style.display = 'none';
}

// Drag & resize for insight modal
(function() {
  var m = document.getElementById('insightModal');
  if (!m) return;
  var header = m.querySelector('.insight-modal-header');
  var grip = m.querySelector('.insight-modal-resize');
  var dragging = false, resizing = false, dx, dy, rx, ry, rw, rh;
  header.addEventListener('mousedown', function(e) {
    if (e.target.tagName === 'BUTTON') return;
    dragging = true; dx = e.clientX - m.offsetLeft; dy = e.clientY - m.offsetTop; e.preventDefault();
  });
  grip.addEventListener('mousedown', function(e) {
    resizing = true; rx = e.clientX; ry = e.clientY; rw = m.offsetWidth; rh = m.offsetHeight; e.preventDefault();
  });
  document.addEventListener('mousemove', function(e) {
    if (dragging) { m.style.left = (e.clientX - dx) + 'px'; m.style.top = (e.clientY - dy) + 'px'; }
    if (resizing) { m.style.width = Math.max(400, rw + e.clientX - rx) + 'px'; m.style.height = Math.max(300, rh + e.clientY - ry) + 'px'; }
  });
  document.addEventListener('mouseup', function() { dragging = false; resizing = false; });
})();

// Exec Messages Modal
function openExecModal(btn) {
  var cell = btn.parentElement;
  var tableDiv = cell.querySelector("div[style*='max-height']");
  if (!tableDiv) return;
  var m = document.getElementById('execModal');
  var body = document.getElementById('execModalContent');
  body.innerHTML = '<div>' + tableDiv.innerHTML + '</div>';
  // Remove max-height in modal copy so full table is visible
  var inner = body.querySelector("div[style*='max-height']");
  if (inner) { inner.style.maxHeight = 'none'; inner.style.overflow = 'visible'; }
  m.style.display = 'flex';
  m.style.width = '90vw';
  m.style.height = '80vh';
  m.style.left = Math.max(30, (window.innerWidth * 0.05)) + 'px';
  m.style.top = Math.max(30, (window.innerHeight * 0.1)) + 'px';
}
function closeExecModal() {
  document.getElementById('execModal').style.display = 'none';
}

// Drag & resize for exec modal
(function() {
  var m = document.getElementById('execModal');
  if (!m) return;
  var header = m.querySelector('.exec-modal-header');
  var grip = m.querySelector('.exec-modal-resize');
  var dragging = false, resizing = false, dx, dy, rx, ry, rw, rh;
  header.addEventListener('mousedown', function(e) {
    if (e.target.tagName === 'BUTTON') return;
    dragging = true; dx = e.clientX - m.offsetLeft; dy = e.clientY - m.offsetTop; e.preventDefault();
  });
  grip.addEventListener('mousedown', function(e) {
    resizing = true; rx = e.clientX; ry = e.clientY; rw = m.offsetWidth; rh = m.offsetHeight; e.preventDefault();
  });
  document.addEventListener('mousemove', function(e) {
    if (dragging) { m.style.left = (e.clientX - dx) + 'px'; m.style.top = (e.clientY - dy) + 'px'; }
    if (resizing) { m.style.width = Math.max(400, rw + e.clientX - rx) + 'px'; m.style.height = Math.max(300, rh + e.clientY - ry) + 'px'; }
  });
  document.addEventListener('mouseup', function() { dragging = false; resizing = false; });
})();
</script>
</body>
</html>
"@

$outDir = Join-Path $PSScriptRoot 'output'
if (-not (Test-Path $outDir)) { New-Item $outDir -ItemType Directory -Force | Out-Null }
$safeTs = (Get-Date).ToString('yyyyMMdd_HHmmss')
$outFile = Join-Path $outDir "wl_failures_NVL_P_A0_PO_Phase3_WW13p5_$safeTs.html"
[System.IO.File]::WriteAllText($outFile, $html, [System.Text.Encoding]::UTF8)
Write-Host "Report saved: $outFile"
Start-Process $outFile
```

---

## Learnings

1. **(removed — pagination rules removed)**
2. **Live data changes between queries** — Failure records can gain new buckets, new failures can appear, and sighting links can be added at any time. This is why the agent must always reload live data and never rely on cached results.
3. **Generate HTML via PowerShell `.ps1` file** — For complex HTML with styling, tables, and many rows, save the generation script to a `.ps1` file and execute it. Inline terminal commands get truncated with long scripts.
4. **NGA MCP server preserves OData fields, NGAI strips them** — `mcp_nga-server_nga_search` passes `$select`, `$expand`, `$filter`, `$top`, and `$count` faithfully to the OData API. The old `mcp_intel_ngai_plan_and_execute` tool silently stripped fields. Still use `mcp_nga-server_nga_get_testrun` after the initial query to get `Result.ResultCode` (Run State) and cleanup path, since OData expand does not reliably return these.
5. **Use `Result.ResultCode` for Run State** — The `Result.ResultCode` field from `nga_get_testrun` (values: `Failed`, `Passed`, etc.) is the actual run state shown in the NGA UI. The `Source` field from OData (values: `Orchestrator`, `RecoveryFlow`) describes failure origin, not run result. Use `Result.ResultCode` as primary, `Source` as fallback.
6. **NGA failure URL uses `nga-prod.laas.intel.com`, NOT `.icloud.intel.com`** — The correct failure link format is `https://nga-prod.laas.intel.com/#/<project>/failureManagement/failures/<failureId>`. Previous HTML reports incorrectly used `nga-prod.laas.icloud.intel.com/projects/...` which produces broken links.
7. **InProgress TestRuns have no `Result` or `EndTime`** — When `nga_get_testrun` returns `State: "InProgress"`, the response has no `Result` object (no `Result.ResultCode`, no `Result.Description`). Use the `State` field as the ResultCode value.
8. **HTML column order must match the agent spec exactly** — The HTML columns must follow the exact sequence defined in the "Failures Table" section of this document: #, Failure Info, Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary.
9. **Deduplicate REST API enrichment calls aggressively** — Multiple failures often share the same TestRunId. Always collect unique IDs first, then batch calls to avoid redundant API requests.
10. **`SubmittedDateTime` from NGA is UTC** -- The field is ISO 8601 with `Z` suffix (e.g., `2026-03-28T22:10:10.2150243Z`). Convert to the station's local timezone for display using `Get-StationTimeZone` (see Learning #81). Append the timezone abbreviation (MYT/PST/PDT/UTC) after the timestamp.
11. **`ExecutionMessages.csv` timestamps are UTC** — Confirmed by sub-second match: CSV line `22:10:09` matches NGA `SubmittedDateTime` `22:10:10Z` for the same failure. Never assume CSV timestamps are local station time.
12. **Step name matching is more reliable than timestamp matching** — The step function name (e.g., `hpreboot_massdeploy_run`) uniquely identifies the failing step in the CSV with 0s diff. Timestamp fallback can match wrong lines if the CSV contains many entries.
13. **Signatures can be bucket descriptions, not step names** — Signatures like `PCD_PMC:PMC_Hang` or `Windows:BSOD:SYSTEM_SERVICE_EXCEPTION` are bucket/signal descriptions, not CSV step function names. They will never match a `*funcName*Failed*` pattern in the CSV. The real step name (e.g., `hpreboot_massdeploy_run`) must come from examining the CSV or test run context.
14. **Cleanup paths get reused — CSV may be stale** — When a station runs a new test on the same test line, the cleanup path is overwritten. To detect staleness, check if the failure's `SubmittedDateTime` falls within the CSV's overall time range (first line timestamp to last line timestamp, with ±1 hour padding). If outside, the CSV belongs to a different run — display `(CSV from different run)`. Do NOT use the matched line's timestamp for the stale check — long gaps (20+ hours) are normal when a station is stuck in `WaitingForTargetReboot` during hangs.
15. **Timestamp fallback must compare UTC vs UTC** — The CSV timestamps are UTC and `SubmittedDateTime` is UTC. Do NOT convert either to local time before comparison, or you'll get false matches offset by the timezone difference (e.g., 8 hours for MYT).
16. **PDX station ZIPs may hang on network access** — Cleanup paths on `pdxcv14a-cifs.pdx.intel.com` can cause indefinite hangs when reading ZIPs. Use `Start-Job` with a timeout (e.g., 90s via `Wait-Job -Timeout`) for remote ZIP extraction.
17. **Post-processing approach for Execution Messages (CSV fallback only)** — When using CSV fallback mode (no API exec messages), generate the base HTML report first (`gen_wl_report_compact.ps1`), then post-process it with `add_execmsg_column.ps1` to inject the Execution Messages column. For API-sourced messages (primary path), color coding is built into the inline HTML table and `color_execmsg.ps1` post-processing is not needed (see Learning #67).
18. **System.evtx Critical & Error Events extraction** — Extract `System.evtx` from ZIP files in the cleanup path (located at `SUT/retry0/Cleanup/eventlogs/system.evtx` inside the ZIP). Use `Get-WinEvent -Path` with `-FilterXPath "*[System[(Level=1 or Level=2)]]"` for Critical (Level=1) and Error (Level=2) events. Convert timestamps to station local timezone via `Get-StationTimeZone` (see Learning #81) for display consistency with Submitted Date. Append the timezone abbreviation (MYT/PST/PDT/UTC) after each timestamp.
19. **"Unbucketised" means `SightingId eq null`, NOT `BucketId eq null`** — In this workflow, "unbucketised" refers to failures that have not been triaged (no sighting assigned). These failures may still have a `BucketId` and `BucketName`. Use `SightingId eq null` in the OData filter. `BucketId eq null` returns a much larger set of literally unbucketed failures (106 vs 8).
20. **Cleanup ZIP internal structure** — The station ZIP (e.g., `FM05WVAW0548.zip`) contains files under `SUT/retry0/`. Key paths: `SUT/retry0/Cleanup/eventlogs/system.evtx` (System event log, ~26MB), `SUT/retry0/Cleanup/bsod_check.log` (BSOD check process log — NOT the same as `bsod.log`), `SUT/retry0/Cleanup/BSOD/` (OS/system info JSONs), `SUT/retry0/Cleanup/intel-content-bsod-check-sut-post.report.json` (BSOD report). There is also a duplicate at `SUT/retry0/Cleanup/eventlog_report/system.evtx`.
21. **`bsod.log` may or may not exist in cleanup ZIPs** — Early testing found no `bsod.log` in some ZIPs, but later ZIPs do contain them (see Learnings #23, #55). The file `bsod_check.log` is the BSOD check process log (contains config args, debug output, "no events found" messages) and should NOT be parsed as BSOD crash data. If `bsod.log` is absent but `.dmp` files exist, display the dmp file listing (path + size). If neither bsod.log nor .dmp files are found, display `(no bsod.log and no .dmp found in ZIP)` in the BSOD Info column.
22. **Empty cleanup paths for InProgress and old Passed runs** — InProgress runs (e.g., `87d826ee`, `f37adc9d`) have empty cleanup directories with no ZIP files because the run hasn't completed cleanup yet. Old Passed runs (e.g., `7d382e9d`) may also have empty cleanup paths if files were cleaned up. Display `(no ZIP)` for both cases.
23. **BSOD Info extraction from `bsod.log`** — The file may be named `bsod.log` or `BSOD.log` (use case-insensitive match: `-ieq 'bsod.log'`). Located at `SUT/retry0/Cleanup/BSOD/BSOD.log` inside the ZIP. Extract three fields: (1) **Debug Session Time** from the line `Debug session time: Thu Mar 26 08:27:15.855 2026 (UTC + 8:00)` — parse the timestamp, account for the timezone offset shown in parentheses, convert to station local timezone via `Get-StationTimeZone` (see Learning #81). Display with timezone abbreviation suffix. (2) **Bugcheck Code** from the first non-empty line after the `Bugcheck Analysis` asterisk box (e.g., `DPC_WATCHDOG_VIOLATION (133)` or `DRIVER_POWER_STATE_FAILURE (9f)`). (3) **FAILURE_BUCKET_ID** from the line `FAILURE_BUCKET_ID: 0x133_ISR_ACPI!ACPIInterruptDispatchEvents`. If none of these fields are found, show the first 300 chars as a preview. Use `Start-Job` with timeout like evtx extraction.
24. **Deduplicate ZIP access across columns** — Critical Events, BSOD Info, and potentially other columns all read from the same ZIP. Cache results per cleanup path (`$cpCriticals`, `$cpBsod`) to avoid re-opening the same ZIP. Multiple failures sharing the same cleanup path (e.g., `87d826ee` and `f37adc9d` on the same test line) benefit from this deduplication.
25. **Debug session time in `bsod.log` includes timezone offset** — The line `Debug session time: Thu Mar 26 08:27:15.855 2026 (UTC + 8:00)` already shows local time with its offset. To convert to station local timezone: parse the timestamp, subtract the stated offset to get UTC, then convert UTC to the station's timezone via `[System.TimeZoneInfo]::ConvertTimeFromUtc()` using the `Get-StationTimeZone` result (see Learning #81). Do NOT assume the offset is always +8 — each station has its own timezone based on SystemName prefix.
26. **Bugcheck code location in `bsod.log`** — The bugcheck code (e.g., `DPC_WATCHDOG_VIOLATION (133)`) is the first non-blank, non-asterisk line after the `Bugcheck Analysis` box. The box is delimited by lines of `*****`. After the closing asterisk line, skip blank lines, then the next content line is the bugcheck name with its hex code in parentheses.
27. **Selective column regeneration (debug only)** — When debugging a single column's extraction logic, you MAY temporarily use `(skipped)` placeholder for other columns to speed up iteration. However, the final report delivered to the user must ALWAYS have all 8 columns fully populated — never deliver a report with `(skipped)` placeholders.
28. **Status Scope Insight Summary via Axon SVTools report** — The DebugSnapshotId field on NGA failures maps to an Axon record containing the SVTools report (`intel-svtools-report-v1`). **ALWAYS use `mcp_axon-server_get_axon_report_content`** to get the full raw SVTools JSON for each record. The raw JSON provides complete insight data (type, message, location, IP, MCA codes, report path). Priority is derived from `TYPE_PREFIX_PRIORITY` mapping (see Learning 39) — **do NOT use `mcp_genimcp_AxonTool` by default**. Only use genimcp for priority if the user explicitly requests it. Raw JSON requires double-parse: `json.loads(data['result'])`. The `sub_reports` field is a list (not dict); walk recursively to extract all insights. Root-level insights at `data['insights']` must be collected separately.
29. **DebugSnapshotId retrieval** — Get DebugSnapshotId via NGA OData `$select=FailureId,FailureName,DebugSnapshotId`. Some failures (~7%) have null DebugSnapshotId. Store the mapping in `output/hx_failure_to_axon.json` (failureId → debugSnapshotId) and compiled Axon insights in `output/hx_axon_insights.json` (debugSnapshotId → {summary, insights}).
30. **Axon batch query format** — Use message format: `{"exact_question": "Get the SVTools report summary and top insight messages for these N Axon records: id1 | id2 | ...", "history_enhanced_query": "...", "AxonLink": "", "prior_tool_errors": ""}`. Pipe-separate record IDs. Returns table with axon_id, summary, and insight messages. Some records (~5%) may not have SVTools reports and won't appear in results.
31. **PowerShell regex `[^"]*?` fails for href matching** — In PowerShell regex, `[^"]` inside a character class can mishandle the double-quote character, causing the pattern to fail silently. Use `.+?` instead of `[^"]*?` when matching href attribute content in HTML row patterns. The working row pattern is: `'(?s)(<tr>\s*<td class="num">\d+</td>.*?<td><a href=".+?">([a-f0-9]{8})</a>.*?)(</tr>)'`.
32. **StatusScope report URL pattern** — The Axon StatusScope report URL is `https://axonsv.app.intel.com/apps/record-viewer/{full-debugSnapshotId-guid}/intel-svtools-report-v1?tab=report`. This URL is auth-gated — `fetch_webpage` returns "Authentication Required". **Always use `mcp_axon-server_get_axon_report_content`** for raw SVTools JSON data. Do NOT use `mcp_genimcp_AxonTool` by default. The URL supports `#fragment` deep links to specific insights: `#path_insight_N` where path is the dotted sub_report path (e.g., `status_scope.analyzers.mca_insight_3`).
33. **`mcp_genimcp_AxonTool` truncates MCE records — another reason to use axon-server** — Records with Machine Check Exception (MCE) errors can have 75-100+ insight messages. The `mcp_genimcp_AxonTool` LLM response layer truncates after ~10-15 messages even when queried individually. `mcp_axon-server_get_axon_report_content` returns ALL insights without truncation. This is a key reason why axon-server is the mandatory default.
34. **Optimal axon-server batch size** — Call `mcp_axon-server_get_axon_report_content` individually per DebugSnapshotId (one call per record). Each call returns the complete raw SVTools JSON. Save raw JSON files to `output/axon_<suite>/` for reuse by the insight extraction script. Do NOT batch via genimcp.
35. **Print complete verbatim insights — do not abbreviate** — The SVTools Insight column must show ALL insight messages exactly as returned by the Axon tool, one per line. Do NOT manually curate, abbreviate, or summarize insights (e.g., merging "FSM hung in module0/1/2/3" into one line). Use a `<pre>` block with `white-space: pre-wrap` inside a scrollable `<div>` (max-height: 300px) for readability.
36. **SVTools column post-processing with JSON data file** — Store compiled Axon insights in `output/fc_axon_insights.json` (keyed by failureId 8-char prefix → {axon, summary, insights[]}). The `add_axon_column.ps1` script loads this JSON and injects verbatim insights into the HTML. This separates data collection (Axon queries) from HTML generation, allowing re-runs without re-querying Axon.
37. **Strip existing axon cells before re-injection** — When re-running `add_axon_column.ps1` on a report that already has SVTools cells, first strip existing `<td class="axon">` cells with regex `\s*<td class="axon">.*?</td>` before injecting fresh ones. Also check if the SVTools header already exists to avoid duplicate headers.
38. **NGA failure `StringExternalInfo` contains Axon links** — The `mcp_nga-server_nga_get_failure` response includes a `StringExternalInfo` field with semicolon-separated links: "Axon Status Scope Report" (StatusScope viewer), "Axon Summary Report" (summary page), and "AxonSV Record Viewer" (raw record). These provide the full DebugSnapshotId GUID needed for StatusScope URLs.
39. **StatusScope insights have priority levels (1, 2, 3, 6, 10) — use TYPE_PREFIX_PRIORITY mapping by default** — Each insight message in the SVTools report has a numeric priority: P1 = critical (MCE, stuck transactions, ports stuck, PMC hung), P2 = warnings (BSOD, DMI not active, TargetEvent, C2U credits), P3 = connection issues (can't read SUSDR), P6 = system state (power state, CPU uptime, NCU/CCF alive), P10 = informational (FSM hung, Port 80, memory warnings). **Priority is derived from the insight's `type` field using `TYPE_PREFIX_PRIORITY` mapping** (ordered longest prefix first): `HW.STUCK_TRANSACTION→1, HW.MCE→1, HW.HANG→1, HW.PORT_STUCK→1, HW.IFA→1, HW.UNEXPECTED_RESET→2, HW.LINK→2, SW.POWER→6, PLATFORM→10, SW→10, HW→10`. Default for unmatched types: 10. This mapping is applied in `extract_all_axon_insights.py` or `build_insight_table_*.py` during raw JSON processing. **Do NOT use `mcp_genimcp_AxonTool` for priority enrichment by default** — it truncates results, requires extra API calls, and the type-prefix mapping produces equivalent results. Only use genimcp if the user explicitly requests Snowflake-based priority.
40. **SVTools insights JSON structure with priority** — `output/fc_axon_insights.json` uses structure: `failureId → {axon, summary, insights: [{priority: N, message: "..."}]}` sorted by priority ascending (1 first). The `build_axon_insights_with_priority.ps1` script compiles all Axon query results into this JSON and injects priority-sorted, color-coded insights into the HTML report.
41. **Per-priority color coding for SVTools insights** — Each priority level gets a distinct color in the HTML: P1 = purple `#7b2d8e` (bold), P2 = red `#c0392b` (bold), P3 = orange `#e67e22`, P6 = blue `#2980b9`, P10 = gray `#888888`. Messages are wrapped in `<span>` tags with inline `style` attributes. The `[P<N>]` prefix is prepended to each message for visual grouping.
42. **PowerShell 5.1 `Join-Path` only accepts 2 arguments** — Unlike PowerShell 7+, PS 5.1's `Join-Path` does not accept 3+ positional path segments. Use nested calls: `Join-Path (Join-Path $PSScriptRoot 'output') 'fc_axon_insights.json'` instead of `Join-Path $PSScriptRoot 'output' 'fc_axon_insights.json'`.
43. **Multi-line `<td>` strip regex needs `(?s)` flag** — When stripping existing `<td class="axon">` cells that contain `<pre>` blocks with newlines, the PowerShell `-replace` operator's `.*?` does NOT match across newlines by default. Use `[regex]::Replace($html, '(?s)\s*<td class="axon">.*?</td>', '')` to enable single-line mode where `.` matches `\n`.
44. **Execution Messages color coding by keyword** — Post-process the Execution Messages column (`<td class="exec"><pre>...</pre></td>`) to color each line based on NGA-style status keywords. Use `color_execmsg.ps1` to wrap lines in `<span style="display:block;...">`. Color scheme: **Failed** = red `#c0392b` on pink `#fde8e8`, **Aborted** = orange `#d35400` on amber `#fff3cd`, **Passed/Completed** = green `#27ae60` on light green `#e8f5e9`, **Running** = blue `#2471a3` on light blue `#e3f2fd`, **Scheduled/Waiting** = gray `#7f8c8d` (no background). The `>>>` matched line gets additional `font-weight:700` and yellow background `#fff9c4` (if no other background applies). Skip placeholder cells (`(skipped`, `(no `, `(empty`, `(CSV from`).
45. **Critical & Error Events — snippet only with rich formatting** — The "System.evtx Critical/Errors" column extracts Level=1 (Critical) and Level=2 (Error) events via XPath `*[System[(Level=1 or Level=2)]]`. Events are cached per cleanup path and filtered to a ±1h window around `SubmittedDateTime` (UTC). **Display is snippet-only** — no summary bar, no EventID breakdown table, no pattern analysis notes. Each event is a rich-formatted row: level badge pill (CRIT=red `#c62828`, ERROR=orange `#e65100`), station local timestamp with TZ abbreviation in monospace, source pill (stripped `Microsoft-Windows-` prefix), blue EID label, and human-readable description (from `EVTX_DESCRIPTIONS` / `get_evtx_description()`). Events sorted **newest first**. A dashed red separator marks the failure point. Closest event gets yellow `#fff9c4` background + red `►` marker. For >30 events, show a 30-event centered window with a "View All Events" expand button. The column outputs raw HTML — not wrapped in `HtmlEnc`.
46. **Statuscope Summary column header and link placement** — The SVTools column is renamed to "Statuscope Summary". The summary text is displayed as bold colored text (not a hyperlink). The "Link to Statuscope" hyperlink is placed on a separate line below the `<pre>` insights block. The `build_axon_insights_with_priority.ps1` script also injects the `<th>` header (matching "Statuscope" or "SVTools" for idempotent strip) before `</tr></thead>`.
47. **Newest-first ordering for Execution Messages and Critical/Error Events** — Both columns display entries sorted from newest to oldest (top to bottom). Execution Messages: the ±5 line extraction loop iterates from `$end` down to `$start` (`for ($i = $end; $i -ge $start; $i--)`). Critical/Error Events: `Sort-Object { [datetime]::Parse($_.utc) } -Descending` in `Format-CritEvents`.
48. **Wrap `Sort-Object` result in `@()` to prevent single-element unwrap** — When `$filtered` contains exactly 1 hashtable, `Sort-Object` returns a bare hashtable instead of a 1-element array. Then `$sorted.Count` returns the number of *keys* (6) instead of 1, and `$sorted[$i]` indexes into nothing useful — producing 6 empty `[] [] EventID ():` rows. Fix: `$sorted = @($filtered | Sort-Object ...)`. This is a classic PowerShell 5.1 pipeline gotcha affecting any single-object-to-Sort-Object pattern.
49. **Stale CSV check must use CSV time range, not matched line timestamp** — The old stale check compared the matched CSV line's timestamp to `SubmittedDateTime` with a 1-hour threshold. This produces false positives when a test run has long gaps in the CSV (e.g., 27+ hours stuck in `WaitingForTargetReboot` during a hang). The failure's `SubmittedDateTime` falls within the gap, so the nearest CSV line is hours away, incorrectly triggering "CSV from different run". Fix: parse the CSV's first and last timestamps to get the overall time range, then check if `SubmittedDateTime` falls within `[first - 1h, last + 1h]`. This correctly identifies the CSV as belonging to the same run.
50. **(removed — pagination rules removed)**
51. **NGA TestRunMessage API for full execution messages** — The NGA Results service exposes `POST /Results/{project}/api/TestRun/TestRunMessage` which accepts `{"Ids":["<testRunId>"]}` and returns ALL execution messages (296+ per test run). This includes Orchestrator step messages (same as CSV), User messages (recovery flow, iteration counts, stage runner), StationAutomationService messages, and ResultService messages. The `mcp_nga-server_nga_get_execution_messages` MCP tool uses the WRONG endpoint path (`/Results/{project}/api/ExecutionMessage/{id}` → 404). Always use the Python helper `get_testrun_messages.py` instead. Swagger spec found at `https://nga-prod.laas.icloud.intel.com/Results/swagger/v1/swagger.json`.
52. **`get_testrun_messages.py` Python helper for authenticated API calls** — NGA Results API requires MSAL bearer token authentication (app ID `5010f2b6-5feb-4de3-89a2-dba1172b07f8`, scope `6af0841e-c789-4b7b-a059-1cec575fbddb/.default`). PowerShell `Invoke-WebRequest -UseDefaultCredentials` does NOT work (returns "Access token is missing"). The Python helper handles auth, calls the POST endpoint, strips HTML tags from messages, and outputs sorted JSON to stdout. Called from PowerShell via `& python "$PSScriptRoot\get_testrun_messages.py" 'nvl_fv_or' $testRunId 2>$null`.
53. **TestRunMessage API message sources and types** — Messages have 4 sources: `Orchestrator` (~263 msgs, step Running/Passed/Failed), `User` (~30 msgs, recovery flow `--- STARTING RECOVERY FLOW ---`/`Hang Flow`/`--- RECOVERY FLOW END ---`, iteration counts `Failure during iteration N`, stage runner output, BIOS knobs), `ResultService` (2 msgs, test started/completed), `StationAutomationService` (1 msg, failing test notification). User messages contain HTML `<span>` tags with inline styles (colors, bold) that must be stripped for display.
54. **ExecutionMessages.csv only has step-level messages** — The CSV in the cleanup path only contains Orchestrator-source step execution messages (Running/Passed/Failed). It does NOT include recovery flow events, status updates, iteration counts, or other NGA platform events that are visible on the NGA failure web page. The API is the only way to get the complete message set.
55. **Multi-BSOD support in cleanup ZIPs** — A single cleanup ZIP may contain multiple `bsod.log` files at different paths (e.g., `SUT/retry0/Cleanup/BSOD/BSOD.log` and `SUT/retry1/Cleanup/BSOD/BSOD.log`). The `Get-BsodInfo` function scans ALL zip entries matching `bsod.log` (case-insensitive), extracts each one, and identifies the BSOD closest to the failure's `SubmittedDateTime` by comparing Debug Session Time. The closest BSOD is highlighted with a yellow `#fff9c4` background and `>>>` marker.
56. **Exec message timestamp display format is `M/d/yy H:mm:ss <TZ>`** -- All timestamps in the Execution Messages column use `M/d/yy H:mm:ss` format (24-hour, no AM/PM) followed by the station's timezone abbreviation (MYT/PST/PDT/UTC). Both API-sourced and CSV-sourced messages use this format after UTC-to-local conversion via `Get-StationTimeZone`.
57. **Failure data block must include `testRunId` for API exec messages** — Each failure entry in `$failures` array in `gen_wl_report_compact.ps1` must include a `testRunId` field (the full GUID from `TestRunComposite.TestRunId`). This is passed to `Get-ExecMessages` which uses it to call the TestRunMessage API. Without `testRunId`, the function falls back to CSV-only mode.
58. **NGA swagger specs available at two services** — Only `Results` and `TestRun` services have swagger specs at `https://nga-prod.laas.icloud.intel.com/{service}/swagger/v1/swagger.json`. Other services (TestExecution, Execution, FailureManagement, Gateway) return 404 for swagger. The TestRunMessage endpoint is in the Results service, not the TestRun service.
59. **BSOD Info column shows full bsod.log content** — Instead of extracting just 3 fields (Debug Session Time, Bugcheck Code, FAILURE_BUCKET_ID), `Get-BsodInfo` now displays the entire bsod.log content inline in a scrollable `<pre>` container (max-height: 200px). The full log content is base64-encoded during ZIP extraction (inside the background job) to safely pass through the pipe-delimited temp file format, then decoded in the main script.
60. **Draggable modal for long BSOD logs** — For logs exceeding 30 lines, a "View Full Log (N lines)" button is rendered below the inline preview. Clicking it opens a shared draggable/resizable modal (`#bsodLogModal`). The modal content is populated dynamically via JavaScript by extracting `textContent` from the sibling `<pre>` element. Modal CSS class `.bsod-modal` provides fixed positioning, flex layout, drag handle in header, and resize grip in bottom-right corner. Only one shared modal exists in the DOM — it gets repopulated each time a different "View Full Log" button is clicked.
61. **PowerShell `[System.Collections.Generic.List[string]]::AddRange()` requires `[string[]]` cast** — In PS 5.1, array slicing returns `object[]`, not `string[]`. `AddRange` on `List[string]` fails with "Cannot convert 'System.Object[]' to 'IEnumerable[string]'". Always cast: `$result.AddRange([string[]]$arraySlice)`.
62. **Splice scripts must be tested carefully — file truncation risk** — If a splice script that reads and rewrites `gen_wl_report_compact.ps1` fails mid-execution (e.g., AddRange type error), it may write only partial content, truncating the file. Since the file is untracked by git, there's no easy recovery. Always verify the splice output line count matches expectations before proceeding. Keep `gen_wl_report_compact_old.ps1` as a reconstruction baseline.
63. **Section detection regex must exclude HTML content** — When scanning `gen_wl_report_compact.ps1` for section boundaries, patterns like `'System\.evtx Critical'` match both the PowerShell section comment AND the HTML `<th>` table header. Use `'^\s*#.*System\.evtx'` (anchored to comment lines) to match only the function section header, not the HTML template.
64. **Use `List[object]` instead of `@() +=` for large array building in background jobs** — PowerShell's `$arr += @{...}` copies the entire array on every append (O(n²)). With 5000+ events (e.g., 5964 Critical+Error events from a 103MB `system.evtx`), this creates ~17.8M array copies, exceeding the 90s `Start-Job` timeout. Fix: use `$events = [System.Collections.Generic.List[object]]::new()` and `$events.Add(@{...})` for O(1) amortized per item. This reduces extraction from timeout to ~3 seconds. **Apply this pattern in ALL `Start-Job` scriptblocks that build arrays from potentially large datasets** (evtx events, CSV rows, ZIP entries). The 90s/120s `Wait-Job` timeouts remain as safety nets against network hangs but should never be hit by the extraction logic itself.
65. **`>>>` marker regex must match both raw and HTML-encoded forms** — In `color_execmsg.ps1`, the `>>>` marker line may appear as raw `>>>` (inside `<pre>` blocks) or HTML-encoded `&gt;&gt;&gt;`. The detection regex must handle both: `'^>>>|^&gt;&gt;&gt;'`. Previously only `'^&gt;&gt;&gt; '` was checked, causing raw `>>>` lines to not get highlighted.
66. **`[datetime]::Parse()` on ISO 8601 `Z` strings returns Local kind** — `[datetime]::Parse('2026-03-29T20:16:18Z')` converts the UTC timestamp to local time (e.g., `03/30 04:16:18 MYT`) with `Kind=Local`. When comparing against a DateTime obtained via `.ToUniversalTime()` (Kind=Utc), PowerShell ignores Kind and compares raw ticks — so `03/30 04:16 local` vs `03/29 21:42 utc` gives wrong results. Fix: always call `.ToUniversalTime()` on both sides of DateTime comparisons in `Format-CritEvents`. This bug caused `(no events in +/-1h window)` for failures where events existed.
67. **Execution Messages uses inline HTML table with -1h/+10 msgs window** — The `Get-ExecMessages` function in `gen_wl_report_compact.ps1` renders a 7-column HTML table (#, Timestamp, Source, Stage, System, Title, Message). Messages are filtered using a two-pass approach: first find the closest message to `SubmittedDateTime`, then collect all messages from -1h before `SubmittedDateTime` through +10 messages after the closest. The closest row gets `id='exec_closest_<failureName>'` and an inline `<script>` auto-scrolls the container to it on load. The cell uses `<td class="exec">` (no `<pre>` wrapper). An "Expand" button opens a shared `#execModal` (draggable/resizable, same pattern as insight/BSOD modals). CSS classes: `.exec-modal`, `.exec-modal-header`, `.exec-modal-body`, `.exec-modal-resize`. JS functions: `openExecModal(btn)`, `closeExecModal()`. CSV fallback still uses `<pre>` text with ±5 lines. The `color_execmsg.ps1` post-processor is no longer needed for API-sourced messages since color coding is built into the table.
68. **Evtx `SpecifyKind` causes double timezone shift — use `.ToUniversalTime()` instead** — In `Format-CritEvents`, `[System.DateTime]::SpecifyKind([datetime]::Parse($evt.utc), [System.DateTimeKind]::Utc)` is WRONG when `$evt.utc` is an ISO 8601 string with `Z` suffix. `[datetime]::Parse('...Z')` converts to local time (e.g., +8h MYT) with `Kind=Local`. `SpecifyKind(..., Utc)` merely relabels the value as UTC without adjusting — so `14:19 MYT` becomes `14:19 UTC`. Then `ConvertTimeFromUtc` adds another +8h → `22:19 MYT` (8 hours too late). Fix: replace `SpecifyKind(...)` with `[datetime]::Parse($evt.utc).ToUniversalTime()`, which properly converts back to UTC regardless of the parsed Kind. This applies ONLY to `Format-CritEvents` — the exec messages `SpecifyKind` (line ~257) works correctly because `$e.utc` is already `Kind=Utc`, and the BSOD `SpecifyKind` (line ~656) works correctly because `$e.utcDebug` is computed with `Kind=Unspecified`.
69. **(removed — duplicate of Core Rule 7: Exclude Passed run state by default)**
70. **(removed — duplicate of Post-Query Deduplication by TestRunId section)**
71. **`openExecModal` JS selector must match the actual DOM structure** — The `openExecModal(btn)` function in the HTML report must use `btn.parentElement` to get the `<td>` cell, then `cell.querySelector("div[style*='max-height']")` to find the scrollable container. A previous version used `btn.closest('td')` + `cell.querySelector('div > div[style*="max-height"]')` which required the scrollable `<div>` to be nested inside a wrapper `<div>`. But `Get-ExecMessages` renders the scrollable div directly inside `<td class="exec">` (no wrapper div), so the `div > div` selector returned null and the modal opened empty. The correct function also removes `max-height` in the modal copy for full visibility: `inner.style.maxHeight = 'none'; inner.style.overflow = 'visible'`. **Always copy the latest `openExecModal` from `gen_wl_report_compact.ps1` when generating new report scripts.**
72. **Always embed new required files in the agent spec** — Whenever a new runtime script or required file is created during a workflow run, it must be embedded as a fenced code block in the "Embedded Runtime Scripts" section of this agent spec, added to the "Required Files" table with `Embedded = Yes`, and committed+pushed. The agent spec must remain fully self-contained — no external file dependency should exist without a corresponding embedded copy. This ensures the agent can self-extract all needed files from the spec alone.
73. **Cleanup paths vary per testrun — never construct or assume them** — Each testrun has its own unique `CleanupPath` returned by `mcp_nga-server_nga_get_testrun`. The suite folder component (e.g., `NVL_MBL_Qual`, `NVL_HX_SST`, `NVL_HX_Concurrency`) and the station/test subfolder are determined by NGA at runtime and cannot be predicted from the test cycle name or suite name. Never hardcode or pattern-construct cleanup paths (e.g., assuming `NVL_HX_EXT_B0_ES2` from the cycle name `nvl-hx-ext-b0`) — this produces paths to non-existent folders and causes all evtx/BSOD columns to be empty. Always use the actual `CleanupPath` value from the `nga_get_testrun` API response for each testrun.
74. **Non-hang Command Failure column MUST include Expand Full Log button** — When generating the Non-hang Command Failure column (Step 5 item 4), always include the "Expand Full Log" button with its hidden `<div>` sibling containing the full UDF step log content, plus the modal overlay HTML, modal CSS classes (`.log-modal-overlay`, `.log-modal`, `.log-modal-header`, `.log-modal-body`, `.log-modal-resize`), and `openLogModal`/`closeLogModal` JavaScript. This was missed in the first report for failure `8250d8bb` — the UDF step log data was retrieved and analyzed but not piped into the HTML output. The assembly step must explicitly: (1) read the full log from `output/devcon_fulllog_<failureName>.txt`, (2) generate syntax-highlighted HTML, (3) render the Expand button + hidden div in the cell, (4) add the shared modal + CSS + JS to the page. Treat this as a mandatory checklist item — do NOT rely on remembering to add it ad-hoc.
75. **Devcon drive disappearance root cause pattern (Galaxy SX cycling)** — When a Galaxy SX/S0ix cycling test fails with `CommandReturnCode: 2` and the GEC classifier decision is SKIP, check for Devcon drive check failures in the cleanup ZIP. Key files to extract from the ZIP's `SUT/retry0/PostTest/Test/DevconCaptures/` folder: `DC_CompareDriveList.log` (per-iteration pass/fail listing), `DC_OriginalDriveList.log` (baseline drive list), `DC_OriginalCapture.log` (baseline devcon output with device IDs), and all `DC_CurrentDriveList_*_FAIL.log` files (snapshots at failure iterations). Also extract a sample `devcon_capture.log` from a FAIL cycle (e.g., `SUT/retry0/PostTest/Test/SX_Traffic_<N>/devcon_capture.log`). The root cause signature is: a USB-connected drive (e.g., `J: USB_Hub_Realtek_OneTouch` → `SCSI\DISK&VEN_SEAGATE&PROD_ONE_TOUCH_W/PW`) disappears at a specific iteration and remains absent through the final iteration. The Galaxy content report (`intel-content-galaxy-GalaxyLog_*.report.json`) confirms via `insights` array with result `FAIL` for the devcon workload showing fail percentage exceeding tolerance (e.g., 19.42% > 1%). In the Non-hang Command Failure column, display: (1) Galaxy insights snippet, (2) Galaxy test summary with pass/fail per workload, (3) Devcon capture log error snippet with "Expand Full Log" button, (4) Missing device identification card (`💾 Drive X: → <product> (<device_id>) via <hub_type>`), (5) DriveList comparison log tail with "Expand Full DriveList" button showing all iterations.
76. **Exec Messages Expand modal must contain ALL messages** — The inline Execution Messages table shows a ±1h window around the failure time for compact display, but the "Expand" modal must include ALL messages (not just the filtered window). The first version incorrectly reused the same filtered dataset for the modal, which meant the modal did not cover the full failure timeline. Fix: build the modal table from the complete `exec_msgs` array, while the inline table uses the filtered subset. Both the inline and modal tables must auto-scroll to the row closest to the failure's `SubmittedDateTime`.
77. **Evtx column CSS must prevent overlap** — System.evtx column content (especially the EventID breakdown table and long provider names) can overflow and overlap adjacent columns. Fix: ensure ALL `<td>` elements use `white-space: normal; word-break: break-word; overflow-wrap: break-word; overflow: hidden;` in the CSS. Use `table-layout: fixed` with explicit `<col>` widths on the main table. The evtx breakdown table inside the cell must also have `word-break: break-word` on its cells. Without these, long provider names like `Microsoft-Windows-Kernel-Power` push the column width beyond its allocation.
78. **Evtx EventID breakdown table must show human-readable descriptions, not raw message samples** — Raw evtx event messages contain unintelligible data: XML `<string>` fragments, base64-encoded service names (e.g., `bAB1AGEAZgB2AAAA`), raw numeric error codes (e.g., `-2147020471`), and parameter placeholders (`%%1275`). The "Sample" column from the first version was unusable. Replace it with a "Description" column using a `EVTX_DESCRIPTIONS` dictionary keyed by `(event_id, provider)` tuples, mapping to plain-English explanations: EventID 41 Kernel-Power → "Unexpected shutdown or restart (bugcheck/power loss)", EventID 6008 EventLog → "Previous system shutdown was unexpected", EventID 16 Kernel-Boot → "Fatal error processing restoration data after resume/reboot", EventID 1796 TPM-WMI → "TPM firmware update validation failed (SBAT/DBX check)", EventID 7000 SCM → "Service failed to start (luafv)", EventID 7043 SCM → "Service did not respond to start in time". Include generic fallbacks by provider substring (TPM → "TPM communication or firmware error", SCM → "Windows service lifecycle event"). This mapping should be extended as new EventIDs are encountered in future analyses.
79. **Evtx column shows snippet only — no summary/breakdown table** — The System.evtx column displays ONLY the rich-formatted event snippet (see Learning #80). The summary bar (total counts), EventID breakdown table, and pattern analysis notes (Kernel-Power, SCM, TPM callouts) have been removed to reduce clutter. The snippet itself already shows all events with level badges, timestamps, sources, EventIDs, and descriptions, providing sufficient context at a glance. The `EVTX_DESCRIPTIONS` dictionary and `get_evtx_description()` function are still used by the snippet for human-readable descriptions.
80. **Evtx snippet must use rich formatting, newest-to-oldest order** — The event log snippet in the System.evtx column must use structured visual elements and display events **newest first** (descending by time). Each event row displays fields in this order: (1) **Level badge** as a colored pill — Critical: white-on-red `#c62828` bold "CRIT", Error: white-on-orange `#e65100` "ERROR", (2) **Date/Time** in gray monospace (`font-family:Consolas,monospace; color:#666`) converted to station local timezone (see Learning #81), (3) **Source** (provider) as a compact pill (`background:#e8eaf6; color:#37474f`) with `Microsoft-Windows-` prefix stripped, (4) **EventID** in bold blue `#1565c0` prefixed with "EID", (5) **General description** (from `EVTX_DESCRIPTIONS` / `get_evtx_description()`) on a second line instead of raw message text. A **dashed red separator line** (`border-top:2px dashed #c62828`) with "▲ FAILURE POINT (timestamp) ▲" is inserted between post-failure and pre-failure events (since newest is on top, post-failure events appear first, then the separator, then pre-failure events below). The closest event to the failure gets a yellow background `#fff9c4` and a red arrow marker `►`. The snippet container uses `max-height:250px; overflow-y:auto; background:#fafafa` for a subtle inset look.
81. **Station timezone varies by location — do not hardcode MYT for all failures** — Stations run in different geographic locations with different local timezones. Determine the station's timezone from the **SystemName** prefix in the failure/testrun data: `pg*` = Penang (MYT, UTC+8, Windows TZ ID `Singapore Standard Time`), `fm*` = Folsom (PST/PDT, UTC-8/-7, Windows TZ ID `Pacific Standard Time`), `jf*` = Oregon/Jones Farm (PST/PDT, UTC-8/-7, Windows TZ ID `Pacific Standard Time`). Use the helper function `Get-StationTimeZone($systemName)` which returns a `[System.TimeZoneInfo]` object and 3-letter abbreviation based on the prefix. Each failure row must use its own station's timezone for ALL timestamp display (exec messages, evtx events, BSOD debug time, submitted date). The `$failures` array must include a `systemName` field populated from the testrun's `SystemName`. Append the timezone abbreviation (e.g., `MYT`, `PST`, `PDT`) after timestamps instead of hardcoding `MYT`. If the prefix is unrecognized, default to UTC with `UTC` label and log a warning.
82. **Per-workload failure log embedding for Galaxy concurrency stress** — When a Galaxy concurrency sustained stress test (e.g., `gmd_system_concurrency_sustained_stress_active_pm_cs_s4`) fails with multiple workloads (FFMPEG, FIO, ChecksumFT, etc.), fetch the **last failed iteration's log** for each failing workload from the cleanup ZIP. Logs are at `SUT/retry0/PostTest/Test/<workload>_<timestamp>.txt` (e.g., `fio_20260408_044407956.txt`, `webcam_ffmpeg_20260408_044407992.txt`, `checksumft_20260407_203845540.txt`). Use `mcp_nga-server_nga_read_cleanup_log` with byte offset to read the tail (last ~30KB) of large logs. Save locally to `output/<workload>_last_fail.txt`. Analyse each for root cause: FFMPEG typically shows `Could not enumerate video devices (or none found)` (webcam lost after S4/S0ix), FIO shows return code 0x05 (I/O verification error), ChecksumFT shows checksum mismatch (data integrity). Embed all logs in the Non-hang Command Failure column using HTML `<details><summary>Expand Full Log (iter N.N.N)</summary><pre>...</pre></details>` elements — one per workload. Each workload section shows: root cause badge, error snippet, failed iteration list, and the expandable full log. Read log files at PS1 runtime via `Get-Content -Raw` and HTML-encode with `[System.Net.WebUtility]::HtmlEncode()` before embedding in the `<pre>` block.
83. **Evtx disk error identification via DevconCaptures** — When System.evtx shows disk controller errors referencing `\Device\HarddiskN\DRN` (provider: `disk`), identify the physical device by reading DevconCaptures from the cleanup ZIP. Key files: `SUT/retry0/PreTest/DevconCaptures/OriginalDriveList.log` (maps drive letters to volume labels, e.g., `H: USB_Rage (Removable)`) and `SUT/retry0/PreTest/DevconCaptures/original_device_report.json` (full device tree with SCSI disk entries containing vendor/product info). The Harddisk index is 0-based from Windows disk enumeration order — Harddisk6 is the 7th physical disk. Display a disk identification card prepended to the evtx column content (before the event snippet) showing: (1) error events timeline grouped by device (`\Device\Harddisk6\DR6` at time1, `\DR12` at time2, `\DR19` burst at time3), (2) drive letter map table with all drives and their physical device info (vendor, model, interface type), (3) correlation note linking disk controller errors to specific workload failures (e.g., "Harddisk6 controller errors correlate with FIO I/O failures (0x05) and USB re-enum issues after S4 cycling"). The card uses orange border styling (`border:1px solid #e65100`) for visibility.
85. **AI-Trained Summary must name the root cause device/drive** — When the failure analysis identifies a specific physical device or drive as the root cause (from evtx disk error identification, DevconCaptures drive mapping, devcon VID/PID lookup, or FIO drive letter mapping), the AI-Trained Summary MUST include the device/drive name in both: (1) the **one-line summary** sentence (e.g., "FIO I/O errors caused by disk controller failures on Harddisk6 (PNY Pro Elite V2 USB)"), and (2) a **Device/Drive root cause callout** card (item 3b) with the full identification: device name, drive letter, hardware ID, and the specific failure evidence (e.g., "80+ controller errors after S4 resume"). This ensures the reader can immediately see which hardware is at fault without scrolling to the evtx or Non-hang Command Failure columns. The callout uses blue styling (`background:#e3f2fd; border-left:3px solid #1565c0`) to stand out from the gray evidence bullets.
84. **Galaxy report JSON parsing for ErrorsTable** — The Galaxy report JSON (`intel-content-galaxy-GalaxyLog_*.report.json`) in the cleanup ZIP contains structured workload failure data. Key fields: `insights[].result` (PASS/FAIL per workload), `insights[].data.ErrorsTable` (array of per-iteration error entries with columns: Iteration, Workload, Error Level, Return Code, Error Log filename), `insights[].data.SummaryTable` (overall pass/fail counts per workload). Parse this JSON to get exact failure counts and iteration numbers for each workload, then cross-reference with the per-workload logs in `SUT/retry0/PostTest/Test/` to identify which log corresponds to which failed iteration. The ErrorsTable `Error Log` field contains the exact log filename (e.g., `fio_20260408_044407956.txt`) used to locate the correct file in the ZIP.
