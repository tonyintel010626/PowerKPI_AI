---
name: ttk3/boot
description: TTK3 Boot Validation for POST code sequence monitoring and verification
---

# TTK3 Boot Validation

Boot validation skill for monitoring and verifying platform boot sequences via POST codes. Tracks the sequence of POST codes during boot, validates against expected sequences, and checks for required final codes.

## Quick Start

```python
from ttk3_agent_platform.skills.boot_validation_skill import BootValidationSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = BootValidationSkill(tools)
result = await skill.execute({
    "timeout": 120,
    "expected_codes": [0x01, 0x10, 0x20, 0xE0],
    "required_final_code": 0xE0
})
print(f"Boot duration: {result.data['boot_duration']}s")
print(f"Sequence match: {result.data['sequence_match_percentage']}%")
```

## API Reference

### Basic Boot Monitoring

```python
from ttk3_agent_platform.skills.boot_validation_skill import BootValidationSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = BootValidationSkill(tools)

# Simple boot monitoring (just capture codes)
result = await skill.execute({
    "timeout": 120,
    "poll_interval": 0.5
})
print(f"Observed codes: {result.data['observed_codes']}")
print(f"Total codes: {result.data['total_codes_seen']}")
print(f"Duration: {result.data['boot_duration']}s")
```

### Boot Sequence Validation

```python
# Validate against expected sequence
result = await skill.execute({
    "timeout": 120,
    "poll_interval": 0.5,
    "expected_codes": [0x01, 0x02, 0x10, 0x20, 0x50, 0xA0, 0xE0],
    "required_final_code": 0xE0
})

if result.success:
    data = result.data
    print(f"Sequence match: {data['sequence_match_percentage']}%")
    print(f"Final code match: {data['final_code_match']}")
    print(f"Boot time: {data['boot_duration']}s")
else:
    print(f"Boot validation failed: {result.error}")
```

### Direct POST Code Tool Usage

```python
from ttk3_agent_platform.tools.post_code_tool import PostCodeTool

post = PostCodeTool()
post.open()

# Monitor boot sequence directly
result = post.monitor_boot(timeout=120, poll_interval=0.5)
# Returns: {
#   "post_codes": [0x01, 0x02, ...],
#   "duration": 45.2,
#   "total_codes": 128,
#   "timed_out": False
# }

post.close()
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| timeout | int | 120 | Boot monitoring timeout in seconds (max 600) |
| poll_interval | float | 0.5 | POST code polling interval in seconds |
| expected_codes | list[int] | [] | Expected POST code sequence |
| required_final_code | int | None | Required final POST code for success |

## Result Fields

| Field | Type | Description |
|-------|------|-------------|
| observed_codes | list[int] | All POST codes observed during boot |
| total_codes_seen | int | Total number of POST codes captured |
| boot_duration | float | Time from start to last code (seconds) |
| sequence_match_percentage | float | How well observed matches expected (0-100) |
| final_code_match | bool | Whether final code matches required_final_code |
