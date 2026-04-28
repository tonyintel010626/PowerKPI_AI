---
name: fv-gbe
description: "Intel GbE (Gigabit Ethernet) functional validation — covers I219 (CNPi) and I226/I225 (2.5GbE) post-silicon and pre-silicon validation across Intel Client SoC platforms. Includes enumeration, PHY bring-up, traffic testing, power management, driver validation, register checkout, and debug triage."
disable: false
---

# Skill: fv-gbe

## Overview

This skill provides complete Intel GbE functional validation knowledge for both post-silicon and pre-silicon (Simics) environments. It covers the Intel I219 (CNPi) 1GbE controller and Intel I226/I225 2.5GbE controllers across all Intel Client SoC platforms: NVL, PTL, LNL, MTL, ARL.

## GbE IP Summary

| Controller | Speed | Interface | Integrated | Platforms |
|------------|-------|-----------|------------|-----------|
| Intel I219-LM / I219-V | 1 GbE | SGMII / PCIe-routed | MAC in SoC, PHY external | MTL, LNL, ARL, PTL, NVL |
| Intel I226-LM / I226-V | 2.5 GbE | PCIe Gen3 x1 | Discrete chip | Platform-dependent |
| Intel I225-LM / I225-V | 2.5 GbE | PCIe Gen3 x1 | Discrete chip | Older platforms |

### I219 Architecture (CNPi)
- MAC resides inside the PCH/SoC
- PHY is external, connected via SGMII
- PCI Device: Bus 0, Device 31, Function 6 (B:D:F = 00:1F.6) on most platforms
- Vendor ID: 0x8086, Device IDs vary per SKU (see registers sub-skill)
- Managed by host via Memory BAR (BAR0)

### I226 / I225 Architecture
- Fully discrete PCIe device
- Connected via PCIe Root Port
- Vendor ID: 0x8086
- Device IDs: I226-LM = 0x125B, I226-V = 0x125C, I225-LM = 0x15F2, I225-V = 0x15F3

## Available Sub-Skills

Load these sub-skills for detailed domain knowledge:

| Sub-Skill | Description | Load Command |
|-----------|-------------|--------------|
| `fv-gbe/platform` | **Per-platform config data**: DIDs, BDFs, PythonSV paths, BIOS knobs, quirks | `/skill fv-gbe/platform` |
| `fv-gbe/enumeration` | PCI enumeration, BDF assignment, BAR allocation, ACPI tables | `/skill fv-gbe/enumeration` |
| `fv-gbe/phy-bringup` | Link bring-up, PHY config, autoneg, speed/duplex negotiation | `/skill fv-gbe/phy-bringup` |
| `fv-gbe/traffic` | TX/RX data path, loopback, throughput, offload validation | `/skill fv-gbe/traffic` |
| `fv-gbe/power` | D-states, Wake-on-LAN, S0ix/S3/S4/S5 integration, LTR | `/skill fv-gbe/power` |
| `fv-gbe/driver` | Windows e1d68.sys / Linux igb/e1000e driver, INF/ko validation | `/skill fv-gbe/driver` |
| `fv-gbe/registers` | MMIO/PCI CSR map, register checkout via PythonSV | `/skill fv-gbe/registers` |
| `fv-gbe/debug` | Failure triage, HSDES sightings, debug bundle collection, known errata | `/skill fv-gbe/debug` |
| `fv-gbe/failure-analysis` | **NGA failure analysis**: failure patterns, bucket classification, log analysis | `/skill fv-gbe/failure-analysis` |
| `fv-gbe/simics` | **Pre-silicon validation**: Simics models, transactors, VP setup, SW-CI | `/skill fv-gbe/simics` |

## Platform Configuration Summary

### I219 BDF and Device IDs Per Platform

| Platform | BDF | Device ID (LM) | Device ID (V) |
|----------|-----|----------------|---------------|
| MTL | 00:1F.6 | 0x550A | 0x550B |
| LNL | 00:1F.6 | 0x7F0C | 0x7F0D |
| ARL | 00:1F.6 | 0xA80D | 0xA80E |
| PTL | 00:1F.6 | TBD | TBD |
| NVL | 00:1F.6 | TBD | TBD |

> Note: PTL/NVL Device IDs should be confirmed against the latest BIOS/HW spec. Update this table when IDs are assigned.

### BIOS Knobs (I219)

| BIOS Knob | Purpose | Recommended Setting |
|-----------|---------|---------------------|
| `LanEnable` | Enable/disable GbE controller | Enabled |
| `GbeLanPme` | Wake-on-LAN PME | Enabled (for WoL tests) |
| `WakeOnLAN` | WoL magic packet | Enabled (for WoL tests) |
| `PchLanPowerCycleDelay` | Power cycle delay | Default |

## Common Validation Scenarios

### Scenario: Basic Bring-Up Checklist
1. Verify device enumerated at expected BDF → `/skill fv-gbe/enumeration`
2. Check link is up at expected speed → `/skill fv-gbe/phy-bringup`
3. Send/receive traffic (ping + iperf) → `/skill fv-gbe/traffic`
4. Verify D0/D3 transitions → `/skill fv-gbe/power`

### Scenario: Failure Triage
1. Collect debug bundle → `/skill fv-gbe/debug`
2. Check HSDES for known sightings → `/skill hsdes`
3. Validate register state → `/skill fv-gbe/registers`

### Scenario: NGA Test Run Analysis
1. Load NGA skills → `/skill nga/results`, `/skill nga/failure`
2. Query test run results for GbE suite
3. Identify failing tests and bucket failures

## Integration with Other Skills

| Skill | When to Use |
|-------|-------------|
| `/skill nga/results` | Fetch NGA GbE test run results |
| `/skill nga/failure` | Analyze failure buckets, sighting links |
| `/skill nga/search` | OData search across GbE test entities |
| `/skill nga/suitereruns` | Schedule reruns for flaky GbE tests |
| `/skill hsdes` | Search HSDES for GbE sightings and bugs |
| `/skill pysv` | PythonSV register access on GbE MMIO |
| `/skill ttk3/power` | Platform power cycling for WoL tests |
