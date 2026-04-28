# THC Windows Driver Diff Report: HIDSPI vs HIDI2C

> **Owner**: Chin, William Willy (`willychi`)
>
> **Generated**: 2026-03-05
>
> **HIDSPI source**: `drivers.platform.ipts.hspi-driver\THCBase\IntelTHCBase\` (36 files)
>
> **HIDI2C source**: `drivers.platform.ipts.hid-i2c-touch\THCBase\IntelTHCBase\` (38 files)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

---

## Executive Summary

| Category | Count | Description |
|----------|------:|-------------|
| **IDENTICAL** | 1 | Byte-identical across both drivers |
| **SIMILAR - Trivial** | 8 | Differences limited to copyright years, confidential headers, include paths |
| **SIMILAR - Significant** | 17 | Functional differences reflecting protocol/architecture divergence |
| **UNIQUE to SPI** | 9 | Files only in the HIDSPI driver |
| **UNIQUE to I2C** | 10 | Files only in the HIDI2C driver |
| **Total distinct files** | 45 | Union of both drivers |

### Key Architectural Differences

1. **HID Framework**: SPI uses Microsoft's HidSpiCx class extension; I2C uses direct HID miniport (no class extension)
2. **Bus Protocol**: SPI has SPI-specific opcodes, frequency selection, IO modes; I2C has full DesignWare I2C controller programming
3. **Proprietary Mode**: SPI has full IPTS filter driver interface for GPU/EU kernel proprietary data path; I2C does not
4. **Smart Filter**: I2C has VSYNC-based smart filtering for display sync; SPI does not
5. **SW DMA**: I2C has an additional software-triggered DMA channel (SWDMA); SPI does not
6. **Power Management**: I2C has explicit I2C SET_POWER commands and sleep state management; SPI uses HidSpiCx power callbacks
7. **Driver Version**: SPI is version 4.x (newer), I2C is version 3.x

---

## 1. IDENTICAL Files

| File | Size | Notes |
|------|-----:|-------|
| `resource.h` | 406 B | Standard resource ID definitions; byte-identical |

---

## 2. SIMILAR Files - Trivial Differences

These files share identical functional content. Differences are limited to copyright year stamps, Intel confidential header blocks, and `#include` path variations (`"stdint.h"` vs `<INC/stdint.h>`).

| File | SPI Lines | I2C Lines | Difference Summary |
|------|----------:|----------:|-------------------|
| `HidDefs.h` | ~same | ~same | Copyright year only (2023 vs 2016) |
| `Ver.h` | ~same | ~same | Copyright year + `VER_MAJOR` 4 (SPI) vs 3 (I2C) |
| `eds.h` | ~same | ~same | SPI has Intel confidential header; `"stdint.h"` vs `<INC/stdint.h>` |
| `TelemetryReport.h` | ~same | ~same | SPI has Intel confidential header block |
| `Public.h` | ~same | ~same | SPI has Intel confidential header block |
| `Queue.h` | ~same | ~same | SPI has Intel confidential header; functionally identical |
| `Utils.h` | ~same | ~same | SPI has Intel confidential header + one extra function (see below) |
| `DebugToolMsgs.h` | ~same | ~same | SPI has 8 extra lines for additional debug tool message IDs |

### Notable Detail: `Utils.h`

SPI declares one additional function not present in I2C:
```c
NTSTATUS THCBaseWriteRegistryDWordKey(...);
```
This is a minor utility addition and does not represent a significant architectural divergence.

---

## 3. SIMILAR Files - Significant Functional Differences

### 3.1 `Acpi.h` / `Acpi.cpp` - ACPI Interface

| Metric | SPI | I2C |
|--------|----:|----:|
| `Acpi.cpp` lines | 330 | 679 |

**SPI-specific (`Acpi.h`)**:
- Defines `GUID_HIDSPI_DSM` and `GUID_THC_DSM` for HIDSPI Device Specific Method evaluation
- DSM function indices for: read opcode, write opcode, flags, input/output report body/address
- Structures: `HIDSPI_READ_OPCODE_DSM`, `HIDSPI_WRITE_OPCODE_DSM`, `HIDSPI_FLAGS_DSM`, `HIDSPI_BODY_DSM`, `HIDSPI_ADDRESS_DSM`
- Functions: `GetAcpiHidSpiReadOpcode()`, `GetAcpiHidSpiWriteOpcode()`, `GetAcpiHidSpiFlags()`, `GetAcpiHidSpiInputReportBodyAddress()`, `GetAcpiHidSpiOutputReportBodyAddress()`

**I2C-specific (`Acpi.h`)**:
- Defines I2C-specific ACPI Device Specific Data (DSD) and configuration reading
- Functions: `GetAcpiHidI2cDescriptorAddress()`, `ReadHIDI2C_DSD()`, `ReadHIDI2C_CONFIG()`
- Significantly larger implementation (679 lines) due to I2C descriptor address parsing and DSD configuration handling

### 3.2 `Device.h` / `Device.cpp` - Device Context & Lifecycle

| Metric | SPI | I2C |
|--------|----:|----:|
| `Device.cpp` lines | 3,095 | 2,367 |

**SPI-specific**:
- Includes `<hidspicx.h>` (Microsoft HidSpiCx class extension)
- `HIDSPICX_REPORT` structure for SPI report handling
- `FILTER_CONTEXT` for IPTS proprietary mode filter driver
- SPI bus lock mechanisms
- `InitiateResetFlowHidSCx()` and `PostResetDmaSetup()` for HidSpiCx reset flow
- Larger implementation reflects HidSpiCx integration complexity

**I2C-specific**:
- `SWDMA_CONTEXT` for software-triggered DMA
- Smart filter integration via `SmartFilter.h`
- I2C bus lock mechanisms
- `SetPowerLock`, `SendSetPowerRequest()`, `TakeDeviceOutOfSleep()` for I2C power management
- `THCConfigureHAE()` for Host Address Enable configuration
- `RESET_RESPONSE_DATA`, `DUMP_REGISTERS` structures
- `BUS_INTERFACE_STANDARD` for PCI bus interface
- `TxQueueThreadHandle` for TX queue management thread
- Multiple I2C-specific state tracking BOOLEANs
- `SMARTFILTER_DATA_INPUT_REPORT` for display-sync filtered reports

### 3.3 `Dma.h` / `Dma.cpp` - DMA Engine

| Metric | SPI | I2C |
|--------|----:|----:|
| `Dma.cpp` lines | 2,983 | 3,414 |

**Shared**: Both define `DMA_CONFIGURATION` with RXDMA/TXDMA channels, PRD tables, interrupt handling.

**SPI-specific**:
- `TxDMA_Override` flag
- `WriteRequestToTxDma()` with `REPORT_TYPE` parameter for SPI output reports
- `WriteReportDescriptorIoctlToTic()` for TIC (Touch Input Controller) report descriptor requests

**I2C-specific**:
- `DmaReConfigureLock` for dynamic DMA reconfiguration
- `DmaReadSmartFilterHeader()` for smart filter header parsing
- `WriteSetPowerToTxDma()` for I2C SET_POWER command over DMA
- `WriteI2CRequestToTxDma()` and `WriteI2CReportToTxDma()` for I2C-specific TX DMA
- `SmartFilterDriverCompleteReadRequest()` for VSYNC-filtered report completion

### 3.4 `Driver.h` / `Driver.cpp` - Driver Entry & Framework

| Metric | SPI | I2C |
|--------|----:|----:|
| `Driver.cpp` lines | 239 | 180 |

**SPI-specific**:
- Includes `<hidspicx.h>`, `<wdm.h>`, `<TraceLoggingProvider.h>`
- Declares `g_hQSpiProvider` (TraceLogging ETW provider)
- `DriverEntry` integrates HidSpiCx class extension initialization
- Additional HidSpiCx-mandated callback registration

**I2C-specific**:
- Minimal driver framework; standard WDF driver entry
- No class extension integration

### 3.5 `Hal.h` / `Hal.cpp` - Hardware Abstraction Layer

| Metric | SPI | I2C |
|--------|----:|----:|
| `Hal.h` lines | 2,499 | 2,937 |
| `Hal.cpp` lines | 3,935 | 4,265 |

This is the largest divergence area. Both share THC register definitions but diverge heavily on bus-specific registers.

**SPI-specific**:
- SPI opcode registers, frequency configuration, IO mode selection
- SPI-specific performance counter registers
- PIO (Programmed I/O) registers for SPI transactions

**I2C-specific**:
- Full DesignWare I2C Sub-IP register programming (maps to `I2CSubIP.h`)
- I2C timing registers (SCL high/low counts, SDA hold/setup)
- I2C target addressing, interrupt status/mask for I2C events
- I2C-specific HAL functions for Sub-IP initialization and configuration
- Larger implementation due to dual register space (THC + I2C Sub-IP)

### 3.6 `ThcHid.h` / `ThcHid.cpp` - HID Protocol Handling

| Metric | SPI | I2C |
|--------|----:|----:|
| `ThcHid.cpp` lines | 2,303 | 2,662 |

**SPI-specific**:
- Uses HidSpiCx callbacks for HID report handling
- Report routing through HidSpiCx class extension

**I2C-specific**:
- `HID_DATA_PACKET` structure for I2C HID data framing
- `CIRCULAR_BUFFER` structure for report buffering
- `getFeatureFailCount`, `setFeatureFailCount` error tracking counters
- `txIoctlInProgressCount` for TX IOCTL concurrency tracking
- Larger implementation due to manual HID report parsing (no class extension)

### 3.7 `Queue.cpp` - I/O Queue Handling

| Metric | SPI | I2C |
|--------|----:|----:|
| `Queue.cpp` lines | 1,122 | 764 |

SPI's queue is significantly larger due to:
- HidSpiCx IOCTL routing for SPI-specific commands
- IPTS proprietary mode IOCTL handling
- Additional queue callbacks for filter driver integration

### 3.8 `Trace.h` - ETW Tracing

| Metric | SPI | I2C |
|--------|----:|----:|
| `Trace.h` lines | 171 | 148 |

SPI has more trace GUIDs, reflecting its additional subsystems (HidSpiCx, filter driver, proprietary mode).

### 3.9 `EventLogMsg.mc` - Event Log Messages

Different event log message definitions reflecting protocol-specific error conditions:
- SPI: SPI bus errors, opcode failures, HidSpiCx integration errors
- I2C: I2C bus errors, NAK conditions, I2C Sub-IP failures

### 3.10 `Utils.cpp` - Utility Functions

| Metric | SPI | I2C |
|--------|----:|----:|
| Functional difference | Minor | Minor |

SPI adds `THCBaseWriteRegistryDWordKey()` for registry DWORD key writing. Otherwise functionally similar.

---

## 4. UNIQUE Files - SPI Only

### 4.1 `Filter.cpp` / `Filter.h` - IPTS Filter Driver Interface

**Purpose**: Implements the Intel Precise Touch & Stylus (IPTS) proprietary mode interface, enabling GPU/EU kernel communication for advanced touch processing.

**Key structures**:
- `FILTER_CONTEXT` - Filter driver context with `IPT_THC_INTERFACE`, proprietary data buffers, feedback buffers
- Provides callbacks for proprietary data delivery from THC to IPTS filter driver
- Manages filter driver attach/detach lifecycle

**Significance**: This is the major differentiator. IPTS proprietary mode allows raw touch data to be processed by GPU compute shaders, enabling advanced palm rejection, pen/touch arbitration, and custom gesture recognition. The I2C driver does not support this mode.

### 4.2 `ThcInterface.h` - THC Interface Definition (532 lines)

**Purpose**: Defines the complete THC interface contract between the base driver and the IPTS filter driver.

**Key definitions**:
- `THC_FUNCTION_TABLE` - Functions the THC driver exposes to the filter
- `THC_CLIENT_FUNCTION_TABLE` - Functions the filter exposes to THC
- `CLIENT_THC_CALLBACKS` - Callback registration structure
- `IPT_THC_INTERFACE` - Top-level interface aggregating all tables
- Proprietary/HID mode switching APIs
- Memory window command interface
- Feedback buffer mechanisms
- Doorbell signaling for data readiness

### 4.3 `TouchSensorRegs.h` - Touch Sensor SPI Register Map (693 lines)

**Purpose**: Defines the SPI touch sensor register space as specified by the HIDSPI protocol.

**Key register groups**:
- Status registers (touch data ready, error flags)
- Frame characteristic registers (data size, format)
- Error registers (SPI bus errors, protocol violations)
- ID/capability registers (vendor ID, device ID, revision)
- Configuration registers (operating mode, report rate)
- Command registers (reset, power management)
- Power management registers (active, idle, sleep states)
- Vendor hardware info registers (OEM-specific)

### 4.4 `IntelQuickSPI.inf` - SPI Driver INF

Standard Windows driver INF for IntelQuickSPI, defining:
- Hardware IDs for SPI-connected THC devices
- HidSpiCx class extension co-installer requirements
- Service installation parameters

### 4.5 `IntelQuickSPI.rc` - SPI Resource File

Windows resource file with SPI-specific version information.

### 4.6 `IntelQuickSPI_provider.man` - SPI ETW Manifest

ETW provider manifest for SPI-specific tracing channels and keywords.

### 4.7 `IntelTHCBase.vcxproj.user` - User Project Settings

Visual Studio user-specific project settings (non-functional).

### 4.8 `stdint.h` - Local Standard Integer Header

Local copy of `stdint.h`. The I2C driver places this in `INC/stdint.h` instead.

---

## 5. UNIQUE Files - I2C Only

### 5.1 `I2CSubIP.h` - I2C Sub-IP Register Definitions (968 lines)

**Purpose**: Complete DesignWare (Synopsys) I2C controller register map for the I2C Sub-IP embedded within the THC.

**Key register groups**:
- `IC_CON` - I2C control (master/slave mode, speed, addressing)
- `IC_TAR` - Target address register
- `IC_SAR` - Slave address register
- `IC_DATA_CMD` - Data and command register
- `IC_SS_SCL_HCNT/LCNT` - Standard speed SCL timing
- `IC_FS_SCL_HCNT/LCNT` - Fast speed SCL timing
- `IC_HS_SCL_HCNT/LCNT` - High speed SCL timing
- `IC_INTR_STAT/MASK/RAW` - Interrupt status, mask, raw status
- `IC_TX_TL/RX_TL` - TX/RX FIFO thresholds
- `IC_DMA_CR/TDLR/RDLR` - DMA control and levels
- `IC_SDA_HOLD/SETUP` - SDA timing parameters
- SMBUS-related registers

**Significance**: This is the I2C-specific hardware abstraction layer counterpart to SPI's `TouchSensorRegs.h`. It programs the DesignWare I2C controller that sits behind the THC DMA engine.

### 5.2 `SmartFilter.h` - Smart Filter Interface (125 lines)

**Purpose**: VSYNC-synchronized input report filtering for display-sync touch delivery.

**Key structures**:
- `SMARTFILTER_CONTROL_REQUEST` - Control commands for smart filter enable/disable
- `SMARTFILTER_DATA_INPUT_REPORT` - Input report with display sync metadata
- VSYNC notification and timestamp correlation
- Input report coalescing for frame-aligned delivery

**Significance**: Enables touch reports to be synchronized with display refresh, reducing perceived input latency and eliminating visual artifacts from asynchronous touch-to-display updates.

### 5.3 `Swdma.cpp` / `Swdma.h` - Software-Triggered DMA (298 lines in .h)

**Purpose**: Software-triggered DMA channel specifically for I2C transactions that cannot use the standard RXDMA/TXDMA hardware-triggered paths.

**Key structures**:
- `SWDMA_CONFIGURATION` - SW DMA channel configuration
- `SWDMA_CONTEXT` - Runtime context for SW DMA operations
- Uses a single PRD table (vs 16 for regular RXDMA)
- Separate interrupt handling from hardware DMA channels

**Significance**: I2C requires software-triggered DMA for certain operations (e.g., reading HID descriptor, getting/setting features) where the transaction must be initiated by the host rather than triggered by device interrupt. SPI handles these through PIO (Programmed I/O) instead.

### 5.4 `IntelQuickI2C.inf` - I2C Driver INF

Standard Windows driver INF for IntelQuickI2C, defining hardware IDs for I2C-connected THC devices.

### 5.5 `IntelQuickI2C.rc` - I2C Resource File

Windows resource file with I2C-specific version information.

### 5.6 `IntelQuickI2C_provider.man` / `IntelQuickI2C_Provider.rc` - I2C ETW Manifest & Resource

ETW provider manifest and compiled resource for I2C-specific tracing.

### 5.7 `IntelQuickI2C_Provider_MSG00001.bin` / `IntelQuickI2C_ProviderTEMP.BIN` - Binary ETW Artifacts

Compiled binary ETW provider message tables (build artifacts).

### 5.8 `INC/` Subdirectory

Contains:
- `stdint.h` - Standard integer header (SPI has this at root level)
- `Filter/` - Subdirectory (empty or containing filter-related headers for I2C)

---

## 6. Line Count Comparison (Significant Source Files)

| File | SPI Lines | I2C Lines | Delta | Larger Driver |
|------|----------:|----------:|------:|:--------------|
| `Hal.cpp` | 3,935 | 4,265 | +330 | I2C |
| `Hal.h` | 2,499 | 2,937 | +438 | I2C |
| `Device.cpp` | 3,095 | 2,367 | +728 | SPI |
| `Dma.cpp` | 2,983 | 3,414 | +431 | I2C |
| `ThcHid.cpp` | 2,303 | 2,662 | +359 | I2C |
| `Queue.cpp` | 1,122 | 764 | +358 | SPI |
| `Acpi.cpp` | 330 | 679 | +349 | I2C |
| `Driver.cpp` | 239 | 180 | +59 | SPI |

**SPI-unique significant files**: `Filter.cpp`, `Filter.h`, `ThcInterface.h` (532 lines), `TouchSensorRegs.h` (693 lines)

**I2C-unique significant files**: `I2CSubIP.h` (968 lines), `SmartFilter.h` (125 lines), `Swdma.cpp`, `Swdma.h` (298 lines)

---

## 7. Validation Implications

### Areas requiring protocol-specific test coverage:

| Area | SPI Test Focus | I2C Test Focus |
|------|---------------|----------------|
| **Bus Init** | SPI opcode configuration, frequency, IO mode | I2C Sub-IP init, SCL timing, target address |
| **DMA** | Standard RXDMA/TXDMA, PIO fallback | RXDMA/TXDMA + SWDMA channel |
| **Power** | HidSpiCx power callbacks | I2C SET_POWER command, sleep state transitions |
| **Reset** | HidSpiCx reset flow, `PostResetDmaSetup` | Direct reset with response data validation |
| **ACPI** | DSM for opcodes, flags, addresses | DSD parsing, descriptor address, config |
| **Proprietary** | IPTS filter attach/detach, data/feedback buffers | N/A |
| **Smart Filter** | N/A | VSYNC sync, report coalescing, timestamps |
| **Error Handling** | SPI bus errors, opcode failures | I2C NAK, bus arbitration, Sub-IP errors |
| **HID Reports** | HidSpiCx report routing | Manual HID parsing, circular buffer |

---

## Appendix A: Complete File Inventory

### Files in HIDSPI driver (36 total)
```
Acpi.cpp          Acpi.h            DebugToolMsgs.h    Device.cpp
Device.h          Dma.cpp           Dma.h              Driver.cpp
Driver.h          eds.h             EventLogMsg.mc      Filter.cpp
Filter.h          Hal.cpp           Hal.h              HidDefs.h
IntelQuickSPI.inf IntelQuickSPI.rc  IntelQuickSPI_provider.man
IntelTHCBase.vcxproj.user           Public.h           Queue.cpp
Queue.h           resource.h        stdint.h           TelemetryReport.h
ThcHid.cpp        ThcHid.h          ThcInterface.h     TouchSensorRegs.h
Trace.h           Utils.cpp         Utils.h            Ver.h
```

### Files in HIDI2C driver (38 total)
```
Acpi.cpp          Acpi.h            DebugToolMsgs.h    Device.cpp
Device.h          Dma.cpp           Dma.h              Driver.cpp
Driver.h          eds.h             EventLogMsg.mc      Hal.cpp
Hal.h             HidDefs.h         I2CSubIP.h         INC/
IntelQuickI2C.inf IntelQuickI2C.rc  IntelQuickI2C_provider.man
IntelQuickI2C_Provider.rc           IntelQuickI2C_Provider_MSG00001.bin
IntelQuickI2C_ProviderTEMP.BIN      Public.h           Queue.cpp
Queue.h           resource.h        SmartFilter.h      Swdma.cpp
Swdma.h           TelemetryReport.h ThcHid.cpp         ThcHid.h
Trace.h           Utils.cpp         Utils.h            Ver.h
```

---

## SwAS-Derived Windows Driver Findings (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0. These findings describe Windows-specific driver behaviors documented in the Software Architecture Specifications.

### 8.1 ISR/DPC Pattern (QuickSPI SwAS P0603-P0624)

The Windows QuickSPI driver uses a standard ISR/DPC interrupt servicing pattern:
- **ISR**: Masks interrupts via `GBL_INT_EN`, queues DPC for processing
- **DPC**: Processes interrupt cause, handles data, then unmasks `GBL_INT_EN`
- **Lock**: Uses `WdfInterruptLock` to protect ISR/DPC re-entrancy
- **Key constraint**: Quiesce should **NOT** be called within ISR/DPC context (SwAS P0574-P0580)

### 8.2 Quiesce Scenarios (QuickSPI SwAS P0574-P0580)

Four documented quiesce scenarios in the Windows driver:
1. **During host-initiated reset** — quiesce before sending reset, unquiesce after
2. **Buffer threshold** — quiesce when free buffers drop to 8 (half of 16 total)
3. **D0Exit before D3** — quiesce as part of power transition
4. **NOT within ISR/DPC** — quiesce must NOT be called from interrupt context

### 8.3 Buffer Throttling (QuickSPI SwAS P0627)

- Throttling triggers at **8 free buffers** (half of 16 total PRD tables)
- Driver quiesces device until ALL buffers are freed
- This prevents buffer starvation during sustained high-rate touch input

### 8.4 Wake-on-Touch Windows Flow (QuickSPI SwAS P0706-P0726; QuickI2C SwAS P0823-P0851)

**WoT Entry (SPI)**:
- Windows issues `WaitWake` IRP to THC driver
- THC driver does NOT send SET_POWER(SLEEP) — device stays in active sensing mode
- Wake path: Touch device → GPIO → vGPIO → Platform wake (NOT through THC IP)
- No THC register writes for WoT — wake is entirely via GPIO/vGPIO path

**WoT Entry (I2C)**:
- SET_POWER(SLEEP) sent on entry — device enters low-power sensing mode
- SET_POWER(ON) sent on exit — device returns to active mode
- No device reset on WoT exit

**WoT Exit (both protocols)**:
- No reset on WoT exit — device returns to normal operation directly
- Windows Extension INF required: `WoT_QuickSpiExtension.inf` / `WoT_QuickI2cExtension.inf`

### 8.5 ECO Registry Keys (QuickSPI SwAS P0790-P0793; QuickI2C SwAS P0857-P0896, T7)

**QuickSPI registry keys**:
| Key | Type | Purpose |
|-----|------|---------|
| `IO_Mode_Override` | DWORD | Override SPI IO mode (Single/Dual/Quad) |
| `SPI_Frequency_Override` | DWORD | Override SPI clock frequency |
| `TxDMA_Override` | DWORD | Override TX DMA behavior |

**QuickI2C registry keys**:
| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `I2C_Max_Frame_Size_Enable` | DWORD | 0 | Enable I2C max frame size cap |
| `I2C_Max_Frame_Size` | DWORD | 128–255 | Max frame size value |
| `I2C_Int_Delay_Enable` | DWORD | 0 | Enable I2C interrupt delay |
| `I2C_Int_Delay` | DWORD | 1ms (PTL/WCL) | Interrupt delay value (variable on NVL+) |
| `EnEdgeTriggeredINT` | DWORD | 0 | Enable edge-triggered interrupt mode |
| `TimeStampEnable` | DWORD | 0 | Enable DMA timestamps |
| `ResetRequiredByDriver` | DWORD | — | Driver controls device reset |
| `ISRDPCProfilingEn` | DWORD | 0 | Enable ISR/DPC profiling |
| `EnResetPollingWA` | DWORD | 0 | Enable reset polling workaround |
| `EnableFWFlashWABOM36` | DWORD | 0 | FW flash workaround for BOM36 |
| `DoNotWaitForResetResponse` | DWORD | 0 | Skip reset response wait |

### 8.6 Bus Clear Recovery — Windows vs Linux (QuickI2C SwAS P0771)

| Feature | Windows | Linux |
|---------|---------|-------|
| SDA/SCL stuck bus clear | **Enabled** | **NOT enabled** |
| Recovery mechanism | THC HW bus clear per HAS | N/A |
| Impact | Auto-recovers from stuck bus | Requires manual reset |

### 8.7 RTD3 ACPI Constraint — Windows Only (QuickI2C SwAS P0300-P0317)

**Critical for BIOS developers targeting Windows**:
- **DO NOT** add `_PRW` (Power Resources for Wake) on THC ACPI device node with GPIO
- Windows interprets PRW as D3cold-capable → issues `WaitWake` IRP → **CRASH**
- **Correct approach**: Use `_PS0`/`_PS3`/`_DSW` methods instead of Power Resource
- For wake devices: no D3cold, `_S0W` = 3, power in `_PS0`/`_PS3`, `_DSW` modifies `_PS3` behavior

### 8.8 ACPI Frequency Encoding (QuickSPI SwAS P0900-P0912)

Windows driver reads SPI frequency from ACPI `connection_speed` DSM:
- Bits 0–2: `011`=40MHz, `100`=30MHz, `101`=24MHz, `110`=20MHz, `111`=17MHz
- `LimitPacketSize` encoding also in DSM return value
