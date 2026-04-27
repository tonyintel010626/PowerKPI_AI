---
name: fv-audio/dmic
description: "DMIC (Digital Microphone) validation — PDM interface, clock configuration, FIFO management, gain control, GPIO pad mode verification, and Microphone Privacy Mode"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
---

# FV-AUDIO: DMIC (Digital Microphone) Sub-Skill

> **Scope**: DMIC interface validation on NVL (Novalake) platforms — PDM interface, clock configuration, FIFO management, gain control, and stereo capture across ACE 4.x IP.

---

## Architecture Overview

DMIC (Digital Microphone) uses the PDM (Pulse Density Modulation) interface to capture audio from digital MEMS microphones. The PDM bitstream is received by the ACE DMIC controller, decimated via CIC/FIR filters, and delivered to the DSP for processing.

### Hardware Configuration

| Feature | PCD-H (NVL) | PCD-S (NVL) |
|---------|-------------|-------------|
| DMIC Interfaces | 3 (PDM0, PDM1, PDM2) | 2 (PDM0, PDM1) |
| Channels per Interface | 2 (stereo L/R) | 2 (stereo L/R) |
| Max Total Channels | 6 (3×2ch) | 4 (2×2ch) |
| PDM Clock Rates (DMIC clock) | 0.768 – 4.8 MHz | 0.768 – 4.8 MHz |
| Sample Rates | 16 / 48 kHz | 16 / 48 kHz |
| Bit Depth | 16 / 32-bit | 16 / 32-bit |
| Connection | GPIO pads (CLK + DATA) | GPIO pads (CLK + DATA) |

### Multi-Platform DMIC Configuration

| Platform | ACE Version | DMIC Interfaces | Max Channels | Privacy Mode |
|----------|-------------|-----------------|--------------|--------------|
| NVL PCD-H | ACE 4.x | 3 (PDM0, PDM1, PDM2) | 6 (3×2ch) | Gen1 (MICPVCE=1 default) |
| NVL PCD-S | ACE 4.x | 2 (PDM0, PDM1) | 4 (2×2ch) | Gen1 (MICPVCE=1 default) |
| PTL (Panther Lake) | ACE 3.0 | 2 | 4 (2×2ch) | Gen1 |
| WCL (Wildcat Lake) | ACE 3.0 | 2 | 4 (2×2ch) | Gen1 |
| LNL (Lunar Lake) | ACE 2.x | 2 | 4 (2×2ch) | Gen1 |
| MTL (Meteor Lake) | ACE 1.5 | 2 | 4 (2×2ch) | Gen1 |
| ARL (Arrow Lake) | ACE 1.5 | 2 | 4 (2×2ch) | Gen1 |
| TTL (Titan Lake) | ACE 3.0/4.0 | 2 | 4 (2×2ch) | Gen1 |
| RZL (Razor Lake) | ACE 4.0 | 2 | 4 (2×2ch) | Gen1 |

> NVL PCD-H is unique in having 3 PDM interfaces (PDM2 available). All other platforms have 2 PDMs.
> Interface counts and privacy mode are nominally consistent across ACE 1.5–4.x; consult the platform DMIC HAS section to confirm SKU-specific limitations.

### Per-Platform PDM Clock Source

The PDM clock that drives DMIC microphones is derived from a SoC-level clock source. The source varies by platform and ACE generation, which affects available PDM clock rates and low-power behavior.

| Platform | ACE | PDM Clock Source | Reference Freq | Available PDM Rates | Notes |
|----------|-----|-----------------|----------------|---------------------|-------|
| **NVL PCD-H** | 4.x | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Power-of-2 dividers in PDMCTRL.ClkDiv |
| **NVL PCD-S** | 4.x | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Same clock tree as PCD-H |
| **PTL** | 3.0 | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Shared with WCL; PLL VCO differs from NVL (442.368 MHz) but DMIC uses XTAL path |
| **WCL** | 3.0 | xosc_clk (XTAL) | 38.4 MHz | 4.8 / 2.4 / 1.2 MHz | Identical clock path to PTL |
| **LNL** | 2.x | Audio PLL (XTAL-derived) | 24.576 MHz/N | Consult HAS ¹ | Audio PLL divides XTAL; PDM rates differ from NVL |
| **MTL SOC-M** | 1.5 | Audio PLL **or** RING_OSC | Platform-specific | Consult HAS ¹ | Unique dual-source option; RING_OSC for low-power |
| **MTL PCH-S** | 1.5 | Audio PLL **or** RING_OSC | Platform-specific | Consult HAS ¹ | Same as MTL SOC-M |
| **ARL** | 1.5 | Audio PLL | Platform-specific | Consult HAS ¹ | Similar to MTL architecture |
| **TTL** | 3.0/4.0 | xosc_clk (XTAL) expected | 38.4 MHz expected | Consult HAS ¹ | ACE 3.0 → PTL clocking; ACE 4.0 → NVL clocking |
| **RZL** | 4.0 | xosc_clk (XTAL) expected | 38.4 MHz expected | Consult HAS ¹ | NVL PCD-H clock tree expected |

> ¹ **HAS verification required** — Clock rates for LNL, MTL, ARL, TTL, and RZL have not been verified against the platform ACE Integration HAS. Do not assume NVL clock divider values apply. Query Co-Design: `"DMIC PDM clock divider table <PLATFORM> ACE integration HAS §16"`.

#### S0ix Clock Behavior for DMIC

During S0ix (PC10), the XTAL oscillator (xosc_clk) is **gated** — DMIC cannot capture audio in deep S0ix. The WoV (Wake on Voice) path uses wovc_clk (38.4 MHz RTC PLL) instead, which remains active during S0ix for keyword detection.

| State | PDM Clock | DMIC Capture | WoV Keyword Detect |
|-------|-----------|-------------|-------------------|
| Active (S0) | xosc_clk running | ✅ Normal capture | ✅ Active |
| S0ix (PC10) | xosc_clk **gated** | ❌ No capture | ✅ via wovc_clk |
| D3 | xosc_clk available but DMIC disabled | ❌ Disabled | Depends on WoV arming |

> See `fv-audio/clocking` for full S0ix clock behavior and `fv-audio/wov` for Wake on Voice clock requirements.

### Signal Path

```
MEMS Mic L ──┐                    ┌──────────┐
             ├── PDM DATA ──────► │  DMIC    │     ┌───────┐
MEMS Mic R ──┘        PDM CLK ◄── │Controller│────►│  DSP  │──► Host DMA
                                  │ CIC/FIR  │     │Pipeline│
                                  └──────────┘     └───────┘
```

### BIOS Prerequisites

| BIOS Knob | Required Value | Purpose |
|-----------|---------------|---------|
| HD Audio | Enabled | Master audio enable |
| HD Audio DMIC | Enabled | DMIC interface enable |
| DMIC Link Clock | Auto / Platform-specific | PDM clock source |

---

## Register Map

DMIC registers reside within the DSP BAR2 memory space. Access requires **GPROCEN** (bit 30 of PPCTL, BAR0 + 0x1004) to be set.

### DMIC Controller Registers (BAR2 + DMIC Base)

| Offset | Register | Description |
|--------|----------|-------------|
| 0x00 | DMICLCTL | DMIC Link Control — enable/disable, clock divider |
| 0x04 | DMICIPPTR | DMIC IP Pointer — base address of DMIC SHIM |
| 0x08 | DMICVSPT | DMIC Vendor-Specific Parameters |

### PDM Control Registers (per DMIC instance)

| Offset | Register | Bits | Description |
|--------|----------|------|-------------|
| +0x00 | PDMCTRL | [0] Enable, [3:1] ClkDiv, [7:4] SkewSel | PDM control |
| +0x04 | PDMCFG | [1:0] SampleRate, [3:2] BitDepth, [4] StereoEn | PDM configuration |
| +0x08 | PDMGAIN_L | [7:0] Gain, [15] Mute | Left channel gain |
| +0x0C | PDMGAIN_R | [7:0] Gain, [15] Mute | Right channel gain |
| +0x10 | PDMFIFO | [31:0] Data | FIFO read port |
| +0x14 | PDMFIFOSTS | [4:0] Level, [5] Overrun, [6] Empty | FIFO status |
| +0x18 | PDMCICCTL | [2:0] Decimation, [5:3] Order | CIC filter control |

### Clock Divider Table

| PDM Clock Target | XTAL (38.4 MHz) Divider | ClkDiv[3:1] Encoded | Actual PDM Clock |
|-----------------|------------------------|---------------------|-----------------|
| 4.800 MHz | ÷8 | 0x3 | 4.800 MHz |
| 2.400 MHz | ÷16 | 0x4 | 2.400 MHz |
| 1.200 MHz | ÷32 | 0x5 | 1.200 MHz |
| 0.768 MHz | ÷50 | — ¹ | 0.768 MHz |

> ¹ 0.768 MHz requires a ÷50 ratio which is not a power-of-2. ClkDiv[3:1] uses power-of-2 encoding (0x0=÷1 … 0x7=÷128). Achieving 0.768 MHz may require a combined DMICLCTL + PDMCTRL divider configuration — verify against ACE HAS for your platform.

---

## Initialization Sequence

### Step 1: Verify ACE Enumeration and DMIC Enable

```python
import pysvtools.pciedut as pcie

# Verify ACE is enumerated
ace = pcie.get_dev(0, 31, 3)
did = ace.cfg.read(0x02, 2)
print(f"ACE Device ID: 0x{did:04X}")  # Expect 0xD328 (PCD-H) or 0xD228 (PCH-S)

# Check BAR2 is allocated (DSP memory)
bar2 = ace.cfg.read(0x18, 4) & 0xFFFFF000
print(f"BAR2 base: 0x{bar2:08X}")
assert bar2 != 0, "BAR2 not allocated — check BIOS DSP enable"
```

### Step 2: Enable DSP Access (GPROCEN)

```python
# Read PPCTL and set GPROCEN (bit 30) for BAR2 access
ppctl = ace.bar0.read(0x1004, 4)
ppctl |= (1 << 30)  # GPROCEN
ace.bar0.write(0x1004, ppctl, 4)
```

### Step 3: Configure DMIC Interface

```python
# Enable DMIC Link
dmic_base = bar2 + DMIC_OFFSET  # Platform-specific offset

# Set PDM clock divider for 2.4 MHz
pdmctrl = (1 << 0)    # Enable
pdmctrl |= (0x4 << 1)  # ClkDiv = 0x4 (divide-by-16: 38.4 MHz / 16 = 2.4 MHz)
ace.bar2.write(dmic_base + 0x00, pdmctrl, 4)

# Configure for 48 kHz, 32-bit, stereo
pdmcfg = (0x1 << 0)   # 48 kHz
pdmcfg |= (0x1 << 2)  # 32-bit
pdmcfg |= (0x1 << 4)  # Stereo enable
ace.bar2.write(dmic_base + 0x04, pdmcfg, 4)
```

### Step 4: Set Channel Gain

```python
# Set left channel gain (0 dB = 0x00, steps vary by platform)
ace.bar2.write(dmic_base + 0x08, 0x00, 4)  # L gain = 0 dB, unmuted

# Set right channel gain
ace.bar2.write(dmic_base + 0x0C, 0x00, 4)  # R gain = 0 dB, unmuted
```

---

## Validation Points

### Enumeration Check

| Check | Expected | Debug if Fail |
|-------|----------|---------------|
| DMIC devices in OS | 2 capture endpoints | Check BIOS DMIC knob, GPIO pad mode |
| PDM clock on scope | Matches configured rate | Check clock divider, XTAL source |
| FIFO not empty during capture | PDMFIFOSTS.Empty = 0 | Check mic connection, PDM DATA line |

### Capture Validation

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Basic capture | Record 10s WAV | Non-silent, no glitches, correct sample rate |
| Stereo separation | L/R tone test | Left mic on channel 0, right mic on channel 1 |
| Gain sweep | Record at gain 0, +6, +12, +20 dB | Monotonic amplitude increase |
| Sample rate switch | Switch 16↔48 kHz during idle | Clean switch, correct output rate |
| Multi-mic | Capture from both DMIC interfaces | Independent streams, no cross-talk |

### Power Management

| Test | Method | Pass Criteria |
|------|--------|---------------|
| D3 entry idle | Stop all DMIC capture, wait | ACE enters D3 (PMCSR[1:0] = 0x3) |
| D3 exit resume | Start capture after D3 | Capture resumes < 100ms, no glitch |
| S0ix with DMIC idle | DMIC idle, enter S0ix | S0ix achieved, DMIC not blocking |

### Microphone Privacy Mode

*Source: NVLDP ACE4.x Integration HAS §16.3*

Microphone Privacy Mode provides **hardware-level DMA data zeroing** via a GPIO mic-disable switch, independent of OS software. On NVLDP, this is enabled by default (**MICPVCE=1**). The ACE IP implements Gen1 privacy (VER=0) supporting PDM DMIC and SoundWire data zeroing.

**Architecture:**
```
Privacy Switch (GPIO) ──► Deglitcher (DGE=1) ──► DfMICPVCP Policy ──► DMA Data Zeroing
                    │         (2-flop filter         │                    │
                    │          on resume clk)         │                    ├── PDM DMIC streams
                    │                                 │                    └── SoundWire streams
                    └──► Privacy LED (GPIO output)    │
                    │                                 ├── Dynamic Mode (DDZE=10b)
                    └──► OS Notification (ACPI)       ├── Static Mode (DDZE=11b)
                                                      └── Policy Lock (DDZPL=1)
```

**HW Privacy Registers (DfMICPVCP — Mic Privacy Control Policy):**

| Field | Bits | NVLDP Default | Description |
|-------|------|---------------|-------------|
| MICPVCE | — | 1 (enabled) | Master mic privacy enable — NVLDP default ON |
| VER | — | 0 (Gen1) | Privacy version: Gen1 = PDM DMIC + SoundWire only |
| DDZE | [1:0] | 10b (dynamic) | Data zeroing mode: 00=disabled, 10=dynamic, 11=static |
| DDZPL | [2] | 0 | Policy lock: when 1, FW cannot override zeroing policy |
| FMMD | [3] | 0 | FW managed mode: when 1, disables HW timeout zeroing (trusts FW to zero) |
| DGE | [4] | 1 | Deglitcher enable: 2-flop filter on GPIO input using resume clock |

**Software vs Hardware Registers:**

| Register | Bit | Function |
|----------|-----|----------|
| PDMGAIN_L | [15] Mute | Software mute left channel (0=unmute, 1=mute) — DSP pipeline level |
| PDMGAIN_R | [15] Mute | Software mute right channel (0=unmute, 1=mute) — DSP pipeline level |
| DfMICPVCP | DDZE, DDZPL | **Hardware** DMA data zeroing — operates below DSP, zeros DMA payload |
| GPIO Pad (Privacy Switch) | Platform-specific | Hardware privacy input — active low or active high per platform |
| GPIO Pad (Privacy LED) | Platform-specific | LED output — mirrors privacy switch state |

> **CRITICAL**: Hardware privacy (DfMICPVCP DMA zeroing) is independent of PDMGAIN Mute bits. DMA zeroing operates at the DMA engine level — data is replaced with zeros before reaching host memory. PDMGAIN Mute is a DSP pipeline-level mute. Both must be validated separately.

**Dynamic vs Static Mode:**
- **Dynamic (DDZE=10b)**: Zeroing follows GPIO switch state in real-time. When switch is toggled, zeroing starts/stops within deglitcher latency.
- **Static (DDZE=11b)**: Zeroing is locked ON regardless of GPIO switch state. Used for manufacturing lockdown or enterprise policy enforcement.
- **Policy Lock (DDZPL=1)**: Once set, prevents FW from changing DDZE mode. Intended for BIOS to lock policy before OS loads.
- **FW Managed (FMMD=1)**: Disables HW timeout-based zeroing, trusts DSP FW to implement zeroing logic. Used when FW needs finer-grained control (e.g., WoV keyword detection must bypass privacy during specific DSP states).

**Validation Points:**

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Privacy switch → mute (dynamic) | Toggle hardware privacy switch ON, DDZE=10b | DMIC DMA data zeroed, privacy LED ON |
| Privacy switch → unmute | Toggle hardware privacy switch OFF | DMIC capture resumes, privacy LED OFF |
| Static mode lock | Set DDZE=11b, toggle switch | DMA data stays zeroed regardless of switch |
| Policy lock | Set DDZPL=1, attempt FW DDZE change | FW write to DDZE rejected, policy unchanged |
| FW managed mode | Set FMMD=1, verify FW controls zeroing | HW timeout zeroing disabled, FW manages mute |
| Deglitcher filtering | Rapid toggle GPIO (<1ms pulses) | Transient pulses filtered, no spurious mute/unmute |
| OS notification on mute | Toggle privacy switch, check OS event | OS receives privacy state change notification |
| Privacy persists across D3 | Mute → D3 → D0 → verify still muted | Privacy state preserved across power transitions |
| Privacy persists across S0ix | Mute → S0ix → wake → verify still muted | Privacy state preserved across S0ix |
| SW mute vs HW mute independence | SW mute ON → HW unmute → verify silent | SW mute still active even when HW switch is unmuted |
| SoundWire privacy | Enable SoundWire capture + toggle privacy | SoundWire DMA data also zeroed (Gen1 covers SDW) |
| Privacy LED accuracy | Toggle switch, observe LED state | LED always matches switch position within 100ms |

---

## GPIO Pad Configuration

DMIC uses dedicated GPIO pads for clock and data signals. Pad mode must be set to native function for DMIC.

| Signal | NVL GPIO Pad | PMode | Direction |
|--------|-------------|-------|-----------|
| DMIC_CLK_A | `pm.DMIC_CLK_A` | Native (PMode 1) | Output |
| DMIC_DATA_A | `pm.DMIC_DATA_A` | Native (PMode 1) | Input |
| DMIC_CLK_B | `pm.DMIC_CLK_B` | Native (PMode 1) | Output |
| DMIC_DATA_B | `pm.DMIC_DATA_B` | Native (PMode 1) | Input |

> **CRITICAL**: Always verify GPIO pad mode via PythonSV. Incorrect pad mode is the #1 cause of DMIC not working. Use `fv-lpss/pmode-check` methodology if pads are misconfigured.
>
> **Platform Note**: Pad names above are for NVL (`pm.` community). PTL, LNL, MTL, and ARL use different pad names — consult the platform GPIO pin table.

```python
# NVL: verify DMIC GPIO pad modes via PythonSV
for pad_name in ["DMIC_CLK_A", "DMIC_DATA_A", "DMIC_CLK_B", "DMIC_DATA_B"]:
    pmode = getattr(soc.gpio.pm, pad_name).cfg0.pmode.read()
    print(f"  {pad_name}: pmode={pmode}  ({'Native OK' if pmode == 1 else 'NOT NATIVE - check BOM'})")
```

---

## Platform Debug Approach Routing

When debugging DMIC issues on newer platforms, apply the closest validated debug procedures:

| Platform | ACE | Route To | Rationale |
|----------|-----|----------|-----------|
| **WCL** | 3.0 | PTL procedures | Same ACE 3.0 DMIC controller, same XTAL-derived PDM clock path |
| **TTL (ACE 4.0)** | 4.0 | NVL PCD-H procedures | Same ACE 4.x DMIC controller and PDM clock dividers |
| **TTL (ACE 3.0)** | 3.0 | PTL procedures | Same ACE 3.0 DMIC controller as WCL/PTL |
| **RZL** | 4.0 | NVL PCD-H procedures | Expected identical DMIC subsystem to NVL PCD-H |

> **GPIO pad names differ per platform**: The `pm.DMIC_CLK_A` / `pm.DMIC_DATA_A` pad names shown in the NVL examples above are NVL-specific. WCL/TTL/RZL use different GPIO communities and pad names. Always consult the platform GPIO pin table for correct DMIC pad assignments.
>
> **Privacy Mode**: All platforms (ACE 1.5–4.x) support Gen1 Microphone Privacy (`MICPVCE=1`). No known platform-specific differences in privacy mode behavior.

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No DMIC capture devices in OS | BIOS DMIC disabled or GPIO pad mode wrong | Check BIOS knob `HD Audio DMIC`, verify GPIO pad PMode |
| Capture is silent | PDM clock not running or mic not connected | Scope PDM_CLK pin, check PDMCTRL.Enable, verify mic power |
| Capture has loud noise | Gain too high or CIC filter misconfigured | Reduce gain, check PDMCICCTL decimation ratio |
| FIFO overrun (PDMFIFOSTS.Overrun=1) | DMA not draining fast enough | Check DSP pipeline, increase DMA burst size |
| Only one channel works | Stereo not enabled or one mic dead | Check PDMCFG.StereoEn, swap L/R mics to isolate |
| Capture glitches after D3 exit | DMIC re-init incomplete | Verify full re-init sequence: clock → config → gain → enable |
| DMIC blocking S0ix | Active capture stream preventing D3 | Stop all capture, check residency with `print_s0ix_y_blocking_conditions` |

---

## Related Sub-Skills

- **fv-audio/dsp** — DSP pipeline configuration for DMIC input processing
- **fv-audio/power** — D0i3/D3 transitions affecting DMIC
- **fv-audio/config-checkout** — BIOS and PCI enumeration verification
- **fv-audio/failure-analysis** — NGA failure triage for DMIC test failures
