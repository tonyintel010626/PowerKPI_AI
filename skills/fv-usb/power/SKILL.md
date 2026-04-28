---
name: power
version: 2.0.0
owner: kvejaya
description: USB power management validation — D-states, LPM (U1/U2/U3), LTR, S0ix, RTD3, wake-on-USB, and UAOL (USB Audio Offload) with ACE3/ACE4 FIFO timing
---

> **Owner**: Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

# FV-USB / Power — USB Power Management Validation

## Purpose
This sub-skill covers USB power management including D-states (D0/D3), Link Power Management (LPM U1/U2/U3), Latency Tolerance Reporting (LTR), S0ix/Modern Standby, wake-on-USB, and Runtime D3 (RTD3).

## When to Use
- User asks about USB D-state transitions (D0 ↔ D3)
- User needs to validate LPM (U1/U2/U3) link states
- User asks about LTR values or configuration
- User is debugging S0ix/Modern Standby USB-related failures
- User asks about wake-on-USB (connect/disconnect wake)
- User needs to check Package C-state residency with USB
- User asks about RTD3 (Runtime D3) for xHCI

## Key Concepts

### USB Power State Hierarchy

```
System Level:     S0 (Active) ←→ S0ix (Modern Standby) ←→ S3/S4/S5
                    │
Device Level:     D0 (Active) ←→ D3hot ←→ D3cold (RTD3)
                    │
Link Level:       U0 (Active) ←→ U1 (Standby) ←→ U2 (Sleep) ←→ U3 (Suspend)
                                   │                │
                              ~1µs exit         ~2ms exit
```

### D-State Definitions

| State    | Description                    | Power    | Register Access |
|----------|--------------------------------|----------|-----------------|
| **D0**   | Fully operational              | Full     | Available       |
| **D3hot**| Low power, context preserved   | Low      | Limited         |
| **D3cold (RTD3)** | Power removed, context lost | None | None          |

### LPM (Link Power Management) States — USB 3.x

| State | Name     | Exit Latency | Description                        |
|-------|----------|--------------|------------------------------------|
| **U0**| Active   | —            | Link fully active, data transfer   |
| **U1**| Standby  | ~1 µs        | Fast exit, clock still running     |
| **U2**| Sleep    | ~2 ms        | Deeper sleep, clock can be gated   |
| **U3**| Suspend  | ~10 ms+      | Device suspended, link inactive    |

### LPM States — USB 2.0

| State | Name    | Description                                  |
|-------|---------|----------------------------------------------|
| **L0**| Active  | Fully active                                 |
| **L1**| Sleep   | Hardware-initiated LPM (BESL-based)          |
| **L2**| Suspend | Software-initiated suspend                   |

### LTR (Latency Tolerance Reporting)

LTR allows USB devices to report their latency tolerance to the platform power manager:

| Parameter          | Description                                           |
|--------------------|-------------------------------------------------------|
| Max Snoop Latency  | Maximum tolerable snoop latency                       |
| Max No-Snoop Latency | Maximum tolerable no-snoop latency                 |

LTR values directly impact Package C-state entry — aggressive LTR allows deeper C-states.

### UAOL Isochronous Power Management

When USB Audio Offload (UAOL) is active, the xHCI offloads isochronous audio transfers to the ACE (Audio Compute Engine). This fundamentally changes how power management interacts with USB audio:

#### pNDE (Periodic Next Device Event)
ACE uses **pNDE** — a periodic scheduling mechanism that fires every **USB microframe (125µs)** to service isochronous endpoints. This is the fundamental timing unit for all USB audio transfers.

> **Key timing:** 1 USB frame = 1ms = 8 microframes. Each microframe = **125µs**. pNDE fires once per microframe. Any missed pNDE = lost audio data with **no hardware recovery**.

| Aspect | Standard NDE | pNDE (Isochronous) |
|--------|-------------|---------------------|
| Trigger | On-demand (doorbell ring) | Periodic — every **125µs** (1 microframe) |
| Miss tolerance | Retries available | **None — missed interval = lost audio data** |
| LPM interaction | Can enter U1/U2 between events | Must be in U0 or exit to U0 within **< 125µs** |
| Power impact | Allows deep idle | Prevents deep USB link sleep during active stream |

**LPM feasibility during active UAOL stream:**

| Link State | Exit Latency | Fits in 125µs? | Verdict |
|------------|-------------|-----------------|----------|
| U1 | ~1µs | Yes (ACE4/NVL: safe; ACE3/PTL: marginal — scheduling jitter may exceed margin) | Allowed with caution |
| U2 | ~2ms | **No** — 16× over budget | **NEVER during active stream** |
| U3 | ~10ms+ | **No** — 80× over budget | **NEVER during active stream** |

#### UAOL Power State Constraints

| USB State | UAOL Active? | Behavior |
|-----------|-------------|----------|
| **U0** | Yes | **Required** during active audio stream — pNDE fires every 125µs |
| **U1** | Conditional | Can enter between pNDE events **only if** exit latency << 125µs. ACE4 (NVL): acceptable. ACE3 (PTL): marginal, not recommended under load |
| **U2** | **No** | Exit latency (~2ms) is 16× the 125µs microframe budget — will miss pNDE |
| **U3** | **No** | Only after stream is explicitly stopped |
| **D3** | **No** | xHCI must remain in D0 while ACE is offloading |

#### Feedback FIFO and Power
The ACE Feedback FIFO buffers isochronous data between the ACE and xHCI:

| Platform | ACE Version | Feedback FIFO | Buffer Duration | Power Implication |
|----------|-------------|---------------|-----------------|-------------------|
| PTL | ACE3 | ~1ms per stream | ~8 microframes | Very tight — any scheduling delay causes underrun |
| NVL | ACE4 | Up to 10ms (4.5MB L2) | ~80 microframes | More headroom for power state transitions |

**Key insight**: ACE3 (PTL) has much tighter power/scheduling margins than ACE4 (NVL). Power management events that briefly delay pNDE scheduling may cause audio glitches on PTL but not on NVL.

#### UAOL Power Validation Considerations
```
When UAOL is active:
├── LPM must NOT enter U2/U3 on the audio endpoint's port
├── xHCI must remain in D0 (cannot RTD3)
├── LTR must reflect isochronous timing constraints
├── Package C-state entry is limited (xHCI in D0 blocks deep PkgC)
└── S0ix with UAOL active requires ACE to manage isochronous autonomously
```

### Runtime Suspend and Selective Suspend

**Runtime suspend** (also called **selective suspend**) allows individual USB devices to be suspended by the host while other devices remain active:

| Mechanism | Platform | Description |
|-----------|----------|-------------|
| **Runtime suspend** | Windows / Linux | xHCI autosuspends idle devices — device enters D3, link enters U3 |
| **Selective suspend** | Windows | Windows-specific USB PM — device driver requests hub to suspend individual port |
| **Autosuspend** | Linux | Linux USB PM — device auto-suspends after `autosuspend_delay_ms` idle timeout |

> Runtime suspend is distinct from system suspend (S3/S4). A device can runtime suspend while the rest of the system stays active (S0).

Key validation points:
- Confirm device supports runtime suspend (check USB descriptor `bU1DevExitLat`, `bU2DevExitLat`)
- Verify selective suspend policy in Windows Device Manager (Power Management tab)
- On Linux, check `/sys/bus/usb/devices/<bus>-<port>/power/autosuspend_delay_ms`

### Wake-on-USB

| PORTSC Bit | Name | Description                        |
|------------|------|------------------------------------|
| 25         | WCE  | Wake on Connect Enable             |
| 26         | WDE  | Wake on Disconnect Enable          |
| 27         | WOE  | Wake on Over-Current Enable        |

## Validation Scripts

### Check Device Power State
```python
from usb_helper_ipsv import USBHelper
helper = USBHelper()
state = helper.get_power_state(device)  # Returns "D0" or "D3"
```

### LPM Validation
```bash
python lpm.py --port <port_number> --check-u1
python lpm.py --port <port_number> --check-u2
```

### LTR Checking
```bash
python LTR_checker.py
```
Reads and validates LTR values for all enumerated USB devices.

### Package C-State Residency
```bash
python pkgc_residency_checker.py
```
Monitors Package C-state residency counters — USB LPM/LTR must be configured correctly for deep C-states.

### S0ix / Modern Standby Validation
```bash
python slp_s0.py
```
Validates S0ix entry/exit with USB devices connected. Checks:
- All USB links enter U3 during S0ix
- xHCI enters D3 during S0ix
- Wake-on-USB triggers correct resume
- No USB-related S0ix blockers

### S3/S4 Connect/Disconnect Tests
```bash
python test_run.py --test s3_connect
python test_run.py --test s3_disconnect
python test_run.py --test s4_connect
python test_run.py --test s4_disconnect
```

## Power Management Validation Workflow

### 1. Verify D0 → D3 Transition
```
1. Check device is in D0: usb_helper_ipsv.py --power-state
2. Trigger idle (no traffic for timeout period)
3. Verify D3 entry in PORTSC (PLS=U3) and PCI PM (PMCSR.PowerState=D3)
4. Resume traffic
5. Verify D0 re-entry and device is functional
```

### 2. Verify LPM U1/U2 Entry
```
1. Ensure LPM is enabled (PORTPMSC.HLE=1 for hardware LPM)
2. Send short burst of traffic, then idle
3. Monitor PORTSC.PLS for U1 entry (~µs after idle)
4. Extended idle → U2 entry (~ms after U1)
5. Verify exit latency meets spec
```

### 3. Verify S0ix with USB
```
1. Run slp_s0.py pre-check (all devices enumerated)
2. Enter Modern Standby
3. Verify xHCI enters D3, all ports in U3
4. Check SLP_S0# assertion (no USB blockers)
5. Wake via USB device (if WCE/WDE enabled)
6. Verify all devices re-enumerate correctly
```

## Per-Platform LPM Support Matrix

| Platform | USB 3.x U1 | USB 3.x U2 | USB 3.x U3 | USB 2.0 L1 | UAOL U2/U3 | Notes |
|----------|-----------|-----------|-----------|-----------|-----------|-------|
| NVL      | Yes       | Yes       | Yes       | Yes       | No (stream active) | ACE4: 10ms FIFO headroom; U1 allowed between pNDE |
| PTL      | Yes       | Yes       | Yes       | Yes       | No (stream active) | ACE3: ~1ms FIFO — U1 marginal during UAOL stream |
| LNL      | Yes       | Yes       | Yes       | Yes       | No (stream active) | Integrated SoC die — verify LPM via LNL HAS |
| MTL      | Yes       | Yes       | Yes       | Yes       | No (stream active) | UAOL behind hub NOT supported |
| ARL      | Yes       | Yes       | Yes       | Yes       | No (stream active) | Aligns with MTL/LNL patterns |

> **Rule:** U2/U3 must NOT be entered on the audio endpoint's port while UAOL stream is active. U1 is conditionally allowed only if exit latency is within the 125µs microframe budget.

> **Cross-reference:** For endpoint purge procedures and UAOL-related failure triage, load the `fv-usb/debug` skill — see the "Endpoint Purge" and "UAOL Debug" sections.

## UAOL Power State Validation Checklist

Use this checklist when validating USB power management with UAOL active:

```
[ ] 1. Confirm UAOL is active
      - Registry: HKLM\SYSTEM\CurrentControlSet\Services\usbxhci\Parameters
      - Or: check ACE FW version via onebkc skill

[ ] 2. Verify U0 during active audio stream
      - Run: python lpm.py --port <audio_port> --check-u0
      - PORTSC.PLS must = 0 (U0) on the audio device port

[ ] 3. Verify U2/U3 NOT entered during stream
      - Run: python lpm.py --port <audio_port> --check-u2 --check-u3
      - PLS must NOT be 2 (U2) or 3 (U3) while recording/playback active

[ ] 4. Verify xHCI stays in D0 during UAOL
      - Run: python usb_helper_ipsv.py --power-state
      - xHCI PCI PMCSR.PowerState must = 0x00 (D0)

[ ] 5. Check Feedback FIFO headroom (platform-dependent)
      - PTL/ACE3: ~1ms — monitor for underrun during PM transitions
      - NVL/ACE4: up to 10ms — more margin, but still verify

[ ] 6. Verify LTR reflects isochronous constraints
      - Run: python LTR_checker.py
      - USB LTR must not block platform from serving isochronous interrupts

[ ] 7. Check PkgC residency expectations
      - xHCI in D0 for UAOL will block deep PkgC — this is EXPECTED
      - Run: python pkgc_residency_checker.py (expect lower residency during UAOL)

[ ] 8. S0ix + UAOL interaction
      - S0ix entry should pause or cleanly stop UAOL stream first
      - Verify audio does not glitch on S0ix entry/exit
```

## Common Power Management Failures

| Symptom                           | Likely Cause                      | Debug Action                        |
|-----------------------------------|-----------------------------------|-------------------------------------|
| Device stuck in D0                | LPM not enabled, driver issue     | Check PORTPMSC, driver PM settings  |
| S0ix blocked by USB               | xHCI not entering D3              | Check RTD3 policy, LTR values       |
| No Package C-state residency      | LTR too aggressive (low value)    | Run LTR_checker.py, check values    |
| Device lost after S3 resume       | Re-enumeration failure            | Check PORTSC.CSC, driver event log  |
| Wake-on-USB not working           | WCE/WDE not set, BIOS config      | Check PORTSC wake bits, BIOS knobs  |
| U1/U2 not entering                | Device doesn't support LPM        | Check USB descriptor bU1DevExitLat  |
| High power in idle                | USB preventing deep sleep          | Run allchecker.py for full audit    |
| UAOL audio glitch during PM transition | pNDE missed due to LPM exit latency | Check U1/U2 entry during active stream, disable LPM on audio port |
| UAOL recording stuck after minutes | Feedback FIFO underrun (ACE3) | Check ACE FIFO sizing, compare ACE3 vs ACE4 behavior |
| No PkgC residency with UAOL active | xHCI stuck in D0 for offload | Expected — xHCI must be D0 during UAOL stream |

## Cross-Domain Delegation

| Issue                              | Delegate To        |
|------------------------------------|--------------------|
| PCH power gating not working       | **FV-PM-SOUTH**    |
| SLP_S0# not asserting              | **FV-PM-SOUTH**    |
| Platform-level power rail issues   | **TTK3-POWER**     |
| BIOS PM configuration              | **FV_Debugger_V1** |
| UAOL audio glitch during offload   | **fv-usb/debug**   |
| ACE FIFO underrun or scheduling    | **fv-usb/debug**   |

## Co-Design Lookup
Use the Playwright browser workflow to query Co-Design HAS for platform-specific power data:
1. `playwright_browser_navigate` to `https://chat.co-design.intel.com/chat`
2. `playwright_browser_snapshot` to locate the chat textarea
3. `playwright_browser_type` your query, then `playwright_browser_wait_for` the response
4. `playwright_browser_snapshot` to read the answer

> **Fallback:** If the browser is unavailable, load the `codesign` skill for REST API access.

**Domain-specific queries:**
- *"What are the xHCI RTD3 requirements for [platform]?"*
- *"What LTR values does the USB controller report on [platform]?"*
- *"Show the USB power management registers from NVL_USB_HAS"*
- *"What is the ACE Feedback FIFO size for UAOL on [platform]?"*
- *"How does pNDE scheduling work for isochronous transfers on [platform]?"*
- *"What are the UAOL power constraints — can xHCI enter D3 during audio offload on [platform]?"*
