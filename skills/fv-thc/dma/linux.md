# DMA — Linux Kernel Implementation
See [SKILL.md](SKILL.md) for shared HW architecture.

> **Owner**: willychi | **Platform**: Linux Kernel | **Source**: drivers/hid/intel-thc-hid/
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

## Linux Kernel PRD Limits vs HW Max

| Parameter | HW Max (HAS) | Linux Kernel | Define |
|-----------|-------------|-------------|--------|
| PRD entries per table | 256 | **16** | `PRD_ENTRIES_NUM = 16` |
| PRD tables in ring | 128 | **16** | `PRD_TABLES_NUM = 16` |
| Ring pointer mask | 0x7F (7-bit) | 0x7F | `POINTER_MASK = 0x7F` |

> **⚠️ Validation note**: Linux kernel allocates only 16 entries × 16 tables = 256 total PRDs. HW supports up to 256 × 128 = 32,768. Windows drivers may use larger values. Test coverage should include both kernel-default and HW-max configurations.

## Linux Pointer Management

- **Write pointer (TPCWP)**: Managed by **SW** (`dma_set_write_pointer`)
- **Read pointer (TPCRP)**: Managed by **HW** (`dma_get_read_pointer`)

Write pointer init during START: `thc_dma_set_write_pointer(0x80)`.

## Linux DMA Timeout Values

| Operation | Timeout | Define |
|-----------|---------|--------|
| DMA pause poll interval | **100 µs** | `sleep_us=100` |
| DMA pause total timeout | **10 ms** | `timeout_us=10000` |
| TXDMA completion | **1 s** | `1*HZ` |
| SWDMA completion | **1 s** | `1*HZ` |
| Poll function | `readl_poll_timeout()` | Kernel macro |

> **⚠️ Cross-platform difference**: Linux uses a much shorter 10ms timeout (aggressive, fails fast), while Windows uses a 1-second timeout (conservative, waits longer for ACTIVE bit to clear). This means Linux will report errors sooner.

## Linux Wrap Constants

- **`THC_WRAPAROUND_VALUE_16 = 0x10`** — wraps pointer to `0x80` (with `THC_` prefix)
- **`THC_WRAPAROUND_VALUE_0X90 = 0x90`** — wraps pointer to `0x0` (with `THC_` prefix)

The `THC_` prefix distinguishes Linux kernel defines from Windows driver defines which omit this prefix.

## Linux DMA Function Names

Key DMA functions in the Linux kernel THC driver:

| Function | Purpose |
|----------|---------|
| `thc_dma_configure()` | Configure DMA channel (PRD base, control, entries) |
| `thc_dma_unconfigure()` | Full teardown of DMA channel (zero base addresses, clear control) |
| `thc_dma_set_write_pointer()` | Set TPCWP (write pointer managed by SW) |
| `thc_dma_get_read_pointer()` | Read TPCRP (read pointer managed by HW) |
| `thc_dma_read()` | Read one frame from DMA ring (returns one frame per call) |
| `quickspi_dma_*()` | QuickSPI-specific DMA wrappers |
| `quicki2c_dma_*()` | QuickI2C-specific DMA wrappers |

## Linux DMA Configure Flow

The `thc_dma_configure()` function performs:
1. Set PRD base address (`RPRD_BA_LOW` / `RPRD_BA_HI`)
2. Set PRD table entry count (N-1 encoding) and circular buffer depth
3. Configure prefetch watermarks
4. Set DMA control bits (IOC policy, coalescing)
5. For RXDMA2: auto-start (set START bit)
6. For SWDMA: also disables `max_rx_size` and `int_delay` (restored after SWDMA completes)

## Linux SWDMA Selective Save/Restore

During SWDMA operations, the Linux kernel only saves and restores two specific settings:
- **`rx_max_size`** — disabled during SWDMA, restored after
- **`int_delay`** — disabled during SWDMA, restored after

This is a **selective** save/restore approach — only these two parameters are modified and restored, not the full DMA channel state. This contrasts with Windows which does a full `DmaUnconfigure` + `DmaConfigure` cycle.

## Linux SWDMA Workflow (14-Step Sequence)

> **Source**: Derived from Linux kernel `intel-thc-dma.c` (`thc_swdma_read()` flow). The underlying operations are documented in the **QuickI2C SwAS v1.0** (P0394-P0418) as ~18 unnumbered bullet points. The "14-step" numbering is an analysis artifact from this kernel code audit — the kernel consolidates some SwAS steps. Always cross-reference with the SwAS for authoritative behavior.

1. Set `SwDmaActive = TRUE`
2. `EnterActiveLTR()` — ensure active power state
3. Quiesce regular interrupts (`THC_DEVINT_QUIESCE_EN = 1`)
4. **Pause RXDMA1** — clear START bit to 0, poll INT_STS ACTIVE bit for 0
5. **Pause RXDMA2** — clear START bit to 0, poll INT_STS ACTIVE bit for 0
6. **Unconfigure SWDMA** — `thc_dma_unconfigure()` (tears down any previous SWDMA state)
7. **Configure SWDMA** — `thc_dma_configure()` (sets up PRD table, base address, control bits in one call; also disables `max_rx_size` and `int_delay`)
8. *(Combined in step 7)*
9. Set `THC_SWDMA_I2C_WBC` (write byte count for I2C command)
10. Set `THC_SWDMA_I2C_RX_DLEN_EN` (0=length known, 1=length in first bytes of data)
11. Write PIO command → set SWDMA START bit (with `SOO=1` set during ReadSetStartBit) → wait for DMA completion interrupt
    - **Completion polling**: After START, the driver polls `READ_DMA_INT_STS_SW` for the `DMACPL` (DMA Complete) status bit. On interrupt-driven paths, the ISR checks this same bit to confirm SWDMA completion before reading response data. The `DMACPL` bit must be explicitly cleared after servicing.
    - **Completion timeout**: **1s** (`1*HZ`)
12. **Read response** from SWDMA PRD buffers (one frame per `thc_dma_read()` call)
13. **Stop SWDMA** → **Restore RXDMA1/RXDMA2 configuration**
    - After SWDMA completion: (1) Stop SWDMA (START=0), (2) Reset SWDMA read pointers by setting TPCPR=1, (3) Restore `rx_max_size` and `int_delay`, (4) Restart RXDMA2, (5) Unquiesce interrupts.
    - **Post-SWDMA catch-up read**: checks `EOF_INT_STS` on RXDMA2 for frames that arrived during SWDMA window
14. **Restart RXDMA2** → Set `SwDmaActive = FALSE`

> **Key detail**: Steps 4-5 must complete (pause acknowledged) before SWDMA can start. Steps 13-14 must restart RXDMA2 to resume normal touch input flow.

## Linux DMA Pause/Resume

```
Pause (stop): Clear START bit to 0 in READ_DMA_CNTRL_x
  → Poll via readl_poll_timeout(): sleep_us=100, timeout_us=10000
  → DMA stopped (safe to reconfigure)
Resume: Re-set START bit to 1 → DMA resumes
```

Linux uses a simpler resume path — just re-set the START bit rather than full teardown/rebuild.

## Linux DMA Buffer Allocation

| Aspect | Linux Kernel |
|--------|-------------|
| Allocation API | `dma_alloc_coherent()` |
| Alignment | PAGE_SIZE (4KB) |
| Coherency | Hardware-coherent (no manual cache flush) |
| Free API | `dma_free_coherent()` |
| PRD table memory | Same coherent allocation |

> **Validation point**: All DMA buffers (both PRD tables and data buffers) must be physically contiguous and 4KB-aligned. Verify alignment with `dma_addr & 0xFFF == 0` checks.

## Linux Buffer Sizing Details

- **Read1 vs Read2 difference (HIDSPI only)**: In Linux HIDSPI, Read1 (RXDMA1) adds `sizeof(INPUT_REPORT_HEADER)` to the buffer size beyond the base data size; Read2 does not include this header overhead.
- **RXDMA1 for I2C**: Not used (not started)
- **MPS alignment**: `mps = ALIGN(size, SZ_4K);` — always aligned to 4KB

## Linux DMA Error Recovery

### Fatal Error Recovery Flow
- `FATAL_ERR` bit in `READ_DMA_INT_STS_x` indicates unrecoverable bus error
- Recovery: `thc_dma_unconfigure()` + `thc_dma_configure()` cycle
- Sequence: Pause all DMA channels → Reset DMA engine → Re-initialize PRD ring → Restart

## Linux TXDMA Completion

- Polling at `readl_poll_timeout()` intervals
- Timeout: **1s** (`1*HZ`)
- Architecturally supports both interrupt-driven and polling (poll START bit for clear)

## Linux DMA Channel Configuration

| Channel | Entries/Table | PRD Tables |
|---------|--------------|------------|
| RXDMA1 | 16 | Up to 16 (ring) |
| RXDMA2 | 16 | Up to 16 (ring) |
| TXDMA | 16 | 1 (no ring) |
| SWDMA | 16 | 1 (no ring) |

## See Also
- **[SKILL.md](SKILL.md)** — Shared HW architecture and cross-platform reference
- **[windows.md](windows.md)** — Windows driver DMA implementation
- **`fv-thc/driver`** — Linux driver source analysis
