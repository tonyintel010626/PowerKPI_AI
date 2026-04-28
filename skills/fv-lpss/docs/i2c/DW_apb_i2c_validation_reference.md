# DW_apb_i2c Silicon Validation Reference -- Intel LPSS

| Field | Value |
|-------|-------|
| Source | Synopsys DW_apb_i2c Databook v2.02a (July 2018), 338 pages |
| IP Version on Intel LPSS | v2.00a |
| Platforms | Novalake (NVL), Panther Lake (PTL) |
| Audience | Intel LPSS Silicon Validation Engineers |
| Document Version | 2.0 |
| Date | 2026-03-11 |
| Purpose | Complete register-level validation reference digesting all content from the Synopsys databook, tailored for Intel LPSS platforms |

> This document is a comprehensive digest of the entire Synopsys DW_apb_i2c Databook v2.02a.
> It is designed to be self-contained for silicon validation work. For edge cases beyond this
> document, consult the original databook directly.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [I2C Protocol as Implemented](#2-i2c-protocol-as-implemented)
3. [Complete Register Map](#3-complete-register-map)
4. [Critical Register Details](#4-critical-register-details)
5. [TX FIFO Management](#5-tx-fifo-management)
6. [Master Mode Programming](#6-master-mode-programming)
7. [Slave Mode Programming](#7-slave-mode-programming)
8. [Abort and Disable Mechanism](#8-abort-and-disable-mechanism)
9. [Error Handling](#9-error-handling)
10. [DMA Interface](#10-dma-interface)
11. [Interrupt System](#11-interrupt-system)
12. [Clock Configuration](#12-clock-configuration)
13. [Spike Suppression](#13-spike-suppression)
14. [Speed Modes](#14-speed-modes)
15. [Bus Clear and Recovery](#15-bus-clear-and-recovery)
16. [Device ID](#16-device-id)
17. [SMBus and PMBus Support](#17-smbus-and-pmbus-support)
18. [Multi-Master](#18-multi-master)
19. [Programming Examples](#19-programming-examples)
20. [Integration and Verification](#20-integration-and-verification)
21. [Configuration Parameters](#21-configuration-parameters)
22. [Validation Checklist](#22-validation-checklist)
23. [Appendix](#23-appendix)

---

## 1. Product Overview

### 1.1 Features

The DW_apb_i2c is a configurable I2C controller IP that supports:

- Master and slave operation (one role at a time, never both simultaneously)
- 7-bit and 10-bit addressing
- Five speed modes: Standard (SS), Fast (FS), Fast-mode Plus (FM+), High-speed (HS), Ultra-Fast (UFM)
- Combined format transfers (write-then-read with RESTART)
- Programmable TX and RX FIFOs (2 to 256 entries)
- DMA handshaking interface (DW_ahb_dmac compatible)
- Programmable SDA hold and setup times
- Spike suppression on SCL and SDA
- Bus clear and recovery mechanism
- Device ID support (I2C v6.0)
- SMBus v3.0 and PMBus v1.2 support with ARP, UDID, Alert, Suspend
- Bulk transfer mode in slave operation
- Register timeout counter

### 1.2 Block Diagram Components

| Block | Function |
|-------|----------|
| AMBA Bus Interface Unit | APB slave interface to host processor |
| Register File | Configuration and status registers (0x00-0xFC) |
| Master State Machine | Controls master-mode protocol sequences |
| Slave State Machine | Controls slave-mode protocol sequences |
| Clock Generator | SCL generation from HCNT/LCNT registers |
| TX Shift Register | Serializes data from TX FIFO to SDA |
| RX Shift Register | Deserializes data from SDA to RX FIFO |
| RX Filter | Spike suppression on SCL and SDA inputs |
| Toggle Synchronizer | Synchronizes asynchronous I2C signals to ic_clk domain |
| DMA Interface | TX/RX handshaking for DW_ahb_dmac |
| Interrupt Controller | 15 I2C + 11 SMBus interrupt sources |
| TX FIFO | Transmit buffer (configurable depth, Intel LPSS: 64) |
| RX FIFO | Receive buffer (configurable depth, Intel LPSS: 64) |

### 1.3 Standards Supported

| Standard | Version | Date |
|----------|---------|------|
| I2C Bus Specification | v6.0 | April 2014 |
| SMBus Specification | v3.0 | January 2015 |
| PMBus Specification | v1.2 | September 2010 |

### 1.4 Speed Modes Summary

| Mode | Abbrev | Max Bit Rate | Drive Type | ACK | Arbitration | Clock Stretching |
|------|--------|-------------|-----------|-----|-------------|-----------------|
| Standard | SS | 100 kbit/s | Open-drain | Yes | Yes | Yes |
| Fast | FS | 400 kbit/s | Open-drain | Yes | Yes | Yes |
| Fast-mode Plus | FM+ | 1 Mbit/s | Open-drain | Yes | Yes | Yes |
| High-speed | HS | 3.4 Mbit/s | Open-drain | Yes | Yes | Yes |
| Ultra-Fast | UFM | 5 Mbit/s | Push-pull | No | No | No |

### 1.5 Intel LPSS Configuration

> **Intel LPSS:** The following configuration applies to all Intel LPSS I2C instances on NVL and PTL platforms.

| Parameter | Intel LPSS Value | Note |
|-----------|-----------------|------|
| Number of instances | 6 (I2C0-I2C5) | |
| TX FIFO depth | 64 entries | IC_TX_BUFFER_DEPTH=64 |
| RX FIFO depth | 64 entries | IC_RX_BUFFER_DEPTH=64 |
| IC_EMPTYFIFO_HOLD_MASTER_EN | 1 (Mode 1) | Explicit STOP/RESTART control required |
| DMA support (I2C0-3) | Yes | IC_HAS_DMA=1 |
| DMA support (I2C4-5) | No | IC_HAS_DMA=0, PIO only |
| IP version | v2.00a | Databook covers v2.02a |
| PythonSV base path | `nn.sv.socket0.pcd.lpss.i2c0.cfg` | NVL PCD-H; replace i2c0 with i2c1-5 |

---

## 2. I2C Protocol as Implemented

### 2.1 Bus Conditions

The I2C bus uses two lines:
- **SDA** (Serial Data): Bidirectional data line
- **SCL** (Serial Clock): Clock line, driven by master

Both lines are open-drain with external pull-up resistors (except UFM mode which uses push-pull).

**Data Validity Rule:** SDA must be stable while SCL is HIGH. SDA may only change while SCL is LOW.

| Condition | SDA Transition | SCL State | Meaning |
|-----------|---------------|-----------|---------|
| START (S) | HIGH -> LOW | HIGH | Begin transfer |
| STOP (P) | LOW -> HIGH | HIGH | End transfer |
| RESTART (Sr) | HIGH -> LOW | HIGH | Repeated START without STOP |
| Data bit | Stable | HIGH | Valid data |
| Data change | Transition | LOW | Allowed |

### 2.2 Addressing

**7-bit addressing format:**
```
S | A6 A5 A4 A3 A2 A1 A0 | R/W | ACK | DATA... | P
```

**10-bit addressing format:**
```
S | 1 1 1 1 0 A9 A8 | W | ACK | A7-A0 | ACK | DATA... | P
```
First byte: `11110XX0` where XX = address bits [9:8]. Second byte: address bits [7:0].

For 10-bit read, a RESTART is required after the write phase:
```
S | 11110XX | W | ACK | A7-A0 | ACK | Sr | 11110XX | R | ACK | DATA... | P
```

### 2.3 Reserved Addresses

| Address (7-bit) | R/W | Description | DW_apb_i2c Support |
|-----------------|-----|-------------|-------------------|
| 0000 000 | 0 | General Call | Yes (IC_ACK_GENERAL_CALL) |
| 0000 000 | 1 | START byte | Yes (IC_TAR[10]=1, [11]=1) |
| 0000 001 | X | CBUS address | No |
| 0000 010 | X | Reserved (different bus) | No |
| 0000 011 | X | Reserved (future) | No |
| 0000 1XX | X | HS mode master code | Yes (IC_HS_MADDR) |
| 1111 1XX | X | Reserved (future) | No |
| 1111 0XX | X | 10-bit addressing prefix | Yes |

### 2.4 ACK/NACK Signaling

- **ACK:** Receiver pulls SDA LOW during the 9th clock cycle
- **NACK:** Receiver leaves SDA HIGH during the 9th clock cycle
- Master-receiver sends NACK on the last byte to signal end of read

### 2.5 General Call

Address 0x00 with W bit. All slaves with IC_ACK_GENERAL_CALL=1 respond with ACK. Triggers GEN_CALL interrupt (bit 11). The first data byte determines the function:
- 0x06: Reset and write programmable part of slave address by hardware
- 0x04: Write programmable part of slave address by hardware
- 0x00: Not allowed (second byte 0x00 = additional General Call info)

### 2.6 START Byte

Address 0x00 with R bit (IC_TAR[10]=1, IC_TAR[11]=1). Used for slow slave processors that need time to detect START. The START byte (0000 0001) is followed by NACK and RESTART.

### 2.7 Clock Stretching

A slave may hold SCL LOW to slow down the master:
- Slave-TX: stretches when TX FIFO is empty (waiting for data)
- Slave-RX: stretches when RX FIFO is full (if RX_FIFO_FULL_HLD_CTRL=1)
- Master Mode 1: holds SCL LOW when TX FIFO empties (IC_EMPTYFIFO_HOLD_MASTER_EN=1)

---

## 3. Complete Register Map

### 3.1 Register Map by Functional Group

#### Core Control Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x00 | IC_CON | config-dependent | R/W | I2C Control |
| 0x04 | IC_TAR | 0x00000055 | R/W | Target Address |
| 0x08 | IC_SAR | 0x00000055 | R/W | Slave Address |
| 0x0C | IC_HS_MADDR | 0x00000001 | R/W | HS Master Mode Code Address |
| 0x10 | IC_DATA_CMD | 0x00000000 | R/W | Data Buffer and Command |
| 0x6C | IC_ENABLE | 0x00000000 | R/W | Enable Register |
| 0x70 | IC_STATUS | 0x00000006 | R | Status Register |
| 0x9C | IC_ENABLE_STATUS | 0x00000000 | R | Enable Status |

#### SCL Clock Configuration Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x14 | IC_SS_SCL_HCNT | 0x00000190 | R/W | SS SCL High Count (also UFM HCNT) |
| 0x18 | IC_SS_SCL_LCNT | 0x000001D6 | R/W | SS SCL Low Count (also UFM LCNT) |
| 0x1C | IC_FS_SCL_HCNT | 0x0000003C | R/W | FS/FM+ SCL High Count (also UFM TBuf) |
| 0x20 | IC_FS_SCL_LCNT | 0x00000082 | R/W | FS/FM+ SCL Low Count |
| 0x24 | IC_HS_SCL_HCNT | 0x00000006 | R/W | HS SCL High Count |
| 0x28 | IC_HS_SCL_LCNT | 0x00000010 | R/W | HS SCL Low Count |

#### FIFO Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x38 | IC_RX_TL | 0x00000000 | R/W | RX FIFO Threshold Level |
| 0x3C | IC_TX_TL | 0x00000000 | R/W | TX FIFO Threshold Level |
| 0x74 | IC_TXFLR | 0x00000000 | R | TX FIFO Level (current entries) |
| 0x78 | IC_RXFLR | 0x00000000 | R | RX FIFO Level (current entries) |

#### Interrupt Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x2C | IC_INTR_STAT | 0x00000000 | R | Interrupt Status (masked) |
| 0x30 | IC_INTR_MASK | 0x000008FF | R/W | Interrupt Mask |
| 0x34 | IC_RAW_INTR_STAT | 0x00000000 | R | Raw Interrupt Status (unmasked) |
| 0x40 | IC_CLR_INTR | 0x00000000 | R | Clear All SW-Clearable Interrupts |
| 0x44 | IC_CLR_RX_UNDER | 0x00000000 | R | Clear RX_UNDER Interrupt |
| 0x48 | IC_CLR_RX_OVER | 0x00000000 | R | Clear RX_OVER Interrupt |
| 0x4C | IC_CLR_TX_OVER | 0x00000000 | R | Clear TX_OVER Interrupt |
| 0x50 | IC_CLR_RD_REQ | 0x00000000 | R | Clear RD_REQ Interrupt |
| 0x54 | IC_CLR_TX_ABRT | 0x00000000 | R | Clear TX_ABRT Interrupt |
| 0x58 | IC_CLR_RX_DONE | 0x00000000 | R | Clear RX_DONE Interrupt |
| 0x5C | IC_CLR_ACTIVITY | 0x00000000 | R | Clear ACTIVITY Interrupt |
| 0x60 | IC_CLR_STOP_DET | 0x00000000 | R | Clear STOP_DET Interrupt |
| 0x64 | IC_CLR_START_DET | 0x00000000 | R | Clear START_DET Interrupt |
| 0x68 | IC_CLR_GEN_CALL | 0x00000000 | R | Clear GEN_CALL Interrupt |
| 0xA8 | IC_CLR_RESTART_DET | 0x00000000 | R | Clear RESTART_DET Interrupt |
| 0xB4 | IC_CLR_SCL_STUCK_DET | 0x00000000 | R | Clear SCL_STUCK_AT_LOW Interrupt |

#### Timing Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x7C | IC_SDA_HOLD | config-dependent | R/W | SDA Hold Time (TX and RX) |
| 0x94 | IC_SDA_SETUP | 0x00000064 | R/W | SDA Setup Time |
| 0xA0 | IC_FS_SPKLEN | IC_DEFAULT_FS_SPKLEN | R/W | FS/SS/FM+ Spike Suppression (also UFM) |
| 0xA4 | IC_HS_SPKLEN | IC_DEFAULT_HS_SPKLEN | R/W | HS Spike Suppression |

#### Abort and Error Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x80 | IC_TX_ABRT_SOURCE | 0x00000000 | R | Transmit Abort Source (21+ bits) |
| 0x84 | IC_SLV_DATA_NACK_ONLY | 0x00000000 | R/W | Slave Data NACK Only |

#### DMA Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x88 | IC_DMA_CR | 0x00000000 | R/W | DMA Control Register |
| 0x8C | IC_DMA_TDLR | 0x00000000 | R/W | DMA Transmit Data Level |
| 0x90 | IC_DMA_RDLR | 0x00000000 | R/W | DMA Receive Data Level |

#### Bus Clear / Recovery Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0xAC | IC_SCL_STUCK_AT_LOW_TIMEOUT | config-dependent | R/W | SCL Stuck Low Timeout |
| 0xB0 | IC_SDA_STUCK_AT_LOW_TIMEOUT | config-dependent | R/W | SDA Stuck Low Timeout |

#### Device ID Register

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0xB8 | IC_DEVICE_ID | 0x00000000 | R | Device ID (24-bit) |

#### Slave Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0x98 | IC_ACK_GENERAL_CALL | 0x00000001 | R/W | ACK General Call |
| 0xD8 | IC_OPTIONAL_SAR | 0x00000000 | R/W | Optional Slave Address |

#### SMBus / PMBus Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0xBC | IC_SMBUS_CLK_LOW_SEXT | config-dependent | R/W | SMBus Slave Clock Extend Timeout |
| 0xC0 | IC_SMBUS_CLK_LOW_MEXT | config-dependent | R/W | SMBus Master Clock Extend Timeout |
| 0xC4 | IC_SMBUS_THIGH_MAX_IDLE_COUNT | config-dependent | R/W | SMBus THigh Max Bus-Idle Count |
| 0xC8 | IC_SMBUS_INTR_STAT | 0x00000000 | R | SMBus Interrupt Status (masked) |
| 0xCC | IC_SMBUS_INTR_MASK | 0x00000000 | R/W | SMBus Interrupt Mask |
| 0xD0 | IC_SMBUS_RAW_INTR_STAT | 0x00000000 | R | SMBus Raw Interrupt Status |
| 0xD4 | IC_CLR_SMBUS_INTR | 0x00000000 | W1C | Clear SMBus Interrupts (write-1-to-clear) |
| 0xDC | IC_SMBUS_UDID_LSB | 0x00000000 | R/W | UDID LSB / Word0 |
| 0xE0 | IC_SMBUS_UDID_WORD1 | 0x00000000 | R/W | UDID Word1 |
| 0xE4 | IC_SMBUS_UDID_WORD2 | 0x00000000 | R/W | UDID Word2 |
| 0xE8 | IC_SMBUS_UDID_WORD3 | 0x00000000 | R/W | UDID Word3 |

#### Identification Registers

| Offset | Register | Reset Value | Access | Description |
|--------|----------|-------------|--------|-------------|
| 0xF0 | REG_TIMEOUT_RST | config-dependent | R/W | Register Timeout Counter Reset |
| 0xF4 | IC_COMP_PARAM_1 | config-encoded | R | Component Parameter 1 (encoded config) |
| 0xF8 | IC_COMP_VERSION | 0x3230322A | R | Component Version (ASCII "202*") |
| 0xFC | IC_COMP_TYPE | 0x44570140 | R | Component Type (ASCII "DW" + 0x0140) |

---

## 4. Critical Register Details

This section provides complete bit-field tables for every register. Registers are writable only when IC_ENABLE[0]=0 unless otherwise noted.

### 4.1 IC_CON (0x00) -- I2C Control Register

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | MASTER_MODE | R/W | IC_MASTER_MODE | 0=slave only; 1=master enabled. Must not be 1 simultaneously with IC_SLAVE_DISABLE=0 in practice. |
| [2:1] | SPEED | R/W | IC_MAX_SPEED_MODE | 1=SS (100k); 2=FS or FM+ (400k/1M); 3=HS (3.4M). Clamped to IC_MAX_SPEED_MODE. |
| [3] | IC_10BITADDR_SLAVE | R/W | IC_10BITADDR_SLAVE | 0=7-bit slave address; 1=10-bit slave address. |
| [4] | IC_10BITADDR_MASTER | R/W | IC_10BITADDR_MASTER | 0=7-bit master address; 1=10-bit master address. Read-only if I2C_DYNAMIC_TAR_UPDATE=1 (use IC_TAR[12] instead). |
| [5] | IC_RESTART_EN | R/W | IC_RESTART_EN | 0=RESTART disabled; 1=RESTART enabled. Required for: 10-bit reads, combined format, HS mode, Device ID. |
| [6] | IC_SLAVE_DISABLE | R/W | IC_SLAVE_DISABLE | 0=slave enabled; 1=slave disabled. |
| [7] | STOP_DET_IFADDRESSED | R/W | IC_STOP_DET_IF_ADDRESSED | Slave mode: 0=STOP_DET always; 1=STOP_DET only when addressed. |
| [8] | TX_EMPTY_CTRL | R/W | 0 | 0=TX_EMPTY when FIFO level <= TX_TL; 1=TX_EMPTY when FIFO level <= TX_TL AND controller is actively transferring. |
| [9] | RX_FIFO_FULL_HLD_CTRL | R/W | 0 | 1=hold bus (stretch SCL) when RX FIFO full. Read-only=0 if IC_RX_FULL_HLD_BUS_EN=0. |
| [10] | STOP_DET_IF_MASTER_ACTIVE | R/W | 0 | 1=STOP_DET interrupt only when master is active. Exists if IC_STOP_DET_IF_MASTER_ACTIVE=1. |
| [11] | BUS_CLEAR_FEATURE_CTRL | R/W | 0 | 1=enable bus clear feature. Exists if IC_BUS_CLEAR_FEATURE=1. |
| [16] | OPTIONAL_SAR_CTRL | R/W | 0 | 1=enable IC_OPTIONAL_SAR register as additional slave address. Exists if IC_OPTIONAL_SAR=1. |
| [17] | SMBUS_SLAVE_QUICK_EN | R/W | 0 | 1=slave receives only Quick commands. Exists if IC_SMBUS=1. |
| [18] | SMBUS_ARP_EN | R/W | 0 | 1=ARP enabled in slave mode. Exists if IC_SMBUS_ARP=1. |
| [19] | SMBUS_PERSISTENT_SLV_ADDR_EN | R/W | 0 | 1=slave address persists across ARP Reset. Exists if IC_SMBUS_ARP=1. |

> **Intel LPSS:** Typical master-mode init: MASTER_MODE=1, SPEED=2 (FS/FM+), IC_RESTART_EN=1, IC_SLAVE_DISABLE=1.

### 4.2 IC_TAR (0x04) -- I2C Target Address Register

> **Write constraint:** If I2C_DYNAMIC_TAR_UPDATE=0, writable only when IC_ENABLE[0]=0. If =1, writable while enabled.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [9:0] | IC_TAR | R/W | 0x055 | Target slave address (7-bit: use bits [6:0]; 10-bit: use all [9:0]). |
| [10] | GC_OR_START | R/W | 0 | When SPECIAL=1: 0=General Call; 1=START byte. |
| [11] | SPECIAL | R/W | 0 | 1=enable special transfers (General Call, START byte, Device ID). |
| [12] | IC_10BITADDR_MASTER | R/W | 0 | Exists if I2C_DYNAMIC_TAR_UPDATE=1. Overrides IC_CON[4]. 0=7-bit; 1=10-bit. |
| [13] | DEVICE_ID | R/W | 0 | 1=Device ID transfer. Requires SPECIAL=1. Exists if IC_DEVICE_ID=1. |
| [16] | SMBUS_QUICK_CMD | R/W | 0 | 1=Quick Command. R/W bit determined by CMD field of IC_DATA_CMD. Exists if IC_SMBUS=1. |

### 4.3 IC_SAR (0x08) -- I2C Slave Address Register

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [9:0] | IC_SAR | R/W | 0x055 | Local slave address. 7-bit: bits [6:0]; 10-bit: bits [9:0]. |

### 4.4 IC_HS_MADDR (0x0C) -- HS Master Mode Code Address

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [2:0] | IC_HS_MAR | R/W | 0x1 | HS mode master code (0-7). Sent as 0000_1XXX in F/S mode preamble. |

### 4.5 IC_DATA_CMD (0x10) -- Data Buffer and Command

> **Access:** Write to push TX data/commands; Read to pop RX data. No enable constraint.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | DAT | R/W | 0x00 | Write: data byte to transmit. Read: received data byte. |
| [8] | CMD | W | 0 | 0=write transfer; 1=read transfer (master issues read request). |
| [9] | STOP | W | 0 | 1=issue STOP after this byte. Only effective when IC_EMPTYFIFO_HOLD_MASTER_EN=1 (Mode 1). |
| [10] | RESTART | W | 0 | 1=issue RESTART before this byte. Requires IC_RESTART_EN=1. Only effective in Mode 1. |
| [11] | FIRST_DATA_BYTE | R | 0 | 1=first data byte received after address match (slave mode). |

> **Intel LPSS (Mode 1):** Since IC_EMPTYFIFO_HOLD_MASTER_EN=1, you MUST set STOP=1 on the last command entry to terminate the transfer. Without it, the master holds SCL LOW indefinitely.

### 4.6 IC_SS_SCL_HCNT (0x14) -- Standard Speed SCL High Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_SS_SCL_HCNT | R/W | 0x0190 | SCL HIGH period count in ic_clk cycles for SS mode. Min: SPKLEN+5 (FREQ_OPT=0) or 1 (FREQ_OPT=1). |

> When IC_UFM_EN=1, this register is repurposed as IC_UFM_SCL_HCNT with min value 3.

### 4.7 IC_SS_SCL_LCNT (0x18) -- Standard Speed SCL Low Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_SS_SCL_LCNT | R/W | 0x01D6 | SCL LOW period count in ic_clk cycles for SS mode. Min: SPKLEN+7 (FREQ_OPT=0) or 6 (FREQ_OPT=1). |

> When IC_UFM_EN=1, this register is repurposed as IC_UFM_SCL_LCNT with min value 5.

### 4.8 IC_FS_SCL_HCNT (0x1C) -- Fast Speed SCL High Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_FS_SCL_HCNT | R/W | 0x003C | SCL HIGH period count for FS and FM+ modes. Min: SPKLEN+5 (FREQ_OPT=0) or 1 (FREQ_OPT=1). |

> When IC_UFM_EN=1, this register is repurposed as IC_UFM_TBUF_CNT (bus free time between STOP and START in UFM mode).

### 4.9 IC_FS_SCL_LCNT (0x20) -- Fast Speed SCL Low Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_FS_SCL_LCNT | R/W | 0x0082 | SCL LOW period count for FS and FM+ modes. Min: SPKLEN+7 (FREQ_OPT=0) or 6 (FREQ_OPT=1). |

### 4.10 IC_HS_SCL_HCNT (0x24) -- High Speed SCL High Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_HS_SCL_HCNT | R/W | 0x0006 | SCL HIGH period count for HS mode. Min: SPKLEN+5 (FREQ_OPT=0) or 1 (FREQ_OPT=1). |

### 4.11 IC_HS_SCL_LCNT (0x28) -- High Speed SCL Low Count

> **Write constraint:** Writable only when IC_ENABLE[0]=0.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_HS_SCL_LCNT | R/W | 0x0010 | SCL LOW period count for HS mode. Min: SPKLEN+7 (FREQ_OPT=0) or 6 (FREQ_OPT=1). |

### 4.12 IC_INTR_STAT (0x2C) -- Interrupt Status (Masked)

Read-only. Each bit is AND of IC_RAW_INTR_STAT and IC_INTR_MASK.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | R_RX_UNDER | R | 0 | Masked RX_UNDER status |
| [1] | R_RX_OVER | R | 0 | Masked RX_OVER status |
| [2] | R_RX_FULL | R | 0 | Masked RX_FULL status |
| [3] | R_TX_OVER | R | 0 | Masked TX_OVER status |
| [4] | R_TX_EMPTY | R | 0 | Masked TX_EMPTY status |
| [5] | R_RD_REQ | R | 0 | Masked RD_REQ status |
| [6] | R_TX_ABRT | R | 0 | Masked TX_ABRT status |
| [7] | R_RX_DONE | R | 0 | Masked RX_DONE status |
| [8] | R_ACTIVITY | R | 0 | Masked ACTIVITY status |
| [9] | R_STOP_DET | R | 0 | Masked STOP_DET status |
| [10] | R_START_DET | R | 0 | Masked START_DET status |
| [11] | R_GEN_CALL | R | 0 | Masked GEN_CALL status |
| [12] | R_RESTART_DET | R | 0 | Masked RESTART_DET status |
| [13] | R_MASTER_ON_HOLD | R | 0 | Masked MASTER_ON_HOLD status |
| [14] | R_SCL_STUCK_AT_LOW | R | 0 | Masked SCL_STUCK_AT_LOW status |

### 4.13 IC_INTR_MASK (0x30) -- Interrupt Mask Register

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | M_RX_UNDER | R/W | 1 | 1=unmasked (enabled) |
| [1] | M_RX_OVER | R/W | 1 | 1=unmasked |
| [2] | M_RX_FULL | R/W | 1 | 1=unmasked |
| [3] | M_TX_OVER | R/W | 1 | 1=unmasked |
| [4] | M_TX_EMPTY | R/W | 1 | 1=unmasked |
| [5] | M_RD_REQ | R/W | 1 | 1=unmasked |
| [6] | M_TX_ABRT | R/W | 1 | 1=unmasked |
| [7] | M_RX_DONE | R/W | 1 | 1=unmasked |
| [8] | M_ACTIVITY | R/W | 0 | 0=masked by default |
| [9] | M_STOP_DET | R/W | 0 | 0=masked by default |
| [10] | M_START_DET | R/W | 0 | 0=masked by default |
| [11] | M_GEN_CALL | R/W | 1 | 1=unmasked |
| [12] | M_RESTART_DET | R/W | 0 | 0=masked by default. Exists if IC_SLV_RESTART_DET_EN=1. |
| [13] | M_MASTER_ON_HOLD | R/W | 0 | 0=masked by default. Exists if IC_EMPTYFIFO_HOLD_MASTER_EN=1 AND I2C_DYNAMIC_TAR_UPDATE=1. |
| [14] | M_SCL_STUCK_AT_LOW | R/W | 0 | 0=masked by default. Exists if IC_BUS_CLEAR_FEATURE=1. |

> **Reset value 0x8FF:** bits [11,7:0] = 1, bits [14:12,10:8] = 0.

### 4.14 IC_RAW_INTR_STAT (0x34) -- Raw Interrupt Status

Read-only. Shows raw interrupt state before masking.

| Bits | Field | Access | Reset | Trigger Condition |
|------|-------|--------|-------|-------------------|
| [0] | RX_UNDER | R | 0 | Read IC_DATA_CMD when RX FIFO empty |
| [1] | RX_OVER | R | 0 | RX FIFO overflow (new data lost) |
| [2] | RX_FULL | R | 0 | RX FIFO level >= IC_RX_TL + 1 |
| [3] | TX_OVER | R | 0 | Write IC_DATA_CMD when TX FIFO full |
| [4] | TX_EMPTY | R | 0 | TX FIFO level <= IC_TX_TL (behavior depends on TX_EMPTY_CTRL) |
| [5] | RD_REQ | R | 0 | Slave-TX: master requests read, TX FIFO empty. Clock stretched. |
| [6] | TX_ABRT | R | 0 | Transfer abort. Check IC_TX_ABRT_SOURCE for cause. |
| [7] | RX_DONE | R | 0 | Slave-TX: master NACKs last byte (transfer complete) |
| [8] | ACTIVITY | R | 0 | Any I2C activity (transfer in progress) |
| [9] | STOP_DET | R | 0 | STOP condition detected. Behavior depends on STOP_DET_IFADDRESSED. |
| [10] | START_DET | R | 0 | START or RESTART condition detected |
| [11] | GEN_CALL | R | 0 | General Call address received and ACKed |
| [12] | RESTART_DET | R | 0 | RESTART detected in slave mode |
| [13] | MASTER_ON_HOLD | R | 0 | Master holding bus, TX FIFO empty (Mode 1 + dynamic TAR) |
| [14] | SCL_STUCK_AT_LOW | R | 0 | SCL stuck LOW beyond timeout |

### 4.15 IC_RX_TL (0x38) -- Receive FIFO Threshold Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | RX_TL | R/W | 0x00 | RX_FULL interrupt fires when RX FIFO level >= RX_TL+1. Range: 0 to IC_RX_BUFFER_DEPTH-1. Intel LPSS: 0 to 63. |

### 4.16 IC_TX_TL (0x3C) -- Transmit FIFO Threshold Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | TX_TL | R/W | 0x00 | TX_EMPTY interrupt fires when TX FIFO level <= TX_TL. Range: 0 to IC_TX_BUFFER_DEPTH-1. Intel LPSS: 0 to 63. |

### 4.17 IC_CLR_INTR (0x40) -- Clear Combined Interrupt

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | CLR_INTR | R | 0 | Read this register to clear ALL software-clearable I2C interrupts. |

> **Note:** This does NOT clear TX_ABRT source register. Use IC_CLR_TX_ABRT (0x54) for that.

### 4.18 Individual Interrupt Clear Registers (0x44-0x68)

All are read-to-clear. Reading bit [0] clears the corresponding interrupt.

| Offset | Register | Clears |
|--------|----------|--------|
| 0x44 | IC_CLR_RX_UNDER | RX_UNDER |
| 0x48 | IC_CLR_RX_OVER | RX_OVER |
| 0x4C | IC_CLR_TX_OVER | TX_OVER |
| 0x50 | IC_CLR_RD_REQ | RD_REQ |
| 0x54 | IC_CLR_TX_ABRT | TX_ABRT and IC_TX_ABRT_SOURCE |
| 0x58 | IC_CLR_RX_DONE | RX_DONE |
| 0x5C | IC_CLR_ACTIVITY | ACTIVITY |
| 0x60 | IC_CLR_STOP_DET | STOP_DET |
| 0x64 | IC_CLR_START_DET | START_DET |
| 0x68 | IC_CLR_GEN_CALL | GEN_CALL |
| 0xA8 | IC_CLR_RESTART_DET | RESTART_DET |
| 0xB4 | IC_CLR_SCL_STUCK_DET | SCL_STUCK_AT_LOW |

### 4.19 IC_ENABLE (0x6C) -- I2C Enable Register

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | ENABLE | R/W | 0 | 0=disable DW_apb_i2c; 1=enable. See disable sequence in Section 8. |
| [1] | ABORT | R/W | 0 | Write 1 to initiate transfer abort. Auto-clears to 0 after abort. TX FIFO flushed, TX_ABRT interrupt generated. |
| [2] | TX_CMD_BLOCK | R/W | 0 | 1=block transmission of commands from TX FIFO without aborting. |
| [3] | SDA_STUCK_RECOVERY_ENABLE | R/W | 0 | Write 1 to initiate SDA stuck recovery. Auto-clears to 0. Requires IC_CON[11]=1. |
| [16] | SMBUS_CLK_RESET | R/W | 0 | Write 1 to reset SMBus clock period timeout. Exists if IC_SMBUS=1. |
| [17] | SMBUS_SUSPEND_EN | R/W | 0 | 1=assert SMBSUS signal. Exists if IC_SMBUS_SUSPEND=1. |
| [18] | SMBUS_ALERT_EN | R/W | 0 | 1=assert SMBALERT. Auto-clears after master ACKs alert response. Exists if IC_SMBUS_SUSPEND=1. |

### 4.20 IC_STATUS (0x70) -- I2C Status Register

Read-only snapshot of controller state.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | ACTIVITY | R | 0 | 1=I2C activity present |
| [1] | TFNF | R | 1 | 1=TX FIFO not full (can accept data) |
| [2] | TFE | R | 1 | 1=TX FIFO completely empty |
| [3] | RFNE | R | 0 | 1=RX FIFO not empty (has data) |
| [4] | RFF | R | 0 | 1=RX FIFO completely full |
| [5] | MST_ACTIVITY | R | 0 | 1=master FSM is not IDLE |
| [6] | SLV_ACTIVITY | R | 0 | 1=slave FSM is not IDLE |
| [7] | MST_HOLD_TX_FIFO_EMPTY | R | 0 | 1=master holding bus because TX FIFO empty |
| [8] | MST_HOLD_RX_FIFO_FULL | R | 0 | 1=master holding bus because RX FIFO full |
| [9] | SLV_HOLD_TX_FIFO_EMPTY | R | 0 | 1=slave holding bus because TX FIFO empty |
| [10] | SLV_HOLD_RX_FIFO_FULL | R | 0 | 1=slave holding bus because RX FIFO full |
| [11] | SDA_STUCK_NOT_RECOVERED | R | 0 | 1=SDA recovery failed (9 clocks + STOP didn't work) |
| [16] | SMBUS_QUICK_CMD_BIT | R | 0 | R/W bit of received Quick command |
| [17] | SMBUS_SLAVE_ADDR_VALID | R | 0 | 1=slave address valid (assigned by ARP or IC_SAR) |
| [18] | SMBUS_SLAVE_ADDR_RESOLVED | R | 0 | 1=address resolved via ARP |
| [19] | SMBUS_SUSPEND_STATUS | R | 0 | SMBSUS input signal status |
| [20] | SMBUS_ALERT_STATUS | R | 0 | SMBALERT input signal status |

> **Reset value 0x6:** TFE=1 and TFNF=1 (TX FIFO starts empty).

### 4.21 IC_TXFLR (0x74) -- Transmit FIFO Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [6:0] | TXFLR | R | 0 | Current number of entries in TX FIFO. Range: 0 to IC_TX_BUFFER_DEPTH (64 on Intel LPSS). |

### 4.22 IC_RXFLR (0x78) -- Receive FIFO Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [6:0] | RXFLR | R | 0 | Current number of entries in RX FIFO. Range: 0 to IC_RX_BUFFER_DEPTH (64 on Intel LPSS). |

### 4.23 IC_SDA_HOLD (0x7C) -- SDA Hold Time

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | IC_SDA_TX_HOLD | R/W | IC_DEFAULT_SDA_HOLD | SDA hold time during transmit, in ic_clk periods. Min: 1 (master mode), IC_FS_SPKLEN+7 (slave mode). Max: must be < (N_SCL_LOW - 2) ic_clk periods. |
| [23:16] | IC_SDA_RX_HOLD | R/W | 0x00 | SDA hold time extension during receive. Extends time SDA is held after SCL goes HIGH. Max depends on speed mode (see Table 2-9 in databook). |

> **Intel LPSS:** SDA hold time impacts D0i2 wake latency. Larger hold values increase time for the controller to respond after exiting low-power state.

### 4.24 IC_TX_ABRT_SOURCE (0x80) -- Transmit Abort Source

Read-only. Cleared by reading IC_CLR_TX_ABRT (0x54).

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | ABRT_7B_ADDR_NOACK | R | 0 | 7-bit address sent, slave did not ACK |
| [1] | ABRT_10ADDR1_NOACK | R | 0 | 10-bit address byte 1 (11110XX0) not ACKed |
| [2] | ABRT_10ADDR2_NOACK | R | 0 | 10-bit address byte 2 (A[7:0]) not ACKed |
| [3] | ABRT_TXDATA_NOACK | R | 0 | Data byte not ACKed by slave |
| [4] | ABRT_GCALL_NOACK | R | 0 | General Call sent, no slave ACKed |
| [5] | ABRT_GCALL_READ | R | 0 | General Call followed by read (invalid) |
| [6] | ABRT_HS_ACKDET | R | 0 | HS master code was ACKed (protocol violation) |
| [7] | ABRT_SBYTE_ACKDET | R | 0 | START byte was ACKed (protocol violation) |
| [8] | ABRT_HS_NORSTRT | R | 0 | HS mode attempted with IC_RESTART_EN=0 |
| [9] | ABRT_SBYTE_NORSTRT | R | 0 | START byte attempted with IC_RESTART_EN=0. Special clearing: read IC_CLR_TX_ABRT, then toggle IC_ENABLE[0]. |
| [10] | ABRT_10B_RD_NORSTRT | R | 0 | 10-bit read attempted with IC_RESTART_EN=0 |
| [11] | ABRT_MASTER_DIS | R | 0 | Master operation attempted with MASTER_MODE=0 |
| [12] | ARB_LOST | R | 0 | Arbitration lost to another master |
| [13] | ABRT_SLVFLUSH_TXFIFO | R | 0 | Slave received RD_REQ but TX FIFO had leftover data (flushed) |
| [14] | ABRT_SLV_ARBLOST | R | 0 | Slave-transmitter lost arbitration |
| [15] | ABRT_SLVRD_INTX | R | 0 | Slave-TX mode received write command from master |
| [16] | ABRT_USER_ABRT | R | 0 | User initiated abort via IC_ENABLE[1] |
| [17] | ABRT_SDA_STUCK_AT_LOW | R | 0 | SDA stuck LOW detected |
| [18] | ABRT_DEVICE_NOACK | R | 0 | Device ID address (0x7C) not ACKed |
| [19] | ABRT_DEVICE_SLVADDR_NOACK | R | 0 | Device ID: slave address in IC_TAR not ACKed |
| [20] | ABRT_DEVICE_WRITE | R | 0 | Device ID transfer attempted with write commands in TX FIFO |
| [31:23] | TX_FLUSH_CNT | R | 0 | Number of TX FIFO entries flushed due to abort |

### 4.25 IC_SLV_DATA_NACK_ONLY (0x84) -- Slave Data NACK Only

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | NACK | R/W | 0 | 1=generate NACK after receiving data in slave-RX mode (data byte, not address). |

### 4.26 IC_DMA_CR (0x88) -- DMA Control Register

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | RDMAE | R/W | 0 | 1=enable receive DMA. RX FIFO drives dma_rx_req/dma_rx_single. |
| [1] | TDMAE | R/W | 0 | 1=enable transmit DMA. TX FIFO drives dma_tx_req/dma_tx_single. |

> **Intel LPSS:** Only accessible on I2C0-3 (IC_HAS_DMA=1). I2C4-5 have IC_HAS_DMA=0.

### 4.27 IC_DMA_TDLR (0x8C) -- DMA Transmit Data Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [5:0] | DMATDL | R/W | 0x00 | TX DMA watermark. dma_tx_req asserted when TX FIFO level <= DMATDL. Range: 0 to IC_TX_BUFFER_DEPTH-1 (0-63 on Intel LPSS). |

### 4.28 IC_DMA_RDLR (0x90) -- DMA Receive Data Level

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [5:0] | DMARDL | R/W | 0x00 | RX DMA watermark. dma_rx_req asserted when RX FIFO level >= DMARDL+1. Range: 0 to IC_RX_BUFFER_DEPTH-1 (0-63 on Intel LPSS). |

### 4.29 IC_SDA_SETUP (0x94) -- SDA Setup Time

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | SDA_SETUP | R/W | 0x64 | SDA setup time in ic_clk periods. Time between SDA data and SCL rising edge. Minimum value: 2. |

### 4.30 IC_ACK_GENERAL_CALL (0x98) -- ACK General Call

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | ACK_GEN_CALL | R/W | 1 | 1=ACK General Call address (0x00); 0=NACK. |

### 4.31 IC_ENABLE_STATUS (0x9C) -- Enable Status

Read-only. Used to confirm enable/disable transitions.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | IC_EN | R | 0 | 1=DW_apb_i2c is enabled and active |
| [1] | SLV_DISABLED_WHILE_BUSY | R | 0 | 1=slave disabled while transfer was active (data may be lost) |
| [2] | SLV_RX_DATA_LOST | R | 0 | 1=slave RX data was lost during disable |

### 4.32 IC_FS_SPKLEN (0xA0) -- FS/SS/FM+ Spike Suppression Length

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | IC_FS_SPKLEN | R/W | IC_DEFAULT_FS_SPKLEN | Spike suppression length for SS/FS/FM+ modes, in ic_clk periods. Min: 1. Max: IC_FS_MAX_SPKLEN (50). |

> When IC_UFM_EN=1, this register is repurposed as IC_UFM_SPKLEN. Min: 1, Max: IC_FS_MAX_SPKLEN (50).

### 4.33 IC_HS_SPKLEN (0xA4) -- HS Spike Suppression Length

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [7:0] | IC_HS_SPKLEN | R/W | IC_DEFAULT_HS_SPKLEN | Spike suppression length for HS mode, in ic_clk periods. Min: 1. Max: IC_HS_MAX_SPKLEN (10). |

### 4.34 IC_SCL_STUCK_AT_LOW_TIMEOUT (0xAC)

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | IC_SCL_STUCK_LOW_TIMEOUT | R/W | config | Timeout count in ic_clk periods. When SCL stays LOW for this duration, SCL_STUCK_AT_LOW interrupt fires. Exists if IC_BUS_CLEAR_FEATURE=1. |

### 4.35 IC_SDA_STUCK_AT_LOW_TIMEOUT (0xB0)

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | IC_SDA_STUCK_LOW_TIMEOUT | R/W | config | Timeout count in ic_clk periods. After timeout, SDA recovery can be initiated. Exists if IC_BUS_CLEAR_FEATURE=1. |

### 4.36 IC_DEVICE_ID (0xB8) -- Device ID Register

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [23:0] | DEVICE_ID | R | 0x000000 | 24-bit Device ID read from slave. [23:12]=manufacturer (12-bit), [11:3]=part ID (9-bit), [2:0]=revision (3-bit). |

### 4.37 SMBus Timeout Registers

#### IC_SMBUS_CLK_LOW_SEXT (0xBC)

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | SMBUS_CLK_LOW_SEXT_TIMEOUT | R/W | config | Slave clock extend timeout in ic_clk periods. Per SMBus spec: 25ms max. |

#### IC_SMBUS_CLK_LOW_MEXT (0xC0)

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | SMBUS_CLK_LOW_MEXT_TIMEOUT | R/W | config | Master clock extend timeout in ic_clk periods. Per SMBus spec: 10ms max. |

#### IC_SMBUS_THIGH_MAX_IDLE_COUNT (0xC4)

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [15:0] | SMBUS_THIGH_MAX_BUS_IDLE_CNT | R/W | config | Bus idle detection count. Used for tHIGH:MAX (50us) per SMBus spec. |

### 4.38 SMBus Interrupt Registers

#### IC_SMBUS_INTR_STAT (0xC8) -- Masked

#### IC_SMBUS_INTR_MASK (0xCC)

#### IC_SMBUS_RAW_INTR_STAT (0xD0)

All three share the same bit layout:

| Bits | Field | Description |
|------|-------|-------------|
| [0] | SLV_CLOCK_EXTND_TIMEOUT | Slave clock extend timeout exceeded |
| [1] | MST_CLOCK_EXTND_TIMEOUT | Master clock extend timeout exceeded |
| [2] | QUICK_CMD_DET | Quick command detected (slave mode) |
| [3] | HOST_NOTIFY_MST_DET | Host Notify received (master mode) |
| [4] | ARP_PREPARE_CMD_DET | ARP Prepare command detected |
| [5] | ARP_RST_CMD_DET | ARP Reset command detected |
| [6] | ARP_GET_UDID_CMD_DET | ARP Get UDID command detected |
| [7] | ARP_ASSGN_ADDR_CMD_DET | ARP Assign Address command detected |
| [8] | SLV_RX_PEC_NACK | PEC byte NACKed in slave mode |
| [9] | SMBUS_SUSPEND_DET | SMBSUS signal asserted |
| [10] | SMBUS_ALERT_DET | SMBALERT signal asserted |

#### IC_CLR_SMBUS_INTR (0xD4) -- Write-1-to-Clear

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [10:0] | CLR_SMBUS_INTR | W1C | Write 1 to corresponding bit to clear that SMBus interrupt. |

> **Important:** SMBus interrupts use write-1-to-clear (W1C), unlike I2C interrupts which use read-to-clear.

### 4.39 IC_OPTIONAL_SAR (0xD8) -- Optional Slave Address

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [6:0] | IC_OPTIONAL_SAR | R/W | 0x00 | Additional 7-bit slave address. Active when IC_CON[16]=1. |

### 4.40 SMBus UDID Registers

128-bit Unique Device Identifier stored across 4 registers:

| Offset | Register | Bits | Description |
|--------|----------|------|-------------|
| 0xDC | IC_SMBUS_UDID_LSB (Word0) | [31:0] | UDID bits [31:0] (LSB) |
| 0xE0 | IC_SMBUS_UDID_WORD1 | [31:0] | UDID bits [63:32] |
| 0xE4 | IC_SMBUS_UDID_WORD2 | [31:0] | UDID bits [95:64] |
| 0xE8 | IC_SMBUS_UDID_WORD3 | [31:0] | UDID bits [127:96] (MSB) |

### 4.41 REG_TIMEOUT_RST (0xF0) -- Register Timeout Counter Reset

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [3:0] | REG_TIMEOUT_RST_VAL | R/W | config | Timeout counter reset value for register access timeout. |

### 4.42 IC_COMP_PARAM_1 (0xF4) -- Component Parameter 1

Read-only. Encodes hardware configuration.

| Bits | Field | Access | Value | Description |
|------|-------|--------|-------|-------------|
| [1:0] | APB_DATA_WIDTH | R | 2 | 0=8-bit, 1=16-bit, 2=32-bit APB data width |
| [3:2] | MAX_SPEED_MODE | R | varies | 1=SS only, 2=FS, 3=HS (encodes IC_MAX_SPEED_MODE) |
| [4] | HC_COUNT_VALUES | R | varies | 1=HCNT/LCNT are hardcoded (read-only) |
| [5] | INTR_IO | R | varies | 0=individual interrupt outputs, 1=combined interrupt |
| [6] | HAS_DMA | R | varies | 1=DMA interface present |
| [7] | ADD_ENCODED_PARAMS | R | 1 | 1=this register contains valid encoded params |
| [15:8] | RX_BUFFER_DEPTH | R | varies | RX FIFO depth encoded (0x3F=64 on Intel LPSS) |
| [23:16] | TX_BUFFER_DEPTH | R | varies | TX FIFO depth encoded (0x3F=64 on Intel LPSS) |

> **Intel LPSS validation:** Read IC_COMP_PARAM_1 to verify FIFO depth, DMA presence, and speed mode configuration match expectations.

### 4.43 IC_COMP_VERSION (0xF8) -- Component Version

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | IC_COMP_VERSION | R | 0x3230322A | ASCII "202*" = version 2.02a. Intel LPSS IP may read as v2.00a equivalent. |

### 4.44 IC_COMP_TYPE (0xFC) -- Component Type

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [31:0] | IC_COMP_TYPE | R | 0x44570140 | ASCII "DW" + 0x0140. Identifies this as a DesignWare component. |

---

## 5. TX FIFO Management

### 5.1 Mode 0 vs Mode 1

| Feature | Mode 0 (EMPTYFIFO_HOLD=0) | Mode 1 (EMPTYFIFO_HOLD=1) |
|---------|--------------------------|--------------------------|
| STOP generation | Automatic when TX FIFO empties | Explicit via IC_DATA_CMD[9] STOP bit |
| RESTART control | Automatic | Explicit via IC_DATA_CMD[10] RESTART bit |
| SCL behavior on empty FIFO | Issues STOP | Holds SCL LOW (clock stretch) |
| Target address change | Must disable to change | Can change mid-stream (if DYNAMIC_TAR_UPDATE=1) |
| Risk of premature STOP | Yes, if software too slow | No, but risk of bus hang if STOP forgotten |
| Intel LPSS | Not used | **Used (IC_EMPTYFIFO_HOLD_MASTER_EN=1)** |

### 5.2 IC_DATA_CMD Usage in Mode 1

```
Write byte:   IC_DATA_CMD = {RESTART, STOP, CMD=0, DAT[7:0]}
Read request:  IC_DATA_CMD = {RESTART, STOP, CMD=1, DAT=don't care}
```

**Transfer termination examples:**

| Operation | IC_DATA_CMD Value | Notes |
|-----------|------------------|-------|
| Write byte, continue | {0, 0, 0, data} | No STOP, no RESTART |
| Write last byte, stop | {0, 1, 0, data} | STOP after this byte |
| Read request, continue | {0, 0, 1, 0x00} | Read, no STOP |
| Read last byte, stop | {0, 1, 1, 0x00} | Read then STOP |
| Write with RESTART | {1, 0, 0, data} | RESTART before this byte |
| Combined W+R (RESTART) | {1, 0, 1, 0x00} | RESTART then read |

### 5.3 TX_EMPTY Interrupt Behavior

With **TX_EMPTY_CTRL=0** (IC_CON[8]=0): TX_EMPTY fires whenever TX FIFO level <= IC_TX_TL, regardless of transfer state. Can fire during idle.

With **TX_EMPTY_CTRL=1** (IC_CON[8]=1): TX_EMPTY fires only when TX FIFO level <= IC_TX_TL AND a transfer is actively in progress. Prevents spurious interrupts during idle.

> **Intel LPSS recommendation:** Set TX_EMPTY_CTRL=1 for master mode to avoid spurious interrupts.

---

## 6. Master Mode Programming

### 6.1 Initialization Sequence

1. **Disable controller:** `IC_ENABLE[0] = 0`; poll `IC_ENABLE_STATUS[0]` until 0
2. **Configure IC_CON:**
   - MASTER_MODE = 1
   - SPEED = desired mode (1=SS, 2=FS/FM+, 3=HS)
   - IC_RESTART_EN = 1 (recommended)
   - IC_SLAVE_DISABLE = 1
   - TX_EMPTY_CTRL = 1
3. **Set target address:** Write IC_TAR[9:0] (7-bit: bits [6:0])
4. **Set SCL timing:** Program appropriate HCNT/LCNT pair for selected speed mode
5. **Set SDA timing:** Program IC_SDA_HOLD and IC_SDA_SETUP
6. **Set spike suppression:** Program IC_FS_SPKLEN (and IC_HS_SPKLEN for HS)
7. **Set FIFO thresholds:** Write IC_RX_TL and IC_TX_TL
8. **Configure interrupts:** Write IC_INTR_MASK
9. **Enable controller:** `IC_ENABLE[0] = 1`

> **PythonSV example (NVL):**
> ```python
> i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg
> i2c.IC_ENABLE.write(0x0)                # Disable
> i2c.IC_CON.write(0x65)                  # Master, FS, restart, slave-disable
> i2c.IC_TAR.write(0x50)                  # Target address 0x50
> i2c.IC_FS_SCL_HCNT.write(0x3C)         # FS high count
> i2c.IC_FS_SCL_LCNT.write(0x82)         # FS low count
> i2c.IC_ENABLE.write(0x1)                # Enable
> ```

### 6.2 Master-Transmitter Flow

1. Initialize as above
2. Write data bytes to IC_DATA_CMD with CMD=0 (write)
3. Set STOP=1 on the last byte (Mode 1)
4. Monitor TX_EMPTY/TX_ABRT interrupts

```
IC_DATA_CMD = 0x0XX  (write byte, continue)
IC_DATA_CMD = 0x2XX  (write last byte, STOP)
```

### 6.3 Master-Receiver Flow

1. Initialize as above
2. Write read commands to IC_DATA_CMD with CMD=1
3. Set STOP=1 on the last read command
4. Read received data from IC_DATA_CMD when RX_FULL fires

```
IC_DATA_CMD = 0x100  (read request, continue)
IC_DATA_CMD = 0x300  (read request, STOP)
```
Then read IC_DATA_CMD[7:0] for each received byte.

### 6.4 Combined Format (Write-then-Read)

1. Write data bytes with CMD=0
2. Issue RESTART + read commands:
   ```
   IC_DATA_CMD = 0x500  (RESTART + read request)
   IC_DATA_CMD = 0x300  (last read + STOP)
   ```

### 6.5 Dynamic TAR Update

When I2C_DYNAMIC_TAR_UPDATE=1:
1. Enable MASTER_ON_HOLD interrupt (IC_INTR_MASK[13]=1)
2. Write first transfer commands
3. On MASTER_ON_HOLD (TX FIFO empty, bus held):
   - Update IC_TAR to new target address
   - Write next transfer commands (RESTART will be automatic if TAR changed)

### 6.6 Static TAR Update

When I2C_DYNAMIC_TAR_UPDATE=0:
1. Complete current transfer (STOP)
2. Disable: IC_ENABLE[0]=0, poll IC_ENABLE_STATUS[0]=0
3. Write new IC_TAR
4. Re-enable: IC_ENABLE[0]=1

---

## 7. Slave Mode Programming

### 7.1 Initialization

1. **Disable controller:** `IC_ENABLE[0] = 0`
2. **Configure IC_CON:**
   - MASTER_MODE = 0
   - IC_SLAVE_DISABLE = 0
   - IC_10BITADDR_SLAVE = 0 or 1
   - STOP_DET_IFADDRESSED = 1 (recommended)
   - RX_FIFO_FULL_HLD_CTRL = 1 (recommended, prevents RX overflow)
3. **Set slave address:** Write IC_SAR[9:0]
4. **Set FIFO thresholds:** IC_RX_TL, IC_TX_TL
5. **Unmask interrupts:** RD_REQ, RX_FULL, TX_ABRT, STOP_DET (minimum)
6. **Enable:** `IC_ENABLE[0] = 1`

### 7.2 Slave-Transmitter (Master Reads from Slave)

1. Master sends read request to slave address
2. **RD_REQ** interrupt fires -> slave must write data to IC_DATA_CMD
3. Hardware stretches SCL LOW until data is available
4. Continue writing data on each RD_REQ
5. **RX_DONE** fires when master NACKs the last byte (end of read)

```
ISR for RD_REQ:
  Read IC_CLR_RD_REQ      // Clear interrupt
  Write IC_DATA_CMD = data // Provide data byte
```

### 7.3 Slave-Receiver (Master Writes to Slave)

1. Master sends write to slave address
2. **RX_FULL** interrupt fires when RX FIFO reaches threshold
3. Read IC_DATA_CMD[7:0] for received data
4. If RX_FIFO_FULL_HLD_CTRL=1, SCL stretches when FIFO is full

```
ISR for RX_FULL:
  data = Read IC_DATA_CMD[7:0]  // Pop received byte
```

### 7.4 Clock Stretching Behavior

| Scenario | SCL Stretched | Condition |
|----------|--------------|-----------|
| Slave-TX, TX FIFO empty | Yes | Always (waiting for RD_REQ handler) |
| Slave-RX, RX FIFO full | Yes | Only if RX_FIFO_FULL_HLD_CTRL=1 |
| Slave-RX, RX FIFO full | No (overflow) | If RX_FIFO_FULL_HLD_CTRL=0 |

### 7.5 General Call Handling

- IC_ACK_GENERAL_CALL=1: slave ACKs General Call, GEN_CALL interrupt fires
- IC_ACK_GENERAL_CALL=0: slave NACKs General Call
- Check FIRST_DATA_BYTE (IC_DATA_CMD[11]) to identify the first byte after address

### 7.6 Bulk Transfer Mode

In slave-receiver mode, when receiving large data blocks, the RX FIFO fills and (with RX_FIFO_FULL_HLD_CTRL=1) the bus is held until software drains the FIFO. This enables reliable bulk reception without data loss.

### 7.7 IC_SLV_DATA_NACK_ONLY

Setting IC_SLV_DATA_NACK_ONLY[0]=1 causes the slave to NACK data bytes (not address bytes) from the master. Useful for testing or when the slave cannot accept data.

### 7.8 Optional Slave Address

When IC_CON[16] OPTIONAL_SAR_CTRL=1, the slave responds to both IC_SAR and IC_OPTIONAL_SAR addresses. The controller can distinguish which address was matched.

---

## 8. Abort and Disable Mechanism

### 8.1 Transfer Abort

**Via IC_ENABLE[1] (ABORT bit):**
1. Write `IC_ENABLE = (current value) | 0x2` (set ABORT=1, keep ENABLE=1)
2. Hardware completes current byte on bus, issues STOP
3. TX FIFO is flushed (count in IC_TX_ABRT_SOURCE[31:23])
4. TX_ABRT interrupt fires with ABRT_USER_ABRT (bit 16)
5. ABORT bit auto-clears to 0
6. **Must read IC_CLR_TX_ABRT before starting next transfer**

### 8.2 Controller Disable

1. Write `IC_ENABLE[0] = 0`
2. Poll `IC_ENABLE_STATUS[0]` until it reads 0
3. Check `IC_ENABLE_STATUS[1]` (SLV_DISABLED_WHILE_BUSY) for active transfer warning
4. Check `IC_ENABLE_STATUS[2]` (SLV_RX_DATA_LOST) for slave data loss
5. Controller completes current transfer before fully disabling

> **Warning:** Do not assume disable is instant. The controller waits for the current byte to complete on the bus. Always poll IC_ENABLE_STATUS.

### 8.3 TX Command Block

IC_ENABLE[2] TX_CMD_BLOCK:
- Setting to 1 prevents new commands from leaving the TX FIFO to the bus
- Does NOT abort the current transfer
- Does NOT flush the TX FIFO
- Useful for temporarily pausing transmission

---

## 9. Error Handling

### 9.1 Complete Abort Source Reference

| Bit | Source | Role | Cause | Recovery Action |
|-----|--------|------|-------|-----------------|
| [0] | ABRT_7B_ADDR_NOACK | Master | 7-bit address NACK | Verify slave present, retry |
| [1] | ABRT_10ADDR1_NOACK | Master | 10-bit addr byte 1 NACK | Verify slave, check addressing mode |
| [2] | ABRT_10ADDR2_NOACK | Master | 10-bit addr byte 2 NACK | Verify slave, check address value |
| [3] | ABRT_TXDATA_NOACK | Master | Data byte NACK | Slave not ready or buffer full |
| [4] | ABRT_GCALL_NOACK | Master | General Call no ACK | No slaves support General Call |
| [5] | ABRT_GCALL_READ | Master | GC + read (invalid) | Software bug: GC is write-only |
| [6] | ABRT_HS_ACKDET | Master | HS master code ACKed | Unexpected: no slave should ACK |
| [7] | ABRT_SBYTE_ACKDET | Master | START byte ACKed | Protocol violation on bus |
| [8] | ABRT_HS_NORSTRT | Master | HS without RESTART | Set IC_RESTART_EN=1 |
| [9] | ABRT_SBYTE_NORSTRT | Master | START byte without RESTART | Set IC_RESTART_EN=1. Special: clear TX_ABRT then toggle IC_ENABLE |
| [10] | ABRT_10B_RD_NORSTRT | Master | 10-bit read without RESTART | Set IC_RESTART_EN=1 |
| [11] | ABRT_MASTER_DIS | Any | Master op, master disabled | Set MASTER_MODE=1 |
| [12] | ARB_LOST | Master | Lost arbitration | Retry transfer (another master won) |
| [13] | ABRT_SLVFLUSH_TXFIFO | Slave | TX data in FIFO on RD_REQ | Clear TX FIFO before slave-TX |
| [14] | ABRT_SLV_ARBLOST | Slave | Slave-TX arbitration loss | Multi-master: data collision |
| [15] | ABRT_SLVRD_INTX | Slave | Write cmd in slave-TX | Software sent write in slave-TX mode |
| [16] | ABRT_USER_ABRT | Any | User abort via IC_ENABLE[1] | Expected abort, no error |
| [17] | ABRT_SDA_STUCK_AT_LOW | Any | SDA stuck LOW | Bus recovery (Section 15) |
| [18] | ABRT_DEVICE_NOACK | Master | Device ID addr NACK | No device supports Device ID |
| [19] | ABRT_DEVICE_SLVADDR_NOACK | Master | Device ID slave NACK | Slave not present at IC_TAR |
| [20] | ABRT_DEVICE_WRITE | Master | Device ID with writes | Software bug: only reads allowed |

### 9.2 Arbitration Loss

In multi-master systems, arbitration is performed bit-by-bit on SDA:
- Master driving SDA HIGH while another drives LOW loses arbitration
- ARB_LOST (bit 12) is set
- Controller releases bus and generates TX_ABRT
- Software should retry the transfer after a delay

### 9.3 SDA/SCL Stuck Detection

**SDA stuck LOW:**
- IC_TX_ABRT_SOURCE[17] indicates SDA stuck
- Recovery via IC_ENABLE[3] (sends 9 SCL clocks + STOP)
- See Section 15 for full procedure

**SCL stuck LOW:**
- Detected by IC_SCL_STUCK_AT_LOW_TIMEOUT register
- SCL_STUCK_AT_LOW interrupt (bit 14) fires
- Cannot be recovered in-band -- requires hardware reset

---

## 10. DMA Interface

### 10.1 DMA Signal Handshaking

| Signal | Direction | Description |
|--------|-----------|-------------|
| dma_tx_req | Output | TX burst DMA request |
| dma_tx_single | Output | TX single DMA request |
| dma_tx_ack | Input | TX DMA acknowledge |
| dma_rx_req | Output | RX burst DMA request |
| dma_rx_single | Output | RX single DMA request |
| dma_rx_ack | Input | RX DMA acknowledge |

### 10.2 TX DMA Watermark

- dma_tx_req asserted when TX FIFO level <= IC_DMA_TDLR
- dma_tx_single asserted when TX FIFO level = IC_DMA_TDLR
- Optimal DMA burst size: `DMA.CTLx.DEST_MSIZE = IC_TX_BUFFER_DEPTH - IC_DMA_TDLR`

### 10.3 RX DMA Watermark

- dma_rx_req asserted when RX FIFO level >= IC_DMA_RDLR + 1
- dma_rx_single asserted when RX FIFO level = IC_DMA_RDLR + 1
- Optimal DMA burst size: `DMA.CTLx.SRC_MSIZE = IC_DMA_RDLR + 1`

### 10.4 DMA Configuration Table

| Parameter | Register | Recommended Value | Description |
|-----------|----------|-------------------|-------------|
| TX DMA enable | IC_DMA_CR[1] | 1 | Enable TX DMA |
| RX DMA enable | IC_DMA_CR[0] | 1 | Enable RX DMA |
| TX watermark | IC_DMA_TDLR | Application-specific | TX request threshold |
| RX watermark | IC_DMA_RDLR | Application-specific | RX request threshold |
| DMA TX burst | DMA controller | FIFO_DEPTH - TDLR | Optimal burst |
| DMA RX burst | DMA controller | RDLR + 1 | Optimal burst |

### 10.5 Clock Constraints

- hclk and pclk must be phase-aligned
- hclk frequency must be an integer multiple of pclk frequency
- Failure to meet these constraints causes DMA handshaking errors

### 10.6 Intel LPSS DMA Instance Mapping

| Instance | IC_HAS_DMA | DMA Capable | Access Method |
|----------|-----------|-------------|---------------|
| I2C0 | 1 | Yes | DMA or PIO |
| I2C1 | 1 | Yes | DMA or PIO |
| I2C2 | 1 | Yes | DMA or PIO |
| I2C3 | 1 | Yes | DMA or PIO |
| I2C4 | 0 | No | PIO only |
| I2C5 | 0 | No | PIO only |

> **Intel LPSS:** On I2C4-5, IC_DMA_CR/IC_DMA_TDLR/IC_DMA_RDLR registers may not exist or return 0.

---

## 11. Interrupt System

### 11.1 I2C Interrupt Sources (15 interrupts)

| Bit | Name | Trigger Condition | Clear Method | Default Mask | Notes |
|-----|------|-------------------|-------------|-------------|-------|
| [0] | RX_UNDER | Read IC_DATA_CMD when RX FIFO empty | Read IC_CLR_RX_UNDER | 1 (unmasked) | Software error |
| [1] | RX_OVER | Data received but RX FIFO full | Read IC_CLR_RX_OVER | 1 (unmasked) | New data lost |
| [2] | RX_FULL | RX FIFO level >= IC_RX_TL + 1 | Read IC_DATA_CMD (drain FIFO) | 1 (unmasked) | Level-sensitive |
| [3] | TX_OVER | Write IC_DATA_CMD when TX FIFO full | Read IC_CLR_TX_OVER | 1 (unmasked) | Data not written |
| [4] | TX_EMPTY | TX FIFO level <= IC_TX_TL | Write IC_DATA_CMD (fill FIFO) | 1 (unmasked) | See TX_EMPTY_CTRL |
| [5] | RD_REQ | Slave-TX: master reads, TX FIFO empty | Read IC_CLR_RD_REQ | 1 (unmasked) | SCL stretched |
| [6] | TX_ABRT | Transfer aborted | Read IC_CLR_TX_ABRT | 1 (unmasked) | Check ABRT_SOURCE |
| [7] | RX_DONE | Slave-TX: master NACKs last byte | Read IC_CLR_RX_DONE | 1 (unmasked) | Transfer complete |
| [8] | ACTIVITY | Any I2C bus activity | Read IC_CLR_ACTIVITY | 0 (masked) | |
| [9] | STOP_DET | STOP condition on bus | Read IC_CLR_STOP_DET | 0 (masked) | See STOP_DET_IF* |
| [10] | START_DET | START or RESTART on bus | Read IC_CLR_START_DET | 0 (masked) | |
| [11] | GEN_CALL | General Call received and ACKed | Read IC_CLR_GEN_CALL | 1 (unmasked) | Slave mode |
| [12] | RESTART_DET | RESTART in slave mode | Read IC_CLR_RESTART_DET | 0 (masked) | If SLV_RESTART_DET_EN |
| [13] | MASTER_ON_HOLD | Master holding, TX empty | Write IC_DATA_CMD | 0 (masked) | Mode 1 + DynTAR |
| [14] | SCL_STUCK_AT_LOW | SCL stuck timeout | Read IC_CLR_SCL_STUCK_DET | 0 (masked) | If BUS_CLEAR_FEATURE |

### 11.2 SMBus Interrupt Sources (11 interrupts)

| Bit | Name | Trigger Condition | Clear Method |
|-----|------|-------------------|-------------|
| [0] | SLV_CLOCK_EXTND_TIMEOUT | Slave held SCL LOW beyond SEXT timeout | W1C via IC_CLR_SMBUS_INTR[0] |
| [1] | MST_CLOCK_EXTND_TIMEOUT | Master held SCL LOW beyond MEXT timeout | W1C via IC_CLR_SMBUS_INTR[1] |
| [2] | QUICK_CMD_DET | Quick command received in slave mode | W1C via IC_CLR_SMBUS_INTR[2] |
| [3] | HOST_NOTIFY_MST_DET | Host Notify command received in master mode | W1C via IC_CLR_SMBUS_INTR[3] |
| [4] | ARP_PREPARE_CMD_DET | ARP Prepare to ARP command received | W1C via IC_CLR_SMBUS_INTR[4] |
| [5] | ARP_RST_CMD_DET | ARP Reset Device (general/directed) received | W1C via IC_CLR_SMBUS_INTR[5] |
| [6] | ARP_GET_UDID_CMD_DET | ARP Get UDID (general/directed) received | W1C via IC_CLR_SMBUS_INTR[6] |
| [7] | ARP_ASSGN_ADDR_CMD_DET | ARP Assign Address received | W1C via IC_CLR_SMBUS_INTR[7] |
| [8] | SLV_RX_PEC_NACK | Slave NACKed received PEC byte | W1C via IC_CLR_SMBUS_INTR[8] |
| [9] | SMBUS_SUSPEND_DET | SMBSUS signal asserted by remote | W1C via IC_CLR_SMBUS_INTR[9] |
| [10] | SMBUS_ALERT_DET | SMBALERT signal asserted by remote | W1C via IC_CLR_SMBUS_INTR[10] |

### 11.3 Interrupt Architecture

```
IC_RAW_INTR_STAT[n] & IC_INTR_MASK[n] -> IC_INTR_STAT[n]
                                            |
All IC_INTR_STAT bits OR'd -> combined interrupt output
```

- **Combined interrupt:** Single output for all I2C interrupts (when IC_INTR_IO=1)
- **Individual interrupts:** Separate output per source (when IC_INTR_IO=0)
- **IC_CLR_INTR (0x40):** Clears ALL software-clearable I2C interrupts in one read

### 11.4 Interrupt Handling Best Practices

1. Read IC_INTR_STAT to determine which interrupts fired
2. Handle each interrupt source
3. Clear interrupts via individual IC_CLR_* registers
4. For TX_ABRT: always read IC_TX_ABRT_SOURCE BEFORE reading IC_CLR_TX_ABRT (clearing also clears source)
5. For RX_FULL: drain RX FIFO to below threshold to deassert
6. For TX_EMPTY: fill TX FIFO to above threshold to deassert

---

## 12. Clock Configuration

### 12.1 SCL Timing Formulas

#### When IC_CLK_FREQ_OPTIMIZATION = 0 (default):

```
SCL_High_Period = (HCNT + IC_*_SPKLEN + 7) x t_ic_clk + t_SCL_Fall
SCL_Low_Period  = (LCNT + 1) x t_ic_clk - t_SCL_Fall + t_SCL_Rise
```

**Minimum count values:**
| Register | Minimum Value |
|----------|--------------|
| HCNT | IC_*_SPKLEN + 5 |
| LCNT | IC_*_SPKLEN + 7 |

#### When IC_CLK_FREQ_OPTIMIZATION = 1:

```
SCL_High_Period = (HCNT + IC_*_SPKLEN + 3) x t_ic_clk + t_SCL_Fall
SCL_Low_Period  = LCNT x t_ic_clk - t_SCL_Fall + t_SCL_Rise
```

**Minimum count values:**
| Register | Minimum Value |
|----------|--------------|
| HCNT | 1 |
| LCNT | 6 |

#### UFM Mode:

```
SCL_High_Period = HCNT x t_ic_clk
SCL_Low_Period  = LCNT x t_ic_clk
```

**Minimum count values:** HCNT >= 3, LCNT >= 5.

### 12.2 Minimum ic_clk Frequencies

| Speed Mode | Min ic_clk (FREQ_OPT=0) | Notes |
|-----------|-------------------------|-------|
| SS (100 kHz) | 2.7 MHz | |
| FS (400 kHz) | 12 MHz | |
| FM+ (1 MHz) | 32 MHz | |
| HS (3.4 MHz, Cb=400pF) | 51 MHz | Higher bus capacitance |
| HS (3.4 MHz, Cb=100pF) | 105.4 MHz | Lower bus capacitance |

### 12.3 I2C Spec Timing Requirements

| Parameter | SS | FS | FM+ | HS (400pF) | HS (100pF) |
|-----------|----|----|-----|-----------|-----------|
| SCL HIGH min | 4.0 us | 0.6 us | 0.26 us | 0.06 us | 0.06 us |
| SCL LOW min | 4.7 us | 1.3 us | 0.5 us | 0.16 us | 0.16 us |
| SDA hold min | 0 | 0 | 0 | 0 | 0 |
| SDA setup min | 250 ns | 100 ns | 50 ns | 10 ns | 10 ns |
| Rise time max | 1000 ns | 300 ns | 120 ns | 80 ns | 40 ns |
| Fall time max | 300 ns | 300 ns | 120 ns | 80 ns | 40 ns |

### 12.4 Worked Example: 400 kHz FS at 100 MHz ic_clk

Given: ic_clk = 100 MHz (t_ic_clk = 10 ns), IC_FS_SPKLEN = 5, FREQ_OPT = 0

**Target:** SCL_High >= 0.6 us, SCL_Low >= 1.3 us

**HCNT calculation (SCL HIGH):**
```
SCL_High = (HCNT + 5 + 7) x 10ns + t_fall
0.6us = (HCNT + 12) x 10ns + 20ns   (assume t_fall = 20ns)
580ns = (HCNT + 12) x 10ns
HCNT = 46                            (minimum)
```

**LCNT calculation (SCL LOW):**
```
SCL_Low = (LCNT + 1) x 10ns - t_fall + t_rise
1.3us = (LCNT + 1) x 10ns - 20ns + 50ns  (assume t_rise = 50ns)
1270ns = (LCNT + 1) x 10ns
LCNT = 126                           (minimum)
```

**Verify minimums:** HCNT >= SPKLEN+5 = 10 (46 > 10, OK); LCNT >= SPKLEN+7 = 12 (126 > 12, OK).

---

## 13. Spike Suppression

### 13.1 Overview

The DW_apb_i2c includes spike suppression filters on both SDA and SCL inputs. Any pulse shorter than the configured spike length is filtered out.

### 13.2 Spike Suppression Registers

| Register | Offset | Applies To | Min | Max | Reset |
|----------|--------|-----------|-----|-----|-------|
| IC_FS_SPKLEN | 0xA0 | SS, FS, FM+ | 1 | 50 (IC_FS_MAX_SPKLEN) | IC_DEFAULT_FS_SPKLEN |
| IC_HS_SPKLEN | 0xA4 | HS | 1 | 10 (IC_HS_MAX_SPKLEN) | IC_DEFAULT_HS_SPKLEN |
| IC_UFM_SPKLEN | 0xA0 | UFM (shared) | 1 | 50 | IC_DEFAULT_UFM_SPKLEN |

### 13.3 Filter Behavior

- Spike filter length = IC_*_SPKLEN ic_clk periods
- Any pulse on SDA or SCL shorter than SPKLEN cycles is suppressed
- Applied to both SCL and SDA input signals
- Affects minimum HCNT value: HCNT >= SPKLEN + 5 (FREQ_OPT=0)

### 13.4 Impact on SCL Timing

The SPKLEN value directly appears in the SCL HIGH formula:
```
SCL_High = (HCNT + SPKLEN + 7) x t_ic_clk + t_fall   [FREQ_OPT=0]
SCL_High = (HCNT + SPKLEN + 3) x t_ic_clk + t_fall   [FREQ_OPT=1]
```

Increasing SPKLEN increases the effective SCL HIGH time and raises the minimum HCNT.

---

## 14. Speed Modes

### 14.1 Standard Speed (SS) -- 100 kbit/s

| Parameter | Value |
|-----------|-------|
| Max bit rate | 100 kbit/s |
| Registers | IC_SS_SCL_HCNT (0x14), IC_SS_SCL_LCNT (0x18) |
| Spike suppression | IC_FS_SPKLEN (0xA0) |
| IC_CON.SPEED | 1 |
| Drive type | Open-drain |
| SCL HIGH min | 4.0 us |
| SCL LOW min | 4.7 us |
| Min ic_clk | 2.7 MHz |

### 14.2 Fast Speed (FS) -- 400 kbit/s

| Parameter | Value |
|-----------|-------|
| Max bit rate | 400 kbit/s |
| Registers | IC_FS_SCL_HCNT (0x1C), IC_FS_SCL_LCNT (0x20) |
| Spike suppression | IC_FS_SPKLEN (0xA0) |
| IC_CON.SPEED | 2 |
| Drive type | Open-drain |
| SCL HIGH min | 0.6 us |
| SCL LOW min | 1.3 us |
| Min ic_clk | 12 MHz |

### 14.3 Fast-mode Plus (FM+) -- 1 Mbit/s

| Parameter | Value |
|-----------|-------|
| Max bit rate | 1 Mbit/s |
| Registers | IC_FS_SCL_HCNT (0x1C), IC_FS_SCL_LCNT (0x20) |
| Spike suppression | IC_FS_SPKLEN (0xA0) |
| IC_CON.SPEED | 2 (same as FS!) |
| Drive type | Open-drain |
| SCL HIGH min | 0.26 us |
| SCL LOW min | 0.5 us |
| Min ic_clk | 32 MHz |

> **Note:** FM+ uses the same SPEED setting (2) and same HCNT/LCNT registers as FS. The difference is in the programmed timing values to achieve 1 MHz.

### 14.4 High Speed (HS) -- 3.4 Mbit/s

| Parameter | Value |
|-----------|-------|
| Max bit rate | 3.4 Mbit/s |
| Registers | IC_HS_SCL_HCNT (0x24), IC_HS_SCL_LCNT (0x28) |
| Spike suppression | IC_HS_SPKLEN (0xA4) |
| IC_CON.SPEED | 3 |
| Drive type | Open-drain (current source optional) |
| SCL HIGH min | 0.06 us |
| SCL LOW min | 0.16 us |
| Min ic_clk | 51-105.4 MHz (depends on Cb) |
| Master code | IC_HS_MADDR (0x0C), 3 bits |

**HS mode protocol:**
1. Transfer starts in F/S mode with master code (0000 1XXX) as address
2. Master code is NOT ACKed (NACK expected; ABRT_HS_ACKDET if ACKed)
3. After master code, switch to HS timing
4. HS continues until STOP condition
5. After STOP, bus returns to F/S mode

> **Requires:** IC_RESTART_EN=1. Without RESTART, ABRT_HS_NORSTRT fires.

### 14.5 Ultra-Fast Mode (UFM) -- 5 Mbit/s

| Parameter | Value |
|-----------|-------|
| Max bit rate | 5 Mbit/s |
| Registers | IC_UFM_SCL_HCNT (0x14), IC_UFM_SCL_LCNT (0x18), IC_UFM_TBUF_CNT (0x1C) |
| Spike suppression | IC_UFM_SPKLEN (0xA0) |
| Drive type | **Push-pull** (not open-drain) |
| ACK | **No ACK** (transmitter drives dummy ACK) |
| Arbitration | **Not supported** |
| Clock stretching | **Not supported** |
| Direction | **Write-only** (master to slave) |
| Min HCNT | 3 |
| Min LCNT | 5 |

**Key differences from other modes:**
- Push-pull drive means no external pull-ups needed (for SCL and SDA)
- No ACK from slave: master generates dummy ACK bit
- No arbitration: only single master allowed
- No clock stretching: slave cannot slow down master
- Write-only: master cannot read from slave (CMD bit must be 0)
- TBuf register (0x1C) controls bus free time between STOP and next START

---

## 15. Bus Clear and Recovery

### 15.1 SDA Stuck LOW Recovery

**Prerequisite:** IC_CON[11] BUS_CLEAR_FEATURE_CTRL must be 1.

**Detection:** IC_TX_ABRT_SOURCE[17] ABRT_SDA_STUCK_AT_LOW is set.

**Recovery procedure:**
1. Confirm IC_TX_ABRT_SOURCE[17] = 1
2. Clear abort: Read IC_CLR_TX_ABRT
3. Initiate recovery: Write IC_ENABLE[3] = 1 (SDA_STUCK_RECOVERY_ENABLE)
4. Hardware sends up to 9 SCL clock pulses followed by STOP condition
5. Poll IC_ENABLE[3] until it reads 0 (recovery complete, auto-clears)
6. Check IC_STATUS[11] SDA_STUCK_NOT_RECOVERED:
   - 0 = Recovery successful, SDA is free
   - 1 = Recovery failed, SDA still stuck (hardware intervention needed)

> **PythonSV example:**
> ```python
> i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg
> abrt = i2c.IC_TX_ABRT_SOURCE.read()
> if abrt & (1 << 17):  # SDA stuck
>     i2c.IC_CLR_TX_ABRT.read()       # Clear abort
>     i2c.IC_ENABLE.write(i2c.IC_ENABLE.read() | 0x8)  # Set bit 3
>     while i2c.IC_ENABLE.read() & 0x8:  # Poll until auto-clear
>         pass
>     status = i2c.IC_STATUS.read()
>     if status & (1 << 11):
>         print("SDA recovery FAILED")
>     else:
>         print("SDA recovery successful")
> ```

### 15.2 SCL Stuck LOW Detection

**Detection:** IC_SCL_STUCK_AT_LOW_TIMEOUT counts ic_clk periods while SCL is LOW. When the count exceeds the programmed value, SCL_STUCK_AT_LOW interrupt (bit 14) fires.

**Recovery:** SCL stuck LOW cannot be recovered by the I2C controller. SCL is driven by the master, and a stuck SCL indicates:
- A slave is holding SCL LOW indefinitely (hung slave)
- Hardware fault on the bus

**Required action:** Hardware reset of the bus or the hung device.

### 15.3 Timeout Configuration

| Register | Offset | Purpose |
|----------|--------|---------|
| IC_SCL_STUCK_AT_LOW_TIMEOUT | 0xAC | SCL LOW timeout (ic_clk periods) |
| IC_SDA_STUCK_AT_LOW_TIMEOUT | 0xB0 | SDA LOW timeout (ic_clk periods) |

---

## 16. Device ID

### 16.1 Device ID Format

The I2C Device ID is a 24-bit value:

| Bits | Field | Width | Description |
|------|-------|-------|-------------|
| [23:12] | Manufacturer ID | 12 bits | Assigned by I2C committee |
| [11:3] | Part Identification | 9 bits | Assigned by manufacturer |
| [2:0] | Revision | 3 bits | Assigned by manufacturer |

### 16.2 Device ID Read Protocol

1. Set IC_TAR: target address in [9:0], DEVICE_ID[13]=1, SPECIAL[11]=1
2. Push 3 read commands to IC_DATA_CMD (CMD=1), last with STOP=1
3. Read 3 bytes from IC_DATA_CMD:
   - Byte 1: [23:16] (MSB of manufacturer ID + upper part ID)
   - Byte 2: [15:8]
   - Byte 3: [7:0] (LSB: lower part ID + revision)
4. Result also available in IC_DEVICE_ID register (0xB8)

### 16.3 Constraints

- **Not supported** with 10-bit slave addressing
- **Not supported** in HS mode
- Requires IC_RESTART_EN=1
- IC_DEVICE_ID configuration parameter must be enabled

---

## 17. SMBus and PMBus Support

### 17.1 SMBus Bus Protocols

| # | Protocol | Direction | Byte Count | PEC | Description |
|---|----------|-----------|-----------|-----|-------------|
| 1 | Quick Command | W | 0 | No | R/W bit only (no data) |
| 2 | Send Byte | W | 1 | Optional | Single data byte to slave |
| 3 | Receive Byte | R | 1 | Optional | Single data byte from slave |
| 4 | Write Byte | W | 2 | Optional | Command + 1 data byte |
| 5 | Read Byte | R | 2 | Optional | Command + 1 data byte |
| 6 | Write Word | W | 3 | Optional | Command + 2 data bytes |
| 7 | Read Word | R | 3 | Optional | Command + 2 data bytes |
| 8 | Block Write | W | N+1 | Optional | Command + count + N data bytes |
| 9 | Block Read | R | N+1 | Optional | Command + count + N data bytes |
| 10 | Process Call | W+R | 4 | Optional | Command + 2W + 2R |
| 11 | Block Write-Block Read | W+R | N+M | Optional | Combined block transfer |

### 17.2 ARP (Address Resolution Protocol)

ARP enables dynamic slave address assignment using a 128-bit UDID.

**UDID Register Layout:**

| Register | Offset | UDID Bits | Content |
|----------|--------|-----------|---------|
| IC_SMBUS_UDID_WORD3 | 0xE8 | [127:96] | Device capabilities, version |
| IC_SMBUS_UDID_WORD2 | 0xE4 | [95:64] | Vendor/device ID |
| IC_SMBUS_UDID_WORD1 | 0xE0 | [63:32] | Interface, subsystem info |
| IC_SMBUS_UDID_LSB | 0xDC | [31:0] | Vendor-specific ID |

**ARP Commands:**
- Prepare to ARP: Notify all slaves to prepare for address assignment
- Reset Device (General/Directed): Reset all or specific slave ARP states
- Get UDID (General/Directed): Read UDID from slave(s)
- Assign Address: Assign a new 7-bit address to a slave

**ARP Control:**
- IC_CON[18] SMBUS_ARP_EN: Enable ARP in slave mode
- IC_CON[19] SMBUS_PERSISTENT_SLV_ADDR_EN: Address persists across ARP Reset
- PEC is handled in hardware for ARP commands in slave mode

### 17.3 SMBus Timeouts

| Timeout | Register | Spec Limit | Description |
|---------|----------|-----------|-------------|
| SEXT | IC_SMBUS_CLK_LOW_SEXT (0xBC) | 25 ms | Slave clock extend: max time slave can hold SCL LOW |
| MEXT | IC_SMBUS_CLK_LOW_MEXT (0xC0) | 10 ms | Master clock extend: max cumulative LOW time between START/ACK or ACK/ACK |
| tHIGH:MAX | IC_SMBUS_THIGH_MAX_IDLE_COUNT (0xC4) | 50 us | Bus idle detection threshold |

### 17.4 SMBus Suspend and Alert

**Suspend (SMBSUS):**
- IC_ENABLE[17] SMBUS_SUSPEND_EN: Assert SMBSUS output signal
- ic_smbsus_in_n: Input signal from remote device
- SMBUS_SUSPEND_DET interrupt when remote asserts

**Alert (SMBALERT):**
- IC_ENABLE[18] SMBUS_ALERT_EN: Assert SMBALERT output signal
- ic_smbalert_in_n: Input signal from remote device
- SMBUS_ALERT_DET interrupt when remote asserts
- SMBUS_ALERT_EN auto-clears after master ACKs alert response address

### 17.5 Quick Command

- IC_TAR[16] SMBUS_QUICK_CMD=1
- No data bytes: R/W bit in address byte is the command
- Slave mode: QUICK_CMD_DET interrupt, R/W bit in IC_STATUS[16]

---

## 18. Multi-Master

### 18.1 SDA-Based Arbitration

When multiple masters start simultaneously:
1. Both masters drive SCL (wired-AND: slowest clock wins)
2. Masters compare their SDA output with bus SDA
3. Master driving HIGH while bus reads LOW has lost arbitration
4. Losing master releases SDA and SCL, sets ARB_LOST
5. Winning master continues unaware

### 18.2 Clock Synchronization

- SCL is wired-AND: any master can hold it LOW
- HIGH period = shortest of all masters' HIGH periods
- LOW period = longest of all masters' LOW periods
- Result: all masters synchronize to a combined clock

### 18.3 Arbitration Rules

| Arbitration Between | Allowed |
|-------------------|---------|
| Two data transfers | Yes |
| Data and RESTART | No (undefined behavior) |
| Data and STOP | No (undefined behavior) |
| RESTART and STOP | No (undefined behavior) |

### 18.4 HS Mode Multi-Master

- Arbitration occurs only during F/S preamble (master code)
- Each master uses a unique IC_HS_MADDR value (0-7)
- After master code wins arbitration, HS transfer proceeds without further arbitration
- After STOP, bus returns to F/S mode

---

## 19. Programming Examples

### 19.1 Master-TX: Write 3 Bytes to Slave 0x50

```python
# PythonSV - NVL PCD-H
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# 1. Disable
i2c.IC_ENABLE.write(0x0)
while i2c.IC_ENABLE_STATUS.read() & 0x1:
    pass

# 2. Configure
i2c.IC_CON.write(0x65)           # Master, FS, restart, slave-disable
i2c.IC_TAR.write(0x50)           # Target address
i2c.IC_FS_SCL_HCNT.write(0x3C)  # FS high count
i2c.IC_FS_SCL_LCNT.write(0x82)  # FS low count
i2c.IC_SDA_HOLD.write(0x01)     # SDA TX hold = 1 ic_clk
i2c.IC_FS_SPKLEN.write(0x05)    # Spike filter = 5 ic_clk
i2c.IC_TX_TL.write(0x00)        # TX threshold = 0
i2c.IC_INTR_MASK.write(0x0)     # Mask all interrupts (polling mode)

# 3. Enable
i2c.IC_ENABLE.write(0x1)

# 4. Write 3 bytes (Mode 1: explicit STOP on last)
i2c.IC_DATA_CMD.write(0x0A0)    # Write byte 0xA0, no STOP
i2c.IC_DATA_CMD.write(0x0B1)    # Write byte 0xB1, no STOP
i2c.IC_DATA_CMD.write(0x2C2)    # Write byte 0xC2, STOP=1 (bit 9)

# 5. Wait for completion
while not (i2c.IC_RAW_INTR_STAT.read() & 0x200):  # STOP_DET
    if i2c.IC_RAW_INTR_STAT.read() & 0x40:         # TX_ABRT
        abrt = i2c.IC_TX_ABRT_SOURCE.read()
        print(f"Abort: 0x{abrt:08X}")
        i2c.IC_CLR_TX_ABRT.read()
        break
```

### 19.2 Master-RX: Read 4 Bytes from Slave 0x50

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# (Assume already initialized and enabled from 19.1)

# Push 4 read commands, STOP on last
i2c.IC_DATA_CMD.write(0x100)    # Read, no STOP
i2c.IC_DATA_CMD.write(0x100)    # Read, no STOP
i2c.IC_DATA_CMD.write(0x100)    # Read, no STOP
i2c.IC_DATA_CMD.write(0x300)    # Read, STOP=1

# Read received data
data = []
for i in range(4):
    while not (i2c.IC_STATUS.read() & 0x8):  # Wait RFNE
        pass
    data.append(i2c.IC_DATA_CMD.read() & 0xFF)
print(f"Received: {[hex(b) for b in data]}")
```

### 19.3 Combined Write-then-Read (Register Read Pattern)

```python
# Common pattern: write register address, then read register value
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# Write 1-byte register address, RESTART, then read 2 data bytes
i2c.IC_DATA_CMD.write(0x010)    # Write reg addr 0x10, no STOP
i2c.IC_DATA_CMD.write(0x500)    # RESTART + Read (bit 10 + bit 8)
i2c.IC_DATA_CMD.write(0x300)    # Read + STOP (bit 9 + bit 8)

# Read 2 result bytes
for i in range(2):
    while not (i2c.IC_STATUS.read() & 0x8):
        pass
    val = i2c.IC_DATA_CMD.read() & 0xFF
    print(f"Byte {i}: 0x{val:02X}")
```

### 19.4 Slave-TX: Respond to Master Reads

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# 1. Disable and configure as slave
i2c.IC_ENABLE.write(0x0)
while i2c.IC_ENABLE_STATUS.read() & 0x1:
    pass

i2c.IC_CON.write(0x00)           # Slave mode, SS, no master
i2c.IC_SAR.write(0x50)           # Slave address 0x50
i2c.IC_INTR_MASK.write(0x020)    # Unmask RD_REQ only (bit 5)
i2c.IC_ENABLE.write(0x1)

# 2. Handle RD_REQ in polling loop
while True:
    intr = i2c.IC_RAW_INTR_STAT.read()
    if intr & 0x20:                 # RD_REQ
        i2c.IC_CLR_RD_REQ.read()   # Clear interrupt
        i2c.IC_DATA_CMD.write(0xAA) # Provide data byte
    if intr & 0x80:                 # RX_DONE
        i2c.IC_CLR_RX_DONE.read()
        break                       # Master finished reading
```

### 19.5 Slave-RX: Receive Data from Master

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# (Assume configured as slave from 19.4)
i2c.IC_INTR_MASK.write(0x04)     # Unmask RX_FULL (bit 2)

# Read incoming data
received = []
while True:
    intr = i2c.IC_RAW_INTR_STAT.read()
    if intr & 0x04:                 # RX_FULL
        data = i2c.IC_DATA_CMD.read() & 0xFF
        received.append(data)
    if intr & 0x200:                # STOP_DET
        # Drain remaining RX FIFO
        while i2c.IC_STATUS.read() & 0x8:  # RFNE
            received.append(i2c.IC_DATA_CMD.read() & 0xFF)
        i2c.IC_CLR_STOP_DET.read()
        break
```

### 19.6 Bus Recovery (SDA Stuck)

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# Check for SDA stuck
abrt = i2c.IC_TX_ABRT_SOURCE.read()
if abrt & (1 << 17):               # ABRT_SDA_STUCK_AT_LOW
    i2c.IC_CLR_TX_ABRT.read()      # Clear abort
    
    # Ensure bus clear feature is enabled
    con = i2c.IC_CON.read()
    if not (con & (1 << 11)):
        i2c.IC_ENABLE.write(0x0)
        while i2c.IC_ENABLE_STATUS.read() & 0x1:
            pass
        i2c.IC_CON.write(con | (1 << 11))  # Enable bus clear
        i2c.IC_ENABLE.write(0x1)
    
    # Initiate SDA recovery
    enable_val = i2c.IC_ENABLE.read()
    i2c.IC_ENABLE.write(enable_val | 0x8)  # Set bit 3
    
    # Wait for completion
    while i2c.IC_ENABLE.read() & 0x8:
        pass
    
    # Check result
    if i2c.IC_STATUS.read() & (1 << 11):
        print("ERROR: SDA recovery failed - hardware intervention needed")
    else:
        print("SDA recovery successful")
```

### 19.7 Device ID Read

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# Configure for Device ID read from slave at 0x50
i2c.IC_ENABLE.write(0x0)
while i2c.IC_ENABLE_STATUS.read() & 0x1:
    pass

i2c.IC_CON.write(0x65)           # Master, FS, restart, slave-disable
i2c.IC_TAR.write(0x50 | (1 << 13) | (1 << 11))  # DEVICE_ID=1, SPECIAL=1, addr=0x50
i2c.IC_ENABLE.write(0x1)

# Push 3 read commands (Device ID is 3 bytes)
i2c.IC_DATA_CMD.write(0x100)     # Read byte 1
i2c.IC_DATA_CMD.write(0x100)     # Read byte 2
i2c.IC_DATA_CMD.write(0x300)     # Read byte 3, STOP

# Read 3 bytes
device_id = 0
for i in range(3):
    while not (i2c.IC_STATUS.read() & 0x8):
        pass
    byte_val = i2c.IC_DATA_CMD.read() & 0xFF
    device_id = (device_id << 8) | byte_val

manufacturer = (device_id >> 12) & 0xFFF
part_id = (device_id >> 3) & 0x1FF
revision = device_id & 0x7
print(f"Device ID: 0x{device_id:06X}")
print(f"  Manufacturer: 0x{manufacturer:03X}")
print(f"  Part ID: 0x{part_id:03X}")
print(f"  Revision: {revision}")
```

### 19.8 SMBus Quick Command (Master)

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# Quick Command write to slave 0x50
i2c.IC_ENABLE.write(0x0)
while i2c.IC_ENABLE_STATUS.read() & 0x1:
    pass
i2c.IC_TAR.write(0x50 | (1 << 16))  # SMBUS_QUICK_CMD=1, addr=0x50
i2c.IC_ENABLE.write(0x1)
i2c.IC_DATA_CMD.write(0x200)         # CMD=0 (write), STOP=1
```

### 19.9 UFM Master Transfer

```python
i2c = nn.sv.socket0.pcd.lpss.i2c0.cfg

# UFM is write-only, push-pull, no ACK
i2c.IC_ENABLE.write(0x0)
while i2c.IC_ENABLE_STATUS.read() & 0x1:
    pass

i2c.IC_CON.write(0x61)           # Master, SS (speed field=1 for UFM), slave-disable
# Note: UFM shares SS registers at 0x14/0x18
i2c.IC_SS_SCL_HCNT.write(0x03)  # UFM HCNT min=3
i2c.IC_SS_SCL_LCNT.write(0x05)  # UFM LCNT min=5
i2c.IC_TAR.write(0x50)

i2c.IC_ENABLE.write(0x1)

# Write-only transfers (no reads in UFM!)
i2c.IC_DATA_CMD.write(0x0AA)     # Write 0xAA
i2c.IC_DATA_CMD.write(0x2BB)     # Write 0xBB, STOP
```

---

## 20. Integration and Verification

### 20.1 Clock and Reset Requirements

| Signal | Description | Requirement |
|--------|-------------|-------------|
| ic_clk | I2C clock domain | Must meet minimum frequency for selected speed mode |
| ic_rst_n | I2C reset (active low) | Synchronous to ic_clk |
| pclk | APB clock | Register access clock |
| presetn | APB reset (active low) | Synchronous to pclk |
| hclk | DMA handshaking clock | Must be phase-aligned with pclk; frequency must be integer multiple |

### 20.2 Register Access Rules

| Rule | Description |
|------|-------------|
| Write-when-disabled | Most config registers only writable when IC_ENABLE[0]=0 |
| SPEED clamping | IC_CON.SPEED is clamped to IC_MAX_SPEED_MODE |
| Threshold clamping | IC_RX_TL/IC_TX_TL clamped to FIFO depth - 1 |
| HCNT/LCNT minimums | Enforced per speed mode and FREQ_OPT setting |
| Read-only enforcement | Read-only registers ignore writes silently |
| IC_DATA_CMD split | Write path: TX FIFO; Read path: RX FIFO |

### 20.3 Key Test Scenarios

From the databook Chapter 7 (Verification):

| Category | Test Scenarios |
|----------|---------------|
| APB Interface | Reset values, R/W access, read-only enforcement, write-when-disabled |
| Master Operation | 7-bit TX/RX, 10-bit TX/RX, combined format, all speed modes |
| Slave Operation | Slave-TX, slave-RX, clock stretching, General Call |
| Interrupts | All 15 I2C + 11 SMBus sources individually, masking, clearing |
| DMA | TX/RX handshaking, watermark levels, burst/single modes |
| Dynamic TAR | MASTER_ON_HOLD interrupt, TAR change mid-stream |
| SDA Hold/Setup | IC_SDA_HOLD timing, IC_SDA_SETUP timing |
| Error Cases | All 21 abort sources, arbitration loss, bus recovery |
| SMBus | Timeouts, ARP, Quick Command, Alert, Suspend |
| Device ID | 3-byte read, manufacturer/part/revision decode |
| FIFO | Overflow, underflow, threshold behavior, depth limits |

### 20.4 Synthesis Reference

| Configuration | Gate Count | Frequency | Power |
|--------------|------------|-----------|-------|
| Default (28nm) | 11,297 gates | 200 MHz | 0.179 uW static + 167.305 uW dynamic |
| Min (slave only, 2-deep FIFO) | 5,777 gates | — | — |
| Max (SMBus, async FIFO) | 20,560 gates | — | — |

---

## 21. Configuration Parameters

### 21.1 Top-Level Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| IC_MASTER_MODE | 1 | 0-1 | Enable master mode at reset |
| IC_SLAVE_DISABLE | 1 | 0-1 | Disable slave mode at reset |
| IC_MAX_SPEED_MODE | 3 (HS) | 1-3 | Maximum speed mode supported (1=SS, 2=FS, 3=HS) |
| IC_10BITADDR_MASTER | 0 | 0-1 | Default master addressing mode |
| IC_10BITADDR_SLAVE | 0 | 0-1 | Default slave addressing mode |
| IC_TX_BUFFER_DEPTH | 8 | 2-256 | TX FIFO depth. **Intel LPSS: 64** |
| IC_RX_BUFFER_DEPTH | 8 | 2-256 | RX FIFO depth. **Intel LPSS: 64** |
| IC_HAS_DMA | 0 | 0-1 | DMA interface present. **Intel LPSS: I2C0-3=1, I2C4-5=0** |
| IC_EMPTYFIFO_HOLD_MASTER_EN | 0 | 0-1 | TX FIFO hold mode. **Intel LPSS: 1** |
| IC_RESTART_EN | 1 | 0-1 | Default RESTART enable |
| IC_INTR_IO | 0 | 0-1 | 0=individual interrupt outputs; 1=combined |
| IC_SLV_RESTART_DET_EN | 0 | 0-1 | Enable RESTART_DET interrupt in slave mode |
| IC_BUS_CLEAR_FEATURE | 0 | 0-1 | Bus clear/recovery feature |
| I2C_DYNAMIC_TAR_UPDATE | 0 | 0-1 | Dynamic target address update support |
| IC_RX_FULL_HLD_BUS_EN | 0 | 0-1 | Allow bus hold on RX FIFO full |
| IC_STOP_DET_IF_MASTER_ACTIVE | 0 | 0-1 | STOP_DET only when master active |
| IC_CLK_FREQ_OPTIMIZATION | 0 | 0-1 | Clock optimization (reduces HCNT overhead) |
| IC_CLK_TYPE | 0 | 0-1 | 0=synchronous clocks; 1=asynchronous |
| IC_HAS_ASYNC_FIFO | 0 | 0-1 | Asynchronous FIFO (different clock domains) |
| IC_DEVICE_ID | 0 | 0-1 | Device ID feature support |
| IC_HC_COUNT_VALUES | 0 | 0-1 | 1=HCNT/LCNT are hardcoded (read-only) |
| IC_OPTIONAL_SAR | 0 | 0-1 | Optional second slave address |

### 21.2 Spike Suppression Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| IC_DEFAULT_FS_SPKLEN | 1 | 1-50 | Default FS/SS/FM+ spike filter length |
| IC_DEFAULT_HS_SPKLEN | 1 | 1-10 | Default HS spike filter length |
| IC_DEFAULT_UFM_SPKLEN | 1 | 1-255 | Default UFM spike filter length |
| IC_FS_MAX_SPKLEN | 50 | — | Maximum FS SPKLEN (constant) |
| IC_HS_MAX_SPKLEN | 10 | — | Maximum HS SPKLEN (constant) |

### 21.3 SMBus Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| IC_SMBUS | 0 | 0-1 | SMBus support enable |
| IC_SMBUS_ARP | 0 | 0-1 | ARP support enable |
| IC_SMBUS_SUSPEND | 0 | 0-1 | Suspend/Alert support |

### 21.4 SCL Timing Default Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| IC_SS_SCL_HIGH_COUNT | SS SCL high count reset value | 0x0190 |
| IC_SS_SCL_LOW_COUNT | SS SCL low count reset value | 0x01D6 |
| IC_FS_SCL_HIGH_COUNT | FS SCL high count reset value | 0x003C |
| IC_FS_SCL_LOW_COUNT | FS SCL low count reset value | 0x0082 |
| IC_HS_SCL_HIGH_COUNT | HS SCL high count reset value | 0x0006 |
| IC_HS_SCL_LOW_COUNT | HS SCL low count reset value | 0x0010 |
| IC_DEFAULT_SDA_HOLD | Default SDA hold time | 0x0001 |
| IC_DEFAULT_SDA_SETUP | Default SDA setup time | 0x0064 |

### 21.5 Internal Parameters (Appendix B)

| Parameter | Value | Description |
|-----------|-------|-------------|
| IC_VERSION_ID | 0x3230322A | ASCII "202*" for v2.02a |
| IC_HCNT_LO_LIMIT (default) | 6 | Minimum HCNT (FREQ_OPT=0, non-UFM) |
| IC_HCNT_LO_LIMIT (FREQ_OPT=1) | 1 | Minimum HCNT |
| IC_HCNT_LO_LIMIT (UFM) | 3 | Minimum HCNT for UFM |
| IC_LCNT_LO_LIMIT (default) | 8 | Minimum LCNT (FREQ_OPT=0, non-UFM) |
| IC_LCNT_LO_LIMIT (FREQ_OPT=1) | 6 | Minimum LCNT |
| IC_LCNT_LO_LIMIT (UFM) | 5 | Minimum LCNT for UFM |
| IC_ADDR_SLICE_LHS | 3'b111 | 7-bit address decode slice |
| IC_COMP_TYPE | 0x44570140 | Component type identifier |

---

## 22. Validation Checklist

### 22.1 Register Access Validation

- [ ] Verify all register reset values match databook/configuration
- [ ] Verify read-only registers (IC_STATUS, IC_TXFLR, IC_RXFLR, IC_INTR_STAT, etc.) reject writes
- [ ] Verify registers writable only when IC_ENABLE[0]=0 reject writes when enabled
- [ ] Verify IC_CON.SPEED field clamps to IC_MAX_SPEED_MODE
- [ ] Verify IC_RX_TL clamps to IC_RX_BUFFER_DEPTH - 1 (63 on Intel LPSS)
- [ ] Verify IC_TX_TL clamps to IC_TX_BUFFER_DEPTH - 1 (63 on Intel LPSS)
- [ ] Verify IC_COMP_PARAM_1 encodes correct FIFO depth, DMA, speed mode
- [ ] Verify IC_COMP_VERSION reads expected version
- [ ] Verify IC_COMP_TYPE reads 0x44570140
- [ ] Verify IC_DATA_CMD write goes to TX FIFO, read comes from RX FIFO
- [ ] Verify HCNT/LCNT minimum value enforcement per speed mode

### 22.2 Master Mode Validation

- [ ] 7-bit addressing: TX single byte with STOP
- [ ] 7-bit addressing: TX multi-byte with STOP
- [ ] 7-bit addressing: RX single byte with STOP
- [ ] 7-bit addressing: RX multi-byte with STOP
- [ ] 10-bit addressing: TX with two-byte address
- [ ] 10-bit addressing: RX with RESTART
- [ ] Combined format: write register address, RESTART, read data
- [ ] STOP bit control in Mode 1 (IC_DATA_CMD[9])
- [ ] RESTART bit control in Mode 1 (IC_DATA_CMD[10])
- [ ] Dynamic TAR update with MASTER_ON_HOLD interrupt
- [ ] Static TAR update (disable, change, re-enable)
- [ ] SS mode (100 kbit/s) timing verification
- [ ] FS mode (400 kbit/s) timing verification
- [ ] FM+ mode (1 Mbit/s) timing verification
- [ ] HS mode (3.4 Mbit/s) with master code preamble
- [ ] Back-to-back transfers without disable
- [ ] Maximum FIFO utilization (64-byte burst)
- [ ] TX_EMPTY_CTRL=0 vs TX_EMPTY_CTRL=1 behavior

### 22.3 Slave Mode Validation

- [ ] Slave-transmitter: RD_REQ interrupt -> write data -> RX_DONE
- [ ] Slave-receiver: RX_FULL interrupt -> read data
- [ ] Clock stretching: slave-TX with delayed response
- [ ] Clock stretching: slave-RX with RX FIFO full (RX_FIFO_FULL_HLD_CTRL=1)
- [ ] No clock stretching: RX FIFO overflow (RX_FIFO_FULL_HLD_CTRL=0)
- [ ] General Call accept (IC_ACK_GENERAL_CALL=1)
- [ ] General Call reject (IC_ACK_GENERAL_CALL=0)
- [ ] Optional SAR (IC_OPTIONAL_SAR_CTRL=1, two slave addresses)
- [ ] IC_SLV_DATA_NACK_ONLY=1 (NACK data bytes)
- [ ] Bulk transfer mode: large data blocks
- [ ] STOP_DET_IFADDRESSED=0 vs =1
- [ ] FIRST_DATA_BYTE (IC_DATA_CMD[11]) flag after address

### 22.4 Interrupt Validation

- [ ] RX_UNDER: read from empty RX FIFO, verify interrupt fires
- [ ] RX_OVER: fill RX FIFO beyond capacity
- [ ] RX_FULL: verify threshold (IC_RX_TL+1) triggers correctly
- [ ] TX_OVER: write to full TX FIFO
- [ ] TX_EMPTY: verify threshold (IC_TX_TL) with TX_EMPTY_CTRL=0 and =1
- [ ] RD_REQ: slave-TX request, verify clock stretch
- [ ] TX_ABRT: trigger each abort source, verify TX_ABRT fires
- [ ] RX_DONE: slave-TX complete (master NACK)
- [ ] ACTIVITY: any transfer, verify activity flag
- [ ] STOP_DET: STOP condition, verify with STOP_DET_IFADDRESSED and STOP_DET_IF_MASTER_ACTIVE
- [ ] START_DET: START/RESTART condition
- [ ] GEN_CALL: General Call received
- [ ] RESTART_DET: RESTART in slave mode
- [ ] MASTER_ON_HOLD: Mode 1 + dynamic TAR, TX FIFO empty
- [ ] SCL_STUCK_AT_LOW: timeout expiration
- [ ] IC_INTR_MASK: mask each bit individually, verify IC_INTR_STAT suppressed
- [ ] IC_CLR_INTR: verify clears all software-clearable interrupts
- [ ] Individual IC_CLR_* registers: verify each clears only its interrupt
- [ ] SMBus interrupts: all 11 sources
- [ ] SMBus W1C clearing: verify write-1-to-clear behavior

### 22.5 DMA Validation

- [ ] TX DMA handshaking at DMATDL=0 (request when FIFO empty)
- [ ] TX DMA handshaking at DMATDL=32 (mid-FIFO watermark)
- [ ] RX DMA handshaking at DMARDL=0 (request when 1+ entries)
- [ ] RX DMA handshaking at DMARDL=31 (mid-FIFO watermark)
- [ ] DMA burst transfer (multi-byte)
- [ ] DMA single transfer
- [ ] Combined DMA TX+RX
- [ ] DMA with I2C0, I2C1, I2C2, I2C3 (IC_HAS_DMA=1)
- [ ] Verify I2C4, I2C5 DMA registers not present/functional (IC_HAS_DMA=0)
- [ ] DMA + interrupt coexistence

### 22.6 Error and Abort Validation

- [ ] ABRT_7B_ADDR_NOACK: no slave at target address
- [ ] ABRT_10ADDR1_NOACK: 10-bit address byte 1 NACK
- [ ] ABRT_10ADDR2_NOACK: 10-bit address byte 2 NACK
- [ ] ABRT_TXDATA_NOACK: slave NACKs data byte
- [ ] ABRT_GCALL_NOACK: General Call NACK
- [ ] ABRT_GCALL_READ: General Call with read
- [ ] ABRT_HS_ACKDET: HS master code ACK
- [ ] ABRT_SBYTE_ACKDET: START byte ACK
- [ ] ABRT_HS_NORSTRT: HS without RESTART
- [ ] ABRT_SBYTE_NORSTRT: START byte without RESTART (special clearing)
- [ ] ABRT_10B_RD_NORSTRT: 10-bit read without RESTART
- [ ] ABRT_MASTER_DIS: master op with master disabled
- [ ] ARB_LOST: multi-master arbitration loss
- [ ] ABRT_SLVFLUSH_TXFIFO: slave TX FIFO flush
- [ ] ABRT_SLV_ARBLOST: slave transmitter lost arbitration
- [ ] ABRT_SLVRD_INTX: write command in slave-TX
- [ ] ABRT_USER_ABRT: user abort via IC_ENABLE[1]
- [ ] ABRT_SDA_STUCK_AT_LOW: SDA stuck detection
- [ ] ABRT_DEVICE_NOACK: Device ID NACK
- [ ] ABRT_DEVICE_SLVADDR_NOACK: Device ID slave NACK
- [ ] ABRT_DEVICE_WRITE: Device ID with writes
- [ ] TX_FLUSH_CNT: verify count accuracy after abort
- [ ] Abort then clear then retry: verify clean recovery

### 22.7 Timing Validation

- [ ] SCL HIGH time at SS (>= 4.0 us)
- [ ] SCL LOW time at SS (>= 4.7 us)
- [ ] SCL HIGH time at FS (>= 0.6 us)
- [ ] SCL LOW time at FS (>= 1.3 us)
- [ ] SCL HIGH time at FM+ (>= 0.26 us)
- [ ] SCL LOW time at FM+ (>= 0.5 us)
- [ ] SCL HIGH time at HS (>= 0.06 us)
- [ ] SCL LOW time at HS (>= 0.16 us)
- [ ] SDA TX hold time (IC_SDA_TX_HOLD)
- [ ] SDA RX hold time (IC_SDA_RX_HOLD)
- [ ] SDA setup time (IC_SDA_SETUP, min 2)
- [ ] Spike suppression: pulse shorter than SPKLEN filtered
- [ ] Spike suppression: pulse equal to SPKLEN passes through
- [ ] HCNT minimum enforcement (write below min, verify clamped/rejected)
- [ ] LCNT minimum enforcement

### 22.8 Bus Clear and Recovery Validation

- [ ] SDA stuck recovery: 9 SCL clocks + STOP
- [ ] SDA stuck: IC_ENABLE[3] auto-clears after recovery
- [ ] SDA stuck: IC_STATUS[11] = 0 on success
- [ ] SDA stuck: IC_STATUS[11] = 1 on failure
- [ ] SCL stuck timeout: IC_SCL_STUCK_AT_LOW_TIMEOUT triggers interrupt
- [ ] Bus clear feature disabled: IC_CON[11]=0, recovery not available

### 22.9 SMBus Validation

- [ ] Quick Command (master and slave)
- [ ] Send Byte / Receive Byte
- [ ] Write Byte / Read Byte
- [ ] Write Word / Read Word
- [ ] Block Write / Block Read
- [ ] Process Call
- [ ] Block Write-Block Read Process Call
- [ ] ARP Prepare to ARP
- [ ] ARP Reset Device (general and directed)
- [ ] ARP Get UDID (general and directed)
- [ ] ARP Assign Address
- [ ] UDID register programming (Word0-3)
- [ ] SEXT timeout: slave clock extend beyond 25ms
- [ ] MEXT timeout: master clock extend beyond 10ms
- [ ] tHIGH:MAX bus idle detection
- [ ] SMBSUS signal assertion/deassertion
- [ ] SMBALERT signal assertion and auto-clear
- [ ] PEC handling in slave ARP
- [ ] Host Notify detection
- [ ] Persistent slave address (SMBUS_PERSISTENT_SLV_ADDR_EN)

### 22.10 Device ID Validation

- [ ] 3-byte Device ID read: correct manufacturer, part, revision
- [ ] Device ID from IC_DEVICE_ID register (0xB8)
- [ ] Device ID with 10-bit address (should fail/abort)
- [ ] Device ID in HS mode (should fail/abort)
- [ ] Device ID with write commands (ABRT_DEVICE_WRITE)

### 22.11 Power and Platform Validation (Intel LPSS)

- [ ] D0i2 entry with active SDA hold
- [ ] D0i2 exit and transfer resumption
- [ ] All 6 I2C instances (I2C0-5) basic functionality
- [ ] DMA instances (I2C0-3) vs PIO-only instances (I2C4-5)
- [ ] FIFO depth = 64 verified on all instances via IC_COMP_PARAM_1
- [ ] Register access via PythonSV on NVL PCD-H path
- [ ] Concurrent operation of multiple I2C instances

---

## 23. Appendix

### 23.1 Signal Reference

#### I2C Interface Signals

| Signal | Direction | Description |
|--------|-----------|-------------|
| ic_clk | Input | I2C module clock |
| ic_clk_in_a | Input | Asynchronous SCL input (for async mode) |
| ic_data_in_a | Input | Asynchronous SDA input (for async mode) |
| ic_rst_n | Input | Active-low reset |
| ic_clk_oe | Output | SCL output enable (open-drain: 0=drive LOW) |
| ic_data_oe | Output | SDA output enable (open-drain: 0=drive LOW) |
| ic_en | Output | I2C enabled indication |
| ic_current_src_en | Output | HS mode current source enable |

#### APB Slave Interface Signals

| Signal | Direction | Width | Description |
|--------|-----------|-------|-------------|
| pclk | Input | 1 | APB clock |
| presetn | Input | 1 | APB reset (active-low) |
| psel | Input | 1 | Slave select |
| penable | Input | 1 | Enable phase |
| pwrite | Input | 1 | Write strobe |
| paddr | Input | varies | Address bus |
| pwdata | Input | 8/16/32 | Write data |
| prdata | Output | 8/16/32 | Read data |
| pready | Output | 1 | Transfer ready |
| pslverr | Output | 1 | Slave error |

#### DMA Interface Signals

| Signal | Direction | Description |
|--------|-----------|-------------|
| dma_tx_req | Output | TX burst DMA request |
| dma_tx_single | Output | TX single DMA request |
| dma_tx_ack | Input | TX DMA acknowledge |
| dma_rx_req | Output | RX burst DMA request |
| dma_rx_single | Output | RX single DMA request |
| dma_rx_ack | Input | RX DMA acknowledge |

#### SMBus Interface Signals

| Signal | Direction | Description |
|--------|-----------|-------------|
| ic_smbsus_in_n | Input | SMBSUS input (active-low) |
| ic_smbalert_in_n | Input | SMBALERT input (active-low) |
| ic_smbsus_out_n | Output | SMBSUS output (active-low) |
| ic_smbalert_oe | Output | SMBALERT output enable |

#### Debug Signals

| Signal | Width | Description |
|--------|-------|-------------|
| debug_s_gen | 1 | START condition generated |
| debug_p_gen | 1 | STOP condition generated |
| debug_data | 1 | Data phase active |
| debug_addr | 1 | Address phase active |
| debug_rd | 1 | Read transfer |
| debug_wr | 1 | Write transfer |
| debug_hs | 1 | HS mode active |
| debug_master_act | 1 | Master FSM active |
| debug_slave_act | 1 | Slave FSM active |
| debug_addr_10bit | 1 | 10-bit address in use |
| debug_mst_cstate | 5 | Master FSM current state |
| debug_slv_cstate | 4 | Slave FSM current state |

### 23.2 Glossary

| Term | Definition |
|------|-----------|
| ACK | Acknowledge: receiver pulls SDA LOW on 9th clock |
| ARP | Address Resolution Protocol (SMBus dynamic address assignment) |
| Cb | Bus capacitance |
| CMD | Command bit in IC_DATA_CMD: 0=write, 1=read |
| DMA | Direct Memory Access |
| FM+ | Fast-mode Plus (1 Mbit/s) |
| FS | Fast Speed (400 kbit/s) |
| GC | General Call |
| HCNT | SCL HIGH count register value |
| HS | High Speed (3.4 Mbit/s) |
| ic_clk | I2C module clock |
| LCNT | SCL LOW count register value |
| LPSS | Low Power SubSystem |
| MEXT | Master clock extend timeout (SMBus) |
| Mode 0 | IC_EMPTYFIFO_HOLD_MASTER_EN=0: auto-STOP on empty FIFO |
| Mode 1 | IC_EMPTYFIFO_HOLD_MASTER_EN=1: explicit STOP/RESTART control |
| NACK | Not Acknowledge: receiver leaves SDA HIGH on 9th clock |
| NVL | Novalake platform |
| PEC | Packet Error Code (SMBus CRC-8) |
| PIO | Programmed I/O (no DMA) |
| PTL | Panther Lake platform |
| RESTART | Repeated START without STOP |
| SCL | Serial Clock Line |
| SDA | Serial Data Line |
| SEXT | Slave clock extend timeout (SMBus) |
| SPKLEN | Spike suppression filter length |
| SS | Standard Speed (100 kbit/s) |
| TAR | Target Address Register |
| UDID | Unique Device Identifier (128-bit, SMBus ARP) |
| UFM | Ultra-Fast Mode (5 Mbit/s) |
| W1C | Write-1-to-Clear (write 1 to clear, write 0 has no effect) |

### 23.3 PythonSV Register Access Quick Reference

```python
# Base path for NVL PCD-H
base = nn.sv.socket0.pcd.lpss

# Access I2C instances
i2c0 = base.i2c0.cfg
i2c1 = base.i2c1.cfg
i2c2 = base.i2c2.cfg
i2c3 = base.i2c3.cfg
i2c4 = base.i2c4.cfg
i2c5 = base.i2c5.cfg

# Common operations
i2c0.IC_CON.read()               # Read IC_CON
i2c0.IC_CON.write(0x65)          # Write IC_CON
i2c0.IC_COMP_PARAM_1.read()      # Read encoded config
i2c0.IC_COMP_VERSION.read()      # Read version (expect 0x3230322A)
i2c0.IC_COMP_TYPE.read()         # Read type (expect 0x44570140)

# Verify FIFO depth
param1 = i2c0.IC_COMP_PARAM_1.read()
tx_depth = (param1 >> 16) & 0xFF  # Should be 0x3F (64) on Intel LPSS
rx_depth = (param1 >> 8) & 0xFF   # Should be 0x3F (64) on Intel LPSS
has_dma = (param1 >> 6) & 0x1     # I2C0-3: 1, I2C4-5: 0
```

---

*End of document. Source: Synopsys DW_apb_i2c Databook v2.02a (July 2018). All 338 pages digested.*
