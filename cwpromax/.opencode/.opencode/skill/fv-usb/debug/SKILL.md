---
name: debug
version: 2.2.0
owner: kvejaya
description: USB failure triage, HSDES sighting lookup, NGA exit code interpretation, debug workflows, platform-specific notes, known errata, and debug bundle collection
---

> **Owner**: Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

# FV-USB / Debug — USB Failure Triage & Debug Workflows

## Purpose
This sub-skill covers USB failure triage, debug workflows, HSDES sighting lookup, common failure signatures, and systematic root-cause analysis for USB validation failures.

> **Before triaging any failure:** Check `fv-usb/docs/known_issues.md` first — the failure may already have a known root cause and workaround.

## NGA Exit Code Interpretation

| Code | Meaning              | USB-Specific Action                                          |
|------|----------------------|--------------------------------------------------------------|
| 0    | PASS                 | No action needed                                             |
| 1    | FAIL                 | Run triage flowchart below; collect debug bundle             |
| 12   | Device not found     | Load `fv-usb/enumeration`; check PORTSC.CCS and PLS         |
| 13   | Configuration error  | Check script config, platform BDF, Galaxy XML parameters     |

## Platform-Specific Debug Notes

| Platform | Key Debug Differences                                                                                      |
|----------|------------------------------------------------------------------------------------------------------------|
| **NVL**  | Two die variants (PCH-H / PCH-S) — USB config may differ. Always confirm die variant before interpreting register dumps. ACE4 FIFO: up to 10ms. Use NVL-specific HAS docs. HSDES 18043001729 for ACE4 FIFO. |
| **PTL**  | ACE3 FIFO: ~1ms — very tight margin. UAOL recording stuck (HSDES 16029865294) is a known ACE3 issue. UAOL behind hub supported (fixed from MTL). |
| **LNL**  | Integrated die — USB controller is on the SoC die, not a separate PCH. BDF and BAR assignments may differ from discrete PCH platforms. Verify against LNL HAS. |
| **MTL**  | UAOL behind hub NOT supported (RTL bug). Do not test UAOL behind hub on MTL — this is by design (fixed PTL+). |
| **ARL**  | Arrow Lake — confirm ARL-specific HAS. USB generally aligns with MTL/LNL patterns. |
| **WCL/RZL/TTL** | Query Co-Design for platform-specific differences. Do not assume register layouts from older platforms. |

## When to Use
- User encounters a USB test failure and needs triage guidance
- User needs to look up HSDES sightings for a USB issue
- User sees yellow-bang, NDE, or enumeration failures
- User needs to analyze USB-related crash dumps or logs
- User asks about known USB errata or workarounds
- User needs step-by-step debug flow for a USB symptom

## Debug Triage Flowchart

```
USB Failure Detected
        │
        ├── Device not enumerated?
        │   ├── Check PORTSC.CCS (connected?)
        │   │   ├── CCS=0 → Physical: cable, connector, CSwitch
        │   │   └── CCS=1 → Check PED, PLS, Speed
        │   ├── Run yellowbang_usb.py (driver failure?)
        │   ├── Run NDE_checker.py (port-level check)
        │   └── Check BIOS USB enable knobs
        │
        ├── Wrong speed?
        │   ├── Check cable (SS requires SS cable)
        │   ├── Check PORTSC.Speed vs expected
        │   ├── Check LTSSM — stuck in Polling/Rx.Detect?
        │   └── Try different port / device
        │
        ├── Data transfer failure?
        │   ├── Check transfer ring for error TRBs
        │   ├── Check USBSTS for Host System Error
        │   ├── Run bulkstart.py / isochstart.py standalone
        │   └── Check device-side error counters
        │
        ├── Power management failure?
        │   ├── Load fv-usb/power sub-skill
        │   ├── Check D-state, LPM, LTR
        │   ├── Run pkgc_residency_checker.py
        │   └── Run slp_s0.py
        │
        ├── Hot-plug failure?
        │   ├── Check PORTSC.CSC (change detected?)
        │   ├── Check CSwitch connection (cswitch_api.py)
        │   ├── Run hotplug.py with debug logging
        │   └── Check device re-enumeration
        │
        └── Unknown / complex failure?
            ├── Collect allchecker.py output
            ├── Search HSDES for matching sighting
            ├── Collect BIOS boot log (UART)
            └── Delegate to FV_Debugger_V1
```

## Diagnostic Scripts

### Comprehensive State Check
```bash
python allchecker.py
```
Runs all USB checks in sequence — enumeration, speed, link status, power state, driver status. **Start here for unknown failures.**

### Yellow-Bang Detection
```bash
python yellowbang_usb.py
```
Scans Device Manager for USB devices with driver failures (yellow exclamation mark).

**Common yellow-bang causes:**
- Driver version mismatch
- Corrupted device descriptor
- Resource conflict
- xHCI controller error

### NDE (No Device Enumerated) Check
```bash
python NDE_checker.py
```
Identifies ports where devices are physically connected but not enumerated by the OS.

**Common NDE causes:**
- Link training failure (check LTSSM)
- Port disabled in BIOS
- xHCI controller reset failed
- Device firmware hang

### ModPHY Register Access (PythonSV — Pre-Silicon / SLE)

For PHY-level debug on pre-silicon platforms. These registers are **not accessible** on production silicon via normal OS tools.

```python
# Elastic Buffer (EB) underflow/overflow sticky flags
# (from HSDES 1404200330 — registers non-functional: read-back always 0x0)
sv.socket0.uncore.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword17.show()
# Fields:
#   reg_rxg3eb_underflow_sticky (bit 9)
#   reg_rxg3eb_overflow_sticky  (bit 10)

# PI quad sensitivity / bonux code override
# (from HSDES 1404165520 — reduce quad sensitivity via bonux code override)
sv.socket0.uncore.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword14.reg_bonuxcode_ovrd_en = 0x1

# DFE Data Summer CM calibration register
# Expected 0x23; if reading 0x9 → asymmetric DFE convergence (see HSDES 1404377924)
sv.socket0.uncore.modphy.readregister("dlane%d" % lane).datasumcmcal0_7_0.show()
```

> **Note (PTL):** Do NOT use f-strings in PythonSV on PTL. Use `%` formatting: `"dlane%d" % lane`.

**Common pre-silicon PHY debug knobs:**
- `cmos2clm RC setting` — fixes RX clock instability (HSDES 1404148593)
- `bonux code override` — reduces PI quad sensitivity (HSDES 1404165520)
- `IO voltage margining` — workaround for Gen2 link-up failure at 1.05V (boost to 1.15V–1.2V)

### Device Tree Validation
```bash
python treeview.py
```
Displays full USB topology. Compare against expected BOM (Bill of Materials) configuration.

## Debug Tools

### Windows USB Debug Tools

| Tool | Purpose | How to Launch |
|------|---------|---------------|
| **USBView** (usbview.exe) | Graphical USB device tree viewer — shows all hubs, ports, devices, descriptors | `usbview.exe` (part of Windows SDK / WDK) |
| **WinUSB** | Generic USB driver for direct device access without a custom driver | Used via `winusb.h` API or via `usb_helper_ipsv.py` |
| **usbhcdiag** | xHCI host controller diagnostic tool — reads controller registers, port states, event ring | `usbhcdiag.exe /port <N>` |
| **Device Manager** | Yellow-bang detection, driver version, device properties | `devmgmt.msc` |
| **Windows Event Viewer** | USB error events, driver fault logs | `eventvwr.msc` → System → filter by `usbxhci` |
| **logman / WPP trace** | Real-time xHCI driver trace (usbxhci.sys, usbhub3.sys) | `logman start usbtrace -p Microsoft-Windows-USB-USBXHCI 0xFFFF 5` |

> **Quick start for unknown failures:** Use `USBView` first to confirm device enumeration, then `usbhcdiag` for controller register state.

### USB Protocol Analyzers (Hardware)

For signal-level or protocol-level capture that the software stack cannot provide:

| Analyzer | Vendor | USB Speeds Supported | Notes |
|----------|--------|---------------------|-------|
| **LeCroy** (Voyager / Summit) | Teledyne LeCroy | USB 2.0 / USB 3.2 / USB4 | Industry standard for xHCI/USB4 validation |
| **Beagle** (480 / 5000 / 10000) | Total Phase | USB 2.0 / USB 3.2 | Compact; good for enumeration debug |
| **Ellisys** USB Explorer | Ellisys | USB 2.0 / USB 3.2 / USB4 | Full protocol decode including UAOL isochronous |

**When a hardware protocol analyzer is required:**
- UAOL isochronous gap investigation (ACE offload is invisible to xHCI trace — only wire capture can show gaps)
- Signal integrity issues (compliance mode, link training failure)
- Hub split-transaction timing analysis
- Intermittent enumeration failures not captured in software logs

**When software tools are sufficient:**
- Driver-level failures (yellow-bang, resource conflicts)
- PORTSC register state queries
- Power management failures (D3, LTR, S0ix)
- NGA test result analysis

## Log Collection

### Key Log Locations
| Log Type              | Location / Method                                |
|-----------------------|--------------------------------------------------|
| Galaxy test logs      | `C:\validation\windows-test-content\usb\logs\`   |
| Windows Event Log     | `eventvwr.msc` → System → USB errors             |
| Driver traces         | `logman` / WPP tracing for usbxhci.sys           |
| BIOS POST log         | UART capture (use UART-MONITOR agent)             |
| xHCI debug capability | Platform-specific extended capability register    |

### Collect Debug Bundle
```bash
python allchecker.py > usb_debug_bundle.txt 2>&1
python treeview.py >> usb_debug_bundle.txt 2>&1
python yellowbang_usb.py >> usb_debug_bundle.txt 2>&1
python NDE_checker.py >> usb_debug_bundle.txt 2>&1
```

## HSDES Sighting Lookup

When a failure matches a known pattern, search HSDES:

1. **Use the `sighting-info` skill** to query HSDES
2. Search with keywords: `USB`, `xHCI`, `enumeration`, `LPM`, platform name
3. Filter by tenant: `sighting` or `bug`
4. Check status: `open`, `resolved`, `duplicate`

### Common Sighting Keywords
| Failure Type          | HSDES Search Keywords                          |
|-----------------------|------------------------------------------------|
| Enumeration failure   | `USB enumeration NDE xHCI [platform]`          |
| Speed fallback        | `USB speed SS HS fallback [platform]`          |
| Link compliance       | `USB compliance mode LTSSM [platform]`         |
| D3/RTD3 failure       | `USB D3 RTD3 power xHCI [platform]`            |
| S0ix blocker          | `USB S0ix SLP_S0 blocker [platform]`           |
| Hot-plug failure      | `USB hotplug CSC connect disconnect [platform]`|
| Data transfer error   | `USB bulk isoch transfer error [platform]`     |
| Yellow-bang           | `USB driver yellow bang [platform]`            |
| PM clock stuck high   | `USB clkreq PRIM_CLKREQ USBCMD RS [platform]`  |
| Gen2 not working      | `USB HCIVERSION SSP Gen2 driver [platform]`    |
| LTSSM stuck polling   | `USB LTSSM polling detect stuck [platform]`    |
| U1/U2 exit fail       | `USB U1 U2 TS1 TS2 exit LFPS [platform]`       |
| PHY/SI failure        | `USB ModPHY LFPS rxdatavalid DFE [platform]`   |

### PORTSC Hex Value Decode

When reading raw PORTSC register values from logs or SLE captures:

| PORTSC Value | Decoded State | Common Context |
|-------------|--------------|----------------|
| `0x12B1`    | CCS=1, PED=1, PLS=2(U2), Speed=4(SS 5G), CSC=1 | Link lost during SV filesystem mount |
| `0x0611`    | CCS=1, PLS=0(U0), Speed=4(SS 5G), but LTSSM=5(rxdet) | U1 entry failure — phy_status never asserted |
| `0x1A0`     | CCS=0, PLS=5(RxDetect), PP=1 | Normal idle, no device connected |
| `0x280`     | CCS=0, PLS=10(Compliance), PP=1 | Compliance mode trap — SI issue |
| `0x263`     | CCS=1, PED=1, PLS=0(U0), Speed=3(HS 480M) | HS device in U0 (normal) |

> **Tip:** Decode PORTSC in 4 fields — CCS[0], PLS[8:5], Speed[13:10], CSC[17]. Run `usbhcdiag.exe /port <N>` to get a named-field decode automatically.

### LTSSM State Decode

When `ltssm_state[5:0]` is read directly from MMIO (pre-silicon or P2SB access):

| Value | LTSSM State | Action |
|-------|-------------|--------|
| `0x00` | U0 — Active | Normal |
| `0x04` | U1 | LPM state |
| `0x05` | RxDetect | No device or link training failed |
| `0x07` | Polling | Link training in progress — stuck here = SI issue |
| `0x08` | Recovery | Link recovering — stuck = LTSSM desync |
| `0x0A` | Recovery (alt) | Scrambling or PHY issue (e.g. scrambling disabled) |
| `0x0F` | Inactive | Port inactive — desync between LTSSM and PM state |
| `0x10` | Compliance | Compliance mode — WPR warm reset to exit |

> **Root cause pattern (HSDES):** `LTSSM stuck = 0x07 (Polling)` at PO bringup → IO voltage margining (1.05 V → 1.15 V) is a fast diagnostic knob before PHY tuning.

### ModPHY Register Access (Pre-Silicon / SLE)

For pre-silicon environments with ModPHY access via PythonSV:

```python
# Read elastic buffer overflow/underflow sticky bits (per-lane)
lane = 0
sv.read_modphy = lambda reg: ulk.modphy.readregister("dlane%d" % lane)

# Check if EB underflow/overflow sticky bits asserted
dw17 = ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword17
dw17.show()
# Fields: reg_rxg3eb_underflow_sticky[09:09], reg_rxg3eb_overflow_sticky[10:10]

# Override PI quad sensitivity (bonux code) — reduces intermittent U2/Ux failures
dw14 = ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword14
dw14.reg_bonuxcode_ovrd_en = 0x1

# DFE Data Summer CM calibration — check for convergence (expected ~0x23, bad=0x09)
dw_cal = ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.datasumcmcal0_7_0
print("DFE CM cal:", hex(dw_cal))

# Check eUSB2 PHY (NVL only)
sv.socket0.uncore.usb.eusb2phy[0].show()
```

> **Note:** ModPHY register paths are platform/stepping-specific. The above examples are from ULK (Union Lake) family. Adapt namespace for current platform. On post-silicon PTL/NVL, use PythonSV `portsc[i].show()` and `usbsts.show()` instead — direct ModPHY access is not available post-silicon.
| U1/U2 transition fail | `USB U1 U2 LPM LTSSM phystatus [platform]`     |
| Link stuck LTSSM      | `USB LTSSM Polling Inactive Recovery [platform]`|

### PORTSC Hex Value Quick Decode

Common PORTSC raw values seen in HSDES sightings — use for first-pass triage before full decode:

| Raw PORTSC  | CCS | PED | PLS   | PP | Speed | Meaning / Action |
|-------------|-----|-----|-------|----|-------|-----------------|
| `0x00000001`| 1   | 0   | 0=U0  | 0  | 0     | Device seen but port not enabled + not powered — check PP |
| `0x001002B0`| 0   | 0   | 5=RxDet| 1 | 0     | Normal idle — no device |
| `0x00000611`| 1   | 0   | 5=RxDet| 1 | 0     | U1 entry fail — PHY phy_status timeout, LTSSM rolled back |
| `0x000012B1`| 1   | 0   | 5=RxDet| 1 | 0     | Link lost bad state — seen during SV mount / stress |
| `0x00001433`| 1   | 1   | 0=U0  | 1  | 4=SS  | SS device active — normal |
| `0x000014B3`| 1   | 1   | 6=Inactive| 1 | 4=SS | Link went Inactive after recovery timeout |
| `0x00001533`| 1   | 1   | 0=U0  | 1  | 5=SS+ | Gen2 device active — normal |
| `0x000003D2`| 0   | 1   | 7=Polling| 1 | 0   | Link training in progress — wait 2-5s |
| `0x000005D3`| 1   | 0   | 10=Comp| 1 | 0    | Compliance mode trap — SI issue |

> **How to decode any PORTSC value:**
> ```python
> portsc = 0x00000611  # replace with actual value
> ccs   = (portsc >> 0) & 0x1
> ped   = (portsc >> 1) & 0x1
> pls   = (portsc >> 5) & 0xF
> pp    = (portsc >> 9) & 0x1
> speed = (portsc >> 10) & 0xF
> print("CCS=%d PED=%d PLS=%d PP=%d Speed=%d" % (ccs, ped, pls, pp, speed))
> ```

## Common Failure Signatures & Root Causes

### 1. PORTSC.PLS = Compliance Mode (10)
**Signature:** Link stuck in compliance mode after connect
**Root Causes:**
- Signal integrity issue (cable, connector, board trace)
- Receiver detection failure
- RTL bug in LFPS signaling
**Debug Steps:**
1. Try different cable (certified SS cable)
2. Try different port
3. Check HAS for compliance mode errata
4. If persistent, may be RTL/board issue — file HSDES sighting

### 2. USBSTS.HSE = 1 (Host System Error)
**Signature:** xHCI controller reports host system error
**Root Causes:**
- Invalid MMIO access
- DMA error (bad address in TRB)
- PCIe link error affecting xHCI
**Debug Steps:**
1. Check USBSTS register for HSE bit
2. Check PCIe AER (Advanced Error Reporting) for xHCI BDF
3. Check DCBAAP alignment (64-byte aligned required)
4. Restart xHCI controller (HCRST)

### 3. Device Lost After S3 Resume
**Signature:** USB device present before S3, gone after resume
**Root Causes:**
- Re-enumeration timeout
- Port power not restored
- xHCI firmware hang during resume
**Debug Steps:**
1. Check PORTSC.CCS and PED after resume
2. Check PORTSC.PP (port power)
3. Verify xHCI USBCMD.Run/Stop after resume
4. Check BIOS S3 resume path (UART log)

### 4. USB Causing S0ix Failure
**Signature:** SLP_S0# not asserting, USB identified as blocker
**Root Causes:**
- xHCI not entering D3
- LTR values preventing deep C-state
- USB device not entering U3/suspend
**Debug Steps:**
1. Run `slp_s0.py` for S0ix substate analysis
2. Run `LTR_checker.py` for LTR values
3. Check all ports in U3 via PORTSC.PLS
4. Verify xHCI PCI PMCSR shows D3
5. Delegate to **FV-PM-SOUTH** if platform-level blocker

### 5. PM Clock Request Stuck High (USB3_PRIM_CLKREQ / ux_ibbs_prim_clkreq)
**Signature:** USB3 clock request signal stays asserted after PM enabling script; Main PLL or ROSC cannot shut down; `USB3_PRIM_CLKREQ=1` or `ux_ibbs_prim_clkreq=1` in SLE/SVOS environment
**Root Causes:**
- USBCMD.RS (Run/Stop bit) not cleared — xHCI still running while PM registers are written
- PORTSC.PP (port power) not cleared on all ports before PM enabling
- Incomplete PM enabling sequence — both must be cleared in order: PP=0, then RS=0
**Debug Steps:**
1. Check `USBCMD.RS` bit — must be 0 before clock requests can de-assert
2. Clear PORTSC.PP=0 for **all** ports (not just connected ports)
3. Clear USBCMD.RS=0 **after** all PP bits cleared
4. Verify clkreq de-asserted via P2SB/Rambo register read-back or SLE signal trace
5. Use VTDB/VCD waveform view to confirm signal de-assertion
> **Root cause pattern (from HSDES 1404376679, 1404302197):** PM scripts that clear PORTSC.PP but skip clearing USBCMD.RS leave the xHCI controller in run state. xHCI keeps asserting clock requests regardless of port state until the Run/Stop bit is also cleared.

### 6. LTSSM U1 Entry Failure — PHY phy_status Not Asserted
**Signature:** U1 LPM transition requested but LTSSM rolls back to Rx.Detect; PORTSC reads PLS=5 (Rx.Detect) immediately after U1 entry attempt; PORTSC value ~`0x611`
**Root Causes:**
- PHY does not assert `phystatus` after powerdown — xHCI waits for `phystatus` before completing U1 transition, times out, and rolls back LTSSM to Rx.Detect
- Back-to-back powerdown-to-powerdown without sufficient inter-sequence spacing (see HSDES 1509209950)
- IO voltage marginal — first occurrence often at 1.05V nominal, may disappear at 1.1V
**Debug Steps:**
1. Check PORTSC.PLS after U1 entry attempt — PLS=5 (Rx.Detect) confirms LTSSM rollback
2. Decode full PORTSC: `0x611` → CCS=1, PLS=5, PP=1, Speed=0 (link lost after U1 fail)
3. Try IO voltage margining (1.05V → 1.15V) to isolate PHY analog dependency
4. Check HSDES 1509209950 for back-to-back powerdown spacing workaround
5. Escalate to PHY team with ModPHY VISA capture if persistent on post-silicon

> **Root cause pattern (from HSDES 1404838956, 1509209950):** The most reliable indicator is PORTSC.PLS=5 immediately after a U1 entry attempt. Distinguish from normal Rx.Detect idle (no device) by CCS=1 in the same PORTSC read — if CCS=1 and PLS=5, the device was present but U1 transition failed.

---

## UAOL (USB Audio Offload) Failure Triage

> **See also:** `fv-usb/power` → *UAOL Isochronous Power Management* and *UAOL Power State Validation Checklist* for power constraints, LPM interaction, and the 8-step validation checklist. Load `fv-usb/platform` for per-platform ACE generation and FIFO timing data.

### When to Use This Section
- User reports USB audio recording or playback failure with UAOL enabled
- User sees audio stream "stuck" or "frozen" after a period of normal operation
- User reports audio glitches, gaps, or dropouts on USB headsets/microphones
- User asks about ACE (Audio Compute Engine) related USB failures
- UAOL works with one device but not another (device-specific behavior)

### UAOL Triage Decision Tree

```
UAOL Audio Failure Detected
        |
        +-- Does the failure occur with UAOL DISABLED?
        |   +-- YES --> Not a UAOL issue. Standard USB audio debug
        |   +-- NO  --> UAOL-specific issue. Continue below
        |
        +-- Recording or Playback?
        |   +-- Recording (IN endpoint) --> See "Recording Stuck" flow
        |   +-- Playback (OUT endpoint) --> See "Playback Failure" flow
        |   +-- Both --> Likely ACE-level or fabric-level issue
        |
        +-- Is the failure device-specific?
        |   +-- YES (fails with Device A, passes with Device B)
        |   |   +-- Compare USB descriptors (wMaxPacketSize, bInterval)
        |   |   +-- Compare device firmware versions (PID may differ)
        |   |   +-- Check if device sends NAK during isochronous IN
        |   |   +-- Test same device with UAOL disabled
        |   +-- NO (fails with all devices)
        |       +-- ACE FW issue, fabric issue, or xHCI offload bug
        |       +-- Check ACE FW version against BKC
        |       +-- Check IOSF fabric errors
        |
        +-- Is the failure time-dependent?
            +-- Fails after ~N seconds/minutes consistently
            |   +-- Feedback FIFO exhaustion (ACE3: ~1ms buffer)
            |   +-- pNDE scheduling drift
            |   +-- Device-side buffer underrun/overrun
            +-- Random / intermittent
                +-- Fabric contention (VCusb channel)
                +-- LTR/power state interaction
                +-- Hub scheduling conflict
```

### Recording Stuck — Detailed Flow

This is the most common UAOL failure pattern, observed in PTL/ACE3 sightings.

```
Recording Stuck (audio stops after N seconds/minutes)
        |
        +-- Step 1: Collect xHCI trace + USB bus analyzer trace
        |   NOTE: xHCI trace has NO visibility when traffic is
        |   offloaded to ACE. EP purge in xHCI trace is EXPECTED
        |   UAOL behavior (not an error).
        |
        +-- Step 2: Look for gap in isochronous IN data
        |   +-- Gap found (e.g., ~3ms silence in recording)
        |   |   +-- Does the device RECOVER after the gap?
        |   |   |   +-- YES --> Device is tolerant. Gap is benign
        |   |   |   |   (Astro40-Old pattern: gaps every ~28s, recovers)
        |   |   |   +-- NO  --> Device stops sending IN data entirely
        |   |   |       +-- This is the critical failure mode
        |   |   |       +-- Device FW entered error state on missed poll
        |   |   |       +-- ACE did not poll within service interval
        |   |   |       +-- Root cause: ACE3 Feedback FIFO too small?
        |   |   |       +-- Check: Related NVL sighting for FIFO sizing
        |   |   +-- No gap found --> Check for data corruption instead
        |   |       +-- Verify audio sample integrity
        |   |       +-- Check for repeated/dropped frames
        |
        +-- Step 3: Determine WHY the gap occurred
        |   +-- pNDE scheduling miss (ACE did not issue IN on time)
        |   +-- Fabric congestion on VCusb/TCusb channel
        |   +-- Hub downstream scheduling delay (if behind hub)
        |   +-- Power state transition interrupted isochronous flow
        |
        +-- Step 4: Determine WHY device did not recover
            +-- Device FW behavior on missed isochronous service interval
            +-- ACE has NO hardware recovery for missed intervals
            +-- ACE has NO hardware endpoint purge/timeout
            +-- SW stack must detect and recover (but may not)
            +-- Compare device FW versions (different PID = different FW)
```

### UAOL Failure Signatures & Root Causes

#### 1. Recording Stuck After ~N Minutes (Device-Specific)
**Signature:** Audio recording works for 30s-3min then stops. Stream appears active but no new data. Specific to certain USB headset models/FW versions.
**Root Causes:**
- Device firmware enters error state on missed isochronous poll
- ACE3 Feedback FIFO (~1ms) too small to absorb scheduling jitter
- Device does not tolerate gaps in isochronous IN polling
**Key Differentiator:** Same device with UAOL disabled works fine. Different FW version of same device may pass.
**Debug Steps:**
1. Confirm UAOL-specific: disable UAOL via registry, verify pass
2. Collect USB bus analyzer trace — look for gap in IN transactions
3. Compare USB descriptors between passing and failing device (focus on PID, wMaxPacketSize, bInterval)
4. Check if device FW is updatable
5. Test with UAOL on NVL/ACE4 (larger 4.5MB L2 FIFO) if available
**Reference Sighting:** 16029865294 (PTL Astro40 recording stuck)

#### 2. Periodic Gaps in Isochronous Stream (Benign or Fatal)
**Signature:** ~3ms gaps appear periodically (e.g., every 28 seconds) in isochronous IN data.
**Key Insight:** The gap itself may NOT be the root cause. What matters is whether the device recovers:
- **Tolerant device:** Resumes sending data after gap (benign)
- **Intolerant device:** Stops sending data entirely after gap (fatal)
**Root Causes for gap:**
- pNDE scheduling jitter in ACE
- IOSF fabric VCusb contention
- Hub-level downstream scheduling delay
**Debug Steps:**
1. Measure gap duration and periodicity
2. Test same conditions with a known-tolerant device
3. If gap is periodic, correlate with system events (PM transitions, other USB traffic)
4. Check if gap correlates with Feedback FIFO drain

#### 3. UAOL Playback Glitches / Dropouts
**Signature:** Audio playback has audible pops, clicks, or brief silences.
**Root Causes:**
- ACE OUT scheduling late (missed service interval)
- Feedback FIFO underrun on playback path
- Adaptive rate feedback not processed in time
**Debug Steps:**
1. Check playback endpoint type (adaptive vs synchronous vs asynchronous)
2. Monitor ACE feedback endpoint for rate adjustment messages
3. Check IOSF fabric utilization during playback
4. Compare with non-offloaded playback (UAOL disabled)

#### 4. UAOL Behind Hub Failure
**Signature:** UAOL works for direct-connected devices but fails behind USB hub.
**Historical Context:** MTL had a known post-silicon bug for UAOL behind hubs. Fixed in USB Standalone from PTL onwards.
**Root Causes:**
- Hub adds scheduling latency to isochronous transfers
- Hub split-transaction timing may exceed ACE service interval budget
- Residual MTL-era bug if on older platform
**Debug Steps:**
1. Verify platform: PTL+ should support UAOL behind hub
2. Test same device directly connected (bypass hub)
3. Check hub type (USB 2.0 vs 3.0) — different split transaction behavior
4. Check for MTL-era BIOS/FW carrying unfixed hub UAOL code

#### 5. EP Purge in xHCI Trace (Expected Behavior — NOT a Bug)
**Signature:** xHCI trace shows endpoint purge (EP purge) for UAOL endpoint. User suspects this is the failure.
**Reality:** EP purge in xHCI trace is **normal UAOL behavior**. This is the standard handoff mechanism between xHCI and ACE.

**What happens during EP purge:**
1. xHCI detects that an isochronous endpoint has been assigned to ACE for offload
2. xHCI issues a **Configure Endpoint** command with the Purge flag set
3. This clears any pending Transfer Request Blocks (TRBs) from the xHCI transfer ring for that endpoint
4. The xHCI transfer ring for that endpoint becomes **inactive** — all future traffic bypasses xHCI entirely
5. Traffic now flows directly: **USB Device → xHCI PHY → IOSF Fabric (VCusb ch2) → ACE → Audio Driver**
6. In the xHCI event ring, you will see `Configure Endpoint Complete` with purge indicator

**What this means for traces:**
- xHCI trace shows EP purge as the **last event** for the offloaded endpoint — this is correct
- After EP purge, **no further traffic** for that endpoint appears in xHCI traces
- To see actual audio data flow, you MUST use a **USB bus/protocol analyzer** (LeCroy, Beagle, Ellisys)
- The reverse (ACE → xHCI handback) occurs when UAOL is disabled or stream stops

**Debug Steps:**
1. Confirm EP purge corresponds to UAOL offload start (not an error condition)
2. Redirect investigation to USB bus analyzer trace (captures wire traffic regardless of offload)
3. Check ACE-level logging if available (ACE FW trace logs)
4. If EP purge occurs unexpectedly (no UAOL active), this IS abnormal — file HSDES sighting

### UAOL Debug Data Collection Checklist

When triaging any UAOL failure, collect ALL of the following before analysis:

```
[ ] 1. UAOL enabled/disabled comparison
      - Run test with UAOL enabled  → record result
      - Run test with UAOL disabled → record result (MUST do this first)

[ ] 2. USB device descriptors
      - Device Descriptor (VID, PID, bcdDevice — FW version indicator)
      - Configuration Descriptor
      - Interface Descriptor (audio class, subclass)
      - Endpoint Descriptors (wMaxPacketSize, bInterval for isoch EPs)
      - AudioControl/AudioStreaming descriptors

[ ] 3. USB bus analyzer trace
      - Captures actual wire traffic regardless of xHCI/ACE offload
      - Record for full failure duration (pre-failure + failure point)
      - Look for: gap in IN data, NAK from device, missed polls

[ ] 4. xHCI trace (limited visibility for UAOL)
      - NOTE: xHCI has NO visibility when offloaded to ACE
      - Useful for: offload handoff, EP purge, non-offloaded phases
      - DO NOT rely solely on xHCI trace for UAOL debug

[ ] 5. Platform configuration
      - ACE FW version (ACE3 for PTL, ACE4 for NVL)
      - BIOS/IFWI version (check against BKC)
      - UAOL registry settings
      - xHCI driver version
      - USB audio class driver version

[ ] 6. System event correlation
      - Windows Event Log (System + Application)
      - USB audio device event log
      - Power state transitions during test
      - Other USB traffic on same controller

[ ] 7. Device FW comparison (if device-specific failure)
      - Compare PID between passing and failing device
      - Different PID = different device firmware
      - Check if vendor provides FW update
      - Test with known-good device as baseline
```

### ACE3 vs ACE4 Debug Considerations

| Aspect | ACE3 (PTL) | ACE4 (NVL) |
|--------|-----------|-----------|
| Feedback FIFO | ~1ms per stream | Up to 10ms (4.5MB L2 cache) |
| Jitter tolerance | Lower — less buffer to absorb scheduling jitter | Higher — larger FIFO absorbs more jitter |
| UAOL behind hub | Supported (fixed from MTL) | Supported |
| Isochronous recovery | No HW recovery for missed intervals | No HW recovery for missed intervals |
| Endpoint purge | No HW endpoint purge/timeout — relies on SW | No HW endpoint purge/timeout — relies on SW |
| FIFO sizing sighting | Investigate if ACE3 affected | 18043001729 (NVL FIFO adjustment) |

> **CRITICAL**: When debugging UAOL on ACE3/PTL, always check whether a known ACE4/NVL
> FIFO-related fix also applies to ACE3. The smaller ACE3 FIFO makes it MORE susceptible
> to the same class of issues.

---

## Cross-Domain Delegation

| Scenario                              | Delegate To            |
|---------------------------------------|------------------------|
| General failure triage, wiki BKMs     | **FV_Debugger_V1**     |
| Platform power management blocker     | **FV-PM-SOUTH**        |
| BIOS boot USB enumeration issue       | **UART-MONITOR**       |
| Hardware-level debug (SPI, power)     | **TTK3**               |
| NGA test failure analysis             | **FV_Debugger_V1**     |
| HSDES sighting search                 | **sighting-info** skill|
| UAOL fabric/IOSF issues              | **FV_Debugger_V1**     |
| ACE FW version / BKC check           | **onebkc** skill       |

## Co-Design Lookup for Debug
Use the Playwright browser workflow to query Co-Design HAS for debug data:
1. `playwright_browser_navigate` to `https://chat.co-design.intel.com/chat`
2. `playwright_browser_snapshot` to locate the chat textarea
3. `playwright_browser_type` your query, then `playwright_browser_wait_for` the response
4. `playwright_browser_snapshot` to read the answer

> **Fallback:** If the browser is unavailable, load the `codesign` skill for REST API access.

**Domain-specific queries:**
- *"What are known xHCI errata for [platform]?"*
- *"What is the debug capability register offset for USB on [platform]?"*
- *"Show USB-related BIOS knobs for [platform]"*
- *"What is the ACE3 Feedback FIFO size for UAOL on [platform]?"*
- *"How does pNDE scheduling work for USB isochronous on [platform]?"*
- *"What is the UAOL offload handoff sequence between xHCI and ACE on [platform]?"*
