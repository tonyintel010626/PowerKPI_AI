---
name: ttk3/ifwi
description: TTK3 IFWI Central for image lifecycle management, search, validation, and export
---

# TTK3 IFWI Central

IFWI (Integrated Firmware Image) Central interface for managing the complete image lifecycle — loading images from IFWI Central or VDC, searching for images, validating binaries, and exporting to Configuration Manager.

## Quick Start

```python
from ttk3_agent_platform.tools.ifwi_central_tool import IFWICentralTool

ifwi = IFWICentralTool()
ifwi.open()
info = ifwi.get_image_info("IFWI-12345")
print(f"Image: {info}")
ifwi.close()
```

## API Reference

### Image Loading

```python
ifwi = IFWICentralTool()
ifwi.open()

# Load image from IFWI Central
ifwi.load_image("IFWI-12345")

# Load image from VDC (Validation Data Center)
ifwi.load_image_from_vdc("VDC-67890")

ifwi.close()
```

### Image Information and Search

```python
ifwi = IFWICentralTool()
ifwi.open()

# Get detailed image information
info = ifwi.get_image_info("IFWI-12345")

# Search for images by query
results = ifwi.search_images("MTL_BIOS_release")

# Get latest image for a board
latest = ifwi.get_latest_image("MTL-P-board-id")

ifwi.close()
```

### Validation and Export

```python
ifwi = IFWICentralTool()
ifwi.open()

# Validate a local IFWI binary
is_valid = ifwi.validate_image("/path/to/ifwi.bin")

# Export current image to Configuration Manager
ifwi.export_to_cm()

ifwi.close()
```

### IFWI Image Management Workflow (using skill)

```python
from ttk3_agent_platform.skills.ifwi_image_management_skill import IFWIImageManagementSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = IFWIImageManagementSkill(tools)
result = await skill.execute({
    "operation": "load_and_validate",
    "ifwi_id": "IFWI-12345",
    "validate": True
})
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| ifwi_id | str | IFWI Central image identifier |
| image_id | str | VDC image identifier |
| image_path | str | Local path to IFWI binary |
| query | str | Search query string |
| board_id | str | Board identifier for latest image lookup |
