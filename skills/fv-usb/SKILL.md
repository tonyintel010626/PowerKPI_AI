---
name: fv-usb
version: 2.0.0
owner: kvejaya
description: Base skill for USB functional validation — xHCI, USB 2.0/3.x, UAOL, power management, and debug triage across Intel Client SoC platforms
---

# FV-USB — USB Functional Validation Base Skill

## Overview
This is the base skill for the FV-USB agent. It provides foundational knowledge for USB functional validation across all Intel client platforms, covering USB 2.0/3.x host controller validation, xHCI registers, power management, UAOL audio offload, and debug triage.

## Scope
- **USB 2.0** — High Speed (480 Mbps), Full Speed (12 Mbps), Low Speed (1.5 Mbps)
- **USB 3.x** — SuperSpeed (5 Gbps), SuperSpeed+ (10/20 Gbps)
- **xHCI** — eXtensible Host Controller Interface for unified USB 2.0/3.x control
- **UAOL** — USB Audio Offload via ACE (Audio Compute Engine) — isochronous audio streaming offloaded from xHCI to dedicated HW

## Target Platforms
All current and upcoming Intel client silicon platforms: MTL, ARL, LNL, PTL, NVL, WCL, RZL, TTL.

**Owner:** Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

> **NVL Multi-Die NOTE:** NVL has two die variants (PCH-H and PCH-S). USB configuration may differ — always confirm which die variant is under test.

---

## Reference Documents (docs/ folder)

| Document                                              | Contents                                             |
|-------------------------------------------------------|------------------------------------------------------|
| `fv-usb/docs/known_issues.md`                         | RTL bugs, HSDES sighting IDs, per-platform workarounds |
| `fv-usb/docs/cheat_sheet.md`                          | Quick command reference — scripts, PythonSV, Galaxy  |
| `fv-usb/docs/test_coverage_matrix.md`                 | Test category × platform validation coverage table   |
| `fv-usb/docs/usb_test_template.py`                    | Python test template with NGA exit codes, logging, and standard patterns |

---

## HAS Documents — Per Platform

| Platform | HAS Document Name                    | Notes                                         |
|----------|--------------------------------------|-----------------------------------------------|
| NVL      | `NVL_USB_HAS` / `NVL_XHCI_HAS`      | PCH-H and PCH-S variants — query for both     |
| PTL      | `PTL_USB_HAS` / `PTL_XHCI_HAS`      | Panther Lake — ACE3 UAOL engine               |
| LNL      | `LNL_USB_HAS`                        | Lunar Lake — integrated die design            |
| MTL      | `MTL_USB_HAS`                        | Meteor Lake — UAOL behind hub NOT supported   |
| ARL      | `ARL_USB_HAS`                        | Arrow Lake                                    |
| Others   | Query Co-Design                      | Use Co-Design for upcoming platforms          |

### Intel Website Access Protocol (MANDATORY)

> **CRITICAL:** To access ANY Intel intranet website (wiki, Co-Design, HSDES, etc.), you MUST follow this protocol. NEVER use `playwright_browser_navigate` directly to Intel URLs — it will open a non-authenticated browser that cannot pass SSO.

**Step 1 — Open Chrome with Guest Profile (via bash):**
```bash
start chrome --guest "<INTEL_URL>"
```

**Step 2 — Wait for user to authenticate:**
The user will manually enter their credentials on the Microsoft SSO page. **Do NOT proceed until the user confirms they are logged in.**

**Step 3 — User confirms login:**
Wait for user to say "ready", "done", "logged in", etc.

**Step 4 — Use Playwright browser tools to navigate and read:**
After user confirmation, use `playwright_browser_navigate` → `playwright_browser_snapshot` to interact with the authenticated page.

> **NEVER skip Steps 1-3.** The Chrome guest profile ensures credentials are not persisted on the host machine.

---

### Co-Design Query Procedure (7-Step)

1. **Open Chrome guest profile** → `start chrome --guest "https://chat.co-design.intel.com/chat"` (bash)
2. **Wait for user SSO login** → user confirms they are logged in
3. `playwright_browser_navigate` → `https://chat.co-design.intel.com/chat`
4. `playwright_browser_snapshot` → locate the chat textarea element reference
5. `playwright_browser_type` → type query into textarea (see example patterns below)
6. `playwright_browser_wait_for` → wait for response to finish loading
7. `playwright_browser_snapshot` → read response from chat feed

**Fallback:** Load `codesign` skill for REST API access when browser is unavailable.

### Example Query Patterns

| Question Type | Example Query |
|---------------|---------------|
| Register layout | *"Show the PORTSC register bit-fields from NVL_USB_HAS"* |
| Device IDs | *"What is the xHCI Device ID (DID) for the NVL USB controller?"* |
| xHCI errata | *"What are known xHCI errata for PTL? List HSDES IDs if available"* |
| UAOL power | *"What are the UAOL power constraints for NVL — can xHCI enter D3 during audio offload?"* |
| BIOS knobs | *"Show USB-related BIOS knobs for LNL"* |

---

## Authoritative Specifications
- USB 3.2 Specification — link training, LTSSM, LPM, speed negotiation
- xHCI Specification (Revision 1.2+) — command/transfer/event rings, TRBs, register maps

---

## Test Repository
```
C:\validation\windows-test-content\usb\
C:\validation\windows-test-content\usb\latest_stable_dynamic\
```

---

## Sub-Skills

| Sub-Skill                      | Description                                              | When to Load                                        |
|--------------------------------|----------------------------------------------------------|-----------------------------------------------------|
| `fv-usb/enumeration`           | PCI enumeration, DID/VID, BDF/BAR, device tree           | Device not found, wrong speed, BDF/BAR questions    |
| `fv-usb/xhci`                  | xHCI register maps, capability structures, protocols      | Register questions, PORTSC, TRB, ring architecture  |
| `fv-usb/power`                 | D-states, LPM U1/U2/U3, LTR, S0ix, wake-on-USB          | PM failures, S0ix blockers, D3/RTD3, LPM debug      |
| `fv-usb/debug`                 | Failure triage, HSDES sightings, UAOL debug, workflows    | Any failure — start here for unknown USB failures   |
| `fv-usb/config-checkout`       | PCI enumeration verify, BAR, BIOS knobs, ACPI tables     | New platform bring-up, config validation             |
| `fv-usb/platform`              | Per-platform DID/BDF/port counts, die variants, BIOS knobs | Platform-specific data lookup, multi-die questions   |
| `fv-usb/debug/etl-decode`      | ETL trace capture, decode, and analysis                   | Deep debug requiring USB/UAOL trace analysis         |
| `fv-usb/dbc`                   | USB Debug Capability (USB3DbC/USB2DBC) setup and validation | DBC cable testing, debug port setup, DBC enumeration |

### Sub-Skill Selection Decision Tree

Start here if unsure which sub-skill to load:

```
┌─ Device not showing up?
│  └─→ Load fv-usb/enumeration → check PORTSC.CCS → then fv-usb/debug
│
├─ Wrong speed or link stuck?
│  └─→ Load fv-usb/xhci → check PORTSC.PLS/Speed → then fv-usb/enumeration
│
├─ Power management failure (S0ix blocker, D3, LPM)?
│  └─→ Load fv-usb/power → check D-state/LPM → then fv-usb/debug
│
├─ UAOL audio issue (glitch, stuck, no sound)?
│  └─→ Load fv-usb/debug (UAOL section) → then fv-usb/power
│
├─ Need ETL/WPP trace analysis?
│  └─→ Load fv-usb/debug/etl-decode → capture and decode traces
│
├─ DBC cable testing or debug port setup?
│  └─→ Load fv-usb/dbc → setup DBC, verify enumeration
│
├─ New platform setup or validation?
│  └─→ Load fv-usb/config-checkout → verify all checks → then fv-usb/platform
│
├─ Platform-specific data (DID, BDF, port counts)?
│  └─→ Load fv-usb/platform → look up die variant data
│
└─ Unknown failure?
   └─→ Load fv-usb/debug → follow triage flowchart → delegate as needed
```

**Loading order for common scenarios:**
- Device not enumerated → `fv-usb/enumeration` then `fv-usb/debug`
- Power / S0ix failure → `fv-usb/power` then `fv-usb/debug`
- UAOL audio failure → `fv-usb/debug` (UAOL section) then `fv-usb/power`
- Register question → `fv-usb/xhci` then Co-Design HAS
- DBC test execution → `fv-usb/dbc` then `fv-usb/debug` if issues arise
- New platform bring-up → `fv-usb/config-checkout` then `fv-usb/platform`

---

## UAOL Content Navigation

UAOL content is distributed across the skill tree by function. Use this index to find what you need:

| What you need | Load this skill | Section |
|---------------|----------------|---------|
| Power constraints, LPM interaction, validation checklist | `fv-usb/power` | *UAOL Isochronous Power Management*, *UAOL Power State Validation Checklist* |
| Failure triage, decision tree, debug checklist | `fv-usb/debug` | *UAOL Failure Triage*, *UAOL Debug Data Collection Checklist* |
| Per-platform ACE generation, FIFO timing, behind-hub support | `fv-usb/platform` | Per-platform tables (UAOL Engine rows) |
| ETL trace decode for audio glitch analysis | `fv-usb/debug/etl-decode` | *Pattern 2: UAOL Audio Glitch Analysis* |
| Step-by-step recording-stuck playbook | `fv-usb/docs/debug_playbooks.md` | *Playbook 4: UAOL Audio Recording Stuck* |
| Quick validation commands | `fv-usb/docs/cheat_sheet.md` | *UAOL Quick Checks* |

---

## Known Issues Pointer
Before triaging any failure, check `fv-usb/docs/known_issues.md` for matching RTL bugs. Key known issues:
- **HSDES 16029865294** — PTL UAOL recording stuck (Astro40 headset, ACE3 FIFO)
- **HSDES 18043001729** — NVL ACE4 FIFO sizing adjustment
- **MTL UAOL hub bug** — UAOL behind USB hub not supported on MTL (fixed PTL+)

---

## Quick Reference — USB Helper Usage

### Check device speed
```python
from usb_helper_ipsv import USBHelper
helper = USBHelper()
speed = helper.get_speed(port)  # Returns 0-7 (see speed mapping in agent)
```

### Check link status
```python
link_status = helper.get_link_status(port)  # Returns 0-15 (PLS value)
```

### Check power state
```python
power_state = helper.get_power_state(device)  # Returns "D0" or "D3"
```

### Run Galaxy test suite
```bash
python run_galaxy.py --xml <suite.xml> --init-all --nga
```

### Run specific test
```bash
python test_run.py --test enumeration
python test_run.py --test bulktraffic
python test_run.py --test hotplug
python test_run.py --test uaol_playback
python test_run.py --test uaol_recording
python test_run.py --test s3_connect
python test_run.py --test s4_disconnect
```

### Collect debug bundle
```bash
python allchecker.py > usb_debug_bundle.txt 2>&1
python treeview.py >> usb_debug_bundle.txt 2>&1
python yellowbang_usb.py >> usb_debug_bundle.txt 2>&1
python NDE_checker.py >> usb_debug_bundle.txt 2>&1
```

---

## NGA Exit Codes

| Code | Meaning              | Action                                               |
|------|----------------------|------------------------------------------------------|
| 0    | PASS                 | No action needed                                     |
| 1    | FAIL                 | Triage via `fv-usb/debug`                            |
| 12   | Device not found     | Load `fv-usb/enumeration`, check PORTSC.CCS          |
| 13   | Configuration error  | Check script config, platform BDF, test parameters   |

---

## ETL Retrieval — MANDATORY Protocol

> **CRITICAL LEARNING:** Always use **NGA communicator** to retrieve ETL files from SUTs. **NEVER** attempt direct network path access (UNC paths like `\\172.22.8.153\c$\Desktop`). Direct network access is unreliable and may be blocked by security policies.

### Proper ETL Retrieval Workflow

When a user provides an ETL file location with a machine IP/hostname:

1. **Use NGA communicator** to connect to the SUT
   - If **hostname** given (e.g., `PG16WVAW2048`) → NGA resolves to SUT IP via StationAutomation
   - If **IP address** given (e.g., `172.22.8.153`) → direct evtar communicator connection
2. **Fetch ETL file** via communicator: `comm.GetFileFromTarget(sut_path, local_path)`
3. **Obtain PDB symbols** via symchk on SUT
4. **Decode and analyze** using `fv-usb/debug/etl-decode` sub-skill

### Implementation Example

```python
import sys, os
sys.path.insert(0, r'C:\SVShare\NGA\ClientScripts')
from evtar.services.communicator.ux import GetCommunicator
from NgaGateway import NgaGateway

# Option A: Hostname → NGA resolution
def get_sut_from_hostname(hostname):
    gw = NgaGateway('StationAutomation', None, hostname)
    project = gw.get_project_name_by_system_name(hostname)
    gw2 = NgaGateway('StationAutomation', project, hostname)
    system = gw2.get_system_by_name(hostname)
    station = gw2.get_station_by_id(system['StationId'])
    sut = next(s for s in station['Systems'] if s['Role'] == 'Target')
    return GetCommunicator(sut['Ip'], nPortNum=8001)

# Option B: Direct IP
def get_sut_from_ip(ip):
    return GetCommunicator(ip, nPortNum=8001)

# Fetch ETL
comm = get_sut_from_ip('172.22.8.153')  # or get_sut_from_hostname('hostname')
comm.GetFileFromTarget(r'C:\Users\<user>\Desktop\<etl_file>.etl', r'C:\ETLDecode\<etl_file>.etl')
```

> **See full workflow in:** `fv-usb/debug/etl-decode` sub-skill, Section *"Step 4 — Fetch ETL File and Obtain PDB Symbols"*

---

## Test Naming Convention

Pattern: `USB_<CATEGORY>_<PLATFORM>_<ID>`

| Field    | Examples                                               |
|----------|--------------------------------------------------------|
| CATEGORY | `ENUM`, `BULK`, `ISOCH`, `HOTPLUG`, `PM`, `UAOL`, `S3`, `S4`, `LPM` |
| PLATFORM | `NVL`, `PTL`, `LNL`, `MTL`, `ARL`                     |
| ID       | Numeric test case ID from NGA or Galaxy XML            |

Examples: `USB_UAOL_PTL_001`, `USB_ENUM_NVL_042`, `USB_PM_S3_LNL_007`

---

## Cross-Domain Delegation

| Issue                          | Delegate To           |
|--------------------------------|-----------------------|
| Power management (PCH/RTD3)    | `FV-PM-SOUTH` agent   |
| General debug / wiki BKMs      | `FV_Debugger_V1` agent|
| Hardware interaction           | `TTK3` agent family   |
| BIOS boot USB enumeration      | `UART-MONITOR` agent  |
| HSDES sighting lookup          | `sighting-info` skill |
| BKC / ACE FW version check     | `onebkc` skill        |
