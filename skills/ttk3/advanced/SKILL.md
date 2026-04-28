---
name: ttk3/advanced
description: TTK3 Advanced Programming for JTAG, Retimer, PD, MCU, Bootloader, NVM, and CutOff operations
---

# TTK3 Advanced Programming

Advanced programming interface supporting multiple programmer types: JTAG, Retimer SPI, Power Delivery (PD), MCU, IFWI Loader, Bootloader, NVM Logging, and CutOff operations. Each subsystem has dedicated methods accessed through a unified tool.

## Quick Start

```python
from ttk3_agent_platform.tools.advanced_programmer_tool import AdvancedProgrammerTool

adv = AdvancedProgrammerTool()
adv.open()
# JTAG programming
adv.jtag_program("/path/to/firmware.bin")
adv.jtag_verify("/path/to/firmware.bin")
adv.close()
```

## API Reference

### JTAG Programming

```python
adv = AdvancedProgrammerTool()
adv.open()

adv.jtag_program("/path/to/jtag_firmware.bin")
adv.jtag_verify("/path/to/jtag_firmware.bin")
adv.jtag_erase()
data = adv.jtag_read(address=0x0, length=0x1000)

adv.close()
```

### Retimer SPI Programming

```python
adv = AdvancedProgrammerTool()
adv.open()

info = adv.retimer_detect()
adv.retimer_program("/path/to/retimer_fw.bin")
adv.retimer_verify("/path/to/retimer_fw.bin")
data = adv.retimer_read(address=0x0, length=256)

adv.close()
```

### Power Delivery (PD) Programming

```python
adv = AdvancedProgrammerTool()
adv.open()

# Program via I2C or SWD interface
adv.pd_program_i2c("/path/to/pd_fw.bin")
adv.pd_program_swd("/path/to/pd_fw.bin")
adv.pd_verify("/path/to/pd_fw.bin")
version = adv.pd_get_version()

adv.close()
```

### MCU Programming

```python
adv = AdvancedProgrammerTool()
adv.open()

adv.mcu_program("/path/to/mcu_fw.bin")
adv.mcu_verify("/path/to/mcu_fw.bin")
version = adv.mcu_get_version()

adv.close()
```

### IFWI Loading

```python
adv = AdvancedProgrammerTool()
adv.open()

# Load from IFWI Central or VDC
adv.ifwi_load_from_central("IFWI-12345")
adv.ifwi_load_from_vdc("VDC-67890")

# Get image info and validate
info = adv.ifwi_get_info("IFWI-12345")
adv.ifwi_validate("/path/to/ifwi.bin")

adv.close()
```

### Bootloader Operations

```python
adv = AdvancedProgrammerTool()
adv.open()

adv.bootloader_enter()
adv.bootloader_program("/path/to/bootloader.bin")
adv.bootloader_exit()

adv.close()
```

### NVM Logging

```python
adv = AdvancedProgrammerTool()
adv.open()

log = adv.nvm_read_log()
entries = adv.nvm_get_entries(count=100)
adv.nvm_clear_log()

adv.close()
```

### CutOff Operations

```python
adv = AdvancedProgrammerTool()
adv.open()

status = adv.cutoff_get_status()
adv.cutoff_execute()

adv.close()
```

## Subsystem Modules

| Subsystem | TTK3 Module | Methods |
|-----------|-------------|---------|
| JTAG | JtagProgrammer | program, verify, erase, read |
| Retimer | RetimerSPIProgrammer | detect, program, verify, read |
| PD | PdProg | program_i2c, program_swd, verify, get_version |
| MCU | MCUProgrammer | program, verify, get_version |
| IFWI | IFWILoader | load_from_central, load_from_vdc, get_info, validate |
| Bootloader | BootLoader | enter, exit, program |
| NVM | NVM_Logging | read_log, clear_log, get_entries |
| CutOff | CutOff | execute, get_status |
