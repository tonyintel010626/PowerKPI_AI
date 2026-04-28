# Config Checkout — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only ACE PCI enumeration verification, BAR allocation, BIOS knob validation, and ACPI table checks.
> **Platform**: NVL (Novalake), extensible to PTL, LNL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| PCI bus | `pci.sys` | Enumerates ACE at BDF 0:31:3, allocates BARs |
| Intel audio bus | `IntcAudioBus.sys` | Reads PCI config, initializes HDA controller |
| Intel SST | `IntcSmartSound.sys` | Reads DSP BAR (BAR4), loads FW |
| ACPI platform | `ACPI.sys` | Provides `_HID`, `_CRS`, `_DSD` for audio endpoints |

---

## Device Enumeration

### Verify ACE PCI Device
```cmd
:: Check ACE controller at BDF 0:31:3
devcon hwids "PCI\VEN_8086&DEV_D328*"   :: NVL PCD-H
devcon hwids "PCI\VEN_8086&DEV_D228*"   :: NVL PCH-S

:: Check device status (should be OK)
devcon status "PCI\VEN_8086&DEV_D328*"

:: Full PCI details via PowerShell
powershell -c "Get-PnpDevice | Where-Object {$_.InstanceId -like 'PCI\VEN_8086&DEV_D*28*'} | Format-List *"
```

### Verify BAR Allocation
```cmd
:: Check BAR addresses from Device Manager:
:: ACE Properties → Resources tab → Memory Range
:: Expected: BAR0 (HDA MMIO) and BAR4 (DSP MMIO) both assigned non-zero

:: PowerShell: read PCI resource descriptors
powershell -c "(Get-PnpDeviceProperty -InstanceId 'PCI\VEN_8086&DEV_D328&...' -KeyName DEVPKEY_Device_Resources).Data"
```

### Check BIOS Knob Configuration (from OS)
```cmd
:: Verify key BIOS knobs are applied by checking functional state:
:: 1. Audio controller enabled: ACE visible in Device Manager
:: 2. DSP enabled: IntcSmartSound service running
:: 3. SoundWire links enabled: SWD\ devices present
:: 4. HDA link enabled: HDAUDIO\ devices present

:: Quick functional check
devcon status =MEDIA
sc query IntcSmartSound
devcon hwids "HDAUDIO\*"
devcon hwids "SWD\*"
```

---

## Windows Registry Knobs

### PCI Config Shadow
```
HKLM\SYSTEM\CurrentControlSet\Enum\PCI\VEN_8086&DEV_D328&SUBSYS_*&REV_*\<InstanceID>\
```
| Value | Type | Purpose |
|-------|------|---------|
| `ConfigFlags` | REG_DWORD | PCI device configuration flags |
| `LocationInformation` | REG_SZ | BDF location string |

### Audio Controller State
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `DisableHdaLink` | REG_DWORD | 1=disable HDA link (isolate SoundWire-only config) |
| `DisableDsp` | REG_DWORD | 1=skip DSP initialization (HDA-only mode) |
| `ForceCoupledMode` | REG_DWORD | 1=force coupled mode (DSP manages codec directly) |

### ACPI Override (Debug)
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\ACPI\
```
| Value | Type | Purpose |
|-------|------|---------|
| `OverrideDmicCount` | REG_DWORD | Override ACPI-reported DMIC count |
| `OverrideSdwSegments` | REG_DWORD | Override active SoundWire segment mask |

---

## ETW / WPP Trace Capture

### Config Checkout Init Trace
```cmd
:: Capture ACE initialization to verify config
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcAudioBus.pdb -p C:\Temp\BusTmf

logman create trace ConfigCheckout ^
  -p {GUID-IntcAudioBus} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\ConfigCheckout.etl -mode Circular -nb 16 256
logman start ConfigCheckout

:: Reboot to capture full init, then:
logman stop ConfigCheckout
tracefmt C:\Temp\ConfigCheckout.etl -tmf C:\Temp\BusTmf -o C:\Temp\ConfigCheckout.txt
```

### Key Init Events
| Pattern | Meaning |
|---------|---------|
| `BAR0=0x` | HDA MMIO base address |
| `BAR4=0x` | DSP MMIO base address |
| `VID=0x8086 DID=0x` | PCI device identification |
| `GCAP=0x` | Global capabilities register |
| `STATESTS=0x` | Codec presence bitmap |
| `CoupledMode=` | Coupled vs decoupled mode decision |

---

## Common Failure Modes

### Failure: ACE not visible at BDF 0:31:3
1. Check BIOS: `AudioController` must be Enabled
2. Check fuse: `FNCFG.ACED` — if 1, ACE is hardware-disabled
3. Verify platform BIOS matches hardware (wrong BIOS = wrong PCI device table)
4. Power cycle platform and retry PCI scan

### Failure: BAR0 or BAR4 = 0x00000000
1. PCI resource conflict — another device may be consuming the MMIO range
2. Check Windows Event Viewer → System → PCI bus errors
3. Verify BIOS memory map allocates space for audio BARs
4. Try `devcon remove` + `devcon rescan` to force BAR re-allocation

### Failure: DSP not initializing (IntcSmartSound not running)
1. Check `sc query IntcSmartSound` — service must be RUNNING
2. Check BAR4 is non-zero (DSP needs its own MMIO region)
3. Check BIOS: `Audio DSP` = Enabled
4. WPP trace for `FW_LOAD` failure messages

### Failure: Wrong coupled/decoupled mode
1. Check BIOS: `Audio DSP` setting determines mode
   - Enabled = decoupled (DSP manages audio independently)
   - Disabled = coupled (HDA controller manages codec directly)
2. Check `ForceCoupledMode` registry override
3. Verify mode in WPP trace: search for `CoupledMode=`

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\config-checkout\`

Key test categories:
- `pci_enum_check\` — verify VID/DID, BAR0, BAR4, PMCSR, CMD register
- `bios_knob_verify\` — check audio BIOS settings via functional state
- `acpi_table_check\` — verify _HID, _CRS, _DSD for audio devices
- `coupled_decoupled_mode\` — verify DSP mode matches BIOS setting

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\config-checkout\pci_enum_check
python run_test.py --verbose --die pcd
```
