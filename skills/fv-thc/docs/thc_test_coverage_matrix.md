# THC IP Test Coverage Matrix

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> Maps THC IP HAS v4.x requirements to test categories, identifies coverage priority, and tracks gaps.
> Last updated: 2026-03-06 | Source: SIP_THC_4x_HAS (September 02, 2025) + Driver Source Code Audit (2026-03-05) + QuickSPI/QuickI2C SwAS v1.0 (2026-03-06)

## Coverage Legend
- **P1**: Must-test (silicon bring-up blocking)
- **P2**: High priority (functional completeness)
- **P3**: Medium priority (corner cases, stress)
- **P4**: Low priority (nice-to-have, rare scenarios)

## 1. PCI Enumeration & Configuration

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| PCI-001 | BAR0 32KB MMIO mapping | P1 | All | Verify BAR0 type, size, and accessibility | |
| PCI-002 | PCI Device ID per platform | P1 | All | Verify DID matches platform (see platform skill) | |
| PCI-003 | THC1 requires THC0 enabled | P1 | All | THC1 enumeration fails if THC0 disabled | |
| PCI-004 | PCIe mode (MTL-S+) | P2 | All | Verify PCIe cap structure at 0xB0 when pciemode=1 | |
| PCI-005 | SetIDValue DID override | P3 | All | Verify upper 9 DID bits overridable via SB msg | |
| PCI-006 | NVL THC1 BDF change | P1 | All | NVL THC1 at Bus=0 Dev=8 Fun=0 (not Dev=16 Fun=1) | |
| PCI-007 | MSI capability | P1 | All | Verify MSI generation from touch interrupt | |
| PCI-008 | LTR capability | P2 | All | Verify LTR register at PCI cap offset | |
| PCI-009 | PM capability (D3-Hot) | P2 | All | Verify D3-Hot entry/exit via PMCSR | |
| PCI-010 | NVL+ PI softstrap | P2 | All | Verify thc_pi_def[7:0] controls PI register | |

## 2. MMIO Register Access

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| REG-001 | Common regs at Base+0x0000 | P1 | All | Read/write common register space | |
| REG-002 | Port 0 regs at Base+0x1000 | P1 | All | Read/write port 0 register space | |
| REG-003 | Port 1 regs at Base+0x2000 | P1 | All | Read/write port 1 register space | |
| REG-004 | BIOS_LOCK_EN sticky | P2 | All | Once set, cannot clear until reset | |
| REG-005 | DRV_LOCK_EN sticky | P2 | All | Once set, cannot clear until reset | |
| REG-006 | Read/Modify/Write for partial | P2 | All | Partial DW writes preserve other bits | |
| REG-007 | SAI access control | P3 | All | Unauthorized SAI rejected on register access | |

## 3. SPI Protocol (HIDSPI)

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SPI-001 | Single IO mode read/write | P1 | HIDSPI | Basic single-IO SPI transactions | |
| SPI-002 | Dual IO mode read/write | P2 | HIDSPI | Dual-IO SPI transactions | |
| SPI-003 | Quad IO mode read/write | P2 | HIDSPI | Quad-IO SPI transactions | |
| SPI-004 | SPI frequency sweep | P1 | HIDSPI | Test across divider range up to 40MHz | |
| SPI-005 | LNL+ half-cycle divider | P2 | HIDSPI | Fractional divider produces correct frequency | |
| SPI-006 | CS# setup/hold timing | P2 | HIDSPI | 30ns min setup and hold | |
| SPI-007 | CS-to-CK delay (LNL+) | P3 | HIDSPI | Programmable CS-to-CK delay | |
| SPI-008 | ICR read opcodes (0B/BB/EB/FB) | P1 | HIDSPI | Verify all ICR opcodes per IO mode | |
| SPI-009 | Dummy clock cycles | P2 | HIDSPI | Correct dummy cycles per IO mode | |
| SPI-010 | Loopback clock compensation | P3 | HIDSPI | Verify loopback clock path functional | |
| SPI-011 | HID descriptor retrieval | P1 | HIDSPI | Read device descriptor (24B) successfully | |
| SPI-012 | Input report read | P1 | HIDSPI | Single touch report via two-phase read | |
| SPI-013 | Output report write | P2 | HIDSPI | Write output report to device | |
| SPI-014 | Feature report get/set | P2 | HIDSPI | Get and set feature reports | |
| SPI-015 | SPI_LOW_FREQ_EN toggle | P2 | HIDSPI | Verify both frequency ranges | |

## 4. I2C Protocol (HIDI2C)

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| I2C-001 | PORT_TYPE=01 for I2C mode | P1 | HIDI2C | Set PORT_TYPE and verify I2C operation | |
| I2C-002 | Standard mode (100KHz) | P2 | HIDI2C | I2C at 100KHz | |
| I2C-003 | Fast mode (400KHz) | P1 | HIDI2C | I2C at 400KHz | |
| I2C-004 | Fast Mode Plus (1MHz) | P2 | HIDI2C | I2C at 1MHz | |
| I2C-005 | SPI_RD_MPS=4KB workaround | P1 | HIDI2C | Must set SPI_RD_MPS to 4096 in I2C mode | |
| I2C-006 | HID descriptor read (30B) | P1 | HIDI2C | Read I2C HID descriptor | |
| I2C-007 | GET_REPORT (Input) | P1 | HIDI2C | Get input report via RXDMA | |
| I2C-008 | GET_REPORT (Feature) | P2 | HIDI2C | Get feature report via RXDMA | |
| I2C-009 | SET_REPORT (Output) | P2 | HIDI2C | Set output report via TXDMA | |
| I2C-010 | SET_POWER command | P2 | HIDI2C | Power state change via PIO | |
| I2C-011 | RESET command | P1 | HIDI2C | Device reset via PIO | |
| I2C-012 | Elan legacy panel (PTL+) | P3 | HIDI2C | Elan-specific workarounds | |
| I2C-013 | I2C NAK retry | P2 | HIDI2C | Device NAK handling and retry | |
| I2C-014 | Clock stretching | P3 | HIDI2C | Device clock stretching tolerance | |

## 5. DMA Engine

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| DMA-001 | RXDMA1 single frame read | P1 | All | Basic DMA read of one frame | |
| DMA-002 | RXDMA2 frame routing | P2 | HIDI2C | Frame Type 1 routes to RXDMA2 | |
| DMA-003 | TXDMA single frame write | P1 | All | Basic DMA write of one frame | |
| DMA-004 | SWDMA SW-triggered read | P2 | All | SWDMA engine triggered by SW (LNL+) | |
| DMA-005 | PRD circular buffer wraparound | P1 | All | CB read/write pointer wraparound | |
| DMA-006 | PRD table max entries (256) | P2 | All | Full PRD table with 256 entries | |
| DMA-007 | CB max tables (128) | P2 | All | Circular buffer with 128 PRD tables | |
| DMA-008 | PRD 4KB alignment (all entries) | P1 | All | Verify RTL bug 15014172472 workaround | |
| DMA-009 | IOC bit MSI generation | P1 | All | Interrupt on PRD entry with IOC=1 | |
| DMA-010 | EOP bit handling | P1 | All | End-of-packet descriptor processing | |
| DMA-011 | Frame size min (64B) | P2 | All | Minimum frame size | |
| DMA-012 | Frame size max (1MB) | P2 | All | Maximum validation frame size | |
| DMA-013 | uFrame size sweep (16B-4KB) | P3 | All | Multiple uFrame sizes | |
| DMA-014 | STALL_STS on PRD exhaustion | P2 | All | PRD table overflow handling | |
| DMA-015 | RXDMA Stop-on-Error | P2 | All | Error stops DMA, status captured | |
| DMA-016 | I2C TX Abort recovery | P2 | HIDI2C | TX abort handling and retry | |
| DMA-017 | Frame coalescing (count-based) | P2 | All | Multiple frames before interrupt | |
| DMA-018 | FCD bypass coalescing | P2 | All | First Contact Detection skips coalesce | |
| DMA-019 | Timing-based coalescing (LNL+) | P3 | All | C_Duration, C_Start_Threshold | |
| DMA-020 | Display sync (VSYNC override) | P3 | All | C_Timer_Override from display | |
| DMA-021 | GuC doorbell ring | P3 | All | GuC notification on frame complete | |
| DMA-022 | PRD descriptor caching | P3 | All | Verify prefetch across boundaries | |

## 6. PIO (Programmed I/O)

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| PIO-001 | SPI PIO register read (7-step) | P1 | HIDSPI | Complete PIO read flow | |
| PIO-002 | SPI PIO register write | P1 | HIDSPI | Complete PIO write flow | |
| PIO-003 | I2C PIO command | P1 | HIDI2C | PIO-based I2C command | |
| PIO-004 | Bus arbitration (PIO > DMA) | P2 | All | PIO has priority over DMA | |
| PIO-005 | Round-robin chicken bit | P3 | All | Override default priority | |
| PIO-006 | No PIO during RXDMA active | P2 | All | SW must not read TIC INT cause during RXDMA | |

## 7. Interrupts

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| INT-001 | GPIO device interrupt (active low) | P1 | HIDSPI | Level-based GPIO interrupt triggers THC | |
| INT-002 | GPIO to MSI routing | P1 | All | Device GPIO → PCI MSI | |
| INT-003 | GBL_INT_EN (bit 31, LNL+) | P2 | All | Global interrupt enable/disable | |
| INT-004 | vGPIO SWGPIO_INT (bit 4) | P3 | All | Software GPIO interrupt | |
| INT-005 | DEVRST interrupt (bit 3) | P2 | All | Device reset interrupt | |
| INT-006 | RX DMA interrupt status | P1 | All | THC_M_PRT_DMA_READ_INT_STS | |
| INT-007 | TX DMA interrupt status | P1 | All | THC_M_PRT_DMA_WRITE_INT_STS | |
| INT-008 | Error interrupts (TXN_ERR) | P2 | All | Transaction error interrupt | |
| INT-009 | Boot: level-trigger during init | P2 | All | Level-trigger before device reset, edge after | |
| INT-010 | THC_DEVINT_QUIESCE_EN | P3 | All | Interrupt quiesce during power transitions | |

## 8. Power Management

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| PM-001 | D0i2 HW autonomous entry | P1 | All | Idle timer triggers power gate | |
| PM-002 | D0i2 exit on interrupt | P1 | All | Device interrupt wakes from D0i2 | |
| PM-003 | D0i2 entry timer max (1s) | P2 | All | Programmable timer up to 1 second | |
| PM-004 | D3-Hot entry/exit | P1 | All | Software-initiated D3-Hot | |
| PM-005 | D3 save/restore (28 regs) | P1 | All | All 28 registers saved and restored correctly | |
| PM-006 | D3 4-level flow (PTL+) | P2 | All | All 4 D3 levels | |
| PM-007 | LTR active state reporting | P2 | All | Correct LTR value in active state | |
| PM-008 | LTR low-power state reporting | P2 | All | Correct LTR value in LP state | |
| PM-009 | Infinite LTR on cold boot | P2 | All | LTR infinite on boot/reset/Vnn removal | |
| PM-010 | S0ix entry/exit with touch | P2 | All | Touch survives S0ix transition | |
| PM-011 | Wake-on-Touch (WoT) | P2 | All | Touch wakes system from sleep (Linux 6.17+) | |
| PM-012 | CGPG clock gating >98% | P3 | All | Clock gating efficiency target | |
| PM-013 | Power gate exit <10us | P2 | All | PG exit latency within spec | |
| PM-014 | PMCLite sideband messages | P3 | All | Correct SB message exchange with PMC | |

## 9. Reset Flows

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| RST-001 | G3 exit / cold boot | P1 | All | Full init from power-on | |
| RST-002 | Soft reset (PSRST+DEVRST+TSFTRST) | P2 | All | Software-initiated reset sequence | |
| RST-003 | Cold reset | P2 | All | Platform cold reset recovery | |
| RST-004 | Warm reset | P2 | All | Platform warm reset recovery | |
| RST-005 | Global reset | P2 | All | Global reset same as cold boot | |
| RST-006 | GPIO reset during reset_warn | P2 | All | GPIO asserted during reset_warn | |
| RST-007 | Controller init after reset | P1 | All | PCI enum → BAR → driver init | |
| RST-008 | SPI_IO_RDY wait | P2 | HIDSPI | Wait for SPI IO ready after reset | |
| RST-009 | Device init state polling (0-4) | P2 | All | Poll through 4 device init states | |

## 10. Stress & Error

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| STR-001 | Continuous touch streaming | P2 | All | Long-duration touch data | |
| STR-002 | Power cycle during DMA | P2 | All | Reset during active DMA | |
| STR-003 | Multi-port simultaneous | P2 | All | THC0 + THC1 concurrent operation | |
| STR-004 | DMA overrun recovery | P2 | All | RX FIFO overflow handling | |
| STR-005 | Bus error recovery | P3 | All | SPI/I2C bus error and retry | |
| STR-006 | Max frame rate sustained | P3 | All | Device at maximum report rate | |

## 11. DFT & Debug

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| DFT-001 | VISA 2-lane debug | P3 | All | VISA trace capture | |
| DFT-002 | TSI device emulation (DFX_Mode_En) | P3 | TSI | 9-step emulation flow | |
| DFT-003 | Performance counters accuracy | P3 | All | All 7+ counters increment correctly | |
| DFT-004 | SWDMA debug reads | P2 | All | SW-triggered DMA for debug | |

## 12. BIOS Configuration Validation (BWG-Derived)

> Source: Chap69_BIOS_WG_THC.docx (Rev 0.5). ⚠️ TGP-era document — verify register defaults on PTL+/NVL.

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| BIOS-001 | BIOS_LOCK_EN set before OS handoff | P1 | All | Verify BIOS_LOCK_EN is set after BIOS init completes | |
| BIOS-002 | THC_CFG_PCE HAE programmed | P1 | All | Verify HAE=1 (default) for HW autonomous PG | |
| BIOS-003 | THC_CFG_PCE D3HE programmed | P2 | All | Verify D3HE set when D3-Hot power gating required | |
| BIOS-004 | SAI policy regs not all-zero | P2 | All | Verify P39h:20h–3Ch configured (not default 0x0) | |
| BIOS-005 | CDC config matches expected state | P2 | All | Verify P39h:0h–Ch match normal (CCC0) or CG (CCC3) | |
| BIOS-006 | Port config matches physical BOM | P1 | All | PORT_SUPPORTED matches connected ports, FD matches disabled | |
| BIOS-007 | LTR values programmed by BIOS | P2 | All | ACT_LTR_VAL/SCALE and LP_LTR_VAL/SCALE non-default | |
| BIOS-008 | MSFT G5 panel bit (MMIO 0x1128 bit31) | P2 | All | Bit 31 set for MSFT G5 panels, clear otherwise | |
| BIOS-009 | Function disable flow correct | P2 | All | CG enabled → HAE=1 → D3 → FD=1 (4-step order) | |
| BIOS-010 | S3 resume full re-init | P1 | All | BIOS re-runs complete init flow on S3 resume | |
| BIOS-011 | DEVRST before D3/Sx entry | P1 | All | BIOS/driver asserts DEVRST before D3 entry | |
| BIOS-012 | GPIO IOSTANDBY config | P2 | All | THC-SPI GPIOs retain last values on Vnn removal | |

## Coverage Summary

| Category | P1 | P2 | P3 | P4 | Total |
|----------|----|----|----|----|-------|
| PCI Enumeration | 5 | 4 | 1 | 0 | 10 |
| MMIO Registers | 3 | 3 | 1 | 0 | 7 |
| SPI Protocol | 5 | 8 | 2 | 0 | 15 |
| I2C Protocol | 6 | 6 | 2 | 0 | 14 |
| DMA Engine | 6 | 11 | 5 | 0 | 22 |
| PIO | 3 | 2 | 1 | 0 | 6 |
| Interrupts | 4 | 4 | 2 | 0 | 10 |
| Power Mgmt | 4 | 8 | 2 | 0 | 14 |
| Reset Flows | 2 | 7 | 0 | 0 | 9 |
| Stress & Error | 0 | 4 | 2 | 0 | 6 |
| DFT & Debug | 0 | 1 | 3 | 0 | 4 |
| BIOS Config (BWG) | 5 | 7 | 0 | 0 | 12 |
| Cross-Platform Driver | 2 | 7 | 3 | 0 | 12 |
| SwAS: Quiesce & Throttling | 0 | 5 | 0 | 0 | 5 |
| SwAS: Interrupt Errata | 1 | 1 | 0 | 0 | 2 |
| SwAS: Unused Error Paths | 0 | 0 | 4 | 0 | 4 |
| SwAS: ISR/DPC Pattern | 0 | 2 | 1 | 0 | 3 |
| SwAS: I2C-Specific | 2 | 2 | 1 | 0 | 5 |
| SwAS: Wake-on-Touch | 0 | 5 | 0 | 0 | 5 |
| SwAS: ECO Registry Keys | 0 | 3 | 7 | 0 | 10 |
| SwAS: ACPI Encoding | 0 | 2 | 0 | 0 | 2 |
| **TOTAL** | **48** | **92** | **37** | **0** | **177** |

## 13. Cross-Platform Driver Validation (Audit-Derived)

> Added from exhaustive driver source code audit (2026-03-05).
> Tests verify that skill documentation matches actual driver behavior across Linux and Windows.

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| XPLAT-001 | DMA pause timeout matches per OS | P2 | All | Linux: 100µs/10ms, Windows: 10µs/1s | |
| XPLAT-002 | DMA pause polls correct register | P1 | All | Must poll INT_STS, not DMA_CNTRL | |
| XPLAT-003 | SET_POWER behavior per OS | P2 | All | Linux fire-and-forget vs Windows synchronous | |
| XPLAT-004 | IC_CON init matches per OS | P2 | HIDI2C | Linux 0x663 direct vs Windows field-by-field | |
| XPLAT-005 | SWDMA save/restore per OS | P2 | All | Linux selective vs Windows full cycle | |
| XPLAT-006 | SPI base clock = 125 MHz | P1 | HIDSPI | Verify 125 MHz not 128 MHz in all calculations | |
| XPLAT-007 | PIO opcodes read=0x4/write=0x6/bulk=0x8 | P2 | All | Verify correct opcodes used in PIO flows | |
| XPLAT-008 | RXDMA1 unused for I2C (size=0) | P2 | HIDI2C | RXDMA2 is primary I2C input path | |
| XPLAT-009 | Host Reset via TXDMA not PIO | P2 | HIDI2C | write_cmd_to_txdma() not PIO opcode 0x18 | |
| XPLAT-010 | Output report PM gap validation | P3 | All | Verify output_report lacks PM runtime handling | |
| XPLAT-011 | I2C FS_HCNT/LCNT per OS | P3 | HIDI2C | Windows 500/588 vs Linux 146/156 | |
| XPLAT-012 | LTR unconfig — no toggle pattern | P3 | All | Clears 4 bits directly, no 0→1→0 toggle | |

## 14. SwAS-Derived Test Scenarios (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 + QuickI2C SwAS v1.0.
> These test IDs cover driver-level behaviors, errata workarounds, and corner cases documented in the SwAS
> that are not covered by the HAS-based matrix above.

### 14.1 Quiesce & Buffer Throttling

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-Q-001 | Quiesce during host-initiated reset | P2 | All | THC_DEVINT_QUIESCE_EN=1 during reset flow, verify no device interrupts processed | |
| SWAS-Q-002 | Buffer threshold throttling at 50% | P2 | All | Fill RX buffers to 8 of 16 free, verify driver quiesces device until all buffers freed | |
| SWAS-Q-003 | Quiesce on D0Exit before D3 | P2 | All | Verify quiesce asserted before D3 entry, cleared after D0 re-entry | |
| SWAS-Q-004 | No quiesce within ISR/DPC | P2 | All | Verify driver never asserts quiesce inside interrupt service routine or DPC | |
| SWAS-Q-005 | RAW_INT_STS MSI blocked during quiesce (LNL) | P2 | All | LNL errata P0587: verify MSI not generated when QUIESCE_EN is set | |

### 14.2 Interrupt Edge Detection Errata

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-I-001 | Double interrupt on slow FW deassert (pre-LNL) | P2 | HIDSPI | P0582: send interrupt, delay FW deassert >1 edge sample, verify no double processing | |
| SWAS-I-002 | Level-to-edge trigger switch at boot | P1 | All | Boot with level-trigger, after first reset interrupt received switch to edge-trigger | |

### 14.3 Unused Error Paths (Negative Testing)

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-E-001 | Write DMA error path not firing | P3 | All | P0635: inject TX DMA error condition, confirm THC does not raise (HW not implemented) | |
| SWAS-E-002 | Fatal Error path not firing | P3 | All | P0636: confirm Fatal Error interrupt never fires (not implemented by SW) | |
| SWAS-E-003 | PIO Error path not firing (I2C) | P3 | HIDI2C | P0753: confirm PIO errors not processed by QuickI2C driver | |
| SWAS-E-004 | I2C subIP Error path not firing | P3 | HIDI2C | P0756: confirm I2C subIP errors not processed by QuickI2C driver | |

### 14.4 ISR/DPC Pattern Validation

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-D-001 | ISR masks via GBL_INT_EN | P2 | All | P0603: verify ISR clears GBL_INT_EN bit 31, queues DPC | |
| SWAS-D-002 | DPC unmasks after processing | P2 | All | P0620: verify DPC re-enables GBL_INT_EN after processing all pending work | |
| SWAS-D-003 | ISR/DPC lock (WdfInterruptLock) | P3 | All | P0624: verify ISR and DPC share correct synchronization lock | |

### 14.5 I2C-Specific SwAS Scenarios

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-I2C-001 | IC_DMA_RDLR ≤ 7 constraint | P1 | HIDI2C | P0350: set IC_DMA_RDLR to 8+, verify overflow; confirm driver uses ≤7 | |
| SWAS-I2C-002 | Bus clear SDA/SCL stuck recovery | P2 | HIDI2C | P0771: force SDA low, verify THC bus clear recovery (Windows only; Linux lacks this) | |
| SWAS-I2C-003 | RTD3 PRW ACPI crash prevention | P1 | HIDI2C | P0300: verify ACPI device uses _PS0/_PS3/_DSW, NOT Power Resource with GPIO PRW | |
| SWAS-I2C-004 | I2C reset timeout = 5 seconds | P2 | HIDI2C | P0479: verify I2C device reset waits 5 seconds (vs 1 second SPI per P0341) | |
| SWAS-I2C-005 | I2C max frame size (128-255B) | P3 | HIDI2C | P0857: verify I2C_Max_Frame_Size registry key limits frame size when enabled | |

### 14.6 Wake-on-Touch (WoT)

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-WOT-001 | WoT via vGPIO path (not THC) | P2 | All | P0706: verify wake signal routes through vGPIO, not THC interrupt path | |
| SWAS-WOT-002 | No device reset on WoT exit | P2 | All | P0726: verify driver does NOT reset device when exiting WoT sleep | |
| SWAS-WOT-003 | Windows Wait Wake IRP flow | P2 | All | P0706: verify Windows extension INF registers Wait Wake IRP for WoT | |
| SWAS-WOT-004 | I2C SET_POWER(sleep) on WoT entry | P2 | HIDI2C | P0823: verify SET_POWER(sleep) sent to I2C device on WoT entry | |
| SWAS-WOT-005 | I2C SET_POWER(ON) on WoT exit | P2 | HIDI2C | P0851: verify SET_POWER(ON) sent to I2C device on WoT exit, no reset | |

### 14.7 ECO Registry Keys

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-REG-001 | IO_Mode_Override (SPI) | P3 | HIDSPI | P0790: set IO mode override registry key, verify SPI mode changes | |
| SWAS-REG-002 | SPI_Frequency_Override | P3 | HIDSPI | P0791: set frequency override, verify SPI clock changes | |
| SWAS-REG-003 | TxDMA_Override (SPI) | P3 | HIDSPI | P0793: set TxDMA override, verify TX DMA behavior changes | |
| SWAS-REG-004 | I2C_Max_Frame_Size_Enable + Size | P3 | HIDI2C | P0857: enable key and set size 128-255, verify frame size limited | |
| SWAS-REG-005 | I2C_Int_Delay_Enable + Delay | P3 | HIDI2C | P0880: enable interrupt delay, verify delay applied (1ms PTL/WCL) | |
| SWAS-REG-006 | EnEdgeTriggeredINT | P2 | All | T7: toggle edge-triggered interrupt mode via registry | |
| SWAS-REG-007 | ResetRequiredByDriver | P2 | All | T7: toggle driver-initiated reset behavior via registry | |
| SWAS-REG-008 | EnResetPollingWA | P2 | All | T7: enable reset polling workaround via registry | |
| SWAS-REG-009 | EnableFWFlashWABOM36 | P3 | All | T7: enable FW flash workaround for BOM36 devices | |
| SWAS-REG-010 | DoNotWaitForResetResponse | P3 | All | T7: skip waiting for device reset response | |

### 14.8 ACPI Frequency & Packet Encoding

| ID | Requirement | Priority | Protocol | Test Description | Status |
|----|-------------|----------|----------|-----------------|--------|
| SWAS-ACPI-001 | ACPI frequency encoding bits 0-2 | P2 | HIDSPI | P0900: verify all 5 encodings: 011=40, 100=30, 101=24, 110=20, 111=17 MHz | |
| SWAS-ACPI-002 | LimitPacketSize ACPI encoding | P2 | HIDSPI | P0912: verify LimitPacketSize encoding from ACPI matches driver behavior | |

## Known Gaps / Not Covered
1. TSI (Touch Sensor Interface) — DPHY-based protocol not POR for SPI/I2C platforms
2. SGX Trusted I/O DMA encryption — requires SGX+TME platform support
3. QuickSPI — Non-POR from PTL+, no active validation
4. OBFF (Optimized Buffer Flush/Fill) — Not supported by THC
5. MSI-X — Not supported (MSI only)
6. Multi-vendor BOM interop — requires physical device matrix
7. BWG register defaults on NVL+/RZL/TTL — BWG is TGP-era, register defaults may differ on Gen4.2 platforms
8. Windows HIDSPI filter driver (IPTS) — proprietary filter interface, limited public documentation
9. TouchSensorRegs.h device-side registers — per EDS 0.71, separate register domain from THC host controller
10. SwAS reset timeout discrepancy — SwAS specifies 1s for SPI (P0341) vs 5s for I2C (P0479), but Linux kernel uses 5s for both; needs clarification whether to test per-SwAS or per-kernel
11. Bus clear on Linux — QuickI2C SwAS P0771 documents SDA/SCL stuck recovery, but Linux kernel does not implement it; gap exists only on Linux platforms
12. WoT extension INF — Windows WoT requires vendor-specific extension INF to register Wait Wake IRP; not all BOM vendors provide this
