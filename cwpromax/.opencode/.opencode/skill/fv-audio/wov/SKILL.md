---
name: fv-audio/wov
description: Wake on Voice (WoV) validation — DMIC-based always-on keyword detection, Clock Ring Oscillator (CRO) ultra-low-power mode, S0ix integration, and automation framework
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# Wake on Voice (WoV) Validation

> **Scope**: Always-on voice keyword detection using DMIC input + DSP processing during S0ix.
> Covers CRO (Clock Ring Oscillator) for ultra-low-power operation (~300 µW), WoV arming/trigger
> flow, S0ix residency validation during WoV idle, DMIC injector-based automation, and
> keyword detection accuracy testing. Platform: NVL with ACE 4.x (BDF 0:31:3).

## Architecture Overview

WoV enables the platform to wake from S0ix (Modern Standby) upon detecting a keyword
("Alexa" default) spoken into the DMIC array. The DSP remains active at ultra-low power
to continuously process DMIC input while the rest of the SoC sleeps.

### Signal Path

```
DMIC Array ──► PDM Interface ──► DSP Core (LX7+HiFi4) ──► Keyword Detection FW
                                      │                        │
                                      │                    [Match?]
                                      │                   ╱        ╲
                                 CRO Clock           YES            NO
                              (~300 µW)               │          (continue)
                                                 Wake Host
                                              (exit S0ix)
```

### Power Architecture

| Mode | Clock Source | Power | Register | Description |
|------|-------------|-------|----------|-------------|
| Normal Audio | XTAL (38.4 MHz) | ~mW range | `DSPWCCTL.DWCS = 00` | Full-quality audio streaming |
| WoV Active | CRO (Ring Oscillator) | ~300 µW | `DSPWCCTL.DWCS = 10` | Ultra-low-power keyword detect |
| WoV + MCLK | MCLK source | Variable | `DSPWCCTL.DWCS = 11` | Alternative clock path |

### CRO vs XTAL Trade-offs

| Parameter | XTAL | CRO |
|-----------|------|-----|
| Power | ~mW | ~300 µW |
| Accuracy | 100 ppm | 10,000 ppm |
| Use Case | Normal audio playback/capture | WoV keyword detection only |
| Wake Latency | N/A (already active) | CRO→XTAL switch on wake |

> **CRITICAL**: Switching between XTAL and CRO trunks causes a **momentary clock stoppage**.
> The switch MUST only be performed during WoV setup/exit transitions — NEVER during an
> active DMIC capture stream. Switching mid-stream will corrupt audio data and may hang the DSP.
> [Wiki Page ID: 1359579145]

### BIOS Prerequisites

| Setting | Path | Value | Purpose |
|---------|------|-------|---------|
| WoV Enable | PCH-IO Config → HD Audio DSP Features Config → WoV[X] | Enabled | Enables WoV firmware feature |
| Intel WoV | PCH-IO Config → HD Audio DSP Features Config → Intel WoV[X] | Enabled | Enables Intel keyword detection |
| HD Audio DSP | PCH-IO Config → HD Audio Config → Audio DSP | Enabled | Required for DSP operation |

> After BIOS changes, merge `MultiPA.reg` into the Windows registry and restart the SUT.
> [Wiki Page ID: 1294973478]

## Multi-Platform WoV Support

| Platform | ACE Version | DSP Core | CRO/RTC | Notes |
|----------|-------------|----------|---------|-------|
| NVL (Novalake) | ACE 4.x | LX7+HiFi4 | RTC deprecated; use CRO (`DWCS=10`) | `DWCS=01` (RTC) removed in ACE 4.x |
| PTL (Panther Lake) | ACE 3.0 | LX7+HiFi4 | CRO supported | Consult PTL ACE HAS |
| WCL (Wildcat Lake) | ACE 3.0 | LX7+HiFi4 | CRO supported | Same ACE 3.0 as PTL — apply PTL WoV procedures |
| LNL (Lunar Lake) | ACE 2.x | LX7+HiFi4 | CRO supported | Consult LNL ACE HAS |
| MTL (Meteor Lake) | ACE 1.5 | HiFi4 | CRO supported | Consult MTL ACE HAS |
| ARL (Arrow Lake) | ACE 1.5 | HiFi4 | CRO supported | Consult ARL ACE HAS |
| TTL (Titan Lake) | ACE 3.0/4.0 | ACE4: HiFi5 / ACE3: LX7+HiFi4 | CRO expected ¹ | ACE 4.0 → use NVL WoV procedures; ACE 3.0 → use PTL WoV procedures |
| RZL (Razor Lake) | ACE 4.0 | HiFi5 | RTC deprecated; CRO expected ¹ | Same ACE 4.0 as NVL — apply NVL WoV procedures |

> ¹ **HAS verification required** — CRO configuration on TTL and RZL has not been validated in the lab. CRO clock selection (`DWCS` field) and WoV arming sequence are expected to match their ACE generation counterparts (NVL for ACE 4.0, PTL for ACE 3.0).

> Automation scripts (`WoV_DMIC_Audio_Test_Host.py`, `WoV_DMIC_Audio_Test_SUT.py`) and IPC message structures may differ between ACE versions. Always validate the WoV flow against the platform ACE Integration HAS.

---

## Register Map

### Clock Ring Oscillator (CRO) Registers

| Register | PythonSV Path | Bits | Field | Description |
|----------|--------------|------|-------|-------------|
| `CLKCTL` | `die.ace.hda.bar0.clkctl` | [4] | `WOVROSCS` | WoV Ring Oscillator Clock Select — switches XTAL trunk to CRO |
| `CLKSTS` | `die.ace.hda.bar0.clksts` | [4] | `WOVROSCS` | CRO switch status indication — confirms trunk switched |
| `DSPWCCTL` | `die.ace.hda.bar0.dspwcctl` | [1:0] | `DWCS` | DSP Wall Clock Select: 00=XTAL, 10=WoV CRO, 11=MCLK |
| `MDIVxCTRL` | `die.ace.hda.bar0.mdivctrl` | varies | `MCDSS` | MCLK Divider Clock Source Select |
| `MDIVxCTRL` | `die.ace.hda.bar0.mdivctrl` | varies | `MDEDWCS` | MCLK Divider Enable DSP Wall Clock Source |

> **NOTE**: PythonSV namednode paths shown use `die` = `sv.socket0.pcd` (PCD-H) or `sv.socket0.pch` (PCH-S).
> Exact bitfield offsets and MMIO addresses must be verified against ACE Integration HAS via Co-Design.
> RTC clock source is **deprecated** starting from ACE 4.x (NVL). Do not use
> `DSPWCCTL.DWCS = 01` (RTC). [Wiki Page ID: 4014651262]

### WoV DSP Firmware IPC

The WoV firmware module runs on one LX7+HiFi4 core and implements:
- Continuous DMIC capture at reduced sample rate
- Keyword detection model evaluation (DNN-based)
- Wake event signaling to PMC on keyword match

## Initialization Sequence

### Step 1: Verify ACE Enumeration and WoV BIOS Settings

```python
# Verify ACE device is enumerated
import pysvtools.pcicfg as pcicfg

vid_did = pcicfg.read(0, 31, 3, 0x00)
vid = vid_did & 0xFFFF
did = (vid_did >> 16) & 0xFFFF
print(f"ACE VID = 0x{vid:04X}, DID = 0x{did:04X}")
# Expected VID:DID = 0x8086:D328 (PCD-H) or 0x8086:D228 (PCH-S)

# Verify BIOS WoV settings are applied via Device Manager:
# Intel(R) Smart Sound Technology → Properties → WoV should show Enabled
```

### Step 2: CRO Clock Switch Sequence

```python
# Read current wall clock source
import pysvtools.bitman as bitman

dspwcctl = bitman.read("pch.ace.bar0.DSPWCCTL")
dwcs = dspwcctl & 0x3
print(f"Current DWCS = {dwcs:#04b}")  # 00=XTAL, 10=CRO, 11=MCLK

# Switch to CRO (only during WoV transition, NOT mid-stream!)
# CLKCTL.WOVROSCS = 1 to request CRO
WOVROSCS_BIT = 4  # CLKCTL bit 4: Wake on Voice Ring Oscillator Clock Select
clkctl = bitman.read("pch.ace.bar0.CLKCTL")
bitman.write("pch.ace.bar0.CLKCTL", clkctl | (1 << WOVROSCS_BIT))

# Poll CLKSTS.WOVROSCS for confirmation
import time
for _ in range(100):
    clksts = bitman.read("pch.ace.bar0.CLKSTS")
    if clksts & (1 << WOVROSCS_BIT):
        print("CRO trunk switch confirmed")
        break
    time.sleep(0.001)
else:
    print("ERROR: CRO switch not confirmed within timeout")
```

### Step 3: Arm WoV via Client Application

```
# On SUT (Windows):
# 1. Launch WoVClientApplication.exe
# 2. Press 'A' to check WoV status (should show "Ready")
# 3. Press '3' to arm WoV keyword detection
# 4. Status should change to "Armed"
# 5. Say "Alexa" near DMIC array to trigger wake
```

## Validation Points

### WoV Functional Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| WoV Arm/Disarm | Arm WoV, verify DSP enters keyword detect mode | WoVClientApplication shows "Armed" status |
| Keyword Wake | Speak "Alexa" while in S0ix | Platform exits S0ix, audio session resumes |
| False Reject | Speak keyword at various distances/volumes | Detection rate within spec (platform-dependent) |
| False Accept | Play non-keyword audio near DMICs | No spurious wake events |
| S0ix Residency | Verify S0ix residency while WoV armed and idle | `slp_s0_residency` counter incrementing |
| CRO Power | Measure power during WoV idle vs XTAL idle | CRO mode ~300 µW vs XTAL ~mW range |
| Clock Switch | Transition XTAL→CRO→XTAL during WoV arm/disarm | No DSP hang, no audio corruption, CLKSTS confirms |

### S0ix Integration Validation

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| WoV + S0ix Entry | Arm WoV, close lid / idle to enter S0ix | Platform enters S0ix with WoV active |
| WoV + S0ix Residency | Monitor `pch.pmc.mmr.slp_s0_residency` while WoV armed | Counter increments (S0ix not blocked by WoV) |
| WoV Wake → S0ix Re-entry | Wake via keyword, dismiss, let platform re-enter S0ix | S0ix re-entered within expected timeout |
| WoV + S0ix Cycling | Iterate arm→S0ix→wake→disarm→re-arm (N iterations) | No failures over 100+ iterations |

> **CRITICAL**: WoV must NOT block S0ix entry. If `slp_s0_residency` stops incrementing
> while WoV is armed, check LTR values — the ACE device may be reporting an active LTR
> that prevents S0ix. Debug with `print_LTRs` doctor script. Cross-reference with
> `power/SKILL.md` for S0ix blocking analysis.

## Automation Framework

### Test Infrastructure

WoV automation requires a **two-machine setup** with a DMIC injector card:

```
┌─────────────┐     Socket (TCP)      ┌─────────────┐
│   HOST PC    │◄────────────────────►│   SUT (DUT)  │
│ 192.168.132.1│    Peer-to-peer      │192.168.132.5 │
│              │                       │              │
│ WoV_DMIC_    │                       │ WoV_DMIC_    │
│ Audio_Test_  │                       │ Audio_Test_  │
│ Host.py      │                       │ SUT.py       │
│              │                       │              │
│ OpenIPC /    │                       │ WoVClient    │
│ PythonSV     │                       │ Application  │
│ (S0ix check) │                       │ .exe         │
└──────┬───────┘                       └──────┬───────┘
       │                                      │
       │            DMIC Injector Card         │
       └──────────► (plays keyword WAV) ──────┘
                    into DMIC array
```

### Automation Scripts

| Script | Runs On | Purpose |
|--------|---------|---------|
| `WoV_DMIC_Audio_Test_Host.py` | Host PC | Orchestrates test iterations, monitors S0ix via OpenIPC |
| `WoV_DMIC_Audio_Test_SUT.py` | SUT | Arms WoV, reports status back to Host |
| Keyword WAV | DMIC Injector | `Alexa_4ch_16bit_48kHz_Test_Phrase_3.wav` played into DMIC array |

### Iteration Flow

```
For each iteration:
  1. Host → SUT: "Arm WoV"
  2. SUT: WoVClientApplication arm (key '3')
  3. SUT → Host: "Armed, entering S0ix"
  4. Host: Wait for S0ix entry (poll slp_s0_residency via OpenIPC)
  5. Host: Play keyword WAV via DMIC injector
  6. Host: Wait for S0ix exit (slp_s0_residency stops incrementing)
  7. SUT → Host: "Woke up, keyword detected"
  8. Host: Log result, proceed to next iteration
```

> [Wiki Page ID: 1760434053] — WoV Complete Automation

### Legacy Automation (EOL)

An older Solar-based automation exists using `LoopKeyword.py` (Host) and
`WoV_Application_start.py` (SUT via Task Scheduler). This approach is **end-of-life** and
should not be used for new NVL validation. Use the socket-based framework above instead.
[Wiki Page ID: 1569950544]

---

## PythonSV — WoV State Diagnostic

Comprehensive WoV state dump for debug and triage:

```python
def dump_wov_state(soc, die_path="pcd"):
    """Dump complete WoV state — clock source, DSP wall clock, S0ix residency.

    Args:
        soc: PythonSV SoC handle
        die_path: 'pcd' for PCD-H, 'pch' for PCD-S
    """
    import pysvtools.bitman as bitman

    die = f"sv.socket0.{die_path}"
    print("=" * 60)
    print("WOV STATE DIAGNOSTIC")
    print("=" * 60)

    # 1. Clock Ring Oscillator state
    try:
        clkctl = bitman.read(f"{die}.ace.bar0.CLKCTL")
        clksts = bitman.read(f"{die}.ace.bar0.CLKSTS")
        wovroscs_req = (clkctl >> 4) & 1
        wovroscs_sts = (clksts >> 4) & 1
        print(f"\n[CRO Clock]")
        print(f"  CLKCTL = 0x{clkctl:08X}  WOVROSCS(request) = {wovroscs_req}")
        print(f"  CLKSTS = 0x{clksts:08X}  WOVROSCS(status)  = {wovroscs_sts}")
        if wovroscs_req and wovroscs_sts:
            print("  → CRO trunk ACTIVE (WoV clock source in use)")
        elif wovroscs_req and not wovroscs_sts:
            print("  → CRO trunk REQUESTED but not confirmed — switch pending")
        else:
            print("  → CRO trunk INACTIVE (using XTAL or other source)")
    except Exception as e:
        print(f"\n[CRO Clock] Read error: {e}")

    # 2. DSP Wall Clock Source
    try:
        dspwcctl = bitman.read(f"{die}.ace.bar0.DSPWCCTL")
        dwcs = dspwcctl & 0x3
        dwcs_names = {0: 'XTAL (normal)', 1: 'RTC (deprecated in ACE4)', 2: 'CRO (WoV)', 3: 'MCLK'}
        print(f"\n[DSP Wall Clock]")
        print(f"  DSPWCCTL = 0x{dspwcctl:08X}  DWCS = {dwcs:#04b} ({dwcs_names.get(dwcs, 'unknown')})")
        if dwcs == 1:
            print("  WARNING: RTC source selected — deprecated in ACE 4.x, use CRO instead")
    except Exception as e:
        print(f"\n[DSP Wall Clock] Read error: {e}")

    # 3. ACE Power State (PMCSR)
    try:
        import pysvtools.pciedut as pcie
        ace = pcie.get_dev(0, 31, 3)
        pmcsr = ace.cfg.read(0x84, 2)  # Typical PMCSR offset — verify per platform
        ps = pmcsr & 0x3
        ps_names = {0: 'D0', 1: 'D1', 2: 'D2', 3: 'D3'}
        print(f"\n[ACE Power State]")
        print(f"  PMCSR = 0x{pmcsr:04X}  PowerState = {ps_names.get(ps, '?')}")
    except Exception as e:
        print(f"\n[ACE Power State] Read error: {e}")

    # 4. S0ix Residency
    try:
        slp_s0_res = bitman.read(f"{die}.pmc.mmr.slp_s0_residency")
        print(f"\n[S0ix Residency]")
        print(f"  slp_s0_residency = {slp_s0_res}  (increments at 30.5 µs/tick)")
        if slp_s0_res > 0:
            print(f"  → S0ix has been entered (residency > 0)")
        else:
            print(f"  → S0ix NOT entered yet (residency = 0)")
    except Exception as e:
        print(f"\n[S0ix Residency] Read error: {e}")

    # 5. DMIC pad state (WoV input source)
    try:
        print(f"\n[DMIC Pads]")
        for pad in ["DMIC_CLK_A", "DMIC_DATA_A"]:
            pmode = getattr(soc.gpio.pm, pad).cfg0.pmode.read()
            print(f"  {pad}: pmode={pmode}  ({'Native OK' if pmode == 1 else 'NOT NATIVE'})")
    except Exception as e:
        print(f"\n[DMIC Pads] Read error: {e}")

    print("\n" + "=" * 60)

# Usage:
# dump_wov_state(soc, die_path="pcd")   # PCD-H
# dump_wov_state(soc, die_path="pch")   # PCD-S
```

### WoV Iteration Stress Script

For automated stress testing of WoV arm/wake/re-arm cycles:

```python
def wov_stress_check(soc, die_path="pcd", iterations=5, s0ix_wait_s=10):
    """Check S0ix residency across multiple WoV arm cycles.

    NOTE: This script monitors residency only — actual WoV arming and
    keyword injection must be done via the two-machine automation framework
    (WoV_DMIC_Audio_Test_Host.py / WoV_DMIC_Audio_Test_SUT.py).

    Args:
        soc: PythonSV SoC handle
        die_path: 'pcd' for PCD-H, 'pch' for PCD-S
        iterations: Number of residency check iterations
        s0ix_wait_s: Seconds to wait between checks
    """
    import pysvtools.bitman as bitman
    import time

    die = f"sv.socket0.{die_path}"
    print(f"WoV Stress Check — {iterations} iterations, {s0ix_wait_s}s wait between checks")
    results = []

    for i in range(iterations):
        res_before = bitman.read(f"{die}.pmc.mmr.slp_s0_residency")
        time.sleep(s0ix_wait_s)
        res_after = bitman.read(f"{die}.pmc.mmr.slp_s0_residency")
        delta = res_after - res_before
        passed = delta > 0
        results.append({'iteration': i+1, 'delta': delta, 'pass': passed})
        status = "PASS" if passed else "FAIL"
        print(f"  Iter {i+1}: residency delta = {delta} ({status})")

    pass_count = sum(1 for r in results if r['pass'])
    print(f"\nResults: {pass_count}/{iterations} iterations with S0ix residency")
    return results
```

---

## Troubleshooting

| Symptom | Possible Cause | Debug Steps |
|---------|---------------|-------------|
| WoV won't arm | BIOS WoV settings not enabled | Check BIOS: WoV[X] and Intel WoV[X] must both be Enabled. Verify MultiPA.reg merged. |
| No keyword detection | DMIC not capturing in WoV mode | Check DMIC pad configuration (`dmic/SKILL.md`). Verify CRO clock is active via `CLKSTS.WOVROSCS`. |
| S0ix blocked when WoV armed | ACE LTR preventing S0ix | Run `print_LTRs` doctor script. Check ACE device LTR value. Cross-ref `power/SKILL.md`. |
| False wakes (no keyword spoken) | DSP FW sensitivity too high | Check FW keyword model version. May need FW update or threshold adjustment. |
| DSP hang after CRO switch | Clock switch during active stream | CRO↔XTAL switch must ONLY occur during WoV arm/disarm transitions. Never mid-stream. [Page ID: 1359579145] |
| WoV works once then fails | S0ix re-entry failure after wake | Check if WoV re-arms correctly after wake. Monitor slp_s0_residency across iterations. |
| DMIC injector not triggering wake | WAV file format mismatch | Use 4-channel, 16-bit, 48 kHz WAV. Verify injector card wiring to correct DMIC headers. |
| Automation socket timeout | Network config mismatch | Host must be 192.168.132.1, SUT 192.168.132.5. Verify peer-to-peer cable connected. |

### Platform Debug Approach Routing

When debugging WoV issues on newer platforms:

| Platform | ACE | Route To | Key WoV Differences |
|----------|-----|----------|---------------------|
| **WCL** | 3.0 | PTL WoV procedures | Same CRO architecture as PTL; verify `DWCS` field behavior |
| **TTL (ACE 4.0)** | 4.0 | NVL WoV procedures | RTC deprecated (`DWCS=01` removed); use CRO (`DWCS=10`) |
| **TTL (ACE 3.0)** | 3.0 | PTL WoV procedures | CRO supported; same WoV flow as PTL |
| **RZL** | 4.0 | NVL WoV procedures | Same CRO architecture as NVL; RTC deprecated |

> **DMIC injector compatibility**: The DMIC injector card and WAV file requirements (4-channel, 16-bit, 48 kHz) are hardware-level and apply identically across all platforms. DMIC GPIO pad assignments differ per platform — consult `dmic/SKILL.md` and the platform GPIO table.

## Related Sub-Skills

- [`dmic/SKILL.md`](../dmic/SKILL.md) — DMIC PDM interface, gain, GPIO pads — WoV input source
- [`dsp/SKILL.md`](../dsp/SKILL.md) — LX7+HiFi4 DSP cores, FW load, IPC — WoV processing engine
- [`power/SKILL.md`](../power/SKILL.md) — D-states, S0ix, LTR — WoV power integration
- [`config-checkout/SKILL.md`](../config-checkout/SKILL.md) — ACE enumeration, BIOS prerequisites
