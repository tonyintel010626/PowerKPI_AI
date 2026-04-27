---
name: ttk3/provisioning
description: TTK3 Full Platform Provisioning for end-to-end platform setup workflow
---

# TTK3 Full Platform Provisioning

End-to-end platform provisioning workflow that orchestrates device discovery, health checks, BIOS flashing, MAC/serial number programming, and boot validation into a single automated sequence.

## Quick Start

```python
from ttk3_agent_platform.skills.full_platform_provisioning_skill import FullPlatformProvisioningSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = FullPlatformProvisioningSkill(tools)
result = await skill.execute({
    "ifwi_id": "IFWI-12345",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "serial_number": "SN123456789"
})
print(f"Provisioning {'succeeded' if result.success else 'failed'}")
```

## Workflow Steps

The provisioning skill executes these steps in order:

1. **Device Discovery** — Detect connected TTK3 devices and verify readiness
2. **Pre-Flash Health Check** — Run flash diagnostics before programming
3. **Power Off** — Safely power down the platform
4. **Load Image** — Fetch IFWI image from IFWI Central or local path
5. **Program BIOS** — Flash the BIOS/IFWI image via SPI
6. **Verify** — Verify the programmed image integrity
7. **Write MAC Address** — Program the network MAC address (optional)
8. **Write Serial Number** — Program the device serial number (optional)
9. **Power On** — Power the platform back on
10. **Boot Validation** — Monitor POST codes to confirm successful boot

## Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| ifwi_id | str | None | Yes* | IFWI Central image ID |
| image_path | str | None | Yes* | Local BIOS binary path |
| verify | bool | True | No | Verify after programming |
| mac_address | str | None | No | MAC address to program (AA:BB:CC:DD:EE:FF) |
| serial_number | str | None | No | Serial number to program |
| boot_timeout | int | 180 | No | Boot monitoring timeout in seconds |

*Either `ifwi_id` or `image_path` must be provided.

## Example: Full Provisioning from IFWI Central

```python
result = await skill.execute({
    "ifwi_id": "IFWI-12345",
    "verify": True,
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "serial_number": "SN123456789",
    "boot_timeout": 180
})

if result.success:
    steps = result.data.get("steps", {})
    for step_name, step_result in steps.items():
        print(f"  {step_name}: {'PASS' if step_result.get('success') else 'FAIL'}")
```

## Example: Provisioning from Local Image

```python
result = await skill.execute({
    "image_path": r"C:\images\bios_release.bin",
    "verify": True,
    "boot_timeout": 120
})
```

## Tools Used

- `DeviceManagerTool` — Device discovery and readiness
- `SPIProgrammerTool` — SPI flash operations
- `PowerControlTool` — Power management
- `IFWICentralTool` — Image loading from IFWI Central
- `PostCodeTool` — Boot monitoring

## Notes

- The workflow stops and reports failure at the first failing step
- MAC and serial number programming are optional steps
- Pre-flash health check ensures the flash chip is in a good state before programming
- Boot timeout should be generous enough for the target platform's boot sequence

---

## IFWI Flash Workflow

This section documents the complete IFWI (Integrated Firmware Image) flash procedure using TTK3 hardware tools, including proper error handling and resource cleanup.

### IFWI File Location

```
C:\SVSHARE\User_Apps\TTK3\Latest\
```

This folder contains previously tested working IFWI images. Example filename:

```
LatestWorkingBios_LatestWorkingBios_NVL_HR11_A1A0-ODCA_CPRF_SEP0_015F0418_2026WW04.2.02_Acode178_Ucode8000000b_Socc7016_SSTKnobs_LpMode_dis_DVFSPatch.bin
```

### Workflow Steps (8 Steps)

| Step | Action | API Method | On Error |
|------|--------|------------|----------|
| 1 | Open power control | `power.open_power_splitter()` | Exit — no cleanup needed |
| 2 | Power down platform (**CRITICAL**) | `power.all_ports_off()` | `power.close()` then exit |
| 3 | Open SPI programmer | `spi.open()` | `power.close()` then exit |
| 4 | Detect flash chip | `spi.detect_chip()` | `spi.close()` → `power.close()` then exit |
| 5 | Flash BIOS (batch) | `spi.flash_bios(image_path)` | `spi.close()` → `power.close()` then exit |
| 6 | Power on platform | `power.all_ports_on()` | `spi.close()` → `power.close()` then exit |
| 7 | Monitor boot (POST codes) | `port80.open()` → `port80.monitor_boot()` | `port80.close()` → `spi.close()` → `power.close()` then exit |
| 8 | Close all resources | `port80.close()` → `spi.close()` → `power.close()` | — |

> **Note:** Step 5 uses `spi.flash_bios(image_path)` which is a batch method that performs `load_image()` → `erase()` → `program_and_verify()` in a single call.

> **CRITICAL:** The platform **MUST** be powered off (Step 2) before SPI flash operations. Attempting to flash while the platform is powered on will result in "Failed to erase the chip" errors.

### Complete Code Example with Error Handling

```python
import sys
sys.path.insert(0, r'C:\SVSHARE\User_Apps\TTK3\API\Python')

from SPI_Programmer import BiosProgrammer
from PowerControl import PowerControl
from Port80 import Port80

ifwi_path = r"C:\SVSHARE\User_Apps\TTK3\Latest\LatestWorkingBios_LatestWorkingBios_NVL_HR11_A1A0-ODCA_CPRF_SEP0_015F0418_2026WW04.2.02_Acode178_Ucode8000000b_Socc7016_SSTKnobs_LpMode_dis_DVFSPatch.bin"

# Step 1: Open power control
power = PowerControl()
try:
    power.OpenPowerSplitter()
except Exception as e:
    print(f"FATAL: Cannot open power control: {e}")
    raise

try:
    # Step 2: Power down platform (CRITICAL - must be off for SPI access)
    power.AllPortsOff()
    print("Platform powered off")

    # Step 3: Open SPI programmer
    flash = BiosProgrammer()
    flash.Open()

    try:
        # Step 4: Detect flash chip
        flash.DetectChip()
        print("Flash chip detected")

        # Step 5: Flash BIOS (batch: load → erase → program & verify)
        flash.SetChipSelect(0)
        flash.LoadImage(ifwi_path)
        flash.Erase()
        result = flash.ProgramAndVerify()
        print(f"IFWI flash complete: {result}")

        # Step 6: Power on platform
        power.AllPortsOn()
        print("Platform powered on")

        # Step 7: Monitor boot via POST codes
        port80 = Port80()
        try:
            port80.Open(deviceType=0)
            post_code = port80.Read()
            print(f"POST code: {post_code}")
        except Exception as e:
            print(f"WARNING: POST code monitoring failed: {e}")
        finally:
            port80.Close()

    except Exception as e:
        print(f"ERROR during flash operation: {e}")
        raise

    finally:
        # Always close SPI programmer
        flash.Close()
        print("SPI programmer closed")

finally:
    # Always close power control
    power.Close()
    print("Power control closed")
```

### Resource Cleanup Order (LIFO)

Resources are closed in **reverse order** of opening. Every `open()` must have a corresponding `close()` in a `finally` block.

| Open Order | Resource | Close Order |
|------------|----------|-------------|
| 1st opened | `power.OpenPowerSplitter()` | Last closed — `power.Close()` |
| 2nd opened | `flash.Open()` | 2nd closed — `flash.Close()` |
| 3rd opened | `port80.Open()` | 1st closed — `port80.Close()` |

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to erase the chip" | Platform is powered on during SPI flash | Power off the platform before flashing (Step 2) |
| "SPI communication failure" | TTK3 not connected or cables loose | Verify TTK3 device is detected, check physical SPI connections |
| "Chip not detected" | Wrong chip select or no flash chip present | Try different `chip_select` value, verify SPI cable to flash chip |
| "POST code timeout" | Platform not booting after flash | Verify IFWI image, re-flash with known-good image from `C:\SVSHARE\User_Apps\TTK3\Latest\` |
| "Power control open failed" | TTK3 power splitter not connected | Check TTK3-to-power-splitter USB connection |

### Safety Notes

1. **Always power off** the platform before SPI flash operations
2. **Verify IFWI file integrity** before flashing
3. **Do not interrupt** the flash process once started
