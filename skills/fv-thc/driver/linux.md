> **Owner**: willychi | **Platform**: Linux Kernel
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Linux Kernel Driver Details

Linux-specific driver implementation details for THC QuickSPI and QuickI2C drivers.
For shared architecture and cross-platform comparison, see [SKILL.md](SKILL.md).

## Device State Machines

### Linux QuickSPI States (6)
```
QUICKSPI_NONE (0) → QUICKSPI_INITIATED (1) → QUICKSPI_RESETING (2) → QUICKSPI_RESET (3) → QUICKSPI_ENABLED (4) → QUICKSPI_DISABLED (5)
```
- `QUICKSPI_NONE (0)`: Never used in practice — initial state is `QUICKSPI_DISABLED` (set at `quickspi_dev_init` start)
- `QUICKSPI_INITIATED (1)`: dev_init complete (port_select, ACPI, SPI config, LTR, interrupt config, WoT)
- `QUICKSPI_RESETING (2)`: Reset in progress (reset_tic issued)
- `QUICKSPI_RESET (3)`: Reset complete (reset_tic acknowledged, descriptors parsed)
- `QUICKSPI_ENABLED (4)`: DMA active, HID device registered, runtime PM enabled (probe complete)
- `QUICKSPI_DISABLED (5)`: Shutdown/remove path — resources freed

### Linux QuickI2C States (6)
```
QUICKI2C_NONE (0) → QUICKI2C_RESETING (1) → QUICKI2C_RESETED (2) → QUICKI2C_INITED (3) → QUICKI2C_ENABLED (4) → QUICKI2C_DISABLED (5)
```
- `QUICKI2C_NONE (0)`: Never used in practice — initial state is `QUICKI2C_DISABLED` (set at `quicki2c_dev_init` start)
- `QUICKI2C_RESETING (1)`: Reset in progress
- `QUICKI2C_RESETED (2)`: Reset complete (handle_input acknowledged reset)
- `QUICKI2C_INITED (3)`: dev_init complete (port_select, ACPI, I2C config, interrupt config)
- `QUICKI2C_ENABLED (4)`: DMA active, HID device registered, runtime PM enabled (probe complete)
- `QUICKI2C_DISABLED (5)`: Shutdown/remove path — resources freed

Note: QuickI2C reset flow differs (uses PIO I2C reset sequence / TXDMA for SET_POWER+RESET) and transitions reflect that.

### Probe-Time State Transitions

**QuickSPI probe path**:
```
QUICKSPI_DISABLED → QUICKSPI_INITIATED (quickspi_dev_init) → QUICKSPI_RESETING (reset_tic) → QUICKSPI_RESET (reset_tic complete) → QUICKSPI_ENABLED (probe)
```

**QuickI2C probe path**:
```
QUICKI2C_DISABLED → QUICKI2C_INITED (quicki2c_dev_init) → QUICKI2C_RESETING (reset) → QUICKI2C_RESETED (handle_input) → QUICKI2C_ENABLED (probe)
```

## QuickSPI Probe Sequence (pci-quickspi.c `quickspi_probe()`)

Actual probe ordering observed in `pci-quickspi.c` (`quickspi_probe()`):
1. `pcim_enable_device`
2. `pcim_iomap_regions` (BAR0)
3. `pci_alloc_irq_vectors(PCI_IRQ_ALL_TYPES)`
4. `thc_dev_init` (allocate THC device struct)
5. `quickspi_dev_init` — bundles: `thc_port_select` + `quickspi_acpi_get_properties` + `thc_spi_configure` (clock, IO mode, opcodes) + `thc_ltr_config` + `thc_interrupt_config` + `thc_wot_config` — all before probe calls reset
6. `reset_tic()` — ACPI `_RST` + wait for NONDMA_INT + validate RESET_RESPONSE + get device descriptor
7. `thc_dma_init` + `thc_dma_configure`
8. `quickspi_hid_parse` (get HID descriptors)
9. `hid_add_device` (register with HID subsystem)

## QuickI2C Probe Sequence (pci-quicki2c.c `quicki2c_probe()`)

Actual probe ordering observed in `pci-quicki2c.c` (`quicki2c_probe()`):
1. `pcim_enable_device`
2. `pcim_iomap_regions` (BAR0)
3. `pci_alloc_irq_vectors(PCI_IRQ_ALL_TYPES)`
4. `thc_dev_init`
5. `quicki2c_dev_init` — bundles: `thc_port_select` + `quicki2c_acpi_get_properties` + `thc_i2c_configure` (I2C speed, address, Synopsys sub-IP init) + `thc_int_trigger_type_select(false)` (level-triggered for I2C) + `thc_interrupt_config`
6. `quicki2c_hid_send_report` (RESET command via I2C PIO)
7. Wait for reset response
8. `thc_dma_init` + `thc_dma_configure`
9. `quicki2c_hid_parse` (get HID descriptors)
10. `hid_add_device`

## HIDSPI Reset Flow (Linux `reset_tic()`)
```
1. INT_EDG_DET_EN = 1         (edge-triggered — NOT level-triggered)
2. ACPI _RST method call      (acpi_tic_reset() with 'TSR_' signature, NOT GPIO toggle)
3. Wait for NONDMA_INT        (reset response via PIO, 5s timeout — NOT 1s)
4. Read + validate response   (type must be RESET_RESPONSE = 0x03)
5. INT_EDG_DET_EN = 1         (re-assert edge-triggered — kernel 6.17 fix 8fe2cd8)
```
> **⚠️ Previous version was wrong**: Showed GPIO LOW/HIGH toggle with level-triggered interrupts.
> Actual kernel uses ACPI `_RST` method with edge-triggered interrupts throughout.
> Windows HIDSPI driver also uses ACPI `_RST` — consistent across both drivers.

## Linux 11-Step Interrupt Triage
Steps 1-5 (NONDMA, TXN_ERR, BUF_OVRRUN, STALL, FATAL_ERR): early return — single type per invocation.
Steps 6-11 (PIO_DONE, RXDMA1/2_EOF, SWDMA, TXDMA, I2CSUBIP): accumulate into bitmask.

### IRQ Thread PM Handling
The threaded IRQ handler calls `pm_runtime_resume_and_get()` at entry and `pm_runtime_put_autosuspend()` at exit, ensuring the device is in an active power state throughout interrupt processing.

## Linux Suspend / Resume Sequence (quickspi_suspend / quickspi_resume)

Linux suspend (example `quickspi_suspend` sequence):
1. `quickspi_set_power(SLEEP)` — or `thc_i2c_set_power(SLEEP)` for I2C
2. `thc_interrupt_quiesce`
3. `thc_interrupt_enable(false)`
4. `thc_dma_unconfigure` (stop DMA)

Linux resume (example `quickspi_resume` sequence):
1. `thc_port_select` (re-select port type)
2. `thc_spi_configure` / `thc_i2c_configure` (re-init protocol)
3. `thc_dma_init` + `thc_dma_configure`
4. `thc_interrupt_config`
5. `thc_ltr_config`
6. `quickspi_set_power(ON)` / `thc_i2c_set_power(ON)`

## Linux Runtime Suspend

Linux runtime suspend uses LTR mode + `pci_save_state` only — lightweight power transition without full DMA teardown.

## pm_runtime in raw_request

Linux `quickspi_hid_raw_request()` and `quicki2c_hid_raw_request()` call `pm_runtime_resume_and_get()` at entry and `pm_runtime_put_autosuspend()` at exit, ensuring the device is in an active power state before performing PIO/MMIO operations and releasing the PM reference after completion.

## pm_runtime in IRQ Thread

The threaded IRQ handler calls `pm_runtime_resume_and_get()` at entry and `pm_runtime_put_autosuspend()` at exit, ensuring the device is in an active power state throughout interrupt processing.

## quickspi_dev_init Bundles

`quickspi_dev_init` bundles the following operations in order:
- `thc_port_select` — select port type (SPI)
- `quickspi_acpi_get_properties` — read ACPI DSM for SPI config
- `thc_spi_configure` — clock, IO mode, opcodes
- `thc_ltr_config` — LTR latency tolerance values
- `thc_interrupt_config` — interrupt enable/mask setup
- `thc_wot_config` — Wake-on-Touch GPIO configuration

All are executed before probe calls reset.

## quicki2c_dev_init

`quicki2c_dev_init` bundles the following operations:
- `thc_port_select` — select port type (I2C)
- `quicki2c_acpi_get_properties` — read ACPI DSM for I2C config
- `thc_i2c_configure` — I2C speed, address, Synopsys sub-IP init
- `thc_int_trigger_type_select(false)` — level-triggered for I2C (NOT edge-triggered like SPI)
- `thc_interrupt_config` — interrupt enable/mask setup

## Linux output_report Callback Lacks PM

The `output_report` callback path lacks explicit PM handling — output reports sent via the HID output_report callback do not include `pm_runtime_get`/`put` pairs, which is a potential gap. This is shared with the Windows side (see [SKILL.md](SKILL.md)).

## Linux Kernel THC Bug Fixes (6.17–6.20)

| Commit | Kernel | Impact |
|--------|--------|--------|
| `e4aa247` | 6.20 | Wrong register fields updating |
| `f390069` | 6.20 | Wrong register reading |
| `a9a9179` | 6.20 | DMA buffer safety check |
| `0e13150` | 6.20 | DMA unmap nents fix (memory leak) |
| **`a7fc15e`** | **6.20** | **CRITICAL: I2C save pointer arithmetic — D3Cold SnR** |
| `1db9df8` | 6.18 | ACPI DSD ICRS/ISUB length fix |
| **`8fe2cd8`** | **6.17** | **INT_EDG_DET_EN fix — prevents duplicate reads** |
| `6c26c05` | 6.18 | QuickI2C type casting fix |
| `73f3a74` | 6.18 | Enhanced QuickI2C reset flow |
| `c430f56` | 6.17 | Redundant PM runtime calls cleanup |

## Linux Driver File Organization

Typical Linux kernel source layout for the THC driver under `drivers/hid/intel-thc-hid/`:
```
drivers/hid/intel-thc-hid/
├── intel-thc-dev.c     # Core THC device management (port select, SPI/I2C config, LTR)
├── intel-thc-dev.h     # THC device struct, function prototypes
├── intel-thc-dma.c     # DMA engine (init, configure, start, stop, read/write callbacks)
├── intel-thc-dma.h     # DMA function prototypes
├── intel-thc-hw.h      # Register definitions (offsets, bit fields, masks)
├── intel-thc-wot.c     # Wake-on-Touch implementation (thc_wot_config/unconfig, ACPI GPIO mapping)
├── intel-thc-wot.h     # WoT struct definition (gpio_irq, gpio_irq_wakeable)
├── pci-quickspi.c      # QuickSPI PCI driver (probe, remove, PM callbacks)
├── quickspi-dev.h      # QuickSPI device struct, state enum, device IDs
├── quickspi-hid.c/h    # QuickSPI HID interface (parse, raw_request)
├── quickspi-protocol.c/h # QuickSPI HIDSPI protocol (reset, set_power, descriptors)
├── pci-quicki2c.c      # QuickI2C PCI driver (probe, remove, PM callbacks)
├── quicki2c-dev.h      # QuickI2C device struct, state enum, device IDs
├── quicki2c-hid.c/h    # QuickI2C HID interface
├── quicki2c-protocol.c/h # QuickI2C HIDI2C protocol
├── hid-over-spi.h      # HIDSPI protocol structs/constants
├── hid-over-i2c.h      # HIDI2C protocol structs/constants
```

## See Also
- **[SKILL.md](SKILL.md)** — Shared architecture, cross-platform comparison, HSDES workarounds
- **[windows.md](windows.md)** — Windows driver implementation details
