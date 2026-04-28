# FV-USB — Quick Reference Cheat Sheet

<!-- owner: kvejaya -->

> Last Updated: 2026-03-18
> Quick-reference for the most common USB validation commands, scripts, register lookups, and one-liners.

---

## Debug Bundle (Run First for Unknown Failures)

```bash
cd C:\validation\windows-test-content\usb\latest_stable_dynamic
python allchecker.py          > usb_debug_bundle.txt 2>&1
python treeview.py            >> usb_debug_bundle.txt 2>&1
python yellowbang_usb.py      >> usb_debug_bundle.txt 2>&1
python NDE_checker.py         >> usb_debug_bundle.txt 2>&1
```

---

## Core Scripts — Most Used Invocations

### Device Enumeration & Tree

```bash
# Show full USB device tree (topology, speed, VID/PID, driver)
python treeview.py

# Check specific port for enumerated device
python usb_helper_ipsv.py --check-device <port>

# Check device speed on port (returns 0-7)
python usb_helper_ipsv.py --get-speed <port>

# Detect yellow-bang (driver failure) in Device Manager
python yellowbang_usb.py

# Detect NDE (No Device Enumerated) — device connected but not seen by OS
python NDE_checker.py
```

### USB Helper API (Python)

```python
from usb_helper_ipsv import USBHelper
helper = USBHelper()

speed  = helper.get_speed(port)        # 0-7 (see speed map)
link   = helper.get_link_status(port)  # 0-15 (PLS value)
pstate = helper.get_power_state(device)# "D0" or "D3"
```

**Speed Map:** 0=Unknown, 1=FS(12M), 2=LS(1.5M), 3=HS(480M), 4=SS(5G), 5=SS+(10G), 6=SS+(20G)

**PLS Map (key values):** 0=U0, 1=U1, 2=U2, 3=U3, 4=Disabled, 5=Rx.Detect, 7=Polling, 10=Compliance, 15=Resume

### Test Execution

```bash
# Run Galaxy XML test suite
python run_galaxy.py --xml <suite.xml> --init-all --nga

# Common test_run.py tests
python test_run.py --test enumeration
python test_run.py --test bulktraffic
python test_run.py --test isochtraffic
python test_run.py --test hotplug
python test_run.py --test uaol_playback
python test_run.py --test uaol_recording
python test_run.py --test s3_connect
python test_run.py --test s3_disconnect
python test_run.py --test s4_connect
python test_run.py --test s4_disconnect
```

### Power Management

```bash
# LPM validation — check U1/U2 entry
python lpm.py --port <port_number> --check-u1
python lpm.py --port <port_number> --check-u2
python lpm.py --port <port_number> --check-u0   # verify U0 during UAOL stream

# LTR values for all USB devices
python LTR_checker.py

# Package C-state residency (USB LPM/LTR must be correct)
python pkgc_residency_checker.py

# S0ix / Modern Standby validation
python slp_s0.py
```

### CSwitch Port Control

```python
from cswitch_api import CSwitch
cs = CSwitch()
cs.connect_port(port_number)     # Physically connect USB port
cs.disconnect_port(port_number)  # Physically disconnect USB port
```

### TCSS / Type-C

```bash
python tcss_customs.py --port <port> --check-orientation
python tcss_customs.py --port <port> --check-speed
```

---

## PythonSV Register One-Liners

> **Prerequisites:** Host-target pairing must be done first. Load `pysv` skill for setup.
> **PTL:** Do NOT use f-strings — use `.format()` or `%` formatting.

```python
# Show full PORTSC for port 0
sv.socket0.uncore.usb.xhci.portsc[0].show()

# Read key PORTSC fields for port 0
pls   = sv.socket0.uncore.usb.xhci.portsc[0].pls     # Link State (0-15)
ccs   = sv.socket0.uncore.usb.xhci.portsc[0].ccs     # Connect Status
ped   = sv.socket0.uncore.usb.xhci.portsc[0].ped     # Port Enabled
speed = sv.socket0.uncore.usb.xhci.portsc[0].speed   # Speed (0-7)

# Show USBSTS (check HSE bit for Host System Error)
sv.socket0.uncore.usb.xhci.usbsts.show()

# Show USBCMD (check Run/Stop bit)
sv.socket0.uncore.usb.xhci.usbcmd.show()

# Show PORTPMSC (LPM control)
sv.socket0.uncore.usb.xhci.portpmsc[0].show()

# Show all port statuses in one loop
for i in range(sv.socket0.uncore.usb.xhci.hcsparams1.maxports):
    print("Port", i, ": PLS=", sv.socket0.uncore.usb.xhci.portsc[i].pls,
          "CCS=", sv.socket0.uncore.usb.xhci.portsc[i].ccs,
          "Speed=", sv.socket0.uncore.usb.xhci.portsc[i].speed)

# Read BAR0 from PCI config space (always verify before MMIO access)
bar0 = sv.read_config_dword(bdf, 0x10)
```

---

## PORTSC Bit-Field Quick Reference

| Bit(s) | Field | Key Values |
|--------|-------|------------|
| 0      | CCS   | 1=connected, 0=not connected |
| 1      | PED   | 1=port enabled |
| 4      | PR    | 1=port reset in progress |
| 8:5    | PLS   | 0=U0, 3=U3, 10=Compliance |
| 9      | PP    | 1=port powered |
| 13:10  | Speed | 4=SS 5G, 5=SS+ 10G, 3=HS 480M |
| 17     | CSC   | 1=connect status changed (RW1C) |
| 22     | PLC   | 1=link state changed (RW1C) |
| 25     | WCE   | 1=wake on connect enabled |
| 26     | WDE   | 1=wake on disconnect enabled |
| 31     | WPR   | Write 1 to issue warm port reset |

### PORTSC Hex Decode Examples (from HSDES sightings)

| Raw Value | Decode | Meaning |
|-----------|--------|---------|
| `0x12B1`  | CCS=1, PED=0, PLS=10(Compliance), PP=1, Speed=4(SS) | Link in Compliance Mode — SI/cable issue |
| `0x0611`  | CCS=1, PED=0, PLS=5(Rx.Detect), PP=1, Speed=0 | U1 entry fail / link fell back to Rx.Detect (phy_status issue, see known_issues.md) |
| `0x00A3`  | CCS=1, PED=1, PLS=0(U0), PP=1, Speed=4(SS) | Normal SS operating state |
| `0x00A0`  | CCS=0, PED=0, PLS=5(Rx.Detect), PP=1, Speed=0 | No device, waiting for connect |
| `0x1400`  | CCS=0, PED=0, PLS=7(Polling), PP=1, Speed=0 | Link training in progress |

> Decode: `PLS = (PORTSC >> 5) & 0xF`, `Speed = (PORTSC >> 10) & 0xF`, `CCS = bit 0`, `PED = bit 1`, `PP = bit 9`

---

## ModPHY Register Access (PythonSV — Pre-Silicon / PHY Debug)

> **Use when:** PHY-level link training fails, Ux transition hangs, or SI characterization is needed.
> **Note:** Pre-silicon/FPGA methodology; not available on post-silicon production platforms.

```python
# Access ModPHY registers for USB3 lane
lane = 0  # Lane index

# Show underflow/overflow sticky registers (debug Ux transitions)
ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword17.show
# Fields: reg_rxg3eb_underflow_sticky[09:09], reg_rxg3eb_overflow_sticky[10:10]

# Override PI quad sensitivity (reduces U0 instability from PI bouncing)
ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.pcs_dword14.reg_bonuxcode_ovrd_en = 0x1

# Check DFE Data Summer CM calibration (should match ~0x23; if 0x9 → mismatch)
# Register: datasumcmcal0_7_0
ulk.modphy.readregister("dlane%d" % lane).pcs_usb3p1.datasumcmcal0.show

# Check LTSSM state (via port base address register read)
# ltssm_state[5:0]: 0=RxDetect, 5=Polling, 8=U0, 0xA=Recovery, 0x13=Inactive
portbase = 0x80540000  # platform-specific
ltssm = sv.mem_read(portbase, 4) & 0x3F
print("LTSSM state:", hex(ltssm))
```

---

## PM Clock Request Debug (USBCMD.RS)

> If `USB3_PRIM_CLKREQ` or `ux_ibbs_prim_clkreq` stays asserted after PORTSC.PP=0,
> the Run/Stop bit was not cleared. Both must be cleared for clkreq to de-assert.

```python
# Step 1: Clear port power (PORTSC.PP = 0) for all ports
# Step 2: Clear Run/Stop bit — this is the commonly missed step
sv.socket0.uncore.usb.xhci.usbcmd.rs = 0

# Verify clkreq de-asserted (use VISA/signal trace or P2SB read-back)
sv.socket0.uncore.usb.xhci.usbcmd.show()  # Confirm RS=0

# See Playbook 6 in debug_playbooks.md for full procedure
```

---

## HCIVERSION Check (New Platform Bringup)

```python
# Verify xHCI version — must be 0x0110 (xHCI 1.1) to enable SSP/Gen2
sv.socket0.uncore.usb.xhci.hciversion.show()
# Expected: 0x0110
# If 0x0100: SSP/Gen2 support silently disabled in OS driver — file RTL sighting
# See known_issues.md HSDES 1304166922
```

---

## PLS Values Quick Reference

| Value | State | Notes |
|-------|-------|-------|
| 0  | U0 — Active | Normal operating state |
| 1  | U1 — Standby | Hardware LPM, ~1µs exit |
| 2  | U2 — Sleep | Hardware LPM, ~2ms exit |
| 3  | U3 — Suspend | SW suspend, ~10ms+ exit |
| 4  | Disabled | Port disabled |
| 5  | Rx.Detect | Waiting for device connect |
| 7  | Polling | Link training in progress |
| 8  | Recovery | Link recovering from error |
| 10 | **Compliance** | **SI issue — see known_issues.md** |
| 11 | Test Mode | USB2 test mode |
| 15 | Resume | Resume signaling in progress |

---

## NGA Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | PASS | — |
| 1 | FAIL | Load `fv-usb/debug`, run triage flowchart |
| 12 | Device not found | Load `fv-usb/enumeration`, check PORTSC.CCS |
| 13 | Config error | Check BDF, script params, Galaxy XML config |

---

## Co-Design Query One-Liners

Navigate to `https://chat.co-design.intel.com/chat` then ask:

```
"Show PORTSC register bit-fields from NVL_USB_HAS"
"What is the xHCI DID for NVL USB controller?"
"What are known xHCI errata for PTL?"
"What are the UAOL power constraints for NVL?"
"Show USB BIOS knobs for LNL"
"What is ACE3 Feedback FIFO size on PTL?"
"How does pNDE scheduling work on NVL?"
"What is the BAR0 address for xHCI on PTL?"
```

---

## UAOL Quick Checks

> **Full UAOL references:** `fv-usb/power` → UAOL power constraints & validation checklist | `fv-usb/debug` → UAOL failure triage decision tree | `fv-usb/platform` → per-platform ACE/FIFO data

```bash
# Disable UAOL via registry (for comparison test)
# HKLM\SYSTEM\CurrentControlSet\Services\usbxhci\Parameters
# Set UaolEnabled = 0, reboot

# Check ACE FW version against BKC
# Use: onebkc skill

# Verify U0 maintained during audio stream
python lpm.py --port <audio_port> --check-u0

# Verify D0 maintained during UAOL
python usb_helper_ipsv.py --power-state

# Check Feedback FIFO (ACE3=~1ms, ACE4=up to 10ms)
# Query Co-Design: "ACE3 Feedback FIFO size PTL"
```

---

## Test Naming Convention

`USB_<CATEGORY>_<PLATFORM>_<ID>`

Examples: `USB_UAOL_PTL_001`, `USB_ENUM_NVL_042`, `USB_PM_S3_LNL_007`

Categories: `ENUM`, `BULK`, `ISOCH`, `HOTPLUG`, `PM`, `UAOL`, `S3`, `S4`, `LPM`

---

## Platform Quick Reference

| Platform | USB Engine | UAOL Engine | Multi-Die? | UAOL Behind Hub |
|----------|-----------|-------------|------------|-----------------|
| NVL      | xHCI      | ACE4 (10ms FIFO) | Yes (PCH-H / PCH-S) | Yes |
| PTL      | xHCI      | ACE3 (~1ms FIFO) | No | Yes |
| LNL      | xHCI      | —           | No (integrated SoC) | TBD |
| MTL      | xHCI      | ACE (gen?)  | No | **No (RTL bug)** |
| ARL      | xHCI      | —           | No | TBD |
