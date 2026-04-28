---
name: fv-gbe/failure-analysis
description: >-
  Analyze GbE-related failures from NGA test results — failure patterns, bucket classification,
  log analysis, sighting correlation, and triage workflows for Intel I219 and I226/I225.
disable: false
---

# GbE Failure Analysis

> **Purpose**: Systematic analysis of GbE test failures from NGA test execution.
> Load this skill when triaging failed NGA GbE tests, analyzing failure buckets,
> or correlating failures with HSDES sightings.

---

## Overview

GbE failures can manifest across enumeration, PHY link, traffic data path, power management, and driver layers. This skill helps you:

1. Identify GbE-related test failures in NGA
2. Extract and analyze relevant logs
3. Classify failure types by subsystem
4. Cross-reference with known sightings (HSDES)
5. Recommend next debug steps

---

## NGA Test Name Patterns for GbE

When filtering NGA results, use these keywords:

```python
GBE_TEST_KEYWORDS = [
    'gbe', 'lan', 'ethernet', 'network',
    'i219', 'i226', 'i225',
    'e1000e', 'igc',
    'wol', 'wake_on_lan', 'wakeonlan',
    'traffic', 'iperf', 'throughput', 'ping',
    'link', 'autoneg', 'sgmii', 'phy',
    'gbe_power', 'gbe_d3', 'gbe_pm',
    'eee', 'energy_efficient',
    'loopback', 'self_test',
]
```

---

## NGA Failure Bucket Classification

NGA classifies failures into buckets. Here's how to interpret them for GbE:

### Bucket Types

| Bucket | Meaning | GbE Example |
|--------|---------|-------------|
| **INFRA** | Test infrastructure issue, not GbE bug | NIC cable unplugged, switch down, station misconfigured |
| **PRODUCT** | Real GbE hardware/firmware/driver bug | Link flapping, WoL failure, throughput regression |
| **TEST** | Test script bug or flaky test logic | Wrong expected value, race condition in test |

### How to Identify Bucket

```python
# Query NGA failure bucket
# Load /skill nga/failure for full API

# Example: Get failure bucket for a test run
failure = nga_api.get_failure(test_run_id)
bucket = failure['bucket']  # INFRA, PRODUCT, or TEST

if bucket == 'INFRA':
    # Check station health, cable, switch
    pass
elif bucket == 'PRODUCT':
    # Real bug — file sighting or search for existing one
    pass
elif bucket == 'TEST':
    # Test script issue — fix test or exclude
    pass
```

---

## GbE Failure Patterns

### Enumeration Failures

**Common patterns in logs:**
```python
ENUM_PATTERNS = [
    r'No network adapter found',
    r'Device not found',
    r'lspci.*00:1f\.6.*not found',
    r'PCI.*enumeration.*failed',
    r'VID.*0xFFFF',                 # Device disabled in BIOS
    r'BAR.*not allocated',
    r'Device Manager.*Error',
]
```

**Typical failure modes:**
- **Device disabled** — BIOS knob `LanEnable` = 0
- **BAR not allocated** — PCI resource conflict
- **Wrong DID** — Platform mismatch or stepping issue

**Triage steps:**
1. Check BIOS knob: `LanEnable = 1`?
2. Check lspci / Device Manager for device presence
3. Read VID/DID via PythonSV: `sv.socket0.pcieB0D31F6.vid.read()`
4. If VID = 0xFFFF → device disabled or PCIe link down

---

### Link Failures

**Common patterns in logs:**
```python
LINK_PATTERNS = [
    r'Link.*down',
    r'Link.*not.*up',
    r'No link detected',
    r'SGMII.*training.*failed',
    r'PHY.*not responding',
    r'autoneg.*failed',
    r'Speed.*negotiation.*failed',
    r'ethtool.*Link detected: no',
    r'STATUS\.LU.*0',               # Link Up bit = 0
]
```

**Typical failure modes:**
- **Cable/switch issue** — INFRA bucket, check physical connection
- **PHY reset stuck** — PHY initialization failed
- **SGMII training failure** — MAC-PHY interface issue
- **Autoneg mismatch** — Speed/duplex negotiation failed

**Triage steps:**
1. Check physical cable and switch port
2. Read STATUS register: `itp.mem.read(bar0 + 0x0008, 4)` — check LU bit [1]
3. Read PHY status via MDIC: `/skill fv-gbe/registers`
4. Try different speed: `ethtool -s eth0 speed 100 duplex full`

---

### Traffic Failures

**Common patterns in logs:**
```python
TRAFFIC_PATTERNS = [
    r'Throughput below threshold',
    r'iperf.*error',
    r'ping.*100% packet loss',
    r'ping.*timeout',
    r'TCP.*connection.*refused',
    r'UDP.*no response',
    r'TX.*timeout',
    r'RX.*buffer.*overflow',
    r'DMA.*error',
    r'CRCERRS.*[1-9]',              # CRC errors > 0
]
```

**Typical failure modes:**
- **IP config wrong** — INFRA bucket, check IP address/gateway
- **Remote server down** — INFRA bucket, check iperf server
- **Offload disabled** — TSO/LRO off, poor throughput
- **Ring buffer too small** — Packet drops under load
- **CRC errors** — Cable or PHY integrity issue

**Triage steps:**
1. Check IP config: `ip addr show` / `ipconfig`
2. Ping gateway first before iperf
3. Check offloads: `ethtool -k eth0`
4. Check statistics: `ethtool -S eth0` for errors
5. Check CRC errors in MMIO: `itp.mem.read(bar0 + 0x4000, 4)`

---

### Power Management Failures

**Common patterns in logs:**
```python
POWER_PATTERNS = [
    r'WoL.*failed',
    r'Wake.*on.*LAN.*not.*working',
    r'System did not wake',
    r'Magic packet.*not received',
    r'D3.*entry.*failed',
    r'D3.*exit.*failed',
    r'PME.*not.*set',
    r'S0ix.*blocked.*GbE',
    r'LTR.*0x0000',                 # LTR not programmed
    r'EEE.*negotiation.*failed',
]
```

**Typical failure modes:**
- **WoL disabled** — BIOS knob or driver config
- **PME not enabled** — Driver didn't arm PME
- **LTR not programmed** — Blocks S0ix
- **D3 transition failed** — Power sequencing issue

**Triage steps:**
1. Check BIOS WoL knobs: `GbeLanPme = 1`, `WakeOnLAN = 1`
2. Check driver WoL config: `ethtool eth0 | grep Wake`
3. Check LTR: `sv.socket0.pcieB0D31F6.ltr_max_snoop_lat.read()`
4. Check PMCSR: power state should be D0 or D3 as expected

---

### Driver Failures

**Common patterns in logs:**
```python
DRIVER_PATTERNS = [
    r'e1000e.*error',
    r'e1000e.*failed',
    r'igc.*error',
    r'Driver.*not.*loaded',
    r'Module.*not.*found',
    r'INF.*not.*found',
    r'Device ID.*not supported',
    r'PnP.*error',
    r'Code 10',                     # Windows driver error
    r'Code 28',                     # Windows no driver
]
```

**Typical failure modes:**
- **Wrong driver version** — DID not in INF/module
- **Driver crash** — Bug in driver initialization
- **Missing driver** — Driver not installed
- **Signature issue** — Windows driver not signed

**Triage steps:**
1. Check driver loaded: `lspci -s 00:1f.6 -vvv | grep driver`
2. Check dmesg/Event Viewer for driver errors
3. Verify DID is in driver INF/PCI ID table
4. Try reinstalling driver

---

## Failure Analysis Workflow

### Step 1: Get Failure Details from NGA

```python
# Load NGA skills
# /skill nga/results
# /skill nga/failure

# Query test run
test_run_id = "abc123"
result = nga_api.get_test_result(test_run_id)
print(f"Status: {result['status']}")
print(f"Exit Code: {result['exit_code']}")
print(f"Message: {result['message']}")

# Get failure bucket
failure = nga_api.get_failure(test_run_id)
print(f"Bucket: {failure['bucket']}")
print(f"Sighting: {failure.get('sighting_id', 'None')}")
```

### Step 2: Classify Failure Type

```python
# Match failure message against patterns
message = result['message']

if any(re.search(p, message, re.I) for p in ENUM_PATTERNS):
    failure_type = "ENUMERATION"
    load_skill = "/skill fv-gbe/enumeration"
elif any(re.search(p, message, re.I) for p in LINK_PATTERNS):
    failure_type = "LINK"
    load_skill = "/skill fv-gbe/phy-bringup"
elif any(re.search(p, message, re.I) for p in TRAFFIC_PATTERNS):
    failure_type = "TRAFFIC"
    load_skill = "/skill fv-gbe/traffic"
elif any(re.search(p, message, re.I) for p in POWER_PATTERNS):
    failure_type = "POWER"
    load_skill = "/skill fv-gbe/power"
elif any(re.search(p, message, re.I) for p in DRIVER_PATTERNS):
    failure_type = "DRIVER"
    load_skill = "/skill fv-gbe/driver"
else:
    failure_type = "UNKNOWN"
    load_skill = "/skill fv-gbe/debug"

print(f"Failure Type: {failure_type}")
print(f"Recommended: {load_skill}")
```

### Step 3: Check for Existing Sighting

```python
# Load HSDES skill: /skill hsdes

# Search for existing sighting
search_terms = [
    f"I219 {failure_type.lower()}",
    f"GbE {message[:50]}",
    f"e1000e {failure_type.lower()}",
]

for term in search_terms:
    sightings = hsdes_api.search(tenant="sighting", query=term)
    if sightings:
        print(f"Found existing sighting: {sightings[0]['id']}")
        break
```

### Step 4: Collect Debug Data

```python
# If no existing sighting, collect debug data
# See /skill fv-gbe/debug for full bundle collection scripts

# Quick data collection:
debug_data = {
    "platform": result.get('platform'),
    "bios_version": get_bios_version(),
    "driver_version": get_driver_version(),
    "failure_message": message,
    "logs": collect_logs(),
}
```

### Step 5: File or Link Sighting

```python
# If existing sighting found:
#   Link failure to sighting in NGA

# If no existing sighting:
#   File new HSDES sighting with debug data
#   Include: platform, BIOS, driver version, logs, repro steps
```

---

## Common NGA GbE Failure Signatures

| NGA Failure Message | Likely Cause | Bucket | Action |
|--------------------|--------------|--------|--------|
| `No network adapter found` | Device not enumerated | INFRA/PRODUCT | Check BIOS, enumeration |
| `Link did not come up within timeout` | PHY/cable issue | INFRA/PRODUCT | Check cable, PHY |
| `iperf3: error - unable to connect` | Network config | INFRA | Check IP, firewall, server |
| `Throughput below threshold` | Offload/config | TEST/PRODUCT | Check TSO/RSS, ring buffers |
| `WoL: system did not wake` | WoL not armed | PRODUCT | Check BIOS/driver WoL |
| `ethtool self-test FAIL` | HW/PHY failure | PRODUCT | Check registers, file sighting |
| `ModuleNotFoundError: e1000e` | Driver missing | INFRA | Install driver |
| `ping: 100% packet loss` | Link/IP issue | INFRA | Check link, IP config |
| `Code 10: device cannot start` | Driver init failed | PRODUCT | Check driver version, DID |

---

## Sighting Correlation

### Known GbE Sighting Categories

Search HSDES with these patterns:

| Search Pattern | Category |
|---------------|----------|
| `I219 link down after S3` | Power/resume |
| `e1000e driver crash` | Driver stability |
| `GbE WoL not working` | Wake-on-LAN |
| `SGMII training failure` | PHY bring-up |
| `I226 2.5G autoneg` | I226 speed negotiation |
| `GbE throughput regression` | Performance |
| `GbE D3 entry failure` | Power management |
| `LAN power sequencing` | Platform bring-up |

### HSDES Query Example

```python
# /skill hsdes

# Query sightings for GbE link issues
query = {
    "tenant": "sighting",
    "product": "Client Platform Validation",
    "component": "GbE",
    "status": "open",
    "keyword": "link down"
}
results = hsdes_api.search(**query)
```

---

## Log Analysis Guide

### Windows Logs to Check

| Log | Location | What to Look For |
|-----|----------|------------------|
| Event Viewer - System | Event Viewer | e1d68 or e2f68 errors |
| Device Manager | devmgmt.msc | Device status, error codes |
| Network Adapter Stats | `Get-NetAdapterStatistics` | Packet errors |
| Driver Traces | `netsh trace` | Detailed driver activity |

### Linux Logs to Check

| Log | Command | What to Look For |
|-----|---------|------------------|
| dmesg | `dmesg \| grep -i e1000e` | Driver init, errors |
| journalctl | `journalctl -k --since "1 hour ago"` | Kernel messages |
| ethtool stats | `ethtool -S eth0` | Packet errors, drops |
| sysfs | `cat /sys/class/net/eth0/statistics/*` | Interface stats |

### Key Error Strings

```python
# High-priority error strings to grep for
ERROR_STRINGS = [
    "e1000e: .* error",
    "e1000e: .* failed",
    "e1000e: .* timeout",
    "igc: .* error",
    "PCIe Bus Error",
    "link state changed.*down",
    "tx_timeout",
    "rx_fifo_errors",
    "crc_errors",
]
```

---

## Quick Reference: Failure → Action

| Symptom | Check First | Load Skill |
|---------|-------------|------------|
| Device not found | BIOS `LanEnable` | `/skill fv-gbe/enumeration` |
| Link down | Cable, switch, PHY | `/skill fv-gbe/phy-bringup` |
| Low throughput | Offloads, ring buffers | `/skill fv-gbe/traffic` |
| WoL not working | BIOS/driver WoL config | `/skill fv-gbe/power` |
| Driver not loading | DID in INF, dmesg | `/skill fv-gbe/driver` |
| Register read error | BAR allocation | `/skill fv-gbe/registers` |
| Any GbE failure | Collect bundle | `/skill fv-gbe/debug` |
