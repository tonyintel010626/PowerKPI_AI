# FV-ISClk Sub-Skill: Power Management Integration

**Owner**: Ooi, Ling Wei (lingweio)

**Parent Skill**: fv-isclk

**Focus**: ISClk-PMC coordination and low-power state validation

---

## Overview

This sub-skill provides specialized knowledge for validating ISClk integration with Power Management Controller (PMC) on NVL platforms. ISClk must coordinate closely with PMC during power state transitions (S0ix, Sx states) to ensure proper clock gating, PLL shutdown, and clock restoration.

---

## Power States and ISClk Requirements

### S0 (Active State)

**ISClk Behavior**:
- All required clocks running
- PLLs locked
- Selective clock gating for idle domains
- Dynamic frequency scaling active

**Validation**: Verify all functional clocks present, domains operational

---

### S0ix (Modern Standby)

**ISClk Behavior**:
- **Entry**:
  - Gate all non-essential clocks
  - Shutdown non-essential PLLs
  - Retain critical clocks (PMC ART, RTC)
  
- **Residence**:
  - Only retention clocks running
  - PLLs in low-power or shutdown state
  - Wake logic powered
  
- **Exit**:
  - Restore PLLs (lock required before ungating)
  - Ungate clocks in proper sequence
  - Resume normal operation

**Critical Requirement**: PC10 (Package C-state 10) achievement requires proper ISClk gating

**Validation**: Coordinate with **FV-PM-SOUTH** for S0ix validation

---

### S3 (Suspend to RAM)

**ISClk Behavior**:
- All PLLs shutdown except retention clocks
- Only RTC and minimal PMC clocks active
- DRAM retention clocks may remain active

**Validation**: Verify proper PLL shutdown, wake-up restoration

---

### S4 (Hibernate) / S5 (Soft Off)

**ISClk Behavior**:
- All PLLs shutdown
- Only RTC active (for wake timer)
- Platform powered off except wake logic

**Validation**: Verify all ISClk components off, wake-up from cold boot

---

## Retention Clocks

### Critical Always-On Clocks

**o_ck_xtal_pmc** (38.4 MHz):
- **Source**: FilterPLL → PMC ART (Always Running Timer)
- **Purpose**: PMC time base, S0ix timing, wake events
- **Requirement**: MUST remain active in S0ix
- **Validation**: Verify never gated during S0ix

**RTC Clock** (32.768 kHz):
- **Source**: Crystal oscillator (separate from main XTAL)
- **Purpose**: Real-time clock, wake timer
- **Requirement**: Always active (even in S5)
- **Validation**: Verify active in all power states

---

## S0ix Validation Workflows

### Workflow 1: S0ix Entry - Clock Gating Sequence

**Objective**: Validate proper clock gating during S0ix entry

**Prerequisites**: Coordinate with **FV-PM-SOUTH** for S0ix orchestration

**HAS Query First**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the ISClk gating sequence for S0ix entry?"
```

**Steps**:
1. **Baseline - S0 State**:
   ```python
   print("=== S0 Baseline ===")
   baseline_clocks = enumerate_active_clocks()
   print(f"Active clocks in S0: {len(baseline_clocks)}")
   for clk in baseline_clocks:
       print(f"  - {clk}")
   ```

2. **Initiate S0ix Entry** (coordinate with FV-PM-SOUTH):
   ```python
   print("\n=== Initiating S0ix Entry ===")
   # FV-PM-SOUTH will coordinate S0ix entry
   enter_s0ix()  # This triggers PM FW to gate clocks
   ```

3. **Monitor Clock Gating During Entry**:
   ```python
   # Poll gating status during entry
   timeout = 5.0  # seconds
   start_time = time.time()
   
   while (time.time() - start_time) < timeout:
       active_clocks = enumerate_active_clocks()
       print(f"Active clocks: {len(active_clocks)}")
       
       if check_s0ix_achieved():
           print("S0ix achieved")
           break
       
       time.sleep(0.1)
   ```

4. **Validate S0ix Residence - Clock State**:
   ```python
   print("\n=== S0ix Residence ===")
   s0ix_active_clocks = enumerate_active_clocks()
   print(f"Active clocks in S0ix: {len(s0ix_active_clocks)}")
   
   # Validate retention clocks are active
   pmc_art_active = is_clock_active('o_ck_xtal_pmc')
   rtc_active = is_clock_active('rtc_clk')
   
   if pmc_art_active:
       print("✓ PMC ART clock retained (o_ck_xtal_pmc)")
   else:
       print("✗ PMC ART clock gated (ERROR - should be retained!)")
   
   if rtc_active:
       print("✓ RTC clock retained")
   else:
       print("✗ RTC clock gated (ERROR - should be retained!)")
   ```

5. **Validate Non-Essential Clocks Gated**:
   ```python
   # Check that non-essential clocks are gated
   gated_clocks = [
       'o_ck_1ghz_iosf',  # Fabric clock
       'o_ck_ref_pcie',   # PCIe ref clock
       'o_ck_ddi',        # Display clock
   ]
   
   for clk in gated_clocks:
       if not is_clock_active(clk):
           print(f"✓ {clk} gated (expected)")
       else:
           print(f"✗ {clk} still active (should be gated!)")
   ```

6. **Validate PC10 Achievement** (coordinate with FV-PM-SOUTH):
   ```python
   pc10_achieved = check_pc10_status()
   if pc10_achieved:
       print("✓ PC10 achieved (ISClk gating successful)")
   else:
       print("✗ PC10 NOT achieved (ISClk gating issue?)")
       # Identify blocker
       blocker_clocks = identify_gating_blockers()
       print(f"Potential blocker clocks: {blocker_clocks}")
   ```

**Expected Outcome**: All non-essential clocks gated, retention clocks active, PC10 achieved

---

### Workflow 2: S0ix Exit - Clock Restoration

**Objective**: Validate proper clock ungating and PLL restoration during S0ix exit

**Steps**:
1. **S0ix Residence Baseline**:
   ```python
   print("=== S0ix Residence Baseline ===")
   s0ix_clocks = enumerate_active_clocks()
   print(f"Active clocks in S0ix: {len(s0ix_clocks)}")
   ```

2. **Initiate S0ix Exit**:
   ```python
   print("\n=== Initiating S0ix Exit ===")
   start_time = time.time()
   exit_s0ix()
   ```

3. **Monitor PLL Restoration**:
   ```python
   # Monitor PLLs coming back online
   plls_to_restore = ['main_pll', 'hp_pll', 'ref_pll', 'display_pll']
   
   for pll_name in plls_to_restore:
       pll = get_pll(pll_name)
       
       # Wait for PLL lock
       lock_timeout = 1.0  # second
       lock_start = time.time()
       
       while not pll.status.lock.read():
           if (time.time() - lock_start) > lock_timeout:
               print(f"✗ {pll_name} lock timeout during S0ix exit")
               break
           time.sleep(0.001)
       
       if pll.status.lock.read():
           lock_time = (time.time() - lock_start) * 1000  # ms
           print(f"✓ {pll_name} locked in {lock_time:.1f} ms")
       else:
           print(f"✗ {pll_name} failed to lock")
   ```

4. **Monitor Clock Ungating**:
   ```python
   # Monitor clocks being ungated
   while not check_s0_achieved():
       active_clocks = enumerate_active_clocks()
       print(f"Active clocks during exit: {len(active_clocks)}")
       time.sleep(0.1)
   
   exit_time = (time.time() - start_time) * 1000  # ms
   print(f"\nS0ix exit completed in {exit_time:.1f} ms")
   ```

5. **Validate All Clocks Restored**:
   ```python
   print("\n=== S0 Restored ===")
   restored_clocks = enumerate_active_clocks()
   print(f"Active clocks in S0: {len(restored_clocks)}")
   
   # Compare to baseline
   missing_clocks = set(baseline_clocks) - set(restored_clocks)
   if missing_clocks:
       print(f"✗ Clocks not restored: {missing_clocks}")
   else:
       print("✓ All clocks restored to S0 state")
   ```

6. **Validate Functionality After Exit**:
   ```python
   # Test that domains are operational
   test_domains = ['fabric', 'pcie', 'display']
   
   for domain in test_domains:
       if test_domain_operational(domain):
           print(f"✓ {domain} domain operational")
       else:
           print(f"✗ {domain} domain NOT operational")
   ```

**Expected Outcome**: All PLLs relock, all clocks ungated, domains operational

---

### Workflow 3: S0ix Stress Test (Multiple Cycles)

**Objective**: Validate S0ix entry/exit cycles repeatedly

**Steps**:
1. **Define Test Parameters**:
   ```python
   num_cycles = 100
   s0ix_duration_sec = 5  # Time in S0ix per cycle
   ```

2. **Run S0ix Cycles**:
   ```python
   failures = {
       'entry_failures': 0,
       'pc10_failures': 0,
       'exit_failures': 0,
       'pll_lock_failures': 0
   }
   
   for cycle in range(num_cycles):
       print(f"\n=== Cycle {cycle+1}/{num_cycles} ===")
       
       # Enter S0ix
       if not enter_s0ix():
           failures['entry_failures'] += 1
           continue
       
       # Check PC10
       if not check_pc10_status():
           failures['pc10_failures'] += 1
       
       # Remain in S0ix
       time.sleep(s0ix_duration_sec)
       
       # Exit S0ix
       if not exit_s0ix():
           failures['exit_failures'] += 1
           continue
       
       # Check PLLs relocked
       if not validate_plls_locked():
           failures['pll_lock_failures'] += 1
   ```

3. **Report Results**:
   ```python
   print(f"\n=== S0ix Stress Test Results ===")
   print(f"Total cycles: {num_cycles}")
   print(f"Entry failures: {failures['entry_failures']}")
   print(f"PC10 failures: {failures['pc10_failures']}")
   print(f"Exit failures: {failures['exit_failures']}")
   print(f"PLL lock failures: {failures['pll_lock_failures']}")
   
   total_failures = sum(failures.values())
   if total_failures == 0:
       print("\n✓ All S0ix cycles successful")
   else:
       print(f"\n✗ {total_failures} total failures")
   ```

**Expected Outcome**: All cycles successful, no accumulated errors

---

## Temperature-Aware Calibration

### Thermal Management and Clocking

**Background**: Clock frequencies may be adjusted based on temperature to:
- Reduce power/heat when temperature is high (thermal throttling)
- Improve accuracy with temperature compensation

**Validation Workflow**:

1. **Query HAS for Thermal Policies**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: Are there temperature-dependent clock adjustments?"
   ```

2. **Monitor Temperature and Frequency**:
   ```python
   import time
   
   duration_sec = 60
   interval_sec = 1
   
   data = []
   
   for i in range(int(duration_sec / interval_sec)):
       temp = read_platform_temperature()  # °C
       freq = measure_frequency('main_pll')  # MHz
       
       data.append({'time': i, 'temp': temp, 'freq': freq})
       print(f"t={i}s: Temp={temp}°C, Freq={freq} MHz")
       
       time.sleep(interval_sec)
   ```

3. **Analyze Correlation**:
   ```python
   # Check if frequency drops as temperature rises
   high_temp_data = [d for d in data if d['temp'] > 80]
   low_temp_data = [d for d in data if d['temp'] < 40]
   
   avg_freq_high_temp = sum([d['freq'] for d in high_temp_data]) / len(high_temp_data)
   avg_freq_low_temp = sum([d['freq'] for d in low_temp_data]) / len(low_temp_data)
   
   print(f"Average frequency at high temp (>80°C): {avg_freq_high_temp} MHz")
   print(f"Average frequency at low temp (<40°C): {avg_freq_low_temp} MHz")
   
   if avg_freq_high_temp < avg_freq_low_temp:
       print("✓ Thermal throttling detected (frequency reduced at high temp)")
   ```

**Expected Outcome**: Frequency adjusts based on temperature per thermal policy

---

## PLL Shutdown Sequencing for Sx States

### S3/S4/S5 PLL Shutdown

**Objective**: Validate proper PLL shutdown for deep sleep states

**Steps**:
1. **Query HAS for Shutdown Sequence**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the PLL shutdown sequence for S3 entry?"
   ```

2. **Initiate S3 Entry**:
   ```python
   print("=== Initiating S3 Entry ===")
   enter_s3()
   ```

3. **Monitor PLL Shutdown**:
   ```python
   plls = ['main_pll', 'hp_pll', 'ref_pll', 'display_pll', 'filter_pll']
   
   for pll_name in plls:
       pll = get_pll(pll_name)
       
       # Check if PLL is shutdown
       enabled = pll.enable.read()
       locked = pll.status.lock.read()
       
       if not enabled and not locked:
           print(f"✓ {pll_name} shutdown")
       else:
           print(f"✗ {pll_name} NOT shutdown (enabled={enabled}, locked={locked})")
   ```

4. **Validate Only RTC Active**:
   ```python
   active_clocks = enumerate_active_clocks()
   if active_clocks == ['rtc_clk']:
       print("✓ Only RTC clock active in S3")
   else:
       print(f"✗ Unexpected clocks active: {active_clocks}")
   ```

5. **Wake from S3 and Validate Restoration**:
   ```python
   print("\n=== Waking from S3 ===")
   wake_from_s3()
   
   # Validate all PLLs relock
   for pll_name in plls:
       if not wait_for_pll_lock(pll_name, timeout_sec=1.0):
           print(f"✗ {pll_name} failed to relock after S3 wake")
   ```

**Expected Outcome**: All PLLs shutdown in S3, successfully restored on wake

---

## Integration with FV-PM-SOUTH

### Coordinated S0ix Validation

**Pattern**: ISClk gating is a prerequisite for PC10 achievement

**Workflow**:
1. **FV-ISClk**: Validate ISClk gating sequence
2. **FV-PM-SOUTH**: Validate PMC achieves PC10
3. **Combined**: Validate ISClk gating enables PC10

**Example Coordination**:
```python
# ISClk validates gating
isclk_gating_ok = validate_isclk_s0ix_gating()

# FV-PM-SOUTH validates PC10
pc10_ok = fv_pm_south_validate_pc10()

# Combined result
if isclk_gating_ok and pc10_ok:
    print("✓ S0ix successful: ISClk gating + PC10 achieved")
elif isclk_gating_ok and not pc10_ok:
    print("✗ ISClk gating OK, but PC10 NOT achieved (non-ISClk blocker)")
elif not isclk_gating_ok and not pc10_ok:
    print("✗ ISClk gating issue blocking PC10")
```

**Delegation**: "Delegating to FV-PM-SOUTH to validate PC10 achievement while ISClk validates clock gating"

---

## Common Power Management Issues

### Issue 1: S0ix Entry Blocked by Clock Not Gating

**Symptoms**: PC10 not achieved, specific clock remains active

**Debug Steps**:
1. Identify which clock is not gating
2. Check if domain using that clock is truly idle
3. Check for FW override preventing gating
4. Check for HW dependency preventing gating

**HSDES Query**: Search for S0ix gating issues on platform

---

### Issue 2: PLL Fails to Relock After S0ix Exit

**Symptoms**: Boot hang or domain failure after S0ix exit

**Debug Steps**:
1. Check if PLL was properly shutdown during S0ix
2. Check if reference clock (XTAL) is stable
3. Check voltage rails during wakeup (may have droop)
4. Validate PLL configuration preserved during S0ix

---

### Issue 3: Clock Restoration Too Slow After S0ix

**Symptoms**: S0ix exit takes too long, performance degraded

**Debug Steps**:
1. Measure PLL lock times (may be longer than expected)
2. Check if ungating sequence is serialized (should be parallel)
3. Validate FW ungating logic is optimized

---

## HAS References

**Primary HAS Document**: `Chap44_0_NVL_PCH_Internal_Clocks.html`

**Key Sections**:
- Power state clock requirements
- S0ix gating sequences
- PLL shutdown/wakeup procedures
- Retention clock specifications

**Query HAS Before Validation**: Always verify power state requirements and sequences from HAS

---

## Summary

This sub-skill covers:
- ✅ Power states (S0, S0ix, S3/S4/S5) and ISClk behavior
- ✅ Retention clocks (PMC ART, RTC)
- ✅ S0ix entry/exit validation workflows
- ✅ PC10 achievement coordination with FV-PM-SOUTH
- ✅ Temperature-aware calibration
- ✅ PLL shutdown sequencing for Sx states
- ✅ S0ix stress testing
- ✅ Common power management issues and debug

**When to Use**: Load this skill when validating S0ix coordination, power state transitions, or PLL shutdown/wakeup behavior.

**Next Steps**: After validating power management, use `fv-isclk/debug` for failure analysis, or coordinate with **FV-PM-SOUTH** for comprehensive S0ix validation.
