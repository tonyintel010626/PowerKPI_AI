# LPSS Reference Sheets

> **Last updated:** 2026-03-10
> **Scope:** Quick-reference procedures for LPSS bring-up, debug, and validation on NVL and PTL

---

## Reference Sheet 0: Quick Platform Identification (MUST DO FIRST)

> **Lesson learned:** Do NOT waste time on `systeminfo` (that's the host), TTK3 POST codes, or searching for PythonSV directories. Go straight to `ipccli`.

### Fastest Method: ipccli JTAG TAP Detection (~5 seconds)

```python
# Run: C:\Python310\python.exe identify_platform.py
# Location: C:\pythonsv\novalake\identify_platform.py (pre-installed)
import ipccli, re, sys
ipc = ipccli.baseaccess()
ipc.forcereconfig()
# The banner printed during forcereconfig() contains:
#   "Detected NVL_PCD_CLTAP A0 (H) on JTAG chain 0 at position 0"
# Parse it from IPC log or just read the console output.
```

**One-liner (PowerShell):**
```powershell
& 'C:\Python310\python.exe' 'C:\pythonsv\novalake\identify_platform.py'
```

### What the TAP Banner Tells You

| Banner Pattern | Platform | SKU | Die |
|---------------|----------|-----|-----|
| `NVL_PCD_CLTAP A0 (H)` | Novalake | **H-series** | PCD-H |
| `NVL_PCD_CLTAP A0 (U)` or `(P)` | Novalake | **U/P-series** | PCD-P |
| `NVL_PCH_CLTAP ...` | Novalake | PCH-S die | PCH-S |
| `PTL_...` | Panther Lake | varies | SOC |

### SKU → DID Series Mapping

| SKU | DID Range | Example (I2C0) | PythonSV Die Path |
|-----|-----------|----------------|-------------------|
| NVL-H (PCD-H) | `0xD3xx` | 0xD378 | `socket0.pcd.lpss` |
| NVL-U/P (PCD-P) | `0xD2xx` | 0xD278 | `socket0.pcd.lpss` |
| NVL-S/HX (PCH-S) | `0x6Exx` | 0x6E4C | `socket0.pch.lpss` / `pch0.lpss` |
| PTL | varies | — | `socket0.soc.lpss` |

### Why This Works

`ipccli.baseaccess()` connects to the SUT via DCI (Intel USB Native Debug Class, VID_8087). When `forcereconfig()` scans the JTAG chain, it auto-detects the TAP controller and prints a banner with:
- **Platform family** (NVL, PTL, etc.)
- **Die type** (PCD, PCH, SOC)
- **Stepping** (A0, B0, etc.)
- **SKU variant** (H, U, P)

### Prerequisites

- **DCI connection** must be present (Intel USB Native Debug Class device in Device Manager)
- **Python 3.10** with `ipccli` package: `C:\Python310\python.exe`
- **SUT powered on** (at minimum, DCI link must be alive)

### If ipccli Fails

Fall back to these (in order):
1. **PCI Device ID read** — if namednodes works, read any LPSS DID and match to table above
2. **UART boot log** — capture via TTK3 UART or serial terminal at 115200 baud during boot
3. **SPI/IFWI dump** — read SPI flash via TTK3, search for platform strings
4. **OS-level SMBIOS** — if SUT boots to OS: `wmic csproduct get name` (remote)

---

## Reference Sheet 1: LPSS Platform Bring-Up

### Pre-Requisites Checklist

Before starting LPSS validation, verify:

- [ ] **BIOS**: SerialIO devices enabled (check BIOS setup menu or BIOS knobs)
- [ ] **PMC firmware**: BKC-compliant version (check with `onebkc` skill)
- [ ] **Pad configuration**: LPSS pins muxed to native function (not GPIO)
- [ ] **PCI enumeration**: All LPSS devices visible in `lspci` / Device Manager
- [ ] **BAR assignment**: All controllers have non-zero BAR0 addresses
- [ ] **PythonSV environment**: `namednodes` import works, `sv.refresh()` succeeds
- [ ] **ITP/DCI connection**: Debugger connected and unlocked (`itp.unlock()`)
- [ ] **VJT framework**: `vjt.lpss.lpss_main` imports successfully

### Step-by-Step Bring-Up

#### Step 1: Verify PCI Enumeration

```python
import namednodes as nn
nn.sv.refresh()

# NVL PCD-H example — adjust die path for your platform
die = nn.sv.socket0.pcd  # PTL: socket0.soc

# Check I2C0 Device ID
i2c0_did = die.lpss.i2c0.cfg.cfg_hi0.read()
print('I2C0 DID:VID = 0x%08X' % i2c0_did)
# Expected: upper 16 bits = Device ID, lower 16 bits = 0x8086 (Intel)

# Check all LPSS controllers exist
controllers = ['i2c0','i2c1','i2c2','i2c3','i2c4','i2c5',
               'i3c0','i3c1',  # I3C Ctrl#1 (I3C0+I3C1), Ctrl#2 (I3C2+I3C3)
               'spi0','spi1','spi2','hsuart0','hsuart1','hsuart2']
for ctrl in controllers:
    try:
        node = getattr(die.lpss, ctrl)
        did = node.cfg.cfg_hi0.read()
        vid = did & 0xFFFF
        device_id = (did >> 16) & 0xFFFF
        status = 'OK' if vid == 0x8086 else 'FAIL (VID=0x%04X)' % vid
        print('%s: DID=0x%04X VID=0x%04X [%s]' % (ctrl, device_id, vid, status))
    except Exception as e:
        print('%s: NOT FOUND (%s)' % (ctrl, str(e)))
```

#### Step 2: Verify BAR Assignment

```python
# Read BAR0 for each controller
for ctrl in controllers:
    try:
        node = getattr(die.lpss, ctrl)
        bar0 = node.cfg.cfg_bar0.read()
        status = 'OK' if bar0 != 0 else 'FAIL (BAR=0x0, not assigned!)'
        print('%s BAR0 = 0x%08X [%s]' % (ctrl, bar0, status))
    except:
        print('%s: cannot read BAR' % ctrl)
```

#### Step 3: Verify Pad Mode (Config Checkout)

Load the `fv-lpss/config-checkout` sub-skill for detailed pad verification:
- Check PMode for each LPSS pin
- PMode=0 means GPIO (wrong for LPSS native function)
- PMode=1+ means native function assigned

#### Step 4: Check Power State

```python
# Read PMCSR for each controller
# PMCSR at PCI config offset 0x84 (HAS-verified: LPSS_HAS.html v5.2)
for ctrl in controllers:
    try:
        node = getattr(die.lpss, ctrl)
        pmcsr = node.cfg.cfg_pmcs.read()  # or cfg_pmcsr — name varies
        pstate = pmcsr & 0x3
        states = {0: 'D0', 1: 'D1', 2: 'D2', 3: 'D3'}
        print('%s: PMCSR=0x%08X → %s' % (ctrl, pmcsr, states.get(pstate, '???')))
    except:
        print('%s: cannot read PMCSR' % ctrl)
```

#### Step 5: Initialize VJT Framework

```python
import sys
sys.path.insert(0, r'C:\pythonsv\novalake')  # PTL: C:\pythonsv\pantherlake

from vjt.lpss import lpss_main as lmain

# lmain.lhc.ports contains all discovered LPSS ports
print('Discovered %d LPSS ports:' % len(lmain.lhc.ports))
for p in lmain.lhc.ports:
    print('  %s%d' % (p.protocol, p.port_number))
```

#### Step 6: Run Quick Smoke Test (UART Loopback)

```bash
# Internal loopback — no external wiring needed
python C:\git\applications.ai.ocode.market.skills\.opencode\skill\fv-lpss\run_uart_traffic.py 0 32
```

Expected: 32 bytes sent = 32 bytes received, return code 0.

#### Step 7: Verify Clock Gating (Power Readiness)

Load `fv-lpss/power-state` sub-skill for:
- Trunk clock gate verification
- Functional clock gate verification
- Side clock gate verification
- D0i2/D0i3 entry confirmation

### Common Bring-Up Failures

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Device ID = 0xFFFF | Device disabled in BIOS or in D3 | Enable in BIOS setup; check PMCSR |
| BAR0 = 0x00000000 | PCI resource not assigned | Re-enumerate PCI; check for conflicts |
| Register reads return 0x0 | Wrong BAR or device in D3 | Verify BAR; write PMCSR=0x0 for D0 |
| VJT finds 0 ports | Wrong cltap config or die path | Verify `nvlh_cltap.py` matches your die |
| I3C BUS_ENABLE won't set | See BUG-001 in `lpss_known_issues.md` | Load known issues for workaround |
| UART loopback mismatch | Pad not in native mode | Check PMode via config-checkout |
| PythonSV "attribute not found" | Wrong die path | NVL: `socket0.pcd`; PTL: `socket0.soc` |

---

## Reference Sheet 2: Debug Triage Decision Tree

Use this decision tree when an LPSS test fails:

```
LPSS Test Failure
│
├─ Device ID = 0xFFFF?
│  ├─ YES → Device not enumerated
│  │  ├─ Check BIOS SerialIO settings
│  │  ├─ Check PMCSR (is it in D3?)
│  │  └─ Load: fv-lpss/config-checkout
│  └─ NO → Device found, continue...
│
├─ Register reads = 0x0?
│  ├─ YES → BAR or power issue
│  │  ├─ Check BAR0 assignment
│  │  ├─ Write PMCSR = 0x0 (force D0)
│  │  └─ Load: fv-lpss/config-checkout
│  └─ NO → Registers accessible, continue...
│
├─ Transfer failure (NACK/timeout/abort)?
│  ├─ I2C → Read IC_TX_ABRT_SOURCE (0x80)
│  │  ├─ Bit[0] 7B_ADDR_NOACK → Wrong address or device absent
│  │  ├─ Bit[1] 10B_ADDR1_NOACK → 10-bit addr phase 1 NACK
│  │  ├─ Bit[3] TXDATA_NOACK → Data NACK from slave
│  │  ├─ Bit[5] GC_NOACK → General call NACK
│  │  ├─ Bit[7] SBYTE_NOACK → START byte NACK
│  │  ├─ Bit[12] ARB_LOST → Bus arbitration lost (multi-master)
│  │  ├─ Bit[14] SLV_ARBLOST → Slave arbitration lost
│  │  └─ Bit[16] TX_FLUSH_CNT[31:23] → # bytes flushed from TX FIFO
│  │
│  ├─ I3C → Read response ERR_STATUS[31:28]
│  │  ├─ 0x0 NO_ERR → Check data content, TID matching
│  │  ├─ 0x1 CRC → CRC error in HDR transfer
│  │  ├─ 0x4 ADDR_HDR_NACK → Broadcast NACK → enters HALT
│  │  ├─ 0x5 ADDR_NACK → Address NACK (device not responding)
│  │  ├─ 0x6 OVL_UFL → TX overflow/underflow → enters HALT
│  │  ├─ 0x8 ABORT → Abort issued → enters HALT
│  │  └─ HALT state? → Drain responses, reset queues, set RESUME. See known_issues for sightings.
│  │
│  ├─ SPI → Check SCTRL status, DMA completion
│  │  ├─ FIFO underrun → Clock too fast or DMA starved
│  │  └─ CS# stuck → Check pad mode and chip select configuration
│  │
│  └─ UART → Read LSR (Line Status Register)
│     ├─ Overrun Error (OE) → RX not reading fast enough
│     ├─ Parity Error (PE) → Baud mismatch or noise
│     ├─ Framing Error (FE) → Wrong stop bits or baud
│     └─ Break Interrupt (BI) → Break condition on line
│
├─ Power management failure?
│  ├─ D3 entry timeout → Load: fv-lpss/power-state
│  │  ├─ Check for pending DMA
│  │  ├─ Check for uncleared interrupts
│  │  └─ Check PMC PGCB registers
│  │
│  ├─ S0ix blocked → Load: fv-lpss/power-state
│  │  ├─ Read PMCSR for ALL controllers → must be 0x3
│  │  ├─ Check PMC S0ix blocker register
│  │  └─ Verify LTR = "no requirement" when idle
│  │
│  └─ Clock not gating → Load: fv-lpss/power-state
│     ├─ Check PMC clock gate enable bits
│     ├─ Verify controller is truly idle
│     └─ Check PMC firmware version (CONFIG-003)
│
├─ BSOD / System crash during test?
│  ├─ Check crash dump for LPSS driver (IntelLpss.sys, SerialIO)
│  ├─ Delegate to FV-GenDebugger for BSOD analysis
│  └─ Search Confluence wikis for known crash patterns
│
└─ None of the above?
   ├─ Load: fv-lpss/failure-analysis (parse NGA logs)
   ├─ Delegate to FV-GenDebugger (wiki search + 8-phase triage)
   └─ Search HSDES with keywords from lpss_known_issues.md
```

---

## Reference Sheet 3: Register Quick Reference

### I2C Key Registers (DW_apb_i2c)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| IC_CON | 0x00 | [6]:SLAVE_DIS, [5]:RESTART_EN, [4]:10BIT_ADDR_MASTER, [2:1]:SPEED, [0]:MASTER_MODE | Speed mode (01=Std, 10=Fast, 11=HS) |
| IC_TAR | 0x04 | [11]:10BIT, [9:0]:IC_TAR | Target address and mode |
| IC_DATA_CMD | 0x10 | [11]:FIRST_DATA_BYTE, [10]:RESTART, [9]:STOP, [8]:CMD(0=W,1=R), [7:0]:DAT | Read/write command + data |
| IC_STATUS | 0x70 | [6]:SLV_ACTIVITY, [5]:MST_ACTIVITY, [4]:RFF, [3]:RFNE, [2]:TFE, [1]:TFNF, [0]:ACTIVITY | Activity and FIFO status |
| IC_ENABLE | 0x6C | [3]:SDA_STUCK_RECOVERY, [1]:ABORT, [0]:ENABLE | Enable/disable/abort/recovery |
| IC_TX_ABRT_SOURCE | 0x80 | [31:23]:TX_FLUSH_CNT, [15:0]:ABRT_xxx | Decode all 16 abort reasons |
| IC_COMP_PARAM_1 | 0xF4 | Read-only | HW config: FIFO depth, max speed, APB width |

### I3C Key Registers (HCI Mode)

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| HC_CONTROL | 0x04 | [31]:BUS_ENABLE, [30]:RESUME, [29]:ABORT, [8]:HOT_JOIN_CTRL, [7]:I2C_SLAVE_PRESENT | Bus state, abort, resume |
| RESET_CONTROL | 0x10 | [2]:CMD_Q_RST, [1]:RESP_Q_RST, [0]:SOFT_RST | Queue and controller reset |
| PRESENT_STATE | 0x14 | Bus idle/busy, current master | Bus occupancy |
| PRESENT_STATE_DEBUG | 0x14C | [21:16]:CM_TFR_ST_STATUS, [13:8]:CM_TFR_STATUS | 0x13/0x0F = HALT state |
| COMMAND_QUEUE_PORT | 0x300 | Varies by CMD_ATTR | Write commands here |
| RESPONSE_QUEUE_PORT | 0x304 | [31:28]:ERR_STATUS, [27:24]:TID | Read responses + errors |
| PIO_INTR_STATUS | 0x320 | Interrupt flags | Check for pending interrupts |

### I3C HCI Command Types (CMD_ATTR[2:0])

| CMD_ATTR | Type | Use Case |
|----------|------|----------|
| 0x0 | Regular XFER | Standard read/write with data buffer |
| 0x1 | IMMED_DATA | Small data (≤4 bytes) in command DWORD |
| 0x2 | ADDR_ASSGN | Dynamic address assignment (ENTDAA/SETDASA) |
| 0x3 | COMBO_XFER | Combined write-then-read |

### I3C HALT Recovery Procedure

```
1. Read response_queue_port until empty (drain all pending responses)
2. Set RESET_CONTROL bits [2:1] = 0x3 (reset CMD + RESP queues)
3. Wait for RESET_CONTROL to self-clear (HW clears when done)
4. Set HC_CONTROL bit[30] = 1 (RESUME)
5. Verify PRESENT_STATE_DEBUG shows non-HALT state
```

### UART Key Registers

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| RBR/THR | 0x00 | [7:0] | Receive/Transmit data |
| IER | 0x04 | [3:0] | Interrupt enables |
| IIR/FCR | 0x08 | IIR:[3:0]IntID; FCR:[7:6]RX_TRIG, [2]TX_RST, [1]RX_RST, [0]FIFO_EN | Interrupt ID / FIFO control |
| LCR | 0x0C | [7]:DLAB, [5]:STICK_PAR, [4]:EPS, [3]:PEN, [2]:STOP, [1:0]:DLS | Line params (8N1 = 0x03) |
| MCR | 0x10 | [4]:LOOPBACK, [3]:OUT2, [1]:RTS, [0]:DTR | Loopback mode, flow control |
| LSR | 0x14 | [6]:TEMT, [5]:THRE, [4]:BI, [3]:FE, [2]:PE, [1]:OE, [0]:DR | Line status / errors |

### SPI Key Registers

| Register | Offset | Key Bits | What to Check |
|----------|--------|----------|---------------|
| CTRLR0 | 0x00 | [11:8]:CFS, [7:6]:FRF, [5:4]:TMOD, [3]:CPOL/CPHA | Mode, frame format |
| CTRLR1 | 0x04 | [15:0]:NDF | Number of data frames |
| SSIENR | 0x08 | [0]:SSI_EN | SPI enable |
| SER | 0x10 | Chip select | Active slave select |
| BAUDR | 0x14 | [15:0]:SCKDV | Clock divider |
| SR | 0x28 | [5]:DCOL, [4]:TXE, [3]:RFF, [2]:RFNE, [1]:TFE, [0]:TFNF | Status + errors |

---

## Reference Sheet 4: Platform-Specific Quick Reference

### Die Path Mapping

| Platform | Die | PythonSV Base | LPSS Root |
|----------|-----|---------------|-----------|
| NVL | PCD-H | `socket0.pcd` | `pcd.lpss` |
| NVL | PCH-S | `socket0.pch` | `pch.lpss` |
| PTL | PTL-H | `socket0.soc` | `soc.lpss` |

### VJT Script Paths

| Platform | VJT Path | CLTAP Config | Python |
|----------|----------|-------------|--------|
| NVL | `C:\pythonsv\novalake\vjt\lpss\` | `nvlh_cltap.py` | Local PythonSV |
| PTL | `C:\pythonsv\pantherlake\vjt\lpss\` | `ptl_cltap.py` | `C:\Python310\python.exe` |

### Port Fabric Mapping (NVL PCD-H) — with IOSF SB Port IDs (HAS-verified)

| Fabric ID | Controller | BDF | Device ID | IOSF SB Port ID | DMA/PIO | SB Address Range |
|-----------|------------|-----|-----------|-----------------|---------|-----------------|
| pf_top_0 | I2C0 | 21:0.0 | 0xD378 | 0x0 | DMA | 0xFF00_0XXX |
| pf_top_1 | I2C1 | 21:1.0 | 0xD379 | 0x1 | DMA | 0xFF00_1XXX |
| pf_top_2 | I2C2 | 21:2.0 | 0xD37A | 0x2 | DMA | 0xFF00_2XXX |
| pf_top_3 | I2C3 | 21:3.0 | 0xD37B | 0x3 | DMA | 0xFF00_3XXX |
| pf_top_4 | I2C4 | 25:0.0 | 0xD350 | 0x4 | PIO | 0xFF00_4XXX |
| pf_top_5 | I2C5 | 25:1.0 | 0xD351 | 0x5 | PIO | 0xFF00_5XXX |
| pf_top_6 | UART0 | 30:0.0 | 0xD325 | 0x6 | DMA | 0xFF00_8XXX |
| pf_top_7 | UART1 | 30:1.0 | 0xD326 | 0x7 | DMA | 0xFF00_9XXX |
| pf_top_8 | UART2 | 25:2.0 | 0xD352 | 0x8 | PIO | 0xFF00_AXXX |
| pf_top_9 | SPI0 | 30:2.0 | 0xD327 | 0x9 | DMA | 0xFF00_CXXX |
| pf_top_10 | SPI1 | 30:3.0 | 0xD330 | 0xA | DMA | 0xFF00_DXXX |
| pf_top_11 | SPI2 | 18:6.0 | 0xD347 | 0xB | DMA | 0xFF00_EXXX |
| pf_top_12 | I3C0/I3C1 | 17:0.0 | 0xD37C | 0xC | DMA (ring) | 0xFF01_0XXX, 0xFF01_1XXX |
| pf_top_13 | I3C2/I3C3 | 17:2.0 | 0xD36F | 0xD | DMA (ring) | 0xFF01_2XXX, 0xFF01_3XXX |

> **Note:** IOSF SB port IDs are 16-bit on NVL PCD-H, 8-bit on NVL PCH-S (same port numbers).
> BDFs and Device IDs are platform-assigned (not in LPSS IP HAS) — values above from nvlh_cltap.py.
> **DID Variants:** Device IDs above are for **PCD-H** (`0xD3xx` series). PCD-P uses `0xD2xx` series (e.g., UART0=0xD225, UART1=0xD226, SPI0=0xD227, SPI1=0xD230). BDFs are identical between variants.

### PTL vs NVL vs MTP-S Controller Counts (HAS-verified, "Table: Slice Configuraton")

> All platforms in the MTL/LNL/PTL/WCL/NVL family share **identical LPSS controller counts**. MTP-S is the only variant with different counts.

| Feature | MTL/LNL/PTL/WCL/NVL | MTP-S |
|---------|----------------------|-------|
| I2C instances | 6 (I2C0-5) | 6 (I2C0-5) |
| I3C instances | 4 (I3C0-3, 2 controllers) | 2 (I3C0-1, 1 controller) |
| SPI instances | 3 (SPI0-2) | 4 (SPI0-3) |
| UART instances | 3 (UART0-2) | 4 (UART0-3) |
| I3C core clock | 100 MHz (PTL/WCL), 200 MHz (NVL) | 100 MHz |
| DMA controllers | I2C0-3, UART0-1, SPI0-2, all I3C | I2C0-3, UART0-1/3, SPI0-3, all I3C |
| PIO controllers | I2C4-5, UART2 | I2C4-5, UART2 |

### NGA Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | PASS | None |
| 1 | FAIL | Investigate — load failure-analysis |
| 2 | BLOCKED | Infrastructure issue — check station health |
| 3 | ERROR | Framework error — check VJT init, PythonSV |
| 4 | NOT_RUN | Skipped — check prerequisites |

---

## Reference Sheet 5: Power Management Quick Validation

### Full LPSS Power State Scan

```python
# Scan all LPSS controllers and report their power state
import namednodes as nn
nn.sv.refresh()

die = nn.sv.socket0.pcd  # PTL: socket0.soc

controllers = {
    'I2C0': 'i2c0', 'I2C1': 'i2c1', 'I2C2': 'i2c2',
    'I2C3': 'i2c3', 'I2C4': 'i2c4', 'I2C5': 'i2c5',
    'I3C_Ctrl1': 'i3c0', 'I3C_Ctrl2': 'i3c1',  # 8KB BAR, shared instances
    'SPI0': 'spi0', 'SPI1': 'spi1', 'SPI2': 'spi2',
    'UART0': 'hsuart0', 'UART1': 'hsuart1', 'UART2': 'hsuart2',
}

states = {0: 'D0 (Active)', 1: 'D1', 2: 'D2', 3: 'D3 (Off)'}
blockers = []

for name, path in controllers.items():
    try:
        node = getattr(die.lpss, path)
        pmcsr = node.cfg.cfg_pmcs.read()
        pstate = pmcsr & 0x3
        state_name = states.get(pstate, 'Unknown')
        marker = ' *** S0ix BLOCKER' if pstate != 3 else ''
        print('%s: PMCSR=0x%08X → %s%s' % (name, pmcsr, state_name, marker))
        if pstate != 3:
            blockers.append(name)
    except Exception as e:
        print('%s: ERROR reading PMCSR (%s)' % (name, str(e)))

if blockers:
    print('\n⚠ S0ix BLOCKERS: %s' % ', '.join(blockers))
    print('These controllers must be in D3 for S0ix entry.')
else:
    print('\n✓ All LPSS controllers in D3 — S0ix ready.')
```

### D-State Transition Test

```python
# Test D0 → D3 → D0 for a single controller
ctrl = die.lpss.i2c0

# Read current state
pmcsr = ctrl.cfg.cfg_pmcs.read()
print('Before: PMCSR = 0x%08X (D%d)' % (pmcsr, pmcsr & 3))

# Force D3
ctrl.cfg.cfg_pmcs.write(pmcsr | 0x3)
import time; time.sleep(0.1)
pmcsr_d3 = ctrl.cfg.cfg_pmcs.read()
print('After D3 write: PMCSR = 0x%08X (D%d)' % (pmcsr_d3, pmcsr_d3 & 3))
assert (pmcsr_d3 & 3) == 3, 'FAIL: D3 entry failed!'

# Return to D0
ctrl.cfg.cfg_pmcs.write(pmcsr_d3 & ~0x3)
import time; time.sleep(0.1)
pmcsr_d0 = ctrl.cfg.cfg_pmcs.read()
print('After D0 write: PMCSR = 0x%08X (D%d)' % (pmcsr_d0, pmcsr_d0 & 3))
assert (pmcsr_d0 & 3) == 0, 'FAIL: D0 re-entry failed!'

print('PASS: D0 → D3 → D0 transition successful.')
```

---

## Reference Sheet 6: Remote Execution (PTL)

### Quick Remote Register Read

```powershell
# Read I3C HC_CONTROL on remote PTL host
powershell -Command "Invoke-Command -ComputerName <HOST> -ScriptBlock {
    & 'C:\Python310\python.exe' -c @'
import namednodes as nn
nn.sv.refresh()
val = nn.sv.socket0.soc.lpss.i3c0_0.lpio.hc_control.read()
print('HC_CONTROL = 0x%08X' % val)
print('BUS_ENABLE = %d' % ((val >> 31) & 1))
print('ABORT = %d' % ((val >> 29) & 1))
'@
}"
```

### Remoting Rules

| Rule | Why |
|------|-----|
| Use `%` formatting, NOT f-strings | PowerShell strips `{}` from f-strings |
| Use `@' ... '@` for multi-line | Avoids escaping issues |
| PTL Python: `C:\Python310\python.exe` | Not the same as NVL PythonSV path |
| PTL die path: `socket0.soc` | Not `socket0.pcd` (NVL) |

---

## Reference Sheet 7: HSDES Quick Search

### One-Liner Searches for Common Issues

```bash
# Search for I3C abort sightings
python .opencode/skill/hsdes/hsdes_query.py "I3C abort BUS_ENABLE LPSS"

# Search for S0ix LPSS blockers
python .opencode/skill/hsdes/hsdes_query.py "S0ix blocker LPSS D3"

# Search for I2C NACK issues on NVL
python .opencode/skill/hsdes/hsdes_query.py "I2C NACK NVL LPSS timeout"
```

### Wiki Search for BKMs

```bash
# Search FVCommon for LPSS debug BKMs
python .opencode/skill/securewiki/securewiki.py search "LPSS debug" --spaces fvcommon --user twai --json

# Search DebugEncyclopedia for S0ix LPSS
python .opencode/skill/securewiki/securewiki.py search "S0ix SerialIO" --spaces DebugEncyclopedia --user twai --json
```

---

## Reference Sheet 8: LTR (Latency Tolerance Reporting) Tables (HAS-Verified)

> **Source:** LPSS HAS v5.2, Section: LTR Calculations. Values at ½ FIFO depth.

### I2C LTR by Speed Mode

LTR = (FIFO_depth / 2) × (byte_time) where byte_time = (9 bits × bit_period)

| Speed Mode | Bit Rate | Byte Time (9 bits) | ½ FIFO (32B) LTR | Full FIFO (64B) LTR |
|------------|----------|---------------------|-------------------|----------------------|
| Standard Mode (SM) | 100 Kbps | 90 μs | **2,880 μs** | 5,760 μs |
| Fast Mode (FM) | 400 Kbps | 22.5 μs | **720 μs** | 1,440 μs |
| Fast Mode Plus (FM+) | 1 Mbps | 9 μs | **288 μs** | 576 μs |
| High Speed (HS) | 3.4 Mbps | 2.647 μs | **84.7 μs** | 169.4 μs |

> **Note:** HAS states approximate values: SM≈2560μs, FM≈640μs, FM+≈256μs, HS≈75.3μs (slight rounding differences). Use the formula for exact values.

### SPI LTR by Clock Speed

LTR = (FIFO_depth / 2) × (byte_time) where byte_time = (8 bits / clock_freq)

| SPI Clock | Byte Time | ½ FIFO (128B) LTR | Full FIFO (256B) LTR |
|-----------|-----------|---------------------|----------------------|
| 1 MHz | 8 μs | **1,024 μs** | 2,048 μs |
| 5 MHz | 1.6 μs | **204.8 μs** | 409.6 μs |
| 10 MHz | 0.8 μs | **102.4 μs** | 204.8 μs |
| 24 MHz | 0.333 μs | **42.67 μs** | 85.33 μs |
| 25 MHz | 0.32 μs | **40.96 μs** | 81.92 μs |

### UART LTR

UART FIFO = 64 bytes. LTR = (32 bytes × 10 bits/byte) / baud_rate

| Baud Rate | ½ FIFO (32B) LTR | Full FIFO (64B) LTR |
|-----------|-------------------|----------------------|
| 9,600 | 33,333 μs | 66,667 μs |
| 115,200 | 2,778 μs | 5,556 μs |
| 921,600 | 347 μs | 694 μs |
| 3,686,400 | 86.8 μs | 173.6 μs |

### LTR Register Format (32-bit)

```
Bits [31:16] = Reserved
Bit  [15]    = Requirement (1=valid latency value, 0=no requirement)
Bits [14:13] = Reserved
Bits [12:10] = Scale (0=1ns, 1=32ns, 2=1024ns, 3=32768ns, 4=1048576ns)
Bits [9:0]   = Value (10-bit unsigned)

Effective latency = Value × Scale

Example: 640μs = 640,000ns → Scale=3 (32768ns), Value = 640000/32768 ≈ 20 → 0x8014
```

### LTR Coalescing Rules

- LPSS uses **N-to-1 coalescing**: each controller has its own CS_ACTIVELTR and CS_IDLELTR
- The **lowest** (most stringent) latency among all active controllers is reported upstream
- **CRITICAL:** CS_IDLELTR must be cleared (bit[15]=0, "no requirement") before entering D3. If bit[15] is non-zero when entering D3, the stale LTR value blocks S0ix entry.

### LTR Programming Example (PythonSV)

```python
# Set I2C0 Active LTR to 640μs (FM mode, ½ FIFO)
# Scale=3 (32768ns), Value=20 → 0x8014 | bit15=1 (valid)
i2c0 = die.lpss.i2c0
i2c0.cs_activeltr.write(0x00008014)  # offset 0x210

# Set I2C0 Idle LTR to "no requirement" (for D3 readiness)
i2c0.cs_idleltr.write(0x00000000)    # offset 0x214, bit15=0

# I3C uses different offsets!
i3c0 = die.lpss.i3c0_0
# I3C CS_ACTIVELTR at BAR+0x2BC, CS_IDLELTR at BAR+0x2C0
```

---

## Reference Sheet 9: I2C SCL Timing Formulas (HAS-Verified)

> **Source:** LPSS HAS v5.2, Section: I2C Slice; DW_apb_i2c v2.02a Databook

### SCL High/Low Count Formulas

The I2C clock is generated by programming HCNT (high count) and LCNT (low count) registers:

```
SCL_HIGH_TIME = (HCNT + IC_xS_SPKLEN + 7) × ic_clk_period
SCL_LOW_TIME  = (LCNT + 1) × ic_clk_period
SCL_PERIOD    = SCL_HIGH_TIME + SCL_LOW_TIME
SCL_FREQ      = 1 / SCL_PERIOD
```

Where `ic_clk` = 100 MHz (10 ns period) for all platforms.

### Register Assignments by Speed Mode

| Speed | HCNT Register | LCNT Register | Spike Suppression |
|-------|---------------|---------------|-------------------|
| Standard (100K) | IC_SS_SCL_HCNT (0x14) | IC_SS_SCL_LCNT (0x18) | IC_FS_SPKLEN (0xA0) |
| Fast (400K) | IC_FS_SCL_HCNT (0x1C) | IC_FS_SCL_LCNT (0x20) | IC_FS_SPKLEN (0xA0) |
| Fast Plus (1M) | IC_FS_SCL_HCNT (0x1C) | IC_FS_SCL_LCNT (0x20) | IC_FS_SPKLEN (0xA0) |
| High Speed (3.4M) | IC_HS_SCL_HCNT (0x24) | IC_HS_SCL_LCNT (0x28) | IC_HS_SPKLEN (0xA4) |

> **FM+ uses the same registers as FM** — just with different count values.

### Recommended Count Values (ic_clk = 100 MHz)

| Speed | HCNT | LCNT | SPKLEN | Resulting SCL |
|-------|------|------|--------|---------------|
| SM (100K) | 520 | 476 | 5 (50ns) | ~100 KHz |
| FM (400K) | 120 | 130 | 5 (50ns) | ~400 KHz |
| FM+ (1M) | 40 | 56 | 5 (50ns) | ~1 MHz |
| HS (3.4M) | 8 | 20 | 1 (10ns) | ~3.4 MHz |

### SDA Hold Time Constraints

```
IC_SDA_HOLD (0x7C):
  Bits [23:16] = IC_SDA_RX_HOLD (receive hold time in ic_clk cycles)
  Bits [15:0]  = IC_SDA_TX_HOLD (transmit hold time in ic_clk cycles)

Constraint: IC_SDA_TX_HOLD must satisfy:
  For Standard/Fast:   IC_SDA_TX_HOLD ≥ 1 (when IC_CLK_TYPE=0)
  For HS:              IC_SDA_TX_HOLD < (LCNT - 2) to avoid bus contention
```

### Spike Suppression

| Register | Offset | Default | Purpose |
|----------|--------|---------|---------|
| IC_FS_SPKLEN | 0xA0 | 5 | Suppress spikes ≤ 50ns (SM/FM/FM+) |
| IC_HS_SPKLEN | 0xA4 | 1 | Suppress spikes ≤ 10ns (HS mode) |

> Spike suppression length in ic_clk cycles. At 100 MHz: 1 cycle = 10 ns.

### FM+ Timing Compliance

Per I2C spec, Fast Mode Plus requires:
- SCL_HIGH ≥ 260 ns
- SCL_LOW ≥ 500 ns
- Minimum ic_clk ≥ 31.25 MHz (LPSS uses 100 MHz — compliant)

---

## Reference Sheet 10: UART M/N Divider & Baud Rate Configuration (HAS-Verified)

> **Source:** LPSS HAS v5.2, Section: UART Slice

### M/N Divider Architecture

The UART uses an M/N divider (PRV_CLKRATE at BAR+0x800) to generate the serial clock from the 120 MHz reference:

```
sClk = (M / N) × 120 MHz
Baud = sClk / (16 × Divisor)

Where:
  M = PRV_CLKRATE[31:16] (16-bit numerator)
  N = PRV_CLKRATE[15:0]  (16-bit denominator)
  Divisor = DLH:DLL (when DLAB=1 in LCR)
```

### Standard Baud Rates (≤ 115,200)

For standard baud rates, use: **M=48, N=3125** → sClk = 1.8432 MHz (classic 16550 frequency)

| Baud Rate | Divisor (DLH:DLL) | M | N | Actual Baud | Error |
|-----------|--------------------|---|---|-------------|-------|
| 50 | 2304 (0x0900) | 48 | 3125 | 50.00 | 0% |
| 75 | 1536 (0x0600) | 48 | 3125 | 75.00 | 0% |
| 110 | 1047 (0x0417) | 48 | 3125 | 110.01 | ~0.01% |
| 300 | 384 (0x0180) | 48 | 3125 | 300.00 | 0% |
| 600 | 192 (0x00C0) | 48 | 3125 | 600.00 | 0% |
| 1,200 | 96 (0x0060) | 48 | 3125 | 1,200.0 | 0% |
| 2,400 | 48 (0x0030) | 48 | 3125 | 2,400.0 | 0% |
| 4,800 | 24 (0x0018) | 48 | 3125 | 4,800.0 | 0% |
| 9,600 | 12 (0x000C) | 48 | 3125 | 9,600.0 | 0% |
| 19,200 | 6 (0x0006) | 48 | 3125 | 19,200.0 | 0% |
| 38,400 | 3 (0x0003) | 48 | 3125 | 38,400.0 | 0% |
| 57,600 | 2 (0x0002) | 48 | 3125 | 57,600.0 | 0% |
| 115,200 | 1 (0x0001) | 48 | 3125 | 115,200.0 | 0% |

### High-Speed Baud Rates (> 115,200)

For high-speed baud rates: **N=32767 (max), Divisor=1, M=round(16 × baud × 32767 / 120,000,000)**

| Baud Rate | M | N | Actual Baud | Error |
|-----------|---|---|-------------|-------|
| 230,400 | 1003 | 32767 | 230,416 | ~0.007% |
| 460,800 | 2007 | 32767 | 460,785 | ~0.003% |
| 921,600 | 4014 | 32767 | 921,570 | ~0.003% |
| 1,500,000 | 6554 | 32767 | 1,500,069 | ~0.005% |
| 3,000,000 | 13107 | 32767 | 2,999,954 | ~0.002% |
| 3,686,400 | 16106 | 32767 | 3,686,170 | ~0.006% |
| 6,250,000 | 27307 | 32767 | 6,250,038 | ~0.001% |

### M/N Reprogramming Procedure

```
CRITICAL: After D3 exit or D0i3 exit, M/N values are LOST and must be reprogrammed.

1. Write PRV_CLKRATE (BAR+0x800) with (M << 16) | N
2. Set PRV_CLKRATE_UPDATE (BAR+0x804) bit[31] = 1
3. Wait ≥ 5 μs for clock to stabilize
4. Proceed with UART operations

WARNING: Do NOT access UART registers during the 5μs stabilization window!
```

### 16550 Legacy Mode

UART supports 8-bit legacy mode via GPPRVRW7 register (BAR+0x618):
- Write GPPRVRW7 to switch to legacy 8-bit register access
- **MUST** read BAR0+0xF8 after mode change to flush the pipeline
- Used for backward compatibility with 16550-based software

---

## Reference Sheet 11: SPI CS (Chip Select) Control (HAS-Verified)

> **Source:** LPSS HAS v5.2, Section: SPI Slice

### SPI_CS_CONTROL Register (BAR+0x224)

This register is **retained during power gating** (one of the few MMIO registers preserved).

```
Bit  [0]   = CS_STATE     — Current CS pin state (0=asserted/low, 1=deasserted/high)
Bit  [1]   = CS_MODE      — 0=HW auto CS, 1=SW manual CS control
Bits [3:2] = Reserved
Bits [7:4] = CS_SELECT     — Which CS# pin to use (0=CS0, 1=CS1, etc.)
Bits [11:8] = Reserved
Bits [15:12] = CS_POLARITY  — Per-CS polarity (bit12=CS0, bit13=CS1, etc.)
                              0=active-low (default), 1=active-high
Bits [31:16] = Reserved
```

### CS Configuration Matrix

| Config | CS_MODE | CS_STATE | Behavior |
|--------|---------|----------|----------|
| HW auto (default) | 0 | X | CS asserted during transfers, deasserted between |
| SW CS assert | 1 | 0 | CS held low — use for multi-frame transfers |
| SW CS deassert | 1 | 1 | CS released — end of multi-frame transfer |

### Multi-Frame SPI Transfer (SW CS Mode)

```python
# Example: SPI multi-frame transfer with SW CS control
spi0 = die.lpss.spi0

# 1. Select CS0, set SW mode, assert CS
spi0.spi_cs_control.write(0x00000002)  # CS_MODE=1, CS_STATE=0

# 2. Write data frames...
spi0.dr0.write(0x12345678)
# ... more frames ...

# 3. Deassert CS when done
spi0.spi_cs_control.write(0x00000003)  # CS_MODE=1, CS_STATE=1
```

### SPI Transfer Bit Counting

**CRITICAL:** SPI transfer length registers count **BITS**, not bytes!

| Register | Offset | Purpose |
|----------|--------|---------|
| TX_BIT_COUNT | varies | Number of bits to transmit |
| RX_BIT_COUNT | varies | Number of bits to receive |

```
For a 4-byte transfer: TX_BIT_COUNT = 32 (not 4!)
For a 256-byte transfer: TX_BIT_COUNT = 2048 (not 256!)
```

### SPI DMA Restriction

> **⚠ CRITICAL:** SPI iDMA burst size (M-Size) MUST be 1! Any M-Size > 1 causes RX data corruption.
> This is documented in the HAS and is NOT a bug — it is a design constraint of the Intel Penwell SSP core.

### SPI Delayed RX Clock (BAR+0x250)

Register for tuning RX sampling point. **Retained during power gating.**

```
Bits [2:0] = RX_CLK_DELAY — Delay in half-clock cycles (0-7)
                            Tune this if RX data is shifted or corrupted at high speeds
```

---

## Reference Sheet 12: Clock Domain Quick Reference (HAS-Verified)

> **Source:** LPSS HAS v5.2, Section: Clocking

| Clock | Frequency | Domain | Source | Used By |
|-------|-----------|--------|--------|---------|
| rosc_fast_clk | 100 MHz | Core | Ring Oscillator | Main clock for all controllers |
| i2c_clk | 100 MHz | Core | Derived from rosc_fast_clk | I2C SCL generation |
| spi_clk | 100 MHz | Core | Derived from rosc_fast_clk | SPI SCLK generation |
| uart_clk | 120 MHz | Core | Derived from rosc_fast_clk | UART baud rate (via M/N divider) |
| i3c_clk | 100 MHz (PTL/WCL) | Core | Derived from rosc_fast_clk | I3C SCL generation |
| i3c_clk | 200 MHz (NVL) | Core | Derived from rosc_fast_clk | I3C SCL (faster on NVL!) |
| iosf_prim2_clk | 125 MHz | Fabric | ICC (PLL) | IOSF primary interface |
| side_clk | 76.8 MHz | Fabric | ICC (Ring Osc) | IOSF sideband interface |
| rosc_slow_clk | 2.56 MHz | AON | Always-on | PGCB state machine |
| rtc_clk | 32.768 kHz | AON | Always-on | I3C IBI vnn_req generation |

### Clock Gating Hierarchy

```
Level 1: Trunk Clock Gate (TCG)
  └── Gates rosc_fast_clk to entire LPSS power domain
  └── Controlled by PMC via PGCB

Level 2: Functional Clock Gate (per-controller)
  └── Gates individual controller clocks
  └── Auto-enabled on D0i2 entry (DEVIDLE_CONTROL.IDLE=1)
  └── Force via: GEN_PVT_LOW_REGRW2 (BAR+0x604) bit[3] = 0

Level 3: Side Clock Gate
  └── Gates sideband clock (76.8 MHz)
  └── Only gated when ALL controllers idle + no pending SB messages
```

### Reset Domain Quick Reference

| Reset | Source | Scope | Clears |
|-------|--------|-------|--------|
| PGCBRST | PMC power gate cycle | Bridge + all slices | All non-retained registers |
| PRIMRST | Platform reset | Bridge + all slices | All non-retained registers |
| SIDERST | Sideband reset | SB interface only | SB state machines |
| GAONRST | Global AON reset | AON logic only | AON counters, PGCB FSM |
| func_reset | PGCBRST ∥ PRIMRST ∥ SIDERST | All logic | Combined functional reset |

> **I3C special:** I3C RESETS register (BAR+0x2B4) provides per-instance software reset.
> **LNL onwards:** I3C reset bit must be set to 1 regardless of controller state for bulk save/restore read operations.
