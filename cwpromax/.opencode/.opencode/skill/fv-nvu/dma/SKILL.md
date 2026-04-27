name: fv-nvu/dma
description: NVU DMA architecture, DesignWare AXI DMA controller, channel configuration, DMA MISC logic, peripheral handshake, and transaction flows

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# NVU DMA Controller

> **SAFETY**: Do NOT trigger DMA transfers or modify DMA channel configuration without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html).
> Any detail marked `TBD` has not been verified or is not present in the current HAS revision.

## Overview

The NVU contains multiple DMA engines serving distinct purposes:

- **Boot/IO DMA (BootDMA)** — The primary general-purpose DMA controller (Synopsys DW_axi_dmac, version 2.00a) with 8 channels, used for boot image transfers and peripheral I/O data movement. This is the main subject of HAS Section 8.11.
- **SRAM-SS Paging DMA** — Located within the SRAM subsystem for paging data between DRAM (IMR) and SRAM via SMMU (up to 3.2 GB/s).
- **SIO DMA (SIODMA)** — A separate 4-channel DW_axi_dmac instance within the UVOL (USB offload) logic for SIO FIFO ↔ SRAM data streaming (up to 1.6 GB/s). **Note:** 4 channels instantiated; channel mapping assigns CH1–CH4 to defined transfers per HAS section 8.8.2.1.2.4.5.
- **NPX6 iDMA/oDMA STU** — NPX6 L1 Streaming Transfer Units for data transfers between L1 memories (VM/AM) and SRAM (up to 3.2 GB/s). These are internal to the NPX6-1K NNA.
- **VPX2 STU** — VPX2 Streaming Transfer Unit for VCCM ↔ SRAM DMA (up to 3.2 GB/s). Internal to the VPX2 DSP.


## Boot/IO DMA Controller (Section 8.11)

### Architecture

The NVU instantiates a single Synopsys DW_axi_dmac (SNPS DW_AXI_DMAC) DMA Controller with 4 channels for boot/IO operations. Note: NVU has additional DMA engines — one within the SRAM-SS for paging and one within the USB offload logic for data streaming to DRAM. Per the HAS:

- **IP**: Synopsys AXI DMA (DW_AXI_DMAC)
- **Purpose**:
  - **Boot Service** — Copy boot image from RS0 (Host DRAM) to RS3 (IMR DRAM) and from RS3 to SRAM
  - **IO Service** — Data movement from/to peripherals to SRAM
- **Interface**: Single AXI4 initiator interface for data transfers, with register programming interface
- **Interrupt**: Combined single interrupt

### Register Addresses

Per the NVU memory map:

| Register Block | Size (KB) | Start Address | End Address |
|----------------|-----------|---------------|-------------|
| DMA | 4 | `0xF3800000` | `0xF3801000` |
| DMA_MISC | 4 | `0xF3900000` | `0xF3901000` |

### Fabric Connectivity

Per HAS Section 8.10.3 (Initiators):

| Initiator | Init ID | Protocol | Target Group Access | Clock (MHz) | Data Width (B) | Burst Size (B) | Max BW (GB/s) | Outstanding |
|-----------|---------|----------|---------------------|-------------|----------------|-----------------|---------------|-------------|
| DMA_INIT | 0x0 | AXI | EXT_RD, EXT_WR, PMEM0, PVT_MEM, IO | 200 | 8 | 64 | 1.6 | 32 |
| IOSF2AXI | 0x1 | AXI | HOST, STRM, DUAL | 200 | 16 | 64 | 3.2 | 4 |
| ISP | 0x2 | AXI | VMEM1, PMEM1 | 200 | 8 | 64 | 1.6 | 4 |
| MJPEG | 0x3 | AXI | VMEM1, PMEM1 | 200 | 8 | 64 | 1.6 | 4 |
| NPX | 0x4 | AXI | VMEM1, PMEM1, ARCSYNC | 400 | 16 | 256 | 6.4 | 4 |
| SRAM_SS | 0x5 | AXI | EXT_RD, EXT_WR | 400 | 16 | 256 | 6.4 | 32 |
| UVOL | 0x6 | AXI | PMEM1 | 200 | 16 | 64 | 3.2 | 4 |
| VPX_CBU | 0x8 | AXI | VMEM0, PMEM0, PVT_MEM | 400 | 16 | 256 | 6.4 | 4 |
| VPX_STU | 0x9 | AXI | VMEM0, PMEM0, PVT_MEM | 400 | 16 | 256 | 6.4 | 4 |
| VPX_LBU | 0xA | AXI | IO, REGS, DUAL, ARCSYNC | 400 | 16 | 256 | 6.4 | 4 |

> **NOC initiator ID 0x7 is reserved/unused.** Only IOSF2AXI has access to HOST target group; only VPX_LBU has access to REGS target group; both DMA_INIT and VPX_LBU have access to IO target group.

Per HAS Section 8.10.2 (Targets):

| Target | Protocol | Target Group | Clock (MHz) | Data Width (B) | Max BW (GB/s) | Pending Trans |
|--------|----------|--------------|-------------|----------------|---------------|---------------|
| DMA_REG | AHB | REGS | 200 | 4 | 0.8 | 4 |
| DMA_MISC_REG | AHB | REGS | 200 | 4 | 0.8 | 4 |

### NOC Address Hole Behavior (HAS Section 8.10)

The Arteris FlexNoC (v5.4) fabric operates at 200/100 MHz and routes transactions based on address decoding:

- **In-range unmapped address**: Transaction completes with OKAY response (no error), writes are dropped, and reads return Zero. This can occur when accessing a valid address range that has no target mapped.
- **Out-of-range address**: Transaction completes with ERROR/UR (Unsupported Request) response. The fabric signals an error to the initiator.
- **~40 target endpoints** connected across 13 target groups: EXT_RD, EXT_WR, PMEM0, PMEM1, REGS, PVT_MEM, IO, DUAL, ARCSYNC, VMEM0, VMEM1, STRM, HOST.

> **Validation note**: When testing DMA to unmapped addresses within the NVU address space, expect OKAY with reads returning Zero and writes dropped — NOT an error. Only addresses completely outside the fabric's decode window generate errors.


## DMA Configuration (Section 8.11.1)

### Global Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| DMAX_ID_NUM | 0x0 | DMA ID |
| DMAX_NUM_CHANNELS | 8 | 8 DMA Channels |
| DMAX_NUM_HS_IF | 26 | 26 hardware handshake interfaces for NVU peripherals |
| DMAX_INTR_IO_TYPE | 0 | Combined single interrupt only |
| DMAX_SLVIF_STATUS_OP_EN | 1 | Target interface status indication |
| DMAX_CORE_STATUS_OP_EN | 1 | Busy/Idle indication from DMA to PM blocks |
| DMAX_HOLD_IO_EN | 0 | No support for DMA hold request feature |
| DMAX_UNALIGNED_XFER_EN | 1 | Support unaligned address on SAR and DAR |
| DMAX_CH_ABORT_EN | 1 | Support for DMA channel abort |
| DMAX_ENABLE_LAST_WRITE | 1 | Enable DMA last data phase indication (for PM logic) |
| DMAX_CH_MEM_EXT | 1 | Use external RF for FIFO memory |
| DMAX_CH_MEM_REGOUT | 0 | No flop on FIFO memory output |
| DMAX_DEBUG_PORTS_EN | 1 | Debug ports for VISA observability |
| DMAX_MSTIF_MODE | 1 | AXI4 initiator interface |
| DMAX_NUM_MASTER_IF | 1 | Single AXI4 initiator interface (HAS Section 8.11) |
| DMAX_MSTIF_OSR_LMT | 16 | 16 outstanding bursts |
| DMAX_STATIC_ENDIAN_SELECT_MSTIF | 1 | Static endian (Little Endian) |
| DMAX_ENDIAN_FORMAT_MSTIF | 0 | Little Endian |
| DMAX_M_ADDR_WIDTH | 64 | 64-bit address |
| DMAX_M_DATA_WIDTH | 64 | 64-bit data |
| DMAX_M_ID_WIDTH | 4 | [3] indicates LLI/Non-LLI, [2:0] indicates CH# |
| DMAX_M_BURSTLEN_WIDTH | 8 | Burst Length |
| DMAX_SLVIF_MODE | 0 | AHB target for register access |
| DMAX_S_DATA_WIDTH | 32 | 32-bit target interface |
| DMAX_SLVIF_CLOCK_MODE | 0 | Target interface synchronous to DMA core clock |
| DMAX_INTR_SYNC2SLVCLK | 0 | Interrupt output synchronous to DMA core clock |
| DMAX_SAFETY_FEATURE_EN | 0 | No safety features enabled |
| DMAX_HAS_QOS | 0 | No QoS signals on AXI4 |
| DMAX_LLI_ENDIAN_SELECTION_PIN_EN | 0 | LLI access same endianness as data access |
| DMAX_ASYNC_HS_EN | 0 | Async handshake enabled for all interfaces |
| DMAX_HS_SAME_ASYNC_CLK | 0 | Not all DMA HW HS signals in same clock domain |

### Context-Sensitive Low Power (CSLP)

| Parameter | Value | Description |
|-----------|-------|-------------|
| DMAX_CSLP_EN | 1 | Context Sensitive Low Power enabled for dynamic clock gating |
| DMAX_CHNL_CSLP_EN | 1 | CSLP on DMA channel |
| DMAX_SBIU_CSLP_EN | 1 | CSLP on target interface |
| DMAX_MXIF_CSLP_EN | 1 | CSLP on initiator interface |
| DMAX_GLCH_LPDLY_WIDTH | 4 | Max 16 clock hysteresis |
| DMAX_SBIU_LPDLY_WIDTH | 4 | Max 16 clock hysteresis |
| DMAX_MXIF_LPDLY_WIDTH | 4 | Max 16 clock hysteresis |
| DMAX_GLCH_LPDLY | 15 | Default hysteresis counter value |
| DMAX_SBIU_LPDLY | 15 | Default hysteresis counter value |
| DMAX_MXIF_LPDLY | 15 | Default hysteresis counter value |


## Channel Configuration (Section 8.11.1)

### Channel Capabilities Summary

The DMA configuration is **intentionally asymmetric** across channels to optimize gate count/area:

| Channel | FIFO Depth | Max Block TS | Multi-Block | LLI Prefetch | Shadow Regs | SRC/DST Stat | LLI WB | Purpose |
|---------|-----------|-------------|-------------|-------------|-------------|-------------|--------|---------|
| CH1 | 4×16B | 4095 | Yes (all types) | Yes | Yes | Yes | Yes | High-BW MEM↔MEM |
| CH2 | 128×8B | 4095 | Yes (all types) | Yes | Yes | Yes | Yes | High-BW MEM↔MEM |
| CH3 | 16×8B | 4095 | Yes (all types) | Yes | Yes | Yes | Yes | Medium-BW IO |
| CH4 | 4×8B | 4095 | No | No | No | No | No | Slow-speed IO |
| CH5 | 4×8B | 4095 | No | No | No | No | No | Slow-speed IO |
| CH6 | 4×8B | 4095 | No | No | No | No | No | Slow-speed IO |
| CH7 | 4×8B | 4095 | No | No | No | No | No | Slow-speed IO |
| CH8 | 4×8B | 4095 | No | No | No | No | No | Slow-speed IO |

### Configuration Notes

- CH1 and CH2 are optimized for **high performance/high bandwidth** and intended for MEM↔MEM transfers
- CH3 is **medium performance** and intended for high-bandwidth IO transfers
- **LLI (Multi-Block) transfer mode** is enabled only on CH1–CH3
- CH4–CH8 are optimized for **slow-speed IO** transfers
- All channels share: `DMAX_CH(x)_MAX_AMBA_BURST_LENGTH = 8`, `DMAX_CH(x)_MAX_MSIZE = 8`, `DMAX_CH(x)_TT_FC = 0x8` (no hardcoded TTFC), `DMAX_CH(x)_SMS/DMS = 0x0` (single initiator), `DMAX_CH(x)_STW/DTW = 0x0` (no hardcoded TR width), `DMAX_CH(x)_LOCK_EN = 1` (channel locking enabled)


## DMA Capabilities Matrix

Per HAS Section 2.5.1.10:

| SRC \ DST | PER (Direct) | PER (LLI) | PER (HW HS) | SRAM (Direct) | SRAM (LLI) | SRAM (HW HS) | DRAM:RS0 (Direct) | DRAM:RS0 (LLI) | DRAM:RS0 (HW HS) | DRAM:RS3 (Direct) | DRAM:RS3 (LLI) | DRAM:RS3 (HW HS) |
|-----------|---|---|---|---|---|---|---|---|---|---|---|---|
| **PER** | N | N | N | Y | Y | Y | Y | Y | Y | N | N | N |
| **SRAM** | Y | Y | Y | Y | Y | N | Y | Y | N | Y | Y | N |
| **DRAM:RS0** | Y | Y | Y | Y | Y | N | Y | Y | N | Y | Y | N |
| **DRAM:RS3** | N | N | N | Y | Y | N | Y | Y | N | Y | Y | N |

> **Note**: When SRC or DST are in DRAM:RS3 and LLI mode is enabled, LLI descriptors must be in SRAM (`LLI_MODE = 0`).

### Unsupported Features

Per the HAS, the following SNPS AXI DMA features are **not supported** on NVU:

- Peripheral as flow controller (DMA is always the flow controller — block size is always known before transfer begins)
- Software handshaking
- DMA hold functionality


## DMA MISC Logic (Section 8.11.2)

The DMA MISC block manages auxiliary DMA functionality including root-space selection, snoop attributes, and internal/external memory routing.

### DMA Channel Control Register (DMA_MISC)

| Bits | Access | Default | Field | Description |
|------|--------|---------|-------|-------------|
| 1:0 | RW | 0 | TRANSFER_MODE | `0`: Src Internal, Dst Internal; `1`: Src Internal, Dst External; `2`: Src External, Dst Internal; `3`: Src External, Dst External |
| 2 | RO | 0 | Reserved | — |
| 4:3 | RW | 0 | RD_RS | Read Root-Space: `0` = RS0 (Host DRAM), `3` = RS3 (IMR DRAM). Other values blocked by HW. |
| 6:5 | RW | 0 | WR_RS | Write Root-Space: `0` = RS0 (Host DRAM), `3` = RS3 (IMR DRAM). Other values blocked by HW. |
| 7 | RO | 0 | Reserved | — |
| 8 | RWO | 0 | RD_NON_SNOOP | `0`: Read transactions snooped in IA cache; `1`: Not snooped |
| 9 | RW | 0 | WR_NON_SNOOP | `0`: Write transactions snooped in IA cache; `1`: Not snooped |
| 10 | RW | 0 | LLI_MODE | `0`: Descriptors in internal memory; `1`: Descriptors in external memory (DRAM) |
| 31:11 | RO | 0 | Reserved | — |

> **Note**: The DMA_MISC register offset within the DMA_MISC block is listed as TBD in the HAS. The DMA_MISC register block base address is not specified in the HAS.

### DMA MISC Address Routing Logic (from HAS Block Diagram)

The DMA MISC block contains per-channel address routing and attribute injection logic between the Boot/IO DMA AXI master interface and the NOC fabric:

#### Address Construction

The DMA MISC extends the 62-bit DMA address to a 64-bit fabric address:

```
AxADDR[63:0] = { AxUSER[1:0], AxADDR[61:0] }
```

Where:
- `AxADDR[61:0]` — 62-bit address from the DW_axi_dmac channel (SAR/DAR)
- `AxUSER[1:0]` — Root-space selector from DMA_CTL_CH[n].RD_RS or WR_RS, mapped to address bits [63:62]

#### RS0Disable Logic (External Access Routing)

When the DMA targets external memory (TRANSFER_MODE indicates external source or destination), the DMA MISC routes transactions based on `AxADDR[63]`:

```
if AxADDR[63] == 1:
    Route → IOSF2AXI bridge → Host/IMR DRAM (external)
else:
    Route → LLIM (Local Locked IMR Memory, internal fabric path)
```

This routing is enforced by the RS0DisableLogic block, which implements the security lockout: if RS0_DISABLE is set and TM[1:0] != 0x0 with (RD_RS || WR_RS) == 0x0, the DMA_MISC forces AxADDR[63] to 0, blocking the transaction from reaching external memory.

#### Per-Channel DMA Control (DMA_CTL_CH[0..7])

Each DMA channel has a corresponding DMA_CTL register in the DMA_MISC block that controls:

| Field | Bits | Description |
|-------|------|-------------|
| TRANSFER_MODE | 1:0 | Transfer Mode: Bit 1 controls Source Memory/Peripheral location relative to NVU, Bit 0 controls Destination |
| RD_RS | 4:3 | Read Root-Space selector → drives AxUSER[1:0] for read address bits [63:62] |
| WR_RS | 6:5 | Write Root-Space selector → drives AxUSER[1:0] for write address bits [63:62] |
| RD_NON_SNOOP | 8 | Read snoop attribute (0=snooped, 1=non-snooped). Access: RWO (read-write-once) |
| WR_NON_SNOOP | 9 | Write snoop attribute |
| LLI_MODE | 10 | LLI descriptor location (0=SRAM, 1=DRAM) |

The Channel Mux selects the appropriate DMA_CTL_CH[n] register based on the active channel's `ARID[2:0]` / `AWID[2:0]` (channel number encoded in AXI ID bits [2:0]).

#### AXI ID Encoding (DMA → NOC)

| AXI ID Bit | Meaning |
|------------|---------|
| `ARID[3]` / `AWID[3]` | `1` = LLI descriptor fetch, `0` = normal data transfer |
| `ARID[2:0]` / `AWID[2:0]` | Channel number (0–7), used by DMA_CTL Channel Mux |

> **Source**: HAS Block Diagram — DMA MISC logic (DMA.vsdx_DMA_MISC)


### RS0/RS3 Security Restrictions

Per the HAS Security section:

- ROM/BUP will **disable RS0 capability** on the DMA once boot is complete
- ROM/BUP will **disable RS3_WR capability** on the DMA once boot is complete

Per HAS Section 8.10.4.1:

| Initiator | Target | RS0_DISABLE | RS3_WR_DISABLE |
|-----------|--------|-------------|----------------|
| DMA_INIT | EXT_WR | `0`: RS0 WR allowed; `1`: RS0 WR blocked | `0`: RS3 WR allowed; `1`: RS3 WR blocked |
| DMA_INIT | EXT_RD | `0`: RS0 RD allowed; `1`: RS0 RD blocked | X: RS3 RD always allowed |


## Peripheral Handshake Assignment (Section 8.11.3)

The DMA supports up to 64 hardware handshake interfaces; the Boot DMA is configured for 26 HW HS interfaces. Below is a sample peripheral handshake assignment:

| HW HS Interface # | Peripheral |
|--------------------|------------|
| 0 | I2C0 Rx |
| 1 | I2C0 Tx |
| 2 | I2C1 Rx |
| 3 | I2C1 Tx |
| 4 | I2C2 Rx |
| 5 | I2C2 Tx |
| 6 | UART0 Rx |
| 7 | UART0 Tx |
| 8 | UART1 Rx |
| 9 | UART1 Tx |
| 10 | UART2 Rx |
| 11 | UART2 Tx |
| 12 | SPI0 Rx |
| 13 | SPI0 Tx |
| 14 | SPI1 Rx |
| 15 | SPI1 Tx |
| 16 | I3C0 Rx |
| 17 | I3C0 Tx |
| 18 | I3C0 CmdQ |
| 19 | I3C0 RespQ |
| 20 | I3C0 IBIQ |
| 21 | I3C1 Rx |
| 22 | I3C1 Tx |
| 23 | I3C1 CmdQ |
| 24 | I3C1 RespQ |
| 25 | I3C1 IBIQ |

### TR Widths for Peripheral Transfers (Section 8.11.4)

| Peripheral | TR Width (bits) | Comments |
|------------|-----------------|----------|
| I2C Tx | 16 | 8 bits data + upper bits carry control information |
| I2C Rx | 8 | 8 bits of data |
| SPI Tx/Rx | 8/16/32 | Based on SPI controller CTRLR0.DFS_32 field |
| UART Rx/Tx | 8 | 8 bits of data |
| I3C | 32 | I3C supports 32-bit TR width |


## DMA Programming Restrictions (Section 8.11.5)

Per the HAS, the following restrictions apply when programming the BootDMA:

1. **BLOCK_TS** must be > max(SRC_TR_WIDTH, DST_TR_WIDTH)
2. **SRC_STAT_EN/DST_STAT_EN** cannot be used when source/destination is DRAM (RS0 or RS3)
3. **Peripheral FIFO threshold** must match the DMA MSIZE programmed
4. **Aligned transfers required** for peripherals:
   - SAR addresses must align to `CHx_CTL.SRC_TR_WIDTH` (AXI bus arsize)
   - DAR addresses must align to `CHx_CTL.DST_TR_WIDTH` (AXI bus awsize)
5. **UART Rx limitation**: DMA must use `MSIZE = 0` and UART Receiver Trigger (`FCR.RT`) must be `0` to trigger DMA request for every byte received (because UART TR width is 1 byte, and the only FIFO threshold matching combination is 1 byte)


## SIO DMA Controller (Section 8.8.2.1.2.4)

The UVOL (USB offload) logic contains a 4-channel DMA controller based on SNPS DW_axi_dmac (4 instantiated, 3 active — Ch0 unused), for moving data between SIO FIFOs and NVU SRAM.

### Register Address

| Block | Size (KB) | Start Address | End Address |
|-------|-----------|---------------|-------------|
| SIODMA | 4 | `0xF4120000` | `0xF4121000` |

### SIO DMA Channel Assignment

| Channel # | Hardware Handshake | Direction |
|-----------|-------------------|-----------|
| 1 | HAT: hst_tx_dpreq/ack[0], HAB: hst_tx_dpreq/ack[1] | SRAM → SIO |
| 2 | HAR: hst_rx_dpreq/ack[0], HAB: hst_rx_dpreq/ack[1] | SIO → SRAM |
| 3 | fifo_dma_req (from DPKTZR) | DPKTZR → SRAM |

### SIO DMA Channel FIFO Depth

| Ch # | Max Outstanding | Data Width (B) | Burst Size (B) | Burst Len | CH_FIFO_DEPTH |
|------|----------------|----------------|-----------------|-----------|---------------|
| 1 | 4 | 16 | 16 | 1 | 4 |
| 2 | 4 | 16 | 16 | 1 | 4 |
| 3 | 4 | 16 | 128 | 8 | 64 |

### SIO DMA Interrupt

- **SIODMA IRQ**: VPX2 IRQ 101, signal `irq101_a`, vector offset `0x194`


## Transaction Flows (Section 9)

### Ordering Model

All ordering and PCI transaction rules are supported by the IOSF2AXI Block in NVU. The IOSF2AXI Bridge is the ordering crossing point between the PCI-ordered world and the non-PCI-ordered AXI world.

#### Downstream Transaction Ordering (Section 9.2.1.1.1)

| Row Pass Column | Posted | Non-Posted | Completion |
|-----------------|--------|------------|------------|
| **Posted (A)** | No | Yes | Yes |
| **Non-Posted (B)** | No | No | Yes |
| **Completion (C)** | Yes/No (based on RO) | Yes | No |

Key rules:
- IOSF2AXI Bridge **converts all DS Posted writes to DS Non-Posted writes** to ensure PCI ordering (NP-pushes-Posted) is met on the AXI side
- No ordering between DS CPL and DS P writes (no data/consumer in IP & flag in memory model for NVU)
- Separate response queue for Write responses
- No ordering between IOSF Sideband accesses and downstream IOSF transactions
- No ordering between DS Completions of different Virtual Channels

#### Upstream Transaction Ordering (Section 9.2.1.1.2)

| Row Pass Column | Posted | Non-Posted | Completion |
|-----------------|--------|------------|------------|
| **Posted (A)** | No | Yes | Yes |
| **Non-Posted (B)** | Yes | No | Yes |
| **Completion (C)** | Yes/No [1] | Yes | Yes/No [2] |

Notes:
- [1] Special cases where CPL pushes P: Config writes to BME=0, D3=1, MSI_Enable=0, MSIX_Enable=0 (only on IOSF primary, not BAR1 indirect or SB)
- [2] Completion can pass completion if IOSF tags differ; cannot pass if same tag
- DS Write response queue updated only after presenting writes to IOSF interface (ensures CPL push P rule)
- **No NP push Posted requirement within the Bridge** — NVU needs to ensure that there are no issues with the current DMA behavior/usages. IOSF2AXI bridge sends Read and Write transactions independently to the IOSF Master Interface. The onus of ensuring Rd-Wr and Wr-Rd ordering is on the IP below the bridge, i.e. NVU DMA.

### SBEP Message Flows (Section 8.13.6)

Three message flow types are defined for the IOSF-SB endpoint:

1. **Upstream Posted Message Flow** — NVU FW initiates upstream posted messages via SBEP registers (`SB_US_STATUS`, `SB_US_ADDRESS_HI`, `SB_US_ADDRESS_LO`, `SB_US_DATA_OUT`)
2. **Upstream Non-Posted Message Flow** — NVU FW initiates upstream non-posted messages (same register set plus `SB_US_ATTRIBUTES`)
3. **SBEP Downstream Message Flow** — IOSF2AXI bridge receives downstream messages and presents them to NVU SBEP HW (`SB_DS_CONTROL_STATUS`, `SB_DS_REGISTERS`, `MSG_RCVD_IRQ_STATUS`)

### IOSF2AXI Bridge Ordering Notes for DMA

Per the HAS:
- The bridge implements **separate response queues** for Write responses; the onus of Rd-Wr and Wr-Rd ordering is on the NVU DMA
- NVU must ensure no issues with DMA behavior when NP push Posted is not enforced within the bridge


## Bandwidth Summary

Per HAS Section 11.2:

| Initiator | Max Bandwidth | Usage |
|-----------|---------------|-------|
| BootDMA | 1.6 GB/s | D2D (DRAM-to-DRAM), D2S (DRAM-to-SRAM) |
| VPX STU | 3.2 GB/s | VCCM ↔ SRAM |
| NPX iDMA/oDMA | 3.2 GB/s | AM/VM ↔ SRAM |
| SMMU Page-IN | 3.2 GB/s | DRAM → SRAM |
| SIODMA | 1.6 GB/s | DPKTZR → SRAM |
| SIO Component | 1.6 GB/s | Host ISOCH Rx → Device ISOCH Rx |


## VPX2 DMA-Related Interrupts

| IRQ # | Source | Name | Signal | Vector Offset |
|-------|--------|------|--------|---------------|
| 55 | DMA | DMA IRQ | irq55_a | 0xDC |
| 56 | DMA | SPARE0 IRQ | irq56_a | 0xE0 |
| 57 | DMA | SPARE1 IRQ | irq57_a | 0xE4 |
| 58 | DMA | SPARE2 IRQ | irq58_a | 0xE8 |


## Error Handling

| Error | Source | Detection | Recovery |
|-------|--------|-----------|----------|
| DMA Error | Boot/IO DMA fault | VPX2 IRQ 55 (DMA IRQ) | FW error handler, reset DMA |
| DMA Fabric Error | Fabric-level error | VPX2 IRQ 59 (MAIN_FABRIC IRQ) | FW error handler |
| SIODMA Error | SIO DMA fault | VPX2 IRQ 101 (SIODMA IRQ) | FW error handler |
| Address Hole (DMA) | DMA access to unmapped range within IP | OKAY response | Write dropped, Read returns zero |
| Address Hole (DMA) | DMA access outside IP range | ERROR/UR response | Optional IRQ to FW; write dropped, read returns zero |


## Test Scenarios

### Basic Boot DMA MEM→MEM Transfer
1. Configure DMA_MISC: `TRANSFER_MODE=0` (internal→internal), verify default root-space settings
2. Program CH2 (high-BW MEM↔MEM): set SAR to SRAM source, DAR to SRAM destination, BLOCK_TS to test size
3. Set `DMAC_CFGREG.DMAC_EN = 1`, `DMAC_CFGREG.INTEN = 1`
4. Enable CH2, wait for DMA IRQ completion
5. Verify destination data matches source

### Boot DMA RS0→RS3→SRAM Transfer
1. Set DMA_MISC: `TRANSFER_MODE=2` (external source, internal dest), `RD_RS=0` (RS0)
2. Program CH1 for RS0 DRAM → RS3 DRAM transfer (boot image copy)
3. Verify transfer completes, verify data integrity
4. Set `RD_RS=3` (RS3), `TRANSFER_MODE=2` for RS3 → SRAM
5. Program CH1 for RS3 → SRAM transfer
6. Verify transfer completes

### Peripheral DMA Transfer (I2C)
1. Configure I2C0 controller, set FIFO threshold to match DMA MSIZE
2. Program a DMA channel with HW handshake interface for I2C0 Rx
3. Set `CHx_CTL.SRC_TR_WIDTH` to 8 bits (I2C Rx), address mode constant (peripheral side)
4. Start DMA, trigger I2C reception
5. Verify DMA completion interrupt, verify received data in SRAM buffer

### Peripheral DMA Transfer (UART Rx)
1. Configure UART0 with `FCR.RT = 0` (trigger every byte)
2. Program DMA channel with `MSIZE = 0`, HW HS interface 6 (UART0 Rx)
3. Set `CHx_CTL.SRC_TR_WIDTH` to 8 bits
4. Start DMA, send data to UART
5. Verify byte-by-byte reception in SRAM

### Multi-Block LLI Transfer
1. Build linked-list descriptors in SRAM
2. Program CH3 or CH4 for multi-block LLI transfer with prefetch enabled
3. Set up multiple blocks with different source/dest addresses
4. Verify all blocks transfer correctly, verify LLI write-back status

### LLI (Linked List Item) Descriptor Details

Per the Synopsys DW_axi_dmac architecture and HAS configuration, multi-block DMA transfers use **LLI (Linked List Item) descriptors** pointed to by the `CHx_LLP` (Channel Linked List Pointer) register. Each LLI descriptor contains the channel register state for the next block transfer.

#### LLI Descriptor Structure (per SNPS DW_axi_dmac v2.00a)

Each LLI descriptor in memory mirrors the channel programming registers. The DMA fetches the next descriptor from the address in `CHx_LLP` after completing each block. The descriptor fields include:

| Descriptor Field | Maps to Register | Description |
|-----------------|-----------------|-------------|
| SAR | `CHx_SAR` | Source address for the next block |
| DAR | `CHx_DAR` | Destination address for the next block |
| BLOCK_TS | `CHx_BLOCK_TS` | Block transfer size for the next block |
| CTL | `CHx_CTL` | Channel control (TR widths, MSIZE, increment mode, etc.) |
| LLP | `CHx_LLP` | Pointer to the next LLI descriptor (0 = last block) |

> **Note**: Exact descriptor layout and field offsets follow the Synopsys DW_axi_dmac v2.00a databook, which is not reproduced in the NVU HAS. The NVU HAS defines the channel configuration parameters and restrictions that apply to LLI operation.

#### LLI AXI ID Encoding

Per HAS: `DMAX_M_ID_WIDTH = 4` — the AXI transaction ID encodes LLI vs non-LLI:
- Bit [3]: `1` = LLI descriptor fetch, `0` = normal data transfer
- Bits [2:0]: Channel number (CH1–CH8)

#### Per-Channel LLI Configuration (HAS Section 8.11.1)

| Parameter | CH1 | CH2 | CH3 | CH4–CH8 | Description |
|-----------|-----|-----|-----|---------|-------------|
| `MULTI_BLK_EN` | 1 | 1 | 1 | 0 | Multi-block transfer enable |
| `MULTI_BLK_TYPE` | 0x0 | 0x0 | 0x0 | 0x0 | All multi-block types allowed (LLI, contiguous, auto-reload, shadow) |
| `LLI_PREFETCH_EN` | 1 | 1 | 1 | 0 | Prefetch next LLI descriptor during current block |
| `SRC_STAT_EN` | 1 | 1 | 1 | 0 | Write back source status after each LLI block |
| `DST_STAT_EN` | 1 | 1 | 1 | 0 | Write back destination status after each LLI block |
| `LLI_WB_EN` | 1 | 1 | 1 | 0 | Write back channel status registers after each multi-block LLI transfer |

#### LLI Descriptor Location (DMA_MISC.LLI_MODE)

- `LLI_MODE = 0` (default): Descriptors reside in **internal memory** (SRAM)
- `LLI_MODE = 1`: Descriptors reside in **external memory** (DRAM)
- **Restriction**: When SRC or DST is in DRAM:RS3, LLI descriptors **must** be in SRAM (`LLI_MODE = 0`)

#### Supported Multi-Block Transfer Methods

Per the HAS, CH1–CH3 support all four multi-block methods:
1. **Linked List (LLI)** — Descriptors chained via `CHx_LLP` pointers
2. **Contiguous Address** — Next block uses contiguous address range
3. **Auto-Reload** — Channel registers reloaded with same values for next block
4. **Shadow Register** — Next block programmed via shadow register set

Dynamic extension of linked lists is supported (new descriptors can be appended while transfer is in progress).

### DMA RS0/RS3 Security Lockout
1. Complete boot sequence (ROM/BUP disables RS0 and RS3_WR)
2. Attempt DMA transfer to RS0 — verify it is blocked
3. Attempt DMA write to RS3 — verify it is blocked
4. Verify DMA read from RS3 still succeeds (always allowed)

### DMA Address Hole Response
1. Program DMA to access an address within IP allocated range but unmapped
2. Verify OKAY response, write dropped, read returns zero, no FW interrupt
3. Program DMA to access address outside IP allocated range
4. Verify ERROR/UR response, optional FW interrupt

### SIO DMA ISOCH Rx Circular Buffer
1. Configure SIODMA CH3 for ISOCH Rx (DPKTZR → SRAM circular buffer)
2. Set burst size 128B, source constant address, destination incremental
3. Start USB ISOCH streaming
4. Verify circular buffer wrap logic and CBUF threshold interrupt
5. Verify EOF detection via SIODMA IRQ

### DMA Channel Abort
1. Start a long DMA transfer on any channel
2. Issue channel abort (`DMAX_CH_ABORT_EN = 1`)
3. Verify channel stops cleanly and reports abort status
4. Verify channel can be reprogrammed and restarted


## PythonSV Patterns

Pending PythonSV namespace allocation for NVU IP. Below are tentative patterns based on HAS register descriptions:

```python
# NVU PythonSV namespace not yet allocated
# NVU is a PCI RCiEP on IOSF, sideband endpoint name: "NVU"
#
# === Boot/IO DMA Registers (base: 0xF3800000) ===
# DMA register block at 0xF3800000 - 0xF3801000 (4KB, AHB)
# Registers are per Synopsys DW_axi_dmac v2.00a databook
#
# Key DMAC registers (offsets per SNPS DW_axi_dmac):
#   DMAC_CFGREG — DMA Configuration (DMAC_EN, INTEN)
#   CHx_SAR — Channel Source Address
#   CHx_DAR — Channel Destination Address
#   CHx_BLOCK_TS — Channel Block Transfer Size
#   CHx_CTL — Channel Control (SMS, DMS, SINC, DINC, SRC_TR_WIDTH,
#              DST_TR_WIDTH, SRC_MSIZE, DST_MSIZE, ARLEN_EN, AWLEN_EN#   CHx_CFG — Channel Configuration (TT_FC, HS_SEL_SRC, HS_SEL_DST,
#              SRC_PER, DST_PER, CH_PRIOR#   CHx_LLP — Channel Linked List Pointer
#
# Exact register offsets per SNPS databook — not specified in NVU HAS v1.0
#
# === DMA_MISC Registers (base: 0xF3900000) ===
# DMA_MISC register block at 0xF3900000 - 0xF3901000 (4KB, AHB)
#
# DMA Channel Control Register (offset TBD within DMA_MISC block):
#   Bits 1:0   TRANSFER_MODE (RW, default=0)
#   Bits 4:3   RD_RS (RW, default=0) — 0=RS0, 3=RS3
#   Bits 6:5   WR_RS (RW, default=0) — 0=RS0, 3=RS3
#   Bit  8     RD_NON_SNOOP (RWO, default=0)
#   Bit  9     WR_NON_SNOOP (RW, default=0)
#   Bit 10     LLI_MODE (RW, default=0) — 0=internal, 1=DRAM
#
# === SIO DMA Registers (base: 0xF4120000) ===
# SIODMA register block at 0xF4120000 - 0xF4121000 (4KB)
# Registers are per SNPS DW_axi_dmac (separate instance)
#
# === VPX2 DMA Interrupt Map ===
# IRQ 55: DMA IRQ (BootDMA combined interrupt)
# IRQ 59: MAIN_FABRIC IRQ
# IRQ 101: SIODMA IRQ
```


## See Also

- [registers/SKILL.md](../registers/SKILL.md) — DMA_MISC register block, MMIO layout
- [inference/SKILL.md](../inference/SKILL.md) — VPX2/NPX6 data flow via DMA
- [camera/SKILL.md](../camera/SKILL.md) — SIODMA camera data path
- [power/SKILL.md](../power/SKILL.md) — DMA clock gating, PGCB domains
- [debug/SKILL.md](../debug/SKILL.md) — DMA error injection, trace

## Related Sub-Skills

- [fv-nvu/inference](../inference/SKILL.md) — Inference engine, model loading, tensor operations


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:16 | Facts added: 566


### Camera Interface (5 facts)

#### MIPI Computer Vision Image Signal Processor (CVISP) — PD2 Processing Block

*(HAS §8.7.2.3.2)*

The PD2 block within the Altek MIPI CVISP sub-block provides the following key processing components:

- Bayer re-mosaicing logic
- Bayer scaling
- Lens Shading and Black Level Correction
- HW Pixel Processing Engine
- Auto-Exposure / Auto-White Balance statistics generation
- Anti-Flicker statistics generation
- DMA interface

---

#### USB Video Offload Logic — Circular Buffer (CBUF) Registers

*(HAS §8.8.2.1.2.5.3)*

| Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| `CBUF_EN` | 0:0 | RW | 0 | Circular Buffer Enable. `0` = CBUF Disable; `1` = CBUF Enable |
| *(bit 1:1)* | 1:1 | RW1CV | 0 | *(See HAS for details)* |
| `HOSTDMA_EN` | 4:4 | RW | 0 | Enable Host DMA Operation. FW sets this to `1` whenever the Host is requesting a camera stream |

**Register:** `CBUF_CTRL` — Circular Buffer Control Register *(HAS §8.8.2.1.2.5.3)*

---

#### Privacy LED Behavior

*(HAS §8.8.2.4)*

- The privacy LED is turned **ON** to indicate to the end user that the camera is active.
- Per the "Privacy LEF for MIPI" section, the Privacy LED is driven by the IPU; it is noted as an open question whether the IPU or USB subsystem should drive the LED when the camera is in use.


### DMA Architecture (468 facts)

### DMA Architecture

#### Overview

The Intel NVU DMA sub-system provides high-performance data movement between internal SRAM, external memory (via IOSF), and peripheral interfaces including USB. The DMA natively supports 64-bit addressing and is integrated with the SMMU, SRAM sub-system, and USB Video Offload Logic. (§8.2.5.1)

---

#### DMA and External Memory Access

#### Access from DMA to IOSF2AXI Target (§8.2.5.1)

- DMA natively supports 64-bit addressing
- See DMA MISC chapter for full addressing details

---

#### SMMU Integration and SRAM Fabric

#### DMA Initiator in SRAMSS Fabric (§8.6.4.3.1)

| Initiator Block | Name | Protocol | UniqName  | Target Group Access  | Clock Domain (MHz) | Max Frequency (MHz) | Data Width (B) |
|-----------------|------|----------|-----------|----------------------|--------------------|---------------------|----------------|
| SMMU            | DMA  | AXI      | SMMU_DMA  | SLICE, EXTMEM        | 400/200            | 400                 | 16             |

#### DMA Channel FIFO Memory (§8.6.4.1.5)

- NVU instantiates a **256×128** channel FIFO dual-ported RF for Page-IN DMA
- Retention is **not required** for this RF
- Interface port: `smmu_page_in_dma_fifo*` — connects DMA FIFO memory to DMA FIFO RF (§8.6.4.1.3)

---

#### MSI Interrupt Support for DMA (§8.1.4.2)

- MSI differentiation between VOD IPC and DMA for the second PCI function is based on MSGDATA
- MSI is not distinguished by a second PCI function alone; MSGDATA is used for differentiation

---

#### SIO DMA Controller (USB Video Offload Logic)

#### Overview (§8.8.2.1.2.4)

The SIO DMA Controller is part of the USB Video Offload Logic and handles data movement between SRAM and the SIO peripheral interface.

#### SIO Pin to DMA Signal Mapping (§8.8.2.1.2.4)

| SIO Pin # | SIO Pin Type | DMA Req (Output)    | DMA Ack (Input)    | DMA Last (Output)   |
|-----------|-------------|---------------------|--------------------|---------------------|
| 0         | HC          | NA                  | NA                 | NA                  |
| 2         | HAT         | hst_tx_dpreq[0]     | hst_tx_dpack[0]    | hst_tx_dplast[0]    |
| 4         | HAR         | hst_rx_dpreq[0]     | hst_rx_dpack[0]    | hst_rx_dplast[0]    |
| 6         | HAB         | hst_tx_dpreq[1]     | hst_tx_dpack[1]    | hst_tx_dplast[1]    |
| —         | HAB         | hst_rx_dpreq[1]     | hst_rx_dpack[1]    | hst_rx_dplast[1]    |
| 7         | HIR         | hst_rx_dpreq[2]     | hst_rx_dpack[2]    | hst_rx_dplast[2]    |
| 9         | DC          | NA                  | NA                 | NA                  |
| 10        | DIR         | dev_rx_dpreq[0]     | dev_rx_dpack[0]    | NA                  |

#### DMA Channel Assignment (§8.8.2.1.2.4.2)

| Channel # | Hardware Handshake              | Direction        |
|-----------|----------------------------------|------------------|
| 1         | HAT: hst_tx_dpreq/ack[0]        | SRAM to SIO      |
| 1         | HAB: hst_tx_dpreq/ack[1]        | SRAM to SIO      |
| 2         | HAR: hst_rx_dpreq/ack[0]        | SIO to SRAM      |
| 2         | HAB: hst_rx_dpreq/ack[1]        | SIO to SRAM      |
| 3         | HIR: hst_rx_dpreq/ack[2]        | SIO to SRAM      |

#### Channel FIFO Depth (§8.8.2.1.2.4.3)

| Ch # | Max Outstanding | Data Width (B) | Burst Size (B) | Burst Len | CH_FIFO_DEPTH |
|------|-----------------|----------------|----------------|-----------|---------------|
| 1    | 4               | 16             | 16             | 1         | 4             |
| 2    | 4               | 16             | 16             | 1         | 4             |
| 3    | 4               | 16             | 128            | 8         | 32            |

#### De-Packetizer DMA Behavior (§8.8.2.1.2.3)

- For channels 3/4 from DPKTZR to SIO DMA, **MULTI BLOCK TRANSFER** is configured: `DMAX_CH3/4_MULTI_BLK_EN = 1`
- In sensing mode, DMA terminates by asserting `dma_last`

#### De-Packetizer Interrupt/DMA Request (§8.8.2.1.2.3.4)

| DPKTZR Output            | Type | Trigger Condition           | Destination |
|--------------------------|------|-----------------------------|-------------|
| Frame Counter Threshold  | IRQ  | FRAME_COUNT > FC_THRESHOLD  | FW          |

---

#### SIO DMA Configuration Parameters (§8.8.2.1.2.4)

| Symbol                          | Type    | Default Value | Description                                                        |
|---------------------------------|---------|---------------|--------------------------------------------------------------------|
| DMAX_ID_NUM                     | uint32  | 0x0           | DMA ID                                                             |
| DMAX_NUM_CHANNELS               | uint32  | 4             | 4 DMA Channels                                                     |
| DMAX_NUM_HS_IF                  | uint32  | 6             | Design to configure                                                |
| DMAX_INTR_IO_TYPE               | uint32  | 2             | All interrupt outputs                                              |
| DMAX_SLVIF_STATUS_OP_EN         | uint32  | 1             | Target interface status indication                                 |
| DMAX_CORE_STATUS_OP_EN          | uint32  | 1             | Busy/Idle indication from DMA to PM blocks                         |
| DMAX_HOLD_IO_EN                 | uint32  | 0             | No support for DMA hold request feature                            |
| DMAX_UNALIGNED_XFER_EN          | uint32  | 1             | Support un-aligned address on SAR and DAR                          |
| DMAX_MULT_ARB_EN                | uint32  | NA            | Not applicable for DMA channels = 4                                |
| DMAX_CH_ABORT_EN                | uint32  | 1             | Support for DMA Channel Abort                                      |
| DMAX_ASYNC_HS_EN                | uint32  | 0             | ASYNC HS is enabled for all interfaces                             |
| DMAX_HS_SAME_ASYNC_CLK          | uint32  | 0             | Not all DMA HW HS signals are in the same clock domain             |
| DMAX_CH_MEM_EXT                 | uint32  | 1             | Use External RF for FIFO memory                                    |
| DMAX_CH_MEM_REGOUT              | uint32  | 0             | No flop on FIFO memory output                                      |
| DMAX_DEBUG_PORTS_EN             | uint32  | 1             | Debug Ports for VISA observability                                 |
| DMAX_ENABLE_LAST_WRITE          | uint32  | 1             | Enable DMA to indicate last data phase of block transfer; useful for PM logic |
| DMAX_CH_MEM_EXT                 | uint32  | 1             | Use External RF for FIFO memory                                    |
| DMAX_CH_MEM_REGOUT              | uint32  | 0             | No flop on FIFO memory output                                      |
| DMAX_DEBUG_PORTS_EN             | uint32  | 1             | Debug Ports for VISA observability                                 |
| DMAX_MSTIF_MODE                 | uint32  | 1             | AXI4                                                               |
| DMAX_HAS_QOS                    | uint32  | 0             | No QoS Signals on AXI4                                             |
| DMAX_NUM_MASTER_IF              | uint32  | 2             | Two AXI4 Initiator Interfaces                                      |
| DMAX_MSTIF_OSR_LMT              | uint32  | 16            | 16 outstanding bursts                                              |
| DMAX_STATIC_ENDIAN_SELECT_MSTIF | uint32  | 1             | Static Endian (Little Endian)                                      |
| DMAX_LLI_ENDIAN_SELECTION_PIN_EN| uint32  | 0             | LLI Access have same endianness as data accesses                   |
| DMAX_ENDIAN_FORMAT_MSTIF        | uint32  | 0             | Little Endian                                                      |
| DMAX_M_ADDR_WIDTH               | uint32  | 32            | 32-bit address                                                     |
| DMAX_M_DATA_WIDTH               | uint32  | 128           | 128-bit data                                                       |
| DMAX_M_ID_WIDTH                 | uint32  | 3             | [3] indicates LLI/Non-LLI; [1:0] indicates CH#                    |
| DMAX_M_BURSTLEN_WIDTH           | uint32  | 8             | Burst Length                                                       |
| DMAX_SLVIF_MODE                 | uint32  | 2             | APB Target for register access                                     |
| DMAX_INTR_SYNC2SLVCLK          | uint32  | 0             | Interrupt output synchronous to DMA Core Clock                     |
| DMAX_S_DATA_WIDTH               | uint32  | 32            | 32-bit target interface                                            |
| DMAX_SLVIF_CLOCK_MODE           | uint32  | 0             | Target interface synchronous to DMA core Clock                     |
| DMAX_S_2_C_SYNC_DEPTH           | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_C_2_S_SYNC_DEPTH           | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_MSTIF_CLOCK_MODE           | uint32  | 0             | NA for Sync Mode                                                   |
| DMAX_M_2_C_SYNC_DEPTH           | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_C_2_M_SYNC_DEPTH           | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_M_ADDR_FIFO_DEPTH          | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_M_DATA_FIFO_DEPTH          | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_M_BRESP_FIFO_DEPTH         | uint32  | NA            | NA for Sync Mode                                                   |
| DMAX_ASYNC_HS_EN                | uint32  | 0             | ASYNC HS is enabled for all interfaces                             |
| DMAX_HS_SAME_ASYNC_CLK          | uint32  | 1             | All DMA HW HS signals are in the same clock domain                 |
| DMAX_HS_2_C_SYNC_DEPTH          | uint32  | NA            | Two-stage sync for HW HS                                           |
| DMAX_C_2_HS_SYNC_DEPTH          | uint32  | NA            |


### DSP Core (VPX2) (11 facts)

#### Interrupts

The DMA module exposes four interrupt lines to the VPX2 DSP core. (8 IP-Specific Description > 8.1 Interrupts > 8.1.1 VPX2 Interrupts)

| Index | Module | IRQ Name   | IRQ Pin  | Address |
|-------|--------|------------|----------|---------|
| 55    | DMA    | DMA IRQ    | irq55_a  | 0xDC    |
| 56    | DMA    | SPARE0 IRQ | irq56_a  | 0xE0    |
| 57    | DMA    | SPARE1 IRQ | irq57_a  | 0xE4    |
| 58    | DMA    | SPARE2 IRQ | irq58_a  | 0xE8    |

---

#### Memory Map

The DMA block occupies two distinct sub-regions within the VPX2 memory map. (8 IP-Specific Description > 8.2 Memory Maps > 8.2.2 VPX2 Memory Map)

| Block    | Sub Region | Size (KB) | Start Address | End Address |
|----------|------------|-----------|---------------|-------------|
| DMA      | DMA        | 4         | 0xF3800000    | 0xF3801000  |
| DMA_MISC | DMA_MISC   | 4         | 0xF3900000    | 0xF3901000  |

---

#### NOC Fabric — Address Holes

The following behavior applies when the VPX/NPX/DMA initiator generates accesses to address holes. (8 IP-Specific Description > 8.10 NOC Fabric > 8.10.5 Address Holes)

| Initiator       | Address Hole                                              | Expected Response | Interrupt to FW  | Write | Read |
|-----------------|-----------------------------------------------------------|-------------------|------------------|-------|------|
| VPX / NPX / DMA | Within the allocated address range for the IP (per memory map)  | OKAY              | NO               | Drop  | Zero |
| VPX / NPX / DMA | Outside the allocated address range for the IP (per memory map) | ERROR / UR        | YES (optional)   | Drop  | Zero |

- For address holes **within** the allocated IP address range, the NOC returns an `OKAY` response; no firmware interrupt is generated; writes are dropped and reads return zero.
  - **Note:** The DMA itself sends an error response for address holes within its allocated address range. (8 IP-Specific Description > 8.10 NOC Fabric > 8.10.5 Address Holes)
- For address holes **outside** the allocated IP address range, the NOC returns an `ERROR/UR` response; a firmware interrupt is optionally raised; writes are dropped and reads return zero.


### GPIO and Pin Mux (2 facts)

#### NVU Power States

(HAS: Chapter 9: NVU Power Management > 13.4 Power States)

The NVU DMA sub-skill operates within a defined set of power states that govern active execution and power saving behavior.

##### Power State Table

| Power State | Description | Power Saving Options | Wake Sources | Lowest Allowed S0ix |
|---|---|---|---|---|
| D0i0 | NVU is in DAQ (Data Acquisition) or VPX/NPX execution from SRAM | Block level CG; SRAM auto retention by HW; RLTR: Infinite (default) or 2ms (RS3 DMA) | — | — |

##### Behavioral Notes

- **D0i0** is the active operational state during which the NVU performs Data Acquisition (DAQ) or executes VPX/NPX workloads from SRAM.
- **Block level clock gating (CG)** is applied as a power saving option during D0i0 to reduce dynamic power consumption.
- **SRAM auto retention** is managed by hardware in D0i0, ensuring data integrity without software intervention.
- The **RLTR (Retention Latency Tolerance Requirement)** has two configurable values in this state:
  - `Infinite` — default setting
  - `2ms` — used specifically in the **RS3 DMA** configuration


### Neural Network Accelerator (25 facts)

#### Neural Network Accelerator — DMA Sub-Skill

---

#### Overview

The NVU DMA subsystem encompasses multiple DMA controller instances serving distinct functional domains: the **Boot DMA** (§8.11), the **SIO DMA** (§8.8.2.1.2.4), and DMA hooks associated with peripheral controllers (§8.18.5). The NPX6-1K neural processing tile also includes dedicated iDMA/oDMA accelerators within its Streaming Transfer Unit (§8.4.3).

---

#### NPX6-1K Streaming Transfer Unit (STU) DMA (§8.4.3)

- The STU performs data transfers between L1 memories and contains two internal DMA accelerators:
  - **NPU iDMA** — inbound data transfers into L1
  - **NPU oDMA** — outbound data transfers from L1
- Supports flexible 2D data transfers with configurable strides
- The L1 ARCv2HS core controls task scheduling for the accelerators and handles asynchronous events via an ISA extension

---

#### Boot DMA Controller — Configuration (§8.11 DMA Controller > 8.11.1 DMA Configuration)

##### Channel Parameters

| Parameter | Type | Value | Description |
|---|---|---|---|
| `DMAX_CH(x)_WR_UID` | uint32 | NA | No support for unique IDs |
| `DMAX_CH1_FIFO_DEPTH` | uint32 | 4 | 4×16 bytes for this channel |
| `DMAX_CH1_MAX_BLOCK_TS` | uint32 | 4095 | Max Block Transfer Size set to 4K |
| `DMAX_CH1_LOCK_EN` | uint32 | 1 | Enable channel locking |

##### LLI Prefetch Enable Parameters

| Parameter | Type | Reset Value | Description |
|---|---|---|---|
| `DMAX_CH1_LLI_PREFETCH_EN` | uint32 | 0x1 | Allow LLI prefetch to improve performance |
| `DMAX_CH2_LLI_PREFETCH_EN` | uint32 | 0x1 | Allow LLI prefetch to improve performance |
| `DMAX_CH3_LLI_PREFETCH_EN` | uint32 | 0x1 | Allow LLI prefetch to improve performance |
| `DMAX_CH4_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH5_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH6_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH7_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH8_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |

##### Configuration Notes (§8.11.1.1)

- **CH1 and CH2** are optimized for high performance and high bandwidth; they are intended for MEM-to-MEM transfers.
- LLI prefetch is enabled by default on CH1–CH3 to maximize throughput for burst transfer workloads.
- CH4–CH8 have LLI prefetch disabled by default.

---

#### SIO DMA Controller — Configuration (§8.8.2.1.2.4 SIO DMA Controller)

##### Channel Parameters

| Parameter | Type | Value | Description |
|---|---|---|---|
| `DMAX_CH(x)_WR_UID` | uint32 | NA | No support for unique IDs |
| `DMAX_CH1_FIFO_DEPTH` | uint32 | 4 | 4×16 bytes for this channel |
| `DMAX_CH1_MAX_BLOCK_TS` | uint32 | 16383 | Max Block Transfer Size set to 16K |
| `DMAX_CH1_LOCK_EN` | uint32 | 1 | Enable channel locking |

##### LLI Prefetch Enable Parameters

| Parameter | Type | Reset Value | Description |
|---|---|---|---|
| `DMAX_CH1_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH2_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH3_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |
| `DMAX_CH4_LLI_PREFETCH_EN` | uint32 | 0x0 | Allow LLI prefetch to improve performance |

##### SIO DMA Behavioral Description

- When pin logic SEN (Serial Enable) is asserted, the DMA is armed and ready to receive transfer requests. (§8.8.2.1.2.4)
- Upon receiving data, the SIO pin logic issues `hst_rx_dpreq` toward the SIO DMA. (§8.8.2.1.2.4)
- The SIO DMA reads data from the SIO interface and writes it to SRAM, then asserts `hst_rx_dpack` to acknowledge the transfer. (§8.8.2.1.2.4)
- For MULTI BLOCK TRANSFER mode, a minimum of two blocks of data must be available to the SIO DMA; failure to meet this requirement results in unpredictable behavior. (§8.8.2.1.2.3)

---

#### Firmware Boot Flow — DMA and LTR Requirements (§9.2.1.1 Extra ROM Tasks)

- The ROM must use an LTR (Latency Tolerance Reporting) message to communicate latency tolerance requirements to the PMC for DDR access during DMA operations.
- **Before DMA operation:** ROM sets a **2 ms LTR** value to the PMC.
- **After DMA operation:** ROM sets an **infinite LTR** value to the PMC.

---

#### SPI Controller DMA Hardware Hooks (§8.18.5 SPI Performance)

- Each SPI controller supports **DMA Hardware Hooks** to improve transfer performance.
- DMA hooks reduce the interrupt overhead from the SPI controller by eliminating the need for a dedicated interrupt to signal Tx space availability or Rx data readiness.

---

#### SRAM Address Mapping and DMA Accessibility (§8.6.2 SRAMSS Memory Mapping)

- Physical SRAM is mapped at address range **`0x6800_0000–0x6808_0000`**.
- When the PTU (Page Table Unit) is configured, SRAM at `0x6800_0000` can be accessed via virtual address `0x6000_0000` on NVU FPGA.
- SRAM regions may be mapped to VMEM for use by DMA and accelerator transactions.
- CV Shared Memory resources loaded via DMA require **4 KiB alignment**; if a resource is already loaded, the load operation is skipped. (§12.10.2)


### Peripheral Interfaces (29 facts)

#### Peripheral Handshake Assignment (8.11.3)

The DMA controller uses hardware handshake interfaces to coordinate data transfers with on-chip peripherals. The following table defines the peripheral ID assignments for all HW handshake interfaces.

| HW Handshake Interface # | Peripheral Handshake Interface |
|---|---|
| 0 | I2C0 Rx |
| 1 | I2C0 Tx |
| 2 | I2C1 Rx |
| 3 | I2C1 Tx |
| 4 | I2C2 Rx |
| 5 | I2C2 Tx |
| 6 | UART0 Rx |
| 7 | UART0 Tx |
| 8 | UART1 Rx |
| 9 | UART1 Tx |
| 10 | UART2 Rx |
| 11 | UART2 Tx |

---

#### TR Widths for Peripheral Data Transfers (8.11.4)

The following table defines the required DMA transfer (TR) widths for each supported peripheral type.

| Peripheral | TR Width (bits) | Comments |
|---|---|---|
| I2C Tx | 16 | 8-bits of data; upper bits carry control information |
| I2C Rx | 8 | 8-bits of data |
| SPI Tx/Rx | 8 / 16 / 32 | SPI supports 8/16/32-bit TR width |
| I3C | 32 | I3C supports 32-bit TR width |

---

#### DMA Programming Restrictions (8.11.5)

- For **UART Rx** transfers, the DMA **must** be configured with `MSIZE = 0`.
- The UART Receiver Trigger (`FCR.RT`) **must** be set to `0` so that a DMA request is generated for every byte received.
- This restriction exists because of the way the UART peripheral signals DMA requests relative to FIFO threshold behavior.

---

#### I2C Controller — DMA Interface (8.17.3, 8.17.6)

**I2C DMA-Related Parameters**

| Name | Type | Default Value | Description |
|---|---|---|---|
| IC_HAS_DMA | uint32 | 0x1 | Configures the inclusion of DMA handshaking interface signals |

**Behavioral Notes**

- Each I2C controller supports **DMA Hardware Hooks** to improve performance.
- DMA hardware hooks reduce the number of interrupts required from the I2C controller to signal the availability of Tx space or Rx data.

---

#### UART Controller — DMA Interface (8.19.2.1)

**UART DMA-Related Parameters**

| Name | Type | Default Value | Description |
|---|---|---|---|
| DMA_EXTRA | uint32 | 1 | Enable 4-wire DMA handshake |
| DMA_POL | uint32 | 0 | DMA signals polarity (active high) |
| DMA_HS_REQ_ON_RESET | uint32 | 1 | DMA Tx request will be asserted on reset |

---

#### I3C Controller — DMA Interface (8.20.1, 8.20.2, 8.20.4)

**I3C DMA Clocking**

- The `pclk` and `dma_clk` are both connected to the NVU fabric clock and scale up/down with NVU CPU/Fabric clocks (8.20.1).
- The DMA clock and core clock are **asynchronous** to each other (`IC_DMA_CORE_CLK_TYPE = 1`) (8.20.4).

**I3C Clock Mode Table** (8.20.1)

| CORE_CLK | PCLK | DMA_CLK | Comments |
|---|---|---|---|
| 200 MHz | 100 MHz | 100 MHz | CORE_CLK at 200 MHz to achieve 12.5 MHz on I3C. 400/200 MHz trunk must be running. |

**I3C DMA Architecture** (8.20.2)

- The I3C controller does **not** have a built-in DMA engine.
- The I3C controller supports the **HW handshake protocol** and relies on the NVU DMA for data movement between SRAM and I3C buffers.

**I3C DMA-Related Parameters** (8.20.4)

| Name | Type | Default Value | Description |
|---|---|---|---|
| IC_HAS_DMA | uint32 | 1 | Support DMA Hardware Handshake |
| IC_HAS_HCI_EDMA | uint32 | 1 | Support DMA Hardware Handshake (HCI eDMA) |
| IC_DMA_CORE_CLK_TYPE | uint32 | 1 | DMA clock and core clock are asynchronous |


### USB Camera Interface (26 facts)

#### USB Camera Interface — DMA Sub-Skill

### Overview

The USB Camera Interface DMA functionality is implemented within the **USB Video Offload Logic (UVOL)** sub-block, part of the USB Interface Sub-System (§8.8). UVOL exposes a `dma_req` signal and integrates a multi-channel DMA controller to move video data between the SIO FIFO and NVU SRAM.

---

#### UVOL Block Diagram Notes (§8.8.2.1.1)

- UVOL acts as the DMA source, asserting `dma_req` to initiate transfers.
- **Pending correction:** The block diagram references Pin 8 (Device cmd/Rsp) for the SIO DMA connection; per Chapter 2, this should be **Pin 6**. Update required.
- **Pending correction:** Channel 3 of the SIO DMA must be mapped to **PIN-7**.

---

#### SIO Component Parameters (§8.8.2.1.2.1.1)

| Symbol | Type    | Default | Description                                              |
|--------|---------|---------|----------------------------------------------------------|
| PFDTW  | uint32  | 16      | Pin FIFO DMA Transfer Width — DMA Interface Width 128 bits |

---

#### SIO Component Clocks and Integration Interface (§8.8.2.1.2.1.3)

| Clock       | Source | Frequency | Purpose            |
|-------------|--------|-----------|--------------------|
| core_clk    | CRPM   | 200 MHz   | Functional Clock   |
| gcore_clk   | CRPM   | 200 MHz   | Functional Clock   |
| xtal_clk    | CRPM   | 38.4 MHz  | XTAL Clock         |

---

#### SIO Component DMA Pin Connectivity (§8.8.2.1.2.1.3)

| Interface       | Pin         | Connectivity                          | Comments                          |
|-----------------|-------------|---------------------------------------|-----------------------------------|
| Device Rx DMA   | dev_rx_dp*  | RAW Link Logic                        | Device mode data payload req/ack  |
| Host Rx DMA     | hst_rx_dp*  | DPKTZR (ISOCH) / SIODMA (ASYNC)       | —                                 |
| Host Tx DMA     | hst_tx_dp*  | SIODMA                                | —                                 |

- For SIO transaction flow details, refer to the SIO Component HAS (§8.8.2.1.2.1.5).
- DMA and De-Packetizer (DPKTZR) flow and programming details are described in their respective sections.

---

#### De-Packetizer (DPKTZR) Flows (§8.8.2.1.2.3.3)

- **Input Flow:** SIO DPKTZR Input Flow (§8.8.2.1.2.3.3.1)
- **Output Flow:** SIO DPKTZR Output Flow (§8.8.2.1.2.3.3.2)
- **Stopping the Streams — Sensing Mode** (§8.8.2.1.2.3.3.3.1)

---

#### SIO DMA Controller (§8.8.2.1.2.4)

- UVOL logic includes a **4-channel DMA controller**.
- Primary function: move data **from/to the SIO FIFO ↔ NVU SRAM**.
- DMA controller is based on the **SNPS DW_axi_dmac** IP.
- For channels 3/4 (DPKTZR to SIO DMA), **multi-block transfer** is used (`DMAX_CH3/4_MULTI_BLK_EN = 1`). In sensing mode, the DMA terminates by signalling `dma_last`.

##### SIO Pin and DMA Interface (§8.8.2.1.2.4.1)

> *Note: Pin Direction refers to direction on the SIO Component.*

| SIO Pin # | SIO Pin Type | DMA Req (Output) | DMA Ack (Input) | DMA Last (Output) |
|-----------|--------------|------------------|-----------------|-------------------|
| 0         | HC           | NA               | NA              | NA                |
| 2         | HAT          | (see HAS table)  | (see HAS table) | (see HAS table)   |

##### DMA Controller Configuration Parameters (§8.8.2.1.2.4.4)

| Name    | Value / Detail             |
|---------|---------------------------|
| IP      | UVOL SIO DMA              |
| Comment | UVOL SIO DMA Functional Parameters |
| DMAX_ID_NUM | uint32 (see HAS for full table) |

---

#### DMA Programming — Host Async Tx (§8.8.2.1.2.4.6)

- Host Async Tx is a **one-shot DMA operation**.
- **CH1** is used for this transfer.
- Required DMA programming sequence:
  - `DMAC_CFGREG.INTEN = 1` → Enable interrupts.
  - `CH1_DAR` → Set to SIO HAT Pin Base Address *(note: must include FSAO offset — pending spec correction)*.
  - `CH1_CFG.DST_PER`:
    - `0x0` for Async Tx
    - `0x1` for Async Bi-Di Tx
    *(pending spec correction — current document incorrectly states `0x1` for HAT)*
  - `CH1_BLOCK_TS` → Set to **3072 B (max)**; however, for CH1 (EP0 Tx and Async Tx), this **must be programmed to the actual message size (DPS)** because no `dma_last` signal is generated by the SIO component for this channel.

---

#### DMA Programming — Host Async Rx (§8.8.2.1.2.4.7)

- Host Async Rx is a **one-shot DMA operation**.
- **CH2** is used for this transfer.
- Required DMA programming sequence:
  - `DMAC_CFGREG.INTEN = 1` → Enable interrupts.
  - *(Refer to HAS §8.8.2.1.2.4.7 for complete register programming sequence.)*

---

#### DMA Programming — Host Async Bi-Di (§8.8.2.1.2.4.8)

- Host Async Bi-Di is a **one-shot operation** that involves **2 DMA channels**.
- Used for EP0 programming of the USB device.
- *(Refer to HAS §8.8.2.1.2.4.8 for complete register programming sequence.)*

---

#### NOC Fabric — UVOL DMA Target (§8.10.2)

| Target     | Name | Protocol | UniqName      | Target Group | Clock Domain (MHz) | Max Freq (MHz) | Data Width (B) | Burst Size (B) |
|------------|------|----------|---------------|--------------|--------------------|----------------|----------------|----------------|
| UVOL_HOST  | DMA  | APB      | UVOL_HOST_DMA | HOST         | 200                | 200            | 4              | 4              |

---

#### NOC Fabric — DMA Initiator Connectivity (§8.10.3, §8.10.4)

- The **DMA_INIT** initiator has the following target group access permissions:

| Initiator | PVT_MEM | REGS | IO | EXT_RD | EXT_WR | DUAL | ARCSYNC | VMEM0 | VMEM1 | PMEM0 | PMEM1 | STRM | HOST |
|-----------|---------|------|----|--------|--------|------|---------|-------|-------|-------|-------|------|------|
| DMA_INIT  | Y       | N    | Y  | Y      | Y      | N    | N       | N     | N     | Y     | N     | N    | N    |

- DMA_INIT operates at the clock domain and frequency defined in the MAIN_INIT initiator table (§8.10.3); refer to the NOC Fabric HAS for full bandwidth parameters.

