# THC Known Issues, RTL Bugs & HSDES Sightings Tracker

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> Consolidated tracker of all known THC IP issues discovered during HAS review, validation, and driver source code audit.
> Last updated: 2026-03-06 | Source: SIP_THC_4x_HAS v4.x + FV experience + Driver Source Code Audit (2026-03-05) + SwAS v1.0 (2026-03-06)

## Critical RTL Bugs

### BUG-001: PRD Last Entry Alignment (15014172472)
- **HSDES**: 15014172472
- **Severity**: Critical
- **Affected**: All platforms with THC DMA (Gen2+)
- **Description**: HAS spec states only non-last PRD entries require 4KB alignment. RTL actually requires ALL entries (including last) to be 4KB aligned.
- **Impact**: DMA data corruption or hang if last PRD buffer is not 4KB-aligned
- **Workaround**: Always allocate 4KB-aligned buffers for ALL PRD entries
- **Status**: RTL bug — workaround in SW
- **Relevant skill**: `fv-thc/dma`

### BUG-002: SPI_RD_MPS Used in I2C Mode
- **HSDES**: TBD (documented in HAS)
- **Severity**: Critical
- **Affected**: All platforms with HIDI2C (LNL+ Gen4.0+)
- **Description**: THC RTL incorrectly references the SPI_RD_MPS register even when operating in I2C mode. The data path shares the SPI MPS register for both protocols.
- **Impact**: I2C DMA reads may be truncated or corrupted if SPI_RD_MPS is not set to maximum
- **Workaround**: Software MUST program SPI_RD_MPS to 4096 (4KB) when using I2C mode
- **Status**: RTL bug — workaround in SW (driver and BIOS)
- **Relevant skill**: `fv-thc/hidi2c`

## HSDES Compliance Issues

### HSDES-001: Chassis 2.2 Non-Compliance (16014286225)
- **HSDES**: 16014286225
- **Severity**: Medium
- **Affected**: All platforms
- **Description**: THC is not fully Chassis 2.2 compliant. *RES_EN bits default to 0 (disabled).
- **Impact**: Sleep state resource management may not work as expected per Chassis 2.2 spec
- **Workaround**: PTL POR keeps same behavior as LNL/MTL (RES_EN disabled)
- **Status**: Known limitation — accepted for current generation
- **Relevant skill**: `fv-thc/power`

### HSDES-002: PTL+ 16-bit SB Port ID (15010734105)
- **HSDES**: 15010734105
- **Severity**: High
- **Affected**: PTL and later platforms
- **Description**: PTL+ requires 16-bit IOSF Sideband port ID. Earlier platforms use 8-bit.
- **Impact**: SB messages will fail if 8-bit port ID used on PTL+
- **Workaround**: Platform-aware SB port ID sizing in BIOS and driver
- **Status**: Architecture change — not a bug, but migration required
- **Relevant skill**: `fv-thc/platform`

## Linux Kernel Bug Fixes (THC-related)

### KERN-001: Edge Detection Fix (6.17)
- **Commit**: 8fe2cd8
- **Kernel**: 6.17
- **Description**: Fix edge detection for THC interrupt handling
- **Impact**: Spurious interrupt handling improved
- **Relevant skill**: `fv-thc/debug`

### KERN-002: I2C Register Save Fix (6.20)
- **Commit**: a7fc15e
- **Kernel**: 6.20
- **Description**: Fix I2C register save/restore during D3Cold transitions
- **Impact**: CRITICAL for D3Cold Save-and-Restore reliability
- **Relevant skill**: `fv-thc/power`, `fv-thc/hidi2c`

### KERN-003: WoT Support Added (6.17)
- **Kernel**: 6.17
- **Description**: Wake-on-Touch support added for THC
- **Impact**: Enables touch wake from sleep states
- **Relevant skill**: `fv-thc/power`

### KERN-004: WCL Device IDs (6.18)
- **Kernel**: 6.18
- **Description**: WCL platform Device ID support added
- **Relevant skill**: `fv-thc/platform`

### KERN-005: ARL Device IDs (6.19)
- **Kernel**: 6.19
- **Description**: ARL platform Device ID support added
- **Relevant skill**: `fv-thc/platform`

### KERN-006: DMA Safety Improvements (6.19)
- **Kernel**: 6.19
- **Description**: DMA safety improvements for THC
- **Relevant skill**: `fv-thc/dma`

### KERN-007: QuickI2C Output Reports (6.20)
- **Kernel**: 6.20
- **Description**: QuickI2C output report support added
- **Relevant skill**: `fv-thc/hidi2c`

## NVL-Specific Known Sightings

### NVL-001 through NVL-006
See `fv-thc/debug` sub-skill for 6 active NVL sightings with full details.

## HAS Reviewer Notes (Open Items)

### REVIEW-001: SnR Register List Outdated — CONFIRMED (HAS Gap)
- **Source**: HAS Appendix A reviewer note
- **Description**: The Save-and-Restore register list in Appendix A is flagged as outdated and needs update
- **Impact**: D3 save/restore may miss registers not in the current list
- **Co-De Sign validation (2026-03-08)**: Queried `sip_thc_4x_has.html` for complete SnR register list. HAS only explicitly lists **3 registers** for D3 save/restore:
  1. `SWGPIO_INT` (MMIO, offset varies) — explicitly says "needs be in save/restore list"
  2. `THC_SB_PM_CTRL` (offset 0x48) — power management control
  3. `THC_CFG_PMCAP_PMNP_PMCID` (offset 0x70) — PCI PM capability
  HAS notes: "scrub through all register space to see if there are any chicken bits" and "full list may be platform-dependent, consult integration guide"
- **Driver reality**: Linux saves/restores ~28 registers; Windows does full unconfigure/reconfigure cycle. Both handle far more than the 3 HAS-listed registers.
- **Conclusion**: HAS SnR list is a known documentation gap. The authoritative SnR list must be derived from driver source code analysis (see `fv-thc/power` and `fv-thc/registers` sub-skills for the complete driver-derived lists).
- **Status**: CONFIRMED — HAS gap documented. No further action unless HAS is updated with a complete list.
- **Relevant skill**: `fv-thc/registers`, `fv-thc/power`

### REVIEW-002: WoG (Wake on Gesture) Opens — CLOSED
- **Source**: HAS section on GPIO Reset/Power
- **Description**: WoG feature has many open items, not POR
- **Impact**: Wake-on-Gesture not validated
- **Action**: No action needed unless WoG becomes POR
- **Status**: CLOSED (2026-03-08) — WoG is not POR on any current platform (PTL/WCL/NVL/RZL/TTL). Re-open if WoG becomes POR in a future generation.

## Cross-Platform Recurring Patterns

See `fv-thc/debug` sub-skill for 7 identified cross-platform recurring failure patterns.

## BWG Document Age Caveat

### BWG-001: BIOS Writer Guide is TGP-Era
- **Document**: Chap69_BIOS_WG_THC.docx (Rev 0.5, March 2017, last modified 2024-09-24 by Kevin Zhenyu Zhu)
- **Severity**: Medium (information risk)
- **Affected**: All platforms — BWG content integrated into `fv-thc/platform`, `fv-thc/power`, `fv-thc/registers`
- **Description**: The THC BIOS Writer Guide is based on TGP-era IP. While the 2024 update added MTL+ DID bit[16] RWOnce, most register defaults, flow descriptions, and policy knobs have NOT been verified against Gen4.1 (PTL/WCL) or Gen4.2 (NVL/RZL/TTL) silicon.
- **Stale items identified**:
  - D0i3 discussion (TGP decided "not supported" — status on newer platforms unverified)
  - ICC SSC disable dependency (marked as open item — BIOS may not have access)
  - Class code assignment (noted "not finalized" — should be finalized by now)
  - THC_CFG_PCE bit defaults may differ per platform stepping
- **Impact**: BWG-sourced register values and flow sequences may not match current silicon behavior on PTL+/NVL
- **Workaround**: Always cross-reference BWG content against: (1) THC IP HAS v4.x (`sip_thc_4x_has.html`), (2) platform-specific BIOS code, (3) actual register reads on target silicon
- **Status**: Documented caveat — BWG sections marked with ⚠️ in all skill files
- **Relevant skills**: `fv-thc/platform`, `fv-thc/power`, `fv-thc/registers`
- **Reference**: `fv-thc/docs/thc_bwg_extraction.md`

## Skill Documentation Issues (Fixed in Driver Source Code Audit — 2026-03-05)

> These issues were discovered during an exhaustive 3-pass cross-check audit of all THC driver source code
> (Linux kernel v6.17-6.20, Windows HIDSPI v4.0.0.9000, Windows HIDI2C v3.0.0.9000) against all 8 THC sub-skill files.
> All issues below have been FIXED in the skill files.

### DOC-001: SPI Base Clock Frequency Wrong
- **Skill**: `fv-thc/hidspi`, `fv-thc/registers`
- **Was**: 128 MHz base clock, formula = base / (divider × 2)
- **Actual**: 125 MHz base clock, formula = base / divider
- **Source**: Linux `intel-thc-hw.h` THC_SPI_DEFAULT_CLOCK_HZ = 125000000
- **Impact**: All SPI frequency calculations were wrong

### DOC-002: LTR Unconfig Toggle Pattern Fabricated
- **Skill**: `fv-thc/power`
- **Was**: "0→1→0 toggle pattern on THC_LTR_EN"
- **Actual**: No toggle. Clears 4 bits (LP_LTR_EN, ACTIVE_LTR_EN, LP_LTR_REQ, ACTIVE_LTR_REQ). No field named THC_LTR_EN exists.
- **Source**: Linux `intel-thc-dev.c` thc_ltr_unconfig()
- **Impact**: Skill described a procedure that doesn't exist in any driver

### DOC-003: SPI PIO Opcodes Wrong
- **Skill**: `fv-thc/hidspi`, `fv-thc/registers`
- **Was**: Write opcode = 0x2
- **Actual**: Read=0x4, Write=0x6, Bulk Write=0x8
- **Source**: Linux `intel-thc-hw.h` THC_PIO_OP_*
- **Impact**: PIO write operations would use wrong opcode

### DOC-004: DEVINT_CFG Register Offsets Wrong
- **Skill**: `fv-thc/registers`
- **Was**: Incorrect offsets for DEVINT_CFG_1/2
- **Actual**: DEVINT_CFG_1=0x0EC, DEVINT_CFG_2=0x0F0
- **Source**: Linux `intel-thc-hw.h`
- **Impact**: Interrupt configuration register access at wrong addresses

### DOC-005: IC_CON Default Value Wrong
- **Skill**: `fv-thc/hidi2c`
- **Was**: 0x665
- **Actual**: Linux writes 0x663; Windows builds field-by-field
- **Source**: Linux `quicki2c-protocol.c` quicki2c_init_i2c_sub_ip()
- **Impact**: I2C sub-IP initialization documentation was inaccurate

### DOC-006: Default I2C Target Address Wrong
- **Skill**: `fv-thc/hidi2c`
- **Was**: 0x086
- **Actual**: 0x0A
- **Source**: Linux `pci-quicki2c.c` DEFAULT_HIDI2C_TGT_ADDR
- **Impact**: I2C address documentation was wrong

### DOC-007: Host Reset / SET_POWER Transport Wrong
- **Skill**: `fv-thc/hidi2c`
- **Was**: Via PIO opcode 0x18
- **Actual**: Via TXDMA using write_cmd_to_txdma()
- **Source**: Linux `quicki2c-protocol.c`
- **Impact**: Described wrong transport mechanism for I2C commands

### DOC-008: RXDMA Channel Usage for I2C Wrong
- **Skill**: `fv-thc/hidi2c`, `fv-thc/dma`
- **Was**: RXDMA1 used for I2C input
- **Actual**: RXDMA1 size=0 (not used for I2C). RXDMA2 is primary input path.
- **Source**: Linux `quicki2c-protocol.c` quicki2c_dma_init()
- **Impact**: DMA channel assignment documentation was inverted for I2C

### DOC-009: DMA Pause Timeout Values Wrong
- **Skill**: `fv-thc/dma`
- **Was**: "1ms per poll × 1000 iterations = 1 second"
- **Actual**: Linux: 100µs interval / 10ms timeout. Windows: 10µs interval / 1s timeout.
- **Source**: Linux `intel-thc-dma.c`, Windows `Dma.h` DEFAULT_QUIESCE_POLLING_*
- **Impact**: Timeout values were completely wrong

### DOC-010: DMA Pause Polls Wrong Register
- **Skill**: `fv-thc/dma`
- **Was**: Polls DMA_CNTRL register
- **Actual**: Polls READ_DMA_INT_STS register
- **Source**: Linux `intel-thc-dma.c` thc_dma_set_max_packet_sizes()
- **Impact**: Debug guidance pointed to wrong register for DMA stall diagnosis

### DOC-011: PIO Timeout Value Wrong
- **Skill**: `fv-thc/registers`
- **Was**: 3 seconds
- **Actual**: 1 second
- **Source**: Linux `intel-thc-dev.c` THC_PIO_TIMEOUT_US
- **Impact**: Timeout expectations too generous — could mask real hangs

### DOC-012: QuickSPI Probe Sequence Wrong
- **Skill**: `fv-thc/hidspi`, `fv-thc/driver`
- **Was**: DMA init before reset; wrong step count
- **Actual**: 14 steps; DMA init happens AFTER device reset
- **Source**: Linux `pci-quickspi.c` quickspi_probe()
- **Impact**: Probe flow documentation misled debug of init failures

### DOC-013: QuickSPI Reset Flow Wrong
- **Skill**: `fv-thc/driver`
- **Was**: GPIO LOW/HIGH with level-triggered interrupt
- **Actual**: ACPI _RST method with edge-triggered interrupt detection
- **Source**: Linux `pci-quickspi.c` quickspi_reset()
- **Impact**: Reset debug guidance used wrong mechanism

### DOC-014: Windows Driver Versions Missing
- **Skill**: `fv-thc/debug`
- **Was**: Wrong or missing version numbers
- **Actual**: HIDSPI v4.0.0.9000, HIDI2C v3.0.0.9000
- **Source**: Windows `Ver.h` (both drivers)
- **Impact**: Version identification was inaccurate for debug triage

### DOC-015: Output Report PM Handling Gap Undocumented
- **Skill**: `fv-thc/driver`
- **Was**: Not mentioned
- **Actual**: output_report() has NO pm_runtime_get/put — potential bug where device could be in D3
- **Source**: Linux `quickspi-hid.c` quickspi_hid_output_report()
- **Impact**: Missing documentation of a potential driver bug

## Validation Notes

### SwAS-Derived Errata (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0. These are driver architecture specification issues, not RTL bugs.

### SWAS-001: P0582 — Double Interrupt Processing on Pre-LNL (QuickSPI)
- **Source**: QuickSPI SwAS v1.0, P0582
- **Severity**: High
- **Affected**: Pre-LNL platforms (THC processes interrupt edge twice when device FW is slow to deassert)
- **Description**: THC processes the interrupt edge twice if the device firmware is slow to deassert the interrupt line. The second processing is spurious.
- **Workaround**: Configure interrupt as **level-triggered** for the first interrupt, then switch to **edge-triggered** after the initial reset interrupt is received.
- **Status**: Driver workaround (edge detection fix in kernel 6.17, commit 8fe2cd8)
- **Relevant skill**: `fv-thc/hidspi`, `fv-thc/debug`

### SWAS-002: P0587 — RAW_INT_STS MSI Blocked During Quiesce (LNL RTL)
- **Source**: QuickSPI SwAS v1.0, P0587
- **Severity**: Medium
- **Affected**: LNL (RTL issue)
- **Description**: MSI is not generated from RAW_INT_STS when `THC_DEVINT_QUIESCE_EN` is set. This is an LNL RTL issue where the quiesce mechanism over-blocks MSI generation.
- **Impact**: Interrupt-driven operations are blocked during quiesce — driver must not expect MSI delivery while quiesced.
- **Status**: LNL RTL limitation — documented behavior
- **Relevant skill**: `fv-thc/registers`, `fv-thc/debug`

### SWAS-003: P0635-P0637 — Unused Error Categories (QuickSPI/QuickI2C)
- **Source**: QuickSPI SwAS v1.0 P0635-P0637; QuickI2C SwAS v1.0 P0753-P0756
- **Severity**: Informational
- **Affected**: All platforms
- **Description**: The following error categories are defined in HAS but **not implemented** by SW or HW:
  - Write DMA Errors (TXDMA error interrupts)
  - Fatal Errors
  - PIO Errors (I2C only)
  - I2C Sub-IP Errors (I2C only)
- **Impact**: Test scripts should NOT expect these error paths to fire. Error injection tests targeting these categories will not produce results.
- **Status**: By design — documented as unused
- **Relevant skill**: `fv-thc/dma`, `fv-thc/registers`

### SWAS-004: RTD3 PRW ACPI Crash (QuickI2C)
- **Source**: QuickI2C SwAS v1.0, P0300-P0317
- **Severity**: Critical
- **Affected**: All I2C platforms with wake-capable touch devices
- **Description**: Adding `_PRW` (Power Resources for Wake) on the ACPI device node with GPIO causes **Windows crash**. Windows interprets PRW as D3cold-capable and issues WaitWake IRP, which crashes when GPIO controller is in a different power domain.
- **Workaround**: Use `_PS0`/`_PS3`/`_DSW` methods instead of Power Resource. No D3cold; `_S0W` returns 3; `_DSW` modifies `_PS3` behavior.
- **Status**: ACPI design constraint — BIOS must not use PRW for THC I2C devices
- **Relevant skill**: `fv-thc/power`, `fv-thc/hidi2c`, `fv-thc/platform`

### SWAS-005: IC_DMA_RDLR ≤ 7 Constraint (QuickI2C)
- **Source**: QuickI2C SwAS v1.0, P0350-P0356
- **Severity**: Medium
- **Affected**: All I2C platforms
- **Description**: The THC internal temp buffer can store a maximum of 8 bytes. Setting `IC_DMA_RDLR` > 7 will cause buffer overflow within the I2C Sub-IP.
- **Impact**: I2C sub-IP initialization MUST set IC_DMA_RDLR ≤ 7. Linux kernel uses IC_DMA_RDLR = 7.
- **Status**: Hardware constraint — documented
- **Relevant skill**: `fv-thc/hidi2c`, `fv-thc/registers`

### SWAS-006: Bus Clear Not Enabled on Linux (QuickI2C)
- **Source**: QuickI2C SwAS v1.0, P0771
- **Severity**: Low
- **Affected**: Linux I2C platforms
- **Description**: THC supports SDA/SCL stuck bus clear recovery per HAS. Windows enables this feature; Linux does **NOT**.
- **Impact**: Linux I2C may not recover from SDA/SCL stuck conditions. Test scripts on Linux should not expect bus clear recovery.
- **Status**: Linux driver limitation — feature not enabled
- **Relevant skill**: `fv-thc/hidi2c`, `fv-thc/debug`

## Validation Notes

### Things That Catch People Off Guard
1. **THC1 won't enumerate** → Check THC0 is enabled first (THC1 is Function 1)
2. **I2C DMA reads truncated** → Set SPI_RD_MPS to 4KB even in I2C mode
3. **DMA hang on last PRD** → All PRD buffers must be 4KB aligned (not just non-last)
4. **SB messages fail on PTL** → Use 16-bit port ID, not 8-bit
5. **D3 resume fails** → Check SnR register list matches actual RTL requirements
6. **NVL THC1 not found** → BDF changed to Dev=8 Fun=0 (not Dev=16 Fun=1)
7. **Loopback clock issues at high freq** → Verify SPI loopback clock path is functional
8. **Chassis 2.2 sleep state failures** → RES_EN bits default disabled — by design
9. **Spurious double interrupts pre-LNL** → Configure level-triggered first, switch to edge after reset (SWAS-001)
10. **No MSI during quiesce on LNL** → RAW_INT_STS MSI blocked when QUIESCE_EN set (SWAS-002)
11. **Windows crash on I2C RTD3 with PRW** → Use _PS0/_PS3/_DSW, not Power Resource (SWAS-004)
12. **I2C RX overflow at IC_DMA_RDLR > 7** → THC temp buffer is only 8 bytes (SWAS-005)
13. **SPI reset timeout 1s vs I2C 5s** → SwAS specifies different timeouts per protocol; kernel uses 5s for both
14. **Write DMA / Fatal error interrupts never fire** → These error paths are unused by design (SWAS-003)
