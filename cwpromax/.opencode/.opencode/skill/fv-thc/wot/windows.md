---
name: fv-thc/wot (Windows)
description: Windows WoT implementation — Extension INF, EWOG bit, TIC ARM_FOR_WAKE state, SwAS WoT entry/exit flows, WDF power callbacks, D3Cold exclusion
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Wake-on-Touch — Windows Implementation

Windows-specific WoT implementation details covering the WoT Extension INF requirement, HIDSPI `EWOG`/`ARM_FOR_WAKE` mechanism, HIDI2C WDF power callbacks, SwAS-defined WoT transition flows, and Windows-specific validation test points.

---

## 1. Windows WoT Extension INF Requirement

**Windows WoT requires installation of an Extension INF** in addition to the base driver. This is NOT required on Linux.

| Protocol | Extension INF | Source Path |
|----------|--------------|-------------|
| HIDSPI (QuickSPI) | `WoT_QuickSpiExtension.inf` | `\QuickSPI-<ver>\Desktop_PreProd\x64\Release\WoT_ExtensionINFs\` |
| HIDI2C (QuickI2C) | `WoT_QuickI2cExtension.inf` | `\QuickI2C-<ver>\Desktop_PreProd\x64\Release\WoT_ExtensionINFs\` |

**Installation**: Right-click INF → Install → Wait for completion popup → **Restart required**.

### Driver Versions with WoT Support

| Protocol | Version | Artifactory |
|----------|---------|-------------|
| QuickSPI | v4.2.0.21 (latest as of 2026-03) | `https://ubit-artifactory-ba.intel.com/artifactory/owr-repos/Submissions/quickspi/` |
| QuickI2C | v5.5.0.7 / v5.5.0.10 (latest as of 2026-03) | `https://ubit-artifactory-or.intel.com/artifactory/one-windows-local/Ingredients/hidi2c_touch/` |

---

## 2. HIDSPI WoT (Device.cpp)

The Windows HIDSPI driver receives WoT requests through the HidSpiCx framework:

| Aspect | Detail |
|--------|--------|
| Wake flag source | `armForWake` from HidSpiCx `EvtNotifyPowerDown` callback |
| TIC state | Set to `ARM_FOR_WAKE = 5` during power-down |
| Hardware config | `TSEQ_CNTRL_1.EWOG` bit set for wake detection |
| D3Cold | **Explicitly disabled** (`ExcludeD3Cold = WdfTrue`) |

> **Note**: Windows HIDSPI sets `EWOG` bit, which is a WoG infrastructure register that is NOT POR per HAS. The actual wake still comes through GPIO IP. This is a Windows-specific driver behavior that uses non-POR THC HW bits.

### HIDSPI WoT Entry Flow

```
1. EvtNotifyPowerDown callback — receives armForWake flag from HidSpiCx
2. Set TIC state = ARM_FOR_WAKE (5)        — via TIC STATE register
3. Set TSEQ_CNTRL_1.EWOG = 1              — Enable Write on GPIO for wake detection
4. DMA unconfigure
5. Enter D3 (D3Hot — D3Cold explicitly disabled)
```

---

## 3. HIDI2C WoT

The Windows HIDI2C driver uses WDF power framework:

| Aspect | Detail |
|--------|--------|
| Wake settings | `WdfDeviceAssignSxWakeSettings` / `WdfDeviceAssignS0IdleSettings` |
| D3Cold | **Explicitly disabled** (`ExcludeD3Cold = WdfTrue`) |

### HIDI2C D0Exit Flow

```
1. StopDozeTimer
2. ChangeInterruptState(false)
3. WaitForRxDMAPause
4. SendSetPower(sleep) — or skip if WoT armed
5. DmaUnconfigure → DmaFree
6. [D3Final: cleanup]
```

### HIDI2C D3 Resume Flow

```
1. TakeDeviceOutOfSleep()
2. DmaAllocate → DmaConfigure
3. LTR configuration
4. Display sync setup
5. SendSetPower(on)
6. Coalescing configuration
7. RearmDozeTimer
```

---

## 4. SwAS WoT Entry/Exit Flows

From QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0 — the authoritative Windows WoT transition sequences:

### WoT Entry (Tap-to-Wake Arming)

```
1. OS issues Wait Wake IRP to driver
2. Driver sends SET_POWER(SLEEP) to TIC
   - HIDSPI: Also sets EWOG bit + ARM_FOR_WAKE TIC state
   - HIDI2C: Standard SET_POWER(SLEEP) via PIO
3. Driver enters D3 (D3Hot — D3Cold explicitly disabled)
4. THC powers down (PGD gated), GPIO pad remains active
5. Touch device enters low-power scanning mode
```

### WoT Exit (Touch Wake → Resume)

```
1. Touch device asserts GPIO interrupt
2. GPIO IP → vGPIO → PMC → Platform Wake
3. OS resumes, driver D0 entry callback invoked
4. Driver sends SET_POWER(ON) to TIC
5. TIC resumes normal operation — NO RESET SENT
   ⚠️ This is different from normal D3→D0 which includes TIC reset
6. Driver reconfigures DMA, interrupts, LTR
7. Touch data resumes flowing
```

> **CRITICAL: No Reset on WoT Exit** — The SwAS explicitly states that WoT exit does NOT include a TIC reset (unlike normal D3→D0 resume or cold boot). The TIC must preserve its configuration across SLEEP→ON. If reset is needed, the `ResetRequiredByDriver` registry key can force it.

> **Validation Point**: Verify touch data flows correctly after WoT resume without a TIC reset. If touch fails after WoT wake but works after normal D3→D0 resume (which includes reset), this indicates a TIC state machine issue.

---

## 5. TIC Power State Enum

| Value | State Name | WoT Relevance |
|-------|-----------|---------------|
| 0 | `NO_OP` | Default/no operation |
| 1 | `DOZE` | Reduced power, limited scanning |
| 2 | `ARMED` | Ready, awaiting touch |
| 3 | `SENSING` | Active touch scanning |
| 4 | `SOFT_RESET` | Device resetting |
| **5** | **`ARM_FOR_WAKE`** | **Armed for Wake-on-Touch** |
| 6 | `ACTIVE_LTR_STATE` | Active LTR power state |
| 7 | `LOWPOWER_LTR_STATE` | Low-power LTR state |

> States 5-7 are Windows-driver-specific management states not directly mapped to HID protocol power commands. `ARM_FOR_WAKE` (5) is written to TIC during WoT entry. Linux uses only ON/SLEEP/OFF power commands.

---

## 6. Key Windows vs Linux WoT Differences

| Aspect | Windows | Linux |
|--------|---------|-------|
| **Extension INF** | Required (`WoT_QuickSpiExtension.inf` / `WoT_QuickI2cExtension.inf`) | Not needed |
| WoT SPI handling | `armForWake` + `EWOG` bit + `ARM_FOR_WAKE` TIC state | **No WoT handling** in SPI suspend path |
| WoT I2C handling | Via WDF power callbacks | Skip `SET_POWER(SLEEP)` if `device_may_wakeup()` |
| D3Cold | Disabled (`ExcludeD3Cold = WdfTrue`) | Supported (QuickI2C: 15-reg save/restore) |
| TIC wake state | Explicit `ARM_FOR_WAKE = 5` written to TIC | No explicit TIC wake state — relies on device staying powered |
| Wake IRQ mgmt | Driver manages wake settings via WDF | PM core auto-manages via `dev_pm_set_dedicated_wake_irq` |
| THC HW used for WoT | `EWOG` bit (not POR per HAS) | **None** — zero THC register writes |

---

## 7. Register Save (D3Cold — 28 Registers)

During D3Cold entry, 28 registers are manually saved by the driver. HIDI2C note: I2C APB SubIP registers are NOT included in the 28-register save set and must be saved/reprogrammed separately.

---

## 8. Windows-Specific Validation Test Points

### WoT Extension INF
- [ ] Verify WoT Extension INF installation and system restart
- [ ] Verify `powercfg /devicequery wake_armed` shows THC device
- [ ] Verify WoT works only after Extension INF installed (negative: no INF → no WoT)

### HIDSPI WoT
- [ ] Verify `armForWake` callback received from HidSpiCx
- [ ] Verify TIC state transitions: SENSING → ARM_FOR_WAKE on power-down
- [ ] Verify `TSEQ_CNTRL_1.EWOG` bit set during WoT entry
- [ ] Verify single/double tap wakes from modern standby
- [ ] Verify D3Cold is excluded (`ExcludeD3Cold = WdfTrue`)

### HIDI2C WoT
- [ ] Verify WDF wake settings applied (`WdfDeviceAssignSxWakeSettings`)
- [ ] Verify D0Exit flow: StopDozeTimer → interrupt disable → DMA pause → SET_POWER(sleep)
- [ ] Verify D3 resume: SET_POWER(on) → DMA → LTR → display sync → coalescing → RearmDozeTimer

### WoT Resume Behavior
- [ ] Verify NO TIC reset on WoT resume (SwAS: WoT exit ≠ normal D3→D0)
- [ ] Verify touch data flows correctly after WoT resume without reset
- [ ] Test `ResetRequiredByDriver` registry key forces reset on WoT resume
- [ ] Compare: WoT resume (no reset) vs normal D3 resume (with reset) — touch must work in both

### Power State Verification
- [ ] Verify TIC power state enum values during WoT transitions
- [ ] Verify D3Hot (not D3Cold) used when WoT armed

---

## See Also

- **`fv-thc/wot`** (shared SKILL.md) — WoT architecture, HW configuration, power domains, platform config
- **`fv-thc/wot`** (linux.md) — Linux WoT implementation, pinctrl-intel, S4 vGPIO investigation
- **`fv-thc/debug`** (windows.md) — WPP tracing, registry keys, telemetry for Windows debug
- **`fv-thc/power`** (windows.md) — Windows PM callbacks, D3 level exclusion, LTR config
- **`fv-thc/driver`** (windows.md) — Windows HIDSPI/HIDI2C driver source analysis
