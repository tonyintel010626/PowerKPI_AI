# THC Power Management — Windows Implementation

> **Owner**: willychi | **Platform**: Windows
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

This file covers Windows-specific THC power management implementation details. For shared HW architecture, see [SKILL.md](SKILL.md). For Linux implementation, see [linux.md](linux.md).

## Windows LTR Management Details (Phase 6)

> **Source**: Windows HIDI2C driver v3.0.0.9000 — Phase 6 audit

### LTR Clamping Policy

| Active LTR Range | Behavior |
|-------------------|----------|
| `0` | Disable all LTR |
| `1-200` | Clamp to `200` |
| `201-1023` | As-is (no clamp) |
| `≥1024` | Clamp to `1023` |

### LTR Defaults (Windows)

- **Default Active LTR**: **0x03FF (1023)** — fallback when ACPI DSM fails
- **Default LP LTR**: **0x03FF (1023)** — fallback when ACPI DSM fails
- **LTR Scale**: Always `2` (1,024 ns units) — Windows hardcodes scale=2

> **Different from Linux**: Linux defaults to Active=5µs, LP=500µs. Windows falls back to 1023 for both.

### LTR Source Priority

Registry > ACPI DSM > default (0x03FF)

Windows adds a registry override layer that Linux does not have.

### Windows vs Linux LTR Comparison

| Parameter | Windows | Linux | Notes |
|-----------|---------|-------|-------|
| Active LTR clamp range | `0` → disable all LTR; `1-200` → clamp to `200`; `201-1023` → as-is; `≥1024` → clamp to `1023` | No clamp | Windows enforces full clamping policy |
| ACT/LP LTR Scale | Always `2` (1,024 ns units) | Auto-selected (Linux selects scale via descending checks: 5→4→3→2) | Windows hardcodes scale=2 |
| Default Active LTR | **0x03FF (1023)** — fallback when ACPI DSM fails | 5 µs (`DEFAULT_ACTIVE_LTR_US`) | **Different defaults**: Windows falls back to 1023, Linux defaults to 5 |
| Default LP LTR | **0x03FF (1023)** — fallback when ACPI DSM fails | 500 µs (`DEFAULT_LP_LTR_US`) | **Different defaults**: Windows falls back to 1023, Linux defaults to 500 |
| LTR source priority | Registry > ACPI DSM > default (0x03FF) | ACPI DSM > default | Windows adds registry override |
| Toggle stall | **5 µs** between LP_LTR_EN 0→1 | None specified (Linux does not use toggle in unconfig) | Windows inserts a short stall for its toggle-based sequence |

### Windows EnterActiveLTR() Flow

1. Write Active LTR value+scale to **LP_LTR** registers (not ACTIVE_LTR registers — Windows uses LP_LTR for the active path)
2. Set `LP_LTR_EN = 0`
3. Wait ~5 µs
4. Set `LP_LTR_EN = 1`
5. (Toggle generates IOSF SB LTR message to PMC)

> **Note**: Despite the name `EnterActiveLTR`, Windows writes to LP_LTR_VALUE/LP_LTR_SCALE registers and toggles LP_LTR_EN. This is an implementation choice that differs from Linux (which writes to ACTIVE_LTR registers for active LTR).

> **Validation point**: The short stall/toggle pattern is a Windows implementation detail. Linux `thc_ltr_config()` programs VALUE/SCALE, sets EN bits, then raises REQ bits to generate the LTR message; Linux `thc_ltr_unconfig()` clears the enable/request bits directly. Verify PMC correctly receives LTR messages on both OS paths.

## TIC Power State Enum (Windows Driver — Phase 6)

> **Source**: Windows HIDI2C driver v3.0.0.9000 / HIDSPI driver v4.0.0.9000

The Windows drivers define a formal 8-state enum for TIC (Touch IC) power states:

| Value | State Name | Description |
|-------|-----------|-------------|
| 0 | `NO_OP` | No operation / default |
| 1 | `DOZE` | Reduced sampling rate |
| 2 | `ARMED` | Ready, no finger detected |
| 3 | `SENSING` | Active touch scanning |
| 4 | `SOFT_RESET` | Software reset in progress |
| 5 | `ARM_FOR_WAKE` | Armed for Wake-on-Touch (WoT) |
| 6 | `ACTIVE_LTR_STATE` | Active LTR power state |
| 7 | `LOWPOWER_LTR_STATE` | Low-power LTR state |

> **Validation point**: States 5-7 are Windows-driver-specific management states not directly mapped to HID protocol power commands. `ARM_FOR_WAKE` (5) is written to the TIC during WoT entry. The Linux kernel uses only ON/SLEEP/OFF power commands (HIDI2C) or SET_POWER ON/SLEEP/OFF (HIDSPI).

## Doze / Idle State Machine (Windows)
```
Active → [idle timeout] → ARMED → [doze timeout] → DOZE (LP LTR)
DOZE → [touch interrupt] → Active (Active LTR)
```
- `DEFAULT_DOZE_TIMER_MS = 1000`
- `DEFAULT_IDLE_TIMER_MS = 1000`
- **HIDSPI doze timer window**: 50ms — `bDozeTimerExpiredIn50msWindow` flag gates doze entry. If the doze timer expires but touch activity occurred within the last 50ms, doze entry is deferred. (Phase 6: Windows HIDSPI driver)

## Windows D3Cold Behavior (Phase 6)

> **Source**: Windows HIDI2C driver v3.0.0.9000

- **D3Cold is explicitly disabled** in the Windows HIDI2C driver — `WdfDeviceAssignS0IdleSettings` with `ExcludeD3Cold = WdfTrue`
- The driver only uses D3Hot for runtime idle
- D3Cold (Vnn removal) is handled by the platform/OS power framework, not by the THC driver directly
- **Contrast with Linux**: Linux QuickI2C supports D3Cold via the full 28-register save/restore path

## D0 → D3 Transition (Windows HIDI2C)

**D0ExitPreInterruptsDisabled** (runs before interrupts disabled):
```
KeStallExecutionProcessor(1000µs) → ChangeInterruptState(false) → RxDma2 START=0 → RxDma1 START=0 → SendSetPower(sleep)
```

> **Note**: The 1000µs stall comes **first** (allows in-flight DMA to complete), then interrupts are disabled, then both RXDMA channels are stopped (START=0), and **only then** is `SET_POWER(SLEEP)` sent. This ordering ensures no DMA activity occurs after the sleep command. `SET_POWER(SLEEP)` is sent in `D0ExitPreInterruptsDisabled`, NOT in `D0Exit` itself.

**D0Exit** (HIDI2C):
```
D0Exit: StopDozeTimer → LtrDisable → WaitForRxDMAPause →
        DmaUnconfigure → DmaFree → [D3Final: cleanup]
```

> **D0Exit Optimization (QuickSPI SwAS v1.0 P0770-P0779)**: Steps 1-3 (StopDozeTimer, ChangeInterruptState, WaitForRxDMAPause + SendSetPower) are **skipped** if touch is already disabled (lid close or monitor off scenario). In this case, D0Exit proceeds directly to DmaUnconfigure → DmaFree → D3Final cleanup. This optimization avoids unnecessary device communication when the touch subsystem is already quiesced.

## D0 → D3 Transition (Windows HIDSPI)

**HIDSPI D0Exit** (different from HIDI2C):
```
D0Exit: LtrDisable → DrainRxQueue → DmaUnconfigure → [D3Final: DmaRelease]
```

> **Key difference**: HIDSPI D0Exit does NOT call StopDozeTimer, SendSetPower, or WaitForRxDMAPause. For HIDSPI, `SET_POWER(SLEEP)` is sent in the `EvtNotifyPowerDown` callback (from HidSpiCx), not in D0Exit. LTR is cleared before DMA unconfigure. On D3Final, DMA resources are released.

### HIDSPI: EvtNotifyPowerDown for SET_POWER(SLEEP)

For HIDSPI, `SET_POWER(SLEEP)` is sent via the `EvtNotifyPowerDown` callback provided by the HidSpiCx framework, NOT in D0Exit. This is the key architectural difference from HIDI2C.

### HIDSPI: No Freeze/Thaw/Poweroff/Restore Callbacks

**Windows HIDSPI has no freeze/thaw/poweroff/restore callbacks** — these hibernate PM callbacks are not implemented in the Windows HIDSPI driver.

### M11: D0ExitPreInterruptsDisabled behavior (I2C vs SPI)

M11: Windows HIDI2C sends `SET_POWER(SLEEP)` before interrupts are fully disabled in `D0ExitPreInterruptsDisabled`, while the HIDSPI path sends `SET_POWER(SLEEP)` only in the `EvtNotifyPowerDown` callback (not in D0Exit at all). This difference can change the ordering of remote device state changes during power-down and may require test expectations to account for earlier SET_POWER writes on I2C.

## D3 → D0 Transition (Windows HIDI2C)
```
D3Final exit:  TakeDeviceOutOfReset() → full reset + init
D3 exit:       TakeDeviceOutOfSleep() → DmaAllocate → DmaConfigure → LTR →
               display sync → SendSetPower(on) → coalescing → RearmDozeTimer
```

**Wakeable resume**: In wakeable mode (device maintained power during D3), driver sends SET_POWER(ON) only — no reset command. Reset is skipped because the device preserved its internal state.

## Windows SET_POWER Async Flag-Gated Pattern

Windows `SET_POWER` implementation is asynchronous with a flag-gated filter: the driver sets `bAwaitingSendSetPowerOnResponse = true` before sending SET_POWER(ON), and the response handler clears the flag. Subsequent operations check this flag before proceeding. This is NOT a synchronous wait — it is an async flag-gated filter pattern.

## Windows Idle Support Registry Keys (QuickSPI SwAS v1.0)

The Windows driver uses two INF-configured registry keys to control idle power management:

| Registry Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `EnhancedPowerManagementEnabled` | DWORD | 1 | Master switch for idle PM. `0` = disable idle transitions entirely |
| `EnhancedPowerManagementUseMonitor` | DWORD | 1 | When `1`, idle PM is gated by monitor state (lid open/close, display on/off). When `0`, idle PM runs independently of monitor state |

> **Validation point**: Both keys are set via INF `[AddReg]` directives during driver installation. `EnhancedPowerManagementUseMonitor=1` enables the D0Exit optimization (skip quiesce steps when touch already disabled due to lid close/monitor off). These keys affect both QuickSPI and QuickI2C Windows drivers.

## Windows Idle Notification Power Flow (Phase 7 Audit)

> **Source**: Windows THCBase driver `ThcHid.cpp` — `HandleIdleNotificationRequest` (line 1578+)

The Windows HIDSPI driver uses HID idle notification for runtime power transitions. Key details:

| Aspect | Detail |
|--------|--------|
| Idle handler | `HandleIdleNotificationRequest` follows Microsoft Synaptics Touch sample pattern |
| Execution level | WDF work items at PASSIVE_LEVEL (not DPC) |
| TxQueue gating | TxQueue **stopped** before idle transition, **restarted** after wake |
| Idle request | Pended via `WdfRequestForwardToIoQueue`; completed when device resumes |

**TxQueue stop/start sequence** prevents output reports (SET_FEATURE, OUTPUT_REPORT) from being sent during power transitions. This avoids DMA errors when the device is transitioning to/from low-power state.

> **Validation point**: If output reports are sent during idle transition (race between idle entry and SET_FEATURE), the TxQueue gate should block them. Verify no DMA timeout or BSOD occurs if an output report arrives concurrently with idle notification.

## Windows STALL Detection

Windows drivers implement STALL detection (THC_STALL_TIMEOUT) — if DMA is stuck beyond the timeout the driver forces a device reset. Add validation to ensure this path behaves as expected.
