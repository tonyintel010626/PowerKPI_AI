---
name: fv-storage/ufs
description: UFS controller validation - UFSHCI compliance, UIC commands, gear switching, and power management
version: "rev2.0"
---

# UFS (Universal Flash Storage) Validation Sub-Skill

**Scope**: This sub-skill provides detailed validation procedures for UFS (Universal Flash Storage) controllers implementing the UFSHCI (UFS Host Controller Interface) specification across Intel Client SoC platforms. Covers UFSHCI register validation, UIC (UFS Interconnect) layer commands, UTP (UFS Transport Protocol) descriptor handling, gear switching, power mode management, MCQ (Multi-Circular Queue), and inline crypto engine.

---

## HAS Reference

| Field | Value |
|-------|-------|
| **Document** | NVL SoC UFS Subsystem HAS |
| **Revision** | 1.1.9.1 |
| **Date** | June 24, 2025 |
| **Author** | Murali Bharadwaj N |
| **Pages** | 77 |
| **Classification** | Intel Top Secret |
| **Compliance** | UFS 4.0, UFSHCI 4.0, UniPro v2.0, MIPI M-PHY v5.0 |
| **Platforms** | NVL (primary), LNL/PTL/WCL (prior gen UFS 3.1) |
| **Local Copy** | `C:\Users\pgsvlab\Downloads\NVL SoC UFS Subsystem.pdf` |
| **Online** | https://docs.intel.com/documents/pch_doc/NVL/PCD-H/HAS/NVL_UFS_SubSystem/NVL_UFS_SubSystem.html |
| **Contact** | Murali Bharadwaj N |

---

## Quick Status Check

```python
# Quick UFS health check - run this first to assess controller state
from pysv import *

def ufs_quick_check(bus=0, dev=0x17, func=0, platform="NVL"):
    """
    Quick UFS controller health check
    NVL: B0:D23:F0 (dev=0x17, func=0)
    LNL/PTL: B0:D18:F7 (dev=0x12, func=7) - verify per HAS
    """
    print(f"=== UFS Quick Health Check ({platform}) ===\n")

    try:
        vendor = pci_read(bus, dev, func, 0x00, size=2)
        device = pci_read(bus, dev, func, 0x02, size=2)

        if vendor == 0xFFFF:
            print(f"FAIL: UFS controller not found at {bus:02X}:{dev:02X}.{func}")
            print("   Check platform HAS for correct PCI location")
            return False

        print(f"PASS: Controller found: VID:DID = {vendor:04X}:{device:04X}")

        # NVL expected Device ID = 0xD335
        if platform == "NVL" and device != 0xD335:
            print(f"  WARNING: Expected NVL DID=0xD335, got 0x{device:04X}")

        # Check class code
        class_code = pci_read(bus, dev, func, 0x08, size=4) >> 8
        print(f"PASS: Class Code: 0x{class_code:06X}", "(UFS)" if class_code == 0x010901 else "(unexpected!)")

        # Check power state
        pmcsr = pci_read(bus, dev, func, 0x84, size=2)
        pstate = pmcsr & 0x3
        print(f"PASS: Power State: D{pstate}", "WARNING: Not in D0!" if pstate != 0 else "")

        # Get UFS BAR
        ufs_bar = pci_read(bus, dev, func, 0x10, size=4) & 0xFFFFFFF0
        if ufs_bar == 0:
            print("FAIL: UFS BAR not allocated")
            return False
        print(f"PASS: UFS Base: 0x{ufs_bar:08X}")

        # Read capabilities
        cap = mem_read(ufs_bar + 0x00, size=4)
        nutrs = (cap & 0x1F) + 1
        nutmrs = ((cap >> 16) & 0x7)
        cs = (cap >> 28) & 1

        print(f"PASS: Transfer Slots: {nutrs}, TM Slots: {nutmrs}, Crypto: {cs}")

        # Read version
        ver = mem_read(ufs_bar + 0x08, size=4)
        major = (ver >> 8) & 0xFF
        minor = (ver >> 4) & 0xF
        patch = ver & 0xF
        print(f"PASS: UFSHCI Version: {major}.{minor}.{patch}")

        # Read status
        hcs = mem_read(ufs_bar + 0x14, size=4)
        dp = hcs & 1
        ucrdy = (hcs >> 3) & 1

        print(f"PASS: Status: DP={dp}, UCRDY={ucrdy}")

        if dp == 0:
            print("WARNING: No UFS device detected")
        if ucrdy == 0:
            print("WARNING: UIC layer not ready - may need initialization")

        # Check interrupts
        is_reg = mem_read(ufs_bar + 0x20, size=4)
        if is_reg != 0:
            print(f"WARNING: Pending interrupts: 0x{is_reg:08X}")

        return True

    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False

# Run with platform-specific B:D.F
# NVL: ufs_quick_check(bus=0, dev=0x17, func=0, platform="NVL")
# LNL: ufs_quick_check(bus=0, dev=0x12, func=7, platform="LNL")
```

---

## Overview

### UFS Controller Architecture

UFS (Universal Flash Storage) is a high-performance storage interface designed for mobile and embedded applications. It uses a serial MIPI M-PHY interface with multiple speed "gears" and sophisticated power management.

**Key Components**:
1. **UFSHCI (Host Controller Interface)** - Register interface and DMA engine
2. **UIC (UFS Interconnect Layer)** - Low-level PHY and link management (DME commands)
3. **UTP (UFS Transport Protocol)** - Command descriptors and data transfer
4. **M-PHY** - Physical layer (typically 2 lanes, HS-G1 through HS-G5)
5. **UFS Device** - Storage device with logical units, descriptors, attributes

### NVL UFS Subsystem Architecture (from HAS Rev 1.1.9.1)

The NVL UFS subsystem is built around the **Synopsys UFSHC v4.0** IP with the following key blocks:

```
┌─────────────────────────────────────────────────────────────┐
│                    NVL UFS Subsystem                        │
│                                                             │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐   │
│  │ IOSF2AXI │──>│  DWC AXI     │──>│  UFSHC Wrapper    │   │
│  │ Bridge   │   │  Fabric      │   │  (Synopsys v4.0)  │   │
│  └──────────┘   │  2 pri ports │   │  UFS 4.0 + MCQ    │   │
│       │         │  3 sec ports │   └────────┬──────────┘   │
│       │         └──────────────┘            │              │
│  ┌──────────┐                      ┌────────┴──────────┐   │
│  │   PGA    │                      │ Convergence Layer  │   │
│  │(Buttress)│                      │   + M-PHY v5.0     │   │
│  │ AIC/PIC7 │                      │   2 lanes          │   │
│  └──────────┘                      └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**NVL-Specific Architecture**:
- **IOSF2AXI Bridge**: Converts IOSF primary/sideband traffic to internal AXI protocol (replaced OCP bridge from LNL/PTL/WCL)
- **DWC AXI Fabric**: Synopsys interconnect with 2 primary ports, 3 secondary ports, 64-bit addressing, first-come-first-serve arbitration
- **UFSHC Wrapper**: Synopsys UFS Host Controller v4.0 with UniPro v2.0
- **PGA (AIC Buttress)**: Intel PIC7 buttress IP with SRAM, JTAG, IOSF-SB, clocking, PMC handshake
- **Convergence Layer**: PHY interface to MIPI M-PHY v5.0

**Changes from LNL/PTL/WCL (Gen 3.1) to NVL**:
1. UFS IP upgraded from **3.1 to 4.0** (Gear 5, MCQ support)
2. 16-bit port ID update
3. IOSF bridge replaced to support **AXI instead of OCP**
4. Updated address map for **MCQ registers**
5. Updated AIC buttress IP to **PIC7**

### UFSHCI Register Map Overview

| Offset Range | Region | Purpose |
|--------------|--------|---------|
| **0x000 - 0xFFF** | UFS SS Registers | CAP, VER, HCS, HCE, IS, IE, UIC CMD, UTP |
| **0x1000 - 0x1FFF** | Crypto Engine | AES-XTS config, key slots, capabilities |
| **0x2000 - 0x2FFF** | MCQ Registers | SQ/CQ base addresses, doorbells, interrupts |
| **0x3000 - 0x3FFF** | Convergence Layer | PHY interface registers |

**NVL BAR0**: 32KB MMIO allocation, 16KB actively used (4 x 4KB regions)

### Platform Coverage

| Platform | BDF | Device ID | Lanes | UFS Version | IP Version | Max Gear | Notes |
|----------|-----|-----------|-------|-------------|------------|----------|-------|
| **MTL** | 0:12.7 | Check HAS | 2 | UFS 3.1 | UFSHC 3.1 | HS-G4 | Mobile SKUs |
| **ARL** | N/A | - | - | - | - | - | Desktop, no UFS |
| **LNL** | 0:12.7 | Check HAS | 2 | UFS 4.0 | UFSHC 3.1 | HS-G5 | Mobile flagship |
| **PTL** | 0:12.7 | Check HAS | 2 | UFS 4.0 | UFSHC 3.1 | HS-G5 | Client |
| **NVL** | **0:23.0** | **0xD335** | 2 | **UFS 4.0** | **UFSHC 4.0** | **HS-G5** | Low-power mobile, MCQ, AXI fabric |
| **WCL** | TBD | TBD | TBD | TBD | TBD | TBD | Check platform HAS |
| **RZL** | TBD | TBD | TBD | TBD | TBD | TBD | Check platform HAS |
| **TTL** | TBD | TBD | TBD | TBD | TBD | TBD | Check platform HAS |

**IMPORTANT**: NVL UFS is at **B0:D23:F0** (different from LNL/PTL at 0:12.7). Always verify PCI B:D.F via platform HAS.

---

## NVL PCI Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Vendor ID** | 0x8086 | Intel |
| **Device ID** | 0xD335 | NVL UFS; bits[15:7] from PMC SetID, bits[6:3] fixed, bits[2:0] from fuses |
| **Class Code** | 0x010901 | UFS controller |
| **BDF** | B0:D23:F0 | Bus 0, Device 23, Function 0 |
| **BAR0** | 32KB MMIO | 16KB used (4 x 4KB regions) |
| **BAR1** | Disabled via BIOS | Not used |
| **Root Space** | RS0 (POR) | RS1 not used in NVL |
| **VT-d** | Supported | AXI base: 0x8000_0000_00FF_0000 |
| **LTR** | **NOT supported** | UFS 4.0 does not use LTR |
| **OBFF** | Not supported | - |
| **Interrupts** | IOSF-SB messages | Assert_IRQn (0x54) / Deassert_IRQn (0x55) to ITSS |

### NVL IOSF Sideband Configuration

| Port ID | Target | Purpose |
|---------|--------|---------|
| **0xFC0E** | IOSF2AXI Endpoint | Bridge sideband access |
| **0xFC20** | UFS PGA | Buttress/PMC interface |
| **0xFC21** | UFS PHY SRAM | PHY firmware access |

### NVL IOSF Sideband Messages

| Message | Opcode | Direction | Purpose |
|---------|--------|-----------|---------|
| **IP_ready** | 0xD0 | UFS → PMC | IP initialization complete |
| **REQFUSES** | 0xB8 | UFS → PMC | Request fuse values |
| **SetID** | 0x67 | PMC → UFS | Set Device ID bits |
| **ResetPrep** | 0x2A | PMC → UFS | Prepare for reset |
| **ResetPrep_Ack** | 0x2B | UFS → PMC | Reset prep acknowledged |
| **BootPrep** | 0x28 | PMC → UFS | Prepare for boot |
| **BootPrep_Ack** | 0x29 | UFS → PMC | Boot prep acknowledged |
| **ForcePwrGatePOK** | 0x2E | PMC → UFS | Force power gate (IP Inaccessible entry) |
| **Assert_IRQn** | 0x54 | UFS → ITSS | Assert interrupt |
| **Deassert_IRQn** | 0x55 | UFS → ITSS | Deassert interrupt |

---

## NVL Address Map

### BAR0 Memory Map (32KB Total, 16KB Used)

| Offset | Size | Region | Description |
|--------|------|--------|-------------|
| **0x0000 - 0x0FFF** | 4KB | UFS SS Registers | Standard UFSHCI registers (CAP, VER, HCS, HCE, IS, IE, UIC, UTP) |
| **0x1000 - 0x1FFF** | 4KB | Crypto Engine | AES-XTS configuration, key slots, capabilities |
| **0x2000 - 0x2FFF** | 4KB | MCQ Registers | Multi-Circular Queue SQ/CQ base, doorbells, interrupts |
| **0x3000 - 0x3FFF** | 4KB | Convergence Layer | PHY interface registers |

### AXI Internal Base Address

| Component | AXI Base | Size | Notes |
|-----------|----------|------|-------|
| **UFS Subsystem** | 0x8000_0000_00FF_0000 | 32KB | VT-d safe address |

---

## UFSHCI Controller Registers

### CAP - Controller Capabilities (Offset 0x00)

```python
# Read and decode UFS capabilities
ufs_bar = 0xYOUR_BAR_HERE  # Get from PCI config 0x10

cap = mem_read(ufs_bar + 0x00, size=4)

# Decode key fields
nutrs = (cap & 0x1F) + 1           # Transfer request slots (bits 4:0)
nortt = ((cap >> 8) & 0xFF) + 1    # Outstanding RTTs
nutmrs = ((cap >> 16) & 0x7)       # Task management slots (bits 18:16)
autoh8 = (cap >> 23) & 1           # Auto H8 entry support
cs = (cap >> 28) & 1               # Crypto support
uicdmetms = (cap >> 26) & 1        # UIC DME test mode

print(f"UFS Capabilities:")
print(f"  Transfer Slots: {nutrs}")
print(f"  Task Mgmt Slots: {nutmrs}")
print(f"  Crypto: {cs}, Auto-H8: {autoh8}")
```

**WARNING**: The lane count encoding varies between UFSHCI versions. Always cross-check with HAS document.

### VER - UFS Version (Offset 0x08)

```python
ver = mem_read(ufs_bar + 0x08, size=4)

major = (ver >> 8) & 0xFF
minor = (ver >> 4) & 0xF
patch = ver & 0xF

version_str = f"{major}.{minor}.{patch}"
print(f"UFSHCI Version: {version_str}")

# Map to UFS spec
if major == 3:
    print("  -> UFS 3.0 / 3.1 spec")
elif major == 4:
    print("  -> UFS 4.0 spec (NVL)")
```

### HCS - Host Controller Status (Offset 0x14)

```python
hcs = mem_read(ufs_bar + 0x14, size=4)

dp = hcs & 1                   # Device Present (bit 0)
utrlrdy = (hcs >> 1) & 1       # UTP Transfer Request List Ready
utmrlrdy = (hcs >> 2) & 1      # UTP Task Management List Ready
ucrdy = (hcs >> 3) & 1         # UIC Ready
upmcrs = (hcs >> 8) & 0x7      # UIC Power Mode Change Request Status

print(f"Host Status:")
print(f"  Device Present: {dp}")
print(f"  UTRL Ready: {utrlrdy}")
print(f"  UTMRL Ready: {utmrlrdy}")
print(f"  UIC Ready: {ucrdy}")

if not ucrdy:
    print("WARNING: UIC not ready - run link startup sequence")
if not dp:
    print("WARNING: No device detected - check UFS card insertion and power")
```

### HCE - Host Controller Enable (Offset 0x34)

```python
hce = mem_read(ufs_bar + 0x34, size=4)
enabled = hce & 1

print(f"Controller Enable: {enabled}")

def enable_ufs_controller(ufs_bar):
    """Enable UFS host controller"""
    hce = mem_read(ufs_bar + 0x34, size=4)

    if hce & 1:
        print("Controller already enabled")
        return True

    # Set HCE bit
    mem_write(ufs_bar + 0x34, 1)

    # Wait for controller ready (check HCS.DP and HCS.UCRDY)
    import time
    for i in range(100):  # 1 second timeout
        hcs = mem_read(ufs_bar + 0x14, size=4)
        if (hcs & 1) and ((hcs >> 3) & 1):  # DP and UCRDY
            print(f"PASS: Controller enabled and ready ({i*10}ms)")
            return True
        time.sleep(0.01)

    print("FAIL: Controller enable timeout")
    return False
```

---

## MCQ (Multi-Circular Queue) - NVL UFS 4.0

NVL introduces **MCQ (Multi-Circular Queue)** support with 8 SQ/CQ pairs, replacing the legacy single-queue UTP Transfer Request List model.

### MCQ Overview

| Feature | Value |
|---------|-------|
| **Queue Count** | 8 SQ/CQ pairs (Queue 0-7) |
| **Register Region** | BAR0 + 0x2000 (4KB) |
| **Queue Model** | Submission Queue (SQ) + Completion Queue (CQ) per queue |
| **Doorbell** | Per-queue SQ doorbell and CQ interrupt status |

### MCQ Register Offsets

Each queue has dedicated registers for base address and doorbell/interrupt:

| Queue | SQDAO Offset | SQDAO Value | SQISAO Offset | SQISAO Value | CQDAO Offset | CQDAO Value | CQISAO Offset | CQISAO Value |
|-------|-------------|-------------|---------------|-------------|-------------|-------------|---------------|-------------|
| **Q0** | Per HAS | Per HAS | Per HAS | Per HAS | Per HAS | Per HAS | Per HAS | Per HAS |
| **Q1-Q7** | Incremental | Incremental | Incremental | Incremental | Incremental | Incremental | Incremental | Incremental |

**NOTE**: Exact MCQ register offset values must be verified against the NVL UFS HAS document Section on MCQ offset programming table. The HAS defines specific SQDAO/SQISAO/CQDAO/CQISAO register offsets and values for all 8 queues.

### MCQ Validation Script

```python
def validate_mcq(ufs_bar):
    """Validate MCQ registers are accessible on NVL"""
    print("=== MCQ Validation (NVL UFS 4.0) ===\n")

    mcq_base = ufs_bar + 0x2000  # MCQ register region

    # Check if MCQ is supported via CAP register
    cap = mem_read(ufs_bar + 0x00, size=4)
    # MCQ support indicated in extended capabilities - check HAS for exact bit

    # Read MCQ configuration registers
    # Verify each queue pair is accessible
    for q in range(8):
        offset = mcq_base + (q * 0x40)  # Approximate - verify per HAS
        try:
            sq_val = mem_read(offset, size=4)
            print(f"  Queue {q}: SQ register readable = 0x{sq_val:08X}")
        except Exception as e:
            print(f"  Queue {q}: FAIL - {e}")

    print("\nNOTE: Verify exact MCQ offsets against NVL UFS HAS MCQ offset table")
```

---

## Inline Crypto Engine - NVL

### Crypto Capabilities

| Feature | Value |
|---------|-------|
| **Algorithm** | AES-XTS only |
| **Key Sizes** | 128-bit and 256-bit (2 capabilities: 256b & 512b key entries) |
| **Config Slots** | 32 crypto configuration slots |
| **Sector Sizes** | 512B, 1KB, 2KB, 4KB, 8KB, 16KB, 32KB |
| **Key Storage** | Keys stored in UFS_AON power well (preserved during power gate) |
| **Register Region** | BAR0 + 0x1000 (4KB) |
| **KAT Self-Test** | NOT enabled in NVL |

### Crypto Engine Validation

```python
def validate_crypto(ufs_bar):
    """Validate UFS inline crypto engine on NVL"""
    print("=== Crypto Engine Validation ===\n")

    crypto_base = ufs_bar + 0x1000

    # Check crypto support in CAP register
    cap = mem_read(ufs_bar + 0x00, size=4)
    cs = (cap >> 28) & 1
    print(f"Crypto Support (CAP.CS): {cs}")

    if not cs:
        print("WARNING: Crypto not supported or disabled")
        return False

    # Read crypto capability registers
    # Verify AES-XTS support and key slot count
    # Exact register offsets per HAS crypto section

    print("NOTE: Verify crypto register offsets against NVL UFS HAS Crypto section")
    return True
```

### BIOS Crypto Enable

Inline encryption is enabled via BIOS register at offset **0x600 bit 30**. Verify this is set during BIOS initialization.

---

## NVL Clocks and Speed Grades

### UFS Gear Speeds

| Gear | Rate | Speed per Lane | TxSymbol Freq | PLL Core Freq | Total (2 lanes) |
|------|------|----------------|---------------|---------------|-----------------|
| **HS-G1** | A | 1,457 Mbps | 18.2 MHz | - | 2.9 Gbps |
| **HS-G2** | A | 2,915 Mbps | 36.4 MHz | - | 5.8 Gbps |
| **HS-G3** | A | 5,830 Mbps | 72.9 MHz | - | 11.7 Gbps |
| **HS-G4** | A | 11,660 Mbps | 145.8 MHz | - | 23.3 Gbps |
| **HS-G5** | **A** | **19,968 Mbps** | **249.6 MHz** | **9,984 MHz** | **~40 Gbps** |
| **HS-G5** | **B** | **23,347 Mbps** | **291.84 MHz** | **11,673.6 MHz** | **~46.7 Gbps** |

**NVL Performance Target**: ~4.5 GB/s per direction at Gear 5, requiring 30 outstanding transactions.

### NVL Subsystem Clocks

| Clock | Frequency | Domain | Purpose |
|-------|-----------|--------|---------|
| **scc_axi_clk** | 400 MHz | AXI | Main data path clock |
| **scc_prim_clk** | 400 MHz | IOSF Primary | Host interface clock |
| **scc_sb_clk** | 100 MHz | IOSF Sideband | Configuration/PMC messages |
| **scc_xsoc_clk** | 38.4 MHz | Cross-SoC | Reference clock domain |
| **pia_aux_clk** | 100 MHz | PHY Aux | PHY auxiliary clock |
| **pgcb_clk** | 2.56 MHz | Power Gate | PGCB state machine clock |
| **cfg_clk** | 38.4 MHz | UFS Config | UFS controller config clock |
| **L2 TX Buffer** | 292 MHz | Data path | TX buffer clock |
| **L2 RX Buffer** | 400 MHz | Data path | RX buffer clock |
| **REF_CLK** | 38.4 MHz | External | From ISCLK via GPIO buffer to UFS device |

---

## NVL Memory Blocks

| Memory | Size | Purpose |
|--------|------|---------|
| **CMU** | 32 x 360 | Command Management Unit |
| **TMU** | 8 x 39 | Task Management Unit |
| **WDP** | 1,152 x 132 | Write Data Path buffer |
| **RDP** | 1,024 x 128 | Read Data Path buffer |
| **L2 TX Buffer** | 2,256 x 128 | Layer 2 transmit buffer |
| **L2 RX Buffer** | 1,296 x 128 | Layer 2 receive buffer |
| **PMU** | 512 x 118 | Power Management Unit |
| **PHY SRAM** | 20K x 16 | M-PHY firmware SRAM |
| **PHY EXT ROM** | 20K x 16 | M-PHY external ROM |

---

## NVL External IOs

| Signal | Direction | Description |
|--------|-----------|-------------|
| **UFS_RX_N/P[1:0]** | Input | Receive differential pairs (2 lanes) |
| **UFS_TX_P/N[1:0]** | Output | Transmit differential pairs (2 lanes) |
| **RESREF** | Input | Reference resistor |
| **UFS_GPIO_RESET_B** | Output | UFS device reset (active low) |
| **UFS_REF_CLK** | Output | 38.4 MHz reference clock to UFS device |

### Device Power Rails

| Rail | Voltage | Purpose |
|------|---------|---------|
| **VCC** | 2.5V | UFS device main power |
| **VCCQ** | 1.2V | UFS 3.x/4.x I/O power (1.2V only) |

---

## UIC (UFS Interconnect) Layer

The UIC layer manages the M-PHY physical layer and link configuration through **DME (Device Management Entity)** commands.

### UIC Command Registers

| Offset | Register | Purpose |
|--------|----------|---------|
| **0x90** | UIC_CMD | Command opcode |
| **0x94** | UIC_CMD_ARG1 | MIB attribute address |
| **0x98** | UIC_CMD_ARG2 | Attribute set/configuration |
| **0x9C** | UIC_CMD_ARG3 | MIB value (read result or write value) |

### UIC Command Opcodes

| Opcode | Name | Purpose |
|--------|------|---------|
| **0x01** | DME_GET | Read UFS device attribute |
| **0x02** | DME_SET | Write UFS device attribute |
| **0x03** | DME_PEER_GET | Read UFS device peer attribute |
| **0x04** | DME_PEER_SET | Write UFS device peer attribute |
| **0x05** | DME_POWERON | Power on UFS device |
| **0x06** | DME_POWEROFF | Power off UFS device |
| **0x07** | DME_ENABLE | Enable UFS device |
| **0x08** | DME_RESET | Reset UFS link |
| **0x09** | DME_ENDPOINTRESET | Endpoint reset |
| **0x0A** | DME_LINKSTARTUP | Start link training |
| **0x0B** | DME_HIBERNATE_ENTER | Enter hibernate state |
| **0x0C** | DME_HIBERNATE_EXIT | Exit hibernate state |
| **0x0D** | DME_TEST_MODE | Enter test mode |

### Issuing UIC Commands

```python
def uic_cmd(ufs_bar, cmd, arg1=0, arg2=0, arg3=0, timeout_ms=1000):
    """Issue a UIC command and wait for completion"""
    import time

    # Check if UIC is ready
    hcs = mem_read(ufs_bar + 0x14, size=4)
    if not ((hcs >> 3) & 1):
        print("FAIL: UIC not ready")
        return None

    # Write arguments first
    mem_write(ufs_bar + 0x94, arg1)
    mem_write(ufs_bar + 0x98, arg2)
    mem_write(ufs_bar + 0x9C, arg3)

    # Write command (triggers execution)
    mem_write(ufs_bar + 0x90, cmd)

    # Wait for UCCS (UIC Command Completion Status) interrupt
    start = time.time()
    while (time.time() - start) < (timeout_ms / 1000.0):
        is_reg = mem_read(ufs_bar + 0x20, size=4)
        if is_reg & (1 << 10):  # UCCS bit
            # Clear interrupt
            mem_write(ufs_bar + 0x20, (1 << 10))
            # Read result from ARG3
            result = mem_read(ufs_bar + 0x9C, size=4)
            return result
        time.sleep(0.001)

    print(f"FAIL: UIC command timeout: 0x{cmd:02X}")
    return None
```

### Link Startup Sequence

```python
def ufs_link_startup(ufs_bar):
    """Perform UFS link startup to establish connection"""
    print("=== UFS Link Startup ===")

    # 1. Enable controller
    if not enable_ufs_controller(ufs_bar):
        return False

    # 2. Issue DME_LINKSTARTUP command
    print("Issuing DME_LINKSTARTUP...")
    result = uic_cmd(ufs_bar, cmd=0x0A, timeout_ms=5000)

    if result is None:
        print("FAIL: Link startup failed")
        return False

    # 3. Check link status
    hcs = mem_read(ufs_bar + 0x14, size=4)
    dp = hcs & 1
    ucrdy = (hcs >> 3) & 1

    if dp and ucrdy:
        print("PASS: Link startup successful")

        # 4. Read link speed (gear)
        tx_lanes = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1560)
        print(f"  Active TX Lanes: {tx_lanes}")

        gear = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1568)
        print(f"  TX Gear: HS-G{gear}" if gear else "  TX Gear: PWM")

        return True
    else:
        print(f"FAIL: Link not ready: DP={dp}, UCRDY={ucrdy}")
        return False
```

---

## Gear Switching (Speed Configuration)

UFS supports multiple speed "gears" for power/performance trade-offs:

| Gear | Mode | Speed per Lane | Total (2 lanes) | Notes |
|------|------|----------------|-----------------|-------|
| **PWM G1-G7** | PWM | 3.0-18.2 Mbps | 6-36 Mbps | Very low power, slow |
| **HS-G1** | High-Speed | 1.46 Gbps | 2.9 Gbps | - |
| **HS-G2** | High-Speed | 2.90 Gbps | 5.8 Gbps | - |
| **HS-G3** | High-Speed | 5.83 Gbps | 11.7 Gbps | UFS 2.0+ |
| **HS-G4** | High-Speed | 11.6 Gbps | 23.2 Gbps | UFS 3.0+ |
| **HS-G5** | High-Speed | 23.2 Gbps | 46.4 Gbps | UFS 4.0+ (NVL) |

### Gear Switch Procedure

```python
def switch_gear(ufs_bar, target_gear=4, mode="HS"):
    """
    Switch UFS link to target gear
    mode: "PWM" or "HS" (high-speed)
    target_gear: 1-7 for PWM, 1-5 for HS
    """
    print(f"=== Switching to {mode}-G{target_gear} ===")

    # 1. Set TX/RX gear
    print(f"Setting TX Gear to {target_gear}...")
    uic_cmd(ufs_bar, cmd=0x02, arg1=0x1568, arg3=target_gear)  # PA_TxGear

    print(f"Setting RX Gear to {target_gear}...")
    uic_cmd(ufs_bar, cmd=0x02, arg1=0x1583, arg3=target_gear)  # PA_RxGear

    # 2. Set HS Series (for HS mode)
    if mode == "HS":
        # Series B (2) is standard for HS-G3+
        series = 2 if target_gear >= 3 else 1
        print(f"Setting HS Series to {series}...")
        uic_cmd(ufs_bar, cmd=0x02, arg1=0x156A, arg3=series)

    # 3. Set power mode to activate gear change
    if mode == "HS":
        pwr_mode = 0x11  # FAST mode TX/RX
    else:
        pwr_mode = 0x22  # SLOW mode (PWM) TX/RX

    print(f"Activating power mode change...")
    result = uic_cmd(ufs_bar, cmd=0x02, arg1=0x1571, arg3=pwr_mode, timeout_ms=5000)

    # 4. Wait for power mode change completion
    import time
    for i in range(100):
        hcs = mem_read(ufs_bar + 0x14, size=4)
        upmcrs = (hcs >> 8) & 0x7
        if upmcrs == 0:  # Idle
            print(f"PASS: Gear switch completed ({i*10}ms)")
            actual_gear = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1568)
            print(f"  Actual TX Gear: {actual_gear}")
            return True
        time.sleep(0.01)

    print("FAIL: Gear switch timeout")
    return False
```

---

## UFS Power Management

### Power States

| State | Power | Description | Entry Method | Exit Latency |
|-------|-------|-------------|--------------|--------------|
| **Active** | ~500mW | Full operation | Normal I/O | N/A |
| **Idle** | ~300mW | No I/O, link active | I/O timeout | < 1us |
| **Sleep** | ~50mW | Link in low-power, fast recovery | DME_HIBERNATE_ENTER (partial) | ~1ms |
| **DeepSleep** | <5mW | Power rail off, PHY off | DME_HIBERNATE_ENTER (full) | ~20ms |

### NVL Power Management Details

| Feature | NVL Value | Notes |
|---------|-----------|-------|
| **D0i3** | Partial (no Vnn removal) | D0i3 supported but Vnn stays on |
| **RTD3** | Supported | Per Chassis spec |
| **LTR** | **NOT supported** | UFS 4.0 does not implement LTR |
| **Auto-H8** | Supported | Auto hibernate entry via idle timer |
| **Power Gating** | PGCB-controlled | AON well preserves crypto keys during power gate |
| **S0ix** | Supported | Via flows G/H |
| **Power Reporting** | ufs_idle_ind, d3/d0i3 indication | monitor[127:124] |

### NVL Power Flows (A through H)

The NVL UFS HAS defines 8 power flows covering all transitions:

| Flow | Name | Description |
|------|------|-------------|
| **A** | AON Power Up | Always-On domain power up sequence |
| **B** | Vnn Ungated Power Up | Main power domain ungated |
| **C** | IP Inaccessible Exit | PMC wake -> PGCB ungate -> FW open (host access resumes) |
| **D** | IP Accessible Entry | Auto H8 idle timer -> hibernate -> CDC -> PGCB -> power gate |
| **E** | IP Accessible Exit | Host access triggers PGCB -> PMC -> AON restore |
| **F** | Same as D | Alternative IP Accessible Entry path |
| **G** | Toward S0ix | Platform entering S0ix, UFS power gated |
| **H** | S0ix Exit | Platform exiting S0ix, UFS restored |

### IP Inaccessible Entry (Power Gate)

NVL uses **ForcePwrGatePOK** sideband message (opcode 0x2E) from PMC to trigger IP Inaccessible entry:

```
PMC sends ForcePwrGatePOK (0x2E)
  -> CDC locks ISMs
  -> Deasserts clkreq
  -> PGCB power gate sequence:
     1. isol_en (isolation enable)
     2. force_rst (force reset)
     3. sleep (SRAM retention)
     4. pg_req (power gate request)
```

### Clock Gating Behavior

- **Downstream access** (host -> UFS): Enables AXI clock via CDC cascade
- **Upstream access** (UFS -> host): Clocks already active

### Entering/Exiting Hibernate

```python
def enter_hibernate(ufs_bar, deep=False):
    """
    Enter UFS hibernate state
    deep=False: Sleep (link low-power)
    deep=True: DeepSleep (power off)
    """
    state = "DeepSleep" if deep else "Sleep"
    print(f"=== Entering {state} ===")

    result = uic_cmd(ufs_bar, cmd=0x0B, timeout_ms=2000)

    if result is not None:
        print(f"PASS: Entered {state}")
        pwr_mode = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1571)
        print(f"  Power Mode: 0x{pwr_mode:02X}")
        return True
    else:
        print(f"FAIL: Failed to enter {state}")
        return False

def exit_hibernate(ufs_bar):
    """Exit UFS hibernate state"""
    print("=== Exiting Hibernate ===")

    result = uic_cmd(ufs_bar, cmd=0x0C, timeout_ms=5000)

    if result is not None:
        print("PASS: Exited hibernate")
        return True
    else:
        print("FAIL: Failed to exit hibernate")
        return False
```

---

## NVL BIOS BWG Configuration

BIOS must program the following registers during UFS initialization:

| Register | Offset | Setting | Purpose |
|----------|--------|---------|---------|
| **PCICFGCTRL** | 0x200 | Device enable | Enable UFS PCI function |
| **Trunk Clock Req** | 0x600 | Enable | Request trunk clock |
| **Clock Gate Enable** | 0x1D0 | Enable | Enable clock gating for power savings |
| **Ref Clock Enable** | 0x385C | Enable | Enable 38.4 MHz reference clock to UFS device |
| **D0i3/HAE/DEVIDLE/D3HE** | 0xA0 | Enable all | Enable power management features |
| **Inline Encryption** | 0x600 bit 30 | Set | Enable AES-XTS inline crypto engine |
| **Dual Lane Enable** | 0x600 | Set | Enable 2-lane operation |
| **BAR1 Disable** | 0x600 | Set | Disable unused BAR1 |

**NOTE**: BIOS also runs the ESE (Early Storage Enable) recipe during UFS initialization. Refer to the UFS Initialization Flow document for the complete sequence.

### Static Disable

BIOS can completely disable the UFS function via static disable. When disabled:
- PCI function is hidden
- Power domain is gated
- No register access possible

---

## NVL Fuse Configuration

| Target | Fuse Count | Notes |
|--------|-----------|-------|
| **Bridge** | 32 | IOSF2AXI bridge fuses |
| **PGA** | 1,280 | Large count due to M-PHY Gear 5 calibration data |

---

## NVL DFx and Debug

### VISA Observability

| Feature | Details |
|---------|---------|
| **Top-Level ULMs** | 3 two-lane ULMs |
| **Next-Level ULMs** | 5 ULMs for detailed VISA trace |
| **DTB Buses** | 2 x 8-bit (PMA+RAWPCS, RMMI) |

### DFx Secure Plugins

4 DFx secure plugin locations within the UFS subsystem for controlled debug access.

### NVL Security

- **SAI Policies**: Defined for control, fuse, PVT, RS0 CFG, MMIO, and buttress regions
- **KAT Self-Test**: NOT enabled in NVL

---

## UFS Device Descriptors

```python
def read_device_descriptor(ufs_bar):
    """Read UFS device descriptor via UIC attributes"""
    print("=== UFS Device Descriptor ===")

    # Manufacturer ID (0x1500)
    mfr_id = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1500)
    mfr_names = {0x002C: "Micron", 0x00CE: "Samsung", 0x0098: "Kioxia", 0x0045: "SK Hynix"}
    print(f"Manufacturer: {mfr_names.get(mfr_id, f'0x{mfr_id:04X}')}")

    # Device Type (0x1502)
    dev_type = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1502)
    print(f"Device Type: 0x{dev_type:02X}")

    # UFS Version (0x1508)
    ufs_ver = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1508)
    major = (ufs_ver >> 8) & 0xFF
    minor = (ufs_ver >> 4) & 0xF
    print(f"UFS Version: {major}.{minor}")

    print("  [Total capacity requires SCSI READ CAPACITY command]")
```

---

## Common Validation Scenarios

### Scenario 1: NVL Controller Enumeration Test

```python
def test_nvl_ufs_enumeration(bus=0, dev=0x17, func=0):
    """Test NVL UFS controller enumeration"""

    print("=== NVL UFS Enumeration Test ===\n")

    # Step 1: PCI enumeration
    vendor = pci_read(bus, dev, func, 0x00, size=2)
    device = pci_read(bus, dev, func, 0x02, size=2)

    if vendor != 0x8086:
        print(f"FAIL: Not an Intel device: VID=0x{vendor:04X}")
        return False

    print(f"PASS: VID:DID = {vendor:04X}:{device:04X}")

    if device != 0xD335:
        print(f"WARNING: Expected NVL DID=0xD335, got 0x{device:04X}")

    # Step 2: Class code
    class_code = pci_read(bus, dev, func, 0x08, size=4) >> 8
    if class_code != 0x010901:
        print(f"FAIL: Unexpected class code: 0x{class_code:06X}")
        return False
    print(f"PASS: Class Code = 0x{class_code:06X} (UFS)")

    # Step 3: BAR allocation
    ufs_bar = pci_read(bus, dev, func, 0x10, size=4) & 0xFFFFFFF0
    if ufs_bar == 0:
        print("FAIL: UFS BAR not allocated")
        return False
    print(f"PASS: UFS BAR = 0x{ufs_bar:08X}")

    # Step 4: Controller capabilities
    cap = mem_read(ufs_bar + 0x00, size=4)
    nutrs = (cap & 0x1F) + 1
    cs = (cap >> 28) & 1
    print(f"PASS: Transfer Slots: {nutrs}, Crypto: {cs}")

    # Step 5: Version check
    ver = mem_read(ufs_bar + 0x08, size=4)
    print(f"PASS: UFSHCI Version: {(ver>>8)&0xFF}.{(ver>>4)&0xF}.{ver&0xF}")

    # Step 6: Device present
    hcs = mem_read(ufs_bar + 0x14, size=4)
    dp = hcs & 1
    if not dp:
        print("WARNING: No UFS device present")
        return False

    print("PASS: UFS device detected")
    return True
```

### Scenario 2: Link Training and Gear Validation

```python
def test_link_training(ufs_bar):
    """Test link startup and gear negotiation"""

    print("=== Link Training Test ===\n")

    if not ufs_link_startup(ufs_bar):
        return False

    tx_gear = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1568)
    rx_gear = uic_cmd(ufs_bar, cmd=0x01, arg1=0x1583)
    print(f"Initial: TX Gear={tx_gear}, RX Gear={rx_gear}")

    # Test gear switching up to G5 for NVL
    max_gear = 5  # NVL supports up to HS-G5
    for gear in range(1, max_gear + 1):
        if switch_gear(ufs_bar, target_gear=gear, mode="HS"):
            print(f"PASS: Successfully switched to HS-G{gear}")
        else:
            print(f"FAIL: Failed to switch to HS-G{gear}")
            return False

    return True
```

### Scenario 3: Power State Cycling

```python
def test_power_states(ufs_bar):
    """Test hibernate entry/exit"""

    print("=== Power State Test ===\n")
    import time

    # Active -> Sleep -> Active
    print("Testing Sleep state...")
    if enter_hibernate(ufs_bar, deep=False):
        time.sleep(2)
        if exit_hibernate(ufs_bar):
            print("PASS: Sleep cycle successful")
        else:
            return False
    else:
        return False

    # Active -> DeepSleep -> Active
    print("\nTesting DeepSleep state...")
    if enter_hibernate(ufs_bar, deep=True):
        time.sleep(2)
        if exit_hibernate(ufs_bar):
            print("PASS: DeepSleep cycle successful")
        else:
            return False
    else:
        return False

    return True
```

### Scenario 4: NVL Crypto Engine Validation

```python
def test_nvl_crypto(ufs_bar):
    """Test NVL UFS inline crypto engine"""

    print("=== NVL Crypto Engine Test ===\n")

    # Check crypto support
    cap = mem_read(ufs_bar + 0x00, size=4)
    cs = (cap >> 28) & 1

    if not cs:
        print("SKIP: Crypto not supported")
        return True

    print(f"PASS: Crypto supported (CAP.CS=1)")

    # Verify crypto register region is accessible
    crypto_base = ufs_bar + 0x1000
    try:
        crypto_cap = mem_read(crypto_base, size=4)
        print(f"PASS: Crypto registers accessible: 0x{crypto_cap:08X}")
    except Exception as e:
        print(f"FAIL: Cannot access crypto registers: {e}")
        return False

    # Verify 32 config slots available
    # Verify AES-XTS support
    # NOTE: Exact register layout per HAS crypto section

    print("NOTE: Full crypto validation requires HAS-specific register checks")
    return True
```

---

## Common Issues and Debug

### Issue 1: No Device Detected (HCS.DP = 0)

**Symptoms**:
- HCS.DP bit is 0
- UFS device not enumerated in OS

**Root Causes**:
- UFS card not inserted (for removable slots)
- UFS device power rail not enabled (VCC 2.5V, VCCQ 1.2V)
- UFS_GPIO_RESET_B stuck low (device held in reset)
- Reference clock (38.4 MHz) not provided
- BIOS statically disabled UFS function

**Debug Steps**:
1. Check physical UFS card insertion
2. Verify VCC (2.5V) and VCCQ (1.2V) power rails
3. Check UFS_GPIO_RESET_B signal (should be high for normal operation)
4. Verify REF_CLK (38.4 MHz) is enabled via BIOS register 0x385C
5. Coordinate with @FV-PM-SOUTH to verify UFS power domain state
6. Check BIOS setting for UFS enable/disable

---

### Issue 2: UIC Not Ready (HCS.UCRDY = 0)

**Symptoms**:
- HCS.UCRDY bit remains 0 after HCE=1
- UIC commands fail or timeout

**Root Causes**:
- Reference clock not provided to UFS PHY
- PHY SRAM firmware not loaded
- Controller not properly initialized
- PGA fuses not loaded (NVL: 1,280 fuses for M-PHY G5)

**Debug Steps**:
1. Verify UFS reference clock enabled (BIOS 0x385C)
2. Check PHY SRAM load status via IOSF-SB port 0xFC21
3. Try full controller reset (HCE 1->0->1 sequence)
4. Check UECPA/UECDL/UECN/UECT error registers for UIC errors
5. Verify fuse loading via REQFUSES (0xB8) sideband message completion

---

### Issue 3: Gear Switch Fails

**Symptoms**:
- Gear remains at HS-G1 after switch attempt
- UPMCRS stuck in non-zero state
- UIC errors after gear change

**Root Causes**:
- Device doesn't support target gear (check descriptor)
- PHY calibration failure (NVL: G5 requires extensive PGA fuse calibration)
- Incorrect HS Series configuration (A vs. B)
- PLL lock failure at target frequency

**Debug Steps**:
1. Read device max gear support via descriptor
2. Check UECPA (PHY Adapter error) register
3. Try intermediate gears (G1->G2->G3->G4->G5 instead of direct)
4. Verify HS Series B for G3+ gears
5. Check PLL lock status (NVL: 9,984 MHz for Rate A G5 or 11,673.6 MHz for Rate B G5)

---

### Issue 4: Hibernate Exit Timeout

**Symptoms**:
- DME_HIBERNATE_EXIT command doesn't complete
- Controller appears hung after DeepSleep

**Root Causes**:
- Power rail didn't turn back on (VCC/VCCQ)
- PGCB sequence stuck (NVL: check PGCB state machine at 2.56 MHz clock)
- Device firmware bug
- PMC didn't send wake signal (NVL: check PMC -> PGCB handshake)

**Debug Steps**:
1. Measure UFS power rail voltage during exit
2. Check PGCB state via PGA sideband registers (port 0xFC20)
3. Try Sleep instead of DeepSleep
4. Check device firmware version for known bugs
5. Verify PMC handshake (NVL: ForcePwrGatePOK and wake flow)

---

### Issue 5: UIC Command Timeout

**Symptoms**:
- UCCS interrupt never fires
- UIC_CMD register doesn't clear

**Root Causes**:
- UIC layer hung
- Device not responding
- Interrupt routing issue (NVL: IOSF-SB Assert_IRQn/Deassert_IRQn to ITSS)

**Debug Steps**:
1. Check interrupt enable register (IE)
2. Poll IS register instead of waiting for interrupt
3. Try UIC reset (DME_RESET command)
4. Check interrupt routing (NVL: SB message path to ITSS via RS0)
5. Verify BME (Bus Master Enable) is set - NVL blocks upstream traffic at bridge when BME=0

---

### Issue 6: NVL MCQ Not Working

**Symptoms**:
- MCQ registers return unexpected values
- Queue operations fail
- Legacy UTP mode works but MCQ mode doesn't

**Root Causes**:
- MCQ not enabled in BIOS configuration
- Incorrect MCQ register offset programming
- MCQ interrupt routing misconfigured

**Debug Steps**:
1. Verify MCQ register region accessible at BAR0 + 0x2000
2. Check BIOS MCQ enable settings
3. Verify MCQ SQDAO/CQDAO offset programming per HAS table
4. Check MCQ interrupt status registers

---

### Issue 7: NVL Crypto Not Functional

**Symptoms**:
- Encrypted I/O fails or returns errors
- Crypto config slots not programmable

**Root Causes**:
- Inline encryption not enabled in BIOS (0x600 bit 30)
- Crypto keys lost during power gate (check AON well)
- CAP.CS = 0 (crypto support disabled)

**Debug Steps**:
1. Verify BIOS enabled inline encryption (offset 0x600 bit 30)
2. Check CAP.CS bit
3. Verify crypto register region at BAR0 + 0x1000
4. Check if keys survived power gate (AON well preservation)

---

## NVL PGCB Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| **ISOLLATCH_NOSR_EN** | 0 | Standard isolation latch |
| **USE_DFX_SEQ** | 1 | Use DFx sequence |
| **UNGATE_TIMER** | 2'b10 (32 clocks) | 32 PGCB clock cycles for ungate |

### CDC (Clock Domain Crossing) Domains

| Domain | Clock | Purpose |
|--------|-------|---------|
| **IOSFPrim** | 400 MHz | IOSF Primary interface |
| **IOSFSB** | 100 MHz | IOSF Sideband interface |
| **AXI** | 400 MHz | Internal AXI data path |
| **XSOC** | 38.4 MHz | Cross-SoC domain |

---

## Verification Checklist

Use this checklist for comprehensive UFS validation:

- [ ] **Controller Enumeration**
  - [ ] Vendor ID = 0x8086 (Intel)
  - [ ] Device ID matches platform HAS (NVL: 0xD335)
  - [ ] Class Code = 0x010901
  - [ ] BDF correct (NVL: B0:D23:F0)
  - [ ] BAR0 allocated and valid (32KB for NVL)
  - [ ] Power state D0

- [ ] **Capabilities Validation**
  - [ ] Transfer slots (NUTRS) >= 1
  - [ ] UFSHCI version matches expected (NVL: 4.x)
  - [ ] Lane count = 2 (typical)
  - [ ] Crypto support (CAP.CS) = 1 if expected
  - [ ] Auto-H8 support

- [ ] **Link Startup**
  - [ ] HCS.DP = 1 (device present)
  - [ ] HCS.UCRDY = 1 (UIC ready)
  - [ ] DME_LINKSTARTUP succeeds

- [ ] **Gear Switching**
  - [ ] HS-G1 negotiation successful
  - [ ] HS-G2/G3/G4 switching (per device capability)
  - [ ] HS-G5 switching (NVL UFS 4.0)
  - [ ] PWM mode functional (optional)

- [ ] **MCQ Validation (NVL)**
  - [ ] MCQ registers accessible at BAR0 + 0x2000
  - [ ] 8 SQ/CQ pairs programmable
  - [ ] MCQ doorbell operations functional
  - [ ] MCQ interrupt delivery working

- [ ] **Crypto Validation (NVL)**
  - [ ] Crypto registers accessible at BAR0 + 0x1000
  - [ ] AES-XTS 128-bit key config works
  - [ ] AES-XTS 256-bit key config works
  - [ ] 32 config slots accessible
  - [ ] Keys preserved across power gate (AON well)

- [ ] **Power Management**
  - [ ] Hibernate entry/exit (Sleep)
  - [ ] Hibernate entry/exit (DeepSleep)
  - [ ] D0i3 entry/exit (NVL: partial, no Vnn removal)
  - [ ] RTD3 flow (per Chassis spec)
  - [ ] Auto-H8 idle timer functional
  - [ ] PGCB power gate/ungate sequence (NVL)
  - [ ] S0ix integration (flows G/H)

- [ ] **Device Attributes**
  - [ ] Manufacturer ID readable
  - [ ] UFS version readable
  - [ ] Descriptor queries functional

- [ ] **Error Handling**
  - [ ] UIC errors logged and cleared
  - [ ] Timeout recovery tested
  - [ ] DO_SERR to IEH for SMI (NVL)

- [ ] **NVL Platform-Specific**
  - [ ] IOSF sideband messages working (IP_ready, ResetPrep, etc.)
  - [ ] Reference clock 38.4 MHz verified
  - [ ] Fuse loading complete (1,280 PGA fuses)
  - [ ] VT-d address translation working
  - [ ] BME blocking behavior verified

---

## Related Skills

- **@fv-storage** (parent): General storage architecture and coordination
- **@fv-storage/sata**: SATA/AHCI controller validation
- **@pysv**: PythonSV register access for all examples above
- **@FV-PM-SOUTH**: PCH power management, UFS power rail control
- **@onebkc**: BIOS version lookup
- **@hsdes**: Search for UFS sightings and known issues
- **@TTK3**: Platform power control for hung controller recovery

---

**Ready to assist with UFS validation, debug, and test development across Intel Client platforms!**
