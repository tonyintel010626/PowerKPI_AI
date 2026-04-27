---
name: fv-audio/failure-analysis
description: "Analyze audio-related failures from NGA test results"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# Audio Failure Analysis

This skill provides procedures to identify, analyze, and triage audio failures from NGA test execution results across Intel Client SoC platforms (NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL).

---

## Overview

Audio failures can manifest across HDA links, SoundWire links, SSP/I2S ports, DSP cores, codec interfaces, and the USB Audio Offload (UAOL) engine. This skill helps you:

1. Identify audio-related test failures in NGA
2. Extract and analyze relevant logs (solar_manager audio logs)
3. Classify failure types by subsystem
4. Cross-reference with known issues (sightings) and FV-TRIAGE patterns
5. Recommend next debug steps

---

## NVL Platform Context

### Audio Subsystem Inventory

| Die | HDA SDI | SoundWire Segments | SSP/I2S | DSP (HP) | DSP (ULP) | DMIC |
|-----|---------|-------------------|---------|----------|-----------|------|
| PCD-H | 2 | 5 | 3 | 4 HiFi5 | 1 | 2 |
| PCH-S | 2 | 5 (4 ext + 1 on-die) | 3 | 2 HiFi5 | 1 | 2 |

### NGA Test Name Patterns for Audio

When filtering NGA results, use these keywords:
```python
AUDIO_TEST_KEYWORDS = [
    'audio', 'hda', 'hd_audio', 'hdaudio',
    'soundwire', 'sdw', 'sndw',
    'ssp', 'i2s', 'tdm',
    'dsp', 'ace', 'sof',  # Sound Open Firmware
    'codec', 'realtek', 'cirrus',
    'dmic', 'microphone',
    'idisp', 'hdmi_audio', 'dp_audio',
    'audio_power', 'audio_d3', 'audio_pm',
    'playback', 'capture', 'stream',
]
```

### NGA Test Automation Repository

All NGA audio tests are driven from the **windows-test-content** automation repo:

```
C:\validation\windows-test-content\audio\
```

**Entry point**: Every NGA audio test calls the Galaxy HJSON config:
```
C:\validation\windows-test-content\audio\common\galaxy_hjson\audio_validation.hjson
```

This invokes the main validation script:
```
C:\validation\windows-test-content\audio\common\validation\audio_validation.py
```

#### NGA Traffic XML → Test Script Mapping

NGA triggers tests via traffic XMLs in `nga_traffic_xmls/`. Each XML points to a Python script:

| NGA Traffic XML | Test Script (under `tests/audio/Automation/Audio_Tests/`) | Subsystem |
|----------------|----------------------------------------------------------|-----------|
| `Start_Audio_Test_S0ix_Playback_and_capture.xml` | `Audio_Test_S0ix_Playback_and_capture.py` | S0ix + Audio |
| `Start_Audio_Test_S0ix_Playback_Only.xml` | `Audio_Test_S0ix_Playback_and_capture.py` | S0ix + Audio |
| `Start_Audio_Test_S3_S4_*.xml` | `Audio_Test_S3_S4_Playback_and_Capture.py` | Sx + Audio |
| `Start_Audio_Test_S5_G3_WR_*.xml` | `Audio_Test_S5_G3_WR_Playback_and_Capture.py` | Reset + Audio |
| `Start_Audio_Test_D3D0_*.xml` | `Audio_Test_D3D0_*.py` | D-state + Audio |
| `Start_Audio_Test_DMic*.xml` | `Audio_Test_DMic*.py` | DMIC |
| `Start_Audio_Test_Long_*.xml` | `Audio_Test_Long_Playback_and_Capture.py` | Stress |
| `Start_Audio_Test_LP_*.xml` | `Audio_Test_LP_Playback_and_capture.py` | Low Power |
| `Start_Audio_Test_CS*.xml` | `Audio_Test_CS.py` | Connected Standby |
| `Start_Audio_Test_WoV*.xml` | `WoV_*.py` | Wake on Voice |
| `Start_Audio_Test_HDA_iDisplay*.xml` | HDA iDisplay test | Display Audio |
| `Start_Solar_S0ix_batch*.xml` | Solar S0ix batch | S0ix batch |

#### Two Test Frameworks

**New framework** (`AudioValidation` class in `audio_validation.py`):
- Extends `TestBaseAudio` from Galaxy
- Flow: `_run_pre_test()` → `_run_test()` → `_run_post_test()`
- Pre-test: BT connect, device enumeration, speaker/mic selection, volume, idle PkgC check, DMA start
- Test: audio playback/capture, LTR checks (`SvNnDef.NN_LTR_C2P2_IP_ACE`), register checks, Solar cycles, D3 power gating (`SvNnDef.NN_ACE_PGS_LIST`), LPIB monitoring, driver disable/enable
- Post-test: cleanup, driver rescan
- Key params: `check_ltr`, `check_register`, `pkg_c_state`, `disable_enable_audio_oed_driver`

**Legacy framework** (standalone scripts using `audio_common as ac`):
- Flow: `ac.prelude()` → `ac.wpp_init()` → `ac.bar_offset()` → `ac.play_audio_stream()` → iteration loop → `ac.exit_wounds('SUCCESS')`
- Key checks: `ac.lpibRunning` (DMA activity), `ac.decoupled_mode`, `ac.check_driver_traces`, `ac.fifoTrk_Run`

#### When Triaging a Failed NGA Audio Test

1. **Identify the test script**: Match the NGA test name to the traffic XML → script mapping above
2. **Read the script**: Navigate to `C:\validation\windows-test-content\audio\tests\audio\Automation\Audio_Tests\<script>.py`
3. **Identify the failure step**: Check which phase failed (pre_test / test / post_test)
4. **Check BIOS knobs**: Audio BIOS knob configs are at `C:\validation\windows-test-content\audio\bios_knobs\`
5. **Cross-reference with sub-skills**: Route to the appropriate FV-AUDIO sub-skill based on subsystem

---

## Multi-Platform Failure Analysis

While the NGA test infrastructure and failure patterns above are primarily documented for NVL, the same test framework runs across all supported platforms. When triaging failures on non-NVL platforms, apply the following routing:

### Platform Debug Routing for Failure Analysis

| Platform | ACE | Route To | Key Differences |
|----------|-----|----------|-----------------|
| **PTL** | 3.0 | PTL-specific procedures | ACE 3.0 DID differs; SSP BCLK inversion (HSDES-003); BT offload S0ix blocking (HSDES-006) |
| **WCL** | 3.0 | PTL procedures | Same ACE 3.0 as PTL — apply PTL known issues. Die path: `socket0.soc.ace` |
| **TTL (ACE 4.0)** | 4.0 | NVL PCD-H procedures | Same ACE 4.x engine. Detect via `ADSPCS` core count (4 HiFi5 = ACE 4.0) |
| **TTL (ACE 3.0)** | 3.0 | PTL procedures | Same ACE 3.0 as WCL/PTL. Detect via `ADSPCS` core count (5 LX7 = ACE 3.0) |
| **RZL** | 4.0 | NVL PCD-H procedures | Direct NVL PCD-H equivalent. Check RZL-specific GPIO/BOM differences |
| **LNL** | 2.x | LNL-specific procedures | No UAOL, no AIOC, simpler topology. ACE 2.x SHIM layout differs |
| **MTL** | 1.5 | MTL-specific procedures | UAOL behind-hub broken (BUG-005); PSF glitch (BUG-004) |
| **ARL** | 1.5 | MTL procedures | Same ACE generation as MTL; cross-reference MTL known issues |

### Platform-Specific NGA Test Considerations

- **AIOC tests** (`aioc_playback`, `aioc_stream_test.py`): Only applicable on NVL, TTL ACE 4.0, and RZL. Expected to fail/be skipped on ACE 3.0 platforms (PTL, WCL, TTL ACE 3.0).
- **UAOL tests** (`uaol_playback`, `uaol_stream_test.py`): UAOL behind-hub tests are known-broken on MTL (BUG-005). On ACE 4.x platforms (NVL, RZL, TTL ACE 4.0), UAOL has larger FIFO — timing thresholds may differ from ACE 3.0.
- **BT offload tests** (`bt_offload`, `bt_offload_test.py`): S0ix blocking issue (HSDES-006) affects PTL and WCL. Verify S0ix residency after BT offload teardown.
- **WoV tests** (`wov_detect`, `wov_kwd_test.py`): CRO/RTC clock path differs by ACE version — `DWCS=01` (RTC) is deprecated on ACE 4.x. See `wov/SKILL.md` for per-platform WoV config.
- **DID checks in test scripts**: Some test scripts hardcode NVL DID values (e.g., `0xD328` PCD-H, `0xD228` PCH-S). On other platforms, the DID will differ — check `fv-audio/platform` for correct DIDs and update test scripts accordingly.

### Cross-Platform Log Keywords

When searching NGA logs for failures across platforms, the `AUDIO_TEST_KEYWORDS` list above applies universally. Additionally, for platform-specific log filtering:

```python
PLATFORM_AUDIO_KEYWORDS = {
    'wcl': ['wcl', 'wildcat', 'ace3'],
    'ttl': ['ttl', 'titan', 'ace3', 'ace4', 'dual_ace'],
    'rzl': ['rzl', 'razor', 'ace4'],
}
```

---

## Audio Failure Patterns

### HDA Controller Failures

**Common patterns in logs:**
```python
HDA_PATTERNS = [
    r'HDA.*Error',
    r'HDA.*Timeout',
    r'CORB.*timeout',           # Command transport timeout
    r'RIRB.*timeout',           # Response transport timeout
    r'RIRB.*overflow',          # Response buffer overflow
    r'codec.*not.*found',       # No codec detected
    r'codec.*not.*respond',     # Codec not responding to verbs
    r'STATESTS.*0x0',           # No codec presence detected
    r'GCTL.*CRST.*0',           # Controller stuck in reset
    r'verb.*timeout',           # Verb send timeout
    r'stream.*error',           # Stream configuration error
    r'DMA.*error',              # DMA transfer error
]
```

**Typical failure modes:**
- **Codec not detected** — STATESTS=0, HDA link not started, codec powered off
- **CORB/RIRB timeout** — Codec not responding, link error, wrong codec address
- **Stream error** — DMA buffer underrun/overrun, format mismatch
- **Controller in reset** — GCTL.CRST=0, controller not initialized

---

### SoundWire Failures

**Common patterns in logs:**
```python
SDW_PATTERNS = [
    r'SoundWire.*Error',
    r'SDW.*link.*fail',
    r'SDW.*bus.*timeout',
    r'SDW.*enumerat.*fail',     # Bus enumeration failure
    r'SDW.*stream.*error',      # Stream configuration error
    r'SDW.*clock.*stop',        # Clock stop failure
    r'SDW.*sync.*error',        # Synchronization error
    r'SDW.*parity',             # Parity error on bus
    r'SDW.*collision',          # Bus collision detected
    r'SHIM.*error',             # SHIM configuration error
]
```

**Typical failure modes:**
- **Link not starting** — SHIM misconfigured, bus clock not running
- **Enumeration failure** — Codec not detected on bus segment
- **Stream error** — Data lane config mismatch, sample rate mismatch
- **Clock stop failure** — Codec cannot enter clock-stop mode

---

### SSP/I2S Failures

**Common patterns in logs:**
```python
SSP_PATTERNS = [
    r'SSP.*Error',
    r'I2S.*Error',
    r'SSP.*timeout',
    r'SSP.*FIFO.*overflow',
    r'SSP.*FIFO.*underrun',
    r'SSP.*clock.*error',
    r'SSP.*frame.*sync.*error',
    r'TDM.*slot.*error',
    r'BCLK.*mismatch',
]
```

**Typical failure modes:**
- **FIFO underrun/overflow** — Clock mismatch, DMA not keeping up
- **Frame sync error** — I2S/TDM framing misconfigured
- **Clock error** — BCLK rate wrong, PLL not locked

---

### DSP Failures

**Common patterns in logs:**
```python
DSP_PATTERNS = [
    r'DSP.*Error',
    r'DSP.*timeout',
    r'DSP.*firmware.*fail',
    r'DSP.*FW.*load.*fail',
    r'DSP.*IPC.*timeout',       # IPC message timeout
    r'DSP.*panic',              # DSP firmware panic
    r'DSP.*core.*stall',        # DSP core stalled
    r'SRAM.*error',             # SRAM access error
    r'pipeline.*error',         # Audio pipeline error
    r'GPROCEN.*0',              # DSP not enabled
]
```

**Typical failure modes:**
- **FW load failure** — GPROCEN not set, SRAM not powered, bad FW image
- **IPC timeout** — DSP not responding to host messages
- **DSP panic** — Firmware crash, pipeline error
- **Core stall** — DSP core stuck, watchdog timeout

---

### Codec Failures

**Common patterns in logs:**
```python
CODEC_PATTERNS = [
    r'codec.*init.*fail',
    r'codec.*verb.*error',
    r'jack.*detect.*fail',
    r'amplifier.*error',
    r'headset.*detect.*fail',
    r'codec.*power.*error',
    r'widget.*config.*error',
    r'pin.*config.*error',
]
```

**Typical failure modes:**
- **Init failure** — Wrong verb sequence, codec not responding
- **Jack detect failure** — Pin sense not working, GPIO misconfigured
- **Amplifier error** — Wrong gain settings, power sequencing issue

---

### UAOL (USB Audio Offload) Failures

**Common patterns in logs:**
```python
UAOL_PATTERNS = [
    r'UAOL.*Error',
    r'UAOL.*timeout',
    r'UAOL.*FIFO.*overflow',
    r'UAOL.*FIFO.*underrun',
    r'UAOL.*xHCI.*error',          # xHCI integration error
    r'UAOL.*isochronous.*error',    # ISO stream error
    r'UAOL.*connect.*fail',         # USB device connection failure
    r'UAOL.*offload.*fail',         # Offload engine start failure
    r'UAOL.*behind.*hub.*fail',     # Behind-hub topology failure
    r'USB.*audio.*offload.*error',
]
```

**Typical failure modes:**
- **Offload start failure** — UAOL engine not enabled, xHCI handshake timeout
- **FIFO underrun/overflow** — ACE↔xHCI FIFO timing mismatch, DMA not keeping up
- **ISO stream error** — Isochronous transfer failure, USB bandwidth insufficient
- **Behind-hub failure** — USB audio device behind hub not supported or routing error
- **xHCI integration error** — Cross-domain ACE↔xHCI communication failure

---

### Power Management Failures

**Common patterns in logs:**
```python
AUDIO_PM_PATTERNS = [
    r'audio.*D3.*timeout',
    r'audio.*D3.*fail',
    r'audio.*D0i3.*fail',
    r'audio.*S0ix.*block',
    r'PLL.*not.*lock',
    r'PLL.*timeout',
    r'SRAM.*power.*gate.*fail',
    r'LTR.*error',
    r'PMC.*audio.*error',
    r'PMCSR.*stuck',
]
```

**Typical failure modes:**
- **D3 timeout** — Active stream blocking D3, pending interrupt
- **PLL not locking** — Clock source issue after D3 exit
- **S0ix blocked** — Audio preventing platform idle state
- **SRAM power gate failure** — DSP SRAM not entering/exiting PG correctly

---

## FV-TRIAGE Audio Pattern Integration

FV-TRIAGE already detects these audio-specific patterns during initial triage:

| FV-TRIAGE Pattern | Audio Subsystem | Drill-Down Skill |
|-------------------|----------------|-------------------|
| `AudioDeviceNotFound` | ACE PCI (0:31:3) | `fv-audio/config-checkout` |
| `StreamError` | HDA/SoundWire/SSP | `fv-audio/hda` or `fv-audio/soundwire` |
| `BufferUnderrun` | HDA/SoundWire DMA | `fv-audio/hda` |
| `CodecInitFailed` | HDA/SoundWire codec | `fv-audio/hda` or `fv-audio/soundwire` |
| `NoSignalDetected` | Output path | `fv-audio/hda` — check stream + codec |
| `DistortionDetected` | Audio quality | `fv-audio/hda` — check format + codec config |
| `LevelOutOfRange` | Amplifier/gain | `fv-audio/hda` — check codec verb (amp gain) |
| `Audio.*Endpoint.*Error` | Endpoint config | `fv-audio/config-checkout` — check ACPI |
| `UaolOffloadFailed` | UAOL engine | `fv-audio/uaol` — check xHCI handshake, FIFO timing |
| `UsbAudioTimeout` | UAOL stream | `fv-audio/uaol` — check ISO transfer, behind-hub |

**Workflow:** FV-TRIAGE detects the pattern -> FV-AUDIO drills deeper with subsystem-specific analysis.

---

## Log Analysis

### Audio Log Locations

| Log File | Path | Content |
|----------|------|---------|
| `audio_error.log` | `<LogsPath>/solar_manager/` | Audio subsystem errors |
| `audio_debug.log` | `<LogsPath>/solar_manager/` | Detailed debug trace |
| `audio_validation.log` | `<LogsPath>/solar_manager/` | Validation test output |
| `triage_tools.log` | `<LogsPath>/solar_manager/` | Triage tool output |
| Audio logs (general) | `<LogsPath>/audio/` | General audio logs |

### Log Analysis Priority

When analyzing audio failures, check logs in this order:
1. **BSOD/crash dump** — check if audio driver (IntcAudioBus.sys, IntcSmartSound.sys, HDAudio.sys) is in the stack
2. **WPP ETL traces** — Driver/FW-level traces with detailed internal state (see WPP Autologger section below)
3. **Event Logs** — look for HD Audio / Intel Smart Sound Technology driver errors
4. **Test execution logs** — Audio register dumps, stream results
5. **PythonSV output** — Register read/write results, traffic pass/fail
6. **Framework logs** — VJT Audio init errors, codec discovery failures

### WPP Autologger (Windows Driver ETL Traces)

*Source: [Wiki Page 4251524533]*

WPP (Windows software trace Preprocessor) autologger captures driver and firmware-level traces for diagnosing YellowBang / DevCon errors and intermittent audio failures that don't produce crash dumps.

#### When to Use WPP

- Audio device shows yellow bang (!) in Device Manager
- `DevCon` reports device error but no BSOD
- Intermittent audio glitches/dropouts with no visible error in Event Viewer
- Driver initialization failures that are timing-dependent

#### WPP Capture Workflow

```
Step 1: Enable WPP autologger for Intel audio drivers
  ├── Open elevated command prompt
  ├── Navigate to WPP tools directory
  │   (check NVL wiki page 4251524533 for latest tool path)
  └── Run autologger setup with correct provider GUIDs

Step 2: Reboot to activate autologger
  └── WPP traces begin capturing from early boot

Step 3: Reproduce the failure

Step 4: Collect ETL files
  ├── Default location: C:\Windows\System32\LogFiles\WMI\
  └── Copy .etl files for decode

Step 5: Decode ETL to human-readable text
  ├── Requires matching PDB symbols for driver version
  ├── tracefmt.exe or Windows Performance Analyzer (WPA)
  └── Filter by audio provider GUIDs
```

#### Key Audio WPP Provider GUIDs

| Driver | Provider GUID | Description |
|--------|--------------|-------------|
| **IntcAudioBus.sys** | `{b18a8cd7-7e56-4687-9b69-1a2c5f263e70}` | Intel Audio Bus driver — codec enum, link init, HDA/SoundWire bus ops |
| **IntcSmartSound.sys** | `{a07e5e66-5c2e-4e03-b82f-89b6a0e6e500}` | Intel SST/SOF driver — DSP FW load, pipeline mgmt, IPC messaging |
| **HDAudio.sys** | `{ab47fe07-5765-4c3a-b3ec-b5a79e9c05c3}` | Microsoft HD Audio class driver — HDA controller ops, stream mgmt |
| **IntcOED.sys** | `{8b53f824-90b7-4bdf-923f-6bc2645a0186}` | Intel OED driver — offload engine, UAOL interface |
| **IntcDAud.sys** | `{b8bf40c3-794e-4c5c-8c28-3d9a2b8c3e5a}` | Intel Display Audio — iDisp codec management, ELD handling |

> **⚠️ VERSION SENSITIVITY**: The GUIDs above are representative values extracted from NVL BKC driver packages (circa 2025-2026). Provider GUIDs **may change** between major driver releases. Always verify the current GUIDs using one of these methods:
> 1. **From PDB**: `tracepdb.exe -f IntcAudioBus.pdb -o IntcAudioBus.tmf` — TMF header contains the GUID
> 2. **From driver binary**: `traceview.exe` → File → Add Provider → scan `.sys` file
> 3. **From wiki**: Check NVL Audio Validation wiki page (ID: 4251524533) for the latest GUID table
> 4. **From registry**: `HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\IntelAudio\{GUID}`

#### WPP Autologger Setup Commands

```powershell
# Enable autologger for Intel Audio Bus driver (run as Admin)
logman create trace "IntelAudioBus" -ow -o C:\AudioLogs\IntcAudioBus.etl ^
    -p "{b18a8cd7-7e56-4687-9b69-1a2c5f263e70}" 0xFFFFFFFF 0xFF -nb 16 256 ^
    -bs 1024 -mode Circular -f bincirc -max 256 -ets

# Enable autologger for Intel SST driver
logman create trace "IntelSST" -ow -o C:\AudioLogs\IntcSST.etl ^
    -p "{a07e5e66-5c2e-4e03-b82f-89b6a0e6e500}" 0xFFFFFFFF 0xFF -nb 16 256 ^
    -bs 1024 -mode Circular -f bincirc -max 256 -ets

# Stop and collect traces after reproducing failure
logman stop "IntelAudioBus" -ets
logman stop "IntelSST" -ets

# Decode ETL to text (requires matching PDB/TMF files)
tracefmt.exe C:\AudioLogs\IntcAudioBus.etl -tmf C:\Symbols\IntcAudioBus.tmf -o decoded.txt
```

#### WPP vs Event Viewer

| Feature | WPP ETL Trace | Windows Event Viewer |
|---------|--------------|---------------------|
| Detail level | Internal driver state, register values, timing | High-level events only |
| Boot capture | Yes (autologger starts before login) | Limited |
| Performance impact | Minimal (binary trace) | Minimal |
| Decode requirement | PDB symbols + tracefmt | Built-in viewer |
| Use case | Deep driver debug, intermittent issues | Quick first-look triage |

---

## Hardware Debug Capabilities (HAS §20)

*Source: NVLDP ACE4.x Integration HAS §20 Debug Requirements*

### VISA2 Observability

ACE IP implements **VISA2** (Visualization of Internal Signals and Attributes) architecture for post-silicon debug signal observation.

**NVLDP VISA Security Configuration:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `DFX_NUM_OF_FEATURES_TO_SECURE` | 1 | Number of DFx features requiring security unlock |
| `DFX_EARLYBOOT_FEATURE_ENABLE` | `001b` | Features enabled before security unlock |
| `DFX_SECURE_POLICY_MATRIX` | `69228A054319h` | Per-feature security policy bitmap |

> **NOTE**: VISA access requires DFx unlock on production silicon. Debug builds have VISA enabled by default.

### DTF Low-Power Tracing (DSP Firmware Debug)

**Debug Trace Fabric (DTF)** provides DSP firmware trace capture routed through the SoC's centralized **North Peak** aggregator — essential for debugging DSP FW crashes, pipeline stalls, and IPC failures without halting the core.

**Architecture:**
```
DSP FW debug messages
    → L2 SRAM buffer (FW posts messages)
    → DTF Source Packetizer (DMA handshake, pulls from L2)
    → DTF Encoder (converts to DTF message format)
    → DTF VISA Network (routed through SoC fabric)
    → North Peak Aggregator (centralized collection)
    → Host memory / trace file
```

**NVLDP DTF Configuration:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `DTF_EN` | 1 | DTF enabled on NVLDP |
| `DTF_MSTID0-3` | `0x16` | DTF Master IDs for ACE IP |
| `DTF_CHID0` | `0x01` | Channel 0 ID |
| `DTF_CHID1` | `0x02` | Channel 1 ID |
| `DTF_CHID2` | `0x03` | Channel 2 ID |
| `DTF_CHID3` | `0x04` | Channel 3 ID |
| Timestamp shift | 6 bits | For 38.4 MHz XTAL clock base |

**Key points:**
- DSP FW directly manages flow control and injects debug messages via bare-minimum control/status register bits
- DMA handshake: DSP FW posts messages in L2 SRAM, DTF Source Packetizer pulls based on DTF Encoder throughput
- **No host SW injection through DTF** — host uses Windows Event Logging routed to North Peak directly
- DTF is the primary method for capturing DSP FW-level traces during audio pipeline failures

### sTAP / On-Chip Debugger (OCD)

Post-silicon DSP core debug uses the **Tensilica On-Chip Debugger (OCD)** accessed through the **secondary TAP port** (sTAP).

**NVLDP sTAP Configuration:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| `SSSTAPE` | 0 | No subsystem sTAP (no SRAM LDO/CRO/PLL in ACE IP) |
| Instruction Register | 5-bit decoded | Standard JTAG IR |
| Data Registers | TDI/TDO | User data via JTAG scan chain |

**JTAG Clock Constraint:** JTAG TCK must NOT exceed **1/4 of Tensilica core clock frequency** (assuming 50% duty cycle). Violating this causes unreliable debug reads.

```python
# Example: Verify JTAG clock constraint
# If DSP core runs at 614 MHz (ACE PLL bypass), max TCK = 153 MHz
# If DSP core runs at 38.4 MHz (XTAL), max TCK = 9.6 MHz
# Always check current DSP clock before setting JTAG speed
```

> **Cross-reference:** For Xtensa OCD setup and XT-OCD probe connection, see `fv-audio/dsp` (§ XT-OCD Debug).

### Silicon Fuses Affecting Debug (HAS §21)

| Fuse | Bits | NVLDP Status | Description |
|------|------|-------------|-------------|
| `SSKUID[15:8]` | 8 | Valid | Silicon SKU identifier |
| `SNDWD[6]` | 1 | Valid | SoundWire disable fuse — if blown, all SoundWire segments disabled |
| `DSPSD[1]` | 1 | Valid | DSP subsystem disable fuse — if blown, DSP cores inaccessible |
| `AONVD[7]` | 1 | Reserved | AON Vision disable (reserved on NVLDP) |

> **Debug tip:** If SoundWire or DSP features are unexpectedly missing, check fuse state first: `fuse_utils.qdf()` and inspect SNDWD/DSPSD bits. A blown fuse cannot be worked around.

### Soft Straps Affecting Audio Configuration

| Strap | Value | Description |
|-------|-------|-------------|
| `DPBCC` | `0x04` | PCI Base Class Code (Multimedia) |
| `DPSCC` | `0x03` | PCI Sub-Class Code (Audio device) |
| `DPPI` | `0x00` | PCI Programming Interface |
| `DDID[6:4]` | varies | Device ID selection bits |
| `DINTPN` | `001b` | Interrupt Pin (INTA#) |
| `DBCLD` | varies | BIOS Configuration Lock Down |
| `DPGE` | varies | Power Gating Enable strap |
| `DCGE` | varies | Clock Gating Enable strap |
| `XOCFS` | `01b` | 38.4 MHz XTAL on NVLDP |

---

## Failure Triage Workflow

### Phase 1: Identify
- Determine affected subsystem (HDA / SoundWire / SSP / DSP / Codec / Power)
- Identify platform die variant (PCD-H vs PCH-S)
- Get NGA test suite name, station, project

### Phase 2: Gather State
- Load `fv-audio/config-checkout` — check enumeration
- Read PCI config: VID, DID, CMD, BAR0, BAR2, PMCSR
- Check GCAP, GCTL, STATESTS for HDA state
- Check PPCTL for DSP state

### Phase 3: Pattern Match
- Scan logs against the failure patterns above
- Check FV-TRIAGE output for audio-specific detections
- Cross-reference with `docs/audio_known_issues.md`

### Phase 4: Root Cause Analysis
- Load subsystem-specific skill (`fv-audio/hda`, `fv-audio/soundwire`, `fv-audio/dsp`)
- Examine registers in detail
- Check power state (`fv-audio/power`) if PM-related

### Phase 5: Resolution
- If known issue: reference HSDES sighting and workaround
- If new issue: document reproduction steps, register state, and recommend filing
- If test issue: check test config, platform config, BIOS settings
- Escalate to `FV_Debugger_V1` for wiki search and deep triage if unresolved

---

## Audio Error Severity Classification

| Severity | Criteria | Examples |
|----------|----------|---------|
| **CRITICAL** | Device not visible, silicon defect suspected | VID=0xFFFF, BAR=0, DSP hard lockup |
| **HIGH** | Functional failure, blocks test execution | Codec not detected, FW load fail, stream error |
| **MEDIUM** | Degraded operation, intermittent | Occasional buffer underrun, jack detect flaky |
| **LOW** | Cosmetic, non-blocking | Log warnings, minor timing deviations |

---

## NGA Integration

### Fetching Audio Test Results

Use NGA skills to retrieve audio test execution results:

```python
# Search for audio test failures in NGA
# Use nga/search skill with audio keywords
# Filter: project=NVL, status=FAIL, keywords=audio|hda|soundwire|dsp
```

### Cross-Referencing with HSDES

Use `hsdes` or `sighting-info` skills to search for known audio sightings:
- Search terms: `Audio HDA SoundWire DSP codec ACE NVL`
- Tenants: `sighting`, `bug`
- Check for existing sightings before filing new ones

---

## Test Template

```python
#!/usr/bin/env python
"""Audio Validation Test Template"""

import logging
import sys

# NGA exit codes
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2
EXIT_ERROR = 3

log = logging.getLogger("AUDIO")
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


def setup(die="pcd"):
    """Initialize PythonSV and verify audio device."""
    import namednodes as nn
    nn.sv.refresh()
    
    if die == "pcd":
        ace = nn.sv.socket0.pcd.ace
        expected_did = 0xD328
    else:
        ace = nn.sv.socket0.pch.ace
        expected_did = 0xD228
    
    vid = ace.cfg.vendor_id.read()
    if vid != 0x8086:
        log.error("Audio device not found: VID=0x%04X" % vid)
        return None
    
    did = ace.cfg.device_id.read()
    log.info("Audio device found: VID=0x%04X DID=0x%04X" % (vid, did))
    return ace


def test_main(ace):
    """Main test logic — override this."""
    # Example: Check codec presence
    statests = ace.bar0.statests.read()
    log.info("STATESTS = 0x%04X" % statests)
    
    if statests == 0:
        log.error("No codec detected on HDA link")
        return EXIT_FAIL
    
    log.info("Codec(s) detected: STATESTS=0x%04X" % statests)
    return EXIT_PASS


def teardown(ace):
    """Cleanup after test."""
    pass


def main():
    die = sys.argv[1] if len(sys.argv) > 1 else "pcd"
    ace = setup(die)
    if ace is None:
        sys.exit(EXIT_BLOCKED)
    
    try:
        result = test_main(ace)
    except Exception as e:
        log.error("Test exception: %s" % str(e))
        result = EXIT_ERROR
    finally:
        teardown(ace)
    
    sys.exit(result)


if __name__ == "__main__":
    main()
```
