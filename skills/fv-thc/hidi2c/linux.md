# THC HIDI2C — Linux Kernel Implementation

> **Owner**: willychi | **Platform**: Linux Kernel | **Source**: pci-quicki2c.c, quicki2c-protocol.c, quicki2c-hid.c
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

Linux-specific QuickI2C driver implementation details. For shared protocol spec and I2C sub-IP HW, see [SKILL.md](SKILL.md). For Windows implementation, see [windows.md](windows.md).

## QuickI2C Driver States (Linux `quicki2c-dev.h`)

```c
enum quicki2c_dev_state {
    QUICKI2C_NONE,         // 0 — Initial/uninitialized
    QUICKI2C_RESETING,     // 1 — Reset in progress (intermediate state during reset flow)
    QUICKI2C_RESETED,      // 2 — After reset complete
    QUICKI2C_INITED,       // 3 — After init
    QUICKI2C_ENABLED,      // 4 — Device enabled, touch input active
    QUICKI2C_DISABLED,     // 5 — Device disabled
};
```

> **Note**: Initial state is set to `QUICKI2C_DISABLED` at the start of `quicki2c_dev_init()`. The `QUICKI2C_RESETING` intermediate state is set during the reset flow before reset completes.

## Probe & Init Sequence (Linux Kernel — ~14 Steps)

> **Source**: `pci-quicki2c.c` — `quicki2c_probe()` (kernel 6.17+)

| Step | Operation | Function |
|------|-----------|----------|
| 1 | Allocate driver state | `devm_kzalloc(quicki2c_driver_data)` |
| 2 | Enable PCI device | `pcim_enable_device()` |
| 3 | Map BAR0 MMIO | `pcim_iomap_regions()` — 32KB MMIO |
| 4 | Set DMA mask | `dma_set_mask_and_coherent(DMA_BIT_MASK(64))` with 32-bit fallback |
| 5 | Allocate IRQ vectors | `pci_alloc_irq_vectors(MSI)` |
| 6 | Register ISR | `devm_request_threaded_irq()` — hardirq + threaded handler |
| 7 | Parse ACPI DSM | Read HIDI2C DSM (`3CDFF6F7-...`) + Platform DSM (`84005682-...`) |
| 8 | Read ACPI ICRS + ISUB | `quicki2c_get_acpi_resources()` — device_address, connection_speed, sub-IP config |
| 9 | Dev init (I2C sub-IP + interrupts) | `quicki2c_dev_init()` — sets state to DISABLED, then `thc_port_select()` + `thc_i2c_subip_init()` + `thc_interrupt_config()` + `thc_interrupt_enable()` |
| 10 | Read HID descriptor (BEFORE DMA) | Via PIO — 30 bytes from HID descriptor register (`quicki2c_get_device_descriptor()`). Device descriptor read happens BEFORE dma_init and BEFORE set_power/reset |
| 11 | Allocate report buffers (BEFORE DMA) | `quicki2c_alloc_report_buf()` — allocates DMA buffers sized from descriptor. If `max_output_len=0`, overrides to `SZ_4K`. Done BEFORE `dma_init` |
| 12 | Initialize + configure DMA | `thc_dma_init()` + `thc_dma_configure()` — allocate PRD rings + program PRD base addresses |
| 13 | Un-quiesce interrupts | `thc_interrupt_quiesce(false)` — separate call to un-quiesce interrupts AFTER dma_init but BEFORE set_power |
| 14 | **SET_POWER ON + RESET device** | Via TXDMA (`write_cmd_to_txdma`) — wake device then send RESET command. Wait for `0x0000` sentinel on RXDMA (5s timeout) |
| 15 | Parse report descriptor | Read report descriptor via **SWDMA** |
| 16 | Configure LTR | `thc_ltr_config()` — active + LP LTR values from Platform DSM |
| 17 | Register HID device | `hid_allocate_device()` + `hid_add_device()` |
| 18 | Setup runtime PM | `pm_runtime_set_autosuspend_delay(5000)` + `pm_runtime_enable()` + `pm_runtime_put_autosuspend()` |

> **Key differences from HIDSPI probe**: (1) HIDI2C reads the device descriptor and allocates report buffers BEFORE dma_init (steps 10-11), while SPI sends reset BEFORE descriptor read in `reset_tic`. (2) HIDI2C reads report descriptor via **SWDMA** (SPI uses TXDMA request → RXDMA response). (3) HIDI2C has no `set_edge_trigger` calls (level-triggered interrupt throughout). (4) `PROBE_PREFER_ASYNCHRONOUS` flag is set, so probe may run concurrently with other device probes. (5) `quicki2c_probe` calls `thc_interrupt_quiesce(false)` AFTER `dma_init` but BEFORE `set_power` (step 13). (6) `quicki2c_alloc_report_buf`: if `max_output_len=0`, overrides to `SZ_4K`. (7) `quicki2c_dma_adv_enable` clamps to smaller of `max_frame_size` vs `max_input_len`.

## Linux I2C Sub-IP Init (10 PIO Operations)

The Linux kernel `thc_i2c_subip_init()` programs the I2C sub-IP via PIO opcode `0x13` (write sub-IP register):

| Step | Register | Value | Notes |
|------|----------|-------|-------|
| 1 | `IC_ENABLE` | `0` | Disable before configuration |
| 2 | `IC_CON` | `0x0663` | **Direct write** — MASTER_MODE + SPEED=01 + RESTART_EN + SLAVE_DISABLE + RX_FIFO_FULL_HLD_CTRL + STOP_DET_IF_MASTER_ACTIVE |
| 3 | `IC_TAR` | Device addr | From ACPI ICRS `device_address` |
| 4 | `IC_SS/FS_SCL_HCNT/LCNT` | Timing values | Per speed mode from ACPI ISUB or defaults |
| 5 | `IC_INTR_MASK` | `0x7FFF` | All I2C interrupts |
| 6 | `IC_RX_TL` | 62 | RX FIFO threshold |
| 7 | `IC_TX_TL` | 0 | TX FIFO threshold |
| 8 | `IC_DMA_CR` | `0x03` | TX+RX DMA enable |
| 9 | `IC_DMA_TDLR` | 7 | DMA TX data level |
| 10 | `IC_DMA_RDLR` | 7 | DMA RX data level |
| 11 | `IC_ENABLE` | `1` | Enable after configuration |

> **Linux vs Windows init**: Linux writes IC_CON as a **direct write** of `0x0663` (not read-modify-write). Linux does NOT program IC_SDA_HOLD. Linux does NOT set PORT_TYPE in the init sequence (set separately). See [windows.md](windows.md) for the Windows 13-step init comparison.

## Linux I2C Timing Defaults

| Speed Mode | Speed | Hcnt | Lcnt | Formula |
|------------|-------|------|------|---------|
| Standard (SM) | 100 kbps | 0x267 (615) | 0x271 (625) | Lcnt=125/(2×Speed_Mbps), Hcnt=Lcnt-10 |
| Fast (FM) | 400 kbps | 0x92 (146) | 0x9C (156) | Same formula |
| Fast Mode Plus (FMP) | 1 Mbps | 0x34 (52) | 0x3E (62) | Same formula |
| Ultra-Fast (UFm) | 5 MHz | — | — | Write-only mode |

Use SM fields (IC_SS_SCL_HCNT/LCNT) for ≤100 kbps. Use FM fields (IC_FS_SCL_HCNT/LCNT) for >100 kbps.

> **Speed rounding / DSM behavior (SwAS)**: The QuickI2C SwAS expects the OS/driver to round the `connection_speed` provided in ACPI (ICRS/_DSM) down to the nearest supported Synopsys timing mode and program the corresponding HCNT/LCNT values. The SwAS provides recommended nominal connection speeds 100 kbps (Standard), 400 kbps (Fast), 1 Mbps (Fast Plus). Drivers should clamp the requested `connection_speed` to these ranges and select the matching HCNT/LCNT timing fields. (QuickI2C SwAS v1.0)

## Linux I2C Speed Mode Selection

The kernel does NOT use the ACPI enum values directly. Instead, it reads `connection_speed` (in Hz) from ACPI ICRS and selects mode by range:

| `connection_speed` Range | IC_CON SPEED | Mode |
|--------------------------|-------------|------|
| ≤ 100,000 Hz | `0x1` (Standard) | SM — uses `IC_SS_SCL_HCNT/LCNT` |
| 100,001 – 400,000 Hz | `0x2` (Fast) | FM — uses `IC_FS_SCL_HCNT/LCNT` |
| 400,001 – 1,000,000 Hz | `0x2` (Fast) | FMP — uses `IC_FS_SCL_HCNT/LCNT` (same as FM) |
| > 1,000,000 Hz | `0x3` (High-Speed) | HS — uses `IC_HS_SCL_HCNT/LCNT` |

> **Validation point**: FMP uses the same IC_CON SPEED=0x2 as FM — the only difference is the SCL timing values. Verify the programmed HCNT/LCNT values match the target frequency.

## Linux I2C Interrupt Enable Mask

9 of 11 interrupt bits are enabled: `RX_UNDER(17) | RX_OVER(18) | RX_FULL(19) | TX_OVER(20) | TX_ABRT(22) | SCL_STUCK_AT_LOW(24) | STOP_DET(25) | START_DET(26) | MST_ON_HOLD(27)`.

**NOT enabled**: TX_EMPTY(21) and ACTIVITY(23 — no enable bit).

> **Key difference from Windows**: Linux enables START_DET(26) and STOP_DET(25); Windows does NOT enable these two bits — Windows only enables 7 of 11.

## Linux IC_SDA_HOLD — NOT Programmed

The **Linux kernel ignores** all SDA hold fields from ACPI ISUB (`SMTD/SMRD/FMTD/FMRD/FPTD/FPRD/HMTD/HMRD`). `IC_SDA_HOLD` is NOT programmed during `thc_i2c_subip_init()`. The ISUB fields are parsed but the values are never written to the register. Only SCL timing (HCNT/LCNT) and override control fields are used.

> **Contrast with Windows**: Windows DOES program `IC_SDA_HOLD` using the ISUB fields (SMTD/FMTD/HMTD for TX hold, SMRD/FMRD/HMRD for RX hold). See [windows.md](windows.md).

## Linux I2C Speed Mode Thresholds (from `quicki2c-dev.h`)

| Constant | Value (Hz) | Description |
|----------|-----------|-------------|
| `QUICKI2C_SUBIP_STANDARD_MODE_MAX_SPEED` | 100,000 | Standard mode ceiling (≤100 kHz) |
| `QUICKI2C_SUBIP_FAST_MODE_MAX_SPEED` | 400,000 | Fast mode ceiling (≤400 kHz) |
| `QUICKI2C_SUBIP_FASTPLUS_MODE_MAX_SPEED` | 1,000,000 | Fast-mode Plus ceiling (≤1 MHz) |
| `QUICKI2C_SUBIP_HIGH_SPEED_MODE_MAX_SPEED` | 3,400,000 | High-speed mode ceiling (≤3.4 MHz) |

> **Usage**: `quicki2c_set_i2c_speed()` uses these thresholds to select the `THC_I2C_SPEED_MODE` enum value (STANDARD=1, FAST_AND_PLUS=2, HIGH_SPEED=3) and program `IC_CON.SPEED`.

## Linux Default LTR Values (from `quicki2c-dev.h`)

| Constant | Value | Description |
|----------|-------|-------------|
| `QUICKI2C_DEFAULT_ACTIVE_LTR_VALUE` | 5 | Default active LTR value (5 × scale units) |
| `QUICKI2C_DEFAULT_LP_LTR_VALUE` | 500 | Default low-power LTR value (500 × scale units) |
| `DEFAULT_INTERRUPT_DELAY_US` | 1000 (USEC_PER_MSEC) | Default interrupt delay (1 ms) |

> **Usage**: These defaults are used if ACPI DSM does not provide LTR values. `thc_change_ltr_mode()` programs the `LTR_CTRL` register with these values during power state transitions.

## PTL Advanced I2C Features (kernel `pci-quicki2c.c`)

PTL platforms provide enhanced I2C configuration via ACPI `ddata`:

| Feature | Default | PTL Value | Register |
|---------|---------|-----------|----------|
| `max_detect_size` | 64B | **255B** | `THC_M_PRT_SPI_ICRRD_OPCODE` |
| `max_interrupt_delay` | 0 (disabled) | **256** (×10µs = 2.56ms) | `THC_M_PRT_SPI_DMARD_OPCODE` |

> **Validation point**: PTL should have max_detect_size=255 and interrupt_delay=256. Non-PTL platforms use defaults.
> **WCL note**: WCL uses PTL `driver_data` (`&ptl`), inheriting max_detect_size=255 and max_interrupt_delay=256.

### PTL I2C Kernel Constants

For PTL platforms the kernel uses the following I2C-related constants (overrides vs defaults):

- `MAX_RX_DETECT_SIZE_PTL = 255`  (default on other platforms = 8)
- `MAX_RX_INTERRUPT_DELAY = 256`
- `DEFAULT_INTERRUPT_DELAY_US = 1000`

These constants originate from the QuickI2C driver and are PTL-specific overrides used to configure the Synopsys sub-IP behavior and interrupt servicing delays.

> **Interrupt Servicing Delay**: See `hidi2c/SKILL.md` for the SwAS-mandated interrupt servicing delay requirements per platform (PTL/WCL: 1ms fixed, NVL+: configurable).

## Linux Suspend/Resume Flows

> **Suspend conditional**: In the HIDI2C suspend path, `SET_POWER(SLEEP)` is only sent when `!device_may_wakeup()`. If the device may wake (WoT enabled), the driver skips SET_POWER(SLEEP) to keep the device in a wake-capable state. See `fv-thc/power` PM callback comparison table for full details.

### Power-Off Behavior (`quicki2c_poweroff`)
- `quicki2c_poweroff` sends `SET_POWER(SLEEP)` but **IGNORES the return value** — power-off continues regardless of whether the device acknowledged the sleep command
- **Validation point**: If the device NAKs or fails to respond to SET_POWER(SLEEP) during power-off, the driver proceeds anyway

## Linux Runtime Power Management

| Parameter | Value | Notes |
|-----------|-------|-------|
| Auto-suspend delay | **5000ms** | `pm_runtime_set_autosuspend_delay(dev, DEFAULT_AUTO_SUSPEND_DELAY_MS)` where `DEFAULT_AUTO_SUSPEND_DELAY_MS = 5000` |
| PM usage count | Initially active | `pm_runtime_use_autosuspend()` + `pm_runtime_put_autosuspend()` |

> **Note**: Both HIDI2C and HIDSPI use the same 5000ms auto-suspend delay (`DEFAULT_AUTO_SUSPEND_DELAY_MS`). The unused constant `QUICKI2C_RPM_TIMEOUT_MS = 500` exists in the kernel but is not used for autosuspend configuration.

## Linux IRQ Thread (`quicki2c_irq_thread`)

- `quicki2c_irq_thread` checks for `THC_UNKNOWN_INT` — this is unique to QuickI2C; QuickSPI does NOT check for unknown interrupts
- **Validation point**: Inject an unexpected interrupt and verify QuickI2C logs/handles THC_UNKNOWN_INT

## Linux Report Buffer Allocation (`quicki2c_alloc_report_buf`)

- If `max_output_len=0` in the HID descriptor, the kernel overrides to `SZ_4K` (4096 bytes)
- `quicki2c_dma_adv_enable` clamps to smaller of `max_frame_size` vs `max_input_len`
- **Input buffer minimum 4KB**: Kernel enforces `min(wMaxInputLength, 4096)` — even if device reports smaller, buffer is at least 4KB
- **Validation point**: Verify buffer allocation with `max_output_len=0` produces 4KB buffers

## Linux-Specific Validation Points

- **output_report callback has NO PM runtime handling**: `quicki2c_hid_output_report()` (the `.output_report` HID callback) does NOT call `pm_runtime_get`/`put` — potential bug if device is runtime-suspended. Note: `quicki2c_hid_raw_request()` DOES have proper PM handling (`pm_runtime_resume_and_get` / `pm_runtime_put_autosuspend`). All other HID ops (parse, start, stop, open, close) also have proper PM handling
- **ARB_POLICY forced to FRAME_BOUNDARY**: Kernel sets `THC_M_PRT_CONTROL.arb_policy` to frame boundary arbitration for I2C mode
- **Reset fallback**: On reset timeout, kernel performs PIO read of 2 bytes from `wInputRegister` to clear stale data before failing
- **PROBE_PREFER_ASYNCHRONOUS**: probe may run concurrently with other device probes
- **I2C Bus Clear Feature NOT enabled**: Neither SDA stuck recovery nor bus clear feature control is set in the kernel `thc_i2c_subip_init()`. However, `SCL_STUCK_AT_LOW` interrupt (bit 24) IS enabled — detection works, but automatic recovery does not

## See Also
- **[SKILL.md](SKILL.md)** — Shared HIDI2C protocol spec and I2C sub-IP HW reference
- **[windows.md](windows.md)** — Windows HIDI2C implementation
- **`fv-thc/wot`** — Wake-on-Touch over I2C: vGPIO wake path (GPIO IP → PMC, NOT THC IP), PADCFGLOCK_VGPIO_THC0 must be 0x0, QuickI2C PM callbacks (WoT-aware suspend skips SET_POWER(SLEEP)), I2C sub-IP reg save/restore for D3Cold, HSDES sightings (15018635096, 16029769688)
- **Reference**: `fv-thc/docs/thc_known_issues.md` — SPI_RD_MPS RTL bug in I2C mode
- **Reference**: `fv-thc/docs/thc_hidspi_hidi2c_kernel_study.md` — Full kernel source analysis
