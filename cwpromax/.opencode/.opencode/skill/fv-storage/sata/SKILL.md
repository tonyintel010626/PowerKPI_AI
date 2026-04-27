---
name: fv-storage/sata
description: SATA/AHCI controller validation - enumeration, protocol compliance, power management, and Intel RST
version: "rev2.0"
---

# SATA/AHCI Validation Sub-Skill

**Scope**: This sub-skill provides detailed validation procedures for SATA controllers implementing the AHCI (Advanced Host Controller Interface) specification across Intel Client SoC platforms. Covers AHCI register validation, SATA protocol compliance, port management, link power states (ALPM, DevSleep), and Intel Rapid Storage Technology (RST) RAID configurations.

### HAS Reference

| Field | Value |
|-------|-------|
| **Document** | SATA 3.0 Controller HAS |
| **Revision** | 1.09 (July 2024) |
| **Pages** | 242 |
| **Compliance** | AHCI 1.3.1, SATA 3.2, IOSF Primary 1.1, Sideband 1.1 |
| **Platforms** | ADP-S, MTL-SOC-M/P, MTP-S, LNL-SOC-P, NVP-S |
| **Power Well** | VNNAON |
| **Local Copy** | `fv-storage/docs/SATA 3.0 Controller.pdf` |
| **Text Dump** | `fv-storage/docs/SATA_3.0_Controller_dump.txt` |
| **Architecture Contact** | Shins Abraham |
| **Validation Contact** | Keat Yee Khoo |

---

## Quick Status Check

```python
# Quick SATA health check - run this first to assess controller state
from pysv import *

def sata_quick_check():
    """Quick SATA controller health check"""
    print("=== SATA Quick Health Check ===\n")
    
    # Find SATA controller (typical location)
    bus, dev, func = 0, 0x17, 0  # Common for most platforms
    
    try:
        vendor = pci_read(bus, dev, func, 0x00, size=2)
        device = pci_read(bus, dev, func, 0x02, size=2)
        
        if vendor == 0xFFFF:
            print("❌ SATA controller not found at 0:17.0")
            print("   Try scanning bus 0 for class code 0x010601 (AHCI)")
            return False
            
        print(f"✓ Controller found: VID:DID = {vendor:04X}:{device:04X}")
        
        # Check power state (PMCS at PCI config offset 0x74 per HAS Section 10.1)
        pmcsr = pci_read(bus, dev, func, 0x74, size=2)
        pstate = pmcsr & 0x3
        print(f"✓ Power State: D{pstate}", "⚠️ Not in D0!" if pstate != 0 else "")
        
        # Get AHCI BAR
        ahci_bar = pci_read(bus, dev, func, 0x24, size=4) & 0xFFFFFFF0
        if ahci_bar == 0:
            print("❌ AHCI BAR not allocated")
            return False
        print(f"✓ AHCI Base: 0x{ahci_bar:08X}")
        
        # Read capabilities
        cap = mem_read(ahci_bar + 0x00, size=4)
        port_count = ((cap >> 0) & 0x1F) + 1
        ncs = ((cap >> 8) & 0x1F) + 1  # NCQ depth
        sss = (cap >> 27) & 1  # Staggered spin-up
        salp = (cap >> 26) & 1  # Aggressive LPM
        
        print(f"✓ Ports: {port_count}, NCQ Depth: {ncs}")
        print(f"  Features: SSS={sss}, SALP={salp}")
        
        # Check which ports are implemented
        pi = mem_read(ahci_bar + 0x0C, size=4)
        print(f"✓ Ports Implemented: 0x{pi:08X}")
        
        # Check port status
        for port in range(port_count):
            if not (pi & (1 << port)):
                continue
            pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)
            det = pxssts & 0xF
            ipm = (pxssts >> 8) & 0xF
            
            status = {0: "Not present", 1: "PHY detected", 3: "PHY ready", 4: "Offline"}
            power = {0: "Not present", 1: "Active", 2: "Partial", 6: "Slumber", 8: "DevSleep"}
            
            print(f"  Port {port}: DET={status.get(det, 'Unknown')}, IPM={power.get(ipm, 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Run the check
sata_quick_check()
```

---

## Overview

### SATA Controller Architecture

The SATA controller in Intel Client platforms implements AHCI (Advanced Host Controller Interface) 1.3.1 specification with Intel-specific extensions for RST (Rapid Storage Technology). AHCI-only mode (no IDE). Up to 8 ports (Desktop=8, Mobile=2), fuse-controlled.

**HAS Building Blocks** (Section 25):
1. **VRUNIT** — Router/config: PCI config decode, IOSF target/initiator, MSI/MSI-X, SGPIO/LED, FLR/HBA reset, clock gating control
2. **VSAUNIT** — Per-port command/DMA/transport/link: BMU (IOSF interface), DMA (PRD/BCU/CmdList), Transport (FIS gen/parse), MUX (syncFIFO), Link (CRC/scramble/8b10b/primitives)
3. **PLPUNIT** — Per-port PHY control: OOB signaling, speed negotiation, per-port power management
4. **PLUNIT** — Common PHY control: PLL, auto-calibration, shared lane resources
5. **VBunit** — Sideband interface: master/target/clock control for PMC/PME/LTR/fuse/strap messaging

**AHCI Software Layers**: Application (AHCI HBA) → Command → Transport → Link → Physical (PHY)

**Key Features**: NCQ (32 cmd slots), DEVSLP (from Slumber only), ALPM (HIPM+DIPM), Partial/Slumber, Staggered Spin-up, MSI-X (per-port vectors), LTR, D3hot+PME, Thermal Throttling, HC Dynamic Power Gating (SR-flop retention, 7167 flops)

**Not Supported**: FIS-based switching, Command Completion Coalescing, FLR capability (bypassed), OBFF (fuse-dependent), D1/D2 power states

### AHCI Register Map Overview

| Offset Range | Region | Purpose |
|--------------|--------|---------|
| **0x00 - 0x2C** | Generic Host Control | HBA capabilities, global control, interrupt status |
| **0x2C - 0xA0** | Reserved/Vendor | Platform-specific extensions, RST metadata |
| **0xA0 - 0x100** | Enclosure Management | LED control for hot-swap bays |
| **0x100 - 0x10FF** | Port 0 Registers | 128 bytes for port 0 control |
| **0x180 - 0x1FF** | Port 1 Registers | 128 bytes for port 1 control |
| ... | ... | Pattern repeats for each port (0x80 byte stride) |

### Platform Coverage

| Platform | Typical Location | Port Count | DevSleep Support | Notes |
|----------|------------------|------------|------------------|-------|
| **MTL** | 0:17.0 | 1-2 | Yes | Mobile SKUs often have 1 port |
| **ARL** | 0:17.0 | 2-4 | Yes | Desktop refresh, more SATA ports |
| **LNL** | 0:17.0 | 1 | Yes | Mobile-first, UFS primary |
| **PTL** | 0:17.0 | 2 | Yes | Client flagship |
| **NVL** | 0:17.0 | 1 | Yes | Low-power mobile |
| **WCL** | TBD | TBD | TBD | Check platform HAS |
| **RZL** | TBD | TBD | TBD | Check platform HAS |
| **TTL** | TBD | TBD | TBD | Check platform HAS |

⚠️ **Always verify port count via CAP register** — SKU variations exist within same platform family.

---

## HBA (Host Bus Adapter) Registers

### CAP - HBA Capabilities (Offset 0x00)

```python
# Read and decode HBA capabilities
ahci_bar = 0xYOUR_BAR_HERE  # Get from PCI config 0x24

cap = mem_read(ahci_bar + 0x00, size=4)

# Decode key fields
np = (cap & 0x1F) + 1           # Number of ports (bits 4:0)
sxs = (cap >> 5) & 1            # External SATA support
ems = (cap >> 6) & 1            # Enclosure management
cccs = (cap >> 7) & 1           # Command completion coalescing
ncs = ((cap >> 8) & 0x1F) + 1   # NCQ command slots (bits 12:8)
psc = (cap >> 13) & 1           # Partial state capable
ssc = (cap >> 14) & 1           # Slumber state capable
pmd = (cap >> 15) & 1           # PIO multiple DRQ
fbss = (cap >> 16) & 1          # FIS-based switching
spm = (cap >> 17) & 1           # Port multiplier
sam = (cap >> 18) & 1           # AHCI mode only
iss = (cap >> 20) & 0xF         # Interface speed (0x2=Gen2, 0x3=Gen3)
sclo = (cap >> 24) & 1          # Command list override
sal = (cap >> 25) & 1           # Activity LED
salp = (cap >> 26) & 1          # Aggressive LPM
sss = (cap >> 27) & 1           # Staggered spin-up
smps = (cap >> 28) & 1          # Mechanical presence switch
ssntf = (cap >> 29) & 1         # SNotification register
sncq = (cap >> 30) & 1          # Native command queuing
s64a = (cap >> 31) & 1          # 64-bit addressing

print(f"Ports: {np}, NCQ Slots: {ncs}, Speed: Gen{iss}")
print(f"LPM: Partial={psc}, Slumber={ssc}, ALPM={salp}")
print(f"Features: SSS={sss}, NCQ={sncq}, 64bit={s64a}")
```

**Key Validations**:
- `NP` should match platform HAS port count specification
- `ISS` should be 0x3 (Gen3, 6 Gbps) for modern platforms
- `SALP` = 1 required for ALPM (Aggressive Link Power Management)
- `SSS` = 1 for staggered spin-up (prevents power surge on boot)

### GHC - Global HBA Control (Offset 0x04)

```python
ghc = mem_read(ahci_bar + 0x04, size=4)

hr = ghc & 1           # HBA Reset (write 1 to reset)
ie = (ghc >> 1) & 1    # Interrupt Enable
mrsm = (ghc >> 2) & 1  # MSI Revert to Single Message
ae = (ghc >> 31) & 1   # AHCI Enable

print(f"AHCI Enable: {ae}, Interrupts: {ie}")

# CRITICAL: AE must be 1 for AHCI mode
if ae == 0:
    print("⚠️ AHCI not enabled - BIOS may be in IDE or RAID mode")
    print("   Check BIOS SATA configuration setting")
```

**Safety Note**: Setting `HR` bit resets the entire controller. Only do this if:
1. No I/O operations in progress
2. OS storage drivers are unloaded
3. Platform can tolerate storage reset

### IS - Interrupt Status (Offset 0x08)

```python
is_reg = mem_read(ahci_bar + 0x08, size=4)

# Each bit corresponds to a port
for port in range(32):
    if is_reg & (1 << port):
        print(f"Port {port} has pending interrupt")
        
# Clear interrupts by writing 1s
mem_write(ahci_bar + 0x08, is_reg)
```

### PI - Ports Implemented (Offset 0x0C)

```python
pi = mem_read(ahci_bar + 0x0C, size=4)

implemented_ports = []
for port in range(32):
    if pi & (1 << port):
        implemented_ports.append(port)
        
print(f"Implemented ports: {implemented_ports}")

# ⚠️ Only iterate over implemented ports!
# Don't assume ports 0-N are implemented sequentially
```

---

## PCI Configuration Registers (HAS Section 10.1)

### Critical PCI Config Register Map

| Offset | Register | Key Fields |
|--------|----------|------------|
| **0x00** | ID | VID=8086h, DID per fuse/strap |
| **0x04** | CMD | BME[2], MSE[1], IOSE[0] |
| **0x08** | RID/CC | PI=01h(AHCI)/00h(RAID), SCC=06h(AHCI)/04h(RAID) |
| **0x24** | ABAR | BAR5 — AHCI MMIO base, size per SATAGC.ASSEL[2:0] |
| **0x70** | PCI PM | PM Cap: D0/D3hot only (no D1/D2), PM spec 1.2 |
| **0x74** | PMCS | PMES[15], PMEE[8], PS[1:0] (00=D0, 11=D3hot) |
| **0x80** | MSI | MC[0]=MSIE, single vector only |
| **0x90** | MAP | SPD[23:16] port disable (RWO), PCD[7:0] port clock disable |
| **0x94** | PCS | PxP[23:16] port present (RO, set on COMINIT), PxE[7:0] port enable |
| **0x9C** | SATAGC | REGLOCK[31], SMS[16] AHCI/RAID, SCFD[10] func disable, ASSEL[2:0] ABAR size |
| **0xA0** | SIRI | SIR Index register (index/data pair with SIRD) |
| **0xA4** | SIRD | SIR Data register |
| **0xD0** | MXID | MSI-X capability (per-port vectors, up to 8 entries) |
| **0xE0** | BFCS | BIST FIS control/status |

### MAP — Port Mapping (Offset 0x90)

```python
# Check port disable and clock disable status
map_reg = pci_read(bus, dev, func, 0x90, size=4)
spd = (map_reg >> 16) & 0xFF  # Port disable (RWO — set once by BIOS)
pcd = map_reg & 0xFF          # Port clock disable

for port in range(8):
    disabled = "DISABLED" if (spd >> port) & 1 else "enabled"
    clk_off = "CLK_OFF" if (pcd >> port) & 1 else "clk_on"
    print(f"  Port {port}: {disabled}, {clk_off}")
# ⚠️ Cannot set PCD if PCS.PxE=1 — must disable port first
```

### PCS — Port Control and Status (Offset 0x94)

```python
# Check port present and enable status
pcs = pci_read(bus, dev, func, 0x94, size=4)
pxp = (pcs >> 16) & 0xFF  # Port present (RO, set on COMINIT detect)
pxe = pcs & 0xFF          # Port enable (master on/off, not reset by FLR)

for port in range(8):
    present = "PRESENT" if (pxp >> port) & 1 else "absent"
    enabled = "ENABLED" if (pxe >> port) & 1 else "disabled"
    print(f"  Port {port}: {present}, {enabled}")
# ⚠️ BIOS must enable all ports (PxE=1) before OS handoff
```

### SATAGC — SATA General Configuration (Offset 0x9C)

```python
satagc = pci_read(bus, dev, func, 0x9C, size=4)
reglock = (satagc >> 31) & 1    # RWO — locks RW/L registers
sms = (satagc >> 16) & 1        # 0=AHCI, 1=RAID (survives D3→D0)
scfd = (satagc >> 10) & 1       # SATA controller function disable
assel = satagc & 0x7            # ABAR size (000=2K, 001=16K, ..., 110=512K)
mss = (satagc >> 3) & 0x3       # MSI-X table BAR size

abar_sizes = {0: "2K", 1: "16K", 2: "32K", 3: "64K", 4: "128K", 5: "256K", 6: "512K"}
print(f"SATAGC: REGLOCK={reglock}, SMS={'RAID' if sms else 'AHCI'}, SCFD={scfd}")
print(f"  ABAR size: {abar_sizes.get(assel, 'Unknown')}")
# ⚠️ REGLOCK=1 is one-time set — locks RW/L regs until next reset
```

### CAP2 — HBA Capabilities Extended (AHCI Offset 0x24)

```python
cap2 = mem_read(ahci_bar + 0x24, size=4)

deso = (cap2 >> 5) & 1   # DevSleep Entrance from Slumber Only (always 1)
sadm = (cap2 >> 4) & 1   # Supports Aggressive Device sleep Management (fuse)
sds = (cap2 >> 3) & 1    # Supports Device Sleep (fuse)
apst = (cap2 >> 2) & 1   # Automatic Partial to Slumber Transitions (fuse)
boh = cap2 & 1           # BIOS/OS Handoff

print(f"CAP2: DESO={deso}, SADM={sadm}, SDS={sds}, APST={apst}, BOH={boh}")
# ⚠️ DESO=1 means DevSleep can ONLY be entered from Slumber state
# ⚠️ SADM/SDS/APST are fuse-controlled — cannot be changed by software
```

### RST Device IDs (HAS Section 24.3.17)

| SKU | Device ID | Description |
|-----|-----------|-------------|
| Mobile AHCI | 0x282A | Mobile client AHCI |
| Desktop AHCI 2-port | 0x2822 | Desktop 2-port |
| Desktop AHCI 4-port | 0x2823 | Desktop 4-port |
| Desktop AHCI 6-port | 0x2824 | Desktop 6-port |
| RSTe 2-port | 0x2826 | Server/workstation 2-port |
| RSTe 4-port | 0x2827 | Server/workstation 4-port |
| RSTe 8-port | 0x2828 | Server/workstation 8-port |

> **Note**: DID[15:7] come from SetID sideband msg (PMC), DID[6:0] from straps/fuses/SATAGC.

---

## Port Registers (0x100 + port * 0x80)

Each port has 128 bytes (0x80) of register space starting at offset 0x100.

### Port Register Map

| Offset | Register | Purpose |
|--------|----------|---------|
| **+0x00** | PxCLB | Command List Base Address (low 32-bit) |
| **+0x04** | PxCLBU | Command List Base Address (high 32-bit) |
| **+0x08** | PxFB | FIS Base Address (low 32-bit) |
| **+0x0C** | PxFBU | FIS Base Address (high 32-bit) |
| **+0x10** | PxIS | Interrupt Status |
| **+0x14** | PxIE | Interrupt Enable |
| **+0x18** | PxCMD | Command and Status |
| **+0x1C** | Reserved | - |
| **+0x20** | PxTFD | Task File Data |
| **+0x24** | PxSIG | Signature |
| **+0x28** | PxSSTS | Serial ATA Status |
| **+0x2C** | PxSCTL | Serial ATA Control |
| **+0x30** | PxSERR | Serial ATA Error |
| **+0x34** | PxSACT | Serial ATA Active |
| **+0x38** | PxCI | Command Issue |
| **+0x3C** | PxSNTF | SNotification |
| **+0x40** | PxFBS | FIS-based Switching |
| **+0x44** | PxDEVSLP | Device Sleep |
| **+0x48-0x6F** | Reserved | - |
| **+0x70-0x7F** | Vendor | Intel RST extensions |

### PxCMD - Port Command and Status

```python
def check_port_state(ahci_bar, port):
    pxcmd_offset = 0x118 + (port * 0x80)
    pxcmd = mem_read(ahci_bar + pxcmd_offset, size=4)
    
    st = pxcmd & 1          # Start (command engine running)
    sud = (pxcmd >> 1) & 1  # Spin-Up Device
    pod = (pxcmd >> 2) & 1  # Power On Device
    clo = (pxcmd >> 3) & 1  # Command List Override
    fre = (pxcmd >> 4) & 1  # FIS Receive Enable
    ccs = (pxcmd >> 8) & 0x1F  # Current Command Slot
    mpss = (pxcmd >> 13) & 1   # Mechanical Presence Switch
    fr = (pxcmd >> 14) & 1     # FIS Receive Running
    cr = (pxcmd >> 15) & 1     # Command List Running
    cps = (pxcmd >> 16) & 1    # Cold Presence State
    pma = (pxcmd >> 17) & 1    # Port Multiplier Attached
    hpcp = (pxcmd >> 18) & 1   # Hot Plug Capable
    mpsp = (pxcmd >> 19) & 1   # Mechanical Presence Switch
    cpd = (pxcmd >> 20) & 1    # Cold Presence Detect
    esp = (pxcmd >> 21) & 1    # External SATA Port
    fbscp = (pxcmd >> 22) & 1  # FIS-based Switching Capable
    apste = (pxcmd >> 23) & 1  # Auto Partial to Slumber Enable
    atapi = (pxcmd >> 24) & 1  # Device is ATAPI
    dlae = (pxcmd >> 25) & 1   # Drive LED on ATAPI Enable
    alpe = (pxcmd >> 26) & 1   # Aggressive LPM Enable
    asp = (pxcmd >> 27) & 1    # Aggressive Slumber/Partial
    icc = (pxcmd >> 28) & 0xF  # Interface Communication Control
    
    icc_decode = {
        0x0: "Idle/No-Op", 0x1: "Active", 0x2: "Partial",
        0x6: "Slumber", 0x8: "DevSleep",
        0xF: "Reserved (HW transition in progress)"
    }
    
    print(f"Port {port} PxCMD: ST={st}, FRE={fre}, CR={cr}, FR={fr}")
    print(f"  ICC={icc} ({icc_decode.get(icc, 'Unknown')})")
    print(f"  LPM: ALPE={alpe}, ASP={asp}, APSTE={apste}")
    print(f"  Hot-plug: HPCP={hpcp}, CPD={cpd}")
    
    return pxcmd

# Enable port
def enable_port(ahci_bar, port):
    pxcmd_offset = 0x118 + (port * 0x80)
    pxcmd = mem_read(ahci_bar + pxcmd_offset, size=4)
    
    # Set FRE (FIS Receive Enable) first
    pxcmd |= (1 << 4)
    mem_write(ahci_bar + pxcmd_offset, pxcmd)
    
    # Wait for FR (FIS Receive Running)
    for _ in range(100):
        pxcmd = mem_read(ahci_bar + pxcmd_offset, size=4)
        if pxcmd & (1 << 14):
            break
    
    # Set ST (Start)
    pxcmd |= 1
    mem_write(ahci_bar + pxcmd_offset, pxcmd)
```

### PxSSTS - Serial ATA Status

```python
pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)

det = pxssts & 0xF          # Device Detection (bits 3:0)
spd = (pxssts >> 4) & 0xF   # Current Speed (bits 7:4)
ipm = (pxssts >> 8) & 0xF   # Interface Power Management (bits 11:8)

det_status = {
    0x0: "No device detected",
    0x1: "PHY communication established (but no device)",
    0x3: "PHY communication established and device present",
    0x4: "PHY offline (disabled or in COMRESET)"
}

spd_status = {
    0x0: "No speed negotiated",
    0x1: "Gen 1 (1.5 Gbps)",
    0x2: "Gen 2 (3.0 Gbps)",
    0x3: "Gen 3 (6.0 Gbps)"
}

ipm_status = {
    0x0: "Not present or not established",
    0x1: "Active",
    0x2: "Partial power management",
    0x6: "Slumber power management",
    0x8: "DevSleep power management"
}

print(f"Port {port} Status:")
print(f"  DET: {det_status.get(det, 'Reserved')}")
print(f"  SPD: {spd_status.get(spd, 'Reserved')}")
print(f"  IPM: {ipm_status.get(ipm, 'Reserved')}")

# Healthy state: DET=3, SPD=3, IPM=1
if det == 3 and spd == 3 and ipm == 1:
    print("✓ Port is healthy and active at Gen3")
```

### PxSERR - Serial ATA Error

```python
pxserr = mem_read(ahci_bar + 0x130 + (port * 0x80), size=4)

# Decode error bits
errors = {
    0: "ERR_I - Recovered Data Integrity Error",
    1: "ERR_M - Recovered Communications Error",
    8: "ERR_T - Transient Data Integrity Error",
    9: "ERR_C - Persistent Communication Error",
    10: "ERR_P - Protocol Error",
    11: "ERR_E - Internal Error",
    16: "DIAG_N - PhyRdy Change",
    17: "DIAG_I - Phy Internal Error",
    18: "DIAG_W - Comm Wake",
    19: "DIAG_B - 10B to 8B Decode Error",
    20: "DIAG_D - Disparity Error",
    21: "DIAG_C - CRC Error",
    22: "DIAG_H - Handshake Error",
    23: "DIAG_S - Link Sequence Error",
    24: "DIAG_T - Transport State Transition Error",
    25: "DIAG_F - Unknown FIS Type",
    26: "DIAG_X - Exchanged"
}

print(f"Port {port} Errors (PxSERR = 0x{pxserr:08X}):")
for bit, desc in errors.items():
    if pxserr & (1 << bit):
        print(f"  Bit {bit}: {desc}")

# Clear errors by writing 1s
mem_write(ahci_bar + 0x130 + (port * 0x80), pxserr)
```

**Common Error Patterns**:
- **ERR_C (bit 9)**: Bad cable, drive failure, or EMI interference
- **DIAG_C (bit 21)**: CRC errors → check cable quality
- **DIAG_N (bit 16)**: PhyRdy change → hot-plug event or link instability
- **ERR_P (bit 10)**: Protocol error → incompatible device or AHCI bug

### PxSIG - Port Signature

```python
pxsig = mem_read(ahci_bar + 0x124 + (port * 0x80), size=4)

signatures = {
    0x00000101: "ATA device (hard drive/SSD)",
    0xEB140101: "ATAPI device (optical drive)",
    0xC33C0101: "Enclosure management bridge",
    0x96690101: "Port multiplier"
}

device_type = signatures.get(pxsig, f"Unknown (0x{pxsig:08X})")
print(f"Port {port} Device: {device_type}")
```

### PxDEVSLP - Device Sleep

```python
# DevSleep control (SATA 3.3 feature for ultra-low power < 5mW)
pxdevslp_offset = 0x144 + (port * 0x80)
pxdevslp = mem_read(ahci_bar + pxdevslp_offset, size=4)

adse = pxdevslp & 1           # Aggressive DevSleep Enable
dsp = (pxdevslp >> 1) & 1     # DevSleep Present (device supports)
deto = (pxdevslp >> 2) & 0xFF # DevSleep Exit Timeout
mdat = (pxdevslp >> 10) & 0x1F # Minimum DevSleep Assertion Time
dito = (pxdevslp >> 15) & 0x3FF # DevSleep Idle Timeout
dm = (pxdevslp >> 25) & 0xF   # DITO Multiplier

print(f"DevSleep: ADSE={adse}, DSP={dsp}")
print(f"  Timeouts: DETO={deto}, MDAT={mdat}, DITO={dito}x{dm}")

# Enable aggressive DevSleep
def enable_devslp(ahci_bar, port):
    pxdevslp = mem_read(ahci_bar + pxdevslp_offset, size=4)
    
    # Check if device supports it
    if not (pxdevslp & (1 << 1)):
        print("Device does not support DevSleep")
        return False
    
    # Set ADSE=1, configure timeouts
    pxdevslp |= 1  # ADSE
    # Example: DITO=0x01F4 (500ms), multiplier=1 (1ms units) = 500ms idle timeout
    pxdevslp = (pxdevslp & ~(0x3FF << 15)) | (0x1F4 << 15)
    pxdevslp = (pxdevslp & ~(0xF << 25)) | (1 << 25)
    
    mem_write(ahci_bar + pxdevslp_offset, pxdevslp)
    print("DevSleep enabled with 500ms idle timeout")
    return True
```

---

## SATA Link Power Management

### ALPM (Aggressive Link Power Management)

ALPM allows automatic transitions to Partial and Slumber link power states during idle periods.

**Power States**:
- **Active** (L0): Full power, ~1.5W
- **Partial** (L1): Reduced power, ~0.5W, < 10μs exit latency
- **Slumber** (L2): Minimal power, ~0.1W, < 10ms exit latency
- **DevSleep** (L3): Ultra-low, < 5mW, ~20ms exit latency (requires DEVSLP signal)

```python
def configure_alpm(ahci_bar, port, mode="aggressive"):
    """
    Configure ALPM for a port
    mode: "disabled", "partial", "slumber", "aggressive"
    """
    pxcmd_offset = 0x118 + (port * 0x80)
    pxsctl_offset = 0x12C + (port * 0x80)
    
    pxcmd = mem_read(ahci_bar + pxcmd_offset, size=4)
    pxsctl = mem_read(ahci_bar + pxsctl_offset, size=4)
    
    if mode == "disabled":
        # Clear ALPE and ASP bits
        pxcmd &= ~((1 << 26) | (1 << 27))
        
    elif mode == "partial":
        # Set ALPE, clear ASP (Partial only)
        pxcmd |= (1 << 26)   # ALPE
        pxcmd &= ~(1 << 27)  # ASP=0
        
    elif mode == "slumber":
        # Set ALPE, set ASP (Partial and Slumber)
        pxcmd |= (1 << 26)   # ALPE
        pxcmd |= (1 << 27)   # ASP=1
        
    elif mode == "aggressive":
        # ALPE + ASP + APSTE (auto Partial→Slumber)
        pxcmd |= (1 << 26)   # ALPE
        pxcmd |= (1 << 27)   # ASP
        pxcmd |= (1 << 23)   # APSTE
        
    mem_write(ahci_bar + pxcmd_offset, pxcmd)
    print(f"Port {port} ALPM configured: {mode}")
```

### Checking Current Power State

```python
def get_link_power_state(ahci_bar, port):
    pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)
    ipm = (pxssts >> 8) & 0xF
    
    states = {
        0x0: "Not present",
        0x1: "Active",
        0x2: "Partial",
        0x6: "Slumber",
        0x8: "DevSleep"
    }
    
    return states.get(ipm, f"Unknown (0x{ipm:X})")

# Monitor state transitions
import time
for i in range(10):
    state = get_link_power_state(ahci_bar, port)
    print(f"T+{i}s: {state}")
    time.sleep(1)
```

---

## Intel RST (Rapid Storage Technology) Mode Detection

```python
def detect_rst_mode(ahci_bar, bus, dev, func):
    """Detect if controller is in RST RAID mode"""
    
    # Check PCI class code
    class_code = pci_read(bus, dev, func, 0x08, size=4) >> 8
    
    modes = {
        0x010601: "AHCI mode",
        0x010400: "RAID mode (RST)",
        0x01018A: "IDE mode (legacy)"
    }
    
    mode = modes.get(class_code, f"Unknown (0x{class_code:06X})")
    print(f"SATA Mode: {mode}")
    
    # In RAID mode, RST metadata is in vendor-specific registers
    if class_code == 0x010400:
        # Example: Read RST version (vendor-specific, check HAS)
        # This is platform-dependent!
        print("⚠️ RAID mode detected - some AHCI features may be unavailable")
        print("   RST OROM/driver manages RAID volumes")
    
    return mode

# Check BIOS settings recommendation
def check_mode_compatibility():
    print("BIOS SATA Mode Settings:")
    print("  AHCI: Standard mode, full AHCI features, no RAID")
    print("  RAID: Intel RST enabled, RAID 0/1/5/10, Optane caching")
    print("  IDE:  Legacy mode, not recommended for modern systems")
```

---

## Common Validation Scenarios

### Scenario 1: Port Enumeration Test

```python
def test_port_enumeration(ahci_bar):
    """Test all ports for device presence and link status"""
    
    cap = mem_read(ahci_bar + 0x00, size=4)
    port_count = (cap & 0x1F) + 1
    
    pi = mem_read(ahci_bar + 0x0C, size=4)
    
    results = []
    for port in range(port_count):
        if not (pi & (1 << port)):
            results.append({"port": port, "status": "Not implemented"})
            continue
            
        pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)
        det = pxssts & 0xF
        spd = (pxssts >> 4) & 0xF
        
        pxsig = mem_read(ahci_bar + 0x124 + (port * 0x80), size=4)
        
        results.append({
            "port": port,
            "det": det,
            "speed": ["None", "Gen1", "Gen2", "Gen3"][spd] if spd < 4 else "Unknown",
            "signature": f"0x{pxsig:08X}",
            "device": "Present" if det == 3 else "Not present"
        })
    
    # Print results
    print("\n=== Port Enumeration Results ===")
    for r in results:
        print(f"Port {r['port']}: {r.get('device', r['status'])}", end="")
        if "speed" in r:
            print(f" @ {r['speed']}", end="")
        print()
    
    return results
```

### Scenario 2: Link Speed Verification

```python
def verify_link_speed(ahci_bar, port, expected_gen=3):
    """Verify link negotiated to expected speed"""
    
    pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)
    spd = (pxssts >> 4) & 0xF
    
    if spd == expected_gen:
        print(f"✓ Port {port} at Gen{spd} (expected Gen{expected_gen})")
        return True
    else:
        print(f"❌ Port {port} at Gen{spd} (expected Gen{expected_gen})")
        print("   Possible causes:")
        print("   - Cable not rated for Gen3")
        print("   - Drive only supports lower speed")
        print("   - EMI interference causing fallback")
        return False
```

### Scenario 3: Error Injection and Recovery

```python
def test_error_recovery(ahci_bar, port):
    """Test link error handling and recovery"""
    
    # Clear existing errors
    pxserr = mem_read(ahci_bar + 0x130 + (port * 0x80), size=4)
    mem_write(ahci_bar + 0x130 + (port * 0x80), pxserr)
    
    # Trigger COMRESET (link reset)
    pxsctl = mem_read(ahci_bar + 0x12C + (port * 0x80), size=4)
    pxsctl = (pxsctl & ~0xF) | 0x1  # DET=1 (perform COMRESET)
    mem_write(ahci_bar + 0x12C + (port * 0x80), pxsctl)
    
    time.sleep(0.1)  # Wait 100ms
    
    pxsctl = (pxsctl & ~0xF)  # DET=0 (return to normal)
    mem_write(ahci_bar + 0x12C + (port * 0x80), pxsctl)
    
    # Wait for link to come back
    for i in range(50):  # 5 seconds max
        pxssts = mem_read(ahci_bar + 0x128 + (port * 0x80), size=4)
        det = pxssts & 0xF
        if det == 3:
            print(f"✓ Link recovered after COMRESET in {i*100}ms")
            return True
        time.sleep(0.1)
    
    print(f"❌ Link did not recover after COMRESET")
    return False
```

### Scenario 4: Hotplug Surprise Removal (Quarch QTL1461)

**Source**: [Page ID: 2016451763] — DebugEncyclopedia: SATA HotPlug
**Script**: `docs/SATA_Hotplug_Surprise_Removal_Silicon.py` (Author: Ainalmardhiah Ulul-Azmin)
**BKM Doc**: `docs/SATA_Hotplug_BKM.md`

#### Hardware Requirements
- **Quarch Torridon 4-Port Array Controller (QTL1461)** — USB-connected module that electrically disconnects/reconnects SATA ports
- SATA drives connected through the Quarch module
- USB connection from host to Quarch module

#### Software Requirements
- Python 3.x with `quarchpy` library
- TestMonkey2 (Quarch control software)
- Quarch USB Driver (Windows 10)
- PythonSV (`namednodes`, `svtools.common.baseaccess`)

#### BIOS Settings (MANDATORY)
Navigate to: **Intel Advanced Menu → PCH-IO Configuration → SATA and RST Configuration → Port N**
- **Hot Plug** → `Enabled`
- **DevSlp** → `Disabled`

#### Usage
```bash
# Single device, single hotplug cycle
python SATA_Hotplug_Surprise_Removal_Silicon.py

# Multiple devices, multiple cycles
python SATA_Hotplug_Surprise_Removal_Silicon.py -d 2 -cycle 10
```

#### Flow
```
Initialize Quarch (USB:QTL1461-06-XXX)
│
├── Read initial PxSSTS for ports 0-7
│   (baseline: expect 0x133 = Gen3 active for connected ports)
│
└── For each cycle:
    ├── Power DOWN (Surprise Removal)
    │   ├── quarch_device.sendCommand("signal:action pull")
    │   ├── Sleep 30 seconds
    │   └── Verify PxSSTS = 0x0 or 0x4 (no device / PHY offline)
    │
    └── Power UP (Re-insertion)
        ├── quarch_device.sendCommand("signal:action plug")
        ├── Sleep 30 seconds
        └── Verify PxSSTS restored to baseline (0x133)
```

#### Key Register: PxSSTS (Port x SATA Status)
Access via PythonSV: `pch.sata.portN.pxsstsN`

| Value | DET | SPD | IPM | Meaning |
|-------|-----|-----|-----|---------|
| 0x133 | 3 (present) | 3 (Gen3) | 1 (active) | Device connected, Gen3, active |
| 0x000 | 0 (no device) | 0 | 0 | No device detected |
| 0x004 | 0 | 0 | 4 (offline) | PHY in offline mode |

#### Pass/Fail Criteria
- **PASS**: After plug, PxSSTS returns to baseline value for all ports within 30s
- **FAIL**: PxSSTS mismatch after plug (device not re-detected or wrong link speed)

---

## Common Issues and Debug

### Issue 1: Controller Not Found (Vendor ID = 0xFFFF)

**Symptoms**:
- PCI read of vendor ID returns 0xFFFF
- Controller not visible in device manager

**Root Causes**:
- Controller in D3 power state (power rail off)
- PCH fuse disabled SATA controller (SKU limitation)
- BIOS disabled SATA in setup

**Debug Steps**:
1. Check PMCSR (PCI config offset 0x74 per HAS Section 10.1) for D-state
2. Query Co-Design: "Is SATA controller present in [platform] [SKU]?"
3. Coordinate with @FV-PM-SOUTH to check PCH power domains
4. Check BIOS setup for SATA controller enable/disable option

---

### Issue 2: AHCI Not Enabled (GHC.AE = 0)

**Symptoms**:
- GHC.AE bit is 0
- Ports not responding to commands
- OS reports IDE or RAID mode

**Root Causes**:
- BIOS configured SATA mode as IDE or RAID instead of AHCI
- BIOS bug not setting AE bit

**Debug Steps**:
1. Check PCI class code: should be 0x010601 for AHCI
2. Enter BIOS setup → SATA Configuration → Mode Selection
3. If RAID needed, coordinate with RST team for proper initialization
4. If AHCI needed, change BIOS setting and reboot

---

### Issue 3: Port Shows DET=1 but Never DET=3

**Symptoms**:
- PxSSTS.DET stuck at 1 (PHY detected but no device)
- Link training fails

**Root Causes**:
- No device connected (expected for empty port)
- Cable defect or not properly seated
- Drive power not connected
- OOB signaling issue (bad trace design)

**Debug Steps**:
1. Verify cable connection and seating
2. Check drive power cable (SATA power connector)
3. Try different SATA cable
4. Check PxSERR for specific error codes (CRC, handshake, etc.)
5. If port multiplier, check COMRESET propagation

---

### Issue 4: DevSleep Won't Exit

**Symptoms**:
- Port in DevSleep (IPM=8)
- Write to DEVSLP signal doesn't wake device
- Port appears hung

**Root Causes**:
- DEVSLP GPIO not routed correctly
- PCH pad configuration wrong
- Device firmware bug

**Debug Steps**:
1. Check DEVSLP signal routing in platform schematics
2. Coordinate with @FV-PM-SOUTH to verify GPIO/pad config
3. Read PxDEVSLP register for timeout values
4. Try asserting DEVSLP manually via GPIO control
5. Check drive firmware version for known DevSleep bugs

---

### Issue 5: CRC Errors (PxSERR.DIAG_C Set)

**Symptoms**:
- Frequent CRC errors in PxSERR
- Data corruption or I/O failures
- Link speed may downgrade to Gen1

**Root Causes**:
- Poor cable quality or too long
- EMI interference (nearby power cables)
- Connector oxidation
- Marginal signal integrity on PCB

**Debug Steps**:
1. Replace SATA cable with known-good, short cable
2. Check for EMI sources (fans, power supplies)
3. Try different port to isolate controller vs. cable issue
4. Use oscilloscope to check signal quality (requires HW team)
5. Review platform SI (signal integrity) validation report

---

## Verification Checklist

Use this checklist for comprehensive SATA/AHCI validation:

- [ ] **Controller Enumeration**
  - [ ] Vendor ID reads 0x8086 (Intel)
  - [ ] Device ID matches platform HAS
  - [ ] Class code is 0x010601 (AHCI) or 0x010400 (RAID)
  - [ ] BAR5 allocated and valid

- [ ] **Capabilities Validation**
  - [ ] Port count (CAP.NP) matches platform fuses
  - [ ] NCQ supported (CAP.SNCQ = 1, NCS = 0x1F = 32 slots)
  - [ ] ALPM capable (CAP.SALP = 1)
  - [ ] Interface speed Gen3 (CAP.ISS = 3) — fuse-dependent per port
  - [ ] Staggered spin-up (CAP.SSS = 1, RWO)
  - [ ] CAP2: DESO=1 (DevSleep from Slumber only), SADM/SDS/APST per fuse
  - [ ] VS register 0x10 = 0x00010301 (AHCI v1.31)

- [ ] **PCI Config Validation**
  - [ ] MAP.SPD matches disabled ports per fuse/strap
  - [ ] PCS.PxE = 1 for all implemented ports (BIOS must set before OS)
  - [ ] SATAGC.REGLOCK = 1 (all RW/L registers locked)
  - [ ] SATAGC.ASSEL matches expected ABAR size
  - [ ] PMCS at 0x74: PS = 00 in D0, PME support from D3hot only

- [ ] **Port Enumeration**
  - [ ] All expected ports in PI register
  - [ ] PxSSTS.DET = 3 for ports with devices
  - [ ] PxSSTS.SPD = 3 (Gen3) for modern drives
  - [ ] PxSIG correct (0x00000101 for ATA, 0xEB140101 for ATAPI)
  - [ ] PCS.PxP = 1 (port present, set on COMINIT receipt)

- [ ] **Power Management**
  - [ ] ALPM can enter Partial state (PxCMD.ICC = 2)
  - [ ] ALPM can enter Slumber state (PxCMD.ICC = 6)
  - [ ] DevSleep entry/exit (PxCMD.ICC = 8, from Slumber only)
  - [ ] APS works (PxCMD.APSTE = 1, auto Partial→Slumber)
  - [ ] LTR values programmed: Active ~10µs, Partial ~60µs, Slumber ~1ms
  - [ ] MOD-PHY enters correct PS states per link PM state
  - [ ] HC DPG entry/exit works (CTM5.SPDPGE = 1)
  - [ ] Power consumption measured in each state

- [ ] **BIOS Programming Verified** (SIR Registers)
  - [ ] PTM2.PxALPDLYE = 1 (aggressive LPM delay)
  - [ ] PTM4.SxPCLKDCGE = 1, SxDCGE = 1 (clock gating)
  - [ ] CTM1.RRSSEL = 11 (64B read request size)
  - [ ] CTM1.NQIUFD = 1, STCI = 1
  - [ ] CTM2.SIDECLKDCGEN = 1, SPLDCGE = 1
  - [ ] CTM5.SPDPGE = 1 (master DPG enable)
  - [ ] CPPMSM.SATALTREN = 1, LTRSLBEN = 1

- [ ] **Protocol Compliance**
  - [ ] NCQ commands execute successfully (32 slots)
  - [ ] Hot-plug detect/remove works (surprise + PM mode)
  - [ ] Error injection and recovery tested (fatal + NCQ recovery flows)
  - [ ] BIST FIS patterns work (T/A/S/L/F/P)

- [ ] **Hotplug Validation** (Quarch QTL1461)
  - [ ] BIOS: Hot Plug = Enabled, DevSlp = Disabled per port
  - [ ] Surprise removal: PxSSTS transitions to 0x0 or 0x4 within 30s
  - [ ] Re-insertion: PxSSTS restores to baseline (0x133 for Gen3) within 30s
  - [ ] Multi-cycle stress: 10+ hotplug cycles with consistent pass
  - [ ] Multi-port: All connected ports tested independently

- [ ] **RST Mode (if applicable)**
  - [ ] RAID volumes detected by OS
  - [ ] RST driver version matches OneBKC
  - [ ] OROM version compatible
  - [ ] Device ID matches RST DID (Mobile=0x282A, Desktop=0x2822/23/24)

---

## Vendor Specific MMIO Registers (0xA0 - 0xCF)

*(HAS Section 10.3.1.2)*

| Offset | Register | Key Fields |
|--------|----------|------------|
| 0xA0 | VSP | SFMS[6], PFS[5] (premium features), PT[4] (mobile/desktop), SRPIR[3] |
| 0xA4 | VS_CAP | NRMO[27:16] (NVM remap offset, default=10h=2K), MSL[12:1] (remap size=34K), NRMBE[0] (NVM remap enable, RWO) |
| 0xA8 | RUN | RUNE[16] (remapping under NVMe, hides AHCI BDF, RWO), NVMEDF[7:0] (NVMe dev/func) |
| 0xC0 | RPID | OFST[31:16]=0031h, RPID[15:0]=DID value |
| 0xC8 | SFM | Feature mask (RWO): R0[0], R1[1], R10[2], R5[3], RRT[4], OROM_UI[5], HDDUNLOCK[6], LED[7], eSATA_RRT[8], SRT[9], Optane[13], CPU_attached[14] |

---

## SIR Registers (SATA Initialization Registers)

*(HAS Section 10.3.2 — accessed via PCI Config SIRI@0xA0 / SIRD@0xA4 index/data pair)*

These registers control critical BIOS settings for power management, clock gating, and test modes.

### Per-Port Test Mode (PTM) Registers

| SIR Index | Register | Key BIOS Settings |
|-----------|----------|-------------------|
| 0x80 | PTM1 | PxSQOFFIDLED (squelch off in slumber), PxRXPOL (RX polarity) |
| 0x84 | PTM2 | **PxALPDLYE=1** (aggressive LPM delay — BIOS must set), PxSOSCDCGE (ring osc DCG), PxPCLKDCGE (PCLK DCG) |
| 0x88 | PTM3 | PxOOBTXDDE (OOB on DEVSLP deassert), PxASR1MSE (async signal recovery 1ms) |
| 0x8C | PTM4 | **SxPCLKDCGE=1** (PCLK DCG — BIOS must set), **SxDCGE=1** (backbone DCG — BIOS must set) |
| 0x90 | PTM5 | LASx (link active status, RO), **PHYDPGEPx=1** (MOD-PHY dynamic power gate — BIOS set if supported) |

### Common Test Mode (CTM) Registers

| SIR Index | Register | Key BIOS Settings |
|-----------|----------|-------------------|
| 0x98 | CTM1 | **RRSSEL=11** (read request size 64B — BIOS must set), **NQIUFD=1** (NCQ underflow detect), **STCI=1** (DMA stops CI), SDFTSEL (short data FIS size), PFAD (PRD fetch-ahead) |
| 0x9C | CTM2 | **SIDECLKDCGEN=1** (sideband DCG), **SPLDCGE=1** (PLunit DCG), PLLSHUTDIS (PLL shutdown fuse), VGCVCI (COMINIT gap count), ALDWTC≥4 (ALIGN detect watchdog), SPSSS=01 (slumber PS state: CM off), UNSQLIND=01 (unsquelch indicator) |
| 0xA0 | CTM3 | **SVRDCGE=1** (VRunit DCG), CWCIBRLMAX/MIN (COMWAKE/COMINIT burst reject limits) |
| 0xA4 | CTM4 | PDETOWUDT=19h (pre-DETO PHY warmup 25µs), **ORM=1** (OOB retry mode), SOSCDCGE=1 (ring osc DCG), PPST (port power stagger time) |
| 0xA8 | CTM5 | **SPDPGE=1** (master DPG enable — BIOS must set), SHADPGE (HW autonomous DPG), SRHDPGE (RTD3-Hot DPG), SRCDPGE=1 (RTD3-Cold DPG default), SD0I3DPGE (D0i3 DPG), PSHT (partial/slumber hysteresis timer, default 20h=131µs) |

### CPPM / LTR Registers

| SIR Index | Register | Key Fields |
|-----------|----------|------------|
| 0xC8 | CPPMSM | SATALTREN (LTR enable), **LTRSLBEN=1** (slumber LTR alt — BIOS must set), LTR_OVR_EN, LTR_LOCK |
| 0xCC | CLTRSLB | Slumber LTR: LAT_SCALE=100 (1.048576ms), LAT_VAL=001h → **~1ms** |
| 0xCE | CLTRPAR | Partial LTR: LAT_SCALE=010 (1024ns), LAT_VAL=03Ch → **~60µs** |
| 0xD0 | CLTRACT | Active LTR: LAT_VAL=00Ah → **~10µs** |
| 0xD2 | CLTRMSGOVR | LTR message override (upper DW=0, no non-snoop) |

```python
# Read SIR register via index/data pair
def sir_read(bus, dev, func, index):
    """Read SATA Initialization Register via SIRI/SIRD"""
    pci_write(bus, dev, func, 0xA0, index, size=4)  # SIRI = index
    return pci_read(bus, dev, func, 0xA4, size=4)    # SIRD = data

# Example: Read CTM5 (master DPG enable)
ctm5 = sir_read(bus, dev, func, 0xA8)
spdpge = (ctm5 >> 0) & 1  # Master DPG enable
print(f"CTM5: SPDPGE={spdpge} (master DPG {'enabled' if spdpge else 'disabled'})")

# Example: Read CPPMSM (LTR config)
cppmsm = sir_read(bus, dev, func, 0xC8)
ltr_en = (cppmsm >> 0) & 1
ltrslben = (cppmsm >> 3) & 1
print(f"CPPMSM: SATALTREN={ltr_en}, LTRSLBEN={ltrslben}")
```

---

## Power Management (HAS Detail)

*(HAS Section 24.3.6)*

### MOD-PHY Power State Mapping

| SATA Link State | MOD-PHY State | PLL | Exit Latency |
|----------------|---------------|-----|-------------|
| Active | PS0 | On | — |
| Partial | PS2/PS4/PS6 (per CTM2.PPSSS) | On | ~10µs |
| Slumber | PS4/PS6/PS3 (per CTM2.SPSSS) | Off | ~20µs (PLL bulk) |
| DEVSLP | PS4/PS3 | Off | DETO + PLL |
| Speed Change | PS2 | On | — |
| Disabled/Offline | PS2-reset | — | COMRESET |

### LTR State Machine

```
Port-level LTR FSM:
  LTRActive ←→ LTRPartial ←→ LTRSlumber.Slumber ←→ LTRSlumber.Listen → LTRSlumber.Disable

Aggregated LTR = highest power state across ALL ports

PLL coupling:
  - LTR_ACTIVE / LTR_PARTIAL → PLL ON
  - LTR_SLUMBER → PLL OFF (saves ~20µs on re-entry)

Timing rule:
  - High→Low power: send LTR AFTER MOD-PHY enters LP + PCLK gated
  - Low→High power: send LTR BEFORE MOD-PHY exits LP (after PCLK ungated)
```

### HC Dynamic Power Gating (DPG)

- **Master enable**: CTM5.SPDPGE=1 (BIOS must set)
- **HW autonomous**: CTM5.SHADPGE (all ports in Slumber/Offline + no pending cmds)
- **RTD3-Hot**: CTM5.SRHDPGE
- **RTD3-Cold**: CTM5.SRCDPGE=1 (default enabled)
- **D0i3**: CTM5.SD0I3DPGE
- **SR-flop retention**: 7167 total flops (PLP=936, PL=24, VR=2005, VS=4040, VB=162)
- **Wake sources**: Primary/Sideband/GP wire/Cycle Router/PMC wake
- **Hysteresis**: CTM5.DPGHT (8/32/128/512 clk), IADPGHTM multiplier (x1/x8/x64/x512)

### MOD-PHY Dynamic Power Gating (per-port)

- **Enable**: PTM5.PHYDPGEPx=1 (BIOS set if MOD-PHY DPG supported)
- **Entry**: No outstanding cmds + Slumber/Offline state
- **Common Lane PG**: Activated when PLL is off (all ports in Slumber)
- **Exit**: On SW wake (PxCMD.ICC write or COMRESET)

### Auto Partial-to-Slumber (APS)

- **Enable**: PxCMD.APSTE=1 (per-port)
- **Requires**: Device supports "extended Partial exit latency" (identify word 79)
- **Behavior**: HW automatically transitions from Partial → Slumber after timeout

### DEVSLP (from HAS)

- **Entry**: From Slumber only (GHC_CAP2.DESO=1 — DEVSLP from Slumber Entry Only)
- **DITO**: Idle timeout, PxDEVSLP[24:15], default=4h (4ms)
- **MDAT**: Min assertion time, PxDEVSLP[14:10], default=Ah (10ms)
- **DETO**: Exit timeout, PxDEVSLP[9:2], default=14h (20ms)
- **DM**: DITO multiplier, PxDEVSLP[28:25], default=Fh
- **Input sensing**: Always disabled (hot-plug/AOAC compatible)
- **Mutually exclusive**: with PxSQOFFIDLED (PTM1) — cannot have both

---

## BIOS Programming Requirements

*(Collected from HAS — all critical BIOS-must-set values)*

### Clock Gating Enables (must set =1)
```
PTM2.PxALPDLYE     = 1  # Aggressive LPM delay (per port pair)
PTM4.SxPCLKDCGE    = 1  # PCLK dynamic clock gate (per port pair)
PTM4.SxDCGE        = 1  # Backbone dynamic clock gate (per port pair)
CTM2.SIDECLKDCGEN  = 1  # Sideband clock gate
CTM2.SPLDCGE       = 1  # PLunit/PLPunit clock gate
CTM3.SVRDCGE       = 1  # VRunit/VBunit clock gate
CTM4.SOSCDCGE      = 1  # Ring oscillator clock gate
```

### Power Gate Enables (must set =1)
```
CTM5.SPDPGE        = 1  # Master HC DPG enable
PTM5.PHYDPGEPx     = 1  # Per-port MOD-PHY DPG (if supported)
```

### DMA / Performance
```
CTM1.RRSSEL        = 11b  # Read request size = 64B
CTM1.NQIUFD        = 1    # NCQ underflow detect
CTM1.STCI          = 1    # DMA stops on CI
```

### LTR Configuration
```
CPPMSM.SATALTREN   = 1    # LTR enable
CPPMSM.LTRSLBEN    = 1    # Slumber LTR alternate
CLTRSLB             = LAT_SCALE=100, LAT_VAL=001h  → ~1ms
CLTRPAR             = LAT_SCALE=010, LAT_VAL=03Ch  → ~60µs
CLTRACT             = LAT_VAL=00Ah                  → ~10µs
```

### OOB & PHY
```
CTM2.ALDWTC        >= 4   # ALIGN detect watchdog
CTM2.UNSQLIND      = 01b  # Unsquelch indicator
CTM4.ORM           = 1    # OOB retry mode
CTM2.SPSSS         = 01b  # Slumber PS state (CM off)
```

### Port Management
```
PCS.PxE            = 1 for all ports  # Must enable ALL before OS handoff
SATAGC.REGLOCK     = 1                # Lock RW/L registers (last step!)
```

---

## Error Recovery Flows (HAS)

*(HAS Section 24.3.5)*

### Fatal Error Recovery (HBFS / HBDS / IFS / TFES)

```
1. Read PxIS to identify error type
2. Clear PxCMD.ST → wait for PxCMD.CR = 0
3. Clear PxSERR (write 1s to clear all bits)
4. Clear PxIS (write 1s to clear all bits)
5. If PxTFD.STS.BSY=1 or DRQ=1:
   → Issue COMRESET (PxSCTL.DET = 1, wait, DET = 0)
   → Wait for PxSSTS.DET = 3
6. Set PxCMD.ST = 1 to resume
```

### NCQ Error Recovery

```
1. Read PxSACT to identify failed tag(s)
2. Clear PxCMD.ST → wait for PxCMD.CR = 0
3. Clear PxSERR, PxIS
4. Issue COMRESET if needed (BSY/DRQ stuck)
5. Set PxCMD.ST = 1
6. Issue READ LOG EXT (page 10h) to get error tag
7. Retry or abort failed command(s)
```

### Unsolicited COMINIT Handling

```
Device sends unexpected COMINIT:
  → Controller responds with COMRESET
  → DMA halts until PxIS.PCS is cleared by software
  → Re-establish link, verify PxSSTS.DET = 3
```

### Error Classification (from PxIS)

| Bit | Name | Type | Meaning |
|-----|------|------|---------|
| [30] | TFES | Fatal | Task File Error (device reported error in PxTFD) |
| [29] | HBFS | Fatal | Host Bus Fatal Error (system memory access failed) |
| [28] | HBDS | Fatal | Host Bus Data Error (data CRC from system memory) |
| [27] | IFS | Fatal | Interface Fatal (PxSERR.ERR.P or DIAG.C/H set) |
| [26] | INFS | Non-fatal | Interface Non-Fatal error |
| [24] | OFS | Fatal | Overflow (command engine too many DWs) |
| [23] | IPMS | Non-fatal | Incorrect Port Multiplier Status |
| [22] | PRCS | RO | PhyRdy Change Status |
| [7] | DMPS | Non-fatal | Device Mechanical Presence |
| [6] | PCS | RO | Port Connect Change |
| [5] | DPS | Non-fatal | Descriptor Processed |
| [4] | UFS | RO | Unknown FIS received |
| [3] | SDBS | Non-fatal | Set Device Bits FIS received |
| [2] | DSS | Non-fatal | DMA Setup FIS received |
| [1] | PSS | Non-fatal | PIO Setup FIS received |
| [0] | DHRS | Non-fatal | Device to Host Register FIS received |

---

## Thermal Throttling

*(HAS Section 24.3.12, SIR Index 0x0C-0x3C)*

- **Levels**: T0 (no throttle) → T1 → T2 → T3 (max throttle)
- **Triggered via**: Sideband thermal throttle message from PMC
- **Per port pair**: TTCTL01 (ports 0-1), TTCTL23 (ports 2-3), TTCTL45, TTCTL67
- **T_inactive**: Blocks command dispatch (~32ms/128ms/8ms normal, µs in fast-init)
- **T_dispatch**: Allows normal operation between inactive periods
- **Multipliers**: T1=disabled/1x, T2=2x, T3=4x (configurable)
- **Constraint**: Minimum 1 second between T-state changes

---

## RST (Intel Rapid Storage Technology)

### Device IDs (from HAS fuses)

| SKU | DID | Notes |
|-----|-----|-------|
| Mobile AHCI | 0x282A | Default mobile |
| Desktop AHCI | 0x2822 | 8-port |
| Desktop AHCI (alt) | 0x2823, 0x2824 | Fuse variants |
| RSTe RAID | 0x2826, 0x2827, 0x2828 | Server/workstation |

### Mode Control

- **SATAGC.SMS[16]**: 0=AHCI, 1=RAID
- **CC.SCC**: AHCI=06h (Serial ATA), RAID=04h (RAID controller)
- **CC.PI**: AHCI=01h (AHCI 1.0), RAID=00h
- Controlled by FFSATA5 + FFSATA3 fuses
- Mode survives D3→D0 transitions

---

## DFx and Debug (HAS)

*(HAS Section 24.5)*

### BIST FIS Patterns

| Pattern | Bit | Description |
|---------|-----|-------------|
| F | BFCS[7] | AFE Far-end Loopback |
| L | BFCS[6] | Retimed Far-end Loopback |
| T | BFCS[5] | TX Only (no response expected) |
| A | BFCS[4] | ALIGN Bypass |
| S | BFCS[3] | Primitive Scramble Bypass |
| P | BFCS[2] | Primitive Bit pattern |

### Loopback Modes (SIR Index 0x00)

- **Digital Loopback**: Internal, no PHY involvement
- **Functional Loopback**: Port-pair grouping (N→N+1 or N+1→N)
- **BERt**: Bit error rate test with 40-bit timestamp
- **HBP Mode**: Gen3 only, 40-bit@125MHz, CRC observable via SIR.SHBP
- **One CI/PRD/256B per loopback session**

### VISA2 Debug

- Per-SoC signal files required
- SCAN: 10 fscan signals available
- Secure Plugin access only (VISA green/red)

---

## FLR (Function Level Reset)

*(HAS Section 24.3.9)*

- **Bypassed** when SATAGC.FLRCSSEL=1
- Resets: Transport/Link/PHY layers
- Triggers: COMRESET on all enabled ports
- Resets: Most PCI config + some AHCI regs
- **Does NOT reset**: SIR registers (PTM/CTM preserved)
- **Does NOT reset**: PCS.PxE, MAP.SPD, SATAGC
- HBA Reset (GHC.HR=1) is equivalent but also resets AHCI command engines

---

## Related Skills

- **@fv-storage** (parent): General storage architecture and coordination
- **@fv-storage/ufs**: UFS controller validation
- **@pysv**: PythonSV register access for all examples above
- **@FV-PM-SOUTH**: PCH power management, GPIO configuration for DEVSLP
- **@onebkc**: BIOS and RST driver version lookup
- **@hsdes**: Search for SATA/AHCI sightings and known issues
- **@TTK3/POWER**: Platform power control for reset scenarios

---

**Ready to assist with SATA/AHCI validation, debug, and test development!**
