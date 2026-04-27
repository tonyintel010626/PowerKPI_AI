# FV-ISClk Sub-Skill: PLL Configuration & Validation

**Owner**: Ooi, Ling Wei (lingweio)

**Parent Skill**: fv-isclk

**Focus**: PLL (Phase-Locked Loop) configuration, locking validation, and stability testing

---

## Overview

This sub-skill provides specialized knowledge for validating all ISClk PLLs on NVL platforms. PLLs are critical components that generate stable, precise clock frequencies from reference sources. Proper PLL configuration and validation ensures clock stability across all platform operating conditions.

---

## PLL Types in ISClk

### 1. Main PLL

**Purpose**: Primary clock source for fabric and interconnect

**Key Characteristics**:
- Configurable frequency range: 800 MHz - 1200 MHz (typical)
- Drives fabric interconnect (PSF, ICC)
- Critical for platform operation - must lock early in boot

**Validation Focus**:
- Lock time < 100 µs (verify against HAS spec)
- Stability across voltage/temperature corners
- SSC modulation within ±0.5% for EMI compliance

**HAS Query Example**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: What are the Main PLL frequency range and lock time requirements?"
```

---

### 2. HP PLL (High-Performance PLL)

**Purpose**: High-frequency compute domain clocks

**Key Characteristics**:
- Higher frequency range: 1.5 GHz - 3.0 GHz (typical)
- Drives CPU, GPU, NPU domains
- Performance-critical, may have tighter jitter requirements

**Validation Focus**:
- Lock time and stability at high frequencies
- Jitter performance (if measurement tools available)
- Voltage/temperature sensitivity at high frequencies

---

### 3. Overclocking PLL

**Purpose**: Performance boost scenarios

**Key Characteristics**:
- Extended frequency range beyond nominal
- May have relaxed stability requirements
- Used for turbo/boost modes

**Validation Focus**:
- Lock behavior at overclocked frequencies
- Thermal throttling coordination
- Graceful fallback to nominal frequencies

---

### 4. Display PLL (DDIPLL)

**Purpose**: Display interface clocking

**Key Characteristics**:
- Configurable for different display modes: 810 MHz, 1250 MHz
- Drives display and Thunderbolt interfaces
- Must meet display timing requirements

**Validation Focus**:
- Lock stability for display refresh rates
- Mode switching (810 MHz ↔ 1250 MHz)
- Thunderbolt compliance

---

### 5. Type-C PLL

**Purpose**: Type-C/Thunderbolt clocking

**Key Characteristics**:
- Type-C protocol timing requirements
- Thunderbolt data rate support
- Fast lock time for hotplug scenarios

**Validation Focus**:
- Lock time for hotplug events
- Stability during data transmission
- Compliance with USB-C specifications

---

### 6. D2D PLL (Die-to-Die PLL)

**Purpose**: Multi-die interconnect clocking

**Key Characteristics**:
- High-speed die-to-die communication
- Synchronization across dies
- Low jitter requirements for data integrity

**Validation Focus**:
- Phase alignment across dies
- Jitter performance
- Lock stability for high-speed links

---

### 7. FilterPLL

**Purpose**: Clean reference clocks for downstream PLLs

**Key Characteristics**:
- Filters jitter from crystal oscillator
- Provides stable reference (typically 38.4 MHz)
- Feeds Display PLLs, SA PLLs, PMC ART

**Validation Focus**:
- Output frequency accuracy
- Jitter filtering effectiveness
- Stability as reference source

---

## PLL Configuration Parameters

### Frequency Selection

PLLs support multiple output frequencies via configuration registers:

**Configuration Method**:
```python
# Example: Configure Main PLL to 1000 MHz
target.isclk.main_pll.freq_select.write(value=0x10)  # Value from HAS
target.isclk.main_pll.enable.write(value=1)

# Wait for lock
timeout = 1000  # µs
start_time = time.time()
while not target.isclk.main_pll.status.lock.read():
    if (time.time() - start_time) * 1e6 > timeout:
        print("ERROR: Main PLL lock timeout")
        break
    time.sleep(0.001)

lock_time_us = (time.time() - start_time) * 1e6
print(f"Main PLL locked in {lock_time_us:.1f} µs")
```

**Validation Steps**:
1. Query HAS for supported frequencies
2. Configure PLL frequency register
3. Enable PLL
4. Monitor lock status register
5. Measure lock time
6. Validate output frequency (if counter available)

---

### SSC (Spread Spectrum Clocking)

SSC modulates clock frequency to reduce EMI (Electromagnetic Interference):

**SSC Configuration**:
- **Modulation Percentage**: Typically ±0.5% (configurable)
- **Modulation Frequency**: 30-33 kHz typical
- **SSC Enable**: Per-PLL configuration bit

**Configuration Method**:
```python
# Enable SSC on Main PLL
target.isclk.main_pll.ssc_enable.write(value=1)
target.isclk.main_pll.ssc_modulation_pct.write(value=0x05)  # 0.5%
target.isclk.main_pll.ssc_freq_khz.write(value=0x1F)  # 31 kHz
```

**SSC Validation**:
1. Query HAS for SSC requirements (especially for PCIe compliance)
2. Configure SSC parameters
3. Validate modulation percentage (spectrum analyzer if available)
4. Check EMI reduction (if lab equipment available)
5. Verify downstream devices tolerate SSC (e.g., PCIe link training succeeds)

**PCIe Compliance Note**: PCIe reference clocks typically require SSC within ±0.5% for compliance

---

### PLL Lock Detection

**Lock Status Register**:
```python
pll_status = target.isclk.main_pll.status.read()
print(f"Lock status: {pll_status.lock}")
print(f"Lock time: {pll_status.lock_time_us} µs")
print(f"VCO frequency: {pll_status.vco_freq_mhz} MHz")
```

**Lock Validation**:
- **Lock Bit**: Status register indicates PLL locked
- **Lock Time**: Time from enable to lock assertion
- **Lock Stability**: Monitor lock bit over time (should remain asserted)

---

## PLL Validation Workflows

### Workflow 1: Basic PLL Lock Validation

**Objective**: Validate PLL locks correctly during boot or configuration

**HAS Query First**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the lock time requirement for [PLL_NAME]?"
```

**Steps**:
1. **Read Current Status**: Check if PLL is already locked (from BIOS)
   ```python
   status = target.isclk.main_pll.status.read()
   if status.lock:
       print("Main PLL already locked by BIOS")
   ```

2. **Configure PLL** (if needed):
   ```python
   target.isclk.main_pll.freq_select.write(value=freq_code)
   target.isclk.main_pll.ssc_enable.write(value=ssc_enable)
   ```

3. **Enable PLL**:
   ```python
   target.isclk.main_pll.enable.write(value=1)
   ```

4. **Monitor Lock Status**:
   ```python
   timeout_us = 1000  # Query HAS for spec
   start_time = time.time()
   while not target.isclk.main_pll.status.lock.read():
       elapsed_us = (time.time() - start_time) * 1e6
       if elapsed_us > timeout_us:
           print(f"ERROR: PLL lock timeout after {elapsed_us:.1f} µs")
           return False
       time.sleep(0.001)
   
   lock_time_us = (time.time() - start_time) * 1e6
   print(f"SUCCESS: PLL locked in {lock_time_us:.1f} µs")
   ```

5. **Validate Lock Time**:
   - Compare measured lock time against HAS specification
   - Typical spec: < 100 µs for most PLLs

6. **Report Results**:
   - Document lock time
   - Note any deviations from HAS spec
   - Log voltage/temperature conditions

**Expected Outcome**: PLL locks within HAS-specified time

---

### Workflow 2: PLL Stability Testing

**Objective**: Validate PLL remains locked over time and conditions

**Steps**:
1. **Initial Lock**: Validate PLL locks successfully (Workflow 1)

2. **Long-Duration Monitoring**:
   ```python
   duration_sec = 60  # Monitor for 60 seconds
   start_time = time.time()
   lock_failures = 0
   
   while (time.time() - start_time) < duration_sec:
       status = target.isclk.main_pll.status.read()
       if not status.lock:
           lock_failures += 1
           print(f"WARNING: PLL lock lost at t={time.time()-start_time:.1f}s")
       time.sleep(0.1)  # Check every 100ms
   
   print(f"Stability test: {lock_failures} lock failures in {duration_sec}s")
   ```

3. **Stress Scenarios** (optional):
   - Run workloads to stress power delivery
   - Monitor lock status during thermal transitions
   - Check lock during voltage droops

**Expected Outcome**: PLL remains locked (no lock failures) throughout monitoring period

---

### Workflow 3: Voltage/Temperature Corner Testing

**Objective**: Validate PLL stability across voltage and temperature corners

**VT Corners**:
- **Nominal**: Typical voltage and temperature
- **Low Voltage**: Minimum operating voltage
- **High Temperature**: Maximum operating temperature
- **Low Voltage + High Temp**: Worst-case corner

**Steps**:
1. **Query HAS for VT Specifications**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What are the voltage and temperature operating ranges for Main PLL?"
   ```

2. **Set Up VT Corner** (via lab equipment or platform controls):
   - Adjust voltage regulator settings
   - Control thermal chamber (if available)
   - Use platform thermal throttling

3. **Run PLL Lock Validation** (Workflow 1) at each corner:
   - Nominal VT
   - Low voltage (e.g., 0.95V if nominal is 1.05V)
   - High temperature (e.g., 85°C if nominal is 25°C)
   - Low voltage + high temperature (worst case)

4. **Document Lock Behavior**:
   - Lock time at each corner
   - Lock stability at each corner
   - Note any corner-specific failures

5. **Compare Against HAS Margins**:
   - Validate lock time within spec at all corners
   - Identify if certain corners show degraded performance

**Expected Outcome**: PLL locks successfully at all specified VT corners

---

### Workflow 4: Multi-PLL Orchestration

**Objective**: Validate PLL dependencies and sequencing

**Background**: Some PLLs depend on others:
- Display PLL may reference FilterPLL output
- Downstream clocks depend on upstream PLLs

**Steps**:
1. **Query HAS for PLL Dependencies**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What are the PLL dependencies and lock sequencing requirements?"
   ```

2. **Identify PLL Sequence**:
   - FilterPLL → Display PLL (example)
   - Main PLL → Fabric clocks
   - HP PLL → Compute clocks

3. **Validate Sequence**:
   ```python
   # Step 1: Lock FilterPLL
   lock_pll(target.isclk.filter_pll)
   
   # Step 2: Lock Display PLL (depends on FilterPLL)
   lock_pll(target.isclk.display_pll)
   
   # Step 3: Validate Display PLL uses FilterPLL as reference
   ref_source = target.isclk.display_pll.ref_source.read()
   assert ref_source == "FilterPLL", "Display PLL should use FilterPLL as reference"
   ```

4. **Test Out-of-Sequence Scenarios** (negative testing):
   - Attempt to lock downstream PLL before upstream PLL
   - Validate error handling or graceful failure

**Expected Outcome**: PLLs lock in correct sequence, downstream PLLs properly reference upstream PLLs

---

### Workflow 5: PLL Error Injection and Recovery

**Objective**: Test PLL error handling and recovery mechanisms

**Error Scenarios**:
1. **Force PLL Unlock**: Disable PLL, check error reporting
2. **Frequency Out of Range**: Configure invalid frequency, check rejection
3. **Reference Loss**: Simulate crystal oscillator failure (if possible)

**Steps**:
1. **Query HAS for Error Handling**:
   ```
   "Reference NVL sTRC_CM Feature Guide: How are PLL lock failures detected and reported?"
   ```

2. **Inject Error**:
   ```python
   # Example: Force PLL unlock by disabling it
   target.isclk.main_pll.enable.write(value=0)
   time.sleep(0.01)  # Wait for unlock
   
   # Check error status
   error_status = target.isclk.main_pll.error_status.read()
   print(f"Error status: {error_status}")
   ```

3. **Validate Error Reporting**:
   - Check PLL status register shows unlock
   - Check sTRC logs for PLL error events
   - Check Clock Monitor error reporting (if available)

4. **Test Recovery**:
   ```python
   # Re-enable PLL
   target.isclk.main_pll.enable.write(value=1)
   
   # Validate re-lock
   if wait_for_lock(target.isclk.main_pll, timeout_us=1000):
       print("SUCCESS: PLL recovered and re-locked")
   else:
       print("ERROR: PLL failed to recover")
   ```

**Expected Outcome**: Errors are properly detected and reported, PLL can recover

---

## PLL Register Access (PythonSV)

### Common Register Operations

**Read PLL Status**:
```python
status = target.isclk.main_pll.status.read()
print(f"Lock: {status.lock}")
print(f"Enabled: {status.enabled}")
print(f"Frequency: {status.freq_mhz} MHz")
```

**Configure PLL**:
```python
# Configure frequency
target.isclk.main_pll.freq_select.write(value=0x10)

# Enable SSC
target.isclk.main_pll.ssc_enable.write(value=1)
target.isclk.main_pll.ssc_modulation.write(value=0x05)  # 0.5%

# Enable PLL
target.isclk.main_pll.enable.write(value=1)
```

**Check Error Status**:
```python
error = target.isclk.main_pll.error_status.read()
if error.lock_timeout:
    print("ERROR: PLL lock timeout")
if error.freq_out_of_range:
    print("ERROR: Frequency out of range")
```

---

## Integration with Other Skills

### With fv-isclk/clock-tree

After validating PLL locks, use `fv-isclk/clock-tree` to validate downstream clocks receive correct frequencies from PLLs.

### With fv-isclk/power

PLLs are shutdown/woken during power state transitions. Coordinate with `fv-isclk/power` for S0ix and Sx validation.

### With fv-isclk/debug

If PLL lock failures occur, use `fv-isclk/debug` for root cause analysis and HSDES correlation.

---

## Common PLL Issues and Debug

### Issue 1: PLL Lock Timeout

**Symptoms**: PLL fails to lock within specified time

**Debug Steps**:
1. Check reference clock is present and stable (crystal oscillator)
2. Verify PLL configuration (frequency in valid range)
3. Check voltage/temperature conditions (may be outside spec)
4. Query HSDES for known PLL lock issues on platform

**HSDES Query**:
```
"Search HSDES for 'PLL lock timeout' on NVL PCH-H"
```

---

### Issue 2: PLL Lock Instability

**Symptoms**: PLL locks but then loses lock intermittently

**Debug Steps**:
1. Monitor voltage rails for droops during lock loss
2. Check thermal conditions (overheating may cause instability)
3. Validate SSC configuration (excessive modulation may cause issues)
4. Check for interference from other clock domains

---

### Issue 3: Frequency Inaccuracy

**Symptoms**: PLL output frequency doesn't match configured frequency

**Debug Steps**:
1. Validate frequency measurement method (ensure accurate counter)
2. Check if SSC is enabled (will modulate frequency)
3. Verify PLL configuration register values
4. Query HAS for frequency tolerance specifications

---

## Tools and Utilities

### PythonSV Helper Functions

**Example: Generic PLL Lock Function**:
```python
def lock_pll(pll, timeout_us=1000):
    """Generic PLL lock function with timeout"""
    pll.enable.write(value=1)
    
    start_time = time.time()
    while not pll.status.lock.read():
        elapsed_us = (time.time() - start_time) * 1e6
        if elapsed_us > timeout_us:
            print(f"ERROR: PLL lock timeout after {elapsed_us:.1f} µs")
            return False
        time.sleep(0.001)
    
    lock_time_us = (time.time() - start_time) * 1e6
    print(f"PLL locked in {lock_time_us:.1f} µs")
    return True
```

### Lab Equipment (Placeholder)

*To be added by owner: oscilloscope, spectrum analyzer, frequency counter integrations*

---

## HAS References

**Primary HAS Document**: `Chap44_0_NVL_PCH_Internal_Clocks.html`

**Key Sections**:
- PLL specifications (frequency ranges, lock time requirements)
- PLL configuration registers
- PLL dependencies and sequencing
- SSC requirements and configuration

**Query HAS Before Validation**: Always verify PLL specifications from HAS before validation

---

## Summary

This sub-skill covers:
- ✅ All 7 ISClk PLL types (Main, HP, OC, Display, Type-C, D2D, FilterPLL)
- ✅ PLL configuration (frequency selection, SSC)
- ✅ PLL lock validation workflows
- ✅ PLL stability testing
- ✅ VT corner testing
- ✅ Multi-PLL orchestration
- ✅ Error injection and recovery
- ✅ PythonSV register access patterns
- ✅ Common PLL issues and debug

**When to Use**: Load this skill when validating PLL configuration, locking behavior, or debugging PLL-related issues.

**Next Steps**: After validating PLLs, use `fv-isclk/clock-tree` to validate downstream clock distribution.
