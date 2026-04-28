---
name: fv-usb/dbc
version: 1.0.0
owner: kvejaya
description: USB Debug Capability (DbC) setup, cable configuration, BIOS knobs, and S0ix interaction for Intel Client SoC platforms
---

# USB Debug Capability (DbC) Sub-Skill

## Purpose

Guide validation engineers through DbC test setup, cable selection, BIOS configuration, and debug triage. DbC provides JTAG-class debug access over USB without requiring a dedicated debug port — critical for USB test execution with DBC cables.

## When to Load This Skill

- Setting up DbC for USB test execution (NGA or manual)
- Debugging DbC enumeration failures
- Investigating S0ix blocks caused by DbC
- Selecting correct cable type for a debug scenario
- Configuring BIOS knobs for USB2DbC or USB3DbC

---

## 1. DbC Overview

DbC (Debug Capability) is an xHCI-defined mechanism that allows a USB port to act as a debug device. Intel platforms support two modes:

| Mode | Speed | S0ix Impact | Primary Use |
|------|-------|-------------|-------------|
| **USB2DbC** | 480 Mbps (HS) | Compatible (NVL+ with Debug Island) | Low-bandwidth debug, S0ix-safe scenarios |
| **USB3DbC** | 5 Gbps (SS) | **Blocks S0ix** even without active debug software | High-bandwidth debug, performance-critical scenarios |

> **Critical:** USB3DbC enumeration alone blocks S0ix entry. If S0ix validation is in scope, use USB2DbC or disconnect the DbC cable when not actively debugging.

---

## 2. ECTRL Register Configuration

The xHCI ECTRL (Extended Control) register controls DbC enablement.

### Required Bits (all must be set for DbC operation)

| Bit | Name | Description |
|-----|------|-------------|
| USB2DBC_en | USB2 Debug Enable | Enables USB2DbC mode on the assigned debug port |
| USB3DBC_en | USB3 Debug Enable | Enables USB3DbC mode on the assigned debug port |
| Debug_Enable | Master Debug Enable | Global enable for debug capability |

### ENUM_CFG Field (ECTRL bits [13:10])

Controls which USB speeds are enumerated for debug:

| Bit | Speed | Notes |
|-----|-------|-------|
| Bit 13 | USB 3.1 (10 Gbps) | Enhanced SuperSpeed |
| Bit 12 | USB 3.0 (5 Gbps) | SuperSpeed |
| Bit 11 | USB 2.0 (480 Mbps) | High-Speed |
| Bit 10 | USB4 (20/40 Gbps) | Platform-dependent support |

### Verify DbC Register State (PythonSV)

```python
# Read ECTRL register
import pysvtools.pciedirect as pcie
ectrl = pcie.read_cfg(0, 0x14, 0, 0x9C)  # BDF varies by platform
print(f"ECTRL: 0x{ectrl:08X}")
print(f"  USB2DBC_en:    {bool(ectrl & (1 << 0))}")
print(f"  USB3DBC_en:    {bool(ectrl & (1 << 1))}")
print(f"  Debug_Enable:  {bool(ectrl & (1 << 2))}")
print(f"  ENUM_CFG:      0x{(ectrl >> 10) & 0xF:X}")
```

---

## 3. Cable Selection Guide

Cable type determines DbC behavior and requires matching BIOS/strap configuration.

| Cable Type | Connector | Strap Required | Supported | Notes |
|------------|-----------|----------------|-----------|-------|
| **A-to-A** | Type-A ↔ Type-A | Yes (soft strap) | Yes | Legacy debug cable; requires EN_DBC_PORT strap |
| **A-to-C UFP** | Type-A ↔ Type-C (UFP) | No | Yes | Standard debug cable; recommended for most scenarios |
| **C-to-C DFP-UFP** | Type-C (DFP) ↔ Type-C (UFP) | No | Yes | Supported orientation |
| **C-to-C UFP-DFP** | Type-C (UFP) ↔ Type-C (DFP) | N/A | **NO** | Not supported — will not enumerate |

> **Recommendation:** Use A-to-C UFP cable for simplest setup. Use C-to-C DFP-UFP only when Type-A is unavailable on the host.

### Soft Strap: EN_DBC_PORT

- Assigns a specific USB port for debug use
- **Required** for A-to-A cables
- On LNL and later platforms, enhanced strap support allows more flexible port assignment (ref: HSD 22012601204)

---

## 4. BIOS Knob Configuration

### Essential BIOS Knobs

| Knob | Path | Value | Purpose |
|------|------|-------|---------|
| `USB Debug` | Advanced > USB Configuration | **Enabled** | Master DbC enable |
| `xDCI Support` | Advanced > USB Configuration | **Disabled** | Conflicts with DbC on shared port |
| `USB2 Debug Port` | Advanced > USB Configuration > Debug | Port number | Selects USB2DbC port |
| `USB3 Debug Port` | Advanced > USB Configuration > Debug | Port number | Selects USB3DbC port |

### Platform-Specific Notes

| Platform | BDF | Debug Port Default | Notes |
|----------|-----|-------------------|-------|
| NVL PCD-H | 0:20.0 | Check BIOS | Full Debug Island for USB2DbC S0ix debug |
| NVL PCD-S | 0:20.0 | Check BIOS | Full Debug Island for USB2DbC S0ix debug |
| PTL | 0:14.0 | Check BIOS | Legacy BDF |
| LNL | 0:20.0 | Check BIOS | Enhanced strap support (HSD 22012601204) |
| ARL | 0:20.0 | Check BIOS | Shares DID pattern with LNL |
| MTL | 0:20.0 | Check BIOS | SOC-M/P variants |

> **Load `fv-usb/platform` skill** for complete BDF/DID/port-count data per platform variant.

---

## 5. DbC Test Setup Procedure

### Step 1: Pre-Flight Checks

```
1. Confirm cable type matches configuration (see Section 3)
2. Verify BIOS knobs are set (see Section 4)
3. Ensure xDCI is DISABLED (conflicts with DbC on shared port)
4. If A-to-A cable: confirm EN_DBC_PORT soft strap is programmed
```

### Step 2: Connect and Verify Enumeration

```powershell
# On HOST side (the machine running debug software):
# Check if DbC device enumerates
pnputil /enum-devices /connected | findstr /i "debug"

# On DUT side (device under test):
# Verify xHCI sees debug capability
# Use Device Manager > Universal Serial Bus controllers
# Look for "USB Debug Connection" device
```

### Step 3: Validate Debug Connection

```powershell
# If using WinDbg over USB:
windbg -k usb:targetname=<target_name>

# If using Intel DCI/DAL:
# Follow Intel DAL tool documentation for USB transport setup
```

### Step 4: S0ix Interaction Check

If S0ix validation is also in scope:

```
1. With USB3DbC cable connected → verify S0ix is BLOCKED (expected)
2. Disconnect USB3DbC cable → verify S0ix resumes
3. With USB2DbC cable on NVL+ → verify S0ix via Debug Island (platform-specific)
```

> **Cross-reference:** Load `fv-usb/power` skill for full S0ix validation procedures and LTR/LPM interaction.

---

## 6. S0ix and DbC Interaction

### USB3DbC Blocks S0ix

USB3DbC enumeration prevents S0ix entry **even without active debug software connected**. This is by design — the SuperSpeed link must remain active for debug readiness.

**Mitigation options:**
1. Use USB2DbC instead (HS-only, S0ix-compatible on NVL+ with Debug Island)
2. Physically disconnect the USB3DbC cable when not debugging
3. Disable USB3DBC_en in ECTRL when running S0ix tests

### NVL Debug Island

NVL PCH includes a dedicated "Debug Island" that allows USB2DbC to remain active during S0ix:
- Only available on NVL PCD-H and PCD-S variants
- USB2DbC traffic is routed through the always-on debug domain
- Does NOT apply to USB3DbC (still blocks S0ix)

### Timing Considerations

| Scenario | S0ix Entry | Wake Latency | Notes |
|----------|-----------|--------------|-------|
| No DbC cable | Normal | Normal | Baseline |
| USB2DbC (NVL+ Debug Island) | Allowed | +50-100 µs | Debug Island overhead |
| USB2DbC (pre-NVL) | May block | N/A | Platform-dependent |
| USB3DbC connected | **Blocked** | N/A | By design |
| USB3DbC cable, USB3DBC_en=0 | Allowed | Normal | Must verify no SS link |

---

## 7. Known Issues and Sightings

| HSD ID | Summary | Platforms | Workaround |
|--------|---------|-----------|------------|
| 14026999287 | USB3DbC cable inserted when USB3DBC_en=0 causes unexpected behavior | Multiple | Physically disconnect cable if USB3DbC is disabled |
| 22012601204 | LNL+ enhanced EN_DBC_PORT strap support | LNL, ARL, NVL, PTL | Use updated BIOS with enhanced strap programming |

> **Cross-reference:** Load `fv-usb/debug` skill for full sighting database and triage workflows. Check `docs/known_issues.md` for the complete known-issues list.

---

## 8. Troubleshooting

### DbC Device Not Enumerating

```
1. Check cable orientation (C-to-C UFP-DFP is NOT supported)
2. Verify BIOS knobs: USB Debug = Enabled, xDCI = Disabled
3. Check ECTRL register: all three enable bits must be set
4. Try different USB port (some ports may not support DbC)
5. For A-to-A cable: verify EN_DBC_PORT soft strap
6. Check if port is claimed by another function (xDCI, UAOL)
```

### DbC Enumerates but No Debug Connection

```
1. Verify debug software is configured for USB transport
2. Check target name matches between host and DUT
3. Ensure no firewall/security software is blocking USB debug
4. Try USB2DbC if USB3DbC is unreliable (cable/signal quality)
```

### S0ix Blocked Unexpectedly After DbC Testing

```
1. Verify DbC cable is physically disconnected
2. Check ECTRL: USB3DBC_en should be 0 if not debugging
3. Run SLP_S0 residency check (load fv-usb/power skill)
4. Check for lingering DbC device in Device Manager
5. Cold reboot if hot-unplug doesn't clear the state
```

---

## 9. Quick Reference

### Minimum Viable DbC Setup

```
Cable:     A-to-C UFP (simplest)
BIOS:      USB Debug = Enabled, xDCI = Disabled
ECTRL:     USB2DBC_en=1, Debug_Enable=1 (USB2DbC)
           USB3DBC_en=1, Debug_Enable=1 (USB3DbC)
Verify:    pnputil /enum-devices /connected | findstr "debug"
```

### Decision: USB2DbC vs USB3DbC

```
Need S0ix testing?
  YES → Use USB2DbC (or disconnect cable during S0ix tests)
  NO  → Use USB3DbC for better bandwidth

Need high-bandwidth debug trace?
  YES → USB3DbC (5 Gbps)
  NO  → USB2DbC (480 Mbps, S0ix-safe on NVL+)
```

---

## 10. USB Diagnostic Device Class Codes (DCh)

DbC devices enumerate using the **Diagnostic Device** class (BaseClass = `0xDC`). Knowing these class codes is essential for verifying correct enumeration in Device Manager, `pnputil`, and USB analyzers.

### DCh SubClass/Protocol Matrix (USB-IF Defined Class Codes)

| BaseClass | SubClass | Protocol | Usage Level | Description |
|-----------|----------|----------|-------------|-------------|
| `DCh` | `01h` | `01h` | Device | **USB2 Compliance Device** — enumerates during USB2 electrical compliance testing |
| `DCh` | `02h` | `00h` | Device | **Debug Target (Vendor-specific)** — generic debug target over DbC |
| `DCh` | `02h` | `01h` | Device | **GNU Remote Debug** — GDB stub over USB DbC |
| `DCh` | `03h` | `01h` | Interface | **Vendor Trace on DbC** — firmware/platform trace streamed over Debug Capability |
| `DCh` | `04h` | `01h` | Interface | **Vendor Dfx on DbC** — design-for-debug (Intel DCI/DAL) over Debug Capability |
| `DCh` | `05h` | `00h` | Interface | **Trace on DvC** — trace on Debug via Capability (DvC path) |
| `DCh` | `06h` | `01h` | Interface | **Dfx on DvC** — design-for-debug over DvC path |

> **Intel DCI/DAL context:** When using Intel DCI over USB DbC, the device enumerates as `DCh/04h/01h` (Vendor Dfx on DbC). If you see `DCh/02h/00h` instead, the debug target is in vendor-specific mode — verify the DCI transport configuration.

### How to Check the Class Code

```powershell
# Enumerate all connected USB devices and show class codes
pnputil /enum-devices /connected /class USB

# More detail via WMI — shows ClassCode for each device
Get-WmiObject Win32_USBControllerDevice | ForEach-Object {
    $_.Dependent.Split("=")[1] -replace '"',''
} | ForEach-Object { pnputil /enum-devices /instanceid $_ }
```

```python
# Via USBHelper: check device class on enumerated port
from usb_helper_ipsv import USBHelper
helper = USBHelper()
desc = helper.get_device_descriptor(port=1)
print(f"bDeviceClass:    0x{desc.bDeviceClass:02X}")
print(f"bDeviceSubClass: 0x{desc.bDeviceSubClass:02X}")
print(f"bDeviceProtocol: 0x{desc.bDeviceProtocol:02X}")
```

### Quick DbC Enumeration Validation Checklist

```
DbC enumerated correctly?
  → bDeviceClass    = 0xDC  (Diagnostic Device)
  → bDeviceSubClass = 0x02  (Debug Target) or 0x04 (Dfx on DbC for DCI)
  → bDeviceProtocol = 0x00 or 0x01 depending on debug software

USB2 Compliance testing?
  → Expect bDeviceClass=0xDC, SubClass=0x01, Protocol=0x01
  → Port should be in Compliance Mode (PORTSC.PLS=10) before test device connects

Vendor trace (ITP/DAL trace over DbC)?
  → bDeviceClass=0xDC, SubClass=0x03, Protocol=0x01
```

---

## Source References

- USB3DBC_EAVAILS_FEATURE_HAS.html (Co-Design / Intel HAS)
- NVL_Standalone_USB_Subsystem_Integration_HAS.html (Co-Design / Intel HAS)
- xHCI Specification, Section 7.6 (Debug Capability)
- USB-IF Defined Class Codes — https://www.usb.org/defined-class-codes (BaseClass DCh, last updated Sep 2023)
