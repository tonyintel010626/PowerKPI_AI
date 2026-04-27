---
name: fv-lpss/d3-state-check
description: "Verify LPSS ports correctly enter and exit D3 power states"
---

# LPSS D3 Power State Check

This skill provides procedures for verifying whether LPSS (Low Power Subsystem) controllers correctly enter and exit D3 power states.

## Overview

D-states (Device Power States) are ACPI-defined power states for PCI/PCIe devices:

- **D0**: Fully operational, device active
- **D1/D2**: Intermediate low-power states (rarely used)
- **D3hot**: Low power, device can wake via PME (Power Management Event)
- **D3cold**: Lowest power, device powered off completely

For LPSS controllers, proper D3 entry is critical for system low-power states like S0ix (Modern Standby) and battery life.

---

## Quick Status Check (RECOMMENDED)

Use the comprehensive status check script to validate all LPSS port states:

```bash
python check_all_lpss_ports_status.py
```

**Features:**
- ✅ Complete validation of all 3 D3 criteria (PSF, PMU, MMR)
- ✅ Checks PSF function disable status for each port
- ✅ Validates PMU and MMR subsystem-level registers
- ✅ Shows per-port power states (D0/D3) with detailed validation
- ✅ Identifies mismatches between port and subsystem states

**Performance:** ~25-30 seconds (includes PythonSV initialization)

**Example Output:**
```
================================================================================
LPSS Port Status Check - Validating All 3 Criteria
================================================================================
✅ CRITERIA 1: LPSS fuse status OK
💤 CRITERIA 2: LPSS subsystem is in D3 (PMU)
💤 CRITERIA 3: LPSS D3 condition is met (MMR)

Port            Status               Validation Details
--------------------------------------------------------------------------------
I2C0            D3 (Low Power)       powerstate=3
I2C1            D3 (Low Power)       powerstate=3
I2C2            D3 (Low Power)       powerstate=3
I2C3            D3 (Low Power)       powerstate=3
I2C4            FUNCTION DISABLED    PSF fundis=1
I2C5            FUNCTION DISABLED    PSF fundis=1
...
================================================================================
Summary:
✅ D0 (Active):        0 ports
💤 D3 (Low Power):     4 ports - I2C0, I2C1, I2C2, I2C3
❌ Function Disabled:  12 ports - I2C4, I2C5, I3C0-I3C3, SPI0-SPI2, UART0-UART2
================================================================================
```

---

## Why D3 State Matters for LPSS

### Power Management Impact
- LPSS controllers must enter D3 when idle to allow SoC to enter low-power states
- Failure to enter D3 can block S0ix (Modern Standby) entry
- Each LPSS controller that stays in D0 consumes power and increases platform power

### Common D3 Issues
1. **Controller stuck in D0**: Most common issue, prevents system low-power state
2. **D3 entry delayed**: Takes too long to enter D3, causing race conditions
3. **Unexpected D3 exit**: Controller wakes from D3 unexpectedly
4. **D3cold not supported**: Platform only supports D3hot, limiting power savings

---

## PCI Power Management Registers

D-state is controlled through PCI configuration space registers:

### PMCSR (Power Management Control/Status Register)

Located in PCI configuration space at the Power Management Capability offset.

**Typical structure:**
- **Offset 0x00**: Power Management Capabilities (read-only)
- **Offset 0x04**: PMCSR (Power Management Control/Status Register)

**PMCSR bit layout:**
- **Bits [1:0]**: PowerState — Current device power state
  - `00b` = D0 (active)
  - `01b` = D1
  - `10b` = D2
  - `11b` = D3hot
- **Bit [8]**: PME_En — Enable PME generation from power state
- **Bit [15]**: PME_Status — PME signal asserted (write-1-to-clear)

---

## PythonSV Access to PMCSR

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

### Searching for LPSS PCI Configuration Space

```python
# Search for LPSS PCI configuration registers
lpss_pci_cfg = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*pci|lpss.*cfg",
    searchType="registers"
)

# Search for power management capability registers
pm_cap_regs = namednodes.sv.socket0.pcd.search(
    regexpression="pm_cap|pmcsr|power_mgmt",
    searchType="registers"
)

# Print found registers
for reg in pm_cap_regs:
    print(f"PM Register: {reg}")
```

### Reading PMCSR Register

```python
# TODO: Replace with actual LPSS PMCSR register path

def read_pmcsr(controller_name):
    """
    Read PMCSR register for an LPSS controller.
    
    Args:
        controller_name: Name of LPSS controller (e.g., 'I2C0', 'SPI0')
    
    Returns:
        PMCSR register value
    """
    # Example path (replace with actual path)
    # pmcsr = namednodes.sv.socket0.uncore.lpss.i2c0.pci_cfg.pmcsr.read()
    
    # Alternative: Access via PCI config space offset
    # pci_cfg_base = namednodes.sv.socket0.uncore.lpss.i2c0.pci_cfg_space
    # pmcsr = pci_cfg_base.read_dword(0x84)  # Example offset, verify actual offset
    
    # return pmcsr
    pass  # Remove when implementing

def extract_power_state(pmcsr_value):
    """
    Extract current power state from PMCSR value.
    
    Args:
        pmcsr_value: PMCSR register value
    
    Returns:
        Power state (0=D0, 1=D1, 2=D2, 3=D3hot)
    """
    power_state = pmcsr_value & 0x3  # Bits [1:0]
    
    state_names = {0: 'D0', 1: 'D1', 2: 'D2', 3: 'D3hot'}
    state_name = state_names.get(power_state, 'Unknown')
    
    return power_state, state_name

# Example usage
# pmcsr = read_pmcsr('I2C0')
# power_state, state_name = extract_power_state(pmcsr)
# print(f"I2C0 Power State: {state_name} ({power_state})")
```

---

## D3 State Verification Procedure

### Step 1: Identify Target Controller

Determine which LPSS controller to check based on:
- Test failure logs
- Power consumption analysis (which controller is preventing low-power state)
- System idle scenario (all unused controllers should be in D3)

### Step 2: Read Current D-State

```python
def check_d_state(controller_name):
    """Check current D-state for an LPSS controller."""
    
    print(f"\n=== Checking D-State for {controller_name} ===")
    
    # Read PMCSR
    # pmcsr = read_pmcsr(controller_name)
    # power_state, state_name = extract_power_state(pmcsr)
    
    # print(f"Current Power State: {state_name} ({power_state})")
    # print(f"PMCSR Value: {hex(pmcsr)}")
    
    # Check PME_En bit
    # pme_en = (pmcsr >> 8) & 0x1
    # print(f"PME Enable: {pme_en}")
    
    # Check PME_Status bit
    # pme_status = (pmcsr >> 15) & 0x1
    # print(f"PME Status: {pme_status}")
    
    pass  # Remove when implementing
```

### Step 3: Verify Expected D-State

```python
def verify_expected_d_state(controller_name, expected_state):
    """
    Verify controller is in expected D-state.
    
    Args:
        controller_name: Name of LPSS controller
        expected_state: Expected D-state (0=D0, 3=D3hot)
    
    Returns:
        True if state matches, False otherwise
    """
    # pmcsr = read_pmcsr(controller_name)
    # actual_state, state_name = extract_power_state(pmcsr)
    
    # expected_names = {0: 'D0', 3: 'D3hot'}
    # expected_name = expected_names.get(expected_state, 'Unknown')
    
    # if actual_state == expected_state:
    #     print(f"✓ {controller_name} in expected state {expected_name}")
    #     return True
    # else:
    #     print(f"✗ {controller_name} state mismatch!")
    #     print(f"  Expected: {expected_name} ({expected_state})")
    #     print(f"  Actual: {state_name} ({actual_state})")
    #     return False
    
    pass  # Remove when implementing
```

### Step 4: Check D3 Entry Prerequisites

Before a controller can enter D3, certain conditions must be met:

```python
def check_d3_prerequisites(controller_name):
    """Check if prerequisites for D3 entry are met."""
    
    print(f"\n=== Checking D3 Prerequisites for {controller_name} ===")
    
    prerequisites_met = True
    
    # 1. No active transactions
    print("1. Checking for active transactions...")
    # Read controller status register
    # status = namednodes.sv.socket0.uncore.lpss.controller.status.read()
    # if status & ACTIVITY_BIT:
    #     print("   ✗ Controller has active transactions")
    #     prerequisites_met = False
    # else:
    #     print("   ✓ No active transactions")
    
    # 2. Clock gated
    print("2. Checking clock gating...")
    # Check if controller clock is gated (see fv-lpss/clock-gating skill)
    # if not clock_is_gated(controller_name):
    #     print("   ✗ Clock not gated (required for D3)")
    #     prerequisites_met = False
    # else:
    #     print("   ✓ Clock gated")
    
    # 3. Driver released device
    print("3. Checking driver state...")
    # This typically requires OS-side checks (see below)
    print("   (Check driver state from OS side)")
    
    # 4. Wake capability configured (for D3hot with wake)
    print("4. Checking PME wake configuration...")
    # pmcsr = read_pmcsr(controller_name)
    # pme_en = (pmcsr >> 8) & 0x1
    # if pme_en:
    #     print("   ✓ PME wake enabled")
    # else:
    #     print("   ⚠ PME wake disabled (D3hot without wake, or D3cold)")
    
    return prerequisites_met
```

---

## Platform-Specific LPSS Configuration

### Novalake Platform
- **6 I2C controllers**: I2C0, I2C1, I2C2, I2C3, I2C4, I2C5
- **4 I3C controllers**: I3C0, I3C1, I3C2, I3C3
- **3 SPI controllers**: SPI0, SPI1, SPI2
- **3 UART controllers**: UART0, UART1, UART2 (appears as HSUART0, HSUART1, HSUART2 in PythonSV)
- **No GPIO controllers** in LPSS subsystem

**Note:** UART controllers are accessed as `hsuart0`, `hsuart1`, `hsuart2` in PythonSV namednodes, not as `uart0`, `uart1`, `uart2`.

### PythonSV Access Paths
- I2C: `namednodes.sv.socket0.pcd.lpss.i2c{0-5}`
- I3C: `namednodes.sv.socket0.pcd.lpss.i3c{0-3}` (naming may vary)
- SPI: `namednodes.sv.socket0.pcd.lpss.spi{0-2}`
- UART: `namednodes.sv.socket0.pcd.lpss.hsuart{0-2}`

---

## D3 Check by Controller Type

### I2C Controllers

```python
def verify_i2c_d3_all():
    """Verify D3 state for all I2C controllers (Novalake: 6 controllers)."""
    
    i2c_controllers = ['I2C0', 'I2C1', 'I2C2', 'I2C3', 'I2C4', 'I2C5']
    
    for controller in i2c_controllers:
        # Check if controller is in use
        # in_use = check_controller_in_use(controller)
        
        # if not in_use:
        #     # Unused controller should be in D3
        #     verify_expected_d_state(controller, expected_state=3)
        # else:
        #     # In-use controller should be in D0
        #     verify_expected_d_state(controller, expected_state=0)
        
        pass  # Remove when implementing
```

### I3C Controllers

```python
def verify_i3c_d3_all():
    """Verify D3 state for all I3C controllers (Novalake: 4 controllers)."""
    
    i3c_controllers = ['I3C0', 'I3C1', 'I3C2', 'I3C3']
    
    for controller in i3c_controllers:
        # Same logic as I2C
        # Note: I3C controller naming in PythonSV may differ from I2C
        # Verify actual naming convention on your platform
        pass  # Remove when implementing
```

### SPI Controllers

```python
def verify_spi_d3_all():
    """Verify D3 state for all SPI controllers (Novalake: 3 controllers)."""
    
    spi_controllers = ['SPI0', 'SPI1', 'SPI2']
    
    for controller in spi_controllers:
        # Same logic as I2C
        pass  # Remove when implementing
```

### UART Controllers

```python
def verify_uart_d3_all():
    """Verify D3 state for all UART controllers (Novalake: 3 controllers).
    
    Note: UART controllers appear as HSUART (High-Speed UART) in PythonSV.
    Access via: namednodes.sv.socket0.pcd.lpss.hsuart{0-2}
    """
    
    # Use HSUART naming convention for Novalake platform
    uart_controllers = ['HSUART0', 'HSUART1', 'HSUART2']
    
    for controller in uart_controllers:
        # Same logic as I2C
        # Access path: socket0.pcd.lpss.hsuart0 (lowercase in PythonSV)
        pass  # Remove when implementing
```

---

## OS-Side D3 Verification

Hardware D-state must match software/driver expectations. Use these OS-side checks:

### Windows

```powershell
# PowerShell: Check device power state

# Get device power state from Device Manager
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*I2C*"} | Format-Table FriendlyName, Status, InstanceId

# Check driver power state via WMI
Get-WmiObject -Class Win32_PnPEntity | Where-Object {$_.Name -like "*I2C*"} | Select-Object Name, Status, ConfigManagerErrorCode

# Use powercfg to check device power state
powercfg /devicequery all_devices
powercfg /devicequery wake_armed

# Check if device is in D3 via power settings
powercfg /energy /duration 10
# Review generated HTML report for devices preventing low-power states
```

### Linux

```bash
# Check device power state via sysfs
cat /sys/bus/pci/devices/0000:00:15.0/power/runtime_status
# Should show "suspended" for D3, "active" for D0

# Check runtime PM statistics
cat /sys/bus/pci/devices/0000:00:15.0/power/runtime_active_time
cat /sys/bus/pci/devices/0000:00:15.0/power/runtime_suspended_time

# Check autosuspend delay
cat /sys/bus/pci/devices/0000:00:15.0/power/autosuspend_delay_ms

# Enable runtime PM debug
echo 'module i2c_designware_platform +p' > /sys/kernel/debug/dynamic_debug/control
dmesg | grep -i "runtime pm"
```

---

## Common D3 Entry Failures

### Issue 1: Controller Stuck in D0

**Symptoms:**
- PMCSR shows D0 when controller should be idle
- System cannot enter S0ix/Modern Standby
- Higher than expected platform power consumption

**Root causes:**
- Driver holding active reference (Windows: IRP_MN_WAIT_WAKE pending)
- Active I/O transaction in progress
- Clock not gated (prerequisite for D3)
- BIOS/ACPI configuration preventing D3
- Connected device holding controller active

**Debug steps:**
1. Check if driver released device (OS power management logs)
2. Verify no active transactions (controller status register)
3. Check clock gating status (use fv-lpss/clock-gating skill)
4. Review ACPI _PS3 method execution
5. Check for connected device activity

### Issue 2: D3 Entry Delayed

**Symptoms:**
- Controller eventually enters D3 but takes longer than expected
- Race condition between D3 entry and system low-power state entry
- Intermittent S0ix entry failures

**Root causes:**
- Driver autosuspend delay too long
- Delayed transaction completion
- Firmware delay in acknowledging D3 request
- Interrupt storm preventing idle

**Debug steps:**
1. Check driver autosuspend timeout settings
2. Monitor time from last transaction to D3 entry
3. Check for unexpected interrupts during idle period
4. Review driver power management callback timing

### Issue 3: Unexpected D3 Exit (Spurious Wake)

**Symptoms:**
- Controller enters D3 but immediately exits back to D0
- PME_Status bit set unexpectedly
- Increased power consumption due to D0/D3 cycling

**Root causes:**
- Connected device generating interrupt/wake signal
- EMI/signal integrity causing false wake detection
- PME configuration error (PME_En set when not intended)
- Shared interrupt line causing wake

**Debug steps:**
1. Check PME_Status bit after wake
2. Identify wake source (check interrupt status registers)
3. Review connected device behavior
4. Check if wake is expected or spurious

### Issue 4: D3cold Not Supported

**Symptoms:**
- Controller can only enter D3hot (PMCSR = 3) but not D3cold
- Higher power consumption than expected in D3
- Wake capability available from D3hot but not needed

**Root causes:**
- Platform doesn't support power rail gating for LPSS
- BIOS/ACPI doesn't implement _PS3 with power rail control
- Hardware limitation (power rails always on)

**Debug steps:**
1. Check ACPI _PR3 (Power Resources for D3cold) availability
2. Verify if platform supports LPSS power rail gating
3. Check PMC (Power Management Controller) for power rail control
4. Review platform power architecture

---

## D3 Entry/Exit Scenario Testing

### Test Scenario 1: Idle D3 Entry

```python
def test_idle_d3_entry(controller_name):
    """Test D3 entry after controller goes idle."""
    
    print(f"\n=== Testing Idle D3 Entry for {controller_name} ===")
    
    # Step 1: Verify controller is in D0 initially
    print("Step 1: Verify initial D0 state...")
    # verify_expected_d_state(controller_name, expected_state=0)
    
    # Step 2: Ensure no active transactions
    print("Step 2: Wait for controller to become idle...")
    # Wait for transactions to complete
    # time.sleep(2)
    
    # Step 3: Trigger driver idle timeout
    print("Step 3: Wait for driver autosuspend timeout...")
    # Wait for OS runtime PM to suspend device
    # time.sleep(10)  # Adjust based on autosuspend delay
    
    # Step 4: Verify D3 entry
    print("Step 4: Verify D3 state...")
    # verify_expected_d_state(controller_name, expected_state=3)
    
    # Step 5: Verify clock gated
    print("Step 5: Verify clock gated...")
    # check_clock_gating(controller_name)
    
    pass  # Remove when implementing
```

### Test Scenario 2: Wake from D3

```python
def test_wake_from_d3(controller_name):
    """Test wake from D3 when controller is accessed."""
    
    print(f"\n=== Testing Wake from D3 for {controller_name} ===")
    
    # Step 1: Verify controller in D3
    print("Step 1: Verify D3 state...")
    # verify_expected_d_state(controller_name, expected_state=3)
    
    # Step 2: Trigger wake event (from OS side - access device)
    print("Step 2: Trigger wake event (access device from OS)...")
    print("   (Perform I/O transaction from OS/driver)")
    
    # Step 3: Verify D0 transition
    print("Step 3: Verify D0 transition after wake...")
    # time.sleep(0.5)  # Allow time for wake
    # verify_expected_d_state(controller_name, expected_state=0)
    
    # Step 4: Verify clock ungated
    print("Step 4: Verify clock ungated...")
    # check_clock_gating(controller_name)
    
    pass  # Remove when implementing
```

---

## Tips and Best Practices

1. **Always check clock gating first**: Clock must be gated before D3 entry is possible
2. **Correlate hardware and software state**: Use both PythonSV and OS tools for complete picture
3. **Check PME configuration**: PME_En should match whether wake-from-D3 is intended
4. **Monitor D3 entry latency**: Slow D3 entry can cause system-level issues
5. **Test all controllers**: Don't assume all controllers behave identically
6. **Verify under different scenarios**: Idle, active, wake, etc.
7. **Check for D3cold support**: Platform-dependent, verify ACPI _PR3 presence
8. **Use OS power management logs**: Essential for understanding driver behavior

---

## Related Skills

- **fv-lpss/clock-gating**: Clock gating is a prerequisite for D3 entry
- **fv-lpss/ip-config**: Verify LPSS IP is properly enumerated before checking D-state
- **fv-lpss/failure-analysis**: Analyze D3-related test failures from NGA

---

## TODO: Platform-Specific Information Needed

To make this skill fully functional, provide:

1. **PMCSR register paths** in PythonSV for each LPSS controller
2. **PM Capability offset** in PCI config space for LPSS devices
3. **Controller status registers** for checking active transaction state
4. **Platform D3cold support**: Does the platform support D3cold for LPSS? Which power rails control LPSS power?
5. **Expected D3 entry latency**: How long should D3 entry take on your platform?
