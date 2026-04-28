---
name: fv-thc/wot
description: THC Wake-on-Touch (WoT) — corrected architecture (GPIO IP / vGPIO wake path), WoG (Not POR / ISH-based), Linux/Windows implementation, platform config, validation, debug
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Wake-on-Touch (WoT) Reference

Comprehensive Wake-on-Touch documentation covering the **corrected** wake architecture (GPIO IP-based, not THC IP-based), WoG status (Not POR), hardware configuration, entry/exit flows, driver implementations, platform-specific details, validation test points, and debug/triage procedures.

> **ARCHITECTURE CORRECTION (2026-03-06)**: Prior versions of this skill incorrectly attributed WoT wake capability to THC IP hardware (UGD domain signaling PMC). The truth is:
> - **WoT wake comes from GPIO IP (vGPIO)**, NOT from THC IP
> - **THC PCI capabilities: WAKE = No, PME = No** — THC cannot generate platform wake signals
> - **THC's role is driver-side only**: register GPIO as wake source, control device power state, restore hardware after resume
> - **WoG (Wake on Gesture) = Not POR** — many open issues remain (HAS Section 10)

---

## 1. WoT Architecture Overview

### CRITICAL: Where Wake Actually Comes From

THC IP does **NOT** generate platform wake signals. The HAS explicitly states:

| PCI Capability | Value | Implication |
|---------------|-------|-------------|
| **WAKE** | **No** | THC cannot generate wake signals |
| **PME** | **No** | THC cannot generate PME# assertions |

The actual WoT wake path **bypasses THC entirely**:

```
Touch Device  ──GPIO pin──>  GPIO Pad (GPIO IP)  ──vGPIO──>  PMC  ──>  Platform Wake
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                             This is GPIO IP territory, NOT THC IP
```

THC's role is **purely software/driver-side**:
1. **During probe**: Register the touch device's GPIO as a wake source (via ACPI + PM subsystem)
2. **During suspend**: Decide whether to keep device awake (skip SET_POWER SLEEP) or arm for wake
3. **During resume**: Re-initialize THC hardware (registers, DMA, interrupts) after platform wakes

### WoT vs WoG Terminology

| Term | Full Name | Status | Mechanism |
|------|-----------|--------|-----------|
| **WoT** | Wake-on-Touch | **Implemented** (Linux 6.17+, Windows) | GPIO interrupt from touch device → GPIO IP → vGPIO → PMC → platform wake |
| **WoG** | Wake-on-Gesture | **NOT POR** (HAS: "many open issues remain") | ISH-based gesture matching; CPU stays in C10, no DRAM access. TSEQ_CNTRL.EWOG bit exists in HW but feature is not validated |

> **WoG ≠ WoT**: WoG is an advanced feature where gesture recognition happens in ISH without waking the CPU. WoT is simple: any touch triggers a full platform wake via GPIO interrupt.

### THC Power Domains — Corrected WoT Role

| Domain | Name | Description | WoT Role (CORRECTED) |
|--------|------|-------------|----------------------|
| **THC_PGD** | Power-Gateable Domain | Main THC logic (DMA, protocol engines, registers) | Gated during D0i2/D3. Contains SWGPIO_INT bit (needs save/restore) |
| **THC_UGD** | Un-gated Domain | Always-on logic for **runtime** interrupt routing | Handles **D0i2 runtime interrupt** (THC still powered, clock-gated). Does **NOT** route platform wake signals to PMC |

> **Prior error**: The skill previously stated "UGD wake logic signals PMC to initiate wake." This is **WRONG**. UGD handles runtime interrupt routing for D0i2 (where THC is still in a powered state). Platform wake from D3/Sx comes through GPIO IP, not THC UGD.

### Isolation Gates

- **Isolation required**: PGD → UGD direction (prevents glitches from powered-down domain reaching always-on logic)
- **Isolation NOT required**: UGD → PGD direction (UGD signals can safely drive into PGD)
- 10-bit `thc_res_own_req/ack` for Chassis 2.2 Sleep States

### D0i2 "Wake" vs Platform Wake — Key Distinction

| Wake Type | Power State | THC State | Wake Source | THC Involvement |
|-----------|------------|-----------|-------------|-----------------|
| **D0i2 runtime wake** | D0i2 (sub-state of D0) | Clock-gated, power ON | Touch device interrupt → UGD routing | **Yes** — UGD routes interrupt, THC wakes from clock-gating |
| **D3/Sx platform wake** | D3Hot, D3Cold, S0ix, S3/S4 | Power OFF (PGD gated, possibly Vnn removed) | Touch device GPIO → GPIO IP → vGPIO → PMC | **No** — GPIO IP handles wake; THC is powered off |

### BWG Wake Constraints (Authoritative)

From the BIOS Writer Guide (BWG):

| State | Touch Device Wake | Notes |
|-------|-------------------|-------|
| **D0i2** | **Supported** | Touch interrupt wakes THC from D0i2 (runtime interrupt via UGD) |
| **D3** | **Only SW wake** | No touch device wake from D3. Touch device power is removed. |
| **Connected Standby** | **Requires D0i2** | If touch wake required during connected standby, THC **must remain in D0i2, not D3** |

> **Implication**: For "WoT from D3" (as claimed by prior skill versions), the wake doesn't come from THC — it comes from the touch device's GPIO pin remaining connected through GPIO IP pads that stay powered in the always-on power well. The touch device itself must be on a separate power rail that remains active.

### WoG Architecture (Not POR — For Reference Only)

WoG was designed to allow gesture-based wake from S0ix/connected standby. The architecture:

```
Touch Device  ──SPI/I2C──>  THC (EWOG mode)  ──>  ISH (gesture matching)
                                                        │
                                                   Match found?
                                                   Yes ──> PMC ──> Platform Wake
                                                   No  ──> Discard, CPU stays in C10
```

**Key WoG requirements** (all NOT POR):
- CPU must stay in C10 with **no DRAM access** during WoG processing
- Gesture matching must occur in **ISH** (not host CPU or EU kernels)
- THC cannot send data to DRAM during WoG (would wake CPU package)
- SW sets `TSEQ_CNTRL_1.EWOG` bit; Read DMA Start bit stays 0
- Softstraps: `THC_TSI_WAKE_ON_GEST_EN` and `THC_SPI_WAKE_ON_GEST_EN` (default: 0)

### WoT Variants (Architecture)

| Variant | Description | Implementation Status |
|---------|-------------|----------------------|
| **Single-stage GPIO WoT** | Dedicated GPIO interrupt wakes system via GPIO IP → PMC | **Implemented** (Linux + Windows) |
| **Two-stage WoT** | Referenced in HAS/docs | **NO implementation** in Linux kernel (v6.17-6.20) or confirmed in Windows |
| **ULP (Ultra-Low-Power) WoT** | Referenced in HAS/docs | **NO implementation** exists |
| **WoG (ISH-based gesture)** | ISH performs gesture matching without waking CPU | **NOT POR** — many open issues |

> **Warning**: Only single-stage GPIO-based WoT is implemented. Do NOT test two-stage, ULP WoT, or WoG variants without confirming driver/FW support exists.

---

## 2. WoT Hardware Configuration

### What THC Hardware Does (and Does NOT Do) for WoT

**THC hardware does NOT**:
- Generate wake signals to PMC (WAKE=No, PME=No)
- Route touch GPIO interrupts to PMC for platform wake
- Contain always-on wake detection logic for D3/Sx wake

**THC hardware DOES contain** (but WoG is Not POR):
- `TSEQ_CNTRL_1.EWOG` (bit 5) — Enable Write on GPIO; used by Windows HIDSPI driver
- `TSEQ_CNTRL_1.RWOGC` (bit 6) — Read Write on GPIO Clear
- `TSEQ_CNTRL_1.INT_EDG_DET_EN` (bit 31) — Edge detection enable
- `SWGPIO_INT` (bit 4 of INT_CAUSE) — vGPIO SW interrupt; **PGD domain** (needs save/restore)

### ACPI _DSM Configuration

THC drivers use ACPI DSM to fetch platform-specific WoT properties:

- **Linux**: `quickspi_acpi_get_properties()` / `quicki2c_acpi_get_properties()` parse DSM returns
- **Windows**: `Acpi.cpp` helpers (`AcpiGetDeviceProperties()`) parse DSM returns for WoT configuration

### GPIO Interrupt Configuration (GPIO IP, NOT THC)

WoT uses a **dedicated GPIO** managed by GPIO IP, separate from the main touch data interrupt:

| Aspect | Main Touch Interrupt | WoT Wake Interrupt |
|--------|---------------------|-------------------|
| **Purpose** | Touch data/report delivery during D0 | Wake system from low-power state |
| **Managed by** | THC IP (interrupt controller) | **GPIO IP** (vGPIO → PMC) |
| **Power domain** | THC PGD (lost during power gate) | **GPIO IP always-on power well** |
| **ACPI key** | (standard interrupt resource) | `"wake-on-touch"` |
| **THC involvement** | Full (DMA, interrupt routing) | **None** (GPIO IP → PMC path) |
| **Required for touch** | Yes | No (graceful degradation) |

### vGPIO Architecture (MTL+)

From HAS/EDS: On MTL and forward, a virtual GPIO based SW interrupt is added as an output signal on THC top level, connected to an input vGPIO at SoC level.

| Register | Bit | Field | Domain | Description |
|----------|-----|-------|--------|-------------|
| INT_CAUSE | 4 | `SWGPIO_INT` | **PGD** | SW-controlled vGPIO interrupt. Driver toggles this bit; THC just provides the output signal. Must be in save/restore list. |

> **vGPIO is INTO THC (as interrupt source), not FROM THC (as wake signal)**. The `pmc_THC_wake` signal documented in HAS is a PMC input for waking THC from IP-inaccessible state, not THC signaling PMC.

### vGPIO Pad Locking (PADCFGLOCK) — CRITICAL for WoT

The vGPIO pad used for THC WoT must be **unlocked** in BIOS for the OS driver to control it. If the pad is locked, WoT will silently fail.

| Register | Required Value | Effect |
|----------|---------------|--------|
| `PADCFGLOCK_VGPIO_THC0` | `0x0` (unlocked) | Allows Host SW/OS driver to control vGPIO_THC0 pad for WoT |
| `PADCFGLOCKTX_VGPIO_THC0` | `0x1` or `0x0` | TX lock does not impact WoT currently |

**BIOS "Force unlock on all GPIO pads" interaction**:
- When `Force unlock = Disable` (default on some platforms), BIOS may lock the vGPIO_THC pad
- **NVL**: Affected — PADCFGLOCK_VGPIO_THC0 was locked when "Force unlock" disabled (HSD 15018635096)
- **PTL**: NOT affected — PADCFGLOCK_VGPIO_THC0 stays 0x0 regardless of "Force unlock" setting
- **WCL**: Affected — fixed in BIOS via HSD 16028429994

> **Debug tip**: If WoT fails on a new platform, check `PADCFGLOCK_VGPIO_THC0` FIRST. Use GPIOConfig.exe or PySV to read the pad lock status. A locked pad is the #1 root cause of vGPIO WoT failures.

### BIOS WoT Knob

**Path**: `BIOS Menu → Intel Advanced Menu → PCH-IO Configuration → THC Configuration → Wake on Touch → <Enabled>`

| Setting | Default | Effect |
|---------|---------|--------|
| Wake on Touch | **Disabled** | Controls whether ACPI tables include the WoT GPIO resource |

---

## 3. WoT Entry Flow (Sleep → WoT Armed)

### Pre-conditions

1. WoT GPIO must be present in ACPI tables (Linux: `"wake-on-touch"` GPIO resource)
2. Device must be marked as wakeup source (`device_init_wakeup(dev, true)`)
3. Dedicated wake IRQ must be registered (`dev_pm_set_dedicated_wake_irq()`)
4. BIOS WoT knob must be enabled (`Wake on Touch: Enabled`)
5. **Windows**: WoT Extension INF must be installed (see Section 6)

### Linux Entry Flows

> See **`linux.md`** for detailed Linux HIDI2C and HIDSPI WoT entry flows.
> Key: HIDI2C **skips** `SET_POWER(SLEEP)` when `device_may_wakeup()` is true.
> HIDSPI has **NO WoT handling** — always sends `SET_POWER(SLEEP)`.
> Wake IRQ managed by PM core via GPIO IP, NOT by THC hardware.

### Windows Entry Flows

> See **`windows.md`** for detailed Windows HIDSPI and HIDI2C WoT entry flows.
> Key: HIDSPI sets `EWOG` bit + `ARM_FOR_WAKE` TIC state. HIDI2C uses WDF D0Exit callbacks.
> Both explicitly disable D3Cold (`ExcludeD3Cold = WdfTrue`).

### Register Save (D3Cold — 28 registers)

During D3Cold entry, 28 registers are manually saved by the driver. HIDI2C note: I2C APB SubIP registers are NOT included in the 28-register save set and must be saved/reprogrammed separately.

### DMA Quiesce Sequence

1. Set `THC_DEVINT_QUIESCE_EN = 1`
2. Poll `HW_STS` until confirmed
3. Perform DMA/power operation
4. (Quiesce remains until exit flow clears it)

> **Known PTL bug**: Quiesce fails during continuous touch (HSDES 16023244313). Workaround: 300us delay before + 700us delay after quiesce.

### PMCLite Sideband Messages (Entry)

| Message Code | Meaning |
|-------------|---------|
| `0x8086D301` | D3 entry |
| `0x8086D302` | D3Hot entry |
| `0x8086D303` | D3Cold entry |
| `0x80860200` | Save Complete |
| `0x80860301` | PG Entry |
| `0x8086D201` | D0i2 Entry |

---

## 4. WoT Exit Flow (Touch → Wake)

### Wake Signal Path (CORRECTED)

When a touch occurs while the system is in a low-power state, the wake signal does **NOT** go through THC:

```
Touch Device asserts GPIO  ──>  GPIO Pad (GPIO IP, always-on power well)
                                    │
                                    v
                               vGPIO routing (GPIO IP)
                                    │
                                    v
                               PMC receives wake signal
                                    │
                                    v
                               Power ungating sequence:
                               1. Restore Vnn (if D3Cold)
                               2. De-isolate PGD from UGD
                               3. Restore clocks to THC
                                    │
                                    v
                               OS PM core invokes driver resume callback
                                    │
                                    v
                               THC driver: register restore → DMA init → touch operational
```

> **Key correction**: THC IP is a **passive recipient** of the wake. GPIO IP detects the touch interrupt, signals PMC, PMC restores power to THC, and then the OS driver re-initializes THC. THC never "signals" PMC for wake.

### D0i2 Runtime Wake (Different Mechanism)

D0i2 "wake" is fundamentally different from platform wake:

```
Touch Device asserts GPIO  ──>  THC UGD interrupt routing (THC still powered!)
                                    │
                                    v
                               THC exits clock-gating
                               (PGD clocks restored, no register restore needed)
                                    │
                                    v
                               THC processes touch data normally
```

> D0i2 wake uses THC UGD because THC is still powered (just clock-gated). This is a **runtime interrupt**, not a platform wake.

### GPIO IP Wake Controller Architecture (pinctrl-intel)

The platform wake path for WoT is managed entirely by the Intel GPIO pinctrl driver (`drivers/pinctrl/intel/pinctrl-intel.c`). Understanding this architecture is essential for WoT debug.

**Key functions in pinctrl-intel.c**:

| Function | Role in WoT |
|----------|-------------|
| `intel_gpio_irq_wake()` | Calls `enable_irq_wake(pctrl->irq)` / `disable_irq_wake(pctrl->irq)` on the parent IRQ controller |
| `intel_pinctrl_suspend_noirq()` | Saves ALL pad configs: `padcfg0/1/2` + `HOSTSW_OWN` + `GPI_IE` + `GPI_GPE_EN` |
| `intel_pinctrl_resume_noirq()` | Restores ALL saved pad configs (critical for WoT GPIO surviving Sx transitions) |

**Key design properties**:
- `IRQCHIP_MASK_ON_SUSPEND` flag — GPIO IRQs are masked during suspend. The wake path uses GPE (General Purpose Event), not the normal IRQ path.
- ACPI-mode pins: "usable as GPIO but cannot be used as IRQ because GPI_IS status bit will not be updated" — WoT GPIO must be in **GPIO mode**, not ACPI mode.
- Pad config save/restore ensures the WoT GPIO configuration survives D3Cold/Sx power loss.

**IO APIC vs GPIO mode for wake**:
- GPIO mode (direct): GPIO controller handles interrupt → works reliably for WoT
- IO APIC mode (routed): GPIO → ITSS → IO APIC → CPU core → has known issues on WCL (HSD 16029769688)
- WoT should use GPIO mode wake, not IO APIC routed interrupts

### S4 (Hibernate) vs S5 (Cold Boot) vGPIO WoT Pad Delta — CRITICAL

There is a **significant architectural delta** in how the vGPIO WoT pad is initialized during S5 (cold boot) vs S4 (hibernate resume). This delta is the root cause of **HSD 15019129309** — system cannot enter hibernate on 2nd cycle with WoT enabled on NVL.

#### The Two Boot Paths

| Phase | S5 → Boot (Cold Boot) | S4 → Resume (Hibernate) |
|-------|----------------------|------------------------|
| **Power state** | Full power loss | Full power loss (same as S5 electrically) |
| **BIOS init** | Full boot: configures vGPIO_THC pad, may apply PADCFGLOCK | Full boot: configures vGPIO_THC pad, may apply PADCFGLOCK |
| **Kernel boot** | Fresh kernel load | Fresh kernel load (finds hibernate image) |
| **Kernel state** | Clean state — no prior driver state | **Restores hibernated kernel image** (all driver state from before hibernate) |
| **pinctrl resume** | N/A — fresh `probe()` configures pads | `intel_pinctrl_resume_noirq()` — attempts to **restore saved pad config** from hibernate image |
| **THC driver** | `probe()` → `thc_wot_config()` called fresh | `restore()` callback — full HW re-init, but `thc_wot_config()` is **NOT re-called** |
| **WoT IRQ** | Freshly requested from ACPI GPIO | **Restored from hibernate image** — IRQ registration persists |
| **PADCFGLOCK risk** | Low — driver configures pad after BIOS | **HIGH** — BIOS may lock pad before pinctrl restore runs |

#### Investigation: Pad Reset Type & Interrupt Routing (Not Yet Confirmed)

Multiple hypotheses are under investigation. The initial focus was on **GPIO pad reset type**, but the HostDeepReset patch did NOT resolve the issue (BIOS 3080.24). Current investigation has shifted to **interrupt routing mode** (APIC vs SCI/GPE) and **Linux pinctrl driver behavior on NVL**.

**Hypothesis 1 — Pad Reset Type** (attempted, did NOT fix):

| Reset Type | Behavior on S-State Resume | WoT Impact |
|-----------|---------------------------|------------|
| `GpioV2ResetHost` (Host Reset) | Does **NOT** clear pad interrupt latch on S-state resume | Interrupt latch may stay asserted after S4 resume |
| `GpioV2ResetHostDeep` (HostDeepReset) | **Clears** pad interrupt latch on S-state resume | Expected to give clean pad state — but BIOS patch with this did NOT resolve the issue |

**Hypothesis 2 — Interrupt Routing Mode** (current focus, BIOS 3100):
- vGPIO_THC pad was configured for **IO APIC interrupt routing** (`GPIROUTIOXAPIC=1`)
- After S4 resume, pad generates IRQ (not SCI/GPE) → OS does not recognize it as a valid ACPI wake source
- BIOS 3100 test: switched pad to **SCI/GPE mode** (`GPIRoutSCI=1`, `HOSTSW_OWN=0`), added ACPI `_PRW` (GPE 0x6F) + `_DSW`, changed level→edge triggered

**Hypothesis 3 — Linux pinctrl driver** (fengxu, Mar 6):
- *"Linux GPIO driver doesn't handle Pin configure during sleep correctly on NVL platform, as previous platforms haven't this issue"*
- NVL may have a platform-specific pinctrl behavior delta vs LNL/PTL/WCL

On **NVL**, the observed symptoms after 1st S4 resume are:

1. **1st S4 entry/resume**: Works — pad state is clean from initial boot
2. **After 1st S4 resume**: `PAD_CFG_DW0` of `VGPIO_THC0` has `RXINV` and `GPIROUTIOXAPIC` bits not properly restored
3. **Interrupt latch stays asserted** → WoT GPIO fires spurious interrupts continuously (interrupt count increases without touch)
4. **2nd S4 entry**: `pm_wakeup_pending` is already set from spurious interrupts → kernel aborts hibernate with `"Wakeup pending. Abort CPU freeze"`

#### pinctrl-intel Suspend/Resume Mechanics

The `pinctrl-intel.c` driver uses `NOIRQ_SYSTEM_SLEEP_PM_OPS` — **same suspend/resume code for ALL sleep states** (S3, S4, S5):

**`intel_pinctrl_suspend_noirq()`** (freeze/poweroff phase of S4):
- Iterates all pins tracked by kernel (`intel_pinctrl_should_save()`)
- Saves `padcfg0`, `padcfg1`, `padcfg2`, `HOSTSW_OWN`, `GPI_IE` for each pin
- vGPIO_THC pad IS saved (it's registered as IRQ by `thc_wot_config()`)

**`intel_pinctrl_resume_noirq()`** (restore phase of S4):
- Calls `intel_restore_padcfg()` for each saved pin — **read-modify-write**
- **⚠️ If `PADCFGLOCK` is set by BIOS during boot, the write silently fails**
- Even if not locked, the restore happens AFTER BIOS has already configured the pad with `GpioV2ResetHost` — the reset type is a BIOS-owned field

**`intel_pinctrl_should_save()`** criteria:
- Pin is owned by kernel (`mux_owner` or `gpio_owner`)
- OR `gpiochip_line_is_irq()` returns true (WoT GPIO: yes, registered by `thc_wot_config()`)
- OR pin is in direct IRQ mode

#### Why S5 Works but S4 Fails (2nd Cycle)

```
S5 (Cold Boot):
  BIOS configures vGPIO_THC (pad reset type = HostReset)
  → Kernel boots fresh
  → THC probe() → thc_wot_config() → requests GPIO IRQ fresh
  → pinctrl configures pad from ACPI (clean state)
  → WoT works ✓

S4 Cycle 1 (1st Hibernate):
  freeze: pinctrl saves pad config (RXINV, GPIROUTIOXAPIC, etc.)
  poweroff: THC driver sends SET_POWER(SLEEP), enters D3
  [Power cut — same as S5 electrically]
  BIOS boot: configures vGPIO_THC (HostReset — does NOT clear interrupt latch)
  Kernel boot: finds hibernate image, restores kernel state
  pinctrl resume: restores saved pad config → works (pad was clean)
  THC restore: full re-init (i2c_subip_init or spi_configure)
  → WoT works ✓ (pad state was clean from initial boot)

S4 Cycle 2 (2nd Hibernate attempt):
  freeze: pinctrl saves pad config (NOW has stale RXINV/GPIROUTIOXAPIC from cycle 1 resume)
  → "Wakeup pending. Abort CPU freeze" — spurious interrupts from stale pad state
  → Hibernate ABORTED ✗
```

#### PythonSV Debug Commands (NVL)

```python
# Read vGPIO_THC0 pad config across transitions
pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show()

# Key bits to check in PAD_CFG_DW0:
#   RXINV (bit 23)      — RX inversion, should match initial config
#   GPIROUTIOXAPIC (bit 20) — IO APIC routing, should be 0 for GPIO mode WoT
#   GPIROUTSCI (bit 19)  — SCI routing for wake
#   RXEVCFG (bits 26:25) — RX event config
#   PMODE (bits 12:10)   — Pad mode

# Compare these 4 states:
#   #1: WoT disabled (baseline)
#   #2: WoT enabled, before any S4
#   #3: Before S4 entry (after WoT armed)
#   #4: After S4 resume (check for stale bits)
```

#### Investigation Status & Fix Attempts

**⚠️ No confirmed root cause or fix as of March 2026. Multiple hypotheses under active investigation.**

**Attempt 1**: BIOS 3080.24 — Set vGPIO_THC pad reset type to `GpioV2ResetHostDeep` → **Did NOT fix** (bug still reproduced; build also caused RVP hang due to PCODE compatibility)

**Attempt 2**: BIOS 3100 — Switched vGPIO_THC pad from IO APIC interrupt to **SCI/GPE mode** (`GPIRoutSCI=1`, `GPI_GPE_EN=1`, `HOSTSW_OWN=0`), added ACPI `_PRW` (GPE 0x6F) + `_DSW`, changed level→edge triggered → **Under test** (had PCODE compatibility issue, required IFWI 2026.09.4.01)

**Latest direction** (fengxu, Mar 6): Linux GPIO pinctrl driver may not handle NVL pad config correctly during sleep — escalated to Linux GPIO driver owner (Saranya Gopal).

**Platform scope**:
- **NVL**: Affected (HSD 15019129309 — OPEN)
- **LNL/PTL/WCL**: NOT affected per sighting comments (different pad reset type or pad config)
- **Windows**: NOT affected (WoT Extension INF not ready for NVL QuickI2C; Windows QuickSPI may have different pad handling)

#### Known Firmware Bug (Upstream)

Linux `pinctrl-intel.c` has a known firmware interaction bug (kernel bugzilla 214749): "firmwares that don't restore pin settings correctly after suspend, Rx value becomes inverted." The THC vGPIO S4 issue may be a manifestation of this broader class of pad config restore failures.

### Register Restore (After Platform Wake)

**Linux QuickSPI resume**:
```
1. pci_set_power_state(D0)
2. pci_restore_state()
3. pci_enable_device()
4. thc_port_select()           — re-select HIDSPI port type
5. thc_spi_configure()         — re-init SPI (clock, IO mode, opcodes)
6. thc_dma_init() + thc_dma_configure()
7. thc_interrupt_config()
8. thc_ltr_config()
9. quickspi_set_power(ON)
10. hid_driver_resume()
```

**Linux QuickI2C resume**:
```
1. pci_set_power_state(D0)
2. pci_restore_state()
3. pci_enable_device()
4. thc_dma_configure()
5. i2c_subip_regs_restore()   — simple register write-back (15-register array)
6. interrupt_enable()
7. unquiesce()
8. SET_POWER(ON)
9. hid_driver_resume()
```

> **Key**: I2C resume uses simple `i2c_subip_regs_restore()` (register write-back), not full `i2c_subip_init()`. Only hibernate `restore` uses the full 11-step init sequence.

### DMA Re-enable

After register restore, DMA engines are re-initialized:
- PRD ring pointers reset
- DMA control registers reprogrammed
- Interrupt configuration restored
- `THC_DEVINT_QUIESCE_EN` cleared to allow interrupt delivery

### PMCLite Sideband Messages (Exit)

| Message Code | Meaning |
|-------------|---------|
| `0x8086D000` | D0 (active) |
| `0x80860201` | Restore Complete |
| `0x80860302` | PG Exit |
| `0x8086D200` | D0i2 Exit |

---

## 5. Linux Driver Implementation

> **Full details**: See **`linux.md`** — covers `intel-thc-wot.c` source analysis (writes ZERO
> THC registers), `thc_wot_config()`/`thc_wot_unconfig()`, data structures, PM callbacks
> (HIDI2C WoT-aware vs HIDSPI no WoT handling), QuickI2C/QuickSPI integration points,
> pinctrl-intel wake architecture, S4 hibernate investigation (HSD 15019129309),
> kernel version feature matrix.

---

## 6. Windows Driver Implementation

> **Full details**: See **`windows.md`** — covers Extension INF requirements, EWOG bit usage,
> TIC ARM_FOR_WAKE state, D3Cold explicitly disabled, SwAS WoT entry/exit flows,
> WDF power callbacks, TIC power state enum, key Windows vs Linux differences.
---

## 7. Platform-Specific WoT Configuration

### GPIO Reset Pins Per Platform

These are the device RESET GPIOs (not the WoT wake GPIOs — WoT wake GPIOs are separate ACPI resources managed by GPIO IP):

| Platform | THC0 Reset GPIO | THC1 Reset GPIO |
|----------|----------------|----------------|
| MTL-S | `gpp_e_19` | `gpp_d_22` |
| MTL-P | `xxgpp_e_6` | `xxgpp_f_16` |
| LNL-M | `xxgpp_e_16` | `xxgpp_f_16` |
| PTL | `xxgpp_e_16` | `xxgpp_f_16` |
| NVL | `xxgpp_e_16` | `xxgpp_f_16` |

> **Note**: WoT wake GPIOs are defined in ACPI tables as separate GpioInt resources with the `"wake-on-touch"` key. They are managed by GPIO IP, NOT by THC. A platform may have a reset GPIO but no WoT GPIO.

### BIOS Prerequisites for WoT

1. **WoT BIOS knob**: `Wake on Touch: Enabled` (BIOS Menu → Intel Advanced Menu → PCH-IO Configuration → THC Configuration)
2. **ACPI WoT GPIO**: Platform ACPI tables must define the `"wake-on-touch"` GpioInt resource (GPIO IP pad)
3. **THC enabled**: THC port must be enabled (THC1 requires THC0 enabled on PTL/NVL)
4. **Power gating**: `HAE` (bit 5) and `D3HE` (bit 2) in `THC_CFG_PCE` must be enabled
5. **LTR**: Properly configured before D0i2/D3 entry
6. **Windows**: WoT Extension INF installed and system restarted

### Platform-Specific WoT Behavior (CORRECTED)

| Platform | WoT from D0i2 | WoT from D3 | WoT from S0ix | Mechanism |
|----------|---------------|-------------|---------------|-----------|
| **BWG-era (TGP)** | **Yes** | **No** (BWG: "only SW wake from D3") | **No** | D0i2: UGD runtime interrupt. D3: no touch wake. |
| **LNL+** | **Yes** | **Possible** (if touch device GPIO stays powered) | **No** | D0i2: UGD runtime interrupt. D3: GPIO IP → vGPIO → PMC (requires touch device on always-on power rail) |
| **PTL+** | **Yes** | **Possible** (platform-dependent) | **No** | Same as LNL; verify GPIO pad power well assignment |
| **NVL** | **Yes** | **Possible** (platform-dependent) | **No** | Same as LNL; verify GPIO pad power well assignment |

> **S0ix**: THC does **NOT** generate wakes from S0ix on any platform.
>
> **D3 WoT clarification**: "WoT from D3" requires the touch device's GPIO pin to be on an always-on power well that stays powered during D3. The wake path goes through GPIO IP → vGPIO → PMC, bypassing THC entirely. Whether this works is a **platform power design decision**, not a THC IP capability.

### PMCLite Port IDs

| Platform | THC0 PortID | THC1 PortID |
|----------|-------------|-------------|
| PTL | `0xF26E` | `0xF26F` |
| NVL | `0xFC6E` | `0xFC6F` |

### NVL-Specific WoT Notes

- THC1 BDF changed to `B:0 D:8 F:0` (was D:16 F:1 on all prior platforms)
- QuickI2C Non-POR from NVL+ (HSD#16028137599) — affects WoT testing on I2C path
- **No NVL I2C PCI Device IDs in Linux kernel** — NVL/ARL/RZL/TTL only have SPI Device IDs registered
- BIOS prerequisites: Disable I2C4, I2C5, SPI, I3C, ISH; LTR = `0xFFFFFFFF`; IFWI >= ww50.1.01

### QuickI2C PCI Device IDs (WoT-Relevant Platforms)

Only platforms with registered I2C Device IDs support QuickI2C WoT on Linux:

| Platform | Port 1 | Port 2 | Driver Data | WoT Support |
|----------|--------|--------|-------------|-------------|
| LNL | `0xA848` | `0xA84A` | NULL (no advanced features) | Basic WoT |
| PTL-H (PTL-H4Xe, PCD-H) | `0xE348` | `0xE34A` | `ptl_ddata` (detect_size=255, int_delay=256) | Full WoT |
| PTL-U & PTL-P (PTL-H12Xe, PCD-P) | `0xE448` | `0xE44A` | `ptl_ddata` | Full WoT |
| WCL | `0x4D48` | `0x4D4A` | `ptl_ddata` | Full WoT |
| NVL (PCD-H) | `0xD348` | `0xD34A` | **Not in kernel yet** — Co-De Sign verified DIDs | Pending kernel support |
| ARL | — | — | **No I2C IDs registered** | SPI only |
| RZL | `0x6C48` | `0x6C4A` | **Not in kernel yet** — Co-De Sign verified DIDs | Pending kernel support |
| TTL | `0x9334` | `0x9339` | **Not in kernel yet** — Co-De Sign verified DIDs ⚠️ Non-standard pattern | Pending kernel support |

> **Note**: `ptl_ddata` enables: `max_rx_detect_size = 255` (vs default), `max_rx_interrupt_delay = 256`.
> LNL uses NULL ddata (no detect size/interrupt delay overrides).
> `DEFAULT_AUTO_SUSPEND_DELAY_MS = 5000` (5 seconds) for all QuickI2C runtime PM.

- **HSD 15018635096**: THC WoT via vGPIO Failed (Force unlock=Disable) — **root_caused**, comp=bios
  - **Root cause**: BIOS "Force unlock on all GPIO pads" = Disable locked the vGPIO_THC pad
  - `PADCFGLOCK_VGPIO_THC0 = 0x0` (unlocked) required for WoT — was locked when "Force unlock" disabled
  - `PADCFGLOCKTX_VGPIO_THC0` remained `0x1` (not impacting WoT currently)
  - **Fix**: BIOS NovaLake_2460_22 ported WCL fix (HSD 16028429994)
  - **Verification**: With fix applied, THC enters D3, clean Saleae waveform, WoT+S0ix PASSED
  - **Note**: HSD 15018631846 (same issue, rejected) was superseded by this sighting

- **HSD 15018635096 debug methodology** (reference for future vGPIO WoT triage):
  1. Check `PADCFGLOCK_VGPIO_THC0` via GPIOConfig.exe or PySV
  2. If locked (≠ 0x0): BIOS issue — check "Force unlock" setting
  3. If unlocked: Check vGPIO pad config (mode, direction, interrupt enable)
  4. Capture Saleae trace on touch GPIO during WoT attempt
  5. Compare PMC power gate status before/after touch

### WCL-Specific WoT Known Issues

- **HSD 16027810168**: Post code stuck at 0x9B0E when enabling WoT in BIOS on WCL platform
- **Impact**: System fails to boot when WoT BIOS knob is enabled
- **Workaround**: Disable WoT in BIOS until BIOS fix available

- **HSD 16029769688**: Wake from touchpad not working after ~10-15 cycles (IO APIC mode) — **OPEN**
  - **Component**: hw.lpss
  - **Two failure signatures** (observed by manishp1):
    - **Signature 1 (6/10 failures)**: RTE84 mask bit stays set after first ITSS→CORE interrupt. OS doesn't unmask after EOI.
    - **Signature 2 (4/10 failures)**: Mask not set but `did`+`edid`=0 → interrupt not routed to any core. Correlated with LNL ISH issue (HSD 15015234406).
  - **FTH trace**: First IO APIC interrupt from `gpp_F_18` (touchpad) processed by ITSS, EOI received, but OS fails to unmask RTE84.
  - **GPIO mode works** — only IO APIC mode affected
  - **Mitigation**: `ForceIdleTimeout` regkey = `0x3` (default `0x7`) → PASS
  - **Promoted to Microsoft**: MTC 22022108803

- **HSD 16028429994**: THC not entering during S0ix — **BIOS bug** (comp=bios.pch)
  - Fix: BIOS unlocks vGPIO_THC pad (PADCFGLOCK_VGPIO_THC0 = 0x0)
  - Ported to NVL BIOS as NovaLake_2460_22

### vGPIO FR (Functional Requirement) for Wake Testing

- **FR 22010872659**: "Wake on attached touch panel from modern standby"
  - 3rd party dependency; no Simics commit
  - Test approach: "On IP FPGA setup, test the VGPIO interrupt state in wake mode. Will need BIOS support to enable the pad in GPIO mode and BIOS expose ACPI interrupt source."

### Kernel Version Feature Matrix (WoT-relevant)

| Kernel | WoT-Related Features |
|--------|---------------------|
| 6.17 | WoT support added, PTL QuickI2C, `INT_EDG_DET_EN` fix (`8fe2cd8`) |
| 6.18 | WCL Device IDs, ACPI config enhancements |
| 6.20 | I2C regs save pointer fix (`a7fc15e`) — **CRITICAL for D3Cold SnR with WoT** |

---

## 8. WoT Validation Test Points

### Test Categories

#### Category 1: WoT Configuration (GPIO IP + PM Subsystem)
- [ ] Verify `thc_wot_config()` succeeds when ACPI `"wake-on-touch"` GPIO present
- [ ] Verify `thc_wot_config()` degrades gracefully (warn, not error) when GPIO absent
- [ ] Verify `device_may_wakeup()` returns true after successful WoT config
- [ ] Verify dedicated wake IRQ registered via `dev_pm_set_dedicated_wake_irq()`
- [ ] Verify `thc_wot_unconfig()` cleans up all WoT state
- [ ] Verify wake IRQ is a GPIO IP interrupt (not THC interrupt)

#### Category 2: WoT from D0i2 (UGD Runtime Interrupt)
- [ ] Touch wakes THC from D0i2 (all platforms) — this is UGD runtime interrupt, NOT platform wake
- [ ] Verify D0i2 entry with WoT armed (check PMCLite `0x8086D201` sent)
- [ ] Verify D0i2 exit on touch (check PMCLite `0x8086D200` sent)
- [ ] Verify touch data resumes correctly after D0i2 wake
- [ ] Verify no register restore needed (state retained in D0i2)

#### Category 3: WoT from D3 (GPIO IP → vGPIO → PMC Path)
- [ ] Touch wakes system from D3Hot (requires touch GPIO on always-on power well)
- [ ] Touch wakes system from D3Cold (requires touch GPIO on always-on power well + 28-reg save/restore)
- [ ] Verify GPIO IP pad stays powered during D3 (check GPIO pad power well assignment)
- [ ] Verify full register restore after D3 wake
- [ ] Verify DMA re-initialization after D3 wake
- [ ] Verify wake path: GPIO IP → vGPIO → PMC → power ungating → driver resume

#### Category 4: WoT with I2C (Primary path)
- [ ] Verify `SET_POWER(SLEEP)` is SKIPPED when `device_may_wakeup()` is true
- [ ] Verify I2C sub-IP registers are saved even with WoT (sub-IP is in PGD)
- [ ] Verify I2C sub-IP registers restored correctly on wake
- [ ] Verify I2C save pointer fix (`a7fc15e`) applied for D3Cold scenarios

#### Category 5: WoT with SPI (Limited)
- [ ] Verify SPI suspend always sends `SET_POWER(SLEEP)` (no WoT handling on Linux)
- [ ] Document WoT behavior expectations for SPI path
- [ ] (Windows) Verify `EWOG` bit set and `ARM_FOR_WAKE` state written
- [ ] (Windows) Verify WoT Extension INF installed (`WoT_QuickSpiExtension.inf`)

#### Category 6: WoT S4 (Hibernate) Stress — CRITICAL
- [ ] S4 hibernate + resume 1 cycle with WoT enabled (baseline)
- [ ] S4 hibernate + resume **2+ cycles** with WoT enabled (**HSD 15019129309 regression**)
- [ ] After S4 resume, verify vGPIO_THC0 `PAD_CFG_DW0` matches pre-S4 config (PySV: `pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show()`)
- [ ] After S4 resume, verify WoT GPIO interrupt count is NOT increasing without touch (`/proc/interrupts`)
- [ ] Verify `RXINV` (bit 23) and `GPIROUTIOXAPIC` (bit 20) in `PAD_CFG_DW0` are correct after S4 resume
- [ ] Check vGPIO_THC0 pad reset type and interrupt routing mode (`GPIROUTIOXAPIC` vs `GPIRoutSCI`) after S4 resume — see HSD 15019129309 (under investigation)
- [ ] S4 with WoT + `SET_POWER(SLEEP)` sent during poweroff (HIDI2C: always sends, HIDSPI: always sends)
- [ ] S4 restore path: verify `i2c_subip_init()` (not `i2c_subip_regs_restore()`) used for full re-init
- [ ] Verify `thc_wot_config()` is NOT re-called on S4 restore (WoT state restored from hibernate image)
- [ ] S4 with WoT on NVL (primary failure platform) vs PTL/WCL (should not be affected)

#### Category 7: WoT Negative Tests
- [ ] Verify no wake from S0ix (THC does NOT generate S0ix wakes)
- [ ] Verify no wake from Sx (S3/S4/S5) via touch (unless GPIO on always-on rail)
- [ ] Verify WoT disabled when BIOS knob disabled (ACPI GPIO resource absent)
- [ ] Verify WoT disabled when ACPI GPIO resource absent
- [ ] Verify system stability with rapid WoT entry/exit cycling
- [ ] Verify WoG (EWOG bit) has no effect when WoG is not POR

#### Category 8: WoT Cross-Platform
- [ ] Test WoT on each supported platform (MTL, LNL, PTL, NVL)
- [ ] Verify platform-specific GPIO IP pad routing for WoT GPIO
- [ ] Test with both THC0 and THC1 independently
- [ ] Test with different BOM devices (WACOM, ELAN, THAT)
- [ ] (WCL) Verify HSD 16027810168 status (post code 0x9B0E when WoT enabled)

#### Category 9: Windows-Specific WoT
- [ ] Verify WoT Extension INF installation and system restart
- [ ] Verify `armForWake` callback received from HidSpiCx
- [ ] Verify TIC state transitions (SENSING → ARM_FOR_WAKE on power-down)
- [ ] Verify sanity: single/double tap wakes from modern standby
- [ ] Verify `powercfg /devicequery wake_armed` shows THC device

### Common Failure Modes and Root Causes (CORRECTED)

| Failure Mode | Likely Root Cause | Debug Action |
|-------------|------------------|--------------|
| WoT never triggers | Missing ACPI `"wake-on-touch"` GPIO resource | Check `dmesg` for `dev_warn` from `thc_wot_config()` |
| WoT never triggers (GPIO present) | GPIO pad not on always-on power well | Check GPIO pad power well assignment in GPIO IP config |
| WoT never triggers (Windows) | WoT Extension INF not installed | Install `WoT_QuickSpiExtension.inf` or `WoT_QuickI2cExtension.inf` |
| WoT triggers but touch data corrupt | Register restore incomplete after D3 | Verify 28-register save/restore, check I2C sub-IP regs |
| WoT works from D0i2 but not D3 | Touch GPIO on power-gateable rail (not always-on) | Verify GPIO pad power well; D3 wake requires always-on GPIO |
| WoT works on I2C but not SPI (Linux) | SPI has no WoT handling | By design — SPI always sends `SET_POWER(SLEEP)` |
| System hangs on WoT exit | Quiesce failure during resume | Check for HSDES 16023244313 (quiesce bug) |
| Device not responding after wake | `SET_POWER(SLEEP)` was sent before WoT | Verify `device_may_wakeup()` returns true in I2C path |
| Post code stuck 0x9B0E (WCL) | WCL BIOS bug with WoT knob | HSD 16027810168 — disable WoT in BIOS until fix |
| **S4 hibernate fails on 2nd cycle** | **Under investigation (HSD 15019129309)** — multiple hypotheses: pad reset type, APIC vs SCI/GPE routing, pinctrl restore failure | **Check `PAD_CFG_DW0` RXINV/GPIROUTIOXAPIC bits after S4 resume via PythonSV. Check `/proc/interrupts` for spurious WoT IRQ. See Section 4.5.** |
| Spurious WoT interrupts after S4 resume | vGPIO pad interrupt latch not cleared or pad misconfigured on S-state resume | Check `/proc/interrupts` for increasing WoT IRQ count without touch. Related to HSD 15019129309 — root cause not yet confirmed. |

---

## 9. WoT Debug & Triage

### Step 1: Verify WoT Armed

**Linux**:
```bash
# Check if device is marked as wakeup source
cat /sys/devices/pci0000:00/<BDF>/power/wakeup
# Should show "enabled" if WoT configured

# Check for WoT config warnings in dmesg
dmesg | grep -i "wake-on-touch"
dmesg | grep -i "thc.*wot\|thc.*wake"

# Verify dedicated wake IRQ (this is a GPIO IP IRQ, not THC)
cat /proc/interrupts | grep THC
```

**Windows**:
```
# Check device wake capability
powercfg /devicequery wake_armed
# THC device should appear if WoT enabled + Extension INF installed

# Check registry workaround flags
reg query "HKLM\SYSTEM\CurrentControlSet\Enum\PCI\<DeviceID>\Device Parameters" /v THC_WORKAROUNDS
```

### Step 2: Verify GPIO IP Configuration (NOT THC)

- Use **GPIOConfig.exe** (CLI/GUI tool) to inspect GPIO pad state
- WoT GPIO is managed by **GPIO IP**, not THC
- Verify WoT GPIO pad is:
  1. Configured for interrupt (not just data)
  2. On an always-on power well (for D3 wake)
  3. Polarity matches device output (active-high vs active-low)
- THC SPI port 0 typically in GPIO Community 4

### Step 3: Common Failure Signatures

| Signature | Diagnosis |
|-----------|-----------|
| `dev_warn: failed to get wake-on-touch GPIO` | ACPI tables missing WoT GPIO resource. Check BIOS WoT knob. |
| `dev_warn: wake-on-touch GPIO not wakeable` | GPIO found but not marked as wakeable in ACPI. BIOS issue. |
| Touch fails after WoT resume, I2C path | I2C sub-IP registers not restored (check `a7fc15e` fix) |
| Touch fails after WoT resume, SPI path | Full SPI reconfiguration needed (port_select + spi_configure) |
| PMC shows THC still in D3 after wake | PMCLite Restore Complete (`0x80860201`) not sent |
| S0ix blocked by THC | Check `pch.pmc.pmu.pg_ip_d3_sts_3` bits thc0_d3_sts(14), thc1_d3_sts(15) |
| Post code 0x9B0E on WCL | HSD 16027810168 — WCL BIOS bug when WoT enabled |

### Step 4: GPIO/Interrupt Debug

```bash
# Linux: Enable dynamic debug for THC module
echo "module intel_thc_hid +p" > /sys/kernel/debug/dynamic_debug/control

# Check interrupt counts before and after WoT
cat /proc/interrupts | grep THC

# Verify PCI power state
lspci -vvv -s <BDF> | grep "Power Management"

# Check GPIO IP pad state (if debugfs available)
cat /sys/kernel/debug/pinctrl/*/pins | grep <WoT_GPIO_pad>
```

### Step 5: PMC Interaction Debug

**PMCLite sideband message verification**:
- Use PySV `tap2sb` or direct sideband read to verify PMCLite messages
- Key messages to verify during WoT:
  - Entry: D3 entry (`0x8086D301/D302/D303`), Save Complete (`0x80860200`), PG Entry (`0x80860301`)
  - Exit: PG Exit (`0x80860302`), Restore Complete (`0x80860201`), D0 (`0x8086D000`)

**PMC power gate status**:
```python
# PySV example: Check THC PG status
import pysvtools.pcdsoc.south as south
pg_sts = south.pmc.pmu.pg_ip_d3_sts_3.read()
thc0_d3 = (pg_sts >> 14) & 1  # bit 14
thc1_d3 = (pg_sts >> 15) & 1  # bit 15
```

**PMC SSRAM Telemetry** (for WoT-related counters):

| Parameter | Value |
|-----------|-------|
| PMC SSRAM Base | `0xFE010000` |
| THC0 Mailbox | `+0xEC0` |
| THC1 Mailbox | `+0xF60` |
| FG_PR_CNTR offset | `+0x00` (foreground power request counter) |
| DEVINT_CNT offset | `+0x0C` (device interrupt count) |

### Step 6: Register Dump Points for WoT Debug

Collect register snapshots at these checkpoints:
1. **Before WoT entry**: Full THC register dump (DMA state, interrupt config, LTR, port control)
2. **After WoT armed**: Verify quiesce state, PCI PM state (D3), GPIO wake config (in GPIO IP, not THC)
3. **On WoT wake**: Verify PCI PM state (D0), register restore completeness
4. **After WoT resume**: Verify DMA active, interrupts enabled, LTR programmed, touch data flowing

### WoT-Related HSDES Sightings

| HSDES ID | Platform | Summary | Status | WoT Relevance |
|----------|----------|---------|--------|---------------|
| **`15018635096`** | **NVL-Hx A1** | **THC WoT via vGPIO Failed (Force unlock=Disable)** | **root_caused** | **#1 reference for vGPIO pad locking debug. PADCFGLOCK_VGPIO_THC0 must be 0x0.** |
| `15018631846` | NVL-Hx A1 | THC WoT via vGPIO Failed (same issue) | rejected | Superseded by 15018635096 |
| **`15019129309`** | **NVL-Hx A1** | **System cannot enter hibernate on 2nd cycle with THC-WOT enable** | **OPEN** | **S4+WoT interaction bug — root cause under investigation. Observations: vGPIO_THC pad RXINV/GPIROUTIOXAPIC bits not restored after S4, spurious IRQs → `pm_wakeup_pending` blocks 2nd S4. Attempted fixes: (1) HostDeepReset — did NOT resolve, (2) SCI/GPE mode + edge trigger + ACPI _PRW — under test. Latest theory: Linux pinctrl driver may not handle NVL pad config correctly during sleep. NVL-only. Linked FW bug: 15019049216. PythonSV: `pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show`** |
| **`16029769688`** | **WCL** | **Wake from touchpad not working after ~10-15 cycles (IO APIC)** | **OPEN** | **IO APIC mode wake failure. Two signatures: RTE84 mask stuck, or did+edid=0. GPIO mode works. Mitigation: ForceIdleTimeout=0x3** |
| **`16028429994`** | **WCL** | **THC not entering during S0ix** | **fixed** | **BIOS fix: unlock vGPIO_THC pad. Ported to NVL as NovaLake_2460_22** |
| `16027810168` | WCL | Post code stuck 0x9B0E when WoT enabled | open | **BLOCKER**: System can't boot with WoT on WCL |
| `15013380739` | MTP-S | THC WoT Not Able to Wake from S0iX | root_caused | comp=bios; BIOS config issue |
| `15013145991` | MTP-S | THC WoT Not Able to Wake from S0iX | rejected | Duplicate of 15013380739 |
| `1504682588` | — | S0ix: Unexpected wake by THC D3 during S0ix entry | complete | THC D3 transition causing unexpected S0ix wake |
| `15012559401` | MTL-P | Low D3 Residency with WoT Enabled | complete | comp=doc.bwg; documentation issue |
| `16026436000` | PTL PCD | System failed S0ix, enable_device_wake:ret=False | rejected | WoT enable failure on PTL |
| `15018720525` | PTL-H | Touchpad can't wake from MS | OPEN | comp=hw.lpss; modern standby wake failure |
| `15017890583` | PTL PCD | GSTATES fail during S4 cycle | rejected | S4 power state issue |
| `15018992269` | NVL | BOM52-I2C S3 resume — RESET GPIO not de-asserted | — | GPIO state after wake |
| `16023244313` | PTL | Quiesce failure during continuous touch | — | Quiesce during WoT entry/exit |
| `a7fc15e` (kernel fix) | All | I2C save pointer arithmetic | — | **CRITICAL** for D3Cold SnR with WoT |
| `8fe2cd8` (kernel fix) | All | INT_EDG_DET_EN fix | — | Prevents duplicate reads affecting WoT interrupt |
| `15018611965` | NVL | THC enabled by default blocks S0i2 | — | Affects WoT from D0i2 |
| `14025560859` | NVL | THC0/1 not PG when disabled | — | Power gating prerequisite for WoT |

### Windows-Specific WoT Debug

**WPP Tracing** (capture driver state during WoT):
```
# HIDSPI
tracelog -start thc -guid #A891081A-80CD-45FC-B1F8-9F4FD8ECC101

# HIDI2C
tracelog -start thc -guid #C47236A7-EEE4-4660-A7A2-349F6BB8E308
```

**ETW Events**:
```
# Structured event telemetry
GUID: {937AD94E-CA8D-4B8E-8143-3FCE4ACCB8CB}
```

**Registry Workarounds** (may affect WoT behavior):
- `THC_WORKAROUNDS` bit 2: `DisableResetOnD0Exit` — may affect WoT exit reset sequence
- `THC_WORKAROUNDS` bit 3: `DisableDoze` — disables D0i2, affects WoT from D0i2

---

## 10. Cross-References

### Related Sub-Skills

| Sub-Skill | WoT-Relevant Content |
|-----------|---------------------|
| **`fv-thc/power`** | Power domains (PGD/UGD), PMCLite messages, D0i2/D3 transitions, PM callback comparison (WoT-aware vs not), wake constraints per power state, BWG wake rules |
| **`fv-thc/driver`** | TIC power state enum (ARM_FOR_WAKE=5), device state machines, Linux probe/remove sequences (WoT config/unconfig steps), PM callback implementations |
| **`fv-thc/platform`** | Per-platform GPIO pins, BIOS WoT knob, PMC addresses, kernel version matrix, BDF/Device ID tables |
| **`fv-thc/debug`** | Failure triage flows, common failure signatures, HSDES sighting database, telemetry counters, register dump methodology |
| **`fv-thc/hidspi`** | Windows HIDSPI WoT (armForWake, EWOG bit — NOT POR), SPI suspend has NO WoT handling, QuickSPI remove/shutdown sequences |
| **`fv-thc/hidi2c`** | I2C suspend WoT-aware path, I2C sub-IP save/restore requirements, device_may_wakeup() check |
| **`fv-thc/registers`** | TSEQ_CNTRL_1 bit fields (EWOG/RWOGC — NOT POR), SWGPIO_INT (PGD domain), INT_EDG_DET_EN |
| **`fv-thc/dma`** | DMA quiesce/unquiesce for WoT entry/exit, PRD ring pointer reset on D3 wake |
| **`fv-thc/simics`** | Simics pre-silicon WoT validation, S0ix PM enabling, GPIO wake emulation |

### Key Source Files

| File | Content |
|------|---------|
| `intel-thc-wot.c` | Linux WoT implementation — **zero THC register writes**, pure GPIO/ACPI/PM subsystem |
| `intel-thc-wot.h` | WoT struct definition (thc_wot: gpio_irq, gpio_irq_wakeable) |
| `pci-quickspi.c` | QuickSPI probe/remove/PM callbacks with WoT integration |
| `pci-quicki2c.c` | QuickI2C probe/remove/PM callbacks with WoT integration |
| `Device.cpp` (Windows HIDSPI) | Windows HIDSPI WoT handling in EvtNotifyPowerDown (EWOG bit, ARM_FOR_WAKE) |
| `WoT_QuickSpiExtension.inf` | Windows WoT extension INF for HIDSPI |
| `WoT_QuickI2cExtension.inf` | Windows WoT extension INF for HIDI2C |

### Delegate Agents

- **`FV-PM-SOUTH`** — For PMC/south complex power debug related to GPIO IP wake routing and power well assignments
- **`FV_Debugger_V1`** — For Confluence wiki BKM search and HSDES sighting correlation

### Reference Documents

- `fv-thc/docs/thc_has_4x_extraction.md` — HAS reference: WAKE=No, PME=No, WoG=Not POR, vGPIO=SWGPIO_INT
- `fv-thc/docs/thc_bwg_extraction.md` — BWG reference: D0i2 wake=supported, D3=only SW wake, connected standby=stay D0i2
- `fv-thc/docs/thc_hidspi_hidi2c_kernel_study.md` — Kernel source analysis with WoT integration details
- `fv-thc/docs/thc_known_issues.md` — REVIEW-002 (WoG not POR), DOC items affecting WoT

### Wiki Pages (Confluence)

| Page ID | Title | WoT Content |
|---------|-------|-------------|
| 3590297728 | BKM BOM36 Touch Panel (QuickSPI) | WoT BKM: BIOS knob + Extension INF + restart |
| 3590298255 | BKM BOM37 Touch Panel (QuickI2C) | WoT BKM: BIOS knob + Extension INF + restart |
| 4501129284 | BKM BOM52-SPI Touch Panel | WoT BKM for BOM52 SPI |
| 4501129290 | BKM BOM52-I2C Touch Panel | WoT BKM for BOM52 I2C |
| 4606212223 | THC WCL Issues | **HSD 16027810168**: Post code 0x9B0E when WoT enabled |
| 4200761602 | WCL THC BKM | THC0/THC1 BDF constraint → S0ix failure |
| 3525690537 | THC I2C BIOS Settings | WoT BIOS knob documentation |

## See Also
- **`fv-thc/registers`** — UGD register subset (always-on domain), DEVINT_CFG_1/2 interrupt config, WoT-related status bits
- **`fv-thc/power`** — D3 entry/exit flows interacting with WoT arm/disarm, LTR unconfiguration before WoT, S0ix integration
- **`fv-thc/dma`** — DMA quiesce before WoT entry, DMA reconfigure after WoT exit, PRD ring state preservation
- **`fv-thc/hidspi`** — HIDSPI SET_POWER ON/OFF commands during WoT transitions, SPI bus reset on wake
- **`fv-thc/hidi2c`** — HIDI2C SET_POWER/RESET commands during WoT transitions, I2C sub-IP re-init on wake
- **`fv-thc/driver`** — Linux/Windows WoT implementation differences (Extension INF, pm_runtime, EWOG bit)
- **`fv-thc/platform`** — Per-platform GPIO wake pin assignments, vGPIO routing, BIOS WoT knob names
- **`fv-thc/debug`** — WoT debug playbook (Phase 4 triage), GPIO wake path verification, PMC wake source log
- **`fv-thc/simics`** — Simics WoT limitations (no real GPIO wake path), SW-CI WoT test considerations
- **Reference**: `fv-thc/docs/thc_vgpio_wot_architecture.md` — Complete vGPIO WoT wake path synthesis
