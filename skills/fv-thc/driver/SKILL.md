---
name: fv-thc/driver
description: THC driver source analysis (Windows HIDI2C, Windows HIDSPI, Linux kernel), HSDES workarounds, IPTS filter, special report IDs
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Driver Source Code Analysis

Platform-specific driver details: see [linux.md](linux.md) and [windows.md](windows.md)

Cross-driver analysis of three THC driver codebases correlated to THC IP HAS register definitions and protocol specifications.

## Driver Codebases

| Codebase | Location | Protocol | Version |
|----------|----------|----------|---------|
| **Linux kernel THC** | `github.com/torvalds/linux/tree/master/drivers/hid/intel-thc-hid` (audited against v6.17–v6.20; content may differ in newer versions) | Both | 6.17–6.20+ |
| **Windows HIDSPI** | `intel-innersource/drivers.platform.ipts.hspi-driver` | HIDSPI | v4.0.0.9000 |
| **Windows HIDI2C** | `intel-innersource/drivers.platform.ipts.hid-i2c-touch` | HIDI2C | v3.0.0.9000 |

> **Phase 6 audit**: Both Windows drivers fully read line-by-line (78 files, ~1.3MB). Findings integrated into all skill files.

## Cross-Driver Architecture Comparison

### QuickSPI vs QuickI2C Driver Architecture (HIDSCx vs Monolithic)

The architectural foundation diverges significantly between the two protocols on Windows:

*   **QuickSPI (HIDSPI):** Leverages a modern Windows class extension framework (`HIDSCx`). The driver acts as a client to `HIDSCx`, mapping requests across parallel/sequential WDF queues. It relies heavily on `HIDSCx` to dictate protocol state management, ping-pong IRP management for input reports, and error validation (e.g., short packet errors).
*   **QuickI2C (HIDI2C):** Operates as a more traditional **monolithic HID miniport driver** interacting directly with the OS `HIDClass` driver. Because there is no equivalent class extension for I2C, the `QuickI2C` driver assumes the full burden of maintaining protocol flow, validating report lengths, and managing request states itself.



| Aspect | Windows HIDI2C | Windows HIDSPI | Linux THC |
|--------|---------------|----------------|-----------|
| Framework | WDF/KMDF | WDF/KMDF + HidSpiCx | Linux PCI + regmap |
| Interrupt model | ISR+DPC, GBL_INT_EN toggle | ISR+DPC, no GBL_INT_EN in ISR | Hardirq + threaded IRQ |
| DMA channels | RXDMA1/2 + TXDMA + SWDMA | RXDMA1/2 + TXDMA (no SWDMA) | RXDMA1/2 + TXDMA + SWDMA(I2C) |
| GET_FEATURE | SWDMA | TX DMA + PendingQueue + timer | SWDMA (I2C) / protocol msg (SPI) |
| Device descriptor | 30 bytes (HID-I2C spec) | 24 bytes (HIDSPI spec) | 30B (I2C) / 24B (SPI) |
| Power states | D0/D3/D3Final + LTR/D0i2 | D0/armForWake + LTR/Doze | Runtime PM + LTR |
| Bus lock | SpinLock | NO-OP (BSOD WA) | N/A |

## Driver Discovery & PCI Enumeration

THC is a PCI device — both Linux and Windows discover it via standard PCI enumeration during boot.

### PCI Matching Flow
```
BIOS configures BAR0 (32KB MMIO) + enables PCI device
  → OS PCI bus scan finds THC (Vendor=0x8086, Device=platform-specific)
    → Driver matching by PCI Device ID table
      → probe() / EvtDeviceAdd() called
        → BAR0 mapped → protocol detection (SPI/I2C) → init
```

### PCI Device ID Tables

Each THC port has two Device IDs, selected by BIOS fuse/softstrap (PORT_TYPE config register).
The **QuickSPI SwAS Table 5** and **QuickI2C SwAS Table 4** are the authoritative DID mapping
references. The SwAS explicitly documents the DID-to-protocol mapping convention:

- **MTL/ARL era**: Lower (even) DID = IPTS INF, Higher (odd) DID = QuickSPI INF
- **LNL+ era**: Lower (even) DID = QuickI2C INF, Higher (odd) DID = QuickSPI INF

| Platform | Port0 SPI (odd) | Port0 I2C/IPTS (even) | Port1 SPI (odd) | Port1 I2C/IPTS (even) | Source |
|----------|----------------|----------------------|----------------|----------------------|--------|
| MTL-S | `0x7F59` | `0x7F58` (IPTS) | `0x7F5B` | `0x7F5A` (IPTS) | **SwAS** Table 5/4 |
| MTL-P/M | `0x7E49` | `0x7E48` (IPTS) | `0x7E4B` | `0x7E4A` (IPTS) | **SwAS** Table 5/4 |
| ARL-H | `0x7749` | N/A | `0x774B` | N/A | Kernel v6.19 (SPI only) |
| LNL-M | `0xA849` | `0xA848` (I2C) | `0xA84B` | `0xA84A` (I2C) | **SwAS** Table 5/4 |
| PTL-H (PTL-H4Xe, PCD-H) | `0xE349` | `0xE348` (I2C) | `0xE34B` | `0xE34A` (I2C) | **SwAS** Table 5/4 |
| PTL-U & PTL-P (PTL-H12Xe, PCD-P) | `0xE449` | `0xE448` (I2C) | `0xE44B` | `0xE44A` (I2C) | **SwAS** Table 5/4 |
| WCL | `0x4D49` | `0x4D48` (I2C) | `0x4D4B` | `0x4D4A` (I2C) | **SwAS** Table 4 |
| NVL | `0xD349` | `0xD348` (I2C) | `0xD34B` | `0xD34A` (I2C) | **Co-De Sign** (novalake PCD) |
| RZL | `0x6C49` | `0x6C48` (I2C) | `0x6C4B` | `0x6C4A` (I2C) | **Co-De Sign** (razorlake PCD) |
| TTL | `0x9335` | `0x9334` (I2C) | `0x933A` | `0x9339` (I2C) | **Co-De Sign** (titanlake PCD) |

> **Notes:**
> - DID pattern for most platforms: even = I2C/IPTS, odd = SPI. THC0 = x8/x9, THC1 = xA/xB
> - **TTL breaks this pattern**: THC0 = 9334/9335, THC1 = 9339/933A (non-contiguous)
> - MTL/ARL are Gen3.0 (HIDSPI only) — even DIDs map to legacy IPTS INF, not QuickI2C
> - ARL-H: Only SPI DIDs confirmed (kernel v6.19). Even DIDs not verified — no SwAS or PCD data
> - ARL-U DIDs (`0x7F49`/`0x7F4B`) appear in some references but are **UNVERIFIED**
> - **See `fv-thc/platform`** for full per-platform details including BDFs, BOM configs, and signal lists

### Driver Matching Behavior
- **Linux**: `pci_device_id` table in `pci-quickspi.c` (SPI) and `pci-quicki2c.c` (I2C). One device ID can match only one driver — the BIOS PORT_TYPE soft strap determines which driver loads.
- **Windows**: INF file `[DeviceInstall]` section maps Device IDs → driver. HIDSPI and HIDI2C are separate driver packages with non-overlapping ID lists.
- **Key rule**: THC1 requires THC0 enabled — THC1 is PCI Function 1; THC0 (Function 0) must be active for THC1 to enumerate.

## Register Access Patterns

### Windows — MMIO Struct Overlay
```c
CommonRegisters = Bar0;                    // Config space at BAR0 base
Port0Registers  = Bar0 + 0x1000;          // Port registers
Port0Registers->THC_M_PRT_CONTROL.Port_Type  // Read port type
```

### Linux — Regmap Framework
```c
regmap_read(dev->thc_regmap, THC_M_PRT_CONTROL_OFFSET, &val);
regmap_write_bits(dev->thc_regmap, offset, mask, val);
// Ranges: 0x10–0x14, 0x1000–0x1320
```

## Interrupt Handling

> ⚠️ D1: GBL_INT_EN sequence divergence — the Windows driver enables and toggles GBL_INT_EN earlier in startup/teardown than the SwAS reference implementation, which changes the interrupt enable sequencing observed on hardware.

> ⚠️ D3: FATAL_ERR_INT_EN width difference — the driver treats FATAL_ERR_INT_EN as a single-bit mask in several operations while the SwAS model exposes a wider field; this difference affects how fatal error conditions are masked and observed.

### Interrupt Quiescing RTL Bug (Pre-LNL)

Prior to Lunar Lake (LNL), there is a race condition where the THC handles interrupt edge transitions twice if the TIC firmware is slow to de-assert the line before un-quiescing. The driver uses a 300µs/700µs delay workaround (HSDES 16023244313) to mitigate this "Interrupt Quiescing RTL Bug" by allowing the TIC time to stabilize before the THC re-samples the edge transition.

## Reset Response Timeout — Spec vs Implementation

| Context | SPI Timeout | I2C Timeout | Source |
|---------|------------|------------|--------|
| **QuickSPI SwAS v1.0** | **1 second** | N/A | SwAS spec (authoritative for SPI) |
| **QuickI2C SwAS v1.0** | N/A | **5 seconds** | SwAS spec (authoritative for I2C) |
| **Linux kernel** (both drivers) | **5 seconds** | **5 seconds** | Implementation choice — uses I2C timeout for both protocols |
| **Windows HIDSPI** | ~1 second | N/A | Follows SwAS SPI spec |
| **Windows HIDI2C** | N/A | ~5 seconds | Follows SwAS I2C spec |

> **Key insight**: The Linux kernel uses 5 seconds for SPI reset timeout (`THC_RESET_TIMEOUT_MS = 5000`), which exceeds the SwAS-specified 1 second for SPI. This provides extra margin but differs from spec. Windows drivers follow their respective SwAS specs more closely. When writing validation tests, use the **spec** timeout (1s SPI, 5s I2C) as the expected value, and flag kernel's 5s SPI timeout as an implementation deviation — not a bug, but worth noting.

> **I2C reset-response handling rule**: During QuickI2C reset, ignore/discard any non-reset input reports until the reset sentinel (`0x0000` length) is received. Only treat the reset as complete after sentinel detection; pre-sentinel traffic should not be dispatched to normal HID report paths.

### Windows Driver Key Constants (from Audit Report)

| Constant | HIDSPI Value | HIDI2C Value | Notes |
|----------|-------------|-------------|-------|
| `DEFAULT_MAX_PACKET_SIZE` | 128 (×16 = 2048 bytes) | 256 (×16 = 4096 bytes) | Protocol-specific DMA buffer sizing |
| `DEFAULT_RESET_MS_TIMEOUT` | 1,000 ms | 5,000 ms | Reset completion wait; Linux kernel uses 5s for SPI (deviation) |

> ⚠️ D7: DEFAULT_MAX_PACKET_SIZE differs between SPI and I2C — SPI uses 128 units (2KB effective), I2C uses 256 units (4KB effective). DMA PRD sizing and buffer allocation tests must use protocol-specific defaults.

## Device State Machines

### Probe-Time State Transitions

**QuickSPI probe path** (see [linux.md](linux.md) for full state enum):
```
QUICKSPI_DISABLED → QUICKSPI_INITIATED (quickspi_dev_init) → QUICKSPI_RESETING (reset_tic) → QUICKSPI_RESET (reset_tic complete) → QUICKSPI_ENABLED (probe)
```

**QuickI2C probe path** (see [linux.md](linux.md) for full state enum):
```
QUICKI2C_DISABLED → QUICKI2C_INITED (quicki2c_dev_init) → QUICKI2C_RESETING (reset) → QUICKI2C_RESETED (handle_input) → QUICKI2C_ENABLED (probe)
```

**Windows DeviceState** (see [windows.md](windows.md) for full state enum):
```
HWUninitialized (0) → HWUninitializing (1) → HWInitializing (2) → HWInitialized (3) → DMAAllocating (4) → TouchEnabled (5) → Active (6)
```

### Full Quiesce Ordering (Driver Teardown)

> **SwAS Requirement**: During device teardown (remove/D0Exit), the driver MUST perform a two-step quiesce in strict order:
> 1. **TIC quiesce first** — drain all pending host-side output reports and confirm the touch IC has acknowledged/completed them
> 2. **THC quiesce second** — only after TIC quiesce is confirmed, assert THC device interrupt quiesce (`thc_interrupt_quiesce`) and wait for HW quiesce status
>
> This ordering prevents stale TIC-generated interrupts from being processed by THC during host-side DMA/MMIO teardown. Reversing the order (THC first) risks processing stale interrupts after DMA buffers are freed.

## Driver Init Lifecycle (Shared Steps)

Both Linux and Windows drivers follow a common initialization sequence after PCI enumeration, regardless of protocol (SPI/I2C). The specifics differ (see `linux.md` / `windows.md`), but the shared high-level flow is:

```
1. Map BAR0 (32KB MMIO)
2. Read PORT_TYPE to determine protocol (SPI=0x00, I2C=0x01)
3. Read ACPI DSM properties (clock, speed, IO mode, device address)
4. Allocate DMA buffers (PRD rings for RXDMA1, RXDMA2, TXDMA, and optionally SWDMA)
5. Configure DMA channels (PRD base address, control bits, callback size)
6. Configure protocol-specific registers:
   - SPI: SPI_CFG (clock divider, IO mode, opcode tables)
   - I2C: I2C sub-IP registers (IC_CON, IC_TAR, HCNT/LCNT, thresholds)
7. Set interrupt configuration (DEVINT_CFG_1/2, GBL_INT_EN, per-channel IE bits)
8. Issue device RESET:
   - SPI: Assert ACPI _RST method (with 'TSR_' signature)
   - I2C: Send HIDI2C protocol RESET command (opcode 0x01) via PIO, or GPIO DEVRST (Windows)
9. Wait for reset response (1s SPI per SwAS, 5s I2C per SwAS; Linux kernel uses 5s for both)
10. Read device descriptor (24B SPI, 30B I2C) via PIO/DMA
11. Read report descriptor (variable length, via DMA)
12. Register with HID subsystem (hid_add_device on Linux, HidSpiCx/HIDClass on Windows)
13. Enable touch input (start RXDMA, enable interrupts, enter active state)
```

> **Source**: Derived from Linux kernel probe sequences (v6.17-6.20) and Windows EvtDeviceD0Entry flows, cross-checked against QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0.

### Init Failure Handling

| Failure Point | Linux Behavior | Windows Behavior |
|--------------|----------------|-----------------|
| BAR0 map failure | Return `-ENOMEM`, PCI cleanup | `STATUS_INSUFFICIENT_RESOURCES`, device not started |
| ACPI DSM missing | Use defaults or fail | Use defaults or fail |
| DMA allocation failure | Goto cleanup label, free partial allocs | `STATUS_INSUFFICIENT_RESOURCES` |
| Reset timeout | Error log, return failure | Retry up to 4× (HIDI2C) or fail (HIDSPI) |
| Descriptor parse error | `hid_destroy_device()`, cleanup | Device enters error state |

## HID Descriptor Retrieval & Registration

Both protocols fetch device information through a multi-step descriptor chain:

```
Device Descriptor → Report Descriptor → HID Registration
```

### Device Descriptor

| Field | HIDSPI (24 bytes) | HIDI2C (30 bytes) |
|-------|------------------|------------------|
| Descriptor length | 2 bytes | 2 bytes |
| BCD version | HID-SPI spec version | HID-I2C spec version |
| Report descriptor length | 2 bytes | 2 bytes |
| Report descriptor offset | N/A (follows device desc) | 2 bytes (register address) |
| Vendor ID | 2 bytes | 2 bytes |
| Product ID | 2 bytes | 2 bytes |
| Version ID | 2 bytes | 2 bytes |
| Max input length | 2 bytes | 2 bytes |
| Max output length | 2 bytes | 2 bytes |
| Max feature length | N/A | 2 bytes |

### Report Descriptor

- Variable-length HID report descriptor (typically 200-2000 bytes for touch devices)
- **SPI**: Retrieved via HIDSPI `GET_REPORT_DESCRIPTOR` input report body (bulk read after device descriptor)
- **I2C**: Retrieved via I2C register read at the offset specified in the device descriptor
- Both platforms parse the report descriptor to determine: max contact count, report sizes, feature report capabilities, and vendor-specific collections

### HID Registration

- **Linux**: `hid_allocate_device()` → populate `hid_device` fields (vendor, product, bus=`BUS_PCI`) → `hid_add_device()` → kernel HID subsystem takes over
- **Windows HIDSPI**: `HidSpiCxDeviceInitialize()` → report descriptor passed to HIDSCx class extension → HIDClass.sys takes over
- **Windows HIDI2C**: Direct HIDClass miniport registration → HID report descriptor provided via `IOCTL_HID_GET_REPORT_DESCRIPTOR`

## Touch IC Register Map (Device-Side)

### EDS Gen2 TIC Register Map (HIDSPI v1.0 — Windows & Linux)

Used by both Windows HIDSPI/HIDI2C drivers and Linux QuickSPI/QuickI2C:

| Offset | Register | Key Value |
|--------|----------|-----------|
| `0x00` | `INT_CAUSE` | Interrupt cause from device (ICR header) |
| `0x04` | `ERR` | Device error status |
| `0x08` | `DATA_SZ` | Data size indicator |
| `0x0C` | `CFG` | Device configuration |
| `0x10` | `STATE` | Device state (TIC power state enum) |
| `0x14` | `ID` | `0x43495424` (`"$TIC"` — magic identifier) |
| `0x18` | `CAPABILITIES` | Device capabilities |
| `0x1C` | `IC_HW_ID` | IC hardware identifier |
| `0x20` | `IC_HW_REV` | IC hardware revision |
| `0x24` | `IC_FW_REV` | IC firmware revision |
| `0x28` | `COMMAND` | Command register |
| `0x2C` | `INIT` | Initialization register |
| `0x34` | `COMPAT_ID` | Compatibility ID |
| `0x1000` | `BULK_WINDOW` | Bulk data window (read/write area) |

### IPTS/Gen1 TIC Register Map (Legacy — CSME/GPU path)

Used by older IPTS (Intel Precise Touch & Stylus) mode via CSME/GPU:

| Offset | Register | Key Value |
|--------|----------|-----------|
| `0x00` | `TOUCH_STS_REG` | `SyncByte=0x5A`, `IntType`(4b), `PwrState`(2b) |
| `0x04` | `TOUCH_FRAME_CHAR_REG` | MicroFrameSize, HidReport flag |
| `0x10` | `TOUCH_ID_REG` | `0x43495424` (`"$TIC"`) |
| `0x14` | `TOUCH_DATA_SZ_REG` | MaxFrameSize (×64B), MaxFeedbackSize |
| `0x18` | `TOUCH_CAPS_REG` | Freq bits, IO mode, MaxTouchPoints |
| `0x1C` | `TOUCH_CFG_REG` | `TouchEnable`, `Dhpm` (0=Raw, 1=HID) |
| `0x20` | `TOUCH_CMD_REG` | NOP=0, SOFT_RESET=1, PREP_4_READ=2, GEN_TEST_PACKETS=3 |

**Constants**: `TOUCH_DATA_WINDOW_START=0x1000`, `TOUCH_SENSOR_MAX_FRAME_SIZE=32KB`

### TIC Power State Enum (EDS Gen2 — from Windows Drivers)

| Value | State | Description |
|-------|-------|-------------|
| 0 | `NO_OP` | No operation |
| 1 | `DOZE` | Reduced power, limited scanning |
| 2 | `ARMED` | Ready, awaiting touch |
| 3 | `SENSING` | Active touch scanning |
| 4 | `SOFT_RESET` | Device is resetting |
| 5 | `ARM_FOR_WAKE` | Armed for wake-on-touch |
| 6 | `ACTIVE_LTR_STATE` | Active LTR power state |
| 7 | `LOWPOWER_LTR_STATE` | Low-power LTR state |

> **Source**: Windows HIDI2C driver (`hi2cHal.h`, `TIC_POWER_STATE` enum). The STATE register at offset `0x10` holds the current TIC power state value.

## Special HID Report IDs

| Report ID | Name | Protocol | Purpose |
|-----------|------|----------|---------|
| 0x40 | SINGLE_TOUCH | Both | Single-finger touch |
| 0x47 | HEARTBEAT | I2C only | Keep-alive feature report |
| 0x5A | DEBUG_FEATURE | Both | Driver state, error recovery trigger |
| 0x5B | DEBUG_DATA | Both | Debug data output |
| 0x5C | TELEMETRY | Both | Reset counts, error stats (version=3) |
| 0x5D | PASSTHROUGH | I2C only | SmartFilter passthrough |

## HSDES Workaround References

| HSDES | Category | Description |
|-------|----------|-------------|
| 14016760177 | Interrupt | WriteDMA interrupt handling disabled — serialize ISR/DPC |
| 14021506058 | Protocol | Report ID encoding: `< 15` not `<= 15` for sentinel |
| 15014216160 | Register | Display sync write ordering — 2μs stall |
| 15014216513 | Clock | Kick THC internal CLK: write TPCPR=1 |
| 16015806448 | DMA | Don't dealloc DMA before alloc during reset |
| 16018918669 | Reset | Only enable interrupts if reset succeeded |
| 16020586422 | Power | TxQueue start → D0EntryPostInterruptsEnabled |
| 16021402362 | DMA | Force write pointer update during reset wait |
| 16021846070 | Flash | Temp edge-triggered interrupts during FW flash |
| 16023244313 | Quiesce | Quiesce fails during continuous touch — delay WA |
| 16023606602 | Power | Skip DPC if device not in D0 |
| 16023750028 | DMA | STALL: ACTIVE==0 && TPCRP==TPCWP → DmaReconfigure |
| 16024259234 | DMA | Null check for CommonPrdBuffer before access |
| 16024309461 | DMA | INVLD_DEV_ENTRY BSOD during FW flash — edge-triggered INT WA |
| 16023561690 | Power | S5 resume BSOD — WdfInterruptAcquireLock when not D0 |
| 16023816174 | I2C | HIDI2C Hal workaround (referenced in Hal.cpp) |
| 16024143384 | DMA | HIDI2C DMA workaround (referenced in Hal.cpp + Dma.cpp) |
| 16024146412 | DMA | HIDI2C DMA workaround (referenced in Hal.cpp + Dma.cpp) |
| 16024165031 | DMA | STALL detection — ACTIVE==0 && TPCRP==TPCWP triggers DMA reconfigure |
| 16024189402 | DMA | HIDI2C DMA workaround (referenced in Hal.cpp + Dma.cpp) |
| 22016570720 | Queue | HIDSPI race condition — Yellow Bang Code 43 on device removal |
| 16024070256 | DMA | HIDI2C DMA workaround (referenced in Dma.cpp) |
| 15016076869 | DMA | HIDI2C DMA workaround (referenced in Dma.cpp) |
| 16019682677 | DMA | HIDI2C DMA workaround (referenced in Dma.cpp) |

## Error Recovery Comparison

| Aspect | Linux QuickSPI | Linux QuickI2C | Windows HIDSPI | Windows HIDI2C |
|--------|---------------|----------------|----------------|----------------|
| **Recovery trigger** | `dma_error_handler()` or `error_recover()` | `dma_error_handler()` | DPC error checks | DPC error checks (6 error types) |
| **Reset involved?** | **Yes** — full `reset_tic()` + DMA reconfigure | **No** — DMA reconfigure only (no device reset) | **Yes** — full reset flow | **Yes** — DmaReconfigure or full reset |
| **DMA handling** | Stop all DMA → reset → reinit | Stop DMA → reconfigure → restart | Quiesce + reconfigure | Quiesce + reconfigure |
| **STALL detection** | ACTIVE==0 check | ACTIVE==0 && TPCRP==TPCWP | Same as Linux | ACTIVE==0 && TPCRP==TPCWP → DmaReconfigure |
| **TXN_ERR** | Logged, DMA reset | Logged, DMA reconfigure | INVLD_DEV_ENTRY → quiesce+reconfigure | INVLD_DEV_ENTRY → quiesce+reconfigure |
| **NVLD_DEV_ENTRY mitigation** | — | Configure `I2C_Max_Frame_Size` registry key to cap input size | — | Same as QuickI2C — caps frame size to avoid oversized read delays |
| **SCL_STUCK** | N/A (SPI) | Not handled explicitly | N/A (SPI) | Recovery sequence in DPC |
| **FATAL_ERR** | DMA reset | DMA reconfigure | Reset flow | Recovery in DPC |
| **Max retries** | 1 (re-init) | 1 (reconfigure) | No retry loop (EvtResetDevice in HidSpiCx has no retry) | 4 (ProcessResetFlow retries) |

> **Key insight**: QuickI2C error recovery is intentionally lightweight — no device reset, just DMA reconfiguration. This differs significantly from QuickSPI which always does a full `reset_tic()`.

## Error Recovery Flows

Common error recovery flows across drivers:
- DMA timeout recovery: stop DMA → reset PRD ring → re-init DMA → restart. Linux uses `thc_dma_unconfigure()` + `thc_dma_init()` + `thc_dma_configure()` to perform a full DMA reset; Windows uses `HalDMA::Reset()` which internally pauses/reconfigures and restarts DMA.
- Device unresponsive: issue device RESET command (via ACPI `_RST` for SPI or PIO I2C reset), wait for response, re-parse descriptors and re-enumerate HID if necessary.
- Bus error (SPI/I2C): log error → increment counter → retry up to N times → escalate to DMA reset or device reset if retries fail.

Linux example sequence for DMA recovery: `thc_dma_unconfigure()` → `thc_dma_init()` → `thc_dma_configure()` → re-enable interrupts → resume HID processing.

## Output Report Handling and Runtime PM (Both Platforms)

Important correction for both driver platforms:
- Linux `quickspi_hid_raw_request()` and `quicki2c_hid_raw_request()` DO call `pm_runtime_resume_and_get()` / `pm_runtime_put_autosuspend()` when processing HID requests. These functions ensure the device is in an active power state before performing PIO/MMIO operations and release the PM reference after completion.
- However, the `output_report` callback path still lacks explicit PM handling on Linux — output reports sent via the HID output_report callback do not include pm_runtime_get/put pairs, which is a potential gap.
- Windows behavior differs: output report send may go through WDF/HidSpiCx queues which have implicit power state handling (WDF will ensure D0 entry for queued I/O in many cases).

## Windows vs Linux Key Behavioral Differences

| Aspect | Windows | Linux | Impact |
|--------|---------|-------|--------|
| SPI base clock | **125 MHz** (HIDSPI driver) | 125 MHz (kernel) | Consistent — all canonical sources use 125 MHz |
| I2C FS_HCNT/LCNT | `0x1F4`/`0x24C` (500/588) | `0x92`/`0x9C` (146/156) | **Major difference** — different I2C timing, affects bus speed |
| I2C init steps | 13 steps (adds PORT_TYPE, RX_FIFO_FULL_HLD, STOP_DET_IF_MASTER, conditional IC_SDA_HOLD) | 11 steps | Windows adds extra safety registers (see `fv-thc/hidi2c` 13-step table) |
| GBL_INT_EN in ISR | HIDI2C: toggled in ISR; HIDSPI: NOT toggled | Not toggled (hardirq) | Different interrupt masking strategies |
| GET_FEATURE | HIDI2C: SWDMA; HIDSPI: TX DMA + PendingQueue + 3s timer | SWDMA (I2C) / protocol msg (SPI) | Windows HIDSPI uses different mechanism |
| SpiBusLock | **NO-OP** (BSOD workaround) | N/A | No SPI bus synchronization in Windows |
| Device reset | ACPI `_RST` method | ACPI `_RST` (SPI) / GPIO toggle (I2C) | Same for SPI; I2C differs |
| D3Cold | **Disabled** (D3ColdEnabledInSystem=false) | Supported (I2C: 15-reg save/restore) | Windows avoids D3Cold entirely |
| Write interrupt | **Polling** (100µs interval, 500ms timeout) — HSD 14016760177 | DMA completion interrupt | Windows works around interrupt unreliability |
| Quiesce timing | 300µs before + 700µs after (HSD 16023244313) | No explicit delay | Windows adds safety delays |

## BIOS Programming Requirements (from HAS)

### External BIOS Guide
Full BIOS programming details are in `Chap69_BIOS_WG_THC.docx` (Intel internal).

### Key BIOS Responsibilities
1. **PCI Enumeration**: Configure BAR0 (32KB MMIO range)
2. **Soft Strap Configuration**: Set PORT_TYPE, clock config, power gate enable
3. **Fuse Loading**: THC_RESERVED_FUSE (8-bit, addr 0x3980)
4. **SAI Policy**: Configure INDEX41 SAI checking for register access control
5. **Lock Bits**: Set BIOS_LOCK_EN before handoff to OS driver
6. **LTR Programming**: Set ACTIVE/LP_LTR_VAL/SCALE via IOSF SB registers
7. **Power Gate Enable**: Configure PowerGateEnable soft strap
8. **Clock Gate Enable**: Configure ClockGateEnable soft strap

### Soft Strap Parameters Set by BIOS
| Soft Strap | Description | Default |
|-----------|-------------|---------|
| PowerGateEnable | Enable D0i2 power gating | Platform-dependent |
| ClockGateEnable | Enable clock gating | Platform-dependent |
| PORT_TYPE | SPI (00) or I2C (01) | 00 (SPI) |
| TSI timing params | TSI-specific timing | N/A for SPI/I2C |
| thc_pi_def[7:0] | PI register value (NVL+) | Platform-dependent |

### NVL+ PI Configuration
Starting with NVL, the PCI Programming Interface (PI) register is configurable via the `thc_pi_def[7:0]` soft strap. This allows:
- Per-port PCI header mode (separate PCI functions per port)
- Shared PCI header mode (single PCI function, multiple ports)

### Lock Bit Sequence
1. BIOS configures all THC registers
2. BIOS sets `BIOS_LOCK_EN` — prevents further BIOS-region modification
3. OS driver loads
4. Driver sets `DRV_LOCK_EN` — prevents modification of driver-configured registers
5. Both locks are sticky until reset

## Fuses and Soft Straps (from HAS)

### Fuse
| Name | Width | Address | Description |
|------|-------|---------|-------------|
| THC_RESERVED_FUSE | 8-bit | 0x3980 | Reserved fuse bits for THC |

### Key Soft Straps
| Soft Strap | Type | Description |
|-----------|------|-------------|
| PowerGateEnable | Boolean | Enable HW power gating |
| ClockGateEnable | Boolean | Enable HW clock gating |
| PORT_TYPE | 2-bit | Port protocol: 00=SPI, 01=I2C |
| thc_pi_def[7:0] | 8-bit | PCI PI value (NVL+) |
| thc_pci_or_pciemode | Boolean | PCI vs PCIe endpoint mode (MTL-S+) |
| pin_scr_funcnum[2:0] | 3-bit | PCI Function Number strap |

## Security Architecture (from HAS)

### Threat Model
3 identified threat points:
1. **Sensor PIO** — Malicious data from touch sensor via PIO register access
2. **VTd** — DMA attacks without proper IOMMU protection
3. **GPIO** — Malicious interrupt injection via GPIO pin

### Access Control
- **SAI-based** (Source Agent Identifier) access control for all register spaces
- **BIOS_LOCK_EN**: Prevents BIOS-configured register modification after boot
- **DRV_LOCK_EN**: Prevents driver-configured register modification after init

### Security Properties
- No secrets stored in THC registers
- No peer-to-peer DMA capability (host root space only)
- DMA controlled by Host IA/OS (not autonomous)
- Traffic class hardcoded (cannot be spoofed)
- Outbound SAI immutable
- VTd compliant (SAI on CFG + MMIO)
- No TAP connection
- No microprocessor/firmware — no FW authentication needed
- Filter by `BUS_PCI` in `hidraw`/`evtest`/`hid-recorder`

## HID LL Driver Layer (Linux)
- `bus = BUS_PCI (0x19)` — THC appears as PCI HID, NOT I2C/SPI bus
- Unlike i2c-hid or spi-hid which register on their respective bus types, THC registers HID devices on the PCI bus because the host controller is a PCI endpoint
- This affects userspace tools: `hid-recorder`, `evtest`, and `hidraw` will show THC touch devices with `BUS_PCI` bus type, not `BUS_I2C` or `BUS_SPI`
- The HID low-level driver callbacks (`ll_driver`) are implemented by `quickspi-hid.c` / `quicki2c-hid.c`:
  - `.start` / `.stop` — manage device lifecycle
  - `.open` / `.close` — enable/disable interrupt processing
  - `.parse` — provide cached HID report descriptor to HID core
  - `.raw_request` — route GET_REPORT/SET_REPORT through PIO (SPI) or SWDMA/TXDMA (I2C)
  - `.output_report` — send output reports (⚠️ no pm_runtime_get/put — known gap in both Linux and Windows)

## ACPI DSM Interface

THC drivers use ACPI DSM to fetch platform-specific properties. Characteristics:
- DSM UUID is defined in platform ACPI tables (platform-specific GUID).
- DSM functions used by THC drivers: Get SPI config (clock, IO mode), Get I2C config (speed, address), Get power config (power gating flags), Get workaround flags.
- Linux accessors: `quickspi_acpi_get_properties()` and `quicki2c_acpi_get_properties()` which parse ACPI buffer/integer returns into driver configuration structures.
- Windows accessors: `Acpi.cpp` helpers (`AcpiGetDeviceProperties()`) parse DSM returns (Integer/Buffer) into HAL/driver properties.

## Key HSDES Workarounds (additional / explicit)

Add/verify the following platform/RTL workarounds which must be present in driver code or docs:
- RTL Bug 15014172472: PRD last entry must be 4KB-aligned. Linux driver includes an explicit check and alignment enforcement when programming PRD rings.
- I2C MPS Bug: `SPI_RD_MPS` register must be programmed to `4096` even in I2C mode — ensure driver programs MPS value regardless of port protocol to satisfy sub-IP expectation.
- HSDES 16014286225: Chassis 2.2 compliance — `RES_EN` bits default to `0`. Drivers should not assume `RES_EN=1` and must program them explicitly if required.
- HSDES 15010734105: PTL+ requires 16-bit sideband port ID — ensure sideband port ID writes use correct width for PTL+ platforms.

## Tracing & Debug Infrastructure

Both platforms provide structured tracing for THC driver debug:

### Windows — WPP (Windows Pre-Processor) Tracing
| Property | HIDSPI Driver | HIDI2C Driver |
|----------|--------------|---------------|
| **WPP GUID** | `{A891081A-...}` | `{C47236A7-...}` |
| **Trace header** | `Trace.h` | `Trace.h` |
| **Trace levels** | FATAL, ERROR, WARNING, INFO, VERBOSE | FATAL, ERROR, WARNING, INFO, VERBOSE |
| **Trace flag count** | 12 flags | 13 flags (extra: TRACE_ACPI) |
| **Key trace flags** | ALL_INFO, DRIVER, DEVICE, QUEUE, DMA, HAL, HID, FILTER, FUNCS, UTILS, POWER, SWDMA | ALL_INFO, DRIVER, DEVICE, QUEUE, DMA, HAL, HID, FILTER, FUNCS, UTILS, POWER, SWDMA, ACPI |
| **Collection** | `tracelog -start ThcTrace -guid #<GUID> -f thc.etl -flags 0xFF -level 5` | Same pattern |
| **Decoding** | `tracefmt thc.etl -p <PDB_path> -o thc.txt` | Same pattern |

- Each `.cpp` file includes a `// WPP_INIT_TRACING` annotation and per-function `TraceEvents()` calls
- WPP traces are compiled into driver binary — zero overhead when not collecting
- Use `-flags 0xFF` to capture ALL flag categories; `-level 5` for VERBOSE

### Linux — ftrace / Dynamic Debug
| Mechanism | Usage |
|-----------|-------|
| **dev_dbg/dev_err/dev_warn** | Standard kernel device messages; enable via `dyndbg` |
| **ftrace** | `echo 'intel_thc*' > /sys/kernel/debug/tracing/set_ftrace_filter` |
| **Dynamic debug** | `echo 'module intel_thc_hid +p' > /sys/kernel/debug/dynamic_debug/control` |
| **dmesg filtering** | `dmesg \| grep -i thc` for boot-time and runtime messages |

- Linux THC drivers use `dev_err_once()` for one-shot error reporting (e.g., DMA timeout) *(verify against current kernel version — API usage may change)*
- `CONFIG_DYNAMIC_DEBUG=y` required for `dev_dbg` messages at runtime

### Common Debug Workflow
1. **Reproduce issue** with tracing enabled
2. **Capture traces** (ETL on Windows, dmesg/ftrace on Linux)
3. **Filter** by THC-specific flags/module
4. **Correlate** trace timestamps with interrupt events and DMA completions
5. **Cross-reference** with register dumps (PIO status, DMA status, INT_STS)

## Filter Driver Architecture (Windows)

Windows THC uses a layered driver model. The architecture differs between HIDSPI and HIDI2C:

### HIDSPI Driver Stack (HIDSCx class extension model)
```
┌─────────────────────────┐
│  HID Class Driver       │  (hidclass.sys)
├─────────────────────────┤
│  HIDSCx Class Extension │  (WDF-based, mediates HID class ↔ client)
├─────────────────────────┤
│  QuickSPI Client Driver │  (IntelTHCHidSpi.sys — unified miniport + function)
├─────────────────────────┤
│  IPTS Filter (optional) │  (lower filter — validates via EvtDeviceProcessQueryInterfaceRequest)
├─────────────────────────┤
│  PCI Bus Driver         │  (pci.sys)
└─────────────────────────┘
```
> Source: QuickSPI SwAS v1.0 P0234: "HIDSCx: WDF based class extension library... handles the interactions with hidclass and provides a DDI abstraction layer to the QUICKSPI client driver."

### HIDI2C Driver Stack (traditional HID miniport model)
```
┌─────────────────────────┐
│  HID Class Driver       │  (hidclass.sys — power policy owner)
├─────────────────────────┤
│  QuickI2C Client Driver │  (IntelTHCHidI2c.sys — unified miniport + function)
├─────────────────────────┤
│  SmartFilter (optional) │  (lower filter — header-only interface via SmartFilter.h)
├─────────────────────────┤
│  PCI Bus Driver         │  (pci.sys)
└─────────────────────────┘
```
> Source: QuickI2C SwAS v1.0 P0219: "Hidclass is the power policy owner for the device."

### Filter Implementation
- **HIDSPI**: `Filter.cpp` manages IPTS filter client callbacks; filter validates 4 mandatory callbacks during `EvtDeviceProcessQueryInterfaceRequest` (source: driver/windows.md)
- **HIDI2C**: `SmartFilter.h` (header-only interface); filter functions implemented in `Dma.cpp`/`ThcHid.cpp`
- If filter is absent, reports pass through unmodified (fallback path)
- Filter load controlled by ACPI property (`_DSM` function) and registry override

> **Note**: Specific filter driver binary names and callback function names (e.g., `FilterFrameCallback`) have NOT been verified against source code — verify before using in debug scripts.

> **Linux**: No equivalent filter layer. Raw HID reports are passed directly to the HID subsystem (`hid_input_report()`). Multi-touch processing relies on the generic `hid-multitouch` driver in the kernel.

## Driver Configuration Sources

THC driver behavior is configured from multiple sources, applied in priority order:

### Configuration Hierarchy (highest priority first)
| Priority | Source | Scope | Examples |
|----------|--------|-------|---------|
| **1** | **Registry overrides** (Windows) / **Module params** (Linux) | Per-device or global | `I2C_Max_Frame_Size_Enable`, `SpiIoMode` |
| **2** | **ACPI _DSM returns** | Per-platform | SPI clock, I2C address, IO mode, power flags |
| **3** | **Touch device descriptor** | Per-device | Max input length, report descriptor length, VID/PID |
| **4** | **Driver defaults** (hardcoded) | Universal | Timeout values, DMA ring sizes, LTR defaults |
| **5** | **BIOS soft straps** | Per-platform | PORT_TYPE, PowerGateEnable, ClockGateEnable |

### Key Windows Registry Overrides
| Registry Value | Type | Description |
|---------------|------|-------------|
| `I2C_Max_Frame_Size_Enable` | DWORD (128-255) | Elan legacy panel frame size workaround |
| `SpiIoMode` | DWORD | Force SPI IO mode (0=single, 1=dual, 2=quad) |
| `EnableFWFlashWABOM36` | DWORD | Enable FW flash workaround for BOM36 |
| `DisableD3` | DWORD | Disable D3 power transitions (debug) |
| `DisableLTR` | DWORD | Disable LTR reporting (debug) |
| `ForceD3Cold` | DWORD | Force D3Cold instead of D3Hot |

### Key Linux Module Parameters / ACPI Properties
- ACPI properties parsed in `quickspi_acpi_get_properties()` / `quicki2c_acpi_get_properties()`
- No `module_param()` declarations in current kernel THC drivers — all config via ACPI
- DT (Device Tree) bindings: not supported (Intel x86 only; ACPI-based platforms)

## DMA Buffer Lifecycle

Both platforms follow a similar DMA buffer lifecycle pattern, though with different APIs:

### Allocation & Setup
| Phase | Linux | Windows |
|-------|-------|---------|
| **Buffer alloc** | `dma_alloc_coherent()` (CMA) | `WdfCommonBufferCreate()` (DMA enabler) |
| **PRD table alloc** | `dma_alloc_coherent()` | `WdfCommonBufferCreate()` |
| **Alignment** | 4KB page-aligned (kernel guarantee) | 4KB page-aligned (WDF guarantee) |
| **DMA direction** | `DMA_FROM_DEVICE` / `DMA_TO_DEVICE` | Read / Write transfer type in DMA enabler |
| **IOMMU mapping** | Automatic via DMA API + VT-d | Automatic via HAL DMA adapter + VT-d |

### Runtime Usage
1. **Write PRD entries** — Fill PRD ring with physical addresses + lengths of data buffers
2. **Program THC registers** — Set PRD base address, write-back control (WBC), ring length
3. **Arm DMA** — Set START bit in DMA control register
4. **Wait for completion** — Poll DMACPL_STS or receive MSI interrupt
5. **Read data** — Access buffer content at CPU virtual address (coherent mapping)
6. **Advance pointers** — Update read/write pointers in CB (circular buffer) registers

### Teardown
| Phase | Linux | Windows |
|-------|-------|---------|
| **DMA stop** | Clear START bit, poll ACTIVE=0 | Clear START bit, poll ACTIVE=0 |
| **Buffer free** | `dma_free_coherent()` | `WdfObjectDelete(commonBuffer)` |
| **Error cleanup** | `devm_*` auto-cleanup on probe failure | WDF object hierarchy auto-cleanup |

### Critical Invariant (RTL Bug 15014172472)
> **ALL PRD entries (including the last) MUST be 4KB-aligned.** The HAS states only non-last entries need alignment, but RTL requires all entries aligned. Both Linux and Windows drivers enforce this.

## Validation Points

| # | Check | Expected | Notes |
|---|-------|----------|-------|
| 1 | **Probe completes** without error | Driver bound to PCI device, HID descriptor retrieved | Linux: 14 steps (QuickSPI), Windows: ~16 steps |
| 2 | **Init lifecycle** reaches active state | Linux: STARTED state, Windows: DeviceActive state | Verify state machine transitions in order |
| 3 | **HID descriptor** retrieved correctly | Valid report descriptor size > 0, correct VID/PID | Both OSes use PIO read after device reset |
| 4 | **Error recovery** functions | Driver recovers from bus errors without crash/hang | Test: inject timeout → verify retry → verify recovery |
| 5 | **PM callbacks** execute correctly | Suspend saves registers, resume restores in correct order | Cross-reference Appendix A restore grouping in `fv-thc/registers` |
| 6 | **Output report delivery** works | SET_OUTPUT/SET_FEATURE reach device | ⚠️ Both OSes missing pm_runtime_get/put — known gap |
| 7 | **Cross-platform behavior** matches | DMA timeouts, LTR config, SET_POWER handling consistent with OS expectations | Linux fire-and-forget vs Windows synchronous SET_POWER |

## See Also
- **[linux.md](linux.md)** — Linux kernel driver: state machines, probe sequences, suspend/resume, runtime PM
- **[windows.md](windows.md)** — Windows driver: DeviceState enum, D0Entry/D0Exit, reset flows, registry keys, HID layer
- **`fv-thc/registers`** — Register access patterns, MMIO overlay vs regmap
- **`fv-thc/hidspi`** — HIDSPI protocol for driver implementation context
- **`fv-thc/hidi2c`** — HIDI2C protocol for driver implementation context
- **`fv-thc/power`** — Driver PM callbacks, D3 save/restore register list, idle notification power flow
- **`fv-thc/platform`** — Per-platform Device IDs, BOM configs, registry overrides
- **`fv-thc/debug`** — Driver-related failure signatures, HSDES workarounds
- **`fv-thc/dma`** — DMA channel architecture, RXDMA/TXDMA/SWDMA for driver DMA handling
- **`fv-thc/wot`** — WoT driver implementation: Linux thc_interrupt_handler wake path, Windows WoT arm/disarm
- **`fv-thc/simics`** — Simics driver install/workarounds, DID patching for pre-silicon, touch device model interaction
- **Reference**: `fv-thc/docs/thc_known_issues.md` — All known RTL bugs requiring driver workarounds
