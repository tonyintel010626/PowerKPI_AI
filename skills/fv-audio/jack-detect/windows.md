# Jack Detection — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only jack detection validation — HDA pin sense, SoundWire slave alerts, UAOL USB hot plug, and endpoint routing on plug/unplug events.
> **Platform**: NVL (Novalake), extensible to PTL, LNL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| HDA bus | `HdAudio.sys` | HDA unsolicited response → jack event dispatch |
| Intel audio bus | `IntcAudioBus.sys` | Intel HDA bus filter — pin sense monitoring |
| SoundWire bus | `SdwBus.sys` | SoundWire slave alert → jack event |
| SDCA class | `SdcaDriver.sys` | SDCA IntStat → jack type classification |
| ACX circuit | `IntcAudioCircuit.sys` | Audio endpoint add/remove on jack event |
| Realtek codec | `RTKVHD64.sys` | Codec-specific jack type detection (TRRS vs TRS) |

---

## Device Enumeration

### Verify Jack-Capable Endpoints
```cmd
:: Check audio endpoints (each jack-capable port appears as endpoint)
powershell -c "Get-PnpDevice -Class MEDIA | Where-Object {$_.FriendlyName -like '*Headphone*' -or $_.FriendlyName -like '*Microphone*' -or $_.FriendlyName -like '*Speaker*'} | Format-Table Status, FriendlyName"

:: Check jack detection events in real-time
:: Device Manager → Sound controllers → Intel SST → Events tab
```

---

## Windows Registry Knobs

### Jack Detection Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `JackDetectPollInterval` | REG_DWORD | Pin sense polling interval in ms (0=interrupt-only) |
| `DebounceTime` | REG_DWORD | Jack event debounce timer in ms (default: 50) |

### Realtek Codec Jack Settings
```
HKLM\SYSTEM\CurrentControlSet\Enum\HDAUDIO\FUNC_01&VEN_10EC&DEV_*\*\Device Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `JackType` | REG_DWORD | Detected jack type (headphone/headset/line-in) |
| `ImpedanceThreshold` | REG_DWORD | Threshold for headphone vs headset detection |

---

## ETW / WPP Trace Capture

### Capture Jack Detection Events
```cmd
:: Extract TMF
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb -p C:\Temp\BusTmf

:: Start trace
logman create trace JackDetectTrace ^
  -p {GUID-IntcAudioBus} 0xFFFFFFFF 0xFF ^
  -p "Microsoft-Windows-Audio" 0xFFFF 4 ^
  -o C:\Temp\JackDetect.etl -mode Circular -nb 16 256
logman start JackDetectTrace

:: Insert/remove headphone jack multiple times, then stop:
logman stop JackDetectTrace
tracefmt C:\Temp\JackDetect.etl -tmf C:\Temp\BusTmf -o C:\Temp\JackDetect.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `JACK_INSERT` / `JACK_REMOVE` | Physical jack event detected |
| `PIN_SENSE` | HDA pin sense register read |
| `UNSOLICITED_RESPONSE` | HDA codec unsolicited response (jack event) |
| `SLAVE_ALERT` | SoundWire slave alert (jack event) |
| `ENDPOINT_ADD` / `ENDPOINT_REMOVE` | Audio endpoint created/destroyed |
| `IMPEDANCE=` | Impedance measurement for jack type classification |

---

## Common Failure Modes

### Failure: No jack event on headphone insert (HDA)
1. Check HDA codec is present: `STATESTS` ≠ 0
2. Check unsolicited responses enabled on pin widget (verb 0x708)
3. Check RIRB not overflowed: `RIRBSTS` overflow bit
4. WPP trace: search for `UNSOLICITED_RESPONSE` after physical plug

### Failure: No jack event on insert (SoundWire)
1. Check SoundWire link active on codec's segment
2. Check slave alert not masked: `SCP_IntMask1` bit[2] for IMPL_DEF
3. WPP trace: search for `SLAVE_ALERT` events
4. Check `SdcaDriver` is handling IntStat correctly

### Failure: Jack type misidentified (headphone vs headset)
1. Check impedance sensing: WPP trace `IMPEDANCE=` value
2. Headphone (TRS) vs headset (TRRS) has different impedance profile
3. Check `ImpedanceThreshold` registry — may need adjustment
4. Check codec driver version: older drivers may have wrong thresholds

### Failure: USB audio hot plug not detected (UAOL)
1. Check xHCI port status: `PORTSC.CCS` and `PORTSC.CSC`
2. Check `IntcOED` service running (handles UAOL hot plug)
3. Both xHCI and ACE must be in D0 for UAOL hot plug
4. See `uaol/windows.md` for full UAOL hot plug debug

### Failure: Audio endpoint doesn't switch on jack event
1. Check Windows audio policy: default endpoint may not auto-switch
2. Check Sound Settings → Manage Sound Devices → endpoint is not disabled
3. WPP trace: `ENDPOINT_ADD` / `ENDPOINT_REMOVE` after jack event
4. Check `IntcAudioCircuit.sys` ACX endpoint creation

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\jack-detect\`

Key test categories:
- `hda_jack_detect\` — HDA pin sense headphone/mic insert/remove
- `sdw_jack_detect\` — SoundWire slave alert jack events
- `uaol_hotplug\` — USB audio device connect/disconnect
- `jack_type_classify\` — headphone vs headset vs line-in detection
- `jack_stress\` — rapid insert/remove cycling (100+ iterations)

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\jack-detect\hda_jack_detect
python run_test.py --verbose
```
