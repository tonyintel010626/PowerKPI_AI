---
name: ttk3/hid
description: TTK3 HID Emulation for keyboard and mouse input simulation
---

# TTK3 HID Emulation

Human Interface Device (HID) emulation for simulating keyboard and mouse input to the platform under test. Supports key press/release, text typing, mouse movement, clicks, and scroll operations.

## Quick Start

```python
from ttk3_agent_platform.tools.hid_emulator_tool import HIDEmulatorTool

hid = HIDEmulatorTool()
hid.keyboard_open()
hid.send_text("Hello World")
hid.send_key(0x28)  # Enter key
hid.keyboard_close()
```

## API Reference

### Keyboard Operations

```python
hid = HIDEmulatorTool()
hid.keyboard_open()

# Send a single key (HID key code)
hid.send_key(key_code=0x04)  # 'A' key
hid.send_key(key_code=0x04, modifier=0x02)  # Shift+A

# Send multiple keys with delay between them
hid.send_keys(key_codes=[0x04, 0x05, 0x06], delay_ms=50)

# Type a text string (handles character-to-keycode mapping)
hid.send_text("Hello World!")

# Key down/up for held keys
hid.key_down(key_code=0xE0)  # Hold Left Ctrl
hid.send_key(key_code=0x06)  # Press 'C' (Ctrl+C)
hid.key_up(key_code=0xE0)    # Release Left Ctrl

hid.keyboard_close()
```

### Mouse Operations

```python
hid = HIDEmulatorTool()
hid.mouse_open()

# Relative mouse movement
hid.move_relative(dx=100, dy=50)

# Absolute mouse movement
hid.move_absolute(x=512, y=384)

# Click operations
hid.left_click()
hid.right_click()
hid.middle_click()

# Scroll wheel
hid.scroll_wheel(delta=3)   # Scroll up
hid.scroll_wheel(delta=-3)  # Scroll down

hid.mouse_close()
```

### HID Test Automation (using skill)

```python
from ttk3_agent_platform.skills.hid_test_automation_skill import HIDTestAutomationSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = HIDTestAutomationSkill(tools)
result = await skill.execute({
    "actions": [
        {"type": "keyboard", "action": "text", "value": "username"},
        {"type": "keyboard", "action": "key", "value": 0x2B},  # Tab
        {"type": "keyboard", "action": "text", "value": "password"},
        {"type": "keyboard", "action": "key", "value": 0x28},  # Enter
        {"type": "mouse", "action": "move", "x": 100, "y": 200},
        {"type": "mouse", "action": "left_click"}
    ]
})
```

## Common HID Key Codes

| Key | Code | Key | Code |
|-----|------|-----|------|
| A-Z | 0x04-0x1D | Enter | 0x28 |
| 1-0 | 0x1E-0x27 | Escape | 0x29 |
| Tab | 0x2B | Space | 0x2C |
| F1-F12 | 0x3A-0x45 | Delete | 0x4C |
| Left Ctrl | 0xE0 | Left Shift | 0xE1 |
| Left Alt | 0xE2 | Left GUI | 0xE3 |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| key_code | int | - | HID key code |
| modifier | int | 0 | Modifier key mask |
| key_codes | list[int] | - | Multiple key codes |
| delay_ms | int | 50 | Delay between keys in ms |
| text | str | - | Text string to type |
| dx, dy | int | - | Relative mouse movement |
| x, y | int | - | Absolute mouse position |
| delta | int | - | Scroll wheel delta |
