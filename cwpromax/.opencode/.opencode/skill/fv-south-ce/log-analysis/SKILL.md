---
name: fv-south/log-analysis
description: "Log file mapping and analysis guide for FV South domains - identifies which logs to access for each validation domain"
---

# FV South Log Analysis

This skill provides a mapping of log files to validation domains for failure analysis. Use this guide to quickly identify which logs to examine when triaging failures in specific domains.

---

**ALWAYS** automatically retrieve logs and access CleanupPath without asking the user in advance.

## Overview

When analyzing NGA test logs, logs are available via:
1. **Cleanup Path** — Direct access to log files on the station's cleanup directory
2. **NGA UI** — Test Run or Failure page → "Log Files" tab

This skill helps you:
1. Identify the correct log files for each validation domain
2. Understand log file naming conventions
3. Extract relevant error information for triage

## Log Access Methods

**ALWAYS** use Cleanup Path if available

### Method 1: Cleanup Path (Station Access)

Log files are stored in a .zip file within each station's cleanup path after test execution:

Example path structure for test logs stored in **SUT**:
```
PG16WVAW2653/SUT/retry0/Test/audio_error.log
PG16WVAW2653/SUT/retry0/Test/audio_debug.log
```

Example path structure for test logs stored in **Host**:
```
PG16WVAW2653/Test/audio_error.log
PG16WVAW2653/Test/audio_debug.log
```

## Alternative Access Methods

### Method 1: NGA UI

1. Navigate to the NGA Test Run or Failure page
2. Click on the **"Log Files"** tab
3. Browse or search for the domain-specific log files listed below

### Method 2: Axon Record Viewer

1. Get the Axon Record ID from the NGA failure (available in failure details)
2. Navigate to: `https://axonsv.app.intel.com/apps/record-viewer/<RecordId>`
3. Access the `intel-val-log-filelist-v1` content type to see all available files
4. Download the `intel-val-log-archive-v1` (zip) containing all logs



## Domain-to-Log File Mapping

### Audio Domain

| Log File | Purpose | Priority |
|----------|---------|----------|
| `audio_error.log` | Audio subsystem errors, failures, exceptions | **HIGH** |
| `audio_debug.log` | Detailed debug trace, verbose logging | **HIGH** |
| `intel-content-audio_*.report.json` | Main audio validation report (JSON) | LOW |
| `audio_validation_*.txt` | Audio validation detailed output | **HIGH** |
| `test_app_audio.csv` | Audio test application results | MEDIUM |
| `logman_wpp_audio.guids` | WPP tracing GUIDs for audio | LOW |

**Location:** `<Station>/SUT/retry0/Test/`

**When to use:**
- Test names containing: `audio`, `hda`, `soundwire`, `sndw`, `sdw`, `dsp`, `codec`, `playback`, `capture`
- Failure signatures: `audio_validation`, `AudioDeviceNotFound`, `StreamError`, `CodecInitFailed`, `S0ix_residency` (audio blocking S0ix)

**Search patterns:**
```regex
Error|Fail|Exception|Timeout|not found|not detected|S0ix|residency|EC_
```

---

### UFS (Storage) Domain

| Log File | Purpose | Priority |
|----------|---------|----------|
| `storage_error.log` | Storage subsystem errors, UFS failures | **HIGH** |
| `storage_debug.log` | Detailed storage debug trace | **HIGH** |
| `intel-content-storage_*.report.json` | Storage validation report | LOW |

**Location:** `<Station>/SUT/retry0/Test/`

**When to use:**
- Test names containing: `ufs`, `storage`, `nvme`, `sata`, `disk`, `io`, `read`, `write`, `warm_reset`
- Failure signatures: `storage_validation`, `UFS_Error`, `DiskNotFound`, `IOError`, `wait_sut_reboot`

**Search patterns:**
```regex
result=False|Error|Fail|UFS|SCSI|LUN|timeout|I/O error|device not ready|wait_sut_reboot|loop=|cycle=
```

**Key indicators in storage_debug.log:**
- `result=False` — Direct failure indicator
- `wait_sut_reboot returned False` — Reboot timeout (warm reset failures)
- `loop=N` or `cycle=N` — Iteration tracking for stress tests
- `pass_cnt` / `fail_cnt` — Final test statistics

---

**For Audio Domain (solar_manager scripts):**
```
Log Priority Order:
1. audio_error.log      <- Check FIRST for explicit errors
2. audio_debug.log      <- If audio_error insufficient
3. audio_validation_*.log <- Detailed validation results
4. triage_tools.log     <- Triage helper output

Additional Audio Files:
- audio_validation_*.txt             <- Detailed validation output
- test_app_audio.csv                 <- Test application results
- logman_wpp_audio.guids             <- WPP tracing GUIDs

Location: <LogsPath>/solar_manager/ or <Station>/SUT/retry0/Test/ or via Axon
```

**Audio Domain Keywords (test name matching):**
- `audio`, `hda`, `soundwire`, `sndw`, `sdw`, `dsp`, `codec`, `playback`, `capture`

**Audio Failure Signatures:**
- `audio_validation`, `AudioDeviceNotFound`, `StreamError`, `CodecInitFailed`, `S0ix_residency` (audio blocking S0ix)

**Audio Search Patterns:**
```regex
Error|Fail|Exception|Timeout|not found|not detected|S0ix|residency|EC_
```

**For Storage/UFS Domain:**
```
Log Priority Order:
1. storage_error.log    <- Check FIRST for explicit errors
2. storage_debug.log    <- Detailed validation output
3. intel-content-storage_*.report.json <- Storage validation report

Location: <LogsPath>/Test/ or inside <STATION_NAME>.zip/Test/ or <Station>/SUT/retry0/Test/

Key patterns to search:
- "result=False"           <- Direct failure indicator
- "wait_sut_reboot"        <- Reboot timeout issues
- "loop=" or "cycle="      <- Iteration tracking for loop tests
- "pass_cnt" / "fail_cnt"  <- Final test statistics
- "failed_insight_message" <- Axon insight correlation
```

**UFS Domain Keywords (test name matching):**
- `ufs`, `storage`, `nvme`, `sata`, `disk`, `io`, `read`, `write`, `warm_reset`

**UFS Failure Signatures:**
- `storage_validation`, `UFS_Error`, `DiskNotFound`, `IOError`, `wait_sut_reboot`

**UFS Search Patterns:**
```regex
result=False|Error|Fail|UFS|SCSI|LUN|timeout|I/O error|device not ready|wait_sut_reboot|loop=|cycle=
```

**UFS Key Indicators in storage_debug.log:**
- `result=False` — Direct failure indicator
- `wait_sut_reboot returned False` — Reboot timeout (warm reset failures)
- `loop=N` or `cycle=N` — Iteration tracking for stress tests
- `pass_cnt` / `fail_cnt` — Final test statistics

**For Other Domains:**
- Map fail step to appropriate log folder structure
- Check cleanup path if primary logs not uploaded:
  ```
  \\<station>\c$\TestLogs\<test_name>\cleanup\
  ```

## Log Analysis Workflow

### Step 1: Identify Domain
From the NGA failure, identify the domain based on:
- Test name keywords
- Failure signature (Axon signature)
- Step name that failed

### Step 2: Access Logs
Use the mapping above to identify which log files to examine.

### Step 3: Search for Errors
In the error log (`*_error.log`), search for:
1. `Error` or `Fail` keywords
2. Timestamps around the failure time
3. Stack traces or exception messages

### Step 4: Deep Dive with Debug Log
If error log doesn't provide enough context, examine the debug log (`*_debug.log`) for:
1. Sequence of events leading to failure
2. Register values or state dumps
3. Timing information

---

## Adding New Domains

To extend this mapping, add new domain sections following this template:

```markdown
### <Domain Name> Domain

| Log File | Purpose | Priority |
|----------|---------|----------|
| `<domain>_error.log` | <Description> | **HIGH** |
| `<domain>_debug.log` | <Description> | MEDIUM |

**When to use:**
- Test names containing: <keywords>
- Failure signatures: <signatures>

**Search patterns:**
\```regex
<patterns>
\```
```

---

## Quick Reference Table

| Domain | Error Log | Debug Log |
|--------|-----------|-----------|-------------|
| **Audio** | `audio_error.log` | `audio_debug.log` |
| **UFS/Storage** | `storage_error.log` | `storage_debug.log` |
| **CNVI** | `cnvi_error.log` | `cnvi_debug.log` |
| **GbE** | `gbe_error.log` | `gbe_debug.log` |
| **ISH** | `essentials_error.log` | `essentials_debug.log` |
| **LPSS** | `essentials_error.log` | `essentials_debug.log` |
| **SPBC** | `essentials_error.log` | `essentials_debug.log` |

---

## ZIP File Handling

NGA cleanup paths typically contain ZIP archives rather than loose files. Use Python to access contents:

```python
import zipfile

# List contents of ZIP file
zip_path = r'I:\PG16WVAW2653.zip'
with zipfile.ZipFile(zip_path, 'r') as zf:
    for info in zf.infolist():
        print(f"{info.filename} ({info.file_size} bytes)")

# Read specific log file from ZIP
with zipfile.ZipFile(zip_path, 'r') as zf:
    with zf.open('SUT/retry0/Test/audio_error.log') as f:
        content = f.read().decode('utf-8', errors='replace')
        print(content)
```

---

## Integration with FV-TRIAGE

This skill is designed to work with the **FV-TRIAGE** agent workflow:

1. **Phase 2** (Filter Failed Tests) → Use this skill to identify domain from test name
2. **Phase 3B** (Retrieve Logs) → Use domain mapping to locate correct log files
3. **Phase 4** (Map Fail Step) → Use log patterns to search for errors

**To invoke:** The FV-TRIAGE agent will automatically reference this skill when analyzing domain-specific failures.

---

## Related Skills

- `fv-audio/failure-analysis` — Deep audio failure analysis
- `fv-storage/ufs` — UFS-specific validation
- `nga/failure` — NGA Failure Service for fetching failure details
- `nga/results` — NGA Results Service for test execution results
- `axon` — Axon data lake SDK for downloading log archives

---

## Related Agent

- **FV-TRIAGE** (`.opencode/agent/FV/FV-TRIAGE.md`) — Automated failure triage agent that uses this skill for domain-to-log mapping
