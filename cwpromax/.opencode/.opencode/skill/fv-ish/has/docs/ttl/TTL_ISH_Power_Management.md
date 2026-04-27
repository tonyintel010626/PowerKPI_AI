# TTL ISH Power Management (from ISH5p9 HAS)

> **Source**: Co-De Sign AI query against `SIP_ISH5p9_HAS.html` (My Files)
> **Date**: 2026-03-16
> **Platforms**: NVL (Nova Lake) — PCD-H, PCD-S, PCH-S

---

## 1. Power States

| State | Description | Entry Condition | Exit Condition |
|-------|-------------|-----------------|----------------|
| **D0** (Active) | Full operation, all clocks/power enabled | Host/sensor activity | Idle timeout |
| **D0i1** (Idle) | Reduced activity, some blocks clock gated | Short idle period | Activity resumes |
| **D0i2** | Most blocks power gated, state retention enabled | Extended idle, CDC timer expires | Wake event |
| **D0i3** (Wake-only) | SRAMs power gated, content saved to DRAM, minimal logic for wake | S0ix wake-only, explicit SW/HW trigger | Wake event / host request |
| **D3** (Off) | All blocks powered down, no retention | Host shutdown / deep sleep | Host resumes / platform reset |

## 2. Clock & Power Gating

- Clock gating for all major blocks during idle/low-power
- Dynamic power gating coordinated by FW and PMC with state retention for rapid resume
- State retention in AON RF SRAM or saved to DRAM

## 3. SRAM Retention & Per-Bank Power Gating

- Up to **20 instances** of 32KB SRAMs (**640KB total**), independently power gated/ungated
- **AON RF SRAM (8KB)** for deep power states (D0i2/D0i3) retention
- ISH FW sends sideband to PMC: **opcode 0x6Fh, tag 0x06h** reporting ungated SRAM count for energy accounting

## 4. PMC Interaction

- IOSF sideband endpoint-specific posted messages to PMC
- PMC FW updates energy accounting based on ISH SRAM gating state
- Coordinates power state transitions
- ISH reports SRAM gating state changes via sideband messages

## 5. Wake Sources

- Sensor activity (motion, proximity)
- Timer events
- GPIO interrupts
- UART activity
- IPC messages
- Configurable per-sensor/event wake triggers
- Host wake support from low-power states

## 6. S0ix Behavior (Always-On Always-Sensing)

- ISH remains **operational in S0ix** (always-on, always-sensing)
- Samples sensor data, processes fusion, can wake host
- Enters D0i2/D0i3 as lowest power states in S0ix
- Active sensor monitoring continues without host involvement

## 7. Power Management Registers

| Offset | Name | Description | Bit Fields |
|--------|------|-------------|------------|
| `0x500` | Power Control | Power gating control | [0] Enable, [1] Clock Gate, [2] Power Gate, [3] Retention Enable |
| `0x504` | Power Status | Current power state | [0:3] Current D-state, [4] Retention Active |
| `0x508` | Wake Event Config | Wake source enable | [0:7] Sensor wake enable, [8:15] GPIO wake enable |
| `0x50C` | SRAM Gating Control | Per-bank SRAM gating | [0:19] Per-bank gating, [20] Retention enable |
| `0x510` | PMC Sideband Status | PMC communication | Last reported SRAM state, message status |

## 8. PMC Sideband Message Format

```
ISH -> PMC Sideband (SRAM Gating Report):
  Opcode: 0x6Fh
  Tag:    0x06h
  Data:   Number of ungated SRAM banks (0-20)
  Purpose: Energy accounting — PMC adjusts power budget based on ISH SRAM usage
```

---

## Referenced Sources

- `nvl_pcds_energy_reporting_has.html`
- `NVL_PCH_Energy_Reporting_HAS.html`
- `sip_thc_4x_has.html`
- `soc_s0ix_substates_has.html`
- `cnv_integration_has-draco.html`
- `novalake_platform_firmware_architecture_specification.html`
