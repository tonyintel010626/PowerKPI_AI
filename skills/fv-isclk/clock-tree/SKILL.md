# FV-ISClk Sub-Skill: Clock Tree & Distribution

**Owner**: Ooi, Ling Wei (lingweio)

**Parent Skill**: fv-isclk

**Focus**: Clock tree topology, distribution hierarchy, and clock integrity validation

---

## Overview

This sub-skill provides specialized knowledge for validating the ISClk clock tree structure and distribution on NVL platforms. The clock tree is a hierarchical system that distributes clocks from sources (PLLs, XTAL, RTC) to all platform domains with proper timing, skew, and jitter characteristics.

---

## Clock Tree Architecture

### Hierarchical Structure

```
Clock Sources (Root)
├── PLLs
│   ├── Main PLL (1000 MHz)
│   ├── HP PLL (2000+ MHz)
│   ├── FilterPLL (38.4 MHz)
│   └── Display/Type-C/D2D PLLs
├── XTAL (Crystal Oscillator - 38.4 MHz)
└── RTC (Real-Time Clock - 32.768 kHz)
    │
    ├── Clock Dividers (÷2, ÷4, ÷8, etc.)
    ├── Clock Muxes (Source Selection)
    └── Clock Buffers (Distribution)
        │
        ├── Fabric/Interconnect Domain
        │   ├── PSF0 (Primary Scalable Fabric) ← o_ck_1ghz_iosf
        │   └── ICC (Interconnect) ← o_ck_400mhz_iosf
        │
        ├── Compute Domain
        │   ├── CPU Clocks
        │   ├── GPU Clocks
        │   └── NPU Clocks
        │
        ├── PCIe Domain
        │   └── PCIe PHY ← o_ck_ref_pcie (100 MHz)
        │
        ├── Display Domain
        │   └── Display/Thunderbolt ← o_ck_ddi (810/1250 MHz)
        │
        ├── PMC Domain
        │   └── ART/PMSYNC ← o_ck_xtal_pmc (38.4 MHz)
        │
        └── Peripheral Domains
            ├── LPSS (I2C, I3C, SPI, UART)
            ├── THC (Touch Host Controller)
            └── USB
```

---

## Example ISClk Clocks (from NVL HAS)

### Fabric/Interconnect Clocks

#### **o_ck_1ghz_iosf**
- **Frequency**: 1000 MHz
- **Source**: Fabric PLL (Main PLL)
- **Destination**: PSF0 (Primary Scalable Fabric)
- **Purpose**: High-speed fabric interconnect for SoC/PCH communication
- **Divider**: Typically no division from Main PLL
- **Validation**: Verify frequency accuracy, check fabric operations

#### **o_ck_400mhz_iosf**
- **Frequency**: 400 MHz
- **Source**: SoC PLL
- **Destination**: PSF/ICC (Primary Scalable Fabric / Interconnect)
- **Purpose**: Fabric and interconnect operations
- **Divider**: Typically ÷2 or ÷4 from source PLL
- **Validation**: Verify divider ratio, check ICC operations

---

### Reference Clocks

#### **o_ck_xtal_compute**
- **Frequency**: 38.4 MHz
- **Source**: FilterPLL (from XTAL)
- **Destination**: Display PLLs, SA (System Agent) PLLs
- **Purpose**: Clean reference clock for downstream PLLs
- **Validation**: Verify jitter specs, check downstream PLL lock quality

#### **o_ck_ref_pcie**
- **Frequency**: 100 MHz
- **Source**: REF PLL
- **Destination**: PCIe PHY
- **Purpose**: PCIe reference clock (specification requirement)
- **SSC**: Must support ±0.5% SSC for PCIe compliance
- **Validation**: Verify 100 MHz ± tolerance, validate SSC if enabled, check PCIe link training

#### **o_ck_xtal_pmc**
- **Frequency**: 38.4 MHz
- **Source**: FilterPLL (from XTAL)
- **Destination**: PMC ART (Always Running Timer), PMSYNC
- **Purpose**: PMC time base, S0ix timing reference
- **Criticality**: Must remain active in S0ix
- **Validation**: Verify always-on behavior, check S0ix timing accuracy

---

### Domain-Specific Clocks

#### **o_ck_ddi**
- **Frequency**: 810 MHz or 1250 MHz (configurable)
- **Source**: DDIPLL (Display PLL)
- **Destination**: Display interfaces, Thunderbolt
- **Purpose**: Display data transmission, Thunderbolt signaling
- **Mode Switching**: Can switch between 810 MHz and 1250 MHz based on display mode
- **Validation**: Verify mode switching, check display timing, validate Thunderbolt compliance

---

## Clock Tree Components

### 1. Clock Dividers

**Purpose**: Divide clock frequencies to derive lower frequencies

**Common Ratios**: ÷2, ÷4, ÷8, ÷16

**Configuration**:
```python
# Example: Configure divider for fabric clock
target.isclk.fabric_clk.divider.write(value=4)  # Divide by 4

# Read back divider setting
divider = target.isclk.fabric_clk.divider.read()
print(f"Fabric clock divider: ÷{divider}")
```

**Validation**:
1. Query HAS for supported divider ratios
2. Configure divider
3. Validate output frequency = input frequency / divider
4. Check for glitches during divider changes

---

### 2. Clock Muxes

**Purpose**: Select clock source from multiple options

**Example Mux Selections**:
- PCIe clock source: REF PLL or external clock
- Display clock source: DDIPLL or backup source
- PMC clock source: FilterPLL or RTC

**Configuration**:
```python
# Example: Select PCIe clock source
target.isclk.pcie_clk.source_select.write(value=0)  # 0 = REF PLL

# Read back source selection
source = target.isclk.pcie_clk.source_select.read()
print(f"PCIe clock source: {source}")
```

**Validation**:
1. Query HAS for supported clock sources
2. Configure mux selection
3. Validate correct source is selected
4. Test switching between sources (if supported)

---

### 3. Clock Buffers

**Purpose**: Distribute clocks to multiple destinations without degradation

**Characteristics**:
- Low skew across outputs
- Low jitter introduction
- Fanout capability

**Validation**:
- Measure skew between buffer outputs (if equipment available)
- Validate signal integrity at all destinations

---

## Clock Tree Validation Workflows

### Workflow 1: Enumerate Clock Tree

**Objective**: Identify all clock sources and destinations for a domain

**HAS Query First**:
```
"Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the clock tree hierarchy for the [DOMAIN] domain?"
```

**Steps**:
1. **Query HAS for Domain Clocks**: Get list of clocks required for domain

2. **Enumerate Sources**:
   ```python
   domain_clocks = {}
   
   # Example: Fabric domain
   fabric_clocks = {
       'o_ck_1ghz_iosf': target.isclk.fabric.clk_1ghz_iosf,
       'o_ck_400mhz_iosf': target.isclk.fabric.clk_400mhz_iosf
   }
   
   for clk_name, clk_reg in fabric_clocks.items():
       source = clk_reg.source.read()
       freq = clk_reg.frequency.read()
       enabled = clk_reg.enabled.read()
       print(f"{clk_name}: {freq} MHz, source={source}, enabled={enabled}")
   ```

3. **Trace to Root**: Follow clock back to PLL/XTAL/RTC source

4. **Document Hierarchy**:
   ```
   o_ck_1ghz_iosf (1000 MHz)
     ← Fabric PLL (Main PLL) (1000 MHz)
       ← XTAL (38.4 MHz) → FilterPLL → Main PLL VCO → Main PLL output
   ```

5. **Validate Against HAS**: Ensure topology matches HAS documentation

**Expected Outcome**: Complete clock tree enumeration for domain

---

### Workflow 2: Validate Clock Frequency

**Objective**: Verify clock frequencies match HAS specifications

**Steps**:
1. **Query HAS for Expected Frequency**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the expected frequency for o_ck_1ghz_iosf?"
   ```

2. **Read Clock Configuration**:
   ```python
   clk_config = target.isclk.fabric.clk_1ghz_iosf.read()
   configured_freq = clk_config.freq_mhz
   print(f"Configured frequency: {configured_freq} MHz")
   ```

3. **Measure Actual Frequency** (if tools available):
   - Use on-chip frequency counter (if available)
   - Use lab equipment (oscilloscope, frequency counter)
   
   ```python
   # Example: On-chip frequency counter
   target.isclk.freq_counter.select.write(value='o_ck_1ghz_iosf')
   target.isclk.freq_counter.start.write(value=1)
   time.sleep(0.1)  # Measure for 100ms
   measured_freq = target.isclk.freq_counter.result.read()
   print(f"Measured frequency: {measured_freq} MHz")
   ```

4. **Calculate Deviation**:
   ```python
   expected_freq = 1000  # MHz from HAS
   deviation_ppm = ((measured_freq - expected_freq) / expected_freq) * 1e6
   print(f"Frequency deviation: {deviation_ppm:.1f} ppm")
   
   tolerance_ppm = 100  # Query HAS for spec
   if abs(deviation_ppm) > tolerance_ppm:
       print(f"ERROR: Frequency deviation exceeds tolerance ({tolerance_ppm} ppm)")
   ```

5. **Account for SSC** (if enabled):
   - SSC modulates frequency by ±0.5% typical
   - Measure frequency over time to capture modulation range

**Expected Outcome**: Frequency within HAS-specified tolerance

---

### Workflow 3: Validate Clock Divider Ratios

**Objective**: Verify clock dividers produce correct output frequencies

**Steps**:
1. **Query HAS for Divider Configuration**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the divider ratio for deriving o_ck_400mhz_iosf from SoC PLL?"
   ```

2. **Read Divider Setting**:
   ```python
   divider = target.isclk.fabric.clk_400mhz_iosf.divider.read()
   print(f"Divider ratio: ÷{divider}")
   ```

3. **Read Source and Output Frequencies**:
   ```python
   source_freq = target.isclk.soc_pll.freq_mhz.read()
   output_freq = target.isclk.fabric.clk_400mhz_iosf.freq_mhz.read()
   print(f"Source: {source_freq} MHz → Output: {output_freq} MHz")
   ```

4. **Validate Divider Math**:
   ```python
   expected_output = source_freq / divider
   if abs(output_freq - expected_output) > 1:  # 1 MHz tolerance
       print(f"ERROR: Divider output incorrect. Expected {expected_output} MHz, got {output_freq} MHz")
   else:
       print(f"SUCCESS: Divider output correct ({output_freq} MHz)")
   ```

5. **Test Divider Changes** (if configurable):
   ```python
   # Try different divider ratios
   for div in [2, 4, 8]:
       target.isclk.fabric.clk_400mhz_iosf.divider.write(value=div)
       time.sleep(0.01)  # Wait for stabilization
       output_freq = measure_frequency('o_ck_400mhz_iosf')
       expected = source_freq / div
       print(f"Divider ÷{div}: {output_freq} MHz (expected {expected} MHz)")
   ```

**Expected Outcome**: Divider produces correct output frequency based on ratio

---

### Workflow 4: Validate Clock Source Selection (Mux)

**Objective**: Verify clock mux selects correct source

**Steps**:
1. **Query HAS for Supported Sources**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What are the supported clock sources for o_ck_ref_pcie?"
   ```

2. **Read Current Source Selection**:
   ```python
   source_mux = target.isclk.pcie.ref_clk.source_select.read()
   print(f"Current source: {source_mux}")  # e.g., 0 = REF PLL, 1 = External
   ```

3. **Validate Source is Correct**:
   ```python
   expected_source = 0  # REF PLL (from HAS or platform config)
   if source_mux != expected_source:
       print(f"WARNING: Unexpected source selected. Expected {expected_source}, got {source_mux}")
   ```

4. **Test Source Switching** (if supported and safe):
   ```python
   # Switch to alternate source
   target.isclk.pcie.ref_clk.source_select.write(value=1)  # External clock
   time.sleep(0.01)
   
   # Validate switch
   new_source = target.isclk.pcie.ref_clk.source_select.read()
   print(f"Switched to source: {new_source}")
   
   # Validate clock still present
   clk_present = target.isclk.pcie.ref_clk.status.present.read()
   if not clk_present:
       print("ERROR: Clock not present after source switch")
   
   # Switch back to original
   target.isclk.pcie.ref_clk.source_select.write(value=0)
   ```

**Expected Outcome**: Correct source selected, switching works without glitches

---

### Workflow 5: Measure Clock Skew and Jitter

**Objective**: Validate clock timing characteristics (requires lab equipment)

**Prerequisites**: Oscilloscope or logic analyzer with skew/jitter measurement capability

**Skew Measurement**:
1. **Query HAS for Skew Specs**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the maximum clock skew between PSF clock domains?"
   ```

2. **Probe Multiple Clock Signals**: Use oscilloscope to capture multiple clocks simultaneously

3. **Measure Skew**: Calculate time difference between clock edges
   - Typical spec: < 100 ps skew between domains

4. **Compare to Spec**:
   ```python
   measured_skew_ps = 75  # From oscilloscope measurement
   max_skew_ps = 100  # From HAS
   
   if measured_skew_ps > max_skew_ps:
       print(f"ERROR: Skew exceeds spec ({measured_skew_ps} ps > {max_skew_ps} ps)")
   else:
       print(f"SUCCESS: Skew within spec ({measured_skew_ps} ps < {max_skew_ps} ps)")
   ```

**Jitter Measurement**:
1. **Query HAS for Jitter Specs**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the maximum jitter for PCIe reference clock?"
   ```

2. **Capture Clock Signal**: Use oscilloscope in persistence mode or jitter analysis mode

3. **Measure Jitter**:
   - Period jitter: Variation in clock period
   - Cycle-to-cycle jitter: Variation between adjacent periods
   - Typical PCIe spec: < 2 ps RMS jitter

4. **Compare to Spec**:
   ```python
   measured_jitter_ps = 1.5  # From oscilloscope
   max_jitter_ps = 2.0  # From HAS or PCIe spec
   
   if measured_jitter_ps > max_jitter_ps:
       print(f"ERROR: Jitter exceeds spec ({measured_jitter_ps} ps > {max_jitter_ps} ps)")
   ```

**Note**: Skew and jitter measurements require specialized lab equipment and are typically performed during platform validation or debug, not routine testing.

---

### Workflow 6: Domain-Specific Clock Validation

**Objective**: Validate all clocks required for a specific domain

**Example: PCIe Domain**

**Steps**:
1. **Query HAS for PCIe Clock Requirements**:
   ```
   "Reference Chap44_0_NVL_PCH_Internal_Clocks: What clocks are required for PCIe operation?"
   ```

2. **Expected Result**: o_ck_ref_pcie (100 MHz) from REF PLL

3. **Validate Clock Present**:
   ```python
   pcie_clk = target.isclk.pcie.ref_clk.status.read()
   if not pcie_clk.present:
       print("ERROR: PCIe reference clock not present")
       return False
   ```

4. **Validate Frequency**:
   ```python
   freq = measure_frequency('o_ck_ref_pcie')
   if abs(freq - 100.0) > 0.1:  # 100 kHz tolerance
       print(f"ERROR: PCIe reference frequency incorrect ({freq} MHz)")
   ```

5. **Validate SSC (if enabled)**:
   ```python
   ssc_status = target.isclk.ref_pll.ssc_enable.read()
   if ssc_status:
       print("SSC enabled for PCIe compliance")
       # Validate SSC modulation is ±0.5%
   ```

6. **Validate PCIe Link Training**:
   ```python
   # Check if PCIe link trains successfully (indicates good clock)
   pcie_link_status = target.pcie.port0.link_status.read()
   if pcie_link_status.trained:
       print("SUCCESS: PCIe link trained (clock validated)")
   else:
       print("ERROR: PCIe link failed to train (possible clock issue)")
   ```

**Expected Outcome**: All required clocks present and correct, domain operates successfully

---

## Integration with Other Skills

### With fv-isclk/pll

After validating PLLs lock correctly (using `fv-isclk/pll`), use this skill to validate downstream clock distribution from PLLs.

### With fv-isclk/frequency-gating

Clock tree topology affects which clocks can be gated. Use `fv-isclk/frequency-gating` to validate gating behavior for specific clocks in the tree.

### With fv-isclk/registers

Use `fv-isclk/registers` for detailed register-level access to clock tree control registers (dividers, muxes, enables).

### With fv-isclk/debug

If clock distribution issues occur (e.g., domain not receiving clock), use `fv-isclk/debug` for root cause analysis.

---

## Common Clock Tree Issues and Debug

### Issue 1: Clock Not Present at Destination

**Symptoms**: Domain reports no clock, operations fail

**Debug Steps**:
1. Trace clock backwards from destination to source
2. Check each stage: buffer enabled? mux selected correctly? divider configured?
3. Verify source PLL is locked
4. Check clock gating status (may be gated)

**Example Debug**:
```python
# Check PCIe clock not present
print("Tracing o_ck_ref_pcie backwards...")

# Step 1: Check clock at destination
dest_clk = target.pcie.ref_clk.status.present.read()
print(f"Clock at PCIe PHY: {dest_clk}")

# Step 2: Check clock at source (REF PLL)
src_clk = target.isclk.ref_pll.status.lock.read()
print(f"REF PLL locked: {src_clk}")

# Step 3: Check clock path (gating, mux)
gating = target.isclk.pcie.ref_clk.gating_ctrl.gated.read()
print(f"Clock gated: {gating}")

mux = target.isclk.pcie.ref_clk.source_select.read()
print(f"Source mux: {mux}")
```

---

### Issue 2: Frequency Incorrect

**Symptoms**: Measured frequency doesn't match expected

**Debug Steps**:
1. Verify source PLL frequency is correct
2. Check divider settings (may be misconfigured)
3. Account for SSC (modulates frequency)
4. Validate measurement method (ensure counter is accurate)

---

### Issue 3: Clock Glitches During Transitions

**Symptoms**: Glitches observed when changing frequency or gating state

**Debug Steps**:
1. Query HAS for proper transition sequence
2. Validate glitch-free mux/divider switching is used
3. Check if clock tree components support glitch-free transitions
4. Use oscilloscope to capture glitches for analysis

---

## Clock Tree Visualization

**Placeholder**: Clock tree visualization tools to be added by owner

**Desired Features**:
- Graphical representation of clock tree hierarchy
- Highlight clock paths from source to destination
- Annotate with frequencies, dividers, mux selections
- Color-code by domain

---

## HAS References

**Primary HAS Document**: `Chap44_0_NVL_PCH_Internal_Clocks.html`

**Key Sections**:
- Clock tree topology and hierarchy
- Clock source to destination mappings
- Divider and mux configurations
- Skew and jitter specifications
- Domain-specific clock requirements

**Secondary HAS Document**: `Chap05_NVL_PCD_H_Clock_Domains.html`

**Key Sections**:
- Per-domain clock requirements (PCH-H specifics)

**Query HAS Before Validation**: Always verify clock tree topology and specifications from HAS

---

## Summary

This sub-skill covers:
- ✅ Clock tree hierarchical architecture
- ✅ Example ISClk clocks (o_ck_1ghz_iosf, o_ck_ref_pcie, etc.)
- ✅ Clock tree components (dividers, muxes, buffers)
- ✅ Clock tree enumeration workflows
- ✅ Frequency validation workflows
- ✅ Divider and mux validation
- ✅ Skew and jitter measurement (with lab equipment)
- ✅ Domain-specific clock validation
- ✅ Common clock tree issues and debug

**When to Use**: Load this skill when validating clock distribution, verifying clock tree topology, or debugging clock availability issues.

**Next Steps**: After validating clock tree, use `fv-isclk/frequency-gating` to validate dynamic frequency control and clock gating, or `fv-isclk/power` for power state coordination.
