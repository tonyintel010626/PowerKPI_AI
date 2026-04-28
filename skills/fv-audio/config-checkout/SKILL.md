---
name: fv-audio/config-checkout
description: "Verify Audio/ACE device enumeration, BAR allocation, BIOS configuration, reset architecture, and BIOS register programming"
source: "NVLDP ACE4.x Integration HAS Rev 1.2 — §8 Reset Transactions, §23 BIOS Programming"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# Audio Configuration Checkout

Comprehensive configuration verification for the ACE (Audio & Communications Engine): PCI enumeration, BAR allocation, BIOS settings, and ACPI verification across all Intel Client SoC platforms.

> **Scope:** ACE PCI function (0:31:3) covering HDA, SoundWire, SSP/I2S, DSP — all under a single PCI device.

---

## Part 1 — PCI Enumeration & BAR Assignment

### NVL PCD-H Audio Device Map (Single PCI Function)

*Source: `nvldp_ace4.x_integration_has.html`*

| Property | Value |
|----------|-------|
| **BDF** | Bus 0, Device 31, Function 3 (PCI 0:31:3) |
| **Vendor ID** | 0x8086 (Intel) |
| **Primary Device ID** | 0xD328 |
| **Device ID Range** | 0xD328 - 0xD32F |
| **Class Code** | Multimedia Audio Controller |
| **BAR0** | 512 KB — HDA-compatible registers |
| **BAR1** | 4 KB — ACPI/PCI config extension |
| **BAR2** | 2 MB — DSP domain (requires GPROCEN) |

### NVL PCH-S Audio Device Map (Single PCI Function)

*Source: `nvps_ace4.x_integration_has.html`*

| Property | Value |
|----------|-------|
| **BDF** | Bus 0, Device 31, Function 3 |
| **Vendor ID** | 0x8086 (Intel) |
| **Primary Device ID** | 0xD228 |
| **Device ID Range** | 0xD228 - 0xD22F |
| **Class Code** | Multimedia Audio Controller |
| **BAR0** | 512 KB — HDA-compatible registers |
| **BAR1** | 4 KB — ACPI/PCI config extension |
| **BAR2** | 2 MB — DSP domain (requires GPROCEN) |

### Multi-Platform Audio Device ID Reference

All platforms enumerate Audio/ACE at **BDF 0:31:3**, VID = **0x8086**. The DID varies by platform and die variant:

| Platform | Die | DID | DID Range | ACE Version | Die Path |
|----------|-----|-----|-----------|-------------|----------|
| **NVL PCD-H** | PCD | **0xD328** | 0xD328–0xD32F | ACE 4.x | `socket0.pcd.ace` |
| **NVL PCH-S** | PCH | **0xD228** | 0xD228–0xD22F | ACE 4.x | `socket0.pch.ace` |
| **MTL SOC-M** | SOC | **0x7E28** | 0x7E28–0x7E2F | ACE 1.5 | `socket0.soc.ace` |
| **MTL PCH-S** | PCH | **0xAE28** | 0xAE28–0xAE2F | ACE 1.5 | `socket0.pch.ace` |
| **PTL** | PCD | ⚠️ *UNVERIFIED* | — | ACE 3.0 | `socket0.soc.ace` |
| **LNL** | SOC | ⚠️ *UNVERIFIED* | — | ACE 2.x | `socket0.soc.ace` |
| **ARL-U/S** | PCH | ⚠️ *UNVERIFIED* | — | ACE 1.5 | `socket0.pch.ace` |
| **WCL** | PCD | ⚠️ *shares PTL DIDs* | — | ACE 3.0 | `socket0.soc.ace` |
| **TTL PCD-H/S** | PCD | **0xD228** ⚠️ | 0xD228–0xD22F | ACE 3.0 / 4.0 | `socket0.pcd.ace` |
| **RZL PCD-H/S/M/W** | PCD | **0xD328** ⚠️ | 0xD328–0xD32F | ACE 4.0 | `socket0.pcd.ace` |

> ⚠️ **TTL / RZL DID CAVEAT**: These DIDs overlap with NVL PCH-S (0xD228) and NVL PCD-H (0xD328) respectively. This may indicate shared silicon or a Co-Design conflation error. **Always verify against the HAS document for your specific stepping/SKU.**

> ⚠️ **TTL Dual ACE**: TTL is unique in offering both ACE 3.0 (LX7-based) and ACE 4.0 (HiFi5-based) variants, fuse-selected at manufacturing. Confirm your SKU's ACE version before interpreting DID or core counts.

> **DID = 0xFFFF** at BDF 0:31:3 means Audio/ACE is disabled in BIOS. Check the `AudioController` BIOS knob and the `FNCFG.ACED` fuse/register.

### PCI Configuration Space Reference

| Offset | Field | Description |
|--------|-------|-------------|
| 0x00 | Vendor ID | Should be 0x8086 (Intel) |
| 0x02 | Device ID | PCD-H: 0xD328, PCH-S: 0xD228 |
| 0x04 | Command Register | Bit 1 = Memory Space Enable, Bit 2 = Bus Master Enable |
| 0x08 | Revision ID | Silicon stepping |
| 0x09 | Class Code | Multimedia Audio Controller |
| 0x10 | BAR0 | Memory-mapped MMIO base address (512 KB, HDA compat) |
| 0x14 | BAR1 | ACPI/PCI config extension (4 KB) |
| 0x18 | BAR2 | DSP domain (2 MB, requires GPROCEN) |
| 0x84 | PMCSR | Power Management Control/Status — [1:0] = PowerState |

### PythonSV Enumeration Check — NVL PCD-H

```python
import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

# ACE is at Bus 0, Device 31, Function 3
ace = namednodes.sv.socket0.pcd.ace

print("=== NVL PCD-H Audio/ACE Enumeration Check ===\n")

# PCI Config
vid = ace.cfg.vendor_id.read()
did = ace.cfg.device_id.read()
cmd = ace.cfg.command.read()
bar0 = ace.cfg.bar0.read()
bar1 = ace.cfg.bar1.read()
bar2 = ace.cfg.bar2.read()
pmcsr = ace.cfg.pmcsr.read()

print("Vendor ID:  0x%04X %s" % (vid, "OK" if vid == 0x8086 else "FAIL - expected 0x8086"))
print("Device ID:  0x%04X %s" % (did, "OK" if did == 0xD328 else "UNEXPECTED - expected 0xD328"))
print("Command:    0x%04X (MemEn=%d, BusMaster=%d)" % (cmd, (cmd >> 1) & 1, (cmd >> 2) & 1))
print("BAR0:       0x%08X %s" % (bar0, "OK" if bar0 != 0 else "FAIL - BAR not assigned"))
print("BAR1:       0x%08X %s" % (bar1, "OK" if bar1 != 0 else "FAIL - BAR not assigned"))
print("BAR2:       0x%08X %s" % (bar2, "OK" if bar2 != 0 else "WARN - DSP BAR not assigned (may need GPROCEN)"))
print("PMCSR:      0x%04X (PowerState=%d)" % (pmcsr, pmcsr & 0x3))

power_states = {0: "D0", 1: "D1", 2: "D2", 3: "D3hot"}
ps = pmcsr & 0x3
print("Power State: %s" % power_states.get(ps, "Unknown"))

if vid == 0xFFFF:
    print("\nERROR: Device not enumerated! Check:")
    print("  1. BIOS audio enable setting")
    print("  2. Device may be in D3 — check PMCSR")
    print("  3. Device may be fuse-disabled")
```

### PythonSV Enumeration Check — NVL PCH-S

```python
# PCH-S uses socket0.pch instead of socket0.pcd
ace = namednodes.sv.socket0.pch.ace

print("=== NVL PCH-S Audio/ACE Enumeration Check ===\n")

vid = ace.cfg.vendor_id.read()
did = ace.cfg.device_id.read()
print("Vendor ID:  0x%04X %s" % (vid, "OK" if vid == 0x8086 else "FAIL"))
print("Device ID:  0x%04X %s" % (did, "OK" if did == 0xD228 else "UNEXPECTED - expected 0xD228"))
# ... same checks as PCD-H but with PCH-S expected values
```

---

## Part 2 — Subsystem Inventory Verification

After confirming the ACE PCI function is enumerated, verify each subsystem is configured correctly.

### HDA Link Verification

```python
# Read Global Capabilities (GCAP) — BAR0 offset 0x00
gcap = ace.bar0.gcap.read()
print("GCAP: 0x%04X" % gcap)

# Decode GCAP fields (HDA Rev 1.0a)
num_oss = (gcap >> 12) & 0xF    # Number of Output Streams
num_iss = (gcap >> 8) & 0xF     # Number of Input Streams
num_bss = (gcap >> 3) & 0x1F    # Number of Bidirectional Streams
nsdo = (gcap >> 1) & 0x3        # Number of Serial Data Out signals
is_64ok = gcap & 0x1            # 64-bit Address Supported

print("Output Streams:  %d" % num_oss)
print("Input Streams:   %d" % num_iss)
print("Bidir Streams:   %d" % num_bss)
print("SDO Signals:     %d" % (nsdo + 1))
print("64-bit Address:  %s" % ("Yes" if is_64ok else "No"))

# Check GCTL — Global Control (BAR0 offset 0x08)
gctl = ace.bar0.gctl.read()
crst = gctl & 0x1  # Controller Reset Status
print("\nGCTL: 0x%08X (CRST=%d — %s)" % (gctl, crst, "Running" if crst else "In Reset"))

# Check STATESTS — State Change Status (BAR0 offset 0x0E)
# Bits indicate which SDI pins have codec presence
statests = ace.bar0.statests.read()
print("STATESTS: 0x%04X" % statests)
for sdi in range(2):  # HDALIPC=2
    present = (statests >> sdi) & 1
    print("  SDI%d: %s" % (sdi, "Codec PRESENT" if present else "No codec"))
```

### SSP/I2S Port Verification

```python
# SSP ports are configured via BAR0 region
# I2SPC=3 — verify 3 SSP ports are accessible
print("\n=== SSP/I2S Port Check ===")
for port in range(3):
    # SSP register access via ACE namednode path (per ACE 4.x HAS)
    # Pattern: soc.ace.ssp[N].sscr0, sscr1, sssr, sstsa, ssrsa
    sscr0 = eval("soc.ace.ssp%d.sscr0.read()" % port)
    sssr = eval("soc.ace.ssp%d.sssr.read()" % port)
    print("SSP%d: SSCR0=0x%08X  SSSR=0x%08X" % (port, sscr0, sssr))
```

### DSP Core Verification

```python
# Check PPCTL (Processing Pipe Control) — bit 30 = GPROCEN
ppctl = ace.bar0.ppctl.read()
gprocen = (ppctl >> 30) & 1
print("\n=== DSP Core Check ===")
print("PPCTL:    0x%08X" % ppctl)
print("GPROCEN:  %d — %s" % (gprocen, "DSP ENABLED (BAR2 accessible)" if gprocen else "DSP DISABLED"))

if gprocen:
    # BAR2 is accessible — can read DSP registers
    print("BAR2 DSP domain is accessible")
    # Read DSP core status registers from BAR2 region
else:
    print("WARNING: GPROCEN=0 — DSP BAR2 not accessible")
    print("To enable: Set PPCTL bit 30 (GPROCEN=1)")
```

---

## Part 3 — BIOS Configuration Verification

### Critical BIOS Knobs for Audio

| BIOS Setting | Expected Value | Effect |
|-------------|----------------|--------|
| **HD Audio** | Enabled | Enables ACE PCI function (0:31:3) |
| **HD Audio DSP** | Enabled | Enables DSP (GPROCEN) for audio processing |
| **HD Audio DMIC** | Enabled (per platform) | Enables DMIC interfaces |
| **SoundWire** | Enabled | Enables SoundWire links |
| **HD Audio Link** | Enabled | Enables HDA codec link |
| **Audio Codec** | Auto/Enabled | Selects audio codec configuration |
| **iDisplay Audio** | Enabled | Enables HDMI/DP audio output |

### ACPI Verification

The audio device should appear in the ACPI namespace. Key items to verify:

| ACPI Object | Description | Expected |
|-------------|-------------|----------|
| `\_SB.PCI0.HDAS` | HDA audio device | Present when audio enabled |
| `_HID` | Hardware ID | `INTC10B0` or similar (NVL-specific) |
| `_CID` | Compatible ID | May list HDA compat ID |
| `_DSM` | Device Specific Method | Audio-specific DSM functions |
| `_PS0` / `_PS3` | Power state methods | D0 / D3 transitions |

### Verification Script

```python
# Check if audio device is visible in ACPI
# This requires OS-level access — PythonSV checks PCI config directly

# Quick check: Is the device in D0 and memory-enabled?
cmd = ace.cfg.command.read()
pmcsr = ace.cfg.pmcsr.read()

mem_enabled = (cmd >> 1) & 1
bus_master = (cmd >> 2) & 1
power_state = pmcsr & 0x3

print("=== Audio BIOS Config Verification ===")
print("Memory Space:  %s" % ("Enabled" if mem_enabled else "DISABLED"))
print("Bus Master:    %s" % ("Enabled" if bus_master else "DISABLED"))
print("Power State:   D%d" % power_state)

if not mem_enabled:
    print("WARNING: Memory space not enabled — BARs not accessible")
    print("Check BIOS 'HD Audio' setting")
if power_state == 3:
    print("WARNING: Device in D3 — registers not accessible")
    print("Write PMCSR[1:0]=00 to transition to D0")
```

---

## Part 3B — Coupled vs Decoupled Audio Mode

*Source: [Wiki Page 4296597663]*

NVL audio can operate in two modes that fundamentally change the driver stack and device enumeration. Most FV testing uses **Decoupled Mode** (default), but some legacy codec tests require **Coupled Mode**.

### Mode Comparison

| Aspect | Decoupled Mode (Default) | Coupled Mode |
|--------|------------------------|--------------|
| **Driver** | Intel Smart Sound Technology (SST) | Microsoft HD Audio Class (UAA) |
| **DSP** | Enabled (GPROCEN=1) | Disabled (GPROCEN=0) |
| **Device Manager** | "Intel Smart Sound Technology" device | "High Definition Audio Controller" + codec nodes |
| **Codec visibility** | Managed by SST driver via DSP | Direct HDA codec enumeration (Realtek/iDisplay nodes visible) |
| **Use case** | Normal operation, all audio features | Legacy HDA testing, direct codec verb access |
| **BAR2 access** | Available (DSP domain) | Not available (DSP disabled) |

### Switching to Coupled Mode

```
BIOS Setup:
  1. Navigate to: PCH-IO Configuration → HD Audio Configuration
  2. Set "HD Audio DSP" = Disabled
  3. Set "HD Audio Compliance Mode" = UAA (Universal Audio Architecture)
  4. Save and reboot

Post-BIOS in Windows:
  1. Open Device Manager
  2. Uninstall "Intel Smart Sound Technology BUS" driver (if present)
  3. Restart
  4. Verify: "High Definition Audio Controller" appears under "Sound, video and game controllers"
  5. Realtek and/or iDisplay Audio codec nodes should be visible as child devices
```

### Switching Back to Decoupled Mode

```
BIOS Setup:
  1. Navigate to: PCH-IO Configuration → HD Audio Configuration
  2. Set "HD Audio DSP" = Enabled
  3. Set "HD Audio Compliance Mode" = (default / not UAA)
  4. Save and reboot

Post-BIOS in Windows:
  1. Intel SST driver should auto-install
  2. Verify: "Intel Smart Sound Technology" appears in Device Manager
  3. GPROCEN should be set (BAR2 accessible)
```

### Validation Points

| Check | Coupled Mode | Decoupled Mode |
|-------|-------------|---------------|
| GPROCEN (PPCTL bit 30) | `0` (DSP disabled) | `1` (DSP enabled) |
| Device Manager entry | HD Audio Controller + codec nodes | Intel Smart Sound Technology |
| HDA STATESTS | Shows codec presence directly | Managed by SST/DSP |
| BAR2 access | Not accessible | Accessible |
| CORB/RIRB | Host-driven verb transport | DSP-managed |

> **CRITICAL**: Do NOT run DSP-dependent tests (FW load, pipeline, UAOL, WoV) in Coupled Mode — GPROCEN=0 means no DSP access.

---

## Part 4 — Quick Enumeration Summary Script

```python
import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

def check_audio_enum(platform="nvl", die="pcd"):
    """Check audio/ACE enumeration across Intel Client SoC platforms.
    
    Args:
        platform: "nvl", "ptl", "lnl", "mtl", "arl", "wcl", "ttl", "rzl"
        die: "pcd" for PCD-H, "pch" for PCH-S, "soc" for SOC
    
    Platform → die path mapping:
        NVL PCD-H: socket0.pcd.ace   NVL PCH-S: socket0.pch.ace
        PTL/WCL:   socket0.soc.ace   LNL:       socket0.soc.ace
        MTL SOC-M: socket0.soc.ace   MTL PCH-S: socket0.pch.ace
        ARL:       socket0.pch.ace   TTL:       socket0.pcd.ace
        RZL:       socket0.pcd.ace
    """
    # Platform → (die_path_key, expected_did, display_name) mapping
    PLATFORM_MAP = {
        ("nvl", "pcd"):  ("pcd", 0xD328, "NVL PCD-H"),
        ("nvl", "pch"):  ("pch", 0xD228, "NVL PCH-S"),
        ("mtl", "soc"):  ("soc", 0x7E28, "MTL SOC-M"),
        ("mtl", "pch"):  ("pch", 0xAE28, "MTL PCH-S"),
        ("ptl", "soc"):  ("soc", None,   "PTL"),
        ("lnl", "soc"):  ("soc", None,   "LNL"),
        ("arl", "pch"):  ("pch", None,   "ARL"),
        ("wcl", "soc"):  ("soc", None,   "WCL"),       # Shares PTL DIDs
        ("ttl", "pcd"):  ("pcd", 0xD228, "TTL"),       # ⚠️ overlaps NVL PCH-S
        ("rzl", "pcd"):  ("pcd", 0xD328, "RZL"),       # ⚠️ overlaps NVL PCD-H
    }
    
    key = (platform.lower(), die.lower())
    if key not in PLATFORM_MAP:
        # Default fallback — try die path directly
        die_path_key, expected_did, die_name = die, None, "%s %s" % (platform.upper(), die.upper())
    else:
        die_path_key, expected_did, die_name = PLATFORM_MAP[key]
    
    ace = getattr(namednodes.sv.socket0, die_path_key).ace
    
    print("=" * 70)
    print("%s Audio/ACE Enumeration Summary" % die_name)
    print("=" * 70)
    
    # PCI Config
    vid = ace.cfg.vendor_id.read()
    did = ace.cfg.device_id.read()
    bar0 = ace.cfg.bar0.read()
    bar2 = ace.cfg.bar2.read()
    pmcsr = ace.cfg.pmcsr.read()
    
    ps = pmcsr & 0x3
    
    # GCAP and GCTL from BAR0
    if ps == 0 and bar0 != 0:
        gcap = ace.bar0.gcap.read()
        gctl = ace.bar0.gctl.read()
        statests = ace.bar0.statests.read()
        ppctl = ace.bar0.ppctl.read()
        crst = gctl & 0x1
        gprocen = (ppctl >> 30) & 1
    else:
        gcap = gctl = statests = ppctl = 0
        crst = gprocen = 0
    
    # Summary
    results = []
    did_ok = vid == 0x8086 and (expected_did is None or did == expected_did) and did != 0xFFFF
    did_str = "0x%04X/0x%04X" % (vid, did)
    if expected_did is None:
        did_str += " (DID unverified — check HAS)"
    results.append(("VID/DID", did_str, did_ok))
    results.append(("BAR0 (HDA)", "0x%08X" % bar0, bar0 != 0))
    results.append(("BAR2 (DSP)", "0x%08X" % bar2, bar2 != 0))
    results.append(("Power State", "D%d" % ps, ps == 0))
    results.append(("Controller", "Running" if crst else "In Reset", crst == 1))
    results.append(("GPROCEN (DSP)", "Enabled" if gprocen else "Disabled", True))  # May be intentionally off
    
    # Codec detection
    for sdi in range(2):
        present = (statests >> sdi) & 1
        results.append(("SDI%d Codec" % sdi, "Present" if present else "Not detected", True))
    
    for name, value, ok in results:
        status = "OK" if ok else "FAIL"
        print("  %-20s %-30s [%s]" % (name, value, status))
    
    print("=" * 70)
    
    # Return pass/fail
    return all(ok for _, _, ok in results[:4])  # Critical checks only

# Usage:
# check_audio_enum("nvl", "pcd")  # NVL PCD-H
# check_audio_enum("nvl", "pch")  # NVL PCH-S
# check_audio_enum("ptl", "soc")  # PTL
# check_audio_enum("wcl", "soc")  # WCL (shares PTL architecture)
# check_audio_enum("ttl", "pcd")  # TTL (ACE 3.0 or 4.0 — fuse-selected)
# check_audio_enum("rzl", "pcd")  # RZL (ACE 4.0)
# check_audio_enum("mtl", "soc")  # MTL SOC-M
# check_audio_enum("lnl", "soc")  # LNL
```

---

## Part 5 — Reset Architecture (HAS §8)

*Source: NVLDP ACE4.x Integration HAS Rev 1.2 — §8 Reset Transactions*

### Reset Input Signals

ACE IP receives four reset inputs from the SoC, each with different scope and stickiness:

| Reset Signal | Sticky | SoC Source | Scope |
|-------------|--------|------------|-------|
| `arsm_rst_b` | Yes | Host deep reset | Resume/deep reset — clears all non-AON state |
| `aprim_rst_b` | No | Host primary reset | IOSF Primary interface reset |
| `aside_rst_b` | No | Host sideband reset | IOSF Sideband interface reset |
| `aon_rst_b` | Yes | Host global reset | PGCB reset — only asserted on global reset / G3 |

> **Sticky** means the reset is NOT asserted on warm reset — only on cold/deep/global resets.

### Reset Behavior Matrix (NVLDP)

| IP Reset | Warm | Cold | Sx Entry | Global | G3 |
|----------|------|------|----------|--------|----|
| **PGCB** (`aon_rst_b`) | — | — | — | Asserted | Asserted |
| **Resume** (`arsm_rst_b`) | Asserted | Asserted | — | Asserted | Asserted |
| **Sideband** (`aside_rst_b`) | Asserted | Asserted | Asserted | Asserted | Asserted |
| **Primary** (`aprim_rst_b`) | Asserted | Asserted | Asserted | Asserted | Asserted |

### HD Audio Controller Reset Types

| Reset Type | Trigger | Scope | Preserves |
|-----------|---------|-------|-----------|
| **PLTRST#** | Platform reset (warm/cold) | Entire ACE controller + all links | Nothing |
| **CRST#** | Software via `GCTL.CRST=0` | Controller + links (unless `GCTL.LPLE=1`) | Link DMA + audio links if LPLE=1 |
| **SRST** | Per-stream reset | Single stream only | All other streams |
| **FLR** | Function Level Reset (PCIe cap) | Full function reset | PCI config (capabilities) |

> **FLR note**: Supported by ACE but NOT used by conventional PCI HD Audio driver. Intel HD Audio driver may use FLR for error recovery. ACE is exposed as PCI (not PCIe), so FLR is a capability extension.

### DSP Domain Reset

The DSP subsystem has a **separate reset domain** from the HD Audio controller:
- DSP powers up when `DSSCS.SPA=1` (Set Power Active)
- HW automatically sequences the DSP out of reset
- DSP domain includes: Tensilica cores, L2 SRAM, DMA engines, ML accelerators
- DSP reset does NOT affect HD Audio controller state

### PythonSV Reset Verification

```python
# Check reset-related registers
gctl = ace.bar0.gctl.read()
crst = gctl & 0x1
lple = (gctl >> 30) & 0x1

print("=== ACE Reset State ===")
print("GCTL:   0x%08X" % gctl)
print("CRST:   %d — %s" % (crst, "Controller Running" if crst else "IN RESET"))
print("LPLE:   %d — %s" % (lple, "Link Pipe preserved on CRST" if lple else "Links reset with CRST"))

# DSP domain reset state
dsscs = ace.bar2.dsscs.read() if bar2 != 0 else 0
spa = (dsscs >> 0) & 0x1
cpa = (dsscs >> 8) & 0x1
print("\nDSSCS:  0x%08X" % dsscs)
print("SPA:    %d (Set Power Active)" % spa)
print("CPA:    %d (Current Power Active — %s)" % (cpa, "DSP POWERED" if cpa else "DSP OFF"))
```

---

## Part 6 — BIOS Register Programming (HAS §23)

*Source: NVLDP ACE4.x Integration HAS Rev 1.2 — §23 BIOS Programming*

These registers MUST be programmed by BIOS during platform init. Incorrect programming causes audio failures, PM issues, or security violations.

### Critical BIOS-Programmed Registers

| Register | Purpose | NVLDP Value | Consequence if Wrong |
|----------|---------|-------------|---------------------|
| **FNCFG.BCLD** | BIOS Config Lock Down | Must be `1` | HW qualifier for clock-crossing on static BIOS registers — **audio will not operate correctly** if not set |
| **FNCFG.CGD** | Clock Gate Disable | `0` (enable CG) | Must clear during init (default=1 during reset disables all CG) |
| **FNCFG.ACED** | ACE Disable | `0` (enabled) | Set `1` + clear CGD = function-disable ACE |
| **EM1.BBRK** | PSF Request Size | Platform-specific | Performance optimization for IOSF Primary burst size |
| **DEVIDLEPOL** | Device Idle Policy | Platform-specific | SoC PG exit latency for D0i3 exit — wrong value causes PM timeout |
| **PCICFGHWI0** | PCI Config HW Init | Platform-specific | Platform config for different SW driver via class code override |
| **PTDC** | Power Tuning & Debug Control | Platform-specific | SoC PM tuning: logic gate PG, SRAM PG, SRAM retention timings |
| **TCA / TTCCFG** | TC/VC Mapping | Platform-specific | IOSF Primary fabric traffic class / virtual channel mapping |
| **EM1.TMODE / ETMODE** | iDisp-A Timing | Relaxed | iDisp-A codec SDI timing relaxation for display audio codec |
| **EM1.NODEID** | iDisp-A Node ID | Platform-specific | Widget node ID for `SET_CLKOFF` command to iDisplay codec |
| **BAR2::DfL2MPAT.PGSZ** | L2 SRAM Page Size | `4KB` for ≤64MB | Must coordinate with ACE IMR allocation (max 48MB on ACE 4.x) |

### BIOS Lock Down Verification

```python
# CRITICAL: FNCFG.BCLD must be set by BIOS
fncfg = ace.cfg.fncfg.read()
cgd = (fncfg >> 0) & 0x1   # Bit 0: Clock Gating Disable (per ACE 4.x HAS)
pgd = (fncfg >> 1) & 0x1   # Bit 1: Power Gating Disable
bcld = (fncfg >> 2) & 0x1  # Bit 2: BIOS Configuration Lock-Down

print("=== BIOS Programming Verification ===")
print("FNCFG:     0x%08X" % fncfg)
print("CGD:       %d — %s" % (cgd, "Clock gating DISABLED (debug)" if cgd else "Clock gating enabled (correct)"))
print("PGD:       %d — %s" % (pgd, "Power gating DISABLED (debug)" if pgd else "Power gating enabled (correct)"))
print("BCLD:      %d — %s" % (bcld, "LOCKED (correct)" if bcld else "UNLOCKED — BIOS BUG!"))

if not bcld:
    print("\n*** CRITICAL: FNCFG.BCLD=0 means BIOS did not lock down config ***")
    print("*** Audio may malfunction — static register clock-crossing not qualified ***")
```

### Fuse & Strap Verification

*Source: NVLDP ACE4.x Integration HAS Rev 1.2 — §21 Fuses*

| Fuse/Strap | Bits | NVLDP | Description |
|-----------|------|-------|-------------|
| `SSKUID[15:8]` | Valid | — | Silicon SKU ID |
| `SNDWD[6]` | Valid | `0` | SoundWire disable fuse (`1`=disabled) |
| `DSPSD[1]` | Valid | `0` | DSP subsystem disable fuse (`1`=disabled) |
| `AONVD[7]` | Reserved | — | AON Vision disable (reserved on NVLDP) |
| `XOCFS` | Hard strap | `01b` | XTAL frequency = 38.4 MHz |
| `DPGE` | Soft strap | `1` | Power gating enable |
| `DCGE` | Soft strap | `1` | Clock gating enable |
| `DBCLD` | Soft strap | — | BIOS lock down strap |

> **UAOL fuse** is on the xHCI side (not ACE). Check xHCI fuse registers for UAOL disable status.

---

## Troubleshooting Quick Reference

| Symptom | Check | Action |
|---------|-------|--------|
| VID=0xFFFF | BIOS audio enable | Enable "HD Audio" in BIOS setup |
| DID unexpected | Die variant mismatch | Confirm PCD-H vs PCH-S, check DID range |
| BAR0=0 | Memory space enable | Check Command register bit 1 |
| BAR2=0 | GPROCEN not set | Enable via PPCTL bit 30 (may need BIOS DSP enable) |
| STATESTS=0 | No codec detected | Check HDA link reset (GCTL.CRST), codec power, physical connection |
| Device in D3 | PMCSR[1:0]=11 | BIOS may have put device in D3; write PMCSR to 00 for D0 |
| GCAP=0 | Device not initialized | Controller may need reset cycle (GCTL.CRST 0->1) |
| Audio malfunction after boot | FNCFG.BCLD | Verify BIOS set BCLD=1 — required for clock-crossing |
| PM timeout on D0i3 exit | DEVIDLEPOL | Check BIOS programmed correct SoC PG exit latency |
| DSP won't power up | DSPSD fuse | Check fuse bit — `1` means DSP hardware-disabled |
| SoundWire links missing | SNDWD fuse | Check fuse bit — `1` means SoundWire hardware-disabled |
| Controller stuck after warm reset | GCTL.CRST | Warm reset asserts arsm_rst_b — verify CRST=1 after deassert |
