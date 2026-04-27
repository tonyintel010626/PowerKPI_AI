---
name: fv-nvu
description: >-
  Neural Vision Unit (NVU/NVU1p0) IP domain knowledge for post-silicon functional validation.
  Covers registers, inference engine, DMA architecture, power management, driver internals,
  platform data, debug/triage, camera interface, and firmware across Intel Client SoC platforms.
disable: false
license: MIT
---

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# FV-NVU Skill Tree

This is the **top-level skill router** for the NVU domain. It indexes all sub-skills and supporting resources.

## Sub-Skills

### Available Sub-Skills

| # | Sub-Skill | Load Command | Description | Lines | TBDs | Status |
|---|-----------|-------------|-------------|-------|------|--------|
| 1 | **registers** | `/skill fv-nvu/registers` | MMIO/PCI register map, bitfields, offsets | 1,941 | 16 | Enriched |
| 2 | **inference** | `/skill fv-nvu/inference` | Inference engine, NPX6+VPX2 dual-engine arch | 1,145 | 8 | Enriched |
| 3 | **dma** | `/skill fv-nvu/dma` | DMA architecture, DesignWare AXI, descriptors | 1,203 | 6 | Enriched |
| 4 | **power** | `/skill fv-nvu/power` | Power states, clock/power gating, PMC, LTR | 2,333 | 9 | Enriched |
| 5 | **driver** | `/skill fv-nvu/driver` | Host driver, PCI enum, IPC, FW loading | 2,778 | 6 | Enriched |
| 6 | **platform** | `/skill fv-nvu/platform` | Reset, straps, fuses, BDF, electricals | 2,749 | 1 | Enriched |
| 7 | **debug** | `/skill fv-nvu/debug` | Debug/triage, RAS, ECC, WDT, telemetry | 2,281 | 6 | Enriched |
| 8 | **camera** | `/skill fv-nvu/camera` | MIPI CSI-2, Altek ISP, USB/MJPEG interface | 2,027 | 7 | Enriched |
| 9 | **firmware** | `/skill fv-nvu/firmware` | Boot ROM, IPC protocol, security, SHA-384 | 4,080 | 3 | Enriched |
| 10 | **bios** | `/skill fv-nvu/bios` | BIOS requirements, IMR, enable/disable, PCI, PM, IRQ, GPIO/VGPIO, RTD3, camera config, ACPI | 1,636 | 0 | Enriched |
| 11 | **simics** | `/skill fv-nvu/simics` | Simics model placeholder — awaiting NVU Simics model availability | 193 | 0 | Enriched |

> **11 sub-skills total — 22,366 lines (1.1 MB) of structured NVU knowledge.** Total TBDs across all SKILL.md files: 62 (down from ~189 after HAS backfill).
> All 11 sub-skills enriched via LLM pipeline (Claude Sonnet 4.6 via GitHub Copilot Premium) from 9,768 HAS facts across 179 sections.
> NVU HAS v1.0 defers OS-specific driver details to the NVU FAS and SwAS, which are not yet available.

## Agent Reference

The full NVU orchestrator agent is defined at:
- **Agent**: `.opencode/agent/FV/FV-NVU.md`

## Reference Documents

> **FRESHNESS WARNING**: NVU is a new IP under active development. Documents change **weekly to bi-weekly**.

### Studied Documents (Extracted into Skill Tree)

| # | Document | Status | Notes |
|---|----------|--------|-------|
| 1 | SIP-NVU1.0-HAS (293 pages) | **Current** | Main SIP HAS, extracted 2026-03-17 |
| 2 | SIP-NVU1.0-Integration-HAS (124 pages) | **Current** | SoC integration, extracted 2026-03-17 |
| 3 | VISION_SS_End-To-End_HAS (13 pages) | **Current** | Vision pipeline, extracted 2026-03-17 |
| 4 | NVU BIOS Requirements (Rev 0.8RC, 16 pages) | **Current** | BIOS programming, extracted 2026-03-26 |
| 5 | NVU BWG | Planned | — |
| 6 | NVU SwAS | Planned | — |

> Extraction artifacts (HAS text, figures, scripts, reports) are maintained locally and excluded from the repository.

### NVU IP HAS — Full Reference Document List

> Source: `NVU_IP_HAS_excel.xlsx` → References sheet (38 entries). Extracted 2026-03-24.
> These are the authoritative reference documents cited by the NVU IP HAS.

#### Platform & Requirements

| # | Reference Document | Version | Link |
|---|---|---|---|
| 1 | TitanLake AON DRD | 0.2 | [TTL AON DRD](https://docs.intel.com/documents/clientplatform/Domains/sensing/ttl/ttl_aon_drd.html) |
| 2 | Novalake Imaging Requirements | 1.0 | [NVL Imaging PAS](https://docs.intel.com/documents/ClientPlatform/Domains/imaging/nvl/nvl_imaging_pas.html) |

#### Synopsys Sub-IP Databooks

| # | Reference Document | Version | Link |
|---|---|---|---|
| 3 | Synopsys ARC VPX2 DSP | 6370-014 | [VPX2 Databook](https://intel.sharepoint.com/:b:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/VPX/ARC_VPXx_Databook.pdf) |
| 4 | Synopsys ARC NPX6-1K NNA | 6442-016 | [NPX6-1K Databook](https://intel.sharepoint.com/:b:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/NPX/ARC_NPX_Databook.pdf) |
| 5 | Altek CVISP | v0.2 | [CVISP Datasheet](https://intel.sharepoint.com/:b:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/Altek%20ISP/CVISP_ISP_IP_Product_Datasheet_0.2.pdf) |
| 6 | Verisilicon VC9000NanoD MJPEG Decoder | 1.05 | [MJPEG Decoder](https://intel.sharepoint.com/:b:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/VSI%20Decoder/Hantro.VC9000NanoD.V1x.HW.Integration.HW.Features-v1.05-D-20230221.pdf) |
| 7 | Arteris FlexNoC Fabric | v5.4 | [Arteris FlexNoC](https://intel.sharepoint.com/:f:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/Arteris%20FlexNoC/FlexNoC%205.4.0%20docs) |
| 8 | DesignWare I2C | 2.02a | [I2C Databook](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/MTL/Docs/Specs/SNPS_IP/DW_apb_i2c_databook.pdf) |
| 9 | DesignWare SSI (SPI) | 4.02a-lp00 | [SPI Databook](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/MTL/Docs/Specs/SNPS_IP/DW_apb_ssi_databook.pdf) |
| 10 | DesignWare UART | 4.02a | [UART Databook](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/MTL/Docs/Specs/SNPS_IP/DW_apb_uart_databook.pdf) |
| 11 | DesignWare MIPI I3C | 1.00-lca03 | [I3C Databook](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/MTL/Docs/Specs/SNPS_IP/DWC_mipi_i3c_databook.pdf) |
| 12 | DesignWare MIPI I3C User Guide | 1.00a-lca03 | [I3C User Guide](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/MTL/Docs/Specs/SNPS_IP/DWC_mipi_i3c_user.pdf) |
| 13 | DesignWare AXI DMA Controller | 2.00a | [DMA Databook](https://intel.sharepoint.com/:b:/r/sites/IPDevNVU/Shared%20Documents/General/NVU%20COE/LNL/Specs/DW_axi_dmac_databook.pdf) |
| 14 | DesignWare MIPI CSI2 Host Controller | 1.55a | [MIPI CSI2 Host](https://intel.sharepoint.com/sites/IPDevAVB/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2Fipdevavb%2FShared%20Documents%2FGeneral%2FHW%2FDocuments%2FCSI2%2DH) |
| 15 | Synopsys MIPI C/D PHY | 8.00a_pre3 | [MIPI PHY Databook](https://intel.sharepoint.com/:b:/r/sites/ipdevavb/Shared%20Documents/General/HW/Arch/SubIP%20Docs/MIPI%20PHY/dwc_mipi_cd_rx_2t2l_int3_reference.pdf) |

#### Intel IP Components & Bridges

| # | Reference Document | Version | Link |
|---|---|---|---|
| 16 | IOSF2AXI Bridge | PIC19 | [IOSF2AXI Bridge HAS](https://docs.intel.com/documents/cfg_customer/Bridges/iosf2axi/HAS/IOSF2AXI_HAS_PIC19.html) |
| 17 | SMMU Component | 0.5 | [SMMU Component HAS](https://docs.intel.com/documents/iparch/avb/has/SMMU/HAS/SMMU_Component_HAS.html) |
| 18 | SIO Component | 0.5 | [SIO Component HAS](https://docs.intel.com/documents/ClientSilicon/IP_Components/SIO_Comp/SIO_Comp.html) |
| 19 | SIO Protocol Spec | 2.0 | [SIO Protocol Spec 2.0](https://docs.intel.com/documents/iparch/avb/has/SIO/Scalable%20IO%20r2p0.html) |
| 20 | AXIBIU Component | — | [AXIBIU HAS](https://docs.intel.com/documents/ClientSilicon/IP_Components/AXIBIU_Comp/AXIBIU_Comp.html) |

#### USB / Camera Offload

| # | Reference Document | Version | Link |
|---|---|---|---|
| 21 | XHCI Camera | — | [SIP USB xHCI Camera](https://docs.intel.com/documents/iparch/usb/has/USB3_GenX_v20.1_xHCI_Cam/SIP_USB_GenX_xHCI_Camera.html) |
| 22 | Camera Offload E2E HAS | — | [Camera Offload E2E HAS](https://docs.intel.com/documents/iparch/usb/has/IP%20Specifications/Camera%20Offload%20End%20to%20End%20HAS/Camera_Offload_EndtoEnd_HAS.html) |
| 23 | IPU9 Input System | — | [IPU9 Input System](https://intel.sharepoint.com/:w:/r/sites/ICGArchsite/Shared%20Documents/IPU%20Specs/IPU9/HAS/IPU9_HAS_Input_System.docx) |
| 24 | IPU9 eUSB2V2 and CCPAL/U | — | [IPU9 CCPALU and SIO](https://intel.sharepoint.com/:w:/r/sites/ICGArchsite/Shared%20Documents/IPU%20Specs/IPU9/HAS/InSys%20files/ISYS%20eUSB2v2%20path%20and%20CCPALU%20support.docx) |
| 25 | IPU9 MIPI PHY Sharing with NVU | — | [IPU9 CDPHY Sharing](https://intel.sharepoint.com/:w:/r/sites/ICGArchsite/Shared%20Documents/IPU%20Specs/IPU9/HAS/InSys%20files/InSys%20sharing%20CDPHY%20with%20NVU%20HAS.docx) |

#### IOSF & Chassis Architecture

| # | Reference Document | Version | Link |
|---|---|---|---|
| 26 | IOSF Spec | 1.5 | [IOSF Spec](https://intel.sharepoint.com/:b:/r/sites/IOSFArchWorkgroup/Shared%20Documents/IOSF_Spec/Spec%20Release/1.5%20Spec%20Release/IOSF%20spec%201.5.pdf) |
| 27 | Chassis 2.0 Clocking Architecture | 2.0 | [Clocking ARCH](https://intel.sharepoint.com/:b:/r/sites/MDGArchMain/converged/chassiswg/HAS%20Releases/Chassis%20Clocking%20Architecture%20HAS%20v1%200RC1_review.pdf) |
| 28 | Chassis 2.0 Reset Architecture | 2.0 | [Reset ARCH](https://intel.sharepoint.com/sites/MDGArchMain/converged/chassiswg/HAS%2010%20RC%20%20Q4%202013/) |
| 29 | Chassis 2.0 Power Management Architecture | 2.0 | [Power Management ARCH](https://intel.sharepoint.com/:b:/r/sites/MDGArchMain/converged/chassiswg/HAS%20Releases/Chassis%20Power%20Management%20HAS%20Rev1%200RC1_review.pdf) |
| 30 | Chassis 2.0 Fuse Controller | 2.0 | [Fuse Controller](https://intel.sharepoint.com/:b:/r/sites/MDGArchMain/converged/chassiswg/HAS%20Releases/SIP_Chassis_Fuse_Controller_Gen2_HAS%20(v%201.18).pdf) |
| 31 | Chassis 2.0 Fuse Puller | 2.0 | [Fuse Puller](https://intel.sharepoint.com/:b:/r/sites/MDGArchMain/converged/chassiswg/HAS%20Releases/SIP_Chassis_Fuse_Puller_Gen2.0_HAS%20(v%200.80).pdf) |
| 32 | Chassis 2.0 Security | 2.0 | [Security HAS](https://intel.sharepoint.com/:b:/r/sites/MDGArchMain/converged/chassiswg/HAS%20Releases/Chassis%20Security%202015%20HAS%200%207.pdf) |
| 33 | Chassis 2.2 Sleep State HAS | 2.2 | [Sleep States HAS](https://docs.intel.com/documents/pm_chassis/Idle%20Power%20Management/Chassis%20Sleep%20States/Chassis%20Sleep%20States.html) |

#### NVU Companion Specifications

| # | Reference Document | Version | Link |
|---|---|---|---|
| 34 | NVU Firmware Architecture Spec (FAS) | — | [NVU FAS](https://docs.intel.com/documents/iparch/avb/fwarch/NVU/NVU%20Firmware%20Architecture%20Spec.html) |
| 35 | NVU Security Requirements Spec | — | [NVU Security Requirements](https://docs.intel.com/documents/iparch/avb/fwarch/NVU/NVU%20Security%20Requirements%20on%20IP%20HW%20and%20Platform.html) |
| 36 | NVU Security Architecture Spec (SeAS) | — | [NVU Security Architecture](https://docs.intel.com/documents/iparch/avb/fwarch/NVU/NVU%20Security%20Architecture%20Spec.html) |
| 37 | NVU BIOS Requirements Spec | — | [NVU BIOS Requirements](https://docs.intel.com/documents/iparch/avb/fwarch/NVU/NVU%20Requirements%20to%20BIOS.html) |
| 38 | NVU DFX HAS/MAS Spec | — | [NVU DFX MAS](https://docs.intel.com/documents/NVU_IP_Internal_Specs/TTL/Design/DFx/nvu_dfx_mas.html) |

#### Link Summary

| Host | Count | Refs |
|------|-------|------|
| **docs.intel.com** | 14 | #1, 2, 16–22, 33–38 |
| **intel.sharepoint.com** (IPDevAVB) | 8 | #3–7, 14, 15 |
| **intel.sharepoint.com** (IPDevNVU) | 6 | #8–13 |
| **intel.sharepoint.com** (ICGArchsite/IPU) | 3 | #23–25 |
| **intel.sharepoint.com** (Chassis WG) | 7 | #26–32 |

### HAS Section Map (HTML Line References)

Complete section-to-line mapping for `sip_nvu_has.html`. Use for traceability when cross-checking skill files against the HAS source.

| Section | Title | HTML Line |
|---------|-------|-----------|
| 1 | Introduction | ~1920 |
| 2 | NVU Architecture Overview | ~1940 |
| 2.2 | NVU Sub-IP Components | ~4200 |
| 2.5.1 | NVU IP Configuration Parameters | ~4500 |
| 3 | Theory of Operations | ~7900 |
| 4 | IP Configuration | ~9500 |
| 4.3 | NVU Bridge (IOSF2AXI) | ~9610 |
| 4.3.1 | Strap Configuration | ~9700 |
| 4.3.4.2.1 | NVU_MAIN_PGCB | ~12833 |
| 5 | Clock Domains | ~27000 |
| 6 | Reset | ~28500 |
| 7 | DMA | 29408 |
| 8 | Register Map | 29668 |
| 8.1 | IOSF2AXI Bridge Registers | 29668 |
| 8.2 | IOSF2AXI Bridge PVT CFG Extension | 30557 |
| 8.2.7.1 | ATT (Address Translation Table) | ~32400 |
| 8.3 | VPX2 DSP Registers | 32760 |
| 8.4 | NPX6 NNA Registers | 35208 |
| 8.5 | IPC Registers | 35524 |
| 8.6 | SRAM Subsystem Registers | 35927 |
| 8.7 | DMA Controller Registers | 38511 |
| 8.8 | I2C Registers | 41776 |
| 8.9 | I3C Registers | 50180 |
| 8.10 | SPI Registers | 50510 |
| 8.11 | UART Registers | 53572 |
| 8.12 | IOSF2AXI Misc Registers | 56402 |
| 8.13 | Timers (HPET / WDT) | 57739 |
| 8.14 | Security Registers (SEC_REG) | 60721 |
| 8.15 | ATT Registers | 61031 |
| 8.16 | CRPM Registers | 61035 |
| 8.17 | DMA MISC Registers | 61096 |
| 8.18 | SRAMSS Config Registers | 62262 |
| 8.19 | CSI2 Host Controller Registers | 62859 |
| 8.20 | Altek CV-ISP Registers | 63481 |
| 8.21 | GPIO Registers | 65098 |
| 8.22 | FlexNoC Fabric Registers | 65263 |
| 8.23 | DTF Trace Registers | 65287 |
| 9 | Interrupts | 66641 |
| 10 | Power Planes | 66777 |
| 11 | Performance Targets | 66970 |
| 12 | Firmware Loading | 67451 |
| 13 | Power Management | 67493 |
| 13.3 | D0i2 (IPAPG) | 68360 |
| 13.6 | Lid Transitions | 68635 |
| 13.7 | PGCB Power Gating | 68944 |
| 14 | Security | ~72300 |
| 14.9 | Security Locks | 72340 |
| 15 | Debug/DFx | ~72420 |
| 16 | Electrical Specifications | 72849 |
| 17 | Validation Strategy | ~72858 *(empty — "Not applicable")* |
| 18 | Test Requirements | ~72862 *(pointer to DFX HAS)* |
| 19 | Fuses | 72870 |
| 19.2 | Fuse Descriptions | 76873 |
| 20 | Revision History | 76928 |
| 21 | Software Driver | 76939 |
| 22 | Known RTL Opens | 76967 |

> **Usage**: When verifying a claim from the skill tree, find the section in this map, open the HAS HTML, and navigate to the approximate line number. Use browser Find (Ctrl+F) for exact text matching.

## Eval Tests

- **Location**: `eval/`
- **Status**: ✅ Active (58 eval tests + 423 BIOS checks + 50 E2E checks)

| Test Suite | File | Checks | Status |
|------------|------|--------|--------|
| Skill eval tests | `eval/nvu_skill_eval_tests.md` | 58 tests across 14 sections | ✅ Active |
| BIOS validator | `eval/validate_bios.py` | 423 requirement checks (939 lines) | ✅ 423P/0F |
| E2E validator | `docs/validate_e2e.py` | 50 cross-document checks (258 lines) | ✅ 50P/0F |

## Self-Improvement Toolchain

- **Location**: `tools/`
- **Status**: ✅ Active — **17 Python tools** (most instrumented skill tree in the repo)
- **Pipeline**: Ported from FV-THC, adapted for NVU-specific validation patterns
- **Config**: `tools/self_improvement_config.json` (11 skills, dual count keys)

### Tool Inventory

| # | Tool | Lines | Purpose | Status |
|---|------|-------|---------|--------|
| 1 | `nvu_self_common.py` | 491 | Foundation library (paths, config, logging) | ✅ |
| 2 | `nvu_self_check.py` | 775 | 10 structural checks (files, YAML, sections) | ✅ 70P/2W |
| 3 | `nvu_self_verify.py` | 1290 | 83 content assertions (HAS cross-refs) | ✅ 83P |
| 4 | `nvu_self_learn.py` | 692 | Knowledge gap detection | ✅ |
| 5 | `nvu_self_study.py` | 686 | External source monitoring | ✅ |
| 6 | `nvu_self_improve.py` | 775 | 5-stage orchestrator | ✅ |
| 7 | `nvu_quality_gate.py` | 392 | CI/CD pass/fail gate | ✅ |
| 8 | `nvu_run_all.py` | 340 | Unified runner (all stages) | ✅ |
| 9 | `nvu_delegation_check.py` | 590 | 8 agent↔skill consistency checks | ✅ 8P/0F |
| 10 | `nvu_pipeline_stress.py` | 440 | N-iteration stress runner | ✅ |
| 11 | `nvu_self_wiki.py` | 540 | Wiki cross-check scaffold | ✅ 30P |
| 12 | `nvu_codesign_test.py` | 543 | CoDeSign NVU HAS verification | ✅ 18P |
| 13 | `nvu_wiki_verify.py` | 625 | Deep wiki content verification | ✅ 50P |
| 14 | `nvu_simics_diff.py` | 483 | Simics model content diff | ✅ 23P |
| 15 | `nvu_changelog.py` | 405 | CHANGELOG auto-generation | ✅ |
| 16 | `nvu_regression_gate.py` | 447 | Pre-commit regression gate | ✅ |
| 17 | `nvu_coverage_report.py` | 651 | HAS section coverage tracker | ✅ 86.7% |

> **2 remaining WARNs** are legitimate: `registers/SKILL.md` HAS TBDs and `simics/SKILL.md` placeholder status — both expected until NVU HAS updates and Simics model availability.

### Validation Summary

| Validator | Result |
|-----------|--------|
| Full pipeline (7 stages) | 626P / 0F / 2W |
| Delegation check | 8P / 0F / 0W |
| CoDeSign test | 18P / 0F |
| Wiki verify | 50P / 0F |
| Simics diff | 23P / 0F |
| BIOS validator | 423 / 423 |
| E2E validator | 50 / 50 |
| HAS coverage | 86.7% avg (17/22 sections covered) |

## See Also

- [Agent Definition](../../agent/FV/FV-NVU.md) — FV-NVU agent configuration

---

## HAS-Extracted Knowledge (Auto-Generated)

> **Auto-generated** from NVU HAS extraction on 2026-04-05.
> 1500 facts from 270 HAS sections not previously covered.
> Cross-reference against HAS source for full context.

### §8.3.3

- **Table entry unknown: compile_translated_nsim_extensions (§8.3.3)**: `compile_translated_nsim_extensions` *(HAS §8.3.3)*
- **Table entry unknown: compile_translated_iss_extensions (§8.3.3)**: `compile_translated_iss_extensions` *(HAS §8.3.3)*
- **Table entry Interrupt Controller: number_of_interrupts (§8.3.3)**: `number_of_interrupts` *(HAS §8.3.3)*
- **Table entry Streaming transfer unit: stu_phy_chnl_num (§8.3.3)**: `stu_phy_chnl_num` *(HAS §8.3.3)*
- **Table entry Bus interface unit: biu_xnn_dmi_bus_num (§8.3.3)**: `biu_xnn_dmi_bus_num` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_dmi_bus_add_pipe_stage (§8.3.3)**: `biu_xnn_dmi_bus_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry Memory Protection Unit: mpu_num_regions (§8.3.3)**: `mpu_num_regions` *(HAS §8.3.3)*
- **Table entry Memory Management Unit: mmu_ecc_option (§8.3.3)**: `mmu_ecc_option` *(HAS §8.3.3)*
- **Table entry unknown: compile_nsim_user_extensions (§8.3.3)**: `compile_nsim_user_extensions` *(HAS §8.3.3)*
- **Table entry unknown: cc_allow_csm_l2_share_memory (§8.3.3)**: `cc_allow_csm_l2_share_memory` *(HAS §8.3.3)*
- **Table entry unknown: aux_volatile_strict_ordering (§8.3.3)**: `aux_volatile_strict_ordering` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem_is_default_slave (§8.3.3)**: `alb_mss_mem_is_default_slave` *(HAS §8.3.3)*
- **Table entry unknown: compile_iss_user_extensions (§8.3.3)**: `compile_iss_user_extensions` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_clkctrl_bypass_mode (§8.3.3)**: `alb_mss_clkctrl_bypass_mode` *(HAS §8.3.3)*
- **Table entry unknown: biu_per0_bus_add_pipe_stage (§8.3.3)**: `biu_per0_bus_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: biu_per1_bus_add_pipe_stage (§8.3.3)**: `biu_per1_bus_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: biu_mem_bus_add_pipe_stage (§8.3.3)**: `biu_mem_bus_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: biu_udmi_ioc_full_coherent (§8.3.3)**: `biu_udmi_ioc_full_coherent` *(HAS §8.3.3)*
- **Table entry unknown: vec_mem_scatter_stage_pipe (§8.3.3)**: `vec_mem_scatter_stage_pipe` *(HAS §8.3.3)*
- **Table entry unknown: ipxact_relative_path_names (§8.3.3)**: `ipxact_relative_path_names` *(HAS §8.3.3)*
- **Table entry ClkCtrl: alb_mss_clkctrl_base_addr (§8.3.3)**: `alb_mss_clkctrl_base_addr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_sim_timeout_limit (§8.3.3)**: `alb_mss_sim_timeout_limit` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_lqwq_per0 (§8.3.3)**: `cpu_top_add_ppb_lqwq_per0` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_dcache_rf (§8.3.3)**: `cpu_top_add_ppb_dcache_rf` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_dcache_cb (§8.3.3)**: `cpu_top_add_ppb_dcache_cb` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_iccm0_dmi (§8.3.3)**: `cpu_top_add_ppb_iccm0_dmi` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_icache_rf (§8.3.3)**: `cpu_top_add_ppb_icache_rf` *(HAS §8.3.3)*
- **Table entry Floating-point unit: fpu_dp_option (§8.3.3)**: `fpu_dp_option` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem_default_space (§8.3.3)**: `alb_mss_mem_default_space` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem_conflict_free (§8.3.3)**: `alb_mss_mem_conflict_free` *(HAS §8.3.3)*
- **Table entry unknown: cc_bus_ecc_parity_option (§8.3.3)**: `cc_bus_ecc_parity_option` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_dccm_dmi (§8.3.3)**: `cpu_top_add_ppb_dccm_dmi` *(HAS §8.3.3)*
- **Table entry unknown: cpu_top_add_ppb_lqwq_mem (§8.3.3)**: `cpu_top_add_ppb_lqwq_mem` *(HAS §8.3.3)*
- **Table entry unknown: ecc_export_error_per_ram (§8.3.3)**: `ecc_export_error_per_ram` *(HAS §8.3.3)*
- **Table entry unknown: ic_full_size_line_buffer (§8.3.3)**: `ic_full_size_line_buffer` *(HAS §8.3.3)*
- **Table entry Performance Monitor: pct_counters (§8.3.3)**: `pct_counters` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem_wr_rsp_ahead (§8.3.3)**: `alb_mss_mem_wr_rsp_ahead` *(HAS §8.3.3)*
- **Table entry unknown: always_instantiate_core (§8.3.3)**: `always_instantiate_core` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_def_div2ref (§8.3.3)**: `alb_mss_fab_def_div2ref` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_cdc_fifo_en (§8.3.3)**: `alb_mss_fab_cdc_fifo_en` *(HAS §8.3.3)*
- **Table entry unknown: cc_support_separate_clk (§8.3.3)**: `cc_support_separate_clk` *(HAS §8.3.3)*
- **Table entry unknown: export_cluster_srams_to (§8.3.3)**: `export_cluster_srams_to` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_dmi_bus0_client (§8.3.3)**: `biu_xnn_dmi_bus0_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_dmi_bus1_client (§8.3.3)**: `biu_xnn_dmi_bus1_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_dmi_bus2_client (§8.3.3)**: `biu_xnn_dmi_bus2_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_dmi_bus3_client (§8.3.3)**: `biu_xnn_dmi_bus3_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_udmi_add_pipe_stage (§8.3.3)**: `biu_udmi_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_ioc_bus0_client (§8.3.3)**: `biu_xnn_ioc_bus0_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_ioc_bus1_client (§8.3.3)**: `biu_xnn_ioc_bus1_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_ioc_bus2_client (§8.3.3)**: `biu_xnn_ioc_bus2_client` *(HAS §8.3.3)*
- **Table entry unknown: biu_xnn_ioc_bus3_client (§8.3.3)**: `biu_xnn_ioc_bus3_client` *(HAS §8.3.3)*
- **Table entry unknown: scantest_ram_bypass_mux (§8.3.3)**: `scantest_ram_bypass_mux` *(HAS §8.3.3)*
- **Table entry unknown: relaxed_ooo_rendez_vous (§8.3.3)**: `relaxed_ooo_rendez_vous` *(HAS §8.3.3)*
- **Table entry unknown: vec_mem_load_store_size (§8.3.3)**: `vec_mem_load_store_size` *(HAS §8.3.3)*
- **Table entry unknown: ipxact_include_aux_regs (§8.3.3)**: `ipxact_include_aux_regs` *(HAS §8.3.3)*
- **Table entry unknown: ipxact_dynamic_aux_regs (§8.3.3)**: `ipxact_dynamic_aux_regs` *(HAS §8.3.3)*
- **Table entry SRAMCtrl: alb_mss_mem_region_num (§8.3.3)**: `alb_mss_mem_region_num` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem0_def_lat_rd (§8.3.3)**: `alb_mss_mem0_def_lat_rd` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem0_def_lat_wr (§8.3.3)**: `alb_mss_mem0_def_lat_wr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem1_def_lat_rd (§8.3.3)**: `alb_mss_mem1_def_lat_rd` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem1_def_lat_wr (§8.3.3)**: `alb_mss_mem1_def_lat_wr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem2_def_lat_rd (§8.3.3)**: `alb_mss_mem2_def_lat_rd` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem2_def_lat_wr (§8.3.3)**: `alb_mss_mem2_def_lat_wr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem3_def_lat_rd (§8.3.3)**: `alb_mss_mem3_def_lat_rd` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem3_def_lat_wr (§8.3.3)**: `alb_mss_mem3_def_lat_wr` *(HAS §8.3.3)*
- **Table entry Tool Configuration: mwdt_version (§8.3.3)**: `mwdt_version` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_def_lat_rd (§8.3.3)**: `alb_mss_fab_def_lat_rd` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_def_lat_wr (§8.3.3)**: `alb_mss_fab_def_lat_wr` *(HAS §8.3.3)*
- **Table entry unknown: cc_bus_ecc_data_option (§8.3.3)**: `cc_bus_ecc_data_option` *(HAS §8.3.3)*
- **Table entry unknown: biu_per0_dedicated_bus (§8.3.3)**: `biu_per0_dedicated_bus` *(HAS §8.3.3)*
- **Table entry unknown: biu_per1_dedicated_bus (§8.3.3)**: `biu_per1_dedicated_bus` *(HAS §8.3.3)*
- **Table entry unknown: biu_dmi_add_pipe_stage (§8.3.3)**: `biu_dmi_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: biu_ioc_add_pipe_stage (§8.3.3)**: `biu_ioc_add_pipe_stage` *(HAS §8.3.3)*
- **Table entry unknown: instance_signal_prefix (§8.3.3)**: `instance_signal_prefix` *(HAS §8.3.3)*
- **Table entry unknown: ignore_encrypt_license (§8.3.3)**: `ignore_encrypt_license` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem0_base_addr (§8.3.3)**: `alb_mss_mem0_base_addr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem1_base_addr (§8.3.3)**: `alb_mss_mem1_base_addr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem2_base_addr (§8.3.3)**: `alb_mss_mem2_base_addr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem3_base_addr (§8.3.3)**: `alb_mss_mem3_base_addr` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_mem_data_width (§8.3.3)**: `alb_mss_mem_data_width` *(HAS §8.3.3)*
- **Table entry unknown: underscores_in_numbers (§8.3.3)**: `underscores_in_numbers` *(HAS §8.3.3)*
- **Table entry BusFabric: alb_mss_fab_ahb_b2b (§8.3.3)**: `alb_mss_fab_ahb_b2b` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_def_wr_bw (§8.3.3)**: `alb_mss_fab_def_wr_bw` *(HAS §8.3.3)*
- **Table entry unknown: alb_mss_fab_def_rd_bw (§8.3.3)**: `alb_mss_fab_def_rd_bw` *(HAS §8.3.3)*
- **Table entry unknown: biu_mem_dedicated_bus (§8.3.3)**: `biu_mem_dedicated_bus` *(HAS §8.3.3)*
- **Table entry unknown: biu_disable_unit_clkg (§8.3.3)**: `biu_disable_unit_clkg` *(HAS §8.3.3)*
- **Table entry unknown: ecc_export_db_sb_only (§8.3.3)**: `ecc_export_db_sb_only` *(HAS §8.3.3)*
- **Table entry Actionpoints: num_actionpoints (§8.3.3)**: `num_actionpoints` *(HAS §8.3.3)*
- **Table entry unknown: dc_io_coherency_ports (§8.3.3)**: `dc_io_coherency_ports` *(HAS §8.3.3)*
- **Table entry Debug Interface: dbg_en_option (§8.3.3)**: `dbg_en_option` *(HAS §8.3.3)*
- **Table entry unknown: apb_atb_clk_interface (§8.3.3)**: `apb_atb_clk_interface` *(HAS §8.3.3)*
- **Table entry unknown: vec_super_with_scalar (§8.3.3)**: `vec_super_with_scalar` *(HAS §8.3.3)*
- **Table entry unknown: execution_trace_level (§8.3.3)**: `execution_trace_level` *(HAS §8.3.3)*
- **Table entry unknown: export_core_srams_to (§8.3.3)**: `export_core_srams_to` *(HAS §8.3.3)*
- **Table entry unknown: biu_ibp2axi_zerodeep (§8.3.3)**: `biu_ibp2axi_zerodeep` *(HAS §8.3.3)*
- **Table entry unknown: biu_udmi_support_ioc (§8.3.3)**: `biu_udmi_support_ioc` *(HAS §8.3.3)*
- **Table entry unknown: biu_udmi_access_per1 (§8.3.3)**: `biu_udmi_access_per1` *(HAS §8.3.3)*
- **Table entry unknown: biu_udmi_bus_axi_idw (§8.3.3)**: `biu_udmi_bus_axi_idw` *(HAS §8.3.3)*
- **Table entry unknown: aux_volatile_disable (§8.3.3)**: `aux_volatile_disable` *(HAS §8.3.3)*
- **Table entry unknown: mmu_itlb_num_entries (§8.3.3)**: `mmu_itlb_num_entries` *(HAS §8.3.3)*

### §8.20.4

- **Table entry IC_HDRRXIF_2_HDRTXIF_SYNC_DEPTH: IC_HDRRXIF_2_HDRTXIF_SYNC_DEPTH (§8.20.4)**: `IC_HDRRXIF_2_HDRTXIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_SCLIF_2_HDRTXIF_SYNC_DEPTH: IC_SCLIF_2_HDRTXIF_SYNC_DEPTH (§8.20.4)**: `IC_SCLIF_2_HDRTXIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_SCLIF_2_HDRRXIF_SYNC_DEPTH: IC_SCLIF_2_HDRRXIF_SYNC_DEPTH (§8.20.4)**: `IC_SCLIF_2_HDRRXIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_SDAIF_2_HDRTXIF_SYNC_DEPTH: IC_SDAIF_2_HDRTXIF_SYNC_DEPTH (§8.20.4)**: `IC_SDAIF_2_HDRTXIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_SDAIF_2_HDRRXIF_SYNC_DEPTH: IC_SDAIF_2_HDRRXIF_SYNC_DEPTH (§8.20.4)**: `IC_SDAIF_2_HDRRXIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_HDRRXIF_2_SCLIF_SYNC_DEPTH: IC_HDRRXIF_2_SCLIF_SYNC_DEPTH (§8.20.4)**: `IC_HDRRXIF_2_SCLIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DFLT_SCL_LOW_TIMEOUT_COUNT: IC_DFLT_SCL_LOW_TIMEOUT_COUNT (§8.20.4)**: `IC_DFLT_SCL_LOW_TIMEOUT_COUNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_OPERATION_REG_OFFSET: IC_DFLT_OPERATION_REG_OFFSET (§8.20.4)**: `IC_DFLT_OPERATION_REG_OFFSET` *(HAS §8.20.4)*
- **Table entry IC_SLV_DFLT_IBI_PAYLOAD_SIZE: IC_SLV_DFLT_IBI_PAYLOAD_SIZE (§8.20.4)**: `IC_SLV_DFLT_IBI_PAYLOAD_SIZE` *(HAS §8.20.4)*
- **Table entry IC_SLVIF_2_COREIF_SYNC_DEPTH: IC_SLVIF_2_COREIF_SYNC_DEPTH (§8.20.4)**: `IC_SLVIF_2_COREIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_COREIF_2_SLVIF_SYNC_DEPTH: IC_COREIF_2_SLVIF_SYNC_DEPTH (§8.20.4)**: `IC_COREIF_2_SLVIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_COREIF_2_DMAIF_SYNC_DEPTH: IC_COREIF_2_DMAIF_SYNC_DEPTH (§8.20.4)**: `IC_COREIF_2_DMAIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DMAIF_2_COREIF_SYNC_DEPTH: IC_DMAIF_2_COREIF_SYNC_DEPTH (§8.20.4)**: `IC_DMAIF_2_COREIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_HDRIF_2_COREIF_SYNC_DEPTH: IC_HDRIF_2_COREIF_SYNC_DEPTH (§8.20.4)**: `IC_HDRIF_2_COREIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_SCLIF_2_COREIF_SYNC_DEPTH: IC_SCLIF_2_COREIF_SYNC_DEPTH (§8.20.4)**: `IC_SCLIF_2_COREIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_COREIF_2_SCLIF_SYNC_DEPTH: IC_COREIF_2_SCLIF_SYNC_DEPTH (§8.20.4)**: `IC_COREIF_2_SCLIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DEV_ADDR_TABLE_BUF_DEPTH: IC_DEV_ADDR_TABLE_BUF_DEPTH (§8.20.4)**: `IC_DEV_ADDR_TABLE_BUF_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DEV_CHAR_TABLE_BUF_DEPTH: IC_DEV_CHAR_TABLE_BUF_DEPTH (§8.20.4)**: `IC_DEV_CHAR_TABLE_BUF_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_HAS_DEVICE_RESET_SUPPORT: IC_HAS_DEVICE_RESET_SUPPORT (§8.20.4)**: `IC_HAS_DEVICE_RESET_SUPPORT` *(HAS §8.20.4)*
- **Table entry IC_SLVIF_2_DMAIF_SYNC_DEPTH: IC_SLVIF_2_DMAIF_SYNC_DEPTH (§8.20.4)**: `IC_SLVIF_2_DMAIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DMAIF_2_SLVIF_SYNC_DEPTH: IC_DMAIF_2_SLVIF_SYNC_DEPTH (§8.20.4)**: `IC_DMAIF_2_SLVIF_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_DFLT_DYNAMIC_ADDR_VALID: IC_DFLT_DYNAMIC_ADDR_VALID (§8.20.4)**: `IC_DFLT_DYNAMIC_ADDR_VALID` *(HAS §8.20.4)*
- **Table entry IC_SLV_MXDS_CLK_DATA_TURN: IC_SLV_MXDS_CLK_DATA_TURN (§8.20.4)**: `IC_SLV_MXDS_CLK_DATA_TURN` *(HAS §8.20.4)*
- **Table entry IC_SLV_INTERFACE_RX_WIDTH: IC_SLV_INTERFACE_RX_WIDTH (§8.20.4)**: `IC_SLV_INTERFACE_RX_WIDTH` *(HAS §8.20.4)*
- **Table entry IC_SLV_INTERFACE_TX_WIDTH: IC_SLV_INTERFACE_TX_WIDTH (§8.20.4)**: `IC_SLV_INTERFACE_TX_WIDTH` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_SLAVE_PRESENT: IC_DFLT_I2C_SLAVE_PRESENT (§8.20.4)**: `IC_DFLT_I2C_SLAVE_PRESENT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_SLV_TSX_SYMBL_CNT: IC_DFLT_SLV_TSX_SYMBL_CNT (§8.20.4)**: `IC_DFLT_SLV_TSX_SYMBL_CNT` *(HAS §8.20.4)*
- **Table entry IC_SLV_MXDS_MAX_WR_SPEED: IC_SLV_MXDS_MAX_WR_SPEED (§8.20.4)**: `IC_SLV_MXDS_MAX_WR_SPEED` *(HAS §8.20.4)*
- **Table entry IC_SLV_MXDS_MAX_RD_SPEED: IC_SLV_MXDS_MAX_RD_SPEED (§8.20.4)**: `IC_SLV_MXDS_MAX_RD_SPEED` *(HAS §8.20.4)*
- **Table entry IC_SLV_DATA_SPEED_LIMIT: IC_SLV_DATA_SPEED_LIMIT (§8.20.4)**: `IC_SLV_DATA_SPEED_LIMIT` *(HAS §8.20.4)*
- **Table entry IC_SLV_MXDS_MAX_RD_TURN: IC_SLV_MXDS_MAX_RD_TURN (§8.20.4)**: `IC_SLV_MXDS_MAX_RD_TURN` *(HAS §8.20.4)*
- **Table entry IC_DFLT_PIO_SEC_OFFSET: IC_DFLT_PIO_SEC_OFFSET (§8.20.4)**: `IC_DFLT_PIO_SEC_OFFSET` *(HAS §8.20.4)*
- **Table entry IC_DFLT_DAT_SEC_OFFSET: IC_DFLT_DAT_SEC_OFFSET (§8.20.4)**: `IC_DFLT_DAT_SEC_OFFSET` *(HAS §8.20.4)*
- **Table entry IC_HAS_TS_ASYNC0_MODE: IC_HAS_TS_ASYNC0_MODE (§8.20.4)**: `IC_HAS_TS_ASYNC0_MODE` *(HAS §8.20.4)*
- **Table entry IC_DMA_SLAVE_CLK_TYPE: IC_DMA_SLAVE_CLK_TYPE (§8.20.4)**: `IC_DMA_SLAVE_CLK_TYPE` *(HAS §8.20.4)*
- **Table entry IC_DFLT_RESP_BUF_THLD: IC_DFLT_RESP_BUF_THLD (§8.20.4)**: `IC_DFLT_RESP_BUF_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_RX_START_THLD: IC_DFLT_RX_START_THLD (§8.20.4)**: `IC_DFLT_RX_START_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_TX_START_THLD: IC_DFLT_TX_START_THLD (§8.20.4)**: `IC_DFLT_TX_START_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_BUS_AVAIL_CNT: IC_DFLT_BUS_AVAIL_CNT (§8.20.4)**: `IC_DFLT_BUS_AVAIL_CNT` *(HAS §8.20.4)*
- **Table entry IC_SLV_BCST_VEND_CCC: IC_SLV_BCST_VEND_CCC (§8.20.4)**: `IC_SLV_BCST_VEND_CCC` *(HAS §8.20.4)*
- **Table entry IC_DMA_CORE_CLK_TYPE: IC_DMA_CORE_CLK_TYPE (§8.20.4)**: `IC_DMA_CORE_CLK_TYPE` *(HAS §8.20.4)*
- **Table entry IC_HDR_TX_CLK_PERIOD: IC_HDR_TX_CLK_PERIOD (§8.20.4)**: `IC_HDR_TX_CLK_PERIOD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_DYNAMIC_ADDR: IC_DFLT_DYNAMIC_ADDR (§8.20.4)**: `IC_DFLT_DYNAMIC_ADDR` *(HAS §8.20.4)*
- **Table entry IC_DFLT_IBI_STS_THLD: IC_DFLT_IBI_STS_THLD (§8.20.4)**: `IC_DFLT_IBI_STS_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_IBI_BUF_THLD: IC_DFLT_IBI_BUF_THLD (§8.20.4)**: `IC_DFLT_IBI_BUF_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_CMD_BUF_THLD: IC_DFLT_CMD_BUF_THLD (§8.20.4)**: `IC_DFLT_CMD_BUF_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_SIR_REJECTED: IC_DFLT_SIR_REJECTED (§8.20.4)**: `IC_DFLT_SIR_REJECTED` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_FMP_HCNT: IC_DFLT_I2C_FMP_HCNT (§8.20.4)**: `IC_DFLT_I2C_FMP_HCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_FMP_LCNT: IC_DFLT_I2C_FMP_LCNT (§8.20.4)**: `IC_DFLT_I2C_FMP_LCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_BUS_FREE_CNT: IC_DFLT_BUS_FREE_CNT (§8.20.4)**: `IC_DFLT_BUS_FREE_CNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_BUS_IDLE_CNT: IC_DFLT_BUS_IDLE_CNT (§8.20.4)**: `IC_DFLT_BUS_IDLE_CNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_TS_SKEW_LCNT: IC_DFLT_TS_SKEW_LCNT (§8.20.4)**: `IC_DFLT_TS_SKEW_LCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_RX_BUF_THLD: IC_DFLT_RX_BUF_THLD (§8.20.4)**: `IC_DFLT_RX_BUF_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_TX_BUF_THLD: IC_DFLT_TX_BUF_THLD (§8.20.4)**: `IC_DFLT_TX_BUF_THLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_MR_REJECTED: IC_DFLT_MR_REJECTED (§8.20.4)**: `IC_DFLT_MR_REJECTED` *(HAS §8.20.4)*
- **Table entry IC_DFLT_HJ_REJECTED: IC_DFLT_HJ_REJECTED (§8.20.4)**: `IC_DFLT_HJ_REJECTED` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I3C_OD_HCNT: IC_DFLT_I3C_OD_HCNT (§8.20.4)**: `IC_DFLT_I3C_OD_HCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I3C_OD_LCNT: IC_DFLT_I3C_OD_LCNT (§8.20.4)**: `IC_DFLT_I3C_OD_LCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I3C_PP_HCNT: IC_DFLT_I3C_PP_HCNT (§8.20.4)**: `IC_DFLT_I3C_PP_HCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I3C_PP_LCNT: IC_DFLT_I3C_PP_LCNT (§8.20.4)**: `IC_DFLT_I3C_PP_LCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_FM_HCNT: IC_DFLT_I2C_FM_HCNT (§8.20.4)**: `IC_DFLT_I2C_FM_HCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_FM_LCNT: IC_DFLT_I2C_FM_LCNT (§8.20.4)**: `IC_DFLT_I2C_FM_LCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_SDA_TX_HOLD: IC_DFLT_SDA_TX_HOLD (§8.20.4)**: `IC_DFLT_SDA_TX_HOLD` *(HAS §8.20.4)*
- **Table entry IC_DFLT_HCI_VERSION: IC_DFLT_HCI_VERSION (§8.20.4)**: `IC_DFLT_HCI_VERSION` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_SS_HCNT: IC_DFLT_I2C_SS_HCNT (§8.20.4)**: `IC_DFLT_I2C_SS_HCNT` *(HAS §8.20.4)*
- **Table entry IC_DFLT_I2C_SS_LCNT: IC_DFLT_I2C_SS_LCNT (§8.20.4)**: `IC_DFLT_I2C_SS_LCNT` *(HAS §8.20.4)*
- **Table entry IC_IBI_BUF_LVL_SEL: IC_IBI_BUF_LVL_SEL (§8.20.4)**: `IC_IBI_BUF_LVL_SEL` *(HAS §8.20.4)*
- **Table entry IC_SLV_OFFLINE_CAP: IC_SLV_OFFLINE_CAP (§8.20.4)**: `IC_SLV_OFFLINE_CAP` *(HAS §8.20.4)*
- **Table entry IC_FW_RAM_RETIMING: IC_FW_RAM_RETIMING (§8.20.4)**: `IC_FW_RAM_RETIMING` *(HAS §8.20.4)*
- **Table entry IC_DFLT_EXT_LCNT_4: IC_DFLT_EXT_LCNT_4 (§8.20.4)**: `IC_DFLT_EXT_LCNT_4` *(HAS §8.20.4)*
- **Table entry IC_DFLT_EXT_LCNT_3: IC_DFLT_EXT_LCNT_3 (§8.20.4)**: `IC_DFLT_EXT_LCNT_3` *(HAS §8.20.4)*
- **Table entry IC_DFLT_EXT_LCNT_2: IC_DFLT_EXT_LCNT_2 (§8.20.4)**: `IC_DFLT_EXT_LCNT_2` *(HAS §8.20.4)*
- **Table entry IC_DFLT_EXT_LCNT_1: IC_DFLT_EXT_LCNT_1 (§8.20.4)**: `IC_DFLT_EXT_LCNT_1` *(HAS §8.20.4)*
- **Table entry IC_DFLT_TERMN_LCNT: IC_DFLT_TERMN_LCNT (§8.20.4)**: `IC_DFLT_TERMN_LCNT` *(HAS §8.20.4)*
- **Table entry IC_RAM_DATA_WIDTH: IC_RAM_DATA_WIDTH (§8.20.4)**: `IC_RAM_DATA_WIDTH` *(HAS §8.20.4)*
- **Table entry IC_RAM_ADDR_WIDTH: IC_RAM_ADDR_WIDTH (§8.20.4)**: `IC_RAM_ADDR_WIDTH` *(HAS §8.20.4)*
- **Table entry IC_DFLT_RING_HDR_SEC_OFFSET: 0x3C0 (§8.20.4)**: `0x3C0` *(HAS §8.20.4)*
- **Table entry IC_SPEED_HDR_DDR: IC_SPEED_HDR_DDR (§8.20.4)**: `IC_SPEED_HDR_DDR` *(HAS §8.20.4)*
- **Table entry IC_SLV_MXDS_PROG: IC_SLV_MXDS_PROG (§8.20.4)**: `IC_SLV_MXDS_PROG` *(HAS §8.20.4)*
- **Table entry IC_DFLT_EXTCAPS_SEC_OFFSET: 0x200 (§8.20.4)**: `0x200` *(HAS §8.20.4)*
- **Table entry IC_SPEED_HDR_TS: IC_SPEED_HDR_TS (§8.20.4)**: `IC_SPEED_HDR_TS` *(HAS §8.20.4)*
- **Table entry IC_HAS_HCI_EDMA: IC_HAS_HCI_EDMA (§8.20.4)**: `IC_HAS_HCI_EDMA` *(HAS §8.20.4)*
- **Table entry IC_HAS_IBI_DATA: IC_HAS_IBI_DATA (§8.20.4)**: `IC_HAS_IBI_DATA` *(HAS §8.20.4)*
- **Table entry IC_SLV_DFLT_MWL: IC_SLV_DFLT_MWL (§8.20.4)**: `IC_SLV_DFLT_MWL` *(HAS §8.20.4)*
- **Table entry IC_SLV_DFLT_MRL: IC_SLV_DFLT_MRL (§8.20.4)**: `IC_SLV_DFLT_MRL` *(HAS §8.20.4)*
- **Table entry IC_SLV_IBI_DATA: IC_SLV_IBI_DATA (§8.20.4)**: `IC_SLV_IBI_DATA` *(HAS §8.20.4)*
- **Table entry IC_HDR_CLK_TYPE: IC_HDR_CLK_TYPE (§8.20.4)**: `IC_HDR_CLK_TYPE` *(HAS §8.20.4)*
- **Table entry IC_DFLT_HJ_CTRL: IC_DFLT_HJ_CTRL (§8.20.4)**: `IC_DFLT_HJ_CTRL` *(HAS §8.20.4)*
- **Table entry IC_DFLT_IBA_INC: IC_DFLT_IBA_INC (§8.20.4)**: `IC_DFLT_IBA_INC` *(HAS §8.20.4)*
- **Table entry IC_DEVICE_ROLE: IC_DEVICE_ROLE (§8.20.4)**: `IC_DEVICE_ROLE` *(HAS §8.20.4)*
- **Table entry IC_BUF_LVL_SEL: IC_BUF_LVL_SEL (§8.20.4)**: `IC_BUF_LVL_SEL` *(HAS §8.20.4)*
- **Table entry IC_NUM_DEVICES: IC_NUM_DEVICES (§8.20.4)**: `IC_NUM_DEVICES` *(HAS §8.20.4)*
- **Table entry IC_DFLT_DCT_SEC_OFFSET: 0x100 (§8.20.4)**: `0x100` *(HAS §8.20.4)*
- **Table entry IC_SLV_BRIDGE: IC_SLV_BRIDGE (§8.20.4)**: `IC_SLV_BRIDGE` *(HAS §8.20.4)*
- **Table entry IC_SYNC_DEPTH: IC_SYNC_DEPTH (§8.20.4)**: `IC_SYNC_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_CLK_PERIOD: IC_CLK_PERIOD (§8.20.4)**: `IC_CLK_PERIOD` *(HAS §8.20.4)*
- **Table entry IC_RAM_DEPTH: IC_RAM_DEPTH (§8.20.4)**: `IC_RAM_DEPTH` *(HAS §8.20.4)*
- **Table entry IC_CLK_TYPE: IC_CLK_TYPE (§8.20.4)**: `IC_CLK_TYPE` *(HAS §8.20.4)*
- **Table entry IC_HAS_HCI: IC_HAS_HCI (§8.20.4)**: `IC_HAS_HCI` *(HAS §8.20.4)*
- **Table entry IC_HAS_PEC: IC_HAS_PEC (§8.20.4)**: `IC_HAS_PEC` *(HAS §8.20.4)*

### §8.17.3

- **Table entry IC_AVOID_RX_FIFO_FLUSH_ON_TX_ABRT: IC_AVOID_RX_FIFO_FLUSH_ON_TX_ABRT (§8.17.3)**: `IC_AVOID_RX_FIFO_FLUSH_ON_TX_ABRT` *(HAS §8.17.3)*
- **Table entry IC_PERSISTANT_SLV_ADDR_DEFAULT: IC_PERSISTANT_SLV_ADDR_DEFAULT (§8.17.3)**: `IC_PERSISTANT_SLV_ADDR_DEFAULT` *(HAS §8.17.3)*
- **Table entry IC_STOP_DET_IF_MASTER_ACTIVE: IC_STOP_DET_IF_MASTER_ACTIVE (§8.17.3)**: `IC_STOP_DET_IF_MASTER_ACTIVE` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_ACK_GENERAL_CALL: IC_DEFAULT_ACK_GENERAL_CALL (§8.17.3)**: `IC_DEFAULT_ACK_GENERAL_CALL` *(HAS §8.17.3)*
- **Table entry IC_EMPTYFIFO_HOLD_MASTER_EN: IC_EMPTYFIFO_HOLD_MASTER_EN (§8.17.3)**: `IC_EMPTYFIFO_HOLD_MASTER_EN` *(HAS §8.17.3)*
- **Table entry IC_FIRST_DATA_BYTE_STATUS: IC_FIRST_DATA_BYTE_STATUS (§8.17.3)**: `IC_FIRST_DATA_BYTE_STATUS` *(HAS §8.17.3)*
- **Table entry IC_CLK_FREQ_OPTIMIZATION: IC_CLK_FREQ_OPTIMIZATION (§8.17.3)**: `IC_CLK_FREQ_OPTIMIZATION` *(HAS §8.17.3)*
- **Table entry IC_STAT_FOR_CLK_STRETCH: IC_STAT_FOR_CLK_STRETCH (§8.17.3)**: `IC_STAT_FOR_CLK_STRETCH` *(HAS §8.17.3)*
- **Table entry IC_TX_CMD_BLOCK_DEFAULT: IC_TX_CMD_BLOCK_DEFAULT (§8.17.3)**: `IC_TX_CMD_BLOCK_DEFAULT` *(HAS §8.17.3)*
- **Table entry IC_OPTIONAL_SAR_DEFAULT: IC_OPTIONAL_SAR_DEFAULT (§8.17.3)**: `IC_OPTIONAL_SAR_DEFAULT` *(HAS §8.17.3)*
- **Table entry IC_UFM_TBUF_CNT_DEFAULT: IC_UFM_TBUF_CNT_DEFAULT (§8.17.3)**: `IC_UFM_TBUF_CNT_DEFAULT` *(HAS §8.17.3)*
- **Table entry I2C_DYNAMIC_TAR_UPDATE: I2C_DYNAMIC_TAR_UPDATE (§8.17.3)**: `I2C_DYNAMIC_TAR_UPDATE` *(HAS §8.17.3)*
- **Table entry IC_SMBUS_SUSPEND_ALERT: IC_SMBUS_SUSPEND_ALERT (§8.17.3)**: `IC_SMBUS_SUSPEND_ALERT` *(HAS §8.17.3)*
- **Table entry IC_ADD_ENCODED_PARAMS: IC_ADD_ENCODED_PARAMS (§8.17.3)**: `IC_ADD_ENCODED_PARAMS` *(HAS §8.17.3)*
- **Table entry IC_SLV_DATA_NACK_ONLY: IC_SLV_DATA_NACK_ONLY (§8.17.3)**: `IC_SLV_DATA_NACK_ONLY` *(HAS §8.17.3)*
- **Table entry IC_RX_FULL_HLD_BUS_EN: IC_RX_FULL_HLD_BUS_EN (§8.17.3)**: `IC_RX_FULL_HLD_BUS_EN` *(HAS §8.17.3)*
- **Table entry IC_SLV_RESTART_DET_EN: IC_SLV_RESTART_DET_EN (§8.17.3)**: `IC_SLV_RESTART_DET_EN` *(HAS §8.17.3)*
- **Table entry IC_UFM_SCL_HIGH_COUNT: IC_UFM_SCL_HIGH_COUNT (§8.17.3)**: `IC_UFM_SCL_HIGH_COUNT` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_UFM_SPKLEN: IC_DEFAULT_UFM_SPKLEN (§8.17.3)**: `IC_DEFAULT_UFM_SPKLEN` *(HAS §8.17.3)*
- **Table entry SLAVE_INTERFACE_TYPE: SLAVE_INTERFACE_TYPE (§8.17.3)**: `SLAVE_INTERFACE_TYPE` *(HAS §8.17.3)*
- **Table entry HC_REG_TIMEOUT_VALUE: HC_REG_TIMEOUT_VALUE (§8.17.3)**: `HC_REG_TIMEOUT_VALUE` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_SDA_SETUP: IC_DEFAULT_SDA_SETUP (§8.17.3)**: `IC_DEFAULT_SDA_SETUP` *(HAS §8.17.3)*
- **Table entry IC_FS_SCL_HIGH_COUNT: IC_FS_SCL_HIGH_COUNT (§8.17.3)**: `IC_FS_SCL_HIGH_COUNT` *(HAS §8.17.3)*
- **Table entry IC_HS_SCL_HIGH_COUNT: IC_HS_SCL_HIGH_COUNT (§8.17.3)**: `IC_HS_SCL_HIGH_COUNT` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_FS_SPKLEN: IC_DEFAULT_FS_SPKLEN (§8.17.3)**: `IC_DEFAULT_FS_SPKLEN` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_HS_SPKLEN: IC_DEFAULT_HS_SPKLEN (§8.17.3)**: `IC_DEFAULT_HS_SPKLEN` *(HAS §8.17.3)*
- **Table entry IC_BUS_CLEAR_FEATURE: IC_BUS_CLEAR_FEATURE (§8.17.3)**: `IC_BUS_CLEAR_FEATURE` *(HAS §8.17.3)*
- **Table entry IC_UFM_SCL_LOW_COUNT: IC_UFM_SCL_LOW_COUNT (§8.17.3)**: `IC_UFM_SCL_LOW_COUNT` *(HAS §8.17.3)*
- **Table entry IC_10BITADDR_MASTER: IC_10BITADDR_MASTER (§8.17.3)**: `IC_10BITADDR_MASTER` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_SDA_HOLD: IC_DEFAULT_SDA_HOLD (§8.17.3)**: `IC_DEFAULT_SDA_HOLD` *(HAS §8.17.3)*
- **Table entry IC_FS_SCL_LOW_COUNT: IC_FS_SCL_LOW_COUNT (§8.17.3)**: `IC_FS_SCL_LOW_COUNT` *(HAS §8.17.3)*
- **Table entry IC_HS_SCL_LOW_COUNT: IC_HS_SCL_LOW_COUNT (§8.17.3)**: `IC_HS_SCL_LOW_COUNT` *(HAS §8.17.3)*
- **Table entry IC_RX_FULL_GEN_NACK: IC_RX_FULL_GEN_NACK (§8.17.3)**: `IC_RX_FULL_GEN_NACK` *(HAS §8.17.3)*
- **Table entry IC_SCL_STUCK_TIMEOUT_DEFAULT: 0xffffffff (§8.17.3)**: `0xffffffff` *(HAS §8.17.3)*
- **Table entry IC_10BITADDR_SLAVE: IC_10BITADDR_SLAVE (§8.17.3)**: `IC_10BITADDR_SLAVE` *(HAS §8.17.3)*
- **Table entry IC_TX_BUFFER_DEPTH: IC_TX_BUFFER_DEPTH (§8.17.3)**: `IC_TX_BUFFER_DEPTH` *(HAS §8.17.3)*
- **Table entry IC_RX_BUFFER_DEPTH: IC_RX_BUFFER_DEPTH (§8.17.3)**: `IC_RX_BUFFER_DEPTH` *(HAS §8.17.3)*
- **Table entry IC_HC_COUNT_VALUES: IC_HC_COUNT_VALUES (§8.17.3)**: `IC_HC_COUNT_VALUES` *(HAS §8.17.3)*
- **Table entry IC_DEVICE_ID_VALUE: IC_DEVICE_ID_VALUE (§8.17.3)**: `IC_DEVICE_ID_VALUE` *(HAS §8.17.3)*
- **Table entry IC_ULTRA_FAST_MODE: IC_ULTRA_FAST_MODE (§8.17.3)**: `IC_ULTRA_FAST_MODE` *(HAS §8.17.3)*
- **Table entry REG_TIMEOUT_WIDTH: REG_TIMEOUT_WIDTH (§8.17.3)**: `REG_TIMEOUT_WIDTH` *(HAS §8.17.3)*
- **Table entry REG_TIMEOUT_VALUE: REG_TIMEOUT_VALUE (§8.17.3)**: `REG_TIMEOUT_VALUE` *(HAS §8.17.3)*
- **Table entry IC_MAX_SPEED_MODE: IC_MAX_SPEED_MODE (§8.17.3)**: `IC_MAX_SPEED_MODE` *(HAS §8.17.3)*
- **Table entry IC_HS_MASTER_CODE: IC_HS_MASTER_CODE (§8.17.3)**: `IC_HS_MASTER_CODE` *(HAS §8.17.3)*
- **Table entry IC_HAS_ASYNC_FIFO: IC_HAS_ASYNC_FIFO (§8.17.3)**: `IC_HAS_ASYNC_FIFO` *(HAS §8.17.3)*
- **Table entry IC_SMBUS_UDID_MSB: IC_SMBUS_UDID_MSB (§8.17.3)**: `IC_SMBUS_UDID_MSB` *(HAS §8.17.3)*
- **Table entry IC_SLAVE_DISABLE: IC_SLAVE_DISABLE (§8.17.3)**: `IC_SLAVE_DISABLE` *(HAS §8.17.3)*
- **Table entry IC_SMBUS_UDID_HC: IC_SMBUS_UDID_HC (§8.17.3)**: `IC_SMBUS_UDID_HC` *(HAS §8.17.3)*
- **Table entry IC_TX_CMD_BLOCK: IC_TX_CMD_BLOCK (§8.17.3)**: `IC_TX_CMD_BLOCK` *(HAS §8.17.3)*
- **Table entry IC_OPTIONAL_SAR: IC_OPTIONAL_SAR (§8.17.3)**: `IC_OPTIONAL_SAR` *(HAS §8.17.3)*
- **Table entry SLVERR_RESP_EN: SLVERR_RESP_EN (§8.17.3)**: `SLVERR_RESP_EN` *(HAS §8.17.3)*
- **Table entry APB_DATA_WIDTH: APB_DATA_WIDTH (§8.17.3)**: `APB_DATA_WIDTH` *(HAS §8.17.3)*
- **Table entry IC_MASTER_MODE: IC_MASTER_MODE (§8.17.3)**: `IC_MASTER_MODE` *(HAS §8.17.3)*
- **Table entry IC_CAP_LOADING: IC_CAP_LOADING (§8.17.3)**: `IC_CAP_LOADING` *(HAS §8.17.3)*
- **Table entry IC_DEFAULT_SLAVE_ADDR: 0x055 (§8.17.3)**: `0x055` *(HAS §8.17.3)*
- **Table entry IC_RESTART_EN: IC_RESTART_EN (§8.17.3)**: `IC_RESTART_EN` *(HAS §8.17.3)*
- **Table entry IC_USE_COUNTS: IC_USE_COUNTS (§8.17.3)**: `IC_USE_COUNTS` *(HAS §8.17.3)*
- **Table entry IC_SS_SCL_HIGH_COUNT: 0x03D9 (§8.17.3)**: `0x03D9` *(HAS §8.17.3)*
- **Table entry IC_SS_SCL_LOW_COUNT: 0x03E6 (§8.17.3)**: `0x03E6` *(HAS §8.17.3)*
- **Table entry IC_DEVICE_ID: IC_DEVICE_ID (§8.17.3)**: `IC_DEVICE_ID` *(HAS §8.17.3)*
- **Table entry IC_SMBUS_ARP: IC_SMBUS_ARP (§8.17.3)**: `IC_SMBUS_ARP` *(HAS §8.17.3)*
- **Table entry IC_INTR_POL: IC_INTR_POL (§8.17.3)**: `IC_INTR_POL` *(HAS §8.17.3)*
- **Table entry IC_CLOCK_PERIOD: 100 MHz (§8.17.3)**: `100 MHz` *(HAS §8.17.3)*
- **Table entry IC_CLK_TYPE: IC_CLK_TYPE (§8.17.3)**: `IC_CLK_TYPE` *(HAS §8.17.3)*
- **Table entry IC_HAS_DMA: IC_HAS_DMA (§8.17.3)**: `IC_HAS_DMA` *(HAS §8.17.3)*
- **Table entry IC_INTR_IO: IC_INTR_IO (§8.17.3)**: `IC_INTR_IO` *(HAS §8.17.3)*
- **Table entry IC_TX_TL: IC_TX_TL (§8.17.3)**: `IC_TX_TL` *(HAS §8.17.3)*
- **Table entry IC_RX_TL: IC_RX_TL (§8.17.3)**: `IC_RX_TL` *(HAS §8.17.3)*
- **Table entry IC_SMBUS: IC_SMBUS (§8.17.3)**: `IC_SMBUS` *(HAS §8.17.3)*

### §8.2.2

- **Register Register Targets - SRAMSS: 0xF5000000 (§8.2.2)**: `0xF5000000` *(HAS §8.2.2)*
- **Register Register Targets - MIPISS: 0xF7000000 (§8.2.2)**: `0xF7000000` *(HAS §8.2.2)*
- **Register Register Targets - NPX: 0xF6000000 (§8.2.2)**: `0xF6000000` *(HAS §8.2.2)*
- **Register PEER_IPC: 0xF1100000 (§8.2.2)**: `0xF1100000` *(HAS §8.2.2)*
- **Register unknown: 0x00000000 (§8.2.2)**: `0x00000000` *(HAS §8.2.2)*
- **Register unknown: 0x01000000 (§8.2.2)**: `0x01000000` *(HAS §8.2.2)*
- **Register unknown: 0x60000000 (§8.2.2)**: `0x60000000` *(HAS §8.2.2)*
- **Register unknown: 0x68000000 (§8.2.2)**: `0x68000000` *(HAS §8.2.2)*
- **Register unknown: 0x80000000 (§8.2.2)**: `0x80000000` *(HAS §8.2.2)*
- **Register unknown: 0xA0000000 (§8.2.2)**: `0xA0000000` *(HAS §8.2.2)*
- **Register unknown: 0xF0000000 (§8.2.2)**: `0xF0000000` *(HAS §8.2.2)*
- **Register unknown: 0xF0001000 (§8.2.2)**: `0xF0001000` *(HAS §8.2.2)*
- **Register unknown: 0xF0002000 (§8.2.2)**: `0xF0002000` *(HAS §8.2.2)*
- **Register unknown: 0xF0100000 (§8.2.2)**: `0xF0100000` *(HAS §8.2.2)*
- **Register unknown: 0xF0101000 (§8.2.2)**: `0xF0101000` *(HAS §8.2.2)*
- **Register unknown: 0xF0200000 (§8.2.2)**: `0xF0200000` *(HAS §8.2.2)*
- **Register unknown: 0xF0201000 (§8.2.2)**: `0xF0201000` *(HAS §8.2.2)*
- **Register unknown: 0xF0300000 (§8.2.2)**: `0xF0300000` *(HAS §8.2.2)*
- **Register unknown: 0xF0301000 (§8.2.2)**: `0xF0301000` *(HAS §8.2.2)*
- **Register unknown: 0xF0302000 (§8.2.2)**: `0xF0302000` *(HAS §8.2.2)*
- **Register unknown: 0xF0400000 (§8.2.2)**: `0xF0400000` *(HAS §8.2.2)*
- **Register unknown: 0xF1000000 (§8.2.2)**: `0xF1000000` *(HAS §8.2.2)*
- **Register unknown: 0xF1001000 (§8.2.2)**: `0xF1001000` *(HAS §8.2.2)*
- **Register unknown: 0xF1101000 (§8.2.2)**: `0xF1101000` *(HAS §8.2.2)*
- **Register unknown: 0xF1102000 (§8.2.2)**: `0xF1102000` *(HAS §8.2.2)*
- **Register unknown: 0xF1103000 (§8.2.2)**: `0xF1103000` *(HAS §8.2.2)*
- **Register unknown: 0xF1104000 (§8.2.2)**: `0xF1104000` *(HAS §8.2.2)*
- **Register unknown: 0xF1105000 (§8.2.2)**: `0xF1105000` *(HAS §8.2.2)*
- **Register unknown: 0xF1106000 (§8.2.2)**: `0xF1106000` *(HAS §8.2.2)*
- **Register unknown: 0xF2000000 (§8.2.2)**: `0xF2000000` *(HAS §8.2.2)*
- **Register unknown: 0xF2100000 (§8.2.2)**: `0xF2100000` *(HAS §8.2.2)*
- **Register unknown: 0xF3000000 (§8.2.2)**: `0xF3000000` *(HAS §8.2.2)*
- **Register unknown: 0xF3100000 (§8.2.2)**: `0xF3100000` *(HAS §8.2.2)*
- **Register unknown: 0xF3200000 (§8.2.2)**: `0xF3200000` *(HAS §8.2.2)*
- **Register unknown: 0xF3300000 (§8.2.2)**: `0xF3300000` *(HAS §8.2.2)*
- **Register unknown: 0xF3400000 (§8.2.2)**: `0xF3400000` *(HAS §8.2.2)*
- **Register unknown: 0xF3500000 (§8.2.2)**: `0xF3500000` *(HAS §8.2.2)*
- **Register unknown: 0xF3600000 (§8.2.2)**: `0xF3600000` *(HAS §8.2.2)*
- **Register unknown: 0xF3700000 (§8.2.2)**: `0xF3700000` *(HAS §8.2.2)*
- **Register unknown: 0xF3800000 (§8.2.2)**: `0xF3800000` *(HAS §8.2.2)*
- **Register unknown: 0xF3900000 (§8.2.2)**: `0xF3900000` *(HAS §8.2.2)*
- **Register unknown: 0xF4000000 (§8.2.2)**: `0xF4000000` *(HAS §8.2.2)*
- **Register unknown: 0xF4100000 (§8.2.2)**: `0xF4100000` *(HAS §8.2.2)*
- **Register unknown: 0xF4200000 (§8.2.2)**: `0xF4200000` *(HAS §8.2.2)*
- **Register unknown: 0xF6100000 (§8.2.2)**: `0xF6100000` *(HAS §8.2.2)*
- **Register unknown: 0xF6200000 (§8.2.2)**: `0xF6200000` *(HAS §8.2.2)*
- **Register unknown: 0xF7100000 (§8.2.2)**: `0xF7100000` *(HAS §8.2.2)*
- **Register unknown: 0xF7200000 (§8.2.2)**: `0xF7200000` *(HAS §8.2.2)*
- **Register unknown: 0xF7300000 (§8.2.2)**: `0xF7300000` *(HAS §8.2.2)*
- **Register HOST_IPC: HOST_IPC (§8.2.2)**: `HOST_IPC` *(HAS §8.2.2)*


*... 1181 additional facts omitted. Run enrichment with higher limit to include.*