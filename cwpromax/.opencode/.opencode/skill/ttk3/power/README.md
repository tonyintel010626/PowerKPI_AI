# TTK3 Power Control Scripts

Standalone power control scripts for TTK3 ATX PowerSplitter operations. All scripts auto-detect the first available TTK3 device by default.

## Scripts

### power_off.py - Power OFF All Ports

Turns off all ATX PowerSplitter ports with state verification.

```bash
python power_off.py
python power_off.py --serial 883001B0916
```

### power_on.py - Power ON All Ports

Turns on all ATX PowerSplitter ports with configurable stabilization delay.

```bash
# Default 2-second delay (allows UART capture to initialize)
python power_on.py

# Custom delay
python power_on.py --delay 5

# Specify device
python power_on.py --serial 883001B0916
```

### verify_power.py - Check Power State

Quick verification of current PowerSplitter port states.

```bash
python verify_power.py
python verify_power.py --serial 883001B0916
```

### power_cycle.py - Standard Power Cycle (Existing)

Standard power cycle with configurable delay (default 3 seconds).

```bash
python power_cycle.py
python power_cycle.py --source splitter --delay 5
```

### advanced_power_cycle.py - Hard Cold Boot

Full power cycle with 15-second capacitor drain delay for complete hardware reset. Use this for recovery scenarios and post-flash operations.

```bash
# Default 15-second hard cold boot
python advanced_power_cycle.py

# Custom delay
python advanced_power_cycle.py --delay 20

# Specify device
python advanced_power_cycle.py --serial 883001B0916
```

## When to Use Which

| Script | Delay | Use Case |
|--------|-------|----------|
| `power_cycle.py` | 3s (default) | Standard testing, quick reboot |
| `advanced_power_cycle.py` | 15s (default) | Recovery, post-flash, stuck platforms, capacitor drain |
| `power_off.py` + `power_on.py` | Manual | Step-by-step control, SPI flash operations |
| `verify_power.py` | N/A | Status check before/after operations |

## Common Workflows

### Pre-SPI Flash Sequence
```bash
python power_off.py                    # Power down for safe SPI access
# ... perform SPI flash operations ...
python power_on.py --delay 5           # Power back on with extra stabilization
```

### Recovery Power Cycle
```bash
python advanced_power_cycle.py --delay 20  # Extended drain for stubborn platforms
```

### Status Check
```bash
python verify_power.py                 # Quick state check
```

## JSON Output Format

All scripts output structured JSON to stdout:

```json
{
  "status": "success",
  "operation": "power_off",
  "device_serial": "883001B0916",
  "timestamp": "2025-01-15T10:30:00",
  "port_states": {
    "port_1": "OFF",
    "port_2": "OFF",
    "port_3": "OFF",
    "port_4": "OFF"
  },
  "all_ports_verified": true
}
```

## Integration with Agents

Power scripts are invoked by TTK3-POWER, TTK3-BOOT, and FV_Debugger_V1 agents:

```python
import subprocess, json

# Power off before SPI operations
result = subprocess.run(['python', 'power_off.py'], capture_output=True, text=True)
data = json.loads(result.stdout)
if data['status'] == 'success':
    # Safe to proceed with SPI flash
    pass
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Operation completed successfully, all ports verified |
| 1 | Operation completed but port verification failed |
| 2 | Device not found or connection error |

## Best Practices

- Always use **10-second minimum** delay for G3 power cycles (capacitor drain)
- Use `advanced_power_cycle.py` (15s) when recovering from stuck states
- Always **verify power state** before SPI flash operations
- Coordinate with UART capture when using `power_on.py` (default 2s delay allows UART initialization)
