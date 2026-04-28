---
name: fv-gbe/power
description: "GbE power management validation — D-states, Wake-on-LAN (WoL), S0ix/S3/S4/S5 integration, EEE (Energy Efficient Ethernet), LTR, and PME for Intel I219 and I226/I225."
disable: false
---

# Skill: fv-gbe/power

## Overview

This skill covers GbE power management validation for Intel I219 and I226/I225. Key areas include PCI D-state transitions, Wake-on-LAN (WoL) via magic packet, Energy Efficient Ethernet (EEE), S0ix integration, and LTR (Latency Tolerance Reporting).

---

## PCI D-States

### I219 D-State Behavior

| System State | GbE D-State | Notes |
|-------------|-------------|-------|
| S0 Active | D0 | Normal operation |
| S0 Idle | D0i3 (driver-managed) | EEE active if EEE enabled |
| S0ix (Modern Standby) | D3cold or D0 | Depends on WoL config — see below |
| S3 (Sleep) | D3 | WoL arm required for wake |
| S4 (Hibernate) | D3 | WoL arm required for wake |
| S5 (Soft Off) | D3 | WoL arm required for wake |

### Verifying D-State (Windows)

```powershell
# Check current power state via WMI
Get-WmiObject -Namespace root\wmi -Class MSNdis_NetworkAdapterPowerState

# Check Device Manager power state
devcon.exe status "PCI\VEN_8086&DEV_550A*"
```

### Verifying D-State (Linux)

```bash
# Check runtime power state
cat /sys/bus/pci/devices/0000:00:1f.6/power/runtime_status
# Expected: "active" or "suspended"

# Check D-state from ACPI
cat /sys/bus/pci/devices/0000:00:1f.6/power_state
# Expected: "D0" or "D3cold"

# Check runtime PM enabled
cat /sys/bus/pci/devices/0000:00:1f.6/power/control
# Expected: "auto" (runtime PM enabled)
```

### PythonSV D-State Check

```python
# Check PMCSR register (PCI Standard Power Management Control/Status)
# Offset 0xCC in PCI config space (find via capability pointer)
pmcsr = sv.socket0.pcieB0D31F6.pmcsr.read()
power_state = pmcsr & 0x3
print(f"Power State: D{power_state}")
# 0=D0, 1=D1, 2=D2, 3=D3
```

---

## Wake-on-LAN (WoL)

### WoL Configuration

WoL allows the GbE controller to wake the system from S3/S4/S5 using a magic packet (6x FF + 16x MAC address).

#### Enable WoL (Windows)

```powershell
# Enable WoL in driver properties
Set-NetAdapterPowerManagement -Name "Ethernet" -WakeOnMagicPacket Enabled

# Verify WoL settings
Get-NetAdapterPowerManagement -Name "Ethernet"
# WakeOnMagicPacket should be: Enabled
```

#### Enable WoL (Linux)

```bash
# Check WoL support
ethtool eth0 | grep -i wake

# Enable magic packet WoL
ethtool -s eth0 wol g

# Verify
ethtool eth0 | grep "Wake-on"
# Wake-on: g = magic packet enabled
```

### BIOS WoL Configuration

Required BIOS knobs:
- `WakeOnLAN` = Enabled
- `GbeLanPme` = Enabled
- `ERP` (Energy Related Products) = Disabled (conflicts with WoL)

### WoL Testing Procedure

1. Enable WoL in OS driver (above)
2. Put system in S3/S4/S5
3. From another machine, send magic packet:
   ```bash
   # Linux — using wakeonlan tool
   wakeonlan <target-MAC-address>

   # Or using etherwake
   etherwake -b <target-MAC-address>

   # Python magic packet sender
   python3 -c "
   import socket, struct
   mac = 'AA:BB:CC:DD:EE:FF'.replace(':','')
   magic = bytes.fromhex('F'*12 + mac*16)
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
   s.sendto(magic, ('255.255.255.255', 9))
   "
   ```
4. Verify system wakes within 5 seconds

### WoL TTK3 Integration

Use TTK3 for automated WoL testing:
- Put system to S3/S4 via TTK3 GPIO or HID
- Send magic packet from a separate network
- Monitor POST codes via TTK3 to verify wake
- Load `/skill ttk3/power` for power control details

---

## Energy Efficient Ethernet (EEE)

EEE (IEEE 802.3az) allows GbE to enter a low-power idle state (LPI — Low Power Idle) when there is no data to transmit.

### EEE Validation (Linux)

```bash
# Check EEE support
ethtool --show-eee eth0

# Enable EEE
ethtool --set-eee eth0 eee on

# Verify link partner also supports EEE
ethtool --show-eee eth0 | grep "EEE active"
```

### EEE Validation (Windows)

```powershell
# Check EEE state
Get-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Energy Efficient Ethernet"

# Enable EEE
Set-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Energy Efficient Ethernet" -DisplayValue "Enabled"
```

### EEE Power Measurement

EEE should reduce power when GbE link is idle. Verify with platform power meter:
- Active traffic: ~0.5–0.8W (I219)
- Idle with EEE: ~0.1–0.2W

---

## S0ix (Modern Standby) Integration

In Modern Standby (S0ix), the GbE controller behavior depends on WoL requirements:

| WoL Needed | GbE in S0ix | Power Behavior |
|-----------|-------------|----------------|
| Yes | D0 (stays active) | Higher power — GbE maintains link to detect magic packet |
| No | D3cold | Lowest power — GbE powered off |

### Verifying S0ix GbE Power State

```powershell
# Windows — check if GbE participates in connected standby
powercfg /sleepstudy

# Check PME (Power Management Event) wake source
powercfg /wakereason
```

```bash
# Linux — check D3cold entry during s2idle
# Watch runtime PM during system idle
udevadm monitor --subsystem-match=power_supply &
echo mem > /sys/power/state   # Enter s2idle
# After wake: check if GbE went to D3cold
cat /sys/bus/pci/devices/0000:00:1f.6/power_state
```

---

## LTR (Latency Tolerance Reporting)

LTR allows the GbE device to report its latency tolerance to the PCIe Root Complex, enabling power-optimized interconnect states.

```python
# Check LTR capability in PCIe Extended Config Space
# LTR Capability is at offset found via extended cap pointer
# LTR Max Snoop Latency Register
ltr_max = sv.socket0.pcieB0D31F6.ltr_max_snoop_lat.read()
ltr_nosnoop = sv.socket0.pcieB0D31F6.ltr_max_nosnoop_lat.read()
print(f"LTR Max Snoop: {ltr_max:#010x}")
print(f"LTR Max No-Snoop: {ltr_nosnoop:#010x}")
```

LTR must be non-zero for proper platform low-power operation.

---

## Common Power Management Issues

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| WoL doesn't work from S5 | BIOS `GbeLanPme` disabled | Enable in BIOS setup |
| WoL works from S3 but not S4/S5 | OS doesn't arm WoL on hibernate/shutdown | Check driver WoL settings, OS power policy |
| System won't enter S0ix | GbE blocking S0ix entry | Check D3cold policy, disable WoL if not needed |
| EEE causes link drops | Link partner EEE timing mismatch | Disable EEE: `ethtool --set-eee eth0 eee off` |
| D3 entry fails | Driver not releasing device | Check driver unload sequence; look for "PCIe PME" errors in dmesg |
| WoL magic packet not received | Network address is off, broadcast not routed | Ensure magic packet sent to subnet broadcast |

---

## NGA Power Test Suites

Common NGA GbE power tests:
- `GbE_WoL_S3_MagicPacket` — WoL from S3
- `GbE_WoL_S4_MagicPacket` — WoL from S4 (hibernate)
- `GbE_WoL_S5_MagicPacket` — WoL from S5 (soft off)
- `GbE_D3_Entry_Exit` — D3 hot/cold transitions
- `GbE_EEE_Validation` — EEE enable/disable and link stability
- `GbE_S0ix_Integration` — S0ix with/without WoL armed

Load `/skill nga/results` to query test results.
