---
name: fv-gbe/platform
description: >-
  Per-platform GbE configuration data — Device IDs, BDF assignments, PythonSV namednode paths,
  BIOS knobs, power domains, known quirks, and platform-specific errata across Intel Client SoC
  platforms (NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL).
disable: false
---

# GbE Per-Platform Configuration Data

> **Purpose**: Single source of truth for platform-specific GbE hardware configuration.
> Load this sub-skill when answering questions about device IDs, BDF assignments, PythonSV
> named node paths, BIOS knobs, or any platform-specific GbE configuration.

---

## Controller Family Summary

| Controller | Speed | Interface | Integration | Driver (Windows) | Driver (Linux) |
|------------|-------|-----------|-------------|------------------|----------------|
| **I219-LM / I219-V** | 1 GbE | SGMII | MAC in PCH/SoC, PHY external | e1d68.sys | e1000e.ko |
| **I226-LM / I226-V** | 2.5 GbE | PCIe Gen3 x1 | Discrete chip | e2f68.sys | igc.ko |
| **I225-LM / I225-V** | 2.5 GbE | PCIe Gen3 x1 | Discrete chip | e2f68.sys | igc.ko |

---

## I219 BDF Assignment

**All platforms**: I219 is always at **Bus 0, Device 31, Function 6** = `00:1F.6`.

This is a fixed PCH function assignment — the I219 MAC is integrated into the PCH/SoC and does not participate in PCI bus enumeration or bridge assignment.

```
PCI Address: 0:1F:6
  Bus      = 0x00
  Device   = 0x1F (31)
  Function = 0x06
```

---

## Device ID Table

**Vendor ID**: All Intel GbE controllers use VID = **0x8086**.

### I219 Device IDs Per Platform

| Platform | Die | I219-LM DID | I219-V DID | Status |
|----------|-----|-------------|------------|--------|
| **MTL** | SOC-M | **0x550A** | **0x550B** | ✅ Verified |
| **MTL** | PCH-S | **0xAE08** | **0xAE09** | ✅ Verified |
| **LNL** | SOC | **0x7F0C** | **0x7F0D** | ✅ Verified |
| **ARL-U** | PCH | **0xA80D** | **0xA80E** | ✅ Verified |
| **ARL-S** | PCH | **0xA80D** | **0xA80E** | ✅ Verified |
| **PTL** | PCD | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |
| **NVL PCD-H** | PCD | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |
| **NVL PCH-S** | PCH | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |
| **WCL** | PCD | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |
| **TTL** | PCD | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |
| **RZL** | PCD | ⚠️ TBD | ⚠️ TBD | 🔴 Unverified |

> ⚠️ **TBD Device IDs**: Verify against the HAS/BIOS spec for your platform stepping before relying on these values. DIDs ending in `8`/`A`/`C` are typically the primary variant; `9`/`B`/`D` are alternate SKUs.

> **DID = 0xFFFF** at BDF 0:1F.6 means GbE is disabled in BIOS. Check the `LanEnable` BIOS knob.

### I226 / I225 Device IDs (Discrete)

| Controller | SKU | Device ID | Notes |
|------------|-----|-----------|-------|
| **I226-LM** | Corporate | **0x125B** | 2.5GbE with vPro |
| **I226-V** | Consumer | **0x125C** | 2.5GbE without vPro |
| **I225-LM** | Corporate | **0x15F2** | 2.5GbE with vPro (older) |
| **I225-V** | Consumer | **0x15F3** | 2.5GbE without vPro (older) |

I226/I225 are discrete PCIe devices — their BDF depends on which PCIe root port they connect to (board-specific).

---

## PythonSV Named Node Paths

GbE registers are accessed via PythonSV named nodes rooted at `namednodes.sv.socket0`.

### I219 Named Node Per Platform

| Platform | Die Type | PythonSV Path | Shorthand |
|----------|----------|---------------|-----------|
| **MTL SOC-M** | SOC | `namednodes.sv.socket0.soc.gbe` | `socket0.soc.gbe` |
| **MTL PCH-S** | PCH | `namednodes.sv.socket0.pch.gbe` | `socket0.pch.gbe` |
| **LNL** | SOC | `namednodes.sv.socket0.soc.gbe` | `socket0.soc.gbe` |
| **ARL-U** | PCH | `namednodes.sv.socket0.pch.gbe` | `socket0.pch.gbe` |
| **ARL-S** | PCH | `namednodes.sv.socket0.pch.gbe` | `socket0.pch.gbe` |
| **PTL** | PCD | `namednodes.sv.socket0.pcd.gbe` | `socket0.pcd.gbe` |
| **NVL PCD-H** | PCD | `namednodes.sv.socket0.pcd.gbe` | `socket0.pcd.gbe` |
| **NVL PCH-S** | PCH | `namednodes.sv.socket0.pch.gbe` | `socket0.pch.gbe` |
| **WCL** | PCD | `namednodes.sv.socket0.pcd.gbe` | `socket0.pcd.gbe` |
| **TTL** | PCD | `namednodes.sv.socket0.pcd.gbe` | `socket0.pcd.gbe` |
| **RZL** | PCD | `namednodes.sv.socket0.pcd.gbe` | `socket0.pcd.gbe` |

> **IMPORTANT**: Using the wrong die path is the #1 PythonSV bring-up mistake. If you get
> `AttributeError: 'NoneType' object has no attribute 'gbe'`, you are using the wrong die
> for your platform. Cross-check against this table.

### Alternative Named Node Path

On some platforms, the GbE named node may be accessed via the PCIe BDF path:

```python
# Via BDF path (works on all platforms)
gbe = sv.socket0.pcieB0D31F6

# Verify device identity
vid = gbe.vid.read()    # Should be 0x8086
did = gbe.did.read()    # Platform-specific
print(f"GbE: VID={vid:#06x} DID={did:#06x}")
```

---

## BIOS Knob Configuration

### Common GbE BIOS Knobs

| BIOS Knob | Token | Purpose | Recommended |
|-----------|-------|---------|-------------|
| `LanEnable` | `GBE_SUPPORT` | Enable/disable GbE controller | **Enabled** |
| `GbeLanPme` | `GBE_PME_SUPPORT` | PME enable for WoL | **Enabled** (for WoL) |
| `WakeOnLAN` | `WAKE_ON_LAN` | Wake-on-LAN enable | **Enabled** (for WoL) |
| `PchLanPowerCycleDelay` | — | Power cycle delay (ms) | Default |
| `GbeLanPhyReset` | — | PHY reset control | Default |
| `GbeLanK1Enable` | `GBE_K1_ENABLE` | Energy Efficient Ethernet (K1) | Default |
| `GbePhyPowerDnEnable` | — | PHY power down in S0ix | Platform-specific |

### Platform-Specific BIOS Notes

#### MTL
- `GbeLanK1Enable` may cause link stability issues with some switches
- WoL from S5 requires additional platform configuration in BSP

#### LNL
- GbE power domain is integrated — no separate power sequencing knobs
- EEE support confirmed working

#### ARL
- Check ARL PCH errata for any LAN power sequencing issues
- WoL from S4/S5 may require ACPI table updates

#### PTL / NVL / WCL / TTL / RZL
- ⚠️ BIOS knob names may differ — verify against platform BIOS spec

---

## Power Domain Configuration

### I219 Power Domains

| Platform | GbE Power Domain | S0ix Policy | Notes |
|----------|------------------|-------------|-------|
| **MTL** | PCH_PWRG_LANPHY | D3cold allowed | PHY powered off in S0ix |
| **LNL** | SOC_GBE_PG | D3cold allowed | Integrated power gating |
| **ARL** | PCH_PWRG_LANPHY | D3cold allowed | Same as MTL |
| **PTL** | TBD | TBD | Verify with BSP team |
| **NVL** | TBD | TBD | Verify with BSP team |

### LTR (Latency Tolerance Reporting)

GbE must program LTR correctly for S0ix entry. Check via PythonSV:

```python
# Read LTR values (adjust path per platform)
gbe = sv.socket0.pcieB0D31F6

# LTR Max Snoop Latency (PCIe capability)
ltr_snoop = gbe.ltr_max_snoop_lat.read()
print(f"LTR Max Snoop: {ltr_snoop:#06x}")

# LTR Max No-Snoop Latency
ltr_nosnoop = gbe.ltr_max_nosnoop_lat.read()
print(f"LTR Max No-Snoop: {ltr_nosnoop:#06x}")
```

> **LTR = 0** blocks S0ix entry. If GbE LTR is 0, check driver initialization.

---

## Platform-Specific Quirks and Errata

### MTL (Meteor Lake)

| Issue | Description | Workaround |
|-------|-------------|------------|
| SGMII link loss after S3 | Link doesn't come back after S3 resume | PHY reset during resume (driver fix) |
| Statistics stale after reset | GPRC/GPTC show stale values | Read stats after driver fully init |
| WoL S5 intermittent | WoL from S5 fails on some boards | Check BIOS WoL knobs + ACPI |

### LNL (Lunar Lake)

| Issue | Description | Workaround |
|-------|-------------|------------|
| Integrated power domain | Different from MTL — single power domain | N/A (by design) |
| EEE interop | EEE works but check switch compatibility | Disable EEE if interop issues |

### ARL (Arrow Lake)

| Issue | Description | Workaround |
|-------|-------------|------------|
| PCH errata | Check ARL PCH errata for GbE items | TBD |

### PTL / NVL / WCL / TTL / RZL

- ⚠️ **Pre-production platforms** — errata list TBD
- Verify known issues with platform BSP team
- Search HSDES for `I219 [platform]` sightings

---

## Quick Platform Reference Card

### MTL Quick Reference

```
Platform: MTL (Meteor Lake)
Die: SOC-M or PCH-S
I219 BDF: 00:1F.6
I219-LM DID: 0x550A (SOC-M), 0xAE08 (PCH-S)
I219-V DID: 0x550B (SOC-M), 0xAE09 (PCH-S)
PythonSV: sv.socket0.soc.gbe (SOC-M), sv.socket0.pch.gbe (PCH-S)
Driver: e1d68.sys (Win), e1000e.ko (Linux)
BIOS: LanEnable=Enabled, GbeLanPme=Enabled
Known Issues: SGMII link after S3, WoL S5 intermittent
```

### LNL Quick Reference

```
Platform: LNL (Lunar Lake)
Die: SOC (single die)
I219 BDF: 00:1F.6
I219-LM DID: 0x7F0C
I219-V DID: 0x7F0D
PythonSV: sv.socket0.soc.gbe
Driver: e1d68.sys (Win), e1000e.ko (Linux)
BIOS: LanEnable=Enabled, GbeLanPme=Enabled
Known Issues: EEE switch interop (rare)
```

### ARL Quick Reference

```
Platform: ARL (Arrow Lake)
Die: PCH
I219 BDF: 00:1F.6
I219-LM DID: 0xA80D
I219-V DID: 0xA80E
PythonSV: sv.socket0.pch.gbe
Driver: e1d68.sys (Win), e1000e.ko (Linux)
BIOS: LanEnable=Enabled, GbeLanPme=Enabled
Known Issues: Check PCH errata
```

### NVL Quick Reference

```
Platform: NVL (Novalake)
Die: PCD-H or PCH-S
I219 BDF: 00:1F.6
I219-LM DID: TBD
I219-V DID: TBD
PythonSV: sv.socket0.pcd.gbe (PCD-H), sv.socket0.pch.gbe (PCH-S)
Driver: e1d68.sys (Win), e1000e.ko (Linux)
BIOS: Verify knob names against NVL BIOS spec
Known Issues: TBD (pre-production)
```

---

## Verification Commands

### Verify Platform and DID

```python
# PythonSV — identify platform and GbE variant
gbe = sv.socket0.pcieB0D31F6

vid = gbe.vid.read()
did = gbe.did.read()
rev = gbe.rid.read()

print(f"VID: {vid:#06x}")   # Expect 0x8086
print(f"DID: {did:#06x}")   # Platform-specific
print(f"RevID: {rev:#04x}")

# Map DID to platform
DID_MAP = {
    0x550A: "MTL SOC-M I219-LM",
    0x550B: "MTL SOC-M I219-V",
    0xAE08: "MTL PCH-S I219-LM",
    0xAE09: "MTL PCH-S I219-V",
    0x7F0C: "LNL I219-LM",
    0x7F0D: "LNL I219-V",
    0xA80D: "ARL I219-LM",
    0xA80E: "ARL I219-V",
}
print(f"Platform: {DID_MAP.get(did, 'Unknown/TBD')}")
```

### Verify BIOS Knob Applied

```python
# Check if GbE is enabled (VID should be 0x8086, not 0xFFFF)
gbe = sv.socket0.pcieB0D31F6
vid = gbe.vid.read()
if vid == 0xFFFF:
    print("ERROR: GbE disabled in BIOS (VID=0xFFFF)")
    print("Action: Enable LanEnable BIOS knob")
else:
    print(f"GbE enabled (VID={vid:#06x})")
```
