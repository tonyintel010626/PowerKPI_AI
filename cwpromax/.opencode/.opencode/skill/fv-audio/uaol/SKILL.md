---
name: fv-audio/uaol
description: "USB Audio Offload (UAOL) validation — ACE4/ACE3 offload engine, xHCI integration, isochronous stream management, FIFO timing, behind-hub support, and cross-domain Audio/USB debug"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# FV-AUDIO: UAOL (USB Audio Offload) Sub-Skill

> **Scope**: USB Audio Offload validation on NVL (Novalake) platforms — ACE4 offload engine, xHCI integration, isochronous stream management, FIFO timing, behind-hub support, power management, and cross-domain debug between Audio (ACE) and USB (xHCI) subsystems.

---

## Architecture Overview

UAOL (USB Audio Offload) allows the ACE (Audio/Communication Engine) to autonomously manage USB isochronous audio transfers without host CPU intervention. The xHCI controller offloads isochronous endpoint management to the ACE offload engine, which handles FIFO buffering, timing, and stream continuity.

### Platform Support Matrix

| Platform | ACE | UAOL Engine | FIFO | Behind Hub | Notes |
|----------|-----|------------|------|------------|-------|
| **NVL** | 4.x | ACE4 | Larger (improved) | ✅ Supported | Current generation, enhanced FIFO sizing |
| **RZL** | 4.0 | ACE4 | Larger (improved) | ✅ Supported | Same ACE4 offload engine as NVL — apply NVL procedures |
| **TTL (ACE 4.0)** | 4.0 | ACE4 | *(verify HAS)* | ✅ Expected | ACE4 variant — same UAOL engine as NVL/RZL |
| **TTL (ACE 3.0)** | 3.0 | ACE3 | ~1ms | ✅ Expected | ACE3 variant — same UAOL engine as PTL |
| **PTL** | 3.0 | ACE3 | ~1ms | ✅ Supported | Fixed from MTL hub issue |
| **WCL** | 3.0 | ACE3 | ~1ms | ✅ Expected | Shares PTL ACE3 architecture — same UAOL engine |
| **LNL** | 2.x | ACE 2.x (internal) | ~1ms | ❌ NOT supported | Internal UAOL only — no behind-hub |
| **MTL** | 1.5 | ACE (early) | ~1ms | ❌ NOT supported | RTL bug — behind-hub broken |
| **ARL** | 1.5 | ACE 1.5 (internal) | ~1ms | ❌ NOT supported | Internal UAOL only — no behind-hub |

> **ACE 4.x platforms (NVL, RZL, TTL ACE4)** share the enhanced UAOL engine with larger FIFO and improved behind-hub support. Debug procedures for UAOL on RZL/TTL ACE4 are identical to NVL.

> **ACE 3.x platforms (PTL, WCL, TTL ACE3)** share the ACE3 UAOL engine. Debug procedures for UAOL on WCL/TTL ACE3 are identical to PTL.

### UAOL Signal Path

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  USB Audio   │  USB    │    xHCI      │ Offload │    ACE4      │
│   Device     │◄──────►│  Controller  │◄───────►│   UAOL       │
│ (Headset/DAC)│  Isoch  │              │  FIFO   │   Engine     │
└──────────────┘         └──────────────┘         └──────┬───────┘
                                                         │
                                                  ┌──────▼───────┐
                                                  │    DSP       │
                                                  │  Pipeline    │──► Host DMA
                                                  └──────────────┘
```

### How UAOL Works

1. USB audio device enumerates on xHCI (standard USB enumeration)
2. Audio driver opens isochronous stream
3. If UAOL is enabled, xHCI offloads the isochronous endpoint to ACE4
4. ACE4 UAOL engine autonomously handles:
   - Isochronous transfer scheduling (microframe timing)
   - FIFO buffering between USB and DSP
   - Stream continuity during brief link glitches
5. Host CPU is freed from isochronous interrupt servicing
6. **When UAOL is active, isochronous traffic is NOT visible in xHCI event ring traces**

---

## Key Differences from Standard USB Audio

| Aspect | Standard USB Audio | UAOL |
|--------|-------------------|------|
| Isochronous handling | Host CPU services each microframe | ACE4 handles autonomously |
| CPU utilization | Higher (interrupt per microframe) | Lower (offloaded) |
| xHCI trace visibility | Visible in event ring | **NOT visible** — offloaded to ACE |
| Power impact | xHCI must stay D0 | xHCI must stay D0 during active stream |
| Behind-hub support | Always works | NVL/PTL: ✅, MTL: ❌ |
| Debug methodology | xHCI ETL traces | ACE FIFO status + UAOL-specific traces |

---

## UAOL Configuration

### Enabling UAOL

| Setting | Location | Value |
|---------|----------|-------|
| Registry (Windows) | `HKLM\SYSTEM\CurrentControlSet\Services\UAOL\Enable` | 1 (enabled) / 0 (disabled) |
| BIOS | HD Audio DSP | Enabled (required for ACE) |
| Driver | USB Audio Class driver + UAOL filter | Both must be loaded |

### Verifying UAOL Status

```powershell
# Check if UAOL service is running (Windows)
Get-Service -Name "UAOL" | Format-List Name, Status, StartType

# Check registry setting
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\UAOL" -Name "Enable"

# Check if UAOL filter is loaded on USB audio device
Get-PnpDevice -FriendlyName "*USB Audio*" | Get-PnpDeviceProperty
```

### PythonSV Verification

```python
# Verify ACE is enumerated with DSP capability
import pysvtools.pciedut as pcie

ace = pcie.get_dev(0, 31, 3)
did = ace.cfg.read(0x02, 2)
print(f"ACE Device ID: 0x{did:04X}")

# Check UAOL-related DSP status via BAR2
# GPROCEN must be set for BAR2 access
ppctl = ace.bar0.read(0x1004, 4)
assert ppctl & (1 << 30), "GPROCEN not set"

# Read UAOL engine status (offset platform-specific)
# Check FIFO status, active stream count
```

---

## FIFO Management

The ACE4 UAOL engine uses a FIFO buffer between the USB isochronous endpoint and the DSP audio pipeline. FIFO sizing is critical for glitch-free audio.

### FIFO Characteristics

| Parameter | NVL (ACE4) | PTL (ACE3) |
|-----------|-----------|-----------|
| FIFO Depth | Enhanced (>1ms) | ~1ms |
| Overrun Protection | Yes | Yes |
| Underrun Protection | Yes | Yes |
| Adaptive Rate | Supported | Supported |

### FIFO-Related Failure Modes

| Failure | Cause | Detection |
|---------|-------|-----------|
| FIFO Underrun | USB transfer delayed, FIFO empties | Audio glitch (silence gap), underrun counter |
| FIFO Overrun | DSP not consuming fast enough | Audio glitch (repeated sample), overrun counter |
| Clock Drift | USB SOF and audio PLL mismatch | Gradual pitch shift, eventual glitch |
| Adaptive Rate Failure | Feedback endpoint not responding | Pitch drift, eventual buffer wrap |

---

## Power Management Interaction

UAOL creates complex power management dependencies between the USB and Audio subsystems.

### Power Rules During Active UAOL Stream

| Component | Required State | Reason |
|-----------|---------------|--------|
| xHCI | **D0** (must stay active) | USB isochronous transfers require active link |
| ACE | **D0** | UAOL engine must be running |
| USB Port | **U0** (no U2/U3) | U2/U3 latency breaks isochronous timing |
| USB Port U1 | Conditional | Only if U1 exit < 125µs budget |

### S0ix Interaction

```
Active UAOL stream → BLOCKS S0ix
  ├── xHCI must stay D0 → blocks PCIe L1.2 → blocks S0ix
  └── ACE must stay D0 → ACE is S0ix blocker

To enter S0ix:
  1. Pause/stop UAOL stream
  2. USB audio device can enter U2/U3 (selective suspend)
  3. xHCI can enter D3
  4. ACE can enter D3
  5. S0ix unblocked
```

### PSF Glitch Risk (NVL-specific)

> **WARNING**: On NVL, there is a known PSF (Primary Sideband Fabric) glitch risk when UAOL is active. The `DfSPSREQ` register must be checked for proper sideband request sequencing. See HSDES 18043001729 for details.

---

## Debug Methodology

### UAOL Debug Playbook

```
Step 1: Verify UAOL is active
  ├── Check registry: HKLM\...\UAOL\Enable = 1
  ├── Check service: UAOL service running
  └── Check device: UAOL filter loaded on USB audio device

Step 2: Compare UAOL enabled vs disabled
  ├── Disable UAOL (registry Enable=0), reboot
  ├── Reproduce issue with UAOL disabled
  ├── If issue disappears → UAOL-specific bug
  └── If issue persists → USB audio or driver bug

Step 3: Check ACE FIFO status
  ├── Read FIFO level registers (platform-specific BAR2 offset)
  ├── Check overrun/underrun counters
  └── Monitor FIFO levels during playback

Step 4: Capture UAOL ETL trace
  ├── Provider: Microsoft-Windows-USB-UAOL
  ├── Start trace: logman start uaol -p {UAOL-GUID} -o uaol.etl -ets
  ├── Reproduce issue
  └── Stop and decode trace
```

### ETL Trace Capture

```powershell
# Start UAOL ETL trace
logman start uaol_trace -p "Microsoft-Windows-USB-UAOL" 0xFFFFFFFF 0xFF -o C:\Logs\uaol_trace.etl -ets

# Reproduce the audio issue...

# Stop trace
logman stop uaol_trace -ets

# Decode (requires USB/UAOL symbols)
# See fv-usb/debug/etl-decode for full decode workflow
```

### NVL SST Log Capture for UAOL Debug

*Source: [Wiki Page 4182673124]*

When debugging UAOL issues on NVL, use the Intel SST (Smart Sound Technology) driver log capture flow. This captures internal driver state during UAOL stream setup and teardown.

> **Related sighting**: HSDES 15017834493 (PTL UAOL debug reference — same log capture methodology applies to NVL)

```
Step 1: Disable IntcAudioBus driver
  ├── Device Manager → Intel Smart Sound Technology for USBAudio
  └── Right-click → Disable device

Step 2: Start SST diagnostic log
  ├── Open elevated PowerShell
  ├── logman start sst_audio -p "IntcSmartSound" 0xFFFFFFFF 0xFF -o C:\Logs\sst_uaol.etl -ets
  └── (Provider name may vary — check WPP Autologger section in failure-analysis skill)

Step 3: Re-enable IntcAudioBus driver
  ├── Device Manager → Intel Smart Sound Technology for USBAudio
  └── Right-click → Enable device

Step 4: Reproduce the UAOL issue
  └── Plug USB audio device, start playback/capture, trigger failure

Step 5: Stop SST log
  └── logman stop sst_audio -ets

Step 6: Decode and analyze
  ├── Use tracefmt with matching PDB symbols
  └── Look for: offload engine init, FIFO setup, stream start/stop events
```

> **KEY**: The disable→start log→re-enable sequence ensures the log captures the full driver initialization path including UAOL offload engine setup. This is critical for diagnosing enumeration-time failures.

### Key Debug Signals

| Signal | Where to Find | What It Means |
|--------|---------------|---------------|
| UAOL active | UAOL ETL trace | Offload engine is handling isochronous |
| FIFO underrun count | ACE BAR2 registers | USB transfer delays |
| FIFO overrun count | ACE BAR2 registers | DSP processing delays |
| xHCI D-state | xHCI PMCSR | Must be D0 during active UAOL |
| USB port link state | xHCI PORTSC PLS | Must be U0, no U2/U3 |
| VISA signals | VISA debug (if available) | HSDES 22018119897: VISA signals may be missing |

---

## Validation Points

### Basic Functionality

| Test | Method | Pass Criteria |
|------|--------|---------------|
| UAOL playback | Play music via USB headset (UAOL enabled) | Clean audio, no glitches |
| UAOL capture | Record via USB mic (UAOL enabled) | Clean capture, correct sample rate |
| UAOL simultaneous | Play + record simultaneously | Both directions clean |
| UAOL vs non-UAOL | Compare A/B with UAOL on/off | No quality difference (UAOL is transparent) |
| USB audio behind hub | USB headset through USB hub | Audio works (NVL/PTL), fails gracefully (MTL) |

### Stress & Robustness

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Long duration | 8hr continuous playback | No glitches, no drift, FIFO stable |
| Plug/unplug during stream | Remove USB audio while playing | Graceful stop, no BSOD/hang |
| Suspend/resume | S3→wake with USB audio active | Stream resumes cleanly |
| Multi-device | 2+ USB audio devices with UAOL | Independent streams, no interference |
| Hub + direct mixed | One device direct, one behind hub | Both work simultaneously |

### Power Management

| Test | Method | Pass Criteria |
|------|--------|---------------|
| S0ix with UAOL idle | USB audio connected, no stream | S0ix achieved (ACE D3, xHCI D3) |
| S0ix blocked by UAOL | Active stream, check S0ix | S0ix correctly blocked |
| Selective suspend | USB audio idle timeout | Device enters U3, UAOL inactive |
| Resume from selective suspend | Start playback after idle | Audio starts < 500ms |

---

## Known Issues

| ID | Description | Platform | Impact |
|----|-------------|----------|--------|
| HSDES 16029865294 | ACE3 recording stuck ~30s-3min with Astro40 headset | PTL | Capture freezes, requires reconnect |
| HSDES 18043001729 | ACE4 FIFO sizing issue, PSF glitch risk | NVL | Check DfSPSREQ register |
| HSDES 22018119897 | VISA signals missing for UAOL glitch debug | NVL | Cannot use VISA for UAOL timing analysis |
| MTL behind-hub | UAOL behind USB hub broken (RTL bug) | MTL | Disable UAOL when behind hub on MTL |

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No audio with UAOL enabled | UAOL service not running or filter not loaded | Check service status, verify registry Enable=1, check device manager |
| Audio glitches (periodic) | FIFO underrun from USB timing | Check FIFO counters, try different USB port, check for U1/U2 entering |
| Audio works without UAOL but fails with | UAOL engine bug or FIFO issue | Disable UAOL to confirm, capture UAOL ETL, file sighting |
| USB audio behind hub fails | Behind-hub not supported (MTL) or hub issue | Check platform (NVL/PTL OK, MTL broken), try direct connection |
| Audio drift over time | Clock mismatch USB SOF vs audio PLL | Check adaptive rate feedback, XTAL stability |
| S0ix blocked with USB audio idle | UAOL not properly releasing offload | Verify stream fully stopped, check ACE PMCSR, check xHCI D-state |
| BSOD during USB audio unplug | Race condition in UAOL teardown | Capture crash dump, check if fixed in latest driver |
| Recording stuck (PTL) | Known ACE3 issue with certain headsets | HSDES 16029865294 — check if headset is Astro40 or similar |

---

## Cross-Domain Debug

UAOL spans two IP domains — **Audio (ACE)** and **USB (xHCI)**. Debug often requires tools from both:

| Domain | Tools | What to Check |
|--------|-------|---------------|
| **Audio** | ACE BAR2 registers, DSP pipeline status | FIFO levels, offload engine state, DSP processing |
| **USB** | xHCI PORTSC, USB ETL trace, UAOL ETL | Port link state, device enumeration, endpoint config |
| **Power** | PMCSR (ACE + xHCI), S0ix blockers | Both IPs must be in correct D-state |
| **Platform** | PSF registers (NVL), VISA | Sideband fabric timing, signal integrity |

> **TIP**: When debugging UAOL issues, always capture BOTH the USB ETL trace and the UAOL ETL trace simultaneously. The USB trace shows enumeration and non-offloaded traffic, while the UAOL trace shows offloaded stream behavior.

---

## Related Sub-Skills

- **fv-usb** — USB enumeration, xHCI registers, power management (UAOL's other half)
- **fv-usb/debug/etl-decode** — ETL trace decode workflow for USB/UAOL traces
- **fv-audio/dsp** — DSP pipeline receiving UAOL audio data
- **fv-audio/power** — ACE D0i3/D3 transitions affecting UAOL
- **fv-audio/config-checkout** — BIOS and PCI enumeration verification
- **fv-audio/failure-analysis** — NGA failure triage for UAOL test failures
