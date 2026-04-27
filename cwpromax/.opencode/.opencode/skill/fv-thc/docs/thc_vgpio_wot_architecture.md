> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC vGPIO Wake-on-Touch Architecture — Complete Reference

> **Synthesized from**: THC IP HAS v4.x (Sep 2025), HSDES sightings, Linux kernel v6.17-6.20 (`intel-thc-wot.c`, `pci-quickspi.c`, `pci-quicki2c.c`, `pinctrl-intel.c`), Confluence wiki BKMs, Windows HIDSPI/HIDI2C driver source
>
> **Date**: 2026-03-06
> **Purpose**: Definitive reference for how Wake-on-Touch (WoT) works in the THC domain, correcting prior misconceptions about THC IP generating wake signals.

---

## 1. Executive Summary

**Wake-on-Touch (WoT) does NOT come from THC IP.** THC has `WAKE=No` and `PME=No` in its PCI capabilities. The actual wake path is:

```
Touch Device GPIO pin  -->  GPIO IP Pad (always-on power well)  -->  vGPIO  -->  PMC  -->  Platform Wake
```

THC's role is **driver-side only**: register the GPIO as a wake source during probe, configure device power state during suspend, and re-initialize THC hardware after resume.

---

## 2. Wake Signal Path — End-to-End

### 2.1 Hardware Wake Path (GPIO IP Territory)

```
┌─────────────┐    GPIO Pin    ┌──────────────────┐    vGPIO    ┌─────────┐
│ Touch Device │──────────────>│ GPIO IP Pad       │───────────>│  PMC    │
│ (WACOM/ELAN) │               │ (always-on well)  │            │         │
└─────────────┘               │ PADCFGLOCK must   │            │ Power   │
                               │ be UNLOCKED (0x0) │            │ Ungating│
                               └──────────────────┘            └────┬────┘
                                                                     │
                                                           Restore power to THC
                                                                     │
                                                                     v
                                                              ┌─────────────┐
                                                              │ THC IP      │
                                                              │ (passive    │
                                                              │  recipient) │
                                                              └─────────────┘
```

### 2.2 Software Wake Path (Driver Territory)

```
                    PROBE TIME                              SUSPEND TIME
                    ==========                              ============
  thc_wot_config()                                    PM suspend callback
        │                                                     │
        v                                                     v
  acpi_dev_add_driver_gpios()                         Skip SET_POWER(SLEEP)
  → manual GPIO mapping                              if device_may_wakeup()
  ("wake-on-touch" key)                                       │
        │                                                     v
        v                                              pci_set_power_state(D3)
  acpi_dev_gpio_irq_wake_get_by()                            │
  → find WoT GPIO IRQ                                        v
        │                                              PM core auto-calls
        v                                              enable_irq_wake()
  device_init_wakeup(dev, true)                        via dedicated wake IRQ
        │
        v                                             RESUME TIME
  dev_pm_set_dedicated_wake_irq()                     ===========
  → PM core manages IRQ wake                    PM resume callback
    enable/disable automatically                      │
                                                      v
                                                pci_set_power_state(D0)
                                                pci_restore_state()
                                                THC register restore
                                                DMA re-init
                                                Touch operational
```

---

## 3. GPIO IP Wake Controller Architecture (pinctrl-intel.c)

The Intel GPIO controller driver (`pinctrl-intel.c`) provides the actual wake infrastructure:

### 3.1 IRQ Wake Management

```c
// drivers/pinctrl/intel/pinctrl-intel.c
static int intel_gpio_irq_wake(struct irq_data *d, unsigned int on) {
    // enable_irq_wake(pctrl->irq) — arms parent IRQ for wake
    // disable_irq_wake(pctrl->irq) — disarms parent IRQ
}
```

- **IRQCHIP_MASK_ON_SUSPEND** flag — GPIO IRQs are masked during suspend; only wake-enabled IRQs remain active
- The parent IRQ is the GPIO controller's consolidated interrupt line to the GIC/APIC

### 3.2 Pad Save/Restore During S-state Transitions

```c
// intel_pinctrl_suspend_noirq / intel_pinctrl_resume_noirq
// Saves and restores ALL pad configurations:
//   - padcfg0, padcfg1, padcfg2 (per-pad config)
//   - HOSTSW_OWN (host software ownership)
//   - GPI_IE (GPIO interrupt enable)
//   - GPI_GPE_EN (GPE enable for wake)
```

### 3.3 ACPI Mode Limitation

ACPI-owned GPIO pins are "usable as GPIO but cannot be used as IRQ because GPI_IS status bit will not be updated." This means WoT GPIO pads MUST be in host-software-owned mode.

---

## 4. vGPIO Architecture (MTL+, from THC HAS)

### 4.1 SWGPIO_INT Register

From HAS (Lines 13231-13276):

> "On MTL and forward, a virtual GPIO based SW interrupt added as output signal on THC top level, connected to input vGPIO at SoC level. vGPIO interrupt pin driven from MMIO register (SWGPIO_INT) bit controlled by driver."

| Register | Bit | Field | Domain | Description |
|----------|-----|-------|--------|-------------|
| INT_CAUSE | 4 | `SWGPIO_INT` | **PGD** | SW-controlled vGPIO interrupt output |

- **1** = Assert through vGPIO (to SoC-level GPIO IP)
- **0** = Deassert
- **Power Domain**: PGD — lost during power gate, must be in save/restore list
- **Purpose**: Provides a THC-to-GPIO-IP signaling path (THC can *trigger* a vGPIO interrupt, but this is NOT used for wake; it's for runtime SW-initiated interrupt signaling)

### 4.2 pmc_THC_wake Signal

From HAS (Lines 15143-15157):

| Signal | Direction | Type | Description |
|--------|-----------|------|-------------|
| `pmc_THC_wake` | **INPUT** (PMC → THC) | RTL Signal | "PMC Wake from IP-Inaccessible" |

**CRITICAL**: This is PMC telling THC to wake up, NOT THC telling PMC it wants to wake. The naming can be misleading.

---

## 5. vGPIO Pad Locking — PADCFGLOCK (Critical for WoT)

### 5.1 The Problem

GPIO pad configuration can be locked by BIOS to prevent OS/driver modification. If the vGPIO_THC pad is locked, the OS driver CANNOT configure it for wake → WoT fails silently.

### 5.2 Required State for WoT

| Register | Required Value | Description |
|----------|---------------|-------------|
| `PADCFGLOCK_VGPIO_THC0` | **0x0** (unlocked) | Allows Host SW/OS driver to control vGPIO_THC pad for WoT |
| `PADCFGLOCKTX_VGPIO_THC0` | 0x0 or 0x1 | TX lock not currently impacting WoT (but 0x0 preferred) |

### 5.3 Root Cause: BIOS "Force Unlock" Setting

- **BIOS Setting**: "Force unlock on all GPIO pads"
- **When set to `Disable`** (default on some platforms): BIOS locks GPIO pads including vGPIO_THC → WoT fails
- **When set to `Enable`**: BIOS unlocks all pads → vGPIO_THC is unlocked → WoT works

### 5.4 Platform-Specific Behavior

| Platform | Affected by "Force unlock = Disable"? | Notes |
|----------|---------------------------------------|-------|
| **PTL** | **No** | PADCFGLOCK for vGPIO_THC stays 0x0 even with Force unlock disabled |
| **NVL** | **Yes** | PADCFGLOCK_VGPIO_THC0 = locked when Force unlock disabled |
| **WCL** | **Yes** | Fixed in HSD 16028429994 (BIOS bug) |

### 5.5 HSDES Reference

| HSD | Platform | Issue | Resolution |
|-----|----------|-------|------------|
| **15018635096** | NVL-Hx A1 | vGPIO WoT failed, PADCFGLOCK locked | BIOS fix: NovaLake_2460_22 |
| **15018631846** | NVL-Hx A1 | Same issue, initial filing | Rejected (dup of above) |
| **16028429994** | WCL | THC not entering D3 during S0ix | BIOS fix (central_firmware.bug tenant) |

### 5.6 Debug: How to Check PADCFGLOCK

```
# Via GPIOConfig.exe (Windows):
GPIOConfig.exe /pad VGPIO_THC0 /show

# Via PySV (requires DFT access):
import pysvtools.pcdsoc.south as south
# Read GPIO community registers for vGPIO pad group
# Look for PADCFGLOCK register in the vGPIO community

# Via Linux (if debugfs available):
cat /sys/kernel/debug/pinctrl/*/pins | grep -i vgpio_thc
```

---

## 6. HSDES Sighting Database — WoT/vGPIO

### 6.1 THC Wake Sightings (sighting_central.sighting)

| HSD | Platform | Title | Status | Component | Key Info |
|-----|----------|-------|--------|-----------|----------|
| **1504682588** | - | S0ix: Unexpected wake by THC D3 during S0ix entry | complete | - | THC D3 interfering with S0ix |
| **15012559401** | MTL-P | Low D3 Residency with WoT Enabled | complete | doc.bwg | BWG documentation issue |
| **15013145991** | MTP-S | THC WoT Not Able to Wake from S0iX | rejected | - | Initial filing |
| **15013380739** | MTP-S | THC WoT Not Able to Wake from S0iX | root_caused | bios | BIOS configuration issue |
| **15018631846** | NVL-Hx A1 | THC WoT via vGPIO Failed (Force unlock=Disable) | rejected | bios | Dup of 15018635096 |
| **15018635096** | NVL-Hx A1 PO | THC WoT via vGPIO Failed (Force unlock=Disable) | root_caused | bios | **PADCFGLOCK issue** (willychi) |
| **16026436000** | PTL PCD | System failed s0ix, enable_device_wake:ret=False | rejected | - | |
| **16029769688** | WCL | Wake from touchpad not working after ~10-15 cycles (IO APIC) | **OPEN** | hw.lpss | **IO APIC RTE masking bug** |
| **15018720525** | PTL-H | Touchpad can't wake from MS | OPEN | hw.lpss | Modern Standby wake fail |
| **15017890583** | PTL PCD | GSTATES fail during S4 cycle | rejected | - | |

### 6.2 WCL IO APIC Wake Failure — Detailed Analysis (HSD 16029769688)

**Status**: OPEN (as of 2026-03-06)

**Two failure signatures** (by manishp1):

#### Signature 1 (6 out of 10 failures):
- RTE84 mask bit stays **set** after first ITSS→CORE interrupt delivery
- OS receives the interrupt but does NOT unmask the RTE after EOI
- Subsequent touch interrupts are blocked by the masked RTE
- **Root cause**: OS IO APIC driver not unmasking after EOI

#### Signature 2 (4 out of 10 failures):
- RTE mask bit is NOT set, but `did` + `edid` = 0
- Interrupt not routed to any core
- Correlated with known LNL ISH issue (HSD 15015234406)
- **Root cause**: Interrupt delivery/routing failure

**Debug evidence**:
- FTH trace: First IOAPIC interrupt from `gpp_F_18` (touchpad GPIO) processed by ITSS, EOI received, but OS fails to unmask RTE84
- **GPIO mode works** — only IO APIC mode is affected
- **Mitigation**: `ForceIdleTimeout` regkey = `0x3` (default `0x7`) → PASS
- **Promoted to Microsoft**: MTC 22022108803

### 6.3 vGPIO Sightings (sighting_central.sighting + client_soc_chipset.sighting)

- 16 vGPIO sightings in sighting_central — mostly CNVi/BT, NOT THC-related
- 4 vGPIO sightings in client_soc_chipset — all CNVi BT, NOT THC-related
- **THC-specific vGPIO**: Only HSD 15018635096 and 15018631846 are THC vGPIO sightings

---

## 7. Linux Kernel Implementation Details

### 7.1 File: `intel-thc-wot.c` (2465 bytes, Copyright 2025)

```c
struct thc_wot {
    int gpio_irq;            // GPIO IRQ number for WoT
    bool gpio_irq_wakeable;  // Whether the GPIO IRQ is wakeable
};
```

**Key property**: ZERO THC register writes. Entirely ACPI/GPIO/PM subsystem.

#### `thc_wot_config(thc_dev, gpio_map)`
1. `acpi_dev_add_driver_gpios(adev, gpio_map)` — manually register GPIO mapping (THC ACPI device has _CRS with GpioInt() but NO _DSD)
2. `acpi_dev_gpio_irq_wake_get_by(adev, "wake-on-touch", 0, &wakeable)` — find WoT GPIO
3. Check `gpio_irq > 0` AND `gpio_irq_wakeable == true`
4. `device_init_wakeup(dev, true)` — mark as wakeup source
5. `dev_pm_set_dedicated_wake_irq(dev, wot->gpio_irq)` — PM core auto-manages

#### `thc_wot_unconfig(thc_dev)`
1. `device_init_wakeup(dev, false)`
2. `dev_pm_clear_wake_irq(dev)`
3. `acpi_dev_remove_driver_gpios(adev)`

### 7.2 GPIO Mapping (QuickSPI)

```c
static const struct acpi_gpio_params wake_gpio = { 0, 0, true };
static const struct acpi_gpio_mapping quickspi_gpios[] = {
    { "wake-on-touch", &wake_gpio, 1 },
    { }
};
// Called: thc_wot_config(qsdev->thc_hw, &quickspi_gpios[0]);
```

### 7.3 GPIO Mapping (QuickI2C)

Identical pattern to QuickSPI — same `"wake-on-touch"` key, same `thc_wot_config()` call:

```c
static const struct acpi_gpio_params wake_gpio = { 0, 0, true };
static const struct acpi_gpio_mapping quicki2c_gpios[] = {
    { "wake-on-touch", &wake_gpio, 1 },
    { }
};
// Called: thc_wot_config(qcdev->thc_hw, &quicki2c_gpios[0]);
```

### 7.4 QuickI2C PM Callbacks — WoT Behavior per Transition

| PM Callback | WoT-Aware? | SET_POWER | I2C Sub-IP Regs | DMA | Notes |
|-------------|-----------|-----------|-----------------|-----|-------|
| **suspend** | **YES** | Skip SLEEP if `device_may_wakeup()` | `i2c_subip_regs_save()` BEFORE dma_unconfigure | Unconfigure | Device stays ON for wake detection |
| **resume** | **YES** | Skip ON if `device_may_wakeup()` | `i2c_subip_regs_restore()` AFTER port_select | Configure | `port_select(I2C)` → restore → int_config → int_enable → dma_configure → quiesce(false) |
| **freeze** | **NO** | None | Not saved | Unconfigure | Hibernate snapshot — no device power change |
| **thaw** | **NO** | None | Not restored | Configure | Resume from snapshot — no device power change |
| **poweroff** | **NO** | **ALWAYS SLEEP** | Not saved | Full deinit | Platform powering off — LTR unconfig, dma_deinit |
| **restore** | **NO** | **ALWAYS ON** | Full `i2c_subip_init()` | Full configure | Hibernate resume — complete re-init from scratch |
| **runtime_suspend** | **NO** | None | Not saved | Unchanged | LTR mode → LP only |
| **runtime_resume** | **NO** | None | Not restored | Unchanged | LTR mode → ACTIVE only |

**Critical I2C-specific detail**: `thc_i2c_subip_regs_save()` MUST be called BEFORE D3 entry. Without this, the Synopsys I2C sub-IP registers are lost during power gating and touch is corrupt after resume. Fixed in kernel 6.20 commit `a7fc15e`.

### 7.5 QuickI2C PCI Device IDs (I2C Mode)

| Platform | Port 1 | Port 2 | Driver Data | Notes |
|----------|--------|--------|-------------|-------|
| LNL | 0xA848 | 0xA84A | NULL | First HIDI2C support, no PTL features |
| PTL-H | 0xE348 | 0xE34A | ptl_ddata | max_detect=255, max_int_delay=256 |
| PTL-U | 0xE448 | 0xE44A | ptl_ddata | Same features as PTL-H |
| WCL | 0x4D48 | 0x4D4A | ptl_ddata | Same features as PTL |
| NVL | — | — | — | **No I2C Device IDs** (SPI-only?) |
| ARL | — | — | — | **No I2C Device IDs** |
| RZL/TTL | — | — | — | **No I2C Device IDs** |

> **⚠️ Gap**: NVL, ARL, RZL, and TTL have NO QuickI2C PCI Device IDs in the Linux kernel driver. These platforms may be SPI-only for touch, or I2C support is pending upstream.

### 7.6 Why Manual GPIO Mapping?

THC ACPI device defines GPIO resources in `_CRS` (Current Resource Settings) but does NOT have `_DSD` (Device Specific Data) with GPIO name bindings. The Linux ACPI GPIO subsystem needs name→resource mapping to find GPIOs by name. The driver provides this mapping manually via `acpi_dev_add_driver_gpios()`.

### 7.5 Non-Fatal Design

All WoT failures produce `dev_warn()` and return void. WoT NEVER blocks main touch functionality. If the wake GPIO is absent or not wakeable, touch still works — just no WoT.

---

## 8. Windows Implementation Differences

### 8.1 HIDSPI WoT (Windows-Specific)

| Aspect | Detail |
|--------|--------|
| Wake flag | `armForWake` from HidSpiCx `EvtNotifyPowerDown` callback |
| TIC state | `ARM_FOR_WAKE = 5` written to TIC STATE register |
| HW config | `TSEQ_CNTRL_1.EWOG` bit set (NOT POR per HAS) |
| D3Cold | **Explicitly disabled** (`ExcludeD3Cold = WdfTrue`) |
| Extension INF | **Required**: `WoT_QuickSpiExtension.inf` |

### 8.2 HIDI2C WoT (Windows)

| Aspect | Detail |
|--------|--------|
| Wake settings | `WdfDeviceAssignSxWakeSettings` / `WdfDeviceAssignS0IdleSettings` |
| D3Cold | **Explicitly disabled** (`ExcludeD3Cold = WdfTrue`) |
| Extension INF | **Required**: `WoT_QuickI2cExtension.inf` |

### 8.3 Linux vs Windows Summary

| Aspect | Linux | Windows |
|--------|-------|---------|
| THC HW registers for WoT | **ZERO** | EWOG bit + ARM_FOR_WAKE TIC state |
| Extension INF | Not needed | Required |
| Wake IRQ management | PM core auto-manages | Driver manages via WDF |
| D3Cold support | Supported | Disabled |
| SPI WoT handling | **None** (always SET_POWER SLEEP) | Full (armForWake + EWOG) |

---

## 9. Platform Configuration Matrix

### 9.1 WoT Support by Platform

| Platform | Gen | WoT from D0i2 | WoT from D3 | PADCFGLOCK Issue | Notes |
|----------|-----|---------------|-------------|------------------|-------|
| MTL | 3.0 | Yes | Platform-dependent | Unknown | First vGPIO support |
| LNL | 4.0 | Yes | Possible | Unknown | First HIDI2C WoT |
| PTL | 4.1 | Yes | Possible | **Not affected** | D3 flow overhauled |
| WCL | 4.1 | Yes | Possible | **Yes** (fixed) | IO APIC wake issue (HSD 16029769688) |
| NVL | 4.2 | Yes | Possible | **Yes** (fixed) | PADCFGLOCK (HSD 15018635096) |
| RZL/TTL | 4.2 | Yes | Possible | TBD | Same HAS as NVL |

### 9.2 BIOS Prerequisites for WoT

1. **THC WoT BIOS knob** = Enabled (`BIOS Menu → Intel Advanced → PCH-IO → THC Configuration → Wake on Touch`)
2. **ACPI GpioInt resource** defined for WoT GPIO in THC device's `_CRS`
3. **vGPIO_THC pad UNLOCKED**: `PADCFGLOCK_VGPIO_THC0 = 0x0`
4. **"Force unlock on all GPIO pads"** = Enable (or BIOS fix applied for platform-specific lock behavior)
5. **THC enabled**: THC port must be active (THC1 requires THC0 on PTL/NVL)
6. **Power gating enabled**: `HAE` (bit 5) and `D3HE` (bit 2) in `THC_CFG_PCE`
7. **LTR configured**: Proper LTR values before D0i2/D3 entry
8. **Windows only**: WoT Extension INF installed + system restarted

### 9.3 Known Blockers by Platform

| Platform | Blocker | HSD | Status | Workaround |
|----------|---------|-----|--------|------------|
| WCL | Post code 0x9B0E when WoT enabled in BIOS | 16027810168 | Open | Disable WoT in BIOS |
| WCL | Touchpad wake fails after 10-15 cycles (IO APIC) | 16029769688 | **OPEN** | ForceIdleTimeout=0x3 |
| NVL | vGPIO WoT fails (PADCFGLOCK locked) | 15018635096 | Fixed | BIOS NovaLake_2460_22 |
| PTL-H | Touchpad can't wake from Modern Standby | 15018720525 | OPEN | TBD |
| NVL-HX | S4 hibernate fails on 2nd cycle with WoT | 15019129309 | **OPEN** | Under investigation — HostDeepReset attempted, did not fix; SCI/GPE mode + pinctrl driver being evaluated |

---

## 9.5 S4 (Hibernate) vs S5 (Cold Boot) vGPIO Pad Initialization Delta

### Critical Difference

| Aspect | S5 (Cold Boot) | S4 (Hibernate Resume) |
|--------|----------------|----------------------|
| `thc_wot_config()` called? | ✅ Yes (during `probe()`) | ❌ No (state restored from hibernate image) |
| pinctrl pad config source | ACPI (fresh) | Saved DW0/DW1 from freeze phase |
| PADCFGLOCK risk | None (kernel configures after BIOS) | **HIGH** — BIOS may lock pad before pinctrl restore |
| Interrupt latch state | Clean (power was off, fresh config) | **Stale** if pad reset type doesn't clear it |
| `pm_wakeup_pending` | 0 (fresh boot) | May be non-zero if latch fires spuriously |

### S4 Entry/Resume Sequence (Linux)

```
[S4 Entry]
  freeze_noirq:  pinctrl saves PAD_CFG_DW0/DW1 of vGPIO_THC (registered as IRQ)
  poweroff:      THC driver sends SET_POWER(SLEEP) — always, regardless of WoT

[Power Cut — electrically identical to S5]

[S4 Resume]
  BIOS boots:    Full init → configures vGPIO_THC → may apply PADCFGLOCK
  Kernel boots:  Finds hibernate image → restores memory state
  restore_noirq: pinctrl tries to restore saved pad config
                 → ⚠️ PADCFGLOCK set? Write silently fails
  THC restore(): Full HW re-init (LTR, DMA, interrupts)
                 → ⚠️ thc_wot_config() NOT called (WoT state from hibernate image)
```

### NVL Investigation (HSD 15019129309 — OPEN, Not Yet Root-Caused)

**Observed symptoms:**
1. vGPIO_THC0 pad configured with `GpioV2ResetHost` (Host Reset)
2. After 1st S4 resume: RXINV and GPIROUTIOXAPIC bits in PAD_CFG_DW0 not correctly restored
3. Interrupt latch stays asserted → spurious interrupts without touch
4. `pm_wakeup_pending++` → 2nd S4 blocked: "Wakeup pending. Abort CPU freeze"

**Fix attempts (none confirmed):**
- **Attempt 1**: BIOS set pad reset to `GpioV2ResetHostDeep` → **Did NOT fix** (BIOS 3080.24)
- **Attempt 2**: BIOS switch pad to SCI/GPE mode (edge trigger) + ACPI `_PRW`/`_DSW` → Under test (BIOS 3100)
- **Hypothesis 3**: Linux pinctrl driver doesn't handle NVL pad config correctly during sleep (fengxu, Mar 6)

### Debug Command (PythonSV)

```python
# Check vGPIO_THC0 pad config across sleep transitions:
pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show()
# Capture in 4 states: WoT off, WoT on, Before S4, After S4 resume
# Look for: RXINV, GPIROUTIOXAPIC, PADRSTCFG (reset type) changes
```

### Platform Scope

- **NVL**: ✅ Affected (`GpioV2ResetHost` used)
- **LNL/PTL/WCL**: ❌ Not affected (different pad reset config)

---

## 10. Validation Checklist

### 10.1 Pre-Test Verification

- [ ] BIOS WoT knob enabled
- [ ] `PADCFGLOCK_VGPIO_THC0 = 0x0` (verify via GPIOConfig or PySV)
- [ ] WoT Extension INF installed (Windows only)
- [ ] `powercfg /devicequery wake_armed` shows THC device (Windows)
- [ ] `cat /sys/devices/.../power/wakeup` shows "enabled" (Linux)
- [ ] `dmesg | grep wake-on-touch` shows no warnings (Linux)

### 10.2 Wake Test Matrix

| Test | D0i2 | D3Hot | D3Cold | S0ix | S3 |
|------|------|-------|--------|------|-----|
| Single tap wake | Yes | Yes* | Yes* | No** | No |
| Multi-tap wake | Yes | Yes* | Yes* | No** | No |
| Wake + touch data | Yes | Yes* | Yes* | No** | No |
| Wake stress (100 cycles) | Yes | Yes* | Yes* | No** | No |

\* Requires touch GPIO on always-on power well
\** THC does NOT generate S0ix wakes; S0ix wake requires WoG (NOT POR)

### 10.3 Known Failure Modes

| Failure | Root Cause | Debug |
|---------|-----------|-------|
| WoT never triggers | PADCFGLOCK locked | Check `PADCFGLOCK_VGPIO_THC0` |
| WoT never triggers | ACPI GPIO missing | Check `dmesg` for `thc_wot_config` warn |
| WoT never triggers (Windows) | Extension INF not installed | Install and restart |
| WoT works 10x then stops (WCL) | IO APIC RTE masking (HSD 16029769688) | Set ForceIdleTimeout=0x3 |
| WoT works from D0i2, not D3 | GPIO not on always-on power well | Check GPIO pad power well |
| Touch corrupt after wake | I2C sub-IP regs not restored | Verify kernel fix `a7fc15e` |
| Post code 0x9B0E (WCL) | BIOS bug | HSD 16027810168, disable WoT |

---

## 11. References

### Source Documents
- **THC IP HAS v4.x** (Sep 2025): `sip_thc_4x_has.html` — Lines 11461-11541 (WoG), 13231-13276 (vGPIO), 15143-15157 (pmc_THC_wake), 15883-15998 (D0i2/D3 wake), 20938-21020 (WoG sequencer)
- **THC BWG** (Rev 0.5): Wake constraints — D0i2 touch wake supported, D3 only SW wake
- **Linux Kernel**: `intel-thc-wot.c` (v6.17+), `pci-quickspi.c`, `pci-quicki2c.c`, `pinctrl-intel.c`
- **Windows HIDSPI Driver**: `Device.cpp` — armForWake, EWOG, ARM_FOR_WAKE TIC state
- **Confluence Wiki**: Pages 3590297728, 3590298255, 4501129284, 4501129290, 4606212223

### HSDES Sightings
- **15018635096** (NVL, root_caused, willychi): vGPIO WoT PADCFGLOCK
- **15019129309** (NVL-HX, OPEN, willychi): S4 hibernate fails on 2nd cycle with WoT — under investigation. Symptoms: RXINV/GPIROUTIOXAPIC bits not restored after S4, spurious interrupts, `pm_wakeup_pending` blocks 2nd hibernate. HostDeepReset attempted but did not fix. SCI/GPE mode + pinctrl driver behavior being evaluated
- **16029769688** (WCL, OPEN): IO APIC touchpad wake failure
- **15013380739** (MTP-S, root_caused): WoT S0iX BIOS config
- **15018720525** (PTL-H, OPEN): Touchpad Modern Standby wake
- **16027810168** (WCL, wiki): Post code 0x9B0E with WoT
- **16028429994** (WCL, central_firmware.bug): THC not entering D3 during S0ix (BIOS fix)
