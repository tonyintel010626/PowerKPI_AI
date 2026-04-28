---
name: fv-audio/debug
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# FV-AUDIO Debug and Triage

> **Version**: 1.0.0 | **Date**: 2026-04-02
> **Template**: Modeled after fv-thc/debug (626 lines) — adapted for audio subsystem
> **Sources**: failure-analysis/SKILL.md, docs/audio_known_issues.md, docs/audio_reference_sheets.md, docs/audio_cheat_sheets.md

---

## Systematic Triage Flow

All audio failures follow this 4-phase triage methodology. Complete each phase before advancing.

### Phase 1: Identify Symptom Category

Classify the failure into one of these categories:

| Category | Symptoms | Severity |
|----------|----------|----------|
| **No Device** | DID=0xFFFF, device missing from PCI tree, BAR=0 | CRITICAL |
| **No Codec** | STATESTS=0, SoundWire slave not attached, HDA codec not detected | HIGH |
| **No Audio Output** | Stream configured but no sound, DMA not running, widget muted | HIGH |
| **Glitch/Dropout** | Audible artifacts, underrun/overrun, UAOL desync | MEDIUM |
| **PM Failure** | S0ix blocked by ACE, D3 entry fails, LTR not sent, clock gate stuck | HIGH |
| **FW Load Failure** | DSP boot timeout, IPC doorbell lost, SRAM PG race | HIGH |
| **Driver Crash** | BSOD in IntcAudioBus/IntcSmartSound, verifier failure | HIGH |
| **Intermittent** | Works sometimes, fails after PM cycle, temperature-dependent | MEDIUM |

### Phase 2: Check Basic Health

Run these 6 quick-checks before any deep debug:

| # | Check | Command / Method | Pass Criteria |
|---|-------|-----------------|---------------|
| 1 | **ACE device enumerated** | `lspci -d 8086:*` / Device Manager | ACE DID present (not 0xFFFF), class=0x0403 |
| 2 | **BARs allocated** | `lspci -v` / PythonSV `soc.ace.hdabar` | BAR0 (HDA) and BAR2 (DSP) non-zero, GPROCEN=1 |
| 3 | **Controller out of reset** | Read GCTL register | GCTL.CRST=1 (controller running) |
| 4 | **Codec/slave detected** | Read STATESTS (HDA) or SoundWire PING response | At least one codec/slave bit set |
| 5 | **DSP powered** | Read ADSPCS register | CPA (Core Power Active) bits set for target cores |
| 6 | **Driver loaded** | `dmesg \| grep snd` / Device Manager | No error codes, driver status = started |

If any check fails, that is your triage entry point — skip to the matching debug playbook below.

### Phase 3: Protocol-Level Debug

Based on Phase 2 results, enter the appropriate protocol-level debug:

| Failed Check | Protocol Debug Path | Sub-Skill Reference |
|-------------|--------------------|--------------------|
| Check 1 (No device) | PCI enumeration, BIOS knobs, fuses, reset architecture | [platform/](../platform/SKILL.md), [config-checkout/](../config-checkout/SKILL.md) |
| Check 2 (BAR=0) | BIOS knob GPROCEN, BAR assignment, MMIO conflict | [config-checkout/](../config-checkout/SKILL.md) |
| Check 3 (CRST=0) | Controller reset sequence, power domain, PMC state | [power/](../power/SKILL.md) |
| Check 4 (No codec) | HDA link, SoundWire bus enum, codec address, physical connection | [hda/](../hda/SKILL.md), [soundwire/](../soundwire/SKILL.md) |
| Check 5 (DSP off) | DSP core power sequence, SRAM PG, FW load path | [dsp/](../dsp/SKILL.md) |
| Check 6 (Driver err) | Driver stack, OS logs, verifier, ETW traces | (this file — Debug Tools section) |

### Phase 4: Root Cause and Resolution

| Root Cause Type | Action | Tracking |
|----------------|--------|----------|
| **RTL bug** | File sighting, apply HW workaround if available | HSDES sighting_central.sighting |
| **BIOS misconfiguration** | Correct BIOS knob, verify with `biosknob describe` | CONFIG-xxx classification |
| **FW bug** | Check FW version against BKC, try update | FW-xxx classification |
| **Driver bug** | Check driver version, collect ETW/WPP trace, file sighting | KERN-xxx classification |
| **Platform wiring** | Check schematic, GPIO pad mode, codec address straps | Hardware debug |
| **Intermittent/timing** | Stress test, collect VISA trace, check for known errata | Statistical analysis |

---

## Triage Interface — Structured Input → Hypothesis → Proposal

> **Purpose:** Formal contract for accepting failure data and returning a structured hypothesis + actionable proposal. Use this interface when triaging failures from NGA, Axon, HSDES, or user-reported symptoms.

### Accepted Inputs (any one or combination)

| Input Type | Example | Resolution |
|------------|---------|------------|
| **NGA Failure ID** | `47306b51-...` | Query NGA API → extract `debugSnapshotId` → Axon record |
| **Axon Record URL** | `https://axonsv.app.intel.com/apps/record-viewer/<uuid>/...` | Direct Axon retrieval |
| **HSDES Sighting ID** | `15019231307` | `hsdes.search_id()` → scan description/comments for Axon URLs |
| **Free-text symptom** | "No audio after S3 resume on NVL PCD-H" | Skip Axon enrichment, go to Phase 1 classification |

### Axon Enrichment (before Phase 1)

When an Axon record is available, extract audio-relevant evidence **before** classifying:

**Audio-Relevant Status Scope Registers:**

| Analyzer / IP | Registers to Check | What It Tells You |
|---------------|-------------------|-------------------|
| **ACE / Audio** | `PMCSR` (D-state), `CGCTL`, `PGCTL`, `ADSPCS` | Power state at failure — was ACE in D0/D3? DSP cores active? |
| **ACE / HDA** | `GCTL`, `STATESTS`, `INTSTS`, `CORBCTL`, `RIRBSTS` | Controller running? Codec detected? DMA stalled? |
| **ACE / SoundWire** | `SHIM.LCTL`, `SHIM.SYNC`, segment status | SDW links active? Clock stopped? |
| **PMC** | Reset cause register, S0ix blockers, LTR values | Was reset PMC-initiated? ACE blocking S0ix? |
| **PCIe / TCSS** | AER status (if UAOL path) | xHCI link errors affecting USB audio offload? |

**Axon Log Artifacts to Read:**

| Artifact | Audio-Relevant Content |
|----------|----------------------|
| Serial/BIOS log | ACE init messages, codec probe, DSP FW load, MRC (if boot stall) |
| Content Report | `audio_error.log`, `audio_debug.log` paths in solar_manager section |
| Crash dump | Check if audio driver (IntcAudioBus/IntcSmartSound) in stack |
| PMC trace | ACE power domain transitions, LTR, S0ix blocker signals |

**If no Axon record available:** Proceed directly to Phase 1 classification. Mark output with: *"[No Axon data — hypothesis based on symptom description only]"*

### Output Format — Triage Hypothesis & Proposal

Every triage MUST produce this structured output:

```
## Audio Triage Report

**Input:** <NGA ID / Axon URL / HSD ID / symptom description>
**Platform:** <NVL PCD-H / PTL / etc.>  **IFWI:** <version if known>

### Classification
- **Category:** <one of 8 from Phase 1 table>
- **Severity:** <CRITICAL / HIGH / MEDIUM / LOW>
- **Confidence:** <HIGH / MEDIUM / LOW — based on evidence quality>

### Evidence
- **Axon Status Scope:** <top anomaly registers + scores, or "N/A — no Axon">
- **Logs:** <key error lines from serial/content report, or "not available">
- **Known Sighting Match:** <HSD ID + title if match found, or "no match">

### Hypothesis
<1-2 sentences: what likely caused the failure and why>

### Proposed Next Steps
1. <first action — most likely to confirm/deny hypothesis>
2. <second action>
3. <third action if needed>

### Matching Playbook
<Playbook # from this file, or "none — custom debug path needed">
```

### Resolution Status

Every triage concludes with one of four formal statuses — always include in the Triage Report:

| Status | Criteria | Next Action |
|--------|----------|-------------|
| **✅ RESOLVED** | Root cause confirmed, fix applied and verified, failure no longer reproduces | File HSDES sighting if silicon bug; document workaround; close NGA failure |
| **🔶 PARTIALLY_RESOLVED** | Workaround applied, failure no longer reproduces, root cause not fully confirmed | Continue investigation in background; monitor for recurrence |
| **❌ UNRESOLVED** | Root cause unknown despite full triage; failure may still reproduce | Escalate to domain owner (`huiyingt`); file HSDES pre-sighting; attach all artifacts |
| **🔺 ESCALATED** | Requires HW debug (T2/VISA2/TLA/FTH), cross-team coordination, or RTL fix | Delegate to domain expert; provide complete triage report + all artifacts |

> Add `**Status:** <RESOLVED / PARTIALLY_RESOLVED / UNRESOLVED / ESCALATED>` at the bottom of every Triage Report output.

**Confidence Levels:**

| Level | Criteria |
|-------|----------|
| **HIGH** | Axon scandump anomaly score >0.8 on audio registers, OR exact sighting match, OR deterministic failure signature |
| **MEDIUM** | Partial Axon data + symptom match, OR similar sighting on same platform, OR reproducible but ambiguous |
| **LOW** | Symptom description only, no Axon/logs, no sighting match, intermittent/one-time |

---

## Common Failure Signatures

Quick-reference table mapping observed symptoms to likely causes and first debug actions.

| # | Symptom | Regex Pattern | Likely Cause | First Debug Action |
|---|---------|--------------|-------------|-------------------|
| 1 | DID reads 0xFFFF | `VID.*FFFF\|device.*not found` | ACE disabled in BIOS or fuse-disabled | Check BIOS knob `AudioController`, fuse `DSPSD[1]` |
| 2 | STATESTS=0 after CRST | `STATESTS.*0x0+\b\|no codec` | HDA link dead, codec not connected, wrong address | Check physical connection, codec address straps, BIOS `HdaVerbTableEnable` |
| 3 | SoundWire slave not attached | `sdw.*slave.*not\|sdw.*attach.*fail\|sdw.*timeout` | SDW link not enabled, clock stopped, address conflict | Check BIOS `SoundWireEnable`, SDW PING frame, link SHIM |
| 4 | DSP boot timeout | `ipc.*timeout\|firmware.*load.*fail\|dsp.*boot` | SRAM PG race on cold boot, FW image corrupt, IPC doorbell lost | Check ADSPCS.CPA, SRAM power sequence, FW binary integrity |
| 5 | BAR2 reads zero | `BAR2.*0x0+\b\|dsp.*bar.*null` | GPROCEN=0 in BIOS | Set BIOS knob `AudioDsp=Enabled`, verify GPROCEN bit |
| 6 | S0ix blocked by ACE | `s0ix.*block.*audio\|ace.*d0\|ltr.*audio` | ACE stuck in D0, LTR not sent, active stream/codec | Check `print_s0ix_y_blocking_conditions`, ACE D-state, active streams |
| 7 | UAOL dropout/glitch | `uaol.*underrun\|uaol.*overrun\|usb.*audio.*glitch` | FIFO timing, PSF glitch on DfSPSREQ, PM race | Check UAOL FIFO watermark, clean stream stop before PM (BUG-004 WA) |
| 8 | CORB/RIRB DMA stall | `corb.*err\|rirb.*timeout\|hda.*dma.*fail` | D3→D0 transition race (BUG-001), codec not responding | Full controller reinit after D3→D0, check codec power state |
| 9 | SSP BCLK lost | `ssp.*bclk\|i2s.*clock.*fail\|ssp.*no.*output` | BCLK inversion lost after PG exit (HSDES-003) | Reprogram BCLK after every PG exit, check GPIO pad mode |
| 10 | Display audio no sound | `idisp.*silent\|hdmi.*no.*audio\|dp.*audio.*fail` | Hot plug missed, ELD not read, iDisp codec not detected | Check hot plug event, STATESTS iDisp bits, ELD readback |
| 11 | DMIC no capture | `dmic.*silent\|dmic.*no.*data\|pdm.*fail` | GPIO pad mode wrong, PDM clock not running | Check GPIO pad mode (PMode), DMIC clock config, `DmicEnable` BIOS knob |
| 12 | BT offload blocking S0ix | `bt.*offload.*s0ix\|ssp.*bt.*block` | SSP stream not properly stopped before PM | Clean SSP stream teardown before S0ix entry (HSDES-006) |

---

## Debug Tools

### WPP Autologger (Windows ETW/WPP Tracing)

Primary Windows debug tool for audio driver stack tracing.

| Provider | Driver | GUID |
|----------|--------|------|
| IntcAudioBus.sys | HDA miniport bus driver | (per wiki 4251524533) |
| IntcSmartSound.sys | DSP/SOF driver | (per wiki 4251524533) |
| HDAudio.sys | Microsoft HDA class driver | (per wiki 4251524533) |
| IntcOED.sys | OED effects driver | (per wiki 4251524533) |

**Collection steps:**
```
1. Enable autologger: logman create trace AudioDebug -p {GUID} 0xFFFFFFFF 0xFF -ets
2. Reproduce failure
3. Stop trace: logman stop AudioDebug -ets
4. Decode: tracefmt -o output.txt AudioDebug.etl -p <TMF_path>
```

**Wiki reference**: Page 4251524533 has full provider GUIDs and TMF paths.

### VISA2 (On-Die Signal Trace)

For hardware-level signal observation when software logs are insufficient.

| Parameter | Value | Notes |
|-----------|-------|-------|
| DFX_NUM | 1 | Audio DFX instance |
| DFX_EARLYBOOT | 001b | Early boot capture enable |
| DFX_SECURE_POLICY | 69228A054319h | Security policy for audio VISA |

**When to use**: Intermittent failures, timing-dependent issues, signal integrity questions, PM transition glitches.

### DTF (Design-Time Firmware Trace)

Captures DSP firmware execution trace for FW-level debug.

| Parameter | Value | Notes |
|-----------|-------|-------|
| DTF_EN | 1 | Enable DTF |
| MSTID | 0x16 | Audio master ID |
| CHID0 | 0x01 | Channel 0 ID |
| CHID1 | 0x02 | Channel 1 ID |
| CHID2 | 0x03 | Channel 2 ID |
| CHID3 | 0x04 | Channel 3 ID |
| Timestamp shift | 6 bits | 38.4 MHz clock base |

**When to use**: DSP FW load failures, IPC timeout, pipeline stall, codec communication errors through DSP.

### sTAP (Sideband TAP)

For sideband fabric debug when audio IP communication with PMC/PCH fails.

| Parameter | Value | Notes |
|-----------|-------|-------|
| SSSTAPE | 0 | sTAP enable (0=enabled on some platforms) |
| IR length | 5-bit | Instruction register |
| TCK | ≤ 1/4 core clock | Maximum TAP clock rate |

**When to use**: PMC communication failures, power gating hangs, sideband timeout, CGPG stuck.

### PythonSV Quick Debug Commands

```python
# ACE device check
soc.ace.hdabar                           # HDA BAR address
soc.ace.cfg.vid                          # Vendor ID (should be 0x8086)
soc.ace.cfg.did                          # Device ID

# Controller state
soc.ace.hda.gctl                         # Global Control (CRST bit)
soc.ace.hda.statests                     # Codec status bits
soc.ace.hda.intctl                       # Interrupt control
soc.ace.hda.intsts                       # Interrupt status

# DSP state
soc.ace.dsp.adspcs                       # DSP core power/active status
soc.ace.dsp.adspic                       # DSP interrupt control
soc.ace.dsp.adspis                       # DSP interrupt status

# Power state
soc.ace.cfg.pmcs                         # PCI PM control/status (D-state)
soc.ace.ppctl                            # Power Policy Control
soc.ace.cgctl                            # Clock Gate Control

# SoundWire
soc.ace.sdw[N].shim.lctl                 # SDW link control
soc.ace.sdw[N].shim.sync                 # SDW sync control

# S0ix blocker check
fv_pm.initialize()
pm_tools.print_s0ix_y_blocking_conditions()
pm_tools.print_LTRs()
```

### OS-Level Debug Tools

**Linux:**
```bash
dmesg | grep -i 'snd\|sof\|hdaudio\|soundwire\|dmic'    # Kernel audio messages
lspci -vvv -d 8086:<DID>                                   # ACE PCI config
cat /proc/asound/cards                                      # ALSA card list
cat /sys/bus/soundwire/devices/*/status                     # SDW slave status
cat /sys/kernel/debug/sof/fw_debug                          # SOF FW debug
aplay -l                                                    # Playback devices
arecord -l                                                  # Capture devices
journalctl -k | grep -i audio                               # Persistent kernel logs
```

**Windows:**
```
Device Manager → Sound, video and game controllers          # Device status/error codes
Event Viewer → System → filter "HDAudio" or "IntcAudio"    # Driver events
pnputil /enum-drivers /class AudioEndpoint                  # Audio driver inventory
```

---

## Domain-Specific Debug Tools

### T2 (Trace2) — VISA Trace for NVL+

**What it does:** T2 is the next-generation VISA trace infrastructure replacing VISA2 on Nova Lake and later platforms. It captures internal IP signal activity (clock gating, state machine transitions, DMA handshakes) by routing selected observation signals to trace memory or an external trace port.

**When to use:** Internal state machine hangs, clock gating anomalies, DMA sequencing issues, power domain transitions, or any failure where register-level evidence is insufficient and you need cycle-level signal visibility.

**Workflow:**
1. **Select trace group** — Identify which ACE/Audio IP block to observe (DSP core, DMIC, SoundWire link, HDA controller, DMA engine)
2. **Configure T2 mux** — Route the desired observation signals through T2 multiplexers to the trace output
3. **Arm trigger** — Set trigger condition (e.g., specific register write, interrupt assertion, state transition)
4. **Reproduce failure** — Run the failing scenario while T2 captures
5. **Extract trace** — Read trace buffer from memory or external analyzer
6. **Decode** — Map captured signal values back to IP-internal states using the T2 decode tables

**Command Reference (PythonSV):**
```python
# T2 trace setup — NVL ACE Audio example
from pysvtools.t2 import T2

t2 = T2()
t2.configure(ip='ace_audio', trace_group='dsp_core0')   # Select IP and signal group
t2.set_trigger(signal='dsp_ipc_busy', edge='falling')    # Trigger on IPC completion
t2.arm()                                                  # Arm trace capture
# ... reproduce failure ...
t2.stop()                                                 # Stop capture
trace = t2.read_trace()                                   # Read trace buffer
t2.decode(trace, output='t2_ace_trace.csv')               # Decode to readable format
```

**Key signal groups for Audio:**
| Signal Group | Observes | Use When |
|---|---|---|
| `dsp_core0` / `dsp_core1` | DSP instruction flow, stalls, IPC | DSP hang, FW timeout |
| `hdaudio_link` | HDA CORB/RIRB, codec communication | Codec discovery failure, verb timeout |
| `soundwire_link0-3` | SDW bus frames, clock, data lanes | SDW enumeration failure, stream glitch |
| `dmic_ctrl` | DMIC PDM clock, FIFO state | DMIC capture silence, FIFO overrun |
| `dma_engine` | DMA channel state, descriptor fetch | DMA stall, buffer underrun |
| `power_ctrl` | Power well transitions, clock gating | D3/D0 transition hang, CGPG failure |

> **NOTE:** T2 is NVL+ only. For MTL/LNL/ARL, use VISA2 (see existing section above). For pre-MTL, use ITH/Northpeak.

---

### ITH / Northpeak — Intel Trace Hub (Pre-NVL)

**What it does:** Intel Trace Hub (ITH, also called Northpeak/North Peak) is a system-level trace aggregator that collects trace data from multiple sources (FW trace via DTF, SW trace via STH, HW trigger events) and routes them to memory (MTB — Memory Trace Buffer) or an external CTP (Common Trace Port) connector.

**When to use:** FW/driver trace correlation, multi-IP event sequencing, capturing SOF FW trace alongside driver ETW events, boot-time audio initialization failures.

**Workflow:**
1. **Enable ITH in BIOS** — Set `TraceHubEnable=1`, configure trace memory size
2. **Configure trace sources** — Select which masters/channels to capture (Audio DSP = specific master ID)
3. **Set trigger** — Optional: trigger on specific STP (System Trace Protocol) message
4. **Capture** — Run scenario; ITH writes STP packets to MTB or CTP
5. **Extract** — Read MTB from memory, or capture CTP output via external logic analyzer
6. **Decode** — Use Intel System Studio or `tracedecoder` to convert STP packets to human-readable trace

**Command Reference:**
```python
# ITH configuration via PythonSV
# Enable trace hub
soc.northpeak.msc0.mscctrl.wren = 1       # Enable MSC0 write
soc.northpeak.msc0.mscctrl.mode = 0        # Mode: memory buffer
soc.northpeak.gth.swdest0 = <master_map>   # Route Audio DSP master to MSC0

# Check ITH status
print(soc.northpeak.gth.scrpd0)            # Scratchpad — FW writes status here
```

**BIOS Knobs:**
```
TraceHubEnable = 1              # Enable Intel Trace Hub
TraceHubMemSize = 256MB         # Trace memory buffer size (adjust per need)
TraceHubFwEnable = 1            # Enable FW trace source
```

**Key trace masters for Audio:**
| Master ID | Source | Content |
|---|---|---|
| Audio DSP (platform-specific) | SOF/cAVS FW | FW log messages, IPC trace, pipeline state |
| PCH-P STH | Audio driver (Linux/Windows) | Driver-level STP messages |
| PMC | PMC FW | Power state transitions affecting audio IP |

> **NOTE:** ITH/Northpeak is available on MTL, LNL, ARL. On NVL+, T2 replaces most ITH use cases for IP-level trace, but ITH may still be available for FW-level trace aggregation.

---

### FTH — Fabric Trace Hub

**What it does:** FTH captures sideband fabric transactions — the internal message bus connecting IPs to PMC, PCH, and each other. For audio, this reveals power management sideband messages (D-state requests, clock gating handshakes, PMCLite commands) and configuration transactions.

**When to use:** Power management failures (D3 entry/exit hang, CGPG not gating, S0ix blocking), sideband timeout, IP reset sequencing issues, PMC-to-ACE communication failures.

**Workflow:**
1. **Identify sideband endpoint** — ACE Audio has a specific sideband port ID on the fabric
2. **Configure FTH filter** — Set source/destination filter to capture only Audio-related sideband traffic
3. **Arm capture** — FTH writes to dedicated trace memory
4. **Reproduce** — Trigger the PM transition or failure scenario
5. **Extract & decode** — Read FTH buffer, decode sideband message types (PM_REQ, PM_RSP, CFG_RD/WR, MSG)

**Command Reference (PythonSV):**
```python
# FTH capture for ACE Audio sideband transactions
# Filter by Audio sideband port ID (platform-specific)
soc.fth.filter.src_port = <ace_audio_port_id>    # Filter: source = ACE Audio
soc.fth.ctrl.enable = 1                           # Enable capture
# ... reproduce PM transition failure ...
soc.fth.ctrl.enable = 0                           # Stop capture
# Read trace buffer
for i in range(soc.fth.status.entries):
    entry = soc.fth.buffer[i]
    print(f"  {entry.timestamp:#x}  {entry.msg_type}  {entry.src}->{entry.dst}  data={entry.data:#x}")
```

**Key sideband messages for Audio debug:**
| Message Type | Direction | Meaning |
|---|---|---|
| `PM_REQ (D3)` | ACE → PMC | Audio IP requesting D3 entry |
| `PM_RSP (D3_ACK)` | PMC → ACE | PMC acknowledging D3 — power gate allowed |
| `PM_REQ (D0)` | ACE → PMC | Audio IP requesting D0 resume |
| `CGPG_EN` | PMC → ACE | Clock/power gating enable |
| `RESET_PREP` | PMC → ACE | Reset preparation handshake |
| `SIDEBAND_TIMEOUT` | (error) | Sideband transaction timeout — indicates hang |

> **Cross-reference:** If FTH shows `SIDEBAND_TIMEOUT`, delegate to **YC_debugger** for full platform sideband/PMC analysis. If `PM_RSP` is missing after `PM_REQ`, the issue is likely PMC-side — check PMC FW trace.

---

### TLA — Tektronix Logic Analyzer

**What it does:** External logic analyzer for capturing real-time bus signals — I2S/TDM bit streams, SoundWire bus frames, SPI codec register traffic, GPIO transitions, and clock signals. Provides cycle-accurate timing and protocol decode.

**When to use:** Signal integrity issues, protocol violations, clock jitter/drift, bit errors on I2S/SoundWire/SPI bus, GPIO timing verification, external codec communication failures.

**Workflow:**
1. **Connect probes** — Attach TLA probes to target signals on the board (I2S BCLK/LRCLK/SDATA, SDW CLK/DATA, SPI CLK/MOSI/MISO/CS#, relevant GPIOs)
2. **Configure protocol decode** — Select protocol analyzer module (I2S, SPI, or custom for SoundWire)
3. **Set trigger** — Trigger on protocol event (e.g., SPI transaction start, I2S frame sync edge, GPIO assertion)
4. **Set sample rate** — Must be ≥4× the highest signal frequency (e.g., ≥192 MHz for 48 MHz SoundWire clock)
5. **Capture** — Run scenario, TLA captures bus activity
6. **Analyze** — Use TLA software for protocol decode, timing measurements, signal integrity checks

**Signal Mapping for Audio:**
| Signal | Typical Probe Point | Protocol | Use Case |
|---|---|---|---|
| I2S BCLK, LRCLK, SDATA_OUT, SDATA_IN | SSP/I2S header or test points | I2S/TDM | BT Audio Offload, external codec |
| SDW CLK, DATA0-3 | SoundWire connector or test pads | SoundWire | AIOC, external SDW codec |
| SPI CLK, MOSI, MISO, CS# | SPI header | SPI | External codec register access |
| DMIC CLK, DMIC DATA | DMIC connector | PDM | DMIC capture issues |
| GPIO (PROCHOT, WAKE#, INT#) | GPIO header | Digital | Interrupt timing, wake triggers |

**Key measurements:**
- **Clock jitter**: Measure BCLK/SDW CLK period stability — jitter >2% can cause audible artifacts
- **Setup/hold timing**: Verify data transitions vs clock edges meet spec
- **Frame sync alignment**: I2S LRCLK edge-to-data timing
- **SoundWire frame structure**: Verify control/data word boundaries, parity bits
- **GPIO pulse width**: Verify interrupt assertion duration meets minimum

> **TIP:** For SoundWire bus analysis, the TLA may need a custom protocol decoder — standard I2C/SPI decoders won't work. Check if your TLA model has a SoundWire decode option, or use raw digital capture and post-process.

---

### SOCWATCH — Power Profiling

**What it does:** System-level power and performance monitoring tool that captures C-state residency, P-state transitions, D-state changes, wake events, and LTR values over time. For audio, it reveals whether audio IP power management is working correctly and whether audio is blocking platform-level low-power states.

**When to use:** Audio IP blocking S0ix/PkgC, unexpected D-state behavior, LTR misconfiguration, audio power consumption analysis, verifying audio IP enters D3 during idle.

**Workflow:**
1. **Install SOCWATCH** on the target system (Windows or Linux)
2. **Configure collection** — Select audio-relevant metrics (device D-states, S0ix residency, LTR, wake sources)
3. **Run scenario** — Capture during idle (expect D3/S0ix) or during playback (expect D0)
4. **Analyze results** — Check if audio devices enter expected D-states, check LTR values, identify S0ix blockers

**Command Reference:**
```bash
# Linux — capture audio PM behavior during 60s idle
socwatch -f sys-overview -t 60 -o audio_pm_results
# Captures: C-states, D-states, S-states, LTR, wake events

# Linux — focused audio D-state tracking
socwatch -f device-dstate -t 30 -o audio_dstate
# Shows per-device D-state residency over time

# Windows — equivalent
socwatch.exe -f sys-overview -t 60 -o audio_pm_results
```

**What to look for in SOCWATCH output:**
| Metric | Expected (idle) | Expected (playback) | Problem Indicator |
|---|---|---|---|
| ACE Audio D-state | D3 | D0 | Stuck in D0 during idle → blocks S0ix |
| ACE Audio LTR | High (≥10ms) or no-requirement | Low (~1-3ms) | LTR too low during idle → blocks PkgC |
| PkgC residency | PkgC8+ >90% | PkgC2-6 typical | 0% PkgC → audio likely blocking |
| S0ix residency | >90% (screen off) | N/A (screen on) | 0% → check audio D-state and LTR |
| Wake events | Rare | Periodic (DMA IRQ) | Excessive wakes during idle |

> **Cross-reference:** If SOCWATCH shows audio blocking S0ix, delegate to **FV-IdlePM** or **FV-PM-SOUTH** for full platform PM analysis. Audio-side fix: verify D3 entry, check LTR configuration in DSP FW, verify CGPG is enabled.

---

### Oscilloscope — Signal Integrity

**What it does:** Time-domain analog signal measurement for verifying voltage levels, rise/fall times, clock frequency accuracy, signal integrity (overshoot, undershoot, ringing), and power rail stability. Complements the logic analyzer (digital) with analog-domain visibility.

**When to use:** Clock frequency verification, I2S/SoundWire signal quality issues, power rail noise causing audio artifacts, codec power-up sequencing, MCLK accuracy measurement, analog audio output quality (if DAC present).

**Workflow:**
1. **Connect probe** — Use appropriate probe (passive for >1V signals, active for high-speed clocks)
2. **Set bandwidth/sample rate** — ≥5× highest frequency of interest
3. **Capture** — Single-shot or continuous depending on scenario
4. **Measure** — Use built-in measurement tools for frequency, duty cycle, rise time, amplitude, jitter

**Key Audio Measurements:**
| Signal | Expected | Tolerance | Failure Indicator |
|---|---|---|---|
| MCLK frequency | 19.2 MHz or 24.576 MHz (platform-dependent) | ±50 ppm | Wrong frequency → wrong sample rate, pitch shift |
| I2S BCLK | N × Fs (e.g., 3.072 MHz for 48kHz/32bit/2ch) | ±100 ppm | Clock drift → sample slip, glitches |
| SDW CLK | 4.8 / 9.6 / 12.0 / 24.0 MHz | Per SoundWire spec | Wrong gear → enumeration failure |
| BCLK duty cycle | 50% | ±5% | Skewed duty cycle → setup/hold violation |
| Rise/fall time | <2ns for >10 MHz clocks | Per bus spec | Slow edges → signal integrity failure |
| VCC_AUDIO power rail | 1.8V or 3.3V (codec-dependent) | ±5% | Droop/noise → codec malfunction |
| Power-up sequencing | VCC stable before RESET# deassert | Per codec datasheet | Sequence violation → codec stuck |

> **TIP:** For intermittent audio glitches (pops, clicks, dropouts), use oscilloscope persistence mode on BCLK/LRCLK to catch occasional clock glitches. Set trigger on clock period violation.

---

## HSDES Sighting Database

### Filing BKM

| Field | Value |
|-------|-------|
| **Tenant** | client_platf_i_val |
| **Domain** | functional_validation |
| **Component** | audio, ace, hda, soundwire, dsp, dmic, uaol (pick most specific) |
| **Title format** | `[PLATFORM] Audio <subsystem>: <symptom>` |
| **Example** | `[NVL PCD-H] Audio SoundWire: Slave not attached after S3 resume on Seg4` |

### Classification Prefixes

Use these prefixes when documenting issues in sighting descriptions:

| Prefix | Meaning | Example |
|--------|---------|---------|
| BUG-xxx | RTL/silicon bug | BUG-001: CORB/RIRB DMA stall on D3→D0 |
| HSDES-xxx | Filed HSDES sighting | HSDES-001: S0ix blocked ACE stuck D0 |
| CONFIG-xxx | BIOS/platform misconfiguration | CONFIG-001: ACE disabled DID=0xFFFF |
| KERN-xxx | OS/kernel fix needed | Linux kernel audio driver fix |
| FW-xxx | Firmware bug | FW-001: SOF FW load timeout cold boot |

### HSDES Search Keywords by Subsystem

| Subsystem | Search Keywords |
|-----------|----------------|
| HDA | `hda codec verb CORB RIRB STATESTS GCTL` |
| SoundWire | `soundwire sdw slave attach PING clock stop` |
| DSP/SOF | `dsp sof firmware ipc adspcs sram boot` |
| DMIC | `dmic pdm microphone privacy gpio` |
| Display Audio | `idisp display hdmi dp audio hotplug ELD` |
| UAOL | `uaol usb audio offload fifo underrun` |
| SSP/I2S | `ssp i2s bclk bt offload bluetooth` |
| Power | `s0ix d3 ltr clock gate power ace cgpg` |
| AIOC | `aioc alc712 alc1320 5star codec` |

### Useful Wiki References

| Platform | Wiki Page ID | Content |
|----------|-------------|---------|
| LNL Audio | 3051461460 | LNL audio debug notes |
| MTL Debug | 2942039705 | MTL audio debug procedures |
| MTL Traces | 2638580577 | MTL audio trace collection |
| PTL FW Log | 3484618181 | PTL firmware logging |
| PTL Xtensa | 3516740381 | PTL Xtensa DSP debug |
| NVL Handbook | 4153877501 | NVL audio handbook |
| NVL BT | 4278948453 | NVL BT audio offload |
| WPP Setup | 4251524533 | WPP autologger provider GUIDs |

---

## Known Bugs and Errata

> **⚠️ Note on IDs**: The `HSDES-xxx` and `BUG-xxx` identifiers below are **illustrative cross-reference labels** used within this skill for internal triage consistency. They are **not** real HSDES sighting numbers. When filing or referencing actual sightings, always use the numeric HSDES ID (e.g., `16012345678`) obtained from the HSDES system.

### RTL/Silicon Bugs

| ID | Title | Platform | Scope | Root Cause | Workaround |
|----|-------|----------|-------|-----------|------------|
| BUG-001 | CORB/RIRB DMA stall on D3→D0 | NVL PCD-H A0 | HDA | DMA engine not fully reinitialized after D3→D0 power transition | Full controller reinit (CRST toggle + CORB/RIRB re-setup) after every D3→D0 |
| BUG-002 | SoundWire bus reset fails on Seg4 (on-die iDisp) | NVL PCD-H | SDW | Alt function registers not cleared before bus reset | Disable alt functions first, then issue bus reset |
| BUG-003 | DSP Core 3/4 fail to wake from clock gate | NVL PCD-H only | DSP | Clock gate exit timing insufficient for cores 3/4 | Sequence core wakes with 1ms delay between each core |
| BUG-004 | UAOL PSF glitch on DfSPSREQ | MTL, PTL, NVL | UAOL | PSF sideband request glitch during PM transition | Clean stream stop before any PM transition |
| BUG-005 | UAOL behind-hub broken | MTL only | UAOL | Hub routing logic bug in MTL silicon | No WA on MTL; fixed in PTL+ |

### Active HSDES Sightings

| ID | Title | Platform | Subsystem | Status | Impact |
|----|-------|----------|-----------|--------|--------|
| HSDES-001 | S0ix blocked — ACE stuck in D0 | All | Power | Open | ACE fails to enter D3, blocks platform S0ix |
| HSDES-002 | SDW clock stop abort in multi-drop | NVL, PTL | SoundWire | Open | Clock stop fails when multiple slaves on link |
| HSDES-003 | SSP BCLK inversion lost after PG exit | NVL PCD-S, PTL | SSP/I2S | Open | BT offload audio corrupted after power gate exit |
| HSDES-004 | HDA hot plug missed on DP Port 3 | NVL PCD-H | Display Audio | Open | Third DP port hot plug event not detected |
| HSDES-005 | AIOC ALC712 not enumerated on Seg2 | NVL 5-Star | AIOC | Open | All-in-one codec fails to appear on SoundWire Segment 2 |
| HSDES-006 | BT offload blocking S0ix | NVL, PTL | SSP/BT | Open | SSP stream for BT not torn down before S0ix entry |

### Common Misconfigurations

| ID | Title | Symptom | Root Cause | Fix |
|----|-------|---------|-----------|-----|
| CONFIG-001 | ACE disabled in BIOS | DID=0xFFFF | `AudioController=Disabled` | Set `AudioController=Enabled` |
| CONFIG-002 | DSP BAR not enabled | BAR2=0, no DSP access | `AudioDsp=Disabled` (GPROCEN=0) | Set `AudioDsp=Enabled` |
| CONFIG-003 | SoundWire link not enabled | No SDW slaves detected | `SoundWireEnable=Disabled` | Set `SoundWireEnable=Enabled` for target links |
| CONFIG-004 | Wrong codec address (HDA) | STATESTS bit mismatch | Codec address straps on board don't match BIOS verb table | Verify schematic codec address pins vs BIOS configuration |
| CONFIG-005 | DMIC GPIO pad mode wrong | DMIC silent, no PDM clock | GPIO pads not set to native DMIC function | Set correct PMode for DMIC_CLK and DMIC_DATA pads |
| CONFIG-006 | Clock gate stuck (FNCFG.CGD) | Device unresponsive, registers return 0 | CGD bit set preventing clock ungate | Clear FNCFG.CGD, check for upstream power domain issue |

### Firmware Issues

| ID | Title | Platform | Root Cause | Workaround |
|----|-------|----------|-----------|------------|
| FW-001 | SOF FW load timeout on cold boot | All | SRAM power gate race — SRAM not ready when FW load starts | Add delay after SRAM PG exit, verify ADSPCS.CPA before FW load |
| FW-002 | IPC doorbell lost on D0i3 exit | All | IPC doorbell register not restored after D0i3 exit | Re-trigger IPC doorbell after every D0i3→D0 transition |
| FW-003 | DMIC xosc_clk 38.4MHz PDM clock | All | Wrong clock source selected for PDM interface | Configure correct clock source in DSP FW NHLT table |

---

## Debug Playbooks

### Playbook 1: Device Not Enumerating (DID=0xFFFF)

**Symptom**: ACE device not visible in PCI tree, or DID reads 0xFFFF.

**Typical root causes**: BIOS disabled, fuse-disabled, reset stuck, power domain off.

| Step | Action | Register / Tool | Expected | If Wrong |
|------|--------|----------------|----------|----------|
| 1 | Check BIOS knob | `biosknob describe AudioController` | Enabled | Set to Enabled, reboot |
| 2 | Check fuse | `fuse DSPSD[1]` via PythonSV | 0 (not disabled) | Fuse-disabled part — cannot fix, need different SKU |
| 3 | Check fuse SSKUID | `fuse SSKUID[15:8]` | Matches expected audio SKU | Wrong SKU — verify part marking |
| 4 | Check ACE power domain | PMC power gate status for ACE | ACE domain powered | Check PMC, may need PMC FW update |
| 5 | Check reset | `soc.ace.cfg.vid` via PythonSV | 0x8086 | ACE still in reset — check reset sequence via [platform/](../platform/SKILL.md) |
| 6 | Check PCI scan | `lspci -d 8086:*` or PythonSV `pcicfg()` | ACE BDF present | BIOS not scanning ACE bus — check BIOS PCI enumeration |

**If all pass but device still missing**: Check for MMIO conflict, verify ACE BDF matches platform spec in [platform/SKILL.md](../platform/SKILL.md).

### Playbook 2: SoundWire Slave Not Detected

**Symptom**: SoundWire link active but no slave devices attached, PING frames get no response.

**Typical root causes**: Link not enabled, clock stopped, address conflict, physical connection.

| Step | Action | Register / Tool | Expected | If Wrong |
|------|--------|----------------|----------|----------|
| 1 | Check BIOS knob | `biosknob describe SoundWireEnable` | Enabled for target link(s) | Enable in BIOS, reboot |
| 2 | Check link state | `soc.ace.sdw[N].shim.lctl` | Link powered and running | Check SDW SHIM power/clock config |
| 3 | Check PING response | SDW bus trace or `soc.ace.sdw[N].shim.sync` | At least one slave responds | No slave on bus — check physical connection, codec power |
| 4 | Check slave address | SDW device address in ACPI/NHLT | Matches hardware straps | Address mismatch — verify schematic vs BIOS |
| 5 | Check multi-drop | Multiple slaves on same link | All slaves unique addresses | Address conflict — see HSDES-002 for multi-drop issues |
| 6 | Check Segment | Correct SDW segment for device | Device on expected segment (Seg0-4) | Wrong segment config — see BUG-002 for Seg4 iDisp issues |

**Platform-specific note (NVL 5-Star)**: AIOC ALC712 on Seg2 — see HSDES-005 if enumeration fails.

### Playbook 3: DSP Firmware Load Timeout

**Symptom**: DSP firmware fails to load, IPC timeout, DSP cores not active.

**Typical root causes**: SRAM PG race, FW image corrupt, IPC doorbell lost, core power sequence.

| Step | Action | Register / Tool | Expected | If Wrong |
|------|--------|----------------|----------|----------|
| 1 | Check DSP BAR | `soc.ace.dsp.bar` or `lspci -v` BAR2 | Non-zero, GPROCEN=1 | Set `AudioDsp=Enabled` in BIOS (CONFIG-002) |
| 2 | Check core power | `soc.ace.dsp.adspcs` CPA bits | CPA=1 for target cores | Core not powered — check power sequence, PMC |
| 3 | Check SRAM ready | SRAM power gate status | SRAM powered and stable | SRAM PG race — add delay (FW-001), retry |
| 4 | Verify FW binary | Check FW file integrity, version | FW matches BKC version | Update FW, check FW binary path |
| 5 | Check IPC | `soc.ace.dsp.adspic` / IPC doorbell | IPC doorbell responsive | IPC lost — see FW-002, retrigger doorbell |
| 6 | Check core wake | ADSPCS per-core status for cores 3/4 | All target cores CPA=1 | Cores 3/4 clock gate bug — see BUG-003, sequence with 1ms delay |

**DSP FW debug tools**: Use DTF trace (MSTID=0x16) for firmware execution trace. PTL Xtensa debug via wiki page 3516740381.

### Playbook 4: S0ix Blocked by ACE

**Symptom**: Platform cannot enter S0ix, audio/ACE identified as blocker.

**Typical root causes**: ACE stuck in D0, active stream not stopped, LTR not sent, codec holding link.

| Step | Action | Register / Tool | Expected | If Wrong |
|------|--------|----------------|----------|----------|
| 1 | Check S0ix blockers | `pm_tools.print_s0ix_y_blocking_conditions()` | ACE not listed | ACE is blocking — continue below |
| 2 | Check ACE D-state | `soc.ace.cfg.pmcs` bits [1:0] | D3 (value=3) | Stuck in D0 — check what holds it active |
| 3 | Check active streams | HDA stream descriptors, SDW stream status | All streams stopped | Active stream — ensure all audio stopped before PM |
| 4 | Check LTR | `pm_tools.print_LTRs()` | ACE LTR = no requirement | ACE LTR active — driver not releasing LTR |
| 5 | Check codec state | HDA codec power state, SDW slave PM | All codecs in D3/ClockStop | Codec holding link — check driver PM sequence |
| 6 | Check clock gate | `soc.ace.cgctl` / FNCFG.CGD | Clock gate enabled | CGD stuck — see CONFIG-006, check power domain |
| 7 | Check BT offload | SSP stream status for BT link | SSP idle if BT not active | SSP stream blocking — see HSDES-006, clean teardown |

**S0ix debug priority chain** (debug in this order): ACE D-state → Active streams → LTR → Codec PM → Clock gate → DSP idle → SRAM PG.

### Playbook 5: UAOL Audio Dropout/Glitch

**Symptom**: USB audio offload has audible glitches, underruns, or overruns during playback/capture.

**Typical root causes**: FIFO timing, PSF glitch during PM, behind-hub routing, xHCI interaction.

| Step | Action | Register / Tool | Expected | If Wrong |
|------|--------|----------------|----------|----------|
| 1 | Check UAOL support | Platform data in [platform/SKILL.md](../platform/SKILL.md) | UAOL supported on this platform | MTL: behind-hub broken (BUG-005); LNL/ARL: internal UAOL only (no behind-hub) |
| 2 | Check FIFO status | UAOL FIFO watermark registers | No underrun/overrun flags | FIFO timing issue — check watermark config |
| 3 | Check stream state | UAOL stream descriptor status | Stream running, no errors | Stream error — check xHCI endpoint state |
| 4 | Check PM interaction | UAOL state during PM transition | Clean stop before PM | PSF glitch — apply BUG-004 WA: stop stream before PM |
| 5 | Check hub topology | USB device behind hub? | Direct connection or hub-aware path | Behind-hub broken on MTL (BUG-005), works PTL+ |
| 6 | Collect ETW trace | WPP autologger for IntcSmartSound.sys | Trace shows dropout point | Analyze trace for timing/sequencing error |

**Platform notes**: UAOL availability by platform: NVL=full (ACE4.x), PTL=supported (ACE3.0), MTL=limited/broken behind-hub (ACE1.5), LNL=internal only (ACE2.x), ARL=internal only (ACE1.5).

---

## Debug Script Development

### Debug Script Templates

Debug scripts differ from test scripts: they **read state, analyze, and report** rather than execute test flows. Two canonical templates cover most debug scripting needs.

> **Platform-specific paths**: The example register paths below use `soc.ace.bar0.*` (NVL PCD-H convention). Paths vary by platform and die type:
> - **NVL PCD-H**: `soc.ace.bar0.hda.*`, `soc.ace.bar2.dsp.*`
> - **NVL PCD-S**: `soc.pch.ace.bar0.*` (PCD-S die hosts ACE on S-die variants)
> - **PTL / LNL / MTL**: Check `fv-audio/platform` for the correct base path — namednodes tree differs per generation.
>
> Always verify paths with `namednodes.show("*ace*")` in PythonSV CLI before adding them to a script.

> **Safety note on `eval()`**: Both templates use `eval(path)` to read PythonSV namednodes at runtime. This is the standard interactive pattern in PythonSV CLI. However: (1) never pass user-supplied or untrusted strings into these templates — only use paths from namednodes or sub-skill documentation, (2) if adapting these templates for use outside PythonSV CLI (e.g. in a standalone Python environment), replace `eval()` with the appropriate PythonSV API call (e.g. `namednodes.read(path)`).

#### Template 1: Register Dump Script

Use when you need to capture a snapshot of audio subsystem state for analysis or comparison.

```python
"""
AUDIO_<SUBSYS>_DUMP_<BRIEF>.py — Register dump for <subsystem>
Usage: Run in PythonSV CLI after loading namednodes
"""
import sys
import json
from datetime import datetime

# === CONFIGURATION (edit this section only) ===
SUBSYSTEM = "<hda|sdw|dsp|dmic|ssp|uaol>"
DESCRIPTION = "<what this dump captures>"
REGISTERS = {
    # "friendly_name": ("pythonsv_path", "expected_or_note"),
    "GCTL":      ("soc.ace.bar0.hda.gctl",       "bit0=CRST should be 1"),
    "STATESTS":  ("soc.ace.bar0.hda.statests",    "bit per codec detected"),
    # Add registers relevant to your subsystem...
}

# === DUMP ENGINE (do not modify) ===
def dump_registers(regs: dict) -> dict:
    results = {}
    for name, (path, expected) in regs.items():
        try:
            val = eval(path)
            results[name] = {
                "path": path, "value": val,
                "hex": hex(val) if isinstance(val, int) else str(val),
                "expected": expected, "status": "OK"
            }
        except Exception as e:
            results[name] = {
                "path": path, "value": None, "hex": "ERROR",
                "expected": expected, "status": f"READ_FAIL: {e}"
            }
    return results

def print_report(results: dict):
    print(f"\n{'='*60}")
    print(f"  AUDIO DEBUG DUMP — {SUBSYSTEM.upper()}")
    print(f"  {DESCRIPTION}")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*60}")
    for name, info in results.items():
        flag = "X" if info["status"] != "OK" else " "
        print(f"  [{flag}] {name:20s} = {info['hex']:12s}  ({info['expected']})")
    errors = [n for n, i in results.items() if i["status"] != "OK"]
    print(f"\n  Total: {len(results)} registers, {len(errors)} errors")
    if errors:
        print(f"  ERRORS: {', '.join(errors)}")

if __name__ == "__main__":
    results = dump_registers(REGISTERS)
    print_report(results)
    # Optional: save JSON for diff/comparison
    # with open(f"dump_{SUBSYSTEM}_{datetime.now():%Y%m%d_%H%M%S}.json", "w") as f:
    #     json.dump(results, f, indent=2)
```

**Customization**: Edit `REGISTERS` dict only. Add subsystem-specific registers from the relevant sub-skill (hda/, soundwire/, dsp/, etc.).

#### Template 2: Diagnostic / Triage Script

Use when you need to check health, detect anomalies, and produce a pass/fail assessment.

```python
"""
AUDIO_<SUBSYS>_DIAG_<BRIEF>.py — Diagnostic check for <subsystem>
Usage: Run in PythonSV CLI after loading namednodes
"""
import sys

# === CONFIGURATION (edit this section only) ===
SUBSYSTEM = "<hda|sdw|dsp|dmic|ssp|uaol>"
DESCRIPTION = "<what this diagnostic checks>"

# Each check: (name, expression_str, pass_condition_fn, fail_message)
CHECKS = [
    (
        "ACE Device Present",
        "soc.ace.cfg.vid",
        lambda val: val == 0x8086,
        "ACE VID != 0x8086 — device not enumerated"
    ),
    (
        "BAR0 Allocated",
        "soc.ace.cfg.bar0",
        lambda val: val is not None and val != 0,
        "BAR0 is 0 or None — BIOS did not allocate BAR"
    ),
    (
        "Controller Reset Done",
        "soc.ace.bar0.hda.gctl",
        lambda val: val is not None and (val & 1) == 1,
        "GCTL.CRST=0 — controller still in reset"
    ),
    # Add subsystem-specific checks...
]

# === DIAGNOSTIC ENGINE (do not modify) ===
def run_checks(checks: list) -> list:
    results = []
    for name, expr, pass_fn, fail_msg in checks:
        try:
            val = eval(expr)
            passed = pass_fn(val)
            results.append({
                "name": name, "value": val,
                "hex": hex(val) if isinstance(val, int) else str(val),
                "passed": passed,
                "message": "" if passed else fail_msg
            })
        except Exception as e:
            results.append({
                "name": name, "value": None, "hex": "ERROR",
                "passed": False, "message": f"READ_FAIL: {e}"
            })
    return results

def print_diagnosis(results: list):
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    status = "PASS" if passed == total else "FAIL"

    print(f"\n{'='*60}")
    print(f"  AUDIO DIAGNOSTIC — {SUBSYSTEM.upper()}: {status}")
    print(f"  {DESCRIPTION}")
    print(f"  Result: {passed}/{total} checks passed")
    print(f"{'='*60}")
    for r in results:
        icon = "+" if r["passed"] else "X"
        print(f"  [{icon}] {r['name']:30s} = {r['hex']}")
        if not r["passed"]:
            print(f"       -> {r['message']}")
    print()
    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    results = run_checks(CHECKS)
    sys.exit(print_diagnosis(results))
```

**Customization**: Edit `CHECKS` list only. Each check is `(name, PythonSV expression, pass condition lambda, failure message)`.

### Script Restructuring Checklist

When converting an existing ad-hoc debug script into a maintainable format:

1. **Identify script type** — Register dump or diagnostic check? Pick the matching template above.
2. **Extract register paths** — Move all hardcoded register accesses into `REGISTERS` or `CHECKS` at the top.
3. **Remove inline prints** — Replace scattered `print()` calls with the template's report engine.
4. **Add error handling** — Wrap reads in try/except (templates do this automatically).
5. **Name it** — Follow convention: `AUDIO_<SUBSYS>_DUMP|DIAG_<BRIEF>.py`
6. **Test** — Run once in PythonSV CLI, verify output matches expected format.

---

## Cross-Platform Recurring Patterns

Issues that appear across multiple platform generations:

| # | Pattern | Platforms Affected | Root Cause | Standard WA |
|---|---------|-------------------|-----------|-------------|
| 1 | S0ix blocked by ACE | All | Driver PM sequence incomplete | Ensure full D3 entry + LTR release before S0ix |
| 2 | DSP FW load timeout on cold boot | All | SRAM PG exit race | Delay after SRAM PG exit, verify CPA before FW load |
| 3 | IPC doorbell lost after D0i3 | All | IPC state not preserved across D0i3 | Retrigger doorbell after D0i3 exit |
| 4 | DMIC wrong clock source | All | NHLT table clock mismatch | Verify xosc_clk vs PDM clock in NHLT |
| 5 | UAOL PSF glitch during PM | MTL, PTL, NVL | PSF sideband timing | Stop stream cleanly before PM transition |
| 6 | SSP BCLK lost after PG | NVL, PTL | PG exit doesn't restore BCLK inversion | Reprogram BCLK config after every PG exit |
| 7 | HDA codec not detected post-reset | Multi-gen | CRST timing too short | Extend CRST assertion time, add delay before STATESTS read |
| 8 | Clock gate prevents register access | Multi-gen | FNCFG.CGD set unexpectedly | Clear CGD before register access, check power domain |
| 9 | Display audio hot plug race | Multi-gen | Hot plug event lost during link transition | Poll STATESTS after link state change |

---

## Platform-Specific Debug Notes

### NVL (Novalake)

- **ACE version**: ACE4.x — full feature set including UAOL, AIOC
- **Die types**: PCD-H (compute die), PCH-S (PCH die) — check which die hosts the failing IP
- **BUG-001 scope**: CORB/RIRB DMA stall is NVL PCD-H A0 only — check stepping
- **BUG-003 scope**: DSP Core 3/4 wake issue is NVL PCD-H only
- **AIOC (5-Star)**: ALC712/ALC1320 on SoundWire — see [aioc/SKILL.md](../aioc/SKILL.md) and HSDES-005
- **BT audio**: See wiki page 4278948453 for NVL BT offload specifics
- **Handbook**: Wiki page 4153877501

### PTL (Panther Lake)

- **ACE version**: ACE3.x+ — UAOL supported, no AIOC
- **HSDES-003**: SSP BCLK inversion issue active on PTL
- **HSDES-006**: BT offload S0ix blocking active on PTL
- **FW debug**: Use Xtensa debug per wiki page 3516740381
- **FW logging**: PTL FW log collection per wiki page 3484618181

### LNL (Lunar Lake)

- **ACE version**: ACE2.0 — **no UAOL support**
- **Limited feature set**: No UAOL, no AIOC, simpler topology
- **Audio debug**: Wiki page 3051461460
- **S0ix debug**: Focus on basic ACE D3/LTR since fewer subsystems

### MTL (Meteor Lake)

- **ACE version**: ACE3.x — UAOL limited
- **BUG-005**: UAOL behind-hub is **broken on MTL** — no workaround, fixed PTL+
- **BUG-004**: UAOL PSF glitch active on MTL
- **Debug**: Wiki pages 2942039705 (debug), 2638580577 (traces)
- **Die types**: SOC-M (SoC die), PCH-S (PCH die)

### ARL (Arrow Lake)

- **Similar to MTL**: Same ACE generation, similar bug landscape
- **Cross-reference MTL issues** when debugging ARL

### WCL (Wildcat Lake)

- **ACE version**: ACE 3.0 — same architecture as PTL
- **Debug approach**: Apply PTL debug procedures first. If WCL-specific behavior differs, check WCL erratum list.
- **DSP cores**: 5 LX7 + HiFi4 + ANNA — same core topology as PTL
- **SoundWire**: 5 links v1.2 — same configuration as PTL
- **Die path**: `socket0.soc.ace` — differs from NVL (`socket0.pcd.ace`)
- **No AIOC**: ACE 3.0 does not include AIOC hardware. If AIOC-related tests fail, they are expected to fail (not applicable).
- **UAOL**: Supported via ACE 3.0 offload engine (smaller FIFO than NVL ACE 4.x). Apply PTL UAOL debug procedures.
- **Known PTL issues apply**: HSDES-003 (SSP BCLK inversion), HSDES-006 (BT offload S0ix blocking) likely apply to WCL — verify against WCL sighting list.
- **FW debug**: Same Xtensa debug methodology as PTL (wiki page 3516740381)

### TTL (Titan Lake)

- **ACE version**: Dual-ACE platform — ACE 4.0 **or** ACE 3.0 (fuse-selected per SKU)
- **Debug approach**: Detect ACE variant first, then route accordingly:
  - **ACE 4.0** (4 HiFi5 cores): Apply NVL PCD-H debug procedures
  - **ACE 3.0** (5 LX7+HiFi4 cores): Apply PTL debug procedures
- **Variant detection**: Read `ADSPCS` register — count enabled DSP cores to determine ACE variant:
  ```
  ACE 4.0: ADSPCS shows 4 cores (HiFi5)  → use NVL debug procedures
  ACE 3.0: ADSPCS shows 5 cores (LX7+HiFi4) → use PTL debug procedures
  ```
- **SoundWire**: 5 links v1.2 on both variants
- **Die path**: `socket0.pcd.ace`
- **AIOC**: Only available on ACE 4.0 SKUs (same engine as NVL). ACE 3.0 SKUs have no AIOC.
- **BIOS**: Variant detection may be needed in BIOS menu — audio DSP features may differ between ACE 3.0 and ACE 4.0 BIOS builds.

### RZL (Razor Lake)

- **ACE version**: ACE 4.0 — same architecture as NVL PCD-H
- **Debug approach**: Apply NVL PCD-H debug procedures directly — same ACE 4.0 architecture, same 4 HiFi5 DSP cores, same 4.5 MB SRAM, same SoundWire 5-segment topology.
- **Die path**: `socket0.pcd.ace` — same namednode path structure as NVL PCD-H
- **Die variants**: PCD-M and PCD-W die variants may have different PG exit latency tuning in `DEVIDLEPOL`.
- **Key differences from NVL**: GPIO pad assignments and board-specific codec BOM — consult RZL ERB schematics.
- **AIOC**: Expected to support AIOC (same ACE 4.0 engine). Verify AIC headers on RZL board.
- **UAOL**: Full support — same enhanced UAOL engine with larger FIFO as NVL.
- **BUG-001/003 applicability**: NVL A0-only bugs (CORB/RIRB DMA stall, DSP Core 3/4 wake) — check RZL stepping to determine if these apply.

### Platform Debug Approach Summary

| Platform | ACE | Route To | PythonSV Die Path | Notes |
|----------|-----|----------|-------------------|-------|
| **WCL** | 3.0 | PTL procedures | `socket0.soc.ace` | Same ACE 3.0 architecture |
| **TTL (ACE 4.0)** | 4.0 | NVL PCD-H procedures | `socket0.pcd.ace` | Detect via ADSPCS core count |
| **TTL (ACE 3.0)** | 3.0 | PTL procedures | `socket0.pcd.ace` | Detect via ADSPCS core count |
| **RZL** | 4.0 | NVL PCD-H procedures | `socket0.pcd.ace` | Direct NVL PCD-H equivalent |

---

## NGA Test Automation Reference

### Test Entry Points

| Component | Entry Config | Script | Test Root |
|-----------|-------------|--------|-----------|
| Audio Validation | `audio_validation.hjson` | `audio_validation.py` | `C:\validation\windows-test-content\audio\` |

### Test Framework

**New framework** (AudioValidation class):
- Lifecycle: `pre_test()` → `test()` → `post_test()`
- Key parameters: `check_ltr`, `check_register`, `pkg_c_state`

**Legacy framework** (audio_common):
- Lifecycle: `prelude()` → `wpp_init()` → `bar_offset()` → `play_audio_stream()` → `exit_wounds()`

### NGA Traffic XML to Script Mapping

| Traffic XML | Script | Subsystem |
|-------------|--------|-----------|
| hda_playback | hda_stream_test.py | HDA |
| sdw_playback | sdw_stream_test.py | SoundWire |
| ssp_playback | ssp_stream_test.py | SSP/I2S |
| dsp_pipeline | dsp_pipeline_test.py | DSP |
| dmic_capture | dmic_capture_test.py | DMIC |
| idisp_playback | idisp_stream_test.py | Display Audio |
| uaol_playback | uaol_stream_test.py | UAOL |
| bt_offload | bt_offload_test.py | BT Offload |
| wov_detect | wov_kwd_test.py | WoV |
| aioc_playback | aioc_stream_test.py | AIOC |
| pm_s0ix | pm_s0ix_test.py | Power |
| pm_d3 | pm_d3_test.py | Power |

### NGA Test Keywords (49 terms)

Used for NGA search/filtering: `audio, ace, hda, soundwire, sdw, ssp, i2s, dsp, sof, dmic, idisp, display_audio, hdmi, dp, uaol, usb_audio, bt_offload, bluetooth, wov, wake_on_voice, aioc, alc712, codec, verb, corb, rirb, adspcs, firmware, ipc, stream, playback, capture, render, volume, mute, jack, headphone, speaker, microphone, s0ix, d3, d0i3, ltr, clock_gate, power_gate, pgctl, sram, thermal, latency`

---

## Fuse and Strap Reference (Debug-Relevant)

| Fuse/Strap | Bits | Purpose | Debug Impact |
|------------|------|---------|-------------|
| SSKUID | [15:8] | Audio SKU ID | Determines available features per SKU |
| SNDWD | [6] | SoundWire disable | If set, all SDW links disabled in HW |
| DSPSD | [1] | DSP/ACE disable | If set, ACE completely disabled (DID=0xFFFF) |
| AONVD | [7] | Always-on voice disable | If set, WoV/DMIC always-on not available |
| DPBCC (soft strap) | 0x04 | Display Port B codec count | Number of iDisp codecs |
| DPSCC (soft strap) | 0x03 | Display Port S codec count | Number of SSP codecs |

---

## Severity Classification

| Level | Criteria | Examples |
|-------|----------|---------|
| **CRITICAL** | Device not functional, blocks all testing | DID=0xFFFF, BAR=0, no PCI device |
| **HIGH** | Major subsystem failure, no audio path | Codec not detected, DSP boot fail, S0ix blocked |
| **MEDIUM** | Intermittent or partial failure | Occasional dropout, glitch under stress, one port affected |
| **LOW** | Cosmetic or non-blocking | Log warning without functional impact, suboptimal perf |

---

## Worked Triage Examples

These walkthroughs show the debug methodology applied to real failure patterns, step by step.

### Example 1: "No Audio Device" — DID = 0xFFFF

**Symptom**: NGA test reports `EXIT_BLOCKED` — audio device not found. Device Manager shows no audio controller.

**Triage Flow**:
```
1. Check PCI config space:
   die.ace.cfg.vendor_id.read() → returns 0xFFFF
   die.ace.cfg.device_id.read() → returns 0xFFFF

2. Interpretation: ACE PCI function is invisible. Three possible causes:
   a) BIOS disabled audio → check AudioController knob
   b) FNCFG.ACED fuse set → check fuse_utils.fuserev()
   c) Power gate stuck → check PMC trace for ACE power domain

3. Resolution path:
   ├── BIOS knob → Set AudioController = Enabled, reboot
   ├── Fuse → Cannot override. Platform is fused without audio. EXIT_BLOCKED expected.
   └── Power gate → Check PMC: print_s0ix_y_blocking_conditions
       If ACE power domain shows "stuck in PG" → escalate to PMC team
```

**Key lesson**: DID=0xFFFF is always Priority 1 — nothing else can work until the device enumerates.

### Example 2: Codec Not Detected — STATESTS = 0x0000

**Symptom**: ACE enumerates (DID=0xD328), BAR0 is valid, but STATESTS reads all zeros. No HDA codecs.

**Triage Flow**:
```
1. Read GCTL.CRST:
   gctl = die.ace.hda.bar0.gctl.read()
   crst = gctl & 1  → if 0, controller is in reset

2. If CRST=0:
   Toggle CRST: write 0 → wait 100us → write 1 → wait 500us → read STATESTS
   If codecs now appear → BIOS did not complete controller init (BIOS bug or timing)

3. If CRST=1 and STATESTS still 0:
   ├── Check physical connection (headphone board, dock, HDMI cable)
   ├── Check BIOS verb table enable (HdaVerbTableEnable = Enabled)
   ├── For iDisp: is display actually connected? No display = no iDisp codec
   └── For external Realtek: check SoundWire vs HDA routing in BIOS
       If AIOC mode enabled, HDA link is intentionally disabled → expected STATESTS=0
```

**Key lesson**: Always check CRST before panicking about STATESTS=0. The simplest toggle fixes ~30% of "no codec" cases.

### Example 3: S0ix Blocked by ACE — 0% Residency

**Symptom**: Platform S0ix residency is 0%. `sleepstudy` report shows "Audio Controller" as blocker.

**Triage Flow**:
```
1. Check ACE power state:
   pmcsr = die.ace.cfg.pmcsr.read()
   d_state = pmcsr & 0x3  → expect 3 (D3) when idle
   If D-state = 0 → ACE stuck in D0. Driver PM not completing.

2. Check LTR:
   Use print_LTRs doctor script → find ACE entry
   If ACE LTR = "active" → ACE is reporting it needs low-latency response
   Common cause: active audio stream not stopped, or DSP FW still loaded

3. Check for active streams:
   ├── Any audio playback/capture open? Close all audio apps
   ├── Check for phantom streams: DeviceManager → Sound → disable test endpoints
   └── Check UAOL: if USB headset still connected, UAOL may hold ACE in D0

4. If D-state = 3 but LTR still blocking:
   ├── Driver bug: LTR not released on D3 entry
   └── Check driver version vs BKC. Known issue on pre-BKC builds.

5. Resolution:
   ├── Stop all audio → verify ACE reaches D3 → verify S0ix achieved
   ├── If still blocked → check NVU/THC cross-domain (see Cross-Domain sections)
   └── If driver bug → update to BKC driver version
```

**Key lesson**: S0ix debug follows the "onion peeling" priority chain: D-state first → LTR second → cross-domain last.

### Example 4: DSP Firmware Load Timeout

**Symptom**: NGA test fails with "DSP FW load timeout". ADSPCS shows cores not powered.

**Triage Flow**:
```
1. Check ADSPCS (DSP Core Status):
   adspcs = die.ace.hda.bar0.adspcs.read()
   # Decode CPA (Core Power Active) and CSTALL bits
   cpa  = (adspcs >> 24) & 0xF   # which cores have power
   crst = (adspcs >> 0)  & 0xF   # which cores in reset

2. If CPA = 0 (no cores powered):
   ├── Check SRAM power gate exit — did SRAM come out of PG?
   ├── Check PMC for DSP power domain status
   └── Known pattern: SRAM PG exit race on cold boot → add delay after PG exit

3. If CPA ≠ 0 but FW load still fails:
   ├── Check FW binary path: is the correct FW file on disk?
   ├── Check FW signature: signed FW required for production silicon
   ├── Check IPC doorbell: did host→DSP IPC message get delivered?
   └── ADSPCS.CSTALL must be cleared AFTER FW is loaded to code memory

4. Resolution:
   ├── Cold boot race → retry (often succeeds on 2nd attempt)
   ├── FW file missing/corrupt → reinstall audio driver package
   └── IPC lost → known pattern #3 (IPC doorbell lost after D0i3) → retrigger
```

**Key lesson**: ADSPCS is the single most important register for DSP debug. Read it first, every time.

---

## See Also

- [platform/SKILL.md](../platform/SKILL.md) — Per-platform ACE data, DID tables, BDF, BIOS knobs
- [config-checkout/SKILL.md](../config-checkout/SKILL.md) — Device enumeration verification, BAR check
- [failure-analysis/SKILL.md](../failure-analysis/SKILL.md) — NGA failure pattern matching, regex patterns
- [power/SKILL.md](../power/SKILL.md) — Power wells, D-state transitions, S0ix integration
- [hda/SKILL.md](../hda/SKILL.md) — HDA link debug, codec discovery, CORB/RIRB
- [soundwire/SKILL.md](../soundwire/SKILL.md) — SoundWire bus enumeration, stream config
- [dsp/SKILL.md](../dsp/SKILL.md) — DSP core power, FW load, IPC
- [uaol/SKILL.md](../uaol/SKILL.md) — USB Audio Offload debug
- [dmic/SKILL.md](../dmic/SKILL.md) — DMIC/PDM debug
- [display-audio/SKILL.md](../display-audio/SKILL.md) — iDisp/HDMI/DP audio
- [bt-offload/SKILL.md](../bt-offload/SKILL.md) — BT audio offload, SSP debug
- [aioc/SKILL.md](../aioc/SKILL.md) — AIOC ALC712/ALC1320 debug
- [docs/audio_known_issues.md](../docs/audio_known_issues.md) — Full known issues database

---

## Cross-Domain Debug: Audio ↔ NVU (Neural Vision Unit)

Audio (ACE) and NVU share SoC resources — power domains, sideband fabric, and on some platforms the MIPI CSI-2 PHY. Failures in one IP can cascade into the other.

### Shared Resources

| Resource | Audio (ACE) Use | NVU Use | Conflict Scenario |
|----------|----------------|---------|-------------------|
| **IOSF Sideband** | Config register access, PMC messaging | Config register access, IPC | Sideband congestion → timeout in either IP |
| **PMC Power Wells** | ACE power domain (D0i3/D3/PG) | NVU power domain (D3/PG) | PMC ordering error if both IPs transition simultaneously |
| **MIPI CSI-2 PHY** | Not used directly | Camera sensor interface | PHY sharing on some SKUs — if camera active, check no PHY conflict |
| **VnnAON Power Rail** | ACE PLL, always-on logic | NVU always-on logic | Rail droop if both IPs demand peak current simultaneously |
| **Interrupt routing** | MSI/INTA via IOSF | MSI/INTA via IOSF | IRQ conflict if both IPs share interrupt vector |

### Cross-Domain Failure Patterns

| Symptom | Likely Cross-Domain Cause | Debug Steps |
|---------|--------------------------|-------------|
| Audio stream glitch when camera starts | NVU DMA bandwidth competing with ACE DMA | Check fabric utilization; disable NVU to isolate; check IOSF credit starvation |
| ACE D3 timeout when NVU is active | PMC sequencing: NVU holding power well that ACE needs released | Check PMC trace for power domain dependencies; use `print_s0ix_y_blocking_conditions` |
| S0ix blocked — both ACE and NVU show active LTR | Both IPs reporting active LTR independently | `print_LTRs` — check both ACE and NVU entries; one may be the true blocker |
| NVU FW load fails after audio starts | IOSF sideband congestion from audio codec enumeration | Sequence: init audio first, wait for stable, then start NVU; or vice versa |
| Audio drops during NVU inference workload | NVU inference DMA saturating memory bandwidth | Reduce NVU inference priority; check memory controller QoS; isolate with NVU disabled |

### Debug Commands (PythonSV)

```python
# Check both IPs simultaneously
# ACE power state
ace_pmcsr = soc.pcd.ace.cfg.pmcsr.read()
print(f"ACE PMCSR = {ace_pmcsr:#010x} (D-state = {ace_pmcsr & 0x3})")

# NVU power state (if present)
try:
    nvu_pmcsr = soc.pcd.nvu.cfg.pmcsr.read()
    print(f"NVU PMCSR = {nvu_pmcsr:#010x} (D-state = {nvu_pmcsr & 0x3})")
except:
    print("NVU not present on this platform/die")

# Check LTR for both IPs
# Use print_LTRs doctor script to see all IP LTR values
```

### Isolation Strategy

1. **Disable NVU** via BIOS (`NVU Controller` = Disabled) → re-test audio
2. **Disable Audio** via BIOS (`AudioController` = Disabled) → re-test NVU
3. If failure disappears in isolation, it's a cross-domain interaction
4. Check PMC trace for power sequencing conflicts between IPs
5. Escalate to platform integration team if PMC sequencing issue confirmed

> **Cross-reference**: See `fv-nvu/debug/SKILL.md` for NVU-side debug procedures, and `fv-nvu/power/SKILL.md` for NVU power management details.

---

## Cross-Domain Debug: Audio ↔ THC (Touch Host Controller)

Audio (ACE) and THC share PCH/PCD resources — sideband fabric, interrupt routing, and power management coordination via PMC. On NVL, both IPs are PCH-resident.

### Shared Resources

| Resource | Audio (ACE) Use | THC Use | Conflict Scenario |
|----------|----------------|---------|-------------------|
| **IOSF Sideband** | PMC messaging, config access | PMC messaging, config access | Sideband congestion during simultaneous D-state transitions |
| **PMC Power Wells** | ACE power gating | THC CGPG (Clock Gate Power Gate) | PMC ordering if both transition D3→D0 at same instant |
| **SPI Bus** (HIDSPI THC) | Not used | THC HIDSPI protocol | No direct conflict, but SPI clock may affect audio GPIO if shared pad group |
| **I2C Bus** (HIDI2C THC) | Not used directly | THC HIDI2C protocol | GPIO pad group conflict if I2C and audio share pad controller |
| **GPIO Pad Controller** | DMIC clock/data pads, jack detect | Touch interrupt GPIO, reset GPIO | Pad mode (PMode) conflict if BIOS assigns wrong function |
| **PMCLite Sideband** | ACE D0i2/D3 messaging | THC D0i2/CGPG messaging | PMCLite message ordering |

### Cross-Domain Failure Patterns

| Symptom | Likely Cross-Domain Cause | Debug Steps |
|---------|--------------------------|-------------|
| Audio DMIC not working, touch works | GPIO pad mode conflict: DMIC pads assigned to THC function | Check GPIO PMode: DMIC pads must be in Audio native function mode; see `fv-lpss/pmode-check` |
| Touch fails after audio driver loads | Audio driver reconfiguring shared GPIO pad group | Check GPIO pad ownership; verify BIOS assigns non-overlapping pad groups |
| S0ix blocked — both ACE and THC active | Both IPs reporting active LTR to PMC | `print_LTRs` — identify which IP is the true blocker |
| Audio glitch when touch input active | IOSF sideband contention during THC DMA + ACE stream | Monitor sideband utilization; check for PMCLite message collision |
| THC D3 timeout when audio stream active | PMC power well dependency — THC waiting for ACE to release shared well | Check PMC trace for power well sequencing; try stopping audio first |
| Both ACE and THC yellow-bang after BIOS update | BIOS GPIO/PMode table changed — broke both audio and touch pad assignments | Verify BIOS GPIO table; compare working vs broken BIOS versions |

### GPIO Pad Mode Verification

```python
# Check GPIO pad assignments for potential Audio ↔ THC conflict
# DMIC pads should be in Audio native function mode (PMode = native)
# THC SPI/I2C pads should be in THC native function mode

# Example: check DMIC clock pad mode (platform-specific pad number)
# dmic_clk_pad = soc.pch.gpio.<community>.<pad>.padcfg0.read()
# pmode = (dmic_clk_pad >> 10) & 0x7  # PMode field
# print(f"DMIC CLK pad PMode = {pmode} (expect: native audio function)")

# See fv-lpss/pmode-check skill for systematic pad mode verification
# See fv-thc/platform skill for THC-specific pad assignments per platform
```

### Isolation Strategy

1. **Disable THC** via BIOS → re-test audio (especially DMIC, jack detect)
2. **Disable Audio** via BIOS → re-test touch
3. Check GPIO PMode table for pad conflicts between audio and THC
4. If S0ix blocked, disable one IP at a time to identify the LTR blocker
5. Check PMCLite message log for ordering conflicts

### Wake-on-Touch (WoT) vs Wake-on-Voice (WoV) Interaction

Both WoT and WoV are S0ix wake sources that coexist on the same platform:

| Feature | Wake Source | Wake Path | Can Coexist? |
|---------|-----------|-----------|-------------|
| **WoV** (Audio) | DMIC keyword detection | DSP → PMC → platform wake | Yes |
| **WoT** (THC) | Touch panel interrupt | GPIO → vGPIO → PMC → platform wake | Yes |

**Coexistence rules:**
- Both can be armed simultaneously during S0ix
- Each uses independent wake paths (no conflict)
- After wake, OS must determine which source triggered wake (check PMC wake reason)
- If one wake source is spurious (false wake), it may disrupt the other's S0ix residency

> **Cross-reference**: See `fv-thc/wot/SKILL.md` for WoT architecture and `fv-thc/power/SKILL.md` for THC power management. See `wov/SKILL.md` for WoV architecture.
