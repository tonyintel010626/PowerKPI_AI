# THC Simics Advanced Topics — SW-CI, Emulation, IPSV & Specialized Validation

> **Parent**: [`fv-thc/simics/SKILL.md`](./SKILL.md)
> **Scope**: CI/CD pipelines, Maestro/HFPGA emulation, IPSV test framework, display sync, WCL sightings, SPI EV, PRD/DMA implementation, fuse debugging, organizational structure, and reference wiki pages
> **Source Sections**: KB S12 (SW-CI), S18 (Wiki Refs), S24 (Org), S25 (Emulation), S26 (WCL Issues), S27 (Display Sync), S28 (IPSV), S30 (SPI EV), S31 (PRD/DMA Maestro), S32 (Fuse Debug)
> **Version**: 1.4

---

## Table of Contents

1. [PythonSV SW-CI Framework](#1-pythonsv-sw-ci-framework)
2. [THC Emulation — Maestro / HFPGA / SLN](#2-thc-emulation--maestro--hfpga--sln)
3. [WCL Known Issues & Sightings](#3-wcl-known-issues--sightings)
4. [Display Sync / Frame Sync Validation](#4-display-sync--frame-sync-validation)
5. [THC IPSV Test Framework](#5-thc-ipsv-test-framework)
6. [SPI Electrical Validation Reference](#6-spi-electrical-validation-reference)
7. [PRD/DMA Maestro Implementation Details](#7-prddma-maestro-implementation-details)
8. [Fuse Debugging for THC](#8-fuse-debugging-for-thc)
9. [CVE Simics Organizational Structure](#9-cve-simics-organizational-structure)
10. [Reference Wiki Pages](#10-reference-wiki-pages)
11. [DFD Debug Components in Simics](#11-dfd-debug-components-in-simics)
12. [ISCTLM Unit Test Methodology](#12-isctlm-unit-test-methodology)
13. [OSAL2DML Code Generation](#13-osal2dml-code-generation)
14. [SimCloud Container Environment](#14-simcloud-container-environment)
15. [VP Release Milestones & Collateral Manifest](#15-vp-release-milestones--collateral-manifest)
16. [Simics Validation Framework — Sloop & FiVE](#16-simics-validation-framework--sloop--five)
17. [RDL/Nebulon XML-to-DML Register Conversion](#17-rdlnebulon-xml-to-dml-register-conversion)
18. [VP Testing Strategy & Quality Gates](#18-vp-testing-strategy--quality-gates)
19. [Modeling Requirements Creation Process](#19-modeling-requirements-creation-process)
20. [PMCLite Implementation Details](#20-pmclite-implementation-details)
21. [Sonora3 Testcard Details](#21-sonora3-testcard-details)
22. [THC Generation Mapping (IPSV vs Post-Silicon Perspective)](#22-thc-generation-mapping-ipsv-vs-post-silicon-perspective)
23. [TTL PCD-H Platform Tickets](#23-ttl-pcd-h-platform-tickets)

---

## 1. PythonSV SW-CI Framework

> **Source**: KB S12 (wiki page 3736864921 — Simics PythonSV SW-CI Framework)

### 1.1 CI Pipeline Structure

| Gate | Frequency | Timeout | Purpose |
|------|-----------|---------|---------|
| **Bronze** | Every 2 hours (model gate) | 1 hour | Quick smoke tests on latest VP |
| **Silver** | 1/day | 3 hours | Extended test suite |
| **Gold** | NGA-based | Variable | Full qualification via NGA |

> **BAT Auto-Trigger**: Bronze BAT (Basic Acceptance Test) runs automatically on every model commit via Falcon CI. BAT failures block Silver/Gold promotion.

### 1.2 Jenkins Pipelines

- Server: `cje-fm-simics-prod01`
- PythonSV SW-CI suite runs every 6 hours on latest Simics Bronze Recipe

### 1.3 Import Sheet Columns (Test Content Tracking)

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

### 1.4 AutoGen Framework

- Builds **TestRun Matrix** from Test YML + Configuration YML files
- Located in `<platform>/config/autogen-test.mk`

### 1.5 Execution Flow

```
1. NGA wrapper (SimicsClientRunner.py) starts
2. Setup script (e.g., startttl_simics.py) initializes VP
3. Boot to SVOS or EFI
4. PythonSV test executes via SimicsBaseAccess
5. Exit code returned (0=PASS, 9=FAIL per NGA convention)
6. Results reported to NGA/VP-Portal
```

### 1.6 Key Repos

| Repo | Branch | Content |
|------|--------|---------|
| `applications.simulators.isim.vp` | develop | VP source + models + tests |
| PythonSV (novalake) | main | Test scripts (`C:\pythonsv\novalake\vjt\thc`) |

### 1.7 Reporting Dashboards

- **VP-Portal**: `vp-portal.intel.com`
- **PowerBI**: Domain-specific dashboards
- **CloudBees SDA**: CI/CD job monitoring

---

## 2. THC Emulation — Maestro / HFPGA / SLN

> **Source**: KB S25 (wiki page 3986290848 — THC Emulation, v16; page 4617015496 — HW Setup; page 3556711840 — NVL-S Model2)

### 2.1 Emulation vs. Simulation

| Aspect | Simics (VP) | Maestro (HFPGA) |
|--------|-------------|-----------------|
| **Model type** | Software functional model | RTL on FPGA fabric |
| **Accuracy** | Register-functional | Cycle-accurate (RTL) |
| **Speed** | Fast (~MIPS) | Slower (~KHz-MHz) |
| **THC mapping** | thc_vdm + platform model | Real THC RTL on HAPS |
| **Use case** | SW bring-up, driver debug | HW validation, timing, PM |

### 2.2 Maestro Setup for THC

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

### 2.3 VTC Limitations

- **pcd_thc_simics** VTC has **NO OWNER** — limited maintenance
- VTC status: **"Occasional support"** — migrated to Simics 6 / Python 3 but not actively developed (source: TC Getting Started page 1249990578)
- Cannot test HIDSPI or HIDI2C end-to-end flows (SPI-only, basic)
- For full protocol testing, use thc_vdm + spi_xtor (SPI) or alps_touchscreen + i3c_xtor (I2C)

### 2.4 THC in HFPGA

- THC controllers are **RTL-mapped** in HFPGA (NOT Simics stubs) — confirmed for ADL, NVL-S
- Touch endpoints (tic00/tic10) also RTL-mapped
- SPI controllers (spi0-6) are Simics-mapped for speed
- THC is listed as RTL IP in NVL-S Model2 config (alongside ACE, USB, ISH, LPSS)
- THC FW = Production in Model2
- **NVL-S HFPGA**: THC on mb2.C3, EM100Pro SPI flash 1.8V (source: page 4617015496)

### 2.5 Waveform Capture for THC

- Use `zprd` + `tardis` switches in csh for waveform capture
- FSDB group: `pch_thc`
- Signal probes defined in: `pch_probes_thc_fwc.v`
- `transactors.json` contains THC transactor version
- `pch_thc_xtor.sv` defines signal connections

### 2.6 Key Configuration Files

| File | Purpose |
|------|---------|
| `transactors.json` | THC transactor version selection |
| `pch_thc_xtor.sv` | Signal connections between THC RTL and transactor |
| `Platform.bl` | Device IDs (differ per project), MMIO BAR for THC |
| `MiniBios.asm` | MMIO BAR for THC — **must match Platform.bl** |
| `pch_probes_thc_fwc.v` | Waveform signal list for THC |
| `pcd_run_dir_ovrd` | Side model overrides (copy + edit paths) |

### 2.7 Key Repos

| Repo | Purpose |
|------|---------|
| `github.com/intel-innersource/frameworks.validation.emulation.sln-and-testlist-repo` | SLN test lists |
| `github.com/intel-restricted/frameworks.validation.maestro.maestro` | Maestro framework |

### 2.8 Reference Documentation Links

- **RZL BDF**: `docs.intel.com/documents/ClientSilicon/RZL/global/RZL_PCD_Addr_BDF_DID_HAS/`
- **RZL GPIO**: `docs.intel.com/documents/pch_doc/RZL/RZLPCDH/HAS/Chap18_RZL_GPIO/`
- **NVL IOSF SB**: `docs.intel.com/documents/pch_doc/NVL/PCD-S/HAS/Chap41_NVL_PCD_IOSF_Sideband/`
- **NVL PSF**: `docs.intel.com/documents/pch_doc/NVL/PCD-S/HAS/Chap07_NVL_PCD_PSF/`

---

## 3. WCL Known Issues & Sightings

> **Source**: KB S26 (wiki page 4606212223 — THC WCL Issues, v6)

### 3.1 WCL Sighting Summary

| HSDES | Issue | Root Cause | Fix/Workaround |
|-------|-------|-----------|----------------|
| **16027559981** | YB on THC0/THC1 I2C at 1 MHz | 1 MHz I2C speed instability | Lower to 100 KHz or 400 KHz |
| **16027560205** | VKB delayed response in pre-OS (SM/FM/FMP) | BIOS I2C speed optimization needed | BIOS update |
| **16027746325** | I2C HID touchpad YB during Sx cycling | PM issue during sleep transitions | Under investigation |
| **16027810168** | POST code stuck 0x9B0E when enabling WoT in BIOS | WoT BIOS implementation issue | Disable WoT in BIOS |
| **16027836554** | Telemetry counters always reading 0 | Telemetry broken | Under investigation |
| **16027877982** | THC0 telemetry counters not incrementing | Same root cause as above | Under investigation |

### 3.2 Key Learnings from WCL

1. **I2C 1 MHz is unstable on WCL** — always validate lower speeds first (100K, 400K)
2. **WoT can cause boot hang** (POST code 0x9B0E) — critical regression gate for WoT testing
3. **Telemetry is broken** — cannot rely on HW counters for performance analysis on WCL
4. **Sx cycling exposes PM issues** — I2C touchpad YB during Sx cycling suggests save/restore or re-init problems

---

## 4. Display Sync / Frame Sync Validation

> **Source**: KB S27 (wiki page 1933394613 — PCR 22013186651 THC Frame Sync, v4)

### 4.1 Display Sync Event Sources

| DISP_SYNC_EVT_SRC | Value | Description |
|--------------------|-------|-------------|
| Disabled | 0 | No display sync |
| Emulated | 1 | Timer-based emulation (10 us/step, min 2 ms, max 100 ms) |
| TCON GPIO | 2 | External GPIO from display timing controller |
| Virtual Wire (VW) | 3 | Sideband virtual wire |

### 4.2 GPIO Mode Configuration

| DISP_SYNC_GPIO_MODE | Value | Trigger |
|---------------------|-------|---------|
| Rising edge | 0 | Rising edge |
| Falling edge | 1 | Falling edge |
| Both edges | 2 | Both edges |
| Reserved | 3 | Do not use |

### 4.3 Timestamp FIFO

- **SYNC_TS_LOG_BUF_x**: FIFO array with indices 0..DEPTH-1 (16 entries)
- **SYNC_TS_LOG_RDPTR**: 5-bit SW-managed read pointer
- **SYNC_TS_LOG_WRPTR**: 5-bit HW-managed write pointer
- **SYNC_TS_LOG_INTR_WM**: 4-bit watermark for almost-full interrupt

### 4.4 D0i2 Interaction

Two independent control bits create **4 combinations**:

| THC_TS_D0I2_MODE | THC_TS_D0I2_CONT_MODE | Behavior |
|------------------|-----------------------|----------|
| 0 | 0 | Counter continues across D0i2; no smoothing |
| 0 | 1 | Counter continues; smoothing active (adjusts for D0i2 gap) |
| 1 | 0 | Counter resets to 0 on D0i2 exit; no smoothing |
| 1 | 1 | Counter resets; smoothing active |

- **Smoothing** = timestamp adjustment to compensate for time spent in D0i2 (eliminates artificial timestamp jumps)
- **PMCLite involvement**: D0i2 entry/exit SB messages (`0x8086D201`/`0x8086D200`) trigger timestamp logic
- **CRITICAL**: Emulated timer MUST be disabled before entering D0i2

- **THC_TIMESTAMP_SRC** register selects timestamp source: GPIO pin, emulated timer, virtual wire, or display sync
- **Timestamp step** = 10 µs resolution per count

*(Source: wiki page 3454666109 — Continuous timestamp smoothing/coalescing; wiki page 1850905269 — PCR HID report timestamp)*

### 4.5 Validation Test Cases (from PCR)

| TC | Description | Key Checks |
|----|-------------|------------|
| TC1 | GPIO source + FIFO sampling | Watermark interrupt, FULL interrupt |
| TC2 | Emulated source | Timer period accuracy, emulation start/stop |
| TC3 | VW source | Virtual wire reception, FIFO capture |
| TC4 | FIFO wraparound | Different read/write pointer offsets |
| TC5 | Concurrency with timestamp PCR | Simultaneous DMA + display sync |

### 4.6 Lab Contacts

- IP FPGA owner: Ban Poh Wei
- Content owner: Chin Xian Hin (Mike Jr), Tan Hooi Jing

### 4.7 Coalescing Architecture

> **Source**: Wiki pages 3565424997 (Coalescing), 2990902476 (Coalescing with FrameSync), 1983235857 (Dynamic frame coalescing)

**Coalescing FSM** — 3-state machine controls when touch reports are delivered to host:

```
Disabled ──[coalescing enabled]──> Armed ──[first touch event]──> Active
   ^                                                                  |
   └──────────[coalescing disabled / idle timeout]────────────────────┘
```

| State | Behavior |
|-------|----------|
| **Disabled** | Reports delivered immediately (no batching) |
| **Armed** | Waiting for first touch event to start coalescing window |
| **Active** | Collecting reports; delivers batch when watermark reached or timer expires |

**Key constraint**: `Watermark + MPS <= 8196` — the combined watermark threshold and Max Packet Size must not exceed 8196 bytes.

**Two coalescing modes**:

| Mode | Trigger | Use Case |
|------|---------|----------|
| **Timer-based** | Internal timer expires (configurable period) | Default mode, predictable latency |
| **TCON Frame Sync** | External display timing sync signal | Aligned with display refresh for optimal UX |

**Dynamic Frame Coalescing** (PCR):
- Timer-based coalescing adjusts delivery to display refresh cadence
- 4 IPSV validation test cases defined for this feature
- PCR "HW frame coalescing at 300Hz" was **cancelled** ("Will not do for LNL") — only timer-based and TCON sync modes are implemented

### 4.8 TCON Frame Sync Signal Generator (Sonora Testcard)

> **Source**: Wiki pages 2038236523 (TCON Signal Generator), 1997025384 (TCON Feature LNL+)

- **Register**: `TCON_CTRL_REG` at Sonora testcard offset `0x1D4`
- **Connector**: QTH/QSH connector on Sonora testcard
- **Hardware pin mapping**: TCON signal routed to THC GPIO input
- Generates programmable frame sync signals for display sync validation without requiring a real display panel

---

## 5. THC IPSV Test Framework

> **Source**: KB S28 (wiki pages 3775412802 — THC Pytest GIT Repo, v4; 3776881921 — Pytest for THC Manual, v3)

### 5.1 IPSV vs PSV Test Repos

| Aspect | IPSV Repo | PSV Repo |
|--------|-----------|----------|
| **URL** | `github.com/intel-restricted/frameworks.validation.pythonsv.ipsv.thc` | `github.com/intel-restricted/frameworks.validation.pythonsv.projects.novalake/vjt/thc` |
| **Target** | Pre-silicon (Simics, HFPGA, emulation) | Post-silicon (real hardware) |
| **Framework** | Pytest (Falcon) | PythonSV + NGA |
| **Entry point** | `main.py` (launcher + ITP init + mode select) | Test scripts called via NGA |

### 5.2 IPSV Repo Structure

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

### 5.3 Running IPSV Tests

```bash
# Activate Falcon pytest virtual environment
D:\falcon\pytest\Scripts\activate

# Run tests
cd ..\src\<package>
pytest -sv <test_file>
```

### 5.4 Key Testcard Support

| Testcard | Protocol | Framework |
|----------|----------|-----------|
| **Sonora 2/3** | SPI | IPSV (`SONORA/`) |
| **PMCLite** | Sideband | IPSV (`PMC/`, `PMCLite_Vector/`) |
| **HIDSPI** | SPI | IPSV (`HIDSPI/`) |
| **HIDI2C** | I2C | IPSV (`HIDI2C/`) |

### 5.5 IPSV Validation Plan Details (LNL+)

> **Source**: Wiki page 1900547074 (THC HIDSPI/HIDI2C Validation Plan LNL+)

**ICR (Input Cause Register) Format Scrambling**: 6 ICR format variants tested to verify THC correctly parses all valid ICR layouts in HIDSPI frames.

**Programmable Opcode Randomization**: All 6 SPI opcodes (read/write per Single/Dual/Quad mode) randomized with varying `cmd_bits`, `addr_bits`, and `dummy_bits` to verify opcode decode logic.

**Dummy Clock Randomization**: Dummy clock cycles between address and data phases varied randomly to stress SPI timing recovery.

**Seed-Based Testing**: **1000+ random seeds** used for regression coverage — each seed generates different ICR formats, opcode configs, and packet sizes.

**I2C Bus Speed Coverage**:

| Speed Mode | Frequency | Abbreviation |
|------------|-----------|-------------|
| Standard Mode | 100 KHz | Sm |
| Fast Mode | 400 KHz | Fm |
| Fast Mode Plus | 1 MHz | Fm+ |
| Ultra Fast Mode | 5 MHz | UFm |

### 5.6 IPSV RTL Bug Fixes (from Wiki)

> **Source**: Wiki pages 3108833308, 3108833339, 3516738658, 3108833358, 2813927240

| HSDES | Platform | Bug | Fix |
|-------|----------|-----|-----|
| **16019332816** | NVL | GPIO sync event mode: coalescing delay counter not resetting on new sync events | Counter reset logic added in NVL RTL |
| **16020879491** | NVL | Buffer overrun SPI vs I2C mismatch: RX FIFO 8KB / 4 slots, SPI and I2C paths used different overrun thresholds | Unified overrun logic in NVL |
| *(NVL HIDSPI Delay Timer)* | NVL | Buffer Packet FIFO undersized (4 slots) causing overrun at high report rates | **FIFO expanded 4→32 slots in NVL** (was 4 on LNL/PTL); 14 reports max before overrun |
| *(quiesce_en_isol)* | NVL | D0i2 PG exit failure when interrupt arrives during power gate sequence | Isolation signal fix in NVL RTL |
| *(Multi-report interrupt)* | LNL | Sonora2 HIDI2C_MANUAL_CTRL: multi-report interrupt assertion not working correctly | Sonora2 testcard register fix for LNL |

### 5.7 VICESW Test Content & RTR Framework

> **Source**: Wiki pages 3762034607 (THC Test Content Support), 3054643734 (THC Content/Features HID PTL)

**RTR (Register-Transfer-Run) Framework**: Structured test content methodology used by VICESW for THC validation:
- **Regflow**: Register flow validation — automated register read/write sequence verification
- **Intent coverage**: Maps test content to HAS intent specifications — tracks which HAS requirements are covered
- **Sonora partition**: Testcard-specific test content partitioned by protocol and feature

**Maestro/Perspec Test Content Mapping**: Extensive test mapping for IPTS/HIDI2C/HIDSPI features in Perspec framework (page 3054643734 contains the full Maestro test content matrix for PTL).

### 5.8 Focus Tests Pending Automation

> **Source**: Wiki page 3566312865 (Python Focus Test list)

**8 manual focus tests** identified for automation migration:
- Tests include `SONORA_INPUT_REPORT_SETUP_SRAM_DATA()` and `COMPARE_REPORT_RX2_TC_AUTONOMOUS()`
- Currently require manual Falcon pytest execution
- Planned migration to CI-triggered Maestro/Perspec framework

---

## 6. SPI Electrical Validation Reference

> **Source**: KB S30 (wiki page 3466824139 — THC SPI EV, v8)

### 6.1 SPI Electrical Specs

| Parameter | Value |
|-----------|-------|
| **Max SPI frequency (platform)** | 40 MHz |
| **Voltage** | 1.8V |
| **IO Modes** | Single, Dual, Quad |

> **Half Clock Divider**: PCR for fastest SPI controller added half-divider support to reach higher SPI frequencies. The **duty cycle feature was ZBBed** (zero-bug-bounced / not implemented in RTL) — do not test duty cycle control.

### 6.2 SPI Opcodes per IO Mode

| Mode | Write Opcode | Read Opcode |
|------|-------------|-------------|
| **Single (1-1-1)** | 0x02 | 0x0B |
| **Dual (1-2-2)** | 0xB2 | 0xBB |
| **Quad (1-4-4)** | 0xE2 | 0xEB |

### 6.3 EV Test Phases

| Phase | Scope | Units |
|-------|-------|-------|
| **PO** | Register + recipe check + interface enable + SIV spot | — |
| **Ax** | Broad (5 units) + worst-case (5 VT corners) | 10 |
| **Deep** | +/-3-sigma qualification | 12 |

### 6.4 Equipment & Tooling

- **Scope**: MSO9254A (2.5 GHz)
- **Probes**: N2496A
- **Positioner**: E2654A
- **Automation**: Dragon (`github.com/intel-restricted/frameworks.validation.wideband-io.flows`)

### 6.5 Contacts

- Arturo Bolanos Cortes, Juan Luis Lopez Padilla (SPI EV team)

---

## 7. PRD/DMA Maestro Implementation Details

> **Source**: KB S31 (wiki page 2761101312 — THC PRD maestro, v1)

### 7.1 Write DMA (TXDMA) PRD

- Single PRD table
- Max 256 KB entries
- Uses `StaticMem` API for allocation
- Setup: `SetupDmaWritePRD(numBytes, iocMode, numFrags)`

### 7.2 Read DMA (RXDMA) PRD

- Circular buffer of up to **128 PRD tables** (configurable via `THC_M_PRT_RPRD_CNTRL.PCD`)
- Each table has same entry count
- Max **256 entries per table** (for 1 MB at 4 KB fragmentation)
- Setup: `SetupDmaReadPRD(engine, numFrames, minFrags, iocMode, maxFrags)`

### 7.3 PRD Random Test Methodology

- `DescribeTable()` generates random fragment sizes
- Max fragment size = 2x average
- `StaticRand::Range()` for size generation
- Shuffle fragments to avoid ordering bias

### 7.4 PRD Field Access by Agent

| Field | SW Write | HW Consume | HW Update | SW Read |
|-------|----------|-----------|-----------|---------|
| **Length** | Yes | Yes | Yes (RXDMA) | Yes |
| **EOP** | N/A (TX) / Yes (RX) | Yes | Yes (RX) | Yes |
| **IOC** | Yes | Yes | No | No |
| **DestAddr** | Yes | Yes | No | No |
| **HW Status** | Clear | No | Yes | Yes |

### 7.5 HIDI2C SWDMA Special Fields

| Field | Bits | Description |
|-------|------|-------------|
| **THC_SWDMA_I2C_WBC** | 31:26 | Write byte count (1-64 bytes) |
| **THC_SWDMA_I2C_RX_DLEN_EN** | 23 | Descriptor vs device length mode |

**DLEN_EN usage**:
- `DLEN_EN=0`: Use PRD length field — for HID/Report descriptor retrieval
- `DLEN_EN=1`: Use device's 2-byte length field — for Get_Report/Idle/Protocol

### 7.6 HIDI2C SWDMA Operational Notes

- **Write phase** uses PIO Data registers (not DMA buffer)
- **SW DMA and PIO shall NOT run simultaneously** — hardware does not arbitrate between them
- **Reset descriptor**: 2-byte length field = 0 (transparent to HW, triggers device reset)
- **Input report**: Device sends 2-byte length prefix; DLEN_EN=1 tells THC to use device-reported length

### 7.7 RX Streaming Mode (Packets >4KB)

> **Source**: Wiki page 1943084492 (PCR THC RX packet >4KB)

RX Streaming Mode enables reception of packets larger than 4KB without increasing the internal RX FIFO buffer size:

| Register Bit | Description |
|-------------|-------------|
| `RXDMA_PKT_STRM_EN` | Enable RX streaming mode for read DMA |
| `TXDMA_PKT_STRM_EN` | Enable TX streaming mode for write DMA |

When enabled, THC streams large packets directly through the DMA engine to host memory, bypassing the internal FIFO size limitation. This is critical for touch devices with large HID report descriptors or high-resolution multi-touch reports.

### 7.8 Buffer Packet FIFO Evolution

> **Source**: Wiki page 3516738658 (NVL HIDSPI Delay Timer bug fix)

| Platform | FIFO Slots | Max Reports Before Overrun |
|----------|-----------|---------------------------|
| **LNL** | 4 | ~3 (depends on MPS) |
| **PTL** | 4 | ~3 |
| **NVL** | **32** | **~14** (8x improvement) |

The FIFO expansion from 4→32 slots in NVL was driven by buffer overrun issues at high touch report rates. With 4 slots, overrun occurred when the host could not drain reports fast enough (e.g., during DMA pause or system load spikes).

---

## 8. Fuse Debugging for THC

> **Source**: KB S32 (wiki page 4261389213 — Debugging Simics Client Fuse Issues, v2)

### 8.1 Fuse Architecture

- Fuse controller accessible via sideband (GPSB/PMSB)
- Fuses populate IP device registers at boot time
- THC fuse attributes accessible via: `<platform>.mb.hub.fuse` -> `fuse_<ip>_<name>`

### 8.2 Debug Flow

1. Check fuse attribute on device model
2. Capture payload from Simics log
3. Decode with `fusegen-tools.py`
4. Compare old vs new fuse patches

### 8.3 fusegen-tools.py Commands

```bash
# Import text blob for analysis
fusegen-tools.py --import_text_blob <file>

# Compare two fuse patches
fusegen-tools.py --compare_patch <old> <new>

# Print fuse statistics
fusegen-tools.py --print_fuse_stats
```

### 8.4 fusegen XML Fields

| Field | Description |
|-------|-------------|
| `IOSFSBEP` | IOSF sideband endpoint |
| `IOSFSBPortID` | Sideband port ID |
| `RamAddr` | RAM address for fuse data |
| `FuseDefaultValue` | Default value when fuse not blown |

### 8.5 FuseLite THC-Specific Details

> **Source**: Wiki pages 2211296045 (FuseLite 1.x, v3), 2798138055 (FuseLite 2.x, v3)

#### FuseLite 1.x (LNL/PTL/WCL/NVL)

| Parameter | THC0 | THC1 |
|-----------|------|------|
| **Sideband Port ID** | `0x39` | `0x3A` |
| **Fuse Address** | `0x80` | `0x80` |
| **Strap Address** | `0x84` | `0x84` |
| **Strap Value (CG+PG enabled)** | `0x3` | `0x3` |

- FuseLite opcode for fuse request: `0xB8` (FuseReq)
- FuseLite opcode for strap request: `0xBC` (StrapReq)
- IP Ready notification opcode: `0xD0` (IPReady)

#### FuseLite 2.x (TTL+)

- **Combined opcode**: `0x45` — merges fuse+strap into single transaction
- **16-bit Port ID**: Required for TTL+ (matches HSDES 15010734105 SB fabric upgrade)
- FuseLite 2.x aligns with PTL+ 16-bit SB port ID infrastructure

#### Simics Fuse/Strap Debug

```simics
# Check THC fuse attributes
print-device-regs <platform>.mb.hub.fuse | grep -i thc

# Verify strap value (0x3 = CG+PG enabled)
# If strap = 0x0, THC will not have clock/power gating enabled
```

### 8.6 CI Debugging Tip

Comment out IP fuse groups to isolate fuse-related boot failures. Test incrementally to identify which IP's fuses are causing issues.

---

## 9. CVE Simics Organizational Structure

> **Source**: KB S24 (wiki page 4605435102 — Simics Phone Book; page 1966867456 — THC Device Overview; page 2364131531 — PTL PCRs)

### 9.1 THC Simics Domain Lead

**William Chin** (`willychi`) — CVE FV THC Simics Domain Lead

### 9.2 Adjacent Domain Leads

| Domain | Lead | Notes |
|--------|------|-------|
| NVU | Bee Koon Lee | Neural Vision Unit |
| LPSS | Kong Jia Wen | Low Power Subsystem |
| ISH | Leem Yi Jie | Integrated Sensor Hub |
| USB | Nagalakshmi Ganta | USB/xHCI |
| Audio | Siva Balasundram | HDA/SoundWire/DSP |
| South PM | Jesse Dickinson / Kedar Kulkarni | Power Management |

### 9.3 Program Tracking Mechanisms

| Mechanism | Description | HSDES Tag |
|-----------|-------------|-----------|
| **Functional Requirements (FRs)** | Simics model requirements filed by FV domains | `CVE_Simics_TTL`, `CVE_Simics_NVL`, `CVE_Simics_RZL` |
| **Quality Events (QEs)** | Bugs found on silicon that SHOULD have been found in Simics | (per project tracking page) |
| **Sightings** | Simics model bugs | NVL Simics Sightings page |

### 9.4 Key Contacts (THC Simics Model)

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

### 9.5 PTL PCRs with Simics Impact

From page 2364131531:

| HSDES | Priority | Description | Relevance |
|-------|----------|-------------|-----------|
| **14016435572** | — | OSXML and HAS updates for SIMICS Shift-Left for LPM Validation | **Directly relevant** — Simics shift-left for PM validation |
| **15010734105** | High | IP to support 16-bit port ID endpoint | Breaking change on PTL+ (matches known HSDES) |
| **22014732835** | — | Enable customer to use ODLA to debug THC IO signals (SPI/I2C/INTR) | Debug capability enhancement |
| **16015843747** | Medium | WA Carry Forward: Resource own req/Ack Violation (Chassis 2.2 signal handshake, 10 resources) | Model workaround |
| **14016605173** | High | Fuzz test IP interfaces (Security) | Security testing |

---

## 10. Reference Wiki Pages

> **Source**: KB S18 — all 47 wiki pages studied and knowledge extracted from

### 10.1 Original Wiki Pages (29 pages)

| Page ID | Title | Space | Key Content |
|---------|-------|-------|-------------|
| 4605435114 | Simics and Virtual Platform | fvcommon | Foundational overview — Simics vs VP definition |
| 4639114330 | Simics Domain Validation Strategy Guidance | fvcommon | 5-area FV domain strategy for Simics |
| 4605435116 | Motivation for Simics | fvcommon | Business case, NVL-S analysis, real-world examples |
| 3736864921 | Simics PythonSV SW-CI Framework Overview | fvcommon | CI pipeline (Bronze/Silver/Gold), AutoGen, import sheets |
| 3041035826 | Simics Virtual Platform Details | Simics | VP architecture details |
| 3844014084 | Altera Simics KM IP Model Types & Stakeholders | ITSpsgaet | Model taxonomy (5 types), stakeholder matrix |
| 2797523774 | Simics VP Ingredients | ITSpsgaet | 8 VP ingredients, build/packaging |
| 4661117246 | BKM for Simics VP device model auto-generating (AutoDML) | hyltxxsc | AI-driven 5-phase DML model generation |
| 1966867225 | Creating a Virtual Platform with Simics | SRESIMICS | Step-by-step platform VP creation |
| 4639109312 | RZL Virtual Platform Execution | fvcommon | SimLauncher setup, practical VP usage |
| 1249986926 | spi_xtor Operation Modes | PPA | SPI transactor modes, THC VTC connection |
| 1249986915 | spi_xtor Simics Interfaces | PPA | thc_vdm class definition, attributes |
| 1966866946 | Chassis Power Management Framework | SRESIMICS | PMC model, D-state transitions, LTR |
| 2710449321 | Simics Key Learnings | npgnseval | Debug techniques, HFPGA, BIOS overview |
| **1966867553** | **THC model development (WIP)** | **SRESIMICS** | MTL TEP model attrs, reset_delay, HID descriptors, doze, MFS, mouse-to-touch, WA 1508517875 |
| **1966867456** | **THC Device Overview** | **SRESIMICS** | Model capabilities (Reset/Interrupts/Registers/PM/LTR), unit test list, GPIO unimplemented known issue |
| **2845164237** | **BKM THC I2C driver on LNL Simics** | **SRESIMICS** | LNL I2C driver install, trigger_input_report, alps include files, DigiInfo validation |
| **4045307441** | **BKM THC QuickI2C driver NVL-S Simics** | **SRESIMICS** | NVL-S load-target, BIOS I2C values (addr=0xA, SCL HIGH=267/LOW=271), alps_touchscreen objects |
| **1966867486** | **THC debugging with WinDbg on MTL Simics** | **SRESIMICS** | Telnet-based kdcom-proxy debugging, port 12375, $windbg_enable=TRUE |
| **3217199088** | **BKM THC HIDSPI & HIDI2C driver on PTL Simics** | **SRESIMICS** | PTL I2C+SPI dual-mode, WA 16015917403, TEP (SPI) vs alps (I2C) objects |
| **1966867128** | **BKM THC IPTS & HIDSPI driver on MTL Simics** | **SRESIMICS** | IPTS/HIDSPI registry WAs, PEI_ASSERT HSDES 1508958117, mouse-to-touch |
| **1433100579** | **THC Simics - Getting Started** | **IPTS** | LKF era (obsolete Simics 5), architecture pattern: thc0 + tic00 + mem_space |
| **1800325877** | **BKM QuickSPI (HIDSPI) on MTL Simics** | **IPTS** | Simics base 6.0.71, DO NOT enable logging during touch test, FPGA_LCBE=1 |
| **1249985406** | **THC BAT Test** | **PPA** | LKF FPGA PIO write/read validation, PIO offsets (+0x1040/1044/1048/104C), opcode 0x04/0x06 |
| **2364131531** | **PantherLake THC Gen 4.1 (PTL-PCD-P)** | **THCipsv** | PTL PCRs: 15010734105 (16-bit port ID), 14016435572 (Simics shift-left for LPM) |
| **1155001205** | **Monthly Knowledge Sharing - CSME/SPI/eSPI/THC** | **THCipsv** | 2018-2019 Penang sessions, Simics pkg install, low relevance |
| **4605435102** | **Simics Phone Book & Queries** | **fvcommon** | THC domain lead=William Chin, CVE Simics FRs via HSDES tags, QE tracking |
| **3740545285** | **Quality Test plan - NVL FV** | **fvcommon** | NVL FV test planning reference |
| **1620643113** | **SPARK 1.11.x Release Notes** | **PPA** | 4 THC entries: 1508628560 (infinite loop fix), 14015253601 (I2C), 16018039801+16018045412 (HAS alignment) |

### 10.2 Newly Discovered Wiki Pages (18 pages, v2.4 Addition)

> **Discovered**: 2026-03-26 via CQL search across SRESIMICS, fvcommon, CVEValPlatforms, THCipsv, PPA, VICESW spaces.

| Page ID | Title | Space | Key Learnings |
|---------|-------|-------|---------------|
| **3986290848** | THC Emulation | THCipsv | Maestro/HFPGA/SLN emulation framework, waveform capture, transactors.json, MiniBios.asm, RTL access groups, RZL/NVL doc links |
| **4175342280** | THC WCL BIOS knobs | fvcommon | WCL BIOS: Intel Advanced > Serial IO for THC0/1, Virtual Keyboard enable |
| **4606212223** | THC WCL Issues | fvcommon | 6 WCL sightings: I2C 1MHz unstable, VKB delays, Sx cycling YB, WoT boot hang 0x9B0E, telemetry broken |
| **3466824139** | THC SPI - EV | IPMWiki | Max SPI freq 40MHz, timing specs at 42.67/32MHz, SPI opcodes per IO mode, Dragon automation |
| **2761101312** | THC PRD table in Maestro | VICESW | Deep PRD/DMA implementation: write/read DMA setup, SWDMA I2C WBC/DLEN_EN bits, PRD random test |
| **3439922659** | PTL Simics Setup | bnatarajan | Linux/Ubuntu setup, ISPM packages, project-setup, custom target scripts, automation json config |
| **1933394613** | PCR 22013186651: THC Frame Sync | THCipsv | Display sync GPIO/emulated/VW sources, timestamp FIFO, watermark interrupt, 5 test cases, D0i2 modes |
| **3775412802** | THC Pytest GIT Repo | THCipsv | IPSV test framework: github.com/intel-restricted/frameworks.validation.pythonsv.ipsv.thc, Sonora testcard, PMCLite vectors |
| **3776881921** | Pytest for THC (Manual) | THCipsv | Falcon pytest environment (D:\falcon\pytest), Config.py setup, debug scheduler |
| **1249986913** | spi_xtor Integration (WIP) | PPA | thc_vdm instantiation code, SPI opcode config per IO mode, simple_io_xtor for interrupts, VTC DEPRECATED in SPARK 1.11.7 |
| **2068317556** | MTL PSS Session Setup Guide | IPTS | Linux VNC setup for Simics MTL, ISPM packages pkg-1000/1001/7500, CRT alternative |
| **1498127969** | IPTS Playbook | CPS | Historical driver versions THCBase 2.1.0.65-3.0.100.230, design wins (Surface/Lenovo/HP/ASUS), team transitions |
| **2918220570** | PM Enabling | fvcommon | S0ix THC disable: ThcAssignment_0/1=0x0, MTL/PTL Simics parity table, SVOS sleep commands |
| **1693808060** | RTL-Simics mappings SOC S | PPA | THC mapped to RTL in HFPGA (not Simics stub), GPIO config issue HSD 1307012183 |
| **4261389213** | Debugging Simics Fuse Issues | SRESIMICS | Fuse controller sideband access, fusegen-tools.py decode/compare, CI isolation |
| **4617015496** | Hardware Setup (WIP) | PPA | NVL-S HFPGA: THC on mb2.C3, EM100Pro SPI flash 1.8V, power-on sequence |
| **1249990578** | TC - Getting Started | PPA | THC VTC migrated to Simics 6/Python 3, occasional support, thc_vdm is current test card |
| **3556711840** | Model 2: Min Boot + PCH IPs | PPA | NVL-S Model2: THC listed as RTL IP on PCH-S, production FW, WinOS boot target |

---

## 11. DFD Debug Components in Simics

> **Source**: Wiki research — page 3242957849 (SDDE space, v3)

> **VISA (Visualization of Internal Signals and Architecture)**: THC supports VISA regression debug for observability of internal signals. Debug artifacts and tracker files are maintained for THC 4.1 VISA regression (ref: ESIPWiki page 3064545564).

### 11.1 Simics DFD Component Inventory

| Component | Package | Purpose | THC Relevance |
|-----------|---------|---------|---------------|
| **TCF Agent** | simics-base | Connects SW debugger to Simics target, trace + run-control | Debug THC model from IDE |
| **simics-ipccli** | #7031 | CScripts connect to VP over TCF; runs on debug host | Access THC registers via CScripts |
| **itp-helper** | #7031 | Connection server ON VP; handles multiple debugger clients | Remote ISD/CScripts/CSE access to THC |
| **tap-devel-common** | — | TAP over JTAG interface | JTAG-based THC debug |
| **tap-endebug-gen** | — | ENDEBUG (TGL and newer) | Enhanced debug for THC platforms |
| **tap2iosfsb** | — | Access IOSF-SB via TAP (ALL platforms) | **Directly relevant** — THC sideband register access via TAP |
| **dfd-rcm** | — | Run Control Module | Core/thread control during THC debug |
| **npk-comp** | — | NPK connectors | THC trace event capture |
| **npk-tcpstream** | — | Trace over TCF | Remote THC trace streaming |
| **npk-parser** | — | Trace decoders | Decode THC DMA/interrupt trace events |
| **npk-interface** | — | IOSF-SB interface for trace injection | Inject test trace events into THC path |
| **npk-gen3** | — | Client PCI model (NPK2/3 HAS) | Client platform NPK for THC |
| **ExI** | — | Embedded DFx Interface — closed-chassis DFx access | Production debug access to THC |
| **DFx Security Aggregator** | — | Secure policy update, boot exit | Security-gated THC debug |
| **SPK (Sierra Peak)** | — | High-bandwidth trace to system memory | High-volume THC DMA trace |

### 11.2 Key Debug Command: `probe-address`

> **Source**: Wiki page 2117879707 (PSG Simics Debug Commands). See also: [operations.md Section 2.2a](./operations.md#22a-address-translation--register-inspection) for full debug command reference.

```simics
# Trace MMIO address through full translation chain to find THC model/register
$a = (probe-address 0xFE040100)
# Output: CPU → bus → device → register with offset
# Critical for: "Which THC register is being accessed at this address?"
```

---

## 12. ISCTLM Unit Test Methodology

> **Source**: Wiki research — page 1172841961 (PPAVirtualPlatforms space, v43)

### 12.1 Overview

Simulation-tool-independent approach using SystemC/C++ standalone executables (no Simics dependency). Blueprint XML defines register model → auto-generates test template code.

### 12.2 Test Structure

```
sc_main.cpp          # Instantiates DUT + testbench, binds ports, runs sc_start()
testbench.cpp        # addTest() registration, automated/interactive modes via CLI
IosfPrimarySender    # Helper: IOSF primary bus transactions
IosfSidebandSender   # Helper: IOSF SBI read/write in tests
```

### 12.3 Standard Test Coverage Areas

| Area | What to Test | THC Example |
|------|-------------|-------------|
| **Reset** | Assert each reset, verify outputs | THC DEVRST, check register defaults |
| **Power** | Drive power-good inputs, verify register access fails when off | THC PGD/UGD isolation |
| **Clock** | Sweep input range, check dividers | THC SPI clock divider |
| **Register** | R/W masks, volatile bits, control field permutations | THC MMIO register map |

### 12.4 Code Generation

```bash
# Auto-generate test template from Blueprint XML
unit_checkin.py --prepare
```

### 12.5 THC Applicability

IOSF SBI helpers are **directly applicable** for THC sideband register testing. This methodology could be adapted for THC Simics model unit testing — validate register read/write masks, power gating isolation, and reset defaults without full VP boot.

---

## 13. OSAL2DML Code Generation

> **Source**: Wiki research — page 3937898817 (SRESIMICS space, v67)

### 13.1 Pipeline

```
OneSource (OSXML) → OSAL Python API → Mako Templates → DML 1.4 Code
```

### 13.2 Key Details

| Aspect | Detail |
|--------|--------|
| **Package** | 9804 (OSAL2DML), 9803 (OSDML — predecessor) |
| **Repo** | `intel-innersource/applications.simulators.isim.vp.osdml` |
| **Release path** | `/nfs/site/disks/ssg_stc_simics_base-packages-release/simics-7/9804` |
| **Config** | Per-chip build config (e.g., `spr-osdml.cfg`) |
| **Input validation** | OSXML Validator + OneSource Validator |
| **Templates** | Mako — compartmentalized file output per register bank |

### 13.3 THC Applicability

If THC HAS is in OSXML format, the THC register model can be **auto-generated** from OneSource/OSAL. Understanding this pipeline is key for model development and HAS-to-model alignment verification.

---

## 14. SimCloud Container Environment

> **Source**: Wiki research — pages 4220991202 (fvcommon, v14), 3157404304 (LADSW, v42)

### 14.1 Architecture

SimCloud = containerized Simics execution via Netbatch. Two container types:

| Type | Lifecycle | Use Case |
|------|-----------|----------|
| **Persistent** | Survives across test runs | Development, interactive debug |
| **Auto-spawned** | Created per NGA test run, destroyed after | CI/CD automation, regression |

### 14.2 SimCloud CLI

```bash
# List running containers
simcloud instance list

# Create new container (VNC mode)
simcloud submit --mode vnc --cores 10 --memory 24 --disk 32

# Kill container
simcloud kill <id>
```

### 14.3 AGS Permissions Required

- EC Resources SSDV, simcld, simcld_ts
- Artifactory Simics BB Viewer
- Faceless account for automation (e.g., `sys_ace_simc` for DMR)

### 14.4 NGA Auto-Spawned Integration

- `VType=SimCloud` in NGA station config
- `GoStatus=GoOnlyWhenQueued` — container created on demand
- **Flexit NGA Load Balancer** distributes across persistent + auto-spawned containers

### 14.5 DML Code Coverage via SimCloud DevTools

DML code coverage is now integrated into SimCloud DevTools (page 3302493229). The legacy standalone flow (page 1966867884) is deprecated.

| Step | Tool | Purpose |
|------|------|---------|
| **Instrumentation** | GCOV | Compile DML models with coverage flags |
| **Execution** | SimCloud | Run tests in containerized environment |
| **Report generation** | LCOV | Generate HTML coverage reports |
| **CI integration** | CI Coverage Flow (page 3118345060) | Automated coverage in CI jobs |

**THC Applicability**: DML code coverage can validate that THC model registers and state machines are exercised by VTCs/IPSV tests. Low-coverage areas indicate undertested model paths.

### 14.6 Development Setup

1. ION Session Manager (VNC) or `simcloud submit`
2. SSH/VSCode Remote to container
3. itools config: gcc 12.1.0, python 3.9.6, vscode 1.81.0
4. Kerberos: `kinit $USER@amr.corp.intel.com`
5. Symlink heavy folders from `$HOME` to NFS work area (`~/.cache`, `~/.vscode-server`)

---

## 15. VP Release Milestones & Collateral Manifest

> **Source**: Wiki research — pages 1966867032 (SRESIMICS, v34), 3423677490 (fvcommon, v22)

### 15.1 VP Release Milestones

| Milestone | HAS Required | Health Checks | Key Criteria |
|-----------|-------------|---------------|-------------|
| **VP0.0** | HAS 0.3 | 6 | Migration from prev project |
| **VP0.3** | HAS 0.5 | 12 | New project registers added |
| **VP0.5** | HAS 0.8 | 30 | Critical + high priority features |
| **VP0.8** | HAS 1.0 | 30 | All new features complete |
| **VP1.0** | HAS 1.1 | 30 | Bug fixes + final RDL/RTL alignment |

- **Cadence**: Monthly time-boxed releases (not content-driven)
- **Bronze**: Delivered day before Silver (official release)
- **VP releases are independent** from SW/FW components

### 15.2 OCI (One Continuous Integration) & Collateral Manifest

**OCI** (One Continuous Integration) is the umbrella project that simplifies VP setup, update, and configuration (page 1966867969). The **Collateral Manifest** is a sub-feature of OCI.

**Collateral Manifest** (DMR Pattern) — single release entity bundling:
- VP (Virtual Platform)
- IFWI (firmware image)
- Microcode
- SVOS (validation OS)
- VTCs (Virtual Test Cards)

Weekly cadence for manifest migration. Triggered by Silver-labeled VP releases.

### 15.3 CI Hierarchy

```
Vanilla → Boot → Sanity → FV Readiness
```

| Gate | Purpose | Details |
|------|---------|---------|
| **Vanilla** | Bare boot | Tests new manifest/IFWI without Flexcon config |
| **Boot** | Flexcon + Moka | Per-target checks (Bmod/PCUdata/FullFW) |
| **Sanity** | FV content integration | Also used for SVOS migration |
| **FV Readiness** | Full FV content | Domain-level test execution |

### 15.4 FLEXCON Integration

- **FLEXCON** = Flexible Configuration methodology + toolkit for managing HW/SW platform configs
- Excel spreadsheet → `flexcon_generation.py` → JSON/XML → override scripts + plugin checkers
- 4 execution phases: HW/Fuse/BIOS overrides → Register workarounds → Config checking → Post-check
- `flexcon_simics.py` module for Simics platform presets
- Plugin system with Enable/Disable/Warn severity, Pre/Normal/Post ordering
- **THC use**: FLEXCON presets could configure THC BIOS knobs (port enable, protocol, GPIO routing)

---

## 16. Simics Validation Framework — Sloop & FiVE

> **Source**: Wiki research — page 2813471096 (ITSNVLPMFW space, v41), page 3214346559 (SRESIMICS, v7), page 4141751804 (SRESIMICS, v5)

### 16.0 Unified Validation Framework

Sloop and FiVE are part of a unified **Simics Validation Framework** (hub page 3214346559). The framework provides:
- **Sloop**: Async co-routine library for BFMs and test scripts
- **FiVE**: Python-based device extension and test development framework
- **Collateral-Based Testing**: Test methodology tied to VP collateral

S3E Tech Exchange recordings available: Sloop (WW11'23), FiVE overview, Validation Framework overview.

### 16.1 Sloop

**Sloop** = Simics Python co-routine library for async testing and BFMs. Discovered from WW11'23 video presentation. Enables asynchronous test patterns in Simics Python scripts.

### 16.2 FiVE

**FiVE** = Python-based device extension and test development framework for Simics.

6-step learning path:
1. PM overview video (WW12'21)
2. Chassis PM framework wiki (page 1966866946)
3. Simics async/coroutines video + `simics-base` PR #3233 for docs
4. Extensions via `generic-chassis-device` README + `ngu_pma.py` example
5. Tests via `libtest/pm` README + examples
6. Sloop async BFM testing (WW11'23) video

### 16.3 FiVE CLI Usage

FiVE provides a CLI (`fwrun_five`) for practical validation tasks such as fuse override generation:

```bash
# Export fuse overrides for a specific DUT
fwrun_five --export_fuses -o <output_dir> cold_boot_only --dut <dut-name>
# Example: --dut rzl-s-a0
# Generates per-management-unit files like: dcode_cdie_0_fuse_override.txt
```

FiVE is actively used in PM/fuse validation workflows, Punit/DMU Fmod integration, and Pcode/Dcode trace analysis.

### 16.4 Key Repos

| Repo | Content |
|------|---------|
| `applications.simulators.simics.simics-base` | Simics base (including Sloop) |
| `applications.simulators.isim.vp` | VP models (develop branch, `mtl/common` dirs) |

### 16.5 THC Applicability

Sloop async patterns could be used for:
- Asynchronous THC interrupt testing (wait for GPIO edge without blocking)
- DMA completion polling with timeout
- Multi-port concurrent test orchestration (THC0 + THC1 in parallel)
- PM state transition verification with async event monitoring

---

## 17. RDL/Nebulon XML-to-DML Register Conversion

> **Source**: Wiki research — page 1172842134 (PPAVirtualPlatforms space, v16)

### 17.1 Overview

Two conversion flows exist for generating DML register definitions from hardware description formats:

| Flow | Input Format | Description |
|------|-------------|-------------|
| **Flow #1** | SystemRDL (with UDPs) | Industry-standard SystemRDL → intermediate XML → DML 1.4 |
| **Flow #2** | Nebulon XML | Intel Nebulon XML → intermediate XML → DML 1.4 |

Both flows share the same 2nd step that consumes an intermediate XML format to produce DML register code.

### 17.2 THC Applicability

If THC register definitions are available in SystemRDL or Nebulon XML format, DML register banks can be **auto-generated** rather than hand-coded. This complements the OSAL2DML pipeline (Section 13) — OSAL2DML uses OSXML input, while this flow handles RDL/Nebulon input.

---

## 18. VP Testing Strategy & Quality Gates

> **Source**: Wiki research — page 4232780202 (SRESIMICS space, v30)

### 18.1 Test Type Hierarchy

| Level | Type | Framework | Example for THC |
|-------|------|-----------|-----------------|
| **Unit** | Model-level | ISCTLM / FiVE | THC register R/W masks, reset defaults |
| **Integration** | Multi-model | VTCs / IPSV | THC + SPI transactor + touch device |
| **System** | Full VP | OS boot / FW load | Windows driver + THC + touch panel E2E |

### 18.2 Quality Gates

| Metric | Tool | Target |
|--------|------|--------|
| **Code coverage** | GCOV/LCOV via SimCloud DevTools | Track % of DML lines exercised |
| **VTC pass rate** | CI pipeline (Bronze/Silver/Gold) | 100% pass for release gates |
| **Bug escape rate** | Quality Events (QEs) in HSDES | Minimize silicon bugs that should have been caught in Simics |

### 18.3 Test Strategy vs Test Plan

- **Test Strategy** = organization-wide approach (applies across all IPs including THC)
- **Test Plan** = project-specific (e.g., NVL THC Simics test plan with specific VTC list + coverage goals)

---

## 19. Modeling Requirements Creation Process

> **Source**: Wiki research — page 1966384489 (SRESIMICS space, v14)

### 19.1 Process

Domain owners + technical leads create **executable feature modeling requirements** that become modeling tasks for VP developers:

```
Domain Owner (FV) → Feature Requirement → Modeling Task → VP Developer → Model Update
```

### 19.2 Key Concepts

| Concept | Description |
|---------|-------------|
| **Executable feature requirements** | Requirements that can be directly validated against the model |
| **Domain ownership** | FV domain (e.g., THC) defines what the model must support |
| **Common process** | Same requirement creation flow across all projects/platforms |

### 19.3 THC Applicability

THC FV domain should author executable feature requirements for:
- Register-functional accuracy (all MMIO registers per HAS)
- Protocol support (HIDSPI/HIDI2C transaction sequences)
- Power state transitions (D0i2, D3, WoT)
- DMA engine behavior (PRD ring, streaming mode, display sync)
- Interrupt routing (GPIO → MSI path)

---

## 20. PMCLite Implementation Details

> **Source**: Wiki pages 2755363002, 3356038208, 1274653307, 2765135286 (THCipsv space)

THC supports 4 D3 levels for power management:
- **D0i2**: HW-autonomous power gating (no SW involvement)
- **D3**: SW-initiated via PMCSR (PM Control Status Register) write — no power gating
- **D3Hot**: SW-initiated via PMCSR + power gating (PMCLite orchestrated)
- **D3Cold**: Deepest state — full save/restore of 28 registers, PMCSR-triggered

D3 entry is triggered by software writing to the PCI PMCSR register. The PMCLite firmware then orchestrates the power gating sequence via sideband messages.

### 20.1 PMCLite Backdoor Register Access

For debug/validation, PMCLite registers can be accessed directly via backdoor address mapping:

| Component | Base Address | Notes |
|-----------|-------------|-------|
| PMCLite backdoor base | `0x01000000` | Simics backdoor for direct PMCLite register R/W |
| THC-PMCLite connection | Event port + Drive port | Minimal: PMCLite drives THC power signals |

**Python API for PMCLite backdoor** (IPSV test framework):
```python
# Read PMCLite register via backdoor
value = thc.pmclite.backdoor.read(0x01000000 + offset)
# Write PMCLite register
thc.pmclite.backdoor.write(0x01000000 + offset, value)
```

### 20.2 PMCLite Vector Compilation

PMCLite behavior is defined by compiled ROM vectors:

- **Tool**: `pmc_kit_rom_parser.pl` (Perl script from PMC team)
- **Output**: `pmcrom.hex` — binary ROM image loaded by Simics PMCLite model
- **Location**: PMCLite_Vector folder in IPSV repo (per Section 5.4)
- **Usage**: Compile custom PMCLite vectors for testing specific PM sequences (D0i2 entry/exit, D3 save/restore, PG handshake)

### 20.3 28 Save-and-Restore (SnR) Registers

D3Cold entry requires saving 28 THC registers; D3Cold exit requires restoring them in order. The full SnR register list (from wiki page 2977738178) includes:

- THC port control and configuration registers
- DMA control registers (RXDMA1, RXDMA2, TXDMA, SWDMA)
- Interrupt configuration registers (DEVINT_CFG_1, DEVINT_CFG_2)
- Coalescing and timestamp configuration
- Protocol-specific registers (SPI config, I2C sub-IP state)
- LTR configuration registers

> **⚠️ CRITICAL**: The exact register list varies by platform (PTL+ overhauled D3 flow). Always verify against the THC IP HAS Section 11 (Power Management) for the authoritative SnR register list per platform.

---

## 21. Sonora3 Testcard Details

> **Source**: Wiki pages 1894180152, 2794294764 (THCipsv space)

### 21.1 Architecture Differences from Sonora2

| Feature | Sonora2 | Sonora3 |
|---------|---------|---------|
| Memory | OCM (On-Chip Memory) | **DDR** (external) |
| Cable | Multiple | **Single HT3 cable** |
| Pin mirroring | N/A | Required for DX7/HAPS80 |
| 50MHz Quad SPI | Supported | **Known issues** — intermittent failures |

### 21.2 RAMLess HIDI2C Mode

Sonora3 supports RAMLess HIDI2C operation with 4 data modes controlled via `ramless_datamode_ctrl` attribute (thc_vdm):

| Mode | Description |
|------|-------------|
| Mode 0 | Standard — device has internal SRAM for report buffering |
| Mode 1 | RAMLess — reports generated on-the-fly from internal state |
| Mode 2 | RAMLess with coalescing — multiple reports before interrupt |
| Mode 3 | RAMLess streaming — continuous data output |

### 21.3 Image Tracking

Sonora3 testcard images (firmware) are tracked per-platform in the THCipsv wiki. Python test scripts reference specific image versions for compatibility:
- Image selection affects DDR vs OCM behavior
- 50MHz quad SPI issues may require image-specific workarounds
- See wiki page 1894180152 for current image versions

---

## 22. THC Generation Mapping (IPSV vs Post-Silicon Perspective)

> **Source**: Wiki page 3028682606 (THCipsv space)

**⚠️ IMPORTANT**: The THC generation numbering differs between IPSV (pre-silicon) and post-silicon validation teams:

| Generation | IPSV Perspective | Post-Silicon Perspective |
|------------|-----------------|------------------------|
| **Gen1.0** | **LKF** (Lakefield) | TGL, ADL |
| **Gen2.0** | **TGL** (Tiger Lake) | ADP-LP+ |
| **Gen3.0** | MTL-M, ARL | MTL-M, ARL |
| **Gen4.0** | LNL-M | LNL-M |
| **Gen4.1** | PTL, WCL | PTL, WCL |
| **Gen4.2** | NVL, RZL, TTL | NVL, RZL, TTL |

- IPSV includes LKF as Gen1.0 (first silicon with THC IP for IPSV bring-up)
- Post-silicon starts Gen1.0 at TGL/ADL (first production-grade THC)
- Gen3.0+ numbering aligns between both perspectives

---

## 23. TTL PCD-H Platform Tickets

> **Source**: Wiki page 4457832574 (THCipsv space)

TTL (Timber Trail) PCD-H die carries forward THC model tickets from PTL, with platform-specific updates:

- **GPIO pullup configuration**: TTL GPIO pad settings differ from PTL — requires model attribute updates
- **simple_io_0_en**: Must be enabled in TTL model for THC GPIO interrupt path
- **Regflow**: TTL uses updated regflow definitions — verify register access paths
- **⚠️ Ticket placeholders**: Many TTL tickets are cloned from PTL with minimal changes — always verify TTL-specific content

---

## See Also

- **SKILL.md** — Core THC Simics concepts, VP architecture, FV strategy, gap analysis
- **models.md** — SPI transactor, thc_vdm, Fmod, touch device architectures, SPARK history, OSAL2DML
- **operations.md** — Setup, debug, per-platform guide, driver install, S0ix PM, FLEXCON, record/replay
- **Post-silicon sub-skills**: `fv-thc/registers`, `fv-thc/hidspi`, `fv-thc/hidi2c`, `fv-thc/dma`, `fv-thc/power`, `fv-thc/platform`, `fv-thc/debug`, `fv-thc/driver`, `fv-thc/wot`

---

*Source: THC SIMICS Pre-Silicon Knowledge Base v2.4 (thc_simics_presi_knowledge.md), sections S12, S18, S24-28, S30-32 + Intel Wiki Research (52 pages studied across 7+ wiki spaces, 32+ searches, redo verification 2026-03-26)*
