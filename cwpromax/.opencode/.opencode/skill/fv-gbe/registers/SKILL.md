---
name: fv-gbe/registers
description: "Intel GbE MMIO/PCI register map — key CSRs for I219 and I226/I225, PythonSV access patterns, and register checkout procedures for post-silicon validation."
disable: false
---

# Skill: fv-gbe/registers

## Overview

This skill provides the GbE register map for Intel I219 (e1000e family) and I226/I225 (igc family). Registers are accessed via BAR0 MMIO. PCI config space registers are accessed via PCI standard offsets.

---

## I219 Key MMIO Registers (BAR0 Base + Offset)

### Control and Status

| Register | Offset | Key Bits | Description |
|----------|--------|----------|-------------|
| CTRL | 0x0000 | [6]=SLU, [26]=RST, [31]=PHY_RST | Device Control |
| STATUS | 0x0008 | [0]=LU, [1]=FD, [7:6]=SPEED | Device Status |
| CTRL_EXT | 0x0018 | [22:21]=LINK_MODE | Extended Control |
| MDIC | 0x0020 | [20]=R, [26]=W, [28]=RDY | MDI Control (PHY access) |
| FCAL | 0x0028 | — | Flow Control Address Low |
| FCAH | 0x002C | — | Flow Control Address High |
| FCT | 0x0030 | — | Flow Control Type |
| FCTTV | 0x0170 | — | Flow Control Transmit Timer Value |

### Receive Registers

| Register | Offset | Key Bits | Description |
|----------|--------|----------|-------------|
| RCTL | 0x0100 | [1]=EN, [4]=MPE, [15]=BAM, [25:16]=BSIZE | Receive Control |
| RDBAL | 0x2800 | — | Receive Descriptor Base Low (Queue 0) |
| RDBAH | 0x2804 | — | Receive Descriptor Base High (Queue 0) |
| RDLEN | 0x2808 | — | Receive Descriptor Ring Length |
| RDH | 0x2810 | — | Receive Descriptor Head |
| RDT | 0x2818 | — | Receive Descriptor Tail |
| RXDCTL | 0x2828 | [25]=ENABLE | Receive Descriptor Control |
| RFCTL | 0x5008 | [15]=EXSTEN | Receive Filter Control |

### Transmit Registers

| Register | Offset | Key Bits | Description |
|----------|--------|----------|-------------|
| TCTL | 0x0400 | [1]=EN, [3]=PSP | Transmit Control |
| TDBAL | 0x3800 | — | Transmit Descriptor Base Low (Queue 0) |
| TDBAH | 0x3804 | — | Transmit Descriptor Base High (Queue 0) |
| TDLEN | 0x3808 | — | Transmit Descriptor Ring Length |
| TDH | 0x3810 | — | Transmit Descriptor Head |
| TDT | 0x3818 | — | Transmit Descriptor Tail |
| TXDCTL | 0x3828 | [25]=ENABLE | Transmit Descriptor Control |

### Interrupt Registers

| Register | Offset | Description |
|----------|--------|-------------|
| ICR | 0x00C0 | Interrupt Cause Read (clear on read) |
| ICS | 0x00C8 | Interrupt Cause Set |
| IMS | 0x00D0 | Interrupt Mask Set/Read |
| IMC | 0x00D8 | Interrupt Mask Clear |
| IVAR0 | 0x00E4 | Interrupt Vector Allocation |

### Statistics Registers (Selected)

| Register | Offset | Description |
|----------|--------|-------------|
| CRCERRS | 0x4000 | CRC Error Count |
| RNBC | 0x40A0 | Receive No Buffers Count |
| GPRC | 0x4074 | Good Packets Received Count |
| GPTC | 0x4080 | Good Packets Transmitted Count |
| TORL | 0x40C0 | Total Octets Received (Low) |
| TORH | 0x40C4 | Total Octets Received (High) |
| TOTL | 0x40C8 | Total Octets Transmitted (Low) |
| TOTH | 0x40CC | Total Octets Transmitted (High) |
| TPR | 0x40D0 | Total Packets Received |
| TPT | 0x40D4 | Total Packets Transmitted |

### NVM/PHY Registers

| Register | Offset | Key Bits | Description |
|----------|--------|----------|-------------|
| EECD | 0x0010 | [6]=FWE, [7]=PRES | EEPROM/Flash Control |
| EEMNGCTL | 0x1010 | [20]=CFG_DONE | Management Controller NVM Control |
| MDICNFG | 0x0E04 | [7:0]=PHY_ADDR | MDI Config |

---

## I226 / I225 Key MMIO Registers

The I226/I225 uses a similar register layout to I219 but with extensions for 2.5G operation.

### Additional / Different Registers

| Register | Offset | Description |
|----------|--------|-------------|
| CTRL | 0x0000 | Device Control (same layout, different bits) |
| STATUS | 0x0008 | Device Status — SPEED field encodes 2.5G |
| CTRL_EXT | 0x0018 | Extended control |
| MDIC | 0x0020 | MDI Control (PHY is internal — may use MDICNFG) |
| EEER | 0x0E30 | EEE Register |
| I2CCMD | 0x1028 | I2C Command Register (for SFP/PHY config) |

**STATUS register SPEED encoding (I226):**
- `00b` = 10 Mbps
- `01b` = 100 Mbps
- `10b` = 1000 Mbps
- `11b` = 2500 Mbps *(I226/I225 specific)*

---

## PCI Config Space Registers

| Register | Offset | Description |
|----------|--------|-------------|
| VID | 0x00 | Vendor ID = 0x8086 |
| DID | 0x02 | Device ID (platform specific) |
| COMMAND | 0x04 | [1]=MEMORY_SPACE, [2]=BUS_MASTER |
| STATUS | 0x06 | PCI Status |
| CLASS_CODE | 0x09 | = 0x020000 |
| BAR0 | 0x10 | MMIO Base (32-bit, bit 0=0) |
| PMCSR | 0xCC | Power State [1:0] |
| MSI_CTRL | varies | MSI capability |
| PCIE_CAP | varies | PCIe capability |
| DEVCTL | varies | [5:3]=MaxPayload, [14:12]=MaxReadReq |
| LNKSTA | varies | [3:0]=LinkSpeed, [9:4]=LinkWidth |

---

## PythonSV Register Checkout

### Setup and Discovery

```python
# Discover I219 at 00:1F.6
# Named node on MTL/LNL (example — may differ by platform)
gbe = sv.socket0.pcieB0D31F6

# Verify device identity
vid = gbe.vid.read()    # Should be 0x8086
did = gbe.did.read()    # Platform-specific
print(f"GbE: VID={vid:#06x} DID={did:#06x}")
```

### MMIO Register Access

```python
# Read BAR0 base address
bar0_raw = gbe.bar0.read()
bar0_base = bar0_raw & ~0xF   # Mask off type/prefetch bits
print(f"BAR0 base: {bar0_base:#010x}")

# Read STATUS register (MMIO)
status = itp.mem.read(bar0_base + 0x0008, 4)
link_up = (status >> 1) & 1
speed_bits = (status >> 6) & 3
speed_map = {0: "10M", 1: "100M", 2: "1G", 3: "2.5G"}
print(f"Link: {'UP' if link_up else 'DOWN'}, Speed: {speed_map[speed_bits]}")

# Read CTRL register
ctrl = itp.mem.read(bar0_base + 0x0000, 4)
slu = (ctrl >> 6) & 1
print(f"CTRL.SLU (Set Link Up): {slu}")
```

### Batch Register Checkout

```python
def gbe_register_checkout(base):
    """Quick GbE register health check."""
    registers = {
        "CTRL":     (0x0000, None),
        "STATUS":   (0x0008, None),
        "CTRL_EXT": (0x0018, None),
        "RCTL":     (0x0100, None),
        "TCTL":     (0x0400, None),
        "CRCERRS":  (0x4000, 0),    # Should be 0
        "GPRC":     (0x4074, None),
        "GPTC":     (0x4080, None),
    }
    print(f"{'Register':<12} {'Offset':<8} {'Value':<12} {'Status'}")
    print("-" * 50)
    for name, (offset, expected) in registers.items():
        val = itp.mem.read(base + offset, 4)
        status = "OK" if expected is None else ("OK" if val == expected else f"FAIL (exp {expected})")
        print(f"{name:<12} {offset:#08x} {val:#012x} {status}")

# Run checkout
gbe_register_checkout(bar0_base)
```

### Checking PHY via MDIC

```python
# Read PHY register via MDI (indirect access through MDIC register)
def read_phy_reg(base, phy_addr, reg_addr):
    """Read PHY register via MDIC."""
    mdic_cmd = (reg_addr << 16) | (phy_addr << 21) | (1 << 27)  # Read command
    itp.mem.write(base + 0x0020, 4, mdic_cmd)
    # Poll for ready
    import time
    for _ in range(100):
        mdic = itp.mem.read(base + 0x0020, 4)
        if (mdic >> 28) & 1:  # RDY bit
            return mdic & 0xFFFF
        time.sleep(0.001)
    raise TimeoutError("MDIC read timeout")

# Read PHY ID registers
phy_id1 = read_phy_reg(bar0_base, 1, 2)
phy_id2 = read_phy_reg(bar0_base, 1, 3)
print(f"PHY ID1: {phy_id1:#06x}, ID2: {phy_id2:#06x}")

# Read PHY Status register (register 1)
phy_status = read_phy_reg(bar0_base, 1, 1)
link_up = (phy_status >> 2) & 1
print(f"PHY Link: {'UP' if link_up else 'DOWN'}")
```

---

## Common Register Checkout Failures

| Register | Unexpected Value | Meaning |
|----------|-----------------|---------|
| STATUS [1:0] = 0 | Link down | PHY not initialized → `/skill fv-gbe/phy-bringup` |
| CTRL.RST = 1 | MAC stuck in reset | Driver not completing initialization |
| RCTL.EN = 0 | RX disabled | Driver not enabling RX path |
| TCTL.EN = 0 | TX disabled | Driver not enabling TX path |
| CRCERRS != 0 | CRC errors | Cable or PHY integrity issue |
| BAR0 = 0x00 | MMIO not allocated | PCI enumeration failure |
| PMCSR [1:0] = 3 | Device in D3 | Device not powered up by driver |
