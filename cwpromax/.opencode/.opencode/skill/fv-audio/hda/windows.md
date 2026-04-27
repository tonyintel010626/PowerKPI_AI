# HDA — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only. All test content at `C:\validation\windows-test-content\audio\hda\`.
> **Platform**: NVL (Novalake) and prior ACE platforms.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Bus driver | `HdAudio.sys` | Microsoft HDA bus driver; enumerates codec function groups |
| Intel bus filter | `IntcAudioBus.sys` | Intel HDA bus filter/extension; NVL-specific init, verb sequencing |
| Codec function driver | `IntcAudioInterface.sys` | Intel HDA codec driver (Cirrus CS42L43 path) |
| Realtek codec | `RTKVHD64.sys` | Realtek ALC256/298/700 codec driver |
| ACX framework | `Hdaudbus.sys` + ACX stack | Windows 11 ACX-based audio class eXtension model (NVL+) |

**INF files**: `HdAudio.inf`, `IntcAudioBus.inf`, codec-specific INFs under `%SystemRoot%\INF\`.

**Device class GUID**: `{4D36E96C-E325-11CE-BFC1-08002BE10318}` (Audio)

---

## Device Enumeration

### Check HDA Controller
```cmd
:: List HDA controller (PCI)
devcon hwids "PCI\VEN_8086&DEV_*" | findstr -i "audio\|hda\|ace"

:: Show all audio devices
devcon status =MEDIA

:: Show HDA codec nodes
devcon hwids "HDAUDIO\FUNC_01*"

:: Rescan for new hardware
devcon rescan
```

### Expected Device IDs (NVL)
- HDA controller: `PCI\VEN_8086&DEV_7728` (NVL PCH-S) or `PCI\VEN_8086&DEV_7748` (NVL PCD-H)
- iDisp codec: `HDAUDIO\FUNC_01&VEN_8086&DEV_2816` (Intel HDMI/DP audio)
- Realtek codec: `HDAUDIO\FUNC_01&VEN_10EC&DEV_0298` (ALC298)

### pnputil Operations
```cmd
:: List installed audio INF packages
pnputil /enum-drivers /class MEDIA

:: Export driver package
pnputil /export-driver "IntcAudioBus.inf" C:\Temp\audio_driver_backup

:: Force reinstall codec driver
pnputil /remove-device "HDAUDIO\FUNC_01&..." && devcon rescan
```

---

## Windows Registry Knobs

### Audio Device Class Settings
```
HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E96C-E325-11CE-BFC1-08002BE10318}\0000\
```
Key values under the instance subkey (0000, 0001, …):
| Value | Type | Purpose |
|-------|------|---------|
| `DriverDesc` | REG_SZ | Friendly driver name |
| `IntelAudioSilentStream` | REG_DWORD | 0=disable silent stream (power optimization) |
| `HdaStreamDescriptorCount` | REG_DWORD | Override stream descriptor count |

### Intel HDA Bus Service
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `LogLevel` | REG_DWORD | WPP trace verbosity (0=off, 4=verbose) |
| `DisableHdaLink` | REG_DWORD | 1=disable HDA link (for iDisp isolation) |
| `CodecResetDelay` | REG_DWORD | GCTL.CRST hold time in ms (default: 1) |

### HDAUDIO Enumeration Key
```
HKLM\SYSTEM\CurrentControlSet\Enum\HDAUDIO\FUNC_01\<DeviceID>\
```
| Value | Purpose |
|-------|---------|
| `DeviceDesc` | Codec description |
| `Mfg` | Manufacturer string |
| `Service` | Active function driver (e.g. `RTKVHD64`) |

---

## ETW / WPP Trace Capture

### Capture Intel HDA Bus WPP Trace
```cmd
:: Step 1 – Enable tracing (run as admin)
logman create trace IntcAudioBusTrace -p {GUID-FROM-PDB} 0xFFFFFFFF 0xFF -o C:\Temp\IntcAudioBus.etl -mode Circular -nb 16 256

:: Step 2 – Start trace
logman start IntcAudioBusTrace

:: Step 3 – Reproduce issue

:: Step 4 – Stop and collect
logman stop IntcAudioBusTrace
tracerpt C:\Temp\IntcAudioBus.etl -o C:\Temp\IntcAudioBus.csv -of CSV
```

> **NOTE**: Extract WPP provider GUIDs from driver PDB files:
> ```cmd
> tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb -p C:\Temp\IntcTmf
> ```
> Then use `tmf` files with `tracefmt.exe` to decode the ETL.

### Microsoft HDA ETW Provider
```cmd
:: List all registered audio-related ETW providers
logman query providers | findstr -i "audio\|hda\|intc"

:: Enable Microsoft HDA provider
logman create trace HdAudioTrace -p "Microsoft-Windows-Audio" 0xFFFF 4 -o C:\Temp\HdAudio.etl
```

### Windows Audio Session API (WASAPI) Trace
```cmd
xperf -on PROC_THREAD+LOADER+PROFILE -start AudioSession -on Microsoft-Windows-Audio:0xFFFF:4 -f C:\Temp\wasapi.etl
:: ... reproduce ...
xperf -stop AudioSession -stop -d C:\Temp\merged_audio.etl
```

---

## HDA Register Debug (via PythonSV + BAR0)

See `SKILL.md` for full register map. Quick Windows-side correlation:

| Windows symptom | BAR0 register to check |
|-----------------|------------------------|
| Codec not enumerated | `STATESTS` @ 0x0E — bits 0/1 for SDI0/SDI1 |
| Audio glitch / dropout | `SDnSTS` bit2 (BCIS) — buffer completion |
| No sound output | `SDnCTL` bit1 (RUN) — stream running |
| Controller lockup | `GCTL` bit0 (CRST) — must be 1 for normal op |

---

## Common Windows HDA Failure Modes

### Failure: Codec not enumerated (`STATESTS` = 0)
1. Check `GCTL.CRST` — if 0, controller is in reset; driver failed to exit reset
2. Check `IntcAudioBus` service status: `sc query IntcAudioBus`
3. Check ACPI `_HID` for HDA controller in Device Manager → Properties → Details → Hardware IDs
4. Verbose log: set `LogLevel=4` in `IntcAudioBus\Parameters`, reboot, collect WPP ETL

### Failure: HDA stream stops (DMA underrun)
1. Check `SDnSTS` FIFOE bit (bit3) — FIFO error
2. Check `SDnSTS` DESE bit (bit4) — descriptor error
3. Increase cyclic buffer (BD list entries): registry `HdaStreamDescriptorCount`
4. Check if MMCSS is active: `sc query MMCSS`

### Failure: iDisp audio absent on HDMI/DP
1. Check if `HDAUDIO\FUNC_01&VEN_8086` is present in Device Manager
2. Check `STATESTS` bit1 (SDI1 = iDisp link); if 0, GPU or link not enabled
3. Check GPU driver: iDisp codec is co-owned by Intel graphics driver
4. On NVL PCD-H, iDisp uses SoundWire Seg0 alt path — check SoundWire link state

### Failure: Driver crash on D3/resume
1. Capture crash dump: `HKLM\SYSTEM\CurrentControlSet\Control\CrashControl\AlwaysKeepMemoryDump=1`
2. Open in WinDbg: `!analyze -v` → check faulting module (`IntcAudioBus.sys` or `HdAudio.sys`)
3. Check D3 entry sequence: streams must be stopped before PMCSR write

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\hda\`

Key test categories:
- `hda_codec_enumeration\` — verify `STATESTS`, codec node count
- `hda_stream_playback\` — PCM playback through all render endpoints
- `hda_stream_capture\` — PCM capture from all capture endpoints
- `hda_verb_sequence\` — CORB write / RIRB read round-trip timing
- `hda_power_state\` — D0/D3 transitions, stream resume integrity

Run a specific test manually:
```cmd
cd C:\validation\windows-test-content\audio\hda\hda_codec_enumeration
python run_test.py --verbose
```
