---
name: fv-audio/aioc
description: "Gen6 AIOC (ALC712/ALC1320) validation — All-In-One Codec via SoundWire, SDCA/ACX driver model, 5-Star topology, hardware setup, and BIOS configuration"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# Gen6 AIOC (ALC712/ALC1320) Validation — Novalake (NVL)

Validate the Realtek Gen6 All-In-One Codec (AIOC) system comprising the **ALC712** combo codec and **ALC1320** smart amplifier, connected via **SoundWire Segment 2** using the **SDCA (SoundWire Device Class for Audio)** protocol and **ACX (Audio Class Extensions)** driver model.

> **Scope:** Gen6 AIOC hardware setup (AIC cards, DIP switches, jumper config), SoundWire Segment 2 enumeration of ALC712+ALC1320, BIOS configuration for SDCA/ACX, 5-Star topology validation, and codec-specific troubleshooting on NVL PCD-H and PCH-S.

---

## AIOC Architecture on NVL

### What is AIOC?

AIOC (All-In-One Codec) is Realtek's integrated audio solution that combines a **combo codec** (headphone/microphone/line) and a **smart amplifier** (speaker driver) into a single SoundWire-connected system. Gen6 is the 6th generation of this architecture, using the standardized **SDCA** protocol for device class enumeration and the **ACX** driver model on Windows.

### Codec Components

| Codec | Function | SoundWire Role | Description |
|-------|----------|---------------|-------------|
| **ALC712-VB** | Combo codec | Primary device on Seg 2 | Headphone out, microphone in, line in/out, jack detection |
| **ALC1320** | Smart amplifier | Secondary device on Seg 2 | Speaker output with integrated DSP for speaker protection |

### SoundWire Topology — 5-Star Configuration

The AIOC system uses a **5-Star Configuration** — a multi-drop SoundWire topology where both codecs (ALC712 + ALC1320) share **SoundWire Segment 2** with multiple audio endpoints:

```
ACE 4.x (Master)
    |
    SoundWire Segment 2
    |
    +--- ALC712-VB (Combo Codec)
    |       +--- Headphone Out (endpoint)
    |       +--- Microphone In (endpoint)
    |       +--- Line In/Out (endpoint)
    |       +--- Jack Detect (endpoint)
    |
    +--- ALC1320 (Smart Amp)
            +--- Speaker L (endpoint)
            +--- Speaker R (endpoint)
            +--- Speaker Protection DSP
```

> **Key:** Both codecs are enumerated as separate SoundWire devices on the same segment. The master assigns unique device numbers to each during bus enumeration (see `fv-audio/soundwire` for enumeration details).

### Bus Controller Subsystem ID

| Parameter | Value |
|-----------|-------|
| **HD Audio Bus Controller Subsystem ID** | `0x305610EC` |
| **Vendor** | Realtek (10EC) |
| **Subsystem** | 3056 (Gen6 AIOC) |

---

## Hardware Setup — AIC Cards and RVP Connections

### Required Hardware

Two Add-In Cards (AICs) are required for Gen6 AIOC validation:

| AIC | Part Name | Purpose |
|-----|-----------|---------|
| **Base AIC** | 3PE Gen6 Audio Base AIOC kit | Main codec board — carries ALC712 + ALC1320, connects to RVP |
| **Transducer AIC** | 3PE AIOC GEN4.1 Transducer board | Speaker and microphone transducers for audio I/O |

### NVL-S ERB DIP Switch Configuration

Before connecting the AIOC, configure the **SoundWire signal routing** on the NVL-S ERB via DIP switches:

| DIP Switch | Pin 1 | Pin 2 | Pin 3 | Pin 4 | Purpose |
|------------|-------|-------|-------|-------|---------|
| **SW9B2** | OFF | ON | OFF | ON | Enable SoundWire signal on JE header |
| **SW9C1** | OFF | ON | OFF | ON | Enable SoundWire signal on JE header |

> **CRITICAL:** Both SW9B2 and SW9C1 must be set identically (OFF-ON-OFF-ON) to route the SoundWire Segment 2 signal to the JE header where the AIOC Base AIC connects.

### Base AIC Jumper Settings

The Base AIC ships with a **golden configuration** — most jumpers are set correctly by default. Verify the following jumper positions match the golden config before connecting to RVP.

> **NOTE:** Refer to the AIC documentation or wiki attachment for the complete jumper map. The golden config enables standard AIOC operation with ALC712 + ALC1320.

### Base AIC to RVP Connections (4 Headers)

| Base AIC Header | RVP Header | Signal |
|----------------|------------|--------|
| **JA** | **JA** | Audio analog signals |
| **JD** | **JD** | Digital control/data |
| **JE** | **JE** | SoundWire Segment 2 (primary audio bus) |
| **JH** | **JH** | Power and auxiliary |

### Transducer AIC Connections

The Transducer AIC connects to the Base AIC (NOT directly to the RVP):

| Transducer AIC Header | Base AIC Header | Signal |
|-----------------------|----------------|--------|
| **Speaker Header** | **Speaker Header** | Speaker output to transducer |
| **DMIC Header** | **DMIC Header** | Microphone input from transducer |

> **NOTE:** No jumper changes needed on the Transducer AIC — use default configuration.

---

## BIOS Configuration

### Path 1: HD Audio Configuration

Navigate to: **Intel Advanced Menu → PCH-IO Configuration → HD Audio Configuration**

| BIOS Knob | Required Setting | Notes |
|-----------|-----------------|-------|
| **HDA Link** | **Disabled** | AIOC uses SoundWire, not HDA link |
| **DMIC #0** | **Disabled** | AIOC DMIC comes via SoundWire, not native DMIC |
| **DMIC #1** | **Disabled** | Same as above |
| **SNDW #0** | **Disabled** | Not used for AIOC |
| **SNDW #1** | **Disabled** | Not used for AIOC |
| **SNDW #2** | **Enabled** | **AIOC SoundWire link — this is the AIOC bus** |
| **SNDW #3** | **Disabled** | Not used for AIOC |
| **SNDW#2 Multilane** | **3 data lanes** | Multi-lane bandwidth for AIOC topology |
| **HD Audio Bus Controller Subsystem Id** | **0x305610EC** | Realtek Gen6 AIOC subsystem ID |
| **SoundWire codecs topology** | **MP ALC712-VB, ALC1320, 5-Star Configuration** | Production (MP) AIOC topology selection |

> **ES vs MP:** If your Realtek Gen6.0 AIOC board is labeled **'ES'** (Engineering Sample), select **"ES ALC712-VB, ALC1320, 5-Star Configuration"** instead of the MP variant. Using the wrong topology selection will cause codec enumeration failure.

### Path 2: HD Audio DSP Features Configuration

Navigate to: **Intel Advanced Menu → PCH-IO Configuration → HD Audio Configuration → HD Audio DSP Features Configuration**

| BIOS Knob | Required Setting | Notes |
|-----------|-----------------|-------|
| **DMIC Stereo** | **Disabled** | AIOC uses SoundWire DMIC path, not native |
| **DMIC Quad** | **Disabled** | Same as above |
| **ACX/SDCA** | **Enabled** | **Required for AIOC — enables SDCA protocol and ACX driver** |
| **ACX/SDCA speaker aggregation** | **Enabled** | **Required for ALC1320 speaker amp aggregation** |

> **CRITICAL:** Both `ACX/SDCA` and `ACX/SDCA speaker aggregation` must be **Enabled** for the AIOC system to function. Without these, the ALC712 and ALC1320 will not enumerate under the SDCA/ACX driver model.

---

## SDCA and ACX Overview

### SDCA (SoundWire Device Class for Audio)

SDCA is the standardized device class protocol defined by the MIPI SoundWire specification for audio devices. It provides:

- **Standardized function discovery** — audio functions are enumerated via SoundWire class-specific registers
- **Unified control model** — common register interface for volume, mute, sample rate, format
- **Multi-function support** — a single codec can expose multiple audio functions (headphone, mic, speaker, jack detect)

### ACX (Audio Class Extensions)

ACX is Microsoft's modern Windows audio driver model that replaces the legacy PortCls/AudioEngine model. Key characteristics:

- **Class-based drivers** — codec-agnostic driver model keyed to SDCA function classes
- **Better power management** — per-endpoint power control, faster D3 transitions
- **Required for AIOC** — Gen6 AIOC codecs expose SDCA functions, which require ACX driver support

> **Coupled vs Decoupled Mode:** AIOC operates in **decoupled mode** (default) where the SST audio driver manages the DSP independently from the codec driver. In decoupled mode, Audio DSP is **Enabled** in BIOS (default). See `fv-audio/config-checkout` for coupled vs decoupled mode details.

---

## Validation Checklist

### Pre-Validation Hardware Checks

- [ ] NVL-S ERB DIP switches SW9B2 and SW9C1 set to OFF-ON-OFF-ON
- [ ] Base AIC jumpers in golden configuration
- [ ] Base AIC connected to RVP: JA→JA, JD→JD, JE→JE, JH→JH (all 4 headers)
- [ ] Transducer AIC connected to Base AIC: Speaker→Speaker, DMIC→DMIC headers
- [ ] BIOS configured per Path 1 and Path 2 tables above

### Post-Boot Validation

- [ ] ACE device enumerated at BDF 0:31:3 (DID 0xD328 PCD-H / 0xD228 PCH-S)
- [ ] SoundWire Segment 2 link active
- [ ] ALC712-VB enumerated on Segment 2 (check device ID in driver/log)
- [ ] ALC1320 enumerated on Segment 2 (check device ID in driver/log)
- [ ] SDCA/ACX driver loaded (Device Manager shows ACX audio endpoints)
- [ ] Headphone output functional (playback test)
- [ ] Microphone input functional (capture test)
- [ ] Speaker output functional via ALC1320 (playback test through smart amp)
- [ ] Jack detection working (plug/unplug headphone triggers endpoint switch)

---

## PythonSV Register Access

```python
# AIOC validation via PythonSV
# AIOC codecs are on SoundWire Segment 2
# Access follows the standard SoundWire register path

import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

# Verify ACE device is enumerated
die = namednodes.sv.socket0.pcd   # PCD-H; use .pch for PCH-S
vid = die.ace.cfg.vendor_id.read()
did = die.ace.cfg.device_id.read()
print("ACE VID=0x%04X  DID=0x%04X" % (vid, did))

# Check SoundWire Segment 2 link status
# SHIM LCTL (Link Control) register — one per segment
# HAS verification required: exact namednode path may vary by ACE version
# Pattern: die.ace.sndw.shim.lctlN  where N = segment number
# If the path below fails, browse: sv.socket0.pcd.ace.sndw child nodes
# Or query Co-Design: "SoundWire SHIM LCTL register for Segment 2 in ACE HAS"
try:
    lctl2 = die.ace.sndw.shim.lctl2.read()
    spa  = (lctl2 >> 0) & 1   # SPA (SyncPoint Active) — link started
    cpa  = (lctl2 >> 8) & 1   # CPA (Current Power Active) — link powered
    print("SHIM LCTL2 (Seg 2): 0x%08X — SPA=%d, CPA=%d" % (lctl2, spa, cpa))
    if spa and cpa:
        print("  SoundWire Segment 2 link is ACTIVE — AIOC bus ready")
    else:
        print("  WARNING: Seg 2 link not active — check BIOS SNDW #2 = Enabled")
        print("  Also check: DIP switches SW9B2/SW9C1 = OFF-ON-OFF-ON, JE header seated")
except Exception as e:
    print("  Could not read SHIM LCTL2 — verify namednode path for your platform")
    print("  Try: sv.socket0.pcd.ace.sndw  and browse child nodes")
    print("  Error: %s" % e)

# Check SoundWire Segment 2 device enumeration status
# PING response status indicates whether slaves have been discovered
# HAS verification required: PING status register path varies by ACE version
try:
    # SoundWire device status — check if ALC712 and ALC1320 responded to PING
    # Device Number assignment: ALC712 = typically Dev 1, ALC1320 = Dev 2 on Seg 2
    # The SHIM PCMS (Port Control / Master Status) register shows attached device count
    pcms2 = die.ace.sndw.shim.pcms2.read()
    print("SHIM PCMS2 (Seg 2 status): 0x%08X" % pcms2)
except Exception:
    print("  PCMS2 not accessible — verify with: dir(die.ace.sndw.shim)")
    print("  Alternative: check Linux sysfs: ls /sys/bus/soundwire/devices/")
    print("  Alternative: check Windows Device Manager for SDCA/ACX audio endpoints")

# Verify subsystem ID matches AIOC configuration
ssid = die.ace.cfg.subsystem_id.read()
print("Subsystem ID=0x%08X (expect 0x305610EC for Gen6 AIOC)" % ssid)
if ssid == 0x305610EC:
    print("  AIOC subsystem ID confirmed")
else:
    print("  WARNING: Subsystem ID mismatch — check BIOS HD Audio Bus Controller Subsystem Id knob")
```

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| ALC712 not enumerated on Seg 2 | SNDW #2 disabled in BIOS, DIP switch wrong | Verify BIOS SNDW #2 = Enabled; check SW9B2/SW9C1 = OFF-ON-OFF-ON |
| ALC1320 not enumerated | Speaker aggregation disabled, topology mismatch | Verify BIOS ACX/SDCA speaker aggregation = Enabled; check topology selection |
| Both codecs missing | SoundWire Segment 2 link not active | Check SHIM LCTL for Seg 2; verify JE header connection Base AIC → RVP |
| "No audio endpoints" in OS | ACX/SDCA not enabled in BIOS | Enable both ACX/SDCA and speaker aggregation BIOS knobs |
| Codec enum but no audio | Wrong topology selected (ES vs MP) | If AIOC board is ES, select ES topology in BIOS; if MP, select MP |
| Headphone works, speaker silent | ALC1320 not initialized, speaker aggregation off | Check ACX/SDCA speaker aggregation BIOS knob; verify Transducer AIC connection |
| Speaker works, headphone silent | ALC712 jack detect or routing issue | Check jack detection; verify ALC712 headphone endpoint active in OS |
| DMIC via AIOC not working | Native DMIC not disabled, AIOC DMIC routing | Verify BIOS DMIC #0/#1 = Disabled and DMIC Stereo/Quad = Disabled |
| Subsystem ID mismatch | BIOS knob not set | Set HD Audio Bus Controller Subsystem Id = 0x305610EC |
| Intermittent codec dropout | SoundWire signal integrity on JE header | Re-seat JE cable; verify DIP switch settings; check for bent pins |
| ACX driver not loading | SDCA BIOS knob disabled, wrong Windows build | Verify ACX/SDCA = Enabled; ensure Windows build supports ACX |

---

## Important Safety Notes

- **Multi-segment resource conflict warning:** Enabling multiple SoundWire segments simultaneously (e.g., SNDW #0 + SNDW #2) can cause resource conflicts and bandwidth contention on the SoundWire fabric. Before enabling additional segments alongside AIOC, verify topology compatibility in BIOS and ensure the SoundWire codecs topology BIOS setting matches the actual hardware configuration connected to the platform. Mismatched topology selection vs actual hardware may cause enumeration failures, audio glitches, or system hangs.
- **ES vs MP board selection:** If the Realtek Gen6.0 AIOC board is labeled "ES" (Engineering Sample), you **must** select the `ES ALC712-VB, ALC1320, 5-Star Configuration` topology in BIOS — not the MP variant. Selecting the wrong variant causes silent enumeration failure.
- **Disable native paths:** When AIOC is active, all native audio paths (HDA Link, DMIC #0/#1, SNDW #0/#1/#3) must be disabled in BIOS to avoid resource conflicts with Segment 2.

---

## Cross-References

| Skill | Relevance to AIOC |
|-------|-------------------|
| **fv-audio/soundwire** | SoundWire Segment 2 bus enumeration, SHIM/ALH registers, multi-drop addressing, data lane config |
| **fv-audio/config-checkout** | ACE PCI enumeration (BDF 0:31:3), BAR allocation, coupled vs decoupled mode |
| **fv-audio/dsp** | DSP firmware loading (required for SDCA pipeline), IPC, SRAM management |
| **fv-audio/power** | D0i3/D3 transitions for ACE during AIOC idle, S0ix integration |
| **fv-audio/dmic** | Contrast: native DMIC (disabled for AIOC) vs AIOC SoundWire DMIC path |
| **fv-audio/hda** | Contrast: HDA codec path (disabled for AIOC) vs AIOC SoundWire path |
| **fv-audio/failure-analysis** | NGA test failure analysis, WPP Autologger for SDCA/ACX driver logging |

---

## Multi-Platform AIOC Notes

The AIOC validation documented above is **NVL-specific** (ACE 4.x). The following notes cover AIOC availability and differences on other platforms:

| Platform | ACE Version | AIOC Support | Key Differences |
|----------|-------------|-------------|-----------------|
| **NVL (Novalake)** | ACE 4.x | ✅ Full (documented above) | SoundWire Seg 2, SDCA/ACX, 5-Star topology |
| **PTL (Panther Lake)** | ACE 3.0 | ✅ Expected | Different DIP switch/header layout — consult PTL ERB schematics. ACE DID differs (check `fv-audio/platform`). BIOS menu path may vary. |
| **LNL (Lunar Lake)** | ACE 2.x | ⚠️ Varies | AIOC support depends on board BOM — not all LNL boards include AIOC AICs. ACE 2.x SHIM register layout differs from ACE 4.x. Consult LNL ACE HAS. |
| **MTL (Meteor Lake)** | ACE 1.5 | ⚠️ Limited | SDCA/ACX support introduced mid-lifecycle. Requires specific BIOS version with ACX knobs. Check BOM for AIOC AIC availability. |
| **ARL (Arrow Lake)** | ACE 1.5 | ⚠️ Board-dependent | ARL-S may support AIOC; ARL-U has limited audio I/O. Confirm with platform BOM. |
| **WCL (Wildcat Lake)** | ACE 3.0 | ⚠️ Not expected | ACE 3.0 lacks AIOC hardware support — WCL uses traditional HDA/SoundWire codec topology. No SDCA/ACX driver model. |
| **TTL (Titan Lake)** | ACE 3.0/4.0 | ⚠️ ACE4 only ¹ | TTL ACE 4.0 SKUs expected to support AIOC (same engine as NVL). TTL ACE 3.0 SKUs have no AIOC — fuse-selected. Verify your SKU via `ADSPCS` core count. |
| **RZL (Razor Lake)** | ACE 4.0 | ✅ Expected ¹ | Same ACE 4.0 architecture as NVL PCD-H — AIOC SoundWire Seg 2 expected. Codec BOM may differ (consult RZL ERB schematics for AIC headers). |

> ¹ **HAS verification required** — AIOC support on TTL ACE 4.0 and RZL has not been validated in the lab. Confirm AIOC AIC availability in the platform BOM and BIOS SDCA/ACX knob presence before attempting validation.

> **When validating AIOC on non-NVL platforms:**
> 1. Confirm AIOC AICs are included in the platform BOM (not all boards ship with them)
> 2. Check `fv-audio/platform` for the platform's ACE DID and BDF assignment
> 3. Verify BIOS menu path — the HD Audio Configuration path may differ between platform BIOS builds
> 4. DIP switch labels and header designations (JA, JD, JE, JH) may differ — consult platform ERB schematics
> 5. SHIM register namednode paths may differ between ACE versions — use `dir(die.ace.sndw.shim)` to discover available nodes
>
> **Debug Approach Routing:**
> - **WCL**: No AIOC support expected (ACE 3.0). If AIOC-like codec issues arise, debug via `hda/SKILL.md` or `soundwire/SKILL.md` instead.
> - **TTL ACE 4.0**: Apply NVL AIOC debug procedures directly — same SDCA/ACX engine. Check SKU via `ADSPCS` core count (4 HiFi5 = ACE 4.0).
> - **TTL ACE 3.0**: No AIOC — apply PTL debug procedures for SoundWire codec issues.
> - **RZL**: Apply NVL PCD-H AIOC debug procedures — same ACE 4.0 architecture. Verify AIC headers against RZL ERB schematics (header labels may differ from NVL).

---

## Wiki Reference

| Page | ID | Content |
|------|-----|---------|
| ALC712 AIOC Enabling | 4293994614 | DIP switches, AIC setup, BIOS config for NVL-S |
| IO Enabling (parent) | 4232368404 | All NVL audio I/O enabling pages |
| NVL ACE Validation | 2955725817 | Top-level NVL ACE validation wiki tree |
