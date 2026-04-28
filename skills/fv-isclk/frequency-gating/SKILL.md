# FV-ISClk Sub-Skill: Frequency Control & Clock Gating

**Owner**: Ooi, Ling Wei (lingweio)

**Parent Skill**: fv-isclk

**Focus**: Dynamic frequency control and clock gating validation

---

## Overview

This sub-skill provides specialized knowledge for validating ISClk frequency control and clock gating on NVL platforms. Frequency control enables dynamic scaling for power/performance optimization, while clock gating reduces power consumption by disabling clocks to idle blocks.

---

## Frequency Control

### Dynamic Frequency Scaling (DFS)

**Purpose**: Adjust clock frequencies based on workload and power requirements

**Frequency Control Mechanisms**:
1. **PLL Frequency Changes**: Reconfigure PLL to different frequency
2. **Divider Changes**: Adjust divider ratios (÷2, ÷4, ÷8)
3. **Source Switching**: Switch between high/low frequency sources

**Use Cases**:
- **Performance Mode**: Higher frequencies for demanding workloads
- **Power Saving Mode**: Lower frequencies when idle or light workload
- **Thermal Throttling**: Reduce frequency to lower temperature
- **Voltage Scaling**: Frequency coordinated with voltage (DVFS)

---

### Frequency Scaling Validation Workflows

#### Workflow 1: Validate Frequency Scaling Range

**Objective**: Verify supported frequency range for a clock

**HAS Query First**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the supported frequency range for [CLOCK_NAME]?"
```

**Steps**:
1. **Query HAS for Supported Frequencies**:
   - Minimum frequency
   - Maximum frequency
   - Discrete frequency steps or continuous range

2. **Test Frequency Points**:
   ```python
   # Example: Test fabric clock frequency scaling
   test_frequencies = [400, 600, 800, 1000]  # MHz, from HAS
   
   for freq in test_frequencies:
       print(f"\nTesting {freq} MHz...")
       
       # Configure frequency
       set_clock_frequency(target.isclk.fabric_clk, freq)
       
       # Wait for stabilization
       time.sleep(0.01)
       
       # Measure actual frequency
       measured = measure_frequency('fabric_clk')
       
       # Validate
       deviation = abs(measured - freq)
       if deviation < 5:  # 5 MHz tolerance
           print(f"✓ {freq} MHz validated (measured: {measured} MHz)")
       else:
           print(f"✗ {freq} MHz failed (measured: {measured} MHz, deviation: {deviation} MHz)")
   ```

3. **Document Supported Range**:
   - Minimum: 400 MHz
   - Maximum: 1000 MHz
   - Steps: 200 MHz increments

**Expected Outcome**: All advertised frequencies within range are achievable

---

#### Workflow 2: Validate Frequency Transition (Glitch-Free)

**Objective**: Ensure frequency changes occur without glitches

**Steps**:
1. **Query HAS for Transition Requirements**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What are the requirements for glitch-free frequency transitions?"
   ```

2. **Set Up Transition Test**:
   ```python
   # Start at initial frequency
   initial_freq = 800  # MHz
   target_freq = 1000  # MHz
   
   set_clock_frequency(target.isclk.fabric_clk, initial_freq)
   time.sleep(0.01)
   
   print(f"Starting frequency: {measure_frequency('fabric_clk')} MHz")
   ```

3. **Perform Frequency Transition**:
   ```python
   # Transition to target frequency
   set_clock_frequency(target.isclk.fabric_clk, target_freq)
   
   # Wait for transition to complete
   time.sleep(0.01)
   
   final_freq = measure_frequency('fabric_clk')
   print(f"Final frequency: {final_freq} MHz")
   ```

4. **Check for Glitches** (if oscilloscope available):
   - Capture clock signal during transition
   - Look for spurious pulses, runt pulses, or missing edges
   - Validate no glitches visible

5. **Validate Functionality After Transition**:
   ```python
   # Check that domain still operates correctly
   fabric_status = target.fabric.psf0.status.read()
   if fabric_status.operational:
       print("✓ Fabric operational after frequency change")
   else:
       print("✗ Fabric NOT operational after frequency change")
   ```

**Expected Outcome**: Frequency transitions smoothly without glitches, domain remains operational

---

#### Workflow 3: Stress Test Frequency Scaling

**Objective**: Validate frequent frequency changes don't cause issues

**Steps**:
1. **Define Frequency Pattern**:
   ```python
   freq_pattern = [800, 1000, 600, 1000, 400, 800]  # MHz
   iterations = 100
   ```

2. **Run Stress Test**:
   ```python
   failures = 0
   
   for i in range(iterations):
       for freq in freq_pattern:
           # Change frequency
           set_clock_frequency(target.isclk.fabric_clk, freq)
           time.sleep(0.001)  # Brief stabilization
           
           # Validate
           measured = measure_frequency('fabric_clk')
           if abs(measured - freq) > 5:
               failures += 1
               print(f"Iteration {i}, freq {freq} MHz: FAILED (measured {measured} MHz)")
   
   print(f"\nStress test complete: {failures} failures in {iterations * len(freq_pattern)} transitions")
   ```

3. **Monitor for Side Effects**:
   - Check for lock loss in source PLL
   - Check for domain operational failures
   - Check for error reporting (sTRC, Clock Monitor)

**Expected Outcome**: All transitions successful, no accumulated errors

---

## Clock Gating

### Clock Gating Overview

**Purpose**: Reduce power consumption by stopping clocks to idle blocks

**Gating Mechanisms**:
1. **Hardware-Automatic**: HW detects idle and gates clocks
2. **Firmware-Controlled**: PM firmware gates clocks based on power state
3. **Software-Requested**: Driver/OS requests clock gating

**Gating Granularity**:
- **Coarse-Grained**: Entire domain (e.g., all PCIe clocks)
- **Fine-Grained**: Individual blocks (e.g., PCIe Port 0 clock only)

**Power States and Gating**:
- **S0 (Active)**: Selective gating based on usage
- **S0ix (Modern Standby)**: Aggressive gating, most clocks gated
- **S3/S4/S5**: Nearly all clocks gated except retention clocks

---

### Clock Gating Validation Workflows

#### Workflow 1: Validate Clock Gating Enable/Disable

**Objective**: Verify clock can be gated and ungated correctly

**HAS Query First**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: Which clocks can be gated for [DOMAIN]?"
```

**Steps**:
1. **Query HAS for Gatable Clocks**: Get list of clocks that support gating

2. **Validate Clock Initially Running**:
   ```python
   # Check PCIe clock is running
   gating_status = target.isclk.pcie.ref_clk.gating_ctrl.read()
   if gating_status.gated:
       print("WARNING: Clock already gated, ungating first")
       target.isclk.pcie.ref_clk.gating_ctrl.gated.write(value=0)
       time.sleep(0.01)
   
   print("Clock running: confirmed")
   ```

3. **Gate the Clock**:
   ```python
   # Request clock gating
   target.isclk.pcie.ref_clk.gating_ctrl.gated.write(value=1)
   time.sleep(0.01)  # Wait for gating to take effect
   
   # Validate clock is gated
   gating_status = target.isclk.pcie.ref_clk.gating_ctrl.read()
   if gating_status.gated:
       print("✓ Clock successfully gated")
   else:
       print("✗ Clock gating FAILED")
   ```

4. **Validate Clock Stopped** (if measurement possible):
   ```python
   # Check frequency counter shows 0 MHz
   freq = measure_frequency('pcie_ref_clk')
   if freq < 1:  # Should be 0 or very low
       print("✓ Clock confirmed stopped")
   else:
       print(f"✗ Clock still running at {freq} MHz")
   ```

5. **Ungate the Clock**:
   ```python
   # Request clock ungating
   target.isclk.pcie.ref_clk.gating_ctrl.gated.write(value=0)
   time.sleep(0.01)  # Wait for ungating
   
   # Validate clock is running
   gating_status = target.isclk.pcie.ref_clk.gating_ctrl.read()
   if not gating_status.gated:
       print("✓ Clock successfully ungated")
   else:
       print("✗ Clock ungating FAILED")
   
   # Validate frequency restored
   freq = measure_frequency('pcie_ref_clk')
   if freq > 99:  # Should be ~100 MHz
       print(f"✓ Clock running at {freq} MHz")
   ```

**Expected Outcome**: Clock gates and ungates successfully, frequency reads correctly

---

#### Workflow 2: Validate Gating Timing (Before Domain Operations)

**Objective**: Ensure clocks are ungated before domain needs them

**Steps**:
1. **Query HAS for Ungating Timing**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the ungating time for [CLOCK_NAME]?"
   ```

2. **Gate Clock**:
   ```python
   target.isclk.pcie.ref_clk.gating_ctrl.gated.write(value=1)
   time.sleep(0.01)
   print("Clock gated")
   ```

3. **Trigger Domain Operation** (e.g., PCIe link training):
   ```python
   # PCIe link training requires ref clock
   # Ungating should happen automatically or via FW
   
   start_time = time.time()
   
   # Trigger PCIe link training
   target.pcie.port0.link_train.write(value=1)
   
   # Wait for ungating
   while target.isclk.pcie.ref_clk.gating_ctrl.gated.read():
       if (time.time() - start_time) > 0.1:  # 100ms timeout
           print("✗ Clock not ungated in time")
           break
       time.sleep(0.001)
   
   ungate_time = (time.time() - start_time) * 1000  # ms
   print(f"Clock ungated in {ungate_time:.1f} ms")
   ```

4. **Validate Domain Operation Succeeds**:
   ```python
   # Check PCIe link training succeeded
   link_status = target.pcie.port0.link_status.read()
   if link_status.trained:
       print("✓ PCIe link training succeeded (ungating was timely)")
   else:
       print("✗ PCIe link training failed (ungating too slow?)")
   ```

**Expected Outcome**: Clock ungates in time for domain operations

---

#### Workflow 3: Validate Power Savings from Gating

**Objective**: Measure power savings when clocks are gated

**Prerequisites**: Power measurement capability (TTK3 power monitor or platform sensors)

**Steps**:
1. **Baseline Power (All Clocks Running)**:
   ```python
   # Ensure all clocks ungated
   ungate_all_clocks()
   time.sleep(0.1)
   
   # Measure baseline power
   baseline_power = measure_platform_power()  # Watts
   print(f"Baseline power (all clocks running): {baseline_power} W")
   ```

2. **Gate Clocks for Idle Domain**:
   ```python
   # Example: Gate PCIe clocks (assume PCIe idle)
   target.isclk.pcie.ref_clk.gating_ctrl.gated.write(value=1)
   target.isclk.pcie.domain_clk.gating_ctrl.gated.write(value=1)
   time.sleep(0.1)
   
   # Measure power with gating
   gated_power = measure_platform_power()  # Watts
   print(f"Power with PCIe clocks gated: {gated_power} W")
   ```

3. **Calculate Power Savings**:
   ```python
   power_savings = baseline_power - gated_power
   savings_pct = (power_savings / baseline_power) * 100
   print(f"Power savings: {power_savings:.3f} W ({savings_pct:.1f}%)")
   ```

4. **Compare to Expected Savings** (from HAS or spec):
   ```python
   expected_savings = 0.5  # Watts, from HAS
   if power_savings >= expected_savings:
       print(f"✓ Power savings meet expectations ({power_savings:.3f} W >= {expected_savings} W)")
   else:
       print(f"✗ Power savings below expectations ({power_savings:.3f} W < {expected_savings} W)")
   ```

**Expected Outcome**: Measurable power savings when clocks are gated

---

## Coordinated Frequency + Gating

### Combined Frequency Scaling and Gating

Often frequency scaling and gating are coordinated:
- **Low Frequency + Selective Gating**: Power saving mode
- **High Frequency + No Gating**: Performance mode

**Validation Workflow**:
1. **Performance Mode**:
   - Set high frequency (e.g., 1000 MHz)
   - Ungate all clocks
   - Validate performance

2. **Power Saving Mode**:
   - Set low frequency (e.g., 400 MHz)
   - Gate idle clocks
   - Validate power savings

3. **Transitions**:
   - Performance → Power Saving: Scale down freq, then gate
   - Power Saving → Performance: Ungate first, then scale up freq

---

## Integration with PM Firmware

### Firmware-Controlled Gating

**Background**: PM firmware often controls clock gating based on power states

**Validation Approach**:
1. **Query FW for Gating Policy**:
   - Which clocks are gated in S0ix?
   - Which clocks remain active (retention clocks)?

2. **Trigger Power State Transition**:
   ```python
   # Example: Enter S0ix (coordinate with FV-PM-SOUTH)
   enter_s0ix()
   ```

3. **Validate Gating State**:
   ```python
   # Check expected clocks are gated
   gated_clocks = check_gating_status()
   print(f"Gated clocks in S0ix: {gated_clocks}")
   
   # Validate retention clocks still running
   pmc_clk_running = not target.isclk.pmc.art_clk.gating_ctrl.gated.read()
   if pmc_clk_running:
       print("✓ PMC ART clock retained in S0ix")
   else:
       print("✗ PMC ART clock gated (should be retained!)")
   ```

4. **Exit Power State and Validate Ungating**:
   ```python
   exit_s0ix()
   
   # Check clocks are ungated
   ungated_clocks = check_gating_status()
   print(f"Ungated clocks after S0ix exit: {ungated_clocks}")
   ```

**Integration with FV-PM-SOUTH**: Coordinate with FV-PM-SOUTH for S0ix testing

---

## Common Issues and Debug

### Issue 1: Clock Fails to Gate

**Symptoms**: Gating request accepted but clock still running

**Debug Steps**:
1. Check if domain is truly idle (may have activity preventing gating)
2. Check for FW override (FW may force clock on)
3. Check HW automatic ungating conditions
4. Validate gating control register write succeeded

---

### Issue 2: Clock Fails to Ungate in Time

**Symptoms**: Domain operation fails because clock not available

**Debug Steps**:
1. Check ungating request was sent
2. Check ungating latency (may exceed requirements)
3. Check if PLL needs to relock after gating (adds delay)
4. Validate ungating sequence (FW coordination)

---

### Issue 3: Frequency Scaling Causes Glitches

**Symptoms**: Clock glitches observed during frequency transitions

**Debug Steps**:
1. Validate HAS-recommended transition sequence
2. Check if glitch-free mux/divider is used
3. Check for PLL lock loss during transition
4. Use oscilloscope to capture and analyze glitches

---

## HAS References

**Primary HAS Document**: `Chap44_0_NVL_PCH_Internal_Clocks.html`

**Key Sections**:
- Frequency scaling ranges and configurations
- Clock gating architecture and controls
- Transition requirements (glitch-free)
- Power state gating policies

**Query HAS Before Validation**: Always verify frequency ranges, gating capabilities, and transition requirements from HAS

---

## Summary

This sub-skill covers:
- ✅ Dynamic frequency scaling (DFS)
- ✅ Frequency scaling validation workflows
- ✅ Glitch-free transition validation
- ✅ Clock gating enable/disable
- ✅ Gating timing validation
- ✅ Power savings measurement
- ✅ Coordinated frequency + gating
- ✅ PM firmware integration
- ✅ Common issues and debug

**When to Use**: Load this skill when validating frequency control, clock gating, or power-saving mechanisms.

**Next Steps**: After validating frequency and gating, use `fv-isclk/power` for S0ix coordination, or `fv-isclk/debug` for failure analysis.
