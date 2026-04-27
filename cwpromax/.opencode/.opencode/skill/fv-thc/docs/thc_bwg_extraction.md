# THC BIOS Writer Guide (BWG) Extraction

> **Owner**: Chin, William Willy (`willychi`)

Structured extraction from **Chap69_BIOS_WG_THC.docx** — "THC Software Flow Specification".

**Source**: `docs.intel.com/documents/iparch/thc/thc_files/Chap69_BIOS_WG_THC.docx`
**Document**: Rev 0.5, March 2017 (TGP-era template). Last modified: 2024-09-24 by Kevin Zhenyu Zhu.
**Scope**: BIOS programming requirements for THC IP. Originally TGP; later updated with MTL+ Device ID note (DID bit[16]).

---

## 1. Software Flow Dependencies

### 1.1 GPIO Dependencies
- BIOS must program THC-SPI GPIOs to retain last driven values on Vnn removal (**IOSTANDBY** configuration).
- BIOS must route native functions to correct THC/SPI controller based on platform configuration.
- GPIO routing determines which THC port owns which SPI/I2C bus.

### 1.2 ICC SSC Dependency
- SSC (Spread Spectrum Clocking) on SPI clock can be disabled via ICC PLL SSC disable bit.
- **Open item**: BIOS may not have access to this control on all platforms.

### 1.3 Reset Dependencies
Two conditions require DEVRST assertion:
1. **Unrecoverable error** — Driver asserts DEVRST to recover the touch IC.
2. **D3/S0ix/Sx entry** — SW must assert DEVRST before entering D3 state.

### 1.4 Platform-Specific Dependencies
- D3 and Vnn power rail sequencing is platform-specific.
- BIOS must coordinate THC power gating with platform power management (PMC).

---

## 2. BIOS Setup / Policy Knobs

BIOS must expose the following configuration options (setup menu or policy):

| Knob | Description | Notes |
|------|-------------|-------|
| Touch Port Config | Port configuration scenario (see Section 4) | Determines GPIO routing, PORT_SUPPORTED, Function Disable |
| LTR Values | Active and Low Power LTR values and scales | ACT_LTR_VAL, ACT_LTR_SCALE, LP_LTR_VAL, LP_LTR_SCALE |
| D0i3 Enable | Enable/disable D0i3 support | TGP POR = not supported; if needed, set NXTP bit in dev idle cap |
| Function Disable | Per-THC function disable | Sets THC_CFG_UR_STS_CTL.FD = 1 (see Section 5) |
| PM Enable/Disable | Enable/disable power management | Controls HAE, D3HE in THC_CFG_PCE |
| Min Reset Time | Minimum device reset assertion time | BIOS-to-driver communication only; no physical register |
| SPI Frequency | SPI clock divider selection | Programs TCWF (write freq) and TCRF (read freq) |
| SPI IO Mode | Single / Dual / Quad | Programs SPI IO mode registers |
| D0i2 Entry Timer | D0i2 idle timer before entry | Default = 100ms; platform-tunable (e.g., TGPLP = 10us) |
| D0i2 RXDMA Policy | D0i2 RXDMA behavior policy | D0I2_RXDMA_POLICY register |
| LTR Enable | Enable LTR reporting | THC_LTR_EN bit |
| MTL+ DID bit[16] | RWOnce: 0 = Intel PTSP, 1 = HIDSPI | MTL and later platforms only |

---

## 3. PCI Init & Enumeration Flow

Ordered BIOS initialization steps:

1. **Read DEVVENDID** — Verify THC device is present (check vendor/device ID register).
2. **Assign BAR** — Program BAR0 (32KB MMIO range, 64-bit, Type 0).
3. **Assign SSID/SSVID** — Program Subsystem ID and Subsystem Vendor ID.
4. **Set Class Codes** — Program Base Class Code and Sub-Class Code.
5. **Configure MSI** — Program MSI capability registers to enable MSI.
6. **Configure Legacy Interrupt** — Set THC_CFG_INT.IPIN for legacy INTx.
   - **MSFT G5 Panel**: If supporting Microsoft G5 panel, set **bit 31 of THC MMIO offset 0x1128** to 1.
7. **Program THC_CFG_PCE** — Set HAE (bit 5) and D3HE (bit 2) for power gating control.
8. **Configure SAI Policy** — Write SAI policy registers (P39h:20h-3Ch) if default values need modification.
9. **Enable Clock Gating** — Set all clock enable bits in IOSF SB private registers.
10. **Enable Power Gating** — Set appropriate bits in THC_CFG_PCE (HAE, SE, D3HE, SPE per platform).
11. **Program LTR** — Set ACT_LTR_VAL, ACT_LTR_SCALE, LP_LTR_VAL, LP_LTR_SCALE, THC_LTR_EN.
12. **Set BIOS_LOCK_EN** — Lock BIOS-configured registers before OS handoff (security requirement).

---

## 4. Port Configuration Scenarios

Four BIOS configuration scenarios for THC port assignment:

### Scenario 1: Two THC Ports, Each with Own Driver
- Program SPI1 GPIOs -> THC0 port 0
- Program 2nd SPI GPIOs -> THC1 port 0
- THC0 clears PORT_SUPPORTED for port 1
- THC1 clears PORT_SUPPORTED for port 1
- Result: Two independent THC instances, each driving one touch device.

### Scenario 2: Two THC Ports, Single Driver (ZBB'ed)
- Program SPI1 GPIOs -> THC0 port 0
- Program 2nd SPI GPIOs -> THC0 port 1
- Function Disable THC1
- Result: Single THC instance driving two ports.

### Scenario 3: One THC Port Only
- Program SPI1 GPIOs -> THC0 port 0
- THC0 clears PORT_SUPPORTED for port 1
- Function Disable THC1
- Result: Single THC instance, single port.

### Scenario 4: Both THCs Disabled
- Program SPI1 GPIOs -> legacy SPI Touch port (not THC)
- Function Disable both THC0 and THC1
- Result: THC IP completely disabled; legacy SPI touch path used.

### Port Configuration Summary

| Scenario | THC0 Port 0 | THC0 Port 1 | THC1 | Use Case |
|----------|-------------|-------------|------|----------|
| 1 | Active | PORT_SUPPORTED=0 | Active (port 0 only) | Dual touch, dual driver |
| 2 | Active | Active | FD=1 | Dual touch, single driver |
| 3 | Active | PORT_SUPPORTED=0 | FD=1 | Single touch |
| 4 | Disabled | Disabled | FD=1 | Legacy SPI touch |

---

## 5. Function Disable Flow

To fully disable a THC function:

1. **Enable all clock gating controls** — Write IOSF SB CDC config registers (CCC0 -> CCC3 transition for P39h:0h and P39h:4h).
2. **Set HAE = 1** in THC_CFG_PCE — Enable HW autonomous power gating.
3. **Set function into D3 state** — Write PMCSR[1:0] = 11.
4. **Set FD = 1** in THC_CFG_UR_STS_CTL — Function Disable bit.

**Post-disable state**:
- No SW or device wake supported.
- PSF programmed by BIOS to UR (Unsupported Request) all cycles to this function.
- Recovery requires power cycle (FD is sticky until reset).

### Disable Port (Not Full Function Disable)
- BIOS clears the **PORT_SUPPORTED** bit of the disabled port.
- The THC function remains active for the other port.

### DFx Clock Override
- BIOS provides **SPI_DFX_CLK_EN** bit for DFX clock override during debug/manufacturing.

---

## 6. Power Management Flow

### 6.1 S3/S4/S5 Entry Sequence
Three-step sequence (strict order):
1. SW asserts **DEVRST** bit (reset touch IC).
2. SW completes **D3 entry** (PMCSR[1:0] = 11).
3. Platform initiates **Sx entry** (S3/S4/S5).

### 6.2 S3 Resume (Exit)
- BIOS shall **reinitialize THC using the same boot init flow** (full re-init from scratch, same as cold boot).
- All registers are lost during S3; no partial restore path.

### 6.3 RTD3 (Runtime D3)
- SW asserts **DEVRST** before D3 entry.
- Same as Sx entry steps 1-2, but without step 3 (no Sx transition).

### 6.4 Connected Standby Power States

| System State | THC Power State | PG Type | Description |
|-------------|----------------|---------|-------------|
| S0 active | D0 | None | Normal operation |
| S0 idle | D0i2 | HW-autonomous (IP-accessible) | Programmable idle timer triggers entry |
| S0 standby | D3 | IP-accessible PG | SW-initiated, IP remains powered |
| S0ix | D3 | IP-inaccessible PG | SW asserts DEVRST -> D3 -> S0ix entry |
| Sx (S3/S4/S5) | D3 | IP-inaccessible PG | Full power removal |

### 6.5 S0ix Entry Sequence
Same three-step pattern as Sx:
1. SW asserts DEVRST.
2. SW completes D3 entry.
3. Platform initiates S0ix entry.

### 6.6 Wake Event Constraints
- **D0i2**: Touch device wake IS supported (touch interrupt wakes THC from D0i2).
- **D3**: Only **SW wake** supported (no touch device wake from D3).
- Implication: If touch wake is required during connected standby, THC must remain in D0i2, not D3.

### 6.7 Clock / PLL Gating (Debug Only)
- IOSF SB private registers can optionally enable/disable clock gating.
- **BIOS does NOT need to configure these for normal operation** — use soft straps `ClockGateEnable` and `PowerGateEnable` instead.
- These registers are for debug and manufacturing override only.

---

## 7. Security

- **BIOS is required to set THC_BIOS_LOCK_EN** after completing all THC initialization.
- This prevents modification of BIOS-configured registers after OS handoff.
- Lock bit sequence:
  1. BIOS configures all THC registers.
  2. BIOS sets `BIOS_LOCK_EN` — prevents further BIOS-region modification.
  3. OS driver loads.
  4. Driver sets `DRV_LOCK_EN` — prevents modification of driver-configured registers.
  5. Both locks are sticky until reset.

---

## 8. SAI Policy Registers (IOSF SB Port P39h)

Source Access Identifier (SAI) policy registers control which agents can access THC register spaces.

| Offset | Register Name | Default | Description |
|--------|---------------|---------|-------------|
| `P39h:20h` | `THC_SB_SAI_CNTRL_PLCY0` | `0x0000_0000` | SAI Access Control Policy Reg 0 |
| `P39h:24h` | `THC_SB_SAI_CNTRL_PLCY1` | `0x0000_0000` | SAI Access Control Policy Reg 1 |
| `P39h:28h` | `THC_SB_SAI_CMN_PLCY0` | `0x0000_0000` | SAI Access Common Register Policy Reg 0 |
| `P39h:2Ch` | `THC_SB_SAI_CMN_PLCY1` | `0x0000_0000` | SAI Access Common Register Policy Reg 1 |
| `P39h:30h` | `THC_SB_SAI_PORT0_PLCY0` | `0x0000_0000` | SAI Access Device 0 (Port 0) Policy Reg 0 |
| `P39h:34h` | `THC_SB_SAI_PORT0_PLCY1` | `0x0000_0000` | SAI Access Device 0 (Port 0) Policy Reg 1 |
| `P39h:38h` | `THC_SB_SAI_PORT1_PLCY0` | `0x0000_0000` | SAI Access Device 1 (Port 1) Policy Reg 0 |
| `P39h:3Ch` | `THC_SB_SAI_PORT1_PLCY1` | `0x0000_0000` | SAI Access Device 1 (Port 1) Policy Reg 1 |

### SAI Policy Structure
- **CNTRL_PLCY** (0x20-0x24): Controls access to THC control registers (config space).
- **CMN_PLCY** (0x28-0x2C): Controls access to common MMIO registers.
- **PORT0_PLCY** (0x30-0x34): Controls access to Port 0 MMIO registers.
- **PORT1_PLCY** (0x38-0x3C): Controls access to Port 1 MMIO registers.
- Each policy has two 32-bit registers (PLCY0 + PLCY1) forming a 64-bit SAI bitmask.

---

## 9. CDC Config Registers (IOSF SB Port P39h)

Clock Domain Crossing (CDC) configuration registers control clock gating behavior.

### Normal Operation (Default State)

| Offset | Register Name | Default | Description |
|--------|---------------|---------|-------------|
| `P39h:0h` | `THC_SB_PR_CDC_CFG` | `0x0000_CCC0` | Primary Clock Domain CDC Config |
| `P39h:4h` | `THC_SB_SD_CDC_CFG` | `0x0000_CCC0` | Side Clock Domain CDC Config |
| `P39h:8h` | `THC_SB_SSC_CDC_CFG` | `0x0000_0001` | SSC Clock Domain CDC Config |
| `P39h:Ch` | `THC_SB_ROSC_CLK_CFG` | `0x0000_0001` | ROSC Clock Domain CDC Config |

### Clock Gating Enabled State (Function Disable / CG Active)

| Offset | Normal Value | CG-Enabled Value | Change |
|--------|-------------|-------------------|--------|
| `P39h:0h` | `0x0000_CCC0` | `0x0000_CCC3` | CCC0 -> CCC3 |
| `P39h:4h` | `0x0000_CCC0` | `0x0000_CCC3` | CCC0 -> CCC3 |
| `P39h:8h` | `0x0000_0001` | `0x0000_0001` | No change |
| `P39h:Ch` | `0x0000_0001` | `0x0000_0001` | No change |

**Key**: The CCC0 -> CCC3 transition in the Primary and Side clock domain registers enables full clock gating. This is Step 1 of the Function Disable flow.

---

## 10. THC_CFG_PCE Bit Reference

Power Control Enable register at PCI config offset `0xA2`:

| Bit | Name | RW | Default | Description |
|-----|------|----|---------|-------------|
| 5 | HAE | RW | 1 | HW Autonomous Enable — PGCB may request PG when IP is idle |
| 4 | RSVD2 | RW | 0 | Reserved |
| 3 | SE | RW | 1 | Sleep Enable — IP may assert Sleep signal during PG |
| 2 | D3HE | RW | 0 | D3-Hot Enable — PG when idle AND PMCSR[1:0]=11 (D3) |
| 1 | I3E | RW | 0 | I3 Enable — PG when idle AND D0i3C[2]=1 |
| 0 | SPE | RW | 0 | SW PG Enable — PG when pmc_sw_pg_req_b=0 (PMC-assisted HW autonomous) |

**BIOS must set**: HAE (bit 5) and D3HE (bit 2) during init. SE (bit 3) defaults to 1.

---

## 11. DEVRST Assertion Summary

| Trigger | Who Asserts | When | Purpose |
|---------|------------|------|---------|
| Unrecoverable error | OS driver | Runtime | Recover touch IC from hung/error state |
| D3 entry | OS driver / BIOS | Before PMCSR write | Reset touch IC before power removal |
| S0ix entry | OS driver | Before D3 -> S0ix | Ensure clean touch IC state for low power |
| Sx entry (S3/S4/S5) | OS driver / BIOS | Before D3 -> Sx | Ensure clean touch IC state for sleep/hibernate |
| RTD3 entry | OS driver | Before D3 | Runtime power savings |

**Critical rule**: DEVRST must ALWAYS be asserted before any D3/S0ix/Sx transition. Failure to assert DEVRST before D3 can leave the touch IC in an undefined state on resume.

---

## SwAS Cross-Reference Notes (Added 2026-03-06)

> The following findings from the QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0 supplement or supersede BWG content.
> The BWG is TGP-era (2017); the SwAS documents are LNL/PTL-era and reflect current driver architecture.

### RTD3 / Power Resource Guidance (QuickI2C SwAS — Supersedes BWG Section 6)

The BWG describes generic RTD3 flow (DEVRST → D3 → Sx). The QuickI2C SwAS v1.0 adds **critical RTD3 ACPI guidance** that is NOT in the BWG:

- **PRW on ACPI device with GPIO will crash Windows** — Windows interprets PRW as "can wake from D3cold" and issues a `WaitWake` IRP, which crashes when the GPIO controller is in a different power domain.
- **Workaround**: Use `_PS0`/`_PS3`/`_DSW` methods instead of Power Resource. For wake-capable devices: no D3cold, `_S0W` returns 3, power rail management goes in `_PS0`/`_PS3`, `_DSW` modifies `_PS3` behavior.
- **Impact on BWG Section 6.3 (RTD3)**: BWG's RTD3 section does not mention this ACPI constraint. Any BIOS implementing RTD3 for THC+I2C must follow the SwAS guidance, not the BWG generic pattern.

### Reset Timeout Discrepancy (SwAS vs BWG)

- **BWG**: Does not specify protocol-specific reset timeouts.
- **QuickSPI SwAS**: Reset timeout = **1 second** (SPI).
- **QuickI2C SwAS**: Reset timeout = **5 seconds** (I2C).
- **Linux kernel**: Uses 5 seconds for **both** SPI and I2C (conservative approach).

### Registry / ECO Keys Not in BWG

The following driver-tunable registry keys are documented in the SwAS but have **no BWG equivalent**:

| Key | SwAS Source | Purpose |
|-----|-----------|---------|
| `IO_Mode_Override` | QuickSPI SwAS | Override SPI IO mode |
| `SPI_Frequency_Override` | QuickSPI SwAS | Override SPI clock frequency |
| `TxDMA_Override` | QuickSPI SwAS | Override TX DMA behavior |
| `I2C_Max_Frame_Size_Enable` | QuickI2C SwAS | Enable I2C max frame size cap |
| `I2C_Max_Frame_Size` | QuickI2C SwAS | Max frame size value (128–255) |
| `I2C_Int_Delay_Enable` | QuickI2C SwAS | Enable I2C interrupt delay |
| `I2C_Int_Delay` | QuickI2C SwAS | Interrupt delay value (1ms default on PTL/WCL) |
| `EnEdgeTriggeredINT` | QuickI2C SwAS | Enable edge-triggered interrupt mode |
| `TimeStampEnable` | QuickI2C SwAS | Enable DMA timestamps |
| `ResetRequiredByDriver` | QuickI2C SwAS | Driver controls device reset |
| `ISRDPCProfilingEn` | QuickI2C SwAS | Enable ISR/DPC profiling |
| `EnResetPollingWA` | QuickI2C SwAS | Enable reset polling workaround |
| `EnableFWFlashWABOM36` | QuickI2C SwAS | FW flash workaround for BOM36 |
| `DoNotWaitForResetResponse` | QuickI2C SwAS | Skip reset response wait |

### ACPI Frequency Encoding (QuickSPI SwAS — New Detail)

The QuickSPI SwAS documents ACPI frequency encoding not present in BWG:
- Bits 0–2 of `connection_speed` DSM return: `011`=40MHz, `100`=30MHz, `101`=24MHz, `110`=20MHz, `111`=17MHz
- `LimitPacketSize` encoding also documented in DSM return value

### Bus Clear Recovery (QuickI2C SwAS — New Detail)

- THC supports SDA/SCL stuck bus clear recovery per HAS.
- **Windows**: Enables bus clear. **Linux**: Does NOT enable bus clear.
- BWG does not mention bus clear capability.

---

## Source Reference
- **Document**: Chap69_BIOS_WG_THC.docx, "THC Software Flow Specification", Rev 0.5
- **Origin**: TGP-era (March 2017), updated with MTL+ DID bit[16] note (September 2024)
- **Download**: `https://docs.intel.com/documents/iparch/thc/thc_files/Chap69_BIOS_WG_THC.docx`
- **Last updated in repo**: 2026-03-06
- **SwAS cross-references added**: 2026-03-06 (QuickSPI SwAS v1.0, QuickI2C SwAS v1.0)
