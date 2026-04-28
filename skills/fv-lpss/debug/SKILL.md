---
name: fv-lpss/debug
description: "LPSS debug and triage flows — systematic failure analysis, common failure signatures, debug tools, HSDES sighting database, playbooks for I2C/I3C/SPI/UART issues"
version: "rev1.0"
---

# LPSS Debug & Triage Sub-Skill

> **Owner:** Kong Jia Wen (kjwen) — Client FV, LPSS/SerialIO
>
> **See also:** `fv-lpss/config-checkout` for enumeration checks, `fv-lpss/power-state` for PM debug, `fv-lpss/failure-analysis` for NGA log parsing, `fv-lpss/driver` for driver internals

---

## Systematic Triage Flow

Follow these 4 phases for **every** LPSS failure. Do NOT skip phases.

### Phase 1: Identify Symptom

| Question | Action |
|----------|--------|
| Which controller? | I2C / I3C / SPI / UART + port number |
| Which platform? | NVL PCD-H / NVL PCH-S / PTL — determines PythonSV path |
| Which die? | Determines BDF table (config-checkout) |
| What fails? | Enumerate / traffic / power / interrupt? |
| Reproducible? | Always / intermittent / first-boot-only? |

### Phase 2: Check Basic Health

```python
# Quick health check script pattern
import namednodes as nn
nn.sv.refresh()

# 1. Check PCI device is alive (Device ID != 0xFFFF)
did = nn.sv.socket0.pcd.lpss.<port>.cfg.cfg_hi0.read()
print("Device ID: 0x%04X" % ((did >> 16) & 0xFFFF))

# 2. Check power state (PMCSR bits[1:0])
pmcsr = nn.sv.socket0.pcd.lpss.<port>.cfg.pmcsr.read()
ps = pmcsr & 0x3
print("Power State: D%d" % ps)

# 3. Check BAR allocation (BAR0 != 0)
bar0 = nn.sv.socket0.pcd.lpss.<port>.cfg.bar0.read()
print("BAR0: 0x%08X" % bar0)

# 4. Check clock gating (idle = clocks gated)
# Load fv-lpss/power-state for specific register paths
```

### Phase 3: Protocol-Level Debug

| Controller | Check | Register | Expected |
|-----------|-------|----------|----------|
| **I2C** | Controller enabled | IC_ENABLE (0x6C) | bit0 = 1 |
| **I2C** | Target address | IC_TAR (0x04) | Correct 7/10-bit address |
| **I2C** | Abort source | IC_TX_ABRT_SOURCE (0x80) | 0 (no abort) |
| **I2C** | Bus status | IC_STATUS (0x70) | bit2=1 (TFE), bit1=0 (TFNF) |
| **I3C** | Bus enabled | HC_CONTROL (0x04) | bit31 = 1 (BUS_ENABLE) |
| **I3C** | Controller state | PRESENT_STATE (0x14) | bits[21:16] = CM_TFR_ST_STATUS |
| **I3C** | HCI version | HCI_VERSION (0x00) | 0x100 (v1.0) |
| **I3C** | Chicken bit | gen_pvt_high_regrw4 | bits[1:0] = 0 (safe) |
| **SPI** | Controller enabled | SCTRL | SSPE bit = 1 |
| **SPI** | FIFO status | SSSR | RNE/TNF bits |
| **UART** | Baud divisor | DLL/DLH | Correct for target baud |
| **UART** | Line control | LCR (0x0C) | Correct word length/parity |
| **UART** | Modem control | MCR (0x10) | Loopback bit if internal test |
| **UART** | Line status | LSR (0x14) | DR=1 (data ready), OE=0 |

### Phase 4: Root Cause Analysis

```
Symptom → Phase 2 (health) → Phase 3 (protocol) → Root Cause
  ↓                                                    ↓
  If still unclear → Load fv-lpss/failure-analysis     ↓
  If NGA failure   → Use GenDebugger 8-phase triage    ↓
  If platform-wide → Check BIOS config, PMC FW, BKC   ↓
  If known issue   → Cross-ref lpss_known_issues.md    ↓
                                                    → File HSDES
```

---

## Common Failure Signatures

| # | Symptom | Likely Cause | First Check | Escalation |
|---|---------|-------------|-------------|------------|
| 1 | Device ID = 0xFFFF | Not enumerated, D3, or fuse-disabled | `config-checkout`: check BDF exists in HAS | Check BIOS knob, fuse status |
| 2 | All registers read 0x00000000 | BAR not assigned or wrong base address | `config-checkout`: check BAR0 allocation | PCI resource conflict |
| 3 | I2C NACK on every transfer | Wrong target address, pad mode, or device absent | Check IC_TAR, PMode (must be ≥1), physical device | Replace device / check pullups |
| 4 | I2C TX_ABRT with specific bits | Decode IC_TX_ABRT_SOURCE 16-bit field | Read offset 0x80, decode per I2C databook | Protocol analyzer capture |
| 5 | I3C BUS_ENABLE stuck at 1 | Abort with chicken_bit[1:0]=3 | Read `gen_pvt_high_regrw4`, check BUG-001 | Set chicken_bit[1:0]=0 |
| 6 | I3C TID mismatch | DMA control queue not cleared on abort | Same chicken bit issue — BUG-001 | Set chicken_bit[1:0]=0 |
| 7 | I3C HALT state (CM_TFR_ST=0x13) | Broadcast NACK, abort, or HDR error | Read PRESENT_STATE_DEBUG(0x14C) | Drain→Reset→RESUME(bit30) |
| 8 | SPI FIFO underrun | Clock too fast or DMA late | Check SCTRL clock divider, DMA config | Reduce SPI clock speed |
| 9 | UART TX timeout | Baud mismatch or flow control stuck | Check LCR baud config, MCR flow control | Use loopback mode to isolate |
| 10 | D3 entry timeout | Outstanding DMA or pending interrupt | `power-state`: check pending IRQs, DMA active | Drain DMA → disable IRQs → retry D3 |
| 11 | S0ix blocked by LPSS | One+ controllers not in D3 | `power-state`: scan PMCSR all controllers | Identify stuck controller |
| 12 | Clock not gated in idle | CGPG not enabled or PMC misconfigured | `power-state`: check PMC CLK_GATE regs | Check PMC FW version |
| 13 | PMode=0 on native pin | Pad stuck in GPIO mode, wrong ownership | `config-checkout`: check pad owner/lock | BIOS pad config issue |
| 14 | Multiple controllers fail | Systemic: BIOS, PMC, platform reset | Check BIOS LPSS enable, PMC FW, cold boot | BKC regression |
| 15 | Intermittent NACK | Electrical: signal integrity, pullup, noise | Check I2C pullup resistor, bus capacitance | Scope/analyzer capture |
| 16 | GPIO interrupt lost after reboot | IOAPIC RTE stuck: RTE_DS=1 AND RTE_Rirr=1 while line deasserted | Read IOAPIC RTE at 0xFEC00000; check `itss.icbi.imf.RTE_DS/RTE_Rirr` | HSDES 14023171649 — see Playbook 6 |
| 17 | Touchpad/clickpad lost after reboot | Same as #16 — GPIO interrupt mode race condition | Check PAD_CFG_DW0.rxevcfg, PAD_CFG_DW1.iosstate, GPI_IS clear timing | Set rxevcfg=0x2 during BIOS, iosstate=0xF |
| 18 | IOAPIC RTE permanently masked | DEASSERT_IRQ arrived before MSI_CMPL during OS boot | VISA: `pessbpmsgdec1/msg_visa[7:0]`, `itsssbmsigen1/visa_w2sbsm_ps` | ITSS HW fix needed (future silicon) |

---

## Debug Checklist (Quick Triage)

Use this 6-item checklist before deep-diving:

- [ ] **PCI alive?** Device ID ≠ 0xFFFF at expected BDF
- [ ] **BAR assigned?** BAR0 ≠ 0x00000000
- [ ] **Power state?** PMCSR[1:0] = 0 (D0), not stuck in D3
- [ ] **Pad routing?** PMode ≥ 1 (native function, not GPIO)
- [ ] **Controller enabled?** IC_ENABLE=1 (I2C), BUS_ENABLE=1 (I3C), SSPE=1 (SPI)
- [ ] **Known issue?** Check `lpss_known_issues.md` for matching symptom

---

## Debug Tools

### ITP/DCI Debug (PythonSV)

```python
# Full LPSS register dump via ITP
import namednodes as nn
nn.sv.refresh()

# Dump all I2C0 config space registers
i2c0 = nn.sv.socket0.pcd.lpss.i2c0.cfg
for offset in range(0, 0x100, 4):
    val = i2c0.regread(offset)
    print("0x%03X: 0x%08X" % (offset, val))

# Dump I3C HCI registers (PTL example)
i3c0 = nn.sv.socket0.soc.lpss.i3c0_0.lpio
regs = {
    'HCI_VERSION': 0x00, 'HC_CONTROL': 0x04,
    'RESET_CONTROL': 0x10, 'PRESENT_STATE': 0x14,
    'INTR_STATUS': 0x20, 'INTR_STATUS_ENABLE': 0x24,
    'COMMAND_QUEUE_PORT': 0x300, 'RESPONSE_QUEUE_PORT': 0x304,
    'PIO_INTR_STATUS': 0x320
}
for name, off in regs.items():
    val = i3c0.regread(off)
    print("%-25s (0x%03X): 0x%08X" % (name, off, val))
```

### Protocol Analyzer

| Tool | Protocol | Use Case |
|------|----------|----------|
| **Total Phase Aardvark** | I2C, SPI | Bus capture, address scan, speed measurement |
| **Total Phase Promira** | I2C, I3C, SPI | Advanced I3C protocol analysis |
| **Saleae Logic** | I2C, SPI, UART | Multi-channel digital capture, timing analysis |
| **Bus Pirate** | I2C, SPI, UART | Quick bus probing, interactive commands |

### OS-Level Debug

**Linux:**
```bash
# Check driver binding
lspci -vvv -s <BDF> | grep -E "Kernel driver|LnkSta|Power"

# I2C bus scan
i2cdetect -l                    # List I2C adapters
i2cdetect -y <bus_number>       # Scan for devices

# Check power state
cat /sys/bus/pci/devices/<BDF>/power/runtime_status
cat /sys/bus/pci/devices/<BDF>/power_state

# dmesg for errors
dmesg | grep -E "i2c_designware|dw-i3c|spi-dw|8250_lpss|LPSS"

# GPIO pad verification
cat /sys/kernel/debug/pinctrl/*/pins | grep -i lpss
```

**Windows:**
```powershell
# Device Manager equivalent
Get-PnpDevice -FriendlyName "*Serial*" -Status OK
Get-PnpDevice -FriendlyName "*I2C*" -Status OK

# Driver info
pnputil /enum-drivers | Select-String -Context 0,5 "SerialIO|IntelLpss"

# Check D-state (WMI)
Get-CimInstance -Namespace root/wmi -ClassName MSPower_DeviceEnable
```

---

## HSDES Sighting Database

### Filing BKM for LPSS Sightings

| Field | Value |
|-------|-------|
| **Tenant** | `sighting` |
| **Domain** | `client` |
| **Component** | `LPSS` or `Serial IO` |
| **Sub-Component** | `I2C` / `I3C` / `SPI` / `UART` |
| **Platform** | `NVL` / `PTL` |
| **Stepping** | From `itp.stepping()` or PCI revision ID |
| **Severity** | HIGH for silicon bug, MEDIUM for driver, LOW for config |

### HSDES Search Patterns

```
# Search for LPSS I3C sightings
component:LPSS AND title:"I3C" AND platform:NVL AND status:open

# Search for abort/recovery issues
component:LPSS AND (title:"abort" OR title:"recovery" OR title:"stuck")

# Search for power management sightings
component:LPSS AND (title:"D3" OR title:"S0ix" OR title:"clock gating")
```

### False Positive Filters

When triaging sightings, filter out:
- **Config issues:** Pad mode wrong (PMode=0) — not a silicon bug
- **BKC mismatch:** Wrong BIOS/PMC/driver version — retest on latest BKC
- **External device:** Peripheral not responding — check device power/presence
- **Test script bug:** VJT script error vs silicon error — verify with manual register access

---

## Debug Playbooks

### Playbook 1: I2C Device Not Responding

**Symptom:** I2C transfer fails with NACK, timeout, or TX_ABRT

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Check PCI enumeration | `cfg.cfg_hi0` (Device ID) | Valid DID (not 0xFFFF) | → Playbook 5 (Not Enumerated) |
| 2 | Check power state | `cfg.pmcsr[1:0]` | 0 (D0) | Write PMCSR=0 to wake |
| 3 | Check BAR allocation | `cfg.bar0` | Non-zero, aligned | Check PCI resource allocation |
| 4 | Check pad mode | PMode for SDA/SCL pads | ≥1 (native function) | Fix BIOS pad config |
| 5 | Check I2C enabled | `IC_ENABLE (0x6C)` | bit0 = 1 | Write IC_ENABLE=1 |
| 6 | Check target address | `IC_TAR (0x04)` | Correct 7/10-bit addr | Set correct address |
| 7 | Check abort source | `IC_TX_ABRT_SOURCE (0x80)` | 0 (no abort) | Decode 16 abort bits |
| 8 | Check bus status | `IC_STATUS (0x70)` | bit5=1 (MST_ACT=0 if idle) | Bus may be stuck — reset |
| 9 | Try loopback | Internal loopback via IC_CON | Data matches | External issue (device/wiring) |

**Typical Root Causes:**
1. Wrong target address (IC_TAR mismatch)
2. Pad mode not set to native function (PMode=0)
3. Target device not powered or not present
4. Bus pullup resistors missing/wrong value
5. Controller in D3 (PMCSR ≠ D0)

---

### Playbook 2: I3C Abort Recovery Failure

**Symptom:** I3C controller stuck after abort — BUS_ENABLE=1, TID mismatch, subsequent commands fail

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Read chicken bit | `gen_pvt_high_regrw4[1:0]` | 0 (safe) | **Set to 0** — this is BUG-001 |
| 2 | Read HC_CONTROL | `HC_CONTROL (0x04)` | bit31=1 (enabled) | If stuck, proceed to step 4 |
| 3 | Read PRESENT_STATE | `PRESENT_STATE_DEBUG (0x14C)` | bits[21:16] = idle state | If 0x13 = HALT → step 5 |
| 4 | Clear BUS_ENABLE | Write HC_CONTROL bit31=0 | bit31 clears to 0 | If stuck → chicken bit is root cause |
| 5 | HALT recovery | Drain responses → reset queues → RESUME(bit30) | State returns to IDLE | If fails → full I3C soft reset |
| 6 | Soft reset | Write RESET_CONTROL(0x10) = 1 | All queues cleared | Wait for reset complete |
| 7 | Re-initialize | Full HCI init sequence | BUS_ENABLE=1, DAA complete | Controller may need cold boot |
| 8 | Verify | Run simple SDR transfer | Transfer completes | File HSDES if still failing |

**Typical Root Causes:**
1. Chicken bit `gen_pvt_high_regrw4[1:0]=3` (BUG-001, HSDES 18044213731)
2. Target device NACK during broadcast CCC
3. HDR mode TX underflow (data not pre-loaded)
4. DMA queue corruption after abort

---

### Playbook 3: UART Traffic Failure

**Symptom:** UART loopback test fails — TX data ≠ RX data, or RX timeout

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Check enumeration | Device ID at UART BDF | Valid DID | → Playbook 5 |
| 2 | Check power state | PMCSR[1:0] | 0 (D0) | Wake controller |
| 3 | Check DLAB/baud | LCR.DLAB=1 → read DLL/DLH | Correct divisor for target baud | Recalculate divisor |
| 4 | Check line config | LCR (word length, stop bits, parity) | Matches expected config | Reconfigure LCR |
| 5 | Check loopback | MCR bit4 (loopback enable) | 1 if internal test | Enable loopback |
| 6 | Check flow control | MCR (RTS/DTR), MSR (CTS/DSR) | CTS=1 if HW flow control | Disable flow control for test |
| 7 | Check FIFO | FCR (FIFO enable), LSR (status) | FIFO enabled, no errors | Reset FIFOs |
| 8 | Check TX status | LSR bit5 (THRE) | 1 (TX holding empty) | Wait for FIFO drain |
| 9 | Single byte test | Write 1 byte → read LSR.DR → read RBR | Data matches | Isolate: TX or RX issue |

**Typical Root Causes:**
1. Baud rate divisor miscalculated
2. Loopback not enabled for internal test
3. Flow control blocking TX (CTS not asserted)
4. FIFO not enabled or overflowed
5. DMA channel not configured (if DMA mode)

---

### Playbook 4: S0ix Blocked by LPSS

**Symptom:** Platform cannot enter S0ix — LPSS identified as blocker

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Scan all PMCSR | Read PMCSR[1:0] for every LPSS controller | All = 3 (D3) | Identify which is NOT in D3 |
| 2 | Check driver status | OS driver PM state | Suspended | Driver holding controller active |
| 3 | Check pending DMA | DMA status registers | No active transfers | Wait for DMA completion |
| 4 | Check pending IRQ | Interrupt status registers | No pending interrupts | Clear/mask interrupts |
| 5 | Check LTR values | LTR registers | Reporting max tolerance | LTR value too restrictive |
| 6 | Check PMC blocker | PMC S0ix blocker register | LPSS not listed | PMC FW issue — check version |
| 7 | Force D3 entry | Write PMCSR[1:0]=3 for stuck controller | Enters D3 | Outstanding transaction — debug further |
| 8 | Recheck S0ix | S0ix entry attempt | Platform enters S0ix | If still blocked → PMC/BIOS issue |

**Typical Root Causes:**
1. One controller held in D0 by active driver/application
2. DMA transfer in progress prevents D3 entry
3. Pending interrupt not cleared
4. LTR value set too low (prevents platform idle)
5. PMC firmware bug — CGPG not releasing LPSS power well

---

### Playbook 5: Device Not Enumerating (0xFFFF)

**Symptom:** PCI config read returns Device ID = 0xFFFF at expected BDF

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Verify BDF from HAS | Cross-check with `config-checkout` tables | BDF exists in HAS | Wrong BDF — check die variant |
| 2 | Check BIOS knob | LPSS controller enable in BIOS setup | Enabled | Enable in BIOS |
| 3 | Check fuse status | Fuse register for LPSS disable | Not fused-off | Silicon limitation — cannot recover |
| 4 | Check power well | PMC LPSS power well status | Powered on | PMC FW issue |
| 5 | Check reset status | Platform reset state | Out of reset | May need cold boot |
| 6 | Try alternate BDF | Check for BDF remapping | Device at different BDF | BIOS resource rebalance |
| 7 | Check other controllers | Are ANY LPSS devices visible? | At least some visible | If none → systemic (BIOS/PMC/fuse) |
| 8 | Check upstream bridge | PCI bridge above LPSS BDF | Bridge enumerated | Upstream topology issue |

---

### Playbook 6: IOAPIC Interrupt Delivery Stuck (GPIO Mode) — HSDES 14023171649

**Symptom:** GPIO-connected device (touchpad, clickpad, sensor) loses interrupt delivery after reboot. Device enumerates but stops responding. IOAPIC RTE shows `RTE_DS=1 AND RTE_Rirr=1` while GPIO line is deasserted.

**Root Cause:** Race condition between GPIO `DEASSERT_IRQ` (opcode 0x55) and ITSS `MSI_CMPL` during OS boot. When the GPIO driver clears `GPI_IS` while ITSS MSI send is still in-flight, `DEASSERT_IRQ` arrives before `MSI_CMPL`, violating ITSS ordering rules. This permanently sticks `RTE_DS[N]` and `RTE_Rirr[N]`.

**Affected Platforms:** LNL-MX (confirmed), potentially NVL/PTL/TTL (same ITSS architecture)

| Step | Action | Register/Command | Expected | If Wrong |
|------|--------|-----------------|----------|----------|
| 1 | Read IOAPIC RTE for affected IRQ | MMIO 0xFEC00000: IOREGSEL=0x10+2*N, read IOWIN (low+high) | msk=0, ds=0, rirr=0 | If ds=1 AND rirr=1 → stuck (step 3) |
| 2 | Check GPIO pad config | `PAD_CFG_DW0`: rxevcfg[26:25], gpiroutioxapic[20] | rxevcfg=0x2 (disabled during BIOS) | If rxevcfg=0x0 → vulnerable to race |
| 3 | Read ITSS internal state | `itss.icbi.imf.RTE_DS[N]`, `itss.icbi.imf.RTE_Rirr[N]` | Both = 0 | Both = 1 → confirmed stuck |
| 4 | Check ITSS state machine | `itss.icbi.imf.CurrentState[1:0]` | 0x0 (IDLE) | 0x1/0x2 → stuck in MSI_SEND/WAIT |
| 5 | Check GPIO interrupt status | `GPI_IS` for affected pad community | Bit N = 0 (cleared) | Bit N = 1 → interrupt pending |
| 6 | Verify PAD_CFG_DW1.iosstate | `PAD_CFG_DW1` bits[17:14] | 0xF (all masked in S0i2.2) | ≠ 0xF → S0i2.2 glitch can re-trigger race |
| 7 | Check sideband message ordering | VISA: `pessbpmsgdec1/msg_visa[7:0]` | ASSERT(0x54)→MSI→MSI_CMPL→DEASSERT(0x55) | DEASSERT before MSI_CMPL → race confirmed |
| 8 | Attempt recovery | Write EOI to MMIO 0xFEC00040, or toggle RTE mask bit | RTE_DS and RTE_Rirr clear | If won't clear → reboot required |

**IOAPIC RTE Register Layout (per IRQ N):**
```
IOREGSEL = 0x10 + 2*N     → RTE_Low[N]  (read via IOWIN at 0xFEC00010)
IOREGSEL = 0x10 + 2*N + 1 → RTE_High[N] (read via IOWIN at 0xFEC00010)

RTE_Low[N] bits:
  [16]   msk  — 1=masked, 0=unmasked
  [15]   tm   — 1=level, 0=edge (MUST be 1 for GPIO interrupts)
  [14]   rirr — Remote IRR (1=LAPIC accepted, awaiting EOI) ← STUCK=BUG
  [13]   pol  — 0=active-high, 1=active-low
  [12]   ds   — Delivery Status (1=send pending) ← STUCK=BUG
  [10:8] dlm  — Delivery Mode (000=Fixed, 001=Lowest Priority)
  [7:0]  vct  — Interrupt Vector
```

**PythonSV Diagnostic Script:**
```python
import namednodes as nn
nn.sv.refresh()

# Read IOAPIC RTE (adjust N for target IRQ)
def read_ioapic_rte(irq_num):
    """Read IOAPIC Redirection Table Entry for a given IRQ."""
    ioapic_base = 0xFEC00000
    ioregsel = ioapic_base + 0x00
    iowin    = ioapic_base + 0x10

    # Read low DWORD
    nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq_num, 4)
    rte_low = nn.sv.socket0.pcd.io.mem.read(iowin, 4)

    # Read high DWORD
    nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq_num + 1, 4)
    rte_high = nn.sv.socket0.pcd.io.mem.read(iowin, 4)

    msk  = (rte_low >> 16) & 1
    tm   = (rte_low >> 15) & 1
    rirr = (rte_low >> 14) & 1
    pol  = (rte_low >> 13) & 1
    ds   = (rte_low >> 12) & 1
    dlm  = (rte_low >> 8) & 7
    vct  = rte_low & 0xFF
    did  = (rte_high >> 24) & 0xFF

    print("IOAPIC RTE[%d]:" % irq_num)
    print("  Low=0x%08X  High=0x%08X" % (rte_low, rte_high))
    print("  msk=%d tm=%d rirr=%d pol=%d ds=%d dlm=%d vct=0x%02X did=0x%02X"
          % (msk, tm, rirr, pol, ds, dlm, vct, did))

    if ds == 1 and rirr == 1 and msk == 0:
        print("  >>> STUCK! ds=1 AND rirr=1 while unmasked — HSDES 14023171649")
        print("  >>> GPIO DEASSERT_IRQ/MSI_CMPL race condition confirmed")
        return True  # Stuck
    return False

# Check all GPIO-routed IRQs (typically IRQ 14 for LPSS community)
for irq in [14, 15, 16]:
    read_ioapic_rte(irq)
```

**IOSF Sideband Message Reference:**

| Opcode | Name | Direction | Description |
|--------|------|-----------|-------------|
| 0x54 | ASSERT_IRQ | GPIO → ITSS | GPIO pad asserted interrupt |
| 0x55 | DEASSERT_IRQ | GPIO → ITSS | GPIO pad deasserted interrupt |
| 0x01 | MSI MWr | ITSS → P2SB | ITSS sends MSI to CPU via P2SB |
| — | MSI_CMPL | P2SB → ITSS | P2SB acknowledges MSI delivery |
| — | EOI | Host → ITSS | CPU sends End-of-Interrupt |

**Race Condition Timeline (failure case):**
```
Time  →  GPIO Driver     IOSF-SB          ITSS           CPU/LAPIC
─────────────────────────────────────────────────────────────────
t0    GPIO asserts   →  ASSERT_IRQ(0x54) → received
t1                                         MSI_SEND  →  MSI MWr(0x01) →
t2    GPI_IS clear   →  DEASSERT(0x55)   → received     (MSI in-flight)
t3                       ✗ ORDERING VIOLATION: DEASSERT arrived before MSI_CMPL
t4                                                    ← MSI_CMPL (too late!)
t5                                         RTE_DS=1, RTE_Rirr=1 ← PERMANENTLY STUCK
```

**Mitigations:**
1. **BIOS:** Set `PAD_CFG_DW0.rxevcfg=0x2` (disable RX events) during init; OS enables when ready
2. **BIOS:** Set `PAD_CFG_DW1.iosstate=0xF` on ALL interrupt-generating pads (prevents S0i2.2 glitches)
3. **OS Driver:** Use IOAPIC direct mode (`gpiroutioxapic=1`) where possible — bypasses ITSS race window
4. **OS Driver:** Fix `GPI_IS` clear ordering — ensure MSI delivery completes before clearing
5. **Future Silicon:** ITSS must handle DEASSERT during MSI_SEND state gracefully

**Cross-References:**
- Known Issue: `docs/lpss_known_issues.md` → HSDES-004
- Failure Analysis: `fv-lpss/failure-analysis` → IOAPIC Interrupt Delivery section
- Config Checkout: `fv-lpss/config-checkout` → GPIO Interrupt Pad Register Checks
- Full Report: [HSDES 14023171649 HTML Report](https://htmlpreview.github.io/?https://github.com/KongJiaWen/applications.ai.ocode.market.skills/blob/hsdes-14023171649-report/HSDES_14023171649_IOAPIC_Report.html)

---

## Key Register Dump Points

When capturing debug state, always dump these registers organized by category:

### Enumeration State
- PCI Config Space: VID/DID, Class Code, BAR0, BAR1, PM Cap, PMCSR

### I2C Protocol State
- IC_CON, IC_TAR, IC_SAR, IC_HS_MADDR
- IC_DATA_CMD, IC_SS/FS/HS_SCL_HCNT, IC_SS/FS/HS_SCL_LCNT
- IC_STATUS, IC_ENABLE, IC_TX_ABRT_SOURCE
- IC_DMA_CR, IC_DMA_TDLR, IC_DMA_RDLR
- IC_COMP_PARAM_1 (IP version)

### I3C Protocol State
- HCI_VERSION, HC_CONTROL, PRESENT_STATE, PRESENT_STATE_DEBUG
- RESET_CONTROL, INTR_STATUS, INTR_STATUS_ENABLE
- COMMAND_QUEUE_PORT, RESPONSE_QUEUE_PORT
- PIO_INTR_STATUS, PIO_INTR_STATUS_ENABLE
- gen_pvt_high_regrw4 (chicken bit)

### Power State
- PMCSR[1:0] (current D-state)
- Trunk/Functional/Side clock gate status
- PMC PGCB registers (LPSS power well)
- LTR value registers

---

## Cross-Platform Recurring Patterns

| Pattern | NVL PCD-H | NVL PCH-S | PTL | Debug Hint |
|---------|-----------|-----------|-----|------------|
| I3C chicken bit default | Check gen_pvt_high_regrw4 | Same register, different base | Same | Always set [1:0]=0 for DMA mode |
| I3C register path | socket0.pcd.lpss.i3c0_0 | socket0.pch.lpss.i3c0_0 | socket0.soc.lpss.i3c0_0.lpio | PTL has .lpio, no .cfg |
| I3C core clock | 200 MHz | 200 MHz | 100 MHz | Affects timing calculations |
| IOSF SB port ID width | 16-bit | 16-bit | 8-bit | Affects sideband addressing |
| PCI Device IDs | 0xD2xx (I2C/SPI/UART), 0xD3xx (I3C) | 0x6Exx | Platform-specific | Always check HAS |
| DMA mode availability | I2C0-3, SPI0-2, UART0-1 | Same | Same | I2C4-5 and UART2 are PIO only |

---

## See Also

- `fv-lpss/config-checkout` — PCI enumeration tables, register values, pad mode checks
- `fv-lpss/power-state` — D-state transitions, clock gating, CGPG, S0ix blockers
- `fv-lpss/failure-analysis` — NGA test failure triage, log parsing, sighting correlation
- `fv-lpss/driver` — Driver internals, cross-platform differences, error recovery
- `docs/lpss_known_issues.md` — HSDES sightings, RTL bugs, driver issues
- `docs/lpss_reference_sheets.md` — Bring-up checklists, quick-reference procedures
- `docs/i2c/DW_apb_i2c_validation_reference.md` — I2C IP register reference
- `docs/i3c/DWC_mipi_i3c_validation_reference.md` — I3C HCI register reference
