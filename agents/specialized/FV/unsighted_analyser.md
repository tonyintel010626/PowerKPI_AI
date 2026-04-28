# unsighted_analyser Agent
# Author: wkong3 
# Purpose: Analyse failures without SightingID by parsing multiple logs into table format and output in html (external browser). Skip failures that have been manually changed to Passed. 
# Usage: Specify failure name or test cycle and/or test suite.
# Development checklist:
#   - Basic failure info (Done)
#   - Execution messages (Done)
#   - System.evtx critical/errors (Done)
#   - BSOD info (Done)
#   - Statuscope/SVTools insights (Done)
#   - Galaxy logging for matching messages and events to failures (In Progress)
#   - Learning-based analysis of failure and recommendation (Not Started)
#   - HSD matching and filing (Not started)


**Purpose**: Query NGA test failures by suite and/or test cycle using the NGA MCP server, with optional sighting filters, and generate a fully enriched HTML report (6 columns) opened in an external browser. All enrichment columns (Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary) are **always populated by default** — never skipped or left as placeholders.

---

## Default Output Behavior

**The 6-column HTML report is the ONLY default output format.** Whenever the user provides ANY of the following inputs, the agent MUST find the matching failures, enrich them, and generate the full 6-column HTML report opened in an external browser:

- **Test cycle** — e.g., `package.nvl-h-ext-a0.val_es1.IVE.NVL_H_A0_ES1_WW12.3` → Query failures with `SightingId eq null`, enrich, generate HTML report.
- **Suite** — e.g., `NVL_H_SST` → Combined with the session's test cycle, query failures with `SightingId eq null`, enrich, generate HTML report.
- **Suite + Test cycle** — Query failures with `SightingId eq null`, enrich, generate HTML report.

**Filtering rules summary:**
| Input type | SightingId filter | Run State filter |
|---|---|---|
| Test cycle and/or Suite | `SightingId eq null` | Exclude `Passed` (post-enrichment) |

**Default: Exclude Passed run state** — After enrichment (step 3), discard any failure whose `Result.ResultCode` is `Passed`. These are false-positive failure records where the test run ultimately passed. Only include Passed failures if the user explicitly asks (e.g., "include passed", "show all run states"). The HTML report summary must note: `"Note: Failures with Run State = Passed are excluded."`.

**Never output failure data as plain text, markdown tables, or chat summaries.** Always produce the full HTML report with all 6 columns populated and open it in the browser. The only exception is if the user explicitly asks for a text/table summary (e.g., "just list the failure IDs", "show me a quick summary").

---

## Core Rules

1. **Never use local scripts, cached JSON, or pre-existing output files** — Every query must go live to NGA.
2. **Always reload live data** — Do not reference existing files in `output/`, prior conversation results, or any cached state. Query NGA, HSDES, and PVIM fresh each time.
3. **Generate HTML output** — Every result must produce an HTML report saved to `output/` and auto-opened in the external browser via PowerShell `Start-Process`.
6. **Never reuse existing generated `.ps1` scripts** — Always generate a fresh `.ps1` report script for each query, even if a script for the same cycle/suite already exists (e.g., `gen_wl_report_s28_ww09.ps1`). Previous scripts contain stale failure data, hardcoded enrichment results, and may not reflect the latest code. Build each script from scratch using the current `gen_wl_report_compact.ps1` as the template.
5. **Use `mcp_nga-server_nga_search` for failure queries, NOT `mcp_intel_ngai_plan_and_execute`** — The NGA MCP server (`mcp_nga-server_nga_search`) supports native OData `$filter`, `$select`, `$expand`, `$top`, `$count`, and `$skip` parameters. It returns exact results without field stripping, supports `$count=true` for totals in a single call, and respects `$top` values above 20. Always use it as the primary query tool. Only fall back to `mcp_intel_ngai_plan_and_execute` if the NGA MCP server is unavailable or the query requires natural language interpretation.
4. **Default output is always the 6-column HTML report** — Any user input containing test cycles or suite names triggers the full workflow: query → enrich → filter → Axon insights → HTML report → post-process → open in browser.
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
4. **Failures Table** with these 6 columns only (in order):
   - `#` — Row number (auto-incremented, 1-based)
   - `Failure Info` — Consolidated column containing all failure metadata as labeled fields inside a single `<div>` block:
     - **Run State**: `Result.ResultCode` from `nga_get_testrun` (e.g., Failed, Passed). Fallback: `Source` field from OData (e.g., Orchestrator, RecoveryFlow).
     - **Failure Name**: linked to NGA failure page: `https://nga-prod.laas.intel.com/#/<project>/failureManagement/failures/<failureId>` (note: `.intel.com`, NOT `.icloud.intel.com`)
     - **Other Failures**: If this TestRunId had multiple failure records that were deduplicated, list the other failure names/IDs as linked text (e.g., `+2 more: a1b2c3d4, e5f6g7h8`). Omit this line if the TestRunId had only one failure record.
     - **Bucket**: from Bucket expand
     - **Signatures**: joined signatures from Signatures expand
     - **Submitted**: `SubmittedDateTime` from NGA, converted from UTC to local MYT (UTC+8). Display format: `M/d/yy H:mm MYT`.
   - `Execution Messages` — Inline scrollable HTML table showing all messages from **-1 hour before the failure OR minimum 10 messages before the failure** (whichever gives more) through **+10 messages after** the closest (failure) message, ordered newest to oldest. The table has 7 columns: #, Timestamp (MYT), Source (color-coded badge: Orch=purple, User=blue, Result=green, Station=orange), Stage, System, Title, Message. The closest message to `SubmittedDateTime` is highlighted with yellow background (`#fff9c4`), bold weight, and a red ► marker. Failed/Aborted rows get pink `#fde8e8` background; Passed/Completed rows get green `#e8f5e9`. The table is wrapped in a scrollable `<div>` (max-height 320px) that **auto-scrolls to the closest (failure) row on page load** so the failure context is immediately visible. An "Expand (N msgs)" button opens a **draggable/resizable full-screen modal** for detailed viewing. **Primary source**: NGA TestRunMessage API (200-300+ messages). **Fallback**: `ExecutionMessages.csv` from cleanup path (step-level messages only, displayed as `<pre>` text with ±5 lines). See Execution Messages Matching below.
   - `System.evtx Critical/Errors` — Extracted from `System.evtx` in the cleanup path ZIP. Shows Critical-level (Level=1) and Error-level (Level=2) events within a ±1 hour window of the failure's `SubmittedDateTime`. Each event displays timestamp converted to MYT (UTC+8), level tag (`[Critical]` or `[Error]`), EventID, provider name, and message (truncated to 200 chars). Format: `[M/d/yy H:mm:ss MYT] [Level] EventID NNN (Provider): Message`. Events sorted by timestamp descending (newest first). Critical events are colored red (`#c0392b`) with bold weight. The event closest to the submitted date gets a `>>>` prefix and yellow background (`#fff9c4`) marker. Shows `(no events in +/-1h window)` if no matching events exist. When extraction fails, displays the **actual reason** as a red warning: `evtx extraction timed out after 90s (ZIP: name, size MB)`, `no cleanup path`, `cleanup path not found`, `no ZIP files in cleanup path`, `no system.evtx entry in ZIP`, or `exception during extraction: <message>`. The column outputs raw HTML with `<span>` tags — not passed through `HtmlEnc` (individual messages are HTML-encoded internally).
   - `BSOD Info` — Shows the **full bsod.log content** from the cleanup path ZIP. Scans ALL zip entries matching `bsod.log` (case-insensitive) for multi-BSOD support. Each BSOD entry displays: (1) Summary card with Debug Session Time (MYT), time diff from submitted, dump file name/size, and folder path. (2) Full log content in a scrollable `<pre>` container (max-height: 200px). For logs exceeding 30 lines, a "View Full Log (N lines)" button opens a **draggable/resizable modal** window. The closest-to-submitted BSOD is highlighted with red border and yellow `#fff9c4` background with `*** CLOSEST TO SUBMITTED ***` marker. Full content is base64-encoded during ZIP extraction for safe temp-file transport. **Additionally, all `.dmp` files found anywhere in the ZIP are listed** with their full path and size (in MB), regardless of whether `bsod.log` exists. When `bsod.log` is absent but `.dmp` files exist, the column shows the dmp file listing instead of `(no bsod.log found in ZIP)`. When both exist, the dmp listing appears below the bsod.log content. Displays `(no bsod.log and no .dmp found in ZIP)` only if neither bsod.log nor .dmp files are found.
   - `Statuscope Summary` — SVTools report insights from Axon. **Data source (MANDATORY DEFAULT)**: `mcp_axon-server_get_axon_report_content` for raw SVTools JSON (provides insight type, message, location, IP domain, MCA codes, report path/signature, sub_report tree structure). **Priority**: Derived from `TYPE_PREFIX_PRIORITY` mapping based on insight type prefixes (see Learning 39). **Do NOT use `mcp_genimcp_AxonTool` unless the user explicitly requests genimcp priority enrichment.** The column contains two parts:
     1. **Summary line**: Classifier summary text displayed as bold colored text, plus a "Link to Statuscope" hyperlink and an "Expand" button to open the full-screen modal.
     2. **Inline Insight Summary table**: The full 13-column Insight Summary table is rendered **inline** inside a scrollable container (`max-height:320px; overflow:auto`) so the table is **partially visible** within the cell. Users scroll/drag within the container to browse insights. Columns: #, Priority, Type, Report (hyperlinked to StatusScope with `#fragment` URL), IP, Message, Location, Signature, MCACOD, MCACOD Decode, MSCOD, MSCOD Decode, UC. Rows sorted by priority ascending (P1 first), color-coded per priority (P1=purple `#f3e5f5`, P2=red `#fde8e8`, P10=gray `#f5f5f5`). Priority badges: P1=`#7b2d8e`, P2=`#c0392b`, P10=`#888888`. Report links use `#path_insight_N` fragment for deep linking. The "Expand" button opens a **draggable/resizable full-screen modal** for detailed viewing.
   Displays `(no DebugSnapshotId)` if the failure has null DebugSnapshotId, `(no SVTools report)` if Axon has no report for the record.

**All 6 columns above are mandatory default output.** Never use `(skipped)` placeholders for any column. Every report must populate Execution Messages, System.evtx Critical/Errors, BSOD Info, and Statuscope Summary for all failures.

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

## Workflow

1. **Parse user request** — Extract suite pattern, test cycle, and any filters (e.g., no sighting).
2. **Query NGA live** — Query NGA with the constructed OData filter to collect all failure records. Deduplicate by FailureId.
3. **Deduplicate by TestRunId** — Group failures by `TestRunComposite.TestRunId`. For each group, keep only the failure with the latest `SubmittedDateTime`. Log: `"OData returned M failure records → N unique test runs after dedup"`. This step reduces redundant rows and matches the NGA UI count.
4. **Enrich via NGA REST APIs** — Call `mcp_nga-server_nga_get_testrun` for each unique `TestRunId` to get `Result.ResultCode` (Run State) and cleanup path. Since we already deduplicated by TestRunId, each enrichment call maps 1:1 to a report row.
5. **Collect Axon insights** — For failures with non-null `DebugSnapshotId`:
   - Call `mcp_axon-server_get_axon_report_content` for each record to get the raw SVTools JSON (29MB+, requires double-parse `json.loads(data['result'])`). Extract all insights from `sub_reports` tree (recursive walk) plus root-level `data['insights']`. Each insight has: type, message, location, ip_domain, mcacod, mcacod_decode, mscod, mscod_decode, uc, source/path, insight_index.
   - **Assign priority using `TYPE_PREFIX_PRIORITY` mapping** (default): Map each insight's `type` field to a priority using longest-prefix-first matching: `HW.STUCK_TRANSACTION→1, HW.MCE→1, HW.HANG→1, HW.PORT_STUCK→1, HW.IFA→1, HW.UNEXPECTED_RESET→2, HW.LINK→2, SW.POWER→6, PLATFORM→10, SW→10, HW→10`. Default priority for unmatched types: 10.
   - **Do NOT call `mcp_genimcp_AxonTool`** unless the user explicitly requests genimcp-based priority enrichment. The type-prefix mapping provides reliable priority assignment without the truncation issues and extra API calls of genimcp.
   - Store compiled results (structured insights with all fields + priority) for injection into the Statuscope Summary column.
6. **Parse response & filter Passed** — Merge deduplicated failure records with enriched Run State, SubmittedDateTime, cleanup paths from REST APIs, and Axon insights. **Then discard all failures where Run State = `Passed`** (unless the user explicitly asked to include them). Log the count of excluded Passed failures for the summary.
7. **Generate full HTML report** — Build the report with ALL 6 columns populated: #, Failure Info (Run State + Failure Name + Bucket + Signatures + Submitted Date), Execution Messages, System.evtx Critical/Errors, BSOD Info, Statuscope Summary. For each failure:
   - Fetch execution messages via NGA TestRunMessage API using `testRunId` (fallback: read `ExecutionMessages.csv` from cleanup path)
   - Extract `System.evtx` from cleanup ZIP (Critical Level=1 + Error Level=2, ±1h window)
   - Extract `bsod.log` from cleanup ZIP
   - Inject Axon insights with priority color coding
   - Use `Start-Job` with 90s timeout for remote ZIP access
   - Cache ZIP results per cleanup path to avoid redundant access
   Save as `gen_wl_report_compact.ps1` and execute.
8. **Post-process: color Execution Messages** — Run `color_execmsg.ps1` to apply keyword-based color coding to the Execution Messages column.
9. **Save and open** — Write to `output/` and auto-open in browser.

**Important**: All 6 columns must be populated in every report. Do NOT generate a "base" report with `(skipped)` placeholders and post-process later. The single `gen_wl_report_compact.ps1` script must produce the complete report with all columns filled.

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
10. **`SubmittedDateTime` from NGA is UTC** — The field is ISO 8601 with `Z` suffix (e.g., `2026-03-28T22:10:10.2150243Z`). Convert to local MYT (UTC+8) for display. MYT abbreviation must be derived manually since PowerShell returns `MalayPeninsulaStandardTime` for `[System.TimeZoneInfo]::Local`.
11. **`ExecutionMessages.csv` timestamps are UTC** — Confirmed by sub-second match: CSV line `22:10:09` matches NGA `SubmittedDateTime` `22:10:10Z` for the same failure. Never assume CSV timestamps are local station time.
12. **Step name matching is more reliable than timestamp matching** — The step function name (e.g., `hpreboot_massdeploy_run`) uniquely identifies the failing step in the CSV with 0s diff. Timestamp fallback can match wrong lines if the CSV contains many entries.
13. **Signatures can be bucket descriptions, not step names** — Signatures like `PCD_PMC:PMC_Hang` or `Windows:BSOD:SYSTEM_SERVICE_EXCEPTION` are bucket/signal descriptions, not CSV step function names. They will never match a `*funcName*Failed*` pattern in the CSV. The real step name (e.g., `hpreboot_massdeploy_run`) must come from examining the CSV or test run context.
14. **Cleanup paths get reused — CSV may be stale** — When a station runs a new test on the same test line, the cleanup path is overwritten. To detect staleness, check if the failure's `SubmittedDateTime` falls within the CSV's overall time range (first line timestamp to last line timestamp, with ±1 hour padding). If outside, the CSV belongs to a different run — display `(CSV from different run)`. Do NOT use the matched line's timestamp for the stale check — long gaps (20+ hours) are normal when a station is stuck in `WaitingForTargetReboot` during hangs.
15. **Timestamp fallback must compare UTC vs UTC** — The CSV timestamps are UTC and `SubmittedDateTime` is UTC. Do NOT convert either to local time before comparison, or you'll get false matches offset by the timezone difference (e.g., 8 hours for MYT).
16. **PDX station ZIPs may hang on network access** — Cleanup paths on `pdxcv14a-cifs.pdx.intel.com` can cause indefinite hangs when reading ZIPs. Use `Start-Job` with a timeout (e.g., 90s via `Wait-Job -Timeout`) for remote ZIP extraction.
17. **Post-processing approach for Execution Messages** — Generate the base HTML report first (`gen_wl_report_compact.ps1`), then post-process it with `add_execmsg_column.ps1` to inject the Execution Messages column. This avoids re-running expensive NGA queries and evtx extraction when only the exec msg logic changes.
18. **System.evtx Critical Events extraction** — Extract `System.evtx` from ZIP files in the cleanup path (located at `SUT/retry0/Cleanup/eventlogs/system.evtx` inside the ZIP). Use `Get-WinEvent -Path` with `-FilterXPath "*[System[Level=1]]"` for Critical events. Convert timestamps to MYT (UTC+8) for display consistency with Submitted Date.
19. **"Unbucketised" means `SightingId eq null`, NOT `BucketId eq null`** — In this workflow, "unbucketised" refers to failures that have not been triaged (no sighting assigned). These failures may still have a `BucketId` and `BucketName`. Use `SightingId eq null` in the OData filter. `BucketId eq null` returns a much larger set of literally unbucketed failures (106 vs 8).
20. **Cleanup ZIP internal structure** — The station ZIP (e.g., `FM05WVAW0548.zip`) contains files under `SUT/retry0/`. Key paths: `SUT/retry0/Cleanup/eventlogs/system.evtx` (System event log, ~26MB), `SUT/retry0/Cleanup/bsod_check.log` (BSOD check process log — NOT the same as `bsod.log`), `SUT/retry0/Cleanup/BSOD/` (OS/system info JSONs), `SUT/retry0/Cleanup/intel-content-bsod-check-sut-post.report.json` (BSOD report). There is also a duplicate at `SUT/retry0/Cleanup/eventlog_report/system.evtx`.
21. **`bsod.log` does not exist in tested ZIPs** — None of the cleanup ZIPs examined contained a `bsod.log` file. The file `bsod_check.log` is the BSOD check process log (contains config args, debug output, "no events found" messages) and should NOT be parsed as BSOD crash data. If `bsod.log` is absent but `.dmp` files exist, display the dmp file listing (path + size). If neither bsod.log nor .dmp files are found, display `(no bsod.log and no .dmp found in ZIP)` in the BSOD Info column.
22. **Empty cleanup paths for InProgress and old Passed runs** — InProgress runs (e.g., `87d826ee`, `f37adc9d`) have empty cleanup directories with no ZIP files because the run hasn't completed cleanup yet. Old Passed runs (e.g., `7d382e9d`) may also have empty cleanup paths if files were cleaned up. Display `(no ZIP)` for both cases.
23. **BSOD Info extraction from `bsod.log`** — The file may be named `bsod.log` or `BSOD.log` (use case-insensitive match: `-ieq 'bsod.log'`). Located at `SUT/retry0/Cleanup/BSOD/BSOD.log` inside the ZIP. Extract three fields: (1) **Debug Session Time** from the line `Debug session time: Thu Mar 26 08:27:15.855 2026 (UTC + 8:00)` — parse the timestamp, account for the timezone offset shown in parentheses, convert to MYT. (2) **Bugcheck Code** from the first non-empty line after the `Bugcheck Analysis` asterisk box (e.g., `DPC_WATCHDOG_VIOLATION (133)` or `DRIVER_POWER_STATE_FAILURE (9f)`). (3) **FAILURE_BUCKET_ID** from the line `FAILURE_BUCKET_ID: 0x133_ISR_ACPI!ACPIInterruptDispatchEvents`. If none of these fields are found, show the first 300 chars as a preview. Use `Start-Job` with timeout like evtx extraction.
24. **Deduplicate ZIP access across columns** — Critical Events, BSOD Info, and potentially other columns all read from the same ZIP. Cache results per cleanup path (`$cpCriticals`, `$cpBsod`) to avoid re-opening the same ZIP. Multiple failures sharing the same cleanup path (e.g., `87d826ee` and `f37adc9d` on the same test line) benefit from this deduplication.
25. **Debug session time in `bsod.log` includes timezone offset** — The line `Debug session time: Thu Mar 26 08:27:15.855 2026 (UTC + 8:00)` already shows local time with its offset. To convert to MYT: parse the timestamp, subtract the stated offset to get UTC, then convert UTC to MYT via `[System.TimeZoneInfo]::ConvertTimeFromUtc()`. Do NOT assume the offset is always +8 (MYT) — some stations may have different timezones.
26. **Bugcheck code location in `bsod.log`** — The bugcheck code (e.g., `DPC_WATCHDOG_VIOLATION (133)`) is the first non-blank, non-asterisk line after the `Bugcheck Analysis` box. The box is delimited by lines of `*****`. After the closing asterisk line, skip blank lines, then the next content line is the bugcheck name with its hex code in parentheses.
27. **Selective column regeneration (debug only)** — When debugging a single column's extraction logic, you MAY temporarily use `(skipped)` placeholder for other columns to speed up iteration. However, the final report delivered to the user must ALWAYS have all 6 columns fully populated — never deliver a report with `(skipped)` placeholders.
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
45. **Critical & Error Events with ±1h time window** — The Critical Events column (renamed to "System.evtx Critical/Errors") extracts both Level=1 (Critical) and Level=2 (Error) events from `System.evtx` via XPath `*[System[(Level=1 or Level=2)]]`. All events are cached as structured data (UTC timestamp, level, provider, EventID, message) per cleanup path. Per-failure filtering applies a ±1 hour window around that failure's `SubmittedDateTime` (compared in UTC). Events are sorted chronologically. Critical events are colored red `#c0392b` bold; Error events use default color. The event closest to submitted date gets a `>>>` prefix and yellow `#fff9c4` background marker. The column outputs raw HTML — `Format-CritEvents` returns `<span>` tags with inline styles and HTML-encodes each message internally, so the row template must NOT wrap it in `HtmlEnc`.
46. **Statuscope Summary column header and link placement** — The SVTools column is renamed to "Statuscope Summary". The summary text is displayed as bold colored text (not a hyperlink). The "Link to Statuscope" hyperlink is placed on a separate line below the `<pre>` insights block. The `build_axon_insights_with_priority.ps1` script also injects the `<th>` header (matching "Statuscope" or "SVTools" for idempotent strip) before `</tr></thead>`.
47. **Newest-first ordering for Execution Messages and Critical/Error Events** — Both columns display entries sorted from newest to oldest (top to bottom). Execution Messages: the ±5 line extraction loop iterates from `$end` down to `$start` (`for ($i = $end; $i -ge $start; $i--)`). Critical/Error Events: `Sort-Object { [datetime]::Parse($_.utc) } -Descending` in `Format-CritEvents`.
48. **Wrap `Sort-Object` result in `@()` to prevent single-element unwrap** — When `$filtered` contains exactly 1 hashtable, `Sort-Object` returns a bare hashtable instead of a 1-element array. Then `$sorted.Count` returns the number of *keys* (6) instead of 1, and `$sorted[$i]` indexes into nothing useful — producing 6 empty `[] [] EventID ():` rows. Fix: `$sorted = @($filtered | Sort-Object ...)`. This is a classic PowerShell 5.1 pipeline gotcha affecting any single-object-to-Sort-Object pattern.
49. **Stale CSV check must use CSV time range, not matched line timestamp**
50. **(removed — pagination rules removed)**

 — The old stale check compared the matched CSV line's timestamp to `SubmittedDateTime` with a 1-hour threshold. This produces false positives when a test run has long gaps in the CSV (e.g., 27+ hours stuck in `WaitingForTargetReboot` during a hang). The failure's `SubmittedDateTime` falls within the gap, so the nearest CSV line is hours away, incorrectly triggering "CSV from different run". Fix: parse the CSV's first and last timestamps to get the overall time range, then check if `SubmittedDateTime` falls within `[first - 1h, last + 1h]`. This correctly identifies the CSV as belonging to the same run.
51. **NGA TestRunMessage API for full execution messages** — The NGA Results service exposes `POST /Results/{project}/api/TestRun/TestRunMessage` which accepts `{"Ids":["<testRunId>"]}` and returns ALL execution messages (296+ per test run). This includes Orchestrator step messages (same as CSV), User messages (recovery flow, iteration counts, stage runner), StationAutomationService messages, and ResultService messages. The `mcp_nga-server_nga_get_execution_messages` MCP tool uses the WRONG endpoint path (`/Results/{project}/api/ExecutionMessage/{id}` → 404). Always use the Python helper `get_testrun_messages.py` instead. Swagger spec found at `https://nga-prod.laas.icloud.intel.com/Results/swagger/v1/swagger.json`.
52. **`get_testrun_messages.py` Python helper for authenticated API calls** — NGA Results API requires MSAL bearer token authentication (app ID `5010f2b6-5feb-4de3-89a2-dba1172b07f8`, scope `6af0841e-c789-4b7b-a059-1cec575fbddb/.default`). PowerShell `Invoke-WebRequest -UseDefaultCredentials` does NOT work (returns "Access token is missing"). The Python helper handles auth, calls the POST endpoint, strips HTML tags from messages, and outputs sorted JSON to stdout. Called from PowerShell via `& python "$PSScriptRoot\get_testrun_messages.py" 'nvl_fv_or' $testRunId 2>$null`.
53. **TestRunMessage API message sources and types** — Messages have 4 sources: `Orchestrator` (~263 msgs, step Running/Passed/Failed), `User` (~30 msgs, recovery flow `--- STARTING RECOVERY FLOW ---`/`Hang Flow`/`--- RECOVERY FLOW END ---`, iteration counts `Failure during iteration N`, stage runner output, BIOS knobs), `ResultService` (2 msgs, test started/completed), `StationAutomationService` (1 msg, failing test notification). User messages contain HTML `<span>` tags with inline styles (colors, bold) that must be stripped for display.
54. **ExecutionMessages.csv only has step-level messages** — The CSV in the cleanup path only contains Orchestrator-source step execution messages (Running/Passed/Failed). It does NOT include recovery flow events, status updates, iteration counts, or other NGA platform events that are visible on the NGA failure web page. The API is the only way to get the complete message set.
55. **Multi-BSOD support in cleanup ZIPs** — A single cleanup ZIP may contain multiple `bsod.log` files at different paths (e.g., `SUT/retry0/Cleanup/BSOD/BSOD.log` and `SUT/retry1/Cleanup/BSOD/BSOD.log`). The `Get-BsodInfo` function scans ALL zip entries matching `bsod.log` (case-insensitive), extracts each one, and identifies the BSOD closest to the failure's `SubmittedDateTime` by comparing Debug Session Time. The closest BSOD is highlighted with a yellow `#fff9c4` background and `>>>` marker.
56. **Exec message timestamp display format is `M/d/yy H:mm:ss MYT`** — All timestamps in the Execution Messages column use `M/d/yy H:mm:ss MYT` format (24-hour, no AM/PM) to match the Submitted Date column style. Both API-sourced and CSV-sourced messages use this same format after UTC-to-MYT conversion.
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
69. **Exclude Passed run state by default** — Failures with `Result.ResultCode = Passed` are excluded from the report after enrichment (workflow step 5). The HTML summary section must include the note `"Note: Failures with Run State = Passed are excluded."`. This filter is applied post-enrichment because the OData API does not expose `Result.ResultCode` as a filterable field — it comes from the `nga_get_testrun` REST call. Only include Passed failures if the user explicitly says "include passed" or "show all run states".
68. **Evtx `SpecifyKind` causes double timezone shift — use `.ToUniversalTime()` instead** — In `Format-CritEvents`, `[System.DateTime]::SpecifyKind([datetime]::Parse($evt.utc), [System.DateTimeKind]::Utc)` is WRONG when `$evt.utc` is an ISO 8601 string with `Z` suffix. `[datetime]::Parse('...Z')` converts to local time (e.g., +8h MYT) with `Kind=Local`. `SpecifyKind(..., Utc)` merely relabels the value as UTC without adjusting — so `14:19 MYT` becomes `14:19 UTC`. Then `ConvertTimeFromUtc` adds another +8h → `22:19 MYT` (8 hours too late). Fix: replace `SpecifyKind(...)` with `[datetime]::Parse($evt.utc).ToUniversalTime()`, which properly converts back to UTC regardless of the parsed Kind. This applies ONLY to `Format-CritEvents` — the exec messages `SpecifyKind` (line ~257) works correctly because `$e.utc` is already `Kind=Utc`, and the BSOD `SpecifyKind` (line ~656) works correctly because `$e.utcDebug` is computed with `Kind=Unspecified`.
70. **OData returns more failure records than NGA UI shows — deduplicate by TestRunId** — The OData API returns individual failure records (e.g., 51), while the NGA UI counts unique test runs (e.g., 39). A single TestRunId can produce 2–5 failure records from different sources (Orchestrator, RecoveryFlow) or multiple failing steps. By default, deduplicate by TestRunId — keep only the failure with the latest `SubmittedDateTime` per TestRunId. This matches the NGA UI count and avoids redundant report rows that share identical cleanup paths, execution messages, and evtx data. Always log both counts: `"OData returned M failure records → N unique test runs after dedup"`. To show all individual records, the user must explicitly request it (e.g., "show all failure records", "don't deduplicate").
71. **`openExecModal` JS selector must match the actual DOM structure** — The `openExecModal(btn)` function in the HTML report must use `btn.parentElement` to get the `<td>` cell, then `cell.querySelector("div[style*='max-height']")` to find the scrollable container. A previous version used `btn.closest('td')` + `cell.querySelector('div > div[style*="max-height"]')` which required the scrollable `<div>` to be nested inside a wrapper `<div>`. But `Get-ExecMessages` renders the scrollable div directly inside `<td class="exec">` (no wrapper div), so the `div > div` selector returned null and the modal opened empty. The correct function also removes `max-height` in the modal copy for full visibility: `inner.style.maxHeight = 'none'; inner.style.overflow = 'visible'`. **Always copy the latest `openExecModal` from `gen_wl_report_compact.ps1` when generating new report scripts.**
73. **Cleanup paths vary per testrun — never construct or assume them** — Each testrun has its own unique `CleanupPath` returned by `mcp_nga-server_nga_get_testrun`. The suite folder component (e.g., `NVL_MBL_Qual`, `NVL_HX_SST`, `NVL_HX_Concurrency`) and the station/test subfolder are determined by NGA at runtime and cannot be predicted from the test cycle name or suite name. Never hardcode or pattern-construct cleanup paths (e.g., assuming `NVL_HX_EXT_B0_ES2` from the cycle name `nvl-hx-ext-b0`) — this produces paths to non-existent folders and causes all evtx/BSOD columns to be empty. Always use the actual `CleanupPath` value from the `nga_get_testrun` API response for each testrun.
