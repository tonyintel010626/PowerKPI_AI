# Display Audio — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only iDisp (HDMI/DisplayPort) audio validation, hot plug detect, ELD readback, and MST topology.
> **Platform**: NVL (Novalake), extensible to PTL, LNL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Intel graphics | `igfx*.sys` | Intel GPU driver — co-manages iDisp codec, HPD signals |
| HDA class | `HdAudio.sys` | Microsoft HDA bus — enumerates iDisp function group |
| Intel audio bus | `IntcAudioBus.sys` | Intel HDA bus filter — iDisp link management |
| Intel HD Audio | `IntcHdAudBusINT.inf` | INF for Intel HD Audio controller including iDisp |

---

## Device Enumeration

### Verify iDisp Codec
```cmd
:: iDisp codec appears as HDAUDIO function group
devcon hwids "HDAUDIO\FUNC_01&VEN_8086&DEV_2816*"

:: Check all display audio endpoints
powershell -c "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*HDMI*' -or $_.FriendlyName -like '*DisplayPort*'} | Format-Table Status, FriendlyName"

:: Check Intel graphics device (co-dependency)
devcon hwids "PCI\VEN_8086&DEV_*" | findstr -i "graphics\|display\|VGA"
```

### Expected Device IDs (NVL)
- iDisp codec: `HDAUDIO\FUNC_01&VEN_8086&DEV_2816` (Intel HD Audio iDisp)
- Intel graphics: `PCI\VEN_8086&DEV_...` (GPU — depends on SKU)

> **NVL PCD-H**: iDisp uses SoundWire Seg0 alt path (not HDA link). Check SoundWire link state if iDisp codec is missing.

---

## Windows Registry Knobs

### Display Audio Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `DisableHdaLink` | REG_DWORD | 1=disable HDA link — **breaks iDisp on HDA-path platforms** |
| `iDispEndpointOverride` | REG_DWORD | Force iDisp endpoint count (debug) |

### Graphics Driver Audio Integration
```
HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E968-E325-11CE-BFC1-08002BE10318}\0000\
```
| Value | Type | Purpose |
|-------|------|---------|
| `AudioEnabled` | REG_DWORD | 1=iDisp audio enabled in GPU driver |

---

## ETW / WPP Trace Capture

### Capture Display Audio Events
```cmd
:: Display audio events come through both audio and graphics stacks
logman create trace iDispAudioTrace ^
  -p {GUID-IntcAudioBus} 0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-Audio" 0xFFFF 4 ^
  -o C:\Temp\iDispAudio.etl -mode Circular -nb 16 256
logman start iDispAudioTrace

:: Plug/unplug HDMI/DP cable to generate HPD events
:: ... then stop:
logman stop iDispAudioTrace
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `HPD` / `HotPlug` | Hot Plug Detect event from GPU |
| `ELD` / `EDID` | ELD (EDID Like Data) readback from display |
| `iDisp` / `HDMI` / `DP` | Display audio path events |
| `SDI1` | iDisp codec on HDA SDI lane 1 |

---

## Common Failure Modes

### Failure: No HDMI/DP audio endpoint after monitor connect
1. Check `STATESTS` bit 1 (SDI1 = iDisp link) — if 0, GPU not driving iDisp codec
2. Verify Intel GPU driver is loaded and display is active
3. Check Event Viewer for GPU driver errors
4. On NVL PCD-H: check SoundWire Seg0 link state (alt path for iDisp)
5. Try different HDMI/DP port; some ports may not support audio

### Failure: ELD readback returns all zeros
1. Check display EDID — if monitor doesn't advertise audio, ELD is empty
2. Check HDMI cable quality — EDID can fail to propagate with bad cables
3. Verify `AudioEnabled=1` in GPU driver registry

### Failure: Audio drops during display mode change
1. Display mode change triggers GPU re-initialization → iDisp codec reset
2. Audio stream must be re-established after mode change
3. Check WPP trace for HPD event sequence during mode switch
4. Verify ELD re-read after display re-configuration

### Failure: MST (Multi-Stream Transport) audio issues
1. MST adds DP MST branch device between GPU and monitor
2. Each MST port has separate iDisp audio endpoint
3. Check `Get-PnpDevice` for multiple iDisp endpoints
4. WPP trace to verify MST topology discovery

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\display-audio\`

Key test categories:
- `idisp_enumeration\` — verify iDisp codec on SDI1, ELD readback
- `idisp_playback\` — PCM playback through HDMI/DP endpoint
- `idisp_hotplug\` — cable plug/unplug, endpoint appear/disappear
- `idisp_mst\` — MST hub topology, multi-endpoint audio
- `idisp_power\` — D3 transitions with display audio active

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\display-audio\idisp_enumeration
python run_test.py --verbose
```
