# THC SIMICS Pre-Silicon Knowledge Base

> **Owner**: Chin, William Willy (`willychi`)
> **Domain**: FV-THC (Touch Host Controller)
> **Created**: 2026-03-25
> **Version**: 2.4
> **Purpose**: Comprehensive reference documenting SIMICS/Virtual Platform concepts, architecture, and THC-specific pre-silicon validation knowledge. Compiled from **47 Intel Wiki pages** + THC domain expertise.
> **Target Platform**: TTL (Gen4.2) — A0 Power On readiness
> **Revision History**:
> - v2.4 (2026-03-26): Re-studied all 29 original wiki pages + discovered and studied 18 NEW pages. Added 8 new sections (26–33): THC Emulation/Maestro, WCL Sightings, Display Sync, IPSV Framework, S0ix PM, SPI EV, PRD/DMA Maestro, Fuse Debug. Added 9 new gaps (G29–G37). Updated reference table to 47 pages. Added RZL platform data.
> - v2.3 (2026-03-26): Initial 25-section document from 29 wiki pages.
> - v2.2 (2026-03-25): Gap analysis (G1–G28), Appendix B model type decision.

---

## Table of Contents

1. [What is SIMICS?](#1-what-is-simics)
2. [SIMICS vs Virtual Platform (VP)](#2-simics-vs-virtual-platform-vp)
3. [Why SIMICS for Pre-Si Validation](#3-why-simics-for-pre-si-validation)
4. [IP Model Types & Taxonomy](#4-ip-model-types--taxonomy)
5. [Virtual Platform Ingredients](#5-virtual-platform-ingredients)
6. [VP Architecture & Build System](#6-vp-architecture--build-system)
7. [DML (Device Modeling Language)](#7-dml-device-modeling-language)
8. [AutoDML — AI-Driven Model Generation](#8-autodml--ai-driven-model-generation)
9. [Chassis Power Management Framework](#9-chassis-power-management-framework)
10. [SPI Transactor & Virtual Test Cards](#10-spi-transactor--virtual-test-cards)
11. [Existing THC Model: thc_vdm](#11-existing-thc-model-thc_vdm)
12. [PythonSV SW-CI Framework](#12-pythonsv-sw-ci-framework)
13. [Practical Setup & Usage](#13-practical-setup--usage)
14. [SIMICS Debug Techniques](#14-simics-debug-techniques)
15. [Feature Model Overrides (Fmod)](#15-feature-model-overrides-fmod)
16. [FV Domain Validation Strategy for SIMICS](#16-fv-domain-validation-strategy-for-simics)
17. [THC Pre-Si Strategy Alignment](#17-thc-pre-si-strategy-alignment)
18. [Reference Wiki Pages](#18-reference-wiki-pages)
19. [Per-Platform THC Simics Operational Guide](#19-per-platform-thc-simics-operational-guide)
20. [Touch Device Model Architectures](#20-touch-device-model-architectures)
21. [Driver Installation & Workarounds in Simics](#21-driver-installation--workarounds-in-simics)
22. [THC Simics Debugging](#22-thc-simics-debugging)
23. [SPARK Transactor THC Support History](#23-spark-transactor-thc-support-history)
24. [CVE Simics Organizational Structure](#24-cve-simics-organizational-structure)
25. [THC Emulation — Maestro, HFPGA & SLN](#25-thc-emulation--maestro-hfpga--sln)
26. [WCL Known Issues & Sightings](#26-wcl-known-issues--sightings)
27. [Display Sync / Frame Sync Validation](#27-display-sync--frame-sync-validation)
28. [THC IPSV Test Framework](#28-thc-ipsv-test-framework)
29. [S0ix PM Enabling & THC Disable](#29-s0ix-pm-enabling--thc-disable)
30. [SPI Electrical Validation Reference](#30-spi-electrical-validation-reference)
31. [PRD/DMA Maestro Implementation Details](#31-prddma-maestro-implementation-details)
32. [Fuse Debugging for THC](#32-fuse-debugging-for-thc)
33. [Requirements Gap Analysis (G1-G37)](#33-requirements-gap-analysis-g1-g37)

---

## 1. What is SIMICS?

**Simics** is Intel's full-system simulator, developed by Wind River (an Intel subsidiary). It simulates entire computing systems — processors, memory, peripherals, buses, and I/O — at the **functional/architectural level** (NOT cycle-accurate, NOT RTL-level).

### Key Characteristics

| Property | Description |
|----------|-------------|
| **Execution Model** | Functional simulation — models register behavior, memory maps, interrupts, DMA, power states |
| **Accuracy Level** | Architecturally accurate but NOT cycle-accurate. No gate-level timing |
| **Binary Compatibility** | Runs **unmodified production binaries** — real BIOS, FW, OS, and drivers |
| **Speed** | Can boot complex SoCs in minutes (vs hours for RTL simulation) |
| **Determinism** | Fully deterministic and reproducible — same input always produces same output |
| **Observability** | Full system visibility — all registers, memory, buses observable simultaneously |
| **Control** | Halt/go/step execution, inject failures, breakpoints on any register access |

### What SIMICS is NOT

- **NOT an RTL simulator** — does not simulate gate-level logic or transistor timing
- **NOT a replacement for all validation** — complements post-silicon, does not replace it
- **NOT cycle-accurate** — timing-sensitive issues (setup/hold, race conditions) cannot be caught
- **NOT a waveform tool** — no signal-level analysis (use HFPGA or RTL for that)

---

## 2. SIMICS vs Virtual Platform (VP)

This distinction is critical and often confused:

| Concept | Definition | Analogy |
|---------|-----------|---------|
| **Simics** | The simulation **engine/tool** | The car engine |
| **Virtual Platform (VP)** | The **model/product** built using Simics | The complete car |

- **Simics** provides the simulation framework, APIs, DML compiler, debug tools, scripting
- **VP** is a specific platform model (e.g., "RazorLake Desktop VP", "NoveLake VP") that:
  - Combines high-speed processor simulators + functional models of all HW blocks
  - Includes target scripts, BIOS images, OS images, and configuration
  - Is packaged and versioned for release (Bronze/Silver/Gold)

### VP Repository Structure

The VP source lives in the `applications.simulators.isim.vp` repo (develop branch):

```
vp/
├── common/modules/srv-tests/     # PythonSV tester scripts
│   ├── pythonsv_tester.py        # PythonSV test runner
│   └── pythonsv_util.py          # Utility functions
├── <platform>/
│   ├── modules/
│   │   ├── <platform>-init/      # Platform init (sw.py, testers.py)
│   │   ├── <platform>-pch/       # PCH IP models
│   │   │   ├── comp.py           # Component instantiation
│   │   │   └── *.dml             # DML device models
│   │   └── <platform>-uncore/    # Uncore models
│   ├── config/
│   │   ├── autogen-test.mk       # AutoGen framework config
│   │   ├── presets/              # BIOS/config presets
│   │   └── pythonsv.yml          # PythonSV test config
│   └── targets/                  # Target launch scripts
│       └── <platform>.py         # Boot/launch config
├── chips/
│   └── <pch_name>/
│       └── private/
│           └── sideband_ports.dml  # IOSF SB port mapping
└── tests/                        # VP unit tests
```

---

## 3. Why SIMICS for Pre-Si Validation

### The Business Case (from NVL-S Analysis)

Intel's internal analysis of NVL-S (NoveLake Server) at Power On revealed:

- **~1200 total sightings** at Power On
- **~800 SV (Silicon Validation)** sightings
- **193 SW/BIOS/FW sightings** analyzed in detail:

| Category | Count | Description |
|----------|-------|-------------|
| HW bugs | 112 | Silicon/RTL issues |
| FW bugs | 135 | Firmware issues |
| BIOS bugs | 46 | BIOS programming errors |
| SW bugs | 12 | Software/driver issues |
| Doc bugs | 47 | Documentation errors |
| Env bugs | 127 | Environment/setup issues |
| Board bugs | 12 | Board-level issues |
| Rejected | 344 | False positives/duplicates |

### Simics Actionability Breakdown

| Action | Count | Effort |
|--------|-------|--------|
| Low effort (model exists, run tests) | 73 | Days |
| Model gaps (partner with S3E for fidelity) | 75 | Weeks |
| Out of scope (need correct environment) | 64 | N/A for Simics |

### Real-World Impact Examples

1. **Register Programming Mismatch**: Found in <1 day on Simics, but took 7+ days to release fix globally to all teams
2. **Memory Allocation Failure**: Took >90 days to root cause on silicon, still open after >5 months. Could have been caught in Simics in hours
3. **USB3 Gen2 Enumeration**: PythonSV script bug found in <1 day on Simics
4. **PCIe Latency Programming**: Checker script found issue in <1 day, but ~3 months to release fix globally

### Key Insight

> **"The ONLY way to achieve A0 PRQ is with heavy investment in Simics."**
> — FV Domain Strategy Guidance (Wiki Page 4605435116)

The lifecycle of a bug is LONG: find → debug → root cause → confirm fix → release → EVERYONE adopts (including customers). Finding bugs in Simics pre-silicon is the **cheapest and fastest** way to resolve them.

---

## 4. IP Model Types & Taxonomy

Every IP block in the SoC needs a **model type decision**. The taxonomy (from Altera/KM Simics practice, universally applicable):

### Model Types (from least to most functional)

| # | Model Type | Description | Use Case | THC Applicability |
|---|-----------|-------------|----------|-------------------|
| 1 | **Memory Model (Register-Only)** | Registers store values but NO behavior/callbacks. Reads/writes go to a memory space, no side-effects | Placeholder until real model available; BIOS can enumerate device | **MINIMUM** for THC — enough for PCI enum but not for functional validation |
| 2 | **Behavioral Model** | Behavior simulated but NOT with real FW. Black-box model that mimics external behavior | When FW is not available or not needed | Not ideal for THC — need real driver interaction |
| 3 | **Register Functional Model** | Full register interface WITH callback functionality. Side-effects on read/write (status bits update, interrupts fire, DMA transfers execute) | When FW/BIOS/driver must interact with real register behavior | **TARGET** for THC — registers + DMA + interrupts + protocol |
| 4 | **Transactional Model** | Models transaction flow (memory-mapped, transaction IDs, NOC fabric) | NOCs, bus fabric, complex interconnects | For IOSF sideband interface to THC |
| 5 | **Feature Model (Fmod)** | RTL-derived model on FPGA via HFPGA transactor stubs. Highest fidelity short of real silicon | When timing/fidelity is critical | Future option if THC RTL available on FPGA |

### Color Coding Convention (VP IP Tracking)

| Color | Status |
|-------|--------|
| 🟢 Green | Model available with main features |
| 🟡 Yellow | Model planned but not yet available |
| 🔴 Red | No model planned |
| ⚪ Gray | Memory/register-only model (no functionality) |

### Stakeholder Matrix for Each IP Model

| Role | Responsibility |
|------|---------------|
| **Simics Model Owner** (S3E team) | Creates and maintains the DML model |
| **RTL Design Owner** (IP team) | Provides HAS/EDS, answers model fidelity questions |
| **DV Owner** (Design Verification) | Validates model against RTL behavior |
| **FW Stakeholder** | Validates FW interaction with model |
| **FV Stakeholder** (us — CVE) | Validates test content works on model |

---

## 5. Virtual Platform Ingredients

A complete VP is assembled from these ingredients:

### 5.1 Python Components

- Define HW board/SoC/block architecture
- Instantiate device models
- Include sub-blocks, interfaces, connectors, helper commands
- File: `comp.py` in each module directory

### 5.2 DML Device Models

- **DML** = Device Modeling Language (Simics-specific, compiled)
- Core modeling language for IP functional models
- Compiled to C, then to native code for speed
- Defines registers, banks, callbacks, interfaces
- See [Section 7](#7-dml-device-modeling-language) for details

### 5.3 SystemC/C++ Models

- Third-party or external code integrated into Simics
- Used when existing C/C++ models are available (e.g., vendor IP models)
- Wrapped in Simics interfaces

### 5.4 Python Device Modules

- Slower DML alternative, used for **prototyping**
- Translated to DML for production use
- Good for rapid model exploration before committing to DML

### 5.5 Target Scripts

- Located in `<workspace>/targets/`
- Instantiate components, pass parameters
- Load ELF/binary images, enable debugger
- Configure boot flow (SVOS, EFI, Windows)

### 5.6 Register and Memory Map Collateral

- **IP-XACT** format register definitions
- **NoC collateral** for memory map routing
- CDB2 flow creates skeleton models from these
- AutoDML can also ingest register definitions (see Section 8)

### 5.7 Library/Common Code

- Reusable DML/Python across platforms
- Parameterized for platform-specific differences
- Located in `vp/common/` and `vp/chips/`

### 5.8 Unit Tests and FW Tests

- VP-level unit tests (instantiation, register access)
- FW regression tests (regtest)
- PythonSV integration tests (Bronze/Silver/Gold gates)

### Build & Packaging

```bash
# Build a specific package
gmake pkg-<number>

# Run package tests
test/runtest.py <tag>
```

---

## 6. VP Architecture & Build System

### Creating a New Platform VP (Step-by-Step)

Based on the SRE Client/Server VP creation guide:

#### Step 1: Initial Setup
1. Copy previous-gen PCH + Uncore directories to new directory
2. Rename with new platform name/sku/stepping
3. Copy platform directory, target scripts, simics-bundle, tests
4. Keep only instantiation test initially
5. Update Makefiles and packaging

#### Step 2: Address Map
- Use MCHBAR/REGBAR/EDRAMBAR/DFDBAR tables from arch docs
- Map to DML/PY files in `vp/chips/<uncore>/private/sideband_ports.dml`

#### Step 3: Sideband Ports (CRITICAL for THC)
- PCH Chapter 41 — IOSF Sideband Interface spreadsheet
- Uncore Sideband PortID spreadsheet
- **THC has IOSF SB port 0x39** — must be mapped in sideband_ports.dml
- PTL+ requires **16-bit SB port ID** (breaking change from 8-bit)

#### Step 4: CRIF Integration
- Create transforms, fuses
- `gmake <fuse-target>`
- DevBanks — "onion-peeling" process

#### Step 5: GPIO Setup (CRITICAL for THC)
- Pad groups with `PAD_START`/`PAD_END`
- Pad size = 0x10
- Configure in `comp.py`
- **THC needs GPIO pad for touch device interrupt** (platform-specific pin assignment)

#### Step 6: PSF (Primary Scalable Fabric)
- Set `PSF_AGENTS_AMOUNT` from PSF Backbone HAS block diagram
- THC's PCI functions route through PSF

#### Step 7: PMC
- Add platform to `pmc-parameters.dml`
- THC uses PMCLite sideband for PM signaling (port IDs: THC0=0xFC6E, THC1=0xFC6F on NVL — **TTL port IDs TBD, verify against TTL HAS/platform data**)

#### Step 8: BIOS Enabling
- BIOS must enumerate THC as PCI device
- THC BIOS init = 14 steps (per BWG Rev 0.5); Requirements doc v2.4 expands to 16 steps (REQ-BIOS-01..16)
- ACPI tables (DSM, _CRS, _DSD) must be present

---

## 7. DML (Device Modeling Language)

DML is the native Simics language for writing device models. Key concepts:

### Structure

```dml
dml 1.4;

device thc_port;

import "utility.dml";
import "pci/common.dml";

// PCI Configuration
param pci_hotplug = false;

// Register Bank
bank regs {
    register PRT_CONTROL @ 0x008 is (read, write) {
        field PORT_TYPE [31:30] is (read, write);
        field PORT_EN [0] is (read, write);
        
        // Callback: side-effect on write
        method after_write(memop) {
            if (PORT_EN.val == 1) {
                log info: "THC port enabled, type=%d", PORT_TYPE.val;
                // Trigger port initialization
            }
        }
    }
    
    register INT_STATUS @ 0x010 is (read, write) {
        // Read clears certain bits (W1C behavior)
        method after_read(memop) {
            // Clear status bits after read
        }
    }
}
```

### Key DML Concepts for THC Modeling

| Concept | Description | THC Relevance |
|---------|-------------|---------------|
| **Banks** | Register groups mapped to memory space | Common regs (base+0x000), Port0 (base+0x1000), Port1 (base+0x2000) |
| **Registers** | Named registers with offset, fields, access methods | All THC MMIO registers (PRT_CONTROL, INT_EN, DMA regs, etc.) |
| **Fields** | Bit fields within registers | port_type[31:30], spi_io_mode[29:28], etc. |
| **Callbacks** | `after_read`, `after_write`, `before_write` methods | Status bit auto-clear, DMA trigger on write, interrupt assertion |
| **Interfaces** | Typed communication between models | PCI interface, SPI master/slave interface, interrupt interface |
| **Connections** | Links between device instances | THC ↔ SPI transactor ↔ VTC (thc_vdm) |
| **Events** | Timed events in simulation | DMA completion, timeout timers, PIO sequence timing |

### Building DML Models

```bash
# Build with debug symbols (for GDB attach)
gmake DEBUG=yes

# Build specific module
gmake <module-name>

# Run unit tests
test/runtest.py <tag>
```

---

## 8. AutoDML — AI-Driven Model Generation

**AutoDML** is an AI-driven, 5-phase workflow for automatically generating Simics device models from HW specifications. Integrated in the VP repo under `.github/skills/`.

### 5-Phase Workflow

```
Phase 1: spec-analyzer
  Input: HW spec (PDF/MD)
  Output: project.md + <device>-registers.xml (IP-XACT format)

Phase 2: proposal
  Input: project.md + IP-XACT
  Output: proposal.md + tasks.md + DML skeleton

Phase 3: apply
  Input: Tasks from proposal
  Process: Implements DML code + Python tests task-by-task
           Builds after each group
           DML code review gate
  Output: Production DML device model

Phase 4: verify-change
  Checks: Completeness (CRITICAL) / Correctness (WARNING) / Coherence (SUGGESTION)

Phase 5: archive-change
  Archives completed change
```

### AutoDML Sub-Skills (10 total)

The AutoDML AI framework consists of **10 sub-skills** (not just the 5 phases above):
1. `autodml` — top-level orchestrator
2. `spec-analyzer` — Phase 1 HAS/spec extraction
3. `spec-clarification` — follow-up questions when spec is ambiguous
4. `ipxact-generator` — generates IP-XACT XML from spec
5. `proposal` — Phase 2 task breakdown
6. `apply` — Phase 3 DML code generation
7. `requesting-dml-code-review` — quality gate after each task group
8. `verify-change` — Phase 4 completeness/correctness/coherence
9. `archive-change` — Phase 5 archival
10. `knowledge-search` — searches prior knowledge base for reuse

*(Source: wiki page 4661117246, AutoDML BKM)*

### Prerequisites

1. VP repo cloned
2. Simics project initialized (e.g., `ttl-7` for THC target)
3. GitHub Copilot CLI
4. HW specification file (PDF or Markdown)

### THC-Specific Opportunity

> **AutoDML can potentially generate the THC Simics model directly from the THC IP HAS (`sip_thc_4x_has.html`).**
> This would produce a DML skeleton with all registers, fields, and basic callbacks that we can then enhance with functional behavior (DMA, interrupts, PIO, power management).

---

## 9. Chassis Power Management Framework

The Simics Chassis PM framework models the complete power management hierarchy relevant to THC. Key integration points:

### PMC Model

- PMC (Power Management Controller) coordinates all power state transitions
- IOSF sideband messages used for PM commands between PMC and IP models
- THC communicates with PMC via **PMCLite** sideband interface

### THC PM Integration Points

| THC PM Feature | SIMICS Model Requirement |
|---------------|------------------------|
| **D0i2** (HW-autonomous PG) | Model PGD/UGD domains, state retention, PMCLite RES_OWN_REQ/ACK |
| **CGPG** (Clock/Power Gating) | Model clock gating signals, power gate entry/exit timing |
| **D3 (4 levels)** | Model L0-L3 D3 variants (PTL+), register save/restore |
| **LTR** (Latency Tolerance Reporting) | Model LTR register writes → PMC notification |
| **S0ix** | Model platform-level sleep integration |
| **WoT** (Wake-on-Touch) | Model GPIO wake path (NOT THC IP — goes through GPIO IP / vGPIO) |

### PMCLite Command Codes (for THC)

| Command | Code | Direction |
|---------|------|-----------|
| D0 | `0x8086D000` | THC → PMC |
| D0i2 Entry | `0x8086D201` | THC → PMC |
| D0i2 Exit | `0x8086D200` | THC → PMC |
| D3 Entry | `0x8086D301` | THC → PMC |
| D3Hot Entry | `0x8086D302` | THC → PMC |
| D3Cold Entry | `0x8086D303` | THC → PMC |
| PG Entry | `0x80860301` | THC → PMC |
| PG Exit | `0x80860302` | THC → PMC |
| Save Complete | `0x80860200` | THC → PMC |
| Restore Complete | `0x80860201` | THC → PMC |
| D3 Level 0 | `0x8086D310` | UHFI → PMCLite |
| D3Hot | `0x8086D311` | UHFI → PMCLite |
| D3Cold | `0x8086D312` | UHFI → PMCLite |

*(Codes from THC power sub-skill, sourced from sip_thc_4x_has.html)*

---

## 10. SPI Transactor & Virtual Test Cards

### SPI Transactor (spi_xtor)

The **SPI transactor** bridges Simics VDM (Virtual Device Model) and the DUT's SPI controller. It operates as:

```
DUT (THC SPI Controller) ──► xtor RTL ──► xtor SW (clock stops)
                                              │
                                              ▼
                                         Process opcode
                                              │
                                              ▼
                                    Get command length
                                              │
                                              ▼
                                    Receive full command
                                              │
                                              ▼
                                    Send to device VDM
                                              │
                                              ▼
                                    VDM responds (thc_vdm)
                                              │
                                              ▼
                                         xtor RTL ──► DUT
```

### SPI Transactor Modes

| Mode | Class | Description | THC Relevant? |
|------|-------|-------------|---------------|
| UART | `spi_xactor_uart` | UART over SPI | No |
| NOR flash | `spi_xactor_nor` | NOR flash interface | No |
| TPM | `spi_xactor_tpm` | TPM over SPI | No |
| GSD AOH | `spi_xactor_gsd_aoh` | GSD AOH mode | No |
| **SPI flash generic** | `spi_xactor_flash` + `spi_xtor_flash_vdm` | **Generic SPI device** | **YES — connects to thc_vdm** |
| eSPI | `spi_xactor_espi` | eSPI mode | No |
| eSPI passthrough | `spi_xactor_espi_pt` | eSPI passthrough | No |

### Critical Quote from Wiki

> *"SPI flash generic mode is currently used to connect an SPI controller in the DUT with a Touch Host Controller (THC) Virtual Test Card (VTC)."*

This confirms that the `spi_xactor_flash` mode is the established connection path for THC in Simics.

### thc_vdm Instantiation Code (from spi_xtor Integration wiki)

> **Source**: Wiki page 1249986913 (spi_xtor Integration WIP, v8)

```python
# thc_vdm instantiation in Simics script
pre_conf_object('test_thc', 'thc_vdm')
# Required attributes:
#   spi_host_obj = SimicsObjectPortRef → spi_xtor (must implement serial_peripheral_interface_master_interface)
#   mem_space    = memory_space object for reads/writes
# Connect via:
#   spi_slave_obj + flash_vdm on the spi_xactor_flash side
```

### SPI Opcode Configuration per IO Mode

| IO Mode | Read Opcode | Write Opcode | Cmd Bits | Addr Bits | Dummy Bits |
|---------|-------------|-------------|----------|-----------|------------|
| Single (1-1-1) | `0x0B` | `0x02` | 40 | 24 | 8 |
| Dual (1-2-2) | `0xBB` | `0xB2` | 40 | 24 | 8 |
| Quad (1-4-4) | `0xEB` | `0xE2` | 40 | 24 | 8 |

### Interrupt Pin Connection (simple_io_xtor)

```
# Connect GPIO interrupt from thc_vdm to THC controller
# thc → thc_int = io_xtor
# outputs_reset_value = 1  (active-low interrupt, idle high)
```

### Integration Setup (SPARK Repositories)

Add to `cfg/repositories.yml`:
- **spi-xtor** repo with `REPO_TAG=develop`
- **thc-vtc** repo with `REPO_TAG=develop`
- SPARK 1.12.x supports Direct Clocking mode for SPI transactor

> **⚠️ THC VTC DEPRECATED**: As of SPARK 1.11.7, the original THC VTC component is deprecated due to lack of support. The replacement is **thc_vdm** (C++ device model). All new integrations should use thc_vdm directly.

---

## 11. Existing THC Model: thc_vdm

### Overview

The **`thc_vdm`** is an existing C++ device model implementing the **THC Virtual Test Card (VTC)** — the simulated touch device that connects to the THC SPI controller via the SPI transactor.

### Connection Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  THC SPI Controller  │────►│ spi_xactor_flash │────►│  thc_vdm    │
│  (DUT model in VP)   │     │   (SPI bridge)   │     │ (Touch VTC) │
│                      │◄────│                  │◄────│             │
└─────────────────────┘     └──────────────────┘     └─────────────┘
```

### thc_vdm Attributes

#### Required Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `spi_host_obj` | SimicsObjectPortRef | Reference to `spi_xtor` object. Must implement `serial_peripheral_interface_master_interface` |
| `mem_space` | SimicsObjectPortRef | Reference to `memory_space` for reads/writes |

#### Optional Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `touch_int_cause` | uint32 | 0 | Interrupt cause register — maps to ICR (Input Cause Register) in HIDSPI |
| `tc_control` | uint32 | 0 | Test card control — configures VTC behavior |
| `ramless_datamode_ctrl` | uint32 | 0 | Ramless datamode control |
| `int_trigger` | uint32 | 0 | Interrupt trigger — simulates touch events |

### spi_xactor_flash Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `flash_vdm` | SimicsObjectPortRef | Reference to `spi_xtor_flash_vdm` for opcode information |
| `check_upstream_timer_max` | uint32 | Max timer for upstream check (default: `0xFFFFFFFF`) |
| `dummy_bits` | uint32 | Number of dummy bits in SPI frames (default: `8`) |
| `fixed_dummy_bits` | uint32 | Fixed dummy bits (default: `0`) |
| `use_inband_alert` | bool | Enable in-band alert mechanism (default: `FALSE`) |
| `disable_sfdp_dummy_byte` | bool | Disable SFDP dummy byte (default: `FALSE`) |
| `send_sfdp_as_fast_read` | bool | Send SFDP as fast read (default: `FALSE`) |

### Implications for THC FV

- **thc_vdm already exists** — we do NOT need to create a touch device VDM from scratch
- We need to understand its current **fidelity level** (does it support all HIDSPI report types? HID descriptors? Power states?)
- The THC **controller model** (the DUT side) is what needs to be created/enhanced
- The `int_trigger` attribute allows **programmatic touch event injection** — essential for automated testing

### VTC Deprecation Notice

> **Source**: Wiki page 1249986913 (spi_xtor Integration WIP) + 1249990578 (TC Getting Started)

- **THC VTC was DEPRECATED as of SPARK 1.11.7** due to lack of support — replaced by `thc_vdm`
- THC VTC status in TC Getting Started: "Migrated to Simics 6/Python 3. **Occasional support.**"
- All new THC Simics work should use `thc_vdm` (C++ device), NOT the legacy VTC
- SPARK repo for spi_xtor: `github.com/intel-innersource/frameworks.validation.spark.spi-xtor`

### thc_vdm Instantiation Code (from spi_xtor Integration)

```python
# thc_vdm instantiation (from wiki page 1249986913)
pre_conf_object('test_thc', 'thc_vdm')
# Set spi_host_obj → spi_xtor object
# Set mem_space → memory_space object
# Connect via spi_slave_obj + flash_vdm
```

### SPI Opcode Configuration per IO Mode

| IO Mode | Read Cmd | Write Cmd | Cmd Bits | Addr Bits | Dummy Bits |
|---------|----------|-----------|----------|-----------|------------|
| Single (1-1-1) | `0x0B` | `0x02` | 40 | 24 | 8 |
| Dual (1-2-2) | `0xBB` | `0xB2` | 40 | 24 | 8 |
| Quad (1-4-4) | `0xEB` | `0xE2` | 40 | 24 | 8 |

> These opcodes match the SPI EV reference data from wiki page 3466824139.

> **⚠️ Write Opcode Discrepancy (Legacy VTC vs thc_vdm)**: The legacy VTC used different write opcodes for Dual and Quad modes: WR_1_2_2=`0x32` and WR_1_4_4=`0xe3`. The current thc_vdm uses WR_1_2_2=`0xB2` and WR_1_4_4=`0xE2` (matching the HIDSPI protocol spec). If referencing old VTC code or wiki pages, be aware of this difference. *(Source: wiki page 1249986913)*

### Interrupt Pin Connection (simple_io_xtor)

```
# simple_io_xtor for interrupt pin
thc → thc_int = io_xtor
outputs_reset_value = 1    # Active-low interrupt
```

---

## 12. PythonSV SW-CI Framework

### CI Pipeline Structure

| Gate | Frequency | Timeout | Purpose |
|------|-----------|---------|---------|
| **Bronze** | Every 2 hours (model gate) | 1 hour | Quick smoke tests on latest VP |
| **Silver** | 1/day | 3 hours | Extended test suite |
| **Gold** | NGA-based | Variable | Full qualification via NGA |

### Jenkins Pipelines

- Server: `cje-fm-simics-prod01`
- PythonSV SW-CI suite runs every 6 hours on latest Simics Bronze Recipe

### Import Sheet Columns (Test Content Tracking)

| Column | Description |
|--------|-------------|
| TestName | PythonSV test script name |
| Cmdline | Full command line for execution |
| Domain | FV domain (e.g., THC, USB, Audio) |
| Owner | Test content owner (IDSID) |
| Auto/Manual | Automation status |
| Status | Current state (Enabled/Disabled/WIP) |
| SW-CI TestID | CI framework test ID |
| SW-CI Suite | CI suite assignment (Bronze/Silver/Gold) |
| SW-CI Status | CI execution status |
| SW-CI Gates | Quality gate assignments |
| SVOS Preconditions | OS boot requirements |
| PythonSV BaseAccess | Access mode (SimicsBaseAccess) |
| BIOS Knobs | Required BIOS configuration |
| HW/SW Config | Hardware/software prerequisites |
| Fmod Requirements | Feature model dependencies |

### AutoGen Framework

- Builds **TestRun Matrix** from Test YML + Configuration YML files
- Located in `<platform>/config/autogen-test.mk`

### Execution Flow

```
1. NGA wrapper (SimicsClientRunner.py) starts
2. Setup script (e.g., startttl_simics.py) initializes VP
3. Boot to SVOS or EFI
4. PythonSV test executes via SimicsBaseAccess
5. Exit code returned (0=PASS, 9=FAIL per NGA convention)
6. Results reported to NGA/VP-Portal
```

### Key Repos

| Repo | Branch | Content |
|------|--------|---------|
| `applications.simulators.isim.vp` | develop | VP source + models + tests |
| PythonSV (novalake) | main | Test scripts (C:\pythonsv\novalake\vjt\thc) |

### Reporting Dashboards

- **VP-Portal**: `vp-portal.intel.com`
- **PowerBI**: Domain-specific dashboards
- **CloudBees SDA**: CI/CD job monitoring

---

## 13. Practical Setup & Usage

### SimLauncher Installation

```bash
pip install simlauncher --index-url https://af02p-or.devtools.intel.com/artifactory/api/pypi/simics-pypi-or-local/simple
```

### Running a VP

```bash
# Setup configuration
dtconfig setup

# Launch VP (example for RazorLake, adapt for TTL)
simlauncher run razorlake-desktop-7 <version> \
    --cores 4 \
    --memory 128 \
    --disk 64 \
    --mode vnc
```

### Working Directory

```
/nfs/site/disks/simcloud_<user>_001/projects/<platform>-7/<version>/
```

### Launch Scripts

```bash
# Default boot (Windows with blessed IFWI)
./simics svos_simics.py

# Custom launch script
./simics my_thc_test.py
```

### Target Documentation

```
https://docs.intel.com/documents/vp_simulation/vp_release/7/<platform>/
```

---

## 14. SIMICS Debug Techniques

### Logging

```simics
# Set verbosity for a device
log-setup thc0 -verbose

# Break on specific log message
break-log thc0 "DMA transfer complete"
```

### Register Access

```simics
# PCI config space read
pci-read bus=16 dev=0 func=0 offset=0x00 size=4

# MMIO read (with SID/CID/TID)
mem-read <thc0.bar0> 0x008 4

# Break on device register access
break-io thc0.regs.PRT_CONTROL -w

# PIO synthetic test (from LNL vjt/thc)
# Read 8 bytes from device address 0x0
PIO_Read(0x0, 8)
# Write 4 bytes (0x12345678) to device address 0x0
PIO_Write(0x0, 4, 0x12345678)
```

### DML Source Debugging

```bash
# Build with debug symbols
gmake DEBUG=yes

# Use Eclipse + GDB attach
# Set breakpoints in DML source files
# Inspect DML variables
```

### BIOS Boot Phases

| Phase | Description | THC Relevance |
|-------|-------------|---------------|
| **SEC** | Security/reset vector | N/A |
| **PEI** | Pre-EFI Initialization | THC softstraps read |
| **DXE** | Driver Execution Environment | **THC PCI enumeration happens here** |
| **BDS** | Boot Device Selection | THC driver loading |

### VP Farm Access

```bash
# Developer debug with source code in farm
crt <session_name>
```

### Scripting

```python
# Python preferred for complex test logic
import simics

# Read THC register
val = simics.SIM_read_phys_memory(cpu, thc_bar0 + 0x008, 4)

# Write THC register
simics.SIM_write_phys_memory(cpu, thc_bar0 + 0x008, value, 4)

# Wait for condition
simics.SIM_run_command("wait-for-log thc0 'ready'")
```

---

## 15. Feature Model Overrides (Fmod)

**Fmod** (Feature Model) replaces a Simics functional model with an **RTL-derived model** for higher fidelity. This uses **HFPGA** (Hybrid FPGA) technology.

### How It Works

```
Normal: CPU ──► Simics DML Model ──► Simics Memory
Fmod:   CPU ──► Simics Stub ──► FPGA ──► RTL Model ──► FPGA ──► Simics Stub ──► Simics Memory
```

### When to Use Fmod

- When **timing-sensitive behavior** must be verified
- When the **functional model has known gaps** that RTL can fill
- When **HW bug reproduction** requires RTL fidelity
- Typically for complex IPs: GPU, NPU, PCIe

### THC Fmod Consideration

- THC is a **medium-complexity IP** — functional model likely sufficient for most FV content
- Fmod may be useful if specific **SPI timing issues** or **DMA race conditions** need RTL-level debug
- Decision: Start with Register Functional Model, add Fmod if needed for specific issues

---

## 16. FV Domain Validation Strategy for SIMICS

Based on the **"Simics Domain Validation Strategy Guidance"** (Wiki Page 4639114330), FV domains should deliver in 5 areas:

### Area 1: Content & Tools

| Activity | Description | THC Action |
|----------|-------------|------------|
| Qualify 100% of content/tools before PO | All PythonSV test scripts must work on Simics | Port all THC tests to Simics |
| Analyze sw.bug/env.bug sightings | Review previous-gen THC sightings | Mine HSDES for Simics-catchable THC bugs |
| Inject failures for recovery testing | Easy to simulate error conditions in Simics | Test DMA overrun, bus errors, timeout recovery |
| Analyze manual TCs and PO tasks | Convert manual test cases to automated | Automate THC PO checklist items |
| Analyze rejected sightings | Review wont_do/not_a_bug from prior programs | Identify environmental issues vs real bugs |

### Area 2: Pre-Si Validation

| Activity | Description | THC Action |
|----------|-------------|------------|
| Qualify RTL model content | Run content before RTL execution | Use Simics THC model to pre-qualify all tests |
| Clean up env/collateral/tool bugs | RTL cycles are EXPENSIVE — find bugs in Simics first | Run Bronze/Silver gates for THC tests |
| Sort out config/collateral issues | Validate BIOS, softstraps, ACPI before RTL | Test all THC BIOS configurations in Simics |

### Area 3: Post-Si Simics Use

| Activity | Description | THC Action |
|----------|-------------|------------|
| Effective triage during post-si | Reproduce silicon bugs in Simics | Use Simics to isolate THC silicon bugs |
| CCM delivers RVP+RTL config | Config matching device topology | Ensure THC BOM topology matches silicon RVP |

### Area 4: Debug

| Activity | Description | THC Action |
|----------|-------------|------------|
| Qualify debug tools before PO | PythonSV enabled early | Verify THC namednode access in Simics |
| Inject failures for debug testing | Test debug data collection | Test THC register dump, DMA state capture |
| Known gap: TAP network not modeled | Some debug paths unavailable | Plan alternative debug methods |

### Area 5: Validation HW (VTC)

| Activity | Description | THC Action |
|----------|-------------|------------|
| Qualify RVP config, test cards, devices | Virtual Test Card (VTC) solutions | Validate thc_vdm VTC model |
| Test card programming abstraction | Same content on Simics(VTC)/RTL(xTOR)/Silicon(real) | Ensure THC test scripts work across all 3 |

### Critical Principle

> **Test card programming interface should be abstracted across Simics (VTC) / RTL (xTOR) / Silicon (real card) — content should NOT change between models.**

This means THC PythonSV scripts must work on:
1. **Simics VP** with `thc_vdm` VTC
2. **RTL simulation** with xTOR SPI transactor
3. **Real silicon** with physical touch device

---

## 17. THC Pre-Si Strategy Alignment

### Strategy Document Reference

`C:\git\THC\Pre-Silicon_High-level-Strategy_for_CVE-FV-THC-domain.txt`

### Pillar 1: Test Content Readiness

| Requirement | SIMICS Dependency | Status |
|-------------|-------------------|--------|
| Bring-up/validate ALL THC test content | THC model in VP must support all test operations | Pending |
| PythonSV scripts for execution/checking/logging/debug | SimicsBaseAccess must provide THC namednode access | Pending |
| Simics must provide THC namednodes/registers | THC model must expose all registers via namednode interface | Pending |
| Execution flow support | DMA, PIO, interrupt flows must be functional in model | Pending |

### Pillar 2: Recipe/Ingredient Readiness

| Requirement | SIMICS Dependency | Status |
|-------------|-------------------|--------|
| Softstrap configs for THC modes | VP must support THC softstrap configuration | Pending |
| BIOS (ACPI/DSM/HID descriptors) | BIOS image must include THC ACPI tables | Pending |
| GPIO pin-mux configuration | GPIO model must support THC interrupt pin routing | Pending |
| PM/LTR settings | PMC model must support THC PMCLite interface | Pending |
| OS/driver readiness | THC driver must load and function in VP OS image | Pending |
| Platform enablement flows | Full boot → enum → init → data flow must work | Pending |

---

## 18. Reference Wiki Pages

All wiki pages studied and knowledge extracted from:

| Page ID | Title | Space | Key Content |
|---------|-------|-------|-------------|
| 4605435114 | Simics and Virtual Platform | fvcommon | Foundational overview — Simics vs VP definition |
| 4639114330 | Simics Domain Validation Strategy Guidance | fvcommon | 5-area FV domain strategy for Simics |
| 4605435116 | Motivation for Simics | fvcommon | Business case, NVL-S analysis, real-world examples |
| 3736864921 | Simics PythonSV SW-CI Framework Overview | fvcommon | CI pipeline (Bronze/Silver/Gold), AutoGen, import sheets |
| 3041035826 | Simics Virtual Platform Details | Simics | VP architecture details (timed out, partial) |
| 3844014084 | Altera Simics KM IP Model Types & Stakeholders | ITSpsgaet | Model taxonomy (5 types), stakeholder matrix |
| 2797523774 | Simics VP Ingredients | ITSpsgaet | 8 VP ingredients, build/packaging |
| 4661117246 | BKM for Simics VP device model auto-generating (AutoDML) | hyltxxsc | AI-driven 5-phase DML model generation |
| 1966867225 | Creating a Virtual Platform with Simics | SRESIMICS | Step-by-step platform VP creation |
| 4639109312 | RZL Virtual Platform Execution | fvcommon | SimLauncher setup, practical VP usage |
| 1249986926 | spi_xtor Operation Modes | PPA | SPI transactor modes, THC VTC connection |
| 1249986915 | spi_xtor Simics Interfaces | PPA | thc_vdm class definition, attributes |
| 1966866946 | Chassis Power Management Framework | SRESIMICS | PMC model, D-state transitions, LTR |
| 2710449321 | Simics Key Learnings | npgnseval | Debug techniques, HFPGA, BIOS overview |
| **1966867553** | **THC model development (WIP)** | **SRESIMICS** | **MTL TEP model attrs, reset_delay, HID descriptors, doze, MFS, mouse-to-touch, WA 1508517875** |
| **1966867456** | **THC Device Overview** | **SRESIMICS** | **Model capabilities (Reset/Interrupts/Registers/PM/LTR), unit test list, GPIO unimplemented known issue** |
| **2845164237** | **BKM THC I2C driver on LNL Simics** | **SRESIMICS** | **LNL I2C driver install, trigger_input_report, alps include files, DigiInfo validation** |
| **4045307441** | **BKM THC QuickI2C driver NVL-S Simics** | **SRESIMICS** | **NVL-S load-target, BIOS I2C values (addr=0xA, SCL HIGH=267/LOW=271), alps_touchscreen objects** |
| **1966867486** | **THC debugging with WinDbg on MTL Simics** | **SRESIMICS** | **Telnet-based kdcom-proxy debugging, port 12375, $windbg_enable=TRUE** |
| **3217199088** | **BKM THC HIDSPI & HIDI2C driver on PTL Simics** | **SRESIMICS** | **PTL I2C+SPI dual-mode, WA 16015917403, TEP (SPI) vs alps (I2C) objects** |
| **1966867128** | **BKM THC IPTS & HIDSPI driver on MTL Simics** | **SRESIMICS** | **IPTS/HIDSPI registry WAs, PEI_ASSERT HSDES 1508958117, mouse-to-touch** |
| **1433100579** | **THC Simics - Getting Started** | **IPTS** | **LKF era (obsolete Simics 5), architecture pattern: thc0 + tic00 + mem_space** |
| **1800325877** | **BKM QuickSPI (HIDSPI) on MTL Simics** | **IPTS** | **Simics base 6.0.71, DO NOT enable logging during touch test, FPGA_LCBE=1** |
| **1249985406** | **THC BAT Test** | **PPA** | **LKF FPGA PIO write/read validation, PIO offsets (+0x1040/1044/1048/104C), opcode 0x04/0x06** |
| **2364131531** | **PantherLake THC Gen 4.1 (PTL-PCD-P)** | **THCipsv** | **PTL PCRs: 15010734105 (16-bit port ID), 14016435572 (Simics shift-left for LPM)** |
| **1155001205** | **Monthly Knowledge Sharing - CSME/SPI/eSPI/THC** | **THCipsv** | **2018-2019 Penang sessions, Simics pkg install, low relevance** |
| **4605435102** | **Simics Phone Book & Queries** | **fvcommon** | **THC domain lead=William Chin, CVE Simics FRs via HSDES tags, QE tracking** |
| **3740545285** | **Quality Test plan - NVL FV** | **fvcommon** | **NVL FV test planning reference** |
| **1620643113** | **SPARK 1.11.x Release Notes** | **PPA** | **4 THC entries: 1508628560 (infinite loop fix), 14015253601 (I2C), 16018039801+16018045412 (HAS alignment)** |

### 18.2 Newly Discovered Wiki Pages (v2.4 Addition)

> **Discovered**: 2026-03-26 via CQL search across SRESIMICS, fvcommon, CVEValPlatforms, THCipsv, PPA, VICESW spaces.

| Page ID | Title | Space | Key Learnings |
|---------|-------|-------|---------------|
| **3986290848** | **THC Emulation** | **THCipsv** | **Maestro/HFPGA/SLN emulation framework, waveform capture, transactors.json, MiniBios.asm, RTL access groups, RZL/NVL doc links** |
| **4175342280** | **THC WCL BIOS knobs** | **fvcommon** | **WCL BIOS: Intel Advanced > Serial IO for THC0/1, Virtual Keyboard enable** |
| **4606212223** | **THC WCL Issues** | **fvcommon** | **6 WCL sightings: I2C 1MHz unstable, VKB delays, Sx cycling YB, WoT boot hang 0x9B0E, telemetry broken** |
| **3466824139** | **THC SPI - EV** | **IPMWiki** | **Max SPI freq 40MHz, timing specs at 42.67/32MHz, SPI opcodes per IO mode, Dragon automation** |
| **2761101312** | **THC PRD table in Maestro** | **VICESW** | **Deep PRD/DMA implementation: write/read DMA setup, SWDMA I2C WBC/DLEN_EN bits, PRD random test** |
| **3439922659** | **PTL Simics Setup** | **bnatarajan** | **Linux/Ubuntu setup, ISPM packages, project-setup, custom target scripts, automation json config** |
| **1933394613** | **PCR 22013186651: THC Frame Sync** | **THCipsv** | **Display sync GPIO/emulated/VW sources, timestamp FIFO, watermark interrupt, 5 test cases, D0i2 modes** |
| **3775412802** | **THC Pytest GIT Repo** | **THCipsv** | **IPSV test framework: github.com/intel-restricted/frameworks.validation.pythonsv.ipsv.thc, Sonora testcard, PMCLite vectors** |
| **3776881921** | **Pytest for THC (Manual)** | **THCipsv** | **Falcon pytest environment (D:\falcon\pytest), Config.py setup, debug scheduler** |
| **1249986913** | **spi_xtor Integration (WIP)** | **PPA** | **thc_vdm instantiation code, SPI opcode config per IO mode, simple_io_xtor for interrupts, VTC DEPRECATED in SPARK 1.11.7** |
| **2068317556** | **MTL PSS Session Setup Guide** | **IPTS** | **Linux VNC setup for Simics MTL, ISPM packages pkg-1000/1001/7500, CRT alternative** |
| **1498127969** | **IPTS Playbook** | **CPS** | **Historical driver versions THCBase 2.1.0.65-3.0.100.230, design wins (Surface/Lenovo/HP/ASUS), team transitions** |
| **2918220570** | **PM Enabling** | **fvcommon** | **S0ix THC disable: ThcAssignment_0/1=0x0, MTL/PTL Simics parity table, SVOS sleep commands** |
| **1693808060** | **RTL-Simics mappings SOC S** | **PPA** | **THC mapped to RTL in HFPGA (not Simics stub), GPIO config issue HSD 1307012183** |
| **4261389213** | **Debugging Simics Fuse Issues** | **SRESIMICS** | **Fuse controller sideband access, fusegen-tools.py decode/compare, CI isolation** |
| **4617015496** | **Hardware Setup (WIP)** | **PPA** | **NVL-S HFPGA: THC on mb2.C3, EM100Pro SPI flash 1.8V, power-on sequence** |
| **1249990578** | **TC - Getting Started** | **PPA** | **THC VTC migrated to Simics 6/Python 3, occasional support, thc_vdm is current test card** |
| **3556711840** | **Model 2: Min Boot + PCH IPs** | **PPA** | **NVL-S Model2: THC listed as RTL IP on PCH-S, production FW, WinOS boot target** |

---

## 19. Per-Platform THC Simics Operational Guide

> **Source**: Wiki pages 2845164237, 4045307441, 3217199088, 1966867128, 1966867553, 1433100579
> **Date studied**: 2026-03-26

### 19.1 THC Simics Object Path Evolution

The THC model object path **changes per platform**. This is critical for PythonSV namednode resolution.

| Platform | Gen | THC Object Path | Die Hierarchy | Source Page |
|----------|-----|----------------|---------------|-------------|
| **LKF** | 1.0 | `lkf.mb.sb.thc0` / `thc1` | `mb.sb` (southbridge) | 1433100579 |
| **MTL** | 3.0 | `mtl.mb.soc.thc0` / `thc1` | `mb.soc` (SoC) | 1966867553 |
| **LNL** | 4.0 | `lnl.mb.south.thc0` / `thc1` | `mb.south` (south complex) | 2845164237 |
| **PTL** | 4.1 | `$system.mb.south.thc0` / `thc1` | `mb.south` (south complex) | 3217199088 |
| **NVL-S** | 4.2 | `nvl.mb.pch.thc0` / `thc1` | `mb.pch` (PCH) | 4045307441 |
| **RZL** | 4.2 | `razorlake.mb.pch.thc0` / `thc1` (inferred) | `mb.pch` (PCH) | 4639109312 |
| **TTL** | 4.2 | **⚠️ UNKNOWN — must determine** | Likely `mb.pch` (same as NVL) | — |

**Key observation**: Hierarchy evolved `sb` → `soc` → `south` → `pch`. TTL must be verified before writing scripts.

#### RZL Platform Details (NEW — from page 4639109312)
- **SimLauncher**: `pip install devtools_launchers` → `simlauncher run razorlake-desktop-7 2026ww06.2.22_47 --cores 4 --memory 128 --disk 64 --mode vnc`
- **Boot**: `load-target razorlake-desktop/platform` (defaults to Windows + latest IFWI + 0F config)
- **Custom launch**: Python script (e.g., `svos_simics.py`) for SVOS or custom IFWI
- **Target guide**: `https://docs.intel.com/documents/vp_simulation/vp_release/7/razorlake-desktop/`
- **Working dir**: `/nfs/site/disks/simcloud_bjlagers_001/projects/razorlake-desktop-7/`
- **Gen4.2 THC**: Same as NVL/TTL — unified HAS `sip_thc_4x_has.html`

### 19.2 Platform Boot Commands (load-target)

| Platform | Protocol | Boot Command |
|----------|----------|-------------|
| **NVL-S** | I2C | `load-target nvl-s/platform touchscreen:enable=TRUE touchscreen:component=i2c` |
| **PTL** | I2C | `load-target ptl/ptl-p touchscreen:enable=TRUE touchscreen:component=i2c sw:disk:enabled=TRUE` |
| **PTL** | SPI | `$wa_16015917403_enable=TRUE` then `load-target ptl/ptl-p touchscreen:enable=TRUE touchscreen:component=ipts sw:disk:enabled=TRUE` |
| **MTL** | SPI | Simics pkg 7500 + base 1000 (no load-target, older launch method) |
| **LNL** | I2C | Simics pkg 7600 + base 1000, IFWI-based boot (HSDES 15012829359) |
| **TTL** | I2C | **⚠️ UNKNOWN** — likely `load-target ttl/platform touchscreen:enable=TRUE touchscreen:component=i2c` |

**Key patterns**:
- `touchscreen:enable=TRUE` — enables the touch device model
- `touchscreen:component=i2c` — I2C mode (alps_touchscreen model)
- `touchscreen:component=ipts` — SPI mode (TEP model)
- `sw:disk:enabled=TRUE` — enables disk image for OS boot
- PTL SPI requires explicit WA: `$wa_16015917403_enable=TRUE` (HSDES 16015917403)
- PTL target script also available as `ptl-m.chromeos.simics` for ChromeOS, with `handle_outside_memory=TRUE` (source: wiki 3439922659)
- **⚠️ ISH/THC1 GPIO mux conflict**: THC1 GPIO pins are shared with ISH — **ISH must be disabled** (`PchIshEnable=0x0`) when THC1 is active (source: BOM52 wiki 4501129290)

### 19.3 BIOS Setup for THC in Simics

All platforms use the same BIOS setup path:

**Navigation**: Boot → **F2** → Intel Advanced → PCH-IO Configuration → **THC Configuration**

#### I2C Mode BIOS Values (NVL-S reference):

| Field | NVL-S Value | Notes |
|-------|------------|-------|
| Mode | HID over I2C | Protocol selection |
| Device Address | `A` | 0x0A (ALPS touchscreen) |
| Connection Speed | `18A60` | 100,960 decimal (~101KHz) |
| Descriptor Address | `1` | HID descriptor register offset |
| SM SCL HIGH | `267` | Standard Mode I2C clock high period |
| SM SCL LOW | `271` | Standard Mode I2C clock low period |
| FM SCL HIGH | `0x5C` (92) | Fast Mode (400KHz) I2C clock high period (source: BOM52 wiki 4501129290) |
| FM SCL LOW | `0x9C` (156) | Fast Mode I2C clock low period |
| FMP SCL HIGH | `0x22` (34) | Fast-Plus (1MHz) I2C clock high period (source: BOM52 wiki 4501129290) |
| FMP SCL LOW | `0x26` (38) | Fast-Plus I2C clock low period |
| Addressing Mode | `1` | 7-bit I2C addressing (PTL BKM) |
| Remaining fields | `FFFF` | Leave as default (PTL BKM) |

> **⚠️ Speed Mode Mapping**: SM Connection Speed = `0x186A0` (100,960), FM = `0x61A80` (400,000), FMP = `0xF4240` (1,000,000). Source: BOM52 wiki 4501129290.

#### SPI Mode BIOS Values (PTL reference):

| Field | PTL Value | Notes |
|-------|----------|-------|
| Mode | HIDSPI | Protocol selection |
| Input Report Body Address | `0x1000` | HIDSPI input report body read address |
| Input Report Header Address | `0x0` | HIDSPI input report header address |
| Output Report Address | `0x1000` | HIDSPI output report write address |
| Write Opcode | `0x2` | SPI write command opcode |
| Read Opcode | `0xB` | SPI read command opcode |
| Limit Packet Size | `1` | Enable packet size limiting |

#### GPIO Unlock (Required for all modes):
Intel Advanced → PCH-IO → Security Configuration → **Force unlock on all GPIO pads → Enabled**

### 19.4 Touch Data Injection

#### SPI Mode (TEP model):
```
# Mouse-to-touch simulation (MTL):
connect mtl.recorder.tablet_out mtl.tep.tic00_as_abs_mouse
mtl.console.con->abs_pointer_enabled = TRUE
# Now mouse movements generate touch events
```

#### I2C Mode (alps_touchscreen model):
```
# Load include files first:
run-command-file alps0_input_report.include
run-command-file alps0_hid_report_descriptor.include
run-command-file alps0_hid_device_descriptor.include

# Trigger touch event:
<platform>.mb.<die>.thc0->trigger_input_report = TRUE
# Change coordinates in include file for different positions
# X=0x1795, Y=0x1537 (little-endian 16-bit format)
```

**⚠️ I2C LIMITATION**: Mouse cursor simulation does NOT work for I2C mode (only SPI). Must manually set X/Y coordinates in the include file and trigger each report individually.

### 19.5 File Transfer to Simics Guest

Two methods available:
1. **FTP**: `ftp://192.168.1.1` from within the Simics guest OS
2. **Simics Agent**: `$matic0.upload <host_path> <guest_path>` / `$matic0.download <guest_path> <host_path>`

---

## 20. Touch Device Model Architectures

> **Source**: Wiki pages 1966867553, 4045307441, 3217199088, 1249986915
> **Date studied**: 2026-03-26

Two completely different touch device model types exist depending on protocol:

### 20.1 SPI Mode: TEP (Touch EndPoint) Model

Used for HIDSPI/QuickSPI protocol simulation.

**Platforms**: MTL, PTL (SPI mode)

**Object path**: `<platform>.tep.tep00` (THC0) / `<platform>.tep.tep10` (THC1)

**Key attributes**:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `reset_delay` | float | 0.2 | Reset delay in seconds (200ms) |
| `bulk_addr_read` | uint32 | 0x1000 | HID report bulk read address |
| `bulk_addr_write` | uint32 | 0x1000 | HID report bulk write address |
| `hid_report_descriptor_data` | tuple | — | 9-byte header + 3-byte padding + 2596-byte descriptor |
| `doze_enable` | bool | FALSE | If FALSE, doze enter/exit interrupts are ignored |
| `test_mfs` | uint32 | 0x9b1 | Max Frame Size (⚠️ wiki source value; description "8 + descriptor_size(2600) + ReadDataHdr(64)" = 2672 ≠ 0x9B1=2481 — discrepancy in original wiki, value likely correct) |
| `trigger_input_report` | bool | — | Set TRUE to trigger touch data delivery via DMA |
| `wa_ignore_setidvalue` | bool | FALSE | WA for HSDES 1508517875 SetIDValue assertion |

**Architecture**: TEP handles HIDSPI protocol framing internally. Connected to THC via spi_xtor transactor.

**Mouse simulation**: Supported via `connect <platform>.recorder.tablet_out <platform>.tep.tic00_as_abs_mouse`

### 20.2 I2C Mode: alps_touchscreen Model

Used for HIDI2C/QuickI2C protocol simulation.

**Platforms**: LNL, PTL (I2C mode), NVL-S

**Object path**: `<platform>.alps_touchscreen0` (THC0) / `<platform>.alps_touchscreen1` (THC1)

**Key attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `trigger_input_report` | bool | Set TRUE to trigger touch data delivery |

**Data injection**: Via include files that define raw report bytes:
- `alps0_input_report.include` — touch coordinate data
- `alps0_hid_report_descriptor.include` — HID report descriptor
- `alps0_hid_device_descriptor.include` — HID device descriptor

**Architecture**: Connected to THC via i3c_xtor with I2C compatibility mode. Does NOT use spi_xtor.

**Mouse simulation**: ❌ NOT supported. Must manually edit X/Y coordinates in include files.

### 20.3 Model Architecture Comparison

```
SPI Path:  [THC Model] ↔ [spi_xtor] ↔ [TEP / thc_vdm]
I2C Path:  [THC Model] ↔ [i3c_xtor] ↔ [alps_touchscreen]
```

| Feature | TEP (SPI) | alps_touchscreen (I2C) |
|---------|-----------|----------------------|
| Mouse simulation | ✅ Yes | ❌ No |
| Protocol framing | Internal | Via include files |
| Reset delay config | ✅ Configurable | ❌ Not documented |
| HID descriptor | Attribute-based | Include file |
| MFS configuration | ✅ `test_mfs` attribute | ❌ Not documented |
| Doze support | ✅ `doze_enable` attribute | ❌ Not documented |

**⚠️ TTL Impact**: Since TTL targets I2C mode, the `alps_touchscreen` model is the relevant architecture. No mouse simulation — all touch testing requires manual coordinate injection via include files.

---

## 21. Driver Installation & Workarounds in Simics

> **Source**: Wiki pages 1966867128, 1800325877, 2845164237, 4045307441, 3217199088
> **Date studied**: 2026-03-26

### 21.1 Common Prerequisites

1. **Test signing**: Required for unsigned drivers in Simics
   ```cmd
   bcdedit /set testsigning on
   bcdedit /set nointegritychecks on
   ```
2. **File transfer**: Copy driver package via FTP (`ftp://192.168.1.1`) or Simics agent (`$matic0.upload`)
3. **Install**: Device Manager → Update Driver → Browse → Select .inf file

### 21.2 Protocol-Specific Registry Workarounds

| Driver | Registry Path | Key | Value | Purpose | Source |
|--------|-------------|-----|-------|---------|--------|
| IPTS | `HKLM\SOFTWARE\Intel\IPTS` | `ResetIntrDelayUs` | `0` (DWORD) | Disable reset interrupt delay | 1966867128 |
| HIDSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `FPGA_LCBE` | `1` (DWORD) | FPGA/Simics workaround | 1966867128, 1800325877 |
| HIDSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `ReadReportDescriptorOnReset` | `1` (DWORD) | Force descriptor re-read after reset | 1966867128 |
| QuickSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `FPGA_LCBE` | `1` (DWORD) | Same as HIDSPI | 1800325877 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `ResetDelayMs` | configurable (DWORD) | Override reset delay | 1966867553 |
| QuickI2C | — | — | — | No registry WAs documented | 4045307441 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `TxDMA_Override` | `1` (DWORD) | Force PIO instead of TxDMA for output reports | 1355098344 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `IO_Mode_Override` | `0/1/2` (DWORD) | Override SPI IO mode: 0=Single, 1=Dual, 2=Quad | 1355098344 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `SPI_Frequency_Override` | (DWORD) | Override SPI clock frequency | 1355098344 |

### 21.3 Known Simics-Specific HSDES Sightings

| HSDES | Description | Workaround | Platform |
|-------|-------------|------------|----------|
| **1508517875** | SetIDValue assertion in THC model | `thc0->wa_ignore_setidvalue = TRUE` | MTL |
| **1508958117** | PEI_ASSERT with default BIOS on Simics | Use updated IFWI | MTL |
| **16015917403** | SPI mode broken on PTL Simics without WA | `$wa_16015917403_enable = TRUE` before load-target | PTL |
| **15012829359** | LNL Simics IFWI version tracking | Use IFWI_LNL_M_Internal_2074.00_Dispatch_VS_DEBUG_PreProd_Simics.bin | LNL |
| **16028137599** | **Windows QuickI2C driver DROPPED from NVL and future platforms** | Use Ubuntu with built-in QuickI2C kernel driver (POR). WinOS requires manual INF install if needed | NVL+ |
| **1307012183** | GPIO of THC device not configured correctly | Simics GPIO model limitation (ADL-era, may persist) | ADL |

### 21.4 Driver Versions Used in Simics (Historical)

| Platform | Driver | Version | Source |
|----------|--------|---------|--------|
| MTL | IPTS | v3.0.0.252 | 1966867128 |
| MTL | HIDSPI | v1.0.0.41 | 1966867128 |
| MTL | QuickSPI (HIDSPI) | Debug_MSI version | 1800325877 |
| LNL | HIDI2C Touch | v5.0.4000.693 | 2845164237 |
| NVL-S | IntelQuickI2C | v5.5.0.7 or v5.5.0.10 | 4045307441, 4501129290 |
| NVL-Hx | WoT_QuickI2cExtension | (separate INF for WoT) | 4501129290 |
| PTL | HIDSPI + HIDI2C | (version not specified) | 3217199088 |

### 21.5 Simics-Specific Driver Installation Notes

- **Do NOT enable verbose logging during touch test** — causes timing delays that result in touch data loss (source: 1800325877)
- **Log level for debug**: `.log-level 4 -r` enables full debug logging on Simics model (source: 4045307441)
- After driver install, **reboot may be required** before touch device appears in Device Manager
- Touch validation tool: **DigiInfo** from Microsoft — shows real-time touch packets (source: 2845164237)
- MS Paint test: Inject 3x `trigger_input_report=TRUE`, then change packet byte `0x05→0x04` for finger-up event

### 21.6 WCL-Specific BIOS Configuration

> **Source**: Wiki page 4175342280
> **Date studied**: 2026-03-26

- **BIOS path**: Intel Advanced → Serial IO Configuration → THC0/THC1
- **Virtual Keyboard**: Boot Maintenance Manager → Boot Configuration → Enable Virtual Keyboard = **Enabled**
- **Key Learning**: WCL requires explicit Virtual Keyboard enable for pre-OS touch input

### 21.7 S0ix THC Disable Procedure

> **Source**: Wiki page 2918220570
> **Date studied**: 2026-03-26

To disable THC for S0ix power management testing:

1. **BIOS Setup**: THC Configuration → THC Port Configuration → **\<None\>** (disables THC port)
2. **xmlcli Knobs**: `ThcAssignment_0=0x0` and `ThcAssignment_1=0x0` (both set to None)
3. **MTL/PTL Simics parity**: MTL has XDP/USB2DBC debug; PTL Simics has no debug connection, no display (VGA)
4. **SVOS sleep command**:
   ```bash
   echo s2idle > /sys/power/mem_sleep
   echo mem > /sys/power/state
   ```

### 21.8 IPTS Program History (Design Wins & Milestones)

> **Source**: Wiki page 1498127969 (IPTS Playbook, v43)
> **Date studied**: 2026-03-26

- **Driver version evolution**: THCBase 2.1.0.65 → 3.0.100.230, Filter 3.1.0.50 → 3.1.0.57, HSPI 4.0.x.x
- **Platforms covered**: TGL-H/R, ADL-P/M/SBGA, RPL, MTL-P/M
- **Design wins**: MSFT Surface, Lenovo Lark, HP Solaris, ASUS
- **Team transition**: IDC → ISH (Intel Shanghai)
- **Pathfinding**: HIDSPI convergence, Test Endpoint, Remote Execution, Touch over LCH, E2E Latency

---

## 22. THC Simics Debugging

> **Source**: Wiki pages 1966867486, 1249985406, 1800325877
> **Date studied**: 2026-03-26

### 22.1 WinDbg Kernel Debugging over Telnet

From MTL Simics BKM (page 1966867486):

1. **Enable WinDbg in Simics script**: `$windbg_enable = TRUE`
2. **Default telnet port**: 12375
3. **Get target IP**: `sim->host_ipv4` in Simics console
4. **Host setup**: Create `C:\WinSymbols` folder for symbol cache
5. **Launch proxy**: Use `kdcom-proxy.exe` from Simics base package
6. **Boot**: Select **'Debug enabled'** in Windows boot menu — do NOT start Windows normally
7. **Connect WinDbg**: Standard kernel debugging session over telnet→kdcom proxy

### 22.2 Simics Model Debug Commands

| Command | Purpose |
|---------|---------|
| `.log-level 4 -r` | Enable full debug logging (level 4) recursively |
| `<thc_obj>->trigger_input_report = TRUE` | Manually trigger a touch input report |
| `<thc_obj>->wa_ignore_setidvalue = TRUE` | Enable SetIDValue workaround |
| `<tep>->doze_enable = FALSE` | Disable doze interrupts |
| `<tep>->reset_delay = 0.2` | Set reset delay (seconds) |
| `run-command-file <path>.include` | Load touch data/descriptor include file |
| `connect <recorder> <tep_mouse>` | Enable mouse-to-touch simulation (SPI only) |

### 22.3 ETL/WPP Trace Capture

From THC BAT Test BKM (page 1249985406):
- Use `ThcTrace.cmd` for WPP trace capture
- Captures driver-level trace events during touch operations
- For WPP GUIDs, see debug sub-skill: HIDSPI `{A891081A...}`, HIDI2C `{C47236A7...}`

### 22.4 PIO Validation in Simics

From THC BAT Test (LKF FPGA era, page 1249985406):

PIO register offsets from BAR0 base (per-port):
| Register | Offset | Purpose |
|----------|--------|---------|
| `THC_SS_CMD` | +0x1040 | PIO command register |
| `THC_SS_BC` | +0x1044 | PIO byte count |
| `THC_SS_DIN` | +0x1048 | PIO data in (read data) |
| `THC_SS_CD` | +0x104C | PIO command data (write data) |

PIO Write sequence: BAR setup (0x91400000) → cmd enable (0x6) → write data to +0x104C → trigger PIO via +0x1040/+0x1044/+0x1048

**Note**: LKF-era offsets. Current platforms use offset base +0x1000 for port 0 registers. Verify against HAS for TTL.

---

## 23. SPARK Transactor THC Support History

> **Source**: SPARK 1.11.x release notes (page 1620643113), analyzed by sub-agent
> **Date studied**: 2026-03-26

SPARK (Simics Platform Architecture Kit) provides the I/O-level transactors that connect THC device models to touch VDMs.

### 23.1 THC-Related SPARK Releases

| SPARK Version | HSDES | Type | Xtor | Description | Platform |
|---------------|-------|------|------|-------------|----------|
| **1.11.5** | 1508628560 | Bug Fix | spi_xtor | **Infinite loop in THC module when paired to spi_xactor_flash device** | MTL-S |
| **1.11.8** | 14015253601 | New Feature | i3c_xtor | **Enhanced device xtor to support THC using I2C** | General |
| **1.11.11** | 16018039801 | New Feature | i3c_xtor | **I2C xtor requirement aligned with THC HAS** | General |
| **1.11.11** | 16018045412 | New Feature | spi_xtor | **Touch device VDM + HIDSPI support per THC HAS** | General |

### 23.2 Evolution Phases

- **Phase 1 (SPARK 1.11.5)**: Bug fix for existing SPI-mode THC on MTL-S — critical infinite loop resolved
- **Phase 2 (SPARK 1.11.8)**: I2C support added to i3c_xtor — HIDI2C protocol enablement
- **Phase 3 (SPARK 1.11.11)**: Both I2C and SPI xtors formally aligned to THC HAS — full protocol compliance

### 23.3 Key Architecture Notes

- **SPI path**: `spi_xtor` → `thc_vdm` (C++ class)
- **I2C path**: `i3c_xtor` with I2C compatibility mode → `alps_touchscreen`
- `thc_vdm` attributes: `spi_host_obj`, `mem_space`, `touch_int_cause`, `tc_control`, `ramless_datamode_ctrl`, `int_trigger`
- **NOT in SPARK**: `TEP`, `alps_touchscreen`, `tic00` — these are in **platform-specific model repos**, not in SPARK
- SPARK 1.11.x was EOL'd; newer platforms (NVL, TTL) likely use SPARK 1.12.x or later

### 23.4 Minimum SPARK Version for THC

| Protocol | Minimum SPARK | Reason |
|----------|---------------|--------|
| HIDSPI (SPI) | ≥ 1.11.11 | VDM + HIDSPI support per HAS (16018045412) |
| HIDI2C (I2C) | ≥ 1.11.8 (basic), ≥ 1.11.11 (HAS-aligned, recommended) | 1.11.8 first added I2C support (16018039801); 1.11.11 aligned both xtors with HAS |
| Any (basic) | ≥ 1.11.5 | Infinite loop fix (1508628560) |

---

## 24. CVE Simics Organizational Structure

> **Source**: Wiki page 4605435102 (Simics Phone Book)
> **Date studied**: 2026-03-26

### 24.1 THC Simics Domain Lead

**William Chin** (`willychi`) — CVE FV THC Simics Domain Lead

### 24.2 Adjacent Domain Leads

| Domain | Lead | Notes |
|--------|------|-------|
| NVU | Bee Koon Lee | Neural Vision Unit |
| LPSS | Kong Jia Wen | Low Power Subsystem |
| ISH | Leem Yi Jie | Integrated Sensor Hub |
| USB | Nagalakshmi Ganta | USB/xHCI |
| Audio | Siva Balasundram | HDA/SoundWire/DSP |
| South PM | Jesse Dickinson / Kedar Kulkarni | Power Management |

### 24.3 Program Tracking Mechanisms

| Mechanism | Description | HSDES Tag |
|-----------|-------------|-----------|
| **Functional Requirements (FRs)** | Simics model requirements filed by FV domains | `CVE_Simics_TTL`, `CVE_Simics_NVL`, `CVE_Simics_RZL` |
| **Quality Events (QEs)** | Bugs found on silicon that SHOULD have been found in Simics | (per project tracking page) |
| **Sightings** | Simics model bugs | NVL Simics Sightings page |

### 24.4 Key Contacts (THC Simics Model)

From THC Device Overview (page 1966867456):

| Role | Name | Notes |
|------|------|-------|
| PM | Ling Yue | Program Manager |
| SW Architect | Even Xu | Also Linux kernel THC author |
| IPTS Engineer | Xinpeng Sun | Also Linux kernel THC author |
| Validation | Chong Han | Model validation |
| HIDSPI Architect | Sai Prasad | SPI protocol expert |
| HIDSPI Engineer | Kruthi Murali | SPI implementation |
| HIDSPI PM | Mike Tran | SPI program management |

### 24.5 PTL PCRs with Simics Impact

From page 2364131531:

| HSDES | Priority | Description | Relevance |
|-------|----------|-------------|-----------|
| **14016435572** | — | OSXML and HAS updates for SIMICS Shift-Left for LPM Validation | **Directly relevant** — Simics shift-left for PM validation |
| **15010734105** | High | IP to support 16-bit port ID endpoint | Breaking change on PTL+ (matches known HSDES) |
| **22014732835** | — | Enable customer to use ODLA to debug THC IO signals (SPI/I2C/INTR) | Debug capability enhancement |
| **16015843747** | Medium | WA Carry Forward: Resource own req↔Ack Violation | Model workaround |
| **14016605173** | High | Fuzz test IP interfaces (Security) | Security testing |

---

## 25. THC Emulation — Maestro / HFPGA / SLN Framework

> **Source**: Page 3986290848 (THC Emulation, v16, THCipsv)
> **Learning**: THC validation extends beyond pure Simics VP — the Maestro/HFPGA path provides RTL-accurate validation with real silicon logic.

### 25.1 Emulation vs. Simulation

| Aspect | Simics (VP) | Maestro (HFPGA) |
|--------|-------------|-----------------|
| **Model type** | Software functional model | RTL on FPGA fabric |
| **Accuracy** | Register-functional | Cycle-accurate (RTL) |
| **Speed** | Fast (~MIPS) | Slower (~KHz-MHz) |
| **THC mapping** | thc_vdm + platform model | Real THC RTL on HAPS |
| **Use case** | SW bring-up, driver debug | HW validation, timing, PM |

### 25.2 Maestro Setup for THC

```bash
# Access groups required
wash -n intelall soc sle ipval phdk73rtl ebg tgp mtl ptlpcd ptlsoc chipsetval1 nvlpcd nvlpch nvlsoc

# Environment setup
setenv LM_PROJECT DDG-TGL
setenv MAESTRO_FRAMEWORK UNIFIED
source setup.env
source perspec/scripts/environment/vice_setup.env

# Generate test objects
perspec generate -f perspec/targets/pch_sa/nvl_pcdh/pch.psf -sln <path> -top_action <action>

# Build
gmake TAGS=nvl.sle PLAT=<Platform.bl> -Bj 32

# Job status
nbstatus jobs --target fm_zse
```

### 25.3 VTC Limitations

> **Source**: Page 3986290848 (THC Emulation, v16)

- **pcd_thc_simics** VTC has **NO OWNER** — limited maintenance
- VTC status: **"Occasional support"** — migrated to Simics 6 / Python 3 but not actively developed (source: TC Getting Started page 1249990578)
- Cannot test HIDSPI or HIDI2C end-to-end flows (SPI-only, basic)
- For full protocol testing, use thc_vdm + spi_xtor (SPI) or alps_touchscreen + i3c_xtor (I2C)

### 25.4 THC in HFPGA

- THC controllers are **RTL-mapped** in HFPGA (NOT Simics stubs) — confirmed for ADL, NVL-S
- Touch endpoints (tic00/tic10) also RTL-mapped
- SPI controllers (spi0-6) are Simics-mapped for speed
- THC is listed as RTL IP in NVL-S Model2 config (alongside ACE, USB, ISH, LPSS)
- THC FW = Production in Model2

### 25.5 Waveform Capture for THC

- Use `zprd` + `tardis` switches in csh for waveform capture
- FSDB group: `pch_thc`
- Signal probes defined in: `pch_probes_thc_fwc.v`
- `transactors.json` contains THC transactor version
- `pch_thc_xtor.sv` defines signal connections

### 25.6 Key Configuration Files

| File | Purpose |
|------|---------|
| `transactors.json` | THC transactor version selection |
| `pch_thc_xtor.sv` | Signal connections between THC RTL and transactor |
| `Platform.bl` | Device IDs (differ per project), MMIO BAR for THC |
| `MiniBios.asm` | MMIO BAR for THC — **must match Platform.bl** |
| `pch_probes_thc_fwc.v` | Waveform signal list for THC |
| `pcd_run_dir_ovrd` | Side model overrides (copy + edit paths) |

### 25.7 Key Repos

| Repo | Purpose |
|------|---------|
| `github.com/intel-innersource/frameworks.validation.emulation.sln-and-testlist-repo` | SLN test lists |
| `github.com/intel-restricted/frameworks.validation.maestro.maestro` | Maestro framework |

### 25.8 Reference Documentation Links (from page)

- **RZL BDF**: `docs.intel.com/documents/ClientSilicon/RZL/global/RZL_PCD_Addr_BDF_DID_HAS/`
- **RZL GPIO**: `docs.intel.com/documents/pch_doc/RZL/RZLPCDH/HAS/Chap18_RZL_GPIO/`
- **NVL IOSF SB**: `docs.intel.com/documents/pch_doc/NVL/PCD-S/HAS/Chap41_NVL_PCD_IOSF_Sideband/`
- **NVL PSF**: `docs.intel.com/documents/pch_doc/NVL/PCD-S/HAS/Chap07_NVL_PCD_PSF/`

---

## 26. WCL Known Issues & Sightings

> **Source**: Page 4606212223 (THC WCL Issues, v6, fvcommon)
> **Learning**: WCL brought several new THC issues, especially around I2C speed stability, WoT, and telemetry.

### 26.1 WCL Sighting Summary

| HSDES | Issue | Root Cause | Fix/Workaround |
|-------|-------|-----------|----------------|
| **16027559981** | YB on THC0/THC1 I2C at 1 MHz | 1 MHz I2C speed instability | Lower to 100 KHz or 400 KHz |
| **16027560205** | VKB delayed response in pre-OS (SM/FM/FMP) | BIOS I2C speed optimization needed | BIOS update |
| **16027746325** | I2C HID touchpad YB during Sx cycling | PM issue during sleep transitions | Under investigation |
| **16027810168** | POST code stuck 0x9B0E when enabling WoT in BIOS | WoT BIOS implementation issue | Disable WoT in BIOS |
| **16027836554** | Telemetry counters always reading 0 | Telemetry broken | Under investigation |
| **16027877982** | THC0 telemetry counters not incrementing | Same root cause as above | Under investigation |

### 26.2 Key Learnings from WCL

1. **I2C 1 MHz is unstable on WCL** — always validate lower speeds first (100K, 400K)
2. **WoT can cause boot hang** (POST code 0x9B0E) — critical regression gate for WoT testing
3. **Telemetry is broken** — cannot rely on HW counters for performance analysis on WCL
4. **Sx cycling exposes PM issues** — I2C touchpad YB during Sx cycling suggests save/restore or re-init problems

---

## 27. Display Sync / Frame Sync Validation

> **Source**: Page 1933394613 (PCR 22013186651 THC Frame Sync, v4, THCipsv)
> **Learning**: Frame sync / display sync is a complex feature with multiple sources and a dedicated timestamp FIFO.

### 27.1 Display Sync Event Sources

| DISP_SYNC_EVT_SRC | Value | Description |
|--------------------|-------|-------------|
| Disabled | 0 | No display sync |
| Emulated | 1 | Timer-based emulation (10 µs/step, min 2 ms, max 100 ms) |
| TCON GPIO | 2 | External GPIO from display timing controller |
| Virtual Wire (VW) | 3 | Sideband virtual wire |

### 27.2 GPIO Mode Configuration

| DISP_SYNC_GPIO_MODE | Value | Trigger |
|---------------------|-------|---------|
| Rising edge | 0 | Rising edge |
| Falling edge | 1 | Falling edge |
| Both edges | 2 | Both edges |
| Reserved | 3 | Do not use |

### 27.3 Timestamp FIFO

- **SYNC_TS_LOG_BUF_x**: FIFO array with indices 0..DEPTH-1 (16 entries)
- **SYNC_TS_LOG_RDPTR**: 5-bit SW-managed read pointer
- **SYNC_TS_LOG_WRPTR**: 5-bit HW-managed write pointer
- **SYNC_TS_LOG_INTR_WM**: 4-bit watermark for almost-full interrupt

### 27.4 D0i2 Interaction

- **Mode 0**: Timestamp counter continues across D0i2 transitions
- **Mode 1**: Timestamp counter resets to 0 on D0i2 exit
- **CRITICAL**: Emulated timer MUST be disabled before entering D0i2

### 27.5 Validation Test Cases (from PCR)

| TC | Description | Key Checks |
|----|-------------|------------|
| TC1 | GPIO source + FIFO sampling | Watermark interrupt, FULL interrupt |
| TC2 | Emulated source | Timer period accuracy, emulation start/stop |
| TC3 | VW source | Virtual wire reception, FIFO capture |
| TC4 | FIFO wraparound | Different read/write pointer offsets |
| TC5 | Concurrency with timestamp PCR | Simultaneous DMA + display sync |

### 27.6 Lab Contacts

- IP FPGA owner: Ban Poh Wei
- Content owner: Chin Xian Hin (Mike Jr), Tan Hooi Jing

---

## 28. THC IPSV Test Framework

> **Source**: Pages 3775412802 (THC Pytest GIT Repo, v4) and 3776881921 (Pytest for THC Manual, v3)
> **Learning**: There are TWO separate THC test repos — IPSV (pre-silicon/emulation) and PSV (post-silicon).

### 28.1 IPSV vs PSV Test Repos

| Aspect | IPSV Repo | PSV Repo |
|--------|-----------|----------|
| **URL** | `github.com/intel-restricted/frameworks.validation.pythonsv.ipsv.thc` | `github.com/intel-restricted/frameworks.validation.pythonsv.projects.novalake/vjt/thc` |
| **Target** | Pre-silicon (Simics, HFPGA, emulation) | Post-silicon (real hardware) |
| **Framework** | Pytest (Falcon) | PythonSV + NGA |
| **Entry point** | `main.py` (launcher + ITP init + mode select) | Test scripts called via NGA |

### 28.2 IPSV Repo Structure

```
main.py              # Launcher, ITP init, mode select
BAT.py               # BAT config
HIDSPI_BAT.py        # HIDSPI BAT config
HIDI2C_BAT.py        # HIDI2C BAT config
IPTS_BAT.py          # IPTS BAT config
pytest.ini           # Pytest configuration
setup.py             # Package setup
requirement.txt      # Dependencies
GENERIC/             # BDF autodetect, mem_read/write utilities
ITP_IPCCLI/          # ITP configuration
HIDI2C/              # HIDI2C_TOP.py + REG.py
HIDSPI/              # HIDSPI_TOP.py + REG.py
PMC/                 # PMCLite functions, compiler, vectors
PMCLite_Vector/      # Stable vectors organized by project/milestone/ww
SONORA/              # Sonora2+3 testcard TOP + REG
```

### 28.3 Running IPSV Tests

```bash
# Activate Falcon pytest virtual environment
D:\falcon\pytest\Scripts\activate

# Run tests
cd ..\src\<package>
pytest -sv <test_file>
```

### 28.4 Key Testcard Support

| Testcard | Protocol | Framework |
|----------|----------|-----------|
| **Sonora 2/3** | SPI | IPSV (`SONORA/`) |
| **PMCLite** | Sideband | IPSV (`PMC/`, `PMCLite_Vector/`) |
| **HIDSPI** | SPI | IPSV (`HIDSPI/`) |
| **HIDI2C** | I2C | IPSV (`HIDI2C/`) |

---

## 29. S0ix PM Enabling & THC Disable

> **Source**: Page 2918220570 (PM Enabling, v20, fvcommon)
> **Learning**: THC must be DISABLED for clean S0ix testing. Specific BIOS knobs and xmlcli commands documented.

### 29.1 THC Disable for S0ix Testing

**BIOS Method**: Intel Advanced → THC Configuration → THC Port Configuration → `<None>` (disable both ports)

**xmlcli Method**:
```
ThcAssignment_0=0x0    # None (disable THC0)
ThcAssignment_1=0x0    # None (disable THC1)
```

### 29.2 S0ix Failure: THC0 Primary Function Dependency

> **Source**: Page 4200761602 (WCL THC BKM, v12)

**⚠️ CRITICAL**: THC0 is the PCI bus **primary function** (Function 0). If only THC1 (e.g., trackpad) is configured:
- THC0 remains enabled without a driver binding
- THC0's PCI power state becomes **uncontrollable** (stuck in D0)
- This **blocks S0ix entry** for the entire platform

**Implication**: During validation, **both THC ports must be configured** (or both disabled) for S0ix testing. Never configure THC1 alone.

**OEM Note**: OEM designs may reverse the RVP assignment (THC0=touchpad, THC1=touchscreen). Validate per-platform BOM.

### 29.3 Full S0ix Disable List (for clean baseline)

All of these IPs must be disabled for a clean S0ix baseline test:
- iGFX, VMD, GNA, NPU, SATA, HDAudio, **THC**, all SerialIO, ISH, LAN

### 29.4 SVOS Sleep Commands

```bash
echo s2idle > /sys/power/mem_sleep
echo mem > /sys/power/state
```

### 29.5 MTL vs PTL Simics Parity

| Feature | MTL Simics | PTL Simics |
|---------|-----------|-----------|
| Debug | XDP, USB2 DBC | No debug connection |
| Network | GbE available | `network:enable_gbe=FALSE` |
| Display | VGA available | No display (VGA) |

---

## 30. SPI Electrical Validation Reference

> **Source**: Page 3466824139 (THC SPI EV, v8, IPMWiki)
> **Learning**: Platform SPI max freq is 40 MHz (signal integrity limit), not the IP max of 125 MHz.

### 30.1 SPI Electrical Specs

| Parameter | Value |
|-----------|-------|
| **Max SPI frequency (platform)** | 40 MHz |
| **Voltage** | 1.8V |
| **IO Modes** | Single, Dual, Quad |

### 30.2 SPI Opcodes per IO Mode

| Mode | Write Opcode | Read Opcode |
|------|-------------|-------------|
| **Single (1-1-1)** | 0x02 | 0x0B |
| **Dual (1-2-2)** | 0xB2 | 0xBB |
| **Quad (1-4-4)** | 0xE2 | 0xEB |

### 30.3 EV Test Phases

| Phase | Scope | Units |
|-------|-------|-------|
| **PO** | Register + recipe check + interface enable + SIV spot | — |
| **Ax** | Broad (5 units) + worst-case (5 VT corners) | 10 |
| **Deep** | ±3σ qualification | 12 |

### 30.4 Equipment & Tooling

- **Scope**: MSO9254A (2.5 GHz)
- **Probes**: N2496A
- **Positioner**: E2654A
- **Automation**: Dragon (`github.com/intel-restricted/frameworks.validation.wideband-io.flows`)

### 30.5 Contacts

- Arturo Bolanos Cortes, Juan Luis Lopez Padilla (SPI EV team)

---

## 31. PRD/DMA Maestro Implementation Details

> **Source**: Page 2761101312 (THC PRD maestro, v1, VICESW)
> **Learning**: Detailed PRD ring implementation for emulation environment — critical for understanding DMA data path validation.

### 31.1 Write DMA (TXDMA) PRD

- Single PRD table
- Max 256 KB entries
- Uses `StaticMem` API for allocation
- Setup: `SetupDmaWritePRD(numBytes, iocMode, numFrags)`

### 31.2 Read DMA (RXDMA) PRD

- Circular buffer of up to **128 PRD tables** (configurable via `THC_M_PRT_RPRD_CNTRL.PCD`)
- Each table has same entry count
- Max **256 entries per table** (for 1 MB at 4 KB fragmentation)
- Setup: `SetupDmaReadPRD(engine, numFrames, minFrags, iocMode, maxFrags)`

### 31.3 PRD Random Test Methodology

- `DescribeTable()` generates random fragment sizes
- Max fragment size = 2× average
- `StaticRand::Range()` for size generation
- Shuffle fragments to avoid ordering bias

### 31.4 PRD Field Access by Agent

| Field | SW Write | HW Consume | HW Update | SW Read |
|-------|----------|-----------|-----------|---------|
| **Length** | Yes | Yes | Yes (RXDMA) | Yes |
| **EOP** | N/A (TX) / Yes (RX) | Yes | Yes (RX) | Yes |
| **IOC** | Yes | Yes | No | No |
| **DestAddr** | Yes | Yes | No | No |
| **HW Status** | Clear | No | Yes | Yes |

### 31.5 HIDI2C SWDMA Special Fields

| Field | Bits | Description |
|-------|------|-------------|
| **THC_SWDMA_I2C_WBC** | 31:26 | Write byte count (1–64 bytes) |
| **THC_SWDMA_I2C_RX_DLEN_EN** | 23 | Descriptor vs device length mode |

**DLEN_EN usage**:
- `DLEN_EN=0`: Use PRD length field — for HID/Report descriptor retrieval

### 31.6 HIDI2C SWDMA Operational Notes

- **Write phase** uses PIO Data registers (not DMA buffer)
- **SW DMA and PIO shall NOT run simultaneously** — hardware does not arbitrate between them
- **Reset descriptor**: 2-byte length field = 0 (transparent to HW, triggers device reset)
- **Input report**: Device sends 2-byte length prefix; DLEN_EN=1 tells THC to use device-reported length
- `DLEN_EN=1`: Use device's 2-byte length field — for Get_Report/Idle/Protocol

---

## 32. Fuse Debugging for THC

> **Source**: Page 4261389213 (Debugging Simics Client Fuse Issues, v2, SRESIMICS)
> **Learning**: Fuses populate THC device registers at boot. Fuse issues can cause THC to not appear or misconfigure.

### 32.1 Fuse Architecture

- Fuse controller accessible via sideband (GPSB/PMSB)
- Fuses populate IP device registers at boot time
- THC fuse attributes accessible via: `<platform>.mb.hub.fuse` → `fuse_<ip>_<name>`

### 32.2 Debug Flow

1. Check fuse attribute on device model
2. Capture payload from Simics log
3. Decode with `fusegen-tools.py`
4. Compare old vs new fuse patches

### 32.3 fusegen-tools.py Commands

```bash
# Import text blob for analysis
fusegen-tools.py --import_text_blob <file>

# Compare two fuse patches
fusegen-tools.py --compare_patch <old> <new>

# Print fuse statistics
fusegen-tools.py --print_fuse_stats
```

### 32.4 fusegen XML Fields

| Field | Description |
|-------|-------------|
| `IOSFSBEP` | IOSF sideband endpoint |
| `IOSFSBPortID` | Sideband port ID |
| `RamAddr` | RAM address for fuse data |
| `FuseDefaultValue` | Default value when fuse not blown |

### 32.5 CI Debugging Tip

Comment out IP fuse groups to isolate fuse-related boot failures. Test incrementally to identify which IP's fuses are causing issues.

---

## 33. Requirements Gap Analysis (G1-G37)

> **Source**: Cross-reference of Pre-Silicon High-level Strategy document (10 lines) + 47 wiki pages against THC_Simics_PreSi_Requirements.md v2.4
> **Date studied**: 2026-03-26 (iteration 2 — expanded from 29 to 47 wiki pages)

### 33.1 Gaps from Strategy Document Analysis (G1-G14)

| # | Gap | Strategy Line | Severity | Status |
|---|-----|---------------|----------|--------|
| G1 | No timeline/milestones — TTL A0 PO date not stated | Line 1 | **HIGH** | Open |
| G2 | No acceptance criteria — what % pass = "ready"? | Lines 1, 5 | **HIGH** | Open |
| G3 | No test inventory/porting plan for existing tests | Line 3 | **HIGH** | Open |
| G4 | No TTL metadata update plan (`thc_project_data.py`) | Line 3 | **HIGH** | Open |
| G5 | No Simics namednode API compatibility analysis | Line 4 | MEDIUM | Open |
| G6 | No NGA/logging integration plan for Simics | Line 4 | MEDIUM | Open |
| G7 | No softstrap combination matrix | Line 7 | MEDIUM | Open |
| G8 | No TTL GPIO pin assignments | Line 8 | **HIGH** | Open |
| G9 | No TTL PMCLite port ID | Lines 8, 10 | **HIGH** | Open |
| G10 | No driver patching plan for TTL DIDs | Line 9 | **HIGH** | Open |
| G11 | No OS image specification for Simics | Line 9 | **HIGH** | Open |
| G12 | No end-to-end integration test plan | Line 10 | MEDIUM | Open |
| G13 | No consistency/regression test plan | Line 10 | LOW | Open |
| G14 | No Simics model delivery dependency tracking | Line 5 | **HIGH** | Open |

### 33.2 Gaps from Wiki Study (G15-G28)

| # | Gap | Wiki Source | Severity | Status |
|---|-----|-----------|----------|--------|
| G15 | TTL Simics object path not documented | Finding 1 | **HIGH** | Open |
| G16 | TEP vs alps_touchscreen model types not distinguished | Finding 2 | MEDIUM | Open |
| G17 | TTL load-target boot command not documented | Finding 3 | **HIGH** | Open |
| G18 | BIOS setup field values not documented | Finding 4 | MEDIUM | Open |
| G19 | GPIO unlock requirement not documented | Finding 4 | MEDIUM | Open |
| G20 | Driver registry workarounds not documented | Finding 5 | MEDIUM | Open |
| G21 | HSDES 1508517875 SetIDValue WA not documented | Finding 5 | MEDIUM | Open |
| G22 | HSDES 16015917403 PTL SPI WA not documented | Finding 5 | MEDIUM | Open |
| G23 | I2C mouse cursor limitation not documented | Finding 2 | MEDIUM | Open |
| G24 | Minimum SPARK transactor version not documented | Finding 7 | MEDIUM | Open |
| G25 | Existing Simics unit tests (7 types) not referenced | Finding 8 | LOW | Open |
| G26 | thc_vdm detailed attributes not documented | Finding 6 | MEDIUM | Open |
| G27 | GPIO unimplemented known issue not documented | Finding 8 | MEDIUM | Open |
| G28 | File transfer method (FTP/agent) not documented | Finding 3 | LOW | Open |

### 33.3 Gaps from Wiki Re-Study — Iteration 2 (G29-G37)

> **Source**: 18 newly discovered wiki pages (v2.4 re-study)

| # | Gap | Wiki Source (Page ID) | Severity | Status |
|---|-----|----------------------|----------|--------|
| G29 | No Maestro/SLN emulation framework guidance for THC | 3986290848 (THC Emulation) | **HIGH** | Open |
| G30 | No display sync / frame sync validation plan | 1933394613 (Frame Sync PCR) | **HIGH** | Open |
| G31 | No WCL sighting cross-reference (6 HSDs) | 4606212223 (WCL Issues) | MEDIUM | Open |
| G32 | No IPSV test framework integration plan | 3775412802 (Pytest Repo) | MEDIUM | Open |
| G33 | No S0ix PM disable procedure / xmlcli knobs | 2918220570 (PM Enabling) | MEDIUM | Open |
| G34 | No SPI EV reference data (max freq, opcodes) | 3466824139 (THC SPI EV) | LOW | Open |
| G35 | No PRD/DMA Maestro implementation reference | 2761101312 (PRD Maestro) | MEDIUM | Open |
| G36 | No fuse debugging guidance for THC boot issues | 4261389213 (Fuse Debug) | LOW | Open |
| G37 | No HFPGA hardware setup reference (THC on mb2.C3) | 4617015496 (HW Setup) | LOW | Open |

### 33.4 Priority Summary (Updated v2.4)

| Priority | Count | Gaps | Action Required |
|----------|-------|------|-----------------|
| **P0 — Must have for TTL** | 6 | G4, G10, G15, G17, G29, G30 | Cannot start ANY TTL Simics work without these |
| **P1 — Required for execution** | 9 | G8, G9, G18, G19, G20, G26, G31, G32, G33 | Needed for successful test execution |
| **P2 — Best practice** | 22 | G1-G3, G5-G7, G11-G14, G16, G21-G25, G27-G28, G34-G37 | Improves quality and completeness |

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **VP** | Virtual Platform — complete simulated SoC + board |
| **DML** | Device Modeling Language — Simics-native compiled language |
| **VDM** | Virtual Device Model — simulated device endpoint |
| **VTC** | Virtual Test Card — VDM acting as test peripheral |
| **xTOR** | Transactor — bridge between simulation and RTL/FPGA |
| **HFPGA** | Hybrid FPGA — FPGA with RTL replacing Simics model |
| **Fmod** | Feature Model — RTL-derived override for Simics model |
| **S3E** | Simics System Solutions Engineering — team that creates VP models |
| **CCM** | Customer Configuration Manager — delivers VP configs matching silicon |
| **SimLauncher** | CLI tool for launching Simics VP sessions |
| **SVOS** | Silicon Validation OS — lightweight OS for testing |
| **AutoDML** | AI-driven DML model generation from HW specs |
| **IP-XACT** | IEEE standard for IP register/memory map description |
| **CDB2** | Collateral Database 2 — flow for creating skeleton models from IP-XACT |
| **PRD** | Physical Region Descriptor — DMA buffer descriptor |
| **PIO** | Programmed I/O — CPU-driven register transactions |
| **PMCLite** | Lightweight PMC sideband interface |
| **IOSF** | Intel On-chip System Fabric — sideband communication bus |
| **Simics** | Intel's full-system functional simulator (not cycle-accurate, not RTL) |
| **Model Gap** | Difference between Simics model behavior and real silicon behavior |
| **Checkpoint** | Simics snapshot of full system state — deterministic save/restore |
| **Import Sheet** | Spreadsheet defining test parameters for NGA/CI integration |
| **CKPT** | Abbreviation for Checkpoint |
| **Content Readiness** | Test scripts, tools, and automation ready for pre-si validation |
| **Recipe Readiness** | BIOS, drivers, softstraps, and platform config ready for pre-si |
| **Day-1 Ready** | All content + recipe ingredients available at silicon power-on |

---

## Appendix B: THC Model Type Decision

Based on the taxonomy in Section 4, the recommended model type for THC:

| Component | Recommended Model Type | Justification |
|-----------|----------------------|---------------|
| **THC Controller (DUT)** | **Register Functional Model** | Need full register behavior + DMA + interrupts + protocol for FV |
| **THC VTC (thc_vdm)** | **Register Functional Model** (already exists) | Must respond to HIDSPI/HIDI2C protocol commands |
| **SPI Transactor** | **Transactional Model** (already exists) | Bridges DUT ↔ VTC |
| **PMCLite Interface** | **Behavioral Model** | PM state transitions, sideband messages |
| **GPIO Interrupt Path** | **Behavioral Model** | Interrupt routing for touch events + WoT |
| **I2C Sub-IP (Synopsys DW_apb_i2c)** | **Register Functional Model** | Full APB register interface needed for HIDI2C |

---

*End of THC SIMICS Pre-Silicon Knowledge Base*
