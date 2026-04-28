# Audio Known Issues & Sighting Tracker
> **Owner**: huiyingt (Tan Hui Ying)

> **Last updated:** 2026-04-06
> **Scope:** HDA, SoundWire, SSP/I2S, DSP, DMIC, UAOL, Codecs on NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
>
> This file tracks confirmed bugs, HSDES sightings, and known workarounds for Audio/ACE IP validation.
> Format follows the FV structured issue tracker pattern for agent consumption.
>
> ⚠️ **HSDES Filing Status (April 2026 audit):** All issues below marked "Not yet filed" represent
> confirmed bugs or sightings that have NOT been formally filed in HSDES. These should be filed
> in `sighting_central.sighting` tenant with appropriate severity and component classification.
> See the [HSDES filing checklist](#hsdes-filing-checklist) at the bottom of this file.

---

## Issue Classification

| Prefix | Category | Description |
|--------|----------|-------------|
| BUG-xxx | RTL/IP Bug | Confirmed silicon or IP-level defect |
| HSDES-xxx | Sighting | Filed in HSDES with tracking ID |
| CONFIG-xxx | Configuration | BIOS/FW/driver misconfiguration that mimics a bug |
| KERN-xxx | OS/Driver Fix | Linux kernel or Windows driver patch |
| FW-xxx | DSP Firmware | SOF/Intel FW bug or workaround |

---

## Critical RTL Bugs

### BUG-001: CORB/RIRB DMA Stall After D3 → D0 Transition

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | Critical |
| **Affected IP** | HDA Controller (ACE 4.x) |
| **Affected Platforms** | NVL (PCD-H) — observed on A0 stepping |
| **Root Cause** | After D3 cold exit, CORB/RIRB base address registers may not be restored correctly by driver; CORBWP and RIRBRP pointers mismatch |
| **Symptoms** | (1) Codec verb commands timeout; (2) CORBSTS shows Memory Error Indication (MEI) bit set; (3) No audio output after resume from S3/S4 |
| **Workaround** | Full CORB/RIRB re-initialization: stop DMA engines → reset pointers → reprogram base addresses → restart DMA |
| **VJT Status** | Not yet automated — manual verification using PythonSV |

**Quick Check:**
```python
import namednodes as nn
nn.sv.refresh()
die = nn.sv.socket0.pcd  # PCH-S: socket0.pch

# Read CORB status
corbsts = die.ace.hda.bar0.corbsts.read()
print('CORBSTS = 0x%02X' % corbsts)
print('MEI (Memory Error) = %d' % ((corbsts >> 0) & 1))

# Read RIRB status
rirbsts = die.ace.hda.bar0.rirbsts.read()
print('RIRBSTS = 0x%02X' % rirbsts)
print('RINTFL (Response Interrupt) = %d' % ((rirbsts >> 0) & 1))
print('OIS (Overrun) = %d' % ((rirbsts >> 2) & 1))
```

---

### BUG-002: SoundWire Bus Reset Fails on Segment 4 (On-Die iDisp)

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | High |
| **Affected IP** | SoundWire Link 4 (on-die iDisp-A/CNVi alternate) |
| **Affected Platforms** | NVL (PCD-H) |
| **Root Cause** | Segment 4 shares pin mux with iDisp-A and CNVi; bus reset sequence may be blocked when alternate function is active |
| **Symptoms** | SNDW bus reset command does not complete; SoundWire device enumeration hangs on Link 4 |
| **Workaround** | Ensure iDisp-A and CNVi alternate functions are disabled before SoundWire Link 4 initialization |
| **VJT Status** | Not yet automated |

---

### BUG-003: DSP Core 3/4 Fail to Wake from Clock Gate (PCD-H Only)

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | High |
| **Affected IP** | HiFi5 HP Cores 3 and 4 |
| **Affected Platforms** | NVL PCD-H (4 HP cores) — does NOT affect PCH-S (2 HP cores) |
| **Root Cause** | SRAM power gate sequencing for core 3/4 may leave them in intermediate state when CGPG is aggressive |
| **Symptoms** | ADSPCS.CPA (Core Power Active) does not assert for Core 3 or Core 4 within expected timeout |
| **Workaround** | Sequence core power-up: Core 0 (ULP) first → Core 1 → Core 2 → wait 1ms → Core 3 → Core 4 |

---

### BUG-004: UAOL PSF Glitch on DfSPSREQ Deassertion (Multi-Platform)

| Field | Value |
|-------|-------|
| **HSDES** | 1804300* series — multiple related sightings |
| **Severity** | High |
| **Affected IP** | UAOL offload engine in ACE |
| **Affected Platforms** | MTL, PTL, NVL — any platform with UAOL |
| **Root Cause** | PSF primary interface may glitch during DfSPSREQ deassertion when UAOL is actively streaming, causing momentary transaction corruption |
| **Symptoms** | Audio stream corruption or xHCI transfer ring stall during UAOL playback |
| **Workaround** | Ensure clean stream stop before UAOL power state transition |
| **Reference** | See `fv-audio/uaol/SKILL.md` — PSF glitch risk documentation |

---

### BUG-005: MTL UAOL Behind-Hub Topology Broken (RTL Bug)

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | High |
| **Affected IP** | UAOL offload engine |
| **Affected Platforms** | MTL only (fixed in PTL/NVL) |
| **Root Cause** | RTL bug in MTL UAOL engine prevents correct routing of isochronous transfers to USB devices connected behind a hub |
| **Symptoms** | UAOL audio playback fails when USB audio device is connected through a USB hub; works when directly connected |
| **Workaround** | Connect USB audio devices directly to root port (no hub); or disable UAOL and use standard USB audio path |
| **Status** | Fixed in PTL and later platforms |

---

## HSDES Sightings

### HSDES-001: S0ix Blocked by ACE Controller Stuck in D0

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | High |
| **Affected Platforms** | NVL (PCD-H, PCH-S), PTL, LNL, MTL |
| **Description** | ACE controller (0:31:3) fails to enter D3 during OS idle, blocking S0ix entry. PMCSR reads 0x00 (D0) instead of 0x03 (D3) |
| **Root Cause** | Pending DMA on active stream, codec link not in reset, or DSP firmware not releasing resources |
| **Detection** | Read PMCSR (PCI+0x84) bits[1:0]; value != 0x3 blocks S0ix |
| **Resolution** | Stop all active streams → put all links in reset → shut down DSP cores → clear pending interrupts |

### HSDES-002: SoundWire Clock Stop Abort on Multi-Drop Bus

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | Medium |
| **Affected Platforms** | NVL (PCD-H, PCH-S), PTL |
| **Description** | Clock Stop Mode 1 command aborts when multiple codecs are on the same SoundWire segment and one codec NAKs the prep sequence |
| **Root Cause** | One device on the multi-drop bus does not support Clock Stop Mode 1; master abort cascades |
| **Detection** | SNDW SHIM registers show clock stop abort status |
| **Workaround** | Use Clock Stop Mode 0 (simple) for buses with mixed codec support; or detach non-supporting codec first |

### HSDES-003: SSP BCLK Inversion Not Applied After Power Gate Exit

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | Medium |
| **Affected Platforms** | NVL (PCH-S), PTL |
| **Description** | SSP BCLK polarity inversion setting lost after SSP power gate exit; audio stream has inverted clock edge |
| **Root Cause** | SSP configuration register (SSPC) not restored after power gate |
| **Workaround** | Re-apply SSPC configuration after each power gate exit; driver should re-initialize SSP params |

### HSDES-004: HDA Hot Plug Detect Missed for DP Port 3

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | Medium |
| **Affected Platforms** | NVL (PCD-H) |
| **Description** | iDisp Audio codec does not generate unsolicited response for DisplayPort Port 3 hot-plug event |
| **Root Cause** | Pin sense configuration for iDisp Port 3 may not be enabled by default |
| **Detection** | Read STATESTS (offset 0x0E) — should have bit set for iDisp codec after DP plug |
| **Workaround** | Explicitly poll pin sense for each iDisp pin widget; do not rely solely on unsolicited responses |

### HSDES-005: AIOC ALC712 Not Enumerated on SoundWire Segment 2

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | High |
| **Affected Platforms** | NVL (5-Star topology boards) |
| **Description** | ALC712 AIOC codec (Device ID 0x305610EC) fails to enumerate on SoundWire Segment 2 despite correct BIOS configuration |
| **Root Cause** | Multi-segment resource conflict when Segment 0 (HDA alt) and Segment 2 (AIOC) are both active; SHIM configuration order matters |
| **Detection** | SoundWire device enumeration on Seg 2 returns no devices; SHIM_IOCTL shows link not powered |
| **Workaround** | Initialize Segment 2 before Segment 0 alt path; or disable Seg 0 alt if not needed |

### HSDES-006: BT Audio Offload Blocking S0ix Entry

| Field | Value |
|-------|-------|
| **HSDES** | Not yet filed |
| **Severity** | Medium |
| **Affected Platforms** | NVL, PTL |
| **Description** | Active BT audio offload stream (HFP or A2DP via SSP/I2S) keeps ACE in D0, preventing S0ix entry even when no audio is playing |
| **Root Cause** | CNVi interface holds SSP link active; BT firmware does not signal idle to ACE driver |
| **Detection** | PMCSR shows D0 during idle; SSP link status shows active BCLK |
| **Workaround** | Ensure BT audio profile disconnects cleanly when idle; driver should tear down SSP link on inactivity timeout |

---

## Configuration Issues

### CONFIG-001: ACE Device Disabled in BIOS

| Field | Value |
|-------|-------|
| **Severity** | High (causes total loss of function) |
| **Affected Platforms** | All (NVL, PTL, LNL, MTL) |
| **Description** | Audio device (0:31:3) reads Device ID 0xFFFF — device disabled in BIOS |
| **Root Cause** | BIOS setup option "HD Audio" set to Disabled, or PCH strap disabling ACE function |
| **Detection** | `fv-audio/config-checkout` — reads VID:DID at 0:31:3 |
| **Resolution** | Enable "HD Audio" in BIOS setup; verify PCH soft strap via DFx |

### CONFIG-002: DSP BAR2 Not Enabled (GPROCEN=0)

| Field | Value |
|-------|-------|
| **Severity** | High (blocks all DSP register access) |
| **Affected Platforms** | All |
| **Description** | BAR2 (DSP domain, 2MB) reads as 0 or returns all-1s; DSP registers inaccessible |
| **Root Cause** | PPCTL.GPROCEN bit not set by BIOS/driver; BAR2 is only active when GPROCEN=1 |
| **Detection** | `fv-audio/config-checkout` — reads PPCTL (BAR0+0x1004) bit 30 |
| **Resolution** | Set PPCTL.GPROCEN=1 to enable BAR2 DSP domain access |

### CONFIG-003: SoundWire Link Not Enabled in BIOS

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Affected Platforms** | All |
| **Description** | SoundWire codecs not detected; SHIM registers show link disabled |
| **Root Cause** | BIOS SoundWire enable knob not set, or incorrect link count configured |
| **Detection** | Read SHIM LCTL register — SPA (Sync Power Active) bit should be set for enabled links |
| **Resolution** | Enable SoundWire links in BIOS; verify link count matches platform BOM |

### CONFIG-004: Wrong Codec Address on HDA Link

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Affected Platforms** | All |
| **Description** | Codec discovery finds wrong address or mismatched VID/DID; verbs routed to wrong codec |
| **Root Cause** | Board wiring or BIOS pin configuration maps codec to unexpected SDI index |
| **Detection** | STATESTS shows codec present on unexpected SDI; Verb F00 (Root Node) returns unexpected VID |
| **Resolution** | Verify board schematic for SDI routing; adjust driver codec address table |

### CONFIG-005: DMIC Not Captured — GPIO Pad Mode Misconfigured

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Affected Platforms** | All — especially NVL, PTL |
| **Description** | DMIC microphones not detected or no audio captured; DMIC controller shows no data flow |
| **Root Cause** | GPIO pad mode for DMIC_CLK_A/B and DMIC_DATA_A/B pins not set to Native Function (PMode != NF) |
| **Detection** | Check GPIO pad configuration for DMIC pins; verify PMode is set to correct native function |
| **Resolution** | Set BIOS DMIC enable knob; verify GPIO pad configuration matches DMIC native function routing |

### CONFIG-006: FNCFG.CGD Stuck — Clock Gating Disabled

| Field | Value |
|-------|-------|
| **Severity** | Medium (performance/power impact) |
| **Affected Platforms** | All |
| **Description** | Clock gating control bit CGD=1 in FNCFG register prevents audio IP from entering low-power clock gated state |
| **Root Cause** | Debug override or incorrect BIOS configuration leaves CGD (Clock Gate Disable) set |
| **Detection** | Read PCI Config FNCFG register — CGD bit should be 0 for normal operation |
| **Resolution** | Clear FNCFG.CGD=0; check if debug BIOS knobs are overriding clock gating |

---

## DSP Firmware Issues

### FW-001: SOF Firmware Load Timeout on Cold Boot

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Affected Platforms** | NVL (PCD-H, PCH-S), PTL — Linux SOF driver |
| **Description** | SOF firmware DMA transfer does not complete within timeout; DSP stays in ROM state |
| **Root Cause** | SRAM power gate not fully exited before firmware DMA starts |
| **Detection** | dmesg shows `sof-audio: firmware load timeout`; ADSPCS shows CPA=0 for target core |
| **Resolution** | Ensure all SRAM banks powered before initiating firmware DMA; check SRAM PGCTL register |

### FW-002: IPC Doorbell Lost During D0i3 Exit

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Affected Platforms** | NVL (PCD-H, PCH-S), PTL, LNL |
| **Description** | Host-to-DSP IPC message sent immediately after D0i3 exit may be lost; pipeline fails to restart |
| **Root Cause** | IPC registers not fully restored before host writes doorbell |
| **Detection** | IPC timeout errors in driver log; HIPCIDR.BUSY stuck at 1 |
| **Workaround** | Wait for ADSPCS.CPA assertion and additional 1ms before first IPC after D0i3 exit |

### FW-003: DMIC xosc_clk 38.4 MHz Misconfigured for PDM Clock

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Affected Platforms** | NVL, PTL |
| **Description** | DMIC PDM clock derived from xosc_clk at 38.4 MHz may produce incorrect sample rate if clock divider is not set correctly |
| **Root Cause** | Firmware/driver does not account for 38.4 MHz base clock when configuring PDM clock divider ratio |
| **Detection** | DMIC capture produces audio at wrong sample rate; clock verification shows incorrect PDMCLKCTL value |
| **Workaround** | Verify DMIC clock configuration matches expected base crystal frequency; adjust divider ratio |

---

## Platform-Specific Notes

### LNL (Lunar Lake)

| Area | Note |
|------|------|
| **UAOL** | LNL has internal UAOL (ACE 2.x) but does NOT support behind-hub USB audio offload |
| **ACE Version** | ACE 2.0 — different register offsets from ACE 3.x/4.x on PTL/NVL |
| **Known Issues** | See wiki page `LNL ACE 2.0 Audio issues` [Page ID: 3051461460] |

### MTL (Meteor Lake)

| Area | Note |
|------|------|
| **UAOL** | Behind-hub topology broken due to RTL bug (see BUG-005); direct-connect only |
| **ACE Version** | ACE 3.x — first generation with UAOL support |
| **Debug BKM** | See wiki page `MTL ACE AUDIO Debug BKM` [Page ID: 2942039705] |
| **Debug Traces** | See wiki page `Audio debug-traces - MTL` [Page ID: 2638580577] |

### PTL (Panther Lake)

| Area | Note |
|------|------|
| **UAOL** | Supported — behind-hub fix from MTL applied |
| **ACE Version** | ACE 3.x+ |
| **Audio FW Log** | See wiki page `[PTL]Audio FW log` [Page ID: 3484618181] |
| **Xtensa Debug** | See wiki page `[PTL]Audio Xtensa` [Page ID: 3516740381] |

### NVL (Novalake)

| Area | Note |
|------|------|
| **UAOL** | Supported — full behind-hub support, ACE 4.x engine |
| **ACE Version** | ACE 4.x — 4 HP cores (PCD-H) or 2 HP cores (PCH-S) |
| **Debug Handbook** | See wiki page `NVL ACE(Audio) Debug Handbook` [Page ID: 4153877501] |
| **AIOC** | ALC712/ALC1320 5-Star topology on select boards |
| **BT Offload** | NVL-S DT: A2DP/HFP/LE Audio offload via SSP [Page ID: 4278948453] |

---

## Search Keywords for HSDES

When searching for new Audio/ACE sightings in HSDES, use these keyword combinations:

```
# General Audio/ACE
"ACE" AND ("NVL" OR "PTL" OR "LNL" OR "MTL") AND ("audio" OR "HDA" OR "SoundWire" OR "SSP")
"Audio" AND ("D3" OR "S0ix" OR "power gate" OR "clock gate") AND ("NVL" OR "PTL")

# HDA specific
"HDA" AND ("CORB" OR "RIRB" OR "codec" OR "verb" OR "unsolicited") AND ("NVL" OR "PTL")
"iDisp" AND ("hot plug" OR "HDMI" OR "DisplayPort") AND ("NVL" OR "PTL" OR "LNL")
"STATESTS" AND ("codec" OR "detect" OR "enumeration")

# SoundWire specific
"SoundWire" AND ("clock stop" OR "bus reset" OR "enumeration" OR "multi-drop")
"SNDW" AND ("SHIM" OR "ALH" OR "link" OR "segment") AND ("NVL" OR "PTL")

# DSP specific
"DSP" AND ("HiFi5" OR "firmware" OR "IPC" OR "SRAM" OR "GPROCEN") AND ("NVL" OR "PTL")
"ADSPCS" AND ("CPA" OR "core" OR "power" OR "stall")
"SOF" AND ("timeout" OR "firmware load" OR "D0i3") AND ("NVL" OR "PTL" OR "LNL")

# DMIC specific
"DMIC" AND ("pad mode" OR "GPIO" OR "PDM" OR "clock" OR "gain") AND ("NVL" OR "PTL")

# SSP/I2S specific
"SSP" AND ("BCLK" OR "I2S" OR "TDM" OR "clock") AND ("NVL" OR "PTL")

# UAOL specific
"UAOL" AND ("offload" OR "xHCI" OR "FIFO" OR "behind-hub" OR "isochronous") AND ("NVL" OR "PTL" OR "MTL")

# AIOC specific
"AIOC" AND ("ALC712" OR "ALC1320" OR "5-Star" OR "SoundWire" OR "SDCA") AND "NVL"

# Power management
"ACE" AND ("PMCSR" OR "D0i3" OR "D3" OR "S0ix" OR "LTR") AND ("NVL" OR "PTL")
"HDAPLLCTL" AND ("PLL" OR "lock" OR "audio" OR "clock")
"SRAM" AND ("power gate" OR "PGCTL") AND "ACE"
"CGCTL" AND ("clock gate" OR "audio" OR "ACE")
```

---

## Filing New Sightings — BKM

When filing a new Audio/ACE sighting in HSDES:

| Field | Recommended Value |
|-------|-------------------|
| **Tenant** | `client_platf_i_val` or relevant project tenant |
| **Subject** | `sighting` |
| **Domain** | `functional_validation` |
| **Component** | `audio` or `ace` or `hda` |
| **Title** | `[<PLATFORM>] Audio <HDA/SoundWire/SSP/DSP/DMIC/UAOL>: <brief symptom>` |
| **Description** | Include: platform, die, stepping, BKC version, register dump, reproduction steps |
| **Attachments** | PythonSV register dumps, NGA test logs, codec dump, DSP trace |

**Required information in description:**
1. Platform + die + stepping (e.g., NVL PCD-H A0, PTL-H B0)
2. Affected subsystem (HDA Link, SoundWire Segment N, SSP Port N, DSP Core N, DMIC, UAOL)
3. BKC version and PMC/DSP firmware version
4. Register dump (PMCSR, GCTL, STATESTS, CORB/RIRB status, SHIM regs, ADSPCS)
5. Reproduction steps (PythonSV commands or test script name)
6. Expected vs actual behavior
7. Workaround if known

---

## HSDES Filing Checklist

> **Audit date**: April 2026 | **Status**: 15 of 20 issues have "Not yet filed" HSDES IDs

The following issues need to be filed in HSDES. Priority order (file Critical/High first):

| Issue ID | Title | Severity | HSDES Status | Priority to File |
|----------|-------|----------|-------------|-----------------|
| BUG-001 | CORB/RIRB DMA Stall After D3→D0 | Critical | ❌ Not filed | **P1** — gate blocker |
| BUG-002 | SoundWire Bus Reset Fails on Seg 4 | High | ❌ Not filed | **P1** |
| BUG-003 | DSP Core 3/4 Fail to Wake from Clock Gate | High | ❌ Not filed | **P1** |
| BUG-004 | UAOL PSF Glitch on DfSPSREQ | High | 🔶 Partial (1804300* series) | Confirm exact IDs |
| BUG-005 | MTL UAOL Behind-Hub Broken | High | ❌ Not filed | P2 (MTL only, fixed in PTL+) |
| HSDES-001 | S0ix Blocked by ACE in D0 | High | ❌ Not filed | **P1** — S0ix blocker |
| HSDES-002 | SoundWire CLK_STOP Abort Multi-Drop | Medium | ❌ Not filed | P2 |
| HSDES-003 | SSP BCLK Inversion After PG Exit | Medium | ❌ Not filed | P2 |
| HSDES-004 | HDA Hot Plug Missed for DP Port 3 | Medium | ❌ Not filed | P2 |
| HSDES-005 | AIOC ALC712 Not Enumerated on Seg 2 | High | ❌ Not filed | **P1** — AIOC blocker |
| HSDES-006 | BT Audio Offload Blocking S0ix | Medium | ❌ Not filed | P2 |

**Filing tenant**: `sighting_central.sighting`
**Title format**: `[NVL/PTL] Audio <subsystem>: <symptom>`
**Required fields**: See "Filing New Sightings — BKM" section above
