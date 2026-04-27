---
name: fv-thc/power
description: THC power management — LTR, D0i2, CGPG, D3 (4 levels), S0ix, WoT, PMCLite sideband messages, Adaptive Touch PM
---

> Platform-specific PM implementation: see [linux.md](linux.md) and [windows.md](windows.md)

## QuickSPI/QuickI2C SwAS note on LTR DSM values

- LTR DSM return types (QuickSPI/QuickI2C SwAS v1.0): platform DSMs that return LTR values provide Active and Idle LTR as integer values expressed in microseconds. Drivers should parse these as integer microsecond values and convert as needed when composing PMC LTR messages or applying power policy. (QuickSPI SwAS v1.0)

# THC Power Management Reference

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.


Complete power management documentation covering all THC power states, transitions, and PMC interactions.
 
## Power Wells and Isolation

### Power Domains
THC has two power domains:
| Domain | Name | Description |
|--------|------|-------------|
| **THC_PGD** | Power-Gateable Domain | Main THC logic, gated during D0i2/D3 |
| **THC_UGD** | Un-gated Domain | Always-on logic (runtime interrupt routing for D0i2 wake). **Note**: UGD does NOT route platform wake signals to PMC — platform wake from D3/Sx comes through GPIO IP (vGPIO), not THC. See `fv-thc/wot` for details. |

### Isolation Gates
- Isolation required: PGD → UGD direction
- Isolation NOT required: UGD → PGD direction
- 10-bit `thc_res_own_req/ack` for Chassis 2.2 Sleep States

### Power Gating Entry
- D0i2 entry: HW-autonomous, programmable timer (max 1 second)
- State retention maintained during power gating
- Context saved in UGD domain

### PMC Power Well Interactions
- THC is located on the LPSS power well (same domain as other serial IP). PMC controls power gating via sideband messages. PMCLite is the lightweight sideband interface used by THC to signal PMC for PG/D0i2/D3 transitions and Save/Restore events.

## LTR (Latency Tolerance Reporting)

Controller-level LTR via IOSF Sideband messages to PMC.

 - **Active LTR**: Sent when RXDMA Start bit set and ACTIVE_LTR_EN = 1, or on a protocol interrupt when ACTIVE_LTR_EN is set
 - **Low Power LTR (LP LTR)**: Sent/used when LP_LTR_EN = 1; permits deeper idle

> **SwAS vs implementation note (QuickSPI)**: QuickSPI SwAS initialization guidance also documents an alternate baseline where Active LTR is configured to 1ms (scale 2) with LP LTR disabled during early reset/init windows. Keep this as a spec-reference note; current Linux/Windows driver defaults in this skill remain 5us Active and 500us LP unless overridden by ACPI/registry/platform policy.

### LTR Registers
- `LP_LTR_EN`, `ACTIVE_LTR_EN`
- `LP_LTR_VALUE`, `LP_LTR_SCALE`, `ACTIVE_LTR_VALUE`, `ACTIVE_LTR_SCALE`
- `LP_LTR_REQ`, `ACTIVE_LTR_REQ`

### LTR Scale Values
| Scale | Multiplier |
|-------|-----------|
| 0b000 | 1 ns |
| 0b001 | 32 ns |
| 0b010 | 1,024 ns |
| 0b011 | 32,768 ns |
| 0b100 | 1,048,576 ns |
| 0b101 | 33,554,432 ns |

### LTR message generation (Linux vs Windows)

- Linux: The driver programs LTR VALUE + SCALE registers, sets LP_LTR_EN/ACTIVE_LTR_EN to enable, and then raises the corresponding LP_LTR_REQ/ACTIVE_LTR_REQ bits to cause the IOSF-sideband LTR message to PMC. There is no special toggle sequence required by the Linux `thc_ltr_unconfig()` implementation — unconfigure simply clears the enable/request bits (see Unconfigure section).
- Windows: Windows drivers may use a write/toggle sequence (set EN=0, short stall, EN=1) in their LTR message path and sometimes insert a short stall (for example ~5 µs). This is an OS-specific implementation detail and not how the Linux driver generates LTR messages.

> **LTR DSM type annotations (SwAS)**: QuickSPI/QuickI2C SwAS v1.0 clarifies that platform `_DSM` function for LTR values (Platform DSM GUID) returns Integer values representing microseconds for both Active and Idle LTR fields. Drivers should parse these DSM returns as Integers (microseconds) when configuring `ACTIVE_LTR_VALUE` and `LP_LTR_VALUE`. (QuickSPI SwAS v1.0)

### LTR Config Flow (Linux vs Windows)

- Linux config flow (thc_ltr_config): caller passes a raw latency in microseconds → driver converts to {scale, value} using descending range checks (scale 5 first, then 4, 3, else default 2) → writes LP_LTR_VALUE+LP_LTR_SCALE and ACTIVE_LTR_VALUE+ACTIVE_LTR_SCALE → sets ACTIVE_LTR_EN (enable) and **clears LP_LTR_EN** (LP_LTR_EN is in ltr_mask but NOT in ltr_ctrl, so it is cleared) → sets LP_LTR_REQ and ACTIVE_LTR_REQ to generate the IOSF-sideband LTR messages.
- Windows config flow: same high-level conversion (findOptimalScaleAndValue) but implemented in HalLTR::SetLTR()/findOptimalScaleAndValue; Windows drivers may use a toggle/write sequence and short stalls as implementation details.

### Performance Limit Enforcement (`perf_limit`)

The kernel enforces a performance limit delay via `udelay(perf_limit * 10)` (units of 10µs) after SPI/I2C configuration changes. This is read from ACPI `_DSM` and stored in the driver context. If `perf_limit` is non-zero, the driver inserts this delay to allow the bus to stabilize before proceeding. Validation should verify that this delay is respected and does not cause timeout issues with touch device response timing.

## RLTR (Resource LTR)

Resource LTR restores the previously configured LTR values after exiting low-power or reset states where the LTR configuration may have been lost (power-gated domain).

**Restore triggers**: D3→D0 transition, S0ix exit, warm reset, CGPG exit
**Registers**: `LTR_CTRL` (offset `0x14` in common space) — fields: `LP_LTR_EN`, `ACTIVE_LTR_EN`, `LP_LTR_REQ`, `ACTIVE_LTR_REQ`, `LP_LTR_VAL[9:0]`, `LP_LTR_SCALE[12:10]`, `ACTIVE_LTR_VAL[25:16]`, `ACTIVE_LTR_SCALE[28:26]`
**Restore sequence**: Driver must re-program both LP and Active LTR values before re-enabling LTR. Linux defaults: LP=5µs, Active=500µs. Windows defaults: LP=0x3FF (max, ~1ms), Active=0x3FF.
**Validation**: After each power transition listed above, read `LTR_CTRL` and verify values match pre-sleep configuration. Check that `LP_LTR_EN` and `ACTIVE_LTR_EN` are set. If values are zero after resume, RLTR restore failed — indicates a driver or BIOS bug.

## D0i2 Idle State

HW autonomous power gating with state retention.

**Entry Flow**: CDC timer expires → `PCE.HAE` enabled → D0i2 Timer Expiry → power gate.

**D0i2 entry conditions (Linux)**:
- THC transitions to D0i2 when the port is idle: no pending DMA descriptors, no active transactions, and D0i2 entry feature enabled (`THC_M_PRT_CONTROL.D0I2_ENTRY_EN`).

> **Mandatory D0i2 entry prerequisites (SwAS)**: Both QuickSPI and QuickI2C SwAS documents specify two hard preconditions that must be satisfied before D0i2 entry: **(1)** no pending PIO transactions (PIO engine fully idle), and **(2)** all DMA engines (RXDMA1, RXDMA2, TXDMA, SWDMA) are idle with no outstanding completions. Attempting D0i2 entry with an active PIO or DMA operation will cause undefined behavior or hang the THC port.

**D0i2 exit conditions**:
- Exit is triggered by a device interrupt (Wake GPIO) or a host-initiated transaction that requires the port to return to D0.

**Key Registers**:
- `PCE.HAE` (bit 5): D0i2 Feature Enable
- `D0I2_RXDMA_POLICY`: DMA idle policy
 - `THC_SB_PM_CTRL`: `TS_D0I2_MODE`, `TIMESTAMP_SRC`, `LP_LTR_EN/ACTIVE_LTR_EN`, D0i2 timers
- `pmc_ip_sw_pg_req`: PMC software PG request

**ECT BIOS Knob**: `THC0_D0i2=1` enables D0i2 for THC0.
**FuseLite**: THC0 PortID=`0x10`, strap value `0x03` enables CG+PG for D0i2.

**Quiesce Bug (PTL, fixed NVL)**: During D0i2 PG exit, quiesce bit must mask interrupts to prevent glitches.

## CGPG (Clock Gating and Power Gating)

HW autonomous power gating (D0i2) + clock gating.

**Key Registers**:
- `THC_CFG_PCE` (offset `0xA2`): `SPE/PMCRE`(0), `I3E`(1), `D3HE`(2), `SE`(3), `HAE`(5)
  > ⚠️ Windows driver accesses at `0xA4` (32-bit DWORD); authoritative HAS offset is `0xA2` (16-bit). See `fv-thc/registers` Phase 6 note.
- CDC configs, DCGE, PGCB, SPI_CTRL
- **PMC Status**: `LPM_LIVE_AGTPGATED_STS_2` (THC0/THC1 PG status bits)

## D3 Transitions (4 Levels, Gen4.1 PTL+)

| Level | Name | Power Gate | Vnn Removal | Save/Restore | Port Support |
|-------|------|-----------|-------------|-------------|--------------|
| Level 0 — D3 (Pure) | SW D3 | No | No | No (context preserved, Vnn maintained) | THC0 + THC1 |
| Level 1 — D3Hot | SW D3 + PG | Yes | No | No (driver/platform saves/restores MMIO state) | THC0 + THC1 |
| Level 2 — D3Cold w/ context | SW D3 + PG + SnR | Yes | Yes | **28 registers manual** (context lost, driver re-init) | **THC0 only** |
| Level 3 — D3Cold removed | SW D3 + PG + SnR | Yes | Yes | Full re-enumeration + platform reprobe | **THC0 only** |

> **THC1 limitation**: Per wiki, THC1 supports up to D3Hot only (no D3Cold). THC IP HAS says both are architecturally capable — may be platform-level restriction.
>
> **Terminology note**: Terminology varies across documents (HAS, BWG, PMCLite codes). Ensure platform-specific HAS/BWG mapping and test coverage for each D3 granularity on PTL/NVL platforms.

### D3Cold Save/Restore
28 registers manually saved/restored. HIDI2C note: I2C APB SubIP registers NOT included — must be reprogrammed separately.

### PCI PM Register
`THC_CFG_PMD_PMCSRBSE_PMCSR` (offset `0x74`): `PWRST` bits[1:0] — 0=D0, 3=D3.

### PMCLite Sideband Message Codes

| Direction | Code | Meaning |
|-----------|------|---------|
| THC→PMC | `0x8086D000` | D0 (active) |
| THC→PMC | `0x8086D301` | D3 entry |
| THC→PMC | `0x8086D302` | D3Hot entry |
| THC→PMC | `0x8086D303` | D3Cold entry |
| THC→PMC | `0x80860200` | Save Complete |
| THC→PMC | `0x80860201` | Restore Complete |
| THC→PMC | `0x80860301` | PG Entry |
| THC→PMC | `0x80860302` | PG Exit |
| THC→PMC | `0x8086D201` | D0i2 Entry |
| THC→PMC | `0x8086D200` | D0i2 Exit |
| UHFI→PMCLite | `0x8086D310` | D3 Level 0 (pure D3) |
| UHFI→PMCLite | `0x8086D311` | D3Hot |
| UHFI→PMCLite | `0x8086D312` | D3Cold (default) |

**PMCLite PortIDs**:
- PTL: THC0=`0xF26E`, THC1=`0xF26F`
- NVL: THC0=`0xFC6E`, THC1=`0xFC6F`

## Chassis 2.2 Sleep States

### Resource Ownership
Uses `resource_own_req/ack` wires (10-bit) and `sleep_level_req/rsp` (IOSF SB messages).

### Resource Mapping (10 bits)
| Bit | Resource | Description |
|-----|----------|-------------|
| 0 | Memory | Host memory access |
| 1 | IOSF Primary | Primary interface |
| 2 | IOSF SB | Sideband interface |
| 3 | THC CORE clk | Core clock domain |
| 4 | THC SB clk | Sideband clock domain |
| 5 | PGCB clk | Power gate control block clock |
| 6 | Vcc_Main (Vnn) | Main power rail |
| 7 | ROSC clk | Ring oscillator clock |
| 8 | SS clk | Spread spectrum clock |
| 9 | THC GPIO | GPIO interface |

### Additional Chassis 2.2 Signals
- `immediate_sleep_level_rsp` (wire) — fast response path
- `QoS_DMD/Rsp` (IOSF SB) — Quality of Service demands
- OBFF: **Not supported** by THC

### QOS_DMD Types
| Type | Direction | Scope | Description |
|------|-----------|-------|-------------|
| RLTR | IP→SOC | Memory only | Replaces THC LTR mechanism |
| RTALTR | SOC→IP | Memory only | Real-time advisory from SOC |
| RALTR | IP→SOC | Memory only | Advisory LTR from IP |

### Known Bug
- **HSDES 16014286225**: THC not fully Chassis 2.2 compliant
- PTL: POR keeps same behavior as LNL/MTL
- *RES_EN bits default to 0 (disabled)

## Touch IC Power States (Device Side)

THC coordinates with the touch IC through these device power states:
| State | Max Power | Description | Exit Latency |
|-------|-----------|-------------|-------------|
| **Off** (D3-Cold) | 0mW | Device powered off | Full init |
| **Sleep** (D3/D0i3) | 1mW | Deep sleep | 5ms |
| **Doze** | 5mW | Reduced sampling rate | Immediate |
| **Armed** | 10mW | Ready, no finger detected | Immediate |
| **Sensing** | 50mW | Active touch scanning | N/A (active) |

### State Transitions
- Sensing → Armed: No finger detected
- Armed → Doze: 300 seconds of inactivity
- Armed/Doze → Sleep: Connected standby entry
- Doze trigger: 30 seconds of inactivity from Armed

## S0ix Integration
- PMC-assisted save/restore
- D3 qualifies Vnn removal → permits S0ix substates
- **S*i2.0 entry permissible with THC in D0** (starting MTL SoC)
- THC does **NOT** generate wakes from S0ix

## Wake-on-Touch (WoT)

### Linux Implementation (kernel 6.17+, `intel-thc-wot.c`)
1. `device_init_wakeup(dev, true)` — mark as wakeup source
2. `dev_pm_set_dedicated_wake_irq(dev, wot->gpio_irq)` — assign wake IRQ; PM core **auto-manages** `enable_irq_wake`/`disable_irq_wake` on suspend/resume (no manual IRQ wake management needed)
3. **Graceful degradation**: If GPIO missing or not wakeable, WoT disabled with `dev_warn()` log message (returns void, non-fatal)
4. **Cleanup**: `thc_wot_unconfig()` calls `dev_pm_clear_wake_irq()` + `device_init_wakeup(dev, false)`

### WoT ACPI GPIO Configuration (Linux Kernel)
- **THC ACPI lacks `_DSD`**: Requires manual GPIO mapping via `acpi_dev_add_driver_gpios(adev, gpio_map)` before GPIO lookup
- **Dedicated GPIO**: WoT uses a **separate** ACPI GpioInt resource, distinct from the main touch interrupt
- **ACPI lookup key**: `"wake-on-touch"` — kernel searches for this named GPIO in the device's ACPI resources
- **Non-fatal absence**: If the `wake-on-touch` GPIO is not found in ACPI, WoT is disabled with `dev_warn()` (non-fatal)
- **Implementation**: `thc_wot_config()` calls `acpi_dev_gpio_irq_wake_get_by(adev, "wake-on-touch", 0, &wakeable)` → checks `wakeable` flag → `dev_pm_set_dedicated_wake_irq()`
- **Key distinction**: Main interrupt GPIO (for touch data) vs WoT GPIO (for wake from low-power) — these are independent; a platform may have data interrupt but no WoT GPIO
- **Single-stage only**: Linux kernel implements only single-stage GPIO-based WoT

### WoT Variants
- ⚠️ **Two-stage WoT and ULP WoT**: Referenced in HAS/docs but **NO implementation exists** in Linux kernel source (v6.17–6.20). Only single-stage GPIO WoT is implemented. Windows driver status unknown. Do NOT test these variants without confirming driver support.

### vGPIO Pad Locking (BIOS Dependency)
- **PADCFGLOCK_VGPIO_THC0** must be `0x0` (unlocked) for WoT to function
- BIOS "Force unlock on all GPIO pads" = Disable can lock the vGPIO_THC pad → WoT fails silently
- See `fv-thc/wot` Section 2.5 for full PADCFGLOCK debug methodology
- **Key HSDES**: 15018635096 (NVL PADCFGLOCK root cause), 15019129309 (NVL S4 hibernate + WoT failure — under investigation, multiple hypotheses: pad reset type, APIC vs SCI/GPE routing, pinctrl driver; linked FW bug 15019049216), 16029769688 (WCL IO APIC wake), 16028429994 (WCL BIOS fix)

## Interrupt Quiesce Mechanism
1. Set `THC_DEVINT_QUIESCE_EN = 1`
2. Poll `HW_STS` until confirmed
3. Perform DMA/power operation
4. Clear `THC_DEVINT_QUIESCE_EN = 0`
5. Poll `HW_STS` until unquiesced

**D0Entry exception**: TIC interrupt quiescing is NOT required during D0Entry — interrupts remain in their current state. Quiescing applies only to D0Exit/remove/shutdown paths.

> **Known PTL bug**: Quiesce fails during continuous touch (HSDES 16023244313 — delay WA applied).

## Adaptive Touch PM (Gen/platform attribution unverified)
- **Adaptive_Touch_PM_Summary**: Dynamic power state adjustment based on touch activity patterns
- **Smart_Touch_Pause_Scan**: Pause scan when no touch detected
- **Time-based coalescing**: Aggregate events over configurable windows
- **CLOS Power Balancing**: Resource prioritization across THC ports

## Power Goals (from HAS)

### Dynamic Power
| Scenario | Max Power |
|----------|-----------|
| PIO + TXDMA + RXDMA Quad/30MHz + IOSF | 4mW |
| PIO only | <4mW |
| RXDMA only | 4mW |
| TXDMA only | 4mW |
| IOSF only | 4mW |

### Static Power
| State | Max Power |
|-------|-----------|
| Idle (not power gated) | 150uW leakage |
| Power Gated (D0i2/D3) | <5uW |

### Performance Targets
| Metric | Target |
|--------|--------|
| TSI read bandwidth | 125MBps x 2 ports |
| SPI read bandwidth | 12MBps (20MBps Gen2) x 2 ports |
| INT to CS# latency | 400ns |
| Frame-end to MSI latency | 800ns |
| Power gate exit latency | 10us |

## Power Management Validation Points
- LTR: Active sent on RXDMA start, LP on idle, scale values match
- RLTR: Values restored after D3→D0, S0ix exit, warm reset
- D0i2: Entry after idle, state retention on exit, D3 overrides D0i2
- CGPG: Clock gating on idle, PG entry/exit, PMC status matches actual state
- D3: All 4 levels (Pure/D3Hot/D3Cold/D0i2), correct PMCLite SB code per level
- D3Cold: 28-register save/restore, Vnn removal qualification, full re-init on exit
- S0ix: Entry with THC idle, with THC in D3, no THC wake events
- WoT: Wake from D3hot/D3cold/S0ix, GPIO dedicated wake IRQ, `wake-on-touch` ACPI key
- Timestamp continuity across D0i2 (Mode 0 = pause, Mode 1 = reset)

- Verify LTR values are correctly programmed before D0i2 entry
- Verify D3 entry clears DMA state (PRD ring pointers reset) and that DMA is fully deconfigured during poweroff paths
- Verify Wake-on-Touch interrupt path remains active when platform/driver claims WoT support for the target D3 level
- Verify PMCLite sideband messages are sent at the correct points in D3/D0i2 entry and exit (Save/Restore, PG Entry/Exit codes)

## BIOS Power Flow (BWG)

> **Source**: `Chap69_BIOS_WG_THC.docx` — Section 6 (Power Management).
> **Full reference**: `fv-thc/docs/thc_bwg_extraction.md`

### DEVRST Assertion Conditions

BIOS/driver MUST assert DEVRST (Device Reset) in two situations:
1. **Unrecoverable error** — Driver detects fatal error → asserts DEVRST to reset the touch device
2. **D3/S0ix/Sx entry** — SW MUST assert DEVRST **before** initiating D3 entry

> **⚠️ DEVRST must complete before D3 transition begins.** Failure to assert DEVRST before D3 can leave the touch device in an undefined state.

### S3/S4/S5 Entry Sequence

| Step | Action | Notes |
|------|--------|-------|
| 1 | SW asserts DEVRST | Reset touch device before power removal |
| 2 | Complete D3 entry | PMCSR[1:0] = `11`, wait for D3 acknowledgment |
| 3 | Initiate Sx entry | Platform proceeds to S3/S4/S5 |

### S3 Resume (Exit)

BIOS shall **reinitialize THC using the same boot init flow** — full re-init from scratch, identical to cold boot. There is no "fast resume" path; all registers must be reprogrammed.

### RTD3 (Runtime D3) Entry

| Step | Action |
|------|--------|
| 1 | SW asserts DEVRST |
| 2 | Complete D3 entry |

RTD3 exit follows the standard D3→D0 restore flow (see D3 Transitions section above).

### Connected Standby Power States

| System State | THC Power State | Power Gating Type | Notes |
|--------------|----------------|-------------------|-------|
| S0 active (idle) | D0i2 | HW-autonomous PG | Programmable entry timer, state retention |
| S0 active (deeper idle) | D3 | IP-accessible PG | SW-initiated, Vnn maintained |
| S0ix | D3 | IP-**inaccessible** PG | SW asserts DEVRST → D3 → S0ix entry |
| Sx (S3/S4/S5) | D3 | IP-**inaccessible** PG | Full power removal, requires cold boot re-init |

**S0ix Entry Sequence**: SW asserts DEVRST → completes D3 entry → initiates S0ix entry (same pattern as Sx).

### Wake Event Constraints (BWG)

| Power State | Touch Wake Supported | SW Wake Supported |
|-------------|---------------------|-------------------|
| D0i2 | **Yes** — touch device interrupt wakes THC | Yes |
| D3 (any level) | **No** — touch device wake NOT supported | Yes — SW-initiated only |
| S0ix | **No** — requires D3→D0→D0i2 first | Yes — via PMC |
| Sx | **No** | Yes — platform wake sources only |

> **Key constraint (BWG-era)**: Touch-initiated wake (Wake-on-Touch / WoT) is only supported from D0i2 per the TGP-era BWG. In D3 or deeper, the touch device interrupt path is not active. The WoT flow documented earlier in this skill applies specifically to the D0i2→D0 transition.
>
> ⚠️ **ARCHITECTURE CORRECTION**: Wake-on-Touch (WoT) from D3/Sx does **NOT** go through THC's UGD domain. The actual wake path is: `Touch Device → GPIO pad → vGPIO (GPIO IP) → PMC → Platform Wake`. THC's PCI capabilities explicitly declare WAKE=No, PME=No — THC cannot generate wake signals. The Linux kernel WoT implementation (`intel-thc-wot.c`) uses `acpi_dev_gpio_irq_wake_get_by()` + `dev_pm_set_dedicated_wake_irq()` — 100% GPIO/ACPI/PM subsystem, zero THC register writes. THC's driver-side role is: register GPIO as wake source during probe, skip SET_POWER(SLEEP) during suspend so the touch device stays responsive, re-init hardware after resume. See `fv-thc/wot` for the complete corrected architecture.

### Clock/PLL Gating (BIOS Debug Only)

IOSF SB private registers can optionally enable/disable clock gating. BIOS does **NOT** need to configure these for normal operation — use soft straps `ClockGateEnable` and `PowerGateEnable` instead. The SB registers are for **debug override only**.

### ⚠️ CRITICAL: Windows RTD3 ACPI Configuration (QuickI2C SwAS v1.0)

**`_PRW` with GPIO on ACPI device causes Windows crash.** This is a known Windows ACPI framework issue documented in the QuickI2C SwAS v1.0.

**Workaround — Two RTD3 Configuration Patterns**:

| Scenario | D3Cold | ACPI Methods | `_S0W` | Power Resource | Notes |
|----------|--------|-------------|--------|---------------|-------|
| **Wake Enabled** | **Disabled** | `_PS0`, `_PS3`, `_DSW` | `3` (D3Hot) | **None** — no `_PR0`/`_PR3` | Must NOT use D3Cold when wake is needed |
| **No Wake** | **Enabled** | `_PR0`, `_PR3` | `0` (D0) | Yes (standard Power Resource) | D3Cold safe when no wake required |

**Key Rules**:
- **NEVER** combine `_PRW` with GPIO on the THC ACPI device — crashes Windows
- **Wake path**: Use `_PS0`/`_PS3` + `_DSW` (Device Sleep Wake) — no Power Resource
- **No-wake path**: Use standard `_PR0`/`_PR3` Power Resource — D3Cold permitted
- **`_DSW` method**: Receives wake enable/disable notification from OS; driver uses this to gate WoT behavior

> **Validation point**: Verify BIOS ACPI tables match the correct pattern for the wake/no-wake configuration. Incorrect pattern → Windows BSOD or silent WoT failure. This does NOT affect Linux (Linux uses `device_may_wakeup()` + GPIO IRQ, not ACPI Power Resources for wake gating).

## Windows vs Linux PM Cross-Platform Comparison

- Linux: uses standard PCI power management helpers (pci_save_state/pci_restore_state) and the Linux runtime PM framework (`pm_runtime_get/put`, autosuspend). Linux `SET_POWER` implementation is asynchronous (fire-and-forget) per protocol.
- Windows: uses WDF power callbacks (EvtDeviceD0Entry/EvtDeviceD0Exit) and driver-level state machines. Windows `SET_POWER` implementation is asynchronous with a flag-gated filter: the driver sets `bAwaitingSendSetPowerOnResponse = true` before sending SET_POWER(ON), and the response handler clears the flag. Subsequent operations check this flag before proceeding. This is NOT a synchronous wait — it is an async flag-gated filter pattern.

- Validation points:
  - Verify that Linux sequences rely on asynchronous `SET_POWER` semantics where appropriate and that the driver does not assume synchronous device acknowledgment.
  - Verify Windows drivers use proper synchronization (flag-gated waits) where the driver expects device-side acknowledgements.

## See Also
- **[linux.md](linux.md)** — Linux kernel PM implementation (LTR defaults, runtime suspend, hibernate callbacks, PM callback table)
- **[windows.md](windows.md)** — Windows PM implementation (LTR clamping, D0Exit flows, HIDSPI/HIDI2C differences, idle notification)
- **`fv-thc/registers`** — Register restore order for D3 save/restore, power domain assignments
- **`fv-thc/platform`** — Per-platform PMC addresses, BIOS power prerequisites
- **`fv-thc/debug`** — Power-related failure triage, known PM sightings
- **`fv-thc/dma`** — DMA interaction with power states, LTR during DMA
- **`fv-thc/driver`** — Driver PM implementation (Windows DPC, Linux PM callbacks)
- **`fv-thc/hidspi`** — SPI power states, QuickSPI PM callbacks, auto-suspend configuration
- **`fv-thc/hidi2c`** — I2C power states, QuickI2C PM callbacks, D3 save/restore of I2C regs
- **`fv-thc/wot`** — Wake-on-Touch architecture (GPIO IP/vGPIO wake path, NOT THC UGD), driver-side WoT config, entry/exit flows, WoG (Not POR), platform-specific WoT enablement
- **`fv-thc/simics`** — Simics S0ix PM enabling, Chassis PM framework emulation, PMCLite sideband in pre-silicon
- **Delegate**: `FV-PM-SOUTH` agent for PMC/south complex power debug
- **Reference**: `fv-thc/docs/thc_known_issues.md` — Chassis 2.2 compliance bug (HSDES 16014286225)
- **Reference**: `fv-thc/docs/thc_bwg_extraction.md` — Full BWG reference document
