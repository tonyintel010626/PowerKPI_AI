# NVU Skill Evaluation Tests

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Purpose**: Evaluate FV-NVU agent accuracy across all 11 sub-skills + self-improvement toolchain
> **Last Updated**: 2026-03-28

---

## Registers Sub-Skill

### NVU-REG-001: BAR0 Size and Mapping
**Prompt**: "What is the NVU BAR0 size and what internal address does it remap to?"
**Expected**: BAR0 is 64 KB MMIO, remapped to internal address `0x8000_0000` via the IOSF2AXI bridge.
**Pass Criteria**: Must mention 64 KB, `0x8000_0000`, and IOSF2AXI bridge.

### NVU-REG-002: PCI Function Count
**Prompt**: "How many PCI functions does NVU expose and what does each do?"
**Expected**: 2 PCI functions. FN0: NVU SW Driver (64KB BAR, IPC IRQ to host). FN1: Camera/VOD (4MB BAR at `0x8010_0000`).
**Pass Criteria**: Must mention 2 functions, FN0 for driver/IPC, FN1 for camera/VOD.

### NVU-REG-003: Interrupt Mechanism
**Prompt**: "What interrupt mechanism does NVU use — MSI, MSI-X, or legacy?"
**Expected**: MSI via WIRE2MSI method (MSI_GEN block). MSI-X is NOT enabled (`ENABLE_MSIX_CAP=0`). Legacy IRQ also supported (AssertIRQ/DeAssertIRQ sideband).
**Pass Criteria**: Must state MSI is primary, MSI-X is disabled, and mention WIRE2MSI.

### NVU-REG-004: Internal Peripheral Register Map
**Prompt**: "What are the base addresses for the NVU internal I2C, SPI, and UART peripherals?"
**Expected**: I2C0: `0xF000_0000`, I2C1: `0xF000_1000`, I2C2: `0xF000_2000`. SPI0: `0xF020_0000`, SPI1: `0xF020_1000`. UART0: `0xF030_0000`, UART1: `0xF030_1000`, UART2: `0xF030_2000`.
**Pass Criteria**: Must provide correct hex addresses for at least I2C0, SPI0, and UART0.

---

## Inference Sub-Skill

### NVU-INF-001: NNA Specification
**Prompt**: "What is the NVU neural network accelerator type and its peak throughput?"
**Expected**: NPX6-1K NNA (Synopsys Neural Processing Unit) with 1024 INT8 MACs/cycle. Supports CNN, RNN/LSTM, Transformers. Has convolution accelerator + tensor accelerator with HS3x-based L1 controller.
**Pass Criteria**: Must state NPX6-1K, 1024 INT8 MACs/cycle.

### NVU-INF-002: DSP Core Architecture
**Prompt**: "Describe the NVU DSP core — what is its architecture and cache configuration?"
**Expected**: ARC VPX2 DSP — Synopsys high-performance VLIW/SIMD DSP core with 32-bit scalar pipe + 128-bit vector processing unit with FPU. 32KB I-cache, 32KB D-cache, 128KB VCCM.
**Pass Criteria**: Must state VPX2, 32KB I$, 32KB D$, 128KB VCCM.

### NVU-INF-003: Dual-Engine Architecture
**Prompt**: "How do the VPX2 DSP and NPX6-1K NNA work together for inference?"
**Expected**: VPX2 handles scalar/vector pre/post-processing and control flow; NPX6-1K handles the heavy neural network compute (convolutions, tensor ops). VPX2 orchestrates model loading and NNA dispatch.
**Pass Criteria**: Must describe both engines and their complementary roles.

---

## DMA Sub-Skill

### NVU-DMA-001: DMA Controller Type
**Prompt**: "What DMA controller does NVU use and what are its key capabilities?"
**Expected**: DesignWare AXI DMA Controller (v2.00a) with 64-bit addressing. Used for both boot DMA (firmware loading) and runtime paging DMA (SRAM↔DRAM).
**Pass Criteria**: Must mention DesignWare AXI DMA, v2.00a, 64-bit addressing.

### NVU-DMA-002: SRAM Configuration
**Prompt**: "What is the NVU SRAM size, organization, and ECC capability?"
**Expected**: 3584 KB total (7 slices x 512 KB each). SECDED ECC protection. Connected via high-performance fabric with SMMU for FW-managed paging to DRAM (IMR).
**Pass Criteria**: Must state 3584 KB, 7 slices x 512 KB, SECDED ECC.

---

## Power Sub-Skill

### NVU-PWR-001: Power States
**Prompt**: "What power states does NVU support? Does it support D0i3 or RTD3?"
**Expected**: NVU supports D0i0, D0i1, D0i2, and Lid-Closed states. NVU does NOT support D0i3. NVU does NOT support RTD3. Maximum idle state is D0i2. Post FW load, SW function enters D3 (D3hot only, not D3cold).
**Pass Criteria**: Must explicitly state NO D0i3, NO RTD3, D0i2 is maximum idle. Must NOT claim NVU supports D0i3 or RTD3.

### NVU-PWR-002: Voltage Domain
**Prompt**: "What voltage domain does NVU operate on?"
**Expected**: VNN power domain at 0.75V nominal. NVU has both gated and ungated VNN regions. No DVFS — fixed voltage.
**Pass Criteria**: Must state VNN, 0.75V, no DVFS.

### NVU-PWR-003: Sx State Behavior
**Prompt**: "Does NVU function in platform Sx sleep states?"
**Expected**: NVU is non-functional in platform Sx states. It only operates in S0 with Chassis 2.2 sleep states.
**Pass Criteria**: Must state non-functional in Sx, operates only in S0.

### NVU-PWR-004: PME Wake Mechanism
**Prompt**: "When does NVU use PME to wake the host?"
**Expected**: FW wakes host via PME for two scenarios: (1) exception reset recovery, (2) Lid-Closed to Lid-Open FW reload transition.
**Pass Criteria**: Must mention both PME scenarios (exception reset and lid transition).

---

## Driver Sub-Skill

### NVU-DRV-001: Host IPC Interface
**Prompt**: "How does the host driver communicate with NVU firmware?"
**Expected**: Via BAR0 MMIO (64KB) mapped to Host IPC registers at internal address `0x8000_0000`. The Host IPC + RS0 path is disabled post-boot for security. IPC uses doorbell/mailbox mechanism.
**Pass Criteria**: Must mention BAR0, IPC, and post-boot lockdown.

### NVU-DRV-002: Driver Information Source
**Prompt**: "Where can I find NVU driver names and device node paths?"
**Expected**: HAS v1.0 does not document OS-specific driver details. Section 21 defers to external specs: NVU FAS, BIOS Programming Guide, and Software Architecture Specification (SwAS).
**Pass Criteria**: Must state the info is NOT in HAS v1.0 and reference external specs.

---

## Platform Sub-Skill

### NVU-PLT-001: First Platform Integration
**Prompt**: "Which Intel platform first integrates the NVU?"
**Expected**: TitanLake PCD-H is the first platform to integrate NVU (NVU1p0).
**Pass Criteria**: Must mention TitanLake PCD-H.

### NVU-PLT-002: BDF Assignment
**Prompt**: "How is the NVU BDF (Bus/Device/Function) assigned?"
**Expected**: BDF is strap-configured. Device/Function from `nvu_br_devfuncnum[7:0]` strap (Dev[7:3], Func[2:0]). Bus number assigned by PSF via `nvu_br_strap_busno_rs[23:0]` per root-space.
**Pass Criteria**: Must mention strap-configured, `nvu_br_devfuncnum`, and PSF bus assignment.

### NVU-PLT-003: Device ID Assignment
**Prompt**: "What is the NVU PCI Device ID?"
**Expected**: Device ID is strap-configured via `nvu_br_strap_deviceid[15:0]`. Not hardcoded in HAS v1.0 — exact per-platform DID depends on SoC integration. Vendor ID is `0x8086`.
**Pass Criteria**: Must state strap-configured, not hardcoded, and VID `0x8086`.

### NVU-PLT-004: MJPEG Decoder Fusing
**Prompt**: "Is the NVU MJPEG decoder enabled by default?"
**Expected**: No — the VC9000NanoD MJPEG decoder is fuse-gated via `NVU_VSI9000NanoD_enable` fuse, default disabled.
**Pass Criteria**: Must state fuse-gated and default disabled.

---

## Debug Sub-Skill

### NVU-DBG-001: Debug Interfaces
**Prompt**: "What debug interfaces does NVU provide for post-silicon validation?"
**Expected**: VISA2 (post-Si signal visibility), OCD via sTAP (VPX2 core debug), DTF trace to Intel Trace Hub/NorthPeak (MIPI-SysT format), IMR model dump in debug mode.
**Pass Criteria**: Must mention at least VISA2, OCD/sTAP, and DTF trace.

### NVU-DBG-002: Telemetry Categories
**Prompt**: "What categories of telemetry counters does NVU provide?"
**Expected**: 3 categories: (1) Debug/Profiling counters, (2) Data Leaking Threat counters, (3) UX Study counters. 53 total counter definitions.
**Pass Criteria**: Must mention all 3 categories.

### NVU-DBG-003: ECC Protection
**Prompt**: "What ECC protection does NVU SRAM provide?"
**Expected**: SECDED (Single Error Correct, Double Error Detect) ECC on all 7 SRAM slices. Watchdog timer also provides RAS coverage.
**Pass Criteria**: Must state SECDED and mention watchdog.

---

## Camera Sub-Skill

### NVU-CAM-001: Camera Interface Types
**Prompt**: "What camera interfaces does NVU support?"
**Expected**: Two types: (1) MIPI cameras via C/D-PHY sharing with IPU (using Synopsys CSI2 Host Controller and Altek CV-ISP), (2) USB cameras via XHCI camera offload (using SIO Component for streaming).
**Pass Criteria**: Must mention both MIPI (with PHY sharing) and USB camera paths.

### NVU-CAM-002: ISP Capabilities
**Prompt**: "What does the Altek CV-ISP inside NVU do?"
**Expected**: Altek CV-ISP is optimized for computer vision (not photography). Provides: motion detection, frame rate conversion, BLC (black level correction), lens shading correction, de-mosaicing, AE/AWB statistics.
**Pass Criteria**: Must state computer-vision optimized and list at least 3 ISP functions.

### NVU-CAM-003: Legacy USB Camera Support
**Prompt**: "Does NVU support legacy USB cameras?"
**Expected**: Legacy USB camera offload is marked as a "future" requirement — it is NOT POR (Plan of Record) for NVU1p0.
**Pass Criteria**: Must state not POR for NVU1p0.

---

## Firmware Sub-Skill

### NVU-FW-001: Firmware Loading Flow
**Prompt**: "How is NVU firmware loaded and authenticated?"
**Expected**: FW is downloaded to IMR via Host IPC (DMA MRd from RS0/RS3 DRAM). ESE authenticates the FW (SVN check + signature verification) before VPX2 begins execution. Host IPC + RS0 path is disabled post-boot for security.
**Pass Criteria**: Must mention IMR, ESE authentication, SVN check, and post-boot lockdown.

### NVU-FW-002: Secure Boot
**Prompt**: "Does NVU have secure boot? What security mechanisms protect the boot process?"
**Expected**: Yes — NVU has ROM-based secure boot with SHA hash engine. SAI-based access control and ATT (Address Translation Table) provide additional security. ROM bypass supported as survivability feature (HSD 15018614010).
**Pass Criteria**: Must mention ROM secure boot, SHA, SAI, and ATT.

### NVU-FW-003: IPC Channels
**Prompt**: "What other IPs can NVU communicate with via IPC?"
**Expected**: NVU has IPC channels to: Host, CSE/CSME, PMC, ESE, ISH, ACE, CNVI, BT.
**Pass Criteria**: Must list at least Host, CSE, PMC, ESE, ISH.

### NVU-FW-004: ROM Bypass
**Prompt**: "What is the NVU ROM bypass feature?"
**Expected**: HSD 15018614010 — NVU ROM code bypass as survivability feature (POR). Allows bypassing ROM secure boot in case of ROM bugs, using soft-strap `NVU_ROM_WAIT_D3`.
**Pass Criteria**: Must reference HSD 15018614010 and mention survivability.

---

## Cross-Domain Tests

### NVU-CROSS-001: NVU vs AVB Predecessor
**Prompt**: "What is the relationship between NVU and AVB?"
**Expected**: NVU replaces the Always-on Vision Block (AVB) from LNL. NVU upgrades include: VPX2 DSP (replacing AVB's DSP), NPX6-1K NNA, USB camera support, and FW-based DRAM paging.
**Pass Criteria**: Must state NVU replaces AVB from LNL and list at least 2 upgrades.

### NVU-CROSS-002: NOC Fabric
**Prompt**: "What interconnect fabric does NVU use internally?"
**Expected**: Arteris FlexNoC (v5.4) interconnect fabric routes all initiator/target traffic within NVU.
**Pass Criteria**: Must mention Arteris FlexNoC v5.4.

### NVU-CROSS-003: Always-ON Use Cases
**Prompt**: "What always-on visual sensing use cases does NVU enable?"
**Expected**: Low-power: Wake-on-Face (WoF), FaceID, static hand gestures. S0 usages: Head-Orientation, Onlooker detection, 3D gestures.
**Pass Criteria**: Must mention Wake-on-Face and at least 2 other use cases.

### NVU-CROSS-004: Known RTL Opens
**Prompt**: "Are there any known open RTL issues documented in the NVU HAS?"
**Expected**: Yes — VPX2 signal opens: `v0c0clk_en`, `v0c0arc_event0_a`, `v0c0arc_event1_a`, `vpx_v0_vm_irq_a`. Also `v1c0*` unused signals (tie-off/open) and `h0host*` open. HSD 15016929800 (TCG FSM corner case, rejected) and HSD 15018335923 (reset values update, POR).
**Pass Criteria**: Must mention at least 2 VPX2 signal opens and 1 HSD reference.

---

## BIOS Sub-Skill

### NVU-BIOS-001: BIOS Init Sequence
**Prompt**: "What are the key BIOS initialization steps for NVU?"
**Expected**: BIOS must configure NVU straps (device ID, BDF), allocate BAR0 (64KB) and BAR1 (if enabled), program PCI config space (VID/DID, class code), and enable MSI. BIOS Programming Guide (BWG) is the authoritative reference.
**Pass Criteria**: Must mention strap configuration, BAR allocation, and reference BWG.

### NVU-BIOS-002: NVU BIOS Knobs
**Prompt**: "What BIOS knobs control NVU behavior?"
**Expected**: Key knobs include NVU enable/disable, MJPEG decoder enable (fuse-gated via `NVU_VSI9000NanoD_enable`), ROM bypass (`NVU_ROM_WAIT_D3`), and BAR1 disable (HSD 15018335923). Exact knob names are platform-specific.
**Pass Criteria**: Must mention at least NVU enable and MJPEG fuse-gate knobs.

### NVU-BIOS-003: Power-On Reset Sequence
**Prompt**: "What happens to NVU during platform power-on reset?"
**Expected**: NVU is held in reset until BIOS releases it. After reset release, ROM secure boot executes (unless bypassed). BIOS configures PCI space, then host driver takes over for FW loading via IPC.
**Pass Criteria**: Must describe reset hold, ROM boot, and BIOS→driver handoff sequence.

### NVU-BIOS-004: BAR1 Disable Feature
**Prompt**: "Can NVU BAR1 be disabled and why would you?"
**Expected**: Yes — BAR1 disable is supported per HSD 15018335923. BAR1 exists because `NUM_BARS=2` in the IOSF2AXI bridge config. Disabling BAR1 saves MMIO address space when the second BAR is not needed.
**Pass Criteria**: Must reference HSD 15018335923 and explain BAR1 disable purpose.

---

## Simics Sub-Skill

### NVU-SIM-001: Simics Model Status
**Prompt**: "Is there a Simics virtual platform model for NVU?"
**Expected**: The Simics sub-skill is currently a PLACEHOLDER — no NVU Simics model is publicly available yet. When available, it would enable pre-silicon validation of NVU register access, DMA flows, power state transitions, and firmware loading without physical hardware.
**Pass Criteria**: Must clearly state this is a placeholder/future capability and describe what a Simics model would enable.

### NVU-SIM-002: Simics Validation Scope
**Prompt**: "What NVU features could be validated in Simics?"
**Expected**: Key validation areas would include: PCI config space enumeration (VID/DID, BARs, capabilities), MMIO register access (BAR0 64KB host IPC space), DMA descriptor setup and data transfers, power state transitions (D0i0→D0i2, Lid-Closed), IPC messaging between host and VPX2 firmware, and basic inference pipeline (model load → execute → result).
**Pass Criteria**: Must mention at least 3 distinct validation areas (registers, DMA, power, IPC, or inference).

---

## Self-Improvement Toolchain Tests

### NVU-TOOL-001: Self-Check Structural Validation
**Prompt**: "Run `python nvu_self_check.py` and explain what it validates."
**Expected**: `nvu_self_check.py` runs 10 structural checks: (1) file existence for all sub-skills, (2) owner/maintainer headers, (3) sub-skill count matches config, (4) cross-references between skill files, (5) docs directory, (6) eval directory, (7) stale references, (8) frontmatter consistency, (9) delegation table, (10) version strings. Outputs JSON with PASS/FAIL/WARN per check.
**Pass Criteria**: Tool must execute without errors. Must report ≥60 PASS findings and 0 FAIL.

### NVU-TOOL-002: Self-Verify Content Assertions
**Prompt**: "Run `python nvu_self_verify.py` and explain what it validates."
**Expected**: `nvu_self_verify.py` runs 81 content assertions across 10 categories (REG/INF/DMA/PWR/DRV/PLAT/DBG/CAM/FW/BIOS). Each assertion checks that specific HAS-sourced facts appear in the correct skill file (e.g., "3584 KB" in DMA, "NPX6-1K" in inference, "D0i2" in power). Outputs JSON with PASS/FAIL per assertion.
**Pass Criteria**: Tool must execute without errors. Must report 81/81 PASS.

### NVU-TOOL-003: BIOS Validator
**Prompt**: "Run `python validate_bios.py` and explain what it validates."
**Expected**: `validate_bios.py` runs 423 checks against `bios/SKILL.md` covering: section structure, BIOS knob tables, cross-references to peer sub-skills, HAS citations, register offset formats, power management content, and security controls. Uses pattern matching and section parsing.
**Pass Criteria**: Tool must execute without errors. Must report 423/423 PASS (100% pass rate).

### NVU-TOOL-004: E2E Validator
**Prompt**: "Run `python validate_e2e.py` and explain what it validates."
**Expected**: `validate_e2e.py` runs 50 end-to-end cross-checks between NVU skill files and the authoritative HAS extraction. Validates key facts like SRAM size (3584 KB), DSP cache sizes (32KB I$, 32KB D$), NNA type (NPX6-1K), power states (D0i2 max, no RTD3), clock domains (10), and IOSF bridge parameters. Reports CONFIRMED/MISMATCH per check.
**Pass Criteria**: Tool must execute without errors. Must report 50/50 CONFIRMED, 0 MISMATCH.

### NVU-TOOL-005: Quality Gate
**Prompt**: "Run `python nvu_quality_gate.py` and explain what it does."
**Expected**: `nvu_quality_gate.py` is the CI/CD quality gate that orchestrates all 5 core validators: self-check, self-verify, validate_bios, validate_e2e, source-crosscheck. The source-crosscheck stage validates 76 facts (including 34 SVG-sourced facts) from 5 source documents against 12 skill files. Core stages are blocking (any failure fails the gate). Supports `--full` flag to also run 3 advisory (non-blocking) stages: self-learn, self-study, self-improve. CLI flags: `--quick`, `--check`, `--verify`, `--full`, `--json`.
**Pass Criteria**: Tool must execute without errors. Must report overall PASS with ≥700 total assertions.

### NVU-TOOL-006: Self-Learn Knowledge Gaps
**Prompt**: "Run `python nvu_self_learn.py` and explain what it detects."
**Expected**: `nvu_self_learn.py` detects knowledge gaps via 4 sources: (1) NGA API for test failure patterns, (2) HSDES for NVU sightings, (3) manual feedback file analysis, (4) coverage gap detection across skill files. Generates proposals for skill file improvements. Runs in advisory mode — findings are informational, not blocking.
**Pass Criteria**: Tool must execute without errors. Must produce a valid JSON report with proposals array.

### NVU-TOOL-007: Self-Study External Sources
**Prompt**: "Run `python nvu_self_study.py` and explain what it monitors."
**Expected**: `nvu_self_study.py` monitors external sources for updates: (1) HAS document changes via `has_manifest.json`, (2) driver repository modifications, (3) skill file edit timestamps for staleness detection. Compares current state against known baselines to detect drift. Runs in advisory mode.
**Pass Criteria**: Tool must execute without errors. Must produce a valid JSON report.

### NVU-TOOL-008: Self-Improve Orchestrator
**Prompt**: "Run `python nvu_self_improve.py` and explain its 5-stage pipeline."
**Expected**: `nvu_self_improve.py` orchestrates 5 stages: (1) Check — structural validation via self-check, (2) Study — external source monitoring via self-study, (3) Learn — knowledge gap detection via self-learn, (4) Verify — content assertions via self-verify, (5) Coverage — cross-sub-skill coverage analysis. Generates prioritized proposals targeting specific skill files. Uses `_map_source_to_skill()` to route findings to correct files.
**Pass Criteria**: Tool must execute without errors. Must complete all 5 stages and produce proposals.

### NVU-TOOL-009: Common Library Foundation
**Prompt**: "What does `nvu_self_common.py` provide to the other tools?"
**Expected**: `nvu_self_common.py` is the foundation library providing: `Finding` dataclass (severity, category, source, message, suggestion), `Report` class (add findings, to_json, summary), config loading from `self_improvement_config.json`, git helpers (last modified date, file diff), and path resolution for the NVU skill tree. All other tools import from this module.
**Pass Criteria**: Must describe Finding/Report classes and config loading. Must NOT be a standalone CLI tool.

### NVU-TOOL-010: Source Crosscheck with SVG Facts
**Prompt**: "Run `python nvu_source_crosscheck.py` and explain what SVG-sourced facts it validates."
**Expected**: `nvu_source_crosscheck.py` validates 76 facts from 5 sources (main_has, bios_req, integration_has, bios_html, svg_extraction) against 12 skill files. The 34 SVG-sourced facts verify content extracted from 183 SVG block diagrams in the HAS/FAS/BIOS `_files/` directories. SVG facts cover all 10 sub-skills: DMA address routing, power clock partitions, camera CSI2/PHY/CVISP pipelines, firmware exception flows, inference NPX6/VPX2 architecture, platform NOC fabric, debug DTF pipeline, registers SRAM map, driver IPC/UVOL/SIO, and BIOS RTD3/VGPIO.
**Pass Criteria**: Must report 112 PASS / 0 FAIL. Must mention SVG extraction as a source.

---

## SVG-Sourced Content Validation

> These tests validate the agent can answer questions using knowledge extracted from SVG block diagrams in the HAS/FAS/BIOS source documents.

### NVU-SVG-001: DMA Address Routing Formula
**Prompt**: "How does the NVU DMA controller construct the full 64-bit AXI address, and what is the RS0DisableLogic routing rule?"
**Expected**: Full address is constructed as `AxADDR[63:0] = {AxUSER[1:0], AxADDR[61:0]}` where AxUSER[1:0] provides the upper 2 bits. RS0DisableLogic routes based on AxADDR[62]: if AxADDR[62]==1, route to IOSF2AXI (host memory); if AxADDR[62]==0, route to LLIM (local NVU memory). AXI ID encoding: ARID[3]=LLI flag, ARID[2:0]=channel number.
**Pass Criteria**: Must state the AxUSER address construction formula and the AxADDR[62] routing rule.

### NVU-SVG-002: Power Clock Partitions
**Prompt**: "What are the NVU clock partitions and how does clock switching work?"
**Expected**: 10 clock partitions: PAR_MAIN (NoC/APB/peripherals), PAR_VPX (DSP core), PAR_NPX (NNA), PAR_SRAM (memory subsystem), PAR_MIPI (camera interface), PAR_USB (USB-IF). Clock switching follows an 8-step procedure involving clock request, PLL lock wait, glitch-free MUX switch, and distribution enable.
**Pass Criteria**: Must name at least 4 clock partitions and describe the switching procedure.

### NVU-SVG-003: Camera CSI2 HC Internal Pipeline
**Prompt**: "What are the sub-blocks inside the NVU CSI2 Host Controller pipeline?"
**Expected**: 7 sub-blocks: PPI (Physical Protocol Interface adaptation), PatternGen (test pattern generator), De-Skew (lane alignment), PHYAdapt (PHY interface adaptation), Descrambler (CSI-2 data descrambling), PacketAnalyzer (header/payload parsing), and IDI→IPI (internal data interface to internal pixel interface conversion).
**Pass Criteria**: Must name at least 5 of the 7 sub-blocks.

### NVU-SVG-004: PHY Sharing State Machine
**Prompt**: "How does NVU share the MIPI C/D-PHY with the IPU? What are the CDPHY_owner values?"
**Expected**: PHY sharing uses CDPHY_owner register: 0x0=Unclaimed, 0x1=IPU owns, 0x2=NVU owns, 0x3=Reserved. Claim/release uses handshake signals (claim_req/claim_ack/release_req/release_ack). PHY ownership transition adds ~1ms D0ix latency overhead.
**Pass Criteria**: Must state the 4 CDPHY_owner values and the handshake mechanism.

### NVU-SVG-005: Firmware Exception Recovery Flow
**Prompt**: "What happens during an NVU VPX firmware exception? Describe the full recovery sequence."
**Expected**: 35-step flow in 4 phases: (1) Camera Shutdown — stop sensor, PHY shutdown (MIPI) or L2 suspend (USB), release shared IO, de-assert release_ack VGPIOs, NVU_claim=0. (2) Exception Dump — collect exception dump (address, reason, call stack; include NPX dump if NPX caused it), print and save to AONRF. (3) HW Reset + BUP Reload — trigger VPX reset, halt NPX if not halted, gate NPX CLK, assert NPX reset, load and jump to BUP, check/restore I2C/I3C PMode and VGPIO PMode, clear reset reason. (4) FW Recovery — RTD3 exit, download Base+App FW, read exception dump from AONRF, upload to host, RTD3 enter, jump to Main FW.
**Pass Criteria**: Must describe all 4 phases and mention AONRF exception dump save/restore.

### NVU-SVG-006: NVU CORE Reset HW Sequence
**Prompt**: "What is the NVU CORE Reset hardware sequence and what triggers it?"
**Expected**: Triggered by WD_RST, ECC_RST, SYSTF_HALT_R, or V0C0_RST_A. 11-step sequence: (1) Assert v0c0_ext_halt_req_a, (2-3) Core pipeline flush to IDLE, (4) Assert v0c0_ext_halt_ack, (5) Assert sys_halt_r (CRPM timeout: CRPM_VPX_HALT_TIMEOUT_CNT), (6) Deassert halt_req, (7) Assert rst_a for 64 clocks, (8) De-assert rst_a, (9) Assert v0c0_ext_run_req_a, (10) Assert v0c0_ext_run_ack, (11) De-assert run_req. ROM must check CRPM_RST_HIS register for reset reason.
**Pass Criteria**: Must mention the 4 trigger sources, 64-clock reset pulse, and CRPM_RST_HIS check.

### NVU-SVG-007: Driver IPC Register Architecture
**Prompt**: "What are the NVU IPC doorbell registers for ESE and Host communication?"
**Expected**: ESE IPC: NVU2ESE_DOORBELL_ESE, ESE2NVU_DOORBELL_ESE, ESE2NVU_CSR_ESE, ESE2NVU_CSR_CLR_ESE, NVU2ESE_DB, ESE2NVU_DB_MIRROR, NVU2ESE_CSR. NVU→ESE uses IOSF SB RS=2 MMIO WR with ROWN_REQ[SBR] handshake. Host IPC: NVU2HOST_DOORBELL_HOST, HOST2NVU_DOORBELL_HOST, NVU_HOST_FWSTS_HOST, NVU_HOST_COMM_HOST. Host IPC uses either legacy IRQ (Assert_IRQx# via IOSF SB msg) or MSI (MSI_GEN block with ROWN_REQ[PSF]).
**Pass Criteria**: Must name at least 4 doorbell/CSR registers and distinguish legacy IRQ vs MSI paths.

### NVU-SVG-008: UVOL Driver and SIO Architecture
**Prompt**: "Describe the NVU UVOL driver software architecture and the SIO interface."
**Expected**: UVOL driver layers: CameraApp→ConfigService+USBSharing→DeviceEnum (6 xHCI commands: Enable Slot, Address Device, Configure Endpoint, Disable Slot, Reset EndPoint, Stop EndPoint)→HostReset/ErrorRecovery→HC/HAR/HAT+ISOCH→UAL/UDF→LinkLogic+MSI2IPI+MISC→SIO_DMA→SIO_HW. SIO sits on NoC Crux Fabric (200MHz, 16B data, max 3.2GB/s BW). IOSF Primary CH0: VC0d(RS0,p2p), VCm(RS3), VCp(receive only). 3 camera sharing modes: IPU Exclusive, NVU Exclusive, Concurrent.
**Pass Criteria**: Must describe the UVOL layer stack and SIO fabric specs (200MHz, 3.2GB/s).

### NVU-SVG-009: SRAM/SMMU Memory Map
**Prompt**: "What is the NVU SRAM memory map with SMMU virtual addresses?"
**Expected**: VMEMP region at `0x6000_0000` (16MB), Pageable SRAM at `0x6800_0000` (3MB), PMEM (persistent memory) at `0x6808_0000` (512KB), EXTMEM/IMR at `0xA000_0000` (16MB). SRAM FW layout includes 12 regions with defined sizes. SMMU provides virtual-to-physical address translation for FW-managed paging between SRAM and DRAM (IMR).
**Pass Criteria**: Must provide at least 3 correct SMMU virtual addresses with sizes.

### NVU-SVG-010: Inference NPX6 Internal Bus Architecture
**Prompt**: "What are the internal buses and sub-blocks of the NPX6-1K NNA?"
**Expected**: NPX6 has 5 internal buses: VM (vector memory), AM (address memory), DM (data memory), CTRL (control), Data. 7 sub-blocks: oDMA (output DMA), iDMA (input DMA), GTOA (global tensor operation accelerator), Conv (convolution engine), L1 ARC controller with CBU (convolution buffer unit), LBU (local buffer unit), DMI (data memory interface).
**Pass Criteria**: Must name at least 3 buses and 4 sub-blocks.

### NVU-SVG-011: Platform NOC Fabric Topology
**Prompt**: "Describe the NVU NOC (Network-on-Chip) fabric topology — how many initiators and what are the key targets?"
**Expected**: Arteris FlexNoC (v5.4) with 7 initiators (all 128-bit): VPX2 DSP, NPX6 NNA, DMA Controller, MIPI-IF subsystem, USB-IF subsystem, IOSF2AXI bridge, and SIO. Key targets: SRAM_SS (SRAM subsystem), APB_PERIPHERALS, SIO_TARG128, UVOL_CFG32, DMI64. 3 bridges for bandwidth matching between different data widths.
**Pass Criteria**: Must state 7 initiators at 128-bit width and name at least 3 targets.

### NVU-SVG-012: Debug DTF Pipeline and Packet Format
**Prompt**: "How does NVU debug trace flow from firmware to the host trace aggregator?"
**Expected**: DTF pipeline: FW writes → Source Packetizer → Encoder → Arbiter → TraceAggregator → NorthPeak (Intel Trace Hub). Packet format: STP D64TS with Sys-T header containing Type, Severity, Unit, ModuleID, SubType fields. FW trace register write sequence: 7-step process to emit a single trace packet. Pre-EOM debug uses JTAG/OCD; Post-EOM debug uses DTF/NorthPeak trace.
**Pass Criteria**: Must describe the 5-stage DTF pipeline and mention STP D64TS Sys-T packet format.
