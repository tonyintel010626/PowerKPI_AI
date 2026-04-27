# FV-USB — HAS Extraction Template

<!-- owner: kvejaya -->

> Last Updated: 2026-03-20
> This template guides systematic extraction of USB/xHCI information from Hardware Architecture Specification (HAS) documents via Co-Design.

---

## Purpose

When a new platform HAS document becomes available, use this template to extract all USB-relevant information and populate the FV-USB skill files. This ensures consistent, complete coverage across all platforms.

---

## Extraction Checklist

### Section 1 — Device Identification

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| xHCI Device ID (DID) | *"What is the xHCI Device ID (DID) from <PLATFORM>_USB_HAS?"* | `config-checkout/SKILL.md` DID table |
| xHCI Vendor ID (VID) | *"What is the xHCI Vendor ID from <PLATFORM>_USB_HAS?"* | `config-checkout/SKILL.md` |
| PCI BDF | *"What is the default BDF for the xHCI controller in <PLATFORM>?"* | `config-checkout/SKILL.md`, `enumeration/SKILL.md` |
| Revision ID | *"What is the Revision ID for xHCI in <PLATFORM>_USB_HAS?"* | `config-checkout/SKILL.md` |
| SSID/SSVID | *"What is the Subsystem ID for xHCI in <PLATFORM>?"* | `enumeration/SKILL.md` |

### Section 2 — Register Maps

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| BAR0 size & alignment | *"What is the BAR0 size and alignment for xHCI in <PLATFORM>_USB_HAS?"* | `xhci/SKILL.md` BAR notes |
| PORTSC offset/layout | *"Show the PORTSC register bit-fields from <PLATFORM>_USB_HAS"* | `xhci/SKILL.md` PORTSC section |
| HCSPARAMS1 | *"Show HCSPARAMS1 register fields for <PLATFORM> xHCI"* | `xhci/SKILL.md` Capability section |
| HCSPARAMS2 | *"Show HCSPARAMS2 register fields for <PLATFORM> xHCI"* | `xhci/SKILL.md` |
| HCCPARAMS1/2 | *"Show HCCPARAMS1 and HCCPARAMS2 for <PLATFORM> xHCI"* | `xhci/SKILL.md` |
| PMCS offset | *"What is the PMCS register offset for xHCI in <PLATFORM>?"* | `power/SKILL.md` |
| Debug Capability offset | *"What is the debug capability register offset for USB on <PLATFORM>?"* | `xhci/SKILL.md` |
| Platform-specific registers | *"List all platform-specific (non-standard) xHCI registers in <PLATFORM>_USB_HAS"* | `xhci/SKILL.md` |

### Section 3 — Port Configuration

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| USB2 port count | *"How many USB2 ports are in <PLATFORM> xHCI?"* | `config-checkout/SKILL.md`, `platform/SKILL.md` |
| USB3 port count | *"How many USB3 ports are in <PLATFORM> xHCI?"* | `config-checkout/SKILL.md`, `platform/SKILL.md` |
| Max speed per port | *"What is the maximum USB speed per port for <PLATFORM>?"* | `platform/SKILL.md` |
| Port-to-connector mapping | *"Show the USB port-to-connector mapping for <PLATFORM>"* | `platform/SKILL.md` |
| TCSS port config | *"Show TCSS USB port configuration for <PLATFORM>"* | `platform/SKILL.md` |

### Section 4 — Power Management

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| D-state support | *"What D-states does xHCI support in <PLATFORM>_USB_HAS?"* | `power/SKILL.md` |
| RTD3 support | *"Is xHCI RTD3 supported in <PLATFORM>? What are the constraints?"* | `power/SKILL.md` |
| LTR values | *"What are the default LTR values for xHCI in <PLATFORM>?"* | `power/SKILL.md` |
| S0ix constraints | *"What are the xHCI S0ix entry requirements for <PLATFORM>?"* | `power/SKILL.md` |
| Wake sources | *"What USB wake sources are supported in <PLATFORM>?"* | `power/SKILL.md` |

### Section 5 — UAOL / ACE (PTL/NVL only)

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| ACE generation | *"What ACE generation is used for UAOL in <PLATFORM>?"* | `power/SKILL.md` UAOL section |
| Feedback FIFO size | *"What is the UAOL feedback FIFO size in <PLATFORM>?"* | `power/SKILL.md`, `debug/SKILL.md` |
| IOSF fabric channel | *"What IOSF traffic class/virtual channel is used for UAOL in <PLATFORM>?"* | `power/SKILL.md` |
| ACE D-state constraints | *"Can xHCI enter D3 during UAOL operation in <PLATFORM>?"* | `power/SKILL.md` |
| UAOL behind hub | *"Is UAOL behind USB hub supported in <PLATFORM>?"* | `docs/cheat_sheet.md` platform table |

### Section 6 — Errata & Known Issues

| Field | Co-Design Query | Target File |
|-------|-----------------|-------------|
| xHCI errata list | *"What are known xHCI errata for <PLATFORM>? List HSDES IDs if available"* | `docs/known_issues.md` |
| PHY errata | *"What are known USB PHY errata for <PLATFORM>?"* | `docs/known_issues.md` |
| PCR/ECR list | *"List PCRs and ECRs for xHCI in <PLATFORM>_USB_HAS"* | `docs/known_issues.md` |
| Integration constraints | *"What are USB integration constraints in <PLATFORM>_USB_HAS?"* | `docs/known_issues.md` §Integration Notes |

---

## Extraction Workflow

```
1. Open Co-Design: playwright_browser_navigate → https://chat.co-design.intel.com/chat
2. Select the correct project/document context for the target platform
3. For each row in the checklist above:
   a. Type the Co-Design query
   b. Wait for response
   c. Extract the relevant data
   d. Update the target file with the extracted data
   e. Mark with CORRECTION (vN) annotation if updating existing data
4. After all extractions:
   a. Run eval/assertions.py to verify no regressions
   b. Update this file's "Last Updated" date
   c. Update docs/known_issues.md "Last Updated" date
```

---

## Platform Extraction Status

| Platform | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 | Last Extracted |
|----------|-----------|-----------|-----------|-----------|-----------|-----------|----------------|
| NVL      | Partial   | Partial   | Partial   | Partial   | Partial   | Done      | 2026-03-18     |
| PTL      | Partial   | Partial   | Partial   | Partial   | Partial   | Done      | 2026-03-18     |
| LNL      | TBD       | TBD       | TBD       | TBD       | N/A       | TBD       | —              |
| MTL      | TBD       | TBD       | TBD       | TBD       | Partial   | Partial   | —              |
| ARL      | TBD       | TBD       | TBD       | TBD       | N/A       | TBD       | —              |
| WCL      | TBD       | TBD       | TBD       | TBD       | TBD       | TBD       | —              |
| RZL      | TBD       | TBD       | TBD       | TBD       | TBD       | TBD       | —              |
| TTL      | TBD       | TBD       | TBD       | TBD       | TBD       | TBD       | —              |

---

## Notes

- **Always query both PCH-H and PCH-S variants for NVL** — they may have different register offsets, port counts, or errata.
- **PLACEHOLDER pattern:** If a value cannot be confirmed from HAS, write `PLACEHOLDER — verify from <PLATFORM>_USB_HAS` in the target file. This makes unverified data searchable.
- **CORRECTION pattern:** When updating existing data with HAS-confirmed values, annotate as `CORRECTION (v2): <old_value> → <new_value> per <PLATFORM>_USB_HAS` in a comment.
