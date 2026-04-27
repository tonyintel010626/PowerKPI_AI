---
name: ttk3/device
description: TTK3 Device Discovery for TTK3/SQUID detection, serial numbers, and firmware/hardware info
---

# TTK3 Device Discovery

Device management interface for discovering connected TTK3 and SQUID USB devices, querying serial numbers, firmware/hardware revisions, and connection status.

## Quick Start

```python
from Ttk3Device import Ttk3Device, DeviceType

device = Ttk3Device()
try:
    device.Open()
    count = device.GetNumConnectedDevices()
    serial = device.GetDeviceSeriaNumberByIndex(0)  # Note: typo in real API (missing 'l')
    fw = device.GetFirmwareRevision()
    print(f"Found {count} devices, serial: {serial}, FW: {fw}")
finally:
    device.Close()
```

## API Reference

### Connection

```python
from Ttk3Device import Ttk3Device, DeviceType

device = Ttk3Device()

# Open default device
device.Open()

# Open specific device by index
device.OpenIndex(deviceIndex=1, deviceType=0)  # 0 = TTK3, 1 = SQUID

# Close when done (always in finally block)
device.Close()
```

### Device Discovery

```python
device = Ttk3Device()
try:
    device.Open()

    # Count connected devices
    count = device.GetNumConnectedDevices()
    print(f"Connected devices: {count}")

    # Get serial number for each device
    for i in range(count):
        serial = device.GetDeviceSeriaNumberByIndex(i)  # Note: typo in real API
        print(f"  Device {i}: {serial}")

finally:
    device.Close()
```

> ⚠️ **API Typo**: The real DLL method is `GetDeviceSeriaNumberByIndex` (missing 'l' in "Serial"). This is a known typo in the TTK3 API — you must use the misspelled version.

### Device Information

```python
device = Ttk3Device()
try:
    device.Open()

    fw_rev = device.GetFirmwareRevision()
    hw_rev = device.GetHardwareRevision()
    print(f"Firmware: {fw_rev}, Hardware: {hw_rev}")

finally:
    device.Close()
```

### Connection Check

```python
device = Ttk3Device()
try:
    device.Open()

    # Check if a TTK3 device is connected
    ttk3_connected = device.IsDeviceConnected(DeviceType.TTK3)   # DeviceType.TTK3 = 0
    squid_connected = device.IsDeviceConnected(DeviceType.SQUID)  # DeviceType.SQUID = 1

    print(f"TTK3: {ttk3_connected}, SQUID: {squid_connected}")

finally:
    device.Close()
```

### Multi-Device Enumeration

```python
from Ttk3Device import Ttk3Device

device = Ttk3Device()
try:
    device.Open()
    count = device.GetNumConnectedDevices()

    devices = []
    for i in range(count):
        device.OpenIndex(deviceIndex=i)
        devices.append({
            "index": i,
            "serial": device.GetDeviceSeriaNumberByIndex(i),
            "fw_rev": device.GetFirmwareRevision(),
            "hw_rev": device.GetHardwareRevision(),
        })

    print(f"Discovered {len(devices)} devices: {devices}")

finally:
    device.Close()
```

### Multi-Device Management (using skill)

```python
from ttk3_agent_platform.skills.multi_device_management_skill import MultiDeviceManagementSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = MultiDeviceManagementSkill(tools)
result = await skill.execute({
    "operation": "discover",
    "device_type": "TTK3"
})
# Returns: list of all discovered devices with details
```

## STUB Methods

> Methods listed as STUB are **not available** in the real TTK3 `Ttk3Device` API. Calling them on the wrapper will raise `NotImplementedError`.

| Wrapper Method | Status | Notes |
|----------------|--------|-------|
| `detect_all_devices()` | **STUB** | Wrapper convenience; iterate with `GetNumConnectedDevices()` + `OpenIndex()` |
| `is_driver_installed(device_type)` | **STUB** | Not in documented Ttk3Device API |
| `is_device_ready(device_type)` | **STUB** | Not in documented Ttk3Device API |
| `set_connected_platform_type(platform)` | **STUB** | Not in documented Ttk3Device API |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| deviceIndex | int | 0 | Device index for multi-device setups |
| deviceType | int | 0 | Device type: 0 = TTK3 (`DeviceType.TTK3`), 1 = SQUID (`DeviceType.SQUID`) |

## Notes

- Always use `try/finally` to ensure `Close()` is called
- `GetDeviceSeriaNumberByIndex` is **intentionally misspelled** — this matches the real DLL API
- `DeviceType.TTK3 = 0`, `DeviceType.SQUID = 1`
- Use `GetNumConnectedDevices()` + loop with `OpenIndex()` instead of the wrapper's `detect_all_devices()`
