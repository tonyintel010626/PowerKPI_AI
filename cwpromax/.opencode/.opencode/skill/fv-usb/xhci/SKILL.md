---
name: xhci
version: 2.0.0
owner: kvejaya
description: xHCI host controller register maps, capability structures, command/transfer/event rings, PORTSC, PLS, USB speed encoding, and PythonSV direct silicon access
---

> **Owner**: Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

# FV-USB / xHCI — eXtensible Host Controller Interface

## Purpose
This sub-skill covers xHCI host controller register maps, capability structures, operational registers, command/transfer/event rings, and protocol-specific features for USB 2.0 and USB 3.x.

## When to Use
- User asks about xHCI registers (PORTSC, PORTPMSC, PORTLI, USBCMD, USBSTS, etc.)
- User needs to understand xHCI capability structures
- User asks about command ring, transfer ring, or event ring operations
- User needs to interpret xHCI register dumps
- User asks about TRB (Transfer Request Block) structures
- User asks about xHCI interrupter configuration

## Key Concepts

### xHCI Register Spaces

The xHCI controller has four register spaces, all accessed via BAR0:

| Space              | Offset from BAR0   | Description                           |
|--------------------|---------------------|---------------------------------------|
| **Capability**     | 0x00                | Read-only capability parameters        |
| **Operational**    | CAPLENGTH           | Runtime control and status             |
| **Runtime**        | RTSOFF              | Interrupter registers                  |
| **Doorbell**       | DBOFF               | Doorbell array for endpoints           |

> **IMPORTANT:** Always verify register offsets against the HAS via Co-Design. Offsets may vary per platform.

### Capability Registers

| Register    | Offset | Description                                    |
|-------------|--------|------------------------------------------------|
| CAPLENGTH   | 0x00   | Capability register length (byte)              |
| HCIVERSION  | 0x02   | xHCI version (e.g., 0x0110 = v1.1)            |
| HCSPARAMS1  | 0x04   | Structural params — MaxSlots, MaxIntrs, MaxPorts |
| HCSPARAMS2  | 0x08   | Structural params — IST, ERST Max, SPB Max     |
| HCSPARAMS3  | 0x0C   | Structural params — U1/U2 exit latency         |
| HCCPARAMS1  | 0x10   | Capability params — 64-bit, BW neg, context sz |
| DBOFF       | 0x14   | Doorbell array offset                          |
| RTSOFF      | 0x18   | Runtime register space offset                  |
| HCCPARAMS2  | 0x1C   | Capability params 2 — extended capabilities    |

### Operational Registers

| Register    | Offset        | Description                              |
|-------------|---------------|------------------------------------------|
| USBCMD      | CAPLENGTH+0x00| USB Command — Run/Stop, HCRST, INTE      |
| USBSTS      | CAPLENGTH+0x04| USB Status — HCH, HSE, EINT, PCD         |
| PAGESIZE    | CAPLENGTH+0x08| Page size register                        |
| DNCTRL      | CAPLENGTH+0x14| Device Notification Control               |
| CRCR        | CAPLENGTH+0x18| Command Ring Control Register             |
| DCBAAP      | CAPLENGTH+0x30| Device Context Base Address Array Pointer |
| CONFIG      | CAPLENGTH+0x38| Configure register — MaxSlotsEn           |

### Port Registers (Per-Port, starting at CAPLENGTH + 0x400)

Each port has a 16-byte register set at offset `0x400 + (16 * (port - 1))`:

| Register    | Port Offset | Description                              |
|-------------|-------------|------------------------------------------|
| **PORTSC**  | 0x00        | Port Status and Control                  |
| **PORTPMSC**| 0x04        | Port Power Management Status and Control |
| **PORTLI**  | 0x08        | Port Link Info                           |
| **PORTHLPMC**| 0x0C       | Port Hardware LPM Control                |

### USB Speed Encoding

| PORTSC Speed Value | USB Name         | Official Gen Name  | Marketing Name          | Data Rate         |
|--------------------|------------------|--------------------|-------------------------|-------------------|
| 1                  | Low Speed        | —                  | Low Speed               | 1.5 Mbps          |
| 2                  | Full Speed       | —                  | Full-Speed              | 12 Mbps           |
| 3                  | High Speed       | —                  | Hi-Speed                | 480 Mbps          |
| 4                  | SuperSpeed       | **Gen 1×1**        | SuperSpeed USB 5Gbps    | 5 Gbps            |
| 5                  | SuperSpeed+      | **Gen 2×1**        | SuperSpeed USB 10Gbps   | 10 Gbps           |
| 6                  | SuperSpeed+      | **Gen 2×2**        | SuperSpeed USB 20Gbps   | 20 Gbps           |

> **Official USB 3.2 Gen naming** (USB Data Performance Language Usage Guidelines, Jan 2024):
> - Gen 1×1 = 5 Gbps single-lane (was "USB 3.1 Gen 1" / "USB 3.0")
> - Gen 1×2 = 10 Gbps dual-lane (not shown in PORTSC — dual-lane SuperSpeed)
> - Gen 2×1 = 10 Gbps single-lane (was "USB 3.1 Gen 2")
> - Gen 2×2 = 20 Gbps dual-lane (USB 3.2 only)
>
> **Marketing names** use "Gbps" (not "Gbits/s" or "Gb/s") per USB-IF guidelines.
> PORTSC Speed=6 covers Gen 2×2 only; Gen 1×2 also reaches 10 Gbps but via a different physical configuration.
>
> USB 2.0: Full-Speed (12 Mbps), Hi-Speed (480 Mbps), Low Speed (1.5 Mbps).

### PORTSC Register Bit-Fields

| Bit(s) | Field | Description                              |
|--------|-------|------------------------------------------|
| 0      | CCS   | Current Connect Status (1=connected)     |
| 1      | PED   | Port Enabled/Disabled (1=enabled)        |
| 3      | OCA   | Over-Current Active                      |
| 4      | PR    | Port Reset                               |
| 8:5    | PLS   | Port Link State (see LTSSM states)       |
| 9      | PP    | Port Power (1=powered)                   |
| 13:10  | Speed | Port Speed (see USB Speed Encoding table above) |
| 16     | LWS   | Link State Write Strobe                  |
| 17     | CSC   | Connect Status Change                    |
| 20     | OCC   | Over-Current Change                      |
| 21     | PRC   | Port Reset Change                        |
| 22     | PLC   | Port Link State Change                   |
| 25     | WCE   | Wake on Connect Enable                   |
| 26     | WDE   | Wake on Disconnect Enable                |
| 27     | WOE   | Wake on Over-Current Enable              |
| 30     | DR    | Device Removable                         |
| 31     | WPR   | Warm Port Reset                          |

### PLS (Port Link State) Values

| Value | USB 3.x State    | USB 2.0 State       |
|-------|------------------|----------------------|
| 0     | U0 (Active)      | L0 (Active)          |
| 1     | U1 (Standby)     | L1 (Sleep)           |
| 2     | U2 (Sleep)       | L2 (Suspend)         |
| 3     | U3 (Suspend)     | L2 (Suspend)         |
| 4     | Disabled         | Disabled             |
| 5     | Rx.Detect        | —                    |
| 6     | Inactive         | —                    |
| 7     | Polling          | —                    |
| 8     | Recovery         | —                    |
| 9     | Hot Reset        | —                    |
| 10    | Compliance Mode  | —                    |
| 11    | Test Mode        | Test Mode            |
| 15    | Resume           | Resume               |

### xHCI Ring Architecture

```
Command Ring (Host → Controller)
  ├── Link TRB → wraps ring
  ├── Enable Slot Command
  ├── Address Device Command
  ├── Configure Endpoint Command
  └── ...

Transfer Ring (Host → Controller, per endpoint)
  ├── Normal TRB (bulk/interrupt)
  ├── Setup Stage TRB (control)
  ├── Data Stage TRB (control)
  ├── Status Stage TRB (control)
  ├── Isoch TRB (isochronous)
  └── Link TRB → wraps ring

Event Ring (Controller → Host)
  ├── Transfer Event TRB
  ├── Command Completion Event TRB
  ├── Port Status Change Event TRB
  └── ...
```

### TRB Types (Common)

| Type | Value | Description                    |
|------|-------|--------------------------------|
| Normal | 1   | Bulk/Interrupt data transfer   |
| Setup Stage | 2 | Control setup stage          |
| Data Stage | 3  | Control data stage           |
| Status Stage | 4 | Control status stage        |
| Isoch | 5    | Isochronous transfer           |
| Link | 6     | Link to next ring segment      |
| No Op | 8    | No operation                   |
| Enable Slot | 9 | Enable device slot           |
| Disable Slot | 10 | Disable device slot        |
| Address Device | 11 | Set device address         |
| Configure EP | 12 | Configure endpoints         |
| Transfer Event | 32 | Transfer completion event  |
| Command Completion | 33 | Command completion event |
| Port Status Change | 34 | Port change event        |

## Register Access via Scripts

### Read PORTSC (svregisters.py wrapper)
```python
from svregisters import SVRegisters
sv = SVRegisters()
portsc = sv.read_portsc(port_number)
print(f"CCS={portsc.ccs}, PED={portsc.ped}, Speed={portsc.speed}, PLS={portsc.pls}")
```

### Read Capabilities (svregisters.py wrapper)
```python
caplength = sv.read_cap(0x00)
hcsparams1 = sv.read_cap(0x04)
max_ports = (hcsparams1 >> 24) & 0xFF
max_slots = hcsparams1 & 0xFF
```

### PythonSV Register Access (direct silicon access)

> **IMPORTANT:** PythonSV requires host-target pairing before use. Run the pairing step first.
> Load `pysv` skill for full PythonSV setup instructions.
> **PTL NOTE:** Do NOT use f-strings in PythonSV scripts on PTL — use `.format()` or `%` formatting instead.

```python
# Read PORTSC for port 1 (adjust socket/path for your platform)
sv.socket0.uncore.usb.xhci.portsc[0].show()

# Read USBSTS — check for HSE (Host System Error) bit
sv.socket0.uncore.usb.xhci.usbsts.show()

# Read USBCMD — check Run/Stop bit
sv.socket0.uncore.usb.xhci.usbcmd.show()

# Read specific PORTSC fields
pls  = sv.socket0.uncore.usb.xhci.portsc[0].pls    # Port Link State (0-15)
ccs  = sv.socket0.uncore.usb.xhci.portsc[0].ccs    # Current Connect Status
ped  = sv.socket0.uncore.usb.xhci.portsc[0].ped    # Port Enabled/Disabled
spd  = sv.socket0.uncore.usb.xhci.portsc[0].speed  # Port Speed (0-7)

# Read PORTPMSC — LPM control
sv.socket0.uncore.usb.xhci.portpmsc[0].show()

# Read HCSPARAMS1 — max ports, slots, interrupters
sv.socket0.uncore.usb.xhci.hcsparams1.show()

# Show all port statuses at once
for i in range(sv.socket0.uncore.usb.xhci.hcsparams1.maxports):
    print("Port", i, ": PLS=", sv.socket0.uncore.usb.xhci.portsc[i].pls,
          "CCS=", sv.socket0.uncore.usb.xhci.portsc[i].ccs,
          "Speed=", sv.socket0.uncore.usb.xhci.portsc[i].speed)
```

### Per-Platform BAR Notes

| Platform | BAR0 Notes                                                                                   |
|----------|----------------------------------------------------------------------------------------------|
| NVL      | PCH-H and PCH-S have separate USB controllers — BAR0 address differs per die variant. Always confirm BDF and BAR from OS `lspci` / Device Manager before assuming addresses. |
| LNL      | Integrated SoC die — USB controller BAR0 is on the SoC die, not separate PCH. Higher base address expected vs discrete PCH designs. |
| MTL/ARL  | Standard discrete PCH BAR allocation. Typical MMIO base in 32-bit or 64-bit range depending on BIOS resource allocation. |
| PTL      | Two-die design (SoC + PCH) — USB on PCH die. Verify BDF 00:14.0 in OS before accessing via PythonSV. |

> **Always verify:** Read BAR0 from PCI config space (`sv.read_config_dword(bdf, 0x10)`) before accessing MMIO registers directly. Never hard-code BAR addresses across platforms.

## Co-Design Lookup
Use the Playwright browser workflow to query Co-Design HAS for xHCI register details:
1. `playwright_browser_navigate` to `https://chat.co-design.intel.com/chat`
2. `playwright_browser_snapshot` to locate the chat textarea
3. `playwright_browser_type` your query, then `playwright_browser_wait_for` the response
4. `playwright_browser_snapshot` to read the answer

> **Fallback:** If the browser is unavailable, load the `codesign` skill for REST API access.

**Domain-specific queries:**
- *"Show me the xHCI PORTSC register layout from NVL_USB_HAS"*
- *"What are the xHCI extended capabilities for [platform]?"*

## Common xHCI Issues

| Symptom                          | Register to Check     | What to Look For                |
|----------------------------------|-----------------------|---------------------------------|
| Controller not running           | USBCMD, USBSTS       | Run/Stop=0, HCH=1              |
| Port not enabled                 | PORTSC                | PED=0, check PLS               |
| Link in compliance mode          | PORTSC.PLS            | PLS=10 (Compliance)            |
| Transfer timeout                 | Event Ring            | Missing Transfer Event TRB     |
| Host system error                | USBSTS.HSE            | HSE=1, check MMIO access       |
| Wrong speed                      | PORTSC.Speed          | Compare expected vs actual      |
| Gen2/SSP not working at OS level | HCIVERSION            | Must be `0x0110` (xHCI v1.1). If `0x0100` (xHCI v1.0), OS driver blocks SSP |
| PM clock request stuck high      | USBCMD.RS + PORTSC.PP | Must clear Run bit AND port power before clkreq de-asserts |

### HCIVERSION Value Decode

The `HCIVERSION` field at capability offset `0x02` identifies the xHCI specification version. The OS driver checks this before enabling SuperSpeedPlus (Gen2) support:

| Value   | Version  | SSP (Gen2) Support | Notes |
|---------|----------|--------------------|-------|
| `0x0100`| xHCI 1.0 | **Blocked** — OS driver will not enable Gen2 | RTL bug if platform should support Gen2 |
| `0x0110`| xHCI 1.1 | **Enabled** | Required for Gen2×1 (10G) and Gen2×2 (20G) |

```python
# Read HCIVERSION via PythonSV
hciversion = sv.socket0.uncore.usb.xhci.hciversion  # Expected: 0x0110
print("HCIVERSION = %04x" % hciversion)
# 0x0110 = xHCI 1.1 (Gen2 supported)
# 0x0100 = xHCI 1.0 (Gen2 BLOCKED by driver) → file HSDES RTL sighting
```

> **Root cause pattern (from HSDES 1304166922):** FPGA/pre-silicon RTL sometimes has HCIVERSION=0x0100. The Windows USB driver reads this register and gates SSP/Gen2 enumeration on version >= 0x0110. A device that physically supports 10G will enumerate as 5G or HS if HCIVERSION is wrong.
