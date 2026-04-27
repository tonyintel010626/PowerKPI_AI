# Audio ACE HAS Extraction
<!-- owner: huiyingt | platform: NVL, PTL, MTL, LNL | last updated: 2026-04-01 -->
<!-- companion to: ../SKILL.md | source: ACE 4.x Integration HAS via Co-Design -->

> **IMPORTANT — Live HAS First**: This doc captures key architectural facts known at
> rev1.9.5. For register-level offsets, bit-field definitions, and reset defaults,
> **always query Co-Design** (`codesign_api.py ask-projects`) first. Never trust cached
> offsets across platform generations.

---

## 1. ACE Block Overview

ACE (Audio and Control Engine) is the Intel SoC audio subsystem IP block. Versions:

| ACE Version | Platforms | DSP Core | SoundWire Links | DMIC Support |
|-------------|-----------|----------|-----------------|--------------|
| ACE 1.5 | MTL, ARL | HiFi4 + ANNA | 4 | Yes |
| ACE 2.x | LNL | LX7 + HiFi4 + ANNA | 4 | Yes |
| ACE 3.0 | PTL, WCL | LX7 + HiFi4 + ANNA | 5 | Yes |
| ACE 4.x | NVL | HiFi5 HP + ULP (PCD-H) / HiFi5 HP + ULP + ANNA (PCD-S) | 5 segments | Yes |

> For ACE 1.x/2.x/3.x offsets query Co-Design: platform-specific HAS docs differ substantially.

---

## 2. ACE 4.x Sub-IP Inventory

```
ACE 4.x
├── HDA Controller (Intel High Definition Audio)
│   ├── CORB (Command Outbound Ring Buffer)
│   ├── RIRB (Response Inbound Ring Buffer)
│   ├── Stream Descriptors (Input/Output/Bidirectional)
│   └── WAKEEN / WAKESTS for jack detect
├── SoundWire Host Controller
│   ├── Segment 0 — primary codec link (Realtek RT722)
│   ├── Segment 1 — secondary codec link
│   ├── Segment 2 — tertiary (NVL PCD-H only)
│   ├── Segment 3 — quaternary (NVL PCD-H only)
│   └── Per-segment: SyncPrd, CLK_STOP, Wake
├── DSP Subsystem
│   ├── HiFi5 cores (NVL PCD-H: 4 cores, NVL PCH-S: 2 cores)
│   ├── HP-SRAM (high-performance SRAM)
│   ├── LP-SRAM (low-power SRAM)
│   ├── IPC registers (HIPCT/HIPCTE/HIPCI/HIPCIE)
│   └── Firmware loader (DMA-based, via ADSP Loader)
├── DMIC Controller
│   ├── PDM 0 (2 channels)
│   ├── PDM 1 (2 channels)
│   └── PDM 2 (2 channels, NVL PCD-H only)
├── SSP / I2S Controller
│   ├── SSP0 (BT HFP offload on CNVi)
│   └── SSP1 (optional secondary)
└── Power Management
    ├── HDAPLLCTL — Audio PLL control
    ├── SRAM power gate control (HP-SRAM, LP-SRAM)
    ├── IP clock gates (per sub-IP)
    └── PMC sideband messages (D3/D0 transitions)
```

---

## 3. PCI Configuration Space Summary

| Field | NVL PCD-H | NVL PCH-S | PTL |
|-------|-----------|-----------|-----|
| BDF | B0:D31:F3 | B0:D31:F3 | B0:D31:F3 |
| VID | 0x8086 | 0x8086 | 0x8086 |
| DID | 0xD328 | 0xD228 | *query Co-Design* |
| SubCls | 0x01 (Audio) | 0x01 | 0x01 |
| BAR0 | 512 KB (HDA regs) | 512 KB | 512 KB |
| BAR1 | 4 KB (SRAM/link) | 4 KB | 4 KB |
| BAR2 | 2 MB (DSP MMIO) | 2 MB | 2 MB |
| MSI-X | Supported | Supported | Supported |
| D3hot | Supported | Supported | Supported |

---

## 4. ACE Power Architecture

### 4.1 Power States

| State | Description | DSP | SoundWire | HDA | DMIC |
|-------|-------------|-----|-----------|-----|------|
| D0 | Fully active | Running FW | Streaming | Verbs OK | Capturing |
| D0i3 | Active idle | Suspended | CLK_STOP | Idle | Gated |
| D3hot | Software-off | FW unloaded | CLK_STOP | Codec reset | Off |
| D3cold | Hardware-off | No power | No power | No power | No power |

### 4.2 Power Domains

```
ACE Power Gate Structure:
  PG0 (Always-on)     ← PMC sideband, wake logic
  PG1 (HDA/SoundWire) ← Gated in D3; PMC controls via sideband
  PG2 (DSP)           ← Gated independently; SRAM retains in D0i3
  PG3 (DMIC)          ← Gated when no capture active
```

> For per-register bit definitions in HDAPLLCTL, SRAM_PGCTL, PMC sideband message IDs:
> **query Co-Design with platform + register name**.

### 4.3 S0ix Interaction

- ACE must complete D0i3 entry for S0ix gate to open
- PMC waits for ACE LTR ≤ exit-latency budget before allowing XTAL off
- If ACE DSP firmware is loaded and active, D0i3 is blocked
- `print_s0ix_y_blocking_conditions` will list ACE as blocker if LTR not satisfied

---

## 5. DSP Firmware Architecture (SOF)

### 5.1 Firmware Load Sequence

```
1. Driver triggers FW load via ADSP DMA
2. HP-SRAM mapped, FW image DMA'd
3. DSP cores released from reset (per-core CRESET bit)
4. DSP boots → sends IPC BOOT_STATUS to host
5. Host sends IPC ENABLE_BASEFW
6. DSP ACKs → ready for pipeline creation
7. Pipelines created via IPC (topology manifest)
```

### 5.2 IPC Register Map (conceptual — verify offsets via Co-Design)

| Register | Direction | Purpose |
|----------|-----------|---------|
| HIPCT | DSP→Host | Trigger: DSP sent message |
| HIPCTE | DSP→Host | Extension: 64-bit payload high |
| HIPCI | Host→DSP | Initiate: host sending message |
| HIPCIE | Host→DSP | Extension: 64-bit payload high |
| HIPCS | Status | IPC status (busy/done bits) |

### 5.3 FW Error Codes (common)

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 0x1 | BOOT_FAILED | HP-SRAM not accessible, clock issue |
| 0x2 | IPC_TIMEOUT | Host/DSP handshake timeout |
| 0x3 | PIPELINE_ERROR | Topology manifest error |
| 0x4 | DMAC_ERROR | DMA controller fault during FW load |
| 0x5 | CLOCK_ERROR | Audio PLL not locked |

> Full error code table: query Co-Design with `ACE DSP IPC error codes`.

---

## 6. HDA Controller Architecture

### 6.1 CORB/RIRB Operation

```
CORB (Command):
  - Circular ring buffer in system memory
  - Host writes codec verbs at CORBWP (write pointer)
  - Controller reads from CORBRP (read pointer)
  - Max 256 entries × 4 bytes = 1 KB

RIRB (Response):
  - Circular ring buffer in system memory
  - Controller writes codec responses at RIRBWP
  - Host reads interrupt on N responses (RINTCNT)
  - Max 256 entries × 8 bytes = 2 KB
  - Includes unsolicited responses (tag in bits[31:26])
```

### 6.2 Stream Descriptor Layout

```
Per-stream descriptor:
  CTL[2:0]  — control/status
  STS       — stream status (BCIS, FIFOE, DESE)
  LPIB      — link position in buffer
  CBL       — cyclic buffer length
  LVI       — last valid index (BDL entries)
  FIFOS     — FIFO size
  FMT       — stream format (rate, bits, channels)
  BDL[]     — buffer descriptor list pointer
```

### 6.3 Codec Verb Structure

```
31:28  — Codec address (CAd)
27:20  — Node ID (NID)
19:8   — Verb ID
7:0    — Payload
```

Common verbs:
| Verb | ID | Usage |
|------|----|-------|
| GET_PARAM | 0xF00 | Read codec capability |
| SET_CONNECT | 0x701 | Connect path nodes |
| SET_POWER | 0x705 | Set node power state |
| GET_PIN_SENSE | 0xF09 | Jack detection sense |
| SET_UNSOLICITED_ENABLE | 0x708 | Enable unsolicited events |

---

## 7. SoundWire Architecture

### 7.1 Frame Format

```
SoundWire bus frame: 50-frame superframe
  Frame 0: control/sync
  Frames 1-49: data payload + control overhead
  Bit rate: 4.8/6/9.6/12.8 MHz typical
  Dynamic payload width: negotiated during enum
```

### 7.2 Device Discovery Sequence

```
1. Host asserts RST (SCP_CTRL.RST = 1)
2. Host de-asserts RST, begins enumeration
3. Slave broadcasts Ping frame with Dev_Num=0
4. Host assigns address via SCP_ADDRPAGE1/2
5. Host reads DisCo manifest via SCP_DEVID registers
6. Host configures DP (Data Port) parameters
7. Host issues PREPARE/ENABLE to activate stream
```

### 7.3 SoundWire Error Classes

| Class | Meaning | Recovery |
|-------|---------|----------|
| CLK_STOP | Clock stopped (deliberate, low-power) | Resume = CLK_START sequence |
| CLK_FAIL | Unexpected clock loss | Full reset + re-enumeration |
| PARITY | Data parity error | Automatic retry (3×) |
| ACK_NACK | Command not acknowledged | Retry with backoff |
| ABORT | Sequence aborted | Re-init segment |

---

## 8. DMIC Architecture

### 8.1 PDM Interface

```
Physical interface:
  DATA line: serial PDM bitstream (1-bit sigma-delta)
  CLK line: clock from host (1-3.072 MHz typical)
  Per PDM controller: 2 channels (L/R via polarity select)

CIC filter chain:
  Stage 1: CIC decimation (configurable ratio)
  Stage 2: HB1 half-band filter
  Stage 3: HB2 half-band filter
  Stage 4: FIR output (configurable coefficients)
  Output: 16/32-bit PCM at target sample rate
```

### 8.2 Clock Source Selection

| Platform | DMIC Clock Source | Frequency |
|----------|------------------|-----------|
| NVL | Audio PLL (XTAL derived) | 24.576 MHz / N |
| PTL | Audio PLL | 24.576 MHz / N |
| MTL | Audio PLL or RING_OSC | See HAS |
| LNL | Audio PLL | 24.576 MHz / N |

> Exact clock divider register fields: query Co-Design with `ACE DMIC clock configuration`.

---

## 9. Key Acronyms

| Acronym | Meaning |
|---------|---------|
| ACE | Audio and Control Engine |
| SOF | Sound Open Firmware (Intel open-source DSP FW) |
| HDA | High Definition Audio |
| SDW | SoundWire |
| SSP | Synchronous Serial Port (I2S-compatible) |
| DMIC | Digital Microphone Interface |
| CORB | Command Outbound Ring Buffer |
| RIRB | Response Inbound Ring Buffer |
| IPC | Inter-Processor Communication |
| HP-SRAM | High-Performance SRAM (DSP code/data) |
| LP-SRAM | Low-Power SRAM (retained in D0i3) |
| ADSP | Audio DSP |
| BDL | Buffer Descriptor List |
| PDM | Pulse Density Modulation |
| CIC | Cascaded Integrator-Comb (decimation filter) |
| DisCo | Device Codec manifest (SoundWire) |
| UAOL | USB Audio Offload |
| WoV | Wake on Voice |
| LTR | Latency Tolerance Reporting |
| PMC | Power Management Controller |
| PG | Power Gate |
