name: fv-nvu/debug
description: NVU debug interfaces, RAS (ECC, watchdog), DTF firmware trace, VISA observability, telemetry, and error reporting

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# NVU Debug and RAS

> **SAFETY**: Do NOT modify debug registers, trigger ECC scrubs, or alter watchdog configuration without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.

## Overview

The NVU provides debug and RAS (Reliability, Availability, Serviceability) capabilities for post-silicon validation and runtime error recovery. The debug subsystem spans multiple interfaces:

- **VISA** — On-chip signal observability (VISA2 architecture) for post-Si debug
- **DTF** (Debug Trace Fabric) — FW instrumentation trace output to Intel Trace Hub (NorthPeak) via MIPI Sys-T protocol
- **OCD / sTAP** — On-Chip Debugger access to VPX2 core via secondary TAP port
- **NPX6 Debug Port** — CoreSight-compatible debug registers for NPX6-1K (ROM Table, ARC Trace, L1 Core debug)
- **Watchdog Timer (WDT)** — Two-stage timeout for FW hang detection and recovery
- **SRAM ECC** — SECDED (Single Error Correct, Double Error Detect) on all SRAM slices
- **Telemetry** — IP telemetry push to PMC via Chassis 2.2 sideband

NVU is **not** intended for safety-critical applications. The RAS features provide basic infrastructure to improve overall FIT rate of the SoC (HAS Section 12).


## Debug Interfaces

### VISA (HAS Section 15.2)

The NVU IP provides signals visible at VISA pins for post-Si debug. The subsystem implements VISA architecture (Interface Type: dft, Version v1.0 r1.0).

**VISA Interface Signals** (from HAS Section 4.3.6.1):

| Signal | Direction | Width | Power Domain | Description |
|--------|-----------|-------|-------------|-------------|
| `nvu_avisa_clk` | output | 1 | VNN | Agent VISA Debug bus clock |
| `nvu_avisa_dbgbus` | output | 32 | VNN | Agent VISA Debug bus (sync to `nvu_fvisa_serstrb`, rising edge) |
| `nvu_fvisa_frame` | input | 1 | VNN | Fabric VISA frame |
| `nvu_fvisa_startid` | input | 9 | VNN | Fabric VISA start ID |
| `nvu_fvisa_endid` | input | 9 | VNN | Fabric VISA ending ID |
| `nvu_fvisa_startid_1` | input | 9 | VNN | Fabric VISA start ID (second) |
| `nvu_fvisa_endid_1` | input | 9 | VNN | Fabric VISA ending ID (second) |
| `nvu_avisa_serial_rd_data_out` | input | 1 | VNN | VISA Serial RD Data |
| `bypass_cr_out` | output | 4 | VNN | VISA bypass control register output (Integration HAS v0.8) |

All VISA signals are referenced to `nvu_fdfx_powergood` reset.

**VISA Color Levels** (from IOSF2AXI bridge parameters):

| Parameter | Value |
|-----------|-------|
| `IOSF2AXIBR_DFX_VISA_RED` | `2'h0` |
| `IOSF2AXIBR_DFX_VISA_GREEN` | `2'h1` |
| `IOSF2AXIBR_DFX_VISA_ORANGE` | `2'h2` |
| `IOSF2AXIBR_DFX_VISA_BLACK` | `2'h3` |

> NVU HW VISA does **not** use the DTF packetizer/encoder interface (HAS Section 15.5.1.3).

### On-Chip Debugger / TAP (HAS Section 15.2, 15.7)

Post-silicon debug can utilize the **On-Chip Debugger (OCD)** to access the VPX2 core using its sTAP connected to the **secondary TAP port**.

- NVU is connected to the TAP network via Chassis sTAP
- All DFx features are enabled via the **DFx secure plugin** and only via the plugin
- DFx secure plugin provides security for both **VISA** and **NPX core debug access**
- The `secure_policy_matrix` of the DSP is exposed at NVU top level for product-specific configuration
- The plugin resides in the **lowest power well** of the IP

Additional TAP capabilities (HAS Section 15.7):
- TAP controls power enables to SRAM
- TAP contains test data registers to program **survivability feature of DTF**
- TAP controls debug channel selection of DMA controller

### JTAG Interface (Integration HAS v0.8, Section 4)

> Source: SIP NVU1.0 Integration HAS v0.8, Section 4.3. JTAG v1.0 r1.2 compliant.

| Signal | Direction | Width | Description |
|--------|-----------|-------|-------------|
| `nvu_vpx2_jtag_tck` | input | 1 | VPX2 JTAG clock (50 MHz) |
| `nvu_main_stap_tck` | input | 1 | MAIN sTAP clock |
| `nvu_vpx2_trstn` | input | 1 | VPX2 JTAG test reset (active low) |
| `nvu_main_trstn` | input | 1 | MAIN sTAP test reset (active low) |
| `nvu_vpx2_jtag_tms` | input | 1 | VPX2 JTAG test mode select |
| `nvu_main_tms` | input | 1 | MAIN sTAP test mode select |
| `nvu_vpx2_jtag_tdi` | input | 1 | VPX2 JTAG test data in |
| `nvu_main_tdi` | input | 1 | MAIN sTAP test data in |
| `nvu_vpx2_tdo` | output | 1 | VPX2 JTAG test data out |
| `nvu_main_tdo` | output | 1 | MAIN sTAP test data out |
| `nvu_vpx2_tdo_en` | output | 1 | VPX2 TDO output enable |
| `nvu_main_tdo_en` | output | 1 | MAIN sTAP TDO output enable |
| `SLVIDCODE` | — | 32 | JTAG IDCODE (Silicon Lifecycle Vendor ID Code) |

All JTAG signals are in the VNN power domain.

### VPX2 Halt-On-Reset (HAS Section 8.3.5.1)

For ROM debug, VPX2 supports halt-on-reset:

1. Set `NVU_VPX_HALT_Fuse` to `1` — HW will not bring VPX2 out of reset
2. From debugger, download reset code to alternate R/W memory (e.g., AONRF)
3. Update reset vector within VPX2 to point to AONRF
4. Put core to RUN state from the debugger

### NPX6-1K Debug Configuration

Per HAS Section 8.4.2:

| Option | NVU Value | Description |
|--------|-----------|-------------|
| `NPU_ARC_TRACE` | CoreSight | ARC Trace — not supported on NVU |
| `NPU_SAFETY_LEVEL` | 0 | No safety mechanisms support |
| `NPU_MEM_ECC` | 0 | No ECC support on L1 memory |
| `dbg_en_option` | FALSE | Debug interface disabled by default |

NPX6 debug access via ARCSYNC:

| Signal | Connection | Description |
|--------|------------|-------------|
| `arc_halt_req_a` | ARCSYNC | Run control halt request |
| `pclkdbg` | CRPM | Debug clock — connect to NPX functional clock / 2 |
| APB Debug (`arct0_p*`) | Fabric | Debug APB port |
| Debug Security (`sl0nl1arc_niden`, `sl0nl1_dbgen`) | DFX | Connect to DFx Secure Plugin (slice DBGEN, NIDEN) |


## NPX6 Debug Memory Map (HAS Section 8.2.3.2)

Base address: `0xF620_0000` (NPX_DEBUG region, 256KB: `0xF6200000`–`0xF6240000`)

| Region | Start Address | Size | Target |
|--------|--------------|------|--------|
| ROM Table | `0xF620_0000` | 4KB | ROM Table |
| ARC Trace | `0xF620_1000` | 4KB | ARC Trace |
| L1 Core | `0xF620_2000` | 4KB | L1 Core |

### ROM Table Registers (at ROM Table base)

| Register | Offset | Mode | Description |
|----------|--------|------|-------------|
| Rom Entry | `0x000` | R | ARC Trace @ offset 0x1 |
| Rom Entry | `0x004` | R | L1 Core0 @ offset 0x2 |
| Rom Entry | `0x008` | R | All Zeros — end of entries marker |
| CLAIMSET | `0xFA0` | RAZ/WI | Claim Tag Set register |
| CLAIMCLR | `0xFA4` | RAZ/WI | Claim Tag Clear register |
| AUTHSTATUS | `0xFB8` | R | Authentication Status register |
| DEVARCH | `0xFBC` | R | Device Architecture register |
| DEVTYPE | `0xFCC` | R | Device Type Identifier register |
| CIDR0 | `0xFF0` | R | Preamble 0 (`0x0D`) |
| CIDR1 | `0xFF4` | R | Component class (`0x9` — CoreSight component) |
| CIDR2 | `0xFF8` | R | Preamble 2 (`0x05`) |
| CIDR3 | `0xFFC` | R | Preamble 3 (`0xB1`) |

### ARC Trace / L1 Core Debug Registers (at ARC Trace and L1 Core bases)

| Register | Offset | Description |
|----------|--------|-------------|
| `DB_STAT` | `0x000` | Debug Status register |
| `DB_CMD` | `0x004` | Debug Command register |
| `DB_ADDR` | `0x008` | Debug Address register |
| `DB_DATA` | `0x00C` | Debug Data register |
| `DB_RESET` | `0x010` | Debug Reset register |
| ITCTRL | `0xF00` | Integration Mode Control — not used, RAZ |
| CLAIMSET | `0xFA0` | Claim Tag Set register (R/W) |
| CLAIMCLR | `0xFA4` | Claim Tag Clear register (R/W) |
| DEVAFF0 | `0xFA8` | Device Affinity register 0 — not used, RAZ |
| DEVAFF1 | `0xFAC` | Device Affinity register 1 — not used, RAZ |
| LAR | `0xFB0` | Lock Access register — not implemented, RAZ |
| LSR | `0xFB4` | Lock Status register — not implemented, RAZ |
| AUTHSTATUS | `0xFB8` | Authentication Status register |


## Debug Trace Fabric (DTF v1.4) — HAS Section 15.5

NVU includes a DTF source packetizer and encoder to support FW instrumentation trace output to **Intel Trace Hub (NorthPeak)**, even in S0ix state. FW trace messages use **MIPI Sys-T** format. DTF interface version: **v1.4** (Integration HAS v0.8, Section 14).

### DTF Register Target

| Block | Base Address | End Address | Size |
|-------|-------------|-------------|------|
| DTF | `0xF3400000` | `0xF3401000` | 4KB |

### DTF Architecture

The DTF path consists of:
1. **DTF-Source-Packetizer** — register target accessible by NVU FW to push debug messages
2. **DTF Encoder** — sub-IP instantiated in NVU, inserts HW timestamps (NVU local ART value)
3. **DTF Arbiter** — external topology targeting the **Trace Aggregator**

Key properties:
- FW debug messages are transferred **losslessly** and **in-order** end-to-end on DTF fabric
- NVU supports only **D64TS**, **D64**, and **D64M** packet types
- DMA mode of operation is **deprecated**
- FW-inserted timestamping is **deprecated** — only HW-inserted timestamping is supported
- Timestamp value is NVU's local ART value (`NVU_local_art_value[55:0]`)

#### DTF Pipeline Diagram (Source: HAS SVG — DTF Block Diagram)

```
FW Register Write                    NVU Internal                         External (SoC)
─────────────────                    ────────────                         ──────────────
                                     ┌────────────────┐
 D64TS_LO/HI_ADDR ──►               │  Source        │
 DATA_WITHOUT_EOP  ──►               │  Packetizer    │    ┌─────────┐    ┌──────────────┐
 DATA_WITH_EOP     ──►               │  (SRCPKT)      │───►│  DTF    │───►│  DTF         │
                                     │  - D64TS hdr   │    │ Encoder │    │  Arbiter     │
                                     │  - Concatenate  │    │ (SRCENC)│    │  (External)  │
                                     │    2×32b→64b   │    │ - HW TS │    │              │
                                     │  - Pad if odd  │    │ - CG    │    └──────┬───────┘
                                     └────────────────┘    └─────────┘           │
                                                                                 ▼
                                                                    ┌──────────────────┐
                                                                    │ Trace Aggregator │
                                                                    │ → NorthPeak/ITH  │
                                                                    └──────────────────┘
```

#### DTF Packet Format — STP D64TS with Sys-T Header (Source: HAS SVG)

The FW writes a **Sys-T Event Header** as the D64TS payload:

| Field | Bits | Description |
|-------|------|-------------|
| `Type` | 4 | Message type (e.g., 0x1 = Build, 0x2 = Short, 0x3 = String, 0x6 = Catalog) |
| `Severity` | 3 | Severity level (0 = Max/Fatal → 6 = Debug) |
| `Unit` | 11 | Sub-module unit identifier (assigned by FW per service) |
| `ModuleID` | 16 | Module identifier (FW component: DSP Service, Vision Service, PM Service, etc.) |
| `SubType` | 6 | Sub-type within message type |
| Reserved | — | Remaining bits per Sys-T spec |

> **Key**: The HW Encoder inserts the 56-bit `NVU_local_art_value` timestamp — FW does NOT insert timestamps.

#### Complete FW Trace Register Write Sequence (Source: HAS SVG — DTF FW Trace)

| Step | Register / Action | Description |
|------|-------------------|-------------|
| 1 | `PCKTZR_DTF_SRC_CONFIG.SRC_EN = 1` | Enable source packetizer |
| 2 | Poll `SRC_STATUS.ENC_ACTIVE == 1` | Wait for encoder to become active |
| 3 | Write `D64TS_HI_ADDR` | Upper 32 bits of Sys-T header |
| 4 | Write `D64TS_LO_ADDR` | Lower 32 bits of Sys-T header (triggers D64TS packet start) |
| 5 | Write `DATA_WITHOUT_EOP` (N times) | Push 32-bit data chunks (SRCPKT concatenates pairs → 64-bit D64 packets) |
| 6 | Write `DATA_WITH_EOP` | Push final 32-bit chunk + signal End-Of-Packet (D64M packet type) |
| 7 | (Repeat 3–6) | Continue for next trace message |

> **Warning**: If an odd number of 32-bit chunks are written before EOP, SRCPKT pads the last 64-bit word with zeros.

#### Debug Flow Diagram (Source: HAS/FAS SVG — Pre/Post-EOM Debug Paths)

```
                    ┌──────────────────────────────────────────────┐
                    │             NVU Debug Sources                 │
                    ├──────────────────────────────────────────────┤
                    │ FW Log (DTF)  │ Probe/Telemetry │ HECI Debug │
                    │ (Sys-T msgs)  │ (PMC counters)  │ (Host CLI) │
                    └───────┬───────┴────────┬────────┴──────┬─────┘
                            ▼                ▼               ▼
                    ┌───────────────────────────────────────────────┐
                    │          Pre-EOM (Before OS Boot)             │
                    │  • FTDI UART/I2C console (UART0/I2C0)        │
                    │  • JTAG/OCD via sTAP                         │
                    │  • NPK trace (DTF → Trace Hub → NorthPeak)   │
                    │  • Image dump to DRAM (debug mode)            │
                    │  • Profiling counters (FW reads VPX/NPX PMU) │
                    └───────────────────────────────────────────────┘
                    ┌───────────────────────────────────────────────┐
                    │          Post-EOM (After OS Boot)             │
                    │  • HECI Debug Client (host-side CLI)          │
                    │  • DTF trace (same path, host-triggered)      │
                    │  • PMC telemetry (via SLR sideband)           │
                    │  • Crash dump (AONRF + SRAM snapshot)         │
                    │  • NPK tools (Intel Trace Hub analyzer)       │
                    └───────────────────────────────────────────────┘
```

> **Source**: HAS/FAS SVGs `nvu_debug.*` — debug flow diagrams with Pre/Post-EOM paths.

### DTF External Signals (HAS Section 4.3.6.2, Integration HAS v0.8 Section 14)

| Signal | Direction | Width | Description |
|--------|-----------|-------|-------------|
| `nvu_dnstream_header_out` | output | 25 | DTF downstream header |
| `nvu_dnstream_data_out` | output | 64 | DTF downstream data |
| `nvu_dnstream_valid_out` | output | 1 | DTF downstream valid |
| `nvu_upstream_header_in` | input | 25 | DTF upstream header |
| `nvu_upstream_data_in` | input | 64 | DTF upstream data |
| `nvu_upstream_valid_in` | input | 1 | DTF upstream valid |
| `nvu_dtf_channel_id` | input | 8 | DTF Channel ID (refer SoC Debug HAS) |
| `nvu_dtf_master_id` | input | 8 | DTF Master ID (refer SoC Debug HAS) |

DTF reset: `nvu_prim_rst_b`. DTF clock: `nvu_func_clk` (200 MHz).

### PCKTZR_DTF_SRC_CONFIG Register

| Bits | Access | Default | Field | Description |
|------|--------|---------|-------|-------------|
| 0:0 | RW | 0 | `SRC_EN` | Enable for source packetizer |
| 1:1 | RW | 0 | `DEST_ID` | Specifies which trace aggregator to use |
| 2:2 | RW | 0 | `ENC_CG_OVRD` | Encoder clock gating override |
| 3:3 | RW | 1 | `LTA_CLOCK_LOW_FREQ` | When DTF clock freq <= 5x XTAL: 0=use fast counter, 1=fast counter is 0 |
| 5:4 | RW | 0 | `LTA_CNTR_WIDTH` | Fast counter width: 0=7-bit, 1=8-bit, 2=6-bit, 3=reserved |
| 31:6 | RO | 0 | Reserved | — |

### PCKTZR_DTF_SRC_STATUS Register

| Field | Description |
|-------|-------------|
| `TS_BIT_SHIFT_VAL` | Platform XTAL frequency indicator (reflects SoC tie-off `nvu_dtf_ts_bit_shift_val[1:0]`) |

### DTF FW Trace Flow (HAS Section 15.5.1.8.1)

Prerequisites:
- FW must complete HH-SYNC to initialize NVU ART timer before starting DTF trace
- FW programs `LTA_CNTR_WIDTH`, `LTA_CLOCK_LOW_FREQ` before enabling packetizer

Message format:
1. FW writes D64TS packet (Sys-T Event Header) to `D64TS_LO_ADDR` / `D64TS_HI_ADDR`
2. FW pushes 32b data chunks by writing to `DATA_WITHOUT_EOP` register
3. FW pushes last 32b chunk by writing to `DATA_WITH_EOP` register
4. SRCPKT concatenates two 32b chunks into 64b (pads if odd count) and pushes to SRCENC
5. SRCENC delivers message to DTF fabric losslessly

### DTF Clock/Power Gating Flow (HAS Section 15.5.1.8.2)

1. FW writes `SRC_EN = 0` in packetizer to stop sending trace
2. `SRC_EN = 0` forces encoder to flush FIFO
3. FW polls for **Encoder FIFO empty** status bit
4. If empty, FW reads DTF status register again for **Arbiter FIFO empty** status
5. When both FIFOs are empty, it is safe to initiate PG/CG flow
6. Clocks for external repeaters provided by SoC

### Model Debug (HAS Section 15.3.1)

In debug mode, NVU allows usage of IMR for dumping intermediate model results. `RS3_WR_DISABLE` is set to `0` in debug mode, unlocking the path to IMR from VPX/NPX via SMMU VMEM.


## RAS — Reliability, Availability, and Serviceability (HAS Section 12)

NVU is not intended for safety-critical applications. NVU HW provides basic infrastructure to improve overall FIT rate.

### Error Summary

| Error Condition | Action |
|----------------|--------|
| Watchdog Expiry | FW Reset (HW resets the CPU) |
| SRAM DED (Double Error Detect) | FW Reset (HW resets the CPU) |

On either error, NVU FW is forced to re-boot.

### SSCEL — SRAM Slice Controller Error Log (HAS Section 8.6)

The **SSCEL register** (per slice) provides error event logging for SRAM ECC errors:

| Field | Description |
|-------|-------------|
| `CNT` (CerrCnt) | **Correctable Error Count** — bits 15:0, ROVP. This register field increments with every correctable error indication. This field will be reset only upon a powergood_rst_b assertion. |

> **Cross-reference**: Full SSCEL register bitfield details are in `/skill fv-nvu/registers` → SRAM Slice Controller section. See also the SSCR register for ECC scrub control.

### Timer Subsystem (Integration HAS v0.8, Section 7)

The NVU includes multiple timers for scheduling, timestamping, and hang detection:

| Timer | Clock Source | Frequency | Notes |
|-------|-------------|-----------|-------|
| **VPX2 Timer** | `nvu_func_clk` | 400 MHz | General-purpose timer for FW scheduling (200 MHz in low-power mode) |
| **Local ART** | `nvu_xtal_clk` | 38.4 MHz | Always Running Timer for timestamps/synchronization |
| **WDT** | `func_clk / divider` | ~64.1 Hz tick (at 200 MHz with divider `0x2F9B80`, period ≈ 15.6 ms) | Two-stage watchdog (see below) |
| **RTC** | `nvu_rtc_clk` | 32.768 KHz | Real-time clock, survives D0i2 |
| **HPET** | `nvu_rtc_clk` | 32 KHz | Three HPET timers: HPET0 (periodic), HPET1 (one-shot), HPET2 (one-shot) for FW-managed scheduling |

HPET registers reside at `0xF360_0000`. The HPET has **three** timers (HAS Section 8.16.2): one periodic timer (HPET0, IRQ 48) that generates interrupts at a fixed rate, and two one-shot timers (HPET1 IRQ 49, HPET2 IRQ 50) that generate interrupts at specific times in the future (countdown-style). FW must re-arm one-shot timers after each expiry.

### Watchdog Timer (WDT) — HAS Section 8.16.3

The WDT detects FW hangs and assists recovery without affecting the platform/SoC.

**WDT Register Target**:

| Block | Base Address | End Address | Size |
|-------|-------------|-------------|------|
| WDT | `0xF3500000` | `0xF3501000` | 4KB |

**WDT Clock**: Derived from `func_clk` via CCU clock divider. VPX2 IRQ 47 (`irq47_a`, vector `0xbc`).

| func_clk | Recommended Divider | WDT Clock Period | Max Time-Out |
|----------|-------------------|-----------------|-------------|
| 200 MHz | `0x2F9B80` | 15.6 ms | ~4 seconds |

**NPX6 WDT Clock**: `nvu_func_clk` at 25/12.5 MHz (from clock table `SL0_WDT_CLK`).

**WDT State Machine** (3 states: Idle, T1, T2):

1. **Idle**: `WDT_EN = 0` — counters do not decrement, no IRQ or reset generated
2. **T1**: FW writes `WDT_EN = 1` — T1 counter decrements; T2 counter at reset value
3. **T1 → T2 transition**: T1 counter reaches 1 — WDT generates **interrupt** (VPX2 IRQ 47), starts decrementing T2
4. **T2 expiry**: T2 counter reaches 1 — WDT indicates to PMU/CCU to perform **FW reset**
5. **Reload**: FW writes `WDT_RL = 1` — both T1 and T2 counters reload from `WDT_T1`/`WDT_T2` fields
6. **Read counters**: FW reads WDT Values Register for current counter values

### SRAM ECC — HAS Section 8.6.4.2

NVU SRAM provides **SECDED ECC** (Hamming code 9b/8b for 128b/64b data path) across all 7 SRAM slices.

#### SSCR (Slice Controller Control Register)

| Bits | Access | Default | Field | Description |
|------|--------|---------|-------|-------------|
| 0:0 | RW | 1 | `RMWPIPESTG` | RMW pipe stage enable (required at higher frequency) |
| 1:1 | RW | 0 | `ECCENB` | ECC enable (active low): when cleared, enables ECC generation/SECDED check |
| 2:2 | RW | 1 | `DSOVREN` | Deep-sleep override enable |
| 3:3 | RW | 0 | `DSOVRVAL` | Deep-sleep override value (1=DEEPSLEEP, 0=ACTIVE) |
| 4:4 | RW | 1 | `SDEN` | Shutdown enable — forces SRAM banks to SHUTDOWN state |
| 5:5 | RW | 1 | `MEMPIPEN` | Memory pipeline enable (adds 1 clock read latency) |
| 11:8 | RW | 0x4 | `DSMINDUR` | Deep-sleep minimum duration (max 16 clocks) |
| 12:12 | RW1SV | 0 | `ECCSCRUB` | Trigger ECC scrub — HW clears when complete |

#### SSCEL (SRAM Slice Controller ECC Log)

| Bits | Access | Default | Field | Description |
|------|--------|---------|-------|-------------|
| 15:0 | ROVP | 0 | `CNT` (CerrCnt) | Correctable error count (saturates at `0xFFFF`, reset only on `powergood_rst_b`) |
| 16:16 | ROVP | 0 | `CERREV` | Correctable error event flag (reset only on `powergood_rst_b` / Sx/G3) |
| 31:31 | ROVP | 0 | `UCERREV` | Uncorrectable error event flag (reset only on `powergood_rst_b` / Sx/G3) |

#### SSCMAS (SRAM Slice Controller Memory Access Status)

| Bits | Access | Default | Field | Description |
|------|--------|---------|-------|-------------|
| 31 | RO/V/P | 0 | `HWZRDONE` | HW SRAM Zeroing done — indicates completion of autonomous zeroing triggered by DFx policy update or reset de-assertion |
| 30:0 | RO | 0 | Reserved | — |

#### ECC Scrub Sequence (HAS Section 8.6.4.2.7.1)

For each slice x [0:N-1]:
1. Program `cr_shutdown_en = 0` (default is 1 — slices come up in shutdown)
2. Note: default `cr_deepsleep_override_val = 0` and `cr_deepsleep_override_en = 1` ensures SRAM is ACTIVE
3. Program `cr_ecc_scrub[x] = 1`
4. SRAM controller HW ensures slice is out of SD, all banks' ROP asserted
5. HW writes pseudo-random data to all SRAMs in the slice
6. HW clears `ECCSCRUB` bit when complete — FW polls for this
7. After scrub, FW reprograms `cr_deepsleep_override_en = 0` to allow HW autonomous DS control

> All slices can be scrubbed simultaneously — power delivery supports writes to all slices at once.

### Exception/Soft Reset Handling (HAS Section 10.2.6)

NVU supports soft reset of VPX core under these conditions:
- FW-initiated soft reset (triggered via `ESE2NVU_IPC.RESET_BIT`)
- Exception Reset triggered by:
  - **Watchdog expiry**
  - **ECC double-bit error**

> Current generation VPX2 does **not** support triple-fault/shutdown indication — this is not a reset source.

**NVU CORE Reset HW Sequence — 11 Steps** (from HAS SVG):

Reset sources: `WD_RST` || `ECC_RST` || `SYSTF_HALT_R` || `V0C0_RST_A`

```
 CRPM                                VPX2 Core
  │                                     │
  │ [1] Assert v0c0_ext_halt_req_a ───► │
  │                                     │ [2] Pipeline flush
  │                                     │ [3] Reach IDLE state
  │ ◄── v0c0_ext_halt_ack ──────────── │ [4] Assert v0c0_ext_halt_ack
  │ ◄── sys_halt_r ─────────────────── │ [5] Assert sys_halt_r
  │                                     │
  │   ⏱ CRPM_VPX_HALT_TIMEOUT_CNT     │  (timeout if VPX2 won't halt)
  │                                     │
  │ [6] De-assert v0c0_ext_halt_req_a   │  ── Core halted ──
  │ [7] Assert rst_a (64 clocks) ─────► │  ── HW reset pulse ──
  │ [8] De-assert rst_a                 │
  │                                     │
  │ [9] Assert v0c0_ext_run_req_a ────► │  ── Resume sequence ──
  │ ◄── v0c0_ext_run_ack ─────────────│ [10] Assert v0c0_ext_run_ack
  │ [11] De-assert v0c0_ext_run_req_a   │  ── Core running ──
```

**Key signals**:
| Signal | Direction | Purpose |
|--------|-----------|---------|
| `v0c0_ext_halt_req_a` | CRPM → VPX2 | Request core halt |
| `v0c0_ext_halt_ack` | VPX2 → CRPM | Core halted acknowledgment |
| `sys_halt_r` | VPX2 → CRPM | System halt confirmed |
| `rst_a` | CRPM → VPX2 | Hard reset pulse (64 clocks) |
| `v0c0_ext_run_req_a` | CRPM → VPX2 | Request core resume |
| `v0c0_ext_run_ack` | VPX2 → CRPM | Core running acknowledgment |

**CRPM_VPX_HALT_TIMEOUT_CNT**: Internal timeout — if VPX2 does not assert `v0c0_ext_halt_ack` within this count, CRPM proceeds with reset regardless (prevents hang).

**Post-reset**: ROM must check `CRPM_RST_HIS` register to determine reset source:
- If `ECC_RST` — ROM/FW must reset/quiesce **all** initiators (the erroneous read could have originated from any initiator on the fabric)
- If `WD_RST` — standard watchdog recovery (check FW state, reload if needed)
- If `V0C0_RST_A` — external reset request (check IPC state)

**PME Recovery**: After exception reset, NVU FW sends PME to wake host SW driver (which is in D3 post FW loading) to trigger FW re-load.


## Telemetry (HAS Section 8.22)

NVU subscribes to **Chassis 2.2 telemetry service** with PMC.

### Telemetry Service Control

| Service | Bit | resource=0 | resource=1 |
|---------|-----|-----------|-----------|
| `telemetry_service` | 2 | Telemetry push not allowed (Host CPU in C10) | Telemetry push allowed (Host CPU in C0) |

VPX2 IRQ 43 (`irq43_a`, vector `0xac`) — `TELEMETRY_SERVICE IRQ` from NVU HW.

### Telemetry Flow

1. PMC writes NVU telemetry sideband registers (available any time after NVU is out of reset — FW loading not required):
   - `NVU SB Address 0x20E0` — `NVU_PMC_TELEMETRY_SRAM_REG0_BASE_OFFSET`
   - `NVU SB Address 0x20E4` — `NVU_PMC_TELEMETRY_SRAM_REG0_SIZE`
   - `NVU SB Address 0x20E8` — `NVU_PMC_TELEMETRY_SRAM_REG1_BASE_OFFSET`
   - `NVU SB Address 0x20EC` — `NVU_PMC_TELEMETRY_SRAM_REG1_SIZE`
   - `NVU SB Address 0x20F0` — `NVU_PMC_TELEMETRY_SRAM_FID`
   - `NVU SB Address 0x20F4` — `NVU_PMC_TELEMETRY_GLOBAL_TELEMETRY_STATUS`
2. If `GLOBAL_TELEMETRY_EN = 1`:
   - PMC sends `Sleep_Level_Req[telemetry_service=1]` to NVU
   - HW sets `CRPM.TELEMETRY_SERVICE = 1` and sends IRQ to FW
   - FW reads telemetry SSRAM region-0/region-1 base, size, and FID
   - FW pushes telemetry data over IOSF_SB (via SBEP) using MMIO WR, DWord by DWord
   - FW asserts `Resource_Own_Req[SBR]` before push, de-asserts after
3. On CPU C10 entry: PMC sends `Sleep_Level_Req[telemetry_service=0]` — NVU stops telemetry push
4. If `GLOBAL_TELEMETRY_EN = 0`: PMC does not write telemetry registers, NVU FW does not maintain telemetry data

### Telemetry-Related IPC Channel

| Channel | Source | Destination | SB Address Range |
|---------|--------|-------------|-----------------|
| PMC → NVU | PMC | NVU | `0x20E0`, `0x20E4` (and extended telemetry range `0x20E0`–`0x215C`) |

### Telemetry Counter Definitions (from NVU IP HAS Excel)

NVU FW pushes these counters to PMC via IOSF_SB (DWord by DWord) when `telemetry_service=1`:

#### Debug & Profiling Counters (37 fields, 148 bytes)

| # | Field | Unit | Size | Comment |
|---|-------|------|------|---------|
| 1 | D0.200M Counter | RTC Tick | 4B | VPX active at 200MHz |
| 2 | D0.400M Counter | RTC Tick | 4B | VPX active at 400MHz |
| 3 | D0.Sleep Counter | RTC Tick | 4B | Time in D0 sleep sub-state |
| 4 | D0i1 Counter | RTC Tick | 4B | Time in D0i1 (FUNC TCG) |
| 5 | D0i2 Counter | RTC Tick | 4B | Time in D0i2 (IPAPG+RET) |
| 6 | IPAPG Main Counter | RTC Tick | 4B | IPAPG duration — Main PD |
| 7 | IPAPG USB Counter | RTC Tick | 4B | IPAPG duration — USB PD |
| 8 | IPAPG MIPI Counter | RTC Tick | 4B | IPAPG duration — MIPI PD |
| 9 | NPX Active Counter | RTC Tick | 4B | NPX6-1K NNA active time |
| 10 | NPX Sleep Counter | RTC Tick | 4B | NPX6-1K NNA sleep time |
| 11 | Wake by Timer Counter | Count | 4B | Wake events from timer |
| 12 | Wake by SIO Counter (Snapshot) | Count | 4B | Wake from SIO (e.g. IPU Config Pin) |
| 13 | Wake by IO Counter | Count | 4B | Wake from IO (e.g. Camera Release IRQ) |
| 14 | Wake by Other Counter | Count | 4B | Other wake sources |
| 15 | D0i1 Enter Max Latency | RTC Tick | 4B | Worst-case D0i1 entry |
| 16 | D0i1 Enter Avg Latency | RTC Tick | 4B | Average D0i1 entry |
| 17 | D0i1 Exit Max Latency | RTC Tick | 4B | Worst-case D0i1 exit |
| 18 | D0i1 Exit Avg Latency | RTC Tick | 4B | Average D0i1 exit |
| 19 | D0i2 Enter Max Latency | RTC Tick | 4B | Worst-case D0i2 entry |
| 20 | D0i2 Enter Avg Latency | RTC Tick | 4B | Average D0i2 entry |
| 21 | D0i2 Exit Max Latency | RTC Tick | 4B | Worst-case D0i2 exit |
| 22 | D0i2 Exit Avg Latency | RTC Tick | 4B | Average D0i2 exit |
| 23 | I2C/I3C Write Access Counter | Count | 4B | Sensor write transactions |
| 24 | I2C/I3C Write Amount | Byte | 4B | Total bytes written to sensors |
| 25 | I2C/I3C Read Access Counter | Count | 4B | Sensor read transactions |
| 26 | I2C/I3C Read Amount | Byte | 4B | Total bytes read from sensors |
| 27 | ISH IPC Message Out Counter | Count | 4B | Messages sent to ISH |
| 28 | ISH IPC Message Out Bytes | Byte | 4B | Total bytes sent to ISH |
| 29 | ISH IPC Message In Counter | Count | 4B | Messages received from ISH |
| 30 | ISH IPC Message In Bytes | Byte | 4B | Total bytes received from ISH |
| 31 | IMR Read Access | Count | 4B | DRAM paging reads |
| 32 | IMR Write Access | Count | 4B | DRAM paging writes |
| 33 | Boot Latency | RTC Tick | 4B | FW boot time |
| 34 | Firmware Status | Enum | 4B | Current FW state |
| 35 | NN Execution Time Max | RTC Tick | 4B | Worst-case inference latency |
| 36 | NN Execution Time Avg | RTC Tick | 4B | Average inference latency |
| 37 | Camera/Algo FPS | Count | 4B | Max/Min/Avg frame rate |

#### Data Leaking Threat Report (4 fields, 16 bytes)

| # | Field | Unit | Size | Comment |
|---|-------|------|------|---------|
| 38 | Violation Counter | Count | 4B | Total data leak violations |
| 39 | Violator_Top1 | App ID | 4B | Most frequent violator |
| 40 | Violator_Top2 | App ID | 4B | Second most frequent |
| 41 | Violator_Top3 | App ID | 4B | Third most frequent |

#### UX Study Counters (12 fields, 300 bytes)

| # | Field | Unit | Size | Comment |
|---|-------|------|------|---------|
| 42 | User Presence with Attention | Second | 4B | User present + looking at screen |
| 43 | User Presence without Attention | Second | 4B | User present + looking away |
| 44 | User Absence | Second | 4B | No user detected |
| 45 | Onlooker Presence | Second | 4B | Additional person detected |
| 46 | Face Height Histogram | Struct | 36B | From IGK (pending PIA review) |
| 47 | Face Yaw Histogram | Struct | 36B | From IGK (pending PIA review) |
| 48 | Face Pitch Histogram | Struct | 36B | From IGK (pending PIA review) |
| 49 | Face Roll Histogram | Struct | 36B | From IGK (pending PIA review) |
| 50 | Face Detection Confidence Histogram | Struct | 36B | From IGK (pending PIA review) |
| 51 | Face ID Similarity Histogram | Struct | 36B | From IGK (pending PIA review) |
| 52 | Steady Scene Histogram | Struct | 36B | From IGK (pending PIA review) |
| 53 | Face Detection Avg ROI Histogram | Struct | 36B | From IGK (pending PIA review) |

> **Total**: 53 counters, ~464 bytes per telemetry push. Counters #1–10 are critical for **power state residency validation**; #15–22 for **latency benchmarking**; #35–37 for **inference performance**; #38–41 for **security audit**.

### Hammock Harbor Timestamp Architecture (HAS Section 8.23)

The NVU integrates a **Hammock Harbor (HH) Type-D** timestamp module for cross-IP time synchronization with the SoC-wide ART (Always Running Timer) framework.

#### ART Timer Flavors

| Timer | Frequency | Clock Source | IPAPG Behavior | Description |
|-------|-----------|-------------|----------------|-------------|
| XTAL ART | 38.4 MHz | `nvu_xtal_clk` | **Resets** (counter lost) | High-resolution timer; requires re-sync after IPAPG exit |
| PGCB ART | 2.56 MHz | `nvu_pgcb_clk` | **Resets** (counter lost) | Medium-resolution timer; also lost during IPAPG |
| RTC ART | 32 KHz | `nvu_rtc_clk` | **Survives** | Low-resolution timer; persists through IPAPG for wake timing |

#### Synchronization Commands

| Command | Opcode | Type | Description |
|---------|--------|------|-------------|
| SyncStartCmd | `0x50` | Posted | Initiates global ART sync sequence |
| LocalSync | `0x51` | Non-Posted | Captures local 64-bit timestamp; requires NP completion |
| SyncComp | `0x92` | Posted | Sync completion acknowledgment |

#### M/N Divider Values (ART-to-local timer conversion)

| Timer | N | Q | R | Derivation |
|-------|---|---|---|------------|
| PGCB (2.56 MHz) | 1 | 15 | 0 | 38.4 / 2.56 = 15.0 |
| RTC (32 KHz) | 32768 | 1171 | 28672 | 38.4 MHz / 32.768 KHz = 1171 + 28672/32768 |

> **GPIO timestamping is NOT supported** on the NVU HH module. Timestamp capture is limited to SB message-based sync commands.
> **XTAL and PGCB counters reset in IPAPG** — after IPAPG exit, the driver must re-sync these timers via SyncStartCmd + LocalSync before using timestamps for event correlation.


## VPX2 Debug-Related Interrupts

| IRQ | Source | Name | Vector | Description |
|-----|--------|------|--------|-------------|
| 1 | ARCv2VPX | MemoryError | `0x04` | VPX2 memory error (I-cache/D-cache/MMU fault) |
| 2 | ARCv2VPX | InstructionError | `0x08` | VPX2 instruction error |
| 20 | ARCv2VPX | Performance Monitor | `0x50` | VPX2 performance monitor interrupt |
| 21 | ARCv2VPX | STU error | `0x54` | Streaming Transfer Unit error |
| 43 | CRPM | TELEMETRY_SERVICE IRQ | `0xac` | Telemetry service status change |
| 47 | TIMERS | WDT IRQ | `0xbc` | Watchdog Timer expiry |
| 48 | TIMERS | HPET0 IRQ | `0xc0` | HPET periodic timer interrupt |
| 49 | TIMERS | HPET1 IRQ | `0xc4` | HPET one-shot timer 1 interrupt |
| 50 | TIMERS | HPET2 IRQ | `0xc8` | HPET one-shot timer 2 interrupt |
| 55 | DMA | DMA IRQ | `0xdc` | DMA completion/error |
| 59 | FABRIC | MAIN_FABRIC IRQ | `0xec` | Fabric error |
| 87 | SRAMSS | SRAM_FABRIC IRQ | `0x15c` | SRAM fabric error |
| 88 | SRAMSS | SMMU IRQ | `0x160` | SMMU page fault/translation |
| 107 | ARCSYNC | IRQ0 | `0x1ac` | ARCSYNC cross-core signaling (NPX6 → VPX2) |
| 108 | ARCSYNC | IRQ1 | `0x1b0` | ARCSYNC cross-core signaling (NPX6 → VPX2) |


## Register Address Summary

| Block | Base Address | End Address | Size | Description |
|-------|-------------|-------------|------|-------------|
| CRPM | `0xF3000000` | `0xF3001000` | 4KB | Clock/Reset/Power Management (includes `CRPM_RST_HIS`, `TELEMETRY_SERVICE`) |
| DTF | `0xF3400000` | `0xF3401000` | 4KB | Debug Trace Fabric (packetizer + encoder config) |
| WDT | `0xF3500000` | `0xF3501000` | 4KB | Watchdog Timer registers |
| FABRIC | `0xF3700000` | `0xF3701000` | 4KB | Main fabric (error reporting) |
| SRAMSS_CFG | `0xF5000000` | `0xF5100000` | 1MB | SRAM subsystem config (per-slice SSCR/SSCEL/SSCMAS) |
| NPX_DEBUG | `0xF6200000` | `0xF6240000` | 256KB | NPX6 debug (ROM Table, ARC Trace, L1 Core) |

**Telemetry Sideband Registers** (PMC → NVU, IOSF_SB):

| SB Address | Register |
|-----------|----------|
| `0x20E0` | `NVU_PMC_TELEMETRY_SRAM_REG0_BASE_OFFSET` |
| `0x20E4` | `NVU_PMC_TELEMETRY_SRAM_REG0_SIZE` |
| `0x20E8` | `NVU_PMC_TELEMETRY_SRAM_REG1_BASE_OFFSET` |
| `0x20EC` | `NVU_PMC_TELEMETRY_SRAM_REG1_SIZE` |
| `0x20F0` | `NVU_PMC_TELEMETRY_SRAM_FID` |
| `0x20F4` | `NVU_PMC_TELEMETRY_GLOBAL_TELEMETRY_STATUS` |


## FW Debug Categories and Debug Policy (FAS §16, L18716-19200)

The NVU FAS defines three categories of debug and three debug policy states that determine what debug features are available.

### Debug Categories (FAS §16.2.1)

| Category | Description | Tools |
|----------|-------------|-------|
| **OS SW Debug** | Host-side debug via HECI/SMHI | HECI log, ETW trace, image dump/tune/probe, profiling, IP telemetry |
| **Direct HW Debug** | Physical hardware debug interfaces | JTAG/OCD, UART/I2C via FTDI adapter |
| **DTF Debug** | Debug Trace Fabric instrumentation | DTF FW trace to NorthPeak/Trace Hub (MIPI Sys-T format) |

### Debug Policy Table (FAS §16.2.2, L19122)

| EOM State | Debug Fuse | OS SW Debug | Direct HW Debug | DTF Debug |
|-----------|-----------|-------------|-----------------|-----------|
| Pre-EOM | Unlock | ✅ All features | ✅ All features | ✅ All features |
| Pre-EOM | Lock | ✅ All features | ✅ All features | ✅ All features |
| Post-EOM | Unlock | ✅ All features | ✅ All features | ✅ All features |
| Post-EOM | Lock | ⚠️ Limited (ROM/BUP only) | ❌ Disabled | ⚠️ Limited (telemetry + DTF base FW always; App FW DTF = TTL-only) |

> **Key**: Post-EOM + Lock is the production configuration. Only telemetry push and base FW DTF are available. App FW DTF is restricted to Intel-signed TTL apps only.

### FW Signature Policy (FAS §16.2.3)

| Debug Fuse State | Signing Key Used |
|-----------------|-----------------|
| Debug-Unlock | Debug Key (development) |
| Debug-Lock | Production Key (release) |

> Key management is handled by ESE (Embedded Security Engine).


## FW Debug Tools (FAS §16, L18800-19800)

### ImageTool — FW Image Generator (FAS §16.2)

Python command-line tool for generating NVU firmware images:

```
python ImageTool.py -t <BASE|EXTENSION> -fv <version> -i <path> [options]
```

| Parameter | Description |
|-----------|-------------|
| `-t BASE` | Generate Base FW image (VPX FW + NPX FW + Core App + AON Image) |
| `-t EXTENSION` | Generate Extension FW image (WASM apps + NN models + PDT) |
| `-fv <version>` | Firmware version string |
| `-i <path>` | Input directory path containing module binaries |

### Variant ID Format (FAS §16.2, L19000)

64-bit identifier for NN models and WASM apps:

```
variant_id[63:0] = (vendor_id << 48) | (type_id << 40) | (variant_id << 8) | model_index
```

Lookup tables: `apptype_list.json`, `vendor_list.json`

### Profiling Tool — SMHI/HECI-based (FAS §16.1.2)

Debug-unlock only. Queries FW via SMHI HECI client.

| Metric Category | Examples |
|----------------|---------|
| **BSP Metrics** | IRQ counters, I2C stats, Wake events, Power state transitions, Boot performance, Heap usage, Task info, D0iX residency, Timer utilization |
| **WASM Metrics** | Active apps count, Execution time per app, NN offload latency, Frame interval |

### PNR Tool — Playback and Record (FAS §16.1.3)

Debug-unlock only. Records camera RAW frames + ISP output via HECI for offline analysis:
- **Record mode**: Captures raw camera frames and CVISP output to host file
- **Playback mode**: Replays captured frames through NVU pipeline for reproducible testing
- **Transport**: HECI bulk transfer

### Logging Tool — Multi-Backend (FAS §16.1.4)

| Feature | Description |
|---------|-------------|
| **Backends** | I2C + UART + HECI + DTF |
| **Formats** | MIPI Sys-T catalog/dictionary mode (compact, binary) + text mode (human-readable) |
| **Filtering** | Per-module log level filtering |
| **Crash Dump Parser** | Parses crash dump from AONRF |
| **NPX Log Aggregation** | NPX logs written to shared buffer, aggregated by VPX FW |


## VPX FW Source Tree (FAS §16.1, L18716-18800)

```
nvu-fw/
├── modules/
│   ├── zephyr/              # Zephyr RTOS v3.7.0
│   └── wasm-micro-runtime/  # WAMR WebAssembly runtime
├── app-mgmt/                # WASM App Manager
│   └── vmlib/               # Vision and Math Library (vmlib)
├── vpxfw/
│   ├── modules/
│   │   └── apps/            # WASM application sources
│   ├── ...                  # VPX core FW modules
│   └── ...
└── ...
```

**Build system**: `west build` (Zephyr build system). Supports targets:
- **FPGA** — Pre-Si FPGA emulation
- **SI** — Post-Si silicon
- **NSIM** — ARC nSIM software simulator

**FDK Project Structure** (FAS §16.1):
```
fdk_project/
├── project.json             # Project-level config
├── selected_functions.json  # Active functions/capabilities
└── app/
    └── <app_name>/
        └── function.json    # Per-app configuration
```

> **NPX FW build flow**: TODO in FAS (not yet documented).


## NN Algorithm Profiling (FAS §16.2.6)

Synopsys NPX6-1K provides built-in profiling features (all require debug-unlock):

| Feature | Description | Requirement |
|---------|-------------|-------------|
| **Hash Checking** | Verify intermediate tensor hash values match golden reference | Debug-unlock |
| **Per-layer Profiling** | Measure execution time per NN layer (convolution, activation, pooling, etc.) | Debug-unlock |
| **Tensor Dump** | Dump intermediate tensor values to SRAM/IMR for offline comparison | Debug-unlock + `RS3_WR_DISABLE=0` |

> **Production restriction**: Profiling metrics are available only in debug-unlocked mode. See the Debug Policy section for mode detection and host permissions.


## FAS Known OPENs, Errata, and TODOs (FAS §17)

> **Note**: No formal errata or ECN (Engineering Change Notice) list has been published for NVU HAS v1.0. Known RTL opens and corner case issues are tracked via HSDES sightings. Add errata entries here as they are discovered during post-silicon validation.

### OPEN Issues

| ID | Description | Impact |
|----|-------------|--------|
| `OPEN_0001` | USB Raw camera ISOCH pin error propagation from XHCI_CAM/NVU to IPU when IPU owns and NVU is in offload mode | Affects USB camera error handling in concurrent mode |

### FAS TODO Items (15 total)

| ID | Area | Description |
|----|------|-------------|
| `TODO_0001` | Image Reformat | Image Reformat optimization (performance) |
| `TODO_0002` | Probe | Probe throughput characterization |
| `TODO_0003` | Camera | External MCLK support |
| `TODO_0004` | SIO | SIO design detail completion |
| `TODO_0005` | Security | ESE attack report mechanism |
| `TODO_0006` | WASM | WASM app functions completion |
| `TODO_0007` | WASM | Restart/erase mechanism |
| `TODO_0008` | WASM | Async result ID handling |
| `TODO_0009` | Platform | I2C/GPIO/ISP/USB configuration details |
| `TODO_0010` | ISH | ISH command/response completion |
| `TODO_0011` | API | CV/DSP/NN callback API completion |
| `TODO_0012` | Telemetry | Telemetry API for WASM apps |
| `TODO_0013` | Documentation | Architecture diagram updates |
| `TODO_0014` | Build | WAMR Docker build environment |
| `TODO_0015` | Documentation | Detailed flow diagram updates |

> **Validation Impact**: OPEN_0001 affects USB camera error path testing. TODOs 0009-0011 affect ISH/camera integration test coverage.


## Test Scenarios

### VISA Observability Test
1. Ensure NVU is out of reset and VISA2 architecture is active
2. Verify `nvu_avisa_dbgbus` signals are observable at VISA pins
3. Validate DFx secure plugin enables/disables VISA per security policy
4. TBD -- specific VISA mux selections and signal groups not detailed in HAS v1.0

### DTF FW Trace Test
1. Complete HH-SYNC to initialize NVU ART timer
2. Program `PCKTZR_DTF_SRC_CONFIG`: set `LTA_CNTR_WIDTH`, `LTA_CLOCK_LOW_FREQ`, then set `SRC_EN = 1`
3. FW writes D64TS header to `D64TS_LO_ADDR` / `D64TS_HI_ADDR`
4. FW pushes payload via `DATA_WITHOUT_EOP` writes
5. FW writes last chunk to `DATA_WITH_EOP`
6. Verify trace message appears at NorthPeak/Trace Aggregator with correct HW timestamp
7. Verify MIPI Sys-T format compliance (D64TS → D64 (1..N) → D64M)

### DTF Power Gate Flow Test
1. Complete a DTF trace session as above
2. Write `SRC_EN = 0` to flush encoder
3. Poll Encoder FIFO empty status
4. Read DTF status register again for Arbiter FIFO empty status
5. Verify both FIFOs empty before initiating IPAPG

### WDT Interrupt Test
1. Configure WDT with known T1/T2 timeout values (divider `0x2F9B80` for 200 MHz)
2. Write `WDT_EN = 1` to start T1 countdown
3. Do NOT reload (`WDT_RL`)
4. Verify VPX2 IRQ 47 fires when T1 expires
5. Verify FW can still reload during T2 phase (`WDT_RL = 1`)
6. If T2 also expires, verify FW reset is triggered

### WDT Recovery Test
1. Configure WDT with short timeout
2. Allow both T1 and T2 to expire
3. Verify HW resets the CPU
4. Verify ROM checks `CRPM_RST_HIS` for WDT reset source
5. Verify FW re-boot completes successfully

### SRAM ECC Correctable Error Test
1. Ensure ECC is enabled (`SSCR.ECCENB = 0`)
2. Inject a single-bit error in SRAM (via error injection mechanism — TBD -- injection method not in HAS v1.0)
3. Verify `SSCEL.CERREV = 1` and `SSCEL.CNT` increments
4. Verify data is corrected by SECDED hardware
5. Verify `CNT` saturates at `0xFFFF` and does not wrap

### SRAM ECC Uncorrectable Error (DED) Test
1. Inject a double-bit error in SRAM
2. Verify `SSCEL.UCERREV = 1`
3. Verify FW reset is triggered (ECC_RST path)
4. After reset, verify ROM checks `CRPM_RST_HIS` — reset due to `ECC_RST`
5. Verify ROM/FW resets/quiesces all initiators before proceeding

### SRAM ECC Scrub Test
1. After NVU power-on, verify SRAM slices are in SHUTDOWN (default `SDEN = 1`)
2. For each slice: clear `SDEN`, write `ECCSCRUB = 1`
3. Poll `ECCSCRUB` until HW clears it (scrub complete)
4. Reprogram `cr_deepsleep_override_en = 0` for autonomous DS
5. Verify no ECC errors were recorded post-scrub

### Telemetry Push Test
1. Verify PMC writes telemetry registers at SB addresses `0x20E0`–`0x20F4`
2. PMC sends `Sleep_Level_Req[telemetry_service=1]`
3. Verify `CRPM.TELEMETRY_SERVICE = 1` and VPX2 IRQ 43 fires
4. Verify FW reads region base/size/FID and pushes telemetry data via SBEP MMIO WR
5. PMC sends `Sleep_Level_Req[telemetry_service=0]` (CPU C10 entry)
6. Verify NVU FW stops telemetry push

### Exception Reset with PME Wake Test
1. Induce an exception reset (WDT expiry or ECC DED)
2. Verify VPX2 core halts (CRPM timeout if VPX2 does not halt)
3. Verify `rst_a` asserted for 64 clocks, then de-asserted
4. Verify ROM re-executes and checks `CRPM_RST_HIS`
5. Verify FW sends PME to wake host SW driver from D3
6. Verify host driver re-loads FW successfully

### FAS-Based Test Scenarios

#### 10. Debug Policy State Verification (FAS §16)
- **Description**: Verify FW debug features are gated by EOM and lock state
- **Steps**:
  1. In Pre-EOM + Unlock state, verify all debug features accessible (SMHI, UART log, JTAG, DTF, PNR)
  2. Set EOM fuse → Post-EOM + Unlock — verify all features still accessible
  3. Set debug-lock → Post-EOM + Lock — verify only limited features (OS debug ROM/BUP, telemetry+DTF base FW)
  4. Verify app-level DTF restricted to Intel-signed apps only in Post-EOM + Lock
- **Pass**: Debug gating matches Debug Policy Table (FAS §16.2.2)

#### 11. FW Logging Multi-Backend Test (FAS §16)
- **Description**: Verify FW log output across HECI and UART backends
- **Steps**:
  1. Configure logging to HECI backend — verify Sys-T catalog/dictionary mode output on host
  2. Configure logging to UART backend — verify text mode output on UART console
  3. Enable per-module log filtering — verify only selected module logs appear
  4. Trigger NPX log aggregation — verify NPX logs forwarded through VPX shared buffer
  5. Trigger FW crash — verify crash dump parser recovers structured data from AONRF
- **Pass**: All log backends produce valid output; crash dump is parseable

#### 12. ImageTool FW Image Generation (FAS §16)
- **Description**: Verify ImageTool generates valid Base and Extension images
- **Steps**:
  1. Run `python ImageTool.py -t BASE -fv <ver> -i <path>` — verify output image
  2. Run `python ImageTool.py -t EXTENSION -fv <ver> -i <path>` — verify output image
  3. Verify Global Manifest header: ext_id='NVG0'/'NVG1', entry_point, SRAM base/limit
  4. Verify Module Manifest entries: ext_id='NVUM', correct module_name and load_addr per module
  5. Load generated image on target — verify FW boots successfully
- **Pass**: Images pass manifest validation; FW boots and runs from generated images

#### 13. PNR Tool Camera Playback/Record (FAS §16)
- **Description**: Verify PNR tool records and plays back camera RAW frames
- **Steps**:
  1. Connect via HECI in debug-unlock state
  2. Record N frames from live camera stream — verify raw frame data captured
  3. Disconnect camera and play back recorded frames — verify ISP pipeline processes them identically
  4. Compare ISP output from live vs playback — verify deterministic results
- **Pass**: Playback output matches live capture output

#### 14. Telemetry Autonomous Push Verification (FAS §16)
- **Description**: Verify telemetry pushes to PMC Shared SRAM autonomously
- **Steps**:
  1. Enable telemetry via `Sleep_Level_Req(telemetry_service=1)`
  2. Verify `sbr_own_req` asserted before SRAM write, deasserted after
  3. Verify telemetry push rate ≤ 3Hz
  4. Read PMC Shared SRAM — verify Table#1 (Debug&Profiling QW1-QW32) and Table#2 (UX Study QW1-QW64) populated
  5. Verify telemetry continues through D0i1/D0i2 transitions
- **Pass**: Telemetry data appears in PMC Shared SRAM at correct rate; sbr_own_req protocol correct


## PythonSV Patterns

Pending PythonSV namespace allocation for NVU IP. Below are tentative patterns based on HAS register descriptions:

```python
# NVU PythonSV namespace not yet allocated
# NVU is a PCI RCiEP on IOSF, sideband endpoint name: "NVU"

# === DTF Registers (Base: 0xF3400000) ===
# PCKTZR_DTF_SRC_CONFIG (offset TBD per HAS):
#   Bit 0: SRC_EN (RW) - Source packetizer enable
#   Bit 1: DEST_ID (RW) - Trace aggregator select
#   Bit 2: ENC_CG_OVRD (RW) - Encoder clock gating override
#   Bit 3: LTA_CLOCK_LOW_FREQ (RW, default=1)
#   Bits 5:4: LTA_CNTR_WIDTH (RW, default=0)
#
# PCKTZR_DTF_SRC_STATUS:
#   TS_BIT_SHIFT_VAL - XTAL frequency indicator
#
# DTF Data Registers:
#   D64TS_LO_ADDR - D64TS low address (write to start trace message)
#   D64TS_HI_ADDR - D64TS high address
#   DATA_WITHOUT_EOP - Push 32b data without end-of-packet
#   DATA_WITH_EOP - Push 32b data with end-of-packet

# === WDT Registers (Base: 0xF3500000) ===
# WDT_EN - Enable watchdog (0=idle, 1=start T1)
# WDT_RL - Reload T1/T2 counters
# WDT_T1 - T1 timeout value
# WDT_T2 - T2 timeout value
# WDT Values Register - Read current counter values

# === SRAM Slice Controller (Base: 0xF5000000, per-slice) ===
# SSCR (Slice Controller Control Register):
#   Bit 0: RMWPIPESTG (RW, default=1)
#   Bit 1: ECCENB (RW, default=0) - ECC enable (active low)
#   Bit 4: SDEN (RW, default=1) - Shutdown enable
#   Bit 12: ECCSCRUB (RW1SV, default=0) - Trigger ECC scrub
#
# SSCEL (ECC Log Register):
#   Bits 15:0: CNT (ROVP) - Correctable error count (saturates 0xFFFF)
#   Bit 16: CERREV (ROVP) - Correctable error event
#   Bit 31: UCERREV (ROVP) - Uncorrectable error event
#
# SSCMAS (Memory Access Status):
#   Bit 31: HWZRDONE (RO/V/P) - HW SRAM Zeroing done

# === CRPM (Base: 0xF3000000) ===
# CRPM_RST_HIS - Reset history (check for ECC_RST, WD_RST sources)
# CRPM.TELEMETRY_SERVICE - Telemetry service status bit
# CRPM_VPX_HALT_TIMEOUT_CNT - Internal timeout for VPX halt during reset

# === NPX6 Debug (Base: 0xF6200000) ===
# ROM Table: 0xF6200000 (4KB)
# ARC Trace: 0xF6201000 (4KB) - DB_STAT/DB_CMD/DB_ADDR/DB_DATA/DB_RESET
# L1 Core:   0xF6202000 (4KB) - DB_STAT/DB_CMD/DB_ADDR/DB_DATA/DB_RESET

# === Debug IRQ Map ===
# IRQ 1:   MemoryError (VPX2)
# IRQ 2:   InstructionError (VPX2)
# IRQ 20:  Performance Monitor
# IRQ 21:  STU Error
# IRQ 43:  TELEMETRY_SERVICE IRQ
# IRQ 47:  Watchdog Timer (WDT)
# IRQ 55:  DMA IRQ
# IRQ 59:  MAIN_FABRIC IRQ
# IRQ 87:  SRAM_FABRIC IRQ
# IRQ 88:  SMMU IRQ
# IRQ 107: ARCSYNC IRQ0
# IRQ 108: ARCSYNC IRQ1
```


## MBIST — Memory Built-In Self Test (HAS Section 15.5)

NVU includes **MBIST** (Memory Built-In Self Test) capability for manufacturing and power-on testing of on-chip SRAM arrays. MBIST provides:

- **Coverage**: All 7 SRAM slices (3584KB total), VPX2 caches (32KB I$, 32KB D$, 128KB VCCM), NPX6-1K internal memories
- **Trigger**: MBIST is initiated during manufacturing test or via DFx scan interface — not directly accessible from host SW during normal operation
- **Result**: Pass/fail per memory instance, reported through DFx infrastructure
- **Interaction with ECC**: MBIST tests the raw SRAM arrays; SECDED ECC protection operates independently during runtime

> **Note**: MBIST is a DFx/manufacturing feature. Post-silicon validation engineers typically do not invoke MBIST directly — it runs as part of ATE (Automatic Test Equipment) flows. For runtime memory integrity, rely on SRAM ECC (Section above). See the NVU DFX HAS for detailed MBIST controller registers and patterns.


## See Also

- [registers/SKILL.md](../registers/SKILL.md) — Register map, IRQ table
- [inference/SKILL.md](../inference/SKILL.md) — VPX2/NPX6 performance counters, NN algorithm profiling
- [dma/SKILL.md](../dma/SKILL.md) — DMA error injection, channel debug
- [power/SKILL.md](../power/SKILL.md) — Power state debug, PMC telemetry
- [firmware/SKILL.md](../firmware/SKILL.md) — FW trace, boot debug, IPC logging, HECI transport, crash dump
- **NVU FAS v1.0** — §16 (FDK and Debug), §17 (OPENs/TODOs) — primary FAS reference for debug tools and known issues

## Related Sub-Skills

- [fv-nvu/registers](../registers/SKILL.md) — MMIO/PCI register map, bitfields, offsets


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:28 | Facts added: 573


### Camera Interface (81 facts)

#### Camera Interface

### Overview

The NVU Camera Interface encompasses the MIPI CSI-2 receive path, PHY sharing logic with the host SoC IPU, IPI data delivery to the Altek CVISP ISP, and associated debug and telemetry instrumentation. The following sections describe the hardware configuration parameters, integration interfaces, boot-time considerations, and debug observability.

---

#### MIPI CSI-2 Host Controller Configuration

(HAS §8.7.2.2.2)

The CSI2 Host Controller (CSI2HC) is parameterized at synthesis time. The table below lists all functional configuration parameters.

| Symbol | Type | Values | Default | Description |
|---|---|---|---|---|
| `CSI2_HOST_PHY` | uint32 | D-PHY (1), Combo-PHY (2) | 2 | Physical layer type selection |
| `CSI2_HOST_SNPS_PHY` | uint32 | 0, 1 | 0 | Enables Synopsys D-PHY |
| `CSI2_HOST_DPHY_NUMBER_OF_LANES` | uint32 | 1–8 | 4 | Selects the number of D-PHY data lanes |
| `CSI2_HOST_DATA_PROCESSING` | uint32 | PIPELINE (1), DESKEW (2) | 2 | Selects data processing mode |
| `CSI2_HOST_PPI_PD` | uint32 | 1–4 | NA | Number of pipeline stages on PPI |
| `CSI2_HOST_DATAINTERFACE` | uint32 | IDI (1), IPI (2), IDI&IPI (3) | 2 | Selects data output interface type |
| `CSI2_HOST_N_DATA_IDS` | uint32 | None (0), 4 (1), 8 (2) | 0 | Selects number of data IDs |
| `CSI2_HOST_PCLK_FREE` | uint32 | 0, 1 | 1 | Specifies if pclk is free-running |
| `CSI2_HOST_DFLT_F_SYNC_TYPE` | uint32 | 2, 3, 4 | 2 | Selects the default frame sync type |
| `CSI2_HOST_PPI_PG` | uint32 | 0, 1 | 1 | Enables PPI Pattern Generator |
| `CSI2_HOST_ADVANCED_IPI_IF` | uint32 | 0, 1 | 1 | Enables Advanced IPI interface |
| `CSI2_HOST_NR_IPI_NHP` | uint32 | 1, 2, 3, 4 | 1 | Select the number of IPI interfaces (non-high-performance) |
| `CSI2_HOST_CSI_HP` | uint32 | 0, 1 | 0 | Enables High-Performance features |
| `CSI2_HOST_NR_IPI_HP` | uint32 | 1–8 | NA | Select the number of IPI interfaces (high-performance) |
| `CSI2_HOST_DPHY_16` | uint32 | 0, 1 | NA | Enables support for 16-bit D-PHY |
| `CSI2_HOST_AP` | uint32 | 0, 1 | NA | Enables Automotive Package |
| `CSI2_HOST_PARITY_MODE` | uint32 | Even (0), Odd (1) | NA | Defines parity mode |
| `CSI2_HOST_IPI_FIFO_DEPTH` | uint32 | 32–4096 | 4096 | Depth of the IPI FIFO |
| `CSI2_HOST_IPI_RAM_DEPTH` | uint32 | 32–4096 | 4096 | Depth of the IPI RAM |

> **Note:** The default value of `CSI2_HOST_PCLK_FREE` was updated to `1` per AR captured in ARC sync meeting WW31'24. (HAS §8.7.2.2.2)

---

#### CSI2 Host Controller Integration Interfaces

(HAS §8.7.2.2.3)

| Interface | Port Name(s) | Connectivity | Description |
|---|---|---|---|
| IRQ | `interrupt` | VPX2 IRQ | Interrupt to VPX2 |
| PPI Clock Lane | `rxskewcalhs`, `rxwordclkhs`, `rxbyteclkhs`, `rxclkactivehs`, `rxulpsclknot`, `stopstateclk` | CSI2 PHY | From PHY Sharing/Mux Logic |
| PPI Data Lane | `rxdatahs`, `rxinvalidcodehs`, `rxvalidhs`, `stopstatedata`, `rxulpsesc`, `err` | CSI2 PHY | From PHY Sharing/Mux Logic |
| PHY Control | `phy`, `dphy` | To CSI2 PHY | To be muxed at SoC with IPU |
| IPI RAM RD I/F | `ipi_rclk`, `ipi_raddr`, `ipi_rdata`, `ipi_ren` | To IPI DP RF | IPI Read Port Memory 4Kx64 |
| IPI RAM WR I/F | `ipi_wclk`, `ipi_waddr`, `ipi_wdata`, `ipi_wen` | To IPI DP RF | IPI Write Port Memory |
| IPI I/F | `pixclk`, `ipi_vsync`, `ipi_hsync`, `ipi_pixen`, `ipi_pixdata`, `ipi_data_end`, `ipi_data_valid` | To Altek ISP | IPI pixel stream to ISP |
| Diagnostics | `*diag*` | — | Diagnostic/debug signals |

---

#### PHY Sharing and Camera Control Interface

(HAS §8.1.2, §2.2 Block Diagram)

- The MIPI-IF block includes PHY sharing logic that communicates with the IPU in the SoC to share the MIPI C/D-PHY. (HAS §2.2)
- PHY sharing supports two usage models:
  - **IPU owning the camera** — the IPU controls the MIPI PHY and camera pipeline.
  - **NVU owning the camera** — the NVU controls the MIPI PHY and camera pipeline.
- The PHY control signals (`phy`, `dphy`) are muxed at the SoC level between NVU and IPU. (HAS §8.7.2.2.3)
- During system boot, NVU may be unable to provide timely acknowledgment if `release_irq` occurs before NVU firmware is loaded. (HAS §8.1.2)

---

#### USB Camera Path: MSIF2IPI Bridge

(HAS §8.8.2.1.2.8, §2.5.1.6.5)

The MSIF2IPI block bridges USB video data into the IPI pixel stream consumed by the Altek CVISP ISP.

- The IPI output from MSIF2IPI feeds directly to the Altek CVISP module. (HAS §8.8.2.1.2.8, §2.5.1.6.5)
- MSIF2IPI reformats payload data from CSI packet format to IPI pixel format. (HAS §8.8.2.1.2.8.6)

**MSIF Protocol Signals** (HAS §8.8.2.1.2.8.3):

| Name | Direction | Width | Description |
|---|---|---|---|
| `msif_valid` | in | 1b | MSIF transaction valid bit |
| `msif_sop` | in | 1b | Start of packet indication |
| `msif_eop` | in | 1b | End of packet indication |
| `msif_data` | in | 64b | MIPI packet data |

**Supported MIPI CSI Data Types** (HAS §8.8.2.1.2.8):

| Data Type | Description |
|---|---|
| 0x00–0x07 | Short Packet Synchronization Data Types |
| 0x08–0x0F | Generic Short Packet Data Types |
| 0x10–0x17 | Generic Long Packet Data Types |
| 0x18–0x38 | (additional types per CSI-2 spec) |
| 0x39 | Reserved for MIPI CSE |
| 0x3A | Reserved for MIPI CSE |

---

#### Camera Telemetry and Debug Observability

(HAS §16.2.5)

The following camera-related fields are exposed via the NVU telemetry mechanism:

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| IPAPG MIPI Counter | Counter | RTC Tick | QW4 | MIPI PD in power gate |
| Wake by IO Counter | Snapshot | Count | QW13 | E.g., Camera Release IRQ wakeup events |
| Camera Sensor FPS | Snapshot | Count | QW20 | Avg/Max/Min/Current sensor frame rate |
| CVISP FPS | Snapshot | Count | QW20 | Avg/Max/Min/Current ISP output frame rate |

---

#### NVU PNR Tool — Camera Debug Utilities

(HAS §16.1.3)

- Receives camera RAW frames and ISP-processed output from the device via HECI and stores them on the host.
- The ISP tuning tool consumes RAW dump images to tune ISP parameters.
- Supports playback of camera frames into the pipeline to reproduce algorithm behavior without live sensors.

---

#### Camera Driver Application — FDK Build and PDT Configuration

(HAS §16.1.1.3, §16.1.1.4, §16.1.1.6.5.2, §16.1.1.6.6, §16.1.1.6.7)

- The physical camera driver is built as a WASM application using the WASM SDK; it is separate from the VPX Zephyr image and loaded by the application manager. (HAS §16.1.1.3)
- The NVU FDK supports creation of projects containing physical camera driver and vision algorithm applications, including libraries from firmware kits, third parties, and user-developed sources. (HAS §16.1.1.4)
- Camera driver applications are declared in the PDT JSON (`nvu_pdt.json`) with `"appType": "Camera_Device"`. (HAS §16.1.1.6.5.2)

**Example PDT JSON entry** (HAS §16.1.1.6.5.2):
```json
{
  "appName": "CameraOV1234",
  "appElfFile": "CameraOV1234.wasm",
  "appType": "Camera_Device",
  "vendor": "OMNIVISION",
  "variantId": "0",
  "variantName": "v1234",
  "usesNNAcceleration": false
}
```

**AppType Lookup Table entry for Camera_Device** (HAS §16.1.1.6.6):
```json
{ "type_id": 2, "type_name": "Camera_Device" }
```

**Variant ID derivation** (HAS §16.1.1.6.7):
- Camera_Device (type_id=2) + OMNIVISION (vendor_id=38) + variantId=0 → `0x0026020000000000`

---

#### MIPI-SysT Trace over Debug Trace Fabric

(HAS §2.5.1.20.1, §15.5.1.4.1, §15.5.1.4.2)

- NVU supports MIPI-SysT format trace output over the Debug


### Clock and Power Gating (2 facts)

#### NPK Power Gating (HAS 16.2.2)

- On retail devices, NPK is power gated by BIOS by default
- To enable NPK on retail devices, one of the following conditions must be met:
  - A valid debug token is present, **or**
  - The KET bit is enabled in the ECTRL register

#### NPX Clock Gating Telemetry (HAS 16.2.5)

The following telemetry field is exposed for debug and profiling purposes related to NPX clock gating state:

| Field | Type | Unit | QW | Usage | Comment |
|---|---|---|---|---|---|
| NPX Sleep Counter | Counter | RTC Tick | QW5 | Debug & Profiling (FW) | NPX Clock Gated |


### DMA Architecture (2 facts)

#### DMA Architecture

##### DMA Engine Overview

- The SMMU logic supports a dedicated DMA engine responsible for managing data movement from virtual to physical memory (2 Introduction > 2.5 Requirements > 2.5.1 Capabilities > 2.5.1.7 SRAM Sub-system > 2.5.1.7.3 SMMU Capabilities)
- The DMA engine operates under hardware (HW) control
- HW provides a programming interface to firmware (FW) for page management operations

##### Debug Interface for DMA Controller

- The TAP (Test Access Port) exposes test data registers that enable debug-time control of the DMA controller (15 Debug Capabilities > 15.7 Other)
- These TAP test data registers provide the following DMA-related debug capabilities:
  - **Debug channel selection** — allows selection of the active debug channel on the DMA controller
  - **DTF survivability feature programming** — controls the survivability feature of the Debug Trace Fabric (DTF)


### DSP Core (VPX2) (40 facts)

#### VPX2 DSP Core Debug Overview

The ARC VPX2 DSP is the control core of the NVU, running Zephyr RTOS and managing NVU control logic. It is supported by the Synopsys ARC MetaWare Development Toolkit for application software development. (8.3 VPX2, 16.1.1.1)

---

#### VPX2 Debug Capabilities

- **Run Control:** External logic can start, stop, and single-step the processor (2.5.1.1.1)
- **State Visibility:** Full visibility of processor state is available through the debug interface (2.5.1.1.1)
- **Breakpoint Support:** Breakpoint instruction support is included (2.5.1.1.1)
- **Post-Silicon Debug:** The VISA2 architecture is implemented; post-silicon debug utilizes the On-Chip Debugger (OCD) to access the VPX2 core via its sTAP connected to the secondary TAP port (15.2)
- **DTF Tracing:** VPX firmware supports DTF for sending firmware tracing messages to Northpeak, including in S0ix state (15.3)
- **Model Debug:** In debug mode, `RS3_WR_DISABLE` is set to `0`, unlocking the path to IMR from VPX/NPX via SMMU VMEM, enabling dumping of intermediate model results (15.3.1)

---

#### VPX2 Components

| Component | Version (HAS Ref: 8.3.2) |
|---|---|
| System | com.arc.hardware.System.1_0 |
| Debug Interface | com.arc.hardware.HS.Debug_Interface.1_0 |

---

#### VPX2 Debug Configuration

| Option | Value | HAS Ref |
|---|---|---|
| Testbench | rascal | 8.3.3 |
| SystemClockPeriodMultiplier | 1 | 8.3.3 |
| JTAGFrequency | 10 | 8.3.3 |

---

#### VPX2 Debug Integration Interfaces

| Interface | Port Name | Connectivity | Description | HAS Ref |
|---|---|---|---|---|
| JTAG | `jtag_*` | JTAG | To SoC | 8.3.4 |
| Debug Run Control | `arc_halt_req_a` | ARCSYNC | Run control halt request to ARCSYNC | 8.3.4 |
| DFX | `test_mode` | DFX | DFX Test Mode | 8.3.4 |

---

#### VPX2 Halt On Reset (Reset Debug) (8.3.5.1)

- From a ROM debug perspective, it is desirable to bypass ROM in order to debug reset vector code
- The VPX2 core must be halted on reset to support this use case
- Halt on reset is activated when the **`NVU_VPX_HALT_Fuse`** is set to `1`
- A hardware flow is implemented to keep the core in a halted state based on `VPX_HALT_FUSE`
- The reset vector within the VPX can be updated to point to AONRF
- **CRPM** is responsible for bringing the core out of HALT state (see NVU CRPM MAS for details)
- Reset-break capability is handled via STAP, which sends an indication to the HW FSM to maintain the halted state on reset exit (DFX HAS)
- The halt-on-reset flow applies after IPAPG exit and in the Exception reset flow

---

#### DTF Memory Map (VPX2 Address Space)

| Block | Sub Region | Size | Start Address | End Address | HAS Ref |
|---|---|---|---|---|---|
| DTF | DTF | 4 KB | 0xF3400000 | 0xF3401000 | 8.2.2 |

---

#### Telemetry: VPX2 Debug & Profiling Fields (16.2.5)

| Field | Type | Unit | Quadword | Comment |
|---|---|---|---|---|
| D0.200M Counter | Counter | RTC Tick | QW1 | VPX active at 200 MHz |
| D0.400M Counter | Counter | RTC Tick | QW1 | VPX active at 400 MHz |
| D0.Sleep Counter | Counter | RTC Tick | QW2 | VPX Clock Gated |

---

#### VPX2 Firmware Structure and Image Generation (16.1.1)

- VPX firmware source is located in the **`vpxfw/`** folder, containing BSP, board definitions, and applications (16.1.1.2)
- The compiled VPX core firmware binary is **`zephyr.bin`** (16.1.1.6.8)
- The **Base NVU Firmware** image includes: VPX core firmware, NPX core firmware, Core WASM APP, and AON image (16.1.1.6)

#### NPX Log Integration via VPX (16.1.4)

- NPX writes logs into a shared buffer with a header
- VPX collects and re-encodes those logs into Sys-T format for uniform output
- Log labels must identify which NPX core produced each entry


### Debug and Trace (108 facts)

### Debug and Trace

#### 16.2 Always-ON Vision Firmware Debug

### 16.2.1 Firmware Debug Mechanisms
(Chapter 12: AON Vision FDK and Debug > 16.2.1)

- **Base FW traces to DTF** — NVU base firmware traces are exposed to DFT and can be routed to multiple destinations (NPK or DDR).
- **App FW traces to DTF** — NVU application firmware traces are exposed to DFT and can be routed to multiple destinations (NPK or DDR). Note: In TTL, App FW traces to DTF can be exposed; in HML and beyond, traces will not be exposed to DTF in post-EOM and debug lock state.
- **NN Algorithm Profiling** — Algorithm-specific test/debug feature supported by specific algorithm test firmware.

---

### 16.2.2 Firmware Debug Policies
(Chapter 12: AON Vision FDK and Debug > 16.2.2)

The table below summarizes debug mechanism support across lifecycle and lock states.

| Debug Mechanism | Pre-EOM & Debug Unlock | Pre-EOM & Debug Lock ³ | Post-EOM & Debug Unlock ³ | Post-EOM & Debug Lock |
|---|---|---|---|---|
| OS debug and log | Support | Support | Support | Only ROM/BUP |
| OS image dump, tuning, probe | Support | Support | Support | No Support |
| OS profiling w/ FW statistics | Support | Support | Support | No Support |
| IP telemetry | Support | Support | Support | Support |
| JTAG debug | Support | Support | Support | No Support |
| Base FW traces to DTF | Support | Support | Support | Support ¹ |
| App FW traces to DTF | Support | Support | Support | Support (TTL) ² / No Support (HML+) |
| NN Algorithm Profiling | Support | Support | Support | No Support |

**Notes:**

- **Note 1:** Base FW traces to DTF remain supported in the Post-EOM & Debug Lock state.
- **Note 2:** In TTL, App FW is from Intel; therefore App FW traces to DTF can be exposed. In HML and beyond, App FW originates from a third party; traces will not be exposed to DTF in the Post-EOM & Debug Lock state.
- **Note 3:** Although "Post-EOM & Debug Unlock" appears identical to "Pre-EOM & Debug Unlock" and "Pre-EOM & Debug Lock" in the above table, the actual firmware running in the NVU differs between these states.

---

### 16.2.4 Post-Production / Post-EOM Debug Flows
(Chapter 12: AON Vision FDK and Debug > 16.2.4)

- If the SoC is unlocked (via OEM token-based unlock, Intel red unlock, or other equivalent mechanisms), only a driver package with debug-signed firmware can be used, and the host interface will not be disconnected after unlock.

---

### 16.2.5 Telemetry Data and Exposure to OS
(Chapter 12: AON Vision FDK and Debug > 16.2.5)

Telemetry data is organized into quadwords (QW) and classified by usage category, type, and unit.

#### Debug & Profiling (FW) Telemetry Fields

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| IPAPG Main Counter | Counter | RTC Tick | QW3 | Main PD in PG |
| IPAPG USB Counter | Counter | RTC Tick | QW4 | USB PD in PG |
| NPX Active Counter | Counter | RTC Tick | QW5 | NPX active; may represent Max Power |
| Boot Latency Prior HLUP | Counter | RTC Tick | QW10 | — |
| Boot Latency Post HLUP | Counter | RTC Tick | QW10 | — |
| NN Execution Time Max | Counter | RTC Tick | QW11 | — |
| NN Execution Time Avg | Counter | RTC Tick | QW11 | — |
| SRAM Status | Snapshot | Count | QW19 | # of active/retention/shutdown banks |
| Algorithm FPS | Snapshot | Count | QW21 | Avg/Max/Min/Current |
| Reserved | — | — | QW21 | — |

#### Data Leaking Threat Report Telemetry Fields

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Violator_Top2 | Snapshot | App ID | QW4 | App ID with the 2nd-highest number of violations |
| Violator_Top3 | Snapshot | App ID | QW4 | App ID with the 3rd-highest number of violations |

#### UX Study (FW) Telemetry Fields

##### Face Height Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face Height Histogram Header | Snapshot | NA | QW5 | Face Height histogram |
| Face Height Histogram Bin0 | Snapshot | NA | QW5 | Face Height histogram |
| Face Height Histogram Bin3 | Snapshot | NA | QW7 | Face Height histogram |
| Face Height Histogram Bin4 | Snapshot | NA | QW7 | Face Height histogram |
| Face Height Histogram Bin5 | Snapshot | NA | QW8 | Face Height histogram |
| Face Height Histogram Bin6 | Snapshot | NA | QW8 | Face Height histogram |
| Face Height Histogram Bin7 | Snapshot | NA | QW9 | Face Height histogram |

##### Face Yaw Orientation Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face Yaw Histogram Header | Snapshot | NA | QW9 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin0 | Snapshot | NA | QW10 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin1 | Snapshot | NA | QW10 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin2 | Snapshot | NA | QW11 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin3 | Snapshot | NA | QW11 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin4 | Snapshot | NA | QW12 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin5 | Snapshot | NA | QW12 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin6 | Snapshot | NA | QW13 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin7 | Snapshot | NA | QW13 | Face Yaw orientation histogram |

##### Face Pitch Orientation Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face Pitch Histogram Header | Snapshot | NA | QW14 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin0 | Snapshot | NA | QW14 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin1 | Snapshot | NA | QW15 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin2 | Snapshot | NA | QW15 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin3 | Snapshot | NA | QW16 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin4 | Snapshot | NA | QW16 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin5 | Snapshot | NA | QW17 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin6 | Snapshot | NA | QW17 | Face Pitch orientation histogram |
| Face Pitch Histogram Bin7 | Snapshot | NA | QW18 | Face Pitch orientation histogram |

##### Face Roll Orientation Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face Roll Histogram Header | Snapshot | NA | QW18 | Face Roll orientation histogram |
| Face Roll Histogram Bin0 | Snapshot | NA | QW19 | Face Roll orientation histogram |
| Face Roll Histogram Bin1 | Snapshot | NA | QW19 | Face Roll orientation histogram |
| Face Roll Histogram Bin2 | Snapshot | NA | QW20 | Face Roll orientation histogram |
| Face Roll Histogram Bin3 | Snapshot | NA | QW20 | Face Roll orientation histogram |
| Face Roll Histogram Bin4 | Snapshot | NA | QW21 | Face Roll orientation histogram |
| Face Roll Histogram Bin5 | Snapshot | NA | QW21 | Face Roll orientation histogram |
| Face Roll Histogram Bin6 | Snapshot | NA | QW22 | Face Roll orientation histogram |
| Face Roll Histogram Bin7 | Snapshot | NA | QW22 | Face Roll orientation histogram |

##### Face ID Similarity Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face ID Similarity Histogram Header | Snapshot | NA | QW27 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin0 | Snapshot | NA | QW28 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin1 | Snapshot | NA | QW28 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin2 | Snapshot | NA | QW29 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin3 | Snapshot | NA | QW29 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin4 | Snapshot | NA | QW30 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin5 | Snapshot | NA | QW30 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin6 | Snapshot | NA | QW31 | FaceID similarity histogram |
| Face ID Similarity Histogram Bin7 | Snapshot | NA | QW31 | FaceID similarity histogram |

##### Steady Scene Histogram

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Steady Scene Histogram Bin1 | Snapshot | NA | QW33 | Histogram of scene dynamic range in steady state |
| Steady Scene Histogram Bin2 | Snapshot | NA | QW33 | Histogram of scene dynamic range in steady state |
| Steady Scene Histogram Bin3 | Snapshot | NA | QW34 | Histogram of scene dynamic range in steady state |


### IOSF Bridge (1 facts)

#### MSIF2IPI Bridge

(HAS: 8 IP-Specific Description > 8.8 USB Interface Sub-System > 8.8.2 Sub-Blocks > 8.8.2.1 USB Video Offload Logic > 8.8.2.1.2 Sub-Blocks > 8.8.2.1.2.8 MSIF2IPI)

- This bridge sits between the SIO Component's BIU Interface and the Main NOC/IOSF2AXI's AXI Port


### IPC Messaging (4 facts)

#### IPC Messaging

Telemetry fields for ISH IPC messaging are exposed to the OS as snapshot counters for firmware debug and profiling purposes. These fields capture both outbound and inbound message activity at the time of telemetry collection. (HAS §16.2.5)

- All fields are of type **Snapshot** — values represent a point-in-time capture rather than a continuously accumulated hardware counter.
- Fields are packed into quadwords (QW) within the telemetry data structure exposed to the OS.
- Both message count and byte volume are tracked independently for each traffic direction (outbound and inbound).

##### ISH IPC Telemetry Fields

| Field | Usage | Type | Unit | QW |
|---|---|---|---|---|
| ISH IPC Message Out Counter | Debug & Profiling (FW) | Snapshot | Count | QW16 |
| ISH IPC Message Out Bytes | Debug & Profiling (FW) | Snapshot | Byte | QW16 |
| ISH IPC Message In Counter | Debug & Profiling (FW) | Snapshot | Count | QW17 |
| ISH IPC Message In Bytes | Debug & Profiling (FW) | Snapshot | Byte | QW17 |

- **ISH IPC Message Out Counter** — Snapshot count of IPC messages transmitted outbound from the NVU to the ISH. (HAS §16.2.5)
- **ISH IPC Message Out Bytes** — Snapshot of the total byte volume of outbound IPC messages sent to the ISH. (HAS §16.2.5)
- **ISH IPC Message In Counter** — Snapshot count of IPC messages received inbound from the ISH. (HAS §16.2.5)
- **ISH IPC Message In Bytes** — Snapshot of the total byte volume of inbound IPC messages received from the ISH. (HAS §16.2.5)


### Inference Engine (1 facts)

#### NN Algorithm Profiling — Model Loading Latency

- Profiling captures **latency metrics (average / minimum / maximum)** for the model loading operation (HAS 16.2.6)
- Model loading latency encompasses the complete duration of:
  - Transferring the model from **IMR (Isolated Memory Region)** to **SRAM**
  - Performing **model hash verification** as part of the load sequence


### Interrupt Configuration (59 facts)

#### Interrupt Configuration

#### Telemetry Service IRQ

(HAS §16.2.5 — AON Vision FDK and Debug > Always-ON Vision Firmware Debug > Telemetry Data and Exposure to OS)

- NVU HW provides a `telemetry_service` IRQ and associated status to NVU FW
- The `telemetry_service` IRQ mechanism follows the same pattern as the `vision_service` IRQ implementation

> **Note:** No register-level offset, size, or reset value data for interrupt configuration registers is present in the provided HAS facts. The facts supplied primarily describe the MSIF2IPI sub-block (§8.8.2.1.2.8) within the USB Interface Sub-System, which is not directly relevant to the NVU debug Interrupt Configuration section. The table below is therefore omitted pending availability of register map data from the relevant HAS sections.


### Neural Network Accelerator (57 facts)

#### Neural Network Accelerator Debug

##### NPX6 Debug Memory Map — ARCTrace and L1 Core Registers
(§8.2.3.2.2)

The following registers are accessible via the NPX6 Debug Memory Map. The base region `0x6000_0000 – 0x7000_0000` spans 256 MB and is mapped to Non-Volatile SRAM.

| Name | Offset | Mode | Description |
|---|---|---|---|
| DB_STAT | 0x000 | — | Debug Status register |
| DB_CMD | 0x004 | — | Debug Command register |
| DB_ADDR | 0x008 | — | Debug Address register |
| DB_DATA | 0x00C | — | Debug Data register |
| DB_RESET | 0x010 | — | Debug Reset register |
| ITCTRL | 0xF00 | — | Integration Mode Control register – not used, RAZ |
| CLAIMSET | 0xFA0 | R/W | Claim Tag Set register |
| CLAIMCLR | 0xFA4 | R/W | Claim Tag Clear register |

---

##### NPX6-1K Debug Configuration
(§8.4.2, §8.4.4)

**Configuration Option:**

| Option Name | NVU Value | Description |
|---|---|---|
| NPU_ARC_TRACE | CoreSight | ARC Trace — not supported on NVU |

**Debug-Related Integration Ports (CORE_ARCHIPELAGO):**

| Interface | Port Name | Connectivity | Comments |
|---|---|---|---|
| Debug Clock | `pclkdbg` | CRPM | Connect to NPX Functional Clock / 2 |
| Trace ATB | `at*` | Open/Tie-Off | Unused |
| APB Debug | `arct0_p*` | Fabric | Debug APB port |
| Debug Security | `sl0nl1arc_niden`, `sl0nl1_dbgen` | DFX | Connect to DFX Secure Plugin (Slice DBGEN, NIDEN) |
| Debug Security | `arct0_niden`, `arct0_dbgen` | DFX | Connect to DFX Secure Plugin (ARC Trace DBGEN, NIDEN) |

---

##### DFx Features
(§2.8.1)

- DFx features and functions are included in the NVU DFX HAS.
- Test firmware containing DFx-specific behavior is not included in formal BKC releases and is not captured in this document. (§16.2.1)

---

##### Debug Trace Fabric (DTF) — NN-Related Flows
(§15.5.1.8, §15.5.1.8.2)

- Writing to addresses `D64TS_LO_ADDR` and `D64TS_HI_ADDR` in sequence sends a `D64TS` message type to the Encoder. (§15.5.1.8)
- Once the Encoder FIFO is read as empty, it cannot transition back to non-empty, because firmware is no longer sending debug data to the DTF packetizer. (§15.5.1.8.2)

---

##### NN Algorithm Profiling
(§16.2.6)

The following profiling features are available for Neural Network models via the Synopsys toolchain. Each feature indicates whether it requires an NNX rebuild and/or an NPX firmware rebuild.

| Feature | Function | NNX Rebuild | NPX FW Rebuild |
|---|---|---|---|
| Hash Checking | Checks whether reference and target outputs of a model are bit-exact | No | Yes (+Inference engine testbench library) |
| Per-layer profiling | Provides detailed per-layer information about model performance | Yes (`-profile_L1`, +Extra XOPS) | Yes (+Inference engine testbench library) |
| Tensor Dump | Captures values of intermediate tensors (option to dump only selected tensors) | Yes (`-tensor_dump`, +Extra XOPS) | Yes (+Inference engine testbench library) |

- Latency metrics (average, minimum, maximum) for model inference are measured from NPX execution entry until NPX returns. (§16.2.6)

---

##### NVU Profiling Tool — NN Offload Metrics
(§16.1.2)

- The NVU Profiling Tool provides system-wide performance and behavior metrics for NVU firmware, including BSP, kernel services, and WASM applications.
- Captures timing and resource usage for VPX tasks, interrupts, **NN offloads**, and WASM app–related performance counters.
- Security and performance considerations apply to profiling configurations.

---

##### NVU Image Tool — Neural Network Model Integration
(§16.1.1.6, §16.1.1.6.1, §16.1.1.6.5.1, §16.1.1.6.8, §16.1.1.6.9)

- The NVU Image Tool supports generation of **Extension NVU Firmware**, which includes multiple WASM apps, multiple Neural Network models, and PDT binary data.
- Neural network models (`.nnx` files) are placed in the image source folder; filenames are specified in the PDT JSON configuration.
- Automatic inclusion of NN models is supported for apps with neural acceleration.
- In the Extension Firmware generation flow, NN models are specified using the `nnModelFileNames` array:
  - A single entry is used for one model; multiple entries are used for multiple models.
  - Each model receives a unique variant ID with a model index.

---

##### Telemetry Data — NN/Vision Metrics Exposure to OS
(§16.2.5)

PMC allocates two telemetry regions for NVU telemetry data:
- **`NVU_PM_Telemetry_Data`** — receives Table #1 data pushed by firmware.
- **`NVU_IP_Telemetry_Data`** — receives Table #2 data pushed by firmware.

**Table #2 — UX Study (FW) Fields:**

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| User Presence with Attention | Counter | Second | QW1 | Time of user presence with attention |
| User Presence without Attention | Counter | Second | QW1 | Time of user presence with no attention |
| User Absence | Counter | Second | QW2 | Time of user not present |
| Onlooker Presence | Counter | Second | QW2 | Time of onlooker detected |
| Face Detection Confidence Histogram Header | Snapshot | NA | QW23 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin0 | Snapshot | NA | QW23 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin1 | Snapshot | NA | QW24 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin2 | Snapshot | NA | QW24 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin3 | Snapshot | NA | QW25 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin4 | Snapshot | NA | QW25 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin5 | Snapshot | NA | QW26 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin6 | Snapshot | NA | QW26 | Face detection confidence histogram |
| Face Detection Confidence Histogram Bin7 | Snapshot | NA | QW27 | Face detection confidence histogram |

---

##### Firmware Debug Mechanisms
(§16.2.1)

- OS SW debug mechanisms include: debug settings via HECI/SMHI, ETW provider for logging, log verbosity control, crash dump support, OS image dump, tuning, and probe capabilities.
- For the full list of firmware tracing messages supported, refer to the FW Architecture Specification listed in the References section. (§15.3)


### NoC Fabric (62 facts)

#### NoC Fabric — Debug Trace Fabric (DTF)

---

#### Overview

(HAS §2.5.1.20, §15.5.1)

- NVU includes a DTF Source Packetizer (SRCPKT) and DTF Encoder (SRCENC) to support firmware instrumentation trace output to Intel Trace Hub (NorthPeak).
- The DTF encoder is a sub-IP instantiated within NVU IP; it interfaces to the external DTF topology of arbiters, which eventually target the trace aggregator.
- FW debug messages are transferred to the trace aggregator in a **lossless, in-order** fashion across the DTF fabric.
- NVU HW VISA does **not** use the DTF packetizer/encoder interface.

---

#### IOSF-to-AXI Bridge Interface

(HAS §2.5.1.11)

- The IOSF Bridge acts as a target to the IOSF Primary Channel to expose registers accessed by the Host CPU and the TAM (DFx).
- The IOSF bridge generates cycles on RS0/3 based on `AxUser` information.

---

#### DTF Packet Format

(HAS §15.5.1.3, §15.5.1.5)

- The desired output sequence from the NVU DTF port is: **D64TS → D64 (×N) → D64M**
- Sys-T protocol packets use the **D64-TS** packet as header, followed by message payload (**D64** packets), ending with a **D64M** packet.
- The DTF encoder inserts an HW timestamp into the packet; the timestamp value is NVU's local ART value (`NVU_local_art_value[55:0]` connected to `dtfe_timestamp_value[55:0]`).
- The `Type` field is used; no SOP/EOP usage.

**FW message production sequence:**
1. FW writes a **D64TS** packet (Sys-T Event Header) to `D64TS_LO/HI_REG`.
2. FW writes intermediate 32-bit data chunks to **`DATA_WITHOUT_EOP`** register → generates D64 message type to Encoder.
3. FW writes the final 32-bit chunk to **`DATA_WITH_EOP`** register → generates D64M message type to Encoder.
4. SRCPKT concatenates two 32-bit chunks into 64-bit before forwarding to SRCENC (APB interface is 32-bit; packetizer-to-encoder interface is 64-bit).
5. SRCENC delivers the complete FW debug message to the DTF fabric in a lossless fashion.

---

#### POR Mode Configuration

(HAS §15.5.1.5.2)

- `dtfe_timestamp_valid` is tied to `'1'`; ART timestamp value connected to local ART.
- Crystal Clock is connected to NVU XTAL clock.
- LTA logic is **enabled** (`DTFE_NO_LTA` parameter = 0) to allow the encoder to insert timestamps.
- `DTFE_USE_LOW_RATIO` parameter shall be set to **1**.
- `ClkReq/Ack` ensures the DTF interface is IDLE.
- Clocks for repeaters outside NVU are provided by SoC; reset for repeaters and arbiter is provided by NVU IP. This reset is asserted when NVU IP enters IPAPG.
- IPAPG flow also ensures the DTF interface is IDLE.

---

#### Register: `PCKTZR_DTF_SRC_CONFIG`

(HAS §15.5.1.5.2.1)

**Offset:** TBD

| Bits | Access | Reset | Field Name | Description |
|------|--------|-------|------------|-------------|
| 0:0 | RW | 0 | `SRC_EN` | Enable for source packetizer |
| 1:1 | RW | 0 | `DEST_ID` | Specifies which trace aggregator to use |
| 2:2 | RW | 0 | `ENC_CG_OVRD` | Encoder clock gating override |
| 3:3 | RW | 1 | `LTA_CLOCK_LOW_FREQ` | When DTF clock frequency ≤ 5× XTAL frequency, this bit should be set. Connected to `dtfe_local_clock_low_freq`. |
| 5:4 | RW | 0 | `LTA_CNTR_WIDTH` | Fast Counter width. Fast counter is enabled only when `LTA_CLOCK_LOW_FREQ` = 0. Connected to `dtfe_fast_cnt_width[1:0]`. |
| 31:6 | — | — | Reserved | — |

**`LTA_CLOCK_LOW_FREQ` value definitions:**

| Value | Definition |
|-------|------------|
| 0 | Enables usage of fast counter for higher granularity in timestamp |
| 1 | Fast Counter is 0 |

**`LTA_CNTR_WIDTH` value definitions:**

| Value | Definition |
|-------|------------|
| 0 | 7-bit Fast Counter |
| 1 | 8-bit Fast Counter |
| 2 | 6-bit Fast Counter |
| 3 | Reserved |

---

#### DTF Timestamping

(HAS §15.5.1.7)

- FW reads the XTAL frequency based on `PCKTZR_DTF_SRC_STATUS.TS_BIT_SHIFT_VAL`.
- FW is expected to program `PCKTZR_DTF_SRC_CONFIG.LTA_CNTR_WIDTH` and `PCKTZR_DTF_SRC_CONFIG.LTA_CLOCK_LOW_FREQ` appropriately before enabling the packetizer.

---

#### DTF FW Debug Flow

(HAS §15.5.1.8.1)

- FW must complete **HH-SYNC** to initialize the NVU ART timer before starting DTF trace.
- FW must program `LTA_CNTR_WIDTH`, `LTA_CLOCK_LOW_FREQ`, and other configuration fields **before** enabling the packetizer (`SRC_EN`).

---

#### DTF FW Clock/Power Gating Flow

(HAS §15.5.1.8.2)

- When FW is done sending trace messages, it must write `SRC_EN` (source_enable bit in Packetizer) to `0`.
- Encoder FIFO empty and Arbiter FIFO empty status are logged as status bits in the DTF status register (`PCKTZR_DTF_SRC_STATUS`).

**Drain sequence before entering PG/CG:**
1. FW writes `SRC_EN = 0`.
2. FW reads the DTF status register; if **Encoder FIFO empty = 1**, proceed.
3. FW reads the DTF status register a **second time** to check **Arbiter FIFO empty** status (minimum delay of **7 clocks** between the two reads, to ensure repeaters between Encoder and Arbiter are also drained).
4. When both empty bits are set to `1`, Encoder and Arbiter are confirmed empty — it is safe to initiate PG or CG.


### PMC Integration and Wake (97 facts)

#### PMC Integration and Wake

> **Note:** The facts provided do not contain PMC Integration and Wake specific content. The 97 HAS facts supplied are scoped entirely to Chapter 12: AON Vision FDK and Debug sections covering the FDK build flow, ImageTool, profiling tool, and PNR tool. No PMC Integration and Wake register definitions, behavioral sequences, or related architecture data are present in the provided fact set. The markdown below accurately synthesizes only what the supplied facts contain.

---

#### AON Vision Firmware Development Kit (FDK) Overview

(HAS §16.1)

- The AON Vision FDK allows developers to write extended drivers and applications to customize their firmware.
- The FDK flow covers firmware build, image generation, profiling, and PNR tooling.

---

#### Firmware Code Structure

(HAS §16.1.1.2)

The firmware code is organized into several modules:

| Module | Location |
|---|---|
| Application Management Module | `modules/app-mgmt/` |
| Vision and Math Library (vmlib) | `modules/vmlib/` |

---

#### Firmware Build Flow

(HAS §16.1.1.3, §16.1.1.4.2)

- The Vision and Math Library (`vmlib`) is built separately and integrated as a binary.
- The build process is initiated using the `west build` command from Zephyr.
- Like any other CMake-based system, the build process takes place in two stages:
  - First, build files are generated using the `cmake` tool with the Ninja generator.
  - Then, source files are compiled and images are produced.
- A project may select several applications, which are then stitched together to create a final executable image.

---

#### NVU FDK Project Structure

(HAS §16.1.1.4.1)

| Component | Description |
|---|---|
| `project.json` | Describes project information such as version or customized configurations |
| `selected_functions.json` | Lists the applications selected for building firmware |
| `out/` | Contains the project executable images |
| `build/` | Stores the CMake build files |
| `app/` | Root folder for applications |
| `app/<application_folder>/` | Root folder of a WASM application; must use a unique folder name |
| `app/<application_folder>/src/` | Contains the main entry function of the WASM application |

---

#### NVU Image Generation Flow and ImageTool

(HAS §16.1.1.6)

##### Supported Features

(HAS §16.1.1.6.1)

- Supports both **Base** and **Extension** firmware types.
- Automatic extension firmware generation from PDT JSON files.
- Smart variant ID generation using app type and vendor lookups.
- Supports version management and build date generation.

##### Basic Syntax

(HAS §16.1.1.6.3.1)

```
python ImageTool.py -t <BASE|EXTENSION> -fv <version> -i <image_path> [options]
```

**Command Line Options:**

| Option | Description |
|---|---|
| `-t`, `--type` | **Required.** Type of firmware: `BASE` or `EXTENSION` |
| `-fv`, `--fwversion` | Firmware version in format `x.x.x.xxxx` |
| `-b`, `--fwversionfile` | Path to directory containing version file |
| `--pdt` | Path to PDT JSON file (recommended for Extension firmware) |

##### PDT JSON Configuration (Recommended for Extension Firmware)

(HAS §16.1.1.6.5.1)

The `--pdt` option allows automatic generation of extension firmware from a single PDT (Platform Definition Table) JSON file. This approach:

- Automatically includes all WASM applications specified in the PDT.
- Generates proper variant IDs using app type and vendor lookups.
- Eliminates manual module configuration.

##### PDT JSON Format (`nvu_pdt.json`)

(HAS §16.1.1.6.5.2)

Key fields used in the PDT JSON:

| Field | Example Value | Description |
|---|---|---|
| `appName` | `"Face_Detection_App"` | Name of the application |
| `appElfFile` | `"face_detection.wasm"` / `"multi_model_app.wasm"` | WASM binary filename |
| `nnModelFileNames` | `["face_detection_model.nnx"]` | Array of NN model filenames |
| `reporters` | `["Image_Reformat"]` | Reporter list for the application |

**NN Model File Configuration:**

- **Single Model:** Use `nnModelFileNames: ["model.nnx"]` (array with one entry).
- **Multiple Models:** Use `nnModelFileNames: ["model1.nnx", "model2.nnx", "model3.nnx"]` (array with multiple entries).
- **Consistent Format:** Always use the array format for simplicity.

##### Required Lookup Tables

(HAS §16.1.1.6.6)

The tool requires two lookup tables in the images directory:

| File | Description | Example Entries |
|---|---|---|
| `apptype_list.json` | Maps app type names to numeric IDs | `{"type_id": 0, "type_name": "Core"}`, `{"type_id": 6, "type_name": "Face_Detection"}` |
| `vendor_list.json` | Maps vendor names to numeric IDs | `{"VendorID": 0, "VendorName": "INTEL"}`, `{"VendorID": 38, "VendorName": "OMNIVISION"}` |

##### Variant ID Generation

(HAS §16.1.1.6.7)

The tool automatically generates 64-bit variant IDs using the formula:

```
base_variant = (vendor_id << 48) | (type_id << 40) | (variant_id << 8)
```

- For NN models with multiple models per app, each model receives a unique variant ID.
- The 64-bit variant ID can be unpacked by firmware into separate fields:
  - Extract `variant_id`: `(variant >> 8) & 0xFFFFFFFF` (32 bits)

**Field Validation — Allocated Bit Ranges:**

| Field | Valid Range | Bit Width |
|---|---|---|
| Vendor IDs | 0–79 | 8 bits |
| App Type IDs | 0–15 | 8 bits |
| User Variant IDs | 0–4,294,967,295 | 32 bits |
| Model Index (NN models) | 0–255 | 8 bits |

- Each NN model receives a unique variant ID that firmware can use for specific model lookup.

##### Image Files Folder Structure

(HAS §16.1.1.6.8)

```
├── npx_core.bin          # NPX core firmware (for BASE firmware)
├── core_wasm_app.wasm    # Core WASM application (for BASE firmware)
├── aon_image.bin         # AON image (for BASE firmware)
├── *.wasm                # WASM apps (filenames specified in PDT JSON)
├── nvu_pdt.bin           # PDT binary data (for EXTENSION firmware)
├── apptype_list.json     # App type lookup table (required for --pdt)
├── vendor_list.json      # Vendor lookup table (required for --pdt)
├── zephyr.dts            # Device tree
└── zephyr.map            # Memory map
```

##### Extension Firmware Generation Flow

(HAS §16.1.1.6.9)

1. Parse `nvu_pdt.json` to find all apps.
2. Include each `appElfFile` as a `WASM_APP` module.
3. Include `nvu_pdt.bin` as the `PDT_DATA` module.
4. Generate variant IDs using `apptype_list.json` and `vendor_list.json`.

##### Output Files

(HAS §16.1.1.6.10)

| Output File | Firmware Type |
|---|---|
| `nvu_base_fw.bin` | Base firmware |
| `nvu_ext_fw.bin` | Extension firmware |

##### Examples

(HAS §16.1.1.6.4)

- **Generate Extension Firmware from PDT JSON (Recommended)**
- **Generate with Custom Manifests**

---

#### NVU Profiling Tool

(HAS §16.1.2)

- Provides low-overhead sampling and event tracing modes suitable for production-like workloads.
- **Output formats:** Prints profiling counter information to the console; also supports structured trace records.
- **Version and build extraction:** Supports retrieving firmware version, per-module component versions, and Windows host driver version.
- **Dynamic runtime control:** Allows the profiling tool to enable/disable firmware features and adjust runtime parameters, including:
  - Feature toggles
  - Sampling rates
  - Component-specific switches
- **Access restriction:** Profiling metrics are available **only in debug-unlocked mode**. Refer to the Debug Policy section for mode detection and host permissions.

---

#### NVU PNR Tool

(HAS §16.1.3)

- For dump buffers generated by different algorithm applications, the `data[]` field may include a manifest describing the data format, followed by the raw data itself. This manifest facilitates downstream processing.
- **Security:** Captured frames may contain sensitive user data; PNR export is subject to debug-lock/EOM policy.


### Peripheral Interfaces (20 facts)

#### I2C Controller

##### I2C Controller Configuration (HAS §8.17.3)

The NVU I2C controller is configured with the following functional parameters:

| Name | Type | Default Value | Description |
|------|------|---------------|-------------|
| SLAVE_INTERFACE_TYPE | uint32 | 0 | APB2 slave interface type |
| SLVERR_RESP_EN | uint32 | N/A | Not applicable for APB2 |
| APB_DATA_WIDTH | uint32 | — | APB data bus width |
| IC_CLK_FREQ_OPTIMIZATION | uint32 | 0x1 | Reduces system clock frequency (ic_clk) by reducing internal latency |

- Multi-master system operation is supported (HAS §7.2.3.2)

##### MIPI Camera I2C/I3C Sharing with IPU (HAS §8.7.2.1.7.2)

- MIPI cameras support an I2C target interface for programming; some modern cameras use I3C instead of I2C
- The I2C/I3C interface must be available to both the NVU and IPU based on current ownership
- IPU accesses the camera I2C/I3C interface via any of the LPSS 6×I2C/4×I3C controllers through driver-to-driver communication between the IP SW driver and the LPSS I2C driver
- NVU GPIO PMode must be changed when transferring I2C/I3C ownership; refer to the NVU Flow For Changing GPIO PMode procedure

---

#### UART Controller

##### Overview (HAS §2.5.1.17.1)

- The UART implements a four-wire, bi-directional point-to-point connection between the NVU and a peripheral
- Typical use case is connection to a GNSS/Modem device

---

#### Debug Use of Peripheral Interfaces

##### Firmware Debug Mechanisms — Direct HW-Connected Interfaces (HAS §16.2.1)

- **JTAG debug:** Requires a standard JTAG debugger connection; supports breakpoints and memory dumping
- **UART/I2C log:** Requires an FTDI device connection; supports debug settings and log output

##### Firmware Debug Policies — UART/I2C Log (HAS §16.2.2)

| Debug Mechanism | Pre-EOM & Debug Unlock | Pre-EOM & Debug Lock | Post-EOM & Debug Unlock | Post-EOM & Debug Lock |
|-----------------|------------------------|----------------------|-------------------------|-----------------------|
| UART/I2C log | Support | Support ³ | Support ³ | No Support |

> ³ See HAS §16.2.2 for footnote conditions.

##### Post-Production / Post-EOM Debug Restrictions (HAS §16.2.4)

- If the SoC remains locked post-EOM, only a driver package with production-signed firmware may be used
- The host interface is disconnected after boot
- **UART/I2C log is disabled**; JTAG is also restricted under this condition

---

#### Telemetry — I2C/I3C Interface Counters (HAS §16.2.5)

The following I2C/I3C telemetry fields are exposed to the OS for debug and profiling purposes:

| Field | Usage | Type | Unit | QW |
|-------|-------|------|------|----|
| I2C/I3C Write Access Counter | Debug & Profiling (FW) | Snapshot | Count | QW14 |
| I2C/I3C Write Amount | Debug & Profiling (FW) | Snapshot | Byte | QW14 |
| I2C/I3C Read Access Counter | Debug & Profiling (FW) | Snapshot | Count | QW15 |
| I2C/I3C Read Amount | Debug & Profiling (FW) | Snapshot | Byte | QW15 |

---

#### NVU Profiling Tool — BSP Peripheral Metrics (HAS §16.1.2)

- The NVU Profiling Tool supports retrieval of component-specific counters for both BSP and WASM applications
- BSP profiling metrics exposed for peripheral interfaces include:
  - **I2C Transaction Count** — total number of I2C transactions executed
  - IRQ Event Count
  - Wake Event count

---

#### NVU Logging Tool — Peripheral Log Backends (HAS §16.1.4)

- Defines tracing and logging pipelines for VPX and NPX processors
- Provides a unified, secure logging pipeline for VPX (with aggregated NPX logs) to multiple backends:
  - **HECI** — primary log collection client for the host
  - **UART** — optional backend, used for bring-up and debug scenarios


### Power States (12 facts)

#### Power States Telemetry Fields

The following telemetry fields are exposed by the Always-ON Vision firmware for debug and profiling of NVU power state transitions. All fields are of type **Counter**, measured in **RTC Ticks**, and are accessed via the telemetry data interface. (HAS §16.2.5)

#### Power State Residence Counters

- **D0i1 Counter** tracks the cumulative time the NVU has spent in the **Clock Gated** state.
- **D0i2 Counter** tracks the cumulative time the NVU has spent in the **Power Gated** state.

| Field | Type | Unit | QW | Description |
|---|---|---|---|---|
| D0i1 Counter | Counter | RTC Tick | QW2 | Cumulative residence time in D0i1 (NVU Clock Gated state) |
| D0i2 Counter | Counter | RTC Tick | QW3 | Cumulative residence time in D0i2 (NVU Power Gated state) |

#### D0i1 Transition Latency Counters

- **D0i1 Enter Max Latency** and **D0i1 Enter Avg Latency** capture the worst-case and average entry latency into the D0i1 (Clock Gated) state respectively.
- **D0i1 Exit Max Latency** and **D0i1 Exit Avg Latency** capture the worst-case and average exit latency from the D0i1 state respectively.

| Field | Type | Unit | QW | Description |
|---|---|---|---|---|
| D0i1 Enter Max Latency | Counter | RTC Tick | QW6 | Maximum observed entry latency into D0i1 |
| D0i1 Enter Avg Latency | Counter | RTC Tick | QW6 | Average entry latency into D0i1 |
| D0i1 Exit Max Latency | Counter | RTC Tick | QW7 | Maximum observed exit latency from D0i1 |
| D0i1 Exit Avg Latency | Counter | RTC Tick | QW7 | Average exit latency from D0i1 |

#### D0i2 Transition Latency Counters

- **D0i2 Enter Max Latency** and **D0i2 Enter Avg Latency** capture the worst-case and average entry latency into the D0i2 (Power Gated) state respectively.
- **D0i2 Exit Max Latency** and **D0i2 Exit Avg Latency** capture the worst-case and average exit latency from the D0i2 state respectively.

| Field | Type | Unit | QW | Description |
|---|---|---|---|---|
| D0i2 Enter Max Latency | Counter | RTC Tick | QW8 | Maximum observed entry latency into D0i2 |
| D0i2 Enter Avg Latency | Counter | RTC Tick | QW8 | Average entry latency into D0i2 |
| D0i2 Exit Max Latency | Counter | RTC Tick | QW9 | Maximum observed exit latency from D0i2 |
| D0i2 Exit Avg Latency | Counter | RTC Tick | QW9 | Average exit latency from D0i2 |


### SRAM and Memory (21 facts)

#### SRAM Sub-system Overview

The physical SRAM in NVU totals **3584 KB** and can be mapped in two modes (HAS §2.5.1.7.1):

- **Physically addressable memory** — accessed via the PMEM range of the address map
- **Page-able memory** — accessed via the VMEMP (virtual memory page) range; pages are mapped at **4 KB granularity** (configurable)

---

#### SRAM Controller / Slice Controller Capabilities

(HAS §2.5.1.7.2)

- Supports an **arbitrary number of slices**; slice count is dictated by physical placement of SRAM modules and operating frequency
- Configurable slice size; typical slice size is **512 KB**
- Supports **configurable data width**
- Supports **arbitrary SRAM technology**; restriction: all SRAM modules within a given slice must use the same technology
- **ECC protection**:
  - Hamming code: 9 b / 8 b ECC for 128-bit / 64-bit data paths respectively
  - Reports single-bit correctable errors (SBE) and multi-bit uncorrectable errors (MBE)
- **Configurable timing pipeline hooks** for high-frequency operation:
  - Configurable pipe stage on the read data path
  - Configurable pipe stage on the read-merge-write data path
- **FW override for SRAM Power Management**: FW can place any SRAM slice (all banks within a slice) into deep sleep or shut down
- **FW-initiated ECC scrub** supported for initializing SRAM modules

---

#### SMMU Capabilities

(HAS §2.5.1.7.3)

- SMMU logic supports **mapping/translation of virtual address space (IMR) to physical address space (SRAM)**
- Mapping is performed at the granularity of the configured page size; typical page size applies
- Mapping is usually virtual-to-physical of the same memory
- SMMU logic supports a **dedicated DMA engine** that manages data movement from virtual to physical memory; the DMA is under HW control and HW provides a programming interface to FW for page management
- **FW is responsible for programming all SMMU mappings**; HW does not apply any default mapping

---

#### Telemetry — SRAM and Memory Fields

The following telemetry fields related to SRAM and memory are captured as snapshots and **pushed to PMC Shared SRAM when allowed by PMC** (HAS §16.2.5):

| Field | Usage | Type | Unit | Quadword | Comment |
|---|---|---|---|---|---|
| IMR Read Access | Debug & Profiling (FW) | Snapshot | Count | QW18 | — |
| IMR Write Access | Debug & Profiling (FW) | Snapshot | Count | QW18 | — |
| SRAM Status | Debug & Profiling (FW) | Snapshot | Count | QW19 | Number of active / retention / shutdown banks |
| Steady Scene Histogram Bin5 | UX Study (FW) | Snapshot | N/A | QW35 | Histogram of scene dynamic range in steady state |

---

#### Debug Trace Fabric — SRAM Usage Note

(HAS §15.5.1.3)

- NVU FW pushes double-word (DW) debug messages into the DTF packetizer interface during its code flow under debug
- **Buffered mode where SRAM is used as intermediate storage is not recommended**

---

#### TAP Control

(HAS §15.7)

- The **Target Test Access Port (TAP)** provides the ability to control power enables to SRAM


### Secure Boot (6 facts)

#### Firmware Signature / Asset Decryption Policies

(HAS §16.2.3 – Chapter 12: AON Vision FDK and Debug > Always-ON Vision Firmware Debug)

- Key management and switching is performed by **ESE**, not by NVU. NVU adopts and follows SoC debug designs, which produces the policy behaviors described below.

The table below defines which signing/encryption key applies to each firmware asset depending on End-of-Manufacturing (EOM) state and debug lock/unlock state.

| Firmware Signing / Asset Encryption | Pre-EOM & Debug Unlock | Pre-EOM & Debug Lock | Post-EOM & Debug Unlock | Post-EOM & Debug Lock |
|-------------------------------------|------------------------|----------------------|-------------------------|-----------------------|
| BUP Signature | Debug Key | Production Key | Debug Key | Production Key |
| Base FW Signature | Debug Key | Production Key | Debug Key | Production Key |
| App FW Signature | Debug Key | Production Key | Debug Key | Production Key |
| Face ID Vector Encryption | Debug Key | Production Key | Debug Key | Production Key |

