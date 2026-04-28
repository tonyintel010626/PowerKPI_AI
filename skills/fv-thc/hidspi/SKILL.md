---
name: fv-thc/hidspi
description: HIDSPI protocol spec, report types, ACPI DSM, ICR config, programmable opcodes, and validation points
---

> **Platform-specific implementation**: see [linux.md](linux.md) and [windows.md](windows.md)

## QuickSPI SwAS v1.0 - Concise DSM & Platform Notes

> **Reference Priority**: QuickSPI SwAS v1.0 is a **Priority 1 (PRIMARY)** reference, equal in authority to the THC IP HAS. Both are golden references for THC validation. If a conflict exists between the SwAS and HAS, the discrepancy must be escalated to the THC architecture team for resolution — neither document automatically overrides the other.

- QuickSPI DSM return/type conventions (per QuickSPI SwAS v1.0): Buffer types are used for function bitfields (returns list of functions supported). Buffer(1) is used for single-byte opcodes (e.g., Read/Write opcode). Integer types are used for numeric fields such as Input Report Header, Input Report Body offsets, Output Report Address and Flags. (QuickSPI SwAS v1.0)

- SPI connection speed: the OS/BIOS/driver is expected to round a requested SPI frequency down to the nearest supported hardware SPI frequency before programming THC registers. Example illustrative mappings from the SwAS: request 0 -> 7.8125 MHz; request 18 -> 17.85 MHz; request 30 -> 15.625 MHz; request >= 40 -> 31.3 MHz. Stick to SPI frequency semantics per ACPI/SwAS guidance. (QuickSPI SwAS v1.0)

- LimitPacketSize semantics (QuickSPI SwAS v1.0): the LimitPacketSize bitfield encodes the maximum SoC-specific packet length supported by the THC. Bit 0: 0 = No limitation; 1 = 64 Bytes. Drivers should honor this bit when sizing frames/PRD entries. (QuickSPI SwAS v1.0)

- Chip-select (CS) to clock (CLK) delay DSM parameter: supported on LNL and later platforms; reserved on MTL and prior platforms. If present in the platform _DSM, drivers should use the provided integer delay value to meet device timing expectations. (QuickSPI SwAS v1.0)

# THC HIDSPI Protocol Reference

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.


Complete HIDSPI protocol specification mapped to THC IP HAS constructs for FV test development and debug.

> **Source**: [HIDSPI Protocol Specification v1.0](https://www.microsoft.com/download/details.aspx?id=103325) (Microsoft, 47 pages)

## Protocol Overview
- **Half-duplex** SPI communication (not full-duplex)
- Supports Single/Dual/Quad SPI modes + DDR. In multi-SPI modes: opcode sent in single-SPI, rest in multi-SPI
- **Falling-edge triggered** GPIO interrupt line from device to host (pulled HIGH, active LOW)
- **Byte ordering**: Little-endian for all data **except ADDRESS fields** (big-endian, 3 bytes). Data shifted MSB first per byte
- **No CRC** — error detection relies on sync constant (`0x5A`) validation; invalid data triggers host-initiated device reset
- Dedicated CS# per device (active LOW)

## HIDSPI Device Descriptor (24 bytes, v1.0)

| Offset | Field | Size | Description |
|--------|-------|------|-------------|
| 0x00 | `wDeviceDescLength` | 2 | Total length (`0x0018` = 24) |
| 0x02 | `bcdVersion` | 2 | Protocol version (`0x0300` = spec v1.0) |
| 0x04 | `wReportDescLength` | 2 | Report descriptor length |
| 0x06 | `wMaxInputLength` | 2 | Maximum input report body length |
| 0x08 | `wMaxOutputLength` | 2 | Maximum output report body length |
| 0x0A | `wMaxFragmentLength` | 2 | Maximum fragment body size |
| 0x0C | `wVendorID` | 2 | Vendor ID (must be non-zero) |
| 0x0E | `wProductID` | 2 | Product ID |
| 0x10 | `wVersionID` | 2 | Device firmware version |
| 0x12 | `wFlags` | 2 | Bit 0: `NoOutputReportAck` |
| 0x14 | Reserved | 4 | Must be `0x00000000` |

> **⚠️ THC IP Legacy Descriptor (28 bytes)**: THC IP HAS documents a **28-byte** descriptor (bcdVersion=`0x0200`) with DWORD max lengths, `wReportDescRegister`, `wCommandRegister`. Check `bcdVersion` first to determine which layout to parse. BOM52 WACOM on NVL returns `0x0300` (24-byte format).

## HIDSPI Input Report Types (Device → Host)

| Type | Name | Description |
|------|------|-------------|
| `0x01` | Data | Touch/HID data (supports fragmentation) |
| `0x03` | Reset Response | Device acknowledges host-initiated reset |
| `0x04` | Command Response | Response to a host command |
| `0x05` | Get Feature Response | Response to GET_FEATURE |
| `0x07` | Device Descriptor | Device descriptor data |
| `0x08` | Report Descriptor | Report descriptor data |
| `0x09` | Set Feature Response | ACK of SET_FEATURE |
| `0x0A` | Set Output Report Response | ACK of OUTPUT_REPORT (unless `NoOutputReportAck`) |
| `0x0B` | Get Input Report Response | Response to GET_INPUT_REPORT |

## HIDSPI Output Report Types (Host → Device)

| Type | Name | Description |
|------|------|-------------|
| `0x01` | Device Descriptor Request | Request device descriptor |
| `0x02` | Report Descriptor Request | Request report descriptor |
| `0x03` | SET_FEATURE | Set a feature report value |
| `0x04` | GET_FEATURE | Request a feature report value |
| `0x05` | OUTPUT_REPORT | Send an output report |
| `0x06` | GET_INPUT_REPORT | Request a specific input report |
| `0x07` | Command | Send a command (SET_POWER, RESET) |

## Two-Phase Input Report Read

1. **Phase 1 — Header Read**: Host sends Read Approval (5 bytes: opcode `0x0B` + 3-byte address BE + `0xFF`) to Input Report Header Address. Returns 4-byte header:
   - Bits [3:0]: Version (must be `0x3`)
   - Bits [21:8]: Input Report Length (14-bit field, units of 4 bytes)
   - Bit 22: Last Fragment Flag
   - Bits [31:24]: Sync Constant (must be `0x5A`)
2. **Phase 2 — Body Read**: Host sends Read Approval to Input Report Body Address. Returns report body with Type(1) + ContentLength(2) + ContentID(1) + Content(n) + Padding(0-3).

### Kernel Struct Definitions (from `hid-over-spi.h`)

```c
/* Input Report Header (4 bytes, DWORD) */
struct input_report_header {
    u32 protocol_version : 4;  /* Must be 0x3 */
    u32 reserved0 : 4;
    u32 input_report_length : 14;  /* Length in 4-byte units */
    u32 last_fragment_flag : 1;
    u32 reserved1 : 1;
    u32 sync_const : 8;  /* Must be 0x5A — HIDSPI_INPUT_HEADER_SYNC_CONST */
};

/* Input Report Body Header (4 bytes) */
struct input_report_body {
    u8 input_report_type;   /* enum input_report_type */
    u16 content_length;     /* Payload size in bytes */
    u8 content_id;          /* Report ID */
    u8 content[];           /* Variable-length payload */
};

/* Output Report Header (4 bytes, DWORD) */
struct output_report_header {
    u8 output_report_type;  /* enum output_report_type */
    u16 content_length;     /* Payload size in bytes */
    u8 content_id;          /* Report ID */
};
```

### Key Constants (from kernel headers)

| Constant | Value | Purpose |
|----------|-------|---------|
| `HIDSPI_INPUT_HEADER_SYNC_CONST` | `0x5A` | Sync constant in input report header |
| `HIDSPI_INPUT_HEADER_VERSION` | `0x03` | Protocol version field |
| `HIDSPI_DEVICE_DESCRIPTOR_LENGTH` | `24` | v1.0 device descriptor size |
| `HIDSPI_OUTPUT_REPORT_HEADER_SIZE` | `4` | Output report header size |

#### THC QuickSPI limit_packet_size bitfield

The QuickSPI DSM `limit_packet_size`/`LimitPacketSize` semantics include a bitfield used by platform firmware to indicate packet-size constraints. Bit 0 (`LimitPacketSize`) semantics per SwAS:
- Bit 0 = 0 : No limitation (use SoC maximum capacity)
- Bit 0 = 1 : Limit packet size to 64 bytes

When Bit 0 = 0 the driver may use the SoC/platform defined maximum packet size (e.g., up to 2KB on some SoCs). When Bit 0 = 1 the driver must cap reads to 64 bytes. Documented here as authoritative SwAS guidance. (QuickSPI SwAS v1.0)

### HIDSPI Protocol Constants (linux `hid-over-spi.h`)

| Constant | Value | Notes |
|----------|-------|-------|
| `HIDSPI_INPUT_HEADER_SIZE` | 4 bytes | DWORD header returned by Phase-1 read |
| `HIDSPI_OUTPUT_HEADER_SIZE` | 8 bytes | Output header size for TXDMA/PIO writes |
| `HIDSPI_INPUT_BODY_HEADER_SIZE` | 4 bytes | Body header: Type(1) + Length(2) + ID(1) |
| `HIDSPI_SUPPORTED_VERSION` | `0x0300` | Protocol version v3.0 (bcd) |
| `HIDSPI_DEVICE_DESCRIPTOR_LENGTH` | 24 bytes | v1.0 device descriptor length (matches line 122; 30 bytes is HIDI2C, not HIDSPI)
| `HIDSPI_MIN_INPUT_REPORT_SIZE` | 8 bytes | `HIDSPI_INPUT_HEADER_SIZE + HIDSPI_INPUT_BODY_HEADER_SIZE`

> **Validation point**: If `sync_const != 0x5A`, the header is invalid and the frame should be discarded. The kernel `quickspi-protocol.c` checks this value during `quickspi_handle_input_data()`.

## HIDSPI Commands

| Command | Content ID | Content | Device Response |
|---------|-----------|---------|-----------------|
| SET_POWER ON | `0x01` | `0x01` | Device will acknowledge but Linux `SET_POWER(ON)` is fire-and-forget (no synchronous wait) — Windows performs synchronous gated wait |
| SET_POWER SLEEP | `0x01` | `0x02` | **No** |
| SET_POWER OFF | `0x01` | `0x03` | **No** |

## Fragmentation
- **Only Data type (`0x01`)** supports fragmentation
- Device asserts interrupt **per fragment**
- **1-second inter-fragment deadline**
- First fragment has Type/ContentLength/ContentID header; subsequent are content-only
- Padding (to 4-byte alignment) only on last fragment

## HIDSPI Power States

| State | Value | ACPI Map | Entry | Device Response |
|-------|-------|----------|-------|-----------------|
| ON | `0x01` | D0 | SET_POWER ON | Yes |
| SLEEP | `0x02` | D2 | SET_POWER SLEEP | No |
| OFF | `0x03` | D3 | SET_POWER OFF | No |

- **OFF → ON**: Via **Host Reset only** (toggle reset line LOW ≥ 10ms)
- **No direct SLEEP ↔ OFF transition**

## HIDSPI ACPI Configuration

- **_CID**: `PNP0C51`

### Three ACPI DSM GUIDs (Linux Kernel Implementation)

The Linux driver uses **three** distinct ACPI DSM GUIDs — not just the HIDSPI spec GUID:

| GUID | Name | Rev | Functions |
|------|------|-----|-----------|
| `{6E2AC436-0FCF-41AF-A265-B32A220DCFAB}` | **HIDSPI DSM** | 2 | input_hdr_addr, input_bdy_addr, output_addr, read_opcode(BUFFER), write_opcode(BUFFER), io_mode |
| `{300D35B7-AC20-413E-8E9C-92E4DAFD0AFE}` | **QuickSPI DSM** | 2 | connection_speed, limit_packet_size, performance_limit |
| `{84005682-5B71-41A4-8D66-8130F787A138}` | **Platform DSM** | 2 | active_ltr_us, lp_ltr_us |

> **Note**: All 3 GUIDs use revision 2, but the Windows THCBase source defines separate revision constants per GUID group (`ACPI_DSM_HIDSPI_REVISION = 2` for the HIDSPI DSM; the THC and Platform DSMs pass revision 2 via their Arg1 parameter without a shared `#define`). The QuickSPI driver uses `ACPI_QUICKSPI_REVISION_NUM = 2` for all three. The QuickI2C driver uses `QUICKI2C_ACPI_REVISION_NUM = 1` for its I2C HID DSM and Platform DSM.

#### HIDSPI DSM Functions (Primary)

| Function | Returns | Description |
|----------|---------|-------------|
| 0 | Bitfield | Supported functions bitmask |
| 1 | Address | Input Report Header Address |
| 2 | Address | Input Report Body Address |
| 3 | Address | Output Report Address |
| 4 | Opcode | Read OpCode (`0x0B` single, `0xBB` dual, `0xEB` quad) — returned as BUFFER |
| 5 | Opcode | Write OpCode (`0x02` single, `0xB2` dual, `0xE2` quad) — returned as BUFFER |
| 6 | Flags | IO mode flags (see below) |

#### IO Mode Flag Parsing (DSM Function 6)

| Bit(s) | Field | Description |
|--------|-------|-------------|
| 13 | `SPI_WRITE_IO_MODE` | If set, write uses different IO mode than read |
| [15:14] | `SPI_IO_MODE_OPCODE` | Multi-SPI mode: 0=Single, 1=Dual, 2=Quad |

Both read and write opcodes share the `SPI_IO_MODE_OPCODE` field via `FIELD_GET`.

#### QuickSPI DSM Functions

| Function | Field | Description |
|----------|-------|-------------|
| 1 | `connection_speed` | SPI clock speed in Hz |
| 2 | `limit_packet_size` | Limits maximum read packet size. DSM return value semantics: **0 = no limit** (use maximum SoC capacity, e.g. 2KB on LNL+), **non-zero = byte count limit** (driver uses this as the max read length). ACPI encoding: `0` = max capacity, `1` = 64B minimum (`DEFAULT_MIN=4`). BIOS sets based on device capabilities and SI validation results. |
| 3 | `performance_limit` | Post-TXDMA delay = value × 10µs. Specifies delay between write-end and read-begin in **10µs multiples**. Applied as `udelay(perf_limit * 10)` in kernel. Value 0 = no delay. |

> **DSM type annotations (SwAS clarification)**: Several QuickSPI DSM functions return typed values that drivers must interpret strictly. The `limit_packet_size` field may be returned as an Integer (0 = no limit, non-zero = max bytes) or as a Buffer containing a bitfield of capabilities in some platform variants. Read/Write opcodes (DSM functions 4 and 5) are returned as Buffer(1) encoding the opcode byte. Input/Output report addresses (DSM functions 1-3) are returned as Integer address values. Where the DSM returns Buffer vs Integer, prefer the documented type per GUID: HIDSPI DSM returns opcodes as Buffer, addresses as Integer, and flags as Integer/bitfield. (QuickSPI SwAS v1.0)

#### Platform DSM Functions

| Function | Field | Description |
|----------|-------|-------------|
| 1 | `active_ltr_us` | Active LTR value in microseconds |
| 2 | `lp_ltr_us` | Low-power LTR value in microseconds |

## EDS Size Constants (Windows HIDSPI — eds.h)

> **Source**: Windows HIDSPI driver `eds.h` — Phase 6b deep read

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_TOUCH_DATA_PACKET_SIZE` | 128 KB | Maximum single packet size |
| `MAX_TOUCH_DATA_FRAME_SIZE` | 256 KB | Maximum frame size (multi-packet) |
| `MAX_WRITE_DATA_SIZE` | 4 KB | Maximum write data payload |
| `MAX_REPORT_DESCRIPTOR_SIZE` | 8 KB | Maximum report descriptor length |
| `MAX_RESET_TIMEOUT` | 10,000 ms (10s) | Maximum reset timeout |
| `DEFAULT_RESET_TIMEOUT` | 3,000 ms (3s) | Default reset timeout |
| `DEFAULT_GET_FEATURE_CANCEL_TIMEOUT` | 3,000 ms (3s) | Default GET_FEATURE cancel timeout (registry-configurable via `GetFeatureCancelTimeout` key) |
| `TIC_RESET_DELAY_US` | 500,000 µs (500ms) | TIC reset delay |
| `CONFIG_CHANGE_INTERRUPT_TIMEOUT` | 50 ms | Config change interrupt timeout |

> **Note (SwAS clarification)**: QuickSPI SwAS v1.0 mandates that a host-initiated RESET (OFF → ON) must assert the device reset line LOW for a minimum of 10 ms (host reset hold >= 10 ms). The EDS/driver documented default TIC reset delay (TIC_RESET_DELAY_US = 500,000 µs = 500 ms) and the Linux kernel's conservative ACK/wait timeouts (for example, QUICKSPI_ACK_WAIT_TIMEOUT = 5 s in kernel `quickspi-protocol.c`) are implementation defaults intended to provide additional robustness.

- Treat 10 ms as the protocol-specified minimum assertion time (authoritative for SwAS compliance tests).
- Treat TIC_RESET_DELAY_US (500 ms) and kernel 5 s ACK timeouts as conservative implementation defaults; drivers may keep longer defaults but must never use values shorter than the SwAS-specified minimum.
- Make TIC reset hold-time configurable where feasible (via ACPI `_DSM`, platform registry, or driver parameter) and document the configuration key so tests can validate both the SwAS minimum and the deployed default.


### SPI Frequency Capability Enum (from EDS)

| Value | Max SPI Frequency |
|-------|-------------------|
| 0 | 17 MHz |
| 1 | 30 MHz |
| 2 | 50 MHz |

### Sensor State Enum (from EDS)

| Value | State | Description |
|-------|-------|-------------|
| 0 | `None` | No state |
| 1 | `Ready` | Sensor ready |
| 2 | `Configuring` | Sensor being configured |
| 3 | `Enabled` | Sensor enabled |
| 4 | `Sensing` | Actively sensing touch |
| 5 | `Resetting` | Sensor resetting |

### HIDSPI Fatal Error Bit Definitions (from Windows Hal.cpp)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | Bus Turnaround | SPI bus turnaround error |
| 1 | Response Timeout | Device response timeout |
| 2 | Intra Packet Timeout | Timeout within a packet |
| 3 | Invalid Response | Invalid response from device |
| 4 | HS RX Timeout | High-speed RX timeout |
| 5 | TIC Init Errors | TIC initialization errors |

> **Validation point**: When `FATAL_ERR` bit is set in interrupt status, read the error register and decode bits 0-5 to identify the specific fatal error type.

### Write DMA Errors and Fatal Errors — Unused (from QuickSPI SwAS v1.0)

> **⚠️ SwAS clarification**: Write DMA errors and Fatal Errors are explicitly listed as **"Unused-errors"** in the QuickSPI SwAS v1.0 — they are not implemented by SW or HW in current platforms. The fatal error bit definitions above are from the Windows HAL layer and represent register fields, but the SwAS indicates these error paths are not actively monitored or handled by the production driver flow. All error recovery is driven by read-path errors (Invalid PRD, Frame Babble, Short Packet, PRD Overrun, THC Buffer Overrun, PIO Error, Write Length Error).

## Programmable SPI Opcodes (Gen2.0+)

| IO Mode | Default Read | Default Write |
|---------|-------------|--------------|
| Single | `0x0B` | `0x02` |
| Dual | `0xBB` | `0xB2` |
| Quad | `0xEB` | `0xE2` |
| Reserved | `0xFB` | `0xF2` |

Dummy clocks (`SPI_TRDC`): Only value 3 = **8 dummy clocks (DEFAULT)** is supported. Values 0-2 "Not Supported".

## Frame Type Routing Control (HIDSPI)

HIDSPI uses `THC_M_PRT_DEVINT_CFG_1` frame type fields to route incoming frames to DMA channels:

| Register Field | Effect |
|---------------|--------|
| `FTYPE_IGNORE = 0` | Normal mode — INT_CAUSE field determines RXDMA1 vs RXDMA2 routing |
| `FTYPE_IGNORE = 1` alone | Ignore frame type — all frames go to RXDMA1 |
| `FTYPE_IGNORE = 1` AND `FTYPE_VAL = 1` | **Frame type routing bypassed entirely** — all frames go to RXDMA2 |

The Linux HIDSPI driver sets **both** `FTYPE_IGNORE` and `FTYPE_VAL` during `thc_spi_configure()`, meaning:
- ALL SPI frames are routed to **RXDMA2** (the HID input channel)
- RXDMA1 receives **nothing** in normal HIDSPI operation
- This is because HIDSPI protocol handles frame type at the software layer (body type field), not hardware routing

> **Validation point**: In HIDSPI mode, RXDMA1 should never receive frames. If RXDMA1 gets data, it indicates incorrect `FTYPE_IGNORE`/`FTYPE_VAL` configuration.

## Timeouts and Error Handling

| Timeout | Duration |
|---------|----------|
| Reset Response | 1 second (spec); **5 seconds** (kernel `QUICKSPI_ACK_WAIT_TIMEOUT`) |
| Descriptor Response | 1 second (spec); **5 seconds** (kernel) |
| Output Report Response | 1 second (spec); **5 seconds** (kernel) |
| Inter-Fragment | 1 second |
| Host-Initiated Reset | ≥ 10 ms (reset LOW hold) |
| Power Transition | 1 second |

> **⚠️ Spec vs Implementation**: The HIDSPI protocol spec defines 1-second timeouts, but the Linux kernel `quickspi-protocol.c` uses `QUICKSPI_ACK_WAIT_TIMEOUT = 5` seconds for all `wait_event` timeouts. FV tests should validate both values.

## THC HAS Cross-Reference: HIDSPI ↔ THC Implementation

| HIDSPI Operation | THC Register / Mechanism |
|-----------------|-------------------------|
| Device Descriptor Read | PIO opcode `0x4` → address from ACPI `_DSM` |
| Report Descriptor Read | PIO opcode `0x4` → `wReportDescLength` bytes |
| Header Read (Phase 1) | PIO opcode `0x4` or RXDMA to Header Address (`_DSM` Fn 1) |
| Body Read (Phase 2) | PIO opcode `0x4` or RXDMA to Body Address (`_DSM` Fn 2) |
| INT_CAUSE routing | `devint_cfg_1` / `devint_cfg_2` filter by frame type |
| Output Report Write | PIO opcode `0x8` or TXDMA to Output Address (`_DSM` Fn 3) |
| SET_POWER OFF → D3 | `thc_cfg_pmd_pmcsrbse_pmcsr.pwrst` = 3 |
| SET_POWER SLEEP → D0i2 | `thc_sb_pm_ctrl.ts_d0i2_mode`, `thc_cfg_pce.hae` |
| SPI Read/Write Opcode | `thc_m_prt_spi_ioc_*` registers |
| SPI PIO Opcodes (PIO) | PIO_OP_SPI_RD=`0x4`, PIO_OP_SPI_WR=`0x6`, PIO_OP_SPI_BULK_WR=`0x8` |
| THC_M_PRT_SPI_CFG Fields | SPI_IO_MODE, CLK_DIV, HALF_CLK_DIV_EN (Gen4.1+), SPI_CSA_CK_DELAY_VAL |
| ICRRD / DMA Read Opcode Register | `THC_M_PRT_SPI_ICRRD_OPCODE` — configures both ICR read opcode and DMA read opcode |
| Write Opcode Register | `THC_M_PRT_SPI_WR_OPCODE` — PIO write opcode (single) |
| Bulk Write Opcode Register | `THC_M_PRT_SPI_BULK_WR_OPCODE` — bulk write opcode for large transfers |
| SPI IO Mode | `thc_m_prt_spi_cfg.spi_io_mode` |
| SPI Clock | `thc_m_prt_spi_cfg.spi_frequency` (divider) |
| Device Reset GPIO | Platform-specific: `xxgpp_e_16` (THC0), `xxgpp_f_16` (THC1) |

## SPI Frequency Divider Table

The kernel derives SPI clock frequencies from a **125 MHz input clock** using a 3-bit divider field plus a `LOW_FREQ_EN` flag. The threshold for `LOW_FREQ_EN` is **17,857,100 Hz** (125MHz ÷ 7):

| Divider Code | `LOW_FREQ_EN` | Output Freq | Calculation | Kernel Enum |
|-------------|--------------|------------|-------------|-------------|
| `THC_SPI_FRQ_DIV_2` | 1 | **7.81 MHz** | 125M ÷ 16 | `spi_freq_val` table |
| `THC_SPI_FRQ_DIV_1` | 1 | **15.63 MHz** | 125M ÷ 8 | `spi_freq_val` table |
| `THC_SPI_FRQ_DIV_7` | 1 | **17.86 MHz** | 125M ÷ 7 | Threshold boundary |
| `THC_SPI_FRQ_DIV_6` | 0 | **20.83 MHz** | 125M ÷ 6 | `spi_freq_val` table |
| `THC_SPI_FRQ_DIV_5` | 0 | **25.00 MHz** | 125M ÷ 5 | `spi_freq_val` table |
| `THC_SPI_FRQ_DIV_4` | 0 | **31.25 MHz** | 125M ÷ 4 | `spi_freq_val` table |
| `THC_SPI_FRQ_DIV_3` | 0 | **41.67 MHz** | 125M ÷ 3 | `spi_freq_val` table |

The kernel `thc_spi_configure()` algorithm:
1. Walk the `spi_freq_val[]` array from lowest to highest frequency
2. Select the largest entry where `entry.freq <= requested_connection_speed`
3. If `selected_freq <= 17,857,100` → set `SPI_LOW_FREQ_EN = 1`
4. Program `SPI_CFG.spi_frequency` with the divider code

> **Source clock**: 125 MHz SSC (TGL/LKF/LNL+). ADP/MTL uses 125 MHz for SPI reference clock — divider results use 125MHz base.

### SPI Frequency ACPI Encoding (BIOS/ASL — from QuickSPI SwAS v1.0)

> **⚠️ Distinct from kernel divider table above.** The ACPI/BIOS layer uses a **separate 3-bit encoding** (bits 0-2 of the SPI frequency DSM field) to communicate desired SPI frequency from BIOS to driver. This is NOT the same as the kernel `spi_freq_val[]` divider codes — the driver translates the ACPI value to the appropriate HW divider at runtime.

| ACPI Bits [2:0] | Frequency | Notes |
|-----------------|-----------|-------|
| `011` | **40 MHz** | Default (platform SI max) |
| `100` | 30 MHz | |
| `101` | 24 MHz | |
| `110` | 20 MHz | |
| `111` | 17 MHz | Lowest supported |

> **Source**: QuickSPI SwAS v1.0 (Priority 1 reference). The driver reads this ACPI value via the QuickSPI DSM `connection_speed` function and selects the closest HW divider from the kernel `spi_freq_val[]` table. Validation should verify the ACPI→HW divider mapping produces the expected frequency on the bus.

**OS/BIOS rounding behavior (SwAS expectation)**: The OS/BIOS is expected to round the requested/ACPI-declared SPI connection speed down to the nearest supported SPI frequency before programming the THC divider registers and the driver/kernel will program that selected HW frequency. Example mappings from request→selected HW frequency (illustrative per QuickSPI SwAS v1.0): 0 → 7.8125 MHz; 18 → 17.85 MHz; 30 → 15.625 MHz; ≥40 → 31.3 MHz. (QuickSPI SwAS v1.0)

## LNL+ SPI Clock DCG (Half-Cycle Divider)

Starting with LNL, THC supports a half-cycle fractional clock divider for more precise SPI clock generation.

### Features
- **Half-cycle fractional divider**: Allows non-integer division ratios
- **Programmable duty cycle**: ZBBed (Zero-Bug-Bounce) feature
- **CS-to-CK delay**: Programmable delay between chip select assertion and first clock edge
- **RX clock selection**: Configurable receive clock source

### Programming
The DCG divider extends the basic 3-bit divider from pre-LNL platforms:
- Pre-LNL: 3-bit divider (001-111) with SPI_LOW_FREQ_EN (0/1) for two frequency ranges
- LNL+: Half-cycle divider adds finer granularity within each range

### Source Clock Reference
| Platform | Source Clock |
|----------|-------------|
| TGL/LKF | 125MHz SSC |
 | ADP/MTL | 125MHz |
| LNL+ | 125MHz SSC (with DCG half-divider) |

### Max Platform Frequency
- SI-limited: **40MHz** maximum on platform
- Validation should sweep frequencies from minimum to 40MHz

## SPI Loopback Clocks

### Purpose
THC uses a dummy pad per SPI port to implement loopback clock compensation. This compensates for on-chip routing delay between the THC IP and the SPI pads.

### Mechanism
- Each port has a dedicated loopback clock path
- The loopback measures actual pad-to-pad delay
- THC adjusts internal sampling timing based on loopback measurement
- Critical for high-frequency SPI operation (>20MHz)

### Validation Impact
- Loopback clock must be functional for reliable data capture
- If loopback path is broken, SPI read data may be corrupted at higher frequencies
- DFT mode can bypass loopback for test purposes

## SPI DMA Opcodes

### ICR (Input Cause Register) Format
The ICR provides a compact status word indicating device interrupt causes and protocol status.

Bit fields (little-endian DWORD):
- Bit 0: INT_CAUSE (device has data)
- Bits 1-2: Reserved
- Bit 3: RESET_RESPONSE (device completed reset)
- Bits 4-7: PROTOCOL_ERROR_CODE
- Bits 8-15: VERSION_NUMBER
- Bits 16-31: Reserved

### ICR Read Opcodes (Input Cause Register)
| IO Mode | Opcode | Description |
|---------|--------|-------------|
| Single | 0x0B | Single-IO ICR read |
| Dual | 0xBB | Dual-IO ICR read |
| Quad | 0xEB | Quad-IO ICR read |
| Quad (alt) | 0xFB | Quad-IO ICR read (alternate) |

### DMA Read Opcodes (Bulk Data)
| IO Mode | Opcode | Description |
|---------|--------|-------------|
| Single | 0x0B | Single-IO DMA read |
| Dual | 0xBB | Dual-IO DMA read |
| Quad | 0xEB | Quad-IO DMA read |
| Quad (alt) | 0xFB | Quad-IO DMA read (alternate) |

### Dummy Clock Cycles
| Configuration | Dummy Clocks |
|--------------|-------------|
| Minimum | 0 |
| Typical Single | 2 |
| Typical Dual | 4 |
| Typical Quad | 8 |

### SPI Instruction Mapping
| Operation | Opcode | Description |
|-----------|--------|-------------|
| PIO Register Read | 0x4 | Register read via PIO (PIO_OP_SPI_RD); `0x2` is legacy Gen2 only |
| PIO Register Write | 0x6 | Register write via PIO (PIO_OP_SPI_WR) |
| Bulk Read | 0x4 | Bulk data read (same opcode as PIO read) |
| Bulk Write | 0x8 | Bulk data write (PIO_OP_SPI_BULK_WR) |

## SPI Timing Requirements (from HAS)

### Critical Timings
| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| CS# Setup Time | 30 | - | - | ns |
| CS# Hold Time | 30 | - | - | ns |
| INT to CS# Assert | - | - | 400 | ns |
| Frame-end to MSI | - | - | 800 | ns |

### Practical Timing at Common Frequencies (Simics Wiki Reference)

Concrete timing values at commonly-used SPI frequencies for validation reference:

| Frequency | Clock Period | Half-Period (Setup/Hold ref) | Divider | Notes |
|-----------|-------------|------------------------------|---------|-------|
| **42.67 MHz** | ~23.4 ns | ~11.7 ns | 125MHz ÷ ~2.93 | Near max platform SI — requires half-divider (Gen4.1+). CS# setup/hold (30 ns min) requires ~1.3 clock cycles minimum |
| **32 MHz** | ~31.3 ns | ~15.6 ns | 125MHz ÷ ~3.91 | Common mid-range. CS# 30 ns ≈ 1 clock cycle |
| **17 MHz** | ~58.8 ns | ~29.4 ns | 125MHz ÷ 7 | LOW_FREQ_EN threshold boundary. Widely validated |
| **7.81 MHz** | ~128 ns | ~64 ns | 125MHz ÷ 16 | Minimum supported. Most timing margin |

> **Validation note**: At 42.67 MHz, CS# setup/hold times (30 ns min from HAS) are less than 2 clock periods — verify with oscilloscope that actual setup/hold meets spec. At 32 MHz and below, timing margins are comfortable.

### SPI Performance Goals
| Metric | Value |
|--------|-------|
| SPI Read Bandwidth (Gen1) | 12 MBps per port |
| SPI Read Bandwidth (Gen2+) | 20 MBps per port |
| Max Ports | 2 |

## SPI Bus Prerequisites (from HAS)

> **⚠️ HAS RULE**: Driver must check `SPI_IO_RDY` bit is HIGH for all ports before ANY bus operation. This reflects boot-time RCOMP completion via `gpio_thc_rcomp_done_x` signal.
> **⚠️ HAS RULE**: `THC_M_PRT_SPI_CFG` cannot be updated while DMA or PIO is running.
> **⚠️ Bus Voltage**: THC SPI bus operates at **1.8V** signaling level. INT# line must also be 1.8V. Incorrect voltage levels (e.g., 3.3V) will cause communication failures or GPIO damage. Verify voltage rails during board bring-up.

## Frame and Microframe Rules (from HAS)
- Microframe size must be **multiple of 16 bytes** except for the last microframe in a frame
- **No interrupts allowed** between packets in the middle of a microframe
- If microframe > MPS, all payloads must be max packet size except the last

## SPI Performance Goals (from HAS)

| Parameter | Value |
|-----------|-------|
| SPI Read/Write throughput | 12 MBps × 2 ports (20 MBps Gen2+) |
| RXDMA: INT → first CS# assert | **400 ns** |
| RXDMA: Inter-packet gap | **400 ns** |
| RXDMA: Frame end → MSI | **800 ns** |
| TXDMA: Start → first CS# | **500 ns** |
| PIO: Go → CS# assert | **300 ns** |
| PIO: CS# deassert → TSSDONE | **200 ns** |
| Source clock requirement | 125 MHz SSC reference |

> Performance goals assume non-concurrent, PRD prefetch enabled, not in PG, 30MHz SPI, >100MHz IOSF.

## HIDSPI Validation Points
- SPI clock frequency and polarity (CPOL/CPHA) configuration
- Chip-select timing (setup, hold, inter-frame gap)
- Opcode verification: all IO modes (Single/Dual/Quad) with correct read/write opcodes
- Dummy clock validation: only 8 clocks supported
- Descriptor version detection: `bcdVersion` `0x0300` (24-byte) vs `0x0200` (28-byte)
- Two-phase input read: Header sync constant `0x5A`, version bits `0x3`, Last Fragment Flag
- Report type validation: all input/output report types
- Fragmentation: multi-fragment with inter-fragment deadline (1s), interrupt-per-fragment
- SET_POWER: ON (responds), SLEEP (no response), OFF (no response); OFF→ON requires HW reset
 - SET_POWER: ON (device may acknowledge). Note: Linux `SET_POWER(ON)` is fire-and-forget (kernel returns immediately after PIO/TXDMA write); Windows driver performs a synchronous gated wait for SET_POWER(ON) response using `bAwaitingSendSetPowerOnResponse` semantics.
- ACPI _DSM: UUID `6E2AC436-...`, Functions 1-6 return correct addresses/opcodes
- NoOutputReportAck flag: if `wFlags` bit 0 set, device does NOT send type `0x0A`
- Sonora SPI injection: 8/17/25/42 MHz in Single/Dual/Quad IO modes

## Interrupt Handling Flow

- GPIO interrupt from device → THC samples SPI bus to read ICR (PIO ICR read)
- Driver checks `INT_CAUSE` bit in ICR; if set, schedule RXDMA to read full report body
- RXDMA reads full report into PRD ring buffer; on completion, MSI/MSI-X (or legacy INTx) interrupts host CPU
- Host driver consumes DMA ring (PRD-based) and dispatches by input report type
- Error/exception paths use PIO read for diagnostics and may trigger `try_recover()`

### ISR/DPC Interrupt Handling Details (from QuickSPI SwAS v1.0)

**ISR behavior** (per-vector masking):
- ISR masks all interrupt sources via **Global IE bit** (single write)
- ISR queues DPC for deferred processing — minimal work in ISR context
- Each MSI vector has independent masking capability

**DPC behavior**:
- DPC reads interrupt status register to determine cause (error/EOF/NONDMA)
- Processes pending data, checks error conditions
- **⚠️ Race condition prevention**: DPC acquires **ISR lock** (WDF Interrupt Lock) before re-enabling IE bits — this prevents a race condition where an ISR fires between DPC status read and IE re-enable
- After processing, DPC unmasks interrupts by restoring Global IE bit

> ⚠️ **SPI vs I2C Interrupt Masking**: The SPI driver uses **per-vector masking** via `ChangeInterruptState()` pattern (~47 call sites) and does NOT toggle `GBL_INT_EN` in the ISR. The I2C driver toggles `GBL_INT_EN` in ISR (disable) and DPC (re-enable). SPI also does NOT perform the report descriptor last-byte `0xC0` validation that the I2C driver performs. See `driver/SKILL.md` for detailed comparison.

### Interrupt Quiesce Scenarios (from QuickSPI SwAS v1.0)

Four specific scenarios require quiescing device interrupts:

| # | Scenario | Description |
|---|----------|-------------|
| 1 | **During reset** | Before TIC is powered up — device may assert stale interrupts |
| 2 | **Buffer threshold** | When free RXDMA2 buffers drop below threshold (8 of 16) — quiesce to let consumption catch up |
| 3 | **D0Exit** | During power state exit — quiesce before DMA teardown |
| 4 | **NOT within ISR/DPC** | Quiesce must NOT be called from ISR or DPC context (deadlock risk) |

> **Validation point**: Verify that quiesce is correctly applied in all 4 scenarios and never called from interrupt context.

## PCI Device IDs (HIDSPI — QuickSPI)

> **Source**: Linux kernel `quickspi-dev.h` and `pci-quickspi.c` (kernel 6.18+)

| Platform | THC0 Device ID | THC1 Device ID | Notes |
|----------|---------------|---------------|-------|
| MTL | `0x7E49` | `0x7E4B` | Gen3.0 |
| ARL | `0x7749` | `0x774B` | Gen3.0 |
| LNL | `0xA849` | `0xA84B` | Gen4.0 |
| PTL-H (PTL-H4Xe, PCD-H) | `0xE349` | `0xE34B` | Gen4.1 |
| PTL-U & PTL-P (PTL-H12Xe, PCD-P) | `0xE449` | `0xE44B` | Gen4.1 |
| WCL | `0x4D49` | `0x4D4B` | Gen4.1 |
| NVL (PCD-H) | `0xD349` | `0xD34B` | Gen4.2, Co-De Sign verified |
| RZL | `0x6C49` | `0x6C4B` | Gen4.2, Co-De Sign verified |
| TTL | `0x9335` | `0x933A` | Gen4.2, Co-De Sign verified ⚠️ Non-standard pattern |

> **Convention**: THC0 ends in `x9`, THC1 ends in `xB` (odd/odd+2 pattern).
> **Exception**: TTL breaks this pattern — THC0=`0x9335`, THC1=`0x933A` (non-contiguous).
> **NVL/RZL/TTL**: Not yet in upstream Linux kernel as of v6.20. DIDs from Co-De Sign platform specs.

## Packet Size Configuration (Per-Platform)

Max packet size (MPS) varies by platform and affects SPI DMA transfer granularity:

| Platform | `max_packet_size` | Actual Size | Notes |
|----------|-------------------|------------|-------|
| Default (fallback) | 4 | 64 bytes | `DEFAULT_MIN_PACKET_SIZE` |
| MTL, ARL | 128 | 2 KB | `MTL_MAX_PACKET_SIZE` |
| LNL, PTL, WCL | 256 | 4 KB | `LNL_MAX_PACKET_SIZE` |

- Packet size value is multiplied by 16 to get byte count (e.g., 256 × 16 = 4096)
- Set via `THC_M_PRT_SPI_CFG.spi_rd_mps` and `spi_wr_mps`
- MPS is aligned to 4KB boundary in DMA: `ALIGN(size, SZ_4K)`

> **WCL note**: WCL QuickSPI uses `&ptl` driver_data, which gives it the LNL max packet size of 256 (4 KB).

## CS# Assertion Delay

SPI Chip Select assertion timing control:
- **Register**: `THC_M_PRT_SPI_CFG` — `SPI_CSA_CK_DELAY_EN` flag + `SPI_CSA_CK_DELAY_VAL`
- **Default value**: 4 clock cycles delay after CS# assertion before first clock edge
- **Purpose**: Ensures touch device has time to prepare after CS# goes active
- Applied by driver during `thc_spi_configure()` if platform data provides delay value

> **CS-to-CLK DSM param (platform note)**: QuickSPI SwAS v1.0 documents an ACPI/DSM-provided Chip-Select-to-Clock delay parameter. This value is supported only on LNL+ platforms and is reserved (must be ignored) on MTL and prior platforms. Drivers should only apply the CS-to-CLK delay when platform or DSM indicates LNL+ capability. (QuickSPI SwAS v1.0)

## Descriptor Retrieval Methods

| Descriptor | Retrieval Method | Notes |
|------------|-----------------|-------|
| Device Descriptor (24/28B) | **PIO** (opcode `0x02`/`0x04`) | Small payload, synchronous |
| Report Descriptor (variable) | **TXDMA** (write request) → **RXDMA** (async response) | Large payload, DMA path |

- Device descriptor is read during the probe sequence after device reset and DMA initialization (modern kernel flow: reset → DMA init → descriptor parse)
- Report descriptor request is sent via TXDMA, response arrives asynchronously on RXDMA2

## Cross-Platform Comparison: Linux vs Windows HIDSPI

| Aspect | Linux (QuickSPI) | Windows (HIDSPI) |
|--------|------------------|-------------------|
| SET_POWER(ON) | Fire-and-forget (no wait) | Synchronous gated wait (`bAwaitingSendSetPowerOnResponse`) |
| SPI_LOW_FREQ_EN threshold | 17,857,100 Hz (125MHz ÷ 7) | 17 MHz |
| GetFeature timeout | 5 seconds | 3 seconds |
| Auto-suspend delay | 5000 ms | Own doze timer |
| SPI bus locking | `thc_bus_lock` mutex | NO-OP stubs (BSOD WA) |
| TXDMA completion | Interrupt-driven | Polling (100µs × 500ms, HSD 14016760177) |
| Freeze/Thaw/Poweroff/Restore | Implemented (hibernate support) | No callbacks |
| ACPI _RST | ACPI `_RST` + THC DEVRST register | ACPI `_RST` only (DEVRST commented out) |
| WCL driver_data | Uses `&ptl` (LNL max packet size) | N/A |
| Wacom opcode override | Not implemented | `0x0C` special read opcode |
| Filter driver (IPTS) | N/A | 9 stubs, GUID_THC_INTERFACE |

## SPI Clock Sweep Validation (test methodology)

- Sweep SPI clock from minimum supported (platform-dependent, e.g., ~1 MHz) up through platform max (SI-limited ≈ 40 MHz)
- At each frequency step, validate data integrity (report CRC/sync, content correctness), check for retries/timeouts
- Validate CS#/clock timing, check for correct handling of dummy clocks and half-divider behavior on Gen4.1+
- For Gen4.1+ platforms, verify half-divider produces expected intermediate frequencies per formula: SPI_CLK = 125MHz / (2 * (divider + 0.5)) when HALF_CLK_DIV_EN set
- **CS# oscilloscope trigger methodology**: Use CS# (active-LOW) falling edge as the oscilloscope trigger source for capturing SPI transactions. This provides a clean, deterministic trigger point that marks the start of every SPI frame. Measure CS#-to-first-CLK-edge delay against the `SPI_CSA_CK_DELAY_VAL` programmed value. Verify CS# setup/hold times (≥30 ns per HAS) at each frequency step. For intermittent failures, use CS# + INT# dual-trigger to capture the device interrupt → host response latency chain

> **Simics HIDSPI model** (TEP architecture, thc_vdm class, SPI BIOS values, mouse-to-touch, SPARK history, validation points) → See **`fv-thc/simics`** sub-skill ([models.md](../simics/models.md#tep-touch-endpoint--spi-mode))

## See Also
- **`fv-thc/registers`** — SPI_CFG register details, PIO sequence registers
- **`fv-thc/dma`** — SPI DMA opcodes, ICR read flow, bulk data transfer
- **`fv-thc/platform`** — Per-platform SPI clock sources, frequency limits, BOM devices
- **`fv-thc/power`** — SPI power state transitions (SET_POWER ON/OFF), LTR during active SPI, D3 save/restore of SPI registers
- **`fv-thc/debug`** — SPI-specific failure signatures, protocol-level debug
- **`fv-thc/simics`** — Simics HIDSPI model (TEP), transactors, SPI BIOS config, touch injection, debug
- **`fv-thc/driver`** — Windows HIDSPI driver internals, ACPI DSM configuration
- **`fv-thc/hidi2c`** — HIDI2C protocol (both use 5000ms auto-suspend)
- **`fv-thc/wot`** — Wake-on-Touch over SPI: UGD interrupt routing, GPIO wake config, ACPI _DSM WoT enable
- **Reference**: `fv-thc/docs/thc_test_coverage_matrix.md` — SPI test coverage (Section 3)
- **Reference**: `fv-thc/docs/thc_hidspi_hidi2c_kernel_study.md` — Complete kernel source analysis
- **Platform-specific**: [linux.md](linux.md) — Linux QuickSPI driver state machine, probe/remove, suspend/resume
- **Platform-specific**: [windows.md](windows.md) — Windows HIDSPI driver architecture, HidSpiCx callbacks, filter driver
- **Automation**: [Dragon Framework](https://github.com/intel-restricted/frameworks.validation.wideband-io.flows) — Intel-internal wideband-IO validation automation framework used for THC SPI/I2C test flow orchestration
