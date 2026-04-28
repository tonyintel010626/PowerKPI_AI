---
name: fv-storage
description: Storage subsystem validation for SATA, UFS, and Intel RST across Intel Client SoC platforms
version: "rev2.0"
---

# Storage Subsystem Validation Skill

## Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| **SATA HAS** | `.opencode/skill/fv-storage/docs/` | AHCI register maps, FIS protocol, DevSleep, ALPM |
| **UFS HAS** | `.opencode/skill/fv-storage/docs/` | UFSHCI registers, UIC commands, gear switching, power modes |
| **Intel RST BWG** | `.opencode/skill/fv-storage/docs/` | RAID configuration, Optane caching, OROM settings |
| **Platform Datasheet** | Co-Design knowledge base | PCI configuration, SKU variations, power domains |

---

## CRITICAL: Dynamic Data Warning

⚠️ **NEVER hard-code storage controller counts, port numbers, or register addresses from memory.**

Storage configurations vary significantly across:
- **Platform families** (MTL vs. LNL vs. PTL)
- **SKUs within same platform** (H/U/P variants)
- **BIOS settings** (AHCI vs. RAID mode, port enabling)
- **Stepping revisions** (A0 vs. B0 register changes)

**ALWAYS**:
1. Query Co-Design for platform-specific data
2. Read PCI config space to verify controller presence
3. Check HAS document for register offsets and bit fields
4. Validate against actual hardware state using PythonSV

---

## Safety Warnings

| Warning | Impact | Prevention |
|---------|--------|------------|
| **Accessing D3 controller** | Bus hang, platform freeze | Check D-state (PCI config 0x84) before register reads |
| **Incorrect mode assumption** | Wrong register map | Verify AHCI vs. RAID vs. IDE mode (PCI class code) |
| **Blind register writes** | Data corruption, drive damage | Always read-modify-write pattern |
| **Port count assumption** | Array out of bounds | Read HBA capabilities for actual port count |
| **Link speed mismatch** | Training failures | Check negotiated speed, don't force speed |
| **Power rail off** | Register reads return 0xFF | Verify power domain state before access |
| **UFS uninitialized** | Hung commands | Check controller ready bit before UIC commands |

---

## Mandatory HAS Lookup Workflow

Before performing any register operation:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Identify Platform + SKU + Stepping                  │
│    → User provides or query via PythonSV               │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Query Co-Design for Architecture                    │
│    → "What is the SATA controller config for [platform]?"│
│    → "Show UFS power domain hierarchy for [platform]"  │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Locate HAS Document in docs/                        │
│    → SATA HAS: Section X.Y for AHCI registers         │
│    → UFS HAS: Section X.Y for UFSHCI registers        │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Cross-Check Against Actual Hardware                 │
│    → Read PCI config: Bus/Dev/Func, BAR addresses     │
│    → Read controller capabilities register             │
│    → Verify port count, feature support                │
└─────────────────────────────────────────────────────────┘
```

**NEVER skip this workflow** — incorrect register addresses can corrupt storage data or hang the platform.

---

## Known HAS Documents

| Document | Platforms | Key Sections | Notes |
|----------|-----------|--------------|-------|
| **SATA 3.0 Controller HAS** (Rev 1.09, July 2024) | ADP-S, MTL-SOC-M/P, MTP-S, LNL-SOC-P, NVP-S | PCI Config (§10.1), AHCI Generic Regs (§10.3.1.1), Port DMA (§10.3.1.3), Port Interface (§10.3.1.4), Vendor Specific (§10.3.1.2), SIR (§10.3.2), Theory of Operation (§24), Microarchitecture (§25) | AHCI 1.3.1 + SATA 3.2 compliant. PDF + text dump in `docs/` |
| **UFS HAS (NVL)** | NVL (Rev 1.1.9.1, June 2025, 77pp) | Architecture, Address Map, MCQ (8 queues), AES-XTS Crypto, Power Flows A-H, IOSF-SB Messages, DFx/VISA, BIOS BWG | UFS 4.0 Gear 5, Synopsys UFSHC v4.0 + MIPI M-PHY v5.0, BDF=0:23.0, DevID=0xD335 |
| **UFS HAS (LNL/PTL/WCL)** | LNL, PTL, WCL (mobile) | UFSHCI Registers, UIC Commands, Power Management | UFS 3.1, BDF=0:12.7 |
| **Intel RST BWG** | Platforms with RST support | RAID Configuration (Ch. 2), Optane Caching (Ch. 4), OROM Settings (Ch. 6) | Legacy feature, check platform support |
| **Platform Datasheet** | Platform-specific | PCI Configuration (Ch. X), Storage Controllers (Ch. Y) | Per-SKU variations critical |
| **SATA HotPlug BKM** | All SATA platforms | Surprise Removal automation with Quarch QTL1461, BIOS settings, PxSSTS register checks | Wiki [Page ID: 2016451763], local BKM + script in `docs/` |

**Document Access**: Place PDF/DOCX files in `.opencode/skill/fv-storage/docs/` and use `@doc-study` skill to extract content.

---

## Architecture Overview

### Storage Controllers in Intel Client Platforms

#### SATA Controller (AHCI)
- **Protocol**: SATA III (6 Gbps), AHCI 1.3.1 compliant
- **Location**: PCH, typically Bus 0 Device 17 or 23
- **Ports**: 1-8 ports (SKU-dependent, check HAS)
- **Modes**: AHCI, RAID (Intel RST), IDE (legacy)
- **Key Features**:
  - Native Command Queuing (NCQ) - up to 32 commands
  - Hot-plug support per port
  - Staggered spin-up
  - DevSleep (SATA 3.3) - ultra-low power < 5mW
  - Aggressive Link Power Management (ALPM) - Partial/Slumber states
  - Port Multiplier support (platform-dependent)

**Key Registers** (relative to AHCI Base Address from PCI BAR5):
- `0x00`: HBA Capabilities (CAP) - port count, features
- `0x04`: Global HBA Control (GHC) - reset, interrupts
- `0x08`: Interrupt Status (IS) - per-port interrupt bits
- `0x0C`: Ports Implemented (PI) - which ports are present
- `0x100 + (port * 0x80)`: Port registers (PxCMD, PxSTAT, PxSIG, etc.)

⚠️ **Always read CAP.NP (port count) before iterating ports** — not all platforms implement all 32 possible ports.

#### UFS Controller (UFSHCI)
- **Protocol**: UFS 3.1/4.0, MIPI M-PHY HS-G1/G2/G3/G4/G5
- **Location**: PCH or SoC-integrated, varies by platform
- **Lanes**: Typically 2 lanes (check HAS for SKU variations)
- **Key Features**:
  - High-speed gears: HS-G4 (11.6 Gbps/lane), HS-G5 (23.2 Gbps/lane)
  - Multi-Circular Queue (MCQ) — 8 SQ/CQ pairs (NVL UFS 4.0+)
  - WriteBooster (UFS 3.1) - SLC cache for write acceleration
  - Host Performance Booster (HPB) - L2P mapping cache
  - DeepSleep (Hibernate) - power rail off, < 1mW
  - Runtime power management - multiple power modes
  - AES-XTS inline encryption (128/256-bit keys, 32 config slots) — NVL+
  - Secure erase, RPMB (Replay Protected Memory Block)

**Platform-Specific Notes**:
- **LNL/PTL/WCL**: UFS 3.1, BDF 0:12.7, single-queue (SQR mode)
- **NVL**: UFS 4.0, BDF 0:23.0, DeviceID=0xD335, MCQ (8 queues), Synopsys UFSHC v4.0 + MIPI M-PHY v5.0, UniPro v2.0, ~4.5 GB/s per direction (Gear 5), 32KB BAR (16KB used)

**Key Registers** (relative to UFS Base Address from PCI BAR):
- `0x00`: Host Capabilities (CAP) - lanes, queue depth, crypto
- `0x08`: UFS Version (VER) - 3.0/3.1/4.0
- `0x14`: Host Controller Status (HCS) - ready, errors
- `0x34`: Interrupt Enable (IE)
- `0x50`: UTP Transfer Request List Base Address
- `0x60`: UTP Task Management Request List Base Address
- `0x90+`: UIC Command registers (for DME layer access)

⚠️ **UFS requires initialization sequence** — check HCS.DP (Device Present) and HCS.UCRDY (UIC Ready) before issuing commands.

---

## Sub-Skills

This skill orchestrates **2 specialized sub-skills** for protocol-specific validation:

### 1. SATA/AHCI Validation (`fv-storage/sata`)
**Purpose**: Validate SATA controller enumeration, AHCI protocol compliance, port management, and power states.

**When to use**:
- SATA drive not detected
- AHCI mode vs. RAID mode issues
- DevSleep or ALPM validation
- NCQ (Native Command Queuing) testing
- Hot-plug event handling
- Intel RST RAID configuration

**Covers**:
- AHCI register map validation (HBA + Port registers)
- FIS (Frame Information Structure) protocol checks
- SATA link speed negotiation (Gen1/2/3)
- Power management: ALPM (Partial/Slumber), DevSleep
- Error handling: PHY errors, CRC errors, interface errors
- Intel RST mode detection and RAID volume validation

**Load with**: `@skill fv-storage/sata`

---

### 2. UFS Validation (`fv-storage/ufs`)
**Purpose**: Validate UFS controller enumeration, UFSHCI compliance, UIC layer commands, gear switching, and power modes.

**When to use**:
- UFS device not enumerated
- Gear speed issues (HS-G3/G4/G5)
- UFS power mode validation (Active/Sleep/DeepSleep)
- WriteBooster or HPB feature testing
- UIC command sequences (DME_GET, DME_SET)
- UFS boot configuration

**Covers**:
- UFSHCI register map validation
- UIC (UFS Interconnect) command layer
- UTP (UFS Transport Protocol) descriptor validation
- Gear switching sequences (PWM → HS-G1 → HS-G4)
- Power mode transitions (Active/Idle/Sleep/Hibernate)
- UFS device descriptor reads (manufacturer, capacity, features)
- Error handling: UIC errors, UTP errors, timeout recovery

**Load with**: `@skill fv-storage/ufs`

---

## Common PythonSV Initialization

### SATA Controller Discovery

```python
from pysv import *
import pysv.client.sve as sve

# Connect to target
sve.connect(target="<platform-hostname>")

# Locate SATA controller via PCI scan
# Typical location: Bus 0, Device 0x17 (23 decimal) or 0x11 (17 decimal)
# Class code: 0x010601 (AHCI)

def find_sata_controller():
    for bus in range(1):  # Usually bus 0
        for dev in range(32):
            for func in range(8):
                try:
                    vendor = pci_read(bus, dev, func, 0x00, size=2)
                    if vendor == 0xFFFF or vendor == 0x0000:
                        continue
                    class_code = pci_read(bus, dev, func, 0x08, size=4) >> 8
                    if class_code == 0x010601:  # AHCI
                        print(f"AHCI Controller found: {bus:02X}:{dev:02X}.{func}")
                        return (bus, dev, func)
                except:
                    continue
    return None

sata_bdf = find_sata_controller()
if sata_bdf:
    bus, dev, func = sata_bdf
    ahci_bar = pci_read(bus, dev, func, 0x24, size=4) & 0xFFFFFFF0  # BAR5
    print(f"AHCI Base Address: 0x{ahci_bar:08X}")
    
    # Read HBA Capabilities
    cap = mem_read(ahci_bar + 0x00, size=4)
    port_count = ((cap >> 0) & 0x1F) + 1
    print(f"Port Count: {port_count}")
```

### UFS Controller Discovery

```python
# UFS controller location is platform-specific, check HAS
# Example for Lunar Lake: Bus 0, Device 0x12, Function 7 (verify per platform)

def find_ufs_controller(platform="NVL"):
    """Find UFS controller - BDF varies by platform"""
    # Platform-specific BDF mapping (verify against HAS)
    bdf_map = {
        "MTL": (0, 0x12, 7),   # Bus 0, Dev 18, Func 7
        "LNL": (0, 0x12, 7),   # Bus 0, Dev 18, Func 7
        "PTL": (0, 0x12, 7),   # Bus 0, Dev 18, Func 7
        "WCL": (0, 0x12, 7),   # Bus 0, Dev 18, Func 7
        "NVL": (0, 0x17, 0),   # Bus 0, Dev 23, Func 0 (UFS 4.0, DevID=0xD335)
    }
    expected_bus, expected_dev, expected_func = bdf_map.get(platform, (0, 0x12, 7))
    try:
        vendor = pci_read(expected_bus, expected_dev, expected_func, 0x00, size=2)
        device = pci_read(expected_bus, expected_dev, expected_func, 0x02, size=2)
        if vendor == 0x8086:  # Intel
            print(f"UFS Controller: {expected_bus:02X}:{expected_dev:02X}.{expected_func}")
            print(f"Device ID: 0x{device:04X}")
            ufs_bar = pci_read(expected_bus, expected_dev, expected_func, 0x10, size=4) & 0xFFFFFFF0
            print(f"UFS Base Address: 0x{ufs_bar:08X}")
            return (expected_bus, expected_dev, expected_func, ufs_bar)
    except:
        pass
    return None

# Read UFS capabilities
ufs_info = find_ufs_controller()
if ufs_info:
    bus, dev, func, ufs_bar = ufs_info
    cap = mem_read(ufs_bar + 0x00, size=4)
    num_lanes = ((cap >> 16) & 0xF) + 1
    print(f"UFS Lanes: {num_lanes}")
```

---

## Platform-Specific Configuration Paths

| Platform | SATA Location | UFS Location | Notes |
|----------|---------------|--------------|-------|
| **MTL** | 0:17.0 | 0:12.7 | Mobile: 1-2 SATA ports, UFS 3.1 |
| **ARL** | 0:17.0 | N/A | Desktop, 2-4 SATA ports, no UFS |
| **LNL** | 0:17.0 | 0:12.7 | Mobile, 1 SATA port, UFS 4.0 HS-G5 |
| **PTL** | 0:17.0 | 0:12.7 | Client flagship, verify SKU for port count |
| **NVL** | 0:17.0 | 0:23.0 | Low-power mobile, UFS 4.0 Gear 5 primary storage, DevID=0xD335 |
| **WCL** | TBD | TBD | Check platform HAS when available |
| **RZL** | TBD | TBD | Check platform HAS when available |
| **TTL** | TBD | TBD | Check platform HAS when available |

⚠️ **Always verify PCI B:D.F via Co-Design query** — these are typical values, SKU variations exist.

---

## Debugging Workflow

### Step 1: Controller Enumeration Check
```
1. Verify PCI device present:
   - Read Vendor ID (offset 0x00) — should be 0x8086 (Intel)
   - Read Device ID (offset 0x02) — match against platform HAS
   - Read Class Code (offset 0x08) — 0x010601 (AHCI), varies for UFS

2. Check power state:
   - Read PMCSR (PCI config 0x84) — should be D0 (0x00)
   - If D3, coordinate with @FV-PM-SOUTH to bring to D0

3. Read Base Address Register (BAR):
   - SATA: BAR5 (offset 0x24)
   - UFS: BAR0 (offset 0x10)
   - Verify non-zero, aligned, within valid MMIO range
```

### Step 2: Controller Ready Check
```
SATA/AHCI:
- Read GHC (Global HBA Control) at BAR5 + 0x04
- Check bit 31 (AE - AHCI Enable) = 1
- If not set, BIOS may have configured IDE/RAID mode

UFS:
- Read HCS (Host Controller Status) at BAR + 0x14
- Check bit 0 (DP - Device Present) = 1
- Check bit 3 (UCRDY - UIC Ready) = 1
- If not ready, perform controller initialization sequence (see UFS sub-skill)
```

### Step 3: Port/Device Enumeration
```
SATA:
- Read PI (Ports Implemented) at BAR5 + 0x0C
- For each set bit, check Port Status (PxSSTAT) at BAR5 + 0x100 + (port * 0x80) + 0x28
- DET field (bits 3:0) should be 0x3 (device detected and PHY communication established)

UFS:
- Issue UIC DME_GET command to read device attributes
- Check device descriptor (manufacturer, model, capacity)
- Verify gear negotiation (read UIC_CMD_ARG3 after link startup)
```

### Step 4: Protocol Validation
- **SATA**: Send IDENTIFY DEVICE command, parse ATA features, check NCQ support
- **UFS**: Read device descriptors, verify WriteBooster/HPB support if UFS 3.1+

### Step 5: Power Management Validation
- **SATA**: Test ALPM (Partial/Slumber), DevSleep entry/exit
- **UFS**: Test Active/Sleep/Hibernate transitions, measure power

---

## Common Failure Signatures

| Signature | Likely Cause | Debug Steps | Related Sub-Skill |
|-----------|--------------|-------------|-------------------|
| **Vendor ID = 0xFFFF** | Controller powered off or not present | Check power domain via @FV-PM-SOUTH, verify SKU supports this controller | - |
| **BAR = 0x00000000** | BIOS didn't allocate MMIO space | Check BIOS settings, PCI resource allocation logs | - |
| **All registers = 0xFF** | Controller in D3 or hung | Check PMCSR, attempt D3→D0 transition, may need platform reset | - |
| **AHCI.GHC.AE = 0** | BIOS configured IDE/RAID mode | Check BIOS SATA mode setting, may need reconfiguration | `sata` |
| **SATA PxSSTAT.DET = 0** | No device on port, or link down | Check cable, drive power, try link retrain | `sata` |
| **SATA PxSERR has errors** | PHY errors, CRC errors | Check link quality, cable, drive firmware | `sata` |
| **UFS HCS.DP = 0** | No UFS device detected | Check device power, UFS card insertion | `ufs` |
| **UFS HCS.UCRDY = 0** | UIC layer not ready | Perform UIC initialization, check ref clock | `ufs` |
| **UFS UIC error** | DME command failed | Check UIC error code, verify attribute address | `ufs` |
| **UFS gear stuck at HS-G1** | Gear switch failed | Check power mode change sequence, PHY calibration | `ufs` |
| **DevSleep won't exit** | DEVSLP signal stuck | Check GPIO routing, PCH pad config via @FV-PM-SOUTH | `sata` |
| **UFS WriteBooster disabled** | Feature not provisioned | Check device descriptor bWriteBoosterBufferType, may need provisioning | `ufs` |
| **RAID volume missing** | RST metadata corrupted | Check OROM version, RST driver, volume metadata with RST CLI | `sata` |

---

## Related Skills

- **@pysv**: PythonSV register access on target platform (required for all storage register operations)
- **@onebkc**: BIOS/driver version lookup for test matrix
- **@nga**: Test execution, failure analysis, station management
- **@hsdes**: Storage bug database, sighting search for AHCI/UFS issues
- **@FV-PM-SOUTH**: PCH power management when storage power issues occur
- **@FV-LPSS**: If storage shares power domain with LPSS (rare, platform-specific)
- **@TTK3**: Platform power control, BIOS reflashing, boot monitoring
- **@securewiki**: Access validation BKMs and debug guides

---

## Next Steps

1. **Load a sub-skill** for protocol-specific validation:
   - SATA/AHCI validation: `@skill fv-storage/sata`
   - UFS validation: `@skill fv-storage/ufs`

2. **Query Co-Design** for platform-specific storage configuration:
   - "What are the SATA port counts for [platform] [SKU]?"
   - "Show UFS controller PCI location for [platform]"

3. **Locate HAS documents** in `.opencode/skill/fv-storage/docs/` and use `@doc-study` to extract register maps

4. **Run PythonSV discovery** using scripts above to enumerate controllers on your target platform

**Ready to assist with storage validation and debug!**
