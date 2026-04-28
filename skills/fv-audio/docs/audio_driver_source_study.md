# Audio Windows Driver Source Study
<!-- owner: huiyingt | platform: NVL, PTL, MTL, LNL | os: Windows 11 only | last updated: 2026-04-01 -->
<!-- companion to: ../SKILL.md, audio_ace_has_extraction.md -->

> Documents the Windows audio driver stack for Intel ACE platforms. Covers driver
> component responsibilities, interaction points, known behavioral quirks, and
> validation-relevant implementation details. For register-level hardware specs see
> `audio_ace_has_extraction.md` and query Co-Design.
>
> **Scope**: Windows 11 only. No Linux driver coverage (NVL validation is Windows-only).

---

## 1. Driver Component Overview

### 1.1 Driver Stack

```
┌─────────────────────────────────────────────────────┐
│              User Mode                              │
│  audiodg.exe (Windows Audio Engine)                 │
│  wasapi / mmdevapi / PortAudio (app layer)          │
└─────────────────────┬───────────────────────────────┘
                      │ KS (Kernel Streaming) IOCTLs
┌─────────────────────▼───────────────────────────────┐
│              Kernel Mode                            │
│  portcls.sys          — PortClass adapter driver    │
│  ks.sys               — Kernel Streaming bus        │
│  hdaudbus.sys         — HDA bus enumerator          │
└──┬─────────────┬──────────────┬─────────────────────┘
   │             │              │
   ▼             ▼              ▼
intcaudiobus  intcpchsnd    intelaud.sys
.sys          .sys          (SOF DSP runtime)
(HDA codec    (SoundWire    ├── DSP FW load
 verbs,        host)        ├── IPC messaging
 CORB/RIRB)                 ├── Pipeline mgmt
   │                        └── D0i3/wake
   ▼
intelpch_dmic.sys           intcbt_offload.sys
(DMIC PDM,                  (SSP BT HFP offload
 privacy mode)               via CNVi)
```

### 1.2 Driver File Summary

| Driver File | Inf | Purpose | Key IOCTL / Interface |
|-------------|-----|---------|----------------------|
| `intcaudiobus.sys` | `intcaudiobus.inf` | HDA miniport — verb programming, codec enumeration, CORB/RIRB | `IOCTL_KS_PROPERTY` via PortCls |
| `intcpchsnd.sys` | `intcpchsnd.inf` | SoundWire host controller — enumeration, stream config | SoundWire DDI |
| `intelaud.sys` | `intelaud.inf` | SOF DSP runtime — FW load, IPC, topology manifest, pipeline create/destroy | `IOCTL_INTELAUD_*` |
| `intelpch_dmic.sys` | `intdmic.inf` | DMIC PDM controller — clock, FIFO, privacy mode | DMIC DDI via ACE |
| `intcbt_offload.sys` | `intcbt.inf` | SSP/I2S BT HFP offload — BCLK config, SAI routing | BT audio offload DDI |
| `hdaudbus.sys` | (OS inbox) | HDA bus enumerator — codec slot assignment | PnP enumeration |
| `portcls.sys` | (OS inbox) | PortClass adapter framework | KS interface, DPC, streams |

---

## 2. intcaudiobus.sys — HDA Miniport

### 2.1 Responsibilities
- CORB/RIRB DMA management (ring buffer init, pointer update, DMA start/stop)
- Codec verb execution (send to CORB, read from RIRB, unsolicited response handling)
- HDA stream descriptor programming (BDL, CBL, LVI, FMT)
- Jack detection: pin-sense polling + unsolicited response → PortClass notification
- Power state transitions: D0 ↔ D3hot (PCICMD + PMCSR + GCTL)

### 2.2 Key Behavioral Notes

| Behavior | Detail | Validation Relevance |
|----------|--------|---------------------|
| D3 → D0 CORB/RIRB re-init | Driver re-programs CORB/RIRB base, size, DMA-run on every D0 resume | BUG-001: DMA stall if base address not re-written before DMA-start |
| Unsolicited response tag | Tags [31:26] identify event type (jack sense, power state) | Verify tag assignment matches codec vendor spec |
| Link position in buffer (LPIB) | Driver reads LPIB per period to advance read pointer | Incorrect LPIB → audio glitch; check LPIB polling interval |
| Cold/warm reset via CRST | GCTL.CRST=0 then CRST=1 to re-enumerate codecs | Allow ≥100 ms after CRST=1 before reading STATESTS |
| Verb timeout | If RIRB response not received in ~300 µs, driver marks codec unsolicited | Check RINTCNT + RIRBSIZE config if timeouts observed |

### 2.3 Debug: HDA Codec Trace (ETW)

```powershell
# Enable HDA miniport ETW tracing
logman create trace hda_trace -p "{GUID_INTCAUDIOBUS}" -o hda.etl -ets
# Run test...
logman stop hda_trace -ets
# Decode
tracerpt hda.etl -o hda_trace.xml -of XML
```

---

## 3. intcpchsnd.sys — SoundWire Host Controller

### 3.1 Responsibilities
- SoundWire bus enumeration (Ping, address assignment, DisCo manifest read)
- Stream configuration (data port prepare/enable/disable/deprepare)
- CLK_STOP entry/exit sequencing
- Wake-on-SoundWire (slave alert → host interrupt)

### 3.2 Key Behavioral Notes

| Behavior | Detail | Validation Relevance |
|----------|--------|---------------------|
| Enumeration timing | Slave must respond within 32 frames or bus restart | Check oscilloscope for proper RST pulse width |
| CLK_STOP handshake | Host sends CLOCK_STOP_REQUEST, waits for CLOCK_STOP_PREP_OK from slave | BUG-002: Seg4 reset fails if CLK_STOP_OK not ACKed before RST |
| Dynamic address change | Not supported post-enumeration — requires full bus reset | If address collision, full RST + re-enum cycle |
| Multi-link synchrony | Segments must be synchronized to same frame clock | Mismatch → audio artefacts in multi-codec path |
| Stream bandwidth negotiation | intcpchsnd negotiates payload width based on sample rate × channels | Overshooting bus BW → NACK during stream enable |

### 3.3 Debug: SoundWire Event Log

```powershell
# Check SoundWire events in Windows Event Viewer:
# → Applications and Services Logs → Intel → SoundWire

# PowerShell: dump recent SoundWire errors
Get-WinEvent -LogName "Intel-SoundWire/Operational" -MaxEvents 50 |
  Where-Object { $_.Level -le 3 } |
  Select-Object TimeCreated, Id, Message
```

---

## 4. intelaud.sys — SOF DSP Runtime

### 4.1 Responsibilities
- DSP firmware load: ADSP DMA transfer of SOF binary into HP-SRAM
- IPC messaging: host ↔ DSP command/response via HIPCI/HIPCT registers
- Topology manifest: parsing `.tplg` file → creating DSP pipelines via IPC
- D0i3 entry/exit: DSP suspend (firmware cooperative suspend, SRAM retention)
- Pipeline start/stop/pause for each audio path

### 4.2 FW Load Sequence (Windows-specific)

```
1. Driver gets DSP device from PnP (BAR2 mapped)
2. Driver reads ADSPCS (core status) — all cores in reset
3. Driver DMA's SOF FW image to HP-SRAM via Scatter-Gather DMA
4. Driver releases core 0 from reset (ADSPCS.CRST[0] = 0)
5. DSP core 0 boots, sends IPC BOOT_STATUS = 0 (success)
6. Driver sends IPC ENABLE_BASEFW with clock config
7. DSP replies IPC_REPLY_OK
8. Driver loads topology manifest (.tplg)
9. Driver creates pipeline widgets via IPC_TPLG_*
10. FW ready for stream operations
```

### 4.3 IPC Message Types (Common)

| Message | Direction | Purpose |
|---------|-----------|---------|
| `IPC_GLB_ROM_CONTROL` | Host→DSP | Trigger ROM boot phase |
| `IPC_GLB_ENABLE_BASEFW` | Host→DSP | Enable base firmware services |
| `IPC_TPLG_COMP_NEW_INSTANCE` | Host→DSP | Create pipeline component |
| `IPC_STREAM_PCM_PARAMS` | Host→DSP | Set PCM stream parameters |
| `IPC_STREAM_PCM_TRIGGER` | Host→DSP | Start/stop/pause/resume stream |
| `IPC_BOOT_STATUS` | DSP→Host | Boot status code (0 = success) |
| `IPC_GLB_NOTIFY_EXCEPTION` | DSP→Host | DSP firmware exception/panic |

### 4.4 D0i3 Entry (Windows SOF Behavior)

```
1. All audio pipelines stopped or paused
2. Driver sends IPC D0I3_REQUEST to DSP
3. DSP saves state to LP-SRAM, gates HP-SRAM
4. DSP sends IPC D0I3_COMPLETE
5. Driver clears IPC BUSY bit
6. Driver sets ADSPCS.SPA[0] = 0 (stall cores)
7. ACE power gate PG2 may be gated by PMC
```

> **Validation note**: If D0i3 entry takes > 10 ms, suspect outstanding IPC
> pending (DSP waiting for topology teardown). Check `intelaud.sys` log for
> `D0I3_REQUEST_TIMEOUT` event.

### 4.5 Debug: SOF DSP Trace

```powershell
# Windows SOF driver logging (if debug build installed):
# C:\Windows\System32\drivers\intelaud_trace.etl

# ETW provider GUID for intelaud.sys:
# Query from driver INF: ProviderGUID = {<check INF for current value>}

# Windows Event Log: Microsoft-Windows-Audio/Operational
Get-WinEvent -LogName "Microsoft-Windows-Audio/Operational" -MaxEvents 100 |
  Where-Object { $_.Message -like "*SOF*" -or $_.Message -like "*DSP*" }
```

---

## 5. intelpch_dmic.sys — DMIC Driver

### 5.1 Responsibilities
- PDM clock generation (DMIC_CLK output to microphone)
- FIFO management for PDM→PCM decimation pipeline
- Privacy mode: mute DMIC_DATA input line, assert privacy LED GPIO
- Power management: gate DMIC clock when no capture active

### 5.2 Privacy Mode Behavior

```
Privacy Mode ON:
  1. DMIC_DATA input electrically muted (register gate, not physical disconnect)
  2. LED GPIO toggled via ACPI DSM or direct write (platform-specific)
  3. Capture pipeline continues but outputs silence (all-zeros PCM)

Privacy Mode OFF:
  1. DMIC_DATA input unmuted
  2. LED GPIO cleared
  3. Normal capture resumes within one FIFO flush period
```

> **Validation**: Use TTK3-COMM GPIO to verify LED GPIO toggles on privacy change.

### 5.3 Key BIOS Dependency

| Knob | Required Value | Effect |
|------|---------------|--------|
| `DmicEnable` | Enabled | DMIC sub-IP powered; driver loads |
| `DmicClockSource` | AudioPLL | Accurate clock for SNR; avoid RING_OSC |
| `DmicMicBias` | Platform-specific | Microphone bias voltage |

---

## 6. intcbt_offload.sys — BT HFP Offload

### 6.1 Responsibilities
- SSP (I2S) port configuration for CNVi BT audio interface
- BCLK rate selection: 8 kHz SCO (256 kHz BCLK) or 16 kHz SCO (512 kHz BCLK)
- Power gate interaction: BCLK must re-lock after power gate exit (HSDES-003)

### 6.2 BCLK Recovery After PG Exit

```
Issue (HSDES-003): SSP BCLK inversion lost after power gate exit
Root cause: SSP BCLK polarity bit not re-programmed on PG resume
Workaround: Driver re-writes SSP config registers on every D0 resume
Validation: ssp_bclk_pg_recovery.py — power gate SSP, resume, verify BCLK
```

---

## 7. Driver Version Tracking

| Driver | Min Validated Version | Notes |
|--------|----------------------|-------|
| `intcaudiobus.sys` | Check via OneBKC audio component | Must match BIOS audio blob version |
| `intcpchsnd.sys` | Check via OneBKC | SoundWire host controller |
| `intelaud.sys` | Check via OneBKC | SOF FW version bundled inside driver package |
| `intelpch_dmic.sys` | Check via OneBKC | Part of audio driver package |
| `intcbt_offload.sys` | Check via OneBKC | Bundled with CNVi BT driver package |

> **Always verify against OneBKC release** (`onebkc` skill → audio component) before
> flashing/installing drivers. Mismatched driver + BIOS versions are the #1 cause of
> "codec not found" failures at BKC checkout.

---

## 8. Windows Audio ETW / Debug Channels

| Channel | Path | Contents |
|---------|------|----------|
| Windows Audio Operational | `Microsoft-Windows-Audio/Operational` | Engine start/stop, device changes |
| Windows Audio Debug | `Microsoft-Windows-Audio/Debug` | Verbose KS pipe events (enable manually) |
| Intel SoundWire | `Intel-SoundWire/Operational` | SDW enum, stream, errors |
| HDA miniport | via ETW GUID in `intcaudiobus.inf` | Verb transactions, CORB/RIRB |
| SOF DSP | via `intelaud.sys` ETW | IPC messages, FW load, D0i3 |

```powershell
# List all Intel audio ETW providers
logman query providers | Select-String -Pattern "Intel.*[Aa]udio|Intc|SOF"
```

---

## 9. Cross-Reference: Driver Gap → HW Sighting

| Driver Gap / Bug | Known HW Sighting | Resolution |
|-----------------|-------------------|-----------|
| CORB/RIRB DMA stall on D3→D0 | BUG-001 | Driver re-init CORB/RIRB base on every D0 resume |
| SDW Seg4 CLK_STOP abort | BUG-002 | FW patch to delay RST until CLK_STOP_OK ACKed |
| DSP core 3/4 clock gate wake | BUG-003 | Driver forces core wake before IPC on PCD-H |
| SSP BCLK polarity lost after PG | HSDES-003 | Driver re-writes SSP config on D0 resume WA |
| HDA hotplug miss at DP3 | HSDES-004 | Driver polls WAKESTS on D3 entry; issue if WAKEEN masked |
