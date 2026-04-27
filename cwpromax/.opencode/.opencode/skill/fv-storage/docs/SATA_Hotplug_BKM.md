# SATA Hotplug Surprise Removal — BKM

**Wiki Source**: [Page ID: 2016451763](https://wiki.ith.intel.com/spaces/DebugEncyclopedia/pages/2016451763/SATA+Hotplug) (DebugEncyclopedia space)
**Author**: Ainalmardhiah Ulul-Azmin (ainalmardhiah.ulul-azmin@intel.com)
**Script**: `SATA_Hotplug_Surprise_Removal_Silicon.py` (in this directory)

---

## Overview

This BKM documents the automated SATA Hotplug Surprise Removal validation procedure using a **Quarch Torridon 4-Port Array Controller (QTL1461)** and **PythonSV**. The Quarch module physically controls SATA device power (plug/pull) while PythonSV reads SATA port status registers (`PxSSTS`) to verify the controller correctly detects device insertion and removal.

---

## Hardware Requirements

| Component | Details |
|-----------|---------|
| **Quarch Module** | QTL1461 — Torridon 4-Port Array Controller |
| **Connection** | USB from host to Quarch module |
| **SATA Devices** | Up to 4 SATA drives connected through Quarch ports |
| **Platform** | Intel platform with SATA controller (PCH-based) |
| **Probe** | XDP/DCI probe for PythonSV access |

### Quarch Port Mapping

The Quarch QTL1461 has 4 ports. Each Quarch port maps to a SATA controller port. The mapping depends on physical cabling:

- Quarch Port 1 → typically SATA Port 0
- Quarch Port 2 → typically SATA Port 1
- Quarch Port 3 → typically SATA Port 2
- Quarch Port 4 → typically SATA Port 3

> **Note**: Verify your specific cabling. The sample log shows Quarch Port 1 connected to SATA Port 0.

---

## Software Prerequisites

| Software | Purpose |
|----------|---------|
| **Python 3.x** | Script runtime |
| **quarchpy** | Python library for Quarch module communication |
| **TestMonkey2** (v2.6.26+) | Quarch management software |
| **Quarch USB Driver** (Win10 v1.0.5) | USB driver for QTL1461 |
| **PythonSV** | Silicon validation framework (namednodes, svtools, baseaccess) |

### Installation

1. Install **TestMonkey2** from the wiki attachment: `TestMonkey2-Installer-2.6.26.zip`
2. Install **Quarch USB Driver**: `Torridon_USB_Driver_Win_10_v1.0.5.zip`
3. Install **quarchpy**: `pip install quarchpy`
4. Ensure PythonSV environment is set up with probe connection to the target

---

## BIOS Configuration

**Required BIOS settings** (Intel Advanced Menu → PCH-IO Configuration → SATA and RST Configuration → Port):

| Setting | Value | Notes |
|---------|-------|-------|
| **Hot Plug** | **Enabled** | Must be enabled for hotplug detection |
| **DevSlp** | **Disabled** | Must be disabled — conflicts with hotplug |

> **Warning**: If DevSleep is enabled, the SATA port may not correctly detect device removal/insertion.

---

## Script Usage

### Command Line

```bash
python SATA_Hotplug_Surprise_Removal_Silicon.py [-d DEVICES] [-cycle CYCLEHOTPLUG]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `-d` / `--devices` | 1 | Number of SATA devices connected to Quarch |
| `-cycle` / `--cyclehotplug` | 1 | Number of hotplug cycles to execute |

### Examples

```bash
# Single device, 1 cycle
python SATA_Hotplug_Surprise_Removal_Silicon.py

# 2 devices, 10 hotplug cycles
python SATA_Hotplug_Surprise_Removal_Silicon.py -d 2 -cycle 10

# 4 devices, 100 cycles (stress test)
python SATA_Hotplug_Surprise_Removal_Silicon.py -d 4 -cycle 100
```

---

## Script Flow

```
1. Initialize Quarch module (USB:QTL1461-06-662)
2. Set all Quarch ports to default state (plugged)
3. Power up any pulled devices
4. Count connected devices
5. Read initial PxSSTS for all 8 SATA ports (ports 0-7)
6. For each cycle (1..N):
   a. PULL: Power down all 4 Quarch ports
   b. Wait 30 seconds
   c. Verify PxSSTS = 0x0 or 0x4 (no device / PHY offline)
   d. PLUG: Power up all 4 Quarch ports
   e. Wait 30 seconds
   f. Verify PxSSTS restored to initial values
   g. Report cycle PASS/FAIL
7. Generate svtools HTML report with PASS/FAIL insight
```

---

## Key Register: PxSSTS (Serial ATA Status)

The script reads `pch.sata.portN.pxsstsN` via PythonSV namednodes to verify hotplug detection.

| PxSSTS Value | Meaning | Expected When |
|-------------|---------|---------------|
| `0x133` | Gen3 (6 Gbps), PHY ready, device active | Device plugged and linked |
| `0x123` | Gen2 (3 Gbps), PHY ready, device active | Device plugged (Gen2) |
| `0x113` | Gen1 (1.5 Gbps), PHY ready, device active | Device plugged (Gen1) |
| `0x0` | No device detected | Device pulled (surprise removal) |
| `0x4` | PHY offline | Device pulled (PHY disabled) |

### PxSSTS Bit Field Decode

| Bits | Field | Description |
|------|-------|-------------|
| 3:0 | DET | Device Detection: 0=none, 1=PHY detected, 3=PHY+device, 4=offline |
| 7:4 | SPD | Current Speed: 0=none, 1=Gen1, 2=Gen2, 3=Gen3 |
| 11:8 | IPM | Interface Power Mgmt: 0=not present, 1=active, 2=partial, 6=slumber, 8=devsleep |

---

## Pass/Fail Criteria

A cycle **PASSES** when ALL of these conditions are met:
1. All connected devices report PULLED state on Quarch module after power down
2. All initially-active SATA ports show PxSSTS = 0x0 or 0x4 after pull
3. All connected devices report PLUGGED state on Quarch module after power up
4. All initially-active SATA ports restore to their original PxSSTS value after plug (no plug errors)

The overall test **PASSES** when all cycles pass.

---

## Sample Log Output

```
**********************************************************************************
*                   Log file for SATA HotPlug Surprise Removal                   *
**********************************************************************************

Module Name: Torridon 4 Port Array Controller
Total cycle: 2

SATA status before run HotPlug:
Port 0 status: 0x133
Port 1 status: 0x0
...

----------------------------------
|     Starting HotPlug cycle     |
----------------------------------

HotPlug Cycle: 0
Pulling the device,
SATA status after devices are pulled:
Port 0 status: 0x0
...
Plugging the device.
SATA status after devices are plugged:
Port 0 status: 0x133
...
Cycle 0 : All SATA devices success to run HotPlug Surprise Removal

Cycle finished!
PASSED: All SATA devices success to run HotPlug Surprise Removal for 2 cycle
```

---

## Customization Notes

- **Quarch Module String**: The script hardcodes `"USB:QTL1461-06-662"`. Update `moduleStr` in `main()` to match your specific Quarch module serial number.
- **Wait Times**: The script uses 30-second waits after pull and plug operations. Adjust `time.sleep(30)` if your drives require different settling times.
- **Port Range**: The script reads all 8 SATA ports (0-7). If your platform has fewer ports, unused ports will show 0x0 (which is fine — the script only validates ports that had active devices initially).

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `FAIL: 0x26 - No device attached` | Quarch port has no drive | Connect a SATA drive to that Quarch port, or reduce `-d` count |
| PxSSTS stays 0x133 after pull | BIOS Hot Plug not enabled | Enable Hot Plug in BIOS SATA settings |
| PxSSTS stays 0x0 after plug | Drive didn't re-link | Increase wait time; check cable; check drive health |
| `quarchpy` import error | Quarch library not installed | `pip install quarchpy` |
| `namednodes` import error | PythonSV not configured | Set up PythonSV environment with probe connection |
| Script hangs at `quarchDevice()` | Quarch not connected or wrong serial | Check USB connection; update `moduleStr` |

---

## References

- **Wiki Page**: [SATA HotPlug](https://wiki.ith.intel.com/spaces/DebugEncyclopedia/pages/2016451763/SATA+Hotplug) (Page ID: 2016451763)
- **Quarch Technical Manual**: `QTL1461 - 4 Port Array Controller - Technical Manual.pdf` (wiki attachment)
- **Quarch Automation Manual**: `Quarch Automation Manual v1.0.pdf` (wiki attachment)
- **SATA 3.0 Controller HAS**: `fv-storage/docs/SATA 3.0 Controller.pdf` — Section 10.3.1.4 (Port Interface Registers, PxSSTS)
- **AHCI Spec 1.3.1**: PxSSTS register definition (Section 3.3.10)
