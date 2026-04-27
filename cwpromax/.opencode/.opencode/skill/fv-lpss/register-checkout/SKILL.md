---
name: fv-lpss/register-checkout
description: "Check LPSS-related register values for correctness using PythonSV"
---

# LPSS Register Checkout

This skill provides procedures for verifying LPSS (Low Power Subsystem) register values to ensure correct hardware configuration and state.

## Overview

Register checkout is a fundamental debugging technique that involves:
1. Reading register values from hardware using PythonSV
2. Comparing actual values against expected values (from specification or reset values)
3. Identifying configuration mismatches or hardware faults
4. Using register specifications (`.getspec()`) to understand register fields

---

## PythonSV Register Access

### Initialization

```python
# Initialize PythonSV environment
import namednodes
from namednodes import *
import baseaccess

# Unlock ITP
itp.unlock()

# Refresh silicon view
sv.refresh()
```

### Searching for LPSS Registers

```python
# Search for LPSS-related registers
lpss_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss",
    searchType="registers"
)

# Search for specific register types
control_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*ctrl|lpss.*control",
    searchType="registers"
)

status_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*sts|lpss.*status",
    searchType="registers"
)

config_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*cfg|lpss.*config",
    searchType="registers"
)

# Print found registers
for reg in lpss_regs:
    print(f"Register: {reg}")
```

### Reading Register Values

```python
# Read a register (replace with actual register path)
# TODO: Replace with actual LPSS register paths from platform specification
reg_value = namednodes.sv.socket0.uncore.pcd.lpss_ctrl.read()

print(f"Register value: {hex(reg_value)}")

# Get register specification
reg_spec = namednodes.sv.socket0.uncore.pcd.lpss_ctrl.getspec()
print(reg_spec)
```

### Reading Register Fields

```python
# Read specific field from a register
# TODO: Replace with actual field names
field_value = namednodes.sv.socket0.uncore.pcd.lpss_ctrl.field_name.read()

print(f"Field value: {hex(field_value)}")

# Get field specification
field_spec = namednodes.sv.socket0.uncore.pcd.lpss_ctrl.field_name.getspec()
print(field_spec)
```

---

## Register Checkout by Port Type

### I2C Controller Registers

**Common I2C registers to check:**

```python
# TODO: Replace with actual I2C register paths for your platform

# I2C Control Register
# Expected: Controller enabled, master mode, speed mode configured
i2c_ctrl = namednodes.sv.socket0.pcd.search(
    regexpression="i2c.*ctrl|i2c.*con",
    searchType="registers"
)

# I2C Status Register
# Check for: Error flags, FIFO status, activity status
i2c_status = namednodes.sv.socket0.pcd.search(
    regexpression="i2c.*sts|i2c.*status",
    searchType="registers"
)

# I2C Clock Configuration
# Verify: SCL high/low count registers match desired speed
i2c_clk = namednodes.sv.socket0.pcd.search(
    regexpression="i2c.*clk|i2c.*hcnt|i2c.*lcnt",
    searchType="registers"
)

# Print I2C register values
for reg in i2c_ctrl:
    print(f"I2C Register: {reg}")
    # Read and print value
    # value = reg.read()
    # print(f"Value: {hex(value)}")
```

**Key I2C register checks:**
- Control register: Master/slave mode, speed mode (standard/fast/high-speed), controller enable
- Status register: Activity bit, FIFO empty/full, error flags (TX abort, RX overflow)
- Clock configuration: SCL high/low count for target frequency
- Enable register: Controller enable status
- Interrupt status/mask: Unexpected interrupts

---

### I3C Controller Registers

**Common I3C registers to check:**

```python
# TODO: Replace with actual I3C register paths for your platform

# I3C Device Control
i3c_ctrl = namednodes.sv.socket0.pcd.search(
    regexpression="i3c.*ctrl|i3c.*device_ctrl",
    searchType="registers"
)

# I3C Status
i3c_status = namednodes.sv.socket0.pcd.search(
    regexpression="i3c.*sts|i3c.*status",
    searchType="registers"
)

# I3C Queue Status (Command, Response, TX, RX)
i3c_queue = namednodes.sv.socket0.pcd.search(
    regexpression="i3c.*queue|i3c.*fifo",
    searchType="registers"
)
```

**Key I3C register checks:**
- Device control: Enable status, mode (I3C/I2C legacy), hot-join enable
- Status register: Error conditions, queue status, IBI (In-Band Interrupt) pending
- Queue status: Command queue, response queue, transmit/receive data
- Timing configuration: SCL frequency, bus characteristics
- Device address table (DAT): Dynamic address assignments

---

### SPI Controller Registers

**Common SPI registers to check:**

```python
# TODO: Replace with actual SPI register paths for your platform

# SPI Control Register
spi_ctrl = namednodes.sv.socket0.pcd.search(
    regexpression="spi.*ctrl|spi.*control",
    searchType="registers"
)

# SPI Status Register
spi_status = namednodes.sv.socket0.pcd.search(
    regexpression="spi.*sts|spi.*status|spi.*sr",
    searchType="registers"
)

# SPI Configuration
spi_config = namednodes.sv.socket0.pcd.search(
    regexpression="spi.*cfg|spi.*config",
    searchType="registers"
)
```

**Key SPI register checks:**
- Control register: Enable bit, mode (master/slave), CPOL/CPHA settings
- Status register: Busy flag, FIFO status, error flags (TX overflow, RX underflow)
- Baud rate: Clock divider settings for target SPI frequency
- Data frame size: Transfer width (8/16/32 bit)
- Chip select: CS polarity, CS mode

---

### UART Controller Registers

**Common UART registers to check:**

```python
# TODO: Replace with actual UART register paths for your platform

# UART Line Control Register (LCR)
uart_lcr = namednodes.sv.socket0.pcd.search(
    regexpression="uart.*lcr|uart.*line_ctrl",
    searchType="registers"
)

# UART Line Status Register (LSR)
uart_lsr = namednodes.sv.socket0.pcd.search(
    regexpression="uart.*lsr|uart.*line_sts",
    searchType="registers"
)

# UART Divisor Latch (for baud rate)
uart_dll = namednodes.sv.socket0.pcd.search(
    regexpression="uart.*dll|uart.*dlh|uart.*divisor",
    searchType="registers"
)
```

**Key UART register checks:**
- Line Control Register (LCR): Data bits, stop bits, parity, divisor latch access
- Line Status Register (LSR): Data ready, overrun/parity/framing errors, FIFO status
- Divisor latch: Baud rate divisor for target baud rate
- FIFO Control Register: FIFO enable, FIFO depth, trigger levels
- Modem Control Register: RTS/DTR signals (if used)

---

### GPIO Controller Registers

**Common GPIO/Pad Configuration registers:**

```python
# TODO: Replace with actual GPIO register paths for your platform

# GPIO Pad Configuration (DW0 and DW1)
gpio_padcfg = namednodes.sv.socket0.pcd.search(
    regexpression="gpio.*padcfg|gpio.*pad_cfg|gpio.*dw0|gpio.*dw1",
    searchType="registers"
)

# GPIO Community Configuration
gpio_community = namednodes.sv.socket0.pcd.search(
    regexpression="gpio.*community|gpio.*group",
    searchType="registers"
)

# GPIO Ownership
gpio_ownership = namednodes.sv.socket0.pcd.search(
    regexpression="gpio.*owner|gpio.*hostsw",
    searchType="registers"
)
```

**Key GPIO register checks:**
- PADCFG DW0: Pad mode (PMode), GPIO direction (Tx/Rx enable), GPIO input/output state
- PADCFG DW1: Pad termination (pull-up/down/none), interrupt config
- Ownership: Host ownership vs CSME/ISH ownership
- GPI_IS/GPI_IE: Interrupt status and enable for GPIO pads
- Community configuration: Pad group assignments

---

## Common Register Issues

### Reset Value Mismatch
**Symptom:** Register doesn't match expected reset value
**Possible causes:**
- BIOS/firmware modified the register before OS boot
- Previous test left hardware in non-reset state
- Hardware defect or signal integrity issue
- Wrong register path or offset

### Configuration Error
**Symptom:** Register configured incorrectly for intended operation
**Possible causes:**
- Driver bug in register programming
- ACPI/BIOS passed wrong parameters
- Platform-specific configuration not applied
- Register access order violation (some registers require specific sequence)

### Read-Only Field Modified
**Symptom:** Attempt to write read-only field has no effect
**Possible causes:**
- Register field is read-only (check `.getspec()`)
- Register is locked by hardware or firmware
- Wrong access size (some registers require 32-bit access)

### Reserved Bits Set
**Symptom:** Reserved bits have non-zero values
**Possible causes:**
- Hardware bug or signal integrity issue
- Register definition mismatch with actual hardware
- Wrong register offset

---

## Register Checkout Procedure

### Step 1: Identify Target Registers
Based on the failure symptom or debugging goal, identify which LPSS registers to check:
- Control/configuration registers: For functional issues
- Status registers: For error conditions
- Power management registers: For D3/clock gating issues
- Interrupt registers: For interrupt-related issues

### Step 2: Search and Locate Registers
Use PythonSV search to find register paths:

```python
# Example: Finding I2C registers for I2C0 controller
i2c0_regs = namednodes.sv.socket0.pcd.search(
    regexpression="i2c0|i2c_0",
    searchType="registers"
)

for reg in i2c0_regs:
    print(reg)
```

### Step 3: Read Register Values
Read the identified registers and print their values:

```python
# TODO: Replace with actual register path
# reg_value = namednodes.sv.socket0.uncore.pcd.i2c0.ctrl.read()
# print(f"I2C0 Control Register: {hex(reg_value)}")
```

### Step 4: Get Register Specification
Use `.getspec()` to understand register layout and expected values:

```python
# TODO: Replace with actual register path
# reg_spec = namednodes.sv.socket0.uncore.pcd.i2c0.ctrl.getspec()
# print(reg_spec)
```

### Step 5: Compare Against Expected Values
Compare actual values with:
- Reset values from specification
- Expected configured values from driver code
- Known-good values from working systems

### Step 6: Analyze Discrepancies
For any mismatches:
1. Check if the difference is expected (e.g., BIOS configuration)
2. Determine if the value is causing the observed failure
3. Cross-reference with driver code and ACPI tables
4. Check for hardware errata or known issues

---

## Tips and Best Practices

1. **Always unlock ITP first** with `itp.unlock()` before reading registers
2. **Refresh silicon view** with `sv.refresh()` to ensure up-to-date state
3. **Use `.getspec()`** to understand register layout before interpreting values
4. **Search broadly first** then narrow down to specific registers
5. **Read status registers** to identify active error conditions
6. **Compare across working/failing systems** to identify configuration differences
7. **Document register paths** for your specific platform for reuse
8. **Check register access permissions** (some registers may be locked or require specific unlock sequences)

---

## Related Skills

- **fv-lpss/pmode-check**: For GPIO pad mode configuration (subset of GPIO register checkout)
- **fv-lpss/d3-state-check**: For power management register checkout
- **fv-lpss/clock-gating**: For clock-related register checkout
- **pysv**: General PythonSV usage and register access patterns

---

## TODO: Platform-Specific Information Needed

To make this skill fully functional for your platform, provide:

1. **Actual LPSS register paths** in PythonSV namespace (e.g., `namednodes.sv.socket0.uncore.lpss.i2c0.ctrl`)
2. **Register reset values** from hardware specification
3. **Expected configured values** from driver code or BIOS settings
4. **Register access restrictions** (locked registers, special unlock sequences)
5. **Platform-specific register names** (may vary by SoC generation)
