# THC Sub-Skill EVAL Test Cases

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> These test prompts validate that the FV-THC sub-skills contain correct and complete domain knowledge from the THC IP HAS v4.x.
> Run via EVAL-THC-* agents. Each test has an expected answer and pass criteria.

## Registers Sub-Skill Tests

### REG-001: MMIO Port Restore Order
**Prompt**: "What is the restore order for THC MMIO port registers during D3 save/restore? Which registers must be restored before DMA registers?"
**Expected**: Restore order groups 3.102-3.146, port control/SPI config before DMA, GuC doorbell last (5.1)
**Pass Criteria**: Mentions restore order numbers AND priority sequence

### REG-002: PCIe Capability Offsets
**Prompt**: "What is the PCIe Capability Structure offset for THC when in PCIe mode? What is the Cap ID?"
**Expected**: Offset 0xB0, Cap ID 0x10, Version 2h, PCIe Endpoint type
**Pass Criteria**: Correct offset (0xB0) AND Cap ID (0x10)

### REG-003: Transaction Attributes
**Prompt**: "What transaction types does THC support on the upstream IOSF Primary interface? What is the max payload for posted upstream?"
**Expected**: MRd32, MRd64, MWr32, MWr64, MsgD, Cpl, CplD upstream; 64B posted upstream
**Pass Criteria**: Lists at least 5 upstream types AND mentions 64B

### REG-004: BAR Configuration
**Prompt**: "What is THC BAR0 size and type? Which BARs are unused?"
**Expected**: BAR0 Type 0, 32KB range, BAR1-5 and ROMBAR unused
**Pass Criteria**: 32KB AND BAR1-5 unused

### REG-005: Reset Domain Exception
**Prompt**: "Which THC registers use the thc_sb_rst reset domain instead of thc_core_rst_b?"
**Expected**: THC_CFG_PCE.HAE, THC_SB_SSC_CLK_CFG, THC_SB_ROSC_CLK_CFG, THC_SB_DCGE_CFG, THC_BUS_NUM
**Pass Criteria**: Mentions at least 3 of the 5 registers

## Power Sub-Skill Tests

### PWR-001: Power Domains
**Prompt**: "What are the two THC power domains and what is the isolation requirement between them?"
**Expected**: THC_PGD (power-gateable) and THC_UGD (un-gated). Isolation required PGD→UGD, NOT required UGD→PGD
**Pass Criteria**: Names both domains AND correct isolation direction

### PWR-002: Chassis 2.2 Resource Bits
**Prompt**: "What are the 10 resource bits in THC's Chassis 2.2 resource_own_req/ack? What does bit 6 represent?"
**Expected**: 10-bit mapping: Memory(0), IOSF Pri(1), IOSF SB(2), CORE clk(3), SB clk(4), PGCB clk(5), Vcc_Main/Vnn(6), ROSC clk(7), SS clk(8), GPIO(9). Bit 6 = Vcc_Main (Vnn)
**Pass Criteria**: Correct bit 6 identification AND at least 5 other bits named

### PWR-003: Power Goals
**Prompt**: "What is THC's maximum dynamic power and power-gated leakage from the HAS?"
**Expected**: 4mW max dynamic (PIO+TXDMA+RXDMA+IOSF), <5uW power gated
**Pass Criteria**: 4mW dynamic AND <5uW PG

### PWR-004: Touch IC Power States
**Prompt**: "What are the touch IC device power states and their max power consumption?"
**Expected**: Off(0mW), Sleep(1mW), Doze(5mW), Armed(10mW), Sensing(50mW)
**Pass Criteria**: At least 4 states with correct power values

### PWR-005: Chassis 2.2 Known Bug
**Prompt**: "Is THC fully Chassis 2.2 compliant? If not, what is the HSDES tracking this?"
**Expected**: No, HSDES 16014286225. RES_EN bits default to 0 (disabled)
**Pass Criteria**: Mentions HSDES 16014286225

## HIDSPI Sub-Skill Tests

### SPI-001: LNL+ Clock Divider
**Prompt**: "What clock divider improvement was introduced in LNL for THC SPI? What was the max platform frequency?"
**Expected**: Half-cycle fractional divider, programmable duty cycle, CS-to-CK delay. Max 40MHz (SI limited)
**Pass Criteria**: Mentions half-cycle/fractional AND 40MHz

### SPI-002: SPI DMA Opcodes
**Prompt**: "What are the ICR Read opcodes for Single, Dual, and Quad SPI IO modes?"
**Expected**: Single=0x0B, Dual=0xBB, Quad=0xEB (or 0xFB alt)
**Pass Criteria**: All 3 opcodes correct

### SPI-003: SPI Timing
**Prompt**: "What are the minimum CS# setup and hold times for THC SPI?"
**Expected**: CS# Setup 30ns min, CS# Hold 30ns min
**Pass Criteria**: Both 30ns values

### SPI-004: Loopback Clocks
**Prompt**: "What is the purpose of SPI loopback clocks in THC? Why are they needed?"
**Expected**: Compensate on-chip routing delay between THC IP and SPI pads. Uses dummy pad per port.
**Pass Criteria**: Mentions routing delay compensation AND dummy pad

## HIDI2C Sub-Skill Tests

### I2C-001: PORT_TYPE Register
**Prompt**: "What register and values configure THC for I2C mode vs SPI mode?"
**Expected**: THC_M_PRT_CONTROL.PORT_TYPE: 00=SPI, 01=I2C
**Pass Criteria**: Correct register name AND both values

### I2C-002: SPI_RD_MPS RTL Bug
**Prompt**: "What is the critical RTL bug when THC operates in I2C mode related to MPS? What is the workaround?"
**Expected**: THC incorrectly uses SPI_RD_MPS in I2C mode. Workaround: program SPI_RD_MPS to 4096 (4KB)
**Pass Criteria**: Identifies SPI_RD_MPS AND 4KB workaround

### I2C-003: Synopsys Sub-IP Speed
**Prompt**: "What is the IC_MAX_SPEED_MODE value for the Synopsys DW_apb_i2c sub-IP in THC?"
**Expected**: 0x2 = Fast Mode Plus (1MHz max)
**Pass Criteria**: 0x2 AND Fast Mode Plus

### I2C-004: Legacy Panel Support
**Prompt**: "Which platforms added legacy panel support for Elan panels?"
**Expected**: PTL/WCL/NVL+ platforms
**Pass Criteria**: Mentions at least PTL and NVL

## DMA Sub-Skill Tests

### DMA-001: Store-and-Forward vs Streaming
**Prompt**: "What is the POR DMA mode for THC? What is the performance difference with streaming?"
**Expected**: Store-and-Forward is POR. Streaming is ~6.5% better but NOT POR
**Pass Criteria**: Store-and-Forward POR AND 6.5% figure

### DMA-002: E2E Touch Flow
**Prompt**: "Describe the end-to-end flow from device interrupt to host notification in SPI mode."
**Expected**: Device INT → ICR Read → Qualify INT_CAUSE → Bulk Data Read → PRD Walk → MSI → EOF → GuC Doorbell
**Pass Criteria**: At least 6 of the 8 steps in correct order

### DMA-003: PRD Alignment Bug
**Prompt**: "What is RTL bug 15014172472 about? How does it affect PRD buffer allocation?"
**Expected**: Last PRD entry also requires 4KB alignment (spec says only non-last need 4KB). All buffers must be 4KB aligned.
**Pass Criteria**: Mentions last entry AND 4KB alignment requirement

### DMA-004: Frame Type Routing
**Prompt**: "How does THC route frames to RXDMA channels based on Frame Type? What's different for HIDSPI?"
**Expected**: Frame Type 0→RXDMA1, Type 1→RXDMA2. HIDSPI ignores Frame Type (all to RXDMA2) when FTYPE_IGNORE=1 AND FTYPE_VAL=1
**Pass Criteria**: Correct routing AND HIDSPI exception

### DMA-005: STALL_STS Error
**Prompt**: "What happens when all PRD table entries are consumed before a frame completes?"
**Expected**: STALL_STS bit set, DMA engine stalls, no data loss but no progress. SW must provide more entries or abort.
**Pass Criteria**: Mentions STALL_STS AND stall behavior

## Platform Sub-Skill Tests

### PLAT-001: Gate Count
**Prompt**: "What is the gate count per THC instance from the HAS?"
**Expected**: 300K gates per instance (with two ports)
**Pass Criteria**: 300K

### PLAT-002: PTL SB Port ID
**Prompt**: "What changed about IOSF SB port ID starting with PTL? What HSDES tracks this?"
**Expected**: PTL+ requires 16-bit SB port ID (was 8-bit). HSDES 15010734105
**Pass Criteria**: 16-bit AND HSDES number

### PLAT-003: SAI Policy
**Prompt**: "What INDEX controls SAI checking for THC register access? Name at least 5 allowed SAIs."
**Expected**: INDEX41. Allowed: ESE_SAI, HOSTIA_POSTBOOT_SAI, HOSTIA_BOOT_SAI, HOSTIA_SMM_SAI, DFX_INTEL_MANUFACTURING_SAI, etc.
**Pass Criteria**: INDEX41 AND at least 5 SAIs listed

## Driver Sub-Skill Tests

### DRV-001: BIOS Lock Sequence
**Prompt**: "What is the THC lock bit sequence between BIOS and OS driver?"
**Expected**: BIOS sets BIOS_LOCK_EN → OS driver loads → Driver sets DRV_LOCK_EN → Both sticky until reset
**Pass Criteria**: Correct order AND sticky behavior

### DRV-002: NVL PI Configuration
**Prompt**: "How is the PCI Programming Interface configured on NVL+ platforms?"
**Expected**: Via thc_pi_def[7:0] soft strap. Allows per-port or shared PCI header modes.
**Pass Criteria**: thc_pi_def AND both modes mentioned

### DRV-003: Security Threat Points
**Prompt**: "What are the 3 threat points in THC's security model?"
**Expected**: Sensor PIO, VTd (DMA without IOMMU), GPIO (interrupt injection)
**Pass Criteria**: All 3 threat points named

## Debug Sub-Skill Tests

### DBG-001: Validation Frame Sizes
**Prompt**: "What are the min and max frame sizes for THC validation per the HAS?"
**Expected**: Min 64B, Max 1MB for validation (EDS allows up to 16MB)
**Pass Criteria**: 64B min AND 1MB validation max AND 16MB EDS max

### DBG-002: Coverage Goals
**Prompt**: "What are THC's stuck-at and at-speed coverage goals?"
**Expected**: 99% stuck-at, 95% at-speed
**Pass Criteria**: Both percentages correct

### DBG-003: VISA Debug Config
**Prompt**: "How many VISA lanes does THC have and what is the tree depth?"
**Expected**: 2 lanes x 8 bits, 100-130MHz clock, 5-level tree
**Pass Criteria**: 2 lanes AND 5-level tree

### DBG-004: Device Emulation
**Prompt**: "What register enables TSI device emulation mode in THC? How many steps in the emulation flow?"
**Expected**: DFX_Mode_En register, 9-step flow
**Pass Criteria**: DFX_Mode_En AND 9 steps

### DBG-005: Performance Counters
**Prompt**: "Name at least 5 THC hardware performance counters."
**Expected**: RXDMA Doorbells, TX/RX DMA Frames, TX/RX uFrames, Dropped Frames, TX/RX Touch Packets, Device Interrupts, SW Interrupts
**Pass Criteria**: At least 5 counter names

## BWG (BIOS Writer Guide) Integration Tests

> These tests validate the BWG-derived content added to platform, power, and registers sub-skills.
> Source: Chap69_BIOS_WG_THC.docx (Rev 0.5, TGP-era, last modified 2024-09-24)
>
> **Results ID mapping**: BWG-001→PLAT-004, BWG-002→PLAT-005, BWG-003→PWR-006, BWG-004→PWR-007, BWG-005→REG-006, BWG-006→REG-007 (see eval results file for details)

### BWG-001: BIOS Port Configuration Scenarios
**Prompt**: "What are the 4 BIOS port configuration scenarios for THC? What register and bit does BIOS clear to disable a port?"
**Expected**: 4 scenarios: (1) Two THC ports dual-driver, (2) Two THC ports single-driver with THC1 Function Disabled, (3) One THC port with THC1 FD, (4) Both THCs disabled via FD. BIOS clears PORT_SUPPORTED bit to disable a port.
**Pass Criteria**: All 4 scenarios described AND PORT_SUPPORTED mentioned

### BWG-002: MSFT G5 Panel Configuration
**Prompt**: "What special MMIO configuration is required for MSFT G5 touch panels? What is the register offset and bit?"
**Expected**: MMIO offset 0x1128, bit 31 must be set to 1 for MSFT G5 panel support.
**Pass Criteria**: Offset 0x1128 AND bit 31

### BWG-003: BIOS S3/S4/S5 Entry Sequence
**Prompt**: "What is the correct sequence for THC when entering S3, S4, or S5 sleep states? What must happen before D3 entry?"
**Expected**: 3-step sequence: (1) SW asserts DEVRST bit, (2) Complete D3 entry, (3) Initiate Sx entry. DEVRST must be asserted BEFORE D3 entry.
**Pass Criteria**: Correct 3-step order AND DEVRST before D3

### BWG-004: Wake Event Constraints
**Prompt**: "In which THC power states is touch device wake supported? What about D3?"
**Expected**: Touch device wake is ONLY supported in D0i2 (HW-autonomous power gate). In D3, only SW-initiated wake is supported — no touch wake.
**Pass Criteria**: D0i2 touch wake AND D3 SW-only wake

### BWG-005: SAI Policy Register Map
**Prompt**: "What are the 8 SAI policy registers in THC IOSF SB space? What port and offset range?"
**Expected**: Port P39h, offsets 0x20–0x3C. Registers: THC_SB_SAI_CNTRL_PLCY0/1, THC_SB_SAI_CMN_PLCY0/1, THC_SB_SAI_PORT0_PLCY0/1, THC_SB_SAI_PORT1_PLCY0/1. All default to 0x00000000.
**Pass Criteria**: Port P39h AND at least 4 register names AND 0x20–0x3C range

### BWG-006: CDC Clock Gating Transition
**Prompt**: "What happens to the CDC config registers during THC function disable? What value transition occurs?"
**Expected**: THC_SB_PR_CDC_CFG and THC_SB_SD_CDC_CFG transition from 0x0000CCC0 to 0x0000CCC3 (CCC0→CCC3). THC_SB_SSC_CDC_CFG and THC_SB_ROSC_CLK_CFG remain unchanged at 0x00000001.
**Pass Criteria**: CCC0→CCC3 transition AND correct registers identified

## Driver Source Code Audit Tests (2026-03-05)

> These test prompts validate content added during the exhaustive cross-check audit of Linux kernel,
> Windows HIDSPI, and Windows HIDI2C driver source code against THC sub-skill documentation.
> Source: Linux v6.17-6.20 THC driver, Windows HIDSPI v4.0.0.9000, Windows HIDI2C v3.0.0.9000

### SPI-005: SPI Base Clock Frequency
**Prompt**: "What is the SPI base clock frequency used for THC SPI divider calculations? Is it 128 MHz or 125 MHz?"
**Expected**: 125 MHz base clock, NOT 128 MHz. Formula is base_freq / divider (not base_freq / (divider × 2))
**Pass Criteria**: States 125 MHz AND rejects 128 MHz

### SPI-006: SPI PIO Opcodes
**Prompt**: "What are the THC SPI PIO opcodes for read, write, and bulk write operations?"
**Expected**: Read=0x4, Write=0x6, Bulk Write=0x8. Write and bulk_write are different opcodes.
**Pass Criteria**: All 3 opcodes correct AND distinguishes write from bulk_write

### SPI-007: QuickSPI Probe Sequence
**Prompt**: "How many steps are in the QuickSPI Linux probe sequence? Does DMA initialization happen before or after device reset?"
**Expected**: 14 steps. DMA initialization happens AFTER device reset (not before).
**Pass Criteria**: States DMA after reset

### SPI-008: QuickSPI State Enum Names
**Prompt**: "What are the THC QuickSPI device state enum values in the Linux kernel driver?"
**Expected**: 6 states in enum order: QUICKSPI_NONE(0), QUICKSPI_INITIATED(1), QUICKSPI_RESETING(2), QUICKSPI_RESET(3), QUICKSPI_ENABLED(4), QUICKSPI_DISABLED(5). Note: INITIATED (not INITED), RESETING/RESET (not RESETED), and no SUSPENDED state in QuickSPI (SUSPENDED exists only in QuickI2C).
**Pass Criteria**: Uses INITIATED and RESET (not INITED/RESETED) AND notes no SUSPENDED in QuickSPI

### I2C-005: IC_CON Default Value
**Prompt**: "What is the IC_CON register default value programmed by the Linux QuickI2C driver? How does Windows differ?"
**Expected**: Linux writes 0x663 directly. Windows builds IC_CON field-by-field. Both produce equivalent Fast Mode Plus configuration.
**Pass Criteria**: Linux 0x663 AND mentions Windows field-by-field approach

### I2C-006: Default I2C Target Address
**Prompt**: "What is the default I2C target address used by the THC I2C driver when ACPI doesn't specify one? How does this differ from the Synopsys IC_TAR hardware default?"
**Expected**: Driver default target address is 0x0A (programmed into IC_TAR by Linux/Windows drivers as fallback). The Synopsys I2C sub-IP hardware default for IC_TAR is 0x086 (before driver initialization). These are different contexts — 0x0A is the *driver-level* default, 0x086 is the *hardware reset* default.
**Pass Criteria**: States 0x0A as driver default AND acknowledges 0x086 as hardware/Synopsys default (different contexts)

### I2C-007: Host Reset and SET_POWER Transport
**Prompt**: "How does the THC I2C driver send Host Reset and SET_POWER commands — via PIO or DMA?"
**Expected**: Via TXDMA using write_cmd_to_txdma(), NOT via PIO opcode 0x18
**Pass Criteria**: States TXDMA (not PIO)

### I2C-008: RXDMA1 Usage in I2C Mode
**Prompt**: "Is RXDMA1 used for I2C input reports? If not, which DMA channel handles I2C input?"
**Expected**: RXDMA1 is NOT used for I2C (configured with size=0). RXDMA2 is the primary input path for I2C.
**Pass Criteria**: States RXDMA1 size=0 AND RXDMA2 is primary

### I2C-009: Report ID Threshold
**Prompt**: "What is the report ID threshold for determining report ID size in the THC I2C driver? Is it <= 15 or < 15?"
**Expected**: Report ID < 15 (strictly less than), not <= 15
**Pass Criteria**: States < 15 (not <=)

### DMA-006: DMA Pause Timeout Cross-Platform
**Prompt**: "What are the DMA pause (quiesce) timeout values for Linux vs Windows THC drivers?"
**Expected**: Linux: 100µs interval, 10ms total timeout. Windows: 10µs interval, 1s (1,000,000µs) total timeout.
**Pass Criteria**: Correct values for BOTH platforms AND notes the 100x timeout difference

### DMA-007: DMA Pause Polling Register
**Prompt**: "What register does the THC driver poll when waiting for DMA to quiesce/pause?"
**Expected**: Polls READ_DMA_INT_STS register (INT_STS), NOT DMA_CNTRL register
**Pass Criteria**: States INT_STS (not DMA_CNTRL)

### DMA-008: SWDMA Save/Restore Cross-Platform
**Prompt**: "How do Linux and Windows THC drivers differ in SWDMA save/restore during power transitions?"
**Expected**: Linux selectively saves/restores only rx_max_size and int_delay for SWDMA. Windows does full DMA unconfigure/reconfigure cycle.
**Pass Criteria**: Mentions selective (Linux) vs full cycle (Windows)

### PWR-008: LTR Unconfig Procedure
**Prompt**: "How does the THC driver unconfigure LTR? Is there a toggle pattern (0→1→0) on THC_LTR_EN?"
**Expected**: NO toggle pattern. LTR unconfig simply clears 4 bits: LP_LTR_EN, ACTIVE_LTR_EN, LP_LTR_REQ, ACTIVE_LTR_REQ. There is no field named THC_LTR_EN.
**Pass Criteria**: States NO toggle AND names the 4 actual bit fields

### PWR-009: SET_POWER Cross-Platform Behavior
**Prompt**: "How does SET_POWER ON behavior differ between Linux and Windows THC drivers?"
**Expected**: Linux: fire-and-forget (sends command, doesn't wait for completion). Windows: synchronous flag-gated (waits for completion with flag check).
**Pass Criteria**: States fire-and-forget (Linux) AND synchronous (Windows)

### DRV-004: Output Report PM Handling Gap
**Prompt**: "Does the THC driver perform PM runtime get/put around output report operations? Is this a potential bug?"
**Expected**: NO — output_report() has NO PM runtime handling (no pm_runtime_get/put). This is a potential bug — device could be in D3 when output report is attempted.
**Pass Criteria**: Identifies missing PM handling AND notes potential bug

### DRV-005: QuickSPI Reset Flow
**Prompt**: "How does the Linux QuickSPI driver perform device reset? Does it use GPIO LOW/HIGH with level-triggered interrupt?"
**Expected**: Uses ACPI _RST method (not GPIO LOW/HIGH). Uses edge-triggered interrupt detection (not level-triggered).
**Pass Criteria**: States ACPI _RST AND edge-triggered

### DBG-006: Windows Driver Version Numbers
**Prompt**: "What are the current version numbers for the Windows HIDSPI and HIDI2C THC drivers?"
**Expected**: HIDSPI: v4.0.0.9000, HIDI2C: v3.0.0.9000 (from Ver.h)
**Pass Criteria**: Both version numbers correct

### DBG-007: WPP Tracing GUIDs
**Prompt**: "Are the WPP tracing GUIDs the same for Windows HIDSPI and HIDI2C drivers?"
**Expected**: NO — they are different. HIDSPI: {A891081A...}, HIDI2C: {C47236A7...}
**Pass Criteria**: States different GUIDs AND provides at least one GUID prefix

---

## Wake-on-Touch (WoT) Tests

### WOT-001: WoT Power Domain Architecture
**Prompt**: "Which THC power domains exist and what role does each play in WoT?"
**Expected**: THC_UGD (Un-Gated Domain) stays always-on for runtime interrupt routing during D0i2 (THC still powered but clock-gated). THC_PGD (Power-Gateable Domain) is gated during D0i2/D3. Isolation is required in PGD→UGD direction only. CRITICAL: UGD does NOT route wake signals to PMC for platform wake from Sx/D3 — platform wake comes through GPIO IP (vGPIO), which is external to THC IP. THC PCI caps: WAKE=No, PME=No.
**Pass Criteria**: Identifies UGD as runtime D0i2 interrupt routing AND PGD as gated AND clarifies UGD is NOT for platform wake

### WOT-002: WoT GPIO Wake Path (Architecture)
**Prompt**: "How does Wake-on-Touch actually work? What is the wake interrupt path from touch device to platform wake?"
**Expected**: The wake path BYPASSES THC entirely: Touch Device → GPIO pad → vGPIO (GPIO IP) → PMC → Platform Wake. THC IP has WAKE=No and PME=No in PCI capabilities — it cannot generate platform wake signals. THC's role is driver-side only: (1) register GPIO as wake source via ACPI during probe, (2) decide sleep behavior during suspend (skip SET_POWER SLEEP if WoT armed), (3) re-init hardware after resume.
**Pass Criteria**: States wake bypasses THC AND mentions GPIO IP/vGPIO AND states THC WAKE=No/PME=No

### WOT-003: WoT Entry Flow
**Prompt**: "What steps does the THC driver perform when entering Wake-on-Touch mode?"
**Expected**: Linux WoT entry (intel-thc-wot.c): (1) acpi_dev_gpio_irq_wake_get_by() finds ACPI wake GPIO, (2) dev_pm_set_dedicated_wake_irq() registers with PM subsystem, (3) During suspend: skip SET_POWER SLEEP so device stays responsive, (4) device_set_wakeup_enable() arms wake. Windows WoT entry: (1) Install WoT Extension INF (WoT_QuickSpiExtension.inf or WoT_QuickI2cExtension.inf), (2) Set TSEQ_CNTRL_1.EWOG bit, (3) ARM_FOR_WAKE TIC state (value=5). BIOS: Enable "Wake on Touch" in THC Configuration menu.
**Pass Criteria**: Includes ACPI GPIO registration AND skip SET_POWER SLEEP AND mentions Extension INF for Windows

### WOT-004: WoT Platform Differences
**Prompt**: "Are there platform-specific differences in WoT support across LNL, PTL, and NVL?"
**Expected**: LNL (Gen4.0): First platform with HIDI2C WoT. PTL (Gen4.1): D3 flow overhauled (4 levels: D3Hot-Host, D3Hot-Device, D3Cold-Host, D3Cold-Device). NVL (Gen4.2): THC1 BDF changed (Bus=0 Dev=8 Fun=0), unified HAS. WoT GPIO pin assignments vary per platform. BWG constraint: For touch wake during connected standby, THC must remain in D0i2 (not D3) — D3 has only SW wake per BWG.
**Pass Criteria**: Mentions at least 2 platform differences AND BWG D0i2 constraint for touch wake

### WOT-005: WoG (Wake-on-Gesture) POR Status
**Prompt**: "Does THC support Wake-on-Gesture? What is the WoG architecture?"
**Expected**: WoG is NOT POR per HAS ("many open issues remain"). WoG architecture uses ISH (Integrated Sensor Hub) for gesture matching — CPU must stay in C10 with no DRAM access during WoG processing. THC has EWOG (bit 5) and RWOGC (bit 6) register bits in TSEQ_CNTRL_1, but they are NOT POR. Softstraps THC_TSI_WAKE_ON_GEST_EN and THC_SPI_WAKE_ON_GEST_EN exist (default=0). Linux driver does NOT use EWOG. Windows HIDSPI driver sets EWOG during armForWake (Windows-specific behavior).
**Pass Criteria**: States WoG is NOT POR AND mentions ISH for gesture matching AND identifies EWOG/RWOGC as unused by Linux

### WOT-006: D0i2 vs Platform Wake Distinction
**Prompt**: "What is the difference between D0i2 wake and platform wake (WoT) for THC?"
**Expected**: D0i2 wake is a RUNTIME interrupt — THC is still powered (PGD clock-gated but not power-gated on some platforms), UGD routes touch interrupt through THC's own interrupt path to wake from sub-D0 state. Platform wake (WoT from Sx/D3) is fundamentally different — THC is fully power-gated, wake signal goes through GPIO IP (vGPIO) → PMC, completely bypassing THC. BWG confirms: D0i2 supports touch device wake, D3 supports only SW wake (no touch device wake from D3 per BWG).
**Pass Criteria**: Distinguishes D0i2 runtime wake from platform wake AND states D3 has no touch wake per BWG

### WOT-007: Linux WoT Implementation Details
**Prompt**: "How is WoT implemented in the Linux kernel THC driver? What registers does it write?"
**Expected**: Linux WoT (intel-thc-wot.c) writes ZERO THC registers. It uses only ACPI/GPIO/PM kernel subsystems: acpi_dev_gpio_irq_wake_get_by() to find wake GPIO, dev_pm_set_dedicated_wake_irq() to register with PM core. The wake GPIO is managed by GPIO IP, not THC. thc_wot_config() returns early if no ACPI wake GPIO found. Added in kernel 6.17.
**Pass Criteria**: States zero THC register writes AND names acpi_dev_gpio_irq_wake_get_by AND states GPIO IP manages wake

### WOT-008: WoT Known Issues
**Prompt**: "What are the known issues and sightings related to THC WoT?"
**Expected**: (1) HSD 16027810168: WCL post code stuck at 0x9B0E when enabling WoT in BIOS. (2) REVIEW-002: WoG has many open items, not POR. (3) SPI WoT gap: Linux SPI suspend always sends SET_POWER SLEEP (no WoT handling) — WoT from SPI sleep may not work. (4) Two-stage WoT and ULP WoT referenced in HAS but NO implementation exists in kernel v6.17-6.20. (5) WoT requires Extension INF on Windows (not installed by default).
**Pass Criteria**: Mentions HSD 16027810168 AND SPI WoT gap AND WoG not POR

### WOT-009: vGPIO Pad Locking (PADCFGLOCK)
**Prompt**: "What BIOS configuration is required for the vGPIO THC pad to enable Wake-on-Touch? What happens if the pad is locked?"
**Expected**: PADCFGLOCK_VGPIO_THC0 must be 0x0 (unlocked) for OS driver to control the vGPIO_THC pad for WoT. If locked (0x1), the OS cannot configure the pad as a wake source. BIOS "Force unlock on all GPIO pads" = Disable can lock the vGPIO_THC pad on some platforms. NVL was affected (HSD 15018635096), PTL was NOT affected (PADCFGLOCK stays 0x0). Fix: BIOS must explicitly leave vGPIO_THC pads unlocked.
**Pass Criteria**: Mentions PADCFGLOCK AND 0x0 (unlocked) AND HSD 15018635096

### WOT-010: HSDES WoT Sighting Knowledge
**Prompt**: "What are the key HSDES sightings for THC WoT? Describe HSD 15018635096 and HSD 16029769688."
**Expected**: HSD 15018635096: NVL-Hx A1 THC WoT via vGPIO failed due to PADCFGLOCK_VGPIO_THC0 being locked by BIOS "Force unlock=Disable" setting. Root cause = BIOS, fixed in NovaLake_2460_22. HSD 16029769688: WCL wake from touchpad not working after ~10-15 cycles, IO APIC mode affected (GPIO mode works). Two signatures: (1) RTE84 mask bit stays set after ITSS→CORE interrupt, (2) did+edid=0, interrupt not routed to core. Status: OPEN, promoted to Microsoft MTC 22022108803. Mitigation: ForceIdleTimeout regkey = 0x3.
**Pass Criteria**: Mentions both HSD numbers AND PADCFGLOCK for 15018635096 AND IO APIC for 16029769688

### WOT-011: WCL IO APIC Wake Failure
**Prompt**: "Describe the WCL touchpad wake failure (HSD 16029769688). What are the two failure signatures?"
**Expected**: Signature 1 (6/10 occurrences): RTE84 mask bit stays set after first ITSS→CORE interrupt — OS doesn't unmask after EOI. Signature 2 (4/10): Mask not set but did+edid=0, interrupt not routed to any core (correlated with LNL ISH issue HSD 15015234406). GPIO mode works, only IO APIC mode affected. FTH trace shows gpp_F_18 (touchpad) interrupt processed by ITSS, EOI received, but OS fails to unmask RTE84. Mitigation: ForceIdleTimeout regkey = 0x3 (default 0x7).
**Pass Criteria**: Describes both signatures AND mentions IO APIC vs GPIO mode AND ForceIdleTimeout mitigation

### WOT-012: pinctrl-intel Wake Architecture
**Prompt**: "How does the Intel GPIO controller (pinctrl-intel) handle wake IRQs? What is IRQCHIP_MASK_ON_SUSPEND?"
**Expected**: pinctrl-intel.c implements intel_gpio_irq_wake() which calls enable_irq_wake()/disable_irq_wake() on the parent IRQ. IRQCHIP_MASK_ON_SUSPEND flag means GPIO IRQs are masked during suspend. intel_pinctrl_suspend_noirq/resume_noirq save/restore ALL pad configs (padcfg0/1/2, HOSTSW_OWN, GPI_IE, GPI_GPE_EN). ACPI mode pins are "usable as GPIO but cannot be used as IRQ because GPI_IS status bit will not be updated." IO APIC mode and GPIO mode are two different wake delivery paths.
**Pass Criteria**: Mentions pinctrl-intel AND IRQCHIP_MASK_ON_SUSPEND AND pad config save/restore

### WOT-013: QuickI2C WoT Implementation
**Prompt**: "How does the Linux QuickI2C driver implement WoT? What are the differences from QuickSPI? What are the PM callback behaviors?"
**Expected**: QuickI2C WoT uses IDENTICAL pattern to QuickSPI: wake_gpio={0,0,true}, quicki2c_gpios[]={{"wake-on-touch",&wake_gpio,1},{}}. thc_wot_config() called in quicki2c_dev_init(). WoT-aware suspend: if(!device_may_wakeup()) → set_power(SLEEP), skips SLEEP when WoT enabled. I2C-specific: thc_i2c_subip_regs_save() BEFORE dma_unconfigure on suspend, thc_i2c_subip_regs_restore() AFTER port_select on resume. freeze/thaw: NO WoT handling. poweroff: ALWAYS sends SLEEP regardless of WoT. restore (hibernate): full re-init including i2c_subip_init. I2C Device IDs: LNL 0xA848/0xA84A, PTL-H 0xE348/0xE34A, PTL-U 0xE448/0xE44A, WCL 0x4D48/0x4D4A. NO NVL/ARL/RZL/TTL I2C Device IDs.
**Pass Criteria**: Mentions QuickI2C WoT identical to QuickSPI AND i2c_subip_regs_save/restore AND freeze/thaw NO WoT AND at least 2 I2C Device IDs

---

## Cross-Skill Deep-Dive Tests (2026-03-06)

> These tests validate advanced and cross-cutting THC domain knowledge requiring synthesis across
> multiple sub-skills (DMA, registers, power, HIDSPI, HIDI2C, debug, driver, platform).

### WOT-014: S4 Hibernate 2nd Cycle Bug
**Prompt**: "What is HSD 15019129309 about? How does the S4 hibernate WoT bug manifest and what is the root cause?"
**Expected**: HSD 15019129309: WoT fails on 2nd S4 hibernate cycle (works on 1st cycle). Root cause: poweroff callback ALWAYS sends SET_POWER SLEEP regardless of WoT arming — device enters sleep and cannot wake host on 2nd cycle. restore callback does full re-init but the initial poweroff already killed WoT. Linux-specific: poweroff path has no WoT-awareness (unlike suspend path which skips SLEEP when WoT armed).
**Pass Criteria**: Mentions HSD 15019129309 AND 2nd cycle failure AND poweroff always sends SLEEP

### WOT-015: PMCLite Sideband Messages
**Prompt**: "What are the PMCLite sideband message codes used by THC for power state transitions? List the D0, D3, save/restore, and power gate codes."
**Expected**: PMCLite codes: D0=0x8086D000, D3 Entry=0x8086D301, D3Hot=0x8086D302, D3Cold=0x8086D303, Save=0x80860200, Restore=0x80860201, PG Entry=0x80860301, PG Exit=0x80860302, D0i2 Entry=0x8086D201, D0i2 Exit=0x8086D200. UHFI→PMCLite codes: D3 Entry=0x8086D310, D3Hot=0x8086D311, D3Cold=0x8086D312.
**Pass Criteria**: At least 6 correct PMCLite codes AND includes both D0i2 Entry/Exit codes

### WOT-016: WoT Negative Test
**Prompt**: "In which THC power states does touch-device wake NOT work? Can touch wake the system from S0ix? From D3? From D0i2?"
**Expected**: D0i2: Touch device wake IS supported (HW-autonomous power gate, UGD routes interrupt). D3: Only SW-initiated wake, NO touch device wake per BWG. S0ix/Sx platform wake: Goes through GPIO IP (vGPIO→PMC), bypasses THC entirely — THC itself cannot generate platform wake (WAKE=No, PME=No in PCI caps). So "THC touch wake from S0ix" is really "GPIO wake from S0ix" — THC is not involved in the wake signal path.
**Pass Criteria**: States D3 has no touch wake AND S0ix wake bypasses THC AND D0i2 touch wake supported

### DMA-009: SWDMA 14-Step Workflow
**Prompt**: "What are the 14 steps of the THC SWDMA (Software DMA) workflow? Which steps pause and restart RXDMA?"
**Expected**: 14-step SWDMA workflow: (1) Disable SWDMA interrupt, (2) Clear pending SWDMA interrupt, (3) Reset SWDMA read pointer, (4) Pause RXDMA1, (5) Pause RXDMA2, (6) Disable write interrupt for RXDMA1, (7) Disable write interrupt for RXDMA2, (8) Clear pending write interrupt RXDMA1, (9) Clear pending write interrupt RXDMA2, (10) Start SWDMA, (11) Wait for SWDMA completion, (12) Enable RXDMA1 write interrupt, (13) Enable RXDMA2 write interrupt, (14) Restart RXDMA2 (NOT RXDMA1). Steps 4-5 pause both RXDMA channels. Step 14 restarts only RXDMA2.
**Pass Criteria**: Lists at least 10 of 14 steps AND notes step 14 restarts only RXDMA2 (not RXDMA1)

### DMA-010: PRD Ring Pointer Management
**Prompt**: "How does THC manage PRD ring buffer pointers? What are TPCWP and TPCRP, and what is the POINTER_WRAPAROUND bit?"
**Expected**: TPCWP (THC PRD Callback Write Pointer) is the SW write pointer — SW advances it to give new PRD entries to HW. TPCRP (THC PRD Callback Read Pointer) is the HW read pointer — HW advances it as it consumes PRD entries. POINTER_WRAPAROUND is bit 7, set by HW when read pointer wraps around the ring. SW uses wraparound detection to know when to replenish PRD entries. Ring is circular with configurable depth.
**Pass Criteria**: Defines both TPCWP and TPCRP AND mentions POINTER_WRAPAROUND bit 7

### REG-008: Interrupt Handler Priority
**Prompt**: "What is the priority order in the THC interrupt handler? How many priority levels are there and what is special about PIO_DONE?"
**Expected**: 11-level interrupt handler priority: (1) Fatal error, (2) NONDMA error, (3) TXN error, (4) DMA error, (5) PIO_DONE, (6) RXDMA2 complete, (7) TXDMA complete, (8) RXDMA1 complete, (9) SWDMA complete, (10) Device interrupt, (11) Microsecond timestamp. PIO_DONE (priority 5) is special: it falls through to DMA processing (does NOT return early). Error checks (priorities 2-4) short-circuit (return immediately). DMA sources (6-9) are accumulated into a bitmask and processed together.
**Pass Criteria**: Lists at least 8 of 11 priority levels AND notes PIO_DONE falls through (does not return)

### REG-009: Counter Register Bug
**Prompt**: "Is there a bug in the THC interrupt handler related to SWINT_CNT registers? What is the copy-paste error?"
**Expected**: Yes — copy-paste bug in interrupt handler: SWINT_CNT_1 is reset twice (once in its own block, once in SWINT_CNT_2's block), while SWINT_CNT_2 is NEVER reset. The SWINT_CNT_2 reset code incorrectly references SWINT_CNT_1 instead of SWINT_CNT_2. This means SWINT_CNT_2 accumulates indefinitely and never clears.
**Pass Criteria**: Identifies SWINT_CNT_1 reset twice AND SWINT_CNT_2 never reset

### SPI-009: HIDSPI Frame Type Routing Details
**Prompt**: "What happens to HIDSPI frame type routing when both FTYPE_IGNORE=1 and FTYPE_VAL=1? Why does this differ from HIDI2C?"
**Expected**: When FTYPE_IGNORE=1 AND FTYPE_VAL=1: all frames route to RXDMA2 regardless of actual frame type. FTYPE_VAL=1 forces the effective frame type to 1, and type 1→RXDMA2. This is the HIDSPI POR configuration because HIDSPI protocol has no frame type field in its header. HIDI2C uses frame type routing normally: type 0→RXDMA1, type 1→RXDMA2, based on the actual frame type field in the I2C input report.
**Pass Criteria**: States FTYPE_IGNORE=1+FTYPE_VAL=1 routes all to RXDMA2 AND explains HIDSPI has no frame type field

### SPI-010: HIDSPI Sync Constant
**Prompt**: "What is the HIDSPI sync constant value? Where is it located in the input report header and what happens if it's invalid?"
**Expected**: Sync constant is 0x5A, located at bits 31:24 of the HIDSPI input report header. If the sync constant is invalid (not 0x5A), the host initiates a device reset. The sync constant validates that the SPI read data is properly framed and not corrupted.
**Pass Criteria**: States 0x5A AND bits 31:24 AND device reset on invalid sync

### I2C-010: SmartFilter Report IDs
**Prompt**: "What are the SmartFilter report ID values for control and data reports? What is the maximum number of reports per VSync?"
**Expected**: CONTROL_REPORT_ID=0xFE, DATA_REPORT_ID=0xFD. Maximum 16 reports per VSync (inputReportIDs[16] array). SmartFilter is an IPTS-specific mechanism for filtering touch reports synchronized to display refresh.
**Pass Criteria**: States 0xFE for control AND 0xFD for data AND 16 max reports

### DRV-006: IPTS Filter Driver GUID
**Prompt**: "What is the IPTS filter driver GUID? How many sensor stubs does it define?"
**Expected**: IPTS filter driver GUID: {A2BCAC85-68F6-41B2-B112-DE4EA74770C6}. Defines 9 sensor stubs. The IPTS filter operates between the HID transport driver and the HID class driver, intercepting touch reports for Intel Precise Touch & Stylus processing.
**Pass Criteria**: Correct GUID {A2BCAC85-68F6-41B2-B112-DE4EA74770C6} AND 9 sensor stubs

### PLAT-006: NVL THC1 BDF Change
**Prompt**: "What changed about THC1's PCI Bus:Device:Function on NVL compared to previous platforms? What was it before?"
**Expected**: NVL THC1 BDF changed to Bus:0 Device:8 Function:0. Previously THC1 was at Device:16 Function:1 (shared function with THC0 at Device:16 Function:0). This change means THC1 is now a separate PCI device rather than a function of the same device as THC0.
**Pass Criteria**: States NVL THC1 at B:0 D:8 F:0 AND mentions previous D:16 F:1

### PLAT-007: Desktop THC Availability
**Prompt**: "Is THC available on desktop platforms? What about NVL-S (desktop variant of NovaLake)?"
**Expected**: NVL-S (desktop) has THC fuse-disabled / ZBB'ed (zero-base-die blocked). THC is primarily a mobile/laptop IP for touch panel support. Desktop platforms generally do not include THC as touchscreens/touchpads are not standard desktop peripherals.
**Pass Criteria**: States NVL-S has THC fuse-disabled or ZBB'ed

### PLAT-008: NVL THC1 BDF Change
**Prompt**: "What changed about THC1's PCI BDF on NVL compared to all prior platforms?"
**Expected**: On NVL, THC1 moved to Bus=0 Dev=8 Fun=0. On all prior platforms (MTL, LNL, PTL, WCL), THC1 was at Dev=16 Fun=1. This is a breaking change that affects PCI enumeration code — any hardcoded BDF for THC1 must be updated for NVL.
**Pass Criteria**: States NVL THC1 is Dev=8 Fun=0 AND prior platforms used Dev=16 Fun=1

### PLAT-009: Gen4.1 D3 Flow Overhaul
**Prompt**: "What changed in the D3 power flow from Gen4.0 (LNL) to Gen4.1 (PTL)?"
**Expected**: Gen4.1 overhauled D3 into 4 levels: D3-hot (PME capable), D3-cold (no power), D3-with-WoT (UGD stays on), and D3-without-WoT. This replaced the simpler Gen4.0 D3 model. The 4-level scheme affects save/restore scope, wake path configuration, and PMCLite sideband messaging.
**Pass Criteria**: Mentions 4 D3 levels AND names at least D3-hot and D3-cold

### PLAT-010: Half-Divider Clock (Gen4.1+)
**Prompt**: "What is the half-divider clock feature introduced in Gen4.1 and how does it affect SPI timing?"
**Expected**: Gen4.1 (PTL+) introduced a half-divider option for SPI clock generation. The base clock is 125 MHz. With integer dividers only (Gen4.0), minimum SPI clock was ~8 MHz (125/16). Half-dividers allow finer granularity. The divider value in THC_M_PRT_SPI_CFG controls the clock frequency as: SPI_CLK = 125 MHz / divider.
**Pass Criteria**: Mentions 125 MHz base clock AND half-divider enabling finer SPI clock granularity

### PLAT-011: THC1 Requires THC0 Enabled
**Prompt**: "What is the dependency between THC0 and THC1 for PCI enumeration?"
**Expected**: THC1 is PCI Function 1 and THC0 is PCI Function 0. Per PCI spec, Function 0 must be active for Function 1 to enumerate. If THC0 is disabled in BIOS, THC1 will not appear on the PCI bus even if independently enabled. This is a common BIOS misconfiguration pitfall.
**Pass Criteria**: States THC0 must be enabled for THC1 to enumerate AND explains PCI Function 0/1 dependency

### PLAT-012: RZL/TTL Platform THC Generation
**Prompt**: "Which THC IP generation do RZL and TTL platforms use? Are there any THC-specific changes for these platforms?"
**Expected**: RZL and TTL use Gen4.2, sharing the unified HAS document `sip_thc_4x_has.html`. The HAS states "RZL/TTL 1.0 (no change)" — meaning no THC-specific silicon changes versus NVL. They inherit all Gen4.x features including HIDSPI, HIDI2C, SWDMA, and the 4-level D3 model.
**Pass Criteria**: States Gen4.2 AND "no change" from NVL AND mentions unified HAS document

### DBG-008: Device Not Enumerating Triage Playbook
**Prompt**: "What are the steps in the THC 'Device Not Enumerating' debug triage playbook?"
**Expected**: 9-step playbook: (1) Check Device Manager for THC controller presence, (2) Verify BIOS THC Configuration menu settings (port enabled, correct mode SPI/I2C), (3) Check touch device hardware connection and power, (4) Verify ACPI DSDT entries for THC device, (5) Check driver load status in Event Viewer, (6) Verify PCI config space (BAR, command register), (7) Check THC MMIO registers (PORT_SUPPORTED, PORT_TYPE), (8) Probe SPI/I2C bus with logic analyzer, (9) Try known-good touch device to isolate HW vs SW issue.
**Pass Criteria**: Lists at least 6 of the 9 steps AND includes BIOS check AND ACPI check

### SWAS-001: SwAS Reference Priority
**Prompt**: "What is the SwAS (Software Architecture Specification) priority level relative to the HAS for THC documentation conflicts?"
**Expected**: SwAS is Priority 1, same level as the HAS. When SwAS and HAS conflict, neither automatically overrides the other — the conflict must be resolved by the architecture team. SwAS covers software-visible behavior and driver interfaces while HAS covers hardware architecture.
**Pass Criteria**: States SwAS is Priority 1 AND same as HAS

### SWAS-002: Double Interrupt Processing Workaround (Pre-LNL)
**Prompt**: "What is the SWAS-001 / P0582 issue about double interrupt processing on pre-LNL QuickSPI platforms, and what is the workaround?"
**Expected**: On pre-LNL platforms, THC processes the interrupt edge twice if the device firmware is slow to deassert the interrupt line — the second processing is spurious. The workaround is to configure the interrupt as level-triggered for the first interrupt, then switch to edge-triggered after the initial reset interrupt is received. This fix is in Linux kernel 6.17 (commit 8fe2cd8).
**Pass Criteria**: Describes spurious double interrupt AND level-to-edge switch workaround AND mentions kernel 6.17 or commit 8fe2cd8

### SWAS-003: RAW_INT_STS MSI Blocked During Quiesce (LNL)
**Prompt**: "What happens to MSI delivery from RAW_INT_STS when THC_DEVINT_QUIESCE_EN is set on LNL?"
**Expected**: MSI is not generated from RAW_INT_STS when THC_DEVINT_QUIESCE_EN is set. This is an LNL RTL issue (SWAS-002 / P0587) where the quiesce mechanism over-blocks MSI generation. The driver must not expect MSI delivery while quiesced.
**Pass Criteria**: States MSI is blocked during quiesce on LNL AND mentions THC_DEVINT_QUIESCE_EN

### SWAS-004: Unused Error Categories in THC
**Prompt**: "Which THC error interrupt categories are defined in the HAS but never actually fire in software? Why?"
**Expected**: Four error categories are defined but unused: (1) Write DMA / TXDMA error interrupts, (2) Fatal Errors, (3) PIO Errors (I2C only), (4) I2C Sub-IP Errors. These are documented as not implemented by SW or HW (SWAS-003 / P0635-P0637, P0753-P0756). Test scripts should NOT expect these error paths to fire.
**Pass Criteria**: Lists at least 3 of the 4 unused categories AND states they don't fire by design

### SWAS-005: RTD3 PRW ACPI Crash (QuickI2C)
**Prompt**: "Why must BIOS NOT use _PRW (Power Resources for Wake) on THC I2C ACPI device nodes? What should be used instead?"
**Expected**: Adding _PRW with GPIO causes a Windows crash (SWAS-004). Windows interprets PRW as D3cold-capable and issues WaitWake IRP, which crashes when the GPIO controller is in a different power domain. The workaround is to use _PS0/_PS3/_DSW methods instead of Power Resource. _S0W should return 3 (D3hot, not D3cold). _DSW modifies _PS3 behavior.
**Pass Criteria**: States _PRW causes Windows crash AND recommends _PS0/_PS3/_DSW instead AND mentions _S0W returns 3

### SWAS-006: IC_DMA_RDLR Constraint (QuickI2C)
**Prompt**: "What is the maximum allowed value for IC_DMA_RDLR on THC I2C platforms, and why?"
**Expected**: IC_DMA_RDLR must be ≤ 7 (SWAS-005). The THC internal temp buffer can store a maximum of 8 bytes. Setting IC_DMA_RDLR > 7 causes buffer overflow within the I2C Sub-IP. Linux kernel uses IC_DMA_RDLR = 7.
**Pass Criteria**: States IC_DMA_RDLR ≤ 7 AND mentions 8-byte temp buffer constraint

### SWAS-007: Bus Clear Not Enabled on Linux (QuickI2C)
**Prompt**: "Does Linux enable THC's I2C bus clear (SDA/SCL stuck recovery) feature? How does this compare to Windows?"
**Expected**: Linux does NOT enable bus clear recovery (SWAS-006). THC supports SDA/SCL stuck bus clear per HAS, and Windows enables this feature, but Linux does not. This means Linux I2C may not recover from SDA/SCL stuck conditions. Test scripts on Linux should not expect bus clear recovery.
**Pass Criteria**: States Linux does NOT enable bus clear AND Windows does AND mentions SDA/SCL stuck recovery

---

## 8. Simics Pre-Silicon Validation

### SIM-001: DML Framework Basics
**Prompt**: "What is DML in the context of Simics THC model development? How does it relate to AutoDML?"
**Expected**: DML (Device Modeling Language) is Simics' native HDL-like language for writing device models. DML 1.4 is the current version. AutoDML auto-generates skeleton DML models from IP-XACT/SystemRDL register specs, reducing manual effort. AutoDML generates register banks, fields, and reset values automatically, but behavioral logic (state machines, DMA engines) must be added manually.
**Pass Criteria**: Explains DML as Simics modeling language AND mentions DML 1.4 AND describes AutoDML auto-generation from register specs

### SIM-002: THC Simics Model Types
**Prompt**: "What are the different THC Simics model types, and what does each provide?"
**Expected**: THC has three model types: (1) thc_vdm (Virtual Device Model) — pure-DML register-accurate model, no RTL, fast simulation; (2) SPI Transactor — bridges Simics SPI bus to VTC/SPARK backends for protocol-level testing; (3) Touch device models (WACOM, ELAN) — endpoint models that generate HID reports. The VTC (Verification Transactor Co-simulation) connects Simics to SystemVerilog testbenches. SPARK is the newer replacement for VTC.
**Pass Criteria**: Names thc_vdm AND SPI Transactor AND touch device models AND explains VTC/SPARK difference

### SIM-003: Chassis PM Framework in Simics
**Prompt**: "How does the Chassis PM framework work in Simics for THC power management validation?"
**Expected**: Chassis PM framework provides standardized power management for IP models in Simics. THC model implements Chassis PM interfaces for D-state transitions (D0/D0i2/D3), clock gating (CGPG), and PMCLite sideband messaging. The framework handles power domain isolation (PGD/UGD) and coordinates with the PMC model for power state transitions.
**Pass Criteria**: Mentions Chassis PM framework AND D-state transitions AND PMCLite sideband AND PGD/UGD domains

### SIM-004: Per-Platform Simics Setup
**Prompt**: "How do I set up a Simics environment for THC validation on LNL vs PTL vs NVL platforms?"
**Expected**: Each platform has specific load-target commands and object paths. Setup involves: (1) Install simlauncher and simics packages; (2) Use load-target with platform-specific scripts; (3) Configure touch device model (enable touchscreen, set SPI/I2C mode). Object paths differ per platform (e.g., board.mb.sb.thc[0] vs board.mb.soc_south.thc). The per-platform guide covers LNL, PTL, NVL, WCL, and TTL.
**Pass Criteria**: Mentions load-target AND platform-specific object paths AND at least 3 platforms (LNL/PTL/NVL)

### SIM-005: PythonSV SW-CI for THC
**Prompt**: "How is PythonSV SW-CI used for THC pre-silicon validation in Simics? What test infrastructure does it provide?"
**Expected**: PythonSV SW-CI (Software Continuous Integration) enables running PythonSV-based THC test scripts against Simics models. Tests use namednodes for register access (same as post-silicon). The SW-CI framework provides automated regression with Simics backend, allowing pre-silicon test execution before tape-out. Tests from the PSV repo can be reused with minimal changes.
**Pass Criteria**: Mentions PythonSV SW-CI AND namednodes AND pre-silicon test execution AND test reuse

### SIM-006: THC IPSV vs PSV Test Repos
**Prompt**: "What is the difference between the THC IPSV and PSV test repositories? When should each be used?"
**Expected**: IPSV (IP-level Silicon Validation) repo contains pre-silicon/emulation tests targeting the THC IP model in isolation or small-scope Simics environments. PSV (Post-Silicon Validation) repo contains post-silicon tests for real hardware. IPSV tests run against Simics models before tape-out; PSV tests run on actual silicon after tape-out. Some tests can be shared between repos with abstraction layers.
**Pass Criteria**: Distinguishes IPSV (pre-silicon) from PSV (post-silicon) AND explains when each is used

### SIM-007: SPI Transactor and VTC/SPARK
**Prompt**: "What is the SPI Transactor in the THC Simics model, and how do VTC and SPARK differ?"
**Expected**: The SPI Transactor bridges the Simics SPI bus interface to co-simulation backends. VTC (Verification Transactor Co-simulation) is the legacy backend that connects to SystemVerilog testbenches for RTL-level co-simulation. SPARK is the newer replacement for VTC with improved performance and simpler integration. The transactor handles SPI opcode translation, clock configuration, and data marshaling between Simics and the backend.
**Pass Criteria**: Explains SPI Transactor role AND distinguishes VTC (legacy) from SPARK (newer) AND mentions co-simulation

### SIM-008: THC Simics Debug Techniques
**Prompt**: "What debug techniques are available for THC validation in Simics? How do you trace register access and DMA operations?"
**Expected**: Debug techniques include: (1) Register access logging via DML log statements; (2) Simics CLI commands (log-level, break-io) for register breakpoints; (3) DMA buffer inspection using memory read commands; (4) Transaction tracing for SPI/I2C bus activity; (5) Fuse debugging for strapped configurations. The `simics>` CLI provides interactive debug, and scripts can automate multi-step debug sequences.
**Pass Criteria**: Lists at least 3 debug techniques AND mentions register breakpoints AND DMA inspection

### SIM-009: Requirements Gap Analysis
**Prompt**: "What are the key gaps in the THC Simics model requirements? Which ones are highest priority?"
**Expected**: The gap analysis identifies 37 gaps (G1-G37) across categories: register coverage, DMA engine completeness, interrupt controller accuracy, power management compliance, protocol support, and test infrastructure. Priority breakdown: ~12 P0 (critical), ~15 P1 (important), ~10 P2 (nice-to-have). P0 gaps include missing SWDMA engine model, incomplete PMCLite sideband, and missing display sync support.
**Pass Criteria**: Mentions G1-G37 gap range AND priority breakdown (P0/P1/P2) AND names at least 2 specific P0 gaps

### SIM-010: S0ix PM Enabling in Simics
**Prompt**: "How is S0ix power management enabled and validated for THC in a Simics environment?"
**Expected**: S0ix PM enabling in Simics involves: (1) Configuring the PMC model to support S0ix entry/exit; (2) Enabling THC LTR (Latency Tolerance Reporting) in the model; (3) Verifying D0i2 entry via CGPG assertion; (4) Testing wake-from-S0ix via GPIO interrupt path. The Chassis PM framework coordinates the S0ix flow between THC, PMC, and platform models. Known challenges include accurate PMCLite timing and power gate sequencing.
**Pass Criteria**: Mentions S0ix entry/exit AND LTR AND D0i2/CGPG AND PMC coordination
