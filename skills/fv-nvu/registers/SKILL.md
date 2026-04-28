---
name: fv-nvu/registers
description: NVU MMIO/PCI register map, bitfields, offsets, and access patterns
---

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`) — william.willy.chin@intel.com, Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.
>
> **⚠️ NEVER trust AI 100%.** This skill file is a productivity aid, not a replacement for engineering judgment. AI can hallucinate, confuse similar IPs (e.g., NVU vs NVL/NPU6), or present outdated information as current. **When in doubt, verify with the owner/co-owner or check the authoritative HAS document directly.** For CoDeSign-based HAS verification, see the FV-NVU agent definition (`FV-NVU.md`).

# NVU Registers

> **SAFETY**: Do NOT write to NVU registers without explicit user confirmation.
> Register data below is sourced from the NVU HAS extraction (v1.0).
> Items marked **TBD** require the external OSXML/HTML register spec referenced by HAS Section 16,
> or data from Synopsys DesignWare IP datasheets that are not included in the HAS.

## Overview

This sub-skill covers the NVU PCI configuration space and MMIO register map. It provides:
- PCI configuration register definitions (from HAS Section 8.12 / 19)
- Internal VPX2 memory map with sub-IP register targets (from HAS Section 8.2.2)
- Host-visible register map via ATT translation (from HAS Section 8.2.6)
- SRAM Slice Controller and DMA_MISC register bitfields (from HAS Sections 8.6 / 8.11)
- Interrupt map summary (from HAS Section 8.1)
- PythonSV access patterns (pending namespace allocation)

### Register Documentation Note

HAS Section 16 (Registers) states: *"Pls download the HTML folder"* for both FW View and Host View register specs. The authoritative per-register bitfield definitions live in an external OSXML/HTML document, not inline in the HAS. The data below captures everything available from the HAS prose and parameter tables.

---

## PCI Configuration Space

NVU is an **RCiEP** (Root Complex integrated Endpoint) with **2 PCI functions**:
- **FN0** — NVU SW Driver (64KB BAR at internal address `0x8000_0000`)
- **FN1** — (details not specified in available source facts)

> **Note**: RTL parameterizes `NUM_PCI_FUNCTIONS=2`, but from the NVU SoC perspective only **1 PCI function is exposed** — the second function's strap is internally tied off and not exposed to SoC (HAS feedback [1754]). The HAS host interrupts section (Section 8.3) also states "NVU has 1 PCI functions." Treat as 2 in RTL, 1 at SoC level.

The IOSF2AXI bridge (Section 8.12) has `NUM_PCI_FUNCTIONS=2`, `NUM_BARS=2`, `PCI_CONFIG_ENABLE=1`. Additional bridge parameters: `VDM_SUPPORT=1` (Vendor Defined Messages enabled), `NUM_VDM_ROUTEBYID_BDF=2` (2 VDM route-by-ID BDF entries for SIO peer-to-peer messaging), `HH_SUPPORT=1` (Hammock Harbor Type-D timestamp synchronization enabled).

### PCI Functions Summary (Integration HAS Section 7)

| Function | Name | BAR Size | Internal Base Address | Description |
|----------|------|----------|-----------------------|-------------|
| FN0 | NVU SW Driver | 64KB | `0x8000_0000` | Host IPC, config registers |
| FN1 | (details not specified in HAS v1.0) | TBD | TBD | Second PCI function — specifics not defined in available source facts |

| Offset | Name | Size | Default / Value | Source | Description |
|--------|------|------|-----------------|--------|-------------|
| `0x00` | VID | 16-bit | `0x8086` | HAS 8.12 | Vendor ID (Intel) |
| `0x02` | DID | 16-bit | Platform-specific (soft-strap) | HAS 19 | Device ID — not given explicitly; set per platform SKU |
| `0x04` | CMD | 16-bit | TBD — not in HAS v1.0 | OSXML | Command Register — PCICMD.INTDIS referenced in interrupt selection (Section 8.1) |
| `0x06` | STS | 16-bit | TBD — not in HAS v1.0 | OSXML | Status Register |
| `0x08` | RID | 8-bit | `0x00` (soft-strap `RevisionId0`, default 0) | HAS 19 | Revision ID |
| `0x09` | CC | 24-bit | `0x000000` (all three bytes via soft-straps, default 0) | HAS 19 | Class Code — `NVU_BaseClass_code_func1_SoftStrap`, `NVU_SubClass_code_func1_SoftStrap`, `NVU_Reg_prg_intf_func1_SoftStrap` |
| `0x10` | BAR0 | 32-bit | 64KB region | HAS 8.12 | MMIO Base Address — `BAR_SIZE_0 = 0x10000` (64KB), remapped to `0x8000_0000` internally |
| `0x2C` | SVID | 16-bit | TBD — not in HAS v1.0 | OSXML | Subsystem Vendor ID |
| `0x2E` | SDID | 16-bit | TBD — not in HAS v1.0 | OSXML | Subsystem Device ID |

### PCI Capabilities

| Capability | Status | Source | Notes |
|------------|--------|--------|-------|
| MSI | **Enabled** (`ENABLE_MSI_CAP = 0x3`) | HAS 8.12 | `MSI_MULT_MSG_CAP = 0` → **1 vector** (HAS cross-check D1: was incorrectly listed as 32) |
| MSI-X | **Disabled** (`ENABLE_MSIX_CAP = 0x0`) | HAS 8.12 | Not present |
| LTR | **Disabled** (`ENABLE_LTR_CAP = 0x0`) | HAS 8.12 | Latency Tolerance Reporting not enabled |
| PCI Idle | **Enabled** (`ENABLE_PCI_IDLE_CAP = 0x3`) | HAS 8.12 | PCI Idle capability (per-function) |

### Interrupt Selection (HAS Section 8.1, Line 3641)

| PCICFG.PCICMD\[INTDIS\] | PCICFG.MSICAP\[MSI_EN\] | Interrupt Mechanism |
|:---:|:---:|---|
| 0 | 0 | Legacy INTx |
| 0 | 1 | MSI |
| 1 | 0 | Interrupts disabled |
| 1 | 1 | MSI |

#### MSI Generation (HAS Section 8.1.4)

MSI messages are generated by the IOSF2AXI bridge using the **WIRE2MSI** method. The `ENABLE_WIRE2MSI` bit must be set to `1` (default).

The MSI_GEN block inside NVU initiates MSI requests to the bridge:
- MSI_GEN detects the **rising edge** of internal interrupt lines (already qualified by `!D3 & BME & MSI_EN`).
- A fixed-priority arbiter selects the winning interrupt (FN1 > FN0).
- MSI_GEN asserts `msi_req` to the IOSF2AXI bridge with the corresponding DEVFN on the `MSI_USER` bus.
- The bridge generates the MSI packet on IOSF using the MSI address/data for that PCI function and acknowledges via `msi_ack`.
- If `OOB_MSI_MASK` is set for the asserted interrupt, MSI_GEN enters PENDING state and asserts `OOB_MSI_PENDING` until the mask is cleared.

---

## Host-Visible Register Map (BAR0, via ATT Translation)

The host sees a single **64KB BAR** at BAR0. The Address Translation Table (ATT) in the IOSF2AXI bridge maps host accesses into the internal VPX2 address space. Only 3 regions are host-accessible via MMIO (HAS Section 8.2.6):

| ATT Entry | Host Offset (from BAR0) | Size | Internal Target Address | Target Name | Access Method |
|:---------:|-------------------------|------|------------------------|-------------|---------------|
| 0 | `0x0000_0000` | 4KB | `0xF100_0000` | HOST_IPC | MMIO via BAR |
| 1 | `0x0001_0000` | 28KB | `0xF110_0000` | PEER_IPC | PVTCR (Private Config Register) |
| 2 | `0x0001_8000` | 4KB | `0xF200_0000` | SEC_REG | PVTCR (Private Config Register) |

> **Key insight**: The host driver's primary interface is through **HOST_IPC** (Inter-Processor Communication) at BAR0 offset 0. The host does NOT have direct MMIO access to internal peripherals (I2C, SPI, DMA, SRAM, etc.) — those are firmware-only.

---

## Internal VPX2 Memory Map (Firmware View)

These addresses are in the VPX2 internal address space (Region 15: `0xF000_0000 – 0x1_0000_0000`). They are **NOT directly accessible from the host** — they are firmware-side register targets. Source: HAS Section 8.2.2.

### IO Peripherals (Synopsys DesignWare IPs)

| Internal Address | Target | Instances | Notes |
|-----------------|--------|-----------|-------|
| `0xF000_0000` | I2C | 3 (4KB each) | DW_apb_i2c — register map per Synopsys databook |
| `0xF010_0000` | I3C | 2 | DW_apb_i3c — register map per Synopsys databook |
| `0xF020_0000` | SPI | 2 | DW_apb_ssi — register map per Synopsys databook |
| `0xF030_0000` | UART | 3 | DW_apb_uart — register map per Synopsys databook |
| `0xF040_0000` | GPIO | 1 | DW_apb_gpio — register map per Synopsys databook |

#### Per-Instance Addresses (HAS Section 8.2.2, 0x1000 stride)

| Instance | Address | Group |
|----------|---------|-------|
| I2C0 | `0xF000_0000` | I2C |
| I2C1 | `0xF000_1000` | I2C |
| I2C2 | `0xF000_2000` | I2C |
| I3C0 | `0xF010_0000` | I3C |
| I3C1 | `0xF010_1000` | I3C |
| SPI0 | `0xF020_0000` | SPI |
| SPI1 | `0xF020_1000` | SPI |
| UART0 | `0xF030_0000` | UART |
| UART1 | `0xF030_1000` | UART |
| UART2 | `0xF030_2000` | UART |
| GPIO | `0xF040_0000` | GPIO |

#### IO Peripheral Detailed Specifications (Integration HAS v0.8, Section 7)

| Peripheral | Instances | Max Speed | FIFO Depth | Modes / Compatibility | Notes |
|------------|-----------|-----------|------------|----------------------|-------|
| **I2C** (DW_apb_i2c) | 3 | 3.4 MHz (HS mode) | 64B TX/RX | Standard (100 KHz), Fast (400 KHz), Fast+ (1 MHz), High-Speed (3.4 MHz) | 4KB register space each; Address: `0xF000_0000` |
| **I3C** (DW_apb_i3c) | 2 | 25 MHz (DDR) | CMD: 16B, Data: 64B, IBI: 16B+64B | PIO mode, DAA (Dynamic Address Assignment), Hot-Join, In-Band Interrupts (IBI) | HDR-DDR at 25 MHz; Address: `0xF010_0000` |
| **SPI** (DW_apb_ssi) | 2 | 25 Mbps | 64B TX/RX | Master/Slave, single/dual/quad SPI | Address: `0xF020_0000` |
| **UART** (DW_apb_uart) | 3 | 6 Mbps | 64B TX/RX | 16550/16750 compatible, programmable baud rate | Address: `0xF030_0000` |

### System & Control Blocks

| Internal Address | Target | Notes |
|-----------------|--------|-------|
| `0xF100_0000` | HOST_IPC | Host-facing IPC (also visible at BAR0+0x0) |
| `0xF110_0000` | PEER_IPC (CSE) | IPC to Converged Security Engine |
| `0xF110_1000` | PEER_IPC (PMC) | IPC to Power Management Controller |
| `0xF110_2000` | PEER_IPC (CNVI) | IPC to Connectivity |
| `0xF110_3000` | PEER_IPC (ACE) | IPC to Audio/Compute Engine |
| `0xF110_4000` | PEER_IPC (ESE) | IPC to Embedded Security Engine |
| `0xF110_5000` | PEER_IPC (BT) | IPC to Bluetooth |
| `0xF110_6000` | PEER_IPC (ISH) | IPC to Integrated Sensor Hub |
| `0xF200_0000` | SEC_REG | Security registers (also visible at BAR0+0x18000) |
| `0xF210_0000` | ATT | Address Translation Table |

### Infrastructure & Debug

| Internal Address | Target | Notes |
|-----------------|--------|-------|
| `0xF300_0000` | CRPM | Clock, Reset, and Power Management — internal register map TBD (not detailed in HAS) |
| `0xF320_0000` | MISC | Miscellaneous registers — TBD |
| `0xF330_0000` | SBEP | Sideband Endpoint — IOSF-SB message interface |
| `0xF340_0000` | DTF | Design-for-Test/Fabric — debug |
| `0xF350_0000` | WDT | Watchdog Timer |
| `0xF360_0000` | HPET | High Precision Event Timer |
| `0xF370_0000` | FABRIC | Internal fabric/interconnect config |

### DMA & Memory

| Internal Address | Target | Notes |
|-----------------|--------|-------|
| `0xF380_0000` | DMA | Synopsys DW_axi_dmac — 8 channels (DMAX_NUM_CHANNELS=8). Note: SIODMA (separate IP) has 4 channels instantiated, 3 active (Ch0 unused). |
| `0xF390_0000` | DMA_MISC | DMA miscellaneous / channel control (see DMA_MISC section below) |
| `0xF500_0000` | SRAMSS_CFG | SRAM Sub-System configuration — 1MB region (see SRAM section below) |

### VMEM Virtual Address Space (SMMU)

The NVU SMMU provides a virtual memory address space for FW-managed paging between DRAM and SRAM:

| Parameter | Value | Description |
|-----------|-------|-------------|
| VMEM Size | 16384 KB (16 MB) | Total SMMU virtual address space |
| PA Memory Pages | 4096 | Total physical address memory pages |
| PA Address Bits | 14 | PA page addressing width |

The SMMU translates virtual addresses from VPX2/NPX6 to physical SRAM pages or external DRAM (RS3 IMR), enabling transparent FW paging of model weights and intermediate data.

### Compute & Media

| Internal Address | Target | Notes |
|-----------------|--------|-------|
| `0xF600_0000` | NPX_DMI | NPX6 Debug Memory Interface |
| `0xF610_0000` | NPX_ARCSYNC | NPX6 ARC Sync module |
| `0xF620_0000` | NPX_DEBUG | NPX6 Debug registers (ROM Table, ARCTrace, L1 Core) |
| `0xF700_0000` | ALTEK_ISP | ISP (Image Signal Processor) |
| `0xF710_0000` | PHY_CFG | MIPI CSI-2 PHY configuration |
| `0xF720_0000` | EXT_PHY | External PHY (CDPHY) registers — 64KB |
| `0xF730_0000` | CSI2_HC | MIPI CSI-2 Host Controller |
| `0xF400_0000` | MJPEG_DEC | Motion JPEG Decoder |
| `0xF410_0000` | UVOL_CFG | USB Camera Offload Logic — 1MB |
| `0xF412_0000` | SIODMA | SIO DMA controller — 4KB |

---

## Detailed Register Definitions

The following registers have bitfield-level definitions available in the HAS.

### SRAM Slice Controller Registers (HAS Section 8.6)

NVU has **3584KB** of physical SRAM (`SRAM_SIZE=3584`), partitioned into **7 slices** of **512KB** each (`NUM_SRAM_SLICES=7`, `SRAM_SLICE_SIZE=512`). Each slice contains **4 × 128KB banks** (tile size 128KB). SRAMSS_PMEM spans `0x68000000–0x68380000`. The SMMU maps this as **Pageable SRAM at 0x68000000** — firmware manages paging between on-chip SRAM and DRAM (IMR) via the DMA controller. In the NVU virtual memory map, VMEMP (Virtual Memory Physical) at `0x60000000` provides the physical SRAM backing for SMMU-translated accesses.

> **SRAM Tile Geometry (Integration HAS v0.8, Section 7.2)**: SRAM tiles are organized as `SRAM_TILE_WIDTH=16B` wide by `SRAM_TILE_HEIGHT=8K` rows. Total number of physical SRAM banks: `NUM_SRAM_BANKS=28` (7 slices × 4 banks/slice). Each tile is 128KB (16B × 8192 rows).

| Slice | Size | Start Address | End Address |
|-------|------|---------------|-------------|
| SLICE0_MEM | 512KB | `0x68000000` | `0x68080000` |
| SLICE1_MEM | 512KB | `0x68080000` | `0x68100000` |
| SLICE2_MEM | 512KB | `0x68100000` | `0x68180000` |
| SLICE3_MEM | 512KB | `0x68180000` | `0x68200000` |
| SLICE4_MEM | 512KB | `0x68200000` | `0x68280000` |
| SLICE5_MEM | 512KB | `0x68280000` | `0x68300000` |
| SLICE6_MEM | 512KB | `0x68300000` | `0x68380000` |

**Power**: Each 128KB bank draws ~150mA inrush current when exiting DeepSleep/ShutDown. Per slice: 150mA × 4 = **600mA**. The SRAM di/dt manager ensures only ONE slice exits DeepSleep at a time.

Each slice's controller has these registers:

#### SSCR — SRAM Slice Controller Control Register

| Bits | Name | Access | Description |
|------|------|--------|-------------|
| 0 | RMWPIPESTG | R/W | Read-Modify-Write Pipeline Stage enable (default = 1) |
| 1 | ECCENB | R/W | ECC Enable (active-low naming per HAS) (default = 0) |
| 2 | DSOVREN | R/W | DeepSleep Override Enable (default = 1) |
| 3 | DSOVRVAL | R/W | DeepSleep Override Value (default = 0) |
| 4 | SDEN | R/W | ShutDown Enable (default = 1) |
| 5 | MEMPIPEN | R/W | Memory Pipeline Enable (default = 1) |
| 7:6 | RSVD | RO | Reserved |
| 11:8 | DSMINDUR | R/W | DeepSleep Minimum Duration (default = 0x4) |
| 12 | ECCSCRUB | RW1SV | ECC Scrub — write-1-to-trigger, HW self-clears when complete (default = 0) |
| 14:13 | RSVD | RO | Reserved (gap — not defined in HAS) |
| 31:15 | RSVD | RO | Reserved |

> **Note**: Exact register offset within SRAMSS_CFG (`0xF500_0000`) region is TBD — not specified in HAS prose. Per-bank stride TBD.

#### SSCEL — SRAM Slice Controller ECC Log Register

| Bits | Name | Access | Description |
|------|------|--------|-------------|
| 15:0 | CNT | ROVP | ECC Correctable Error Count — auto-increments on error, saturates at `0xFFFF`, reset only on `powergood_rst_b` (default = 0) |
| 16 | CERREV | ROVP | Correctable ECC Error Event — RO for FW, reset only on `powergood_rst_b` (Sx/G3) (default = 0) |
| 30:17 | RSVD | RO | Reserved |
| 31 | UCERREV | ROVP | Uncorrectable ECC Error Event — RO for FW, reset only on `powergood_rst_b` (Sx/G3) (default = 0) |

#### SSCMAS — SRAM Slice Controller Memory Access Status

| Bits | Name | Access | Description |
|------|------|--------|-------------|
| 30:0 | RSVD | RO | Reserved |
| 31 | HWZRDONE | RO/V/P | Hardware Zeroing Done — indicates SRAM initialization complete (volatile, policy-gated) |

> **Note**: HAS revision history (line 1192) states "Removed SSCMAS from Slice Controller section per design feedback," but the register definition still appears in HAS Section 8.6.4.2.6. Treat as provisional — confirm with design team.

### SMMU and Memory Paging Registers (HAS Section 8.6.3, FAS Section 4)

The SRAM subsystem includes an **SMMU** (System Memory Management Unit) for address translation between VPX virtual addresses and physical SRAM/DRAM addresses.

#### SMMU Page Fault Avoidance

The SMMU **does not support on-demand paging** by HW design. To use VMEM (virtual memory), the memory mappings in page tables must be managed by FW in a predictable manner to **avoid page faults**. If a page fault occurs, it is a fatal error requiring NVU reset — there is no hardware page fault handler.

#### SRAM↔DRAM Paging Architecture

NVU supports **FW-managed SRAM paging** to/from DRAM (IMR) for models and data that exceed the 3584 KB on-chip SRAM capacity:

- **SRAM paging DMA**: A dedicated DMA engine within the SRAM-SS handles runtime encrypted paging between SRAM and IMR DRAM (RS3)
- **USB streaming DMA**: Two additional DMA engines within the USB offload logic handle data streaming to SRAM/DRAM
- **IMR page management**: FW pre-maps all required pages in the SMMU page tables before starting inference, then uses the SRAM paging DMA to swap SRAM slices to/from IMR as needed
- **Encryption**: All DRAM paging traffic is encrypted (IMR protection) — only SRAM contents are in plaintext

> **Key Constraint**: Because the SMMU cannot handle page faults, FW must ensure all SMMU page table entries are valid before any DMA or VPX access. Missing mappings cause unrecoverable page fault errors.

### DMA_MISC — DMA Channel Control Register (HAS Section 8.11)

The DMA subsystem uses Synopsys **DW_axi_dmac** (version **2.00a**). The Boot DMA controller (Section 8.11) has **8 channels** (`DMAX_NUM_CHANNELS=8`), with per-channel DMA_CTL_CH[0..7] control registers. The DMA_MISC block at `0xF390_0000` manages DMA traffic routing (root-space selection, snoop attributes, internal/external memory transfer modes). Offset within DMA_MISC is listed as **"TBD"** in the HAS itself.

> **Note**: The **SIODMA** (Section 8.8) is a separate DMA controller with 4 channels, of which only 3 are active (Ch0 unused). Do not confuse with Boot DMA's 8 channels.

#### DMA Channel Control Register (per-channel, from dma/SKILL.md — authoritative)

| Bits | Name | Access | Default | Description |
|------|------|--------|---------|-------------|
| 1:0 | TRANSFER_MODE | R/W | 0 | `0`: Src Internal, Dst Internal; `1`: Src Internal, Dst External; `2`: Src External, Dst Internal; `3`: Src External, Dst External |
| 2 | Reserved | RO | 0 | — |
| 4:3 | RD_RS | R/W | 0 | Read Root-Space: `0` = RS0 (Host DRAM), `3` = RS3 (IMR DRAM). Other values blocked by HW. |
| 6:5 | WR_RS | R/W | 0 | Write Root-Space: `0` = RS0 (Host DRAM), `3` = RS3 (IMR DRAM). Other values blocked by HW. |
| 7 | Reserved | RO | 0 | — |
| 8 | RD_NON_SNOOP | RWO | 0 | `0`: Read transactions snooped in IA cache; `1`: Not snooped |
| 9 | WR_NON_SNOOP | R/W | 0 | `0`: Write transactions snooped in IA cache; `1`: Not snooped |
| 10 | LLI_MODE | R/W | 0 | `0`: Descriptors in internal memory; `1`: Descriptors in external memory (DRAM) |
| 31:11 | Reserved | RO | 0 | — |

#### DMA Security Controls — BLOCK_RS0 and RS0_DISABLE (HAS Section 14.9.1)

The DMA_MISC block enforces security through root-space access controls:

- **BLOCK_RS0**: Originally a bit in DMA_MISC, this security control was **removed from DMA misc registers** as this functionality is moved under global security control (`RS0_DISABLE`) per HAS design feedback. BLOCK_RS0 should no longer be used in DMA_MISC — use RS0_DISABLE instead.
- **RS0_DISABLE**: Once set by FW (via MISC registers), the Boot/IO DMA must **block all RS0 transactions** (error-terminated). Security logic: if `RS0_DISABLE` is asserted AND `TRANSFER_MODE[1:0] != 0x0` (i.e., external transfer) AND `(RD_RS || WR_RS) == 0x0` (targeting RS0 / Host DRAM), then the AxADDR is redirected to an error-termination address. This prevents the DMA from accessing Host DRAM after the FW loading phase, enforcing the security boundary for NVU's isolated execution environment.

> **Security Note**: After NVU firmware loading completes, RS0_DISABLE is set to cut off DMA transfers to/from Host DDR (RS0). Only RS3 (IMR DRAM) access remains available for runtime encrypted paging.

#### DMA Configuration Summary (HAS Section 8.11)

| Parameter | Value |
|-----------|-------|
| IP | Synopsys DW_axi_dmac |
| IP Channels (max) | 8 (Synopsys IP capacity) |
| Boot DMA Instantiated | 8 channels (all active, DMAX_NUM_CHANNELS=8) |
| SIODMA (separate IP, Section 8.8) | 4 channels instantiated, 3 active (Ch0 unused) |
| AXI data width | 64-bit (`DMAX_M_DATA_WIDTH=64`, HAS 8.11.1) |
| Max burst length | 8 (`DMAX_CH(x)_MAX_AMBA_BURST_LENGTH=8`, HAS 8.11.1) |
| LLI support | Yes (TRANSFER_MODE bit) |
| Internal base address | `0xF380_0000` (DMA), `0xF390_0000` (DMA_MISC) |

---

## SHA-384 Hash Engine Registers (HAS Section 8.6, SVG: SHA_One_Time_Flow)

The SHA-384 hash engine is part of the SRAM subsystem (SRAMSS) and is used for firmware integrity verification during secure boot and runtime. It is reused from the CSME IP block. The SHA AXI initiator runs at 400 MHz and targets SRAM slices directly.

### SHA Control Registers

| Register | Description |
|----------|-------------|
| **PIBBA** | SHA Pipe Input Base Buffer Address — points to source data in SRAM |
| **PIBS** | SHA Pipe Input Buffer Size — size of data chunk to hash |
| **SHACTL** | SHA Control Register — starts operation, selects algorithm, controls multi-chunk mode |
| **SHASTS** | SHA Status Register — poll `BUSY` bit for completion |
| **PIBFPI** | SHA Pipe Input Buffer Finished Pointer Index — tracks completed hash fragment position in multi-chunk mode |

> **Summary**: The SHA-384 hash engine exposes SHACTL, SHASTS, PIBBA, PIBS, and PIBFPI registers for firmware integrity verification during secure boot and runtime.

### SHACTL Bitfields

| Field | Description |
|-------|-------------|
| `SHACTL.EN` | Set to `1` to start SHA operation |
| `SHACTL.ALGO` | Algorithm select: `0x3` = SHA-384 |
| `SHACTL.HFM` | Hash Fragment Mode: `0x0` = Last Chunk, `0x2` = First Chunk (multi-chunk >64KB) |
| `SHACTL.RSM` | Resume mode — used for multi-chunk SHA resume flow |

### SHA Operation Flow (from SVG: f1.SHA_One_Time_Flow)

1. NVU_FW configures `PIBBA` with source SRAM address
2. NVU_FW sets `PIBS` with data size
3. NVU_FW writes `SHACTL.EN=1, SHACTL.ALGO=0x3` to start
4. Poll `SHASTS.BUSY` until clear
5. Read hash result from SHA output buffer

> **Multi-chunk flow** (>64KB, SVG: f2.SHA_Resume_Flow): First chunk uses `SHACTL.HFM=0x2`, intermediate chunks use `SHACTL.RSM`, last chunk uses `SHACTL.HFM=0x0`.

### SHA Interrupt

| IRQ | Source | Description |
|-----|--------|-------------|
| 89 | SHA | SHA operation complete (part of SRAMSS IRQ group, HAS Section 8.1) |

---

## IOSF Sideband Interface (HAS Section 8.13)

NVU communicates with the SoC fabric via IOSF-SB (Sideband). The SBEP target port is defined in the IOSF SB messages specification. The IOSF2AXI bridge exposes a 64KB private config space (PVT CFG extension) accessible via IOSF sideband messages (CRRd opcode 0x06, CRWr opcode 0x07), used for bridge configuration and platform-specific setup that is not exposed through standard PCI config space.

| Feature | Details |
|---------|---------|
| Message types | MRd (0x00), MWr (0x01), CfgRd (0x04), CfgWr (0x05), CRRd (0x06), CRWr (0x07), Cpl (0x20), CplD (0x21) |
| Opcode masking | Configurable — controls which opcodes NVU accepts |
| Payload Bus Width | 8 |
| Port ID Width | 16 |
| Port ID Count | 1 |
| Sideband clock | Tied to NVU IP clock domain |

> **Note**: NVU supports messages with EH=0. All SB messages are handled via the IOSF2AXI Bridge. Individual SB register offsets are in the OSXML register spec (HAS Section 16 reference), not in the HAS prose.

---

## Interrupt Map Summary (HAS Section 8.1)

VPX2 has **109 interrupt indices** (0–108) mapped across internal modules, with ~103–105 actively defined. Key interrupt assignments:

| IRQ Range | Module | Count | Key IRQ Names | Notes |
|-----------|--------|-------|---------------|-------|
| 0–13 | ARCv2VPX | 12 | Reset, MemoryError, InstructionError, EV_MachineCheck, EV_TLBMissI/D, EV_ProtV, EV_PrivilegeV, EV_SWI, EV_Trap, EV_DivZero, EV_DCError, EV_Misaligned | CPU exceptions (indices 10, 14–15 unused) |
| 16–22 | ARCv2VPX | 7 | Timer0/1 (16–17), Reserved (18–19), PerfMon (20), STU Error/Done (21–22) | Internal timers + STU |
| 23–34 | IPC | 12 | HOST (23), VOD_HOST (24), CSE/PMC/CNVI/ACE/ESE/BT/ISH (25–31), SPARE0–2 (32–34) | Inter-Processor Communication |

> **IPC Channel Architecture (HAS Section 8.9)**: NVU has **12 IPC channels** organized as **2 HOST channels** (HOST at IRQ 23, VOD_HOST at IRQ 24) + **7 non-host channels** (CSE, PMC, CNVI, ACE, ESE, BT, ISH at IRQs 25–31) + **3 spare IPCs** (SPARE0–2 at IRQs 32–34). Each IPC channel uses a **doorbell register** following the Standard Long Format per the Embedded Engines IPC HAS. The spare IRQs are pre-allocated for future IPC channel expansion.
| 35–46 | CRPM | 12 | RESETPREP (35), WAKE (37), RESOURCE_OWN_ACK (38), PCIDEV (39), PMU2IOAPIC (40), VISION_SERVICE (42), TELEMETRY_SERVICE (43), SPARE0–4 (36,41,44–46) | Clock/Reset/Power Management |
| 47–54 | TIMERS | 8 | WDT (47), HPET0–2 (48–50), SPARE0–3 (51–54) | Watchdog + HPET timers |
| 55–58 | DMA | 4 | DMA IRQ (55), SPARE0–2 (56–58) | Boot DMA (4 IRQs, not 8) |
| 59–62 | FABRIC | 4 | MAIN_FABRIC (59), SPARE0–2 (60–62) | Interconnect errors |
| 63–64 | GPIO | 2 | GPIO IRQ (63), SPARE (64) | GPIO (2 IRQs, not 16) |
| 65–70 | I2C | 6 | I2C0/1/2 (65–67), SPARE0–2 (68–70) | 1 per instance + 3 spares |
| 71–74 | I3C | 4 | I3C0/1 (71–72), SPARE0–1 (73–74) | 1 per instance + 2 spares |
| 75–78 | SPI | 4 | SPI0/1 (75–76), SPARE0–1 (77–78) | 1 per instance + 2 spares |
| 79–84 | UART | 6 | UART0/1/2 (79–81), SPARE0–2 (82–84) | 1 per instance + 3 spares |
| 85–86 | SBEP | 2 | SBEP US (85), SBEP DS (86) | Sideband endpoint (2 IRQs, not 4) |
| 87–92 | SRAMSS | 6 | SRAM_FABRIC (87), SMMU (88), SHA (89), SPARE0–2 (90–92) | SRAM sub-system (6 IRQs, not 8) |
| 93–98 | ISP | 6 | ALTEK ISP (93), PHY SHARING (94), CSI2 HC (95), SPARE0–2 (96–98) | Image Signal Processor (6 IRQs, not 8) |
| 99–106 | USB | 8 | SIO (99), DPTZR (100), SIODMA (101), UDF_UAL (102), MSIF2IPI (103), MJPEG (104), CBUF (105), LL (106) | USB/Camera pipeline (8 IRQs, not 4) |
| 107–108 | ARCSYNC | 2 | IRQ0 (107), IRQ1 (108) | ARC synchronization (2 IRQs, not 4) |

> **Note**: Exact IRQ-to-MSI vector mapping is platform-specific and configured via IOSF2AXI bridge parameter `NUM_MSI_VECTORS=0x20` (bridge internal routing table capacity = 32 entries). This is **not** the number of MSI vectors exposed to the OS — the device exposes only **1 MSI vector** (MSI_MULT_MSG_CAP=0). All 109 IRQs are multiplexed through the single vector via WIRE2MSI.

---

## NPX6 Debug Registers (HAS Section 8.4)

The NPX6-1K DSP core has debug registers accessible at `0xF620_0000`:

| Sub-block | Description | Notes |
|-----------|-------------|-------|
| ROM Table | CoreSight ROM Table for debug discovery | Standard ARM CoreSight format |
| ARCTrace | ARC trace buffer for instruction/data tracing | Per Synopsys ARC debug manual |
| L1 Core | NPX6 L1 core debug/status registers | Per Synopsys NPX6 databook |

> **Note**: Individual register offsets within NPX_DEBUG are per the Synopsys NPX6-1K debug specification, not detailed in the NVU HAS.

---

## Soft-Strap Configuration (HAS Section 19)

These fuses/soft-straps control PCI enumeration and platform identity:

| Strap Name | Default | Description |
|------------|---------|-------------|
| `NVU_BaseClass_code_func1_SoftStrap` | `0x00` | PCI Base Class Code (byte at CC+2) |
| `NVU_SubClass_code_func1_SoftStrap` | `0x00` | PCI Sub-Class Code (byte at CC+1) |
| `NVU_Reg_prg_intf_func1_SoftStrap` | `0x00` | PCI Programming Interface (byte at CC+0) |
| `RevisionId0` | `0x00` | PCI Revision ID |
| `NVU_Softstrap_select_disable` | `1` | Disable NVU at SoC level |
| Boot mode straps | Platform-specific | FW boot source selection |

> **Note**: All class code straps default to 0, meaning the actual PCI class code is configured at the platform integration level (not hardcoded in the NVU IP).

---

## PythonSV Access Patterns

> **Pending PythonSV namespace allocation.**
>
> NVU PythonSV register paths have not been defined in the HAS. Once the PythonSV namespace
> is allocated for the NVU IP, access patterns will follow the standard form:
>
> ```python
> # Template — replace with actual NVU PythonSV namespace when available
> # import pysvtools.pciedecode as pcie
> #
> # nvu = pcie.get_device(bus=0, dev=TBD, func=0)
> #
> # # Read PCI config
> # vid = nvu.cfg.read(0x00) & 0xFFFF
> # did = nvu.cfg.read(0x02) & 0xFFFF
> #
> # # Read HOST_IPC (BAR0 + 0x0000)
> # ipc_val = nvu.mmio.read(0x0000)
> #
> # # Note: Only HOST_IPC (0x0000-0x0FFF), PEER_IPC (0x10000-0x16FFF),
> # # and SEC_REG (0x18000-0x18FFF) are host-accessible via BAR0.
> ```

---

## Config Checkout Checklist

Use this for initial platform bring-up:

- [ ] NVU device enumerates on PCI bus (check `lspci` / Device Manager)
- [ ] Vendor ID reads `0x8086`
- [ ] Device ID matches expected platform DID (check platform soft-strap table)
- [ ] Revision ID matches `RevisionId0` strap (default `0x00`)
- [ ] Class Code matches platform strap configuration (default `0x000000` if not overridden)
- [ ] BAR0 is allocated and non-zero (expected 64KB region)
- [ ] HOST_IPC region at BAR0+0x0000 is accessible (read without fault)
- [ ] MSI capability is present and MSI_EN can be set (1 vector; MSI_MULT_MSG_CAP=0)
- [ ] MSI-X capability is NOT present (disabled by design)
- [ ] LTR capability is NOT present (disabled by design)
- [ ] PCI Idle capability is present (`ENABLE_PCI_IDLE_CAP=0x3`)
- [ ] NVU_DISABLE strap is 0 (NVU not fused off)
- [ ] Firmware status indicates ready state (via HOST_IPC mailbox — protocol TBD)

---

## What's TBD (Not in HAS v1.0)

The following items require the external OSXML/HTML register spec (HAS Section 16 reference) or Synopsys IP datasheets:

| Category | What's Missing | Where to Find |
|----------|---------------|---------------|
| PCI Config register defaults | CMD, STS, SVID, SDID default values | OSXML register spec |
| HOST_IPC register map | Individual mailbox register offsets and bitfields | OSXML register spec (Host View) |
| PEER_IPC register map | Per-peer IPC register offsets | OSXML register spec (FW View) |
| SEC_REG register map | Security register offsets and bitfields | OSXML register spec |
| CRPM register map | Clock/Reset/Power Management registers | OSXML register spec |
| MISC register map | Miscellaneous registers at `0xF320_0000` (security controls moved here per HAS) | OSXML register spec |
| DMA core registers | DW_axi_dmac channel registers (beyond DMA_MISC) | Synopsys DW_axi_dmac databook |
| DMA_MISC offset | Exact offset of Channel Control Register within DMA_MISC | HAS says "TBD" |
| SRAM register offsets | Exact offsets of SSCR/SSCEL/SSCMAS within SRAMSS_CFG | OSXML register spec |
| IO Peripheral registers | I2C, I3C, SPI, UART, GPIO internal register maps | Synopsys DW IP datasheets |
| NPX6 debug register offsets | ROM Table, ARCTrace, L1 Core register offsets | Synopsys NPX6-1K debug spec |
| PythonSV paths | NVU register tree namespace | PythonSV namespace allocation |

### Resolved from HAS (previously TBD)

| Item | Resolved Value | HAS Source |
|------|---------------|------------|
| DMA AXI data width | 64-bit (`DMAX_M_DATA_WIDTH=64`) | HAS Section 8.11.1 |
| DMA Max burst length | 8 (`DMAX_CH(x)_MAX_AMBA_BURST_LENGTH=8`) | HAS Section 8.11.1 |
| SSCR bitfields | Corrected: RMWPIPESTG, ECCENB, DSOVREN, DSOVRVAL, SDEN, MEMPIPEN, DSMINDUR, ECCSCRUB | HAS Section 8.6.4.2.6 |
| SSCEL bitfields | Corrected: CNT[15:0], CERREV[16], UCERREV[31] | HAS Section 8.6.4.2.6 |
| SSCMAS bitfields | Corrected: HWZRDONE[31] (provisional — removal noted in HAS rev history) | HAS Section 8.6.4.2.6 |

---

## See Also

- [dma/SKILL.md](../dma/SKILL.md) — DMA engine registers, DMA_MISC bitfield (authoritative)
- [inference/SKILL.md](../inference/SKILL.md) — VPX2/NPX6 compute registers
- [power/SKILL.md](../power/SKILL.md) — PGCB domains, clock gating registers
- [platform/SKILL.md](../platform/SKILL.md) — PCI config, BAR layout, partition table
- [bios/SKILL.md](../bios/SKILL.md) — BIOS register programming (PCICFGCTR1 at PCR+0x200, PMCTL at PCR+0x1D0, D0I3_MAX_POW_LAT_PG_CONFIG at CFG+0xA0)
- [firmware/SKILL.md](../firmware/SKILL.md) — HOST_IPC mailbox registers

## Related Sub-Skills

- [fv-nvu/firmware](../firmware/SKILL.md) — FW architecture, boot ROM, secure boot, IPC protocol
- [fv-nvu/debug](../debug/SKILL.md) — Debug interfaces, RAS, DTF trace, VISA, telemetry


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:34 | Facts added: 2464


### Additional HAS Details (1 facts)

#### ARCSYNC Semaphore and Barrier Support

- The ARCSYNC block provides support for semaphores and barriers (8.5.2 ARCSYNC Features)


### Boot and Reset Sequences (18 facts)

| Field | Bits | Access | Reset | Description |
|-------|------|--------|-------|-------------|
| `PTN_PORT_CONFIG.RSVD` | [31:2] | RO | `0x00000000` | RSVD: Reserved |
| `PTN_ISM_CONFIG.ISMIdleEntryCnt` | [15:0] | RW | `0x0000` | This field contains the number of cycles for the agent ISM remained in ACTIVE state when all the idle conditions are met |
| `PTN_ISM_CONFIG.RSVD` | [31:16] | RO | `0x0000` | RSVD: Reserved |
| `PTN_EH_STATUS.PErr_CH0` | [0] | RW/1C/V | `0x0` | If set, PtN NAP Error Handler has received and dropped an erroneous Posted transaction. Cleared by writing a 1'b. |
| `PTN_EH_STATUS.NPErr_CH0` | [1] | RW/1C/V | `0x0` | If set, PtN NAP Error Handler has received an erroneous NP transaction. If the error was an Unexpected Completion (UC) o |
| `PTN_EH_STATUS.CPLErr_CH0` | [2] | RW/1C/V | `0x0` | If set, the Error Handler has received and dropped an erroneous Completion transaction. Cleared by writing a 1'b1. |
| `PTN_EH_STATUS.RSVD` | [31:24] | RO | `0x00` | RSVD: Reserved |
| `PTN_AER_MSG_DW1.RSVD1` | [0] | RO | `0x0` | RSVD: Reserved |
| `PTN_AER_MSG_DW1.ANF` | [1] | RO | `0x0` | Advisory Non-Fatal |
| `PTN_AER_MSG_DW1.RSVD2` | [19:2] | RO | `0x00000` | RSVD: Reserved |
| `PTN_AER_MSG_DW1.URES` | [20] | RO | `0x0` | Unsupported Request Error Status |
| `PTN_AER_MSG_DW1.RSVD3` | [21] | RO | `0x0` | RSVD: Reserved |
| `PTN_AER_MSG_DW1.UIES` | [22] | RO | `0x0` | Uncorrectable Internal Error Status |
| `PTN_AER_MSG_DW1.RSVD4` | [31:23] | RO | `0x000` | RSVD: Reserved |

- Scan Parameters Name Scan Parameters Comment : Interface Parameters for SCAN Symbol Type Default Value SoC Modifiable Description NUM_CLKGENCTRL uint32 1 no Number of Clock GEN Control NUM_CLKGENCTRLEN uint32 1 no Number of Clock GEN Control Enable NUM_BYPRST_B uint32 1 no Number of Bypass Reset Bar NUM_BYPPST_B uint32 1 no Number of Bypass Preset Bar SCAN_CTL_WIDTH uint32 1 no Scan control input width SCAN_DATA_WIDTH uint32 1 no Scan data channel width NUM_RAM_BYPSEL uint32 1 no Number of Ram Bypass Select NUM_BYPLATRST_B uint32 1 no Number of Bypass Latch Reset Bar NUM_RSTBYPEN uint32 1 no Maximum value of NUM_BYPRST_B and NUM_BYPLATRST_B *(HAS §4 IP Configuration > 4.3 Interfaces > 4.3.13 DFT Interfaces > 4.3.13.1 Scan)*


### Camera Interface (282 facts)

### Camera Interface Registers

#### MIPI CSI-2 Camera Interface

### Overview

The NVU Camera Interface supports MIPI CSI-2 input via shared C/D-PHY resources with the IPU. Register-based arbitration controls ownership of each PHY, and dedicated NVU registers manage claim, ownership status, sticky tracking, and soft reset behavior.

---

#### PHY Sharing — Register Summary (8.7.2.1.1 Registers)

The following registers in NVU support CDPHY sharing between NVU and IPU:

| Name | Access | Description |
|------|--------|-------------|
| `NVU_claim` | RW | Control register written by NVU FW, read by CDPHY HW. Used to claim ownership of shared C/D-PHY resources. |
| `CDPHY_owner` | RO | Updated by HW; read by IPU or NVU FW to verify ownership acquisition. |
| `CDPHY_force_ownership` | RW | Contains `TAP_override` field; routed to the final MUX that determines which unit controls the C/D-PHY. |
| `CDPHY_owner_sticky` | RO (hidden) | Tracks NVU usage of C/D-PHY since the last OS boot. |
| `Soft_reset` | RW | Resets the Arbitration Logic and all registers in the power-gated domain. Use only for unexpected errors. |

> **Note:** `CDPHY_A` and `CDPHY_B` can operate together in aggregated mode. In this mode, the claim and ownership must be asserted/relinquished for both PHYs, and the respective bits must be set in the claim registers. (HAS 8.7.2.1.1)

---

#### `NVU_claim` Register Fields (HAS 8.7.2.1.1)

| Field | Bits | Access | Reset | Description |
|-------|------|--------|-------|-------------|
| `NVU_claim_A` | 0:0 | RW | 0 | `0` = NVU FW does not want to use shared CDPHY_A; `1` = NVU FW wants to use shared CDPHY_A |
| `NVU_claim_B` | 1:1 | RW | 0 | `0` = NVU FW does not want to use shared CDPHY_B; `1` = NVU FW wants to use shared CDPHY_B |
| `NVU_claim_C` | 2:2 | RW | 0 | `0` = NVU FW does not want to use shared CDPHY_C; `1` = NVU FW wants to use shared CDPHY_C |

---

#### PHY Ownership Arbitration Behavior (HAS 8.7.2.1 / Chapter 4: 8.1.1)

- `IPU_claim` and `NVU_claim` registers are written by IPU FW and NVU FW respectively to negotiate ownership of a specific C/D-PHY. (8.1.1)
- The `CDPHY_owner` registers are updated by HW; IPU or NVU FW reads them to verify if ownership has been acquired. (8.1.1)
- The `TAP_override` field from `CDPHY_force_ownership` is routed to the final MUX that determines which unit controls the C/D-PHY. (8.1.1)
- The `CDPHY_owner_sticky` hidden register tracks NVU usage of the C/D-PHY since the last OS boot. (8.1.1)
- HW monitors `CDPHY_owner` registers and interrupts NVU FW via `NVU_ownership_release_irq` when they change. (8.1.1)
- The `Soft_reset` register resets the Arbitration Logic and all registers in the power-gated domain; it should only be used for unexpected errors. (8.1.1)

---

#### Register Domain and Clock Details (HAS 8.7.2.1)

- The `IPU_claim` register resides in the IPU power-gated domain and is written by IPU SW using `is_clk`.
- The `NVU_claim` register resides in the NVU unit, written by NVU FW using NVU clock; its output is sent as asynchronous wires to IPU's always-on domain.
- IPU SW and NVU FW may write to their respective claim registers (`IPU_claim` and `NVU_claim`) to claim ownership of a CDPHY.

> For IPU-side registers, refer to _"InSys sharing CDPHY with NVU HAS"_ in the reference documents. (HAS 8.7.2.1.1)

---

### Camera Sensor Control — MCLK (HAS Chapter 4: 8.1.3.1)

- NVU FW is responsible for controlling the MCLK enable via the HW-provided register.
- The clock selection from NVU is unused.

---

### Memory Map — MIPI ISP Register Region (HAS 8.2.2)

| Region | Block | Sub-Region | Size (KB) | Start Address | End Address |
|--------|-------|------------|-----------|---------------|-------------|
| Register Targets – MIPISS | ALTEK_ISP | ALTEK_ISP | 512 | `0xF7000000` | `0xF7080000` |

---

### SIO Peer-to-Peer — Remote Peer IP BDF Registers (HAS 8.4.1.2)

- New `SIO_RPIBDFx` registers are provided to allow IOSF2AXI bridge forwarding of SIO messages based on BDF (Target Route ID).
- FW shall program the `SIO_RPIBDFx` registers with the BDF values of the corresponding peer IPs (i.e., `XHCI_CAM` and IPU).
- Refer to _TTL PCD Register and Memory Mappings_ for the BDF values allocated for `XHCI_CAM` and IPU.


### DMA Architecture (53 facts)

#### DMA Architecture

### Overview

The NVU incorporates two DMA controller instances: a **Boot DMA** (§8.11 DMA Controller) and a **SIO DMA** embedded within the USB Video Offload Logic (§8.8.2.1.2.4 SIO DMA Controller). Both are derived from a common DesignWare DMA IP but differ in configuration parameters.

---

#### Common DMA IP Parameters (Both Instances)

The following parameters apply to both Boot DMA and SIO DMA instances (§8.11.1, §8.8.2.1.2.4):

| Parameter | Type | Description |
|---|---|---|
| `DMAX_CH_MEM_EXT` | uint32 | Use External RF for FIFO memory (value: 1) |
| `DMAX_CH_MEM_REGOUT` | uint32 | No flop on FIFO memory output (value: 0) |
| `DMAX_DEBUG_PORTS_EN` | uint32 | Debug ports for VISA observability (value: 1) |

---

#### Boot DMA Configuration Parameters (§8.11.1 DMA Configuration)

| Parameter | Type | Value | Description |
|---|---|---|---|
| `DMAX_SLVIF_MODE` | uint32 | 0 | AHB target for register access |
| `DMAX_CH1_SHADOW_REG_EN` | uint32 | 1 | Include shadow registers for channel 1 |
| `DMAX_CH1_LLI_WB_EN` | uint32 | 1 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH1) |
| `DMAX_CH2_SHADOW_REG_EN` | uint32 | 1 | Include shadow registers for channel 2 |
| `DMAX_CH2_LLI_WB_EN` | uint32 | 1 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH2) |
| `DMAX_CH3_SHADOW_REG_EN` | uint32 | 1 | Include shadow registers for channel 3 |
| `DMAX_CH3_LLI_WB_EN` | uint32 | 1 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH3) |
| `DMAX_CH4_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 4 |
| `DMAX_CH4_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH4) |
| `DMAX_CH5_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 5 |
| `DMAX_CH5_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH5) |
| `DMAX_CH6_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 6 |
| `DMAX_CH6_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH6) |
| `DMAX_CH7_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 7 |
| `DMAX_CH7_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH7) |
| `DMAX_CH8_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 8 |
| `DMAX_CH8_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH8) |

---

#### SIO DMA Configuration Parameters (§8.8.2.1.2.4 SIO DMA Controller)

| Parameter | Type | Value | Description |
|---|---|---|---|
| `DMAX_SLVIF_MODE` | uint32 | 2 | APB target for register access |
| `DMAX_CH1_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 1 |
| `DMAX_CH1_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH1) |
| `DMAX_CH2_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 2 |
| `DMAX_CH2_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH2) |
| `DMAX_CH3_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 3 |
| `DMAX_CH3_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH3) |
| `DMAX_CH4_SHADOW_REG_EN` | uint32 | 0 | Include shadow registers for channel 4 |
| `DMAX_CH4_LLI_WB_EN` | uint32 | 0 | Enable write-back of channel status registers after completing every block of multi-block LLI transfer (CH4) |

---

#### DMA Channel Control Register (§8.11.2 DMA Misc Logic)

- **Offset:** TBD
- The register fields below control traffic routing from the DMA towards the NVU fabric.

| Bits | Access | Default | Field | Description |
|---|---|---|---|---|
| 1:0 | RW | 0 | `TRANSFER_MODE` | Transfer Mode Memory Control. Bit 1 controls the Source Memory/Peripheral location relative to NVU. Bit 0 controls the Destination Memory/Peripheral location relative to NVU. |
| 4:3 | RW | 0 | `RD_RS` | Read Root-Space. Values other than defined enumerations are not allowed and shall be blocked by HW. `0` = Read transaction (default); see enumeration table for other values. |
| 6:5 | RW | 0 | `WR_RS` | Write Root-Space. Values other than defined enumerations are not allowed and shall be blocked by HW. `0` = Write transaction (default); see enumeration table for other values. |
| 8 | RWO | 0 | `RD_NON_SNOOP` | Read Non-Snoop Attribute. `0` = Read transaction from NVU should be snooped in IA cache. `1` = Read transaction from NVU should not be snooped in IA cache. |
| 9 | RW | 0 | `WR_NON_SNOOP` | Write Non-Snoop Attribute. `0` = Write transaction from NVU should be snooped in IA cache. `1` = Write transaction from NVU should not be snooped in IA cache. |
| 10 | RW | 0 | `LLI_MODE` | `0` = Descriptors are in internal memory. `1` = Descriptors are in external memory (DRAM). |

---

#### DMA Misc Logic — Behavioral Notes (§8.11.2 DMA Misc Logic)

- The different fields of the DMA Channel Control Register are used by HW to control traffic routing from the DMA towards the NVU fabric.
- **Address Translation Risk:** `AWADDR[31:0]` is routed to the ATT (Address Translation Table). If programmed with an address falling between `MMIO_BASE` and `LIMIT`, the ATT may translate it and send an incorrect address to DRAM. Software must program DMA addresses with care to avoid this condition.
- **`BLOCK_RS0` Removal:** The `BLOCK_RS0` bit has been removed from DMA misc registers. This functionality is superseded by the global security control bit `RS0_DISABLE` (§8.11.2, §8.11.5).

---

#### DMA Programming Restrictions (§8.11.5 DMA Programming Restrictions)

- `BLOCK_RS0` configuration previously defined in MISC registers has been removed from DMA misc; the feature is now controlled via `RS0_DISABLE` under global security control.

---

#### Host DMA Access Control Policy Registers (CRIF: nvu_sec_reg_top)

These registers configure SAI-based read and write access policies for the Host DMA register space. All registers reset on `FUNCRST`.

| Name | Offset | Size | Reset (SAI_MASK) | Access | Description |
|---|---|---|---|---|---|
| `NVU_HOST_DMA_RAC_LO` | 0x9200 | 32 | `0x0100001E` | RW | Read Access Control Policy (low). Bit-vector determining which agents are allowed read access to registers in this policy group based on SAI value. |
| `NVU_HOST_DMA_RAC_LO.SAI_MASK` | 0x9200 [31:0] | 32 | `0x0100001E` | RW | SAI mask for read access (low word). |
| `NVU_HOST_DMA_RAC_HI` | 0x9204 | 32 | `0x00080C00` | RW | Read Access Control Policy (high). |
| `NVU_HOST_DMA_RAC_HI.SAI_MASK` | 0x9204 [31:0] | 32 | `0x00080C00` | RW | SAI mask for read access (high word). |
| `NVU_HOST_DMA_WAC_LO` | 0x9208 | 32 | `0x0100001E` | RW | Write Access Control Policy (low). Bit-vector determining which agents are allowed write access to registers in this policy group based on SAI value. |
| `NVU_HOST_DMA_WAC_LO.SAI_MASK` | 0x9208 [31:0] | 32 | `0x0100001E` | RW | SAI mask for write access (low word). |
| `NVU_HOST_DMA_WAC_HI` | 0x920C | 32 | `0x00080C00` | RW | Write Access Control Policy (high). |
| `NVU_HOST_DMA_WAC_HI.SAI_MASK` | 0x920C [31:0] | 32 | `0x00080C00` | RW | SAI mask for write access (high word). |

- Each `SAI_MASK` field is a 32-bit bit-vector; a set bit indicates the corresponding SAI agent is permitted access.
- Read and write access policies are independently configurable via `RAC` and `WAC` register pairs respectively.
- The `_LO` and `_HI` suffix registers together form a 64-bit SAI mask covering agents 0–63.


### DSP Core (VPX2) (8 facts)

#### VPX2 Interrupt Configuration

##### UDF_UAL IRQ
(HAS 8.1.1 VPX2 Interrupts)

- The UDF_UAL IRQ is an interrupt from the UAL sub-IP and is **pulse-type by default**
- A register-level configuration option exists to switch the interrupt to **level-sensitive** mode
- To enable level interrupt mode, **Bit 2 of the `UDF_UAL_CTRL` register must be set to 1**

##### ARCSYNC IRQ Support
(HAS 8.5.2 ARCSYNC Features)

- ARCSYNC supports raising a **level-sensitive interrupt** on any processor within the cluster
- Level-sensitive interrupts can also be raised to cores in **other clusters**
- Supported processor targets include: Host processor, multiple ARC HS / VPX / EV clusters

---

#### VPX2 Memory Map

##### Addressable Memory Regions
(HAS 8.2.1 VPX2 Addressable Memory Map)

| Region | Size | Start Address | End Address | Memory Type | Target |
|--------|------|---------------|-------------|-------------|--------|
| 15 | 256 MB | 0xF000_0000 | 0x1_0000_0000 | Peripheral (Non-Cacheable) | I/O Peripherals and Registers |

##### Register Target Sub-Regions
(HAS 8.2.2 VPX2 Memory Map)

| Region | Block | Sub-Region | Size (KB) | Start Address | End Address |
|--------|-------|------------|-----------|---------------|-------------|
| Register Targets – SRAMSS | SRAMSS_CFG | SRAMSS_CFG | 1024 | 0xF5000000 | 0xF5100000 |
| Register Targets – NPX | NPX_DMI | NPX_DMI | 32 | 0xF6000000 | 0xF6008000 |
| Register Targets – USBSS | — | — | — | — | — |

> **Note:** Full address range details for the USBSS register target region are not specified in the available HAS data.


### GPIO and Pin Mux (16 facts)

#### GPIO and Pin Mux

##### GPIO Implementation Overview
(HAS §8.21 GPIO > 8.21.1 Implementation Notes)

- The NVU CPU selects the behavior of pins via registers inside the NVU's GPIO unit and sends the resulting signals to the SoC's GPIO unit.

---

##### GPIO Behaviors

###### Detecting Pin Level
(HAS §8.21 GPIO > 8.21.2 GPIO Behaviors > 8.21.2.1 Detecting Pin Level)

- NVU firmware can read the pin level using the **GPLR** register.
- The GPLR register can be read even if the GPIO pin is configured as an output.
  - Note: Per the GPLR register description, the GPLR value is architecturally valid only for input pins; firmware should account for this constraint when reading output-configured pins.

###### Glitch Filtering
(HAS §8.21 GPIO > 8.21.2 GPIO Behaviors > 8.21.2.2 Glitch Filtering)

- Glitch filtering is supported on GPIO and is enabled on a per-pin basis via the **GFBR** register.

---

##### GPIO Flows

###### Input Function — Register Access Sequencing
(HAS §8.21 GPIO > 8.21.6 GPIO Flows > 8.21.6.1 Input Function)

- An additional **busy-poll** step is performed before every register read or write operation.
- This ensures that the previously issued register RD/WR has completed after synchronization to the RTC domain before a new access is issued.

---

##### GPIO Restrictions
(HAS §8.21 GPIO > 8.21.7 GPIO Restrictions)

- Firmware must ensure that bits in the **GFER** (GPIO Falling-Edge detect Register) and **GRER** (GPIO Rising-Edge detect Register) are set **only** for pins configured as input function.

---

##### Camera Sensor GPIO Sharing with IPU
(HAS §8.7 MIPI Interface Sub-System > 8.7.2.1.7 MIPI Camera Controls > 8.7.2.1.7.3 MIPI Camera GPIO Sharing with IPU)

- Camera GPIO pins must be driven by either IPU or NVU, depending on camera sensor ownership.
- **IPU** drives these pins using the SoC GPIO controller in GPIO mode (`PMode=0`), accessing GPIO registers via a DDI with the GPIO driver.
- **NVU FW**, when it holds camera sensor ownership, drives the pins' Tx by programming the corresponding pad registers in the SoC GPIO controller through **IOSF-SB**.
  - NVU FW shall not modify any other pad registers beyond those associated with the owned camera sensor pins.

(HAS §8 Chapter 4: Camera and ISP > 8.1 MIPI CSI-2 Camera > 8.1.3 Camera Sensor Control > 8.1.3.3 MIPI Camera Control via GPIO)

---

##### MIPI PHY Control/Status Registers — FORCETXSTOPMODE Fields
(HAS §8.7 MIPI Interface Sub-System > 8.7.2.1 MIPI PHY Sharing with IPU > 8.7.2.1.1 Registers)

###### NVU_PHY_P_CTRL_STS (Primary PHY Control and Status)

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| P_FORCETXSTOPMODE_DCK | 1:1 | RW | 0 | DPHY clock lane — force lane/trio module into transmit mode / generate stop state |
| P_FORCETXSTOPMODE_0 | 7:7 | RW | 0 | Force lane/trio module into transmit mode / generate stop state — Lane 0 |
| P_FORCETXSTOPMODE_1 | 8:8 | RW | 0 | Force lane/trio module into transmit mode / generate stop state — Lane 1 |

###### NVU_PHY_S_CTRL_STS (Secondary PHY Control and Status)

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| S_FORCETXSTOPMODE_DCK | 1:1 | RW | 0 | DPHY clock lane — force lane/trio module into transmit mode / generate stop state |
| S_FORCETXSTOPMODE_0 | 7:7 | RW | 0 | Force lane/trio module into transmit mode / generate stop state — Lane 0 |
| S_FORCETXSTOPMODE_1 | 8:8 | RW | 0 | Force lane/trio module into transmit mode / generate stop state — Lane 1 |

---

##### IOSF-SB Clock Parameters (GPIO / Pad Register Access Context)
(HAS §8.12 IOSF to AXI Bridge > 8.12.2 IOSF to AXI Bridge Parameters)

NVU FW accesses SoC GPIO pad registers via IOSF-SB. The relevant IOSF2AXI bridge is configured with the following parameters:

| Parameter | NVU Value |
|---|---|
| PRIM_CLK | 200 MHz |
| SIDE_CLK | 100 MHz |
| AXI_CLK | 200 MHz |
| TDEC | 0 |
| IOSF_SPEC | 1.1 |
| DS_SB_PM_MESSAGES | 1 |
| US_SB_INTR_SUPPORT | 1 |
| US_SB_PME_SUPPORT | 1 |


### IOSF Bridge (1507 facts)

### IOSF Bridge Registers

#### Overview

The IOSF Bridge provides the primary host interface for the NVU (Neural Vision Unit), including an IOSF Primary interface, an IOSF-to-AXI (IOSF2AXI) Bridge, and an IOSF Sideband (IOSF-SB) interface. Address translation, message handling, and IPC communication are managed through these blocks.

---

#### IOSF Primary Interface

### IOSF Primary Parameters
(HAS §4.3.7.1 IOSF Primary)

| Parameter | Type | Default Value | SoC Modifiable | Description |
|---|---|---|---|---|
| MultiFunctionDevice | bit | 0 | no | Multi-Function Device: Sets the default value of bit[7] in the header type register. |

---

#### IOSF-to-AXI (IOSF2AXI) Bridge

### Host Address Map
(HAS §8.2.6 Host Address Map)

- The NVU Host SW Driver BAR is mapped to FN0 of the IOSF2AXI Bridge and exposes a **64KB BAR**.
- This BAR is remapped at the IOSF2AXI Bridge to address range **0x8000_0000** via `_strap_axi_remap_address[0]` tie-off.

### IOSF2AXI Bridge Parameters
(HAS §8.12.2 IOSF to AXI Bridge Parameters)

| Parameter | NVU Value |
|---|---|
| #PRIM_CLK# | 200 |
| #SIDE_CLK# | 100 |
| #AXI_CLK# | 200 |
| #TDEC# | 0 |
| #IOSF_SPEC# | 1.1 |
| #DS_SB_PM_MESSAGES# | 1 |
| #US_SB_INTR_SUPPORT# | 1 |
| #US_SB_PME_SUPPORT# | 1 |

---

#### Address Translation Table (ATT)

### Overview
(HAS §8.2.7.1 ATT)

- The ATT (Address Translation Block) translates PCI MMIO BAR addresses into NVU internal MMIO addresses to enable host access to various address ranges within the NVU.
- Incoming host MMIO address (aligned to 4KB boundary, i.e., bits [31:12]) is compared against `StartMMIOX` and `LimitMMIOX` to generate a hit bit vector.
- The 1-hot HitVector is used to AND-OR the appropriate entry's Translate Offset/Mask value.
- Incoming MMIO address is translated only when any one of the defined address ranges in the ATT is a hit **and** the address falls within the ATT range (**0x8000_0000** to **0x8020_0000**).

### ATT Register Default Values
(HAS §8.2.7.1.2 ATT Register Default Values)

| Entry # | Valid | Access | BAR | Bar Size (KB) | Block | MMIO Base | MMIO Limit | Size (KB) | Translate Offset | Translate Mask |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | MMIO | 0x80000000 | 4 | HOST_IPC | 0x80000000 | 0x80001000 | 4 | 0xF1000000 | — |
| 1 | 1 | PVTCR | 0x80010000 | 64 | PEER_IPC | 0x80010000 | 0x80017000 | 28 | 0xF1100000 | — |
| 2 | 1 | PVTCR | — | — | SEC_REG | 0x80018000 | 0x80019000 | 4 | 0xF2000000 | 0xFFFFF000 |

> **Note:** MMIO_LIMIT for the PEER IPC entry should be `0x80017000` to accommodate ISH IPC. If 3 additional spare IPC entries are considered, the MMIO_LIMIT would become `0x8001A000`. (HAS §8.2.7.1.2)

### ATT Error Handling
(HAS §8.2.7.1.4 Error Handling)

- Translation is only applied when the incoming address is a hit within the ATT-defined ranges.
- The ATT range check is performed against bits [31:23] = `9'b100` in RTL.
- A single BAR for a single PCI function is used; 2MB is sufficient for this configuration.

---

#### IOSF Sideband (IOSF-SB) Interface

### Opcode Masking
(HAS §8.13.1 Opcode Masking)

| Message Type | Opcode Type | Opcode | Opcode Index | Hex Value |
|---|---|---|---|---|
| Register Access | Global | MRd | 0 | 8'h00 |
| Register Access | Global | MWr | 1 | 8'h01 |
| Register Access | Global | CRRd | 6 | 8'h06 |
| Register Access | Global | CRWr | 7 | 8'h07 |

### SB MSGIF Block
(HAS §8.13.2 SB MSGIF Block)

The MSGIF block houses the following registers:
- Hammock Harbor Time-stamp received with LocalSync Message
- Hammock Harbor Attributes, Control and Status registers for HH message handling
- Up-stream Address and Attribute registers

The MSGIF block also has an APB target port for NVU FW to access the registers, and a generic avail/get interface with the IOSF2AXI bridge for sending and receiving downstream and up-stream messages.

### SB Message Handling with EH=0
(HAS §8.13.3 SB Message Handling with EH=0)

- NVU supports messages with `EH=0`.
- NVU checks all downstream SB messages for `EH=0`.
- All SB messages are handled via the IOSF2AXI Bridge.
- For registers whose behavior is affected by `EH=0`, the appropriate handling policy is applied as specified.

### Supported SB Messages
(HAS §8.13.5 List of SB Messages Supported)

**Inbound (to NVU) — PCI Register Access:**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| PCI Register MRd | Register Access | 0x00 | in | Non-Posted | Unicast |
| PCI Register MWr (non-posted) | Register Access | 0x01 | in | Non-Posted | Unicast |
| PCI Register MWr (posted) | Register Access | 0x01 | in | Posted | Unicast |
| PCI Register CfgRd | Register Access | 0x04 | in | Non-Posted | Unicast |
| PCI Register CfgWr | Register Access | 0x05 | in | Non-Posted | Unicast |

**Outbound (from NVU) — PCI Register Completions:**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| PCI Register CplD | Completion | 0x21 | out | Posted | Unicast |
| PCI Register Cpl | Completion | 0x20 | out | Posted | Unicast |

**Inbound — PvtCfg Register Access:**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| PvtCfg Register CRRd | Register Access | 0x06 | in | Non-Posted | Unicast |
| PvtCfg Register CRWr (non-posted) | Register Access | 0x07 | in | Non-Posted | Unicast |
| PvtCfg Register CRWr (posted) | Register Access | 0x07 | in | Posted | Unicast |

**Outbound — PvtCfg Register Completions:**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| PvtCfg Register CplD | Completion | 0x21 | out | Posted | Unicast |
| PvtCfg Register Cpl | Completion | 0x20 | out | Posted | Unicast |

**PMC Bulk Register Access (via pmc_agent):**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| Register Access Bulk Rd | Register Access | 0x08 | in | Non-Posted | Unicast |
| Register Access Bulk Wr (non-posted) | Register Access | 0x09 | in | Non-Posted | Unicast |
| Register Access Bulk Wr (posted) | Register Access | 0x09 | in | Posted | Unicast |
| Register Access Bulk Rd CplD | Completion | 0x21 | out | Posted | Unicast |
| Register Access Bulk Wr Cpl | Completion | 0x20 | out | Posted | Unicast |

**IPC Register Access (Inbound):**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| IPC Register CRRd | Register Access | 0x06 | in | Non-Posted | Unicast |
| IPC Register CRWr (posted) | Register Access | 0x07 | in | Posted | Unicast |
| IPC Register CplD | Completion | 0x21 | in | Posted | Unicast |
| IPC Register Cpl | Completion | 0x20 | in | Posted | Unicast |

**IPC Register Access (Outbound):**

| Message | Type | Opcode | Direction | Transaction Type | Addressing |
|---|---|---|---|---|---|
| IPC Register CRRd | Register Access | 0x06 | out | Non-Posted | Unicast |
| IPC Register CRWr (posted) | Register Access | 0x07 | out | Posted | Unicast |
| IPC Register CplD | Completion | 0x21 | out | Posted | Unicast |
| IPC Register Cpl | Completion | 0x20 | out | Posted | Unicast |

> **Security:** All SB messages defer to the Security Section of the HAS for access control policies.

---

#### IPC Cycle Details (Peer Agents)

### IOSF Sideband IPC Routing
(HAS §8.14.1 IPC Cycle Details from/to Peer Agents)

| IPC Channel | FROM | TO | SrcID | DstID | Opcode | RS | FID | BARID | DB | DBM |
|---|---|---|---|---|---|---|---|---|---|---|
| NVU → ISH | NVU | ISH | nvu | ishbr | 0x7 | 0x0 | 0x0 | 0x0 | 0x2048 | 0x2054 |
| ISH → NVU | ISH | NVU | ish | nvu | 0x7 | 0x0 | 0x0 | 0x0 | — | — |
| NVU → ESE | NVU | ESE | nvu | ese_cse | 0x1 | 0x2 | 0x1 | — | — | — |
| ESE → NVU | ESE | NVU | ese_cse | nvu | 0x7 | 0x0 | 0x0 | 0x0 | — | — |
| PMC → NVU | PMC | NVU | pmc | nvu | 0x7 | 0x0 | 0x0 | 0x0 | — | — |

---

#### PTN (Port-to-Network) NAP Bridge Registers

### PTN_PORT_CONFIG
(HAS CRIF: ptn_apb_Msg_Cr_ptn_map_ptn_map)

| Field | Bit(s) | Reset | Access | Description |


### IPC Messaging (3 facts)

#### IPC Messaging — FW Care-abouts

*(HAS §8.14.2.5)*

---

#### Outbound Message Sequencing

The following behavioral rules apply when the NVU firmware sends outbound IPC messages (NVU2\* direction):

- `ROWN_REQ`/`ROWN_ACK` **must be held high** throughout the entire duration of sending any NVU2\* outbound message.
- `ROWN_RQ` **must be set** before the firmware begins writing to any message registers.
- The **doorbell (DB) is pressed** after all message registers have been written.
- `ROWN_RQ` is **cleared** inside the `busy_clr` handler upon completion.

---

#### ESE — NVU Register Set

> ⚠️ **Documentation Gap** *(HAS §8.14.2.5)*: The register set table currently documented covers **CSE** only. Equivalent register set tables for **ESE** and **ISH** are required but have not yet been provided in the source HAS. The sections below will be populated once the corresponding ESE and ISH register definitions are available.

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| *(pending)* | — | — | — | ESE register definitions not yet specified in HAS |

> **Action Required:** HAS authors to supply ESE-specific and ISH-specific NVU register set tables analogous to the existing CSE table. *(HAS §8.14.2.5)*


### Neural Network Accelerator (140 facts)

#### Neural Network Accelerator — NPX6 Debug Memory Map Registers

### Overview

The NPX6 debug memory map is organized into two primary register groups within the addressable debug memory map (HAS §8.2.3.2):

- **ROM Table Registers** (§8.2.3.2.1)
- **ARC Trace and L1 Core Registers** (§8.2.3.2.2)

---

#### ROM Table Registers (HAS §8.2.3.2.1)

##### ROM Entry Registers

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| Rom Entry | 0x000 | R | ARC Trace @ offset 0x1 (see ROM entries table) |
| Rom Entry | 0x004 | R | L1 Core0 @ offset 0x2 (see ROM entries table) |
| Rom Entry | 0x008 | R | All Zeros — End of Entries marker (see ROM entries table) |

##### Claim Tag Registers

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| CLAIMSET | 0xFA0 | RAZ/WI | Claim Tag Set register |
| CLAIMCLR | 0xFA4 | RAZ/WI | Claim Tag Clear register |

##### Device Affinity and Lock Registers

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| DEVAFF0 | 0xFA8 | RAZ | Device Affinity register 0 — not used, RAZ |
| DEVAFF1 | 0xFAC | RAZ | Device Affinity register 1 — not used, RAZ |
| LAR | 0xFB0 | RAZ | Lock Access register — not implemented, RAZ |
| LSR | 0xFB4 | RAZ | Lock Status register — not implemented, RAZ |

##### Device Identification Registers

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| AUTHSTATUS | 0xFB8 | R | Authentication Status register |
| DEVARCH | 0xFBC | R | Device Architecture register |
| DEVID2 | 0xFC0 | R | Device Configuration register 2 |
| DEVID1 | 0xFC4 | R | Device Configuration register 1 |
| DEVID | 0xFC8 | R | Device Configuration register |
| DEVTYPE | 0xFCC | R | Device Type Identifier register |

##### Peripheral Identification Registers (PIDRn)

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| PIDR4 | 0xFD0 | R | [7:4] SIZE; [3:0] DES_2 |
| PIDR5 | 0xFD4 | R | Reserved |
| PIDR6 | 0xFD8 | R | Reserved |
| PIDR7 | 0xFDC | R | Reserved |
| PIDR0 | 0xFE0 | R | Part number bits [7:0] |
| PIDR1 | 0xFE4 | R | [7:4] JEP106 identification code bits[3:0]; [3:0] Part number bits[11:8] |
| PIDR2 | 0xFE8 | R | [7:4] Revision; [3] JEDEC; [2:0] JEP106 identification code[6:4] |
| PIDR3 | 0xFEC | R | [7:4] RevAnd; [3:0] Customer Modified |

##### Component Identification Registers (CIDRn)

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| CIDR0 | 0xFF0 | R | Preamble 0 (0x0D) |
| CIDR1 | 0xFF4 | R | [7:4] Component class (0x9 — CoreSight component); [3:0] Preamble 1 (0x0) |
| CIDR2 | 0xFF8 | R | Preamble 2 (0x05) |
| CIDR3 | 0xFFC | R | Preamble 3 (0xB1) |

- CLAIMSET and CLAIMCLR are both RAZ/WI — writes are ignored and reads return zero (HAS §8.2.3.2.1)
- DEVAFF0, DEVAFF1, LAR, and LSR are RAZ — these registers are not used or not implemented (HAS §8.2.3.2.1)
- The ROM Entry at offset 0x008 returning all zeros serves as the end-of-entries marker for ROM table traversal (HAS §8.2.3.2.1)
- CIDR1 bits [7:4] identify this as a CoreSight component (class 0x9) (HAS §8.2.3.2.1)

---

#### ARC Trace and L1 Core Registers (HAS §8.2.3.2.2)

| Name | Address | Mode | Description |
|------|---------|------|-------------|
| DB_STAT | 0x000 | — | Debug Status register |


### NoC Fabric (197 facts)

#### NoC Fabric Registers

### Overview

The NVU NoC Fabric register space provides control and status registers for the internal AXI bus fabric, IOSF-to-AXI bridge, credit management, clock gating, and error handling. The fabric register base lower address parameter is **16** (HAS §8.12.2).

---

#### IOSF Primary Interface Signals (HAS §4.3.7.1)

| Signal Name | Port Name | Direction | Width | Required/Optional | Description |
|---|---|---|---|---|---|
| MADDRESS | `nvu_iosf_prim_maddress` | output | MMAX_ADDR+1 | required | Transaction address for memory/IO transactions or Completions on the master command channel |
| TADDRESS | `nvu_iosf_prim_taddress` | input | TMAX_ADDR+1 | required | Transaction address for memory/IO transactions or Completions on the target command channel |

- For memory and IO transactions, the address field contains the transaction address.
- For Completions, this field carries completion-specific address information.

---

#### DFT Scan Interface Signals (HAS §4.3.13.1)

| Signal Name | Port Name | Direction | Width | Required/Optional | Clocking | Description |
|---|---|---|---|---|---|---|
| FSCAN_BYPRST_B | `nvu_fscan_byprst_b` | input | NUM_BYPRST_B | required | async | Fabric Scan Bypass Reset Bar: reset input for scan operations that bypasses the internal agent reset logic |
| FSCAN_BYPLATRST_B | `nvu_fscan_byplatrst_b` | input | NUM_BYPLATRST_B | optional | async | Fabric Scan Bypass Latch Reset Bar: reset input for scan operations that bypasses the internal agent reset |
| FSCAN_LATCHCLOSED_B | `nvu_fscan_latchclosed_b` | input | 1 | optional | async | Fabric Scan Latch Closed Bar: controls the latch closed during scan operations |
| FSCAN_RAM_RDDIS_B | `nvu_fscan_ram_rddis_b` | input | 1 | optional | async | Fabric Scan RAM Read Disable Bar: controls the read enable on the agent's array during scan operations |
| FSCAN_RAM_WRDIS_B | `nvu_fscan_ram_wrdis_b` | input | 1 | optional | async | Fabric Scan RAM Write Disable Bar: controls the write enable on the agent's array during scan operations |
| FSCAN_CLKGENCTRL | `nvu_fscan_clkgenctrl` | input | NUM_CLKGENCTRL | optional | async | Fabric Scan Clock Generator Control |
| FSCAN_CLKGENCTRLEN | `nvu_fscan_clkgenctrlen` | input | NUM_CLKGENCTRLEN | optional | async | Fabric Scan Clock Generator Control Enable |

---

#### PCI Configuration Registers — CFG B0:D18:F0 (CRIF: file_iosf2axi_pci_configreg_CFG)

##### STATUSCOMMAND Register

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| RTA | [28] | 0x0 | RW/1C | Received Target Abort |

##### BAR Register

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| BASEADDR | [31:12] | 0x00000 | RW | Base Address Register Low — base address of the AXI fabric memory space, taken from strap values |

##### BAR1_HIGH Register

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| BASEADDR1_HIGH | [31:0] | 0x00000000 | RW | Base address of the AXI fabric memory space (upper 32 bits), taken from strap values |

---

#### Private Configuration Registers — IOSF2AXI Bridge (CRIF: file_iosf2axi_private_configreg)

##### ERRSTATUS Register

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| DS_SB_ERR_RESP | [14] | 0x0 | RW/1C | Set whenever a downstream MMIO transaction (P/NP) is dropped due to Bridge internal conditions (e.g., SAI mismatch, error response) |

---

#### NOC Fabric PTN Registers — Base Offset 0x4C00 (CRIF: NOC_VISION_FABRIC / nvu_ptn_0x00004c00)

> **NOC IP**: Arteris FlexNoC v5.4 interconnect fabric — routes all initiator/target traffic within NVU.

> All registers in this block are at MSG B?:D?:F? address space.

---

##### `bridge_nvu_ptn_2_10_noc_ctrl_value` — Streaming TX Clock Gating Override

**Offset:** 0x0000_4C30 | **Size:** 32 bits

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| UNSD_31_3 | [31:3] | 0x00000000 | DC | Unused bits |
| B2H_RAS_CHECK | [2] | 0x0 | NA | Disabled register field |
| H2B_RAS_CHECK | [1] | 0x0 | NA | Disabled register field |
| CG_OR | [0] | 0x0 | RW | Coarse-grained clock gating override: set to `1b1` to override coarse clock gating for the streaming TX path |

- This register controls miscellaneous bridge settings. (HAS §8.10 NOC Fabric)

---

##### `bridge_nvu_ptn_2_10_noc_rx_a_vc_b2h_credit_counter_value_value` — B2H Interface VC Credit Counter (RX-A)

**Offset:** 0x0000_4CD0 | **Size:** 64 bits

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| UNSD_63_62 | [63:62] | 0x0 | DC | Unused bits |
| VC7 | [61:56] | 0x00 | NA | Disabled register field |
| UNSD_55_54 | [55:54] | 0x0 | DC | Unused bits |
| VC6 | [53:48] | 0x00 | NA | Disabled register field |
| UNSD_47_46 | [47:46] | 0x0 | DC | Unused bits |
| VC5 | [45:40] | 0x00 | NA | Disabled register field |
| UNSD_39_38 | [39:38] | 0x0 | DC | Unused bits |
| VC4 | [37:32] | 0x00 | NA | Disabled register field |
| UNSD_31_30 | [31:30] | 0x0 | DC | Unused bits |
| VC3 | [29:24] | 0x00 | NA | Disabled register field |
| UNSD_23_22 | [23:22] | 0x0 | DC | Unused bits |
| VC2 | [21:16] | 0x00 | NA | Disabled register field |
| UNSD_15_14 | [15:14] | 0x0 | DC | Unused bits |
| VC1 | [13:8] | 0x00 | NA | Disabled register field |
| UNSD_7_6 | [7:6] | 0x0 | DC | Unused bits |
| VC0 | [5:0] | 0x02 | RO | Credit count for VC0 |

---

##### `bridge_nvu_ptn_2_10_noc_rx_a_shared_b2h_credit_counter_value_value` — B2H Interface Shared Credit Counter (RX-A)

**Offset:** 0x0000_4CD8 | **Size:** 64 bits

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| UNSD_63_6 | [63:6] | 0x000000000000000 | DC | Need to be updated |
| SHARED | [5:0] | 0x00 | RO | Shared credit count for interface |

---

##### `bridge_nvu_ptn_2_10_noc_rx_b_vc_b2h_credit_counter_value_value` — B2H Interface VC Credit Counter (RX-B)

**Offset:** 0x0000_4CE0 | **Size:** 64 bits

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| UNSD_63_62 | [63:62] | 0x0 | DC | Unused bits |
| VC7 | [61:56] | 0x00 | NA | Disabled register field |
| UNSD_55_54 | [55:54] | 0x0 | DC | Unused bits |
| VC6 | [53:48] | 0x00 | NA | Disabled register field |
| UNSD_47_46 | [47:46] | 0x0 | DC | Unused bits |
| VC5 | [45:40] | 0x00 | NA | Disabled register field |
| UNSD_39_38 | [39:38] | 0x0 | DC | Unused bits |
| VC4 | [37:32] | 0x00 | NA | Disabled register field |
| UNSD_31_30 | [31:30] | 0x0 | DC | Unused bits |
| VC3 | [29:24] | 0x00 | NA | Disabled register field |
| UNSD_23_22 | [23:22] | 0x0 | DC | Unused bits |
| VC2 | [21:16] | 0x00 | NA | Disabled register field |
| UNSD_15_14 | [15:14] | 0x0 | DC | Unused bits |
| VC1 | [13:8] | 0x00 | NA | Disabled register field |
| UNSD_7_6 | [7:6] | 0x0 | DC | Unused bits |
| VC0 | [5:0] | 0x02 | RO | Credit count for VC0 |

---

##### `bridge_nvu_ptn_2_10_noc_rx_b_shared_b2h_credit_counter_value_value` — B2H Interface Shared Credit Counter (RX-B)

**Offset:** 0x0000_4CE8 | **Size:** 64 bits

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| UNSD_63_6 | [63:6] | 0x000000000000000 | DC | Need to be updated |
| SHARED | [5:0] | 0x00 | RO | Shared credit count for interface |

---

##### `bridge_nvu_ptn_2_10_noc_rx_c_vc_b2h_credit_counter_value_value` — B2H Interface VC Credit Counter (RX-C)

**Offset:** 0x0000_4CF0 | **Size:** 64 bits

> Field layout identical to RX-A and RX-B VC credit counter registers. VC0 reset = 0x02 (RO); VC1–VC7 disabled (NA); unused/DC bits interleaved per VC pair.

---

##### `bridge_nvu_ptn_2_10_noc_rx_c_shared_b2h_credit_counter


### PMC Integration and Wake (4 facts)

#### PMC Integration and Wake — Register Context

> **Note:** The facts available for this section originate from AON Vision App Development and ARCSYNC IP chapters. No dedicated PMC wake register map (offsets, reset values, field sizes) is present in the provided HAS extracts. The content below reflects only what is specified in the source material.

---

#### ARCSYNC Semaphore-Based Wake Mechanism

(HAS §8.5 IP-Specific Description > 8.5.2 ARCSYNC Features)

- **Counting semaphores** are supported for managing shared resources across cores.
- **Barrier semaphores** are supported for intra-cluster synchronization (rendezvous points).
- Cores may **sleep and wake up** on a successful semaphore acquire, driven by interrupt, enabling low-power wait states without polling.

---

#### NN Offload Service — Interrupt Enable and Wake Flow

(HAS §12.9 AON Vision App Development > 12.9.2 Requirements and Flow)

- When a task is registered from **APP MGMT**, the Scheduler updates the task queue accordingly.
- As part of the model runner initialization flow:
  - **Interrupts are enabled.**
  - The **model runner workload callback** is registered with the ISR (Interrupt Service Routine), coupling neural network offload completion to the system wake path.

---

#### Runtime STATUS Register Initialization for Unaligned Access

(HAS §12.6.2.3.2 AON Vision App Development > WASM SDK — AOT Cross-Compile)

- When the processor is configured to **permit unaligned memory accesses** (e.g., via the `-Xunaligned` compiler flag), the compiler inserts a runtime initialization call.
- The function **`_init_ad()`** is invoked at startup to configure the **STATUS register** to reflect the unaligned-access policy before any application code executes.

| Initialization Function | Trigger Condition | Target Register | Purpose |
|---|---|---|---|
| `_init_ad()` | `-Xunaligned` specified at compile time | STATUS | Enable unaligned memory access mode at runtime startup |

---

> ⚠️ **HAS Coverage Gap:** No explicit PMC wake register offsets, field definitions, or reset values are present in the provided facts for this section. Register tables will be populated when the corresponding PMC Integration HAS extracts are supplied.


### Peripheral Interfaces (59 facts)

#### Peripheral Interfaces

### GPIO Interface

#### GPIO Allocation for Camera Sensor Control
(HAS: Chapter 4 > 8.1 MIPI CSI-2 Camera > 8.1.2 Camera Control Interface Sharing)

- Up to 8 GPIOs can be allocated as ad-hoc functional output pins for sensor reset, power control, and similar functions
- There is no multiplexer for GPIO between NVU and LPSS; these pins are dedicated

---

### I2C/I3C Camera Control Interface Sharing

#### PMode Switching — NVU vs. LPSS Ownership
(HAS: Chapter 4 > 8.1.3 Camera Sensor Control > 8.1.3.2 MIPI Camera Control via I2C/I3C)

- FW is responsible for switching the PMode between NVU and LPSS according to camera sensor ownership
- PMode switching is performed by programming the corresponding pad register in the SoC GPIO controller through IOSF-SB

#### I2C/I3C Sharing with IPU
(HAS: 8.7 MIPI Interface Sub-System > 8.7.2.1.7.2 MIPI Camera I2C/I3C Sharing with IPU)

- The I2C/I3C interface of the camera must be available to both NVU and IPU based on ownership
- IPU uses any of the LPSS 6×I2C / 4×I3C via driver-to-driver communication between the IP SW driver and the LPSS I2C/I3C driver

---

### I2C Controller

#### I2C Controller Configuration Parameters
(HAS: 8.17 I2C Controller > 8.17.3 I2C Controller Configuration)

| Name | Type | Default Value | Description |
|---|---|---|---|
| SLAVE_INTERFACE_TYPE | uint32 | 0 | APB2 interface |
| IC_FIRST_DATA_BYTE_STATUS | uint32 | 0x1 | Controls whether I2C generates FIRST_DATA_BYTE status bit in IC_DATA_CMD register |
| IC_SCL_STUCK_TIMEOUT_DEFAULT | uint32 | 0xFFFFFFFF | Default value of the IC_SCL_STUCK_LOW_TIMEOUT register |
| IC_SDA_STUCK_TIMEOUT_DEFAULT | uint32 | 0xFFFFFFFF | Default value of the IC_SDA_STUCK_LOW_TIMEOUT register |
| IC_DEVICE_ID | uint32 | 0x0 | Master mode includes a DEVICE_ID bit 13 in IC_TAR register to initiate Device ID read for a particular slave |
| IC_DEVICE_ID_VALUE | uint32 | 0x0 | Device ID value of the I2C slave stored in the IC_DEVICE_ID register |
| IC_SMBUS_CLK_LOW_SEXT_DEFAULT | uint32 | 0xFFFFFFFF | Default value of the IC_SMBUS_CLK_LOW_SEXT register |
| IC_SMBUS_CLK_LOW_MEXT_DEFAULT | uint32 | 0xFFFFFFFF | Default value of the IC_SMBUS_CLK_LOW_MEXT register |
| IC_SMBUS_RST_IDLE_CNT_DEFAULT | uint32 | 0xFFFFFFFF | Default value of the IC_SMBUS_THIGH_MAX_IDLE_COUNT register |
| IC_SMBUS_UDID_MSB | uint32 | 0x0 | Upper 96-bits of UDID registers (use 0x0) |
| IC_SMBUS_UDID_LSB_DEFAULT | uint32 | 0xFFFFFFFF | Lower 32-bits of UDID registers |
| IC_PERSISTANT_SLV_ADDR_DEFAULT | uint32 | 0x0 | Default value of the Persistent Slave Address register bit in IC_CON register |

#### I2C Controller Registers
(HAS: 8.17 I2C Controller > 8.17.4 I2C Controller Registers)

- Register definitions are described separately in the Designware I2C datasheet from the IP vendor
- Refer to the Designware I2C document in the References section for individual register definitions

---

### SPI Controller

#### SPI Controller Configuration Parameters
(HAS: 8.18 SPI Controller > 8.18.2.1 SPI Controller Parameters)

| Name | Type | Default Value | Description |
|---|---|---|---|
| SSI_APBIF_TYPE | uint32 | 0 | APB2.0 interface |
| SSI_APB3_ERR_RESP_EN | uint32 | N/A | N/A for APB2.0 |

---

### UART Controller

#### UART IP Configuration Parameters
(HAS: 8.19 UART Controller > 8.19.2.1 UART IP Parameter)

| Name | Type | Default Value | Description |
|---|---|---|---|
| SLAVE_INTERFACE_TYPE | uint32 | 0 | APB2 interface |
| FIFO_MODE | uint32 | 64 | 64-byte FIFO |
| THRE_MODE_USER | uint32 | 1 | Enable Transmitter Hold Register Empty interrupt |
| SHADOW | uint32 | 0 | Shadow programming registers are not enabled |
| UART_ADD_ENCODED_PARAMS | uint32 | 1 | Enable component parameter register |
| LSR_STATUS_CLEAR | uint32 | 0 | LSR status bits cleared on reading Rx FIFO (RBR Read) or on reading the LSR register |

---

### I3C Controller

#### I3C Clocking
(HAS: 8.20 I3C Controller > 8.20.1 I3C Clocking)

- The selection of `core_clk` is performed by programming the CRU `I3C_CLK_SEL` register
- Clock selection must be performed before the I3C controller is enabled
- If FW wishes to switch the clock, it must quiesce the controller prior to doing so

#### I3C Configuration Parameters
(HAS: 8.20 I3C Controller > 8.20.4 I3C Parameters)

| Name | Type | Default Value | Description |
|---|---|---|---|
| IC_DEVICE_ROLE | uint32 | 1 | Master Only |
| IC_HAS_HCI | uint32 | 1 | HCI Compliant |
| IC_DFLT_RX_START_THLD | uint32 | 3'h1 | 4 — set to half of RX Command Buffer depth |
| IC_DFLT_TX_START_THLD | uint32 | 3'h1 | 4 — set to half of TX Command Buffer depth |
| IC_DFLT_RX_BUF_THLD | uint32 | 3'h4 | 32 — set to half of RX Buffer depth |
| IC_DFLT_OPERATION_REG_OFFSET | uint32 | 0x0 | Default value of Operational Register Section Offset |
| IC_DFLT_PIO_SEC_OFFSET | uint32 | 0xC0 | Default value of PIO Section Offset |
| IC_DFLT_RING_HDR_SEC_OFFSET | uint32 | 0x3C0 | Default value of Ring Header Section Offset |
| IC_DFLT_EXTCAPS_SEC_OFFSET | uint32 | 0x200 | Default value of Extended Capabilities Section Offset |
| IC_DFLT_DAT_SEC_OFFSET | uint32 | 0x80 | Default value of DAT Section Offset |
| IC_DFLT_DCT_SEC_OFFSET | uint32 | 0x100 | Default value of DCT Section Offset |
| IC_FW_RAM_RETIMING | uint32 | 1 | Enable register re-timing on forward and return path |
| IC_DFLT_HCI_VERSION | uint32 | 32'h100 | Reset value of HCI Version field in IC_HCI_VERSION register (v1.00) |

#### I3C SCL Timing Parameters
(HAS: 8.20 I3C Controller > 8.20.4 I3C Parameters)

| Name | Type | Default Value | Description |
|---|---|---|---|
| IC_DFLT_I3C_OD_HCNT | uint32 | 8'h8 | Reset value of I3C_OD_HCNT field in SCL_HCNT_TIMING register |
| IC_DFLT_I3C_OD_LCNT | uint32 | 8'h34 | Reset value of I3C_OD_LCNT field in SCL_LCNT_TIMING register |
| IC_DFLT_I3C_PP_HCNT | uint32 | 8'h8 | Reset value of I3C_PP_HCNT field in SCL_HCNT_TIMING register |
| IC_DFLT_I3C_PP_LCNT | uint32 | 8'h8 | Reset value of I3C_PP_LCNT field in SCL_LCNT_TIMING register |
| IC_DFLT_I2C_FM_HCNT | uint32 | 16'hB4 | Reset value of I2C_FM_HCNT field in SCL_I2C_FM_TIMING register |
| IC_DFLT_I2C_FM_LCNT | uint32 | 16'h140 | Reset value of I2C_FM_LCNT field in SCL_I2C_FM_TIMING register |
| IC_DFLT_I2C_FMP_HCNT | uint32 | 8'h4C | Reset value of I2C_FMP_HCNT field in SCL_I2C_FMP_TIMING register |
| IC_DFLT_I2C_FMP_LCNT | uint32 | 16'h7C | Reset value of I2C_FMP_LCNT field in SCL_I2C_FMP_TIMING register |
| IC_DFLT_I2C_SS_HCNT | uint32 | 16'h320 | Reset value of I2C_SS_HCNT field in SCL_I2C_SS_TIMING register |
| IC_DFLT_I2C_SS_LCNT | uint32 | 32'h3AC | Reset value of I2C_SS_LCNT field in SCL_I2C_SS_TIMING register |
| IC_DFLT_EXT_LCNT_1 | uint32 | 8'h20 | Reset value of I3C_EXT_LCNT_1 field in SCL_EXT_LCNT_TIMING register |
| IC_DFLT_EXT_LCNT_2 | uint32 | 8'h20 | Reset value of I3C_EXT_LCNT_2 field in SCL_EXT_LCNT_TIMING register |
| IC_DFLT_EXT_LCNT_3 | uint32 | 8'h20 | Reset value of I3C_EXT_LCNT_3 field in SCL_EXT_LCNT_TIMING register |
| IC_DFLT_EXT_LCNT_4 | uint32 | 8'h20 | Reset value of I3C_EXT_LCNT_4 field in SCL_EXT_LCNT_TIMING register |
| IC_DFLT_TERMN_LCNT | uint32 | 4'h0 | Reset value of TERMN_LCNT field in SCL_TERMN_LCNT_TIMING register |

#### I3C Bus Timing Parameters
(HAS: 8.20 I3C Controller > 8.20.4 I3C Parameters)

| Name |


### Register Details (23 facts)

#### USB Video Offload Logic — De-Packetizer Registers

(8.8.2.1.2.3 De-Packetizer)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| DPKTZR_CTRL | — | — | — | De-Packetizer Control Register |
| DPKTZR_STS | — | — | — | De-Packetizer Status Register |
| FRAME_CNT | — | — | — | Frame Count Register |

---

#### USB Video Offload Logic — Circular Buffer Registers

(8.8.2.1.2.5 Circular Buffer)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| CBUF_CTRL | — | — | — | Circular Buffer Control Register |
| CBUF_BASE_ADDR | — | — | — | Circular Buffer Base Address Register |

---

#### USB Video Offload Logic — Link Logic Registers

(8.8.2.1.2.6 Link Logic)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| LL_CTRL | — | — | — | Link Logic Control and Status Register |
| NVU_CLAIM | — | — | — | Control register written by NVU FW, and read by IPU HW |
| NVU_USB_CAM_OWNER | — | — | — | Status register written by IPU HW, and read by NVU FW |
| NVU_RELEASE_CLAIM_IRQ | — | — | — | Status register written by IPU HW, and read by NVU FW |

##### LL_CTRL Field Details

(8.8.2.1.2.6.2 Registers)

| Bits | Access | Default | Field Name | Description |
|------|--------|---------|------------|-------------|
| 0:0 | RW | 0 | LL_EN | Enable the Link Logic |
| 3:1 | RO | 0 | RSVD | Reserved |
| 4:4 | RW1CV | 0 | SC_REQ_ASSERT_IRQ | — |

##### NVU_RELEASE_CLAIM_IRQ Field Details

(8.8.2.1.2.6 Link Logic)

| Bits | Access | Default | Field Name | Description |
|------|--------|---------|------------|-------------|
| 2:2 | RW | 0 | NVU_OWNERSHIP_RELEASE_IRQ_MASK | Value 0 = `NVU_OWNERSHIP_RELEASE_IRQ` is masked; Value 1 = `NVU_OWNERSHIP_RELEASE_IRQ` is unmasked |

##### USB Video Offload — XHCI Access

(8.8.2.1 USB Video Offload Logic)

- The NVU USB Video Offload Architecture supports **direct access to XHCI registers**; this capability is **not** present in the USB Audio Offload Architecture (ACE).

---

#### Real Time Counter Registers

(8.16.1.1 Real Time Counter Registers)

- The Real Time Counter provides a single **64-bit counter** exposed via **two consecutive 32-bit registers**.
- The base address of the RTC registers is defined in the Real Time Counter section of the HAS.

---

#### SPI Controller Registers

(8.18.2.1 SPI Controller Parameters, 8.18.3 SPI Controller Registers, 8.18.4 SPI Controller Clocking)

| Parameter | Type | Value | Description |
|-----------|------|-------|-------------|
| SSI_RX_DLY_SR_DEPTH | uint32 | 255 | Supports 256 flops in the Rx Delay shift register |

- SPI controller registers are **not described in this document**; refer to the **SPI controller IP vendor datasheet** for full register details.
- Only **even values** (2, 4, 6, 8, …) may be programmed into the SPI clock divider register.

---

#### Time-Stamping — XTAL Frequency Register Field

(8.23.1.2 XTAL Frequency Dependency)

- FW shall read the **`PCKTZR_DTF_SRC_STATUS.TS_BIT_SHIFT_VAL`** field in the DTF module to decode the platform XTAL frequency.
- This field reflects the SoC tie-off value present on the NVU port `nvu_dtf_ts_bit_shift`.

---

#### PtN NAP Registers — MSG CRIF (`ptn_apb_Msg_Cr_ptn_map_ptn_map`)

(CRIF: ptn_apb_Msg_Cr_ptn_map_ptn_map)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PTN_PORT_CONFIG | 0x0000D000 | 32 bits | — | PtN NAP Port Configuration Register |
| PTN_ISM_CONFIG | 0x0000D004 | 32 bits | — | PtN NAP Port Configuration Register |
| PTN_EH_STATUS | 0x0000D020 | 32 bits | — | PtN NAP Error Handler Status Register |

---

#### PtN NAP Registers — APB.MEM CRIF (`ptn_map`)

(CRIF: ptn_map APB.MEM)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PTN_PORT_CONFIG | 0x00000000 | 32 bits | — | PtN NAP Port Configuration Register |
| PTN_ISM_CONFIG | 0x00000004 | 32 bits | — | PtN NAP Port Configuration Register |
| PTN_EH_STATUS | 0x00000020 | 32 bits | — | PtN NAP Error Handler Status Register |


### SRAM and Memory (143 facts)

#### SRAM and Memory Registers

### SRAM Sub-System Overview (8.6 SRAM Sub-System)

#### Memory Interface Mapping (8.6.2 SRAMSS Memory Mapping)

| Memory Interface | Size | Type | SRAM Usage | Secondary Memory |
|---|---|---|---|---|
| PMEM | 3.5 MB | Physical Memory | MMIO Mapped To Physical SRAM Slices | None |

- EXTMEM_BASE is derived from UMA_BASE registers in ESE IPC; there is no conflict with the SIO region at `0xA0000000` (8.6.4.3.4)
- After booting is complete, security registers are updated to block writes to the bridge; no action required from SRAM SS for disabling writes to IMR (8.6.4.5.3)

---

### Slice Controller Registers (8.6.4.2 SRAM Slice Controller > 8.6.4.2.6)

- All registers required to control and manage the slice controller are integrated with the slice controller (8.6.4.2)

#### SSCR — SRAM Slice Control Register

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| RMWPIPESTG (`cr_rmw_pipe_stg`) | 0:0 | RW | 0x1 | When set, enables a pipe stage between Fill-Read and Merge-Write cycles. Required when operating at high frequency. |
| ECCENB (`cr_ecc_enable_b`) | 1:1 | RW | 0x0 | When **cleared**, enables ECC bit generation on writes and enables SECDED (Single Bit Error Correction, Double Bit Error Detection) on reads. |
| DSOVREN (`cr_deepsleep_override_en`) | 2:2 | RW | 0x1 | When set, overrides the DS pin of all banks in this slice with the value programmed in `cr_deepsleep_override_val`. |
| DSOVRVAL (`cr_deepsleep_override_val`) | 3:3 | RW | 0x0 | Value driven to the DS pin when `cr_deepsleep_override_en` is set. |
| SDEN (`cr_shutdown_en`) | 4:4 | RW | 0x1 | When set, forces all SRAM banks in this slice into SHUTDOWN state. When cleared, the SRAM banks pin remains in its default state. |
| MEMPIPEN (`cr_mempipe_en`) | 5:5 | RW | 0x1 | When set, enables a pipe stage between the read command and read data, adding 1 clock cycle of latency to read data return. |
| DSMINDUR (`cr_deepsleep_min_duration`) | 11:8 | RW | 0x4 | Minimum duration (in clocks) for SRAM to remain in deep sleep mode. Maximum value is 16 clocks. |
| *(Reserved)* | 12:12 | — | — | Reserved. |
| *(Reserved)* | 31:15 | — | — | Reserved. |

---

#### SSCEL — SRAM Slice Controller ECC Log Register

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| CNT (`CerrCnt`) | 15:0 | ROVP | 0x0 | Increments with every correctable error indication. Reset only upon `powergood_rst_b` assertion (Sx state). |
| CERREV (`Cerr Event`) | 16:16 | ROVP | 0x0 | Indicates a correctable error was encountered during a read operation. RO for FW; cleared by hardware on next access. |
| *(Reserved)* | 30:17 | — | — | Reserved. |
| UCERREV (`UCerr Event`) | 31:31 | ROVP | 0x0 | Indicates an uncorrectable error was encountered during a read operation. RO for FW; cleared by hardware on next access. |

---

### SHA384 Accelerator — Control and Status Registers (8.6.4.5 Secure HASH Algorithm Accelerator)

- The SHA algorithm selection (SHA-1 / SHA-224 / SHA-256 / SHA-384 / SHA-512) is controlled by register field **`SHACTL.ALGO`** (8.6.4.5)
- FW stops an SHA operation by clearing **`SHACTL.EN`** to `0` when the intended data length has been reached; the hash result is then consumed from the **`SHARDWx`** registers after confirming **`SHASTS.BUSY = 0`** (8.6.4.5)
- FW resumes a saved SHA context by: (8.6.4.5.3)
  - Programming the previously saved hash result into **`SHAIVDWx`** registers
  - Programming the accumulated data length into **`SHAALDWx`** registers
  - Setting **`SHACTL.EN`** to `1` with the appropriate `SHACTL` resume mode configuration

---

### HOST IPC IOSF Primary Memory Registers (CRIF: nvu_HOST_IPC_IOSF_Primary_Mem)

#### Register Summary

| Register Name | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| PISR_HOST2NVU | 0x00000000 | 32 bits | FUNCRST | Peripheral Interrupt Status — IRQ to NVU; contains inbound interrupt status bits |
| PIMR_HOST2NVU | 0x00000004 | 32 bits | FUNCRST | Peripheral Interrupt Mask — IRQ to NVU; enables/disables inbound interrupts from AGENT |
| PIMR_NVU2HOST | 0x00000008 | 32 bits | FUNCRST | Peripheral Interrupt Mask — IRQ to AGENT; enables/disables outbound interrupts |
| PISR_NVU2HOST | 0x0000000C | 32 bits | FUNCRST | Peripheral Interrupt Status — IRQ to AGENT; contains outbound interrupt status bits |

#### PIMR_HOST2NVU Fields

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| AGENT2NVU_DB | 0 | RW | 0x0 | Mask bit for AGENT2NVU Doorbell BUSY interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED2 | 10:1 | RO | 0x000 | Reserved. |
| NVU2AGENT_BC | 11 | RW | 0x0 | Mask bit for NVU2AGENT doorbell busy clear interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED1 | 26:12 | RO | 0x0000 | Reserved. |
| AGENT2NVU_BCISC | 27 | RW | 0x0 | Mask bit for AGENT2NVU Busy Clear Interrupt Status Clear interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED0 | 31:28 | RO | 0x0 | Reserved. |

#### PIMR_NVU2HOST Fields

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| NVU2AGENT_DB | 0 | RW | 0x0 | Mask bit for NVU2AGENT Doorbell BUSY Set. Written by AGENT only. `1` = unmasked. |
| RESERVED1 | 7:1 | RO | 0x00 | Reserved. |
| AGENT2NVU_BC | 8 | RW | 0x0 | Mask bit for AGENT2NVU Busy Clear Interrupt. Written by AGENT only. `1` = unmasked. |
| RESERVED0 | 31:9 | RO | 0x000000 | Reserved. |

---

### VOD IPC IOSF Sideband Memory Registers (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem)

#### Register Summary

| Register Name | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| PISR_VOD2NVU | 0x00001000 | 32 bits | FUNCRST | Peripheral Interrupt Status — IRQ to NVU; contains inbound interrupt status bits |
| PIMR_VOD2NVU | 0x00001004 | 32 bits | FUNCRST | Peripheral Interrupt Mask — IRQ to NVU; enables/disables inbound interrupts from AGENT |
| PIMR_NVU2VOD | 0x00001008 | 32 bits | FUNCRST | Peripheral Interrupt Mask — IRQ to AGENT; enables/disables outbound interrupts |
| PISR_NVU2VOD | 0x0000100C | 32 bits | FUNCRST | Peripheral Interrupt Status — IRQ to AGENT; contains outbound interrupt status bits |

#### PIMR_VOD2NVU Fields

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| AGENT2NVU_DB | 0 | RW | 0x0 | Mask bit for AGENT2NVU Doorbell BUSY interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED2 | 10:1 | RO | 0x000 | Reserved. |
| NVU2AGENT_BC | 11 | RW | 0x0 | Mask bit for NVU2AGENT doorbell busy clear interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED1 | 26:12 | RO | 0x0000 | Reserved. |
| AGENT2NVU_BCISC | 27 | RW | 0x0 | Mask bit for AGENT2NVU Busy Clear Interrupt Status Clear interrupt. Written by NVU FW only. `1` = unmasked. |
| RESERVED0 | 31:28 | RO | 0x0 | Reserved. |

#### PIMR_NVU2VOD Fields

| Field Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| NVU2AGENT_DB | 0 | RW | 0x0 | Mask bit for NVU2AGENT Doorbell BUSY Set. Written by AGENT only. `1` = unmasked. |
| RESERVED1 | 7:1 | RO | 0x00 | Reserved. |
| AGENT2NVU_BC | 8 | RW | 0x0 | Mask bit for AGENT2NVU Busy Clear Interrupt. Written by AGENT only. `1` = unmasked. |
| RESERVED0 | 31:9 | RO | 0x000000 | Reserved. |

---

### CSE IPC IOSF Sideband Message Registers (CRIF: nvu_CSE_IPC_IOSF_SideBand_Msg)

#### Register Summary

| Register Name | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| PISR_CSE2NVU | 0x00001000 | 32 bits | FUNCRST | Peripheral Interrupt Status — IRQ to NVU; contains inbound interrupt status bits |
| PIMR_CSE2NVU | 0x00001004 | 32 bits | FUNCRST | Peripheral Interrupt Mask — IRQ to NVU; enables/disables inbound interrupts from AGENT |

#### PIMR_CSE2NVU Fields

| Field Name |


### Secure Boot (2 facts)

#### NVU USB Camera Ownership Registers

(8 IP-Specific Description > 8.8 USB Interface Sub-System > 8.8.2 Sub-Blocks > 8.8.2.1 USB Video Offload Logic > 8.8.2.1.2 Sub-Blocks > 8.8.2.1.2.6 Link Logic)

---

##### NVU_USB_CAM_OWNER — NVU USB Camera Owner Claim Register

| Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| NVU_CLAIM_USB_CAM | 0:0 | RW | 0 | NVU firmware claim bit for shared USB_CAM |
| Reserved | 31:2 | RO | 0 | Reserved |

- **NVU_CLAIM_USB_CAM** field definitions:
  - `0` — NVU FW does not want to use shared USB_CAM
  - `1` — NVU FW wants to use shared USB_CAM

---

##### USB_CAM_OWNER — USB Camera Current Ownership Status Register

| Name | Bits | Access | Reset | Description |
|---|---|---|---|---|
| USB_CAM_OWNER | 1:0 | ROV | 0 | Reflects current ownership state of the shared USB_CAM resource |
| Reserved | 31:2 | RO | 0 | Reserved |

- **USB_CAM_OWNER** field definitions:
  - `00` — No one owns USB_CAM
  - `01` — NVU owns shared USB_CAM
  - `10` — IPU owns shared USB_CAM
  - `11` — NVU owns shared USB_CAM; IPU is requesting ownership


### USB Camera Interface (8 facts)

#### USB Camera Interface Registers

---

#### SIO Component Integration Interface

**(8 IP-Specific Description > 8.8 USB Interface Sub-System > 8.8.2 Sub-Blocks > 8.8.2.1 USB Video Offload Logic > 8.8.2.1.2 Sub-Blocks > 8.8.2.1.2.1 SIO Component)**

##### Clock Connectivity

| Signal | Source | Frequency | Description |
|---|---|---|---|
| `core_clk` | CRPM | 200 MHz | Functional Clock |
| `gcore_clk` | CRPM | 200 MHz | Functional Clock |
| `xtal_clk` | CRPM | 38.4 MHz | XTAL Clock |

##### SIO Frame Counter

- XHCI schedules commands to the USB device using a frame counter running on XTAL clock.
- All isochronous commands that XHCI receives over SIO must be processed relative to this frame counter.

**(8.8.2.1.2.1.6)**

---

#### De-Packetizer (DPKTZR) Registers

**(8 IP-Specific Description > 8.8 USB Interface Sub-System > 8.8.2 Sub-Blocks > 8.8.2.1 USB Video Offload Logic > 8.8.2.1.2 Sub-Blocks > 8.8.2.1.2.3 De-Packetizer — Section 8.8.2.1.2.3.6)**

##### DPKTZR_CTRL — Depacketizer Control Register

| Bits | Access | Reset | Name | Description |
|---|---|---|---|---|
| 0:0 | RW | 0 | `SEN` | Stream Enable: `0` = Stream Disable, `1` = Stream Enable |
| 1:1 | RW | 0 | *(see spec)* | *(additional field — full definition not provided in available facts)* |

##### DPKTZR_STS — Depacketizer Status Register

| Bits | Access | Reset | Name | Description |
|---|---|---|---|---|
| 5:5 | ROV | 0 | `SIOC_RESET_PREP_ACK` | Live value of SIO Component Reset Prep Ack |
| 31:6 | RO | 0 | Reserved | — |

- HW clears the Reset Prep request once `ResetPrepAck` is received from the SIO Component.

##### De-Packetizer Flows

**(8.8.2.1.2.3.3)**

- **Input Flow:** SIO DPKTZR Input Flow defines how data enters the De-Packetizer from the SIO component.
- **Output Flow:** SIO DPKTZR Output Flow defines how processed data exits the De-Packetizer.
- **Stopping Streams (Sensing Mode):** A defined procedure governs stream halt in sensing mode operation.

---

#### Link Logic Registers

**(8 IP-Specific Description > 8.8 USB Interface Sub-System > 8.8.2 Sub-Blocks > 8.8.2.1 USB Video Offload Logic > 8.8.2.1.2 Sub-Blocks > 8.8.2.1.2.6 Link Logic)**

| Bits | Access | Reset | Name | Description |
|---|---|---|---|---|
| 1:1 | RW1CV | 0 | `NVU_RELEASE_CLAIM_IRQ_STS` | HW sets this bit on detection of a `0→1` transition on `NVU_RELEASE_CLAIM`. FW clears by writing 1. |

- IPU HW will clear `NVU_RELEASE_CLAIM_IRQ` in response to NVU FW writing `NVU_CLAIM = 0`.

---

#### NVU2UVOL IPC

**(8 IP-Specific Description > 8.2 Memory Maps > 8.2.6 Host Address Map > 8.2.6.1 Peer Streaming over IOSF)**

- The NVU2UVOL IPC register block has been **marked as spare and removed from the specification**.
- The question of whether UVOL IPC would carry the same register set as HOST IPC is **no longer applicable** following this removal.

