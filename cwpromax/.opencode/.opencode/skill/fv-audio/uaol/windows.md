# UAOL — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only USB Audio Offload (UAOL) validation — ACE↔xHCI integration, isochronous stream offload, FIFO timing, behind-hub support, and hot plug.
> **Platform**: NVL (ACE 4.x), PTL (ACE 3.0). **Not supported**: LNL (ACE 2.x), MTL/ARL (ACE 1.5).

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Intel OED | `IntcOED.sys` | Intel Offload Engine Driver — UAOL engine management |
| Intel SST | `IntcSmartSound.sys` | DSP pipeline for UAOL audio processing |
| xHCI host | `usbxhci.sys` | Microsoft xHCI driver — USB host controller |
| USB Audio 2.0 | `usbaudio2.sys` | Microsoft USB Audio Class 2.0 driver |
| Intel audio bus | `IntcAudioBus.sys` | HDA bus — UAOL handshake with ACE |

---

## Device Enumeration

### Verify UAOL Capability
```cmd
:: Check xHCI controller
devcon hwids "PCI\VEN_8086&DEV_*" | findstr -i "xhci\|usb"

:: Check USB audio device connected
powershell -c "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*USB Audio*'} | Format-Table Status, FriendlyName, InstanceId"

:: Check OED driver (handles UAOL)
sc query IntcOED

:: Check ACE version supports UAOL (ACE 3.x+ required)
:: NVL = ACE 4.x ✓, PTL = ACE 3.0 ✓, LNL/MTL/ARL = ✗
devcon hwids "PCI\VEN_8086&DEV_D328*"  :: NVL PCD-H (UAOL supported)
```

### Expected UAOL Topology
```
USB Audio Device ←→ xHCI Host ←→ UAOL Engine (ACE) ←→ Audio Endpoint
  usbaudio2.sys      usbxhci.sys    IntcOED.sys         IntcSmartSound.sys
```

---

## Windows Registry Knobs

### UAOL Engine Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `UaolEnable` | REG_DWORD | 1=enable UAOL offload, 0=disable (host-only USB audio) |
| `UaolBehindHub` | REG_DWORD | 1=enable behind-hub UAOL (ACE 4.x only) |
| `LogLevel` | REG_DWORD | WPP verbosity (0=off, 4=verbose) |

### UAOL FIFO Tuning
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcOED\Parameters\UAOL\
```
| Value | Type | Purpose |
|-------|------|---------|
| `FifoWatermark` | REG_DWORD | FIFO fill level trigger (affects latency vs glitch) |
| `IsoPacketCount` | REG_DWORD | Number of isochronous packets per URB |
| `MaxLatencyMs` | REG_DWORD | Maximum acceptable audio latency in ms |

---

## ETW / WPP Trace Capture

### Capture UAOL Trace
```cmd
:: Extract WPP GUIDs from OED driver
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcOED.pdb -p C:\Temp\OedTmf

:: Create combined UAOL + USB trace
logman create trace UaolTrace ^
  -p {GUID-IntcOED}     0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-USB-USBHUB3" 0xFFFF 4 ^
  -p "Microsoft-Windows-USB-USBXHCI" 0xFFFF 4 ^
  -o C:\Temp\Uaol.etl -mode Circular -nb 32 512
logman start UaolTrace

:: Connect USB audio device, play audio, disconnect, then stop:
logman stop UaolTrace
tracefmt C:\Temp\Uaol.etl -tmf C:\Temp\OedTmf -o C:\Temp\Uaol.txt
```

### USB ETL Analyzer (Cross-Domain Debug)
```cmd
:: For deep xHCI-side analysis, use USB ETL Analyzer:
:: 1. Extract USB WPP symbols
tracepdb.exe -f %SystemRoot%\System32\drivers\usbxhci.pdb -p C:\Temp\UsbTmf

:: 2. Use standalone analyzer (see fv-usb/debug/etl-decode skill)
python usb_debug_standalone_v8.py --src C:\Temp\Uaol.etl
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `UAOL_OFFLOAD_START` | UAOL engine accepted USB audio offload |
| `UAOL_OFFLOAD_STOP` | UAOL offload teardown |
| `UAOL_FIFO_UNDERRUN` | ACE↔xHCI FIFO underrun — timing issue |
| `UAOL_FIFO_OVERRUN` | ACE↔xHCI FIFO overrun — data not consumed |
| `ISO_TRANSFER` | Isochronous USB transfer event |
| `PORTSC_CHANGE` | xHCI port status change (connect/disconnect) |
| `BEHIND_HUB` | Device behind USB hub detection |

---

## Common Failure Modes

### Failure: USB audio not offloaded (uses host CPU)
1. Check `UaolEnable=1` in `IntcOED\Parameters`
2. Check platform supports UAOL: ACE 3.x+ required (NVL/PTL only)
3. Check `IntcOED` service running: `sc query IntcOED`
4. Check BIOS: UAOL must be enabled in Audio DSP Features
5. WPP trace: search for `UAOL_OFFLOAD_START` — if absent, offload rejected

### Failure: UAOL FIFO underrun/overrun (audio glitch)
1. Check ACE↔xHCI clock coherency — must share XTAL reference
2. Check FIFO watermark setting — too low = underrun, too high = latency
3. Check USB bandwidth: other USB devices may starve ISO transfers
4. WPP trace: `UAOL_FIFO_UNDERRUN` or `UAOL_FIFO_OVERRUN` with timestamp
5. Known issue: **BUG-004** PSF glitch on MTL — fixed PTL+

### Failure: Behind-hub USB audio not offloaded
1. Behind-hub UAOL requires ACE 4.x (NVL only)
2. Check `UaolBehindHub=1` registry setting
3. Known issue: **BUG-005** behind-hub broken on MTL — no workaround
4. WPP trace: search for `BEHIND_HUB` + `REJECT` or `UNSUPPORTED`

### Failure: USB audio device disconnect during offload
1. Check UAOL stream teardown completed cleanly
2. Quick replug can cause state machine race — add 2s delay between unplug/replug
3. WPP trace: `UAOL_OFFLOAD_STOP` should precede `PORTSC_CHANGE` disconnect
4. Check ACE FIFO reset after teardown

### Failure: UAOL breaks after S0ix cycle
1. Both xHCI and ACE must be in D0 for UAOL
2. After S0ix exit: UAOL re-establishment sequence runs
3. WPP trace: search for `D0_RESUME` → `UAOL_OFFLOAD_START` after wake
4. Check xHCI PORTSC.PLS = U0 (active) after resume

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\uaol\`

Key test categories:
- `uaol_offload\` — verify UAOL offload start/stop with USB headset
- `uaol_playback_capture\` — PCM stream through UAOL path
- `uaol_behind_hub\` — device behind USB hub offload (NVL only)
- `uaol_hotplug\` — USB audio plug/unplug during offload
- `uaol_power\` — D3/S0ix transitions during UAOL stream
- `uaol_fifo_stress\` — FIFO stress under concurrent USB traffic

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\uaol\uaol_offload
python run_test.py --verbose
```
