# Failure Analysis — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only audio failure analysis — NGA test result retrieval, log parsing, WPP decode, failure pattern matching, and sighting cross-reference.
> **Platform**: NVL (Novalake), extensible to all ACE platforms.

---

## Driver Stack (Analysis-Relevant)

| Layer | Binary | Log Source |
|-------|--------|-----------|
| Intel audio bus | `IntcAudioBus.sys` | WPP ETL — codec enum, link init errors |
| Intel SST | `IntcSmartSound.sys` | WPP ETL — DSP FW load, IPC, pipeline errors |
| Intel OED | `IntcOED.sys` | WPP ETL — UAOL, BT offload errors |
| HDA class | `HdAudio.sys` | Windows Event Viewer — HDA controller errors |
| ACX circuit | `IntcAudioCircuit.sys` | WPP ETL — endpoint creation errors |
| Audio service | `AudioSrv.dll` | Windows Event Viewer — audio session errors |

---

## Device Enumeration

### Quick Failure Identification
```cmd
:: Check for errored audio devices
powershell -c "Get-PnpDevice -Class MEDIA | Where-Object {$_.Status -ne 'OK'} | Format-Table Status, FriendlyName, ConfigManagerErrorCode"

:: Check audio service status
sc query AudioSrv
sc query AudioEndpointBuilder

:: Check for recent audio driver crashes
powershell -c "Get-WinEvent -LogName System -MaxEvents 50 | Where-Object {$_.Message -like '*audio*' -or $_.Message -like '*IntcAudio*' -or $_.Message -like '*HdAudio*'} | Format-Table TimeCreated, Message -Wrap"
```

---

## Windows Registry Knobs

### Enable Comprehensive Logging
```
:: Enable WPP verbose on all audio drivers
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
    LogLevel = REG_DWORD 4

HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\
    LogLevel = REG_DWORD 4

HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\
    LogLevel = REG_DWORD 4
```

### Crash Dump for Audio BSODs
```
HKLM\SYSTEM\CurrentControlSet\Control\CrashControl\
    CrashDumpEnabled = REG_DWORD 1   (complete memory dump)
    AlwaysKeepMemoryDump = REG_DWORD 1
```

### Audio Diagnostic Mode
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Audio\
    EnableDiagnosticMode = REG_DWORD 1
```

---

## ETW / WPP Trace Capture

### Comprehensive Audio Failure Trace
```cmd
:: Step 1 — Extract TMF from ALL audio driver PDBs
for %%d in (IntcAudioBus IntcSmartSound IntcOED) do (
  tracepdb.exe -f %SystemRoot%\System32\drivers\%%d.pdb -p C:\Temp\AudioTmf
)

:: Step 2 — Create all-providers trace
logman create trace AudioFailureAll ^
  -p {GUID-IntcAudioBus}     0xFFFFFFFF 0xFF ^
  -p {GUID-IntcSmartSound}   0xFFFFFFFF 0xFF ^
  -p {GUID-IntcOED}          0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-Audio" 0xFFFF 4 ^
  -o C:\Temp\AudioFailure.etl -mode Circular -nb 64 1024

:: Step 3 — Start, reproduce failure, stop
logman start AudioFailureAll
:: ... reproduce ...
logman stop AudioFailureAll

:: Step 4 — Decode
tracefmt C:\Temp\AudioFailure.etl -tmf C:\Temp\AudioTmf -o C:\Temp\AudioFailure.txt
```

### Autologger for Intermittent Failures
```cmd
:: Captures from early boot — essential for failures during init
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioFailCapture" /v Start /t REG_DWORD /d 1 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioFailCapture" /v FileName /t REG_SZ /d "C:\Windows\System32\LogFiles\WMI\AudioFail.etl" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioFailCapture" /v FileMax /t REG_DWORD /d 5 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioFailCapture" /v MaxFileSize /t REG_DWORD /d 128 /f
:: Add provider GUID subkeys, then reboot
```

---

## NGA Failure Log Locations

### On NGA Test Station
| Log | Path | Content |
|-----|------|---------|
| Test result | `<LogsPath>\solar_manager\audio_validation.log` | Test pass/fail output |
| Audio error | `<LogsPath>\solar_manager\audio_error.log` | Audio-specific errors |
| Audio debug | `<LogsPath>\solar_manager\audio_debug.log` | Detailed debug trace |
| WPP ETL | `<LogsPath>\audio\*.etl` | Driver WPP captures |
| Register dump | `<LogsPath>\audio\reg_dump.txt` | BAR0/BAR4 register snapshot |

### Log Retrieval Priority
1. **Axon DataLake** — primary source (via axon skill)
2. **NGA API** — secondary (via nga/results skill)
3. **LogsPath UNC** — direct file share
4. **Station fallback** — `C:\Intel\Logs\` on test station

---

## Failure Pattern Quick Reference

### Pattern Matching Regex
```python
# Quick-scan log for failure category
CRITICAL_PATTERNS = [
    r'DID=0xFFFF',           # ACE disabled
    r'BAR[04]=0x0{8}',       # BAR not allocated
    r'DSP.*panic',           # DSP firmware crash
    r'BSOD|BugCheck',        # System crash
]
HIGH_PATTERNS = [
    r'codec.*not.*found',    # No codec detected
    r'FW.*load.*fail',       # DSP FW load failure
    r'stream.*error',        # Audio stream error
    r'S0ix.*block',          # S0ix blocked by audio
    r'TIMEOUT',              # Any timeout
]
MEDIUM_PATTERNS = [
    r'underrun|overrun',     # Buffer underrun/overrun
    r'jack.*detect.*fail',   # Jack detection issue
    r'intermittent',         # Intermittent failures
]
```

---

## Common Failure Modes

### Failure: NGA audio test returns EXIT_FAIL
1. Download test logs from Axon/NGA (see Log Retrieval Priority)
2. Open `audio_validation.log` → find failure step (pre_test / test / post_test)
3. Pattern match against CRITICAL → HIGH → MEDIUM patterns
4. Route to appropriate sub-skill based on subsystem:
   - `config-checkout/windows.md` for enumeration failures
   - `hda/windows.md` for HDA codec failures
   - `soundwire/windows.md` for SoundWire failures
   - `uaol/windows.md` for UAOL failures
   - `power/windows.md` for PM failures

### Failure: NGA audio test returns EXIT_BLOCKED
1. Check platform state: is audio device present?
2. Check BIOS knobs: audio may be disabled
3. Check test prerequisites: dependencies not met
4. Check station health: platform may need power cycle

### Failure: NGA audio test returns EXIT_ERROR
1. Check test script execution error (Python traceback)
2. Check test infrastructure: network, file paths, tool availability
3. Check if platform is responsive (may be hung)

### Failure: Intermittent audio test failure
1. Enable WPP autologger for continuous capture
2. Run test in loop (50+ iterations) to establish failure rate
3. Check for timing-sensitive race conditions
4. Check thermal throttling during stress (DTS sensors)
5. Cross-reference with known issues: `docs/audio_known_issues.md`

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\failure-analysis\`

Key test categories:
- `driver_health_check\` — all-driver status verification
- `register_snapshot\` — BAR0/BAR4 register dump for analysis
- `log_collection\` — automated WPP + event log + register capture
- `pattern_scan\` — regex-based failure pattern scanner

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\failure-analysis\log_collection
python run_test.py --verbose --output C:\Temp\failure_capture
```
