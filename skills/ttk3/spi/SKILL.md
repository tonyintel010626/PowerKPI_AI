---
name: ttk3/spi
description: TTK3 SPI Flash Programming for BIOS/IFWI read, write, erase, program, and verify operations
---

# TTK3 SPI Flash Programming

SPI flash programming interface for BIOS/IFWI operations via the TTK3 hardware tool. Supports chip detection, image loading, erase, program with verification, BIOS version reading, and a batch `flash_bios()` method that combines multiple operations in one call.

## Quick Start

```python
from SPI_Programmer import BiosProgrammer

flash = BiosProgrammer()
try:
    flash.Open()
    chip = flash.DetectChip()
    print(f"Chip: {chip}")
finally:
    flash.Close()
```

## API Reference

### Connection

```python
flash = BiosProgrammer()

# Open default device
flash.Open()

# Open specific device by index
flash.OpenIndex(deviceIndex, deviceType=0)  # deviceType: 0=TTK3, 1=SQUID

# Always close when done
flash.Close()
```

### Chip Operations

```python
flash = BiosProgrammer()
try:
    flash.Open()

    # Detect the SPI flash chip
    chip_info = flash.DetectChip()

    # Select chip (for multi-chip setups)
    flash.SetChipSelect(0)

    flash.Close()
finally:
    flash.Close()
```

### BIOS Programming (Individual Steps)

```python
flash = BiosProgrammer()
try:
    flash.Open()
    flash.DetectChip()

    # Load image from local file
    flash.LoadImage(r"C:\path\to\bios.bin")

    # Or load from IFWI Central
    flash.LoadImageFromIfwiCentral(Id="IFWI-12345", env="production", timeout=300)

    # Erase flash chip
    flash.Erase()

    # Blank check (verify chip is erased)
    flash.BlankCheck()

    # Program and verify in one step
    flash.ProgramAndVerify()

    # Or program and verify separately
    flash.Program()
    flash.Verify()

    # Read BIOS version
    version = flash.ReadBiosVersion(turnOff=True)
    print(f"BIOS Version: {version}")

    # Clear CMOS
    flash.ClearCMOS()

finally:
    flash.Close()
```

### Batch Flash Method (Recommended)

The `flash_bios()` method combines load, erase, program, and verify in one call:

```python
from ttk3_agent_platform.tools.spi_programmer_tool import SPIProgrammerTool
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
spi = SPIProgrammerTool(event_store=event_store, config=None)
try:
    spi.open()
    spi.detect_chip()
    result = spi.flash_bios(r"C:\path\to\bios.bin", chip_select=0)
    # Internally does: SetChipSelect → LoadImage → Erase → ProgramAndVerify
    print(f"Flash result: {result}")
finally:
    spi.close()
```

### Complete Flash Workflow with Error Handling

```python
from SPI_Programmer import BiosProgrammer
from PowerControl import PowerControl
from Port80 import Port80

power = PowerControl()
flash = BiosProgrammer()
port80 = Port80()

try:
    # Step 1: Open power control
    power.OpenPowerSplitter()
    try:
        # Step 2: Power down (CRITICAL before SPI access)
        power.AllPortsOff()

        # Step 2.5: MANDATORY 10-second wait for power to fully discharge
        import time
        time.sleep(10)  # DO NOT reduce — required for reliable SPI access

        # Step 3: Open SPI programmer
        flash.Open()
        try:
            # Step 4: Detect chip
            flash.DetectChip()

            # Step 5: Flash BIOS (load → erase → program → verify)
            flash.SetChipSelect(0)
            flash.LoadImage(r"C:\path\to\bios.bin")
            flash.Erase()
            flash.ProgramAndVerify()

            # Step 6: Power on platform
            power.AllPortsOn()

            # Step 7: Monitor boot
            port80.Open()
            try:
                post_code = port80.Read()
                print(f"POST code: {post_code}")
            finally:
                port80.Close()

        finally:
            # Step 8a: Close SPI
            flash.Close()
    finally:
        # Step 8b: Close power
        power.Close()

except Exception as e:
    print(f"BIOS flash failed: {e}")
    raise
```

## STUB Methods

The following methods are **STUBs** that raise `NotImplementedError`. Their exact TTK3 API signatures need verification against real hardware:

| Method | Status | Notes |
|--------|--------|-------|
| `read_flash(address, length)` | STUB | Raw flash read not in documented API |
| `write_flash(address, data)` | STUB | Raw flash write not in documented API |
| `erase_sector(address)` | STUB | Sector erase not in documented API — use `Erase()` for full chip |
| `read_mac_address()` | STUB | Needs API verification |
| `write_mac_address(mac)` | STUB | Needs API verification |
| `get_ifwi_version()` | STUB | Needs API verification |
| `set_spi_read_mode(mode)` | STUB | Needs API verification |
| `assert_plt_rst()` | STUB | Needs API verification |
| `deassert_plt_rst()` | STUB | Needs API verification |

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| image_path | str | Path to BIOS/IFWI binary file |
| chip_select | int | Chip select index (default: 0) |
| deviceIndex | int | Device index for multi-device setups |
| deviceType | int | Device type: 0=TTK3, 1=SQUID |
| turnOff | bool | Turn off after reading BIOS version |
| Id | str | IFWI Central image identifier |
| env | str | IFWI Central environment |
| timeout | int | Timeout in seconds for IFWI Central download |

## Notes

- **Always power off** the platform before SPI flash operations and **wait at least 10 seconds** before opening the SPI programmer. This mandatory wait ensures power fully discharges and the SPI flash is in a stable state for reliable access.
- Always call `Open()` before operations and `Close()` in a `finally` block
- Uses `SPI_Programmer` module from `C:\SVSHARE\User_Apps\TTK3\API\Python\`
- The `BiosProgrammer` class wraps `TTK3_SpiProgrammer.dll` via ctypes
- All operations emit events via the event store for audit trails

## SPI Flash Programming Lessons (Learned from NVL-S Debug Session)

### When IFWI Reflash is NOT the Solution
- If platform is stuck at FFFF and IFWI reflash succeeds but platform still shows FFFF → **hardware issue**, not firmware
- IFWI reflash fixes: corrupted firmware, bad CMOS settings, bricked BIOS
- IFWI reflash does NOT fix: dead PMC, hardware power delivery failures, silicon defects

### IFWI Central — DO NOT USE
- `LoadImageFromIfwiCentral()` has known API bugs and should **NOT be used**
- Always use `LoadImage()` with a local file path instead

### IFWI Source Priority
1. **Local path**: `C:\SVSHARE\User_Apps\TTK3\Latest` — check here first for pre-staged IFWI binaries
2. **Ask the user** — if no binary found locally, ask the user to provide the IFWI file path

```python
# Correct: Use local file
flash.LoadImage(r"C:\SVSHARE\User_Apps\TTK3\Latest\NVL_S_B0_IFWI.bin")

# WRONG: Do NOT use IFWI Central
# flash.LoadImageFromIfwiCentral(Id="...", env="production", timeout=300)  # BUG — DO NOT USE
```

### Chip Detection Reliability
- `DetectChip()` is reliable and should always be called before any flash operation
- If `DetectChip()` fails, the SPI connection or hardware is bad — do NOT proceed
- Successful `DetectChip()` confirms the SPI bus and flash chip are functional

### ClearCMOS Scope
- `ClearCMOS()` only resets CMOS/NVRAM settings — it does NOT reflash the IFWI
- Use ClearCMOS as a lighter-weight recovery step before attempting full IFWI reflash
- ClearCMOS requires SPI connection (power off → Open → ClearCMOS → Close → power on)
