# THC HIDSPI — Linux Kernel Implementation (QuickSPI)

> **Owner**: willychi | **Platform**: Linux Kernel | **Source**: pci-quickspi.c, quickspi-protocol.c, quickspi-hid.c
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

Linux-specific HIDSPI driver details: state machine, probe/remove sequences, suspend/resume/freeze/restore flows, runtime PM, and behavioral notes.

> For protocol spec, report types, ACPI DSM, SPI opcodes, and shared validation points, see [SKILL.md](SKILL.md).
> For Windows implementation, see [windows.md](windows.md).

## QuickSPI Driver States (enum from quickspi-dev.h)

```c
enum quickspi_dev_state {
    QUICKSPI_NONE,         // 0 - Initial/uninitialized
    QUICKSPI_INITIATED,    // 1 - After init started
    QUICKSPI_RESETING,     // 2 - Reset in progress (intermediate state during reset flow)
    QUICKSPI_RESET,        // 3 - After reset complete
    QUICKSPI_ENABLED,      // 4 - Device enabled, touch input active
    QUICKSPI_DISABLED,     // 5 - Device disabled
};
```

| State | Description |
|-------|-------------|
| `QUICKSPI_NONE` | Initial — no hardware interaction yet |
| `QUICKSPI_INITIATED` | After init started (dev_init called) |
| `QUICKSPI_RESETING` | Intermediate state — reset in progress |
| `QUICKSPI_RESET` | After device reset and reset response parsed |
| `QUICKSPI_ENABLED` | Device enabled, DMA active, touch input operational |
| `QUICKSPI_DISABLED` | Touch disabled (full remove or fatal error). Also the initial state set at `quickspi_dev_init` start |

> **Note**: Initial state is set to `QUICKSPI_DISABLED` at the start of `quickspi_dev_init()`, not `QUICKSPI_NONE`. The `QUICKSPI_RESETING` intermediate state is set during the reset flow before reset completes.

## QuickSPI Probe Sequence (14 Steps)

> **Source**: `pci-quickspi.c` — `quickspi_probe()` (kernel 6.17+)

| Step | Operation | Function |
|------|-----------|----------|
| 1 | Allocate driver state | `devm_kzalloc(quickspi_driver_data)` |
| 2 | Enable PCI device | `pcim_enable_device()` |
| 3 | Map BAR0 MMIO | `pcim_iomap_regions()` — 32KB MMIO |
| 4 | Set DMA mask | `dma_set_mask_and_coherent(DMA_BIT_MASK(64))` with 32-bit fallback |
| 5 | Allocate IRQ | `pci_alloc_irq_vectors(PCI_IRQ_ALL_TYPES)` |
| 6 | Register ISR | `devm_request_threaded_irq()` |
| 7 | Parse ACPI DSM | Read all 3 DSM GUIDs (HIDSPI, QuickSPI, Platform) |
| 8 | Dev init (interrupts + port/SPI config) | `quickspi_dev_init()` — quiesces interrupts, then `thc_port_select()` + `thc_spi_read_config()` + `thc_spi_write_config()` + `thc_interrupt_config()` + `thc_interrupt_enable()`. Interrupts are configured INSIDE dev_init BEFORE reset |
| 9 | Send device RESET | `reset_tic(qsdev)` — ACPI `_RST` + wait for reset response (NONDMA_INT/PIO) + validate RESET_RESPONSE + get device descriptor |
| 10 | Initialize DMA (AFTER reset) | `quickspi_alloc_report_buf()` + `quickspi_dma_init()` (which bundles `thc_dma_set_max_packet_sizes()` + `thc_dma_allocate()` + `thc_dma_configure()`) — DMA is configured after device reset |
| 11 | Parse HID descriptors | `quickspi_get_report_descriptor()` — read report descriptor via TXDMA request → RXDMA response |
| 12 | Register HID device | `hid_allocate_device()` + `hid_add_device()` |
| 13 | Setup runtime PM | `pm_runtime_set_autosuspend_delay(5000)` + `pm_runtime_enable()` |
| 14 | Set state ENABLED | `driver_data->state = QUICKSPI_ENABLED` |

> **Note**: `PROBE_PREFER_ASYNCHRONOUS` flag is set, so probe may run concurrently with other device probes.
> **Note**: `quickspi_dev_init()` quiesces interrupts BEFORE `thc_port_select()`. Interrupts are configured inside `quickspi_dev_init()`, not after reset. Only DMA init happens after reset.

## QuickSPI Remove Sequence (6 Steps)

> **Source**: `pci-quickspi.c` — `quickspi_remove()` (kernel 6.17+)

| Step | Operation | Function |
|------|-----------|----------|
| 1 | Unregister HID | `hid_destroy_device()` |
| 2 | Deinitialize DMA | `thc_dma_deinit()` — unconfigure + release |
| 3 | Prevent runtime suspend | `pm_runtime_get_noresume(qsdev->dev)` |
| 4 | Dev deinit (sets state DISABLED) | `quickspi_dev_deinit()` — calls `thc_interrupt_enable(false)` + `thc_ltr_unconfig()` + `thc_wot_unconfig()` + sets `state = QUICKSPI_DISABLED` |
| 5 | Disable PCI bus mastering | `pci_clear_master()` |

> **Note**: There is no explicit `thc_interrupt_quiesce(true)` call in the remove path. `quickspi_dev_deinit()` handles interrupt disable, LTR unconfig, and WoT unconfig internally.

## QuickSPI Shutdown Handler (2 Steps)

The driver registers a PCI `shutdown` callback that performs a minimal teardown (order and actions differ from full remove):
1. `thc_dma_deinit()` — deinitialize DMA engines (unconfigure + release PRD resources)
2. `quickspi_dev_deinit()` — disable interrupts, unconfigure LTR, unconfigure WoT

> **Note**: `quickspi_shutdown()` does NOT call `thc_interrupt_quiesce()`, `hid_destroy_device()`, or `pci_clear_master()`. Shutdown is intentionally lightweight compared to the full `quickspi_remove()` path.

## HIDSPI Reset Flow (Linux Kernel Implementation)

> **Source**: `quickspi-protocol.c` — `quickspi_reset()` (kernel 6.17+)

The reset flow requires a **double edge-trigger** pattern (kernel 6.17 fix):

1. Set GPIO interrupt to **edge-triggered** (first time)
1b. **Quiesce and un-quiesce interrupt handling**: `thc_interrupt_quiesce(true)` is called during `dev_init` to fully quiesce interrupts before reset. Then `thc_interrupt_quiesce(false)` is called inside `reset_tic()` to un-quiesce before waiting for the NONDMA_INT reset response. This sequence prevents stale interrupt processing during the reset window while allowing the reset-complete interrupt through.
2. Assert device reset via ACPI `_RST` method (uses reversed signature `'TSR_'` in Windows ACPI implementation)
3. Wait for reset response via **NONDMA_INT** path (PIO read, NOT RXDMA)
4. Parse reset response (must be type `RESET_RESPONSE` = `0x03`)
5. Set GPIO interrupt to **edge-triggered** (second time — kernel 6.17 fix `8fe2cd8`)
6. Read device descriptor via PIO
7. Read report descriptor via TXDMA request → RXDMA response

> **⚠️ Critical**: `reset_tic()` does **NOT** send `SET_POWER(ON)`. The power-on command is sent separately in the resume flow after reset completes (e.g., in `resume` callback). The second `set_edge_trigger` call (step 5) was added to fix a race condition where the interrupt mode reverted between reset response and descriptor read. Verify on kernels < 6.17.

> **SwAS vs implementation note**: QuickSPI SwAS describes a conservative initialization window that can begin in level-triggered mode before switching to edge-triggered after the first stable reset interrupt. Current Linux implementation keeps edge-triggered handling throughout `reset_tic()` and re-asserts edge mode after reset response. Keep both views documented to avoid false mismatches during audits.

## Input Data Dispatch Table (Linux)

> **Source**: `quickspi-protocol.c` — `quickspi_handle_input_data()`

After RXDMA receives data, the **input report type** field in the body header determines dispatch. Values are from `enum input_report_type` in `hid-over-spi.h`:

| Body Type | Value | Handler | Description |
|-----------|-------|---------|-------------|
| `DATA` | `0x01` | `hid_input_report(HID_INPUT_REPORT)` | Normal touch data → HID subsystem |
| `RESET_RESPONSE` | `0x03` | Reset completion signal | Device reset acknowledged |
| `COMMAND_RESPONSE` | `0x04` | `quickspi_handle_response()` | Response to host command |
| `GET_FEATURE_RESPONSE` | `0x05` | Copy to `report_buf` → wake `get_report_cmpl` | Feature report data (returned via `raw_request` callback, NOT directly to HID core) |
| `DEVICE_DESCRIPTOR_RESPONSE` | `0x07` | Stored as device descriptor | Device descriptor response |
| `REPORT_DESCRIPTOR_RESPONSE` | `0x08` | Stored for later parsing | Report descriptor response |
| `SET_FEATURE_RESPONSE` | `0x09` | Completion signal | ACK for SET_FEATURE |
| `OUTPUT_REPORT_RESPONSE` | `0x0A` | Completion signal | ACK for output report |
| `GET_INPUT_REPORT_RESPONSE` | `0x0B` | Copy to `report_buf` → wake `get_report_cmpl` | On-demand input report (returned via `raw_request` callback, NOT directly to HID core) |

> **Note**: `OUTPUT_REPORT_RESPONSE` (`0x0A`) is suppressed if `wFlags` bit 0 (`NoOutputReportAck`) is set in device descriptor. Values `0x00`, `0x02`, `0x06`, and `0x0F` are defined as `INVALID` in the enum.

## Runtime Power Management

| Parameter | Value | Notes |
|-----------|-------|-------|
| Auto-suspend delay | **5000 ms** | `pm_runtime_set_autosuspend_delay(dev, 5000)` |
| PM strategy | `pm_runtime_use_autosuspend` | Delayed suspend to avoid frequent transitions |
| Initial state | Active | `pm_runtime_set_active(dev)` at probe |
| Runtime PM | Enabled | `pm_runtime_enable(dev)` at probe completion |

> **Note**: Both HIDSPI and HIDI2C use the same 5000ms auto-suspend delay (`DEFAULT_AUTO_SUSPEND_DELAY_MS`).

## HIDSPI Protocol Behavioral Notes (Linux)

### SET_POWER is Asynchronous (Fire-and-Forget)
- `SET_POWER(ON)` is sent via TXDMA but the kernel does **NOT** wait for a device response before proceeding
- `SET_POWER(SLEEP)` and `SET_POWER(OFF)` never receive a response per protocol spec
- **Validation point**: Do not expect a synchronous ACK after SET_POWER(ON) in timing-sensitive tests

### Error Recovery: `try_recover()` → Permanent DISABLED
- If the QuickSPI driver enters error state and `try_recover()` fails, the device transitions to **permanent `DISABLED` state**
- There is **no automatic re-recovery** — the device remains disabled until the next full driver reload or system reboot
- **Validation point**: After inducing a protocol error, verify that successful recovery returns to `ENABLED`. If recovery fails, confirm the device stays in `DISABLED` and does not attempt further operations

### No WoT Handling in SPI Suspend
- Unlike HIDI2C (which checks `device_may_wakeup()` and conditionally skips `SET_POWER(SLEEP)`), the **SPI suspend path has NO WoT handling**
- SPI suspend **always** sends `SET_POWER(SLEEP)` (HIDSPI_SLEEP, not OFF) and unconfigures DMA regardless of wake state
- **Validation point**: WoT from SPI sleep states may not work as expected — verify WoT behavior is tested through the I2C path or alternate wake mechanisms

### Freeze / Restore / Runtime Suspend Behavioral Details

**`quickspi_freeze`** (hibernate freeze):
- Does **NOT** send SET_POWER to the device
- Only quiesces interrupts + unconfigures DMA
- **Validation point**: Device remains powered during freeze — no power command sent

**`quickspi_restore`** (hibernate restore):
- Performs full SPI reconfiguration (port_select, spi_configure, interrupt config, reset, DMA init)
- Calls `thc_change_ltr_mode(THC_LTR_MODE_ACTIVE)` to restore active LTR
- **Validation point**: Full device reinitialization occurs on restore, similar to probe

**Runtime suspend** (`quickspi_runtime_suspend`):
- Only changes LTR mode + calls `pci_save_state()`
- Does **NOT** send SET_POWER to the device
- Does **NOT** stop DMA
- **Validation point**: Runtime suspend is very lightweight — device stays in active power state

### HID Bus Registration
- QuickSPI registers with HID subsystem using `bus_type = BUS_PCI` (not BUS_SPI or BUS_I2C)
- `set_report` callback skips the first byte (report ID) when writing to the device — the report ID is passed separately as `reportnum`
- `input_buf` is sized to `max(report_desc_len, max_input_len)` — whichever is larger

### SPI_LOW_FREQ_EN Threshold (Linux)
- Threshold: **17,857,100 Hz** (125MHz ÷ 7)
- If `selected_freq <= 17,857,100` → set `SPI_LOW_FREQ_EN = 1`

### WCL Uses PTL driver_data
- WCL QuickSPI uses `&ptl` driver_data, which gives it the LNL max packet size of 256 (4 KB)
