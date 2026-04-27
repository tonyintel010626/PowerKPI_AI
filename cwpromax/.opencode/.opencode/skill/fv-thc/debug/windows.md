---
name: fv-thc/debug/windows
description: Windows-specific THC debug details — WPP tracing, registry keys, telemetry reports, debug report IDs, driver workarounds
---

> **Owner**: willychi | **Platform**: Windows | **Source**: HIDSPI v4.0.0.9000, HIDI2C v3.0.0.9000
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Windows Debug Reference

Windows-specific debug infrastructure, tracing GUIDs, registry keys, telemetry reports, debug tool protocol, and driver workarounds. For shared debug methodology and triage flows, see [SKILL.md](SKILL.md).

## Windows Driver Tracing GUIDs

| Type | GUID | Usage |
|------|------|-------|
| **WPP (HIDSPI)** (debug traces) | `{A891081A-80CD-45FC-B1F8-9F4FD8ECC101}` | `tracelog -start thc -guid #A891081A-80CD-45FC-B1F8-9F4FD8ECC101` |
| **WPP (HIDI2C)** (debug traces) | `{C47236A7-EEE4-4660-A7A2-349F6BB8E308}` | `tracelog -start thc -guid #C47236A7-EEE4-4660-A7A2-349F6BB8E308` |
| **ETW** (event telemetry) | `{937AD94E-CA8D-4B8E-8143-3FCE4ACCB8CB}` | Windows Event Viewer / `logman` collection |

> **Debug tip**: Enable WPP tracing with `tracelog` for detailed driver state machine traces. Note: HIDSPI and HIDI2C define separate WPP control GUIDs; enable the driver-specific GUID to capture the correct trace stream. ETW provides structured events for telemetry analysis.

### HIDSPI WPP Trace Flags (12 flags)

The HIDSPI driver defines 12 WPP trace flags for fine-grained trace filtering:

| Flag | Description |
|------|-------------|
| `QUICKSPI_ALL_INFO` | All info-level traces |
| `TRACE_DRIVER` | Driver entry/exit and lifecycle |
| `TRACE_DEVICE` | Device create/destroy and state changes |
| `TRACE_QUEUE` | I/O queue operations |
| `TRACE_DMA` | DMA engine operations |
| `TRACE_HAL` | Hardware abstraction layer |
| `TRACE_HID` | HID protocol handling |
| `TRACE_FILTER` | Filter driver interface |
| `TRACE_FUNCS` | Function entry/exit tracing |
| `TRACE_UTILS` | Utility functions |
| `TRACE_POWER` | Power management state transitions |
| `TRACE_SWDMA` | Software DMA (SWDMA) channel operations |

### HIDI2C WPP Trace Flags (13 flags)

The HIDI2C driver defines 13 WPP trace flags for fine-grained trace filtering:

| Flag | Description |
|------|-------------|
| `QUICKI2C_ALL_INFO` | All info-level traces |
| `TRACE_DRIVER` | Driver entry/exit and lifecycle |
| `TRACE_DEVICE` | Device create/destroy and state changes |
| `TRACE_QUEUE` | I/O queue operations |
| `TRACE_DMA` | DMA engine operations |
| `TRACE_HAL` | Hardware abstraction layer |
| `TRACE_HID` | HID protocol handling |
| `TRACE_FILTER` | Filter driver interface |
| `TRACE_FUNCS` | Function entry/exit tracing |
| `TRACE_UTILS` | Utility functions |
| `TRACE_POWER` | Power management state transitions |
| `TRACE_SWDMA` | Software DMA (SWDMA) channel operations |
| `TRACE_ACPI` | ACPI method evaluation and DSM parsing |

> **Usage**: Use `-flag` bitmask with `tracelog` to enable specific trace categories. For example, to trace only DMA and power: `-flag 0x0430` (TRACE_DMA | TRACE_POWER). Use `-flag 0xFFFF` for all flags.

## Debug Channel & Special HID Report IDs

| Report ID Constant | Value | Purpose |
|-------------------|-------|---------|
| `DEBUG_CHANNEL_FEATURE_REPORT_ID` | `0x5A` | Debug channel feature report — SetFeature with this ID is intercepted locally (bypasses TIC) |
| `DEBUG_CHANNEL_DATA_REPORT_ID` | `0x5B` | Debug channel data report |
| `TELEMETRY_REPORT_ID` | `0x5C` | Telemetry feature report |
| `PASSTHROUGH_FEATURE_REPORT_ID` | `0x5D` | Passthrough feature report |
| `INTEL_DEBUG_FEATURE_REPORT_SIZE` | 60 bytes | Fixed size of Intel debug feature reports |

> **Note**: SetFeature with `DEBUG_CHANNEL_FEATURE_REPORT_ID` (0x5A) is intercepted locally by the driver and does NOT get forwarded to the Touch IC (TIC). This is used for driver-internal debug tool communication.

## Windows Driver Telemetry Report

> **Source**: Windows drivers

The Windows drivers (HIDSPI and HIDI2C) expose a telemetry HID feature report used for diagnostics. The telemetry structure is defined in each driver's TelemetryReport.h and is identical across the QuickSPI and QuickI2C families. Current driver versions (from Intel THCBase Ver.h):

- HIDSPI driver: v4.0.0.9000
- HIDI2C driver: v3.0.0.9000

The Windows driver generates a telemetry HID feature report for diagnostics:

| Parameter | Value |
|-----------|-------|
| **Report ID** | `TELEMETRY_REPORT_ID = 0x5C` |
| **Version** | `TelemetryVersion = 3` (compile-time constant, hardcoded) |
| **Counter count** | 17 |

### Telemetry Counters (17 total)

> **Source**: Windows drivers `TelemetryReport.h`

Counters track driver-level **sensor reset** and **error** events (NOT hardware DMA/power/watchdog counters):

| # | Counter Name | Type | Description |
|---|-------------|------|-------------|
| 1 | `TotalSensorResetCount` | `uint32_t` | Total number of sensor resets |
| 2 | `SensorRespondsAfterInitialResetCount` | `uint16_t` | Sensor OK after initial reset |
| 3 | `SensorRespondsAfter1stResetRetryCount` | `uint16_t` | Sensor OK after 1st retry |
| 4 | `SensorRespondsAfter2ndResetRetryCount` | `uint16_t` | Sensor OK after 2nd retry |
| 5 | `SensorRespondsAfter3rdResetRetryCount` | `uint16_t` | Sensor OK after 3rd retry |
| 6 | `SensorFailsAfterAllResetRetriesCount` | `uint16_t` | Sensor still failed after all retries |
| 7 | `SensorResetReasonUnknownCount` | `uint16_t` | Resets with unknown reason |
| 8 | `SensorResetReasonFbRequestCount` | `uint32_t` | Resets due to FB request |
| 9 | `SensorResetReasonDrvRequestCount` | `uint16_t` | Resets due to driver request |
| 10 | `SensorResetReasonSpuriousInterruptCount` | `uint16_t` | Resets due to spurious interrupt |
| 11 | `SensorResetReasonMonitorOnCount` | `uint16_t` | Resets due to monitor-on event |
| 12 | `SensorResetReasonBistTestCount` | `uint16_t` | Resets due to BIST test |
| 13 | `SensorResetReasonPolicyUpdateCount` | `uint16_t` | Resets due to policy update |
| 14 | `SensorResetReasonMissingUframeCount` | `uint16_t` | Resets due to missing microframe |
| 15 | `SensorResetReasonDataSizeErrorCount` | `uint16_t` | Resets due to data size error |
| 16 | `SensorResetReasonUframeTimeoutCount` | `uint16_t` | Resets due to microframe timeout |
| 17 | `SensorErrorInterruptCount` | `uint16_t` | Error interrupt count |

Additional telemetry APIs (TELEMETRY_GET_FEATURE_COMMANDS):
- `GET_TELEMETRY_REPORT` command = `0x0001`
- `UNSUPPORED_COMMAND` sentinel = `0xFFFF`

> **Validation point**: This telemetry is Windows-only. Linux uses kernel tracepoints and debugfs instead.

## Heartbeat Feature Report

| Parameter | Value |
|-----------|-------|
| **Report ID** | `0x47` |
| **Purpose** | Periodic health check between driver and device |
| **Interval** | Configurable via registry |
| **HEARTBEAT_RESPONSE_TYPE** | `ALIVE(0)`, `RESET(1)`, `NEEDS_RESET(2)` |
| **TimeToNextHB** | Field in heartbeat response; time (ms) until next expected heartbeat |

> **Usage**: Driver periodically sends GET_FEATURE(0x47) to verify device responsiveness. Device responds with HEARTBEAT_RESPONSE_TYPE: `ALIVE(0)` = healthy, `RESET(1)` = device self-reset occurred, `NEEDS_RESET(2)` = device requests host-initiated reset. The `TimeToNextHB` field indicates the interval (ms) before the driver should send the next heartbeat. If no response within timeout, triggers device reset. Linux does not implement heartbeat.

## SmartFilter Protocol

The Windows driver implements a **fully functional** SmartFilter vendor-specific protocol for display-synchronized touch input:

| Report ID | Direction | Purpose |
|-----------|-----------|---------|
| `0xFE` | Control | SmartFilter control commands (enable/disable VSync) |
| `0xFD` | Data | SmartFilter data payloads (VSync-coalesced touch reports) |

SmartFilter data structures (from `SmartFilter.h`):
- `SMARTFILTER_CONTROL_REQUEST`: reportID + EnableAsyncReportingFlags + DisplaySyncSettings (delay 0-13107 × 10µs) + 3 reserved DWORDs
- `SMARTFILTER_DATA_INPUT_REPORT`: reportID + ErrorSts + vsyncTimestamp + inputReportCount + inputReportIDs[16] + inputReportTimeStampCount + inputReportTimestamp[16]

> **Note**: SmartFilter is fully implemented with complete data structures, hardware timestamp integration, and VSync alignment. The filter driver interface (GUID `{A2BCAC85-68F6-41B2-B112-DE4EA74770C6}`) has 9 sensor functions that are STUBs only in the **filter driver** — the core SmartFilter protocol handling in the THCBase driver itself is fully functional. The MSFT G5 extension INF (`MSFT_G5_ThcExtension.inf`) enables SmartFilter via `SmartFilter=1` for specific SUBSYS IDs.

## Fatal Error Bit Definitions

The Windows drivers define specific fatal error cause bits within `FATAL_ERR_CAUSE` (GENMASK(23,16) of ERR_CAUSE register):

| Bit | Name | Description |
|-----|------|-------------|
| 0 | Bus error | SPI/I2C bus-level fatal error |
| 1 | DMA error | DMA engine fatal error |
| 2 | Protocol error | Protocol state machine fatal error |
| 3 | Timeout | Hardware timeout fatal error |
| 4 | FIFO error | RX/TX FIFO fatal error |
| 5 | Integrity error | Data integrity check fatal error |

> **Unverified**: These bit definitions are from Windows driver source code and have NOT been verified against the HAS. The HAS defines `FATAL_ERR_CAUSE` as an 8-bit field but may use different bit assignments. Verify against `sip_thc_4x_has.html` before use.

## Windows Debug Tool Communication

The Windows drivers implement an internal debug-tool protocol (used by test-signed drivers and engineering tools) described in DebugToolMsgs.h. Important clarifications:

- These are NOT standard Windows CTL_CODE IOCTL control codes. The drivers define an enum of DEBUG_SET_GET_FEATURE_COMMANDS (DEBUG_REQUEST) and use feature-report based HID Set/Get/Async reports to exchange a debug message header + payload with the debug tool. In short: these are internal debug message types (enum values) carried over HID feature/input reports — not standalone CTL_CODE control codes.
- The debug message structure (from DebugToolMsgs.h):
  - Header fields: `BYTE reportID; DEBUG_REQUEST requestID; uint32_t timestamp;`
  - Payload: union of response structures (state, firmware version, register dumps, telemetry structures, etc.) sized to fit the debug input report (`INTEL_DEBUG_INPUT_REPORT_SIZE`).
- Key message types (examples from DebugToolMsgs.h):
  - `GET_TOUCH_SENSOR_ALL_REGISTERS` (0x0007) — read sensor register block
  - `GET_TOUCH_SENSOR_DEV_INFO` (0x0008) — sensor device info
  - `GET_TOUCH_SENSOR_FIRMWARE_VER` (0x000C) — firmware/hw version
  - `GET_DEBUG_TOOL_PROTOCOL_VERSION` (0x0010)
  - `FLUSH_DEBUG_QUEUE` (0x0011)
  - Notifications: `NOTIFY_GRAPHICS_STATE_CHANGED` (0x1001), `NOTIFY_THC_STATE_CHANGED` (0x1002), `NOTIFY_LOST_TOUCH_PACKETS` (0x1004)
  - Async control: `ENABLE_ASYNC_DEBUG_REPORTS` (0x2001), `DISABLE_ASYNC_DEBUG_REPORTS` (0x2002)
  - Additional commands: `GET_HID_MODE_TOUCH_PACKET_COUNT`, `GET_FEATURE_REPORTS_TO_TOUCH_SENSOR_COUNT`, `THCBASE_DEVICE_STATE`, `THCBASE_INITIATE_ERROR_RECOVERY_FLOW`
- How the debug tool connects: the driver exposes a HID interface — engineering tools use HID GET_FEATURE / SET_FEATURE / INPUT_REPORT mechanisms (DeviceIoControl wrappers on Windows) to send DEBUG_REQUEST values and receive HID_DEBUG_REPORT payloads. See DebugToolMsgs.h for the full enum and packet layout.
- When triaging, remember that the driver may forward debug communication to a TxThreadQueue / TxQueue. **HIDI2C** creates TxThreadQueue with `WdfIoQueueDispatchManual` (the driver explicitly dequeues and processes forwarded requests). **HIDSPI** creates TxQueue with `WdfIoQueueDispatchSequential` (WDF automatically dispatches requests one at a time). Do not assume the same dispatch model for both drivers.

> **Note**: Production drivers may not expose the engineering debug interface; DebugToolMsgs.h is present in test/debug builds. Use platform INF and driver build configuration to confirm availability.

## CancelGetFeatureRequest Race Condition

The Windows driver has a known race condition in `CancelGetFeatureRequest`: if a GetFeature request is cancelled while the driver is waiting for a TIC response, the cancellation can trigger `ScheduleErrorRecoveryFlowWorkItem`, which initiates a full error recovery flow (device reset + re-init). This can cause unexpected device resets during normal operation if GetFeature requests time out frequently. Debug tip: check telemetry `SensorResetReasonDrvRequestCount` for unexplained reset spikes.

## GetFeature report_type Bug (HIDI2C)

In the Windows HIDI2C driver, there is a bug at `ThcHid.cpp:1428` where `GET_INPUT_REPORT` is overwritten to feature type. This means that HID input report requests via GetFeature are silently converted to feature report requests, which can return incorrect data. This only affects the HIDI2C driver path.

## Windows Driver Sightings (from Audit Report)

| HSD | Status | Category | Description |
|-----|--------|----------|-------------|
| `22016570720` | documented | sw.driver | **Queue Race → Error Code 43**: Race condition in `Queue.cpp` during device removal causes Yellow Bang Error Code 43. Windows HIDSPI driver-specific. |
| `14021506058` | fixed | protocol | **Report ID Encoding**: Report ID threshold corrected to `< 15` (not `<= 15`) for 3rd-byte encoding in HIDI2C. |
| `16021846070` | workaround | sw.driver | **Edge-Triggered FW Flash**: I2C driver switches to edge-triggered interrupts during firmware flash. Registry key `EnableFWFlashWABOM36` controls the workaround. |

## Windows Driver HSDES Workarounds

### From HIDI2C Driver Audit

| HSDES ID | Title | Workaround |
|----------|-------|-----------|
| `16023750028` | DMA stall on S4 resume | Detect stalled RXDMA2 (ACTIVE==0 && pointers equal && non-zero) → full DMA reconfigure |
| `16024309461` | INVLD_DEV_ENTRY BSOD during FW flash | Guard against invalid device entry during firmware update |
| `16023561690` | S5 resume BSOD | Avoid WdfInterruptAcquireLock when not in D0 state |
| `16024259234` | Elan trackpad null pointer BSOD | Null pointer check for Elan trackpad (VID/PID-specific) |
| `16023244313` | Quiesce failure during continuous touch | 300µs delay before + 700µs delay after quiesce |

### From HIDSPI Driver Audit

| HSDES ID | Title | Workaround |
|----------|-------|-----------|
| `14016760177` | Write interrupt unreliable | `UseWriteInterrupts=false`, poll with 100µs interval, 500ms timeout |
| (no ID) | SpiBusLock BSOD | SpiBusLock/IELock are NO-OP stubs (bus synchronization disabled) |
| (no ID) | ADL A1 opcode register overlay | ICRRD aliased to DMARD@0x14, WR_OPCODE shifted to 0x18 on ADL A1 |
| (no ID) | MSFT Surface quiesce check | Surface-specific quiesce verification before reset |
| (no ID) | Wacom SET_POWER_ON fabrication | When content_length==0, fabricate response (length=1, content=0x1) |

## THC_WORKAROUNDS Bitfield (Registry)

> **Source**: Windows HIDSPI/HIDI2C drivers — `THC_WORKAROUNDS` registry value (DWORD)

The Windows drivers support a bitfield of workaround flags read from the registry at init:

| Bit | Name | Description |
|-----|------|-------------|
| 0 | `G5` | Enable MSFT G5 panel compatibility mode |
| 1 | `G5_NoResetInts` | Skip interrupt enable during G5 reset sequence |
| 2 | `DisableResetOnD0Exit` | Do not reset device when exiting D0 |
| 3 | `DisableDoze` | Disable D0i2 (doze) power state transitions |
| 4 | `SetSensing` | Use SET_SENSING command (not G5-specific) |
| 5 | `DisableHeartbeat` | Disable periodic heartbeat feature reports |
| 6 | `DisableIntCauseBadReset` | Do not reset on bad INT_CAUSE values |

> **Debug tip**: When triaging Windows driver issues, check if any workaround bits are set via `reg query "HKLM\SYSTEM\CurrentControlSet\Enum\PCI\...\Device Parameters" /v THC_WORKAROUNDS`. A non-zero value indicates active workarounds.

## Complete Windows Registry Key Reference

> **Source**: Windows HIDI2C driver `Registry.txt` + source code audit

### Standard Registry Keys (from Registry.txt)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Workarounds` | `REG_DWORD` | 0 | Workarounds bitfield (see THC_WORKAROUNDS above) |
| `ReportDescriptor` | `REG_BINARY` | — | HID Report Descriptor override |
| `DefaultSpiSpeed` | `REG_DWORD` | — | Override SPI default speed at startup (EDS TIC SPI Speed value) |
| `C_Start_Threshold` | `REG_DWORD` | — | Number of RX frames before coalescing starts |
| `C_Duration` | `REG_DWORD` | — | Coalescing duration |
| `C_Timer_Override` | `REG_DWORD` | — | One-time override of current coalescing countdown timer |
| `C_Idle_Threshold` | `REG_DWORD` | — | Number of idle coalescing timeouts |
| `DisplaySyncEventSource` | `REG_DWORD` | — | Display Sync Event source (00=None, 01=SW, 10=GPIO, 11=VW) |
| `DisplaySyncEmulatedTimerPeriod` | `REG_DWORD` | — | Emulated display sync period (2-100ms, unit=8µs) |
| `CoalescingEnable` | `REG_DWORD` | — | Enable display sync-based coalescing (1=enable) |
| `FPGA_LCBE` | `REG_DWORD` | 0 | Block Get Descriptor TCTL for LCBE workaround (1=using LCBE) |
| `GetFeatureCancelTimeout` | `REG_DWORD` | 3000 | GetFeature cancel timeout in ms |
| `GetFeatureOverrideReportId` | `REG_DWORD` | — | Report ID to override for GetFeature |
| `GetFeatureOverrideReportValue` | `REG_BINARY` | — | Report data to send on override |
| `ResetIntrDelayUs` | `REG_DWORD` | 500000 | Delay after reset in µs (default 500ms) |
| `UseTICReportDescriptorOnly` | `REG_DWORD` | 0 | Use TIC report descriptor only, don't concatenate Intel single finger |
| `ReadReportDescriptorOnReset` | `REG_DWORD` | — | Read report descriptor from TIC after each reset |
| `ResetTimeout` | `REG_DWORD` | — | Reset timeout in ms |
| `HoldResetLineHighOnFailure` | `REG_DWORD` | 0 | Leave RESET line high when driver fails to load |
| `FlashlessFw` | `REG_DWORD` | — | Enable flashless FW support |
| `FlashlessFwStage1File` | `REG_UNICODE_STRING` | — | Path to FW Stage 1 file |
| `FlashlessFwStage2File` | `REG_UNICODE_STRING` | — | Path to FW Stage 2 file |
| `FlashlessFwDataFile` | `REG_UNICODE_STRING` | — | Path to FW Data file |
| `TxDMA_Override` | `REG_DWORD` | 0 | Use PIO instead of TXDMA (TGL A0 debug) |

### Source-Only Registry Keys (NOT in Registry.txt)

| Key | Type | Default | Source | Description |
|-----|------|---------|--------|-------------|
| `EnableFWFlashWABOM36` | `REG_DWORD` | 0 | `Dma.cpp:46` | Enable FW flash workaround for BOM36 |
| `EnableTxQueueThreadWA` | `REG_DWORD` | 1 | `Dma.cpp:48,2954` (HIDI2C driver only) | Thread-based TX queue processing (HIDI2C only; does NOT exist in HIDSPI driver) |
| `EnableTHATWorkAround` | `REG_DWORD` | 0 | `Hal.cpp:88,2092` | THAT trackpad workaround (BOM5/FPGA) |
| `DontConcat` | `REG_DWORD` | — | `ThcHid.cpp:45` | Don't concatenate report descriptors |
| `RxDma2LogFilename` | `REG_UNICODE_STRING` | — | `Registry.txt:29` | Log RXDMA2 packets to file |
| `TxHoldDelay` | `REG_DWORD` | — | Source code | TX hold delay timing parameter |
| `RxHoldDelay` | `REG_DWORD` | — | Source code | RX hold delay timing parameter |
| `EnableDelayWA` | `REG_DWORD` | 0 | Source code | Enable delay workaround |
| `holdResetLineHighOnFailure` | `REG_DWORD` | 0 | Source code | Keep reset line high on driver load failure (lowercase variant) |
| `EnResetPollingWA` | `REG_DWORD` | 0 | Source code | Enable reset polling workaround |
| `DonNotWaitForResetResponse` | `REG_DWORD` | 0 | Source code | Skip waiting for reset response (note: typo "DonNot" is intentional — matches driver source) |

## See Also
- **[SKILL.md](SKILL.md)** — Shared debug methodology, triage flows, failure signatures, playbooks
- **`fv-thc/driver`** — Driver source analysis (Windows HIDI2C, Windows HIDSPI, Linux kernel)
- **`fv-thc/power`** — Power state triage, D0i2/D3 debug, PMCLite messages
