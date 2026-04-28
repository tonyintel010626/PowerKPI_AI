---
name: fv-gbe/enumeration
description: "GbE PCI enumeration, BDF assignment, BAR allocation, ACPI table validation, and device tree verification for Intel I219 and I226/I225 controllers."
disable: false
---

# Skill: fv-gbe/enumeration

## Overview

This skill covers PCI enumeration verification for Intel GbE controllers (I219 and I226/I225) on Intel Client SoC platforms. The I219 is integrated into the PCH/SoC and always appears at a fixed BDF, while the I226/I225 is a discrete PCIe device behind a root port.

---

## I219 (CNPi) Enumeration

### Expected BDF
The I219 MAC is always at **Bus 0, Device 31, Function 6** = `00:1F.6`.

This is fixed in the PCH and does not change across platforms.

### PCI Config Space (I219)

| Field | Expected Value |
|-------|----------------|
| Vendor ID | `0x8086` |
| Class Code | `0x020000` (Ethernet Controller) |
| Header Type | `0x00` |
| BAR0 | 32-bit MMIO, 128KB aligned |
| BAR1 | I/O BAR (legacy, may be unused) |
| Subsystem Vendor | Platform/OEM specific |

### Device ID Reference (I219)

| Platform | SKU | Device ID |
|----------|-----|-----------|
| MTL | I219-LM | 0x550A |
| MTL | I219-V  | 0x550B |
| LNL | I219-LM | 0x7F0C |
| LNL | I219-V  | 0x7F0D |
| ARL | I219-LM | 0xA80D |
| ARL | I219-V  | 0xA80E |
| PTL | TBD | TBD |
| NVL | TBD | TBD |

> Confirm PTL/NVL Device IDs from the platform HAS/BIOS spec when available.

### Windows Verification (I219)

```powershell
# Check device enumeration in Device Manager
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*I219*" -or $_.FriendlyName -like "*Ethernet*" }

# Check PCI config via devcon or lspci equivalent
pnputil /enum-devices /class Net

# Check via WMI
Get-WmiObject Win32_NetworkAdapter | Where-Object { $_.Name -like "*Intel*" } | Select-Object Name, DeviceID, PNPDeviceID
```

Expected PNP Device ID pattern: `PCI\VEN_8086&DEV_550A&...` (MTL I219-LM example)

### Linux Verification (I219)

```bash
# Check enumeration
lspci -d 8086: -nn | grep Ethernet

# Check BDF 00:1f.6 specifically
lspci -s 00:1f.6 -vvv

# Check driver binding
ls -la /sys/bus/pci/devices/0000:00:1f.6/driver

# Check BAR allocation
cat /sys/bus/pci/devices/0000:00:1f.6/resource
```

### PythonSV Verification (I219)

```python
# Access GbE device via PythonSV
import pysvtools.xmlcli.XmlCli as cli

# Named node for I219 on MTL (example — confirm per platform)
sv.socket0.pcieB0D31F6.vid.read()   # Should return 0x8086
sv.socket0.pcieB0D31F6.did.read()   # Should return platform-specific DID
sv.socket0.pcieB0D31F6.cc.read()    # Should return 0x020000

# Read BAR0 (MMIO base address)
bar0 = sv.socket0.pcieB0D31F6.bar0.read()
print(f"BAR0 = 0x{bar0:08X}")
```

---

## I226 / I225 Enumeration

### Overview
The I226/I225 is a discrete PCIe Gen3 x1 device behind a PCIe Root Port. Its BDF depends on which root port it connects to — this is board-specific.

### PCI Config Space (I226)

| Field | Expected Value |
|-------|----------------|
| Vendor ID | `0x8086` |
| Device ID (I226-LM) | `0x125B` |
| Device ID (I226-V)  | `0x125C` |
| Device ID (I225-LM) | `0x15F2` |
| Device ID (I225-V)  | `0x15F3` |
| Class Code | `0x020000` |
| BAR0 | 64-bit MMIO, 1MB aligned |
| BAR3 | 64-bit MMIO (flash region) |

### Windows Verification (I226)

```powershell
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*I226*" -or $_.FriendlyName -like "*2.5GbE*" }
```

### Linux Verification (I226)

```bash
# Find I226 by device ID
lspci -d 8086:125b -vvv   # I226-LM
lspci -d 8086:125c -vvv   # I226-V

# Check driver
ls -la /sys/bus/pci/devices/*/driver | grep igc
```

---

## ACPI Table Validation

### I219 ACPI (\_SB.PCI0.GLAN or \_SB.PC00.GLAN)

The I219 should have an ACPI device node. Verify:

```
\_SB.PCI0.GLAN  (or \_SB.PC00.GLAN on newer platforms)
  - _ADR = 0x001F0006  (Device 31, Function 6)
  - _PRW method (power resources for wake)
  - _DSM methods (device specific methods)
```

**Windows:**
```powershell
# Dump ACPI namespace
acpidump.exe -o acpi.txt
# Search for GLAN node
Select-String "GLAN" acpi.txt
```

**Linux:**
```bash
cat /sys/bus/acpi/devices/*/path | grep -i glan
acpidump | acpixtract -a; iasl -d *.dat; grep -i "GLAN\|1F0006" DSDT.dsl
```

---

## Common Enumeration Failures

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| Device not found at 00:1F.6 | `LanEnable` BIOS knob = Disabled | Check BIOS setup → Advanced → PCH Configuration → LAN |
| Device found but no driver | Missing INF, wrong OS driver | Check Device Manager for yellow bang |
| BAR0 = 0x00000000 | PCI enumeration failed or resource conflict | Check BIOS MMIO resource allocation |
| Unexpected Device ID | Wrong BIOS/FW version, fuse issue | Verify IFWI version, check fuse reads |
| Device present but link down | PHY not initialized | Check → `/skill fv-gbe/phy-bringup` |

---

## Simics Pre-Silicon Notes

- I219 is modeled in Simics PCH models. Verify model version supports target platform.
- BAR0 access may be limited in simulation — confirm with model team.
- `lspci` equivalent in Simics: use SIMICS CLI `pci.status` or Python transactor.
- Device IDs in simulation may differ from final silicon — always check model changelog.
