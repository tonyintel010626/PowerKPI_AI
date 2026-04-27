# FV-ISClk Debug Sub-Skill

**Owner**: Ooi, Ling Wei (lingweio)  
**Parent Skill**: `fv-isclk`  
**Agent**: `FV-ISClk`

---

## Overview

This sub-skill provides comprehensive ISClk debug and failure analysis knowledge for NVL platforms. It covers common failure signatures, debug workflows, triage procedures, HSDES sighting search and correlation, known errata and workarounds, integration with FV_Debugger_V1 for automated NGA triage, boot-time clock debugging using TTK3 hardware, error log parsing, root cause analysis decision trees, and remediation strategies.

**Key Focus Areas**:
- Common ISClk failure signatures
- Debug workflows and triage procedures
- HSDES sighting search and correlation
- Known errata and workarounds
- NGA test failure analysis (integration with FV_Debugger_V1)
- Boot-time clock debugging (UART logs via TTK3-UART, POST codes via TTK3-POSTCODE)
- Error log parsing (sTRC logs, Clock Monitor errors)
- Root cause analysis decision trees
- Remediation strategies and fixes

---

## HAS-First Policy

**ALWAYS query Co-Design** before making debug assumptions or applying workarounds.

**Primary HAS Documents**:
- `Chap44_0_NVL_PCH_Internal_Clocks.html` - ISClk specifications and expected behavior
- `NVL-PCD-S Feature Guide - sTRC_CM.html` - Error handling and logging mechanisms

**Co-Design Query Examples**:
```
"What are the expected PLL lock times from Chap44_0_NVL_PCH_Internal_Clocks.html?"
"Show me the ISClk error codes and sTRC integration from NVL-PCD-S Feature Guide"
"What are the ISClk-related boot dependencies from Chap44_0?"
"Show me ISClk S0ix entry/exit sequence from Chap44_0"
```

---

## Common ISClk Failure Signatures

### Signature 1: PLL Lock Failure

**Symptoms**:
- PLL lock status register remains 0 (unlocked)
- System hangs during boot (waiting for PLL lock)
- sTRC error log shows "PLL_LOCK_TIMEOUT" error code
- No clocks downstream of failed PLL

**Possible Root Causes**:
1. **Invalid PLL configuration** - Frequency selection out of range
2. **Crystal oscillator failure** - Crystal not oscillating or unstable
3. **Voltage rail issue** - VccPLL too low or noisy
4. **Temperature extreme** - PLL outside calibration range
5. **Hardware defect** - Damaged PLL circuitry
6. **Fuse setting** - PLL disabled by fuse or PMC lock

**Debug Workflow**: See [Workflow 1: Debug PLL Lock Failure](#workflow-1-debug-pll-lock-failure)

### Signature 2: Clock Frequency Mismatch

**Symptoms**:
- Clock Monitor reports frequency out-of-range error
- Functional failures in downstream logic (timing violations)
- Measured frequency does not match expected frequency
- System instability or crashes

**Possible Root Causes**:
1. **Incorrect divider configuration** - Divider register misconfigured
2. **Wrong PLL source selected** - Clock mux pointing to wrong PLL
3. **PLL frequency misconfigured** - PLL not running at expected frequency
4. **SSC interference** - Spread spectrum causing frequency deviation
5. **Dynamic frequency scaling bug** - DFS transition incomplete
6. **Register access failure** - Clock control register not written correctly

**Debug Workflow**: See [Workflow 2: Debug Clock Frequency Mismatch](#workflow-2-debug-clock-frequency-mismatch)

### Signature 3: Clock Gating Stuck

**Symptoms**:
- Clock gating control register shows gating enabled, but clock still active
- Clock gating control register shows gating disabled, but clock is gated
- Power consumption does not match expected gating state
- Functional failures due to unexpected clock gating

**Possible Root Causes**:
1. **PMC firmware override** - PMC forcing clock on/off regardless of SW control
2. **Hardware gating logic failure** - Clock gate circuitry stuck
3. **Gating dependency not met** - Upstream condition not satisfied
4. **Register shadow/commit issue** - Gating control not committed to hardware
5. **Race condition** - Gating control changing during access

**Debug Workflow**: See [Workflow 3: Debug Clock Gating Issues](#workflow-3-debug-clock-gating-issues)

### Signature 4: Boot Hang (Clock-Related)

**Symptoms**:
- System hangs during early boot (BIOS/IFWI)
- POST code stuck at clock initialization phase
- UART log shows "Waiting for PLL lock..." message and stops
- No display output

**Possible Root Causes**:
1. **PLL lock failure** - See Signature 1
2. **Clock sequencing error** - Clocks enabled in wrong order
3. **Crystal oscillator failure** - See Signature 1
4. **BIOS bug** - BIOS clock initialization code has defect
5. **Hardware defect** - ISClk IP completely non-functional

**Debug Workflow**: See [Workflow 4: Debug Boot Hang (Clock-Related)](#workflow-4-debug-boot-hang-clock-related)

### Signature 5: S0ix Entry/Exit Failure (Clock-Related)

**Symptoms**:
- System fails to enter S0ix (PC10 not reached)
- System enters S0ix but does not exit (resume hang)
- S0ix exit is slow (> 5 seconds)
- Display does not restore after S0ix exit
- sTRC log shows clock retention or restoration errors

**Possible Root Causes**:
1. **Clock not gated during S0ix entry** - Preventing deep sleep
2. **Retention clock configuration error** - PMC ART or RTC not retained
3. **Clock restoration failure on exit** - PLL fails to re-lock on resume
4. **PMC coordination failure** - ISClk and PMC out of sync
5. **Display PLL delay** - DDIPLL slow to lock on resume

**Debug Workflow**: See [Workflow 5: Debug S0ix Clock Issues](#workflow-5-debug-s0ix-clock-issues)

### Signature 6: Display Artifacts (Clock-Related)

**Symptoms**:
- Screen flicker or tearing
- Incorrect refresh rate
- Display not syncing properly
- Thunderbolt display issues

**Possible Root Causes**:
1. **DDIPLL frequency incorrect** - Not at 810 MHz or 1250 MHz
2. **SSC interference** - Main PLL SSC causing DDIPLL instability
3. **Display clock divider misconfigured** - Display aux clock wrong
4. **DDIPLL lock unstable** - PLL hunting or jitter
5. **Voltage rail noise** - VccPLL or VccDisplay too noisy

**Debug Workflow**: See [Workflow 6: Debug Display Clock Issues](#workflow-6-debug-display-clock-issues)

---

## Debug Workflows

### Workflow 1: Debug PLL Lock Failure

**Objective**: Identify why a PLL is failing to lock and remediate.

**Steps**:
1. Query HAS for PLL specifications (lock time, voltage, frequency range)
2. Read PLL configuration registers and verify against HAS
3. Read PLL error status and sTRC logs
4. Measure crystal oscillator with oscilloscope (if FilterPLL failure)
5. Check VccPLL voltage rail
6. Check temperature (for calibration range)
7. Try alternative PLL configuration (different frequency)
8. Apply known workarounds from HSDES
9. If hardware defect suspected, escalate to Silicon Debug

**Example Code**:
```python
from namednodes import *
import time

# Step 1: Query HAS (use Co-Design)
print("Query Co-Design: 'Show me Main PLL specifications from Chap44_0'")

# Step 2: Read PLL configuration
print("=== Main PLL Configuration ===")
pll_enable = pch.isclk.main_pll.enable.read()
pll_freq_sel = pch.isclk.main_pll.freq_sel.read()
pll_ssc_ctrl = pch.isclk.main_pll.ssc_ctrl.read()
pll_lock_status = pch.isclk.main_pll.lock_status.read()

print(f"Enable: 0x{pll_enable:08x}")
print(f"Freq Sel: 0x{pll_freq_sel:08x}")
print(f"SSC Ctrl: 0x{pll_ssc_ctrl:08x}")
print(f"Lock Status: 0x{pll_lock_status:08x}")

if (pll_lock_status & 0x1) == 0x1:
    print("Main PLL is LOCKED (unexpected, recheck symptoms)")
    exit()
else:
    print("Main PLL is UNLOCKED (confirming failure)")

# Step 3: Read error status
pll_error_status = pch.isclk.pll_error_status.read()
print(f"PLL Error Status: 0x{pll_error_status:08x}")
if (pll_error_status & (1 << 0)) != 0:
    print("  - Main PLL lock failure error flagged")

# Read sTRC log
strc_error_code = pch.isclk.strc_clk_error_code.read()
strc_error_context = pch.isclk.strc_clk_error_context.read()
print(f"sTRC Error Code: 0x{strc_error_code:08x}")
print(f"sTRC Error Context: 0x{strc_error_context:08x}")

# Step 4: Check crystal oscillator (if FilterPLL)
print("\n=== Crystal Oscillator Check ===")
filterpll_lock = pch.isclk.filterpll.lock_status.read()
if (filterpll_lock & 0x1) == 0x1:
    print("FilterPLL is locked (crystal OK)")
else:
    print("FilterPLL is UNLOCKED (crystal failure suspected)")
    print("ACTION: Measure crystal oscillator with oscilloscope")
    print("  - Check 38.4 MHz output")
    print("  - Check amplitude (should be > 0.5V pk-pk)")
    print("  - Check for noise or instability")

# Step 5: Check VccPLL voltage (requires TTK3 or voltmeter)
print("\n=== VccPLL Voltage Check ===")
print("ACTION: Measure VccPLL voltage rail")
print("  - Expected: 1.05V ±50mV (consult HAS)")
print("  - Check for droop or noise")

# Step 6: Check temperature
print("\n=== Temperature Check ===")
print("ACTION: Check platform temperature")
print("  - PLL calibration range: -40°C to +105°C (consult HAS)")
print("  - If outside range, PLL may fail to lock")

# Step 7: Try alternative configuration
print("\n=== Alternative Configuration Test ===")
print("Trying Main PLL at 1000 MHz (safe frequency)...")
pch.isclk.main_pll.freq_sel.write(0x0)  # 0x0 = 1000 MHz (consult HAS)
pch.isclk.main_pll.ssc_ctrl.write(0x0)  # Disable SSC
pch.isclk.main_pll.enable.write(0x0)    # Reset PLL
time.sleep(0.01)
pch.isclk.main_pll.enable.write(0x1)    # Re-enable

# Wait for lock
start = time.time()
while time.time() - start < 1.0:
    lock_status = pch.isclk.main_pll.lock_status.read()
    if (lock_status & 0x1) == 0x1:
        print("Main PLL locked with safe configuration")
        print("CONCLUSION: Original configuration was invalid")
        break
    time.sleep(0.01)
else:
    print("Main PLL still fails to lock with safe configuration")
    print("CONCLUSION: Hardware issue suspected (crystal, voltage, or PLL defect)")

# Step 8: Search HSDES for known issues
print("\n=== HSDES Search ===")
print("Search HSDES for: 'ISClk Main PLL lock failure NVL'")
print("Check for known errata and workarounds")

# Step 9: Escalation
print("\n=== Next Steps ===")
print("If all debug steps fail:")
print("  1. Collect full register dump (all ISClk registers)")
print("  2. Collect sTRC logs")
print("  3. Collect oscilloscope measurements (crystal, VccPLL)")
print("  4. File HSDES sighting with debug data")
print("  5. Escalate to Silicon Debug team")
```

### Workflow 2: Debug Clock Frequency Mismatch

**Objective**: Identify why a clock frequency does not match expected value.

**Steps**:
1. Query HAS for expected clock frequency and source
2. Read clock divider and mux registers
3. Trace clock path from PLL to output
4. Measure actual clock frequency with oscilloscope
5. Check for SSC (spread spectrum) modulation
6. Check for dynamic frequency scaling (DFS) in progress
7. Verify register writes were successful (readback)
8. Apply corrections and re-test

**Example Code**:
```python
from namednodes import *

# Step 1: Query HAS
print("Query Co-Design: 'Show me o_ck_1ghz_iosf clock path from Chap44_0'")
print("Expected: Main PLL (1600 MHz) → /1 divider → 1000 MHz")

# Step 2: Read clock divider and mux
print("\n=== IOSF Clock Configuration ===")
iosf_div = pch.isclk.clk_div.iosf.read()
iosf_mux = pch.isclk.clk_mux.iosf.read()
print(f"IOSF Divider: 0x{iosf_div:08x}")
print(f"IOSF Mux: 0x{iosf_mux:08x}")

# Decode mux (example decoding, consult HAS)
mux_sources = ["Main PLL", "HP PLL", "OC PLL", "Reserved"]
if iosf_mux < len(mux_sources):
    print(f"IOSF Clock Source: {mux_sources[iosf_mux]}")
else:
    print(f"IOSF Clock Source: Unknown (0x{iosf_mux:08x})")

# Step 3: Trace clock path
print("\n=== Clock Path Trace ===")
if iosf_mux == 0:  # Main PLL
    main_pll_freq_sel = pch.isclk.main_pll.freq_sel.read()
    main_pll_lock = pch.isclk.main_pll.lock_status.read()
    print(f"Main PLL Freq Sel: 0x{main_pll_freq_sel:08x}")
    print(f"Main PLL Lock: {'LOCKED' if (main_pll_lock & 0x1) else 'UNLOCKED'}")
    
    # Decode frequency (example, consult HAS)
    pll_freqs = {0x0: 1000, 0x1: 1200, 0x2: 1600}
    pll_freq = pll_freqs.get(main_pll_freq_sel, "Unknown")
    print(f"Main PLL Frequency: {pll_freq} MHz")
    
    # Calculate output frequency
    div_ratios = {0x0: 1, 0x1: 2, 0x2: 4, 0x3: 8}
    div_ratio = div_ratios.get(iosf_div, "Unknown")
    if isinstance(pll_freq, int) and isinstance(div_ratio, int):
        expected_freq = pll_freq / div_ratio
        print(f"Expected IOSF Frequency: {expected_freq} MHz")
    else:
        print("Cannot calculate expected frequency (unknown PLL freq or divider)")

# Step 4: Measure actual frequency
print("\n=== Frequency Measurement ===")
print("ACTION: Measure o_ck_1ghz_iosf with oscilloscope or frequency counter")
print("  - Connect probe to IOSF clock test point")
print("  - Measure frequency")
measured_freq = float(input("Enter measured frequency (MHz): "))

if isinstance(pll_freq, int) and isinstance(div_ratio, int):
    expected_freq = pll_freq / div_ratio
    freq_error = abs(measured_freq - expected_freq) / expected_freq * 100
    print(f"Frequency Error: {freq_error:.2f}%")
    
    if freq_error < 1:
        print("Frequency is within tolerance (< 1%)")
    else:
        print("Frequency mismatch detected")

# Step 5: Check SSC
print("\n=== SSC Check ===")
main_pll_ssc = pch.isclk.main_pll.ssc_ctrl.read()
print(f"Main PLL SSC Control: 0x{main_pll_ssc:08x}")
if (main_pll_ssc & 0x1) != 0:
    print("SSC is ENABLED (frequency will vary ±0.5% to ±1%)")
    print("  - This is expected behavior for EMI reduction")
else:
    print("SSC is disabled")

# Step 6: Check DFS
print("\n=== DFS Check ===")
print("Check if dynamic frequency scaling is in progress")
# Read DFS status register (if available)
# dfs_status = pch.isclk.dfs_status.read()
print("If DFS is active, frequency may be transitioning")

# Step 7: Verify register writes
print("\n=== Register Write Verification ===")
print("Re-writing IOSF divider and verifying readback...")
original_div = iosf_div
pch.isclk.clk_div.iosf.write(original_div)
readback_div = pch.isclk.clk_div.iosf.read()
if readback_div == original_div:
    print("Register write successful (readback matches)")
else:
    print(f"Register write FAILED (wrote 0x{original_div:08x}, read 0x{readback_div:08x})")
    print("CONCLUSION: Register access issue (bus error, lock, or HW defect)")
```

### Workflow 3: Debug Clock Gating Issues

**Objective**: Debug clock gating control that is not functioning as expected.

**Steps**:
1. Query HAS for clock gating specifications
2. Read clock gating control registers
3. Check PMC firmware gating overrides
4. Measure power consumption to verify gating state
5. Check gating dependencies (upstream conditions)
6. Test manual gating control
7. Check for register commit requirements
8. Apply fixes and re-test

**Example Code**:
```python
from namednodes import *

# Step 1: Query HAS
print("Query Co-Design: 'Show me ISClk clock gating control from Chap44_0'")

# Step 2: Read gating control
print("\n=== Clock Gating Status ===")
iosf_gate = pch.isclk.clk_gate_ctrl.iosf.read()
gate_policy = pch.isclk.clk_gate_policy.read()
print(f"IOSF Gating Control: 0x{iosf_gate:08x}")
print(f"Global Gating Policy: 0x{gate_policy:08x}")

if (iosf_gate & 0x1) != 0:
    print("IOSF clock gating is ENABLED (per register)")
else:
    print("IOSF clock gating is DISABLED (per register)")

# Step 3: Check PMC overrides
print("\n=== PMC Override Check ===")
pmc_clk_req = pch.isclk.pmc_clk_req.read()
print(f"PMC Clock Request: 0x{pmc_clk_req:08x}")
if (pmc_clk_req & 0x1) != 0:
    print("PMC is requesting IOSF clock ON (overriding SW gating control)")
    print("CONCLUSION: PMC firmware is forcing clock active")
else:
    print("PMC is not overriding IOSF clock gating")

# Step 4: Measure power consumption
print("\n=== Power Measurement ===")
print("ACTION: Measure platform power consumption")
print("  - With gating enabled, power should decrease")
print("  - If power does not decrease, gating is not effective")
baseline_power = float(input("Enter baseline power (mW, gating disabled): "))
gated_power = float(input("Enter gated power (mW, gating enabled): "))
power_savings = baseline_power - gated_power
print(f"Power Savings: {power_savings} mW ({power_savings/baseline_power*100:.1f}%)")

if power_savings < 0.01 * baseline_power:
    print("Power savings < 1% (gating not working)")
else:
    print("Power savings detected (gating is working)")

# Step 5: Check gating dependencies
print("\n=== Gating Dependencies ===")
print("Check if IOSF gating has upstream dependencies:")
print("  - Fabric clock must be gated first")
print("  - No active IOSF transactions")
print("  - PMC permission required")
# Read dependency status registers (if available)

# Step 6: Test manual gating
print("\n=== Manual Gating Test ===")
print("Disabling IOSF clock gating...")
pch.isclk.clk_gate_ctrl.iosf.write(0x0)
readback = pch.isclk.clk_gate_ctrl.iosf.read()
if (readback & 0x1) == 0:
    print("Gating disabled successfully")
else:
    print("Gating control register did not change (stuck or locked)")

print("Enabling IOSF clock gating...")
pch.isclk.clk_gate_ctrl.iosf.write(0x1)
readback = pch.isclk.clk_gate_ctrl.iosf.read()
if (readback & 0x1) == 0x1:
    print("Gating enabled successfully")
else:
    print("Gating control register did not change (stuck or locked)")

# Step 7: Check commit requirement
print("\n=== Register Commit Check ===")
print("Some platforms require a 'commit' write to apply gating changes")
print("Check HAS for commit register requirement")
# If commit required:
# pch.isclk.clk_gate_commit.write(0x1)
```

### Workflow 4: Debug Boot Hang (Clock-Related)

**Objective**: Debug system boot hang caused by ISClk issues.

**Steps**:
1. Capture POST code via TTK3-POSTCODE agent
2. Capture UART boot log via TTK3-UART agent
3. Identify last successful boot stage
4. Query HAS for clock initialization sequence
5. Check which PLL or clock is failing
6. Use TTK3-GPIO to monitor platform power states
7. If crystal failure, measure crystal with oscilloscope
8. Apply BIOS workaround or update IFWI
9. If hardware defect, escalate

**Example Code (TTK3 Integration)**:
```python
# This workflow uses TTK3 agents for hardware-level debug

# Step 1: Capture POST code
print("=== POST Code Capture ===")
print("Use TTK3-POSTCODE agent to capture POST codes during boot")
print("Command: ttk3 postcode monitor --duration 60")
print("Look for last POST code before hang")
# Example output: Last POST code = 0x15 (PLL initialization)

# Step 2: Capture UART log
print("\n=== UART Boot Log ===")
print("Use TTK3-UART agent to capture BIOS boot log")
print("Command: ttk3 uart read --port 0 --baud 115200 --duration 60")
print("Look for last log message before hang")
# Example output: "Initializing Main PLL..." (then hangs)

# Step 3: Identify failure point
print("\n=== Failure Point Analysis ===")
print("POST code 0x15 = PLL initialization phase")
print("UART log stopped at 'Initializing Main PLL...'")
print("CONCLUSION: Main PLL lock failure during boot")

# Step 4: Query HAS for boot sequence
print("\n=== HAS Boot Sequence ===")
print("Query Co-Design: 'Show me ISClk boot initialization sequence from Chap44_0'")
print("Expected sequence:")
print("  1. FilterPLL lock (crystal)")
print("  2. Main PLL lock")
print("  3. HP PLL lock")
print("  4. Other PLLs as needed")
print("  5. Clock distribution enable")

# Step 5: Check which PLL is failing
print("\n=== PLL Status Check ===")
print("Use TTK3-I2C or TTK3-SPI to read ISClk registers during hang")
print("Command: ttk3 i2c read --bus 0 --addr 0x50 --reg 0x100 --count 4")
# Read PLL lock status registers
print("Example: Main PLL lock status = 0x0 (UNLOCKED)")

# Step 6: Monitor power states
print("\n=== Power State Monitoring ===")
print("Use TTK3-GPIO agent to monitor platform power states")
print("Command: ttk3 gpio monitor --pin SLP_S0# --duration 60")
print("Check if platform is in S0 (SLP_S0# = HIGH)")
print("If not in S0, clock initialization may not have started")

# Step 7: Measure crystal
print("\n=== Crystal Measurement ===")
print("If FilterPLL is suspected to be failing:")
print("  1. Connect oscilloscope probe to crystal output (use TTK3 as reference)")
print("  2. Measure 38.4 MHz signal")
print("  3. Check amplitude (> 0.5V pk-pk)")
print("  4. Check startup time (< 10 ms)")

# Step 8: BIOS workaround
print("\n=== BIOS/IFWI Workaround ===")
print("If known BIOS issue:")
print("  1. Update to latest BIOS/IFWI version")
print("  2. Check for BIOS clock initialization patches")
print("  3. Apply BIOS workaround (e.g., increase PLL lock timeout)")

# Step 9: Escalation
print("\n=== Escalation ===")
print("If hardware defect suspected:")
print("  1. Try different board (to rule out board-level issue)")
print("  2. Try different silicon (to rule out die-level defect)")
print("  3. File HSDES sighting with POST codes, UART log, TTK3 debug data")
print("  4. Escalate to Silicon Debug team")
```

### Workflow 5: Debug S0ix Clock Issues

**Objective**: Debug ISClk issues preventing S0ix entry or causing S0ix exit failures.

**Steps**:
1. Query HAS for S0ix clock requirements
2. Use FV-PM-SOUTH agent to coordinate S0ix entry
3. Monitor clock gating during S0ix entry via registers
4. Check retention clock configuration (PMC ART, RTC)
5. Verify PC10 is reached (all clocks gated except retention)
6. Test S0ix exit and measure PLL re-lock time
7. Check sTRC logs for S0ix clock errors
8. Apply S0ix clock workarounds
9. Integrate with FV_Debugger_V1 for NGA S0ix failure analysis

**Example Code**:
```python
from namednodes import *
import time

# Step 1: Query HAS
print("Query Co-Design: 'Show me ISClk S0ix entry sequence from Chap44_0'")

# Step 2: Coordinate with FV-PM-SOUTH
print("\n=== S0ix Entry Coordination ===")
print("Use FV-PM-SOUTH agent to trigger S0ix entry")
print("This will coordinate PMC firmware and ISClk")

# Step 3: Monitor clock gating during entry
print("\n=== Clock Gating Monitoring ===")
print("Reading clock gating status before S0ix entry...")
iosf_gate_before = pch.isclk.clk_gate_ctrl.iosf.read()
fabric_gate_before = pch.isclk.clk_gate_ctrl.fabric.read()
print(f"IOSF Gating (before): 0x{iosf_gate_before:08x}")
print(f"Fabric Gating (before): 0x{fabric_gate_before:08x}")

print("Entering S0ix...")
# <S0ix entry code via FV-PM-SOUTH>
time.sleep(2)  # Wait for entry

print("Reading clock gating status in S0ix...")
iosf_gate_in = pch.isclk.clk_gate_ctrl.iosf.read()
fabric_gate_in = pch.isclk.clk_gate_ctrl.fabric.read()
print(f"IOSF Gating (in S0ix): 0x{iosf_gate_in:08x}")
print(f"Fabric Gating (in S0ix): 0x{fabric_gate_in:08x}")

if (iosf_gate_in & 0x1) == 0x1:
    print("IOSF clock is gated in S0ix: PASS")
else:
    print("IOSF clock is NOT gated in S0ix: FAIL (will prevent PC10)")

# Step 4: Check retention clocks
print("\n=== Retention Clock Check ===")
retention_status = pch.isclk.s0ix_clk_retention_status.read()
print(f"Retention Status: 0x{retention_status:08x}")
if (retention_status & 0x1) == 0x1:
    print("PMC ART (38.4 MHz) is active: PASS")
else:
    print("PMC ART is NOT active: FAIL (PMC will malfunction)")

# Step 5: Verify PC10
print("\n=== PC10 Verification ===")
print("Use FV-PM-SOUTH agent to check PC10 status")
# pc10_status = fv_pm_south.read_pc10_status()
print("If PC10 is NOT reached, ISClk clock is preventing deep sleep")
print("Check which clock is not gated (enumerate all gating registers)")

# Step 6: Test S0ix exit
print("\n=== S0ix Exit Test ===")
print("Exiting S0ix...")
start = time.time()
# <S0ix exit code via FV-PM-SOUTH>
exit_time = time.time() - start

# Check PLL re-lock time
main_pll_lock = pch.isclk.main_pll.lock_status.read()
if (main_pll_lock & 0x1) == 0x1:
    print(f"Main PLL re-locked after S0ix exit: {exit_time:.2f}s")
    if exit_time > 1.0:
        print("WARNING: PLL re-lock time > 1 second (slow resume)")
else:
    print("Main PLL FAILED to re-lock after S0ix exit")

# Step 7: Check sTRC logs
print("\n=== sTRC Log Analysis ===")
strc_error_code = pch.isclk.strc_clk_error_code.read()
if strc_error_code != 0:
    print(f"sTRC Error Code: 0x{strc_error_code:08x}")
    # Decode error code (consult HAS)
    if strc_error_code == 0x10:
        print("  - Clock gating failure during S0ix entry")
    elif strc_error_code == 0x11:
        print("  - Clock restoration failure during S0ix exit")
else:
    print("No sTRC errors")

# Step 8: Apply workarounds
print("\n=== Workarounds ===")
print("Search HSDES for: 'ISClk S0ix clock gating failure NVL'")
print("Common workarounds:")
print("  - Increase PLL re-lock timeout")
print("  - Pre-lock DDIPLL before GPU resume")
print("  - Force PMC clock request during S0ix transition")

# Step 9: NGA failure analysis
print("\n=== NGA Failure Analysis ===")
print("Use FV_Debugger_V1 agent to analyze NGA S0ix test failures")
print("Command: Search NGA for S0ix failures with 'clock' keyword")
print("Correlate NGA failure patterns with ISClk debug data")
```

### Workflow 6: Debug Display Clock Issues

**Objective**: Debug display artifacts or issues caused by ISClk DDIPLL problems.

**Steps**:
1. Query HAS for DDIPLL specifications
2. Read DDIPLL configuration and lock status
3. Measure DDIPLL output frequency with oscilloscope
4. Check for SSC interference from Main PLL
5. Check display clock divider configuration
6. Test DDIPLL stability (jitter measurement)
7. Check VccDisplay and VccPLL voltage rails
8. Apply DDIPLL workarounds
9. Coordinate with display driver team if needed

**Example Code**:
```python
from namednodes import *
import time

# Step 1: Query HAS
print("Query Co-Design: 'Show me DDIPLL specifications from Chap44_0'")
print("Expected frequencies: 810 MHz or 1250 MHz")

# Step 2: Read DDIPLL configuration
print("\n=== DDIPLL Configuration ===")
ddipll_enable = pch.isclk.ddipll.enable.read()
ddipll_freq_sel = pch.isclk.ddipll.freq_sel.read()
ddipll_lock = pch.isclk.ddipll.lock_status.read()
print(f"DDIPLL Enable: 0x{ddipll_enable:08x}")
print(f"DDIPLL Freq Sel: 0x{ddipll_freq_sel:08x}")
print(f"DDIPLL Lock: {'LOCKED' if (ddipll_lock & 0x1) else 'UNLOCKED'}")

# Decode frequency
if ddipll_freq_sel == 0x0:
    expected_freq = 810
elif ddipll_freq_sel == 0x1:
    expected_freq = 1250
else:
    expected_freq = "Unknown"
print(f"Expected DDIPLL Frequency: {expected_freq} MHz")

# Step 3: Measure frequency
print("\n=== Frequency Measurement ===")
print("ACTION: Measure DDIPLL output (o_ck_ddi) with oscilloscope")
print("  - Connect probe to DDI clock test point")
print("  - Measure frequency and jitter")

# Step 4: Check SSC interference
print("\n=== SSC Interference Check ===")
main_pll_ssc = pch.isclk.main_pll.ssc_ctrl.read()
if (main_pll_ssc & 0x1) != 0:
    print("Main PLL SSC is ENABLED")
    print("Known Issue: Main PLL SSC can cause DDIPLL instability")
    print("Workaround: Disable Main PLL SSC when display is active")
    print("Disabling Main PLL SSC...")
    pch.isclk.main_pll.ssc_ctrl.write(0x0)
    time.sleep(0.1)
    print("Re-check display artifacts after SSC disable")
else:
    print("Main PLL SSC is disabled (no interference)")

# Step 5: Check display divider
print("\n=== Display Clock Divider ===")
display_div = pch.isclk.clk_div.display.read()
print(f"Display Divider: 0x{display_div:08x}")
# Verify divider is correct for display mode

# Step 6: Test stability (jitter)
print("\n=== DDIPLL Stability Test ===")
print("ACTION: Measure DDIPLL jitter with oscilloscope")
print("  - Use jitter measurement function")
print("  - Expected jitter: < 50 ps RMS (consult HAS)")
print("  - If jitter > 50 ps, DDIPLL is unstable")

# Step 7: Check voltage rails
print("\n=== Voltage Rail Check ===")
print("ACTION: Measure VccDisplay and VccPLL voltages")
print("  - VccDisplay: 1.05V ±50mV")
print("  - VccPLL: 1.05V ±50mV")
print("  - Check for noise or droop during display activity")

# Step 8: Apply workarounds
print("\n=== Workarounds ===")
print("Search HSDES for: 'DDIPLL display artifacts NVL'")
print("Common workarounds:")
print("  - Disable Main PLL SSC")
print("  - Increase VccPLL voltage by 50 mV")
print("  - Use 810 MHz mode instead of 1250 MHz")

# Step 9: Coordinate with display driver
print("\n=== Display Driver Coordination ===")
print("If ISClk DDIPLL is confirmed stable:")
print("  - Issue may be in display driver or panel")
print("  - Coordinate with Display team for further debug")
```

---

## HSDES Sighting Search and Correlation

### Using HSDES Agent

**FV-ISClk agent should use the `hsdes` skill** to search for ISClk-related sightings.

**Example Search Queries**:
```python
# Search for PLL lock failures
hsdes.search("tenant:sighting subject:'ISClk PLL lock failure' platform:NVL")

# Search for S0ix clock issues
hsdes.search("tenant:sighting subject:'S0ix clock' component:ISClk platform:NVL")

# Search for display clock issues
hsdes.search("tenant:sighting subject:'DDIPLL' OR subject:'display clock' platform:NVL")

# Search for known ISClk bugs
hsdes.search("tenant:bug component:ISClk platform:NVL status:open,fixed")
```

### Correlating NGA Failures with HSDES

**Use FV_Debugger_V1 agent** to correlate NGA test failures with HSDES sightings:

1. **Extract failure signature** from NGA test result (error message, logs)
2. **Search HSDES** for similar failures using keywords
3. **Match failure signature** to known HSDES sighting
4. **Apply workaround** or escalate if no known fix

**Example Workflow**:
```
1. NGA test "S0ix_Entry_Exit" fails with error "PC10 not reached"
2. Extract keywords: "S0ix", "PC10", "clock gating"
3. Search HSDES: "S0ix PC10 clock gating ISClk NVL"
4. Find HSDES sighting: "ISClk fabric clock not gating in S0ix"
5. Apply workaround from HSDES: "Force fabric clock gating via PMC override"
6. Re-run NGA test to verify fix
```

---

## Known ISClk Errata and Workarounds

### Erratum 1: Main PLL SSC Causes DDIPLL Instability (PCH-H)

**Symptom**: Display flicker when Main PLL SSC enabled  
**Platforms**: NVL PCH-H (all steppings)  
**Workaround**: Disable Main PLL SSC when DDIPLL is active  
**HSDES**: [Link to bug]  
**Code**:
```python
pch.isclk.main_pll.ssc_ctrl.write(0x0)  # Disable SSC
```

### Erratum 2: OC PLL Lock Failure Above 1800 MHz (PCH-H)

**Symptom**: OC PLL fails to lock at 1900-2000 MHz  
**Platforms**: NVL PCH-H stepping A0  
**Workaround**: Increase VccPLL by 50 mV or limit OC PLL to 1800 MHz  
**HSDES**: [Link to bug]  
**Code**:
```python
# Increase VccPLL voltage (requires platform-specific voltage control)
# OR limit frequency
pch.isclk.oc_pll.freq_sel.write(0x8)  # Max 1800 MHz
```

### Erratum 3: Type-C PLL Lock Delay on Cold Boot (PCH-S)

**Symptom**: Type-C PLL takes > 500 ms to lock on cold boot  
**Platforms**: NVL PCH-S (all steppings)  
**Workaround**: Increase PLL lock timeout to 1 second  
**HSDES**: [Link to bug]  
**Code**:
```python
# Increase timeout in PLL lock polling loop
timeout = 1.0  # 1 second instead of 500 ms
```

### Erratum 4: Shared PLL Contention on SoC During CPU DVFS

**Symptom**: IOSF clock glitches when CPU changes P-state  
**Platforms**: NVL SoC (all steppings)  
**Workaround**: Coordinate ISClk divider changes with CPU DVFS  
**HSDES**: [Link to bug]  
**Code**:
```python
# Requires CPU PM coordination (complex, see detailed workaround in HSDES)
```

### Erratum 5: S0ix Resume Delay Due to DDIPLL Lock Time (SoC)

**Symptom**: Display takes 1-2 seconds to restore after S0ix exit  
**Platforms**: NVL SoC (all steppings)  
**Workaround**: Pre-lock DDIPLL before GPU resume  
**HSDES**: [Link to bug]  
**Code**:
```python
# Pre-lock DDIPLL during S0ix exit sequence (before GPU power-on)
pch.isclk.ddipll.enable.write(0x1)
time.sleep(0.1)  # Wait for lock
# Then proceed with GPU power-on
```

---

## Root Cause Analysis Decision Tree

```
ISClk Failure Detected
│
├─ Boot Hang?
│  ├─ YES → Check POST code and UART log
│  │       ├─ Stuck at PLL init? → PLL Lock Failure (see Workflow 1)
│  │       └─ Stuck at clock enable? → Clock Sequencing Error
│  └─ NO → Continue
│
├─ Display Issue?
│  ├─ YES → Check DDIPLL
│  │       ├─ DDIPLL unlocked? → PLL Lock Failure (see Workflow 1)
│  │       ├─ DDIPLL locked but artifacts? → SSC Interference or Jitter (see Workflow 6)
│  │       └─ DDIPLL frequency wrong? → Frequency Mismatch (see Workflow 2)
│  └─ NO → Continue
│
├─ S0ix Failure?
│  ├─ YES → Check S0ix phase
│  │       ├─ Entry failure (PC10 not reached)? → Clock Gating Issue (see Workflow 3)
│  │       ├─ Exit failure (hang or slow)? → PLL Re-lock Issue (see Workflow 5)
│  │       └─ Resume display delay? → DDIPLL Pre-lock Needed (see Erratum 5)
│  └─ NO → Continue
│
├─ Frequency Mismatch?
│  ├─ YES → Check clock path
│  │       ├─ PLL frequency wrong? → PLL Configuration Error
│  │       ├─ Divider wrong? → Divider Configuration Error
│  │       ├─ Mux wrong? → Mux Configuration Error
│  │       └─ SSC enabled? → Expected Modulation (see Workflow 2)
│  └─ NO → Continue
│
├─ Clock Gating Issue?
│  ├─ YES → Check gating control
│  │       ├─ PMC override? → PMC Forcing Clock On (see Workflow 3)
│  │       ├─ Register locked? → Register Access Issue
│  │       └─ Dependencies not met? → Upstream Condition Not Satisfied
│  └─ NO → Continue
│
└─ Unknown Failure → Collect full debug data and escalate
   ├─ Register dump (all ISClk registers)
   ├─ sTRC logs
   ├─ TTK3 hardware measurements (clocks, voltages)
   ├─ POST codes and UART logs
   └─ File HSDES sighting
```

---

## Integration with Other Agents

### FV_Debugger_V1 (NGA Failure Triage)

**Use Case**: Automated NGA test failure analysis

**Integration**:
```python
# FV-ISClk agent should invoke FV_Debugger_V1 for NGA failures
# Example: NGA test "ISClk_PLL_Lock_Stress" fails
# 1. FV_Debugger_V1 extracts failure logs from NGA
# 2. FV_Debugger_V1 searches HSDES for similar failures
# 3. FV_Debugger_V1 calls FV-ISClk agent with failure context
# 4. FV-ISClk agent applies debug workflow (e.g., Workflow 1)
# 5. FV-ISClk agent returns root cause and remediation
# 6. FV_Debugger_V1 logs analysis and creates HSDES sighting if needed
```

### TTK3 Agents (Hardware Debug)

**Use Case**: Low-level hardware access for boot hang or register access

**Integration**:
- **TTK3-UART**: Capture BIOS boot log for clock initialization debug
- **TTK3-POSTCODE**: Capture POST codes to identify boot hang phase
- **TTK3-GPIO**: Monitor platform power states (S0, S0ix, etc.)
- **TTK3-I2C**: Read ISClk registers via sideband (if MMIO not accessible)
- **TTK3-POWER**: Control platform power for boot testing

### FV-PM-SOUTH (S0ix Coordination)

**Use Case**: S0ix clock coordination and PC10 tracking

**Integration**:
```python
# FV-ISClk agent should coordinate with FV-PM-SOUTH for S0ix workflows
# Example: S0ix entry test
# 1. FV-PM-SOUTH triggers S0ix entry
# 2. FV-ISClk monitors clock gating during entry
# 3. FV-PM-SOUTH checks PC10 status
# 4. If PC10 not reached, FV-ISClk identifies which clock is not gated
# 5. FV-ISClk applies gating fix
# 6. FV-PM-SOUTH re-tests S0ix entry
```

---

## Summary Checklist

When debugging ISClk issues, ensure:
- [ ] Query HAS via Co-Design for expected behavior
- [ ] Identify failure signature (PLL lock, frequency mismatch, gating, boot hang, S0ix, display)
- [ ] Follow appropriate debug workflow
- [ ] Collect register dumps and sTRC logs
- [ ] Use TTK3 agents for hardware-level debug if needed
- [ ] Search HSDES for known issues and workarounds
- [ ] Correlate with NGA test failures via FV_Debugger_V1
- [ ] Apply workarounds from known errata
- [ ] Use root cause analysis decision tree to narrow down issue
- [ ] Document findings and remediation
- [ ] File HSDES sighting if new issue discovered
- [ ] Escalate to Silicon Debug if hardware defect suspected

---

**End of fv-isclk/debug sub-skill**
