---
name: fv-gbe/simics
description: >-
  GbE Simics pre-silicon validation — models, transactors, per-platform setup, SW-CI integration,
  and debug workflows for Intel I219 GbE on Intel Client SoC Virtual Platforms (NVL, PTL, LNL, MTL, ARL).
disable: false
---

# GbE Simics Pre-Silicon Validation

> **Purpose**: Entry point for GbE pre-silicon validation on Intel Simics Virtual Platforms.
> Covers GbE model architecture, transactor configuration, validation procedures, and
> debug workflows.
>
> **Scope**: This sub-skill covers **PRE-SILICON Simics/VP** concepts only.
> For post-silicon GbE validation, use the other `fv-gbe/*` sub-skills (registers, phy-bringup, traffic, power, debug, driver).

---

## Table of Contents

1. [What is Simics Pre-Si Validation](#1-what-is-simics-pre-si-validation)
2. [GbE in the Virtual Platform](#2-gbe-in-the-virtual-platform)
3. [GbE Model Architecture](#3-gbe-model-architecture)
4. [Per-Platform Setup](#4-per-platform-setup)
5. [GbE Validation Scenarios](#5-gbe-validation-scenarios)
6. [PythonSV in Simics](#6-pythonsv-in-simics)
7. [SW-CI Integration](#7-sw-ci-integration)
8. [Debug Workflows](#8-debug-workflows)
9. [Known Simics Limitations](#9-known-simics-limitations)

---

## 1. What is Simics Pre-Si Validation

**Simics** is Intel's full-system simulator that runs **unmodified production BIOS, drivers, and OS** on a functional model of the SoC. Pre-silicon validation on Simics allows:

- Early driver/firmware validation before silicon arrives
- BIOS programming verification
- Power state transition testing
- Basic functional validation of GbE IP

### What Simics CAN Validate for GbE

| Category | Simics Capability |
|----------|-------------------|
| **PCI Enumeration** | ✅ Full — BDF, BAR allocation, VID/DID |
| **Register Access** | ✅ Full — MMIO reads/writes, config space |
| **Driver Load** | ✅ Full — Windows/Linux driver binding |
| **Power States** | ✅ Partial — D0/D3 transitions, PME signaling |
| **Link Bring-Up** | ⚠️ Limited — PHY simulation may be basic |
| **Traffic** | ⚠️ Limited — Loopback only, no real packets |
| **Wake-on-LAN** | ⚠️ Limited — Magic packet injection depends on model |
| **Throughput** | ❌ N/A — Not cycle-accurate, no real Ethernet |
| **PHY Timing** | ❌ N/A — SGMII training not modeled |

### What Simics CANNOT Validate for GbE

- Real Ethernet traffic throughput
- Cable/switch interoperability
- PHY-level timing (autoneg, SGMII training details)
- Energy Efficient Ethernet (EEE) timing
- Cycle-accurate performance

---

## 2. GbE in the Virtual Platform

### VP Repository Location

GbE models are part of the Intel Virtual Platform (VP) repository:

```
applications.simulators.isim.vp/
├── <platform>/
│   ├── modules/
│   │   ├── <platform>-pch/
│   │   │   ├── comp.py              # Component instantiation
│   │   │   ├── gbe.dml              # GbE device model (DML)
│   │   │   └── gbe_phy.dml          # PHY model (if separate)
│   │   └── <platform>-init/
│   │       └── sw.py                # Platform init scripts
│   └── targets/
│       └── <platform>.py            # Boot/launch config
└── chips/
    └── <pch_name>/
        └── private/
            └── sideband_ports.dml   # IOSF SB port mapping
```

### GbE Model Type

The I219 GbE controller is typically modeled as a **Functional Model** (Fmod):

| Model Type | Description | GbE Status |
|------------|-------------|------------|
| **Fmod** | Functional model — registers, interrupts, DMA | ✅ Typical for I219 |
| **Pass-through** | Host NIC passthrough to Simics | ⚠️ Optional for real traffic |
| **Loopback** | TX → RX loopback within model | ✅ For basic validation |

---

## 3. GbE Model Architecture

### I219 GbE Model Components

```
┌──────────────────────────────────────────────────────────┐
│                    GbE Model (gbe.dml)                   │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ PCI Config  │  │ MMIO Regs   │  │ DMA Engine      │  │
│  │ Space       │  │ (BAR0)      │  │ (TX/RX Rings)   │  │
│  │ VID/DID/BAR │  │ CTRL/STATUS │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Interrupt   │  │ PHY Model   │  │ Power Mgmt      │  │
│  │ Controller  │  │ (MDIC)      │  │ (D0/D3, PME)    │  │
│  │ MSI/INTA    │  │             │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
   ┌────────────┐       ┌────────────────┐
   │  PCIe Bus  │       │ PHY Transactor │
   │  Model     │       │ (if external)  │
   └────────────┘       └────────────────┘
```

### Key DML Registers

The GbE DML model implements these critical registers:

```dml
// PCI Config Space
register VID  @ 0x00 { value = 0x8086; }
register DID  @ 0x02 { value = platform_did; }  // Platform-specific
register CMD  @ 0x04 { ... }
register BAR0 @ 0x10 { ... }
register PMCSR @ 0xCC { ... }  // Power state

// MMIO Registers (BAR0 + offset)
register CTRL   @ bar0 + 0x0000 { ... }
register STATUS @ bar0 + 0x0008 { ... }
register RCTL   @ bar0 + 0x0100 { ... }
register TCTL   @ bar0 + 0x0400 { ... }
register MDIC   @ bar0 + 0x0020 { ... }  // PHY access
```

---

## 4. Per-Platform Setup

### MTL VP Setup

```python
# Launch MTL VP with GbE enabled
# In Simics CLI:
run-command-file targets/mtl/mtl-gbe.simics

# Or via command line:
./simics -e "run-command-file targets/mtl/mtl-gbe.simics"
```

BIOS configuration for GbE:
```
LanEnable = 1
GbeLanPme = 1
```

### LNL VP Setup

```python
# LNL uses single-die SOC — GbE in SOC
run-command-file targets/lnl/lnl-gbe.simics
```

### NVL VP Setup

```python
# NVL has PCD-H and PCH-S variants
# PCD-H (compute die):
run-command-file targets/nvl/nvl-pcd-gbe.simics

# PCH-S:
run-command-file targets/nvl/nvl-pch-gbe.simics
```

### Verifying GbE in VP

After VP boot, verify GbE enumeration:

```python
# In Simics CLI / PythonSV
gbe = sv.socket0.pcieB0D31F6
print(f"VID: {gbe.vid.read():#06x}")   # Should be 0x8086
print(f"DID: {gbe.did.read():#06x}")   # Platform-specific
print(f"BAR0: {gbe.bar0.read():#010x}")
```

---

## 5. GbE Validation Scenarios

### Scenario 1: PCI Enumeration Validation

**Objective**: Verify GbE enumerates with correct VID/DID/BAR.

```python
# PythonSV test script
def test_gbe_enumeration():
    gbe = sv.socket0.pcieB0D31F6
    
    vid = gbe.vid.read()
    assert vid == 0x8086, f"VID mismatch: {vid:#06x}"
    
    did = gbe.did.read()
    assert did != 0xFFFF, "GbE disabled (DID=0xFFFF)"
    
    bar0 = gbe.bar0.read()
    assert bar0 != 0, "BAR0 not allocated"
    
    print("PASS: GbE enumeration verified")
```

### Scenario 2: Register Access Validation

**Objective**: Verify MMIO register reads/writes work correctly.

```python
def test_gbe_registers():
    gbe = sv.socket0.pcieB0D31F6
    bar0 = gbe.bar0.read() & ~0xF
    
    # Read STATUS register
    status = itp.mem.read(bar0 + 0x0008, 4)
    print(f"STATUS: {status:#010x}")
    
    # Read CTRL register
    ctrl = itp.mem.read(bar0 + 0x0000, 4)
    print(f"CTRL: {ctrl:#010x}")
    
    # Write/read test (CTRL.SLU bit)
    ctrl_new = ctrl | (1 << 6)  # Set SLU
    itp.mem.write(bar0 + 0x0000, 4, ctrl_new)
    ctrl_verify = itp.mem.read(bar0 + 0x0000, 4)
    assert (ctrl_verify >> 6) & 1 == 1, "CTRL.SLU write failed"
    
    print("PASS: Register access verified")
```

### Scenario 3: Driver Load Validation

**Objective**: Verify Windows/Linux driver loads on VP.

**Windows (in VM on VP):**
```powershell
# Check driver loaded
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*I219*" }

# Check driver status
Get-NetAdapter
```

**Linux (in VM on VP):**
```bash
# Check driver loaded
lspci -s 00:1f.6 -vvv | grep driver
# Expected: Kernel driver in use: e1000e

# Check interface
ip link show
```

### Scenario 4: Power State Transition

**Objective**: Verify D0/D3 transitions in Simics.

```python
def test_gbe_power_states():
    gbe = sv.socket0.pcieB0D31F6
    
    # Read current power state
    pmcsr = gbe.pmcsr.read()
    power_state = pmcsr & 0x3
    print(f"Initial power state: D{power_state}")
    
    # Transition to D3
    gbe.pmcsr.write(pmcsr | 0x3)
    pmcsr_d3 = gbe.pmcsr.read()
    assert (pmcsr_d3 & 0x3) == 3, "D3 transition failed"
    print("D3 transition: OK")
    
    # Transition back to D0
    gbe.pmcsr.write(pmcsr_d3 & ~0x3)
    pmcsr_d0 = gbe.pmcsr.read()
    assert (pmcsr_d0 & 0x3) == 0, "D0 transition failed"
    print("D0 transition: OK")
    
    print("PASS: Power state transitions verified")
```

### Scenario 5: Loopback Traffic (If Supported)

**Objective**: Verify basic TX/RX path via internal loopback.

```python
def test_gbe_loopback():
    # This requires model support for loopback mode
    gbe = sv.socket0.pcieB0D31F6
    bar0 = gbe.bar0.read() & ~0xF
    
    # Set loopback mode in RCTL
    rctl = itp.mem.read(bar0 + 0x0100, 4)
    rctl |= (1 << 6)  # LBM (Loopback Mode)
    itp.mem.write(bar0 + 0x0100, 4, rctl)
    
    # Configure TX/RX rings and send test packet
    # (Implementation depends on model)
    
    # Check TX/RX counters
    gptc = itp.mem.read(bar0 + 0x4080, 4)  # TX packets
    gprc = itp.mem.read(bar0 + 0x4074, 4)  # RX packets
    print(f"TX packets: {gptc}, RX packets: {gprc}")
```

---

## 6. PythonSV in Simics

### Connecting PythonSV to Simics

PythonSV can connect to a running Simics session for register access:

```python
# In PythonSV environment connected to Simics
import pysvtools.xmlcli.XmlCli as cli

# Discover GbE device
gbe = sv.socket0.pcieB0D31F6

# All standard PythonSV operations work
vid = gbe.vid.read()
did = gbe.did.read()
```

### Simics-Specific PythonSV Notes

- **Breakpoints**: Can set breakpoints on register access
- **Stepping**: Can step through transactions
- **Determinism**: Simics is fully deterministic — same test always produces same result
- **Speed**: Faster than RTL but slower than post-silicon

---

## 7. SW-CI Integration

### Running GbE Tests in SW-CI

GbE pre-silicon tests run in the Intel SW-CI (Software Continuous Integration) framework:

```yaml
# Example SW-CI test definition
test_gbe_enumeration:
  platform: mtl
  target: mtl-gbe.simics
  script: tests/gbe/test_enumeration.py
  timeout: 300
  
test_gbe_driver_load:
  platform: mtl
  target: mtl-gbe-windows.simics
  script: tests/gbe/test_driver_windows.py
  timeout: 600
```

### CI Pipeline Stages

1. **VP Build** — Build platform VP with GbE model
2. **VP Boot** — Boot VP to OS (Windows or Linux)
3. **GbE Tests** — Run GbE validation scripts
4. **Results** — Collect logs and report pass/fail

---

## 8. Debug Workflows

### Debug: GbE Not Enumerating in VP

```
1. Check BIOS knob: LanEnable = 1?
   - Verify in BIOS setup or via PythonSV BIOS knob read

2. Check model instantiation:
   - Look in comp.py for GbE component
   - Verify gbe.dml is compiled into VP

3. Check PCI enumeration logs:
   - Simics CLI: log-level gbe 4
   - Look for PCI config space access during boot

4. Read VID/DID directly:
   - sv.socket0.pcieB0D31F6.vid.read()
   - 0xFFFF = disabled, 0x8086 = enabled
```

### Debug: Driver Not Loading

```
1. Verify device enumerated (VID=0x8086, DID=expected)

2. Check driver INF matches DID:
   - Windows: e1d68.inf should list the platform DID
   - Linux: e1000e module should match via PCI ID table

3. Check for driver errors:
   - Windows: Event Viewer > System log
   - Linux: dmesg | grep e1000e

4. Simics trace:
   - Enable register access logging
   - Check if driver is accessing expected registers
```

### Debug: Register Access Failures

```
1. Check BAR0 allocation:
   - sv.socket0.pcieB0D31F6.bar0.read()
   - Should be non-zero

2. Check PCI CMD register:
   - Bit 1 (Memory Space) must be set
   - sv.socket0.pcieB0D31F6.cmd.read() & 0x2

3. Try direct memory access:
   - itp.mem.read(bar0_base + 0x0008, 4)  # STATUS register
   - Should return valid data (not 0xFFFFFFFF)

4. Check model logs for access errors
```

---

## 9. Known Simics Limitations

### GbE Model Limitations

| Feature | Limitation | Impact |
|---------|------------|--------|
| **Ethernet Traffic** | No real network stack in model | Cannot test throughput, iperf |
| **PHY Training** | SGMII training simplified/stubbed | Cannot validate PHY bring-up timing |
| **EEE** | Not modeled | Cannot validate Energy Efficient Ethernet |
| **Wake-on-LAN** | Magic packet injection may not work | Limited WoL validation |
| **Statistics** | Counters may not increment realistically | Limited stats validation |
| **NVM/OTP** | Flash emulation may be basic | EEPROM tests may fail |

### Workarounds

- **Traffic testing**: Use loopback mode or connect to Simics virtual network
- **PHY validation**: Defer PHY-level tests to post-silicon
- **WoL**: Use PythonSV to directly inject PME events
- **Statistics**: Manually increment counters for test purposes

---

## Quick Reference

### Start GbE Validation in Simics

```bash
# 1. Launch VP
./simics -e "run-command-file targets/mtl/mtl-gbe.simics"

# 2. Wait for OS boot
# 3. Connect PythonSV
# 4. Run validation script
python tests/gbe/test_enumeration.py
```

### Common Simics CLI Commands

```tcl
# Enable GbE logging
log-level gbe 4

# List GbE component
list-objects -all | grep -i gbe

# Read register
(gbe.bank.regs)->STATUS

# Set breakpoint on register access
break-io address=0xFE600008 -r   # Break on STATUS read
```
