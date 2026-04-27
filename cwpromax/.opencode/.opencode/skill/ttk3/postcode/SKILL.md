---
name: ttk3/postcode
description: TTK3 POST Code Monitoring for Port80 boot sequence tracking and validation
---

# TTK3 POST Code Monitoring

Port80 POST code monitoring interface for tracking platform boot sequences. Captures BIOS POST codes in real-time, supports event-based callbacks, and async polling.

## Quick Start

```python
from Port80 import Port80

port80 = Port80()
try:
    port80.Open()
    current = port80.Read()  # Returns hex string like "A0B1"
    print(f"Current POST code: {current}")
finally:
    port80.Close()
```

## API Reference

### Connection

```python
from Port80 import Port80

port80 = Port80()

# Open default device
port80.Open(deviceType=0)   # 0 = TTK3, 1 = SQUID

# Close when done (always in finally block)
port80.Close()
```

### POST Code Reading

```python
port80 = Port80()
try:
    port80.Open()

    # Read current POST code (returns hex string like "A0B1")
    current = port80.Read()
    print(f"Current POST code: {current}")

finally:
    port80.Close()
```

### Event-Based Monitoring

```python
port80 = Port80()
try:
    port80.Open()

    # Subscribe to POST code change events
    def on_post_code_changed(code):
        print(f"POST code changed: {code}")

    port80.SubscribePort80ChangedEvent(on_post_code_changed)

    # Start async reading at specified frequency
    port80.ReadAsync(freqInMs=100)  # Poll every 100ms

    # ... wait for boot to complete ...

    # Stop async reading
    port80.RequestStop()

finally:
    port80.Close()
```

### Boot Monitoring Workflow (with Power Cycle)

```python
from Port80 import Port80
from PowerControl import PowerControl
import time

power = PowerControl()
port80 = Port80()
try:
    power.OpenPowerSplitter()
    try:
        port80.Open()

        # Power cycle and monitor POST codes
        power.AllPortsOff()
        time.sleep(2)
        power.AllPortsOn()

        # Read POST codes during boot
        port80.ReadAsync(freqInMs=100)
        time.sleep(120)  # Monitor for 2 minutes
        port80.RequestStop()

    finally:
        port80.Close()
finally:
    power.Close()
```

### Boot Validation (using skill)

```python
from ttk3_agent_platform.skills.boot_validation_skill import BootValidationSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = BootValidationSkill(tools)
result = await skill.execute({
    "timeout": 120,
    "poll_interval": 0.5,
    "expected_codes": [0x01, 0x10, 0x20, 0xE0],
    "required_final_code": 0xE0
})
# Returns: observed_codes, total_codes_seen, boot_duration,
#          sequence_match_percentage, final_code_match
```

## STUB Methods

> Methods listed as STUB are **not available** in the real TTK3 `Port80` API. Calling them on the wrapper will raise `NotImplementedError`.

| Wrapper Method | Status | Notes |
|----------------|--------|-------|
| `clear_post_codes()` | **STUB** | Not in documented Port80 API. POST code log is wrapper-only. |
| `get_last_post_code()` | **STUB** | Wrapper convenience method; use `Read()` for current code |
| `get_post_code_log()` | **STUB** | Wrapper convenience method; use event subscription for history |
| `monitor_boot(timeout, poll_interval)` | **STUB** | Wrapper convenience; use `ReadAsync()` + `SubscribePort80ChangedEvent()` |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| deviceType | int | 0 | Device type: 0 = TTK3, 1 = SQUID |
| freqInMs | int | 100 | Polling frequency for `ReadAsync()` in milliseconds |
| callback | function | - | Callback function for `SubscribePort80ChangedEvent()` |

## Notes

- `Read()` returns a **hex string** (e.g., `"A0B1"`), not an integer
- Always use `try/finally` to ensure `Close()` is called
- For boot monitoring, prefer `ReadAsync()` + `SubscribePort80ChangedEvent()` over polling `Read()` in a loop
- `RequestStop()` must be called to stop `ReadAsync()` before `Close()`

## POST Code Reading Reliability Issues (Learned from NVL-S Debug Session)

### False FFFF Readings
- **FFFF postcode can be a false TTK3 reading** — it does not always mean the platform is stuck
- HSDES 15019045327 documents this as a known issue
- When reading FFFF, **always cross-verify with physical observation** (LEDs, fan spin, display output)

### FFFF Interpretation Guide
| Scenario | Meaning | Action |
|----------|---------|--------|
| FFFF immediately after power-on | Normal — platform hasn't started POST yet | Wait 10+ seconds, read again |
| FFFF persistent after 30+ seconds | Platform may be stuck or PMC not waking | Verify physically, attempt G3 power cycle |
| FFFF after IFWI reflash | IFWI flash didn't fix the issue | Likely hardware problem |
| FFFF reading but platform visually booting | False TTK3 reading (known bug) | Trust physical observation over TTK3 |

### Verification Methods
1. **Read multiple times** — take 3-5 readings with 2-second intervals before concluding FFFF is real
2. **Physical check** — verify fan spin, LED status, display output
3. **Cross-reference** with power state — use `GetPortState()` to confirm power is actually on

### Monitoring Best Practices
- Always wait **minimum 10 seconds** after power-on before first POST code read
- Use `ReadAsync()` with event subscription for continuous monitoring rather than single `Read()` calls
- Log all POST code transitions for debug analysis — a sequence of codes is more useful than a single reading
- If monitoring shows no code transitions at all (stuck at one value), that's more significant than any single reading
