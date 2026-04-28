---
name: fv-thc/debug
description: THC debug and triage flows, failure signatures, debug tools, HSDES sighting database, known errata, Linux kernel fixes
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Debug, Triage & Sighting Reference

Systematic triage flows, common failure patterns, debug tools, HSDES sighting database overview, and known errata.

Windows-specific debug details (WPP, registry, telemetry): see [windows.md](windows.md)

## Systematic Triage Flow

### Phase 1: Identify the Symptom
1. **No touch input** → enumeration failure
2. **Intermittent touch loss** → data path or interrupt issue
3. **Corrupted touch data** → DMA or protocol error
4. **Touch fails after resume** → power management issue
5. **System hang/BSOD** → driver or HW fatal error

### Phase 2: Check Basic Health
1. Verify THC PCI device enumerated (`lspci` / Device Manager)
2. Check THC driver loaded and bound
3. Read global status register for error bits
4. Check interrupt delivery (count, MSI allocation)
5. Verify GPIO pin configuration for INT# line

### Phase 3: Protocol-Level Debug
1. Read protocol-specific status registers
2. Check bus configuration (SPI clock / I2C speed)
3. Use logic analyzer to capture bus traffic
4. Compare waveform against protocol spec

### Phase 4: Root Cause Analysis
1. Cross-reference with known sightings (HSDES)
2. Check platform-specific vs cross-platform
3. Determine fix layer: HW, FW, driver, or BIOS
4. File sighting with complete debug data

## Common Failure Signatures

| Symptom | Likely Cause | Debug Action |
|---------|-------------|--------------|
| THC not in lspci | Device disabled, fuse/strap | Check BIOS, verify fuse, check PMC |
| Enumeration hangs | Device not responding to HID desc | Check bus, logic analyzer, device power |
| No data after enum | Interrupt broken, DMA misconfigured | Check GPIO, MSI, DMA descriptors |
| Intermittent loss | Interrupt lost, DMA overrun | Check coalescing, ring depth, device error |
| Corrupted coordinates | DMA alignment, report parsing | Capture raw DMA buffer, check report desc |
| Touch fails after S3 | Re-init sequence incomplete | Trace resume, register restore, device reset |
| Touch fails after D3 | D3 exit sequence error | Check PME, MMIO restore, D3 exit flow |
| High latency | DMA/interrupt latency | Measure interrupt-to-DMA time, C-state |
| BSOD in THC driver | DMA invalid addr, deadlock | Crashdump, stack trace, DMA desc validity |

## IP-SV Common Debug Scenarios

## Debug Checklist (Triage Shortcut)

1. No device enumerated: Check PCI BDF (`lspci` / Device Manager) → verify BIOS enable, check PMC PG status and fuses, confirm PORT_TYPE in port control register.
2. DMA timeout/stall: Check INT_STS for interrupt delivery → check PRD ring entries, PRD_BA, DMA_CNTRL and DMA pointers → confirm DMA engine ACTIVE bits and interrupts.
3. Corrupted touch data: Capture raw DMA buffer → verify PRD alignment and report parsing → check SPI clock / I2C timings and IO mode / MPS.
4. Device not responding after resume: Validate power sequence and D-state → check register restore order and whether SET_POWER/SET_SENSING sequence was sent.
5. Spurious interrupts: Inspect GPIO polarity and INT_MASK → read INT_CAUSE/TOUCH_INT_CAUSE in ICR to identify source; check debounce and edge-detect enable.
6. BSOD / Bugcheck: Record driver version and BIOS version → search HSDES for known sightings; collect minidump and reproduce with debug-enabled driver.


| Scenario | Symptom | Root Cause | Fix |
|----------|---------|-----------|-----|
| SPI >17MHz fails | No device response | GPIO loopback settings | Check GPIO config, reduce freq |
| Touch fails after hibernation | No touch after S4 | INT# voltage incorrect (should be 1.8V) | Verify INT# level, GPIO pad |
| Duplicate read transactions | Same report read twice | INT edge detect not enabled | Enable `INT_EDG_DET_EN` |
| Init failure | No communication | GPIO output not driving | Check GPIO enable, 1.8V levels |

## Debug Tools

### ITP/DCI Debug
- Use ITP to halt and inspect THC register state
- Read MMIO directly via ITP memory read
- **XDP**: Verified on NVL A0 via XDPA connector (IPC-based)
- **DBC**: Alternative via USB-C
- PySV + namednodes: `pch_thc.port.mem.thc_m_prt_control.port_type.read()`

### Logic Analyzer
- Probe SPI: SCK, MOSI, MISO, CS#, INT#
- Probe I2C: SCL, SDA, INT#
- Trigger on NAK, timeout, glitch

### GPIO Debug
- **GPIOConfig.exe**: CLI/GUI tool for GPIO pad inspection
- THC SPI port 0 typically in Community 4

### OS-Level Debug

**Linux**:
```bash
dmesg | grep -i thc          # Driver messages
cat /proc/interrupts | grep THC  # Interrupt delivery
lspci -vvv -s <BDF>          # PCI config space
evtest / hid-recorder         # HID report verification
```

**Windows**: Device Manager, WinDbg (`!devnode`/`!devobj`), ETW tracing, `pnputil /enum-devices`. See [windows.md](windows.md) for WPP GUIDs, trace flags, and registry keys.

Linux debug infrastructure (additional details):

- Kernel debug helpers: `dev_dbg()`, `dev_err()`, `dev_warn()` used throughout THC kernel driver for dynamic debug logging.
- Enable dynamic debug at runtime: echo "module intel_thc_hid +p" > /sys/kernel/debug/dynamic_debug/control
- Or enable via kernel boot parameter: `dyndbg="module intel_thc_hid +p"`
- No WPP/ETW equivalent in kernel space — use dmesg, dynamic_debug, tracepoints and debugfs for collections.
- DMA debug: inspect `/sys/kernel/debug/dma-buf/` and driver-specific debugfs entries for DMA buffer state and backing information.
- PCI debug: `lspci -vvv -s <BDF>` and `setpci` for config space reads; use `pci_dump` in scripts when available.

## HSDES Sighting Database

### Filing BKM
- **Tenant**: `sighting_central.sighting` (538+ sightings, 353+ open/active)
- **Filing shortcut**: [goto/nvl.newsighting](http://goto/nvl.newsighting)
- **Domain**: `human_input`
- **Submitter Org**: `ingvalidation_itouch`
- **Components**: `hw.thc`, `sw.driver.thc`, `bios`, `fw.pmc`, `fw.ifwi.softstrap`, `doc.has`, `doc.crif`
- **Forums**: `pcd.presighting` (initial) → `pcd.logic` (promoted); `pch.*` for desktop

### HSDES Query Examples
```python
import pysvtools.hsdes as hsdes
hsdes.config('sighting_central.sighting')
results = hsdes.search(
    "title contains 'THC' AND title contains 'NVL' AND status = 'open'",
    showFields='id,title,status,owner,component')
```

### HSDES Search Tips

- Suggested search terms: "THC", "Touch Host Controller", "HIDSPI", "HIDI2C", "QuickSPI", "QuickI2C".
- Key components to filter on: `THC_DMA`, `THC_PIO`, `THC_LTR`, `THC_PM`.
- Tenant: `sighting_central.sighting` (post-silicon sightings). Filter by platform (PTL, LNL, NVL), status (open, resolved), and domain (Touch/HID).
- When triaging, include driver version, BIOS version, BDF, and a short reproduction step in the sighting to accelerate root cause.

### False Positive Filter
Exclude: ACPHY, MPE, HVM, BCPHY, THERMAL, DRNG — not Touch Host Controller.

## Cross-Platform Recurring Patterns

### Pattern 1: THC Blocks S0ix (ALL platforms TGL→NVL)
- TGL: `14011886603` — PMC FW WA
- LKF: `1606864802`
- MTL: `16018940785` — PMC FW WA
- PTL: `15016491839` — PMC FW fix
- NVL: `15018611965` — BIOS default enabled
- **Debug**: Check `pch.pmc.pmu.pg_ip_d3_sts_3` for THC D3 status

### Pattern 2: Dual/Quad SPI Write Failures (TGL→NVL)
- LNL: `14020715290`; PTL: `15016533618`; NVL: `15018791185`
- **Debug**: Test IO modes individually; verify write opcode config

### Pattern 3: S3 Resume Touch Failure (NVL)
- `15018992269` (**OPEN**): BOM52-I2C, RESET GPIO not de-asserted
- `15018909752`: BOM52-SPI, Ubuntu only
- **Debug**: Check GPIO reset pin state after resume

### Pattern 4: Pre-OS VKB Issues (PTL/NVL/WCL)
- VKB not visible/responsive, delayed key press, fails with Dual/Quad SPI
- **Component**: Almost always `bios`

### Pattern 5: PMC FW Workarounds (TGL/MTL/PTL)
- Multiple platforms need PMC FW fixes for THC power
- **Debug**: Check PMC FW version, verify PG status registers

### Pattern 6: THC1-Specific Issues (NVL/LNL/ADP)
- NVL: `15018463626` — THC1 ACPI resource retrieval failure
- NVL: THC1 BDF changed to B:0 D:8 F:0
- **Debug**: Always test THC0 and THC1 independently

### Pattern 7: Telemetry Counter Issues (NVL/WCL)
- NVL: `15018672812` — FG_PR_CNTR stuck at 0
- WCL: `16028044561` — ER counters not incrementing

### Pattern 8: WCL I2C Speed / Pre-OS Issues (WCL PO)
- WCL: `16027559981` — THC0/1 I2C YB at 1MHz (FMP mode). **Root Cause**: 1MHz frequency instability on WCL silicon — I2C bus unreliable at Fast Mode Plus. **Fix**: Lower I2C speed to 100K (SM) or 400K (FM) via BIOS knob or ACPI `connection_speed` override.
- WCL: `16027560205` — THC0/1 Delayed VKB Response Pre-OS all modes. **Root Cause**: BIOS I2C speed configuration delay affecting virtual keyboard responsiveness before OS handoff. **Fix**: Tune BIOS I2C speed config and timing parameters.

### Pattern 9: WCL Power Management / Telemetry Issues (WCL PM/THC)
- WCL: `16027746325` — I2C HID touchpad YB during Sx cycling. Touchpad reports yellow-bang after repeated S3/S4 suspend-resume cycles. Sx power state transitions cause I2C sub-IP state loss or incomplete restore.
- WCL: `16027836554` — THC telemetry counters always reading 0's. All telemetry counters (FG_PR_CNTR, TX_FRM_CNT, ER_CNTR, etc.) read as zero via PMC SSRAM mailbox despite active touch traffic.
- WCL: `16027877982` — ER (Error Rate) telemetry counters not incrementing. Specifically targets error counters — touch works but error monitoring is non-functional. Related to Pattern 7 (`16028044561`).

## Key NVL Sightings (Active)

| ID | Status | Component | Summary |
|----|--------|-----------|---------|
| `15018992269` | **OPEN** | sw.driver | BOM52-I2C S3 resume — RESET GPIO |
| `14025560859` | root_caused | hw.fuse.xml | THC0/1 not PG when disabled |
| `15018463626` | root_caused | bios | THC1 ACPI resource failure |
| `15018611965` | root_caused | bios | THC enabled by default → blocks S0i2 |
| `15018791185` | root_caused | bios | BOM52-SPI Dual/Quad VKB fails |
| `15018909752` | root_caused | sw.driver | BOM52-SPI S3 resume Ubuntu |
| `15018635096` | root_caused | bios | **WoT vGPIO**: NVL-Hx PADCFGLOCK_VGPIO_THC0 locked by BIOS "Force unlock=Disable" → WoT failed. Fix: BIOS NovaLake_2460_22 |
| `16029769688` | **OPEN** | hw.lpss | **WoT IO APIC**: WCL touchpad wake fails after ~10-15 cycles. Two signatures: (1) RTE84 mask stuck, (2) did+edid=0. Mitigation: `ForceIdleTimeout`=0x3 |
| `15019129309` | **OPEN** | sw.driver | **WoT S4 Hibernate**: NVL-Hx system cannot enter hibernate on 2nd cycle with WoT enabled. Under investigation — multiple hypotheses: (1) pad reset type `GpioV2ResetHost` not clearing interrupt latch on S4 resume, (2) APIC-routed interrupt not visible to ACPI GPE, (3) Linux pinctrl driver not restoring NVL vGPIO pad config correctly. HostDeepReset BIOS patch attempted but did NOT fix. Latest attempt: switch pad to SCI/GPE mode + edge trigger + ACPI `_PRW`. Linked FW bug: 15019049216 (`central_firmware.bug`). NVL-only (LNL/PTL/WCL not affected) |
| `15013380739` | root_caused | bios | MTP-S THC WoT not able to wake from S0iX — BIOS config issue |

## Known Errata and Bug Fixes

### Quiesce Enable Isolation (PTL, fixed NVL)
D0i2 PG exit: `quiesce_en_isol` fails to mask interrupts → spurious interrupt delivery.

### GPIO Sync Coalescing Delay (PTL, fixed NVL)
`DISP_SYNC_DELAY` counter uses TCON pulses instead of internal 10μs clock when `THC_TIMESTAMP_EN=0`.
**WA**: Enable `THC_TIMESTAMP_EN=1`.

### Multi-Report Interrupt (LNL Gen4.0, fixed PTL Gen4.1)
Rapid I2C interrupts cause report loss. Use Sonora2 WW08.3+ to test.

### I2C MPS Limitation (LNL/PTL, fixed NVL)
Set `spi_rd_mps = 4096` for HIDI2C mode.

### NVL Buffer Overrun
FIFO depth 4→16→32. Buffer-full at packet 29. Max 14 reports/coalescing window.

### QuickSPI/QuickI2C Non-POR (NVL+)
HSD#16028137599. QuickSPI Non-POR from PTL+, QuickI2C Non-POR from NVL+.

**CCB 16028137599 — Drop Windows THC QuickI2C Driver (Sep 2025)**:
- **Proposal**: Remove Windows QuickI2C driver from NVL and future platforms
- **CVE Impact**: CVE (formerly iVE) post-silicon validation framework fully relies on Windows drivers as primary vehicle. Dropping Windows QuickI2C removes the validation pipeline for THC I2C touch
- **Coverage Gaps if Dropped**: PM cycling (S0ix, Sx, Reset), cold reset cycling, IP PM states (D3, D0i2), THC telemetry — ALL have **zero Linux/Chrome coverage**
- **Quantified Risk**: Manual gap-fill caps at 15 cycles vs 50 automated (3.3× reduction). Design flagged as "huge diff"
- **Additional Risk**: TSMC→Intel process change (PTL→NVL MBL PCD) — eSPI bug discovered from process switch
- **CVE Position**: Do NOT commit to removing Windows QuickI2C for NVL. Will evaluate Linux/Chrome for future programs
- **Affected Products**: All NVL MBL PCD-H (U/H/P/Ax/Am) + RZL MBL
- **Reference Docs**: `nvl_thc_windows_driver_drop_briefing.md`, `nvl_thc_windows_driver_drop_gap_analysis.md`, `nvl_thc_validation_coverage_matrix.md`

### THC Blocking S0ix (Cross-Platform)
Always check `pg_ip_d3_sts_3` bits `thc0_d3_sts(14)`, `thc1_d3_sts(15)`.

### THC S3 Resume GPIO (NVL)
RESET GPIO remains asserted after S3 exit. Sighting `15018992269` (**OPEN**).

### THC Fuse/FD Blocks PG (NVL)
Disabled THC still not power-gated per PMC. Sighting `14025560859`.

### Linux Kernel Fix: INT_EDG_DET_EN (`8fe2cd8`, 6.17)
Prevents duplicate read transactions. Bit 31 of `TSEQ_CNTRL_1`.

### Linux Kernel Fix: I2C Save Pointer (`a7fc15e`, 6.20)
**CRITICAL** for D3Cold SnR on HIDI2C. Wrong pointer arithmetic → wrong registers saved.

### Pre-LNL Double Interrupt Processing (QuickSPI SwAS P0582)
**Platforms**: Pre-LNL (TGL, ADL, MTL).
THC can double-process an interrupt edge transition — the HW sees both the rising and falling edges of the same INT# pulse and processes two read transactions for one device interrupt. **Workaround**: Use level-triggered mode for the first interrupt after reset, then switch to edge-triggered after receiving the reset response. This issue was fixed in LNL Gen4.0+ silicon.
> **Source**: QuickSPI SwAS v1.0, P0582.

### LNL RAW_INT_STS MSI Blocked During Quiesce (QuickSPI SwAS P0587)
**Platforms**: LNL Gen4.0.
When external device interrupts are quiesced (`DEVINT_QUIESCE_EN=1`), `RAW_INT_STS` MSI delivery is blocked — the interrupt status register updates but no MSI is generated. This means SW cannot poll for device interrupts via MSI during quiesce; it must read `RAW_INT_STS` directly via MMIO polling.
> **Source**: QuickSPI SwAS v1.0, P0587. **Debug**: If interrupt-based flows fail during quiesce, switch to MMIO polling of `RAW_INT_STS`.

### Write DMA Errors and Fatal Errors — Unused (QuickSPI SwAS P0635-P0637)
Write DMA errors and Fatal Errors are explicitly documented as **"Unused-errors"** in the QuickSPI SwAS v1.0. Neither the HW nor the SW implements these error paths. If `FATAL_ERR_CAUSE` bits (23:16 of `ERR_CAUSE`) or Write DMA error bits are observed during debug, they should be treated as **spurious** or indicative of a silicon bug rather than a legitimate error condition.
> **Source**: QuickSPI SwAS v1.0, P0635-P0637. **Impact**: Test scripts should NOT write test cases expecting these errors to fire. Debug playbooks should deprioritize these bits when triaging.

### I2C Sub-IP / PIO Errors — SwAS Unused-Errors Nuance (QuickI2C)
QuickI2C SwAS also calls out an unused-errors nuance for some I2C Sub-IP and PIO error paths in specific flow contexts. Treat this as a triage hint: if these bits assert without matching functional symptoms, prioritize correlation with transaction context (SWDMA/PIO sequencing and reset phase) before classifying as root cause.

> **Debug rule**: Do not promote isolated I2C Sub-IP/PIO error bits to primary failure without confirming data-path impact (report loss, timeout, reset failure, or descriptor read failure).

### Interrupt Lock Race Condition Prevention (QuickSPI SwAS P0620-P0622)
The Windows driver DPC acquires the ISR lock (`WdfInterruptAcquireLock`) before enabling IE (Interrupt Enable) bits to prevent a race condition between the ISR and DPC. Without this lock, the ISR could fire on a newly-enabled interrupt source while the DPC is still processing, leading to reentrant interrupt handling or missed interrupt acknowledgment.
> **Source**: QuickSPI SwAS v1.0, P0620-P0622. **Validation**: Verify that test scripts and custom drivers follow the same locking discipline when enabling/disabling interrupt sources.

### Sonora Test Card
Register map: `TOUCH_INT_CAUSE` (0x00), `TEST_CARD_CONTROL` (0x100), `STATUS` (0x104), `PERIODIC_INT_INTERVAL` (0x110), `INT_CONTROL` (0x118), `NUM_INTS_GENERATED` (0x184).
Requires FW WW08.3+ for HIDI2C multi-report interrupt testing.

## Validation Guidance (from HAS)

### Frame Size Limits for Validation
| Parameter | Min | Max (Validation) | Max (EDS/Spec) |
|-----------|-----|-------------------|----------------|
| Frame Size | 64B | 1MB | 16MB |
| uFrame Size | 16B (multiple of 16) | - | - |
| uFrames per Frame | 1 | 64 | - |
| PRD Table Size (RX) | - | 1MB | - |
| PRD Table Size (TX) | - | 64KB | - |

### PRD Entry Alignment Rules
- Non-last PRD entry: MUST be 4KB aligned
- Last PRD entry: Can be 1B to 1MB (spec)
- **RTL Bug 15014172472**: Last entry also requires 4KB alignment in practice

### Validation Best Practices
- Always test with both minimum (64B) and maximum (1MB) frame sizes
- Sweep uFrame sizes: 16B, 32B, 64B, 128B, 256B, 512B, 1KB, 4KB
- Test PRD table with 1 entry, half-full, and full (256 entries max)
- Test circular buffer wraparound at all PRD table counts (1, 64, 128)
- Verify frame coalescing with count=1 (disabled), count=2, count=max

## DFT and Test Requirements (from HAS)

### VISA Debug
- 2 lanes x 8 bits each
- Clock: 100-130MHz
- 5-level VISA tree
- No FW engine, no trigger events, no DTF, no North Peak trace
- DFT Feature: THC supports DFT security plugin for VISA

### Coverage Goals
| Metric | Target |
|--------|--------|
| Stuck-at coverage | 99% |
| At-speed coverage | 95% |

### DFx Chassis Requirements
| Requirement | Status |
|-------------|--------|
| sTAP/wTAP | Not Supported |
| Memory co-location | Mandatory |
| Scan hooks | Mandatory (95% stuck-at, 85% at-speed) |
| LBIST DRC | Optional |
| VISA ULM | Mandatory (v2.13+) |
| DFX Security Plugin | Conditional |
| VISA Security | Conditional |
| All debug hooks in SB | Mandatory |
| Fuse-Puller-Endpoint | Required |
| IOSF-DFX compliance | Mandatory |

### MBIST/PBIST
Refer to SPI Integration Guide for details.

### Array Freeze, MISR
Not applicable to THC IP.

### HVM Tooling
- `dft_spi_clk` used when `dfx_ovrd.SBDCE` (0xC000[2]) is set
- `dft_espi_clk` used when `dfx_ovrd.EBDCE` (0xC000[3]) is set
- No determinism support

## TSI Device Emulation Mode (DFX)

### Purpose
DFX_Mode_En enables internal device emulation for testing without a physical touch device.

### Configuration
| Register | Description |
|----------|-------------|
| DFX_Mode_En | Enable emulation mode |
| TSI_Port_sel | 2-bit port selector |
| DFX_HS_DATA_GEN | HS data generation pattern |
| DFX_MODE_CTL | Mode control |
| DFX_HS_HDR | HS header config |
| DFX_HS_CRC | HS CRC config |
| DFX_TXESC_STATUS | TX escape status |
| DFX_LP_DATA_GEN | LP data generation pattern |
| DFX_TX_LP_HDR | TX LP header |
| DFX_TX_LP_PAYLOAD | TX LP payload |
| DFX_TX_LP_CRC | TX LP CRC |
| DFX_RX_LP_HDR | RX LP header |
| DFX_RX_LP_PAYLOAD | RX LP payload |
| DFX_RX_LP_CRC | RX LP CRC |

### Data Patterns
- PRBS (Pseudo-Random Binary Sequence)
- Constant pattern
- Alternating pattern

### 9-Step Device Emulation Flow
1. Enable DFX mode (DFX_Mode_En = 1)
2. Select target port (TSI_Port_sel)
3. Configure HS data generation pattern
4. Set HS header and CRC
5. Configure LP data generation (if LP mode)
6. Start data generation
7. Monitor TX/RX status registers
8. Verify received data against expected pattern
9. Disable DFX mode

**Note:** This is TSI-specific (DPHY). For SPI/I2C debug without physical device, use SWDMA engine instead.

## Functional and Performance Monitoring Counters

THC provides hardware counters for monitoring and debug:

| Counter | Description |
|---------|-------------|
| RXDMA Doorbells | Count of GuC doorbell rings from RXDMA |
| TX DMA Frames | Total frames transmitted |
| RX DMA Frames | Total frames received |
| TX uFrames | Total micro-frames transmitted |
| RX uFrames | Total micro-frames received |
| Dropped Frames | Frames dropped (overflow/error) |
| TX Touch Packets | Touch packets sent to device |
| RX Touch Packets | Touch packets received from device |
| Device Interrupts | Count of device GPIO interrupts |
| SW Interrupts | Count of software-triggered interrupts |

### Usage
- Counters are read-only, cleared on reset
- Useful for performance profiling and error rate monitoring
- Compare RXDMA Frames vs Device Interrupts to detect missed frames
- Compare TX/RX DMA Frames to detect asymmetric communication issues

## Telemetry Mailbox (PMC SSRAM)

THC telemetry counters are accessible via PMC SSRAM mailbox:

| Parameter | Value |
|-----------|-------|
| **THC0 Mailbox Offset** | `0xEC0` (from PMC SSRAM base) |
| **THC1 Mailbox Offset** | `0xF60` (from PMC SSRAM base) |
| **PMC SSRAM Base** | `0xFE010000` |

### Telemetry Counter Names (per mailbox)
| Offset | Counter | Description |
|--------|---------|-------------|
| +0x00 | `FG_PR_CNTR` | Foreground power request counter |
| +0x04 | `TX_FRM_CNT` | TX frame count |
| +0x08 | `TXDMA_PKT_CNT` | TXDMA packet count |
| +0x0C | `DEVINT_CNT` | Device interrupt count |
| +0x10 | `ER_CNTR` | Error counter |

> **Known Issues**: NVL `15018672812` — FG_PR_CNTR stuck at 0. WCL `16028044561` — ER counters not incrementing.
> **Reading methodology**: Use PySV `tap2sb` or direct MMIO read from `PMC_SSRAM_BASE_ADDR + mailbox_offset + counter_offset`.

## LTR Failure Detection

### LTR Failure Signature
- **Threshold**: `ACTIVE_LTR < 500,000 ns` (500 µs) indicates LTR programming issue
- **LTR Scale Dictionary** (nanosecond conversion):

| Scale Value | Multiplier | Unit |
|-------------|-----------|------|
| 0 | 1 ns | Nanoseconds |
| 1 | 32 ns | 32 Nanoseconds |
| 2 | 1,024 ns | ~1 µs |
| 3 | 32,768 ns | ~32 µs |
| 4 | 1,048,576 ns | ~1 ms |
| 5 | 33,554,432 ns | ~33 ms |

- **Formula**: `LTR_value_ns = LTR_VAL × 2^(5 × LTR_SCALE)`
- **Debug**: Read `THC_M_CMN_LTR_CTRL.LAST_LTR_SENT` to see last LTR message sent to PMC

### LTR Full Sweep Test Methodology
1. Iterate over all 6 LTR scales (0–5)
2. For each scale, test multiple LTR values (1, 50, 100, max)
3. Verify `LAST_LTR_SENT` matches programmed value
4. Verify PMC acknowledges LTR (check S0ix entry capability)

## Fuse RAM Validation

All THC fuses are expected to be `0` in normal operation:
- Read `THC_FUSES` sideband register (SB addr `0x80`, port `0x39`)
- Expected value: `0x00000000`
- Non-zero fuse values indicate manufacturing override (e.g., THC disabled via fuse)
- Related sighting: `14025560859` — THC0/1 not PG when fuse-disabled

## tap2sb Access Method Fallback

For sideband register access, the test scripts use a fallback pattern:
1. **Primary**: `target.tap2sb` (TAP-based sideband access)
2. **Fallback**: `target.sb` (direct sideband access)
3. **Port ID**: `0x39` (THC sideband port)

> **Example**: `fuse_val = target.tap2sb.sbi_read(0x39, 0x80, 0x06)` — reads THC fuses via sideband opcode 0x06.

## Port80 Postcode-Correlated Register Polling

For boot-time debug, THC register state can be correlated with BIOS POST codes:
1. Monitor Port 80 postcodes via TTK3 or logic analyzer
2. At each relevant postcode, dump THC register snapshot
3. Key postcodes to watch: THC PCI enum, BAR assignment, BIOS lock, OS handoff
4. Compare register state transitions against BIOS init checklist (see `fv-thc/platform`)

> **Tool**: `debug_poll_register_change_with_BIOS_port80_postcode.py` in THC test scripts implements this methodology.

## ERR_CAUSE Register — Write-to-Clear Side Effect

The Linux kernel function `thc_print_txn_error_cause()` reads `ERR_CAUSE` bits to log error details. **Important**: `ERR_CAUSE` is a write-to-clear (W1C) register — the act of reading it for debug logging does NOT clear it, but the driver subsequently writes back the read value to clear the bits. This means:
- **Debug reads consume error state** — calling `thc_print_txn_error_cause()` clears the error bits as a side effect
- **Test scripts must capture ERR_CAUSE BEFORE any driver error handler runs**, or the bits will already be cleared
- If debugging via PythonSV, read `ERR_CAUSE` before the driver's ISR/threaded handler processes the interrupt

## SWINT_CNT Double-Reset Workaround

The Linux kernel resets `SWINT_CNT_1` twice during certain DMA initialization flows — once at the start and once after configuration. This appears to be a defensive workaround to ensure the counter is truly zeroed, possibly due to a race condition where the counter could increment between reset and DMA start. Test scripts should verify SWINT_CNT_1 == 0 after DMA init completes.

## Key Register Dump Points for Debug

When performing staged debug dumps collect the following register groups (MMIO / sideband) at each checkpoint (boot, enum, post-resume, error):

- PCI config: DeviceID, VendorID, Command, Status, BAR0, BAR1, PM_CSR/PM_CAP (power capabilities), Link Status
- Port/Port-control: THC_M_PRT_CONTROL (port_type, device enable), THC_M_PRT_STATUS
- SPI config: THC_M_PRT_SPI_CFG (clock divisor, IO mode), SPI opcodes/WR_OPCODE/READ_OPCODE registers
- I2C config: IC_CON, IC_TAR, IC_ENABLE, IC_SS_SCL_HCNT, IC_SS_SCL_LCNT (or FS/HS equivalents), IC_FIFO_CTRL
- DMA state: DMA_CNTRL, PRD_BA (PRD base address), PRD_ENTRY_CNT, PRD_CURRENT_IDX, DMA read/write pointers, DMA ACTIVE/INT_STS bits
- Interrupt/control: INT_STS, INT_EN, INT_MASK, DEVINT_CFG, TOUCH_INT_CAUSE, ICR (INT_CAUSE registers)
- LTR / Power: THC_M_PRT_LTR_CTRL_REG (LP/ACTIVE LTR values), PMCLite status, D-state (PCI power state), PG_IP_D3_STS registers
- Telemetry/Diagnostic: PMC SSRAM mailbox region (PMC_SSRAM_BASE + mailbox offsets), FG_PR_CNTR, TX_FRM_CNT, ER_CNTR
- SmartFilter/Filter status: SmartFilter control flags and last vsync timestamps (when applicable; check debug feature reports)

Collect register snapshots in a consistent order and with timestamping so diffs between stages are clear. Use tap2sb for sideband reads where MMIO is not available.

## Debug Playbooks

### Playbook 1: "Device Not Enumerating"

**Symptom**: THC touch device does not appear in `lspci` / Device Manager. No HID device registered. Touch input completely absent.

**Typical Root Causes**:
1. THC disabled in BIOS or fuse-disabled (HSDES `14025560859`)
2. BAR0 not mapped or PCI command register missing Memory Enable
3. PORT_TYPE misconfigured (SPI vs I2C mismatch)
4. Device not responding to HID descriptor read (NACK, timeout, GPIO wiring)
5. ACPI _DSM missing or returning wrong parameters

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Verify THC PCI device present | **Linux**: `lspci -d 8086: \| grep THC` **Windows**: Device Manager → System Devices | Device ID listed (see `fv-thc/platform` for per-platform DIDs). THC0 typically at Dev:16 Fun:0, THC1 varies (NVL: Dev:8 Fun:0) | Device not in lspci → Step 2 (fuse/BIOS). If present but no HID → Step 6 |
| 2 | Check Function Disable bit | PySV: `pch_thc.port0.cfg.thc_cfg_ur_sts_ctl.fd.read()` **Offset**: PCI config `0x40`, bit FD | `FD = 0` (not disabled) | `FD = 1` → THC is fuse/BIOS disabled. Check BIOS setup. **WARNING**: FD is in `AVOID_THC_BITS` — requires power cycle to recover if set. See sighting `14025560859` (NVL: disabled THC still not PG) |
| 3 | Verify BAR0 mapped and Memory Enable | PySV: `pch_thc.port0.cfg.thc_cfg_bar0_low.read()` **Linux**: `lspci -vvv -s <BDF>` — check "Region 0: Memory" **Offset**: PCI config `0x10` (BAR0_LOW), `0x14` (BAR0_HI), `0x04` (CMD) | BAR0 non-zero, 32KB range. CMD register bit 1 (Memory Space Enable) = 1 | BAR0 = 0 → BIOS did not assign MMIO. CMD bit 1 = 0 → driver not enabled. Check BIOS THC resource allocation |
| 4 | Check PORT_TYPE register | PySV: `pch_thc.port0.mem.thc_m_prt_control.port_type.read()` **Offset**: port base + `0x008`, bits [31:30] | `00` = SPI, `01` = I2C (must match actual device on bus) | Wrong PORT_TYPE → BIOS or ACPI misconfiguration. Also check `PORT_SUPPORTED` (bit 28, RO) — if 0, port not present in silicon |
| 5 | Verify BIOS enabled THC and check power state | PySV: `pch_thc.port0.cfg.thc_cfg_pmd_pmcsrbse_pmcsr.pwrst.read()` **Offset**: PCI config `0x74`, bits [1:0] | `PWRST = 00` (D0 state) | `PWRST = 11` (D3) → device in D3, driver not transitioned to D0. Check PMC PG status: `pch.pmc.pmu.pg_ip_d3_sts_3` bits 14 (THC0) / 15 (THC1) |
| 6 | Check device interrupt GPIO | **GPIOConfig.exe** (Windows) or GPIO pad dump via PySV. Probe INT# line with logic analyzer | INT# line toggling on touch. Voltage = 1.8V. Correct polarity (active-low typical) | No INT# toggle → device not asserting interrupt. Check device power supply (1.8V rail), RESET# pin state. See sighting `15018992269` (NVL: RESET GPIO not de-asserted) |
| 7 | Read HID descriptor via PIO | PySV PIO sequence: Write `0x1048` (SW_SEQ_DATA[0]) = device HID desc register addr → Write `0x1040` (SW_SEQ_CNTRL) = opcode 0x4 (SPI read) or 0x1C (I2C write+read), byte count, TSSGO=1 → Poll `0x1044` (SW_SEQ_STS) for TSSDONE(bit 0). **Timeout**: 1 second | TSSDONE = 1, THC_SS_ERR = 0. Read `0x1048`+ for HID descriptor (first 2 bytes = wHIDDescLength) | TSSDONE timeout → device not responding. THC_SS_ERR = 1 → bus error (NACK on I2C, no MISO response on SPI). Check bus wiring with logic analyzer |
| 8 | Verify ACPI _DSM | **Linux**: `cat /sys/firmware/acpi/tables/DSDT \| iasl -d` and search for THC _DSM. **Windows**: check ACPI tables via RWEverything | _DSM returns valid connection speed, address, GPIO info | Missing _DSM → driver cannot configure bus parameters. Wrong GPIO number → interrupt delivery fails. See `fv-thc/hidspi` and `fv-thc/hidi2c` for required _DSM fields |
| 9 | Check driver load status | **Linux**: `dmesg \| grep -i thc` — look for probe success/failure. **Windows**: Device Manager error codes, `pnputil /enum-devices /problem` | Driver loaded, no error messages | Driver probe failed → check error code. Common: `-ETIMEDOUT` (device not responding), `-ENOMEM` (DMA alloc fail), `-ENODEV` (ACPI resource missing). See sighting `15018463626` (NVL: THC1 ACPI resource failure) |

### Playbook 2: "DMA Timeout / Overrun"

**Symptom**: Touch input stalls or drops frames. DMA errors in logs. `BUF_OVRRUN_ERR` or `STALL_STS` set. Intermittent data corruption.

**Typical Root Causes**:
1. PRD last entry not 4KB-aligned (RTL bug `15014172472`)
2. SPI_RD_MPS not set to 4096 in I2C mode (BUG-002)
3. PRD ring exhaustion (too few entries or slow SW consumer)
4. DMA buffer overrun (NVL FIFO depth: 4→16→32, max 14 reports/coalescing window)
5. Interrupt delivery failure (MSI not configured, GPIO broken)

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Check DMA control status | PySV: `pch_thc.port0.mem.thc_m_prt_read_dma_cntrl_1.read()` **Offset**: port base + `0x10C` (RXDMA1), `0x20C` (RXDMA2) | `START` (bit 0) = 1 (DMA running), `ACTIVE` in INT_STS = 1 | START=0 → DMA not started. ACTIVE=0 with START=1 → DMA stalled. Check STALL_STS |
| 2 | Read interrupt status for error bits | PySV: `pch_thc.port0.mem.thc_m_prt_read_dma_int_sts_1.read()` **Offset**: port base + `0x110` (RXDMA1), `0x210` (RXDMA2) | `DMACPL_STS`(0)=0, `ERROR_STS`(1)=0, `STALL_STS`(3)=0. Only `ACTIVE`(8)=1 | `ERROR_STS`=1 → read DMA_ERR register (`0x114`/`0x214`). `STALL_STS`=1 → PRD ring exhausted, SW not consuming fast enough. `EOF_INT_STS`(5) without `DMACPL_STS`(0) → partial frame received |
| 3 | Read master INT_STATUS and ERR_CAUSE | PySV: `pch_thc.port0.mem.thc_m_prt_int_status.read()` and `pch_thc.port0.mem.thc_m_prt_err_cause.read()` **Offsets**: port base + `0x024` (INT_STATUS), `0x028` (ERR_CAUSE) | INT_STATUS: `TXN_ERR_INT_STS`(28)=0, `FATAL_ERR_INT_STS`(30)=0. ERR_CAUSE: all bits 0 | `BUF_OVRRUN_ERR`(bit 12)=1 → buffer overrun. `INVLD_DEV_ENTRY`(bit 9)=1 → bad device ICR data. `FATAL_ERR_CAUSE`(bits 23:16) non-zero → decode fatal cause (see [windows.md](windows.md) for Windows-specific fatal error bit definitions). **Note**: ERR_CAUSE is W1C — reading for debug does NOT clear it, but driver ISR will clear it |
| 4 | Check PRD ring configuration and 4KB alignment | PySV: `pch_thc.port0.mem.thc_m_prt_rprd_ba_low_1.read()` **Offset**: port base + `0x100` (RPRD_BA_LOW_1). Check RPRD_CNTRL: `0x108` (PTEC field bits 15:8) | PRD base address bits [11:0] = 0 (4KB aligned). PTEC > 0 (has entries). **ALL PRD buffer addresses** must be 4KB aligned (including last entry) | Base not 4KB aligned → DMA will fail. **RTL Bug 15014172472**: last PRD entry ALSO requires 4KB alignment despite HAS saying otherwise. PTEC=0 → no PRD entries configured |
| 5 | Verify DMA buffer sizes and MPS | PySV: `pch_thc.port0.mem.thc_m_prt_spi_cfg.spi_rd_mps.read()` **Offset**: port base + `0x010`, bits [15:7] | For HIDSPI: MPS matches frame size. **For HIDI2C: SPI_RD_MPS MUST be 4096** (9-bit field value = 0x200 = 512 → encodes 4096). See BUG-002 | I2C mode with SPI_RD_MPS < 4096 → DMA reads truncated/corrupted. This is the #1 I2C DMA failure cause. Fix: program `spi_rd_mps = 4096` |
| 6 | Read DMA counters | PySV: read `thc_m_prt_frm_cnt_1` (`0x1A4`), `thc_m_prt_rxdma_pkt_cnt_1` (`0x1AC`), `thc_m_prt_frame_drop_cnt_1` (`0x1B4`) | Frame count incrementing. Drop count = 0 | Drop count > 0 → frames being lost (SW too slow or ring too small). Compare `DEVINT_CNT` (`0x0E8`) vs `FRM_CNT` — mismatch means missed frames |
| 7 | Check interrupt delivery | **Linux**: `cat /proc/interrupts \| grep THC`. PySV: read `thc_m_prt_int_en` (`0x020`) | `GBL_INT_EN` (bit 31) = 1. Interrupt count incrementing in `/proc/interrupts` | GBL_INT_EN=0 → interrupts globally disabled. No interrupt count increase → MSI not configured or GPIO not wired. Check `DEVINT_CNT` register — if incrementing but no OS interrupts, MSI delivery broken |
| 8 | Cross-platform: verify timeout parameters | **Linux** DMA pause: 100µs poll interval, 10ms timeout. **Windows** DMA pause: 10µs poll interval, 1s timeout (from `Dma.h DEFAULT_QUIESCE_POLLING_*`) | Timeout appropriate for platform | Linux 10ms timeout can be too aggressive for slow devices → consider if device needs more time. Windows 1s timeout may mask real hangs. Check `READ_DMA_INT_STS` (not DMA_CNTRL) for stall status — DOC-010 fix |

### Playbook 3: "No Touch After S0ix Resume"

**Symptom**: Touch worked before sleep. After S0ix/S3 resume, no touch input. Device may or may not appear in OS. Common on all platforms TGL→NVL.

**Typical Root Causes**:
1. Register restore incomplete or wrong order after D3 exit
2. I2C sub-IP `IC_CON` not restored (wrong pointer arithmetic — HSDES `a7fc15e`)
3. DMA not re-enabled after resume
4. SET_POWER ON not sent to device
5. LTR config not restored → THC blocks S0ix re-entry (cross-platform pattern: `14011886603`/`16018940785`/`15016491839`/`15018611965`)

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Check current power state | PySV: `pch_thc.port0.cfg.thc_cfg_pmd_pmcsrbse_pmcsr.pwrst.read()` **Offset**: PCI config `0x74`, bits [1:0] | `PWRST = 00` (D0). Device should be back in D0 after resume | `PWRST = 11` (D3) → device stuck in D3. Driver did not transition to D0. Check PMC PG status: `pch.pmc.pmu.pg_ip_d3_sts_3` bits 14/15 for THC0/THC1 D3 status |
| 2 | Verify register restore happened | PySV: read `thc_m_prt_control` (`0x008`), `thc_m_prt_spi_cfg` (`0x010`), `thc_m_prt_int_en` (`0x020`) | PORT_TYPE correct, SPI_CFG matches pre-sleep values, GBL_INT_EN=1. Compare against pre-suspend register snapshot | Registers reset to defaults → Save/Restore (SnR) failed. Check driver SnR implementation. **REVIEW-001**: HAS Appendix A SnR register list may be outdated — verify against RTL. Restore order: config (3.102-3.110) → PIO (3.111-3.130) → DMA (3.131-3.146) → GuC (5.1) |
| 3 | Check IC_CON value (I2C mode) | PySV I2C sub-IP read: PIO opcode `0x12`, address `0x00` (IC_CON) | `IC_CON = 0x0663` (Linux default: Master, Fast mode, 7-bit addr, Restart EN, Slave DIS, RX_FIFO_FULL_HLD_CTRL, STOP_DET_IF_MASTER_ACTIVE) | Wrong IC_CON → I2C sub-IP not re-initialized. **CRITICAL**: kernel commit `a7fc15e` (6.20) fixes D3Cold SnR for HIDI2C — wrong pointer arithmetic caused wrong registers saved. If on kernel < 6.20, this is a known bug |
| 4 | Verify DMA re-enabled | PySV: read `thc_m_prt_read_dma_cntrl_1` (`0x10C`) and `thc_m_prt_read_dma_cntrl_2` (`0x20C`) | `START` (bit 0) = 1 on active channels. PRD base addresses non-zero and 4KB-aligned | START=0 → DMA not restarted after resume. PRD_BA=0 → PRD base not restored. Driver must reprogram DMA after D3 exit |
| 5 | Check interrupt re-armed | PySV: read `thc_m_prt_int_en` (`0x020`), check per-channel `READ_DMA_CNTRL` IE bits | `GBL_INT_EN`(31)=1. Per-channel: `IE_ERROR`(1), `IE_IOC`(2), `IE_STALL`(3), `IE_NDDI`(4), `IE_EOF`(5) set as needed | Interrupt enables cleared → driver did not re-enable after resume. Check `DEVINT_QUIESCE_EN` (PRT_CONTROL bit 1) — if still 1, interrupts are quiesced |
| 6 | Send SET_POWER ON and verify response | **Linux**: driver sends automatically during resume. **Debug**: use PIO to send HID SET_POWER(ON) command. For I2C: via TXDMA (`write_cmd_to_txdma()`). For SPI: via PIO opcode 0x6 | Device ACKs SET_POWER. For HIDI2C: no NACK on I2C bus. For HIDSPI: valid ICR response | No response → device still in sleep/reset state. Check RESET# GPIO — sighting `15018992269` (NVL: RESET GPIO remains asserted after S3). Try explicit device reset via `DEVRST` (PRT_CONTROL bit 3) |
| 7 | Check LTR config restored | PySV: read `thc_m_cmn_ltr_ctrl` (common space `0x14`) | `ACTIVE_LTR_EN`(1)=1, `LP_LTR_EN`(3)=1. `LAST_LTR_SENT` (bits 31:30) shows recent LTR. LTR value > 500µs (below 500µs indicates LTR programming issue) | LTR not restored → THC may block S0ix on next sleep attempt. This is cross-platform pattern #1 (TGL→NVL). Check PMC: `pg_ip_d3_sts_3` for THC D3 status |
| 8 | Check for D3Cold SnR I2C bug | Verify kernel version: `uname -r`. Check if commit `a7fc15e` is present | Kernel >= 6.20, or backport of `a7fc15e` applied | **If kernel < 6.20 and using HIDI2C**: I2C register save uses wrong pointer arithmetic → wrong registers saved/restored during D3Cold. This causes silent corruption of I2C sub-IP state after resume. Upgrade kernel or apply backport |

### Playbook 4: "Wake-on-Touch Not Working"

**Symptom**: System enters S0ix/S3 successfully but does not wake when user touches the screen. Touch works normally when system is awake.

**Typical Root Causes**:
1. WoT not enabled in ACPI _DSM or driver
2. GPIO wake configuration incorrect (wrong pin, polarity, or trigger type)
3. GPIO pad not configured for wake (wrong pin, wrong power domain, not always-on)
4. Platform wake source mask does not include THC touch GPIO
5. Driver did not skip SET_POWER(SLEEP) — touch device asleep, cannot generate wake interrupt

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Verify WoT enabled in ACPI _DSM | **Linux**: check dmesg for WoT enable during suspend, or `cat /sys/power/pm_wakeup_irq`. Verify ACPI _DSM advertises WoT capability. **Windows**: check `powercfg /devicequery wake_armed` for THC device | THC device listed as wake-armed. _DSM returns WoT-capable. Kernel 6.17+ required for Linux WoT support (KERN-003) | Not wake-armed → check ACPI _PRW / _DSM for wake support flag. Linux < 6.17 → WoT not supported. Windows: check registry `THC_WORKAROUNDS` bit 3 (`DisableDoze`) — if set, doze disabled which may affect wake. See [windows.md](windows.md) for full registry reference |
| 2 | Check GPIO wake configuration | PySV: dump GPIO pad config for THC INT# pin (typically Community 4 for SPI port 0). **GPIOConfig.exe** on Windows | GPIO pad: Wake Enable = 1. Trigger = Edge (not Level for SPI, per kernel fix `8fe2cd8`). Polarity matches device (active-low typical). `INT_EDG_DET_EN` (TSEQ_CNTRL_1 bit 31) = 1 | Wake Enable = 0 → GPIO not configured for wake. Wrong polarity → wake fires continuously or never. Missing `INT_EDG_DET_EN` → duplicate reads or missed interrupts (fixed in kernel 6.17 commit `8fe2cd8`) |
| 3 | Verify GPIO pad wake config | PySV: Read GPIO pad config for THC touch INT# pin. Check pad is in **always-on power domain** (not gated with THC). Verify `Wake Enable = 1` in pad config. **Note**: WoT wake path bypasses THC entirely — goes through GPIO IP (vGPIO) → PMC. THC PCI caps: WAKE=No, PME=No | GPIO pad: Wake Enable = 1, pad in always-on domain. vGPIO routed to PMC wake. THC MMIO will be inaccessible (power-gated) — this is expected and correct | Wake Enable = 0 → GPIO pad not configured for wake. Pad in gated power domain → wake signal lost during PG. Check BIOS WoT knob enabled. Check ACPI _DSM for wake-on-touch capability flag |
| 4 | Check driver suspend behavior | **Linux**: dmesg for `device_may_wakeup` result during suspend. If WoT enabled, driver must SKIP `SET_POWER(SLEEP)` so touch device stays responsive. **Windows**: check `armForWake` flag in driver trace, `TSEQ_CNTRL_1.EWOG` bit set before D3 | WoT: SET_POWER(SLEEP) skipped (Linux), EWOG=1 + ARM_FOR_WAKE TIC state (Windows). Touch device stays awake to generate interrupt | SET_POWER(SLEEP) sent → touch device asleep, cannot generate wake. EWOG=0 (Windows) → WoT Extension INF not installed or WoT BIOS knob disabled |
| 5 | Verify platform wake source | **Linux**: `cat /sys/power/pm_wakeup_irq` after failed wake attempt. **Windows**: `powercfg /sleepstudy` or `powercfg /lastwake` | Wake source = THC GPIO IRQ number | Different wake source → THC GPIO not triggering. No wake source → system did not detect any wake event. Check if GPIO interrupt fires at all with logic analyzer on INT# pin during touch |
| 6 | Check GPIO interrupt polarity and trigger | PySV GPIO pad register read for INT# pin: check `INTSEL`, `RXINV`, `RXEV` (edge/level select) fields | `RXEV` = Edge-triggered (01 or 10). `RXINV` matches device output polarity. `INTSEL` routes to correct IRQ | Level-triggered on SPI → known issue, causes duplicate transactions. Edge-detect on I2C may miss rapid interrupts (see Multi-Report Interrupt errata: LNL Gen4.0, fixed PTL Gen4.1) |
| 7 | Verify power gating state allows wake | PySV: read `thc_cfg_pce` (PCI config `0xA2`): HAE(5), D3HE(2) | `HAE=1`, `D3HE=1` (BIOS requirement per BWG). When in D3 with HAE=1, PGCB can request PG but GPIO wake path must remain powered | `HAE=0` → no HW autonomous PG (device stays powered but wastes power). `D3HE=0` → no PG on D3-Hot. Check if GPIO pad is in an always-on power domain |
| 8 | **Check vGPIO pad lock state** | PySV: read `PADCFGLOCK_VGPIO_THC0` for relevant THC port. **Must be 0x0 (unlocked)** for WoT. Also check `PADCFGLOCKTX_VGPIO_THC0` | `PADCFGLOCK=0x0` (unlocked). Driver/OS can control vGPIO pad for WoT wake | `PADCFGLOCK=0x1` → BIOS locked vGPIO pad, WoT will fail. **Known root cause**: BIOS "Force unlock on all GPIO pads" = Disable locks vGPIO_THC pad. See HSD `15018635096` (NVL), fix: BIOS update. PTL not affected (stays 0x0 regardless). WCL: check HSD `16028429994` |

### Playbook 5: "BSOD / Driver Crash"

**Symptom**: System crashes with Blue Screen of Death (Windows) or kernel panic/oops (Linux). Crash occurs during touch usage, suspend/resume, or driver init.

**Typical Root Causes**:
1. DMA accessing invalid/freed memory (NULL pointer in PRD, buffer overrun)
2. NULL pointer dereference in filter callback (SmartFilter/IPTS path)
3. Timeout in PIO path leading to use-after-free or deadlock
4. Driver accessing registers while device in D3 (output_report PM gap — DOC-015)
5. Known HSDES workaround not applied (see [windows.md](windows.md) for Windows driver HSDES workarounds)

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Identify bugcheck code / crash signature | **Windows**: `!analyze -v` in WinDbg on minidump. Note BugCheck code (e.g., `KERNEL_MODE_HEAP_CORRUPTION`, `IRQL_NOT_LESS_OR_EQUAL`, `PAGE_FAULT_IN_NONPAGED_AREA`). **Linux**: `dmesg` for stack trace, `journalctl -k -b -1` for previous boot | Crash signature with faulting module (e.g., `IntelTHCBase.sys`, `QuickSPI.sys`, `QuickI2C.sys`, `intel-thc-hid.ko`) | If faulting module is NOT THC driver → may be a filter driver or other component. Check if IPTS filter driver is loaded (GUID `{A2BCAC85-68F6-41B2-B112-DE4EA74770C6}`) |
| 2 | Enable and collect WPP/debug traces | **Windows**: See [windows.md](windows.md) for WPP GUIDs (HIDSPI: `{A891081A...}`, HIDI2C: `{C47236A7...}`). Use `tracelog -start thc -guid #<GUID> -f thc.etl -flag 0xFFFF -level 5`. **Linux**: `echo "module intel_thc_hid +p" > /sys/kernel/debug/dynamic_debug/control` | Trace captured before crash reproduction. Stop with `tracelog -stop thc`. Decode with `tracefmt thc.etl` | Cannot reproduce → collect ETW telemetry: `logman start thc_etw -p {937AD94E-CA8D-4B8E-8143-3FCE4ACCB8CB} -o thc_etw.etl -ets`. Linux: also enable `dyndbg="module intel_thc_hid +p"` on boot cmdline |
| 3 | Check if crash in DMA path | Examine crash stack for DMA-related functions: `thc_dma_*`, `Dma::*`, PRD setup, buffer allocation. Check `ERR_CAUSE` (`0x028`): `BUF_OVRRUN_ERR`(12), `PRD_ENTRY_ERR`(13), `FATAL_ERR_CAUSE`(23:16) | Stack trace identifies specific DMA function. ERR_CAUSE captured before driver ISR clears it | `BUF_OVRRUN_ERR` → NVL FIFO overrun (max 14 reports/coalescing window). `PRD_ENTRY_ERR` → bad PRD descriptor (check 4KB alignment — RTL bug `15014172472`). Windows HSDES `16023750028`: DMA stall on S4 resume → RXDMA2 ACTIVE==0 with non-zero equal pointers |
| 4 | Check for NULL pointer dereference | **Windows**: Check if crash at offset 0x0-0x1000 (NULL page). Look for Elan trackpad VID/PID if `INVLD_DEV_ENTRY` BSOD (HSDES `16024259234`). **Linux**: check oops for "BUG: kernel NULL pointer dereference" | Stack trace shows specific NULL access location | Windows Elan trackpad NULL pointer → apply HSDES `16024259234` WA (VID/PID-specific null check). Filter callback NULL → check SmartFilter sensor function stubs (9 functions are stubs in filter driver). Linux `output_report()` PM gap (DOC-015): no `pm_runtime_get/put` → device could be in D3 during output report |
| 5 | Check for PIO timeout | Look for PIO-related crash: `thc_pio_*`, `SW_SEQ` in stack. PIO timeout = 1 second (`THC_PIO_DONE_TIMEOUT_US = USEC_PER_SEC`). Read `SW_SEQ_STS` (`0x044`): `THC_SS_CIP`(3)=1 means PIO stuck | `TSSDONE`(0)=1 and `THC_SS_ERR`(1)=0 → PIO completed OK | `THC_SS_CIP`(3)=1 after timeout → PIO cycle hung. Device not responding on bus. Check if DMA was running during PIO (HAS RULE: no PIO to bulk address space while RXDMA running). Windows HSDES `16023244313`: quiesce failure during continuous touch → need 300µs delay before + 700µs delay after quiesce |
| 6 | Verify driver version and check known sightings | **Windows**: `driverquery /v \| findstr -i thc`. Check `IntelTHCBase.sys` version. Current: HIDSPI v4.0.0.9000, HIDI2C v3.0.0.9000. **Linux**: `modinfo intel-thc-hid` | Driver version identified | Search HSDES for crash signature: `pysvtools.hsdes.search("title contains 'THC' AND title contains 'BSOD' AND status = 'open'")`. Key Windows BSOD sightings: `16023750028` (S4 resume DMA stall), `16024309461` (INVLD_DEV_ENTRY during FW flash), `16023561690` (S5 resume — WdfInterruptAcquireLock not in D0). See [windows.md](windows.md) for full workaround list |
| 7 | Collect full debug data for sighting | Collect: (1) minidump/vmcore, (2) WPP/dmesg traces, (3) driver version, (4) BIOS version, (5) THC register snapshot (see Key Register Dump Points section), (6) BDF, (7) reproduction steps | Complete data package for HSDES filing | File sighting at [goto/nvl.newsighting](http://goto/nvl.newsighting). Tenant: `sighting_central.sighting`. Domain: `human_input`. Submitter Org: `ingvalidation_itouch`. Include register dump, trace log, and repro steps per HSDES Filing BKM section above |
| 8 | Check Windows registry workarounds | See [windows.md](windows.md) for complete registry reference and THC_WORKAROUNDS bitfield. `reg query "HKLM\SYSTEM\CurrentControlSet\Enum\PCI\...\Device Parameters" /v THC_WORKAROUNDS` and `/v Workarounds` | Value identifies active workarounds | Non-zero → workarounds active. Check if relevant WA bit is missing: bit 6 `DisableIntCauseBadReset` may prevent crash-on-bad-INT_CAUSE. HSDES `14016760177`: `UseWriteInterrupts=false` (poll instead, 100µs interval, 500ms timeout) |

---

> **Simics-specific debugging** (WinDbg over Simics, console log levels, ETL tracing, model sightings, unit tests, touch injection, file transfer) → See **`fv-thc/simics`** sub-skill ([operations.md](../simics/operations.md))

---

## Validation Points (Debug & Triage)

| ID | Check | Method | Pass Criteria |
|----|-------|--------|---------------|
| VP-DBG-001 | 4-phase triage narrows to specific subsystem | Run systematic triage (PCI → MMIO → Protocol → DMA → Interrupt → Data) on known-bad config | Each phase eliminates ≥1 root cause category; final phase identifies specific failure point |
| VP-DBG-002 | Key register dump captured before ISR clears status | Read `ERR_CAUSE` (0x028), `INT_STS` (0x0E4), `READ_DMA_CNTRL_x` before driver handles interrupt | All error/status bits captured with timestamps; `ERR_CAUSE` reflects original error, not post-ISR cleared state |
| VP-DBG-003 | HSDES sighting search returns relevant matches | Search HSDES with crash signature keywords (tenant: `sighting_central.sighting`, domain: `human_input`) | Known sightings returned within 10 results; key sightings: `16023750028` (S4 DMA stall), `16024309461` (INVLD_DEV_ENTRY), `16023561690` (S5 resume lock) |
| VP-DBG-004 | WPP/trace collection captures pre-crash events | Enable WPP (HIDSPI: `{A891081A...}`, HIDI2C: `{C47236A7...}`) at level 5, reproduce crash | Trace file contains ≥100 events before crash; DMA/PIO/interrupt transitions visible in decoded trace |
| VP-DBG-005 | Driver version correctly identified | `driverquery /v \| findstr -i thc` (Windows) or `modinfo intel-thc-hid` (Linux) | HIDSPI v4.0.0.9000, HIDI2C v3.0.0.9000 (Windows); kernel module version matches running kernel (Linux) |
| VP-DBG-006 | Debug bundle contains all required artifacts | Collect per Playbook step 7: minidump/vmcore, WPP/dmesg, driver version, BIOS version, register snapshot, BDF, repro steps | All 7 artifacts present; register snapshot includes at minimum: `THC_M_PRT_CONTROL`, `ERR_CAUSE`, `INT_STS`, `READ_DMA_CNTRL_1/2`, `WRITE_DMA_CNTRL`, `SW_SEQ_STS` |
| VP-DBG-007 | Windows registry workaround lookup covers known WAs | Query `THC_WORKAROUNDS` and `Workarounds` registry values under THC PCI device parameters | Known WA bits documented: bit 6 `DisableIntCauseBadReset`, `UseWriteInterrupts=false` (HSD 14016760177). Non-zero value → identify which WA bits are active |

## See Also
- **[windows.md](windows.md)** — Windows-specific debug: WPP GUIDs, trace flags, registry keys, telemetry, debug report IDs, HSDES workarounds
- **`fv-thc/registers`** — Register definitions for debug (status, error, interrupt regs)
- **`fv-thc/dma`** — DMA error handling, STALL_STS, Stop-on-Error
- **`fv-thc/power`** — Power state triage, D0i2/D3 debug, PMCLite messages
- **`fv-thc/hidspi`** — SPI protocol-level debug, opcode verification
- **`fv-thc/hidi2c`** — I2C protocol-level debug, NAK/abort handling
- **`fv-thc/platform`** — Platform-specific BDFs, Device IDs
- **`fv-thc/simics`** — Simics pre-si debugging: WinDbg setup, log levels, model sightings, touch injection, unit tests
- **`fv-thc/driver`** — Driver-level debug, HSDES workarounds, interrupt handling
- **`fv-thc/wot`** — Wake-on-Touch architecture (GPIO IP/vGPIO wake path), driver-side WoT config, entry/exit flows, WoG (Not POR), platform-specific WoT enablement, WoT debug & known issues (WCL HSD 16027810168)
- **Delegate**: `FV-GenDebugger` for Confluence wiki BKM search and HSDES sighting correlation
- **Reference**: `fv-thc/docs/thc_known_issues.md` — Consolidated bug tracker
- **Reference**: `fv-thc/eval/thc_skill_eval_tests.md` — EVAL test cases for skill validation
