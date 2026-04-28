# THC HIDSPI/HIDI2C Deep Study — Linux Kernel Source Analysis

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> **Date**: 2026-03-04
> **Source**: Linux kernel `drivers/hid/intel-thc-hid/` (master branch, ~March 2026)
> **Files analyzed**: 12 source files across 3 subdirectories
> **Purpose**: Identify gaps in FV-THC skill files and enrich with kernel implementation details

## 1. Files Analyzed

### intel-thc/ (core THC hardware abstraction)
| File | Lines | Key Content |
|------|-------|-------------|
| `intel-thc-hw.h` | ~600 | Register offsets, bit fields, enums, constants |
| `intel-thc-dev.h` | ~200 | Device structures, API declarations |
| `intel-thc-dev.c` | ~1200 | PIO, interrupts, SPI/I2C config, LTR, port select |
| `intel-thc-dma.c` | ~800 | DMA init/configure/read/write/SWDMA operations |
| `intel-thc-wot.c` | ~80 | Wake-on-Touch ACPI GPIO implementation |

### intel-quickspi/ (HIDSPI protocol layer)
| File | Lines | Key Content |
|------|-------|-------------|
| `quickspi-dev.h` | ~180 | PCI Device IDs, ACPI DSM GUIDs, states, packet sizes |
| `quickspi-protocol.c` | ~500 | HIDSPI protocol: descriptors, reports, reset, power |
| `quickspi-protocol.h` | ~30 | Timeout constants |
| `pci-quickspi.c` | ~700 | PCI probe, PM callbacks, ACPI config |

### intel-quicki2c/ (HIDI2C protocol layer)
| File | Lines | Key Content |
|------|-------|-------------|
| `quicki2c-dev.h` | ~200 | PCI Device IDs, ACPI methods, I2C speed modes |
| `quicki2c-protocol.c` | ~400 | HIDI2C protocol: descriptors, reports, reset, power |
| `quicki2c-protocol.h` | ~30 | API declarations |
| `pci-quicki2c.c` | ~650 | PCI probe, PM callbacks, I2C sub-IP config |

### include/linux/ (protocol definitions)
| File | Lines | Key Content |
|------|-------|-------------|
| `hid-over-spi.h` | ~120 | HIDSPI structures, report types, device descriptor |
| `hid-over-i2c.h` | ~100 | HIDI2C structures, opcodes, device descriptor |

---

## 2. HIDSPI Protocol Findings

### 2.1 ACPI Configuration — Three Separate DSM GUIDs

The Linux driver uses **three** distinct ACPI DSM GUIDs (not just one):

| GUID | Name | Functions |
|------|------|-----------|
| `{6e2ac436-0fcf-41af-a265-b32a220dcfab}` | HIDSPI DSM (Rev 2) | input_hdr_addr, input_bdy_addr, output_addr, read_opcode(BUFFER), write_opcode(BUFFER), io_mode |
| `{300d35b7-ac20-413e-8e9c-92e4dafd0afe}` | QuickSPI DSM | connection_speed, limit_packet_size, performance_limit |
| `{84005682-5b71-41a4-8d66-8130f787a138}` | Platform DSM | active_ltr_us, lp_ltr_us |

> **Gap**: HIDSPI skill only documented the first GUID. QuickSPI and Platform GUIDs are critical for validation.

### 2.2 IO Mode Flags in ACPI

The `io_mode` return from DSM Function 6 encodes:
- **Bit 13**: `SPI_WRITE_IO_MODE` — if set, write uses different IO mode than read
- **Bits [15:14]**: `SPI_IO_MODE_OPCODE` — Multi-SPI mode selection (0=Single, 1=Dual, 2=Quad)

Both read and write opcodes share `SPI_IO_MODE_OPCODE` field via FIELD_GET.

### 2.3 Device Descriptor Retrieval — PIO, Not DMA

Device descriptor is read via **PIO** (not DMA):
1. PIO write DEVICE_DESCRIPTOR command to output_report_addr
2. Wait for non-DMA interrupt (nondma_int)
3. PIO read INT_CAUSE header → validate length = HIDSPI_INPUT_DEVICE_DESCRIPTOR_SIZE
4. PIO read body from input_report_bdy_addr → validate type = DEVICE_DESCRIPTOR_RESPONSE

Report descriptor uses **TXDMA** (write_cmd_to_txdma), not PIO.

### 2.4 Reset Flow — Edge Trigger Set Twice

```
state = RESETING
set_edge_trigger(true)      ← first time
ACPI _RST method
unquiesce
wait reset_ack_wq (5s timeout)
read INT_CAUSE
validate len == 0 (empty body)
set_edge_trigger(true)      ← second time (re-arm)
PIO read body
validate type == RESET_RESPONSE
state = RESET
get_device_descriptor()
```

> **Key**: Edge trigger must be re-armed after reading INT_CAUSE. This is the fix from kernel 6.17 (`8fe2cd8`).

### 2.5 Input Data Handling (Dispatch Table)

| Input Report Type | Action |
|-------------------|--------|
| DATA | Validate state==ENABLED, check len ≤ max_input_len, send to HID core |
| REPORT_DESCRIPTOR_RESPONSE | Copy to report_descriptor buffer, wake report_desc_got_wq |
| COMMAND_RESPONSE | Validate content_id == SET_POWER_CMD_ID |
| RESET_RESPONSE | If state==RESETING: set reset_ack + wake; else log as DIR |
| GET_FEATURE_RESPONSE | Copy content_id+content to report_buf, wake get_report_cmpl_wq |
| GET_INPUT_REPORT_RESPONSE | Same as GET_FEATURE_RESPONSE |
| SET_FEATURE_RESPONSE | Wake set_report_cmpl_wq |
| OUTPUT_REPORT_RESPONSE | Wake set_report_cmpl_wq |

### 2.6 Packet Size Logic

| Condition | Packet Size |
|-----------|-------------|
| `limit_packet_size == true` OR no driver_data | DEFAULT_MIN = 4 (64 bytes) |
| MTL / ARL | MAX = 128 (2KB) |
| LNL / PTL / WCL | MAX = 256 (4KB) |

### 2.7 SPI CS Assertion Delay

Port selection enables CS assertion delay:
- `SPI_CSA_CK_DELAY_EN` = 1
- Default value = `THC_CSA_CK_DELAY_VAL_DEFAULT` (4)

This adds delay between CS# assertion and first SPI clock edge — critical for device setup time.

### 2.8 Driver States (SPI)

```
QUICKSPI_NONE → QUICKSPI_INITIATED → QUICKSPI_RESETING → QUICKSPI_RESET → QUICKSPI_ENABLED → QUICKSPI_DISABLED
```

### 2.9 PCI Device IDs (SPI)

| Platform | THC0 | THC1 |
|----------|------|------|
| MTL | 0x7E49 | 0x7E4B |
| LNL | 0xA849 | 0xA84B |
| PTL-H | 0xE349 | 0xE34B |
| PTL-U | 0xE449 | 0xE44B |
| WCL | 0x4D49 | 0x4D4B |
| ARL | 0x7749 | 0x774B |

> **Note**: No NVL SPI Device IDs in kernel yet.

---

## 3. HIDI2C Protocol Findings

### 3.1 Command Encoding (16-bit)

```
Bits [3:0]   = report_id (0x0F sentinel if ≥ 15)
Bits [5:4]   = report_type (0=RESERVED, 1=INPUT, 2=OUTPUT, 3=FEATURE)
Bits [7:6]   = reserved
Bits [11:8]  = opcode (1=RESET, 2=GET_REPORT, ..., 8=SET_POWER)
Bits [15:12] = reserved
Optional 3rd byte [23:16] = actual report_id when sentinel used
```

### 3.2 Power State Values — Different from HIDSPI!

| Protocol | ON | SLEEP | OFF |
|----------|-----|-------|-----|
| HIDSPI | 1 | 2 | 3 |
| HIDI2C | 0 | 1 | N/A |

> **Critical**: SET_POWER value encoding is **protocol-specific**. Test scripts must use correct values per protocol.

### 3.3 SWDMA Usage in I2C — Extensive

| Operation | Mechanism | Notes |
|-----------|-----------|-------|
| Device Descriptor | PIO write+read | thc_tic_pio_write_and_read() |
| Report Descriptor | **SWDMA** | desc_reg as write data → SWDMA read |
| GET_REPORT | **SWDMA** | cmd+data_reg → SWDMA combined write+read |
| SET_REPORT | TXDMA | write_cmd_to_txdma() |
| Output Report | TXDMA | Direct to output_reg (no command prefix) |
| SET_POWER | TXDMA | power_state in report_id field |
| RESET | TXDMA | Wait 5s for reset_ack |

> **Gap**: HIDI2C skill listed SWDMA for report descriptor but not for GET_REPORT. DMA skill SWDMA matrix needs update.

### 3.4 Output Report — No Command Prefix

I2C output reports write **directly** to output_reg:
```
[output_reg(2B)] [length(2B)] [data...]
```
No command register prefix — this is different from SET_REPORT which goes through cmd_reg.

### 3.5 Reset Protocol — 5-Second Timeout

1. Send RESET via TXDMA to cmd_reg
2. Wait 5 seconds for reset_ack interrupt
3. If no ack: manually PIO read from input_reg
4. Valid reset = packet with length == 0 (0x0000 sentinel)
5. After reset: device in ON state

### 3.6 I2C Register Reuse from SPI

Two SPI registers are **repurposed** for I2C mode:
| SPI Register | I2C Usage | Field |
|-------------|-----------|-------|
| `SPI_ICRRD_OPCODE` | I2C max RX frame size | I2C_MAX_SIZE + I2C_MAX_SIZE_EN |
| `SPI_DMARD_OPCODE` | I2C RX interrupt delay | I2C_INT_DELAY + I2C_INT_DELAY_EN |

> PTL+ only: Enabled via ACPI ISUB method (FSEN/FSVL for max size, INDE/INDV for delay).

### 3.7 PTL Advanced I2C Features

| Feature | ACPI Field | Register | Effect |
|---------|-----------|----------|--------|
| Max RX detect size | FSEN + FSVL | SPI_ICRRD_OPCODE | Caps max DMA read to min(device_max, FSVL) |
| RX interrupt delay | INDE + INDV | SPI_DMARD_OPCODE | INDV × 10µs delay between INT and DMA start |

Defaults: MAX_RX_DETECT_SIZE = 255 bytes, MAX_RX_INTERRUPT_DELAY = 256 (2.56ms), DEFAULT_INT_DELAY = 1ms.

### 3.8 I2C Sub-IP Init — Full Sequence from Kernel

```
1. IC_ENABLE = 0              (disable)
2. IC_CON = 0x0663            (Master, Fast, 7-bit, RestartEN, SlaveDIS)
3. IC_TAR = device_address    (from ACPI)
4. IC_xS_SCL_HCNT/LCNT       (speed-dependent)
5. IC_INTR_MASK = 0x7FFF      (all interrupts masked)
6. IC_RX_TL = 62              (RX threshold)
7. IC_TX_TL = 0               (TX threshold)
8. IC_DMA_CR = RDMAE|TDMAE    (both DMA enables)
9. IC_DMA_TDLR = 7            (TX DMA data level)
10. IC_DMA_RDLR = 7           (RX DMA data level)
11. IC_ENABLE = 1             (enable)
```

> **Gap**: Skill file had 13 steps with IC_SDA_HOLD. Kernel uses 11 steps without IC_SDA_HOLD in init — but IC_SDA_HOLD IS in the save/restore list.

### 3.9 I2C Sub-IP Save/Restore — Corrected List from Kernel

The kernel saves/restores these 15 registers (order matters):
```
IC_CON, IC_TAR, IC_INTR_MASK, IC_RX_TL, IC_TX_TL, IC_DMA_CR,
IC_DMA_TDLR, IC_DMA_RDLR, IC_SS_SCL_HCNT, IC_SS_SCL_LCNT,
IC_FS_SCL_HCNT, IC_FS_SCL_LCNT, IC_HS_SCL_HCNT, IC_HS_SCL_LCNT,
IC_ENABLE
```

> **Difference from skill file**: Skill lists IC_SAR and IC_SDA_HOLD/IC_SDA_SETUP. Kernel does NOT save IC_SAR, IC_SDA_HOLD, or IC_SDA_SETUP — but DOES save IC_HS_SCL_HCNT/LCNT.

### 3.10 I2C Interrupt Bits (THC_M_PRT_INT_EN bits 17-27)

| Bit | Name | In INT_EN | In INT_STS |
|-----|------|-----------|------------|
| 17 | RX_UNDER | Yes | Yes |
| 18 | RX_OVER | Yes | Yes |
| 19 | RX_FULL | Yes | Yes |
| 20 | TX_OVER | Yes | Yes |
| 21 | TX_EMPTY | Yes | Yes |
| 22 | TX_ABRT | Yes | Yes |
| 23 | ACTIVITY | **No** | Yes |
| 24 | SCL_STUCK | Yes | Yes |
| 25 | STOP_DET | Yes | Yes |
| 26 | START_DET | Yes | Yes |
| 27 | MST_ON_HOLD | Yes | Yes |

> **Asymmetry**: ACTIVITY(23) is readable in status but NOT configurable in enable register.

### 3.11 PCI Device IDs (I2C)

| Platform | THC0 | THC1 |
|----------|------|------|
| LNL | 0xA848 | 0xA84A |
| PTL-H | 0xE348 | 0xE34A |
| PTL-U | 0xE448 | 0xE44A |
| WCL | 0x4D48 | 0x4D4A |

> **Note**: No MTL/ARL I2C (I2C added in Gen4.0 LNL). No NVL I2C Device IDs in kernel yet.

### 3.12 Driver States (I2C)

```
QUICKI2C_NONE → QUICKI2C_RESETING → QUICKI2C_RESETED → QUICKI2C_INITED → QUICKI2C_ENABLED → QUICKI2C_DISABLED
```

---

## 4. DMA Architecture Findings

### 4.1 DMA Configure — RXDMA2 Auto-Started, Not RXDMA1

During `thc_dma_configure()`:
- RXDMA2: START bit set immediately
- RXDMA1: **NOT** auto-started — started later by protocol layer
- SWDMA: Not configured during init

### 4.2 TXDMA — Single PRD Table Only

- TXDMA uses exactly 1 PRD table (not a ring)
- RXDMA1/2 use `PRD_TABLES_NUM` tables in circular ring
- SWDMA uses 1 PRD table

### 4.3 SWDMA 14-Step Sequence (from kernel)

```
1.  Set thc_dev->swdma_active = true
2.  Quiesce device interrupts
3.  Pause RXDMA1 (if active)
4.  Pause RXDMA2
5.  Reset SWDMA (thc_dma_set_max_packet_sizes with swdma)
6.  Allocate SWDMA PRD buffers
7.  Configure SWDMA (PRD base, control, packet sizes)
8.  Disable I2C sub-IP features temporarily
9.  Program SWDMA write data + byte count
10. Set SWDMA START → wait for completion interrupt
11. Read response data from SWDMA PRD buffers
12. Pause SWDMA
13. Restart RXDMA2
14. Unquiesce → set thc_dev->swdma_active = false
```

### 4.4 Performance Limit Delay

After TXDMA write, driver inserts delay: `perf_limit × 10µs`
- `perf_limit` comes from ACPI QuickSPI DSM `performance_limit` field
- Only applies to SPI mode

### 4.5 DMA Read — One Frame Per Call

`thc_dma_read()` reads **one frame per call**:
- Returns `read_finished = true` when all data consumed
- Caller must loop until `read_finished == true`
- Each call advances TPCRP by one

### 4.6 ARB_POLICY Values

| Value | Name | Description |
|-------|------|-------------|
| 0 | PACKET_BOUNDARY | Arbitrate at packet boundaries |
| 1 | UFRAME_BOUNDARY | Arbitrate at microframe boundaries |
| 2 | FRAME_BOUNDARY | Arbitrate at frame boundaries |

I2C mode uses FRAME_BOUNDARY (set during port_select).

### 4.7 MPS Alignment

All MPS values aligned to 4KB: `ALIGN(size, SZ_4K)` — not just the I2C MPS workaround.

---

## 5. Register Findings

### 5.1 New Registers Not in Skills (from hw.h)

| Offset | Register | Purpose |
|--------|----------|---------|
| 0x1300 | `THC_M_PRT_SPI_DUTYC_CFG` | SPI duty cycle + CS assertion delay (default=4) |
| 0x1304 | `THC_M_PRT_SW_SEQ_I2C_WR_CNTRL` | I2C write sequencing for PIO write+read |
| 0x1308 | `THC_M_PRT_TIMESTAMP_1` | Per-RXDMA1 timestamp |
| 0x130C | `THC_M_PRT_TIMESTAMP_2` | Per-RXDMA2 timestamp |
| 0x1310 | `THC_M_PRT_SYNC_TIMESTAMP` | Display sync event timestamp |
| 0x1314 | `THC_M_PRT_DISP_SYNC` | Display sync config 1 |
| 0x1318 | `THC_M_PRT_DISP_SYNC_2` | Display sync config 2 |
| 0x131C | `THC_M_PRT_I2C_CFG` | I2C configuration register |
| 0x12E4 | `THC_M_PRT_SW_DMA_PRD_TABLE_LEN` | SW DMA PRD table length |
| 0x12E8 | `THC_M_PRT_COALESCE_CNTRL_1` | Timing-based coalescing control ch1 |
| 0x12EC | `THC_M_PRT_COALESCE_CNTRL_2` | Timing-based coalescing control ch2 |
| 0x12F0 | `THC_M_PRT_PRD_EMPTY_CNT_1` | PRD table empty counter ch1 |
| 0x12F4 | `THC_M_PRT_PRD_EMPTY_CNT_2` | PRD table empty counter ch2 |
| 0x12F8 | `THC_M_PRT_COALESCE_STS_1` | Coalescing FSM state ch1 |
| 0x12FC | `THC_M_PRT_COALESCE_STS_2` | Coalescing FSM state ch2 |

### 5.2 DEVINT_CFG Bit Fields (Detailed)

**DEVINT_CFG_1** (offset 0x1000):
| Bits | Field | Description |
|------|-------|-------------|
| [4:0] | INTTYP_OFFSET | INT_CAUSE type field offset in ICR |
| [9:5] | INTTYP_LEN | INT_CAUSE type field length |
| [14:10] | EOF_OFFSET | End-of-frame bit offset in ICR |
| [15] | SEND_ICR_US_EN | Embed ICR in PRD data |
| [31:16] | INTTYP_DATA_VAL | Expected INT_CAUSE data value |

**DEVINT_CFG_2** (offset 0x1004):
| Bits | Field | Description |
|------|-------|-------------|
| [4:0] | UFSIZE_OFFSET | Microframe size field offset |
| [9:5] | UFSIZE_LEN | Microframe size field length |
| [14:10] | UFSIZE_UNIT | Microframe size unit |
| [16] | FTYPE_IGNORE | Ignore frame type in routing |
| [17] | FTYPE_VAL | Expected frame type value |
| [24] | RXDMA_ADDRINC_DIS | Disable RXDMA address increment |
| [25] | TXDMA_ADDRINC_DIS | Disable TXDMA address increment |
| [26] | RXDMA_PKT_STRM_EN | Enable RX streaming mode |
| [27] | TXDMA_PKT_STRM_EN | Enable TX streaming mode |
| [28] | DEVINT_POL | Device interrupt polarity |

### 5.3 Regmap Configuration

```
Common range: 0x10 - 0x14 (2 registers)
MMIO range:   0x1000 - 0x1320 (full port register space)
Access:       32-bit register/value, stride=4
Cache:        REGCACHE_NONE (no caching)
I/O:          fast_io = true (no mutex for regmap access)
Max register: 0x1320
```

### 5.4 Interrupt Handler Priority Order

```
1. NonDMA (device inband interrupt)
2. TXN_ERR (transaction error)
3. BUF_OVRRUN / STALL (buffer overrun or stall)
4. FATAL_ERR (fatal error)
5. PIO_DONE (PIO sequence complete)
6. RXDMA1 (legacy data channel)
7. RXDMA2 (HID input channel)
8. SWDMA (software DMA complete)
9. TXDMA (write DMA complete)
10. I2CSUBIP (I2C sub-IP interrupt)
11. UNKNOWN (unexpected — error)
```

### 5.5 Counters Cleared by thc_clear_state()

All performance/debug counters reset during clear_state:
```
DB_CNT_1, DEVINT_CNT, TPCPR, FRAME_DROP_CNT_1/2, FRM_CNT_1/2,
RXDMA_PKT_CNT_1/2, SWINT_CNT_1, TX_FRM_CNT, TXDMA_PKT_CNT,
UFRM_CNT_1/2, PRD_EMPTY_CNT_1/2
```

---

## 6. Power Management Findings

### 6.1 PM Callback Comparison: SPI vs I2C

| Callback | SPI (QuickSPI) | I2C (QuickI2C) |
|----------|----------------|-----------------|
| **suspend** | SET_POWER(SLEEP) → quiesce → disable_int → dma_unconfigure | save_i2c_subip_regs → (skip SET_POWER if wakeup) → quiesce → disable_int → dma_unconfigure |
| **resume** | port_select(SPI) → int_config → int_enable → dma_configure → unquiesce → SET_POWER(ON) | port_select(I2C) → i2c_subip_regs_restore → int_config → int_enable → dma_configure → unquiesce → (SET_POWER(ON) if !wakeup) |
| **freeze** | quiesce → disable_int → dma_unconfigure (no SET_POWER) | Same as SPI |
| **thaw** | dma_configure → int_enable → unquiesce (no SET_POWER) | Same as SPI |
| **poweroff** | quiesce → disable_int → ltr_unconfig → dma_deinit (full teardown) | SET_POWER(SLEEP) → quiesce → disable_int → ltr_unconfig → dma_deinit |
| **restore** | quiesce → port_select → SPI full reconfig → reset_tic → dma_configure → ltr_config → ENABLED | port_select → i2c_subip_init (FULL reinit) → int_config → int_enable → dma_configure → ltr_config → SET_POWER(ON) (NO reset_tic) |
| **runtime_suspend** | ltr_mode(LP) → pci_save_state | Same |
| **runtime_resume** | ltr_mode(ACTIVE) | Same |

### 6.2 Key PM Differences

1. **I2C ALWAYS saves subip regs** on suspend — even with WoT enabled. Because I2C sub-IP is in PGD (power-gated during D3).
2. **I2C restore uses FULL i2c_subip_init()** — not just register restore. Because hibernate loses all context.
3. **SPI restore does reset_tic** (full device reset). I2C restore does NOT reset — just reinit and SET_POWER(ON).
4. **I2C poweroff sends SET_POWER(SLEEP)** before teardown. SPI poweroff does NOT send SET_POWER.
5. **I2C suspend skips SET_POWER(SLEEP) if device_may_wakeup** — WoT requires device to stay active.

### 6.3 Runtime PM Timeouts

| Protocol | Auto-Suspend Delay |
|----------|-------------------|
| SPI (QuickSPI) | 5000ms |
| I2C (QuickI2C) | 500ms |

### 6.4 WoT Implementation Details

- Uses ACPI `wake-on-touch` GPIO resource (separate from main touch interrupt GPIO)
- GPIO mapping registered via `acpi_dev_add_driver_gpios()`
- Non-fatal: only `dev_warn` on failures — doesn't impact main touch function
- `device_init_wakeup(true)` + `dev_pm_set_dedicated_wake_irq(gpio_irq)`
- Copyright 2025 — newer implementation than other files

### 6.5 LTR Scale Selection (Kernel Implementation)

```c
if (latency_us >= 33554432)  → scale_5, value >>= 15
else if (>= 1048576)         → scale_4, value >>= 10
else if (>= 32768)           → scale_3, value >>= 5
else                          → scale_2 (× 1024 ns)
```

Geometric progression: each scale = 2^(5×n) nanoseconds.

---

## 7. Probe Sequence Comparison

### SPI Probe Order
```
1. pcim_enable → pci_set_master → iomap BAR0 → DMA mask
2. alloc_irq_vectors (MSI)
3. dev_init: quiesce → port_select(SPI) → ACPI DSM → SPI addr config → SPI read/write config → LTR config → interrupt config → enable → WoT config
4. request_threaded_irq (IRQF_ONESHOT)
5. reset_tic (ACPI _RST + wait for RESET_RESPONSE)
6. alloc_report_buf
7. dma_init: set_max_packet_sizes → allocate → configure
8. get_report_descriptor
9. hid_probe (register with HID core)
10. state = ENABLED
11. pm_runtime_set_autosuspend_delay(5000ms)
```

### I2C Probe Order (Key Differences)
```
1-2. Same as SPI
3. dev_init: quiesce → ACPI (ICRS + ISUB) → port_select(I2C) → i2c_subip_init → int_trigger(LEVEL) → int_config → int_enable → WoT
4. request_threaded_irq
5. get_device_descriptor (PIO — BEFORE DMA init!)
6. alloc_report_buf
7. dma_init: set_max_sizes (with SWDMA!) → allocate → configure → adv_features
8. unquiesce → SET_POWER(ON)
9. reset_tic
10. get_report_descriptor (via SWDMA)
11. hid_probe
12. pm_runtime_set_autosuspend_delay(500ms)
```

> **Critical difference**: I2C gets device descriptor BEFORE DMA init (needs PIO first). SPI resets BEFORE device descriptor.

---

## 8. Gap Analysis — Findings vs Current Skill Files

### hidspi/SKILL.md Gaps — ✅ ALL INTEGRATED (2026-03-04)
- [x] Three ACPI DSM GUIDs (only first documented)
- [x] IO mode flag parsing (SPI_WRITE_IO_MODE, SPI_IO_MODE_OPCODE)
- [x] Device descriptor via PIO (not DMA) — report descriptor via TXDMA
- [x] Reset flow double edge-trigger detail
- [x] Input data dispatch table
- [x] Packet size per platform (MTL=2KB, LNL+=4KB)
- [x] CS assertion delay mechanism
- [x] Driver states
- [x] PCI Device IDs
- [x] Auto-suspend timeout (5000ms)

### hidi2c/SKILL.md Gaps — ✅ ALL INTEGRATED (2026-03-04)
- [x] Command encoding bit field layout
- [x] Power state values differ from HIDSPI (ON=0, SLEEP=1)
- [x] SWDMA for GET_REPORT (not just report descriptor)
- [x] Output report: no command prefix, direct to output_reg
- [x] SPI register reuse for I2C (ICRRD_OPCODE → max_size, DMARD_OPCODE → int_delay)
- [x] PTL advanced features (max_detect_size, interrupt_delay)
- [x] I2C sub-IP init: kernel uses 11 steps (not 13)
- [x] Save/restore list correction (kernel differs from skill)
- [x] I2C interrupt bit detail (bits 17-27, ACTIVITY asymmetry)
- [x] PCI Device IDs
- [x] ACPI ICRS + ISUB methods
- [x] Probe order (dev_desc before DMA)
- [x] Auto-suspend timeout (500ms)

### dma/SKILL.md Gaps — ✅ ALL INTEGRATED (2026-03-04)
- [x] RXDMA2 auto-started, not RXDMA1
- [x] TXDMA single PRD table only
- [x] SWDMA full 14-step sequence
- [x] perf_limit delay after TXDMA
- [x] DMA read: one frame per call
- [x] ARB_POLICY values
- [x] MPS 4KB alignment
- [x] SWDMA usage for I2C GET_REPORT (matrix update)

### registers/SKILL.md Gaps — ✅ ALL INTEGRATED (2026-03-04)
- [x] 15 new register offsets (0x12E4-0x131C)
- [x] DEVINT_CFG_1/2 bit field details
- [x] Regmap config (ranges, stride, cache)
- [x] Interrupt handler priority order
- [x] Counter clear list

### power/SKILL.md Gaps — ✅ ALL INTEGRATED (2026-03-04)
- [x] PM callback SPI vs I2C comparison table
- [x] Key PM differences (5 points)
- [x] Runtime PM timeouts per protocol
- [x] WoT: dedicated GPIO, ACPI 'wake-on-touch' key
- [x] LTR scale selection algorithm

---

## 9. SwAS Cross-Reference (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0. This section documents where the Software Architecture Specifications confirm, supplement, or conflict with the kernel source findings above.

### 9.1 Reset Timeout Discrepancy: SwAS vs Kernel

| Protocol | SwAS Timeout | Kernel Timeout | Discrepancy |
|----------|-------------|----------------|-------------|
| SPI (QuickSPI) | **1 second** (P0341) | **5 seconds** | Kernel is 5× more conservative |
| I2C (QuickI2C) | **5 seconds** (P0479) | **5 seconds** | Match |

**Analysis**: The kernel uses 5s for both protocols, matching the I2C SwAS but exceeding the SPI SwAS by 4 seconds. This is a deliberate conservative choice by the Linux maintainers — slow devices may need extra time, and 5s is a safe upper bound. Windows SwAS explicitly specifies 1s for SPI.

### 9.2 WCL Device IDs — Confirmed by Both SwAS and Kernel

| Source | HIDSPI THC0 | HIDSPI THC1 | HIDI2C THC0 | HIDI2C THC1 |
|--------|-------------|-------------|-------------|-------------|
| Kernel (Section 2.9, 3.11) | 0x4D49 | 0x4D4B | 0x4D48 | 0x4D4A |
| QuickI2C SwAS T4 | — | — | 0x4D48 | 0x4D4A |
| QuickSPI SwAS T5 | Not listed | Not listed | — | — |

**Note**: WCL SPI DIDs appear in kernel but NOT in QuickSPI SwAS DID table (T5). WCL I2C DIDs confirmed in both kernel and QuickI2C SwAS. All WCL DIDs are in the `0x4D48-0x4D4B` range (NOT `0x57xx`).

### 9.3 Edge Detection Fix — SwAS Documents Root Cause

The kernel edge detection fix (Section 2.4, commit `8fe2cd8` kernel 6.17) aligns with **SwAS P0582**:
- SwAS documents the pre-LNL double interrupt processing bug as a known issue
- SwAS workaround: level-triggered for first interrupt → edge after reset
- Kernel fix: re-arms edge trigger after reading INT_CAUSE (same approach)

### 9.4 Quiesce Scenarios — SwAS Adds Context Missing from Kernel

The kernel `thc_interrupt_quiesce()` function is called in several contexts. The SwAS documents **4 specific quiesce scenarios** not explicitly enumerated in kernel comments:
1. During host-initiated reset
2. Buffer threshold at 8 free buffers (half of 16)
3. D0Exit before D3 transition
4. NOT within ISR/DPC context

Scenario 2 (buffer threshold throttling) is a Windows-specific optimization — the Linux kernel does not implement buffer-count-based quiesce.

### 9.5 Unused Error Paths — SwAS Confirms Kernel Behavior

The kernel interrupt handler (Section 5.4) lists FATAL_ERR at priority 4, but the SwAS (P0635-P0637 for SPI; P0753-P0756 for I2C) confirms these are **unused**:
- Write DMA Errors: not implemented by SW or HW
- Fatal Errors: not implemented
- PIO Errors (I2C only): not implemented
- I2C Sub-IP Errors: not implemented

This means the kernel's interrupt handler paths for these categories are defensive code that should never execute in normal operation.

### 9.6 I2C IC_DMA_RDLR ≤ 7 — SwAS Explains Kernel Value

The kernel sets `IC_DMA_RDLR = 7` (Section 3.8, step 10). The QuickI2C SwAS (P0350-P0356) explains why: the THC internal temp buffer can store max 8 bytes. Setting `IC_DMA_RDLR > 7` causes buffer overflow. The kernel value of 7 is the **maximum safe value**.

### 9.7 Bus Clear — Linux Does NOT Enable

The QuickI2C SwAS (P0771) documents that THC supports SDA/SCL stuck bus clear recovery. The kernel source confirms Linux does NOT enable this feature. Windows enables it. This is a potential Linux robustness gap for I2C deployments.

### 9.8 Kernel Changes Summary (6.17–6.20) with SwAS Context

| Kernel | Change | SwAS Cross-Reference |
|--------|--------|---------------------|
| 6.17 | Edge detection fix (8fe2cd8) | P0582: pre-LNL double interrupt workaround |
| 6.17 | WoT support added | P0706-P0726 (SPI WoT), P0823-P0851 (I2C WoT) |
| 6.18 | WCL Device IDs | SwAS T4 confirms 0x4D48-0x4D4A (I2C) |
| 6.19 | ARL Device IDs | Not in SwAS DID tables |
| 6.19 | DMA safety improvements | Aligns with SwAS quiesce/throttle guidance |
| 6.20 | I2C register save fix (a7fc15e) | I2C Sub-IP in PGD — must save on every D3 |
| 6.20 | QuickI2C output reports | Output report path via TXDMA (no cmd prefix) |
