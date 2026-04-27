---
name: fv-audio/hda
description: "HDA link validation — codec discovery, verb programming, CORB/RIRB, stream management, iDisp audio"
version: "1.1.0"
owner: huiyingt
platform: "NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL"
---

# HDA (High Definition Audio) Link Validation

Validate HDA link initialization, codec discovery, verb programming via CORB/RIRB, stream management, and iDisp Audio for HDMI/DP output across Intel Client SoC platforms.

> **Scope:** HDA serial links (SDI pins), HDA-compatible registers in BAR0, external codecs, and iDisp Audio codec.

---

## Multi-Platform HDA Link Configuration

All platforms share a common HDA link architecture with 2 SDI pins (HDALIPC=2). The primary platform-specific difference is iDisp Audio routing, which depends on the die topology.

| Platform | ACE | SDI Count | SDI0 | SDI1 | iDisp Routing | Die Path |
|----------|-----|-----------|------|------|---------------|----------|
| **NVL PCD-H** | 4.x | 2 | External codec | iDisp Audio | SDW Seg 0 alt or HDA SDI | `pcd.ace` |
| **NVL PCH-S** | 4.x | 2 | External codec | iDisp Audio | On-die SDW Seg or HDA SDI | `pch.ace` |
| **PTL** | 3.0 | 2 | External codec | iDisp Audio | *(verify — HAS: ptlsm_ace3.x)* | `soc.ace` |
| **LNL** | 2.x | 2 | External codec | iDisp Audio | *(verify — CoDesign)* | `soc.ace` |
| **MTL SOC-M** | 1.5 | 2 | External codec | iDisp Audio | *(verify — CoDesign)* | `soc.ace` |
| **MTL PCH-S** | 1.5 | 2 | External codec | iDisp Audio | *(verify — CoDesign)* | `pch.ace` |
| **ARL** | 1.5 | 2 | External codec | iDisp Audio | *(verify — CoDesign)* | `pch.ace` |
| **WCL** | 3.0 | 2 | External codec | iDisp Audio | *(same as PTL — verify HAS)* | `soc.ace` |
| **TTL (ACE 4.0)** | 4.0 | 2 | External codec | iDisp Audio | *(ACE 4.x — similar to NVL, verify HAS)* | `pcd.ace` |
| **TTL (ACE 3.0)** | 3.0 | 2 | External codec | iDisp Audio | *(ACE 3.x — similar to PTL, verify HAS)* | `pcd.ace` |
| **RZL** | 4.0 | 2 | External codec | iDisp Audio | *(ACE 4.x — similar to NVL, verify HAS)* | `pcd.ace` |

> **Notes:**
> - All platforms use 1.8V HDA link signaling.
> - Max external codecs per HDA spec: 4 (on SDI0, addresses 0–3).
> - **WCL**: Shares ACE 3.x HDA architecture with PTL — apply PTL debug procedures for HDA issues.
> - **TTL dual-ACE**: Both ACE 4.0 and ACE 3.0 variants use 2 SDI pins. The iDisp routing follows the ACE version: ACE 4.0 → NVL-like routing, ACE 3.0 → PTL-like routing.
> - **RZL**: ACE 4.0 architecture, closest to NVL PCD-H — apply NVL HDA debug procedures directly.
> - iDisp routing details depend on the display-audio path selected at the platform level. See **[fv-audio/display-audio](../display-audio/SKILL.md)** for full iDisp path options per platform.

---

## HDA Architecture on NVL (Reference Platform)

### Link Configuration Detail

| Property | NVL PCD-H | NVL PCH-S |
|----------|-----------|-----------|
| **SDI Pins** | 2 (HDALIPC=2) | 2 (HDALIPC=2) |
| **SDI0** | External codec link | External codec link |
| **SDI1** | iDisp Audio (HDMI/DP) | iDisp Audio (HDMI/DP) |
| **Voltage** | 1.8V only | 1.8V only |
| **Max External Codecs** | 4 (per HDA spec) | 4 (per HDA spec) |
| **iDisp Routing** | Via SoundWire Seg 0 alt | Dedicated on-die link |

### Supported External Codecs (POR)

| Vendor | Common Part Numbers | Interface |
|--------|-------------------|-----------|
| Realtek | ALC256, ALC298, ALC700 series | HDA or SoundWire |
| Cirrus Logic | CS35L41, CS42L43 | HDA or SoundWire |
| Conexant | CX series | HDA |
| Maxim | MAX98373, MAX98390 | HDA or SoundWire |
| Texas Instruments | TAS2781 | HDA or SoundWire |

---

## HDA Register Map (BAR0)

> ⛔ **HAS-First Override**: The register offsets below are **reference summaries** for quick triage.
> When a user asks for register offsets **"according to HAS"**, **"from the HAS"**, or **"per HAS"**,
> you **MUST NOT** return these cached values. Instead, **query Co-Design for authoritative HAS data**.
>
> **Method 1 (preferred)** — Use `browsermcp_browser_navigate` to navigate to Co-Design:
> ```
> browsermcp_browser_navigate → https://chat.co-design.intel.com/chat
> Type: "HDA global register offsets for NVL PCD-H from nvldp_ace4.x_integration_has.html"
> Wait 20s → parse response → present as authoritative HAS answer
> ```
>
> **Method 2 (fallback)** — Use the codesign API script via Bash:
> ```bash
> python .opencode/skill/codesign/codesign_api.py ask-projects "HDA global register offsets for NVL PCD-H" --project nvldp_ace4.x_integration_has
> ```
>
> **You MUST execute one of these methods.** Do NOT return the table below as the answer to a HAS query.
> Only use the table below for triage/debug when the user does NOT specifically request HAS values.

### Global Registers

| Offset | Name | Size | Description |
|--------|------|------|-------------|
| 0x00 | GCAP | 16-bit | Global Capabilities — stream counts, 64-bit support |
| 0x02 | VMIN | 8-bit | Minor Version |
| 0x03 | VMAJ | 8-bit | Major Version |
| 0x04 | OUTPAY | 16-bit | Output Payload Capability |
| 0x06 | INPAY | 16-bit | Input Payload Capability |
| 0x08 | GCTL | 32-bit | Global Control — bit 0 = CRST (Controller Reset) |
| 0x0C | WAKEEN | 16-bit | Wake Enable |
| 0x0E | STATESTS | 16-bit | State Change Status — codec presence per SDI |
| 0x10 | GSTS | 16-bit | Global Status |
| 0x18 | OUTSTRMPAY | 16-bit | Output Stream Payload |
| 0x1A | INSTRMPAY | 16-bit | Input Stream Payload |
| 0x20 | INTCTL | 32-bit | Interrupt Control |
| 0x24 | INTSTS | 32-bit | Interrupt Status |
| 0x30 | WALCLK | 32-bit | Wall Clock Counter |
| 0x38 | SSYNC | 32-bit | Stream Synchronization |

### CORB Registers (Command Output)

| Offset | Name | Size | Description |
|--------|------|------|-------------|
| 0x40 | CORBLBASE | 32-bit | CORB Lower Base Address |
| 0x44 | CORBUBASE | 32-bit | CORB Upper Base Address |
| 0x48 | CORBWP | 16-bit | CORB Write Pointer |
| 0x4A | CORBRP | 16-bit | CORB Read Pointer |
| 0x4C | CORBCTL | 8-bit | CORB Control — bit 1 = DMA Run |
| 0x4D | CORBSTS | 8-bit | CORB Status |
| 0x4E | CORBSIZE | 8-bit | CORB Size |

### RIRB Registers (Response Input)

| Offset | Name | Size | Description |
|--------|------|------|-------------|
| 0x50 | RIRBLBASE | 32-bit | RIRB Lower Base Address |
| 0x54 | RIRBUBASE | 32-bit | RIRB Upper Base Address |
| 0x58 | RIRBWP | 16-bit | RIRB Write Pointer |
| 0x5A | RINTCNT | 16-bit | Response Interrupt Count |
| 0x5C | RIRBCTL | 8-bit | RIRB Control — bit 1 = DMA Run |
| 0x5D | RIRBSTS | 8-bit | RIRB Status |
| 0x5E | RIRBSIZE | 8-bit | RIRB Size |

### Stream Descriptor Registers (per stream, offset base varies)

| Offset | Name | Size | Description |
|--------|------|------|-------------|
| +0x00 | SDnCTL | 24-bit | Stream Descriptor Control |
| +0x03 | SDnSTS | 8-bit | Stream Descriptor Status |
| +0x04 | SDnLPIB | 32-bit | Link Position In Buffer |
| +0x08 | SDnCBL | 32-bit | Cyclic Buffer Length |
| +0x0C | SDnLVI | 16-bit | Last Valid Index |
| +0x10 | SDnFIFOS | 16-bit | FIFO Size |
| +0x12 | SDnFMT | 16-bit | Stream Format |
| +0x18 | SDnBDPL | 32-bit | Buffer Descriptor List Pointer (Low) |
| +0x1C | SDnBDPU | 32-bit | Buffer Descriptor List Pointer (Upper) |

---

## HDA Initialization Sequence

### Step 1: Controller Reset

```python
# Read GCTL — check CRST bit
gctl = ace.bar0.gctl.read()
crst = gctl & 0x1
print("GCTL: 0x%08X, CRST=%d" % (gctl, crst))

if crst == 0:
    # Controller is in reset — bring out of reset
    print("Controller in reset — setting CRST=1")
    ace.bar0.gctl.write(gctl | 0x1)
    
    # Wait for CRST to stick at 1
    import time
    for _ in range(100):
        gctl = ace.bar0.gctl.read()
        if gctl & 0x1:
            break
        time.sleep(0.001)
    
    if not (gctl & 0x1):
        print("ERROR: CRST did not set — controller stuck in reset")
    else:
        print("Controller out of reset (CRST=1)")
```

### Step 2: Codec Detection

```python
# Wait for codec status change after reset
import time
time.sleep(0.5)  # Codecs need time to signal presence

statests = ace.bar0.statests.read()
print("STATESTS: 0x%04X" % statests)

codecs_found = []
for sdi in range(2):  # HDALIPC=2 on NVL
    if (statests >> sdi) & 1:
        codecs_found.append(sdi)
        print("  SDI%d: Codec PRESENT" % sdi)
    else:
        print("  SDI%d: No codec" % sdi)

if not codecs_found:
    print("WARNING: No codecs detected — check link, codec power, BIOS config")
```

### Step 3: CORB/RIRB Setup

```python
# The CORB and RIRB are ring buffers for sending verbs and receiving responses.
# They must be allocated in DMA-accessible memory and started.

# Check CORB/RIRB sizes supported
corbsize = ace.bar0.corbsize.read()
rirbsize = ace.bar0.rirbsize.read()
print("CORBSIZE cap: 0x%02X, RIRBSIZE cap: 0x%02X" % (corbsize, rirbsize))

# Verify CORB and RIRB DMA is running
corbctl = ace.bar0.corbctl.read()
rirbctl = ace.bar0.rirbctl.read()
print("CORBCTL: 0x%02X (DMA Run=%d)" % (corbctl, (corbctl >> 1) & 1))
print("RIRBCTL: 0x%02X (DMA Run=%d)" % (rirbctl, (rirbctl >> 1) & 1))
```

---

## Verb Programming

### HDA Verb Format

HDA verbs are 28-bit commands sent via CORB:

```
[31:28] Codec Address (0-14)
[27:20] Node ID (0-127 for direct, 0 for root)
[19:8]  Verb ID
[7:0]   Payload
```

Or for short verbs (Get/Set):
```
[31:28] Codec Address
[27:20] Node ID
[19:16] Verb ID (short)
[15:0]  Payload (16-bit)
```

### Common Verb IDs

| Verb | ID | Direction | Description |
|------|-----|-----------|-------------|
| Get Parameter | 0xF00 | Get | Read codec/node parameters |
| Get Connection Select | 0xF01 | Get | Current input selection |
| Set Connection Select | 0x701 | Set | Select input connection |
| Get Pin Widget Control | 0xF07 | Get | Pin output/input enable |
| Set Pin Widget Control | 0x707 | Set | Enable pin as output/input |
| Get Amp Gain/Mute | 0xB | Get | Amplifier gain and mute status |
| Set Amp Gain/Mute | 0x3 | Set | Set amplifier gain and mute |
| Get Pin Sense | 0xF09 | Get | Jack detection status |
| Get Config Default | 0xF1C | Get | Pin configuration defaults |
| Set Power State | 0x705 | Set | Node power state |
| Get Power State | 0xF05 | Get | Node power state |

### Codec Parameter IDs (used with Get Parameter verb 0xF00)

| Parameter ID | Description |
|-------------|-------------|
| 0x00 | Vendor ID |
| 0x02 | Revision ID |
| 0x04 | Subordinate Node Count |
| 0x05 | Function Group Type |
| 0x09 | Widget Capabilities |
| 0x0A | Supported PCM Sizes/Rates |
| 0x0B | Supported Stream Formats |
| 0x0C | Pin Capabilities |
| 0x0D | Amplifier Capabilities (Input) |
| 0x12 | Amplifier Capabilities (Output) |
| 0x0E | Connection List Length |
| 0x0F | Supported Power States |
| 0x10 | Processing Capabilities |
| 0x11 | GPIO Count |

### Example: Read Codec Vendor ID

```python
# Send verb: Codec 0, Root Node 0, Get Parameter (0xF00), Param=VendorID (0x00)
# Verb word = (0 << 28) | (0x00 << 20) | (0xF0000)
verb = 0x000F0000  # Codec 0, Node 0, Get Parameter, VendorID

# To send via CORB:
# 1. Write verb to CORB entry at (CORBWP+1) % CORBSIZE
# 2. Update CORBWP
# 3. Wait for RIRB entry
# This requires DMA memory setup — typically done by driver

# For PythonSV direct access, codec verbs may be available via
# immediate command interface if supported
```

---

## iDisp Audio (HDMI/DP)

### Overview

iDisp Audio provides audio output over HDMI and DisplayPort connections. It uses an on-die codec connected to the HDA controller.

### iDisp Routing by Die Topology

The iDisp Audio routing depends on the die type, not the platform. This pattern applies across all platforms:

| Die Topology | iDisp Routing | Platforms Using This Pattern |
|-------------|--------------|------------------------------|
| **PCD-H / PCD-S** | SoundWire Segment 0 alt mode (shares SDW Seg 0) | NVL PCD-H, TTL (ACE 4.0), RZL |
| **PCH-S** | Dedicated on-die HDA link (separate from SoundWire) | NVL PCH-S |
| **SOC (monolithic)** | *(varies — verify against HAS)* | PTL, LNL, WCL, MTL-M, ARL |
| **PCH (chiplet)** | *(varies — verify against HAS)* | MTL-S, ARL-S |

> For full iDisp path details (HDA vs SoundWire Seg 0 Alt), see **[fv-audio/display-audio](../display-audio/SKILL.md)**.

### Verification

```python
# Check if iDisp codec is detected on SDI1
statests = ace.bar0.statests.read()
idisp_present = (statests >> 1) & 1  # SDI1 = iDisp typically
print("iDisp codec: %s" % ("Present" if idisp_present else "Not detected"))

if idisp_present:
    # Query iDisp codec Vendor ID
    # iDisp codec address is typically 2 (may vary)
    # Send Get Parameter (VendorID) to iDisp root node
    print("iDisp codec detected — verify via verb programming")
```

---

## Stream Configuration

### Stream Setup Procedure

1. **Reset stream** — Set SDnCTL.SRST=1, wait for it to read back 1
2. **Clear reset** — Set SDnCTL.SRST=0, wait for it to read back 0
3. **Set stream format** — Write SDnFMT (sample rate, bits, channels)
4. **Set buffer** — Configure SDnBDPL/SDnBDPU, SDnCBL, SDnLVI
5. **Set stream ID** — Write SDnCTL.STRM field
6. **Start stream** — Set SDnCTL.RUN=1

### Stream Format Register (SDnFMT)

| Bits | Field | Description |
|------|-------|-------------|
| [15] | TYPE | 0=PCM, 1=Non-PCM |
| [14] | BASE | 0=48kHz, 1=44.1kHz |
| [13:11] | MULT | Sample rate multiplier |
| [10:8] | DIV | Sample rate divisor |
| [7:4] | BITS | Bits per sample (001=16, 010=20, 011=24, 100=32) |
| [3:0] | CHAN | Number of channels minus 1 |

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| STATESTS=0 | No codec on link | Check GCTL.CRST, codec power, physical connection |
| CORB timeout | Codec not responding | Verify CORB DMA running, check codec address |
| RIRB overflow | Host not reading responses fast enough | Check RINTCNT, RIRBCTL |
| Stream underrun | DMA not keeping up | Check buffer size (SDnCBL), format (SDnFMT) |
| iDisp not working | Routing mismatch | PCD-H: check SDW Seg 0; PCH-S: check dedicated link |
| Wrong sample rate | Format register wrong | Verify SDnFMT BASE/MULT/DIV fields |
| No jack detect | Pin sense not configured | Send Get Pin Sense verb to output pin |

---

## See Also

- **[fv-audio/display-audio](../display-audio/SKILL.md)** — iDisp HDA link for HDMI/DP audio, ELD readback
- **[fv-audio/soundwire](../soundwire/SKILL.md)** — SoundWire Seg 0 alt mode sharing with HDA on PCD-H
- **[fv-audio/dsp](../dsp/SKILL.md)** — DSP pipelines consuming HDA streams
- **[fv-audio/jack-detect](../jack-detect/SKILL.md)** — HDA pin sense verbs for jack detection
- **[fv-audio/aioc](../aioc/SKILL.md)** — AIOC codec connection via HDA or SoundWire
- **[fv-audio/platform](../platform/SKILL.md)** — Per-platform HDA Device IDs, BDF assignments
- **[hda/windows.md](windows.md)** — Windows HDA driver stack, verb programming, codec enumeration
