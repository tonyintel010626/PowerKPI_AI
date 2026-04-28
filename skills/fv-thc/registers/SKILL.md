---
name: fv-thc/registers
description: THC register maps, PIO flows, PIO opcodes, and I2C APB Sub-IP configurations
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Registers and PIO Configuration

This skill provides the authoritative register offsets, PIO programming flows, and I2C sub-IP configurations for the Touch Host Controller (THC) IP.

## Safety: AVOID_THC_BITS

> **⚠️ WARNING**: Registers in `AVOID_THC_BITS` must NEVER be written carelessly:
> - `cfg.thc_cfg_ur_sts_ctl.fd` — **Function Disable** (writing `1` disables THC entirely, requires power cycle to recover)
> - `port.mem.thc_m_prt_control.thc_bios_lock_en` — BIOS lock (prevents further register modification)
> - `port.mem.thc_m_prt_control.thc_drv_lock_en` — Driver lock (prevents further register modification)

## THC Register Map (Real Register Names)

THC registers are accessed via namednodes in PythonSV. Key register groups mapped from the port base (0x1000):

| Offset | Register | Key Fields | Purpose |
|------|----------|-----------|---------|
| `0x0EC` | `THC_M_PRT_DEVINT_CFG_1` | `int_type_offset/length` | Device interrupt config 1 |
| `0x0F0` | `THC_M_PRT_DEVINT_CFG_2` | `RXDMA_PKT_STRM_EN`(26), `TXDMA_PKT_STRM_EN`(27) | Interrupt config 2 (streaming mode >4KB) |
| `0x008` | `THC_M_PRT_CONTROL` | `port_type` (0=SPI, 1=I2C), `devint_quiesce_en`(1), `devrst`(3) | Main port control and reset |
| `0x010` | `THC_M_PRT_SPI_CFG` | `spi_frequency`, `spi_io_mode`, `spi_rd_mps`, `spi_wr_mps` | SPI bus config (IO mode: Single/Dual/Quad) |
| `0x014` | `THC_M_PRT_SPI_ICRRD_OPCODE` | ICR Read Opcode | Programmable SPI opcode |
| `0x018` | `THC_M_PRT_SPI_DMARD_OPCODE` | DMA Read Opcode | Programmable SPI opcode |
| `0x01C` | `THC_M_PRT_SPI_WR_OPCODE` | Write Opcode | Programmable SPI opcode |
| `0x020` | `THC_M_PRT_INT_EN` | `GBL_INT_EN`, `I2CSUBIP`, `TXN_ERR`, `FATAL_ERR` | Master interrupt enable |
| `0x024` | `THC_M_PRT_INT_STATUS` | Status bits | Interrupt status |
| `0x028` | `THC_M_PRT_ERR_CAUSE` | `invld_dev_entry`, `buf_ovrrun_err`, `fatal_err_cause` | Error cause register |
| `0x040` | `THC_M_PRT_SW_SEQ_CNTRL` | Opcode, Byte Count, `TSSGO`(0) | PIO sequence control |
| `0x044` | `THC_M_PRT_SW_SEQ_STS` | `thc_ss_cip`, `thc_ss_err`, `tssdone`(0) | PIO sequence status |
| `0x048` | `THC_M_PRT_SW_SEQ_DATA[0-16]` | PIO Data | Up to 68 bytes of PIO data |
| `0x090` | `THC_M_PRT_WPRD_BA_LOW` | WPRD base addr low | Write PRD base address (low 32 bits, 4KB aligned) |
| `0x094` | `THC_M_PRT_WPRD_BA_HI` | WPRD base addr high | Write PRD base address (high 32 bits) |
| `0x098` | `THC_M_PRT_WRITE_DMA_CNTRL` | `START`, `IOC` | TXDMA control |
| `0x09C` | `THC_M_PRT_WRITE_INT_STS` | CMPL/ERROR/IOC/ACTIVE | TXDMA interrupt status |
| `0x0A0` | `THC_M_PRT_WRITE_DMA_ERR` | DMA error | TXDMA error register |
| `0x0B4` | `THC_M_PRT_WR_BULK_ADDR` | Bulk write address | Device address for bulk write |
| `0x0B8` | `THC_M_PRT_DEV_INT_CAUSE_ADDR` | INT cause address | Device interrupt cause register address |
| `0x0BC` | `THC_M_PRT_DEV_INT_CAUSE_REG_VAL` | INT_TYPE, MFS, EOF | Device interrupt cause register value |
| `0x0E0` | `THC_M_PRT_TX_FRM_CNT` | Frame count | TXDMA frame count (counter) |
| `0x0E4` | `THC_M_PRT_TXDMA_PKT_CNT` | Packet count | TXDMA packet count (counter) |
| `0x0E8` | `THC_M_PRT_DEVINT_CNT` | Device INT count | Device interrupt count (counter) |
| `0x100` | `THC_M_PRT_RPRD_BA_LOW_1` | RPRD base low | RXDMA1 PRD base address (low, 4KB aligned) |
| `0x104` | `THC_M_PRT_RPRD_BA_HI_1` | RPRD base high | RXDMA1 PRD base address (high) |
| `0x108` | `THC_M_PRT_RPRD_CNTRL_1` | PCD, PTEC, WM | RXDMA1 PRD control |
| `0x10C` | `THC_M_PRT_READ_DMA_CNTRL_1` | START, IE bits, TPCR/W | RXDMA1 DMA control |
| `0x110` | `THC_M_PRT_READ_DMA_INT_STS_1` | CMPL/ERR/IOC/STALL/EOF | RXDMA1 interrupt status |
| `0x114` | `THC_M_PRT_READ_DMA_ERR_1` | DLERR | RXDMA1 DMA error |
| `0x118` | `THC_M_PRT_GUC_OFFSET_LOW_1` | GuC offset low | RXDMA1 GuC tail offset (low) |
| `0x11C` | `THC_M_PRT_GUC_OFFSET_HI_1` | GuC offset high | RXDMA1 GuC tail offset (high) |
| `0x120` | `THC_M_PRT_GUC_WORKQ_ITEM_SZ_1` | Work queue item size | RXDMA1 GuC work queue item size |
| `0x124` | `THC_M_PRT_GUC_WORKQ_SZ_1` | Work queue size, FCD, GIC | RXDMA1 GuC work queue size |
| `0x128` | `THC_M_PRT_TSEQ_CNTRL_1` | RGD, EGP, RTO, EWOG | RXDMA1 touch sequencer control |
| `0x130` | `THC_M_PRT_GUC_DB_ADDR_LOW_1` | GuC DB addr low | RXDMA1 GuC doorbell address (low) |
| `0x134` | `THC_M_PRT_GUC_DB_ADDR_HI_1` | GuC DB addr high | RXDMA1 GuC doorbell address (high) |
| `0x138` | `THC_M_PRT_GUC_DB_DATA_1` | GuC DB data | RXDMA1 GuC doorbell data |
| `0x140` | `THC_M_PRT_GUC_OFFSET_INITVAL_1` | GuC offset init | RXDMA1 GuC tail offset initial value |
| `0x170` | `THC_M_PRT_RD_BULK_ADDR_1` | Bulk read address | RXDMA1 device bulk read address |
| `0x1A0` | `THC_M_PRT_DB_CNT_1` | Doorbell count | RXDMA1 doorbell count (counter) |
| `0x1A4` | `THC_M_PRT_FRM_CNT_1` | Frame count | RXDMA1 frame count (counter) |
| `0x1A8` | `THC_M_PRT_UFRM_CNT_1` | Microframe count | RXDMA1 microframe count (counter) |
| `0x1AC` | `THC_M_PRT_RXDMA_PKT_CNT_1` | Packet count | RXDMA1 packet count (counter) |
| `0x1B0` | `THC_M_PRT_SWINT_CNT_1` | SW interrupt count | RXDMA1 software interrupt count |
| `0x1B4` | `THC_M_PRT_FRAME_DROP_CNT_1` | Frame drop count | RXDMA1 frame drop count (counter) |
| `0x1B8` | `THC_M_PRT_COALESCE_1` | Coalesce timeout | RXDMA1 coalescing timeout |
| `0x200` | `THC_M_PRT_RPRD_BA_LOW_2` | RPRD base low | RXDMA2 PRD base address (low, 4KB aligned) |
| `0x204` | `THC_M_PRT_RPRD_BA_HI_2` | RPRD base high | RXDMA2 PRD base address (high) |
| `0x208` | `THC_M_PRT_RPRD_CNTRL_2` | PCD, PTEC, WM | RXDMA2 PRD control |
| `0x20C` | `THC_M_PRT_READ_DMA_CNTRL_2` | START, IE bits, TPCR/W | RXDMA2 DMA control |
| `0x210` | `THC_M_PRT_READ_DMA_INT_STS_2` | CMPL/ERR/IOC/STALL/EOF | RXDMA2 interrupt status |
| `0x214` | `THC_M_PRT_READ_DMA_ERR_2` | DLERR | RXDMA2 DMA error |
| `0x218` | `THC_M_PRT_GUC_OFFSET_LOW_2` | GuC offset low | RXDMA2 GuC tail offset (low) |
| `0x21C` | `THC_M_PRT_GUC_OFFSET_HI_2` | GuC offset high | RXDMA2 GuC tail offset (high) |
| `0x220` | `THC_M_PRT_GUC_WORKQ_ITEM_SZ_2` | Work queue item size | RXDMA2 GuC work queue item size |
| `0x224` | `THC_M_PRT_GUC_WORKQ_SZ_2` | Work queue size, FCD, GIC | RXDMA2 GuC work queue size |
| `0x228` | `THC_M_PRT_TSEQ_CNTRL_2` | RGD, EGP, RTO | RXDMA2 touch sequencer control |
| `0x230` | `THC_M_PRT_GUC_DB_ADDR_LOW_2` | GuC DB addr low | RXDMA2 GuC doorbell address (low) |
| `0x234` | `THC_M_PRT_GUC_DB_ADDR_HI_2` | GuC DB addr high | RXDMA2 GuC doorbell address (high) |
| `0x238` | `THC_M_PRT_GUC_DB_DATA_2` | GuC DB data | RXDMA2 GuC doorbell data |
| `0x240` | `THC_M_PRT_GUC_OFFSET_INITVAL_2` | GuC offset init | RXDMA2 GuC tail offset initial value |
| `0x270` | `THC_M_PRT_RD_BULK_ADDR_2` | Bulk read address | RXDMA2 device bulk read address |
| `0x2A0` | `THC_M_PRT_DB_CNT_2` | Doorbell count | RXDMA2 doorbell count (counter) |
| `0x2A4` | `THC_M_PRT_FRM_CNT_2` | Frame count | RXDMA2 frame count (counter) |
| `0x2A8` | `THC_M_PRT_UFRM_CNT_2` | Microframe count | RXDMA2 microframe count (counter) |
| `0x2AC` | `THC_M_PRT_RXDMA_PKT_CNT_2` | Packet count | RXDMA2 packet count (counter) |
| `0x2B0` | `THC_M_PRT_SWINT_CNT_2` | SW interrupt count | RXDMA2 software interrupt count |
| `0x2B4` | `THC_M_PRT_FRAME_DROP_CNT_2` | Frame drop count | RXDMA2 frame drop count (counter) |
| `0x2B8` | `THC_M_PRT_COALESCE_2` | Coalesce timeout | RXDMA2 coalescing timeout |
| `0x2BC` | `THC_M_PRT_SPARE_REG` | Chicken bits | Spare register (debug overrides) |
| `0x2C0` | `THC_M_PRT_RPRD_BA_LOW_SW` | RPRD base low | SWDMA PRD base address (low, 4KB aligned) |
| `0x2C4` | `THC_M_PRT_RPRD_BA_HI_SW` | RPRD base high | SWDMA PRD base address (high) |
| `0x2C8` | `THC_M_PRT_RPRD_CNTRL_SW` | PCD, PTEC, WM | SWDMA PRD control |
| `0x2CC` | `THC_M_PRT_READ_DMA_CNTRL_SW` | START, IE bits, TPCR/W | SWDMA DMA control |
| `0x2D0` | `THC_M_PRT_READ_DMA_INT_STS_SW` | CMPL/ERR/IOC/STALL/EOF | SWDMA interrupt status |
| `0x2D4` | `THC_M_PRT_TSEQ_CNTRL_SW` | Touch seq control | SWDMA touch sequencer control |
| `0x2D8` | `THC_M_PRT_RD_BULK_ADDR_SW` | Bulk read address | SWDMA device bulk read address |
| `0x2DC` | `THC_M_PRT_FRM_CNT_SW` | Frame count | SWDMA frame count (counter) |
| `0x2E0` | `THC_M_PRT_RXDMA_PKT_CNT_SW` | Packet count | SWDMA packet count (counter) |
| `0x31C` | `THC_M_PRT_I2C_CFG` | I2C config | HIDI2C specific configuration |

### WRITE_DMA_CNTRL Bit Fields (Offset 0x098)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `WRDMA_START` | `BIT(0)` | Start write DMA transfer |
| `[1]` | `IE_IOC_ERROR` | `BIT(1)` | Interrupt enable on IOC error |
| `[2]` | `IE_IOC` | `BIT(2)` | Interrupt enable on IOC (I/O completion) |
| `[3]` | `IE_IOC_DMACPL` | `BIT(3)` | Interrupt enable on DMA completion |
| `[23]` | `UHS` | `BIT(23)` | Upper half space (use upper 32-bit address) |
| `[31:24]` | `PTEC` | `GENMASK(31,24)` | PRD Table Entry Count (number of PRD entries for TXDMA) |

### WRITE_INT_STS Bit Fields (Offset 0x09C)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `CMPL_STATUS` | `BIT(0)` | Write DMA completion status |
| `[1]` | `ERROR_STS` | `BIT(1)` | Write DMA error status |
| `[2]` | `IOC_STS` | `BIT(2)` | Write DMA IOC status |
| `[3]` | `ACTIVE` | `BIT(3)` | Write DMA active (RO) |

### READ_DMA_CNTRL Bit Fields (Offset 0x10C/0x20C/0x2CC per channel)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `START` | `BIT(0)` | Start read DMA transfer |
| `[1]` | `IE_ERROR` | `BIT(1)` | Interrupt enable on error |
| `[2]` | `IE_IOC` | `BIT(2)` | Interrupt enable on IOC |
| `[3]` | `IE_STALL` | `BIT(3)` | Interrupt enable on stall (PRD exhaustion) |
| `[4]` | `IE_NDDI` | `BIT(4)` | Interrupt enable on non-DMA device interrupt |
| `[5]` | `IE_EOF` | `BIT(5)` | Interrupt enable on end-of-frame |
| `[7]` | `IE_DMACPL` | `BIT(7)` | Interrupt enable on DMA completion |
| `[15:8]` | `TPCRP` | `GENMASK(15,8)` | Total PRD Count Read Pointer (HW-managed) |
| `[23:16]` | `TPCWP` | `GENMASK(23,16)` | Total PRD Count Write Pointer (SW sets) |
| `[28]` | `INT_SW_DMA_EN` | `BIT(28)` | Software DMA interrupt enable (SWDMA channel only) |
| `[29]` | `SOO` | `BIT(29)` | Start-on-one (start DMA with single PRD entry) |
| `[30]` | `UHS` | `BIT(30)` | Upper half space (use upper 32-bit address) |
| `[31]` | `TPCPR` | `BIT(31)` | Total PRD Count Pointer Reset |

### READ_DMA_INT_STS Bit Fields (Offset 0x110/0x210/0x2D0 per channel)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `DMACPL_STS` | `BIT(0)` | Read DMA completion status |
| `[1]` | `ERROR_STS` | `BIT(1)` | Read DMA error status |
| `[2]` | `IOC_STS` | `BIT(2)` | Read DMA IOC status |
| `[3]` | `STALL_STS` | `BIT(3)` | Read DMA stall status (PRD exhaustion) |
| `[4]` | `NONDMA_INT_STS` | `BIT(4)` | Non-DMA interrupt status |
| `[5]` | `EOF_INT_STS` | `BIT(5)` | End-of-frame interrupt status |
| `[8]` | `ACTIVE` | `BIT(8)` | Read DMA active (RO) |

### RPRD_CNTRL Bit Fields (Offset 0x108/0x208/0x2C8 per channel)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[6:0]` | `PCD` | `GENMASK(6,0)` | PRD Count Decrement |
| `[15:8]` | `PTEC` | `GENMASK(15,8)` | PRD Table Entry Count |
| `[19:16]` | `PREFETCH_WM` | `GENMASK(19,16)` | PRD Prefetch Watermark |

### Extended Register Map (0x12E4–0x131C, from Linux kernel `intel-thc-hw.h`)

| Offset | Register | Key Fields | Purpose |
|--------|----------|-----------|---------|
| `0x2E4` | `THC_M_PRT_SW_DMA_PRD_TABLE_LEN` | SWDMA PRD length | SWDMA PRD table length |
| `0x2E8` | `THC_M_PRT_COALESCE_CNTRL_1` | Coalesce control 1 | Frame coalescing control (RXDMA ch1) |
| `0x2EC` | `THC_M_PRT_COALESCE_CNTRL_2` | Coalesce control 2 | Frame coalescing control (RXDMA ch2) |
| `0x2F0` | `THC_M_PRT_PRD_EMPTY_CNT_1` | PRD empty count 1 | PRD empty descriptor count (ch1) |
| `0x2F4` | `THC_M_PRT_PRD_EMPTY_CNT_2` | PRD empty count 2 | PRD empty descriptor count (ch2) |
| `0x2F8` | `THC_M_PRT_COALESCE_STS_1` | Coalesce status 1 | Coalescing status (ch1) |
| `0x2FC` | `THC_M_PRT_COALESCE_STS_2` | Coalesce status 2 | Coalescing status (ch2) |
| `0x300` | `THC_M_PRT_SPI_DUTYC_CFG` | SPI duty cycle | SPI clock duty cycle configuration |
| `0x304` | `THC_M_PRT_SW_SEQ_I2C_WR_CNTRL` | I2C write control | I2C PIO write sequence control |
| `0x308` | `THC_M_PRT_TIMESTAMP_1` | RXDMA1 timestamp | DMA frame timestamp for RXDMA channel 1 (per-channel, NOT low half of a 64-bit timestamp) |
| `0x30C` | `THC_M_PRT_TIMESTAMP_2` | RXDMA2 timestamp | DMA frame timestamp for RXDMA channel 2 (per-channel, NOT high half of a 64-bit timestamp) |
| `0x310` | `THC_M_PRT_SYNC_TIMESTAMP` | Sync timestamp | Display sync timestamp |
| `0x314` | `THC_M_PRT_DISP_SYNC` | Display sync 1 | Display synchronization config |
| `0x318` | `THC_M_PRT_DISP_SYNC_2` | Display sync 2 | Display synchronization config 2 |
| `0x31C` | `THC_M_PRT_I2C_CFG` | I2C config | HIDI2C specific configuration |

> **Note**: Offsets above are relative to port base (0x1000 for Port 0, 0x2000 for Port 1). The `max_register` for the regmap is `0x1320` (absolute). Source: Linux kernel `intel-thc-hw.h` (v6.17+).

### SW_SEQ_I2C_WR_CNTRL Bit Fields (Offset 0x304 — I2C PIO Write Control)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[23]` | `THC_I2C_RW_PIO_EN` | `BIT(23)` | Enable I2C read/write PIO mode |
| `[31:26]` | `THC_PIO_I2C_WBC` | `GENMASK(31,26)` | PIO I2C write byte count |

> **Usage**: When performing I2C PIO writes, set `THC_I2C_RW_PIO_EN` and program `THC_PIO_I2C_WBC` with the write byte count before issuing the PIO command via `SW_SEQ_CNTRL.TSSGO`.

### RPRD_CNTRL_SW — I2C-Specific Bit Fields (Offset 0x2C8)

In addition to the standard RPRD_CNTRL fields (PCD, PTEC, PREFETCH_WM), the SWDMA channel's RPRD_CNTRL_SW register has I2C-specific fields:

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[23]` | `THC_SWDMA_I2C_RX_DLEN_EN` | `BIT(23)` | Enable I2C SWDMA RX data length |
| `[31:26]` | `THC_SWDMA_I2C_WBC` | `GENMASK(31,26)` | SWDMA I2C write byte count |

> **Usage**: Used by the QuickI2C driver when configuring SWDMA for I2C read operations. `THC_SWDMA_I2C_RX_DLEN_EN` enables the hardware to use the device-reported data length for SWDMA RX transfers.

### HIDSPI Default Configuration Constants (from `intel-thc-hw.h`)

These constants define the default ICR header field layout for HIDSPI devices, used to program `DEVINT_CFG_1` and `DEVINT_CFG_2`:

| Constant | Value | Description |
|----------|-------|-------------|
| `THC_BIT_OFFSET_INTERRUPT_TYPE` | 4 | INT_TYPE field starts at bit 4 of ICR |
| `THC_BIT_LENGTH_INTERRUPT_TYPE` | 4 | INT_TYPE field is 4 bits wide |
| `THC_BIT_OFFSET_LAST_FRAGMENT_FLAG` | 22 | Last fragment flag at bit 22 |
| `THC_BIT_OFFSET_MICROFRAME_SIZE` | 8 | Microframe size starts at bit 8 |
| `THC_BIT_LENGTH_MICROFRAME_SIZE` | 14 | Microframe size is 14 bits wide |
| `THC_UNIT_MICROFRAME_SIZE` | 2 | MFS unit is 2^2 = 4 bytes |
| `THC_BITMASK_INTERRUPT_TYPE_DATA` | 1 | Bitmask for data interrupt type |
| `THC_BITMASK_INVALID_TYPE_DATA` | 2 | Bitmask for invalid interrupt type |

> **Usage**: `thc_spi_read_config()` uses these constants to program the DEVINT_CFG_1/2 registers based on ACPI DSM-reported values or these defaults. The constants define the Microsoft HIDSPI protocol's ICR header bit layout.

### DEVINT_CFG_1 Bit Fields (Offset 0x0EC)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[4:0]` | `INTTYP_OFFSET` | `GENMASK(4,0)` | INT_TYPE field offset within ICR header |
| `[9:5]` | `INTTYP_LEN` | `GENMASK(9,5)` | INT_TYPE field bit length |
| `[14:10]` | `EOF_OFFSET` | `GENMASK(14,10)` | End-of-Frame bit offset |
| `[15]` | `SEND_ICR_US_EN` | `BIT(15)` | Embed interrupt cause in microframe/PRD |
| `[31:16]` | `INTTYP_DATA_VAL` | `GENMASK(31,16)` | Device interrupt type data value |

> **⚠️ CORRECTION (v2)**: Previous version had wrong bit positions (3:0/7:4/11:8 etc.) based on HAS field names. The kernel GENMASK values above are authoritative — verified from `intel-thc-hw.h`. The HAS fields `mfs_offset`, `mfs_length`, `eof_bit_polarity`, `devint_mask` are NOT present in the kernel register definition — they may be in a different register or HAS-only constructs.

### DEVINT_CFG_2 Bit Fields (Offset 0x0F0)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[4:0]` | `UFSIZE_OFFSET` | `GENMASK(4,0)` | Microframe size field offset within ICR header |
| `[9:5]` | `UFSIZE_LEN` | `GENMASK(9,5)` | Microframe size field bit length |
| `[15:12]` | `UFSIZE_UNIT` | `GENMASK(15,12)` | Microframe size unit (power of 2) |
| `[16]` | `FTYPE_IGNORE` | `BIT(16)` | Ignore frame type field in ICR header |
| `[17]` | `FTYPE_VAL` | `BIT(17)` | Frame type value (when FTYPE_IGNORE=0) |
| `[24]` | `RXDMA_ADDRINC_DIS` | `BIT(24)` | Disable RXDMA address auto-increment |
| `[25]` | `TXDMA_ADDRINC_DIS` | `BIT(25)` | Disable TXDMA address auto-increment |
| `[26]` | `RXDMA_PKT_STRM_EN` | `BIT(26)` | Enable RXDMA packet streaming mode (frames >4KB) |
| `[27]` | `TXDMA_PKT_STRM_EN` | `BIT(27)` | Enable TXDMA packet streaming mode |
| `[28]` | `DEVINT_POL` | `BIT(28)` | Device interrupt polarity |

> **⚠️ CORRECTION (v3)**: Previous version stated "Bits[23:0] not defined in kernel" — WRONG. Kernel defines 5 fields in bits[17:0]: UFSIZE_OFFSET(4:0), UFSIZE_LEN(9:5), UFSIZE_UNIT(15:12), FTYPE_IGNORE(16), FTYPE_VAL(17). These configure how THC parses the microframe size and frame type from the device interrupt cause register (ICR header). Bits[11:10], [23:18], and [31:29] remain undefined. `RXDMA_ADDRINC_DIS`/`TXDMA_ADDRINC_DIS` disable automatic address increment during DMA — used for memory-mapped device registers that auto-advance.

### Config Space Registers (from port base offset)
- `THC_CFG_UR_STS_CTL` (`0x70`): `FD` (Function Disable bit)
- `THC_CFG_PMD_PMCSRBSE_PMCSR` (`0x74`): `PWRST` (Power State: 0=D0, 3=D3)
- `THC_CFG_PCE` (`0xA2`): `HAE`(5), `SE`(3), `D3HE`(2), `I3E`(1), `SPE`(0) — Clock/Power gating enables

### PRT_CONTROL Register Bit Fields (Offset 0x008)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `TSFTRST` | `BIT(0)` | Touch soft reset |
| `[1]` | `THC_DEVINT_QUIESCE_EN` | `BIT(1)` | Device interrupt quiesce enable |
| `[2]` | `THC_DEVINT_QUIESCE_HW_STS` | `BIT(2)` | Quiesce HW status (RO) |
| `[3]` | `DEVRST` | `BIT(3)` | Device reset assertion |
| `[13]` | `THC_DRV_LOCK_EN` | `BIT(13)` | Driver lock (prevents register modification — in `AVOID_THC_BITS`) |
| `[18:16]` | `THC_INSTANCE_INDEX` | `GENMASK(18,16)` | Instance index |
| `[22:20]` | `PORT_INDEX` | `GENMASK(22,20)` | Port index |
| `[25:24]` | `THC_ARB_POLICY` | `GENMASK(25,24)` | Arbitration policy: `0`=Packet, `1`=µFrame, `2`=Frame boundary |
| `[27]` | `THC_BIOS_LOCK_EN` | `BIT(27)` | BIOS lock (prevents register modification — in `AVOID_THC_BITS`) |
| `[28]` | `PORT_SUPPORTED` | `BIT(28)` | Port is supported (RO) |
| `[29]` | `SPI_IO_RDY` | `BIT(29)` | SPI IO ready (RCOMP complete) — RO |
| `[31:30]` | `PORT_TYPE` | `GENMASK(31,30)` | `00`=SPI, `01`=I2C |

> **⚠️ CORRECTION (v3)**: Previous version had QUIESCE_EN at BIT(0) and QUIESCE_HW_STS at BIT(1) — shifted by 1. Kernel defines TSFTRST=BIT(0), QUIESCE_EN=BIT(1), QUIESCE_HW_STS=BIT(2). Also added missing fields: DRV_LOCK_EN(13), INSTANCE_INDEX(18:16), PORT_INDEX(22:20), ARB_POLICY(25:24), BIOS_LOCK_EN(27), PORT_SUPPORTED(28). SPI_IO_RDY is BIT(29) not BIT(8). SPI_BUS_RECOVERY_CNT at GENMASK(7,4) is NOT defined in kernel — may be HAS-only.

### Device Interrupt Quiesce Flow

To safely quiesce device interrupts (required before DMA reconfiguration or PIO access to bulk address space):

1. Set `THC_M_PRT_CONTROL.THC_DEVINT_QUIESCE_EN` (bit 1) = 1
2. Poll `THC_M_PRT_CONTROL.THC_DEVINT_QUIESCE_HW_STS` (bit 2) until = 1
3. Perform DMA stop/reconfigure or PIO operations
4. Clear `THC_DEVINT_QUIESCE_EN` (bit 1) = 0 to resume interrupt delivery

> **Note**: The quiesce flow ensures no device interrupts are processed while DMA or PIO state is being modified. The HW status bit confirms the quiesce took effect. Used by both SPI and I2C paths during suspend/resume and PIO bulk operations.

### SPI_CFG Register Bit Fields (Offset 0x010)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[1:0]` | `SPI_TRDC` | `GENMASK(1,0)` | SPI read dummy cycles config |
| `[3:2]` | `SPI_TRMODE` | `GENMASK(3,2)` | SPI read IO mode: `00`=Single, `01`=Dual, `10`=Quad, `11`=Quad-Parallel |
| `[6:4]` | `SPI_TCRF` | `GENMASK(6,4)` | SPI read frequency divider (3-bit, see `thc_spi_frq_div`) |
| `[15:7]` | `SPI_RD_MPS` | `GENMASK(15,7)` | Read Max Packet Size (9-bit) |
| `[19:18]` | `SPI_TWMODE` | `GENMASK(19,18)` | SPI write IO mode |
| `[22:20]` | `SPI_TCWF` | `GENMASK(22,20)` | SPI write frequency divider (3-bit) |
| `[23]` | `SPI_LOW_FREQ_EN` | `BIT(23)` | Low frequency enable (DIV ×8 — e.g., DIV=3 → 125/24 ≈ 5.2 MHz) |
| `[31:24]` | `SPI_WR_MPS` | `GENMASK(31,24)` | Write Max Packet Size (8-bit) |

> **⚠️ CORRECTION (v3)**: Completely rewritten. Previous version had wrong bit positions throughout: SPI_TCRF was at GENMASK(2,0) — actually GENMASK(6,4). SPI_LOW_FREQ_EN was at BIT(3) — actually BIT(23). SPI_IO_MODE at GENMASK(5,4) does not exist — replaced by separate SPI_TRMODE(3:2) for read and SPI_TWMODE(19:18) for write. SPI_RD_MPS is 9-bit GENMASK(15,7) not 10-bit GENMASK(15,6). SPI_WR_MPS is 8-bit GENMASK(31,24) not 10-bit GENMASK(25,16). SPI_CSA_CK_DELAY_EN and SPI_CSA_CK_DELAY_VAL are NOT in this register — they are in `SPI_DUTYC_CFG` (offset 0x300).

### SPI_DUTYC_CFG Register Bit Fields (Offset 0x300)

> **Note**: Offset 0x300 is relative to port base. For Port 0 (base 0x1000), the absolute MMIO offset is 0x1300.

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[3:0]` | `SPI_CSA_CK_DELAY_VAL` | `GENMASK(3,0)` | CS-to-clock delay value (default: 4 clock cycles) |
| `[25]` | `SPI_CSA_CK_DELAY_EN` | `BIT(25)` | CS-to-clock delay enable |

> **Note**: CS assertion delay is enabled by kernel during SPI `thc_port_select()` with default value of 4 (`THC_CSA_CK_DELAY_VAL_DEFAULT`). This register is separate from `SPI_CFG`.

### SPI_ICRRD_OPCODE Register — I2C Dual-Purpose Fields (Offset 0x014)

When `PORT_TYPE=I2C`, the `SPI_ICRRD_OPCODE` register (offset 0x014) is reused with different bit field semantics for I2C configuration:

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[15:0]` | `I2C_MAX_SIZE` | `GENMASK(15,0)` | Maximum I2C transfer size (bytes) |
| `[23:16]` | `I2C_INTERVAL` | `GENMASK(23,16)` | I2C polling interval |
| `[30]` | `I2C_INTERVAL_EN` | `BIT(30)` | Enable I2C polling interval |
| `[31]` | `I2C_MAX_SIZE_EN` | `BIT(31)` | Enable I2C max transfer size limit |

When `PORT_TYPE=SPI`, the same register holds SPI opcode fields:

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[15:8]` | `SPI_QIO` | `GENMASK(15,8)` | Quad IO read opcode |
| `[23:16]` | `SPI_DIO` | `GENMASK(23,16)` | Dual IO read opcode |
| `[31:24]` | `SPI_SIO` | `GENMASK(31,24)` | Single IO read opcode |

> **Note**: The register name (`SPI_ICRRD_OPCODE`) is misleading when used in I2C mode. The kernel defines separate `_I2C_*` and `_SPI_*` field macros for the same register offset. The I2C fields configure transfer size limits and polling behavior for the QuickI2C driver.

### SPI Clock Frequency Reference

THC base clock: **`THC_SSC_CLK` = 125 MHz** (all supported platforms).

The `SPI_TCRF` (read) and `SPI_TCWF` (write) 3-bit divider fields in `SPI_CFG` select the SPI clock frequency:

| Divider Value | High Freq (MHz) | Low Freq (`SPI_LOW_FREQ_EN`=1, ÷8) (MHz) | Kernel Usage |
|---------------|-----------------|-------------------------------------------|--------------|
| 0 | Reserved | Reserved | — |
| 1 | 125.0 | 15.625 | LOW only (15.625 MHz) |
| 2 | 62.5 | 7.8125 | LOW only (7.813 MHz) |
| 3 | 41.667 | 5.208 | HIGH (41.667 MHz) |
| 4 | 31.25 | 3.906 | HIGH (31.25 MHz) |
| 5 | 25.0 | 3.125 | HIGH (25 MHz) |
| 6 | 20.833 | 2.604 | HIGH (20.833 MHz) |
| 7 | 17.857 | 2.232 | HIGH (17.857 MHz) |

> **Formula**: `SPI_CLK = THC_SSC_CLK / divider` for high freq; `SPI_CLK = THC_SSC_CLK / (divider × 8)` for low freq. `SPI_LOW_FREQ_EN` threshold = 17.857 MHz (dividers 1-2 always use LOW mode in kernel). Gen4.1+ (PTL/WCL) adds **half-divider** support via DCG — see `fv-thc/hidspi` for details.
> **⚠️ Correction (Phase 7)**: Previous version used 128 MHz base and `/(divider×2)` formula — WRONG. Linux kernel `thc_get_spi_freq_div_val()` confirms 125 MHz base with direct division. Only 7 frequencies are mapped by the kernel driver.

### SW_SEQ_CNTRL Register Bit Fields (Offset 0x040)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `TSSGO` | `BIT(0)` | PIO trigger — set to 1 to start |
| `[1]` | `THC_SS_CD_IE` | `BIT(1)` | PIO interrupt enable (completion interrupt) |
| `[15:8]` | `THC_SS_CMD` | `GENMASK(15,8)` | PIO opcode (8-bit) |
| `[31:16]` | `THC_SS_BC` | `GENMASK(31,16)` | PIO byte count (16-bit) |

> **⚠️ CORRECTION (v3)**: Previous version had completely wrong field names and positions. `THC_SS_CD` at GENMASK(8,1) was actually `THC_SS_CD_IE` at BIT(1) (interrupt enable, not byte count). `THC_SS_CMD` was at GENMASK(13,9) — actually GENMASK(15,8). `THC_SS_DEV_ADDR` at GENMASK(31,14) does not exist — replaced by `THC_SS_BC` (byte count) at GENMASK(31,16). The device address for SPI PIO is written to `SW_SEQ_DATA0_ADDR` (offset 0x048), not packed into the control register.

### SW_SEQ_STS Register Bit Fields (Offset 0x044)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `TSSDONE` | `BIT(0)` | PIO sequence done |
| `[1]` | `THC_SS_ERR` | `BIT(1)` | PIO sequence error |
| `[3]` | `THC_SS_CIP` | `BIT(3)` | PIO cycle in progress |

### INT_EN Register Bit Fields (Offset 0x020)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `SIPE` | `BIT(0)` | SPI Interrupt Pending Enable |
| `[1]` | `SBO` | `BIT(1)` | SPI Bus Ownership |
| `[2]` | `SIDR` | `BIT(2)` | SPI Interrupt Data Received |
| `[3]` | `SOFB` | `BIT(3)` | SPI Overflow Buffer |
| `[9]` | `INVLD_DEV_ENTRY_INT_EN` | `BIT(9)` | Invalid device entry interrupt enable |
| `[10]` | `FRAME_BABBLE_ERR_INT_EN` | `BIT(10)` | Frame babble error interrupt enable |
| `[12]` | `BUF_OVRRUN_ERR_INT_EN` | `BIT(12)` | Buffer overrun error interrupt enable |
| `[13]` | `PRD_ENTRY_ERR_INT_EN` | `BIT(13)` | PRD entry error interrupt enable |
| `[14]` | `DISP_SYNC_EVT_INT_EN` | `BIT(14)` | Display sync event interrupt enable |
| `[15]` | `DEV_RAW_INT_EN` | `BIT(15)` | Device raw interrupt enable |
| `[16]` | `FATAL_ERR_INT_EN` | `BIT(16)` | Fatal error interrupt enable |
| `[17]` | `I2C_IC_RX_UNDER_INT_EN` | `BIT(17)` | I2C RX underflow interrupt enable |
| `[18]` | `I2C_IC_RX_OVER_INT_EN` | `BIT(18)` | I2C RX overflow interrupt enable |
| `[19]` | `I2C_IC_RX_FULL_INT_EN` | `BIT(19)` | I2C RX FIFO full interrupt enable |
| `[20]` | `I2C_IC_TX_OVER_INT_EN` | `BIT(20)` | I2C TX overflow interrupt enable |
| `[21]` | `I2C_IC_TX_EMPTY_INT_EN` | `BIT(21)` | I2C TX empty interrupt enable |
| `[22]` | `I2C_IC_TX_ABRT_INT_EN` | `BIT(22)` | I2C TX abort interrupt enable |
| `[24]` | `I2C_IC_SCL_STUCK_AT_LOW_DET_INT_EN` | `BIT(24)` | I2C SCL stuck at low interrupt enable |
| `[25]` | `I2C_IC_STOP_DET_INT_EN` | `BIT(25)` | I2C stop detect interrupt enable |
| `[26]` | `I2C_IC_START_DET_INT_EN` | `BIT(26)` | I2C start detect interrupt enable |
| `[27]` | `I2C_IC_MST_ON_HOLD_INT_EN` | `BIT(27)` | I2C master on hold interrupt enable |
| `[29]` | `TXN_ERR_INT_EN` | `BIT(29)` | Transaction error interrupt enable |
| `[31]` | `GBL_INT_EN` | `BIT(31)` | Global interrupt enable (master switch) |

> **⚠️ CORRECTION (v3)**: Completely rewritten. Previous version had GBL_INT_EN at BIT(0) — actually BIT(31). TXN_ERR_INT_EN was at BIT(1) — actually BIT(29). FATAL_ERR_INT_EN was at BIT(2) — actually BIT(16). The old layout showed DMA channel enables (NONDMA/RXDMA/TXDMA/SWDMA/PIO/STALL) at bits 3-11 — these do NOT exist in INT_EN. Per-DMA interrupts are enabled via per-channel `READ_DMA_CNTRL_x` registers (IE_ERROR, IE_IOC, IE_STALL, IE_NDDI, IE_EOF, IE_DMACPL bits), NOT via INT_EN. I2C sub-IP bits are at 17-27 (not 17-27 as before, but bit assignments were shifted). Note: BIT(23) (ACTIVITY) has NO enable — only appears in INT_STATUS.

### INT_STATUS Register Bit Fields (Offset 0x024)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[14]` | `DISP_SYNC_EVT_INT_STS` | `BIT(14)` | Display sync event interrupt status |
| `[15]` | `DEV_RAW_INT_STS` | `BIT(15)` | Device raw interrupt status |
| `[17]` | `I2C_IC_RX_UNDER_INT_STS` | `BIT(17)` | I2C RX underflow status |
| `[18]` | `I2C_IC_RX_OVER_INT_STS` | `BIT(18)` | I2C RX overflow status |
| `[19]` | `I2C_IC_RX_FULL_INT_STS` | `BIT(19)` | I2C RX FIFO full status |
| `[20]` | `I2C_IC_TX_OVER_INT_STS` | `BIT(20)` | I2C TX overflow status |
| `[21]` | `I2C_IC_TX_EMPTY_INT_STS` | `BIT(21)` | I2C TX empty status |
| `[22]` | `I2C_IC_TX_ABRT_INT_STS` | `BIT(22)` | I2C TX abort status |
| `[23]` | `I2C_IC_ACTIVITY_INT_STS` | `BIT(23)` | I2C activity status (RO — no enable bit) |
| `[24]` | `I2C_IC_SCL_STUCK_AT_LOW_INT_STS` | `BIT(24)` | I2C SCL stuck at low status |
| `[25]` | `I2C_IC_STOP_DET_INT_STS` | `BIT(25)` | I2C stop detect status |
| `[26]` | `I2C_IC_START_DET_INT_STS` | `BIT(26)` | I2C start detect status |
| `[27]` | `I2C_IC_MST_ON_HOLD_INT_STS` | `BIT(27)` | I2C master on hold status |
| `[28]` | `TXN_ERR_INT_STS` | `BIT(28)` | Transaction error occurred |
| `[30]` | `FATAL_ERR_INT_STS` | `BIT(30)` | Fatal error occurred |

> **⚠️ CORRECTION (v3)**: Completely rewritten. Previous version had TXN_ERR at BIT(1) — actually BIT(28). FATAL_ERR was at BIT(2) — actually BIT(30). The old layout showed per-DMA interrupt status bits (NONDMA/RXDMA/TXDMA/SWDMA/PIO/STALL) at bits 3-12 — these do NOT exist in INT_STATUS. Per-DMA interrupt status is in per-channel `READ_DMA_INT_STS_x` registers (DMACPL_STS, ERROR_STS, IOC_STS, STALL_STS, NONDMA_INT_STS, EOF_INT_STS, ACTIVE bits). The kernel reads NONDMA_INT_STS from `READ_DMA_INT_STS_1` BIT(4), and checks TXN_ERR_INT_STS_BIT=BIT(28) / TXN_FATAL_INT_STS_BIT=BIT(30) from INT_STATUS. BIT(23) ACTIVITY appears in status but has NO corresponding enable bit.

### ERR_CAUSE Register Bit Fields (Offset 0x028)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[9]` | `INVLD_DEV_ENTRY` | `BIT(9)` | Invalid device entry |
| `[10]` | `FRAME_BABBLE_ERR` | `BIT(10)` | Frame babble error (unexpected data on bus) |
| `[12]` | `BUF_OVRRUN_ERR` | `BIT(12)` | Buffer overrun error |
| `[13]` | `PRD_ENTRY_ERR` | `BIT(13)` | PRD entry error (bad descriptor) |
| `[23:16]` | `FATAL_ERR_CAUSE` | `GENMASK(23,16)` | Fatal error cause code (8-bit) |

> **⚠️ CORRECTION (v3)**: Previous version had INVLD_DEV_ENTRY at BIT(0) — actually BIT(9). BUF_OVRRUN_ERR was at BIT(1) — actually BIT(12). FATAL_ERR_CAUSE was at GENMASK(31,28) — actually GENMASK(23,16). Added missing fields: FRAME_BABBLE_ERR at BIT(10) and PRD_ENTRY_ERR at BIT(13).

## PIO (Programmed I/O) Flow

### SPI PIO Flow
1. Set Port Control (`0x1008`): Write `0x10000008` to set port type=0 (SPI)
2. Clear Status (`0x1044`): Write to clear pending errors/completion
3. Set Address (`0x1048`): Device target register address
4. Set Opcode + Length (`0x1040`): Opcode + byte count
5. Trigger (`0x1040`): Set `TSSGO` (bit 0 = 1)
6. Poll (`0x1044`): Wait for `TSSDONE` (bit 0) with 1-second timeout (kernel: `THC_PIO_DONE_TIMEOUT_US = USEC_PER_SEC`), polling at `THC_REGMAP_POLLING_INTERVAL_US` = 10µs interval
7. Read Data (`0x1048`-`0x1088`): Fetch response

> **Back-to-back PIO rule (SwAS)**: A new PIO operation MUST NOT be issued until the prior one completes. The driver must confirm `TSSDONE` (or `THC_SS_ERR`) is set and then clear both status bits before initiating the next PIO. Violating this sequencing constraint is a programming error that can corrupt the PIO state machine and produce undefined register read-back values.

**SPI PIO Opcodes** (canonical, Gen4.0+):
- `0x4`: SPI TIC Read — PIO_OP_SPI_TIC_READ (register reads, descriptor reads)
- `0x6`: SPI TIC Write — PIO_OP_SPI_TIC_WRITE (device commands, single report writes)
- `0x8`: SPI Bulk Write — PIO_OP_SPI_BULK_WR (**HAS-defined only; not present in kernel header** — only 0x4 and 0x6 are defined in kernel source)
- `0x2`: Legacy SPI Register Read (Gen2.0 only — **not used by current drivers**)

### I2C PIO Flow
I2C PIO must first configure the Synopsys DW I2C APB Sub-IP via opcodes 0x12/0x13.

**I2C PIO Opcodes**:
- `0x12`: I2C-SubIP APB Register Read
- `0x13`: I2C-SubIP APB Register Write
- `0x14`: I2C Device Read
- `0x18`: I2C Device Write
- `0x1C`: I2C Write+Read PIO (Repeated START, used for descriptors/GET_REPORT) — **I2C-only; returns `-EINVAL` for SPI port type** (kernel: `thc_tic_pio_write_and_read`)

### PIO Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_PIO_BC` | 64 bytes | Maximum byte count per single PIO transfer (**HAS limitation; not enforced in kernel** — `THC_SS_BC` is 16-bit GENMASK(31,16) allowing up to 65535) |
| `PIO_CYCLE_TIMEOUT` | 1 second | Timeout for PIO cycle completion — kernel: `THC_PIO_DONE_TIMEOUT_US = USEC_PER_SEC` (regmap_read_poll_timeout) |
| `THC_SSC_CLK` | 125 MHz | THC base SSC clock frequency (all supported platforms) |

> **Note**: `MAX_PIO_BC` = 64 bytes is the maximum data payload per PIO cycle. The `SW_SEQ_DATA[0-16]` registers provide 17 DWORDs (68 bytes) of data space, but the maximum transfer per cycle is limited to 64 bytes. For larger transfers, multiple PIO cycles are required.

## Synopsys DW I2C Sub-IP Initialization

THC accesses I2C sub-IP via APB registers (using PIO opcode 0x13). 
Initialization Sequence (12-step, HAS-based):
1. `IC_ENABLE` (`0x6C`) = 0 (disable)
2. `IC_CON` (`0x00`) = `0x0663` (Master, Fast, 7-bit, Restart EN, Slave DIS, RX_FIFO_FULL_HLD_CTRL, STOP_DET_IF_MASTER_ACTIVE)
3. `IC_TAR` (`0x04`) = Device Address (e.g., `0x0A` WACOM, `0x16` ELAN)
4. `IC_SS_SCL_HCNT/LCNT` (`0x14/0x18`) or `IC_FS_SCL_HCNT/LCNT` (`0x1C/0x20`) = Timing
5. `IC_INTR_MASK` (`0x30`) = `0x7FFF` (All interrupts)
6. `IC_RX_TL` (`0x38`) = 62 (RX threshold)
7. `IC_TX_TL` (`0x3C`) = 0 (TX threshold)
8. `IC_DMA_CR` (`0x88`) = `0x03` (TX+RX DMA enable)
9. `IC_DMA_TDLR` (`0x8C`) = 7
10. `IC_DMA_RDLR` (`0x90`) = 7
11. `IC_SDA_HOLD` (`0x7C` kernel / `0x9C` HAS) = Configured value
12. `IC_ENABLE` (`0x6C`) = 1 (enable)

> **⚠️ IC_SDA_HOLD offset discrepancy**: The Linux kernel defines `IC_SDA_HOLD` at offset `0x7C` (`THC_I2C_IC_SDA_HOLD = 0x7C` in `intel-thc-hw.h`), while the HAS documents it at `0x9C`. Verify which offset is correct for your platform.
> **⚠️ Kernel vs HAS**: The Linux kernel `thc_i2c_subip_init()` uses **10 PIO operations** (disable → TAR → speed → INTR_MASK → RX_TL → TX_TL → DMA_CR → DMA_TDLR → DMA_RDLR → enable) — it omits both `IC_CON` (step 2) and `IC_SDA_HOLD` (step 11) from the HAS sequence. The kernel ignores ACPI ISUB `sda_hold` values entirely during the core init. If `IC_SDA_HOLD` is provided via ACPI ISUB data, it is NOT applied. Always verify against the HAS for the authoritative init sequence.

### Post-Init: ARB_POLICY Configuration
After I2C sub-IP init, the kernel forces the arbitration policy for I2C mode:
- `THC_M_PRT_CONTROL.arb_policy` = **FRAME_BOUNDARY** (`THC_ARB_POLICY_FRAME_BOUNDARY`)
- This ensures DMA arbitration occurs at I2C frame boundaries, preventing mid-transaction bus conflicts
- This is set unconditionally for I2C mode (not configurable via ACPI)

## PIO Safety Restrictions (from HAS)

> **⚠️ HAS RULE**: "SW must not access bulk address space (≥0x1000) via PIO while RXDMA is running."
> **⚠️ HAS RULE**: `THC_M_PRT_SPI_CFG` cannot be written/updated when TX/RX DMA is running or PIO is running cycles on the bus.

### DMA Engine Stop/Restore During PIO

When performing PIO operations that require DMA to be stopped (per HAS rules above):

1. **Quiesce interrupts**: Set `DEVINT_QUIESCE_EN` → poll `QUIESCE_HW_STS` (see quiesce flow above)
2. **Stop DMA**: Clear `START` bit in `READ_DMA_CNTRL_x` for active RXDMA channels
3. **Wait**: Poll for DMA engine to become idle (check DMA status registers)
4. **Perform PIO**: Execute SW_SEQ operation (set opcode/byte count, trigger TSSGO, poll TSSDONE)
5. **Restore DMA**: Re-enable RXDMA by setting `START` bit in `READ_DMA_CNTRL_x`
6. **Unquiesce**: Clear `DEVINT_QUIESCE_EN` to resume interrupt delivery

> **Pattern**: The test scripts implement this as a `quiesce → stop_dma → pio_operation → restore_dma → unquiesce` sequence to ensure bus exclusion between DMA and PIO operations. This is critical for register reads during active touch sessions.

## PCI Configuration Space Register Map (23 registers)

| CFG Addr | Default | Restore | Register | Description |
|----------|---------|---------|----------|-------------|
| `0x00` | `0000_8086h` | No | `THC_CFG_DID_VID` | Device ID and Vendor ID |
| `0x04` | `0290_0000h` | 2.01 | `THC_CFG_STS_CMD` | Status and Command |
| `0x08` | `0901_0000h` | 2.02 | `THC_CFG_CC_RID` | Revision ID and Class Code |
| `0x10` | `0000_0004h` | 2.04 | `THC_CFG_BAR0_LOW` | BAR0 MMIO Low |
| `0x14` | `0000_0000h` | 2.05 | `THC_CFG_BAR0_HI` | BAR0 MMIO High |
| `0x40` | `0000_0000h` | 2.08 | `THC_CFG_UR_STS_CTL` | Unsupported Request Status (FD bit) |
| `0x50` | `0080_7005h` | 2.09 | `THC_CFG_MSIMC_MSINP_MSICID` | MSI Control/Capability |
| `0x54` | `0000_0000h` | 2.10 | `THC_CFG_MSIMA` | MSI Message Address |
| `0x58` | `0000_0000h` | 2.11 | `THC_CFG_MSIMUA` | MSI Message Upper Address |
| `0x5C` | `0000_0000h` | 2.12 | `THC_CFG_MSIMD` | MSI Message Data |
| `0x74` | `0000_0008h` | 2.14 | `THC_CFG_PMD_PMCSRBSE_PMCSR` | PM Control/Status |
| `0x90` | `F014_0009h` | No | `THC_CFG_DEVIDLE` | Device Idle Capability |
| `0x98` | `0000_0000h` | No | `THC_CFG_SWLTRPTR` | SW LTR Pointer |
| `0xA2` | `0028h` | 5.10 | `THC_CFG_PCE` | Power Control Enables (HAE/SE/D3HE/I3E/SPE) |

> **Restore Order**: Phase 1.xx = SAI policies, Phase 2.xx = PCI config, Phase 3.xx = MMIO + sideband, Phase 5.xx = PCE/CONTROL. "Driver reinitialize" = DMA registers reprogrammed by driver.

## IOSF Sideband Register Map (Port 0x39, 20 registers)

| SB Addr | Default | Register | Description |
|---------|---------|----------|-------------|
| `0x00` | `0000_CCC0h` | `THC_SB_PR_CDC_CFG` | Primary Clock Domain CDC Config |
| `0x04` | `0000_CCC0h` | `THC_SB_SD_CDC_CFG` | Side Clock Domain CDC Config |
| `0x08` | `0000_0000h` | `THC_SB_SSC_CLK_CFG` | SSC Config |
| `0x0C` | `0000_0000h` | `THC_SB_ROSC_CLK_CFG` | Ring Oscillator Config |
| `0x10` | `0000_0000h` | `THC_SB_DCGE_CFG` | Dynamic Clock Gate Config |
| `0x20` | `0000_0000h` | `THC_SB_SAI_CNTRL_PLCY0` | SAI Access Control Policy Reg 0 |
| `0x24` | `0000_0000h` | `THC_SB_SAI_CNTRL_PLCY1` | SAI Access Control Policy Reg 1 |
| `0x28` | `0000_0000h` | `THC_SB_SAI_CMN_PLCY0` | SAI Access Common Register Policy Reg 0 |
| `0x2C` | `0000_0000h` | `THC_SB_SAI_CMN_PLCY1` | SAI Access Common Register Policy Reg 1 |
| `0x30` | `0000_0000h` | `THC_SB_SAI_PORT0_PLCY0` | SAI Access Device 0 (Port 0) Policy Reg 0 |
| `0x34` | `0000_0000h` | `THC_SB_SAI_PORT0_PLCY1` | SAI Access Device 0 (Port 0) Policy Reg 1 |
| `0x38` | `0000_0000h` | `THC_SB_SAI_PORT1_PLCY0` | SAI Access Device 1 (Port 1) Policy Reg 0 |
| `0x3C` | `0000_0000h` | `THC_SB_SAI_PORT1_PLCY1` | SAI Access Device 1 (Port 1) Policy Reg 1 |
| `0x40` | `0000_0000h` | `THC_SB_SPI_CTRL` | SPI Interface Control |
| `0x48` | `0000_0700h` | `THC_SB_PM_CTRL` | Power Management Control (LTR, D0i2, timestamps) |
| `0x4C` | `0000_0000h` | `THC_SB_WRITTEN_BITS_CFG` | Lock Bits for Config |
| `0x50` | `0000_0000h` | `THC_SB_WRITTEN_BITS_MMIO` | Lock Bits for MMIO |
| `0x54` | `0000_0111h` | `THC_DN_ARB_CTRL` | Downstream Arbitration Control |
| `0x80` | `0000_0000h` | `THC_FUSES` | THC Fuses Register |
| `0x84` | `0000_0000h` | `THC_SOFTSTRAPS` | THC Softstraps Register |

### CDC Config Register State Transitions (BWG)

During Function Disable or clock gating enable, BIOS transitions CDC config registers from normal to CG-enabled state:

| SB Addr | Register | Normal Default | CG-Enabled Value | Notes |
|---------|----------|---------------|-----------------|-------|
| `0x00` | `THC_SB_PR_CDC_CFG` | `0000_CCC0h` | `0000_CCC3h` | Primary clock — CCC0→CCC3 |
| `0x04` | `THC_SB_SD_CDC_CFG` | `0000_CCC0h` | `0000_CCC3h` | Side clock — CCC0→CCC3 |
| `0x08` | `THC_SB_SSC_CLK_CFG` | `0000_0001h` | `0000_0001h` | SSC clock — unchanged |
| `0x0C` | `THC_SB_ROSC_CLK_CFG` | `0000_0001h` | `0000_0001h` | ROSC clock — unchanged |

> **Usage**: CCC0→CCC3 transition is Step 1 of the Function Disable flow. For normal operation, BIOS uses soft straps (`ClockGateEnable`, `PowerGateEnable`) instead of programming these registers directly. Direct register access is for **debug only**.

### THC_CFG_PCE Bit Reference (Config Offset 0xA2) (BWG)

| Bit | Name | RW | Default | Description |
|-----|------|----|---------|-------------|
| 5 | `HAE` | RW | 1 | HW Autonomous Enable — PGCB may request PG when idle |
| 4 | `RSVD2` | RW | 0 | Reserved |
| 3 | `SE` | RW | 1 | Sleep Enable — IP may assert Sleep during PG |
| 2 | `D3HE` | RW | 0 | D3-Hot Enable — PG when idle and PMCSR[1:0]=11 |
| 1 | `I3E` | RW | 0 | I3 Enable — PG when idle and D0i3C[2]=1 |
| 0 | `SPE` | RW | 0 | SW PG Enable — PG when `pmc_sw_pg_req_b`=0 (PMC-assisted HW autonomous) |

> **BIOS requirement**: BIOS must set `HAE=1` and `D3HE=1` during init (BWG Section 4.2.3). `I3E` is TGP-era (POR=not supported; reserved for future use). `SPE` enables PMC-assisted software power gating.

### Function Disable Flow (BWG)

1. Enable all clock gating controls (CDC regs: CCC0→CCC3 for `THC_SB_PR_CDC_CFG` and `THC_SB_SD_CDC_CFG`)
2. Set `HAE` bit in `THC_CFG_PCE` to 1
3. Set function into D3 state (write PMCSR[1:0]=11)
4. Set `THC_CFG_UR_STS_CTL.FD` = 1

> **⚠️ WARNING**: After FD=1, no SW or device wake is supported. PSF programmed by BIOS to UR all cycles. **Requires power cycle to recover** (listed in `AVOID_THC_BITS`).

## MMIO Common Register Map (2 registers)

| MEM Addr | Default | Register | Description |
|----------|---------|----------|-------------|
| `0x10` | `0000_0008h` | `THC_M_CMN_DEVIDLECTRL` | Device Idle Control |
| `0x14` | `0000_0000h` | `THC_M_CMN_LTR_CTRL` | LTR Control (LAST_LTR_SENT field for debug) |

### LTR_CTRL Bit Fields (Common Space Offset 0x14)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `ACTIVE_LTR_REQ` | `BIT(0)` | Active LTR request |
| `[1]` | `ACTIVE_LTR_EN` | `BIT(1)` | Active LTR enable |
| `[2]` | `LP_LTR_REQ` | `BIT(2)` | Low-power LTR request |
| `[3]` | `LP_LTR_EN` | `BIT(3)` | Low-power LTR enable |
| `[6:4]` | `LP_LTR_SCALE` | `GENMASK(6,4)` | LP LTR scale (geometric: 2^(5×scale) ns) |
| `[16:7]` | `LP_LTR_VAL` | `GENMASK(16,7)` | LP LTR value (10-bit) |
| `[19:17]` | `ACT_LTR_SCALE` | `GENMASK(19,17)` | Active LTR scale |
| `[29:20]` | `ACT_LTR_VAL` | `GENMASK(29,20)` | Active LTR value (10-bit) |
| `[31:30]` | `LAST_LTR_SENT` | `GENMASK(31,30)` | Last LTR sent (RO debug): 0=Active, 1=LP |

### LTR Scale and Threshold Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `THC_LTR_SCALE_0` – `THC_LTR_SCALE_5` | 0–5 | Scale factor: final LTR = value × 2^(5×scale) ns |
| `THC_LTR_MODE_ACTIVE` | 0 | Active LTR mode |
| `THC_LTR_MODE_LP` | 1 | Low-power LTR mode |
| `THC_LTR_MIN_VAL_SCALE_3` | `BIT(10)` = 1024 | Min LTR value for scale 3 (1µs) |
| `THC_LTR_MAX_VAL_SCALE_3` | `BIT(15)` = 32768 | Max LTR value for scale 3 |
| `THC_LTR_MIN_VAL_SCALE_4` | `BIT(15)` = 32768 | Min LTR value for scale 4 |
| `THC_LTR_MAX_VAL_SCALE_4` | `BIT(20)` | Max LTR value for scale 4 |
| `THC_LTR_MIN_VAL_SCALE_5` | `BIT(20)` | Min LTR value for scale 5 |
| `THC_LTR_MAX_VAL_SCALE_5` | `BIT(25)` | Max LTR value for scale 5 |

> **Usage**: `thc_change_ltr_mode()` programs the LTR_CTRL register to switch between Active and LP LTR modes during power state transitions. The QuickI2C driver uses default values of 5 (Active) and 500 (LP).

## Register Reset Power Domains

| Register Block (RTL) | Reset Domain | Power Well |
|----------------------|-------------|------------|
| `thcss_thc_cfg_bridge.sv` | `thc_core_rst_b` | VNN |
| `thcss_thc_mmio_common_bridge.sv` | `thc_core_rst_b` | VNN |
| `thcss_thc_mmio_port_bridge.sv` | `thc_core_rst_b` | VNN |
| `thcss_thc_sb_bridge.sv` | `thc_core_rst_b` | VNN (except PCE.HAE, SSC/ROSC/DCGE_CFG, BUS_NUM → `thc_sb_rst`) |

## ICR (Input Command Register) Config
Configurable field offsets for the SPI frame header:
- **THC Default**: EOF bit 30, IntType offset 0/len 4, MFS offset 4/len 0x14
- **Microsoft HIDSPI Spec**: EOF bit 8, IntType offset 4/len 4, MFS offset 9/len 0xF

## MMIO Port Per-Port Register Details with Restore Order

Each THC port has ~80 MMIO registers. The restore order is critical for D3 Save/Restore operations.

### Restore Order Groups (per Appendix A of HAS)
| Restore Order | Register Group | Notes |
|---------------|---------------|-------|
| 3.102-3.110 | Port Control, SPI Config, INT Enable/Mask | Must restore before DMA |
| 3.111-3.130 | SW Sequence (PIO) registers (17 data DWs) | THC_M_PRT_SW_SEQ_CNTRL/STS/DATA[16:0] |
| 3.131-3.140 | WPRD/RPRD base addresses, DMA control | Write PRD and Read PRD base addresses |
| 3.141-3.146 | DMA status/error, bulk addresses | DMA-related — some require "Driver reinitialize" |
| 5.1 | GuC doorbell/offset | Restore last |

### Key Registers NOT in Restore List (Driver Reinitialize)
- DMA Read/Write INT Status registers — cleared by driver
- DMA Error registers — read-only status
- Counter registers (RX/TX DMA frames, uframes, dropped, etc.)
- GuC doorbell cookie — driver manages

### All register blocks use:
- **Reset domain**: `thc_core_rst_b`
- **Power well**: VNN
- **Power domain**: `pd_pwell_dummy_thcss_pd`

### Exception Registers (different reset/power domain)
Located in `thcss_thc_sb_bridge.sv`:
- `THC_CFG_PCE.HAE` — `thc_sb_rst` reset domain
- `THC_SB_SSC_CLK_CFG` — `thc_sb_rst` reset domain
- `THC_SB_ROSC_CLK_CFG` — `thc_sb_rst` reset domain
- `THC_SB_DCGE_CFG` — `thc_sb_rst` reset domain
- `THC_BUS_NUM` — `thc_sb_rst` reset domain

## Transaction Attributes

### Supported Transaction Types (Port 0, IOSF Primary)
| Transaction | Upstream | Downstream |
|-------------|----------|------------|
| MRd32 | Yes | Yes |
| MRd64 | Yes | Yes |
| MWr32 | Yes | Yes |
| MWr64 | Yes | Yes |
| CfgRd0 | No | Yes |
| CfgWr0 | No | Yes |
| MsgD | Yes | No |
| Cpl | Yes | Yes |
| CplD | Yes | Yes |

### NOT Supported
LTMRd/LTMWr, MRdLk, IORd/IOWr, CfgRd1/CfgWr1, Msg, CplLk/CplDLk, FetchAdd, Swap, CAS

### Transaction Sizes
- Port 0, 1 Channel
- Peak BW: 1GBps (125MHz @ 8B) both UP and DN
- Max Payload Posted: UP=64B, DN=8B
- Max Payload NP: UP=0, DN=1DW
- Max Payload Completion: UP=8B, DN=64B

### Ordering Rules
THC follows standard IOSF ordering on both downstream and upstream paths.
IOSF Primary Physical Attributes: Port 0, Address Width 63:0, Data Width 63:0, Frequency 125 MHz

## PCIe Capability Registers (MTL-S+ when thc_pci_or_pciemode=1)

### PCI PM Capability (offset 0x70)
- NXTP → 0xB0 when PCIe mode enabled

### PCIe Capability Structure (offset 0xB0)
- Cap ID: 0x10
- Version: 2h
- Device/Port Type: PCIe Endpoint

### PCIe Device Capability (offset 0xB4)
- Max_Payload_Size: 128B
- FLR Capability: 0 (not supported)
- Extended Tag: 8-bit
- L0s/L1 Acceptable Latency: No limit

### PCIe Device Control/Status (offset 0xB8)
- Max_Read_Request_Size: Ignored (always 64B internally)
- No Snoop: Ignored (always 0)
- Transactions Pending: Implemented

### PCIe Summary
| Capability | Support |
|-----------|---------|
| PMCS | Yes |
| PCIeCAP | If pciemode |
| LTR | Yes |
| PTM | No |
| FLR | No |
| MSI | Yes |
| MSI-X | No |
| AER | No |
| D3-Cold | No |
| D3-Hot | Yes |
| PME | No |
| WAKE | No |

## Decoding and Channel Mapping

### BAR Configuration
- **BAR0**: Type 0, Range 32KB, Target Channel 0
- **BAR1-5, ROMBAR**: Unused
- **Memory Enable**: Yes
- **IO Enable**: No
- **Power State Address**: PMCR @ 0x34
- **Config Target Channel**: 0

### MMIO Layout
- **Common registers**: Base + 0x0000
- **Port 0 registers**: Base + 0x1000
- **Port 1 registers**: Base + 0x2000

### Register Access Rules
- 64-bit addressed, all regs Dword access
- Read/Modify/Write required for partial writes
- DID bits 31:16 RO/V (upper 9 bits overridable via SetIDValue SB msg)
- DID bit 16: RWOnce (MTL+)

### NVL+ PI Configuration
- PI (Programming Interface) configurable via `thc_pi_def[7:0]` softstrap
- Two driver models: per-port PCI header vs shared

## Hardware Initialization Sequence (`thc_dev_init()`)

The `thc_dev_init()` function is the entry point for THC hardware initialization. It performs the following steps:

1. **Allocate** `thc_device` structure (`devm_kzalloc`)
2. **Initialize regmap** — `devm_regmap_init()` with `thc_regmap_cfg` (see Regmap Configuration below)
3. **Clear hardware state** — `thc_clear_state()` (see Counter Registers section):
   - Clear `ERR_CAUSE` register (INVLD_DEV_ENTRY, FRAME_BABBLE, BUF_OVRRUN, PRD_ENTRY)
   - Clear DMA STALL bits on RXDMA1/RXDMA2
   - Clear `INT_STATUS` TXN_ERR and FATAL_ERR bits
   - Enable error reporting interrupts (TXN_ERR, FATAL_ERR, BUF_OVRRUN)
   - Clear PIO status (SS_ERR, TSSDONE)
   - Disable RXDMA1/RXDMA2 EOF interrupts, clear NONDMA_INT_STS on ch1
   - Enable TXDMA DMACPL interrupt only (`IE_IOC_DMACPL`, BIT(3)) — note: despite the field name containing "IOC", only the DMACPL (DMA complete) interrupt is enabled; the separate IOC interrupt (BIT(2)) is NOT enabled. Clear TXDMA error/IOC/complete status
   - Reset ALL counter registers (see Counter Registers section)
4. **Initialize mutexes** — `thc_bus_lock` (PIO/DMA bus exclusion)
5. **Initialize wait queues** — `write_complete_wait`, `swdma_complete_wait`
6. **Initialize DMA context** — `thc_dma_init()` (see `fv-thc/dma`)

> **Validation point**: After `thc_dev_init()`, all error status bits should be cleared, all counters should be zero, and the DMA context should be allocated. Verify no stale interrupt status from a previous driver session.

## DEV_INT_CAUSE Register Value (Offset 0x0BC from port base, read via `thc_int_cause_read()`)

The `thc_int_cause_read()` function reads offset `THC_M_PRT_DEV_INT_CAUSE_REG_VAL_OFFSET` and returns the raw u32 value. Bit fields:

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[3:0]` | `INTERRUPT_TYPE` | `GENMASK(3,0)` | Interrupt type from device ICR header |
| `[23:4]` | `MICRO_FRAME_SIZE` | `GENMASK(23,4)` | Microframe size (20-bit) |
| `[29]` | `BOF` | `BIT(29)` | Beginning of frame flag |
| `[30]` | `EOF` | `BIT(30)` | End of frame flag |
| `[31]` | `FRAME_TYPE` | `BIT(31)` | Frame type: 0→RXDMA1, 1→RXDMA2 |

> **Usage**: Called by `thc_interrupt_handler()` after a non-DMA interrupt to inspect what the device reported. The INTERRUPT_TYPE and FRAME_TYPE fields are used to route data to the correct DMA channel.

## Regmap Configuration (Linux Kernel)

The Linux kernel THC driver uses `regmap_mmio` for register access with the following configuration:

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Ranges** | `0x10–0x14` (common), `0x1000–0x1320` (port) | Two non-contiguous MMIO regions |
| **Register stride** | 4 bytes | All registers are 32-bit DWORD-aligned |
| **Value bits** | 32 | All registers are 32-bit wide |
| **Cache type** | `REGCACHE_NONE` | No register caching — every access hits hardware |
| **Max register** | `0x1320` | Highest accessible MMIO offset |
| **fast_io** | `true` | Uses spinlocks instead of mutexes for register access (safe for IRQ context) |

> **Implication**: No write-back optimization. Every `regmap_write()` immediately hits MMIO. This ensures consistency but means SW must minimize register access in hot paths for performance.

## Interrupt Handler Priority Order (Linux Kernel)

The THC interrupt handler (`thc_interrupt_handler`) processes interrupt sources in this strict priority order. Each error check returns immediately if matched (short-circuit):

| Priority | Source | Kernel Behavior | Notes |
|----------|--------|-----------------|-------|
| 1 (highest) | Non-DMA interrupt | Return `THC_IRQ_HDL_NONDMA` immediately | Check first: if no DMA-related bits set |
| 2 | `TXN_ERR` | Log + return immediately | Transaction error — abort processing |
| 3 | `BUF_OVRRUN` or `STALL` | Log + return immediately | Buffer overrun or DMA stall |
| 4 | `FATAL_ERR` | Log + return immediately | Fatal hardware error |
| 5 | `PIO_DONE` | Set flag, **falls through** | PIO completion — does NOT return, continues checking DMA |
| 6 | RXDMA Channel 1 | Accumulate into return bitmask | Legacy/raw data channel |
| 7 | RXDMA Channel 2 | Accumulate into return bitmask | HID input channel (primary) |
| 8 | SWDMA | Accumulate into return bitmask | Software DMA (Gen4.0+) |
| 9 | TXDMA | Accumulate into return bitmask | Write DMA completion |
| 10 | I2C Sub-IP | Accumulate into return bitmask | HIDI2C mode only |
| 11 (lowest) | Unknown | Warning log | Unexpected interrupt source |

> **⚠️ CORRECTION (v2)**: Previous version showed PIO at priority 2 (before error checks). Kernel actually checks ALL errors (priorities 2-4) before PIO. PIO also does NOT return — it falls through to continue checking DMA sources. DMA sources (6-9) are accumulated into a bitmask (not short-circuited). I2C sub-IP interrupt is checked AFTER all DMA channels.

## Counter Registers (Cleared by `thc_clear_state`)

THC maintains hardware counter registers that track DMA frame/microframe statistics. The following are cleared to 0 during driver init and state reset:

| Register Group | Counters Cleared |
|----------------|-----------------|
| **TXDMA** | `TX_FRM_CNT`, `TXDMA_PKT_CNT` |
| **RXDMA Ch1** | `FRM_CNT_1`, `UFRM_CNT_1`, `RXDMA_PKT_CNT_1`, `FRAME_DROP_CNT_1`, `DB_CNT_1`, `PRD_EMPTY_CNT_1` |
| **RXDMA Ch2** | `FRM_CNT_2`, `UFRM_CNT_2`, `RXDMA_PKT_CNT_2`, `FRAME_DROP_CNT_2`, `PRD_EMPTY_CNT_2` |
| **Device/SW** | `DEVINT_CNT`, `SWINT_CNT_1` (cleared **twice** — see bug note below) |

Additionally, `thc_clear_state()` clears these software interrupt counters:
- `THC_M_PRT_SWINT_CNT_1` — Software interrupt count 1 (cleared twice)

> **⚠️ CORRECTION (audit)**: Previous version claimed SWDMA and TXDMA had uframe/drop counters that were cleared — they do NOT. SWDMA counters (`FRM_CNT_SW`, `RXDMA_PKT_CNT_SW`) and TXDMA uframe/drop counters are NOT cleared by `thc_clear_state()`. Only the counters listed above are actually reset in the kernel code.

> **⚠️ Likely kernel bug**: In `thc_clear_state()`, `SWINT_CNT_1` is reset **twice** and `SWINT_CNT_2` is **never** reset. The second `regmap_write_bits(SWINT_CNT_1, ...)` should likely be `SWINT_CNT_2`. Harmless if SWINT_CNT registers are not used, but indicates a copy-paste error.

> **Key**: These are NOT in the D3 save/restore list — they are driver-reinitialized (cleared to 0 on every resume).

## TSEQ_CNTRL_1 Register (Touch Sequencer Control, Offset 0x128)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[2]` | `RGD` | `BIT(2)` | Read GuC Doorbell |
| `[3]` | `EGP` | `BIT(3)` | Enable GuC Processing |
| `[4]` | `RTO` | `BIT(4)` | Read Timeout |
| `[5]` | `EWOG` | `BIT(5)` | Enable Write on GPIO |
| `[6]` | `RWOGC` | `BIT(6)` | Read Write on GPIO Clear |
| `[25:16]` | `RX_DATA_FIFO_WR_WM` | `GENMASK(25,16)` | RX Data FIFO Write Watermark |
| `[30]` | `RESET_PREP_CHICKEN` | `BIT(30)` | Reset preparation "chicken bit" (debug workaround) |
| `[31]` | `INT_EDG_DET_EN` | `BIT(31)` | Interrupt edge detection enable |

> **⚠️ CORRECTION (v3)**: Previous version had SPI_TRDC at GENMASK(3,0), SPI_TWDC at GENMASK(7,4), and SPI_TRDECNT at GENMASK(15,8) — none of these exist in the kernel TSEQ_CNTRL_1 definition. Kernel defines RGD(2), EGP(3), RTO(4), EWOG(5), RWOGC(6) for control bits. Added missing INT_EDG_DET_EN at BIT(31). Note: TSEQ_CNTRL_2 (offset 0x228) has a subset: only RGD(2), EGP(3), RTO(4).

> **Note**: `RESET_PREP_CHICKEN` is a "chicken bit" — a debug override that disables or modifies behavior of a specific hardware feature. Named after the practice of "chickening out" of a new feature. Set during `thc_reset_tic()` when resetting the touch device.

## Linux Kernel Module Structure

The THC driver is split into 3 kernel modules:

| Module | Kconfig Symbol | Source Files | Description |
|--------|---------------|-------------|-------------|
| `intel-thc` | `INTEL_THC_HID` | `intel-thc-dev.c`, `intel-thc-dma.c`, `intel-thc-wot.c` | Core THC hardware library (no PCI binding) |
| `intel-quickspi` | `INTEL_QUICKSPI` | `pci-quickspi.c`, `quickspi-protocol.c`, `quickspi-hid.c` | HIDSPI protocol + PCI driver (depends on `INTEL_THC_HID`) |
| `intel-quicki2c` | `INTEL_QUICKI2C` | `pci-quicki2c.c`, `quicki2c-protocol.c`, `quicki2c-hid.c` | HIDI2C protocol + PCI driver (depends on `INTEL_THC_HID`) |

All modules are `tristate` (can be built-in, module, or off). `INTEL_THC_HID` depends on `ACPI` and selects `SGL_ALLOC`. `INTEL_QUICKSPI` and `INTEL_QUICKI2C` depend on `INTEL_THC_HID`. There is NO `SPI_INTEL_THC` dependency.

> **Build note**: `intel-thc` is a library module — it does not register as a PCI driver itself. The protocol modules (`intel-quickspi`, `intel-quicki2c`) are the actual PCI drivers that call into `intel-thc` for hardware operations.
>
> **Build path**: The Makefile adds `ccflags-y += -I $(src)/intel-thc` to the include path, allowing protocol modules to include THC core headers directly.
>
> **Kconfig dependencies**: `INTEL_THC_HID` depends on `ACPI` and selects `SGL_ALLOC`. `INTEL_QUICKSPI` depends on `INTEL_THC_HID`. `INTEL_QUICKI2C` depends on `INTEL_THC_HID`.

## THC_M_PRT_SPARE_REG (Offset 0x2BC — Chicken Bits) (Phase 6)

> **Source**: Windows HIDI2C/HIDSPI drivers — Phase 6 audit

The spare register at offset `0x2BC` contains "chicken bits" (debug overrides):

| Bit | Name | Description |
|-----|------|-------------|
| 0 | `DIS_RXDMA_DUMMY_WR_UF_FIX` | Disable RXDMA dummy write underflow fix |
| 1 | `DIS_CDC_FIX_VIO` | Disable CDC fix violation |

> **⚠️ Warning**: These are debug-only bits. Setting them disables hardware fixes and may cause DMA errors. Only use for targeted debug when instructed by IP validation team.

## THC_CFG_PCE Offset Note (Phase 6)

The Windows driver accesses `THC_CFG_PCE` at PCI config offset **`0xA4`**, while the Linux kernel and this skill file document it at **`0xA2`**.

| Source | Offset | Width |
|--------|--------|-------|
| Linux kernel (`intel-thc-hw.h`) | `0xA2` | 16-bit (WORD) |
| Windows HIDI2C driver | `0xA4` | 32-bit (DWORD) |

> **Resolution**: The PCE register is a 16-bit register at `0xA2`. The Windows driver likely reads/writes a 32-bit DWORD at `0xA4` which accesses adjacent bytes. Verify actual hardware behavior — the `0xA2` offset (Linux/HAS) is considered authoritative. The `0xA4` access may be reading a different portion of the extended PCE block.

## Clock Gating Register Details (Phase 6)

> **Source**: Windows drivers — Phase 6 audit

The Windows drivers program additional clock gating registers during init:

### IOSF SB Dynamic Clock Gate Enable (SB offset 0x10)
The `THC_SB_DCGE_CFG` register enables/disables dynamic clock gating for different clock domains:
- Bit patterns match the CDC config register transitions (CCC0→CCC3)
- Windows driver sets all clock gating bits enabled during normal operation
- **Debug override**: Clear specific bits to keep clocks running for VISA/debug visibility

> **Cross-reference**: See `THC_SB_PR_CDC_CFG` (0x00) and `THC_SB_SD_CDC_CFG` (0x04) in the IOSF Sideband Register Map for related CDC configuration.

## Validation Points

| ID | What to Validate | Expected | Register/Method |
|----|-----------------|----------|-----------------|
| VP-REG-01 | PCI BAR0 allocation | 32KB MMIO range, 64-bit addressing | Read BAR0 (PCI offset 0x10/0x14), verify size and type bits |
| VP-REG-02 | PIO read opcode | Opcode = 0x4 for PIO read transactions | Verify `THC_M_PRT_READ_DMA_CNTRL_1.PIO_OP` = 0x4 |
| VP-REG-03 | PIO write opcode | Opcode = 0x6 for PIO write transactions | Verify `THC_M_PRT_WRITE_DMA_CNTRL.PIO_OP` = 0x6 |
| VP-REG-04 | I2C Sub-IP IC_CON init | IC_CON = 0x0663 after driver init | Read I2C Sub-IP IC_CON register at APB offset 0x00 |
| VP-REG-05 | Interrupt quiesce | GBL_INT_EN cleared, INT_STS polled until quiet | Verify `THC_M_PRT_INT_EN.GBL_INT_EN` = 0, then check INT_STS = 0 |
| VP-REG-06 | Register restore order | Appendix A grouping preserved after D3 exit | Dump all registers, cycle D3, re-dump — compare per HAS restore groups |
| VP-REG-07 | DEVINT_CFG routing | Interrupt source → MSI vector mapping correct | Read DEVINT_CFG_1 (0x0EC) / DEVINT_CFG_2 (0x0F0), verify bit assignments |
| VP-REG-08 | Clock gating enabled | Dynamic clock gating bits set in normal operation | Read SB register `THC_SB_DCGE_CFG` (0x10), verify all CG bits enabled |
| VP-REG-09 | Lock bits set | BIOS_LOCK_EN and DRV_LOCK_EN asserted post-init | Verify lock bit registers are set and immutable |
| VP-REG-10 | PCE power control | SPE, I3E, D3HE, SE, HAE bits correctly configured | Read `THC_CFG_PCE` at offset 0xA2, verify bit field values |

## See Also
- **`fv-thc/power`** — D3 save/restore register list, restore order during power transitions
- **`fv-thc/dma`** — DMA register configuration, PRD base address registers
- **`fv-thc/platform`** — Per-platform Device IDs, BAR configuration, PCIe capabilities
- **`fv-thc/hidspi`** — SPI-specific register programming (SPI_CFG, opcodes)
- **`fv-thc/hidi2c`** — I2C-specific register programming (PORT_TYPE, I2C sub-IP regs)
- **`fv-thc/driver`** — BIOS programming requirements, lock bit sequences
- **`fv-thc/debug`** — Register dump methodology, error/status register debug procedures
- **`fv-thc/wot`** — Wake-on-Touch UGD register subset, WoT interrupt configuration, UGD register retention, GPIO wake register config
- **`fv-thc/simics`** — Simics pre-silicon register access via PythonSV SW-CI, namednode paths, model register overrides
- **Reference**: `fv-thc/docs/thc_has_4x_extraction.md` — Complete HAS extraction with all register details
