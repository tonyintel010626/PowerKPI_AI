# Platform — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only platform identification, die detection, and per-platform audio feature verification.
> **Platform**: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| PCI bus driver | `pci.sys` | PCI enumeration; creates ACE PDO at BDF 0:31:3 |
| Intel audio bus | `IntcAudioBus.sys` | Intel HDA bus driver/filter; reads DID, configures per-platform |
| Intel SST driver | `IntcSmartSound.sys` | Intel Smart Sound Technology; DSP FW load, pipeline mgmt |
| ACPI tables | `DSDT`/`SSDT` | Platform-specific audio _HID, _CRS, _DSD entries |

---

## Device Enumeration

### Identify Platform and Die Variant
```cmd
:: Read ACE Device ID from PCI config
devcon hwids "PCI\VEN_8086&DEV_*&SUBSYS_*&REV_*" | findstr -i "audio\|ace\|smart sound"

:: PowerShell: get audio PCI device details
powershell -c "Get-PnpDevice -Class MEDIA | Select-Object Status, FriendlyName, InstanceId"

:: Read DID directly (requires admin)
powershell -c "(Get-PnpDevice | Where-Object {$_.InstanceId -like 'PCI\VEN_8086&DEV_D328*'}).InstanceId"
```

### Expected Device IDs

| Platform | Die | DID | Hardware ID Pattern |
|----------|-----|-----|---------------------|
| NVL PCD-H | PCD | 0xD328 | `PCI\VEN_8086&DEV_D328` |
| NVL PCH-S | PCH | 0xD228 | `PCI\VEN_8086&DEV_D228` |
| MTL SOC-M | SOC | 0x7E28 | `PCI\VEN_8086&DEV_7E28` |
| MTL PCH-S | PCH | 0xAE28 | `PCI\VEN_8086&DEV_AE28` |
| PTL / LNL / ARL | varies | ⚠️ UNVERIFIED | Check `SKILL.md` DID table |

> **DID = 0xFFFF** means ACE is disabled in BIOS. Check `AudioController` BIOS knob.

### ACPI Table Verification
```cmd
:: Dump ACPI DSDT/SSDT and search for audio entries
:: Requires ACPI tools (iasl)
acpidump -b
iasl -d dsdt.dat
findstr /i "HDAS\|SNDW\|ACE\|DMIC" dsdt.dsl
```

---

## Windows Registry Knobs

### Platform Detection Keys
```
HKLM\SYSTEM\CurrentControlSet\Enum\PCI\VEN_8086&DEV_<DID>&SUBSYS_*\
```
| Value | Type | Purpose |
|-------|------|---------|
| `DeviceDesc` | REG_SZ | Audio controller friendly name |
| `LocationInformation` | REG_SZ | PCI BDF location (Bus 0, Device 31, Function 3) |
| `SubSystemID` | REG_SZ | Board-level subsystem identifier (varies by OEM/ERB) |

### Feature Detection
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `PlatformId` | REG_DWORD | Platform identifier used by SST driver |
| `AceVersion` | REG_DWORD | ACE IP version (driver-reported) |
| `UaolSupported` | REG_DWORD | 1=UAOL capable (ACE 3.x+) |

---

## ETW / WPP Trace Capture

### Platform Init Trace
```cmd
:: Capture early audio bus init to verify platform detection
logman create trace PlatformAudioInit ^
  -p {GUID-FROM-IntcAudioBus-PDB} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\PlatformAudioInit.etl -mode Circular -nb 16 256
logman start PlatformAudioInit

:: Reboot to capture init sequence, then stop:
logman stop PlatformAudioInit

:: Decode with tracepdb-extracted TMF
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb -p C:\Temp\BusTmf
tracefmt C:\Temp\PlatformAudioInit.etl -tmf C:\Temp\BusTmf -o C:\Temp\PlatformInit.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `PlatformId=` | Driver detected platform type |
| `DeviceId=0x` | PCI DID read by driver |
| `AceVersion=` | ACE generation detected |
| `FeatureMask=` | Enabled audio features bitmask |

---

## Common Failure Modes

### Failure: Wrong platform detected by driver
1. Check PCI DID via `devcon hwids` — does it match expected platform?
2. Check ACPI `_HID` — wrong ACPI tables can cause feature mismatch
3. Check Subsystem ID — OEM boards may have unexpected SSID values
4. Verify BIOS version matches platform (e.g. NVL BIOS on NVL hardware)

### Failure: ACE device missing (DID = 0xFFFF)
1. Check BIOS `AudioController` knob = Enabled
2. Check fuse: `FNCFG.ACED` — if set, ACE is hardware-disabled
3. Check `DSPSD` fuse via PythonSV: `fuse_utils.qdf()`
4. Power cycle and retry — transient PCI enumeration failure

### Failure: Feature mismatch (e.g. UAOL expected but not available)
1. Check ACE version for platform: NVL=ACE4.x, PTL=ACE3.0, LNL=ACE2.x, MTL/ARL=ACE1.5
2. UAOL requires ACE 3.x+; LNL (ACE 2.x) and MTL/ARL (ACE 1.5) do NOT support UAOL
3. AIOC requires ACE 4.x; only NVL and TTL/RZL support Gen6 AIOC

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\platform\`

Key test categories:
- `platform_detect\` — verify DID, ACE version, die variant
- `platform_feature_check\` — verify feature availability per platform
- `platform_bios_knobs\` — validate BIOS audio configuration

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\platform\platform_detect
python run_test.py --verbose
```
