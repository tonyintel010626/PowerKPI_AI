# AIOC — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only Gen6 AIOC (ALC712/ALC1320) validation — SoundWire Segment 2 enumeration, SDCA/ACX driver model, 5-Star topology, and codec-specific troubleshooting.
> **Platform**: NVL (Novalake) — ACE 4.x. AIOC requires SoundWire Seg 2 and SDCA/ACX support.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| SoundWire bus | `SdwBus.sys` | Microsoft SoundWire bus — enumerates ALC712 + ALC1320 on Seg 2 |
| Intel SoundWire host | `IntcAudioSdw.sys` | Intel ACE SoundWire master controller |
| SDCA class driver | `SdcaDriver.sys` | Microsoft SDCA protocol — function block discovery |
| ACX circuit | `IntcAudioCircuit.sys` | ACX topology — audio endpoint creation |
| Realtek codec | Realtek SDCA INF | ALC712-VB + ALC1320 codec driver |
| Intel audio bus | `IntcAudioBus.sys` | Bus filter — subsystem ID matching |

---

## Device Enumeration

### Verify AIOC Codecs on SoundWire Seg 2
```cmd
:: Check SoundWire codec devices (ALC712 + ALC1320)
devcon hwids "SWD\*" | findstr -i "VEN_025D\|ALC712\|ALC1320"

:: Check all SoundWire devices
powershell -c "Get-PnpDevice | Where-Object {$_.InstanceId -like 'SWD*'} | Format-Table Status, FriendlyName, InstanceId"

:: Check SDCA driver loaded
sc query SdcaDriver

:: Check ACX circuit driver
sc query IntcAudioCircuit

:: Verify subsystem ID = 0x305610EC (Gen6 AIOC)
:: Check Device Manager → Intel SST → Properties → Details → Subsystem ID
```

### Expected AIOC Device IDs
- ALC712-VB combo codec: `SWD\VEN_025D&DEV_0712` (MIPI SoundWire Peripheral ID)
- ALC1320 smart amp: `SWD\VEN_025D&DEV_1320`

> **ES vs MP boards**: Engineering Sample boards use different firmware. If codec enumerates but no audio, verify BIOS topology matches board label (ES vs MP).

---

## Windows Registry Knobs

### AIOC-Specific Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioSdw\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `ActiveSegmentMask` | REG_DWORD | Must include bit 2 (Seg 2) = 0x04 or 0x1F for all |
| `LogLevel` | REG_DWORD | WPP verbosity (0=off, 4=verbose) |

### SDCA/ACX Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\SdcaDriver\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `SdcaLogVerbosity` | REG_DWORD | SDCA trace level |
| `DisableDynamicTopology` | REG_DWORD | 1=static topology only (debug fallback) |
| `DisableSpeakerAggregation` | REG_DWORD | 1=disable ALC1320 speaker aggregation |

### Subsystem ID Override (Debug)
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `SubsystemIdOverride` | REG_DWORD | Override subsystem ID for topology matching (0x305610EC for AIOC) |

---

## ETW / WPP Trace Capture

### Capture AIOC Enumeration + Audio
```cmd
:: Extract TMF from all relevant drivers
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioSdw.pdb -p C:\Temp\Tmf
tracepdb.exe -f %SystemRoot%\System32\drivers\SdwBus.pdb       -p C:\Temp\Tmf
tracepdb.exe -f %SystemRoot%\System32\drivers\SdcaDriver.pdb   -p C:\Temp\Tmf

:: Start combined trace
logman create trace AiocTrace ^
  -p {GUID-IntcAudioSdw} 0xFFFFFFFF 0xFF ^
  -p {GUID-SdwBus}       0xFFFFFFFF 0xFF ^
  -p {GUID-SdcaDriver}   0xFFFFFFFF 0xFF ^
  -o C:\Temp\Aioc.etl -mode Circular -nb 32 512
logman start AiocTrace

:: Boot / plug headphone / play audio, then stop:
logman stop AiocTrace
tracefmt C:\Temp\Aioc.etl -tmf C:\Temp\Tmf -o C:\Temp\Aioc.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `SEGMENT_2` / `SEG2` | SoundWire Segment 2 activity |
| `ALC712` / `ALC1320` | Codec-specific events |
| `SDCA_FB` / `FunctionBlock` | SDCA function block discovery |
| `SPEAKER_AGGREGATION` | ALC1320 speaker amp aggregation |
| `5STAR` / `MULTI_DROP` | 5-Star multi-drop topology events |
| `JACK_DETECT` | Headphone/mic jack insertion via slave alert |
| `SUBSYS_ID=0x305610EC` | Subsystem ID confirmation |

---

## Common Failure Modes

### Failure: ALC712 not enumerated on Segment 2
1. Check BIOS: `SNDW #2` = Enabled (this is the AIOC bus)
2. Check DIP switches: SW9B2 and SW9C1 = OFF-ON-OFF-ON
3. Check `ActiveSegmentMask` includes bit 2
4. Check JE header connection between Base AIC and RVP
5. WPP trace: search for `SEGMENT_2` + `PING` — no response = physical issue

### Failure: ALC1320 missing (speaker amp not detected)
1. Check BIOS: `ACX/SDCA speaker aggregation` = Enabled
2. Check topology: select MP or ES variant matching your board
3. WPP trace: search for `ALC1320` + `ENUMERATION`
4. Check Transducer AIC speaker header connection to Base AIC

### Failure: "No audio endpoints" despite codecs enumerated
1. Check BIOS: `ACX/SDCA` = Enabled
2. Check `SdcaDriver` loaded: `sc query SdcaDriver`
3. Check `IntcAudioCircuit` loaded: `sc query IntcAudioCircuit`
4. WPP trace: search for `SDCA_FB` — function blocks must be discovered
5. Verify Windows version supports ACX (Windows 11 22H2+)

### Failure: Headphone works but speaker silent
1. Check ALC1320 initialization: WPP trace for `SPEAKER_AGGREGATION`
2. Check BIOS `ACX/SDCA speaker aggregation` = Enabled
3. Check Transducer AIC speaker cable connection
4. Try `DisableSpeakerAggregation=0` to confirm feature is active

### Failure: Subsystem ID mismatch
1. Check BIOS: `HD Audio Bus Controller Subsystem Id` = `0x305610EC`
2. Verify via Device Manager → Intel SST → Properties → Details → Subsystem ID
3. Wrong SSID causes topology mismatch → no AIOC codec loading

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\aioc\`

Key test categories:
- `aioc_enumeration\` — verify ALC712 + ALC1320 on Seg 2, SDCA function blocks
- `aioc_playback\` — headphone + speaker playback through AIOC codecs
- `aioc_capture\` — microphone capture through ALC712
- `aioc_jack_detect\` — headphone plug/unplug via SoundWire slave alert
- `aioc_power\` — D3/S0ix transitions with AIOC active

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\aioc\aioc_enumeration
python run_test.py --verbose
```
