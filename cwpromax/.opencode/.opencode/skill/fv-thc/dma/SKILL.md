---
name: fv-thc/dma
description: THC DMA architecture — PRD ring, RXDMA/TXDMA/SWDMA, streaming mode, burst mode, display sync, timestamps, buffer overrun
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC DMA Architecture Reference

Complete DMA engine documentation for THC including PRD descriptor rings, all DMA channels, streaming/burst modes, display synchronization, timestamps, and buffer management.

**Platform-specific implementation details: see [linux.md](linux.md) and [windows.md](windows.md)**

## PRD (Physical Region Descriptor) Table Structure

- **Write DMA (TXDMA)**: Single PRD table for host-to-device transfers
- **Read DMA (RXDMA)**: Up to **128 PRD tables** in a circular ring buffer (HW max); **SwAS recommends up to 64** (SW policy limit)
  > **⚠️ 64 vs 128 discrepancy**: THC IP HAS documents HW max of 128 PRD tables. QuickSPI/QuickI2C SwAS v1.0 states "up to 64 PRD tables". The SwAS figure is the **SW policy limit** (validated/supported by drivers); HW supports up to 128 but is not tested/qualified beyond 64. Linux kernel uses 16 (conservative).
- **Each PRD table**: Up to **256 entries** (PRDs) (HW max). Note: the PTEC register uses N-1 encoding, so the max register value is **255 (0xFF)** representing 256 entries.
- **PRD entry**: 128-bit (16 bytes)
- **Fragmentation boundary**: 4KB — DMA transfers crossing 4KB must be split
- **Max PRD table length**: Up to 16MB
- **⚠️ PRD RTL Bug**: Non-last PRD entries must be **multiple of 4KB** (min 4KB, max 1MB). Last entry should also be 4KB aligned due to RTL bug (HAS-confirmed workaround).

### PRD Entry Format (128 bits)
```
Bits [53:0]   — DestinationAddress (physical address >> 10, 1KB aligned)
Bits [63]     — IOC (Interrupt on Completion)
Bits [87:64]  — Length (transfer size in bytes)
Bits [88]     — EndOfPRD (last entry in this PRD table)
Bits [90:89]  — HWStatus (written by THC DMA engine)
Bits [127:91] — Reserved
```

### Circular Buffer Management
- `POINTER_MASK = 0x7F` — lower 7 bits = table index (0–15 for 16-slot ring)
- `POINTER_WRAPAROUND = 0x80` — bit 7 = phase/generation bit
- TPCWP == TPCRP → ring empty
- **Pointer role assignment differs by platform** — see cross-platform table below and [linux.md](linux.md) / [windows.md](windows.md)

### Cross-Platform Quick-Reference

| Aspect | Linux Kernel | Windows Driver |
|--------|-------------|----------------|
| **Write pointer (TPCWP)** | Managed by **SW** (`dma_set_write_pointer`) | Advanced by **HW** |
| **Read pointer (TPCRP)** | Managed by **HW** (`dma_get_read_pointer`) | Advanced by **SW** |
| **PRD entries per table** | 16 (`PRD_ENTRIES_NUM`) | 255 (`MAX_PRD_ENTRIES = 0xFF`) |
| **PRD tables in ring** | 16 (`PRD_TABLES_NUM`) | Dynamic (up to HW max) |
| **DMA pause poll interval** | 100 µs | 10 µs |
| **DMA pause total timeout** | 10 ms | 1 s |
| **TXDMA/SWDMA completion timeout** | 1 s (`1*HZ`) | 500 ms |
| **Wrap constant (16-index)** | `THC_WRAPAROUND_VALUE_16 = 0x10` (with `THC_` prefix) | `WRAPAROUND_VALUE_16 = 0x10` (no `THC_` prefix) |
| **Wrap constant (0x90)** | `THC_WRAPAROUND_VALUE_0X90 = 0x90` (with `THC_` prefix) | `WRAPAROUND_VALUE_0X90 = 0x90` (no `THC_` prefix) |
| **SWDMA save/restore** | Selective: `rx_max_size` + `int_delay` only | Full `DmaUnconfigure` + `DmaConfigure` cycle |
| **DMA buffer allocation** | `dma_alloc_coherent()` / `dma_free_coherent()` | `WdfCommonBufferCreate()` / `WdfObjectDelete()` |
| **Fatal error recovery** | `thc_dma_unconfigure()` + `thc_dma_configure()` | Full device reset via `DeviceD0Exit()` → `DeviceD0Entry()` |
| **DMA max size cap** | No explicit cap | 1 MB maximum per buffer |
| **RXDMA1 buffer sizing** | Not used for I2C | Full-size (same as RXDMA2) |
| **Read1 vs Read2 sizing** | HIDSPI: Read1 adds `sizeof(INPUT_REPORT_HEADER)` | HIDI2C: Identical formulas for Read1 and Read2 |

### PRD Ring Initialization Rules (from SwAS)

1. **Write pointer init**: Set `TPCWP = 0x80` (`POINTER_WRAPAROUND`) — the wraparound/phase bit signals the DMA engine that the full ring is available. Note: PRD entry count is encoded as `PRD_ENTRIES_NUM - 1` (e.g., 15 for 16 entries) and cb_depth as `prd_tbl_num - 1` (15) — 0-based encoding.
2. **Unused PRD entries**: Initialize all unused PRD entry fields to `0x00`. This enables **frame babble detection** — the DMA engine can detect spurious data in uninitialized entries. *(QuickSPI SwAS v1.0)*
3. **PRD entry length reset after consumption**: After the driver reads a completed DMA frame, it **MUST reset the PRD entry's length field back to the original allocated buffer size** before re-arming the entry for the next DMA cycle. Failure to do this causes subsequent DMA transfers to use the stale (consumed) length. *(QuickSPI SwAS v1.0)*
4. **Buffer allocation timing**: DMA buffers should be allocated **immediately after device descriptor read** (not deferred). The descriptor provides the max report size needed for buffer sizing. *(QuickSPI SwAS v1.0)*

> **Validation point**: Verify all three initialization rules in test scripts — especially rule 3 (length reset), which is a common source of data corruption if missed.

## DMA Channel Configuration

| Channel | Purpose | PRD Tables | Auto-Start |
|---------|---------|------------|------------|
| RXDMA1 | Legacy/IPTS raw data | Up to 16 (ring) | No — manual start only |
| RXDMA2 | HID input reports | Up to 16 (ring) | **Yes** — auto-started during DMA configure |
| TXDMA | Host-to-device writes | **1** (no ring) | No — started per-write |
| SWDMA | SW-triggered reads (Gen4.0+) | **1** (no ring) | No — started per-operation |

> **Key insight (from kernel)**: Only RXDMA2 is auto-started during DMA configure. RXDMA1 is allocated and configured but NOT started — it must be explicitly started if IPTS/raw data path is needed. TXDMA and SWDMA have only 1 PRD table (no circular ring buffer). Platform-specific PRD entry counts: Linux uses 16, Windows uses up to 255 (0xFF) with dynamic sizing.

> **TXDMA architecture contrast (SwAS)**: TXDMA is a **single-PRD, single-buffer, write-and-done** engine — the driver fills one PRD entry, triggers the write, and waits for completion before reusing the buffer. This is fundamentally different from RXDMA2's **circular 16-table ring** that auto-advances through PRD tables continuously. TXDMA has no ring pointer advancement, no wrap-around logic, and no throttle mechanism. Each TXDMA operation is a discrete one-shot transfer.

### RXDMA2 Software Throttle

RXDMA2 implements a software throttle mechanism to prevent ring buffer overrun:

- **Throttle threshold**: **8** — when the number of unprocessed PRD entries reaches this count, the driver throttles incoming DMA
- **Reset/power-down guard**: Throttle threshold check includes guard against reset and power-down states to prevent false throttle during transitions
- **Purpose**: Provides backpressure when the host is not consuming touch reports fast enough
- **Behavior**: When throttled, new incoming frames may be dropped (counted in `frame_drop_cnt_2`) rather than overwriting unread data

> Platform-specific throttle constant naming: see [windows.md](windows.md) (`RXDMA2_THROTLE_THRESHOLD = 8`).

### Key DMA Registers

| Register | Offset | Purpose |
|----------|--------|---------|
| `THC_M_PRT_WPRD_BA_LOW/HI` | 0x090/0x094 | Write DMA PRD base address |
| `THC_M_PRT_WRITE_DMA_CNTRL` | 0x098 | Write DMA control (START, IOC) |
| `THC_M_PRT_WRITE_DMA_INT_STS` | 0x09C | Write DMA interrupt status |
| RXDMA1 register set | 0x100–0x1B8 | Read DMA channel 1 |
| RXDMA2 register set | 0x200–0x2B8 | Read DMA channel 2 |
| SWDMA register set | 0x2C0–0x2E4 | Software DMA (LNL+) |

## SWDMA Engine (Gen4.0+ / LNL-M+)

Debug DMA engine with same capacity as RXDMA1/2 but **ignores INT_CAUSE frame type** — captures all frames.

- **Trigger**: CPU-initiated (not device-interrupt-driven like RXDMA)
- **Synchronous**: Driver sets START bit, then waits for `INT_STS.SWDMA_DONE` completion interrupt
- **Exclusive access**: Requires RXDMA1/RXDMA2 paused before use (see SWDMA Workflow below)

**SWDMA Command Register Length**: The write-byte-count field for the SWDMA command register is `0x02` (2 bytes). This is the standard HIDI2C command register payload size used in all SWDMA write-read transactions (e.g., GET_REPORT, descriptor reads).

**Key SWDMA Registers**:
- `THC_M_PRT_SW_DMA_PRD_TABLE_LEN`: PRD table length (up to 16MB)
- `THC_M_PRT_RPRD_BA_LOW/HI_SW`: PRD ring base address
- `THC_M_PRT_RPRD_CNTRL_SW`: PTEC, PCD, PREFETCH_WM
- `THC_M_PRT_READ_DMA_CNTRL_SW`: START, TPCPR, UHS, TPCWP, TPCRP, IE_DMACPL, IOC

**SWDMA CB initialization**: During START, set write pointer `TPCWP = 0x80` (POINTER_WRAPAROUND, indicating single buffer available). During reset, set `TPCPR = 1` to advance past completed entry. This matches the single-PRD single-buffer nature of SWDMA.

### SWDMA Usage Matrix

| Operation | Windows HIDI2C | Windows HIDSPI | Linux I2C | Linux SPI |
|-----------|---------------|----------------|-----------|-----------|
| GET_FEATURE | **SWDMA** | TX DMA + PendingQueue | **SWDMA** | Protocol msg |
| GET_INPUT_REPORT | **SWDMA** | TX DMA + PendingQueue | **SWDMA** | Protocol msg |
| Report descriptor | **SWDMA** (RX_DLEN_EN=0) | TX DMA → async RX | **SWDMA** | Protocol msg |
| Device descriptor | PIO (0x14) | PIO (0x02/0x04) | PIO | PIO |

> **Key insight**: SWDMA requires exclusive DMA access — RXDMA must be paused first. This creates a window where touch input is NOT received.

### The SWDMA vs RxDMA Race Condition

There is a critical architectural race condition between SWDMA and RxDMA. During `SwDMA` execution (which uses PIO Write-followed-by-Repeated-Start-and-Read constructs for bidirectional operations), if an active RxDMA HW MSI fires, it can severely corrupt the internal state machine. 

To mitigate this race condition, the driver *must* explicitly stop `RxDMA2`, **quiesce the device interrupts**, and drop all incoming HID input MSIs while the SWDMA transaction is processed. This creates a hard window where normal touch input is blocked.

### PRD Ring Overflow / Stall Recovery

If the circular buffer read pointer (TPCRP) collides with the write pointer (TPCWP) under sustained input load, a PRD ring stall occurs. The driver detects this via the STALL condition (`ACTIVE==0 && TPCRP==TPCWP`) and must execute a DMA reconfigure sequence: pause DMA, reset ring pointers, flush pending completions, and restart. This is a data-loss event — any in-flight touch frames in the stalled ring segment are dropped.

### SWDMA I2C Configuration Registers

| Register Field | Purpose | Values |
|---------------|---------|--------|
| `THC_SWDMA_I2C_WBC` | Write Byte Count — size of I2C command written to device | Varies per command type |
| `THC_SWDMA_I2C_RX_DLEN_EN` | RX Data Length Enable | `0` = length known in advance (e.g., report descriptor), `1` = length in first bytes of DMA data |
| `THC_SWDMA_I2C_RX_DLEN` | RX Data Length — expected read size (when `RX_DLEN_EN=0`) | Size in bytes |

> **Validation point**: When `RX_DLEN_EN=0`, the SWDMA engine reads exactly `RX_DLEN` bytes. When `RX_DLEN_EN=1`, the device's first 2 bytes indicate length (standard HIDI2C length-prefix behavior).

### SWDMA Workflow (Canonical Sequence)

> **Source attribution**: This workflow is synthesized from the **QuickI2C SwAS v1.0** (P0394-P0418, which describes ~18 unnumbered bullet points) and verified against the **Linux kernel source** (`intel-thc-dma.c`). The 14-step enumeration below is an organizational convenience — the SwAS does not assign step numbers. The THC HAS describes SWDMA registers but does not provide a step-by-step workflow.

The complete SWDMA transaction follows this sequence. Both Linux and Windows drivers implement this workflow (with minor implementation differences noted in their respective platform files).

1. **Disable SWDMA interrupt** — prevent spurious SWDMA completion interrupts during setup
2. **Clear pending SWDMA interrupt** — ensure no stale `DMACPL` status from prior transactions
3. **Reset SWDMA read pointer** — set `TPCPR = 1` to advance past any completed entry from previous use
4. **Pause RXDMA1** — clear START bit to 0, poll `INT_STS` ACTIVE bit until 0 (DMA idle confirmed)
5. **Pause RXDMA2** — clear START bit to 0, poll `INT_STS` ACTIVE bit until 0 (DMA idle confirmed)
6. **Disable write interrupt for RXDMA1** — suppress RXDMA1 completion interrupts during SWDMA window
7. **Disable write interrupt for RXDMA2** — suppress RXDMA2 completion interrupts during SWDMA window
8. **Clear pending write interrupt RXDMA1** — flush any stale RXDMA1 completion status
9. **Clear pending write interrupt RXDMA2** — flush any stale RXDMA2 completion status
10. **Start SWDMA** — configure WBC/RX_DLEN_EN/RX_DLEN, write PIO command, set START bit (with `SOO=1`), initiate the SWDMA read transaction
11. **Wait for SWDMA completion** — poll or wait for `DMACPL` bit in `READ_DMA_INT_STS_SW` (timeout: 1s on Linux, similar on Windows)
12. **Enable RXDMA1 write interrupt** — re-enable RXDMA1 completion interrupts
13. **Enable RXDMA2 write interrupt** — re-enable RXDMA2 completion interrupts
14. **Restart RXDMA2 only** — set RXDMA2 START bit to 1 to resume normal touch input flow. **RXDMA1 is NOT restarted** — only RXDMA2 carries the primary input report path in I2C mode

> **Critical detail**: Step 14 restarts **only RXDMA2** (not RXDMA1). This is because RXDMA2 is the primary input data channel for HIDI2C. RXDMA1 handles frame-type-0 data which is not used in standard HIDI2C touch input flow.
>
> **Validation point**: After SWDMA completes, verify that (a) RXDMA2 is restarted and receiving touch input, (b) RXDMA1 remains paused, (c) all interrupt enables are restored to pre-SWDMA state.

### DMA Pause/Resume Mechanism

The DMA engine uses a START-bit-based stop protocol for each channel (there is NO dedicated PAUSE bit or PAUSE_ACK bit):

```
Pause (stop): Clear START bit to 0 in READ_DMA_CNTRL_x
  → Poll READ_DMA_INT_STS_x for ACTIVE bit == 0
  → DMA stopped (safe to reconfigure)
Resume: Platform-dependent — see linux.md and windows.md
```

- **Stop request**: Clear START bit in `READ_DMA_CNTRL_1` / `READ_DMA_CNTRL_2` / `READ_DMA_CNTRL_SW`
- **Completion polling register**: `READ_DMA_INT_STS_1` (0x110) / `READ_DMA_INT_STS_2` (0x210) / `READ_DMA_INT_STS_SW` (0x2D0) — polls the **ACTIVE** bit in `INT_STS` register for 0
- **Critical**: If ACTIVE bit does not clear within timeout, DMA may be in an inconsistent state

> **Validation point**: DMA stop latency should be << 1ms under normal conditions. Extended stop times indicate DMA engine is mid-transfer and waiting for bus completion. Test both timeout boundaries.

### DmaUnconfigure Full Teardown

`DmaUnconfigure` / `thc_dma_unconfigure()` performs a **full teardown**, not just a pause:
- Zeros PRD base addresses (`RPRD_BA_LOW` / `RPRD_BA_HI` set to 0)
- Clears all DMA control registers for the channel
- Resets ring pointers
- This is used for SWDMA restore (post-SWDMA RXDMA rebuild) and error recovery

## Streaming Mode (Packets > 4KB)

Streaming mode allows THC to receive packets larger than the configured MPS (Max Packet Size) by spanning multiple PRD entries. Without streaming mode, a single touch report is limited to one PRD entry (max 4KB).

- **RX Enable**: `RXDMA_PKT_STRM_EN` = bit 26 in `THC_M_PRT_DEVINT_CFG_2`
- **TX Enable**: `TXDMA_PKT_STRM_EN` = bit 27 in `THC_M_PRT_DEVINT_CFG_2`

**How it works**: When enabled, the DMA engine chains consecutive PRD entries for a single logical packet. The first PRD entry receives the initial MPS-sized chunk; subsequent entries receive overflow data. The completion interrupt fires only after the entire logical packet is transferred.

**When to use**: Required for touch devices with large report descriptors (e.g., pen+touch combo devices), multi-touch reports exceeding 4KB, or vendor-specific bulk data transfers.

**Validation**: Test with packet sizes at boundary conditions: exactly MPS, MPS+1, 2×MPS, and maximum supported size. Verify PRD ring wraparound during multi-entry streaming transfers.

## Burst Mode and Interrupt Control

- **GBL_INT_EN**: Global interrupt enable in `THC_M_PRT_INT_EN`
- **Stall Read**: `THC_STALL_READ_EN_1/2` — controls DMA behavior when PRD ring is full (LNL+):
  - **`STALL_READ_EN = 0`** (default): When PRD entries are exhausted, HW behavior depends on `SOO` (Stop-on-Overflow) bit:
    - `SOO = 0`: HW **drops frames** silently (counted in `frame_drop_cnt`)
    - `SOO = 1`: HW **stops RXDMA** — requires SW intervention to restart
  - **`STALL_READ_EN = 1`**: HW **stalls the read** — DMA engine stops reading from device until PRD entries become available. No data loss, but device backpressure may cause device-side buffer overflow.
  > **Source**: QuickI2C SwAS v1.0 — THC_STALL_READ_EN behavior with SOO interaction
- **NOPTE Counter**: `THC_M_PRT_PRD_EMPTY_CNT_1/2` — frames dropped due to no PRD entries
- **INT_CAUSE in PRD**: `THC_M_PRT_SEND_ICR_US_EN` — embeds interrupt cause in PRD
- **4 test combos**: Stall ON/OFF × GBL_INT ON/OFF

## Display Sync and Frame Coalescing

### Dynamic Frame Coalescing FSM
```
C_DISABLED → C_ARMED → C_ACTIVE (C_ACTIVE_WAIT + C_ACTIVE_SYNC)
```

| Parameter | Purpose |
|-----------|---------|
| `C_Duration` | Maximum coalescing window |
| `C_Start_Threshold` | Frames to trigger coalescing start |
| `C_Idle_Threshold` | Idle time before exit |
| `C_Timer_Override` | Override for forced flush |

### Display Sync Event Sources (DISP_SYNC_EVT_SRC)

| Value | Source |
|-------|--------|
| `0x0` | Disabled |
| `0x1` | Emulated |
| `0x2` | TCON GPIO |
| `0x3` | Virtual Wire (VW) |

**Sonora2 TCON**: `TCON_CTRL_REG` at offset `0x1D4`.
**Important**: Enable DSYNC on **one THC port only** per platform.

Sync event delay is programmable via `DISP_SYNC_DELAY` register; enable delay with `DISP_SYNC_COAL_DELAY_EN`.

### Coalescing Registers

| Register | Offset | Purpose |
|----------|--------|---------|
| `thc_m_prt_coalesce_cntrl_1` | 0x12E8 | Coalescing control ch1 |
| `thc_m_prt_coalesce_cntrl_2` | 0x12EC | Coalescing control ch2 |
| `thc_m_prt_coalesce_sts_1` | 0x12F8 | Coalescing status ch1 |
| `thc_m_prt_coalesce_sts_2` | 0x12FC | Coalescing status ch2 |
| `thc_m_prt_sync_timestamp` | 0x1310 | Sync timestamp |
| `thc_m_prt_disp_sync_2` | 0x1318 | Display sync config 2 |

## HID Report Timestamps

**Key Register**: `thc_sb_pm_ctrl`
- `THC_TIMESTAMP_EN` (bit 31): Enable timestamp in PRD data
- `THC_TIMESTAMP_SRC` (bit 17): Clock source
- `THC_MICROSEC_CNT` (bits 30:24): 10-microsecond step counter
- `THC_TS_D0I2_MODE` (bit 18): D0i2 behavior (0=pause, 1=reset to 0)

**Format**: First QWord (8 bytes) of PRD data = 64-bit timestamp (28-bit counter, zero-extended). Each step = 10 μs.

## Buffer Overrun Management

### RX FIFO
- **Size**: 8KB total
- **Slots**: 4 (original) → 16 → 32 on NVL for HIDSPI
- **Buffer Full Delay Timer**: `BUF_FULL_DLY_TMR` in `THC_SB_SPI_CTRL` bits [31:14]
- NVL: buffer-full at packet 29 (of 32), max 14 reports per coalescing window

### Frame Drop Counters
- `frame_drop_cnt_1`: Frames dropped on RXDMA channel 1
- `frame_drop_cnt_2`: Frames dropped on RXDMA channel 2

## DMA Initialization Sequence
1. Allocate physically contiguous DMA buffers
2. Build PRD table entries pointing to buffers
3. Program PRD ring base address (`RPRD_BA_LOW`/`RPRD_BA_HI`)
4. Set PRD table length and watermarks
5. Configure DMA control (prefetch, coalescing, IOC policy)
6. Set DMA START bit

### Recommended Buffer Sizing (from SwAS)

Both QuickSPI and QuickI2C SwAS v1.0 recommend the following production configuration:

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| PRD tables (ring depth) | **16** | Matches Linux kernel `PRD_TABLES_NUM` |
| Buffers per PRD table | **16** | One buffer per PRD entry |
| Buffer size | **4KB** (4096 bytes) | Aligned to 4KB boundary (RTL bug workaround) |
| Total DMA memory | ~1MB | 16 tables × 16 entries × 4KB per buffer |
| RxDMA1 | **Allocated but NOT started** | Windows: full-size buffers same as RXDMA2; Linux: not used for I2C |
| **TXDMA** | **ALIGN_UP_BY(wMaxOutputLength, 4KB)** | Buffer size derived from `wMaxOutputLength` in the HID Device Descriptor, 4KB-aligned |
| **SWDMA/RXDMA** | **max(wReportDescLength, wMaxInputLength) + sizeof(uint16_t)** | Buffer size = max of report descriptor length and max input length, plus 2 bytes for I2C length prefix |

> **Key insight**: Windows allocates full-size RXDMA1 buffers (same as RXDMA2) but does NOT start RXDMA1 in production. RxDMA2 is the sole active input DMA channel for both HIDSPI and HIDI2C. Linux does not use RXDMA1 for I2C. This is confirmed by both SwAS documents and driver source.

### DMA Buffer Formats

**HIDI2C Write DMA**:
```
[wCommandRegister(2B)] [I2C_COMMAND_REQUEST] [reportID(1B,opt)] [wDataRegister(2B)] [length(2B)] [reportBuffer]
```

**HIDSPI Write DMA**:
```
[OUTPUT_REPORT_HEADER_VAL(4B)] [data payload (DWORD-aligned)]
```

**HIDSPI Input Report**:
```
Header: [protocol_version:4][reserved:4][input_report_length:14][lastfragment:1][reserved:7][sync_const:8=0x5A]
Body:   [input_report_type:8][content_length:16][content_id:8][payload...]
```

## Store-and-Forward vs Streaming Mode

### Store-and-Forward (POR — Plan of Record)
- **Default mode** — all production platforms use this
- DMA waits for complete frame from device before writing to host memory
- Higher latency but simpler error handling
- Frame integrity guaranteed before host notification

### Streaming Mode (NOT POR)
- DMA writes to host memory as data arrives (before frame complete)
- ~6.5% better performance than Store-and-Forward
- More complex error handling — partial frames possible
- **Not POR for any current platform** — validation/debug use only
- Requires careful PRD management to handle incomplete frames

## End-to-End DMA Flow (Touch Sequencer)

The complete flow from device interrupt to host notification:

### SPI Touch Read Flow
1. **Device INT** — Touch device asserts GPIO interrupt (active low)
2. **ICR Read** — THC reads Input Cause Register from device via SPI
   - Uses ICR Read opcode (0x0B/0xBB/0xEB/0xFB depending on IO mode)
3. **Qualify** — THC examines INT_CAUSE bits in ICR to determine frame type
4. **Bulk Data Read** — THC reads touch data via SPI DMA read opcode
5. **PRD Walk** — DMA engine walks PRD table, writing data to host memory
6. **MSI** — THC generates MSI interrupt to host when IOC bit set in PRD entry
7. **EOF** — End-of-frame processing, update DMA pointers
8. **GuC Doorbell** — THC rings GuC doorbell (if configured) for GPU-direct touch

### Frame Type Routing
- Frame Type 0 → RXDMA1
- Frame Type 1 → RXDMA2
- HIDSPI: Ignores Frame Type (all go to RXDMA2)
- HIDI2C: Uses Frame Type for routing; RXDMA2 is the primary I2C input path (RXDMA1 allocated with full-size buffers but NOT started)

### Frame Coalescing
- Configurable frame count before interrupt
- FCD (First Contact Detection): Bypasses coalescing for first touch event
- Timeout: 10-100ms configurable
- Timing-based coalescing (LNL+): C_Start_Threshold, C_Duration (0.1ms granularity, 1-50ms, typical 16.7ms)
- C_Timer_Override (VSYNC): External display sync signal overrides coalescing timer
- C_Idle_Threshold: Auto-disable coalescing when touch is idle

## SPI DMA Opcodes

### ICR Read Opcodes (Input Cause Register)
| IO Mode | Opcode | Description |
|---------|--------|-------------|
| Single | 0x0B | Single-IO ICR read |
| Dual | 0xBB | Dual-IO ICR read |
| Quad | 0xEB | Quad-IO ICR read |
| Quad (alt) | 0xFB | Quad-IO ICR read (alternate) |

### DMA Read Opcodes (Bulk Data)
| IO Mode | Opcode | Description |
|---------|--------|-------------|
| Single | 0x0B | Single-IO bulk read |
| Dual | 0xBB | Dual-IO bulk read |
| Quad | 0xEB | Quad-IO bulk read |
| Quad (alt) | 0xFB | Quad-IO bulk read (alternate) |

### Dummy Clock Cycles
| Configuration | Dummy Clocks |
|--------------|-------------|
| Minimum | 0 |
| Typical Single | 2 |
| Typical Dual | 4 |
| Typical Quad | 8 |

## DMA Error Handling

### Error Types and Recovery

| Error Type | Detection | Recovery | Register |
|-----------|-----------|----------|----------|
| **RXDMA Stop-on-Error** | DMA error status bit set | Clear error, restart DMA | `READ_DMA_INT_STS_x` |
| **I2C TX Abort** | NAK from device, TX Abort status | Clear abort, retry or abandon | TX Abort status register |
| **PRD Table Overflow (STALL_STS)** | All PRD entries consumed | Provide more PRDs or abort | DMA status register |
| **Bus Error** | AXI/IOSF bus error during transfer | Reset DMA channel, re-init | `FATAL_ERR` in INT_STS |
| **Alignment Error** | PRD address not 4KB aligned | Fix PRD allocation (see RTL bug) | DMA error register |
| **DMA Timeout** | Transfer not completing in time | Pause + reset channel | Pause ACK in INT_STS |
| **Buffer Overrun** | Ring full, new frame arrives | Frame dropped (counted) | `frame_drop_cnt_1/2` |
| **Frame Babble → NVLD_PRD** | Babble cascades into invalid PRD | Clear error, inspect PRD init | PRD entry + DMA error register |

> **Frame babble cascade**: Frame babble may cascade into `NVLD_PRD_ENTRY` error. Unused PRD entries are initialized to `0x00` specifically to detect frame babble via the invalid PRD error path.

### RXDMA Stop-on-Error
- When RXDMA encounters an error, it stops processing the current frame
- Error status captured in DMA error registers
- SW must clear error and restart DMA

### I2C TX Abort Handling
- I2C TXDMA may encounter NAK from device
- TX Abort status register indicates cause
- SW must clear abort status and retry or abandon transaction

### PRD Table Overflow (STALL_STS)
- If all PRD table entries consumed before frame complete
- STALL_STS bit set in DMA status
- DMA engine stalls — no data loss but no progress
- SW must provide more PRD entries or abort

### Bus/Fatal Error Recovery
- `FATAL_ERR` bit in `READ_DMA_INT_STS_x` indicates unrecoverable bus error
- Recovery requires full DMA channel reset — platform-specific details in [linux.md](linux.md) and [windows.md](windows.md)

### RTL Bug 15014172472 — PRD Last Entry Alignment
- **Bug**: Last PRD entry in a table must also be 4KB aligned (contrary to spec)
- **Spec says**: Only non-last entries require 4KB alignment; last can be any size
- **RTL reality**: Last entry also requires 4KB alignment
- **Impact**: SW must ensure ALL PRD buffer addresses are 4KB aligned
- **Workaround**: Always allocate 4KB-aligned buffers for all PRD entries

## DMA Arbitration Policy (ARB_POLICY)

Controls how the DMA engine arbitrates between channels when multiple are active:

| Value | Name | Description |
|-------|------|-------------|
| 0 | `PACKET_BOUNDARY` | Arbitrate at packet boundary — lowest latency, used for SPI |
| 1 | `UFRAME_BOUNDARY` | Arbitrate at microframe boundary |
| 2 | `FRAME_BOUNDARY` | Arbitrate at frame boundary — used for I2C (HIDI2C) |

> **Protocol default**: SPI uses `PACKET_BOUNDARY` (0) for lowest latency. I2C uses `FRAME_BOUNDARY` (2) because I2C transactions are frame-oriented and cannot be interrupted mid-frame.

## MPS (Max Packet Size) Alignment

The `spi_rd_mps` value is always aligned to 4KB in driver implementations:
```c
mps = ALIGN(size, SZ_4K);  // e.g., 4096 → 4096, 2048 → 4096
```

> **⚠️ RTL Bug (I2C MPS)**: THC uses the `SPI_RD_MPS` register even in I2C mode. SW must program `SPI_RD_MPS = 4096` for I2C regardless of actual I2C transfer sizes. See `fv-thc/hidi2c` MPS Workaround section.

## Asymmetric Wraparound Logic (ODD/EVEN)

The wraparound mechanism uses two constants with asymmetric behavior:

- **`WRAPAROUND_VALUE_16 = 0x10`** — wraps pointer to `0x80`
- **`WRAPAROUND_VALUE_0X90 = 0x90`** — wraps pointer to `0x0`

This creates an asymmetric phase toggle: ODD wrap sets the phase bit (bit 7), EVEN wrap clears it. The DMA engine uses this phase bit to distinguish between "ring full" and "ring empty" conditions when read and write pointers have the same index value.

> Platform-specific naming: Linux uses `THC_` prefix (`THC_WRAPAROUND_VALUE_16`, `THC_WRAPAROUND_VALUE_0X90`); Windows omits it (`WRAPAROUND_VALUE_16`, `WRAPAROUND_VALUE_0X90`). See [linux.md](linux.md) and [windows.md](windows.md).

## DMA Pause/Resume Timing Cross-Reference

> ⚠️ D7 reference: DEFAULT_MAX_PACKET_SIZE (MPS) impacts PRD alignment and pause/resume timing. Drivers that set MPS to values requiring more frequent PRD wraparound may observe longer pause times during PRD ring reconfiguration. Ensure `SPI_RD_MPS` is aligned to 4KB to avoid extra pause latencies.

## DMA Stall Recovery Notes

> ⚠️ M12: DMA stall recovery conservative timeout — Windows uses a 1s quiesce polling timeout while Linux uses a 10ms timeout. For robust recovery across platforms, tests should validate both 10ms (fast fail) and 1s (tolerant) bounds.

## DMA Read Behavior (One Frame Per Call)

The `thc_dma_read()` / equivalent read function returns **one frame per call**. The caller must loop until all frames are consumed:
```
read_finished = false
while (!read_finished):
    dma_read(dma_channel, &buffer, &size, &read_finished)
    process(buffer, size)
```

- `read_finished = true` when the read pointer catches up to the write pointer
- Each call advances the read pointer by one PRD entry
- For multi-frame coalesced data, multiple calls are required

## TXDMA Performance Limit Delay

After writing data to TXDMA and setting the START bit, the DMA engine waits for a configurable delay:
```
delay = perf_limit × 10µs
```

- **Purpose**: Rate-limits TXDMA writes to prevent overwhelming the touch device
- **Register**: `THC_M_PRT_WRITE_DMA_CNTRL.perf_limit`
- **Default**: Platform-specific, typically 0 (no delay)
- **Usage**: Set non-zero when the touch device has limited SPI/I2C input bandwidth

## TXDMA Completion Detection

**Completion detection**: TXDMA architecturally supports both interrupt-driven and polling (poll START bit for clear). Platform-specific timeout values in [linux.md](linux.md) and [windows.md](windows.md).

## PRD Descriptor Caching

### Configuration
- Configurable cache depth for PRD descriptors
- DMA engine prefetches PRD entries ahead of current position
- Prefetch works across PRD table boundaries in circular buffer

### Performance Impact
- Deeper cache → lower DMA latency (fewer memory reads for descriptors)
- Deeper cache → more host memory bandwidth consumed for prefetch
- Default depth suitable for most touch workloads

## SGX Trusted I/O (DMA Encryption) — Historical

> **⚠️ Historical feature**: SGX Trusted I/O for touch was designed for Gen1.0/Gen2.0 IPTS mode where touch data flowed through CSME/GPU. With the shift to HIDSPI/HIDI2C direct host mode (Gen3.0+), SGX Trusted I/O for touch is **not actively used** in current production configurations. The registers and channel IDs remain in the HAS for backward compatibility.

### Channel ID for DMA Encryption
- THC DMA supports SGX Trusted I/O via encrypted DMA channels
- Each DMA engine assigned a Channel ID for encryption context
- Enables secure touch data path from device to trusted enclave
- Requires platform-level SGX and TME (Total Memory Encryption) support

## Validation Points

| ID | What to Validate | Expected | Register/Method |
|----|-----------------|----------|-----------------|
| VP-DMA-01 | PRD entries 4KB-aligned | All PRD entries (including last) must be 4KB-aligned | Check PRD_BA_LOW bits [11:0] = 0 (RTL bug 15014172472) |
| VP-DMA-02 | DMA pause completes | ACTIVE bit clears after setting START=0 | Poll `READ_DMA_INT_STS_x` within timeout (Linux: 10ms, Windows: 1s) |
| VP-DMA-03 | RXDMA channel routing | SPI uses RXDMA1 (0x100), I2C uses RXDMA2 (0x200) | Verify `PORT_TYPE` matches active RXDMA channel |
| VP-DMA-04 | SWDMA independence | SWDMA ignores INT_CAUSE, operates on SW trigger | Write SW_DMA_CNTRL.START=1, verify data without device interrupt |
| VP-DMA-05 | Buffer overrun detection | Frame drop counter increments on overrun | Fill PRD ring, inject touch data, read `FRAME_DROP_CNT` |
| VP-DMA-06 | MPS alignment (I2C mode) | SPI_RD_MPS=4096 even in I2C mode | Read `THC_M_PRT_SPI_CFG.SPI_RD_MPS` — must be 4096 (RTL bug workaround) |
| VP-DMA-07 | DMA streaming mode | Packets > MPS split across multiple PRD entries | Send large report, verify multi-PRD completion |
| VP-DMA-08 | Display sync coalescing | Touch data coalesced to display refresh boundary | Verify `DISP_SYNC_EVT_SRC` config and `DISP_SYNC_INT` timing |
| VP-DMA-09 | PRD ring wraparound | Circular buffer wraps correctly at ring end | Fill ring to capacity, verify write/read pointer wrap |
| VP-DMA-10 | DMA quiesce before D3 | All DMA engines stopped before power transition | Verify all ACTIVE bits = 0 before D3 entry |

## See Also
- **[linux.md](linux.md)** — Linux kernel DMA implementation details
- **[windows.md](windows.md)** — Windows driver DMA implementation details
- **`fv-thc/registers`** — DMA register offsets (RPRD/WPRD base, control, status, error)
- **`fv-thc/hidspi`** — SPI DMA opcodes (ICR read, bulk read), IO mode selection
- **`fv-thc/hidi2c`** — I2C DMA modes, TXDMA/RXDMA mapping to HIDI2C commands
- **`fv-thc/power`** — DMA interaction with D0i2/D3, LTR during active DMA
- **`fv-thc/debug`** — DMA error triage, STALL_STS debug, frame drop analysis
- **`fv-thc/platform`** — Per-platform DMA performance targets
- **`fv-thc/driver`** — Driver DMA implementation, interrupt handling for DMA channels
- **`fv-thc/wot`** — DMA quiesce during WoT entry, DMA re-arm after WoT exit, PRD state across sleep transitions
- **`fv-thc/simics`** — Simics PRD/DMA Maestro debug, DMA register validation in pre-silicon, display sync emulation
- **Reference**: `fv-thc/docs/thc_known_issues.md` — PRD alignment bug (15014172472)
