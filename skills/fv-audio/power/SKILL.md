---
name: fv-audio/power
description: "Audio power management — power wells, PG domains, D0i3/D3 transitions, PLL control, SRAM power gating, LTR/CPPM, S0ix integration"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# Audio Power Management

Validate audio subsystem power management: power wells, power gating domains, D-state transitions, HD Audio PLL control, SRAM power gating, LTR/CPPM, S0ix integration, and codec power coordination.

> **Scope:** ACE power wells (Vnn/VnnAON), power gating domains, D0/D0i3/D3 transitions, HDAPLLCTL, SRAM PGCTL, LTR/CPPM/pNDE, PMC coordination, codec PM.
> **HAS Source:** NVLDP ACE4.x Integration HAS §7 Power Management (Rev 1.2 WIP, Sep 2025)

---

## Multi-Platform Power Management Comparison

| Platform | ACE | PGD Count | SRAM Size | SRAM PG | D0i3 | D3 | S0ix Integration | Notes |
|----------|-----|-----------|-----------|---------|------|-----|------------------|-------|
| **NVL PCD-H** | 4.x | 10 | 4.5 MB | Per-EBB | ✅ | ✅ | Full Chassis 2.2 | Reference implementation |
| **NVL PCH-S** | 4.x | 10 | 2.25 MB | Per-EBB | ✅ | ✅ | Full Chassis 2.2 | Fewer cores → smaller SRAM |
| **PTL** | 3.0 | *(verify HAS)* | — | ✅ | ✅ | ✅ | Chassis 2.x | ACE 3.x PG architecture |
| **WCL** | 3.0 | *(verify HAS)* | — | ✅ | ✅ | ✅ | Chassis 2.x | Same PM architecture as PTL |
| **TTL (ACE 4.0)** | 4.0 | *(verify HAS)* | 3.0 MB | Per-EBB | ✅ | ✅ | Chassis 2.x | Smaller SRAM than NVL PCD-H |
| **TTL (ACE 3.0)** | 3.0 | *(verify HAS)* | 4.6 MB | Per-EBB | ✅ | ✅ | Chassis 2.x | Larger SRAM than ACE 4.0 variant |
| **RZL** | 4.0 | *(verify HAS)* | 4.5 MB | Per-EBB | ✅ | ✅ | Chassis 2.x | Same PM as NVL PCD-H (ACE 4.0) |
| **LNL** | 2.x | *(verify HAS)* | — | ✅ | ✅ | ✅ | Chassis 2.x | Single SOC die |
| **MTL** | 1.5 | *(verify HAS)* | — | ✅ | ✅ | ✅ | Chassis 2.x | RING_OSC clock option for DMIC |
| **ARL** | 1.5 | *(verify HAS)* | — | ✅ | ✅ | ✅ | Chassis 2.x | PCH-based ACE |

> **Cross-platform PM principles:** All platforms share the same fundamental D-state model (D0 → D0i3 → D3) and S0ix integration requirements (ACE in D3, PLL off, SRAM gated, streams stopped, SoundWire clock-stopped, LTR no-req). The detailed PGD layout and SRAM EBB count vary per platform/die.

> **RZL PM debug:** Apply NVL PCD-H PM debug procedures directly — same ACE 4.0 architecture, same SRAM size, same PGD structure. Key RZL-specific differences: PCD-M and PCD-W die variants may have different PG exit latency tuning in `DEVIDLEPOL`.

> **WCL PM debug:** Apply PTL PM debug procedures — same ACE 3.0 architecture. Known shared issues with PTL: BT offload S0ix blocking (see `bt-offload` sub-skill).

---

## Power State Overview

### ACE Device Power States

| State | Description | Clocks | Power | Registers | Resume Latency |
|-------|-------------|--------|-------|-----------|----------------|
| **D0** | Fully operational | All running | Full | All accessible | -- |
| **D0i3** | Deep idle — clock-gated, partial PG | Gated | Reduced | BAR0 accessible, BAR2 may be gated | ~100 us - 1 ms |
| **D3** | Full power-down — OS-initiated | Off | Minimal | PCI config only | ~1-10 ms |

### Power State Transitions

```
D0 <---> D0i3 (autonomous, managed by driver/FW)
D0 <---> D3   (OS-initiated via PMCSR)
D3 ---> D0    (requires full re-init: PLL, SRAM, FW reload)
```

### Why This Matters

- ACE **must** enter D3 when idle for SoC to reach S0ix (Modern Standby)
- PLL must be shut down in D3 to save power
- SRAM must be power-gated in D3 via SRAM-PG (FW context lost)
- All SoundWire links must be in clock-stop mode before D3
- All HDA streams must be stopped before D3
- **D3 exit requires full re-initialization** — PLL lock, SRAM power-up, FW reload

---

## Power Wells (HAS §7.1)

ACE IP uses two core logic power wells on NVLDP:

| Power Well | Voltage | Scope | Off In | Always On Through |
|-----------|---------|-------|--------|-------------------|
| **Vnn** | 0.77V | IOSF interfaces (Primary + Sideband) | S0i2.1+ / Sx / G3 | Active operation only |
| **VnnAON** | 0.77V | Tensilica cores + DSP domain + HD Audio controller/link | G3 only | S0i2.x and Sx |
| **VnnSRAM** | 0.77V | SRAM banks (single-rail, tied to VnnAON on NVLDP) | Per-EBB gating | Same as VnnAON |

- **Vnn↔PMC handshake**: Full `resource_own` req/ack signaling (Intel Chassis 2.2)
- **Core 1 domain**: May be on Vnn or VnnAON depending on `DSPAONC` parameter
- **SRAM LDO**: Not used on NVLDP — VnnSRAM tied directly to VnnAON logic gate power

### PythonSV Power Well Check

```python
# Check power well status via PMC sideband
# Power gating status reflected in PGCB registers
ace = nn.sv.socket0.pcd.ace

# Check if ACE is power-gated
# PMC maintains PG status for each partition
print("=== ACE Power Well Status ===")
pmcsr = ace.cfg.pmcsr.read()
ps = pmcsr & 0x3
print("Device Power State: D%d" % ps)
if ps == 3:
    print("  Vnn: OFF (D3 — IOSF interfaces power-gated)")
    print("  VnnAON: ON (always-on domain still powered)")
elif ps == 0:
    print("  Vnn: ON (active)")
    print("  VnnAON: ON (active)")
```

---

## Power Gating Domains (HAS §7.2)

ACE IP supports up to 17 PGDs. NVLDP implements 10 active PGDs:

| PGD | SoC Partition | Power Well | Function |
|-----|--------------|------------|----------|
| **gated-HST** | PGDA / paracehost | VnnAON | IOSF Primary/Sideband, DSP I/O peripherals (host domain), HD Audio controller |
| **gated-HUB-HP** | PGDB / paracemem | VnnAON | Subsystem fabric + L2 local memory (high performance) |
| **gated-DSP-HP0** | PGDC1 / paracehpdspa | VnnAON | DSP Core 0 (high performance) |
| **gated-DSP-HP1** | PGDC2 / paracehpdspb | VnnAON | DSP Core 1 (high performance) |
| **gated-DSP-HP2** | PGDC3 / paracehpdspc | VnnAON | DSP Core 2 (high performance) |
| **gated-DSP-HP3** | PGDC4 / paracehpdspd | VnnAON | DSP Core 3 (high performance) |
| **gated-ML-ANNA** | PGDM0 / paracehost | VnnAON | HW DSP Accelerator (ML/ANNA block) |
| **gated-HUB-ULP** | PGDD / paracehubio | VnnAON | Subsystem fabric + L2 local memory (ultra low power) |
| **gated-IO-0** | PGDIO0 / paracehubio | VnnAON | HD Audio link + DSP I/O peripherals (ULP domain, instance 0) |
| **gated-IO-1** | PGDIO1 / paracehubio | VnnAON | HD Audio link + DSP I/O peripherals (ULP domain, instance 1) |

**NVLDP PGD Config:** `PGDSPULP=0` (ULP DSP disabled), `PGHUBHP=1` (HUB-HP enabled), `PGIOC=2` (2 I/O PGDs), `DEFPFOL=0` (disabled), `DEFIPGIW=4` (16 AONROSC cycles wake interval)

### Usage Model → PGD State Matrix

| Use Case | HST | HUB-HP | HUB-ULP | IO-0/1 | DSP-HP0 | DSP-HP1+ | ML |
|----------|-----|--------|---------|--------|---------|----------|-----|
| **HD Audio only** | ON | ON | ON | ON | OFF | OFF | OFF |
| **WoV (Wake on Voice)** | OFF | OFF | ON | OFF | periodic | OFF | periodic |
| **Low-power playback** | ON | OFF | ON | ON | ON | OFF | OFF |
| **UAOL/GAOL offload** | ON | ON | ON | OFF | ON | ON | OFF |
| **D0i3 snooze / D3** | OFF | OFF | OFF | OFF | OFF | OFF | OFF |

### PGCB (Power Gate Control Block)

NVLDP uses **Intel Chassis 2.0 PGCB** (`CHASSISPGCBMOD=1`). Each PGD has an associated PGCB controller that interfaces with PMC via sideband req/ack protocol.

- L1/L2 SRAM EBBs have **individual per-EBB power gating** — NOT affected by PGD states above
- PG exit latency configured in `DEVIDLEPOL` register (BIOS-programmed)

### CGCTL (Clock Gating Control)

The **CGCTL** register controls trunk and dynamic clock gating for the ACE/HD Audio IP:

- **Trunk Clock Gating** (`MISCBDCGE` bit) — gates the backbone clock when IP is idle
- **Dynamic Clock Gating** — per-module clock gating within DSP, DMA, and link controllers
- CGCTL must be properly configured before D0i3 entry — incorrect clock gating settings can prevent power state transitions or cause hangs on D0i3 exit
- BIOS programs default CGCTL values; driver may override during runtime for debug

---

## Enhanced D-State Behaviors (HAS §7.3)

### D3hot/D3cold

Supported. DSP-only WoV can continue running even while ACE PCI device reports D3 (WoV uses VnnAON domain which stays powered through Sx).

### D0i3 — Deep Idle Sub-State

D0i3 is a PCI **sub-state of D0** — not a separate PCI power state:

- If DSP FW is alive and managing idle, D0i3 from SW adds **no extra power savings** (FW already knows idle)
- For **legacy HD Audio driver** (no DSP FW, Coupled Mode), D0i3 is still needed for power savings
- D0i3 entry/exit signaled via `D0I3C` register (BAR0)
- On D0i3 exit, all PGDs must be restored before register access

### DMI L1 Residency

Supported. HD Audio DMA is **optimized for long DMI L1 residency** via deep buffering:
- 1ms HD Audio buffer → ~100μs LTR default → allows platform to enter DMI L1 between buffer refills
- Deeper buffering = longer DMI L1 windows = more SoC power savings

### CPPM (Chassis Power & Performance Management)

Intel Chassis 2.2 compliant. Uses `QoS_DMD` (Quality of Service Demand) for resource-specific LTR:
- Each IP resource can assert independent latency demands
- PMC aggregates all QoS_DMD signals to determine deepest achievable SoC idle state

### pNDE (Periodic Next Device Event)

ACE registers **periodic events with PMC** for audio processing wakeups:
- PMC ensures target power state is achieved before timer tick
- Used for periodic audio frame processing (e.g., 10ms WoV frames)
- Eliminates jitter from async wake → deterministic wake timing

### DDR Access Latency

NVLDP memory access characteristics:
- **Best case**: ~350 ns DDR access latency
- **Typical**: ~600 ns DDR access latency
- SoC **speeds up fabric** whenever ACE asserts `ddr_own_req` (automatic performance boost)

---

## PMCSR — PCI Power Management

### Register Layout

Located in PCI config space at PM Capability offset (0x84 on NVL):

| Bits | Field | Description |
|------|-------|-------------|
| [1:0] | PowerState | `00b`=D0, `01b`=D1, `10b`=D2, `11b`=D3hot |
| [8] | PME_En | Enable PME generation |
| [15] | PME_Status | PME asserted (write-1-to-clear) |

### PythonSV Power State Check

```python
import namednodes as nn
nn.sv.refresh()

ace = nn.sv.socket0.pcd.ace  # PCD-H
# ace = nn.sv.socket0.pch.ace  # PCH-S

pmcsr = ace.cfg.pmcsr.read()
ps = pmcsr & 0x3
pme_en = (pmcsr >> 8) & 1
pme_sts = (pmcsr >> 15) & 1

power_states = {0: "D0", 1: "D1", 2: "D2", 3: "D3hot"}
print("PMCSR: 0x%04X" % pmcsr)
print("  PowerState: %s (%d)" % (power_states.get(ps, "Unknown"), ps))
print("  PME_En:     %d" % pme_en)
print("  PME_Status: %d" % pme_sts)

if ps == 0:
    print("Device is in D0 — fully operational")
elif ps == 3:
    print("Device is in D3 — low power, registers not accessible")
    print("To bring to D0: Write PMCSR[1:0]=00")
```

### D3 Entry Procedure

1. **Stop all streams** — SDnCTL.RUN=0 for all active streams
2. **Stop CORB/RIRB** — CORBCTL.DMA_RUN=0, RIRBCTL.DMA_RUN=0
3. **Clock-stop SoundWire links** — Send clock stop to all active segments
4. **Idle DSP** — Stop pipelines, stall cores
5. **Gate SRAM** — Power gate SRAM banks via SRAM PGCTL
6. **Shut down PLL** — Disable HD Audio PLL via HDAPLLCTL
7. **Write PMCSR** — Set PowerState to D3 (PMCSR[1:0]=11)

### D3 Exit Procedure

1. **Write PMCSR** — Set PowerState to D0 (PMCSR[1:0]=00)
2. **Wait for PLL lock** — HDAPLLCTL indicates PLL is locked
3. **Power up SRAM** — Clear SRAM PGCTL power gate bits
4. **Re-initialize controller** — GCTL.CRST cycle (0->1)
5. **Reload DSP firmware** — FW context was lost in D3
6. **Re-enumerate codecs** — STATESTS, SoundWire enumeration
7. **Restore stream configuration** — Recreate pipelines, streams

---

## HD Audio PLL Control (HDAPLLCTL)

The HD Audio PLL generates the clock tree for all audio subsystems.

### Register Location

HDAPLLCTL is in the BAR0 register region.

### PLL States

| State | Description |
|-------|-------------|
| **PLL On / Locked** | Normal operation — audio clocks running |
| **PLL Off** | D3 / low-power — no audio clocks |
| **PLL Locking** | Transitional — after D3 exit, PLL acquiring lock |

### PLL Verification

```python
# Check PLL status
# hdapllctl = ace.bar0.hdapllctl.read()
# print("HDAPLLCTL: 0x%08X" % hdapllctl)

# Check PLL lock status bit
# pll_locked = (hdapllctl >> <lock_bit>) & 1
# print("PLL Lock: %s" % ("Locked" if pll_locked else "NOT LOCKED"))

print("=== HD Audio PLL Status ===")
print("(Register path and bit layout from ACE HAS)")
```

### PLL Troubleshooting

| Symptom | Cause | Action |
|---------|-------|--------|
| PLL not locking after D3 exit | Clock source issue, reference clock missing | Check platform clock source, wait longer for lock |
| PLL timeout | Silicon issue or wrong config | Verify HDAPLLCTL settings against HAS |
| Audio clock jitter | PLL parameters misconfigured | Check PLL divider/multiplier settings |

---

## SRAM Power Gating (HAS §7.4)

### Architecture

SRAM power gating operates at the **individual EBB (Embedded Block RAM) level** — independent from PGD (Power Gating Domain) states. Each L1/L2 SRAM EBB has its own power gate control.

NVLDP SRAM power configuration is managed via `PTDC` register (BIOS-programmed):
- **Logic gate PG**: Controlled per-PGD
- **SRAM PG**: Per-EBB granularity
- **SRAM retention**: Selectable per-bank (retain context in low-power vs full gate)

BAR2 page size (`DfL2MPAT.PGSZ`) must coordinate with ACE IMR allocation:
- Max 48 MB on ACE 4.x
- Use **4 KB page-size** for allocations ≤64 MB

### SRAM PGCTL Register

Located in the BAR2 region (requires GPROCEN=1):

```python
# SRAM Power Gate Control
# Each bit controls one SRAM bank
# 0 = Bank powered ON
# 1 = Bank power GATED (contents lost!)

# Read current status
# sram_pgctl = <read SRAM PGCTL>
# print("SRAM PGCTL: 0x%08X" % sram_pgctl)

# Power up all banks (for FW load):
# <write SRAM PGCTL = 0x00000000>

# Power gate all banks (for D3):
# <write SRAM PGCTL = 0xFFFFFFFF>
```

### SRAM Configuration

| Die | SRAM Size | Banks | Usage |
|-----|----------|-------|-------|
| **PCD-H** | 4.5 MB | Multiple | FW code + data for 4 HP + 1 ULP cores |
| **PCH-S** | 2.25 MB | Multiple | FW code + data for 2 HP + 1 ULP cores |

### SRAM Power Gating Rules

1. **ALWAYS power up SRAM before FW load** — write is lost if bank is gated
2. **ALWAYS power gate SRAM in D3** — saves significant power
3. **FW context is lost** when SRAM is power-gated — full FW reload required on D3 exit
4. **Partial power gating** possible — gate unused banks while keeping active pipeline banks powered
5. **GPROCEN must be 1** to access SRAM PGCTL register
6. **Per-EBB granularity** — individual SRAM blocks can be gated independently of PGDs (HAS §7.4)
7. **SRAM retention mode** — some banks can retain data in low-power mode (configured via `PTDC`)

---

## Latency Tolerance Reporting (LTR)

### Overview

LTR tells the platform how much latency the audio device can tolerate for power management.

### LTR Register

LTRC (LTR Capability) is in the PCIe extended capability space.

| Field | Description |
|-------|-------------|
| **Snoop Latency** | Max tolerable latency for snooped transactions |
| **No-Snoop Latency** | Max tolerable latency for non-snooped transactions |

### LTR Values and Impact

| LTR Setting | Impact | Use Case |
|-------------|--------|----------|
| **Low latency** (< 1ms) | Platform cannot enter deep C-states | Active streaming, low-latency audio |
| **Medium latency** (1-10ms) | Platform can enter some C-states | Idle but codec active |
| **High latency / No-req** | Platform can enter deepest C-states | Audio fully idle, ready for S0ix |

### Verification

```python
# Read LTR values from PCIe extended capability
# Check if LTR values are appropriate for current audio state:
# - Active streaming: expect low latency
# - Idle: expect high latency or LTR no-requirement
# - D3: LTR should not block platform idle

print("=== LTR Status ===")
# ltrc = <read LTRC register>
# print("LTRC: 0x%08X" % ltrc)
print("(LTR register access from PCIe capability)")
```

---

## S0ix Integration

### S0ix Requirements for Audio

For the platform to enter S0ix (Modern Standby), the audio subsystem must meet ALL of these conditions:

| Requirement | Verification |
|-------------|-------------|
| ACE in D3 | PMCSR[1:0] = 11 |
| PLL shut down | HDAPLLCTL indicates PLL off |
| SRAM power-gated | SRAM PGCTL = all banks gated |
| All streams stopped | SDnCTL.RUN = 0 for all streams |
| SoundWire in clock-stop | All SDW links clock-stopped |
| LTR no-requirement | LTR set to max / no-requirement |
| No pending interrupts | INTSTS = 0 |

### S0ix Blocker Detection

```python
# Check if audio is blocking S0ix entry

print("=== Audio S0ix Blocker Check ===")

ace = nn.sv.socket0.pcd.ace  # or .pch for PCH-S

# 1. Check power state
pmcsr = ace.cfg.pmcsr.read()
ps = pmcsr & 0x3
print("Power State: D%d %s" % (ps, "OK" if ps == 3 else "BLOCKING — not in D3"))

# 2. Check GCTL
gctl = ace.bar0.gctl.read()
crst = gctl & 0x1
print("GCTL CRST: %d %s" % (crst, "OK (reset)" if crst == 0 else "WARN — controller running"))

if ps == 0:
    # Device in D0 — check what's keeping it active
    
    # 3. Check active streams
    # intsts = ace.bar0.intsts.read()
    # print("INTSTS: 0x%08X" % intsts)
    
    # 4. Check PPCTL (DSP)
    ppctl = ace.bar0.ppctl.read()
    gprocen = (ppctl >> 30) & 1
    print("GPROCEN: %d %s" % (gprocen, "WARN — DSP enabled" if gprocen else "OK"))
    
    # 5. Check STATESTS (codec activity)
    statests = ace.bar0.statests.read()
    print("STATESTS: 0x%04X" % statests)
    
    print("\nACTION: Investigate why audio is still in D0")
    print("  - Active audio stream?")
    print("  - Codec keeping link active?")
    print("  - Driver not releasing device?")
    print("  - BIOS/ACPI _PS3 method failing?")
else:
    print("\nAudio in D3 — NOT blocking S0ix")
```

---

## Codec Power Management

### HDA Codec Power States

HDA codecs support per-node power states via verbs:

| Node Power State | Description |
|-----------------|-------------|
| D0 | Fully operational |
| D1 | Intermediate low power |
| D2 | Lower power, slower resume |
| D3 | Lowest power (node level) |
| D3cold | Completely off (codec level) |

### Codec PM Coordination

1. **Before ACE D3:** All codec nodes should be in D3
2. **Codec D3cold:** Codec can be completely powered off (external power control)
3. **SoundWire clock-stop:** Codecs must acknowledge clock stop before link stops
4. **Wake capability:** Configure codec pins for jack detect wake in D3

### Verification

```python
# Verify codec power state via HDA verbs
# Get Power State verb: 0xF05 (to each function group node)
# Expected: D3 (0x03) when system is idle

# For SoundWire codecs: verify clock-stop acknowledgment
# Read SoundWire slave status for each codec
```

---

## Power Management Verification Checklist

| Check | Register / Method | Expected (Idle) | Expected (Active) |
|-------|------------------|-----------------|-------------------|
| ACE Power State | PMCSR[1:0] | D3 (0x3) | D0 (0x0) |
| Controller Status | GCTL.CRST | 0 (reset) | 1 (running) |
| DSP Enable | PPCTL.GPROCEN | 0 (disabled) | 1 (enabled) |
| PLL Status | HDAPLLCTL | Off | Locked |
| SRAM Power | SRAM PGCTL | All gated | Active banks on |
| Streams | SDnCTL.RUN | All stopped | Active streams running |
| Interrupts | INTSTS | 0 | May have pending |
| LTR | LTRC | Max/No-req | Low latency |
| SoundWire | SHIM LCTL | Clock-stopped | Links active |
| Codecs | Verb 0xF05 | D3 | D0 |

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| D3 entry timeout | Active stream or pending IRQ | Check all stream RUN bits, INTSTS |
| PLL not locking on D3 exit | Reference clock missing | Check platform clock, wait for lock |
| S0ix blocked by audio | ACE not in D3 | Run S0ix blocker check above |
| SRAM access after D3 | Bank still power-gated | Check SRAM PGCTL, power up needed banks |
| FW crash after D3 exit | FW reload incomplete | Verify SRAM powered, IPC handshake |
| High idle power | LTR too aggressive, partial D state | Check LTR values, verify full D3 |
| Codec not waking | Wake pin not configured | Check codec pin sense, PME config |
| SoundWire resume fail | Clock-stop exit sequence wrong | Verify SHIM clock resume, codec sync |

---

## See Also

- **[fv-audio/clocking](../clocking/SKILL.md)** — Audio PLL, XTAL, CRO clock sources powering audio subsystem
- **[fv-audio/dsp](../dsp/SKILL.md)** — DSP core power states, SRAM power gating dependencies
- **[fv-audio/soundwire](../soundwire/SKILL.md)** — SoundWire clock-stop power management
- **[fv-audio/hda](../hda/SKILL.md)** — HDA controller power states, codec wake signaling
- **[fv-audio/wov](../wov/SKILL.md)** — Wake on Voice CRO ultra-low-power mode, S0ix integration
- **[fv-audio/platform](../platform/SKILL.md)** — Per-platform power domains, PMC addresses, D-state mappings
- **[power/windows.md](windows.md)** — Windows audio power management, RTD3, D3 transitions
