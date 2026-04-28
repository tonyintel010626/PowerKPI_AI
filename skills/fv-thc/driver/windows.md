> **Owner**: willychi | **Platform**: Windows
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Windows Driver Details

Windows-specific driver implementation details for THC HIDSPI and HIDI2C drivers.
For shared architecture and cross-platform comparison, see [SKILL.md](SKILL.md).

## Device State Machine

### Windows DeviceState Enum (HIDSPI and HIDI2C — same enum)
```
HWUninitialized (0) → HWUninitializing (1) → HWInitializing (2) → HWInitialized (3) → DMAAllocating (4) → TouchEnabled (5) → Active (6)
```
- `HWUninitialized (0)`: Hardware not initialized
- `HWUninitializing (1)`: Teardown in progress
- `HWInitializing (2)`: Hardware init in progress (MMIO, protocol config)
- `HWInitialized (3)`: MMIO mapped, basic tables in place
- `DMAAllocating (4)`: DMA allocation and configuration in progress
- `TouchEnabled (5)`: Touch enabled, reports can flow
- `Active (6)`: Device fully active

Both HIDSPI and HIDI2C Windows drivers use this same `DeviceState` enum for hardware lifecycle tracking.

### Windows HIDSPI — HidSpiCx Framework States
Additionally, the HIDSPI driver uses the HidSpiCx framework state machine (managed by OS). Driver-internal states track reset flow progress via `ResetStage` enum and `DeviceReady` flag.

Note: Windows state names are present-tense; Linux enums use past-tense style (`_RESETED`, `_INITED`) in the kernel sources.

## Windows Driver Architecture Details

- HIDSPI Windows driver: built on top of Microsoft HidSpiCx (HID SPI Class Extension) framework. The driver implements HidSpiCx callbacks and uses the class extension for report transport.
- HIDI2C Windows driver: direct KMDF driver (no HidSpiCx class extension). Implements KMDF device callbacks for I2C transport.
- Key WDF callbacks implemented in Windows drivers: `EvtDevicePrepareHardware`, `EvtDeviceReleaseHardware`, `EvtDeviceD0Entry`, `EvtDeviceD0Exit` (and associated D0EntryPostInterruptsEnabled helper flows).
- **D0EntryPostInterruptsEnabled arm-for-wake path**: On D0 re-entry from an armed-for-wake state, the driver performs DMA re-setup without issuing a device reset. This avoids unnecessary TIC reset cycles when the device was merely in a low-power wake-armed state (not fully powered off).
- HAL classes / abstractions used by the drivers: HalSPI, HalI2C, HalDMA, HalLTR, HalPIO, HalINT, HalGPIO, HalMMIO — these provide thin hardware abstraction layers for protocol-specific register sequences and DMA operations.
- Filter driver: an IPTS filter (historical) sits below the THC driver for HIDSPI/HIDI2C variants and validates client callbacks and forwards events via WDF work items.

## Windows ISR → DPC Handling

### Windows HIDI2C ISR → DPC
**ISR (DIRQL)**: Checks 6 sources (TIC, DMA ch1/2, ThcTx, ThcPio, SubIp, DispSync). Disables `GBL_INT_EN` → queues DPC.

**DPC priority order**:
1. STALL detection (ACTIVE==0 && TPCRP==TPCWP → DmaReconfigure)
2. TXN_ERR (INVLD_DEV_ENTRY → quiesce+reconfigure)
3. SCL_STUCK recovery
4. BUF_OVRRUN handling
5. FATAL_ERR recovery
6. TSSDONE (PIO completion)
7. DISP_SYNC event
8. SW RXDMA (SWDMA completion)
9. RxDma1/2 EOF (process HID reports)
10. Write DMA complete
11. I2C sub-IP errors

Re-enables `GBL_INT_EN` at DPC exit. Skips if device not in D0.

> **QuickI2C SwAS note**: The following THC error categories are NOT implemented by the QuickI2C driver: Write DMA errors, PIO Errors, I2C Sub-IP Errors. The THC IP generates these error bits but the QuickI2C driver does not handle them. FATAL_ERR IS handled in the DPC (priority #5 above). Note that FATAL_ERR recovery documented elsewhere applies to THC IP-level behavior.

> **ISR/DPC IE Race Pattern (SwAS)**: The ISR disables `GBL_INT_EN` at DIRQL, then the DPC re-enables it at DISPATCH_LEVEL on exit. To prevent a race where a new interrupt fires between DPC completion check and IE re-enable, the driver must acquire the WDF interrupt lock before writing `GBL_INT_EN=1` in the DPC exit path. Without this lock, a concurrent ISR could clear IE while the DPC is about to re-enable it, causing lost interrupts or double-processing.

### Windows HIDSPI ISR → DPC
Does NOT check/toggle `GBL_INT_EN` in ISR. DPC validates `sync_const==0x5A` and `protocol_version` in headers.

### EvtNotifyPowerDown (HIDSPI)
The HIDSPI driver implements an `EvtNotifyPowerDown` callback as the interrupt quiesce mechanism before D0Exit. This callback is invoked by HidSpiCx before the device transitions out of D0, allowing the driver to quiesce interrupts and DMA cleanly before power-down.

### ChangeInterruptState Pattern (M1)

The Windows HIDSPI driver implements a `ChangeInterruptState()` helper used extensively (~47 call sites) for selective per-vector interrupt masking/unmasking. This is the canonical SPI quiesce/unquiesce mechanism — the SPI ISR does NOT toggle `GBL_INT_EN` (unlike the I2C ISR which does). Instead, SPI uses per-vector masking via individual IE bits.

### EnableTxQueueThreadWA (M4)

> ⚠️ M4: Registry-controlled workaround (`EnableTxQueueThreadWA`) in the Windows HIDI2C driver creates a dedicated `TxThreadQueue` and kernel thread to serialize TX processing. Used on platforms/panels requiring serialized TX throughput. Check registry key presence when debugging I2C TX ordering issues.

## HIDSPI Reset Flow (Windows)
1. `InitiateHostResetProlog` (~600 lines): Program SPI addresses, modes, opcodes, DEVINT_CFG, MPS
2. ACPI `_RST` method with `'TSR_'` signature
3. Enable NonDMA interrupt → wait for reset response
4. `ProcessResetFlow()`: Read 24-byte descriptor via PIO → validate → configure LTR
5. `PostResetDmaSetup()`: DMA configuration

## HIDI2C Reset Flow (Windows)
1. SendSetPower(on)
2. Toggle DEVRST pin → SendResetRequest()
3. Wait for reset response via RX DMA
4. ProcessResetFlow(): Read 30-byte descriptor, validate, configure LTR
5. DmaAllocate → DmaConfigure → Display sync

### ProcessResetFlow Ordering
`ProcessResetFlow()` reads the device descriptor (24B SPI / 30B I2C), validates fields, and configures LTR. This is called after the reset response is received — it must complete before DMA setup proceeds.

### Error Recovery — MAX_RESET_RETRY_COUNT=4 and WdfDeviceSetFailed
The Windows HIDI2C driver retries `ProcessResetFlow` up to 4 times (`MAX_RESET_RETRY_COUNT=4`). When all reset retries are exhausted, the driver calls `WdfDeviceSetFailed(WdfDeviceFailedNoRestart)` to mark the device as permanently failed — no automatic restart is attempted.

## WDF Queue Architecture

### HIDI2C Queues
| Queue | Type | Purpose |
|-------|------|---------|
| RxQueue | Manual | Incoming HID reports from RXDMA |
| TxQueue | Sequential | Outgoing reports to TXDMA (**starts paused** — HSDES 16020586422) |
| PendingQueue | Manual | GET_REPORT waiting for SWDMA response |
| TxThreadQueue | Sequential | Alternative TX path (optional WA) |

### HIDSPI Queues
| Queue | Type | Purpose |
|-------|------|---------|
| HidSpiCx InputQueue | Parallel | OS HID reads |
| HidSpiCx OutputQueue | Sequential | OS HID writes |
| RxQueue | Manual | RXDMA routing |
| PendingQueue | Manual | GET_FEATURE/GET_INPUT (3s default timer, registry-configurable via `GetFeatureCancelTimeout`) |

> **⚠️ GET_FEATURE timer race condition**: There is a documented TODO in `ThcHid.cpp:1111-1117` noting a race between `CancelGetFeatureRequest` timer and `DmaReadBuffer`. If `DmaReadBuffer` calls `WdfTimerStop` + `WdfObjectDelete` while `CancelGetFeatureRequest` is executing `WdfTimerGetParentObject`, a BSOD can occur. The 3-second timeout makes this unlikely but not impossible.

## THC_WORKAROUNDS (Windows Registry Bitfield)

Windows driver exposes a `THC_WORKAROUNDS` bitfield read from a **registry key** (not ACPI/DSM). Individual bits control platform-specific quirks:

| Bit Flag | Description |
|----------|-------------|
| `G5` | G5 (S5/off-state) power handling workaround |
| `G5_NoResetInts` | Skip reset interrupt enable in G5 path |
| `DisableResetOnD0Exit` | Do not issue device reset during D0Exit |
| `DisableDoze` | Disable doze/idle power state transitions |
| `G5_SetSensing` | Set sensing mode in G5 path |
| `DisableHeartbeat` | Disable heartbeat keep-alive mechanism |
| `DisableIntCauseBadReset` | Disable interrupt-cause-triggered bad reset recovery |

These flags are initialized from the registry and gate application of specific code paths in Hal.cpp / Dma.cpp.

## Additional Windows Driver Behaviors

### POW_STATE Enum (ON/SLEEP only, no OFF)
The Windows `POW_STATE` enum only has two values: `ON` and `SLEEP`. There is no `OFF` state — the driver transitions between ON and SLEEP for TIC power management.

### i2cSettings() 13-Step Re-init on Every D0Entry
The Windows HIDI2C driver performs a full 13-step I2C sub-IP re-initialization on **every** D0Entry, not just on first init. This ensures the Synopsys I2C sub-IP is in a known good state after any power transition.

### SDA_STUCK_RECOVERY_ENABLE
During I2C init, the Windows driver sets `SDA_STUCK_RECOVERY_ENABLE` in the `IC_ENABLE` register to enable automatic SDA stuck bus recovery in the Synopsys I2C sub-IP.

### SetPowerLock
The Windows driver uses a `SetPowerLock` mechanism to synchronize concurrent SET_POWER command access, preventing races when multiple code paths attempt to change TIC power state simultaneously.

### HIDI2C: ACPI `_RST` Commented Out
The Windows HIDI2C driver has the ACPI `_RST` method call commented out in source. Instead, it uses GPIO DEVRST pin toggle for device reset. This differs from HIDSPI which uses ACPI `_RST`.

### SpiBusLock NO-OP
The Windows HIDSPI driver's `SpiBusLock` is a NO-OP (BSOD workaround) — no SPI bus synchronization is performed.

### HIDSPI: No freeze/thaw/poweroff/restore Callbacks
The Windows HIDSPI driver does NOT implement `freeze`, `thaw`, `poweroff`, or `restore` callbacks. Only `D0Entry`/`D0Exit` and the HidSpiCx-managed power transitions are used.

## Windows THCBase HID Layer (ThcHid.cpp — Phase 7 Audit)

> **Source**: Windows HIDSPI THCBase driver `ThcHid.cpp` (2303 lines) — Phase 7 line-by-line audit

### Registry Keys Controlling HID Behavior

7 registry keys control HID report descriptor loading, GET_FEATURE behavior, and FPGA fallback:

| Registry Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `ReportDescriptor` | Binary | — | Load HID report descriptor from registry instead of TIC |
| `DontConcat` | DWORD | 0 | If set, do NOT concatenate Intel debug/telemetry descriptors with TIC descriptor |
| `GetFeatureCancelTimeout` | DWORD | 3000 | GET_FEATURE cancel timer in milliseconds (overrides 3s default) |
| `GetFeatureOverrideReportId` | DWORD | — | Report ID to intercept for override response |
| `GetFeatureOverrideReportValue` | Binary | — | Fabricated response data for overridden report ID |
| `ReadReportDescriptorOnReset` | DWORD | 0 | If set, re-read report descriptor from TIC on each reset |
| `UseTICReportDescriptorOnly` | DWORD | 0 | If set, use only TIC report descriptor (no Intel descriptors appended) |

> **Validation point**: These keys are read during `HID_CONTEXT::Init()`. `GetFeatureOverrideReportId` + `GetFeatureOverrideReportValue` together enable registry-based response fabrication — GET_FEATURE requests matching the override report ID are completed immediately with the override value, never reaching the TIC.

### FPGA LCBE Fallback Path

| Registry Key | Type | Description |
|-------------|------|-------------|
| `FPGA_LCBE` | DWORD | If set, triggers Wacom default report descriptor fallback |

When `FPGA_LCBE` is set and `ReadReportDescriptorOnReset` is not set, the driver uses a hardcoded 475-byte `WacomReportDescriptor` (ThcHid.cpp:60-131) instead of reading from TIC. This descriptor defines:
- 5-finger multitouch digitizer (report ID `0x0C`)
- Pen digitizer (report ID `0x14`)
- Mouse (report ID `0x01`)
- Vendor-specific reports (IDs `0x03`, `0x10`, `0x0B`, `0x0F`, etc.)

### Report Descriptor Concatenation Modes

The driver builds the final HID report descriptor by concatenating multiple arrays. Two modes exist:

| Mode | Arrays Concatenated | Trigger |
|------|-------------------|---------|
| **withIntel** (default) | TIC descriptor + `IntelSingleFingerReportDescriptor` + `IntelDebugReportDescriptor` + `TelemetryReportDescriptor` | `DontConcat` = 0 AND `UseTICReportDescriptorOnly` = 0 |
| **withoutIntel** | TIC descriptor only | `DontConcat` = 1 OR `UseTICReportDescriptorOnly` = 1 |

Intel-appended descriptors add:
- **Single finger report** (report ID `0x40`): Simple single-touch digitizer
- **Debug report** (report ID `0x5A`): 512-byte feature + 512-byte input, vendor-defined
- **Telemetry report** (report ID `0x5C`): 19 telemetry fields (version 3)

### Two-Stage GET_FEATURE Dispatch

GET_FEATURE requests are dispatched in two stages before reaching the TIC:

1. **Telemetry intercept** (report ID `0x5C`): Handled locally — driver fills `IPT_TOUCH_TELEMETRY_DATA` struct directly, never sent to TIC
2. **Debug intercept** (report ID `0x5A`): Handled by `HandleGetDebugFeature()` — 9 sub-commands, never sent to TIC
3. **Override intercept**: If `getFeatureOverrideReport == TRUE` and report ID matches `getFeatureOverrideReportId`, returns registry-fabricated response
4. **TIC forward**: All other report IDs forwarded to TIC via TX DMA + PendingQueue + cancel timer

### Debug Feature Sub-Commands (Report ID 0x5A)

`HandleGetDebugFeature()` at ThcHid.cpp:1158-1254 handles 9 sub-commands via `DEBUG_SET_GET_FEATURE_COMMANDS` enum:

| Sub-Command | Description | Response Data |
|------------|-------------|---------------|
| `GET_HID_DRIVER_STATE` | Returns current driver state | `DevExt.state` as UINT8 |
| `GET_HID_MODE_TOUCH_PACKET_COUNT` | RxDMA2 frame count | `thc_m_prt_frm_cnt_2` register value |
| `GET_FEATURE_REPORTS_TO_TOUCH_SENSOR_COUNT` | GET/SET feature counters | `getFeatureRepToTicCount` + `setFeatureRepToTicCount` |
| `GET_HID_MODE_ERROR_COUNT` | Error count | `STATUS_NOT_SUPPORTED` (TODO) |
| `GET_RAW_MODE_ERROR_COUNT` | Raw mode errors | `STATUS_NOT_SUPPORTED` (filter driver) |
| `GET_NO_OF_MODE_TRANSITIONS` | HID↔Proprietary transitions | `NumOfTransitionsBetweenHidAndProprietary` |
| `GET_ME_PROTOCOL_VER` | ME protocol version | `STATUS_NOT_SUPPORTED` (not relevant) |
| `GET_GFX_PROTOCOL_VER` | GFX protocol version | `STATUS_NOT_SUPPORTED` (filter driver) |
| `THCBASE_DEVICE_STATE` | Device + power state | `state` + `devicePowerState` as UINT8 |
| `THCBASE_INITIATE_ERROR_RECOVERY_FLOW` | **Debug-only** (DBG build) | Triggers `ScheduleErrorRecoveryFlowWorkItem` if in D0 |

> **Note**: `THCBASE_INITIATE_ERROR_RECOVERY_FLOW` is only available in debug builds (`#ifdef DBG`). It provides a debug-tool trigger for the error recovery flow.

### Telemetry Report Details (Report ID 0x5C)

The `TelemetryReportDescriptor` (ThcHid.cpp:220-301) defines 19 fields with telemetry version 3:

| Field | Size | Description |
|-------|------|-------------|
| TelemetryVersion | 32-bit | Version number (currently 3) |
| TotalSensorResetCount | 32-bit | Total reset count |
| SensorRespondsAfterInitialResetCount | 16-bit | Resets recovered on first attempt |
| SensorRespondsAfter1stResetRetryCount | 16-bit | Recovered on 1st retry |
| SensorRespondsAfter2ndResetRetryCount | 16-bit | Recovered on 2nd retry |
| SensorRespondsAfter3rdResetRetryCount | 16-bit | Recovered on 3rd retry |
| SensorFailsAfterAllResetRetriesCount | 16-bit | Failed after all retries |
| SensorResetReasonUnknownCount | 16-bit | Unknown reset reason |
| SensorResetReasonFbRequestCount | 32-bit | Feedback request reset |
| SensorResetReasonDrvRequestCount | 16-bit | Driver-requested reset |
| SensorResetReasonSpuriousInterruptCount | 16-bit | Spurious interrupt reset |
| SensorResetReasonMonitorOnCount | 16-bit | Monitor-on reset |
| SensorResetReasonBistTestCount | 16-bit | BIST test reset |
| SensorResetReasonPolicyUpdateCount | 16-bit | Policy update reset |
| SensorResetReasonMissingUframeCount | 16-bit | Missing microframe reset |
| SensorResetReasonDataSizeErrorCount | 16-bit | Data size error reset |
| SensorResetReasonUframeTimeoutCount | 16-bit | Microframe timeout reset |
| SensorErrorInterruptCount | 16-bit | Error interrupt count |
| Reserved | 16-bit × 20 | 40 bytes reserved for future use |

### TraceLogging / ETW / WPP Triple Tracing

The driver uses three independent tracing systems (Driver.cpp:61-115):

| System | Provider Name | GUID | Init Order |
|--------|-------------|------|------------|
| **TraceLogging** | `Intel-QuickSPI` | `{de09e372-44f2-429e-9ef2-5d361adc076d}` | 1st (DriverEntry) |
| **ETW** | `Intel_Driver_THCBase_Provider` | (manifest-generated) | 2nd |
| **WPP** | (TMH-based) | — | 3rd |

Cleanup order is reverse: TraceLoggingUnregister → WPP_CLEANUP → EventUnregister.

> **Validation point**: WPP traces go to IFR (In-Flight Recorder) via WppRecorder. ETW events are logged via manifest-generated `EventWrite*` functions. TraceLogging is the newest system. All three are active simultaneously.

### Idle Notification and Power Transitions

The idle notification handler (`HandleIdleNotificationRequest`, ThcHid.cpp:1578+) follows the Microsoft Synaptics Touch sample pattern:
- Uses WDF work items at PASSIVE_LEVEL for idle processing
- **TxQueue stop/start**: TxQueue is stopped before idle transition and restarted after wake — prevents output reports during power transitions
- Idle request is pended and completed when device resumes

### HID String Identifiers

| String ID | Value |
|-----------|-------|
| Manufacturer | `"Intel"` |
| Product | `"precise touch"` |
| Serial Number | `""` (empty) |
| Device | `"Intel(R) Precise Touch 3.0 - Base Driver"` |

## IPTS Filter Driver (Historical — HIDSPI Only)

Interface GUID: `{A2BCAC85-68F6-41B2-B112-DE4EA74770C6}`, Version 1.0

**THC Function Table (9 functions — ALL stubs, IPTS EOL)**:
RegisterSensorReadyNotification, GetDeviceInfo, SetMode, SetMemWindow, SignalReadyForData, SendFeedbackData, ResetSensor, DisableTouchSensor, EnableTouchSensor.

**Client Callbacks (3)**: NotifyDataAvailable, NotifyTouchSensorDetectedResponse, NotifyTouchSensorStatus — delivered via WDF work items at PASSIVE_LEVEL.

### Filter Interface Client Validation

The filter driver (`Filter.cpp`) validates 4 mandatory client callbacks during `EvtDeviceProcessQueryInterfaceRequest`:

| Callback | Required | Purpose |
|----------|----------|---------|
| `NotifyDataAvailable` | **Yes** | Called when new touch data arrives |
| `NotifyTouchSensorDetectedResponse` | **Yes** | Called when sensor detected |
| `NotifyTouchSensorStatus` | **Yes** | Called on sensor status change |
| `ClientContext` (Handle) | **Yes** | Client context handle (non-null) |

If any of these 4 are NULL, the query interface request is rejected with `STATUS_INVALID_PARAMETER`. All callbacks are delivered via WDF work items at PASSIVE_LEVEL, not directly from DPC context.

## See Also
- **[SKILL.md](SKILL.md)** — Shared architecture, cross-platform comparison, HSDES workarounds
- **[linux.md](linux.md)** — Linux kernel driver implementation details
