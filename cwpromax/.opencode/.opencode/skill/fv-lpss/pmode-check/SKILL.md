---
name: fv-lpss/pmode-check
description: "Verify GPIO pad mode (PMode) configuration for LPSS native function routing"
---

# LPSS PMode (Pad Mode) Check

This skill provides procedures for verifying GPIO pad mode (PMode) configuration to ensure correct native function routing for LPSS controllers.

## Overview

**PMode (Pad Mode)** in Intel architecture refers to the configuration setting that determines how a GPIO pad functions:

- **PMode = 0h**: Standard GPIO operation (software-controlled input/output)
- **PMode ≠ 0h**: Native function mode (hardware-specific feature routing)

For LPSS controllers (I2C, I3C, SPI, UART) to function, their signal pads must be configured with the correct PMode values to route controller signals to physical pins.

---

## Why PMode Matters for LPSS

Each LPSS controller requires specific GPIO pads configured in native function mode:

### Example: I2C Controller
An I2C controller needs two pads:
- **I2C_SDA** (Serial Data): Bidirectional data line
- **I2C_SCL** (Serial Clock): Clock line

If these pads are left in GPIO mode (PMode=0), the I2C controller cannot communicate with external devices, even if the controller registers are correctly configured.

### Common PMode Issues
1. **Pad stuck in GPIO mode (PMode=0)**: Most common issue. Pad not switched to native function.
2. **Wrong native function selected**: PMode set to non-zero value, but wrong function for the LPSS port.
3. **Pad ownership conflict**: Pad owned by CSME/ISH instead of host, preventing PMode configuration.
4. **BIOS configuration error**: ACPI or BIOS didn't configure PMode correctly.

---

## PythonSV Access to Pad Configuration

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

### Searching for GPIO Pad Configuration Registers

```python
# Search for GPIO PADCFG registers (DW0 contains PMode field)
padcfg_regs = namednodes.sv.socket0.pcd.search(
    regexpression="padcfg.*dw0|pad_cfg.*dw0|gpio.*dw0",
    searchType="registers"
)

# Search for specific community GPIO registers
gpio_community = namednodes.sv.socket0.pcd.search(
    regexpression="gpio.*community",
    searchType="registers"
)

# Print found registers
for reg in padcfg_regs:
    print(f"Pad Config Register: {reg}")
```

### GPIO Pad Configuration Register Structure

Most Intel platforms use a standard GPIO pad configuration structure:

**PADCFG DW0 (Double Word 0)** — Primary configuration:
- **Bits [31:30]**: Reserved or pad reset config
- **Bits [29:28]**: Reserved  
- **Bits [27:25]**: Reserved
- **Bits [24:20]**: Reserved
- **Bits [13:10]**: **PMode** — Pad Mode (native function selector)
- **Bits [9:8]**: GPIO Tx/Rx enable
- **Bit [1]**: GPIO Tx state (if in GPIO mode)
- **Bit [0]**: GPIO Rx state (if in GPIO mode)

**PADCFG DW1 (Double Word 1)** — Electrical configuration:
- **Bits [13:10]**: Pad termination (pull-up, pull-down, none)
- **Bits [9:0]**: Interrupt configuration

**Note:** Exact bit positions may vary by platform. Use `.getspec()` to verify.

---

## TODO: Platform-Specific PythonSV Access Method

**⚠️ Platform-specific information needed:**

Please provide the PythonSV method for accessing pad configuration on your platform. Common patterns:

### Option 1: Direct pad register access
```python
# Example format (replace with actual paths)
# pad_dw0 = namednodes.sv.socket0.uncore.gpio.community0.pad_X.dw0.read()
# pmode = (pad_dw0 >> 10) & 0xF  # Extract PMode bits [13:10]
```

### Option 2: GPIO community-based access
```python
# Example format (replace with actual paths)
# gpio_base = namednodes.sv.socket0.uncore.gpio_community_0
# pad_cfg_dw0 = gpio_base.padcfg_dw0[pad_number].read()
```

### Option 3: Using utility functions
```python
# Example format (replace with actual utility module)
# from gpio_utils import read_pad_config
# pad_cfg = read_pad_config(community=0, pad=25)
# pmode = pad_cfg['pmode']
```

**Please specify which method applies to your platform and provide actual register paths.**

---

## Reading PMode Value

### Generic Template (Adapt for Your Platform)

```python
# TODO: Replace with actual register path and bit extraction method

def read_pmode(pad_register_path):
    """
    Read PMode value from a GPIO pad configuration register.
    
    Args:
        pad_register_path: PythonSV path to PADCFG DW0 register
    
    Returns:
        PMode value (0-15, typically 4-bit field)
    """
    # Read DW0
    dw0_value = pad_register_path.read()
    
    # Extract PMode field (bits [13:10] on most platforms)
    pmode = (dw0_value >> 10) & 0xF
    
    return pmode

# Example usage (replace with actual path)
# pmode = read_pmode(namednodes.sv.socket0.uncore.gpio.community0.pad_25.dw0)
# print(f"PMode: {pmode} ({hex(pmode)})")
```

---

## TODO: PMode Value to Native Function Mapping

**⚠️ Platform-specific information needed:**

Each platform has different PMode value mappings for LPSS native functions. Please provide the mapping table for your platform.

### Example Mapping Structure (Replace with Actual Values)

```python
# TODO: Fill in actual PMode mappings for your platform

# I2C PMode mappings (example - not actual values)
I2C_PMODE_MAP = {
    'I2C0_SDA': {'pad': 'GPP_A25', 'pmode': 1},  # Example: PMode=1 for I2C0_SDA
    'I2C0_SCL': {'pad': 'GPP_A24', 'pmode': 1},  # Example: PMode=1 for I2C0_SCL
    'I2C1_SDA': {'pad': 'GPP_B10', 'pmode': 2},  # Example: PMode=2 for I2C1_SDA
    'I2C1_SCL': {'pad': 'GPP_B11', 'pmode': 2},
    # ... more I2C mappings
}

# I3C PMode mappings (example - not actual values)
I3C_PMODE_MAP = {
    'I3C0_SDA': {'pad': 'GPP_C20', 'pmode': 3},
    'I3C0_SCL': {'pad': 'GPP_C21', 'pmode': 3},
    # ... more I3C mappings
}

# SPI PMode mappings (example - not actual values)
SPI_PMODE_MAP = {
    'SPI0_CLK': {'pad': 'GPP_D0', 'pmode': 1},
    'SPI0_MISO': {'pad': 'GPP_D1', 'pmode': 1},
    'SPI0_MOSI': {'pad': 'GPP_D2', 'pmode': 1},
    'SPI0_CS0': {'pad': 'GPP_D3', 'pmode': 1},
    # ... more SPI mappings
}

# UART PMode mappings (example - not actual values)
UART_PMODE_MAP = {
    'UART0_RXD': {'pad': 'GPP_E8', 'pmode': 1},
    'UART0_TXD': {'pad': 'GPP_E9', 'pmode': 1},
    'UART0_RTS': {'pad': 'GPP_E10', 'pmode': 1},
    'UART0_CTS': {'pad': 'GPP_E11', 'pmode': 1},
    # ... more UART mappings
}
```

**Information needed:**
1. Pad names (e.g., GPP_A25, GPP_B10) for each LPSS signal
2. Expected PMode values for each native function
3. Pad community assignments (Community 0, 1, 2, etc.)
4. Alternative function mappings if multiple PMode values can select the same function

---

## PMode Verification Procedure

### Step 1: Identify Target Pads
Based on the LPSS controller being debugged, identify which pads need verification.

**Example: I2C0 controller**
- I2C0_SDA pad
- I2C0_SCL pad

### Step 2: Read Current PMode Values

```python
# TODO: Replace with actual implementation using your platform's method

def verify_i2c0_pmode():
    """Verify PMode configuration for I2C0 controller."""
    
    # Read I2C0_SDA PMode
    # sda_pmode = read_pmode(namednodes.sv.socket0.uncore.gpio.pad_i2c0_sda.dw0)
    
    # Read I2C0_SCL PMode
    # scl_pmode = read_pmode(namednodes.sv.socket0.uncore.gpio.pad_i2c0_scl.dw0)
    
    # Expected values (from platform mapping)
    # expected_pmode = 1  # Example
    
    # Compare
    # if sda_pmode != expected_pmode:
    #     print(f"ERROR: I2C0_SDA PMode mismatch. Expected: {expected_pmode}, Actual: {sda_pmode}")
    # else:
    #     print(f"OK: I2C0_SDA PMode correct ({sda_pmode})")
    
    # if scl_pmode != expected_pmode:
    #     print(f"ERROR: I2C0_SCL PMode mismatch. Expected: {expected_pmode}, Actual: {scl_pmode}")
    # else:
    #     print(f"OK: I2C0_SCL PMode correct ({scl_pmode})")
    
    pass  # Remove when implementing

# Run verification
# verify_i2c0_pmode()
```

### Step 3: Check for Common Misconfiguration

```python
def check_pmode_stuck_in_gpio(pad_name, actual_pmode, expected_pmode):
    """Check if pad is stuck in GPIO mode when it should be in native mode."""
    
    if actual_pmode == 0 and expected_pmode != 0:
        print(f"ERROR: {pad_name} stuck in GPIO mode (PMode=0)!")
        print(f"       Expected PMode={expected_pmode} for native function")
        print(f"       Possible causes:")
        print(f"         - BIOS/ACPI didn't configure pad")
        print(f"         - Driver failed to set PMode")
        print(f"         - Pad locked by firmware")
        return False
    
    if actual_pmode != 0 and actual_pmode != expected_pmode:
        print(f"WARNING: {pad_name} in native mode but wrong PMode!")
        print(f"         Expected: {expected_pmode}, Actual: {actual_pmode}")
        print(f"         This may select wrong native function")
        return False
    
    return True
```

### Step 4: Verify Pad Ownership

Pads can be owned by different entities (Host, CSME, ISH). Only the owner can configure PMode.

```python
# TODO: Add pad ownership check using your platform's method

def check_pad_ownership(pad_name):
    """Check if pad is owned by host (required for PMode configuration)."""
    
    # Read ownership register
    # ownership_reg = namednodes.sv.socket0.uncore.gpio.hostsw_own.read()
    # OR
    # ownership_reg = namednodes.sv.socket0.uncore.gpio.pad_own.read()
    
    # Check if host owns the pad
    # Typical encoding: 0 = ACPI/Host, 1 = CSME, 2 = ISH
    
    # if ownership != HOST:
    #     print(f"ERROR: {pad_name} not owned by host!")
    #     print(f"       Current owner: {owner_name}")
    #     print(f"       Cannot configure PMode without host ownership")
    #     return False
    
    # print(f"OK: {pad_name} owned by host")
    return True
```

---

## PMode Check by Controller Type

### I2C Controllers

```python
# TODO: Implement I2C PMode verification for all I2C controllers

def verify_i2c_pmode_all():
    """Verify PMode for all I2C controllers."""
    
    # I2C controllers to check (adjust for your platform)
    i2c_controllers = ['I2C0', 'I2C1', 'I2C2', 'I2C3', 'I2C4', 'I2C5', 'I2C6', 'I2C7']
    
    for controller in i2c_controllers:
        print(f"\n=== Checking {controller} PMode ===")
        
        # Get pad mappings for this controller
        # sda_pad = I2C_PMODE_MAP[f'{controller}_SDA']
        # scl_pad = I2C_PMODE_MAP[f'{controller}_SCL']
        
        # Verify each pad
        # verify_single_pad(sda_pad)
        # verify_single_pad(scl_pad)
        
        pass  # Remove when implementing
```

### I3C Controllers

```python
# TODO: Implement I3C PMode verification

def verify_i3c_pmode_all():
    """Verify PMode for all I3C controllers."""
    
    # I3C uses same two-wire interface as I2C
    # Check SDA and SCL pads for each I3C controller
    
    pass  # Remove when implementing
```

### SPI Controllers

```python
# TODO: Implement SPI PMode verification

def verify_spi_pmode_all():
    """Verify PMode for all SPI controllers."""
    
    # SPI typically has 4+ pads:
    # - CLK (Clock)
    # - MISO (Master In, Slave Out)
    # - MOSI (Master Out, Slave In)
    # - CS0, CS1, ... (Chip Select lines)
    
    pass  # Remove when implementing
```

### UART Controllers

```python
# TODO: Implement UART PMode verification

def verify_uart_pmode_all():
    """Verify PMode for all UART controllers."""
    
    # UART typically has 2-4 pads:
    # - RXD (Receive Data)
    # - TXD (Transmit Data)
    # - RTS (Request To Send) - optional
    # - CTS (Clear To Send) - optional
    
    pass  # Remove when implementing
```

---

## Common PMode Issues and Root Causes

### Issue 1: Pad Stuck in GPIO Mode (PMode=0)

**Symptoms:**
- LPSS controller configured correctly but not communicating
- No signal activity on physical pins
- Device enumeration works but data transfer fails

**Root causes:**
- BIOS/ACPI didn't configure PMode during boot
- Driver failed to set PMode during initialization
- Pad configuration register locked by firmware
- Wrong pad selected in BIOS configuration

**Debug steps:**
1. Read current PMode value (should be non-zero for native function)
2. Check if pad is locked (PADCFGLOCK register)
3. Check ACPI tables for pad configuration methods
4. Check driver code for pad configuration sequence

### Issue 2: Wrong Native Function Selected

**Symptoms:**
- PMode is non-zero but wrong value
- LPSS controller doesn't function despite pad not being in GPIO mode
- Signal integrity issues or wrong protocol on pins

**Root causes:**
- Platform configuration error (wrong PMode value in mapping table)
- Multiple functions multiplexed on same pad, wrong one selected
- Platform-specific PMode encoding differs from expected

**Debug steps:**
1. Verify expected PMode value from platform specification
2. Check if pad supports multiple native functions
3. Cross-reference with working platform configuration

### Issue 3: Pad Ownership Conflict

**Symptoms:**
- Cannot configure PMode (writes ignored)
- Pad owned by CSME/ISH instead of host
- Ownership register shows non-host owner

**Root causes:**
- BIOS assigned pad to wrong owner
- CSME/ISH firmware claimed pad ownership
- Platform configuration error in BIOS

**Debug steps:**
1. Read pad ownership register
2. Check BIOS settings for pad ownership assignment
3. Verify CSME/ISH firmware configuration
4. Check if ownership can be changed (some pads are fixed-ownership)

---

## Tips and Best Practices

1. **Check PMode before debugging controller**: Many LPSS issues are actually pad configuration problems, not controller issues
2. **Verify all pads for a controller**: Don't assume if one pad is correct, all are correct
3. **Check ownership first**: If ownership is wrong, PMode configuration will fail silently
4. **Use platform-specific documentation**: PMode values vary significantly between platforms
5. **Compare with working configuration**: If available, compare PMode values with a known-good system
6. **Check pad locking**: Some platforms lock pad configuration after BIOS, preventing runtime changes
7. **Verify ACPI methods**: ACPI may have methods (_ON, _OFF, _PS0, _PS3) that reconfigure pads during power transitions

---

## Related Skills

- **fv-lpss/register-checkout**: For checking GPIO controller registers (PADCFG DW0/DW1)
- **fv-lpss/ip-config**: For verifying LPSS IP enumeration (prerequisite to PMode check)
- **pysv**: General PythonSV register access patterns

---

## Next Steps After This Skill is Completed

Once you provide the platform-specific information (PythonSV access method and PMode mappings), this skill will be able to:

1. Read current PMode values for all LPSS controller pads
2. Compare against expected native function assignments
3. Identify pads stuck in GPIO mode
4. Detect wrong native function selection
5. Check pad ownership conflicts
6. Generate a comprehensive PMode configuration report

**Please provide:**
1. PythonSV register paths for GPIO PADCFG DW0 registers
2. PMode bit field positions (if different from bits [13:10])
3. Complete pad-to-native-function mapping table for I2C, I3C, SPI, UART controllers on your platform
