# BT Audio Offload — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only BT Audio Offload (SSP/I2S) validation — HFP (SCO/eSCO) voice offload, A2DP music offload, BCLK configuration, and CNVi integration.
> **Platform**: NVL (Novalake), extensible to PTL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Intel OED | `IntcOED.sys` | Intel Offload Engine Driver — manages SSP/I2S offload path |
| BT HFP driver | `BthHFPAudio.sys` | Microsoft BT HFP audio driver — SCO/eSCO voice |
| BT A2DP driver | `BthA2dp.sys` | Microsoft BT A2DP audio driver — stereo music |
| Intel BT | `ibtusb.sys` | Intel BT controller driver (CNVi) |
| Intel audio bus | `IntcAudioBus.sys` | HDA bus — BT offload SSP configuration |

---

## Device Enumeration

### Verify BT Audio Offload Path
```cmd
:: Check BT controller
devcon hwids "USB\VID_8087*" | findstr -i "bluetooth"

:: Check BT audio devices
powershell -c "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Bluetooth*Audio*'} | Format-Table Status, FriendlyName"

:: Check OED driver loaded
sc query IntcOED

:: Check SSP device instances
devcon hwids "ACPI\INT0008*"   :: Intel SSP ACPI node (platform-dependent)
```

### Expected BT Offload Topology
```
BT Controller (CNVi) ←→ SSP/I2S Port ←→ ACE DSP ←→ Audio Endpoint
  ibtusb.sys              IntcOED.sys    IntcSmartSound.sys
```

---

## Windows Registry Knobs

### BT Audio Offload Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `LogLevel` | REG_DWORD | WPP verbosity (0=off, 4=verbose) |
| `BtOffloadEnable` | REG_DWORD | 1=enable BT audio offload, 0=disable (fallback to host) |
| `SspPortIndex` | REG_DWORD | SSP port number for BT offload (platform-specific) |

### BT HFP Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\BthHFPAudio\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `DisableWideBand` | REG_DWORD | 1=force narrowband SCO (8 kHz) for debug |
| `EscoMode` | REG_DWORD | 0=SCO, 1=eSCO (transparent data) |

### BCLK Configuration (SSP/I2S)
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\SSP\
```
| Value | Type | Purpose |
|-------|------|---------|
| `BclkFrequency` | REG_DWORD | I2S BCLK frequency in Hz (e.g. 3072000 for 3.072 MHz) |
| `SampleRate` | REG_DWORD | Audio sample rate (8000, 16000, 48000) |
| `BitDepth` | REG_DWORD | Sample bit depth (16, 24) |

---

## ETW / WPP Trace Capture

### Capture BT Offload Trace
```cmd
:: Extract WPP GUIDs
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcOED.pdb -p C:\Temp\OedTmf

:: Start trace
logman create trace BtOffloadTrace ^
  -p {GUID-IntcOED} 0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-Bluetooth-BthLEPrepairing" 0xFFFF 4 ^
  -o C:\Temp\BtOffload.etl -mode Circular -nb 16 256
logman start BtOffloadTrace

:: Pair BT headset, start audio playback/call, then stop:
logman stop BtOffloadTrace
tracefmt C:\Temp\BtOffload.etl -tmf C:\Temp\OedTmf -o C:\Temp\BtOffload.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `SSP_START` / `SSP_STOP` | SSP/I2S port lifecycle |
| `BT_CONNECT` / `BT_DISCONNECT` | BT link state change |
| `HFP_SCO` / `HFP_ESCO` | Voice call offload path |
| `A2DP_STREAM` | Music streaming offload |
| `BCLK=` | I2S bit clock frequency configured |
| `OFFLOAD_START` / `OFFLOAD_STOP` | Offload engine activation |

---

## Common Failure Modes

### Failure: BT audio not offloaded (uses host CPU instead)
1. Check `BtOffloadEnable=1` in `IntcOED\Parameters`
2. Check `IntcOED` service is running: `sc query IntcOED`
3. Check BIOS: BT offload SSP port must be enabled
4. Check SSP port ACPI `_CRS` — must match expected port index
5. WPP trace: search for `OFFLOAD_START` — if absent, fallback to host path

### Failure: Voice call audio (HFP) distorted
1. Check BCLK frequency: SSP BCLK must match BT controller expectation
2. Check eSCO mode: narrowband (8 kHz) vs wideband (16 kHz)
3. Check I2S format: bit depth, channel count, frame sync polarity
4. WPP trace: search for `BCLK` and `FORMAT` mismatch indicators

### Failure: A2DP streaming drops out
1. Check BT link quality: `netsh bluetooth show devices`
2. Check SSP FIFO status — underrun indicates clock mismatch
3. Check if SSP/DSP power state is interrupting stream (D3 transition)
4. Increase BT audio buffer size if available

### Failure: BT offload breaks after S0ix cycle
1. Check SSP port re-initialization after resume
2. Check BT controller state after wake: `ibtusb.sys` must re-establish link
3. WPP trace: search for `SSP_START` after `D0_RESUME`

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\bt-offload\`

Key test categories:
- `bt_hfp_offload\` — HFP SCO/eSCO voice call through SSP
- `bt_a2dp_offload\` — A2DP stereo music through SSP
- `bt_offload_power\` — D3/S0ix transitions during BT audio
- `bt_reconnect\` — BT disconnect/reconnect while streaming

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\bt-offload\bt_hfp_offload
python run_test.py --verbose
```
