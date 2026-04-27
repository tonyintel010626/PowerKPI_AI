---
name: ttk3/i2c
description: TTK3 I2C Bus Operations for device read/write with clock speed control
---

# TTK3 I2C Bus Operations

I2C bus interface for reading/writing to slave devices on the I2C bus via TTK3 hardware. Supports configurable clock speed, offset-based read operations, and bus scanning.

## Quick Start

```python
from I2cControl import I2cControl

i2c = I2cControl()
try:
    i2c.Open()
    i2c.SetClock(400)  # 400 KHz
    data = i2c.Read(0x50, 16)
    print(f"Data: {data}")
finally:
    i2c.Close()
```

## API Reference

### Connection

```python
i2c = I2cControl()

# Open default device
i2c.Open()

# Open specific device by index
i2c.OpenIndex(deviceIndex)

# Open specific device by index and type
i2c.OpenDevice(deviceIndex, deviceType)  # deviceType: 0=TTK3, 1=SQUID

# Always close when done
i2c.Close()
```

### Basic Operations

```python
i2c = I2cControl()
try:
    i2c.Open()

    # Set clock speed in KHz
    i2c.SetClock(400)  # 400 KHz

    # Direct read (deviceAddress, size)
    data = i2c.Read(0x50, 8)

    # Direct write (deviceAddress, data)
    i2c.Write(0x50, [0x00, 0x01, 0x02])

    # Read with offset/register address (deviceAddress, offset, size)
    reg_data = i2c.ReadWithOffset(0x50, 0x10, 4)

finally:
    i2c.Close()
```

### I2C Bus Scan with Error Handling

```python
from I2cControl import I2cControl

i2c = I2cControl()
try:
    i2c.Open()
    i2c.SetClock(100)  # 100 KHz for scanning

    found_devices = []
    for addr in range(0x08, 0x78):
        try:
            data = i2c.Read(addr, 1)
            if data:
                found_devices.append(addr)
                print(f"Device found at 0x{addr:02X}")
        except Exception:
            pass  # No device at this address

    print(f"Total devices found: {len(found_devices)}")

finally:
    i2c.Close()
```

## STUB Methods

The following methods are **STUBs** that raise `NotImplementedError`:

| Method | Status | Notes |
|--------|--------|-------|
| `set_bus_voltage(voltage)` | STUB | Not in documented TTK3 API |
| `set_retries(count)` | STUB | Needs API verification |
| `get_firmware_revision()` | STUB | Needs API verification |
| `get_hardware_revision()` | STUB | Needs API verification |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| deviceAddress | int | - | 7-bit I2C slave address (0x08-0x77) |
| offset | int | - | Sub/register address within the device |
| size | int | - | Number of bytes to read |
| data | list[int] | - | Data bytes to write |
| clockValueKhz | int | 400 | Bus clock speed in KHz |

## Notes

- Clock speed is set in **KHz** (not Hz): 100, 400, 1000, 3400
- Always call `Open()` before operations and `Close()` in a `finally` block
- Uses `I2cControl` module from `C:\SVSHARE\User_Apps\TTK3\API\Python\`
- The `I2cControl` class wraps `TTK3_I2C.dll` via ctypes
