---
name: fv-audio/dsp
description: "DSP core validation — bring-up, firmware load, IPC messaging, SRAM management, pipeline configuration"
version: "1.1.0"
owner: huiyingt
platform: NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL
---

# DSP Core Validation

Validate DSP core bring-up, firmware loading, IPC (Inter-Processor Communication) messaging, SRAM management, and audio pipeline configuration.

> **Scope:** HiFi5/HiFi4/LX7 Tensilica DSP cores, ULP core, SRAM power gating, IPC mailbox, BAR2 domain, pipeline topology.

---

## Multi-Platform DSP Core Comparison

| Platform | ACE | HP Cores | HP Architecture | ULP/ANNA | SRAM | Die Path |
|----------|-----|----------|-----------------|----------|------|----------|
| **NVL PCD-H** | 4.x | 4 HiFi5 | Tensilica HiFi5 | 1 ULP | 4.5 MB | `socket0.pcd.ace` |
| **NVL PCH-S** | 4.x | 2 HiFi5 | Tensilica HiFi5 | 1 ULP + 1 ANNA | 2.25 MB | `socket0.pch.ace` |
| **PTL** | 3.0 | 5 LX7 | Tensilica LX7 | HiFi4 + ANNA | — | `socket0.soc.ace` |
| **WCL** | 3.0 | 5 LX7 | Tensilica LX7 | HiFi4 + ANNA | — | `socket0.soc.ace` |
| **TTL (ACE 4.0)** | 4.0 | 4 HiFi5 | Tensilica HiFi5 | ULP | 3.0 MB | `socket0.pcd.ace` |
| **TTL (ACE 3.0)** | 3.0 | 5 LX7-HiFi4 | Tensilica LX7 | — | 4.6 MB | `socket0.pcd.ace` |
| **RZL** | 4.0 | 4 HiFi5 | Tensilica HiFi5 | ULP | 4.5 MB | `socket0.pcd.ace` |
| **LNL** | 2.x | 5 LX7 | Tensilica LX7 | HiFi4 + ANNA | — | `socket0.soc.ace` |
| **MTL SOC-M** | 1.5 | 3 HiFi4 | Tensilica HiFi4 | ANNA | — | `socket0.soc.ace` |
| **MTL PCH-S** | 1.5 | 2 HiFi4 | Tensilica HiFi4 | ANNA | — | `socket0.pch.ace` |
| **ARL-U** | 1.5 | 3 LX7 | Tensilica LX7 | HiFi4 + ANNA | — | `socket0.pch.ace` |
| **ARL-S** | 1.5 | 2 LX7 | Tensilica LX7 | HiFi4 + ANNA | — | `socket0.pch.ace` |

> **Key architecture differences:**
> - **ACE 4.x (NVL, RZL, TTL ACE4)**: HiFi5 cores — highest performance, largest SRAM
> - **ACE 3.x (PTL, WCL, TTL ACE3)**: LX7 cores — 5 HP cores but different ISA from HiFi5
> - **ACE 2.x (LNL)**: LX7 cores — monolithic SOC die, 4 SoundWire links (vs 5 on newer)
> - **ACE 1.5 (MTL, ARL)**: HiFi4/LX7 cores — earliest generation, 4 SoundWire links

> **⚠️ TTL Dual ACE**: TTL can be fused for ACE 3.0 (5 LX7) or ACE 4.0 (4 HiFi5). Read `ADSPCS` register to determine core count: 4 cores = ACE 4.0, 5 cores = ACE 3.0. Use NVL PCD-H debug procedures for ACE 4.0, PTL procedures for ACE 3.0.

> **⚠️ RZL = NVL PCD-H equivalent**: RZL shares ACE 4.0 architecture, 4 HiFi5 cores, and 4.5 MB SRAM with NVL PCD-H. Apply NVL PCD-H debug procedures directly. Key differences are platform-specific GPIO pad assignments and board-specific codec BOM.

---

## DSP Architecture — NVL Detail

### Core Configuration

| Property | NVL PCD-H | NVL PCH-S |
|----------|-----------|-----------|
| **HP Cores** | 4 HiFi5 (Cores 1-4) | 2 HiFi5 (Cores 1-2) |
| **ULP Core** | 1 (Core 0) | 1 (Core 0) |
| **Architecture** | Tensilica LX / HiFi5 | Tensilica LX / HiFi5 |
| **SRAM** | 4.5 MB | 2.25 MB |
| **ANNA Core** | -- | 1 (38.4/219.4285 MHz) |
| **BAR2 Size** | 2 MB | 2 MB |
| **Enable Bit** | PPCTL.GPROCEN (bit 30) | PPCTL.GPROCEN (bit 30) |

### Core ID Mapping

| Core ID | Type | Use |
|---------|------|-----|
| Core 0 | ULP (Ultra Low Power) | Always-on monitoring, low-power audio tasks |
| Core 1 | HP (High Performance) | Primary audio processing |
| Core 2 | HP (High Performance) | Secondary processing / offload |
| Core 3 | HP (High Performance) | PCD-H only — additional processing |
| Core 4 | HP (High Performance) | PCD-H only — additional processing |

---

## BAR2 — DSP Register Domain

BAR2 provides access to DSP-specific registers and SRAM. It is **only accessible when GPROCEN=1** (PPCTL bit 30).

### BAR2 Region Layout

| Offset Range | Content | Description |
|-------------|---------|-------------|
| DSP Core Regs | Core status, control | Per-core power state, reset, stall |
| IPC Registers | Mailbox, doorbell | Host-to-DSP and DSP-to-host messaging |
| SRAM | Firmware + data | DSP firmware code and data storage |
| SRAM PGCTL | Power gate control | Per-bank SRAM power gating |

### Enabling BAR2 Access

```python
import namednodes as nn
nn.sv.refresh()

# Choose die variant
ace = nn.sv.socket0.pcd.ace  # PCD-H
# ace = nn.sv.socket0.pch.ace  # PCH-S

# Read PPCTL
ppctl = ace.bar0.ppctl.read()
gprocen = (ppctl >> 30) & 1
print("PPCTL: 0x%08X, GPROCEN=%d" % (ppctl, gprocen))

if not gprocen:
    print("Enabling GPROCEN (DSP access)...")
    ppctl |= (1 << 30)
    ace.bar0.ppctl.write(ppctl)
    
    # Verify
    ppctl = ace.bar0.ppctl.read()
    gprocen = (ppctl >> 30) & 1
    print("PPCTL: 0x%08X, GPROCEN=%d — %s" % (ppctl, gprocen, "OK" if gprocen else "FAILED"))

if gprocen:
    print("BAR2 (DSP domain) is now accessible")
    bar2 = ace.cfg.bar2.read()
    print("BAR2 base: 0x%08X" % bar2)
else:
    print("ERROR: Cannot enable GPROCEN — check BIOS DSP setting")
```

---

## DSP Core Bring-Up

### Core Power-Up Sequence

1. **Enable GPROCEN** — Set PPCTL bit 30
2. **Power up SRAM** — Clear SRAM power gate bits
3. **Release core reset** — Clear core reset bit
4. **Un-stall core** — Clear core stall bit
5. **Load firmware** — Write FW image to SRAM
6. **Start core** — Core begins executing from reset vector

### Core Status Verification

```python
# After GPROCEN is enabled, check DSP core status
# Register paths are in BAR2 domain

print("=== DSP Core Status ===")

# Determine max cores based on die
# PCD-H: Cores 0-4 (1 ULP + 4 HP)
# PCH-S: Cores 0-2 (1 ULP + 2 HP)

die = "pcd"  # or "pch"
max_hp_cores = 4 if die == "pcd" else 2

print("Die: %s, Expected HP cores: %d" % (die.upper(), max_hp_cores))

# Read core status registers
# The primary register for DSP core status is **ADSPCS** (Audio DSP Core Status)
# Location: BAR0+0x04 (HDA-compatible offset — verify from ACE HAS for your platform)
#
# ADSPCS bit fields (per-core, repeated for each core):
#   - **CPA** (Core Power Active)  — 1 = core powered on
#   - **SPA** (Set Power Active)   — write 1 to request power-on
#   - **CSTALL** (Core Stall)      — 1 = core is stalled (halted)
#   - **CRST** (Core Reset)        — 1 = core is in reset
#
# On ACE 4.x (NVL), core enable is initiated via PPCTL.GPROCEN (bit 30),
# but ADSPCS remains the standard register for reading core power/reset/stall
# status. ADSPCS fields are per-core bitmasks — check ACE HAS for exact
# bit positions per core ID.

for core_id in range(max_hp_cores + 1):  # +1 for ULP Core 0
    core_type = "ULP" if core_id == 0 else "HP"
    # Read ADSPCS and decode per-core fields
    # adspcs = ace.bar0.adspcs.read()  # or BAR2 path — verify from ACE HAS
    # cpa    = (adspcs >> (core_id + CPA_SHIFT)) & 1
    # crst   = (adspcs >> (core_id + CRST_SHIFT)) & 1
    # cstall = (adspcs >> (core_id + CSTALL_SHIFT)) & 1
    print("  Core %d (%s): [Read ADSPCS — CPA/SPA/CSTALL/CRST bits per core, verify offsets from ACE HAS]" % (core_id, core_type))
```

---

## Firmware Loading

### FW Load Procedure

1. **Verify GPROCEN=1** and BAR2 is accessible
2. **Power up SRAM banks** needed for FW image (clear SRAM PGCTL bits)
3. **Stall all cores** — set ADSPCS.CSTALL per-core bits to prevent execution during load
4. **DMA-based firmware transfer** — The FW image is transferred from **host system memory to DSP SRAM via the DMA engine** (not direct BAR2 MMIO writes). The host driver prepares the FW image in a DMA-accessible buffer, configures the DMA channel (source = host memory, destination = SRAM base), and initiates the transfer. DMA is required because direct BAR2 writes are too slow for multi-MB firmware images and lack burst/streaming capability.
5. **Configure IPC** — set up mailbox, doorbell, interrupts
6. **Release core 0** (ULP) — clear ADSPCS.CRST and CSTALL for Core 0 to start boot loader
7. **Wait for FW ready** signal via IPC (FW_READY message in IPC mailbox)

> **Note:** On SOF (Sound Open Firmware) platforms, the `sof-intel-ipc` driver handles the DMA-based FW load automatically. For bare-metal PythonSV validation, you may write directly to SRAM via BAR2 for small test payloads, but production FW loading always uses DMA.

### FW Image Verification

```python
# After FW load, verify via IPC handshake
# 1. Check IPC mailbox for FW_READY message
# 2. Verify FW version matches expected
# 3. Confirm all expected modules are loaded

print("=== DSP Firmware Status ===")
# Read IPC registers
# ipc_ctl = <read IPC control register>
# ipc_sts = <read IPC status register>
# Check for FW_READY indicator
print("(FW status check via IPC — register paths from HAS)")
```

---

## IPC (Inter-Processor Communication)

### IPC Architecture

IPC provides bidirectional messaging between the host CPU and DSP cores:

| Direction | Mechanism | Use |
|-----------|-----------|-----|
| Host -> DSP | Doorbell + Mailbox | Commands: FW load, pipeline create, parameter set |
| DSP -> Host | Doorbell + Mailbox | Responses, notifications, error reports |

### IPC Message Types

| Type | Description |
|------|-------------|
| **FW_READY** | DSP firmware boot complete |
| **INIT_INSTANCE** | Initialize a processing module |
| **BIND** | Connect pipeline modules |
| **SET_PIPELINE** | Create/configure audio pipeline |
| **SET_PARAMS** | Set module parameters |
| **GET_PARAMS** | Read module parameters |
| **NOTIFICATION** | Asynchronous event from DSP |
| **ERROR** | Error report from DSP |

### IPC Communication Pattern

```python
# Host-to-DSP IPC:
# 1. Write message to IPC mailbox (BAR2 region)
# 2. Set doorbell bit to notify DSP
# 3. Wait for DSP to process and respond
# 4. Read response from DSP mailbox

# DSP-to-Host IPC:
# 1. DSP writes to host mailbox
# 2. DSP sets host doorbell
# 3. Host interrupt fires (or poll)
# 4. Host reads notification/response

print("=== IPC Status ===")
# Read IPC registers from BAR2
# Check doorbell status
# Check mailbox contents
print("(IPC register paths from HAS)")
```

---

## SRAM Management

### SRAM Configuration

| Die | Total SRAM | Banks | Bank Size |
|-----|-----------|-------|-----------|
| **PCD-H** | 4.5 MB | Multiple | Varies by bank |
| **PCH-S** | 2.25 MB | Multiple | Varies by bank |

### SRAM Power Gating

SRAM banks can be individually power-gated to save power when not needed:

```python
# SRAM Power Gate Control (SRAM PGCTL) — BAR2 region
# Each bit controls power gating for one SRAM bank
# 0 = powered on, 1 = power gated

# Read current SRAM power gate status
# sram_pgctl = <read SRAM PGCTL register>
# print("SRAM PGCTL: 0x%08X" % sram_pgctl)

# To power up all SRAM banks:
# Write 0x00000000 to SRAM PGCTL (all banks on)

# To power gate unused banks:
# Set bits for banks not needed by current FW/pipelines
```

### SRAM Allocation Strategy

- **Core 0 (ULP)** — Small SRAM allocation for always-on tasks
- **Core 1-N (HP)** — Larger allocations for audio processing pipelines
- **FW code** — Loaded into SRAM, typically in lower banks
- **FW data/heap** — Upper SRAM banks, dynamically allocated
- **DMA buffers** — SRAM or system memory, depending on pipeline

---

## Audio Pipeline Configuration

### Pipeline Concepts

| Concept | Description |
|---------|-------------|
| **Pipeline** | End-to-end audio data path (capture or playback) |
| **Module** | Processing block within a pipeline (mixer, EQ, volume, etc.) |
| **Binding** | Connection between modules in a pipeline |
| **Widget** | ALSA/ASoC representation of a pipeline element |

### Pipeline Topology Examples

**Playback Pipeline:**
```
Host DMA -> Volume -> Mixer -> DAC -> HDA/SoundWire/SSP Output
```

**Capture Pipeline:**
```
HDA/SoundWire/SSP/DMIC Input -> ADC -> Volume -> Host DMA
```

**Multi-stream:**
```
Host DMA 1 -> Vol -> Mixer -+-> DAC -> Speaker
Host DMA 2 -> Vol ------->-+
```

### Pipeline Verification

```python
# Pipeline status can be verified via:
# 1. IPC queries to DSP for active pipelines
# 2. Stream descriptor status (HDA/SDW/SSP)
# 3. DMA channel status

print("=== Pipeline Status ===")
# Query DSP for active pipeline list via IPC
# For each pipeline:
#   - State (created, running, paused, stopped)
#   - Module chain
#   - Stream association
#   - Buffer status
print("(Pipeline query via IPC)")
```

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| BAR2 reads 0 | GPROCEN not set | Check PPCTL bit 30, enable if 0 |
| Core stuck in reset | Reset not released | Check core reset register in BAR2 |
| Core stalled | Stall bit set or FW crash | Check stall register, read DSP panic info |
| FW load failure | SRAM not powered, wrong image | Verify SRAM PGCTL, check FW image integrity |
| IPC timeout | DSP not running, FW hung | Check core status, verify FW is alive |
| DSP panic | FW crash, invalid memory access | Read panic info from IPC mailbox |
| No audio output | Pipeline not running | Check pipeline state via IPC |
| Wrong core count | Die variant mismatch | PCD-H=4 HP, PCH-S=2 HP — verify die |
| SRAM access error | Bank power-gated | Check SRAM PGCTL, power up needed banks |
| Poor audio quality | Pipeline misconfigured | Check module params, sample rate, bit depth |

### DSP Debug Registers

When the DSP encounters an error, check these areas:

1. **Core status** — Is the core running, stalled, or in panic?
2. **IPC mailbox** — Any pending error notifications?
3. **SRAM PGCTL** — Are all needed banks powered?
4. **Exception info** — DSP exception register (if accessible via BAR2)
5. **Watchdog** — Has the DSP watchdog fired?

---

## DSP Wall Clock Configuration

*Source: [Wiki Page 4014651262]*

The DSP uses a wall clock for scheduling and timestamping. On ACE 4.x (NVL), three clock sources are available:

### DSPWCCTL.DWCS — Wall Clock Source Select

| DWCS Value | Clock Source | Use Case |
|-----------|-------------|----------|
| `00` | **XTAL** (Crystal Oscillator) | Default — accurate (100 ppm), higher power |
| `10` | **WoV Ring Oscillator (CRO)** | Ultra-low-power WoV mode (~300μW), lower accuracy (10K ppm) |
| `11` | **MCLK** (Master Clock) | External MCLK input — see MDIVxCTRL |

> **CRITICAL**: RTC (Real-Time Clock) as DSP wall clock source is **deprecated starting from ACE 4.x**. Do not use RTC-based wall clock on NVL.

### MCLK Source Configuration (MDIVxCTRL)

When DWCS=11 (MCLK), the MCLK source is selected via `MDIVxCTRL.MCDSS`:

| MCDSS Value | MCLK Source |
|------------|-------------|
| `00` | XTAL |
| `01` | Audio Cardinal Clock |
| `10` | Audio PLL Fixed |
| `11` | WoV Ring Oscillator |

The `MDIVxCTRL.MDEDWCS` field selects whether the DSP wall clock uses MCLK (from MCDSS) or XTAL directly.

### Wall Clock Verification

```python
# Read DSP Wall Clock Control register
dspwcctl = ace.bar0.dspwcctl.read()
dwcs = (dspwcctl >> 0) & 0x3  # bits [1:0] = wall clock source

clock_sources = {0: "XTAL", 2: "WoV CRO", 3: "MCLK"}
print("DSPWCCTL: 0x%08X" % dspwcctl)
print("Wall Clock Source (DWCS): %s (%d)" % (clock_sources.get(dwcs, "RESERVED"), dwcs))

# If MCLK selected, check MCLK source
if dwcs == 3:
    # Read MDIVxCTRL for MCLK source selection
    # mdivctrl = ace.bar0.mdiv0ctrl.read()
    # mcdss = (mdivctrl >> X) & 0x3  # MCDSS field offset from HAS
    print("MCLK selected — verify MDIVxCTRL.MCDSS for MCLK source")
```

---

## Xtensa On-Chip Debug (XT-OCD)

*Source: [Wiki Pages 4242636811, 4242636856, 4242636866, 4659487621]*

XT-OCD provides source-level debug of DSP firmware running on the HiFi5 Tensilica cores. This enables breakpoints, single-stepping, memory inspection, and register reads on live DSP cores.

### Prerequisites

| Component | Version / Detail |
|-----------|-----------------|
| **Xtensa Xplorer IDE** | 9.0.20 or later (from Cadence XPG) |
| **XPG Release** | RI-2022.10 or later |
| **XtensaAdapter.dll** | v12.0.7 (32-bit required for tcp_probe) |
| **Debug Probe** | XDP/DCI with TAP access to DSP cores |

### Enabling XT-OCD on NVL

```python
# Step 1: Enable XT-OCD via PythonSV (NVL-specific)
from acelib import ace_bringup
ace_bringup.enable_xt_ocd_nvl()

# Step 2: Start tcp_probe bridge
# tcp_probe translates Xtensa debug protocol over JTAG TAP
# TAP device names vary by platform:
#
# NVL:  NVL0_PCH_ADSP_TSC10 (Core 0), NVL0_PCH_ADSP_TSC20 (Core 1), ...
# PTL:  PTL0_SOC_ADSP_TSC10 (Core 0), PTL0_SOC_ADSP_TSC20 (Core 1), ...
# WCL:  WCL0_SOC_ADSP_TSC10 (Core 0), WCL0_SOC_ADSP_TSC20 (Core 1), ...
# TTL:  TTL0_PCD_ADSP_TSC10 (Core 0), TTL0_PCD_ADSP_TSC20 (Core 1), ...
# RZL:  RZL0_PCD_ADSP_TSC10 (Core 0), RZL0_PCD_ADSP_TSC20 (Core 1), ...
# LNL:  LNL0_SOC_ADSP_TSC10 (Core 0), ...
# MTL:  MTL0_SOC_ADSP_TSC10 (Core 0), ...
#
# ⚠️ TAP names above follow the standard naming convention pattern:
#     <PLATFORM>0_<DIE>_ADSP_TSC<N>0  (N = 1-based core ID)
# Verify exact names via: itp.devicelist  (filter for ADSP)

# tcp_probe command (run from command prompt):
# tcp_probe.exe --topology topology.xml --port 64222
```

### Topology Configuration

Create `topology.xml` for NVL with the correct TAP device names:

```xml
<!-- NVL XT-OCD Topology — map TAP devices to DSP core IDs -->
<topology>
  <core id="0" tap="NVL0_PCH_ADSP_TSC10" />  <!-- ULP Core -->
  <core id="1" tap="NVL0_PCH_ADSP_TSC20" />  <!-- HP Core 1 -->
  <!-- Add TSC30/TSC40/TSC50 for Cores 2-4 on PCD-H -->
</topology>
```

### Connecting Xtensa Xplorer

1. Launch Xtensa Xplorer IDE
2. Create a debug configuration targeting `localhost:64222`
3. Select the core to debug (Core 0 = ULP, Core 1-4 = HP)
4. Load DSP firmware symbols (.elf file)
5. Set breakpoints, step through FW code

### Accessing DSP Core Registers via tcp_probe

```python
# Direct register read via XT-OCD tcp_probe (without Xplorer IDE)
# Useful for scripted register dumps

# tcp_probe exposes a GDB-compatible interface on port 64222
# Connect via telnet or GDB client:
#   target remote localhost:64222

# Read DSP core register (example):
#   monitor reg a0   # Read register a0
#   monitor reg pc   # Read program counter
#   x/16x 0x70000    # Read 16 words at SRAM address 0x70000
```

### Dumping IMR (Isolated Memory Region)

*Source: [Wiki Page 4659487621]*

IMR contains DSP firmware code and data that persists across DSP resets. Dumping IMR is useful for post-mortem FW crash analysis.

> **WARNING**: IMR dump takes **3+ hours** due to the large memory region and JTAG bandwidth limitations. Plan accordingly.

```python
# IMR dump script location — check NVL ACE validation wiki for latest path
# Typical: \\<share>\ace_tools\imr_dump\dump_imr.py

# Usage:
# python dump_imr.py --core 0 --output imr_dump.bin
# Analyze with Xtensa Xplorer: load imr_dump.bin + FW symbols
```

### Multi-Core Debug

When debugging across multiple DSP cores simultaneously:

1. Start `tcp_probe` with topology mapping all cores
2. Open separate Xplorer debug sessions per core (different port offsets)
3. **Core 0 (ULP) handles boot** — always debug Core 0 first for FW load issues
4. HP cores (1-4) handle audio pipelines — debug for stream/processing issues

---

## See Also

- **[fv-audio/power](../power/SKILL.md)** — DSP power domains (D0i3/D3), SRAM power gating, PLL control
- **[fv-audio/interrupts](../interrupts/SKILL.md)** — DSP IPC interrupt routing, MSI configuration
- **[fv-audio/clocking](../clocking/SKILL.md)** — DSP clock domains, Audio PLL, XTAL configuration
- **[fv-audio/soundwire](../soundwire/SKILL.md)** — DSP pipeline endpoints on SoundWire links
- **[fv-audio/hda](../hda/SKILL.md)** — HDA stream management that feeds DSP pipelines
- **[fv-audio/platform](../platform/SKILL.md)** — Per-platform DSP core counts, SRAM sizes, PythonSV paths
- **[dsp/windows.md](windows.md)** — Windows driver DSP firmware loading, IPC, and power management
