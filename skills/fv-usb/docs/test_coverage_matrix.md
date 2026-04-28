# FV-USB — Test Coverage Matrix

<!-- owner: kvejaya -->

> Last Updated: 2026-03-18
> This matrix tracks which USB test categories have been validated on each platform.
> Update this file whenever new test results are confirmed or test gaps are filled.

---

## Coverage Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Validated — tests passing in NGA |
| ○ | Partial — some tests pass, gaps remain |
| ✗ | Known failing — open issue, see known_issues.md |
| — | Not tested / not applicable |
| ? | Unknown — needs investigation |
| N/A | Not applicable for this platform |

---

## Test Category × Platform Coverage

> **NVL note:** NVL has two die variants — **PCH-H** and **PCH-S**. USB controller configuration (port counts, TCSS, BAR assignments) differs between them. Always confirm die variant before interpreting results. Both columns must be populated independently.

| Test Category | Priority | NVL-PCH-H | NVL-PCH-S | PTL | LNL | MTL | ARL | WCL/RZL/TTL |
|---------------|----------|-----------|-----------|-----|-----|-----|-----|-------------|
| **Enumeration — SS (5 Gbps)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Enumeration — SS+ (10 Gbps)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ○ | ? |
| **Enumeration — HS (480 Mbps)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Enumeration — FS/LS** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Speed Detection** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Bulk Data Transfer** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Isochronous Transfer** | P1 | ✓ | ? | ✓ | ○ | ✓ | ○ | ? |
| **Interrupt Transfer** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Hot-Plug (Connect)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Hot-Plug (Disconnect)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **LPM — U1** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **LPM — U2** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ○ | ? |
| **LPM — U3 (Suspend)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **USB 2.0 LPM (L1)** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **S3 Connect** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **S3 Disconnect** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **S4 Connect** | P2 | ✓ | ? | ✓ | ○ | ✓ | ○ | ? |
| **S4 Disconnect** | P2 | ✓ | ? | ✓ | ○ | ✓ | ○ | ? |
| **S0ix / Modern Standby** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **RTD3 (Runtime D3)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Wake-on-USB (Connect)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Wake-on-USB (Disconnect)** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **UAOL Playback** | P1 | ✓ | ? | ✓ | — | ○ | — | ? |
| **UAOL Recording** | P1 | ○ | ? | ✗ | — | — | — | ? |
| **UAOL Behind Hub** | P2 | ✓ | ? | ✓ | — | N/A | — | ? |
| **Compliance Mode Recovery** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Type-C Orientation** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Type-C Speed (TCSS)** | P1 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **USB Audio Device Class** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ○ | ? |
| **USB Storage / IOmeter** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **USB Webcam** | P2 | ✓ | ? | ✓ | ✓ | ✓ | ✓ | ? |
| **Stress (Long Duration)** | P3 | ○ | ? | ○ | ○ | ✓ | ○ | ? |

---

## Known Gaps & Open Issues

| Platform | Category | Gap Description | HSDES / Reference |
|----------|----------|-----------------|-------------------|
| PTL | UAOL Recording | Recording stuck after ~30s-3min (ACE3 Feedback FIFO). Known RTL issue. | 16029865294 |
| MTL | UAOL Behind Hub | Not supported — RTL bug. Fixed PTL+. | N/A (by design) |
| NVL | UAOL Recording | ACE4 FIFO sizing adjustment needed. Fixed in BKC. | 18043001729 |
| ARL | LPM U2 | Partial coverage — needs additional test runs | — |
| LNL | S4 Connect/Disconnect | Incomplete coverage — needs validation runs | — |
| NVL-PCH-S | All | PCH-S bring-up in progress — no NGA results yet. Shared RTL errata apply (see known_issues.md). | — |
| WCL/RZL/TTL | All | Pre-silicon / early silicon — matrix not yet populated | — |

---

## Platform Notes

### NVL (Nova Lake)
- Two die variants: **PCH-H** (PCD-H) and **PCH-S** — USB controller configuration (port counts, TCSS presence, BAR assignments) differs between them
- **PCH-H**: Full TCSS + xHCI + UAOL ACE4 validated; matrix populated from NGA results
- **PCH-S**: Matrix unpopulated (`?`) — no NGA test results available yet; PCH-S bring-up is in progress. Errata HSDES 15013449180, 15013245412, 14020114105, 14018741394, 1509699522, 1509308928, 1509209950 apply to both PCH-H and PCH-S (shared RTL)
- ACE4 UAOL engine — larger FIFO (4.5MB L2, up to 10ms) vs PTL ACE3
- UAOL Recording partial: ACE4 FIFO fix in BKC resolves most scenarios
- NVL uses Lake Tahoe PHY for USB4/TCSS; USB4 Host Router + xHCI on TCSS

### PTL (Panther Lake)
- ACE3 UAOL engine — tight ~1ms Feedback FIFO
- UAOL Recording: known HSDES 16029865294 (Astro40 headset stuck). Workaround: disable UAOL or update headset FW
- UAOL Behind Hub: **supported** (fixed from MTL)

### LNL (Lunar Lake)
- Integrated SoC die — USB controller on SoC, not discrete PCH
- BAR and BDF assignments differ from PCH-based platforms
- UAOL: not applicable (no ACE on LNL)
- S4 coverage needs additional validation runs

### MTL (Meteor Lake)
- UAOL Behind Hub: **not supported** (known RTL bug) — mark N/A
- All other categories well-covered

### ARL (Arrow Lake)
- Generally aligns with MTL/LNL patterns
- Some categories at partial coverage — ongoing validation

### WCL / RZL / TTL
- Pre-silicon or early silicon
- Matrix will be populated as bring-up progresses
- Use Co-Design to confirm USB architecture differences vs prior platforms

---

## How to Update This Matrix

1. After running a test suite, update the symbol for the relevant (Category, Platform) cell
2. If a test reveals a new known issue, add it to `known_issues.md` and reference it in the gap table above
3. Update `Last Updated` date at the top of this file
4. Commit with message: `docs(fv-usb): update test coverage matrix for <platform> <date>`
