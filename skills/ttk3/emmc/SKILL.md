---
name: ttk3/emmc
description: TTK3 eMMC Programming for sector/user area/boot partition access and BIOS flashing
---

# TTK3 eMMC Programming

eMMC flash programming interface for reading/writing sectors, user area data, boot partitions, and performing BIOS programming on eMMC-based platforms.

## Quick Start

```python
from ttk3_agent_platform.tools.emmc_programmer_tool import EMMCProgrammerTool

emmc = EMMCProgrammerTool()
emmc.open()
info = emmc.get_card_info()
print(f"eMMC: {info}")
emmc.close()
```

## API Reference

### Device Operations

```python
emmc = EMMCProgrammerTool()

# Open default device
emmc.open()

# Open specific device by index
emmc.open_index(index=1)

# Detect eMMC device
device = emmc.detect_device()
# Returns: {"detected": True, "type": "...", "size": ...}

# Get card information
info = emmc.get_card_info()

# Reconnect to SUT (System Under Test)
emmc.reconnect_to_sut()

emmc.close()
```

### Sector Operations

```python
emmc = EMMCProgrammerTool()
emmc.open()

# Read a sector (512 bytes)
sector_data = emmc.read_sector(sector=0)

# Write a sector
emmc.write_sector(sector=0, data=b'\x00' * 512)

emmc.close()
```

### User Area Operations

```python
emmc = EMMCProgrammerTool()
emmc.open()

# Read from user area
data = emmc.read_user_area(offset=0x0, length=0x1000)

# Write to user area
emmc.write_user_area(offset=0x0, data=binary_data)

emmc.close()
```

### Boot Partitions

```python
emmc = EMMCProgrammerTool()
emmc.open()

# Read boot partitions
boot1 = emmc.read_boot1()
boot2 = emmc.read_boot2()

emmc.close()
```

### BIOS Programming

```python
emmc = EMMCProgrammerTool()
emmc.open()

# Program BIOS to eMMC
emmc.program_bios("/path/to/bios.bin")

# Read current BIOS from eMMC
bios_data = emmc.read_bios()

emmc.close()
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| index | int | Device index for multi-device |
| sector | int | Sector number (512-byte blocks) |
| offset | int | Byte offset in user area |
| length | int | Number of bytes to read |
| data | bytes | Binary data to write |
| image_path | str | Path to BIOS binary file |
