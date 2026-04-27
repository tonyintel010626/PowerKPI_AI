---
name: fv-lpss/ip-config
description: Check LPSS IP configuration, enumeration, and BAR assignment
---

# LPSS IP Configuration and Enumeration

This skill provides procedures to verify LPSS (Low Power Subsystem) IP enumeration on the PCI bus, configuration, and base address register (BAR) assignment.

---

## Overview

LPSS controllers (I2C, I3C, SPI, UART, GPIO) are typically implemented as PCI devices on Intel platforms. Proper enumeration and configuration are prerequisites for functional validation.

**This skill covers:**
1. Verifying LPSS devices appear on PCI bus
2. Checking PCI configuration space (Vendor ID, Device ID, Class Code)
3. Verifying BAR assignment
4. Checking ACPI/BIOS configuration
5. Diagnosing enumeration failures

---

## PCI Configuration Space Basics

Each LPSS controller has a PCI configuration space with standard fields:

| Offset | Field | Description |
|--------|-------|-------------|
| 0x00 | Vendor ID | Should be 0x8086 for Intel |
| 0x02 | Device ID | Unique ID for LPSS controller type |
| 0x04 | Command Register | Controls device access to memory/IO |
| 0x06 | Status Register | Device status flags |
| 0x08 | Revision ID | Silicon revision |
| 0x09 | Class Code | Device class (0x0C for Serial Bus Controllers) |
| 0x10-0x24 | BAR0-BAR5 | Base Address Registers |
| 0x2C | Subsystem Vendor ID | Subsystem vendor |
| 0x2E | Subsystem ID | Subsystem ID |

---

## PythonSV Procedure

### Initialization

```python
import namednodes
import baseaccess

# Initialize ITP and PythonSV
itp.unlock()
sv.refresh()
```

---

## Enumerating LPSS Devices

### Finding LPSS Controllers

**TODO:** Replace with actual LPSS device paths for your platform.

```python
# Search for LPSS PCI devices
# Example search patterns (adjust for your platform):
lpss_devices = namednodes.sv.socket0.pcd.search(
    regexpression="lpss|serialio|i2c|i3c|spi|uart",
    searchType="comp"  # Search for components
)

for device in lpss_devices:
    print(f"Found LPSS Device: {device}")
    print(f"  Path: {device.path}")
```

### Reading PCI Configuration Space

```python
# Example structure (replace with actual paths)
# i2c0_cfg = namednodes.sv.socket0.uncore.lpss.i2c0.cfg

# Read Vendor ID and Device ID
# vendor_id = i2c0_cfg.vendor_id.read()  # Should be 0x8086
# device_id = i2c0_cfg.device_id.read()

# Read Class Code
# class_code = i2c0_cfg.class_code.read()  # Should be 0x0C80xx for I2C

# Read BAR0
# bar0 = i2c0_cfg.bar0.read()

print(f"Vendor ID: 0x{vendor_id:04X}")
print(f"Device ID: 0x{device_id:04X}")
print(f"Class Code: 0x{class_code:06X}")
print(f"BAR0: 0x{bar0:08X}")
```

---

## Per-Port Configuration Checks

### I2C Controllers

**Typical I2C Device IDs (platform-specific):**
- **TODO:** Add actual Device IDs for I2C controllers on your platform

**Configuration checks:**
```python
# For each I2C controller (I2C0, I2C1, I2C2, etc.)

# 1. Verify device is present
# i2c0_vendor = namednodes.sv.socket0.uncore.lpss.i2c0.cfg.vendor_id.read()
# if i2c0_vendor != 0x8086:
#     print("ERROR: I2C0 not enumerated or not Intel device")

# 2. Check Device ID
# i2c0_devid = namednodes.sv.socket0.uncore.lpss.i2c0.cfg.device_id.read()
# print(f"I2C0 Device ID: 0x{i2c0_devid:04X}")

# 3. Verify Class Code (should be Serial Bus Controller - I2C)
# i2c0_class = namednodes.sv.socket0.uncore.lpss.i2c0.cfg.class_code.read()
# Expected: 0x0C8000 or similar

# 4. Check BAR0 assignment
# i2c0_bar0 = namednodes.sv.socket0.uncore.lpss.i2c0.cfg.bar0.read()
# if i2c0_bar0 == 0 or i2c0_bar0 == 0xFFFFFFFF:
#     print("ERROR: I2C0 BAR0 not assigned")

# 5. Check Command Register (Memory Space Enable, Bus Master Enable)
# i2c0_cmd = namednodes.sv.socket0.uncore.lpss.i2c0.cfg.command.read()
# if not (i2c0_cmd & 0x02):  # Bit 1 = Memory Space Enable
#     print("WARNING: I2C0 memory space not enabled")
```

**Repeat for all I2C controllers on the platform.**

---

### I3C Controllers

**Typical I3C Device IDs (platform-specific):**
- **TODO:** Add actual Device IDs for I3C controllers on your platform

**Configuration checks:**
```python
# Similar to I2C, but check for I3C-specific class code
# Expected Class Code: 0x0C8xxx (I3C falls under Serial Bus Controllers)

# TODO: Add actual I3C controller paths and checks
```

---

### SPI Controllers

**Typical SPI Device IDs (platform-specific):**
- **TODO:** Add actual Device IDs for SPI controllers on your platform

**Configuration checks:**
```python
# For each SPI controller

# 1. Verify device present
# 2. Check Device ID
# 3. Verify Class Code (Serial Bus Controller - SPI)
# 4. Check BAR0 assignment
# 5. Verify Memory Space and Bus Master Enable

# TODO: Add actual SPI controller paths and checks
```

---

### UART Controllers

**Typical UART Device IDs (platform-specific):**
- **TODO:** Add actual Device IDs for UART controllers on your platform

**Configuration checks:**
```python
# For each UART controller

# 1. Verify device present
# 2. Check Device ID
# 3. Verify Class Code (Communication Controller - Serial)
# 4. Check BAR0 assignment
# 5. Verify Memory Space Enable

# TODO: Add actual UART controller paths and checks
```

---

### GPIO Controllers

**Typical GPIO Device IDs (platform-specific):**
- **TODO:** Add actual Device IDs for GPIO controllers on your platform

**Configuration checks:**
```python
# For GPIO controller(s)

# 1. Verify device present
# 2. Check Device ID
# 3. Verify Class Code
# 4. Check BAR0 assignment (GPIO may have multiple BARs)
# 5. Check BAR1 if present

# TODO: Add actual GPIO controller paths and checks
```

---

## Common Enumeration Issues

### Issue: Device Not Present (Vendor ID = 0xFFFF)

**Symptoms:**
- Reading Vendor ID returns 0xFFFF or 0x0000
- Device doesn't appear in PCI device tree

**Root Causes:**
1. **Device Fused Off** — Hardware fuse disabled the device
2. **BIOS/ACPI Configuration** — Device hidden or disabled by firmware
3. **PCI Bus Scan Issue** — Bus not properly scanned
4. **Silicon Bug** — Hardware enumeration failure

**Debug Steps:**
```python
# 1. Check device fuses
# TODO: Add fuse register paths
# fuse_reg = namednodes.sv.socket0.uncore.lpss.fuse_config.read()
# Check if device is fused off

# 2. Check BIOS settings
# - Enter BIOS setup and check if LPSS devices are enabled
# - Check ACPI tables for device visibility

# 3. Verify PCI bus configuration
# - Check if parent bridge is configured correctly
# - Verify secondary bus number assignment
```

---

### Issue: BAR Not Assigned (BAR = 0x00000000)

**Symptoms:**
- BAR0 reads as 0x00000000
- Device present but not functional
- Memory access to device fails

**Root Causes:**
1. **BIOS Resource Allocation Failure** — BIOS didn't assign resources
2. **Resource Conflict** — BAR overlaps with another device
3. **BAR Size Negotiation Failure** — BIOS couldn't allocate required size

**Debug Steps:**
```python
# 1. Check if device is enabled
# cmd_reg = device.cfg.command.read()
# if not (cmd_reg & 0x02):
#     print("Device memory space not enabled")

# 2. Read BAR size (write all 1s, read back)
# Original: bar0_original = device.cfg.bar0.read()
# device.cfg.bar0.write(0xFFFFFFFF)
# bar0_size_mask = device.cfg.bar0.read()
# device.cfg.bar0.write(bar0_original)  # Restore
# bar_size = ~bar0_size_mask + 1
# print(f"BAR0 size requirement: {bar_size} bytes")

# 3. Check for resource conflicts in BIOS resource allocation
```

---

### Issue: Wrong Device ID

**Symptoms:**
- Device present but Device ID is unexpected
- Device ID doesn't match datasheet

**Root Causes:**
1. **Wrong Silicon Stepping** — Different stepping has different Device ID
2. **Fused Configuration** — Some configurations change Device ID
3. **Reading Wrong Device** — Incorrect PCI BDF (Bus/Device/Function)

**Debug Steps:**
```python
# 1. Verify you're reading the correct BDF
# Check device path and BDF coordinates

# 2. Cross-reference Device ID with datasheet for your silicon stepping
# revision_id = device.cfg.revision_id.read()
# print(f"Revision ID: 0x{revision_id:02X}")

# 3. Check if device is in a special configuration mode
```

---

### Issue: Device in D3 (Not Accessible)

**Symptoms:**
- Vendor ID reads as 0xFFFF when accessed
- Device was previously enumerated but now appears missing

**Root Causes:**
1. **Device in D3cold** — Device powered off, config space inaccessible
2. **Clock Gated** — Device clocks stopped

**Debug Steps:**
```python
# 1. Check power state
# Use fv-lpss/d3-state-check skill
# pmcsr = device.cfg.pmcsr.read()
# power_state = pmcsr & 0x03
# if power_state == 3:
#     print("Device is in D3")

# 2. Bring device to D0 before reading configuration
# device.cfg.pmcsr.write(0x00)  # Request D0
# Wait for transition
# import time
# time.sleep(0.1)

# 3. Now read configuration
```

---

## ACPI/BIOS Configuration Checks

### ACPI Device Objects

LPSS devices typically have ACPI device objects. Check ACPI tables for:

- Device presence in DSDT
- _STA (Status) method result
- _CRS (Current Resource Settings)
- _DSD (Device Specific Data) for additional properties

**TODO:** Add ACPI table reading procedures or tools specific to your platform.

---

### BIOS Settings

Common BIOS settings affecting LPSS enumeration:

- **LPSS Configuration** — Enable/Disable toggle
- **Serial IO Configuration** — PCI vs ACPI mode
- **DMA Configuration** — DMA controller enable/disable
- **Individual Controller Enable** — Per-controller toggles

**Check:** Enter BIOS setup and verify LPSS devices are enabled.

---

## Verification Checklist

For each LPSS port (I2C, I3C, SPI, UART, GPIO):

- [ ] Device appears in PCI device tree
- [ ] Vendor ID = 0x8086 (Intel)
- [ ] Device ID matches expected value for platform/stepping
- [ ] Class Code is correct for device type
- [ ] BAR0 is assigned (non-zero, not 0xFFFFFFFF)
- [ ] Memory Space Enable bit set in Command Register
- [ ] Device not in D3 (or can be brought to D0 successfully)
- [ ] No resource conflicts with other devices
- [ ] ACPI device object present and enabled
- [ ] BIOS settings enable the device

---

## Related Skills

- **`fv-lpss/register-checkout`** — Read/verify register values after enumeration
- **`fv-lpss/d3-state-check`** — Check if device in D3 causing access issues
- **`fv-lpss/pmode-check`** — Verify pad configuration after enumeration

---

## Complete Example: Verifying I2C0 Enumeration

```python
import namednodes
import baseaccess

# Initialize
itp.unlock()
sv.refresh()

# TODO: Replace with actual I2C0 configuration space path
# i2c0_cfg = namednodes.sv.socket0.uncore.lpss.i2c0.cfg

print("=== I2C0 Enumeration Check ===")

# 1. Read Vendor ID
# vendor_id = i2c0_cfg.vendor_id.read()
# if vendor_id == 0xFFFF or vendor_id == 0x0000:
#     print("ERROR: I2C0 not present")
#     exit(1)
# print(f"Vendor ID: 0x{vendor_id:04X} (Expected: 0x8086)")

# 2. Read Device ID
# device_id = i2c0_cfg.device_id.read()
# print(f"Device ID: 0x{device_id:04X}")

# 3. Read Revision ID
# revision_id = i2c0_cfg.revision_id.read()
# print(f"Revision ID: 0x{revision_id:02X}")

# 4. Read Class Code
# class_code = i2c0_cfg.class_code.read()
# print(f"Class Code: 0x{class_code:06X} (Expected: 0x0C80xx)")

# 5. Read BAR0
# bar0 = i2c0_cfg.bar0.read()
# if bar0 == 0 or bar0 == 0xFFFFFFFF:
#     print("ERROR: BAR0 not assigned")
# else:
#     print(f"BAR0: 0x{bar0:08X}")

# 6. Read Command Register
# command = i2c0_cfg.command.read()
# mem_space_enable = (command >> 1) & 0x01
# bus_master_enable = (command >> 2) & 0x01
# print(f"Command: 0x{command:04X}")
# print(f"  Memory Space Enable: {mem_space_enable}")
# print(f"  Bus Master Enable: {bus_master_enable}")

# 7. Check Power State
# pmcsr = i2c0_cfg.pmcsr.read()
# power_state = pmcsr & 0x03
# power_state_names = {0: "D0", 1: "D1", 2: "D2", 3: "D3"}
# print(f"Power State: {power_state_names.get(power_state, 'Unknown')}")

print("=== Enumeration Check Complete ===")
```

---

## TODO Summary

**Platform-Specific Information Needed:**

1. **PCI Device Paths** — Actual PythonSV paths to LPSS PCI config spaces
2. **Device IDs** — Expected Vendor ID / Device ID for each LPSS controller type and platform
3. **Class Codes** — Expected Class Code values
4. **BAR Requirements** — Expected BAR sizes and types (memory-mapped, I/O-mapped)
5. **Fuse Register Paths** — Paths to check if devices are fused off
6. **ACPI Table Access** — Tools or procedures to read ACPI tables on your platform
7. **BDF Coordinates** — Bus/Device/Function numbers for each LPSS controller

Once this information is available, update the TODO sections with actual values and paths.
