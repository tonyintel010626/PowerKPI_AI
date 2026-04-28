# FV-TCSS Registers Sub-Skill

## Overview

This sub-skill provides comprehensive register-level knowledge for TCSS (Type-C Subsystem) functional validation. It covers:
- **PCI Configuration Space** — DID/VID, BDF, BAR, Capabilities
- **MMIO Register Maps** — IOM, USB4 Router, Thunderbolt Controller, DMA
- **Power Management Registers** — D-states, clock gating, power rails
- **Debug Registers** — Status, error reporting, telemetry

---

## CRITICAL: HAS-First Policy

> **NEVER guess register layouts or bit-field definitions.**
> Always query Co-Design HAS for the specific platform before providing register information.
> This skill provides **general patterns and common register types** — actual offsets, bit-fields, and defaults are platform-specific.

---

## PCI Configuration Space

### Device Identification

| Register | Offset | Size | Description |
|----------|--------|------|-------------|
| **VID** | 0x00 | 16-bit | Vendor ID (Intel = 0x8086) |
| **DID** | 0x02 | 16-bit | Device ID (platform-specific, query HAS) |
| **Command** | 0x04 | 16-bit | Bus master, memory space enable |
| **Status** | 0x06 | 16-bit | Capability list, interrupt status |
| **Revision ID** | 0x08 | 8-bit | Stepping ID |
| **Class Code** | 0x09 | 24-bit | Base/Sub/Interface class |
| **Cache Line Size** | 0x0C | 8-bit | Cache line size |
| **Latency Timer** | 0x0D | 8-bit | Latency timer |
| **Header Type** | 0x0E | 8-bit | Header type (0x00 = Type 0) |
| **BIST** | 0x0F | 8-bit | Built-in self-test |

### Base Address Registers (BARs)

TCSS typically uses **BAR0** for MMIO register access:

| Register | Offset | Size | Description |
|----------|--------|------|-------------|
| **BAR0** | 0x10 | 64-bit | MMIO base address (query HAS for size) |
| **BAR2** | 0x18 | 64-bit | (May be unused or alternate register space) |
| **BAR4** | 0x20 | 64-bit | (May be unused) |

**Typical BAR0 Size:** 64KB–256KB (platform-specific)

### PCI Capabilities

| Capability | Cap ID | Description |
|------------|--------|-------------|
| **Power Management** | 0x01 | PM capabilities, D-state control |
| **MSI** | 0x05 | Message Signaled Interrupts |
| **MSI-X** | 0x11 | Extended MSI (if supported) |
| **PCIe** | 0x10 | PCIe capabilities, link status |
| **Advanced Error Reporting (AER)** | 0x0001 (Extended) | Error logging and reporting |
| **Latency Tolerance Reporting (LTR)** | 0x0018 (Extended) | LTR for power management |
| **L1 PM Substates** | 0x001E (Extended) | L1 sub-state support |

### Common Device IDs (Platform-Specific)

> **Always query HAS for the exact DID for your platform.**

| Platform | TCSS DID (Example) | Notes |
|----------|-------------------|-------|
| **MTL** | 0x7EC1 (example) | Query MTL_TCSS_HAS for actual DID |
| **NVL** | 0x9EC1 (example) | Query NVL_TCSS_HAS for actual DID |
| **TTL** | TBD | Query TTL_TCSS_HAS for actual DID |

**PythonSV Command to Read DID:**
```python
from pythonsv.device import pci
tcss_dev = pci.Device("00:0d.2")  # Example BDF — query HAS for actual BDF
did = tcss_dev.config.read16(0x02)
print(f"TCSS Device ID: 0x{did:04X}")
```

---

## MMIO Register Space (BAR0)

TCSS MMIO space is divided into multiple functional blocks:

```
BAR0 Base Address
├── 0x0000 - 0x0FFF   IOM (I/O Manager) Registers
├── 0x1000 - 0x1FFF   USB4 Router Registers
├── 0x2000 - 0x2FFF   Thunderbolt Controller Registers
├── 0x3000 - 0x3FFF   DisplayPort Registers
├── 0x4000 - 0x4FFF   DMA Engine Registers
├── 0x5000 - 0x5FFF   Power Management Registers
├── 0x6000 - 0x6FFF   Debug/Telemetry Registers
└── 0x7000 - 0xFFFF   Reserved / Vendor-Specific
```

> **Note:** Actual offsets vary by platform — always query HAS for the correct register map.

---

## IOM (I/O Manager) Registers

### IOM Overview
IOM manages Type-C port configuration, mux control, orientation detection, and connection state.

### Key IOM Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **IOM_PORT_STATUS** | BAR0 + 0x00 | Port connection status, orientation |
| **IOM_PORT_CONTROL** | BAR0 + 0x04 | Port configuration, mux control |
| **IOM_PHY_CONFIG** | BAR0 + 0x08 | PHY lane configuration |
| **IOM_TYPEC_STATUS** | BAR0 + 0x10 | Type-C CC pin status, Vbus |
| **IOM_USB4_CONFIG** | BAR0 + 0x20 | USB4 router enable, tunneling config |
| **IOM_TBT_CONFIG** | BAR0 + 0x24 | Thunderbolt enable, security level |
| **IOM_DP_CONFIG** | BAR0 + 0x28 | DisplayPort Alt Mode configuration |
| **IOM_PM_CONTROL** | BAR0 + 0x30 | Power management control |

### IOM_PORT_STATUS Bit-Fields (Example)

| Bit(s) | Field | Description |
|--------|-------|-------------|
| [0] | **CONNECTED** | 1 = Device connected, 0 = Disconnected |
| [1] | **ORIENTATION** | 0 = Normal, 1 = Flipped |
| [3:2] | **USB_MODE** | 00 = USB2, 01 = USB3, 10 = USB4 |
| [4] | **TBT_MODE** | 1 = Thunderbolt active |
| [5] | **DP_MODE** | 1 = DisplayPort Alt Mode active |
| [7:6] | **POWER_STATE** | 00 = D0, 01 = D0i2, 10 = D3hot, 11 = D3cold |
| [15:8] | **PORT_NUMBER** | Physical port number |

**PythonSV Command to Read IOM Port Status:**
```python
from pythonsv.device import pci
tcss_dev = pci.Device("00:0d.2")  # Query HAS for BDF
bar0_base = tcss_dev.bars[0]
iom_status = bar0_base.read32(0x00)  # Query HAS for offset
print(f"IOM Port Status: 0x{iom_status:08X}")
connected = (iom_status & 0x1) != 0
orientation = "Flipped" if (iom_status & 0x2) else "Normal"
print(f"Connected: {connected}, Orientation: {orientation}")
```

---

## USB4 Router Registers

### USB4 Router Overview
USB4 router manages tunneling for USB, PCIe, and DisplayPort protocols over USB4 links.

### Key USB4 Router Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **USB4_ROUTER_CONFIG** | BAR0 + 0x1000 | Router enable, tunneling mode |
| **USB4_LINK_STATUS** | BAR0 + 0x1004 | Link training status, speed |
| **USB4_TUNNEL_CONFIG** | BAR0 + 0x1008 | Tunnel type (USB, PCIe, DP) |
| **USB4_BANDWIDTH** | BAR0 + 0x100C | Bandwidth allocation |
| **USB4_ERROR_STATUS** | BAR0 + 0x1010 | Error flags |

### USB4_LINK_STATUS Bit-Fields (Example)

| Bit(s) | Field | Description |
|--------|-------|-------------|
| [0] | **LINK_TRAINED** | 1 = Link training complete |
| [2:1] | **LINK_SPEED** | 00 = Gen2 (10G), 01 = Gen3 (20G), 10 = Gen4 (40G), 11 = Gen5 (80G) |
| [3] | **ASYMMETRIC** | 1 = Asymmetric link (different TX/RX speeds) |
| [7:4] | **TX_LANES** | Number of active TX lanes |
| [11:8] | **RX_LANES** | Number of active RX lanes |

---

## Thunderbolt Controller Registers

### Thunderbolt Overview
Thunderbolt controller handles authentication, link training, and security for Thunderbolt devices.

### Key Thunderbolt Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **TBT_CONTROL** | BAR0 + 0x2000 | Thunderbolt enable, security mode |
| **TBT_AUTH_STATUS** | BAR0 + 0x2004 | Authentication status |
| **TBT_LINK_STATUS** | BAR0 + 0x2008 | Link training, speed, width |
| **TBT_SECURITY** | BAR0 + 0x200C | Security level (SL0-SL3) |
| **TBT_TUNNEL_STATUS** | BAR0 + 0x2010 | Active tunnels (PCIe, USB, DP) |

### TBT_SECURITY Bit-Fields (Example)

| Value | Security Level | Description |
|-------|----------------|-------------|
| 0x0 | **SL0 (None)** | No authentication — all devices allowed |
| 0x1 | **SL1 (User)** | User approval required |
| 0x2 | **SL2 (Secure)** | Challenge-response authentication |
| 0x3 | **SL3 (DP Only)** | Only DisplayPort allowed, no PCIe tunneling |

---

## DisplayPort Registers

### DisplayPort Overview
DisplayPort engine manages DP Alt Mode over Type-C, including link training and stream management.

### Key DisplayPort Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **DP_CONTROL** | BAR0 + 0x3000 | DP enable, lane count |
| **DP_LINK_STATUS** | BAR0 + 0x3004 | Link training status, rate |
| **DP_LANE_CONFIG** | BAR0 + 0x3008 | Lane mapping, polarity |
| **DP_STREAM_CONFIG** | BAR0 + 0x300C | Active streams, resolution |

### DP_LINK_STATUS Bit-Fields (Example)

| Bit(s) | Field | Description |
|--------|-------|-------------|
| [0] | **LINK_TRAINED** | 1 = Link training successful |
| [2:1] | **LINK_RATE** | 00 = 1.62 Gbps, 01 = 2.7 Gbps, 10 = 5.4 Gbps, 11 = 8.1 Gbps |
| [4:3] | **LANE_COUNT** | 00 = 1 lane, 01 = 2 lanes, 10 = 4 lanes |

---

## DMA Engine Registers

### DMA Overview
DMA engine handles data transfer for tunneled protocols (USB, PCIe, DP).

### Key DMA Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **DMA_CONTROL** | BAR0 + 0x4000 | DMA enable, channel config |
| **DMA_STATUS** | BAR0 + 0x4004 | Active channels, errors |
| **DMA_SRC_ADDR** | BAR0 + 0x4008 | Source address (64-bit) |
| **DMA_DST_ADDR** | BAR0 + 0x4010 | Destination address (64-bit) |
| **DMA_LENGTH** | BAR0 + 0x4018 | Transfer length |
| **DMA_DOORBELL** | BAR0 + 0x401C | Trigger transfer |

---

## Power Management Registers

### PM Overview
Power management registers control D-states, clock gating, and power rails for TCSS.

### Key PM Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **PM_CONTROL** | BAR0 + 0x5000 | Power state control (D0, D0i2, D3) |
| **PM_STATUS** | BAR0 + 0x5004 | Current power state |
| **CLOCK_GATING** | BAR0 + 0x5008 | Clock gating enable per IP block |
| **POWER_GATING** | BAR0 + 0x500C | Power gating enable per IP block |
| **LTR_CONTROL** | BAR0 + 0x5010 | Latency Tolerance Reporting |
| **S0IX_CONFIG** | BAR0 + 0x5014 | S0ix entry/exit configuration |

### PM_CONTROL Bit-Fields (Example)

| Bit(s) | Field | Description |
|--------|-------|-------------|
| [1:0] | **POWER_STATE** | 00 = D0, 01 = D0i2, 10 = D3hot, 11 = D3cold |
| [2] | **CLOCK_GATE_EN** | 1 = Enable clock gating |
| [3] | **POWER_GATE_EN** | 1 = Enable power gating |
| [4] | **S0IX_READY** | 1 = Ready for S0ix entry |

**PythonSV Command to Check Power State:**
```python
from pythonsv.device import pci
tcss_dev = pci.Device("00:0d.2")  # Query HAS for BDF
bar0_base = tcss_dev.bars[0]
pm_status = bar0_base.read32(0x5004)  # Query HAS for offset
power_state = pm_status & 0x3
state_names = {0: "D0", 1: "D0i2", 2: "D3hot", 3: "D3cold"}
print(f"TCSS Power State: {state_names[power_state]}")
```

---

## Debug and Telemetry Registers

### Debug Overview
Debug registers provide error status, telemetry counters, and trace buffers for failure analysis.

### Key Debug Registers (Generic Pattern)

| Register | Offset (Example) | Description |
|----------|------------------|-------------|
| **ERROR_STATUS** | BAR0 + 0x6000 | Error flags (enumeration, link, auth) |
| **ERROR_LOG** | BAR0 + 0x6004 | First error log entry |
| **TELEMETRY_CONTROL** | BAR0 + 0x6010 | Telemetry enable, sampling rate |
| **LINK_FAILURE_COUNT** | BAR0 + 0x6020 | Link training failure counter |
| **AUTH_FAILURE_COUNT** | BAR0 + 0x6024 | Thunderbolt auth failure counter |
| **TRACE_BUFFER** | BAR0 + 0x6100 | Circular trace buffer base |

### ERROR_STATUS Bit-Fields (Example)

| Bit | Field | Description |
|-----|-------|-------------|
| [0] | **ENUM_ERROR** | 1 = PCI enumeration error |
| [1] | **LINK_ERROR** | 1 = USB4/TBT link training error |
| [2] | **AUTH_ERROR** | 1 = Thunderbolt authentication error |
| [3] | **DP_ERROR** | 1 = DisplayPort link training error |
| [4] | **DMA_ERROR** | 1 = DMA transfer error |
| [5] | **TIMEOUT_ERROR** | 1 = Operation timeout |

**PythonSV Command to Read Error Status:**
```python
from pythonsv.device import pci
tcss_dev = pci.Device("00:0d.2")  # Query HAS for BDF
bar0_base = tcss_dev.bars[0]
error_status = bar0_base.read32(0x6000)  # Query HAS for offset
if error_status:
    print(f"TCSS Error Status: 0x{error_status:08X}")
    if error_status & 0x1:
        print("  - Enumeration error detected")
    if error_status & 0x2:
        print("  - Link training error detected")
    if error_status & 0x4:
        print("  - Authentication error detected")
else:
    print("No errors detected")
```

---

## Common Register Access Patterns

### Reading a Register via PythonSV

```python
from pythonsv.device import pci

# Step 1: Get TCSS device (query HAS for BDF)
tcss_dev = pci.Device("00:0d.2")

# Step 2: Read PCI config register
did = tcss_dev.config.read16(0x02)
print(f"Device ID: 0x{did:04X}")

# Step 3: Access BAR0 MMIO register
bar0_base = tcss_dev.bars[0]
iom_status = bar0_base.read32(0x00)  # Query HAS for offset
print(f"IOM Status: 0x{iom_status:08X}")
```

### Writing a Register via PythonSV (Caution)

```python
from pythonsv.device import pci

# ALWAYS confirm with user before writing to hardware registers
tcss_dev = pci.Device("00:0d.2")
bar0_base = tcss_dev.bars[0]

# Example: Set IOM port to D3 state (query HAS for correct offset and bit-field)
pm_control = bar0_base.read32(0x5000)
pm_control = (pm_control & ~0x3) | 0x2  # Set bits [1:0] to 10 (D3hot)
bar0_base.write32(0x5000, pm_control)
print("Set TCSS to D3hot")
```

### Dumping All PCI Config Space

```python
from pythonsv.device import pci

tcss_dev = pci.Device("00:0d.2")
print("PCI Config Space Dump:")
for offset in range(0, 256, 16):
    values = [tcss_dev.config.read8(offset + i) for i in range(16)]
    hex_str = " ".join(f"{v:02X}" for v in values)
    print(f"  {offset:02X}: {hex_str}")
```

---

## Platform-Specific Register Differences

> **CRITICAL:** Register layouts differ between platforms. Always query HAS before accessing registers.

### Example Differences

| Register | MTL Offset | NVL Offset | Notes |
|----------|------------|------------|-------|
| IOM_PORT_STATUS | BAR0 + 0x00 | BAR0 + 0x00 | Same across platforms (example) |
| USB4_ROUTER_CONFIG | BAR0 + 0x1000 | BAR0 + 0x1200 | Offset may differ (example) |
| TBT_SECURITY | BAR0 + 0x200C | BAR0 + 0x2010 | Offset may differ (example) |

**Always use HAS as the source of truth for register offsets and bit-fields.**

---

## Validation Checklist

### Register Enumeration Check

- [ ] Verify TCSS DID/VID match expected values
- [ ] Confirm BAR0 is allocated and within valid memory range
- [ ] Check Power Management Capability is present
- [ ] Verify LTR Capability is present and enabled
- [ ] Confirm MSI/MSI-X is configured correctly

### Register Access Check

- [ ] Read IOM_PORT_STATUS successfully
- [ ] Read USB4_LINK_STATUS successfully
- [ ] Read TBT_AUTH_STATUS successfully
- [ ] Read DP_LINK_STATUS successfully
- [ ] Read PM_STATUS matches expected power state

### Error Register Check

- [ ] Read ERROR_STATUS register
- [ ] Verify no error flags are set
- [ ] Check LINK_FAILURE_COUNT is zero
- [ ] Check AUTH_FAILURE_COUNT is zero

---

## References

- **Co-Design HAS** — Always query for platform-specific register maps
- **iTBT80G HAS** — Thunderbolt controller register specification
- **USB4 Specification** — USB4 router register requirements
- **PCI Express Base Specification** — PCI config space layout
- **Intel Client SoC External Design Specification (EDS)** — Platform-specific register details

---

## Audit Trail

| Date       | Author    | Change |
|------------|-----------|--------|
| 2026-03-30 | lingweio  | Initial registers sub-skill creation |
