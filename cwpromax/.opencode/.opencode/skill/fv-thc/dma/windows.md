# DMA — Windows Driver Implementation
See [SKILL.md](SKILL.md) for shared HW architecture.

> **Owner**: willychi | **Platform**: Windows | **Source**: drivers.platform.ipts.hspi-driver + hid-i2c-touch
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

## Windows PRD Configuration

| Parameter | Windows Value | Define |
|-----------|-------------|--------|
| PRD entries per table (max) | **255** | `MAX_PRD_ENTRIES = 0xFF` |
| PRD tables in ring | Dynamic (up to HW max) | Computed per-channel based on buffer requirements |
| PRD sizing | Dynamic | Actual PRD entry count computed per-channel, not fixed |

> Windows uses dynamic sizing (not fixed) — actual PRD entry count is computed per-channel based on buffer requirements.

## Windows Pointer Management

- **Write pointer (TPCWP)**: Advanced by **HW**
- **Read pointer (TPCRP)**: Advanced by **SW**

This is the **opposite** of Linux where write pointer is SW-managed and read pointer is HW-managed.

## Windows DMA Timeout Values

| Operation | Timeout | Define |
|-----------|---------|--------|
| DMA pause poll interval | **10 µs** | `DEFAULT_QUIESCE_POLLING_US_INTERVAL = 10` |
| DMA pause total timeout | **1 s** (1,000,000 µs) | `DEFAULT_QUIESCE_POLLING_US_TIMEOUT = 1000000` |
| TXDMA completion | **500 ms** | Polling at 100µs intervals |
| SWDMA completion | **500 ms** | — |
| Poll function | `WaitForQuiesceWithPolling()` | Custom driver function |

> **⚠️ Cross-platform difference**: Windows uses a 1-second timeout (conservative, waits longer for ACTIVE bit to clear), while Linux uses a much shorter 10ms timeout. Windows is more tolerant of slow DMA quiesce but may delay error detection.

## Windows Wrap Constants

- **`WRAPAROUND_VALUE_16 = 0x10`** — wraps pointer to `0x80` (no `THC_` prefix)
- **`WRAPAROUND_VALUE_0X90 = 0x90`** — wraps pointer to `0x0` (no `THC_` prefix)

The Windows driver omits the `THC_` prefix that the Linux kernel uses for these same constants.

### WRAPAROUND_VALUE_0X90 (M10)

The Windows HIDI2C `Dma.cpp` uses an alternate DMA write pointer wraparound constant `WRAPAROUND_VALUE_0X90 = 0x90` (144 decimal) in the `UpdateWritePointer` logic, differing from the common `0x80` (128) wrap value used elsewhere. I2C-specific DMA behavior uses this alternate constant for write pointer wrap detection. Tests verifying DMA ring wraparound on I2C ports should account for both `0x80` and `0x90` wrap values.

## Windows DMA Function / Class Names

Key DMA functions and classes in the Windows THC driver:

| Function/Class | Purpose |
|----------------|---------|
| `Dma::DmaConfigure()` | Configure DMA channel (full setup) |
| `Dma::DmaUnconfigure()` | Full teardown of DMA channel |
| `Dma::UpdateWritePointer()` | Update TPCWP with wraparound logic |
| `Dma::*` | DMA class methods for channel management |
| `SwdmaConfigure()` | SWDMA-specific configuration |
| `SwdmaUnconfigure()` | SWDMA-specific teardown |

## Windows SWDMA Full Unconfigure/Reconfigure Restore

After SWDMA completion, Windows performs a **full** `DmaUnconfigure` + `DmaConfigure` cycle to restore RXDMA state:

1. Stop SWDMA (START=0)
2. Reset SWDMA read pointers (TPCPR=1)
3. **Full `DmaUnconfigure`** on RXDMA2 — zeroes PRD base addresses for complete teardown
4. **Full `DmaConfigure`** on RXDMA2 — reconfigures from scratch
5. Unquiesce interrupts
6. Restart RXDMA2

This contrasts with Linux which only selectively saves/restores `rx_max_size` and `int_delay`.

### Windows SWDMA Workflow Differences

Windows follows the same 14-step SWDMA sequence as Linux (see [SKILL.md](SKILL.md)) but with these platform-specific differences:
- **Step 6**: Uses `SwdmaUnconfigure()` (Windows class method)
- **Step 7**: Uses `SwdmaConfigure()` (Windows class method)
- **Step 11**: Completion timeout = **500ms** (vs Linux 1s)
- **Step 13**: Full `DmaUnconfigure` + `DmaConfigure` cycle (not selective restore)
- **Post-SWDMA catch-up read**: checks `EOF_INT_STS` on RXDMA2 for frames that arrived during SWDMA window

## Windows DMA Pause/Resume

```
Pause (stop): Clear START bit to 0 in READ_DMA_CNTRL_x
  → Poll via WaitForQuiesceWithPolling(): interval=10µs, timeout=1,000,000µs
  → DMA stopped (safe to reconfigure)
Resume: Full DmaUnconfigure + DmaConfigure cycle (tears down and rebuilds channel state)
```

Windows uses a more conservative resume path — full teardown and rebuild rather than just re-setting the START bit.

## Windows I2C Bus Locking (TXDMA)

Windows HIDI2C driver acquires an I2C bus lock (`AquireI2CBusLock`) before TXDMA operations and releases it (`ReleaseI2CBusLock`) after completion.

> **⚠️ Source code typo**: The source code spells it `AquireI2CBusLock` — missing 'c' — this is a typo in the driver source, not a documentation error.

This serializes TXDMA with other I2C bus operations to prevent bus contention.

## Windows Buffer Sizing Details

### Read1 vs Read2 Buffer Sizing (HIDI2C)

Windows HIDI2C uses **identical formulas** for both Read1 and Read2:
```
buffer_size = MAX(wReportDescLength, wMaxInputLength) + sizeof(uint16_t)
```
4KB aligned. There is no `INPUT_REPORT_HEADER` difference in the Windows I2C path (unlike Linux HIDSPI where Read1 adds header overhead).

### DMA Max Size Cap

Windows caps any single DMA buffer at **1MB** maximum.

### MIN_BYTES_PER_SG_LIST_ENTRY

Windows defines `MIN_BYTES_PER_SG_LIST_ENTRY = 4096` — minimum scatter-gather list entry size for DMA buffer fragmentation.

### RXDMA1 Buffer Sizing

Windows allocates RXDMA1 with **full-size buffers** (same size as RXDMA2) but does NOT start RXDMA1 in production.

### EGP Bit

`EGP` (End Group Packet) bit in `TSEQ_CNTRL` is set during Read1 (RXDMA1) start to mark end-of-group boundaries in the touch sequencer.

## Windows DMA Buffer Allocation

| Aspect | Windows Driver |
|--------|----------------|
| Allocation API | `WdfCommonBufferCreate()` |
| Alignment | 4KB (aligned by framework) |
| Coherency | WDF manages coherency |
| Free API | `WdfObjectDelete()` on common buffer |
| PRD table memory | Same WDF common buffer |

## Windows RXDMA2 Software Throttle

- **Throttle threshold constant**: `RXDMA2_THROTLE_THRESHOLD = 8`
  > Note: the source code spells it `THROTLE` (missing 't') — this is a typo in the driver source.
- When the number of unprocessed PRD entries reaches 8, the driver throttles incoming DMA
- Reset/power-down guard: Throttle threshold check includes guard against reset and power-down states

## SmartFilter (Windows HIDI2C Only)

The Windows HIDI2C driver implements a **SmartFilter** module (`SmartFilter.h`) that provides host-side touch report filtering:

- **Purpose**: Reduces redundant/duplicate touch reports before they reach the HID stack
- **Integration**: Sits between DMA read path and HID report delivery
- **Platform**: Windows HIDI2C driver only — not present in HIDSPI or Linux drivers
- **Status**: May be disabled/enabled via driver configuration

> **Validation point**: When SmartFilter is active, the number of HID reports delivered to the OS may be less than the number of DMA frames received. Compare `frame_drop_cnt_2` with HID report count to isolate SmartFilter vs DMA-level drops.

## Windows TXDMA Quiesce-During-Write (PerformanceLimitation)

Windows implements a **quiesce-during-write** pattern for PerformanceLimitation: during TXDMA writes, the driver quiesces RXDMA interrupts to prevent read-side DMA activity from interfering with the write path, then unquiesces after completion.

## Windows TXDMA Completion

- The Windows QuickI2C driver uses polling at **100µs intervals** with a **500ms timeout**
- Architecturally supports both interrupt-driven and polling (poll START bit for clear)

## Windows DMA Error Recovery

### Fatal Error Recovery Flow
- `FATAL_ERR` bit in `READ_DMA_INT_STS_x` indicates unrecoverable bus error
- Recovery: Full device reset via `DeviceD0Exit()` → `DeviceD0Entry()` cycle
- This is a heavier reset than Linux's `thc_dma_unconfigure()` + `thc_dma_configure()` approach

## Windows DMA Channel Configuration

| Channel | Entries/Table (max) | PRD Tables |
|---------|--------------------|------------|
| RXDMA1 | 255 (0xFF) | Up to HW max (ring) |
| RXDMA2 | 255 (0xFF) | Up to HW max (ring) |
| TXDMA | 255 (0xFF) | 1 (no ring) |
| SWDMA | 255 (0xFF) | 1 (no ring) |

## Windows DMA Stall Recovery

Windows uses a **1s quiesce polling timeout** (`DEFAULT_QUIESCE_POLLING_US_TIMEOUT = 1000000`) for DMA stall recovery. This is significantly more conservative than Linux's 10ms timeout. For robust recovery testing, validate both the 10ms (fast fail) and 1s (tolerant) bounds.

## See Also
- **[SKILL.md](SKILL.md)** — Shared HW architecture and cross-platform reference
- **[linux.md](linux.md)** — Linux kernel DMA implementation
- **`fv-thc/driver`** — Windows driver source analysis
