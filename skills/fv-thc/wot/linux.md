---
name: fv-thc/wot (Linux)
description: Linux WoT implementation — thc_wot_config/unconfig, pinctrl-intel wake architecture, PM callback WoT behavior, S4 vGPIO pad delta, QuickI2C/QuickSPI WoT differences
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Wake-on-Touch — Linux Implementation

Linux-specific WoT implementation details covering the kernel driver (`intel-thc-wot.c`), pinctrl-intel wake path, QuickI2C/QuickSPI PM callback differences, and the NVL S4 vGPIO pad delta investigation.

> **Key principle**: Linux WoT implementation writes **ZERO THC registers**. It operates entirely through ACPI, GPIO, and PM subsystem APIs.

---

## 1. Linux WoT Source File

**Location**: `drivers/hid/intel-thc-hid/intel-thc/intel-thc-wot.c`

> **Note**: The extra `intel-thc/` subdirectory — the WoT code is in the core THC library, not in the protocol-specific directories.

### Data Structure

```c
struct thc_wot {
    int gpio_irq;           /* GPIO IRQ number for WoT */
    bool gpio_irq_wakeable; /* Whether the GPIO IRQ is wakeable */
};
```

---

## 2. thc_wot_config() — WoT Initialization

Exported function called during probe to set up WoT:

```
1. Validate thc_dev (non-null check)
2. Get ACPI companion device (acpi_dev)
3. acpi_dev_add_driver_gpios(adev, gpio_map)
   — THC ACPI lacks _DSD, requires manual GPIO mapping
4. acpi_dev_gpio_irq_wake_get_by(adev, "wake-on-touch", 0, &wakeable)
   — Lookup dedicated WoT GPIO by ACPI name "wake-on-touch"
   — This is a GPIO IP resource, NOT a THC register
5. Check gpio_irq > 0 AND gpio_irq_wakeable
6. device_init_wakeup(dev, true)
   — Mark device as wakeup source in PM subsystem
7. dev_pm_set_dedicated_wake_irq(dev, wot->gpio_irq)
   — PM core auto-manages enable_irq_wake/disable_irq_wake on suspend/resume
   — The IRQ is a GPIO IP interrupt, routed through vGPIO to PMC
```

### Key Design Properties

- **Non-fatal**: All failures produce `dev_warn()` and return void — WoT **never blocks** main touch functionality
- **Single-stage only**: Linux only implements single-stage GPIO-based WoT
- **PM core managed**: `dev_pm_set_dedicated_wake_irq()` means PM core automatically calls `enable_irq_wake()`/`disable_irq_wake()` during suspend/resume — no manual IRQ wake management
- **Separate GPIO**: WoT uses a dedicated ACPI GpioInt resource distinct from the main touch interrupt
- **ACPI lookup key**: `"wake-on-touch"` — kernel searches for this named GPIO
- **Zero THC HW interaction**: No THC register reads or writes in the entire WoT module

---

## 3. thc_wot_unconfig() — WoT Cleanup

Exported function called during remove:

```
1. Check gpio_irq_wakeable flag
2. device_init_wakeup(dev, false)
3. Check gpio_irq > 0
4. dev_pm_clear_wake_irq()
5. acpi_dev_remove_driver_gpios(adev)
```

---

## 4. Integration Points

WoT is called from probe and remove sequences:

**QuickSPI probe** (step after DMA/interrupt setup):
```
thc_wot_config(dev)    — called after thc_interrupt_config()
```

**QuickSPI remove** (step 5 of 8):
```
thc_wot_unconfig(dev)  — called after interrupt quiesce, before DMA deinit
```

**QuickI2C probe** (step after DMA/interrupt setup):
```
thc_wot_config(dev)    — called after thc_interrupt_enable(), same as QuickSPI
```

**QuickI2C remove** (step in quicki2c_dev_deinit):
```
thc_wot_unconfig(dev)  — called during device deinit, same pattern as QuickSPI
```

**QuickI2C GPIO mapping** (identical to QuickSPI):
```c
static const struct acpi_gpio_params wake_gpio = { 0, 0, true };
static const struct acpi_gpio_mapping quicki2c_gpios[] = {
    { "wake-on-touch", &wake_gpio, 1 }, { }
};
// Called during init: thc_wot_config(qcdev->thc_hw, &quicki2c_gpios[0]);
```

> **Key**: QuickI2C and QuickSPI use **identical** WoT config code — same ACPI GPIO name `"wake-on-touch"`, same `acpi_gpio_params {0, 0, true}` (index 0, pin 0, active-low). The only WoT difference between protocols is in suspend/resume behavior (I2C is WoT-aware, SPI is not).

---

## 5. Linux Entry Flows (Sleep → WoT Armed)

### HIDI2C Entry (WoT-Aware)

```
1. hid_driver_suspend()                    — notify HID subsystem
2. [SKIP SET_POWER(SLEEP)]                 — if device_may_wakeup() is true
3. i2c_subip_save()                        — save I2C sub-IP registers (always, even with WoT)
4. thc_interrupt_quiesce(true)             — quiesce device interrupts
5. thc_dma_unconfigure()                   — stop DMA engines
6. pci_save_state()                        — save PCI config space
7. pci_disable_device()                    — disable PCI
8. pci_set_power_state(D3hot/D3cold)       — enter D3
   [PM core auto-enables wake IRQ via dev_pm_set_dedicated_wake_irq]
```

> **Key**: I2C suspend **skips** `SET_POWER(SLEEP)` when `device_may_wakeup()` returns true. The touch device must stay responsive to generate the WoT interrupt.

### HIDSPI Entry (NO WoT Handling)

```
1. hid_driver_suspend()
2. SET_POWER(SLEEP)                        — ALWAYS sent regardless of wake state
3. thc_interrupt_quiesce(true)
4. thc_dma_unconfigure()
5. pci_save_state()
6. pci_disable_device()
7. pci_set_power_state(D3hot/D3cold)
```

> **Critical difference**: SPI suspend has **NO WoT handling** — it always sends `SET_POWER(SLEEP)` and unconfigures DMA regardless of wake state. WoT from SPI sleep states may not work as expected on Linux.

---

## 6. Linux Exit Flows (Wake → Resume)

### QuickSPI Resume

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

### QuickI2C Resume

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

---

## 7. PM Callback WoT Behavior (HIDI2C vs HIDSPI)

| PM Callback | HIDI2C (WoT-aware) | HIDSPI (No WoT handling) |
|-------------|-------------------|--------------------------|
| **suspend** | Skip `SET_POWER(SLEEP)` if `device_may_wakeup()` | Always sends `SET_POWER(SLEEP)` |
| **resume** | Skip `SET_POWER(ON)` if `device_may_wakeup()` | Always sends `SET_POWER(ON)` |
| **I2C sub-IP** | Always save/restore regs (sub-IP is in PGD, lost during PG) | N/A |
| **freeze** | No WoT handling — quiesce + DMA unconfigure only (NO `SET_POWER`) | Same — quiesce + DMA unconfigure only (NO `SET_POWER`) |
| **thaw** | No WoT handling — DMA configure + interrupt enable + quiesce(false) | Same |
| **poweroff** | **Always** `SET_POWER(SLEEP)` + LTR unconfig + full DMA deinit | **Always** `SET_POWER(SLEEP)` + quiesce + DMA deinit + LTR unconfig |
| **restore** | Full re-init: `i2c_subip_init()` + interrupt + DMA + LTR + `SET_POWER(ON)` | Full re-init: SPI config + interrupt + DMA + LTR + `SET_POWER(ON)` |
| **DMA** | Unconfigure regardless of WoT | Unconfigure regardless |
| **Wake IRQ** | PM core auto-manages via dedicated wake IRQ (GPIO IP) | PM core auto-manages via dedicated wake IRQ (GPIO IP) |

> **Critical implementation note**: The `device_may_wakeup()` checks are in **`pci-quicki2c.c`** (protocol-level PM callbacks), NOT in `intel-thc-wot.c`. The WoT module itself performs zero THC register writes.

> **Key differences**:
> - **freeze/thaw**: NO WoT handling — hibernate snapshot doesn't involve device power state changes
> - **poweroff**: ALWAYS sends `SET_POWER(SLEEP)` regardless of WoT — platform is powering off entirely
> - **restore**: Full hardware re-init from scratch (uses `i2c_subip_init()`, NOT `i2c_subip_regs_restore()`)
> - **I2C sub-IP registers** are in PGD and **always lost** during power gating — must be saved/restored even with WoT

---

## 8. pinctrl-intel Wake Controller Architecture

The platform wake path for WoT is managed entirely by the Intel GPIO pinctrl driver (`drivers/pinctrl/intel/pinctrl-intel.c`).

### Key Functions

| Function | Role in WoT |
|----------|-------------|
| `intel_gpio_irq_wake()` | Calls `enable_irq_wake(pctrl->irq)` / `disable_irq_wake(pctrl->irq)` on parent IRQ controller |
| `intel_pinctrl_suspend_noirq()` | Saves ALL pad configs: `padcfg0/1/2` + `HOSTSW_OWN` + `GPI_IE` + `GPI_GPE_EN` |
| `intel_pinctrl_resume_noirq()` | Restores ALL saved pad configs (critical for WoT GPIO surviving Sx transitions) |

### Key Design Properties

- `IRQCHIP_MASK_ON_SUSPEND` flag — GPIO IRQs are masked during suspend. Wake path uses GPE, not normal IRQ path.
- ACPI-mode pins: "usable as GPIO but cannot be used as IRQ because GPI_IS status bit will not be updated" — WoT GPIO must be in **GPIO mode**, not ACPI mode.
- Pad config save/restore ensures WoT GPIO configuration survives D3Cold/Sx power loss.

### IO APIC vs GPIO Mode for Wake

| Mode | Path | WoT Reliability |
|------|------|----------------|
| **GPIO mode** (direct) | GPIO controller handles interrupt directly | ✅ Works reliably for WoT |
| **IO APIC mode** (routed) | GPIO → ITSS → IO APIC → CPU core | ⚠️ Has known issues on WCL (HSD 16029769688) |

> **Recommendation**: WoT should use GPIO mode wake, not IO APIC routed interrupts.

### intel_pinctrl_should_save() Criteria

A pin is saved during suspend if:
- Pin is owned by kernel (`mux_owner` or `gpio_owner`)
- OR `gpiochip_line_is_irq()` returns true (WoT GPIO: yes, registered by `thc_wot_config()`)
- OR pin is in direct IRQ mode

---

## 9. S4 (Hibernate) vGPIO Pad Delta — CRITICAL

### HSD 15019129309: System Cannot Enter Hibernate on 2nd Cycle with WoT Enabled (NVL)

There is a **significant architectural delta** in how the vGPIO WoT pad is initialized during S5 (cold boot) vs S4 (hibernate resume). This delta is the root cause of the NVL S4 WoT regression.

### The Two Boot Paths

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

### Observed Symptoms on NVL

1. **1st S4 entry/resume**: Works — pad state is clean from initial boot
2. **After 1st S4 resume**: `PAD_CFG_DW0` of `VGPIO_THC0` has `RXINV` and `GPIROUTIOXAPIC` bits not properly restored
3. **Interrupt latch stays asserted** → WoT GPIO fires spurious interrupts continuously
4. **2nd S4 entry**: `pm_wakeup_pending` already set → kernel aborts hibernate with `"Wakeup pending. Abort CPU freeze"`

### Why S5 Works but S4 Fails (2nd Cycle)

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
  THC restore: full re-init
  → WoT works ✓ (pad state was clean from initial boot)

S4 Cycle 2 (2nd Hibernate attempt):
  freeze: pinctrl saves pad config (NOW has stale RXINV/GPIROUTIOXAPIC from cycle 1)
  → "Wakeup pending. Abort CPU freeze" — spurious interrupts from stale pad
  → Hibernate ABORTED ✗
```

### Investigation Hypotheses

**Hypothesis 1 — Pad Reset Type** (attempted, did NOT fix):
- Changed vGPIO_THC pad from `GpioV2ResetHost` to `GpioV2ResetHostDeep`
- BIOS 3080.24 — did NOT resolve issue

**Hypothesis 2 — Interrupt Routing Mode** (under test):
- Switched from IO APIC (`GPIROUTIOXAPIC=1`) to SCI/GPE mode (`GPIRoutSCI=1`)
- BIOS 3100 — added ACPI `_PRW` (GPE 0x6F) + `_DSW`, changed level→edge triggered

**Hypothesis 3 — Linux pinctrl driver NVL delta** (escalated):
- fengxu (Mar 6): "Linux GPIO driver doesn't handle Pin configure during sleep correctly on NVL"
- Escalated to Linux GPIO driver owner (Saranya Gopal)

### PythonSV Debug Commands (NVL)

```python
# Read vGPIO_THC0 pad config across transitions
pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show()

# Key bits to check in PAD_CFG_DW0:
#   RXINV (bit 23)          — RX inversion, should match initial config
#   GPIROUTIOXAPIC (bit 20) — IO APIC routing, should be 0 for GPIO mode WoT
#   GPIROUTSCI (bit 19)     — SCI routing for wake
#   RXEVCFG (bits 26:25)    — RX event config
#   PMODE (bits 12:10)      — Pad mode

# Compare these 4 states:
#   #1: WoT disabled (baseline)
#   #2: WoT enabled, before any S4
#   #3: Before S4 entry (after WoT armed)
#   #4: After S4 resume (check for stale bits)
```

### Platform Scope

| Platform | Status |
|----------|--------|
| **NVL** | Affected (HSD 15019129309 — OPEN) |
| **LNL/PTL/WCL** | NOT affected per sighting comments |
| **Windows** | NOT affected (WoT Extension INF not ready for NVL QuickI2C) |

### Known Firmware Bug (Upstream)

Linux `pinctrl-intel.c` has a known firmware interaction bug (kernel bugzilla 214749): "firmwares that don't restore pin settings correctly after suspend, Rx value becomes inverted." The THC vGPIO S4 issue may be a manifestation of this broader class.

---

## 10. Kernel Version Feature Matrix (WoT-Relevant)

| Kernel | WoT-Related Features |
|--------|---------------------|
| 6.17 | WoT support added, PTL QuickI2C, `INT_EDG_DET_EN` fix (`8fe2cd8`) |
| 6.18 | WCL Device IDs, ACPI config enhancements |
| 6.20 | I2C regs save pointer fix (`a7fc15e`) — **CRITICAL for D3Cold SnR with WoT** |

---

## 11. Linux-Specific Validation Test Points

### WoT Config
- [ ] Verify `thc_wot_config()` succeeds when ACPI `"wake-on-touch"` GPIO present
- [ ] Verify `thc_wot_config()` degrades gracefully (warn, not error) when GPIO absent
- [ ] Verify `device_may_wakeup()` returns true after successful WoT config
- [ ] Verify dedicated wake IRQ registered via `dev_pm_set_dedicated_wake_irq()`
- [ ] Verify `thc_wot_unconfig()` cleans up all WoT state
- [ ] Verify wake IRQ is a GPIO IP interrupt (not THC interrupt)

### WoT with I2C (Primary Path)
- [ ] Verify `SET_POWER(SLEEP)` is SKIPPED when `device_may_wakeup()` is true
- [ ] Verify I2C sub-IP registers are saved even with WoT (sub-IP is in PGD)
- [ ] Verify I2C sub-IP registers restored correctly on wake
- [ ] Verify I2C save pointer fix (`a7fc15e`) applied for D3Cold scenarios

### WoT with SPI (Limited)
- [ ] Verify SPI suspend always sends `SET_POWER(SLEEP)` (no WoT handling on Linux)
- [ ] Document WoT behavior expectations for SPI path

### S4 Hibernate Stress
- [ ] S4 hibernate + resume 1 cycle with WoT enabled (baseline)
- [ ] S4 hibernate + resume **2+ cycles** with WoT enabled (HSD 15019129309 regression)
- [ ] After S4 resume, verify vGPIO_THC0 `PAD_CFG_DW0` matches pre-S4 config
- [ ] After S4 resume, verify WoT GPIO interrupt count is NOT increasing without touch (`/proc/interrupts`)
- [ ] Verify `RXINV` (bit 23) and `GPIROUTIOXAPIC` (bit 20) correct after S4 resume
- [ ] S4 restore path: verify `i2c_subip_init()` (not `i2c_subip_regs_restore()`) used for full re-init
- [ ] Verify `thc_wot_config()` is NOT re-called on S4 restore (state from hibernate image)
- [ ] S4 with WoT on NVL (primary failure platform) vs PTL/WCL (should not be affected)

---

## See Also

- **`fv-thc/wot`** (shared SKILL.md) — WoT architecture, HW configuration, power domains, validation test points
- **`fv-thc/wot`** (windows.md) — Windows WoT Extension INF, EWOG, TIC states, SwAS flows
- **`fv-thc/debug`** (linux.md) — Linux debug tools (dmesg, ftrace, sysfs) for general THC triage
- **`fv-thc/power`** (linux.md) — Linux PM callbacks, runtime PM, D3 levels
- **`fv-thc/hidi2c`** (linux.md) — QuickI2C Linux probe, I2C sub-IP save/restore
- **`fv-thc/hidspi`** (linux.md) — QuickSPI Linux probe, SET_POWER fire-and-forget
