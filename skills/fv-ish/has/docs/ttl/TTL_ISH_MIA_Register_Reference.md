# TTL ISH MIA Internal Register Reference

**Source**: `ish_mia_bfm_rdl_top.pdf` (OSXML register spec, 30 sections)
**Platform**: TTL (Titan Lake) — ISH 5.9
**Power Well**: VNNAON | **Reset**: Per-block (see each section)

---

## Table of Contents

1. [I2C Controller (DW_apb_i2c)](#1-i2c-controller)
2. [GPIO Controller (ish_gpio_config)](#2-gpio-controller)
3. [IPC Channels (HOST through AVB)](#3-ipc-channels)
4. [PMU - Power Management Unit](#4-pmu-power-management-unit)
5. [CCU - Clock Control Unit](#5-ccu-clock-control-unit)
6. [Misc Config](#6-misc-config)
7. [SBEP Config](#7-sbep-sideband-endpoint)
8. [HPET Timer](#8-hpet-timer)
9. [I3C HCI Controller](#9-i3c-hci-controller)
10. [Watchdog Timer](#10-watchdog-timer)
11. [Security Block](#11-security-block)
12. [SPI Controller (DW_apb_ssi)](#12-spi-controller)
13. [UART Controller (DW_apb_uart)](#13-uart-controller)
14. [DMA Misc](#14-dma-misc)
15. [SRAM Controller](#15-sram-controller)
16. [Fabric](#16-fabric)

---

## 1. I2C Controller

**Block**: DW_apb_i2c (3 instances) | **Base**: `0x00000000` (I2C0), `0x00002000` (I2C1), `0x00004000` (I2C2)
**Reset**: I2C_RST | **Bus**: APB.MEM (32-bit)

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| IC_CON | 0x00 | 0x7F | I2C control: master/slave mode, speed, restart, stop |
| IC_TAR | 0x04 | 0x1055 | Target address (10/7 bit), special/GC_START |
| IC_SAR | 0x08 | 0x55 | Slave address |
| IC_HS_MADDR | 0x0C | 0x1 | High-speed master mode code address |
| IC_DATA_CMD | 0x10 | 0x0 | Data buffer and command (R/W, STOP, RESTART) |
| IC_SS_SCL_HCNT | 0x14 | 0x190 | Standard speed SCL high count |
| IC_SS_SCL_LCNT | 0x18 | 0x1D6 | Standard speed SCL low count |
| IC_FS_SCL_HCNT | 0x1C | 0x3C | Fast speed SCL high count |
| IC_FS_SCL_LCNT | 0x20 | 0x82 | Fast speed SCL low count |
| IC_HS_SCL_HCNT | 0x24 | 0x6 | High-speed SCL high count |
| IC_HS_SCL_LCNT | 0x28 | 0x10 | High-speed SCL low count |
| IC_INTR_STAT | 0x2C | 0x0 | Interrupt status (masked) |
| IC_INTR_MASK | 0x30 | 0x8FF | Interrupt mask |
| IC_RAW_INTR_STAT | 0x34 | 0x0 | Raw interrupt status (unmasked) |
| IC_RX_TL | 0x38 | 0x0 | Receive FIFO threshold level |
| IC_TX_TL | 0x3C | 0x0 | Transmit FIFO threshold level |
| IC_CLR_INTR | 0x40 | 0x0 | Clear combined interrupt |
| IC_CLR_RX_UNDER | 0x44 | 0x0 | Clear RX_UNDER interrupt |
| IC_ENABLE | 0x6C | 0x0 | I2C enable, TX abort, SDA stuck recovery |
| IC_STATUS | 0x70 | 0x6 | I2C status: activity, TF not full, TF empty, RF not empty, RF full |
| IC_TXFLR | 0x74 | 0x0 | Transmit FIFO level |
| IC_RXFLR | 0x78 | 0x0 | Receive FIFO level |
| IC_FS_SPKLEN | 0xA0 | 0x5 | Fast speed spike suppression limit |
| IC_HS_SPKLEN | 0xA4 | 0x1 | High-speed spike suppression limit |
| IC_SCL_STUCK_AT_LOW_TIMEOUT | 0xAC | varies | SCL stuck at low timeout |
| IC_SDA_STUCK_AT_LOW_TIMEOUT | 0xB0 | varies | SDA stuck at low timeout |
| IC_COMP_PARAM_1 | 0xF4 | varies | Component parameter (RO) |
| IC_COMP_VERSION | 0xF8 | varies | Component version (RO) |
| IC_COMP_TYPE | 0xFC | 0x44570140 | Component type (RO) |

---

## 2. GPIO Controller

**Block**: ish_gpio_config | **Base**: `0x00100000`
**Reset**: GPIO_RST | **Bus**: APB.MEM (32-bit)

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| GCCR | 0x00 | 0x0 | GPIO controller config. [0]=GPDR_LOCK (locks pin direction) |
| GPLR0 | 0x04 | 0x0 | Pin level read GPIO[31:0] (RO) |
| GPLR1 | 0x08 | 0x0 | Pin level read GPIO[63:32] (RO) |
| GPLR_H0 | 0x0C | 0x0 | Pin level read historical GPIO[31:0] (RO) |
| GPLR_H1 | 0x10 | 0x0 | Pin level read historical GPIO[63:32] (RO) |
| GPDR0 | 0x1C | 0x0 | Pin direction GPIO[31:0] (1=output, 0=input) |
| GPDR1 | 0x20 | 0x0 | Pin direction GPIO[63:32] |
| GPSR0 | 0x34 | 0x0 | Pin set GPIO[31:0] (WO, writing 1 drives high) |
| GPSR1 | 0x38 | 0x0 | Pin set GPIO[63:32] |
| GPCR0 | 0x4C | 0x0 | Pin clear GPIO[31:0] (WO, writing 1 drives low) |
| GPCR1 | 0x50 | 0x0 | Pin clear GPIO[63:32] |
| GRER0 | 0x64 | 0x0 | Rising edge detect enable GPIO[31:0] |
| GRER1 | 0x68 | 0x0 | Rising edge detect enable GPIO[63:32] |
| GFER0 | 0x7C | 0x0 | Falling edge detect enable GPIO[31:0] |
| GFER1 | 0x80 | 0x0 | Falling edge detect enable GPIO[63:32] |
| GFBR0 | 0x94 | 0x0 | Glitch filter bypass GPIO[31:0] (1=bypass) |
| GFBR1 | 0x98 | 0x0 | Glitch filter bypass GPIO[63:32] |
| GIMR0 | 0xAC | 0x0 | Interrupt mask GPIO[31:0] (1=enabled) |
| GIMR1 | 0xB0 | 0x0 | Interrupt mask GPIO[63:32] |
| GISR0 | 0xC4 | 0x0 | Interrupt source GPIO[31:0] (RW/1C) |
| GISR1 | 0xC8 | 0x0 | Interrupt source GPIO[63:32] (RW/1C) |
| GWMR0 | 0x100 | 0x0 | Wake mask GPIO[31:0] (1=wake enabled) |
| GWMR1 | 0x104 | 0x0 | Wake mask GPIO[63:32] |
| GWSR0 | 0x118 | 0x0 | Wake source GPIO[31:0] (RW/1C) |
| GWSR1 | 0x11C | 0x0 | Wake source GPIO[63:32] (RW/1C) |
| GSEC | 0x130 | 0x0 | Security: hides pin level and masks interrupts |

---

## 3. IPC Channels

**Sections 3-10**: 8 IPC channels with identical per-channel register layout.
Each channel uses the same register structure at different base addresses.

| Channel | Section | Base (MIA side) | Bus Type | Description |
|---------|---------|-----------------|----------|-------------|
| HOST | Sec 3 | 0x04100000 | MEM | Host driver communication |
| HOSTSPARE | Sec 4 | 0x04101000 | MEM | Spare host channel |
| CSE | Sec 5 | 0x04102000 | MSG | CSME engine |
| PMC | Sec 6 | 0x04103000 | MSG | Power Management Controller |
| CNVi | Sec 7 | 0x04104000 | MSG | Connectivity (WiFi/BT) |
| ACE | Sec 8 | 0x04105000 | MSG | Audio/Comms Engine |
| ESE | Sec 9 | 0x04106000 | MSG | Embedded Security Engine |
| AVB | Sec 10 | 0x04107000 | MSG | Audio/Video Bridging |

### Per-Channel Register Layout

| Register | Offset | Default | Access | Description |
|----------|--------|---------|--------|-------------|
| PISR | 0x00 | 0x0 | RO/RW1C | Primary interrupt status. [27]=H2IBCISC(RW/1C), [0]=INBOUND(RO) |
| PIMR | 0x04 | 0x0 | RW | Primary interrupt mask. [27]=H2IBCISC_IE, [11]=OUTBOUND_BUSY_CLEAR, [0]=PIMR_INBOUND |
| HOST_PIMR | 0x08 | 0x0 | RW | Host-side interrupt mask. [8]=INBOUND_BUSY_CLEAR, [0]=OUTBOUND_IPC |
| HOST_PISR | 0x0C | 0x0 | RO/RW1C | Host-side interrupt status. [8]=INBOUND_BUSY_CLEAR(RW/1C), [0]=OUTBOUND_IPC(RO) |
| CIM | 0x10 | 0x0 | RW | Channel interrupt mask. [0]=CH_INTR_MASK |
| CIS | 0x14 | 0x0 | RO | Channel interrupt status. [0]=CH_INTR_STATUS |
| FWSTS | 0x34 | varies | RO/RW | Firmware status (32-bit) |
| COMM | 0x38 | 0x0 | RW/RO | Communication register (32-bit) |
| INBOUND_DB | 0x48 | 0x0 | RW | Inbound doorbell. [31]=BUSY, [30:0]=PAYLOAD |
| OUTBOUND_DB | 0x54 | 0x0 | RW | Outbound doorbell. [31]=BUSY, [30:0]=PAYLOAD |
| OUT_MSG1-32 | 0x60-0xDC | 0x0 | RW | Outbound message registers (32 × 32-bit) |
| IN_MSG1-32 | 0xE0-0x15C | 0x0 | RO | Inbound message registers (32 × 32-bit) |
| REMAP0-5 | 0x360-0x374 | varies | RW | Address remap registers (6 × 32-bit) |
| BUSY_CLEAR | 0x378 | 0x0 | RW | Busy clear register |
| D0IX counters | 0x500-0x53C | 0x0 | RW | D0ix transition counters |
| D0I3C | 0x6D0 | 0x8 | RW | D0i3 control. [4]=IRC(RO), [3]=RR(RW/1C,def=1), [2]=D0i3(RW), [1]=IR(RW), [0]=CIP(RO) |

### IPC Doorbell Protocol
1. **Sender** writes payload to OUT_MSG registers, then sets BUSY=1 in doorbell
2. **Receiver** reads payload from IN_MSG registers
3. **Receiver** clears BUSY bit to acknowledge
4. Level-sensitive interrupt to IOAPIC while BUSY=1

---

## 4. PMU - Power Management Unit

**Block**: ish_pmu_config | **Base**: `0x04200000`
**Reset**: FUNCRST | **Bus**: APB.MEM (32-bit)

### 4.1 PMU_SRAM_PG_EN (0x00) — SRAM Bank Power Gate Enable
**Default**: `0x3FFFFFFF`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [31:30] | RSVD | RO | 0x0 | Reserved |
| [29:0] | SRAM_PG_EN_BANKn_TILEm | RW | all 1 | Per-bank per-tile power gate enable. 15 banks × 2 tiles = 30 bits. 1=Enable PG, 0=Disable PG |

### 4.2 PMU_HOST_WAKEUP (0x08) — Host Wake / PME Control
**Default**: `0x00000000`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [9] | PMU_PME_STATUS_CLR_INTR_MSK | RW | 0 | PME status clear interrupt mask |
| [8] | PMU_PME_STATUS_CLR_INTR_STS | RW/1C | 0 | PME status clear interrupt status |
| [1] | PMC_STS_SHADOW | RO | 0 | Live PME_STS from PCI config |
| [0] | OOB_PME | RW | 0 | Assert oob_pme_b signal |

### 4.3 PMU_ISH_WAKE_EVENT (0x0C) — Wake Event Record
**Default**: `0x00000000` | All event bits are **RW/1C**

| Bit | Wake Source | Logged During |
|-----|------------|---------------|
| [31] | VNN_ACK falling edge | IPAPG + MIACG |
| [30] | VNN_ACK rising edge | IPAPG + MIACG |
| [29] | D0I3 | MIACG |
| [27] | SPI1 | MIACG |
| [26] | SBEP (sideband) | IPAPG + MIACG |
| [25] | I2C2 | MIACG |
| [24] | Bridge (PwrActive) | IPAPG |
| [23] | UART | MIACG |
| [22] | SPI0 | MIACG |
| [21] | I2C1 | MIACG |
| [20] | I2C0 | MIACG |
| [19] | DMA | MIACG |
| [17] | IPC (any channel) | MIACG |
| [16] | HPET Timer | IPAPG + MIACG |

### 4.4 PMU_ISH_MASK_EVENT (0x10) — Wake Event Mask
**Default**: `0x00000000` — Mirrors WAKE_EVENT bit positions. 1=Mask wake, 0=Allow wake.

### 4.5 PMU_ISH_FABRIC_CNT (0x18) — Fabric Idle/Timeout Configuration
**Default**: `0x3A980008`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [31:16] | PMU_FABRIC_TIMEOUT_CNT | RW | 0x3A98 | Timeout value for fabric timeout counter |
| [15:0] | PMU_FABRIC_IDLE_CNT | RW | 0x0008 | Idle counter value (0-16) |

### 4.6 PMU_ISH_GLITCH_BYPASS (0x1C) — Glitch Filter Bypass
**Default**: `0x00000001`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [0] | GLITCH_BYPASS | RW | 1 | 0=Use glitch filter, 1=Bypass glitch filter |

### 4.7 Power Gating FSM Timing Registers

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| PMU_RF_ROM_CLKGATE_TO_ISOEN_CTRL | 0x20 | 0x00000002 | Clocks between CLKGATE→ISOEN |
| PMU_RF_ROM_ISOEN_TO_PWRGATE_CTRL | 0x24 | 0x00000002 | Clocks between ISOEN→PWRGATE |
| PMU_RF_ROM_PWRUNGATE_TO_ISODIS_CTRL | 0x28 | 0x00000002 | Clocks between PWRUNGATE→ISODIS |
| PMU_RF_ROM_ISODIS_TO_CLKGATEEXIT_CTRL | 0x2C | 0x00000002 | Clocks between ISODIS→CLKGATEEXIT |

All [15:0] = count value (RW), [31:16] = Reserved (RO).

### 4.8 PMU_RF_ROM_PWR_CTRL (0x30) — RF/ROM Power Gating Control
**Default**: `0x00000000`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [1] | AONRF_DEEPSLEEP_EN | RW | 0 | AON RF deepsleep mode enable |
| [0] | RF_ROM_POWER_GATING_ENABLE | RW | 0 | RF/ROM power gating enable |

### 4.9 PMU_SRAM_PWR_CTRL (0x34) — SRAM PG FSM Timing
**Default**: `0x0F0F0F02`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [27:24] | SRAM_ISODIS_TO_IDLE_COUNTER | RW | 0xF | ISODIS→IDLE count |
| [19:16] | SRAM_POWERUNGATE_TO_ISODIS_COUNTER | RW | 0xF | POWERUNGATE→ISODIS count |
| [11:8] | SRAM_POWERGATE_TO_POWERUNGATE_COUNTER | RW | 0xF | POWERGATE→POWERUNGATE count |
| [3:0] | SRAM_ISOEN_TO_POWERGATE_COUNTER | RW | 0x2 | ISOEN→POWERGATE count |

### 4.10 PMU_VNN_REQ (0x3C) — VNN Request Assert
**Default**: `0x00000000`

32 bits, each **RW/1S/1C/V**. ISH FW asserts ish_pmc_vnn_req toward PMC. Any bit set=VNN requested. OR of all 32 bits drives the physical VNN_REQ signal.

### 4.11 PMU_VNN_REQ_ACK (0x40) — VNN Req/Ack Status
**Default**: `0x00000000`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [5] | VNN_ACK_FALLING_EDGE_INTERRUPT_MASK | RW | 0 | Mask VNN_ACK fall interrupt |
| [4] | VNN_ACK_RISING_EDGE_INTERRUPT_MASK | RW | 0 | Mask VNN_ACK rise interrupt |
| [3] | VNN_ACK_FALLING_EDGE_INTERRUPT | RW/1C | 0 | VNN_ACK fall interrupt status |
| [2] | VNN_ACK_RISING_EDGE_INTERRUPT | RW/1C | 0 | VNN_ACK rise interrupt status |
| [1] | VNN_ACK_STATUS | RO | 0 | VNN_ACK live status |
| [0] | VNN_REQ_ACK_STATUS | RO | 0 | VNN_REQ AND VNN_ACK both set |

---

## 5. CCU - Clock Control Unit

**Block**: ish_ccu_config | **Base**: `0x04300000`
**Reset**: FUNCRST | **Bus**: APB.MEM (32-bit)

| Register | Offset | Default | Key Bits | Description |
|----------|--------|---------|----------|-------------|
| TRUNK_CG | 0x00 | 0x0 | [0]=CCU_ISH_TRUNK_CG | Trunk clock gate enable. 1=initiate trunk CG on Halt |
| BLK_CG | 0x04 | 0x0 | [1]=CCU_HPET_CG | HPET block clock gate |
| UART_BLK_CG | 0x08 | 0x0 | [2:0]=ccureg_uart_cg | Per-UART instance clock gate (3 UARTs) |
| I2C_BLK_CG | 0x0C | 0x0 | [2:0]=ccureg_i2c_cg | Per-I2C instance clock gate (3 I2Cs) |
| SPI_BLK_CG | 0x10 | 0x0 | [1:0]=ccureg_spi_cg | Per-SPI instance clock gate (2 SPIs) |
| GPIO_BLK_CG | 0x14 | 0x0 | [0]=ccureg_gpio_cg | GPIO block clock gate |
| I2S_BLK_CG | 0x18 | 0x0 | [0]=ccureg_i2s_cg | I2S block clock gate (reserved) |
| TSN_BLK_CG | 0x1C | 0x0 | [0]=ccureg_tsn_cg | TSN block clock gate (reserved) |
| SRAM_BLK_CG | 0x20 | 0x0 | [1:0]=ccureg_sram_cg | SRAM block clock gate |
| QEP_BLK_CG | 0x24 | 0x0 | [0]=rsvd | Reserved |
| DMA_BLK_CG | 0x28 | 0x0 | [0]=ccureg_dma_cg | DMA block clock gate |
| PWM_BLK_CG | 0x2C | 0x0 | [0]=ccureg_pwm_cg | PWM block clock gate (reserved) |
| ADC_BLK_CG | 0x30 | 0x0 | [0]=ccureg_adc_cg | ADC block clock gate (reserved) |
| CANBUS_BLK_CG | 0x34 | 0x0 | [0]=ccureg_canbus_cg | CANBUS block clock gate (reserved) |
| RST_HIS | 0x3C | 0x0 | [4:0] | Reset history. [4]=ESE_SW, [3]=SRECC, [2]=MIASS, [1]=WD, [0]=CSE_SW (all RW/1C) |

---

## 6. Misc Config

**Block**: ish_misc_config | **Base**: `0x04400000`
**Reset**: FUNCRST

Contains miscellaneous configuration registers including:
- ROM control
- Debug/DTF control
- Fabric configuration
- Clock divider settings

*(Register details available in raw text, Section 13)*

---

## 7. SBEP - Sideband Endpoint

**Block**: ish_sbep_config | **Base**: `0x04500000`
**Reset**: FUNCRST

PMC sideband interface registers. Opcode 0x6Fh, Tag 0x06h for SRAM gating energy reporting.

*(Register details available in raw text, Section 14)*

---

## 8. HPET Timer

**Block**: ish_hpet | **Base**: `0x04700000`
**Reset**: FUNCRST

High Precision Event Timer used for ISH firmware scheduling and wake events.

*(Register details available in raw text, Section 16)*

---

## 9. I3C HCI Controller

**Block**: DW_apb_i3c (2 instances) | **Base**: `0x04800000` (I3C0), `0x04802000` (I3C1)
**Reset**: I3C_RST | **Bus**: APB.MEM (32-bit)

### Core Control Registers

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| HCI_VERSION | 0x00 | 0x100 | HCI spec version (v1.0) |
| HC_CONTROL | 0x04 | 0x0 | Bus control: [31]=BUS_ENABLE, [30]=RESUME, [29]=ABORT, [8]=HOT_JOIN_CTRL, [7]=I2C_SLAVE_PRESENT, [0]=IBA_INCLUDE |
| MASTER_DEVICE_ADDR | 0x08 | 0x80000000 | [31]=DYNAMIC_ADDR_VALID, [22:16]=DYNAMIC_ADDR |
| HC_CAPABILITIES | 0x0C | varies | [7]=HDR_TS, [6]=HDR_DDR, [5]=NON_CURRENT_MASTER, [3]=AUTO_CMD, [2]=COMBO_CMD |
| RESET_CONTROL | 0x10 | 0x0 | [5]=IBI_QUEUE_RST, [4]=RX_FIFO_RST, [3]=TX_FIFO_RST, [2]=RESP_QUEUE_RST, [1]=CMD_QUEUE_RST, [0]=SOFT_RST |
| PRESENT_STATE | 0x14 | varies | [2]=CURRENT_MASTER |

### Interrupt Registers

| Register | Offset | Description |
|----------|--------|-------------|
| INTR_STATUS | 0x20 | Interrupt status (RW/1C). [10]=HC_INTERNAL_ERR |
| INTR_STATUS_ENABLE | 0x24 | Enable status reporting |
| INTR_SIGNAL_ENABLE | 0x28 | Enable interrupt signal |
| INTR_FORCE | 0x2C | Force interrupt (debug, WO) |

### Table Offset Registers

| Register | Offset | Description |
|----------|--------|-------------|
| DAT_SECTION_OFFSET | 0x30 | Device Address Table: [17:12]=TABLE_SIZE(0x10), [11:0]=OFFSET(0x080) |
| DCT_SECTION_OFFSET | 0x34 | Device Characteristic Table: [18:12]=TABLE_SIZE(0x20), [11:0]=OFFSET(0x100) |
| RING_HEADERS_SECTION_OFFSET | 0x38 | Ring headers offset: 0x3C0 |
| PIO_SECTION_OFFSET | 0x3C | PIO mode offset: 0x0C0 |
| EXTCAPS_SECTION_OFFSET | 0x40 | Extended capabilities offset: 0x200 |

### I3C Capabilities
- **Speed**: Up to 25 Mb/s (HDR/DDR mode)
- **Modes**: SDR, HDR-DDR, HDR-TS
- **Features**: In-Band Interrupts (IBI), Hot-Join, Dynamic Address Assignment
- **FIFO**: Command/Response/TX/RX/IBI queues

---

## 10. Watchdog Timer

**Block**: ish_wdt_config | **Base**: `0x04900000`
**Reset**: WD_RST | **Bus**: APB.MEM (32-bit)

### WDTC — Control (0x00)
**Default**: `0x0000A0A0`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [17] | WDT_EN | RW | 0 | Watchdog enable |
| [15:8] | WDT_T2 | RW | 0xA0 | T2 counter load value |
| [7:0] | WDT_T1 | RW | 0xA0 | T1 counter load value |

**Operation**: Two-stage watchdog. T1 counts down → interrupt. T2 counts down → reset.

### WDTR — Reload (0x04)
**Default**: `0x00000000`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [0] | WDT_RL | RW | 0 | Write 1 to reload T1/T2 counters. Auto-clears. |

### WDTV — Current Values (0x08)
**Default**: `0x0000A0A0`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [15:8] | WDT_T2_VAL | RO | 0xA0 | Current T2 counter value |
| [7:0] | WDT_T1_VAL | RO | 0xA0 | Current T1 counter value |

---

## 11. Security Block

**Block**: ish_security_block | **Base**: `0x04A00000`
**Reset**: FUNCRST

Contains security registers for:
- Firewall configuration
- Memory protection
- Access control

*(Register details available in raw text, Sections 22-23)*

---

## 12. SPI Controller

**Block**: DW_apb_ssi (2 instances) | **Base**: `0x08000000` (SPI0), `0x08002000` (SPI1)
**Reset**: SPI_RST | **Bus**: APB.MEM (32-bit)

### Control Registers

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| CTRLR0 | 0x00 | 0x70000 | Control reg 0. [24]=SSTE, [22:21]=SPI_FRF, [20:16]=DFS_32(0x7=8bit), [11]=SRL, [9:8]=TMOD(00=TX+RX), [7]=SCPOL, [6]=SCPH, [5:4]=FRF(00=SPI) |
| CTRLR1 | 0x04 | 0x0 | [15:0]=NDF: Number of data frames (RX-only/EEPROM mode) |
| SSIENR | 0x08 | 0x0 | [0]=SSI_EN: SSI enable (must be 0 to change config) |
| MWCR | 0x0C | 0x0 | Microwire control: [2]=MHS, [1]=MDD, [0]=MWMOD |
| SER | 0x10 | 0x0 | [1:0]=Slave select enable (1 bit per slave) |
| BAUDR | 0x14 | 0x0 | [15:0]=SCKDV: Clock divider (ssi_clk/SCKDV = SCLK freq, must be even) |

### FIFO & Status

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| TXFTLR | 0x18 | 0x0 | [5:0]=TX FIFO threshold (interrupt when level ≤ TFT) |
| RXFTLR | 0x1C | 0x0 | [5:0]=RX FIFO threshold (interrupt when level ≥ RFT+1) |
| TXFLR | 0x20 | 0x0 | [6:0]=TX FIFO level (RO) |
| RXFLR | 0x24 | 0x0 | [6:0]=RX FIFO level (RO) |
| SR | 0x28 | 0x6 | Status: [6]=DCOL, [4]=RFF, [3]=RFNE, [2]=TFE, [1]=TFNF, [0]=BUSY |

### Interrupt Registers

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| IMR | 0x2C | 0x3F | Interrupt mask: [5]=MSTIM, [4]=RXFIM, [3]=RXOIM, [2]=RXUIM, [1]=TXOIM, [0]=TXEIM |
| ISR | 0x30 | 0x0 | Interrupt status (masked, RO) |
| RISR | 0x34 | 0x0 | Raw interrupt status (unmasked, RO) |
| TXOICR | 0x38 | 0x0 | Read clears TX overflow interrupt |
| RXOICR | 0x3C | 0x0 | Read clears RX overflow interrupt |
| RXUICR | 0x40 | 0x0 | Read clears RX underflow interrupt |
| MSTICR | 0x44 | 0x0 | Read clears multi-master contention interrupt |
| ICR | 0x48 | 0x0 | Read clears ALL SPI interrupts |

### DMA & Data

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| DMACR | 0x4C | 0x0 | [1]=TDMAE (TX DMA enable), [0]=RDMAE (RX DMA enable) |
| DMATDLR | 0x50 | 0x0 | [5:0]=DMA TX data level threshold |
| DMARDLR | 0x54 | 0x0 | [5:0]=DMA RX data level threshold |
| IDR | 0x58 | 0xFFFFFFFF | Peripheral identification (RO) |
| SSI_VERSION_ID | 0x5C | 0x3430332A | Component version (RO) |
| DR0 | 0x60 | 0x0 | Data register (R=RX FIFO, W=TX FIFO). 36 sequential addresses for burst |

---

## 13. UART Controller

**Block**: DW_apb_uart (3 instances) | **Base**: `0x08100000` (UART0), `0x08102000` (UART1), `0x08104000` (UART2)
**Reset**: UART_RST | **Bus**: APB.MEM (32-bit) | **Speed**: Up to 4 Mb/s

### Data & Control

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| RBR/THR/DLL | 0x00 | 0x0 | Receive buffer (read, DLAB=0) / Transmit holding (write, DLAB=0) / Divisor latch low (DLAB=1) |
| IER/DLH | 0x04 | 0x0 | Interrupt enable (DLAB=0): [7]=PTIME, [3]=EDSSI, [2]=ELSI, [1]=ETBEI, [0]=ERBFI / Divisor latch high (DLAB=1) |
| IIR/FCR | 0x08 | 0x1 | Interrupt ID (read): [7:6]=FIFOSE, [3:0]=IID / FIFO control (write): [7:6]=RCVR_TRIGGER, [5:4]=TX_EMPTY_TRIGGER, [2]=XFIFOR, [1]=RFIFOR, [0]=FIFOE |
| LCR | 0x0C | 0x0 | Line control: [7]=DLAB, [6]=BC(break), [5]=SP, [4]=EPS, [3]=PEN, [2]=STOP, [1:0]=DLS(data length) |
| MCR | 0x10 | 0x0 | Modem control: [5]=AFCE, [4]=Loopback, [3]=OUT2, [2]=OUT1, [1]=RTS, [0]=DTR |
| LSR | 0x14 | 0x60 | Line status (RO): [7]=RFE, [6]=TEMT, [5]=THRE, [4]=BI, [3]=FE, [2]=PE, [1]=OE, [0]=DR |
| MSR | 0x18 | 0x0 | Modem status (RO): [7]=DCD, [6]=RI, [5]=DSR, [4]=CTS, [3]=DDCD, [2]=TERI, [1]=DDSR, [0]=DCTS |
| SCR | 0x1C | 0x0 | Scratchpad (no HW function) |

### Extended Registers

| Register | Offset | Description |
|----------|--------|-------------|
| FAR | 0x70 | FIFO access register (test mode) |
| USR | 0x7C | UART status register |
| TFL | 0x80 | TX FIFO level |
| RFL | 0x84 | RX FIFO level |
| HTX | 0xA4 | Halt TX |
| DMASA | 0xA8 | DMA software acknowledge |
| TCR | 0xAC | Transceiver control |
| DE_EN | 0xB0 | Driver output enable |
| RE_EN | 0xB4 | Receiver output enable |
| DET | 0xB8 | Driver output enable timing |
| TAT | 0xBC | Turn-around timing |
| DLF | 0xC0 | Divisor latch fraction |
| RAR | 0xC4 | Receive address register |
| TAR | 0xC8 | Transmit address register |
| LCR_EXT | 0xCC | Line control extended |
| CPR | 0xF4 | Component parameter (RO) |
| UCV | 0xF8 | UART component version (RO) |
| CTR | 0xFC | Component type (RO) |

---

## 14. DMA Misc

**Block**: ish_dma_misc_config | **Base**: `0x10101000`
**Reset**: DMA_RST | **Bus**: APB.MEM (32-bit)

8 channels (CH0-CH7) with identical register layout:

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| DMA_CTL_CH0 | 0x00 | 0x0 | DMA control channel 0 |
| DMA_CTL_CH1 | 0x04 | 0x0 | DMA control channel 1 |
| DMA_CTL_CH2 | 0x08 | 0x0 | DMA control channel 2 |
| DMA_CTL_CH3 | 0x0C | 0x0 | DMA control channel 3 |
| DMA_CTL_CH4 | 0x10 | 0x0 | DMA control channel 4 |
| DMA_CTL_CH5 | 0x14 | 0x0 | DMA control channel 5 |
| DMA_CTL_CH6 | 0x18 | 0x0 | DMA control channel 6 |
| DMA_CTL_CH7 | 0x1C | 0x0 | DMA control channel 7 |

### Per-Channel Bit Fields

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [10] | LLI_MODE | RW | 0 | Descriptor location: 0=internal SRAM, 1=external DRAM |
| [9] | WR_NON_SNOOP | RW | 0 | Write non-snoop: 0=snoop IA cache, 1=no snoop |
| [8] | RD_NON_SNOOP | RW | 0 | Read non-snoop: 0=snoop IA cache, 1=no snoop |
| [6:5] | WR_RS | RW | 0 | Write root-space: 0=RS0(Host DRAM), 3=RS3(IMR DRAM) |
| [4:3] | RD_RS | RW | 0 | Read root-space: 0=RS0(Host DRAM), 3=RS3(IMR DRAM) |
| [1:0] | TRANSFER_MODE | RW | 0 | 0=Int→Int, 1=Int→Ext, 2=Ext→Int, 3=Ext→Ext |

---

## 15. SRAM Controller

**Block**: ish_sramc_config | **Base**: `0x10500000`
**Reset**: SRAM_RST | **Bus**: APB.MEM (32-bit)

### Configuration

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| SRAM_CFGR | 0x00 | 0x0 | Config: [4]=ECC_DISABLE, [3]=DISABLE_SPEC_RMW |
| SRAM_LIMIT | 0x40 | 0x0 | [29:20]=CCM_LIMIT (4KB units), [9:0]=ICCM_LIMIT (4KB units). E.g. 384KB CCM=0x60, 48KB ICCM=0xC |

### Interrupt Registers

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| SRAM_INTR_STS | 0x04 | 0x0 | Interrupt status (RW/1C): [6]=OCP_RANGE_ERR, [5]=DCCM_RANGE_ERR, [4]=ICCM_RANGE_ERR, [3]=CCM_ERASE_DONE, [2]=L2_ERASE_DONE |
| SRAM_INTR_MASK | 0x08 | 0x74 | Interrupt mask: [6]=OCP_ERR, [5]=DCCM_ERR, [4]=ICCM_ERR, [2]=ERASE_DONE (all default masked=1) |

### Erase Engine

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| SRAM_ERASE_CTRL | 0x0C | 0x0 | [19:2]=ERASE_SIZE (QWords), [1]=MEMORY_RANGE(0=L2,1=CCM), [0]=ERASE_START(RW/1S, auto-clear) |
| SRAM_ERASE_ADDR | 0x10 | 0x0 | [20:0]=Starting physical address for erase |

### ECC Error Logging

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| SRAM_ECC_FAKE_ERR | 0x1C | 0x0 | Debug: [1]=FAKE_ERR_STS(RW/1C), [0]=FAKE_ERR(RW/1C, generates 1-cycle pulse) |
| SRAM_LOG_EN | 0x20 | 0x0 | Enable logging: [4]=OCP, [3]=DCCM, [2]=ICCM, [1]=Single ECC, [0]=Double ECC |
| SRAM_DOUBLE_ERR_ECC_LOG | 0x24 | 0x0 | [31]=Lock(RW/1C), [30]=Uncorrectable, [28:24]=Bank_CCM, [22:18]=Bank_L2, [12:0]=Address |
| SRAM_DOUBLE_ECC_COUNT | 0x28 | 0x0 | [31]=Reset(RW/1C), [15:8]=L2_count, [7:0]=CCM_count (saturate at 0xFF) |
| SRAM_SINGLE_ERR_ECC_LOG | 0x30 | 0x0 | [31]=Lock(RW/1C), [30]=Correctable, [28:24]=Bank_CCM, [22:18]=Bank_L2, [12:0]=Address |
| SRAM_SINGLE_ECC_COUNT | 0x34 | 0x0 | [31]=Reset(RW/1C), [15:8]=L2_count, [7:0]=CCM_count (saturate at 0xFF) |

### Bank Status & Error Logs

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| SRAM_BANK_STATUS | 0x2C | 0x0 | [9:0]=Per-bank ready status (RO, 1=ready) |
| SRAM_ICCM_ERROR_LOG | 0x44 | 0x0 | [31]=Lock, [30]=CMD(0=Read), [20:0]=Address |
| SRAM_DCCM_ERROR_LOG | 0x48 | 0x0 | [31]=Lock, [30]=CMD(0=Read,1=Write), [20:0]=Address |
| SRAM_OCP_ERROR_LOG | 0x4C | 0x0 | [31]=Lock, [30]=CMD, [29:24]=MConnID, [21:0]=Address |

### Bank Table (Flexible Banking)

10 entries at offsets `0x50`-`0x74` (BANK_TABLE_0 through BANK_TABLE_9).
Each maps a 16KB memory segment to a physical SRAM bank.

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [31:25] | GRW | RW | 0 | Generic RW |
| [24] | CLKSEL | RW | 0 | 0=Low speed clock, 1=High speed clock to bank |
| [17:16] | LB | RW | 0x2 | Logical bank (L2=2, CCM=others) |
| [8] | PB_TYPE | RW | 0 | Physical bank type |
| [3:0] | PB_INDEX | RW | N | Physical bank index (default = entry number) |

---

## 16. Fabric

**Block**: ish_fabric | **Base**: `0x10600000`
**Reset**: FABRIC_RST

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| ID_COREID | 0x00 | varies | Fabric core ID (RO) |
| ID_REVISIONID | 0x04 | varies | Fabric revision ID (RO) |
| FAULTEN | 0x08 | 0x0 | Fault enable |
| ERRVLD | 0x0C | 0x0 | Error valid (RO) |
| ERRCLR | 0x10 | 0x0 | Error clear (write to clear) |
| ERRLOG0 | 0x14 | 0x0 | Error log 0: command/opcode |
| ERRLOG1 | 0x18 | 0x0 | Error log 1: address low |
| ERRLOG3 | 0x20 | 0x0 | Error log 3: address high |
| ERRLOG4 | 0x24 | 0x0 | Error log 4: security info |
| ERRLOG5 | 0x28 | 0x0 | Error log 5: master ID |
| STALLEN | 0x4C | 0x0 | Stall enable |

---

## Address Map Summary

| Block | Base Address | Section(s) | Instance Count |
|-------|-------------|------------|----------------|
| I2C | 0x00000000 | 1 | 3 (0x2000 stride) |
| GPIO | 0x00100000 | 2 | 1 |
| IPC HOST | 0x04100000 | 3 | 1 |
| IPC HOSTSPARE | 0x04101000 | 4 | 1 |
| IPC CSE | 0x04102000 | 5 | 1 |
| IPC PMC | 0x04103000 | 6 | 1 |
| IPC CNVi | 0x04104000 | 7 | 1 |
| IPC ACE | 0x04105000 | 8 | 1 |
| IPC ESE | 0x04106000 | 9 | 1 |
| IPC AVB | 0x04107000 | 10 | 1 |
| PMU | 0x04200000 | 11 | 1 |
| CCU | 0x04300000 | 12 | 1 |
| Misc | 0x04400000 | 13 | 1 |
| SBEP | 0x04500000 | 14 | 1 |
| HPET | 0x04700000 | 16 | 1 |
| I3C | 0x04800000 | 17-20 | 2 (0x2000 stride) |
| WDT | 0x04900000 | 21 | 1 |
| Security | 0x04A00000 | 22-23 | 1 |
| Dashboard | 0x04B00000 | 24 | 1 |
| SPI | 0x08000000 | 25 | 2 (0x2000 stride) |
| UART | 0x08100000 | 26-27 | 3 (0x2000 stride) |
| DMA Misc | 0x10101000 | 28 | 1 (8 channels) |
| SRAM Ctrl | 0x10500000 | 29 | 1 |
| Fabric | 0x10600000 | 30 | 1 |

---

*Generated from TTL ISH OSXML register PDF (ish_mia_bfm_rdl_top.pdf). Raw text: 80,645 lines.*
