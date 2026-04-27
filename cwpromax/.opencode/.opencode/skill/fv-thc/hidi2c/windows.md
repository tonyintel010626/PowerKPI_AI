# THC HIDI2C — Windows Implementation

> **Owner**: willychi | **Platform**: Windows | **Source**: drivers.platform.ipts.hid-i2c-touch
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

Windows-specific HIDI2C driver implementation details. For shared protocol spec and I2C sub-IP HW, see [SKILL.md](SKILL.md). For Linux implementation, see [linux.md](linux.md).

## Windows I2C Init Sequence (13 Steps)

The Windows HIDI2C driver uses a 13-step I2C sub-IP init (vs 11-step Linux kernel). Note: Windows IC_CON is programmed via read-modify-write (not direct write), and SPEED is set dynamically from ACPI connection_speed:

| Step | Register | Value | Notes |
|------|----------|-------|-------|
| 1 | `PORT_TYPE` | `0x01` (I2C) | ⚠️ Not in Linux init — set separately |
| 2 | `IC_ENABLE` | `0` | Disable before configuration |
| 3 | `IC_CON` | `0x0663` | Master, Fast, Restart EN, Slave DIS, **+RX_FIFO_FULL_HLD_CTRL(9)**, **+STOP_DET_IF_MASTER_ACTIVE(10)**. **TX_EMPTY_CTRL(bit 8) = 0** — Windows explicitly does NOT set TX_EMPTY_CTRL. Written via **read-modify-write**, SPEED field set dynamically from ACPI |
| 4 | `IC_TAR` | Device addr | e.g., `0x0A` (WACOM) |
| 5 | `IC_SS/FS_SCL_HCNT/LCNT` | Timing values | Per speed mode |
| 6 | `IC_INTR_MASK` | `0x7FFF` | All I2C interrupts |
| 7 | `IC_RX_TL` | 62 | RX FIFO threshold |
| 8 | `IC_TX_TL` | 0 | TX FIFO threshold |
| 9 | `IC_DMA_CR` | `0x03` | TX+RX DMA enable |
| 10 | `IC_DMA_TDLR` | 7 | DMA TX data level |
| 11 | `IC_DMA_RDLR` | 7 | DMA RX data level |
| 12 | **`IC_SDA_HOLD`** | ISUB/Registry/Default | Windows DOES program `IC_SDA_HOLD` using ISUB fields (SMTD/FMTD/HMTD for TX hold, SMRD/FMRD/HMRD for RX hold), registry override, or default values. This differs from Linux which does NOT program IC_SDA_HOLD |
| 13 | `IC_ENABLE` | `1` | Enable after configuration |

> **Windows extras vs Linux**: Steps 1 (PORT_TYPE), 3 (RX_FIFO_FULL_HLD_CTRL + STOP_DET_IF_MASTER_ACTIVE in IC_CON, read-modify-write), and 12 (IC_SDA_HOLD from ISUB/registry) are not in the Linux 11-step init. Note: `IC_SDA_STUCK_RECOVERY_ENABLE` (previously listed as a separate step) is conditionally set but not always present, reducing the count from 14 to 13. Step 12 programs IC_SDA_HOLD using ISUB fields SMTD/FMTD/HMTD (TX hold) and SMRD/FMRD/HMRD (RX hold) per mode.

> ⚠️ D4: TX_EMPTY_CTRL behavior divergence — Windows sets `TX_EMPTY_CTRL` (IC_CON bit 8) to **0** (disabled) and leaves TX_EMPTY interrupt disabled in `IC_INTR_MASK`; the driver relies on software TX queue state instead of TX_EMPTY IRQ, whereas SwAS expects HW-driven TX_EMPTY notifications.

> ⚠️ D5: Missing IC_SDA_SETUP / IC_FS_SPKLEN / IC_HS_SPKLEN programming — the Windows driver conditionally programs `IC_SDA_HOLD` but does not program `IC_SDA_SETUP`, `IC_FS_SPKLEN`, or `IC_HS_SPKLEN` unless explicit registry/ACPI overrides are present. SwAS lists these as required for proper spike suppression and high-speed timing.

## Windows I2C Timing Defaults (HIDI2C v3.0.0.9000)

| Parameter | Windows Value | Notes |
|-----------|--------------|-------|
| SS_HCNT | `0x73` (115) | |
| SS_LCNT | `0x7D` (125) | |
| FS_HCNT | `0x1F4` (500) | ⚠️ Defined as defaults but NEVER used as actual fallbacks — code falls back to SS defaults (115/125) regardless of speed mode |
| FS_LCNT | `0x24C` (588) | ⚠️ Same as FS_HCNT — these FS defaults are defined but never used as fallbacks |
| RX_TL | 62 | |
| TX_TL | 0 | |
| DMA_CR | `0x03` | TX+RX DMA enable |
| DMA_TDLR | 7 | |
| DMA_RDLR | 7 | |
| INTR_MASK | `0x7FFF` | All interrupts enabled |
| TARGET_ADDR | `0x0A` | Default = WACOM address |

## Windows I2C Interrupt Enable Mask

Only 7 of 11 interrupt bits are enabled. Windows does NOT enable START_DET(26) or STOP_DET(25), in addition to TX_EMPTY(21) being disabled and ACTIVITY(23) having no enable bit.

> **Key difference from Linux**: Linux enables 9 of 11 bits (includes START_DET and STOP_DET); Windows only enables 7 of 11.

## Windows IC_SDA_HOLD via ISUB

Windows DOES program `IC_SDA_HOLD` using the ISUB fields:
- **TX Hold**: SMTD (Standard), FMTD (Fast), HMTD (High-Speed)
- **RX Hold**: SMRD (Standard), FMRD (Fast), HMRD (High-Speed)

The driver uses ISUB values, registry override, or built-in defaults as fallback. This contrasts with Linux which ignores all SDA hold fields entirely.

## Windows BUS_CLEAR_FEATURE_CTRL

- `IC_SDA_STUCK_RECOVERY_ENABLE=1` is set in Windows init
- `BUS_CLEAR_FEATURE_CTRL` in IC_CON is **COMMENTED OUT** in the Windows code — it is NOT enabled despite being documented
- **Validation point**: SDA stuck recovery is enabled (SCL pulse recovery), but SCL stuck bus-clear is not

## Windows ACPI _RST Behavior

Windows ACPI _RST is **commented out** — the driver uses GPIO DEVRST (device reset pin) instead of ACPI `_RST` method.

## Error Recovery (Windows HIDI2C)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MAX_RESET_RETRY` | 4 | Maximum reset attempts before giving up |
| `TIC_RESET_ASSERT` | 300 ms | DEVRST pin assertion duration |
| `POWER_UP` | 500 ms | Wait after power-up before communication |
| `DEASSERT_NEW` | 100 ms | Wait after DEVRST de-assertion (newer devices) |

## DELAY_BEFORE_DEVICE_PIO (Windows HIDI2C)

The Windows HIDI2C driver enforces a **300ms delay** before the first PIO transaction to the device after power-on:

| Constant | Value | Description |
|----------|-------|-------------|
| `DELAY_BEFORE_DEVICE_PIO` | 300,000 µs (300ms) | Delay before first PIO to device |

> **Validation point**: This delay allows the touch device to fully initialize after power-on. Without it, PIO reads may return stale or invalid data. Linux does not have an equivalent explicit delay — it relies on ACPI `_RST` timing.

## Report Descriptor Validation (M7)

The Windows HIDI2C driver (`ThcHid.cpp`) validates that the report descriptor's **last byte equals `0xC0`** (HID End Collection tag). If the last byte is not `0xC0`, the driver rejects the descriptor as malformed. The Windows HIDSPI driver does **NOT** perform this same last-byte check — SPI tests should not assume this validation exists.

## GetFeature Timeout and Error Recovery Escalation

When a GET_FEATURE request times out (default 3 seconds per `DEFAULT_GET_FEATURE_CANCEL_TIMEOUT`), the Windows driver escalates through an error recovery sequence:
1. Cancel the pending SWDMA operation
2. If cancellation fails, attempt device reset
3. If reset fails, disable the device
- **Validation point**: Induce GET_FEATURE timeout and verify escalation path completes without hang

## SET_FEATURE Behavior (HIDI2C)

- **SET_FEATURE has no I2C device response** — after the host sends a SET_FEATURE command via TXDMA, there is no interrupt or acknowledgement from the I2C device. The driver must rely on TXDMA completion alone to confirm the write was clocked onto the bus.
- **Validation point**: Do not wait for a device interrupt after SET_FEATURE. Verify TXDMA completion status only.

## Passthrough Feature Report (Windows HIDI2C)

| Constant | Value | Description |
|----------|-------|-------------|
| `PASSTHROUGH_FEATURE_REPORT_ID` | `0x5D` | Passthrough feature report ID used for vendor-specific data passthrough |

## THAT Trackpad Workaround (Windows HIDI2C — Swdma.h/Swdma.cpp)

> **Source**: Windows HIDI2C driver `Swdma.h:18-19`, `Swdma.cpp:1205,1896`

The Windows driver includes a vendor-specific workaround for the THAT trackpad that strips 160 extra bytes from the report descriptor:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `THAT_VID` | `0x911` | Vendor ID for THAT trackpad |
| `THAT_PID` | `0x5288` | Product ID for THAT trackpad |
| **Workaround** | Strip 160 bytes | Report descriptor has 160 extra trailing bytes that must be removed |

The workaround is triggered by either:
1. `EnableTHATWorkAround` registry key set to `1`, OR
2. Device VID/PID matches `0x911`/`0x5288`

> **Additional behavior**: For THAT devices, the driver also skips waiting for reset response during device initialization (`Device.cpp:1169,1221`).

## Heartbeat Feature Report (Windows HIDI2C — eds.h)

> **Source**: Windows HIDI2C driver `eds.h:108-129`

### HEARTBEAT_RESPONSE_TYPES Enum

| Value | Name | Description |
|-------|------|-------------|
| 0 | `HEARTBEAT_RESPONSE_TYPE_SUCCESS` | Device healthy |
| 1 | `HEARTBEAT_RESPONSE_TYPE_ERROR` | Device error — proprietary data contains error info |
| 2 | `HEARTBEAT_RESPONSE_TYPE_NEEDS_RESET` | Device requests reset |
| 3 | `HEARTBEAT_RESPONSE_TYPE_DATA_TYPE_MAX` | Sentinel value |

### TOUCH_HEARTBEAT_FEATURE_REPORT Struct

| Field | Type | Description |
|-------|------|-------------|
| `ReportId` | `uint8_t` | Always `0x47` (`HEARTBEAT_FEATURE_REPORT_ID`) |
| `HeartbeatResponseType` | `uint32_t` | Value from `HEARTBEAT_RESPONSE_TYPES` |
| `ProprietaryData[16]` | `uint8_t[16]` | Vendor-specific data (populated on ERROR) |
| `TimeToNextHB` | `uint32_t` | Time in ms until next heartbeat from driver |

> **Validation point**: When `HeartbeatResponseType == NEEDS_RESET`, the driver triggers a full device reset. When `== ERROR`, the `ProprietaryData` field contains vendor-specific error information.

## SmartFilter Protocol (Windows HIDI2C — Display Sync)

> **Source**: Windows HIDI2C driver `SmartFilter.h` / `ThcHid.cpp` — Phase 6b deep read

SmartFilter enables display-synchronized touch input for reduced latency and jitter. It uses special HID report IDs to control async reporting and VSync alignment.

### SmartFilter Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CONTROL_REPORT_ID` | `0xFE` | SmartFilter control report ID |
| `DATA_REPORT_ID` | `0xFD` | SmartFilter data report ID |
| `MAX_REPORTS_PER_VSYNC` | 16 | Maximum reports per VSync period |
| `ENABLE_ASYNC` | `0x0001` | Enable async reporting |
| `DISABLE_ASYNC` | `0x0000` | Disable async reporting |
| `DisplaySyncDelay` | 0–13107 | Delay in units of 10µs (0–131.07ms) |

### VSync Enable Sequence (3 Steps)

1. Send `DISABLE_ASYNC` (0x0000) to control report ID `0xFE`
2. Configure `DisplaySyncDelay` value
3. Send `ENABLE_ASYNC` (0x0001) to control report ID `0xFE`

### SmartFilter VSync Retry Mechanism

When VSync enable fails (e.g., SET_FEATURE to control report `0xFE` times out or returns error), the Windows driver implements a retry mechanism:
- Retries the VSync enable sequence up to a configured limit
- Each retry re-sends the DISABLE_ASYNC → configure delay → ENABLE_ASYNC sequence
- **Validation point**: Verify retry behavior when the device temporarily NAKs SmartFilter control commands

### MSFT G5 Extension INF

- **ExtensionId**: `{3c146409-7256-4a7f-8927-292a8cdf3143}`
- **Purpose**: Enables SmartFilter (`SmartFilter=1`) for specific SUBSYS IDs matching Microsoft G5 touch panels
- **INF file**: `MSFT_G5_ThcExtension.inf` (only in HIDI2C driver)

> **Validation point**: SmartFilter requires both driver support AND device support (via `0xFE`/`0xFD` report IDs). Verify SmartFilter VSync enable/disable transitions and `MAX_REPORTS_PER_VSYNC` limit.

## Windows Queue Architecture (Queue.h/Queue.cpp)

> **Source**: Windows HIDI2C driver `Queue.h`, `Queue.cpp`, `Device.h`, `Dma.cpp`

The Windows driver uses 5 WDF I/O queues with different dispatch types:

| Queue | Dispatch Type | Purpose | Context |
|-------|--------------|---------|---------|
| **DefaultQueue** | Parallel | Default I/O dispatch — handles most HID IOCTLs | `DEVICE_CONTEXT` |
| **RxQueue** | Manual | Stores pending read requests until DMA data arrives | `DEVICE_CONTEXT` |
| **TxQueue** | Sequential | Serialized write/command requests to device | `WRITE_QUEUE_CONTEXT` |
| **TxThreadQueue** | Manual | Thread-based TX processing (when `EnableTxQueueThreadWA=1`) — uses `WdfIoQueueDispatchManual` | `WRITE_QUEUE_CONTEXT` |
| **PendingQueue** | Manual | Stores requests awaiting matching response data | `DEVICE_CONTEXT` |

### Request Matching (FindRequestWithMatchingData)

The driver implements a callback-based request matching system for finding pending requests:

| Callback | Purpose | Match Criteria |
|----------|---------|---------------|
| `CompareByInternalIoctl` | Match by IOCTL code | `Ioctl` field |
| `CompareByRequestValue` | Match by request handle | Direct WDFREQUEST comparison |
| `CompareByReportId` | Match by HID Report ID | `ReportId` field |

> **Usage**: `FindRequestWithMatchingData(Queue, Callback, Data, &OutRequest)` walks the queue calling the comparison callback for each pending request. Used to complete GET_FEATURE requests when the matching response arrives via SWDMA.

## WRITE_DATA_TYPE Enum (Windows HIDI2C — eds.h)

The Windows HIDI2C driver defines a `WRITE_DATA_TYPE` enum for firmware update write operations:

The Windows HIDI2C driver (`eds.h`) defines:

| Value | Name | Description |
|-------|------|-------------|
| 0 | `FW_STAGE1_LOAD` | Firmware stage 1 load |
| 1 | `FW_STAGE2_LOAD` | Firmware stage 2 load |
| 2 | `FEEDBACK_DATA` | Feedback data |
| 3 | `SET_FEATURES_DATA` | Set features data |
| 4 | `GET_FEATURES_DATA` | Get features data |
| 5 | `OUTPUT_REPORT_DATA` | Output report data |
| 6 | `DATA_LOAD` | Data load |
| 7 | `TCTL_REQUEST` | TCTL request |
| 8 | `IMAGE_NOT_AVAILABLE` | Image not available |
| 9 | `MAX_WRITE_DATA_TYPES` | Maximum value sentinel |

A separate legacy enum exists in `TouchSensorRegs.h` (IPTS/TIC interface):

| Value | Name | Description |
|-------|------|-------------|
| 0 | `FW_LOAD` | Firmware load |
| 1 | `DATA_LOAD` | Data load |
| 2 | `FEEDBACK` | Feedback data |
| 3 | `SET_FEATURES` | Set features |
| 4 | `GET_FEATURES` | Get features |
| 5 | `OUTPUT_REPORT` | Output report |
| 6 | `NO_DATA_USE_DEFAULTS` | No data, use defaults |
| 7 | `MAX` | Maximum value sentinel |

> **Validation point**: Firmware flash operations use `WRITE_DATA_TYPE` values 1–4 to sequence multi-stage firmware updates. The `EnableFWFlashWABOM36` registry key enables FW flash workaround for BOM36 devices.

## Windows Registry Keys

### Additional Windows Registry Keys (Source-Only — Not in Registry.txt)

> **Source**: Various source files in THCBase

| Key | Type | Default | Source | Description |
|-----|------|---------|--------|-------------|
| `EnableFWFlashWABOM36` | `REG_DWORD` | 0 | `Dma.cpp:46` | Enable FW flash workaround for BOM36 devices |

> **Mutual exclusivity**: `EnableFWFlashWABOM36` and `I2C_Int_Delay_Enable` must NOT be enabled simultaneously — use one or the other.

| `EnableTxQueueThreadWA` | `REG_DWORD` | 1 (enabled) | `Dma.cpp:48,2954` | Enable thread-based TX queue processing |
| `EnableTHATWorkAround` | `REG_DWORD` | 0 | `Hal.cpp:88,2092` | Enable THAT trackpad workaround (BOM5 panel with FPGA) |
| `DontConcat` | `REG_DWORD` | — | `ThcHid.cpp:16` | Don't concatenate report descriptors |
| `RxDma2LogFilename` | `REG_UNICODE_STRING` | — | `Registry.txt:29` | Log RXDMA2 packets to file for debug |

### ECO Fix Registry Keys (from QuickI2C SwAS v1.0)

The QuickI2C SwAS defines additional registry keys for ECO fixes and platform-specific tuning that are NOT documented in the Windows driver's `Registry.txt`:

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `I2C_Max_Frame_Size_Enable` | `REG_DWORD` | 0 | 0-1 | Enable max frame size override (ECO fix) |
| `I2C_Max_Frame_Size` | `REG_DWORD` | 255 | **128–255** | Maximum I2C frame size in bytes. Only effective when `I2C_Max_Frame_Size_Enable=1` |
| `I2C_Int_Delay_Enable` | `REG_DWORD` | 0 | 0-1 | Enable interrupt delay override (ECO fix) |
| `I2C_Int_Delay` | `REG_DWORD` | Platform-dependent | In 10µs multiples | Interrupt servicing delay. PTL/WCL defaults to 1ms (100×10µs); NVL+ configurable |
| `EnEdgeTriggeredINT` | `REG_DWORD` | 0 | 0-1 | Enable edge-triggered interrupt mode (vs default level-triggered) |
| `TimeStampEnable` | `REG_DWORD` | 1 | 0-1 | Enable DMA timestamp feature for touch reports |
| `ResetRequiredByDriver` | `REG_DWORD` | 0 | 0-1 | Whether driver should issue HID RESET during init |
| `ISRDPCProfilingEn` | `REG_DWORD` | 0 | 0-1 | Enable ISR/DPC profiling for performance analysis |
| `EnResetPollingWA` | `REG_DWORD` | 1 | 0-1 | Enable reset polling workaround (poll for reset sentinel instead of waiting for interrupt). When enabled, reset response is read via polling (not interrupt). Interrupts are enabled only after the report descriptor has been successfully read |
| `DoNotWaitForResetResponse` | `REG_DWORD` | 0 | 0-1 | Skip waiting for reset response sentinel. Used for devices (e.g., THAT trackpad) that don't send proper reset response |

> **⚠️ Source**: QuickI2C SwAS v1.0 (Sep 10, 2025). These keys are read from the Windows registry during driver init and override ACPI-provided defaults. The `I2C_Max_Frame_Size` range of 128–255 is a SwAS constraint — values outside this range may cause unpredictable behavior.
> **Validation point**: Test each ECO fix key independently. Verify `I2C_Max_Frame_Size` rejects values < 128 or > 255. Verify `I2C_Int_Delay` is in 10µs multiples. Verify `DoNotWaitForResetResponse=1` allows init to complete even when device doesn't send reset sentinel.
> **Reset-response rule**: During reset flow, discard any non-reset input reports until the reset sentinel (`0x0000` length) is observed. Treat pre-sentinel reports as stale/noise and do not dispatch them to HID paths.

## Windows-Only PCI Device IDs (HIDI2C)

| Platform | THC0 Device ID | THC1 Device ID | Source |
|----------|---------------|---------------|--------|
| ADL-LP | `0x7A50` | `0x7A51` | Windows HIDI2C driver (not in Linux kernel) |
| LNL-M | `0xA848` | `0xA84A` | Both Windows and Linux |

> **⚠️ ADL-LP HIDI2C**: The ADL-LP PCI IDs `7A50`/`7A51` appear in the Windows HIDI2C driver but NOT in the Linux kernel. This suggests HIDI2C support was validated on ADL-LP with the Windows driver before the Linux kernel gained HIDI2C support at LNL.

## See Also
- **[SKILL.md](SKILL.md)** — Shared HIDI2C protocol spec and I2C sub-IP HW reference
- **[linux.md](linux.md)** — Linux QuickI2C implementation
- **`fv-thc/driver`** — Windows HIDI2C driver analysis, IPTS filter, special report IDs
