# SoundWire — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only. All test content at `C:\validation\windows-test-content\audio\soundwire\`.
> **Platform**: NVL (Novalake) — 5 SoundWire segments (Seg0–4), ACE 4.x master.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| SoundWire bus driver | `SdwBus.sys` | Microsoft SoundWire bus driver; enumerates slave devices |
| Intel SoundWire host | `IntcAudioSdw.sys` | Intel ACE SoundWire master controller driver |
| SDCA class driver | `SdcaDriver.sys` | Microsoft SDCA (SoundWire Device Class for Audio) driver |
| Codec function driver | Per-codec `.sys` | e.g. `CsAudioAcx.sys` (Cirrus CS42L43/CS35L56), `MaxxAudio.sys` (Maxim) |
| ACX framework | `IntcAudioCircuit.sys` | Windows 11 ACX circuit driver for SDCA topology |

**SoundWire bus device**: appears under "System devices" in Device Manager as `"Intel(R) Smart Sound Technology (Intel(R) SST) Audio Controller"`

**Slave codec devices**: appear under "Sound, Video and Game Controllers" once enumerated by `SdwBus.sys`.

---

## Device Enumeration

### Verify SoundWire Bus and Codec Enumeration
```cmd
:: Show SoundWire bus instances
devcon hwids "ACPI\INT0004*"   :: Intel SoundWire ACPI node (platform-specific HID)
devcon hwids "SWD\*"           :: SoundWire Device namespace

:: Show all SoundWire codec devices
devcon status "SWD\*"

:: Detailed codec hardware IDs (Peripheral ID format: MIPI SDW PIDS)
devcon hwids "SWD\*" | findstr -i "VEN\|DEV\|SDW"

:: PowerShell: list SoundWire codecs
powershell -c "Get-PnpDevice | Where-Object {$_.InstanceId -like 'SWD*'} | Select-Object Status, FriendlyName, InstanceId"
```

### Expected SoundWire Device IDs (NVL)
- Cirrus CS42L43: `SWD\VEN_01FA&DEV_4243` (MIPI Peripheral ID based)
- Cirrus CS35L56: `SWD\VEN_01FA&DEV_3556`
- Realtek ALC5682: `SWD\VEN_025D&DEV_5682`
- Maxim MAX98373: `SWD\VEN_019F&DEV_8373`

> **Note**: MIPI SoundWire Peripheral IDs are 48-bit. Windows displays a subset. Full ID format: `{mfgID[15:0], partID[15:0], classID[7:0], version[7:0]}`. Verify against codec datasheet.

---

## Windows Registry Knobs

### Intel SoundWire Master Controller
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioSdw\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `LogLevel` | REG_DWORD | WPP verbosity: 0=off, 4=verbose |
| `LinkClockFrequency` | REG_DWORD | Override bus clock in Hz (default: 9600000 = 9.6 MHz) |
| `EnumerationTimeout` | REG_DWORD | Slave enumeration timeout in ms (default: 200) |
| `ClockStopMode` | REG_DWORD | 0=Mode0 (all slaves), 1=Mode1 (advanced, codec keeps context) |
| `ActiveSegmentMask` | REG_DWORD | Bitmask of enabled segments (bits 0-4 for Seg0-4) |

### SoundWire Bus Driver
```
HKLM\SYSTEM\CurrentControlSet\Services\SdwBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `EnumerationRetryCount` | REG_DWORD | Number of PING retries before giving up (default: 3) |
| `DeepSleepEnable` | REG_DWORD | 1=allow clock-stop Mode1 (codec deep sleep) |

### SDCA Class Driver
```
HKLM\SYSTEM\CurrentControlSet\Services\SdcaDriver\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `SdcaLogVerbosity` | REG_DWORD | SDCA trace level |
| `DisableDynamicTopology` | REG_DWORD | 1=static SDCA topology only (debug fallback) |

### Codec-Specific Keys
```
HKLM\SYSTEM\CurrentControlSet\Enum\SWD\<DeviceID>\Device Parameters\
```
Codec-specific INF registry settings (e.g. gain tables, clock config) land here.

---

## ETW / WPP Trace Capture

### Capture SoundWire Bus + SDCA Trace
```cmd
:: Step 1 – Extract WPP GUIDs from driver PDBs
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioSdw.pdb -p C:\Temp\SdwTmf
tracepdb.exe -f %SystemRoot%\System32\drivers\SdwBus.pdb      -p C:\Temp\SdwBusTmf
tracepdb.exe -f %SystemRoot%\System32\drivers\SdcaDriver.pdb  -p C:\Temp\SdcaTmf

:: Step 2 – Start composite trace (all three providers)
logman create trace SoundWireTrace ^
  -p {WPP-GUID-IntcAudioSdw} 0xFFFFFFFF 0xFF ^
  -p {WPP-GUID-SdwBus}       0xFFFFFFFF 0xFF ^
  -p {WPP-GUID-SdcaDriver}   0xFFFFFFFF 0xFF ^
  -o C:\Temp\SoundWire.etl -mode Circular -nb 32 512
logman start SoundWireTrace

:: Step 3 – Reproduce (boot, plug device, start audio stream, etc.)

:: Step 4 – Stop and decode
logman stop SoundWireTrace
:: Decode each provider's TMF separately
tracefmt C:\Temp\SoundWire.etl -tmf C:\Temp\SdwTmf    -o C:\Temp\SoundWire_IntcSdw.txt
tracefmt C:\Temp\SoundWire.etl -tmf C:\Temp\SdwBusTmf -o C:\Temp\SoundWire_Bus.txt
tracefmt C:\Temp\SoundWire.etl -tmf C:\Temp\SdcaTmf   -o C:\Temp\SoundWire_Sdca.txt
```

### Key Trace Events to Search For
| Pattern | Meaning |
|---------|---------|
| `PING` / `ENUMERATION` | Slave discovery phase |
| `DeviceID` | 48-bit Peripheral ID response from slave |
| `ATTACHED_OK` | Slave reached Attached_OK state |
| `CLOCK_STOP` | Mode0/Mode1 clock stop entry |
| `CLOCK_RESTART` | Bus clock restart after stop |
| `SDW_TIMEOUT` / `ACK_TIMEOUT` | Slave not responding |
| `SDCA_CONTROL_READ/WRITE` | SDCA register access |

---

## SoundWire Enumeration Debug (Windows)

### Enumeration Sequence
1. Master activates segment: `LCTL[N]` — link power + clock keeper enabled
2. Master sends PING frames — `COMMAND=PING, DeviceNumber=0`
3. Slave responds with Peripheral ID bits via `STAT` field
4. Master assigns `DeviceNumber` 1–11 via `WRITE DeviceNumber` command
5. Slave reaches `Attached_OK` — Windows sees `SWD\` device instance

### Check Slave Enumeration State (PythonSV)
```python
# Segment N (0-4) link control
soc.ace.sdw.shim.lctl[N].spa     # 1 = segment power active
soc.ace.sdw.shim.lctl[N].ioctl   # clock keeper

# Check enumeration status for segment N
soc.ace.sdw.shim.lcap[N]         # link capability register

# Per-slave status (slave index 1-11)
soc.ace.sdw.link[N].sdw_dpn_status[slave_idx]  # DP0 status
```

### SHIM Register Quick Checks
```python
# Mandatory first checks for enumeration failure:
soc.ace.sdw.shim.lctl[N]         # link control — is clock/power enabled?
soc.ace.sdw.shim.clkctl[N]       # clock source and frequency
```
If `lctl[N].spa = 0`, the segment is not powered — check `ActiveSegmentMask` registry value and ACE driver initialization.

---

## Clock-Stop Mode Debug

### Mode 0 (Simple — all slaves must support)
- Master sends `STOP_CLOCK` bit to all slaves simultaneously
- All slaves freeze — simple, no context retained
- On restart: full re-enumeration required

### Mode 1 (Advanced — codec retains context)
- Codec advertises `ClockStopMode1` in `SDW_SCP_SDCA_INTMASK`
- Codec freezes bus transactions but retains audio engine state
- On restart: no re-enumeration needed, pipeline resumes faster
- Enable via `DeepSleepEnable=1` + `ClockStopMode=1` registry

### Clock Stop Failure Symptoms
| Symptom | Likely Cause |
|---------|-------------|
| Audio glitch on S0ix exit | Clock restart too fast; codec not ready |
| Codec disappears after resume | Mode1 failed; codec lost context |
| S0ix blocked | Clock stop never completed; slave ACK timeout |

Check:
```python
# Is clock stopped?
soc.ace.sdw.shim.clkctl[N].mcs   # master clock state; 0=running, 1=stopped
```

---

## SDCA (SoundWire Device Class for Audio)

SDCA is the class model used by Windows for SoundWire codecs (Windows 11+). It replaces proprietary codec INF sequences with a standardized control model.

### Key SDCA Concepts
| Term | Meaning |
|------|---------|
| **Function Block (FB)** | Logical audio function (e.g. Speaker, Microphone) |
| **Control Selector (CS)** | Register inside a FB (e.g. Volume, Mute) |
| **Control Number (CN)** | Index within a CS |
| **IntStat** | Interrupt status register (slave reports events) |

### SDCA Debug Registry
```
HKLM\SYSTEM\CurrentControlSet\Enum\SWD\<DeviceID>\Device Parameters\SDCA\
```
Contains SDCA function block map, control selectors, and interrupt mapping.

### SDCA Interrupt Handling
Codecs signal events (jack detection, overcurrent, etc.) via SoundWire `INT` frames. Windows routes these through `SdcaDriver.sys` → `IntcAudioCircuit.sys` → audio endpoint change notification.

If jack detection is not working:
1. Check `SDW_SCP_INTSTAT` register on codec (via PythonSV SoundWire SBI read)
2. Check `SHIM_WAKEEN[N]` — segment wake interrupt enable
3. Check `SdcaDriver` WPP trace for unhandled IntStat bits

---

## Common Windows SoundWire Failure Modes

### Failure: Codec not enumerated (no `SWD\` device)
1. Check `ActiveSegmentMask` — ensure the segment hosting this codec is enabled
2. Check `SdwBus` service: `sc query SdwBus` — must be RUNNING
3. Check `LCTL[N].spa` (via PythonSV) — segment must be powered
4. Increase `EnumerationTimeout` to 500 ms
5. Increase `EnumerationRetryCount` to 5
6. WPP trace — search for `PING` timeout or no `DeviceID` response
7. Check ACPI `_SDW` or `_CRS` descriptor for the codec in `SSDT` (iasl disassembly)

### Failure: Codec enumerates but audio endpoint absent
1. Check `SdcaDriver` loaded: `sc query SdcaDriver`
2. Check SDCA function block definition in INF — missing FB definition → no audio endpoint
3. Check ACX circuit creation: WPP trace in `IntcAudioCircuit.sys`

### Failure: Audio drops or distorts during playback
1. Check for clock stability: capture WPP trace, look for `SDW_SYNC_LOST` or `BUS_RESET`
2. Check `LinkClockFrequency` — ensure it matches codec's supported clock range
3. Check SoundWire data port configuration (DP width, sample interval) — must match stream format

### Failure: S0ix blocked by SoundWire
1. Check clock-stop completed: `clkctl[N].mcs = 1`
2. Check slave ACK to clock-stop: WPP trace `CLOCK_STOP` ACK
3. Try `ClockStopMode=0` (Mode0) as fallback — simpler, all slaves must support it
4. Check `IntcAudioSdw` WPP trace for `CLOCK_STOP_TIMEOUT`

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\soundwire\`

Key test categories:
- `sdw_enumeration\` — segment activation, PING, 48-bit device ID, Attached_OK
- `sdw_stream_playback\` — PCM playback via SoundWire codec
- `sdw_stream_capture\` — PCM capture via SoundWire codec
- `sdw_clock_stop_mode0\` — Mode0 clock stop/restart, codec re-enum
- `sdw_clock_stop_mode1\` — Mode1 deep sleep, context retention
- `sdw_sdca_controls\` — SDCA function block read/write, volume/mute controls
- `sdw_jack_detect\` — SDCA interrupt → jack insertion/removal event

Run a specific test manually:
```cmd
cd C:\validation\windows-test-content\audio\soundwire\sdw_enumeration
python run_test.py --verbose --segment 0
```
