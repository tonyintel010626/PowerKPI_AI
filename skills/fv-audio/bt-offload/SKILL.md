---
name: fv-audio/bt-offload
description: "BT Audio Offload validation — SSP/I2S interface for BT HFP (SCO/eSCO) voice and A2DP music offload, BCLK configuration, CNVi integration, and power management"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# FV-AUDIO: BT Audio Offload Sub-Skill

> **Scope**: Bluetooth audio offload validation across Intel Client SoC platforms — SSP/I2S interface for BT SCO/eSCO voice and A2DP music offload, SSP register configuration, BCLK/frame sync, CNVi integration, and power management.

---

## Architecture Overview

BT Audio Offload routes Bluetooth audio through the SSP (Synchronous Serial Port) interface on the ACE IP, connecting to the CNVi (Connectivity Integration) Bluetooth controller. This offloads BT audio processing from the host CPU to dedicated hardware.

### Hardware Configuration

| Feature | PCD-H (NVL) | PCD-S (NVL) |
|---------|-------------|-------------|
| SSP Ports | 3 | Platform-dependent |
| BT SSP Port | Typically SSP0 or SSP1 | Typically SSP0 |
| Interface | I2S / PCM | I2S / PCM |
| BCLK Rates | 0.5 – 24 MHz | 0.5 – 24 MHz |
| Sample Rates | 8 / 16 kHz (SCO), 44.1 / 48 kHz (A2DP) | Same |
| Bit Depth | 16 / 24 / 32-bit | 16 / 24 / 32-bit |
| Channels | Mono (SCO) / Stereo (A2DP) | Same |
| Frame Format | I2S, Left-Justified, PCM Short/Long | Same |

### Multi-Platform SSP/BT Offload Configuration

| Platform | ACE Version | SSP Ports | BT SSP | BCLK Source | CNVi Generation | Notes |
|----------|-------------|-----------|--------|-------------|-----------------|-------|
| **NVL PCD-H** | ACE 4.x | 3 | SSP0/SSP1 | 12.288 MHz ext | CNVi 3.0 | Primary validation target |
| **NVL PCD-S** | ACE 4.x | Platform-dep. | SSP0 | 12.288 MHz ext | CNVi 3.0 | Fewer SSP ports than PCD-H |
| **PTL** | ACE 3.0 | 3 ¹ | SSP0/SSP1 ¹ | 12.288 MHz ext ¹ | CNVi 2.0 ¹ | Consult PTL ACE HAS |
| **WCL** | ACE 3.0 | 3 ¹ | SSP0/SSP1 ¹ | 12.288 MHz ext ¹ | CNVi 2.0 ¹ | Same as PTL expected |
| **LNL** | ACE 2.x | 2 ¹ | SSP0 ¹ | Consult HAS ¹ | CNVi 2.0 ¹ | Single SOC die; fewer SSPs |
| **MTL** | ACE 1.5 | 3 ¹ | SSP0/SSP1 ¹ | Consult HAS ¹ | CNVi 2.0 | Verified CNVi BT offload |
| **ARL** | ACE 1.5 | 3 ¹ | SSP0/SSP1 ¹ | Consult HAS ¹ | CNVi 2.0 ¹ | Similar to MTL |
| **TTL** | ACE 3.0/4.0 | 3 ¹ | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | Dual ACE option |
| **RZL** | ACE 4.0 | 3 ¹ | Consult HAS ¹ | Consult HAS ¹ | Consult HAS ¹ | NVL PCD-H arch expected |

> ¹ **HAS verification required** — SSP port count, BT SSP assignment, and BCLK source for non-NVL platforms require verification via the platform ACE Integration HAS. Query Co-Design: `"SSP port configuration <PLATFORM> ACE integration HAS"`.

### BT Audio Offload Path

```
                                    ┌──────────────┐
                                    │   BT Radio   │
                                    │  (CNVi/BT)   │
                                    └──────┬───────┘
                                           │ HCI Audio
                                           ▼
┌─────────┐    ┌─────────┐    ┌──────────────────┐
│  Host   │◄──►│   DSP   │◄──►│     SSP Port     │
│  DMA    │    │ Pipeline│    │ (I2S/PCM Master)  │
└─────────┘    └─────────┘    │  BCLK + FSYNC    │
                              │  TX_DATA / RX_DATA│
                              └──────────────────┘
```

### BT Audio Use Cases

| Use Case | BT Profile | SSP Format | Sample Rate | Channels |
|----------|-----------|------------|-------------|----------|
| Voice Call (HFP) | SCO / eSCO | PCM Short | 8 / 16 kHz | Mono |
| Music Playback | A2DP (SBC/AAC/aptX) | I2S | 44.1 / 48 kHz | Stereo |
| Voice Assistant | SCO / eSCO | PCM Short | 16 kHz | Mono |
| HFP Wideband (mSBC) | SCO / eSCO | PCM Short | 16 kHz | Mono |

---

## SSP Register Map

SSP registers reside within the DSP BAR2 memory space. Each SSP port has its own register block.

### SSP Control Registers (BAR2 + SSP Base, per port)

| Offset | Register | Description |
|--------|----------|-------------|
| +0x00 | SSCR0 | SSP Control Register 0 — enable, frame format, data size |
| +0x04 | SSCR1 | SSP Control Register 1 — clock polarity, FIFO thresholds |
| +0x08 | SSSR | SSP Status Register — busy, RX/TX FIFO level, overrun/underrun |
| +0x0C | SSITR | SSP Interrupt Test Register |
| +0x10 | SSDR | SSP Data Register — FIFO read/write port |
| +0x28 | SSTSA | SSP TX Time Slot Active — active TX time slots |
| +0x2C | SSRSA | SSP RX Time Slot Active — active RX time slots |
| +0x40 | SSCR2 | SSP Control Register 2 — turbo mode, SLV_LAG |
| +0x44 | SSPSP | SSP Programmable Serial Protocol — frame sync timing |
| +0x48 | SSTSS | SSP TX Time Slot Status |
| +0x4C | SSACD | SSP Audio Clock Divider — BCLK divider from source clock |

### Key Register Fields

#### SSCR0 (SSP Control Register 0)

| Bits | Field | Description |
|------|-------|-------------|
| [0] | SSE | SSP Enable (1=active) |
| [4:3] | FRF | Frame Format: 00=SPI, 01=SSP, 10=I2S, 11=PSP |
| [7] | ECS | External Clock Source select |
| [15:8] | SCR | Serial Clock Rate divider |
| [19:16] | EDSS+DSS | Data Size (combined: 3–32 bits) |
| [24] | MOD | Master/Slave mode (0=Master, 1=Slave) |
| [29] | ACS | Audio Clock Source |

#### SSPSP (Programmable Serial Protocol)

| Bits | Field | Description |
|------|-------|-------------|
| [2:0] | SCMODE | Serial Clock Mode (clock polarity/phase) |
| [6:4] | SFRMP | Serial Frame Polarity |
| [8:7] | DMYSTRT | Dummy start cycles |
| [24:16] | SFRMWDTH | Frame sync width (in BCLK cycles) |
| [31:25] | DMYSTOP | Dummy stop cycles |

---

## Configuration Procedures

### SSP Port Initialization for BT SCO

```python
# Step 1: Verify DSP BAR2 access (GPROCEN must be set)
ppctl = ace.bar0.read(0x1004, 4)
assert ppctl & (1 << 30), "GPROCEN not set — enable DSP access first"

# Step 2: Configure SSP for BT SCO (PCM Short Frame, 16kHz mono)
ssp_base = bar2 + SSP0_OFFSET  # Platform-specific

# SSCR0: Master mode, PSP/PCM frame format, 16-bit data
sscr0 = (0x0 << 24)   # MOD=0 (Master)
sscr0 |= (0x3 << 3)   # FRF=11 (PSP/PCM)
sscr0 |= (0xF << 16)  # DSS=15 (16-bit)
ace.bar2.write(ssp_base + 0x00, sscr0, 4)

# SSPSP: PCM Short Frame, frame width = 1 BCLK
sspsp = (0x0 << 0)    # SCMODE=00 (mode 0)
sspsp |= (0x1 << 4)   # SFRMP=1 (active high frame sync)
sspsp |= (0x1 << 16)  # SFRMWDTH=1 (1 BCLK frame sync pulse)
ace.bar2.write(ssp_base + 0x44, sspsp, 4)

# SSACD: Clock divider for 16kHz * 16bits * 1ch = 256kHz BCLK
# Divider from source clock — platform-specific
ace.bar2.write(ssp_base + 0x4C, clk_div, 4)

# Time slots: 1 TX, 1 RX (mono)
ace.bar2.write(ssp_base + 0x28, 0x1, 4)  # SSTSA: slot 0 active
ace.bar2.write(ssp_base + 0x2C, 0x1, 4)  # SSRSA: slot 0 active

# Enable SSP
sscr0 |= (1 << 0)  # SSE=1
ace.bar2.write(ssp_base + 0x00, sscr0, 4)
```

### SSP Port Initialization for BT A2DP (I2S)

```python
# SSCR0: Master mode, I2S frame format, 16-bit stereo
sscr0 = (0x0 << 24)   # MOD=0 (Master)
sscr0 |= (0x2 << 3)   # FRF=10 (I2S)
sscr0 |= (0xF << 16)  # DSS=15 (16-bit)
ace.bar2.write(ssp_base + 0x00, sscr0, 4)

# SSPSP: I2S standard, frame width = 16 BCLK (one channel)
sspsp = (0x0 << 0)     # SCMODE=00
sspsp |= (0x0 << 4)    # SFRMP=0 (I2S standard: low = left)
sspsp |= (16 << 16)    # SFRMWDTH=16 (16 BCLK per channel)
ace.bar2.write(ssp_base + 0x44, sspsp, 4)

# SSACD: Clock divider for 48kHz * 16bits * 2ch = 1.536MHz BCLK
ace.bar2.write(ssp_base + 0x4C, clk_div, 4)

# Time slots: 2 TX, 2 RX (stereo)
ace.bar2.write(ssp_base + 0x28, 0x3, 4)  # SSTSA: slots 0,1 active
ace.bar2.write(ssp_base + 0x2C, 0x3, 4)  # SSRSA: slots 0,1 active

# Enable SSP
sscr0 |= (1 << 0)  # SSE=1
ace.bar2.write(ssp_base + 0x00, sscr0, 4)
```

---

## CNVi Integration

The BT controller is integrated via CNVi (Connectivity Integration). The SSP port provides the audio data path while BT HCI manages the connection.

### BT Audio Offload Flow

```
1. BT HCI establishes SCO/A2DP connection
2. BT driver signals audio offload request to audio driver
3. Audio driver configures SSP port (format, clock, slots)
4. DSP pipeline created: SSP → processing → Host DMA (capture)
                          Host DMA → processing → SSP (render)
5. Audio streams over SSP while BT manages link
6. On disconnect: SSP disabled, pipeline torn down
```

### BIOS Prerequisites

| BIOS Knob | Required Value | Purpose |
|-----------|---------------|---------|
| HD Audio | Enabled | Master audio enable |
| HD Audio DSP | Enabled | DSP required for SSP pipeline |
| CNVi BT Audio Offload | Enabled (if present) | Platform-specific BT offload enable |
| BT Interface | SSP (not UART) | Route BT audio to SSP, not UART |

---

## Validation Points

### Enumeration & Configuration

| Check | Expected | Debug if Fail |
|-------|----------|---------------|
| SSP port visible in DSP topology | SSP node in pipeline graph | Check BIOS DSP enable, GPROCEN |
| BT controller paired | BT device connected | Check BT driver, CNVi enumeration |
| Audio offload path active | SSP SSSR shows active transfer | Check SSCR0.SSE=1, verify BT offload enabled in driver |

### Audio Quality

| Test | Method | Pass Criteria |
|------|--------|---------------|
| BT SCO voice call (NB) | Make call via BT headset, CVSD codec | Clear voice both directions, no echo, 8 kHz NB |
| BT HFP wide-band (WBS) | Make call, verify mSBC codec negotiation | Clear 16 kHz wide-band voice, mSBC in AT+BCS |
| BT HFP codec switch | Force NB↔WB switch mid-call | Clean codec renegotiation, no audio drop |
| BT A2DP playback (SBC) | Play music via BT speaker, SBC codec | Clean stereo, no dropouts, 44.1/48 kHz |
| BT A2DP playback (AAC) | Play music via AAC-capable BT device | AAC codec selected, clean stereo output |
| BT SCO ↔ A2DP switch | Switch between call and music | Clean transition < 1s, correct profile switch |
| BT range test | Move device to 10m distance | Audio stable at range, graceful degrade |
| Multi-BT device | Connect 2 BT audio devices | Correct routing, no cross-talk |

### HFP Profile Validation

HFP (Hands-Free Profile) uses SCO/eSCO links for voice. Two codec modes must be validated:

| Mode | Codec | Sample Rate | Frame | SSP Config |
|------|-------|-------------|-------|------------|
| Narrow-band (NB) | CVSD | 8 kHz | PSP/PCM mode (FRF=11) | BCLK = 256 kHz, 16-bit slots |
| Wide-band (WBS) | mSBC | 16 kHz | PSP/PCM mode (FRF=11) | BCLK = 512 kHz, 16-bit slots |

```
## HFP codec negotiation flow
# 1. HFP SLC (Service Level Connection) established
# 2. AG sends AT+BAC (available codecs) → HF responds
# 3. AG sends AT+BCS=<codec_id> to select codec
#    codec_id=1 → CVSD (NB), codec_id=2 → mSBC (WB)
# 4. SSP reconfigured for selected codec rate
# 5. eSCO link established with chosen parameters
```

> **CRITICAL**: When HFP switches between NB (CVSD) and WB (mSBC), the SSP must be reconfigured for the new sample rate. Verify SSACD divider and BCLK update during codec renegotiation.

### Power Management

| Test | Method | Pass Criteria |
|------|--------|---------------|
| SSP power gate (idle) | Disconnect BT audio, wait | SSP clock gated, ACE can reach D3 |
| D3 with BT connected (no audio) | BT paired but no stream | ACE enters D3 |
| S0ix with BT audio idle | BT connected, no audio stream | S0ix achieved |
| BT reconnect after S3 | Sleep → wake → BT audio | Audio resumes after reconnect |

---

## Known Issues

| ID | Description | Platform | Workaround |
|----|-------------|----------|------------|
| HSDES-003 | SSP BCLK inversion lost after power gate exit | PCD-S | Re-configure SSPSP.SCMODE after power gate exit |

---

## LE Audio (Bluetooth Low Energy Audio) — Future Offload Path

> **Status**: LE Audio offload via ACE SSP is **not yet validated** on current platforms (NVL, PTL). This section documents the expected architecture for future enablement.

### What is LE Audio?

Bluetooth LE Audio (defined in Bluetooth 5.2+) introduces the **LC3 codec** and **Isochronous Channels (ISO)** for audio transport, replacing the classic HFP SCO/eSCO voice path and A2DP SBC music path.

| Feature | Classic BT Audio | LE Audio |
|---------|-----------------|----------|
| **Codec** | CVSD/mSBC (HFP), SBC/AAC (A2DP) | LC3 (mandatory), LC3plus (optional) |
| **Transport** | SCO/eSCO (voice), L2CAP (music) | ISO channels (both) |
| **Multi-stream** | Single stream per device | Multiple streams (Broadcast, Multi-device) |
| **Hearing aid support** | Limited | Native (ASHA profile) |
| **Power efficiency** | Moderate | Improved (LC3 at lower bitrate = same quality) |
| **Latency** | ~40ms (A2DP) | ~20ms (ISO low-latency mode) |

### Expected SSP Offload for LE Audio

When LE Audio offload is enabled on future platforms, the SSP interface is expected to carry LC3-encoded audio between the ACE DSP and the CNVi BT controller, similar to the existing BT offload architecture:

```
Host DSP ──► SSP (I2S/TDM) ──► CNVi BT Controller ──► BT LE Audio (LC3)
```

| Parameter | Expected LE Audio Config |
|-----------|------------------------|
| **SSP port** | Same SSP used for classic BT offload (platform-dependent) |
| **Sample rate** | 8/16/24/32/48 kHz (LC3 supports all) |
| **Bit depth** | 16 or 24 bit |
| **BCLK** | Reconfigured based on LC3 frame duration (7.5ms or 10ms) |
| **Codec location** | DSP (host-side LC3 encode/decode) or BT controller (offloaded LC3) |

### Validation Readiness Checklist (for future LE Audio offload)

- [ ] CNVi BT firmware supports LE Audio ISO channels
- [ ] Windows BT stack supports LE Audio profiles (available in Windows 11 24H2+)
- [ ] BIOS SSP configuration supports LC3 frame timing
- [ ] DSP FW pipeline includes LC3 encoder/decoder module
- [ ] ACX driver model supports LE Audio endpoint creation
- [ ] SSP BCLK reconfiguration for LC3 frame boundaries verified

> **NOTE**: Until LE Audio offload is officially enabled and validated, BT audio testing should focus on the classic HFP/A2DP offload path documented above.

---

## PythonSV — SSP Register Dump

Use this script to capture the complete SSP port state for BT audio offload debug:

```python
def dump_ssp_state(soc, ssp_port=0, bar2_base=None):
    """Dump SSP port registers for BT audio offload debug.

    Args:
        soc: PythonSV SoC handle
        ssp_port: SSP port number (0, 1, or 2)
        bar2_base: BAR2 base address (reads from PCI config if None)
    """
    import pysvtools.pciedut as pcie

    ace = pcie.get_dev(0, 31, 3)
    if bar2_base is None:
        bar2_base = ace.cfg.read(0x18, 4) & 0xFFFFF000
    assert bar2_base != 0, "BAR2 not allocated — check BIOS DSP enable"

    # SSP base offsets are platform-specific; typical NVL offsets:
    SSP_OFFSETS = {0: 0x00000, 1: 0x01000, 2: 0x02000}  # Verify against HAS
    ssp_base = bar2_base + SSP_OFFSETS.get(ssp_port, 0)

    print(f"{'=' * 60}")
    print(f"SSP{ssp_port} REGISTER DUMP (base=0x{ssp_base:08X})")
    print(f"{'=' * 60}")

    regs = {
        'SSCR0':  (0x00, 4, 'SSP Control 0'),
        'SSCR1':  (0x04, 4, 'SSP Control 1'),
        'SSSR':   (0x08, 4, 'SSP Status'),
        'SSITR':  (0x0C, 4, 'SSP Interrupt Test'),
        'SSTSA':  (0x28, 4, 'TX Time Slot Active'),
        'SSRSA':  (0x2C, 4, 'RX Time Slot Active'),
        'SSCR2':  (0x40, 4, 'SSP Control 2'),
        'SSPSP':  (0x44, 4, 'Programmable Serial Protocol'),
        'SSTSS':  (0x48, 4, 'TX Time Slot Status'),
        'SSACD':  (0x4C, 4, 'Audio Clock Divider'),
    }

    for name, (offset, width, desc) in regs.items():
        try:
            val = ace.bar2.read(ssp_base + offset, width)
            print(f"  {name:8s} (+0x{offset:02X}) = 0x{val:08X}  # {desc}")
        except Exception as e:
            print(f"  {name:8s} (+0x{offset:02X}) = READ ERROR: {e}")

    # Decode key fields from SSCR0
    try:
        sscr0 = ace.bar2.read(ssp_base + 0x00, 4)
        sse = sscr0 & 1
        frf = (sscr0 >> 3) & 0x3
        mod = (sscr0 >> 24) & 1
        scr = (sscr0 >> 8) & 0xFF
        frf_names = {0: 'SPI', 1: 'SSP', 2: 'I2S', 3: 'PSP/PCM'}
        print(f"\n  SSCR0 decode: SSE={sse} FRF={frf_names.get(frf, '?')} MOD={'Slave' if mod else 'Master'} SCR={scr}")

        # Decode SSSR
        sssr = ace.bar2.read(ssp_base + 0x08, 4)
        bsy = (sssr >> 4) & 1
        rfl = sssr & 0xF
        tfl = (sssr >> 8) & 0xF
        ror = (sssr >> 7) & 1
        print(f"  SSSR decode:  BSY={bsy} RFL={rfl} TFL={tfl} ROR(overrun)={ror}")
    except Exception:
        pass

    print(f"{'=' * 60}")
```

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No BT audio, BT connected | Offload not enabled or SSP misconfigured | Check SSCR0.SSE, verify BT offload registry/driver setting |
| BT audio choppy/dropouts | Clock mismatch or FIFO underrun | Check SSSR for underrun, verify BCLK rate matches BT profile |
| One-way audio (SCO) | TX or RX time slot not active | Check SSTSA/SSRSA, verify both directions configured |
| Echo on voice calls | Loopback or AEC failure | Check DSP echo cancellation pipeline, verify no HW loopback |
| BCLK wrong frequency | Clock divider misconfigured | Measure BCLK on scope, recalculate SSACD divider |
| Audio artifacts after power gate | SSP state lost on power gate | Known issue HSDES-003 — re-init SSP after power gate exit |
| BT audio blocking S0ix | Active SSP stream preventing D3 | Disconnect BT audio, check SSP is disabled, verify ACE PMCSR |
| No audio after BT reconnect | Pipeline not re-created | Verify DSP pipeline teardown/recreate on BT disconnect/reconnect |

---

## Related Sub-Skills

- **fv-audio/dsp** — DSP pipeline for BT audio processing (AEC, NR, AGC)
- **fv-audio/power** — D0i3/D3 impact on SSP and BT audio path
- **fv-audio/config-checkout** — BIOS and PCI enumeration verification
- **fv-audio/failure-analysis** — NGA failure triage for BT audio test failures
