# TCSS Validation Cheat Sheet

## Quick Command Reference

### Linux Commands

#### Device Enumeration
```bash
# List Thunderbolt devices
lspci | grep -i thunderbolt

# USB4 device tree
tree /sys/bus/thunderbolt/devices/

# Type-C port status
ls /sys/class/typec/port*/
cat /sys/class/typec/port0/data_role
```

#### Link Status
```bash
# Thunderbolt link speed
cat /sys/bus/thunderbolt/devices/0-0/link_speed

# USB4 router info
cat /sys/bus/thunderbolt/devices/0-0/device_name
```

#### Power Management
```bash
# Runtime PM status
cat /sys/bus/pci/devices/0000:*/power/runtime_status

# Enable runtime PM
echo auto > /sys/bus/pci/devices/0000:*/power/control

# S0ix residency
cat /sys/kernel/debug/pmc_core/slp_s0_residency_usec
```

#### Debug Logs
```bash
# Kernel messages
dmesg | grep -i "thunderbolt\|usb4\|typec"

# Thunderbolt events
journalctl -k | grep -i thunderbolt
```

---

### Windows Commands

#### Device Enumeration
```powershell
# Thunderbolt devices
Get-PnpDevice -FriendlyName *Thunderbolt*

# USB4 devices
Get-PnpDevice -Class USB4
```

#### Power Management
```powershell
# Device power state
powercfg /devicequery wake_armed

# Sleep study
powercfg /sleepstudy

# Power requests
powercfg /requests
```

#### Debug Logs
```powershell
# Thunderbolt event log
Get-WinEvent -LogName "Microsoft-Windows-Thunderbolt/Operational"

# Export events
Get-WinEvent -LogName "Microsoft-Windows-Thunderbolt/Operational" | Export-Csv tcss_events.csv
```

---

### PythonSV Quick Access

#### TCSS Controller
```python
# Device ID check
tcss = getattr(target, "tcss")
did = tcss.cfg.device_id.read()
vid = tcss.cfg.vendor_id.read()
print(f"DID:VID = 0x{did:04X}:0x{vid:04X}")
```

#### IOM Registers
```python
# Port configuration
iom = getattr(target, "iom")
port0_cfg = iom.port0.config.read()
port0_sts = iom.port0.status.read()
print(f"Port0 Config: 0x{port0_cfg:08X}")
print(f"Port0 Status: 0x{port0_sts:08X}")
```

#### Power Status
```python
# Power state
pwr = getattr(target, "tcss_power")
state = pwr.status.read()
print(f"Power State: 0x{state:08X}")
```

---

## Register Quick Reference

> **CRITICAL:** Always verify against platform HAS. This is example format only.

| Register | Offset | Key Bits | Description |
|----------|--------|----------|-------------|
| IOM_PORT_CONFIG | Query HAS | [2:0] Mode | Port mode (USB/DP/TBT) |
| IOM_PORT_STATUS | Query HAS | [0] Connected | Port connection status |
| IOM_MUX_STATE | Query HAS | [1:0] State | Mux state (Safe/USB/DP/TBT) |
| TCSS_PWR_CTRL | Query HAS | [1:0] D-State | D0/D1/D2/D3 |
| TCSS_WAKE_EN | Query HAS | [0] Enable | Wake-on-connect enable |

---

## Common Debug Sequences

### Check TCSS Enumeration
```bash
# Linux
lspci | grep -i thunderbolt
lspci -vvv -s <BDF>

# Windows
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*Thunderbolt*"}
```

### Check Port Connection
```bash
# Linux
cat /sys/class/typec/port0/data_role
cat /sys/class/typec/port0/orientation

# PythonSV
iom.port0.status.read()
```

### Force D0 (Disable Runtime PM)
```bash
# Linux
echo on > /sys/bus/pci/devices/0000:*/power/control

# Windows
powercfg /devicedisablewake "<device_name>"
```

### Collect Debug Bundle
```bash
# Linux
dmesg > dmesg.log
lspci -vvv > lspci.log
tree /sys/bus/thunderbolt/devices/ > tbt_tree.txt
tree /sys/class/typec/ > typec_tree.txt
cat /sys/kernel/debug/pmc_core/slp_s0_residency_usec > s0ix.log

# Windows
Get-WinEvent -LogName "Microsoft-Windows-Thunderbolt/Operational" | Export-Csv tbt_events.csv
powercfg /sleepstudy /output sleepstudy.html
```

---

## Test Execution Quick Start

> **TODO:** Add test execution commands once test framework is established.

---

## Co-Design HAS Query Examples

### Via Browser
1. Navigate to `https://chat.co-design.intel.com/chat`
2. Type: `"Show IOM register map from NVL_TCSS_HAS"`
3. Wait for response

### Common Queries
- `"What is the TCSS Device ID for MTL?"`
- `"Show USB4 router registers from NVL_iTBT80G_HAS"`
- `"What are the IOM power management registers?"`
- `"List DisplayPort Alt Mode configuration registers"`

---

## Useful Links

- **Co-Design:** https://chat.co-design.intel.com/chat
- **HSDES:** https://hsdes.intel.com/
- **Confluence FVCommon:** (Internal link - add when available)
- **NGA:** (Internal link - add when available)

---

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
- **Last Updated:** 2026-03-30
