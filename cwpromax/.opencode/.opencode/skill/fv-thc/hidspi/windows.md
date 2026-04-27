# THC HIDSPI — Windows Implementation

> **Owner**: willychi | **Platform**: Windows | **Source**: drivers.platform.ipts.hspi-driver
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

Windows-specific HIDSPI driver details: DeviceState enum, HidSpiCx callbacks, D0Exit flow, SET_POWER gating, filter driver, and behavioral differences.

> For protocol spec, report types, ACPI DSM, SPI opcodes, and shared validation points, see [SKILL.md](SKILL.md).
> For Linux implementation, see [linux.md](linux.md).

## Windows HIDSPI Driver Architecture (summary)

- Uses WDF/KMDF model with core entry points: DriverEntry → WdfDriverCreate → DeviceAdd → PrepareHardware → D0Entry
- Key HAL components: HalSPI, HalDMA, HalLTR, HalPIO, HalINT, HalGPIO
- Integrates with Microsoft HidSpiCx class extension for HID-over-SPI
- Filter driver (IPTS) sits below THC driver for GPU-direct paths; many filter functions stubbed in shipped driver

## Windows-Only PCI Device IDs (HIDSPI)

> **Source**: Windows HIDSPI driver (`hidspi_hal.h`, v4.0.0.9000) — Phase 6 audit

| Platform | THC0 Device ID | THC1 Device ID | Notes |
|----------|---------------|---------------|-------|
| RPL-S | `0x7A50` | `0x7A51` | Not in Linux driver |
| RPL-H | `0x7A58` | `0x7A59` | Not in Linux driver |
| ADL-P | `0x51D0` | `0x51D1` | Not in Linux driver |
| ADL-N | `0x54D0` | `0x54D1` | Not in Linux driver |
| MTL-P | `0x7E49` | `0x7E4B` | Same as Linux |
| MTL-S | `0x7F59` | `0x7F5B` | Not in Linux driver |

> **⚠️ Phase 6**: Windows driver supports 6 platform families (ADL/RPL/MTL) with 12 Device IDs not present in Linux. RPL-S shares DID `0x7A50/7A51` with ADL-LP HIDI2C driver — same silicon, different protocol binding.

## Windows HIDSPI Behavioral Differences (Phase 6)

> **Source**: Windows HIDSPI driver v4.0.0.9000 — Phase 6 audit. Full report: `_win_drivers/hidspi/WINDOWS_HIDSPI_DRIVER_ANALYSIS_REPORT.md`

### Key Constants (Windows vs Linux)

| Constant | Windows Value | Linux Value | Notes |
|----------|-------------|-------------|-------|
| HIDSPI_VERSION | `0x03` | `0x03` | Same |
| SYNC_CONST | `0x5A` | `0x5A` | Same |
| DEFAULT_READ opcode | `0x0B` | `0x0B` | Same |
| DUAL_READ opcode | `0xBB` | `0xBB` | Same |
| QUAD_READ opcode | `0xEB` | `0xEB` | Same |
| DEFAULT_WRITE opcode | `0x02` | `0x02` | Same |
| Port0 MMIO offset | `0x1000` | `0x1000` | Same |
| MAX_BLOCK_SIZE | 64 | 64 (`MAX_PIO_BC`) | Same |
| TIC_BULK_AREA | `0x1000` | — | Windows-only constant |
| TOUCH_ID (`$TIC`) | `0x43495424` | — | TIC ID register expected value |
| GetFeature timeout | **3 seconds** | **5 seconds** | Windows is more aggressive |
| Auto-suspend delay | — | 5000 ms | Windows uses own doze timer |

### SPI_LOW_FREQ_EN Threshold (Windows)
- Threshold: **17 MHz** (vs Linux 17,857,100 Hz)

### ADL A1 Opcode Register Overlay (HSD — Windows Only)

On ADL A-stepping, the Windows driver applies an opcode register overlay workaround:
- `ICRRD` opcode register aliased to `0x14` (normally `DMARD` offset)
- `WR_OPCODE` register moved to `0x18`
- **Impact**: ADL A1 silicon has different opcode register layout than B0+
- **Validation point**: If testing on ADL A-step, verify opcode register addresses

### SpiBusLock / IELock — NO-OP Stubs (CRITICAL)

The Windows HIDSPI driver's `SpiBusLock()` and `IELock()` functions are **NO-OP stubs** that return immediately:
- **Root cause**: Full locking implementation caused BSOD
- **Impact**: No SPI bus synchronization between concurrent accessors
- **Validation point**: Multi-threaded SPI bus access may produce undefined behavior on Windows; Linux uses `thc_bus_lock` mutex

### ACPI _RST for Device Reset (Windows vs Linux)

| Aspect | Windows HIDSPI | Linux QuickSPI |
|--------|---------------|----------------|
| Reset method | **ACPI `_RST`** method | ACPI `_RST` method |
| THC DEVRST register | Commented out (NOT used) | Used via `thc_reset_tic()` |
| Surface WA | Checks MSFT Surface quiesce before reset | Not applicable |

> **⚠️ Phase 6**: Windows HIDSPI driver has the THC DEVRST path commented out — it exclusively uses ACPI `_RST`. Linux uses both ACPI `_RST` AND THC DEVRST register. Verify on platforms where `_RST` ACPI method is absent.

### Write Interrupt Polling Workaround (HSD 14016760177)

Windows HIDSPI driver disables write interrupts and uses polling instead:
- **Registry key**: `UseWriteInterrupts` = `false` (default)
- **Poll interval**: 100µs per iteration
- **Timeout**: 500ms total
- **Impact**: TXDMA completion is polled, not interrupt-driven
- **Validation point**: Linux uses interrupt-driven TXDMA completion — verify timing differences

### RxDMA2 Throttle Mechanism

> **⚠️ General THC behavior (not Windows-specific)**: Throttling at 8 free buffers is the standard THC throttle threshold — half of the 16 PRD tables used for RXDMA2. QuickSPI SwAS v1.0 documents this as the general throttle point for all implementations.

- **Threshold**: `RXDMA2_THROTLE_THRESHOLD = 8` (half of 16 PRD tables)
- **Behavior**: When free RXDMA2 buffers drop to ≤8, throttle kicks in — host quiesces device interrupts to allow buffer consumption to catch up
- **Windows constant**: `RXDMA2_THROTLE_THRESHOLD = 8` in driver source
- **Linux**: No explicit named threshold constant — relies on PRD ring depth and coalescing, but the underlying HW behavior is the same

### Wacom SET_POWER_ON Response Fabrication

Windows HIDSPI driver fabricates SET_POWER_ON response for Wacom devices:
- **Trigger**: `content_length == 0` in device response after SET_POWER_ON
- **Action**: Fabricates response with `length = 1`, `content = 0x1`
- **Root cause**: Wacom devices return empty response to SET_POWER_ON
- **Validation point**: Verify Wacom BOM52 SET_POWER_ON response handling on Linux (may silently fail)

### Wacom Special Read Opcode 0x0C

Windows HIDSPI driver uses a **non-standard SPI read opcode** for Wacom devices:
- **Opcode**: `0x0C` (instead of standard HIDSPI read opcode)
- **Usage**: Reading report descriptors from Wacom touch controllers
- **Context**: Wacom devices require vendor-specific command framing for descriptor retrieval
- **Linux**: Linux QuickSPI driver does NOT implement Wacom-specific opcode override — uses standard HIDSPI read opcode for all vendors
- **Validation point**: If Wacom report descriptor retrieval fails on Linux, check if device requires opcode 0x0C

### bAwaitingSendSetPowerOnResponse Gate (CRITICAL)

During power-on wake sequence, the Windows driver sets a gate flag that **drops ALL incoming packets** until the SET_POWER_ON response is received:
- Flag: `bAwaitingSendSetPowerOnResponse`
- **Impact**: Touch input lost during wake-up window until device acknowledges power-on
- **Validation point**: If SET_POWER_ON response is delayed/lost, device remains in non-functional state

### HostInitiatedDozeExit — STUB (CRITICAL)

The Windows `HostInitiatedDozeExit()` function always returns `SUCCESS` without performing any operation:
- **Impact**: Host cannot actively wake device from doze state
- **Validation point**: Doze exit relies entirely on device-initiated wake (touch interrupt)

### Queue Write Handler Bug

The Windows HIDSPI driver has a constant expression bug in the queue write handler:
- `SET_POWER` check condition always evaluates to `true`
- **Impact**: May incorrectly classify non-SET_POWER writes, though functional impact appears minimal

## Windows HidSpiCx D0Exit Quiesce Behavior

On `EvtDeviceD0Exit`, the Windows HIDSPI driver performs quiesce in a specific gated sequence:
1. **Wait for HidSpiCx output completion** — pending output reports must be drained by the class extension before proceeding
2. **Send SET_POWER OFF** via the HidSpiCx output-report path (gated on step 1)
3. **Confirm TIC quiesce** — verify touch IC has acknowledged power-off
4. **THC HW quiesce** — clear RXDMA2 START, release PRD allocations, disable interrupts
5. **Place THC into D3**

> **Optimization**: When touch is already disabled (lid closed / monitor-off), the driver may skip steps 1-3 (TIC quiesce + TX DMA teardown). This is controlled by the INF/registry key `EnhancedPowerManagementUseMonitor`.

## WoT (Wake-on-Touch) — Windows HIDSPI

- `armForWake` flag received from HidSpiCx `EvtNotifyPowerDown` callback
- TIC state set to `ARM_FOR_WAKE = 5` during power-down
- `TSEQ_CNTRL_1.EWOG` bit (Enable Write on GPIO) set for wake detection
- **Validation point**: Verify WoT interrupt routing through UGD domain during D3

## Windows No Freeze/Thaw/Poweroff/Restore Callbacks

The Windows HIDSPI driver does **NOT** implement hibernate freeze/thaw/poweroff/restore callbacks:
- No equivalent to Linux `quickspi_freeze` / `quickspi_restore` / `quickspi_poweroff`
- Windows relies on standard WDF D0Exit/D0Entry for all power transitions
- **Validation point**: Hibernate S4 behavior on Windows uses standard D0Exit→D0Entry path, not specialized freeze/restore

## Filter Driver Stub (IPTS Compatibility)

Windows HIDSPI includes an IPTS filter driver interface:
- **GUID**: `{A2BCAC85-68F6-41B2-B112-DE4EA74770C6}` (GUID_THC_INTERFACE)
- All 9 sensor functions are **STUBS** (return empty/zero):
  1. GetSensorInfo
  2. GetSensorCapabilities
  3. GetSensorMode
  4. SetSensorMode
  5. GetSensorState
  6. SetSensorState
  7. GetSensorData
  8. SetSensorData
  9. GetSensorDescriptor
- **Impact**: IPTS/GPU-direct touch path not functional in Windows HIDSPI driver
