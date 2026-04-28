# FV-ISClk Platform Sub-Skill

**Owner**: Ooi, Ling Wei (lingweio)  
**Parent Skill**: `fv-isclk`  
**Agent**: `FV-ISClk`

---

## Overview

This sub-skill provides platform-specific ISClk knowledge for NVL platforms: **NVL PCH-H**, **NVL PCH-S**, and **NVL SoC**. It covers platform-specific clock tree differences, PLL configurations, crystal oscillator requirements, BOM (Bill of Materials) specifications, platform prerequisites for validation, and platform-specific known issues.

**Key Focus Areas**:
- Platform comparison (PCH-H vs PCH-S vs SoC)
- Platform-specific clock trees and PLL configurations
- Crystal oscillator specifications per platform
- Platform BOM requirements (clock components)
- Platform prerequisites for ISClk validation
- Platform-specific errata and workarounds
- Platform detection and identification

---

## HAS-First Policy

**ALWAYS query Co-Design** before making platform-specific assumptions.

**Primary HAS Documents**:
- `Chap44_0_NVL_PCH_Internal_Clocks.html` - ISClk platform specifications
- `Chap05_NVL_PCD_H_Clock_Domains.html` - PCH-H specific clock domains
- `NVL-PCD-S Feature Guide - sTRC_CM.html` - PCH-S specific features

**Co-Design Query Examples**:
```
"Show me the ISClk differences between NVL PCH-H and PCH-S from Chap44_0"
"What are the crystal oscillator requirements for NVL SoC?"
"Show me the platform-specific PLL configurations for NVL PCH-H"
"What are the ISClk BOM requirements for NVL PCH-S?"
```

---

## Supported Platforms

### Platform Overview

| Platform | Description | ISClk Architecture | Key Differentiators |
|----------|-------------|-------------------|---------------------|
| **NVL PCH-H** | High-performance desktop/workstation PCH | Full ISClk IP with all PLLs | Maximum PLL count, highest frequency support, OC PLL support |
| **NVL PCH-S** | Standard desktop/mobile PCH | Standard ISClk IP | Balanced PLL configuration, standard frequency ranges |
| **NVL SoC** | System-on-Chip integrated design | Integrated ISClk with shared resources | Shared PLLs with CPU/GPU, power-optimized configurations |

### Platform Detection

Use PythonSV to detect platform at runtime:

```python
from namednodes import *

# Read platform ID register (example)
platform_id = pch.platform_id.read()

# Decode platform
if platform_id == 0x5100:
    platform = "NVL PCH-H"
elif platform_id == 0x5200:
    platform = "NVL PCH-S"
elif platform_id == 0x5300:
    platform = "NVL SoC"
else:
    platform = f"Unknown (0x{platform_id:04x})"

print(f"Detected platform: {platform}")
```

---

## NVL PCH-H Platform

### Overview
- **Target Market**: High-performance desktop, workstation
- **ISClk Features**: Full feature set, all PLLs enabled
- **Max Frequency**: 1250 MHz (DDIPLL)
- **Overclocking Support**: Yes (OC PLL)
- **PCIe Support**: Gen5 (requires high-speed reference clocks)

### PCH-H Clock Tree

**Key Clocks**:
- `o_ck_1ghz_iosf` - 1000 MHz (Main PLL → PSF0)
- `o_ck_400mhz_iosf` - 400 MHz (Main PLL → PSF/ICC)
- `o_ck_ref_pcie_gen5` - 100 MHz (REF PLL → PCIe Gen5 PHY)
- `o_ck_ddi_1250` - 1250 MHz (DDIPLL → Thunderbolt/Display)
- `o_ck_oc_fabric` - Variable (OC PLL → Fabric overclocking)
- `o_ck_xtal_pmc` - 38.4 MHz (FilterPLL → PMC ART)

**Clock Tree Diagram**:
```
FilterPLL (38.4 MHz Crystal)
  ├── o_ck_xtal_compute (38.4 MHz) → Display/SA PLLs
  ├── o_ck_xtal_pmc (38.4 MHz) → PMC ART/PMSYNC
  └── o_ck_xtal_rtc (32.768 kHz) → RTC

Main PLL (1600 MHz)
  ├── /1 → o_ck_1ghz_iosf (1000 MHz) → PSF0
  ├── /4 → o_ck_400mhz_iosf (400 MHz) → PSF/ICC
  └── /2 → o_ck_800mhz_fabric (800 MHz) → Fabric

HP PLL (1200 MHz)
  ├── /1 → o_ck_1200mhz_compute (1200 MHz) → Compute
  └── /3 → o_ck_400mhz_compute (400 MHz) → Compute aux

OC PLL (Variable 1000-2000 MHz)
  └── /1 → o_ck_oc_fabric (Variable) → Overclocked Fabric

DDIPLL (1250 MHz)
  ├── /1 → o_ck_ddi_1250 (1250 MHz) → Thunderbolt
  └── /2 → o_ck_ddi_625 (625 MHz) → Display aux

Type-C PLL (1200 MHz)
  └── /1 → o_ck_typec_1200 (1200 MHz) → Type-C PHY

D2D PLL (1000 MHz)
  └── /1 → o_ck_d2d_1000 (1000 MHz) → Die-to-Die link

REF PLL (100 MHz)
  └── /1 → o_ck_ref_pcie_gen5 (100 MHz) → PCIe Gen5 PHY
```

### PCH-H PLL Configuration

| PLL | Frequency Range | SSC Support | Use Case |
|-----|----------------|-------------|----------|
| Main PLL | 1000-1600 MHz | Yes (center/down) | Fabric, IOSF |
| HP PLL | 1200-1600 MHz | Yes (center) | Compute, high-perf domains |
| OC PLL | 1000-2000 MHz | No | Overclocking scenarios |
| DDIPLL | 810/1250 MHz | No | Display, Thunderbolt |
| Type-C PLL | 1200 MHz | No | Type-C PHY |
| D2D PLL | 1000 MHz | No | Die-to-Die interconnect |
| FilterPLL | 38.4 MHz | No | Crystal filtering, reference |

### PCH-H Crystal Oscillator

**Specification**:
- **Frequency**: 38.4 MHz
- **Tolerance**: ±50 ppm
- **Stability**: ±20 ppm over temperature (-40°C to +105°C)
- **Load Capacitance**: 12 pF
- **Startup Time**: < 10 ms

**BOM Requirements**:
- Crystal: 38.4 MHz, 12 pF load, ±50 ppm
- Load capacitors: 2x 22 pF (18 pF series)
- PCB trace: Differential, controlled impedance (100Ω ±10%)

### PCH-H Prerequisites

**Hardware**:
- PCH-H silicon (stepping B0 or later recommended)
- 38.4 MHz crystal oscillator (verified BOM)
- Proper power rails (VccIO, VccCore, VccPLL)
- PCIe clock generator (for Gen5 support)

**Software/Firmware**:
- BIOS/IFWI with ISClk initialization
- PMC firmware with ISClk power management support
- OS drivers with ISClk awareness (if applicable)

**Test Environment**:
- TTK3 hardware for low-level access
- Oscilloscope for clock measurement (1 GHz+ bandwidth)
- Power supply with voltage margining capability

### PCH-H Known Issues

**Issue 1: OC PLL Lock Failure at High Frequencies**
- **Symptom**: OC PLL fails to lock above 1800 MHz
- **Workaround**: Increase VccPLL voltage by 50 mV
- **HSDES**: [Link to sighting]

**Issue 2: DDIPLL SSC Interference**
- **Symptom**: Display artifacts when SSC enabled on Main PLL
- **Workaround**: Disable Main PLL SSC when DDIPLL is active
- **HSDES**: [Link to sighting]

---

## NVL PCH-S Platform

### Overview
- **Target Market**: Standard desktop, mobile
- **ISClk Features**: Standard feature set, OC PLL disabled
- **Max Frequency**: 1200 MHz
- **Overclocking Support**: No
- **PCIe Support**: Gen4

### PCH-S Clock Tree

**Key Clocks**:
- `o_ck_1ghz_iosf` - 1000 MHz (Main PLL → PSF0)
- `o_ck_400mhz_iosf` - 400 MHz (Main PLL → PSF/ICC)
- `o_ck_ref_pcie_gen4` - 100 MHz (REF PLL → PCIe Gen4 PHY)
- `o_ck_ddi_810` - 810 MHz (DDIPLL → Display)
- `o_ck_xtal_pmc` - 38.4 MHz (FilterPLL → PMC ART)

**Clock Tree Diagram**:
```
FilterPLL (38.4 MHz Crystal)
  ├── o_ck_xtal_compute (38.4 MHz) → Display/SA PLLs
  ├── o_ck_xtal_pmc (38.4 MHz) → PMC ART/PMSYNC
  └── o_ck_xtal_rtc (32.768 kHz) → RTC

Main PLL (1600 MHz)
  ├── /1 → o_ck_1ghz_iosf (1000 MHz) → PSF0
  ├── /4 → o_ck_400mhz_iosf (400 MHz) → PSF/ICC
  └── /2 → o_ck_800mhz_fabric (800 MHz) → Fabric

HP PLL (1200 MHz)
  └── /1 → o_ck_1200mhz_compute (1200 MHz) → Compute

DDIPLL (810 MHz)
  └── /1 → o_ck_ddi_810 (810 MHz) → Display

Type-C PLL (1200 MHz)
  └── /1 → o_ck_typec_1200 (1200 MHz) → Type-C PHY

REF PLL (100 MHz)
  └── /1 → o_ck_ref_pcie_gen4 (100 MHz) → PCIe Gen4 PHY
```

### PCH-S PLL Configuration

| PLL | Frequency Range | SSC Support | Use Case |
|-----|----------------|-------------|----------|
| Main PLL | 1000-1600 MHz | Yes (center/down) | Fabric, IOSF |
| HP PLL | 1200 MHz | Yes (center) | Compute |
| DDIPLL | 810 MHz | No | Display |
| Type-C PLL | 1200 MHz | No | Type-C PHY |
| FilterPLL | 38.4 MHz | No | Crystal filtering, reference |

**Note**: PCH-S does NOT include OC PLL or D2D PLL.

### PCH-S Crystal Oscillator

**Specification** (same as PCH-H):
- **Frequency**: 38.4 MHz
- **Tolerance**: ±50 ppm
- **Stability**: ±20 ppm over temperature (-40°C to +105°C)
- **Load Capacitance**: 12 pF
- **Startup Time**: < 10 ms

**BOM Requirements** (same as PCH-H):
- Crystal: 38.4 MHz, 12 pF load, ±50 ppm
- Load capacitors: 2x 22 pF (18 pF series)
- PCB trace: Differential, controlled impedance (100Ω ±10%)

### PCH-S Prerequisites

**Hardware**:
- PCH-S silicon (stepping A0 or later)
- 38.4 MHz crystal oscillator (verified BOM)
- Proper power rails (VccIO, VccCore, VccPLL)
- PCIe clock generator (for Gen4 support)

**Software/Firmware**:
- BIOS/IFWI with ISClk initialization
- PMC firmware with ISClk power management support
- OS drivers with ISClk awareness (if applicable)

**Test Environment**:
- TTK3 hardware for low-level access
- Oscilloscope for clock measurement (1 GHz+ bandwidth)
- Power supply with voltage margining capability

### PCH-S Known Issues

**Issue 1: Main PLL SSC Modulation Interference**
- **Symptom**: Fabric timing violations when SSC center spread enabled
- **Workaround**: Use down spread instead of center spread
- **HSDES**: [Link to sighting]

**Issue 2: Type-C PLL Lock Delay**
- **Symptom**: Type-C PLL takes > 500 ms to lock on cold boot
- **Workaround**: Increase lock timeout to 1 second
- **HSDES**: [Link to sighting]

---

## NVL SoC Platform

### Overview
- **Target Market**: Mobile, low-power devices
- **ISClk Features**: Integrated with CPU/GPU clocking, power-optimized
- **Max Frequency**: 1000 MHz
- **Overclocking Support**: No
- **PCIe Support**: Gen4
- **Key Difference**: Shared PLL resources with CPU/GPU domains

### SoC Clock Tree

**Key Clocks**:
- `o_ck_1ghz_iosf` - 1000 MHz (Shared PLL → PSF0)
- `o_ck_400mhz_iosf` - 400 MHz (Shared PLL → PSF/ICC)
- `o_ck_ref_pcie_gen4` - 100 MHz (Shared REF PLL → PCIe Gen4 PHY)
- `o_ck_ddi_810` - 810 MHz (Shared DDIPLL → Display)
- `o_ck_xtal_pmc` - 38.4 MHz (FilterPLL → PMC ART)

**Clock Tree Diagram**:
```
FilterPLL (38.4 MHz Crystal)
  ├── o_ck_xtal_compute (38.4 MHz) → CPU/GPU/Display PLLs
  ├── o_ck_xtal_pmc (38.4 MHz) → PMC ART/PMSYNC
  └── o_ck_xtal_rtc (32.768 kHz) → RTC

Shared PLL (1600 MHz) - shared with CPU
  ├── /1 → o_ck_1ghz_iosf (1000 MHz) → PSF0
  ├── /4 → o_ck_400mhz_iosf (400 MHz) → PSF/ICC
  ├── /2 → o_ck_800mhz_fabric (800 MHz) → Fabric
  └── [CPU/GPU domains]

Shared DDIPLL (810 MHz) - shared with GPU
  ├── /1 → o_ck_ddi_810 (810 MHz) → Display
  └── [GPU domains]

Type-C PLL (1200 MHz)
  └── /1 → o_ck_typec_1200 (1200 MHz) → Type-C PHY

Shared REF PLL (100 MHz) - shared with CPU PCIe
  └── /1 → o_ck_ref_pcie_gen4 (100 MHz) → PCIe Gen4 PHY
```

### SoC PLL Configuration

| PLL | Frequency Range | SSC Support | Use Case | Sharing |
|-----|----------------|-------------|----------|---------|
| Shared PLL | 1000-1600 MHz | Yes (down) | Fabric, IOSF, CPU | Shared with CPU |
| Shared DDIPLL | 810 MHz | No | Display, GPU | Shared with GPU |
| Type-C PLL | 1200 MHz | No | Type-C PHY | Dedicated |
| FilterPLL | 38.4 MHz | No | Crystal filtering, reference | Dedicated |

**Note**: SoC does NOT include HP PLL, OC PLL, or D2D PLL. Main PLL and DDIPLL are shared with CPU/GPU.

### SoC Crystal Oscillator

**Specification** (lower power than PCH):
- **Frequency**: 38.4 MHz
- **Tolerance**: ±50 ppm
- **Stability**: ±30 ppm over temperature (-20°C to +85°C) - mobile temperature range
- **Load Capacitance**: 10 pF (lower power)
- **Startup Time**: < 5 ms (optimized for fast boot)

**BOM Requirements**:
- Crystal: 38.4 MHz, 10 pF load, ±50 ppm, low-power variant
- Load capacitors: 2x 18 pF (12 pF series)
- PCB trace: Differential, controlled impedance (100Ω ±10%)

### SoC Prerequisites

**Hardware**:
- NVL SoC silicon (stepping A0 or later)
- Low-power 38.4 MHz crystal oscillator (verified BOM)
- Proper power rails (VccIO, VccCore, VccPLL with dynamic voltage scaling)
- Integrated PCIe clock (no external generator needed)

**Software/Firmware**:
- SoC BIOS/IFWI with integrated ISClk/CPU/GPU clocking
- PMC firmware with aggressive power management
- OS drivers with SoC power management awareness (P-states, C-states coordination)

**Test Environment**:
- TTK3 hardware for low-level access
- Oscilloscope for clock measurement (1 GHz+ bandwidth)
- Power analyzer for power measurement (ISClk + CPU/GPU coordination)
- Battery simulator for mobile validation

### SoC Known Issues

**Issue 1: Shared PLL Contention with CPU Frequency Scaling**
- **Symptom**: ISClk IOSF frequency glitches when CPU changes P-state
- **Workaround**: Coordinate ISClk divider changes with CPU DVFS (Dynamic Voltage and Frequency Scaling)
- **HSDES**: [Link to sighting]

**Issue 2: S0ix Resume Delay Due to Shared DDIPLL**
- **Symptom**: Display does not restore immediately on S0ix exit (1-2 second delay)
- **Workaround**: Pre-lock DDIPLL before GPU resume (requires GPU coordination)
- **HSDES**: [Link to sighting]

**Issue 3: Type-C PLL Power Consumption in S0ix**
- **Symptom**: Type-C PLL remains active in S0ix, consuming 10 mW
- **Workaround**: Shutdown Type-C PLL if no Type-C devices connected (requires runtime detection)
- **HSDES**: [Link to sighting]

---

## Platform Comparison Table

### Clock Tree Differences

| Clock | PCH-H | PCH-S | SoC | Notes |
|-------|-------|-------|-----|-------|
| o_ck_1ghz_iosf | ✓ (Main PLL) | ✓ (Main PLL) | ✓ (Shared PLL) | SoC shared with CPU |
| o_ck_400mhz_iosf | ✓ | ✓ | ✓ | All platforms |
| o_ck_oc_fabric | ✓ (OC PLL) | ✗ | ✗ | PCH-H only |
| o_ck_ddi_1250 | ✓ (DDIPLL) | ✗ | ✗ | PCH-H only (Thunderbolt) |
| o_ck_ddi_810 | ✓ (DDIPLL) | ✓ (DDIPLL) | ✓ (Shared DDIPLL) | SoC shared with GPU |
| o_ck_d2d_1000 | ✓ (D2D PLL) | ✗ | ✗ | PCH-H only |
| o_ck_ref_pcie_gen5 | ✓ (REF PLL) | ✗ | ✗ | PCH-H only (Gen5) |
| o_ck_ref_pcie_gen4 | ✓ (REF PLL) | ✓ (REF PLL) | ✓ (Shared REF PLL) | All platforms (Gen4) |
| o_ck_xtal_pmc | ✓ | ✓ | ✓ | All platforms (retention) |

### PLL Differences

| PLL | PCH-H | PCH-S | SoC | Notes |
|-----|-------|-------|-----|-------|
| Main PLL | ✓ | ✓ | ✗ | SoC uses Shared PLL |
| HP PLL | ✓ | ✓ | ✗ | Not needed in SoC |
| OC PLL | ✓ | ✗ | ✗ | PCH-H only (overclocking) |
| DDIPLL | ✓ (1250 MHz) | ✓ (810 MHz) | ✗ | SoC uses Shared DDIPLL |
| Type-C PLL | ✓ | ✓ | ✓ | All platforms |
| D2D PLL | ✓ | ✗ | ✗ | PCH-H only |
| FilterPLL | ✓ | ✓ | ✓ | All platforms |
| Shared PLL | ✗ | ✗ | ✓ | SoC only (CPU shared) |
| Shared DDIPLL | ✗ | ✗ | ✓ | SoC only (GPU shared) |

### Feature Differences

| Feature | PCH-H | PCH-S | SoC |
|---------|-------|-------|-----|
| Max Frequency | 1250 MHz | 1200 MHz | 1000 MHz |
| Overclocking | ✓ | ✗ | ✗ |
| PCIe Gen5 | ✓ | ✗ | ✗ |
| PCIe Gen4 | ✓ | ✓ | ✓ |
| Thunderbolt | ✓ | ✗ | ✗ |
| CPU/GPU Sharing | ✗ | ✗ | ✓ |
| SSC Support | ✓ (all modes) | ✓ (limited) | ✓ (down only) |
| Power Optimization | Standard | Standard | Aggressive |
| S0ix Support | ✓ | ✓ | ✓ (optimized) |

---

## Platform-Specific Validation Workflows

### Workflow 1: Platform Detection and Feature Enumeration

**Objective**: Detect platform and enumerate available ISClk features.

**Steps**:
1. Read platform ID register
2. Enumerate available PLLs
3. Enumerate available clocks
4. Check for platform-specific features (OC, D2D, shared PLLs)
5. Log platform capabilities

**Example Code**:
```python
from namednodes import *

# Step 1: Detect platform
platform_id = pch.platform_id.read()
if platform_id == 0x5100:
    platform = "NVL PCH-H"
    expected_plls = ["Main", "HP", "OC", "DDIPLL", "Type-C", "D2D", "FilterPLL"]
elif platform_id == 0x5200:
    platform = "NVL PCH-S"
    expected_plls = ["Main", "HP", "DDIPLL", "Type-C", "FilterPLL"]
elif platform_id == 0x5300:
    platform = "NVL SoC"
    expected_plls = ["Shared", "Shared DDIPLL", "Type-C", "FilterPLL"]
else:
    platform = f"Unknown (0x{platform_id:04x})"
    expected_plls = []

print(f"Platform: {platform}")

# Step 2: Enumerate PLLs
print("Available PLLs:")
for pll_name in expected_plls:
    # Read PLL enable register (if accessible)
    print(f"  - {pll_name}")

# Step 3: Enumerate clocks (platform-specific)
# See fv-isclk/clock-tree for full enumeration workflow

# Step 4: Check platform-specific features
if platform == "NVL PCH-H":
    print("Platform features:")
    print("  - Overclocking support: Yes")
    print("  - PCIe Gen5: Yes")
    print("  - Thunderbolt: Yes")
elif platform == "NVL SoC":
    print("Platform features:")
    print("  - CPU/GPU PLL sharing: Yes")
    print("  - Power optimization: Aggressive")
```

### Workflow 2: Platform-Specific Crystal Verification

**Objective**: Verify crystal oscillator meets platform requirements.

**Steps**:
1. Detect platform
2. Read crystal frequency from FilterPLL
3. Measure crystal startup time
4. Verify crystal stability (requires oscilloscope)
5. Check BOM compliance

**Example Code**:
```python
from namednodes import *
import time

# Step 1: Detect platform
platform_id = pch.platform_id.read()
if platform_id == 0x5100:
    platform = "NVL PCH-H"
    expected_freq = 38.4  # MHz
    expected_load = 12    # pF
elif platform_id == 0x5200:
    platform = "NVL PCH-S"
    expected_freq = 38.4  # MHz
    expected_load = 12    # pF
elif platform_id == 0x5300:
    platform = "NVL SoC"
    expected_freq = 38.4  # MHz
    expected_load = 10    # pF (lower power)
else:
    print("Unknown platform, cannot verify crystal")
    exit()

print(f"Platform: {platform}")
print(f"Expected crystal: {expected_freq} MHz, {expected_load} pF load")

# Step 2: Read crystal frequency from FilterPLL
# This assumes FilterPLL has a frequency readback register
xtal_freq = pch.isclk.filterpll.freq_readback.read()
print(f"Crystal frequency: {xtal_freq} MHz")

if abs(xtal_freq - expected_freq) < 0.1:
    print("Crystal frequency: PASS")
else:
    print("Crystal frequency: FAIL (out of tolerance)")

# Step 3: Measure crystal startup time
# Reset FilterPLL and measure lock time
pch.isclk.filterpll.enable.write(0x0)  # Disable
time.sleep(0.01)  # Wait for shutdown
start = time.time()
pch.isclk.filterpll.enable.write(0x1)  # Enable
# Wait for lock
while time.time() - start < 0.1:  # 100ms timeout
    lock_status = pch.isclk.filterpll.lock_status.read()
    if (lock_status & 0x1) == 0x1:
        startup_time = (time.time() - start) * 1000  # ms
        print(f"Crystal startup time: {startup_time:.2f} ms")
        if platform == "NVL SoC" and startup_time < 5:
            print("Startup time: PASS (< 5 ms for SoC)")
        elif startup_time < 10:
            print("Startup time: PASS (< 10 ms)")
        else:
            print("Startup time: FAIL (too slow)")
        break
    time.sleep(0.001)
else:
    print("FilterPLL failed to lock (crystal issue)")

# Step 4: Measure stability (requires oscilloscope)
print("Crystal stability verification requires oscilloscope measurement")
print("  - Connect probe to crystal output")
print("  - Measure frequency drift over temperature range")
print(f"  - Expected stability: ±20 ppm for PCH, ±30 ppm for SoC")
```

### Workflow 3: Platform-Specific PLL Configuration Test

**Objective**: Test platform-specific PLL configurations (e.g., OC PLL on PCH-H, Shared PLL on SoC).

**Steps**:
1. Detect platform
2. Configure platform-specific PLL (OC PLL for PCH-H, Shared PLL for SoC)
3. Verify PLL lock
4. Measure output frequency
5. Test platform-specific use case

**Example Code (PCH-H OC PLL)**:
```python
from namednodes import *
import time

# Step 1: Detect platform
platform_id = pch.platform_id.read()
if platform_id != 0x5100:
    print("OC PLL only available on PCH-H, skipping test")
    exit()

print("Platform: NVL PCH-H")

# Step 2: Configure OC PLL for 1800 MHz
pch.isclk.oc_pll.freq_sel.write(0x8)  # 0x8 = 1800 MHz (consult HAS)
pch.isclk.oc_pll.voltage_ctrl.write(0x2)  # Increase voltage for stability
pch.isclk.oc_pll.enable.write(0x1)

# Step 3: Wait for lock
start = time.time()
while time.time() - start < 1.0:
    lock_status = pch.isclk.oc_pll.lock_status.read()
    if (lock_status & 0x1) == 0x1:
        print("OC PLL locked at 1800 MHz")
        break
    time.sleep(0.01)
else:
    print("OC PLL failed to lock")
    exit()

# Step 4: Measure frequency (requires clock measurement tool)
print("Measure OC PLL output frequency with oscilloscope")

# Step 5: Test overclocking use case (route OC PLL to fabric)
pch.isclk.clk_mux.fabric.write(0x2)  # 0x2 = OC PLL (consult HAS)
print("Fabric clocked from OC PLL at 1800 MHz")
# Run fabric stress test here
```

**Example Code (SoC Shared PLL Coordination)**:
```python
from namednodes import *

# Step 1: Detect platform
platform_id = pch.platform_id.read()
if platform_id != 0x5300:
    print("Shared PLL only available on SoC, skipping test")
    exit()

print("Platform: NVL SoC")

# Step 2: Read current Shared PLL configuration (set by CPU)
shared_pll_freq = pch.isclk.shared_pll.freq_sel.read()
print(f"Shared PLL frequency (CPU-controlled): {shared_pll_freq}")

# Step 3: Verify ISClk dividers are coordinated with CPU
iosf_div = pch.isclk.clk_div.iosf.read()
print(f"IOSF divider: {iosf_div}")

# WARNING: Do NOT change Shared PLL frequency (controlled by CPU)
# Only adjust ISClk dividers to maintain correct IOSF frequency
print("SoC Shared PLL is CPU-controlled, ISClk must coordinate via dividers")

# Step 5: Test coordination (CPU frequency scaling)
print("To test CPU coordination:")
print("  1. Trigger CPU P-state change (e.g., load stress)")
print("  2. Monitor Shared PLL frequency change")
print("  3. Verify ISClk dividers adjust automatically")
print("  4. Verify IOSF frequency remains stable")
```

---

## Integration with Other Skills

### With `fv-isclk/pll`
- **pll** skill uses platform-specific PLL configurations from this skill
- **Workflow**: Detect platform first, then load platform-specific PLL parameters

### With `fv-isclk/clock-tree`
- **clock-tree** skill uses platform-specific clock tree from this skill
- **Workflow**: Enumerate clocks based on platform (PCH-H has more clocks than SoC)

### With `fv-isclk/debug`
- **debug** skill uses platform-specific known issues from this skill
- **Workflow**: When debugging, check platform-specific errata first

### With Other FV Agents
- **FV-PM-SOUTH**: Platform-specific S0ix coordination (SoC more aggressive)
- **FV_Debugger_V1**: Platform detection for HSDES sighting correlation

---

## Summary Checklist

When validating ISClk on a specific platform, ensure:
- [ ] Query HAS via Co-Design for platform-specific specifications
- [ ] Detect platform at runtime (PCH-H, PCH-S, or SoC)
- [ ] Enumerate platform-specific PLLs and clocks
- [ ] Verify crystal oscillator meets platform BOM requirements
- [ ] Test platform-specific features (OC PLL, Shared PLL, etc.)
- [ ] Check platform-specific known issues and workarounds
- [ ] Coordinate with CPU/GPU if on SoC platform
- [ ] Adjust validation expectations based on platform capabilities
- [ ] Document platform-specific findings in test reports

---

**End of fv-isclk/platform sub-skill**
