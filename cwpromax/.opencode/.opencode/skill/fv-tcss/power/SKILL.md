# TCSS Power Management — D-states, Power Gating, and Wake-on-Connect

## Overview

This sub-skill covers TCSS power management validation including D-states, power gating, S0ix integration, wake-on-connect, and runtime power management.

## Power Management Architecture

### TCSS Power Domains

```
┌──────────────────────────────────────────┐
│         TCSS Power Architecture          │
│  ┌───────────────────────────────────┐   │
│  │   Active Domain (D0)              │   │
│  │   • Full functionality            │   │
│  │   • All controllers active        │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Low Power Domain (D3)           │   │
│  │   • Controllers power-gated       │   │
│  │   • Wake logic active             │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Always-On Domain                │   │
│  │   • Wake detection                │   │
│  │   • PMC interface                 │   │
│  └───────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

## D-States (Device Power States)

### D-State Definitions

| D-State | Description | Power Consumption | Wake Capability |
|---------|-------------|-------------------|-----------------|
| **D0** | Fully operational | High (~100-500 mW) | N/A (already on) |
| **D1** | Light sleep (optional) | Medium | Fast wake |
| **D2** | Deep sleep (optional) | Low | Medium wake |
| **D3hot** | Power-gated, bus active | Very low (~1-10 mW) | Wake via bus |
| **D3cold** | Power removed | Zero | Wake via sideband |

### D-State Transitions

```
D0 (Active)
  ↕ (Runtime suspend/resume)
D3hot (Power-gated)
  ↕ (System suspend/resume)
D3cold (Power off)
```

**Transition Timing:**
- **D0 → D3hot:** <100 ms
- **D3hot → D0:** <200 ms
- **D3hot → D3cold:** <50 ms
- **D3cold → D0:** <500 ms

## Power Gating

### Clock Gating

Clock gating reduces power when functional units are idle:

| Component | Clock Gating Benefit |
|-----------|---------------------|
| USB4 Router | ~20-30% power reduction |
| IOM | ~10-15% power reduction |
| DMA Engine | ~30-40% power reduction |

### Power Gating

Power gating completely removes power to idle blocks:

| Component | Power Gating Benefit |
|-----------|---------------------|
| USB4 Router | ~80-90% power reduction |
| Thunderbolt Controller | ~70-80% power reduction |
| PCIe Adapter | ~85-95% power reduction |

### Power Gating Flow

1. **Idle Detection** — No activity on TCSS for timeout period
2. **Save Context** — Save TCSS register state
3. **Quiesce Controllers** — Ensure no pending transactions
4. **Power Gate** — Remove power to TCSS domain
5. **Enter D3hot** — Report D3hot to OS/PMC

**Restore Flow:**
1. **Wake Event** — Cable connect or system resume
2. **Power Ungate** — Restore power to TCSS
3. **Restore Context** — Restore register state
4. **Resume Controllers** — Re-enable TCSS controllers
5. **Enter D0** — Report D0 to OS/PMC

## S0ix (Modern Standby) Integration

### S0ix Entry Requirements

For TCSS to allow S0ix entry:
- [ ] All TCSS ports in D3 (or no device connected)
- [ ] No active data transfers
- [ ] Wake-on-connect configured (if required)
- [ ] PMC notified of TCSS idle state

### S0ix Exit Triggers

TCSS can wake system from S0ix on:
- **Cable connect** — New Type-C device plugged in
- **HPD assertion** — Display connect event
- **PMC wake** — System-initiated wake

## Wake-on-Connect

### Wake Architecture

Wake-on-connect allows TCSS to wake system when device connects:

```
Type-C Cable Connect
  ↓
CC Detection (Always-on logic)
  ↓
Wake Signal to PMC
  ↓
PMC Wakes System (S0ix → S0)
  ↓
TCSS Enumerates Device
```

### Wake Configuration

| Setting | Description |
|---------|-------------|
| **Wake Enable** | Enable/disable wake-on-connect |
| **Wake Source** | Which ports can wake (Port 0/1/both) |
| **Wake Filter** | Filter spurious wake events |

## Runtime Power Management (RTD3)

### RTD3 Overview

Runtime D3 (RTD3) allows TCSS to enter D3 while system is in S0:

**Benefits:**
- Reduces idle power consumption
- Extends battery life
- Maintains system responsiveness (fast wake)

### RTD3 Policy

| Condition | Action |
|-----------|--------|
| No device connected | Enter D3 after timeout (typically 2-5 seconds) |
| Device connected, idle | Enter D3 after timeout (typically 30-60 seconds) |
| Active data transfer | Remain in D0 |
| Wake event | Resume to D0 within 200 ms |

## TCSS Power Registers

> **CRITICAL:** Always verify register offsets against platform HAS.

| Register | Offset | Description |
|----------|--------|-------------|
| TCSS_PWR_CTRL | Query HAS | Power control — D-state transitions |
| TCSS_PWR_STATUS | Query HAS | Current power state |
| TCSS_WAKE_EN | Query HAS | Wake-on-connect enable |
| TCSS_CLK_GATE | Query HAS | Clock gating control |
| TCSS_PWR_GATE | Query HAS | Power gating control |

## Validation Points

### D-State Transitions

- [ ] D0 → D3hot transition completes within 100 ms
- [ ] D3hot → D0 transition completes within 200 ms
- [ ] Context save/restore works correctly
- [ ] No data loss during D-state transitions

### Power Gating

- [ ] Clock gating reduces power measurably
- [ ] Power gating achieves >80% power reduction
- [ ] Controllers resume correctly after power gating
- [ ] No functional issues after multiple power cycles

### S0ix Integration

- [ ] TCSS allows S0ix entry when idle
- [ ] TCSS blocks S0ix when active
- [ ] Wake-on-connect from S0ix works
- [ ] S0ix residency not impacted by TCSS

### RTD3

- [ ] TCSS enters D3 after idle timeout
- [ ] TCSS resumes quickly on activity (<200 ms)
- [ ] Multiple D3 entry/exit cycles stable
- [ ] Data transfer resumes correctly after RTD3 wake

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| S0ix entry blocked | TCSS not entering D3, active transfer | Check TCSS power state, verify idle detection |
| Wake-on-connect not working | Wake enable not set, PMC config issue | Verify wake enable, check PMC settings |
| Slow resume from D3 | Context restore slow, FW initialization delay | Measure resume time, check FW version |
| Device not working after D3 | Context restore incomplete, power sequencing issue | Verify context save/restore, check power rails |
| High idle power | Clock/power gating not active | Check gating status, verify policy settings |

## Debug Tools

### Linux

```bash
# TCSS power state
cat /sys/bus/pci/devices/0000:*/power/runtime_status

# Runtime PM control
echo auto > /sys/bus/pci/devices/0000:*/power/control

# S0ix residency
cat /sys/kernel/debug/pmc_core/slp_s0_residency_usec

# Wake sources
cat /sys/kernel/debug/wakeup_sources
```

### Windows

```powershell
# Device power state
powercfg /devicequery wake_armed

# S0ix diagnostics
powercfg /sleepstudy

# Power configuration
powercfg /requests
```

### PythonSV

```python
# TCSS power registers (example — verify against HAS)
tcss_pwr = getattr(target, "tcss_power")
pwr_state = tcss_pwr.status.read()
wake_en = tcss_pwr.wake_enable.read()
clk_gate = tcss_pwr.clock_gate.read()

print(f"Power State: 0x{pwr_state:08X}")
print(f"Wake Enable: {wake_en}")
print(f"Clock Gate: 0x{clk_gate:08X}")
```

## Power Measurement

### Power Consumption Targets

| State | Target Power | Measurement Method |
|-------|--------------|-------------------|
| D0 (idle) | <200 mW | Multimeter on power rail |
| D0 (active) | <500 mW | Multimeter on power rail |
| D3hot | <10 mW | Multimeter on power rail |
| D3cold | <1 mW | Multimeter on power rail |

### S0ix Impact

TCSS power in S0ix:
- **Target:** <5 mW total platform impact
- **Measurement:** S0ix power delta with/without TCSS

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — Power management registers
- **ACPI Spec:** ACPI Specification — D-state definitions
- **PMC Spec:** Platform PMC specification — S0ix integration

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
