# Audio Validation Cheat Sheets
<!-- owner: huiyingt | platform: NVL, PTL, MTL, LNL | os: Windows 11 only | last updated: 2026-04-01 -->
<!-- companion to: ../SKILL.md, audio_reference_sheets.md -->

> Quick-reference cards for the most common audio debug and validation operations.
> For full workflows see `audio_validation_workflows.md`. For known bugs see `audio_known_issues.md`.

---

## Card 1 — Audio Device Enumeration (PythonSV)

```python
# Verify ACE device is visible on PCI bus
import pythonsv as psv
psv.refresh()

# Check BDF B0:D31:F3
vid = pci_read(0, 31, 3, 0x00) & 0xFFFF   # Vendor ID  → 0x8086
did = pci_read(0, 31, 3, 0x00) >> 16       # Device ID  → 0xD328 (NVL PCD-H)
cmd = pci_read(0, 31, 3, 0x04) & 0xFFFF   # Command    → bit1 (MSE) must be set
bar0 = pci_read(0, 31, 3, 0x10)            # BAR0       → 512 KB HDA MMIO
bar2 = pci_read(0, 31, 3, 0x18)            # BAR2       → 2 MB DSP MMIO
print(f"VID={vid:#06x} DID={did:#06x} CMD={cmd:#06x} BAR0={bar0:#010x} BAR2={bar2:#010x}")

# Expected NVL PCD-H: VID=0x8086 DID=0xd328 BAR0=<non-FF> BAR2=<non-FF>
# If DID=0xFFFF → device not enumerated; check BIOS knob AudioController=Enabled
```

---

## Card 2 — HDA Codec Presence Check (PythonSV)

```python
# Read STATESTS register — bit N set = codec present on link N
bar0_base = pci_read(0, 31, 3, 0x10) & ~0xF   # strip type bits
STATESTS_OFFSET = 0x0E    # STATESTS register
statests = mem_read32(bar0_base + STATESTS_OFFSET)
print(f"STATESTS = {statests:#010x}")
# Bit 0 = codec on link 0, Bit 1 = link 1, etc.
# Expected: at least bit 0 set (primary codec)

# Force codec detection (CRST cycle)
GCTL_OFFSET = 0x08
gctl = mem_read32(bar0_base + GCTL_OFFSET)
mem_write32(bar0_base + GCTL_OFFSET, gctl & ~0x1)  # de-assert CRST
import time; time.sleep(0.1)
mem_write32(bar0_base + GCTL_OFFSET, gctl | 0x1)   # assert CRST
time.sleep(0.5)
statests = mem_read32(bar0_base + STATESTS_OFFSET)
print(f"STATESTS after CRST = {statests:#010x}")
```

---

## Card 3 — BIOS Knob Quick Reference

| Knob Name | Path | Default | When to Change |
|-----------|------|---------|----------------|
| `AudioController` | Advanced → PCH Config | Enabled | Disable to isolate PCH audio from SoC |
| `AudioDsp` | Advanced → Audio Config | Enabled | Must be ON for SOF FW to load |
| `SoundWireEnable` | Advanced → Audio Config | Enabled | Disable to isolate HDA-only path |
| `DmicEnable` | Advanced → Audio Config | Enabled | Disable to stop DMIC capturing |
| `I2S_SSP_Enable` | Advanced → Audio Config | Enabled | Disable to isolate BT HFP path |
| `AudioD3PG` | Advanced → PM Config | Enabled | D3 power gate control |
| `UsitEnable` | Advanced → USB Config | Enabled | Required for UAOL |
| `ModernStandby` | Advanced → PM Config | S0ix | S0ix mode for audio PM tests |
| `WoVEnable` | Advanced → Audio Config | Enabled | WoV keyword detect enable |
| `HdaVerbTableEnable` | Advanced → Audio Config | Enabled | Codec init verb table |

---

## Card 4 — DSP Firmware Status Check

```python
# Check DSP firmware load status via IPC BOOT_STATUS
# IPC registers are in BAR2 (DSP MMIO region)
bar2_base = pci_read(0, 31, 3, 0x18) & ~0xF

# HIPCT — DSP to host interrupt trigger
# NOTE: HIPCT at offset 0x78 applies to legacy HDA (pre-ACE 3.0).
# On ACE 4.x (NVL) and ACE 3.0 (PTL), offset 0x78 is RESERVED.
# Use PythonSV namednode path instead: soc.ace.hda.bar0.hipct
# Alternatively, IPC registers are accessed via DSP BAR at IPC_CMD=0x00, IPC_STS=0x04
HIPCT_OFFSET = 0x78   # Legacy HDA only — do NOT use on ACE 3.0+ (see note above)
hipct = mem_read32(bar2_base + HIPCT_OFFSET)
print(f"HIPCT = {hipct:#010x}")

# Windows: check Event Viewer → Applications and Services Logs
#   → Microsoft → Windows → Audio → Operational
#   Event ID 1 = Audio Engine started
#   Event ID 65536 = SOF FW load success

# PowerShell: check Windows Audio service state
# Get-Service -Name 'AudioSrv','Audiosrv','AudioEndpointBuilder' | Select Name,Status
```

---

## Card 5 — S0ix Audio PM Quick Check

```python
# Step 1: Verify ACE LTR is satisfied (not blocking S0ix)
# Run doctor script (requires PMC FW debug access):
# fv_pm.initialize()
# pm_tools.print_LTRs()
# pm_tools.print_s0ix_y_blocking_conditions()
# → Look for ACE/Audio entry in blocking conditions list

# Step 2: Check ACE power state via PMCSR
bar0_base = pci_read(0, 31, 3, 0x10) & ~0xF
PMCSR_OFFSET = 0xFC    # PCI Power Management Control/Status
pmcsr = mem_read16(bar0_base + PMCSR_OFFSET)
ps = pmcsr & 0x3
print(f"PMCSR PowerState = D{ps}")
# Expected in S0ix gate: D3hot (ps == 3)
# If D0 (ps == 0) → ACE blocking S0ix; check DSP FW activity

# Step 3: Residency counters via SoCWatch
# socwatch -f debug-cpu-cstate -f debug-pkg-cstate -t 30 -o audio_s0ix
```

---

## Card 6 — SoundWire Segment Status Check

```python
# SoundWire registers are in BAR0 at platform-specific offsets
# Segment 0 base offset: query Co-Design for ACE 4.x SDW_LINK0_BASE

# Quick: check Windows Device Manager or powershell
# Get-PnpDevice | Where-Object { $_.FriendlyName -like "*SoundWire*" }
# Expected: Intel SoundWire Controller × N (N = active segments)

# PythonSV: read SoundWire sync status
# Bit patterns indicating good link: SYNPRD locked, CLK not stopped
# Command: css.run(collectors=["acesoundwire"])  ← if collector available

# NGA: run sdw_enum_test.py and check for:
# "SDW_SLAVE_DETECTED: addr=0x..." → slave found
# "SDW_ENUM_COMPLETE" → enumeration success
# "SDW_CLK_STOP" → normal sleep; "SDW_CLK_FAIL" → error
```

---

## Card 7 — DMIC Capture Quick Start

```python
# Windows PowerShell: capture 5s of DMIC audio
$cap = New-Object -ComObject "WbemScripting.SWbemLocator"
# Or use SoundRecorder / ffmpeg for quick capture test:
# ffmpeg -f dshow -i audio:"Microphone Array" -t 5 dmic_test.wav

# PythonSV: verify DMIC clock is running
# Check pad mode for DMIC clock/data pads
# Expected PMode = 1 (native DMIC function)
# NVL pad names: DMIC_CLK_A, DMIC_DATA0_A, DMIC_DATA1_A (query Co-Design for exact names)

# NGA: run dmic_capture_pdm0.py
# Pass criteria: SNR > 30 dB, no clipping, sample rate locked at 16 kHz or 48 kHz
```

---

## Card 8 — Key NGA Test Scripts & XMLs

| Purpose | Script / XML |
|---------|-------------|
| BKC checkout (quick 15 min) | `audio_bkc_checkout.xml` |
| Full regression (~6 hr) | `audio_regression_full.xml` |
| HDA only | `audio_hda_full.xml` |
| SoundWire only | `audio_sdw_full.xml` |
| DSP firmware | `audio_dsp_full.xml` |
| DMIC | `audio_dmic_full.xml` |
| PM / S0ix | `audio_pm_full.xml` |
| UAOL | `audio_uaol_full.xml` |
| WoV | `audio_wov_full.xml` |
| Jack detect | `audio_jack_full.xml` |
| BT SCO offload | `audio_ssp_full.xml` |
| S0ix audio deep | `audio_s0ix_validation.xml` |
| Stress overnight | `audio_stress_overnight.xml` |

Test content root: `C:\validation\windows-test-content\audio\`

---

## Card 9 — Common Failure → Sub-skill Routing

| Symptom | Route to Sub-skill |
|---------|-------------------|
| Device not enumerated / DID = 0xFFFF | `config-checkout` |
| Codec not found / STATESTS = 0 | `hda` |
| No SoundWire slave detected | `soundwire` |
| DSP FW load timeout / IPC_TIMEOUT | `dsp` |
| DMIC: no audio / silent capture | `dmic` |
| BT HFP SCO no audio | `bt-offload` |
| HDMI/DP no audio | `display-audio` |
| Headset not detected / jack miss | `jack-detect` |
| S0ix blocked by audio | `power` |
| LTR not satisfied | `power` |
| IRQ missing / MSI not firing | `interrupts` |
| UAOL USB audio dropouts | `uaol` |
| WoV keyword not detected | `wov` |
| AIOC codec not present (NVL) | `aioc` |
| Clocking / PLL not locked | `clocking` |
| NGA failure analysis / triage | `failure-analysis` |

---

## Card 10 — Windows Audio Driver Stack (Quick Reference)

```
Application
    │
    ▼
Windows Audio Engine (audiodg.exe)
    │ KS (Kernel Streaming) via PortCls
    ▼
HDA Class Driver: portcls.sys
    │ miniport
    ▼
Intel HDA Miniport: intcaudiobus.sys      ← verb programming, codec enumeration
    │
    ▼
Intel ACE / SoundWire: intcpchsnd.sys     ← SoundWire host controller
    │
    ▼
Intel SOF DSP Runtime: intelaud.sys       ← DSP FW load, IPC, pipeline mgmt
    │
    ▼
Intel DMIC Driver: intelpch_dmic.sys      ← PDM clock, FIFO config
    │
    ▼
ACE Hardware (BAR0 / BAR2)
```

Driver log location: `%SystemRoot%\System32\drivers\`
Event log: `Event Viewer → Applications and Services Logs → Microsoft → Windows → Audio`
