---
name: ttk3/power
description: TTK3 Power Control for ATX, PowerSplitter, and PDU management
---

# TTK3 Power Control

Power management interface supporting three power source types: ATX power supply, PowerSplitter, and PDU (Power Distribution Unit). Provides per-port control, state monitoring, and power cycling.

## Quick Start

```python
from PowerControl import PowerControl

power = PowerControl()
try:
    power.OpenPowerSplitter()
    power.AllPortsOn()
    state = power.GetPortState(1)
    print(f"Port 1 state: {state}")
finally:
    power.Close()
```

## Power Source Selection

Agents MUST specify which power interface to use. Two supported options:

| Source | Method | Default |
|--------|--------|---------|
| **PowerSplitter** | `power.OpenPowerSplitter()` | YES — use if unspecified |
| **ATX** | `power.OpenATX()` | No |

If unspecified, default to PowerSplitter. The orchestrator should ask the user which interface their system is configured with before delegating power tasks.

```python
# Select power source based on configuration
if power_source == "ATX":
    power.OpenATX()
else:
    power.OpenPowerSplitter()  # default
```

## API Reference

### Opening Power Sources

```python
power = PowerControl()

# Open PowerSplitter (most common for lab setups — default)
power.OpenPowerSplitter()  # No arguments

# Open ATX power supply
power.OpenATX()  # No arguments

# Always close when done
power.Close()
```

### Port Control

```python
power = PowerControl()
try:
    power.OpenPowerSplitter()

    # Single port control
    power.PortOn(1)
    power.PortOff(1)

    # All ports
    power.AllPortsOn()
    power.AllPortsOff()

    # Get individual port state
    state = power.GetPortState(1)

finally:
    power.Close()
```

### Power Cycle with Error Handling

```python
import time
from PowerControl import PowerControl
from Port80 import Port80

power = PowerControl()
port80 = Port80()

try:
    power.OpenPowerSplitter()
    try:
        # Power off
        power.AllPortsOff()
        time.sleep(5)

        # Power on
        power.AllPortsOn()

        # Monitor boot
        port80.Open()
        try:
            post_code = port80.Read()
            print(f"POST code after power cycle: {post_code}")
        finally:
            port80.Close()

    finally:
        power.Close()

except Exception as e:
    print(f"Power cycle failed: {e}")
    raise
```

## STUB Methods

The following methods are **STUBs** that raise `NotImplementedError`:

| Method | Status | Notes |
|--------|--------|-------|
| `get_all_port_states()` | STUB | Needs API verification |
| `get_num_ports()` | STUB | Needs API verification |
| `get_device_serial_num()` | STUB | Needs API verification |
| `get_device_type()` | STUB | Needs API verification |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| portNum | int | - | Port number for single port operations |
| ip | str | - | PDU IP address |
| user | str | - | PDU username |
| pw | str | - | PDU password |
| ports | list[int] | - | PDU port list |

## Notes

- PowerSplitter is the most common for lab bench setups
- `OpenPowerSplitter()` and `OpenATX()` take **no arguments**
- PDU requires network connectivity and credentials
- **Always** call `Close()` in a `finally` block to release the device handle
- Uses `PowerControl` module from `C:\SVSHARE\User_Apps\TTK3\API\Python\`
- The `PowerControl` class wraps `TTK3_PowerControl.dll` via ctypes

## Power Sequencing Best Practices (Learned from NVL-S Debug Session)

### Minimum Wait Times
- **All power off/on transitions require a minimum 10-second wait time**
- This applies to: G3 power cycles, pre-flash power-off, post-flash power-on
- Shorter waits risk incomplete power rail discharge or unstable power-on

```python
# Correct G3 power cycle
power.AllPortsOff()
time.sleep(10)   # MINIMUM 10 seconds — do not reduce
power.AllPortsOn()
time.sleep(10)   # Wait for power stabilization before reading POST codes
```

### Known Behaviors
- `AllPortsOn()` turning on all ports simultaneously is **normal and expected** — this is NOT a problem
- PowerSplitter `GetPortState()` is reliable for verifying port state after operations

### What Does NOT Work for Recovery
- **Staged power sequencing** (turning on ports one at a time with delays) — not a valid recovery technique
- **Power pulse recovery** (rapid on/off/on sequences) — not a valid recovery technique
- These were tested during debug and provide no benefit over standard G3 power cycling

### G3 Power Cycle Pattern for Recovery
```python
# Standard G3 recovery cycle (repeat up to 3 times)
for attempt in range(3):
    power.AllPortsOff()
    time.sleep(10)
    power.AllPortsOn()
    time.sleep(10)
    post_code = port80.Read()
    if post_code != "FFFF":
        break
```

## CLI Power Control Scripts

Pre-built standalone scripts for power operations. All scripts auto-detect the first available TTK3 device, or accept `--serial` to target a specific device. All output JSON to stdout for agent parsing.

| Script | Usage | Description |
|--------|-------|-------------|
| `power_cycle.py` | `python power_cycle.py [--source splitter] [--delay 3]` | Standard power cycle (existing, configurable delay, default 3s) |
| `advanced_power_cycle.py` | `python advanced_power_cycle.py [--serial SN] [--delay 15]` | Hard cold boot with 15s capacitor drain delay for full recovery scenarios |
| `power_off.py` | `python power_off.py [--serial SN]` | Power OFF all PowerSplitter ports with per-port verification |
| `power_on.py` | `python power_on.py [--serial SN] [--delay 2]` | Power ON all ports with configurable stabilization delay (default 2s for UART capture) |
| `verify_power.py` | `python verify_power.py [--serial SN]` | Quick read-only port state verification (no state changes) |
| `port_control.py` | `python port_control.py --action on --port 1` | Individual port control (existing) |

### Running Power Control Scripts

```bash
# Quick power state check
python .opencode/skill/ttk3/power/verify_power.py

# Simple power off / power on
python .opencode/skill/ttk3/power/power_off.py
python .opencode/skill/ttk3/power/power_on.py

# Standard power cycle (3s delay)
python .opencode/skill/ttk3/power/power_cycle.py --source splitter --delay 3

# Hard cold boot for recovery (15s capacitor drain)
python .opencode/skill/ttk3/power/advanced_power_cycle.py --delay 15

# Target a specific TTK3 device
python .opencode/skill/ttk3/power/power_off.py --serial 883001B0916
```

### Script Output Format

All power scripts output JSON to stdout:

```json
{
  "status": "success",
  "action": "power_off",
  "device_serial": "883001B0916",
  "ports": {
    "1": "OFF",
    "2": "OFF",
    "3": "OFF",
    "4": "OFF"
  }
}
```

### When to Use Which Power Script

| Scenario | Recommended Script |
|----------|--------------------|
| Pre-SPI flash operations | `power_off.py` |
| Post-SPI flash boot | `power_on.py` |
| Quick test cycle | `power_cycle.py` (3s delay) |
| Recovery from POST FFFF | `advanced_power_cycle.py` (15s delay) |
| Verify current state only | `verify_power.py` |
| Single port control | `port_control.py` |
