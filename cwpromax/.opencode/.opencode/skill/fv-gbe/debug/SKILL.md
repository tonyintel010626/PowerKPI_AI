---
name: fv-gbe/debug
description: "GbE failure triage, debug bundle collection, HSDES sighting lookup, NGA failure analysis, known errata, and debug workflows for Intel I219 and I226/I225."
disable: false
---

# Skill: fv-gbe/debug

## Overview

This skill provides systematic debug workflows for GbE failures on Intel Client SoC platforms. It covers failure classification, debug data collection, HSDES sighting lookup, NGA failure bucket analysis, known errata, and platform-specific debug notes.

---

## Failure Triage Decision Tree

```
GbE Failure
├── Device not enumerated
│     └── → /skill fv-gbe/enumeration
│           Check BIOS knob LanEnable, lspci, Device Manager
│
├── Device enumerated but link down
│     └── → /skill fv-gbe/phy-bringup
│           Check PHY reset, SGMII training, cable, switch config
│
├── Link up but no traffic / poor throughput
│     └── → /skill fv-gbe/traffic
│           Check offloads, ring buffers, TSO, RSS config
│
├── Wake-on-LAN failure
│     └── → /skill fv-gbe/power
│           Check BIOS WoL knobs, driver WoL config, magic packet
│
├── Driver not loading
│     └── → /skill fv-gbe/driver
│           Check Device ID in INF, dmesg errors, module probe
│
├── Register readback error
│     └── → /skill fv-gbe/registers
│           Check BAR0 allocation, PythonSV MMIO access
│
└── NGA test failure
      └── Query NGA → /skill nga/results, /skill nga/failure
            Identify bucket, check HSDES sightings → /skill hsdes
```

---

## Debug Bundle Collection

### Windows Debug Bundle

Collect the following data for any GbE failure:

```powershell
# 1. Device enumeration info
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*Ethernet*" } | FL > gbe_device.txt

# 2. Driver info
Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceName -like "*I219*" -or $_.DeviceName -like "*I226*" } | Select-Object DeviceName, DriverVersion, DriverDate | FL >> gbe_driver.txt

# 3. Adapter config and stats
Get-NetAdapter | FL > gbe_adapter.txt
Get-NetAdapterStatistics | FL >> gbe_adapter.txt
Get-NetAdapterAdvancedProperty -Name "Ethernet" >> gbe_adapter.txt

# 4. Link state and speed
Get-NetAdapter | Select-Object Name, Status, LinkSpeed, MediaType >> gbe_adapter.txt

# 5. IP configuration
ipconfig /all > gbe_ipconfig.txt

# 6. Event log
Get-EventLog -LogName System -Newest 100 | Where-Object { $_.Source -like "*e1d68*" -or $_.Source -like "*e2f68*" } | FL > gbe_events.txt

# 7. Ping test to default gateway
ping (Get-NetRoute -DestinationPrefix "0.0.0.0/0").NextHop -n 20 > gbe_ping.txt

# Bundle all
Compress-Archive -Path gbe_*.txt -DestinationPath gbe_debug_bundle.zip
Write-Host "Bundle: gbe_debug_bundle.zip"
```

### Linux Debug Bundle

```bash
#!/bin/bash
OUT=gbe_debug_$(date +%Y%m%d_%H%M%S)
mkdir -p $OUT

# Device enumeration
lspci -d 8086: -vvv > $OUT/lspci.txt 2>&1

# Driver info
ethtool -i eth0 > $OUT/ethtool_info.txt 2>&1
ethtool eth0 >> $OUT/ethtool_info.txt 2>&1
ethtool -S eth0 > $OUT/ethtool_stats.txt 2>&1
ethtool -k eth0 > $OUT/ethtool_offloads.txt 2>&1
ethtool -c eth0 > $OUT/ethtool_coalesce.txt 2>&1
ethtool --show-eee eth0 > $OUT/ethtool_eee.txt 2>&1

# System logs
dmesg | grep -i "e1000e\|igc\|0000:00:1f" > $OUT/dmesg_gbe.txt
journalctl -k --since "1 hour ago" > $OUT/journal_kernel.txt

# Network state
ip addr show > $OUT/ip_addr.txt
ip link show > $OUT/ip_link.txt
ip route show > $OUT/ip_route.txt

# Power state
cat /sys/bus/pci/devices/0000:00:1f.6/power_state > $OUT/power_state.txt
cat /sys/bus/pci/devices/0000:00:1f.6/power/control >> $OUT/power_state.txt

# Ping test
ping -c 20 $(ip route | grep default | awk '{print $3}') > $OUT/ping.txt 2>&1

# Bundle
tar czf ${OUT}.tar.gz $OUT/
echo "Bundle: ${OUT}.tar.gz"
```

---

## HSDES Sighting Lookup

Use the HSDES skill to search for known GbE issues.

### Search Patterns

```
# Common search terms for GbE sightings:
- "I219 link down"
- "e1000e driver crash"
- "GbE WoL not working"
- "SGMII training failure"
- "CNPi enumeration failed"
- "I226 2.5G autoneg"
- "GbE D3 entry failure"
- "LAN power sequencing"
```

Load `/skill hsdes` and search with:
- **Tenant:** `sighting`
- **Product:** `Client Platform Validation`
- **Component:** `GbE` or `LAN` or `CNPi`
- **Keywords:** From list above

---

## NGA Failure Analysis

### Querying GbE Test Failures

Load `/skill nga/results` and `/skill nga/failure` for:

1. **Find recent GbE test failures:**
   ```
   Suite name contains: GbE, LAN, Ethernet
   Status: Failed
   Platform: [target platform]
   ```

2. **Check failure buckets:**
   - `INFRA` — Infrastructure/station issue, not a GbE bug
   - `PRODUCT` — Real GbE hardware/firmware/driver bug
   - `TEST` — Test script issue

3. **Look for sighting links** in failure records — these point to HSDES entries.

### Common NGA GbE Failure Signatures

| Failure Message | Likely Cause | Action |
|----------------|-------------|--------|
| `No network adapter found` | Device not enumerated, BIOS knob | Check enumeration, BIOS |
| `Link did not come up within timeout` | PHY issue, cable, switch | Check phy-bringup skill |
| `iperf3: error - unable to connect` | IP config, firewall, remote server down | Check IP, ping first |
| `Throughput below threshold` | Offload disabled, congestion | Check TSO/LRO, ring buffers |
| `WoL: system did not wake` | BIOS knob, driver config | Check power skill |
| `ethtool self-test FAIL` | Hardware/PHY failure | Check registers, HSDES |
| `ModuleNotFoundError: e1000e` | Missing driver module | Install driver, check kernel |

---

## Known Errata and Workarounds

### I219 — SGMII Link Loss After S3 Resume
**Symptom:** Link doesn't come back after S3 resume in some conditions.
**Workaround:** Driver issues PHY reset during resume. If issue persists, check PCH LAN power sequencing in BSP.
**HSDES:** Search "I219 link down after S3"

### I219 — Incorrect Statistics After Reset
**Symptom:** Statistics registers (GPRC, GPTC etc.) show stale values after MAC reset.
**Workaround:** Statistics are cleared on reset — accumulate after driver fully initializes.

### I226 — 2.5G Link Not Established With Some Switches
**Symptom:** I226 shows 1G link with switches that advertise 2.5G.
**Root Cause:** Some switch firmware has NBASE-T autoneg interoperability issues.
**Workaround:** Force 2.5G: `ethtool -s eth0 speed 2500 duplex full autoneg off`

### I219 — WoL Disabled By OS on Shutdown
**Symptom:** WoL from S5 doesn't work even with driver config correct.
**Root Cause:** Some OS builds disable PME on shutdown by default.
**Workaround (Linux):** 
```bash
# In /etc/systemd/system/wol.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/ethtool -s eth0 wol g
```

### I219 — LTR Not Programmed Correctly
**Symptom:** Platform fails to enter deep S0ix because GbE LTR is 0.
**Root Cause:** Driver LTR initialization skipped under certain conditions.
**Debug:** Check `sv.socket0.pcieB0D31F6.ltr_max_snoop_lat.read()` — should be non-zero.

---

## Platform-Specific Debug Notes

### NVL (Novalake)
- I219 Device IDs not yet finalized — verify against latest HAS
- Named node path for PythonSV: TBD (check with platform team)
- New LAN power domain — verify power sequencing in BSP

### PTL (Panther Lake)
- I219 Device IDs TBD — update when assigned
- Check PCH stepping for any GbE errata

### LNL (Lunar Lake)
- I219-LM: 0x7F0C, I219-V: 0x7F0D
- Integrated into SoC (not discrete PCH chip)
- Power domain: PCH GbE power well — verify enabled in BSP

### MTL (Meteor Lake)
- I219-LM: 0x550A, I219-V: 0x550B
- Well-characterized platform — most errata documented in HSDES

### ARL (Arrow Lake)
- I219-LM: 0xA80D, I219-V: 0xA80E
- Check ARL PCH errata for any LAN-related items

---

## Debug Escalation Criteria

Escalate to GbE IP team when:
- MMIO register reads return 0xFFFFFFFF (PCIe link error)
- PHY ID reads via MDIC return garbage values
- Link flapping with no cable/switch changes
- Any register stuck at unexpected value after multiple resets
- NVM/OTP read errors (EECD/EEMNGCTL)

When escalating, attach:
1. Full debug bundle (above)
2. PythonSV register dump
3. HSDES sighting if applicable
4. Platform IFWI version and BSP version
