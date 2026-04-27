---
name: ttk3/gpio
description: TTK3 GPIO Control for pin read/write, sleep state detection, and platform status monitoring
---

# TTK3 GPIO Control

> ⚠️ **WARNING**: Most methods in this skill are STUBs pending real TTK3 API verification. They will raise `NotImplementedError` when called. Only `open()` and `close()` are verified. The real TTK3 GPIO API (Gpio/GpiosManager modules) has not been fully documented yet.

GPIO interface for direct pin control, direction configuration, platform sleep state detection, and comprehensive platform status monitoring. Uses both Gpio and GpiosManager TTK3 modules.

## Quick Start

```python
# NOTE: Real GPIO/GpiosManager API not yet verified.
# Only open() and close() are confirmed to work.
# All other methods are STUBs and will raise NotImplementedError.

from ttk3_agent_platform.tools.gpio_control_tool import GPIOControlTool

gpio = GPIOControlTool()
try:
    gpio.open()
    # sleep_state = gpio.get_sleep_state()       # STUB — will raise NotImplementedError
    # platform_status = gpio.get_platform_status() # STUB — will raise NotImplementedError
finally:
    gpio.close()
```

## API Reference

### Connection

```python
gpio = GPIOControlTool()

# Open — verified to work
gpio.open()

# Close — verified to work (always in finally block)
gpio.close()
```

### Pin Operations (ALL STUBs)

> ⚠️ All pin operation methods below are STUBs. They will raise `NotImplementedError` until the real Gpio API is verified and wrappers are implemented.

```python
gpio = GPIOControlTool()
try:
    gpio.open()

    # Configure pin direction ("input" or "output")
    gpio.configure_gpio(pin=0, direction="output")    # STUB

    # Read a GPIO pin value (returns 0 or 1)
    value = gpio.read_gpio(pin=0)                     # STUB

    # Write to a GPIO pin
    gpio.write_gpio(pin=0, value=1)                   # STUB

    # Read all GPIO pins at once
    all_values = gpio.read_all_gpios()                # STUB

    # Set direction without full configure
    gpio.set_gpio_direction(pin=0, direction="input")  # STUB

finally:
    gpio.close()
```

### Platform Monitoring (ALL STUBs)

> ⚠️ All platform monitoring methods below are STUBs. They will raise `NotImplementedError` until the real GpiosManager API is verified.

```python
gpio = GPIOControlTool()
try:
    gpio.open()

    # Get current sleep state (S0, S3, S4, S5, etc.)
    sleep_state = gpio.get_sleep_state()               # STUB

    # Get comprehensive platform status
    status = gpio.get_platform_status()                # STUB

finally:
    gpio.close()
```

### Device Information (ALL STUBs)

```python
gpio = GPIOControlTool()
try:
    gpio.open()

    fw_rev = gpio.get_firmware_revision()              # STUB
    hw_rev = gpio.get_hardware_revision()              # STUB

finally:
    gpio.close()
```

## STUB Methods

> ⚠️ **9 of 11 methods are STUBs.** Only `open()` and `close()` are verified. All other methods will raise `NotImplementedError` until the real TTK3 Gpio/GpiosManager API is documented and verified.

| Wrapper Method | Status | Notes |
|----------------|--------|-------|
| `open()` | **Verified** | Works with TTK3 device |
| `close()` | **Verified** | Works with TTK3 device |
| `configure_gpio(pin, direction)` | **STUB** | Needs Gpio API verification |
| `read_gpio(pin)` | **STUB** | Needs Gpio API verification |
| `write_gpio(pin, value)` | **STUB** | Needs Gpio API verification |
| `read_all_gpios()` | **STUB** | Needs Gpio API verification |
| `set_gpio_direction(pin, direction)` | **STUB** | Needs Gpio API verification |
| `get_sleep_state()` | **STUB** | Needs GpiosManager API verification |
| `get_platform_status()` | **STUB** | Needs GpiosManager API verification |
| `get_firmware_revision()` | **STUB** | Needs Gpio API verification |
| `get_hardware_revision()` | **STUB** | Needs Gpio API verification |

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| pin | int | GPIO pin number |
| direction | str | Pin direction: "input" or "output" |
| value | int | Pin value: 0 or 1 |

## Notes

- **Most methods are STUBs** — the real Gpio and GpiosManager TTK3 DLL APIs have not been verified yet
- Only `open()` and `close()` are confirmed working
- Always use `try/finally` to ensure `close()` is called
- Sleep state detection is expected to use the GpiosManager module once verified
- Pin numbering will be hardware-specific to the TTK3/SQUID device
