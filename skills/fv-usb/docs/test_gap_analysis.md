# FV-USB — Test Gap Analysis

<!-- owner: kvejaya -->

> Last Updated: 2026-03-20
> This document tracks gaps between the USB test coverage matrix and the full validation scope defined in HAS documents and specification requirements.

---

## Purpose

Identify test scenarios that are **not covered** by current USB validation suites, and prioritize gap closure. Cross-reference with `test_coverage_matrix.md` for current coverage status.

---

## Gap Categories

### GAP-ENUM: Enumeration Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | eUSB2 PHY enumeration validation | NVL | High | Open | NVL uses eUSB2 PHY exclusively (no legacy USB2 fallback). PTL uses standard USB2 PHY (eUSB2 is optional PCB stuffing only). HAS §Integration Notes #4 — PCRs 14019161428, 14019160906 require validation |
| 2 | xDCI device-mode enumeration alongside xHCI | PTL, NVL | Medium | Open | Known constraint: HSDES 1509699522 |
| 3 | Multi-TT hub enumeration stress | All | Low | Open | Current tests use single-TT hubs only |
| 4 | USB4/TBT tunnel enumeration | NVL, PTL | Medium | Open | USB tunneled through Thunderbolt — not directly tested |

### GAP-XFER: Data Transfer Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | Concurrent bulk + isochronous stress (camera + storage) | PTL, NVL | High | Open | HSDES 15013449180 — known to trigger missed service events |
| 2 | Gen2 device behind Gen1 hub transfer stability | PTL, NVL | High | Open | HSDES 15013245412 — HC reset during bulk traffic |
| 3 | USB3 Gen2x2 (20 Gbps) bulk throughput validation | NVL | Medium | Open | Requires Gen2x2 capable device |
| 4 | Isochronous traffic during S0ix transitions | All | Medium | Open | Currently tested separately, not combined |

### GAP-PM: Power Management Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | USB2DBC S0ix interaction timing | PTL, NVL | Medium | Open | HAS §Integration Notes #3 — connection timing affects S0ix |
| 2 | XTAL refclk switching during UAOL + LP states | PTL, NVL | High | Open | HAS §Integration Notes #2 — PMC refclk switching required |
| 3 | RTD3 ↔ UAOL interaction (D3 during audio offload) | PTL, NVL | High | Open | Can xHCI enter D3 during UAOL? Need HAS confirmation |
| 4 | LPM U1/U2 transition stress under load | All | Medium | Open | Current LPM tests are idle-only |
| 5 | Package C-state residency with USB wake sources | All | Medium | Open | `pkgc_residency_checker.py` exists but not in automated suite |

### GAP-UAOL: USB Audio Offload Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | UAOL long-duration recording stability (>1 hour) | PTL | High | Open | HSDES 16029865294 — recording stuck after ~30s-3min |
| 2 | UAOL behind hub validation | PTL, NVL | Medium | Open | Fixed from MTL, but needs regression testing |
| 3 | UAOL multi-stream (playback + recording simultaneous) | PTL, NVL | Medium | Open | ACE3 FIFO may be insufficient for multi-stream |
| 4 | UAOL with S3/S4 resume cycle | PTL, NVL | Medium | Open | Does UAOL recover correctly after S3/S4? |
| 5 | VISA signal validation for UAOL glitch events | PTL, NVL | Low | Open | HSDES 22018119897 — VISA signals not fully implemented |
| 6 | PSF glitch validation on NVL | NVL | High | Open | HAS §Integration Notes #1 — DfSPSREQ must be set |

### GAP-DBC: Debug Capability Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | USB3DbC dual-bit enablement qualification | PTL, NVL | Medium | Open | HAS §Integration Notes #5 — both ECTRL bits required |
| 2 | DBC PID/strap configuration validation | PTL, NVL | Medium | Open | HAS §Integration Notes #6 — wrong strap = DBC not enumerated |

### GAP-PLATFORM: Platform-Specific Gaps

| # | Gap Description | Platforms Affected | Priority | Status | Notes |
|---|-----------------|-------------------|----------|--------|-------|
| 1 | NVL PCH-H vs PCH-S USB config comparison | NVL | High | Open | No automated test compares both die variants |
| 2 | WCL/RZL/TTL USB bring-up validation | WCL, RZL, TTL | Medium | Open | Upcoming platforms — no test content yet |
| 3 | DP Alt-Mode + USB concurrent validation | PTL, NVL | Medium | Open | HSDES 14020114105 — TC0b entry issue |
| 4 | Compliance test TD 7.06 workaround validation | PTL, NVL | Low | Open | HSDES 14018741394 — skip TD 7.06 in automation |

---

## Gap Closure Priority Matrix

| Priority | Criteria | Target Timeline |
|----------|----------|-----------------|
| **High** | Test-blocking, data integrity, or HAS-mandated validation with known RTL bug | Current milestone |
| **Medium** | Feature coverage gap, intermittent failure, or upcoming platform | Next milestone |
| **Low** | Edge case, cosmetic, or low-frequency scenario | Backlog |

---

## How to Close a Gap

1. Create or update test script in `C:\validation\windows-test-content\usb\latest_stable_dynamic\`
2. Add test case to Galaxy XML suite
3. Update `test_coverage_matrix.md` with new coverage
4. Run test on target platform(s) and verify pass
5. Update this file: change Status from `Open` to `Closed` with date
6. If gap revealed a new bug, add entry to `known_issues.md`

---

## Cross-References

| Document | Relationship |
|----------|-------------|
| `test_coverage_matrix.md` | Current coverage — gaps identified by comparing to this analysis |
| `known_issues.md` | Known bugs that create or prevent gap closure |
| `usb_has_extraction.md` | HAS extraction checklist — new platform data reveals new gaps |
| `debug_playbooks.md` | Debug procedures for failures found during gap closure testing |
