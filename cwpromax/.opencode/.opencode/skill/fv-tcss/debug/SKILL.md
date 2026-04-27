# TCSS Debug — Failure Triage, HSDES Sightings, and Known Issues

## Overview

This sub-skill provides debug workflows, failure triage methodologies, HSDES sighting database, and known issues for TCSS functional validation.

## Debug Workflow

### Initial Triage Process

```
1. Identify Symptom
   ↓
2. Gather Platform Context
   ↓
3. Check Known Issues
   ↓
4. Collect Debug Logs
   ↓
5. Analyze Failure Signature
   ↓
6. Search HSDES
   ↓
7. Root Cause or Escalate
```

## Failure Signatures

### Common Failure Patterns

| Symptom | Likely Component | Initial Debug Steps |
|---------|------------------|---------------------|
| Device not detected | Enumeration, IOM | Check PCI config, verify BDF, IOM registers |
| Authentication timeout | Thunderbolt controller | Check security level, device UUID, FW version |
| Link training failure | Physical layer, cable | Verify cable spec, check link status registers |
| No video output | DisplayPort, IOM mux | Check HPD, EDID, DP link training, mux state |
| Low throughput | DMA, bandwidth allocation | Check DMA config, bandwidth registers, QoS |
| Power state stuck | Power management | Check D-state registers, PMC interface |
| Wake not working | Wake logic, PMC | Verify wake enable, check PMC wake status |

## Debug Log Collection

### Linux Debug Logs

```bash
# Kernel messages
dmesg | grep -i "thunderbolt\|usb4\|typec" > tcss_dmesg.log

# Thunderbolt device tree
tree /sys/bus/thunderbolt/devices/ > tcss_device_tree.txt

# Type-C port status
for port in /sys/class/typec/port*/; do
    echo "=== $(basename $port) ===" >> tcss_typec.log
    cat $port/* 2>/dev/null >> tcss_typec.log
done

# PCI configuration
lspci -vvv | grep -A 40 "Thunderbolt" > tcss_pci.log

# Power management status
cat /sys/bus/pci/devices/0000:*/power/runtime_status > tcss_power.log
```

### Windows Debug Logs

```powershell
# Event logs
Get-WinEvent -LogName "Microsoft-Windows-Thunderbolt/Operational" | 
    Export-Csv tcss_events.csv

# Device Manager export
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*Thunderbolt*" -or 
    $_.FriendlyName -like "*USB4*"} | Export-Csv tcss_devices.csv

# Power state
powercfg /devicequery all > tcss_power.txt
```

### PythonSV Debug Dump

```python
# Comprehensive register dump
def dump_tcss_debug():
    target = get_target()  # Platform-specific
    
    # TCSS controller
    tcss = getattr(target, "tcss", None)
    if tcss:
        print(f"=== TCSS Controller ===")
        print(f"DID: 0x{tcss.cfg.device_id.read():04X}")
        print(f"VID: 0x{tcss.cfg.vendor_id.read():04X}")
        print(f"BAR0: 0x{tcss.cfg.bar0.read():016X}")
    
    # IOM
    iom = getattr(target, "iom", None)
    if iom:
        print(f"=== IOM ===")
        print(f"Port0 Config: 0x{iom.port0.config.read():08X}")
        print(f"Port0 Status: 0x{iom.port0.status.read():08X}")
    
    # Power management
    tcss_pwr = getattr(target, "tcss_power", None)
    if tcss_pwr:
        print(f"=== Power ===")
        print(f"Power State: 0x{tcss_pwr.status.read():08X}")
```

## Known Issues Database

> **TODO:** Populate this section as TCSS-specific issues are discovered.

### RTL Bugs

| HSDES ID | Platform | Component | Summary | Workaround | Status |
|----------|----------|-----------|---------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD |

### Driver/FW Issues

| HSDES ID | Platform | Component | Summary | Workaround | Status |
|----------|----------|-----------|---------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD |

### Platform-Specific Issues

| HSDES ID | Platform | Component | Summary | Workaround | Status |
|----------|----------|-----------|---------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD |

## Triage Checklists

### Enumeration Failure

- [ ] Verify TCSS device appears in `lspci` / Device Manager
- [ ] Check Device ID matches platform specification
- [ ] Verify BAR0 allocation is correct
- [ ] Check BIOS settings for TCSS enable
- [ ] Verify platform straps/fuses
- [ ] Check PMC power state
- [ ] Review BIOS boot logs for TCSS init errors

### Thunderbolt Authentication Failure

- [ ] Check security level setting (SL0/SL1/SL2)
- [ ] Verify device UUID readable
- [ ] Check Thunderbolt controller FW version
- [ ] Review authentication timeout value
- [ ] Test with known-good device
- [ ] Check user authorization policy (Windows/Linux)
- [ ] Review Thunderbolt event logs

### Link Training Failure

- [ ] Verify cable specification (passive/active, length, speed)
- [ ] Test with different cable
- [ ] Check link status registers
- [ ] Verify lane count negotiation
- [ ] Check for signal integrity issues (BER)
- [ ] Test both cable orientations
- [ ] Review link training timeout values

### DisplayPort No Video

- [ ] Check HPD status (asserted/deasserted)
- [ ] Verify EDID readable
- [ ] Check DP link training status
- [ ] Verify mux state (DP mode selected)
- [ ] Test with different display/cable
- [ ] Check DP AUX channel communication
- [ ] Review display driver logs

### DMA Performance Issue

- [ ] Check DMA descriptor configuration
- [ ] Verify bandwidth allocation registers
- [ ] Check for DMA errors in status registers
- [ ] Review DMA interrupt latency
- [ ] Check memory bandwidth contention
- [ ] Verify buffer alignment
- [ ] Review QoS settings

### Power Management Issue

- [ ] Check D-state transition registers
- [ ] Verify context save/restore
- [ ] Check PMC interface status
- [ ] Review wake enable configuration
- [ ] Check S0ix entry/exit logs
- [ ] Verify RTD3 policy settings
- [ ] Check power rail voltage levels

## Debug Tools Reference

### Intel Internal Tools

| Tool | Purpose | Location |
|------|---------|----------|
| **PythonSV** | Direct register access | Platform-specific installation |
| **TTK3** | Hardware-level debug, power control | Lab equipment |
| **JTAG/ITP** | Low-level silicon debug | Lab equipment |

### OS-Level Tools

| Tool | Platform | Purpose |
|------|----------|---------|
| **lspci** | Linux | PCI enumeration |
| **dmesg** | Linux | Kernel messages |
| **tree** | Linux | File system tree view |
| **Device Manager** | Windows | Device enumeration |
| **Event Viewer** | Windows | System event logs |
| **powercfg** | Windows | Power configuration |

### Specialized Tools

| Tool | Purpose |
|------|---------|
| **Thunderbolt Control Center** | Thunderbolt device management (Windows) |
| **boltctl** | Thunderbolt management (Linux) |
| **edid-decode** | EDID parsing |
| **usb-devices** | USB topology viewer |

## HSDES Search Keywords

### Effective Search Terms

| Category | Keywords |
|----------|----------|
| **Component** | TCSS, USB4, Thunderbolt, TBT, iTBT, IOM |
| **Protocol** | DisplayPort, DP, PCIe, USB3 |
| **Symptom** | "not detected", "authentication fail", "link training", "no video" |
| **Platform** | MTL, NVL, TTL, plus stepping (A0, B0, etc.) |
| **Domain** | CVE, FV, validation, silicon |

### HSDES Query Examples

```
title:"TCSS" AND platform:"NVL" AND status:("Open" OR "Fixed")
component:"Thunderbolt" AND severity:(1 OR 2)
summary:"USB4 authentication" AND project:"MTL"
```

## Escalation Path

### When to Escalate

| Condition | Escalate To |
|-----------|-------------|
| TCSS power blocking S0ix | FV-PM-SOUTH |
| USB-specific issue in TCSS | FV-USB |
| Cross-domain failure (TCSS + other) | FV_Debugger_V1 |
| Hardware-level debug needed | TTK3 agents |
| BIOS configuration issue | BIOS team + UART-MONITOR |
| New RTL bug suspected | Silicon debug team + file HSDES |

### Escalation Information Required

When escalating, provide:
- [ ] Platform and stepping
- [ ] TCSS component (USB4/TBT/IOM/DP/DMA)
- [ ] Failure symptom and frequency
- [ ] Debug logs collected
- [ ] Reproduction steps
- [ ] Known-good configuration (if available)
- [ ] HSDES search results (if any)

## Root Cause Analysis Template

```
HSDES ID: <sighting_id>
Platform: <platform_stepping>
Component: <tcss_component>
Symptom: <failure_description>

Reproduction Steps:
1. <step_1>
2. <step_2>
...

Debug Data:
- <log_files>
- <register_dumps>
- <traces>

Root Cause:
<analysis>

Workaround:
<workaround_if_available>

Fix:
<permanent_fix_if_available>
```

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — Register definitions for debug
- **HSDES:** Intel Hardware Sighting Database
- **Confluence:** FVCommon wiki, TCSS validation pages

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
