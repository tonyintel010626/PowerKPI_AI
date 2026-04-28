# FV-ISClk Skill

**Owner**: Ooi, Ling Wei (lingweio)

**Domain**: ISClk (Interconnect Clock) Functional Validation

**Platforms**: NVL PCH-H, NVL PCH-S, NVL SoC

---

## Overview

The **FV-ISClk Skill** provides comprehensive knowledge and workflows for validating Intel's **ISClk (Interconnect Clock)** domain on NVL platforms. ISClk is the central clocking IP for NVL PCH/SoC, responsible for clock generation, distribution, and management across all platform domains.

This skill serves as the knowledge base for the FV-ISClk agent, providing:
- ISClk architecture understanding
- Validation workflows and best practices
- Integration with hardware validation tools (TTK3, PythonSV)
- Coordination with other FV agents
- Failure analysis and debug procedures

---

## ISClk Architecture Summary

### What is ISClk?

ISClk (Interconnect Clock) is the foundational clocking infrastructure for NVL platforms, providing:

1. **Clock Generation**: Multiple PLLs for different frequency domains
2. **Clock Distribution**: Hierarchical clock tree to all platform subsystems
3. **Clock Management**: Dynamic frequency control, clock gating, power management
4. **Error Handling**: sTRC and Clock Monitor integration for fault detection

### Key Components

#### 1. PLLs (Phase-Locked Loops)

ISClk includes multiple PLLs for different domains:

- **Main PLL**: Primary clock source for fabric and interconnect
- **HP PLL** (High-Performance PLL): High-frequency compute clocks
- **Overclocking PLL**: Performance boost scenarios
- **Display PLL**: Display interface clocking
- **Type-C PLL**: Type-C/Thunderbolt clocking
- **D2D PLL** (Die-to-Die): Multi-die interconnect clocking
- **FilterPLL**: Clean reference clocks for downstream PLLs

Each PLL has:
- Configurable frequency ranges
- Lock detection and status reporting
- SSC (Spread Spectrum Clocking) support
- Voltage/temperature stability requirements

#### 2. Clock Tree

Hierarchical clock distribution from sources (PLLs, XTAL, RTC) to all platform domains:

**Clock Sources**:
- PLLs (Main, HP, OC, Display, Type-C, D2D, FilterPLL)
- XTAL (Crystal oscillator - 38.4 MHz typical)
- RTC (Real-Time Clock - 32.768 kHz)

**Clock Distribution Domains**:
- **Fabric/Interconnect**: PSF (Primary Scalable Fabric), ICC (Interconnect)
- **Compute**: CPU, GPU, NPU domains
- **PCIe**: PCIe PHY reference clocks (100 MHz)
- **Display**: Display/Thunderbolt interfaces
- **PMC**: Power Management Controller, Always Running Timer (ART)
- **LPSS**: Low Power Subsystem (I2C, I3C, SPI, UART)
- **THC**: Touch Host Controller

**Clock Tree Features**:
- Clock dividers for frequency scaling
- Clock muxes for source selection
- Clock buffers for distribution
- Skew and jitter management

#### 3. Frequency Control

Dynamic frequency management capabilities:

- **Frequency Scaling**: Change clock frequencies based on workload/power requirements
- **Clock Division**: Programmable divider ratios
- **Frequency Modulation**: SSC for EMI reduction
- **Transition Management**: Glitch-free frequency changes

#### 4. Clock Gating

Power-aware clock gating for power savings:

- **Dynamic Gating**: Gate clocks when blocks are idle
- **Power State Coordination**: Gate/ungate based on power states (S0ix, Sx)
- **FW Coordination**: PM firmware controls gating sequences
- **Ungating Timing**: Ensure clocks available before operations

#### 5. Error Handling

Fault detection and reporting mechanisms:

- **sTRC (System Trace Controller)**: System-level error logging and trace
- **Clock Monitor**: Detects clock failures (loss, frequency errors)
- **Error Reporting**: Status registers, interrupts, telemetry
- **Recovery Mechanisms**: PLL relock, clock source switching

---

## Supported Platforms

### NVL PCH-H (Platform Controller Hub - High Performance)

- **Target Market**: High-performance desktop, workstation
- **Clock Tree**: Full feature set, all PLLs available
- **Key Differences**: Enhanced clocking for high-performance I/O

### NVL PCH-S (Platform Controller Hub - Standard)

- **Target Market**: Standard desktop, mainstream
- **Clock Tree**: Standard feature set
- **Key Differences**: Subset of PCH-H clocking features

### NVL SoC (System-on-Chip)

- **Target Market**: Mobile, integrated platforms
- **Clock Tree**: SoC-integrated clocking
- **Key Differences**: Integrated with CPU/GPU clocking, power-optimized

---

## Sub-Skills Structure

This skill has **7 specialized sub-skills** for focused validation tasks:

### 1. **fv-isclk/pll** - PLL Configuration & Validation

**Focus**: PLL-specific validation workflows

**Load when**:
- Validating PLL configuration and locking behavior
- Testing PLL stability across voltage/temperature corners
- Configuring and validating SSC (Spread Spectrum Clocking)
- Analyzing PLL lock failures
- Validating multi-PLL interactions and dependencies

**Key Topics**:
- PLL lock time requirements
- Frequency selection and configuration
- SSC modulation validation
- Voltage/temperature corner testing
- PLL error conditions and recovery

**HAS Reference**: `Chap44_0_NVL_PCH_Internal_Clocks.html` (PLL specifications)

---

### 2. **fv-isclk/clock-tree** - Clock Tree & Distribution

**Focus**: Clock distribution and integrity validation

**Load when**:
- Validating clock tree topology and hierarchy
- Verifying clock source selection (PLLs, XTAL, RTC)
- Measuring clock skew and jitter
- Validating clock dividers and mux configurations
- Testing domain-specific clock distribution

**Key Topics**:
- Hierarchical clock tree structure
- Clock source to destination mapping
- Skew and jitter specifications
- Clock divider ratios
- Domain-specific clock requirements

**Example Clocks**:
- `o_ck_1ghz_iosf` (Fabric PLL → PSF0)
- `o_ck_400mhz_iosf` (SoC PLL → PSF/ICC)
- `o_ck_ref_pcie` (REF PLL → PCIe PHY)

**HAS References**: 
- `Chap44_0_NVL_PCH_Internal_Clocks.html` (clock tree)
- `Chap05_NVL_PCD_H_Clock_Domains.html` (domain specifics)

---

### 3. **fv-isclk/frequency-gating** - Frequency Control & Clock Gating

**Focus**: Dynamic frequency management and clock gating validation

**Load when**:
- Validating dynamic frequency scaling
- Testing clock gating sequences
- Verifying power-aware gating coordination
- Analyzing frequency transition behavior
- Testing gating/ungating timing

**Key Topics**:
- Frequency scaling workflows
- Clock gating enable/disable sequences
- Power state coordination (with PM FW)
- Transition validation (frequency changes, gating state changes)
- Glitch-free operation

**HAS Reference**: `Chap44_0_NVL_PCH_Internal_Clocks.html` (gating architecture)

---

### 4. **fv-isclk/power** - Power Management Integration

**Focus**: ISClk-PMC coordination and low-power modes

**Load when**:
- Validating S0ix entry/exit clock coordination
- Testing PLL shutdown/wakeup sequences
- Verifying temperature-aware calibration
- Analyzing clock behavior in low-power states
- Coordinating with FV-PM-SOUTH on power issues

**Key Topics**:
- S0ix clock gating sequences
- PLL shutdown/wakeup timing
- Retention clocks (PMC, RTC)
- Temperature-aware clock adjustments
- Power state transition validation

**Integration**: Works closely with **FV-PM-SOUTH** for S0ix coordination

**HAS Reference**: `Chap44_0_NVL_PCH_Internal_Clocks.html` (power management)

---

### 5. **fv-isclk/registers** - Register Map & Error Handling

**Focus**: Register-level configuration and error monitoring

**Load when**:
- Configuring ISClk via register access
- Reading PLL/clock status registers
- Analyzing error status and reporting
- Validating sTRC and Clock Monitor integration
- Testing register access patterns

**Key Topics**:
- PLL configuration/status registers
- Clock control registers (dividers, muxes, gating)
- Error status and reporting registers
- sTRC integration
- Clock Monitor error detection
- PythonSV namednodes for register access

**HAS References**:
- `Chap44_0_NVL_PCH_Internal_Clocks.html` (register maps)
- `NVL-PCD-S Feature Guide - sTRC_CM.html` (error handling)

---

### 6. **fv-isclk/platform** - Platform-Specific Configurations

**Focus**: Platform variant differences and configurations

**Load when**:
- Validating platform-specific clock configurations
- Performing platform bring-up
- Checking platform BOM (Bill of Materials) requirements
- Comparing cross-platform clock behavior
- Debugging platform-specific issues

**Key Topics**:
- NVL PCH-H specific configurations
- NVL PCH-S specific configurations
- NVL SoC integrated clocking
- Crystal oscillator specifications
- Platform prerequisites and BOM

**HAS Reference**: `Chap05_NVL_PCD_H_Clock_Domains.html` (platform specifics)

---

### 7. **fv-isclk/debug** - Failure Analysis & Debug Flows

**Focus**: Triage, root cause analysis, and failure correlation

**Load when**:
- Analyzing NGA test failures
- Performing root cause analysis of clock issues
- Correlating with HSDES sightings
- Debugging boot hangs related to clocks
- Applying known errata and workarounds

**Key Topics**:
- Common failure signatures (PLL lock failures, gating stuck, frequency mismatches)
- Debug workflows and triage procedures
- HSDES sighting search and correlation
- Known errata and workarounds
- Integration with FV_Debugger_V1 for NGA triage
- Boot-time clock debugging (UART logs, POST codes)

**Integration**: Works with **FV_Debugger_V1**, **TTK3-UART**, **TTK3-POSTCODE**

**HAS Reference**: `NVL-PCD-S Feature Guide - sTRC_CM.html` (error codes)

---

## HAS-First Policy

**CRITICAL**: Always query Co-Design for ISClk HAS documentation before making technical decisions.

### Primary HAS Documents

1. **`Chap44_0_NVL_PCH_Internal_Clocks.html`**
   - Primary ISClk architecture reference
   - PLL configurations and specifications
   - Clock tree topology
   - Register maps
   - Gating architecture

2. **`NVL-PCD-S Feature Guide - sTRC_CM.html`**
   - System Trace Controller (sTRC) integration
   - Clock Monitor error detection
   - Error reporting mechanisms
   - Debug and telemetry

3. **`Chap05_NVL_PCD_H_Clock_Domains.html`**
   - Per-domain clock requirements
   - Platform-specific configurations
   - PCH-H domain details

### How to Query HAS

Use the `browsermcp` tool to navigate to Co-Design and query HAS:

**Example Queries**:
```
"Reference NVL ISClk HAS Chap44_0_NVL_PCH_Internal_Clocks: What are the PLL locking requirements for Main PLL?"

"Reference Chap44_0_NVL_PCH_Internal_Clocks: What is the clock tree hierarchy for the PCIe domain?"

"Reference NVL sTRC_CM Feature Guide: How does Clock Monitor detect PLL lock failures?"
```

**Workflow**:
1. Navigate to https://chat.co-design.intel.com/chat
2. Submit HAS query
3. Wait for response with HAS references
4. Apply HAS guidance to validation workflow
5. Cite HAS sections when explaining clock behavior

---

## Integration with Other Agents

The FV-ISClk skill works within a multi-agent ecosystem:

### FV Agents

#### **FV-PM-SOUTH** - Power Management South
- **Use Case**: S0ix coordination, PC10 tracking
- **Integration**: Coordinate on clock gating for S0ix entry/exit
- **Example**: "Validating ISClk gating sequences while FV-PM-SOUTH monitors PMC"

#### **FV_Debugger_V1** - General Debug Orchestrator
- **Use Case**: NGA failure triage, HSDES correlation
- **Integration**: Receive clock-related failures from FV_Debugger_V1 for specialized analysis
- **Example**: "FV_Debugger_V1 identified PLL lock failure, performing ISClk-specific root cause analysis"

#### **FV-LPSS** - LPSS Validation
- **Use Case**: Cross-domain clock validation (LPSS uses ISClk sources)
- **Integration**: Validate ISClk provides correct clocks to LPSS domain
- **Example**: "LPSS I2C failure may be due to ISClk source, coordinating validation"

#### **FV-THC** - Touch Host Controller Validation
- **Use Case**: THC clock validation (THC depends on ISClk)
- **Integration**: Validate ISClk provides correct clocks to THC domain
- **Example**: "Validating ISClk clock sources to THC domain"

### TTK3 Sub-Agents (Hardware Validation)

#### **TTK3-POWER** - Power Control
- **Use Case**: Power cycling for clock state transitions
- **Example**: "Using TTK3-POWER to power cycle platform for cold boot PLL validation"

#### **TTK3-UART** - Serial Debug
- **Use Case**: Capture boot logs for clock initialization sequences
- **Example**: "Capturing BIOS boot logs via TTK3-UART, parsing for PLL lock messages"

#### **TTK3-GPIO** - Platform State Monitoring
- **Use Case**: Monitor platform power states, sleep states
- **Example**: "Monitoring SLP_S0# signal via TTK3-GPIO during S0ix transition"

#### **TTK3-POSTCODE** - Boot Sequence Tracking
- **Use Case**: Track boot sequence via POST codes
- **Example**: "Capturing POST codes via TTK3-POSTCODE to identify boot hang location"

### Other Agents

- **UART-MONITOR**: Real-time boot log analysis
- **NGA agents**: Test execution and failure tracking
- **HSDES**: Sighting queries for known issues
- **GENI**: Fallback HAS queries
- **AXON**: Historical validation data

---

## PythonSV Test Framework

ISClk validation uses the PythonSV framework for register access and test automation.

### Base Class Pattern

Create `isclk_common.py` as the base class for ISClk tests:

```python
# isclk_common.py (to be created by team)
class ISClkCommon:
    """Base class for ISClk validation tests"""
    
    def __init__(self, target):
        self.target = target
        # Initialize namednodes for ISClk register access
        
    def read_pll_status(self, pll_name):
        """Read PLL lock status"""
        # Implementation: read PLL status register
        pass
        
    def configure_pll(self, pll_name, freq_mhz, ssc_enable=False):
        """Configure PLL with frequency and SSC settings"""
        # Implementation: write PLL config registers
        pass
        
    def validate_clock_tree(self, domain):
        """Validate clock tree for specific domain"""
        # Implementation: enumerate and validate clock sources
        pass
        
    def check_gating_state(self, clock_name):
        """Check clock gating state"""
        # Implementation: read gating control registers
        pass
        
    def measure_frequency(self, clock_name):
        """Measure clock frequency (if counter available)"""
        # Implementation: use frequency counter or telemetry
        pass
```

### Host-Target Pairing

Use the standard PythonSV naming convention:
- **Host**: `pgXXwvawXXXX` (e.g., pg01wvaw0001)
- **Target**: `pgXXwvawXXXXtg` (e.g., pg01wvaw0001tg)

### Namednodes for Register Access

Use PythonSV namednodes to access ISClk registers:

```python
# Example: Read Main PLL status
pll_status = target.isclk.main_pll.status.read()
if pll_status.lock == 1:
    print("Main PLL locked")
    print(f"Lock time: {pll_status.lock_time_us} µs")
else:
    print("Main PLL NOT locked")
    
# Example: Configure clock divider
target.isclk.fabric_clk.divider.write(value=4)  # Divide by 4

# Example: Check gating state
gating_state = target.isclk.pcie_clk.gating_ctrl.read()
if gating_state.gated == 1:
    print("PCIe clock is gated")
```

### Test Execution

Execute PythonSV tests via bash:

```bash
# Navigate to test directory
cd /path/to/isclk/tests

# Run PythonSV test
python test_pll_lock.py --target pg01wvaw0001tg --pll main

# Parse results
grep -i "PASS\|FAIL" test_results.log
```

---

## Example ISClk Clocks (from NVL HAS)

These concrete clock examples help with validation scenarios:

### Fabric/Interconnect Clocks

**o_ck_1ghz_iosf**
- Frequency: 1000 MHz
- Source: Fabric PLL
- Destination: PSF0 (Primary Scalable Fabric)
- Use: High-speed fabric interconnect

**o_ck_400mhz_iosf**
- Frequency: 400 MHz
- Source: SoC PLL
- Destination: PSF/ICC (Interconnect)
- Use: Fabric and interconnect operations

### Reference Clocks

**o_ck_xtal_compute**
- Frequency: 38.4 MHz
- Source: FilterPLL
- Destination: Display/SA PLLs
- Use: Reference clock for downstream PLLs

**o_ck_ref_pcie**
- Frequency: 100 MHz
- Source: REF PLL
- Destination: PCIe PHY
- Use: PCIe reference clock (compliance requirement)

**o_ck_xtal_pmc**
- Frequency: 38.4 MHz
- Source: FilterPLL
- Destination: ART/PMSYNC (PMC Always Running Timer)
- Use: PMC time base, S0ix timing

### Domain-Specific Clocks

**o_ck_ddi**
- Frequency: 810 MHz / 1250 MHz (configurable)
- Source: DDIPLL
- Destination: Thunderbolt/Display interfaces
- Use: Display and Thunderbolt data transmission

---

## Common Validation Workflows

Quick reference for typical ISClk validation scenarios:

### 1. PLL Lock Validation
1. Query HAS for PLL requirements
2. Load `fv-isclk/pll` skill
3. Configure PLL via PythonSV
4. Validate lock time < HAS spec
5. Test stability over time
6. Test across VT corners

### 2. Clock Tree Integrity
1. Query HAS for clock tree topology
2. Load `fv-isclk/clock-tree` skill
3. Enumerate clock sources and destinations
4. Validate divider ratios
5. Measure frequency accuracy
6. Check skew/jitter (if tools available)

### 3. S0ix Coordination
1. Coordinate with FV-PM-SOUTH
2. Load `fv-isclk/power` skill
3. Validate clock gating sequences for S0ix entry
4. Check PLL shutdown timing
5. Validate S0ix exit and PLL wakeup
6. Verify PC10 achievement

### 4. Boot-Time Clock Debug
1. Use TTK3-UART for log capture
2. Use TTK3-POSTCODE for boot tracking
3. Load `fv-isclk/debug` skill
4. Parse logs for clock init errors
5. Identify failed clocks causing boot hang
6. Suggest remediation

### 5. NGA Failure Triage
1. Coordinate with FV_Debugger_V1
2. Review failure signature for clock keywords
3. Query HSDES for similar issues
4. Load appropriate ISClk sub-skill
5. Perform root cause analysis
6. Report findings and remediation

---

## Tool Placeholders (For Future)

**NOTE**: This section will be populated with team-specific tools as they become available.

### Clock Measurement Tools
- [To be added: Oscilloscope/logic analyzer integrations]
- [To be added: Frequency counter automation]
- [To be added: Spectrum analyzer for SSC validation]

### Custom Scripts
- [To be added: ISClk validation scripts repository]
- [To be added: PythonSV ISClk modules]
- [To be added: Clock tree visualization tools]

### Lab Equipment
- [To be added: Automated measurement tools]
- [To be added: Lab equipment integration]

**Owner (lingweio)**: Add team-specific tools as they become available.

---

## Quick Reference

### Key Commands

**Load Sub-Skills**:
```
skill("fv-isclk/pll")           # PLL validation
skill("fv-isclk/clock-tree")    # Clock tree validation
skill("fv-isclk/frequency-gating")  # Frequency/gating validation
skill("fv-isclk/power")         # Power management
skill("fv-isclk/registers")     # Register access
skill("fv-isclk/platform")      # Platform specifics
skill("fv-isclk/debug")         # Debug and triage
```

**Query HAS via Co-Design**:
```
Navigate to: https://chat.co-design.intel.com/chat
Query: "Reference NVL ISClk HAS Chap44_0: [YOUR QUESTION]"
```

**Execute PythonSV Test**:
```bash
python test_isclk.py --target pg01wvaw0001tg
```

### Key HAS Documents
- `Chap44_0_NVL_PCH_Internal_Clocks.html` (primary)
- `NVL-PCD-S Feature Guide - sTRC_CM.html` (errors)
- `Chap05_NVL_PCD_H_Clock_Domains.html` (domains)

### Key Agents
- **FV-PM-SOUTH**: S0ix coordination
- **FV_Debugger_V1**: NGA triage
- **FV-LPSS/FV-THC**: Cross-domain validation
- **TTK3-***: Hardware validation

---

## Owner Information

**Name**: Ooi, Ling Wei  
**IDSID**: lingweio  
**Domain**: ISClk (Interconnect Clock) Functional Validation  
**Platforms**: NVL PCH-H, NVL PCH-S, NVL SoC

For questions, contributions, or tool additions, contact the owner.

---

**This skill provides the foundation for ISClk functional validation. Load specialized sub-skills for focused validation tasks.**
