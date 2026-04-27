---
name: fv-audio
description: "Audio subsystem debugging skills for HDA, SoundWire, DSP, DMIC, Display Audio, BT Audio Offload, UAOL, WoV, AIOC, Jack Detection, Interrupts, Clocking, and codec validation"
version: "rev2.1"
owner: huiyingt
---

# Audio Subsystem Debugging Skills

The Audio subsystem on Intel Client SoC platforms is managed by the **ACE (Audio & Communications Engine)** IP, integrating HDA links, SoundWire links, SSP/I2S ports, DSP cores, and codec interfaces under a single PCI function.

## Platform Coverage

| Platform | ACE Ver | Key Feature Delta |
|----------|---------|-------------------|
| **NVL** | 4.x | Full UAOL + AIOC Gen6, 5 SDW segments, HiFi5 |
| **PTL** | 3.0 | 5 SDW v1.2, 442/221 MHz DSP, WCL shares ACE 3.x |
| **LNL** | 2.x | Single-die, WoV, internal UAOL only |
| **MTL** | 1.5 | First chiplet audio, behind-hub UAOL RTL bug |
| **ARL** | 1.5 | Desktop-focused, ARL-U no iDisp |
| **WCL** | 3.0 | Shares ACE 3.x with PTL, 5 SDW links, PCD/SOC die |
| **TTL** | 3.0/4.0 | Dual ACE option (fuse-selected); PCD-H/PCD-S dies |
| **RZL** | 4.0 | ACE 4.x, 4 die variants (PCD-H/S/M/W), 4.5 MB SRAM |

> **Full per-platform config** (DIDs, DSP cores, SRAM, BAR layout, PythonSV paths, BIOS knobs, bring-up checklists): → Load **`fv-audio/platform`**

> **Known issues & sightings**: → Load `docs/audio_known_issues.md` first when triaging any failure.

> **Reference sheets**: → Load `docs/audio_reference_sheets.md` for step-by-step triage trees.

## CRITICAL: NEVER HARD-CODE LINK/PORT COUNTS — ALWAYS QUERY CO-DESIGN

Link counts, DSP cores, SRAM sizes, and feature availability **vary by platform AND die variant**. Always query the project-specific ACE Integration HAS via Co-Design before assuming any configuration.

**Workflow:** Query `https://chat.co-design.intel.com/chat` with: `"Please reference {PROJECT}_{DIE}_ace4.x_integration_has.html and tell me: How many HDA links, SoundWire segments, SSP/I2S ports, and DSP cores are available on {PLATFORM} {DIE}?"`

| Project | HAS Document |
|---------|-------------|
| NVL PCD-H | `nvldp_ace4.x_integration_has.html` |
| NVL PCD-S | `nvps_ace4.x_integration_has.html` |
| PTL | `ptlsm_ace3.x_integration_has.html` |
| WCL | `wcl_ace3.x_integration_has.html` |
| TTL / RZL | ACE 4.x Integration HAS (verify exact doc name via Co-Design) |
| MTL / LNL / ARL | Query Co-Design: `"{PLATFORM} ACE integration HAS"` |

---

## Safety Warnings

> These rules apply to ALL sub-skills and any PythonSV commands executed for audio.

| Rule | Details |
|------|---------|
| **DO NOT** write to fuse registers | Audio fuse overrides are permanent — irreversible silicon damage |
| **DO NOT** modify PLL settings without confirmation | Wrong PLL config can disrupt all audio clocks until platform reset |
| **DO NOT** force-write PMCSR to D0 during S0ix entry | Can cause PMC firmware hang — requires cold boot to recover |
| **DO NOT** send codec verbs without verifying codec address | Wrong codec address can corrupt other codec state on shared HDA link |
| **DO NOT** modify DSP SRAM or firmware without confirmation | Can cause DSP lockup requiring platform reset |
| **DO NOT** assume port/link counts across die variants | PCD-H and PCH-S have different DSP core counts and iDisp routing |
| **ALWAYS** confirm target platform and die variant before register access | Wrong base path = wrong silicon, wrong results |
| **ALWAYS** read a register before writing it | Preserve other bit fields — don't blindly overwrite |

---

## CRITICAL: MANDATORY HAS Document Lookup Workflow

**Before answering ANY audio question for ANY project/platform, you MUST first look up the project-specific ACE Integration HAS document from Codesign.**

### Mandatory Steps for Every New Project/Platform Query:

1. **Identify the project name** (e.g., NVL, PTL, LNL, etc.) and the die type (PCD-H, PCH-S, etc.)
2. **Search Codesign** (https://chat.co-design.intel.com/chat) for the project's ACE Integration HAS
3. **Ask Codesign to reference that specific HAS document** when querying link counts, BDF assignments, DSP core details, etc.
4. **NEVER assume configurations** from one die variant apply to another — each die's HAS is the single source of truth.

### Known HAS Documents (Reference):

| Project | Die | HAS Document |
|---------|-----|-------------|
| Nova Lake (NVL) | PCD-H | `nvldp_ace4.x_integration_has.html` |
| Nova Lake (NVL) | PCH-S | `nvps_ace4.x_integration_has.html` |
| Panther Lake (PTL) | PCD/PCH | `ptlsm_ace3.x_integration_has.html` |
| Wildcat Lake (WCL) | PCD/SOC | `wcl_ace3.x_integration_has.html` |
| TitanLake (TTL) | PCD-H/PCD-S | ACE 4.x or 3.x Integration HAS (fuse-dependent) |
| RazorLake (RZL) | PCD-H/S/M/W | ACE 4.x Integration HAS |
| Meteor Lake (MTL) | SOC/IOE | Query via Co-Design: `"MTL ACE integration HAS"` |
| Lunar Lake (LNL) | SOC | Query via Co-Design: `"LNL ACE integration HAS"` |
| Arrow Lake (ARL) | PCH | Query via Co-Design: `"ARL ACE integration HAS"` |

> **Note:** For any new project not listed above, search Codesign for the ACE Integration HAS. Add newly discovered HAS documents to this table.

### ⛔ "According to HAS" Override Rule

**When the user's question contains ANY of these phrases, you MUST navigate to Co-Design — NEVER return cached sub-skill values:**
- "according to HAS"
- "from HAS"
- "HAS says"
- "per the HAS"
- "what does the HAS document say"
- "register offsets for ... according to HAS"

**This rule overrides all cached values in sub-skills.** Even if `fv-audio/hda`, `fv-audio/dsp`, or any other sub-skill contains register offset tables, those are reference summaries — NOT authoritative HAS data. When the user explicitly asks for HAS values, you MUST:

1. **Navigate** to `https://chat.co-design.intel.com/chat` using `browsermcp_browser_navigate`
2. **Query** with the specific HAS document: e.g., `"Please reference nvldp_ace4.x_integration_has.html and list the HDA global register offsets for NVL PCD-H"`
3. **Wait** for the response to complete (15+ seconds typical)
4. **Parse** the Co-Design response and present it to the user
5. **NEVER** substitute cached skill content for a Co-Design HAS query

> **WHY**: Sub-skill register tables may be stale or incomplete. The HAS document in Co-Design is the single source of truth for register offsets, and the user is explicitly requesting it.

---

## Audio Architecture Overview

All audio subsystems are integrated under **BDF 0:31:3** (single PCI function) across all platforms. BAR0 (512 KB) = HDA registers, BAR1 (4 KB) = ACPI extension, BAR2 (2 MB) = DSP domain (requires `PPCTL.GPROCEN=1`).

**Subsystems:** HDA links (external codec + iDisp), SoundWire (multi-segment, 16 bidirectional PCM streams/link), SSP/I2S (BT offload to CNVi), DSP (HiFi5/HiFi4 + ULP core), DMIC (PDM, GPIO PMode 1), Display Audio (iDisp via HDA SDI 2 or SoundWire Seg 0 Alt), UAOL (xHCI→ACE isochronous offload), AIOC (ALC712+ALC1320 on SoundWire Seg 2, SDCA/ACX).

> **Per-platform DIDs, die variant differences, DSP core counts, SRAM sizes, PythonSV paths:** → Load **`fv-audio/platform`**
>
> **Per-subsystem deep-dive (registers, protocols, debug):** → Load the corresponding sub-skill (hda, soundwire, dsp, dmic, display-audio, bt-offload, uaol, aioc, etc.)

---

## Subsystem Quick Reference

Each subsystem below has a dedicated sub-skill with full register maps, protocols, debug checklists, and known issues.

| Subsystem | Key Facts | Sub-Skill |
|-----------|-----------|-----------|
| **HDA** | 2 SDI pins (HDALIPC=2). SDI 0/1=external codecs, SDI 2=iDisp. CORB/RIRB for command transport. 1.8V link voltage on NVL. | `fv-audio/hda` |
| **SoundWire** | NVL PCD-H: **5 segments** (SNDWSC=5). Seg 0: iDisp-A alt (PCD-H). Seg 2/3: up to 4 data lanes (multi-lane). Seg 4: **external** on PCD-H (up to 5 lanes); **on-die** iDisp-A/CNVi alt on PCH-S. 16 bidirectional PCM streams/link. | `fv-audio/soundwire` |
| **DSP** | PCD-H: 4 HiFi5 HP + 1 ULP core, 4.5 MB SRAM. PCH-S: 2 HiFi5 HP + 1 ULP + 1 ANNA, 2.25 MB. FW load via IPC. | `fv-audio/dsp` |
| **DMIC** | PCD-H: **3 PDM interfaces** (PDM0/PDM1/PDM2) = **6 channels** (3×2ch). PCD-S: 2 PDM = 4ch. PCD-H is unique — all other platforms have 2 PDMs. PDM clock 0.768–4.8 MHz (XTAL 38.4 MHz). GPIO PMode 1 required. **#1 failure cause: GPIO pad mode not Native.** | `fv-audio/dmic` |
| **Display Audio** | iDisp via HDA SDI 2 or SoundWire Seg 0 Alt (PCD-H, mutually exclusive). Up to 3 streams, 8ch, 192 kHz. HPD→EDID→ELD flow. | `fv-audio/display-audio` |
| **BT Offload** | SSP/I2S ↔ CNVi BT controller. SCO=PSP mode, A2DP=I2S mode. Known: BCLK inversion lost after PG exit (PCH-S). | `fv-audio/bt-offload` |
| **UAOL** | xHCI→ACE isochronous offload. **NVL**: ACE4, behind-hub ✅, enhanced FIFO (>1ms). **PTL/WCL**: ACE3, behind-hub ✅, ~1ms FIFO. **MTL**: behind-hub ❌ (RTL bug). **LNL**: ACE 2.x internal UAOL only, no behind-hub. **ARL**: ACE 1.5 internal UAOL only, no behind-hub. Blocks S0ix when active. Cross-domain: load `fv-audio/uaol` + `fv-usb`. | `fv-audio/uaol` |
| **AIOC** | ALC712+ALC1320 on SoundWire Seg 2, SDCA/ACX driver. NVL-S only. DIP switches SW9B2/SW9C1. | `fv-audio/aioc` |
| **WoV** | DMIC + DSP + CRO (~300μW) for always-on keyword detection during S0ix. | `fv-audio/wov` |

> **Known sightings for all subsystems:** → Load `docs/audio_known_issues.md`

---

## Sub-Skills

The fv-audio skill provides 17 specialized sub-skills for audio validation and debugging:

### 1. fv-audio/platform
**Purpose:** Per-platform ACE configuration data — DIDs, BDF, BAR layout, PythonSV paths, DSP cores, reset architecture, power domains, BIOS knobs, AIOC/UAOL hardware setup, and bring-up checklists

**When to use:**
- Identifying Device IDs, BDF assignments, or BAR layout for a specific platform
- Looking up PythonSV namednode paths for a die variant
- Checking DSP core count, SRAM size, or SoundWire segment count per platform
- Finding BIOS knob names/defaults for audio configuration
- NVL-S AIOC hardware setup (DIP switches, AIC connections)
- Platform bring-up checklist and common bring-up failure triage
- Comparing feature availability across platforms (UAOL, AIOC, link counts)

**Covers:** ACE version mapping (1.x–4.x), die type / PythonSV paths, DID tables, BAR layout, PCI config, coupled vs decoupled mode, per-platform feature matrix, reset architecture, power domains (PG0–PG3), BIOS knobs, fuses/straps, DMIC clock sources, AIOC hardware, NGA test content, bring-up checklist, common failures

---

### 2. fv-audio/config-checkout
**Purpose:** Verify audio hardware configuration — PCI enumeration, BAR allocation, BIOS settings, ACPI tables

**When to use:**
- Checking PCI device presence (DID, VID, BAR)
- Validating BIOS audio knobs and ACPI _HID entries
- Debugging "audio device not found" or "BAR reads 0x0" issues
- Verifying audio subsystem is enabled in BIOS

**Covers:** PCI enumeration, Device ID validation, BAR0/BAR1/BAR2 allocation, BIOS config, ACPI verification

---

### 3. fv-audio/hda
**Purpose:** Validate HDA link initialization, codec discovery, verb programming, and stream management

**When to use:**
- Debugging HDA codec detection failures
- Verifying CORB/RIRB command transport
- Programming codec verbs (widget config, amplifier, jack detect)
- Validating iDisp audio for HDMI/DP output
- Stream setup and DMA buffer management

**Covers:** HDA link init, STATESTS codec detection, CORB/RIRB, verb programming, stream descriptors, iDisp

---

### 4. fv-audio/soundwire
**Purpose:** Validate SoundWire link initialization, bus enumeration, and stream configuration

**When to use:**
- Debugging SoundWire link bring-up failures
- Verifying bus enumeration and device discovery
- Configuring streams and data lanes
- Multi-drop codec configuration
- PCD-H vs PCH-S iDisp routing differences

**Covers:** SoundWire link init, bus enumeration, stream setup, multi-drop, data lane config, 5 segment details

---

### 5. fv-audio/dsp
**Purpose:** Validate DSP core bring-up, firmware loading, IPC messaging, and SRAM management

**When to use:**
- Debugging DSP core initialization (GPROCEN, PPCTL)
- Firmware load and verification
- IPC (Inter-Processor Communication) message passing
- SRAM power gating and allocation
- Audio pipeline configuration
- PCD-H (4 cores) vs PCH-S (2 cores) differences

**Covers:** DSP core init, FW load, IPC mailbox, SRAM management, pipeline config, BAR2 access

---

### 6. fv-audio/power
**Purpose:** Validate audio power management — D-state transitions, PLL, SRAM power gating, S0ix integration

**When to use:**
- Debugging D0i3/D3 entry/exit failures
- Verifying PLL shutdown and restart
- SRAM power gating validation
- LTR configuration and reporting
- S0ix blocker investigation (audio blocking platform idle)
- Codec power management coordination

**Covers:** PMCSR D-states, HDAPLLCTL, SRAM PGCTL, LTR, PMC coordination, S0ix, codec PM

---

### 7. fv-audio/failure-analysis
**Purpose:** Analyze audio-related test failures from NGA test results

**When to use:**
- Investigating audio test failures from NGA
- Parsing solar_manager audio logs
- Cross-referencing failures with known sightings
- Identifying failure trends across test runs
- FV-TRIAGE audio pattern correlation

**Covers:** NGA integration, log parsing, sighting correlation, audio error signatures

---

### 8. fv-audio/dmic
**Purpose:** Validate DMIC (Digital Microphone) PDM interface, clock configuration, FIFO, and gain control

**When to use:**
- Debugging DMIC capture failures (no audio, distortion, noise)
- Verifying PDM clock rates and duty cycle
- Checking DMIC FIFO status and overrun conditions
- Validating CIC decimation filter and gain settings
- Diagnosing DMIC enumeration or BIOS configuration issues
- PCD-H vs PCH-S DMIC routing differences

**Covers:** PDM interface, clock config, FIFO management, CIC filter, gain control, stereo L/R pairing, BIOS knobs

---

### 9. fv-audio/display-audio
**Purpose:** Validate display audio (iDisp) for HDMI/DP — hot plug detect, ELD, multi-stream, codec programming

**When to use:**
- Debugging HDMI/DP audio not working after display connect
- Verifying iDisp codec enumeration and hot plug detect (HPD)
- Reading/validating ELD (EDID-Like Data) for audio capabilities
- Configuring multi-stream transport (MST) audio on DP
- PCD-H (SoundWire Seg0 alt) vs PCH-S (dedicated iDisp link) routing
- Known issue: HSDES-004 HDA hot plug detect missed DP Port 3

**Covers:** iDisp codec, HPD, ELD, MST audio, HDA vs SoundWire iDisp routing, DP/HDMI audio streams

---

### 10. fv-audio/bt-offload
**Purpose:** Validate Bluetooth audio offload via SSP/I2S — SCO/eSCO voice, BT controller integration

**When to use:**
- Debugging BT audio offload path (SSP ↔ BT controller)
- Verifying SSP port configuration (I2S/PCM/TDM mode, BCLK, frame sync)
- Diagnosing SCO/eSCO voice call audio issues
- Checking SSP clock inversion after power gate exit (known issue HSDES-003)
- Validating CNVi ↔ SSP routing for BT audio
- SSP register access and format configuration

**Covers:** SSP/I2S registers, BT SCO/eSCO offload, CNVi integration, BCLK/frame sync, I2S/TDM modes, power gate recovery

---

### 11. fv-audio/uaol
**Purpose:** Validate USB Audio Offload (UAOL) — ACE offload engine, xHCI integration, FIFO timing

**When to use:**
- Debugging UAOL playback/recording failures
- Verifying UAOL offload engine status (ACE3 on PTL, ACE4 on NVL)
- Diagnosing audio glitches or underruns during offloaded USB audio
- Checking UAOL ↔ xHCI integration and isochronous transfer handoff
- Power management: xHCI D-state constraints during UAOL, S0ix interaction
- Platform-specific UAOL support (NVL=full, PTL=yes, LNL/ARL=internal only)
- Known issues: PTL ACE3 recording stuck, NVL ACE4 FIFO sizing

**Covers:** UAOL offload engine, xHCI integration, FIFO timing, ACE3/ACE4 differences, power constraints, ETL debug, platform support matrix

---

### 12. fv-audio/wov
**Purpose:** Validate Wake on Voice (WoV) — always-on keyword detection during S0ix using DMIC + DSP with ultra-low-power Clock Ring Oscillator (CRO)

**When to use:**
- Debugging WoV keyword detection failures (no wake, false wake)
- Verifying CRO clock switching (CLKCTL.WOVROSCS) and XTAL→CRO trunk handoff
- Validating S0ix residency during WoV armed state
- Checking DMIC injector card setup and keyword phrase injection
- Diagnosing WoV automation failures (host↔SUT socket, OpenIPC residency tracking)
- BIOS WoV knob configuration (WoV[X], Intel WoV[X])

**Covers:** WoV architecture, CRO clock (~300μW), DSPWCCTL.DWCS clock source, CLKCTL/CLKSTS registers, WoVClientApplication, S0ix integration, DMIC injector automation, keyword detection pipeline

---

### 13. fv-audio/aioc
**Purpose:** Validate Gen6 AIOC (All-In-One Codec) — Realtek ALC712 combo codec + ALC1320 smart amplifier via SoundWire, SDCA/ACX driver model

**When to use:**
- Setting up Gen6 AIOC hardware (AIC cards, DIP switches, RVP header connections)
- Configuring BIOS for AIOC (SNDW #2 enable, ACX/SDCA enable, topology selection)
- Debugging ALC712 or ALC1320 enumeration failures on SoundWire Segment 2
- Validating 5-Star topology and SDCA function discovery
- Troubleshooting ES vs MP topology mismatch
- Verifying headphone, microphone, and speaker endpoints via AIOC
- Jack detection through ALC712 SoundWire slave alerts

**Covers:** ALC712/ALC1320 codec setup, SoundWire Segment 2, SDCA protocol, ACX driver model, 5-Star topology, AIC hardware config, DIP switches (SW9B2/SW9C1), BIOS knobs, subsystem ID 0x305610EC

---

### 14. fv-audio/jack-detect
**Purpose:** Validate jack detection across HDA pin sense, SoundWire slave alerts, and UAOL USB hot plug

**When to use:**
- Debugging headphone/microphone jack insert/remove not detected (HDA Realtek pin sense)
- Verifying SoundWire slave alert mechanism for jack events (ALC711/ALC722/ALC712-VB)
- Diagnosing USB audio device hot plug detection for UAOL offload path
- Troubleshooting jack type misidentification (headphone vs headset, impedance sensing)
- Verifying unsolicited response delivery (HDA RIRB) or alert clearing (SoundWire SCP_IntClear1)
- Checking xHCI PORTSC.CCS/CSC/PED/PLS for USB audio hot plug

**Covers:** HDA verb 0xF09 pin sense, unsolicited responses (verb 0x708), Realtek pin widget table, SoundWire SCP_IntStat1/IntMask1/IntClear1 IMPL_DEF bit, xHCI PORTSC for UAOL hot plug, jack type impedance classification

> **Note:** Display Audio HPD (HDMI/DP hot plug detect) is **NOT** covered here — see `fv-audio/display-audio` for iDisp HPD.

---

### 15. fv-audio/interrupts
**Purpose:** Understand and debug ACE interrupt architecture — HDA interrupt tree, DSP offload IRQ mapping, MSI/legacy routing

**When to use:**
- Debugging audio interrupts not firing or stuck asserted
- Verifying MSI vs legacy INTA interrupt routing configuration
- Analyzing DSP offload interrupt controller (DW_apb_ictl) IRQ mapping
- Diagnosing IPC interrupt masking issues (HIPCIE/HIPCIS registers)
- Understanding 3-level HDA interrupt hierarchy (SIS→CIS→GIS→IS)
- Checking ACPI interrupt routing (HxPCICFGCTL.ACPIIE)

**Covers:** HDA 3-level interrupt tree (SIS/CIS/PIS/GIS/IS), DSP offload IRQ map (Host IPC, ML, Timers, Watchdog, FW Load), MSI/legacy conditions, HIPCIE per-instance masking, ACPI mode routing, PME wake interrupt path

---

### 16. fv-audio/clocking
**Purpose:** Understand and debug ACE clock architecture — clock sources, PLL/CRO configuration, clock gating, DSP clock requirements

**When to use:**
- Debugging audio clock failures (no output, wrong sample rate, glitches)
- Verifying clock source selection and PLL lock status
- Analyzing clock gating configuration (CLKCTL, FNCFG.CGD)
- Understanding ACE PLL/CRO clock tree and divider chain
- Diagnosing WoV CRO clock switching issues
- Checking DSP firmware clock requirements (common reference clock for UAOL)

**Covers:** 10+ clock sources (XTAL, ACE PLL, Audio PLL, WoV CRO, AON CRO, resume clock), clock gating (CLKCTL, FNCFG.CGD, DCGE), integrated CRO/PLL (CLKINTHVER, VCO frequency switching via INTCLKCTL.FVS), Chassis 2.2 clock_own_req/ack, common reference requirement for UAOL, platform-specific clock mapping (example: NVLDP)

---

### 17. fv-audio/debug
**Purpose:** Systematic audio failure triage — 4-phase methodology with debug playbooks, failure signatures, known sightings, and escalation paths

**When to use:**
- Triaging any audio failure that doesn't have an obvious root cause
- Following a structured debug methodology (Identify Symptom → Check Basic Health → Protocol-Level Debug → Root Cause & Escalate)
- Looking up common failure signatures and their known resolutions
- Checking HSDES sighting database for audio-specific known issues
- Debugging intermittent audio failures (PM-cycle dependent, temperature-dependent)
- Driver crash analysis (IntcAudioBus/IntcSmartSound BSOD)
- DSP firmware load failures (IPC doorbell lost, SRAM PG race)

**Covers:** 8 failure categories (No Device, No Codec, No Audio Output, Glitch/Dropout, PM Failure, FW Load Failure, Driver Crash, Intermittent), 6-check basic health validation, protocol-level debug paths, sub-skill cross-references, known sighting patterns, escalation criteria

---

## PythonSV Quick Start for Audio

```python
import namednodes; from namednodes import *; import baseaccess
itp.unlock(); sv.refresh()

# Find your platform's ACE path (example: NVL PCD-H)
ace = namednodes.sv.socket0.pcd.ace           # ← ADJUST per platform
vid = ace.cfg.vendor_id.read()                # Expect 0x8086
gcap = ace.bar0.gcap.read()                   # HDA Global Capabilities
# DSP access requires GPROCEN=1 in PPCTL first
```

> **⚠️ Base path varies by platform/die.** NVL PCD-H=`socket0.pcd.ace`, NVL PCH-S=`socket0.pch.ace`, MTL SOC-M=`socket0.soc.ace`, PTL/LNL=`socket0.soc.ace`, ARL=`socket0.pch.ace`. Wrong path → "attribute not found". Verify with `namednodes.sv.socket0.search(regexpression="ace")`.
>
> **Full per-platform paths, DIDs, BAR layout, BIOS knobs:** → Load **`fv-audio/platform`**

---

## General Audio Debugging Workflow

> **TIP:** Load `docs/audio_reference_sheets.md` for step-by-step triage decision trees and bring-up checklists.

1. **Identify the affected subsystem** from failure symptoms or test results (HDA/SoundWire/SSP/DSP/DMIC/iDisp/UAOL)
2. **Check known issues first** — load `docs/audio_known_issues.md` and search for matching symptoms
3. **Check hardware config** using `fv-audio/config-checkout` — enumeration, BARs, BIOS
4. **Check subsystem-specific** using `fv-audio/hda`, `fv-audio/soundwire`, `fv-audio/dsp`, `fv-audio/dmic`, `fv-audio/display-audio`, `fv-audio/bt-offload`, `fv-audio/uaol`, `fv-audio/wov`, `fv-audio/aioc`, or `fv-audio/jack-detect`
5. **Analyze power states** using `fv-audio/power` — D3, PLL, SRAM, S0ix blockers
6. **Cross-reference failures** using `fv-audio/failure-analysis` with NGA/sightings
7. **Deep triage with Debugger** using `FV_Debugger_V1` sub-agent — when steps 2-6 don't resolve:
   - Search Confluence wikis (FVCommon, DebugEncyclopedia) for Audio BKMs
   - Run the full 8-phase NGA triage workflow
   - Analyze BSOD/crash dumps if failure involves audio driver in the stack
   - Check PMC firmware version (critical for audio power gating)

### Common Failure Signatures (Quick Reference)

| Symptom | Likely Root Cause | First Action |
|---------|-------------------|--------------|
| Device ID = 0xFFFF | Not enumerated, in D3, or fuse-disabled | `fv-audio/config-checkout` — check BDF + PMCSR |
| BAR reads 0x00000000 | BAR not assigned or device disabled | `fv-audio/config-checkout` — check BAR allocation |
| No codec detected on HDA link | Link not started, STATESTS=0 | `fv-audio/hda` — check GCTL reset, STATESTS |
| CORB/RIRB timeout | Codec not responding to verbs | `fv-audio/hda` — check codec address, link status |
| SoundWire link not starting | SHIM config, bus not enumerated | `fv-audio/soundwire` — check SHIM, link status |
| DSP FW load failure | GPROCEN not set, SRAM not powered | `fv-audio/dsp` — check PPCTL, SRAM PGCTL |
| Buffer underrun during playback | DMA timing, stream config | `fv-audio/hda` or `fv-audio/soundwire` — check stream desc |
| D3 entry timeout | Active stream or pending interrupt | `fv-audio/power` — check stream status, IRQ pending |
| S0ix blocked by audio | ACE not in D3 | `fv-audio/power` — check PMCSR, PLL, active links |
| iDisp audio not working | iDisp codec not detected, wrong routing | `fv-audio/display-audio` — PCD-H: check SDW Seg 0 alt; PCH-S: check dedicated iDisp link |
| Audio distortion / wrong sample rate | Stream config mismatch, codec settings | `fv-audio/hda` — check stream descriptor format, codec verb config |
| DMIC capture silent / noise | PDM clock misconfigured, FIFO overrun | `fv-audio/dmic` — check PDM clock, FIFO status, CIC filter |
| BT audio offload no sound | SSP misconfigured, CNVi routing | `fv-audio/bt-offload` — check SSP config, BCLK, BT controller link |
| BT audio glitch after resume | SSP BCLK inversion lost after PG exit | `fv-audio/bt-offload` — known issue HSDES-003, re-init SSP clocks |
| UAOL playback failure | UAOL engine not active, xHCI constraint | `fv-audio/uaol` — check offload status, xHCI D-state, FIFO |
| UAOL recording stuck | ACE3 FIFO timing issue (PTL) | `fv-audio/uaol` — known issue, check ACE FIFO sizing |
| AIOC codecs not enumerated | SNDW #2 disabled, DIP switches wrong | `fv-audio/aioc` — check BIOS SNDW #2, DIP SW9B2/SW9C1 |
| AIOC no audio endpoints in OS | ACX/SDCA not enabled in BIOS | `fv-audio/aioc` — enable ACX/SDCA + speaker aggregation |
| AIOC speaker silent, headphone works | ALC1320 not initialized | `fv-audio/aioc` — check speaker aggregation BIOS knob, Transducer AIC connection |
| Jack insert not detected (HDA) | Unsolicited response not enabled or RIRB not serviced | `fv-audio/jack-detect` — check verb 0x708, RIRB status |
| SoundWire jack event not firing | Slave alert masked or not cleared | `fv-audio/jack-detect` — check SCP_IntMask1, SCP_IntClear1 |
| USB audio device not detected on plug (UAOL) | xHCI port issue or D3 state | `fv-audio/jack-detect` — check PORTSC.CCS/CSC, xHCI D-state |
| Jack type misidentified (HP vs headset) | Impedance sensing calibration | `fv-audio/jack-detect` — read pin sense impedance bits[30:0] |

> **See also:** `docs/audio_known_issues.md` for HSDES sightings with full reproduction steps and workarounds.

---

## FV-TRIAGE Integration

The FV-TRIAGE agent has built-in audio failure detection patterns. When performing initial failure triage, FV-TRIAGE will detect:

- `AudioDeviceNotFound` — ACE PCI device not enumerated
- `StreamError` — Audio stream setup or runtime errors
- `BufferUnderrun` — DMA buffer underrun during playback/capture
- `CodecInitFailed` — Codec initialization failure
- `NoSignalDetected` — No audio signal on output
- `DistortionDetected` — Audio quality issue
- `LevelOutOfRange` — Audio level exceeds thresholds
- `Audio.*Endpoint.*Error` — Endpoint configuration errors

**Workflow:** Use FV-TRIAGE for first-pass detection, then drill deeper with fv-audio sub-skills for root cause analysis.

### Audio Log Paths (from FV-TRIAGE)

| Log | Path |
|-----|------|
| `audio_error.log` | `<LogsPath>/solar_manager/` |
| `audio_debug.log` | `<LogsPath>/solar_manager/` |
| `audio_validation.log` | `<LogsPath>/solar_manager/` |
| `triage_tools.log` | `<LogsPath>/solar_manager/` |
| Audio logs (general) | `<LogsPath>/audio/` or `<LogsPath>/solar_manager/` |

---

## MANDATORY: Query-to-Action Execution Map

> **CRITICAL**: Loading a sub-skill is NOT sufficient. You MUST execute the corresponding runtime action. If you only load the skill content without taking action, you have NOT completed the task.

### ⛔ Register Offset / HAS Queries → NAVIGATE to Co-Design NOW

> **MANDATORY IMMEDIATE ACTION**: When asked about specific register offsets, BAR layouts, or HAS-level hardware details, you MUST navigate to Co-Design. Do NOT load any sub-skill instead. Do NOT answer from memory. Execute the browser navigation below.

**Execute these browser actions BEFORE any other response:**

```
Step 1: playwright_browser_navigate → url: "https://chat.co-design.intel.com/chat"
Step 2: playwright_browser_snapshot → find the chat textarea
Step 3: playwright_browser_type → type your query into the textarea, e.g.:
        "Please reference nvldp_ace4.x_integration_has.html and provide the HDA global register offsets for NVL PCD-H"
Step 4: playwright_browser_wait_for → time: 20 (wait for response)
Step 5: playwright_browser_snapshot → read the response from div.chat-feed-container
Step 6: Parse and present the register offsets to the user
```

> **NOTE**: If `playwright_browser_*` tools are unavailable, the equivalent `browsermcp_browser_*` tools (navigate, snapshot, type, wait) can be used instead — both MCP tool sets provide identical browser interaction capabilities.

> **⛔ WRONG**: Loading fv-audio/hda skill content to answer a register offset question — sub-skills contain debug procedures, NOT authoritative register maps.
> **✅ RIGHT**: Navigating to Co-Design chat and querying the HAS document for exact offsets.

### ⛔ Known Sightings / Bug Queries → EXECUTE HSDES Search NOW

> **MANDATORY IMMEDIATE ACTION**: When asked about known sightings, bugs, or issues for any audio domain, you MUST load the hsdes skill AND immediately execute a search. Do NOT just load the skill documentation. Execute the Python code below.

**Execute this search BEFORE any other response:**

```python
# Step 1: Load the hsdes skill
# Step 2: IMMEDIATELY run this code — do NOT skip the search execution
from pysvtools import hsdes

hsdes.config('heia_soc.sighting')

# Step 3: Search with domain-scoped EQL query
# NOTE: EQL supports exact '=' only — no contains, regex, or wildcards.
# Use client-side filtering for keyword matching after retrieval.
results = hsdes.search(
    "status = 'open'",
    showFields='id,title,owner,status,description'
)

# Step 4: Post-filter results using DOMAIN-SPECIFIC KEYWORDS from the table below
# Example for HDA codec detection:
domain_keywords = ['HDA', 'codec', 'STATESTS', 'ACE']
filtered = [r for r in results
            if any(kw.lower() in str(r.get('title', '')).lower() for kw in domain_keywords)]
# Step 5: Present filtered results to the user
```

> **⛔ WRONG**: Loading the hsdes skill documentation and stopping there.
> **✅ RIGHT**: Loading the hsdes skill AND executing `hsdes.search()` with domain keywords.

**Mandatory HSDES search keywords by audio domain:**

| Domain | Required Keywords (include at least 3 in your search/filter) |
|--------|---------------------------------------|
| HDA codec | `HDA`, `codec`, `STATESTS`, `NVL`, `ACE`, `SDI`, `detection` |
| SoundWire | `SoundWire`, `SNDW`, `enumeration`, `segment`, `codec`, `ACE` |
| DSP / firmware | `DSP`, `firmware`, `CPA`, `ADSPCS`, `GPROCEN`, `ACE`, `load` |
| DMIC | `DMIC`, `PDM`, `clock`, `capture`, `ACE`, `NVL` |
| Display Audio | `iDisp`, `display`, `audio`, `HDMI`, `DP`, `ELD`, `HDA` |
| UAOL | `UAOL`, `USB`, `audio`, `offload`, `ACE`, `xHCI` |
| Power / PM | `audio`, `D3`, `S0ix`, `CGCTL`, `LTR`, `power`, `ACE` |
| AIOC | `AIOC`, `ALC712`, `ALC1320`, `SDCA`, `ACX`, `SoundWire` |

### Debug / Triage Queries → Load Sub-Skill AND Execute Checks

When asked to **debug or triage** an audio issue:

1. **Load** the appropriate fv-audio sub-skill (e.g., `fv-audio/soundwire`)
2. **IMMEDIATELY execute** the mandatory register checks listed in that sub-skill's debug checklist
3. For SoundWire enumeration: **MUST read SHIM.LCTL** and segment clock config — see `fv-audio/soundwire` Enumeration Failure Debug Checklist
4. For DSP issues: **MUST check ADSPCS/PPCTL** core status bits
5. For power issues: **MUST read CGCTL and LTR registers**

> **INSUFFICIENT**: Loading the sub-skill and describing what *should* be checked. You must show the actual register read commands or PythonSV code executing those checks.

### NGA Test Result Queries → Execute NGA Search with Audio Filters

When asked about **NGA test results** for audio:

1. **Load** the `nga/results` or `nga/search` skill
2. **Execute** a search filtered for audio tests — include parameters like `project`, `platform=<PROJECT>`, and filter for audio test names or suite names
3. **Parse** and present the results

---

## Related Skills

- **FV_Debugger_V1**: General debug agent with Confluence wiki knowledge — search FVCommon & DebugEncyclopedia for Audio BKMs, run 8-phase NGA failure triage
- **pysv**: PythonSV register access and silicon validation
- **nga**: NGA test automation and failure tracking
- **sighting-info**: HSDES sighting lookup
- **hsdes**: Direct HSDES query — **ALWAYS execute searches with domain-specific keywords from the table above**
- **codesign**: Co-Design HAS document lookup — **ALWAYS navigate to https://chat.co-design.intel.com/chat for register offset queries**
- **onebkc**: BKC/firmware version information
- **securewiki**: Confluence wiki access (used by FV_Debugger_V1 for wiki searches)
