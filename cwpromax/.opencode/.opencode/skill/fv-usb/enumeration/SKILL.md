---
name: enumeration
version: 2.0.0
owner: kvejaya
description: USB PCI enumeration, device discovery, BDF assignment, BAR allocation, and device tree validation for Intel Client SoC platforms
---

> **Owner**: Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

# FV-USB / Enumeration — USB PCI Enumeration & Device Discovery

## Purpose
This sub-skill covers USB device enumeration through the PCI configuration space, including device identification, topology mapping, BAR allocation, and device tree validation.

## When to Use
- User asks about USB device IDs (DID/VID)
- User needs to check BDF (Bus:Device:Function) assignments
- User wants to validate BAR (Base Address Register) allocation
- User needs to view or verify the USB device tree
- User encounters "device not found" or enumeration failures
- User asks about PCI capabilities of the xHCI controller

## Key Concepts

### PCI Configuration Space
The xHCI controller is a PCI device with standard configuration space:

| Register       | Offset | Description                              |
|----------------|--------|------------------------------------------|
| VID            | 0x00   | Vendor ID (Intel = 0x8086)               |
| DID            | 0x02   | Device ID (platform-specific)            |
| Command        | 0x04   | PCI command register                     |
| Status         | 0x06   | PCI status register                      |
| RevID          | 0x08   | Revision ID                              |
| ClassCode      | 0x09   | Class code (0x0C0330 for xHCI)           |
| BAR0           | 0x10   | Base Address Register 0 (MMIO base)      |
| BAR1           | 0x14   | Base Address Register 1 (upper 32 bits)  |
| SubsysVID      | 0x2C   | Subsystem Vendor ID                      |
| SubsysDID      | 0x2E   | Subsystem Device ID                      |
| CapPtr         | 0x34   | Capabilities pointer                     |

> **IMPORTANT:** Always verify DID values against the HAS for your specific platform via Co-Design.

### BDF Assignment
```
Bus:Device:Function
  │    │       │
  │    │       └── Function number (0-7)
  │    └────────── Device number (0-31)
  └─────────────── Bus number (0-255)
```

### Device Tree
The USB device tree shows the hierarchy:
```
xHCI Controller (BDF: 00:14.0 typical)
├── USB 3.x Root Hub
│   ├── Port 1 — [Device or empty]
│   ├── Port 2 — [Device or empty]
│   └── Port N — [Device or empty]
└── USB 2.0 Root Hub
    ├── Port 1 — [Device or empty]
    ├── Port 2 — [Device or empty]
    └── Port N — [Device or empty]
```

## Validation Scripts

### View USB Device Tree
```bash
python treeview.py
```
Displays the full USB device hierarchy with speed, VID/PID, and driver info.

### Check Device Enumeration
```bash
python usb_helper_ipsv.py --check-device <port>
```

### Verify Device Speed
```python
from usb_helper_ipsv import USBHelper
helper = USBHelper()
speed = helper.get_speed(port)
# Expected: 4 (SS 5Gbps), 5 (SS+ 10Gbps) for USB 3.x devices
# Expected: 3 (HS 480Mbps) for USB 2.0 devices
```

### Yellow-Bang Detection
```bash
python yellowbang_usb.py
```
Checks for driver failures (yellow exclamation mark in Device Manager).

### NDE (No Device Enumerated) Check
```bash
python NDE_checker.py
```
Detects ports where devices should be present but are not enumerated.

## USB Protocol Enumeration

While the xHCI controller itself is discovered via PCI, USB **devices** are enumerated via the USB protocol. This section covers the protocol-level enumeration flow.

### USB Descriptor Set

After a device connects, the host reads descriptors to identify and configure it:

| Descriptor            | Get via                  | Key Fields                                      |
|-----------------------|--------------------------|-------------------------------------------------|
| **Device Descriptor** | `GET_DESCRIPTOR(0x01)`   | bcdUSB, idVendor, idProduct, bcdDevice, bMaxPacketSize0 |
| **Configuration Descriptor** | `GET_DESCRIPTOR(0x02)` | bNumInterfaces, bConfigurationValue, bmAttributes |
| **Interface Descriptor** | embedded in config   | bInterfaceClass, bInterfaceSubClass, bInterfaceProtocol |
| **Endpoint Descriptor** | embedded in config   | bEndpointAddress, bmAttributes, wMaxPacketSize, bInterval |

### USB2 Reset & Speed Negotiation (Chirp Handshake)

```
Device connect (SE0 / D+ pull-up)
        │
        ├── Host issues Reset (SE0 for ≥10ms)
        ├── Device drives Chirp K (HS capable device)
        ├── Host responds Chirp K–J–K–J–K–J
        │   └── Both sides agree: High Speed (HS, 480 Mbps)
        ├── If no chirp response: Full Speed (FS, 12 Mbps)
        └── Low Speed (LS): D- pull-up, 1.5 Mbps
```

> **Assertion keyword:** `chirp`, `SE0`, `FS.*HS`, `handshake`

### USB3 Link Training (LTSSM)

The USB3 link state machine must reach **U0** (active) from **RxDetect**:

```
RxDetect → Polling.LFPS → Polling.RxEQ → Polling.Active
        → U0 (link active)
```

Key LTSSM states for validation:

| State      | PLS Value | Meaning                          |
|------------|-----------|----------------------------------|
| RxDetect   | 0x5       | Looking for far-end receiver     |
| Polling    | 0x7       | Link training in progress        |
| U0         | 0x0       | Active, link up                  |
| U3         | 0x3       | Suspended                        |
| Compliance | 0xA       | Stuck — signal integrity issue   |

> If PORTSC.PLS stays in **Polling** or **RxDetect** after connect: link training failed.

### USB Address Assignment (SET_ADDRESS)

After Reset, every device starts at address 0. The host assigns a unique address:

```
1. Host sends SETUP token to address 0: SET_ADDRESS(N)
2. Device ACKs, switches to address N within 2ms
3. Host sends GET_DESCRIPTOR to address N to confirm
4. If device fails to respond at new address → enumeration failure
```

> **Common failure:** SET_ADDRESS succeeds but device not found at new address → possible device firmware hang or power issue.

### Hub Enumeration

USB hubs are special devices that extend the bus topology:

```
Root Hub Port (xHCI)
  └── Hub (TT = Transaction Translator for HS hubs)
        ├── Port 1 → Device A (enumerated independently)
        ├── Port 2 → Device B
        └── Port N → ...
```

#### Hub Enumeration Sequence
1. Hub connects to root port → enumerated as a composite device (class 0x09)
2. Hub driver loads → queries hub descriptor for port count
3. Hub starts monitoring each downstream port for connect events
4. Device connects on hub port → hub reports `PORT_CONNECTION` change via interrupt endpoint
5. Host reads `GET_PORT_STATUS` → sees connect status on that port
6. Host issues `SET_FEATURE(PORT_RESET)` on that hub port
7. After reset completes → downstream device is at address 0 on that hub port
8. Host issues `SET_ADDRESS` → device gets unique address
9. Standard descriptor enumeration continues

#### Transaction Translator (TT)
Every USB 2.0 hub contains a **Transaction Translator (TT)** that converts between HS upstream and FS/LS downstream:

| Hub Type | TT Behavior | Impact |
|----------|-------------|--------|
| **Single-TT** | One TT shared across all downstream FS/LS ports | FS/LS devices compete for TT bandwidth — may cause scheduling delays |
| **Multi-TT** | Dedicated TT per downstream port | Better isolation — each FS/LS device gets dedicated translation |

> **Validation note:** Current USB test suites primarily use single-TT hubs. Multi-TT hub testing is an identified gap (see `docs/test_gap_analysis.md` GAP-ENUM #3).

#### Split Transactions (FS/LS behind HS Hub)
When a FS/LS device is behind a HS hub, the xHCI uses **split transactions**:
- **Start-Split (SSPLIT):** Host → Hub at HS, hub converts and sends to device at FS/LS
- **Complete-Split (CSPLIT):** Hub → Host with device response converted back to HS
- Split transactions add latency — timing-sensitive protocols (isochronous) may be affected

#### Hub Port Reset Timing
| Phase | Duration | Notes |
|-------|----------|-------|
| Port reset | ≥10ms (USB 2.0) / ≥20ms (warm reset USB 3.x) | Hub holds reset on downstream port |
| Reset recovery | 10ms | Device must be ready for SET_ADDRESS within this window |
| Address assignment | 50ms max | Host must complete SET_ADDRESS before timeout |

#### Common Hub Enumeration Failures

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Hub enumerated, downstream device not seen | Hub port reset failed or device behind hub didn't respond | Check hub port status via `GET_PORT_STATUS`; try different hub port |
| FS device at wrong speed behind hub | TT not converting correctly | Verify hub is HS; LS/FS device should connect at native speed |
| Intermittent disconnect behind hub | Hub power insufficient for downstream devices | Check hub power descriptor; use powered hub |
| UAOL audio fails behind hub | Split-transaction latency exceeds ACE service interval | Verify PTL+ (MTL had known bug); check hub type (single-TT adds more latency) |

- **UAOL behind hub:** Supported PTL+ (MTL had known silicon bug — see `docs/known_issues.md`)

### Enumeration Failure Triage Quick Reference

| Symptom | Check | Tool |
|---------|-------|------|
| Stuck at address 0 | SET_ADDRESS NAK/STALL | USB analyzer trace |
| Wrong descriptor returned | Device firmware issue | `usb_helper_ipsv.py --get-descriptor` |
| No config selected | bConfigurationValue mismatch | Bus analyzer trace |
| Interface not claimed | Driver binding failure | `yellowbang_usb.py` |
| Hub port not reset | Hub TT issue | PORTSC.PLS on hub port |

## USB Device Class Codes

When a device enumerates, its **Interface Descriptor** carries `bInterfaceClass`, `bInterfaceSubClass`, and `bInterfaceProtocol`. Use this table to identify device type from a descriptor dump or ETL trace.

### USB Base Class Reference

| BaseClass | Name | Notes |
|-----------|------|-------|
| `00h` | Use Interface Descriptor | Device class defined per-interface |
| `01h` | Audio | Microphones, speakers, MIDI |
| `02h` | CDC (Communication) | Serial, RNDIS Ethernet, NCM |
| `03h` | HID | Keyboard, mouse, gamepad, touch |
| `05h` | Physical | Force-feedback joysticks |
| `06h` | Image | Still cameras, scanners |
| `07h` | Printer | USB printers |
| `08h` | Mass Storage | Flash drives, HDDs (MSC/BOT, UAS) |
| `09h` | Hub | USB hubs (see TT-type decode below) |
| `0Ah` | CDC-Data | CDC data interfaces |
| `0Bh` | Smart Card | CCID smart card readers |
| `0Dh` | Content Security | CPRM/CGMS content protection |
| `0Eh` | Video | UVC webcams |
| `0Fh` | Personal Healthcare | Heart rate monitors, glucose meters |
| `10h` | Audio/Video (AV) | Combined AV devices |
| `11h` | Billboard | **Type-C Alt-Mode status device** (see below) |
| `12h` | USB Type-C Bridge | **TCSS bridge device** (see below) |
| `14h` | MCTP over USB | Management Component Transport Protocol |
| `DCh` | Diagnostic | USB Debug devices (see `fv-usb/dbc` sub-skill) |
| `E0h` | Wireless Controller | Bluetooth adapters, WUSB |
| `EFh` | Miscellaneous | Composite devices, IAD |
| `FEh` | Application Specific | DFU (firmware update), IrDA, Test/Measurement |
| `FFh` | Vendor Specific | Custom/proprietary class |

> **Source:** USB-IF Defined Class Codes — https://www.usb.org/defined-class-codes

### Hub TT-Type Decode (Class 09h)

When `bInterfaceClass=09h`, read `bDeviceProtocol` from the **Device Descriptor** (not Interface Descriptor) to determine TT type:

| bDeviceProtocol | TT Type | Meaning |
|-----------------|---------|---------|
| `00h` | Full-Speed Hub | FS hub — no TT (USB 1.x era) |
| `01h` | Single-TT | One TT shared across all FS/LS downstream ports |
| `02h` | Multi-TT | Dedicated TT per downstream port |

```python
# Read bDeviceProtocol from Device Descriptor via usb_helper_ipsv.py
from usb_helper_ipsv import USBHelper
helper = USBHelper()
desc = helper.get_device_descriptor(port)
print(f"Hub TT type: bDeviceProtocol={desc['bDeviceProtocol']:02X}h")
# 00h = FS hub, 01h = Single-TT, 02h = Multi-TT
```

> **Validation note:** Multi-TT hubs provide better isolation for FS/LS devices. Single-TT hubs cause scheduling contention when multiple FS/LS devices are active simultaneously. UAOL isochronous traffic is more sensitive to TT latency — prefer Multi-TT hubs in UAOL test setups.

### Billboard Class (11h) — Type-C Alt-Mode Status

`bInterfaceClass=11h` indicates a **Billboard Device** — a USB interface exposed by a Type-C adapter or dock to report which Alternate Mode (Alt-Mode) is currently active.

| Field | Typical Value | Meaning |
|-------|--------------|---------|
| `bInterfaceClass` | `11h` | Billboard |
| `bInterfaceSubClass` | `00h` | (always 00h) |
| `bInterfaceProtocol` | `00h` | (always 00h) |

**When to expect a Billboard device:**
- USB-C adapter advertising DisplayPort, Thunderbolt, or other Alt-Mode
- Type-C dock during TCSS bring-up
- After `VDM Discover Identity` exchange completes at the Type-C port

**Validation check:**
```bash
# Should see Billboard interface if Alt-Mode negotiation succeeded
python treeview.py  # Look for Class=11h interface on Type-C device
```

> If a Type-C Alt-Mode adapter connects but **no Billboard interface** appears, Alt-Mode negotiation may have failed. Check TCSS port state via `tcss_customs.py`.

### USB Type-C Bridge (12h) — TCSS Bridge

`bInterfaceClass=12h` is the **USB Type-C Bridge** class, used for devices that bridge USB and non-USB protocols over the TCSS (Type-C Subsystem) fabric.

| Field | Value |
|-------|-------|
| `bInterfaceClass` | `12h` |
| Typical device | Intel TBT/USB4 retimer in USB-only mode, some TCSS muxes |
| Relevance | TCSS bring-up, USB4 host-router configuration |

> On NVL/PTL with USB4 Host Router active, a Type-C Bridge interface may appear during initial TCSS port configuration. This is expected behavior — not an enumeration failure.

### Quick Class Code Lookup (PowerShell)

```powershell
# List all USB devices with their class codes on Windows
Get-PnpDevice -Class USB | Select-Object FriendlyName, DeviceID |
  ForEach-Object { $_ }
```

```python
# Parse bInterfaceClass from Interface Descriptor via usb_helper_ipsv.py
from usb_helper_ipsv import USBHelper
helper = USBHelper()
interfaces = helper.get_interfaces(port)
for iface in interfaces:
    print(f"  Interface {iface['bInterfaceNumber']}: "
          f"Class={iface['bInterfaceClass']:02X}h "
          f"SubClass={iface['bInterfaceSubClass']:02X}h "
          f"Protocol={iface['bInterfaceProtocol']:02X}h")
```

---

## eUSB2 PHY Enumeration (NVL)

Nova Lake (NVL) is the first Intel client platform to **fully transition to eUSB2 PHY** for all USB 2.0 ports. There is no legacy USB2 PHY fallback on NVL.

> **Note:** PTL uses standard USB2 PHY by default (eUSB2 is only an optional PCB stuffing option on PTL boards). This section applies to **NVL only**.

### Architecture

| Feature | NVL eUSB2 |
|---------|-----------|
| **PHY IP** | Synopsys eUSB2 (2 instances of x4 PHY) |
| **Max Ports** | 8 eUSB2 ports (PCD-H die) |
| **Default Mode** | Repeater mode (native mode supported but not default) |
| **Repeaters** | Required on all walk-up ports (Type-A and Type-C) unless ecosystem supports native eUSB2 |

### eUSB2 vs Legacy USB2 Enumeration Differences

| Aspect | Legacy USB2 PHY | eUSB2 PHY (NVL) |
|--------|-----------------|------------------|
| Signal levels | 3.3V signaling | 1.2V native; repeater converts to 3.3V at connector |
| Initialization | Direct PHY init | Requires repeater handshake before link-up |
| Speed negotiation | Chirp handshake on wire | Chirp handshake via repeater (transparent if repeater trained) |
| Low-power states | Standard USB2 suspend | eUSB2 L1/L2 states mapped to repeater sleep |

### eUSB2 Enumeration Flow

```
eUSB2 PHY Init
    │
    ├── Repeater detection (HSIO lane assigned to eUSB2)
    ├── Repeater training (PHY ↔ Repeater link-up)
    │   └── If repeater training fails → port stays in Disabled (PLS=4)
    ├── Standard USB2 connect signaling (via repeater)
    ├── Chirp handshake (HS negotiation — transparent through repeater)
    └── Normal USB2 enumeration (SET_ADDRESS, GET_DESCRIPTOR, etc.)
```

### Common eUSB2 Failures

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Port stuck at PLS=4 (Disabled) | Repeater not trained | Check HSIO PHY lane config, verify repeater is populated on board |
| FS instead of HS | Repeater in bypass mode | Verify repeater config, check BIOS eUSB2 knob |
| Intermittent disconnect | Signal integrity at 1.2V boundary | Check board routing, verify repeater power rail |
| Enumeration timeout | PHY init sequence stalled | Dump eUSB2 PHY status via PythonSV (see below) |

### PythonSV: Check eUSB2 PHY Status

```python
# Show eUSB2 PHY status for port 0 (NVL)
sv.socket0.uncore.usb.eusb2phy[0].show()

# Check repeater training status
sv.socket0.uncore.usb.eusb2phy[0].repeater_status.show()
```

> **IMPORTANT:** Exact register paths depend on NVL die variant (PCD-H vs PCD-S). Always verify against the HAS via Co-Design: *"Show eUSB2 PHY registers from NVL_HSIO_PHY_SoC_Integration_HAS"*

### References
- [NVL USB32_20 PAS](https://docs.intel.com/documents/clientplatform/domains/usb32_20/nvl/NVL_USB32_20_PAS.html)
- [NVL HSIO PHY SoC Integration HAS](https://docs.intel.com/documents/pch_doc/nvl/pcd-h/HAS/NVL_HSIO_PHY_SoC_Integration_HAS/NVL_HSIO_PHY_SoC_Integration_HAS.html)

---

## Common Enumeration Failures

| Symptom                        | Likely Cause                         | First Action                        |
|--------------------------------|--------------------------------------|-------------------------------------|
| Device not in tree             | Cable/connector issue, port disabled | Check PORTSC.CCS, reseat cable      |
| Wrong speed (HS instead of SS) | SS link training failed              | Check LTSSM, verify SS cable        |
| Yellow-bang in Device Manager  | Driver load failure                  | Check driver version, event log     |
| BDF not present                | xHCI disabled in BIOS               | Verify BIOS USB enable knob         |
| BAR not allocated              | MMIO resource conflict               | Check PCI resource allocation       |

## Co-Design Lookup
Use the Playwright browser workflow to query Co-Design HAS for DID/VID and BDF data:
1. `playwright_browser_navigate` to `https://chat.co-design.intel.com/chat`
2. `playwright_browser_snapshot` to locate the chat textarea
3. `playwright_browser_type` your query, then `playwright_browser_wait_for` the response
4. `playwright_browser_snapshot` to read the answer

> **Fallback:** If the browser is unavailable, load the `codesign` skill for REST API access.

**Domain-specific queries:**
- *"What is the xHCI Device ID for [platform] USB controller?"*
- *"What is the default BDF for USB xHCI on [platform]?"*

## Return Codes (usb_helper_ipsv.py)

| Code | Meaning              |
|------|----------------------|
| 0    | PASS — device found  |
| 1    | FAIL                 |
| 12   | Device not found     |
| 13   | Configuration error  |
