---
name: fv-thc/hidi2c
description: HIDI2C protocol spec, I2C class requests, ACPI DSM, Synopsys sub-IP, I2C MPS workaround, and validation points
---

> **Platform-specific implementation**: see [linux.md](linux.md) and [windows.md](windows.md)

> **Reference Priority**: QuickI2C SwAS v1.0 is a **Priority 1 (PRIMARY)** reference, same level as the THC IP HAS. Both are authoritative for their respective domains (SwAS for driver/BIOS/ACPI implementation, HAS for HW registers/behavior). Conflicts between SwAS and HAS must be resolved by the architecture team — neither takes automatic precedence.

## QuickI2C SwAS v1.0 - Concise DSM & Platform Notes

- _DSD property clarifications (QuickI2C SwAS v1.0): `RevisionID` indicates the _DSD revision for the connection object. `DeviceAddress` encodes the I2C address with the following bit layout: bits[6:0] = lowest 7 bits of address (complete address in 7-bit mode); bit[7] = MSB for 10-bit mode (in 10-bit addressing this is part of the address; in 7-bit mode this bit must be 0); bits[15:8] = upper 8 bits for 10-bit addressing (set to 0 for 7-bit mode); bits[15:10] are reserved and must be 0; bits[9:8] are the highest two bits in 10-bit mode and reserved (0) in 7-bit mode. Drivers and BIOS should encode/decode DeviceAddress per this layout. (QuickI2C SwAS v1.0)

- ConnectionSpeed rounding: per QuickI2C SwAS v1.0 the OS/BIOS/driver should round the requested connection speed down to the nearest supported THC I2C mode (Standard/Fast/FastPlus/HighSpeed) and select corresponding HCNT/LCNT timing values. Recommended nominal speeds: 100 kbps (Standard), 400 kbps (Fast), 1 Mbps (Fast Plus). (QuickI2C SwAS v1.0)

- Workaround DSM integer flags (QuickI2C SwAS v1.0): the platform may expose integer DSM properties to enable I2C workarounds: e.g., a boolean-style integer flag to enable I2C_MAX_FRAME_SIZE workaround (value 1 = enabled) and an integer specifying the max frame size for reads. Another integer may enable the interrupt-delay workaround (value 1 = enabled) and a paired integer provides the delay multiplier (value × 10µs). Drivers should check these DSM entries and apply the specified workaround behavior when present. (QuickI2C SwAS v1.0)

# THC HIDI2C Protocol Reference

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.


Complete HIDI2C protocol specification mapped to THC IP HAS constructs for FV test development and debug.

> **Source**: [HID Over I2C Protocol Specification v1.0](https://learn.microsoft.com/en-us/windows-hardware/drivers/hid/hid-over-i2c-guide) (Microsoft)

## Protocol Overview
- HOST (master) communicates with DEVICE (slave) over I2C
- All transactions HOST-initiated except device-initiated reset (DIR)
- Dedicated interrupt line (INT) per device — **Exclusive, Level-triggered, ActiveLow REQUIRED** (v1.0)
- **Byte ordering**: Little-endian, LSB first (same as USB HID)
- **No CRC** — no error detection mechanism for bit errors
- **Clock stretching**: Device must not exceed **10 milliseconds**
- **No multi-master support**
- **HIDI2C added in Gen4.0 (LNL-M)** with SWDMA, TXDMA, RXDMA support
- **1 I2C transaction = 1 THC frame** — no microframe concept for I2C (unlike SPI fragmentation)
- Supports up to **Fast Speed Plus (FM+)** I2C mode explicitly per HAS/LNL SAS

## HIDI2C HID Descriptor (30 bytes)

| Offset | Field | Size | Description |
|--------|-------|------|-------------|
| 0 | wHIDDescLength | 2 | `0x001E` (30 bytes) |
| 2 | bcdVersion | 2 | Protocol version (`0x0100`) |
| 4 | wReportDescLength | 2 | Report Descriptor length |
| 6 | wReportDescRegister | 2 | Register address for Report Descriptor |
| 8 | wInputRegister | 2 | Register address for Input Reports |
| 10 | wMaxInputLength | 2 | Max input report length (minimum=2) |
| 12 | wOutputRegister | 2 | Register address for Output Reports |
| 14 | wMaxOutputLength | 2 | Max output report length |
| 16 | wCommandRegister | 2 | Register address for Commands |
| 18 | wDataRegister | 2 | Register address for Data |
| 20 | wVendorID | 2 | USB Vendor ID (must be non-zero) |
| 22 | wProductID | 2 | USB Product ID |
| 24 | wVersionID | 2 | Device firmware version |
| 26 | Reserved | 4 | Must be zero |

## HIDI2C Class-Specific Requests (Opcodes)

Commands sent via Command Register (2 bytes):

### Command Encoding (16-bit, Little-Endian)
```
Byte 0 (Low):  [ReportID:3-0] [ReportType:5-4] [Reserved:7-6]
Byte 1 (High): [Opcode:11-8]  [Reserved:15-12]
```
- **ReportType**: `01`=Input, `10`=Output, `11`=Feature
- **Opcode**: See table below
- When **ReportID ≥ 15**: Low byte's ReportID = `0xF` (sentinel), **3rd byte appended** with actual Report ID (0-255)
- HSDES fix `14021506058`: threshold is `< 15` not `<= 15`

| Request | Opcode | Mandatory | Description |
|---------|--------|-----------|-------------|
| RESET | `0x01` | Yes | Host-initiated reset (HIR) or Device-initiated reset (DIR) |
| GET_REPORT | `0x02` | Yes* | Uses I2C repeated START (write cmd → read data) |
| SET_REPORT | `0x03` | Yes | Sets Feature or Output reports |
| GET_IDLE | `0x04` | Optional | Returns 2-byte frequency |
| SET_IDLE | `0x05` | Optional | Sets reporting frequency |
| GET_PROTOCOL | `0x06` | Optional | Returns protocol value |
| SET_PROTOCOL | `0x07` | Optional | Sets protocol mode |
| SET_POWER | `0x08` | Device=Yes | `0x00`=ON, `0x01`=SLEEP |

## HIDI2C RESET Protocol
- **HIR**: Host sends RESET (`0x01`) to Command Register. Device writes `0x0000` sentinel to Input Register + asserts INT. Must complete within **5 seconds**.
- **DIR**: Device self-resets, same sentinel mechanism. Host detects via interrupt.
- After any RESET → device in **ON** power state.

> **Reset frequency**: Reset command is sent once per boot during first initialization. On subsequent D0 entries, reset is optional — host may send it at any time for error recovery.

## HIDI2C Power States

| State | Value | Description |
|-------|-------|-------------|
| ON | `0x00` | Fully operational |
| SLEEP | `0x01` | Low-power, device can wake host via INT |

- **No OFF state** — only ON↔SLEEP transitions
- After RESET → always ON
- Transition must complete within **< 1 second**

## HIDI2C ACPI Configuration

| Property | Value |
|----------|-------|
| `_CID` | `PNP0C50` (or `ACPI0C50` — both valid) |
| `_DSM UUID` | `3CDFF6F7-4267-4555-AD05-B30A3D8938DE` |
| `_DSM Rev` | 1 |
| `_DSM Func 1` | HID Descriptor Address (2 bytes) |
| `_CRS` | I2CSerialBus + GpioInt (must appear first) |

### THC Platform DSM (Separate GUID)
A **second** ACPI DSM GUID is used for THC platform-level LTR configuration:

| Property | Value |
|----------|-------|
| `_DSM UUID` | `84005682-5B71-41A4-8D66-8130F787A138` |
| `_DSM Rev` | 1 |
| `_DSM Func 1` | Active LTR value (microseconds) |
| `_DSM Func 2` | Low Power LTR value (microseconds) |

> **Key distinction**: The HIDI2C GUID (`3CDFF6F7-...`) is device-level (returns HID descriptor address). The platform GUID (`84005682-...`) is THC-level (returns LTR configuration). Both are queried during probe.
> **LTR sentinel value**: If the ACPI _DSM returns `0xFFFFFFFF` for Active or Low Power LTR, the driver interprets this as "use driver default" — the ACPI value is ignored and the built-in default LTR is applied instead. This sentinel convention allows platforms to defer LTR tuning to the driver rather than specifying explicit values in ACPI tables.

### Additional ACPI GUIDs (from QuickI2C SwAS v1.0)

The QuickI2C SwAS defines additional ACPI GUIDs beyond the two above:

| GUID | Purpose | Used By |
|------|---------|---------|
| `{41C1B4AF-E89A-44B5-AAB0-039D4B5BFF61}` | **THC DSD** — THC device-specific data properties | Windows driver — ACPI `_DSD` for THC-level configuration |
| `{B38B028B-AB16-45C3-92FB-758686BBC3A4}` | **Platform DSD** — Platform-specific configuration | Windows driver — ACPI `_DSD` for platform-level config (board/OEM settings) |
| `300D35B7-AC20-413E-8E9C-92E4DAFD0AFE` | **Platform DSM** — Platform workarounds/overrides | Windows driver — ACPI `_DSM` for ECO fixes and workaround control |

> **⚠️ Source**: QuickI2C SwAS v1.0 (Sep 10, 2025). The Platform DSM GUID `300D35B7-...` is the same GUID used in the QuickSPI SwAS for THC-level configuration — it is a shared THC platform GUID across both HIDSPI and HIDI2C drivers.
> **Validation point**: Verify all 4 GUIDs are present in ACPI tables: HIDI2C DSM (`3CDFF6F7-...`), LTR DSM (`84005682-...`), THC DSD (`41C1B4AF-...`), Platform DSD (`B38B028B-...`). The Platform DSM (`300D35B7-...`) may be optional depending on whether ECO fixes are needed.

> **_RST behavior**: QuickI2C driver does NOT invoke ACPI _RST directly — OSPM handles it per ACPI spec. The driver uses the HIDI2C protocol RESET command (opcode 0x01) instead.

### Extended ACPI Properties (Windows Driver)
- `_DSD GUID_HIDI2C_CONFIG` (`{daffd814-6eba-4d8c-8a91-bc9bbf4aa301}`): Standard device properties — ICRS property
- `_DSD GUID_HIDI2C_SUBIPCONFIG` (`{dbb8e3e6-5886-4ba6-8795-1319f52a966b}`): I2C Sub-IP config overrides (ISUB method)

## I2C Speed Configuration

### I2C timing registers and counts (QuickI2C SwAS v1.0)

- HCNT/LCNT register mapping per I2C mode: the Synopsys timing fields are mode-specific and drivers must program the matching pair for the selected mode:
  - Standard mode (≈100 kbps): IC_SS_SCL_HCNT and IC_SS_SCL_LCNT (use these for all Standard-mode timing). (QuickI2C SwAS v1.0)
  - Fast mode (≈400 kbps) and Fast-Plus (≈1 Mbps): IC_FS_SCL_HCNT and IC_FS_SCL_LCNT (these fields are used for both 400 kbps and 1 Mbps ranges; select appropriate counts per the chosen nominal speed). (QuickI2C SwAS v1.0)
  - High-Speed mode (≈3.4 Mbps): IC_HS_SCL_HCNT and IC_HS_SCL_LCNT. (QuickI2C SwAS v1.0)

- SDA timing (Hold / Setup): the DSM/ISUB/ICRS timing fields include per-mode SDA Hold and SDA Setup time counts. These values are provided as integers expressed in ic_clk_cycles (Synopsys I2C core clock cycles). Drivers must convert ic_clk_cycles → time using the configured ic_clk rate and program the corresponding SDA hold/setup registers for the selected mode. (QuickI2C SwAS v1.0)

- Spike suppression (receive hold / suppressed-spike length): QuickI2C SwAS documents per-mode spike suppression fields expressed as an integer maximum length in ic_clk_cycles. These fields limit the length of a glitch/spike that the Synopsys block will suppress rather than treat as a line transition. Typical field names in firmware/platform descriptors map to `ic_*_spklen` or `receive_hold` semantics; drivers should read the ISUB/DSD fields (or Synopsys register defaults) and apply the indicated `ic_clk_cycles` suppression length per mode (Std/Fast/FastPlus/HighSpeed). (QuickI2C SwAS v1.0)

- Receive HOLD per mode: the SwAS enumerates a "Receive HOLD" parameter for each mode (Standard, Fast, FastPlus, HighSpeed) expressed as the maximum suppressed-spike length in ic_clk_cycles. When present in ACPI/ISUB the driver should use this integer to tune the Synopsys receive/spike-suppression behavior. (QuickI2C SwAS v1.0)

- Units and conversion: all timing DSM / ISUB integer timing values called out by the SwAS (HCNT/LCNT, SDA hold/setup, receive_hold, spklen) are integer counts in ic_clk_cycles unless otherwise specified. Drivers must convert ic_clk_cycles → nanoseconds using the platform-provided I2C core clock rate before comparing against absolute time requirements in the I2C device datasheet. (QuickI2C SwAS v1.0)

> **Implementation note**: The SwAS intentionally provides timing primitives as counts (ic_clk_cycles) and mode-specific HCNT/LCNT pairs; drivers should avoid hard-coded microsecond numbers and instead compute timing from the HCNT/LCNT/hold/setup counts after reading the platform's ic_clk frequency. (QuickI2C SwAS v1.0)

### Concrete timing fields referenced in SwAS (reconstructed)

- SCL HIGH/LOW counts: the SwAS references SCL high/low period counts per mode. Map these to Synopsys fields as follows (counts = number of ic_clk_cycles):
  - Standard (100 kbps): IC_SS_SCL_HCNT (SCL high period), IC_SS_SCL_LCNT (SCL low period). (QuickI2C SwAS v1.0)
  - Fast (400 kbps): IC_FS_SCL_HCNT (SCL high), IC_FS_SCL_LCNT (SCL low). (QuickI2C SwAS v1.0)
  - Fast Plus (1 Mbps): use IC_FS_SCL_HCNT / IC_FS_SCL_LCNT with counts selected for 1 Mbps timing. (QuickI2C SwAS v1.0)
  - High Speed (3.4 Mbps): IC_HS_SCL_HCNT / IC_HS_SCL_LCNT. (QuickI2C SwAS v1.0)

- SDA Hold / SDA Setup counts per mode: the SwAS documents per-mode SDA hold/setup counts (expressed in ic_clk_cycles). Typical platform property names and Synopsys register groups follow the mode prefixes (SS/FS/HS). Drivers should apply the corresponding per-mode SDA hold/setup counts when configuring the controller. (QuickI2C SwAS v1.0)

- Spike suppression / Receive HOLD: the SwAS lists a per-mode "Receive HOLD" or spike-suppression maximum length expressed in ic_clk_cycles (often named `ic_*_spklen` or `receive_hold` in platform descriptors). This integer defines the maximum glitch length that will be suppressed. Drivers must read the ISUB/_DSD value and program controller spike-suppression or use it to tune driver-side filtering. (QuickI2C SwAS v1.0)

- Serial Data timing fields: SwAS references Serial Data hold/setup counts for Std/Fast/FastPlus/HighSpeed — map these to the per-mode data hold/setup registers on the Synopsys core (mode-prefixed fields). Use counts converted from ic_clk_cycles to validate against device datasheet requirements. (QuickI2C SwAS v1.0)

- Example usage note: if platform _DSM exposes `receive_hold` = N, then the driver interprets N as ic_clk_cycles and programs spike suppression accordingly (e.g., if ic_clk = 48 MHz, 1 ic_clk_cycle ≈ 20.83 ns). Convert counts to time before validating against device timing windows. (QuickI2C SwAS v1.0)

### Cross-Platform Timing Comparison

| Parameter | Windows Value | Linux Value | Notes |
|-----------|--------------|-------------|-------|
| SS_HCNT | `0x73` (115) | `0x267` (615) | **Significantly different** |
| SS_LCNT | `0x7D` (125) | `0x271` (625) | **Significantly different** |
| FS_HCNT | `0x1F4` (500) | `0x92` (146) | **3.4× higher** — slower Fast mode. ⚠️ Windows: defined as defaults but NEVER used as actual fallbacks — code falls back to SS defaults (115/125) regardless of speed mode |
| FS_LCNT | `0x24C` (588) | `0x9C` (156) | **3.8× higher**. ⚠️ Same as FS_HCNT — Windows FS defaults are defined but never used as fallbacks |
| RX_TL | 62 | 62 | Same |
| TX_TL | 0 | 0 | Same |
| DMA_CR | `0x03` | `0x03` | Same (TX+RX DMA enable) |
| DMA_TDLR | 7 | 7 | Same |
| DMA_RDLR | 7 | 7 | Same |
| INTR_MASK | `0x7FFF` | — | All interrupts enabled |
| TARGET_ADDR | `0x0A` | From ACPI | Windows default = WACOM address |

> **⚠️ Windows vs Linux I2C timing**: The Windows driver uses significantly larger HCNT/LCNT values for Fast mode, resulting in a slower actual bus speed. This may be for compatibility with legacy panels or to provide more timing margin. ACPI ISUB overrides take priority over these defaults on both platforms.

### BOM52 NVL I2C Speed Mode Hex Values (Validated)

From BOM52 I2C Touch Panel wiki (page 4501129290) — validated on NVL across all three speed modes:

| Speed Mode | Connection Speed (Hex) | HCNT (Hex) | LCNT (Hex) | Frequency |
|------------|----------------------|------------|------------|-----------|
| Standard (SM) | `0x186A0` (100,000) | `0x267` (615) | `0x271` (625) | 100 KHz |
| Fast (FM) | `0x61A80` (400,000) | `0x92` (146) | `0x9C` (156) | 400 KHz |
| Fast Plus (FMP) | `0xF4240` (1,000,000) | `0x34` (52) | `0x3E` (62) | 1 MHz |

> **Source**: BOM52 I2C Touch Panel Confluence wiki. These hex values match the Linux kernel defaults for SM and FM modes. The FMP values (`0x34`/`0x3E`) are specific to NVL platform timing and should be verified against ACPI ISUB on other platforms.
> **⚠️ WCL FMP instability**: FMP (1 MHz) mode on WCL has known instability — see HSDES `16027559981` and `platform/SKILL.md` for details.

## I2C MPS Workaround

- **Root Cause**: **RTL bug** — I2C mode incorrectly uses `SPI_RD_MPS` register for internal operation (confirmed by HAS: "Uses SPI_RD_MPS register for internal operation due to RTL bug")
- **Affected**: LNL, PTL
- **Fixed in**: NVL
- `spi_rd_mps` must be set to `I2C_MPS_WA = 4096` for HIDI2C mode
- Applied automatically by `thc_common.py` via `thc_i2c_rtl_bug_wa()`

## THC HAS Cross-Reference: HIDI2C ↔ THC Implementation

| HIDI2C Operation | THC Register / Mechanism |
|-----------------|-------------------------|
| HID Descriptor Read (30B) | PIO opcode `0x1C` (Write+Read) |
| Report Descriptor Read | PIO opcode `0x1C` |
| Port Type = HIDI2C | `thc_m_prt_control.port_type` = `0x1` (offset `0x1008` bits[31:30]) |
| I2C Bus Speed | Synopsys APB: `IC_CON`, `IC_SS/FS_SCL_HCNT/LCNT` via PIO `0x13` |
| I2C Device Address | `IC_TAR` via PIO `0x13` |
| I2C Enable/Disable | `IC_ENABLE` via PIO `0x13` |
| I2C DMA Enable | `IC_DMA_CR` = `0x03` via PIO `0x13` |
| Input Report Read | RXDMA (runtime) or PIO opcode `0x14` (setup) |
| Output Report Write | TXDMA (runtime) or PIO opcode `0x18` (setup) |
| GET_REPORT (repeated START) | PIO opcode `0x1C` (Write+Read) |
| SET_REPORT | TXDMA or PIO opcode `0x18` |
| Host Reset (HIR) | **TXDMA** (`write_cmd_to_txdma`) + GPIO reset pin toggle |
| Device Reset sentinel | RXDMA detects length=0x0000 |
| SET_POWER ON/SLEEP | **TXDMA** (`write_cmd_to_txdma`) to wCommandRegister |

> **Output report acknowledgement (SwAS)**: For HIDI2C output reports, the device is NOT expected to send an interrupt acknowledgement after receiving the write. The driver should not wait for or expect a TIC interrupt following an output report TXDMA completion. This differs from input report flows where every frame triggers a device interrupt.

### QuickI2C PIO Opcode Map (Must-Know)

The QuickI2C SwAS uses five core PIO opcodes for THC-side I2C transactions:

| Opcode | Direction | Operation | Typical Use |
|--------|-----------|-----------|-------------|
| `0x12` | THC -> Sub-IP | Read I2C Sub-IP register | Read `IC_STATUS`, debug/status probes |
| `0x13` | THC -> Sub-IP | Write I2C Sub-IP register | Program `IC_CON`, `IC_TAR`, thresholds, DMA ctrl |
| `0x14` | THC -> Device | Read from I2C device | Small reads during setup/diagnostics |
| `0x18` | THC -> Device | Write to I2C device | Write command/data payloads |
| `0x1C` | THC <-> Device | Write then repeated-START read | HID descriptor/report descriptor/GET_REPORT paths |

> **Validation point**: `0x1C` is the critical repeated-START write-read primitive for HID-over-I2C semantics. Do not model descriptor fetch as write-write-read.

### PIO Write-Read Sequence (Opcode 0x1C)
1. Clear THC_SS_ERR + TSSDONE in `thc_m_prt_sw_seq_sts`
2. Set `THC_PIO_I2C_WBC` in `thc_m_prt_sw_seq_cntrl` = write byte count
3. Set `THC_SS_BC` in `thc_m_prt_sw_seq_cntrl` = total read byte count
4. Load write data into `THC_SW_SEQ_DATA0_ADDR`
5. Set `THC_SS_CD_IE` for completion interrupt
6. Set `THC_I2C_RW_PIO_EN` in `thc_m_prt_sw_seq_i2c_wr_cntrl` = 1
7. Set THC_SS_CMD = 0x1C, then TSSGO = 1
8. Wait for TSSDONE interrupt; read data from `thc_m_prt_sw_seq_data[0..n]`
9. Clear THC_SS_ERR + TSSDONE

## I2C Sub-IP Save/Restore (D3Cold)

15 Synopsys APB registers saved/restored across D3Cold (from Linux kernel `thc_i2c_subip_regs[]`):
`IC_CON`, `IC_TAR`, `IC_INTR_MASK`, `IC_RX_TL`, `IC_TX_TL`, `IC_DMA_CR`, `IC_DMA_TDLR`, `IC_DMA_RDLR`, `IC_SS_SCL_HCNT`, `IC_SS_SCL_LCNT`, `IC_FS_SCL_HCNT`, `IC_FS_SCL_LCNT`, `IC_HS_SCL_HCNT`, `IC_HS_SCL_LCNT`, `IC_ENABLE`

> **⚠️ Correction**: Previous versions listed `IC_SAR`, `IC_SDA_HOLD`, `IC_SDA_SETUP` — the kernel actually saves `IC_HS_SCL_HCNT`, `IC_HS_SCL_LCNT`, `IC_ENABLE` instead. The HAS may define a different set — always verify against HAS.
> **⚠️ CRITICAL Linux fix `a7fc15e` (kernel 6.20)**: Incorrect pointer arithmetic caused wrong registers to be saved/restored. Verify all 15 registers on kernels < 6.20.
> **⚠️ Restore behavior**: I2C **resume** (from suspend) uses simple `i2c_subip_regs_restore()` — a register write-back loop over the 15 saved values. Only **restore** (from hibernate) calls full `i2c_subip_init()` re-initialization. SPI restore does `reset_tic` + full reconfig instead.

## HIDI2C Validation Points
- I2C speed mode transitions: SM (100K), FM (400K), FMP (1M), HS (1.7M/3.4M), UFm (5M write-only)
- Device addressing (7-bit) and clock stretching (≤10ms)
- HID descriptor read (30 bytes) and report descriptor read
- RESET protocol: HIR and DIR — verify 0x0000 sentinel + INT assert within 5 seconds
- Report ID ≥ 15: verify 3rd byte sentinel mechanism
- GET_REPORT with repeated START (write-read, not write-write-read)
- SET_POWER: ON (0x00) ↔ SLEEP (0x01) only — no OFF state, RESET always returns to ON
- Level-triggered interrupt: REQUIRED — verify remains asserted until data fully read
- I2C MPS workaround: verify applied on LNL/PTL, not needed on NVL
- Synopsys APB register programming sequence validation
- I2C sub-IP interrupts in `thc_m_prt_int_en` — **Linux**: 9 of 11 bits enabled (TX_EMPTY and ACTIVITY NOT enabled); **Windows**: only 7 of 11 enabled (START_DET=0, STOP_DET=0 in addition to TX_EMPTY=0 and ACTIVITY having no enable bit)
- D3Cold save/restore of all 15 APB registers
- ACPI _CID = `PNP0C50`, _DSM UUID `3CDFF6F7-...`, Function 1 returns HID descriptor address
- ACPI platform DSM UUID `84005682-...` — Function 1/2 return Active/LP LTR values
- NAK handling and bus error recovery (⚠️ Windows HIDI2C.sys has **no built-in retry logic** — test retry behavior is host-driver-specific)
- **Maximum I2C transfer size**: 4 KB per transaction; max HID report descriptor length = 4 KB
- **Input buffer minimum 4KB**: Kernel enforces `min(wMaxInputLength, 4096)` — even if device reports smaller, buffer is at least 4KB
- **Reset fallback**: On reset timeout, kernel performs PIO read of 2 bytes from `wInputRegister` to clear stale data before failing
- **output_report callback has NO PM runtime handling**: `quicki2c_hid_output_report()` (the `.output_report` HID callback) does NOT call `pm_runtime_get`/`put` — potential bug if device is runtime-suspended. Note: `quicki2c_hid_raw_request()` DOES have proper PM handling (`pm_runtime_resume_and_get` / `pm_runtime_put_autosuspend`). All other HID ops (parse, start, stop, open, close) also have proper PM handling
- **ARB_POLICY forced to FRAME_BOUNDARY**: Kernel sets `THC_M_PRT_CONTROL.arb_policy` to frame boundary arbitration for I2C mode

## PORT_TYPE Register Configuration

The THC port type is configured via the `THC_M_PRT_CONTROL.PORT_TYPE` register:
| Value | Mode | Description |
|-------|------|-------------|
| 00 | SPI | Default — HIDSPI/QuickSPI mode |
| 01 | I2C | HIDI2C mode (LNL+ Gen4.0+) |

### Important Notes
- PORT_TYPE must be set BEFORE any I2C transactions
- Changing PORT_TYPE requires a soft reset of the port
- BIOS typically sets PORT_TYPE based on ACPI configuration

## SPI Register Reuse for I2C (RTL Quirk)

THC reuses SPI-named registers for I2C configuration. The Linux kernel maps:

| SPI Register Name | I2C Usage | Kernel Mapping |
|-------------------|-----------|---------------|
| `THC_M_PRT_SPI_ICRRD_OPCODE` (0x14) | **I2C Max Data Size** | `thc_i2c_subip_set_max_data_size()` — sets max transfer size |
| `THC_M_PRT_SPI_DMARD_OPCODE` (0x18) | **I2C Interrupt Delay** | `thc_i2c_subip_set_max_interrupt_delay()` — PTL+ only |
| `THC_M_PRT_SPI_CFG.spi_rd_mps` (0x10) | **I2C MPS** | Must be set to 4096 (known RTL bug) |

> **Validation point**: When PORT_TYPE=I2C, verify that SPI opcode registers contain I2C config values (not SPI opcodes).

### Interrupt Servicing Delay — Platform Requirements (from QuickI2C SwAS v1.0)

The interrupt servicing delay is a SwAS-mandated requirement that both Windows and Linux drivers must comply with:

| Platform | Delay Value | Behavior | Notes |
|----------|-------------|----------|-------|
| **PTL** | Fixed **1ms** | `DEFAULT_INTERRUPT_DELAY_US = 1000` | Hardcoded in driver; not configurable via ACPI |
| **WCL** | Fixed **1ms** | Same as PTL | Same driver defaults |
| **NVL+** | Variable | Configurable in **10µs multiples** via ACPI or registry | `I2C_Int_Delay` registry key or ACPI `ddata` |

> **⚠️ Source**: QuickI2C SwAS v1.0 (Sep 10, 2025). The 1ms fixed delay on PTL/WCL is a SW policy choice, not a HW limitation. NVL+ allows finer-grained tuning for different touch device response characteristics.
> **Validation point**: On PTL/WCL, verify interrupt delay is always 1ms regardless of ACPI settings. On NVL+, verify delay is programmable via registry and ACPI `ddata`.

## PCI Device IDs (HIDI2C — THC0/THC1)

| Platform | THC0 Device ID | THC1 Device ID | Source |
|----------|---------------|---------------|--------|
| LNL | `0xA848` | `0xA84A` | `pci-quicki2c.c` |
| PTL-H (PTL-H4Xe, PCD-H) | `0xE348` | `0xE34A` | `pci-quicki2c.c` |
| PTL-U & PTL-P (PTL-H12Xe, PCD-P) | `0xE448` | `0xE44A` | `pci-quicki2c.c` |
| WCL | `0x4D48` | `0x4D4A` | `pci-quicki2c.c` |
| NVL (PCD-H) | `0xD348` | `0xD34A` | Co-De Sign (novalake PCD regmaps) |
| RZL | `0x6C48` | `0x6C4A` | Co-De Sign (razorlake PCD) |
| TTL | `0x9334` | `0x9339` | Co-De Sign (titanlake PCD) ⚠️ Non-standard pattern |

> **No MTL/ARL I2C**: HIDI2C support starts at LNL (Gen4.0). MTL and ARL are SPI-only.
> **NVL/RZL/TTL**: Not yet in upstream Linux kernel as of v6.20. DIDs from Co-De Sign platform specs.
> **TTL breaks the standard pattern**: THC0=`0x9334`, THC1=`0x9339` (not the usual x8/xA even-nibble pattern).
> **⚠️ QuickI2C Non-POR on NVL+**: HSDES `16028137599` — the Windows THC QuickI2C driver is **dropped from NVL+ platforms**. QuickI2C/QuickSPI are Non-POR starting NVL. The inbox Microsoft HIDI2C driver replaces the Intel QuickI2C driver on these platforms. See `debug/SKILL.md` → Pattern "QuickSPI/QuickI2C Non-POR (NVL+)" for full details.

### Windows-Only PCI Device IDs (HIDI2C)

> **Windows QuickI2C Driver Versions**: v5.5.0.7 (initial WCL release) and v5.5.0.10 (latest validated). These are the Intel QuickI2C driver versions — distinct from the inbox Microsoft HIDI2C driver. QuickI2C is **Non-POR from NVL+** (see HSDES `16028137599`).

| Platform | THC0 Device ID | THC1 Device ID | Source |
|----------|---------------|---------------|--------|
| ADL-LP | `0x7A50` | `0x7A51` | Windows HIDI2C driver (not in Linux kernel) |
| LNL-M | `0xA848` | `0xA84A` | Both Windows and Linux |

> **⚠️ ADL-LP HIDI2C**: The ADL-LP PCI IDs `7A50`/`7A51` appear in the Windows HIDI2C driver but NOT in the Linux kernel. This suggests HIDI2C support was validated on ADL-LP with the Windows driver before the Linux kernel gained HIDI2C support at LNL.

## ACPI Configuration (ICRS / ISUB Methods)

### ACPI _DSM Methods (HIDI2C)
- **_CID**: `PNP0C50` (standard HID-over-I2C compatible ID)
- **_DSM UUID**: `3CDFF6F7-4267-4555-AD05-B30A3D8938DE` — Function 1 returns HID descriptor register address

### Device-Specific Data (ACPI `ddata`)
The Linux kernel reads I2C configuration from two ACPI methods:

| Method | Purpose | Key Fields |
|--------|---------|-----------|
| **ICRS** | I2C Configuration Resource | `device_address` (u16), `connection_speed` (u64, in Hz), `addressing_mode` (u8), `reserved` (u8) — **12 bytes total** |
| **ISUB** | I2C Sub-IP Configuration | 22 u64 fields + 1 reserved byte = **177 bytes** (see ISUB Field Map below) |

### `_DSD` / Device-Specific Data properties (SwAS clarifications)

QuickI2C SwAS v1.0 documents `_DSD` properties used by Windows drivers for device-level configuration. Key properties include `RevisionID` (Integer — indicates revision of the `_DSD` object) and `DeviceAddress` (u16 packed bitfields per ACPI/I2C definition). The `DeviceAddress` bit layout follows the ACPI spec: Bit[7] = 0 in 7-bit addressing mode; Bits[6:0] = lowest 7 bits of the address; Bits[9:8] = highest two bits for 10-bit addressing; Bits[15:10] are reserved and must be 0. Drivers must parse these bitfields to determine 7-bit vs 10-bit addressing modes and construct `IC_TAR` accordingly. (QuickI2C SwAS v1.0)

### ISUB Field Map (22 u64 fields from ACPI)

| Field | Full Name | I2C Register | Used by Linux | Used by Windows |
|-------|-----------|-------------|----------------|-----------------|
| `SMHX` | SS SCL High Count | `IC_SS_SCL_HCNT` | **Yes** | **Yes** |
| `SMLX` | SS SCL Low Count | `IC_SS_SCL_LCNT` | **Yes** | **Yes** |
| `SMTD` | SS SDA TX Hold | `IC_SDA_HOLD[15:0]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `SMRD` | SS SDA RX Hold | `IC_SDA_HOLD[23:16]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `FMHX` | FS SCL High Count | `IC_FS_SCL_HCNT` | **Yes** | **Yes** |
| `FMLX` | FS SCL Low Count | `IC_FS_SCL_LCNT` | **Yes** | **Yes** |
| `FMTD` | FS SDA TX Hold | `IC_SDA_HOLD[15:0]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `FMRD` | FS SDA RX Hold | `IC_SDA_HOLD[23:16]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `FMSL` | FS Spike Length | `IC_FS_SPKLEN` | **No** (ignored) | **No** (ignored) |
| `FPHX` | FMP SCL High Count | `IC_FS_SCL_HCNT` | **Yes** (FMP uses FS regs) | **Yes** |
| `FPLX` | FMP SCL Low Count | `IC_FS_SCL_LCNT` | **Yes** (FMP uses FS regs) | **Yes** |
| `FPTD` | FMP SDA TX Hold | `IC_SDA_HOLD[15:0]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `FPRD` | FMP SDA RX Hold | `IC_SDA_HOLD[23:16]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `HMHX` | HS SCL High Count | `IC_HS_SCL_HCNT` | **Yes** | **Yes** |
| `HMLX` | HS SCL Low Count | `IC_HS_SCL_LCNT` | **Yes** | **Yes** |
| `HMTD` | HS SDA TX Hold | `IC_SDA_HOLD[15:0]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `HMRD` | HS SDA RX Hold | `IC_SDA_HOLD[23:16]` | **No** (ignored) | **Yes** (programs IC_SDA_HOLD) |
| `HMSL` | HS Spike Length | `IC_HS_SPKLEN` | **No** (ignored) | **No** (ignored) |
| `FSEN` | FS Enable | Override flag | **Yes** (if non-zero, use ISUB values) | **Yes** |
| `FSVL` | FS Value | Override value | **Yes** | **Yes** |
| `INDE` | Index Enable | Override flag | **Yes** | **Yes** |
| `INDV` | Index Value | Override value | **Yes** | **Yes** |

> **⚠️ 10 of 22 fields ignored by Linux**: The **Linux kernel** ignores ALL SDA hold fields (`SMTD/SMRD/FMTD/FMRD/FPTD/FPRD/HMTD/HMRD`) and ALL spike length fields (`FMSL/HMSL`). `IC_SDA_HOLD` is NOT programmed during Linux `thc_i2c_subip_init()`. Only SCL timing (HCNT/LCNT) and override control fields are used. **Windows DOES program `IC_SDA_HOLD`** using the ISUB fields: SMTD/FMTD/HMTD for TX hold and SMRD/FMRD/HMRD for RX hold, with registry override and defaults as fallback.

### I2C Speed Mode Encoding (from ACPI ICRS)
| Value | Mode | Frequency |
|-------|------|-----------|
| 0x01 | Standard | 100 KHz |
| 0x02 | Fast | 400 KHz |
| 0x03 | Fast Mode Plus | 1 MHz |
| 0x04 | High-Speed | 3.4 MHz |

## I2C Sub-IP Interrupt Bits (Bits 17–27 of THC_M_PRT_INT_EN)

| Bit | Name | Readable (STS) | Writable (EN) | Linux Enabled | Windows Enabled | Notes |
|-----|------|----------|----------|-------------------|-----------------|-------|
| 17 | RX_UNDER | Yes | Yes | **Yes** | **Yes** | RX FIFO underflow |
| 18 | RX_OVER | Yes | Yes | **Yes** | **Yes** | RX FIFO overflow |
| 19 | RX_FULL | Yes | Yes | **Yes** | **Yes** | RX FIFO above threshold |
| 20 | TX_OVER | Yes | Yes | **Yes** | **Yes** | TX FIFO overflow |
| 21 | TX_EMPTY | Yes | Yes | No | No | TX FIFO below threshold — **NOT enabled by either driver** |
| 22 | **TX_ABRT** | Yes | Yes | **Yes** | **Yes** | **TX abort occurred** (NOT RD_REQ — corrected from prior versions) |
| 23 | **ACTIVITY** | **Yes (status)** | **No (enable)** | No | No | **Asymmetry: readable in status but NOT writable in enable register** |
| 24 | SCL_STUCK_AT_LOW | Yes | Yes | **Yes** | **Yes** | SCL stuck low (bus hung) |
| 25 | STOP_DET | Yes | Yes | **Yes** | **No** | Stop condition detected — **Linux only** |
| 26 | START_DET | Yes | Yes | **Yes** | **No** | Start condition detected — **Linux only** |
| 27 | MST_ON_HOLD | Yes | Yes | **Yes** | **Yes** | Master on hold |

> **⚠️ CORRECTION (v3)**: RX_FULL (bit 19) IS enabled by kernel — previous version incorrectly said "No". The kernel `thc_interrupt_config()` enables RX_FULL as part of the I2C interrupt mask. Updated enabled count: **9 of 11** bits are enabled (not 7 as previously stated). The 2 NOT enabled are: TX_EMPTY(21) and ACTIVITY(23 — no enable bit). Also corrected bit 27 from "SCL_STUCK_AT_LOW (duplicate)" to "MST_ON_HOLD" — the kernel defines `THC_I2C_IC_MST_ON_HOLD_INT_EN` at BIT(27) and `THC_I2C_IC_SCL_STUCK_AT_LOW_DET_INT_EN` at BIT(24).
> **Kernel enable mask (Linux)**: 9 of 11 interrupt bits are enabled: `RX_UNDER(17) | RX_OVER(18) | RX_FULL(19) | TX_OVER(20) | TX_ABRT(22) | SCL_STUCK_AT_LOW(24) | STOP_DET(25) | START_DET(26) | MST_ON_HOLD(27)`. TX_EMPTY(21) is NOT enabled; ACTIVITY(23) has no enable bit.
> **Windows enable mask**: Only 7 of 11 interrupt bits are enabled. Windows does NOT enable START_DET(26) or STOP_DET(25), in addition to TX_EMPTY(21) being disabled and ACTIVITY(23) having no enable bit.
> **⚠️ Bit 22 correction**: Bit 22 is `TX_ABRT` in the kernel mapping (`THC_I2CSUBIP_INT_TX_ABRT_OFFSET = 22`), not `RD_REQ` as previously documented. The Synopsys DW_apb_i2c IP defines bit 6 as RD_REQ in its native register space, but THC remaps the I2C sub-IP interrupts to bits 17–27 of `THC_M_PRT_INT_EN`.
> **Validation point**: Bit 23 (ACTIVITY) asymmetry — attempting to enable ACTIVITY interrupt has no effect. Only readable via status register.

## Report ID ≥ 15 Encoding (M8)

For HID Report IDs ≥ 15, the HIDI2C protocol uses a **2-byte encoding**: a sentinel value `0x0F` in the low nibble of the first byte, followed by a second byte containing the actual Report ID. The threshold is `< 15` (not `<= 15`) per HSD 14021506058. Tests sending reports with Report ID 15 or higher must use this 3rd-byte encoding format.

## Synopsys DW_apb_i2c Sub-IP Details (from HAS)

### Configuration Constants
| Parameter | Value | Description |
|-----------|-------|-------------|
| IC_MAX_SPEED_MODE | 0x2 | Fast Mode Plus (1MHz max) |
| IC_TAR Reset Value | `0x086` (Synopsys HW reset) | **Not used at runtime.** Synopsys sub-IP powers up with IC_TAR = `0x086`; driver **always** overwrites this with the ACPI-provided target address (e.g., `0x0A` for WACOM) during `thc_i2c_subip_init()`. Do not confuse with the actual I2C slave address. |
| IC_CON Default | `0x0663` | `MASTER_MODE(0) \| SPEED=01(1:2) \| RESTART_EN(5) \| SLAVE_DISABLE(6) \| RX_FIFO_FULL_HLD_CTRL(9) \| STOP_DET_IF_MASTER_ACTIVE(10)` |

> **IC_CON breakdown**: `0x0663` = bits 0,1,5,6,9,10 set. SPEED field (bits 1:2) = `01` (Standard mode) as default, overwritten to match ACPI connection_speed during init. The kernel writes `0x0663` first, then modifies SPEED bits based on the selected mode.
> **ISUB SDA hold**: ACPI ISUB provides `sda_hold_transmit` and `sda_hold_receive` values, but the **Linux kernel ignores them entirely** — `IC_SDA_HOLD` is NOT programmed during `thc_i2c_subip_init()`. If SDA hold tuning is needed, it must be applied separately.

### I2C Speed Modes Supported
| Mode | Frequency | IC_CON Setting |
|------|-----------|---------------|
| Standard | 100 KHz | SPEED=01 |
| Fast | 400 KHz | SPEED=10 |
| Fast Mode Plus | 1 MHz | SPEED=10 + IC_FS_SPKLEN |

> **IC_FS_SPKLEN programming (SwAS)**: `IC_FS_SPKLEN` (offset `0xA0`) controls spike suppression length for Fast and Fast-Plus modes. The Synopsys DW_apb_i2c IP uses this value to filter glitches shorter than the specified number of `ic_clk` cycles on SDA/SCL lines. **Linux kernel** does NOT program this register (relies on HW reset default). **Windows driver** only programs it when an explicit registry override or ACPI value is provided. For FMP (1 MHz) operation, verify that the default spike suppression length is adequate for the bus capacitance and rise/fall times of the target platform.

> **IC_SDA_HOLD / IC_SDA_SETUP programming points (SwAS)**: `IC_SDA_HOLD` (offset `0x7C`) controls SDA hold time after SCL falling edge (transmit) and before SCL rising edge (receive). `IC_SDA_SETUP` (offset `0x94`) controls SDA setup time before SCL rising edge. These are optional tuning registers for bus timing compliance. **Linux kernel** ignores both — ACPI ISUB `sda_hold_transmit`/`sda_hold_receive` values are parsed but never written to `IC_SDA_HOLD`. `IC_SDA_SETUP` is not programmed by either driver. **Windows driver** conditionally programs `IC_SDA_HOLD` from registry overrides only. If I2C timing violations are observed (setup/hold failures on scope), these registers are the primary tuning points.

### Extended I2C Sub-IP Register Map (from kernel `intel-thc-hw.h`)

The kernel defines additional I2C sub-IP registers beyond the core init set:

| Offset | Register | Purpose | Notes |
|--------|----------|---------|-------|
| `0x00` | `IC_CON` | Control | Core config (speed, master, restart) |
| `0x04` | `IC_TAR` | Target Address | 7-bit device address |
| `0x08` | `IC_SAR` | Slave Address | Unused (master mode) |
| `0x0C` | `IC_HS_MADDR` | HS Master Address | High-speed master code |
| `0x10` | `IC_DATA_CMD` | Data Command | TX/RX data + control bits |
| `0x14` | `IC_SS_SCL_HCNT` | SS High Count | Standard-mode SCL high period |
| `0x18` | `IC_SS_SCL_LCNT` | SS Low Count | Standard-mode SCL low period |
| `0x1C` | `IC_FS_SCL_HCNT` | FS High Count | Fast-mode SCL high period |
| `0x20` | `IC_FS_SCL_LCNT` | FS Low Count | Fast-mode SCL low period |
| `0x24` | `IC_HS_SCL_HCNT` | HS High Count | High-speed SCL high period |
| `0x28` | `IC_HS_SCL_LCNT` | HS Low Count | High-speed SCL low period |
| `0x2C` | `IC_INTR_STAT` | Interrupt Status | Current interrupt status |
| `0x30` | `IC_INTR_MASK` | Interrupt Mask | All I2C interrupts |
| `0x34` | `IC_RAW_INTR_STAT` | Raw Interrupt Status | Pre-mask interrupt status |
| `0x38` | `IC_RX_TL` | RX Threshold | Default: 62 |
| `0x3C` | `IC_TX_TL` | TX Threshold | Default: 0 |
| `0x40` | `IC_CLR_INTR` | Clear All Interrupts | Write to clear |
| `0x44` | `IC_CLR_RX_UNDER` | Clear RX Under | Write to clear |
| `0x48` | `IC_CLR_RX_OVER` | Clear RX Over | Write to clear |
| `0x4C` | `IC_CLR_TX_OVER` | Clear TX Over | Write to clear |
| `0x50` | `IC_CLR_RD_REQ` | Clear Read Request | Write to clear |
| `0x54` | `IC_CLR_TX_ABRT` | Clear TX Abort | Clear abort status |
| `0x58` | `IC_CLR_RX_DONE` | Clear RX Done | Write to clear |
| `0x5C` | `IC_CLR_ACTIVITY` | Clear Activity | Write to clear |
| `0x60` | `IC_CLR_STOP_DET` | Clear Stop Detect | Write to clear |
| `0x64` | `IC_CLR_START_DET` | Clear Start Detect | Write to clear |
| `0x68` | `IC_CLR_GEN_CALL` | Clear General Call | Write to clear |
| `0x6C` | `IC_ENABLE` | Enable | Enable/disable sub-IP |
| `0x70` | `IC_STATUS` | Status | Active, TX/RX FIFO status |
| `0x74` | `IC_TXFLR` | TX FIFO Level | Current TX FIFO level |
| `0x78` | `IC_RXFLR` | RX FIFO Level | Current RX FIFO level |
| `0x7C` | `IC_SDA_HOLD` | SDA Hold | Hold time (Linux kernel ignores ACPI value; Windows programs from ISUB) |
| `0x80` | `IC_TX_ABRT_SOURCE` | TX Abort Source | Abort cause (16 bits) |
| `0x84` | `IC_SLV_DATA_NACK_ONLY` | Slave NACK Only | Slave mode NACK config |
| `0x88` | `IC_DMA_CR` | DMA Control | `0x03` = TX+RX DMA enable |
| `0x8C` | `IC_DMA_TDLR` | DMA TX Level | Default: 7 |
| `0x90` | `IC_DMA_RDLR` | DMA RX Level | Default: 7 |
| `0x94` | `IC_SDA_SETUP` | SDA Setup | SDA setup time |
| `0x98` | `IC_ACK_GENERAL_CALL` | ACK General Call | General call ACK config |
| `0x9C` | `IC_ENABLE_STATUS` | Enable Status | Current enable state |
| `0xA0` | `IC_FS_SPKLEN` | FS Spike Len | Fast-mode spike suppression |
| `0xA4` | `IC_HS_SPKLEN` | HS Spike Len | High-speed spike suppression |
| `0xA8` | `IC_CLR_RESTART_DET` | Clear Restart Detect | Write to clear |
| `0xAC` | `IC_SCL_STUCK_AT_LOW_TIMEOUT` | SCL Stuck Timeout | SCL stuck low timeout |
| `0xB0` | `IC_SDA_STUCK_AT_LOW_TIMEOUT` | SDA Stuck Timeout | SDA stuck low timeout |
| `0xB4` | `IC_CLR_SCL_STUCK_DET` | Clear SCL Stuck | Write to clear |
| `0xB8` | `IC_DEVICE_ID` | Device ID | I2C device ID |
| `0xF4` | `IC_COMP_PARAM_1` | Component Param 1 | RO: HW configuration |
| `0xF8` | `IC_COMP_VERSION` | Component Version | RO: Synopsys IP version |
| `0xFC` | `IC_COMP_TYPE` | Component Type | RO: `0x44570140` expected |

> **HW constraint**: DMA_RDLR MUST be ≤7 — THC internal temp buffer is 8 bytes max. Values >7 cause RF memory overflow (QuickI2C SwAS P0356).

> **Recommendation**: DMA_TDLR ≥3 to avoid frequent TX_EMPTY interrupts. Default value 7 matches LPSS defaults (QuickI2C SwAS T6R003).

> **IC_ENABLE mandatory programming contract**: The Synopsys DW_apb_i2c requires `IC_ENABLE` (offset `0x6C`) bit 0 = 0 (disabled) before ANY configuration register changes (`IC_CON`, `IC_TAR`, `IC_*_SCL_HCNT/LCNT`, `IC_SDA_HOLD`, etc.), then re-enabled (bit 0 = 1) after all changes are complete. Both Linux (`thc_i2c_subip_init()`) and Windows (Step 6 in init sequence) follow this contract. Writing to configuration registers while IC_ENABLE=1 produces UNDEFINED behavior.

> **⚠️ CORRECTION (v3)**: Previous version had several wrong offsets. `IC_TX_ABRT_SOURCE` was listed at `0xA0` — actually `0x80`. `IC_FS_SPKLEN` was at `0xA8` — actually `0xA0`. `IC_HS_SPKLEN` was at `0xAC` — actually `0xA4`. `IC_SDA_HOLD` was listed at `0x9C` — actually `0x7C` (kernel) or `0x9C` (HAS). The kernel offset `0x7C` is authoritative. Added many previously missing registers: IC_HS_MADDR(0x0C), IC_DATA_CMD(0x10), IC_INTR_STAT(0x2C), IC_RAW_INTR_STAT(0x34), IC_CLR_* series (0x40-0x68), IC_TXFLR(0x74), IC_RXFLR(0x78), IC_SLV_DATA_NACK_ONLY(0x84), IC_SDA_SETUP(0x94), IC_ACK_GENERAL_CALL(0x98), IC_ENABLE_STATUS(0x9C), IC_CLR_RESTART_DET(0xA8), IC_SCL_STUCK_AT_LOW_TIMEOUT(0xAC), IC_SDA_STUCK_AT_LOW_TIMEOUT(0xB0), IC_CLR_SCL_STUCK_DET(0xB4), IC_DEVICE_ID(0xB8).

#### Ultra-Fast Mode (UFM) Registers
| Offset | Register | Alias Of | Purpose |
|--------|----------|----------|---------|
| `0x14` | `IC_UFM_SCL_HCNT` | `IC_SS_SCL_HCNT` | UFM SCL High Count |
| `0x18` | `IC_UFM_SCL_LCNT` | `IC_SS_SCL_LCNT` | UFM SCL Low Count |
| `0x1C` | `IC_UFM_TBUF_CNT` | `IC_FS_SCL_HCNT` | UFM T-buf Count |
| `0xA0` | `IC_UFM_SPKLEN` | `IC_FS_SPKLEN` | UFM Spike Length |

> **⚠️ CORRECTION (v4)**: Previous version had WRONG offsets (`0x100`, `0x104`, `0x108`, `0x2C`). The kernel defines UFM registers as **aliases** at the same physical offsets as their SS/FS counterparts: `IC_UFM_SCL_HCNT=0x14` (same as `IC_SS_SCL_HCNT`), `IC_UFM_SCL_LCNT=0x18` (same as `IC_SS_SCL_LCNT`), `IC_UFM_TBUF_CNT=0x1C` (same as `IC_FS_SCL_HCNT`), `IC_UFM_SPKLEN=0xA0` (same as `IC_FS_SPKLEN`). These are NOT separate registers — they share the same MMIO addresses.
> **UFM note**: Ultra-Fast Mode (5 MHz) is **write-only** — no read support. Registers are defined in kernel header but not used in current driver.

#### SMBUS Registers (12+ registers defined)
| Offset | Register | Purpose |
|--------|----------|---------|
| `0xBC` | `IC_SMBUS_CLK_LOW_SEXT` | SMBUS Clock Low SEXT |
| `0xC0` | `IC_SMBUS_CLK_LOW_MEXT` | SMBUS Clock Low MEXT |
| `0xC4` | `IC_SMBUS_THIGH_MAX_IDLE_CNT` | SMBUS T-High Max Idle |
| `0xC8` | `IC_SMBUS_INT_STS` | SMBUS Interrupt Status |
| `0xCC` | `IC_SMBUS_INT_MASK` | SMBUS Interrupt Mask |
| `0xD0` | `IC_SMBUS_RAW_INT_STS` | SMBUS Raw Interrupt Status |
| `0xD4` | `IC_CLR_SMBUS_INT` | Clear SMBUS Interrupt |
| `0xD8` | `IC_OPT_SAR` | Optional Slave Address |
| `0xDC` | `IC_SMBUS_UDID_LSB/WORD0` | SMBUS UDID Word 0 |
| `0xE0-E8` | `IC_SMBUS_UDID_WORD1-3` | SMBUS UDID Words 1-3 |

> **⚠️ CORRECTION (v3)**: Previous version had shifted SMBUS register offsets (starting at 0xB0 instead of 0xBC). Kernel defines: `IC_SMBUS_CLK_LOW_SEXT=0xBC`, `IC_SMBUS_CLK_LOW_MEXT=0xC0`, `IC_SMBUS_THIGH_MAX_IDLE_COUNT=0xC4`, `IC_SMBUS_INTR_STAT=0xC8`, `IC_SMBUS_INTR_MASK=0xCC`, `IC_SMBUS_RAW_INTR_STAT=0xD0`, `IC_CLR_SMBUS_INTR=0xD4`, `IC_OPTIONAL_SAR=0xD8`, `IC_SMBUS_UDID_LSB/WORD0=0xDC`, WORD1=0xE0, WORD2=0xE4, WORD3=0xE8.
> **SMBUS note**: These registers are defined in the kernel header (`intel-thc-hw.h`) but **not used** by the current THC I2C driver. They indicate the Synopsys DW_apb_i2c sub-IP includes SMBUS support in its configuration, even though THC only uses standard I2C mode.

### I2C Sub-IP Key Register Bit Fields (from `intel-thc-hw.h`)

#### IC_CON Bit Fields (Offset 0x00)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `MASTER_MODE` | `BIT(0)` | Master mode enable |
| `[2:1]` | `SPEED` | `GENMASK(2,1)` | Speed mode: `01`=Standard, `10`=Fast/Plus, `11`=High |
| `[3]` | `IC_10BITADDR_SLAVE` | `BIT(3)` | 10-bit slave address mode |
| `[4]` | `IC_10BITADDR_MASTER` | `BIT(4)` | 10-bit master address mode |
| `[5]` | `IC_RESTART_EN` | `BIT(5)` | Restart condition enable |
| `[6]` | `IC_SLAVE_DISABLE` | `BIT(6)` | Slave mode disable |
| `[7]` | `STOP_DET_IFADDRESSED` | `BIT(7)` | Stop detect if addressed |
| `[8]` | `TX_EMPTY_CTRL` | `BIT(8)` | TX empty interrupt control |
| `[9]` | `RX_FIFO_FULL_HLD_CTRL` | `BIT(9)` | RX FIFO full hold control |
| `[10]` | `STOP_DET_IF_MASTER_ACTIVE` | `BIT(10)` | Stop detect if master active |
| `[11]` | `BUS_CLEAR_FEATURE_CTRL` | `BIT(11)` | Bus clear feature control |
| `[16]` | `OPTIONAL_SAR_CTRL` | `BIT(16)` | Optional slave address control |
| `[17]` | `SMBUS_SLAVE_QUICK_EN` | `BIT(17)` | SMBUS slave quick enable |
| `[18]` | `SMBUS_ARP_EN` | `BIT(18)` | SMBUS ARP enable |
| `[19]` | `SMBUS_PERSISTENT_SLV_ADDR_EN` | `BIT(19)` | SMBUS persistent slave address enable |

> **THC default IC_CON**: `0x0663` = MASTER_MODE + SPEED=01 + RESTART_EN + SLAVE_DISABLE + RX_FIFO_FULL_HLD_CTRL + STOP_DET_IF_MASTER_ACTIVE.

#### IC_TAR Bit Fields (Offset 0x04)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[9:0]` | `IC_TAR` | `GENMASK(9,0)` | Target I2C address (7-bit or 10-bit) |
| `[10]` | `GC_OR_START` | `BIT(10)` | General Call or START byte |
| `[11]` | `SPECIAL` | `BIT(11)` | Special command (GC or START) |
| `[12]` | `IC_10BITADDR_MASTER` | `BIT(12)` | 10-bit addressing mode (TAR) |
| `[13]` | `DEVICE_ID` | `BIT(13)` | Device ID transfer |
| `[16]` | `SMBUS_QUICK_CMD` | `BIT(16)` | SMBUS Quick Command |

#### IC_ENABLE Bit Fields (Offset 0x6C)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `ENABLE` | `BIT(0)` | Enable I2C sub-IP |
| `[1]` | `ABORT` | `BIT(1)` | Abort current transfer |
| `[2]` | `TX_CMD_BLOCK` | `BIT(2)` | Block TX command queue |
| `[3]` | `SDA_STUCK_RECOVERY_ENABLE` | `BIT(3)` | SDA stuck recovery enable |
| `[16]` | `SMBUS_CLK_RESET` | `BIT(16)` | SMBUS clock reset |
| `[17]` | `SMBUS_SUSPEND_EN` | `BIT(17)` | SMBUS suspend enable |
| `[18]` | `SMBUS_ALERT_EN` | `BIT(18)` | SMBUS alert enable |

#### IC_INTR_MASK Bit Fields (Offset 0x30)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `M_RX_UNDER` | `BIT(0)` | Mask RX underflow |
| `[1]` | `M_RX_OVER` | `BIT(1)` | Mask RX overflow |
| `[2]` | `M_RX_FULL` | `BIT(2)` | Mask RX FIFO full |
| `[3]` | `M_TX_OVER` | `BIT(3)` | Mask TX overflow |
| `[4]` | `M_TX_EMPTY` | `BIT(4)` | Mask TX FIFO empty |
| `[5]` | `M_RD_REQ` | `BIT(5)` | Mask read request |
| `[6]` | `M_TX_ABRT` | `BIT(6)` | Mask TX abort |
| `[7]` | `M_RX_DONE` | `BIT(7)` | Mask RX done |
| `[8]` | `M_ACTIVITY` | `BIT(8)` | Mask activity |
| `[9]` | `M_STOP_DET` | `BIT(9)` | Mask stop detect |
| `[10]` | `M_START_DET` | `BIT(10)` | Mask start detect |
| `[11]` | `M_GEN_CALL` | `BIT(11)` | Mask general call |
| `[12]` | `M_RESTART_DET` | `BIT(12)` | Mask restart detect |
| `[13]` | `M_MASTER_ON_HOLD` | `BIT(13)` | Mask master on hold |
| `[14]` | `M_SCL_STUCK_AT_LOW` | `BIT(14)` | Mask SCL stuck at low |

#### IC_DMA_CR Bit Fields (Offset 0x88)

| Bits | Field | Kernel Define | Description |
|------|-------|---------------|-------------|
| `[0]` | `RDMAE` | `BIT(0)` | Receive DMA enable |
| `[1]` | `TDMAE` | `BIT(1)` | Transmit DMA enable |

> **THC default IC_DMA_CR**: `0x03` = both RDMAE + TDMAE enabled for DMA-based I2C transfers.

### RTL Bug — SPI_RD_MPS in I2C Mode
**Critical:** THC incorrectly uses `SPI_RD_MPS` register even when operating in I2C mode.
- **Root cause**: RTL shares the SPI MPS register for both SPI and I2C data paths
- **Workaround**: Software MUST program `SPI_RD_MPS` to 4096 (4KB) when using I2C mode
- **Impact**: Without workaround, I2C DMA reads may be truncated or corrupted
- This affects ALL platforms with HIDI2C support (LNL+)

### I2C Bus Clear Feature (from QuickI2C SwAS v1.0)

THC supports the Synopsys DW_apb_i2c **bus clear** feature for recovering from stuck SDA/SCL conditions:

| Condition | Detection | Recovery Mechanism |
|-----------|-----------|-------------------|
| **SDA stuck low** | `IC_ENABLE.SDA_STUCK_RECOVERY_ENABLE` (bit 3) | Sub-IP drives SCL pulses to release SDA; monitored via `IC_SDA_STUCK_AT_LOW_TIMEOUT` (offset `0xB0`) |
| **SCL stuck low** | `IC_CON.BUS_CLEAR_FEATURE_CTRL` (bit 11) | Timeout-based detection via `IC_SCL_STUCK_AT_LOW_TIMEOUT` (offset `0xAC`); generates `SCL_STUCK_AT_LOW` interrupt (THC bit 24) |

- **Windows**: `IC_SDA_STUCK_RECOVERY_ENABLE=1` (Step 13 in Windows init). `BUS_CLEAR_FEATURE_CTRL` in IC_CON is **COMMENTED OUT** in the Windows code — it is NOT enabled despite being documented
- **Linux does NOT enable**: Neither SDA stuck recovery nor bus clear feature control is set in the kernel `thc_i2c_subip_init()`
- **Interrupt**: `SCL_STUCK_AT_LOW` interrupt (bit 24 of `THC_M_PRT_INT_EN`) IS enabled by the Linux kernel — so detection works, but automatic recovery does not

> **⚠️ Source**: QuickI2C SwAS v1.0 + IC_ENABLE/IC_CON bit field definitions from kernel `intel-thc-hw.h`.
> **Validation point**: Test SDA/SCL stuck scenarios on Windows (auto-recovery expected) vs Linux (interrupt fires but no auto-recovery). Verify `IC_SDA_STUCK_AT_LOW_TIMEOUT` and `IC_SCL_STUCK_AT_LOW_TIMEOUT` register values are appropriate for the target I2C speed mode.

## I2C DMA Mode Details

### DMA Engines in I2C Mode
| Engine | Direction | Description |
|--------|-----------|-------------|
| RXDMA1 | Device → Host | **Not used for I2C** (size set to 0; kernel only starts RXDMA2) |
| RXDMA2 | Device → Host | **Primary input report path** (kernel uses `THC_RXDMA2` exclusively) |

**RxDMA2 buffer allocation**: 16 PRD tables with 16 data buffers. Each buffer sized to `ceil(wMaxInputLength / 4096) * 4096` (4KB-aligned). Max single buffer = 1MB (THC HW limit).

| TXDMA | Host → Device | Output reports and commands |
| SWDMA | Device → Host | SW-triggered debug DMA (LNL+) |

### Slow Panel DMA Stalling (STALL_READ_EN + SOO)

For I2C devices with slow response times (e.g., panels that cannot prepare data within the normal bus turnaround), the QuickI2C SwAS recommends enabling **STALL_READ_EN** in combination with **SOO** (Start On Opcode) mode. When `STALL_READ_EN=1`, the DMA engine inserts a configurable stall between the write phase (sending the register address) and the read phase (clocking in data), giving the device time to prepare its response. The stall duration is controlled by `THC_SS_BC` (stall count) in the read DMA configuration. This is particularly important for HIDI2C panels where the device may NACK or stretch the clock if the host reads too aggressively after a write. See `dma/SKILL.md` → **Burst Mode** section for full `STALL_READ_EN` + `SOO` register programming details.

### I2C-Specific DMA Registers
Each DMA engine has dedicated registers for I2C operation, separate from SPI DMA registers.
The register offsets are in the per-port MMIO space (Port 0 @ 0x1000, Port 1 @ 0x2000).

### HIDI2C Command → DMA Mapping
| HIDI2C Command | DMA Engine | Notes |
|----------------|------------|-------|
| GET_REPORT (Input) | **SWDMA** | Requires RXDMA pause → SWDMA sequence (kernel confirmed) |
| GET_REPORT (Feature) | **SWDMA** | Same SWDMA flow as GET_INPUT_REPORT |
| Report Descriptor Read | **SWDMA** | `RX_DLEN_EN=0` (length known from HID descriptor) |
| SET_REPORT (Output) | TXDMA | Request via TXDMA |
| SET_REPORT (Feature) | TXDMA | Request via TXDMA |
| Output Report (runtime) | TXDMA | **No command prefix** — written directly to `wOutputRegister` |
| SET_POWER | **TXDMA** | Command written via `write_cmd_to_txdma()` → `thc_dma_write()` |
| RESET | **TXDMA** | Command written via `write_cmd_to_txdma()` → `thc_dma_write()` |

> **Output Report Note (kernel 6.20+)**: I2C output reports are written directly to `wOutputRegister` with NO command register prefix — just `[length(2B)][reportID(1B)][payload]`. This differs from SET_REPORT which goes through `wCommandRegister`.

> **Validation**: Output report length field must be > 3 bytes. Reports with length ≤ 3 are invalid per HIDI2C spec.

## SWDMA I2C Feature Interaction

When SWDMA is active in I2C mode, the **Linux kernel** disables two I2C-specific features and restores them after SWDMA completes:

| Feature | Disabled During SWDMA | Restored After SWDMA | Register |
|---------|----------------------|---------------------|----------|
| `rx_max_size` | Set to 0 (disabled) | Restored to original value | `THC_M_PRT_SPI_ICRRD_OPCODE` |
| `rx_int_delay` | Set to 0 (disabled) | Restored to original value | `THC_M_PRT_SPI_DMARD_OPCODE` |

This is done because SWDMA bypasses the normal RXDMA path — the max size and interrupt delay features would interfere with SWDMA's direct read behavior. The kernel calls:
1. `thc_i2c_subip_set_max_data_size(dev, 0)` — before SWDMA start
2. `thc_i2c_subip_set_max_interrupt_delay(dev, 0)` — before SWDMA start
3. (... SWDMA operation ...)
4. `thc_i2c_subip_set_max_data_size(dev, original)` — after SWDMA complete
5. `thc_i2c_subip_set_max_interrupt_delay(dev, original)` — after SWDMA complete

> **⚠️ Windows HIDI2C difference**: The Windows driver does **NOT** use selective rx_max_size/int_delay save/restore. Instead, Windows performs a full `DmaUnconfigure()` → `DmaConfigure()` cycle around SWDMA operations. This is a fundamentally different approach — Windows tears down and rebuilds the entire DMA configuration rather than surgically disabling individual features.
>
> **Validation point**: After SWDMA completes, verify `rx_max_size` and `rx_int_delay` are restored to their pre-SWDMA values (Linux). On Windows, verify full DMA reconfiguration completes successfully.

## Legacy Panel Support (PTL/WCL/NVL+)

### Elan Panel HIDI2C Frame Size Workaround

**Platforms**: Legacy Elan panel support was added starting with **PTL** (Panther Lake), and extended to **WCL** (Wildcat Lake) and **NVL** (Nova Lake) and later platforms. These platforms include BOM configurations with cost-optimized Elan touch panels that require special handling.

Certain cost-optimized Elan panels violate HIDI2C compliance by reporting invalid, oversized frame lengths. If processed by the THC, this discrepancy causes Frame Babble and irrecoverable sequencer desynchronization.

To work around this, the QuickI2C driver utilizes a specific ECO fix via the `I2C_Max_Frame_Size_Enable` registry override (value range 128-255). This hard-caps the frame acceptance limit within the driver, preventing the non-compliant Elan frame lengths from overflowing the PRD buffers and crashing the state machine.

### Key Considerations
- **PTL, WCL, NVL** (and later) platforms include BOM entries with Elan legacy panels
- Elan panels may not fully comply with HIDI2C specification
- Custom register sequences may be needed during init
- Driver must handle Elan-specific reset timing
- BIOS may need to configure special I2C timing parameters for Elan panels
- Refer to BOM device matrix in platform sub-skill for specific Elan panel models and per-platform availability

> **Simics I2C touch model** (alps_touchscreen architecture, BIOS config, touch data injection, SPARK i3c_xtor, validation points) → See **`fv-thc/simics`** sub-skill ([models.md](../simics/models.md#alps_touchscreen--i2c-mode))

## See Also
- **`fv-thc/registers`** — PORT_TYPE register, I2C APB sub-IP register init sequence
- **`fv-thc/dma`** — I2C DMA mode, TXDMA for output reports, RXDMA for input
- **`fv-thc/platform`** — Per-platform I2C BOM devices, BIOS prerequisites
- **`fv-thc/power`** — I2C power states (ON/SLEEP), D3 save/restore of I2C regs, PM callback differences
- **`fv-thc/debug`** — I2C-specific failure signatures, NAK/clock stretch debug
- **`fv-thc/simics`** — Simics I2C model (alps_touchscreen), BIOS config, touch injection, transactors, debug
- **`fv-thc/driver`** — Windows HIDI2C driver, Linux QuickI2C driver (6.20+)
- **`fv-thc/hidspi`** — Compare SPI vs I2C: PCI Device IDs, power states, auto-suspend, probe order
- **`fv-thc/wot`** — Wake-on-Touch over I2C: vGPIO wake path, PADCFGLOCK requirements, WoT-aware suspend (skips SET_POWER(SLEEP)), I2C sub-IP save/restore for D3Cold
- **[linux.md](linux.md)** — Linux QuickI2C implementation details (probe, PM, state machine, timing)
- **[windows.md](windows.md)** — Windows HIDI2C implementation details (init, queues, workarounds, registry)
