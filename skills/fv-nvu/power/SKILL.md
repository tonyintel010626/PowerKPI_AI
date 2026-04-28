name: fv-nvu/power
description: NVU power management -- power states, clock/power gating, voltage domains, CRPM, PMC integration, SRAM PM, wake, and Chassis 2.2 services

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`) — william.willy.chin@intel.com, Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.
>
> **⚠️ NEVER trust AI 100%.** This skill file is a productivity aid, not a replacement for engineering judgment. AI can hallucinate, confuse similar IPs (e.g., NVU vs NVL/NPU6), or present outdated information as current. **When in doubt, verify with the owner/co-owner or check the authoritative HAS document directly.** For CoDeSign-based HAS verification, see the FV-NVU agent definition (`FV-NVU.md`).

# NVU Power Management

> **SAFETY**: Do NOT modify power-related registers (CRPM, SSCR, PGCB, PMC sideband) or trigger power-state transitions without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.

## Overview

The NVU supports multiple power states designed to minimize energy consumption while maintaining always-on visual sensing capability. Power management spans voltage domains, clock gating (block-level and trunk-level), IP-accessible power gating (IPAPG) with SRAM retention, PGCB-based power-domain control, and integration with the SoC PMC via Chassis 2.2 sideband messaging.

Key topics:

- **Power States**: D0i0 (Active), D0i1 (Idle / Trunk Clock Gating), D0i2 (Deep Idle / IPAPG + Retention), Lid Closed (Shutdown)
- **Voltage Domains**: VNN, gated/ungated power domains, VNN resource own req/ack
- **Clocking**: 10 clock domains (func 400/200MHz, pixel 562.5MHz, bridge 200/100MHz, xtal 38.4MHz, pgcb 2.56MHz, rtc 32.768KHz, JTAG 50MHz, MIPI RX 312.5/357.1MHz), clock gating and switching
- **Power Gating**: 3 PGCB domains (NVU_MAIN, NVU_USB, NVU_MIPI) with FET_EN/ACK interfaces
- **SRAM Power Management**: 3584 KB total SRAM (7 slices × 512 KB) with per-slice deep-sleep, retention, shutdown via SSCR registers
- **PMC Integration**: Chassis 2.2 resources, services (vision/telemetry), QoS_DMD RLTR, PRNDE, PME
- **Wake**: PME for host wake, GPIO wake, wake event logs and masks


## Power States

The NVU defines four power states (HAS Section 13.2, NVU Power States Table):

| Power State | Description | Main PD | USB/MIPI PD | SRAM | Clocks | Lowest SoC State |
|-------------|-------------|---------|-------------|------|--------|-------------------|
| **D0i0** (Active) | Multiple sub-states: MIPI RAW sensing, USB RAW sensing, Algo Processing, FW Paging, IPC to ISH | ON | ON (active sensor) | ON | FUNC clock ON | S0 |
| **D0i1** (Idle / FUNC TCG) | Trunk-level clock gating; NVU idle but retains state | ON | OFF | ON | All OFF except XTAL, PGCB + RTC | S0i2.0 |
| **D0i2** (Deep Idle / IPAPG+RET) | IP-accessible power gating with SRAM retention | OFF | OFF | RETENTION | PGCB CG, only RTC clock ON | S0i2.0 |
| **Lid Closed** (Shutdown) | NVU not operational; VNN de-asserted to allow VNN removal (lid closed) | OFF | OFF | RETENTION | All OFF | S0i2.2 |

> **HAS constraints (Section 13)**: NVU supports **D3 Hot only** — D3 Cold is NOT supported. There is **no D0i3** state — **Reason** (HAS Feedback [2678]): after BUP loading, `RS3_WR_DISABLE` is set, making the IMR (Isolated Memory Region) **not writable**; there is no provision for FW context save to DRAM, which D0i3 would require. **RTD3 is not supported per HAS** (however, BIOS Req doc Section 6.8 confirms RTD3 D3hot IS supported via ACPI with `_S0W=0x03` and PEP constraint=D3hot — see bios/SKILL.md). The deepest runtime idle state is D0i2 (IPAPG with SRAM retention). D3 is only entered/exited via host driver request through PMC.
>
> **ROM_WAIT_D3 soft-strap** (`oob_fuse[158]` → `NVU_SOFT_STRAP1[30]`, register offset `0x0662[30]`, default=0): Controls IOSF2AXI bridge D3 bypass. 0=normal D3 entry, 1=bypass IOSF2AXI bridge D3 (survivability/debug). See platform/SKILL.md § Soft-Strap Register Map for full strap details.

### Detailed Power State Matrix (from NVU IP HAS Excel — PM Sheet)

> Source: `NVU_IP_HAS_excel.xlsx` → PM sheet. This is the authoritative per-domain ON/OFF/On-Demand matrix for all NVU power states.

#### Table A: Power Domains, Logical Resources & SoC State

| Power State | Sub-State | Main PD | USB PD | MIPI PD | SRAM | VNN | Peer Fabric | DDR | PSF | SBR | SoC State |
|-------------|-----------|---------|--------|---------|------|-----|-------------|-----|-----|-----|-----------|
| **D0i0** (Active) | MIPI RAW — LP Sensing (IPU D3) | ON | OFF | ON | ON | ON | On Demand | OFF | OFF | OFF | S0 |
| | MIPI RAW — Sensing + IPU Streaming | ON | ON | ON | ON | ON | On Demand | OFF | OFF | On Demand | S0 |
| | USB RAW — LP Sensing (IPU D3) | ON | ON | ON | ON | ON | On Demand | OFF | OFF | OFF | S0 |
| | USB RAW — Sensing + IPU Streaming | ON | ON | ON | ON | ON | On Demand | OFF | OFF | On Demand | S0 |
| | USB Legacy — LP Sensing (IPU D3) | ON | ON | OFF | ON | ON | On Demand | OFF | OFF | OFF | S0 |
| | USB Legacy — Sensing + IPU Streaming | ON | ON | ON | ON | ON | On Demand | OFF | OFF | On Demand | S0 |
| | Algo Processing — LP Sensing | ON | OFF | OFF | ON | ON | OFF | OFF | OFF | OFF | S0 |
| | Algo Processing — Sensing + Host Streaming | ON | ON | ON | ON | ON | On Demand | OFF | OFF | On Demand | S0 |
| | FW Paging | ON | OFF | OFF | ON | ON | ON | ON | ON | OFF | S0 |
| | IPC to ISH (Algo results) | ON | OFF | OFF | ON | ON | OFF | OFF | OFF | ON | S0 |
| **D0i1** (Idle) | FUNC TCG | ON | OFF | OFF | ON | ON | OFF | OFF | OFF | OFF | S0i2.0 |
| **D0i2** (Deep Idle) | IPAPG + RET | OFF | OFF | OFF | RET | ON | OFF | OFF | OFF | OFF | S0i2.0 |
| **Lid Closed** | Shutdown | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | S0i2.2 |

#### Table B: Clock Domains per Power State

| Power State | Sub-State | PRIM | SIDE | FUNC | PIXEL | CDPHY | XTAL | PGCB | RTC |
|-------------|-----------|------|------|------|-------|-------|------|------|-----|
| **D0i0** (Active) | MIPI RAW — LP Sensing (IPU D3) | On Demand | OFF | ON | OFF | ON | OFF | ON | ON |
| | MIPI RAW — Sensing + IPU Streaming | On Demand | On Demand | ON | OFF | ON | OFF | ON | ON |
| | USB RAW — LP Sensing (IPU D3) | On Demand | OFF | ON | OFF | OFF | ON | ON | ON |
| | USB RAW — Sensing + IPU Streaming | On Demand | On Demand | ON | OFF | OFF | ON | ON | ON |
| | USB Legacy — LP Sensing (IPU D3) | On Demand | OFF | ON | OFF | OFF | ON | ON | ON |
| | USB Legacy — Sensing + IPU Streaming | On Demand | On Demand | ON | OFF | OFF | ON | ON | ON |
| | Algo Processing — LP Sensing | OFF | OFF | ON | OFF | OFF | OFF | ON | ON |
| | Algo Processing — Sensing + Host Streaming | On Demand | On Demand | ON | OFF | OFF | ON | ON | ON |
| | FW Paging | On Demand | OFF | ON | OFF | OFF | OFF | ON | ON |
| | IPC to ISH (Algo results) | OFF | ON | ON | OFF | OFF | OFF | ON | ON |
| **D0i1** (Idle) | FUNC TCG | OFF | OFF | OFF | OFF | OFF | OFF | ON | ON |
| **D0i2** (Deep Idle) | IPAPG + RET | OFF | OFF | OFF | OFF | OFF | OFF | OFF | ON |
| **Lid Closed** | Shutdown | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF |

#### Key Observations from PM Matrix

- **VNN stays ON** in D0i0 and D0i1; still ON in D0i2 (IPAPG retains VNN for SRAM retention); OFF only in Lid Closed
- **PGCB + RTC** are the last clocks to turn off — active through D0i1, RTC alone in D0i2, both OFF only in Lid Closed
- **FUNC clock** is always ON during any D0i0 sub-state (the main NVU processing clock)
- **CDPHY vs XTAL**: MIPI sub-states use CDPHY (no XTAL); USB sub-states use XTAL (no CDPHY) — mutually exclusive camera clock paths
- **PEER FABRIC + DDR**: Only active during FW Paging (SMMU DRAM access); On Demand during host streaming; Peer Fabric On Demand and DDR OFF during LP sensing sub-states
- **SIDE clock**: Only active when sideband IPC is needed (IPC to ISH, host streaming sub-states)
- **D0i2 SRAM = RET**: SRAM slices enter retention mode (not OFF) — context preserved for fast resume

### D0i1 Entry/Exit (Section 13.7.4)

- **Entry**: FW enters IDLE loop, prepares for low-power entry. HW performs trunk-level clock gating (FUNC clock gated, PGCB and RTC remain active).
- **Exit**: Wake event triggers clock un-gating; FW resumes from idle loop.

#### D0i1 HW-Level Entry Flow (from HAS SVG: D0i1 Entry diagram — 9 steps)

| Step | Actor | Action | Signal |
|------|-------|--------|--------|
| 1 | FW | Enters IDLE loop, executes SLEEP (WFI) | `sys_sleep_r` asserted |
| 2 | HW | Asserts quiescence request to bridge | `QREQN` → 0 (active low) |
| 3 | Bridge | Checks for in-flight IOSF transactions | — |
| 4 | Bridge | Accepts quiescence (no pending traffic) | `QACCEPT` → 1 |
| 5 | HW | Gates AXI fabric clocks | AXI clock OFF |
| 6 | HW | De-asserts functional clock request | `nvu_func_clk_req` → 0 |
| 7 | PMC | Acknowledges func clock release | `nvu_func_clk_ack` → 0 |
| 8 | HW | TCG complete — D0i1 entered | Only PGCB + RTC clocks active |
| 9 | — | **Abort path**: If `BRIDGE_WAKE` asserts during TCG, abort D0i1 entry and resume | `BRIDGE_WAKE` → 1 aborts TCG |

> **TCG Abort**: If a sideband message or PME arrives during the TCG sequence (`BRIDGE_WAKE` assertion), the entire D0i1 entry is aborted — HW re-asserts `nvu_func_clk_req`, un-gates AXI clocks, and de-asserts `QREQN`. FW resumes from IDLE loop without entering D0i1.

#### D0i1 Bridge Quiescence (QREQN/QACCEPT/QDENY) — Integration HAS v0.8, Section 13

During D0i1 entry, the NVU bridge performs a quiescence handshake to ensure no in-flight IOSF transactions:

1. HW asserts `QREQN` (quiescence request, active low) to bridge
2. Bridge checks for in-flight completions/requests on both primary and sideband
3. If no pending traffic: bridge asserts `QACCEPT` (quiescence accepted)
4. If traffic pending: bridge asserts `QDENY` — D0i1 entry is deferred until traffic drains
5. On `QACCEPT`: HW proceeds to gate functional clocks (trunk-level CG)
6. On D0i1 exit: HW de-asserts `QREQN`, bridge de-asserts `QACCEPT`, clocks un-gate

### D0i2 Entry/Exit (Section 13.7.5)

- **Entry**: FW prepares context save, HW performs PGCB clock gating (mandatory for IPAPG) + SRAM retention + IPAPG (Main PD powered off). PA memories must be in ungated or gated domain under retention.
- **Exit**: PMC restores power, SRAM exits retention, FW resumes from saved context.

#### D0i2 + IPAPG Detailed Flow (Integration HAS v0.8, Section 13)

**Entry**:

1. FW saves all context to SRAM retention memory
2. FW configures SRAM slice retention settings (DSOVREN/DSOVRVAL per slice)
3. FW programs WDT disable and peripheral quiescence
4. FW disables all interrupts
5. **FW executes NOP race-guard sequence** — drains in-flight interrupts before clock freeze (detail from HAS §13.7.5.1.1 D0i2 entry flow diagram; exact count per PDF figure)
6. FW executes SLEEP instruction (WFI equivalent)
7. HW detects idle — asserts `QREQN` to bridge
8. Bridge quiescence completes (`QACCEPT`)
9. HW gates AXI fabric clocks
10. HW gates all peripheral HW clocks
11. HW sends `func_clk_req=0` (release functional clock)
12. PMC acknowledges `func_clk_ack=0`
13. HW sends `PGCB_clk_req=0` (release PGCB clock)
14. PMC acknowledges `PGCB_clk_ack=0`
15. IPAPG entry — Main PD powered off, VNN_GATED de-asserted

**Exit**:

1. Wake source triggers (timer expiry, external IPC doorbell, or host command)
2. PMC re-asserts `pgcb_clk_req=1` → PMC provides `pgcb_clk_ack=1`
3. PMC re-asserts `func_clk_req=1` → PMC provides `func_clk_ack=1`
4. HW un-gates all clocks
5. IPAPG exit — Main PD powered on, VNN_GATED re-asserted
6. HW applies functional reset to VPX core
7. ROM re-executes from reset vector
8. ROM checks power status saved in CRPM registers to determine wake type (cold boot vs D0i2 exit)
9. ROM branches to AON task located in AONRF memory (in the un-gated power domain) for D0i2 resume
10. AON task restores VPX core registers and stack contents from AON memory (AON task handles both saving and restoring VPX core registers and stack contents to/from AON memory during D0i2/IPAPG entry/exit), and restores per-slice SRAM settings: clears `DSOVREN`/`DSOVRVAL` to exit retention mode
11. FW resumes from saved context

> **NOP Race Guard**: The NOP instructions between interrupt disable and SLEEP are mandatory. Without this guard, an interrupt arriving after the disable but before the SLEEP could be lost, causing the core to enter IPAPG with a pending unhandled interrupt. The NOPs provide sufficient pipeline drain time for any in-flight interrupt to be delivered to the core before clock freeze.

### Lid Closed / Lid Open Transitions

- **Lid Closed**: Full shutdown -- all power domains OFF (MAIN PD: IPAPG, USB and MIPI PD: PG), SRAM in retention by FW, VNN removal supported. Triggered via `vision_service` (Chassis 2.2 service).
- **Lid Open**: PME wake triggers NVU re-initialization. Transition from Lid Closed to Lid Open generates a PME event (Section 13.8).

#### Lid Closed Detailed Flow (from HAS SVG: Lid Closed/Open diagram — 53 steps)

The Lid Closed transition involves coordinated sequencing between FW, HW, and PMC:

**Phase 1 — FW Shutdown (Steps 1–17)**:

| Step | Actor | Action | Signal/Register |
|------|-------|--------|----------------|
| 1 | PMC | Sends SleepLevelReq with `VISION_SERVICE=0` | `IOSF_SB::Sleep_Level_Req` |
| 2 | FW | Receives VISION_SERVICE IRQ | VPX2 interrupt |
| 3 | FW | Sends `IPC::Lid-Closed=1` to App Manager | Internal IPC |
| 4 | FW | App Manager stops camera pipeline | Camera Config Service |
| 5 | FW | Powers off camera PHY (MIPI or USB) | PHY shutdown |
| 6 | FW | Releases all IOs (PHY sharing, GPIOs) | `NVU_Claim=0` |
| 7 | FW | Sends shutdown notification to ISH | Cross-core IPC |
| 8 | FW | Saves persistent state to AONRF | AONRF write |
| 9 | FW | Configures SRAM for shutdown (SRAM slices enter shutdown mode via `cr_shutdown_en` default value of 1) | SSCR registers |
| 10 | FW | Disables all interrupts | VPX2 IRQ disable |
| 11 | FW | Executes 50 NOP race-guard | Pipeline drain |
| 12 | FW | Executes SLEEP (WFI) | `sys_sleep_r` |

**Phase 2 — HW D0i2 IPAPG Entry (Steps 13–26)**:

| Step | Actor | Action | Signal |
|------|-------|--------|--------|
| 13 | HW | Asserts `QREQN` to bridge | Bridge quiescence |
| 14 | Bridge | Returns `QACCEPT` | No in-flight transactions |
| 15 | HW | Gates AXI clocks | AXI clock OFF |
| 16 | HW | De-asserts `nvu_func_clk_req` | `nvu_func_clk_req` → 0 |
| 17 | PMC | Acknowledges | `nvu_func_clk_ack` → 0 |
| 18 | HW | De-asserts `nvu_pgcb_clk_req` | `nvu_pgcb_clk_req` → 0 |
| 19 | PMC | Acknowledges | `nvu_pgcb_clk_ack` → 0 |
| 20 | HW | IPAPG entry criteria met: `HAE=1` + `SLEEP_EN=1` | PMCTL register |
| 21 | HW | Asserts PGCB power gate request | `nvu_pmc_pg_req_b` → 0 |
| 22 | PMC | Disables power FET | `pmc_nvu_fet_en_b` → 0 |
| 23 | HW | Acknowledges FET disable | `nvu_pmc_fet_en_ack_b` → 0 |
| 24 | PMC | Acknowledges PG complete | `pmc_nvu_pg_ack_b` → 0 |

**Phase 3 — VNN Removal (Steps 25–40)**:

| Step | Actor | Action | Signal |
|------|-------|--------|--------|
| 25 | HW | De-asserts VNN own request | `nvu_pmc_vnn_own_req` → 0 |
| 26 | PMC | Acknowledges VNN release | `nvu_pmc_vnn_own_ack` → 0 |
| 27 | PMC | Asserts VNN isolation | `vnn_isol_en_b` → 0 |
| 28 | PMC | Removes VNN supply | VNN rail OFF |

**Phase 4 — PMC Save/Restore Sequence (Steps 29–53)**:

| Step | Actor | Action | Signal/Register |
|------|-------|--------|----------------|
| 29 | PMC | Initiates save sequence | `pmc_nvu_restore_b` → 0 |
| 30 | PMC | Saves IPC ESE, ISH IPC Channels, IOSF2AXI PCI Config, Bridge Private Registers | SB write sequence |
| 31 | PMC | Sets `SRM_DONE` flag | Save complete |
| 32 | PMC | Polls `APB::CRPM.SR_IN_PRG` until clear | Verify save committed |
| 33–53 | PMC | Additional PMC-internal save steps | (PMC-internal) |

> **VISION_SERVICE softstrap**: `NVU_WAIT_FW_LOAD_VISION_SERVICE` — when set, PMC delays sending `VISION_SERVICE` SleepLevelReq until after FW is fully loaded. This prevents the Lid Closed flow from racing with FW boot.

#### Lid Open / PMC Restore Flow (from HAS SVG: 34 steps)

| Phase | Steps | Actor | Action | Signal |
|-------|-------|-------|--------|--------|
| VNN Restore | 1–6 | PMC | Restores VNN rail, de-asserts isolation | `vnn_isol_en_b` → 1, VNN ON |
| Power Restore | 7–12 | PMC | Re-enables power FET, restores PGCB | `pmc_nvu_fet_en_b` → 1, `pmc_nvu_pg_ack_b` → 1 |
| Clock Restore | 13–18 | PMC | Re-enables clocks (pgcb → func → prim) | `nvu_pgcb_clk_ack` → 1, `nvu_func_clk_ack` → 1 |
| Config Restore | 19–24 | PMC | Restores IOSF2AXI bridge saved config | `pmc_nvu_restore_b` → 1 |
| FW Boot | 25–30 | HW/FW | ROM re-executes, checks wake type, cold boots | `PMU_PWR_ST_REG` check |
| Service Notify | 31–34 | PMC | Sends `VISION_SERVICE=1` (Lid Open) | `IOSF_SB::Sleep_Level_Req`, `nvu_vnn_rown_req/ack` |

> **Cold boot on Lid Open**: Unlike D0i2 exit (which resumes from saved context), Lid Open triggers a **full cold boot** — ROM executes from reset vector, performs ECC scrub on all SRAM slices, loads BUP and main FW. SRAM contents are lost (shutdown mode, not retention).

#### Boot with Lid Closed Flow (from HAS SVG: 83 steps)

When the platform boots with lid already closed, a special sequence occurs:

1. **Host IP Bringup** (Steps 1–20): PMC brings up NVU HW, provides clocks and power
2. **IOSF2AXI Init** (Steps 21–30): Bridge configuration, `HAE=1`, `PMCTL=0x3F`
3. **Telemetry Service** (Steps 31–35): PMC sends `TELEMETRY_SERVICE` via SleepLevelReq (SLR)
4. **ROM Wait** (Steps 36–45): ROM checks `NVU_ROM_WAIT_D3` softstrap
   - If `NVU_ROM_WAIT_D3=0`: Normal D3 entry
   - If `NVU_ROM_WAIT_D3=1`: Bypass IOSF2AXI bridge D3 (survivability)
5. **FW Load Wait** (Steps 46–55): Checks `NVU_WAIT_FW_LOAD_VISION_SERVICE` softstrap
6. **Lid Closed Entry** (Steps 56–83): Executes the full Lid Closed shutdown sequence (Phase 1–4 above)

> **Key**: `IPAPG criteria = HAE=1 + SLEEP_EN=1` — both Host Access Enable and Sleep Enable must be set in PMCTL for IPAPG to trigger. BIOS must program these during init (see bios/SKILL.md REQ2).

#### Lid-Closed Standby High-Level FW Flow (from FAS SVG: 17 steps)

| Step | Actor | Action |
|------|-------|--------|
| 1 | App Manager | Receives Lid-Closed notification |
| 2 | Camera Config | Stops camera pipeline |
| 3 | PM Driver | Initiates power-off sequence |
| 4 | PM Driver | Sends stop to ISH (cross-core IPC) |
| 5 | Camera Config | Powers off camera sensor |
| 6 | PM Driver | Releases IOs (PHY, GPIOs) |
| 7 | PM Driver | Sets `NVU_Claim=0` (releases PHY ownership) |
| 8 | App Manager | Initiates shutdown |
| 9 | FW | Enters D0i2 IPAPG |
| 10 | PMC | VNN de-assertion |


## Voltage Domains (Section 6)

The NVU operates across multiple voltage domains:

| Domain | Voltage | Description |
|--------|---------|-------------|
| **VNN** | — | Ungated rail supplied by SoC |
| **VNN_GATED** | — | Gated VNN domain; power switch on VNNAON generates VNN_GATED supply |
| **VNNAON** | — | Always-on VNN; powers SRAM memories and gated VNN power switch |

### Power Domain Architecture

```
  SoC VNN Rail
  │
  ├── VNN Ungated ──► PGCB clk domain, RTC domain, always-on logic
  │
  └── VNNAON ──┬──► SRAM memories
               │
               └──► Power Switch ──► VNN_GATED ──► NVU Main PD, USB PD, MIPI PD
```

- Resource ownership concept is supported via resource_own_req/resource_own_ack mechanism for resource ownership hand-off with PMC.
- During Lid Closed state, NVU must support complete VNN removal.


## Clocking (Section 5)

### Clock Domains

The NVU uses 10 clock domains (7 from SIP HAS + 3 from Integration HAS):

| Clock | Frequency | Purpose | Available in D0i1 | Available in D0i2 |
|-------|-----------|---------|--------------------|--------------------|
| **nvu_func_clk** | 400MHz (default) / 200MHz (low-power) | Main functional clock for VPX2, NPX, SRAM, fabric | No (TCG) | No |
| **nvu_pixel_clk** | 562.5MHz | MJPEG decode | No | No |
| **nvu_br_prim_clk** | 200MHz | IOSF Bridge Primary interface | No | No |
| **nvu_br_side_clk** | 100MHz | IOSF Bridge Sideband interface | No | No |
| **nvu_xtal_clk** | 38.4MHz | Hammock Harbor reference clock | No | No |
| **nvu_pgcb_clk** | 2.56MHz | PGCB / CDC / PCGL logic | Yes | No |
| **nvu_rtc_clk** | 32KHz | RTC timestamps (no clk_req/ack) | Yes | Yes |
| **nvu_vpx_jtag_tck** | 20MHz | VPX2 JTAG test clock (Integration HAS) | No | No |
| **nvu_rxwordclkhs** | 312.5MHz | MIPI PHY RX word clock (high-speed, Integration HAS) | No | No |
| **nvu_rxbyteclkhs** | 357.1MHz | MIPI PHY RX byte clock (high-speed, Integration HAS) | No | No |

### Clock Partitions (from HAS SVG: NVU_Clocking diagram)

The NVU clocking architecture is organized into 10 partitions with clock handshake interfaces:

| Partition | Clock Domain(s) | Frequency | Purpose |
|-----------|----------------|-----------|---------|
| **PAR_MAIN** | FUNC clock | 400/200 MHz | Main processing (VPX2, NPX6, SRAM, DMA, NOC) |
| **PAR_VPX** | VPX2 core clock | 400/200 MHz | VPX2 DSP execution |
| **PAR_NPX** | NPX core clock | 400/200 MHz | NPX NNA inference |
| **PAR_SRAM** | SRAM clock | 400/200 MHz | SRAM slice access |
| **PAR_MIPI** | CDPHY RX clocks | 312.5/357.1 MHz | MIPI camera PHY |
| **PAR_USB** | XTAL + Pixel | 38.4 MHz / Pixel | USB camera + MJPEG decode |
| **PGCU** | PGCB clock | 2.56 MHz | Power gate control |
| **SCC1–SCC4** | Sideband/bridge | 200/100 MHz | IOSF Primary/Sideband, Debug |
| **XTAL** | Crystal ref | 38.4 MHz | Hammock Harbor reference |
| **RTC** | RTC | 32 KHz | Timestamp, always-on timer |

Clock handshake interfaces per partition:
- **SIDE clk_req/ack** — Sideband clock request/acknowledge (SCC region)
- **PRIM clk_req/ack** — Primary clock request/acknowledge (SCC region)
- **FUNC_* clk_req/ack** — Per-partition functional clock handshakes
- **PIXEL_USB clk_req/ack** — USB pixel clock handshake
- **XTAL clk_req/ack** — Crystal reference clock handshake

Clock tree elements:
- **DFS MUX** — Dynamic Frequency Switching multiplexer (400 MHz ↔ 200 MHz selection)
- **FUNC DCG** — Functional Dynamic Clock Gating
- **XTAL DCG** — Crystal Dynamic Clock Gating
- **PIXEL_USB DCG** — Pixel/USB Dynamic Clock Gating
- **Async Bridges** — Clock domain crossing bridges between partitions (POST SCC CDC, PRE SCC CDC)

> **APB clock**: 50 MHz — used for register access to all DesignWare peripherals (I2C, I3C, SPI, UART, DMA MISC).
> **WDT clock**: 25 MHz (normal) / 12.5 MHz (low-power) — watchdog timer clock.
> **Debug clock**: 200 MHz (normal) / 100 MHz (low-power) — DTF trace. **JTAG clock (JTAG_TCK)**: 20 MHz.

### Clock Switching (from HAS SVG: SRAM_SS clock switching + Clocking diagram)

8-step glitch-free clock switching procedure:

1. FW writes `CORE_CLK_SEL` register to select target frequency (0x0 = 400 MHz default, 0x1 = 200 MHz)
2. FW sets `CLK_SW_EN` bit to initiate the switch
3. FW disables all interrupts (critical section — switch must not be interrupted)
4. FW executes **50 NOP instructions** (pipeline drain, same race-guard as D0i2 entry)
5. FW executes **SLEEP instruction** (WFI equivalent — core halts, allowing clock MUX to switch)
6. HW performs **glitch-less clock switch** via DFS MUX (seamless transition between clock trees)
7. **PMU Wake IRQ** fires — wakes the core on the new clock frequency
8. FW re-enables interrupts and resumes execution at the new frequency

> **Constraints**: Clock switch must only occur during ROM/bring-up when no activity is in progress. The switch is not dynamic during active inference — changing frequency mid-inference would corrupt NPX6 NNA timing and DMA transfer calculations.

### Clock Gating

Two levels of clock gating are supported:

| Level | Mechanism | Trigger | Power State |
|-------|-----------|---------|-------------|
| **Block-Level CG** | FW-initiated per-peripheral clock gating | FW writes to CCU `*_BLK_CG` registers | D0i0 (sub-blocks idle) |
| **Trunk-Level CG** | HW-initiated gating of nvu_func_clk tree | FW enters IDLE loop, HW detects idle | D0i1 |

#### Block-Level Clock Gating (Section 13.7.3)

FW enables block-level clock gating by:
1. Programming `CRU_BLK_CG_DIS.BLK_CG_DIS` to `0x0` (enable all block CG)
2. Writing to per-peripheral `*_BLK_CG` registers in CCU for corresponding peripheral blocks

Peripherals supporting block-level CG:

| Peripheral | Block CG Support |
|------------|-----------------|
| I2C | Yes |
| I3C | Yes |
| SPI | Yes |
| UART | Yes |
| BOOTDMA | Yes |
| MJPEGDEC | Yes (fuse-controlled) |
| SHA | Yes |

#### Block Clock Gating (BCG) and Save/Restore (SR) Support Matrix (Integration HAS v0.8, Section 13)

> Full per-block BCG and Save/Restore capability matrix across the 4 NVU partitions that have BCG/SR blocks (MAIN, MIPI, USB, SRAM — VPX and NPX are entire PGCB domains without per-block BCG):

| Partition | Block | BCG Support | Save/Restore | Notes |
|-----------|-------|-------------|-------------|-------|
| **MAIN** | I2C (×3) | Yes | Yes | DW_apb_i2c |
| **MAIN** | I3C (×2) | Yes | Yes | DW_apb_i3c |
| **MAIN** | SPI (×2) | Yes | Yes | DW_apb_ssi |
| **MAIN** | UART (×3) | Yes | Yes | DW_apb_uart |
| **MAIN** | BOOTDMA | Yes | Yes | Boot DMA engine |
| **MIPI** | CVISP | No | Yes | Altek ISP — no block CG, SR via FW context save |
| **MIPI** | CSI2HC | No | Yes | CSI-2 Host Controller — no block CG, SR via FW |
| **USB** | SIOC | No | Yes | SIO Controller |
| **USB** | DPKTZR | No | Yes | De-packetizer |
| **USB** | CBUF | No | Yes | Circular Buffer |
| **USB** | LINK_LOGIC | No | Yes | USB Link Logic |
| **USB** | MSIF2IPI | No | Yes | MSIF-to-IPI bridge |
| **USB** | UDF_UAL | No | Yes | UDF/UAL processing |
| **USB** | SIODMA | No | Yes | SIO DMA |
| **USB** | MJPEGDEC | Yes (Fuse) | Yes (Fuse) | MJPEG Decoder — BCG and SR are fuse-controlled |
| **SRAM** | SHA | Yes | Yes | SHA-384 hash engine |

> **Note**: "No" BCG means the block relies on trunk-level CG (D0i1) for clock gating. All USB partition blocks support SR but not BCG — they are quiesced during D0i2 entry rather than individually clock-gated.

### Clock Req/Ack Interfaces (Section 4.3.4.1)

Five Chassis 2.0 CLOCK_REQ_ACK consumer interfaces:

| Interface | Clock Domain |
|-----------|-------------|
| FUNC_CLK | nvu_func_clk |
| PGCB_CLK | nvu_pgcb_clk |
| XTAL_CLK | nvu_xtal_clk |
| CDPHY_XTAL_CLK | CDPHY crystal clock |
| PIXEL_CLK | nvu_pixel_clk |


## Power Gating (Sections 4.3.4.2, 13.7)

### PGCB Domains

The NVU has three Power Gate Control Block (PGCB) domains (confirmed in HTML HAS):

| PGCB Domain | Power Domain | SW_PG_REQ_B | RESTORE_B | HAS Location | Notes |
|-------------|-------------|-------------|-----------|-------------|-------|
| **NVU_MAIN_PGCB** | Main power domain (VPX2, NPX6, SRAM, fabric) | Yes | Yes | Section 4.3.4.2.1, line ~12833 | Primary domain; supports software-initiated PG |
| **NVU_USB_PGCB** | USB camera interface (USB PD) | No | No | Section 13.7.1, line ~2656 | Sensor-specific; no SW PG request |
| **NVU_MIPI_PGCB** | MIPI camera interface (MIPI PD) | No | No | Section 13.7.2, line ~2657 | Sensor-specific; no SW PG request |

> **Cross-check status**: All 3 PGCB domains confirmed against HTML HAS source. Domain names and power gate capabilities match RTL integration (HAS Section 13.7).

### PGCB Interfaces

Each PGCB domain exposes the following signals to the PMC:

| Signal | Direction | Description |
|--------|-----------|-------------|
| `PMC_FET_EN_B` | PMC -> NVU | Power FET enable (active low) |
| `FET_PMC_EN_ACK_B` | NVU -> PMC | FET enable acknowledge (active low) |
| `SW_PG_REQ_B` | NVU -> PMC | Software power-gate request (Main domain only) |
| `RESTORE_B` | PMC -> NVU | Restore signal after PG exit (Main domain only) |

All PGCB interfaces operate on:
- Clock: `nvu_pgcb_clk` (2.56MHz)
- Power: VNN power domain
- Reset: `nvu_pgcb_rst_b` reset domain

### IPAPG Flow (D0i2)

During D0i2 entry, IPAPG (IP-Accessible Power Gating) is performed (PGCBCG is mandatory for IPAPG):
1. AON task (located in AONRF memory in the un-gated power domain) saves VPX core registers and stack contents to AONRF and prepares for power gating
2. SRAM slices placed in retention by FW; USB and MIPI power domains are power gated (already clock-gated for D0i2 or PG'ed for IPAPG)
3. FW programs CRPM_IPAPG_EN register; PGCB clock gating is applied
4. MAIN PD enters IPAPG, gating VNN_GATED supply
5. On wake, power is restored; Boot ROM executes and checks power status saved in CRPM registers indicating IPAPG exit, then jumps to AON task to continue the restore flow
6. AON task restores VPX core registers and stack contents from AONRF; SRAM exits retention, FW restores context


## SRAM Power Management

### Per-Slice Control (SSCR Register)

Each of the 7 SRAM slices has an SSCR (SRAM Slice Control Register) with the following power management fields:

| Bit | Field | Description |
|-----|-------|-------------|
| 4 | `cr_shutdown_en` | Enable slice shutdown (SRAM contents lost) |
| 3 | `cr_deepsleep_override_val` | Deep-sleep override value: 0 = force active, 1 = force retention |
| 2 | `cr_deepsleep_override_en` | Enable deep-sleep override (FW control instead of HW autonomous) |
| 12 | `cr_ecc_scrub` | Trigger ECC scrub (FW sets to 1, HW clears when complete) |
| 11:8 | `cr_deepsleep_min_duration` | Minimum idle duration before HW enters deep-sleep |

### SRAM Power Modes

| Mode | How to Set | Effect |
|------|-----------|--------|
| **HW Autonomous Deep-Sleep** | Default (override_en=0) | HW enters deep-sleep per slice based on AXI idle; auto-wakes on access |
| **Force Active** | override_en=1, override_val=0 | Slice stays active regardless of idle state |
| **Force Retention** | override_en=1, override_val=1 | Slice enters retention; contents preserved but not accessible |
| **Shutdown** | shutdown_en=1 | Slice fully powered off; contents lost |

### Deep-Sleep Exit Latency

- ~75ns (~30 clocks @ 400MHz) per 128KB bank
- Must be accounted for in latency-sensitive inference scheduling

### ECC Scrub Flow

Before first use of each SRAM slice, FW must perform ECC scrub:
1. Clear `cr_shutdown_en` (bit 4 = 0)
2. Set `cr_ecc_scrub` (bit 12 = 1)
3. Poll `ECCSCRUB` bit until HW clears it (scrub complete)
4. Disable deep-sleep override: `cr_deepsleep_override_en` = 0

### SSCR Register Address

- Base: `SRAMSS_CFG` at `0xF5000000 - 0xF5100000`


## Resource Management (Section 4.3.5)

### Resource Own Req/Ack Pairs

The NVU has 12 resource own_req/ack pairs for coordinating with PMC:

| Bit | Resource | Category | FW Programming Required |
|-----|----------|----------|------------------------|
| 0 | func_clk | Clock | No (HW auto during TCG) |
| 1 | prim_clk | Clock | No (HW auto during TCG) |
| 2 | side_clk | Clock | No (HW auto during TCG) |
| 3 | xtal_clk | Clock | No (HW auto during TCG) |
| 4 | pgcb_clk | Clock | No (HW auto during TCG) |
| 5 | pixel_clk | Clock | No (HW auto during TCG) |
| 6 | vnn | SoC Power | Yes (FW programs CRPM_RESOURCE*_REQ) |
| 7 | peer_fabric | SoC Fabric | Yes (FW programs CRPM_RESOURCE*_REQ) |
| 8 | ddr_snoop | SoC Memory | Yes (FW programs CRPM_RESOURCE*_REQ) |
| 9 | ddr_non_snoop | SoC Memory | Yes (FW programs CRPM_RESOURCE*_REQ) |
| 10 | psf | SoC Fabric | Yes (FW programs CRPM_RESOURCE*_REQ) |
| 11 | sbr | SoC Fabric | Yes (FW programs CRPM_RESOURCE*_REQ) |

- Clock resources are requested/released automatically by HW during trunk-level clock gating flows. FW is not required to program CRPM resource registers for clock resources.
- For SoC resources (VNN, PEER_FABRIC, DDR, PSF, SBR), FW must explicitly program `CRPM_RESOURCE*_REQ` registers.

### CRPM Register Base

- CRPM address range: `0xF3000000 - 0xF3001000`

### CRPM PMC-Side Resource Mapping (Integration HAS Section 12)

The PMC maps NVU CRPM resources to the following indices (used in PMC resource management):

| PMC Index | Resource | Type |
|-----------|----------|------|
| RESOURCE_0 | VNN | HW-managed |
| RESOURCE_1 | PEER_FABRIC | FW-managed |
| RESOURCE_2 | DDR_SNOOP | FW-managed |
| RESOURCE_3 | DDR_NON_SNOOP | FW-managed |
| RESOURCE_4 | PSF | FW-managed |
| RESOURCE_5 | SBR | FW-managed |

> **Note**: The IP-side 12-bit resource vector (bits 0–11) maps clock resources to bits 0–5 and SoC resources to bits 6–11. The PMC-side uses a 6-index scheme (RESOURCE_0–RESOURCE_5) covering only the SoC resources, since clock resources are requested by HW as part of TCG gating/un-gating flows.

### PMC ↔ NVU Message Timeout Rules (from NVU IP HAS Excel — Latency Sheet)

| Message | Sender | Receiver | Timeout Value | Action on Timeout |
|---------|--------|----------|---------------|-------------------|
| **ResetPrep** | PMC | NVU | Strap-configured (see `NVU_Timeout` soft-strap: 2 RTC / 8ms / 16ms / **32ms default**) | **Global Reset** |
| **SleepLevelReq** | PMC | NVU | Strap-configured (same timeout strap) | **Global Reset** |

> **⚠️ CRITICAL**: Both messages trigger a **platform Global Reset** if NVU fails to respond within the timeout window. This means NVU FW must always be responsive to PMC sideband messages — a hung VPX2 DSP or stuck DMA transfer that prevents timely ACK will cause a full platform reset. The timeout is controlled by the `NVU_Timeout` soft-strap at `0x0662[23:21]` (default `0x3` = 32ms).


## PMC Integration (Section 13.5)

### IOSF-SB Configuration

| Parameter | Value |
|-----------|-------|
| IOSF-SB Endpoint Name | NVU |
| Static Disable | F, S, B |
| Chassis Version | 2.2 |
| Host Reset Group | Yes |
| Save/Restore | Yes |
| Hammock Harbor Type | Type-D |
| Power Gate Default | OFF |
| ENABLE_LTR_CAP | 0 (LTR via QoS_DMD RLTR instead) |
| PME Support | D0 and D3 |

### Chassis 2.2 Resources (Section 13.6)

Resources mapped to PMC via CRPM_RESOURCE_*_REQ registers, supporting the Resource Own Req/Ack mechanism.

### Chassis 2.2 Services

| Bit | Service | Purpose |
|-----|---------|---------|
| 1 | `vision_service` | Lid Closed / Lid Open transitions |

### QoS_DMD: RLTR (Resolved Latency Tolerance Reporting)

Since `ENABLE_LTR_CAP = 0`, the NVU uses QoS_DMD RLTR messages instead of PCI LTR:

| Scenario | RLTR Value |
|----------|------------|
| Baseline | Infinite |
| Boot DMA | 2ms |
| Paging DMA | 2ms |
| D0ix | Infinite |

### PRNDE (Periodic Non-Demand Event)

*No verified parameters available from HAS source documentation.*

### QoS_DMD Tag Usage

- NVU always uses tag = 0 for QoS_DMD messages.


## Wake (Sections 13.8, 13.9)

### PME Wake

PME (Power Management Event) is used for host wake in two scenarios:
- **Exception Reset**: Hardware fault requiring host intervention
- **Lid Closed to Lid Open Transition**: NVU signals wake when lid is opened

PME is supported in both D0 and D3 power states.

> **ACPI GPE**: NVU wake is routed through GPE handler `_L94` (ACPI `\_GPE._L94`). BIOS configures the GPE routing; see bios/SKILL.md for full ACPI integration (device path `_SB.PC00.NVUD`).

#### PME Wake Detailed Flow (from HAS SVG: PME Wake diagram — 28 steps)

| Step | Actor | Action | Signal/Register |
|------|-------|--------|-----------------|
| 1 | FW | Sets PME enable in PMCS register | `PMCS[PME_EN] = 1` |
| 2 | FW | Writes CRPM resource request via sideband | `CRPM_RESOURCE_REQ` SBR |
| 3 | FW | Triggers PMU host wakeup sequence | `PMU_HOST_WAKEUP` register write |
| 4 | HW | Sets OOB PME bit in PMU_HOST_WAKEUP | `PMU_HOST_WAKEUP[OOB_PME] = 1` |
| 5 | HW | Sets PME status shadow | `PMU_HOST_WAKEUP[PME_STS_SHADOW] = 1` |
| 6 | HW | Masks PME status clear interrupt | `PMU_HOST_WAKEUP[PME_STATUS_CLR_INT_MSK]` |
| 7 | HW | Sets PME status | `PMU_HOST_WAKEUP[PME_STATUS] = 1` |
| 8 | HW | Asserts OOB AXI PME signal (active low) | `oob_axi_pme_b` assert (low) |
| 9 | IOSF2AXI | Detects PME assertion, generates IOSF SB message | `AssertPME` IOSF SB message |
| 10 | PMC | Receives AssertPME, processes PME wake | PMC internal |
| 11 | PMC | Initiates VNN restore if in VNN-removed state | `nvu_pmc_vnn_own_req` |
| 12 | PMC | Restores clocks and power domains | Clock/power restore sequence |
| 13 | Host | Receives PME interrupt via GPE `_L94` | GPE SCI to OS |
| 14 | OS | Clears PME status | PCI PMCS register write |
| 15 | HW | Deasserts OOB AXI PME signal | `oob_axi_pme_b` deassert (high) |
| 16 | IOSF2AXI | Generates DeAssertPME sideband message | `DeAssertPME` IOSF SB message |
| 17 | PMC | Acknowledges PME deassert | PMC internal |
| 18 | HW | Generates PCI device interrupt | `pmu_pcie_dev_intr` |
| 19–28 | Host/FW | D3 clear, FW reload, service restart | D3 exit → FW load → D0i0 |

> **Key signals**: `oob_axi_pme_b` (active-low PME to IOSF2AXI bridge), `AssertPME`/`DeAssertPME` (IOSF SB messages to PMC), `pmu_pcie_dev_intr` (PCI interrupt to host after PME clear).

### Wake Event Logging

| Register | Description |
|----------|-------------|
| `PMU_WAKE_EVENT1` | Wake event log 1 (sticky; must be cleared by FW) |
| `PMU_WAKE_EVENT2` | Wake event log 2 (sticky; must be cleared by FW) |
| `PMU_WAKE_MASK_EVENT1` | Wake mask for event group 1 |
| `PMU_WAKE_MASK_EVENT2` | Wake mask for event group 2 |

- Wake event registers are **sticky** -- FW must explicitly clear them after reading.

### GPIO Wake

GPIO wake is supported via:

| Register | Description |
|----------|-------------|
| `WAKE_GPIO.GPIO_GISR0` | GPIO Interrupt Status Register (wake sources) |
| `WAKE_GPIO.GPIO_GIMR0` | GPIO Interrupt Mask Register (wake enable/disable) |


## VPX2 Power Management IRQs

CRPM-related interrupts routed to VPX2 for power management:

| IRQ | Name | Description |
|-----|------|-------------|
| 35 | RESETPREP | Reset preparation notification from PMC |
| 37 | WAKE | Wake event interrupt |
| 38 | RESOURCE_OWN_ACK | Resource own request acknowledge from PMC |
| 39 | PCIDEV | PCI device state change |
| 40 | PMU2IOAPIC | PMU to IO-APIC interrupt |
| 42 | VISION_SERVICE | Vision service event (Lid Open/Close) |
| 43 | TELEMETRY_SERVICE | Telemetry service event (Host C0/C10) |

### VPX2 Power Management Signals to CRPM

| Signal | Description |
|--------|-------------|
| `cc_idle` | Core complex idle indication |
| `sys_halt_r` | System halt request |
| `sys_sleep_r` | System sleep request |
| `sys_sleep_mode_r[2:0]` | Sleep mode encoding |


## Power Management Flows (Summary)

### Detailed Power States by Resource (Integration HAS Section 12)

The following table shows the status of each resource across all NVU power sub-states:

| Sub-State | func_clk | prim_clk | side_clk | xtal_clk | pgcb_clk | pixel_clk | cdphy_clk | rtc_clk | VNN | peer_fabric | ddr_snoop | ddr_non_snoop | psf | sbr |
|-----------|----------|----------|----------|----------|----------|-----------|-----|-------------|-----------|---------------|-----|-----|
| D0i0: MIPI RAW | ON | ON | ON | ON | ON | OFF | ON | ON | ON | ON | ON | ON |
| D0i0: USB RAW | ON | ON | ON | ON | ON | ON | ON | ON | ON | ON | ON | ON |
| D0i0: Algo Proc | ON | OFF | ON | OFF | ON | OFF | ON | ON | OFF | OFF | OFF | ON |
| D0i0: FW Paging | ON | ON | ON | OFF | ON | OFF | ON | ON | ON | ON | ON | ON |
| D0i0: IPC to ISH | ON | ON | ON | OFF | ON | OFF | ON | ON | OFF | OFF | ON | ON |
| D0i0: Boot DMA | ON | ON | ON | OFF | ON | OFF | ON | ON | ON | ON | ON | ON |
| D0i1: FUNC TCG | OFF | OFF | OFF | OFF | ON | OFF | ON | ON | OFF | OFF | OFF | ON |
| D0i2: IPAPG+RET | OFF | OFF | OFF | OFF | OFF | OFF | ON | ON | OFF | OFF | OFF | ON |
| Lid Closed | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF | OFF |

> **Note**: "ON" means the resource own_req is asserted. The actual D0i0 sub-state depends on the current NVU operation. During D0i1, only pgcb_clk remains for PGCB/CDC logic and sbr for sideband reset. During D0i2, VNN and sbr remain for SRAM retention. Lid Closed removes all resources including VNN.

### USB PD Gating Flow (Integration HAS Section 12)

USB camera power domain gating is managed via `NVU_USB_PGCB`:

1. **Entry (USB PD OFF)**: When USB camera is not active, FW releases USB resources
2. PMC de-asserts `NVU_USB_FET_EN` for USB PGCB → USB power domain gated
3. USB PHY and USB camera interface logic powered off
4. **Exit (USB PD ON)**: When USB camera streaming is needed, FW requests USB resources
5. PMC asserts `NVU_USB_FET_EN` for USB PGCB → USB power domain restored
6. USB PHY re-initialized

> USB PD can be independently gated from MIPI PD and MAIN PD. Only the active camera interface power domain needs to be ON.

### MIPI PD Gating Flow (Integration HAS Section 12)

MIPI camera power domain gating is managed via `NVU_MIPI_PGCB`:

1. **Entry (MIPI PD OFF)**: When MIPI camera is not active, FW releases MIPI resources
2. PMC de-asserts `NVU_MIPI_FET_EN` for MIPI PGCB → MIPI power domain gated
3. MIPI CSI-2 PHY and MIPI camera interface logic powered off
4. **Exit (MIPI PD ON)**: When MIPI camera streaming is needed, FW requests MIPI resources
5. PMC asserts `NVU_MIPI_FET_EN` for MIPI PGCB → MIPI power domain restored
6. MIPI PHY re-initialized, D-PHY/C-PHY lane training

> MIPI PD can be independently gated from USB PD and MAIN PD. The NVU supports concurrent operation where both MIPI and USB PDs can be independently gated, and concurrent mode allows NVU and IPU to access the camera simultaneously.

### D0i0 Block-Level Clock Gating Flow

1. FW programs `CRU_BLK_CG_DIS.BLK_CG_DIS` = `0x0` to enable block CG globally
2. FW writes to per-peripheral `*_BLK_CG` in CCU for idle blocks
3. Idle peripherals have their clocks gated; active peripherals remain clocked

### D0i1 (Trunk CG) Entry Flow

1. FW completes current work and enters IDLE loop
2. FW prepares for low-power entry (resource release, context housekeeping)
3. HW detects idle condition and performs trunk-level clock gating
4. All clocks gated except `nvu_xtal_clk` (38.4MHz), `nvu_pgcb_clk` (2.56MHz), and `nvu_rtc_clk` (32KHz)
5. SoC can enter up to S0i2.0

### D0i1 Exit Flow

1. Wake event triggers (GPIO, PMC service, timer)
2. HW un-gates trunk clocks
3. FW resumes from IDLE loop

### D0i2 (IPAPG + Retention) Entry Flow

1. FW saves context to SRAM
2. FW configures SRAM slices for retention (`cr_deepsleep_override_en=1, cr_deepsleep_override_val=1`)
3. HW performs trunk-level clock gating
4. NVU_MAIN_PGCB asserts `SW_PG_REQ_B` to PMC
5. PMC de-asserts `PMC_FET_EN_B` -- VNN_GATED supply cut
6. Main power domain OFF; SRAM in retention on VNNAON
7. SoC can enter up to S0i2.0

### D0i2 Exit Flow

1. PMC re-asserts `PMC_FET_EN_B` (power restore)
2. PMC asserts `RESTORE_B` signal
3. SRAM exits retention; FW context preserved
4. Trunk clocks un-gated
5. FW restores context and resumes operation

### Lid Closed Entry Flow

1. PMC sends `sleep_level_req(vision_service=0)` (Chassis 2.2 service bit 1) to NVU to allow VNN removal during lid-closed condition (the system doesn't need to be in modern standby)
2. NVU FW receives the sleep_level_req interrupt (VISION_SERVICE)
3. NVU HW responds to the message and sets a status bit in CRPM to indicate the service bit status to FW. FW performs orderly shutdown: stop cameras, flush DMA; PMC saves specific NVU HW registers (IPC, IOSF2AXI PCI Config, Bridge Private Registers, etc.) before VNN removal
4. SRAM slices are in shutdown mode (all SRAM content is lost during VNN removal)
5. All power domains OFF, VNN removal supported
6. SoC can enter deeper power states as NVU is fully powered down (Shutdown state). For FW, the VNN removal flow appears like an IP reset; after lid-open, FW will reboot from ROM

### Lid Open / Wake Flow

1. External wake event (lid open sensor)
2. PMC initiates NVU power-on sequence
3. PME generated to host (supported in D0 and D3)
4. NVU re-initializes: all SRAM content was lost during lid-close, FW reboots from ROM, sensor re-init
5. PMC sends sleep_level_req with vision_service=1; NVU HW sets a status bit in CRPM to indicate the service status to FW; VPX2 FW receives VISION_SERVICE notification for Lid Open


## FW Power Management Architecture (FAS §13, L14038-14280)

The NVU firmware implements power management through power management framework, coordinating across 4 power domains with the SoC PMC.

### FW Power Domains (FAS §13, L14050-14080)

| Domain | Contents | Gating |
|--------|----------|--------|
| **MAIN Gated** | VPX2 DSP, NPX6-1K NNA, SRAM, DMA, NOC fabric | Power-gated during D0i2/IPAPG |
| **USB Gated** | USB-IF subsystem (XHCI_CAM, SIO, VC9000NanoD) | Power-gated when USB camera inactive |
| **MIPI Gated** | MIPI-IF subsystem (CSI-2 HC, CVISP, PHY sharing logic) | Power-gated when MIPI camera inactive |
| **Un-gated** | AONRF (16KB), AON task logic, GPIO wake, RTC, WDT | Always powered in S0 |

### FW Power States (FAS §13, L14080-14120)

| State | Description | What's Active | S0ix Depth |
|-------|-------------|--------------|------------|
| **D0i0** | Active (DAQ or VPX/NPX execution from SRAM) | All domains powered, block-level CG, SRAM auto retention by HW | S0 only |
| **D0i1** | FW idle loop (Time to Next Event allows D0i1) | Trunk clock gating, USB+MIPI PG, SRAM on (auto retention by HW) | S0 only |
| **D0i2** | Deep idle (IPAPG) | Only un-gated domain; SRAM retained | Up to S0i2.0 (NVU Exclusive) |
| **Shutdown** | VNN de-asserted (lid closed) | Main PD: OFF, USB+MIPI PD: OFF, SRAM OFF | Deepest (Lid-Closed standby) |

### Lid-Open vs Lid-Closed Standby (FAS §13, L14120-14180)

| Aspect | Lid-Open Standby | Lid-Closed Standby |
|--------|-----------------|-------------------|
| Use case | LPVS (Wake-on-Human-Presence) | Platform sleep, no vision |
| Vision | Active at low power | Deactivated |
| Max S0ix | **S0i2.0** (NVU blocks deeper) | **S0i2.1/S0i2.2** (not blocked) |
| VNN | Asserted | **De-asserted** (power removed) |
| Wake behavior | Continuous monitoring | Cold boot on lid-open (SRAM content lost; FW reboots from ROM) |

### Zephyr OSPM Integration (FAS §13, L14200-14250)

NVU uses Zephyr RTOS v3.7.0 power management framework:

- **`pm_state_set()`** — Called by Zephyr idle thread to enter low-power state (D0i1 or D0i2)
- **`pm_state_exit_post_ops()`** — Called on wake to restore context and re-enable clocks

### AON Task (FAS §13, L14180-14200)

The Always-ON task runs from AONRF (un-gated power domain) and handles:
1. **D0i2/IPAPG entry sequence** — saves VPX core registers and stack contents to AONRF
2. **D0i2/IPAPG exit sequence** — restores VPX core registers and stack contents from AONRF
3. **GPIO wake monitoring** — monitors wake sources (camera motion, lid open, host IPC)

> **Note**: AON task code is part of `AON_IMAG` module (aon_image.bin) loaded during BUP phase.

#### AON Task State Machine (Source: FAS SVG `nvu_pm` diagrams)

The AON task implements the following state machine for power management:

| State | Description | Triggers | Next States |
|-------|-------------|----------|-------------|
| **IPAPG** | IP is power-gated, AON task in retention | PMC wake signal, GPIO interrupt | → Wake |
| **Wake** | Boot ROM executes, checks CRPM registers, jumps to AON task to restore VPX context | Context restore complete | → D0i2 Exit |
| **D0i2 Exit** | Exiting D0i2 — re-enabling clocks, restoring config | Clock restore done, FW ready | → Active (normal operation) |
| **D0i2 Enter** | Entering D0i2 — saving context, gating clocks | Save complete, IPAPG criteria met | → IPAPG |
| **Lid Closed** | Lid-closed standby mode — all SRAM content lost | `handle_lid_close()` → VNN removal | → IPAPG (VNN removal) |
| **ResetPrep** | Reset preparation — orderly shutdown | `handle_reset_prep()` from PMC | → Shutdown |
| **Shutdown** | NVU not operational, VNN de-asserted to allow VNN removal | Lid closed | → (FW reboots from ROM on lid-open) |
| **Sx** | System sleep state — NVU non-functional | Platform Sx entry | → Wake (on Sx exit) |

AON Task Handlers (from FAS SVGs):
- **`handle_lid_close()`** — Releases camera/IO resources, enters IPAPG with VNN de-assertion (all SRAM content is lost; FW reboots from ROM on lid-open)
- **`handle_reset_prep()`** — Orderly shutdown in response to PMC ResetPrep sideband message
- **`handle_d0i2()`** — Manages IPAPG entry with SRAM retention, triggered by idle timeout or FW decision


### PMC Signal Reference (Source: HAS SVG power flow diagrams)

Complete list of PMC ↔ NVU power management signals from SVG flow diagrams:

| Signal | Direction | Description |
|--------|-----------|-------------|
| `nvu_pmc_vnn_own_req` | NVU → PMC | VNN ownership request — asserted when NVU needs VNN power |
| `nvu_pmc_vnn_own_ack` | PMC → NVU | VNN ownership acknowledge — PMC confirms VNN is stable |
| `nvu_pmc_pg_req_b` | NVU → PMC | Power-gate request (active low) — NVU requests IPAPG entry |
| `NVU_MAIN_FET_EN` | PMC → NVU | Main power domain FET enable — PMC controls main power island FET (PGCB::FET v2.0 r1.2) |
| `NVU_USB_FET_EN` | PMC → NVU | USB power domain FET enable — PMC controls USB power island FET (PGCB::FET v2.0 r1.2) |
| `NVU_MIPI_FET_EN` | PMC → NVU | MIPI power domain FET enable — PMC controls MIPI power island FET (PGCB::FET v2.0 r1.2) |
| `nvu_pmc_fet_en_ack_b` | NVU → PMC | FET enable acknowledge (active low) — NVU confirms FET state |
| `pmc_nvu_pg_ack_b` | PMC → NVU | Power-gate acknowledge (active low) — PMC confirms PG complete |
| `pmc_nvu_pg_wake` | PMC → NVU | Power-gate wake — PMC signals NVU to exit power-gate |
| `vnn_isol_en_b` | PMC → NVU | VNN isolation enable (active low) — isolates NVU during VNN removal |
| `pmc_nvu_restore_b` | PMC → NVU | Restore (active low) — signals NVU to begin context restore |
| `nvu_pgcb_clk_req` | NVU → PMC | PGCB clock request — NVU requests clock for power-gate controller |
| `nvu_pgcb_clk_ack` | PMC → NVU | PGCB clock acknowledge — PMC confirms clock delivered |
| `nvu_func_clk_req` | NVU → PMC | Functional clock request — NVU requests main functional clock |
| `nvu_func_clk_ack` | PMC → NVU | Functional clock acknowledge — PMC confirms functional clock |
| `nvu_vnn_rown_req` | NVU → PMC | VNN ROWN (Resource OWNership) request |
| `nvu_vnn_rown_ack` | PMC → NVU | VNN ROWN acknowledge |
| `oob_axi_pme_b` | NVU → PMC | OOB PME assertion (active low) — out-of-band PME for D3 wake |
| `IOSF_SB::AssertPME` | NVU → Host | Sideband PME assertion — triggers GPE in OS ACPI |
| `IOSF_SB::DeAssertPME` | NVU → Host | Sideband PME de-assertion — clears PME after host ACK |
| `IOSF_SB::Sleep_Level_Req` | NVU ↔ PMC | Sleep level request with `VISION_SERVICE` parameter (0=sleep, 1=active) |
| `IOSF_SB::SetID` | PMC → NVU | Set ID message during boot — configures NVU identity |

### NPX Power Management (FAS §13, L14250-14280)

- NPX is in the **same power domain (MAIN)** as VPX — they are always power-gated together
- NPX has an **external PMU** (separate from VPX PMU)
- **ARCSync** is used for NPX boot/shutdown control (cpu_start/cpu_stop operations)
- NPX enters low-power when no inference is scheduled (clock-gated by VPX FW)


## USB Camera Power Transitions (E2E HAS v0.1)

> Source: VISION SS End-To-End HAS v0.1. USB camera link power states during ownership handoff.

During USB camera ownership handoff between IPU and NVU, the USB link undergoes power state transitions:

| Link State | Description |
|------------|-------------|
| **U0** | Active state — USB camera streaming data |
| **L2 Suspend** | Low-power suspend — camera idle, no IP streaming |

### USB Camera L2 Suspend / U0 Transition Flow

1. Active owner completes streaming, clears `SEN` (Stream Enable)
2. XHCI_CAM transitions USB link to **L2 suspend** (camera enters low-power)
3. Ownership arbitration occurs (via `USB_CAM_OWNER` flag in IPU_AON)
4. New owner claims USB camera
5. XHCI_CAM transitions USB link from **L2 suspend** to **U0** (active)
6. New owner issues **ConfigureEndpoint** + **InterfaceRequest** to set up ISOCH EPs
7. `SEN` set — isochronous streaming resumes


## Key Register Summary

| Register / Range | Address | Purpose |
|------------------|---------|---------|
| CRPM | `0xF3000000 - 0xF3001000` | Clock, reset, and power management control |
| SRAMSS_CFG | `0xF5000000 - 0xF5100000` | SRAM subsystem configuration (SSCR per slice) |
| CRU_BLK_CG_DIS | Not specified in NVU HAS v1.0 | Block-level clock gating disable register |
| PMU_WAKE_EVENT1 | Not specified in NVU HAS v1.0 | Wake event log 1 |
| PMU_WAKE_EVENT2 | Not specified in NVU HAS v1.0 | Wake event log 2 |
| PMU_WAKE_MASK_EVENT1 | Not specified in NVU HAS v1.0 | Wake mask 1 |
| PMU_WAKE_MASK_EVENT2 | Not specified in NVU HAS v1.0 | Wake mask 2 |
| WAKE_GPIO.GPIO_GISR0 | Not specified in NVU HAS v1.0 | GPIO wake interrupt status |
| WAKE_GPIO.GPIO_GIMR0 | Not specified in NVU HAS v1.0 | GPIO wake interrupt mask |
| CRPM_RESOURCE*_REQ | Not specified in NVU HAS v1.0 | SoC resource request registers (VNN, DDR, etc.) |
| SSCR (per slice) | Within SRAMSS_CFG range | SRAM slice control: shutdown, deep-sleep, ECC |
| PMCTL | `PCR[NVU]+1D0h` | Power Management Control — BIOS programs clock gating enables (trunk and local gate enables) (see bios/SKILL.md REQ2) |
| D0I3_MAX_POW_LAT_PG_CONFIG | CFG offset `A0h` | D0i3 Max Power Latency and Power Gating Config (see bios/SKILL.md REQ3) |


## Validation Checklist

| # | Check | Power State | Expected |
|---|-------|-------------|----------|
| 1 | Verify D0i0 block-level CG reduces dynamic power for idle peripherals | D0i0 | Clock gated for idle blocks |
| 2 | Verify D0i1 entry: all clocks gated except PGCB + RTC | D0i1 | Only nvu_pgcb_clk and nvu_rtc_clk active |
| 3 | Verify D0i1 exit: wake event restores trunk clocks | D0i1 -> D0i0 | All functional clocks restored |
| 4 | Verify D0i2 entry: SRAM in retention, Main PD OFF | D0i2 | SRAM retention by FW, IPAPG active |
| 5 | Verify D0i2 exit: context preserved after IPAPG restore | D0i2 -> D0i0 | FW resumes correctly from saved context |
| 6 | Verify Lid Closed: all power off, VNN removal supported | Lid Closed | VNN removed, SRAM in retention by HW (SDF) |
| 7 | Verify Lid Open: PME generated, NVU re-initializes | Lid Closed -> D0i0 | Full re-init including ECC scrub |
| 8 | Verify SRAM deep-sleep exit latency ~75ns per 128KB bank | D0i0 | Latency within spec |
| 9 | Verify ECC scrub completes for all 7 slices before first use | Boot / Lid Open | ECCSCRUB bit clears per slice |
| 10 | Verify PGCB FET_EN/ACK handshake for all 3 domains | D0i2 entry/exit | Proper PMC handshake |
| 11 | Verify clock req/ack for all 5 interfaces | D0i1 transitions | Chassis 2.2 protocol compliance |
| 12 | Verify resource own req/ack for SoC resources (VNN, DDR, etc.) | All transitions | PMC acknowledges all requests |
| 13 | Verify RLTR values match HAS spec (2ms for DMA, Infinite for baseline/D0ix) | D0i0 / D0ix | QoS_DMD RLTR correct |
| 14 | Verify PRNDE 333ms periodic wake during camera streaming | D0i0 (streaming) | Periodic wake at 333ms |
| 15 | Verify vision_service triggers Lid Close/Open correctly | Lid transitions | IRQ 42 received by VPX2 |
| 16 | Verify telemetry_service reports Host C0/C10 | Runtime | IRQ 43 received by VPX2 |
| 17 | Verify wake event registers are sticky and must be FW-cleared | Wake | PMU_WAKE_EVENT* sticky |
| 18 | Verify 400MHz -> 200MHz clock switch during bring-up | Boot | Switch only when no activity |
| 19 | Verify SoC reaches S0i2.0 during D0i1/D0i2 | D0i1, D0i2 | PMC residency counters |
| 20 | Verify SoC reaches S0i2.2 during Lid Closed | Lid Closed | PMC residency counters |


## See Also

- [registers/SKILL.md](../registers/SKILL.md) — PGCB, clock gating, PMU registers
- [driver/SKILL.md](../driver/SKILL.md) — D-state transitions, PM callbacks
- [firmware/SKILL.md](../firmware/SKILL.md) — FW-driven power sequencing, PMC sideband, WAMR thread model
- [platform/SKILL.md](../platform/SKILL.md) — PMC addresses, partition power domains
- [bios/SKILL.md](../bios/SKILL.md) — BIOS programming recipe (PMCTL, HAE, SLEEP_EN, D0i3 Max Power Latency), RTD3 ACPI flow (22-step D3hot entry/exit)
- [debug/SKILL.md](../debug/SKILL.md) — Power state debug, PMC telemetry
- **NVU FAS v1.0** — §13 Power Management (L14038-14280): FW power domains, Zephyr OSPM, AON task, NPX PM

## Related Sub-Skills

- [fv-nvu/platform](../platform/SKILL.md) — Platform integration, reset sequences, straps, fuses, BDF
- [fv-nvu/bios](../bios/SKILL.md) — BIOS/FW requirements, power management BIOS flows


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:44 | Facts added: 527


### Additional HAS Details (18 facts)

#### Lid-Open Standby Power Accounting

*(13 Chapter 9: NVU Power Management > 13.2 Lid-Open Standby)*

- Power for NVU use cases is accounted for only based on the resources NVU uses and the duration of time NVU uses them.
- Whether the SoC is in S0ix or S0 is irrelevant to NVU power accounting under this model.

---

#### BIOS Power Management Configuration

*(6 NVU Requirements to BIOS > 6.4 NVU Power Management Configuration)*

| Field | Register | Bits | Value |
|---|---|---|---|
| Latency Scale | PCI[NVU] + A0h | [12:10] | `111b` |
| Latency Value | PCI[NVU] + A0h | [9:0] | `0x3FF` |

---

#### RTD3 Support

*(6 NVU Requirements to BIOS > 6.8 NVU RTD3 Support; 13 Power Management > 13.7 Power Management Flows > 13.7.6 RTD3 Flows)*

- RTD3 is **not supported** for NVU; RTD3 flow is not a use case for NVU.
- The second PCI function has no role in any RTD3 flow.
- ACPI reference check example:
  ```
  If (CondRefOf (\_SB.PC00.NVUD)) {
  ```

---

#### Power Supply

*(13 Power Management > 13.4 Power Supply)*

- Ground reference is defined for the NVU power supply domain.

---

#### Chassis 2.2 Support — Services and QoS

*(13 Power Management > 13.6 Chassis 2.2 Support > 13.6.2 Services; 13.6.3.1 DDR Snoop & Non-Snoop)*

**Services Table**

| IP Service | Bit Number |
|---|---|
| Global | 0 |

- The D0ix scenario is defined within the DDR Snoop & Non-Snoop QoS demand (`QoS_DMD`) context.

---

#### Zephyr OSPM Integration — Device Power Management

*(13 Chapter 9: NVU Power Management > 13.6 Zephyr OSPM Integration > 13.6.0.2 Device Power Management)*

- Device drivers must implement a PM callback function supporting the following Zephyr device PM actions:
  - `PM_DEVICE_ACTION_SUSPEND`
  - `PM_DEVICE_ACTION_RESUME`
- The PM callback function pointer must be initialized within the device structure using one of the following macro pairs:
  - `PM_DEVICE_DEFINE()` **and** `DEVICE_DEFINE()`
  - `PM_DEVICE_DT_INST_DEFINE()` **and** `DEVICE_DT_INST_DEFINE()`

---

#### NPX Power Management

*(13 Chapter 9: NVU Power Management > 13.7 NPX Power Management)*

- NPX follows the Zephyr device power management mechanism and adheres to NVU power policy.
- On `PM_DEVICE_ACTION_SUSPEND`: the ARCSync driver performs its clean-up operation.


### Boot and Reset Sequences (2 facts)

#### NPX Boot and Reset Sequences

##### PM_DEVICE_ACTION_RESUME – NPX Core Boot

(HAS: Chapter 9: NVU Power Management > 13.7 NPX Power Management)

- On a `PM_DEVICE_ACTION_RESUME` action, the ARCSync driver will follow the **NPX Reset flow** to boot the NPX core.

---

##### NPX Boot Flow – Data Section Operation

(HAS: Chapter 9: NVU Power Management > 13.7 NPX Power Management)

- During the NPX boot flow, a dedicated **data section operation** is performed as part of the initialization sequence.


### Camera Interface (41 facts)

#### Camera Interface

### Overview

The NVU camera interface implements a MIPI CSI-2 camera pipeline consisting of a shared MIPI CSI-2 Combo (C/D) PHY sourced from the Image Processing Unit (IPU), a MIPI CSI-2 Host Controller, and the CVISP low-power computer vision focused ISP pipeline. (HAS 5.1)

---

#### MIPI CSI-2 Pipeline Components

- **MIPI CSI-2 PHY**: Shared MIPI CSI-2 Combo (C/D) PHY from the Image Processing Unit (IPU) (HAS 5.1)
- **MIPI CSI-2 Host Controller (CSI2HC)**: Receives and processes raw MIPI camera data (HAS 5.1)
- **CVISP**: Low-power computer vision focused ISP pipeline for processing camera data (HAS 5.1)

---

#### PHY Sharing

##### Architecture

- The **Arbitration Logic**, which arbitrates between requests from IPU and NVU to own a specific C/D-PHY, resides in the **IPU power un-gated domain** and is shared with NVU. (HAS 8.1.1)
- Inside NVU, the **PHY Sharing Logic** resides in the **NVU power un-gated domain**. (HAS 8.1.1)

##### Arbitration Behavior

- The `nvu_release_claim_req` signal is sent to NVU when both `IPU_claim` and `NVU_claim` are simultaneously asserted for any C/D-PHY. (HAS 8.1.1)
- Upon receiving `nvu_release_claim_req`, NVU firmware is **woken and interrupted**; FW is expected to release `NVU_claim` so that IPU can proceed. (HAS 8.1.1)

##### Reset

- The `Soft_reset` register resets the Arbitration Logic and all registers in the power-gated domain. (HAS 8.1.1)
- `Soft_reset` should be used **only for unexpected errors**. (HAS 8.1.1)

---

#### Camera Sensor Control — MIPI Camera MCLK

- The SoC defaults to **XTAL 19.2 MHz** as the MCLK source. (HAS 8.1.3.1)
- If IPU switches to a different MCLK source, that configuration **persists during NVU operation**. (HAS 8.1.3.1)
- If **IMGPLL** is selected (e.g., to meet jitter requirements), that selection remains in effect; NVU FW must account for the active MCLK source at time of operation. (HAS 8.1.3.1)

---

#### Power Domains and Camera Interface

NVU contains 4 power domains relevant to camera operation: **MAIN Gated**, **USB Gated**, **MIPI Gated**, and **Un-gated**. USB and MIPI power domains (PDs) can be gated independently of the MAIN PD. MAIN PD can only be gated after both USB and MIPI PDs have been gated. (HAS 13.1)

##### Power State Behavior — Camera Sub-States

The table below summarizes power domain states for camera-related operating sub-states. (HAS 13.2)

| Power State | Sub-State | Main PD | USB PD | MIPI PD | SRAM |
|---|---|---|---|---|---|
| D0i0 (Active) | MIPI RAW – Low Power Sensing (IPU in D3) | ON | OFF | ON | ON |
| D0i0 (Active) | MIPI RAW – Sensing + (Host) IPU Streaming | ON | ON | ON | ON |
| D0i0 (Active) | USB RAW – Low Power Sensing (IPU in D3) | ON | ON | ON | ON |
| D0i0 (Active) | USB RAW – Sensing + (Host) IPU Streaming | ON | ON | ON | ON |
| D0i0 (Active) | USB Legacy – Low Power Sensing (IPU in D3) | ON | ON | OFF | ON |
| D0i0 (Active) | USB Legacy – Sensing + (Host) IPU Streaming | ON | ON | ON | ON |
| D0i0 (Active) | Algo Processing – Low Power Sensing | ON | OFF | OFF | ON |
| D0i0 (Active) | Algo Processing – Sensing + Host Streaming | ON | ON | ON | ON |
| D0i0 (Active) | FW Paging | ON | OFF | OFF | ON |
| D0i0 (Active) | IPC to ISH (Algo results) | ON | OFF | OFF | ON |
| D0i1 (Idle) | FUNC TCG | ON | OFF | OFF | ON |
| D0i2 (Deep Idle) | IPAPG + RET | OFF | OFF | OFF | RET |
| Lid Closed (Shutdown) | Shutdown | OFF | OFF | OFF | RET |

- In the **Shutdown** state, VNN is de-asserted to allow VNN removal; this state is entered when the lid is closed. SRAM is placed in retention before full power removal. (HAS 13.4)
- For detailed PG entry and exit procedures for USB and MIPI power domains, and for D0i0, D0i1, and D0i2 (including IPAPG) state transitions, refer to **NVU HAS: Power Management Flows**. (HAS 13.4)

---

#### Block-Level Clock Gating and Soft Resets — MIPI Partition

The following camera-related blocks reside in the **MIPI partition**. (HAS 13.10)

| Partition | Block | CRPM BCG | CRPM SR |
|---|---|---|---|
| MIPI | CVISP | N | Y |
| MIPI | CSI2HC | N | Y |

- Neither CVISP nor CSI2HC supports CRPM-controlled Block Clock Gating (BCG). (HAS 13.10)
- Both CVISP and CSI2HC support CRPM-controlled Soft Reset (SR). (HAS 13.10)

---

#### Wake Signals

- NVU exposes three wake signal domains to PMC: **main**, **usb**, and **mipi**. (HAS 13.5)

---

#### QoS and Camera Streaming

- NVU uses **QoS_DMD with PRNDE** (Periodic Next Device Event) to communicate periodic next device event information during camera streaming. (HAS 13.6.3.2)

---

#### USB Camera Interface

- The USB camera pipeline sub-component (SIO Component) supports **link power management**. (HAS 2.5.1.6.1)
- NVU has sideband/IPC interfaces to **ESE, ISH, and PMC**; sensing capabilities are exposed to the host (Windows or Linux) via ISH as HID sensors. (HAS 5.2)

---

#### Camera Streaming and Handoff Flows

- The "Camera App opens on Host" sequence (Step 3 in MIPI streaming and handoff flows) is also applicable for **Wake on Approach** with Windows Hello Biometric authentication requiring IR and RGB streams. (HAS 5.1.2)
- The "Camera App opens on Host" sequence (Step 3 in USB streaming and handoff flows) is also applicable for **Wake on Approach** with Windows Hello Biometric authentication requiring IR and RGB streams. (HAS 5.2.3)

---

#### Power Targets

The following SoC power targets (adder) apply to camera sensing use-cases. (HAS 2.8.1)

| Use-Case / Feature | SOC Power Target (Adder) | Target fps |
|---|---|---|
| User Presence / Face Detection (MIPI Camera) | 5 mW | 3 fps |
| User Presence / Face Detection (USB Camera) | 8–10 mW | 3 fps |

- Power targets for face detection use-cases are also dependent on the **number of faces detected** in the camera frame. (HAS 2.8.1)


### Clock and Power Gating (15 facts)

#### Clock and Power Gating

##### Overview (§13 Power Management)

- NVU supports **IP Accessible Power Gating (IPAPG)** of logic.
- NVU supports **Truck level Clock Gating (TCG)**.
- NVU supports **Block level Clock Gating (BCG)**.
- NVU supports **PGCB clock gating**.
- NVU supports **SRAM retention by FW**.
- NVU supports **SRAM runtime shutdown**.
- Full details of the power management feature are documented in the power management related MAS documents on the NVU SharePoint (§13.1 Isolation Gates and Power Gating).
- For clock resources, FW is **not** required to program any CRPM resource register. These resources are requested by HW as part of TCG gating/un-gating flows.

---

##### IP Disable (§2.5.1.23 IP Disable)

- The SOC adds support for disabling the NVU via **Fuse**, **Soft-strap**, or **BIOS Menu**.
- When NVU is disabled by any of these mechanisms, **PMC** is responsible for maintaining NVU in an **IP-Inaccessible Power Gated** state.

---

##### Power Gating Flows (§13.7 Power Management Flows)

###### USB Domain Power Gating (§13.7.1)

- Power gating flows are defined for the **USB Domain**.
- **TCG (Trunk Clock Gating) flows** are also required for this domain and are noted as pending addition to this section.

---

##### Block-Level Clock Gating and Soft Resets (§13.10 Block Level Clock Gating & Soft Resets)

The table below lists NVU blocks, their partition membership, and support for CRPM-controlled Block Clock Gating (BCG) and Soft Reset (SR).

> **Key:** Y = Supported | N = Not Supported | Y (Fuse) = Supported, enabled via Fuse

| Partition | Block | CRPM BCG | CRPM SR |
|-----------|-------------|----------|---------|
| MAIN | SPI[0:N] | Y | Y |
| MAIN | I2C[0:N] | Y | Y |
| MAIN | I3C[0:N] | Y | Y |
| USB | SIOC | N | Y |
| USB | DPKTZR | N | Y |
| USB | CBUF | N | Y |
| USB | LINK_LOGIC | N | Y |
| USB | MSIF2IPI | N | Y |
| USB | UDF_UAL | N | Y |
| USB | MJPEGDEC | Y (Fuse) | Y (Fuse) |

> **Note:** A CRPM BCG value of **Y (Fuse)** indicates that block-level clock gating is conditionally enabled based on fuse configuration (§13.10).


### DMA Architecture (5 facts)

#### DMA Architecture

##### Security Configuration for DMA
(HAS §9 Chapter 5: NVU Firmware Loading > 9.2.2.1 Extra BUP Tasks)

During the BUP (Bring-Up Processor) boot flow, NVU firmware must establish the following DMA-related security settings:

- **IPC_DISABLE** — Cuts off IPC communication between the NVU and the host, preventing unauthorized inter-processor messaging after firmware load
- **RS3_WR_DISABLE** — Restricts DMA to one-way transfers only (from host to NVU), ensuring write-back paths are disabled for security isolation

---

##### DMA Latency Tolerance Reporting (LTR) — QoS Scenarios
(HAS §13 Power Management > 13.6.3.1 DDR Snoop & Non-Snoop)

The following LTR values apply to DMA scenarios under Chassis 2.2 QoS_DMD support:

| DMA Scenario | Phase | LTR Value |
|---|---|---|
| Boot DMA | Pre-firmware | 2 ms |
| Paging DMA | Run-time paging IN | 2 ms |

- LTR values are used to communicate acceptable memory latency tolerances to the platform power management logic during DDR snoop and non-snoop DMA transactions

---

##### Block-Level Clock Gating and Soft Resets for DMA Blocks
(HAS §13 Power Management > 13.10 Block Level Clock Gating & Soft Resets)

| Partition | Block | CRPM BCG | CRPM SR |
|---|---|---|---|
| MAIN | BOOTDMA | Y | Y |
| USB | SIODMA | N | Y |

- **BOOTDMA** (MAIN partition) supports both CRPM-controlled block clock gating (BCG) and soft reset (SR), enabling full power management of the boot DMA engine
- **SIODMA** (USB partition) does **not** support CRPM block clock gating but does support CRPM soft reset; clock gating for this block must be managed through alternate means


### DSP Core (VPX2) (41 facts)

#### DSP Core (VPX2) — Power Management

---

#### VPX2 Power-Related Capabilities

- **Sleep / power management** (§2.5.1.1.1):
  - Supports the `SLEEP` instruction with multiple sleep modes
  - Programmable interrupt priority threshold for wake-up from sleep mode
  - Hardware run and halt control through external interface

- **Memory Management Unit** (§2.5.1.1.1):
  - Two configurable page sizes: normal pages and super-pages
  - Each size can be configured to any power-of-2 size from 4 KB to 16 MB
  - Software-managed TLB with hardware assist for TLB entry management

---

#### VPX2 Configuration Options

(§8.3.3)

| Option | Value |
|---|---|
| `power_domains` | FALSE |
| `clock_gating` | TRUE |

---

#### VPX2 Clock and Reset Integration

All clock and reset signals are connected to **CRPM** (§8.3.4).

| Interface | Port Name | Connectivity | Description |
|---|---|---|---|
| Clock | `clk` | CRPM | DSP Functional Clock |
| Clock | `mbus_clk_en` | CRPM | Memory Bus Clock Enable (For Clock Division) for CBU I/F |
| Clock | `lbus0_clk_en` | CRPM | Peripheral Bus Clock Enable (For Clock Division) for LBU I/F |
| Clock | `stu_initiator_clk_en` | CRPM | STU Bus Clock Enable (For Clock Division) for STU I/F |
| Reset | `rst_a` | CRPM | DSP Functional Reset |

> **Note (§8.3.4):** Although the `sys_tf_halt_r` signal is connected to CRPM, VPX2 does **not** support assertion of this signal. This connectivity exists for future usage. VPX2 only supports double-faults via the expected mechanism.

---

#### VPX2 Reset Flow

(§8.3.5)

- CRPM brings the VPX2 core out of HALT state by asserting the `run_req` signal.

##### Halt-on-Reset (Reset Debug) (§8.3.5.1)

- CRPM asserts `run_req` to release the core from the halted state following reset.
- A **reset break** capability is supported via STAP sending an indication to the HW FSM; refer to the DFX HAS for full details.
- A new HW flow keeps the core in the halted state based on the **`VPX_HALT_FUSE`** value.
- For additional information on the CRPM IP, see:
  `https://docs.intel.com/documents/ISH_IP_Internal_Specs/AVB/Design/NVU/CRPM/Doc/NVU_CRPM_MAS.html`

---

#### Power-Related Interrupts on VPX2

(§8.1.1)

| Index | Module | IRQ Name | IRQ Pin | Address |
|---|---|---|---|---|
| 26 | IPC | PMC IRQ | `irq26_a` | 0x68 |
| 35 | CRPM | RESETPREP IRQ | `irq35_a` | 0x8C |
| 36 | CRPM | SPARE0 IRQ | `irq36_a` | 0x90 |
| 37 | CRPM | WAKE IRQ | `irq37_a` | 0x94 |
| 38 | CRPM | RESOURCE_OWN_ACK IRQ | `irq38_a` | 0x98 |
| 39 | CRPM | PCIDEV IRQ | `irq39_a` | 0x9C |
| 40 | CRPM | PMU2IOAPIC IRQ | `irq40_a` | 0xA0 |
| 41 | CRPM | SPARE1 IRQ | `irq41_a` | 0xA4 |
| 42 | CRPM | VISION_SERVICE IRQ | `irq42_a` | 0xA8 |
| 43 | CRPM | TELEMETRY_SERVICE IRQ | `irq43_a` | 0xAC |
| 44 | CRPM | SPARE2 IRQ | `irq44_a` | 0xB0 |
| 45 | CRPM | SPARE3 IRQ | `irq45_a` | 0xB4 |
| 46 | CRPM | SPARE4 IRQ | `irq46_a` | 0xB8 |

---

#### Power-Related Memory Map Regions

(§8.2.2)

| Block | Sub Region | Size (KB) | Start Address | End Address |
|---|---|---|---|---|
| PMC_IPC | PMC_IPC | 4 | 0xF1101000 | 0xF1102000 |
| CRPM | CRPM | 4 | 0xF3000000 | 0xF3001000 |

---

#### Firmware Components and Power State Roles

##### AON Task (§13.5.1)

- Located in **AONRF memory**, which resides in the **un-gated power domain**.
- Handles **D0i2** and **IPAPG** entry/exit flows.
- Responsibilities include saving and restoring VPX core registers and stack contents to/from AO (Always-On) memory.

##### Boot ROM (§13.5.2)

- Executed when the VPX core is brought out of reset.
- Checks power status saved in **CRPM registers** to determine if the boot is an exit from IPAPG.
- If an IPAPG exit is detected, execution jumps to the AON task to continue the resume flow.

---

#### Zephyr OSPM Integration (§13.6)

- **Zephyr RTOS v3.7.0** runs on NVU VPX as the OSPM layer to manage system power state transitions.
- Refer to the Zephyr PM power management subsystem documentation for details on power management internals.

---

#### NPX Power Management (§13.7)

- NPX resides in the **same Power Domain (PD) as VPX**, as specified in the NVU HAS.


### Debug and Trace (1 facts)

#### System Power Management Hooks

(HAS §13 Chapter 9: NVU Power Management > 13.6 Zephyr OSPM Integration > 13.6.0.1 System Power Management)

- The PM service implements the following two hook functions to integrate with the Zephyr power subsystem framework for system power management:


### GPIO and Pin Mux (19 facts)

#### GPIO and Pin Mux

##### PHY Sharing — GPIO Wake Sources

The following internal GPIOs are assigned as wake sources to support MIPI CSI-2 PHY sharing between the NVU and IPU. (HAS: Chapter 4 > 8.1.1 PHY Sharing)

| GPIO    | Signal                    | Source | Purpose                                      |
|---------|---------------------------|--------|----------------------------------------------|
| GPIO[21] | `nvu_release_claim_req`  | IPU    | Wake source for NVU release/claim request    |
| GPIO[22] | `CDPHY_owner[0]`         | IPU    | Toggle detect on CDPHY ownership, bit 0      |
| GPIO[23] | `CDPHY_owner[1]`         | IPU    | Toggle detect on CDPHY ownership, bit 1      |

- `nvu_release_claim_req` shall be connected to GPIO[21] as an internal GPIO wake source. (HAS: 8.1.1 PHY Sharing)
- `CDPHY_owner[0]` and `CDPHY_owner[1]` shall be connected to GPIO[22] and GPIO[23] respectively as internal GPIO wake sources. (HAS: 8.1.1 PHY Sharing)
- FW shall configure GPIO[22] and GPIO[23] for **dual edge detection**. (HAS: 8.1.1 PHY Sharing)

---

##### Camera Configuration — GPIO Pin Function

The BIOS camera configuration structure exposes a GPIO function field per GPIO set entry. (HAS: Chapter 6 > 6.11 Camera Configurations)

| Configuration Field                  | Data Type | Range   | Description                                                                                                                                                  |
|--------------------------------------|-----------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `MipiConfig.GPIO.GpioSet[0].Function` | UINT8     | [0, 22] | Function of the GPIO pin. Values: `0` = GPIO_RESET, `1` = GPIO_PWDN, `2` = GPIO_STROBE, `3` = GPIO_TORCH, `4` = GPIO_FLASH, `5` = GPIO_INDICATOR_REAR, `6` = GPIO_INDICATOR_FRONT |

---

##### GPIO Wakes and Wake Masks

The NVU GPIO wake architecture uses a three-tier register structure: a global wake event/mask at the PMU level, per-bit wake event/mask registers for D0ix states, and IRQ status/mask registers for the D0 active state. (HAS: Chapter 9 > 13.9.1 GPIO Wakes and Wake Masks)

| GPIO Group | Global Wake Event / Mask                                                    | Per-Bit Wake Event/Mask (D0ix)             | IRQ Status/Mask (D0)                       |
|------------|-----------------------------------------------------------------------------|--------------------------------------------|--------------------------------------------|
| GPIO[1]    | `PMU_NVU_WAKE_EVENT1.GPIO_WAKE[1]` / `PMU_NVU_WAKE_MASK_EVENT1.GPIO_WAKE_MASK[1]` | `WAKE_GPIO.GPIO_GISR0` / `WAKE_GPIO.GPIO_GIMR0` | `WAKE_GPIO.GPIO_GISR0` / `WAKE_GPIO.GPIO_GIMR0` |

> **Note:** Comprehensive wake capture, partial wake handling, and spurious wake documentation for NVU GPIO will be captured in the CRPM MAS. (HAS: 13.9.1 GPIO Wakes and Wake Masks)

---

##### Power State Context for GPIO Wakes

GPIO wake sources are relevant across the NVU D0ix power states. The following power states define when GPIO wakes may be received. (HAS: Chapter 9 > 13.4 Power States)

| Power State | Description                                                              | Power Saving Options                                                                 |
|-------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| D0i0        | NVU is in DAQ (Data Acquisition) or VPX/NPX execution from SRAM         | Block-level CG; SRAM auto-retention by HW; RLTR: Infinite (default) or 2 ms (RS3 DMA) |
| D0i1        | NVU FW enters IDLE loop with no activity; Time to Next Event allows D0i1 entry | MAIN PD: Trunk CG; USB and MIPI PD: PG; SRAM auto-retention by HW                  |
| D0i2        | NVU FW enters IDLE loop with no activity; Time to Next Event allows D0i2 entry | MAIN PD: IPAPG; USB and MIPI PD: PG; SRAM in retention by FW PGCB                  |


### IOSF Bridge (92 facts)

#### IOSF Bridge

### Overview

The NVU IOSF Bridge provides the sideband messaging interface between NVU and PMC via IOSF Sideband (IOSF-SB). This bridge implements the PMC IPC channel used for power management coordination, doorbell signaling, and inter-processor messaging.

- NVU exposes IOSF-SB endpoint names to PMC as part of the PMC Integration Checklist (13 Power Management > 13.5 PMC Integration Checklist)
- The SOC IOSF Sideband (`sbr`) resource is assigned bit number 11, managed by PMC, with no RLTR, PRNDE, or sleep_level_req signaling from/to NVU (13 Power Management > 13.6 Chassis 2.2 Support > 13.6.1 Resources)

#### BIOS Requirements

- BIOS shall enable the PMCTL (Power Management Control) for the NVU Bridge (6 NVU Requirements to BIOS > 6.4 NVU Power Management Configuration)

#### Save and Restore Behavior

During VNN voltage domain removal and restore, the following IOSF Bridge-related state is managed (6 Voltage Domains > 6.1 Lid Closed vs Lid Open > 6.1.2 Save and Restore):

- NVU saves the following registers to PMC prior to VNN removal:
  - IPC ESE and ISH IPC Channels
  - IOSF2AXI PCI Config registers
  - Bridge Private Registers
- PMC restores these registers upon VNN restore

---

### PMC IPC IOSF Sideband Message Interface (`nvu_PMC_IPC_IOSF_SideBand_Msg`)

All registers below are accessed via IOSF Sideband Message (MSG B?:D?:F?). All registers are 32 bits wide and reset on FUNCRST.

#### Channel Interrupt Registers

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| `CIM_PMC` | 0x2010 | 32 | — | AGENT Channel Interrupt Mask. Masks per-channel interrupts toward NVU FW. Reset: FUNCRST |
| `CIS_PMC` | 0x2014 | 32 | — | AGENT Channel Interrupt Status. Per-channel interrupt status for NVU FW. Reset: FUNCRST |

##### `CIM_PMC` — AGENT Channel Interrupt Mask (Offset 0x2010)
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > CIM_PMC)

| Field | Bits | Reset | Access | Description |
|-------|------|-------|--------|-------------|
| `CH_INTR_MASK` | [0] | 0x0 | RW | Global interrupt enable toward FW for the channel. 0 = interrupt unmasked |
| `RESERVED0` | [31:1] | 0x00000000 | RO | Reserved |

##### `CIS_PMC` — AGENT Channel Interrupt Status (Offset 0x2014)
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > CIS_PMC)

| Field | Bits | Reset | Access | Description |
|-------|------|-------|--------|-------------|
| `CH_INTR_STATUS` | [0] | 0x0 | RO/V | Global interrupt status for FW. Set if any enabled interrupt source is active |
| `RESERVED0` | [31:1] | 0x00000000 | RO | Reserved |

---

#### Doorbell Registers

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| `PMC2NVU_DOORBELL_PMC` | 0x2048 | 32 | — | Inbound Doorbell: AGENT to NVU. Used by PMC to interrupt NVU. Reset: FUNCRST |
| `NVU2PMC_DOORBELL_PMC` | 0x2054 | 32 | — | Outbound Doorbell: NVU to AGENT. Used by NVU to interrupt PMC. Reset: FUNCRST |

##### `PMC2NVU_DOORBELL_PMC` — Inbound Doorbell AGENT To NVU (Offset 0x2048)
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > PMC2NVU_DOORBELL_PMC)

| Field | Bits | Reset | Access | Description |
|-------|------|-------|--------|-------------|
| `PAYLOAD_31BIT` | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |

##### `NVU2PMC_DOORBELL_PMC` — Outbound Doorbell NVU To AGENT (Offset 0x2054)
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > NVU2PMC_DOORBELL_PMC)

| Field | Bits | Reset | Access | Description |
|-------|------|-------|--------|-------------|
| `PAYLOAD_31BIT` | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |
| `BUSY` | [31] | 0x0 | RW | When cleared, AGENT CPU is ready to accept a new message |

---

#### Interrupt Status Register — `PISR_PMC2NVU`
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > PISR_PMC2NVU)

| Field | Bits | Reset | Access | Description |
|-------|------|-------|--------|-------------|
| `AGENT2NVU_DB` | [0] | 0x0 | RO/V | AGENT2NVU Inbound Message Interrupt Status. Read by NVU FW only. 1 = DOORBELL BUSY interrupt active |
| `RESERVED1` | [26:1] | 0x0000000 | RO | Reserved |
| `AGENT2NVU_BCISC` | [27] | 0x0 | RW/1C/V | AGENT2NVU Inbound message busy clear interrupt status. Written by NVU FW only to clear the interrupt status |
| `RESERVED0` | [31:28] | 0x0 | RO | Reserved |

---

#### Inbound Inter-Processor Message Registers (PMC → NVU)

All registers carry inter-process messages from AGENT (PMC) to NVU. All fields are a single 32-bit `MSG [31:0]` word with reset value `0x00000000`, access `RW`, and reset signal FUNCRST.
(CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg > PMC2NVU_MSGn_PMC)

| Register | Offset | Description |
|----------|--------|-------------|
| `PMC2NVU_MSG0_PMC` | 0x20E0 | Inbound IPC Message 0, AGENT → NVU |
| `PMC2NVU_MSG1_PMC` | 0x20E4 | Inbound IPC Message 1, AGENT → NVU |
| `PMC2NVU_MSG2_PMC` | 0x20E8 | Inbound IPC Message 2, AGENT → NVU |
| `PMC2NVU_MSG3_PMC` | 0x20EC | Inbound IPC Message 3, AGENT → NVU |
| `PMC2NVU_MSG4_PMC` | 0x20F0 | Inbound IPC Message 4, AGENT → NVU |
| `PMC2NVU_MSG5_PMC` | 0x20F4 | Inbound IPC Message 5, AGENT → NVU |
| `PMC2NVU_MSG6_PMC` | 0x20F8 | Inbound IPC Message 6, AGENT → NVU |
| `PMC2NVU_MSG7_PMC` | 0x20FC | Inbound IPC Message 7, AGENT → NVU |
| `PMC2NVU_MSG8_PMC` | 0x2100 | Inbound IPC Message 8, AGENT → NVU |
| `PMC2NVU_MSG9_PMC` | 0x2104 | Inbound IPC Message 9, AGENT → NVU |
| `PMC2NVU_MSG10_PMC` | 0x2108 | Inbound IPC Message 10, AGENT → NVU |
| `PMC2NVU_MSG11_PMC` | 0x210C | Inbound IPC Message 11, AGENT → NVU |
| `PMC2NVU_MSG12_PMC` | 0x2110 | Inbound IPC Message 12, AGENT → NVU |
| `PMC2NVU_MSG13_PMC` | 0x2114 | Inbound IPC Message 13, AGENT → NVU |
| `PMC2NVU_MSG14_PMC` | 0x2118 | Inbound IPC Message 14, AGENT → NVU |
| `PMC2NVU_MSG15_PMC` | 0x211C | Inbound IPC Message 15, AGENT → NVU |
| `PMC2NVU_MSG16_PMC` | 0x2120 | Inbound IPC Message 16, AGENT → NVU |
| `PMC2NVU_MSG17_PMC` | 0x2124 | Inbound IPC Message 17, AGENT → NVU |
| `PMC2NVU_MSG18_PMC` | 0x2128 | Inbound IPC Message 18, AGENT → NVU |
| `PMC2NVU_MSG19_PMC` | 0x212C | Inbound IPC Message 19, AGENT → NVU |
| `PMC2NVU_MSG20_PMC` | 0x2130 | Inbound IPC Message 20, AGENT → NVU |
| `PMC2NVU_MSG21_PMC` | 0x2134 | Inbound IPC Message 21, AGENT → NVU |
| `PMC2NVU_MSG22_PMC` | 0x2138 | Inbound IPC Message 22, AGENT → NVU |
| `PMC2NVU_MSG23_PMC` | 0x213C | Inbound IPC Message 23, AGENT → NVU |
| `PMC2NVU_MSG24_PMC` | 0x2140 | Inbound IPC Message 24, AGENT → NVU |
| `PMC2NVU_MSG25_PMC` | 0x2144 | Inbound IPC Message 25, AGENT → NVU |
| `PMC2NVU_MSG26_PMC` | 0x2148 | Inbound IPC Message 26, AGENT → NVU |
| `PMC2NVU_MSG27_PMC` | 0x214C | Inbound IPC Message 27, AGENT → NVU |
| `PMC2NVU_MSG28_PMC` | 0x2150 | Inbound IPC Message 28, AGENT → NVU |
| `PMC2NVU_MSG29_PMC` | 0x2154 | Inbound IPC Message 29, AGENT → N |


### Neural Network Accelerator (36 facts)

#### Neural Network Accelerator — Power Management

---

#### Overview (Chapter 9: NVU Power Management § 13.1)

- NVU is a **VNN-powered**, Chassis 2.2 compliant IP.
- Supports the **Resource Ownership** concept and the `resource_own_req` / `resource_own_ack` mechanism for resource ownership hand-off.
- Complies with the **Chassis 2.2** standard for sleep states management (§ 2.3).

---

#### Power Supply Architecture (§ 13.4)

- The **power switch** in the gated VNN domain operates on VNNAON to generate the `VNN_GATED` supply.
- **VNNAON** is also used to power SRAM memories.
- `VNN_GATED` is derived from VNNAON (not directly from VNN).

---

#### Power Domains — NPX6-1K Configuration (§ 8.4.2)

| Option Name | NVU Value | Description |
|---|---|---|
| `NPU_HAS_POWERDOMAINS` | 0 | No Per-Slice Power Domain |

---

#### NPX6-1K Clock Interfaces — CORE_ARCHIPELAGO Integration (§ 8.4.4)

| Interface | Port Name | Connectivity | Description |
|---|---|---|---|
| Clock | `npu_core_clk` | CRPM | Core Clock — connect to NPX Functional Clock (unused internally) |
| Clock | `npu_noc_clk` | CRPM | NoC Clock — connect to NPX Functional Clock |
| Clock | `sl0_clk` | CRPM | Slice Clock — connect to NPX Functional Clock |
| Clock | `sl0_wdt_clk` | CRPM | Watchdog Clock — connect to FUNC_CLK/16 |
| Clock | `arcsync_axi_clk` | CRPM | ARCSYNC AXI Clock — connect to NPX Functional Clock |
| Clock | `arcsync_clk` | CRPM | ARCSYNC Clock — connect to NPX Functional Clock |
| Clock | `pclkdbg` | CRPM | Debug Clock — connect to NPX Functional Clock / 2 |

---

#### NPX6-1K Reset Interfaces — CORE_ARCHIPELAGO Integration (§ 8.4.4)

| Interface | Port Name | Connectivity | Description |
|---|---|---|---|
| Reset | `npu_core_rst_a` | CRPM | Core Reset — connect to NPX Functional Reset (unused internally) |
| Reset | `npu_noc_rst_a` | CRPM | NoC Reset — connect to NPX Domain Functional Reset |
| Reset | `arcsync_axi_rst_a` | CRPM | ARCSYNC AXI Reset — connect to NPX Domain Functional Reset |
| Reset | `arcsync_rst_a` | CRPM | ARCSYNC Reset — connect to NPX Domain Functional Reset |

---

#### Lid-Open Standby (§ 13.2)

- NVU design differs from ISH (which is VNNAON-powered): NVU idle power (gated leakage) is significantly higher than ISH.
- The PM architecture targets avoiding any increase to baseline power consumption for **S0i2.1/S0i2.2** states.

---

#### Lid-Closed Standby (§ 13.3, § 6.1.1)

- During the **lid-close flow**, VNN is removed; prior to removal, NVU HW configurations are saved via the PMC save/restore mechanism.
- After VNN is removed during lid-closed entry, the subsequent behavior is analogous to a **global reset** flow.
- Once FW receives the `SLEEP_LVL_REQ` message from PMC, the response is returned to the SoC over a **`SleepRSP`** message.

---

#### PMC Save/Restore (§ 9.2.1.1)

- PMC save/restore occurs during the **lid-close and lid-open flow**.
- During lid-close, VNN is removed; NVU HW configurations (e.g., register state) must be saved before power removal.
- ROM checks **PMC save/restore done status** as part of extra ROM tasks at boot.
- **Reset Prep interrupt handling**: Reset Prep may occur when the power button is pressed while the system is in the S0 state; NVU ROM needs to handle the Reset Prep interrupt.
- **Security configuration** setup by NVU BUP includes: **IPC_DISABLE** (cuts off IPC communication between NVU and host) and **RS3_WR_DISABLE** (supports only one-way DMA from NVU).

---

#### LTR (Latency Tolerance Reporting) to PMC (§ 9.2.1.1, § 13.6.3.1)

- ROM must use **LTR messages** to communicate latency tolerance requirements to PMC with respect to DDR access:
  - Sets **2 ms LTR** to PMC **before** DMA operations.
  - Sets **infinite LTR value** to PMC **before** entering idle (post-DMA).
- NVU uses **QoS_DMD with RLTR type** to communicate latency tolerance toward DDR access (§ 13.6.3.1).

---

#### D0i1 — Trunk-Level Clock Gating Entry Flow (§ 13.7.4.1.2)

- **HW sequence for low-power entry:**
  - FW quiescence is sufficient for D0i1 entry.
  - VPX sleep ensures no outstanding transactions from VPX remain.
  - All remaining quiescence is guaranteed by FW.

---

#### Power Management Firmware Components (§ 13.5.4)

- **Peripheral drivers** are responsible for their own power state transitions.
- PM driver APIs are provided to assist peripheral drivers with power state management.
- **AON task** is located in **AONRF memory** (in the un-gated power domain) and handles **D0i2 and IPAPG** entry/exit flow, including saving/restoring VPX core registers and stack contents to/from AONRF.
- **Boot ROM** is executed when VPX core is brought out of reset; after checking power status saved in CRPM registers (indicating exit from IPAPG), execution jumps to the AON task to continue the restore flow.

---

#### BIOS Requirements — RTD3 Support (§ 6.8)

- To meet compliance requirements, BIOS must include **NVU D3hot** in the **PEP (Platform Extension Plugin) constraints**.

---

#### Local ART Timers (§ 8.8)

- NVU HW implements **three flavors of Local ART timers**: one running on the **XTAL clock**, one on the **PGCB 2.56 MHz clock**, and one on the **RTC 32 KHz clock**.
- NVU HW ensures that all three timers are running and synchronized.

#### DFx Power Considerations (§ 2.8.1)

- DFx features and functions are included in the **NVU DFX HAS** (refer to the DFX HAS section in references).

---

#### PMC IPC Sideband Register — PMC2NVU Doorbell (CRIF: nvu_PMC_IPC_IOSF_SideBand_Msg)

| Name | Bit | Reset | Access | Description |
|---|---|---|---|---|
| `PMC2NVU_DOORBELL_PMC.BUSY` | [31] | 0x0 | RW | Set by the AGENT to indicate a new message has been written in the payload registers. Cleared by FW once the message has been processed. |

---

#### NPX6-1K Neural Processor IP (§ 2.5.1.2)

- The **DesignWare® ARC® NPX Neural Processor IP** family provides a high-performance, power- and area-efficient solution for AI-enabled SoC applications.


### NoC Fabric (8 facts)

#### NoC Fabric Power Management

##### Capabilities
(2 Introduction > 2.5 Requirements > 2.5.1 Capabilities > 2.5.1.9 NOC Fabric > 2.5.1.9.1 Capabilities)

- The NoC fabric supports a **power-down/acknowledge protocol** to enable trunk-level clock gating and power gating flows.

---

##### Power Targets
(2 Introduction > 2.8 Power Targets > 2.8.1 Power Goals)

> Source for power targets: TTL AON DRD

| Use Case | Power Budget | Target FPS |
|---|---|---|
| Face Enrollment / Feature Extraction | 15 mW | 5 fps |
| Face Identification | 15 mW | 3 fps |

- Total memory budget referenced for this configuration: **3.0 MB**

---

##### Chassis 2.2 Support — Resources
(13 Power Management > 13.6 Chassis 2.2 Support > 13.6.1 Resources)

| IP Resource | Bit Number | PMU | IP → PMU RLTR | IP → PMU PRNDE | PMU → IP sleep_level_req | SoC Resource Description |
|---|---|---|---|---|---|---|
| peer_fabric | 7 | PMC | No | Yes | No | Peer Fabric |

---

##### CRPM Resource Mapping
(13 Power Management > 13.6 Chassis 2.2 Support > 13.6.1 Resources > 13.6.1.1 Resources Mapping to CRPM Register)

| CRPM Register | Resource | Assertion Condition | De-Assertion Condition |
|---|---|---|---|
| CRPM_RESOURCE_1_REQ | PEER_FABRIC | Before initiating peer cycles (over SIO to IPU/XHCI) | After completing peer cycles (over SIO to IPU/XHCI) |

- The `PEER_FABRIC` resource must be **asserted** prior to any peer transactions initiated over SIO to IPU or XHCI.
- The `PEER_FABRIC` resource must be **de-asserted** only after all peer transactions over SIO to IPU or XHCI have completed.


### PCI Configuration (2 facts)

#### Low Power Vision Subsystem (LPVS) Traffic Mapping

- In **TTL-H** configurations, LPVS traffic is mapped to **PSF6 VC0d** for XHCI-CAM DWB usage (HAS §6.2)
- This mapping requires **IOC to perform source decode** of downstream transactions in the IOC-to-LPVS direction (HAS §6.2)


### PMC Integration and Wake (128 facts)

#### PMC Integration and Wake

---

#### Overview
(13 Chapter 9: NVU Power Management > 13.1 Overview)

- NVU supports host wake via PME.
- Refer to NVU HAS: Power Management and NVU CRPM MAS for hardware architecture and design details.
- NVU implements Hammock Harbor (HH) support with PMC for accurate time distribution across platform components via an Always Running Timer (ART) in the Always Running Unit (ARU) in PMC. (2 Introduction > 2.5 Requirements > 2.5.1.22.1.1)

---

#### PMC Integration Checklist
(13 Power Management > 13.5 PMC Integration Checklist)

| Item | Value |
|---|---|
| ip_propsMembers | nvu |
| CUST | TTL-PCDH |
| Static Disable Capability | F, S, B |
| Static Disable | F, S, B |
| Reset Group | Host |
| HVM Reset Group | HVM_Host |
| Wake Signal Asserts | main |
| ForcePwrGatePOK | Yes |
| ForcePwrGatePOK Order | NA |
| Side POK Name | nvu |
| Side POK Status | nvu |
| Prim POK Name | nvu |
| Prim POK Status | nvu |
| IP_READY Status | nvu |
| BootPrep Early | No |
| BootPrep General | No |
| IP to be kept awake | No |
| ResetPrep (ResetEntry) | No |
| ResetPrep (Gen) | Yes |
| ResetPrep (LinkTurnOff) | No |
| ResetPrep (Shutdown) | No |
| Early_Boot Done | No |
| Vnn Resets | prim, side, pgcb |
| Reset Overrides Supported | No |
| SaveRestore | Yes |

---

#### NVU IPC Channels — PMC Integration Parameters
(2 Introduction > 2.5 Requirements > 2.5.1.12 IPC > 2.5.1.12.1 Overview)

NVU implements multiple IPC channels, each with its own dedicated register set. The channels relevant to PMC integration are listed below.

| Parameter | HOST | SPARE | CSE (Spare) | PMC (Telemetry) | CNVI (Spare) | ACE (Spare) | ESE | BT (Spare) | ISH |
|---|---|---|---|---|---|---|---|---|---|
| IPC_NAME | HOST | SPARE | CSE | PMC | CNVI | ACE | ESE | BT | ISH |
| IPC_TYPE | HOST | HOST | SEC | PEER | PEER | PEER | SEC | PEER | PEER |
| IPC_NUM_PAYLOAD_DOWNSTREAM | 32 | 32 | 32 | 32 | 32 | 32 | 32 | 32 | 32 |
| IPC_NUM_PAYLOAD_UPSTREAM | 32 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IPC_FWSTS | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| IPC_COMM | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| IPC_NUM_REMAP_REG | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IPC_NUM_UMA_REGIONS | 0 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| IPC_D0i3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IPC_MIA_RESET | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| IPC_CSR_REG | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

> **Note:** Validation is expected to cover IPC functionality for CSE, PMC, CNVI, ACE, and BT IPCs even though they are marked as SPARE, as functionality with these peer agents may be added in future. (2 Introduction > 2.5.1.12.1 Overview)

---

#### Telemetry Signals to PMC
(2 Introduction > 2.5 Requirements > 2.5.1.21 Telemetry Signals to PMC)

- NVU will send IP telemetry information to PMC for debugging purposes.
- NVU supports the `telemetry_service` bit as part of the C2.2 `Sleep_Level_Req` message from PMC. (HSD id: 16029771132)
- Support for IP Telemetry to PMC is marked as **rejected** in requirements tracking. (HSD id: 16027973436)

---

#### C2.2 Sleep State Support
(2 Introduction > 2.5 Requirements)

- NVU supports Chassis 2.2 sleep states management. (2 Introduction > 2.2 Block Diagram)
- NVU provides out-of-band chassis-compliant signals for clock and wakeup control. (2 Introduction > 2.2 Block Diagram)
- NVU supports C2.2 Sleep States (HSD id: 15017732834, status: POR).
- NVU supports HH with PMC (HSD id: 14026812782, status: POR).

---

#### NVU Enable and Disable via PMC
(6 NVU Requirements to BIOS > 6.2 NVU Enable and Disable)

- **Enable NVU:** Clear the NVU Static PG bit in PMC.
- **Disable NVU:** If NVU is not already in Static PG, set the NVU Static PG bit at `PWRMBASE + ST_PG_FDIS_PMC_2[NVU_FDIS_PMC]` in PMC. A global reset is required for the disable to take effect.
- **Put NVU into D3:** Program `PMCSR[1:0] = 2'b11` in NVU PCI configuration space.

---

#### NVU Power Management Configuration (BIOS Requirements)
(6 NVU Requirements to BIOS > 6.4 NVU Power Management Configuration)

- BIOS shall set **HAE (Hardware Autonomous Enable)** and **SLEEP_EN** to allow NVU to independently enter/exit IPAPG state.
- Write to NVU PMCTL register in NVU private config space:

| Register | Offset | Field | Value | Description |
|---|---|---|---|---|
| PMCTL | `PCR[NVU] + 1D0h` | `[5:0]` | `111111b` | Enable all PM control bits |
| SLEEP_EN | `PCI[NVU] + A2h` | `[3]` | `1b` | Enable SLEEP_EN |

---

#### RTD3 and PME Wake Support
(6 NVU Requirements to BIOS > 6.8 NVU RTD3 Support)

- BIOS shall report NVU wake capability and GPE in the ACPI table.
- ACPI wake method shall return: `GPRW(GPE1_NVU_PME_B0, 0x04)`
- ACPI device wake notify: `Notify(\_SB.PC00.NVUD, 0x02) // Device Wake`
- The ACPI `_PRW` object shall reference `NVUD` with wake value `0x02`.
- PME support tracked under HSD: `[TTL][NVU] Support for PME`.

---

#### Clocking — CRPM/PGCB
(5 Clocking > 5.1 Clocking Requirements > 5.1.1 Clock Distribution)

| Block | Clock Name | Source Clock | Frequency (MHz) |
|---|---|---|---|
| CRPM / SHIM / PGCB / CDC | CLK | nvu_func_clk | 200 |


### Peripheral Interfaces (31 facts)

#### Peripheral Interfaces

##### I2C Controllers

- NVU includes I2C controllers. The architecture is designed to be scalable so that additional controllers can be added with little effort. (HAS 2.5.1.15)
- All I2C controller instances operate in the **VNN power domain**. (HAS 4.3.12.2)
- I2C interface: Reference Interface Name **Non-Standard::I2C**, Interface Version **v1.0 r1.0**, Interface Side: **Consumer**, Reset Domain: **Not Defined**. (HAS 4.3.12.2)
- All I2C[0:N], I3C[0:N], and UART[0:N] blocks in the **MAIN partition** support both **CRPM Block Clock Gating (BCG)** and **CRPM Soft Reset (SR)**. (HAS 13.10)
- Upon completion of a task by a HW controller (e.g., I2C0), FW may choose to **clock-gate** that particular element to save power during D0i0 block-level clock gating flows. (HAS 13.7.3)

---

##### Camera Control Interface Sharing (I2C / I3C / GPIO)

For MIPI Camera, NVU and IPU share I2C/I3C pins for controlling the camera sensor configured for low power vision usage.

###### Pin Mux Configuration

- For **TTL-H** platforms, to enable NVU-based lower-power vision sensing, the MIPI UF RGB camera sensor shall be connected to **LPSS I2C0/I2C1/I3C0**, which are multiplexed with **NVU I2C0/I2C1/I3C**. (HAS 8.1.2)
- **NVU FW** is responsible for switching the PADMODE to select between **IPU** or **NVU** on the shared I2C/I3C pins. (HAS 6.7)
- GPIOs can be allocated as ad-hoc functional output pins for sensor reset, power control, etc. (HAS 8.1.2)

###### Release / Claim Handshake

- The **IPU sensor driver** controls the I2C and GPIO connected to MIPI cameras but has no direct SW interface to the IPU camera driver; therefore, the standard release/claim/owner handshake mechanism cannot be used. (HAS 8.21.5)
- In the platform, **16 virtual GPIOs (vGPIOs)** are allocated to establish a **4-way handshake** interface between the IPU sensor driver and NVU. (HAS 8.21.5)
- For HW design details refer to: *GPIO as Wake for sensor driver requesting/relinquishing shared I2C GPIO* in the NVU HAS. (HAS 6.7, 8.1.2)

**Handshake Flow — IPU Sensor Driver Requesting I2C Ownership:**

1. The IPU sensor driver writes to a vGPIO pin to assert **`release_req`**. (HAS 8.21.5)
2. The SoC routes this vGPIO output to another vGPIO input connected to an NVU GPIO, asserting that NVU GPIO. (HAS 8.21.5)
3. NVU HW triggers a **wake via GPIO**. (HAS 8.21.5)
4. NVU FW wakes and places the shared **I2C/GPIO into quiescent state**. (HAS 8.21.5)
5. NVU FW programs another NVU GPIO (connected to a vGPIO) to assert **`release_ack`**. (HAS 8.21.5)
6. The IPU sensor driver receives `release_ack` as a **GPIO toggle IRQ** via the associated vGPIO input. (HAS 8.21.5)
7. The IPU sensor driver is now free to take ownership of the shared I2C resource. It **de-asserts `release_req`**, and NVU subsequently **de-asserts `release_ack`**, completing the handshake. (HAS 8.21.5)

**NVU FW Release Behavior (Host or IPU-initiated):**

- When a release request is received from either the **IPU** (via PHY Sharing) or **host software** (via vGPIO), NVU FW shall:
  - Close and power off the UF RGB camera sensor
  - Release I2C/I3C bus ownership
  - Acknowledge the release as soon as possible (HAS 8.1.2)

---

##### RTD3 Support — ACPI Methods

The following ACPI control methods are required in the BIOS for NVU RTD3 support. (HAS 6.8)

| Method | Signature | Description |
|---|---|---|
| `_S0W` | `Method (_S0W, 0, NotSerialized)` | Returns `0x03`; defines the deepest D-state from which the device can wake the system during S0 |
| `_PRW` | `Method (_PRW, 0, NotSerialized)` | Sets the GPE event as the device wake power resource; references `GPRW(GPE1_N, ...)` |
| `_L94` | `Method (_L94, 0, Serialized)` | GPE handler; issues `Notify(\_SB.NVUD, ...)` to signal ACPI device wake event (logged as "L94 Event") |

- The `_PRW` method returns a power resource package referencing the **GPE1_N** event number. (HAS 6.8)
- The `_L94` handler is serialized and notifies the `\_SB.NVUD` ACPI device object upon GPE assertion. (HAS 6.8)

---

##### Reset Prep Interrupt Handling

- **Reset Prep** may occur when the power button is pressed while the system is in the **S0 state**. (HAS 9.2.1.1)
- NVU **ROM** must handle the Reset Prep interrupt as part of its extra ROM tasks during the boot flow. ROM will check if the Reset Prep condition is active and respond accordingly. (HAS 9.2.1.1)


### Power States (50 facts)

#### Power States

#### Overview

NVU supports multiple power states to enable aggressive platform-level power management. Power management requires close coordination between the AON task, Boot ROM, PM driver, and peripheral drivers to achieve various low-power states and support transition flows. (13 Chapter 9: NVU Power Management > 13.5 Firmware Components and Roles)

The following table summarizes the power states supported by NVU. Refer to NVU HAS: Behavior in Various Power States for detailed power saving features used in each state. (13 Chapter 9: NVU Power Management > 13.4 Power States)

| Power State | Description |
|---|---|
| D0i0 | NVU is in DAQ (Data Acquisition) or VPX/NPX execution from SRAM; block-level clock gating; SRAM auto retention by HW; RLTR: Infinite (default) or 2ms (RS3 DMA) |
| D0i1 | NVU FW enters IDLE loop with no activity; Time to Next Event allows D0i1 entry; trunk-level clock gating; SRAM auto retention by HW |
| D0i2 | NVU FW enters IDLE loop with no activity; Time to Next Event allows D0i2 entry; MAIN PD: IPAPG; USB and MIPI PD: PG; SRAM in retention by FW; PGCB clock gating |
| Shutdown | NVU not operational, VNN de-asserted to allow VNN removal; entered when lid is closed; MAIN PD: IPAPG; USB and MIPI PD: PG; SRAM in retention by FW |

> **Note:** D0i3 has been removed from NVU power state support. (13 Power Management > 13.7 Power Management Flows > 13.7.4 D0i1 > 13.7.4.2 D0i1 Exit Flow)

---

#### Behavior in Various Power States

(13 Power Management > 13.2 Behavior in Various Power States)

| Attribute | D0i0 | D0i1 | D0i2 |
|---|---|---|---|
| SubState | FW Paging | — | Shutdown |
| Main PD | On | Trunk CG | IPAPG |
| USB PD | On | PG | PG |
| Clocks | On Demand | Trunk-Level Clock Gated | Off (PGCB gated) |

- **Block-level clock gating** is used in the D0i0 state, with SRAM auto retention by HW. (13 Power Management)
- **Trunk-level clock gating** is used in the D0i1 state. (13 Power Management)
- In D0i2, PGCB clock gating is used to achieve lower power. The VNN handler FSM was moved from RTC to the PGCB clock domain; PGCB does not need to remain on in D0i2 and can be OFF during VNN removal to minimize power. (13 Power Management > 13.2 Behavior in Various Power States)

---

#### D0i0 — Block-Level Clock Gating

(13 Power Management > 13.7 Power Management Flows > 13.7.3 D0i0 - Block Level Clock Gating Flow)

- To enable block-level clock gating, NVU FW must program `CRU_BLK_CG_DIS.BLK_CG_DIS` to `0x0`.

---

#### D0i1 — Trunk-Level Clock Gating

(13 Power Management > 13.7 Power Management Flows > 13.7.4 D0i1 - Trunk Level Clock Gating)

- D0i1 entry involves HW performing low-power entry via trunk clock gating (TCG).
- D0ix with PGCB clock gating (PGCBCG) is supported. (13.7.4.1.2 HW performs low power entry)
- **D0i1 Exit:** The D0ix/IPAPG entry/exit flow applies to both the ISP and USB partitions. (13.7.4.2 D0i1 Exit Flow)

---

#### Lid-Closed Standby

(13 Chapter 9: NVU Power Management > 13.3 Lid-Closed Standby)

NVU implements an aggressive platform-level power management policy when the system lid is closed. This state is distinct from Modern Standby (S0ix). (9 Chapter 5 > 9.1.3 VNN Removal in Lid Close State Requirements)

**Requirements:**

- NVU is **not operational** when the lid is closed and shall support VNN removal to release all resources including VNN. (13.3 Lid-Closed Standby)
- NVU is **operational** when the lid is opened and will keep VNN resource requested. (6 Voltage Domains > 6.1 Lid Closed vs Lid Open)
- Boot design must accommodate and handle the corresponding lid-close vs. lid-open flow. (9.1.3 VNN Removal in Lid Close State Requirements)

**Lid-Closed Standby Trigger:**

- PMC sends `sleep_level_req(vision_service = 0)` to NVU to allow VNN removal during lid-closed condition. The system does not need to be in Modern Standby for this to occur. (13.3 Lid-Closed Standby)

**Chassis 2.2 / vision_service Mapping:**

| IP Service | Bit Number | sleep_level_req(resource=0) Condition | sleep_level_req(resource=1) Condition |
|---|---|---|---|
| vision_service | 1 | Lid Closed Entry (VNN Removal) | Lid Open |

(13 Power Management > 13.6 Chassis 2.2 Support > 13.6.2 Services)

**VNN Resource (CRPM):**

| CRPM Register | Resource | Assertion | De-Assertion |
|---|---|---|---|
| CRPM_RESOURCE_0_REQ | VNN | Register unused; HW Controlled; Refer Lid-Closed/Open Flows | Register unused; HW Controlled; Refer Lid-Closed/Open Flows |

(13 Power Management > 13.6 Chassis 2.2 Support > 13.6.1.1 Resources Mapping to CRPM Register)

- Refer to TTL Lid Closed Standby Overview for additional platform-level details. (13.3 Lid-Closed Standby)

---

#### Lid-Closed/Lid-Open Transition Flows

(6 Voltage Domains > 6.1 Lid Closed vs Lid Open > 6.1.1 Transition Flows)

- Lid-close and lid-open transitions follow a defined flow; transition flows for NVU are similar across lid-close entry and exit.
- All POKs (prim/side/pgcb) and resets (prim/side/pgcb) are asserted during lid-closed entry.
- Restore order for each block is captured in OSXML; there is no special handling required for RO registers during restore. (6.1.1 Transition Flows)

**Save and Restore:** (6 Voltage Domains > 6.1 Lid Closed vs Lid Open > 6.1.2 Save and Restore)

- For FW, the VNN removal flow appears like an IP reset. When the lid is closed, all content in SRAM will be lost, and after lid-open, FW will reboot from ROM.
- NVU **must re-download FW** after VNN removal.
- IPC ESE and ISH IPC Channels, IOSF2AXI PCI Config registers, and Bridge Private Registers are saved and restored by PMC.

**VNN Removal Boot Flow:** (9 Chapter 5 > 9.2 NVU Firmware Boot Flow > 9.2.4 VNN Removal Flow)

- The VNN removal lid-close → lid-open flow is identical to the cold boot flow, traversing ROM, BUP, and FW stages.
- ROM supports power management during lid-close/lid-open flow as an extra ROM task. On IPAPG exit, ROM checks power status saved in CRPM registers which indicates it is an exit from IPAPG; if so, execution jumps to the AON task to continue the IPAPG exit flow. (9.2.1.1 Extra ROM tasks)
- BUP checks the sleep level request interrupt status at startup and transitions to IPAPG if a lid-close event has occurred. (9.2.2.1 Extra BUP tasks)

**Host Wake on Lid-Open:** (13 Power Management > 13.8 Host Wake Flow)

- NVU FW wakes up the host during Lid-Closed → Lid-Open transition to trigger FW reload.
- NVU FW also issues host wake during exception reset cases where FW re-load is required.

---

#### BIOS Requirements

(6 NVU Requirements to BIOS > 6.8 NVU RTD3 Support)

- **REQ:** BIOS shall expose the PEP constraint as **D3hot** for the NVU device.

---

#### Requirements Tracking

(2 Introduction > 2.5 Requirements)

| Requirement ID | Title | Status |
|---|---|---|
| 14024260079 | Lid-closed standby power optimization | Rejected |
| 16028072658 | [TTL PCD-H] NVU Power Optimization in Lid Closed State | POR |


### Register Details (2 facts)

#### D0i3 Max Power On Latency Register

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| D0i3 Max Power On Latency | NVU PCI Config Space | — | — | Specifies the maximum power-on latency for D0i3 power state transitions |

- Write operations to the D0i3 Max Power On Latency register must be performed in the NVU PCI configuration space (HAS 6.4 NVU Power Management Configuration)
- This register is configured by BIOS as part of NVU power management initialization (HAS 6 NVU Requirements to BIOS > 6.4)

---

#### Security Registers (SEC_REG) — Power Flow Behavior

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| Security Registers (SEC_REG) | — | — | No reset on power-flow | Registers holding security state that must persist across NVU power transitions |

- Security registers **must not** be reset or lose state during any NVU power-flows, including IPAPG (Intellectual Property Active Power Gating) sequences (HAS 2.5.1.13 Security Registers)
- Preservation of SEC_REG state is a mandatory capability requirement for NVU power management compliance (HAS 2 Introduction > 2.5.1 Capabilities)


### SRAM and Memory (23 facts)

#### SRAM Overview

- The NVU SRAM sub-system has a total size of **3584 KB** (HAS 2.8.1)
- NVU HW provides the following SRAM-related power saving capabilities (HAS 13.1):
  - SRAM retention by FW
  - SRAM run-time power management
  - IP Accessible Power Gating (IPAPG)
  - Truck level Clock Gating (TCG)
  - Block level Clock Gating (BCG)
  - PGCB clock gating

---

#### SRAM Power Management — FW Override

- FW can place any SRAM slice (all banks within a slice) into **deep sleep** or **shut down** state (HAS 2.5.1.7.2)
- SRAM retention is managed by FW as part of the D0i2 low-power entry flow (HAS 13.1)

---

#### SRAM Behavior During VNN Removal (Lid Close/Open)

- **FW perspective:** The VNN removal flow appears as an IP reset. When the lid is closed, **all SRAM content is lost**. After lid-open, FW will reboot from ROM. (HAS 9.2.4)
- **SW perspective:** During lid-close/lid-open, the NVU PCI device is reset; the driver is reloaded and re-enumerated. (HAS 9.2.4)

---

#### SRAM and D0i2 (Trunk Level Clock Gating with IPAPG)

- In the D0i2 + IPAPG entry flow, **PGCBCG is mandatory** (HAS 13.7.5.1.2)
- FW must program the `CRPM_IPAPG_EN` register as part of D0i2 with IPAPG entry (HAS 13.7.5.1.2)

---

#### SRAM and D0i3 / RTD3 Context Save Constraint

- During D0i3 with IPAPG entry, if FW needs to save context, the IMR region is **not writable** (`RS3_WR_DISABLE` is set after BUP loading), constraining context save options. (HAS 13.7.6)

---

#### Block Level Clock Gating — SRAM Partition

| Partition | Block | CRPM BCG | CRPM SR |
|-----------|-------|----------|---------|
| SRAM      | SHA   | Y        | Y       |

(HAS 13.10)

---

#### PMC–NVU IPC Interrupt Registers (SRAM/Memory Context)

##### Register: `PISR_PMC2NVU` — Peripheral Interrupt Status (IRQ to NVU)

| Name            | Offset       | Size    | Reset | Reset Signal | Description                                              |
|-----------------|--------------|---------|-------|--------------|----------------------------------------------------------|
| PISR_PMC2NVU    | 0x0000002000 | 32 bits | —     | FUNCRST      | Contains inbound interrupt status bits for PMC-to-NVU messages (HAS CRIF) |

---

##### Register: `PIMR_PMC2NVU` — Peripheral Interrupt Mask (IRQ to NVU)

| Name         | Offset       | Size    | Reset | Reset Signal | Description                                                         |
|--------------|--------------|---------|-------|--------------|---------------------------------------------------------------------|
| PIMR_PMC2NVU | 0x0000002004 | 32 bits | —     | FUNCRST      | Enables or disables inbound interrupts from AGENT to NVU (HAS CRIF) |

**Fields:**

| Field Name          | Bits  | Reset  | Access | Description                                                                                                          |
|---------------------|-------|--------|--------|----------------------------------------------------------------------------------------------------------------------|
| AGENT2NVU_DB        | [0]   | 0x0    | RW     | Mask bit for inbound AGENT2NVU Doorbell BUSY interrupt. Written by NVU FW only. `1` = interrupt unmasked. (HAS CRIF) |
| RESERVED2           | [10:1]| 0x000  | RO     | Reserved. (HAS CRIF)                                                                                                 |
| NVU2AGENT_BC        | [11]  | 0x0    | RW     | Mask bit for NVU2AGENT doorbell busy clear interrupt. Written by NVU FW only. `1` = interrupt unmasked. (HAS CRIF)   |
| RESERVED1           | [26:12]| 0x0000| RO     | Reserved. (HAS CRIF)                                                                                                 |
| AGENT2NVU_BCISC     | [27]  | 0x0    | RW     | Mask bit for AGENT2NVU Busy Clear Interrupt Status Clear interrupt. Written by NVU FW only. `1` = interrupt unmasked. (HAS CRIF) |
| RESERVED0           | [31:28]| 0x0   | RO     | Reserved. (HAS CRIF)                                                                                                 |


### Secure Boot (2 facts)

#### Secure Boot – Power Management Context

##### D0i3 Max Power-On Latency (6 NVU Requirements to BIOS > 6.4 NVU Power Management Configuration)

- BIOS is required to configure the **D0i3 Max Power-On Latency** value as part of NVU power management initialization.

##### Additional References (13 Power Management)

- Detailed specifications for each power management feature, including D0i3 configuration parameters, are documented in the **power management related MAS documents** available on the NVU SharePoint.


### USB Camera Interface (1 facts)

#### Block-Level Clock Gating & Soft Resets — USB Camera Interface

The USB partition includes the MJPEG decoder (MJPEGDEC) block, which supports both Clock Gate and Soft Reset controls managed by the CRPM (Clock and Reset Power Manager), with behavior conditioned by fuse configuration.

(HAS §13.10 Block Level Clock Gating & Soft Resets)

| Partition | Block | CRPM BCG | CRPM SR |
|-----------|-----------|------------|----------|
| USB | MJPEGDEC | Y (Fuse) | Y (Fuse) |

- **Clock Gating (BCG):** The MJPEGDEC block supports CRPM-controlled block-level clock gating; availability is conditioned on fuse state
- **Soft Reset (SR):** The MJPEGDEC block supports CRPM-controlled soft reset; availability is conditioned on fuse state
- Both BCG and SR capabilities are gated by fuse configuration — if the corresponding fuse is not set, the CRPM will not assert clock gate or soft reset control for this block


### Voltage Domains (10 facts)

#### Voltage Domain Overview

NVU operates as a VNN-powered, Chassis 2.2 compliant IP block, capable of functioning under S0 and S0ix power states. (5.2 NVU Introduction)

#### Voltage Domain Definitions

| Domain Name | Description |
|---|---|
| VNN | VNN ungated rail supplied by SoC |

(6 Voltage Domains)

#### Power Supply Specifications

| Logical Port Name | Supply Port | Nominal Voltage | Comments |
|---|---|---|---|
| VNN | vcc | 0.75V | VNN supply |
| VSS | vss | 0.00V | Ground |

(13 Power Management > 13.4 Power Supply)

#### Gated and Ungated Power Domains

- NVU has both a **gated VNN power domain** and an **ungated VNN power domain**. (13 Power Management > 13.3 Power Domains)
- NVU supports the `resource_own_req/resource_own_ack` mechanism for resource ownership hand-off. (6 Voltage Domains) (6 Voltage Domains)

#### VNN Removal and Restore

- PMC sends `sleep_level_req(vision_service = 0)` to NVU to allow VNN removal during lid-closed condition.

- NVU supports **VNN Removal** and **VNN Restore**, and participates in Save/Restore flows for context preservation. For FW, the VNN removal flow appears like an IP reset; when the lid is closed, all content in SRAM will be lost, and after lid-open, FW will reboot from ROM. NVU saves the following registers to PMC during VNN removal: IPC ESE and ISH IPC Channels, IOSF2AXI PCI Config registers, and Bridge Private Registers. (13 Chapter 9: NVU Power Management > 13.1 Overview)

#### Lid-Open Standby Constraints

- When the lid is open and NVU is enabled, the system can only enter up to **S0i2.0** during lid-open standby; S0i2.1/S0i2.2 cannot be entered. (13 Chapter 9: NVU Power Management)
- Lid-Open Standby is limited to **S0i2.0** and cannot transition deeper to S0i2.1 or S0i2.2. (13 Chapter 9: NVU Power Management > 13.2 Lid-Open Standby)
- NVU **cannot allow VNN removal** in the Lid-Open Standby state, as the Low Power Vision Subsystem (LPVS) must remain active for the Wake On Human Presence feature. (13 Chapter 9: NVU Power Management > 13.2 Lid-Open Standby)
- When the lid is **closed**, NVU is expected not to be operational and VNN is de-asserted to allow VNN removal. The Wake On Human Presence feature is not supported, and the Low Power Vision Subsystem (LPVS) is deactivated. (5.2 NVU Introduction)

#### Zephyr OSPM Device Power Management Actions

The following device power management actions are defined for NVU integration with Zephyr OSPM: (13 Chapter 9: NVU Power Management > 13.6 Zephyr OSPM Integration > 13.6.0.2 Device Power Management)

- `PM_DEVICE_ACTION_SUSPEND` — Suspend the device
- `PM_DEVICE_ACTION_RESUME` — Resume the device
- `PM_DEVICE_ACTION_TURN_OFF` — Turn off the device (action triggered only by a power domain event)

