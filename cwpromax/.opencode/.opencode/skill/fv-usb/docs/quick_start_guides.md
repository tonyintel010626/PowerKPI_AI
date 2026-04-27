# FV-USB Quick-Start Guides

> Fast-track workflows for common USB validation scenarios.
> Each guide is 5-7 steps max. For deep-dive details, load the referenced sub-skill.

---

## Guide 1: New Platform Bring-Up (USB Config Checkout)

**When to use:** First boot on a new platform or new IFWI drop.

**Sub-skill:** `fv-usb/config-checkout`

| Step | Action | Expected |
|------|--------|----------|
| 1 | Load `fv-usb/platform` skill, verify DID/BDF for your platform | DID matches platform table |
| 2 | Run `python check_usb_config.py` from test repo | All 7 checks PASS |
| 3 | Open Device Manager → USB controllers | xHCI shows with correct DID (no yellow bang) |
| 4 | Run `python treeview.py` | Device tree matches expected port topology |
| 5 | Verify BIOS knobs: USB Support=Enabled, XHCI Mode=Enabled | Knobs match expected config |
| 6 | If UAOL platform: verify UAOL Support=Enabled in BIOS | UAOL knob present and enabled |
| 7 | Run `python yellowbang_usb.py` | Zero yellow-bang devices |

**If any step fails:** Load `fv-usb/debug` skill → follow debug flowchart.

---

## Guide 2: First-Time UAOL Validation

**When to use:** Starting UAOL (USB Audio Offload) testing on a new setup.

**Sub-skill:** `fv-usb/power` (UAOL section)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Confirm platform supports UAOL: NVL (ACE4), PTL (ACE3). MTL/LNL/ARL = no UAOL | Platform in supported list |
| 2 | Connect USB audio device directly to root port (NOT behind hub on MTL) | Device enumerates in Device Manager |
| 3 | Run `python NDE_checker.py` | UAOL offload path detected |
| 4 | Start audio playback (e.g., `USB_UAOL_PLT_001` test) | Audio plays without glitches |
| 5 | Verify xHCI stays in D0, USB link stays U0/U1 during playback | `python lpm.py` shows U0 or U1 only |
| 6 | Stop playback, verify device returns to normal power state | xHCI can enter D3, link can enter U2/U3 |

**Platform-specific notes:**
- **NVL (ACE4):** 10ms FIFO, 4.5MB L2 cache → more tolerant of scheduling jitter
- **PTL (ACE3):** ~1ms FIFO → sensitive to timing, check HSDES 16029865294 for known recording stuck issue
- **MTL:** UAOL behind hub NOT supported (silicon bug, fixed PTL+)

**If audio glitches or recording stuck:** Load `fv-usb/debug` skill → UAOL triage decision tree.

---

## Guide 3: S0ix Blocker Triage (5-Minute Version)

**When to use:** S0ix residency is zero or low, USB suspected as blocker.

**Sub-skill:** `fv-usb/power`

| Step | Action | Expected |
|------|--------|----------|
| 1 | Run `python slp_s0.py` | Check SLP_S0 residency (should be >0%) |
| 2 | Run `python LTR_checker.py` | All USB devices report valid LTR values |
| 3 | Run `python pkgc_residency_checker.py` | Package C-state residency >0% |
| 4 | Check xHCI power state: `python lpm.py` | xHCI in D3, all ports in U3 or disconnected |
| 5 | If UAOL active: verify UAOL is NOT blocking D3/U3 transition | Disable UAOL, re-check residency |

**Common blockers:**
- USB device not entering U3 → check LPM support in device descriptor
- xHCI stuck in D0 → check if UAOL stream is active (expected behavior)
- LTR value too high → check device firmware, try different USB port
- Wake event storm → check PORTSC.WCE/WDE/WOE bits

**If still blocked:** Load `fv-usb/debug` skill → S0ix debug section, collect debug bundle.

---

## Guide 4: Hot-Plug Failure Quick-Debug

**When to use:** USB device not detected after plug-in, or disappears after plug-out/plug-in.

**Sub-skill:** `fv-usb/enumeration`, then `fv-usb/debug`

| Step | Action | Expected |
|------|--------|----------|
| 1 | Check PORTSC.CCS (Current Connect Status) via `python usb_helper_ipsv.py` | CCS=1 if device physically connected |
| 2 | Check PORTSC.PLS (Port Link State) | PLS=0 (U0) for active link |
| 3 | If PLS=5 (RxDetect): device not detected → check cable/port/device | Try different cable or port |
| 4 | If PLS=10 (Compliance): compliance mode entry → known issue | Check HSDES 14018741394 (TD 7.06) |
| 5 | Run `python treeview.py` | Device appears in tree with correct speed |
| 6 | If device shows wrong speed: check PORTSC.Speed field | 4=SS 5G, 5=SS+ 10G, 6=SS+ 20G |

**If device intermittently drops:** Load `fv-usb/debug/etl-decode` skill → capture ETL trace during replug.

---

## Guide 5: DBC (Debug Capability) Test Setup

**When to use:** Setting up USB Debug Capability cable for test execution.

**Sub-skill:** `fv-usb/dbc`

| Step | Action | Expected |
|------|--------|----------|
| 1 | Identify DBC-capable port on SUT (check platform BIOS knobs) | DBC port identified |
| 2 | Enable USB3DbC or USB2DBC in BIOS (both ECTRL bits on PTL/NVL) | DBC knobs enabled |
| 3 | Connect DBC cable between SUT and Host | DBC debug device enumerates on Host |
| 4 | Verify DBC connection: Host sees debug device in Device Manager | Debug device present, no errors |
| 5 | Run test suite via DBC connection | Tests execute and return results |

**Platform-specific notes:**
- **PTL/NVL:** USB3DbC requires dual-bit enablement in ECTRL register (see test_gap_analysis.md GAP-DBC)
- **PTL/NVL:** DBC PID/strap configuration must be validated
- **S0ix interaction:** USB2DBC has timing sensitivity during S0ix entry (see test_gap_analysis.md GAP-PM)

**If DBC not enumerating:** Check BIOS DBC knobs, try different port, verify cable is DBC-capable (not standard USB cable).

---

## Guide 6: NGA USB Test Execution

**When to use:** Running USB tests through NGA automation framework.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Verify test content is deployed: `C:\validation\windows-test-content\usb\` | Test scripts present |
| 2 | Check test naming: `USB_<CATEGORY>_<PLATFORM>_<ID>` | Names follow convention |
| 3 | Submit test run via NGA | Test queued and starts |
| 4 | Monitor NGA exit codes: 0=PASS, 1=FAIL, 12=Device Not Found, 13=Config Error | Correct exit code returned |
| 5 | If exit code 12: device not found → run Guide 4 (hot-plug debug) | Device enumeration fixed |
| 6 | If exit code 13: config error → run Guide 1 (config checkout) | Configuration corrected |

**For NGA failures:** Load `fv-usb/debug` skill → NGA exit code interpretation section.

---

## Sub-Skill Quick Reference

| I need to... | Load this sub-skill |
|--------------|-------------------|
| Check PCI config, BIOS knobs, ACPI | `fv-usb/config-checkout` |
| Debug device not enumerating | `fv-usb/enumeration` |
| Read xHCI registers, PORTSC, PLS | `fv-usb/xhci` |
| Debug power/LPM/S0ix/UAOL issues | `fv-usb/power` |
| Triage failures, collect debug bundle | `fv-usb/debug` |
| Decode ETL/WPP traces | `fv-usb/debug/etl-decode` |
| Look up platform DID/BDF/ports | `fv-usb/platform` |
| Set up DBC test cable | `fv-usb/dbc` |

---

## Audit Trail

- **v1.0.0** | 2026-03-27 | Created as part of Phase 2 FV-USB improvement | 6 quick-start guides
