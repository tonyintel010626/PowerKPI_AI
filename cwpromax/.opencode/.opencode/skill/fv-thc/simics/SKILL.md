---
name: fv-thc/simics
description: THC Simics pre-silicon validation — models, transactors, DML operations, SW-CI, IPSV, per-platform setup, and debug workflows for Intel Client SoC platforms
---

# THC Simics Pre-Silicon Validation

> **Owner**: Chin, William Willy (`willychi`)
> **Domain**: FV-THC / Pre-Silicon Simics
> **Version**: 1.4 (3rd verification: +3 glossary terms NPK/TCF/BFM, +2 section separators)
> **Created**: 2026-03-26
> **Purpose**: Entry point for THC Simics pre-silicon validation knowledge. Core concepts, FV strategy, gap analysis, and glossary.
> **Target Platform**: TTL (Gen4.2) — A0 Power On readiness
>
> **Scope boundary**: This sub-skill covers **PRE-SILICON Simics/VP** concepts only.
> For post-silicon THC validation, use the other `fv-thc/*` sub-skills (registers, hidspi, hidi2c, dma, power, platform, debug, driver, wot).

---

## Sub-File Structure

| File | Content | When to Load |
|------|---------|-------------|
| **`SKILL.md`** (this file) | Core Simics concepts, FV strategy, gap analysis, glossary | Always load first for Simics questions |
| **`models.md`** | THC models (thc_vdm, TEP, alps_touchscreen), SPARK transactors, Fmod | Model architecture, transactor config, device simulation |
| **`operations.md`** | Per-platform setup, BIOS config, driver install, debugging, S0ix | Day-to-day Simics operations and troubleshooting |
| **`advanced.md`** | SW-CI, emulation/HFPGA, IPSV, display sync, SPI EV, fuse debug, wiki refs, org | Advanced topics, frameworks, references |

**Full raw KB archive**: `fv-thc/docs/thc_simics_presi_knowledge.md` (2013 lines, all 33 sections)

### Companion Documents (not incorporated — cross-reference only)

| Document | Location | Purpose |
|----------|----------|---------|
| **THC Simics PreSi Requirements v2.4** | `C:\git\THC\THC_Simics_PreSi_Requirements.md` | Formal model requirements spec delivered to S3E. Contains PCI config registers with offsets/reset values, full MMIO register map, IOSF Sideband registers (Port 0x39), DMA/PIO engine specs, interrupt controller bit maps, PMCLite message flow, 67-item dependency matrix, acceptance criteria, risk register. |
| **Simics 101 THC FV Guide** | `C:\git\THC\Simics_101_THC_FV_Guide.html` | Visual HTML onboarding guide with SVG diagrams. 12 chapters covering Simics concepts, THC FV workflow, and getting started steps for new engineers. |

> **Note**: The `Pre-Silicon_High-level-Strategy_for_CVE-FV-THC-domain.txt` (10 lines) is NOT listed here — its content is already covered by sections 10-11 below.

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
10. [FV Domain Validation Strategy for SIMICS](#10-fv-domain-validation-strategy-for-simics)
11. [THC Pre-Si Strategy Alignment](#11-thc-pre-si-strategy-alignment)
12. [Requirements Gap Analysis (G1-G37)](#12-requirements-gap-analysis-g1-g37)
13. [Glossary](#appendix-a-glossary)
14. [THC Model Type Decision](#appendix-b-thc-model-type-decision)

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

The lifecycle of a bug is LONG: find -> debug -> root cause -> confirm fix -> release -> EVERYONE adopts (including customers). Finding bugs in Simics pre-silicon is the **cheapest and fastest** way to resolve them.

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
| Green | Model available with main features |
| Yellow | Model planned but not yet available |
| Red | No model planned |
| Gray | Memory/register-only model (no functionality) |

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

> **⚠️ THC Generation Numbering — IPSV vs Post-Si Perspective**
> IPSV numbering differs from post-silicon: IPSV Gen1.0 = **LKF** (first silicon with THC model), IPSV Gen2.0 = **TGL** (first full HIDSPI validation). Post-silicon counts Gen1.0 = TGL/ADL, Gen2.0 = ADP-LP+. The Simics/IPSV perspective reflects model development history, while post-si reflects productized feature sets. Always clarify which perspective when referencing "Gen X.0" in cross-team communication.
> *(Source: THCipsv wiki page 3028682606 'Project PCR and Good-to-Know')*

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
| **Connections** | Links between device instances | THC <-> SPI transactor <-> VTC (thc_vdm) |
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

### DML 1.4 Adoption & Migration

**DML 1.4 is the current standard** for all new Simics model development. Key improvements over DML 1.2:

| Feature | DML 1.2 | DML 1.4 |
|---------|---------|---------|
| **Templates** | Limited | Full template support with inheritance |
| **Method overrides** | Not supported | `method` override in templates |
| **`each`/`select`** | Combined | Independent statements |
| **Serialization** | Manual | Built-in serialization hooks |
| **Parameters** | Untyped | Typed parameters with validation |
| **Error messages** | Basic | Improved, actionable error messages |

- **Frontrunner platform**: Granite Rapids (GNR) — first full DML 1.4 VP
- **Migration status**: GNR/DMR SOC-internal models fully migrated DML 1.2→1.4; non-SoC models in `<vp_repo>/common/modules/` still pending migration
- **Register definitions**: Can be auto-generated from RDL/Nebulon XML via 2-step conversion flow (SystemRDL→intermediate XML→DML, or Nebulon XML→intermediate XML→DML) — see `advanced.md` Section 17
- **THC implication**: Any new THC model MUST use DML 1.4. The `dml 1.4;` header is mandatory.

*(Source: wiki pages 1966867505 (DML 1.4 adoption), 2678711724 (DML 1.4 migration), 1172842134 (RDL/Nebulon XML-to-DML))*

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
| **LTR** (Latency Tolerance Reporting) | Model LTR register writes -> PMC notification |
| **S0ix** | Model platform-level sleep integration |
| **WoT** (Wake-on-Touch) | Model GPIO wake path (NOT THC IP — goes through GPIO IP / vGPIO) |

### PMCLite Command Codes (for THC)

| Command | Code | Direction |
|---------|------|-----------|
| D0 | `0x8086D000` | THC -> PMC |
| D0i2 Entry | `0x8086D201` | THC -> PMC |
| D0i2 Exit | `0x8086D200` | THC -> PMC |
| D3 Entry | `0x8086D301` | THC -> PMC |
| D3Hot Entry | `0x8086D302` | THC -> PMC |
| D3Cold Entry | `0x8086D303` | THC -> PMC |
| PG Entry | `0x80860301` | THC -> PMC |
| PG Exit | `0x80860302` | THC -> PMC |
| Save Complete | `0x80860200` | THC -> PMC |
| Restore Complete | `0x80860201` | THC -> PMC |
| D3 Level 0 | `0x8086D310` | UHFI -> PMCLite |
| D3Hot | `0x8086D311` | UHFI -> PMCLite |
| D3Cold | `0x8086D312` | UHFI -> PMCLite |

*(Codes from THC power sub-skill, sourced from sip_thc_4x_has.html)*

---

## 10. FV Domain Validation Strategy for SIMICS

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

## 11. THC Pre-Si Strategy Alignment

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
| Platform enablement flows | Full boot -> enum -> init -> data flow must work | Pending |

---

## 12. Requirements Gap Analysis (G1-G37)

> **Source**: Cross-reference of Pre-Silicon High-level Strategy document (10 lines) + 47 wiki pages against THC_Simics_PreSi_Requirements.md v2.4
> **Date studied**: 2026-03-26 (iteration 2 — expanded from 29 to 47 wiki pages)

### 12.1 Gaps from Strategy Document Analysis (G1-G14)

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

### 12.2 Gaps from Wiki Study (G15-G28)

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

### 12.3 Gaps from Wiki Re-Study — Iteration 2 (G29-G37)

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

### 12.4 Priority Summary (Updated v2.4)

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
| **BAT** | Basic/Build Acceptance Test — automated regression suite (Bronze/Silver/Gold tiers) triggered on model commits |
| **FiVE** | Python-based device extension and test development framework for Simics validation |
| **FLEXCON** | Flexible Configuration — methodology and toolkit for managing HW/SW platform configurations |
| **FuseLite** | Lightweight fuse emulation subsystem for Simics VP (v1.x: LNL–NVL; v2.x: TTL+) |
| **ISCTLM** | Model-level unit test methodology for DML register R/W mask and reset default verification |
| **ISPM** | Intel Simics Package Manager — CLI tool for VP package installation and management |
| **Maestro** | HFPGA emulation orchestration framework (Maestro/Perspec) |
| **NGA** | Next Generation Automation — Intel test infrastructure platform |
| **OCI** | One Continuous Integration — umbrella project for VP setup, update, and collateral manifest |
| **OSAL2DML** | OS Abstraction Layer to DML — code generation pipeline: OSXML → OSAL Python API → DML 1.4 |
| **OSXML** | OneSource XML — HAS/register input format for the OSAL2DML pipeline |
| **RDL** | Register Description Language (SystemRDL) — formal register spec format for XML-to-DML conversion |
| **Regflow** | Register Flow — automated register read/write sequence verification methodology |
| **SimCloud** | Containerized Simics execution environment via Netbatch (CPU and GPU container types) |
| **SLN** | Simics Lab Network — networked multi-VP infrastructure for emulation testing |
| **Sloop** | Simics Python co-routine library for asynchronous BFM and test script execution |
| **Sonora** | Hardware testcard platform for IPSV testing (Sonora 2/3, QTH/QSH connectors) |
| **SPARK** | Simics Package Architecture — model packaging and release framework (e.g., SPARK 1.11.x) |
| **TCON** | Timing Controller — display timing controller providing frame sync signals to THC |
| **TEP** | Touch Event Provider — Simics SPI-mode VDM model for generating touch input events |
| **IPTS** | Intel Precision Touch and Stylus — THC predecessor driver framework (TGL/ADL era); registry path `HKLM\SOFTWARE\Intel\IPTS` still used for Simics workarounds |
| **PSF** | Primary Scalable Fabric — PCI routing fabric through which THC PCI functions are routed to the system bus |
| **XmlCli** | XML-based CLI tool (`pysvtools.xmlcli`) for BIOS knob programming via GBT-XML parsing and NVRAM mailbox interface |
| **BFM** | Bus Functional Model — simulation model that exercises a bus protocol interface for verification |
| **NPK** | Northpeak — Intel trace hub IP for DFD debug data capture and trace aggregation |
| **TCF** | Target Communication Framework — Eclipse-based protocol connecting SW debuggers to Simics VP targets |

---

## Appendix B: THC Model Type Decision

Based on the taxonomy in Section 4, the recommended model type for THC:

| Component | Recommended Model Type | Justification |
|-----------|----------------------|---------------|
| **THC Controller (DUT)** | **Register Functional Model** | Need full register behavior + DMA + interrupts + protocol for FV |
| **THC VTC (thc_vdm)** | **Register Functional Model** (already exists) | Must respond to HIDSPI/HIDI2C protocol commands |
| **SPI Transactor** | **Transactional Model** (already exists) | Bridges DUT <-> VTC |
| **PMCLite Interface** | **Behavioral Model** | PM state transitions, sideband messages |
| **GPIO Interrupt Path** | **Behavioral Model** | Interrupt routing for touch events + WoT |
| **I2C Sub-IP (Synopsys DW_apb_i2c)** | **Register Functional Model** | Full APB register interface needed for HIDI2C |

---

## Validation Points (Simics Pre-Silicon)

| ID | Check | Method | Pass Criteria |
|----|-------|--------|---------------|
| VP-SIM-001 | THC VDM model responds to protocol commands | Send HIDSPI INPUT_REPORT_HEADER / HIDI2C GET_REPORT via transactor | VDM returns valid HID report body; ICR `INT_CAUSE` bits reflect touch event |
| VP-SIM-002 | DMA descriptors (PRD) processed correctly | Configure RXDMA PRD ring with known buffer addresses; trigger touch event | `TPCRP` advances after report received; buffer contains expected report data; 4KB alignment enforced (RTL bug `15014172472`) |
| VP-SIM-003 | GPIO interrupt path triggers MSI in guest OS | Inject touch event from VDM → GPIO INT → THC → PCI MSI | Guest OS ISR fires; `INT_STS` shows expected interrupt source; driver processes report |
| VP-SIM-004 | Power state transitions preserve register state | Transition D0→D3→D0; compare register snapshot before/after | All SnR-listed registers restored correctly; DMA re-initialized; device functional after resume |
| VP-SIM-005 | Touch event injection produces HID reports | Use `alps_touchscreen` or `thc_vdm` touch injection; verify guest OS receives HID input event | Touch coordinates appear in guest OS HID input stream; coordinates match injected values |
| VP-SIM-006 | SW-CI gate criteria pass | Run Bronze/Silver/Gold test suites via SimLauncher | Bronze: driver loads, device enumerates. Silver: touch input works. Gold: PM transitions + stress |
| VP-SIM-007 | PMCLite sideband messages handled correctly | Trigger D0i2/CGPG entry via PM path; observe PMCLite SB messages in Simics console | Correct `PortID`, `Opcode`, `Reg` fields in sideband messages; PM state transitions complete without hang |

## See Also

- **`fv-thc/simics/models.md`** — THC model architecture (thc_vdm, TEP, alps_touchscreen, SPARK)
- **`fv-thc/simics/operations.md`** — Per-platform setup, BIOS config, driver install, debugging
- **`fv-thc/simics/advanced.md`** — SW-CI, emulation/HFPGA, IPSV, display sync, advanced topics
- **`fv-thc/docs/thc_simics_presi_knowledge.md`** — Full raw KB archive (2013 lines)
- **Post-silicon sub-skills**: `fv-thc/registers`, `fv-thc/hidspi`, `fv-thc/hidi2c`, `fv-thc/dma`, `fv-thc/power`, `fv-thc/platform`, `fv-thc/debug`, `fv-thc/driver`, `fv-thc/wot`

---

*End of THC Simics Pre-Silicon — SKILL.md (Entry Point)*
