---
name: fv-audio/soundwire
description: "SoundWire link validation — bus enumeration, stream configuration, multi-drop, data lanes"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# SoundWire Link Validation

Validate SoundWire link initialization, bus enumeration, stream configuration, multi-drop codec setup, and data lane management across all Intel Client SoC platforms.

> **Scope:** SoundWire bus segments, SHIM/ALH registers, codec enumeration, stream setup, data ports, data lanes.

> **Standard:** SoundWire is defined by the **MIPI SoundWire specification** (published by the MIPI Alliance). All bus protocol, frame structure, device class definitions, and transport mechanisms follow the MIPI SoundWire standard. The specification defines the physical layer, data link layer, and application layer for multi-drop audio buses.

---

## Multi-Platform SoundWire Configuration

| Platform | ACE | Segments | SoundWire Ver | Multi-Lane (Seg 2/3) | Die Path | Notes |
|----------|-----|----------|---------------|---------------------|----------|-------|
| **NVL PCD-H** | 4.x | **5** | v1.2 | Up to 4 lanes | `socket0.pcd.ace` | Seg 4: external; Seg 0 alt = iDisp |
| **NVL PCH-S** | 4.x | **5** | v1.2 | Up to 4 lanes | `socket0.pch.ace` | Seg 4: on-die iDisp/CNVi |
| **PTL** | 3.0 | **5** | v1.2 | Up to 4 lanes | `socket0.soc.ace` | Same 5-seg architecture as NVL |
| **WCL** | 3.0 | **5** | v1.2 | Up to 4 lanes | `socket0.soc.ace` | Shares PTL SoundWire config |
| **TTL** | 3.0/4.0 | **5** | v1.2 | Up to 4 lanes | `socket0.pcd.ace` | Both ACE variants have 5 segments |
| **RZL** | 4.0 | **5** | v1.2 | Up to 4 lanes | `socket0.pcd.ace` | Same 5-seg as NVL PCD-H |
| **LNL** | 2.x | **4** | v1.2 | Up to 4 lanes | `socket0.soc.ace` | ⚠️ Only 4 segments (no Seg 4) |
| **MTL** | 1.5 | **4** | v1.2 | Up to 4 lanes | `socket0.soc.ace` / `pch.ace` | ⚠️ Only 4 segments |
| **ARL** | 1.5 | **4** | v1.2 | Up to 4 lanes | `socket0.pch.ace` | ⚠️ Only 4 segments |

> **Key difference: 4 vs 5 segments.** ACE 3.0+ platforms (PTL, WCL, TTL, NVL, RZL) have **5 SoundWire segments** (Seg 0–4). ACE 2.x and earlier (LNL, MTL, ARL) have **4 segments** (Seg 0–3). When writing validation scripts, always check the platform's segment count before iterating: `range(5)` for 5-seg platforms, `range(4)` for 4-seg platforms.

> **TTL dual-ACE note:** Both ACE 3.0 and ACE 4.0 TTL variants expose 5 SoundWire segments. The segment count is not affected by the ACE version fuse — only DSP core configuration differs.

---

## SoundWire Architecture on NVL

### Bus Segment Configuration

| Segment | NVL PCD-H | NVL PCH-S | Max Data Lanes | Notes |
|---------|-----------|-----------|----------------|-------|
| **Seg 0** | External codec | External codec | Standard | Alt: iDisp-A on PCD-H |
| **Seg 1** | External codec | External codec | Standard | -- |
| **Seg 2** | External codec | External codec | Up to 4 | Multi-lane support |
| **Seg 3** | External codec | External codec | Up to 4 | Multi-lane support |
| **Seg 4** | External codec | On-die iDisp-A/CNVi | Up to 5 | PCD-H: external; PCH-S: on-die alt |

- **Total Segments:** 5 (SNDWSC=5)
- **NVL is master** on all 5 segments
- **PCM Streams:** 16 bidirectional per link
- **Multi-drop:** Multiple codecs can share a single bus segment

### PCD-H vs PCH-S SoundWire Differences

| Feature | NVL PCD-H | NVL PCH-S |
|---------|-----------|-----------|
| **External segments** | 5 | 4 |
| **iDisp-A routing** | Seg 0 alternate | Seg 4 on-die |
| **Seg 4 function** | External codec | On-die iDisp-A/CNVi alternate |
| **Multi-lane (Seg 2/3)** | Up to 4 lanes | Up to 4 lanes |

---

## SoundWire Register Architecture

SoundWire link control is managed through two register regions:

### SHIM (SoundWire Host Interface Module) Registers

The SHIM provides link-level control for each SoundWire bus segment.

| Register | Description |
|----------|-------------|
| **LCTL** | Link Control — enable, power control, clock stop |
| **LCAP** | Link Capabilities — supported features |
| **LSDIID** | Link SDI ID — device identification |
| **SHIM_CFG** | SHIM Configuration — link mode, clock source |
| **SHIM_WAKEEN** | SHIM Wake Enable — wake sources |
| **SHIM_WAKESTS** | SHIM Wake Status — wake event status |
| **SHIM_IOCTL** | SHIM I/O Control — pin control |
| **SHIM_CTMCTL** | SHIM Counter/Timer Control |

### ALH (Audio Link Hub) Registers

The ALH manages stream-to-link mapping and DMA channels.

| Register | Description |
|----------|-------------|
| **ALH_STRMZCFG** | Stream Z Configuration — stream format, channel config |
| **ALH_STRMZCFG2** | Stream Z Configuration 2 — extended format |

---

## SoundWire Link Initialization

### Step 1: Link Enable

```python
# SoundWire Link Initialization and Verification via PythonSV
# NVL ACE 4.x — 5 SoundWire segments (SNDWSC=5)
# HAS verification required: namednode paths may vary by ACE version

import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

die = namednodes.sv.socket0.pcd   # PCD-H; use .pch for PCH-S

print("=== SoundWire Link Status (all 5 segments) ===\n")

# Check each SoundWire segment's link status via SHIM LCTL
for seg in range(5):
    print("Segment %d:" % seg)
    try:
        # SHIM LCTL (Link Control) — per-segment
        # Namednode pattern: die.ace.sndw.shim.lctlN  where N = segment number
        lctl = eval("die.ace.sndw.shim.lctl%d.read()" % seg)
        spa  = (lctl >> 0) & 1   # SPA — SyncPoint Active (link started by SW)
        cpa  = (lctl >> 8) & 1   # CPA — Current Power Active (HW confirms power on)
        print("  SHIM LCTL%d: 0x%08X — SPA=%d, CPA=%d" % (seg, lctl, spa, cpa))
        if spa and cpa:
            print("  --> Link ACTIVE")
        elif spa and not cpa:
            print("  --> Link powering up (SPA set, CPA not yet — wait or check PMC)")
        else:
            print("  --> Link INACTIVE (BIOS may have disabled this segment)")
    except Exception as e:
        print("  LCTL%d read failed: %s" % (seg, e))
        print("  Try browsing: dir(die.ace.sndw.shim)")

print("\n=== SoundWire Clock Verification ===\n")

# Verify ACE audio clock is running (prerequisite for SoundWire)
try:
    clkctl = die.ace.hda.bar0.clkctl.read()
    print("CLKCTL: 0x%08X" % clkctl)
    # CLKCTL contains clock source selection and status bits
    # Bit[0]: Audio PLL enable
    # Bit[4]: WoV CRO select (should be 0 for normal operation)
    pll_en = clkctl & 1
    print("  Audio PLL enable: %d (expect 1 for active SoundWire)" % pll_en)
    if not pll_en:
        print("  WARNING: Audio PLL not enabled — SoundWire links cannot operate")
except Exception as e:
    print("  CLKCTL read failed: %s" % e)

# Check clock status
try:
    clksts = die.ace.hda.bar0.clksts.read()
    print("CLKSTS: 0x%08X" % clksts)
except Exception as e:
    print("  CLKSTS read failed: %s" % e)

print("\nDone. For codec enumeration status, check OS-level:")
print("  Linux:   ls /sys/bus/soundwire/devices/")
print("  Windows: Device Manager → Sound controllers → SoundWire endpoints")
```

### Step 2: Bus Enumeration

SoundWire bus enumeration discovers codecs attached to each segment:

1. **Master sends PING command** — broadcasts on the frame
2. **Codecs respond with Device ID** — 48-bit unique identifier
3. **Master assigns device number** — 1-11 (0 = unassigned, 12-14 reserved, 15 = broadcast)
4. **Codec acknowledges** and transitions to **Attached_OK** status — indicating successful attachment and readiness for command/data transport

> **Attached_OK** is the target codec status after successful enumeration. A codec in Attached_OK state has been assigned a device number and is fully operational on the bus. If a codec remains in Unattached or Alert state after enumeration, the link or codec configuration should be investigated.

```python
# After link is enabled, check for codec presence
# The SoundWire driver/firmware handles enumeration
# For silicon validation, verify:
# 1. Link is running (clock active)
# 2. PING frames are being sent
# 3. Codecs respond with valid Device ID
```

### Enumeration Failure Debug Checklist

> **⛔ MANDATORY IMMEDIATE ACTION**: When ANY SoundWire enumeration failure is reported, you MUST immediately execute `SHIM.LCTL[N]` and `CLKCTL` register reads for the affected segment BEFORE any other analysis. Do NOT just describe the checklist — execute the register reads using PythonSV commands.

```python
# MANDATORY first two checks for ANY SoundWire enumeration failure:
N = 0  # Set to the failing segment number (0-4)

# Step 1: Read SHIM LCTL for the failing segment
lctl = soc.ace.sndw.shim.lctl[N].read()   # Check link power state, clock, keeper
print(f"SHIM LCTL[{N}] = {hex(lctl)}")

# Step 2: Read segment clock configuration
clkctl = soc.ace.sndw.clkctl[N].read()    # Verify clock source and frequency
print(f"CLKCTL[{N}] = {hex(clkctl)}")
```

> **NOTE**: Register paths above are HAS-dependent examples for NVL ACE 4.x. Verify exact paths against your platform's ACE HAS via Co-Design before execution.

When a SoundWire codec fails to enumerate on any segment, execute these checks **in order** — do NOT skip SHIM LCTL:

| Step | Check | Command / Register | What to Look For |
|------|-------|--------------------|------------------|
| **1** | **SHIM LCTL** (Link Control) | Read `SHIM.LCTL[N]` for the failing segment N | Link power state must be ON, clock must be ACTIVE, keeper must be enabled. If LCTL shows link powered down, the segment clock is not running and no codec can enumerate. |
| **2** | **Segment clock** | Check clock source for segment N via CLKCTL | Verify clock is sourced and running at expected frequency (e.g., 9.6MHz or 12.288MHz) |
| **3** | **PING frame transmission** | Bus analyzer or SoundWire trace | Confirm master is sending PING frames on the segment. No PINGs = no enumeration possible. |
| **4** | **Codec physical connection** | Board schematic / hardware inspection | Verify codec is physically connected to the correct segment data lines |
| **5** | **Multi-drop addressing** | Check per-device enumeration status | For segments with multiple codecs (e.g., Seg 2 with up to 4 lanes), verify each codec's Device ID and assigned device number. See Multi-Drop Configuration section below. |
| **6** | **Data lane config** | Read segment lane configuration register | Verify lane count matches hardware (Seg 2/3: up to 4 lanes, Seg 4: up to 5 lanes) |

> **MANDATORY**: Steps 1-2 (SHIM LCTL and segment clock) must ALWAYS be checked first for any enumeration failure. These are the most common root causes and gate all subsequent checks.

### Step 3: Stream Setup

SoundWire streams carry audio data between host and codecs:

```python
# Configure stream via ALH registers
# Stream configuration includes:
# - Sample rate (8kHz to 192kHz)
# - Bit depth (16, 20, 24, 32)
# - Channel count
# - Data lane assignment
# - Stream number (0-15 per link)

# Example: Configure 48kHz/16-bit/stereo stream on Segment 0
# alh_strmcfg = <read ALH_STRMZCFG for stream>
# Set format fields
# Write back
```

---

## Multi-Drop Configuration

SoundWire supports multiple codecs on a single bus segment (multi-drop topology).

### Addressing

| Device Number | Usage |
|--------------|-------|
| 0 | Unassigned (default after reset) |
| 1-11 | Assigned device numbers |
| 12-14 | Reserved |
| 15 | Broadcast (all devices) |

### Multi-Drop Considerations

- Each codec on a shared bus must have a unique 48-bit Device ID
- Master assigns unique device numbers during enumeration
- Multiple codecs share the bus bandwidth — consider frame layout
- Data lanes can be assigned per-codec for bandwidth isolation
- Clock stop affects all codecs on the bus

---

## Data Lane Management

Segments 2, 3, and 4 support multi-lane operation for higher bandwidth.

### Lane Configuration

| Segment | Max Lanes | Typical Use |
|---------|-----------|-------------|
| Seg 0 | Standard (1) | Speaker codec / iDisp alt |
| Seg 1 | Standard (1) | Speaker codec |
| Seg 2 | Up to 4 | Multi-lane amplifier array |
| Seg 3 | Up to 4 | Multi-lane amplifier array |
| Seg 4 | Up to 5 | High-bandwidth / on-die (PCH-S) |

### Lane Enable

```python
# Multi-lane configuration via SHIM registers
# Each additional lane provides more bandwidth for audio data
# Lane assignment is per-stream, configured via SHIM_CFG and ALH_STRMZCFG

# Example: Verify lane configuration on Segment 2
# HAS verification required: exact register paths vary by ACE version
try:
    # SHIM CFG for segment 2 — contains lane enable and mode bits
    shim_cfg2 = die.ace.sndw.shim.cfg2.read()
    print("SHIM CFG2 (Seg 2 lane config): 0x%08X" % shim_cfg2)
    # Decode lane enable bits (HAS-dependent bit positions)
    # Typical: bits[3:0] = lane enable mask (1 bit per lane)
except Exception as e:
    print("  SHIM CFG2 read failed — check namednode path: %s" % e)
    print("  Browse available: dir(die.ace.sndw.shim)")
```

---

## SoundWire Codec Validation

### Data Ports

In the MIPI SoundWire architecture, **data ports** are the codec-side endpoints for audio streams. Each codec exposes one or more data ports, each capable of carrying audio data in a specific direction (source or sink).

| Port Number | Typical Function | Direction |
|-------------|-----------------|-----------|
| **Port 0** | BRA (Bulk Register Access) | Bidirectional |
| **Port 1-14** | Audio data ports | Source or Sink |

- Each data port maps to one stream at a time
- Data port capabilities (sample rates, bit depths, channel count) are described in the codec's SDCA (SoundWire Device Class for Audio) properties
- Multi-lane segments can assign different data lanes to different data ports for bandwidth isolation
- Data port flow control is managed by the SoundWire master (NVL ACE controller)

### Supported Codecs

| Vendor | Parts | Bus Support |
|--------|-------|-------------|
| Realtek | ALC5682, ALC711, ALC722 | Single/Multi-drop |
| Cirrus Logic | CS42L43, CS35L56 | Single/Multi-drop |
| Maxim | MAX98373 | Single |
| Texas Instruments | TAS2781 | Single/Multi-drop |
| Knowles | DMIC devices | Single |

### Codec Discovery Verification

```python
# After SoundWire enumeration, verify codec presence and device numbers
# Enumeration is handled by driver/FW — silicon validation verifies the result

import namednodes
from namednodes import *

die = namednodes.sv.socket0.pcd   # PCD-H; use .pch for PCH-S

print("=== SoundWire Codec Discovery Verification ===\n")

# Method 1: Check link status — a segment with active codecs will show CPA=1
for seg in range(5):
    try:
        lctl = eval("die.ace.sndw.shim.lctl%d.read()" % seg)
        cpa = (lctl >> 8) & 1
        if cpa:
            print("Segment %d: ACTIVE (CPA=1) — codec(s) likely enumerated" % seg)
        else:
            print("Segment %d: INACTIVE (CPA=0)" % seg)
    except Exception:
        print("Segment %d: LCTL read failed" % seg)

# Method 2: OS-level verification (recommended for codec identification)
print("\nOS-level codec enumeration check:")
print("  Linux:   ls /sys/bus/soundwire/devices/")
print("           cat /sys/bus/soundwire/devices/*/dev-properties")
print("           # Shows Device ID (48-bit), device number, status")
print("  Windows: Device Manager → Sound, video and game controllers")
print("           # Look for SoundWire codec entries (IntcPchSnd devices)")
print("           # Or check WPP trace for codec enumeration log")
```

---

## Clock Stop Mode

SoundWire supports clock stop for power saving:

| Mode | Description | Wake Source |
|------|-------------|-------------|
| **Clock Stop Mode 0** | Simple clock stop — all codecs support | Master-initiated resume |
| **Clock Stop Mode 1** | Advanced — codec keeps context | In-band wake (codec-initiated) |

### Clock Stop Procedure

1. Master sends Clock Stop Prepare command
2. Codecs acknowledge readiness
3. Master stops the bus clock
4. On resume: Master restarts clock, codecs re-sync

```python
# Verify clock stop capability and current state
# SHIM LCTL contains clock stop status bits

try:
    # Check Segment 0 as example (change seg number as needed)
    lctl0 = die.ace.sndw.shim.lctl0.read()
    # Clock stop bits in LCTL (HAS-dependent positions):
    # CLSS (Clock Stop Status) — indicates if clock is currently stopped
    # CLSE (Clock Stop Enable) — enables clock stop capability
    print("SHIM LCTL0: 0x%08X" % lctl0)
    print("  Check CLSS/CLSE bits per ACE HAS for clock stop state")
except Exception as e:
    print("  LCTL read failed: %s" % e)

# OS-level clock stop verification:
#   Linux:   Check dmesg for "soundwire.*clock_stop" messages
#   Windows: WPP trace with IntcPchSnd provider for clock stop events
```

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No codec on segment | Link not started, codec power off | Check SHIM LCTL, codec power supply |
| Enumeration failure | Bus clock not running, PING not sent | Verify link enable, clock config |
| Stream setup failure | Format mismatch, lane not enabled | Check ALH stream config, lane assignment |
| Audio glitches | Bandwidth contention in multi-drop | Review frame layout, consider lane separation |
| Clock stop failure | Codec not supporting requested mode | Check codec clock stop capabilities |
| Seg 0 conflict (PCD-H) | iDisp-A alt mode active | Verify segment mode (external vs iDisp alt) |
| Seg 4 not working (PCH-S) | On-die routing, not external | Confirm PCH-S Seg 4 is iDisp/CNVi, not external codec |
| Multi-drop collision | Multiple codecs with same device number | Re-enumerate, check Device IDs |

---

## See Also

- **[fv-audio/hda](../hda/SKILL.md)** — HDA link sharing with SoundWire Seg 0 on PCD-H
- **[fv-audio/display-audio](../display-audio/SKILL.md)** — iDisp audio via SoundWire Seg 0 alt path
- **[fv-audio/aioc](../aioc/SKILL.md)** — AIOC codec topology over SoundWire segments
- **[fv-audio/power](../power/SKILL.md)** — SoundWire clock-stop power management, D3 transitions
- **[fv-audio/dsp](../dsp/SKILL.md)** — DSP pipeline endpoints on SoundWire links
- **[fv-audio/platform](../platform/SKILL.md)** — Per-platform segment counts, lane assignments, codec maps
- **[soundwire/windows.md](windows.md)** — Windows SoundWire driver stack, bus enumeration, codec matching
