---
name: ttk3/uart
description: TTK3 UART Serial Debug for read/write/capture with baud rate control
---

# TTK3 UART Serial Debug

> ⚠️ **WARNING**: Most methods in this skill are STUBs pending real TTK3 API verification. They will raise `NotImplementedError` when called. Only `open()` and `close()` are verified. The real TTK3 UART API has not been fully documented yet.

UART serial interface for reading, writing, and capturing serial debug output from the platform. Supports configurable baud rates, delimiter-based reading, timed log capture, and buffer management.

## Quick Start

```python
# NOTE: Real UART API not yet verified.
# Only open() and close() are confirmed to work.
# All other methods are STUBs and will raise NotImplementedError.

from ttk3_agent_platform.tools.uart_tool import UARTTool

uart = UARTTool()
try:
    uart.open()
    # uart.set_baud_rate(115200)              # STUB — will raise NotImplementedError
    # log = uart.capture_log(duration=60)     # STUB — will raise NotImplementedError
finally:
    uart.close()
```

## API Reference

### Connection

```python
uart = UARTTool()

# Open — verified to work
uart.open()

# Close — verified to work (always in finally block)
uart.close()
```

### Basic Read/Write (ALL STUBs)

> ⚠️ All read/write methods below are STUBs. They will raise `NotImplementedError` until the real UART API is verified and wrappers are implemented.

```python
uart = UARTTool()
try:
    uart.open()

    uart.set_baud_rate(115200)                # STUB

    # Read available data
    available = uart.get_available_bytes()     # STUB
    data = uart.read(length=256)              # STUB

    # Write data
    uart.write(b"command\r\n")                # STUB

    # Flush buffers
    uart.flush_buffers()                      # STUB

finally:
    uart.close()
```

### Targeted Reading (ALL STUBs)

```python
uart = UARTTool()
try:
    uart.open()

    # Read until a specific delimiter is found
    result = uart.read_until(delimiter=b"\n", timeout=30)  # STUB
    # Would return: {
    #   "data": b"...",
    #   "found_delimiter": True,
    #   "duration": 0.5
    # }

finally:
    uart.close()
```

### Log Capture (ALL STUBs)

```python
uart = UARTTool()
try:
    uart.open()

    # Capture serial output for a duration
    log = uart.capture_log(duration=60)        # STUB
    # Would return: {
    #   "log": "...",
    #   "bytes_captured": 4096,
    #   "duration": 60.0
    # }

finally:
    uart.close()
```

### Serial Debug Workflow (using skill)

```python
from ttk3_agent_platform.skills.serial_debug_skill import SerialDebugSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = SerialDebugSkill(tools)
result = await skill.execute({
    "baud_rate": 115200,
    "capture_duration": 60,
    "patterns": ["error", "warning", "fail"],
    "wait_for_prompt": True
})
# Returns: captured log, pattern matches, analysis
```

## STUB Methods

> ⚠️ **7 of 9 methods are STUBs.** Only `open()` and `close()` are verified. All other methods will raise `NotImplementedError` until the real TTK3 UART API is documented and verified.

| Wrapper Method | Status | Notes |
|----------------|--------|-------|
| `open()` | **Verified** | Works with TTK3 device |
| `close()` | **Verified** | Works with TTK3 device |
| `set_baud_rate(baud_rate)` | **STUB** | Needs UART API verification |
| `read(length)` | **STUB** | Needs UART API verification |
| `write(data)` | **STUB** | Needs UART API verification |
| `get_available_bytes()` | **STUB** | Needs UART API verification |
| `flush_buffers()` | **STUB** | Needs UART API verification |
| `read_until(delimiter, timeout)` | **STUB** | Needs UART API verification |
| `capture_log(duration)` | **STUB** | Needs UART API verification |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| baud_rate | int | 115200 | UART baud rate |
| length | int | - | Number of bytes to read |
| data | bytes | - | Data to write |
| delimiter | bytes | - | Delimiter for read_until |
| timeout | int | 30 | Timeout for read_until in seconds |
| duration | int | 60 | Duration for capture_log in seconds |

## Notes

- **Most methods are STUBs** — the real TTK3 UART DLL API has not been verified yet
- Only `open()` and `close()` are confirmed working
- Always use `try/finally` to ensure `close()` is called
- Once the real API is verified, wrapper methods will be updated to call the actual DLL methods
