# FV-USB Skill Evaluation Tests

> Structured evaluation tests for the FV-USB skill tree.
> Companion to `eval/assertions.py` (machine-executable) and `eval/opencode.json` (machine-readable config).

---

## Category 1: Skill Structure

### TEST-STRUCT-001: Root SKILL.md frontmatter
**Query:** "Load the fv-usb skill"
**Expected:** SKILL.md loads with `name: fv-usb`, `version: 2.0.0`, `owner: kvejaya`

### TEST-STRUCT-002: Sub-skill enumeration
**Query:** "What sub-skills does FV-USB have?"
**Expected:** Lists at minimum: enumeration, xhci, power, debug, debug/etl-decode, config-checkout, platform

### TEST-STRUCT-003: Reference documents listed
**Query:** "What reference documents are available for FV-USB?"
**Expected:** Lists known_issues.md, cheat_sheet.md, test_coverage_matrix.md, debug_playbooks.md, usb_has_extraction.md, test_gap_analysis.md, agent_workflows.md, usb_test_template.py

### TEST-STRUCT-004: Co-Design access method documented
**Query:** "How do I look up USB register details from the HAS?"
**Expected:** Mentions both Playwright browser method and REST API (codesign skill) method

---

## Category 2: Technical Accuracy

### TEST-TECH-001: USB speed encoding
**Query:** "What is USB speed value 1 in xHCI?"
**Expected:** Full Speed (12 Mbps) — NOT Low Speed

### TEST-TECH-002: USB speed encoding value 2
**Query:** "What is USB speed value 2?"
**Expected:** Low Speed (1.5 Mbps) — NOT Full Speed

### TEST-TECH-003: PLS value for U0
**Query:** "What PLS value means the link is active?"
**Expected:** PLS=0 means U0 (Active)

### TEST-TECH-004: PLS value for Compliance Mode
**Query:** "What PLS value indicates compliance mode?"
**Expected:** PLS=10 indicates Compliance Mode

### TEST-TECH-005: PORTSC register offset formula
**Query:** "How do I calculate the PORTSC register address for port N?"
**Expected:** PORTSC(N) = BAR + Operational_Base + 0x400 + 16*(N-1)

### TEST-TECH-006: xHCI capability register chain
**Query:** "How are xHCI extended capabilities organized?"
**Expected:** Linked list starting at HCCPARAMS1.xECP, each entry has Next Capability Pointer

### TEST-TECH-007: TRB types
**Query:** "What are the main TRB types in xHCI?"
**Expected:** Mentions Normal, Setup Stage, Data Stage, Status Stage, Link, Event Data, Transfer Event, Command Completion Event

---

## Category 3: Platform Coverage

### TEST-PLAT-001: NVL multi-die awareness
**Query:** "Tell me about NVL USB configuration"
**Expected:** Mentions PCH-H and PCH-S die variants, warns about potential differences

### TEST-PLAT-002: PTL UAOL engine
**Query:** "What UAOL engine does PTL use?"
**Expected:** ACE3 with ~1ms feedback FIFO per stream

### TEST-PLAT-003: NVL UAOL engine
**Query:** "What UAOL engine does NVL use?"
**Expected:** ACE4 with 4.5MB L2 cache, up to 10ms feedback FIFO

### TEST-PLAT-004: MTL UAOL behind hub
**Query:** "Does UAOL work behind a hub on MTL?"
**Expected:** No — RTL bug on MTL, fixed in PTL+

### TEST-PLAT-005: Platform BIOS knobs
**Query:** "What USB BIOS knobs should I check?"
**Expected:** Lists xHCI Mode, USB Controller Enable, UAOL Enable, RTD3 Enable, Wake Enable

---

## Category 4: Debug Workflows

### TEST-DEBUG-001: NDE triage flow
**Query:** "USB device not enumerating — how do I debug?"
**Expected:** Mentions checking PORTSC.CCS, running NDE_checker.py, checking yellowbang_usb.py, verifying BIOS knobs

### TEST-DEBUG-002: S0ix blocker triage
**Query:** "USB is blocking S0ix — what do I check?"
**Expected:** Mentions xHCI D-state, LTR values, RTD3 policy, slp_s0.py, LTR_checker.py

### TEST-DEBUG-003: Wrong speed triage
**Query:** "USB device connecting at High Speed instead of SuperSpeed"
**Expected:** Mentions checking PLS, cable quality, PORTSC speed field, USB3 port disable knob

### TEST-DEBUG-004: UAOL recording stuck
**Query:** "UAOL audio recording stops after a few minutes"
**Expected:** Mentions HSDES 16029865294, ACE3 feedback FIFO limitation, Astro40 headset, disable UAOL workaround

### TEST-DEBUG-005: Compliance mode trap
**Query:** "Port stuck in compliance mode"
**Expected:** Mentions PLS=10, signal integrity, cable replacement, board trace check

### TEST-DEBUG-006: ETL trace decode
**Query:** "How do I decode a USB ETL trace?"
**Expected:** Mentions etl-decode sub-skill, capture procedure, symbol setup, xperf/WPA, UAOL trace markers

---

## Category 5: UAOL Coverage

### TEST-UAOL-001: UAOL architecture
**Query:** "How does USB Audio Offload work?"
**Expected:** Mentions ACE engine, isochronous transfer offload from xHCI, IOSF fabric TCusb/VCusb, pNDE scheduler

### TEST-UAOL-002: ACE3 vs ACE4
**Query:** "What's the difference between ACE3 and ACE4?"
**Expected:** ACE3 (PTL) ~1ms FIFO, no L2; ACE4 (NVL) up to 10ms FIFO, 4.5MB L2

### TEST-UAOL-003: UAOL xHCI trace visibility
**Query:** "Can I see UAOL audio data in xHCI traces?"
**Expected:** No — when UAOL is active, isochronous traffic is offloaded to ACE, NOT visible in xHCI traces

### TEST-UAOL-004: Missed service interval recovery
**Query:** "What happens if UAOL misses an isochronous service interval?"
**Expected:** No hardware recovery mechanism — relies on SW stack; ACE4 has larger FIFO buffer (up to 10ms) for better tolerance

---

## Category 6: Cross-References

### TEST-XREF-001: Sub-agent delegation
**Query:** "Who handles PCH power gating issues?"
**Expected:** Delegates to FV-PM-SOUTH agent

### TEST-XREF-002: HSDES lookup
**Query:** "Search for known USB enumeration sightings"
**Expected:** Mentions using sighting-info skill or hsdes skill with USB/xHCI/enumeration keywords

### TEST-XREF-003: NGA exit code interpretation
**Query:** "NGA test returned exit code 12"
**Expected:** Exit code 12 = Device not found — check enumeration, load fv-usb/enumeration skill

---

## Category 7: Known Issues

### TEST-KI-001: Classification prefixes
**Query:** "What are the known USB issues?"
**Expected:** Each issue has a classification prefix (HSDES, RTL, INTEG, CONFIG, FW, DRIVER)

### TEST-KI-002: Workaround provided
**Query:** "What's the workaround for HSDES 16029865294?"
**Expected:** Disable UAOL via registry; update device firmware

### TEST-KI-003: Status tracking
**Query:** "Is HSDES 18043001729 resolved?"
**Expected:** Yes — resolved, BIOS/FW update per BKC

---

## Audit Trail

| Version | Date       | Author    | Changes                                    |
|---------|------------|-----------|--------------------------------------------|
| 2.0.0   | 2026-03-20 | AI-assist | Initial creation — 30 eval tests across 7 categories |
