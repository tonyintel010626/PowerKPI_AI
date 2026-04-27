# FV-AUDIO Agent Triage & Debug Workflows

> **Platform**: Intel Client SoC (NVL/PTL/MTL/LNL/ARL) — Windows only  
> **Last Updated**: 2026-04-01  
> **Owner**: huiyingt  
> **Version**: rev2.0

This document captures the canonical step-by-step agent workflows for the seven most common audio validation failure scenarios. Each workflow maps directly to the FV-AUDIO decision trees and sub-skill delegations.

---

## Workflow 1: HDA Codec Not Detected (Missing CORB/RIRB Activity)

**Symptom**: `verb_read(codec_addr, nid, verb)` returns 0xFF or raises timeout; Device Manager shows no HDA codec node; NGA test fails at codec enumeration step.

**Sub-skill**: `fv-audio/hda`

### Step 1 — Verify ACE PCI Enumeration
```python
# Check ACE BAR0 is non-zero (PCI device present)
soc.pcie.ace.config.bar0  # expect != 0
soc.pcie.ace.config.command  # bit1 (MSE) must be set
```
If BAR0 = 0 → escalate to `fv-audio/config-checkout`. HDA cannot proceed without ACE enumeration.

### Step 2 — Check HDA Link Clock
```python
# ACE Global Control Register — CRST bit must be 1 (out of reset)
ace_gcr = mem(BAR0 + 0x008, 4)
print(f"CRST={ace_gcr & 1}")  # 0 = HDA controller in reset
```
If CRST=0: write `1` to CRST bit, wait 1ms, re-read. Persistent 0 → hardware/clock issue.

### Step 3 — Read STATESTS Register
```python
# STATESTS shows which codec addresses responded on reset
statests = mem(BAR0 + 0x00E, 2)
print(f"STATESTS=0x{statests:04X}")  # bit N set = codec at address N responded
```
- All zeros: no codec responded → check physical connection / codec power
- Bit 0 set but verb fails: codec present but not responding → check BIOS codec enumeration knob

### Step 4 — Attempt Manual Verb
```python
# Write verb via CORB (simplified — use driver API in practice)
# NID 0 = root node, Verb 0xF00 = GET_PARAM, Param 0x00 = Vendor/Device ID
# Expected: Intel HDA codec VID/DID
```

### Step 5 — Check BIOS Knob
Ensure `HdAudioEnable=1` in BIOS setup. If disabled, ACE HDA link is clock-gated and no verb traffic is possible.

### Decision Tree
```
STATESTS = 0 → check ACE CRST → check codec power rail (TTK3-I2C VR read) → hardware triage
STATESTS != 0, verb fails → CORB/RIRB parity issue → check ACE interrupt status
STATESTS != 0, verb ok, driver missing → Windows driver load issue → Workflow 7 (driver)
```

---

## Workflow 2: DSP Firmware Load Failure / IPC Timeout

**Symptom**: `IntcAudioBus` or `IntelSmartSound` driver fails to load FW; Device Manager shows Code 10 or Code 43; NGA DSP tests time out at IPC handshake.

**Sub-skill**: `fv-audio/dsp`

### Step 1 — Confirm DSP ROM Boot
```
# WPP trace — IntelSmartSound provider
# Look for: "DSP ROM boot complete" or "ROM_STATUS=0x1"
# If absent: DSP did not come out of reset
```
Collect ETL trace:
```cmd
logman start audio_dsp -p {INTC_AUDIO_BUS_WPP_GUID} -o C:\logs\audio_dsp.etl -ets
<reproduce failure>
logman stop audio_dsp -ets
```

### Step 2 — Check FW Image Integrity
```cmd
# Verify FW binary is not zero-length or corrupt
dir C:\Windows\System32\DriverStore\FileRepository\*intcaudiobus*\*.bin
# Expect: non-zero size, matches expected version
```

### Step 3 — Check IPC Mailbox Registers
```python
# HIPCT (Host-to-DSP IPC) — any stuck bits indicate prior timeout
hipct = mem(BAR0 + 0x40, 4)
print(f"HIPCT=0x{hipct:08X}")  # bit31=BUSY should be 0 at idle

# HIPCIE (IPC Error) — check for error codes
hipcie = mem(BAR0 + 0x44, 4)
print(f"HIPCIE=0x{hipcie:08X}")
```

### Step 4 — Check Power Well
DSP requires power well PG2 to be up. If S0ix residency work is ongoing, DSP power well may be forced down.
```python
soc.pmc.pwrm.d3_pgcb_pg_en  # check DSP PG bit
```

### Step 5 — Collect Windows Event Log
```cmd
wevtutil qe System /q:"*[System[Provider[@Name='Service Control Manager']]]" /f:text | findstr -i "audio"
wevtutil qe Application /q:"*[System[Provider[@Name='IntcAudioBus']]]" /f:text
```

### Decision Tree
```
No ROM boot message → DSP stuck in reset → check ACE reset register
ROM boot ok, IPC timeout → FW load issue → check FW binary, check PG2 power
IPC timeout persistent → check HIPCT/HIPCIE → file sighting if register stuck
FW load ok, driver Code 43 → Windows driver version mismatch → Workflow 6 (driver diff)
```

---

## Workflow 3: SoundWire Slave Enumeration Failure

**Symptom**: SoundWire codec (e.g. RT711, CS42L43) not discovered; `SoundWire Manager` shows no slaves; NGA SoundWire tests fail at detection.

**Sub-skill**: `fv-audio/soundwire`

### Step 1 — Verify SoundWire Link is Active
```python
# SoundWire Link Control Register — link must be enabled
sdw_lcr = mem(BAR0 + SDW_LINK_BASE + 0x4, 4)
print(f"LINK_ENABLE={sdw_lcr & 1}")
```
If link not enabled: check `SoundWireEnable` BIOS knob.

### Step 2 — Check Bus Clock
SoundWire requires a valid bus clock (typically 9.6 MHz or 6 MHz for low-power mode).
```python
# Read ACE clock source register — SoundWire must not be in clock-stop
sdw_clk = mem(BAR0 + SDW_LINK_BASE + 0x10, 4)
print(f"CLK_STOP={(sdw_clk >> 16) & 1}")
```

### Step 3 — Check PING Frame Response
The master broadcasts PING frames at startup. Slaves respond with their Device ID.
```
# ETL trace: look for "PING response from address X" or "No response on link N"
```
No response: check codec power (VDDIO, VDDA) via TTK3-I2C. Check board routing.

### Step 4 — Check Enumeration Address Assignment
```python
# SoundWire Slave Device Number register
# Each slave should have a unique assigned address (1-14)
sdw_devn = mem(BAR0 + SDW_LINK_BASE + 0x30, 4)
print(f"Assigned addresses: 0x{sdw_devn:08X}")
```

### Step 5 — Multi-link Conflict Check
On platforms with multiple SoundWire links (e.g. NVL has 4), confirm the codec is wired to the correct link number. BIOS pin descriptors (`_DSD`) define which codec is on which link.

### Decision Tree
```
Link not enabled → BIOS knob → SoundWireEnable=1
Clock stop → power management interference → check S0ix PM interaction (Workflow 5)
No PING response → codec power issue → TTK3 VR read / board trace
PING ok, no address → enumeration software issue → check IntcAudioBus version
Enumeration ok, driver fails → slave capabilities mismatch → check codec firmware version
```

---

## Workflow 4: DMIC No-Record / Silence

**Symptom**: DMIC capture stream returns zeros; no waveform on oscilloscope; NGA DMIC tests fail with silence or noise floor only.

**Sub-skill**: `fv-audio/dmic`

### Step 1 — Verify DMIC GPIO Pad Mode
DMIC CLK and DATA pads must be in native function mode (PMode = 1 for DMIC function).
```python
# Check GPIO pad configuration for DMIC CLK pin
soc.gpio.<community>.dmic_clk_pad_cfg0.pmode  # expect 1 (native function)
soc.gpio.<community>.dmic_data_pad_cfg0.pmode  # expect 1
```
If pmode=0 (GPIO mode): DMIC is electrically disconnected from ACE.

### Step 2 — Check DMIC Clock Source and Frequency
```python
# ACE DMIC clock divider register
dmic_clk_div = mem(BAR0 + DMIC_BASE + 0x04, 4)
# Expected: divide ratio producing 2.4 MHz or 3.072 MHz PDM clock
```

### Step 3 — Check FIFO Status
```python
# DMIC FIFO overrun/underrun status
dmic_fifo_sts = mem(BAR0 + DMIC_BASE + 0x20, 4)
print(f"OVR={(dmic_fifo_sts >> 1) & 1}  UDR={dmic_fifo_sts & 1}")
```
Persistent overrun with silence = FIFO filling with invalid data (clock present but no DMIC response).

### Step 4 — Microphone Privacy Mode Check
NVL and PTL platforms have a hardware microphone privacy mute controlled by an EC GPIO. If the privacy LED is on, PDM data is gated at hardware level.
```python
soc.gpio.<community>.mic_privacy_gpio.gpiorxstate  # 0 = privacy mute active
```

### Step 5 — Test with Known-Good Tone Source
Replace physical DMIC with signal generator at 2.4 MHz PDM rate. If capture then works → MEMS microphone hardware failure.

### Decision Tree
```
pmode wrong → pad config → BIOS/platform bug → file sighting
pmode ok, no clock → ACE clock source → check BIOS DMIC enable knob
Clock ok, FIFO overrun → data corrupted → check PDM polarity / inversion
Privacy mute active → EC GPIO issue → check EC firmware / platform board design
All ok, driver sees silence → gain register → check DMIC gain settings in driver
```

---

## Workflow 5: S0ix Blocked by Audio IP

**Symptom**: S0ix (Modern Standby / PC10) residency is 0% or very low; `powercfg /sleepstudy` shows audio IP in D0; PMC Doctor script reports Audio as blocker.

**Sub-skill**: `fv-audio/power`  
**Cross-delegation**: `FV-IdlePM` for PC10/S0ix framework context

### Step 1 — Run PMC Doctor Script
```python
fv_pm.initialize()
pm_tools.print_s0ix_y_blocking_conditions()  # shows which IPs are blocking
# Look for: ACE / HDA / SoundWire entries in blocker list
```

### Step 2 — Check Audio IP D-state
```python
# ACE must be in D3 before S0ix entry is possible
ace_pmcs = mem(ACE_PCI_BASE + 0xC4, 4)  # PCI PM Control/Status
print(f"POWER_STATE={(ace_pmcs & 0x3)}")  # 3 = D3hot
```
If D0 (=0): audio stack has not released the device. Check which driver handle is open.

### Step 3 — Check LTR Values
```python
pm_tools.print_LTRs()  # LTR values for all IPs
# ACE LTR should be non-zero (device advertising latency tolerance)
# LTR=0 means "cannot tolerate any latency" → blocks S0ix
```

### Step 4 — Close Audio Streams
Any open PCM stream (even at 0 bytes/sec) prevents D3. Use Windows Sound Settings to ensure no application has an audio endpoint open.
```cmd
# Check active audio sessions
powershell -Command "Get-AudioSession"
# Or use Process Monitor to find which process has audio handle open
```

### Step 5 — Force D3 and Verify
```cmd
# Disable audio device in Device Manager, then re-enable
# OR use devcon to cycle
devcon disable *INTCAUDIOBUS*
devcon enable *INTCAUDIOBUS*
# Then re-run sleepstudy
powercfg /sleepstudy /duration 1
```

### Decision Tree
```
ACE D0 with no streams → driver not releasing PM → check IntcAudioBus D3 path
LTR=0 → driver bug → check WPP trace for "LTR programming" messages
ACE D3 but SoundWire link blocking → SoundWire clock-stop not entered → check SW link PM
All D3 but audio still in blocker list → check other audio IPs (BT offload, ISH mic)
Residency improves after driver cycle → intermittent PM handle leak → file sighting
```

---

## Workflow 6: DMA Glitch / Buffer Underrun (XRUN)

**Symptom**: Audio playback/capture has audible clicks or drops; WASAPI reports `AUDCLNT_E_BUFFER_ERROR`; NGA glitch tests detect non-monotonic timestamps or amplitude anomalies.

**Sub-skill**: `fv-audio/dsp` (for offloaded streams), `fv-audio/hda` (for host-mode streams)

### Step 1 — Determine Stream Mode
```cmd
# Offloaded (DSP mode): IntcAudioBus handles DMA, DSP pipeline active
# Host mode: HdAudio.sys handles DMA, no DSP involvement
# Check via ETL trace: look for "OFFLOAD" vs "HOST" stream allocation messages
```

### Step 2 — Check DMA Position Registers
```python
# HDA Stream Descriptor Position in Buffer (LPIB)
# Compare reported position vs wall-clock time
# Large jumps (>period size) indicate a missed interrupt
stream_lpib = mem(BAR0 + SD0_BASE + 0x04, 4)
```

### Step 3 — Check Interrupt Delivery
```python
# INTSTS — pending stream interrupts
intsts = mem(BAR0 + 0x024, 4)
print(f"INTSTS=0x{intsts:08X}")
# Bit 30 = Global Interrupt Status; bits 0-29 = per-stream
```
Missed interrupts (INTSTS set but handler not called) → check MSI-X configuration.

### Step 4 — CPU Stall Correlation
Cross-correlate glitch timestamps with CPU throttle events (C-state demotion, P-state changes).
```cmd
# Windows Performance Recorder — CPU/Platform profile
wpr -start GeneralProfile -start CPU -filemode
<reproduce glitch>
wpr -stop C:\logs\glitch_trace.etl
# Open in WPA → CPU Usage (Sampled) → correlate with audio thread
```

### Step 5 — Check FIFO Watermark Settings
```python
# HDA stream FIFOS (FIFO Size register)
fifos = mem(BAR0 + SD0_BASE + 0x10, 2)
print(f"FIFO_SIZE=0x{fifos:04X}")  # should match configured period size
```

### Decision Tree
```
Glitch correlates with CPU throttle → PM interaction → tune C-state latency via audio BIOS knob
Missed interrupt → MSI-X config → check ACE MSI enable bit
FIFO overrun → period size too small → increase buffer in driver test
Offload glitch but host-mode ok → DSP pipeline issue → Workflow 2 (DSP)
Glitch only under load → bandwidth contention → memory bandwidth test
```

---

## Workflow 7: Jack Detection Failure (Headphone/Headset Not Recognized)

**Symptom**: Headphone plug not detected; `GetJackSinkInformation` returns empty; no pin-sense change event; NGA jack detection test times out.

**Sub-skill**: `fv-audio/jack-detect`

### Step 1 — Identify Jack Type
| Connection | Jack Type | Detection Mechanism |
|------------|-----------|-------------------|
| Analog headphone | HDA codec pin sense | Codec interrupt → `pin_sense_verb` |
| USB Type-C headset | USB hot-plug | xHCI port change event |
| UAOL headset | USB Audio Offload | xHCI + ACE UAOL link |
| SoundWire headset | SoundWire slave alert | SDW alert → driver notification |

### Step 2a — HDA Path: Read Pin Sense Verb
```python
# Codec NID for headphone pin (typically NID 0x21 on Realtek)
# Verb: GET_PIN_SENSE (0xF09) → bit31=presence, bit30=ELD valid
pin_sense = codec_verb_read(codec_addr=0, nid=0x21, verb=0xF09)
print(f"PRESENT={(pin_sense >> 31) & 1}")
```
If PRESENT=0 with headphone plugged: check R_SENSE signal on board; check BIOS VREF/VDET settings.

### Step 2b — SoundWire Path: Read Slave Alert
```python
# SoundWire Slave0 alert register
sdw_alert = mem(BAR0 + SDW_LINK_BASE + SDW_SLAVE0_OFFSET + 0x48, 4)
print(f"JACK_ALERT={(sdw_alert >> 4) & 1}")
```

### Step 3 — Check Codec Interrupt Enable
```python
# Codec must have pin-change interrupt enabled
# GET_EAPD_BTLENABLE (0xF0C) on pin NID
eapd = codec_verb_read(0, 0x21, 0xF0C)
print(f"EAPD={eapd & 0x7}")  # bit1 = EAPD, bit2 = LR_SWAP
# Also check global interrupt mask — codec must have INTEN set
```

### Step 4 — Check Windows Audio Endpoint
```cmd
# Windows sometimes fails to re-enumerate endpoint after codec interrupt
# Restart Windows Audio service as diagnostic
net stop audiosrv && net start audiosrv
# Check if jack is now detected
```

### Step 5 — ETL Trace for Interrupt Path
```cmd
logman start jack_detect -p {INTC_HDA_WPP_GUID} -o C:\logs\jack.etl -ets
# Plug/unplug headphone
logman stop jack_detect -ets
# Look for: "PinSenseChange NID=0x21" or "JackDetect callback"
```

### Decision Tree
```
Pin sense never changes → hardware → check R_SENSE / VREF / board routing
Pin sense changes but no interrupt → INTEN mask → codec interrupt enable verb
Interrupt fires but driver not notified → MSI routing → check ACE interrupt status
Driver notified but Windows no endpoint → audiodg.exe crash → Windows Audio service restart
Works manually, fails in NGA → timing issue → check NGA test jack plug timing parameter
```

---

## Quick Sub-skill Delegation Reference

| Failure Scenario | Primary Sub-skill | Secondary Delegate |
|------------------|-----------------|--------------------|
| HDA codec missing | `fv-audio/hda` | `fv-audio/config-checkout` |
| DSP FW load failure | `fv-audio/dsp` | `fv-audio/power` |
| SoundWire no slave | `fv-audio/soundwire` | `fv-audio/clocking` |
| DMIC silence | `fv-audio/dmic` | `fv-audio/config-checkout` |
| S0ix audio blocker | `fv-audio/power` | `FV-IdlePM` |
| DMA glitch/XRUN | `fv-audio/dsp` or `fv-audio/hda` | `FV-ISH` (if sensor-triggered) |
| Jack detect fail | `fv-audio/jack-detect` | `fv-audio/hda` or `fv-audio/soundwire` |
| UART/serial log capture | `UART-MONITOR` | — |
| Boot-time audio failure | `fv-audio/config-checkout` | `YC_debugger` |
