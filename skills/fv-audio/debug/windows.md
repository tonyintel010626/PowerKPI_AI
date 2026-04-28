# Debug — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only audio debug tools, crash dump analysis, WPP tracing, and systematic triage methodology.
> **Platform**: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL

---

## Driver Stack (Debug-Relevant)

| Layer | Binary | Debug Role |
|-------|--------|-----------|
| Intel audio bus | `IntcAudioBus.sys` | HDA init, codec enum, link management — first place to check |
| Intel SST | `IntcSmartSound.sys` | DSP FW load, IPC, pipeline — DSP crash analysis |
| Intel OED | `IntcOED.sys` | Offload Engine Driver — UAOL, BT offload |
| HDA class | `HdAudio.sys` | Microsoft HDA bus — codec function groups |
| ACX circuit | `IntcAudioCircuit.sys` | ACX topology, SDCA — endpoint creation |
| SoundWire bus | `SdwBus.sys` | SoundWire enumeration — slave detection |
| Realtek codec | `RTKVHD64.sys` | Codec driver — verb/register failures |

---

## Device Enumeration

### Quick Audio Health Check
```cmd
:: Check all audio devices and their status
devcon status =MEDIA

:: Check for yellow-bang (error code 10, 28, 43, etc.)
powershell -c "Get-PnpDevice -Class MEDIA | Format-Table Status, FriendlyName, InstanceId -AutoSize"

:: List audio driver services
sc query IntcAudioBus
sc query IntcSmartSound
sc query IntcOED
sc query SdwBus
```

### Check Audio Device Error Codes
```cmd
:: PowerShell: get device error codes
powershell -c "Get-PnpDevice -Class MEDIA | Where-Object {$_.Status -ne 'OK'} | Select-Object Status, FriendlyName, ConfigManagerErrorCode"
```

| Error Code | Meaning | Debug Action |
|-----------|---------|-------------|
| 10 | Device cannot start | Check WPP trace for init failure; check BIOS knobs |
| 28 | Driver not installed | Run `pnputil /scan-devices`; reinstall INF |
| 43 | Device stopped (driver reported problem) | Check crash dump; WPP trace for driver assertion |
| 45 | Device not connected | Check PCI BDF; ACE may be disabled or powered off |

---

## Windows Registry Knobs (Debug)

### Enable Verbose Logging
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
    LogLevel = REG_DWORD 4   (0=off, 4=verbose)

HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\
    LogLevel = REG_DWORD 4

HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\
    LogLevel = REG_DWORD 4
```

### Crash Dump Configuration
```
HKLM\SYSTEM\CurrentControlSet\Control\CrashControl\
    CrashDumpEnabled = REG_DWORD 1   (1=Complete, 2=Kernel, 3=Small)
    AlwaysKeepMemoryDump = REG_DWORD 1
    AutoReboot = REG_DWORD 0   (disable auto-reboot to inspect BSOD)
```

### Audio Policy Debug
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Audio\
    DisableProtectedAudioDG = REG_DWORD 1   (disable audio DRM for debug)
```

---

## ETW / WPP Trace Capture

### Comprehensive Audio Debug Trace
```cmd
:: Step 1 — Extract TMF from all audio driver PDBs
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb     -p C:\Temp\Tmf
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcSmartSound.pdb   -p C:\Temp\Tmf
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcOED.pdb          -p C:\Temp\Tmf

:: Step 2 — Create combined trace session
logman create trace AudioDebugAll ^
  -p {GUID-IntcAudioBus}    0xFFFFFFFF 0xFF ^
  -p {GUID-IntcSmartSound}  0xFFFFFFFF 0xFF ^
  -p {GUID-IntcOED}         0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-Audio" 0xFFFF 4 ^
  -o C:\Temp\AudioDebug.etl -mode Circular -nb 32 512

:: Step 3 — Start, reproduce, stop
logman start AudioDebugAll
:: ... reproduce failure ...
logman stop AudioDebugAll

:: Step 4 — Decode
tracefmt C:\Temp\AudioDebug.etl -tmf C:\Temp\Tmf -o C:\Temp\AudioDebug.txt
```

### WPP Autologger (Captures from Early Boot)
```cmd
:: Create autologger that starts before user login
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioBootTrace" /v Start /t REG_DWORD /d 1 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioBootTrace" /v FileName /t REG_SZ /d "C:\Windows\System32\LogFiles\WMI\AudioBoot.etl" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioBootTrace" /v FileMax /t REG_DWORD /d 3 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\AudioBootTrace" /v MaxFileSize /t REG_DWORD /d 64 /f
:: Add provider GUIDs as subkeys (from tracepdb output)
:: Reboot to start capture
```

### Key WPP Patterns to Search
| Pattern | Subsystem | Meaning |
|---------|-----------|---------|
| `ERROR` / `FAIL` | Any | Primary error indicator |
| `TIMEOUT` | Any | Operation exceeded time limit |
| `IPC_SEND` / `IPC_RECV` | DSP | Host ↔ DSP IPC messaging |
| `FW_LOAD` / `FW_BOOT` | DSP | Firmware load sequence |
| `D3_ENTER` / `D0_RESUME` | Power | D-state transitions |
| `STREAM_START` / `STREAM_STOP` | HDA/SDW | DMA stream lifecycle |
| `CODEC_VERB` | HDA | HDA verb send/receive |
| `SDW_PING` / `SDW_ENUM` | SoundWire | Bus enumeration |

---

## Crash Dump Analysis (WinDbg)

### Audio BSOD Triage
```
:: Open crash dump
windbg -z C:\Windows\MEMORY.DMP

:: Automated analysis
!analyze -v

:: Check if audio driver is in the stack
.ecxr
k
:: Look for IntcAudioBus.sys, IntcSmartSound.sys, HdAudio.sys, IntcOED.sys

:: Search for audio-related strings in memory
s -a 0 L?0x7FFFFFFF "IntcAudioBus"
s -a 0 L?0x7FFFFFFF "IntcSmartSound"

:: Check WHEA records for hardware errors
!errrec
```

### Common Audio-Related Bugchecks
| Bugcheck | Audio Context | Debug Focus |
|----------|--------------|-------------|
| 0x9F `DRIVER_POWER_STATE_FAILURE` | ACE D3 entry/exit timeout | Check PMCSR, active streams, pending IPC |
| 0xD1 `DRIVER_IRQL_NOT_LESS_OR_EQUAL` | Audio driver paged memory access | Stack trace → faulting driver + offset |
| 0x1E `KMODE_EXCEPTION_NOT_HANDLED` | Driver assertion or null deref | Stack trace → exception address |
| 0x116 `VIDEO_TDR_FAILURE` | Display Audio (iDisp) during GPU TDR | Check GPU state + iDisp codec |

---

## Common Failure Modes

### Failure: Audio device yellow-bang after boot
1. Check error code via `Get-PnpDevice` — code 10 vs 28 vs 43
2. Enable WPP autologger → reboot → collect ETL → decode
3. Search decoded trace for first `ERROR` or `FAIL` entry
4. Common root causes: BIOS knob mismatch, FW load failure, codec timeout

### Failure: Audio works initially, then stops
1. Check D3/resume cycle: was there a sleep/wake transition?
2. Check Event Viewer → System → filter by Source=`IntcAudioBus` or `IntcSmartSound`
3. Capture WPP during the failure window
4. Check if MMCSS (Multimedia Class Scheduler Service) is running: `sc query MMCSS`

### Failure: BSOD during audio playback
1. Collect `MEMORY.DMP` + minidump from `C:\Windows\Minidump\`
2. WinDbg `!analyze -v` → identify faulting module
3. If audio driver in stack → file sighting with dump + WPP ETL
4. If MCA present (`!errrec` shows WHEA) → route to MCA debug

### Failure: No audio endpoints visible in Sound Settings
1. Check Device Manager for audio devices (expand "Sound, Video and Game Controllers")
2. Run `devcon status =MEDIA` → check for disabled/errored devices
3. Check `IntcAudioCircuit.sys` load: `sc query IntcAudioCircuit`
4. Check ACPI `_DSD` for audio endpoint definitions

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\debug\`

Key test categories:
- `driver_health_check\` — verify all audio driver services loaded and running
- `register_dump\` — dump BAR0/BAR4 registers for offline analysis
- `wpp_autologger_capture\` — automated WPP collection during test

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\debug\driver_health_check
python run_test.py --verbose
```
