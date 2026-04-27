---
name: fv-gbe/phy-bringup
description: "GbE PHY bring-up, link negotiation, autoneg, speed/duplex configuration, and SGMII interface validation for Intel I219 and I226/I225 controllers."
disable: false
---

# Skill: fv-gbe/phy-bringup

## Overview

This skill covers PHY bring-up and link management for Intel GbE controllers. The I219 uses an external PHY connected via SGMII to the internal MAC. The I226/I225 have the PHY integrated. Both require proper initialization before link can be established.

---

## I219 PHY Architecture

```
[ CPU/SoC ]
    |
[ PCH GbE MAC ] ←→ SGMII ←→ [ External PHY ] ←→ [ RJ-45 Port ]
    |                              |
  BAR0 MMIO                   PHY Registers
  (host access)               (via MDI/MDIO)
```

- MAC resides in PCH at `00:1F.6`
- PHY is accessed indirectly via MAC MDI registers (`MDIC` register)
- PHY address is typically 1 (platform-dependent)
- SGMII link must be established between MAC and PHY before Ethernet link

---

## I226 / I225 PHY Architecture

- PHY is integrated inside the I226/I225 package
- MAC and PHY communicate internally
- Host accesses PHY via PCIe MMIO registers

---

## Link Bring-Up Sequence (I219)

### Step 1: Verify Hardware Power
- Check 3.3V LAN power rail is present
- Check PHY reset pin (PERST# or LAN_RESET#) de-asserted

### Step 2: Driver Initialization
The driver performs these steps automatically:
1. Reset MAC (CTRL.RST bit)
2. Load NVM defaults
3. Configure autoneg (CTRL.ASDE + CTRL.SLU)
4. Reset PHY via CTRL.PHY_RST
5. Wait for PHY ready (EEMNGCTL.CFG_DONE)
6. Enable link (CTRL.SLU = 1)

### Step 3: Autonegotiation
Default autoneg advertises:
- 1000BASE-T Full Duplex
- 100BASE-TX Full/Half Duplex
- 10BASE-T Full/Half Duplex

Autoneg completion: `STATUS.LU` bit = 1

### Step 4: Verify Link
```
STATUS register (offset 0x0008):
  Bits [1:0] = Speed: 00=10M, 01=100M, 10=1000M
  Bit  [0]   = Link Up (LU)
  Bit  [1]   = Full Duplex (FD)
```

---

## Checking Link Status

### Windows

```powershell
# Get adapter info
Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*Intel*Ethernet*" } | Select-Object Name, Status, LinkSpeed, MediaType

# Detailed adapter statistics
Get-NetAdapterStatistics -Name "Ethernet"

# Check link speed specifically
(Get-NetAdapter -Name "Ethernet").LinkSpeed
# Expected: "1 Gbps" for I219, "2.5 Gbps" for I226
```

### Linux

```bash
# Check link state and speed
ethtool eth0          # Replace eth0 with actual interface name
ip link show eth0

# Expected ethtool output when link is up:
# Speed: 1000Mb/s (I219) or 2500Mb/s (I226)
# Duplex: Full
# Link detected: yes

# Show autoneg advertisement
ethtool -A eth0
ethtool --show-pause eth0
```

### PythonSV (Register Check)

```python
# Check STATUS register (offset 0x0008 in MMIO space)
# Requires BAR0 base address from enumeration
base = sv.socket0.pcieB0D31F6.bar0.read() & 0xFFFFFFF0
status = sv.mem.read(base + 0x0008, 4)
link_up    = (status >> 1) & 1   # LU bit
speed      = (status >> 6) & 3   # SPEED bits [7:6]
full_duplex = (status >> 0) & 1  # FD bit

print(f"Link Up: {link_up}")
print(f"Speed: {['10M','100M','1000M','reserved'][speed]}")
print(f"Full Duplex: {full_duplex}")
```

---

## Common PHY/Link Issues

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Link stays down after boot | PHY not reset properly, SGMII not trained | Check CTRL.PHY_RST sequence; check SGMII training via STATUS.PHYRA |
| 100M only, won't autoneg to 1G | Cable is Cat5 (not Cat5e/6), or remote end forced to 100M | Use Cat5e+ cable; check switch port config |
| Link flapping | Noise on SGMII, bad cable/connector | Check signal integrity; replace cable |
| Link up but no traffic | IP configuration issue, firewall | Verify IP config; try ping with -S |
| PHY responds but SGMII not training | BIOS power sequencing issue | Check LAN power domain sequencing in BSP |
| I226 shows 1G instead of 2.5G | Switch doesn't support 2.5G NBASE-T | Connect to 2.5G-capable switch |

---

## Forcing Link Speed (Test Scenarios)

### Windows
```powershell
# Force 100M Full Duplex (for testing)
Set-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Speed & Duplex" -DisplayValue "100 Mbps Full Duplex"

# Restore Autoneg
Set-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Speed & Duplex" -DisplayValue "Auto Negotiation"
```

### Linux
```bash
# Force 100M Full Duplex
ethtool -s eth0 speed 100 duplex full autoneg off

# Restore autoneg
ethtool -s eth0 autoneg on
```

---

## SGMII Training (I219 MAC-to-PHY Interface)

The SGMII link between the PCH MAC and external PHY must train successfully before Ethernet link can come up.

**Key registers:**
- `CTRL_EXT.LINK_MODE [22:21]` — Interface mode (01b = SGMII)
- `STATUS.PHYRA` — PHY Reset Asserted (must be 0 for normal operation)
- `MDICNFG.PHY_ADDR` — PHY address on MDIO bus

**Check SGMII training status:**
```python
ctrl_ext = sv.mem.read(base + 0x0018, 4)
link_mode = (ctrl_ext >> 21) & 0x3
print(f"Link Mode: {link_mode:#b}")  # Should be 0b01 for SGMII
```

---

## Autonegotiation Troubleshooting Flow

```
Link down?
  ├─ Check PHY power → is LAN power rail present?
  │     No → Hardware/BIOS power sequencing issue
  │     Yes → Continue
  ├─ Check STATUS.PHYRA == 0?
  │     No (PHY in reset) → Driver not releasing PHY reset → check CTRL.PHY_RST
  │     Yes → Continue
  ├─ Check MDI access works?
  │     No → MDIO bus issue or wrong PHY address
  │     Yes → Continue
  ├─ Check PHY link partner detected?
  │     No → Cable problem or switch port down
  │     Yes → Autoneg failure → check advertisement registers
  └─ STATUS.LU == 1? → Link is UP
```

---

## Pre-Silicon / Simics Notes

- In Simics, the PHY model behavior may differ from real hardware.
- Use the Simics transactor to inject link-up events if PHY model is not full-featured.
- Autoneg may complete immediately in simulation without cable/partner simulation.
- SGMII training may be bypassed in some simulation models.
