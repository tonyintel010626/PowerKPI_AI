---
name: fv-lpss/config-checkout
description: "Verify LPSS IP enumeration, register configuration, and pad mode routing on Novalake"
---

# LPSS Configuration Checkout — Novalake (NVL)

Comprehensive configuration verification for LPSS controllers: PCI enumeration, register values, and GPIO pad mode (PMode) routing.

> **Scope:** I2C, I3C, SPI, UART controllers only. GPIO is a separate domain.

---

## Part 1 — PCI Enumeration & BAR Assignment

### NVL PCH-S LPSS Device Map (14 PCI Functions)

*Sources: `NVL_PCH_S_LPSS_Integration_HAS.html`, `Chap06_NVP-S_RegMaps.html`*

| Controller | BDF (Bus 0) | Device ID | BAR Size | Class Code |
|-----------|-------------|-----------|----------|------------|
| I2C0 | Dev 21, Fn 0 | 0x6E4C | 4 KB | 0x0C8000 |
| I2C1 | Dev 21, Fn 1 | 0x6E4D | 4 KB | 0x0C8000 |
| I2C2 | Dev 21, Fn 2 | 0x6E4E | 4 KB | 0x0C8000 |
| I2C3 | Dev 21, Fn 3 | 0x6E4F | 4 KB | 0x0C8000 |
| I2C4 | Dev 25, Fn 0 | 0x6E7A | 4 KB | 0x0C8000 |
| I2C5 | Dev 25, Fn 1 | 0x6E7B | 4 KB | 0x0C8000 |
| I3C Ctrl#1 (I3C0/I3C1) | Dev 19, Fn 0 | 0x6E2C | 8 KB | 0x0C8000 |
| I3C Ctrl#2 (I3C2/I3C3) | Dev 19, Fn 1 | 0x6E2D | 8 KB | 0x0C8000 |
| SPI0 | Dev 30, Fn 2 | 0x6E2A | 4 KB | 0x0C8000 |
| SPI1 | Dev 30, Fn 3 | 0x6E2B | 4 KB | 0x0C8000 |
| SPI2 | Dev 30, Fn 4 | 0x6E5E | 4 KB | 0x0C8000 |
| UART0 | Dev 30, Fn 0 | 0x6E28 | 4 KB | 0x070002 |
| UART1 | Dev 30, Fn 1 | 0x6E29 | 4 KB | 0x070002 |
| UART2 | Dev 25, Fn 2 | 0x6E5C | 4 KB | 0x070002 |

> **Notes:**
> - PCH-S has single DID per controller (no PCD-P/PCD-H variant — `0x6Exx` series only).
> - I3C controllers use **Dev 19** (vs Dev 17 on PCD); SPI2 at **Dev 30, Fn 4** (vs Dev 18, Fn 6 on PCD).
> - I3C Ctrl#2 at **Fn 1** (sequential — no function gap, unlike PCD which has a gap at Fn 2).
> - I3C controllers have **8 KB BAR** (2 instances per controller); all others have 4 KB BAR.
> - All controllers support D0/D3hot/D3cold power states, PMCSR at PCI config offset 0x84.

### NVL PCD LPSS Device Map (14 PCI Functions) — PCD-H and PCD-P Variants

*Sources: `NVL_PCD_H_LPSS_Integration_HAS.html`, `NVL_PCD_RegMaps.html`*

> **IMPORTANT:** NVL PCD has **two DID variants** — PCD-P (`0xD2xx` series) and PCD-H (`0xD3xx` series). BDFs are identical between variants; only DIDs differ. Always verify which variant your silicon is before validating Device IDs.

| Controller | BDF (Bus 0) | DID (PCD-H) | DID (PCD-P) | BAR Size | Class Code |
|-----------|-------------|-------------|-------------|----------|------------|
| I2C0 | Dev 21, Fn 0 | 0xD378 | 0xD278 | 4 KB | 0x0C8000 |
| I2C1 | Dev 21, Fn 1 | 0xD379 | 0xD279 | 4 KB | 0x0C8000 |
| I2C2 | Dev 21, Fn 2 | 0xD37A | 0xD27A | 4 KB | 0x0C8000 |
| I2C3 | Dev 21, Fn 3 | 0xD37B | 0xD27B | 4 KB | 0x0C8000 |
| I2C4 | Dev 25, Fn 0 | 0xD350 | 0xD250 | 4 KB | 0x0C8000 |
| I2C5 | Dev 25, Fn 1 | 0xD351 | 0xD251 | 4 KB | 0x0C8000 |
| I3C Ctrl#1 (I3C0/I3C1) | Dev 17, Fn 0 | 0xD37C | 0xD27C | 8 KB | 0x0C8000 |
| I3C Ctrl#2 (I3C2/I3C3) | Dev 17, Fn 2 | 0xD36F | 0xD26F | 8 KB | 0x0C8000 |
| SPI0 | Dev 30, Fn 2 | 0xD327 | 0xD227 | 4 KB | 0x0C8000 |
| SPI1 | Dev 30, Fn 3 | 0xD330 | 0xD230 | 4 KB | 0x0C8000 |
| SPI2 | Dev 18, Fn 6 | 0xD347 | 0xD247 | 4 KB | 0x0C8000 |
| UART0 | Dev 30, Fn 0 | 0xD325 | 0xD225 | 4 KB | 0x070002 |
| UART1 | Dev 30, Fn 1 | 0xD326 | 0xD226 | 4 KB | 0x070002 |
| UART2 | Dev 25, Fn 2 | 0xD352 | 0xD252 | 4 KB | 0x070002 |

> **Notes:**
> - PCD-H has 3 SPI (SPI0-2) and 3 UART (UART0-2) controllers, same count as PCH-S but with different BDFs and Device IDs.
> - SPI0/SPI1 and UART0/UART1 are at Dev 30 (same device number as PCH-S) while SPI2 (Dev 18, Fn 6) and UART2 (Dev 25, Fn 2) have unique PCD BDF assignments.
> - I3C Ctrl#2 is at Dev 17, **Fn 2** (NOT Fn 1) — note the function number gap.
> - I3C controllers have **8 KB BAR** (2 instances per controller); all others have 4 KB BAR.
> - All controllers support D0/D3hot/D3cold power states, PMCSR at PCI config offset 0x84.

### PCI Configuration Space Reference

| Offset | Field | Description |
|--------|-------|-------------|
| 0x00 | Vendor ID | Should be 0x8086 (Intel) |
| 0x02 | Device ID | See tables above |
| 0x04 | Command Register | Bit 1 = Memory Space Enable, Bit 2 = Bus Master Enable |
| 0x08 | Revision ID | Silicon stepping |
| 0x09 | Class Code | 0x0C80xx (Serial Bus) or 0x0700xx (UART) |
| 0x10 | BAR0 | Memory-mapped MMIO base address |
| 0x80 | POWERCAPID | PM Capability ID (start of PM capability structure) |
| 0x84 | PMCSR (PMECTRLSTATUS) | Power Management Control/Status — POWERSTATE[1:0], PMEENABLE, PMESTATUS |
| 0xA0 | D0I3_MAX_POW_LAT_PG_CONFIG | D0i3/Power Gating enables — PMCRE(16), DEVIDLEN(17), D3HEN(18), SLEEP_EN(19), HAE(21) |

### PythonSV Enumeration Check — NVL PCD-H

```python
import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()

lpss_devices = {
    # I2C controllers (6)
    "I2C0": {"path": "namednodes.sv.socket0.pcd.lpss.i2c0.cfg", "expected_did": 0xD378},
    "I2C1": {"path": "namednodes.sv.socket0.pcd.lpss.i2c1.cfg", "expected_did": 0xD379},
    "I2C2": {"path": "namednodes.sv.socket0.pcd.lpss.i2c2.cfg", "expected_did": 0xD37A},
    "I2C3": {"path": "namednodes.sv.socket0.pcd.lpss.i2c3.cfg", "expected_did": 0xD37B},
    "I2C4": {"path": "namednodes.sv.socket0.pcd.lpss.i2c4.cfg", "expected_did": 0xD350},
    "I2C5": {"path": "namednodes.sv.socket0.pcd.lpss.i2c5.cfg", "expected_did": 0xD351},
    # I3C controllers (2 PCI functions, 4 instances)
    "I3C_Ctrl1": {"path": "namednodes.sv.socket0.pcd.lpss.i3c0.cfg", "expected_did": 0xD37C},
    "I3C_Ctrl2": {"path": "namednodes.sv.socket0.pcd.lpss.i3c1.cfg", "expected_did": 0xD36F},
    # SPI controllers (3)
    "SPI0": {"path": "namednodes.sv.socket0.pcd.lpss.spi0.cfg", "expected_did": 0xD327},
    "SPI1": {"path": "namednodes.sv.socket0.pcd.lpss.spi1.cfg", "expected_did": 0xD330},
    "SPI2": {"path": "namednodes.sv.socket0.pcd.lpss.spi2.cfg", "expected_did": 0xD347},
    # UART controllers (3) — note: PythonSV uses 'hsuart' naming
    "UART0": {"path": "namednodes.sv.socket0.pcd.lpss.hsuart0.cfg", "expected_did": 0xD325},
    "UART1": {"path": "namednodes.sv.socket0.pcd.lpss.hsuart1.cfg", "expected_did": 0xD326},
    "UART2": {"path": "namednodes.sv.socket0.pcd.lpss.hsuart2.cfg", "expected_did": 0xD352},
}
# NOTE: DIDs above are for PCD-H variant (0xD3xx). PCD-P uses 0xD2xx series
# (e.g., SPI0=0xD227, SPI1=0xD230, UART0=0xD225, UART1=0xD226, etc.)

print("=== NVL PCD-H LPSS Enumeration Check ===\n")
for name, info in lpss_devices.items():
    cfg = eval(info["path"])
    vid = cfg.vendor_id.read()
    did = cfg.device_id.read()
    bar0 = cfg.bar0.read()
    cmd = cfg.command.read()
    
    status = "✅" if (vid == 0x8086 and did == info["expected_did"]) else "❌"
    bar_ok = "✅" if (bar0 != 0 and bar0 != 0xFFFFFFFF) else "❌"
    mse = "ON" if (cmd & 0x02) else "OFF"
    bme = "ON" if (cmd & 0x04) else "OFF"
    
    print(f"{status} {name}: VID=0x{vid:04X} DID=0x{did:04X} (expected 0x{info['expected_did']:04X})")
    print(f"   {bar_ok} BAR0=0x{bar0:08X}  MSE={mse}  BME={bme}")
```

### PythonSV Enumeration Check — NVL PCH-S

```python
lpss_devices_pchs = {
    "I2C0": {"path": "namednodes.sv.socket0.pch.lpss.i2c0.cfg", "expected_did": 0x6E4C},
    "I2C1": {"path": "namednodes.sv.socket0.pch.lpss.i2c1.cfg", "expected_did": 0x6E4D},
    "I2C2": {"path": "namednodes.sv.socket0.pch.lpss.i2c2.cfg", "expected_did": 0x6E4E},
    "I2C3": {"path": "namednodes.sv.socket0.pch.lpss.i2c3.cfg", "expected_did": 0x6E4F},
    "I2C4": {"path": "namednodes.sv.socket0.pch.lpss.i2c4.cfg", "expected_did": 0x6E7A},
    "I2C5": {"path": "namednodes.sv.socket0.pch.lpss.i2c5.cfg", "expected_did": 0x6E7B},
    "I3C_Ctrl1": {"path": "namednodes.sv.socket0.pch.lpss.i3c0.cfg", "expected_did": 0x6E2C},
    "I3C_Ctrl2": {"path": "namednodes.sv.socket0.pch.lpss.i3c1.cfg", "expected_did": 0x6E2D},
    "SPI0": {"path": "namednodes.sv.socket0.pch.lpss.spi0.cfg", "expected_did": 0x6E2A},
    "SPI1": {"path": "namednodes.sv.socket0.pch.lpss.spi1.cfg", "expected_did": 0x6E2B},
    "SPI2": {"path": "namednodes.sv.socket0.pch.lpss.spi2.cfg", "expected_did": 0x6E5E},
    "UART0": {"path": "namednodes.sv.socket0.pch.lpss.hsuart0.cfg", "expected_did": 0x6E28},
    "UART1": {"path": "namednodes.sv.socket0.pch.lpss.hsuart1.cfg", "expected_did": 0x6E29},
    "UART2": {"path": "namednodes.sv.socket0.pch.lpss.hsuart2.cfg", "expected_did": 0x6E5C},
}
# Same enumeration loop as PCD-H above
```

### PCICFGCTRL Offsets (PMC Sideband — HAS-Verified)

PMC uses PCICFGCTRL registers to assign Device IDs and control PCI function visibility. These offsets are used in sideband `setIDValue` messages.

**MTL/LNL/PTL/WCL/NVL:**

| Controller | PCICFGCTRL Offset | Notes |
|-----------|------------------|-------|
| I2C0 | 0x200 | |
| I2C1 | 0x204 | |
| I2C2 | 0x208 | |
| I2C3 | 0x20C | |
| I2C4 | 0x210 | |
| I2C5 | 0x214 | |
| UART0 | 0x218 | |
| UART1 | 0x21C | |
| UART2 | 0x220 | |
| SPI0 | 0x224 | |
| SPI1 | 0x228 | |
| SPI2 | 0x22C | |
| I3C0/I3C1 | 0x230 | Shared controller #1 |
| I3C2/I3C3 | 0x234 | Shared controller #2 |

**MTP-S (different — has UART3 and SPI3):**

| Controller | PCICFGCTRL Offset | Notes |
|-----------|------------------|-------|
| I2C0–I2C5 | 0x200–0x214 | Same as above |
| UART0–UART2 | 0x218–0x220 | Same as above |
| UART3 | 0x224 | MTP-S only |
| SPI0 | 0x228 | Shifted! |
| SPI1 | 0x22C | Shifted! |
| SPI2 | 0x230 | Shifted! |
| SPI3 | 0x234 | MTP-S only |
| I3C0/I3C1 | 0x238 | Shifted! |

> **Note:** Device IDs are set dynamically via PMC `setIDValue` sideband messages — they are NOT in the IP-level HAS. VendorID `0x8086` is hardcoded in RTL.

---

### BAR Configuration Rules (HAS-Verified)

| BAR | Size | Type | Usage |
|-----|------|------|-------|
| BAR0 | 4 KB | 64-bit MMIO | Primary register space (controller + DMA + convergence layer) |
| BAR1 | 4 KB | 64-bit MMIO | Alias of PCI config space (ACPI mode access) |

> **CRITICAL BAR1 Rule:** A BAR1 **read MUST follow every write** to BAR1 — failure to do so can hang the IOSF bridge. This is because BAR1 maps to PCI config space which has different ordering semantics.

**I3C BAR Exception:**
- I3C controllers have an **8 KB BAR** (not 4 KB) because each PCI function hosts 2 I3C instances
- Bus#0 registers at offset 0x000, Bus#1 at offset 0x400

**Fixed Address Region (FAR):**
- FAR = 4 MB at physical address `0x80000_0000_FF000_0000` (fixed, outside Host Physical Address space)
- Used for sideband-routed MMIO access
- VT-D compliant (v1.x), no P2P support

---

### Complete Address Map (HAS-Verified)

**MTL/LNL/PTL/WCL/NVL:**

| Port# | Controller | ConnID (Hex) | FAR Address Range | BAR Size |
|--------|-----------|-------------|-------------------|----------|
| 0 | I2C0 | 0x0 | 0xFF00_0XXX | 4 KB |
| 1 | I2C1 | 0x1 | 0xFF00_1XXX | 4 KB |
| 2 | I2C2 | 0x2 | 0xFF00_2XXX | 4 KB |
| 3 | I2C3 | 0x3 | 0xFF00_3XXX | 4 KB |
| 4 | I2C4 | 0x4 | 0xFF00_4XXX | 4 KB |
| 5 | I2C5 | 0x5 | 0xFF00_5XXX | 4 KB |
| 6 | UART0 | 0x6 | 0xFF00_8XXX | 4 KB |
| 7 | UART1 | 0x7 | 0xFF00_9XXX | 4 KB |
| 8 | UART2 | 0x8 | 0xFF00_AXXX | 4 KB |
| 9 | SPI0 | 0x9 | 0xFF00_CXXX | 4 KB |
| 10 | SPI1 | 0xA | 0xFF00_DXXX | 4 KB |
| 11 | SPI2 | 0xB | 0xFF00_EXXX | 4 KB |
| 12 | I3C0/I3C1 | 0xC | 0xFF01_0XXX / 0xFF01_1XXX | 8 KB |
| 13 | I3C2/I3C3 | 0xD | 0xFF01_2XXX / 0xFF01_3XXX | 8 KB |

**MTP-S differences (Port 8+ shifted):**

| Port# | Controller | ConnID | FAR Address |
|--------|-----------|--------|-------------|
| 8 | UART2 | 0xE | 0xFF00_AXXX |
| 9 | UART3 | 0x8 | 0xFF00_BXXX |
| 10 | SPI0 | 0x9 | 0xFF00_DXXX |
| 11 | SPI1 | 0xA | 0xFF00_EXXX |
| 12 | SPI2 | 0xB | 0xFF00_FXXX |
| 13 | SPI3 | 0xC | 0xFF01_0XXX |
| 14 | I3C0/I3C1 | 0xD | 0xFF01_2XXX / 0xFF01_3XXX |

---

### GPIO Pin Assignments (HAS-Verified)

> **Note:** These are the LPSS-side signal names from the HAS. Actual GPIO pad names (GPP_xxx) come from the platform GPIO HAS — always cross-reference.

**I2C Signals (per instance, 5 pins):**

| Signal | Direction | Description |
|--------|-----------|-------------|
| i2c_sda | Bidir | Serial Data |
| i2c_scl | Bidir | Serial Clock |
| i2c_sda_aux | Bidir | Auxiliary SDA (FM+ only, optional) |
| i2c_wake | Output | Wake signal (optional) |
| i2c_clk_loopback | Input | Clock loopback (test, optional) |

**UART Signals (per instance, 4 pins):**

| Signal | Direction | Description |
|--------|-----------|-------------|
| uart_txd | Output | Transmit Data |
| uart_rxd | Input | Receive Data |
| uart_rts_n | Output | Request To Send (active low) |
| uart_cts_n | Input | Clear To Send (active low) |

**SPI Signals (per instance, 7 pins):**

| Signal | Direction | Description |
|--------|-----------|-------------|
| spi_clk | Output | Serial Clock |
| spi_miso | Input | Master In / Slave Out |
| spi_mosi | Output | Master Out / Slave In |
| spi_cs0_n | Output | Chip Select 0 (active low) |
| spi_cs1_n | Output | Chip Select 1 (active low, deprecated since ADP-P) |
| spi_clk_loopback | Input | Clock loopback (test) |
| spi_rx_clk | Input | Delayed RX clock (optional) |

**I3C Signals (per controller = 2 instances, 8 pins):**

| Signal | Direction | Description |
|--------|-----------|-------------|
| i3c_bus0_sda | Bidir | Bus #0 Serial Data |
| i3c_bus0_scl | Bidir | Bus #0 Serial Clock |
| i3c_bus1_sda | Bidir | Bus #1 Serial Data |
| i3c_bus1_scl | Bidir | Bus #1 Serial Clock |
| i3c_bus0_clk_loopback | Input | Bus #0 clock loopback (2x buffer) |
| i3c_bus1_clk_loopback | Input | Bus #1 clock loopback (2x buffer) |
| i3c_bus0_wake | Output | Bus #0 IBI wake (to PMC) |
| i3c_bus1_wake | Output | Bus #1 IBI wake (to PMC) |

---

### Common Enumeration Issues

**Device Not Present (VID = 0xFFFF):**
1. Device fused off — check fuse config via VJT CLTAP
2. BIOS/ACPI disabled the device
3. Device in D3cold — config space inaccessible
4. PCD-H vs PCH-S mismatch (e.g., different Device IDs and some BDF differences between dies)

**BAR Not Assigned (BAR = 0x00000000):**
1. BIOS resource allocation failure
2. Memory Space Enable bit OFF in Command Register
3. Device disabled in BIOS setup

**Device in D3 (intermittent 0xFFFF):**
```python
# Check and fix via PMCSR
pmcsr = cfg.pmcsr.read()
power_state = pmcsr & 0x03
if power_state == 3:
    cfg.pmcsr.write(pmcsr & ~0x03)  # Transition to D0
    import time; time.sleep(0.01)
```

---

## Part 2 — Register Verification

### NVL LPSS PythonSV Access Paths

| Controller | PythonSV Path | Config Space |
|-----------|---------------|-------------|
| I2C0 | `sv.socket0.pcd.lpss.i2c0` | `sv.socket0.pcd.lpss.i2c0.cfg` |
| I2C1 | `sv.socket0.pcd.lpss.i2c1` | `sv.socket0.pcd.lpss.i2c1.cfg` |
| I2C2 | `sv.socket0.pcd.lpss.i2c2` | `sv.socket0.pcd.lpss.i2c2.cfg` |
| I2C3 | `sv.socket0.pcd.lpss.i2c3` | `sv.socket0.pcd.lpss.i2c3.cfg` |
| I2C4 | `sv.socket0.pcd.lpss.i2c4` | `sv.socket0.pcd.lpss.i2c4.cfg` |
| I2C5 | `sv.socket0.pcd.lpss.i2c5` | `sv.socket0.pcd.lpss.i2c5.cfg` |
| I3C Ctrl#1 (I3C0/I3C1) | `sv.socket0.pcd.lpss.i3c0` | `sv.socket0.pcd.lpss.i3c0.cfg` |
| I3C Ctrl#2 (I3C2/I3C3) | `sv.socket0.pcd.lpss.i3c1` | `sv.socket0.pcd.lpss.i3c1.cfg` |
| SPI0 | `sv.socket0.pcd.lpss.spi0` | `sv.socket0.pcd.lpss.spi0.cfg` |
| SPI1 | `sv.socket0.pcd.lpss.spi1` | `sv.socket0.pcd.lpss.spi1.cfg` |
| SPI2 | `sv.socket0.pcd.lpss.spi2` | `sv.socket0.pcd.lpss.spi2.cfg` |
| UART0 (HSUART0) | `sv.socket0.pcd.lpss.hsuart0` | `sv.socket0.pcd.lpss.hsuart0.cfg` |
| UART1 (HSUART1) | `sv.socket0.pcd.lpss.hsuart1` | `sv.socket0.pcd.lpss.hsuart1.cfg` |
| UART2 (HSUART2) | `sv.socket0.pcd.lpss.hsuart2` | `sv.socket0.pcd.lpss.hsuart2.cfg` |

> **Note:** UARTs appear as `hsuart` (High-Speed UART) in PythonSV, not `uart`.
> **Note:** I3C has 4 interfaces but 2 PCI controllers. `i3c0` = Controller#1 (I3C0/I3C1), `i3c1` = Controller#2 (I3C2/I3C3).

### Register Discovery and Inspection

```python
# Search all registers for a controller
i2c0_regs = namednodes.sv.socket0.pcd.lpss.i2c0.search(
    regexpression=".*", searchType="registers"
)
for reg in i2c0_regs:
    print(reg)

# Read a specific register and understand its layout
reg = namednodes.sv.socket0.pcd.lpss.i2c0.cfg.cfg_hi0
val = reg.read()
print(f"Value: {hex(val)}")
print(reg.getspec())  # Shows field layout
```

### I2C Register Checks

```python
i2c0 = namednodes.sv.socket0.pcd.lpss.i2c0

# PCI VID/DID
vid = i2c0.cfg.cfg_hi0.read()
print(f"I2C0 VID/DID: {hex(vid)}")

# Control and status registers
i2c0_ctrl = i2c0.search(regexpression="ctrl|con|enable", searchType="registers")
for reg in i2c0_ctrl:
    print(f"{reg} = {hex(reg.read())}")

i2c0_sts = i2c0.search(regexpression="sts|status", searchType="registers")
for reg in i2c0_sts:
    print(f"{reg} = {hex(reg.read())}")
```

**Key I2C checks:** Control register (master/slave, speed: 100k/400k/1M/3.4M), status (activity, FIFO, errors), clock config (SCL high/low counts), enable, interrupt status/mask.

#### I2C Register Bit-Field Reference (DW_apb_i2c v2.02a)

**IC_CON (0x00) — Control Register:**

| Bits | Field | Values | Description |
|------|-------|--------|-------------|
| [0] | MASTER_MODE | 1=master, 0=slave | Controller role |
| [2:1] | SPEED | 1=standard(100K), 2=fast(400K), 3=high(3.4M) | Bus speed mode |
| [3] | IC_10BITADDR_SLAVE | 1=10-bit, 0=7-bit | Slave address width |
| [4] | IC_10BITADDR_MASTER | 1=10-bit, 0=7-bit | Master addressing mode |
| [5] | IC_RESTART_EN | 1=enable | Allow RESTART conditions |
| [6] | IC_SLAVE_DISABLE | 1=disable slave | Disable slave mode |
| [7] | STOP_DET_IFADDRESSED | Controls STOP_DET when addressed | Slave-mode only |
| [8] | TX_EMPTY_CTRL | 1=controlled generation | TX_EMPTY interrupt behavior |
| [9] | RX_FIFO_FULL_HLD_CTRL | 1=hold bus when RX full | Prevents RX overflow |
| [10] | STOP_DET_IF_MASTER_ACTIVE | 1=issue STOP_DET when master active | Master-mode only |
| [11] | BUS_CLEAR_FEATURE_CTRL | 1=enable bus clear | SDA/SCL stuck recovery |
| [16] | OPTIONAL_SAR_CTRL | 1=enable optional SAR | Additional slave address |
| [17] | SMBUS_SLAVE_QUICK_CMD_EN | 1=enable | SMBus quick command |
| [18] | SMBUS_ARP_EN | 1=enable | SMBus ARP (Address Resolution Protocol) |
| [19] | SMBUS_PERSISTENT_SLV_ADDR_EN | 1=persist | Retain slave address across resets |

**IC_STATUS (0x70) — Status Register (read-only):**

| Bit | Field | Meaning when 1 |
|-----|-------|----------------|
| [0] | ACTIVITY | Bus activity detected |
| [1] | TFNF | TX FIFO not full (can accept data) |
| [2] | TFE | TX FIFO completely empty |
| [3] | RFNE | RX FIFO not empty (data available) |
| [4] | RFF | RX FIFO completely full |
| [5] | MST_ACTIVITY | Master FSM is not idle |
| [6] | SLV_ACTIVITY | Slave FSM is not idle |
| [7] | MST_HOLD_TX_FIFO_EMPTY | Master holds bus — TX FIFO empty |
| [8] | MST_HOLD_RX_FIFO_FULL | Master holds bus — RX FIFO full |
| [9] | SLV_HOLD_TX_FIFO_EMPTY | Slave holds bus — TX FIFO empty |
| [10] | SLV_HOLD_RX_FIFO_FULL | Slave holds bus — RX FIFO full |
| [11] | SDA_STUCK_NOT_RECOVERED | SDA stuck AND bus clear failed |
| [20] | SMBUS_QUICK_CMD_BIT | SMBus R/W bit for quick command |
| [21] | SMBUS_SLAVE_ADDR_VALID | SMBus slave address resolved |
| [22] | SMBUS_SLAVE_ADDR_RESOLVED | ARP address resolved |
| [23] | SMBUS_SUSPEND_STATUS | SMBus SUSPEND asserted |
| [24] | SMBUS_ALERT_STATUS | SMBus ALERT asserted |

**IC_ENABLE (0x6C) — Enable Register:**

| Bit | Field | Description |
|-----|-------|-------------|
| [0] | ENABLE | 1=enable controller, 0=disable (check IC_ENABLE_STATUS after clearing) |
| [1] | ABORT | 1=issue abort (self-clearing). Use when TX FIFO stuck. Generates TX_ABRT interrupt |
| [2] | TX_CMD_BLOCK | 1=block TX commands in slave-mode |
| [3] | SDA_STUCK_RECOVERY_ENABLE | 1=initiate SDA stuck recovery (sends 9 SCL clocks + STOP) |
| [16] | SMBUS_CLK_RESET | 1=reset SMBus clock period counters |
| [17] | SMBUS_SUSPEND_EN | 1=enable SMBus SUSPEND |
| [18] | SMBUS_ALERT_EN | 1=enable SMBus ALERT |

**IC_COMP_PARAM_1 (0xF4) — Hardware Configuration Discovery (read-only):**

This register reveals the **compile-time configuration** of the I2C controller instance. Essential for validating the specific LPSS instantiation on NVL:

| Bits | Field | Meaning |
|------|-------|---------|
| [1:0] | APB_DATA_WIDTH | 0=8-bit, 1=16-bit, 2=32-bit APB bus |
| [3:2] | MAX_SPEED_MODE | 1=standard, 2=fast, 3=high-speed |
| [4] | HC_COUNT_VALUES | 1=programmable SCL counts |
| [5] | INTR_IO | 1=combined interrupt (vs. individual) |
| [6] | HAS_DMA | 1=DMA handshake signals present |
| [7] | ADD_ENCODED_PARAMS | 1=this register (0xF4) is valid |
| [15:8] | RX_BUFFER_DEPTH | RX FIFO depth (actual depth = value) |
| [23:16] | TX_BUFFER_DEPTH | TX FIFO depth (actual depth = value) |

```python
# Hardware capability discovery — run once per controller
def check_i2c_hw_config(port, name="i2c0"):
    """Read IC_COMP_PARAM_1 to discover hardware configuration."""
    try:
        param1 = port.ic_comp_param_1.read()
    except:
        try:
            # Alternate naming in some PythonSV versions
            results = port.search(regexpression="comp_param", searchType="registers")
            if results:
                param1 = results[0].read()
            else:
                print("  Cannot find IC_COMP_PARAM_1 register")
                return
        except:
            print("  Cannot read IC_COMP_PARAM_1 (device may be in D3)")
            return

    apb_width = {0: "8-bit", 1: "16-bit", 2: "32-bit"}.get(param1 & 0x3, "unknown")
    max_speed = {1: "Standard(100K)", 2: "Fast(400K)", 3: "High-Speed(3.4M)"}.get((param1 >> 2) & 0x3, "unknown")
    has_dma = (param1 >> 6) & 0x1
    rx_depth = (param1 >> 8) & 0xFF
    tx_depth = (param1 >> 16) & 0xFF

    print("  %s HW Config (IC_COMP_PARAM_1=0x%08X):" % (name, param1))
    print("    APB width:  %s" % apb_width)
    print("    Max speed:  %s" % max_speed)
    print("    DMA:        %s" % ("Yes" if has_dma else "No"))
    print("    TX FIFO:    %d entries" % tx_depth)
    print("    RX FIFO:    %d entries" % rx_depth)
```

### I3C Register Checks

```python
i3c_ctrl1 = namednodes.sv.socket0.pcd.lpss.i3c0

# Device control and queue status
i3c_ctrl = i3c_ctrl1.search(regexpression="device_ctrl|dev_ctrl", searchType="registers")
for reg in i3c_ctrl:
    print(f"{reg} = {hex(reg.read())}")
    print(reg.getspec())

i3c_queue = i3c_ctrl1.search(regexpression="queue|fifo", searchType="registers")
for reg in i3c_queue:
    print(f"{reg} = {hex(reg.read())}")
```

**Key I3C checks:** Device control (enable, mode, hot-join), status (errors, IBI pending), queue levels, timing (SCL freq, SDR/HDR), DAT (dynamic address table). All 4 interfaces operate in DMA mode on NVL.

### I3C HCI Register Reference

The I3C controllers use HCI (Host Controller Interface) v1.0. Key registers accessible via PythonSV:

| Register | Offset | Description | Key Bits |
|----------|--------|-------------|----------|
| `hc_control` | 0x004 | Host controller control | Bit 31=BUS_ENABLE, Bit 30=RESUME, Bit 29=ABORT |
| `hc_capabilities` | 0x008 | Controller capabilities | CMD_SIZE, SG_CAPABILITY, etc. |
| `present_state` | 0x00C | Current bus state | CM_TFR_ST_STATUS[21:16], CM_TFR_STATUS[13:8] |
| `present_state_debug` | 0x14C | Extended state debug | 0x13=HALT in CM_TFR_ST_STATUS |
| `reset_control` | 0x010 | Soft/hard reset triggers | Bit 1=SOFT_RST, Bit 0=CORE_RST |
| `hci_version` | 0x000 | HCI spec version | 0x100 = HCI v1.0 |
| `intr_status` | 0x020 | Interrupt status | HC_INTERNAL_ERR, HC_SEQ_CANCEL_ERR, TRANSFER_ERR, etc. |
| `intr_signal_enable` | 0x028 | Interrupt signal enable | Same layout as intr_status |
| `dat_section` | 0x030 | DAT section offset/size | TABLE_OFFSET[11:0], TABLE_SIZE[18:12] |
| `command_queue_port` | 0x0C0 | Write commands here | CMD_ATTR[2:0], TID[6:3], DEV_INDEX[19:16] |
| `response_queue_port` | 0x0C4 | Read responses here | ERR_STATUS[31:28], TID[27:24], DATA_LENGTH[15:0] |
| `tx_data_port` | 0x0C8 | Write TX data here | 32-bit data word |
| `rx_data_port` | 0x0CC | Read RX data here | 32-bit data word |
| `queue_thld_ctrl` | 0x0D0 | Queue threshold control | CMD_BUF_EMPTY_THLD, RESP_BUF_THLD, etc. |

**HC_CONTROL Bit Layout (critical for abort debugging):**
> **Source:** DWC MIPI I3C Databook v1.00a, Table 6-4

```
Bit 31: BUS_ENABLE      — 1=bus enabled, 0=bus disabled (poll until 0 after clearing)
Bit 30: RESUME          — Write 1 to resume from HALT state (auto-clears)
Bit 29: ABORT           — Write 1 to trigger abort (auto-clears when done)
Bit  8: HOT_JOIN_CTRL   — 1=ACK Hot-Join, 0=NACK Hot-Join
Bit  7: I2C_SLAVE_PRESENT — 1=I2C slave device on bus
Bit  0: IBA_INCLUDE     — Include I3C broadcast address
```

> ⚠️ **PREVIOUSLY DOCUMENTED BUG (now fixed):** Bit 7 was incorrectly labeled as RESUME. The correct mapping is **Bit 30 = RESUME**, **Bit 7 = I2C_SLAVE_PRESENT**. This matters for HALT recovery — writing to Bit 7 instead of Bit 30 would NOT resume the controller.

### I3C HCI Command Structure (CMD_ATTR types)

> **Source:** DWC MIPI I3C Databook v1.00a, Chapter 6.4

Commands are written as 2×32-bit DWORDs to `command_queue_port`:

| CMD_ATTR[2:0] | Type | Description |
|---------------|------|-------------|
| 0x0 | REGULAR_TRANSFER | Standard read/write with data pointer |
| 0x1 | IMMEDIATE_DATA | Short data (≤4 bytes) embedded in command DWORD1 |
| 0x2 | ADDR_ASSIGN | Dynamic Address Assignment (ENTDAA/SETDASA) |
| 0x3 | COMBO_TRANSFER | Combined write-then-read in one command |

**Command DWORD0 common fields:**
```
Bit 31:    TOC            — Terminate On Completion (release bus after)
Bit 30:    ROC            — Response On Completion (generate response entry)
Bit 29:    RNW            — 1=Read, 0=Write
Bits[28:26]: MODE/SPEED   — 0=SDR0(1st), 1=SDR1(2nd), 2=SDR2(3rd), 3=SDR3(4th), 4=SDR4, 5=HDR-TSx, 6=HDR-DDR, 7=I2C
Bits[19:16]: DEV_INDEX    — Index into Device Address Table (DAT)
Bit 15:    CP             — Command Present (1=CMD field valid, for CCC)
Bits[14:7]: CMD           — CCC command code (when CP=1)
Bits[6:3]:  TID           — Transaction ID (echoed in response)
Bits[2:0]:  CMD_ATTR      — Command type (see table above)
```

**Response DWORD format:**
```
Bits[31:28]: ERR_STATUS    — Error code (see failure-analysis SKILL for full table)
Bits[27:24]: TID           — Transaction ID (must match command TID)
Bits[15:0]:  DATA_LENGTH   — Actual bytes transferred (for reads)
```

### I3C PRESENT_STATE_DEBUG State Machine Decoding

> **Source:** DWC MIPI I3C Databook v1.00a, Table 6-7

Use `present_state_debug` (offset 0x14C) for detailed controller state during debugging:

**CM_TFR_ST_STATUS [21:16] — Transfer State Machine:**

| Value | State | Description |
|-------|-------|-------------|
| 0x00 | IDLE | No transfer in progress |
| 0x01 | START | Generating START condition |
| 0x02 | RESTART | Generating RESTART condition |
| 0x03 | STOP | Generating STOP condition |
| 0x04 | START_HOLD | Holding START |
| 0x08 | BROADCAST_W | Broadcast write (CCC) |
| 0x09 | BROADCAST_R | Broadcast read |
| 0x0A | DAA_PROCESS | Dynamic Address Assignment in progress |
| 0x0B | ENTDAA_BYTE | ENTDAA byte transfer |
| 0x0D | SDR_WRITE | SDR write transfer |
| 0x0E | SDR_READ | SDR read transfer |
| 0x0F | HDR_CMD | HDR command phase |
| 0x13 | **HALT** | ⚠️ Controller halted — requires RESUME |
| 0x14 | HDR_EXIT | Exiting HDR mode |

**CM_TFR_STATUS [13:8] — Overall Transfer Status:**

| Value | State | Description |
|-------|-------|-------------|
| 0x00 | IDLE | Controller idle |
| 0x01 | PROCESSING | Command being processed |
| 0x02 | WAITING | Waiting for data/response |
| 0x0F | **HALTED** | ⚠️ Controller in HALT state |

**Diagnostic script for state machine debugging:**
```python
# Read I3C controller state machine status
import namednodes as nn
nn.sv.refresh()

# Adjust path for NVL (.pcd) vs PTL (.soc)
i3c = nn.sv.socket0.pcd.lpss.i3c0  # NVL
# i3c = nn.sv.socket0.soc.lpss.i3c0_0.lpio  # PTL

present_debug = i3c.present_state_debug.read()
cm_tfr_st = (present_debug >> 16) & 0x3F
cm_tfr = (present_debug >> 8) & 0x3F

STATES = {0x00:"IDLE", 0x01:"START", 0x02:"RESTART", 0x03:"STOP",
          0x08:"BROADCAST_W", 0x0A:"DAA_PROCESS", 0x0D:"SDR_WRITE",
          0x0E:"SDR_READ", 0x13:"HALT", 0x14:"HDR_EXIT"}
STATUS = {0x00:"IDLE", 0x01:"PROCESSING", 0x02:"WAITING", 0x0F:"HALTED"}

print("PRESENT_STATE_DEBUG = 0x%08X" % present_debug)
print("  CM_TFR_ST_STATUS[21:16] = 0x%02X (%s)" % (cm_tfr_st, STATES.get(cm_tfr_st, "UNKNOWN")))
print("  CM_TFR_STATUS[13:8]     = 0x%02X (%s)" % (cm_tfr, STATUS.get(cm_tfr, "UNKNOWN")))
if cm_tfr_st == 0x13 or cm_tfr == 0x0F:
    print("  WARNING: Controller is HALTED! Use HC_CONTROL bit30 (RESUME) to recover.")
```

> **IMPORTANT:** If BUS_ENABLE (bit 31) cannot be set to 1, or gets stuck at 1 after abort, check the I3C chicken bit register. See **I3C Chicken Bit (DMA Abort Control)** section below.

### I3C Chicken Bit Register (DMA Abort Control)

The `gen_pvt_high_regrw4` register controls I3C DMA abort behavior. This is critical for diagnosing I3C abort recovery failures (see HSDES 18044213731).

**Register Details:**
| Field | Value |
|-------|-------|
| Formal Name | GEN_REGRW8 (in XML), gen_pvt_high_regrw4 (in PythonSV) |
| Offset | 0x61C in IOSF2AXI private config space |
| Size | 32 bits, RW |
| Default | 0x00000000 |

**Key Bits:**
| Bits | Field | Description |
|------|-------|-------------|
| [1:0] | DMAC_NO_CLEAR_CTRL_Q_ON_ABORT | Controls DMA controller queue clear on abort. **0 = clear queue (correct/workaround)**, 3 = don't clear (buggy, causes BUS_ENABLE stuck) |

> **NOTE:** Bit-level mapping is defined in the **Synopsys DWC MIPI I3C IP Databook** (vendor-confidential), NOT in Intel HAS. Co-Design will not have this detail.

**PythonSV Access Paths:**
```python
# NVL PCD-H
cb_nvl = nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4

# PTL-H
cb_ptl = nn.sv.socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
```

**VJT Framework Convention:**
- DMA mode: chicken bit = **0** (clears control queue on abort — correct behavior)
- PIO mode: chicken bit = **5**
- Reference: `vjt/lpss/lpss_i3c.py` line ~136 (PTL) / ~150 (NVL)

**Diagnostic Script:**
```python
import namednodes as nn
nn.sv.refresh()

# Read chicken bit (adjust path for NVL vs PTL)
cb = nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
val = cb.read()
bits10 = val & 3
print("gen_pvt_high_regrw4 = 0x%08X" % val)
print("DMAC_NO_CLEAR_CTRL_Q_ON_ABORT (bits[1:0]) = %d" % bits10)
if bits10 == 0:
    print("OK: Abort queue clear enabled (workaround active)")
elif bits10 == 3:
    print("WARNING: Abort queue clear DISABLED (buggy default, see HSDES 18044213731)")
else:
    print("INFO: Non-standard value %d" % bits10)
```

### PTL Platform I3C Register Access

PTL (Panther Lake) has a **different register hierarchy** from NVL for I3C:

| Platform | SoC Path | I3C Base | HCI Registers | Config Space |
|----------|----------|----------|---------------|--------------|
| NVL PCD-H | `socket0.pcd` | `pcd.lpss.i3c0` | `.i3c0.cfg` sub-nodes | `.i3c0.cfg` |
| PTL-H | `socket0.soc` | `soc.lpss.i3c0_0` | `.i3c0_0.lpio.*` (flat) | **No `.cfg` sub-node** |

**PTL I3C Controller Mapping:**

> **HAS-verified ("Table: Slice Configuraton"):** PTL has **4 I3C instances under 2 controllers** — identical to NVL. Each controller hosts 2 I3C instances sharing an 8K MMIO BAR. Only clock differs: PTL=100 MHz, NVL=200 MHz.

| PythonSV Node | PCI Function | I3C Interfaces | Notes |
|---------------|-------------|----------------|-------|
| `soc.lpss.i3c0_0` | Dev 17, Fn 0 | I3C0 + I3C1 (Controller #1) | DMA mode, 8K BAR |
| `soc.lpss.i3c1_0` | Dev 17, Fn 1 | I3C2 + I3C3 (Controller #2) | DMA mode, 8K BAR |

**PTL I3C HCI Register Access:**
```python
# PTL — registers are directly under .lpio (NO .cfg sub-node)
i3c = nn.sv.socket0.soc.lpss.i3c0_0.lpio
hc_control    = i3c.hc_control.read()       # HC_CONTROL
present_state = i3c.present_state.read()     # PRESENT_STATE
reset_control = i3c.reset_control.read()     # RESET_CONTROL
hci_version   = i3c.hci_version.read()       # HCI_VERSION
intr_status   = i3c.intr_status.read()       # INTR_STATUS

# Command/Response queues
i3c.command_queue_port.write(cmd)             # Send command
resp = i3c.response_queue_port.read()         # Read response

# DMA controller access
dma = nn.sv.socket0.soc.lpss.i3c0cl_dma      # DMA HC
```

> **Key difference:** On PTL, there is no `.cfg` sub-node for I3C PCI config space access via PythonSV. PCI config must be accessed through direct BDF reads or the `.lpio` hierarchy.

### SPI Register Checks

```python
spi0 = namednodes.sv.socket0.pcd.lpss.spi0

spi0_ctrl = spi0.search(regexpression="ctrl|control|enable", searchType="registers")
for reg in spi0_ctrl:
    print(f"{reg} = {hex(reg.read())}")

spi0_sts = spi0.search(regexpression="sts|status|sr", searchType="registers")
for reg in spi0_sts:
    print(f"{reg} = {hex(reg.read())}")
```

**Key SPI checks:** Control (enable, CPOL/CPHA, master/slave), status (busy, FIFO, errors), baud rate divider, data frame size, chip select polarity.

### UART Register Checks

```python
uart0 = namednodes.sv.socket0.pcd.lpss.hsuart0

uart0_regs = uart0.search(regexpression="lcr|lsr|mcr|dll|dlh|fcr", searchType="registers")
for reg in uart0_regs:
    print(f"{reg} = {hex(reg.read())}")
    print(reg.getspec())
```

**Key UART checks:** LCR (data/stop bits, parity, DLAB), LSR (data ready, errors, THRE, TEMT), DLL/DLH (baud divisor — set DLAB=1 first), FCR (FIFO enable/depth), MCR (loopback bit 4, RTS/DTR).

### Bulk Register Dump

```python
def dump_controller_regs(controller_path, label):
    """Dump all registers for an LPSS controller."""
    ctrl = eval(f"namednodes.sv.socket0.pcd.lpss.{controller_path}")
    all_regs = ctrl.search(regexpression=".*", searchType="registers")
    print(f"\n=== {label} Register Dump ===")
    for reg in all_regs:
        try:
            val = reg.read()
            print(f"  {reg}: {hex(val)}")
        except Exception as e:
            print(f"  {reg}: READ ERROR - {e}")

# Dump all controllers
for i in range(6): dump_controller_regs(f"i2c{i}", f"I2C{i}")
dump_controller_regs("i3c0", "I3C Controller 1 (I3C0/I3C1)")
dump_controller_regs("i3c1", "I3C Controller 2 (I3C2/I3C3)")
for i in range(3): dump_controller_regs(f"spi{i}", f"SPI{i}")
for i in range(3): dump_controller_regs(f"hsuart{i}", f"UART{i}")
```

---

## Part 3 — Pad Mode (PMode) Verification

### What is PMode?

**PMode (Pad Mode)** determines how a GPIO pad functions:
- **PMode = 0h**: Standard GPIO operation (software-controlled)
- **PMode ≠ 0h**: Native function mode (routes signal to LPSS controller)

For LPSS controllers to communicate with external devices, their signal pads **must** be in the correct native function mode. A pad stuck in GPIO mode (PMode=0) is the #1 cause of "controller configured but not communicating" failures.

### Required Signals Per Controller

| Controller | Required Signals |
|-----------|-----------------|
| I2C | SDA (data), SCL (clock) |
| I3C | SDA (data), SCL (clock) |
| SPI | CLK, MISO, MOSI, CS0 (+ optional CS1) |
| UART | TXD, RXD (+ optional RTS, CTS for flow control) |

### NVL Die Differences
- **PCH-S**: All controllers, all pads (I2C0–5, I3C0–3, SPI0–2, UART0–2)
- **PCD-H**: All controllers, all pads (I2C0–5, I3C0–3, SPI0–2, UART0–2) — same count as PCH-S but with different BDFs/DIDs

### PADCFG Register Structure

**PADCFG DW0** — Primary configuration:
- **Bits [13:10]**: **PMode** — Pad Mode (native function selector)
- **Bits [9:8]**: Tx/Rx enable
- **Bit [1]**: Tx state (GPIO mode)
- **Bit [0]**: Rx state (GPIO mode)

**PADCFG DW1** — Electrical configuration:
- **Bits [13:10]**: Pad termination (pull-up/down/none)
- **Bits [9:0]**: Interrupt configuration

> Use `.getspec()` to verify exact bit positions on NVL.

### PMode Lookup

Specific pad names and PMode values come from the NVL GPIO HAS. Query Co-Design:
```
Please reference NVL_PCD_H_GPIO_HAS.html (or NVL_PCH_S_GPIO_HAS.html) and list 
the GPIO pad assignments for LPSS controllers: which pads are used for I2C0-5 
SDA/SCL, I3C0-3 SDA/SCL, SPI0-2 CLK/MISO/MOSI/CS, and UART0-2 TX/RX/RTS/CTS? 
Include the expected PMode value for each.
```

### PMode Verification Code

```python
# Search for pad config registers
padcfg_regs = namednodes.sv.socket0.pcd.search(
    regexpression="padcfg.*dw0|pad_cfg.*dw0", searchType="registers"
)

def read_pmode(pad_dw0_register):
    """Read PMode value from PADCFG DW0."""
    dw0_value = pad_dw0_register.read()
    return (dw0_value >> 10) & 0xF  # Bits [13:10]

def verify_lpss_pmode(pad_name, pad_dw0_register, expected_pmode):
    """Verify PMode for an LPSS signal pad."""
    actual_pmode = read_pmode(pad_dw0_register)
    
    if actual_pmode == expected_pmode:
        print(f"  ✅ {pad_name} PMode={actual_pmode} (correct)")
        return True
    elif actual_pmode == 0:
        print(f"  ❌ {pad_name} stuck in GPIO mode (PMode=0)! Expected {expected_pmode}")
        return False
    else:
        print(f"  ⚠️ {pad_name} PMode={actual_pmode}, expected {expected_pmode} — wrong native function")
        return False

def check_pad_ownership(pad_name, ownership_register, pad_bit):
    """Check if pad is host-owned (required for PMode config)."""
    ownership = ownership_register.read()
    owner_bit = (ownership >> pad_bit) & 0x1
    # Typical: 0 = ACPI/Host, 1 = Driver/GPIO-mode (verify with platform spec)
    print(f"  {'✅' if owner_bit == 0 else '⚠️'} {pad_name} ownership bit={owner_bit}")
    return owner_bit == 0

def check_pad_lock(pad_name, padcfglock_register, pad_bit):
    """Check if pad configuration is locked."""
    is_locked = (padcfglock_register.read() >> pad_bit) & 0x1
    print(f"  {'🔒' if is_locked else '🔓'} {pad_name} {'LOCKED' if is_locked else 'UNLOCKED'}")
    return is_locked
```

### Common PMode Issues

1. **Pad stuck in GPIO mode (PMode=0)** — BIOS didn't configure, driver failed, or pad locked
2. **Wrong native function** — PMode non-zero but wrong value for this LPSS port
3. **Pad ownership conflict** — Pad owned by CSME/ISH, host can't configure PMode
4. **Pad locked by BIOS** — Configuration register locked, runtime changes impossible

---

## VJT Fabric-to-Controller Mapping

*Source: `C:\pythonsv\novalake\vjt\lpss\nvlh_cltap.py`*

| Fabric ID | Controller | PythonSV Path (PCD-H) |
|-----------|-----------|----------------------|
| pf_top_0 | I2C0 | `sv.socket0.pcd.lpss.i2c0` |
| pf_top_1 | I2C1 | `sv.socket0.pcd.lpss.i2c1` |
| pf_top_2 | I2C2 | `sv.socket0.pcd.lpss.i2c2` |
| pf_top_3 | I2C3 | `sv.socket0.pcd.lpss.i2c3` |
| pf_top_4 | I2C4 | `sv.socket0.pcd.lpss.i2c4` |
| pf_top_5 | I2C5 | `sv.socket0.pcd.lpss.i2c5` |
| pf_top_6 | UART0 (HSUART0) | `sv.socket0.pcd.lpss.hsuart0` |
| pf_top_7 | UART1 (HSUART1) | `sv.socket0.pcd.lpss.hsuart1` |
| pf_top_8 | UART2 (HSUART2) | `sv.socket0.pcd.lpss.hsuart2` |
| pf_top_9 | SPI0 | `sv.socket0.pcd.lpss.spi0` |
| pf_top_10 | SPI1 | `sv.socket0.pcd.lpss.spi1` |
| pf_top_11 | SPI2 | `sv.socket0.pcd.lpss.spi2` |
| pf_top_12 | I3C0/I3C1 (shared) | `sv.socket0.pcd.lpss.i3c0` |
| pf_top_13 | I3C2/I3C3 (shared) | `sv.socket0.pcd.lpss.i3c1` |

> **IMPORTANT:** Do NOT assume sequential PCI function → fabric ID mapping. Always reference `nvlh_cltap.py`.

---

## IOSF Sideband Port ID Mapping (HAS-Verified)

*Source: `LPSS_HAS.html` — IP Version 5.2, Doc revision 1.02 (April 2025)*

Each LPSS controller has an IOSF Sideband (IOSF SB) port for register access. Port IDs match the fabric mapping in `nvlh_cltap.py`.

| Controller | Port ID (Hex) | Role | IOSF SB Address Range | DMA Mode |
|---|---|---|---|---|
| I2C0 | 0x0 | Initiator/Target | 0xFF00_0XXX | DMA |
| I2C1 | 0x1 | Initiator/Target | 0xFF00_1XXX | DMA |
| I2C2 | 0x2 | Initiator/Target | 0xFF00_2XXX | DMA |
| I2C3 | 0x3 | Initiator/Target | 0xFF00_3XXX | DMA |
| I2C4 | 0x4 | Target only | 0xFF00_4XXX | PIO |
| I2C5 | 0x5 | Target only | 0xFF00_5XXX | PIO |
| UART0 | 0x6 | Initiator/Target | 0xFF00_8XXX | DMA |
| UART1 | 0x7 | Initiator/Target | 0xFF00_9XXX | DMA |
| UART2 | 0x8 | Target only | 0xFF00_AXXX | PIO |
| SPI0 | 0x9 | Initiator/Target | 0xFF00_CXXX | DMA |
| SPI1 | 0xA | Initiator/Target | 0xFF00_DXXX | DMA |
| SPI2 | 0xB | Initiator/Target | 0xFF00_EXXX | DMA |
| I3C0/I3C1 (Slice #1) | 0xC | Initiator/Target | 0xFF01_0XXX, 0xFF01_1XXX | DMA (ring) |
| I3C2/I3C3 (Slice #2) | 0xD | Initiator/Target | 0xFF01_2XXX, 0xFF01_3XXX | DMA (ring) |

> **NVL PCD-H vs PCH-S:** Same port numbers but **16-bit port IDs** on PCD-H, **8-bit port IDs** on PCH-S. Address ranges are identical.
> **MTP-S only:** UART3 (DMA, handshake 0x8), SPI3 (DMA, handshake 0xC). MTP-S has only 2 I3C instances (1 controller). MTL/LNL/PTL/WCL/NVL all share the same port layout shown above.

---

## DMA Channel Assignments (HAS-Verified)

*Source: `LPSS_HAS.html` — IP Version 5.2*

Each DMA-capable controller has **2 channels**: TX (Channel 0) and RX (Channel 1).
I3C uses **ring-based DMA**: TX Ring 0/1 and RX Ring 2/3 (2 rings per controller).
PIO controllers (I2C4, I2C5, UART2) have **no DMA channels**.

| Controller | DMA Handshake # | TX Channel | RX Channel | Notes |
|---|---|---|---|---|
| I2C0 | 0 | Ch0 | Ch1 | |
| I2C1 | 1 | Ch0 | Ch1 | |
| I2C2 | 2 | Ch0 | Ch1 | |
| I2C3 | 3 | Ch0 | Ch1 | |
| I2C4 | 4 | — | — | PIO only |
| I2C5 | 5 | — | — | PIO only |
| UART0 | 6 | Ch0 | Ch1 | |
| UART1 | 7 | Ch0 | Ch1 | |
| UART2 | 8 | — | — | PIO only |
| SPI0 | 9 | Ch0 | Ch1 | |
| SPI1 | 0xA | Ch0 | Ch1 | |
| SPI2 | 0xB | Ch0 | Ch1 | |
| I3C0/I3C1 | 0xC | Ring 0/1 | Ring 2/3 | Ring-based DMA |
| I3C2/I3C3 | 0xD | Ring 0/1 | Ring 2/3 | Ring-based DMA |

> DMA handshake # is used in `SRC_PER` / `DST_PER` register fields.
> **MTP-S only:** MTP-S adds UART3 (DMA, handshake 0x8) and SPI3 (DMA, handshake 0xC), but has only 1 I3C controller (2 instances). MTL/LNL/PTL/WCL/NVL all share the same DMA assignment layout.

---

## Platform Differences (HAS-Verified)

*Source: `LPSS_HAS.html` — "Table: Slice Configuraton"*

> **HAS-verified:** MTL/LNL/PTL/WCL/NVL all have **identical LPSS controller counts**: 6 I2C, 3 UART, 3 SPI, 4 I3C (2 controllers). Only MTP-S differs.

| Feature | MTL/LNL/PTL/WCL/NVL | MTP-S |
|---|---|---|
| I2C instances | 6 (I2C0-5: 4 DMA + 2 PIO) | 6 (same) |
| I3C instances | **4** (2 per controller, 2 controllers) | **2** (1 controller) |
| SPI instances | 3 (SPI0-2, all DMA) | **4** (adds SPI3 DMA) |
| UART instances | 3 (UART0-2: 2 DMA + 1 PIO) | **4** (adds UART3 DMA) |
| I3C core clock | 100 MHz (PTL/WCL), **200 MHz (NVL)** | 100 MHz |
| PIO controllers | I2C4-5, UART2 | I2C4-5, UART2 |

**PTL vs NVL — key differences (same controller counts):**

| Feature | PTL | NVL |
|---|---|---|
| I3C core clock | 100 MHz | **200 MHz** |
| SoC path (PythonSV) | `socket0.soc` | `socket0.pcd` (PCD-H) / `socket0.pch` (PCH-S) |
| I3C node names | `i3c0_0.lpio`, `i3c1_0.lpio` | `i3c0.cfg`, `i3c1.cfg` |
| IOSF SB port ID width | 8-bit | 16-bit (PCD-H), 8-bit (PCH-S) |

---

## Verification Checklist

For each LPSS port (I2C, I3C, SPI, UART):

**Enumeration:**
- [ ] Device appears in PCI tree (VID ≠ 0xFFFF)
- [ ] Vendor ID = 0x8086 (Intel)
- [ ] Device ID matches expected value from tables above
- [ ] BAR0 assigned (non-zero, not 0xFFFFFFFF)
- [ ] Memory Space Enable and Bus Master Enable set

**Registers:**
- [ ] Control registers match expected configuration
- [ ] Status registers show no error conditions
- [ ] Enable register shows correct state
- [ ] No unexpected interrupts pending

**Pad Mode:**
- [ ] All required pads in correct native function mode (PMode ≠ 0)
- [ ] PMode value matches expected from GPIO HAS
- [ ] Pad ownership is correct (host-owned for LPSS)
- [ ] Pad lock status understood (locked = BIOS set, cannot change)

---

## Register Checkout Procedure

1. **Identify target registers** based on failure symptom:
   - Functional issues → control/config registers
   - Error conditions → status registers
   - Power issues → PMCSR (use `fv-lpss/power-state`)
   - No communication → PMode (Part 3 above)

2. **Locate registers** via PythonSV search:
   ```python
   regs = namednodes.sv.socket0.pcd.lpss.i2c0.search(
       regexpression=".*", searchType="registers"
   )
   ```

3. **Read and inspect** with `.getspec()` for field layout

4. **Compare** against HAS reset values, driver-configured values, or a known-good system

5. **Analyze discrepancies** — check if BIOS/driver expected, cross-reference HSDES for errata

---

## Tips

1. **Always `itp.unlock()` and `sv.refresh()`** before register access
2. **Use `.getspec()`** to understand register layout before interpreting values
3. **Check PMode before debugging controller** — many LPSS issues are pad config, not controller
4. **PCH-S uses `pch` path, PCD-H uses `pcd` path** — don't mix them
5. **Search broadly first** then narrow: `search(regexpression="i2c0.*", searchType="registers")`
6. **Compare working vs failing** systems to isolate configuration differences
7. **Check ownership before PMode** — if wrong owner, writes are silently ignored

---

## Related Skills

- **`fv-lpss/power-state`** — D3 entry/exit and clock gating verification
- **`fv-lpss/failure-analysis`** — Analyze NGA test failures
- **`pysv`** — General PythonSV usage patterns

---

## Part 4 — GPIO Interrupt Pad Register Checks (IOAPIC Race Condition)

> **Context:** HSDES 14023171649 identified a race condition between GPIO `DEASSERT_IRQ` and ITSS `MSI_CMPL` that can permanently stick IOAPIC RTE entries, causing GPIO-connected LPSS peripherals (touchpads, sensors) to lose interrupt delivery. This section provides register checks to detect and prevent this condition.
>
> **See also:** `fv-lpss/debug` Playbook 6, `fv-lpss/failure-analysis` IOAPIC section, `docs/lpss_known_issues.md` HSDES-004

### GPIO Pad Configuration Registers (Per-Pad)

**PAD_CFG_DW0 — Primary Pad Configuration:**

| Bits | Field | Critical Values | Description |
|------|-------|----------------|-------------|
| [31] | gpiorxdis | 0=RX enabled | GPIO RX disable |
| [30] | gpiotxdis | 0=TX enabled | GPIO TX disable |
| [26:25] | **rxevcfg** | **0x2=disabled (BIOS)**, 0x0=level, 0x1=edge, 0x3=disabled | RX event config — **MUST be 0x2 during BIOS init** to prevent race |
| [20] | **gpiroutioxapic** | 0=GPIO mode (vulnerable), **1=IOAPIC direct (safer)** | Interrupt routing mode |
| [19] | gpiroutsci | 0/1 | Route to SCI |
| [18] | gpiroutsmi | 0/1 | Route to SMI |
| [17] | gpiroutnmi | 0/1 | Route to NMI |
| [13:10] | pmode | ≥1 for native function | Pad mode (see Part 3 above) |
| [1] | gpiotxstate | — | GPIO TX state |
| [0] | **gpiorxstate** | Read-only — current RX level | GPIO RX state (physical line level) |

**PAD_CFG_DW1 — Electrical & Interrupt Configuration:**

| Bits | Field | Critical Values | Description |
|------|-------|----------------|-------------|
| [17:14] | **iosstate** | **0xF = all masked (required)** | IO Standby state — **MUST be 0xF** to prevent S0i2.2 glitches |
| [13:10] | term | 0=none, 2=5K PD, 9=1K PU, etc. | Pad termination |
| [7:0] | **intsel** | IRQ number | Interrupt select — maps to IOAPIC RTE index |

**MISCCFG — Community Miscellaneous Configuration:**

| Bits | Field | Critical Values | Description |
|------|-------|----------------|-------------|
| [7:0] | **gpdmintsel** | e.g., 0x0E = IRQ 14 | GPIO DM interrupt select — IRQ# for this pad community |

**Ownership & Status Registers:**

| Register | Description | Key Bits |
|----------|-------------|----------|
| `HOSTSW_OWN` | Host software ownership | 0=ACPI, 1=driver (per-pad bit) |
| `PAD_OWN` | Pad ownership | 0=host, 1=CSME (per-pad 2 bits) |
| `GPI_IE` | GPIO interrupt enable | 1=enabled (per-pad bit) |
| `GPI_IS` | GPIO interrupt status | 1=interrupt pending (W1C per-pad bit) — **clearing this triggers DEASSERT_IRQ** |

### GPIO Interrupt Pad Audit Script

```python
import namednodes as nn
nn.sv.refresh()

def audit_gpio_interrupt_pads(community_base, community_name, num_pads=24):
    """Audit GPIO pads for IOAPIC race condition vulnerability (HSDES 14023171649).
    
    Checks:
    1. rxevcfg should be 0x2 during BIOS (disabled until OS enables)
    2. iosstate MUST be 0xF on interrupt-generating pads
    3. gpiroutioxapic=1 is safer than GPIO mode (gpiroutioxapic=0)
    4. GPI_IS clear timing (informational — cannot detect race statically)
    """
    vulnerable_pads = []
    
    for pad_idx in range(num_pads):
        try:
            dw0 = community_base.padcfg_dw0[pad_idx].read()
            dw1 = community_base.padcfg_dw1[pad_idx].read()
        except:
            continue
        
        rxevcfg        = (dw0 >> 25) & 0x3
        gpiroutioxapic = (dw0 >> 20) & 0x1
        gpiroutsci     = (dw0 >> 19) & 0x1
        pmode          = (dw0 >> 10) & 0xF
        gpiorxstate    = dw0 & 0x1
        
        iosstate = (dw1 >> 14) & 0xF
        intsel   = dw1 & 0xFF
        
        # Only check pads routed to IOAPIC or SCI (interrupt-generating)
        is_irq_pad = gpiroutioxapic or gpiroutsci
        if not is_irq_pad:
            continue
        
        issues = []
        if rxevcfg == 0x0:
            issues.append("rxevcfg=0x0 (level-triggered, VULNERABLE to race)")
        if iosstate != 0xF:
            issues.append("iosstate=0x%X (should be 0xF, S0i2.2 glitch risk)" % iosstate)
        if gpiroutioxapic == 0 and gpiroutsci == 0:
            issues.append("not routed to IOAPIC direct (GPIO mode)")
        
        status = "VULNERABLE" if issues else "OK"
        if issues:
            vulnerable_pads.append((pad_idx, issues))
        
        print("  Pad[%02d] %s: rxevcfg=%d gpiroutioxapic=%d iosstate=0x%X intsel=%d pmode=%d rx=%d"
              % (pad_idx, status, rxevcfg, gpiroutioxapic, iosstate, intsel, pmode, gpiorxstate))
        for issue in issues:
            print("    WARNING: %s" % issue)
    
    print("\n%s: %d/%d interrupt pads are VULNERABLE to IOAPIC race condition"
          % (community_name, len(vulnerable_pads), num_pads))
    return vulnerable_pads

# Example: Audit GPP_B community on NVL PCD-H (adjust path per platform)
# audit_gpio_interrupt_pads(nn.sv.socket0.pcd.gpio.gpp_b, "GPP_B", num_pads=24)
```

### IOAPIC RTE Validation Script

```python
def validate_ioapic_rte_health(max_irqs=24):
    """Validate IOAPIC Redirection Table Entries for stuck conditions.
    
    Detects the HSDES 14023171649 failure signature:
    RTE_DS[N]==1 AND RTE_Rirr[N]==1 AND RTE_Mask[N]==0
    
    This indicates a permanently stuck interrupt — no further IRQs on this line.
    """
    import namednodes as nn
    ioapic_base = 0xFEC00000
    ioregsel = ioapic_base + 0x00
    iowin    = ioapic_base + 0x10
    
    stuck_irqs = []
    
    print("=== IOAPIC RTE Health Check (HSDES 14023171649) ===\n")
    print("IRQ  Mask  Trig  RIRR  DS   DlvM  Vector  Dest  Status")
    print("---  ----  ----  ----  ---  ----  ------  ----  ------")
    
    for irq in range(max_irqs):
        # Read low DWORD
        nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq, 4)
        rte_low = nn.sv.socket0.pcd.io.mem.read(iowin, 4)
        
        # Read high DWORD
        nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq + 1, 4)
        rte_high = nn.sv.socket0.pcd.io.mem.read(iowin, 4)
        
        msk  = (rte_low >> 16) & 1
        tm   = (rte_low >> 15) & 1
        rirr = (rte_low >> 14) & 1
        pol  = (rte_low >> 13) & 1
        ds   = (rte_low >> 12) & 1
        dlm  = (rte_low >> 8) & 7
        vct  = rte_low & 0xFF
        did  = (rte_high >> 24) & 0xFF
        
        # Check for stuck condition
        is_stuck = (ds == 1 and rirr == 1 and msk == 0)
        status = "STUCK!" if is_stuck else "OK"
        
        if is_stuck:
            stuck_irqs.append(irq)
        
        trig_str = "Level" if tm else "Edge"
        dlm_str = {0:"Fixed", 1:"LoPri", 2:"SMI", 4:"NMI", 5:"INIT", 7:"ExtINT"}.get(dlm, "?")
        
        # Only print non-masked or stuck IRQs for readability
        if msk == 0 or is_stuck:
            print("%3d  %4d  %5s  %4d  %3d  %4s  0x%02X    0x%02X  %s"
                  % (irq, msk, trig_str, rirr, ds, dlm_str, vct, did, status))
    
    if stuck_irqs:
        print("\n>>> CRITICAL: %d IRQ(s) are STUCK: %s" % (len(stuck_irqs), stuck_irqs))
        print(">>> Root cause: IOAPIC DEASSERT_IRQ/MSI_CMPL race (HSDES 14023171649)")
        print(">>> Recovery: Write EOI to 0xFEC00040, or reboot with BIOS mitigations")
    else:
        print("\nAll active IOAPIC RTEs are healthy.")
    
    return stuck_irqs
```

### Verification Checklist — GPIO Interrupt Pads

For each GPIO pad that routes interrupts to LPSS peripherals:

- [ ] `PAD_CFG_DW0.rxevcfg` = 0x2 during BIOS init (disabled until OS ready)
- [ ] `PAD_CFG_DW1.iosstate` = 0xF (all signals masked during S0i2.2)
- [ ] `PAD_CFG_DW0.gpiroutioxapic` = 1 where possible (IOAPIC direct mode, safer)
- [ ] `PAD_CFG_DW0.pmode` ≥ 1 for native function pads
- [ ] `HOSTSW_OWN` bit = 1 for driver-controlled pads
- [ ] `GPI_IS` = 0 (no stale interrupts pending after init)
- [ ] IOAPIC RTE: `ds=0`, `rirr=0`, `msk=0`, `tm=1` (level-triggered for GPIO)
- [ ] IOAPIC RTE: `vct` matches expected vector for the IRQ
- [ ] No stuck RTEs after reboot cycle (run `validate_ioapic_rte_health()`)
