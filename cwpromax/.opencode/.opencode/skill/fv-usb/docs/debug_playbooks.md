# FV-USB — Debug Playbooks

<!-- owner: kvejaya -->

> Last Updated: 2026-03-20
> Each playbook is a step-by-step decision tree for a specific USB failure scenario. Follow the numbered steps in order; branch at decision points.

---

## Playbook 1: Device Not Enumerated (NDE)

**Symptom:** USB device physically connected but not visible in Device Manager or `treeview.py`. NGA exit code 12.

```
Step 1: Check physical connection
  └─ Is cable seated firmly? Try different cable.
  └─ Is port powered? Check LED / hub power indicator.

Step 2: Run NDE_checker.py
  $ python NDE_checker.py
  └─ If NDE_checker reports specific port → go to Step 3
  └─ If NDE_checker sees no ports → check BIOS knobs (config-checkout)

Step 3: Read PORTSC for the affected port
  PythonSV:
    import pysvtools.pciedut as pcie
    xhci = pcie.get_device(bus=0, dev=0x14, func=0)
    # PORTSC offset = 0x400 + 16*(port-1)
    portsc = xhci.mmio.read(0x400 + 16*(port_num-1), 4)
    print(f"PORTSC = {portsc:#010x}")
    ccs = (portsc >> 0) & 1   # Current Connect Status
    ped = (portsc >> 1) & 1   # Port Enabled
    pls = (portsc >> 5) & 0xF # Port Link State
    pp  = (portsc >> 9) & 1   # Port Power
    speed = (portsc >> 10) & 0xF  # Port Speed
    print(f"CCS={ccs} PED={ped} PLS={pls} PP={pp} Speed={speed}")

Step 4: Branch on PORTSC values
  ├─ CCS=0, PP=1 → Device not detected at PHY level
  │   └─ Check signal integrity (cable, connector, board trace)
  │   └─ Try warm port reset: write PORTSC.WPR=1
  │   └─ If still CCS=0 → possible dead port or device. Try different port.
  │
  ├─ CCS=0, PP=0 → Port power is OFF
  │   └─ Check BIOS knob "USB Port Disable"
  │   └─ Write PORTSC.PP=1 to power the port
  │   └─ If PP won't set → escalate to FV-PM-SOUTH (power gating issue)
  │
  ├─ CCS=1, PED=0, PLS=7 (Polling) → Link training in progress
  │   └─ Wait 2-5 seconds, re-read PORTSC
  │   └─ If stuck in Polling → signal integrity or device PHY issue
  │
  ├─ CCS=1, PED=0, PLS=10 (Compliance Mode) → Signal integrity failure
  │   └─ See Playbook 5 (Compliance Mode Trap)
  │
  ├─ CCS=1, PED=1, PLS=0 (U0) → Port looks healthy!
  │   └─ Device should be visible. Run treeview.py again.
  │   └─ If still not visible → driver issue. Check yellowbang_usb.py
  │   └─ If yellow-bang → reinstall driver per BKC
  │
  └─ CCS=1, PED=0, PLS=5 (Rx.Detect) → Link reset failed
      └─ Issue warm reset: PORTSC.WPR=1
      └─ If persistent → file HSDES sighting with PORTSC dump

Step 5: Collect debug bundle
  $ python allchecker.py > nde_debug.txt 2>&1
  $ python treeview.py >> nde_debug.txt 2>&1
  $ python yellowbang_usb.py >> nde_debug.txt 2>&1
  Capture ETL trace (see debug/etl-decode sub-skill)

Step 6: Search HSDES
  Use sighting-info skill with keywords: "USB NDE <platform> port <port_num>"
```

---

## Playbook 2: Wrong Speed Negotiation

**Symptom:** USB 3.x device enumerating at USB 2.0 High Speed (480 Mbps) instead of SuperSpeed (5/10/20 Gbps).

```
Step 1: Confirm current speed
  $ python -c "from usb_helper_ipsv import USBHelper; h=USBHelper(); print(h.get_speed(PORT))"
  Expected: 4 (SS 5G), 5 (SS+ 10G), or 6 (SS+ 20G)
  Actual: 3 (HS 480M) ← WRONG

Step 2: Check SS companion port
  USB 3.x ports have paired USB2 and USB3 PORTSC registers.
  If USB3 PORTSC shows CCS=0 but USB2 PORTSC shows CCS=1 → device fell back to USB2.
  PythonSV:
    # USB3 ports start at higher offset — check HCSPARAMS1 for port split
    # Read both USB2 and USB3 PORTSC for the same physical connector

Step 3: Check cable
  ├─ USB 3.x requires shielded cable with SS signal pairs
  ├─ Try a known-good certified USB 3.x cable
  └─ If cable change fixes it → original cable was USB 2.0 only or damaged

Step 4: Check BIOS knob
  ├─ "USB3 Speed" BIOS knob → should be "Auto" or "Gen2"
  └─ If set to "Disabled" or "Gen1" → change and reboot

Step 5: Check device descriptor
  $ python -c "
  import usb.core
  dev = usb.core.find(idVendor=0xVVVV, idProduct=0xPPPP)
  print(f'bcdUSB={dev.bcdUSB:#06x}')  # Should be 0x0300+ for USB3
  print(f'Speed={dev.speed}')
  "

Step 6: If all above pass, suspect PHY/link training issue
  └─ Capture ETL trace during device connection
  └─ Look for LTSSM transitions: Rx.Detect → Polling → U0
  └─ If link fails at Polling → PHY/signal integrity
  └─ Check known_issues.md for platform-specific errata
  └─ File HSDES sighting with PORTSC dump + ETL trace
```

---

## Playbook 3: USB Blocking S0ix (SLP_S0# Not Asserting)

**Symptom:** Platform cannot enter S0ix/Modern Standby. SLP_S0# signal not asserting. USB identified as blocker in `slp_s0.py` output.

```
Step 1: Identify the USB blocker
  $ python slp_s0.py
  └─ Output identifies which USB device/port is blocking S0ix

Step 2: Check xHCI power state
  PythonSV:
    # Read PMCS (Power Management Control/Status) register
    xhci = pcie.get_device(bus=0, dev=0x14, func=0)
    pmcs = xhci.cfg.read(0x74, 4)  # PMCS offset varies — check HAS
    power_state = pmcs & 0x3  # D0=0, D3hot=3
    print(f"xHCI Power State = D{power_state}")
  
  ├─ D0 → xHCI not entering D3. Go to Step 3.
  └─ D3 → xHCI is in D3. USB is not the S0ix blocker — check other IPs.

Step 3: Check which ports prevent D3
  For each port:
    PythonSV:
      portsc = xhci.mmio.read(0x400 + 16*(port-1), 4)
      pls = (portsc >> 5) & 0xF
      print(f"Port {port}: PLS={pls}")
  
  ├─ All ports PLS=3 (U3/Suspended) → ports are OK, check RTD3 policy
  └─ Any port PLS=0 (U0/Active) → that device is preventing suspend
      └─ Identify the device on that port (treeview.py)
      └─ Check if device supports selective suspend
      └─ Check device driver power policy

Step 4: Check LTR values
  $ python LTR_checker.py
  └─ If LTR is too aggressive (low value) → may prevent deep C-state
  └─ Check known_issues.md for LTR-related sightings

Step 5: Check RTD3 policy
  ├─ BIOS knob "RTD3 for USB" must be Enabled
  ├─ Windows registry: check USB selective suspend is enabled
  └─ Group Policy: check power plan allows USB selective suspend

Step 6: Check Package C-state residency
  $ python pkgc_residency_checker.py
  └─ If PC2+ residency is 0 → platform power issue
  └─ Delegate to FV-PM-SOUTH agent for platform-level analysis

Step 7: Collect debug bundle
  $ python slp_s0.py > s0ix_debug.txt 2>&1
  $ python LTR_checker.py >> s0ix_debug.txt 2>&1
  $ python pkgc_residency_checker.py >> s0ix_debug.txt 2>&1
  $ python allchecker.py >> s0ix_debug.txt 2>&1
  Capture ETL trace during S0ix entry attempt
```

---

## Playbook 4: UAOL Audio Recording Stuck

**Symptom:** USB audio recording stops after ~30 seconds to 3 minutes when UAOL is enabled. Playback may still work. Primarily seen on PTL with ACE3.

```
Step 1: Check known issues
  └─ HSDES 16029865294: PTL/ACE3 recording stuck with Astro40 headset
  └─ If symptom matches → apply workaround from known_issues.md

Step 2: Verify UAOL is active
  Check registry:
    reg query "HKLM\SYSTEM\CurrentControlSet\Services\UAOL" /v Enable
  ├─ Enable=1 → UAOL active. Continue.
  └─ Enable=0 → UAOL disabled. Issue is NOT UAOL-related. Debug as standard USB audio.

Step 3: Compare UAOL-enabled vs UAOL-disabled behavior
  Disable UAOL:
    reg add "HKLM\SYSTEM\CurrentControlSet\Services\UAOL" /v Enable /t REG_DWORD /d 0 /f
    # Reboot required
  
  ├─ Recording works with UAOL disabled → UAOL-specific issue. Continue.
  └─ Recording fails with UAOL disabled too → NOT UAOL. Debug as standard USB audio issue.

Step 4: Check ACE FW version
  Use onebkc skill to verify ACE FW version matches current BKC.
  ├─ FW is up to date → Continue to Step 5
  └─ FW is outdated → Update to BKC version and retest

Step 5: Capture UAOL ETL trace
  Start capture with UAOL provider:
    logman create trace UAOLTrace -ow -o C:\UAOLTrace.etl \
      -p "Microsoft-Windows-USB-UAOL" 0xFFFFFFFF 0xFF \
      -p "Microsoft-Windows-USB-USBXHCI" 0xFFFFFFFF 0xFF
    logman start UAOLTrace
  
  Reproduce recording stuck scenario. Stop capture when recording stalls.
  
  Analyze ETL for:
  - EndpointPurge events (xHCI → ACE handoff)
  - MissedServiceInterval events
  - FIFO underrun/overrun indicators
  - Timing gap between last successful isochronous transfer and failure

Step 6: Check ACE3 vs ACE4
  ├─ PTL (ACE3): ~1ms feedback FIFO. Vulnerable to pNDE scheduling jitter.
  │   └─ If possible, test same device on NVL (ACE4) to confirm ACE3-specific.
  └─ NVL (ACE4): 10ms FIFO. Should absorb jitter.
      └─ If still failing on ACE4 → different root cause. Check HSDES 18043001729.

Step 7: Check PSF glitch risk (NVL only)
  └─ Verify DfSPSREQ register is set in ACE FW
  └─ If PSF not kept alive during UAOL → audio glitch (see known_issues.md §Integration Notes #1)

Step 8: File HSDES sighting
  Include: platform, ACE version, device model, ETL trace, repro steps, timing data.
  Reference HSDES 16029865294 if PTL/ACE3.
```

---

## Playbook 5: Compliance Mode Trap (PLS=10)

**Symptom:** USB 3.x port stuck in Compliance Mode (PORTSC.PLS=10). Device not functional. Link cannot exit compliance without intervention.

```
Step 1: Confirm Compliance Mode
  PythonSV:
    portsc = xhci.mmio.read(0x400 + 16*(port-1), 4)
    pls = (portsc >> 5) & 0xF
    assert pls == 10, f"Not in Compliance Mode (PLS={pls})"

Step 2: Attempt warm port reset
  PythonSV:
    # Set WPR (Warm Port Reset) bit in PORTSC
    portsc |= (1 << 31)  # WPR is bit 31
    xhci.mmio.write(0x400 + 16*(port-1), portsc, 4)
    # Wait for reset to complete
    import time; time.sleep(1)
    portsc = xhci.mmio.read(0x400 + 16*(port-1), 4)
    pls = (portsc >> 5) & 0xF
    print(f"After warm reset: PLS={pls}")
  
  ├─ PLS=0 (U0) → Reset succeeded. Device should enumerate.
  └─ PLS=10 (still Compliance) → Continue to Step 3.

Step 3: Check cable and connector
  ├─ Replace with certified USB 3.x cable
  ├─ Try different physical port
  ├─ Try different device
  └─ If Compliance Mode only on one port with any cable/device → board SI issue

Step 4: Check board signal integrity
  └─ Inspect board trace for the affected port
  └─ Check connector for damage or contamination
  └─ If multiple ports affected → possible reference clock issue

Step 5: Platform-specific checks
  ├─ NVL: Check PCH-H vs PCH-S die variant — different PHY tuning
  ├─ PTL: Check eUSB2 PHY init sequence (known_issues.md §Integration Notes #4)
  └─ Check known_issues.md for platform-specific compliance mode errata

Step 6: If persistent across cables/ports/devices
  └─ File HSDES sighting as potential RTL or board SI issue
  └─ Include: PORTSC dump, cable info, port number, platform, die variant
  └─ Tag: xHCI, LTSSM, Compliance Mode
```

---

## Debug Bundle Collection Template

For any USB failure, collect this standard debug bundle before filing HSDES:

```bash
#!/bin/bash
# USB Debug Bundle Collection Script
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUNDLE_DIR="usb_debug_bundle_${TIMESTAMP}"
mkdir -p ${BUNDLE_DIR}

# Core diagnostics
python allchecker.py > ${BUNDLE_DIR}/allchecker.txt 2>&1
python treeview.py > ${BUNDLE_DIR}/treeview.txt 2>&1
python yellowbang_usb.py > ${BUNDLE_DIR}/yellowbang.txt 2>&1
python NDE_checker.py > ${BUNDLE_DIR}/nde_checker.txt 2>&1

# Power diagnostics
python LTR_checker.py > ${BUNDLE_DIR}/ltr.txt 2>&1
python pkgc_residency_checker.py > ${BUNDLE_DIR}/pkgc.txt 2>&1
python slp_s0.py > ${BUNDLE_DIR}/slp_s0.txt 2>&1

# Device tree
python treeview.py -v > ${BUNDLE_DIR}/treeview_verbose.txt 2>&1

echo "Debug bundle collected: ${BUNDLE_DIR}"
echo "Attach this directory to HSDES sighting."
```

---

---

## Playbook 6: PM Clock Request Stuck High

**When to use:** USB3 clock request signal stays asserted after applying PM register settings; `USB3_PRIM_CLKREQ=1`, `ux_ibbs_prim_clkreq=1`, or ROSC/Main PLL cannot shut down; seen in SLE/SVOS/PO bringup PM debug.

**Root cause:** xHCI Run/Stop bit (`USBCMD.RS`) not cleared. The PM enabling sequence must clear PORTSC.PP on all ports **and** clear `USBCMD.RS` — missing either step keeps clkreq asserted.

### Step-by-Step

```
1. Verify symptom:
   - Read USB3_PRIM_CLKREQ or ux_ibbs_prim_clkreq via P2SB/PythonSV/SLE signal
   - Confirm = 1 (stuck high) when it should be 0 for PM gating

2. Clear PORTSC.PP for ALL ports:
   - Loop over all ports (even disconnected ones): PORTSC.PP = 0
   - Verify read-back: PORTSC.PP should return 0
   - If read-back hangs → check for EXI fuse status (see HSDES 1404420695)

3. Clear USBCMD.RS (Run/Stop):
   - Write USBCMD.RS = 0 (stop the controller)
   - Wait for USBSTS.HCH = 1 (Halted bit) to confirm stop
   - Do NOT proceed until HCH=1

4. Verify clkreq de-asserted:
   - Re-read USB3_PRIM_CLKREQ / ux_ibbs_prim_clkreq
   - Should now = 0

5. If still stuck after Steps 2-4:
   - Check USB3_SIDE_CLKREQ as well (separate signal for side PLL)
   - Check if xDCI (Device Controller) is also running — clear xDCI separately
   - Check BIOS strap: if xHCI is strap-disabled but PRIM_CLKREQ=1, RTL bug
     → file HSDES sighting referencing 1404345436

6. Attach PM debug bundle to sighting:
   python slp_s0.py > slp_s0.txt
   python LTR_checker.py > ltr.txt
   (SLE only: attach P2SB register access log + VTDB/VCD waveform screenshot)
```

### Signal Reference
| Signal | Domain | Description |
|--------|--------|-------------|
| `USB3_PRIM_CLKREQ` | Primary clock | Controls Main PLL shutdown; must = 0 for PLL SD |
| `USB3_SIDE_CLKREQ` | Side clock | Controls ROSC SIDE TCG; separate from primary |
| `ux_ibbs_prim_clkreq` | Internal SLE signal | Same semantic as USB3_PRIM_CLKREQ in SLE testbench |
| `USBCMD.RS` | MMIO (offset 0x00, bit 0) | Run/Stop; must = 0 before PM clock gates can assert |
| `USBSTS.HCH` | MMIO (offset 0x04, bit 0) | Halted; = 1 confirms controller stopped |

### Related HSDES Sightings
- **1404376679** — PORTSC.PP cleared but USBCMD.RS not cleared → clkreq stuck
- **1404302197** — `ux_ibbs_prim_clkreq=1` after PM enabling, P2SB/Rambo access
- **1404376674** — `USB3_SIDE_CLKREQ=1`, needed 0 for ROSC SIDE TCG
- **1404345436** — xHCI strap-disabled but `PRIM_CLKREQ=1` → RTL bug

---

## Cross-References

| Playbook | Related Sub-Skill | Related Doc |
|----------|-------------------|-------------|
| NDE | `fv-usb/enumeration`, `fv-usb/config-checkout` | `known_issues.md` |
| Wrong Speed | `fv-usb/enumeration`, `fv-usb/xhci` | `cheat_sheet.md` (speed map) |
| S0ix Blocker | `fv-usb/power` | `known_issues.md` (PM section) |
| UAOL Stuck | `fv-usb/debug` (UAOL section) | `known_issues.md` (HSDES 16029865294) |
| Compliance Mode | `fv-usb/xhci` (PORTSC) | `known_issues.md` (LTSSM section) |
| PM Clock Stuck | `fv-usb/power`, `fv-usb/xhci` | `known_issues.md` (PM clkreq entry) |
