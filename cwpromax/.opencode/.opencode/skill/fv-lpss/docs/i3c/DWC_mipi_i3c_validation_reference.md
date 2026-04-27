DWC_mipi_i3c Validation Reference — Synopsys IP + MIPI I3C Basic Spec — Intel FV-LPSS (NVL/PTL)
> **Source Documents:**
> - MIPI I3C Basic Specification v1.1.1 + Errata 01 (09-Jun-2021, MIPI Alliance)
> - Synopsys DWC_mipi_i3c Databook v1.00a-lca03 (January 2020)
> - NVL_PCD_H_LPSS_Integration_HAS v5.2 (Intel)

**IP:** Synopsys DWC_mipi_i3c in **HCI mode** (IC_HAS_HCI=1), Master-Only role
**Date:** March 2026

---

### 1.2 Intel Platform Context (Expanded)

This subsection captures the Intel FV-LPSS platform context that affects integration and validation of the Synopsys DWC_mipi_i3c IP. These values are authoritative from NVL_PCD_H_LPSS_Integration_HAS v5.2 and the LPSS HAS digest.

- Platforms: NVL (PCD-H / PCH-S), PTL, MTL, LNL, WCL, MTP-S (see HAS for per-die deviations).
- Instances: 4 I3C instances per platform (2 controllers × 2 buses) — MTP-S has 2 instances (1 controller).
- BAR size: 8 KB per controller pair (shared between two bus instances).
- Ring layout: Command/Response and Data rings cross into upper BAR ranges (RH1 at 0x1180/0x1580). See Section 11.2 for ring layout.
- Core clock (i3c_clk): POR values vary by platform. NVL: 200 MHz (POR); PTL/WCL: 100 MHz; minimum core_clk for 12.5 MHz SCL = 125 MHz.
- IOSF bridge type: PTL/WCL/NVL use IOSF2AXI (AXI downstream), others use IOSF2OCP.
- IOSF sideband port width and bridge behavior: AXI downstream uses 16-bit port IDs and supports bulk R/W; OCP uses 8-bit.
- DMA/PIO policy: DMA is the production-only mode (ROC=1 required for DMA commands). PIO mode is debug-only (enable via GPPRVRW8.bit0) and MUST NOT be used in production firmware.
- Chicken-bit workaround: exists in bridge private register `gen_pvt_high_regrw4` (private config region; chicken-bit referenced near private offset 0x61C in some platform docs). See Section 11.14 and 11.20 for exact PythonSV paths and code snippets.
- Power-management constraints: I3C does NOT support D0i3 (Vnn removal in D0i3 is NOT allowed). Vnn removal must use D3-hot / S0ix sequences with PMC handshake (`lpss_pmc_vnn_req` / `pmc_lpss_vnn_ack`). See Section 14 for full sequences.
- Electrical: I3C on LPSS is 1.8V-only. Platform must configure pads to 1.8V and set PMode correctly before enabling the controller.
- Limitations (LPSS deviations): DEV_INDEX is 4 bits (bits [19:16]) — max 8 DAT entries per bus. CHUNK_SIZE max = 128 bytes. Ring size = 0 or 2–255 (size=1 invalid). Immediate data = write-only, SDR-only. Combo transfers limited to SDR WR+WR or SDR WR+RD only.

These platform constraints MUST be validated early in bring-up and included in the platform integration checklist.

---

### 2.10 Intel DWC Configuration

Intel LPSS-specific recommended HCI configuration parameters:

| Parameter | Suggested Value (Intel) | Rationale |
|-----------|-------------------------|-----------|
| TX Queue Depth | 64 DW | Default HW depth; validated in HAS |
| RX Queue Depth | 64 DW | Default HW depth |
| IBI Queue Depth | 64 DW | Supports wake/IBI capture during Vnn events |
| DMA Threshold | 32 DW | Matches iDMA default watermark |
| DAT Entries | 8 per bus | Must not exceed DEV_INDEX encoding (4-bit) |
| DCT Entries | 8 per bus (transient) | Captured during ENTDAA |
| DEV_INDEX Field | Bits [19:16] (4-bit) | LPSS deviation from HCI spec (max 8 entries) |
| CHUNK_SIZE | Max = 128 bytes | HCI-spec allows 256B; LPSS limited to 128B |
| ROC | 1 for DMA commands | Production DMA must set ROC=1 |
| CP (CCC flag) | Per-command | Use CP=1 for CCCs as HCI spec requires |
| TX_START_THLD | Platform tuned (HDR safe) | Must be large enough to pre-load TX for HDR-DDR to avoid underflow (see BUG-003) |
| IBI_STATUS_THLD | 0 (immediate) | Recommended to avoid lost IBIs and to generate prompt host wake |
| Queue sizes (ring headers) | Use values in HAS: avoid size=1 | Size=1 is invalid; use 0 or 2–255 |

Notes:
- Program DAT base at BAR+0x80 (Bus0) and BAR+0x480 (Bus1). Program DCT base at BAR+0x100 / BAR+0x500 respectively.
- Configure HC_CONTROL: set I2C_SLAVE_PRESENT=1 for mixed bus before ENTDAA; set BUS_ENABLE last after all DAT & chicken-bit programming.

---

### 5.8 Intel Platform DAA Constraints

Additional constraints and best-practices when performing DAA on Intel LPSS platforms:

- Maximum targets per bus = 8 (limited by DAT entries).
- Mixed bus caution: If legacy I2C devices present, set `HC_CONTROL.I2C_SLAVE_PRESENT = 1` before ENTDAA and prefer SETDASA for known static I2C devices.
- DAT.DEVICE field: set `DEVICE=1` for I2C static devices so controller treats them as static and doesn't capture them during ENTDAA.
- DEV_INDEX encoding: use bits [19:16] only; do not place DAT indices outside 0–7.
- After ENTDAA completes, software must update each DAT.IBI_WITH_DATA field from captured DCT.BCR[2].

---

### 8.9 HSDES 18044213731 

HSDES ID: 18044213731 (tracked as BUG-001 in lpss_known_issues.md).

Summary:
- Symptom: Controller may enter HALT or exhibit BUS_ENABLE stuck behavior after a HW-initiated or SW-initiated abort when DMAC_NO_CLEAR_CTRL_Q_ON_ABORT=3. Subsequent transfers can see TID mismatches and failures.
- Affected platforms: PTL, WCL, NVL (platforms using IOSF2AXI + DMA).

Root cause:
- Bridge private chicken-bit default value causes DMAC behavior that does not clear control queue on abort. When the DMA controller does not properly clear internal control structures on abort, the HCI layer may get confused on resuming and present stale TID/queue pointers.

Workaround (Intel authoritative):
Insert the IOSF2AXI bridge chicken-bit workaround early in bring-up (before enabling BUS_ENABLE). Exact PythonSV paths are provided in Section 11.20. Example (verbatim):

```python
# Set chicken_bit gen_pvt_high_regrw4[1:0] = 0
# NVL PCD-H path:
cb = nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
cb.write(cb.read() & ~0x3)  # Clear bits [1:0]

# PTL path:
cb = nn.sv.socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
cb.write(cb.read() & ~0x3)
```

Additional notes:
- The chicken-bit register is referenced in the HAS and known-issues tracker. In some platform documentation the private register is referenced near offset ~0x61C in the private region; use the PythonSV named-node paths above for exact access in VJT.
- Apply this workaround for all DMA-based I3C initializations on PTL/WCL/NVL. For debug or PIO-only flows this is not required but still recommended.

---

### 10.3 Intel Platform Electrical Notes

- I3C I/O voltage: 1.8V only. Platform must ensure pads are configured to 1.8V and PMode selects the I3C function.
- Pull-up sizing: use calculated Rp in Section 10.1; Errata 21 increased pull-up rise time expectation to 120ns.
- PAD configuration: ensure Push-Pull / Open-Drain muxing is correct for SDR/HDR transitions. Pad misconfiguration may cause bus contention or permanent damage to peripherals.
- Clock loopback: LPSS I3C uses a 2x buffer loopback path for high-frequency SCL. Validate loopback routing during hardware bring-up.

---

### 11.1.1 LPSS I3C Topology & HCI Notes (Intel)

| Platform | Controllers (instances) | Notes |
|----------|------------------------|-------|
| NVL | 4 instances (2 controllers × 2 buses) | POR core_clk = 200 MHz; IOSF2AXI bridge; bulk R/W supported |
| PTL | 4 instances | POR core_clk = 100 MHz; IOSF2AXI bridge |
| MTL / LNL | 4 instances | IOSF2OCP bridge |
| MTP-S | 2 instances | Single controller (I3C0+I3C1) |

Notes:
- A single controller reset (RESETS at BAR+0x2B4) resets both bus instances plus DMA. There is no per-bus independent reset.
- HCI version varies by platform; validate HCI_VERSION register early and program configuration accordingly.

---

### 11.14 DMA Architecture (Intel additions)

- IOSF2AXI bridge nuance: AXI downstream semantics may present multi-beat writes; LPSS/driver MUST avoid multi-beat bursts into bridge private region. Use single DW writes to private registers.
- Chicken-bit register: `gen_pvt_high_regrw4` (bridge private config register, referenced in HAS and known-issues). Workaround bits [1:0] control DMAC abort-clear behavior. Intel documentation references this private register near offset ~0x61C in the private region; use PythonSV named-nodes for exact access (Section 11.20).
- iDMA/chicken-bit relationship: set chicken-bit to clear abort-control behavior before enabling DMA-based I3C operations.

---

### 11.20 PythonSV Access Paths (Intel NVL/PTL)

Intel-provided exact PythonSV named-node paths for the chicken-bit and I3C controller instances. These strings MUST be used verbatim in test scripts and the VJT framework.

- NVL PCD-H chicken-bit path:
  nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4

- PTL chicken-bit path:
  nn.sv.socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4

- NVL I3C controller examples (named nodes):
  - i3c_ctrl1_bus0 = nn.sv.socket0.pcd.lpss.i3c0_0
  - i3c_ctrl1_bus1 = nn.sv.socket0.pcd.lpss.i3c0_1
  - i3c_ctrl2_bus0 = nn.sv.socket0.pcd.lpss.i3c2_0
  - i3c_ctrl2_bus1 = nn.sv.socket0.pcd.lpss.i3c2_1

- PTL I3C controller examples (named nodes):
  - i3c_ctrl1_bus0 = nn.sv.socket0.soc.lpss.i3c0_0
  - i3c_ctrl1_bus1 = nn.sv.socket0.soc.lpss.i3c0_1

Initialization snippet (recommended order):

```python
# 1) Set chicken-bit (NVL/PTL path as appropriate) BEFORE enabling BUS_ENABLE
cb = nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
cb.write(cb.read() & ~0x3)

# 2) Program DAT entries and ring headers
# 3) Enable BUS_ENABLE in HC_CONTROL (bit 31)
# 4) Perform ENTDAA/SETAASA flows
```

Use these exact named-nodes in PythonSV test scripts to ensure reproducible register access across NVL and PTL trees.

---

### 12.3 Intel Platform Note

Note: Secondary master / multi-master capability is NOT supported on Intel LPSS I3C controllers. Drivers and firmware must not enable or expect secondary master behavior.

---

## 14. Power Management (Intel LPSS I3C)

This section consolidates Intel LPSS power-management guidance for I3C controllers (Vnn removal, DEVIDLE_CONTROL, RESETS, save/restore, IBI wake flows).

### 14.1 D-State Summary (Intel)

| State | Trigger | Resume Latency | Clock | Power |
|-------|---------|---------------:|-------|------:|
| D0 | Active | 0 | On | Full |
| D0i2 | Auto on idle | ~10 µs | Gated | Reduced |
| D0i3 | N/A for I3C | N/A | N/A | N/A |
| D3-Hot | OS/PMC | ~1–10 ms | Off (Vnn removed) | Power gated |
| S0ix | OS coordinated with PMC | Platform-specific | Off | Power gated |

Notes:
- I3C does NOT support D0i3; Vnn removal must be performed only in D3-Hot or S0ix states with PMC coordination.

### 14.2 Key PM Registers (BAR-relative)

- DEVIDLE_CONTROL: BAR + 0x2CC (I3C). Controls device idle, restore flags and idle status.
- RESETS: BAR + 0x2B4 (I3C). Assert I3C_RESET = 0 to reset controller, wait for RESET_DONE.
- CS_ACTIVELTR: BAR + 0x2BC (I3C) — Active LTR
- CS_IDLELTR: BAR + 0x2C0 (I3C) — Idle LTR

### 14.3 Vnn Removal Entry Sequence (Intel simplified)

1. Ensure all command/response queues are drained (no pending CMD/RSP or DMA outstanding).
2. Program DEVIDLE_CONTROL.DEVIDLE = 1 to indicate device intends to idle.
3. Clear IDLE_LTR if set (platform-specific) and set LTRs to conservative values.
4. PMC coordinates power gate: PM firmware performs lpss_pmc_vnn_req handshake and asserts vnn_isol_latchen.
5. Vnn rail removed; only AON domain is live (RTC and VNNAON logic remain).

### 14.4 Vnn Removal Exit Sequence (Intel simplified)

1. IBI wake or host-initiated restore asserts lpss_pmc_vnn_req.
2. PMC restores Vnn and asserts pmc_lpss_vnn_ack.
3. Isolation latches are cleared, clocks restored (rosc_fast_clk).
4. Software executes save/restore flow: restore PCI config registers 1 then MMIO CL registers, then DEVIDLE_CONTROL last.
5. Reinitialize DAT/DCT if necessary and resume bus operations.

### 14.5 IBI Wake Flow Notes

-+- IBI wake path uses RTC/32.768kHz and VNNAON domain to capture wake events when Vnn removed.
-+- The IBI wake flow includes 29 logical steps in HAS; testers should validate at minimum: lpss_pmc_vnn_req assertion, pmc_lpss_vnn_ack handshake, controller reset and re-init, and successful capture of IBI payload after Vnn restore.

### 14.6 Save/Restore Guidance (Intel)

Save order (Group 1 then Group 2):
1) Force clocks on via GEN_PVT_LOW_REGRW2 (BAR+0x604 bit 3) to access retention registers.
2) Save PCI config headers and MMIO convergence layer registers.
3) Save DEVIDLE_CONTROL last.
4) Save bridge private registers (bulk read if supported on platform).

Restore (reverse): restore PCI config, MMIO CL, DEVIDLE_CONTROL, then bridge private.

---

### M. Power Management Checklist (Intel additions)

- [ ] Verify DEVIDLE_CONTROL at BAR+0x2CC read/write behavior and RESTORE bit handling.
- [ ] Verify RESETS at BAR+0x2B4 performs controller reset for both bus instances.
- [ ] Validate Vnn removal entry sequencing: lpss_pmc_vnn_req -> pmc_lpss_vnn_ack -> isolation latchengage -> Vnn OFF.
- [ ] Validate Vnn restore sequencing and software save/restore ordering (DEVIDLE_CONTROL restored last).
- [ ] Test IBI wake from Vnn-removed state (D3-Hot): host receives IBI payload and system asserts PME as expected.
- [ ] Confirm that I3C controllers are not expected to support D0i3 (attempting D0i3 should be rejected or documented).

---

### N. Multi-Bus Checklist (Intel additions)

- [ ] Verify independent DAA per bus: ENTDAA may be run independently on Bus #0 and Bus #1.
- [ ] Verify DAT/DCT base offsets: DAT@BAR+0x80 / BAR+0x480 and DCT@BAR+0x100 / BAR+0x500.
- [ ] Verify simultaneous transfers on Bus #0 and Bus #1 do not interfere (shared iDMA but separate rings).
- [ ] Ensure RESETS at BAR+0x2B4 resets both bus instances and DMA; verify reset sequence recovers both buses.
- [ ] Validate IOSF SB routing and bridge private register access for each controller pair (port IDs and connIDs).

---

## References (Intel)

- NVL_PCD_H_LPSS_Integration_HAS v5.2 (Intel) 
- LPSS Integration HAS Digest (v5.2, Doc Rev 1.02) 
- LPSS I3C HCI Reference (HAS v5.2 Digest)
- LPSS Known Issues & Sighting Tracker (lpss_known_issues.md)

*End of file (merged Intel LPSS content)*
## Table of Contents

1. [Document Overview and Errata](#1-document-overview-and-errata)
2. [I3C Bus Architecture](#2-i3c-bus-architecture)
3. [SDR Mode Protocol](#3-sdr-mode-protocol)
4. [Common Command Codes (CCCs)](#4-common-command-codes-cccs)
5. [Dynamic Address Assignment (DAA)](#5-dynamic-address-assignment-daa)
6. [In-Band Interrupt (IBI)](#6-in-band-interrupt-ibi)
7. [HDR Modes](#7-hdr-modes)
8. [Error Detection and Recovery](#8-error-detection-and-recovery)
9. [Timing Specifications](#9-timing-specifications)
10. [Electrical Specifications](#10-electrical-specifications)
11. [DWC Implementation Details](#11-dwc-implementation-details)
12. [Multi-Master / Secondary Controller](#12-multi-master--secondary-controller)
13. [Target Reset](#13-target-reset)
14. [Power Management](#14-power-management)
15. [Validation Checklist](#15-validation-checklist)

---

## 1. Document Overview and Errata

### 1.1 Purpose

This document includes Intel-specific validation guidance for the Synopsys DWC_mipi_i3c controller when integrated in Intel FV-LPSS platforms (NVL/PTL). It augments the MIPI I3C Basic Spec and Synopsys databook with Intel HAS-derived constraints, register offsets, and validation flows. Where Intel HAS is referenced, exact register offsets and PythonSV access paths from NVL_PCD_H_LPSS_Integration_HAS v5.2 are authoritative.

Intel-specific constraints and deviations emphasized in this document include:

- DEV_INDEX is 4-bit (Intel deviation) — maximum 8 DAT entries per bus.
- CHUNK_SIZE maximum is 128 bytes (Intel deviation).
- DEVIDLE_CONTROL register offset: BAR + 0x2CC.
- RESETS register offset: BAR + 0x2B4.
- DAT/DCT base offsets: DAT@BAR+0x80 / BAR+0x480, DCT@BAR+0x100 / BAR+0x500.
- IOSF2AXI private config chicken-bit for abort recovery at gen_pvt_high_regrw4 (private config reg, referenced at 0x61C in HAS); PythonSV access paths provided in Section 11.20.
- PIO mode is debug-only; production firmware should use DMA (ROC=1) for heavy traffic and HDR modes.
- Secondary master mode is NOT supported on Intel LPSS I3C controllers.

These platform items are mandatory checks for FV-LPSS integration and validation.
### 1.3 Errata 01 — Normative Corrections

Errata 01 (21 items) supersedes original v1.1.1 text. All corrections are **normative**.

| # | Area | Change | Validation Impact |
|---|------|--------|-------------------|
| 3 | OD Timing | First 7'h7E after bus init **MUST** use FM/FM+ OD timing | Verify first broadcast uses OD speed |
| 5-7 | Passive Hot-Join | Target must see 7'h7E/W + STOP before emitting HJ Request | Verify passive HJ sequence |
| 8 | ENTDAA | Changed from Required to **Conditional** | ENTDAA may not be on all devices |
| 9-14 | SETMWL/SETMRL | Minimum payload removed (was 16B, now Target-defined; supports legacy 8B from v1.0) | Do NOT assume 16-byte minimum |
| 16-17 | SETDASA/SETAASA | Target **SHALL NACK** if DA already assigned | Verify NACK on duplicate DA |
| 19 | RSTACT GET default | Changed from 0x00 to **0x80** | Verify default GET returns 0x80 |
| 20 | Target Reset Pattern | **tDIG_H minimum** applies to ALL SDA/SCL transitions during pattern | Timing compliance |
| 21 | Pull-Up Rise Time | Changed from 100ns to **120ns** (JEDEC JESD403) | Update timing parameters |

### 1.4 Known Bugs and Sightings (Intel)

This section lists Intel LPSS known issues and HSDES sightings relevant to I3C integration (extracted from lpss_known_issues.md):

- BUG-001 (HSDES 18044213731) — Abort Recovery / HALT during HDR-DDR abort on NVL. Symptoms: controller may enter HALT when aborting HDR-DDR frames; workaround: enable IOSF2AXI chicken-bit (gen_pvt_high_regrw4 private config register) to alter abort handling. See Section 8.9 for full description and PythonSV snippet.
- BUG-003 — DAT/DCT overflow under heavy IBI/mixed bus traffic. Mitigation: increase IBI FIFO depth, tune IBI_STATUS_THLD, and validate QUEUE_STATUS_LEVEL handling.
- HSDES-003 — Power-management wake ordering and Vnn removal/restore edge cases. Follow Power Management checklist (Section M).
- STARs / Sightings: validation reported multiple STARs relating to IBI sizing, CHUNK_SIZE handling, and DEVIDLE_CONTROL sequencing on NVL/PTL platforms.


---

## 2. I3C Bus Architecture

### 2.1 Device Roles (MIPI Table 2)

| Role | Key Requirements |
|------|------------------|
| Primary Controller | All SDR + CCC required. HDR Exit Pattern detection **REQUIRED** even if HDR not supported |
| Secondary Controller | Full protocol + DA retention + device table |
| SDR-Only Target | **Must still detect HDR Exit Pattern** to track bus state |
| HDR-Capable Target | Must implement HDR-DDR and/or HDR-BT protocol |

**Critical:** ALL Targets, including SDR-Only, **SHALL** implement HDR Exit Pattern detection.

### 2.2 Bus Types

| Bus Type | Description | fSCL | Key Constraints |
|----------|-------------|------|-----------------|
| Pure I3C | Only I3C devices | Up to 12.5 MHz PP | tDIG_H for OD |
| Mixed Fast | I2C with 50ns spike filter | Up to 12.5 MHz PP | tDIG_H_MIXED ≤45ns; 50ns spike filter hides PP from I2C |
| Mixed Slow/Limited | I2C Fm/Fm+ only | Fm (400 KHz) / Fm+ (1 MHz) | Full I2C timing compliance |

### 2.3 Legacy I2C on I3C Bus (MIPI Table 3)

- **Fm or Fm+** speed required (no Sm/HS)
- 50ns Spike Filter **SHALL be disabled** on I3C bus
- Clock Stretching **NOT allowed**
- 20mA OD driver **NOT used**
- Must not respond to 7'h7E

### 2.4 Legacy I2C Categories (MIPI Table 4)

| Index | Category | Spike Filter | Freq Tolerant | Notes |
|-------|----------|-------------|---------------|-------|
| 0 | With spike filter | Yes (must disable) | N/A | Best compatibility |
| 1 | No spike filter, freq tolerant | No | Yes | Acceptable |
| 2 | No spike filter, not freq tolerant | No | No | Most limiting; degrades bus performance |

LVR byte encodes the category index.

### 2.5 7-Bit Address Map (MIPI Table 8)

| Address | Usage | Notes |
|---------|-------|-------|
| 7'h00 | Reserved | I2C General Call |
| 7'h01 | Reserved | I2C CBUS, Minimal Bus SETDASA form |
| 7'h02 | Hot-Join Address | Very low = high arbitration priority |
| 7'h03 | Optional | I2C reserved; usable if no conflict |
| 7'h04-07 | Conditional | Only if HS mode not in use |
| 7'h08-3D | Usable | IBI-capable targets prefer 7'h03-3F |
| 7'h3E | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h40-5D | Usable | Non-IBI targets prefer 7'h40-7B |
| 7'h5E | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h6E | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h76 | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h78-7B | Conditional | Only if Extended Address not in use |
| 7'h7A | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h7C | **SHALL NOT USE** | Broadcast single-bit error detection |
| 7'h7E | Broadcast Address | Used for CCC initiation |
| 7'h7F | **SHALL NOT USE** | Broadcast single-bit error detection |

**~108 usable addresses.** IBI-capable targets assigned in low range (higher IBI priority), non-IBI in high range.

### 2.6 BCR — Bus Characteristics Register (MIPI Table 5)

| Bit | Name | Values |
|-----|------|--------|
| [7:6] | Device Role | 00=Target, 01=Secondary Controller |
| [5] | Advanced Capabilities | 1=Use GETCAPS |
| [4] | Virtual Target | 1=VT |
| [3] | Offline Capable | 1=May go offline (affects error escalation) |
| [2] | IBI Payload | 1=MDB follows IBI |
| [1] | IBI Request Capable | 1=Can issue IBI |
| [0] | Max Data Speed Limitation | 1=Use GETMXDS (tSCO >12ns sets this) |

**DWC Note:** After ENTDAA, software **must** update `DAT.IBI_WITH_DATA` from `BCR[2]`.

### 2.7 DCR — Device Characteristics Register (MIPI Table 6)

8-bit device type (0x00 = Generic/Unspecified). Assigned by MIPI Alliance.

### 2.8 PID — Provisional ID (48 bits)

Returned by GETPID as 6 bytes MSB-first:

```
Bits [47:33] = MIPI Manufacturer ID (15-bit, LSBs of full MIPI ID)
Bit  [32]    = ID Type Selector (0=Vendor Fixed, 1=Random 32-bit)
Bits [31:16] = Part ID (vendor-assigned)
Bits [15:12] = Instance ID (distinguishes identical parts)
Bits [11:0]  = Extra Info (vendor-defined)
```

When Bit[32]=1, bits [31:0] are random for distinguishing identical devices during DAA.

**DWC:** Captured in DCT DW0-DW1 during ENTDAA.

### 2.9 LVR — Legacy Virtual Register (MIPI Table 7)

| Bit | Name |
|-----|------|
| [7:5] | I2C Device Index (per Table 4) |
| [4] | I2C Mode (0=Fm+, 1=Fm) |
| [3:0] | Reserved (0) |

| IC_CLK_TYPE | 1 (async) |
| HC_CONTROL.I2C_SLAVE_PRESENT | Set for mixed bus |
| HC_CONTROL.IBA_INCLUDE | Set for IBI priority detection |

---

## 3. SDR Mode Protocol

### 3.1 Data Words (9-bit)

Each SDR data word = 8 data bits + 1 T-bit (Transition bit):

| Direction | T-bit Meaning |
|-----------|---------------|
| Write (Ctrl→Tgt) | Odd Parity = `XOR(Data[7:0], 1)` |
| Read T=0 | End of data (Target drives Low→High-Z, Controller drives Low) |
| Read T=1 | More data (Target High-Z on rising SCL, Controller may abort by driving SDA Low) |

**Target timeout:** If SCL unchanged for **100 µs**, Target should abandon read.

### 3.2 ACK/NACK Handoff

**ACK → Write Handoff:**
1. Target ACKs in OD (drives SDA Low)
2. Target releases SDA on rising SCL edge
3. Controller drives SDA Low on rising SCL (safe overlap — both driving Low)
4. Controller transitions to Push-Pull on falling SCL edge

**ACK → IBI MDB Handoff:**
1. Controller holds SDA Low during ACK phase
2. Target drives SDA Low after rising SCL edge
3. Controller may release SDA after tSCO delay
4. MDB data follows in Push-Pull

### 3.3 SDA Mode Switching During Frame (MIPI Tables 88-90)

**New Frame Without Contention on A6 (Table 88):**

| Phase | START | Addr[6] | Addr[5:0]+RnW | ACK | Data+T | STOP |
|-------|-------|---------|----------------|-----|--------|------|
| SDA Mode | OD | OD | **PP** | OD | PP | PP |

**New Frame With Contention on A6 (Table 89):**

| Phase | START | Addr[6] | Addr[5:0]+RnW | ACK | Data+T | STOP |
|-------|-------|---------|----------------|-----|--------|------|
| SDA Mode | OD | OD | **OD** | OD | PP | PP |

**Continuation with Repeated START (Table 90):**

| Phase | Sr | Addr+RnW | ACK | Data+T | STOP |
|-------|-----|----------|-----|--------|------|
| SDA Mode | PP | PP | OD | PP | PP |

### 3.4 Bus Conditions

| Condition | Parameter | Pure I3C | Mixed Fast | Mixed Slow |
|-----------|-----------|----------|------------|------------|
| Bus Free | tCAS / tBUF | ≥38.4ns | ≥0.5µs (Fm+) / ≥1.3µs (Fm) | Same as I2C |
| Bus Available | tAVAL | ≥1.0µs | ≥1.0µs | — |
| Bus Idle | tIDLE | ≥200µs | ≥200µs | — |

### 3.5 Activity States (MIPI Table 11)

| State | tCAS Max | CCC | Default |
|-------|----------|-----|---------|
| ENTAS0 | 1 µs | 0x02 | — |
| ENTAS1 | 100 µs | 0x03 | — |
| ENTAS2 | 2 ms | 0x04 | — |
| ENTAS3 | 50 ms | 0x05 | **Default at init** |

Target may NACK access if polled before the interval expires.

### 3.6 Clock Stalling Limits

| Phase | Max Stall |
|-------|-----------|
| ACK | ≤100 µs |
| Write Parity / Read T-bit | ≤100 µs |
| DAA first bit | ≤15 ms |
| **Absolute max** | **15 ms** |

**DWC:** Controller stalls SCL in SDR only (TX empty, RX full). **No stalling in HDR** — underflow/overflow causes abrupt termination.

### 3.7 Mixed Fast Bus Duty Cycle Technique

Short SCL High (e.g., 40ns) + long SCL Low (e.g., 280ns) = 3.125 MHz effective. I2C spike filter (50ns) suppresses the short High pulse — I2C device sees no activity. Allows higher effective data rates hidden from Legacy I2C.

### 3.8 Address Header Arbitration

- **Bit value 0:** Device drives SDA Low
- **Bit value 1:** Device releases SDA (High-Z), pulled High by bus pull-up
- Device that reads back a value different from what it drove has **lost arbitration** and must stop driving
- Three collision scenarios with Controller Role Request vs. Private Read/Write — live-lock avoidance via **Repeated START** (not STOP + START)

---

## 4. Common Command Codes (CCCs)

### 4.1 CCC Framework

- Address range: **0x00-0x7F** = Broadcast, **0x80-0xFE** = Direct, **0xFF** = Reserved
- Every CCC starts with **7'h7E/W** (Broadcast Address, Write)
- CCC ends with **STOP** or **Sr + 7'h7E** (Repeated START to Broadcast Address)

**Four CCC Categories:**
1. Broadcast Write (Controller → all Targets)
2. Direct Read (Controller ← specific Target)
3. Direct Write (Controller → specific Target)
4. Direct Read/Write (bidirectional with specific Target)

### 4.2 Complete CCC Reference — Broadcast (0x00-0x7F)

| Code | Name | Type | Req/Opt | Payload | Key Details |
|------|------|------|---------|---------|-------------|
| 0x00 | ENEC | Broadcast | Req | 1B bitmask | Enable Events: bit0=SIR, bit1=MR, bit3=HJ |
| 0x01 | DISEC | Broadcast | Req | 1B bitmask | Disable Events: same bitmask as ENEC |
| 0x02 | ENTAS0 | Broadcast | Opt | None | Activity State 0 (tCAS max 1µs) |
| 0x03 | ENTAS1 | Broadcast | Opt | None | Activity State 1 (tCAS max 100µs) |
| 0x04 | ENTAS2 | Broadcast | Opt | None | Activity State 2 (tCAS max 2ms) |
| 0x05 | ENTAS3 | Broadcast | Opt | None | Activity State 3 (tCAS max 50ms, **default**) |
| 0x06 | RSTDAA | Broadcast | Req | None | Clear all DAs + Group Addrs |
| 0x07 | ENTDAA | Broadcast | Cond | DAA proc | DAA procedure (Errata 8: Conditional) |
| 0x08 | DEFTGTS | Broadcast | Req(SC) | 4B/entry | Define Targets for Secondary Controllers |
| 0x09 | SETMWL | Broadcast | Opt | 2B MSB-first | Max Write Length; min=Target-defined (Errata 9-14) |
| 0x0A | SETMRL | Broadcast | Opt | 2B + opt 3rd | Max Read Length; 3rd byte=IBI payload limit (0=unlimited) |
| 0x0B | ENTTM | Broadcast | Opt | 1B | Test Mode: 0x00=Exit, 0x01=Vendor test |
| 0x0C | SETBUSCON | Broadcast | Opt | 1B | Bus context byte |
| 0x12 | ENDXFER | Broadcast | Opt | 1-2B | HDR-DDR early termination |
| 0x20 | ENTHDR0 | Broadcast | Cond | None | Enter HDR-DDR mode |
| 0x21 | ENTHDR1 | Broadcast | — | None | Enter HDR-TSP (NOT in I3C Basic) |
| 0x22 | ENTHDR2 | Broadcast | — | None | Enter HDR-TSL (NOT in I3C Basic) |
| 0x23 | ENTHDR3 | Broadcast | Cond | None | Enter HDR-BT mode |
| 0x29 | SETAASA | Broadcast | Opt | None | Static→Dynamic for all; NACK if DA assigned (Errata 16-17) |
| 0x2A | RSTACT | Broadcast | Req | 1B def byte | Reset action config (see 4.5) |
| 0x2B | DEFGRPA | Broadcast | Opt | 4B/entry | Define Group membership |
| 0x2C | RSTGRPA | Broadcast | Opt | None | Reset Group Addresses |
| 0x2D | MLANE | Broadcast | Opt | Varies | Multi-Lane config |

### 4.3 Complete CCC Reference — Direct (0x80-0xFE)

| Code | Name | Type | Req/Opt | Payload | Key Details |
|------|------|------|---------|---------|-------------|
| 0x80 | ENEC | Direct | Req | 1B bitmask | Enable Events per target |
| 0x81 | DISEC | Direct | Req | 1B bitmask | Disable Events per target |
| 0x82 | ENTAS0 | Direct | Opt | None | Activity State 0 per target |
| 0x83 | ENTAS1 | Direct | Opt | None | Activity State 1 per target |
| 0x84 | ENTAS2 | Direct | Opt | None | Activity State 2 per target |
| 0x85 | ENTAS3 | Direct | Opt | None | Activity State 3 per target |
| 0x86 | RSTDAA | Direct | — | — | (Not a valid Direct CCC) |
| 0x87 | SETDASA | Direct | Opt | 1B addr | DA from static; NACK if DA assigned (Errata 16-17) |
| 0x88 | SETNEWDA | Direct | Req* | 1B new DA | Change existing DA (*unless static-only) |
| 0x89 | SETMWL | Direct | Opt | 2B MSB-first | Max Write Length per target |
| 0x8A | SETMRL | Direct | Opt | 2-3B | Max Read Length per target |
| 0x8B | GETMWL | Direct | Opt | Returns 2B | Get Max Write Length |
| 0x8C | GETMRL | Direct | Opt | Returns 2-3B | Get Max Read Length |
| 0x8D | GETPID | Direct | Opt | Returns 6B | Get 48-bit PID (MSB-first) |
| 0x8E | GETBCR | Direct | Opt | Returns 1B | Get Bus Characteristics Register |
| 0x8F | GETDCR | Direct | Opt | Returns 1B | Get Device Characteristics Register |
| 0x90 | GETSTATUS | Direct | Req | Returns 2B | See 4.4 |
| 0x91 | GETSTATUS | Direct | Req | DB + Returns 2B | Format 2 with Defining Byte PRECR=0x91 |
| 0x92 | ENDXFER | Direct | Opt | 1-2B | HDR-DDR early termination per target |
| 0x93 | — | — | — | — | Reserved |
| 0x94 | — | — | — | — | Reserved |
| 0x95 | GETCAPS | Direct | Req | Returns 2-4B | See 4.6 |
| 0x96 | SETROUTE | Direct | Opt | Varies | Routing Device config |
| 0x97-0x99 | — | — | — | — | Reserved |
| 0x9A | RSTACT | Direct | Req | 1B def byte | Reset action config per target |
| 0x9B | SETGRPA | Direct | Opt | 1B | Assign Group Address |
| 0x9C | RSTGRPA | Direct | Opt | None | Reset Group Address |
| 0x9D | MLANE | Direct | Opt | Varies | Multi-Lane config per device |

### 4.4 GETSTATUS (0x90) Detail

**Format 1** (no Defining Byte): Returns 2 bytes:

| Byte | Bit | Name | Notes |
|------|-----|------|-------|
| LSB | [7:6] | Activity Mode | Current Activity State |
| LSB | [5] | Protocol Error | **Self-clearing** flag |
| LSB | [4] | Reserved | — |
| LSB | [3:0] | Pending Interrupt | Count 0-15 |
| MSB | [15:8] | Vendor Reserved | — |

**Format 2** (Defining Byte PRECR=0x91): Secondary Controller deep-sleep status.

### 4.5 RSTACT (0x2A/0x9A) Detail

**SET Defining Bytes:**

| Value | Action | Description |
|-------|--------|-------------|
| 0x00 | No Reset | Clear any pending reset action |
| 0x01 | Reset Peripheral | Reset I3C peripheral only (default action) |
| 0x02 | Reset Whole Target | Reset entire target chip |
| 0x03 | Debug Network Reset | Debug-specific reset |
| 0x04 | Virtual Target Detect | VT detection trigger |

**GET Defining Bytes:**

| Value | Returns | Default NACK Time |
|-------|---------|-------------------|
| 0x80 | Default (no prior SET) | — (Errata 19) |
| 0x81 | Peripheral reset time | 1 ms |
| 0x82 | Whole target reset time | 1 s |
| 0x83 | Debug reset time | 100 ms |

- **Default GET value:** 0x80 (per Errata 19, avoids ambiguity with 0x00)
- RSTACT action is **cleared on next START** (not Repeated START)
- **Escalation default:** 1st Target Reset = peripheral; 2nd without RSTACT/GETSTATUS = whole chip

### 4.6 GETCAPS (0x95) Detail

**Format 1** (2-4 bytes, no Defining Byte):

**GETCAP1 byte:**

| Bit | Name |
|-----|------|
| [0] | HDR-DDR supported |
| [3] | HDR-BT supported |

**GETCAP2 byte:**

| Bit | Name | Values |
|-----|------|--------|
| [7] | HDR-DDR Abort CRC | 1=Supports DDR Abort CRC |
| [6] | HDR-DDR Write Abort | 1=Supports DDR Write Abort |
| [5:4] | Group Address Caps | 0=none, 1/2/3=count supported |
| [3:0] | I3C Basic Version | 4'b0001 = v1.1.1 |

**GETCAP3 byte (optional):**

| Bit | Name |
|-----|------|
| [6] | Pending Read Notification support |
| [5] | HDR-BT CRC-32 support |
| [4] | GETSTATUS Defining Byte support |
| [3] | GETCAPS Defining Byte support (Format 2) |
| [0] | Multi-Lane (ML) support |

**Format 2** (with Defining Byte):

| Defining Byte | Name | Returns |
|---------------|------|---------|
| 0x00 | TGTCAPS | Same as Format 1 |
| 0x5A | TESTPAT | `0xA55AA55A` (4-byte test pattern) |
| 0x91 | CRCAPS | Controller Role capabilities |
| 0x93 | VTCAPS | Virtual Target capabilities |
| 0xD7 | DBGCAPS | Debug capabilities |

**CRCAPS (0x91) — Controller Role Capabilities:**

| Byte | Bit | Name |
|------|-----|------|
| CRCAP1 | [2] | ML support as Controller |
| CRCAP1 | [1] | Group Management as Controller |
| CRCAP1 | [0] | Hot-Join support as Controller |
| CRCAP2 | [3] | Delayed Handoff |
| CRCAP2 | [2] | Deep Sleep capable |
| CRCAP2 | [1] | Controller Pass-Back |
| CRCAP2 | [0] | IBI Support as Controller |

**VTCAPS (0x93) — Virtual Target Capabilities:**

| Bit | Name | Values |
|-----|------|--------|
| [5] | Shared Peripheral Detect | 1=supports detection |
| [4] | Side Effects | 1=VT operations have side effects |
| [2:0] | VT Type | 0=None, 1=Bridge+SETBRGTGT, 2=Bridge self-setup, 3=Routing+SETROUTE, 4=Mixed Debug, 5=Shared Peripheral VTs, 6=Hub |

### 4.7 GETMXDS Detail

**Format 1** (2 bytes: maxWr + maxRd):

**maxWr byte:**

| Bit | Name | Values |
|-----|------|--------|
| [3] | Defining Byte Support | 1=F2/F3 supported |
| [2:0] | Max Write Speed | 0=fSCL, 1=8M, 2=6M, 3=4M, 4=2M |

**maxRd byte:**

| Bit | Name | Values |
|-----|------|--------|
| [6] | W→R Permits STOP | — |
| [5:3] | tSCO | 0=≤8ns, 1=≤9ns, 2=≤10ns, 3=≤11ns, 4=≤12ns, 7=>12ns |
| [2:0] | Max Read Speed | Same encoding as write |

**tSCO > 12ns** → BCR[0]=1 AND maxRd[2:0]=3'b111.

**Format 2:** 5 bytes (maxWr + maxRd + 3-byte turnaround).

**Format 3 CRHDLY (0x91):** Controller Handoff Activity State — CRHDLY1[2]=Set Bus Activity State, CRHDLY1[1:0]=State.

### 4.8 ENDXFER (0x12/0x92) Detail

HDR-DDR Early Termination:

**Defining Byte 0xF7:**

| Bit | Name |
|-----|------|
| [7:6] | CRC Indicator |
| [5] | WRITE enable |
| [4] | ACK/NACK enable |

**Defining Byte 0xAA:** Confirm early termination.

### 4.9 GETXTIME Detail

Returns 4 bytes:
1. **Supported Modes** (bitfield)
2. **State** (current timing state)
3. **Frequency** (in 0.5 MHz increments; 0 = 32 KHz)
4. **Inaccuracy** (in 0.1% increments)

### 4.10 Group CCCs (MIPI Table 58)

| CCC | Group Address Support |
|-----|-----------------------|
| ENEC/DISEC | May use as multicast |
| ENTASx | May use as multicast |
| SETMWL | May use as multicast |
| SETMRL | Not recommended |
| SETDASA/SETNEWDA | **NOT supported** |
| RSTACT | Limited |
| Direct GET/Read | **NOT supported** with Group Address |

### 4.11 CCCs NOT Permitted in HDR (MIPI Table 62)

| CCC | Reason |
|-----|--------|
| RSTDAA | Requires SDR arbitration |
| ENTDAA | Requires SDR Open Drain |
| ENTTM | Test Mode requires SDR |
| ENTHDRx | Already in HDR |
| SETAASA | Requires SDR broadcast |
| SETDASA | Requires SDR addressing |
| SETNEWDA | Requires SDR addressing |
| GETPID | Requires SDR read |
| GETACCCR | Requires SDR handoff |

### 4.12 MLANE CCC (0x2D/0x9D) Detail

**Sub-Commands:**

| Value | Function |
|-------|----------|
| 0xFF | Get ML Capabilities |
| 0x7F | Reset ML Configuration |
| 0x23 | HDR-BT Frame Format |

**ML Frame Format byte (for sub-command 0x23):**

| Bit | Name | Values |
|-----|------|--------|
| [2:0] | Additional Lanes | 3'b000=Single, 3'b001=Dual, 3'b011=Quad |
| [7:3] | Data Transfer Coding | Coding number |


---

## 5. Dynamic Address Assignment (DAA)

### 5.1 Assignment Methods

| Method | CCC | Code | Type | Required? | Notes |
|--------|-----|------|------|-----------|-------|
| SETDASA | Direct | 0x87 | From known static I2C addr | Optional | Target **SHALL NACK** if DA already assigned (Errata 16-17) |
| SETAASA | Broadcast | 0x29 | All Targets use static as DA | Optional | Target **SHALL NACK** if DA already assigned (Errata 16-17) |
| ENTDAA | Broadcast | 0x07 | OD arbitration on PID+BCR+DCR | Conditional (Errata 8) | Lowest concatenated {PID,BCR,DCR} wins |
| SETNEWDA | Direct | 0x88 | Change existing DA | Required* | *Unless static-only devices |
| RSTDAA | Broadcast | 0x06 | Clear all DAs + Group Addrs | Required | Revert all Targets to unaddressed |

**Recommended Order:** SETDASA/SETAASA first → ENTDAA for remaining. This minimizes time in the slower Open Drain DAA arbitration.

### 5.2 ENTDAA Procedure (MIPI §5.1.4)

1. Controller broadcasts **7'h7E/W + 0x07** (ENTDAA CCC)
2. All unaddressed Targets respond with PID(48b) + BCR(8b) + DCR(8b) = 64 bits in **Open Drain**
3. **Arbitration:** Bit-by-bit MSB-first; device driving High-Z (1) but reading Low (0) has **lost** and stops
4. Winning Target (lowest {PID,BCR,DCR}) receives Dynamic Address from Controller
5. Repeat Sr + 7'h7E/R until NACK (no more unaddressed Targets)

**Frame Sequence (Annex A, Figure 162):**
```
S/Sr → 7'h7E(W) → ACK → ENTDAA CCC → T
  Sr → 7'h7E(R) → ACK → [PID 6B + BCR 1B + DCR 1B] → Assign DA+PAR → ACK
  [Repeat per Target...]
  Sr → 7'h7E(R) → NACK → P (exit)
```

### 5.3 PID Arbitration Details

During ENTDAA, Targets drive their PID/BCR/DCR bits one at a time in Open Drain:
- Bit value 0: Device drives SDA Low
- Bit value 1: Device releases SDA (High-Z), pulled High by bus pull-up
- A Target that drives 1 but reads back 0 has **lost arbitration** and must stop driving
- After all 64 bits, exactly one Target remains; it ACKs the assigned DA

### 5.4 DAA Error Conditions

| Error | Type | Condition | Recovery |
|-------|------|-----------|----------|
| TE3 | Target | DAA address parity error | NACK + wait for Sr + 7'h7E/R |
| TE4 | Target | Missing 7'h7E/R after Sr in DAA | NACK + wait for STOP |
| Clock stall | Target | DAA first bit | ≤15 ms max stall |

### 5.5 DWC ENTDAA Programming Flow

1. **Pre-program DAT entries** (DEV_INDEX start) with desired dynamic addresses in `DAT.DEV_DYNAMIC_ADDR[23:16]`
2. **Queue Address Assignment command:**
   - CMD_ATTR = 0x2 (Address Assignment)
   - CMD = 0x07 (ENTDAA)
   - DEV_COUNT = N (number of expected Targets)
   - DEV_INDEX = starting DAT index
3. Controller auto-captures PID/BCR/DCR in **DCT** (transient — populated by hardware)
4. **Response:** DATA_LENGTH = remaining unassigned count (0 = all assigned)
5. **After ENTDAA:** Software **must** update `DAT.IBI_WITH_DATA` from `BCR[2]`

### 5.6 DWC SETDASA Programming Flow

1. Program DAT entry with `STATIC_ADDRESS[6:0]` = Target's I2C address
2. Program `DAT.DEV_DYNAMIC_ADDR[23:16]` = desired dynamic address
3. Queue command: CMD_ATTR=0x2, CMD=0x87 (SETDASA), DEV_INDEX=target
4. Target NACKs if DA already assigned (Errata 16-17)

### 5.7 DWC SETAASA Programming Flow

1. Queue regular transfer: CMD_ATTR=0x0, CP=1, CMD=0x29 (SETAASA)
2. After broadcast completes, **manually** update all DAT entries: `DEV_DYNAMIC_ADDR` = `STATIC_ADDRESS`
3. Target NACKs if DA already assigned (Errata 16-17)


### 5.9 Mixed Bus DAA

For Mixed Fast Bus with both I2C and I3C devices:
1. I2C devices retain their static addresses (no DAA needed)
2. Program DAT with `DAT.DEVICE=1` (I2C) and static address
3. I3C devices get dynamic addresses via SETDASA/ENTDAA
4. Set `HC_CONTROL.I2C_SLAVE_PRESENT = 1` for mixed bus timing

---

## 6. In-Band Interrupt (IBI)

### 6.1 IBI Protocol (MIPI §5.1.6)

- Target drives its **Dynamic Address + RnW=1** after a **START** (not Repeated START)
- Only occurs when bus is available: **tAVAL ≥ 1.0 µs** since last STOP
- Lower address = higher priority (wins OD arbitration)
- IBI competes with Controller Role Request (CRR) and regular transfers at START

### 6.2 IBI Types

| Type | Initiator | Address | Direction | Notes |
|------|-----------|---------|-----------|-------|
| **SIR** (Slave Interrupt Request) | Target | Target DA | RnW=1 (Read) | Standard IBI |
| **MR** (Mastership Request) | Secondary Controller | SC DA | RnW=0 (Write) | Controller Role Request |
| **HJ** (Hot-Join) | New Target | 7'h02 | RnW=0 (Write) | Uses reserved address, very high priority |

### 6.3 Controller Response Options

| Response | Action | When |
|----------|--------|------|
| ACK | Read MDB if BCR[2]=1, optional payload | Normal acceptance |
| NACK | Target may retry later | Temporary rejection |
| NACK + DISEC | Disable future IBIs from this Target | Permanent rejection |

### 6.4 Mandatory Data Byte — MDB (MIPI Tables 12-13)

Present when BCR[2]=1 (IBI Payload bit). Format:
```
MDB[7:5] = Interrupt Group ID    MDB[4:0] = Group-Specific ID
```

| Group ID | Name | Specific IDs | Notes |
|----------|------|-------------|-------|
| 3'b000 | Vendor Defined | Vendor-specific | — |
| 3'b001 | I3C Working Group | 5'h0D = S0/S1 error, 5'h0E = S2/S3 error | Standard error reporting |
| 3'b010 | MIPI Groups | MIPI WG defined | — |
| 3'b011 | Reserved | — | — |
| 3'b100 | Timing Control | Timestamp IBI | Async Mode 0 |
| 3'b101 | Pending Read Notification | Pending data available | Controller **must** do Private Read after ACK |
| 3'b110-111 | Reserved | — | — |

### 6.5 Pending Read Notification (MIPI §5.1.6.2.2)

- IBI with MDB[7:5] = `3'b101`
- After accepting this IBI, Controller is **obligated** to perform a Private Read from the Target
- Used when Target has data ready but cannot push it via IBI payload
- Controller must complete the Private Read before handling other Targets

### 6.6 IBI Arbitration and Timing

- If no START from Controller within Bus Available time (tAVAL), Target may pull SDA Low
- Controller must pull SCL Low within **tCAS** of detecting SDA Low
- Multiple Targets arbitrate using their addresses (lower wins)
- Collision with CRR: Both use START; DA vs. DA+RnW determines winner

### 6.7 Timestamp IBI (Async Mode 0)

Counters:
- **T_C1:** 16-bit counter (2 bytes, LSB first in IBI payload)
- **T_C2:** 8-bit counter (1 byte in IBI payload)

Timestamp formula: `C_TS = C_REF – C_C2 × T_C1 / T_C2`

End-of-Timestamp markers:
- EOT_C1 = First SCL rising edge after IBI ACK
- EOT_C2 = First SCL rising edge after MDB T-bit

T_C2 = 0x00 means "rely on GETXTIME frequency" (no per-IBI correction). Overflow: all counter bits = 1.

### 6.8 DWC IBI Queue Format

IBI data arrives as IBI Status Descriptor (1 DW) + Data DWORDs (interleaved):

| Bit Field | Name | Description |
|-----------|------|-------------|
| [31] | IBI_STS | 0 = ACK, 1 = NACK |
| [24] | LAST_STATUS | 1 = Final chunk |
| [15:8] | IBI_ID | Slave address + RnW bit |
| [7:0] | DATA_LENGTH | Bytes in this chunk |

Data DWORDs follow the status descriptor, packed LSB-first.

### 6.9 DWC Auto-Command (HCI SIR)

When IBI MDB matches the DAT Auto-Command configuration:
```
Condition: (MDB & DAT.AUTOCMD_MASK) == DAT.AUTOCMD_VALUE
```
→ Controller automatically issues a read at `DAT.AUTOCMD_MODE` speed.

**DAT DW1 (Auto-Cmd) fields:**

| Bit | Name | Description |
|-----|------|-------------|
| [26:19] | AUTOCMD_HDR_CODE | HDR command code for auto-read |
| [18:16] | AUTOCMD_MODE | Speed mode (0=SDR0, 1=SDR1, ..., 6=HDR-DDR) |
| [15:8] | AUTOCMD_VALUE | Expected MDB value (after masking) |
| [7:0] | AUTOCMD_MASK | Mask applied to MDB before comparison |

**Auto-Command Trigger Condition:**
```
if ((MDB & AUTOCMD_MASK) == AUTOCMD_VALUE):
    issue automatic read at AUTOCMD_MODE speed
```

### 6.10 DWC IBI Critical Settings

| Setting | Value | Reason |
|---------|-------|--------|
| DAT.SIR_REJECT | 0 | Allow SIR from this target |
| DAT.IBI_WITH_DATA | BCR[2] | Must match target capability |
| IBI_STATUS_THLD | 0 | Immediate notification (recommended) |
| IBI_NOTIFY_CTRL.NOTIFY_SIR_REJECTED[3] | 1 | Generate notification on NACK |

**Warning:** If IBI queue is full when a target sends IBI, the controller will stall SCL or NACK — this can cause a bus hang. Monitor `QUEUE_STATUS_LEVEL` to prevent overflow.

### 6.11 Hot-Join

**Standard Hot-Join:**
1. Target waits for Bus Idle (tIDLE ≥ 200µs)
2. Pulls SDA Low
3. Controller issues START → Target drives 7'h02 + RnW=0
4. Controller assigns DA via ENTDAA

**Passive Method (Errata 5-7):** Target must see 7'h7E/W + STOP before emitting HJ Request.

**DWC Hot-Join Control:**
- `HC_CONTROL.HOT_JOIN_CTRL`: 0=ACK Hot-Join, 1=NACK + auto-disable via CCC
- `BUS_IDLE_TIMING[19:0]` (non-HCI register): Bus Idle threshold
- **Not compatible with Legacy I2C** — requires failsafe I/O pads


---

## 7. HDR Modes

### 7.1 HDR Common — Exit and Restart Patterns

**HDR Exit Pattern:**
- 4 SDA transitions (falling edges) while SCL remains Low
- Returns all devices to SDR mode
- **All Targets MUST implement HDR Exit Pattern Detector**, even SDR-only devices
- RTL reference code in spec (Listing 2): 4-bit shift register counting SDA falling edges while SCL Low

**HDR Restart Pattern:**
- Same as HDR Exit Pattern but followed immediately by Repeated START (Sr)
- Allows chaining HDR/SDR transfers without returning to bus idle
- Combined detector recognizes both patterns (Figure 95)

**Target Reset Pattern vs HDR Exit:**

| Pattern | SDA Transitions | Purpose |
|---------|----------------|---------|
| HDR Exit | 4 | Return to SDR mode |
| Target Reset | 14 | Reset target device |

Targets with both detectors distinguish by counting transitions.

### 7.2 HDR CCC Framing (§5.2.1.2)

**Structure:**
1. **Indicator Block:** Contains 7'h7E (broadcast address marker)
2. **Selector Block:** Contains Target Address for Direct CCCs
3. **Data Block:** CCC data payload
4. **CRC Block:** Mode-specific CRC

**CCCs Permitted in HDR (Table 61):** Subset of standard CCCs.

**CCCs NOT Permitted in HDR (Table 62):**

| CCC | Reason |
|-----|--------|
| RSTDAA | Requires SDR arbitration |
| ENTDAA | Requires SDR Open Drain |
| ENTTM | Test Mode requires SDR |
| ENTHDRx | Already in HDR |
| SETAASA | Requires SDR broadcast |
| SETDASA | Requires SDR addressing |
| SETNEWDA | Requires SDR addressing |
| GETPID | Requires SDR read |
| GETACCCR | Requires SDR handoff |

**Group Addressing in HDR:** Only Write Segments supported; all Group members must support the CCC in that HDR mode.

### 7.3 HDR-DDR Mode

#### 7.3.1 Mode Entry

1. Controller issues **ENTHDR0** (0x20) CCC in SDR mode
2. After CCC T-bit falling edge, Controller drives SDA for first DDR edge
3. Next SCL rising edge begins DDR clocking
4. Bus transitions from SDR to HDR-DDR after C9 falling edge

#### 7.3.2 Word Format (20 bits)

```
[19:18] = Preamble (2 bits)
[17:2]  = Payload (16 bits)
[1:0]   = Parity (PA1, PA0)
```

**Parity Calculation:**
```
PA1 = XOR of all odd-indexed payload bits
PA0 = XOR of all even-indexed payload bits XOR 1
```
PA0 includes the inversion (XOR with 1) for bus turnaround signaling.

**Word Types:**

| Preamble | Type | Nibble | Description |
|----------|------|--------|-------------|
| 2'b01 | Command | — | Command word |
| 2'b10 | Data (even) | — | Data at even position |
| 2'b11 | Data (odd) | — | Data at odd position |
| 2'b01 | CRC | 4'hC | CRC-5 word |
| — | Reserved | 4'hD/E/F | Must not be used |

#### 7.3.3 Preamble Context (MIPI Table 64)

| Previous State | Preamble 2'b01 | Preamble 2'b10 | Preamble 2'b11 |
|----------------|----------------|-----------------|-----------------|
| After Enter HDR | Command word | — | — |
| After Read CMD | ACK + data follows | — | NACK |
| After Read DATA | CRC follows | Controller Abort | More data follows |
| After Write CMD | ACK | — | NACK |
| After Write DATA | CRC follows | Target early END | More data follows |

#### 7.3.4 Command Word (MIPI Table 67)

16-bit payload:

```
Bit [15]    = R/W (0=Write, 1=Read)
Bits [14:8] = 7-bit Command Code
Bits [7:1]  = 7-bit Target Address
Bit [0]     = Parity Adjust (ensures PA0=1 for bus turnaround)
```

- Write command codes: 0x00–0x7F
- Read command codes: 0x80–0xFF

#### 7.3.5 CRC-5 Word

Part of the CRC Word (Preamble = 2'b01):

```
Payload[15:12] = 4'hC (CRC identifier)
Payload[11:7]  = 5-bit CRC-5
Payload[6]     = 1'b1 (setup bit)
Payload[5:0]   = Token/padding
```

#### 7.3.6 Data Rates

At 12.5 MHz SCL:
- **Raw rate:** 25 Mbps (DDR = 2× SCL frequency)
- **Effective data rate:** 20 Mbps (16 payload bits per 20-bit word)

#### 7.3.7 Flow Control

**Write ACK/NACK:**
- Target drives SDA Low on PRE0 bit → ACK (preamble = 2'b01)
- Target does not drive → NACK (preamble = 2'b11, since PA0=1'b1 always)
- PRE1 is always 1 due to PA0=1'b1 in command word

**Read ACK/NACK:**
- Same mechanism with bus turnaround after command word

**CRC Word Transitions:**
- **Write CRC:** Controller parks SDA High → HDR Restart or HDR Exit
- **Read CRC:** Target drives CRC word including setup bit, releases SDA after tSCO, Controller enables OD Pull-Up on CRC_CLK6 rising edge, drives SDA High on falling edge, then issues HDR pattern after ≥tDIG_H

#### 7.3.8 HDR-DDR CCC Framing

**Structure:**
1. **Indicator Word:** Write to 7'h7E (broadcast address marker)
2. **Command Word:** CCC code + Defining Byte
3. **Selector Word:** Target address (for Direct CCCs)
4. **Data Block:** Uses 1-Lane mode for compatibility
5. **CRC Block:** Standard HDR-DDR CRC Word

**CCC End Procedures (3 options):**
1. HDR Restart → new CCC (chain commands)
2. HDR Restart → write 7'h7E → dummy 0x1F → CRC → exit/restart
3. HDR Exit Pattern (return to SDR)

#### 7.3.9 DWC HDR-DDR Implementation

- Command: `CMD_ATTR=0x0`, `MODE=6` (HDR-DDR), `CP=1`
- **No clock stalling in HDR** — pre-load TX via `TX_START_THLD`
- `ERR_STATUS`: 0x1=CRC error, 0x2=Parity error
- Underflow/overflow → abrupt termination (no recovery, transfer lost)

### 7.4 HDR-BT Mode

#### 7.4.1 Overview (§5.2.4)

- Clock-and-Data DDR model (data on both clock edges)
- Supports Single, Dual, and Quad lane configurations
- Data rates at 12.5 MHz: **~24 Mbps (Single), ~48 Mbps (Dual), ~97 Mbps (Quad)**
- Rate multipliers vs. SDR: 2× (Single), 4× (Dual), 8× (Quad)

#### 7.4.2 Block Structure

| Block | Size | Content |
|-------|------|---------|
| Header | 7 bytes | Address + Cmd0-3 + Control + Transition |
| Data | 33 bytes | Transition_Control (1B) + Data (32B) |
| CRC | 6 bytes | Control + CRC0-3 + Transition_Verify |

**Header Block (7 bytes):**

| Byte | Name | Content |
|------|------|---------|
| 0 | Address | 7-bit Target Address + R/W bit |
| 1 | Cmd0 | Command byte 0 |
| 2 | Cmd1 | Command byte 1 |
| 3 | Cmd2 | Command byte 2 |
| 4 | Cmd3 | Command byte 3 |
| 5 | Control | R/W, CRC type, Target SCL capability, parity |
| 6 | Transition | Park1 + High-Z for accept/reject signaling |

**Control byte details:**
- Bit[0]: R/W direction
- Bit[1]: CRC type (0=CRC-16, 1=CRC-32)
- Bit[2]: Target SCL on Read (0=Target may use Data Block Delay, 1=not permitted)
- Other bits: Parity fields

**Transition_Control byte:**
- Bit[0]: Park1 (bus turnaround)
- Bit[4]: Data Block Delay (1 = delay byte, no real data in this block)
- Bit[7]: Last Data Block indicator

**Transition_Verify byte:**
- Bit[0]: Park1 — Transmitter drives SDA High
- Bit[1]: High-Z — Transmitter releases, receiver drives SDA Low to confirm CRC match

#### 7.4.3 CRC Polynomials

| CRC | Polynomial | Hex (Normal) | Hex (Reflected) | Init |
|-----|-----------|--------------|-----------------|------|
| CRC-16 | X^16 + X^15 + X^2 + 1 | 0x8005 | 0xA001 | 0xFFFF |
| CRC-32 | X^32 + X^26 + X^23 + X^22 + X^16 + X^12 + X^11 + X^10 + X^8 + X^7 + X^5 + X^4 + X^2 + X + 1 | 0x04C11DB7 | 0xEDB88320 | 0xFFFFFFFF |

**CRC Test Vectors:**

| Input Byte | CRC-16 | CRC-32 |
|------------|--------|--------|
| 0x00 | 0x40BF | 0x2DFD1072 |
| 0x91 | 0xEC7E | 0xAAF5B3A0 |
| 0xF7 | 0xC6FE | 0x0E2477CD |

- Targets that support HDR-BT **SHALL** support CRC-16 (mandatory)
- CRC-32 support is optional, advertised via GETCAPS Format 1, GETCAP3 byte bit 5

#### 7.4.4 Data Block Delay Mechanism

- Controller determines permission at transfer start: Header Block Control Bit[2]
  - Bit[2] = 0 → Target IS permitted to use Data Block Delay
  - Bit[2] = 1 → Target NOT permitted
- Target sends Transition_Control with Bit[4] = 1 to indicate a Delay byte (no full Data Block)
- Target may send up to **tBT_DBD max = 1024 Delay bytes** at each opportunity
- After max delay bytes, Target MUST either send a real Data Block or a Last Data Block
- Controller may terminate at any Delay byte using "Park1,High-Z" mechanism on SDA[0]

**Lane-Dependent Timing:**
- QUAD Lane: Target sends Bit[4] early enough for Controller to terminate immediately
- DUAL/SINGLE Lane: Bit[4] arrives later; Controller must react at start of next block

#### 7.4.5 Performance (MIPI Table 77)

| Lanes | Raw Rate | 1KB Effective | 10KB Effective |
|-------|----------|---------------|----------------|
| Single | 25 Mbps | 23.96 Mbps | 24.0 Mbps |
| Dual | 50 Mbps | 47.9 Mbps | 48.0 Mbps |
| Quad | 100 Mbps | 95.8 Mbps | 96.86 Mbps |

**Worst-case early termination delay at 12.5 MHz:**

| Lane Config | Worst Case | Average | CRC Overhead |
|-------------|-----------|---------|--------------|
| Single | 10.5 µs | 5.28 µs | 1.92 µs |
| Dual | 5.28 µs | 2.64 µs | 960 ns |
| Quad | 2.64 µs | 1.32 µs | 480 ns |

#### 7.4.6 HDR-BT CCC Framing (§5.2.4.4)

**HDR-BT CCC Indicator Block:**
- Byte 0: Broadcast Address (7'h7E)
- Byte 1: Command Code
- Byte 2: Optional Defining Byte (Direct) or data (Broadcast)
- Bytes 3-4: Optional additional data or reserved
- Byte 5 (Control): Bit[0]=0 (Write), Bit[3]=0 (start of CCC)

**HDR-BT CCC Selector Block:**
- Byte 0: Target/Group Address
- Bytes 1-4: Reserved (0x00)
- Byte 5 (Control): Bit[0]=0/1 (W/R segment), Bit[3]=1 (continuation)

**CCC End Procedures:**
1. HDR Restart → New HDR-BT CCC Indicator Block (chain CCCs)
2. HDR Restart → Read from 7'h7E Header Block → CRC Block → HDR Restart/Exit
3. HDR Exit Pattern directly

#### 7.4.7 HDR-BT Target Requirements

- **SHALL** support CRC-16
- **MAY** optionally support CRC-32 (GETCAPS GETCAP3[5])
- **SHALL** support SCL from Controller on Read
- **MAY** optionally support emitting own SCL on Read
- Target that does NOT support driving SCL for Read SHALL NACK if Header Block Bit[2]=1

#### 7.4.8 HDR-BT Write Flow Control

| Scenario | Mechanism |
|----------|----------|
| Target rejects Write | Does not ACK in Transition byte |
| Target accepts Write | ACKs in Transition byte; receives Data Blocks |
| Target terminates early | Drives SDA[0] Low in Transition_Control byte |
| CRC mismatch | Target indicates in Transition_Verify byte of CRC Block |

#### 7.4.9 HDR-BT Read Flow Control

| Scenario | Mechanism |
|----------|----------|
| Target rejects Read | Does not ACK in Transition byte |
| Target accepts Read | ACKs; sends Data Blocks |
| Controller terminates early | Drives SDA[0] Low in Transition_Control byte |
| Target uses Data Block Delay | Sends Delay bytes (Bit[4]=1 in Transition_Control) |

#### 7.4.10 Bit Packing

- Bit order: **LSb first** for all HDR-BT data
- Lane mapping for Single/Dual/Quad defined in spec tables
- **Transition bytes** use Park1/High-Z swizzle pattern for lane-dependent signaling

### 7.5 Multi-Lane Data Transfer

#### 7.5.1 Overview (§5.3)

Multi-Lane adds SDA[1], SDA[2], SDA[3] to the standard SDA[0] + SCL:
- All bus management (START, EXIT, Enter HDR, CCC, Flow Control) uses only SCL and SDA[0]
- ML transfers do NOT adversely affect non-ML Devices on the bus
- ML is available for HDR-BT Mode in I3C Basic

#### 7.5.2 Lane Configurations (MIPI Table 78)

| Additional Wires | Lane Config | Multi-Lane? | Total Wires | MLANE Data Byte |
|------------------|-------------|-------------|-------------|-----------------|
| 0 | SINGLE | No | 2 | 0x00 (default) |
| 1 | DUAL | Yes | 3 | 0x01 (Coding 0) or 0x19 (Coding 3) |
| 3 | QUAD | Yes | 5 | 0x03/0x1B/0x3B |

#### 7.5.3 HDR-BT Data Transfer Codings (MIPI Table 80)

| Coding | MLANE Data Byte | Lanes | Header Format | Requirement |
|--------|-----------------|-------|---------------|-------------|
| 0 (Compatible) | 0x00 | SINGLE | 1-Lane | Default; interoperable with all |
| 0 | 0x01 | DUAL | 1-Lane header, 2-Lane data | Compatible headers |
| 0 | 0x03 | QUAD | 1-Lane header, 4-Lane data | Compatible headers |
| 3 (Alternate) | 0x19 | DUAL | 2-Lane all blocks | Requires ALL ≥ DUAL |
| 3 | 0x1B | QUAD | 2-Lane header, 4-Lane data | Requires ALL ≥ DUAL |
| 7 (Alternate) | 0x3B | QUAD | 4-Lane all blocks | Requires ALL = QUAD |

#### 7.5.4 Interoperability (MIPI Table 81)

| Coding | Compatible With | NOT Compatible With |
|--------|----------------|---------------------|
| 0 | All HDR-BT devices | — |
| 3 | Other Coding 3 (≥2-Lane) | 1-Lane only |
| 7 | Only Coding 7 (4-Lane only) | 1-Lane, 2-Lane |

#### 7.5.5 Sticky State (§5.3.2.4.1)

- Switching from Coding 0 → Alternate enters **sticky state**
- In sticky state: **Cannot** use Direct SET CCC to any non-interoperable Coding
- **Can** use Broadcast CCC to any valid format
- **Exit sticky state:** Broadcast MLANE with Data Byte 0x00, or Sub-Command Reset ML (0x7F)
- Direct SET CCC CANNOT exit sticky state

#### 7.5.6 MLANE CCC Configuration

- Controllers SHALL use MLANE CCC (0x2D/0x9D) to configure ML-capable Devices
- ML configuration is per-I3C-Mode, per-Dynamic-Address
- Configuration persists until new MLANE CCC or ML-inclusive RESET
- Use GETCAPS Format 1 to determine ML capability before MLANE CCC
- MLANE Defining Byte for HDR-BT: **0x23** (same as ENTHDR3 CCC value)

#### 7.5.7 Group Address ML Requirements

- For I3C Basic: Only variant 2'b01 (separate ML config per Group Address)
- Controller SHALL NOT assign same Group Address to Targets of both variant 2'b00 and 2'b01
- On entering sticky state: ML config for all assigned Group Addresses changes to common ML Frame format


---

## 8. Error Detection and Recovery

### 8.1 SDR Target Error Types (MIPI Table 59)

| Error | Name | Condition | Recovery Action |
|-------|------|-----------|-----------------|
| TE0 | Invalid Broadcast Address | Single-bit error in 7'h7E detection | Activate HDR Exit Detector OR optional 60µs SCL+SDA High |
| TE1 | CCC Parity Error | Parity mismatch on CCC byte | Same as TE0 |
| TE2 | Write Data Parity Error | Parity mismatch on write data | Wait for STOP or Repeated START |
| TE3 | DAA Address Parity Error | Parity error during ENTDAA address assignment | NACK + wait for Sr + 7'h7E/R |
| TE4 | Missing 7'h7E/R after Sr in DAA | Expected broadcast read after Repeated START | NACK + wait for STOP |
| TE5 | Illegal CCC Format | CCC structure does not match expected format | NACK + wait for STOP or Repeated START |
| TE6 | Monitoring Error (Optional) | Target detects protocol violation while monitoring | Stop monitoring + wait |
| DBR | Dead Bus Recovery (Optional) | Bus inactive for 50 ms timeout | Secondary Controller may take over bus |

### 8.2 SDR Controller Error Types (MIPI Table 60)

| Error | Name | Condition | Recovery Action | Required? |
|-------|------|-----------|-----------------|-----------|
| CE0 | Illegal CCC Detected | Controller detects improper CCC response | STOP + retry | Required |
| CE1 | Monitoring Error | Controller detects protocol violation | — | Optional |
| CE2 | No ACK to 7'h7E | No Target ACKs broadcast address | HDR Exit Pattern + STOP | Required |
| CE3 | Failed Controller Handoff | New Controller does not take over | Test new controller ≥100µs then SDA Low test | Required |

### 8.3 Error Escalation Path

```
Retry Transfer
    ↓ (still fails)
GETSTATUS (check Protocol Error bit [LSB bit 5])
    ↓ (still fails)
CE2: HDR Exit Pattern + STOP
    ↓ (still fails)
Slow SCL (reduced frequency)
    ↓ (still fails)
Target Reset Pattern (14 SDA transitions)
    ↓ (still fails)
Out of scope (platform-level recovery)
```

- **BCR[3] (Offline Capable)** affects escalation: offline-capable Targets may need longer recovery windows

### 8.4 Stuck SDA Recovery

| Bus Mode | Method | Details |
|----------|--------|---------|
| I2C | 9 SCL clock pulses | Standard I2C recovery |
| I3C SDR | Up to 8 SCL clocks | Watch T-bit; when T=1 (end), abort transfer. Hold SCL for 150µs if needed |
| HDR-DDR | §5.2.2.4 specific | Mode-specific recovery procedure |

### 8.5 Controller Crash Recovery

1. **Determine SDA state:** Weak pull-down test, or drive SDA Low to claim bus
2. **Issue HDR Exit Pattern** (ensures all devices return to SDR)
3. **Issue RSTDAA** (reset all Dynamic Addresses)
4. **If SDA stuck Low:**
   - Drive SCL Low to check for IBI/CRR/Hot-Join
   - Or emit **19+ SCL clocks** to flush any stuck transfer

### 8.6 DWC ERR_STATUS Codes (Response Descriptor)

| Code | Error | Causes HALT? | Recovery |
|------|-------|-------------|----------|
| 0x0 | Success | No | — |
| 0x1 | CRC Error (HDR-DDR) | No | Retry transfer |
| 0x2 | Parity Error (HDR-DDR) | No | Retry transfer |
| 0x3 | Frame Error (HDR-TS) | No | Retry transfer |
| 0x4 | Broadcast NACK | **Yes** | Drain responses → reset queues → RESUME |
| 0x5 | Address NACK | No | Check address/DAT programming |
| 0x6 | Overflow/Underflow | Depends | Reset FIFOs, adjust TX_START_THLD |
| 0x8 | Aborted (SW or HW) | **Yes** | Drain responses → reset queues → RESUME |
| 0x9 | I2C Write NACK | No | Check I2C slave |

### 8.7 DWC HALT State Recovery

When `ERR_STATUS` = 0x4 (Broadcast NACK) or 0x8 (Aborted), the controller enters HALT state:

**Recovery Procedure:**
1. Read `RESPONSE_QUEUE_PORT` to get the error response
2. Read any pending RX data from `RX_TX_DATA_PORT`
3. Reset queues: `RESET_CONTROL` bits — CMD_QUEUE_RST[1], RESP_QUEUE_RST[2], TX_FIFO_RST[3], RX_FIFO_RST[4]
4. Write `HC_CONTROL.RESUME` = 1 (bit 30)
5. Verify via `PRESENT_STATE_DEBUG` that CM_TFR_ST_STATUS exits 0x13 (HALT)


### 8.8 DWC Bus Recovery

`BUS_RESET_TYPE` bits [30:29] in a special command:

| Value | Type | Action |
|-------|------|--------|
| 2'b00 | HDR-EXIT | Send HDR Exit Pattern |
| 2'b11 | SCL Low Reset | SCL Low for recovery |

Set `BUS_RESET[31]=1` → auto-clears when done.



---

## 9. Timing Specifications

### 9.1 Legacy I2C Timing (MIPI Table 85)

| Parameter | Symbol | Fm (400 kHz) | Fm+ (1 MHz) | Unit |
|-----------|--------|-------------|-------------|------|
| SCL Clock Frequency | fSCL | 0 – 0.4 | 0 – 1.0 | MHz |
| Setup Time Repeated START | tSU_STA | ≥600 | ≥260 | ns |
| Hold Time (Repeated) START | tHD_STA | ≥600 | ≥260 | ns |
| SCL Low Period | tLOW | ≥1300 | ≥500 | ns |
| SCL High Period | tHIGH | ≥600 | ≥260 | ns |
| Data Setup Time | tSU_DAT | ≥100 | ≥50 | ns |
| SCL Rise Time | trCL | 20 – 300 | 20 – 120 | ns |
| SCL Fall Time | tfCL | 20×(VDD/5.5V) – 300 | 20×(VDD/5.5V) – 120 | ns |
| SDA Rise Time | trDA | 20 – 300 | 20 – 120 | ns |
| SDA Fall Time | tfDA | 20×(VDD/5.5V) – 300 | 20×(VDD/5.5V) – 120 | ns |
| Setup Time STOP | tSU_STO | ≥600 | ≥260 | ns |
| Bus Free (STOP→START) | tBUF | ≥1.3 µs | ≥0.5 µs | µs |
| Spike Filter Width | tSPIKE | 0 – 50 | 0 – 50 | ns |

### 9.2 I3C Open Drain Timing (MIPI Table 86)

| Parameter | Symbol | Min | Max | Unit | Notes |
|-----------|--------|-----|-----|------|-------|
| SCL Low Period | tLOW_OD | 200 | — | ns | Enough for pull-up to pull SDA High |
| Digital Low Period | tDIG_OD_L | tLOW_OD_min + tfDA_OD_min | — | ns | |
| SCL High (1st Broadcast) | tHIGH_INIT | — | 200 | ns | First addr after bus init; disables I2C spike filter |
| SCL High (Mixed Bus) | tHIGH | — | 41 | ns | Keeps I2C devices from seeing I3C traffic |
| SCL High (Pure Bus) | tHIGH | 24 | — | ns | Same as Push-Pull min |
| SDA Fall Time | tfDA_OD | — | 12 | ns | |
| SDA Data Setup (OD) | tSU_OD | 3 | — | ns | |
| Clock After START | tCAS | 38.4 | — | ns | For ENTASx states: 1µs/100µs/2ms/50ms max |
| Clock Before STOP | tCBP | tCAS_min/2 | — | ns | |
| Controller Handoff Overlap | tCRHP | tDIG_OD_L_min | — | ns | |
| **Bus Available** | **tAVAL** | **1 µs** | — | **µs** | On Mixed Bus with Fm: 300ns shorter than tBUF |
| **Bus Idle** | **tIDLE** | **200 µs** | — | **µs** | Hot-Join permitted after this |
| New Controller Lock | tNEWCRLock | tAVAL_min | — | µs | |

### 9.3 I3C Push-Pull Timing — SDR/ML/HDR-DDR/HDR-BT (MIPI Table 87)

| Parameter | Symbol | Min | Typ | Max | Unit | Notes |
|-----------|--------|-----|-----|-----|------|-------|
| **SCL Clock Frequency** | **fSCL** | **0.01** | **12.5** | **12.9** | **MHz** | fSCL = 1/(tDIG_L + tDIG_H) |
| SCL Low Period | tLOW | 24 | — | — | ns | |
| Digital Low Period | tDIG_L | 32 | — | — | ns | Allows 40/60 duty cycle at 12.5 MHz |
| SCL High (Mixed Bus) | tHIGH_MIXED | 24 | — | — | ns | |
| Digital High (Mixed) | tDIG_H_MIXED | 32 | — | 45 | ns | Constrained so I2C devices don't see I3C |
| SCL High (Pure Bus) | tHIGH | 24 | — | — | ns | |
| Digital High (Pure) | tDIG_H | 32 | — | — | ns | |
| **Target Clock-to-Data** | **tSCO** | — | — | **12** | **ns** | BCR[0]=1 if > 12ns; supports GETMXDS |
| SCL Rise Time | tCR | — | — | 150e6×(1/fSCL), capped at 60 | ns | |
| SCL Fall Time | tCF | — | — | 150e6×(1/fSCL), capped at 60 | ns | |
| SDA Hold (Controller PP) | tHD_PP | tCR+3 and tCF+3 | — | — | ns | Both edges for DDR |
| SDA Hold (Target PP) | tHD_PP | 0 | — | — | ns | |
| SDA Setup (PP) | tSU_PP | 3 | — | — | ns | |
| Clock After Repeated START | tCASr | tCAS_min/2 | — | — | ns | |
| Clock Before Repeated START | tCBSr | tCAS_min/2 | — | — | ns | |
| **Bus Capacitive Load** | **Cb** | — | — | **50** | **pF** | Max for peak speed operation |
| **HDR-BT SCL Frequency** | **tBT_FREQ** | 0.1 | 12.5 | 12.9 | MHz | |
| **HDR-BT Handoff Delay** | **tBT_HO** | — | — | **10** | **µs** | Controller-to-Target handoff timeout |
| **HDR-BT Delay Bytes** | **tBT_DBD** | — | — | **1024** | **bytes** | Max Delay bytes per opportunity |

### 9.4 Mixed Fast Bus Duty Cycle Technique

Short SCL High (e.g., 40ns) + long SCL Low (e.g., 280ns) = 3.125 MHz effective. I2C spike filter (50ns) suppresses the short High pulse — I2C device sees no activity. This allows I3C PP transfers to proceed without disturbing legacy I2C devices.

### 9.5 SDA Mode Switching During Frame (MIPI Tables 88-90)

**New Frame Without Contention on A6 (Table 88):**

| Phase | START | Addr[6] | Addr[5:0]+RnW | ACK | Data+T | STOP |
|-------|-------|---------|---------------|-----|--------|------|
| SDA Mode | OD | OD | **PP** | OD | PP | PP |

**New Frame With Contention on A6 (Table 89):**

| Phase | START | Addr[6] | Addr[5:0]+RnW | ACK | Data+T | STOP |
|-------|-------|---------|---------------|-----|--------|------|
| SDA Mode | OD | OD | **OD** | OD | PP | PP |

**Continuation with Repeated START (Table 90):**

| Phase | Sr | Addr/RnW | ACK | Data+T | STOP |
|-------|-----|----------|-----|--------|------|
| SDA Mode | PP | PP | OD | PP | PP |


---

## 10. Electrical Specifications

### 10.1 Standard DC I/O Characteristics (MIPI Table 82)

| Parameter | Symbol | VDD < 1.4V | VDD ≥ 1.4V | Unit | Notes |
|-----------|--------|-----------|-----------|------|-------|
| Operating Voltage | VDD | 1.10/1.20/1.30 | 1.65/1.80/1.95 or 2.97/3.30/3.63 | V | 1.2V, 1.8V, 3.3V nominal |
| Low-Level Input | VIL | -0.1×VDD to 0.3×VDD | same | V | Includes normal undershoot |
| High-Level Input | VIH | 0.7×VDD to 1.1×VDD | same | V | Includes normal overshoot |
| Hysteresis | Vhys | ≥0.1×VDD | same | V | Schmitt trigger required |
| Output Low | VOL | ≤0.18V @ IOL=2mA | ≤0.27V @ IOL=3mA | V | |
| Output High (PP) | VOH | ≥VDD-0.18V @ IOH=-2mA | ≥VDD-0.27V @ IOH=-3mA | V | Push-Pull only |
| Input Current | Ii | ±5 µA | ±10 µA | µA | < 1.8V / ≥ 1.8V |
| Pin Capacitance | Ci | ≤5 pF | ≤10 pF | pF | < 1.8V / ≥ 1.8V |
| Cap Mismatch | ΔC | ≤1.5 pF (Ci≤5pF) | ≤3 pF (Ci>5pF) | pF | Between SDA and SCL |
| Pull-Up Resistance | Rp | (VDD-VOL)/IOL min | tr/(0.8473×Cb) max | Ω | |

**Pull-Up Calculation:** For tr=120ns (Errata 21), Cb=50pF: Rp_max ≈ 120ns / (0.8473 × 50pF) ≈ 2833 Ω.

**Critical Rules:**
- Pull-Up for Open Drain **SHALL be switched off** during Push-Pull operation
- Open Drain never occurs on SCL in I3C (only on SDA during OD phases)
- A weak Pull-Up or **High-Keeper** is separately sized for Controller handoff and HDR-BT "Park1,High-Z"
- Drive strength must be rated at **twice** the indicated IOL/IOH current (peak current at max voltage difference)

### 10.2 Low Voltage / High Capacitive Load I/O (MIPI Table 83 — DDR5 SPD)

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Operating Voltage | VDD | 0.95 / 1.0 / 1.25 | V |
| Low-Level Input | VIL | -0.3 to 0.3 | V |
| High-Level Input | VIH | 0.7 to 1.25 | V |
| Hysteresis | Vhys | 0.1×VDD to 0.4×VDD | V |
| Output Low | VOL | ≤0.3V @ IOL=4mA | V |
| Output High (PP) | VOH | ≥0.75V @ IOH=-3mA | V |
| Pin Capacitance | Ci | ≤5 pF | pF |
| Cap Mismatch | ΔC | ≤1.5 pF | pF |
| Reference Pull-Up | Rp | (VDD-VOL)/4mA min, tr/(0.8473×Cb) max | Ω |

Reference: tr=100ns, Cb=100pF, VDD=1V.


---

## 11. DWC Implementation Details

### 11.1 Controller Architecture


**HCI Compliance:**

### 11.2 BAR Memory Layout (Per Controller = 8K)

```
Controller BAR (8K total)
├── Bus #0 Region (at offset 0x000)
│   ├── HCI Registers          0x000 – 0x07F
│   ├── DAT (8 entries)        0x080 – 0x0BF  (16 DW)
│   ├── DCT (8 entries)        0x100 – 0x17F  (32 DW, transient)
│   ├── Ring Header 0 (RH0)    0x180
│   ├── Ring Header 1 (RH1)    0x1180
│   └── Ring Headers Base       0x3C0
│
├── Bus #1 Region (at offset 0x400)
│   ├── HCI Registers          0x400 – 0x47F
│   ├── DAT (8 entries)        0x480 – 0x4BF
│   ├── DCT (8 entries)        0x500 – 0x57F
│   ├── Ring Header 0 (RH0)    0x480
│   ├── Ring Header 1 (RH1)    0x1580
│   └── Ring Headers Base       0x7C0
│
├── Convergence Layer          0x2B4 – 0x2CC (Bus #0)
│                              0x6B4 – 0x6CC (Bus #1)
│
└── iDMA Registers             Shared between both buses
```

### 11.3 HCI Core Registers (Per Bus)

| Register | Offset (Bus 0) | Offset (Bus 1) | Key Bits |
|----------|----------------|-----------------|----------|
| HCI_VERSION | 0x000 | 0x400 | HCI spec version |
| HC_CONTROL | 0x004 | 0x404 | BUS_ENABLE[31], RESUME[30], ABORT[29], HOT_JOIN_CTRL[8], I2C_SLAVE_PRESENT[7], IBA_INCLUDE[0] |
| MASTER_DEVICE_ADDR | 0x008 | 0x408 | DYNAMIC_ADDR_VALID[31], DYNAMIC_ADDR[22:16] |
| HC_CAPABILITIES | 0x00C | 0x40C | HDR_DDR_EN[6], NON_CURRENT_MASTER_CAP[5], AUTO_COMMAND[3] |
| RESET_CONTROL | 0x010 | 0x410 | IBI_QUEUE_RST[5], RX_FIFO_RST[4], TX_FIFO_RST[3], RESP_QUEUE_RST[2], CMD_QUEUE_RST[1], SOFT_RST[0] |
| PRESENT_STATE | 0x014 | 0x414 | CURRENT_MASTER[2] |
| INTR_STATUS | 0x020 | 0x420 | R/W1C; HC_INTERNAL_ERR_STAT[10] |
| INTR_STATUS_ENABLE | 0x024 | 0x424 | Enable status updates |
| INTR_SIGNAL_ENABLE | 0x028 | 0x428 | Enable interrupt pin |
| INTR_FORCE | 0x02C | 0x42C | Force interrupt (debug) |
| DAT_SECTION_OFFSET | 0x030 | 0x430 | DAT base and size |
| DCT_SECTION_OFFSET | 0x034 | 0x434 | DCT base and size |
| RING_HEADERS_SECTION_OFFSET | 0x038 | 0x438 | Ring headers base |
| PIO_SECTION_OFFSET | 0x03C | 0x43C | PIO base (debug only) |
| EXT_CAPS_SECTION_OFFSET | 0x040 | 0x440 | Extended capabilities |
| IBI_NOTIFY_CTRL | 0x058 | 0x458 | NOTIFY_SIR_REJECTED[3], NOTIFY_HJ_REJECTED[0] |
| DEV_CTX_BASE_LO | 0x060 | 0x460 | Device context base low |
| DEV_CTX_BASE_HI | 0x064 | 0x464 | Device context base high |

### 11.4 Interrupt Registers

**Level 1 (INTR_STATUS at offset 0x020/0x420):**

| Bit | Name | Description |
|-----|------|-------------|
| 0 | HC_INTERNAL_ERR | Unrecoverable controller error |
| 3 | TRANSFER_ABORT_STAT | Abort completed |
| 5 | RESP_READY_STAT | Response available in queue |
| 8 | IBI_THLD_STAT | IBI queue threshold reached |
| 9 | CMD_QUEUE_READY_STAT | Command queue ready |
| 10 | HC_WARN | Warning (non-fatal) |
| 11 | HC_SEQ_CANCEL | Sequence cancelled |

**Level 2 (PIO_INTR_STATUS at offset 0x320/0x720):**

| Bit | Name | Type |
|-----|------|------|
| 9 | TRANSFER_ERR_STAT | R/W1C |
| 5 | TRANSFER_ABORT_STAT | R/W1C |
| 4 | RESP_READY_STAT | Auto-clear on read |
| 3 | CMD_QUEUE_READY_STAT | Auto-clear on read |
| 2 | IBI_STATUS_THLD_STAT | Auto-clear on read |
| 1 | RX_THLD_STAT | Auto-clear on read |
| 0 | TX_THLD_STAT | Auto-clear on read |

### 11.5 SCL Timing Registers (ExtCap base 0x100+)

| Register | Offset | Fields |
|----------|--------|--------|
| SCL_I3C_OD_TIMING | 0x114 | HCNT[23:16], LCNT[7:0] |
| SCL_I3C_PP_TIMING | 0x118 | HCNT[23:16], LCNT[7:0] |
| SCL_I2C_FM_TIMING | 0x11C | HCNT[23:16], LCNT[15:0] |
| SCL_I2C_FMP_TIMING | 0x120 | HCNT[23:16], LCNT[7:0] |
| SCL_EXT_LCNT_TIMING | 0x128 | EXT_LCNT_4[31:24] / EXT_LCNT_3[23:16] / EXT_LCNT_2[15:8] / EXT_LCNT_1[7:0] (SDR1-4) |
| SDA_HOLD_SWITCH_DLY | 0x130 | SDA_TX_HOLD[18:16], OD↔PP switch delays |
| BUS_FREE_TIMING | 0x134 | MST_FREE[15:0] |

**SCL Frequency Formulas:**
```
SDR:  f_SCL = 1 / ((HCNT + LCNT) × t_core_clk)
I2C:  f_SCL = 1 / ((FM_HCNT + FM_LCNT) × t_core_clk)
SDA:  t_HD_DAT = SDA_TX_HOLD × t_core_clk
T-bit: t_low_T = (PP_LCNT + EXT_TERMN_LCNT) × t_core_clk  [SDR0]
       t_low_T = (EXT_LCNT_n + EXT_TERMN_LCNT) × t_core_clk  [SDR1-4]
```

**Timing Register Map:**

| Speed | HCNT Source | LCNT Source | Target Frequency |
|-------|-------------|-------------|------------------|
| I3C OD | OD_TIMING[23:16] | OD_TIMING[7:0] | ~1.5 MHz |
| I3C PP (SDR0) | PP_TIMING[23:16] | PP_TIMING[7:0] | 12.5 MHz |
| I3C SDR1-4 | PP_TIMING[23:16] | EXT_LCNT[7:0]..[31:24] | 8/6/4/2 MHz |
| I2C FM | FM_TIMING[23:16] | FM_TIMING[15:0] | 400 kHz |
| I2C FM+ | FMP_TIMING[23:16] | FMP_TIMING[7:0] | 1 MHz |

**SDA Hold & Switch Delay:**

| Parameter | Register | Range |
|-----------|----------|-------|
| SDA TX Hold | SDA_HOLD[18:16] | 1-7 core_clk |
| OD→PP Switch | SDA_HOLD[2:0] | 0-4 core_clk |
| PP→OD Switch | SDA_HOLD[10:8] | 0-4 core_clk |

**Bus Timing:**

| Parameter | Register |
|-----------|----------|
| Bus Free | BUS_FREE_TIMING[15:0] |
| Bus Available | BUS_FREE_AVAIL_TIMING[31:16] (non-HCI) |
| Bus Idle | BUS_IDLE_TIMING[19:0] (non-HCI) |
| SCL Low Timeout | SCL_LOW_MST_EXT_TIMEOUT |

### 11.6 PIO Registers (offset 0x300+)

| Register | Offset | Access | Description |
|----------|--------|--------|-------------|
| COMMAND_QUEUE_PORT | 0x300 | W | Write command descriptors |
| RESPONSE_QUEUE_PORT | 0x304 | R | Read response descriptors |
| RX_TX_DATA_PORT | 0x308 | R/W | Data buffer port |
| IBI_PORT | 0x30C | R | IBI status descriptors |
| QUEUE_THLD_CTRL | 0x310 | R/W | Queue threshold configuration |
| DATA_BUFFER_THLD_CTRL | 0x314 | R/W | Data buffer thresholds |
| PIO_INTR_STATUS | 0x320 | R/W1C | PIO interrupt status |

**Threshold Encoding:** 000=1, 001=4, 010=8, 011=16, 100=32, 101=64, 110=128, 111=256 DWORDs.

**Threshold Configuration:**

| Register | Field | Purpose |
|----------|-------|---------|
| QUEUE_THLD_CTRL | CMD_EMPTY_BUF_THLD[7:0] | CMD_QUEUE_READY when free ≥ N |
| QUEUE_THLD_CTRL | RESP_BUF_THLD[15:8] | RESP_READY when count ≥ N+1 |
| QUEUE_THLD_CTRL | IBI_STATUS_THLD[31:24] | IBI threshold (set 0 for immediate) |
| DATA_BUFFER_THLD_CTRL | TX_START_THLD | Start TX when loaded ≥ value (**critical for HDR — no stalling**) |

### 11.7 DAT — Device Address Table (base 0x080/0x480)

8 entries per bus, 2 DWORDs per entry:

**DW0 Layout:**

| Bit | Name | Description |
|-----|------|-------------|
| [31] | DEVICE | 0=I3C, 1=I2C |
| [30:29] | DEV_NACK_RETRY_CNT | NACK retry count |
| [23:16] | DEV_DYNAMIC_ADDR | Dynamic address (I3C) |
| [14] | MR_REJECT | 1=Reject Mastership Request |
| [13] | SIR_REJECT | 1=Reject SIR (IBI) |
| [12] | IBI_WITH_DATA | 1=MDB follows IBI (must match BCR[2]) |
| [6:0] | STATIC_ADDRESS | Static address (I2C/SETDASA) |

**DW1 Layout (Auto-Command):**

| Bit | Name | Description |
|-----|------|-------------|
| [26:19] | AUTOCMD_HDR_CODE | HDR command code for auto-read |
| [18:16] | AUTOCMD_MODE | Speed mode (0=SDR0, ..., 6=HDR-DDR) |
| [15:8] | AUTOCMD_VALUE | Expected MDB value (after masking) |
| [7:0] | AUTOCMD_MASK | Mask applied to MDB before comparison |

### 11.8 DCT — Device Characteristics Table (base 0x100/0x500)

8 entries per bus, 4 DWORDs per entry. **Transient** — populated by hardware during ENTDAA.

| DWORD | Content |
|-------|---------|
| DW0 | PID[47:16] |
| DW1 | PID[15:0] |
| DW2 | BCR[15:8] + DCR[7:0] |
| DW3 | Dynamic Address (assigned) |

### 11.9 Command Descriptor (2 DWORDs)

**CMD_ATTR[2:0] Types:**

| Attr | Type | Use |
|------|------|-----|
| 0x0 | Regular Transfer | Private R/W, CCC, HDR |
| 0x1 | Immediate Data | ≤4 bytes inline, **Write-only** |
| 0x2 | Address Assignment | ENTDAA/SETDASA |
| 0x3 | Combo Transfer | Write offset + Read (**SDR only**) |
| 0x7 | Internal Control | Non-bus operations |

**DWORD0 Bit Fields:**

| Bit | Name | Description |
|-----|------|-------------|
| [31] | TOC | Terminate On Complete (1=allow BUS_ENABLE clear/IBI check after this cmd) |
| [30] | ROC | Response On Complete (1=generate response) — **must be 1 for DMA** |
| [29] | RNW | Read/Not-Write (1=Read, 0=Write) |
| [28:26] | MODE | Speed mode (0=SDR0, ..., 6=HDR-DDR) |
| [25] | DBP | Defining Byte Present |
| [19:16] | DEV_INDEX | DAT entry index (**4-bit, NOT 5-bit**) |
| [15] | CP | Command Present (1=CCC, 0=Private) |
| [14:7] | CMD | Command code (CCC code when CP=1) |
| [6:3] | TID | Transaction ID (0-15) |
| [2:0] | CMD_ATTR | Command attribute type |

**DWORD1 Bit Fields:**

| Bit | Name | Description |
|-----|------|-------------|
| [31:16] | DATA_LENGTH | Data length in bytes |
| [15:8] | DEF_BYTE | Defining byte (when DBP=1) |

### 11.10 Transfer Type Decode

| CP | RNW | DAT.DEVICE | Type |
|----|-----|------------|------|
| 0 | 0 | 0 | I3C Private Write |
| 0 | 1 | 0 | I3C Private Read |
| 0 | 0 | 1 | I2C Write |
| 0 | 1 | 1 | I2C Read |
| 1 | x | x | CCC (CMD[14]: 0=Broadcast, 1=Directed) |

### 11.11 MODE/SPEED Encoding

| Value | I3C Mode | I2C Mode | Frequency |
|-------|----------|----------|-----------|
| 0 | SDR0 | FM | 12.5 MHz / 400 kHz |
| 1 | SDR1 | FM+ | 8 MHz / 1 MHz |
| 2 | SDR2 | SS | 6 MHz / 100 kHz |
| 3 | SDR3 | — | 4 MHz |
| 4 | SDR4 | — | 2 MHz |
| 5 | HDR-TS | — | variable |
| 6 | HDR-DDR | — | variable |

### 11.12 Response Descriptor

| Bit | Name | Description |
|-----|------|-------------|
| [31:28] | ERR_STATUS | Error code (see §8.6) |
| [27:24] | TID | Transaction ID (matches command) |
| [15:0] | DATA_LENGTH | Actual data length transferred |

### 11.13 Queue / FIFO Sizes

| Queue | Depth | Unit | Notes |
|-------|-------|------|-------|
| TX Command Queue | 64 | DW | Shared across all transfers |
| RX Response Queue | 64 | DW | |
| TX Data Queue | 64 | DW | |
| RX Data Queue | 64 | DW | |
| IBI Queue | 64 | DW | In-band interrupt status |
| iDMA TX FIFO | 32 | DW | Per DMA channel |
| iDMA RX FIFO | 32 | DW | Per DMA channel |

### 11.14 DMA Architecture

- **External DMA** (DW_ahb_dmac) via SDMA handshake for TX/RX FIFOs only
- **Command/Response/IBI queues** always use PIO (even in DMA mode)
- **ROC must be 1** for all DMA mode commands

DWC HCI Deviations from MIPI HCI Spec


|---|----------|---------------------|--------|
| 1 | DEV_INDEX = bits [20:16] (5-bit) | DEV_INDEX = bits [19:16] (4-bit) | Max 8 devices per bus |
| 2 | CHUNK_SIZE up to 256B | CHUNK_SIZE max 128B | Must chunk large transfers |
| 3 | PIO mode mandatory | PIO debug only (GPPRVRW8[0]=1) | DMA required for production |
| 4 | Ring size 1 valid | Ring size 1 INVALID | Must use 0 or 2–255 |
| 5 | Immediate data R/W | Immediate data WRITE only | No immediate reads |
| 6 | All combo types | SDR WR+WR or SDR WR+RD only | No HDR combo |
| 7 | HDR-TSL/TSP optional | Not implemented | DDR is the only HDR mode |

### 11.16 Enable / Disable / Abort

**Enable:** `HC_CONTROL.BUS_ENABLE = 1` (bit 31).

**Disable:** Clear `BUS_ENABLE` → poll until reads back 0 (waits for TOC=1 commands + IBI to complete).

**Abort:** Set `ABORT` (bit 29) → STOP after byte boundary → `TRANSFER_ABORT_STAT` set → HALT → flush queues → `RESUME=1` (bit 30).

**Soft Reset:** `RESET_CONTROL.SOFT_RST = 1` — resets buffers/queues, NOT config registers, no bus activity generated.

### 11.17 DWC Debug — PRESENT_STATE_DEBUG (offset 0x14C)

**Most important debug register.** Shows real-time FSM state.

**MASTER_IDLE[28]:** 1 = all queues empty + IDLE.

**CM_TFR_ST_STATUS[21:16] — Transfer Sub-State:**

| Value | State | Description |
|-------|-------|-------------|
| 0x00 | IDLE | No activity |
| 0x01 | START | Sending START condition |
| 0x05 | BCAST_WRITE | Sending 7'h7E/W broadcast |
| 0x07 | DAA | Dynamic Address Assignment |
| 0x0B | CCC_BYTE | Sending CCC byte |
| 0x0C | HDR_CMD | HDR command word |
| 0x0D | WRITE_DATA | Writing data bytes |
| 0x0E | READ_DATA | Reading data bytes |
| 0x11 | HDR_DDR_CRC | HDR-DDR CRC phase |
| 0x12 | CLOCK_EXT | Clock stalling (buffer empty/full) |
| 0x13 | **HALT** | **Controller halted — requires RESUME** |

**CM_TFR_STATUS[13:8] — Transfer Type:**

| Value | Type |
|-------|------|
| 0x01-0x03 | CCC (Broadcast / Directed Write / Directed Read) |
| 0x04-0x05 | ENTDAA / SETDASA |
| 0x06-0x07 | I3C SDR Write / Read |
| 0x08-0x09 | I2C Write / Read |
| 0x0C-0x0D | HDR-DDR Write / Read |
| 0x0F | **HALTED** |

**Bus Line Status:**
- `SCL_LINE[0]`: Real-time SCL level
- `SDA_LINE[1]`: Real-time SDA level

### 11.18 Debug Scenarios

| Scenario | First Check | Key Register |
|----------|-------------|--------------|
| Not responding | BUS_ENABLE=1? HALT state? | HC_CONTROL, PRESENT_STATE_DEBUG |
| Transfer timeout | CLOCK_EXT? Buffer empty/full? | CM_TFR_ST_STATUS, DATA_BUFFER_STATUS |
| DAA failure | ERR_STATUS 0x4/0x5? | RESPONSE_QUEUE_PORT, DAT, DCT |
| IBI missing | SIR_REJECT=0? IBI_WITH_DATA? Queue full? | DAT, QUEUE_STATUS_LEVEL |
| HDR failure | TX pre-loaded? CRC error? | TX_START_THLD, ERR_STATUS |

### 11.19 Minimum Register Dump for Debug

```
HC_CONTROL                    — Enable/Abort/Resume state
PRESENT_STATE_DEBUG           — FSM state + bus lines
RESPONSE_QUEUE_PORT           — Error status
QUEUE_STATUS_LEVEL            — Queue fill levels
DATA_BUFFER_STATUS_LEVEL      — Buffer levels
PIO_INTR_STATUS               — Pending interrupts
```



---

## 12. Multi-Master / Secondary Controller

### 12.1 Controller Role Request

- Only **one Active Controller** at a time on the I3C bus
- Secondary Controller requests mastership via DA + RnW=0 (like IBI but Write direction)
- Lower Dynamic Address = higher priority

### 12.2 Handoff Procedure

1. Current Active Controller: `GETSTATUS` of new controller
2. `DISEC` (disable events on bus)
3. Reconfigure ML if needed
4. Set Activity State
5. Resync: `DEFTGTS`, `DEFGRPA` (inform Secondary Controllers of device table)
6. `GETACCCR` + STOP (hand off)
7. New Active Controller: START within **100 µs** (tNEWCRLock)

### 12.3 CE3: Failed Controller Handoff Recovery

1. Wait at least **100 µs** (tNEWCRLock)
2. Test new controller by pulling SDA Low
3. If SDA does not go Low → new controller is not driving → reclaim bus
4. If SDA goes Low → new controller may still be initializing → wait more



---

## 13. Target Reset

### 13.1 Target Reset Pattern (§5.1.10)

**Pattern Definition:**
- **14 SDA transitions** while SCL remains Low
- SDA ends in **High** state
- Followed by **Repeated START (Sr)** + **STOP**
- Triggers reset action configured by RSTACT CCC

**Distinguished from HDR Exit Pattern:**

| Pattern | SDA Transitions | SCL State | Purpose |
|---------|----------------|-----------|---------|
| HDR Exit | 4 | Low | Return to SDR mode |
| Target Reset | 14 | Low | Reset target device |

Targets with both detectors distinguish by counting transitions.

### 13.2 Timing Requirements (Errata 20)

- **tDIG_H minimum** applies to ALL transitions on both SDA and SCL during the reset pattern
- Each SDA transition must meet minimum timing for reliable detection by all targets on the bus

### 13.3 RSTACT CCC Configuration

**SET Defining Bytes:**

| Value | Action | Description |
|-------|--------|-------------|
| 0x00 | No Reset Action | Disarm reset |
| 0x01 | Reset Peripheral Only | Default reset action |
| 0x02 | Reset Whole Target | Full device reset |
| 0x03 | Debug Network Reset | Debug infrastructure reset |
| 0x04 | Virtual Target Detect | VT detection |

**GET Defining Bytes:**

| Value | Returns | Default NACK Time |
|-------|---------|-------------------|
| 0x81 | Time to reset peripheral | 1 ms |
| 0x82 | Time to reset whole target | 1 s |
| 0x83 | Time for debug reset | 100 ms |

**Default GET value (no prior SET):** **0x80** (per Errata 19, avoids ambiguity with 0x00 "No Reset").

### 13.4 Reset Escalation

1. **First Target Reset Pattern** (no prior RSTACT): Reset I3C Peripheral only
2. **Second pattern** without intervening RSTACT or GETSTATUS: Reset whole chip
3. **RSTACT is cleared on next START** (not Repeated START)

### 13.5 Validation Implications

- Must verify 14 SDA transitions are correctly generated
- Must verify tDIG_H minimum on all transitions (Errata 20)
- Must verify escalation sequence (1st → peripheral, 2nd → whole chip)
- Must verify RSTACT clearing on START vs. Sr
- Must verify Target correctly distinguishes from HDR Exit (4 transitions)


---


---

## 15. Validation Checklist

### A. Bus Initialization and DAA

- [ ] First 7'h7E broadcast uses OD (FM/FM+) timing (Errata 3)
- [ ] SETDASA/SETAASA NACKs on duplicate DA (Errata 16-17)
- [ ] ENTDAA selects lowest PID+BCR+DCR in OD arbitration
- [ ] ENTDAA: DCT entries populated correctly (PID/BCR/DCR/DA)
- [ ] Passive Hot-Join waits for 7'h7E/W + STOP (Errata 5-7)
- [ ] DAT.IBI_WITH_DATA updated from BCR[2] after ENTDAA
- [ ] Reserved addresses (Table 8) not assigned
- [ ] IBI-capable targets get addresses in 7'h03–7'h3F range
- [ ] Non-IBI targets get addresses in 7'h40–7'h7B range
- [ ] Maximum 8 targets per bus (DAT size limitation)
- [ ] Mixed bus: I2C static + I3C dynamic addressing

### B. SDR Protocol

- [ ] Write T-bit = XOR(Data[7:0], 1) (odd parity)
- [ ] Read T=0 terminates, T=1 continues
- [ ] Target abandons read after 100µs SCL timeout
- [ ] Clock stalling ≤100µs (ACK/Parity/T-bit), ≤15ms (DAA), 15ms absolute
- [ ] OD→PP and PP→OD SDA mode transitions correct per frame type (Tables 88-90)
- [ ] ACK handoff: OD → release → PP transition correct
- [ ] Activity states: ENTAS0=1µs, ENTAS1=100µs, ENTAS2=2ms, ENTAS3=50ms

### C. CCC Compliance

- [ ] RSTACT default GET returns 0x80 (Errata 19)
- [ ] SETMWL/SETMRL minimum is Target-defined (Errata 9-14)
- [ ] GETCAPS GETCAP2[3:0]=0001 for v1.1.1
- [ ] GETMXDS reports correct tSCO and speed limits
- [ ] GETSTATUS Protocol Error bit [5] is self-clearing
- [ ] GETPID returns 6 bytes MSB-first (48-bit PID)
- [ ] ENEC/DISEC correctly enable/disable events
- [ ] RSTDAA clears all Dynamic Addresses + Group Addresses
- [ ] ENDXFER for HDR-DDR early termination

### D. IBI and Events

- [ ] IBI uses START (not Repeated START)
- [ ] MDB format correct per group ID (Table 12-13)
- [ ] Pending Read Notification (MDB[7:5]=101) triggers Private Read
- [ ] tAVAL ≥ 1µs before Target-initiated events
- [ ] DWC: DAT.SIR_REJECT=0, IBI_WITH_DATA=BCR[2]
- [ ] DWC: IBI_STATUS_THLD=0 for immediate notification
- [ ] DWC: Auto-Command mask/value matching verified
- [ ] Hot-Join: standard method (tIDLE ≥ 200µs) and passive method

### E. Error Handling

- [ ] TE0-TE6 Target error responses verified (Table 59)
- [ ] CE0-CE3 Controller error handling verified (Table 60)
- [ ] Error escalation: retry → GETSTATUS → HDR Exit → slow SCL → Target Reset
- [ ] Stuck SDA recovery (SDR: 8 clocks + 150µs; I2C: 9 clocks)
- [ ] Controller crash recovery (HDR Exit → RSTDAA → 19+ SCL if stuck)
- [ ] DWC: HALT recovery (read response → flush queues → RESUME bit 30)
- [ ] DWC: ERR_STATUS 0x4 (Broadcast NACK) correctly triggers HALT
- [ ] DWC: ERR_STATUS 0x8 (Aborted) correctly triggers HALT
- [ ] BCR[3] (Offline Capable) considered in escalation path

### F. Target Reset

- [ ] 14 SDA transitions while SCL Low (distinct from HDR Exit = 4)
- [ ] SDA ends High after pattern
- [ ] Followed by Sr + STOP
- [ ] tDIG_H min on all transitions (Errata 20)
- [ ] Escalation: 1st=peripheral, 2nd without RSTACT/GETSTATUS=whole chip
- [ ] RSTACT cleared on next START (not Sr)
- [ ] RSTACT GET default returns 0x80 (Errata 19)

### G. HDR-DDR

- [ ] 20-bit word: 2 preamble + 16 payload + 2 parity
- [ ] Preamble context correct per Table 64
- [ ] CRC-5 word: 4'hC identifier + 5-bit CRC + setup bit
- [ ] ACK/NACK via preamble (01=ACK, 11=NACK)
- [ ] PA1=XOR(odd bits), PA0=XOR(even bits, 1)
- [ ] Command word: [15]=R/W, [14:8]=CC, [7:1]=addr, [0]=PA adjust
- [ ] CCC framing: Indicator+Command+Selector words
- [ ] DWC: MODE=6, CMD_ATTR=0x0, CP=1
- [ ] DWC: TX pre-loaded (TX_START_THLD), no clock stalling in HDR
- [ ] DWC: ERR_STATUS 0x1=CRC, 0x2=Parity
- [ ] Data rates: 25 Mbps raw, 20 Mbps effective at 12.5 MHz

### H. HDR-BT

- [ ] Header (7B) + Data (33B) + CRC (6B) block structure
- [ ] CRC-16: polynomial 0x8005, init 0xFFFF (mandatory)
- [ ] CRC-32: polynomial 0x04C11DB7, init 0xFFFFFFFF (optional, GETCAP3[5])
- [ ] CRC test vectors verified (0x00→0x40BF, 0x91→0xEC7E, 0xF7→0xC6FE)
- [ ] Transition_Verify CRC match confirmation
- [ ] Data Block Delay (max 1024 bytes, Controller Bit[2] controls permission)
- [ ] Write flow: reject/accept/terminate/CRC-mismatch
- [ ] Read flow: reject/accept/Controller terminate/Delay
- [ ] LSb-first bit packing
- [ ] HDR-BT CCC framing: Indicator Block + Selector Block

### I. Multi-Lane

- [ ] Default SINGLE Lane (0x00) after reset
- [ ] MLANE CCC (Defining Byte 0x23) configures HDR-BT ML
- [ ] Coding 0: all devices; Coding 3: ≥DUAL; Coding 7: QUAD only
- [ ] Sticky state: enter via Direct SET from Coding 0, exit only via Broadcast
- [ ] Group Address ML variant 2'b01 for I3C Basic
- [ ] GETCAPS used to determine ML capability before MLANE CCC

### J. Electrical

- [ ] VIL ≤ 0.3×VDD, VIH ≥ 0.7×VDD
- [ ] Vhys ≥ 0.1×VDD
- [ ] VOL ≤ 0.18V (VDD<1.4V) or ≤ 0.27V (VDD≥1.4V) at rated IOL
- [ ] VOH ≥ VDD-0.18V (VDD<1.4V) or ≥ VDD-0.27V (VDD≥1.4V) at rated IOH
- [ ] Ci ≤ 5pF (<1.8V) or ≤ 10pF (≥1.8V)
- [ ] ΔC (SDA/SCL mismatch) ≤ 1.5pF (Ci≤5pF) or ≤ 3pF (Ci>5pF)
- [ ] Pull-up Rp in range: (VDD-VOL)/IOL ≤ Rp ≤ tr/(0.8473×Cb)
- [ ] Pull-up OFF during Push-Pull
- [ ] High-Keeper on both SDA and SCL
- [ ] Pull-up rise time ≤ 120ns (Errata 21)

### K. Timing

- [ ] fSCL ≤ 12.9 MHz (Push-Pull)
- [ ] tDIG_L ≥ 32ns, tDIG_H ≥ 32ns (Push-Pull)
- [ ] tDIG_H_MIXED ≤ 45ns (Mixed bus — hides PP from I2C spike filter)
- [ ] tSCO ≤ 12ns (Target clock-to-data)
- [ ] tLOW_OD ≥ 200ns (Open Drain)
- [ ] tHIGH_INIT ≤ 200ns (first broadcast)
- [ ] tCR/tCF ≤ 60ns (capped)
- [ ] Cb ≤ 50pF
- [ ] tAVAL ≥ 1µs (Bus Available)
- [ ] tIDLE ≥ 200µs (Bus Idle)
- [ ] tBUF ≥ 1.3µs (Fm) / ≥ 0.5µs (Fm+)
- [ ] tBT_HO ≤ 10µs (HDR-BT handoff)
- [ ] tBT_DBD ≤ 1024 bytes (HDR-BT delay)
- [ ] Activity States: ENTAS0=1µs, ENTAS1=100µs, ENTAS2=2ms, ENTAS3=50ms
- [ ] DWC: SCL timing registers (OD, PP, FM, FMP) match target frequencies
- [ ] DWC: SDA hold and switch delays configured

### L. DWC IP Specific

- [ ] HC_CONTROL.BUS_ENABLE volatile — poll until 0 on disable
- [ ] SOFT_RST resets buffers, not config registers
- [ ] ROC=1 for all DMA mode commands
- [ ] TX_START_THLD sufficient for HDR (no clock stalling)
- [ ] Interrupt thresholds configured (IBI_STATUS_THLD=0 recommended)
- [ ] DEV_INDEX is 4 bits [19:16] (max 8 devices per bus)
- [ ] CHUNK_SIZE max 128B (not 256B per HCI spec)
- [ ] Ring sizes: 0 or 2-255 (size=1 INVALID)
- [ ] Immediate data: write-only, SDR-only
- [ ] Combo transfers: SDR WR+WR or SDR WR+RD only
- [ ] PRESENT_STATE_DEBUG accessible for debug

### M. Power Management


### N. Multi-Bus


---

