# DSP — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only. All test content at `C:\validation\windows-test-content\audio\dsp\`.
> **Platform**: NVL (Novalake) ACE 4.x — 4 HiFi5 HP cores + 1 ULP core (PCD-H), 2 HP + 1 ULP (PCH-S).

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| ACE DSP driver | `IntcSST2.sys` | Intel Smart Sound Technology 2 — main DSP host driver |
| ACE bus driver | `IntcAudioBus.sys` | Exposes DSP-processed endpoints to Windows audio stack |
| ACX circuit driver | `IntcAudioCircuit.sys` | Windows 11 ACX extension for DSP topology |
| DSP firmware | `IntcSST2FW.bin` (or path in INF) | Loaded by `IntcSST2.sys` from `%SystemRoot%\System32\drivers\` |
| Topology blob | ACPI UCM or INF `AddReg` | Defines DSP pipeline connections (audio graph) |

**Service name**: `IntcSST2`
**Device instance path**: `PCI\VEN_8086&DEV_77xx` (same PCI function as ACE, selected by INF match)

---

## DSP Firmware

### Firmware Location
```
%SystemRoot%\System32\drivers\IntcSST2FW.bin   :: Primary firmware image
%SystemRoot%\System32\drivers\IntcSST2FW2.bin  :: Secondary/ULP firmware (if applicable)
```
> Exact filename depends on INF `AddReg` entries. Check:
> ```cmd
> reg query "HKLM\SYSTEM\CurrentControlSet\Services\IntcSST2\Parameters" /v FirmwareName
> ```

### Firmware Version
```cmd
:: Via Device Manager → Driver Details → IntcSST2.sys properties
:: Or query registry after driver loads:
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E96C-E325-11CE-BFC1-08002BE10318}\0000" /v FirmwareVersion

:: PythonSV (with probe, DSP running):
soc.ace.dsp.ipc.fw_version_major
soc.ace.dsp.ipc.fw_version_minor
```

---

## Windows Registry Knobs

### IntcSST2 Driver Parameters
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSST2\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `FirmwareName` | REG_SZ | Override FW binary filename |
| `FirmwarePath` | REG_EXPAND_SZ | Override FW binary directory path |
| `IpcTimeout` | REG_DWORD | IPC reply timeout in ms (default: 500). Increase to 2000 for debug |
| `LogLevel` | REG_DWORD | WPP verbosity: 0=off, 1=error, 2=warn, 3=info, 4=verbose |
| `DspCoreCount` | REG_DWORD | Restrict active HP core count (debug) |
| `DisableDsp` | REG_DWORD | 1=bypass DSP, use HDA fallback path (disables offload) |
| `SramPowerGate` | REG_DWORD | 0=disable SRAM power gating (debug stability) |

### Topology Overrides
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSST2\TopologyParams\
```
| Value | Type | Purpose |
|-------|------|---------|
| `PipelineCount` | REG_DWORD | Active pipeline count override |
| `OffloadEnable` | REG_DWORD | 1=enable audio offload to DSP (default: 1) |
| `KWSEnable` | REG_DWORD | 1=enable keyword spotter (WoV) pipeline |

---

## ETW / WPP Trace Capture

### Capture IntcSST2 DSP Driver Trace
```cmd
:: Step 1 – Extract WPP GUID from PDB
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcSST2.pdb -p C:\Temp\SstTmf

:: Step 2 – Create and start trace
logman create trace DspTrace ^
  -p {WPP-GUID-FROM-TRACEPDB} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\Dsp.etl -mode Circular -nb 32 512
logman start DspTrace

:: Step 3 – Reproduce (start audio stream, trigger FW load, etc.)

:: Step 4 – Stop and decode
logman stop DspTrace
tracefmt C:\Temp\Dsp.etl -tmf C:\Temp\SstTmf -o C:\Temp\Dsp_decoded.txt
```

### IPC Trace Focus Points
When decoding `Dsp_decoded.txt`, search for:
- `FW_READY` — DSP firmware has booted and is ready for IPC
- `INIT_INSTANCE` / `BIND` — pipeline setup messages
- `IPC_TIMEOUT` — DSP not responding within `IpcTimeout` ms
- `IPC_ERROR` — DSP replied with error code
- `ROM_CONTROL` — early boot ROM control messages

### Windows Audio Offload ETW
```cmd
:: Audio offload uses PortCls + KS offload path
logman create trace AudioOffload ^
  -p "Microsoft-Windows-Audio" 0xFFFF 5 ^
  -p "Microsoft-Windows-Kernel-Audio" 0xFFFF 5 ^
  -o C:\Temp\AudioOffload.etl
logman start AudioOffload
:: ... reproduce offload pipeline issue ...
logman stop AudioOffload
```

---

## DSP State Debug (Windows-side)

### Service State Checks
```cmd
:: Check driver service state
sc query IntcSST2

:: Check if DSP FW was loaded (event log)
wevtutil qe System /q:"*[System[Provider[@Name='Service Control Manager'] and (EventID=7036)]]" /f:text | findstr -i "IntcSST2"

:: Check for DSP error events
wevtutil qe Application /q:"*[System[Provider[@Name='IntcSST2']]]" /f:text /c:20
```

### DSP Core State (PythonSV — requires probe)
```python
# Cores must have GPROCEN=1 before BAR2 is accessible
soc.ace.dsp.ppctl.gprocen       # must be 1 for BAR2 access

# Per-core state (NVL PCD-H: cores 0-4)
soc.ace.dsp.adspcs.cpa0         # Core 0 (ULP) power active
soc.ace.dsp.adspcs.cpa1         # Core 1 (HP) power active
soc.ace.dsp.adspcs.spa0         # Core 0 stall
soc.ace.dsp.adspcs.crst0        # Core 0 reset (1=in reset)

# IPC doorbell
soc.ace.dsp.hipcidr.busy        # 1 = host-to-DSP IPC pending (not yet acked)
soc.ace.dsp.hipcida.done        # 1 = DSP-to-host IPC pending
```

---

## Common Windows DSP Failure Modes

### Failure: DSP firmware load timeout
**Symptom**: `IntcSST2` service starts but DSP stays non-functional; WPP trace shows `FW_READY` never received

1. Check `IpcTimeout` — increase to 5000 ms for slow silicon
2. Verify firmware file exists: `dir %SystemRoot%\System32\drivers\IntcSST2FW*`
3. Check `GPROCEN` (BAR0+0x1004 bit30) via PythonSV — must be 1 for DSP to run
4. Check SRAM power gate: `SramPowerGate=0` registry override to keep SRAM always-on
5. Check for ACPI `_RST` DSP reset conflict — may need BIOS update

### Failure: IPC timeout during stream setup
**Symptom**: Audio stream starts then fails; WPP trace shows `IPC_TIMEOUT` on `INIT_INSTANCE` or `BIND`

1. Increase `IpcTimeout` to 2000 in registry, reboot, retry
2. Check if other DSP cores are running: `adspcs.cpa1..4` should be 1
3. Check DSP workload: too many simultaneous pipelines may exceed capacity
4. Set `DspCoreCount=1` to restrict to single HP core (reduces parallelism, improves stability)
5. Capture WPP ETL + DSP FW log (via IMR dump — requires probe, 3+ hours via JTAG on NVL)

### Failure: Audio offload not working (offload falls back to host)
**Symptom**: Task Manager shows high CPU for audio; offload endpoint present but not used

1. Verify `OffloadEnable=1` in `TopologyParams`
2. Check KS offload driver: `PortCls.sys` must support offload (Win 8.1+)
3. Check if player uses WASAPI exclusive mode (offload requires shared mode)
4. Check Event Log for `Microsoft-Windows-Audio` source 4xxx errors

### Failure: WoV (Wake-on-Voice) keyword not detected
**Symptom**: Voice wake fails in S0ix/standby

1. Check `KWSEnable=1` in `TopologyParams`
2. Check DSP is in D0i3 (not D3) — D3 kills DSP context, WoV pipeline must be in D0i3
3. Verify DMIC clock is CRO-sourced during WoV: `DSPWCCTL.DWCS = 10b` (CRO)
4. Check Windows `LockScreenAppHost` has microphone permission

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\dsp\`

Key test categories:
- `dsp_fw_load\` — firmware load time, FW_READY latency
- `dsp_ipc_basic\` — IPC round-trip, INIT_INSTANCE/BIND/UNBIND
- `dsp_pipeline_playback\` — DSP-routed PCM playback (offload path)
- `dsp_pipeline_capture\` — DSP-routed PCM capture (DMIC through DSP)
- `dsp_power_d0i3\` — DSP D0i3 entry/exit with active WoV pipeline
- `dsp_kws\` — keyword spotter pipeline, WoV trigger verification

Run a specific test manually:
```cmd
cd C:\validation\windows-test-content\audio\dsp\dsp_fw_load
python run_test.py --verbose --timeout 5000
```
