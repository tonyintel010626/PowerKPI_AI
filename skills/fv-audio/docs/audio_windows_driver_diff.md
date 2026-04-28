# FV-AUDIO Windows Driver Behavior Guide

> **Platform**: Intel Client SoC (NVL/PTL/MTL/LNL/ARL) — Windows only  
> **Last Updated**: 2026-04-01  
> **Owner**: huiyingt  
> **Version**: rev2.0

This document details Windows-specific audio driver behaviors, inter-driver differences, registry controls, ETW/WPP trace GUIDs, and known per-generation driver issues. It is the primary reference for understanding why audio behavior differs across driver versions or platforms even when hardware is identical.

---

## 1. Windows Audio Driver Stack Overview

```
┌─────────────────────────────────────────────────────────┐
│                 User-Mode Applications                    │
│   WASAPI / DirectSound / WinMM / AudioGraph API          │
├─────────────────────────────────────────────────────────┤
│              audiodg.exe (Audio Device Graph)            │
│        APO (Audio Processing Objects) pipeline           │
├─────────────────────────────────────────────────────────┤
│           Windows Audio Session API (WASAPI)             │
├─────────────────────────────────────────────────────────┤
│           Port Class Driver (PortCls.sys)                │
│    KS (Kernel Streaming) miniport driver interface       │
├─────────────────────────────────────────────────────────┤
│                        ACE Bus                           │
│           IntcAudioBus.sys  (Intel ACE bus driver)       │
├──────────────────┬──────────────────┬───────────────────┤
│  HDA Miniport    │  SoundWire MM    │  DSP/FW Miniport  │
│  intcaudiohda.sys│ intcsdwhda.sys   │ IntcSmartSound.sys│
├──────────────────┴──────────────────┴───────────────────┤
│          ACE Hardware (PCI Device — VID:8086)            │
│     HDA Controller / SoundWire Links / DSP Core          │
└─────────────────────────────────────────────────────────┘
```

### Key Driver Files by Function

| Driver Binary | Function | Inf File |
|--------------|----------|----------|
| `IntcAudioBus.sys` | ACE PCI bus enumeration, power management, FW load coordination | `IntcAudioBus.inf` |
| `intcaudiohda.sys` | HDA codec verb I/O, stream management, CORB/RIRB | `intcaudiohda.inf` |
| `intcsdwhda.sys` | SoundWire link management, slave discovery, SDW streaming | `intcsdwhda.inf` |
| `IntcSmartSound.sys` | DSP firmware load, IPC, topology management | `IntcSmartSound.inf` |
| `HdAudio.sys` | Microsoft inbox HDA (fallback when Intel driver absent) | in-box |
| `CsAudioAcp3x.sys` / `CsAudioAcp6x.sys` | Cirrus Logic UAOL codec companion | `csaudioacp*.inf` |

---

## 2. IntcAudioBus vs HdAudio.sys — Behavioral Differences

| Behavior | `IntcAudioBus.sys` (Intel) | `HdAudio.sys` (Microsoft Inbox) |
|----------|---------------------------|----------------------------------|
| Power management | Full D0i3/D3hot/D3cold support; LTR programming; autonomous CGPG | D3hot only; no LTR; no clock gating |
| S0ix readiness | Actively gates clocks, enters D3 for S0ix; coordinates with PMC | Typically stays D3hot but does not coordinate with PMC |
| DSP offload | Loads DSP firmware; enables offload pipeline | No DSP support; host-mode only |
| SoundWire | Full SDW link management including multi-drop, banked config | No SoundWire support |
| Stream format | Supports TDM, PDM (DMIC), I2S via DSP | HDA PCM only |
| DMIC | Exposes ACE DMIC capture via DSP pipeline | No DMIC support |
| UAOL | Coordinates ACE FIFO timing with xHCI for USB audio offload | No UAOL support |
| Acoustic echo cancel | Hardware AEC offload via DSP | Software AEC via APO only |
| Debug visibility | WPP traces via Intel provider GUIDs (see §4) | ETW via Microsoft HdAudio provider |
| Fallback behavior | Driver crash → Windows falls back to `HdAudio.sys` automatically | — |

**Validation note**: NGA audio tests require `IntcAudioBus.sys` to be loaded. If `HdAudio.sys` is active instead (driver installation failure), most NGA tests will fail at capability check step.

---

## 3. Driver Behavior Differences Across Silicon Generations

| Feature / Behavior | NVL (Novalake) | PTL (Panther Lake) | MTL (Meteor Lake) | LNL (Lunar Lake) | ARL (Arrow Lake) |
|--------------------|----------------|--------------------|-------------------|-------------------|-------------------|
| ACE version | ACE4 | ACE4 | ACE3 | ACE4 | ACE3 |
| UAOL support | ✅ ACE4 UAOL | ✅ ACE4 UAOL | ✅ ACE3 UAOL | ✅ ACE4 UAOL | ✅ ACE3 UAOL |
| AIOC codec | ✅ ALC712/ALC1320 | ✅ ALC1320 | ❌ | ✅ ALC712 | ❌ |
| BT Audio Offload SSP | ✅ SSP1 | ✅ SSP1 | ✅ SSP0 | ✅ SSP1 | ✅ SSP0 |
| SoundWire links | 4 | 4 | 2 | 4 | 2 |
| DMIC max channels | 4 | 4 | 4 | 4 | 4 |
| DSP firmware name | `dsp_fw_nvl.bin` | `dsp_fw_ptl.bin` | `dsp_fw_mtl.bin` | `dsp_fw_lnl.bin` | `dsp_fw_arl.bin` |
| IntcAudioBus min ver | 12.0.0.xxxx | 12.0.0.xxxx | 11.0.0.xxxx | 12.0.0.xxxx | 11.0.0.xxxx |
| WoV HW support | ✅ CRO-based | ✅ CRO-based | ✅ DSP-based | ✅ CRO-based | ✅ DSP-based |

**Driver load note**: `IntcAudioBus.inf` contains hardware IDs per platform. If a new silicon stepping has a new DID, the driver INF must be updated — otherwise Windows loads `HdAudio.sys` as fallback. Always verify DID match when bringing up a new stepping.

---

## 4. WPP / ETW Trace GUIDs

Use these GUIDs with `logman` or Windows Performance Recorder to capture component-specific audio traces.

| Component | Provider GUID | Log Usage |
|-----------|-------------|-----------|
| IntcAudioBus (bus driver) | Consult Intel innersource `IntcAudioBus.h` — search for `WPP_DEFINE_CONTROL_GUID` | Bus-level PM, FW load, device enumeration |
| IntcSmartSound (DSP) | Consult Intel innersource `IntcSmartSound.h` — search for `WPP_DEFINE_CONTROL_GUID` | DSP IPC, FW state, DMA |
| intcaudiohda (HDA codec) | Consult Intel innersource `intcaudiohda.h` | Verb I/O, stream, interrupt |
| intcsdwhda (SoundWire) | Consult Intel innersource `intcsdwhda.h` | Link management, slave discovery |
| Microsoft HdAudio | `{4ADE9CFF-3DC5-4D91-8D30-EF5DD42DD9E9}` | Inbox HDA fallback (non-Intel) |
| Windows Audio Graph | `{A6A678AA-8AEA-4B35-B073-F5E3AEC5B2EF}` | audiodg.exe, APO pipeline |

> **Note**: Intel WPP GUIDs are defined in driver source headers. Access via Intel innersource at `//depot/sw/audio/drivers/windows/`. The exact GUIDs are not reproduced here to avoid stale values — always use the GUID from the source corresponding to the driver version under test.

### ETL Capture Template
```cmd
:: Capture all Intel audio components
logman start audio_full ^
    -p <IntcAudioBus_GUID> ^
    -p <IntcSmartSound_GUID> ^
    -p <intcaudiohda_GUID> ^
    -p <intcsdwhda_GUID> ^
    -o C:\logs\audio_full_%DATE%.etl ^
    -ets

:: Reproduce the failure...

logman stop audio_full -ets

:: Decode (requires .pdb files in same directory as .etl)
tracepdb.exe -f <pdb_dir>
tracefmt.exe audio_full_<date>.etl -p <tmf_dir> -o audio_full.txt
```

---

## 5. Registry Knobs (Windows Audio Debug Controls)

These registry values are set under `HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters` unless noted.

| Registry Value | Type | Default | Effect |
|---------------|------|---------|--------|
| `DisableDSP` | DWORD | 0 | 1 = disable DSP firmware load; forces host-mode HDA only |
| `DisableSoundWire` | DWORD | 0 | 1 = disable SoundWire link enumeration |
| `DisableD3Cold` | DWORD | 0 | 1 = prevent D3cold entry; useful to keep ACE alive for debug |
| `EnableVerboseLogging` | DWORD | 0 | 1 = enable verbose WPP trace output |
| `OverrideD3Timeout` | DWORD | 0 (ms) | Non-zero: override D3 idle timeout in milliseconds |
| `DisableUAOL` | DWORD | 0 | 1 = disable USB Audio Offload engine |
| `ForceHostMode` | DWORD | 0 | 1 = force all streams to host-mode (no DSP offload) |
| `DisableDMIC` | DWORD | 0 | 1 = disable DMIC capture path |

> **Note**: Registry keys vary by driver version. Confirm key names against driver INF or WPP trace messages. Non-standard keys added by pre-production drivers may differ from production.

---

## 6. Power Management State Machine (Windows Driver Perspective)

```
Device Active (D0)
    │  ←── Stream opened / audio playing
    │  ──→ All streams closed + idle timeout
    ▼
D0i3 (clock gated, context retained)
    │  ←── Quick-resume needed (short idle)
    │  ──→ Extended idle (driver-determined, typically 150ms+)
    ▼
D3hot (power removed from link power domain)
    │  ←── New stream request → D0 re-init
    │  ──→ D3cold entry negotiated with PMC
    ▼
D3cold (full power removed, PMC controls sequencing)
    │  ←── Wake event (audio trigger, WoV, jack detect)
    └──→ S0ix entry possible once all IPs reach D3cold
```

**Key Windows PM hooks in IntcAudioBus**:
- `EvtDeviceD0Entry` — called on D0 re-entry; triggers FW reload if D3cold was entered
- `EvtDeviceD0Exit` — called on D0 exit; programs LTR, gates DSP clocks
- `PoSetDeviceBusyEx` — prevents D3 while stream is active
- `WdfDeviceAssignS0IdleSettings` — configures idle timeout and D3 type

**Common validation failure**: Test script holds an audio capture handle open while checking S0ix residency. ACE stays in D0 → S0ix blocked. Always close all audio handles before measuring S0ix.

---

## 7. Known Driver Behavioral Quirks by Version Band

| Driver Version Band | Platform | Known Behavior | Workaround |
|--------------------|----------|---------------|------------|
| 10.x.x.xxxx | MTL/ARL (ACE 1.5) | No D3cold support | Use DisableD3Cold=0 but accept no S0ix |
| 11.x.x.xxxx | MTL/ARL (ACE 1.5) | D3cold support added; may race with PMC on first S0ix entry | Ensure PMC FW ≥ BKC version before testing |
| 12.x.x.xxxx | NVL (ACE 4.x), PTL (ACE 3.0), LNL (ACE 2.x) | UAOL FIFO timing strict; requires HAS-compliant firmware | Always use NGA-specified IFWI + driver combo |
| 12.x.x.xxxx | NVL | WoV CRO clock handoff timing sensitive to BIOS microcode patch | Verify ucode ≥ required version from OneBKC |

> **Accuracy disclaimer**: Version bands above are approximate. Consult `OneBKC` for the exact BKC-approved driver + IFWI combination for each platform/stepping before drawing debug conclusions.

---

## 8. Debug Differentiation: IntcAudioBus Fault vs Hardware Fault

| Symptom | Intel Driver Fault Indicator | Hardware Fault Indicator |
|---------|------------------------------|--------------------------|
| Codec not detected | Driver loads, STATESTS=0, inbox HdAudio detects codec | STATESTS=0 with both drivers; itp probe confirms no codec VID |
| DSP FW load fails | WPP trace shows load command sent, no ACK; reload fixes | ACE BAR0 reads return 0xFF (power issue) |
| S0ix blocked | `powercfg /sleepstudy` names IntcAudioBus as blocker | PMC Doctor shows non-audio IP blocking; audio D3 confirmed |
| Jack detect fails | Pin sense verb returns correct value; Windows UI wrong | Pin sense verb returns 0 with headphone plugged |
| Glitch/XRUN | Only under DSP offload; host mode clean | Both host and offload glitch at same CPU load |
| SoundWire no slave | Link enabled; PING sent; no response | Bus scope shows no CLK on SDW lines |

---

## 9. Recommended Debug Sequence for "Audio Device Missing" (Quickref)

```
1. devmgmt.msc → is ACE PCI device present?
   NO  → config-checkout triage (BAR, PCI enumeration)
   YES ↓

2. Is Intel driver (IntcAudioBus) loaded or Microsoft HdAudio?
   HdAudio → driver install failure → check INF hardware ID vs DID
   IntcAudioBus ↓

3. Device Manager error code?
   Code 10 → driver failed to start → check WPP trace / Event Log
   Code 43 → driver self-reported error → check IPC timeout / FW load
   Code 28 → no driver → hardware ID mismatch (new DID)
   No error ↓

4. Is audio endpoint visible in Sound Settings?
   NO  → audiodg.exe issue → restart Windows Audio service
   YES → endpoint visible but wrong → APO or topology issue
```
