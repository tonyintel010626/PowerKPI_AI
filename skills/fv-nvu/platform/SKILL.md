name: fv-nvu/platform
description: NVU platform integration — reset sequences, IP configuration, straps, fuses, electricals, BDF assignment, and platform references

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`) — william.willy.chin@intel.com, Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.
>
> **⚠️ NEVER trust AI 100%.** This skill file is a productivity aid, not a replacement for engineering judgment. AI can hallucinate, confuse similar IPs (e.g., NVU vs NVL/NPU6), or present outdated information as current. **When in doubt, verify with the owner/co-owner or check the authoritative HAS document directly.** For CoDeSign-based HAS verification, see the FV-NVU agent definition (`FV-NVU.md`).

# NVU Platform Integration

> **SAFETY**: Do NOT modify reset, fuse, or strap configurations without explicit user confirmation.
> Platform details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.

## Overview

The NVU (Neural Vision/Sensing Unit) is integrated into Intel Client SoC platforms as a **PCI RCiEP** (Root Complex Integrated Endpoint) connected via IOSF (Vendor ID `0x8086`, Device ID strap-configured via `nvu_br_strap_deviceid[15:0]`). It provides always-on visual sensing for MIPI and USB cameras with power targets of **5 mW** (MIPI @ 3 fps) and **8 mW** (USB @ 3 fps), and an area target of **< 3.5 mm²** for the 3.5 MB SRAM configuration.

Platform integration covers:
- Reset sequencing (Host Reset group, cold/warm/soft reset flows)
- IP configuration (functional parameters, clocks, power gating domains)
- Strap and fuse programming (device ID, boot mode, IP disable)
- PCI/BDF assignment and BAR mapping
- PMC interaction (Dashboard, PGCB, IP disable)
- Electrical specifications
- Target platform references (TitanLake, Novalake)


## Reset Sequence (HAS Section 10)

The NVU belongs to the **Host Reset group** and is **Chassis 2.2 compliant**. It does NOT support sending global reset requests to PMC.

### Reset Inputs

| Reset Signal | Mapped To | Scope |
|---|---|---|
| `nvu_side_rst_b` | Host group side_rst_b | Maps internally to side_rst_b for both the IOSF2AXI bridge and the NVU SBEP Host Register Reset |
| `nvu_prim_rst_b` | Host register reset / Functional Reset | Primary host register reset |
| `nvu_main_pgcb_rst_b` | PGCB reset | PGCB domain reset |

### Cold Reset (G3 → S0)

Cold reset occurs during initial power-on (G3 → S0). The HAS defines HW waveform sequences for:
- **Boot with Lid Closed** — sequence covering PMC PGCB power-down handshakes, VNN removal, wake detection, VNN restore, PGCB power-up, and ROM re-execution (Integration HAS Section 9)
- **Boot with Lid Open** — cold boot flow (Integration HAS Section 9)

During cold reset, all NVU registers are returned to their default/reset values.

### Warm Reset (S0 → Sx → S0)

Warm reset covers platform sleep transitions (with ResetPrep/ForcePwrGatePOK per Integration HAS):
- **S0 → Sx**: NVU is non-functional in platform Sx states. State is lost unless explicitly saved by firmware prior to entry. SRAM must be scrubbed after reset to prevent leakage of sensitive data (e.g., Face ID vectors).
- **Sx → S0**: NVU re-initializes as part of Host Reset group. Firmware must reload models and re-establish camera paths. NVU ROM must handle the Reset Prep interrupt during the S0 → Sx transition.

### Surprise Reset

**Surprise Reset = Global Reset** — NVU does NOT send global reset requests to PMC. A surprise reset is equivalent to a platform global reset (Integration HAS Section 9).

### Soft Reset (Exception Reset)

Soft reset is triggered by one of three sources:

| Source | Mechanism |
|---|---|
| FW-initiated reset | `ESE2NVU_IPC.RESET_BIT` set by firmware |
| Watchdog Expiry | NVU internal watchdog timer expires |
| ECC double-bit error | Uncorrectable ECC error in SRAM |

During exception reset:
- **RW/O registers** are cleared
- **PME** (Power Management Event) is asserted for host recovery notification
- NVU does NOT send a global reset request to PMC


## IP Configuration (HAS Section 4)

### Functional Parameters

| Parameter | Value | Description |
|---|---|---|
| `DST_ID_WIDTH` | 15 | IOSF destination ID width |
| `MD_WIDTH` | 127 | IOSF message data width |
| `MMAX_ADDR` | 63 | Maximum IOSF message address |
| `NUM_GPIO_PINS` | 32 | GPIO pin count |
| `NUM_I2C` | 3 | I2C controller count (3x I2C DesignWare peripheral controllers for sensor control) |
| `NUM_I3C` | 2 | I3C controller count (2x I3C DesignWare peripheral controllers for sensor control) |
| `NUM_SPI` | 2 | SPI controller count (2x SPI DesignWare peripheral controllers for sensor control) |
| `NUM_UART` | 3 | UART controller count (3x UART DesignWare peripheral controllers for sensor control) |
| `MNUMCHAN` | 1 | IOSF number of channels |
| `RS_WIDTH` | 1 | Root space width |
| `SAI_WIDTH` | 7 | Security Agent Identifier width |
| `SRC_ID_WIDTH` | 15 | IOSF source ID width |
| `TD_WIDTH` | 127 | IOSF target data width |
| `TMAX_ADDR` | 63 | Maximum IOSF target address |
| `TNUMCHAN` | 1 | IOSF target number of channels |
| `MNUMCHANL2` | 0 | IOSF master number of L2 channels (Integration HAS v0.8) |
| `TNUMCHANL2` | 0 | IOSF target number of L2 channels (Integration HAS v0.8) |
| `SRAM_SIZE` | 3584 KB | Total SRAM size |
| `NUM_SRAM_SLICES` | 7 | SRAM slice count |
| `SRAM_SLICE_SIZE` | 512 KB | Per-slice SRAM size |

### IOSF Traffic Class / Virtual Channels (from EAIG Security Review)

NVU supports **2 Virtual Channels** for upstream IOSF traffic:

| Virtual Channel | Traffic Class | Usage |
|---|---|---|
| **VC0** | TC0 | Default traffic — host IPC, register access, general DMA |
| **VC1** | TC1 | High-priority traffic — time-sensitive camera/inference data |

- Each PCI function has **two BDF assignments** for peer-to-peer (P2P) usage
- P2P streaming paths: **NVU↔XHCI** (USB camera offload) and **NVU↔IPU** (MIPI PHY sharing)
- VTd/SAI access control enforced on both CFG and MMIO spaces
- DFx: sTAP integrated, DFx secure plugin on DFx secure bus, in lowest power well, unmodified chassis code

### Physical Partitions

The NVU is organized into **6 physical partitions**:

| Partition | Description |
|---|---|
| `PAR_VPX` | VPX2 DSP processor partition |
| `PAR_NPX` | NPX6-1K NNA partition |
| `PAR_USB` | USB camera interface partition |
| `PAR_MIPI` | MIPI camera interface partition |
| `PAR_SRAM` | Shared SRAM fabric partition |
| `PAR_MAIN` | Main control/host interface partition |

### Clocks

| Clock Signal | Description |
|---|---|
| `nvu_func_clk` | Primary functional clock |
| `nvu_pgcb_clk` | PGCB domain clock |
| `nvu_pixel_clk` | Pixel processing clock |
| `nvu_rtc_clk` | Real-time clock |
| `nvu_xtal_clk` | Crystal oscillator clock |

Clock gating interfaces (request/acknowledge pairs):
- `FUNC_CLK` req/ack
- `PGCB_CLK` req/ack
- `XTAL_CLK` req/ack
- `CDPHY_XTAL_CLK` req/ack
- `PIXEL_CLK` req/ack

### Detailed IO Peripheral Parameters (HAS Sections 8.17–8.21)

#### I2C Controller (HAS Section 8.17)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `IC_CLOCK_PERIOD` | 10 (100 MHz input) | Core clock period in ns |
| `IC_MAX_SPEED_MODE` | 0x3 (High Speed) | Supports SS/FS/HS |
| `IC_TX_BUFFER_DEPTH` | 64 | TX FIFO depth |
| `IC_RX_BUFFER_DEPTH` | 64 | RX FIFO depth |
| `IC_CAP_LOADING` | 100 pF | Bus capacitance loading |
| `IC_DEFAULT_FS_SPKLEN` | 0xA | Fast-speed spike length filter |
| `IC_DEFAULT_HS_SPKLEN` | 0x4 | High-speed spike length filter |

**SCL Timing Counts per Speed Mode:**

| Speed | SCL High Count | SCL Low Count |
|-------|---------------|--------------|
| Standard (100 KHz) | `IC_SS_SCL_HIGH_COUNT` = 0x03D9 | `IC_SS_SCL_LOW_COUNT` = 0x03E6 |
| Fast (400 KHz) | `IC_FS_SCL_HIGH_COUNT` = 0xE2 | `IC_FS_SCL_LOW_COUNT` = 0xF8 |
| High Speed (3.4 MHz) | `IC_HS_SCL_HIGH_COUNT` = 0x52 | `IC_HS_SCL_LOW_COUNT` = 0x64 |

> **FW restrictions**: HCNT must be programmed as HCNT+1 for correct duty cycle. `TX_EMPTY_CTRL` must NOT be used. SCL duty cycle must be maintained at ~50%.

#### SPI Controller (HAS Section 8.18)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `SSI_CLK` | 100 MHz | SPI system clock |
| Max Serial Clock | 25 MHz | Maximum SPI bus speed |
| `SSI_MAX_XFER_SIZE` | 32 | Max transfer size in bits |
| `SSI_RX_FIFO_DEPTH` | 0x40 (64) | RX FIFO depth |
| `SSI_TX_FIFO_DEPTH` | 0x40 (64) | TX FIFO depth |
| `SSI_NUM_SLAVES` | 2 | Number of chip selects |
| `SSI_HC_FRF` | 0 | Fixed frame format |
| `SSI_DFLT_FRF` | 0 | Default frame format (Motorola SPI) |

**Speed Configuration:**

| Speed | SCKDV (Divisor) |
|-------|-----------------|
| 1 Mbps | 100 |
| 10 Mbps | 10 |
| 25 Mbps | 4 |

> **FW restriction**: No back pressure on RX DMA handshake — FW must ensure RX FIFO is read in time to avoid overflow. SSP and Microwire modes are **not POR** (only Motorola SPI is supported).

#### UART Controller (HAS Section 8.19)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `FIFO_MODE` | 64 | UART FIFO depth |
| `UART_RS485_INTERFACE_EN` | 1 | RS-485 mode supported |
| `UART_9BIT_DATA_EN` | 1 | 9-bit data mode supported |
| `AFCE_MODE` | 1 | Auto flow control (CTS/RTS) enabled |
| `UART_16550_COMPATIBLE` | 1 | 16550-compatible register interface |
| `FRACTIONAL_BAUD_DIVISOR_EN` | 1 | Fractional baud rate divisor supported |
| `DLF_SIZE` | 4 | Divisor Latch Fraction size (4 bits) |
| `DMA_EXTRA` | 1 | 4-wire DMA handshake mode |

#### I3C Controller (HAS Section 8.20)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `IC_DEVICE_ROLE` | 1 | Master only |
| `IC_HAS_HCI` | 1 | HCI (Host Controller Interface) compliant |
| `IC_SPEED_HDR_DDR` | 1 | HDR-DDR mode supported |
| `IC_SPEED_HDR_TS` | 1 | HDR-Ternary Symbol mode supported |
| `IC_CLK_PERIOD` | 5 (200 MHz core) | Core clock; pclk = 100 MHz |
| `IC_BUF_LVL_SEL` | 3 | Buffer level selection |
| `IC_NUM_DEVICES` | 8 | Max devices on bus |
| `IC_DEV_ADDR_TABLE_BUF_DEPTH` | 16 | Device address table depth |
| `IC_DEV_CHAR_TABLE_BUF_DEPTH` | 32 | Device characteristic table depth |
| `IC_IBI_BUF_LVL_SEL` | 3 | IBI buffer level selection |

**I3C Timing (HCNT/LCNT per speed):**

| Speed | Frequency | HCNT | LCNT |
|-------|-----------|------|------|
| Open Drain (OD) | 3.33 MHz | 0x8 | 0x34 |
| Push-Pull (PP) | 12.5 MHz | 0x8 | 0x8 |
| FM+ (I2C) | 1 MHz | 0x4C | 0x7C |
| FM (I2C) | 400 KHz | 0xB4 | 0x140 |

> **Clock switching procedure**: To change I3C clock, FW must: quiesce bus → disable controller → apply BCG → switch clock source → re-enable controller. This is required when transitioning between I3C native speeds and I2C legacy speeds.

#### GPIO Controller (HAS Section 8.21)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Total GPIO | 32 | 16 pinned out, 16 virtual |
| VGPIO | 16 | `NVU_GP[0-7]` — sensor driver handshake |
| Glitch Filtering | **DEFEATURED** | Glitch filter logic present but disabled |
| Min Pulse (no GF) | 3 RTC clocks | Minimum detectable pulse width |
| Min Pulse (with GF) | 5 RTC clocks | If glitch filter were enabled |

**Wake Pin Assignments:**

| GPIO Range | Function |
|------------|----------|
| GPIO[16-18] | UART nCTS signals |
| GPIO[19-20] | I3C SDA signals |
| GPIO[21-23] | CDPHY ownership control |
| GPIO[24-26] | USB CAM ownership control |

> **Busy-poll required**: FW must poll the GPIO busy status bit before every GPIO register read or write operation. Writing without checking busy may corrupt GPIO state.

### Reset Signals

| Reset Signal | Description |
|---|---|
| `nvu_prim_rst_b` | IOSF Primary Reset |
| `nvu_side_rst_b` | IOSF Sideband Reset |
| `nvu_pgcb_rst_b` | PGCB Reset |

> **Integration HAS v0.8**: All three reset signals are present and operate in their respective reset domains.

### NOC Fabric Topology (Source: HAS SVG — FlexNoC v5.4 Block Diagram)

The NVU internal interconnect is an **Arteris FlexNoC v5.4** fabric operating at **200/100 MHz** (func_clk / func_clk_div2). All initiator-to-target routing goes through the NOC:

#### Initiators (AXI Masters)

| Initiator | Bus Width | Description |
|-----------|-----------|-------------|
| `VPX2_CBU128` | 128-bit | VPX2 DSP code/data access via CBU (Close-coupled Bus Unit) |
| `NPX6_NPU128` | 128-bit | NPX6 NNA tensor data access |
| `ALTEK_ISP` | 128-bit | Altek CV-ISP DMA for frame data |
| `CSI2_HC` | 128-bit | CSI-2 Host Controller frame ingress |
| `UVOL_INIT128` | 128-bit | UVOL USB camera offload initiator |
| `DMA` | 128-bit | DesignWare AXI DMA (boot + runtime paging) |
| `IOSF2AXI_BR` | 128-bit | IOSF-to-AXI bridge (host MMIO access) |

#### Targets (AXI Slaves)

| Target | Bus Width | Description |
|--------|-----------|-------------|
| `SRAM_SS` (VMEMP0/1, PMEM0/1, CFG, EXTMEM, VMEM0/1) | 128-bit | SRAM subsystem — 7 slices + SMMU virtual memory + external DRAM (IMR) |
| `APB_PERIPHERALS` (via APB2APB Bridge 1:2) | 32-bit | All APB targets: SB_MSG, CRPM, MISC, DTF, IPC, SEC_REG, GPIO, ATT, HPET, WDT, I2C×3, I3C×2, SPI×2, UART×3, DMA_MISC |
| `SIO_TARG128` | 128-bit | SIO Component target for USB camera data |
| `UVOL_CFG32` | 32-bit | UVOL configuration registers |
| `DMI64` | 64-bit | NPX6 Debug Memory Interface |

#### Bridges

| Bridge | Description |
|--------|-------------|
| `ASYNC_BR` | Asynchronous bridge between 200 MHz and 100 MHz clock domains |
| `APB2APB_BR` | APB-to-APB bridge (1:2 split) connecting NOC APB port to all peripheral targets |
| `AXI_BIU_BR` | AXI BIU bridge for VPX2/NPX6 close-coupled memory interface |

> **Source**: HAS SVG `FlexNoc.vsdx` — full fabric topology with all initiator/target connections and bus widths.

### HW Reset Signal Timing (Source: HAS SVG — Reset Timing Diagram)

The NVU HW reset sequence involves precise signal timing between PMC, PGCB, and the NVU clock/power domains:

| # | Signal / Event | Description |
|---|----------------|-------------|
| 1 | `pmc_nvu_pg_wake` asserted | PMC initiates power-on wake |
| 2 | `nvu_pgcb_rst_b` deasserted | PGCB reset released |
| 3 | `nvu_pmc_pg_req_b` deasserted | NVU releases power gate request (requesting power ON) |
| 4 | `pmc_nvu_fet_en_b` asserted low | PMC enables FET (power rails come up) |
| 5 | `nvu_pmc_fet_en_ack_b` asserted low | NVU acknowledges FET enable |
| 6 | `pmc_nvu_pg_ack_b` asserted low | PMC confirms power gate exit complete |
| 7 | POK signals asserted | Power-OK indicators for VNN domain |
| 8 | `nvu_side_rst_b` deasserted | IOSF Sideband reset released |
| 9 | `nvu_pgcb_clk_req` / `nvu_pgcb_clk_ack` | PGCB clock handshake |
| 10 | `nvu_br_side_clk_req` / `nvu_br_side_clk_ack` | Bridge sideband clock handshake |
| 11 | `nvu_func_clk_req` / `nvu_func_clk_ack` | Functional clock handshake (400 MHz) |
| 12 | `nvu_prim_rst_b` deasserted | IOSF Primary reset released — NVU is now operational |
| 13 | NVU STATE → `Running` | NVU transitions from PwrGated state to Running |

> **Critical**: Reset signals are **asynchronous** in the VNN domain. Clock handshakes must complete in sequence (PGCB → SB → FUNC → PRIM) before the NVU can accept host transactions.

> **Source**: HAS SVG `f1.Reset.Timing` — full signal timing waveform.

### IOSF Primary Interface (Integration HAS Section 7)

| Parameter | Value |
|---|---|
| Spec Version | IOSF Primary v1.4.1 r0.2 |
| Role | Consumer (NVU is an IOSF Primary consumer) |
| Key Signals | MCONTROL, MCOMMAND, MDATA (master), TCONTROL, TCOMMAND, TDATA (target) |
| ISM | PRIM_ISM_FABRIC / PRIM_ISM_AGENT |
| Power OK | PRIM_POK |
| Clock Req/Ack | PRIM_CLKREQ / PRIM_CLKACK |
| Signal Count | 100+ signals (full table in Integration HAS Section 7) |

### IOSF Sideband Interface (Integration HAS Section 7)

| Parameter | Value |
|---|---|
| Spec Version | IOSF Sideband v1.4 r1.4 |
| Role | Agent (NVU is an IOSF-SB agent) |
| `MESSAGEPAYLOADWIDTH` | 8 |
| `SB_PARITY_REQUIRED` | 0 (parity not required) |
| Endpoint Name | NVU |
| Private Config Space | 64 KB accessible via IOSF-SB |

### Power Gating Domains (PGCB)

The NVU has **3 PGCB power gating domains**, each with its own FET_EN control:

| PGCB Domain | Description |
|---|---|
| `NVU_MAIN_PGCB` | Main partition power gate |
| `NVU_USB_PGCB` | USB camera interface power gate |
| `NVU_MIPI_PGCB` | MIPI camera interface power gate |

### D0i2 / IPAPG (IP Accessible Power Gate)

D0i2 is the NVU's deep idle state combining **trunk-level clock gating**, **SRAM retention**, and **IPAPG** (HAS Section 13.7.5). During D0i2 with IPAPG:

- **IPAPG is asserted** — the PG domain gets its power removed while state-retention (SR) flops hold their values
- **Timers stop** — XTAL and PGCB ART counters stop counting and get reset in IPAPG; FW must use the RTC (32 KHz) counter for accuracy across D0ix, or re-sync with PMC after every IPAPG event
- **DTF interface must be IDLE** — the IPAPG flow ensures the DTF interface is quiesced before power gate entry
- **Security registers must not lose state** — security registers must not be reset during NVU power-flows (IPAPG)
- **External repeater resets asserted** — the reset signal for repeaters and arbiter outside NVU-IP is asserted when NVU enters IPAPG state
- **PCE_SHADOW.HAE** — FW checks this register to confirm the host allows IP to enter IPAPG; if HAE == 0, fall back to D0i1
- **IPAPG_EN / TCG_EN** — FW programs CRPM `IPAPG_EN` and `TCG_EN` registers for entry; clears `IPAPG_EN` on exit
- **PMU_IPAPG_EN[0]** — on exit from IPAPG, FW polls `IPAPG_EXIT_INDICATION` to confirm successful exit

> **Note**: NVU does NOT support RTD3. Post FW loading, the NVU SW function will be in D3 and not wake capable (HAS Section 13.7.6).


## Fuses (HAS Section 19)

**Fuse receiver address base**: `16'h0650`

### Fuse Bit Map

| Bit | Fuse Name | Default | Description |
|---|---|---|---|
| 0 | `NVU_VPX_HALT_Fuse` | 0 | Keeps the core in halted state on reset |
| 1 | `NVU_HVM_MODE_Fuse` | 0 | High Volume Manufacturing mode |
| 2 | `NVU_Secure_Load_Fuse` | 1 | Enables secure firmware load |
| 3 | `NVU_Debug_Mode_Fuse` | 0 | Enables debug mode |
| 4 | `NVU_Softstrap_select_disable` | 0 | Disables soft-strap override of fuse values |
| 5 | `NVU_VSI9000NanoD_enable` | 0 | Enables VSI9000 NanoD feature |
| 6 | `NVU_SRAM_SCRUB_BY_FW` | 0 | When set (`0x1`), ROM/BUP uses FW SW writes for SRAM scrubbing instead of the HW ECC scrub method. Added per HAS Feedback [2829]. |
| 7–95 | Spare | 0 | Reserved spare fuses |

### Fuse RTL Signal Paths (`oob_fuse` Mapping)

Each fuse maps to a bit range in the `oob_fuse` bus (received from the fuse controller) and an internal `NVU_FUSE0` register:

| Fuse Name | `oob_fuse` Bits | `NVU_FUSE0` Bits |
|---|---|---|
| `NVU_VPX_HALT_Fuse` | `oob_fuse[0]` | `NVU_FUSE0[0]` |
| `NVU_HVM_MODE_Fuse` | `oob_fuse[1]` | `NVU_FUSE0[1]` |
| `NVU_Secure_Load_Fuse` | `oob_fuse[2]` | `NVU_FUSE0[2]` |
| `NVU_Debug_Mode_Fuse` | `oob_fuse[3]` | `NVU_FUSE0[3]` |
| `NVU_Softstrap_select_disable` | `oob_fuse[4]` | `NVU_FUSE0[4]` |
| `NVU_VSI9000NanoD_enable` | `oob_fuse[5]` | `NVU_FUSE0[5]` |
| `NVU_Spare_Fuse1` | `oob_fuse[7:6]` | `NVU_FUSE0[7:6]` |
| `NVU_Spare_Fuse2` | `oob_fuse[15:8]` | `NVU_FUSE0[15:8]` |
| `NVU_Spare_Fuse3` | `oob_fuse[31:16]` | `NVU_FUSE0[31:16]` |
| `NVU_Spare_Fuse4` | `oob_fuse[63:32]` | `NVU_FUSE0[63:32]` |
| `NVU_Spare_Fuse5` | `oob_fuse[95:64]` | `NVU_FUSE0[95:64]` |

### Softstrap Select Disable Encoding

The `NVU_Softstrap_select_disable` fuse (`oob_fuse[4]`) controls whether SECURE/DEBUG mode is sourced from fuses or soft-straps:

| Value | Stepping | Meaning |
|---|---|---|
| `0x1` | Fused production stepping | SECURE/DEBUG mode determined by **fuse** values (soft-strap override disabled) |
| `0x0` | Fused non-production stepping | SECURE/DEBUG mode determined by **soft-strap** values (soft-strap override enabled) |

> **Default = 1** (production): Soft-strap override is disabled. Set to 0 only on pre-production silicon to allow soft-strap-based boot mode selection.

### Boot Mode Decoding

Boot mode is determined by the combination of `NVU_HVM_MODE_Fuse`, `NVU_Debug_Mode_Fuse`, and `NVU_Secure_Load_Fuse` fuses:

| HVM_MODE | DEBUG_MODE | SECURE_LOAD | Boot Mode |
|---|---|---|---|
| 0 | 0 | 0 | Fuse Pull Error (Halt NVU) |
| 0 | 0 | 1 | SECURE Load — Post-production silicon load from CSME (Interrupt Driven) |
| 0 | 1 | 0 | DEBUG Mode — Load from Host/CSME (Polling Driven) |
| 0 | 1 | 1 | SECURE Load — Post-production silicon load from CSME (Interrupt Driven) |
| 1 | 0 | 0 | HVM Mode — Load from Host (Interrupt Driven) |
| 1 | 0 | 1 | SECURE Load — Post-production silicon load from CSME (Interrupt Driven) |
| 1 | 1 | 0 | DEBUG Mode — Load from Host/CSME (Polling Driven) |
| 1 | 1 | 1 | SECURE Load — Post-production silicon load from CSME (Interrupt Driven) |

> **Note**: Boot mode priority: SECURE_LOAD=1 always selects SECURE mode; DEBUG_MODE=1 (with SECURE_LOAD=0) selects DEBUG mode; HVM_MODE=1 (with both others=0) selects HVM mode; all zeros = Fuse Pull Error. (HAS Section 19.2)

### IP Disable

NVU can be disabled via three mechanisms:
1. **Fuse** — hardware fuse permanently disables the IP
2. **Soft-strap** — soft-strap override disables the IP (`NVU_Softstrap_select_disable`)
3. **BIOS Menu** — platform BIOS setting disables the IP
4. **Absence** — NVU is not present on the platform

When disabled, **PMC keeps NVU in the IP-Inaccessible Power Gate state** — the IP is not visible on the bus and consumes no dynamic power.


## Soft-Straps (HAS Section 19)

### Class Code / Device Identity Soft-Straps

| Soft-Strap | Bits | Description |
|---|---|---|
| `NVU_Reg_prg_intf_func1_SoftStrap` | ClassCode[7:0] | Programming Interface byte |
| `NVU_SubClass_code_func1_SoftStrap` | ClassCode[15:8] | SubClass Code byte |
| `NVU_BaseClass_code_func1_SoftStrap` | ClassCode[23:16] | Base Class Code byte |

### Functional Soft-Straps

| Soft-Strap | Width | Default | Description |
|---|---|---|---|
| `NVU_platform_sku_SoftStrap` | 2-bit | 0 | Platform SKU selection |
| `NVU_Secure_Load_softstrap` | 1-bit | 1 (Secure Load Mode) | Overrides Secure Load fuse (if allowed) |
| `NVU_Debug_Mode_softstrap` | 1-bit | 0 (Non-Debug Mode) | Overrides Debug Mode fuse (if allowed) |
| `NVU_Timeout_softstrap` | 3-bit | See boot method for details | Timeout value for NVU operations |
| `NVU_HW_AutoAck_Disable` | 1-bit | 0 (HW auto-ack enabled) | Disables HW auto-acknowledgement for ResetPrep and BootPrep |
| `NVU_SRAM_SCRUB_BY_FW` | 1-bit | 0 (HW scrub) | FW-managed SRAM scrubbing (when 1, ROM/BUP uses SW writes instead of HW scrub) |
| `NVU_HASH_BY_FW` | 1-bit | 0 (HW hash) | FW-managed hash computation (when 1, ROM/BUP uses SW algo instead of HW HASH engine) |
| `NVU_WAIT_FW_LOAD_VISION_SERVICE` | 1-bit | 1 | Wait for FW load before vision service |
| `NVU_VPX2_Debug_Cache_Rst_Disable` | 1-bit | 0 (debug cache reset enabled) | Disables VPX2 debug cache reset |
| `NVU_ROM_WAIT_D3` | 1-bit | 0 | ROM waits until NVU PCI device is in D3 before initiating D0i2 (IPAPG). Offset `0x0663`, bit[30]. |
| `NVU_SPARE_SS7` | 1-bit | 0 (no bypass) | Bypass IOSF2AXI bridge D3 functionality (0=normal D3, 1=bypass D3 in IOSF bridge). Offset `0x0662`, bit[16]. Debug/spare strap. |

### Fuse & Soft-Strap Register Address Map (from NVU IP HAS Excel)

| Offset | Width | Content |
|--------|-------|---------|
| `0x0650[0]` | 1-bit | `VPX_HALT` — Halt VPX2 DSP (Fuse) |
| `0x0650[1]` | 1-bit | `HVM_MODE` — HVM Mode (Fuse, default=1) |
| `0x0650[2]` | 1-bit | `Secure_Load` — Secure Load Enable (Fuse, default=1) |
| `0x0650[3]` | 1-bit | `Debug_Mode` — Debug Mode (Fuse) |
| `0x0650[4]` | 1-bit | `Softstrap_select_disable` — Production Mode (Fuse, default=0) |
| `0x0650[5]` | 1-bit | `VSI9000NanoD_enable` — MJPEG Decoder Enable (Fuse) |
| `0x0650[7:6]` | 2-bit | `Spare_Fuse1` — Reserved (Fuse) |
| `0x0651` | 8-bit | `Spare_Fuse2` — Reserved (Fuse) |
| `0x0652` | 16-bit | `Spare_Fuse3` — Reserved (Fuse) |
| `0x0654` | 32-bit | `Spare_Fuse4` — Reserved (Fuse) |
| `0x0658` | 32-bit | `Spare_Fuse5` — Reserved (Fuse) |
| `0x065C` | 8-bit | `Reg_prg_intf_func1` — Programming Interface ClassCode[7:0] |
| `0x065D` | 8-bit | `SubClass_func1` — SubClass ClassCode[15:8] |
| `0x065E` | 8-bit | `BaseClass_func1` — Base Class ClassCode[23:16] |
| `0x065F` | 8-bit | `SPARE_SS1` — Reserved |
| `0x0660` | 16-bit | `SPARE_SS2` — Reserved |
| `0x0662[16]` | 1-bit | `D3_bypass` / `SPARE_SS7` |
| `0x0662[18:17]` | 2-bit | `platform_sku` |
| `0x0662[19]` | 1-bit | `Secure_Load_ss` (default=1) |
| `0x0662[20]` | 1-bit | `Debug_Mode_ss` |
| `0x0662[23:21]` | 3-bit | `Timeout` (default=0; 0=2RTC, 1=8ms, 2=16ms, 3=32ms) |
| `0x0663[24]` | 1-bit | `HW_AutoAck_Disable` |
| `0x0663[25]` | 1-bit | `SPARE_SS3` — Reserved |
| `0x0663[26]` | 1-bit | `VPX2_Debug_Cache_Rst_Disable` |
| `0x0663[27]` | 1-bit | `WAIT_FW_LOAD_VISION_SERVICE` (default=1) |
| `0x0663[28]` | 1-bit | `SRAM_SCRUB_BY_FW` |
| `0x0663[29]` | 1-bit | `HASH_BY_FW` |
| `0x0663[30]` | 1-bit | `ROM_WAIT_D3` |
| `0x0663[31]` | 1-bit | `SPARE_SS4` — Reserved |
| `0x0664` | 32-bit | `SPARE_SS5` — Reserved |
| `0x0668` | 32-bit | `SPARE_SS6` — Reserved |

### Soft-Strap RTL Signal Paths (`oob_fuse` Mapping)

Each soft-strap maps to a bit range in the `oob_fuse` bus (bits 96+) and an internal `NVU_SOFT_STRAP` register:

| Soft-Strap Name | `oob_fuse` Bits | `NVU_SOFT_STRAP` Bits |
|---|---|---|
| `NVU_Reg_prg_intf_func1_SoftStrap` | `oob_fuse[103:96]` | `NVU_SOFT_STRAP0[7:0]` |
| `NVU_SubClass_code_func1_SoftStrap` | `oob_fuse[111:104]` | `NVU_SOFT_STRAP0[15:8]` |
| `NVU_BaseClass_code_func1_SoftStrap` | `oob_fuse[119:112]` | `NVU_SOFT_STRAP0[23:16]` |
| `NVU_SPARE_SS1` | `oob_fuse[127:120]` | `NVU_SOFT_STRAP0[31:24]` |
| `NVU_SPARE_SS2` | `oob_fuse[143:128]` | `NVU_SOFT_STRAP1[15:0]` |
| `NVU_D3_bypass_SoftStrap` (SPARE_SS7) | `oob_fuse[144]` | `NVU_SOFT_STRAP1[16]` |
| `NVU_platform_sku_SoftStrap` | `oob_fuse[146:145]` | `NVU_SOFT_STRAP1[18:17]` |
| `NVU_Secure_Load_softstrap` | `oob_fuse[147]` | `NVU_SOFT_STRAP1[19]` |
| `NVU_Debug_Mode_softstrap` | `oob_fuse[148]` | `NVU_SOFT_STRAP1[20]` |
| `NVU_Timeout_softstrap` | `oob_fuse[151:149]` | `NVU_SOFT_STRAP1[23:21]` |
| `NVU_HW_AutoAck_Disable` | `oob_fuse[152]` | `NVU_SOFT_STRAP1[24]` |
| `NVU_SPARE_SS3` | `oob_fuse[153]` | `NVU_SOFT_STRAP1[25]` |
| `NVU_VPX2_Debug_Cache_Rst_Disable` | `oob_fuse[154]` | `NVU_SOFT_STRAP1[26]` |
| `NVU_WAIT_FW_LOAD_VISION_SERVICE` | `oob_fuse[155]` | `NVU_SOFT_STRAP1[27]` |
| `NVU_SRAM_SCRUB_BY_FW` | `oob_fuse[156]` | `NVU_SOFT_STRAP1[28]` |
| `NVU_HASH_BY_FW` | `oob_fuse[157]` | `NVU_SOFT_STRAP1[29]` |
| `NVU_ROM_WAIT_D3` | `oob_fuse[158]` | `NVU_SOFT_STRAP1[30]` |
| `NVU_SPARE_SS4` | `oob_fuse[159]` | `NVU_SOFT_STRAP1[31]` |
| `NVU_SPARE_SS5` | `oob_fuse[191:160]` | `NVU_SOFT_STRAP2[31:0]` |
| `NVU_SPARE_SS6` | `oob_fuse[223:192]` | `NVU_SOFT_STRAP3[31:0]` |

### Timeout Strap Value Encoding

The `NVU_Timeout_softstrap` (3-bit, `oob_fuse[151:149]`) controls the PMC-to-NVU timeout duration:

| Value | Timeout | Notes |
|---|---|---|
| `0x0` | 2 RTC clocks | Test mode — **reserved, do not use in production** |
| `0x1` | 8 ms | |
| `0x2` | 16 ms | |
| `0x3` | 32 ms | **Default** |
| `0x4`–`0x7` | Reserved | Do not program |

### D3 Bypass Strap

The `NVU_D3_bypass_SoftStrap` (1-bit, `oob_fuse[144]`, also known as `NVU_SPARE_SS7`) controls IOSF2AXI bridge D3 behavior:

| Value | Behavior |
|---|---|
| `0` | Normal D3 operation — IOSF2AXI bridge enters D3 when commanded (**default**) |
| `1` | Bypass D3 functionality in the IOSF2AXI bridge — debug/survivability use only |

### Hardware Straps (from IP Configuration)

| Strap | Width | Required | Description |
|---|---|---|---|
| `nvu_br_strap_deviceid` | 16 | Required | IOSF2AXI BR DeviceID: Tie to NVU DEVICEID |
| `nvu_br_devfuncnum` | 8 | Required | IOSF2AXI BR NVU Device Function Number: Device[7:3], Function[2:0] (Bus assigned separately via `nvu_br_strap_busno_rs`) |
| `nvu_br_strap_mulfndev` | 1 | Required | IOSF2AXI BR Multi Function Device: Refer SOC PSF HAS |
| `nvu_br_strap_destid_xhci` | 15 | Required | IOSF2AXI BR XHCI_CAM Destination ID: Tie to DESTID of XHCI_CAM |
| `nvu_br_strap_destid_ipu` | 15 | Required | IOSF2AXI BR IPU Destination ID: Tie to IPU DESTID |
| `nvu_br_strap_fp_sai` | 8 | Required | IOSF2AXI BR Fuse Puller Request SAI: Tie to NVU_SAI |
| `nvu_br_strap_untrusted_sai` | 8 | Required | IOSF2AXI BR Untrusted SAI: Tie Platform Untrusted SAI |

#### Additional Hardware Straps (Integration HAS v0.8, Section 4)

| Strap | Width | Description |
|---|---|---|
| `nvu_br_strap_cpl_mdestid` | 52 | IOSF2AXI BR Completion Dest ID per RS: Refer SOC PSF HAS |
| `nvu_br_strap_destid_host` | 15 | Host destination ID |
| `nvu_br_strap_intr_dst_portid` | 48 | Interrupt destination port ID |
| `nvu_br_strap_pm_msg_sai` | 8 | Power management message SAI |
| `nvu_br_strap_port` | 4 | IOSF2AXI bridge port number |
| `nvu_br_strap_port_group` | 1 | Port group assignment |
| `nvu_br_strap_psf` | 4 | PSF destination ID |
| `nvu_br_strap_busno_rs` | 24 | Bus number root space |
| `nvu_br_strap_fp_sai_cmpl` | 64 | IOSF2AXI BR Fuse Puller Completion SAI: Completion SAI from FP |
| `nvu_br_strap_fp_destid` | 128 | Fuse puller destination ID |
| `nvu_br_strap_fp_ready_portid` | 16 | Fuse puller ready port ID |
| `nvu_br_strap_bridge_portid` | 16 | Bridge port ID |
| `nvu_br_strap_hh_sai_art` | 8 | Hammock Harbor ART SAI |
| `nvu_br_strap_hh_src_id` | 16 | Hammock Harbor source ID |
| `nvu_br_strap_ltr_destid` | 16 | LTR message destination ID |
| `nvu_br_strap_pcierr_destid` | 48 | PCIe error message destination ID |
| `nvu_br_strap_sb_srcdestid_16bit` | 1 | Enable 16-bit sideband source/destination ID |
| `nvu_cse_portid_strap` | 16 | CSE port ID |
| `nvu_cse_sai_strap` | 8 | CSE SAI |
| `nvu_ese_portid_strap` | 16 | ESE port ID |
| `nvu_ese_sai_strap` | 8 | ESE SAI |
| `nvu_xhci_sai_strap` | 8 | XHCI SAI |
| `nvu_ipu_sai_strap` | 8 | IPU SAI |
| `nvu_pgcb_clkgate_disabled_strap` | 1 | Disable PGCB clock gating (debug) |
| `nvu_ip_trusted_sai_strap` | 8 | IP trusted SAI |
| `nvu_dfx_red2_sai_strap` | 8 | DFx RED2 SAI |
| `nvu_br_strap_pme_destid` | 8 | PME destination ID |
| `nvu_br_strap_pme_support` | 5 | PME support |
| `nvu_iosf_prim_prim_prim_tdest_id` | 15 | IOSF primary target destination ID |
| `nvu_dtf_channel_id` | 8 | DTF Channel ID: Refer SOC Debug HAS |
| `nvu_dtf_master_id` | 8 | DTF Master ID: Refer SOC Debug HAS |
| `nvu_dtf_ts_bit_shift_val` | 2 | DTF timestamp bit shift value |
| `nvu_gpio_oe_actlow` | 1 | GPIO output enable active-low polarity |
| `nvu_i2c_crtsrcen_actlow` | 1 | I2C CRT source enable active-low polarity |
| `nvu_i2c_dataclk_oe_actlow` | 1 | I2C data/clock output enable active-low polarity |
| `nvu_i3c_dataclk_oe_actlow` | 1 | I3C data/clock output enable active-low polarity |

### SRAM Fabric Straps

| Strap | Value | Description |
|---|---|---|
| `strap_error_base_addr` | `0x80000000` | SRAM error base address |
| `strap_extmem_base_addr` | `0xA0000000` | External memory base address |
| `strap_pmem_base_addr` | `0x68000000` | Persistent memory base address |


## BDF / PCI Configuration

The NVU is a **PCI RCiEP** (Root Complex Integrated Endpoint) on the IOSF bus.

### PCI Function Map

| Function | BAR Size | Description |
|---|---|---|
| FN0 | 64KB | NVU Host SW Driver — primary host interface (HOST_IPC, PEER_IPC, SEC_REG via ATT) |
| FN1 | — | Camera/VOD data path (BAR size and remap address not specified in HAS source facts) |

### BAR and Address Mapping

- FN0 exposes a **64 KB BAR** remapped to `0x8000_0000`
- The NVU has a **64 KB private config space** accessible via IOSF-SB
- IOSF-SB endpoint name: **NVU**

### Address Translation Table (ATT)

The ATT contains **8 entries**. Example firmware-programmed mappings (HW does not provide any default mapping):

| Entry | Region | Base Address |
|---|---|---|
| 0 | HOST_IPC | `0x80000000` |
| 1 | PEER_IPC | `0x80010000` |
| 2 | SEC_REG | `0x80018000` |
| 3 | SPARE (Valid=0) | — |
| 4 | SPARE (Valid=0) | — |
| 5 | SPARE (Valid=0) | — |
| 6 | SPARE (Valid=0) | — |
| 7 | SPARE (Valid=0) | — |

### Device Identification

| Parameter | Value |
|---|---|
| Device ID strap | `nvu_br_strap_deviceid` (16-bit, actual value not specified in HAS) |
| BDF strap | `nvu_br_devfuncnum` — Device[7:3], Function[2:0] (Bus via `nvu_br_strap_busno_rs`) |
| IOSF-SB endpoint | NVU |


## PMC Dashboard

| Parameter | Value |
|---|---|
| Reset Group | Host |
| HVM Reset Group | HVM_Host |
| Static Disable | F (Fuse), S (Soft-strap), B (BIOS Menu) |
| SETID | Yes |
| Chassis Version | 2.2 |
| IOSF-SB Endpoint Name | NVU |
| Hammock Harbor | Type-D |
| SaveRestore | Yes |
| PG Default | OFF |
| S0ix Miniset | No |
| Wake Signals | main, usb, mipi |


## Electrical Specifications (HAS Section 20)

### Power Supply

| Rail | Voltage |
|---|---|
| VNN | 0.75 V (nominal) |
| VSS | 0.00 V (ground) |

### AC / DC Characteristics

- **AC Characteristics**: N/A for this IP (per HAS Section 20)
- **DC Characteristics**: N/A for this IP (per HAS Section 20)

### Power Targets

| Use Case | Camera Interface | Power Target | Frame Rate |
|---|---|---|---|
| User Presence / Face Detection | MIPI | 5 mW | 3 fps |
| User Presence / Face Detection | USB | 8 mW | 3 fps |

### Area Target

- < 3.5 mm² for 3.5 MB SRAM configuration


## Security Architecture (EAIG Review)

> Source: NVU_IP_HAS_excel.xlsx → EAIG sheet (177 rows, 20 categories). Categories 1–2 are administrative checklists; categories 3–20 contain security architecture data documented below.

### Security Objectives (EAIG Cat 3)

- **Privacy**: Camera images and face templates stored in NVU SRAM must remain inaccessible to host applications
- **Firmware Integrity**: NVU firmware must be authenticated before execution; unauthorized code must not run on the VPX or NPX

### HW/FW Security Requirements (EAIG Cat 4)

| # | Requirement | Description |
|---|-------------|-------------|
| 1 | SRAM Isolation | NVU IP has its own local SRAM, dedicated IMR, and local peripherals — isolated from other IP via SAI-based access control |
| 2 | SAI Protection | Source Agent Identifier (SAI) enforced on all NVU initiator/target transactions |
| 3 | I/O Isolation | NVU peripheral I/Os (IPC, I2C, GPIO, ISP, CSI) only accessible by VPX — isolated from host |
| 4 | NPX Memory Isolation | NPX only accessible by VPX; HW supports NPX memory isolation from host read-back |
| 5 | One-Direction DMA (IMR→SRAM) | One-way DMA from host to NVU SRAM only — prevents SRAM data exfiltration back to host |
| 6 | SRAM Scrub | SRAM contents scrubbed to prevent sensitive data (e.g., Face ID vectors) remanence |
| 7 | Reset After Unlock | Debug unlock triggers full NVU reset — no stale data survives unlock transition |
| 8 | USB Camera Isolation | USB camera data path isolated from host when routed through NVU USB-IF subsystem |

### Assets and Secrets (EAIG Cat 5)

- **Camera images**: Raw/processed frames in SRAM — must remain secret from host applications
- **Face templates**: Biometric enrollment data in SRAM — highest sensitivity asset
- **Third-party ML models**: Downloaded to IMR, then paged to SRAM — code is **unencrypted on HDD** (not a secret, but integrity-protected)
- **Storage**: All sensitive assets reside in NVU SRAM (volatile) or IMR (integrity-verified); no persistent secret storage

### Integrity Requirements (EAIG Cat 6)

- **Host IPC disabled after FW download**: Once FW is loaded and authenticated, the Host IPC path is disabled — host cannot inject code post-boot
- **ESE authentication**: ESE performs SVN (Security Version Number) check + signature verification before VPX executes FW
- **SHA hash engine**: On-die SHA accelerator for boot-time and runtime integrity checks
- **PQC/LMS support**: Post-Quantum Cryptography (Leighton-Micali Signature) for future-proof FW authentication
- **Debug key on unlock**: Debug unlock requires authenticated key — unlocked state allows register/SRAM access but triggers full reset first (Cat 4 #7)
- **SPI NOR boot chain**: Boot ROM uses SHA engine to ensure BUP (Bring-Up) in SRAM is identical to BUP in IMR; ESE performs SVN + signature verification
- **IMR hash check**: IMR contents hash-verified at boot time and during runtime FW paging operations

### Availability (EAIG Cat 7)

- **Attack surfaces**: SW attack (malicious host driver), BIOS/ME FW attack (malicious BIOS/ME FW config), HW attack (physical)
- **BIOS disable**: BIOS can disable NVU by hiding the PCI device (function-level disable via fuses and straps) — this is by-design, not a vulnerability

### Fuses and Straps (EAIG Cat 8)

- **Functional fuses**: NVU has functional feature and SRAM DFx fuses only (see Fuse Map section above)
- **SRAM DFx fuses**: DFx-specific fuses for SRAM BIST/debug — fuse-gated, not accessible in production
- **No special fuse protections**: Fuses follow standard Intel fuse security model (OTP, blown during manufacturing)

### Authorized Users (EAIG Cat 9)

| Entity | Role | SAI |
|--------|------|-----|
| Host CPU | Target + Initiator (IPC, config) | `DEV_UNTRUSTED_SAI` (for MSI) |
| ESE (Embedded Security Engine) | FW authentication, SVN check | N/A |
| ISH (Integrated Sensor Hub) | Peer IPC target + initiator | Sideband peer path |
| IPU (Image Processing Unit) | MIPI PHY sharing, frame streaming | P2P streaming path |
| XHCI (USB Host Controller) | USB camera offload data path | P2P data path |

- **Dual SAI model**: MSI transactions use `DEV_UNTRUSTED_SAI`; all other NVU outbound traffic (from SIODMA, SMMU DMA, BOOTDMA, and peer outbound) uses `NVU_SAI`

### Important Locks (EAIG Cat 10)

- NVU has lock registers defined: LAR (Lock Access Register) at address 0xFB0 (RAZ – not implemented) and LSR (Lock Status Register) at address 0xFB4 (RAZ – not implemented). Standard PCI config space lock bits also apply.

### Feature Disable Impact (EAIG Cat 11)

- Disabling NVU (via BIOS strap or PCI function hide) has **no impact** on other platform IPs — NVU is a standalone accelerator with no critical dependencies

### Peer/Bus DMA Architecture (EAIG Cat 12)

| DMA Type | Description | SAI |
|----------|-------------|-----|
| SIODMA | Streaming I/O DMA — camera frame data (MIPI/USB) | `NVU_SAI` |
| SMMU DMA | SMMU-managed DMA — FW paging between SRAM and IMR (DRAM) | `NVU_SAI` |
| BOOTDMA | Boot DMA — initial FW load from host memory to SRAM | `NVU_SAI` |

- **FW programs all DMA**: Host does not directly program DMA descriptors — all DMA configuration done by NVU firmware
- **SAI tagging**: All three DMA types (SIODMA, SMMU DMA, BOOTDMA) use `NVU_SAI` for IOSF Primary traffic
- **P2P paths**: NVU↔XHCI (USB camera data), NVU↔IPU (MIPI frame streaming), NVU↔ESE (FW authentication sideband)

### Traffic Class / Virtual Channels (EAIG Cat 13)

> See also: [IOSF Traffic Class / Virtual Channels](#iosf-traffic-class--virtual-channels-from-eaig-security-review) section above for detailed VC/TC mapping.

- **2 Virtual Channels**: VC0 = TC0 (host traffic), VCpeer = TCpeer (peer-to-peer traffic)

### IP Identity (EAIG Cat 14)

- **SAI immutable**: Source Agent Identifier is hardware-assigned, not software-configurable
- **PCI Device ID lockable**: BIOS can lock PCI DID via strap (`nvu_br_strap_deviceid`) — prevents runtime modification
- **Requester ID hardcoded**: PCI Requester ID (BDF) is hardcoded from straps — not modifiable by software

### SAI Policy Details (EAIG Cat 15)

| Path | Outbound SAI | Notes |
|------|-------------|-------|
| Primary (MSI) | `DEV_UNTRUSTED_SAI` | Host-bound MSI interrupts |
| Primary (DMA/peer) | `NVU_SAI` | From SIODMA, SMMU DMA, and BOOTDMA; NVU_SAI for all peer outbound traffic |
| Sideband (all) | `NVU_SAI` | All sideband messages |

- **Strap-configurable outbound SAI**: Outbound SAI can be configured via straps (but defaults are hardcoded per HAS)
- **Inbound access control**: Combined RAC/WAC (Read/Write Access Control) in a single policy register per target
- **Hardcoded default policy**: Access control parameters are hardcoded in RTL — not software-modifiable
- **No completion SAI check**: NVU does not verify SAI on completion packets (standard Intel behavior)

### Root Space / IMR Architecture (EAIG Cat 16)

| Root Space | Purpose | SAI |
|------------|---------|-----|
| RS0 | Host access (IPC, config) | `NVU_SAI` |
| RS2 | ESE access (FW authentication) | ESE SAI |
| RS3 | IMR (DRAM) — FW code/data, model weights | `NVU_SAI` |

- **FW configures RS dynamically**: Root space mapping configured by NVU firmware during boot
- **Different SAI per RS**: Each root space has independent SAI policy
- **IP generates RS**: NVU hardware generates the root space tag on outbound transactions
- **Per-RS access control**: Inbound transactions filtered by root space + SAI combination
- **RS security lockdown**: NVU BUP configures RS3_WR_DISABLE (one-way DMA from NVU to host only) and IPC_DISABLE to cut off host communication after boot
- **IMR for FW authentication**: IMR region used as staging area for FW download; ESE authenticates before VPX2 executes
- **SMMU IMR-to-SRAM mapping**: SMMU logic supports mapping/translation of virtual address space (IMR) to physical address space (SRAM)

### Cycle Support (EAIG Cat 17)

- **No LT (Lock Transaction)** support
- **No RAVDM** support
- **No MCTP** (Management Component Transport Protocol) support
- **No cycle injection** capability

### Microprocessor Security (EAIG Cat 18)

- FW authentication follows NVU FAS (Firmware Architecture Specification) — secure boot ROM validates initial code, ESE performs SVN + signature verification

### VTd / Access Control (EAIG Cat 19)

- **SAI enforced on CFG + MMIO**: All PCI configuration and MMIO transactions carry SAI
- **Dual policy registers for P2P**: Separate access control policies for host-initiated vs peer-initiated P2P transactions
- **No OCP P2P**: No Open Compute Project peer-to-peer protocol support
- **No Primary→Sideband propagation**: Primary bus transactions do not propagate to sideband
- **No Sideband→Primary propagation**: Sideband transactions do not propagate to primary bus

### DFx Security (EAIG Cat 20)

- **TAP access via sTAP**: Debug TAP chain accessed through sTAP (secure TAP) infrastructure
- **DFx security plugin**: Standard Intel DFx security plugin — unmodified plugin code
- **Policy matrix exposed**: `policy_matrix` register exposed for debug policy configuration
- **Lowest power well**: DFx logic in lowest (always-on) power well — accessible in all power states
- **All info exposable via SB/TAP**: In unlocked state, all NVU internal state observable via sideband or TAP
- **SAI unchanged on unlock**: Debug unlock does not change SAI values — access control policies remain in effect (but debug registers become accessible)


## Platform References

| Platform | Reference Document | Version |
|---|---|---|
| TTL | TTL AON Domain Requirements | |
| HML | HML AON Domain Requirements | |

### Platform Notes

- NVU is **non-functional in platform Sx states** — all state is lost on Sx entry
- NVU targets always-on operation in S0 only (AON = Always-On-Nano)
- Platform must ensure power rail sequencing per VNN requirements before NVU de-reset
- BIOS is responsible for strap/fuse programming and PMC IP enable/disable policy


## BIOS Platform Camera Configuration (E2E HAS v0.1)

> Source: VISION SS End-To-End HAS v0.1. BIOS must provide camera configuration to the NVU FW via ACPI DSM.

BIOS is responsible for configuring the following platform camera parameters, which are passed to NVU FW at boot via DSM (Device Specific Method) ACPI call:

| Parameter | Values | Description |
|-----------|--------|-------------|
| Camera Type | MIPI / USB Legacy / USB RAW | Type of camera connected to the platform |
| PHY Type | C-PHY / D-PHY | MIPI PHY type (for MIPI cameras only) |
| Max Resolution | e.g., VGA, 1080p, 4K | Maximum supported camera resolution |
| Sensor Type | Platform-specific | Sensor model/capability identifier |
| NVU Enabled | Yes / No | Whether NVU vision sensing is enabled on this platform |
| GPIO Pins | Platform-specific | GPIO pin assignments for camera control |
| I2C Pins | Platform-specific | I2C pin assignments for sensor communication |
| Shared Camera | Designation flag | Which camera is shared between IPU and NVU |
| **USB Hosting Mode** | **IPU Hosted / SW Hosted** | **USB RAW camera hosting model (E2E HAS v0.1)** |

#### USB-Specific BIOS Configuration (E2E HAS v0.1)

For USB RAW cameras, BIOS provides additional configuration:

| Parameter | Description |
|-----------|-------------|
| USB RAW (CCPAL-U) camera enabled | Whether USB RAW camera is present on the platform |
| UVC Legacy Camera | Whether a UVC legacy camera is present |
| IPU Hosted vs SW Hosted | Whether USB RAW camera datapath is managed by IPU FW or by host SW |
| NVU Enabled/Disabled | Whether NVU sensing is active for this camera |
| **Device Descriptor Table** | BIOS pre-populates USB device descriptor information to **speed up USB camera enumeration** at boot. Without this, XHCI_CAM must perform full USB enumeration from scratch. |

> **Open Review (E2E HAS v0.1)**: There is an unresolved debate about whether GPIO allocation should use **GRP4** or **GROUPHOST** for NVU camera GPIO pin assignments. This affects platform strap/BIOS configuration. Check the latest E2E HAS revision for resolution.


## Performance KPIs and Targets (FAS §15, L18379-18715)

The NVU FAS defines quantitative performance and accuracy targets for the AON vision platform. These KPIs are critical for validation pass/fail criteria.

### Power Targets

| Use Case | Target | Notes |
|----------|--------|-------|
| Face Detect — MIPI camera @ 3 FPS | SoC power adder to MCS (refer to platform KPI) | MIPI PHY shared with IPU |
| Face Detect — USB camera @ 3 FPS | SoC power adder to MCS (refer to platform KPI) | Includes USB subsystem overhead |

### Boot Time

| Metric | Target | Notes |
|--------|--------|-------|
| ROM execution → Main FW load complete | **< 5 seconds** | NVU is **NOT boot-critical** — does not block platform POST |

### FPS Jitter

| Metric | Target | Notes |
|--------|--------|-------|
| Frame-to-frame interval jitter | **< 15%** | At 3 FPS (333 ms nominal), acceptable range = 283–383 ms |

### NN Algorithm Memory Footprint

| Metric | Target | Notes |
|--------|--------|-------|
| Per-NN-algorithm (model + runtime) | **≤ 1.5 MB** | Includes model weights, activations, NNRT workspace; aligned to 0x40 (64B dcache line) |

### Face Detection KPIs (FAS §15, L18450-18550)

| KPI | Target | Condition |
|-----|--------|-----------|
| Minimum face size | **24 × 24 px** | ~2 m range on 320×320 frame |
| Maximum faces | **3** | Simultaneous detection |
| Yaw range | **±90°** | |
| Pitch range | **±20°** | |
| Roll range | **±20°** | |
| True Positive Rate (TPR) | **> 95%** | |
| False Positive Rate (FPR) | **< 1%** | |
| Orientation MAE | **< 5°** | Mean Absolute Error for head pose |
| Landmark NME | **< 5%** | Normalized Mean Error for 12-landmark |

### Face ID KPIs (FAS §15, L18550-18600)

| KPI | Target | Condition |
|-----|--------|-----------|
| Minimum face size | **64 × 64 px** | ~75 cm range (Windows Hello distance) |
| Maximum faces | **3** | Simultaneous recognition |
| Yaw range | **±20°** | |
| FAR @ 95% TAR | **< 5%** | False Accept Rate at 95% True Accept Rate |

### Body Posture KPIs (FAS §15, L18600-18650)

| KPI | Target | Condition |
|-----|--------|-----------|
| Minimum face size | **60 × 60 px** | Face used as proxy for body detection |
| Maximum persons | **1** | Single-user posture assessment |
| TPR | **> 95%** | Ergo vs Non-ergo classification |
| FPR | **< 5%** | |

### Hand Pose KPIs (FAS §15, L18650-18715)

| KPI | Target | Condition |
|-----|--------|-----------|
| Range | **0.3–1.2 m** | Distance from camera |
| Maximum hands | **1** | Single-hand gesture recognition |
| TPR | **> 95%** | HaGRID dataset benchmark |
| FPR | **< 5%** | HaGRID dataset benchmark |

> **Validation Note**: These KPIs define the **pass/fail thresholds** for NVU functional validation tests. Test scenarios should verify these targets under reference conditions (controlled lighting, standard test faces/hands, calibrated camera).


## Validation Scenarios

### Platform Bring-Up Checklist

| # | Check | Method | Expected |
|---|---|---|---|
| 1 | NVU PCI enumeration | `lspci` or PythonSV PCI scan | NVU appears as RCiEP with correct Device ID |
| 2 | BAR assignment | Read PCI BAR0 | 64 KB BAR mapped to `0x8000_0000` |
| 3 | IOSF-SB reachability | PythonSV IOSF-SB read to NVU endpoint | Valid response (no UR) |
| 4 | Fuse values | Read fuse receiver at base `0x0650` | Match expected fuse bitmap |
| 5 | Soft-strap values | Read soft-strap registers | Match platform strap file |
| 6 | Reset recovery | Trigger soft reset via `ESE2NVU_IPC.RESET_BIT` | NVU re-enumerates, PME asserted |
| 7 | IP disable (BIOS) | Disable NVU in BIOS menu | NVU not visible on PCI bus |
| 8 | IP disable (fuse) | Set IP disable fuse | PMC keeps NVU in IP-Inaccessible PG |
| 9 | PGCB domains | Check FET_EN for MAIN/USB/MIPI PGCB | All three domains independently controllable |
| 10 | Cold boot flow | G3 → S0 with lid open | NVU initializes in Host group reset domain |
| 11 | Warm reset flow | S0 → S3 → S0 | NVU re-initializes, FW reloads models |
| 12 | Watchdog reset | Allow watchdog to expire | Exception reset, PME assertion |

### PythonSV Quick-Reference

```python
# === PCI Enumeration ===
# Check NVU appears in PCI device list
# Device ID is set by nvu_br_strap_deviceid (16-bit strap)
# BDF is set by nvu_br_devfuncnum strap
#
# === BAR Read ===
# NVU FN0 BAR0 should map to 0x8000_0000 (64 KB)
#
# === Fuse Read ===
# Fuse receiver base: 0x0650
#   Bit 0: NVU_VPX_HALT_Fuse
#   Bit 1: NVU_HVM_MODE_Fuse
#   Bit 2: NVU_Secure_Load_Fuse (default=1)
#   Bit 3: NVU_Debug_Mode_Fuse
#   Bit 4: NVU_Softstrap_select_disable (default=1)
#   Bit 5: NVU_VSI9000NanoD_enable
#   Bits 6-95: Spare
#
# === IOSF-SB Access ===
# NVU endpoint name: "NVU"
# Private config space: 64 KB via IOSF-SB
#
# === Address Translation Table (ATT) ===
# Entry 0: HOST_IPC  -> 0x80000000
# Entry 1: PEER_IPC  -> 0x80010000
# Entry 2: SEC_REG   -> 0x80018000
#
# === SRAM Fabric Straps ===
# strap_error_base_addr  = 0x80000000
# strap_extmem_base_addr = 0xA0000000
# strap_pmem_base_addr   = 0x68000000
#
# === Reset Signals ===
# nvu_prim_rst_b   - IOSF Primary Reset (Host register reset)
# nvu_side_rst_b   - IOSF Sideband Reset
# nvu_pgcb_rst_b   - PGCB Reset (mapped to vnn_host_powergood_rst_b)
#
# === Soft Reset Trigger ===
# ESE2NVU_IPC.RESET_BIT - FW-initiated exception reset
# Watchdog expiry        - automatic exception reset
# ECC double-bit error   - automatic exception reset
#
# === PGCB Power Gating Domains ===
# NVU_MAIN_PGCB - Main partition (FET_EN)
# NVU_USB_PGCB  - USB camera interface (FET_EN)
# NVU_MIPI_PGCB - MIPI camera interface (FET_EN)
#
# === PMC Dashboard ===
# Reset Group: Host
# Static Disable: F,S,B
# Chassis Version: 2.2
# IOSF-SB endpoint: NVU
```


## See Also

- [registers/SKILL.md](../registers/SKILL.md) — BAR layout, PCI config space
- [power/SKILL.md](../power/SKILL.md) — PMC addresses, PGCB domains
- [driver/SKILL.md](../driver/SKILL.md) — PCI enumeration, driver binding
- [firmware/SKILL.md](../firmware/SKILL.md) — Strap configuration, fuse definitions
- [bios/SKILL.md](../bios/SKILL.md) — BIOS enable/disable flow (DEVEN, CAPID, static PG), fuse check (PWRMBASE+STPG_FUSE_SS_DIS_RD_2), IRQ/MSI config, GPIO/VGPIO pin mux
- [debug/SKILL.md](../debug/SKILL.md) — Platform-level debug, IOSF trace
- **NVU FAS v1.0** (Firmware Architecture Specification) — §15 KPIs, §16 FDK

## Related Sub-Skills

- [fv-nvu/power](../power/SKILL.md) — Power states, clock/power gating, CRPM, PMC integration
- [fv-nvu/bios](../bios/SKILL.md) — BIOS/FW requirements, power management BIOS flows
- [fv-nvu/inference](../inference/SKILL.md) — NN model execution, memory budget (related to KPI targets)
- [fv-nvu/camera](../camera/SKILL.md) — Camera/sensor interface, MIPI CSI-2, USB camera, ISP


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:52 | Facts added: 1206


### Additional HAS Details (3 facts)

#### Hammock Harbor (HH) Peripheral

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral)

- **Peripheral Name:** Hammock Harbor
- **Usage:** Cross-platform time synchronization engine enabling the use of a universal timestamp across all platform IPs that support the Hammock Harbor protocol.

#### Hammock Harbor Protocol Overview

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.9 Hammock Harbor)

- Hammock Harbor (HH) is a protocol intended to distribute **time** accurately across all HH-components within a platform.
- All platform IPs that implement the HH protocol share a synchronized, universal timestamp.

#### Cross-Feature Dependencies

(7 Functional Description > 7.3 Cross-Feature Dependencies)

- The BR exposes a **4 MB** region. *(Note: Additional details for this dependency are pending full HAS specification data.)*


### Boot and Reset Sequences (38 facts)

#### Boot and Reset Sequences

---

#### Reset Interface Overview (4.3.3 Resets)

The NVU exposes a single primary power-domain reset interface conforming to the Chassis 2.0 PGCB specification.

| Name | Unique Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|---|
| PGCB_RST_B | `nvu_pgcb_rst_b` | input | 1 | required | Reset signal for PGCB interface; expected to be powergood signal |

**PGCB Reset Interface Properties:**

| Property | Value |
|---|---|
| Instantiated Interface Name | NVU_PGCB_RST |
| Interface Version | v2.0 r1.2 |
| Interface Type | power |
| Reset Domain | Not Defined |
| Sync/Async | async |
| Clock Name | `nvu_pgcb_clk` |
| Sample/Drive Edge | rise_edge |
| Comment | Chassis 2.0 PGCB interface to an IP |

---

#### Reset Domains by Interface (4.3 Interfaces)

The following table summarizes the reset domain assignments across all NVU interfaces:

| Interface | Reset Domain |
|---|---|
| Clocks (4.3.2) | Not Defined |
| PGCB Reset (4.3.3) | Not Defined |
| Resource Management (4.3.5) | Not Defined |
| VISA Debug (4.3.6.1) | Not Defined |
| DTF Debug (4.3.6.2) | `nvu_prim_rst_b` |
| DTF_MISC Debug (4.3.6.2) | Not Defined |
| MAIN STAP / JTAG (4.3.6.3) | TRST_B |
| Hammock Harbor Time-Sync (4.3.8) | Not Defined |
| SPI IO (4.3.12.4) | Not Defined |
| Scan DFT (4.3.13.1) | FDFX_POWERGOOD |

---

#### JTAG Reset — MAIN STAP TRSTn (4.3.6.3)

| Signal Name | Instantiated Name | Type | Direction | Width | Required | Description |
|---|---|---|---|---|---|---|
| TRST_B | `nvu_main_stap_trst_n` | bit | input | 1 | required | Reset for primary TAP interface on SoC physical pins |

- The MAIN STAP interface is instantiated as **MAIN STAP::Reset Consumer**.
- The reset domain for all MAIN STAP signals is **TRST_B**.

---

#### Time-Sync Interface Reset (4.3.8)

| Signal Name | Direction | Width | Required | Reset Domain | Sync/Async | Clock Name | Description |
|---|---|---|---|---|---|---|---|
| `nvu_hh_sync_req` | input | 1 | required | `nvu_prim_rst_b` | sync | `nvu_xtal_clk` | Hammock Harbor Sync Request |

---

#### SPI Interface Reset (4.3.12.4)

| Signal Name | Direction | Width | Required | Reset Domain | Sync/Async | Clock Name | Drive Edge | Description |
|---|---|---|---|---|---|---|---|---|
| `nvu_spi_rxd` | input | NUM_SPI | required | `nvu_prim_rst_b` | sync | `nvu_spi_sclk_out` | rise_edge | SPI RxData |
| `nvu_spi_sclk_out` | output | NUM_SPI | required | — | — | — | — | SPI Clock Output |

---

#### DFT Scan Reset Parameters (4.3.13.1)

The Scan interface resets under the **FDFX_POWERGOOD** domain. Key bypass reset parameters are fixed and not SoC-modifiable:

| Parameter Name | Type | Default Value | SoC Modifiable | Description |
|---|---|---|---|---|
| NUM_BYPRST_B | uint32 | 1 | no | Number of Bypass Reset Bar |
| NUM_BYPLATRST_B | uint32 | 1 | no | Number of Bypass Latch Reset Bar |

---

#### D0I3 Power Gating Configuration at Reset (BIOS Programming Recipe)

The `D0I3_MAX_POW_LAT_PG_CONFIG` register (CFG space, offset `0xA0`) controls power latency behaviour relevant to reset/power-gate sequences.

| Reg Name | Offset | Reg Size | Field Name | Bits | Attribute | Reset Value |
|---|---|---|---|---|---|---|
| D0I3_MAX_POW_LAT_PG_CONFIG | 0xA0 | 32 | POW_LAT_VALUE | [9:0] | RW/O | 0x000 |
| D0I3_MAX_POW_LAT_PG_CONFIG | 0xA0 | 32 | POW_LAT_SCALE | [12:10] | RW/O | 0x2 |

---

#### HECI Bus Reset Message (7.2.3.16.1 HECI Transport Protocol)

A dedicated HECI bus message is defined for issuing reset requests over the HECI transport layer:

| Message Name | Command Byte | Payload Fields |
|---|---|---|
| HECI_BUS_MSG_RESET_REQ | `0x09` | `uint8_t command; uint8_t fw_addr; uint8_t host_addr; uint8_t reserved1;` |
| HECI_BUS_MSG_RESET_RESP | `0x89` | *(response to the above request)* |

---

#### BSP Statistics Reset (7.2.6.2 Profiling)

| Command Name | Description |
|---|---|
| `SMHI_RESET_BSP_STAT` | Reset BSP statistics |

---

#### Crash Dump Persistence Across Resets (7.2.7 Crash Dump)

- Crash dumps stored in **AONRF** (Always-On Retention Flip-flops) **persist through NVU resets**.
- This ensures post-reset diagnostic data is preserved for recovery and analysis.


### Camera Interface (88 facts)

#### Camera Interface

### Overview (§2 Introduction)

- The Neural Vision Sensing Unit (NVU) provides AON visual sensing functionality associated with MIPI and USB cameras on the platform. (§2.1)
- NVU must be able to stream from USB Camera at max line-rate via Peer-to-peer fabric — up to **5 Gb/s** line rate on eUSB2V2. (§2.6)

---

#### MIPI CSI-2 Camera Interface (§8 Chapter 4, §2.5.1.4)

- IPU and NVU each have knowledge of which of the *n* C/D PHYs at the SoC are connected to the front-facing camera used for sensing; this information is derived from platform configuration and conveyed to the respective drivers. (§2.5.1.4.1)
- The CSI-2 Host Controller drives control signals to the PHY, including reset, clock, and shutdown. (§2.5.1.4)

##### PHY Sharing and Reset Behavior (§8.1.1)

- The Arbitration Logic is reset using `host_prim_rst_b`.
- The `Soft_reset` register resets the Arbitration Logic and all registers in the power-gated domain; it **must only be used for unexpected errors**.

##### MIPI CSI-2 Host Controller Integration (§8.7.2.2.3)

| Interface | Port Name(s) | Connectivity | Notes |
|---|---|---|---|
| IRQ | `interrupt` | VPX2 IRQ | Interrupt signal |
| PPI Clock Lane | `rxskewcalhs`, `rxwordclkhs`, `rxbyteclkhs`, `rxclkactivehs`, `rxulpsclknot`, `stopstateclk` | CSI-2 PHY | From PHY Sharing/Mux Logic |
| PPI Data Lane | `rxdatahs`, `rxinvalidcodehs`, `rxvalidhs`, `stopstatedata`, `rxulpsesc`, `err` | CSI-2 PHY | From PHY Sharing/Mux Logic |
| PHY Control | `phy`, `dphy` | To CSI-2 PHY | To be muxed at SoC with IPU |
| IPI RAM RD I/F | `ipi_rclk`, `ipi_raddr`, `ipi_rdata`, `ipi_ren` | IPI DP RF | IPI Read Port Memory 4Kx64 |
| IPI RAM WR I/F | `ipi_wclk`, `ipi_waddr`, `ipi_wdata`, `ipi_wen` | IPI DP RF | IPI Write Port Memory |
| IPI I/F | `pixclk`, `ipi_vsync`, `ipi_hsync`, `ipi_pixen`, `ipi_pixdata`, `ipi_data_end`, `ipi_data_valid` | Altek ISP | IPI Interface |

---

#### MIPI Camera Interfaces — IP Configuration (§4.3.9)

##### PPI Interface (§4.3.9.1)

| Interface | Unique Name | Reference Interface | Version |
|---|---|---|---|
| CSI2 PPI I/F – Primary | `PPI Primary I/F` | `Non-Standard::PPI I/F` | v1.0 r1.0 |
| CSI2 PPI I/F – Secondary | `PPI Secondary I/F` | `Non-Standard::PPI I/F` | v1.0 r1.0 |

- Reset domain for both Primary and Secondary PPI interfaces: **Not Defined**.

##### PHY Control and Status Interface (§4.3.9.2)

| Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|
| `nvu_p_phy_mode` | output | 1 | required | Primary CPHY/DPHY mode selector: `1` = CPHY, `0` = DPHY |
| `nvu_s_phy_mode` | output | 1 | required | Secondary CPHY/DPHY mode selector: `1` = CPHY, `0` = DPHY |
| `nvu_p_phy_rst_n` | output | 1 | required | Primary CPHY/DPHY reset |
| `nvu_s_phy_rst_n` | output | 1 | required | Secondary CPHY/DPHY reset |

- Interface unique name: `PHY Control Status I/F`; reference interface: `Non-Standard::PHY Control Status I/F`.
- Reset domain: **Not Defined**.

##### PHY APB Interface (§4.3.9.3)

| Interface | Unique Name | Reference Interface | Version | Side | Reset Domain |
|---|---|---|---|---|---|
| EXT PHY APB | `EXT_PHY` | `APB4` | vC r1.2 | Requester | `nvu_prim_rst_b` |
| APB_CLK | `APB4::Clock Requester` | `APB4::Clock` | — | Requester | `PRESETn` |
| APB_PRESETn | `APB4::Reset Requester` | `APB4::Reset` | — | Requester | `PRESETn` |

- `APB_CLK`: synchronous interface, sampled/driven on rising edge.
- `APB_PRESETn`: synchronous interface, sampled/driven on rising edge.

---

#### IPU MIPI-PHY Sharing Interface (§4.3.10)

| Interface | Unique Name | Reference Interface |
|---|---|---|
| IPU PHY Sharing I/F | `IPU PHY Sharing I/F` | `Non-Standard::IPU PHY Sharing I/F` |

- Reset domain: **Not Defined**.

---

#### USB Camera Interface (§8.3, §2.5.1.6)

- **IPU Exclusive Mode**: System is in S0 state and host application is accessing the camera. NVU is either disabled (through fuse, soft-strap, BIOS, or absence). (§8.3.1)
- NVU must support streaming from USB Camera at a max line-rate via peer-to-peer fabric (up to **5 Gb/s** on eUSB2V2). (§2.6)

##### SIO Component (§2.5.1.6.1)

- SIO Component Logic is responsible for handshake and data movement between NVU, the XHCI controller, and IPU via the peer-to-peer path provided by the SoC fabric.
- The protocol used for messaging and data transfers is Vendor Defined Messages (VDMs) over the SoC fabric.

##### IPU USB Camera Sharing Interface (§4.3.11)

| Interface | Unique Name | Reference Interface |
|---|---|---|
| IPU USB Camera Sharing I/F | `IPU USB Camera Sharing I/F` | `Non-Standard::IPU USB Camera Sharing I/F` |
| PHY Misc I/F | `PHY Misc I/F` | `Non-Standard::PHY Misc I/F` (v1.0 r1.0) |

- Reset domain for both interfaces: **Not Defined**.

---

#### SIO Peer-to-Peer Communication (§8.4)

- SIO component within NVU interconnects with `XHCI_CAM` and IPU Input System via SoC fabric. (§8.4)

##### VDM Message Format (§8.4.1.1)

| Bits | Field | Description |
|---|---|---|
| 71:64 | Target Route ID[15:8] | BDF of the Target |
| 79:72 | Target Route ID[7:0] | BDF of the Target |
| 87:80 | Vendor ID[15:8] | Vendor ID |
| 39:32 | Requester ID[15:8] | Requester ID; length field matches PCI Express convention: `1` = 1 DW, `2` = 2 DWs, `0` = 1024 DW |

- Value `0x7F` in the message type field indicates a Vendor Defined Message.

##### BDF Configuration for Remote Peer IPs (§8.4.1.2)

- New `SIO_RPIBDFx` registers have been added to allow IOSF2AXI bridge forwarding of SIO messages based on BDF (Target Route ID).
- FW **shall** program the `SIO_RPIBDFx` registers with the BDF values of corresponding peer IPs (i.e., `XHCI_CAM` and IPU).
- Refer to TTL PCD Register and Memory Mappings for the BDF values allocated for `XHCI_CAM`.
- Refer to SIO Component HAS for design details.

##### XHC TRB Commands (§8.4.2.2.4)

| TRB Type | XHCI Command | Description | TRB.DW3 Key Fields |
|---|---|---|---|
| 14 | Reset Endpoint Command | Reset selected endpoint; used to recover from a halted endpoint | TRB Type = `6'hF`; Endpoint ID[20:16]; Cycle bit[0] = `1` |
| 17 | Reset Device Command | Reset selected Device Slot; synchronizes Device Slot state when resetting a USB device | TRB Type = `6'hC`; Cycle bit[0] = `1`; Deconfigure(DC)[9] = `0` |

##### Error Handling (§8.4.2.1.7)

- Upon exception in NVU, NVU de-asserts `NVU_claim` at the earliest opportunity.
- NVU logs the exception context and attempts recovery through NVU core reset.
- Following recovery, NVU only reattempts operation under defined conditions.

##### Timestamp Drift Sources — XHCI_CAM (§8.4.2.2.3)

- Drift sources include:
  - Local ART vs. ART Base in PMC.
  - Different XTAL reference between `XHCI_Cam` and NVU (per TTL-PCD-H PerIP Clocks and AON Super SubSystem Integration HAS: XTAL reference in XHCI is run from a separate source).

---

#### MIPI Power Domain — Power Gating Interface (§4.3.4.2.3)

##### NVU_MIPI_PGCB

| Group | Signal Name | Direction | Width | Strap | Required | Description |
|---|---|---|---|---|---|---|
| Handshake | `nvu_mipi_pmc_pg_req_b` (`IP_PMC_PG_REQ_B`) | output | 1 | no | required | Request from IP or Fabric that IP wants to be power-gated |

- Interface: `NVU_MIPI_PGCB`; Reference: `PGCB`; Version: v2.0 r1.2; Side: Target; Type: power.
- Reset domain: `nvu_pgcb_rst_b`.

##### NVU_MIPI_FET_EN

- Interface: `NVU_MIPI_FET_EN`; Reference: `PGCB::FET`; Version: v2.0 r1.2; Side: Target; Type: power.
- Reset domain: `nvu_pgcb_rst_b`.


### Clock and Power Gating (17 facts)

#### Clock and Power Gating

#### Clock Gating Interface (4.3.4.1)

The NVU exposes multiple clock request/acknowledge handshake pairs. Each CLKREQ signal is driven as an output by the NVU to indicate that it requires a clock; the corresponding CLKACK is received as an input from the clock source.

| Signal Name (CLKREQ) | Signal Name (CLKACK) | Direction (REQ/ACK) | Reset Domain | Description |
|---|---|---|---|---|
| `nvu_func_clkreq` | `nvu_func_clkack` | output / input | `nvu_prim_rst_b` | Functional clock request/acknowledge handshake (FUNC_CLK_REQ_ACK) |
| `nvu_pgcb_clkreq` | `nvu_pgcb_clkack` | output / input | `nvu_pgcb_rst_b` | PGCB clock request/acknowledge handshake (PGCB_CLK_REQ_ACK) |
| `nvu_xtal_clkreq` | `nvu_xtal_clkack` | output / input | `nvu_prim_rst_b` | Crystal clock request/acknowledge handshake (XTAL_CLK_REQ_ACK) |
| `nvu_cdphy_xtal_clkreq` | `nvu_cdphy_xtal_clkack` | output / input | `nvu_prim_rst_b` | CDPHY crystal clock request/acknowledge handshake (CDPHY_XTAL_CLK_REQ_ACK) |
| `nvu_pixel_clkreq` | `nvu_pixel_clkack` | output / input | `nvu_prim_rst_b` | Pixel clock request/acknowledge handshake (PIXEL_CLK_REQ_ACK) |

- All CLKREQ signals are of handshake type, with a width of 1, no strap, and no discovery mechanism required. (§4.3.4.1)
- The `nvu_pgcb_clkreq/clkack` pair operates under the `nvu_pgcb_rst_b` reset domain; all other clock pairs operate under `nvu_prim_rst_b`. (§4.3.4.1)

---

#### Power Gating Interface (4.3.4.2)

##### Main Power Domain (4.3.4.2.1)

| Signal Name | Reset Domain | Description |
|---|---|---|
| `NVU_MAIN_PGCB` | `nvu_pgcb_rst_b` | Power gating control block interface for the NVU main power domain |
| `NVU_MAIN_FET_EN` | `nvu_pgcb_rst_b` | FET enable signal for the NVU main power domain |

##### USB Power Domain (4.3.4.2.2)

| Signal Name | Reset Domain | Description |
|---|---|---|
| `NVU_USB_PGCB` | `nvu_pgcb_rst_b` | Power gating control block interface for the NVU USB power domain |
| `NVU_USB_FET_EN` | `nvu_pgcb_rst_b` | FET enable signal for the NVU USB power domain |

- Both the Main and USB power domain PGCB and FET_EN signals are governed by the `nvu_pgcb_rst_b` reset domain. (§4.3.4.2)

---

#### IP Disable via Power Gating (§2.5.1.23)

- The SOC provides support for disabling the NVU via **Fuse**, **Soft-strap**, or **BIOS Menu**. (§2.5.1.23)
- When the NVU is disabled, the **PMC (Power Management Controller)** is responsible for maintaining the NVU in an **IP-Inaccessible Power Gated** state. (§2.5.1.23)

---

#### BIOS Programming: D0I3 / Power Gating Configuration Register (§7)

**Register:** `D0I3_MAX_POW_LAT_PG_CONFIG`
**Register Space:** CFG
**Offset:** `0xA0`
**Register Size:** 32 bits

| Field Name | Start Bit | End Bit | Size | Attribute | Reset Value | Recommended Value | Description |
|---|---|---|---|---|---|---|---|
| `SLEEP_EN` | 19 | 19 | 1 | RW | 0x0 | 0x0 | Enables sleep mode for D0I3/power gating control |
| `HAE` | 21 | 21 | 1 | RW | 0x0 | 0x1 | Hardware Autonomous Enable; BIOS should set to 1 to enable autonomous power gating |

- `SLEEP_EN` (bit 19): BIOS recommended value is **0** (disabled). (§7)
- `HAE` (bit 21): BIOS recommended value is **0x1** (enabled); this enables hardware-autonomous entry into low-power states. (§7)


### DMA Architecture (3 facts)

#### NVU Boot Method Decoding

The NVU boot mode is determined by a combination of fuse values: `HVM_MODE`, `DEBUG_MODE`, and `SECURE_LOAD`. (19 Fuses > 19.2 NVU Boot Method Decoding)

| HVM_MODE | DEBUG_MODE | SECURE_LOAD | Boot Mode |
|----------|------------|-------------|-----------|
| 1 | 0 | 0 | HVM Mode — Load from Host (Interrupt Driven) |
| X | 1 | 0 | DEBUG Mode — Load from Host/CSME (Polling Driven) |
| X | X | 1 | SECURE Load — Post Production |

- **HVM Mode**: Activated when `HVM_MODE = 1`, `DEBUG_MODE = 0`, and `SECURE_LOAD = 0`; firmware is loaded from the host using an interrupt-driven mechanism.
- **DEBUG Mode**: Activated when `DEBUG_MODE = 1` and `SECURE_LOAD = 0` (regardless of `HVM_MODE`); firmware is loaded from the host or CSME using a polling-driven mechanism.
- **SECURE Load**: Activated when `SECURE_LOAD = 1` (regardless of other fuse values); intended for post-production secure boot scenarios.


### DSP Core (VPX2) (106 facts)

#### DSP Core (VPX2)

### Overview

The NVU integrates an ARCv2VPX DSP core (VPX2). The sections below describe its memory map, interrupt assignments, integration interfaces, clocking, reset, and debug capabilities.

---

#### Timers (2.5.1.14)

| Timer | Clock Source | Frequency | Description |
|---|---|---|---|
| VPX Timer | Func Clock | 400 MHz | Timer inside VPX |
| Local ART | XTAL Clock | 38.4 MHz | NVU local ART timer running on XTAL clock, sync'd to global ART in the SoC |

---

#### VPX2 Addressable Memory Map (8.2.1)

- VPX2 has a **4 GB** addressable space divided into **16 regions** of **256 MB** each.

| Region | Size | Address Range | Memory Type | Target |
|---|---|---|---|---|
| 0 | 256 MB | `0x0000_0000` – `0x1000_0000` | Non-Volatile (Cacheable) | BROM/AONRF |
| 1 | 256 MB | `0x1000_0000` – `0x2000_0000` | Non-Volatile (Cacheable) | Reserved |
| 2 | 256 MB | `0x2000_0000` – `0x3000_0000` | Non-Volatile (Cacheable) | Reserved |
| 3 | 256 MB | `0x3000_0000` – `0x4000_0000` | Non-Volatile (Cacheable) | Reserved |
| 4 | 256 MB | `0x4000_0000` – `0x5000_0000` | Non-Volatile (Cacheable) | Reserved |
| 5 | 256 MB | `0x5000_0000` – `0x6000_0000` | Non-Volatile (Cacheable) | Reserved |
| 6 | 256 MB | `0x6000_0000` – `0x7000_0000` | Non-Volatile (Cacheable) | SRAM |
| 7 | 256 MB | `0x7000_0000` – `0x8000_0000` | Non-Volatile (Cacheable) | Reserved |
| 8 | 256 MB | `0x8000_0000` – `0x9000_0000` | Non-Volatile (Cacheable) | Reserved |
| 9 | 256 MB | `0x9000_0000` – `0xA000_0000` | Non-Volatile (Cacheable) | VCCM |
| 10 | 256 MB | `0xA000_0000` – `0xB000_0000` | Non-Volatile (Cacheable) | Reserved |
| 11 | 256 MB | `0xB000_0000` – `0xC000_0000` | Non-Volatile (Cacheable) | Reserved |
| 12 | 256 MB | `0xC000_0000` – `0xD000_0000` | Volatile (Non-Cacheable) | Reserved |
| 13 | 256 MB | `0xD000_0000` – `0xE000_0000` | Non-Volatile (Cacheable) | Reserved |
| 14 | 256 MB | `0xE000_0000` – `0xF000_0000` | Peripheral (Non-Cacheable) | Reserved |
| 15 | 256 MB | `0xF000_0000` – `0x1_0000_0000` | Peripheral (Non-Cacheable) | I/O Peripherals and Registers |

---

#### VPX2 Detailed Memory Map (8.2.2)

| Block | Sub Region | Sub Region Size | Start Address | End Address |
|---|---|---|---|---|
| FABRIC | FABRIC | 4 KB | `0xF370_0000` | `0xF370_1000` |

---

#### VPX2 Interrupt Table (8.1.1)

| Index | Module | IRQ Name | IRQ Pin | Address |
|---|---|---|---|---|
| 0 | ARCv2VPX | Reset | `irq0_a` | `0x00` |
| 35 | CRPM | RESETPREP IRQ | `irq35_a` | `0x8C` |
| 59 | FABRIC | MAIN_FABRIC IRQ | `irq59_a` | `0xEC` |
| 60 | FABRIC | SPARE0 IRQ | `irq60_a` | `0xF0` |
| 61 | FABRIC | SPARE1 IRQ | `irq61_a` | `0xF4` |
| 62 | FABRIC | SPARE2 IRQ | `irq62_a` | `0xF8` |

---

#### VPX2 Integration Interfaces (8.3.4)

##### Clock Interfaces

| Port Name | Connectivity | Description |
|---|---|---|
| `clk` | CRPM | DSP Functional Clock |
| `mbus_clk_en` | CRPM | Memory Bus Clock Enable (For Clock Division) for CBU I/F |
| `lbus0_clk_en` | CRPM | Peripheral Bus Clock Enable (For Clock Division) for LBU I/F |
| `stu_initiator_clk_en` | CRPM | STU Bus Clock Enable (For Clock Division) for STU I/F |

##### Reset Interface

| Port Name | Connectivity | Description |
|---|---|---|
| `rst_a` | CRPM | DSP Functional Reset |

##### AXI Bus Initiator Interfaces

| Interface | Port Name | Connectivity | Description |
|---|---|---|---|
| CBU AXI Initiator | `cbu_axi_*` | FABRIC | Combined Instruction Fetch and Data Access AXI Initiator Port |
| LBU AXI Initiator | `lbu_axi_*` | FABRIC | Peripheral Access AXI Initiator Port |
| STU AXI Initiator | `stu_axi_*` | FABRIC | Streaming Unit AXI Initiator Port |

##### Interrupt Interface

| Port Name | Connectivity | Description |
|---|---|---|
| `irq*_a` | — | VPX2 interrupt inputs (see interrupt table) |

##### Debug Run Control Interface (ARCSYNC)

| Port Name | Connectivity | Description |
|---|---|---|
| `arc_halt_req_a` | ARCSYNC | Run control halt request |
| `arc_halt_ack` | ARCSYNC | Run control halt acknowledge |
| `arc_run_req_a` | ARCSYNC | Run control run request |
| `arc_run_ack` | ARCSYNC | Run control run acknowledge |
| `clusternum[7:0]` | ARCSYNC | Connect to ARCSYNC |

##### JTAG Interface (4.3.6.3)

| Port Name | Connectivity | Description |
|---|---|---|
| `jtag_*` | JTAG | Connected to SoC JTAG interface |

- The JTAG TAP reset domain is **TRST_B**, driven by signal `nvu_vpx2_jtag_trst_n` (1-bit input, required).
- `TRST_B` provides reset for the primary TAP interface on SoC physical pins.

##### DFX Interface

| Port Name | Connectivity | Description |
|---|---|---|
| `test_mode` | DFX | DFX Test Mode |
| `cc_idle` | Open | — |

##### Static Tie-offs and Soft-Straps

| Port Name | Connectivity | Description |
|---|---|---|
| `vmem_sys_addr_base[31:0]` | Tie-off | Tie to `0x9000_0000` |
| `arcnum[7:0]` | Tie-off | Connect to ARCSYNC |
| `dbg_cache_rst_disable` | Soft-Strap | Connect to Soft-Strap |

---

#### Triple-Fault / Crash Dump Limitation (7.2.7)

- The VPX core generation integrated by NVU **does not support triple-fault/shutdown indication**.
- Triple-fault reset **cannot be triggered**.
- **Workaround (Synopsys recommendation):** Avoid relying on triple-fault behavior in firmware or BSP crash dump logic.


### Debug and Trace (1 facts)

#### Integration with System Services

- NVU HW includes DTF source packetizer and encoder blocks to support FW instrumentation trace output to Intel Trace Hub (NorthPeak). NVU FW defines DTF driver APIs to fulfill the functionality since Zephyr doesn't have DTF driver support natively. DMA usage for sending buffered trace packets is deprecated with trace format moving to MIPI Sys-T.


### Firmware (2 facts)

#### SOC or Platform Firmware

(HAS 20.1.2 SOC or Platform Firmware)

- BIOS programming requirements for the NVU are defined in the NVU BIOS Programming Guide (BWG).
  - **Note:** The BWG link requires updating: `https://docs.intel.com/documents/iparch/avb/fwarch/NVU/NVU%20Requirements%20to%20BIOS.html`


### GPIO and Pin Mux (10 facts)

#### GPIO and Pin Mux

#### GPIO Instance Overview

- The NVU GPIO instance supports **16 pins** (HAS §2.5.1.19.1)
- Note: A discrepancy exists in the HAS between the capabilities section (16 pins) and the functional description (32 pins); the authoritative capability statement specifies 16 pins (HAS §2.5.1.19.1)
- The GPIO interface conforms to **Non-Standard::GPIO Interface Version v1.0 r1.0**, instantiated on the Consumer side (HAS §4.3.12.1)
- The Reset Domain for the GPIO interface is listed as **Not Defined** (HAS §4.3.12.1)

#### GPIO Interface Signals

The following signals are defined for the NVU GPIO interface (HAS §4.3.12.1):

| Instantiated Signal Name | Direction | Dimension | Tie-off Value | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Description |
|---|---|---|---|---|---|---|---|---|---|
| `nvu_gpio_in` | input | `NUM_GPIO_PINS` | `0x0` | required | `nvu_prim_rst_b` | async | NA | rise_edge | GPIO Input |
| `nvu_gpio_dirctrl` | output | `NUM_GPIO_PINS` | NA | required | — | — | — | — | GPIO Direction Control |

> **Note:** Only signals explicitly defined in the HAS facts are listed above. Additional signal rows may exist in the full interface specification.

#### Input Multiplexing and OR Gate Architecture

- An **OR gate** is implemented at the SoC level on the NVU input, enabling flexible NVU GPIO connectivity to: (HAS §8.1.2)
  - Physical GPIO
  - Virtual GPIO (vGPIO)
  - Both simultaneously, through input signal multiplexing

#### Virtual GPIO (vGPIO) Pin Mux and Pad Mode Configuration

- For **vGPIO pins 8–15**, hardware defaults the pad mode to **GPIO mode** (HAS §8.1.2)
- **BIOS responsibility:** When the corresponding vGPIO pins (8–15) are selected for camera ownership handshake functionality, BIOS shall configure the pad mode to **Native Function (Native FN)** mode (HAS §8.1.2)

#### GPIO Configuration for Camera Sensor Control

- The following GPIO-related settings are **configured in BIOS** and **queried by the NVU SW driver** during OS boot, alongside other camera configurations (HAS §8.1.3.3):
  - Community
  - Group
  - Pad
  - Function
  - Initial value
  - Active value

#### NVU FW GPIO Access and Ownership Rules

- When NVU holds **camera sensor ownership**, NVU FW may drive pin TX by programming the corresponding **pad register in the SoC GPIO controller via IOSF-SB** (HAS §8.1.3.3)
- **Restriction:** NVU FW shall **not** modify any pad registers other than those corresponding to the pins it owns (HAS §8.1.3.3)


### IOSF Bridge (265 facts)

#### IOSF Bridge

The NVU integrates an IOSF2AXI bridge that connects the IOSF primary and sideband interfaces to the internal AXI fabric. This section documents the bridge straps, interface parameters, reset and clock domains, and BIOS programming requirements.

---

#### Overview

- The IOSF bridge translates between IOSF Primary/Sideband protocols and the internal AXI bus (§4.3)
- The bridge supports 16-bit sideband Port IDs when `nvu_br_strap_sb_srcdestid_16bit` is set to 1 (§4.3.1)
- The bridge supports Multi Function Device mode via `nvu_br_strap_mulfndev` (§4.3.1)
- The DST_ID_WIDTH functional parameter defaults to 15 bits for IOSF Destination ID width (§4.1.1)
- A softstrap (`NVU_SPARE_SS7`) is available to bypass IOSF2AXI bridge D3 functionality: `0` = no D3 bypass (default), `1` = bypass D3 functionality (§19.1)

---

#### IOSF Primary Interface Parameters (§4.3.7.1)

| Parameter | Type | Default | Configurable | Description |
|---|---|---|---|---|
| BusSelect | bit | 0 | no | Bus Select: transaction claimed only if address[0] matches BusSelect strap for Type 0 configuration transactions; `1` = Type 0 Primary Bus Select |
| NUM_ROOT_SPACES | uint32 | 2 | no | Number of Root Spaces (zeros-based) |
| STRAP_REQ_PULL_GROUP | uint32 | 0 | no | Soft-Strap Pull Group |
| CREDIT_DATA_WIDTH | uint32 | 0 | no | Credit Data Width: specifies the width of the `[m/t]credit_data` signal |
| SharedCreditsEn | bool | 0 | no | Shared Credits Enable: enables the shared credit feature |
| TTIF_ENABLED | bool | 0 | no | If set to `1`, the arbitration phase on the Master Control Interface is replaced with a transaction flow control phase |
| IOSF_Max_Payload_Size (IMPS) | bit3 | 0 | no | Sets the maximum transaction payload size for an agent on its IOSF primary interface |

---

#### IOSF Primary Interface Signals (§4.3.7.1)

**MCOMMAND (Master, output):**

| Signal Group | Signal Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| MCOMMAND | nvu_iosf_prim_mrqid | output | 16 | required | Requester ID: Bus Number[15:8], Device Number[7:3], Function Number[2:0] |
| MCOMMAND | nvu_iosf_prim_mrsvd1_7 | output | 1 | optional-conditional `Or(SupportsRSVD, RequesterTenBitTagEn, CompleterTenBitTagEn)` | PCI Express Reserved header field bit 7 |
| MCOMMAND | nvu_iosf_prim_mrsvd1_3 | output | 1 | optional-conditional `Or(SupportsRSVD, RequesterTenBitTagEn, CompleterTenBitTagEn)` | PCI Express Reserved header field bit 3 |

**TCOMMAND (Target, input):**

| Signal Group | Signal Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| TCOMMAND | nvu_iosf_prim_trqid | input | 16 | required | Requester ID: Bus Number[15:8], Device Number[7:3], Function Number[2:0] |
| TCOMMAND | nvu_iosf_prim_trsvd1_7 | input | 1 | optional-conditional `Or(SupportsRSVD, RequesterTenBitTagEn, CompleterTenBitTagEn)` | PCI Express Reserved header field bit 7 |
| TCOMMAND | nvu_iosf_prim_trsvd1_3 | input | 1 | optional-conditional `Or(SupportsRSVD, RequesterTenBitTagEn, CompleterTenBitTagEn)` | PCI Express Reserved header field bit 3 |

---

#### IOSF Primary Reset (NVU_PRIM_RST) (§4.3.3)

| Property | Value |
|---|---|
| Interface Type | reset |
| Instantiated Unique Name | NVU_PRIM_RST |
| Interface Version | v1.4.1 r0.2 |
| Interface Side | Consumer |
| Reset Domain | Not Defined |
| Sync/Async | async |
| Clock Name | nvu_br_prim_clk |
| Power Domain | VNN |
| Reset Domain Signal | nvu_prim_rst_b |

**PRIM_RST_B Signal:**

| Signal Name | Port Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| PRIM_RST_B | nvu_prim_rst_b | input | 1 | required | Primary Interface Reset: specifies the primary reset |

---

#### IOSF Sideband Reset (NVU_SIDE_RST) (§4.3.3)

| Property | Value |
|---|---|
| Interface Type | function |
| Instantiated Unique Name | NVU_SIDE_RST |
| Interface Version | v1.4 r1.4 |
| Interface Side | Agent |
| Reset Domain | Not Defined |
| Sync/Async | async |
| Clock Name | nvu_br_side_clk |
| Power Domain | VNN |
| Reset Domain Signal | nvu_side_rst_b |

**SIDE_RST_B Signal:**

| Signal Name | Port Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| SIDE_RST_B | nvu_side_rst_b | input | 1 | required | Sideband reset; connects to IOSF sideband reset |

---

#### IOSF Clock Domains (§4.3.2)

| Clock | Reset Domain |
|---|---|
| IOSF Primary Clock (`nvu_br_prim_clk`) | Not Defined |
| IOSF Sideband Clock (`nvu_br_side_clk`) | Not Defined |

---

#### IOSF Sideband Interface Signals (§4.3.7.2)

| Signal Name | Port Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| SIDE_POK | nvu_iosf_sb_side_pok | output | 1 | optional | Sideband Power OK signal |

- Reset domain for all IOSF Sideband interfaces (Agent, Power, POK): `nvu_side_rst_b` (§4.3.7.2)

---

#### IOSF Bridge Straps (§4.3.1)

All straps listed below are inputs and required unless otherwise noted.

| Strap Name | Width | Description / Tie-off |
|---|---|---|
| nvu_br_strap_mulfndev | 1 | IOSF2AXI BR Multi Function Device — refer SOC PSF HAS |
| nvu_br_strap_sb_srcdestid_16bit | 1 | `1` → 16-bit SB Port ID; `0` → 8-bit Port ID |
| nvu_br_strap_bridge_portid | 16 | NVU Port ID |
| nvu_br_strap_deviceid | 16 | NVU Device ID — tie to NVU DEVICEID |
| nvu_br_devfuncnum | 8 | NVU Device Function Number |
| nvu_br_strap_busno_rs | 24 | Bus Number for each Root Space — refer PSF HAS |
| nvu_br_strap_port | 4 | PSF Port — refer PSF HAS |
| nvu_br_strap_port_group | 1 | PSF Group — refer PSF HAS |
| nvu_br_strap_psf | 4 | PSF Number — refer PSF HAS |
| nvu_br_strap_cpl_mdestid | 52 | Completion Destination ID per Root Space — refer SOC PSF HAS |
| nvu_br_strap_pcierr_destid | 48 | PCIERR Destination ID per Root Space — tie to IEH Port ID |
| nvu_br_strap_destid_host | 15 | Host Destination ID — unused, tie to `0x0` |
| nvu_br_strap_destid_xhci | 15 | XHCI_CAM Destination ID — tie to DESTID of XHCI_CAM |
| nvu_br_strap_destid_ipu | 15 | IPU Destination ID — tie to IPU DESTID |
| nvu_iosf_prim_prim_prim_tdest_id | 15 | DESTID of DS access — unused, tie to `0x0` |
| nvu_br_strap_ltr_destid | 16 | LTR Message Destination ID — tie to PMC Port ID |
| nvu_br_strap_pme_destid | 8 | PME Destination ID — tie to PMC Port ID |
| nvu_br_strap_pme_support | 5 | PME Support — tie to `0x9` (enable in D0 and D3) |
| nvu_br_strap_pm_msg_sai | 8 × NUM_PM_MSG_AGENTS | PM MSG SAI[0] — tie to PMC SAI |
| nvu_br_strap_untrusted_sai | 8 | Untrusted SAI — tie to Platform Untrusted SAI |
| nvu_br_strap_fp_sai | 8 | Fuse Puller Request SAI — tie to NVU_SAI |
| nvu_br_strap_fp_sai_cmpl | 64 | Fuse Puller Completion SAI — tie to Completion SAI from FP |
| nvu_br_strap_fp_destid | 128 | Fuse Puller Destination ID — tie to FP Port ID |

---

#### BIOS Programming Recipe — PMCTL Register (§7)

| Reg Space | Offset | Reg Name | Field Name | Start Bit | End Bit | Attribute |
|---|---|---|---|---|---|---|
| PCR | 0x1D0 | PMCTL | IOSF_SB_LOCAL_GATE_EN | 5 | 5 | RW |
| PCR | 0x1D0 | PMCTL | IOSF_PRIM_LOCAL_GATE_EN | 4 | 4 | RW |
| PCR | 0x1D0 | PMCTL | AXI_LOCAL_GATE_EN | 3 | 3 | RW |
| PCR | 0x1D0 | PMCTL | IOSF_PRIM_TRUNK_GATE_EN | 2 | 2 | RW |
| PCR | 0x1D0 | PMCTL | IOSF_SB_TRUNK_GATE_EN | 1 | 1 | RW |

- BIOS must program the PMCTL register at PCR offset `0x1D0` to configure IOSF primary, sideband, and AXI local/trunk clock gating enables (§7)


### Interrupt Configuration (2 facts)

#### Watchdog Timer (WDT) Interrupt Configuration

(Ref: 2 Introduction > 2.5 Requirements > 2.5.1 Capabilities > 2.5.1.14 Timers; 7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.8 WDT)

##### Timer Properties

| Timer | Clock Source | Frequency | Clock Divider Value |
|-------|-------------|-----------|-------------------|
| WDT | Func Clock (`func_clk_clock`) | 63.9 Hz | `0x17DDC4` |

##### Behavioral Description

- The WDT clock is derived by dividing `func_clk_clock` by the recommended divider value of `0x17DDC4`, resulting in an operating frequency of 63.9 Hz.
- The Watchdog Timer generates an interrupt if the NVU code fails to reload the timer within the specified timeout period.
- The WDT follows a **two-stage timeout sequence**:
  - **First timeout:** Triggers an interrupt to the NVU.
  - **Second timeout:** Issues a hardware reset of the NVU.


### Neural Network Accelerator (133 facts)

#### Neural Network Accelerator

### Overview

The Intel NVU (Neural Vision Unit) Neural Network Accelerator integrates a scalable compute and memory subsystem designed for high-performance neural network inference workloads.

#### Key Architectural Features (Section 2.2)

- Scalable high-performance SRAM sub-system with SRAM Slice Controllers
- Support for scalable tile configurations
- In-line SECDED ECC support
- Run-time retention capability
- High Performance Fabric interconnect

#### Performance Characteristics (Section 2.6)

| Domain | Performance Metric |
|---|---|
| Fabric Performance | NVU backbone fabric supports max bandwidth of 6.4 GB/s between compute and memory |
| Peer-to-Peer Fabric | Up to 5 GB/s |

---

### Reference Documents (Section 4)

| Index | Document | Location |
|---|---|---|
| — | NVU Clocking Reset Power Management (CRPM) MAS | Link |
| — | NVU SoC Integration Documents | NVU SoC Integration Documents |
| — | TTL Vision SubSystem Integration HAS | Link |
| — | TTL PCD-H Elemental Security Engine (ESE) Integration HAS | Link |
| — | SoC and Platform Documents | SoC and Platform Documents |
| 11 | TTL PCD-H NVU SoC Integration HAS | Link |
| 12 | TTL AON Super SubSystem Integration HAS | Link |
| 16 | TTL PCD NoC Crux-based IOSF Primary Fabric | Link |
| 17 | TTL NOC FABRIC Power Management | Link |
| 18 | TTL PCD Primary Fabric HAS | Link |
| 20 | TTL USB Subsystem Integration | Link |
| 25 | TTL Platform Firmware Architecture Specification (FAS) | Link |

---

### IP Configuration — Interfaces (Section 4.3)

#### Straps (Section 4.3.1)

- Straps follow the **Non-Standard::Straps** reference interface pattern.

#### Clocks (Section 4.3.2)

| Interface Name | Unique Name | Reference Interface | Version |
|---|---|---|---|
| IOSF Primary Clock | NVU_BR_PRIM_CLK | IOSF::Primary::Clock | v1.4 r0.2 |
| IOSF Sideband Clock | NVU_BR_SIDE_CLK | IOSF::SB::Clock | v1.4 r1.4 |

#### Resets (Section 4.3.3)

| Interface Name | Unique Name | Reference Interface | Version | Interface Side | Type |
|---|---|---|---|---|---|
| IOSF Primary Reset | NVU_PRIM_RST | IOSF::Primary::Reset | v1.4.1 r0.2 | — | reset |
| IOSF Sideband Reset | NVU_SIDE_RST | IOSF::SB::Reset | v1.4 r1.4 | — | function |
| PGCB Reset | NVU_PGCB_RST | PGCB::Reset | v2.0 r1.2 | Target | power |

#### Power Management — Clock Gating Interfaces (Section 4.3.4.1)

All clock gating interfaces use Reference Interface Name **CLOCK_REQ_ACK**, version **v2.0 r1.1**, Interface Side **Consumer**, Interface Type **function**.

| Interface Name | Unique Name |
|---|---|
| FUNC_CLK_REQ_ACK | FUNC_CLK_REQ_ACK |
| PGCB_CLK_REQ_ACK | PGCB_CLK_REQ_ACK |
| XTAL_CLK_REQ_ACK | XTAL_CLK_REQ_ACK |
| CDPHY_XTAL_CLK_REQ_ACK | CDPHY_XTAL_CLK_REQ_ACK |
| PIXEL_CLK_REQ_ACK | PIXEL_CLK_REQ_ACK |

#### Power Management — Power Gating Interfaces (Section 4.3.4.2)

**Main Power Domain** (Section 4.3.4.2.1)

| Interface Name | Unique Name | Reference Interface | Version | Interface Side | Type | Reset Domain |
|---|---|---|---|---|---|---|
| NVU_MAIN_PGCB | NVU_MAIN_PGCB | PGCB | v2.0 r1.2 | Target | power | nvu_pgcb |
| NVU_MAIN_FET_EN | NVU_MAIN_FET_EN | PGCB::FET | v2.0 r1.2 | Target | power | — |

**USB Power Domain** (Section 4.3.4.2.2)

| Interface Name | Unique Name | Reference Interface | Version | Interface Side | Type | Reset Domain |
|---|---|---|---|---|---|---|
| NVU_USB_PGCB | NVU_USB_PGCB | PGCB | v2.0 r1.2 | Target | power | nvu_pgcb |
| NVU_USB_FET_EN | NVU_USB_FET_EN | PGCB::FET | v2.0 r1.2 | Target | power | — |

#### Debug Interfaces (Section 4.3.6)

**VISA** (Section 4.3.6.1)

| Property | Value |
|---|---|
| Unique Name | VISA |
| Reference Interface | Non-Standard::VISA |
| Version | v1.0 r1.0 |
| Interface Side | Producer |
| Interface Type | dft |

**DTF** (Section 4.3.6.2)

| Property | Value |
|---|---|
| Unique Name | DTF |
| Reference Interface | DTF::Signals |
| Version | v1.4 r1.4 |
| Interface Side | Producer |
| Interface Type | dfd |
| Reset Domain | nvu_prim_rst_b |

- **DTF_MISC**: Unique Name `DTF_MISC`, Reference Interface `Non-Standard::DTF_MISC`, Version v1.0 r1.0, Interface Side Producer, Interface Type dft.

**JTAG** (Section 4.3.6.3)

| Interface Name | Unique Name | Reference Interface | Sync/Async | Sample Edge | Role |
|---|---|---|---|---|---|
| VPX2 JTAG TRSTn | VPX2 JTAG::Reset | JTAG::Reset | sync | rise_edge | Consumer |
| MAIN STAP TRSTn | MAIN STAP::Reset | JTAG::Reset | sync | rise_edge | Consumer |
| VPX2 JTAG | VPX2 JTAG | JTAG | sync | rise_edge | Consumer |
| MAIN STAP | MAIN STAP | JTAG | sync | rise_edge | Consumer |

#### Host Interfaces (Section 4.3.7)

**IOSF Primary** (Section 4.3.7.1)

| Property | Value |
|---|---|
| Unique Name | IOSF_Primary_Consumer |
| Reference Interface | IOSF::Primary |
| Version | v1.4.1 r0.2 |
| Interface Side | Consumer |

- `MCONTROL REQ_CHAIN` is **NOT_SUPPORTED** (output, dimension 1, conditional on `And(SupportsRequestChaining, Not(TTIF_ENABLED))`). This signal is provided as a hint to the fabric arbiter that the IOSF agent has a sequence of transactions.

**IOSF Sideband** (Section 4.3.7.2)

| Interface Name | Unique Name | Reference Interface | Version | Interface Side | Type | Sync/Async |
|---|---|---|---|---|---|---|
| IOSF_Sideband_Agent | IOSF_Sideband_Agent | IOSF::SB | v1.4 r1.4 | Agent | function | — |
| IOSF_Sideband_Power | IOSF2AXI_SB_Power_Agent | IOSF::SB (Power) | — | — | function | async |
| IOSF_Sidebnd_POK | IOSF2AXI_Sideband_POK | IOSF::SB::POK | — | — | function | sync |

#### IO Interfaces — SPI (Section 4.3.12.4)

| Property | Value |
|---|---|
| Unique Name | SPI |
| Reference Interface | Non-Standard::SPI |
| Version | v1.0 r1.0 |
| Interface Side | Consumer |
| Interface Type | function |

#### DFT Interfaces — Scan (Section 4.3.13.1)

| Property | Value |
|---|---|
| Unique Name | IOSF::DFX::SCAN |
| Reference Interface | IOSF::DFX (Scan) |
| Interface Type | function |
| Sync/Async | async |
| Sample/Drive Edge | rise_edge |
| Role | Consumer |

---

### NPX6 Debug Memory Map — ARCTrace and L1 Core Registers (Section 8.2.3.2.2)

The following registers are located in the NPX6 Debug Memory Map under ARCTrace and L1 Core Registers.

| Register | Address | Mode | Description |
|---|---|---|---|
| DB_STAT | 0x000 | — | Debug Status register |
| DB_CMD | 0x004 | — | Debug Command register |
| DB_ADDR | 0x008 | — | Debug Address register |
| DB_DATA | 0x00C | — | Debug Data register |
| DB_RESET | 0x010 | — | Debug Reset register |
| ITCTRL | 0xF00 | — | Integration Mode Control register — not used, RAZ |
| CLAIMSET | 0xFA0 | RAZ/WI | Claim Tag Set register |

---

### WAMR Memory Management — Shared Memory (Section 11.5.2)

- The **shared heap** is an advanced WAMR feature that provides flexibility to share data between multiple WASM instances.
- When using the shared heap, the same address mapping is maintained across different WASM instances.
- Shared heap memory can also be shared between WASM instances and other NVU firmware components.


### NoC Fabric (309 facts)

### NoC Fabric

#### Overview

(§2.5.1.9)

- NVU implements a network-on-chip (NoC) based interconnect fabric based on **Arteris FlexNoC®** technology
- Supports a mix of **AXI, AHB, APB, and OCP** initiators and targets
- Fabric power-down/acknowledge protocol enables trunk-level clock gating and power gating flows

---

#### AONRF/BROM Controller

(§2.5.1.8)

- Highly scalable controller that converts fabric bus cycles to memory cycles
- Supports **zero-wait-state** access from fabric to memories

---

#### IOSF to AXI Bridge

(§2.5.1.11)

- NVU interfaces to the PCH's IOSF Primary and IOSF-SB using the IOSF to AXI Bridge
- To the IOSF backbone, NVU appears as a **PCI device**; the bridge connects to NVU's internal fabric
- Due to the fixed address map on the fabric, a **remap is required** for accesses from the IOSF-SB
- The IOSF-to-AXI bridge uses the **BAR0 register** (in PCI Config space) to add the offset from the IOSF-SB (§7.2.3.12)

---

#### NoC Fabric Interfaces

### Power Management Signals

(§4.3.4.2)

#### Main Power Domain

| Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|
| `nvu_main_pmc_pg_req_b` | output | 1 | required | Request from IP or Fabric that IP wants to be power-gated (IP_PMC_PG_REQ_B) |

#### USB Power Domain

| Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|
| `nvu_usb_pmc_pg_req_b` | output | 1 | required | Request from IP or Fabric that IP wants to be power-gated (IP_PMC_PG_REQ_B) |

---

### Resource Management Signals

(§4.3.5)

| Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|
| `nvu_func_clk_own_req` | output | 1 | required | Functional Clock Resource Ownership Request |
| `nvu_func_clk_own_ack` | input | 1 | required | Functional Clock Resource Ownership Ack |
| `nvu_prim_clk_own_req` | output | — | required | Primary Clock Resource Ownership Request |
| `nvu_peer_fabric_own_req` | output | 1 | required | Peer Fabric Resource Ownership Request |
| `nvu_peer_fabric_own_ack` | input | 1 | required | Peer Fabric Resource Ownership Ack |

---

### Debug Interfaces

#### VISA Signals

(§4.3.6.1)

| Signal Name | Direction | Width | Required | Power Domain | Description |
|---|---|---|---|---|---|
| `nvu_fvisa_frame` | input | 1 | required | VNN | Fabric VISA frame |
| `nvu_fvisa_serstrb` | — | — | — | — | VISA serial strobe (rising edge) |
| `nvu_fvisa_startid` | input | 9 | required | VNN | Fabric VISA start ID |
| `nvu_fvisa_endid` | input | 9 | required | VNN | Fabric VISA ending ID |
| `nvu_fvisa_startid_1` | input | 9 | required | VNN | Fabric VISA start ID (second instance) |
| `nvu_fvisa_endid_1` | input | 9 | required | VNN | Fabric VISA ending ID (second instance) |

- All VISA signals are synchronised to `nvu_fdfx_powergood`, captured on rising edge of `nvu_fvisa_serstrb`

#### DTF (Debug Trace Fabric) Signals

(§4.3.6.2)

| Signal Name | Direction | Width | Required | Description |
|---|---|---|---|---|
| `nvu_dnstream_header_out` | output | 25 | required | DTF Header (`adtf_dnstream_header_out`) |
| `nvu_dnstream_data_out` | output | 64 | required | Packet data (`adtf_dnstream_data_out`) |
| `nvu_dnstream_valid_out` | output | — | required | Downstream valid out |
| `nvu_upstream_active_in` | input | 1 | required | Fabric tracing is active (`fdtf_upstream_active_in`) |

---

### IOSF Primary Interface

(§4.3.7.1)

#### IOSF Primary Configuration Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `MMAX_ADDR` | uint32 | MMAX_ADDR | Master Interface Maximum Address: address bus width on the master side |
| `TMAX_ADDR` | uint32 | MMAX_ADDR | Target Interface Maximum Address: address bus width on the target side |
| `PARITY_REQUIRED` | bool | 0 | Parity Required: set to `1` if the IOSF fabric requires parity |
| `CID_WIDTH` | uint32 | 0 | Specifies the CID width on the master and target interface |
| `TgtInputFlops` | uint32 | 0 | Target Input Flops: when set, `prim_ism_fabric` and all target inputs are flopped |
| `SharedCreditsEn` | bool | 0 | Shared Credits Enable: enables the shared credit feature |
| `SupportsSAI` | bool | 1 | SAI: specifies whether Security Attributes of Initiator (SAI) bits are present |

#### IOSF Primary Master Control Signals

| Group | Signal Name | Direction | Width | Condition | Description |
|---|---|---|---|---|---|
| MCONTROL | `nvu_iosf_prim_req_put` | output | 1 | conditional, Not(TTIF_ENABLED) | Request Put: asserted for one clock cycle to push a request to the fabric arbiter |
| MCONTROL | NOT_SUPPORTED (REQ_OPP) | output | 1 | optional-conditional, Not(TTIF_ENABLED) | Request Opportunistic: fabric may delay servicing this request |
| MCONTROL | `nvu_iosf_prim_req_priority` | output | MNUMCHAN+1 | optional-conditional, And((MNUMCHAN!=0),Not(TTIF_ENABLED)) | Priority Request: priority per channel from agent |
| MCONTROL | `nvu_iosf_prim_req_dest_id` | output | DST_ID_WIDTH+1 | optional-conditional, Not(TTIF_ENABLED) | Destination ID: source-decoded destination information |
| MCONTROL | `nvu_iosf_prim_gnt` | input | 1 | conditional, Not(TTIF_ENABLED) | Grant: asserted by fabric in response to a request |
| MCONTROL | NOT_SUPPORTED (OBFF) | input | 2 | conditional, SupportsDefferingInLowPower | Optimized Buffer Flush/Fill (OBFF): signal from fabric indicating low-power deferring |
| MCONTROL | NOT_SUPPORTED (MCMD_PUT) | output | 1 | conditional, TTIF_ENABLED | Master Command Put: asserted by fabric to put a command to target agent |
| MCONTROL | NOT_SUPPORTED (MCMD_CHID) | output | MNUMCHANL2+1 | conditional, And((MNUMCHAN!=0),TTIF_ENABLED) | Master Command Channel ID: identifies targeted channel |
| MCONTROL | NOT_SUPPORTED (MCMD_RTYPE) | output | 2 | optional-conditional, TTIF_ENABLED | Master Put Request Type: 00=Posted, 01=Non-Posted, 10=Completion, 11=Reserved |
| MCONTROL | NOT_SUPPORTED (MCMD_NFS_ERR) | output | 1 | optional-conditional, And(SupportsNFSError,TTIF_ENABLED) | Master Put Non-Function Specific Error |

#### IOSF Primary Master Command Signals

| Group | Signal Name | Direction | Width | Condition | Description |
|---|---|---|---|---|---|
| MCOMMAND | `nvu_iosf_prim_mlength` | output | 10 | required | Transaction Length |
| MCOMMAND | `nvu_iosf_prim_maddress` | output | MMAX_ADDR+1 | required | Transaction Address (memory/IO address or Completion) |
| MCOMMAND | `nvu_iosf_prim_msrc_id` | output | SRC_ID_WIDTH+1 | optional-conditional, SupportsMasterSrcIdTargetDestId | Source ID: Source ID information to fabric |
| MCOMMAND | `nvu_iosf_prim_mdest_id` | output | DST_ID_WIDTH+1 | conditional, SupportsMasterDestIdTargetSrcId | Destination ID: source-decoded destination information |
| MCOMMAND | `nvu_iosf_prim_mat` | output | 2 | optional-conditional, SupportsAddressTranslation | Address Translation Services: AT field for memory transactions |
| MCOMMAND | NOT_SUPPORTED (MPRIORITY) | output | MNUMCHAN+1 | conditional, And(SupportsDeadline,TTIF_ENABLED) | Priority Request per channel |
| MCOMMAND | NOT_SUPPORTED (MCHAIN) | output | 1 | conditional, And(SupportsTargetCmdChaining,TTIF_ENABLED) | Chain: chain command attribute forwarded to target |

#### IOSF Primary Target Control Signals

| Group | Signal Name | Direction | Width | Condition | Description |
|---|---|---|---|---|---|
| TCONTROL | `nvu_iosf_prim_tdec` | input | 1 | optional-conditional, Not(TargetDecodeDisable) | Target Decode: asserted by fabric to cause agent to decode transaction |
| TCONTROL | NOT_SUPPORTED (SUB_HIT) | output | TNUMCHAN+1 | optional-conditional, Not(TargetDecodeDisable) | Subtractive Hit: asserted if transaction subtractively decodes |

#### IOSF Primary Target Command Signals

| Group | Signal Name | Direction | Width | Condition | Description |
|---|---|---|---|---|---|
| TCOMMAND | `nvu_iosf_prim_cmd_put` | input | 1 | required | Command Put: asserted by fabric to put a command to target agent |
| TCOMMAND | `nvu_iosf_prim_cmd_chid` | input | TNUMCHANL2+1 | conditional, (TNUMCHAN!=0) | Command Channel ID: identifies targeted channel |
| TCOMMAND | `nvu_iosf_prim_cmd_rtype` | input | 2 | required | Put Request Type: 00=Posted, 01=Non-Posted, 10=Completion, 11=Reserved |
| TCOMMAND | NOT_SUPPORTED (CMD_NFS_ERR) | input | 1 | optional-conditional, SupportsNFSError | Put Non-Function Specific Error |
| TCOMMAND | NOT_SUPPORTED (TCHAIN) | input | 1 | conditional, SupportsTargetCmdChaining | Chain: chain command attribute from fabric arbiter |
| TCOMMAND | `nvu_iosf_prim_taddress` | input | TMAX_ADDR+1 | required | Transaction Address (memory |


### PMC Integration and Wake (7 facts)

#### PMC Integration Overview

The NVU interfaces with the SoC/PCH Power Management Controller (PMC) to receive and process system-level control messages and distribute platform timing signals. (HAS §7.2.3.12)

---

#### PMC SideBand Message Reception

The NVU receives system-specific sideband messages originating from the SoC/PCH PMC. Supported message types include:

- **ResetPrep** — signals the NVU to prepare for a platform reset sequence
- **BootPrep** — indicates an impending boot flow requiring NVU readiness
- **SETID** — delivers identity assignment from the PMC
- **Hammock Harbor** — conveys time synchronization protocol messages (see §Hammock Harbor Support below)
- **Fuse Pull requests** — triggers fuse data retrieval sequences

(HAS §7.2.3.12)

---

#### Hammock Harbor Time Synchronization

- Hammock Harbor (HH) is a platform-wide protocol for accurate time distribution across all HH-capable components. (HAS §2.5.1.22.1.1)
- An **Always Running Timer (ART)** is implemented within the **Always Running Unit (ARU)** residing in the PMC. (HAS §2.5.1.22.1.1)
- The NVU receives Hammock Harbor messages via the PMC sideband interface to synchronize with the platform ART. (HAS §7.2.3.12, §2.5.1.22.1.1)

---

#### PMC Telemetry and Platform Monitoring

- PMC telemetry data generated by the NVU is retrievable by the **IPF Platform Monitoring Technology (PMT)** provider. (HAS §11.6.3)
- PMT exposes this telemetry to host software clients for platform health and performance monitoring purposes. (HAS §11.6.3)

---

#### Power Management Register Requirements

The following tracked requirements govern default reset values and configuration for PMC-related registers:

| Requirement ID | Owner | Title | Status |
|---|---|---|---|
| 15018335923 | rchaddha | [TTL][NVU] Update Default Reset Values for HAE, PMCTL, D0i3 Max Power Latency and BAR1_Disable Registers | POR |
| 16028406377 | rchaddha | [NVU][SMMU] Update ACE Config PMEM size to 8MB | POR |

(HAS §2.5 Requirements)

- The `PMCTL`, `HAE`, `D0i3 Max Power Latency`, and `BAR1_Disable` registers have pending updates to their default reset values per requirement 15018335923. (HAS §2.5)
- The ACE configuration PMEM size is updated to **8 MB** per requirement 16028406377. (HAS §2.5)

---

#### Fuse Configuration

| Name | Fuse Index | Reset Value | Description |
|---|---|---|---|
| StrapMemLimit | 0 | 0 | Memory limit strap fuse configuration | 

(HAS §19.1)


### Peripheral Interfaces (32 facts)

#### Peripheral Interfaces

---

#### I2C Interface (§4.3.12.2)

The NVU exposes an I2C interface defined as a Non-Standard::I2C v1.0 r1.0 Consumer-side interface. The reset domain is Not Defined for interface-level metadata.

**I2C Signal Table**

| Instantiated Signal Name | Direction | Dimension | Tie-off Value | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Description |
|---|---|---|---|---|---|---|---|---|---|
| `nvu_i2c_clk_in_a` | input | NUM_I2C | 0x1 | required | `nvu_prim_rst_b` | async | NA | rise_edge | I2C Clock Input |
| `nvu_i2c_data_in_a` | input | NUM_I2C | 0x1 | required | `nvu_prim_rst_b` | async | NA | rise_edge | I2C Data Input |

**I2C Controller Configuration Parameters** (§8.17.3)

| Parameter Symbol | Type | Default Value | Description |
|---|---|---|---|
| `SLAVE_INTERFACE_TYPE` | uint32 | 0 | APB2 |
| `IC_DEFAULT_SLAVE_ADDR` | uint32 | 0x055 | Reset value of IC_SAR |
| `IC_DEFAULT_TAR_SLAVE_ADDR` | uint32 | 0x055 | Reset value of IC_TAR |
| `IC_MASTER_MODE` | uint32 | 0x1 | Default to master mode after reset |
| `IC_SLAVE_DISABLE` | uint32 | 0x1 | Slave disabled after reset |
| `IC_TX_TL` | uint32 | 0x0 | Reset value of Tx FIFO threshold |
| `IC_RX_TL` | uint32 | 0x0 | Reset value of Rx FIFO threshold |

---

#### I3C Interface (§4.3.12.3)

The NVU exposes an I3C interface defined as a Non-Standard::I3C v1.0 r1.0 Consumer-side interface. The reset domain is Not Defined for interface-level metadata.

**I3C Signal Table**

| Instantiated Signal Name | Direction | Dimension | Tie-off Value | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Description |
|---|---|---|---|---|---|---|---|---|---|
| `nvu_i3c_scl_in_a` | input | NUM_I3C | 0x1 | required | `nvu_prim_rst_b` | async | `nvu_func_clk` | rise_edge | I3C Clock Input |
| `nvu_i3c_sda_in_a` | input | NUM_I3C | 0x1 | required | `nvu_prim_rst_b` | async | `nvu_func_clk` | rise_edge | I3C Data Input |

---

#### UART Interface (§4.3.12.5)

The NVU exposes a UART interface defined as a Non-Standard::UART v1.0 r1.0 Consumer-side interface. The reset domain is Not Defined for interface-level metadata.

**UART Signal Table**

| Instantiated Signal Name | Direction | Dimension | Tie-off Value | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Description |
|---|---|---|---|---|---|---|---|---|---|
| `nvu_uart_cts_n` | input | NUM_UART | 0x1 | required | `nvu_prim_rst_b` | async | NA | rise_edge | UART Clear To Send |
| `nvu_uart_sin` | input | NUM_UART | 0x1 | required | `nvu_prim_rst_b` | async | NA | rise_edge | UART Serial Input |

---

#### VISA Debug Interface (§4.3.6.1)

**VISA Signal Table**

| Signal Name | Direction | Width | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Power Domain | Description |
|---|---|---|---|---|---|---|---|---|---|
| `nvu_avisa_clk` | output | 1 | required | `nvu_fdfx_powergood` | async | NA | NA | VNN | Agent VISA Debug bus clock |
| `nvu_avisa_dbgbus` | output | 32 | required | `nvu_fdfx_powergood` | async | NA | NA | VNN | Agent VISA Debug bus |
| `nvu_fvisa_serdata` | input | 1 | required | `nvu_fdfx_powergood` | sync | `nvu_fvisa_serstrb` | rise_edge | VNN | Fabric Serial Data |
| `nvu_fvisa_serstrb` | input | 9 | required | `nvu_fdfx_powergood` | sync | `nvu_fvisa_serstrb` | rise_edge | VNN | Fabric Serial Strobe |

---

#### DFT Scan Interface (§4.3.13.1)

**Scan Signal Table**

| Reference Name | Instantiated Signal Name | Direction | Dimension | Required? | Sync/Async | Description |
|---|---|---|---|---|---|---|
| `FSCAN_SDI` | `nvu_fscan_sdi` | input | SCAN_DATA_WIDTH | optional | sync | Fabric Scan Data In — scan data inputs for all serially-stitched scan flops/latches |

---

#### Strap Interface (§4.3.1)

**Strap Signal Table**

| Signal Name | Direction | Width | Required? | Description |
|---|---|---|---|---|
| `nvu_br_strap_mulfndev` | input | 1 | required | IOSF2AXI BR Multi Function Device — refer SOC PSF HAS |
| `nvu_br_strap_cpl_mdestid` | input | 52 | required | IOSF2AXI BR Completion Dest ID per RS — refer SOC PSF HAS |

---

#### Camera Control Interface Sharing — I2C/I3C/GPIO (§8.1.2, §8.7.2.1.7.2)

##### I2C/I3C Sharing Between NVU and IPU

- The I2C/I3C interface of the camera must be available to both NVU and IPU based on current ownership (§8.7.2.1.7.2)
- IPU accesses the camera via any of the **LPSS 6×I2C / 4×I3C** controllers through driver-to-driver communication between the IP SW driver and the LPSS I2C subsystem (§8.7.2.1.7.2)
- For **TTL-H** platforms, to enable NVU-based lower-power vision sensing, the MIPI UF RGB camera sensor shall be connected to **LPSS I2C0/I2C1/I3C0**, which is multiplexed with **NVU I2C0/I2C1/I3C** (§8.1.2)
- During runtime operation (post-NVU FW loading), if NVU FW hangs when `release_irq` is asserted, NVU BUP shall — during exception reset — check the current I2C/I3C ownership and **release it if still held by NVU** (§8.1.2)

##### GPIO Allocation for Camera Control

- Up to **8 GPIOs** may be allocated as ad-hoc functional output pins for sensor reset, power control, and similar functions (§8.1.2)
- There is **no hardware multiplexer** for GPIO between NVU and LPSS; these pins operate independently (§8.1.2)
- In the platform, **16 virtual GPIOs** are allocated to establish a **4-way handshake** interface between the IPU sensor driver and NVU (§8.21.5)
- BIOS shall place GPIO pads into the **Host Group** and **lock down pad configuration**; I2C/I3C pins are configured to **Grp4** with default pad mode set to LPSS/IPU (§5.1.1.1)

---

#### VPX2 Memory Map — Selected Regions (§8.2.2)

| Region | Block | Sub-Region | Size (KB) | Start Address | End Address |
|---|---|---|---|---|---|
| BROM | BROM | — | 16 | `0x00000000` | `0x00004000` |
| AONRF | AONRF | — | 16 | `0x01000000` | `0x01004000` |
| SRAMSS_VMEMP | SRAMSS | VMEMP | — | — | — |


### Power States (1 facts)

No power state fuse details are available in the current source facts for this section.


### Register Details (1 facts)

#### Security Registers (SEC_REG)

**Behavioral Description**

- Security registers must not be reset or lose state during NVU power-flows (IPAPG). (2.5.1.13)


### SRAM and Memory (17 facts)

#### SRAM and Memory

#### SRAM Usage Modes

The NVU SRAM supports two distinct addressing modes (§2.5.1.7.1 SRAM Usage):

- **Physically Addressable Memory:** To use SRAM as physically addressed memory, the `PMEM` range of the address map must be used.
- **Page-able Memory:** To use SRAM as page-able memory, the page-able address range (`VMEMP`) in the memory map must be used. Pages are mapped at **4 KB granularity** (configurable).

---

#### SMMU Capabilities

The NVU SMMU provides virtual-to-physical address translation for SRAM access (§2.5.1.7.3 SMMU Capabilities):

- Supports mapping and translation of virtual address space (IMR) to physical address space (SRAM).
- Mapping is supported at the granularity of page size; typical page size is configurable.
- Mapping is usually virtual-to-physical of the same memory region.
- It is the responsibility of firmware to program SMMU mappings. **HW does not perform any default mapping.**

---

#### AONRF / BROM Controller

(§2.5.1.8.1 Capabilities)

- Highly scalable, light-weight RF controller module.
- Supports OCP target interface to the NVU Fabric.
- Interfaces to non-ECC memory and memory that is either read-only or supports write strobes.

---

#### Firmware and SRAM Boot

(§6.1 NVU Firmware Architecture)

- Bring-UP (BUP) firmware is stored in the platform IFWI.
- It is loaded and authenticated by the ESE before BUP is placed into NVU SRAM and begins execution.

---

#### SRAM Scrub Fuse Control

The following fuse controls SRAM scrubbing behavior (§19.1 Fuses):

| Name | Fuse Count | Bit Position | Strap Register | Reset Signal | Default |
|---|---|---|---|---|---|
| `NVU_SRAM_SCRUB_BY_FW` | 1 | STRAP1[28] | SoftStrap | `side_rst_b` | `0x0` |

- **STRAP1[28]** — `SRAM_SCRUB_BY_FW_disable`: Key-value pair default is `0x0`.
- **Note:** The fuses `NVU_SRAM_SCRUB_BY_FW` and `NVU_HASH_BY_FW` are listed under `NVU_Spare_SS4` and are not present in the main fuse table. (§19.1 Fuses)

---

#### ECC Error Reporting — NOC Bridge Fields

The following register fields are associated with ECC correctable error reporting on the NVU PTN NOC bridge. All fields are currently **disabled** (§NOC_VISION_FABRIC registers):

| Field | Register | Bit | Reset | Access | Description |
|---|---|---|---|---|---|
| `B2H_TP_RAS_ECC_CORR_ERR` | `bridge_nvu_ptn_2_10_noc_tx_error_inject_value` | [17] | 0x0 | NA | Disabled register field |
| `B2H_TP_RAS_ECC_CORR_ERR` | `bridge_nvu_ptn_2_10_noc_tx_error_status_value` | [17] | 0x0 | NA | Disabled register field |
| `B2H_TP_RAS_ECC_CORR_ERR` | `bridge_nvu_ptn_2_10_noc_tx_error_status_strg_value` | [17] | 0x0 | NA | Disabled register field |


### Secure Boot (7 facts)

#### PCICFGCTR1 Register — BIOS Programming Recipe

The following fields within the `PCICFGCTR1` register (PCR offset `0x200`) must be programmed by BIOS as part of NVU platform initialization. (§7 BIOS Programming Recipe)

| Field Name | Bits | Size | Reg Size | Attribute | Reset Value | Recommended Value |
|------------|------|------|----------|-----------|-------------|-------------------|
| IPIN | [11:8] | 4 | 32 | RW | 0x1 | 0x1 |
| ACPI_IRQ | [19:12] | 8 | 32 | RW | 0x00 | > 23 |
| DIS_MSI_CAP | [29:29] | 1 | 32 | RW | 0x0 | 0x0 |

- **Register Space:** PCR
- **Offset:** 0x200
- **Register Name:** PCICFGCTR1

---

#### NVU Secure Boot Fuse — NVU_HASH_BY_FW

The `NVU_HASH_BY_FW` soft strap controls whether firmware-based hash validation is enabled or disabled during secure boot. (§19 Fuses > 19.1 Fuses)

| Name | Fuse Count | STRAP Register | Bit Position | Reset Domain | Strap Type | Reset Value |
|------|------------|----------------|--------------|--------------|------------|-------------|
| NVU_HASH_BY_FW | 1 | STRAP1 | [29:29] | side_rst_b | SoftStrap | 0 |

- **Fuse ID:** `16'h0663`
- **Reset Domain:** `side_rst_b`
- **Strap Classification:** SoftStrap (encoding, decoding, and storage all defined as SoftStrap)
- The field `HASH_BY_FW_disable` within `STRAP1[29:29]` encodes the following values: (§19 Fuses > 19.1 Fuses)
  - `0x0` — Hash-by-firmware **enabled** (default)
  - Non-zero — Hash-by-firmware **disabled**
- This fuse is not security-locked by default (`False`) and does not participate in additional lock or override mechanisms as defined in the fuse metadata.


### Sideband Messages (1 facts)

#### Sideband Messages

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.12 SideBand)

- Hammock Harbor, BootPrep, and ResetPrep messages are transmitted over a dedicated pair of avail/get handshake interfaces.


### Straps, Fuses, and Security (153 facts)

### Straps, Fuses, and Security

---

#### NVU Straps, Fuses, and Security

### Overview

This section describes the strap interface signals, fuse configuration, and soft-strap definitions for the Intel NVU (Neural Vision Unit). Requirements are tracked under HAS section [2 Introduction > 2.5 Requirements] and fuse/soft-strap definitions are specified in HAS section [19 Fuses > 19.1 Fuses].

**Applicable Requirements:**
- [HAS 2.5] `id: 16028265561` — **[TTL][NVU] Fuse/Soft-Strap Requirements** (status: POR)
- [HAS 2.5] `id: 16024719766` — **[OSXML][ISH/NVU] Request to add scalability in OSXML to support variable reset value and attribute type for registers dependent on straps** (status: POR)
- [HAS 2.5] `id: 14026563144` — **TTL PCD Fuse Configuration to enable/disable IPs for B/BX and H SKUs** (status: Rejected)

---

#### Strap Interface Signals (HAS 4.3.1)

The NVU Straps interface is a **consumer-side**, **asynchronous** functional interface (version v1.0 r1.0). There is no associated clock (clock name: N/A) and sample/drive edge is **NA**.

| Instantiated Signal Name | Direction | Dimension | Required? | Description |
|---|---|---|---|---|
| `nvu_ip_trusted_sai_strap` | input | 8 | required | NVU SAI (Security Attribute of Initiator) strap |
| `nvu_dtf_channel_id` | input | 8 | required | DTF Channel ID — refer to SOC Debug HAS |
| `nvu_dtf_master_id` | input | 8 | required | DTF Master ID — refer to SOC Debug HAS |

**Strap Interface Properties:**

| Property | Value |
|---|---|
| Interface Type | function |
| Interface Side | Consumer |
| Reset Domain | (see IP configuration) |
| Sync/Async | async |
| Sample/Drive Edge | NA |
| Version | v1.0 r1.0 |

**Notes on `nvu_ip_trusted_sai_strap` Dimension:**
- The dimension of `8` should be a 2D array with each index of 8 bits as per RTL (`NUM_PCI_FUNCTIONS = 2`).
- `NUM_PCI_FUNCTIONS` is **1** from the NVU SOC perspective.
- The second strap index must be internally tied off and **not** exposed to the SOC. (HAS 4.3.1)

---

#### Fuse Definitions (HAS 19.1)

Fuse memory base address: `16'h0650`. All fuses listed below use reset type `side_rst_b`, array type `DirectFuse`, category `IntelHVM`, and group `HighDensity`.

| Fuse Name | RcvrAddr | StartBit | MiscStartBit | Width | Default Value | Reset Type | Array Type | Category | Zeroization | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `NVU_HVM_MODE_Fuse` | `16'h0650` | 1 | 1 | 1 | `0` | `side_rst_b` | `DirectFuse` | `IntelHVM` | False | Feature: Security IP Hardware. Causes ROM to halt NVU CPU. |
| `NVU_Secure_Load_Fuse` | `16'h0650` | 2 | 2 | 1 | `1` | `side_rst_b` | `DirectFuse` | `IntelHVM` | False | Feature: Security IP Hardware (ROM). See boot method for details. |
| `NVU_Debug_Mode_Fuse` | `16'h0650` | 3 | 3 | 1 | `0` | `side_rst_b` | `DirectFuse` | `IntelHVM` | False | Feature: Security IP Hardware (ROM). See boot method for details. |

**Common Fuse Attributes:**
- **BlkOnDbg:** False
- **VFOverrideDisable:** False
- **LockoutValidIDTag:** False
- **IPOwner:** `alokanan`
- **RTLSignalPath:** `oob_fuse[0:0]`
- **Consumer:** IP Hardware
- **EncodingValueType / EncodingValues:** per individual fuse definition
- **SubClass:** per individual fuse definition

---

#### Soft-Strap Definitions (HAS 19.1)

Soft-straps use array type `SoftStrap`, category `SoftStrap`, reset type `side_rst_b`. The `NVU_Debug_Mode_softstrap` is a separate Functional IP software-controlled override.

| Soft-Strap Name | RcvrAddr | StartBit | Width | Default Value | Reset Type | Array Type | Description |
|---|---|---|---|---|---|---|---|
| `NVU_Debug_Mode_softstrap` | `16'h0662` | 4 (bit 148 absolute, bit 20 in word) | 1 | `0` | `side_rst_b` | `SoftStrap` | Feature: Functional IP Hardware. See boot method for details. |

---

#### Soft-Strap Register Map (HAS 19.1)

The NVU soft-strap space consists of four 32-bit registers (STRAP0–STRAP3).

**STRAP0 (`16'h0662` word 0)**

| Bits | Key | Default | Description |
|---|---|---|---|
| `STRAP0[7:0]` | `PCI_func1_Interface` | `0x0` | Indicates PCI Function 1 Interface type |
| `STRAP0[15:8]` | `PCI_func1_Sub_Class` | `0x0` | Defines PCI Function 1 Sub-Class |
| `STRAP0[23:16]` | `PCI_func1_Base_Class` | `0x0` | Defines PCI Function 1 Base-Class |
| `STRAP0[31:24]` | `spare_default` | `0x0` | Spare Softstraps |

**STRAP1**

| Bits | Key / Encoding | Default | Description |
|---|---|---|---|
| `STRAP1[15:0]` | `spare_default` | `0x0` | Spare Softstraps |
| `STRAP1[16:16]` | `spare_default` | `0x0` | Spare bit in NVU |
| `STRAP1[18:17]` | `PLATFORM_SKU` | `0x0` | Indicates platform SKU |
| `STRAP1[19:19]` | `Non-Secure_Load_Mode=0x0`; `Secure_Load_Mode` | `0x0` | Secure/Non-Secure Load Mode select |
| `STRAP1[20:20]` | `Non-Debug_Mode=0x0`; `Debug_Mode` | `0x0` | Debug Mode enable |
| `STRAP1[24:24]` | `HW_autoack_enable=0x0`; `HW_autoack_disable` | `0x0` | HW Auto-Acknowledge control |
| `STRAP1[25:25]` | `spare_default` | `0x0` | Spare Softstraps |
| `STRAP1[27:27]` | `WAIT_FW_LOAD_VISION_SERVICE_disable` | `0x0` | Wait for FW Load Vision Service control |
| `STRAP1[30:30]` | `ROM_WAIT_D3_enable=0x1`; `ROM_WAIT_D3_disable` | `0x1` | ROM Wait D3 enable/disable |
| `STRAP1[31:31]` | `spare_default` | `0x0` | Spare SoftStraps |

**STRAP2**

| Bits | Key | Default | Description |
|---|---|---|---|
| `STRAP2[31:0]` | `spare_default` | `0x0` | Spare SoftStraps |

**STRAP3**

| Bits | Key | Default | Description |
|---|---|---|---|
| `STRAP3[31:0]` | `spare_default` | `0x0` | Spare SoftStraps |

---

#### Fuse Word Spare Bits (HAS 19.1)

| Bits | Key | Default | Description |
|---|---|---|---|
| `FUSE0[31:16]` | `spare_default` | `0x0` | Spare Fuses |

---

#### Behavioral Notes

- **HVM Mode Fuse (`NVU_HVM_MODE_Fuse`):** When blown, causes the ROM to halt the NVU CPU. This fuse is associated with the Security IP Hardware feature. (HAS 19.1)
- **Secure Load Fuse (`NVU_Secure_Load_Fuse`):** Controls secure boot load method. See boot method documentation for full details. Default reset value is `1`. (HAS 19.1)
- **Debug Mode Fuse (`NVU_Debug_Mode_Fuse`):** Controls debug mode at the hardware fuse level. Default is non-debug (`0`). See boot method documentation for details. (HAS 19.1)
- **Debug Mode Soft-Strap (`NVU_Debug_Mode_softstrap`):** Provides a software-controlled functional override for debug mode. (HAS 19.1)
- **Platform SKU (`STRAP1[18:17]`):** Two-bit field used to indicate the platform SKU configuration. (HAS 19.1)
- **ROM Wait D3 (`STRAP1[30:30]`):** Default value is `0x1` (enabled), meaning ROM waits on D3 by default; this is the only non-zero default in the soft-strap space. (HAS 19.1)
- All straps are asynchronous inputs with no associated sampling clock. (HAS 4.3.1)
- The OSXML flow must support variable reset values and attribute types for registers that depend on straps. (HAS 2.5, `id: 16024719766`)


### USB Camera Interface (6 facts)

#### USB Camera Interface Overview

The NVU USB Camera Interface integrates an xHCI-based camera subsystem into the NVU SoC fabric. Primary integration reference is the TTL xHCI CAM SOC Integration specification (HAS §4 Reference Documents, Index 34).

---

#### PCI Function Mapping

- NVU exposes **2 PCI functions** to the host software stack (HAS §7.3)
- The **NVU Host SW Driver** is mapped to **FN0** of the IOSF2AXI Bridge (BR)
  - FN0 exposes a **64 KB BAR**
  - This BAR is remapped at the IOSF2AXI BR to address range **0x8000_0000** (HAS §7.3)

---

#### Strap Interface

Strap interface details for xHCI camera configuration should be referenced from the SoC PSF HAS documentation.

---

#### Fuse Configuration

The following fuses govern USB camera interface behavior and softstrap control (HAS §18.1, §19.1):

| Fuse Name | Width | Address | Reset | Reset Domain | Fuse Type | Access | Description |
|---|---|---|---|---|---|---|---|
| `NVU_Softstrap_select_disable` | 1 | `16'h0650` | 0 | `side_rst_b` | DirectFuse | IntelHVM / HighDensity | Disables softstrap selection; see boot method for details (HAS §18.1, §19.1) |
| `NVU_VSI9000NanoD_enable` | 1 | `16'h0650` | 0 | `side_rst_b` | DirectFuse | IntelHVM / HighDensity | Enables VSI9000NanoD camera device support (HAS §19.1) |

- `NVU_Softstrap_select_disable` is classified as a **Security** feature (IP: Hardware/ROM)
- `NVU_Softstrap_select_disable` fusability is `False` with default value `0`; ROM override is listed as `NA`
- ROM override is listed as **NA** for both entries


### Voltage Domains (4 facts)

#### Power Domain Overview

The Intel NVU operates under a defined power domain architecture as specified in the IP Configuration interfaces section.

---

#### Straps Interface — Power Domain Assignment

(HAS 4 IP Configuration > 4.3 Interfaces > 4.3.1 Straps)

| Name | Straps |
|------|--------|
| Power Domain | — |

- The NVU power domain assignment via the straps interface is not specified in the provided source facts.

---

#### Resets Interface — Power Domain Reset Mapping

(HAS 4 IP Configuration > 4.3 Interfaces > 4.3.3 Resets)

| Name | PGCB Reset |
|------|------------|
| Power Domain | — |

- The NVU power domain association with the PGCB Reset signal voltage rail is not specified in the provided source facts.

---

#### VISA Debug Interface — Power Domain Association

(HAS 4 IP Configuration > 4.3 Interfaces > 4.3.6 Debug > 4.3.6.1 VISA)

| Name | Direction | Dimension | Required? | Reset Domain | Sync/Async | Clock Name | Sample/Drive Edge | Power Domain |
|------|-----------|-----------|-----------|--------------|------------|------------|-------------------|--------------|
| Instantiated Signal Name | — | — | — | — | — | — | — | — |

- VISA debug signals include a **Power Domain** attribute field, associating each instantiated signal with its corresponding voltage domain.
- The VISA signal table captures per-signal metadata including reset domain, synchronization type, clock source, and power domain affiliation.

