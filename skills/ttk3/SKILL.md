---
name: ttk3
description: TTK3 hardware validation platform for Intel test equipment programming and debugging
---

# TTK3 Hardware Validation Platform

TTK3 (Test Tool Kit v3) provides comprehensive hardware programming, debugging, and validation capabilities for Intel platforms. It interfaces with TTK3/SQUID USB devices to perform SPI flash programming, power control, I2C/UART communication, GPIO monitoring, POST code tracking, HID emulation, eMMC programming, and advanced operations (JTAG, Retimer, PD, MCU, IFWI, NVM).

## Quick Start

```python
import sys
sys.path.insert(0, r"C:\SVSHARE\User_Apps\TTK3\API\Python")

from Ttk3Device import Ttk3Device
from SPI_Programmer import BiosProgrammer
from PowerControl import PowerControl

# Discover connected devices
device = Ttk3Device()
try:
    device.Open()
    num_devices = device.GetNumConnectedDevices()
    print(f"Found {num_devices} TTK3 device(s)")
finally:
    device.Close()

# Flash a BIOS image
power = PowerControl()
flash = BiosProgrammer()
try:
    power.OpenPowerSplitter()
    try:
        power.AllPortsOff()
        flash.Open()
        try:
            flash.DetectChip()
            flash.SetChipSelect(0)
            flash.LoadImage(r"C:\path\to\bios.bin")
            flash.Erase()
            flash.ProgramAndVerify()
            power.AllPortsOn()
        finally:
            flash.Close()
    finally:
        power.Close()
except Exception as e:
    print(f"Flash failed: {e}")
    raise
```

## Error Handling Best Practices

### Rule: Every `open()` MUST have a corresponding `close()` in a `finally` block

All TTK3 hardware resources (SPI, Power, I2C, Port80, UART, GPIO, Device) hold device handles that must be released. Failure to call `close()` can leave the device in an unusable state.

### Pattern: Nested try/finally

```python
# Open resources in order, close in REVERSE order (LIFO)
resource_a.Open()
try:
    resource_b.Open()
    try:
        # ... operations ...
    finally:
        resource_b.Close()  # Close inner resource first
finally:
    resource_a.Close()      # Close outer resource last
```

### Pattern: Single resource with error handling

```python
resource = SomeClass()
try:
    resource.Open()
    # ... operations ...
finally:
    resource.Close()
```

### LIFO Cleanup Order

Resources must be closed in **reverse order** of opening:

| Open Order | Close Order |
|------------|-------------|
| 1. Power (first) | 3. Power (last) |
| 2. SPI (second) | 2. SPI (second) |
| 3. Port80 (last) | 1. Port80 (first) |

## Available Subskills

| Subskill | Description | Load Command |
|----------|-------------|--------------|
| `ttk3/spi` | SPI flash programming - BIOS/IFWI read/write/erase/program/verify | `/skill ttk3/spi` |
| `ttk3/power` | Power control - ATX, PowerSplitter, PDU management | `/skill ttk3/power` |
| `ttk3/i2c` | I2C bus operations - read/write with clock speed control | `/skill ttk3/i2c` |
| `ttk3/gpio` | GPIO control - pin read/write, sleep state, platform status | `/skill ttk3/gpio` |
| `ttk3/postcode` | POST code monitoring - Port80 boot sequence tracking | `/skill ttk3/postcode` |
| `ttk3/uart` | UART serial debug - read/write/capture with baud control | `/skill ttk3/uart` |
| `ttk3/hid` | HID emulation - keyboard and mouse input simulation | `/skill ttk3/hid` |
| `ttk3/emmc` | eMMC programming - sector/user area/boot partition access | `/skill ttk3/emmc` |
| `ttk3/device` | Device discovery - TTK3/SQUID detection, serial numbers, FW/HW info | `/skill ttk3/device` |
| `ttk3/advanced` | Advanced programming - JTAG, Retimer, PD, MCU, Bootloader, NVM, CutOff | `/skill ttk3/advanced` |
| `ttk3/ifwi` | IFWI Central - image lifecycle, search, validate, export | `/skill ttk3/ifwi` |
| `ttk3/provisioning` | Full platform provisioning - end-to-end IFWI flash workflow | `/skill ttk3/provisioning` |
| `ttk3/diagnostics` | Flash diagnostics - SPI health checks and scoring | `/skill ttk3/diagnostics` |
| `ttk3/boot` | Boot validation - POST code sequence validation | `/skill ttk3/boot` |

## Common Use Cases

### Discover Connected TTK3 Devices

```python
from Ttk3Device import Ttk3Device

device = Ttk3Device()
try:
    device.Open()
    count = device.GetNumConnectedDevices()
    for i in range(count):
        serial = device.GetDeviceSeriaNumberByIndex(i)
        print(f"Device {i}: serial={serial}")
    fw = device.GetFirmwareRevision()
    hw = device.GetHardwareRevision()
    print(f"FW: {fw}, HW: {hw}")
finally:
    device.Close()
```

### Flash BIOS with Full Error Handling

```python
from SPI_Programmer import BiosProgrammer
from PowerControl import PowerControl
from Port80 import Port80

power = PowerControl()
flash = BiosProgrammer()
port80 = Port80()

try:
    power.OpenPowerSplitter()
    try:
        power.AllPortsOff()
        flash.Open()
        try:
            flash.DetectChip()
            flash.SetChipSelect(0)
            flash.LoadImage(r"C:\path\to\bios.bin")
            flash.Erase()
            flash.ProgramAndVerify()
            power.AllPortsOn()
            port80.Open()
            try:
                post_code = port80.Read()
                print(f"POST code: {post_code}")
            finally:
                port80.Close()
        finally:
            flash.Close()
    finally:
        power.Close()
except Exception as e:
    print(f"BIOS flash failed: {e}")
    raise
```

### I2C Device Scanning

```python
from I2cControl import I2cControl

i2c = I2cControl()
try:
    i2c.Open()
    i2c.SetClock(400)  # 400 KHz
    for addr in range(0x08, 0x78):
        try:
            data = i2c.Read(addr, 1)
            if data:
                print(f"Device found at 0x{addr:02X}")
        except Exception:
            pass
finally:
    i2c.Close()
```

## CLI Scripts (Ready for Hardware Testing)

Pre-built executable scripts for common TTK3 operations. Each script handles `sys.path` setup, error handling with `try/finally`, and outputs JSON to stdout.

| Script | Usage | Description |
|--------|-------|-------------|
| `ttk3/spi/flash_bios.py` | `python flash_bios.py --image <path> [--power-off-first]` | Full BIOS flash: power off, detect chip, load image, erase, program+verify, power on |
| `ttk3/spi/detect_chip.py` | `python detect_chip.py [--read-bios-version]` | Detect SPI flash chip, optionally read BIOS version |
| `ttk3/power/power_cycle.py` | `python power_cycle.py --source splitter [--delay 5]` | Power cycle via splitter, ATX, or PDU |
| `ttk3/power/port_control.py` | `python port_control.py --action on --port 1` | Control individual power ports (on/off/status/all-on/all-off) |
| `ttk3/postcode/read_postcode.py` | `python read_postcode.py` | Read current POST code from Port80 |
| `ttk3/postcode/monitor_boot.py` | `python monitor_boot.py --timeout 120 [--target-code 00B1]` | Poll POST codes until target code or timeout |
| `ttk3/device/detect_devices.py` | `python detect_devices.py [--verbose]` | Enumerate connected TTK3/SQUID devices with serial numbers |
| `ttk3/diagnostics/comprehensive_diagnostics.py` | `python comprehensive_diagnostics.py [--serial SN] [--output result.json]` | Full device + SPI health check with scoring and FFFF root cause assessment |
| `ttk3/diagnostics/enhanced_diagnostics.py` | `python enhanced_diagnostics.py [--serial SN] [--keep-power-off]` | Power-aware diagnostics: powers down before SPI access |
| `ttk3/diagnostics/interface_check.py` | `python interface_check.py [--serial SN]` | Pre-flight validation of all TTK3 interfaces |
| `ttk3/power/advanced_power_cycle.py` | `python advanced_power_cycle.py [--serial SN] [--delay 15]` | Hard cold boot with 15s capacitor drain for recovery |
| `ttk3/power/power_off.py` | `python power_off.py [--serial SN]` | Power OFF all ports with verification |
| `ttk3/power/power_on.py` | `python power_on.py [--serial SN] [--delay 2]` | Power ON all ports with stabilization delay |
| `ttk3/power/verify_power.py` | `python verify_power.py [--serial SN]` | Quick power state verification (read-only) |

### Running Scripts

Scripts must be run from the skill directory or with full path:

```bash
# From repo root
python .opencode/skill/ttk3/device/detect_devices.py --verbose
python .opencode/skill/ttk3/spi/flash_bios.py --image "C:\SVSHARE\User_Apps\TTK3\Latest\bios.bin" --power-off-first
python .opencode/skill/ttk3/postcode/monitor_boot.py --timeout 120 --target-code 00B1
```

### Script Output Format

All scripts output JSON to stdout for agent parsing:

```json
{"status": "success", "post_code": "00B1", "elapsed_seconds": 45.2}
{"status": "error", "error": "No TTK3 device connected"}
```

## Architecture

The TTK3 platform follows a three-tier architecture:

1. **Tools** (`ttk3_agent_platform/tools/`) — Direct hardware interface wrappers around TTK3 DLL modules
2. **Skills** (`ttk3_agent_platform/skills/`) — Multi-step workflows combining multiple tools
3. **Agents** (`ttk3_agent_platform/agents/`) — AI-driven orchestrators that plan and execute tasks

All tools use lazy module loading from `C:\SVSHARE\User_Apps\TTK3\API\Python\` and emit events via SQLite event sourcing for full audit trails.

## STUB Methods

Some tool methods are **STUBs** that raise `NotImplementedError` because their exact TTK3 API signatures have not been verified against real hardware. See individual subskill documentation for details on which methods are stubs.

## Configuration

```python
from ttk3_agent_platform.config.settings import TTK3Config, get_config

config = get_config()
config.ttk3_base_path = r"C:\SVSHARE\User_Apps\TTK3"
config.default_power_source = "power_splitter"
config.i2c_speed = 400000
config.uart_baud_rate = 115200
config.save_config()
```

## Requirements

- Windows OS with TTK3 drivers installed
- TTK3/SQUID USB device connected
- TTK3 API at `C:\SVSHARE\User_Apps\TTK3\API\Python\`
- Python 3.8+

## Multi-Interface Debug Strategy (Learned from NVL-S Debug Session)

### Validated vs Unvalidated Interfaces
Before using any TTK3 interface, check its validation status:

| Interface | Module | Status | Key Limitations |
|-----------|--------|--------|-----------------|
| SPI Flash | `BiosProgrammer` | **VALIDATED** | Full workflow works: Open, DetectChip, LoadImage, Erase, ProgramAndVerify, ClearCMOS |
| POST Code | `Port80` | **VALIDATED** | Open, Read, ReadAsync, SubscribePort80ChangedEvent, RequestStop, Close all work |
| Power Control | `PowerControl` | **VALIDATED** | OpenPowerSplitter, AllPortsOn/Off, PortOn/Off, GetPortState work |
| Device Info | `Ttk3Device` | **VALIDATED** | Open, GetNumConnectedDevices, GetFirmwareRevision, GetHardwareRevision work |
| UART | `BiosLog` | **NOT VALIDATED** | Only BiosLogEnable/BiosLogDisable exist. No serial console Open/Read/Write |
| I2C | `I2cControl` | **NOT VALIDATED** | Do not use until validated on real hardware |
| GPIO | `GpioControl` | **NOT VALIDATED** | Constructor bug with _controller parameter. Do not use |
| JTAG | — | **NOT VALIDATED** | Do not use |
| IFWI Central | `BiosProgrammer` | **NOT VALIDATED** | `LoadImageFromIfwiCentral()` has API bugs. Use `LoadImage()` with local file |

### TTK3 vs DBC Debug Capabilities
| Capability | TTK3 | DBC (PySV/IPC) |
|------------|------|-----------------|
| SPI flash programming | Yes | No |
| POST code monitoring | Yes | No |
| Power control | Yes | No |
| Register read/write | No | Yes (requires SUT powered on + booted past FFFF) |
| PMC debug | No | Yes (requires DBC probe connected) |
| Bootstall/DAM | No | Yes |

### Local IFWI Source
- Pre-staged IFWI binaries: `C:\SVSHARE\User_Apps\TTK3\Latest`
- Always check this path first before asking user or attempting network downloads
- Do NOT use IFWI Central API (`LoadImageFromIfwiCentral`) — known bugs

### API Version Differences
- `Detect_Connected_Devices` module is **Linux-only** — fails on Windows
- Use `Ttk3Device` class for Windows-based device discovery
- TTK3 API path: `C:\SVSHARE\User_Apps\TTK3\API\Python\`
- Always add this path to `sys.path` before importing TTK3 modules

## AI Agent Quick Reference

For a comprehensive reference guide on TTK3 operations optimized for AI agents, see:
- **Reference document**: `ttk3/reference/ai_agent_quick_reference.md`
- Covers: SPI flash workflows, CLI usage patterns, programmatic API, best practices, troubleshooting, and platform notes
