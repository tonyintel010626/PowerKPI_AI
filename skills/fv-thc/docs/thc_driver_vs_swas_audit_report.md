# THC Windows Driver vs SwAS/Skills Comprehensive Audit Report

> **Owner**: Chin, William Willy (`willychi`)

**Date**: 2026-03-06  
**Scope**: HIDSPI (QuickSPI) and HIDI2C (QuickI2C) Windows drivers cross-referenced against SwAS v1 documents and all THC skill files  
**Files Analyzed**: 24 driver source files fully read (~35,000 lines), 2 SwAS documents, 6 skill files, 4 Extension INFs

---

## SECTION 1: DISCREPANCIES (Driver vs SwAS vs Skills)

### D1. GBL_INT_EN ISR Masking — SPI Non-Compliant with SwAS

| Aspect | SwAS Specification | SPI Driver | I2C Driver |
|--------|-------------------|------------|------------|
| ISR masking method | GBL_INT_EN=0 to mask all interrupts | Per-vector masking only (IE_EOF=0, IE_THC_RESET=0, etc.) | GBL_INT_EN=0 in ISR ✅ |
| GBL_INT_EN bit defined? | Yes (bit 31 of THC_M_PRT_INT_EN) | **NOT DEFINED in Hal.h** | Defined at bit 31 ✅ |
| Re-enable in DPC | GBL_INT_EN=1 | Per-vector re-enable via `ChangeInterruptState(true)` | GBL_INT_EN=1 under WdfSpinLock(Read2Lock) ✅ |

**Impact**: SPI driver has a theoretical race window between individual bit clears in the ISR. The SwAS explicitly recommends GBL_INT_EN as the atomic global mask. SPI Hal.h doesn't even define the bit.

**Skill Status**: Not documented in any skill file.

### D2. HIDSPI Offset Collision — THC_M_PRT_SPI_ICRRD_OPCODE and THC_M_PRT_SPI_DMARD_OPCODE

Both registers are defined at offset 0x14 in SPI Hal.h. This is the ADL-P A1 silicon workaround — the ICRRD opcode register was repurposed for DMA read opcode on A1 stepping. The driver switches between them based on `ADLA1Platf` registry flag.

**SwAS**: Documents them as separate registers at different offsets.  
**Driver**: Overlays them at the same offset with runtime selection.  
**Skill Status**: Documented in driver/SKILL.md under ADL-P A1 workaround.

### D3. FATAL_ERR_INT_EN Bit Width Mismatch

| Register | SPI Hal.h | I2C Hal.h |
|----------|-----------|-----------|
| THC_M_PRT_INT_EN.FATAL_ERR_INT_EN | 8-bit field (bits 16-23) | 1-bit field (bit 16) |

**Impact**: SPI enables 8 individual fatal error interrupt bits; I2C enables a single aggregate fatal error interrupt. This reflects different THC IP revisions but is not documented anywhere.

**Skill Status**: Not documented.

### D4. TX_EMPTY_CTRL Programming (I2C)

| Aspect | SwAS Init Sequence | I2C Driver (Hal.cpp) |
|--------|-------------------|---------------------|
| IC_CON.TX_EMPTY_CTRL | Set to 1 | Set to 0 |

**SwAS Step**: "IC_CON: IC_SLAVE_DISABLE=1, IC_RESTART_EN=1, TX_EMPTY_CTRL=1, MASTER_MODE=1"  
**Driver**: `con.fields.TX_EMPTY_CTRL = 0;` (Hal.cpp I2C init)

**Impact**: TX_EMPTY_CTRL=0 means TX_EMPTY is set when FIFO is completely empty; =1 means set when FIFO is at or below TX_TL threshold. Driver uses a simpler model.

**Skill Status**: hidi2c/SKILL.md lists IC_CON programming but doesn't specify TX_EMPTY_CTRL value.

### D5. Missing I2C Sub-IP Register Programming

The SwAS specifies these registers in the init sequence, but the driver does **NOT** program them:

| Register | SwAS Value | Driver Status |
|----------|-----------|---------------|
| IC_SDA_SETUP | "tSU;DAT" timing | Not programmed (uses silicon default) |
| IC_FS_SPKLEN | Fast-speed spike suppression | Not programmed |
| IC_HS_SPKLEN | High-speed spike suppression | Not programmed |

**Impact**: Driver relies on silicon power-on defaults for these timing parameters. Could cause issues on platforms where defaults don't match BOM device requirements.

**Skill Status**: hidi2c/SKILL.md mentions "IC_DMA_RDLR ≤ 7" but does not call out these missing registers.

### D6. SDA_STUCK_RECOVERY_ENABLE — Driver-Only Feature

The I2C driver sets `IC_ENABLE.SDA_STUCK_RECOVERY_ENABLE = 1` during initialization. This is **NOT** mentioned in the SwAS init sequence at all.

**Impact**: This enables hardware-assisted SDA stuck recovery. It's a defensive measure added by the driver team, likely based on field experience.

**Skill Status**: Not documented in any skill file.

### D7. DEFAULT_MAX_PACKET_SIZE Divergence

| Constant | SPI | I2C | Unit |
|----------|-----|-----|------|
| DEFAULT_MAX_PACKET_SIZE | 128 | 256 | 16-byte units |
| Actual byte size | 2,048 | 4,096 | bytes |

**SwAS**: Both SwAS documents say "up to 4KB" as maximum.  
**Impact**: SPI's default is half the I2C default. This may cause fragmentation for SPI devices with large reports.

**Skill Status**: dma/SKILL.md mentions "MaxPacketSize from device descriptor" but not the defaults.

### D8. DEFAULT_RESET_MS_TIMEOUT Divergence

| Constant | SPI | I2C |
|----------|-----|-----|
| DEFAULT_RESET_MS_TIMEOUT | 1,000 ms | 5,000 ms |

**Impact**: I2C devices get 5x more time to complete reset. This reflects I2C devices generally being slower to initialize.

**Skill Status**: Not documented.

### D9. LTR Default Value Divergence

| Constant | SPI | I2C |
|----------|-----|-----|
| DEFAULT_ACTIVE_LTR | 5 (5 × 1024ns = 5.12µs) | 0x03FF (raw register value) |
| DEFAULT_IDLE_LTR | 40,000 (40ms) | 0xC351 (raw register value) |

**Impact**: Different encoding conventions — SPI uses decoded values, I2C uses raw register values. Could cause confusion during cross-driver debugging.

**Skill Status**: power/SKILL.md documents LTR concepts but not specific default values.

---

## SECTION 2: MISSING FROM SKILLS (Items in Driver Not Covered by Skills)

### M1. ChangeInterruptState (SPI) — Quiesce/Unquiesce Core Mechanism

The SPI driver's primary interrupt management function `ChangeInterruptState(bool)` is called 47 times across Queue.cpp, Hal.cpp, Dma.cpp, and Device.cpp. It controls:
- Quiesce (false): Disables IE_EOF, IE_THC_RESET, IE_RX_FIFO_OVERFLOW on each DMA channel
- Unquiesce (true): Re-enables all the above plus programs RXDMA2_THROTLE_THRESHOLD=8

**Skill gap**: dma/SKILL.md discusses quiesce conceptually but doesn't document this as SPI's central mechanism.

### M2. IRQL-Aware Write Dispatch (SPI Queue.cpp)

SPI Queue.cpp checks `KeGetCurrentIrql() < DISPATCH_LEVEL` before deciding whether to write inline or queue a work item. This is because `WriteRequestToTxDma` requires PASSIVE_LEVEL for WDF I/O target operations.

**Skill gap**: Not documented anywhere.

### M3. HidSpiCx Queue Architecture (SPI)

SPI driver does NOT create a default queue — HidSpiCx framework manages it. SPI creates:
- `InputQueue` — for HidSpiCx CX input reports
- `OutputQueue` — for HidSpiCx CX output reports
- `TxQueue` — for DMA write operations

I2C driver creates its own default queue with `EvtIoDeviceControl`.

**Skill gap**: driver/SKILL.md mentions framework differences but not queue architecture.

### M4. EnableTxQueueThreadWA (I2C Queue.cpp)

Registry-controlled flag that creates a separate `TxThreadQueue` (manual dispatch, power-unmanaged) with a dedicated kernel thread signaled via `threadTxQueueEvent`. This is an alternative Tx IOCTL serialization mechanism.

**Skill gap**: Not documented in any skill file.

### M5. SmartFilter Extension INF Configuration

SmartFilter is enabled via Extension INF setting `SmartFilterEnabled=1` and `DisplaySyncEventSource=2`. The I2C driver reads these registry values and appends `IntelSmartFilterReportDescriptor` to the device's report descriptor.

**Skill gap**: driver/SKILL.md mentions smart filter exists but doesn't document the Extension INF mechanism or DisplaySyncEventSource values.

### M6. MSFT G5 Panel Workarounds Bitmask

`MSFT_G5_ThcExtension.inf` sets `Workarounds=0x03` for DEV_98D0/98D1 (ICL). This bitmask (bits 0 and 1) enables specific workarounds for the Microsoft G5 panel.

**Skill gap**: Not documented. The 0x03 bitmask meaning is not clear from any documentation.

### M7. I2C Report Descriptor Validation

I2C ThcHid.cpp validates that the last byte of the report descriptor is 0xC0 (HID End Collection marker). SPI does NOT perform this validation.

**Skill gap**: Not documented in any skill file.

### M8. I2C Report ID Encoding (HSD 14021506058)

When reportId >= 15, I2C uses the optional 3rd-byte encoding per HID-over-I2C spec. The condition was fixed from `<=15` to `<15`. This is a protocol-level detail.

**Skill gap**: hidi2c/SKILL.md doesn't document this encoding detail.

### M9. I2C SetReport Immediate Completion

I2C `SetReport` completes immediately after sending to device — "A I2C device will not send the response of Set Feature request so a driver needs to complete the request." SPI forwards to PendingQueue and waits for device response.

**Skill gap**: Not documented as a behavioral difference.

### M10. POINTER_WRAPAROUND Constants

| Constant | SPI (Dma.cpp) | I2C (ThcHid.cpp) | I2C (Dma.cpp) |
|----------|---------------|-------------------|----------------|
| WRAPAROUND_VALUE | 0x80 (128) | 0x80 (128) | 0x90 (144) alternate |

I2C Dma.cpp uses `WRAPAROUND_VALUE_0X90 = 144` as an alternate wraparound value in `UpdateWritePointer`.

**Skill gap**: dma/SKILL.md doesn't document wraparound constants or the alternate value.

### M11. D0ExitPreInterruptsDisabled (I2C Only)

I2C has `EvtDeviceD0ExitPreInterruptsDisabled` callback that sends SET_POWER sleep command to device BEFORE interrupts are disabled. SPI does NOT have this callback — it handles everything in D0Exit.

**Skill gap**: power/SKILL.md doesn't document this I2C-specific power transition step.

### M12. DMA Stall Recovery (I2C Only)

I2C has `ScheduleDmaReconfigureFlowWorkItem` with `DmaReConfigureLock` (InterlockedCompareExchange-based). When `buffersLeft==0`, stops START bits, resets TPCPR, and schedules DMA reconfigure. SPI does not have an equivalent.

**Skill gap**: dma/SKILL.md doesn't document stall recovery.

---

## SECTION 3: ECO/WORKAROUND CATALOG

### Documented in Skills (16 items)

| # | HSD/Name | Driver | Description | Skill Reference |
|---|----------|--------|-------------|-----------------|
| 1 | ADL-P A1 Opcode Fix | SPI | ADLA1Platf registry flag, offset 0x14 collision | driver/SKILL.md |
| 2 | HSD 14016760177 | SPI | CS wake pulse before SET_POWER_ON | driver/SKILL.md |
| 3 | SpiBusLock NO-OP | SPI | Empty acquire/release (vs I2C real I2CBusLock) | driver/SKILL.md |
| 4 | Wacom Fabrication | Both | Hardcoded report descriptor for Wacom devices | driver/SKILL.md |
| 5 | bAwaitingSendSetPowerOnResponse | SPI | SET_POWER_ON pending response tracking | driver/SKILL.md |
| 6 | HSD 15014216513 | I2C | I2C bus lock serialization | driver/SKILL.md |
| 7 | HSD 16019682677 | Both | Error recovery flow | driver/SKILL.md |
| 8 | HSD 16020370654 | Both | Reset flow refinement | driver/SKILL.md |
| 9 | HSD 16020586422 | I2C | TxQueue Stop/Start around HandleTxHidIoctl | driver/SKILL.md |
| 10 | HSD 16023244313 | I2C | Recovery flow improvements | driver/SKILL.md |
| 11 | HSD 16023606602 | I2C | Power state management | driver/SKILL.md |
| 12 | HSD 16023750028 | Both | DMA configuration | driver/SKILL.md |
| 13 | HSD 16024143384/146412/165031 | Both | Multiple related fixes | driver/SKILL.md |
| 14 | Hynitron THAT Trackpad | I2C | Special SWDMA handling | driver/SKILL.md |
| 15 | HSD 16024309461 | I2C | Partial documentation | driver/SKILL.md |
| 16 | NoOutputReportAck | SPI | Device flag check for output report completion | hidspi/SKILL.md |

### NOT Documented in Skills (11 items) — RECOMMENDED FOR ADDITION

| # | HSD/Name | Driver | File:Line | Description |
|---|----------|--------|-----------|-------------|
| 17 | **ECO EWOG=1** | SPI | Hal.cpp:~1580 | EWOG (Early Wake On GPIO) bit set during init. Purpose unclear from code alone. |
| 18 | **HSD 16015806448** | SPI | Hal.cpp | Related to interrupt handling timing |
| 19 | **HSD 22016570720** | SPI | Queue.cpp:602-604, 765-767 | **Race condition → Error Code 43**. Fix: Commented-out IE_EOF re-enable after SET_POWER_ON. Leaving IE_EOF disabled at that point prevents race. |
| 20 | **HSD 14021506058** | I2C | ThcHid.cpp:1153 | Report ID encoding fix: changed `<=15` to `<15` for 3rd-byte encoding threshold |
| 21 | **HSD 16018918669** | I2C | Hal.cpp | Related to DMA configuration |
| 22 | **HSD 16021402362** | I2C | Hal.cpp | Related to interrupt state management |
| 23 | **HSD 16023561690** | I2C | Dma.cpp | DMA flow workaround |
| 24 | **HSD 16023816174** | I2C | Dma.cpp | DMA configuration workaround |
| 25 | **HSD 16024189402** | I2C | Device.cpp | Device initialization workaround |
| 26 | **HSD 16024259234** | I2C | Swdma.cpp | SWDMA flow workaround |
| 27 | **HSD 15016076869 / 16024070256** | I2C | Swdma.cpp | Combined SWDMA workarounds |
| 28 | **HSD 16021846070** | I2C | Dma.cpp | Switches to edge-triggered interrupts during FW flash (EnableFWFlashWABOM36 registry) |

### Potential Code Quality Issues (Not HSDs)

| # | Issue | Driver | File:Line | Description |
|---|-------|--------|-----------|-------------|
| A | **DbgBreakPoint() in production** | SPI | Dma.cpp:1332 | Active `DbgBreakPoint()` call — will BSOD on checked builds |
| B | **DbgBreakPoint() commented out** | I2C | Dma.cpp:1391 | Same location, but commented out — I2C team caught it |
| C | **DbgPrintEx(0,0,...) in production** | I2C | Dma.cpp (SmartFilterDriverCompleteReadRequest) | Debug print left in production code path |
| D | **Truthy constant in condition** | SPI | Queue.cpp:588,751 | `((uint32_t)OUTPUT_REPORT_HEADER_VAL::REPORT_TYPE::command_content)` evaluates to 7 (always truthy). Condition `if (7 && ...)` is equivalent to `if (...)` — works but is a coding error |

---

## SECTION 4: KEY CONSTANTS COMPARISON TABLE

### DMA Constants

| Constant | SPI Value | I2C Value | SwAS Value | Notes |
|----------|-----------|-----------|------------|-------|
| DEFAULT_MAX_PACKET_SIZE | 128 (2KB) | 256 (4KB) | Up to 4KB | SPI is half of I2C |
| DEFAULT_PRD_TABLE_SIZE_IN_ENTRIES | 256 | 256 | — | Match |
| RXDMA2_THROTLE_THRESHOLD | 8 | 8 | 8 of 16 | Match ✅ |
| WRAPAROUND_VALUE | 0x80 (128) | 0x80 (128) | — | Match |
| WRAPAROUND_VALUE_0X90 | N/A | 0x90 (144) | — | I2C alternate |
| UseWriteInterrupts | false (default) | false (default) | — | Match |

### Power Management Constants

| Constant | SPI Value | I2C Value | Notes |
|----------|-----------|-----------|-------|
| DEFAULT_ACTIVE_LTR | 5 (5.12µs) | 0x03FF | Different encoding |
| DEFAULT_IDLE_LTR | 40,000 (40ms) | 0xC351 | Different encoding |
| IdleTimerPeriod | 200ms (INF) | 50ms (INF) | SPI 4x longer |
| UseD3HotPowerPolicy | 1 (INF) | Not set | SPI only |
| DEFAULT_RESET_MS_TIMEOUT | 1,000 ms | 5,000 ms | I2C 5x longer |

### Touch Configuration States

| State | SPI Value | I2C Value | Notes |
|-------|-----------|-----------|-------|
| TOUCH_ACTIVE_STATE | 0 | 0 | Match |
| TOUCH_IDLE_STATE | 1 | 1 | Match |
| TOUCH_DISABLE_STATE | 2 | 2 | Match |
| TOUCH_HW_READY_STATE | 3 | 3 | Match |
| TOUCH_DISABLE_NO_RESET_STATE | 4 | 4 | Match |
| TOUCH_SENSOR_SLEEP_STATE | 5 | 5 | Match |
| ACTIVE_LTR_STATE | N/A | 6 | **I2C only** |
| LOWPOWER_LTR_STATE | N/A | 7 | **I2C only** |

### ISR/DPC Constants

| Feature | SPI | I2C | Notes |
|---------|-----|-----|-------|
| ISR profiling | Always on | Conditional (ISRDPCProfilingEn) | SPI more verbose |
| DPC re-enable lock | WdfInterruptAcquireLock | WdfSpinLock(Read2Lock) | Different lock types |
| Interrupt masking | Per-vector bits | GBL_INT_EN bit 31 | **Architectural divergence** |

---

## SECTION 5: DEVICE ID COMPARISON

### HIDSPI (QuickSPI) — Main INF + WoT Extension INF

| Platform | Port 1 | Port 2 | Main INF | WoT Extension | Status |
|----------|--------|--------|----------|---------------|--------|
| ADL-LP | 7A50 | 7A51 | ✅ | ✅ | Complete |
| ADL-P | 51D0 | 51D1 | ✅ | ✅ | Complete |
| ADL-N | 54D0 | 54D1 | ✅ | ✅ | Complete |
| RPL-S | 7A58 | 7A59 | ✅ | ✅ | Complete |
| MTL | 7E49 | 7E4B | ✅ | ✅ | Complete |
| MTP-S | 7F59 | 7F5B | ✅ | ✅ | Complete |
| **LNL** | **A849** | **A84B** | **MISSING** | **MISSING** | ❌ Gap |
| **PTL** | **E349** | **E34B** | **MISSING** | **MISSING** | ❌ Gap |
| **PTL-U** | **E449** | **E44B** | **MISSING** | **MISSING** | ❌ Gap |

**Note**: SPI main INF has two install sections:
- `IntelQuickSPI_Device` — ADL-era platforms (sets `ADLA1Platf=1`, installs `WakeLevel` filter)
- `IntelQuickSPI_Device_MTL` — MTL+ platforms (no ADLA1Platf, no WakeLevel filter)

### HIDI2C (QuickI2C) — Main INF + WoT Extension + SmartFilter Extension

| Platform | Port 1 | Port 2 | Main INF | WoT Extension | SmartFilter Extension | Status |
|----------|--------|--------|----------|---------------|----------------------|--------|
| LNL-M | A848 | A84A | ✅ | ✅ | ✅ | Complete |
| ADL-LP (FPGA) | 7A50 | 7A51 | ✅ | ✅ | ✅ | Complete |
| **PTL** | **E348** | **E34A** | **MISSING** | **MISSING** | **MISSING** | ❌ Gap |
| **PTL-U** | **E448** | **E44A** | **MISSING** | **MISSING** | **MISSING** | ❌ Gap |
| **WCL** | **4D48** | **4D4A** | **MISSING** | **MISSING** | **MISSING** | ❌ Gap |

### Legacy/Special Extension INFs

| INF | Platform | Device IDs | Registry Settings |
|-----|----------|------------|-------------------|
| MSFT_G5_ThcExtension.inf | ICL | 98D0, 98D1 | Workarounds=0x03 (bits 0+1) |

### Skill Coverage

**platform/SKILL.md** lists:
- MTL: 7E48/7E49/7E4A/7E4B ✅
- LNL: A848/A849/A84A/A84B ✅
- PTL: E348/E349/E34A/E34B ✅
- PTL-U: E448/E449/E44A/E44B ✅
- ARL: E048/E049/E04A/E04B ✅
- NVL: B848/B849/B84A/B84B ✅

**Gap**: PTL, PTL-U, LNL (SPI), WCL device IDs exist in platform/SKILL.md but are NOT in the driver INF files. This means the skill documents future platforms not yet in the driver.

---

## SECTION 6: RECOMMENDATIONS

### Critical (Should Fix in Skills)

1. **Document GBL_INT_EN architectural divergence** — Add to registers/SKILL.md and driver/SKILL.md explaining that SPI uses per-vector masking while I2C uses GBL_INT_EN. This is the most significant architectural difference between the two drivers and is not documented anywhere.

2. **Add 11 undocumented HSDs** — Items #17-28 from Section 3 should be added to driver/SKILL.md with at minimum the HSD number, affected driver, file location, and one-line description. Priority items:
   - HSD 22016570720 (race condition, Error Code 43) — has user-visible impact
   - HSD 14021506058 (report ID encoding) — protocol correctness
   - HSD 16021846070 (edge-triggered interrupt for FW flash) — affects FW update flow

3. **Document Extension INF mechanism** — Add a new subsection to driver/SKILL.md or platform/SKILL.md explaining:
   - WoT Extension INF structure and WakeScreenOnTouch.HW include
   - SmartFilter Extension INF with SmartFilterEnabled and DisplaySyncEventSource values
   - MSFT G5 Workarounds bitmask (0x03)
   - That Extension INF device IDs must match main INF device IDs

4. **Document TX_EMPTY_CTRL discrepancy** — Add to hidi2c/SKILL.md noting the SwAS says 1, driver uses 0, and explain the behavioral difference.

### Important (Should Add to Skills)

5. **Document missing I2C sub-IP registers** — Add to hidi2c/SKILL.md that IC_SDA_SETUP, IC_FS_SPKLEN, and IC_HS_SPKLEN are NOT programmed by the driver (relies on silicon defaults). Note SDA_STUCK_RECOVERY_ENABLE IS set by driver but not in SwAS.

6. **Document ChangeInterruptState mechanism** — Add to dma/SKILL.md explaining the SPI quiesce/unquiesce pattern, its 47 call sites, and how it differs from I2C's GBL_INT_EN approach.

7. **Add key constants table to driver/SKILL.md** — Include the constants from Section 4, especially the divergent values (DEFAULT_MAX_PACKET_SIZE, DEFAULT_RESET_MS_TIMEOUT, LTR defaults, IdleTimerPeriod).

8. **Document D0ExitPreInterruptsDisabled** — Add to power/SKILL.md explaining this I2C-only callback and why SPI doesn't need it.

9. **Document DMA stall recovery** — Add to dma/SKILL.md explaining I2C's `ScheduleDmaReconfigureFlowWorkItem` and `DmaReConfigureLock` pattern.

10. **Document INVLD_DEV_ENTRY handling divergence** — I2C treats as non-fatal (quiesce + DMA reconfigure), SPI treats as fatal (full recovery). Add to driver/SKILL.md.

### Nice-to-Have (Low Priority)

11. **Document queue architecture differences** — SPI has no default queue (HidSpiCx manages it) with InputQueue/OutputQueue; I2C creates its own default queue. Add to driver/SKILL.md.

12. **Document I2C report descriptor validation** — I2C validates End Collection (0xC0) marker; SPI doesn't. Add to hidi2c/SKILL.md.

13. **Document SmartFilter report handling** — I2C has SMART_FILTER_CONTROL_FEATURE_REPORT_ID and SMART_FILTER_DATA_REPORT_ID. Add to driver/SKILL.md.

14. **Flag code quality issues to driver team**:
    - DbgBreakPoint() in SPI Dma.cpp:1332 (active in production)
    - DbgPrintEx(0,0,...) in I2C SmartFilterDriverCompleteReadRequest
    - Truthy constant condition in SPI Queue.cpp:588,751

### Device ID Gaps (Action Required)

15. **SPI driver needs LNL/PTL/PTL-U device IDs** — A849/A84B, E349/E34B, E449/E44B are in platform/SKILL.md but missing from IntelQuickSPI.inf and WoT_QuickSpiExtension.inf.

16. **I2C driver needs PTL/PTL-U/WCL device IDs** — E348/E34A, E448/E44A, 4D48/4D4A are in platform/SKILL.md but missing from all I2C INF files.

---

## APPENDIX A: Complete File Inventory Analyzed

### HIDSPI Driver Files (Fully Read)
| File | Lines | Key Content |
|------|-------|-------------|
| Hal.h | 2,499 | Register definitions, no GBL_INT_EN |
| Hal.cpp | 3,935 | ISR/DPC, init, ChangeInterruptState, ECO EWOG |
| Device.cpp | 3,095 | D0Entry/Exit, WoT, HidSpiCx integration |
| Dma.cpp | 2,983 | DMA init, PRD, quiesce, DbgBreakPoint |
| Queue.cpp | 1,122 | HSD 22016570720, IRQL dispatch, no default queue |
| ThcHid.cpp | 2,303 | HID IOCTLs, Wacom descriptor, telemetry |
| eds.h | ~200 | PRD_ENTRY, WRITE_DATA_TYPE |
| IntelQuickSPI.inf | 211 | 6 platforms, 2 install sections |

### HIDI2C Driver Files (Fully Read)
| File | Lines | Key Content |
|------|-------|-------------|
| Hal.h | 2,937 | Register definitions, GBL_INT_EN at bit 31 |
| I2CSubIP.h | 968 | I2C sub-IP registers (IC_CON through IC_CLR_SCL_STUCK) |
| Hal.cpp | 4,265 | ISR/DPC, I2C init, recovery, DMA reconfigure |
| Device.cpp | 2,367 | D0Entry/Exit, D0ExitPreInterruptsDisabled, WoT |
| Dma.cpp | 3,414 | DMA init, stall recovery, quiesce, wraparound |
| Swdma.cpp | 2,101 | 14-step SWDMA, THAT trackpad WA |
| Queue.cpp | 764 | HSD 16020586422, TxQueueThread WA |
| ThcHid.cpp | 2,662 | HSD 14021506058, SmartFilter, report validation |
| eds.h | ~200 | Same as SPI |
| IntelQuickI2C.inf | 179 | 2 platforms (LNL, ADL-LP FPGA) |

### Extension INF Files (Fully Read)
| File | Lines | Platforms | Key Settings |
|------|-------|-----------|-------------|
| WoT_QuickSpiExtension.inf | 94 | 6 (ADL through MTP-S) | WakeScreenOnTouch.HW |
| WoT_QuickI2cExtension.inf | 85 | 2 (LNL, ADL-LP) | WakeScreenOnTouch.HW |
| SmartFilter_QuickI2cExtension.inf | 85 | 2 (LNL, ADL-LP) | SmartFilterEnabled=1, DisplaySyncEventSource=2 |
| MSFT_G5_ThcExtension.inf | 56 | 1 (ICL) | Workarounds=0x03 |

### Reference Documents (Fully Read)
| Document | Lines |
|----------|-------|
| quickspi_swas_v1_extraction.md | 1,147 |
| quicki2c_swas_v1_extraction.md | 1,048 |
| thc_windows_driver_diff.md | 423 |

### Skill Files (Fully Loaded and Cross-Referenced)
- registers/SKILL.md
- power/SKILL.md
- dma/SKILL.md
- hidspi/SKILL.md
- hidi2c/SKILL.md
- driver/SKILL.md

---

## APPENDIX B: Summary Statistics

| Metric | Count |
|--------|-------|
| Total driver source lines analyzed | ~35,000 |
| Discrepancies found (driver vs SwAS) | 9 |
| Items missing from skills | 12 |
| ECO/workarounds cataloged | 28 |
| — Documented in skills | 16 |
| — Undocumented (need addition) | 11 |
| — Code quality issues | 4 |
| Device ID gaps (driver vs skills) | 8 platform-port combinations |
| Recommendations generated | 16 |
| — Critical priority | 4 |
| — Important priority | 6 |
| — Nice-to-have | 6 |
