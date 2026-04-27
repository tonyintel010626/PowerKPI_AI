# FV-USB — Agent Workflows

<!-- owner: kvejaya -->

> Last Updated: 2026-03-20
> Standard workflows for common FV-USB agent interactions. Each workflow defines the exact sequence of skills, tools, and sub-agents to invoke.

---

## Workflow 1: New Platform Bring-Up

**Trigger:** First-time USB validation on a new platform (e.g., WCL, RZL, TTL)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Extract HAS data                                         │
│    Load: codesign skill (or Playwright → Co-Design)         │
│    Use: docs/usb_has_extraction.md template                 │
│    Output: Populate platform data in all sub-skills         │
├─────────────────────────────────────────────────────────────┤
│ 2. Verify config checkout                                   │
│    Load: fv-usb/config-checkout                             │
│    Run: check_usb_config("<PLATFORM>")                      │
│    Output: Pass/fail for each config check                  │
├─────────────────────────────────────────────────────────────┤
│ 3. Run enumeration validation                               │
│    Load: fv-usb/enumeration                                 │
│    Run: treeview.py, yellowbang_usb.py                      │
│    Output: USB device tree, no yellow-bang devices           │
├─────────────────────────────────────────────────────────────┤
│ 4. Run basic functional tests                               │
│    Run: test_run.py --test enumeration                      │
│    Run: test_run.py --test bulktraffic                      │
│    Run: test_run.py --test hotplug                          │
│    Output: Basic USB functionality confirmed                │
├─────────────────────────────────────────────────────────────┤
│ 5. Update coverage matrix                                   │
│    Edit: docs/test_coverage_matrix.md                       │
│    Add: New platform column with initial coverage           │
├─────────────────────────────────────────────────────────────┤
│ 6. Run test gap analysis                                    │
│    Review: docs/test_gap_analysis.md                        │
│    Add: Platform-specific gaps                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow 2: USB Failure Triage (Unknown Failure)

**Trigger:** Test failure with unknown root cause. User provides platform, symptom, test name.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Gather context                                           │
│    Ask user: Platform? Symptom? Test name? NGA exit code?   │
│    Ask user: Which die variant (NVL PCH-H vs PCH-S)?        │
├─────────────────────────────────────────────────────────────┤
│ 2. Check known issues                                       │
│    Read: docs/known_issues.md                               │
│    Does symptom match a known entry?                        │
│    ├─ YES → Apply documented workaround. Done.              │
│    └─ NO → Continue to Step 3.                              │
├─────────────────────────────────────────────────────────────┤
│ 3. Load debug sub-skill                                     │
│    Load: fv-usb/debug                                       │
│    Follow: Triage Flowchart for the symptom category        │
│    ├─ Device not found → Playbook 1 (NDE)                   │
│    ├─ Wrong speed → Playbook 2                              │
│    ├─ S0ix blocker → Playbook 3                             │
│    ├─ UAOL audio issue → Playbook 4                         │
│    └─ Compliance mode → Playbook 5                          │
├─────────────────────────────────────────────────────────────┤
│ 4. Collect debug bundle                                     │
│    Run: allchecker.py + treeview.py + yellowbang_usb.py     │
│    Run: NDE_checker.py (if enumeration issue)               │
│    Capture: ETL trace (load fv-usb/debug/etl-decode)        │
├─────────────────────────────────────────────────────────────┤
│ 5. Search HSDES                                             │
│    Load: sighting-info skill                                │
│    Search: keywords from symptom + platform                 │
│    ├─ Match found → Apply workaround, file duplicate        │
│    └─ No match → Continue to Step 6.                        │
├─────────────────────────────────────────────────────────────┤
│ 6. Cross-domain escalation (if needed)                      │
│    ├─ Power issue → Delegate to FV-PM-SOUTH                 │
│    ├─ BIOS/POST issue → Delegate to UART-MONITOR            │
│    ├─ Hardware issue → Delegate to TTK3 family              │
│    └─ General debug → Delegate to FV_Debugger_V1            │
├─────────────────────────────────────────────────────────────┤
│ 7. File HSDES sighting (if new issue)                       │
│    Include: debug bundle, ETL trace, PORTSC dumps           │
│    Update: docs/known_issues.md with new entry              │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow 3: UAOL Validation (PTL/NVL)

**Trigger:** UAOL audio validation or UAOL-related failure triage.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Verify prerequisites                                     │
│    Check: Platform is PTL or NVL (UAOL not on MTL/LNL/ARL) │
│    Check: ACE FW version matches BKC (load onebkc skill)    │
│    Check: UAOL registry key = Enabled                       │
│    Check: USB audio device connected and enumerated          │
├─────────────────────────────────────────────────────────────┤
│ 2. Run config-checkout                                      │
│    Load: fv-usb/config-checkout                             │
│    Verify: BIOS knob "UAOL Support" = Enabled               │
│    Verify: ACE device enumerated in PCI                      │
├─────────────────────────────────────────────────────────────┤
│ 3. Run UAOL tests                                           │
│    Run: test_run.py --test uaol_playback                    │
│    Run: test_run.py --test uaol_recording                   │
│    Run: audio.py (comprehensive audio test)                  │
├─────────────────────────────────────────────────────────────┤
│ 4. If failure:                                              │
│    Load: fv-usb/debug (UAOL Failure Triage section)         │
│    Follow: Playbook 4 (UAOL Recording Stuck)                │
│    Check: ACE3 (PTL) vs ACE4 (NVL) timing differences       │
│    Check: PSF glitch risk on NVL (DfSPSREQ register)         │
├─────────────────────────────────────────────────────────────┤
│ 5. Compare with UAOL-disabled baseline                      │
│    Disable UAOL → rerun same tests                          │
│    ├─ Tests pass without UAOL → UAOL-specific issue         │
│    └─ Tests fail without UAOL → Standard USB audio issue    │
├─────────────────────────────────────────────────────────────┤
│ 6. Capture UAOL ETL trace (if needed)                       │
│    Load: fv-usb/debug/etl-decode                            │
│    Start: UAOL + USBXHCI providers                          │
│    Reproduce: failure scenario                              │
│    Analyze: endpoint purge, missed intervals, FIFO state     │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow 4: S0ix / Modern Standby Validation

**Trigger:** Verify USB doesn't block S0ix entry, or debug S0ix blocking.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Baseline S0ix check                                      │
│    Load: fv-usb/power                                       │
│    Run: slp_s0.py                                           │
│    ├─ S0ix achieved → USB not blocking. Done.               │
│    └─ USB identified as blocker → Continue.                  │
├─────────────────────────────────────────────────────────────┤
│ 2. Identify specific blocker                                │
│    Run: LTR_checker.py                                      │
│    Run: pkgc_residency_checker.py                           │
│    Follow: Playbook 3 (USB Blocking S0ix)                   │
├─────────────────────────────────────────────────────────────┤
│ 3. Check all port states                                    │
│    For each port: read PORTSC.PLS                           │
│    All ports should be PLS=3 (U3/Suspended) before S0ix     │
│    Any port at PLS=0 (U0) = active blocker                  │
├─────────────────────────────────────────────────────────────┤
│ 4. Check xHCI D-state                                       │
│    Read PMCS register → xHCI should be in D3                │
│    ├─ D0 → Check RTD3 BIOS knob, selective suspend policy   │
│    └─ D3 → xHCI is good. Check other IPs.                   │
├─────────────────────────────────────────────────────────────┤
│ 5. Escalate if needed                                       │
│    Delegate: FV-PM-SOUTH for platform power gating           │
│    Delegate: FV_Debugger_V1 for cross-domain analysis        │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow 5: Galaxy XML Test Suite Execution

**Trigger:** Running USB test suite via Galaxy framework.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Pre-flight checks                                        │
│    Load: fv-usb/config-checkout                             │
│    Run: check_usb_config("<PLATFORM>")                      │
│    Verify: All checks pass                                  │
├─────────────────────────────────────────────────────────────┤
│ 2. Load Galaxy skill                                        │
│    Load: intel-galaxy skill                                 │
│    Validate XML: python run_galaxy.py --xml <suite> --dry-run│
├─────────────────────────────────────────────────────────────┤
│ 3. Execute test suite                                       │
│    Run: python run_galaxy.py --xml <suite> --init-all --nga │
│    Monitor: NGA dashboard for results                       │
├─────────────────────────────────────────────────────────────┤
│ 4. Analyze results                                          │
│    Load: nga/results skill                                  │
│    For each failure:                                        │
│    ├─ Exit code 0 → PASS                                    │
│    ├─ Exit code 1 → Load fv-usb/debug, triage               │
│    ├─ Exit code 12 → Load fv-usb/enumeration, check config  │
│    └─ Exit code 13 → Check test config, parameters           │
├─────────────────────────────────────────────────────────────┤
│ 5. Report                                                   │
│    Update: test_coverage_matrix.md with results             │
│    File: HSDES sightings for new failures                   │
│    Update: known_issues.md if new bugs found                │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow 6: BKC Update Validation

**Trigger:** After BIOS, driver, or ACE FW update per BKC release.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Verify BKC versions                                      │
│    Load: onebkc skill                                       │
│    Confirm: BIOS version, USB driver version, ACE FW version│
├─────────────────────────────────────────────────────────────┤
│ 2. Run config-checkout                                      │
│    Load: fv-usb/config-checkout                             │
│    Verify: All checks pass after update                     │
├─────────────────────────────────────────────────────────────┤
│ 3. Run regression test suite                                │
│    Run: Galaxy XML regression suite                         │
│    Focus: Previously-failing tests (from known_issues.md)    │
├─────────────────────────────────────────────────────────────┤
│ 4. Verify known issue fixes                                 │
│    Check: known_issues.md for issues marked "Resolved (BKC)"│
│    Retest: Those specific scenarios                         │
│    ├─ Fixed → Update status to "Verified Fixed"             │
│    └─ Still failing → Reopen sighting, escalate             │
├─────────────────────────────────────────────────────────────┤
│ 5. Update documentation                                     │
│    Update: known_issues.md status column                    │
│    Update: test_coverage_matrix.md with new results         │
│    Update: cheat_sheet.md if commands/paths changed         │
└─────────────────────────────────────────────────────────────┘
```

---

## Sub-Agent Delegation Quick Reference

| Condition | Delegate To | How |
|-----------|-------------|-----|
| PCH power gating / RTD3 / SLP_S0# | FV-PM-SOUTH | `task` tool with `subagent_type: "FV-PM-SOUTH"` |
| Confluence wiki BKMs / debug articles | FV_Debugger_V1 | `task` tool with `subagent_type: "FV_Debugger_V1"` |
| SPI flash / BIOS programming | TTK3 / TTK3-BIOS | `task` tool with `subagent_type: "TTK3"` |
| Power cycling / port control | TTK3-POWER | `task` tool with `subagent_type: "TTK3-POWER"` |
| I2C/UART/GPIO for CSwitch | TTK3-COMM | `task` tool with `subagent_type: "TTK3-COMM"` |
| BIOS boot log capture | UART-MONITOR | `task` tool with `subagent_type: "UART-MONITOR"` |
| HSDES sighting lookup | sighting-info skill | `skill` tool → `sighting-info` |
| BKC version check | onebkc skill | `skill` tool → `onebkc` |
| NGA test results | nga/results skill | `skill` tool → `nga/results` |
| Co-Design HAS query | codesign skill | `skill` tool → `codesign` |

---

## Appendix: Playwright Co-Design Query Examples

When querying Co-Design via Playwright MCP, follow this exact sequence:

### Step 1 — Open Chrome with Intel SSO
```bash
# MANDATORY: Open via Chrome guest profile for Intel SSO
start chrome --guest "https://chat.co-design.intel.com/chat"
```
Ask user to authenticate, then proceed.

### Step 2 — Navigate & Snapshot
```
playwright_browser_navigate → https://chat.co-design.intel.com/chat
playwright_browser_snapshot → find the chat textarea element reference
```

### Step 3 — Type Query
```
playwright_browser_type → ref: <textarea_ref>, text: "Show PORTSC register bit-fields from NVL_USB_HAS"
```

### Step 4 — Wait for Response
```
playwright_browser_wait_for → text: "PORTSC", timeout: 30000
playwright_browser_snapshot → read the full response
```

### Common Co-Design Queries (USB)

| Query | When to Use |
|-------|------------|
| `"Show PORTSC register from <PLATFORM>_USB_HAS"` | Register bit-field lookup |
| `"What is the xHCI DID for <PLATFORM>?"` | Device ID verification |
| `"What are known xHCI errata for <PLATFORM>?"` | Pre-test errata check |
| `"Show USB BIOS knobs for <PLATFORM>"` | Config checkout |
| `"Show eUSB2 PHY registers from NVL_HSIO_PHY_SoC_Integration_HAS"` | NVL eUSB2 debug |
| `"What is ACE3/ACE4 Feedback FIFO size?"` | UAOL architecture |
| `"What is the BAR0 address for xHCI on <PLATFORM>?"` | MMIO base lookup |
