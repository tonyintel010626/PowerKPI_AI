---
name: fv-usb/config-checkout
version: 1.0.0
owner: kvejaya
description: USB configuration checkout — PCI enumeration verification, BAR allocation, BIOS knob validation, and ACPI table checks for Intel Client SoC platforms
---

# FV-USB — Config Checkout Sub-Skill

## Purpose
Verify that USB/xHCI hardware is correctly enumerated, configured, and ready for functional validation. This is the **first step** before running any USB test — a misconfigured platform will produce false failures.

**Run config-checkout when:**
- Setting up a new platform for the first time
- After BIOS/IFWI flash
- After BKC update
- When tests fail with exit code 12 (device not found) or 13 (configuration error)
- When USB devices are missing or enumerated at wrong speed

---

## Config Checkout Checklist

### Step 1 — Verify xHCI PCI Enumeration

```python
# Check xHCI controller is enumerated in PCI
# Expected: Device present with correct DID/VID
import subprocess
result = subprocess.run(['pnputil', '/enum-devices', '/class', 'USB'], capture_output=True, text=True)
print(result.stdout)
```

**PythonSV (direct silicon access):**
```python
# Read xHCI PCI config space — DID/VID at offset 0x00
import pysvtools.pciedut as pcie
xhci = pcie.get_device(bus=0, dev=0x14, func=0)  # Typical BDF — varies per platform
did_vid = xhci.cfg.read(0x00, 4)
print(f"DID:VID = {did_vid:#010x}")
```

**Expected DID/VID per platform:**

| Platform | Typical BDF   | Expected DID | Notes                          |
|----------|---------------|-------------|--------------------------------|
| NVL PCH-H | 0:14.0      | Query HAS   | PCH-H die variant              |
| NVL PCH-S | 0:14.0      | Query HAS   | PCH-S die variant              |
| PTL      | 0:14.0        | Query HAS   | Panther Lake                   |
| LNL      | 0:14.0        | Query HAS   | Integrated SoC                 |
| MTL      | 0:14.0        | Query HAS   | Meteor Lake                    |
| ARL      | 0:14.0        | Query HAS   | Arrow Lake                     |

> **IMPORTANT:** Always query Co-Design HAS for the exact DID — never guess.
>
> **How to query:** Use `playwright_browser_navigate` to `https://chat.co-design.intel.com/chat`, then `playwright_browser_type` + `playwright_browser_snapshot` to ask: *"What is the xHCI Device ID (DID) for <PLATFORM>_USB_HAS?"*
>
> **Fallback:** If browser is unavailable, load the `codesign` skill for REST API access.

### Step 2 — Verify BAR Allocation

```python
# Read BAR0 (MMIO base address for xHCI registers)
bar0 = xhci.cfg.read(0x10, 4) & 0xFFFFF000  # Mask lower bits
print(f"BAR0 = {bar0:#010x}")
# BAR0 must be non-zero and 64KB-aligned for xHCI
assert bar0 != 0, "ERROR: BAR0 not allocated!"
assert (bar0 & 0xFFFF) == 0, "ERROR: BAR0 not 64KB-aligned!"
```

**Windows verification:**
```powershell
# Check BAR in Device Manager properties or via PowerShell
Get-PnpDeviceProperty -InstanceId "PCI\VEN_8086&DEV_XXXX*" -KeyName DEVPKEY_Device_Address
```

### Step 3 — Verify BIOS USB Knobs

Critical BIOS knobs that affect USB validation:

| BIOS Knob                    | Expected Value | Impact if Wrong                        |
|------------------------------|----------------|----------------------------------------|
| `USB Support`                | Enabled        | No USB at all                          |
| `XHCI Mode`                 | Enabled/Auto   | xHCI controller disabled               |
| `USB3 Speed`                 | Auto/Gen2      | May limit to Gen1 (5Gbps) only         |
| `UAOL Support`              | Enabled        | No USB audio offload (PTL/NVL)         |
| `RTD3 for USB`              | Enabled        | No runtime D3 power gating             |
| `USB Wake Support`          | Enabled        | No wake-on-USB from S3/S4/S0ix         |
| `USB Port Disable`          | All Enabled    | Specific ports won't enumerate         |
| `TCSS USB Enable`           | Enabled        | No Type-C USB (NVL/PTL)               |

> **How to check:** Load `securewiki` skill and search for BIOS knob documentation, or use PythonSV BIOS knob readback.

### Step 4 — Verify Port Count and Status

```python
# Read HCSPARAMS1 to get port count
from usb_helper_ipsv import USBHelper
helper = USBHelper()

# Check all ports
for port in range(1, helper.get_port_count() + 1):
    ccs = helper.get_ccs(port)      # Current Connect Status
    ped = helper.get_ped(port)      # Port Enabled
    speed = helper.get_speed(port)  # Speed encoding
    pls = helper.get_pls(port)      # Port Link State
    print(f"Port {port}: CCS={ccs} PED={ped} Speed={speed} PLS={pls}")
```

**Expected for connected device:**
- `CCS=1` (device connected)
- `PED=1` (port enabled)
- `Speed` matches device capability (4=SS 5Gbps, 5=SS+ 10Gbps, 3=HS)
- `PLS=0` (U0 — active link)

**Red flags:**
- `CCS=0` on a port with a physically connected device → cable/connector/signal integrity issue
- `PLS=4` (Disabled) → port disabled by BIOS or driver
- `PLS=10` (Compliance Mode) → signal integrity issue, see `known_issues.md`
- `Speed=1` for a USB3 device → device fell back to Full Speed (wrong)

### Step 5 — Verify USB Device Tree

```bash
# Run treeview to see full USB device tree
python treeview.py
```

**Check for:**
- All expected devices appear in the tree
- Devices are at correct speed (SS vs HS)
- No yellow-bang (driver failure) markers
- Hub topology matches physical setup

```bash
# Check for yellow-bang devices
python yellowbang_usb.py
```

### Step 6 — Verify UAOL Configuration (PTL/NVL only)

```python
# Check if UAOL is enabled and ACE is present
# ACE should be enumerated as a separate PCI device
# PTL: ACE3 | NVL: ACE4
```

**Registry check (Windows):**
```powershell
# UAOL enable/disable registry key
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\UAOL" -Name "Enable" -ErrorAction SilentlyContinue
```

> **UAOL NOT supported on:** MTL behind hub, LNL (no UAOL), ARL (no UAOL)

### Step 7 — Verify ACPI/SSDT Tables

```powershell
# Dump ACPI tables to check USB _DSM methods
# Use acpidump or AIDA64 to extract SSDT tables
# Look for USB device scope entries: \_SB.PCI0.XHCI
```

**Key ACPI objects to verify:**
- `_ADR` — PCI address matches expected BDF
- `_S0W` / `_S3W` / `_S4W` — Wake capability from sleep states
- `_DSM` — Device Specific Methods for USB features
- `_PRW` — Power Resources for Wake
- `_CRS` — Current Resource Settings

---

## Reusable Checkout Function

```python
def check_usb_config(platform="NVL"):
    """
    Run full USB configuration checkout.
    Returns dict with pass/fail for each check.
    
    Usage:
        results = check_usb_config("NVL")
        if all(results.values()):
            print("CONFIG CHECKOUT: PASS")
        else:
            failed = [k for k, v in results.items() if not v]
            print(f"CONFIG CHECKOUT: FAIL — {failed}")
    """
    from usb_helper_ipsv import USBHelper
    helper = USBHelper()
    results = {}
    
    # Check 1: xHCI enumerated
    try:
        port_count = helper.get_port_count()
        results['xhci_enumerated'] = port_count > 0
    except Exception:
        results['xhci_enumerated'] = False
    
    # Check 2: At least one port has CCS=1
    any_connected = False
    for port in range(1, port_count + 1):
        if helper.get_ccs(port) == 1:
            any_connected = True
            break
    results['device_connected'] = any_connected
    
    # Check 3: No yellow-bang devices
    import subprocess
    yb = subprocess.run(['python', 'yellowbang_usb.py'], capture_output=True, text=True)
    results['no_yellowbang'] = 'FAIL' not in yb.stdout.upper()
    
    # Check 4: Device tree populated
    tv = subprocess.run(['python', 'treeview.py'], capture_output=True, text=True)
    results['treeview_populated'] = len(tv.stdout.strip()) > 50
    
    return results
```

---

## Common Config Checkout Failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| BAR0 = 0 | BIOS didn't allocate resources | Check BIOS knob `XHCI Mode`; reflash BIOS |
| Port count = 0 | xHCI not initialized | Check USBCMD.Run bit; issue HCRST |
| All ports CCS=0 | No devices detected | Check physical connections, cables, hub power |
| Wrong speed | Cable or BIOS speed limit | Check USB3 Speed BIOS knob; try certified cable |
| Yellow-bang | Driver failure | Check driver version matches BKC; reinstall driver |
| UAOL not found | ACE not enumerated | Check BIOS UAOL knob; verify ACE FW version via `onebkc` |

---

## Cross-References

| Topic | Resource |
|-------|----------|
| Full enumeration debug | `fv-usb/enumeration` sub-skill |
| Register-level checks | `fv-usb/xhci` sub-skill |
| Power state verification | `fv-usb/power` sub-skill |
| Platform-specific BDF/DID | Co-Design HAS (use 5-step query) |
| BIOS knob documentation | `securewiki` skill — search FVCommon |
| BKC version check | `onebkc` skill |
