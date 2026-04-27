# Wake on Voice — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only WoV (Wake on Voice) validation — keyword detection arming, S0ix integration, CRO clock switch, DMIC injector automation.
> **Platform**: NVL (ACE 4.x), PTL (ACE 3.0), LNL (ACE 2.x), MTL/ARL (ACE 1.5).

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Intel SST | `IntcSmartSound.sys` | DSP FW load, WoV pipeline management |
| Intel audio bus | `IntcAudioBus.sys` | HDA bus, DMIC clock configuration |
| WoV client app | `WoVClientApplication.exe` | User-space WoV arm/disarm/status tool |
| PMC integration | (kernel) | PMC wake event on keyword detect |

---

## Device Enumeration

### Verify WoV Prerequisites
```cmd
:: Check ACE device enumerated
devcon hwids "PCI\VEN_8086&DEV_D328*"  :: NVL PCD-H

:: Check DSP driver loaded (required for WoV FW)
sc query IntcSmartSound

:: Check DMIC device (WoV input source)
powershell -c "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Microphone*Array*'} | Format-Table Status, FriendlyName"

:: Verify WoV BIOS settings applied
:: (check Device Manager → Intel SST → Properties → WoV status)
```

---

## Windows Registry Knobs

### WoV Configuration
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `WoVEnabled` | REG_DWORD | 1=WoV feature enabled |
| `KeywordModel` | REG_SZ | Path to keyword detection model file |
| `LogLevel` | REG_DWORD | WPP verbosity (0=off, 4=verbose) |

### WoV Power Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\WoV\
```
| Value | Type | Purpose |
|-------|------|---------|
| `CroClockEnable` | REG_DWORD | 1=use CRO for ultra-low-power (~300 µW) |
| `WoVTimeout` | REG_DWORD | Timeout in seconds before WoV disarms (0=infinite) |

### MultiPA Registry (Required)
```cmd
:: Merge MultiPA.reg after BIOS changes (configures audio policy for WoV)
reg import MultiPA.reg
:: Reboot required after merge
```

---

## ETW / WPP Trace Capture

### Capture WoV Arm/Trigger Cycle
```cmd
:: Extract TMF from SST driver
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcSmartSound.pdb -p C:\Temp\SstTmf

:: Start trace
logman create trace WoVTrace ^
  -p {GUID-IntcSmartSound} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\WoV.etl -mode Circular -nb 16 256
logman start WoVTrace

:: Run WoV test: arm → S0ix → keyword trigger → wake → disarm
:: ... then stop:
logman stop WoVTrace
tracefmt C:\Temp\WoV.etl -tmf C:\Temp\SstTmf -o C:\Temp\WoV.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `WOV_ARM` | WoV keyword detection armed |
| `WOV_DISARM` | WoV keyword detection disarmed |
| `WOV_TRIGGER` / `KWD_DETECT` | Keyword detected — wake event |
| `CRO_SWITCH` | Clock switched from XTAL to CRO (or reverse) |
| `DMIC_START` | DMIC capture started for WoV pipeline |
| `S0IX_ENTRY` / `S0IX_EXIT` | Platform sleep state transitions |
| `FW_PIPELINE_CREATE` | DSP WoV pipeline created |

---

## Common Failure Modes

### Failure: WoV won't arm
1. Check BIOS: both `WoV[X]` and `Intel WoV[X]` must be Enabled
2. Verify `MultiPA.reg` merged and reboot completed
3. Check `IntcSmartSound` service running: `sc query IntcSmartSound`
4. Run `WoVClientApplication.exe` → press 'A' to check status
5. WPP trace: search for `WOV_ARM` + `ERROR` or `FAIL`

### Failure: No keyword detection (WoV armed but won't trigger)
1. Check DMIC is functional: test regular capture first
2. Check DMIC pad configuration: see `dmic/SKILL.md` and `dmic/windows.md`
3. Check CRO clock active: via PythonSV `CLKSTS.WOVROSCS`
4. Check keyword WAV format: must be 4-channel, 16-bit, 48 kHz
5. Check DMIC injector card wiring to correct headers

### Failure: S0ix blocked when WoV armed
1. Check ACE LTR value: should report idle-capable LTR
2. Run `print_LTRs` doctor script via PythonSV
3. Check `CroClockEnable=1` — CRO mode uses ~300 µW vs mW for XTAL
4. Cross-reference with `power/SKILL.md` §S0ix LTR Validation

### Failure: DSP hang after CRO clock switch
1. CRO↔XTAL switch must ONLY occur during WoV arm/disarm transitions
2. Never switch mid-stream — causes DSP hang and audio corruption
3. WPP trace: check `CRO_SWITCH` timing relative to `DMIC_START`
4. Check `DSPWCCTL.DWCS` register value matches expected clock source

### Failure: WoV works once then fails on subsequent iterations
1. Check WoV re-arm after wake: automation must explicitly re-arm
2. Check S0ix re-entry after keyword wake: monitor `slp_s0_residency`
3. WPP trace: verify `WOV_DISARM` → `WOV_ARM` cycle per iteration

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\wov\`

Key test categories:
- `wov_arm_disarm\` — basic WoV arm/disarm cycle
- `wov_keyword_detect\` — keyword trigger via DMIC injector
- `wov_s0ix_residency\` — S0ix residency while WoV armed
- `wov_iteration_stress\` — 100+ arm→wake→disarm cycles
- `wov_false_reject\` — keyword detection accuracy at various distances

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\wov\wov_keyword_detect
python run_test.py --verbose
```
