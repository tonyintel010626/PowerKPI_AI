# Audio Reference Sheets

> **Last updated:** 2026-03-16
> **Scope:** Quick-reference procedures for Audio/ACE bring-up, debug, and validation on NVL (PCD-H, PCH-S)

---

## Reference Sheet 1: Audio Platform Bring-Up

### Pre-Requisites Checklist

Before starting Audio validation, verify:

- [ ] **BIOS**: HD Audio enabled (BIOS setup → Advanced → HD Audio Configuration)
- [ ] **BIOS**: SoundWire links enabled (if SoundWire codecs present on board)
- [ ] **BIOS**: DSP enabled (GPROCEN bit will be set by driver/FW)
- [ ] **PMC firmware**: BKC-compliant version (check with `onebkc` skill)
- [ ] **PCI enumeration**: ACE device visible at 0:31:3 (Device ID D328 PCD-H / D228 PCH-S)
- [ ] **BAR assignment**: BAR0 (HDA, 512KB), BAR1 (ACPI, 4KB) non-zero
- [ ] **Codec presence**: STATESTS (BAR0+0x0E) shows at least one codec detected
- [ ] **PythonSV environment**: `namednodes` import works, `sv.refresh()` succeeds
- [ ] **ITP/DCI connection**: Debugger connected and unlocked (`itp.unlock()`)

### Step-by-Step Bring-Up

#### Step 1: Verify PCI Enumeration

```python
import namednodes as nn
nn.sv.refresh()

# NVL PCD-H
die = nn.sv.socket0.pcd  # PCH-S: socket0.pch

# Check ACE Device ID at 0:31:3
ace_cfg0 = die.ace.hda.cfg.cfg_hi0.read()
vid = ace_cfg0 & 0xFFFF
did = (ace_cfg0 >> 16) & 0xFFFF
print('ACE VID:DID = 0x%04X:0x%04X' % (vid, did))
# Expected PCD-H: 0x8086:0xD328
# Expected PCH-S: 0x8086:0xD228

if vid != 0x8086:
    print('FAIL: ACE not enumerated or disabled in BIOS!')
elif did == 0xD328:
    print('OK: NVL PCD-H ACE detected')
elif did == 0xD228:
    print('OK: NVL PCH-S ACE detected')
else:
    print('WARNING: Unexpected DID 0x%04X — check HAS for this stepping' % did)
```

#### Step 2: Verify BAR Assignment

```python
# Read BAR0 (HDA compatible, 512KB)
bar0 = die.ace.hda.cfg.cfg_bar0.read()
print('BAR0 (HDA) = 0x%08X [%s]' % (bar0, 'OK' if bar0 != 0 else 'FAIL: not assigned!'))

# Read BAR1 (ACPI/PCI config, 4KB)
bar1 = die.ace.hda.cfg.cfg_bar1.read()
print('BAR1 (ACPI) = 0x%08X [%s]' % (bar1, 'OK' if bar1 != 0 else 'FAIL: not assigned!'))

# BAR2 (DSP, 2MB) — only active when GPROCEN=1
bar2 = die.ace.hda.cfg.cfg_bar2.read()
ppctl = die.ace.hda.bar0.ppctl.read()
gprocen = (ppctl >> 30) & 1
print('BAR2 (DSP)  = 0x%08X [GPROCEN=%d]' % (bar2, gprocen))
if bar2 == 0 and gprocen == 0:
    print('INFO: BAR2 inactive — set PPCTL.GPROCEN=1 to enable DSP domain')
```

#### Step 3: Check Codec Detection

```python
# Read Global Control — CRST must be 1 (controller out of reset)
gctl = die.ace.hda.bar0.gctl.read()
crst = gctl & 1
print('GCTL = 0x%08X, CRST=%d [%s]' % (gctl, crst, 'OK' if crst else 'FAIL: controller in reset!'))

# Read STATESTS — bits indicate codec presence on each SDI
statests = die.ace.hda.bar0.statests.read()
print('STATESTS = 0x%04X' % statests)
for sdi in range(4):  # PCD-H has 2 SDI, but check 4 for safety
    if statests & (1 << sdi):
        print('  SDI%d: Codec PRESENT' % sdi)
    else:
        print('  SDI%d: (no codec)' % sdi)
```

#### Step 4: Verify Global Capabilities

```python
# Read GCAP (Global Capabilities)
gcap = die.ace.hda.bar0.gcap.read()
print('GCAP = 0x%04X' % gcap)
print('  64-bit Address: %d' % ((gcap >> 0) & 1))
print('  Num Serial Data Out: %d' % ((gcap >> 1) & 3))
print('  Num Serial Data In: %d' % ((gcap >> 3) & 3))     # PCD-H: 2
print('  Num Bidirectional Streams: %d' % ((gcap >> 5) & 0x1F))
print('  Num Input Streams: %d' % ((gcap >> 8) & 0xF))
print('  Num Output Streams: %d' % ((gcap >> 12) & 0xF))
```

#### Step 5: Check Power State

```python
# Read PMCSR
pmcsr = die.ace.hda.cfg.cfg_pmcs.read()
pstate = pmcsr & 0x3
states = {0: 'D0 (Active)', 1: 'D1', 2: 'D2', 3: 'D3 (Off)'}
print('PMCSR = 0x%08X → %s' % (pmcsr, states.get(pstate, 'Unknown')))
```

#### Step 6: Quick Codec Probe (via CORB/RIRB)

Once CORB/RIRB DMA is running, send a Root Node verb:
```
Verb: 0x000F0000  (codec 0, NID 0, Get Parameter — Vendor ID)
Expected Response: VID:DID of attached codec (e.g., 0x10EC0257 for Realtek ALC257)
```

### Common Bring-Up Failures

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Device ID = 0xFFFF | Device disabled in BIOS or PCH strap | Enable "HD Audio" in BIOS setup |
| BAR0 = 0x00000000 | PCI resource not assigned | Re-enumerate PCI; check for conflicts |
| STATESTS = 0x0000 | No codecs detected | Check CRST (assert reset then deassert); verify board wiring |
| GCTL.CRST = 0 | Controller stuck in reset | Write GCTL.CRST=1; if no effect, check power state |
| BAR2 reads 0x0 | GPROCEN not set | Write PPCTL.GPROCEN=1 (bit 30) |
| DSP core CPA=0 | Core not powered | Set ADSPCS.CSTALL → SPA=1 → wait CPA=1 → clear CSTALL |
| SoundWire no devices | Link not enabled or wrong segment | Check SHIM LCTL SPA bit; verify segment config |
| PythonSV "attribute not found" | Wrong die path | PCD-H: `socket0.pcd`; PCH-S: `socket0.pch` |

---

## Reference Sheet 2: Debug Triage Decision Tree

Use this decision tree when an Audio test fails:

```
Audio Test Failure
│
├─ Device ID = 0xFFFF?
│  ├─ YES → ACE not enumerated
│  │  ├─ Check BIOS "HD Audio" setting
│  │  ├─ Check PCH soft strap (DFx)
│  │  └─ Load: fv-audio/config-checkout
│  └─ NO → Device found, continue...
│
├─ GCTL.CRST = 0 (controller in reset)?
│  ├─ YES → Controller not initialized
│  │  ├─ Write GCTL.CRST=1 (deassert reset)
│  │  ├─ Wait 521us (codec detection time)
│  │  └─ Read STATESTS for codec presence
│  └─ NO → Controller running, continue...
│
├─ STATESTS = 0x0 (no codecs)?
│  ├─ YES → Codec detection issue
│  │  ├─ Toggle CRST: write 0 → wait 100us → write 1 → wait 521us
│  │  ├─ Check HDA link voltage (1.8V only on NVL)
│  │  ├─ Verify board schematic for SDI wiring
│  │  └─ Load: fv-audio/hda
│  └─ NO → Codecs detected, continue...
│
├─ Stream/playback failure?
│  ├─ HDA stream → Check SDCTL/SDSTS for errors
│  │  ├─ FIFO Error (bit 3 SDSTS) → Buffer descriptor list issue
│  │  ├─ Descriptor Error (bit 2 SDSTS) → BDL entry invalid
│  │  └─ Buffer Completion (bit 2 SDCTL) → Normal completion
│  │
│  ├─ SoundWire stream → Load: fv-audio/soundwire
│  │  ├─ Bus clash → Check multi-drop addressing
│  │  ├─ Clock stop failure → Check codec clock stop support
│  │  └─ Device not responding → Re-enumerate segment
│  │
│  └─ SSP/I2S stream → Check SSCR0, SSCR1, SSSR registers
│     ├─ BSY (Busy) stuck → SSP not receiving BCLK
│     ├─ ROR (Rx Overrun) → Consumer too slow
│     └─ TUR (Tx Underrun) → Producer too slow
│
├─ DSP failure?
│  ├─ Firmware load timeout → Load: fv-audio/dsp
│  │  ├─ Check ADSPCS.CPA (Core Power Active)
│  │  ├─ Check SRAM PGCTL (all banks powered?)
│  │  └─ Verify GPROCEN=1 (BAR2 accessible)
│  │
│  ├─ IPC timeout → Load: fv-audio/dsp
│  │  ├─ Check HIPCIDR.BUSY (should clear after DSP acks)
│  │  ├─ Check DSP core not in STALL
│  │  └─ Verify D0i3 state if recently woken
│  │
│  └─ Pipeline creation failure → Load: fv-audio/dsp
│     ├─ Insufficient SRAM → Check SRAM allocation
│     └─ Module load error → Check FW binary compatibility
│
├─ Power management failure?
│  ├─ D3 entry timeout → Load: fv-audio/power
│  │  ├─ Check for active streams (stop all first)
│  │  ├─ Check for codec link not in reset
│  │  └─ Check for DSP cores still active
│  │
│  ├─ S0ix blocked → Load: fv-audio/power
│  │  ├─ Read PMCSR → must be 0x3 (D3)
│  │  ├─ Check PMC S0ix blocker register for ACE
│  │  └─ Verify LTR = "no requirement" when idle
│  │
│  └─ PLL not locking → Load: fv-audio/power
│     ├─ Check HDAPLLCTL for lock status
│     └─ Verify input reference clock
│
├─ BSOD / System crash during audio test?
│  ├─ Check crash dump for audio drivers (IntcAudioBus.sys, IntcOED.sys)
│  ├─ Delegate to FV_Debugger_V1 for BSOD analysis
│  └─ Search Confluence wikis for known crash patterns
│
└─ None of the above?
   ├─ Load: fv-audio/failure-analysis (parse NGA logs)
   ├─ Delegate to FV_Debugger_V1 (wiki search + 8-phase triage)
   └─ Search HSDES with keywords from audio_known_issues.md
```

---

## Reference Sheet 3: Register Quick Reference

### HDA Global Registers (BAR0)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| GCAP | 0x00 | [15:12]:OSS, [11:8]:ISS, [7:3]:BSS, [2:1]:NSDO, [0]:64OK | Stream/SDO counts |
| VMIN | 0x02 | [7:0] | Minor version |
| VMAJ | 0x03 | [7:0] | Major version |
| OUTPAY | 0x04 | [15:0] | Output payload cap |
| INPAY | 0x06 | [15:0] | Input payload cap |
| GCTL | 0x08 | [8]:UNSOL, [0]:CRST | Controller reset, unsolicited enable |
| WAKEEN | 0x0C | [14:0] | Wake enable per SDI |
| STATESTS | 0x0E | [14:0] | SDI change status (codec detect) |
| GSTS | 0x10 | [1]:FSTS | Flush status |
| INTCTL | 0x20 | [31]:GIE, [30]:CIE, [29:0]:SIE | Global/stream interrupts |
| INTSTS | 0x24 | [31]:GIS, [30]:CIS, [29:0]:SIS | Interrupt status |
| CORBLBASE | 0x40 | [31:7] | CORB lower base (128-byte aligned) |
| CORBUBASE | 0x44 | [31:0] | CORB upper base |
| CORBWP | 0x48 | [7:0] | CORB write pointer |
| CORBRP | 0x4A | [15]:RST, [7:0] | CORB read pointer |
| CORBCTL | 0x4C | [1]:RUN, [0]:MEIE | CORB DMA run, mem error IE |
| CORBSTS | 0x4D | [0]:MEI | CORB memory error |
| RIRBLBASE | 0x50 | [31:7] | RIRB lower base |
| RIRBUBASE | 0x54 | [31:0] | RIRB upper base |
| RIRBWP | 0x58 | [15]:RST, [7:0] | RIRB write pointer |
| RIRBCTL | 0x5C | [1]:DMA_EN, [0]:RINTCTL | RIRB DMA run |
| RIRBSTS | 0x5D | [2]:OIS, [0]:RINTFL | RIRB overrun, response int |
| PPCTL | 0x1004 | [30]:GPROCEN | DSP Processing Entity Enable |

### HDA Stream Descriptor Registers (per stream, 0x20 stride from 0x80)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| SDnCTL | +0x00 | [24:20]:STRM, [19:16]:STRIPE, [2]:IOCE, [1]:RUN, [0]:SRST | Stream ID, run, reset |
| SDnSTS | +0x03 | [4]:FIFOERR, [3]:DESE, [2]:BCIS | FIFO/desc errors, completion |
| SDnLPIB | +0x04 | [31:0] | Link Position in Buffer |
| SDnCBL | +0x08 | [31:0] | Cyclic Buffer Length |
| SDnLVI | +0x0C | [7:0] | Last Valid Index |
| SDnFMT | +0x12 | [15:0] | Stream format (rate, bits, channels) |
| SDnBDPL | +0x18 | [31:7] | BDL lower pointer (128-byte aligned) |
| SDnBDPU | +0x1C | [31:0] | BDL upper pointer |

### DSP Registers (BAR2, when GPROCEN=1)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| ADSPCS | 0x04 | [31:24]:CPA, [23:16]:SPA, [15:8]:CSTALL, [7:0]:CRST | Core power/stall/reset per core |
| HIPCIDR | 0x40 | [31]:BUSY, [30:0]:MSG | Host→DSP IPC doorbell + data |
| HIPCIDA | 0x44 | [31]:DONE, [30:0]:MSG | Host→DSP IPC acknowledgement |
| HIPCTDR | 0x48 | [31]:BUSY, [30:0]:MSG | DSP→Host IPC doorbell |
| HIPCTDA | 0x4C | [31]:DONE | DSP→Host IPC acknowledgement |
| SRAM PGCTL | Varies | Per-bank bits | SRAM bank power gate control |

### SoundWire SHIM Registers (offsets relative to SoundWire SHIM base)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| LCTL | +0x04 | [3]:SPA, [2]:CPA, [1:0]:MODE | Link power active, clock mode |
| IPPTR | +0x08 | [31:20]:PTR | IP pointer to link registers |
| SYNC | +0x0C | [0]:SYNCGO | Sync trigger for multi-link |
| CTLSCAP | +0x10 | Capability | Controller-level SoundWire cap |
| CTLS0CM | +0x12 | Clock mode | Clock stop mode config |

---

## Reference Sheet 4: Platform-Specific Quick Reference

### Die Path Mapping

| Platform | Die | PythonSV Base | ACE Root |
|----------|-----|---------------|----------|
| NVL | PCD-H | `socket0.pcd` | `pcd.ace` |
| NVL | PCH-S | `socket0.pch` | `pch.ace` |

### Device ID Mapping

| Die | Primary DID | DID Range | ACE Version |
|-----|-------------|-----------|-------------|
| PCD-H | 0xD328 | D328–D32F | 4.x, 4 HiFi5 HP + 1 ULP |
| PCH-S | 0xD228 | D228–D22F | 4.x, 2 HiFi5 HP + 1 ULP + 1 ANNA |

### Audio Subsystem Counts

| Feature | PCD-H | PCH-S |
|---------|-------|-------|
| HDA SDI Pins | 2 | 2 |
| SoundWire Segments | 5 (Seg 0 = alt iDisp-A) | 4 external + 1 on-die iDisp |
| SSP/I2S Ports | 3 | 3 |
| HiFi5 HP Cores | 4 | 2 |
| ULP Core | 1 (Core 0) | 1 (Core 0) |
| ANNA Core | 0 | 1 |
| SRAM | 4.5 MB | 2.25 MB |
| DMIC | 2 | 2 |

### NGA Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | PASS | None |
| 1 | FAIL | Investigate — load failure-analysis |
| 2 | BLOCKED | Infrastructure issue — check station health |
| 3 | ERROR | Framework error — check PythonSV, VJT init |
| 4 | NOT_RUN | Skipped — check prerequisites |

---

## Reference Sheet 5: Power Management Quick Validation

### ACE Power State Check

```python
import namednodes as nn
nn.sv.refresh()
die = nn.sv.socket0.pcd  # PCH-S: socket0.pch

# Read PMCSR for ACE (0:31:3)
pmcsr = die.ace.hda.cfg.cfg_pmcs.read()
pstate = pmcsr & 0x3
states = {0: 'D0 (Active)', 1: 'D1', 2: 'D2', 3: 'D3 (Off)'}
marker = ' *** S0ix BLOCKER' if pstate != 3 else ''
print('ACE PMCSR = 0x%08X → %s%s' % (pmcsr, states.get(pstate, 'Unknown'), marker))
```

### D-State Transition Test

```python
# Test D0 → D3 → D0 for ACE
ace_cfg = die.ace.hda.cfg

# Read current state
pmcsr = ace_cfg.cfg_pmcs.read()
print('Before: PMCSR = 0x%08X (D%d)' % (pmcsr, pmcsr & 3))

# Pre-req: stop all streams, put links in reset
gctl = die.ace.hda.bar0.gctl.read()
die.ace.hda.bar0.gctl.write(gctl & ~1)  # Assert reset (CRST=0)
import time; time.sleep(0.01)

# Force D3
ace_cfg.cfg_pmcs.write(pmcsr | 0x3)
time.sleep(0.1)
pmcsr_d3 = ace_cfg.cfg_pmcs.read()
print('After D3 write: PMCSR = 0x%08X (D%d)' % (pmcsr_d3, pmcsr_d3 & 3))
assert (pmcsr_d3 & 3) == 3, 'FAIL: D3 entry failed!'

# Return to D0
ace_cfg.cfg_pmcs.write(pmcsr_d3 & ~0x3)
time.sleep(0.1)
pmcsr_d0 = ace_cfg.cfg_pmcs.read()
print('After D0 write: PMCSR = 0x%08X (D%d)' % (pmcsr_d0, pmcsr_d0 & 3))
assert (pmcsr_d0 & 3) == 0, 'FAIL: D0 re-entry failed!'

# Re-initialize: deassert reset
die.ace.hda.bar0.gctl.write(gctl | 1)  # CRST=1
time.sleep(0.001)  # 521us codec detect time
print('PASS: D0 → D3 → D0 transition successful.')
```

### DSP Core Power Check

```python
# Check DSP core states (requires GPROCEN=1 for BAR2 access)
adspcs = die.ace.dsp.bar2.adspcs.read()
print('ADSPCS = 0x%08X' % adspcs)

# PCD-H: 5 cores (Core 0=ULP, Cores 1-4=HP)
# PCH-S: 3 cores (Core 0=ULP, Cores 1-2=HP) + ANNA
num_cores = 5  # Adjust for PCH-S: 3
for i in range(num_cores):
    crst = (adspcs >> i) & 1
    cstall = (adspcs >> (i + 8)) & 1
    spa = (adspcs >> (i + 16)) & 1
    cpa = (adspcs >> (i + 24)) & 1
    core_type = 'ULP' if i == 0 else 'HP%d' % i
    print('Core %d (%s): CRST=%d CSTALL=%d SPA=%d CPA=%d [%s]' % (
        i, core_type, crst, cstall, spa, cpa,
        'ACTIVE' if cpa and not cstall else 'OFF' if not spa else 'STALLED'))
```

### S0ix Blocker Check for ACE

```python
# Complete S0ix readiness check for Audio subsystem
issues = []

# 1. ACE must be in D3
pmcsr = die.ace.hda.cfg.cfg_pmcs.read()
if (pmcsr & 3) != 3:
    issues.append('ACE in D%d (must be D3)' % (pmcsr & 3))

# 2. All HDA links must be in reset
gctl = die.ace.hda.bar0.gctl.read()
if gctl & 1:  # CRST=1 means controller NOT in reset
    issues.append('HDA controller not in reset (GCTL.CRST=1)')

# 3. DSP cores must be powered down (if GPROCEN was set)
ppctl = die.ace.hda.bar0.ppctl.read()
if (ppctl >> 30) & 1:  # GPROCEN=1
    adspcs = die.ace.dsp.bar2.adspcs.read()
    spa = (adspcs >> 16) & 0x1F  # SPA bits for 5 cores
    if spa != 0:
        issues.append('DSP core(s) still powered: SPA=0x%02X' % spa)

if issues:
    print('S0ix BLOCKED by Audio:')
    for iss in issues:
        print('  - %s' % iss)
else:
    print('Audio subsystem S0ix ready.')
```

---

## Reference Sheet 6: HSDES Quick Search

### One-Liner Searches for Common Issues

```bash
# Search for HDA codec detection sightings
python .opencode/skill/hsdes/hsdes_query.py "HDA codec detection STATESTS NVL ACE"

# Search for SoundWire enumeration issues
python .opencode/skill/hsdes/hsdes_query.py "SoundWire enumeration clock stop NVL"

# Search for DSP firmware load failures
python .opencode/skill/hsdes/hsdes_query.py "DSP firmware load timeout ADSPCS NVL"

# Search for S0ix audio blockers
python .opencode/skill/hsdes/hsdes_query.py "S0ix blocker audio ACE D3 NVL"

# Search for SSP/I2S issues
python .opencode/skill/hsdes/hsdes_query.py "SSP I2S BCLK audio NVL"
```

### Wiki Search for BKMs

```bash
# Search FVCommon for Audio debug BKMs
python .opencode/skill/securewiki/securewiki.py search "Audio debug HDA ACE" --spaces fvcommon --user huiyingt --json

# Search DebugEncyclopedia for S0ix Audio
python .opencode/skill/securewiki/securewiki.py search "S0ix Audio ACE" --spaces DebugEncyclopedia --user huiyingt --json

# Search for SoundWire validation procedures
python .opencode/skill/securewiki/securewiki.py search "SoundWire validation" --spaces fvcommon --user huiyingt --json
```
