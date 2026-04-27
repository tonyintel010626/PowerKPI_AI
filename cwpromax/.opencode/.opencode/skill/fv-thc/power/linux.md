# THC Power Management — Linux Kernel Implementation

> **Owner**: willychi | **Platform**: Linux Kernel
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

This file covers Linux-specific THC power management implementation details. For shared HW architecture, see [SKILL.md](SKILL.md). For Windows implementation, see [windows.md](windows.md).

## LTR Defaults (Linux)

- **Default Active LTR**: 5μs (`DEFAULT_ACTIVE_LTR_US=5`)
- **Default LP LTR**: 500μs (`DEFAULT_LP_LTR_US=500`)

## LTR Scale Selection Algorithm (Linux Kernel)

The kernel `thc_ltr_config()` accepts LTR values in microseconds and operates directly on the µs value — there is no nanosecond conversion. Scale selection checks the largest scales first (descending) and falls through to the default scale 2 for small values. Conceptual logic:

```
/* Input: ltr_us (microseconds) */
if (ltr_us > 1023 * 1024) {
    /* scale = 5 (unit ≈ 32768 µs (33,554,432 ns)); value = clamp(0..1023) */
    scale = 5; value = min(ltr_us >> 15, 1023);
} else if (ltr_us > 1023 * 32) {
    /* scale = 4 (unit ≈ 1024 µs (1,048,576 ns)); value = ltr_us >> 10 */
    scale = 4; value = ltr_us >> 10;
} else if (ltr_us > 1023) {
    /* scale = 3 (unit ≈ 32 µs (32768 ns)); value = ltr_us >> 5 (0..1023) */
    scale = 3; value = ltr_us >> 5;
} else {
    /* default: scale = 2 (unit ≈ 1 µs (1024 ns)); value = ltr_us (0..1023) */
    scale = 2; value = ltr_us;
}
```

Default values: `DEFAULT_ACTIVE_LTR_US = 5`, `DEFAULT_LP_LTR_US = 500`.

Note: integer division via right-shift means the programmed latency may be slightly less than requested; validate tolerance for small values (scale 2 maps to ~1024 ns units).

## LTR Config (thc_ltr_config)

Linux config flow: caller passes a raw latency in microseconds → driver converts to {scale, value} using descending range checks (scale 5 first, then 4, 3, else default 2) → writes LP_LTR_VALUE+LP_LTR_SCALE and ACTIVE_LTR_VALUE+ACTIVE_LTR_SCALE → sets ACTIVE_LTR_EN (enable) and **clears LP_LTR_EN** (LP_LTR_EN is in ltr_mask but NOT in ltr_ctrl, so it is cleared) → sets LP_LTR_REQ and ACTIVE_LTR_REQ to generate the IOSF-sideband LTR messages.

## LTR Unconfigure (thc_ltr_unconfig)

The kernel `thc_ltr_unconfig()` disables LTR (used during poweroff paths) by clearing the enable and request bits in the THC LTR control register. Concretely, it simply clears the following bits in THC_M_PRT_LTR_CTRL_REG:

- LP_LTR_EN
- ACTIVE_LTR_EN
- LP_LTR_REQ
- ACTIVE_LTR_REQ

There is no intermediate toggle sequence in the Linux `thc_ltr_unconfig()` implementation — the driver clears the bits directly. This function is called during SPI and I2C `poweroff` callbacks (not during normal suspend). After `poweroff`, LTR must be fully reconfigured (not just restored).

## Runtime Power Management

### Auto-Suspend Timeouts
| Protocol | Auto-Suspend Delay | Rationale |
|----------|-------------------|-----------|
| **HIDSPI (QuickSPI)** | 5000 ms | SPI devices have higher reinit cost (full reset + descriptor retrieval) |
| **HIDI2C (QuickI2C)** | 5000 ms | Same default as SPI (`DEFAULT_AUTO_SUSPEND_DELAY_MS = 5000`) |

### Runtime Suspend/Resume Flow
- `pm_runtime_use_autosuspend(dev)` + `pm_runtime_set_autosuspend_delay(dev, delay)`
- Runtime suspend: same as system suspend flow (protocol-specific, see PM callback table below)
- Runtime resume: same as system resume flow

**Linux runtime suspend is lightweight**: Unlike system suspend, Linux runtime suspend only changes LTR mode (active → low-power) and calls `pci_save_state()`. It does **NOT** send `SET_POWER(SLEEP)` to the device, does **NOT** stop DMA, and does **NOT** quiesce interrupts. The device remains in an operational state with reduced LTR tolerance.

## Interrupt Quiesce Timeout

**Linux quiesce timeout**: `THC_QUIESCE_EN_TIMEOUT_US = 1000000` (1 second). The driver polls for quiesce completion with this timeout.

## Hibernate PM Sequences (Linux Kernel, Verified from Source)

Hibernate uses separate freeze/thaw (snapshot) and poweroff/restore (resume) paths, distinct from S3 suspend/resume.

### QuickSPI (SPI) Hibernate
```
freeze:   quiesce → int_disable → DMA_unconfig
thaw:     DMA_config → int_enable → unquiesce
poweroff: quiesce → int_disable → LTR_unconfig → DMA_deinit
restore:  quiesce → port_select → SPI_reconfig(addr/read/write) → int_config →
          int_enable → reset_tic → DMA_config → LTR_config → LTR_ACTIVE → unquiesce
```

### QuickI2C (I2C) Hibernate
```
freeze:   quiesce → DMA_unconfig
thaw:     DMA_config → int_config → int_enable → unquiesce
poweroff: set_power(SLEEP) → quiesce → LTR_unconfig → DMA_deinit
restore:  port_select → i2c_subip_init(full) → int_config → int_enable →
          unquiesce → DMA_config → LTR_config → LTR_ACTIVE → set_power(ON)
```

> **Key difference**: `restore` requires **full re-initialization** (same as cold boot), while `thaw` only reconfigures DMA+interrupts. `poweroff` fully de-initializes (DMA_deinit, LTR_unconfig), while `freeze` only unconfigures DMA. QuickI2C `restore` calls `i2c_subip_init` (full 12-step sequence), not just `regs_restore`.

### Hibernate Callbacks (Linux 6.17+)

Linux THC drivers implement separate callbacks for hibernate (S4) handling starting around kernel 6.17: `freeze`/`thaw` (snapshot path) and `poweroff`/`restore` (S4 power-off/restore). These are handled independently from normal S3 suspend/resume.

- `freeze`: save minimal runtime state without powering down (quiesce, disable interrupts, DMA unconfigure)
- `thaw`: restore runtime state from snapshot (DMA configure, enable interrupts, unquiesce)
- `poweroff`: full S4 entry path — quiesce, disable interrupts, `ltr_unconfig`, DMA deinit and deeper teardown
- `restore`: S4 resume — full reinitialization path (port select, sub-IP full init, reset_tic as needed, DMA config, LTR config and activation)

Validation: Ensure these callbacks are present and exercised in the platform kernel tree and that `restore` performs full re-init while `thaw` remains lightweight.

## Linux freeze Does NOT Send SET_POWER

Both SPI and I2C `freeze` callbacks are minimal — they do NOT send `SET_POWER(SLEEP)` to the touch device. Freeze only quiesces and unconfigures DMA. Neither modifies device power state (snapshot-for-hibernate doesn't need device state changes).

Similarly, both SPI and I2C `thaw` callbacks are minimal — they do NOT send `SET_POWER(ON)`. Thaw only reconfigures DMA and re-enables interrupts (resuming from snapshot, device state unchanged).

## Linux Suspend/Resume — Conditional on device_may_wakeup

I2C suspend skips `SET_POWER(SLEEP)` when `device_may_wakeup()` returns true — device must stay responsive for WoT interrupt. **SPI suspend has NO WoT handling** — always sends `SET_POWER(SLEEP)` regardless of wake state.

## PM Callback Comparison (HIDSPI vs HIDI2C — Linux Kernel)

Key differences between QuickSPI and QuickI2C power management callbacks:

| PM Callback | QuickSPI (HIDSPI) | QuickI2C (HIDI2C) |
|-------------|-------------------|-------------------|
| **suspend** | `SET_POWER(SLEEP)` → quiesce → `dma_unconfigure` | `SET_POWER(SLEEP)` (skip if `device_may_wakeup`) → `i2c_subip_save` → quiesce → disable int → `dma_unconfigure` |
| **resume** | `port_select` → `interrupt_config` → `interrupt_enable` → `dma_configure` → unquiesce → `SET_POWER(ON)` | `dma_configure` → `i2c_subip_regs_restore` (simple register write-back) → enable int → unquiesce → `SET_POWER(ON)` |
| **freeze** | quiesce → `dma_unconfigure` (**NO** `SET_POWER(SLEEP)`) | quiesce → disable int → `dma_unconfigure` (**NO** `SET_POWER`, **NO** `i2c_subip_save`) |
| **thaw** | `dma_configure` → `interrupt_enable` → unquiesce (**NO** `port_select`, **NO** `SET_POWER(ON)`) | `dma_configure` → enable int → unquiesce (**NO** `i2c_subip` restore, **NO** `SET_POWER(ON)`) |
| **poweroff** | `SET_POWER(SLEEP)` → quiesce → `dma_deinit` (unconfigure + release) + `ltr_unconfig` | `SET_POWER(SLEEP)` → `i2c_subip_save` → quiesce → disable int → `dma_deinit` (unconfigure + release) + `ltr_unconfig` |
| **restore** | `reset_tic` → full SPI reconfig (device descriptor + report descriptor re-retrieval) | `dma_configure` → full `i2c_subip_init` (NOT just restore) → enable int → unquiesce → `SET_POWER(ON)` |
| **WoT handling** | **No WoT handling** — SPI suspend always sends `SET_POWER(SLEEP)` and unconfigures DMA regardless of wake state | Skip `SET_POWER(SLEEP)` if `device_may_wakeup`; **always** save I2C sub-IP regs |

### Key PM Behavioral Differences

1. **I2C sub-IP is in PGD** — always lost during power gating, MUST be saved/restored even with WoT enabled
2. **I2C resume = simple `i2c_subip_regs_restore`** — just writes back saved register values (loop over 15-register array). Only **restore** (hibernate resume) calls full `i2c_subip_init()` (the complete 11-step init sequence)
3. **SPI `restore` ≠ SPI `resume`** — `restore` (hibernate resume) calls `reset_tic()` which does full Touch IC reset + device/report descriptor re-retrieval. `resume` (normal S3 resume) does NOT call `reset_tic()` — it does `port_select → interrupt_config → interrupt_enable → dma_configure → unquiesce → SET_POWER(ON)` without resetting the device
4. **Both SPI and I2C `poweroff` do full `dma_deinit` + `ltr_unconfig`** — goes beyond `dma_unconfigure` to also release DMA resources and unconfigure LTR
5. **I2C suspend skips `SET_POWER(SLEEP)` when wake-enabled** — device must stay responsive for WoT interrupt. **SPI suspend has NO WoT handling** — always sends `SET_POWER(SLEEP)` regardless of wake state
6. **Both SPI and I2C `freeze` are minimal** — SPI freeze: quiesce → dma_unconfigure (NO SET_POWER). I2C freeze: quiesce → disable int → dma_unconfigure (NO SET_POWER, NO i2c_subip_save). Neither modifies device power state (snapshot-for-hibernate doesn't need device state changes)
7. **Both SPI and I2C `thaw` are minimal** — SPI thaw: dma_configure → interrupt_enable → unquiesce. I2C thaw: dma_configure → enable int → unquiesce. Neither sends SET_POWER(ON) (resuming from snapshot, device state unchanged)
8. **`runtime_suspend` calls `pci_save_state()`** — saves PCI config space before runtime suspend (undocumented in HAS)
9. **`SET_POWER` is fire-and-forget (async)** — SPI `SET_POWER(ON)` completes immediately after sending; the kernel does NOT wait for a device response before proceeding. `SET_POWER(SLEEP/OFF)` never receives a response per protocol spec
