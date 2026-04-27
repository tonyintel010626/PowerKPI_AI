# DMIC — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only. All test content at `C:\validation\windows-test-content\audio\dmic\`.
> **Platform**: NVL (Novalake) and prior ACE platforms.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| ACE bus driver | `IntcAudioBus.sys` | Exposes DMIC capture path as Windows audio endpoint |
| DSP topology driver | `IntcSST2.sys` | Routes DMIC PDM data through DSP pipeline (ACE DSP) |
| MicArray geometry | ACE ACPI / INF | Describes microphone array geometry to Windows |
| Privacy HW engine | ACE DMIC HW | Hardware DMA zeroing (operates below DSP, S/W-transparent) |

**Device class**: Sound, Video and Game Controllers → `{4D36E96C-E325-11CE-BFC1-08002BE10318}`

DMIC endpoints appear in Windows as **"Microphone Array"** or **"Digital Microphone"** in Sound settings.

---

## Device Enumeration

### Verify DMIC is Enumerated
```cmd
:: Show all capture endpoints
pnputil /enum-devices /class MEDIA /connected | findstr -i "dmic\|microphone\|array"

:: Check ACE BAR2 exposure (GPROCEN must be set by driver)
devcon status "PCI\VEN_8086&DEV_7728"   :: NVL PCH-S ACE

:: PowerShell: list audio capture devices
powershell -c "Get-PnpDevice -Class MEDIA | Where-Object {$_.FriendlyName -match 'microphone|DMIC|array'} | Select-Object Status, FriendlyName, DeviceID"
```

### Expected Endpoint Name
NVL exposes DMIC as: `"Microphone Array (Intel® Smart Sound Technology)"` or `"DMIC Microphone Array"`

---

## Windows Registry Knobs

### MicArray Geometry Override
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture\{GUID}\Properties\
```
> The per-device GUID is found via `MMDevAPI` or the Sound control panel. Properties include:
| DEVPROPKEY | Purpose |
|------------|---------|
| `{0x026e516e,...} 3` | Microphone array geometry (channel count, angles) |
| `PKEY_AudioEndpoint_FormFactor` | `MicrophoneArray (0x000D)` |

### Intel Audio Bus DMIC Parameters
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `DmicClockSource` | REG_DWORD | 0=XTAL (default), 1=external MCLK |
| `DmicSampleRate` | REG_DWORD | Override capture sample rate (16000 or 48000) |
| `DmicChannelMask` | REG_DWORD | Bitmask of active PDM channels (default: 0x3) |
| `DisableMicPrivacy` | REG_DWORD | 1=bypass HW DMA zeroing (debug only — never ship) |
| `LogLevel` | REG_DWORD | WPP verbosity (0=off, 4=verbose) |

### Windows Microphone Privacy Setting
```
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\
```
| Value | Meaning |
|-------|---------|
| `Value = "Allow"` | Global microphone access permitted |
| `Value = "Deny"` | Global microphone access blocked (DMIC captures return silence) |

> **NOTE**: On NVL, hardware privacy mode (`MICPVCE=1`, `DDZE=10b`) operates independently of the OS privacy switch. Even with OS `Allow`, the ACE HW zeroing can engage if the physical privacy key is pressed. Both layers must be checked during DMIC capture failures.

---

## ETW / WPP Trace Capture

### Capture DMIC / Audio Capture Pipeline Trace
```cmd
:: Step 1 – Extract WPP GUID from driver PDB
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb -p C:\Temp\IntcTmf

:: Step 2 – Start circular trace (4 MB per buffer, 16 buffers)
logman create trace DmicTrace -p {WPP-GUID-FROM-TRACEPDB} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\Dmic.etl -mode Circular -nb 16 256
logman start DmicTrace

:: Step 3 – Reproduce (start recording in Voice Recorder / Teams)

:: Step 4 – Stop and decode
logman stop DmicTrace
tracefmt C:\Temp\Dmic.etl -tmf C:\Temp\IntcTmf -o C:\Temp\Dmic_decoded.txt
```

### Microsoft Audio Capture ETW
```cmd
:: Windows built-in audio graph / capture engine provider
logman create trace WinAudioCapture ^
  -p "Microsoft-Windows-Audio" 0xFFFF 4 ^
  -p "Microsoft-Windows-AudioEndpointBuilder" 0xFFFF 4 ^
  -o C:\Temp\WinAudioCapture.etl
logman start WinAudioCapture
:: ... reproduce capture failure ...
logman stop WinAudioCapture
```

---

## GPIO Pad Mode Verification (Windows-side)

DMIC PDM pads must be in **PMode 1** (native function). Incorrect pad mode is the #1 cause of DMIC not working.

From Windows, pad mode is set by ACPI/BIOS and is not directly readable from userland. Indirect checks:
```cmd
:: Check if ACPI correctly describes DMIC pads — look for _GPIO resource in ACPI dump
acpidump.exe -o C:\Temp\acpi_tables.bin   :: Intel ACPI dump tool
acpixtract.exe -a C:\Temp\acpi_tables.bin
iasl.exe -d SSDT*.dat   :: Disassemble SSDTs, search for DMIC_CLK/DMIC_DATA
```
From PythonSV (with probe):
```python
# Verify DMIC_CLK_A pad mode = 1 (native function)
soc.gpio.northwest.dmic_clk_a_pad_cfg0.pmode  # expect 1
soc.gpio.northwest.dmic_data_a_pad_cfg0.pmode  # expect 1
```

---

## Common Windows DMIC Failure Modes

### Failure: No capture endpoint visible in Sound settings
1. Check `IntcAudioBus` service: `sc query IntcAudioBus` — must be RUNNING
2. Check GPIO PMode (above) — PMode=0 means DMIC pads are GPIO, not PDM
3. Check ACPI DMIC device node (`ACPI\INT343B` or similar) in Device Manager
4. Set `LogLevel=4`, reboot, capture WPP ETL, look for DMIC init errors

### Failure: DMIC endpoint present but captures silence
1. Check Windows microphone privacy: `Settings → Privacy → Microphone`
2. Check HW privacy mode: physical Fn+F4 (or privacy key) state; `MICPVCE` in ACE regs
3. Check `DmicChannelMask` registry — if 0, no channels enabled
4. Check `PDMCTRL.PDMCEN` bits via PythonSV (requires BAR2 access, GPROCEN=1)
5. Check input volume in Sound control panel → Recording → DMIC Properties

### Failure: Distorted or noisy capture
1. Check `DmicClockSource` — XTAL (0) is preferred for low-jitter
2. Check PDM clock frequency: must be 0.768–4.8 MHz; check ACPI/BIOS DMIC clock config
3. Check for EMI coupling: DMIC_DATA line may pick up interference from nearby high-frequency IOs
4. Try lower sample rate: `DmicSampleRate=16000` registry override

### Failure: Privacy LED stuck / HW privacy mismatch
1. HW DMA zeroing (`DDZE=10b`) operates below DSP — it zeroes PCM DMA data before driver sees it
2. Verify `MICPVCE` bit in `DfMICPVCP` register (via PythonSV)
3. Physical privacy LED GPIO state: check via `soc.gpio.<community>.mic_mute_led_pad_cfg0`
4. If LED is stuck ON after privacy disable, check `DDZPL` (policy lock) bit — may require BIOS update

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\dmic\`

Key test categories:
- `dmic_enum\` — verify capture endpoint enumeration, channel count
- `dmic_capture_16k\` — 16 kHz PCM capture, SNR/THD measurement
- `dmic_capture_48k\` — 48 kHz PCM capture
- `dmic_privacy_mode\` — HW zeroing engage/disengage, verify silence vs signal
- `dmic_multichannel\` — 4-channel capture, channel mapping validation

Run a specific test manually:
```cmd
cd C:\validation\windows-test-content\audio\dmic\dmic_capture_16k
python run_test.py --verbose --channel-mask 0x3
```
