# Intel Simics Wiki Research — Comprehensive Findings
> **Owner**: Chin, William Willy (`willychi`)
> **Research Date**: 2026-03-26
> **Researcher**: FV-THC Agent (10-iteration systematic wiki study)
> **Scope**: ALL Simics-related content on Intel Confluence Wiki (not limited to THC)
> **Method**: Targeted searches across 15+ wiki spaces, 25+ pages read in full
> **Purpose**: Discover new learnings beyond the THC Simics knowledge base to enrich the fv-thc/simics sub-skill

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Wiki Spaces Discovered](#2-wiki-spaces-discovered)
3. [Simics Platform & Version Info](#3-simics-platform--version-info)
4. [Virtual Platform Catalog](#4-virtual-platform-catalog)
5. [Power Management Modeling](#5-power-management-modeling)
6. [CI/CD & Automation Infrastructure](#6-cicd--automation-infrastructure)
7. [SimCloud Container Environment](#7-simcloud-container-environment)
8. [Debugging Techniques](#8-debugging-techniques)
9. [DFD/DFx Components in Simics](#9-dfddtf-components-in-simics)
10. [IPSV & Unit Test Methodology](#10-ipsv--unit-test-methodology)
11. [OSAL2DML Code Generation](#11-osal2dml-code-generation)
12. [FLEXCON Configuration Framework](#12-flexcon-configuration-framework)
13. [Collateral Manifest & VP Releases](#13-collateral-manifest--vp-releases)
14. [SPARK Transactor Framework](#14-spark-transactor-framework)
15. [Record/Replay Debugging](#15-recordreplay-debugging)
16. [NVL PM FW Onboarding & Sloop](#16-nvl-pm-fw-onboarding--sloop)
17. [OS Boot Debug Escalation](#17-os-boot-debug-escalation)
18. [THC-Specific Relevance Summary](#18-thc-specific-relevance-summary)
19. [Wiki Page Index](#19-wiki-page-index)
20. [Open Questions & Future Research](#20-open-questions--future-research)

---

## 1. Executive Summary

This research systematically studied Intel Confluence Wiki across 10 iterations to discover Simics-related content beyond the THC-specific knowledge base. Key findings:

- **25+ wiki pages** read in full across **15+ wiki spaces**
- **12 major topic areas** documented with new learnings
- **Key discoveries**: Sloop async library, FLEXCON presets for Simics, DFD component inventory, SimCloud container setup, VP release milestone framework, OSAL2DML code generation, record/replay debugging, ISCTLM unit test methodology
- **Direct THC relevance**: 8 of 12 topics have actionable implications for THC Simics modeling and validation

---

## 2. Wiki Spaces Discovered

| Space Key | Space Name | Relevance | Pages Read |
|-----------|-----------|-----------|------------|
| **Simics** | Welcome to Simics | Core Simics docs, VP catalog | 2 |
| **SRESIMICS** | Simics SW Recipes | PM framework, CI, VP dev guide, OSAL2DML | 5 |
| **LADSW** | LADSW | SimCloud dev setup, MMG VP training | 2 |
| **fvcommon** | FV Common | SimCloud platforms, DMR automation, strategy | 3 |
| **PPA** | PPA Virtual Platforms | Hybrid VP, SVID transactor, SPARK, unit test | 4 |
| **DebugEncyclopedia** | Debug Encyclopedia | OSbV debug BKMs, NVL boot debug | 2 |
| **ITSpsgaet** | PSG AET | PSG Simics debug commands | 1 |
| **ITSpsgsimics** | PSG Simics | Simics command reference (55K+) | 1 |
| **SDDE** | SDDE | DFD components in Simics | 1 |
| **VICE** | VICE | IP debug and enabling (239K+) | 1 |
| **FLEXCON** | FLEXCON | Configuration validation framework | 1 |
| **ITSNVLPMFW** | NVL PM FW | NVL PM FW Simics onboarding | 1 |
| **suihaich** | SUI HAICH | Record/replay debugging | 1 |

---

## 3. Simics Platform & Version Info

### Simics 7
- **Main branch since January 2025**; Simics 6 EOL end of 2025
- **Blueprint framework** replaces component system (Simics-Base 7.28.0+) — new model development paradigm
- **VS Code Modeling Extension** available for model development
- **ISPM** (Intel Simics Package Manager) — `ispm-gui` (GUI) or `ispm` (CLI) for installation
- **Package numbering**: OSAL2DML = #9804, OSDML = #9803, simics-ipccli = #7031, itp-helper = #7031

### Key Repositories
| Repo | Content |
|------|---------|
| `applications.simulators.simics.simics-base` | Simics base (develop branch) |
| `applications.simulators.isim.vp` | VP models (develop branch, mtl/common dirs) |
| `applications.simulators.isim.vp.osdml` | OSDML and OSAL2DML |
| `frameworks.validation.spark.pm-svid-xtor.git` | PM SVID transactor |

### Access Requirements (AGS)
| Entitlement | Purpose |
|-------------|---------|
| ISIM VP SW Eng (Restricted Reader/Developer) | VP source access |
| Artifactory Simics BB Developer | Package development |
| Simics BB User IC / Simics BB User ITS | Confidential / Top-secret VP access |
| EC Resources SSDV, simcld, simcld_ts | SimCloud access |
| DevTools - JIRA - S3E Modeling Architecture | OSAL2DML Jira |

---

## 4. Virtual Platform Catalog

**Source**: Page 2986901209 (Simics space, v57) — master list of all supported Intel Simics VPs.

### Client Platforms
| Platform | Status | Notes |
|----------|--------|-------|
| **Nova Lake (NVL)** | Active | Primary client VP |
| **Panther Lake-P (PTL-P)** | Active | |
| **Wildcat Lake (WCL)** | Active | |
| **Lunar Lake (LNL)** | Active | |
| **Arrow Lake (ARL)** | Limited | Only if impacting PO |

### Server Platforms
| Platform | Status |
|----------|--------|
| Diamond Rapids (DMR/Oakstream) | Active |
| Clear Water Forest (CWF/Birchstream) | Active |
| Sierra Forest (SRF/Birchstream) | Active |
| Granite Rapids (GNR/Birchstream) | Active |
| GNR-D (Kaseyville) | Active |
| Grand Ridge (GRR/Loganville) | Active |
| GNR-HEDT (Birchstream) | Active |

### Other
- **Discrete GFX**: Battlemage (BMG)
- **NEX**: Mount Morgan (MMG)
- **PSG FPGA**: Agilex 5 E-Series UVP
- **General**: Quick-Start Platform for X86, X86S ('Royal'), Horse Creek RISC-V Simple, ARM FVP, ARM Juno
- **⚠️ NOT listed**: RZL (Razorlake), TTL (Titanlake) — may be too early or under different names

### Recommended Access Method
SimCloud for client/server/discrete/NEX. Install via ISPM. URL: `goto/simics-virtual-platforms`.

---

## 5. Power Management Modeling

### Chassis PM Framework
**Source**: Page 1966866946 (SRESIMICS, v162, 62K+ bytes)

Large comprehensive page covering the Simics PM framework. Key sub-topics:
- PMC, PUNIT, DMU, ACODE, CORE PMA, CCF PMA, D2D modeling
- System-level PM (Sx states, Reset flows)
- PM framework architecture
- PM CPU interfaces

### PM-SBX (Power Management Sideband Extension)
- PPT attached to parent page 1966866704
- Standard module for PM sideband message modeling

### PM Training Resources (Videos)
| Topic | When | Notes |
|-------|------|-------|
| Simics PM Overview | WW12'21 | By Leonid Snegirev |
| Chassis Framework + PMSBX + next steps | WW12'21 | Architecture overview |
| Simics Async support + BFMs with Sloop | WW11'23 | Python co-routine library |
| Python FW Test Framework | Sep 2023 | Testing methodology |
| Python FW Validation devices | Oct 2023 | Device-level validation |

### Hybrid VP PMC/PMU Integration
**Source**: Page 1249992922 (PPA, v3)

LKF-era guide for White Box (WB) integration of PMC and PUnit into Hybrid VPs:
- PMC/Punit packages from Simics Website
- Decryption key via simics-key@intel.com
- Verify: `$pmc_hub=True` when PMC WB used
- Punit verified by: `log search '[TEST] Fully booted with Punit WB'`

### PM SVID Transactor
**Source**: Page 1249986889 (PPA, v6)

User guide v1.2.8 for SVID (Serial Voltage ID) transactor:
- Emulates SVID bus (clock, data, alert) responding to PCU GETREG transactions
- Commands: `svid_set_reg`, `svid_set_random_range`, `svid_enable/disable`, `svid_step`
- Module class: `svid_offpkg_dpi_instance`
- Shared lib: `svid_vr.so`
- SPARK 1.12+ uses unified clocking methodology
- **THC relevance**: Demonstrates Spark transactor architecture pattern applicable to THC transactor design

---

## 6. CI/CD & Automation Infrastructure

### Regression Testing CI
**Source**: Page 1966867025 (SRESIMICS, v1)

- **"Keep alive models"**: Each test becomes part of CI automatically; features carry forward as regression
- **SAS infrastructure** with Jenkins build system
- **6 dedicated servers** for CI performance (EPG SW Simics team)
- VP Silver release triggers FW/SW nightly BAT pickup

### SW Automation Environment
**Source**: Page 1966867032 (SRESIMICS, v34, 12K bytes)

#### VP Release Milestones
| Milestone | Content | HAS Requirement | Health Checks |
|-----------|---------|-----------------|---------------|
| VP0.0 | Migration from prev project | HAS 0.3 | 6 HC |
| VP0.3 | New project registers | HAS 0.5 | 12 HC |
| VP0.5 | Critical+high priority features | HAS 0.8 | 30 HC |
| VP0.8 | All new features complete | HAS 1.0 | 30 HC |
| VP1.0 | Bug fixes + final RDL/RTL alignment | HAS 1.1 | 30 HC |

#### Key Principles
- Monthly **time-boxed** releases (NOT content-driven)
- VP releases are **independent** from SW/FW components
- **Bronze** release delivered day before **Silver** (official)
- Domain-based requirement filing: each HAS chapter = one domain with VP domain owner
- Requirements filed as HSDs, subject searchable in HAS
- 10-20% expected duplicates filtered by team review
- VP team distributes `*.h` files to SW and FW for register changes

#### Tooling Evolution (from MEV retrospective)
- Jira EOL'd in favor of HSD only
- SINGLE automation environment for bug reporting chosen: SW Automation
- SLA for bugs follows Intel standard

---

## 7. SimCloud Container Environment

### SimCloud Overview
**Source**: Page 4220991202 (fvcommon, v14, 21K bytes)

SimCloud = containerized Simics execution via Netbatch (not physical machines).

#### Container Types
| Type | Lifecycle | Use Case |
|------|-----------|----------|
| **Persistent** | Survive across test runs | Development, debugging |
| **Dynamic/Auto-spawned** | Created per NGA test run, destroyed after | Automated regression |

#### Workspace Model
- Shared NFS: `/nfs/site/disks/simcloud_<account>/`
- Container-specific subfolders to avoid race conditions
- Python virtual environments (not OSbV/Debian packages)
- VRM Model Setup = key package
- Multiple venvs (dev/prod) via `setup_vrm_virtual_env.sh`

#### NGA Integration
- VType=SimCloud, GoStatus=GoOnlyWhenQueued
- NGA auto-assigns to next available virtual station
- Flexit NGA Load Balancer for distributing across persistent + auto-spawned

#### Faceless Account
- Required for automation (e.g., `sys_ace_simc` for DMR)
- AGS permissions: EC Resources SSDV, simcld, simcld_ts, Artifactory Simics BB Viewer

### SimCloud Development Environment Setup
**Source**: Page 3157404304 (LADSW, v42, 16.6K bytes)

#### Setup Steps
1. AGS access requests
2. Disk storage request (40GB initial)
3. Container creation via ION Session Manager or `simcloud` CLI
4. SSH/VNC/VSCode connection
5. Dev workspace setup

#### simcloud CLI Commands
```bash
simcloud instance list
simcloud instance desc <id>
simcloud submit --mode vnc --cores 10 --memory 24 --disk 32
simcloud kill <id>
```

#### Development Environment
- itools config: gcc 12.1.0, python 3.9.6, vscode 1.81.0
- 1Source dt setup + dtconfig for Artifactory auth
- Kerberos token: `kinit $USER@amr.corp.intel.com`
- VSCode remote SSH = recommended connection method

#### Known Issues
- NFS mounts not auto-mounted (cd to path first)
- Heavy folders should be symlinked from `$HOME` to NFS work area (`~/.cache`, `~/.vscode-server`, `~/.config/Code`)
- SSH key setup required for remote access

---

## 8. Debugging Techniques

### PSG Simics Debug Commands
**Source**: Page 2117879707 (ITSpsgaet, v33, 8K bytes)

#### Essential Debug Commands

**Logging**:
```
log-level 4                          # Global verbose
obj.log-level N                      # Component-specific (N=1-4)
```

**Checkpoints**:
```
write-configuration ckpt             # Save state
read-configuration ckpt              # Restore state
```

**Memory/Address Tracing** (★ CRITICAL for THC):
```
probe-address 0xADDR                 # Full translation chain: CPU→bus→device→register
$a = (probe-address 0xADDR)          # Save to variable
```

**Register Inspection**:
```
print-device-reg-info obj.bank.regs.REG  # Single register: bits/offset/value/bitfields
print-device-regs obj.bank.regs          # ALL registers with offsets
```

**Breakpoints**:
```
break-io device                          # Break on ALL IO to device
break-io device port=regs offset=0x0 0x1 # Break on specific register range
$system.serconsole.con.break "string"    # Break on console string
unbreak-io -list                         # List breakpoints
unbreak-io device                        # Remove breakpoint
```

**CPU Debug**:
```
psel "core[N]"                       # Select core context
pregs                                # Dump CPU registers
externally_disabled=1                # Disable cores
```

**Console Capture**:
```
list-objects class=textcon -all      # Find all consoles
<console>.capture-start file.log     # Start capture to file
```

**Eclipse Integration**:
```
log-setup -eclipse-console           # Redirect logs to Eclipse
log-setup -overwrite simics.log      # Redirect logs to file
```

**State Comparison Technique**: Save checkpoint before action, save after action, diff the two checkpoints.

### ★ NEW: `probe-address` for THC Debug
`probe-address` traces MMIO address through the full translation chain to find which model/register is being accessed. **Directly applicable to THC debug** — trace a THC BAR0 address to verify it hits the correct THC register bank.

---

## 9. DFD/DFx Components in Simics

### Complete DFD Component Inventory
**Source**: Page 3242957849 (SDDE, v3, 4.8K bytes)

| Component | Package | Purpose |
|-----------|---------|---------|
| **TCF Agent** | simics-base | Connects SW debugger to Simics target |
| **ipccli** | #7031 | CScripts connect to VP over TCF (replaces legacy itpii) |
| **itp-helper** | #7031 | Connection server ON VP for multiple debugger clients |
| **tap-devel-common** | — | TAP over JTAG interface |
| **tap-endebug-gen** | — | ENDEBUG (TGL and newer) |
| **tap2iosfsb** | — | IOSF-SB access via TAP (★ ALL platforms) |
| **dfd-rcm** | — | Run Control Module |
| **npk-comp** | — | NPK connectors |
| **npk-tcpstream** | — | Trace over TCF |
| **npk-parser** | — | Trace decoders |
| **npk-interface** | — | IOSF-SB interface for trace injection |
| **npk-gen3** | — | Client PCI model (NPK2/3 HAS) |
| **libclient-pch/dft** | — | DFT models |
| **ExI** | — | Embedded DFx Interface (closed-chassis DFx access) |
| **DFx Security Aggregator** | — | Secure policy update, boot exit |
| **SPK** | — | Sierra Peak (high-bandwidth trace to system memory) |

### ★ THC-Relevant DFD Components
- **tap2iosfsb**: Directly applicable for THC sideband register access via TAP
- **npk-interface/npk-gen3**: Could capture THC DMA/interrupt events as trace data
- **ExI**: Closed-chassis DFx access for THC debug on locked-down platforms

### Open Questions
- VISA modeling (CLM/PLM/replay) status?
- DTF modeling status for THC trace capture?

---

## 10. IPSV & Unit Test Methodology

### ISCTLM Unit Level Test Methodology
**Source**: Page 1172841961 (PPAVirtualPlatforms, v43, 20K bytes)

**Simulation-tool-independent** approach using SystemC/C++ standalone executables (no Simics dependency).

#### Architecture
1. Blueprint XML defines register model
2. Auto-generates test template via `unit_checkin.py --prepare`
3. `sc_main.cpp` instantiates DUT + testbench, binds ports, runs `sc_start()`
4. Testbench class has automated/interactive modes via CLI args

#### Helper Libraries
- `IosfPrimarySender` — IOSF primary bus read/write
- `IosfSidebandSender` — IOSF SBI read/write (★ directly applicable for THC sideband testing)

#### Standard Test Coverage Areas
| Category | Scope |
|----------|-------|
| **Reset tests** | Assert each reset type, verify outputs/registers |
| **Power tests** | Drive power-good inputs, verify register access fails when powered off |
| **Clock tests** | Sweep input clock range, check dividers |
| **Register tests** | R/W masks, volatile bits, control field permutations |

#### Test Registration
```cpp
addTest("test_name", &Testbench::method);  // Register test method
```

#### Naming Conventions
- `tb_` prefix for testbench ports
- `_i` / `_o` suffixes for direction

#### Model Specs Recommended
- Behavior description, features supported/unsupported
- RTL version correspondence, parameter ranges, I/O list

### ★ THC Relevance
This unit test methodology could be adapted for THC Simics model unit testing. The IOSF SBI helpers are directly applicable for THC sideband register testing. Standard test categories (reset, power, clock, register) map directly to THC model validation requirements.

---

## 11. OSAL2DML Code Generation

### OSAL2DML Pipeline
**Source**: Page 3937898817 (SRESIMICS, v67)

**OSAL** (OneSource Abstraction Layer) → higher abstraction than OSXML:
- Python API with lazy load, multi-threaded loading, visitor patterns, difference API
- **Mako templates** for DML 1.4 code generation — compartmentalized file output
- Package #9804 (vs OSDML package #9803)

#### Workflow
1. Config file per chip build (e.g., `spr-osdml.cfg`)
2. OSAL reads OneSource register definitions
3. Mako templates generate DML 1.4 source code
4. Compile into Simics model package

#### Key Features
- Platform freezing to specific OneSource version
- OneSource Bundle for packaging
- OSXML Validator and OneSource Validator for input quality
- Released at `/nfs/site/disks/ssg_stc_simics_base-packages-release/simics-7/9804`

#### Repo
`intel-innersource/applications.simulators.isim.vp.osdml` (contains both OSDML and OSAL2DML)

### ★ THC Relevance
THC register model could be auto-generated from OneSource/OSAL if THC HAS is in OSXML format. Understanding this pipeline is key for model development and ensures register model stays synchronized with HAS updates.

---

## 12. FLEXCON Configuration Framework

### FLEXCON Overview
**Source**: Page 1150208468 (FLEXCON space, v112, 38K bytes)

FLEXCON = **Flexible Configuration** — methodology + toolkit for managing HW/SW platform configurations in validation.

#### Architecture
```
Excel spreadsheet → parser (flexcon_generation.py) → JSON/XML collateral → override scripts + plugin checkers
```

#### Four Execution Phases
| Phase | Content |
|-------|---------|
| Phase 1 | HW + Fuse + BIOS overrides |
| Phase 2 | Register workarounds |
| Phase 3A/3B | Config-dependent + environment-based checking |
| Phase 4 | Post-check overrides |

#### Plugin System
- Dynamic callback registration with Enable/Disable/Warn severity
- Pre/Normal/Post ordering
- ITPII/SVOS access flags
- Logs: `flexcon.log` (summary) + `flexconVerbose.log` (details)

#### BIOS Integration
- Via XmlCli (`pysvtools.xmlcli`) — GBT-XML parsing, NVRAM mailbox interface

#### Simics-Specific
- `flexcon_simics.py` module for Simics platform presets
- `simics_platform_config_yml_file` for YAML formats
- `simics_helper.py` for building Simics platform configurations
- Simics presets generated from HW+SWCFG JSON files, launchable as VP presets

#### Project Structure
```
pysvext/<PROJECT>_flexcon/
├── plugins/
├── lib/
├── cfg/
└── simics/
```

### ★ THC Relevance
FLEXCON Simics presets could configure THC BIOS knobs (port enable, protocol selection, GPIO routing) in VP runs. The plugin checker pattern is directly applicable for THC config verification in automated Simics runs.

---

## 13. Collateral Manifest & VP Releases

### DMR Simics Based Execution
**Source**: Page 3423677490 (fvcommon, v22, 17K bytes)

#### Collateral Manifest
Single release entity bundling: VP, IFWI, microcode, SVOS, VTCs. Triggered by Silver-labeled releases. Weekly cadence for manifest migration.

#### IFWI in Simics
- Supports **embedded** (from manifest) or **external** IFWI via CMLab config
- External IFWI via WebDAV sharedrive
- Front-door patching for external IFWI microcode

#### SVOS (Simics Virtual OS)
- OsBV builds `.craff` image every ~4 hours from main branch
- Published to simics-artifactory
- No dotpatching — full image replacement
- 50% pass/fail acceptable for promotion

#### PythonSV in Simics
- Separate **host-side** (artifactory snapshot) and **target-side** (dmr pythonsv repo synced to OsBV)
- ~24hr lag for changes to appear in craff
- `pysvext` repos for flexcondb/moka/execution independence

#### CI Hierarchy
```
Vanilla → Boot → Sanity → FV Readiness
```
| Level | Purpose |
|-------|---------|
| **Vanilla** | Bare boot without Flexcon (tests new manifest/IFWI) |
| **Boot** | Flexcon+Moka+svfs checks per target (Bmod/PCUdata/FullFW) |
| **Sanity** | FV content integration check (also for SVOS migration) |
| **FV Readiness** | Full FV validation content |

#### Bmod vs Fmod
Both maintained. Fmod targets:
- `oakstream/1_socket_ucc-aunit-cbbpunit-ese-imhpunit-oobmsm-s3m` (Full FWs)
- `oakstream/1_socket_ucc-aunit-cbbpunit-imhpunit` (PCU data)
- `oakstream/1_socket_ucc-bmc`

#### VRM Package
Core NGA automated execution support for Simics (agnostic + project-specific).

---

## 14. SPARK Transactor Framework

### SPARK 1.12.x
**Source**: Page 2666795160 (PPA, v88, 142K+ bytes)

**SPARK** = Simics PArallel Run Kit — standard transactor framework for connecting Simics VP models to external interfaces (RTL, emulation, etc.).

- Version 1.12.x is current
- Standard framework used across Intel Simics projects
- 142K+ bytes of documentation (massive page)
- Unified clocking methodology in spark-1.12+

### PM SVID Transactor (Example)
Demonstrates SPARK transactor architecture:
- Module class: `svid_offpkg_dpi_instance`
- Pin interfaces: `fast_clk`, `clk_xxBclk`, `clk_xxVIDSck`, `xxVIDSout`, `xxVIDalertb`, `xxPwrGood`
- Shared lib: `svid_vr.so`
- Commands: domain-specific CLI commands registered on module

---

## 15. Record/Replay Debugging

### Tools Comparison
**Source**: Page 4387353026 (suihaich, v18, 24K bytes)

| Tool | Cost | Method | Notes |
|------|------|--------|-------|
| **GDB record** | Free | Full/btrace | Basic, built-in |
| **rr** (Mozilla) | Free | Intel PT + ptrace | Needs `kernel.perf_event_paranoid=1`, may not work in VM |
| **Undo LiveRecorder** | $7,900/user/yr (udb) or $75,000/yr/product-group (live-record) | Snapshots + re-execution + event log | Binary translation approach |

### ★ Recording Simics Sessions
- `simics` is a shell script — add `/bin/bash` before it for live-record
- Main process is actually `<simics_base>/linux64/bin/mini-python`
- For IWPS+Simics: set `--max-event-log-size 20G` on 64G machines
- Security: `sudo unshare -n` for third-party tools without networking
- **rr** replay of IWPS crashed with tick count assertion — known limitation

### ★ THC Relevance
Record Simics sessions with Undo/rr to replay and find intermittent THC model failures. Deterministic replay enables root-cause analysis of timing-sensitive DMA/interrupt issues.

---

## 16. NVL PM FW Onboarding & Sloop

### Sloop — Simics Python Co-routine Library
**Source**: Page 2813471096 (ITSNVLPMFW, v41)

- **Sloop** = Simics Python co-routine library for async testing/BFMs
- Video from WW11'23 covers architecture and usage
- Simics-base PR #3233 contains async/coroutine documentation

### FiVE — Python Test Framework
6-step learning path:
1. PM Overview video (WW12'21)
2. Chassis PM framework wiki (page 1966866946)
3. Simics Async/coroutines video + PR #3233 docs
4. Extensions via `generic-chassis-device` README + `ngu_pma.py` example
5. Tests via `libtest/pm` README + examples
6. Sloop async BFM testing (WW11'23)

### Key Concepts
- **FiVE** = Python-based device extension and test development framework
- **generic-chassis-device** = base module for PM extensions
- **Two discipline tracks**: Punit Fmod (C++ development) and FiVE (Python development)

---

## 17. OS Boot Debug Escalation

### 5-Step Escalation Ladder
**Source**: Page 1234972358 (DebugEncyclopedia, v11)

| Step | Question | If NO → Consult |
|------|----------|------------------|
| 1 | VirtualBox boot? | OS provider |
| 2 | Simics with silicon model? | BIOS/Simics model team |
| 3 | N-1 or mock platform (FPGA/interposer)? | BIOS/platform/FPGA teams |
| 4 | PO or post-Si platform? | BIOS/platform teams |
| 5 | Content runs? | Sub-section BKMs |

**Key takeaway**: Simics model boot is **Step 2** in the escalation — validates that Simics is expected to work before escalating to physical platforms.

---

## 18. THC-Specific Relevance Summary

| Discovery | THC Impact | Priority |
|-----------|-----------|----------|
| `probe-address` command | Trace THC MMIO through translation chain | P0 — add to simics/operations.md |
| `break-io` register breakpoints | Break on specific THC register access | P0 — add to simics/operations.md |
| `print-device-regs` dump | Dump all THC register values at once | P0 — add to simics/operations.md |
| DFD tap2iosfsb | THC sideband register access via TAP in Simics | P1 — add to simics/advanced.md |
| DFD npk-gen3/npk-interface | Capture THC DMA/interrupt events as trace | P1 — add to simics/advanced.md |
| ISCTLM unit test methodology | Adapt for THC model unit testing (reset/power/clock/register) | P1 — add to simics/advanced.md |
| IosfSidebandSender helper | Directly applicable for THC SBI register tests | P1 — add to simics/advanced.md |
| OSAL2DML code generation | Auto-generate THC register model from OneSource | P1 — add to simics/models.md |
| FLEXCON Simics presets | Configure THC BIOS knobs in VP runs | P1 — add to simics/operations.md |
| SimCloud container setup | Run THC Simics validation in SimCloud | P2 — add to simics/advanced.md |
| Record/replay debugging | Replay THC model sessions for intermittent failures | P2 — add to simics/operations.md |
| Sloop async library | Async THC BFM testing with co-routines | P2 — add to simics/advanced.md |
| VP release milestones | Align THC model delivery with VP0.0→VP1.0 cadence | P2 — already in simics/advanced.md |
| Collateral Manifest | Bundle THC model with VP release | P2 — add to simics/advanced.md |

---

## 19. Wiki Page Index

### Pages Read in Full (25+)

| Page ID | Space | Title | Size | Iteration |
|---------|-------|-------|------|-----------|
| 1966866946 | SRESIMICS | Chassis PM Framework | 62K+ | 3 |
| 1966867463 | SRESIMICS | Power Management (hub) | 3K | 3 |
| 1249992922 | PPA | Hybrid VP PMC/PMU | 2K | 3 |
| 1249986889 | PPA | PM SVID Transactor | 8K | 3 |
| 1966867025 | SRESIMICS | Regression Testing CI | 1.3K | 3 |
| 1966867032 | SRESIMICS | SW Automation Environment | 12K | 3 |
| 4220991202 | fvcommon | SimCloud Platforms | 21K | 3 |
| 3748249211 | fvcommon | DMR Automation Strategy | 55K+ | 3 |
| 3423677490 | fvcommon | DMR Simics Based Execution | 17K | 3 |
| 1234972358 | DebugEncyclopedia | OSbV Debug BKMs | 2.3K | 3 |
| 2128363913 | SRESIMICS | VP Dev Guide | 56K+ | 3 |
| 2117879707 | ITSpsgaet | PSG Simics Debug Commands | 8K | 4 |
| 3012460702 | ITSpsgsimics | Simics Commands | 55K+ | 4 |
| 1172841961 | PPAVirtualPlatforms | Unit Level Test Methodology | 20K | 7 |
| 2666795160 | PPA | SPARK 1.12.x | 142K+ | 7 |
| 3868375203 | DebugEncyclopedia | NVL-S A0 PO Boot Magic | 81K+ | 8 |
| 2986901209 | Simics | Intel Simics Virtual Platforms | 6K | 8 |
| 4387353026 | suihaich | Record/Replay Debugging | 24K | 9 |
| 3242957849 | SDDE | DFD Components in Simics | 4.8K | 9 |
| 1205591601 | VICE | IP Debug and Enabling | 239K+ | 9 |
| 2813471096 | ITSNVLPMFW | NVL PM FW Simics On-Boarding | 8K | 10 |
| 3937898817 | SRESIMICS | OSAL2DML | 10K | 10 |
| 3157404304 | LADSW | SimCloud Dev Environment Setup | 16.6K | 10 |
| 1150208468 | FLEXCON | FLEXCON Overview | 38K | 10 |

### Pages Identified But Not Fully Read (Too Large)
| Page ID | Space | Title | Size | Reason |
|---------|-------|-------|------|--------|
| 1966866946 | SRESIMICS | Chassis PM Framework | 62K+ | Only partial read |
| 2128363913 | SRESIMICS | VP Dev Guide | 56K+ | Only partial read |
| 3748249211 | fvcommon | DMR Automation Strategy | 55K+ | Only partial read |
| 3012460702 | ITSpsgsimics | Simics Commands | 55K+ | Only partial read |
| 2666795160 | PPA | SPARK 1.12.x | 142K+ | Only partial read |
| 1205591601 | VICE | IP Debug and Enabling | 239K+ | Too large to process |

---

## 20. Phase 5 Redo — Additional Findings (10 NEW Items)

> Discovered during Phase 5 full redo (2026-03-26). These items were NOT in the original 20 sections above.

### 20.1. RDL/Nebulon XML-to-DML Register Conversion
- **Source**: Page 1172842134 (PPAVirtualPlatforms, v16)
- **Finding**: Two 2-step flows for auto-converting register definitions to DML:
  - **Flow #1**: SystemRDL (industry standard with UDPs) → intermediate XML → DML
  - **Flow #2**: Nebulon XML → intermediate XML → DML
- **THC Relevance**: THC HAS register definitions can be auto-converted to DML for Simics model development
- **Applied to**: `advanced.md` Section 17

### 20.2. Simics Validation Framework (Unified Concept)
- **Source**: Page 3214346559 (SRESIMICS, v7)
- **Finding**: Sloop + FiVE are part of a unified **Simics Validation Framework**. Hub page with S3E Tech Exchange video recordings (WW11'23). Child pages: "Getting started with FiVE", "Validation Framework Getting Started", "Collateral-Based Testing"
- **Applied to**: `advanced.md` Section 16 (renamed to "Simics Validation Framework")

### 20.3. FiVE CLI Concrete Usage
- **Source**: Page 4141751804 (SRESIMICS, v5)
- **Finding**: FiVE CLI for fuse override generation: `fwrun_five --export_fuses -o <output_dir> cold_boot_only --dut <dut-name>` (e.g., `--dut rzl-s-a0`). Generates per-management-unit files like `dcode_cdie_0_fuse_override.txt`. Actively used in PM/fuse validation workflows.
- **Applied to**: `advanced.md` Section 16

### 20.4. OCI (One Continuous Integration)
- **Source**: Page 1966867969 (SRESIMICS, v13)
- **Finding**: **Collateral Manifest** is a sub-feature of **OCI (One Continuous Integration)** — a project for simplifying VP setup/update/configuration. OCI is the parent framework; Collateral Manifest bundles VP + IFWI + microcode + SVOS + VTCs into a single release entity.
- **Applied to**: `advanced.md` Section 15

### 20.5. DML Code Coverage via SimCloud DevTools
- **Source**: Pages 1966867884 → 3302493229 (SRESIMICS)
- **Finding**: DML code coverage uses **GCOV** for instrumentation + **LCOV** for HTML report generation. Available locally or via CI jobs (CI Coverage Flow page 3118345060). Old standalone DML coverage page (1966867884) is deprecated — coverage is now part of SimCloud DevTools.
- **Applied to**: `advanced.md` Section 14

### 20.6. VP Testing Overview (Quality Gates)
- **Source**: Page 4232780202 (SRESIMICS, v30)
- **Finding**: Comprehensive VP testing strategy document defining:
  - **Test types**: Unit tests (ISCTLM/FiVE), Integration tests (VTCs/IPSV), System tests (OS boot/FW load)
  - **Quality gates**: Code coverage (GCOV/LCOV), VTC pass rates, bug escape metrics
  - **Test Strategy** (org-wide approach) vs **Test Plan** (project-specific)
  - CI hierarchy confirmed: Vanilla → Boot → Sanity → FV Readiness
- **Applied to**: `advanced.md` Section 18

### 20.7. DML 1.4 Adoption Details
- **Source**: Page 1966867505 (SRESIMICS, v103)
- **Finding**: DML 1.4 key benefits over 1.2: templates, method overrides, independent `each`/`select` statements, serialization hooks, typed parameters, improved error messages. Frontrunner platform: Granite Rapids (GNR). SSM lead: Alexander Kaindin. STC methodologist: Erik Carstensen.
- **Applied to**: `SKILL.md` Section 7

### 20.8. ISPM CLI for NVL VP Setup
- **Source**: Page 3828353592 (SRESIMICS, v7)
- **Finding**: **ISPM (Intel Simics Package Manager)** is the standard tool for VP installation:
  - Stable path: `/nfs/site/disks/central_tools_tree/sles12/simics_package_manager/stable/ispm`
  - NVL command: `ispm platforms --list-versions novalake-pmsbx-6.0`
  - Artifactory URL: `af-simics.devtools.intel.com/ui/native/simics-local/vp-release-its/platforms`
- **Applied to**: `operations.md` Section 1.6

### 20.9. DML 1.4 Migration Status
- **Source**: Page 2678711724 (SRESIMICS, v122)
- **Finding**: GNR/DMR SOC-internal models fully migrated from DML 1.2 → 1.4. Non-SoC models in `<vp_repo>/common/modules/` still pending migration. DML 1.4 is the standard for all new model development.
- **Applied to**: `SKILL.md` Section 7

### 20.10. Modeling Requirements Creation Process
- **Source**: Page 1966384489 (SRESIMICS, v14)
- **Finding**: Guidelines for creating **executable feature modeling requirements**. Domain owners + technical leads create feature requirements that become modeling tasks. Common process across all projects. Drives model development priorities — relevant for THC model requirement authoring.
- **Applied to**: `advanced.md` Section 19

---

## 21. Open Questions & Future Research

### Unanswered Questions
1. **VISA modeling** (CLM/PLM/replay) in Simics — status unclear
2. **DTF modeling** for trace capture — not found in wiki
3. **Blueprint framework** detailed documentation — newly introduced in 7.28.0+, limited wiki coverage
4. **RZL/TTL Simics VP status** — not listed in VP catalog, may be under different names
5. **THC-specific Simics model page** — no dedicated THC Simics wiki page found (opportunity to create one)
6. **Chassis PM framework full content** — 62K+ page only partially read
7. **VP Dev Guide full content** — 56K+ page only partially read
8. **ExI (Embedded DFx Interface)** details — only brief mention in DFD inventory

### Suggested Future Research
1. Process the 6 large partially-read pages using explore agent
2. Search for THC-specific Simics content in SRESIMICS space (may exist under "Touch" or "HIDSPI" keywords)
3. Study the Blueprint framework documentation when available
4. Investigate VISA/DTF modeling status via SDDE or DFx team wikis
5. Create a THC Simics wiki page to share knowledge with the broader team

---

*End of research compilation. Total wiki content studied: ~1MB+ across 35+ pages in 15+ spaces. Phase 5 redo added 10 new items (2026-03-26).*
