---
name: fv-usb/galaxy-xml-validator
version: 1.0.0
owner: kvejaya
description: Galaxy XML test case validator — standardization checks against golden flow, dictionary-based flow validation, and naming convention enforcement for USB Galaxy test cases
---

# FV-USB — Galaxy XML Validator

## Overview

This skill validates Galaxy XML test cases for USB functional validation. It performs two categories of checks:

1. **Standardization** — structural/format consistency cross-checked against golden flow and peer XML files
2. **Flow Validation** — test flow correctness enforced via a dictionary of required patterns

## Golden Flow Reference

```
C:\validation\windows-test-content\usb\Galaxy\USB_Golden_Flow_ww*.xml
```

The golden flow defines the authoritative structure for all Galaxy XML test cases. All submitted XML files are compared against it for structural consistency.

## Test Case Directory

```
C:\validation\windows-test-content\usb\galaxy\test_case\
```

---

## Standardization Checks

These checks enforce consistent XML structure across all test cases.

### 1. Root Structure

- XML must start with `<GALAXY><CONFIGURATION>` — **no `<ATTRIBUTES>` block** between them
- Forbidden: `<ATTRIBUTES><GeneratedWith>...</GeneratedWith><GeneratedAt>...</GeneratedAt></ATTRIBUTES>` after `<GALAXY>`

### 2. VARIABLES Section Formatting

All variables must be grouped with XML comments matching the golden flow:

```xml
<VARIABLES>
    <TimeOut>...</TimeOut>
    <Duration>...</Duration>
    <NumDisplay>...</NumDisplay>
    <TestLoop>...</TestLoop>

    <!-- Device/Platform -->
    <ip_mode>...</ip_mode>
    <cswitch_enable>...</cswitch_enable>
    <device_list>...</device_list>
    <connect_port_list>...</connect_port_list>
    <disconnect_port_list>...</disconnect_port_list>

    <!-- Port/Speed -->
    <portchain>...</portchain>
    <portchainspeed>...</portchainspeed>
    <ignoreportchain>...</ignoreportchain>

    <!-- Power Management - TTK3/Timeouts -->
    <ttk3_timeout>...</ttk3_timeout>
    <ping_server_timeout>...</ping_server_timeout>
    <PMStateTime>...</PMStateTime>

    <!-- Power Management - Sx/S0ix Checks -->
    <FailOnPMCError>...</FailOnPMCError>
    <FailOnMemorySelfRefresh>...</FailOnMemorySelfRefresh>
    <FailOnGlobalResetPolicy>...</FailOnGlobalResetPolicy>
    <FailOnLastWakeCause>...</FailOnLastWakeCause>
    <FailOnLastPowerFlow>...</FailOnLastPowerFlow>
    <PMLegacyVerification>...</PMLegacyVerification>
    <FailOnSxix>...</FailOnSxix>
    <SxixState>...</SxixState>
    <SxixThreshold>...</SxixThreshold>
    <FailOnS0ix>...</FailOnS0ix>
    <S0ixState>...</S0ixState>
    <S0ixThreshold>...</S0ixThreshold>

    <!-- Workload -->
    <bulk_time>...</bulk_time>
    <ffmpeg_time>...</ffmpeg_time>
    <ffmpeg_speed>...</ffmpeg_speed>
    <audio_time>...</audio_time>
    <player>...</player>
    <playback>...</playback>
    <record>...</record>
    <periodic_time>...</periodic_time>
    <test_time>...</test_time>

    <!-- Performance Counters -->
    <pc>...</pc>
    <pccheckinterval>...</pccheckinterval>
    <pccheckduration>...</pccheckduration>

    <!-- Misc -->
    <xhciSelect>...</xhciSelect>
</VARIABLES>
```

### 3. Top-Level FLOW Structure

All test cases must have this top-level flow hierarchy:

```
FLOW (Example Test Flow)
├── FLOW (Pre Test)
│   ├── ConditionBlock (CheckEvent Cswitch Pre)
│   └── TEST (Speed Verification Pre)
├── FLOW (Test)
│   └── [test-specific steps]
└── FLOW (Post Test)
    └── ConditionBlock (CheckEvent Cswitch Post)
```

### 4. Peer Cross-Check

When validating a specific XML file, compare its structure against other XML files with similar keywords in the filename. For example:
- `PM_S0ix_*.xml` → compare against other `*S0ix*.xml` files
- `S3_*.xml` → compare against other `*S3*.xml` files
- `USB_20_*.xml` → compare against other `*Base_traffic*.xml` files

Key structural elements to match:
- Same FLOW nesting depth
- Same element types in equivalent positions
- Consistent attribute patterns (CapExeTime, Delay, Duration, EnableRun, ExecuteOrder, etc.)

---

## Flow Dictionary — Test Flow Validation Rules

### Rule 1: Base Traffic

**Trigger:** XML filename or flow contains "Base traffic", "Bulk", "Isoch", or "Interrupt"

**Required:** Must include ALL three traffic types **within the Test FLOW** (not just in TESTCONFIG):
- **Bulk** — FIO, CheckSumFT, or IOMeter TEST steps inside `<FLOW Desc="Test">`
- **Isoch Audio** — `<TEST Desc="Audio"/>` as a **flat direct child** of `<FLOW Desc="Test">` — NOT wrapped in a nested `<FLOW Desc="Isoch_Audio_Traffic">`
- **Isoch Camera** — FFMPEG TEST steps inside `<FLOW Desc="Test">`

**Correct Audio structure (match reference `USB_20_Run_Base_traffic_*.xml`):**
```xml
<FLOW Desc="Test" ...>
    <TEST ... Desc="FFMPEG" ... ExecuteOrder="1" .../>
    <TEST ... Desc="Audio" ... ExecuteOrder="1" .../>   ← flat, direct child
    <TEST ... Desc="Speed Verification" ... ExecuteOrder="2" .../>
    ...
</FLOW>
```

**Wrong (do NOT do this):**
```xml
<FLOW Desc="Test" ...>
    <TEST ... Desc="FFMPEG" .../>
    <FLOW Desc="Isoch_Audio_Traffic" ...>               ← WRONG: nested FLOW wrapper
        <TEST Desc="Audio Validation" .../>
        <TEST Desc="Audio" .../>
    </FLOW>
</FLOW>
```

**Important:** Do NOT scan the entire file for these keywords. TESTCONFIG may define Audio/FFMPEG entries that are never called. Check `<TEST>` elements that are direct children of `<FLOW Desc="Test">` **AND** recurse into any nested `<FLOW>` children inside the Test FLOW when checking for Audio. A common mistake is having FFMPEG and CheckSumFT in the Test flow but Audio only defined in TESTCONFIG — this is a FAIL.

### Rule 2: Sx + Sxiy (Power Management Flows)

**Trigger:** XML filename or flow contains "S0ix", "S0ixy", "S3", "S3ixy", "S4", "S4ixy", "S5", "S5ixy"

**Required:**
- **Sxix residency checking** — CHECKER with Command containing "S0ixCaptureCheck" or "SxixCaptureCheck"
- **Pre capture** — CHECKER with `-Capture` flag must appear BEFORE SleepState in the flow

### Rule 3: Connect/Disconnect/Hotplug in Sx State

**Trigger:** XML filename or flow contains "Connect", "Disconnect", "Hotplug" AND an Sx state (S0ix, S3, S4, S5)

**Required:** After any connect/disconnect/hotplug step within an Sx flow, there must be a **TTK Verify Post Event** — HOST-EV with Desc containing "TTK Verify" and "Post Event" (or "Post")

### Rule 4: No "Copy" in Step Names

**Trigger:** All test steps (FLOW, TEST, HOST-EV, CHECKER, SleepState, DELAY, RemoteUtils, ConditionBlock)

**Required:** The `Desc` attribute must NOT contain the word "copy" (case-insensitive). This indicates a duplicated step that was not properly renamed.

### Rule 5: Sxix Residency Naming Convention

**Trigger:** All XML files containing CHECKER elements related to Sxix/S0ix residency

**Required:** All CHECKER `Desc` attributes referencing Sxix/S0ix residency must follow the golden flow naming convention:

**Valid patterns:**
- `Capture Sxix Residencies - S3ix`
- `Capture Sxix Residencies - S4ix`
- `Capture Sxix Residencies - S5ix`
- `Capture S0ix Residencies - S0ix`
- `Capture Sxix Residencies Flow`
- `Capture S0ix Residencies Flow`
- `Capture Sxix Residencies`
- `Capture S0ix Residencies`
**Invalid patterns (will FAIL):**
- `Captur S0ix Residencies - S0ix` (typo — missing 'e' in Capture)
- `CaptureEvent Sxix Residencies - S3` (should be `Capture`, not `CaptureEvent`, and missing "ix" suffix)
- `CaptureEvent Sxix Residencies - S4` (should be `Capture`, not `CaptureEvent`, and missing "ix" suffix)
- `CaptureEvent Sxix Residencies - S5` (should be `Capture`, not `CaptureEvent`, and missing "ix" suffix)
- `S0ix Residency Capture` (wrong word order — should be `Capture Sxix Residencies - S3ix` etc.)

### Rule 6: PM Verification Blocks

**Trigger:** XML filename contains PM sleep state keywords (S3, S4, S5, S0ix, WR, G3)

**Required:** PM files must contain a `PM Verification` FLOW block inside their sleep state flow. The structure differs by sleep type:

**S3/S4/S5 PM Verification:**
- `CheckEvent GlobalReset - Sx`
- `CheckEvent Sxi2-0 or Above - Sx`
- `CheckEvent Memory Self Refresh - Sx`
- `CheckEvent Non-Legacy Verification - Sx` (wraps LastPowerFlow, LastWakeCause, PMC FW Error Checker)

**S0ix PM Verification:**
- `CheckEvent GlobalReset - S0ix`
- `CheckEvent S0i2-0 or Above - S0ix`
- `CheckEvent Non-Legacy Verification - S0ix` (wraps PMC FW Error Checker, LastWakeCause — no MemSelfRefresh, no LastPowerFlow)

### Rule 7: TESTCONFIG Entry Matching

**Trigger:** All XML files with a `<TESTCONFIG>` section containing `<CHECKER>` entries

**Required:**
1. **No wrong-suffix entries** — CHECKER Desc suffixes (e.g., `- S3`, `- S4`, `- S0ix`) must match the file's sleep state. A PM_S3 file must not contain CHECKERs ending in `- S4`, `- S5`, `- S0ix`, etc.
2. **No unreferenced entries** — Every CHECKER in TESTCONFIG must be referenced by at least one step in the FLOW section. Unreferenced CHECKERs are dead weight and must be deleted.
3. **Correct inner Arg values** — For CHECKERs with hardcoded sleep state args (`LastPowerFlow -PowerFlow`, `MemSelfRefresh -State`), the inner `val` must match the file's sleep state.

**Non-PM files** (base traffic, split traffic, hotplug, UAOL, etc.) should have **zero** PM CHECKER entries unless their FLOW explicitly references them.

---

## Bonus Checks (Cosmetic)

These enforce consistent formatting across all XML files:

| ID | Check | Fix |
|----|-------|-----|
| B1 | `Error checker` casing | Must be `Error Checker` (capital C) |
| B2 | `Exit1` spacing | Must be `Exit 1` (with space) |
| B3 | Double spaces in Desc | `PMC FW  Error` → `PMC FW Error` |
| B4 | `S0iX` casing | Must be `S0ix` (lowercase x) |
| B5 | Space before self-closing tag | `RunType="Default" />` → `RunType="Default"/>` (no space before `/>`) |
| B6 | Blank line before VARIABLES comment group | Each `<!-- comment -->` header in `<VARIABLES>` must be preceded by a blank line (empty `\n`) — e.g. `\n\n            <!-- Port/Speed -->` |

---

## PM Flow Reference Patterns (from Golden Flow)

### S0ix Flow Pattern

```
FLOW (S0ix Flow)
├── CHECKER (Capture S0ix Residencies)
├── SleepState (S0ix)
├── HOST-EV (TTK Verify S0ix)
├── DELAY (S0ix Sleep Time)
├── HOST-EV (TTK Press PowerButton Flow - S0ix)
├── RemoteUtils (After S0ix Test Connection)
└── FLOW (PM Verification - S0ix)
    ├── ConditionBlock (CheckEvent GlobalReset - S0ix)
    ├── ConditionBlock (CheckEvent S0i2-0 or Above - S0ix)
    └── ConditionBlock (CheckEvent Non-Legacy Verification - S0ix)
        └── ConditionBlock (CheckEvent PMC FW Error Checker - S0ix)
```

### S3/S4/S5 Flow Pattern

```
FLOW (Sx Flow)
├── CHECKER (Capture Sxix Residencies)
├── SleepState (S3/S4/S5)
├── HOST-EV (TTK Verify Sx)
├── DELAY (PMStateTime)
├── HOST-EV (Wake — Galaxy Wake or TTK PowerButton)
├── RemoteUtils (After Sx Test Connection)
└── FLOW (PM Verification - Sx)
    ├── ConditionBlock (CheckEvent GlobalReset - Sx)
    ├── ConditionBlock (CheckEvent Sxix - Sx)
    ├── ConditionBlock (CheckEvent Memory Self Refresh - Sx)
    └── ConditionBlock (CheckEvent Non-Legacy Verification - Sx)
        ├── ConditionBlock (CheckEvent LastPowerFlow - Sx)
        ├── ConditionBlock (CheckEvent LastWakeCause - Sx)
        └── ConditionBlock (CheckEvent PMC FW Error Checker - Sx)
```

---

## Validation Script

The validation script is located at:

```
.opencode/skill/fv-usb/galaxy-xml-validator/validate.py
```

### Usage

```bash
# Validate a single XML file
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --file <path_to_xml>

# Validate all XML files in a directory
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --dir <path_to_directory>

# Validate with golden flow cross-check
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --file <path_to_xml> --golden <path_to_golden>

# Output to both console and report file
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --file <path_to_xml> --report <path_to_report>

# Auto-fix standardization issues (removes ATTRIBUTES block, adds VARIABLES comment groups)
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --file <path_to_xml> --fix

# Auto-fix all XML files in a directory
python .opencode/skill/fv-usb/galaxy-xml-validator/validate.py --dir <path_to_directory> --fix
```

### Auto-Fix Capabilities

The `--fix` flag automatically corrects all standardization and cosmetic issues:

**Phase 1 — Global Text Replacements:**
- Removes `<ATTRIBUTES>` block (Galaxy auto-generated metadata)
- Reorganizes VARIABLES with proper XML comment headers
- `CaptureEvent` / `Captur` → `Capture` prefix
- `Error checker` → `Error Checker` (casing)
- `Exit1` → `Exit 1` (spacing)
- Double spaces in Desc attributes
- `S0iX` → `S0ix` (casing)
- Removes `copy` / `Copy` from Desc attributes
- `" />"` → `"/>"` — removes space before self-closing tag
- Adds blank line before each `<!-- comment -->` group header in `<VARIABLES>` section

**Phase 2 — TESTCONFIG Cleanup:**
- Deletes CHECKER entries with wrong sleep-state suffixes
- Deletes unreferenced CHECKER entries (not called by any FLOW step)
- Fixes inner Arg values (`LastPowerFlow -PowerFlow`, `MemSelfRefresh -State`) to match file's sleep state

**Phase 3 — Residency Naming:**
- `S0ix Residency Capture` → `Capture Sxix Residencies - S{3,4,5}ix` (per file's sleep state)
- Missing `ix` suffix: `S3` → `S3ix`, `S4` → `S4ix`, `S5` → `S5ix`

### Output Format

```
╔══════════════════════════════════════════════════════╗
║  Galaxy XML Validator — <filename.xml>               ║
╠══════════════════════════════════════════════════════╣
║  [PASS] Standardization: Root structure OK           ║
║  [PASS] Standardization: VARIABLES formatting OK     ║
║  [FAIL] Standardization: Missing <ATTRIBUTES> block  ║
║  [PASS] Flow Rule 1: Base traffic has bulk+isoch     ║
║  [FAIL] Flow Rule 4: "copy" found in step Desc       ║
╠══════════════════════════════════════════════════════╣
║  Results: 3 PASS, 2 FAIL, 0 SKIP                     ║
╚══════════════════════════════════════════════════════╝
```

---

## inject_golden_flow_helper.py — Formatting Rules

The inject script at `C:\validation\windows-test-content\usb\Galaxy\inject_golden_flow_helper.py` generates/updates Test_Case XMLs. It **MUST** call `fix_variables_section()` after every write. This function enforces:

1. **No space before `"/>`** — `re.sub(r' +/>', '/>', text)` — self-closing tags must be `RunType="Default"/>` not `RunType="Default" />`
2. **Blank line + comment before each VARIABLES group** — each of the 7 comment headers must be preceded by `\n\n` (one blank line):

```xml
            <TimeOut>...</TimeOut>
            <Duration>...</Duration>
            <NumDisplay>...</NumDisplay>
            <TestLoop>...</TestLoop>

            <!-- Device/Platform -->
            <ip_mode>...</ip_mode>
            <cswitch_enable>...</cswitch_enable>
            <device_list>...</device_list>
            <connect_port_list>...</connect_port_list>
            <disconnect_port_list>...</disconnect_port_list>

            <!-- Port/Speed -->
            <portchain>...</portchain>
            <portchainspeed>...</portchainspeed>
            <ignoreportchain>...</ignoreportchain>

            <!-- Power Management - TTK3/Timeouts -->
            <ttk3_timeout>...</ttk3_timeout>
            <ping_server_timeout>...</ping_server_timeout>
            <PMStateTime>...</PMStateTime>

            <!-- Power Management - Sx/S0ix Checks -->
            <FailOnPMCError>...</FailOnPMCError>
            ...

            <!-- Workload -->
            <bulk_time>...</bulk_time>
            ...

            <!-- Performance Counters -->
            <pc>...</pc>
            ...

            <!-- Misc -->
            <xhciSelect>...</xhciSelect>
```

> **NEVER remove `fix_variables_section()` or bypass its call in `inject()`.** Any future edits to the inject script must preserve these two fixes.

---

## Known File-Specific Issues & Learnings

### Files that were fixed (learnings for future sessions)

#### VARIABLES comment groups missing — root causes
- Files generated or edited by tools using Python's `xml.etree.ElementTree` will silently lose all XML comments on round-trip. Always use raw string manipulation (not ET) when writing these XMLs.
- Some files have no blank lines between variable groups — the comment injection regex must handle BOTH cases: blank lines present AND no blank lines before anchor. Use direct string replacement as fallback:
  ```python
  text = text.replace(f'\n{indent}<ip_mode>', f'\n\n{indent}<!-- Device/Platform -->\n{indent}<ip_mode>', 1)
  ```
- The 4 Exercise files (`PM_S0ix/S3/S4/S5_+_*ixy_-_Exercise_*_flow_with_device_connected.xml`) had no comment groups at all — injected all 7.
- `USB_20_Run_Base_traffic_with_Bulk_Isoch_Interrupt_Traffic_with_LPM_RTD3.xml` had no blank lines before anchors — required direct replacement instead of blank-line-based regex.

#### `--timeout` hardcoded values
- All `<arg name="--timeout" val="60"/>` in TESTCONFIG HOST-EV entries must use `val="$VAR{ttk3_timeout}"`.
- **Do NOT change** `<ttk3_timeout>60</ttk3_timeout>` inside `<VARIABLES>` — this is the variable *definition* with a default value, not a hardcoded timeout arg.
- Files affected: all 4 Exercise files + `PM_S0ix_+_S0ixy_-_Connect_while_in_CS_S0ix.xml`.

#### Double spaces in Desc — origin is the golden flow
- The golden flow itself (`USB_Golden_Flow_ww*.xml`) had double spaces: `"CheckEvent PMC FW Error Checker -  S3"` (double space before Sx state). Fix the golden first, then propagate to all Test_Case XMLs.
- Pattern: `re.sub(r'(Desc="[^"]*?)  ([^"]*")', lambda m: m.group(1) + ' ' + m.group(2), text)`

#### `Pre test` capitalisation
- 3 files had `Desc="Pre test"` (lowercase `t`). Golden standard is `Desc="Pre Test"`.
- Files: `PM_S3_+_S3ixy_-_USB20_32_Gen1x1_32_Gen2x1_application_traffic*.xml`, `S3_with_USB2_UAOL_non-UAOL_traffic.xml`, `S3_with_USB2_UAOL_non-UAOL_traffic_behind_hub.xml`.

#### Trailing space in Desc
- 3 files had `Desc="Speed Verification 2 "` (trailing space). Strip with `re.sub(r'Desc="([^"]*) "', r'Desc="\1"', text)`.
- Files: `Rapid_system_Warm_Reset.xml`, `xHCI_RTD3_with_ADSP_in_D0_with_USB2_UAOL_device_connected.xml`, `xHCI_RTD3_with_ADSP_in_D0_with_USB2_UAOL_device_connected_behind_hub.xml`.

#### Space before `/>` — origin
- Spaces before `/>` (e.g. `RunType="Default" />`) predate the inject script — they were in the original source XMLs. The inject script does NOT introduce them. Fix with `re.sub(r' +/>', '/>', text)` on all Test_Case XMLs. Also fix in `fix_variables_section()` so future inject runs stay clean.
- `USB_20_Run_Base_traffic_with_Bulk_Isoch_Interrupt_Traffic_with_LPM_RTD3.xml` in `Downloads/Galaxy_XMLs` had 6 hardcoded `val="60"` `--timeout` args; fix same as above.

---

## Rule 2 — Validator Bug & File Exclusions

### Validator bug (fixed)
`check_sx_sxiy_residency()` originally searched for `-Capture` in Desc text only. But `-Capture` is an `<arg name="-Capture"/>` element — not a Desc attribute. Fix: search `tree.iter()` for `<arg>` elements with `name="-Capture"`.

### Files correctly excluded from Rule 2
- **`PM_G3_-_Boot_from_G3_to_S5_to_S0_*.xml`** — G3 boot test, not an Sx residency test. No residency check needed.
- **`USB_xHCI_Abrupt_wake_from_S0ix.xml`** — special abrupt wake test, residency check not applicable.

### Files that genuinely need Rule 2 (residency + `-Capture`)
- All `PM_S0ix/S3/S4/S5_+_*ixy_-_*.xml` files
- All `S3/S4/S5_with_USB2_UAOL_*.xml` files (they exercise Sx states so residency check IS appropriate)
- `PM_S4_+_S4ixy_-_Connect_followed_by_Disconnect_*.xml` — has CHECKER in FLOW but missing `-Capture` arg in TESTCONFIG definition

---

## Rule 6 — PM Verification Exclusions

The following files do **NOT** need a PM Verification FLOW block — skip Rule 6 for them:
- `Rapid_system_Warm_Reset.xml`
- `USB_xHCI_Abrupt_wake_from_S0ix.xml`

---

## Rule 1 — Validator Bug (fixed)

`get_test_flow_steps()` originally only returned direct children of `<FLOW Desc="Test">`. Since `Audio` TEST is a flat direct child, a future nested-FLOW structure would miss it. Fix: also recurse into child `<FLOW>` elements inside the Test FLOW when collecting step Desc values.

---

## `ttk3_timeout` in Golden Flow

All `<arg name="--timeout" val="N"/>` entries in `USB_Golden_Flow_ww*.xml` must use `val="$VAR{ttk3_timeout}"`. The golden had 6 hardcoded `val="60"` entries — all replaced. Line 1675 was already correct.

---
- Reviewing/approving Galaxy XML test case commits
- Checking XML standardization against golden flow
- Validating test flow patterns against dictionary rules
- Cross-checking XML structure with peer files
