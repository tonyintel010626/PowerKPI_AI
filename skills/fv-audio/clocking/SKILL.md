---
name: fv-audio/clocking
description: "ACE Audio Clocking Architecture — clock sources, gating, integrated CRO/PLL, DSP clock domains, and XTAL/WoV/Audio PLL configuration"
version: "1.1.0"
author: FV-Audio Team
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
ip: ACE 1.5 / 2.x / 3.0 / 4.x
tags: [audio, clocking, PLL, CRO, XTAL, WoV, clock-gating, NVLDP, DSP]
source: "NVLDP ACE4.x Integration HAS Rev 1.2 §6"
owner: huiyingt
---

# ACE Audio Clocking Architecture

> **Scope**: Clock source hierarchy, clock gating control, integrated CRO/PLL architecture, DSP clock domain selection, and XTAL/WoV/Audio PLL configuration for ACE 4.x on NVL (Nova Lake). Critical for understanding audio I/O timing, low-power DSP operation, and S0ix clock requirements.
>
> **Source**: NVLDP ACE4.x Integration HAS Rev 1.2, §6 Clocking

---

## Clock Source Hierarchy

ACE IP receives clocks from the SoC. On NVLDP, these are the **active** clock sources:

### Active Clocks (NVLDP)

| Clock | Frequency | SoC Source | Power-Up Time | Power | Purpose |
|-------|-----------|-----------|---------------|-------|---------|
| **rsm_clk** | 32.768 kHz | RTC oscillator | Always on | ~0 | Resume well, always-on timing (mandatory) |
| **aon_clk** | 2.560273 MHz | RTC PLL | 900 µs | 50 µW | AON ring oscillator — PM + AON operations (mandatory) |
| **xosc_clk** | 38.4 MHz | XTAL oscillator | 1 ms | 5 mW | Low-power audio I/O — DMIC, SoundWire (mandatory) |
| **wovc_clk** | 38.404096 MHz | RTC PLL | 900 µs | 50 µW | Ultra-low-power WoV DSP processing (CLKWOVROSCE=1) |
| **acepll_clk** | 614.4 MHz | ACE PLL | 25 µs | 5.3 mW | Full-performance DSP + I/O (CLKINTE=1, CLKINTHP=1) |
| **apll_clk** | 96 MHz | IMG PLL | 20 µs | 300 µW | High-performance audio I/O — HDA link, SSP (CLKAPLLE=1) |
| **prim_clk** | 250 MHz | Fabric PLL | 20 µs | 7 mW | IOSF Primary fabric clock |
| **side_clk** | 100 MHz | SoC PLL | 20 µs | 300 µW | IOSF Sideband clock |
| **I2S/PCM clk** | 12.288 MHz | External | — | — | BT Audio Offload SSP device clock |

### Disabled Clocks (NVLDP — Not Connected)

| Clock | Reason |
|-------|--------|
| hpcro_clk, lpcro_clk, sio_clk, hsio_clk | Supplied internally by ACE PLL dividers |
| vdphyclk, vdphyslowclk, vcamrefclk | Vision/CSI disabled (CSILC=0) |
| card_clk | Cardinal clock disabled (CLKACE=0) |
| axi_clk | AXI/AHB disabled (AHIE=0) |

---

## Clock Domain Architecture

```
  ┌──────────────────────────────────────────────────────────┐
  │                    SoC Clock Sources                      │
  ├──────────┬───────────┬──────────┬───────────┬────────────┤
  │  RTC     │  XTAL     │  ACE PLL │ Audio PLL │  Fabric    │
  │ 32.768kHz│ 38.4 MHz  │ 614.4MHz │  96 MHz   │  250 MHz   │
  └────┬─────┴─────┬─────┴────┬─────┴─────┬─────┴──────┬─────┘
       │           │          │           │            │
  ┌────▼────┐ ┌────▼────┐ ┌──▼───┐  ┌────▼────┐  ┌───▼────┐
  │ rsm_clk │ │xosc_clk │ │ PLL  │  │apll_clk │  │prim_clk│
  │ (AON)   │ │ (DMIC,  │ │Divs  │  │ (HDA,   │  │side_clk│
  │         │ │  SdW)   │ │      │  │  SSP)   │  │(fabric)│
  └─────────┘ └─────────┘ ├──────┤  └─────────┘  └────────┘
                          │DSP HP│
       ┌──────────┐       │DSP LP│
       │ aon_clk  │       │ I/O  │
       │ 2.56 MHz │       │ WoV  │
       │(PM, AON) │       │ Card │
       └──────────┘       └──────┘
           │
       ┌───▼──────┐
       │ wovc_clk │
       │ 38.4 MHz │
       │(WoV DSP) │
       └──────────┘
```

---

## Integrated CRO/PLL (NVLDP)

On NVLDP, the ACE uses a **PLL** (not CRO) that physically resides in the SoC (CLKINTHP=1). The ACE IP contains only **programmable dividers**.

| Parameter | NVLDP Value | Description |
|-----------|-------------|-------------|
| CLKINTHVER | 1 | PLL mode (not CRO) |
| CLKINTHP | 1 | PLL is physically in SoC (external to ACE IP) |
| VCO Frequency | 614.4 MHz | Base frequency, selectable via FVS |
| Power Rail | VnnAON iCLK (1.05V) | PLL on always-on rail |
| Digital Rail | VnnAON (0.75V in S0ix) | Clock switching logic |

### DSP FW Clock Control

DSP FW can change VCO frequency via `INTCLKCTL.FVS` (2-bit field → wire to PLL):

| FVS | VCO Frequency | Use Case |
|-----|---------------|----------|
| 00 | 614.4 MHz | Default / full performance (NVL ACE 4.x) |
| 01 | Platform-specific¹ | Intermediate performance |
| 10 | Platform-specific¹ | Low power operation |
| 11 | Platform-specific¹ | Ultra low power |

> ¹ FVS frequency mapping is platform-specific. PTL ACE 3.0 uses 442.368 / 221.184 MHz. Consult the platform ACE Integration HAS `§6 Clocking` for your target platform's FVS frequency table.

### Clock Request Protocol

PLL uses **Intel Chassis 2.2** `clock_own_req`/`clock_own_ack` handshake:

```python
# Check ACE PLL clock status
intclkctl = soc.ace.hda.bar4.intclkctl.read()
fvs = (intclkctl >> 0) & 0x3  # Frequency VCO Select
print(f"INTCLKCTL={intclkctl:#010x}  FVS={fvs} (VCO freq select)")

# Check clock gating control
clkctl = soc.ace.hda.bar4.clkctl.read()
print(f"CLKCTL={clkctl:#010x}")
```

### Default Dividers (NVLDP)

| Output | Divider | Result |
|--------|---------|--------|
| DSP Core | Bypass (÷1) | 614.4 MHz |
| I/O | ÷3 | 204.8 MHz |
| WoV | N/A | Uses wovc_clk directly |
| Cardinal | ÷25 | ~24.576 MHz |

---

## Clock Gating

Clock gating is controlled at two levels:

### 1. Module-Local Clock Gating

Individual IP modules gate their own clocks when idle. Controlled by the `CLKCTL` register.

### 2. Trunk Clock Gating

Fabric-level trunk gating controlled by `FNCFG.CGD` (Clock Gating Disable):

| FNCFG.CGD | Behavior |
|-----------|----------|
| 1 (default at reset) | Clock gating **disabled** — all clocks run continuously |
| 0 (set by BIOS) | Clock gating **enabled** — normal operation |

**BIOS init sequence:**
1. During platform reset: `FNCFG.CGD=1` (clocks ungated for initialization)
2. After ACE init complete: BIOS clears `FNCFG.CGD=0` to enable gating
3. Alternative: `DCGE` soft strap can control default gating state

**Function disable (ACE disabled by BIOS):**
- Set `FNCFG.ACED=1` (ACE disable)
- Clear `FNCFG.CGD=0` (allow clock gating to save power)

```python
# Check clock gating status
fncfg = soc.ace.hda.pcicfg.fncfg.read()
cgd = (fncfg >> 0) & 1   # Bit 0: Clock Gating Disable (per ACE 4.x HAS)
pgd = (fncfg >> 1) & 1   # Bit 1: Power Gating Disable
bcld = (fncfg >> 2) & 1  # Bit 2: BIOS Configuration Lock-Down
print(f"FNCFG={fncfg:#010x}  CGD={cgd} PGD={pgd} BCLD={bcld}")
if cgd:
    print("WARNING: Clock gating DISABLED — power savings lost")
```

---

## Critical Clock Coherency Rule

> **IMPORTANT**: ALL ACE IP audio I/O clocks (Audio PLL 96 MHz, ACE PLL 614.4 MHz, XTAL 38.4 MHz, WoV CRO 38.4 MHz) **AND** the xHCI XTAL clock (for UAOL) **MUST** derive from a **common reference clock** to avoid the need for Asynchronous Sample Rate Conversion (ASRC).

This means:
- Audio PLL, ACE PLL, XTAL, and WoV clocks must share a reference
- The xHCI XTAL used for USB Audio Offload must also be coherent
- If clocks are not coherent, audio streams will drift and require ASRC (which adds latency and power)

---

## NVLDP Default Clock Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| DEFOCS | 1 | Default fabric clock select: WOVROSC |
| DEFEOCS | 1 | Default fabric clock select ext: WOVROSC |
| XOCFS | 01b | XTAL frequency: 38.4 MHz (hard strap) |
| HP/LP/HSIO/SIO Ring OSCs | Internal | Supplied by ACE PLL dividers |

---

## Multi-Platform Clock Summary

ACE clock architecture varies by platform generation. The table below summarizes known differences; consult the platform ACE Integration HAS §6 for authoritative values.

### DSP PLL / VCO Frequencies

| Platform | ACE Version | PLL VCO (FVS=00) | FVS=01 | FVS=10 | FVS=11 | Notes |
|----------|-------------|-------------------|--------|--------|--------|-------|
| **NVL (Novalake)** | ACE 4.x | **614.4 MHz** | Platform-specific ¹ | Platform-specific ¹ | Platform-specific ¹ | PLL in SoC (CLKINTHP=1) |
| **PTL / WCL** | ACE 3.0 | **442.368 MHz** | 221.184 MHz | Consult HAS ¹ | Consult HAS ¹ | Shared ACE 3.x clock tree |
| **LNL (Lunar Lake)** | ACE 2.x | Consult HAS ¹ | Consult HAS ¹ | — | — | Single SOC die; Audio PLL XTAL-derived (24.576 MHz/N) |
| **MTL (Meteor Lake)** | ACE 1.5 | Consult HAS ¹ | Consult HAS ¹ | — | — | Supports Audio PLL **or** RING_OSC (dual-source unique to MTL) |
| **ARL (Arrow Lake)** | ACE 1.5 | Consult HAS ¹ | Consult HAS ¹ | — | — | Similar to MTL; ARL-U/ARL-S may differ |
| **TTL (Titan Lake)** | ACE 3.0/4.0 | ACE4: ~614.4 MHz ¹ / ACE3: ~442.4 MHz ¹ | Consult HAS ¹ | — | — | Dual ACE option (fuse-selected); verify your SKU |
| **RZL (Razor Lake)** | ACE 4.0 | ~614.4 MHz ¹ | Consult HAS ¹ | — | — | Expected to match NVL PCD-H clock tree |

> ¹ **HAS verification required** — Frequencies marked with ¹ have not been verified against the platform-specific ACE Integration HAS. Query Co-Design: `"DSP PLL VCO frequency table <PLATFORM> ACE integration HAS §6"`.

### Per-Platform Audio I/O Clock Sources

| Clock | NVL (ACE 4.x) | PTL/WCL (ACE 3.0) | LNL (ACE 2.x) | MTL (ACE 1.5) | ARL (ACE 1.5) |
|-------|---------------|-------------------|---------------|---------------|---------------|
| **XTAL (xosc_clk)** | 38.4 MHz | 38.4 MHz | 38.4 MHz | 38.4 MHz | 38.4 MHz |
| **Audio PLL (apll_clk)** | 96 MHz | Consult HAS ¹ | 24.576 MHz/N ¹ | Platform-specific ¹ | Platform-specific ¹ |
| **ACE PLL (acepll_clk)** | 614.4 MHz | 442.368 MHz | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ |
| **WoV (wovc_clk)** | 38.404096 MHz | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ |
| **AON (aon_clk)** | 2.560273 MHz | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ |
| **Resume (rsm_clk)** | 32.768 kHz | 32.768 kHz | 32.768 kHz | 32.768 kHz | 32.768 kHz |
| **Fabric (prim_clk)** | 250 MHz | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ |

> ¹ **HAS verification required** — Only NVL values are confirmed from the NVLDP ACE4.x Integration HAS. Other platforms require verification via their platform-specific ACE Integration HAS §6.

### CRO vs PLL by Platform

The clock oscillator architecture changed across ACE generations:

| Platform | ACE | Oscillator Type | CLKINTHVER | CLKINTHP | Notes |
|----------|-----|----------------|-----------|---------|-------|
| **NVL** | 4.x | PLL (SoC-external) | 1 | 1 | PLL physically in SoC, ACE has dividers only |
| **PTL / WCL** | 3.0 | PLL | Consult HAS ¹ | Consult HAS ¹ | Expected PLL mode similar to NVL |
| **LNL** | 2.x | CRO (internal) expected ¹ | Consult HAS ¹ | Consult HAS ¹ | May use integrated CRO — verify against HAS |
| **MTL** | 1.5 | CRO or RING_OSC ¹ | Consult HAS ¹ | Consult HAS ¹ | Dual-source option unique to MTL |
| **ARL** | 1.5 | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | Similar to MTL architecture expected |

> ¹ **HAS verification required** — Oscillator type and configuration registers for non-NVL platforms have not been verified. The CRO → PLL migration started with ACE 3.0; older ACE versions may use integrated CRO. Query Co-Design: `"ACE clock oscillator CRO vs PLL <PLATFORM> ACE integration HAS §6"`.

### DMIC PDM Clock Source by Platform

| Platform | PDM Clock Source | Reference Freq | PDM Clock Rates | Notes |
|----------|-----------------|----------------|-----------------|-------|
| **NVL** | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Power-of-2 dividers via PDMCTRL.ClkDiv |
| **PTL / WCL** | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Same XTAL source as NVL |
| **LNL** | Audio PLL (XTAL-derived) | 24.576 MHz/N ¹ | Consult HAS ¹ | Different divider ratios from NVL |
| **MTL** | Audio PLL or RING_OSC | Platform-specific ¹ | Consult HAS ¹ | Dual-source unique to MTL |
| **ARL** | Audio PLL | Platform-specific ¹ | Consult HAS ¹ | Similar to MTL |

> See `fv-audio/dmic` for full PDM clock divider tables and DMIC-specific initialization.

### S0ix Clock Behavior

During S0ix (PC10), ACE clock sources transition as follows:

| Clock | S0ix State | Notes |
|-------|-----------|-------|
| **rsm_clk** (32.768 kHz) | Always active | Resume clock — required for wake detection |
| **aon_clk** (2.56 MHz) | Active if WoV armed | AON ring oscillator drives WoV keep-alive |
| **wovc_clk** (38.4 MHz RTC PLL) | Active during WoV | WoV DSP runs at ~300 µW |
| **xosc_clk** (38.4 MHz XTAL) | **Gated in deep S0ix** | XTAL shuts off at PC10 |
| **acepll_clk** (614.4 MHz) | **Gated** | ACE PLL off in S0ix |
| **apll_clk** (96 MHz) | **Gated** | Audio PLL off in S0ix |

> **Debug tip**: If S0ix is blocked, verify `acepll_clk` is not still running — an active ACE PLL prevents package-level clock gating. Use `print_LTRs` and `print_s0ix_y_blocking_conditions` doctor scripts to identify the blocking clock.

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No audio output after boot | FNCFG.CGD=1 still set | BIOS failed to clear CGD after init. Check `FNCFG` register |
| DSP FW load timeout | ACE PLL not locked | Check PLL lock status. Verify `CLKINTE=1`, `CLKINTHP=1` in config |
| Audio glitches / drift | Clock coherency violation | Verify all audio clocks derive from common XTAL reference. Check UAOL xHCI XTAL |
| WoV not waking | wovc_clk not enabled | Check `CLKWOVROSCE=1`. WoV requires 38.4 MHz RTC PLL clock |
| Low-power playback fails | XTAL not available | XTAL takes 1 ms to power up. Check xosc_clk availability timing |
| Clock gating prevents debug | CGD=0 gates debug clocks | Temporarily set `FNCFG.CGD=1` to keep clocks running during debug |
| DMIC not clocking | XTAL misconfigured | DMIC uses xosc_clk (38.4 MHz XTAL). Verify XOCFS strap = 01b |
| SSP/BT offload clock wrong | I2S device clock missing | BT offload needs 12.288 MHz external clock. Check platform clock routing |

---

## Platform Debug Approach Routing

When debugging clock issues on newer platforms, apply the closest validated debug procedures:

| Platform | ACE | Route To | Rationale |
|----------|-----|----------|-----------|
| **WCL** | 3.0 | PTL procedures | Same ACE 3.0 clock tree (PLL VCO 442.368 MHz, shared XTAL path) |
| **TTL (ACE 4.0)** | 4.0 | NVL PCD-H procedures | Same ACE 4.x PLL architecture (614.4 MHz VCO) |
| **TTL (ACE 3.0)** | 3.0 | PTL procedures | Same ACE 3.0 clock tree as WCL/PTL |
| **RZL** | 4.0 | NVL PCD-H procedures | Expected identical clock tree to NVL PCD-H |

> **TTL ACE variant detection**: Read `ADSPCS` core count — 4 HiFi5 cores = ACE 4.0 (use NVL procedures); 5 LX7+HiFi4 cores = ACE 3.0 (use PTL procedures).
>
> **Key WCL/TTL/RZL clock differences from NVL**: PLL VCO frequency differs for ACE 3.0 platforms (442.368 MHz vs 614.4 MHz). All platforms share the same 38.4 MHz XTAL reference. CRO behavior for WoV may differ — consult platform ACE Integration HAS §6.

---

## Cross-References

- **[power/SKILL.md](../power/SKILL.md)** — Power gating domains affect clock availability; D0i3/D3 clock behavior
- **[dsp/SKILL.md](../dsp/SKILL.md)** — DSP core clock requirements, FW clock selection via INTCLKCTL
- **[config-checkout/SKILL.md](../config-checkout/SKILL.md)** — BIOS FNCFG.CGD initialization sequence
- **[dmic/SKILL.md](../dmic/SKILL.md)** — DMIC PDM clock sourced from xosc_clk (38.4 MHz XTAL)
- **[wov/SKILL.md](../wov/SKILL.md)** — WoV uses wovc_clk (38.4 MHz RTC PLL) for ultra-low-power DSP
- **[bt-offload/SKILL.md](../bt-offload/SKILL.md)** — SSP/I2S device clock (12.288 MHz) for BT Audio Offload
- **[uaol/SKILL.md](../uaol/SKILL.md)** — UAOL requires xHCI XTAL coherent with ACE audio clocks
