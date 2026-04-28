---
name: fv-audio/jack-detect
description: "Jack detection validation — HDA Realtek pin sense, SoundWire slave alerts, UAOL USB hot plug across Intel Client SoC audio subsystems"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# Jack Detection Validation

Validate jack detection (plug/unplug event handling) across three audio subsystems: HDA codec pin sense, SoundWire slave alert mechanism, and UAOL USB audio device hot plug.

> **Scope:** Jack insert/remove detection for headphones, microphones, and USB audio devices. Covers HDA pin sense (Realtek), SoundWire slave alerts, and UAOL hot plug. **Does NOT cover** Display Audio HPD (hot plug detect for HDMI/DP) — see `fv-audio/display-audio` for iDisp HPD.

---

## Multi-Platform Jack Detection Support

| Platform | ACE | HDA Pin Sense | SoundWire Alert | UAOL Hot Plug | Common Codec(s) |
|----------|-----|:------------:|:--------------:|:------------:|----------------|
| **NVL PCD-H** | 4.x | ✅ | ✅ | ✅ | ALC256/ALC298/ALC711/ALC712-VB |
| **NVL PCD-S** | 4.x | ✅ | ✅ | ✅ | ALC256/ALC298/ALC711 |
| **PTL** | 3.0 | ✅ | ✅ | ✅ | ALC256/ALC298/ALC711 ¹ |
| **WCL** | 3.0 | ✅ | ✅ | ✅ ¹ | Consult HAS ¹ |
| **LNL** | 2.x | ✅ | ✅ | ❌ (no UAOL) | ALC256/ALC298 ¹ |
| **MTL** | 1.5 | ✅ | ✅ | ❌ (no UAOL) | ALC256/ALC298 ¹ |
| **ARL** | 1.5 | ✅ | ✅ | ❌ (no UAOL) | ALC256/ALC298 ¹ |
| **TTL** | 3.0/4.0 | ✅ | ✅ | Consult HAS ¹ | Consult HAS ¹ |
| **RZL** | 4.0 | ✅ | ✅ | ✅ ¹ | NVL codecs expected ¹ |

> ¹ **HAS verification required** — Codec population and UAOL availability vary by platform and board design (CRB vs OEM). Verify against the platform BOM/schematic.

### Platform-Specific Notes

- **LNL / MTL / ARL**: No UAOL engine — USB audio jack detection uses standard xHCI path only, no offload
- **NVL PCD-S**: Fewer SoundWire segments than PCD-H — AIOC (ALC712-VB) may not be present on all PCD-S boards
- **PTL**: SoundWire jack detect timing may differ from NVL due to ACE 3.0 vs 4.x alert processing pipeline
- **Cross-codec consistency**: When switching between HDA Realtek and SoundWire Realtek codecs on the same board, jack event delivery latency may differ (HDA = immediate via unsolicited response; SoundWire = bus-level alert polling)

---

## Jack Detection Architecture Overview

NVL supports jack detection through three independent mechanisms, each tied to a different audio subsystem:

| Subsystem | Mechanism | Trigger | Codec/Device | Response Time |
|-----------|-----------|---------|--------------|---------------|
| **HDA** | Pin Sense (verb 0xF09) | Physical jack insert/remove | Realtek ALC256/ALC298/ALC700 | Immediate (interrupt-driven) |
| **SoundWire** | Slave Alert | Peripheral-initiated alert | ALC711/ALC722/ALC712-VB | Bus-level alert → host read |
| **UAOL** | USB Hot Plug | USB device connect/disconnect | USB headset/speaker | xHCI port status change |

### Detection Flow (All Subsystems)

```
Physical Event (jack insert/remove or USB plug)
    │
    ├─── HDA Path ──────────► Pin Sense Change → Unsolicited Response → OS Notification
    │                          (codec interrupt → RIRB → driver → endpoint add/remove)
    │
    ├─── SoundWire Path ────► Slave Alert → Master reads status → OS Notification
    │                          (INTSTAT → driver reads AlertStatus → endpoint add/remove)
    │
    └─── UAOL Path ─────────► USB Port Status Change → xHCI Event → ACE Notification
                               (PORTSC.CCS → xHCI event ring → UAOL engine → endpoint)
```

---

## 1. HDA Jack Detection (Realtek Pin Sense)

### How It Works

HDA codecs detect physical jack insertion via an impedance-sensing circuit on output/input pin widgets. When a plug is inserted or removed, the codec generates an **unsolicited response** to notify the host.

### Key Verb: Get Pin Sense (0xF09)

| Bit | Field | Description |
|-----|-------|-------------|
| [31] | Presence Detect | `1` = jack inserted, `0` = jack removed |
| [30:0] | Impedance Value | Raw impedance measurement (codec-specific) |

### Impedance Thresholds for Jack Type Classification

Realtek codecs use impedance sensing on the headphone jack to distinguish between device types. The impedance value from verb 0xF09 bits [30:0] determines the jack type:

| Impedance Range (ohms) | Jack Type | Detection | Notes |
|------------------------|-----------|-----------|-------|
| **0 - 10** | Short / error | No device | May indicate damaged jack or sensing circuit error |
| **10 - 70** | Headset (TRRS) | Microphone present | 4-pole TRRS plug — headphone + mic. Typical: 32Ω headphone + mic ring detected |
| **70 - 1000** | Headphone (TRS) | No microphone | 3-pole TRS plug — headphone only. Impedance varies by headphone driver (16-600Ω) |
| **> 1000** | Line out / high-Z | Special device | Line-level output or high-impedance device. May require manual endpoint selection |
| **No response (0x7FFFFFFF)** | No jack / open circuit | Nothing inserted | Jack empty or sensing disabled |

> **⚠️ CODEC-SPECIFIC**: These thresholds are **approximate values for Realtek ALC256/ALC298/ALC700 series**. Actual threshold boundaries are programmed in the codec's internal registers and may differ between codec models, board layouts, and jack connector types. The key distinction is between headset (TRRS with mic ring ~32Ω) and headphone (TRS, no mic ring, higher impedance). Consult the codec datasheet for exact threshold programming.

> **Impedance Sensing Calibration**: Some Realtek codecs require impedance calibration during manufacturing or first boot. If jack type misidentification occurs consistently (e.g., headset always detected as headphone), check:
> 1. Codec calibration data in EEPROM / OTP
> 2. Board-level jack connector spec (TRRS pin order: CTIA vs OMTP)
> 3. Codec-specific threshold register values (vendor-specific verbs)

### Realtek Pin Sense Configuration

Realtek codecs (ALC256, ALC298, ALC700) on NVL use the following pin widget nodes for jack detection:

| Pin Widget | Typical Function | Jack Type | Detection |
|------------|-----------------|-----------|-----------|
| Node 0x12 | Internal Mic (DMIC fallback) | N/A (always present) | No jack sense |
| Node 0x14 | Speaker Out | N/A (always present) | No jack sense |
| Node 0x18 | Mic In (rear) | 3.5mm TRS | Pin sense enabled |
| Node 0x19 | Mic In (front) | 3.5mm TRS | Pin sense enabled |
| Node 0x1A | Line In | 3.5mm TRS | Pin sense enabled |
| Node 0x1B | Line Out (rear) | 3.5mm TRS | Pin sense enabled |
| Node 0x21 | Headphone Out | 3.5mm TRRS (combo) | Pin sense enabled |

> **Note:** Actual node assignments are codec-specific and configured via Pin Configuration Defaults (verb 0xF1C). The table above shows common Realtek assignments — always verify against the specific codec datasheet.

### PythonSV: Read Pin Sense

```python
# Read jack detection status via HDA verb
# Codec address 0 (external Realtek), Node 0x21 (headphone out)
# Verb 0xF09 = Get Pin Sense

# Build verb word: [31:28]=CAddr, [27:20]=NID, [19:0]=Verb
codec_addr = 0
node_id = 0x21  # Headphone out (common Realtek assignment)
verb = (codec_addr << 28) | (node_id << 20) | 0xF0900

# Send via CORB (requires DMA setup by driver)
# Or use immediate command interface if available:
# Response bit[31] = 1 means jack inserted
print("Pin Sense verb for HP out: 0x%08X" % verb)
print("Check response bit[31]: 1=inserted, 0=removed")
```

### Unsolicited Response for Jack Events

HDA codecs send unsolicited responses when jack state changes:

```python
# Enable unsolicited response on headphone pin (Node 0x21)
# Verb: Set Unsolicited Response (0x708)
# Payload: bit[7]=Enable, bits[5:0]=Tag

enable_unsol = (codec_addr << 28) | (node_id << 20) | 0x70880
# Tag = 0x00 (default), Enable = 1 (bit 7)
print("Enable unsolicited response: 0x%08X" % enable_unsol)

# When jack state changes, codec sends unsolicited response via RIRB:
# Response format: [31:26]=Tag, [25:0]=Subtag (codec-specific)
# The driver reads RIRB and dispatches jack event to OS
```

### HDA Jack Detect Verification Procedure

1. **Read Pin Config Defaults** — Send verb `0xF1C` to each pin widget to identify which pins have jack sense capability (check Pin Capabilities bit for Presence Detect)
2. **Check Pin Sense** — Send verb `0xF09` to each jack-capable pin, read bit[31] for current state
3. **Enable Unsolicited Response** — Send verb `0x708` with Enable=1 to each pin for event-driven detection
4. **Verify RIRB delivery** — Insert/remove jack, check RIRB for unsolicited response entries
5. **Check OS endpoint** — Verify audio endpoint appears/disappears in OS device list

---

## 2. SoundWire Jack Detection (Slave Alerts)

### How It Works

SoundWire peripherals (codecs) use the **Slave Alert** mechanism to notify the master (ACE) of jack events. When a jack is inserted or removed, the peripheral sets an alert bit and the master reads the alert status register to determine the event type.

### SoundWire Alert Flow

```
Jack Event on Peripheral
    │
    ▼
Peripheral sets IntStat register (Slave-level interrupt status)
    │
    ▼
Peripheral asserts Slave Alert on SoundWire bus (in-band signaling)
    │
    ▼
Master detects alert → reads INTSTAT (Master-level) → identifies alerting device
    │
    ▼
Master reads peripheral's SCP_IntStat1/IntStat2 registers → gets event type
    │
    ▼
Driver processes jack event → OS endpoint add/remove
```

### Key SoundWire Registers for Jack Detection

**Master-side (SHIM/Host):**

| Register | Description |
|----------|-------------|
| INTSTAT | Master interrupt status — bit per device indicating alert pending |
| INTMASK | Master interrupt mask — enable/disable alerts per device |

**Peripheral-side (SCP — SoundWire Configuration Port):**

| Register | Address | Description |
|----------|---------|-------------|
| SCP_IntStat1 | 0x0064 | Interrupt status — bit[0]=BUS_CLASH, bit[1]=PARITY, bit[2]=IMPL_DEF (jack event) |
| SCP_IntStat2 | 0x0068 | Extended interrupt status (implementation-defined) |
| SCP_IntMask1 | 0x006C | Interrupt mask for IntStat1 |
| SCP_IntClear1 | 0x0070 | Write-1-to-clear for IntStat1 |

### Realtek SoundWire Jack Detection

Realtek SoundWire codecs (ALC711, ALC722, ALC712-VB) use the **IMPL_DEF** (Implementation Defined) bit in SCP_IntStat1 to signal jack events:

| Codec | Jack Detection Method | Alert Bit |
|-------|----------------------|-----------|
| ALC711 | Impedance sensing + slave alert | SCP_IntStat1 bit[2] (IMPL_DEF) |
| ALC722 | Impedance sensing + slave alert | SCP_IntStat1 bit[2] (IMPL_DEF) |
| ALC712-VB (AIOC) | Impedance sensing + slave alert | SCP_IntStat1 bit[2] (IMPL_DEF) |

### SoundWire Jack Detect Verification Procedure

1. **Check INTMASK** — Verify alerts are unmasked for the target device number on the master
2. **Read INTSTAT** — Check if any device has a pending alert
3. **Read SCP_IntStat1** — For the alerting device, check bit[2] for IMPL_DEF (jack event)
4. **Read codec-specific status** — Realtek codecs may have vendor-specific registers for detailed jack status (plug type: headphone, headset, line-in)
5. **Clear alert** — Write 1 to SCP_IntClear1 bit[2] to acknowledge
6. **Verify OS endpoint** — Confirm audio endpoint appears/disappears after jack event

---

## 3. UAOL Jack Detection (USB Hot Plug)

### How It Works

USB audio device hot plug is detected by the **xHCI host controller** via port status change events. When a USB audio device (headset, speaker, microphone) is connected or disconnected, xHCI generates a Port Status Change Event, which the UAOL engine in ACE processes to set up or tear down the offloaded audio stream.

### USB Hot Plug Detection Flow

```
USB Device Plug/Unplug
    │
    ▼
xHCI PORTSC.CCS (Current Connect Status) changes
    │
    ▼
xHCI generates Port Status Change Event on Event Ring
    │
    ▼
xHCI driver processes event → device enumeration (if connect)
    │
    ▼
USB Audio Class driver identifies audio endpoints
    │
    ▼
UAOL engine in ACE notified → offload setup (if UAOL capable)
    │
    ▼
Audio endpoint appears in OS
```

### Key xHCI Registers for Hot Plug

| Register | Description |
|----------|-------------|
| PORTSC.CCS | Current Connect Status — `1` = device connected |
| PORTSC.CSC | Connect Status Change — `1` = change detected (write-1-to-clear) |
| PORTSC.PED | Port Enabled/Disabled — `1` = port enabled after successful link training |
| PORTSC.PLS | Port Link State — current USB link state (U0=active, U3=suspended) |

### UAOL-Specific Hot Plug Considerations

| Consideration | Details |
|--------------|---------|
| **Behind-hub support** | NVL ACE4 supports devices behind USB hubs. Hub port status change propagates through hub driver. |
| **UAOL stream teardown** | On USB device disconnect, UAOL engine must gracefully tear down the offloaded stream before xHCI releases the port |
| **Reconnect race** | Quick unplug-replug can cause UAOL state machine race if previous teardown isn't complete |
| **Power state** | xHCI and ACE must both be in D0 for UAOL hot plug to work. If either is in D3, hot plug is handled by standard USB path (no offload) |

### UAOL Hot Plug Verification Procedure

1. **Check PORTSC.CCS** — Verify USB audio device is physically connected
2. **Check PORTSC.PLS** — Verify port link state is U0 (active)
3. **Check UAOL offload status** — Verify ACE has accepted the offload for this device
4. **Disconnect device** — Verify UAOL stream teardown completes cleanly
5. **Reconnect device** — Verify UAOL offload re-establishes without error
6. **Check OS endpoint** — Confirm audio endpoint appears/disappears correctly

---

## Troubleshooting

| Symptom | Subsystem | Likely Cause | Debug Steps |
|---------|-----------|-------------|-------------|
| No jack event on headphone insert (HDA) | HDA | Unsolicited response not enabled or RIRB not serviced | Check verb 0x708 sent with Enable=1 on pin widget; verify RIRBCTL.DMA_RUN=1; check RIRBSTS for overflow |
| Pin Sense always reads 0 (HDA) | HDA | Pin widget lacks Presence Detect capability | Read Pin Capabilities (verb 0xF00, param 0x0C) — check PD bit; verify Pin Config Default (0xF1C) for correct port connectivity |
| Jack event not reaching OS (HDA) | HDA | Driver not processing unsolicited responses | Check RIRB for pending unsolicited entries; verify driver IRQ handler is active; check INTCTL.GIE and stream interrupt enables |
| No slave alert on jack insert (SoundWire) | SoundWire | Alert masked or peripheral not configured | Check master INTMASK for target device; verify SCP_IntMask1 bit[2] is unmasked on peripheral; check SoundWire link is active |
| Stale alert status (SoundWire) | SoundWire | Alert not cleared after previous event | Write 1 to SCP_IntClear1 to clear pending alerts; re-read SCP_IntStat1 |
| USB audio device not detected on plug | UAOL | xHCI port issue or device enumeration failure | Check PORTSC.CCS and PORTSC.CSC; verify xHCI is in D0; check USB cable and hub connectivity; see `fv-usb/config-checkout` |
| UAOL stream not re-established after replug | UAOL | Teardown/re-setup race condition | Check UAOL state machine status in ACE; verify previous stream fully torn down; add delay between unplug-replug; check ACE FIFO reset |
| Jack type misidentified (headphone vs headset) | HDA | Impedance sensing calibration issue | Read Pin Sense impedance value (bits[30:0]); compare against codec-specific thresholds for TRRS (headset) vs TRS (headphone) |
| Intermittent phantom jack events | HDA/SoundWire | Noisy impedance sensing or debounce too short | Check codec debounce configuration; verify no EMI on jack sense circuit; increase debounce timer if configurable |

---

## Important Safety Notes

- **Do NOT send jack detect verbs to wrong codec address** — wrong address can corrupt state on other codecs sharing the HDA link. Always verify codec address from STATESTS before sending verbs.
- **Do NOT disable unsolicited responses during active audio** — this will prevent jack removal detection, leaving a dangling audio endpoint when the user unplugs.
- **Do NOT clear SoundWire alerts without reading status first** — clearing without reading loses the event type information needed for correct jack type classification.
- **UAOL hot plug requires D0 on both xHCI and ACE** — if either is in D3/suspended, hot plug reverts to standard USB path without audio offload.

---

## PythonSV — Jack Detection Diagnostic

Comprehensive jack detection state dump across all three subsystems:

```python
def dump_jack_detect_state(soc):
    """Dump jack detection state across HDA, SoundWire, and UAOL subsystems."""
    import pysvtools.pciedut as pcie

    ace = pcie.get_dev(0, 31, 3)
    print("=" * 60)
    print("JACK DETECTION STATE DUMP")
    print("=" * 60)

    # 1. HDA Codec Presence — STATESTS shows which codecs are present
    statests = ace.bar0.read(0x0E, 2)
    print(f"\n[HDA] STATESTS = 0x{statests:04X}")
    for sdi in range(15):
        if (statests >> sdi) & 1:
            print(f"  SDI{sdi}: Codec PRESENT")

    # 2. HDA Interrupt State — INTSTS for pending jack events
    intsts = ace.bar0.read(0x24, 4)
    cis = (intsts >> 30) & 1
    print(f"\n[HDA] INTSTS = 0x{intsts:08X}  CIS={cis}")
    if cis:
        print("  Controller interrupt ACTIVE — may indicate pending jack event (unsolicited response)")

    # 3. Wake state
    wakeen = ace.bar0.read(0x0C, 2)
    wakests = ace.bar0.read(0x0E, 2)  # Note: shared with STATESTS on some HDA revs
    print(f"\n[HDA] WAKEEN = 0x{wakeen:04X}")

    # 4. RIRB check — unsolicited responses queue
    rirbsts = ace.bar0.read(0x5D, 1)
    rintcnt = ace.bar0.read(0x5A, 2)
    print(f"\n[HDA] RIRBSTS = 0x{rirbsts:02X}  RINTCNT = 0x{rintcnt:04X}")
    if rirbsts & 0x01:
        print("  RIRB Response Interrupt pending — unsolicited response may be queued")

    # 5. SoundWire link status (check for active alerts)
    try:
        # SoundWire SHIM registers in BAR4 — offsets are platform-specific
        # Read Master INTSTAT for slave alert bits
        print("\n[SoundWire] Check master INTSTAT for slave alerts via driver or BAR4 SHIM registers")
        print("  (Platform-specific: use driver WPP trace or PythonSV SoundWire SHIM read)")
    except Exception as e:
        print(f"\n[SoundWire] Read error: {e}")

    # 6. UAOL / xHCI presence check
    try:
        xhci = pcie.get_dev(0, 20, 0)  # Common xHCI BDF
        xhci_cmd = xhci.cfg.read(0x04, 2)
        print(f"\n[UAOL/xHCI] PCI CMD = 0x{xhci_cmd:04X}  (BME={bool(xhci_cmd & 4)})")
        # Check PORTSC for first few ports
        bar0 = xhci.cfg.read(0x10, 4) & 0xFFFFF000
        if bar0:
            # Read PORTSC for port 1 (offset depends on xHCI CAPLENGTH)
            print(f"  xHCI BAR0 = 0x{bar0:08X} — check PORTSC.CCS for USB audio device presence")
    except Exception:
        print("\n[UAOL/xHCI] xHCI not found at 0:20:0 — check platform BDF")

    print("\n" + "=" * 60)

# Usage:
# dump_jack_detect_state(soc)
```

---

## Cross-References

| Sibling Skill | Relevance to Jack Detection |
|---------------|---------------------------|
| `fv-audio/hda` | Full HDA verb reference, CORB/RIRB setup, pin widget programming |
| `fv-audio/soundwire` | SoundWire bus enumeration, SHIM registers, segment configuration |
| `fv-audio/uaol` | UAOL offload engine, FIFO timing, xHCI integration details |
| `fv-audio/aioc` | ALC712-VB jack detection via SoundWire slave alerts on Segment 2 |
| `fv-audio/config-checkout` | PCI enumeration, BAR verification, BIOS audio enable |
| `fv-audio/power` | D-state impact on jack detection — D3 disables jack sense |
| `fv-audio/display-audio` | Display Audio HPD (HDMI/DP hot plug) — **separate from jack detection** |
| `fv-usb/config-checkout` | USB port enumeration, xHCI PORTSC for UAOL hot plug debug |
