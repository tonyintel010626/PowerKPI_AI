# THC Test Gap Analysis Report

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> Compares the 177-item THC IP Test Coverage Matrix against actual PythonSV test scripts in `C:\pythonsv\novalake\vjt\thc\` to identify coverage gaps.
> Generated: 2026-03-05 | Updated: 2026-03-06 (SwAS-derived tests added) | Source Matrix: `thc_test_coverage_matrix.md` | Script Repo: `novalake/vjt/thc/`

---

## Executive Summary

| Metric | Count | % of 177 |
|--------|-------|----------|
| **EXISTS** (dedicated test script) | 0 | 0.0% |
| **PARTIAL** (related code exists, not full coverage) | 19 | 10.7% |
| **MISSING** (no test script at all) | 158 | 89.3% |

**Critical Finding**: There are **zero** dedicated, automated pass/fail test scripts that fully cover any single test ID. The repository contains debug/validation utilities and infrastructure code that *partially* addresses 19 of the 177 requirements. The remaining 158 test IDs — including **39 of the 48 P1 (must-test)** items — have no corresponding test code whatsoever. The 36 SwAS-derived test IDs added on 2026-03-06 are ALL MISSING — no PythonSV scripts exist for any SwAS-documented scenario.

### P1 Gap Breakdown

| P1 Status | Count | % of 48 P1 |
|-----------|-------|------------|
| P1 PARTIAL | 9 | 18.8% |
| P1 MISSING | 39 | 81.3% |

---

## Matching Scripts Inventory

The following scripts in `C:\pythonsv\novalake\vjt\thc\` contain code relevant to test IDs:

| Script | Class / Function | Coverage Scope |
|--------|-----------------|----------------|
| `thc_registers.py` | `ThcStatus.check_bdf_vid_did()` | PCI BDF/DID validation (dumps, no pass/fail) |
| `thc_registers.py` | `ThcStatus.check_thc_port_config()` | Port config dump for SPI/I2C |
| `thc_registers.py` | `ThcStatus.check_telemetry()` | Telemetry register dump for low-power debug |
| `thc_registers.py` | `ThcStatus.read_ip_tm_mailbox()` | PMC SSRAM telemetry comparison |
| `thc_registers.py` | `ThcStatus.check_thc_fuse()` | Fuse validation |
| `pio_access.py` | `ThcPioAccess.spi_pio_access()` | SPI PIO full flow with descriptor read |
| `pio_access.py` | `ThcPioAccess.i2c_pio_access()` | I2C PIO command flow |
| `pio_access.py` | `test_spi_pio()` | End-to-end SPI PIO test (closest to a real test) |
| `thc_ltr_rltr.py` | `THC_LTR.thc_ltr_test()` | LTR scale/value sweep THC→PMC |
| `thc_common.py` | `ThcBase.thc_i2c_rtl_bug_wa()` | I2C MPS 4KB workaround |

---

## Full Gap Analysis Table

### 1. PCI Enumeration & Configuration (10 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| PCI-001 | P1 | BAR0 32KB MMIO mapping | **PARTIAL** | `thc_registers.py::check_bdf_vid_did()` | Reads BAR0 address but does not validate size=32KB or type bits |
| PCI-002 | P1 | PCI Device ID per platform | **PARTIAL** | `thc_registers.py::check_bdf_vid_did()` | Compares DID against `thc_project_data.py` table; dump only, no automated pass/fail |
| PCI-003 | P1 | THC1 requires THC0 enabled | **MISSING** | — | No script tests THC1 dependency on THC0 |
| PCI-004 | P2 | PCIe mode (MTL-S+) | **MISSING** | — | No PCIe cap structure verification |
| PCI-005 | P3 | SetIDValue DID override | **MISSING** | — | No sideband message test |
| PCI-006 | P1 | NVL THC1 BDF change | **PARTIAL** | `thc_registers.py::check_bdf_vid_did()` | NVL BDF defined in `thc_project_data.py`; checked but not asserted |
| PCI-007 | P1 | MSI capability | **MISSING** | — | No MSI cap register verification |
| PCI-008 | P2 | LTR capability | **MISSING** | — | LTR test exists but does not verify PCI cap offset |
| PCI-009 | P2 | PM capability (D3-Hot) | **MISSING** | — | No PMCSR access test |
| PCI-010 | P2 | NVL+ PI softstrap | **MISSING** | — | No PI register verification |

### 2. MMIO Register Access (7 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| REG-001 | P1 | Common regs at Base+0x0000 | **PARTIAL** | `thc_common.py::thc_register_table()` | Reads common reg space for dump; no write-back verification |
| REG-002 | P1 | Port 0 regs at Base+0x1000 | **PARTIAL** | `thc_common.py::ip_register_table()` | Reads port 0 registers; dump only |
| REG-003 | P1 | Port 1 regs at Base+0x2000 | **PARTIAL** | `thc_common.py::ip_register_table()` | Reads port 1 registers if port valid; dump only |
| REG-004 | P2 | BIOS_LOCK_EN sticky | **MISSING** | — | No sticky-bit test |
| REG-005 | P2 | DRV_LOCK_EN sticky | **MISSING** | — | No sticky-bit test |
| REG-006 | P2 | Read/Modify/Write for partial | **MISSING** | — | No partial-write preservation test |
| REG-007 | P3 | SAI access control | **MISSING** | — | No SAI rejection test |

### 3. SPI Protocol — HIDSPI (15 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| SPI-001 | P1 | Single IO mode read/write | **PARTIAL** | `thc_registers.py::check_thc_port_config()` | Reads SPI port config including IO mode; does not perform data transfer test |
| SPI-002 | P2 | Dual IO mode read/write | **PARTIAL** | `thc_registers.py::check_thc_port_config()` | Config check only, no data transfer |
| SPI-003 | P2 | Quad IO mode read/write | **PARTIAL** | `thc_registers.py::check_thc_port_config()` | Config check only, no data transfer |
| SPI-004 | P1 | SPI frequency sweep | **MISSING** | — | `thc_constants.py` defines dividers but no sweep test exists |
| SPI-005 | P2 | LNL+ half-cycle divider | **MISSING** | — | No fractional divider test |
| SPI-006 | P2 | CS# setup/hold timing | **MISSING** | — | No timing test |
| SPI-007 | P3 | CS-to-CK delay (LNL+) | **MISSING** | — | No delay test |
| SPI-008 | P1 | ICR read opcodes (0B/BB/EB/FB) | **MISSING** | — | `thc_constants.py` defines opcodes but no test exercises them |
| SPI-009 | P2 | Dummy clock cycles | **MISSING** | — | No dummy-cycle validation |
| SPI-010 | P3 | Loopback clock compensation | **MISSING** | — | No loopback test |
| SPI-011 | P1 | HID descriptor retrieval | **PARTIAL** | `pio_access.py::test_spi_pio()` | Reads descriptor via PIO; closest to a real test but no automated pass/fail assertion |
| SPI-012 | P1 | Input report read | **PARTIAL** | `pio_access.py::test_spi_pio()` | Reads report descriptor; partial coverage of input report flow |
| SPI-013 | P2 | Output report write | **MISSING** | — | PIO write exists in `pio_access.py` but no output report test |
| SPI-014 | P2 | Feature report get/set | **MISSING** | — | No feature report test |
| SPI-015 | P2 | SPI_LOW_FREQ_EN toggle | **MISSING** | — | No frequency toggle test |

### 4. I2C Protocol — HIDI2C (14 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| I2C-001 | P1 | PORT_TYPE=01 for I2C mode | **PARTIAL** | `thc_registers.py::check_thc_port_config()` | Reads PORT_TYPE; no mode-switch test |
| I2C-002 | P2 | Standard mode (100KHz) | **MISSING** | — | `snps_i2c_subip_register.py` defines SCL count regs but no speed test |
| I2C-003 | P1 | Fast mode (400KHz) | **MISSING** | — | No speed test |
| I2C-004 | P2 | Fast Mode Plus (1MHz) | **MISSING** | — | No speed test |
| I2C-005 | P1 | SPI_RD_MPS=4KB workaround | **PARTIAL** | `thc_common.py::thc_i2c_rtl_bug_wa()` | Applies the workaround; no verification that it was needed or effective |
| I2C-006 | P1 | HID descriptor read (30B) | **MISSING** | — | `pio_access.py::i2c_pio_access()` exists but no descriptor test |
| I2C-007 | P1 | GET_REPORT (Input) | **MISSING** | — | No RXDMA input report test |
| I2C-008 | P2 | GET_REPORT (Feature) | **MISSING** | — | No feature report test |
| I2C-009 | P2 | SET_REPORT (Output) | **MISSING** | — | No TXDMA output report test |
| I2C-010 | P2 | SET_POWER command | **MISSING** | — | No power state change test |
| I2C-011 | P1 | RESET command | **MISSING** | — | No device reset via PIO test |
| I2C-012 | P3 | Elan legacy panel (PTL+) | **MISSING** | — | `thc_bom_devices.py` defines Elan addresses but no workaround test |
| I2C-013 | P2 | I2C NAK retry | **MISSING** | — | No NAK handling test |
| I2C-014 | P3 | Clock stretching | **MISSING** | — | No clock stretching test |

### 5. DMA Engine (22 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| DMA-001 | P1 | RXDMA1 single frame read | **MISSING** | — | No DMA test scripts exist |
| DMA-002 | P2 | RXDMA2 frame routing | **MISSING** | — | `thc_register_maps.py` defines RXDMA2 regs but no test |
| DMA-003 | P1 | TXDMA single frame write | **MISSING** | — | No DMA test scripts exist |
| DMA-004 | P2 | SWDMA SW-triggered read | **MISSING** | — | No SWDMA test |
| DMA-005 | P1 | PRD circular buffer wraparound | **MISSING** | — | No PRD test |
| DMA-006 | P2 | PRD table max entries (256) | **MISSING** | — | No PRD table test |
| DMA-007 | P2 | CB max tables (128) | **MISSING** | — | No CB test |
| DMA-008 | P1 | PRD 4KB alignment (all entries) | **MISSING** | — | No alignment verification |
| DMA-009 | P1 | IOC bit MSI generation | **MISSING** | — | No IOC test |
| DMA-010 | P1 | EOP bit handling | **MISSING** | — | No EOP test |
| DMA-011 | P2 | Frame size min (64B) | **MISSING** | — | No frame size test |
| DMA-012 | P2 | Frame size max (1MB) | **MISSING** | — | No frame size test |
| DMA-013 | P3 | uFrame size sweep (16B-4KB) | **MISSING** | — | No uFrame test |
| DMA-014 | P2 | STALL_STS on PRD exhaustion | **MISSING** | — | No stall handling test |
| DMA-015 | P2 | RXDMA Stop-on-Error | **MISSING** | — | No error handling test |
| DMA-016 | P2 | I2C TX Abort recovery | **MISSING** | — | No TX abort test |
| DMA-017 | P2 | Frame coalescing (count-based) | **MISSING** | — | `thc_register_maps.py` defines THC_COALESCE regs but no test |
| DMA-018 | P2 | FCD bypass coalescing | **MISSING** | — | No FCD test |
| DMA-019 | P3 | Timing-based coalescing (LNL+) | **MISSING** | — | No timing coalesce test |
| DMA-020 | P3 | Display sync (VSYNC override) | **MISSING** | — | `thc_register_maps.py` defines THC_DSYNC_CFG but no test |
| DMA-021 | P3 | GuC doorbell ring | **MISSING** | — | No GuC test |
| DMA-022 | P3 | PRD descriptor caching | **MISSING** | — | No prefetch test |

### 6. PIO — Programmed I/O (6 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| PIO-001 | P1 | SPI PIO register read (7-step) | **PARTIAL** | `pio_access.py::spi_pio_access()` | Implements 7-step PIO read; no automated pass/fail |
| PIO-002 | P1 | SPI PIO register write | **PARTIAL** | `pio_access.py::spi_pio_access()` | Write flow present; no assertion |
| PIO-003 | P1 | I2C PIO command | **PARTIAL** | `pio_access.py::i2c_pio_access()` | I2C PIO flow present; no assertion |
| PIO-004 | P2 | Bus arbitration (PIO > DMA) | **MISSING** | — | No arbitration test |
| PIO-005 | P3 | Round-robin chicken bit | **MISSING** | — | No chicken bit test |
| PIO-006 | P2 | No PIO during RXDMA active | **MISSING** | — | No concurrent access test |

### 7. Interrupts (10 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| INT-001 | P1 | GPIO device interrupt (active low) | **MISSING** | — | No interrupt test scripts |
| INT-002 | P1 | GPIO to MSI routing | **MISSING** | — | No MSI routing test |
| INT-003 | P2 | GBL_INT_EN (bit 31, LNL+) | **MISSING** | — | `thc_register_maps.py` defines THC_INT_CFG but no test |
| INT-004 | P3 | vGPIO SWGPIO_INT (bit 4) | **MISSING** | — | No vGPIO test |
| INT-005 | P2 | DEVRST interrupt (bit 3) | **MISSING** | — | No DEVRST interrupt test |
| INT-006 | P1 | RX DMA interrupt status | **MISSING** | — | Register map exists but no test |
| INT-007 | P1 | TX DMA interrupt status | **MISSING** | — | Register map exists but no test |
| INT-008 | P2 | Error interrupts (TXN_ERR) | **MISSING** | — | No error interrupt test |
| INT-009 | P2 | Boot: level-trigger during init | **MISSING** | — | No boot interrupt mode test |
| INT-010 | P3 | THC_DEVINT_QUIESCE_EN | **MISSING** | — | No quiesce test |

### 8. Power Management (14 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| PM-001 | P1 | D0i2 HW autonomous entry | **MISSING** | — | `thc_register_maps.py` defines THC_D0I2/THC_CGPG regs but no test |
| PM-002 | P1 | D0i2 exit on interrupt | **MISSING** | — | No D0i2 exit test |
| PM-003 | P2 | D0i2 entry timer max (1s) | **MISSING** | — | No timer test |
| PM-004 | P1 | D3-Hot entry/exit | **MISSING** | — | No D3 test |
| PM-005 | P1 | D3 save/restore (28 regs) | **MISSING** | — | No save/restore test |
| PM-006 | P2 | D3 4-level flow (PTL+) | **MISSING** | — | No D3 level test |
| PM-007 | P2 | LTR active state reporting | **PARTIAL** | `thc_ltr_rltr.py::thc_ltr_test()` | Sweeps LTR values and compares THC→PMC; covers active LTR |
| PM-008 | P2 | LTR low-power state reporting | **PARTIAL** | `thc_ltr_rltr.py::thc_ltr_test()` | Partial — tests LTR values but LP-specific behavior not isolated |
| PM-009 | P2 | Infinite LTR on cold boot | **MISSING** | — | LTR test does not check boot/reset state |
| PM-010 | P2 | S0ix entry/exit with touch | **MISSING** | — | No S0ix test |
| PM-011 | P2 | Wake-on-Touch (WoT) | **MISSING** | — | No WoT test |
| PM-012 | P3 | CGPG clock gating >98% | **MISSING** | — | Telemetry dump exists but no efficiency calculation |
| PM-013 | P2 | Power gate exit <10us | **MISSING** | — | No latency measurement test |
| PM-014 | P3 | PMCLite sideband messages | **MISSING** | — | Telemetry reads PMC SSRAM but no SB message test |

### 9. Reset Flows (9 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| RST-001 | P1 | G3 exit / cold boot | **MISSING** | — | No reset test scripts |
| RST-002 | P2 | Soft reset (PSRST+DEVRST+TSFTRST) | **MISSING** | — | No soft reset test |
| RST-003 | P2 | Cold reset | **MISSING** | — | No cold reset test |
| RST-004 | P2 | Warm reset | **MISSING** | — | No warm reset test |
| RST-005 | P2 | Global reset | **MISSING** | — | No global reset test |
| RST-006 | P2 | GPIO reset during reset_warn | **MISSING** | — | No GPIO reset test |
| RST-007 | P1 | Controller init after reset | **MISSING** | — | No post-reset init test |
| RST-008 | P2 | SPI_IO_RDY wait | **MISSING** | — | No IO ready test |
| RST-009 | P2 | Device init state polling (0-4) | **MISSING** | — | No init state test |

### 10. Stress & Error (6 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| STR-001 | P2 | Continuous touch streaming | **MISSING** | — | No stress test scripts |
| STR-002 | P2 | Power cycle during DMA | **MISSING** | — | No power-cycle stress test |
| STR-003 | P2 | Multi-port simultaneous | **MISSING** | — | No multi-port test |
| STR-004 | P2 | DMA overrun recovery | **MISSING** | — | No overrun test |
| STR-005 | P3 | Bus error recovery | **MISSING** | — | No bus error test |
| STR-006 | P3 | Max frame rate sustained | **MISSING** | — | No max-rate test |

### 11. DFT & Debug (4 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| DFT-001 | P3 | VISA 2-lane debug | **MISSING** | — | No VISA test |
| DFT-002 | P3 | TSI device emulation (DFX_Mode_En) | **MISSING** | — | No TSI emulation test |
| DFT-003 | P3 | Performance counters accuracy | **MISSING** | — | Telemetry dump reads counters but does not verify accuracy |
| DFT-004 | P2 | SWDMA debug reads | **MISSING** | — | No SWDMA debug test |

### 12. BIOS Configuration Validation (12 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| BIOS-001 | P1 | BIOS_LOCK_EN set before OS handoff | **MISSING** | — | No BIOS lock test |
| BIOS-002 | P1 | THC_CFG_PCE HAE programmed | **MISSING** | — | No HAE verification |
| BIOS-003 | P2 | THC_CFG_PCE D3HE programmed | **MISSING** | — | No D3HE verification |
| BIOS-004 | P2 | SAI policy regs not all-zero | **MISSING** | — | No SAI check |
| BIOS-005 | P2 | CDC config matches expected state | **MISSING** | — | No CDC config test |
| BIOS-006 | P1 | Port config matches physical BOM | **PARTIAL** | `thc_registers.py::check_thc_port_config()` | Reads port config and BOM data; comparison is manual, not automated |
| BIOS-007 | P2 | LTR values programmed by BIOS | **MISSING** | — | LTR test runs after boot, doesn't check BIOS programming |
| BIOS-008 | P2 | MSFT G5 panel bit (MMIO 0x1128 bit31) | **MISSING** | — | No G5 panel bit test |
| BIOS-009 | P2 | Function disable flow correct | **MISSING** | — | No FD flow test |
| BIOS-010 | P1 | S3 resume full re-init | **MISSING** | — | No S3 resume test |
| BIOS-011 | P1 | DEVRST before D3/Sx entry | **MISSING** | — | No DEVRST ordering test |
| BIOS-012 | P2 | GPIO IOSTANDBY config | **MISSING** | — | No GPIO IOSTANDBY test |

### 13. Cross-Platform Driver Validation (12 tests)

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| XPLAT-001 | P2 | DMA pause timeout matches per OS | **MISSING** | — | No cross-platform test scripts |
| XPLAT-002 | P1 | DMA pause polls correct register | **MISSING** | — | No INT_STS polling test |
| XPLAT-003 | P2 | SET_POWER behavior per OS | **MISSING** | — | No SET_POWER test |
| XPLAT-004 | P2 | IC_CON init matches per OS | **MISSING** | — | `snps_i2c_subip_register.py` defines IC_CON but no init test |
| XPLAT-005 | P2 | SWDMA save/restore per OS | **MISSING** | — | No save/restore test |
| XPLAT-006 | P1 | SPI base clock = 125 MHz | **MISSING** | — | No clock frequency verification |
| XPLAT-007 | P2 | PIO opcodes read=0x4/write=0x6/bulk=0x8 | **MISSING** | — | PIO scripts use opcodes but don't verify them |
| XPLAT-008 | P2 | RXDMA1 unused for I2C (size=0) | **MISSING** | — | No I2C RXDMA1 check |
| XPLAT-009 | P2 | Host Reset via TXDMA not PIO | **MISSING** | — | No host reset method test |
| XPLAT-010 | P3 | Output report PM gap validation | **MISSING** | — | No PM gap test |
| XPLAT-011 | P3 | I2C FS_HCNT/LCNT per OS | **MISSING** | — | No SCL count comparison |
| XPLAT-012 | P3 | LTR unconfig — no toggle pattern | **MISSING** | — | No LTR unconfig test |

### 14. SwAS-Derived Test Scenarios (36 tests) — Added 2026-03-06

> All 36 SwAS-derived test IDs are **MISSING**. No PythonSV scripts exist for any QuickSPI/QuickI2C SwAS-documented scenario.

| ID | Priority | Description | Status | Matching Script | Notes |
|----|----------|-------------|--------|----------------|-------|
| SWAS-Q-001 | P2 | Quiesce during host-initiated reset | **MISSING** | — | SwAS P0574: quiesce flow not testable without driver-level hooks |
| SWAS-Q-002 | P2 | Buffer threshold throttling at 50% | **MISSING** | — | SwAS P0627: requires filling 8 of 16 RX buffers; no DMA test infra |
| SWAS-Q-003 | P2 | Quiesce on D0Exit before D3 | **MISSING** | — | SwAS P0580: D0Exit/D3 transition not exercised |
| SWAS-Q-004 | P2 | No quiesce within ISR/DPC | **MISSING** | — | SwAS P0580: negative test — requires interrupt injection |
| SWAS-Q-005 | P2 | RAW_INT_STS MSI blocked during quiesce (LNL) | **MISSING** | — | SwAS P0587: LNL-specific RTL bug — requires LNL silicon |
| SWAS-I-001 | P2 | Double interrupt on slow FW deassert | **MISSING** | — | SwAS P0582: pre-LNL errata — needs FW delay injection |
| SWAS-I-002 | P1 | Level-to-edge trigger switch at boot | **MISSING** | — | SwAS P0582 workaround: level→edge switch not tested |
| SWAS-E-001 | P3 | Write DMA error path not firing | **MISSING** | — | SwAS P0635: negative test — confirm error never fires |
| SWAS-E-002 | P3 | Fatal Error path not firing | **MISSING** | — | SwAS P0636: negative test — confirm error never fires |
| SWAS-E-003 | P3 | PIO Error path not firing (I2C) | **MISSING** | — | SwAS P0753: QuickI2C-specific unused error |
| SWAS-E-004 | P3 | I2C subIP Error path not firing | **MISSING** | — | SwAS P0756: QuickI2C-specific unused error |
| SWAS-D-001 | P2 | ISR masks via GBL_INT_EN | **MISSING** | — | SwAS P0603: ISR pattern requires interrupt-level observation |
| SWAS-D-002 | P2 | DPC unmasks after processing | **MISSING** | — | SwAS P0620: DPC completion pattern |
| SWAS-D-003 | P3 | ISR/DPC lock (WdfInterruptLock) | **MISSING** | — | SwAS P0624: Windows driver internal — not PythonSV-testable |
| SWAS-I2C-001 | P1 | IC_DMA_RDLR ≤ 7 constraint | **MISSING** | — | SwAS P0350: register value can be read via PythonSV, but overflow test needs DMA |
| SWAS-I2C-002 | P2 | Bus clear SDA/SCL stuck recovery | **MISSING** | — | SwAS P0771: requires I2C bus fault injection |
| SWAS-I2C-003 | P1 | RTD3 PRW ACPI crash prevention | **MISSING** | — | SwAS P0300: ACPI table audit — could be PythonSV + ACPI dump |
| SWAS-I2C-004 | P2 | I2C reset timeout = 5 seconds | **MISSING** | — | SwAS P0479: timeout verification needs device reset + timer |
| SWAS-I2C-005 | P3 | I2C max frame size (128-255B) | **MISSING** | — | SwAS P0857: registry key + frame size verification |
| SWAS-WOT-001 | P2 | WoT via vGPIO path (not THC) | **MISSING** | — | SwAS P0706: vGPIO wake path — requires sleep/wake cycle |
| SWAS-WOT-002 | P2 | No device reset on WoT exit | **MISSING** | — | SwAS P0726: verify device state after WoT wake |
| SWAS-WOT-003 | P2 | Windows Wait Wake IRP flow | **MISSING** | — | SwAS P0706: Windows-specific — not PythonSV-testable |
| SWAS-WOT-004 | P2 | I2C SET_POWER(sleep) on WoT entry | **MISSING** | — | SwAS P0823: I2C WoT entry sequence |
| SWAS-WOT-005 | P2 | I2C SET_POWER(ON) on WoT exit | **MISSING** | — | SwAS P0851: I2C WoT exit sequence |
| SWAS-REG-001 | P3 | IO_Mode_Override (SPI) | **MISSING** | — | SwAS P0790: registry key not exercised |
| SWAS-REG-002 | P3 | SPI_Frequency_Override | **MISSING** | — | SwAS P0791: registry key not exercised |
| SWAS-REG-003 | P3 | TxDMA_Override (SPI) | **MISSING** | — | SwAS P0793: registry key not exercised |
| SWAS-REG-004 | P3 | I2C_Max_Frame_Size_Enable + Size | **MISSING** | — | SwAS P0857: registry key not exercised |
| SWAS-REG-005 | P3 | I2C_Int_Delay_Enable + Delay | **MISSING** | — | SwAS P0880: registry key not exercised |
| SWAS-REG-006 | P2 | EnEdgeTriggeredINT | **MISSING** | — | SwAS T7: registry key not exercised |
| SWAS-REG-007 | P2 | ResetRequiredByDriver | **MISSING** | — | SwAS T7: registry key not exercised |
| SWAS-REG-008 | P2 | EnResetPollingWA | **MISSING** | — | SwAS T7: registry key not exercised |
| SWAS-REG-009 | P3 | EnableFWFlashWABOM36 | **MISSING** | — | SwAS T7: registry key not exercised |
| SWAS-REG-010 | P3 | DoNotWaitForResetResponse | **MISSING** | — | SwAS T7: registry key not exercised |
| SWAS-ACPI-001 | P2 | ACPI frequency encoding bits 0-2 | **MISSING** | — | SwAS P0900: ACPI table parsing + SPI clock verify |
| SWAS-ACPI-002 | P2 | LimitPacketSize ACPI encoding | **MISSING** | — | SwAS P0912: ACPI table parsing + packet size verify |

---

## Unlisted Test Scripts

The following scripts exist in the repository but are **not mapped to any test ID** in the coverage matrix. They serve infrastructure, debug, or utility purposes:

| Script | Purpose | Potential Coverage |
|--------|---------|-------------------|
| `thc_common.py` | Base class, project detection, register table infrastructure | Foundation for all tests; not a test itself |
| `ip_register_check.py` | Generic IP register dump (GPIO, ITSS) | Not THC-specific; utility for other IPs |
| `metadata/thc_constants.py` | LTR scales, SPI dividers, IO modes, vendor IDs | Data definitions consumed by tests |
| `metadata/thc_project_data.py` | Per-project DIDs, BDFs, reset pins, telemetry offsets | Platform config data (MTL/LNL/PTL/NVL) |
| `metadata/thc_register_maps.py` | Register/bitfield dictionaries for all THC register blocks | Rich register definitions — ready for test scripts to consume |
| `metadata/thc_bom_devices.py` | BOM device addresses (WACOM, ELAN, ALPS, Sensel) | Device address lookup |
| `metadata/snps_i2c_subip_register.py` | Synopsys I2C Sub-IP register definitions | IC_CON, IC_TAR, SCL timing regs — needed by I2C tests |
| `include_nvl_paths.py` | Python path setup for NVL | Infrastructure |
| `common_utility/register_utils.py` | Register read/write/poll helpers | Infrastructure |
| `common_utility/bitwise_utils.py` | Bit manipulation utilities | Infrastructure |
| `common_utility/table_utils.py` | Table formatting | Infrastructure |
| `common_utility/file_utils.py` | File I/O utilities | Infrastructure |
| `common_utility/debug_poll_register_change_with_BIOS_port80_postcode.py` | BIOS postcode debug polling | Debug utility; potentially useful for RST-001/RST-007 |

---

## Priority Gaps — Top 10 Missing P1 Tests

These are the highest-impact gaps: P1 (must-test, silicon bring-up blocking) items with **no test script at all**.

| Rank | ID | Category | Description | Impact |
|------|----|----------|-------------|--------|
| 1 | DMA-001 | DMA Engine | RXDMA1 single frame read | **No DMA tests exist.** DMA is the core data path — 22 test IDs, all MISSING. |
| 2 | DMA-003 | DMA Engine | TXDMA single frame write | Same as above — bidirectional DMA is untested |
| 3 | DMA-005 | DMA Engine | PRD circular buffer wraparound | PRD ring is the fundamental DMA data structure |
| 4 | DMA-008 | DMA Engine | PRD 4KB alignment (all entries) | RTL bug 15014172472 — must verify workaround |
| 5 | DMA-009 | DMA Engine | IOC bit MSI generation | DMA-to-interrupt path untested |
| 6 | PM-001 | Power Mgmt | D0i2 HW autonomous entry | **No power management tests.** PM is critical for battery life. |
| 7 | PM-004 | Power Mgmt | D3-Hot entry/exit | D3 transition untested |
| 8 | PM-005 | Power Mgmt | D3 save/restore (28 regs) | Register corruption on D3 exit would be silent |
| 9 | INT-001 | Interrupts | GPIO device interrupt (active low) | **No interrupt tests.** Interrupt path is untested. |
| 10 | RST-001 | Reset Flows | G3 exit / cold boot | **No reset tests.** Cold boot path untested. |

### Additional P1 Gaps (not in top 10 but critical)

| ID | Category | Description |
|----|----------|-------------|
| PCI-003 | PCI | THC1 requires THC0 enabled |
| PCI-007 | PCI | MSI capability |
| SPI-004 | SPI Protocol | SPI frequency sweep |
| SPI-008 | SPI Protocol | ICR read opcodes |
| I2C-003 | I2C Protocol | Fast mode (400KHz) |
| I2C-006 | I2C Protocol | HID descriptor read (30B) |
| I2C-007 | I2C Protocol | GET_REPORT (Input) |
| I2C-011 | I2C Protocol | RESET command |
| DMA-010 | DMA Engine | EOP bit handling |
| INT-002 | Interrupts | GPIO to MSI routing |
| INT-006 | Interrupts | RX DMA interrupt status |
| INT-007 | Interrupts | TX DMA interrupt status |
| PM-002 | Power Mgmt | D0i2 exit on interrupt |
| RST-007 | Reset Flows | Controller init after reset |
| BIOS-001 | BIOS Config | BIOS_LOCK_EN set before OS handoff |
| BIOS-002 | BIOS Config | THC_CFG_PCE HAE programmed |
| BIOS-006 | BIOS Config | Port config matches physical BOM (partial exists) |
| BIOS-010 | BIOS Config | S3 resume full re-init |
| BIOS-011 | BIOS Config | DEVRST before D3/Sx entry |
| XPLAT-002 | Cross-Platform | DMA pause polls correct register |
| XPLAT-006 | Cross-Platform | SPI base clock = 125 MHz |
| SWAS-I-002 | SwAS: Interrupt | Level-to-edge trigger switch at boot (P0582 workaround) |
| SWAS-I2C-001 | SwAS: I2C | IC_DMA_RDLR ≤ 7 constraint (P0350 — temp buffer overflow) |
| SWAS-I2C-003 | SwAS: I2C | RTD3 PRW ACPI crash prevention (P0300 — Windows crash) |

---

## SwAS-Derived Gap Analysis (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 + QuickI2C SwAS v1.0 cross-referenced against PythonSV test scripts.
> All 36 SwAS-derived test IDs are **MISSING**. This section analyzes the gaps by theme.

### SwAS Gap Theme 1: Quiesce & Buffer Throttling (5 tests, 0% covered)

**Why this matters**: The quiesce mechanism is the driver's primary defense against interrupt storms and buffer exhaustion. SwAS documents 4 distinct quiesce scenarios (P0574-P0580) plus a LNL-specific RTL bug (P0587). None are tested.

| Gap | Impact | PythonSV Feasibility |
|-----|--------|---------------------|
| Quiesce during reset (SWAS-Q-001) | Medium — reset flow already untested | **Feasible** — can set QUIESCE_EN and verify INT_STS behavior via register reads |
| Buffer threshold at 50% (SWAS-Q-002) | High — silent data loss if throttling fails | **Hard** — needs DMA infrastructure to fill 8+ buffers |
| Quiesce on D0Exit (SWAS-Q-003) | Medium — D3 transition untested | **Feasible** — can observe QUIESCE_EN around PM transitions |
| No quiesce in ISR (SWAS-Q-004) | Low — negative test | **Not feasible** — requires driver-internal observation |
| LNL RAW_INT_STS bug (SWAS-Q-005) | High on LNL — MSI lost during quiesce | **Feasible on LNL** — set QUIESCE_EN, trigger interrupt, check MSI |

### SwAS Gap Theme 2: I2C-Specific Corner Cases (5 tests, 0% covered)

**Why this matters**: QuickI2C SwAS reveals 3 P1-level issues not in the HAS: IC_DMA_RDLR overflow, RTD3 ACPI crash, and bus clear gap. These are **production-impacting** — the RTD3 PRW issue crashes Windows.

| Gap | Impact | PythonSV Feasibility |
|-----|--------|---------------------|
| IC_DMA_RDLR ≤ 7 (SWAS-I2C-001, P1) | **Critical** — overflow corrupts DMA data | **Feasible** — read IC_DMA_RDLR register, verify ≤ 7 |
| Bus clear recovery (SWAS-I2C-002) | Medium — stuck bus requires power cycle | **Hard** — needs bus fault injection |
| RTD3 PRW ACPI crash (SWAS-I2C-003, P1) | **Critical** — Windows BSOD | **Feasible** — ACPI table dump + pattern match for Power Resource vs _PS0/_PS3 |
| I2C reset timeout 5s (SWAS-I2C-004) | Medium — 1s vs 5s discrepancy | **Feasible** — time reset sequence |
| I2C max frame size (SWAS-I2C-005) | Low — ECO key rarely used | **Feasible** — registry key + frame observation |

### SwAS Gap Theme 3: Wake-on-Touch (5 tests, 0% covered)

**Why this matters**: WoT is a key user-facing feature (Linux 6.17+, Windows via extension INF). PM-011 in the original matrix was already MISSING. The SwAS adds 5 more specific WoT test IDs. Combined, there are **6 WoT-related test IDs and zero coverage**.

| Gap | Impact | PythonSV Feasibility |
|-----|--------|---------------------|
| vGPIO wake path (SWAS-WOT-001) | High — WoT silently fails if routed wrong | **Hard** — needs sleep/wake cycle with touch |
| No reset on WoT exit (SWAS-WOT-002) | High — unnecessary reset adds 1-5s latency | **Hard** — needs WoT wake observation |
| Windows Wait Wake IRP (SWAS-WOT-003) | Medium — Windows-only | **Not PythonSV-testable** — driver internal |
| I2C SET_POWER(sleep) on entry (SWAS-WOT-004) | Medium — I2C device won't sleep | **Hard** — needs I2C bus monitoring during WoT |
| I2C SET_POWER(ON) on exit (SWAS-WOT-005) | Medium — I2C device won't wake | **Hard** — needs I2C bus monitoring during WoT |

### SwAS Gap Theme 4: ECO Registry Keys (10 tests, 0% covered)

**Why this matters**: ECO (Engineering Change Order) registry keys are the driver's primary mechanism for field-debugging and workaround deployment. SwAS documents 13+ keys across QuickSPI (P0790-P0793) and QuickI2C (P0857-P0896, T7). None are tested. If a key doesn't work, the field workaround fails.

| Gap | Impact | PythonSV Feasibility |
|-----|--------|---------------------|
| SPI mode/freq/TxDMA overrides (SWAS-REG-001 to 003) | Medium — SPI ECO keys | **Not feasible** — Windows registry keys, not register-level |
| I2C frame size + int delay (SWAS-REG-004 to 005) | Medium — I2C ECO keys | **Not feasible** — Windows registry keys |
| Edge-triggered INT, reset polling, etc. (SWAS-REG-006 to 010) | High — behavioral overrides | **Not feasible** — Windows registry keys |

> **Note**: ECO registry keys are Windows driver-internal and not directly testable via PythonSV. Testing requires Windows driver test infrastructure (WDK HLK, TAEF, or manual registry + observe). These gaps are real but outside the PythonSV test repo scope.

### SwAS Gap Theme 5: ISR/DPC & Interrupt Errata (5 tests, 0% covered)

**Why this matters**: The ISR/DPC pattern (P0603-P0624) is the core interrupt processing loop. The double-interrupt errata (P0582) caused real bugs on pre-LNL silicon. The level-to-edge boot switch is a P1 item.

| Gap | Impact | PythonSV Feasibility |
|-----|--------|---------------------|
| ISR masks GBL_INT_EN (SWAS-D-001) | Medium — incorrect masking = interrupt storm | **Feasible** — observe GBL_INT_EN bit 31 toggle during interrupt |
| DPC unmasks (SWAS-D-002) | Medium — stuck mask = touch stops | **Feasible** — observe GBL_INT_EN after DPC completion |
| WdfInterruptLock (SWAS-D-003) | Low — driver internal | **Not PythonSV-testable** |
| Double interrupt (SWAS-I-001) | High on pre-LNL — phantom touches | **Hard** — needs FW delay injection |
| Level-to-edge switch (SWAS-I-002, P1) | **Critical** — incorrect boot = missed interrupts | **Feasible** — read INT config before/after first reset interrupt |

---

## Category Coverage Summary

| Category | Total | EXISTS | PARTIAL | MISSING | % Covered (EXISTS+PARTIAL) |
|----------|-------|--------|---------|---------|---------------------------|
| PCI Enumeration | 10 | 0 | 3 | 7 | 30.0% |
| MMIO Registers | 7 | 0 | 3 | 4 | 42.9% |
| SPI Protocol | 15 | 0 | 4 | 11 | 26.7% |
| I2C Protocol | 14 | 0 | 2 | 12 | 14.3% |
| DMA Engine | 22 | 0 | 0 | 22 | 0.0% |
| PIO | 6 | 0 | 3 | 3 | 50.0% |
| Interrupts | 10 | 0 | 0 | 10 | 0.0% |
| Power Mgmt | 14 | 0 | 2 | 12 | 14.3% |
| Reset Flows | 9 | 0 | 0 | 9 | 0.0% |
| Stress & Error | 6 | 0 | 0 | 6 | 0.0% |
| DFT & Debug | 4 | 0 | 0 | 4 | 0.0% |
| BIOS Config | 12 | 0 | 1 | 11 | 8.3% |
| Cross-Platform | 12 | 0 | 0 | 12 | 0.0% |
| SwAS: Quiesce & Throttling | 5 | 0 | 0 | 5 | 0.0% |
| SwAS: Interrupt Errata | 2 | 0 | 0 | 2 | 0.0% |
| SwAS: Unused Error Paths | 4 | 0 | 0 | 4 | 0.0% |
| SwAS: ISR/DPC Pattern | 3 | 0 | 0 | 3 | 0.0% |
| SwAS: I2C-Specific | 5 | 0 | 0 | 5 | 0.0% |
| SwAS: Wake-on-Touch | 5 | 0 | 0 | 5 | 0.0% |
| SwAS: ECO Registry Keys | 10 | 0 | 0 | 10 | 0.0% |
| SwAS: ACPI Encoding | 2 | 0 | 0 | 2 | 0.0% |
| **TOTAL** | **177** | **0** | **18** | **159** | **10.2%** |

> **Note**: "PARTIAL" means related code exists (register dumps, config reads, infrastructure methods) but falls short of a dedicated, automated pass/fail test for that specific requirement. All 36 SwAS-derived test IDs are MISSING — no PythonSV scripts address any SwAS-documented scenario.

---

## Observations & Recommendations

### What Exists Is Good Infrastructure
The repository has solid **infrastructure** for writing tests:
- `thc_common.py` provides project detection, register access, and halt/go primitives
- `metadata/` contains comprehensive register maps, project data, BOM devices, and constants
- `common_utility/` has register R/W helpers, bitwise ops, and table formatting
- `pio_access.py` has a near-complete SPI PIO implementation

### What's Missing Is Automated Test Coverage
The existing scripts are **debug/validation utilities**, not automated test scripts. They:
- Dump register state for human inspection (no assertions)
- Lack pass/fail criteria
- Don't exercise DMA, interrupt, power management, or reset flows
- Don't have test harness integration (no pytest, no test runner framework)

### Recommended Development Priority

1. **DMA Engine** (22 tests, 0% coverage) — Core data path, highest test count, all MISSING
2. **Interrupts** (10 tests, 0% coverage) — Interrupt path is fundamental to touch operation
3. **Power Management** (14 tests, 0% coverage, 4 P1) — Critical for battery life, S0ix, D3
4. **Reset Flows** (9 tests, 0% coverage, 2 P1) — Silicon bring-up blocking
5. **I2C Protocol** (14 tests, 14.3% coverage, 6 P1) — Many P1 items MISSING
6. **BIOS Config** (12 tests, 8.3% coverage, 5 P1) — Post-BIOS validation
7. **Cross-Platform Driver** (12 tests, 0% coverage) — OS-specific behavior differences
8. **Convert existing PARTIAL scripts to full tests** — Add assertions to existing utilities

### SwAS-Derived Priority Additions (Added 2026-03-06)

9. **SwAS I2C Corner Cases** (5 tests, 0% coverage, 2 P1) — IC_DMA_RDLR overflow and RTD3 PRW ACPI crash are **production-impacting P1 gaps**. IC_DMA_RDLR is a simple register read check. RTD3 PRW is an ACPI table audit.
10. **SwAS Quiesce & Throttling** (5 tests, 0% coverage) — Buffer exhaustion defense. 2 of 5 are PythonSV-feasible via register observation.
11. **SwAS Wake-on-Touch** (5 tests, 0% coverage) — WoT is user-facing but hard to test via PythonSV; needs sleep/wake cycle infrastructure.
12. **SwAS Interrupt Errata** (2 tests, 0% coverage, 1 P1) — Level-to-edge boot switch (SWAS-I-002) is P1 and PythonSV-feasible.
13. **SwAS ECO Registry Keys** (10 tests, 0% coverage) — All require Windows driver test infrastructure, outside PythonSV scope. Flag for WDK/HLK test development.
14. **SwAS ISR/DPC Pattern** (3 tests, 0% coverage) — 2 of 3 are PythonSV-feasible via GBL_INT_EN observation.
15. **SwAS Unused Error Paths** (4 tests, 0% coverage) — Low priority P3 negative tests, but useful for completeness.
16. **SwAS ACPI Encoding** (2 tests, 0% coverage) — ACPI table parsing + SPI clock verification; PythonSV-feasible.

### PythonSV-Feasible SwAS Tests (Quick Wins)

The following SwAS-derived tests can be implemented with **existing PythonSV infrastructure** (register reads, ACPI dumps, timing):

| ID | Description | How to Implement |
|----|-------------|-----------------|
| SWAS-I2C-001 | IC_DMA_RDLR ≤ 7 | Read `IC_DMA_RDLR` register, assert value ≤ 7 |
| SWAS-I2C-003 | RTD3 PRW ACPI audit | Dump ACPI table, grep for Power Resource on THC device |
| SWAS-I-002 | Level-to-edge boot switch | Read INT config register before/after first device reset |
| SWAS-D-001 | ISR masks GBL_INT_EN | Observe GBL_INT_EN bit 31 during interrupt sequence |
| SWAS-D-002 | DPC unmasks GBL_INT_EN | Observe GBL_INT_EN bit 31 after interrupt processing |
| SWAS-Q-001 | Quiesce during reset | Set QUIESCE_EN, verify INT_STS behavior |
| SWAS-Q-003 | Quiesce on D0Exit | Observe QUIESCE_EN around PM state transitions |
| SWAS-ACPI-001 | ACPI freq encoding | Parse ACPI, verify SPI clock matches encoded value |
| SWAS-ACPI-002 | LimitPacketSize | Parse ACPI, verify packet size matches encoding |
| SWAS-I2C-004 | I2C reset timeout 5s | Time device reset sequence, verify ≥5s timeout |
