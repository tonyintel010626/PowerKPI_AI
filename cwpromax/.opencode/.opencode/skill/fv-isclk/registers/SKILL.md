# FV-ISClk Registers Sub-Skill

**Owner**: Ooi, Ling Wei (lingweio)  
**Parent Skill**: `fv-isclk`  
**Agent**: `FV-ISClk`

---

## Overview

This sub-skill provides comprehensive knowledge of ISClk register maps, error handling mechanisms, and PythonSV-based register access patterns for NVL platforms. It covers PLL configuration registers, clock control registers (dividers, muxes, gating), error status and reporting registers, sTRC (System Trace Controller) integration, and Clock Monitor error detection.

**Key Focus Areas**:
- PLL configuration and status registers
- Clock control registers (dividers, muxes, gating)
- Error status and reporting registers
- sTRC (System Trace Controller) integration
- Clock Monitor error detection and logging
- PythonSV namednodes for register access
- Register access patterns and side effects
- Common register access issues and debugging

---

## HAS-First Policy

**ALWAYS query Co-Design** before making register map decisions or assumptions.

**Primary HAS Document**:
- `Chap44_0_NVL_PCH_Internal_Clocks.html` - ISClk register specifications

**Co-Design Query Examples**:
```
"Show me the ISClk PLL configuration registers from Chap44_0_NVL_PCH_Internal_Clocks.html"
"What are the ISClk clock gating control registers for NVL PCH?"
"Show me the ISClk error status registers and sTRC integration from Chap44_0"
"What are the Clock Monitor configuration registers in ISClk?"
```

---

## ISClk Register Categories

### 1. PLL Configuration Registers

**Main PLL (Fabric PLL)**:
- `MAIN_PLL_ENABLE` - PLL enable/disable control
- `MAIN_PLL_FREQ_SEL` - Frequency selection (e.g., 1000MHz, 800MHz)
- `MAIN_PLL_SSC_CTRL` - Spread spectrum configuration (enable, center/down spread, modulation depth)
- `MAIN_PLL_LOCK_STATUS` - Lock status bit (read-only)
- `MAIN_PLL_CAL_CTRL` - Calibration control (temperature compensation)

**HP PLL (High-Performance PLL)**:
- `HP_PLL_ENABLE`
- `HP_PLL_FREQ_SEL`
- `HP_PLL_SSC_CTRL`
- `HP_PLL_LOCK_STATUS`
- `HP_PLL_CAL_CTRL`

**OC PLL (Overclocking PLL)**:
- `OC_PLL_ENABLE`
- `OC_PLL_FREQ_SEL` - Extended frequency range for OC scenarios
- `OC_PLL_SSC_CTRL`
- `OC_PLL_LOCK_STATUS`
- `OC_PLL_VOLTAGE_CTRL` - Voltage control for overclocking

**Display PLL (DDIPLL)**:
- `DDIPLL_ENABLE`
- `DDIPLL_FREQ_SEL` - 810MHz or 1250MHz
- `DDIPLL_LOCK_STATUS`
- `DDIPLL_MODE_CTRL` - Display mode configuration

**Type-C PLL**:
- `TCPLL_ENABLE`
- `TCPLL_FREQ_SEL`
- `TCPLL_LOCK_STATUS`
- `TCPLL_PORT_SEL` - Port selection for Type-C PHY

**D2D PLL (Die-to-Die)**:
- `D2DPLL_ENABLE`
- `D2DPLL_FREQ_SEL`
- `D2DPLL_LOCK_STATUS`
- `D2DPLL_LINK_CTRL` - D2D link configuration

**FilterPLL (Crystal Filter)**:
- `FILTERPLL_ENABLE`
- `FILTERPLL_XTAL_SEL` - Crystal frequency selection (38.4MHz)
- `FILTERPLL_LOCK_STATUS`
- `FILTERPLL_FILTER_CTRL` - Filter configuration

### 2. Clock Control Registers

**Clock Divider Registers**:
- `CLK_DIV_IOSF` - IOSF clock divider (e.g., /1, /2, /4)
- `CLK_DIV_PCIe` - PCIe clock divider
- `CLK_DIV_DISPLAY` - Display clock divider
- `CLK_DIV_COMPUTE` - Compute clock divider
- `CLK_DIV_PMC` - PMC clock divider

**Clock Mux (Source Selection) Registers**:
- `CLK_MUX_IOSF` - IOSF clock source selection (Main PLL / HP PLL / OC PLL)
- `CLK_MUX_PCIe` - PCIe clock source selection
- `CLK_MUX_DISPLAY` - Display clock source selection
- `CLK_MUX_COMPUTE` - Compute clock source selection

**Clock Gating Control Registers**:
- `CLK_GATE_CTRL_IOSF` - IOSF clock gating enable/disable
- `CLK_GATE_CTRL_PCIe` - PCIe clock gating enable/disable
- `CLK_GATE_CTRL_DISPLAY` - Display clock gating enable/disable
- `CLK_GATE_CTRL_COMPUTE` - Compute clock gating enable/disable
- `CLK_GATE_POLICY` - Global gating policy (aggressive/balanced/disabled)

**Clock Enable Registers**:
- `CLK_ENABLE_MASK` - Bitmask for enabling/disabling individual clocks
- `CLK_TRUNK_ENABLE` - Trunk clock enable (high-level gating)

### 3. Error Status and Reporting Registers

**PLL Error Registers**:
- `PLL_ERROR_STATUS` - Aggregate PLL error status (read-only)
  - Bit 0: Main PLL lock failure
  - Bit 1: HP PLL lock failure
  - Bit 2: OC PLL lock failure
  - Bit 3: Display PLL lock failure
  - Bit 4: Type-C PLL lock failure
  - Bit 5: D2D PLL lock failure
  - Bit 6: FilterPLL lock failure
- `PLL_ERROR_CLEAR` - Write 1 to clear corresponding error bit
- `PLL_ERROR_MASK` - Mask PLL errors from triggering sTRC

**Clock Monitor Registers**:
- `CLK_MON_ENABLE` - Enable clock monitoring
- `CLK_MON_SELECT` - Select which clock to monitor
- `CLK_MON_REF_FREQ` - Reference frequency for comparison
- `CLK_MON_TOLERANCE` - Tolerance threshold (%)
- `CLK_MON_ERROR_STATUS` - Clock frequency out-of-range error
- `CLK_MON_ERROR_CLEAR` - Clear clock monitor error

**sTRC (System Trace Controller) Integration**:
- `STRC_CLK_ERROR_LOG` - sTRC log entry for clock errors
- `STRC_CLK_ERROR_TIMESTAMP` - Timestamp of clock error
- `STRC_CLK_ERROR_CODE` - Error code (PLL lock failure, frequency mismatch, gating stuck, etc.)
- `STRC_CLK_ERROR_CONTEXT` - Additional context (which PLL, which clock, etc.)

**General Error Registers**:
- `ISCLK_ERROR_STATUS` - Top-level ISClk error status
- `ISCLK_ERROR_LOG` - Error log buffer (FIFO)
- `ISCLK_ERROR_INT_ENABLE` - Enable interrupts on errors
- `ISCLK_ERROR_INT_STATUS` - Interrupt status

### 4. Power Management Registers

**S0ix Clock Retention Registers**:
- `S0IX_CLK_RETENTION_CTRL` - Control which clocks remain active in S0ix
- `S0IX_CLK_RETENTION_STATUS` - Status of retention clocks
- `S0IX_CLK_RESTORE_CTRL` - Control clock restoration on S0ix exit

**PLL Shutdown Registers**:
- `PLL_SHUTDOWN_SEQ_CTRL` - Control PLL shutdown sequence for Sx states
- `PLL_SHUTDOWN_STATUS` - Status of PLL shutdown

**PMC Coordination Registers**:
- `PMC_CLK_REQ` - PMC clock request (read-only, from PMC)
- `PMC_CLK_ACK` - ISClk acknowledgment to PMC

---

## PythonSV Register Access Patterns

### Accessing ISClk Registers via Namednodes

PythonSV provides `namednodes` for structured register access. ISClk registers are typically accessed via MMIO (Memory-Mapped I/O) or sideband (IOSFSB).

**Example: Read Main PLL Lock Status**
```python
from namednodes import *

# Access Main PLL lock status register
main_pll_lock_status = pch.isclk.main_pll.lock_status.read()

# Check lock bit (assume bit 0 is lock status)
is_locked = (main_pll_lock_status & 0x1) == 0x1

if is_locked:
    print("Main PLL is locked")
else:
    print("Main PLL lock FAILED")
```

**Example: Configure Main PLL Frequency**
```python
from namednodes import *

# Set Main PLL frequency to 1000MHz
pch.isclk.main_pll.freq_sel.write(0x0)  # 0x0 = 1000MHz (consult HAS for encoding)

# Enable Main PLL
pch.isclk.main_pll.enable.write(0x1)

# Wait for PLL to lock (poll lock status)
import time
timeout = 1.0  # 1 second timeout
start = time.time()
while time.time() - start < timeout:
    lock_status = pch.isclk.main_pll.lock_status.read()
    if (lock_status & 0x1) == 0x1:
        print("Main PLL locked successfully")
        break
    time.sleep(0.01)  # 10ms poll interval
else:
    print("ERROR: Main PLL failed to lock within timeout")
```

**Example: Enable Clock Gating for IOSF**
```python
from namednodes import *

# Read current gating control
current_ctrl = pch.isclk.clk_gate_ctrl.iosf.read()

# Set gating enable bit (assume bit 0)
new_ctrl = current_ctrl | 0x1

# Write back
pch.isclk.clk_gate_ctrl.iosf.write(new_ctrl)

print(f"IOSF clock gating enabled: 0x{new_ctrl:08x}")
```

**Example: Read PLL Error Status**
```python
from namednodes import *

# Read PLL error status register
pll_error_status = pch.isclk.pll_error_status.read()

# Decode error bits
errors = []
if pll_error_status & (1 << 0):
    errors.append("Main PLL lock failure")
if pll_error_status & (1 << 1):
    errors.append("HP PLL lock failure")
if pll_error_status & (1 << 2):
    errors.append("OC PLL lock failure")
if pll_error_status & (1 << 3):
    errors.append("Display PLL lock failure")
if pll_error_status & (1 << 4):
    errors.append("Type-C PLL lock failure")
if pll_error_status & (1 << 5):
    errors.append("D2D PLL lock failure")
if pll_error_status & (1 << 6):
    errors.append("FilterPLL lock failure")

if errors:
    print("PLL Errors detected:")
    for error in errors:
        print(f"  - {error}")
else:
    print("No PLL errors")
```

**Example: Clear PLL Errors**
```python
from namednodes import *

# Read current error status
pll_error_status = pch.isclk.pll_error_status.read()

# Write to error clear register (write-1-to-clear)
pch.isclk.pll_error_clear.write(pll_error_status)

print(f"Cleared PLL errors: 0x{pll_error_status:08x}")
```

### Register Access Side Effects

**IMPORTANT**: Some ISClk registers have side effects when read or written:

1. **Write-1-to-Clear Registers**: Error status registers often require writing `1` to clear the error bit
   - Example: `PLL_ERROR_CLEAR`, `CLK_MON_ERROR_CLEAR`
   - **Pattern**: Read error status, then write same value to clear register

2. **Read-to-Clear Registers**: Some error logs are cleared upon read
   - Example: `STRC_CLK_ERROR_LOG` (reading consumes FIFO entry)
   - **Pattern**: Read once and cache value, do not re-read

3. **Shadow Registers**: Some control registers are double-buffered and require a "commit" write
   - Example: PLL frequency selection may require writing to a `COMMIT` register
   - **Pattern**: Write configuration, then write to commit register

4. **PMC Handshake Registers**: Writing to PMC coordination registers may trigger PMC firmware actions
   - Example: `PMC_CLK_ACK` triggers PMC to proceed with power state transition
   - **Pattern**: Only write after confirming ISClk is ready

5. **Lock Status Polling**: Reading lock status does NOT cause side effects, but register may be updated asynchronously by hardware
   - **Pattern**: Poll with timeout, do not assume instant lock

---

## Validation Workflows

### Workflow 1: Validate PLL Configuration Registers

**Objective**: Verify PLL configuration registers are correctly programmed and accessible.

**Steps**:
1. Query HAS for PLL register specifications (Co-Design)
2. Enumerate all PLL configuration registers via PythonSV
3. Read default values and verify against HAS
4. Write test values (if safe) and read back to verify RW access
5. Verify read-only registers (e.g., lock status) cannot be written
6. Document any discrepancies

**Example Code**:
```python
from namednodes import *

# Step 2: Enumerate PLL registers
pll_registers = [
    ("Main PLL Enable", pch.isclk.main_pll.enable),
    ("Main PLL Freq Sel", pch.isclk.main_pll.freq_sel),
    ("Main PLL SSC Ctrl", pch.isclk.main_pll.ssc_ctrl),
    ("Main PLL Lock Status", pch.isclk.main_pll.lock_status),
    ("HP PLL Enable", pch.isclk.hp_pll.enable),
    ("HP PLL Freq Sel", pch.isclk.hp_pll.freq_sel),
    # ... (add all PLLs)
]

# Step 3: Read default values
print("PLL Register Default Values:")
for name, reg in pll_registers:
    value = reg.read()
    print(f"  {name}: 0x{value:08x}")

# Step 4: Test RW access (CAUTION: only if safe)
# Example: Write to SSC control (if disabled by default)
original_ssc = pch.isclk.main_pll.ssc_ctrl.read()
test_value = 0xDEADBEEF
pch.isclk.main_pll.ssc_ctrl.write(test_value)
readback = pch.isclk.main_pll.ssc_ctrl.read()
if readback == test_value:
    print("SSC Ctrl RW access: PASS")
else:
    print(f"SSC Ctrl RW access: FAIL (wrote 0x{test_value:08x}, read 0x{readback:08x})")
# Restore original value
pch.isclk.main_pll.ssc_ctrl.write(original_ssc)

# Step 5: Verify read-only registers
original_lock = pch.isclk.main_pll.lock_status.read()
pch.isclk.main_pll.lock_status.write(0xFFFFFFFF)  # Attempt write
new_lock = pch.isclk.main_pll.lock_status.read()
if new_lock == original_lock:
    print("Lock Status is read-only: PASS")
else:
    print("Lock Status is writable (unexpected): FAIL")
```

### Workflow 2: Validate Clock Control Registers

**Objective**: Verify clock divider, mux, and gating control registers function correctly.

**Steps**:
1. Query HAS for clock control register specifications
2. Read current clock divider settings
3. Modify divider and verify clock frequency change (requires clock measurement or functional test)
4. Read current mux settings
5. Change mux source and verify clock source change
6. Test clock gating enable/disable
7. Restore original settings

**Example Code**:
```python
from namednodes import *

# Step 2: Read current IOSF divider
current_div = pch.isclk.clk_div.iosf.read()
print(f"Current IOSF divider: 0x{current_div:08x}")

# Step 3: Modify divider (e.g., from /1 to /2)
# CAUTION: This will affect system operation, only do in controlled environment
pch.isclk.clk_div.iosf.write(0x1)  # 0x1 = divide by 2 (consult HAS)
new_div = pch.isclk.clk_div.iosf.read()
print(f"New IOSF divider: 0x{new_div:08x}")
# TODO: Measure clock frequency to verify change

# Restore original divider
pch.isclk.clk_div.iosf.write(current_div)

# Step 4: Read current IOSF mux
current_mux = pch.isclk.clk_mux.iosf.read()
print(f"Current IOSF mux: 0x{current_mux:08x}")

# Step 5: Change mux source (e.g., from Main PLL to HP PLL)
# CAUTION: Only if HP PLL is locked
hp_pll_lock = pch.isclk.hp_pll.lock_status.read()
if (hp_pll_lock & 0x1) == 0x1:
    pch.isclk.clk_mux.iosf.write(0x1)  # 0x1 = HP PLL (consult HAS)
    new_mux = pch.isclk.clk_mux.iosf.read()
    print(f"New IOSF mux: 0x{new_mux:08x}")
    # Restore original mux
    pch.isclk.clk_mux.iosf.write(current_mux)
else:
    print("HP PLL not locked, skipping mux test")

# Step 6: Test clock gating
current_gate = pch.isclk.clk_gate_ctrl.iosf.read()
print(f"Current IOSF gating: 0x{current_gate:08x}")

# Enable gating
pch.isclk.clk_gate_ctrl.iosf.write(current_gate | 0x1)
print("IOSF gating enabled")

# Disable gating
pch.isclk.clk_gate_ctrl.iosf.write(current_gate & ~0x1)
print("IOSF gating disabled")

# Restore original gating
pch.isclk.clk_gate_ctrl.iosf.write(current_gate)
```

### Workflow 3: Validate Error Status Registers

**Objective**: Verify error status registers correctly report and clear errors.

**Steps**:
1. Query HAS for error register specifications
2. Read baseline error status (should be clear)
3. Inject error (if possible in test environment)
4. Read error status and verify error is logged
5. Read sTRC error log and verify error context
6. Clear error status
7. Verify error status is cleared

**Example Code**:
```python
from namednodes import *

# Step 2: Read baseline error status
baseline_pll_error = pch.isclk.pll_error_status.read()
baseline_clk_mon_error = pch.isclk.clk_mon_error_status.read()
print(f"Baseline PLL error status: 0x{baseline_pll_error:08x}")
print(f"Baseline Clock Monitor error status: 0x{baseline_clk_mon_error:08x}")

# Step 3: Inject error (example: force Main PLL to unlock by disabling it)
# CAUTION: This will cause system instability, only in test environment
print("Injecting PLL lock failure by disabling Main PLL...")
pch.isclk.main_pll.enable.write(0x0)
import time
time.sleep(0.1)  # Wait for error to propagate

# Step 4: Read error status
pll_error = pch.isclk.pll_error_status.read()
print(f"PLL error status after injection: 0x{pll_error:08x}")
if (pll_error & (1 << 0)) != 0:
    print("Main PLL lock failure detected: PASS")
else:
    print("Main PLL lock failure NOT detected: FAIL")

# Step 5: Read sTRC error log
strc_log = pch.isclk.strc_clk_error_log.read()
strc_code = pch.isclk.strc_clk_error_code.read()
strc_context = pch.isclk.strc_clk_error_context.read()
print(f"sTRC error log: 0x{strc_log:08x}")
print(f"sTRC error code: 0x{strc_code:08x}")
print(f"sTRC error context: 0x{strc_context:08x}")

# Step 6: Clear error status
pch.isclk.pll_error_clear.write(pll_error)
print("PLL error cleared")

# Step 7: Verify cleared
pll_error_after = pch.isclk.pll_error_status.read()
print(f"PLL error status after clear: 0x{pll_error_after:08x}")
if pll_error_after == 0:
    print("PLL error successfully cleared: PASS")
else:
    print("PLL error NOT cleared: FAIL")

# Re-enable Main PLL to restore system
pch.isclk.main_pll.enable.write(0x1)
time.sleep(0.1)  # Wait for PLL to lock
```

### Workflow 4: Validate Clock Monitor Registers

**Objective**: Configure and validate Clock Monitor error detection.

**Steps**:
1. Query HAS for Clock Monitor register specifications
2. Select target clock to monitor (e.g., o_ck_1ghz_iosf)
3. Configure reference frequency and tolerance
4. Enable Clock Monitor
5. Verify Clock Monitor detects in-range frequency (no error)
6. Inject frequency error (if possible, e.g., by changing divider)
7. Verify Clock Monitor detects out-of-range frequency (error)
8. Clear error and restore configuration

**Example Code**:
```python
from namednodes import *

# Step 2: Select IOSF clock to monitor
pch.isclk.clk_mon_select.write(0x0)  # 0x0 = o_ck_1ghz_iosf (consult HAS)

# Step 3: Configure reference frequency (1000 MHz) and tolerance (5%)
pch.isclk.clk_mon_ref_freq.write(1000)  # 1000 MHz
pch.isclk.clk_mon_tolerance.write(5)    # 5% tolerance

# Step 4: Enable Clock Monitor
pch.isclk.clk_mon_enable.write(0x1)
print("Clock Monitor enabled for o_ck_1ghz_iosf")

# Step 5: Verify no error (frequency in range)
import time
time.sleep(0.1)  # Allow time for monitoring
clk_mon_error = pch.isclk.clk_mon_error_status.read()
if clk_mon_error == 0:
    print("Clock Monitor: No error (frequency in range): PASS")
else:
    print(f"Clock Monitor: Unexpected error: 0x{clk_mon_error:08x}")

# Step 6: Inject frequency error by changing divider
print("Injecting frequency error by changing IOSF divider to /4...")
original_div = pch.isclk.clk_div.iosf.read()
pch.isclk.clk_div.iosf.write(0x3)  # 0x3 = divide by 4 (consult HAS)
time.sleep(0.1)  # Allow time for error detection

# Step 7: Verify Clock Monitor detects error
clk_mon_error = pch.isclk.clk_mon_error_status.read()
if clk_mon_error != 0:
    print(f"Clock Monitor detected frequency error: PASS (0x{clk_mon_error:08x})")
else:
    print("Clock Monitor did NOT detect frequency error: FAIL")

# Step 8: Clear error and restore
pch.isclk.clk_mon_error_clear.write(clk_mon_error)
pch.isclk.clk_div.iosf.write(original_div)
pch.isclk.clk_mon_enable.write(0x0)  # Disable monitor
print("Clock Monitor error cleared and configuration restored")
```

### Workflow 5: Validate S0ix Clock Retention Registers

**Objective**: Verify S0ix clock retention control registers function correctly during S0ix entry/exit.

**Steps**:
1. Query HAS for S0ix clock retention register specifications
2. Configure retention control (which clocks to keep active in S0ix)
3. Coordinate with **fv-isclk/power** skill to enter S0ix
4. Read retention status in S0ix
5. Verify retention clocks are active (e.g., PMC ART at 38.4 MHz)
6. Exit S0ix
7. Read clock restore status
8. Verify all clocks restored

**Example Code**:
```python
from namednodes import *

# Step 2: Configure retention control
# Keep PMC ART and RTC clocks active in S0ix
retention_mask = (1 << 0) | (1 << 1)  # Bit 0=PMC ART, Bit 1=RTC (consult HAS)
pch.isclk.s0ix_clk_retention_ctrl.write(retention_mask)
print(f"S0ix retention configured: 0x{retention_mask:08x}")

# Step 3: Enter S0ix (coordinate with fv-isclk/power)
# This requires PMC firmware coordination and platform-specific steps
# See fv-isclk/power skill for full S0ix entry workflow
print("Entering S0ix (see fv-isclk/power for full workflow)...")
# <S0ix entry code here>

# Step 4: Read retention status in S0ix
retention_status = pch.isclk.s0ix_clk_retention_status.read()
print(f"S0ix retention status: 0x{retention_status:08x}")
if (retention_status & retention_mask) == retention_mask:
    print("Retention clocks active in S0ix: PASS")
else:
    print("Retention clocks NOT active in S0ix: FAIL")

# Step 5: Verify retention clock frequency (requires measurement)
# Example: Measure PMC ART frequency should be 38.4 MHz
# <Frequency measurement code here>

# Step 6: Exit S0ix
print("Exiting S0ix...")
# <S0ix exit code here>

# Step 7: Read clock restore status
restore_status = pch.isclk.s0ix_clk_restore_ctrl.read()
print(f"S0ix restore status: 0x{restore_status:08x}")

# Step 8: Verify all clocks restored
# Enumerate all clocks and verify frequencies match pre-S0ix values
# <Clock enumeration and verification code here>
```

---

## Integration with Other Skills

### With `fv-isclk/pll`
- **pll** skill configures PLL parameters via registers
- **registers** skill provides low-level register access patterns
- **Workflow**: pll skill uses register access patterns from this skill

### With `fv-isclk/clock-tree`
- **clock-tree** skill reads clock divider and mux registers to enumerate tree
- **registers** skill provides register map for clock tree components
- **Workflow**: clock-tree skill uses register access to read divider ratios and mux selections

### With `fv-isclk/frequency-gating`
- **frequency-gating** skill uses clock gating control registers
- **registers** skill provides register access patterns for gating
- **Workflow**: frequency-gating skill uses register access for DFS and gating workflows

### With `fv-isclk/power`
- **power** skill uses S0ix retention registers and PLL shutdown registers
- **registers** skill provides low-level access patterns
- **Workflow**: power skill coordinates S0ix transitions using retention control registers

### With `fv-isclk/debug`
- **debug** skill reads error status registers and sTRC logs for failure analysis
- **registers** skill provides error register map and access patterns
- **Workflow**: debug skill uses error status and sTRC registers to diagnose failures

---

## Common Register Access Issues

### Issue 1: Register Read Returns All 0xFF or 0x00
**Symptom**: Reading ISClk register returns `0xFFFFFFFF` or `0x00000000`

**Possible Causes**:
- ISClk IP is in reset
- ISClk clock is gated
- IOSFSB sideband access is not enabled
- Register address is incorrect
- Platform is in low-power state (S0ix, S3)

**Debug Steps**:
1. Verify ISClk IP is out of reset (check PMC or fabric reset status)
2. Verify ISClk trunk clock is enabled
3. Verify IOSFSB sideband is enabled and functional
4. Verify register address matches HAS specification
5. Verify platform is in S0 (fully active) state

### Issue 2: Register Write Has No Effect
**Symptom**: Writing to ISClk register does not change value (readback shows old value)

**Possible Causes**:
- Register is read-only
- Register requires "commit" write to shadow register
- Register is locked by PMC firmware or fuse
- Write was masked by a separate mask register
- Register is conditionally writable (e.g., only when PLL is disabled)

**Debug Steps**:
1. Verify register is read-write (RW) in HAS specification
2. Check if register requires commit write (consult HAS)
3. Check PMC firmware locks or fuse configuration
4. Check for associated mask register
5. Check register access conditions (e.g., PLL must be disabled before changing frequency)

### Issue 3: PLL Lock Status Does Not Update
**Symptom**: PLL lock status register remains 0 (unlocked) after enabling PLL

**Possible Causes**:
- PLL configuration is invalid (frequency out of range, SSC misconfigured)
- PLL input clock (crystal) is not stable
- PLL requires additional time to lock (timeout too short)
- PLL is in reset
- Hardware PLL failure

**Debug Steps**:
1. Verify PLL configuration matches HAS requirements
2. Verify crystal oscillator is stable (measure with oscilloscope)
3. Increase polling timeout (some PLLs take up to 1 second to lock)
4. Verify PLL is out of reset
5. Read PLL error status register for failure indication
6. Consult HAS for PLL lock time specification

### Issue 4: Clock Monitor False Positives
**Symptom**: Clock Monitor reports frequency error when clock is in range

**Possible Causes**:
- Reference frequency is incorrect
- Tolerance is too tight
- Clock frequency is unstable (jitter, transient)
- Clock Monitor sampling too early (clock not settled)
- Clock Monitor misconfigured (wrong clock selected)

**Debug Steps**:
1. Verify reference frequency matches HAS specification
2. Increase tolerance to account for jitter and SSC
3. Add delay after clock configuration before enabling Clock Monitor
4. Verify Clock Monitor select register points to correct clock
5. Measure clock frequency with oscilloscope to verify actual frequency

### Issue 5: sTRC Error Log is Empty
**Symptom**: sTRC error log register returns 0 despite known clock errors

**Possible Causes**:
- sTRC is not enabled
- Error mask register is blocking error logging
- sTRC FIFO is full (old errors not consumed)
- sTRC clock is gated
- sTRC log was already read (read-to-clear)

**Debug Steps**:
1. Verify sTRC is enabled globally (check PMC or sTRC control register)
2. Check error mask register and ensure errors are not masked
3. Read sTRC FIFO depth register and clear old entries if full
4. Verify sTRC clock is active
5. Avoid re-reading sTRC log (cache result after first read)

---

## Common Register Access Patterns

### Pattern 1: Read-Modify-Write (RMW)
**Use Case**: Change specific bits without affecting other bits

**Example**:
```python
# Enable clock gating (bit 0) without changing other bits
current = pch.isclk.clk_gate_ctrl.iosf.read()
new = current | 0x1  # Set bit 0
pch.isclk.clk_gate_ctrl.iosf.write(new)
```

### Pattern 2: Write-1-to-Clear
**Use Case**: Clear error status bits

**Example**:
```python
# Clear all PLL errors
pll_errors = pch.isclk.pll_error_status.read()
pch.isclk.pll_error_clear.write(pll_errors)  # Write 1 to clear each error bit
```

### Pattern 3: Polling with Timeout
**Use Case**: Wait for hardware status to change (e.g., PLL lock)

**Example**:
```python
import time

def poll_register(reg, mask, expected, timeout=1.0):
    start = time.time()
    while time.time() - start < timeout:
        value = reg.read()
        if (value & mask) == expected:
            return True
        time.sleep(0.01)  # 10ms poll interval
    return False

# Wait for Main PLL to lock
if poll_register(pch.isclk.main_pll.lock_status, 0x1, 0x1, timeout=1.0):
    print("PLL locked")
else:
    print("PLL lock timeout")
```

### Pattern 4: Shadow Register Commit
**Use Case**: Configure register with double-buffering

**Example**:
```python
# Configure PLL frequency (shadow register)
pch.isclk.main_pll.freq_sel.write(0x2)  # Write to shadow register

# Commit configuration
pch.isclk.main_pll.commit.write(0x1)  # Trigger hardware to load shadow register

# Wait for commit to complete
poll_register(pch.isclk.main_pll.commit, 0x1, 0x0, timeout=0.1)
```

### Pattern 5: Bitmask Enumeration
**Use Case**: Decode multi-bit fields or error bitmasks

**Example**:
```python
# Decode PLL error status bitmask
pll_errors = pch.isclk.pll_error_status.read()
error_names = [
    "Main PLL", "HP PLL", "OC PLL", "Display PLL",
    "Type-C PLL", "D2D PLL", "FilterPLL"
]

print("PLL Errors:")
for i, name in enumerate(error_names):
    if pll_errors & (1 << i):
        print(f"  - {name} lock failure")
```

---

## HAS References

**Primary Reference**:
- `Chap44_0_NVL_PCH_Internal_Clocks.html` - ISClk register map and specifications

**Query Co-Design** for:
- Register addresses and offsets
- Register bit field definitions
- Register access permissions (RW, RO, WO, W1C)
- Register reset values
- Register access side effects
- sTRC integration details
- Clock Monitor specifications

---

## Summary Checklist

When validating ISClk registers, ensure:
- [ ] Query HAS via Co-Design for register specifications
- [ ] Enumerate all register categories (PLL, clock control, error, power)
- [ ] Validate register access (RW, RO) matches HAS
- [ ] Test register side effects (write-1-to-clear, shadow commit)
- [ ] Validate error status and sTRC integration
- [ ] Validate Clock Monitor configuration and error detection
- [ ] Validate S0ix retention and restore registers
- [ ] Use PythonSV namednodes for structured access
- [ ] Use common access patterns (RMW, polling, commit)
- [ ] Document register access issues and resolutions
- [ ] Integrate with other sub-skills (pll, clock-tree, frequency-gating, power, debug)

---

**End of fv-isclk/registers sub-skill**
