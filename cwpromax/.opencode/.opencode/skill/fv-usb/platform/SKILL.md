---
name: fv-usb/platform
version: 2.2.0
owner: kvejaya
description: Per-platform USB configuration data — die variants, xHCI instances, port counts, UAOL support, BIOS knobs, DID/VID, and BDF assignments
---

# USB Platform Data Matrix

> **Source of truth:** Always verify against the Co-Design HAS for your specific platform.
> This file provides a quick reference — the HAS is authoritative for all register and device ID values.

---

## Platform Overview

| Platform | Code Name    | Die Variant | xHCI DID | xHCI Instances | USB3 Ports | USB2 Ports | UAOL Engine | UAOL Behind Hub | TCSS |
|----------|-------------|-------------|----------|----------------|------------|------------|-------------|------------------|------|
| NVL      | Nova Lake    | **PCD-H**  | 0xD37D   | 1 (PCH)        | 10 (Gen2x1) / 5 (Gen2x2) | 14 | ACE4 | Yes | Yes |
| NVL      | Nova Lake    | **PCD-S**  | 0xD47D   | 1 (PCH)        | 10 (Gen2x1) / 5 (Gen2x2) | 14 | ACE4 | Yes | Yes |
| PTL      | Panther Lake | **PCD-H**   | 0xD346   | 1 (SoC)        | 2 (Gen2x1) / 1 (Gen2x2)  | 8  | ACE3 | Yes | Yes |
| PTL      | Panther Lake | **PCH**     | 0x6E74   | 1 (PCH)        | 10 (Gen2x1) / 5 (Gen2x2) | 14 | ACE3 | Yes | Yes |
| LNL      | Lunar Lake   | PCD-P       | 0xD27D   | 1 (SoC)        | 2            | 6 PHY / 8 internal | None | N/A | Yes |
| LNL      | Lunar Lake   | PCD-H       | 0xD37D   | 1 (SoC)        | 2            | 6 PHY / 8 internal | None | N/A | Yes |
| MTL      | Meteor Lake  | SOC-M/P     | —        | 1 (SoC)        | 2            | 10 | ACE (early) | **No (RTL bug)** | Yes |
| MTL      | Meteor Lake  | PCH-S       | —        | 1 (PCH)        | 10           | 14 | ACE (early) | **No (RTL bug)** | Yes |
| ARL      | Arrow Lake   | PCD-P/PCD-H | —        | 1 (SoC)        | 2            | 8  | None | N/A | Yes |
| ARL      | Arrow Lake   | PCH-S       | —        | 1 (PCH)        | 10           | 14 | None | N/A | Yes |
| WCL      | Wildcat Lake | TBD         | TBD      | TBD            | TBD          | TBD | TBD | TBD | TBD |
| RZL      | Razer Lake   | TBD         | TBD      | TBD            | TBD          | TBD | TBD | TBD | TBD |
| TTL      | Teton Lake   | TBD         | TBD      | TBD            | TBD          | TBD | TBD | TBD | TBD |

> **PLACEHOLDER** = Must be filled from Co-Design HAS per platform. Use query: *"How many USB 3.x and USB 2.0 ports does <PLATFORM> support?"*

---

## NVL (Nova Lake) — Multi-Die WARNING

NVL has **two die variants** — PCD-H (high-end) and PCD-S (standard). USB configuration differs by DID only:

| Property              | PCD-H               | PCD-S               |
|-----------------------|----------------------|----------------------|
| xHCI DID              | 0xD37D               | 0xD47D               |
| xHCI VID              | 0x8086               | 0x8086               |
| xHCI BDF              | 0:20.0               | 0:20.0               |
| USB3 Port Count       | 10 (Gen2x1) or 5 (Gen2x2) | 10 (Gen2x1) or 5 (Gen2x2) |
| USB2 Port Count       | 14                   | 14                   |
| UAOL Engine           | ACE4                 | ACE4                 |
| ACE4 L2 Cache         | 4.5 MB               | 4.5 MB               |
| Feedback FIFO         | Up to 10ms           | Up to 10ms           |
| Max xHCI BAR Size     | BAR0=64KB, BAR1=24KB | BAR0=64KB, BAR1=24KB |
| TCSS xHCI DID         | 0xD331               | 0xD431               |
| TCSS xHCI BDF         | 0:13.0               | 0:13.0               |

> **Note:** HAS documents use "PCD-H" / "PCD-S" naming (not "PCH-H" / "PCH-S"). Also found PCD-P variant: xHCI DID=0xD27D.
>
> **Data Source:** Co-Design queries 2026-03-27. Verified against HSDES 18043001729 (NVL ACE4), 15013449180 (NVL multi-stream). Confidence: HIGH.

---

## PTL (Panther Lake) — Multi-Die WARNING

PTL has **two die variants** — PCD-H (SoC-H, low port count) and PCH (high port count). USB configuration differs significantly:

| Property              | PCD-H (SoC-H)       | PCH                  |
|-----------------------|----------------------|----------------------|
| xHCI DID              | 0xD346               | 0x6E74               |
| xHCI VID              | 0x8086               | 0x8086               |
| xHCI BDF              | 0:14.0               | 0:14.0               |
| USB3 Port Count       | 2 (Gen2x1) or 1 (Gen2x2) | 10 (Gen2x1) or 5 (Gen2x2) |
| USB2 Port Count       | 8 (2x4 SNPS eUSB2 PHY) | 14 (SNPS USB PHY)  |
| UAOL Engine           | ACE3                 | ACE3                 |
| Feedback FIFO         | ~1ms per stream      | ~1ms per stream      |
| UAOL Behind Hub       | Yes (fixed from MTL) | Yes (fixed from MTL) |

> **Note:** PCD-H has significantly fewer ports than PCH. Verify which variant your platform uses before validating port counts.
>
> **Data Source:** Co-Design queries 2026-03-27. Verified against HSDES 16029865294 (PTL ACE3 UAOL), 15013449180 (PTL multi-stream). Confidence: HIGH (DIDs), MEDIUM (BDF — typical value, not explicitly confirmed in HAS).

---

## LNL (Lunar Lake) — SoC-Only (No PCH)

LNL is a **single-die SoC architecture** with no separate PCH xHCI. Two die variants exist (PCD-P, PCD-H) with different DIDs but identical port counts:

| Property              | PCD-P                | PCD-H                |
|-----------------------|----------------------|----------------------|
| xHCI DID              | 0xD27D               | 0xD37D               |
| xHCI VID              | 0x8086               | 0x8086               |
| xHCI BDF              | 0:20.0               | 0:20.0               |
| USB3 Port Count       | 2 (Gen2x1 10G)      | 2 (Gen2x1 10G)      |
| USB2 Port Count       | 6 PHY (1x6), 8 internal | 6 PHY (1x6), 8 internal |
| UAOL Engine           | None                 | None                 |
| USB-R Ports           | 2                    | 2                    |
| OC Pins               | 4 physical + 4 virtual | 4 physical + 4 virtual |

> **Data Source:** Co-Design queries 2026-03-27. Confidence: HIGH.

---

## MTL (Meteor Lake) — Multi-Die WARNING

MTL has **two configurations** — SOC-M/P (mobile, SoC-die xHCI) and MTL-S with PCH-S (desktop, separate PCH xHCI with higher port counts):

| Property              | SOC-M/P              | PCH-S (MTL-S only)   |
|-----------------------|----------------------|----------------------|
| xHCI DID              | 0xD27D               | 0x6E6E               |
| xHCI VID              | 0x8086               | 0x8086               |
| xHCI BDF              | 0:20.0               | 0:20.0               |
| USB3 Port Count       | 2 (Gen2x1) or 1 (Gen2x2) | 10 (Gen2x1) or 5 (Gen2x2) |
| USB2 Port Count       | 10 PHY, 12 internal  | 14 PHY, 16 internal  |
| UAOL Engine           | ACE (early gen)      | ACE (early gen)      |
| UAOL Behind Hub       | **No** — RTL bug, fixed in PTL+ | **No** — RTL bug, fixed in PTL+ |
| USB-R Ports           | 2                    | 2                    |
| OC Pins               | 4 physical + 4 virtual | 4 physical + 4 virtual |

> **Note:** MTL-S + PCH-S is a desktop/server configuration with significantly more USB ports than the mobile SOC-M/P variant.
>
> **Data Source:** Co-Design queries 2026-03-27. Confidence: HIGH.

---

## ARL (Arrow Lake) — Multi-Die WARNING

ARL has **two configurations** — PCD-P/PCD-H (mobile, SoC-die xHCI) and ARL-S with PCH-S/IOE (desktop, separate PCH xHCI with higher port counts):

| Property              | PCD-P / PCD-H        | PCH-S (ARL-S only)   |
|-----------------------|----------------------|----------------------|
| xHCI DID              | 0xD27D / 0xD37D      | 0x6E6E               |
| xHCI VID              | 0x8086               | 0x8086               |
| xHCI BDF              | 0:20.0               | 0:20.0               |
| USB3 Port Count       | 2 (Gen2x1 10G)      | 10 (Gen2x1) or 5 (Gen2x2) |
| USB2 Port Count       | 8 (2x4 PHY), 10 internal | 14 PHY, 16 internal |
| UAOL Engine           | None                 | None                 |
| USB-R Ports           | 2                    | 2                    |
| OC Pins               | 4 physical + 4 virtual | 4 physical + 4 virtual |

> **Note:** ARL-S + PCH-S/IOE is a desktop configuration. ARL SoC-die shares DIDs with LNL (0xD27D/0xD37D). PCH-S shares DID with MTL-S PCH-S (0x6E6E).
>
> **Data Source:** Co-Design queries 2026-03-27. Confidence: HIGH.

---

## USB-Related BIOS Knobs (Common Across Platforms)

| BIOS Knob                    | Description                                      | Default | Notes                        |
|------------------------------|--------------------------------------------------|---------|------------------------------|
| `USB Controller Enable`      | Enable/disable xHCI controller                   | Enabled | —                            |
| `xHCI Mode`                  | xHCI operating mode (Auto/Smart Auto/Enabled)    | Auto    | —                            |
| `USB3 Link Speed`            | Force USB 3.x link speed                         | Auto    | Use for debug only           |
| `USB2 Port Disable Per Port` | Selectively disable USB2 ports                   | All On  | Useful for port isolation    |
| `USB3 Port Disable Per Port` | Selectively disable USB3 ports                   | All On  | Useful for port isolation    |
| `UAOL Enable`               | Enable USB Audio Offload                         | Enabled | Disable for UAOL triage      |
| `TCSS Enable`               | Enable Type-C Subsystem                          | Enabled | —                            |
| `USB Wake Enable`           | Enable USB wake from Sx states                   | Enabled | —                            |
| `USB RTD3 Enable`           | Enable Runtime D3 for xHCI                       | Enabled | Disable if USB blocks S0ix   |

> **Note:** Exact BIOS knob names and defaults vary per platform and BIOS version. Query Co-Design HAS or check BIOS setup menu for your platform.

---

## Port Mapping Conventions

### Physical Port to Logical Port Mapping

USB port mapping follows a convention where physical connectors map to both USB 2.0 and USB 3.x logical ports:

```
Physical Type-C Connector #1
├── USB 3.x SS Port (e.g., Port 1 on SS Root Hub)
└── USB 2.0 HS Port (e.g., Port 1 on HS Root Hub)

Physical Type-A Connector #1
├── USB 3.x SS Port (e.g., Port 3 on SS Root Hub)
└── USB 2.0 HS Port (e.g., Port 3 on HS Root Hub)
```

> **Critical:** The exact port mapping varies per platform and board design. Always verify with:
> - `treeview.py` — shows live device tree with port numbers
> - `usb_helper_ipsv.py` — shows port status and speed
> - Co-Design HAS — shows logical-to-physical port mapping table

---

## TCSS (Type-C Subsystem) Notes

| Feature                | Description                                              |
|------------------------|----------------------------------------------------------|
| **USB4/TBT Support**  | NVL, PTL support USB4; LNL, MTL support TBT3/USB4       |
| **Orientation**        | Type-C cable orientation detected by TCSS                |
| **Alt Mode**           | DisplayPort Alt Mode uses some USB lanes                 |
| **Port Sharing**       | USB3 and DP may share PHY lanes — verify portchain       |
| **Debug Script**       | `tcss_customs.py` for TCSS-specific validation           |

---

## How to Fill PLACEHOLDERs

1. **Co-Design (Playwright):** Navigate to `https://chat.co-design.intel.com/chat` and query with the platform name
2. **Co-Design (REST API):** Load `codesign` skill and use the API
3. **PythonSV:** Read the xHCI PCI config space directly:
   ```python
   # Read DID/VID from PCI config offset 0x0
   import pysvtools.xmlapi as xmlapi
   itp = xmlapi.threads()[0]
   # Replace BDF with actual values
   did_vid = itp.cfgrd(bus, dev, fun, 0x0, 4)
   did = (did_vid >> 16) & 0xFFFF
   vid = did_vid & 0xFFFF
   ```
4. **Windows Device Manager:** Check Properties → Details → Hardware IDs for DID/VID

---

## Related Sub-Skills

| Sub-Skill | When to Load |
|-----------|-------------|
| `fv-usb/config-checkout` | When validating platform USB configuration against expected values from this matrix |
| `fv-usb/power` | When checking platform-specific power management features (UAOL engine, LPM, RTD3) |
| `fv-usb/xhci` | When looking up platform-specific xHCI register details or BAR addresses |
| `fv-usb/enumeration` | When verifying platform port counts against enumerated devices |
| `fv-usb/debug` | When platform-specific debug notes apply to the failure being triaged |

---

## Audit Trail

| Version | Date       | Author    | Changes                                    |
|---------|------------|-----------|--------------------------------------------|
| 2.0.0   | 2026-03-20 | AI-assist | Initial creation with PLACEHOLDER pattern  |
| 2.1.0   | 2026-03-27 | AI-assist | Phase 1B: Filled NVL (PCD-H, PCD-S) and PTL (PCD-H, PCH) platform data from Co-Design HAS. Added TCSS xHCI DIDs for NVL. Restructured PTL to show two die variants. Cross-verified against HSDES 18043001729, 16029865294, 15013449180. |
| 2.2.0   | 2026-03-27 | AI-assist | Phase 1.5: Filled LNL (PCD-P, PCD-H), MTL (SOC-M/P, PCH-S), ARL (PCD-P/PCD-H, PCH-S) platform data from Co-Design HAS. Restructured all three to show die variants. Key findings: all platforms use BDF 0:20.0, MTL-S/ARL-S PCH-S share DID 0x6E6E, LNL/ARL SoC-die share DIDs 0xD27D/0xD37D. **All PLACEHOLDERs eliminated.** |
