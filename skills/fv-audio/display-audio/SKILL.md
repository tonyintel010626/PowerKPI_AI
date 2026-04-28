---
name: fv-audio/display-audio
description: "Display Audio (iDisp) validation — HDMI/DisplayPort audio, hot plug detection, ELD readback, MST, HDA and SoundWire Seg0 Alt paths"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# FV-AUDIO: Display Audio (iDisp) Sub-Skill

> **Scope**: Display audio validation on NVL (Novalake) platforms — HDMI/DisplayPort audio via Intel Display Audio (iDisp) codec, hot plug detection, ELD readback, multi-stream transport (MST), and SoundWire Seg0 alternate path.

---

## Architecture Overview

Display Audio (iDisp) delivers audio over HDMI and DisplayPort connections. On NVL, display audio can be routed through two paths:

1. **HDA Path**: Traditional HDA link using the built-in Intel Display Audio codec
2. **SoundWire Seg0 Alt**: Alternate routing via SoundWire Segment 0 for iDisp traffic

### Hardware Configuration

| Feature | PCD-H (NVL) | PCH-S (NVL) |
|---------|-------------|-------------|
| Display Audio Codec | Intel iDisp (onboard) | Intel iDisp (onboard) |
| Max Simultaneous Streams | 3 (one per display output) | 3 |
| HDMI Ports | Up to 3 (platform-dependent) | Up to 3 |
| DisplayPort (DP) Ports | Up to 4 (platform-dependent) | Up to 4 |
| HDA Path | Via SDI (STATESTS) | Via SDI (STATESTS) |
| SoundWire Alt Path | Seg0 alternate mode | Seg0 alternate mode |
| Audio Formats | LPCM, compressed (IEC 61937) | LPCM, compressed (IEC 61937) |
| Max Sample Rate | 192 kHz | 192 kHz |
| Max Channels | 8ch (7.1) per stream | 8ch (7.1) per stream |

### Signal Path

```
                    ┌──────────────────┐
                    │    Display Engine │
                    │    (GT/Graphics)  │
                    └───────┬──────────┘
                            │ Hot Plug Event
                            ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐
│  DSP    │◄──►│  iDisp Codec     │───►│ HDMI/DP PHY   │──► Display + Audio
│ Pipeline│    │  (HDA or SWire)  │    │ (Combo PHY)   │
└─────────┘    └──────────────────┘    └───────────────┘
```

### Display Audio via HDA

The iDisp codec appears as an HDA codec on SDI, discovered via the STATESTS register. It uses standard HDA verb programming for configuration.

### Display Audio via SoundWire Seg0 Alt

On NVL, display audio can alternatively route through SoundWire Segment 0 in alternate mode. This path shares the physical segment with external SoundWire codecs — **mutually exclusive** with external codec use on Seg0.

### SoundWire Seg0 Alt Configuration and Verification

When iDisp is routed via SoundWire Seg0 alternate mode (instead of HDA), the following applies:

| Aspect | Detail |
|--------|--------|
| **BIOS knob** | `SNDW #0` = **Enabled** with display audio alt mode topology selected |
| **HDA path** | Disabled (iDisp codec will NOT appear in STATESTS) |
| **Mutual exclusion** | External codecs on Seg0 cannot be used simultaneously |
| **Driver model** | SoundWire bus driver manages iDisp endpoint (not HDA codec driver) |

#### PythonSV — Verify SoundWire Seg0 Alt Link Status

```python
# SoundWire Seg0 Alt Path — verify link is active for iDisp routing
# NOTE: SoundWire SHIM register namednode paths require ACE HAS verification.
# The paths below follow the standard namednode pattern for ACE 4.x on NVL.
# If paths fail, query Co-Design: "SoundWire SHIM LCTL register for Segment 0 in ACE HAS"

import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

die = namednodes.sv.socket0.pcd   # PCD-H; use .pch for PCH-S

# Check SoundWire Segment 0 link control
# SHIM LCTL (Link Control) — one per segment
# HAS verification required: exact namednode path may vary by ACE version
# Pattern: die.ace.sndw.shim.lctlN  where N = segment number
try:
    lctl0 = die.ace.sndw.shim.lctl0.read()
    spa  = (lctl0 >> 0) & 1   # SPA (SyncPoint Active) — link started
    cpa  = (lctl0 >> 8) & 1   # CPA (Current Power Active) — link powered
    print("SHIM LCTL0: 0x%08X — SPA=%d, CPA=%d" % (lctl0, spa, cpa))
    if spa and cpa:
        print("  SoundWire Seg0 link is active")
    else:
        print("  WARNING: Seg0 link not active — check BIOS SNDW #0 = Enabled")
except Exception as e:
    print("  Could not read SHIM LCTL0 — verify namednode path for your platform")
    print("  Try: sv.socket0.pcd.ace.sndw  and browse child nodes")
    print("  Error: %s" % e)

# When Seg0 Alt is active, iDisp codec will NOT appear in HDA STATESTS.
# Instead, verify via SoundWire device enumeration:
#   Linux: cat /sys/bus/soundwire/devices/*/dev-properties
#   Windows: Device Manager → Sound → SoundWire display audio endpoint
```

> **IMPORTANT**: When switching between HDA path and SoundWire Seg0 Alt path, a full platform reboot is required after changing the BIOS topology selection. The SoundWire SHIM must be re-initialized during boot — hot-switching is not supported.

---

## Multi-Platform iDisp Support

| Platform | ACE Version | iDisp Support | iDisp Path Options | Notes |
|----------|-------------|---------------|-------------------|-------|
| **NVL PCD-H** | ACE 4.x | Yes | HDA SDI + SoundWire Seg0 Alt | Reference implementation |
| **NVL PCH-S** | ACE 4.x | Yes | HDA SDI + SoundWire Seg0 Alt | On-die iDisp via Seg 4 |
| **PTL** | ACE 3.0 | Yes | Consult PTL ACE HAS for path options | PCD/SOC die |
| **WCL** | ACE 3.0 | Yes | Same as PTL — HDA SDI + SoundWire Alt | Shares PTL ACE 3.x architecture |
| **TTL (ACE 4.0)** | ACE 4.0 | Yes | *(verify HAS)* — expected HDA SDI + SoundWire Alt | ACE4 variant — similar to NVL |
| **TTL (ACE 3.0)** | ACE 3.0 | Yes | *(verify HAS)* — expected same as PTL | ACE3 variant |
| **RZL** | ACE 4.0 | Yes | *(verify HAS)* — expected HDA SDI + SoundWire Alt | ACE4 — same iDisp architecture as NVL |
| **LNL** | ACE 2.x | Yes | Consult LNL HAS | Monolithic SOC die |
| **MTL** | ACE 1.5 | Yes | Consult MTL HAS | SOC-M and PCH-S variants |
| **ARL-U** | ACE 1.5 | **NO iDisp** | iDisp removed on ARL-U | Display audio via alternate path only |
| **ARL-S** | ACE 1.5 | Yes | Consult ARL-S HAS | — |

> **CRITICAL**: ARL-U has **no Intel Display Audio (iDisp) codec**. Do not attempt iDisp-based display audio validation on ARL-U platforms — tests will fail by design. Confirm platform variant (ARL-U vs ARL-S) before running iDisp test suites.

> **WCL/TTL/RZL debug approach**: For iDisp issues on WCL, apply PTL debug procedures (same ACE 3.x). For TTL ACE 4.0 and RZL, apply NVL debug procedures (same ACE 4.x iDisp routing).

---

## Key Registers

### HDA Registers for iDisp (BAR0)

| Offset | Register | Bits | Description |
|--------|----------|------|-------------|
| 0x0E | STATESTS | [14:0] Codec detect | Bit set = codec present on SDI. iDisp typically on SDI 2 |
| 0x08 | GCTL | [0] CRST | Controller reset — must be 1 for codec discovery |
| 0x40 | CORBLBASE | [31:0] | CORB base address (verb commands to codec) |
| 0x50 | RIRBLBASE | [31:0] | RIRB base address (verb responses from codec) |
| 0x58 | RINTCNT | [7:0] | Response interrupt count |
| 0x80+ | Stream Desc | 0x20 stride | Output stream descriptors for audio playback |

### iDisp Codec Verb Commands

| Verb/Parameter | NID | Description |
|---------------|-----|-------------|
| GET_PARAMETER (0xF00) | Root (0x00) | Vendor ID, Revision, Subordinate node count |
| GET_PARAMETER (0xF00) | AFG (0x01) | Audio Function Group capabilities |
| GET_PIN_WIDGET_CONTROL | Pin NIDs | Pin enable, EPT (Encapsulated Packet Type) |
| GET_CONN_LIST | Pin NIDs | Connection list for pin routing |
| SET_CHANNEL_STREAMID | Converter NIDs | Associate converter with stream |
| GET_HDMI_DIP_SIZE | Pin NIDs | Data Island Packet buffer size |
| SET_HDMI_DIP_DATA | Pin NIDs | Write Audio InfoFrame data |
| GET_HDMI_ELD_DATA | Pin NIDs | Read ELD (EDID-Like Data) from display |

### ELD (EDID-Like Data) Structure

ELD contains the audio capabilities of the connected display, read from the EDID:

| Field | Offset | Description |
|-------|--------|-------------|
| ELD Version | 0 | Format version (typically 0x02) |
| Baseline Length | 1 | Length of baseline ELD block |
| Monitor Name Len | 2[4:0] | Characters in monitor name |
| SAD Count | 2[7:4] | Number of Short Audio Descriptors |
| Conn Type | 3[3:2] | 0=HDMI, 1=DP |
| SAD[n] | Variable | CEA-861 Short Audio Descriptor (3 bytes each) |

> **CRITICAL**: Always read and validate ELD after hot plug detection. If ELD is empty or invalid, the display does not support audio or the connection handshake is incomplete.

---

## Hot Plug Detection

Display audio depends on hot plug events from the display engine. The flow is:

### Hot Plug Flow

```
1. Display connected (HDMI/DP cable or dock)
2. Graphics driver detects hot plug via HPD pin
3. EDID read → ELD extracted → ELD written to iDisp codec
4. Audio driver reads ELD via GET_HDMI_ELD_DATA verb
5. Audio endpoint becomes available in OS
6. Audio stream can be opened on the display output
```

### Validation Sequence

```python
# Display Audio Validation via PythonSV (namednode paths)
import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

die = namednodes.sv.socket0.pcd   # PCD-H; use .pch for PCH-S

# ── Step 1: Verify HDA controller is out of reset ──
gctl = die.ace.hda.bar0.gctl.read()
crst = gctl & 1
print("GCTL: 0x%08X — CRST=%d (expect 1 for active)" % (gctl, crst))
if crst == 0:
    print("  ERROR: Controller in reset — codec discovery not possible")

# ── Step 2: Check iDisp codec discovery via STATESTS ──
statests = die.ace.hda.bar0.statests.read()
print("STATESTS: 0x%04X" % statests)
# iDisp codec typically appears on SDI 2 (bit 2)
if statests & (1 << 2):
    print("  iDisp codec detected on SDI 2")
else:
    print("  WARNING: iDisp codec NOT detected")
    print("  Debug: check display physically connected, GCTL.CRST=1, graphics driver loaded")

# ── Step 3: ELD Readback ──
# ELD is read via HDA CORB/RIRB verb transactions using GET_HDMI_ELD_DATA (verb 0xF6D)
# Verb encoding: codec_addr<<28 | nid<<20 | 0xF6D<<8 | eld_byte_offset
# iDisp codec is typically at codec_addr=2 (SDI bit 2), NID=5 (first pin widget)
# CORB/RIRB physical addresses are programmed by the driver — verb injection
# requires either driver cooperation or manual CORB/RIRB DMA buffer setup.
#
# Practical ELD readback methods:
#   Linux:   cat /proc/asound/card0/eld#*
#   Windows: Use WPP Autologger trace with HDAudio bus driver GUIDs
#            or codec dump utility (hdaudio_codec_dump.exe)
#   PythonSV: Advanced — requires CORB/RIRB setup (see fv-audio/hda for details)
#
# ELD structure:
#   ELD[0] = version (expect 0x02)
#   ELD[2] bits[7:4] = SAD count (>0 means display supports audio)
#   ELD[3] bits[3:2] = connection type (0=HDMI, 1=DP)
```

---

## Multi-Stream Transport (MST) — DisplayPort

DP MST allows multiple displays over a single DP link (daisy-chain or hub). Each display can have its own audio stream.

| Feature | Description |
|---------|-------------|
| Max MST Streams | 3 audio streams (platform-dependent) |
| Stream Assignment | Each DP MST output gets unique stream ID |
| Independent Config | Each stream has its own ELD, sample rate, channels |
| Hot Plug | Each MST display generates independent HPD |

### MST Validation Points

| Test | Pass Criteria |
|------|---------------|
| Single DP display | Audio plays, ELD valid |
| 2 DP displays (MST hub) | Both streams play independently |
| 3 DP displays (MST daisy) | All 3 streams play simultaneously |
| MST hot plug/unplug | Audio endpoint appears/disappears cleanly |
| MST + HDMI mixed | DP MST and HDMI audio work simultaneously |

---

## Validation Points

### Basic Enumeration

| Check | Expected | Debug if Fail |
|-------|----------|---------------|
| iDisp codec in STATESTS | Bit set for iDisp SDI | Check GCTL.CRST=1, display connected |
| Audio endpoint in OS | Display audio device listed | Check ELD valid, driver loaded |
| ELD readback | Non-zero, valid SAD entries | Check display supports audio, EDID valid |

### Playback Validation

| Test | Method | Pass Criteria |
|------|--------|---------------|
| HDMI audio playback | Play 48kHz stereo WAV | Audio on TV/monitor, no glitches |
| DP audio playback | Play 48kHz stereo WAV | Audio on DP display, no glitches |
| Multi-channel (5.1/7.1) | Play 6ch/8ch WAV | All channels routed correctly |
| High sample rate (192kHz) | Play 192kHz stereo | Clean output, verify with analyzer |
| Format switch | Switch 44.1→48→96→192 | Clean transition, correct rate |
| Compressed passthrough | Play AC3/DTS bitstream | Receiver decodes correctly |

### Hot Plug Validation

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Plug HDMI during playback | Insert cable while streaming | Stream routes to display < 2s |
| Unplug during playback | Remove cable while streaming | Stream stops gracefully, no crash |
| Rapid plug/unplug | 10x plug/unplug cycles | No driver crash, endpoint stable |
| Dock with display | Connect USB-C/TB dock with monitor | Display audio available after dock settle |

### Power Management

| Test | Method | Pass Criteria |
|------|--------|---------------|
| D3 with display idle | No audio playing, display connected | ACE can reach D3 |
| S0ix with display connected | Display on but audio idle | S0ix not blocked by iDisp |
| Resume playback after S3/S4 | Sleep → wake → play | Audio plays within 1s of wake |

---

## Known Issues

> Search HSDES for current display audio sightings using terms such as `"iDisp hot plug"`, `"display audio ELD"`, or `"SoundWire Seg0 iDisp"` on tenant `sighting_central.sighting`. Prior placeholder IDs (HSDES-004, BUG-002) have been removed — consult live HSDES for platform-specific known issues and workarounds.

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No display audio endpoint in OS | iDisp codec not detected | Check STATESTS, verify GCTL.CRST=1, confirm display connected |
| Endpoint present but no audio | Stream not configured or ELD invalid | Read ELD, verify SAD entries, check stream-to-converter mapping |
| Audio glitches on HDMI | Bandwidth or clock domain issue | Check display mode (4K@60 leaves less bandwidth), try lower resolution |
| Hot plug not detected | HPD pin or graphics driver issue | Check GT HPD registers, verify cable/connector, test with different display |
| Audio on wrong display | Stream-to-pin routing error | Verify pin widget → converter → stream mapping via verbs |
| No audio after dock connect | Dock settle time or TB tunneling | Wait 5s after dock, check TB driver, verify DP tunnel established |
| Display audio blocking S0ix | Active stream preventing D3 | Stop playback, check `print_s0ix_y_blocking_conditions` |
| No audio after resume (S3/S4) | Codec re-init failure | Check STATESTS after resume, verify CORB/RIRB re-initialized |

---

## Related Sub-Skills

- **fv-audio/hda** — HDA link mechanics (CORB/RIRB, stream descriptors) used by iDisp
- **fv-audio/soundwire** — SoundWire Seg0 alternate path for iDisp
- **fv-audio/power** — D3/S0ix impact on display audio
- **fv-audio/config-checkout** — BIOS and PCI enumeration verification
- **fv-audio/failure-analysis** — NGA failure triage for display audio test failures
