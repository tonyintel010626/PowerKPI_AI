---
name: fv-lpss/power-state
description: "Verify LPSS D3 power states and clock gating on Novalake platform"
---

# LPSS Power State & Clock Gating — Novalake (NVL)

Verify that LPSS controllers correctly enter/exit D3 power states and that clocks are properly gated when idle.

> **Scope:** I2C, I3C, SPI, UART controllers only. No GPIO controllers in LPSS subsystem.

---

## Quick Status Check (RECOMMENDED)

```bash
python check_all_lpss_ports_status.py
```

Validates all 3 D3 criteria (PSF function disable, PMU subsystem state, MMR subsystem state) and shows per-port power states with detailed validation. Takes ~25-30 seconds.

**Example Output:**
```
================================================================================
LPSS Port Status Check - Validating All 3 Criteria
================================================================================
✅ CRITERIA 1: LPSS fuse status OK
💤 CRITERIA 2: LPSS subsystem is in D3 (PMU)
💤 CRITERIA 3: LPSS D3 condition is met (MMR)

Port            Status               Validation Details
--------------------------------------------------------------------------------
I2C0            D3 (Low Power)       powerstate=3
I2C1            D3 (Low Power)       powerstate=3
I2C4            FUNCTION DISABLED    PSF fundis=1
I3C0-I3C3      FUNCTION DISABLED    PSF fundis=1
...
================================================================================
Summary:
✅ D0 (Active):        0 ports
💤 D3 (Low Power):     4 ports - I2C0, I2C1, I2C2, I2C3
❌ Function Disabled:  12 ports
================================================================================
```

---

## Overview

### D-States (Device Power States)

| State | Description | Clocks | Power | Config Space |
|-------|-------------|--------|-------|-------------|
| D0 | Fully operational | Running | Full | Accessible |
| D3hot | Low power, PME wake possible | Gated | Minimal | Accessible |
| D3cold | Lowest power, powered off | Off | None | Inaccessible |

### Clock Gating Types

1. **Trunk Clock Gating** — Main clock to the LPSS IP block
2. **Functional Clock Gating** — Clocks to specific functional units within the IP
3. **Side Clock Gating** — Peripheral/interface clocks

### Why This Matters

- LPSS controllers **must** enter D3 when idle for SoC to reach S0ix (Modern Standby)
- Each controller stuck in D0 increases platform power and blocks low-power states
- **Clock gating is a prerequisite for D3 entry** — clocks must be gated first

**Verification flow:**
1. Check device is idle (no active transactions)
2. Verify functional clocks are gated
3. Confirm device entered D3

---

## Power Management Registers (HAS-Verified)

> **Source:** LPSS_HAS.html (IP v5.2, Rev 1.02, April 2025) — verified via Co-Design

### PCI Config Space PM Registers

#### PMCSR (PM Control/Status Register) — PCI Config Offset 0x84

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [1:0] | PowerState | RW | 0x0 | `00b`=D0, `01b`=D1, `10b`=D2, `11b`=D3hot |
| [8] | PME_En | RW | 0x0 | Enable PME generation |
| [15] | PME_Status | RW/1C | 0x0 | PME asserted (write-1-to-clear) |

> PM Capability ID (POWERCAPID) is at PCI config offset 0x80.

#### D0I3_MAX_POW_LAT_PG_CONFIG — PCI Config Offset 0xA0

Controls power gating enables and D0i3 latency. This is the **actual** register that controls
power gating — older references to "PCE" at BAR+0xF80 are **incorrect** for this IP version.

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [9:0] | POW_LAT_VALUE | RW/O | 0x0 | Power On Latency value |
| [12:10] | POW_LAT_SCALE | RW/O | 0x2 | Power On Latency Scale |
| [15:13] | RESERVED | RO | 0x0 | Reserved |
| [16] | PMCRE | RW | 0x1 | PMC Request Enable — power gates when idle + pmc_sw_pg_req_b=0 |
| [17] | DEVIDLEN | RW | 0x1 | DevIdle Enable — power gates when idle + DEVIDLE_CONTROL[2]=1 |
| [18] | D3HEN | RW | 0x1 | D3-Hot Enable — power gates when PMCSR[1:0]=11 |
| [19] | SLEEP_EN | RW | 0x1 | Sleep Enable — may assert Sleep during power gating |
| [20] | RESERVED | RO | 0x0 | Reserved |
| [21] | HAE | RW | 0x0 | HW Autonomous Enable — HW may request PG when idle |
| [31:22] | RESERVED | RO | 0x0 | Reserved |

### BAR-Relative PM Registers

> **NOTE:** I3C controllers use different offsets than I2C/SPI/UART due to the HCI register map.

| Register | Offset (I2C/SPI/UART) | Offset (I3C) | Size | Reset | Access | Description |
|----------|----------------------|-------------|------|-------|--------|-------------|
| CS_ACTIVELTR | BAR+0x210 | BAR+0x2BC | 32-bit | 0x00000000 | RW | Active state LTR value |
| CS_IDLELTR | BAR+0x214 | BAR+0x2C0 | 32-bit | 0x00000000 | RW | Idle state LTR value |
| DEVIDLE_CONTROL | BAR+0x24C | BAR+0x2CC | 32-bit | 0x00000001 | RW/RO/1C | Device idle control |
| RESETS | — | BAR+0x2B4 | 32-bit | 0x00000000 | RW/RO | I3C soft reset (I3C only) |

#### DEVIDLE_CONTROL Bit Fields

| Bits | Field | Access | Reset | Description |
|------|-------|--------|-------|-------------|
| [0] | cmd_in_progress | RO | 0 | HW sets during D-state transitions |
| [1] | intr_req | RO | 0 | Reserved |
| [2] | devidle | RW | 0 | SW writes 1 to enter DevIdle; 0 = D0 active |
| [3] | restore_required | RW/1C | 1 | HW sets if register state restore needed after exit |
| [4] | intr_req_capable | RO | 0 | HW capability indicator |
| [31:5] | spare | RW | 0 | Reserved |

> **IMPORTANT — Legacy Register Names:**
> - "PCE" (Power Control Enable) at BAR+0xF80 → **Does NOT exist** in LPSS HAS v5.2. Use `D0I3_MAX_POW_LAT_PG_CONFIG` at PCI config 0xA0 instead.
> - "D0I3C" (D0i3 Control) at BAR+0xF84 → **Does NOT exist** in LPSS HAS v5.2. Use `DEVIDLE_CONTROL` at BAR+0x24C (non-I3C) or BAR+0x2CC (I3C) instead.
> - "CS_DEVIDLESTAT" → **Does NOT exist** in LPSS HAS v5.2.

### Clock Domains (HAS-Verified)

| Clock | Frequency | Source | Used By |
|-------|-----------|--------|---------|
| rosc_fast_clk | 100 MHz | Ring Oscillator | Main clock: internal logic, OCP fabric, IP slices |
| i2c_clk | 100 MHz | Derived from rosc_fast_clk | I2C controllers |
| i3c_clk | 100 MHz (PTL/WCL), **200 MHz (NVL)** | Derived from rosc_fast_clk | I3C controllers |
| spi_clk | 100 MHz | Derived from rosc_fast_clk | SPI controllers |
| uart_clk | 100 MHz | Derived from rosc_fast_clk | UART controllers |
| iosf_prim2_clk | 125 MHz | ICC (PLL) | IOSF Primary bus interface |
| side_clk | 76.8 MHz | ICC (Ring Oscillator) | IOSF Sideband bus interface |

### Reset Domains (HAS-Verified)

Each controller and its DMA engine has an **independent reset**, controlled via Convergence Layer registers.

**Global Resets (override per-controller):**
| Reset | Scope |
|-------|-------|
| PGCBRST | Power gate cold boot reset — full LPSS subsystem |
| PRIMRST | Primary reset — full LPSS subsystem |
| SIDERST | Sideband reset — IOSF SB interface |
| GAONRST | Global always-on reset — always-on domain |

### PythonSV Initialization

```python
import namednodes
from namednodes import *
import baseaccess

itp.unlock()
sv.refresh()
```

---

## Power Domains (HAS-Verified)

> **Source:** LPSS_HAS.html §Power Management — IP v5.2, Rev 1.02

LPSS uses a **single Power Gate Domain (PGD)** covering the bridge, base fabric, and all slices.
Power gating is triggered when **all** slices are in D0i3 OR D3-Hot.

| Power Domain | Signal Name | Coverage | Always-On? |
|-------------|------------|----------|------------|
| **PGD (gated)** | `pd_lpss_VNN_gated` | Bridge + base fabric + all controller slices | No — gated by PMC during PG |
| **AON** | `pd_lpss_VNN` | Always-on logic within LPSS (PGCB, wake logic) | Yes (while Vnn active) |
| **VNNAON** | `pd_lpss_VNNAON` | Always-on even during Vnn removal (I3C IBI wake, rtc_clk) | Yes (always) |

### Power Gating Trigger Conditions

PG occurs when **ALL** of these are true:
1. All slices in D0i3 or D3-Hot (via DEVIDLE_CONTROL or PMCSR)
2. PMC asserts `pmc_sw_pg_req_b = 0` (software PG request)
3. `D0I3_MAX_POW_LAT_PG_CONFIG` enables are set (PMCRE=1, DEVIDLEN=1, D3HEN=1)

### I3C Power Management Exception

> ⚠️ **CRITICAL:** I3C controllers do **NOT** support D0i3. Vnn removal is not supported in D0i3 for I3C.
> I3C can only enter D3-Hot for power gating. D0i2 (clock gating only) is supported.

| Controller | D0i2 | D0i3 | D3-Hot | Vnn Removal |
|-----------|------|------|--------|-------------|
| I2C | ✅ | ✅ | ✅ | ✅ (via D0i3 or D3) |
| SPI | ✅ | ✅ | ✅ | ✅ (via D0i3 or D3) |
| UART | ✅ | ✅ | ✅ | ✅ (via D0i3 or D3) |
| **I3C** | ✅ | ❌ **NOT supported** | ✅ | ✅ (via D3 only) |

---

## D-State Transition Flows (HAS-Verified)

### D0 → D0i2 (Auto Clock Gate)

D0i2 is **automatic** — the controller clock-gates itself when idle.

1. Controller finishes all pending transactions
2. FIFOs drain to empty
3. HW auto-asserts internal clock gate
4. Resume latency: ~10 μs (no register restore needed)

> No software action required. D0i2 is entered/exited by hardware automatically.

### D0 → D0i3 (Deep Idle — NOT for I3C)

D0i3 adds partial power gating on top of clock gating:

1. **SW writes** `DEVIDLE_CONTROL[2] = 1` (devidle bit) at BAR+0x24C (non-I3C) or BAR+0x2CC (I3C)
2. **Poll** `DEVIDLE_CONTROL[0]` (cmd_in_progress) until 0 — confirms transition complete
3. **HW auto-gates** clocks and may remove partial power
4. Resume latency: ~100 μs (register restore may be needed)
5. **Check** `DEVIDLE_CONTROL[3]` (restore_required) — if 1, SW must restore saved registers

```python
def enter_d0i3(port, is_i3c=False, name=""):
    """Enter D0i3 via DEVIDLE_CONTROL. NOT supported for I3C!"""
    import time
    
    if is_i3c:
        print(f"  ❌ {name}: I3C does NOT support D0i3 — use D3-Hot instead")
        return False
    
    # DEVIDLE_CONTROL offset differs: 0x24C (non-I3C), 0x2CC (I3C)
    devidle = port.devidle_control.read()
    port.devidle_control.write(devidle | 0x4)  # Set devidle bit[2]
    
    # Poll cmd_in_progress bit[0]
    for _ in range(100):
        val = port.devidle_control.read()
        if (val & 0x1) == 0:
            print(f"  ✅ {name}: Entered D0i3 (DEVIDLE_CONTROL=0x{val:08X})")
            return True
        time.sleep(0.001)
    
    print(f"  ❌ {name}: D0i3 entry timeout")
    return False
```

### D0 → D3-Hot (OS-Initiated Full Power Down)

D3-Hot is initiated by the OS writing PMCSR:

1. **OS/driver** disables controller (I2C: IC_ENABLE[0]=0; I3C: HC_CONTROL[31]=0)
2. **OS writes** `PMCSR[1:0] = 11b` (D3-Hot) at PCI config offset 0x84
3. **HW asserts** clock gate → power gate sequence
4. **PMC** may remove Vnn if all LPSS slices are in D3/D0i3
5. Resume latency: ~1-10 ms (full register restore required)

> ⚠️ **CRITICAL — LTR before D3:** If `CS_IDLELTR` bit[15] (RequirementType) is non-zero,
> SW **MUST** clear `CS_IDLELTR` to 0x00000000 **before** writing PMCSR to D3. Failure to do
> so leaves a stale LTR requirement that can block S0ix.

### D3-Hot → D0 (Resume)

1. **OS writes** `PMCSR[1:0] = 00b` (D0)
2. **HW restores** power → de-asserts clock gate
3. **SW checks** `DEVIDLE_CONTROL[3]` (restore_required):
   - If 1: SW must restore all saved registers (see Save/Restore section)
   - Write 1 to `DEVIDLE_CONTROL[3]` to clear (write-1-to-clear)
4. **Re-initialize** the controller (I2C: IC_CON, IC_TAR, IC_ENABLE; I3C: HC_CONTROL, DAT entries)

---

## Save/Restore Registers (HAS-Verified)

> **Source:** LPSS_HAS.html §Power Management — Save/Restore

When power gating occurs (D0i3 or D3), register state is lost. The save/restore mechanism has two groups:

### Group 1: MMIO CL + PCI Config (SW-managed)

These must be saved by SW before D3 entry and restored after D0 re-entry:

| Category | Registers |
|----------|-----------|
| **PCI Config Header** | Command, BAR0, BAR1, Interrupt Line/Pin, MSI capability |
| **MMIO Convergence Layer** | CS_ACTIVELTR, CS_IDLELTR, DEVIDLE_CONTROL |
| **SPI-specific** | SPI_CS_CONTROL (BAR+0x224) — chip select polarity, retained during PG |
| **SPI-specific** | SPI delayed RX clock config (BAR+0x250) — retained during PG |
| **UART-specific** | CTS_Override (BAR+0x250) — retained during PG |

### Group 2: Bridge Private Registers (SW-managed)

| Category | Registers |
|----------|-----------|
| **SAI Policy** | Registers at 0x700–0x770 (64-bit each) |
| **PCICFGCTRL** | Per-function PCI config control registers (0x200–0x238) |
| **Private config** | Bridge private configuration registers |

### Registers Retained During Power Gating (NOT lost)

These survive power gating and do **not** need save/restore:

- Bridge private registers (Group 2 — retained in always-on domain)
- PCI configuration headers (retained by hardware)
- LTR registers (CS_ACTIVELTR, CS_IDLELTR)
- DEVIDLE_CONTROL
- SPI_CS_CONTROL (BAR+0x224)
- SPI delayed RX clock (BAR+0x250)
- UART CTS_Override (BAR+0x250)

### Force Clocks for Save/Restore

> Before performing bulk save/restore (PTL/WCL/NVL only), **force clocks ON** to ensure
> all registers are accessible:

```python
# Force clocks ON before save/restore
# GEN_PVT_LOW_REGRW2 at bridge private offset 0x604, bit 3 = force_clk_on
gen_pvt = lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_low_regrw2.gen_pvt_low_regrw2
val = gen_pvt.read()
gen_pvt.write(val | (1 << 3))  # Set bit 3 = force clocks on

# ... perform save/restore operations ...

# Release forced clocks
gen_pvt.write(val & ~(1 << 3))  # Clear bit 3
```

### Bulk Read/Write for Save/Restore (PTL/WCL/NVL onwards)

PTL and later platforms support **IOSF SB Bulk Read/Write** messages for faster save/restore:

- **BulkRd** (opcode varies) — Read contiguous register block in one SB transaction
- **BulkWr** (opcode varies) — Write contiguous register block in one SB transaction

> ⚠️ **LNL onwards:** I3C reset bit must be set to 1 **regardless of controller state** before
> issuing a bulk read. This is a known HW requirement.

---

## Vnn Removal Entry/Exit Sequences (HAS-Verified)

> **Source:** LPSS_HAS.html §Power Management — Vnn Entry/Exit

Vnn removal is the deepest LPSS power state — Vnn voltage rail is removed entirely.
Only the VNNAON domain (rtc_clk, I3C IBI wake logic) remains powered.

### Vnn Removal Entry (Simplified)

1. All LPSS controllers in D0i3 or D3-Hot
2. PMC sends `pmc_sw_pg_req_b = 0` (power gate request)
3. Bridge PGCB (Power Gate Control Block) begins entry sequence:
   a. Assert `func_reset` to all slices
   b. Gate `rosc_fast_clk` (100 MHz main clock)
   c. Gate `iosf_prim2_clk` (125 MHz IOSF primary)
   d. Gate `side_clk` (76.8 MHz sideband)
4. PGCB asserts `pg_ack` to PMC
5. PMC asserts `vnn_ack` — Vnn rail removed
6. Only `rtc_clk` (32.768 kHz) remains active for I3C IBI monitoring
7. PGCB uses `rosc_slow_clk` (2.56 MHz) for internal housekeeping

### Vnn Restoration Exit (Simplified)

1. Wake event (I3C IBI, PME, or PMC request) triggers exit
2. PMC de-asserts `vnn_ack` — Vnn rail restored
3. Wait for Vnn stabilization
4. PGCB de-asserts `pg_ack` to PMC
5. De-gate `rosc_fast_clk`, `iosf_prim2_clk`, `side_clk`
6. De-assert `func_reset` from all slices
7. HW sets `DEVIDLE_CONTROL[3]` (restore_required) on each slice
8. SW must restore registers for slices that were in D3 (see Save/Restore section)

### I3C IBI Wake During Vnn Removal (HAS-Verified)

I3C supports wake via In-Band Interrupt (IBI) even during Vnn removal:

1. I3C target device drives SDA low (IBI start)
2. VNNAON domain detects SDA transition using `rtc_clk` (32.768 kHz)
3. VNNAON logic asserts `vnn_req` to PMC
4. PMC restores Vnn rail
5. `rosc_fast_clk` restored → I3C controller resumes
6. I3C controller ACKs the IBI on the bus
7. IBI data read and delivered to host via interrupt
8. If no further activity, controller returns to idle → PMC may re-remove Vnn

> This is the only LPSS wake mechanism that works during full Vnn removal.
> I2C/SPI/UART require PMC-level wake (GPIO wake pin or PME).

---

## LTR Configuration & Coalescing (HAS-Verified)

> **Source:** LPSS_HAS.html §LTR, §iDMA

### LTR Register Format

Both `CS_ACTIVELTR` and `CS_IDLELTR` use the same format:

| Bits | Field | Description |
|------|-------|-------------|
| [9:0] | VALUE | Latency value (units defined by SCALE) |
| [12:10] | SCALE | `000`=1ns, `001`=32ns, `010`=1024ns, `011`=32768ns, `100`=1048576ns |
| [14:13] | Reserved | |
| [15] | REQ_TYPE | `0`=no requirement, `1`=requirement is valid |
| [25:16] | S_VALUE | Snoop latency value |
| [28:26] | S_SCALE | Snoop latency scale (same encoding as SCALE) |
| [30:29] | Reserved | |
| [31] | S_REQ_TYPE | `0`=no snoop requirement, `1`=snoop requirement valid |

### LTR Coalescing Rules

LPSS uses **N-to-1 coalescing** — all controller LTR values are merged into a single LTR message to PMC:

- **Coalescing policy:** The **lowest** (most demanding) LTR value is selected
- If ANY controller has `REQ_TYPE=1`, the coalesced LTR has a requirement
- Only when ALL controllers have `REQ_TYPE=0` does the coalesced LTR become "no requirement"

> ⚠️ **CRITICAL for S0ix:** Before entering D3, SW **MUST** write `CS_IDLELTR = 0x00000000`
> (clearing REQ_TYPE bit[15]) to remove the LTR requirement. If any controller leaves
> a stale idle LTR with REQ_TYPE=1, S0ix entry will be blocked.

### LTR Calculation Formulas

LTR values represent the maximum tolerable latency for the controller to resume from idle:

**I2C LTR formula** (based on FIFO half-full at given speed):
```
LTR = (FIFO_DEPTH / 2) × (byte_time)
byte_time = 9 bits / bit_rate  (8 data + 1 ACK)
```

**I2C LTR values** (at ½ FIFO = 32 bytes):

| Speed Mode | Bit Rate | Byte Time | LTR (32 bytes) |
|-----------|----------|-----------|-----------------|
| Standard (SM) | 100 Kbps | 80 μs | **2,560 μs** |
| Fast (FM) | 400 Kbps | 20 μs | **640 μs** |
| Fast-Plus (FM+) | 1 Mbps | 8 μs | **256 μs** |
| High-Speed (HS) | 3.4 Mbps | 2.35 μs | **75.3 μs** |

**SPI LTR formula** (at ½ FIFO = 128 bytes):
```
LTR = (FIFO_DEPTH / 2) × 8 / bit_rate
```

| Clock Rate | LTR (128 bytes) |
|-----------|-----------------|
| 1 Mbps | **1,024 μs** |
| 5 Mbps | **204.8 μs** |
| 10 Mbps | **102.4 μs** |
| 24 Mbps | **42.67 μs** |

**Programming example:**
```python
def program_ltr(port, active_us, idle_us, is_i3c=False, name=""):
    """Program LTR values for an LPSS controller.
    Values in microseconds. Set idle_us=0 to clear idle LTR before D3."""
    
    def encode_ltr(us_value):
        if us_value == 0:
            return 0x00000000  # No requirement
        # Use 1024ns scale (010) for μs-range values
        ns_value = int(us_value * 1000)
        scale = 0x2  # 1024 ns
        value = ns_value // 1024
        if value > 1023:
            scale = 0x3  # 32768 ns
            value = ns_value // 32768
        return (1 << 31) | (scale << 26) | (value << 16) | (1 << 15) | (scale << 10) | value
    
    active_reg = encode_ltr(active_us)
    idle_reg = encode_ltr(idle_us)
    
    offset_active = 0x2BC if is_i3c else 0x210
    offset_idle = 0x2C0 if is_i3c else 0x214
    
    port.cs_activeltr.write(active_reg)
    port.cs_idleltr.write(idle_reg)
    print(f"  {name}: ACTIVE_LTR=0x{active_reg:08X} ({active_us}μs), IDLE_LTR=0x{idle_reg:08X} ({idle_us}μs)")
```

---

## PME Handling (HAS-Verified)

> **Source:** LPSS_HAS.html §IOSF Sideband Messages, §Power Management

### PME Messages

| Message | Opcode | Direction | Description |
|---------|--------|-----------|-------------|
| Assert_PMEWithData | 0x52 | LPSS → PMC | Assert PME (wake request) |
| DeAssert_PMEWithData | 0x53 | LPSS → PMC | De-assert PME |

### PME Storm Prevention

> ⚠️ **CRITICAL BUG:** Clearing `PMCSR.PME_Status` (bit[15]) **before** clearing `PMCSR.PME_En` (bit[8])
> causes a **PME storm** — the controller repeatedly sends Assert_PME messages.

**Correct PME disable sequence:**
```python
def safe_pme_disable(port, name=""):
    """Disable PME without triggering PME storm.
    MUST clear PME_En BEFORE PME_Status!"""
    pmcsr = port.cfg.cfg_pmcsr.read()
    
    # Step 1: Clear PME_En (bit 8) FIRST
    port.cfg.cfg_pmcsr.write(pmcsr & ~(1 << 8))
    
    # Step 2: THEN clear PME_Status (bit 15) by writing 1
    pmcsr = port.cfg.cfg_pmcsr.read()
    port.cfg.cfg_pmcsr.write(pmcsr | (1 << 15))  # W1C
    
    print(f"  ✅ {name}: PME disabled safely (PME_En cleared before PME_Status)")

def WRONG_pme_disable(port):
    """❌ DO NOT DO THIS — causes PME storm!"""
    pmcsr = port.cfg.cfg_pmcsr.read()
    # WRONG: clearing PME_Status while PME_En is still 1
    port.cfg.cfg_pmcsr.write(pmcsr | (1 << 15))  # W1C PME_Status
    # This triggers new PME assertion → infinite loop!
```

**Correct PME enable sequence for D3 wake:**
```python
def enable_pme_wake(port, name=""):
    """Enable PME wake for D3 — used for devices that need to wake the platform."""
    pmcsr = port.cfg.cfg_pmcsr.read()
    
    # Set PME_En (bit 8)
    port.cfg.cfg_pmcsr.write(pmcsr | (1 << 8))
    
    # Now enter D3
    pmcsr = port.cfg.cfg_pmcsr.read()
    port.cfg.cfg_pmcsr.write((pmcsr & ~0x3) | 0x3)  # PowerState = D3
    
    print(f"  ✅ {name}: PME enabled, entering D3 (wake-capable)")
```

### Known HAS STARs (Power Management)

| STAR | Summary |
|------|---------|
| 4175499 | PM-related STAR (check HAS for details) |
| 4175488 | PM-related STAR (check HAS for details) |
| 4105199 | PM-related STAR (check HAS for details) |
| 4142080 | PM-related STAR (check HAS for details) |

### Known HSDs (Power Management)

| HSD | Summary |
|-----|---------|
| 16019395124 | PM-related HSD (check HSDES for full details) |
| 16020014569 | PM-related HSD (check HSDES for full details) |

---

## NVL Port Inventory

### NVL PCD-H (14 PCI functions)

> **HAS-Verified:** NVL PCD-H and PCH-S have identical controller counts.
> I2C0-3 and UART0-1 use DMA; I2C4-5 and UART2 are PIO-only; all SPI and I3C use DMA.

```python
nvl_pcdh_ports = {
    # I2C (6 ports): I2C0-3 = DMA, I2C4-5 = PIO
    'i2c0':    'namednodes.sv.socket0.pcd.lpss.i2c0',
    'i2c1':    'namednodes.sv.socket0.pcd.lpss.i2c1',
    'i2c2':    'namednodes.sv.socket0.pcd.lpss.i2c2',
    'i2c3':    'namednodes.sv.socket0.pcd.lpss.i2c3',
    'i2c4':    'namednodes.sv.socket0.pcd.lpss.i2c4',    # PIO only
    'i2c5':    'namednodes.sv.socket0.pcd.lpss.i2c5',    # PIO only
    # UART (3 ports): UART0-1 = DMA, UART2 = PIO
    'hsuart0': 'namednodes.sv.socket0.pcd.lpss.hsuart0',
    'hsuart1': 'namednodes.sv.socket0.pcd.lpss.hsuart1',
    'hsuart2': 'namednodes.sv.socket0.pcd.lpss.hsuart2', # PIO only
    # SPI (3 ports): all DMA
    'spi0':    'namednodes.sv.socket0.pcd.lpss.spi0',
    'spi1':    'namednodes.sv.socket0.pcd.lpss.spi1',
    'spi2':    'namednodes.sv.socket0.pcd.lpss.spi2',
    # I3C (4 instances in 2 PCI controllers): all DMA
    'i3c0':    'namednodes.sv.socket0.pcd.lpss.i3c0',   # Controller#1 (I3C0/I3C1) — pf_top_12
    'i3c1':    'namednodes.sv.socket0.pcd.lpss.i3c1',   # Controller#2 (I3C2/I3C3) — pf_top_13
}
```

### NVL PCH-S (14 PCI functions)

```python
nvl_pchs_ports = {
    'i2c0':    'namednodes.sv.socket0.pch.lpss.i2c0',
    'i2c1':    'namednodes.sv.socket0.pch.lpss.i2c1',
    'i2c2':    'namednodes.sv.socket0.pch.lpss.i2c2',
    'i2c3':    'namednodes.sv.socket0.pch.lpss.i2c3',
    'i2c4':    'namednodes.sv.socket0.pch.lpss.i2c4',
    'i2c5':    'namednodes.sv.socket0.pch.lpss.i2c5',
    'i3c0':    'namednodes.sv.socket0.pch.lpss.i3c0',   # Controller#1 (I3C0/I3C1) — pf_top_12
    'i3c1':    'namednodes.sv.socket0.pch.lpss.i3c1',   # Controller#2 (I3C2/I3C3) — pf_top_13
    'spi0':    'namednodes.sv.socket0.pch.lpss.spi0',
    'spi1':    'namednodes.sv.socket0.pch.lpss.spi1',
    'spi2':    'namednodes.sv.socket0.pch.lpss.spi2',
    'hsuart0': 'namednodes.sv.socket0.pch.lpss.hsuart0',
    'hsuart1': 'namednodes.sv.socket0.pch.lpss.hsuart1',
    'hsuart2': 'namednodes.sv.socket0.pch.lpss.hsuart2',
}
```

---

## D3 State Verification

### Read Power State for All Ports

```python
def check_all_port_power_states(ports_dict):
    """Check D-state for all LPSS ports."""
    print("=== LPSS Power State Report ===\n")
    d0_ports, d3_ports, error_ports = [], [], []
    
    for name, path in ports_dict.items():
        try:
            port = eval(path)
            pmcsr = port.cfg.cfg_pmcsr.read()
            power_state = pmcsr & 0x3
            pme_en = (pmcsr >> 8) & 0x1
            pme_status = (pmcsr >> 15) & 0x1
            
            state_label = {0: "D0 (Active)", 1: "D1", 2: "D2", 3: "D3hot"}
            label = state_label.get(power_state, "Unknown")
            
            icon = "✅" if power_state == 3 else ("⚡" if power_state == 0 else "⚠️")
            print(f"  {icon} {name:10s}: {label}  PME_En={pme_en} PME_Status={pme_status}")
            
            if power_state == 0:
                d0_ports.append(name)
            elif power_state == 3:
                d3_ports.append(name)
        except Exception as e:
            print(f"  ❌ {name:10s}: ERROR — {e}")
            error_ports.append(name)
    
    print(f"\nSummary: D0={len(d0_ports)} D3={len(d3_ports)} Errors={len(error_ports)}")
    if d0_ports:
        print(f"  ⚡ Active (D0): {', '.join(d0_ports)}")
    if d3_ports:
        print(f"  ✅ Low Power (D3): {', '.join(d3_ports)}")
    if error_ports:
        print(f"  ❌ Errors: {', '.join(error_ports)}")
    
    return d0_ports, d3_ports, error_ports

# Usage:
check_all_port_power_states(nvl_pcdh_ports)
```

### Verify Expected D-State

```python
def verify_expected_d_state(port_path, expected_state, name=""):
    """Verify a specific port is in expected D-state."""
    port = eval(port_path)
    pmcsr = port.cfg.cfg_pmcsr.read()
    actual = pmcsr & 0x3
    expected_name = {0: 'D0', 3: 'D3hot'}.get(expected_state, f'D{expected_state}')
    actual_name = {0: 'D0', 3: 'D3hot'}.get(actual, f'D{actual}')
    
    if actual == expected_state:
        print(f"✅ {name}: in expected state {expected_name}")
        return True
    else:
        print(f"❌ {name}: MISMATCH — expected {expected_name}, got {actual_name}")
        return False
```

### Force D0 Transition (Debug Only)

```python
def force_d0(port_path, name=""):
    """Force controller to D0 for debug access. USE WITH CAUTION."""
    port = eval(port_path)
    pmcsr = port.cfg.cfg_pmcsr.read()
    if (pmcsr & 0x3) == 3:
        port.cfg.cfg_pmcsr.write(pmcsr & ~0x3)  # Clear PowerState bits
        import time; time.sleep(0.01)
        new_pmcsr = port.cfg.cfg_pmcsr.read()
        print(f"⚠️ {name}: Forced D0 (was D3). New PMCSR={hex(new_pmcsr)}")
    else:
        print(f"ℹ️ {name}: Already in D{pmcsr & 0x3}")
```

---

## Clock Gating Verification

### Discover Clock Gating Registers

```python
# Search LPSS clock gating registers
clock_gate_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*clk.*gate|lpss.*clk.*ctrl|lpss.*pwr.*gate",
    searchType="registers"
)
for reg in clock_gate_regs:
    print(f"Register: {reg} = {hex(reg.read())}")

# Fabric-level clock gating (per VJT mapping)
fabric_clk_regs = namednodes.sv.socket0.pcd.search(
    regexpression="file_iosf2axi_pci_pf_top.*clk|file_iosf2axi_pci_pf_top.*gate",
    searchType="registers"
)
for reg in fabric_clk_regs:
    print(f"Fabric CLK: {reg} = {hex(reg.read())}")
```

### Per-Port Clock Status via PMCSR + Activity

A device in D3 has its clocks gated. Combined PMCSR + activity status gives full picture:

```python
def check_clock_gating_all(ports_dict):
    """Check clock gating status for all LPSS ports."""
    print("=== LPSS Clock Gating Report ===\n")
    
    for name, path in ports_dict.items():
        try:
            port = eval(path)
            pmcsr = port.cfg.cfg_pmcsr.read()
            power_state = pmcsr & 0x3
            
            # Check activity based on controller type
            activity = None
            if 'i2c' in name:
                try:
                    ic_status = port.ic_status.read()
                    activity = ic_status & 0x1
                    master_active = (ic_status >> 5) & 0x1
                    fifo_empty = (ic_status >> 2) & 0x1  # TFE bit
                    print(f"  {name}: D{power_state} | Activity={activity} MasterActive={master_active} TxFIFOEmpty={fifo_empty}")
                except:
                    print(f"  {name}: D{power_state} | (status not accessible — likely D3)")
                    continue
            elif 'spi' in name:
                try:
                    sscr0 = port.sscr0.read()
                    sse = (sscr0 >> 7) & 0x1
                    print(f"  {name}: D{power_state} | SSE(enable)={sse}")
                except:
                    print(f"  {name}: D{power_state} | (not accessible — likely D3)")
                    continue
            elif 'hsuart' in name:
                try:
                    lsr = port.lsr.read()
                    tx_empty = (lsr >> 6) & 0x1
                    data_ready = lsr & 0x1
                    print(f"  {name}: D{power_state} | TxEmpty={tx_empty} DataReady={data_ready}")
                except:
                    print(f"  {name}: D{power_state} | (not accessible — likely D3)")
                    continue
            elif 'i3c' in name:
                try:
                    dev_ctrl = port.search(regexpression="device_ctrl|dev_ctrl", searchType="registers")
                    if dev_ctrl:
                        val = dev_ctrl[0].read()
                        print(f"  {name}: D{power_state} | DevCtrl={hex(val)}")
                    else:
                        print(f"  {name}: D{power_state}")
                except:
                    print(f"  {name}: D{power_state} | (not accessible — likely D3)")
                    continue
            
            # Verdict
            if power_state == 3:
                print(f"    ✅ Clock GATED (D3)")
            elif power_state == 0 and activity == 0:
                print(f"    ⚠️ Idle but D0 — clock may NOT be gated")
            elif power_state == 0 and activity == 1:
                print(f"    ℹ️ Active in D0 — clock correctly running")
        except Exception as e:
            print(f"  ❌ {name}: ERROR — {e}")

check_clock_gating_all(nvl_pcdh_ports)
```

### Stuck-Active Port Diagnostic

When a port is idle but won't enter D3 (clock not gating):

```python
def diagnose_stuck_active(port_path, name=""):
    """Full diagnostic for a port stuck in D0 when it should be idle."""
    port = eval(port_path)
    
    print(f"\n=== Stuck-Active Diagnostic: {name} ===")
    
    # 1. Power state
    pmcsr = port.cfg.cfg_pmcsr.read()
    print(f"1. Power State: D{pmcsr & 0x3}")
    
    # 2. Controller-specific activity check
    if 'i2c' in name.lower():
        ic_status = port.ic_status.read()
        ic_enable = port.ic_enable.read()
        ic_intr_stat = port.ic_intr_stat.read()
        print(f"2. IC_STATUS: {hex(ic_status)}")
        print(f"   Activity={ic_status & 0x1}, TFNF={( ic_status >> 1) & 0x1}, TFE={(ic_status >> 2) & 0x1}")
        print(f"   RFNE={(ic_status >> 3) & 0x1}, MasterActive={(ic_status >> 5) & 0x1}")
        print(f"3. IC_ENABLE: {hex(ic_enable)}")
        if ic_enable & 0x1:
            print("   ⚠️ Controller ENABLED — disable to allow clock gating")
        print(f"4. IC_INTR_STAT: {hex(ic_intr_stat)}")
        if ic_intr_stat != 0:
            print("   ⚠️ Pending interrupts — may prevent clock gating")
    elif 'hsuart' in name.lower():
        lsr = port.lsr.read()
        print(f"2. LSR: {hex(lsr)}")
        print(f"   DataReady={lsr & 0x1}, OverrunErr={(lsr >> 1) & 0x1}")
        print(f"   TxHoldEmpty={(lsr >> 5) & 0x1}, TxEmpty={(lsr >> 6) & 0x1}")
    elif 'spi' in name.lower():
        sscr0 = port.sscr0.read()
        print(f"2. SSCR0: {hex(sscr0)}, SSE(enable)={(sscr0 >> 7) & 0x1}")
    
    print(f"\nRecommendation:")
    print(f"  1. Check OS driver runtime PM status")
    print(f"  2. Verify no pending transfers/interrupts")
    print(f"  3. Cross-ref HSDES for known clock gating sightings")
```

---

## VJT Fabric-Level Access

*Source: `C:\pythonsv\novalake\vjt\lpss\nvlh_cltap.py`*

| Fabric ID | Controller | PythonSV Name |
|-----------|-----------|--------------|
| pf_top_0–5 | I2C0–5 | `i2c0`–`i2c5` |
| pf_top_6–8 | UART0–2 | `hsuart0`–`hsuart2` |
| pf_top_9–11 | SPI0–2 | `spi0`–`spi2` |
| pf_top_12 | I3C0/I3C1 (shared) | `i3c0` |
| pf_top_13 | I3C2/I3C3 (shared) | `i3c1` |

```python
import sys
sys.path.insert(0, r'C:\pythonsv\novalake')
from vjt.lpss import lpss_main as lmain

for port in lmain.lhc.ports:
    print(f"{port.protocol}{port.port_number}: fabric={port.fabric}")
```

---

## D3 Entry Prerequisites

Before a controller can enter D3:

1. **No active transactions** — FIFO empty, no in-progress transfers
2. **Clocks gated** — Functional clocks must be gated first
3. **Driver released device** — OS runtime PM suspended the device
4. **Interrupts cleared** — No pending interrupts

```python
def check_d3_prerequisites(port_path, name=""):
    """Check if all prerequisites for D3 entry are met."""
    port = eval(port_path)
    ok = True
    
    print(f"\n=== D3 Prerequisites: {name} ===")
    
    # 1. Power state
    pmcsr = port.cfg.cfg_pmcsr.read()
    ps = pmcsr & 0x3
    print(f"1. Current state: D{ps}")
    
    # 2. Activity (generic check)
    try:
        if 'i2c' in name.lower():
            ic_status = port.ic_status.read()
            if ic_status & 0x1:
                print("2. ❌ Active transactions detected")
                ok = False
            else:
                print("2. ✅ No active transactions")
        elif 'hsuart' in name.lower():
            lsr = port.lsr.read()
            if not ((lsr >> 6) & 0x1):  # TX not empty
                print("2. ❌ TX FIFO not empty")
                ok = False
            else:
                print("2. ✅ TX empty")
        else:
            print("2. ℹ️ Activity check skipped (manual verification needed)")
    except:
        print("2. ℹ️ Cannot read status (device may already be in D3)")
    
    # 3. PME config
    pme_en = (pmcsr >> 8) & 0x1
    print(f"3. PME_En={pme_en} {'(wake enabled)' if pme_en else '(wake disabled)'}")
    
    return ok
```

---

## IP-Specific Disable Procedures (Before D3 Entry)

> **Source:** DW_apb_i2c Databook v2.02a §3.8.1 "Disabling DW_apb_i2c",
> DWC_mipi_i3c Databook v1.00a §2.5 "Abort / Disable / Resume"

Before an LPSS controller can enter D3, the IP must be properly disabled. An abrupt D3 entry while
the IP is active can leave stale state, corrupt FIFOs, or cause the controller to hang on next D0 entry.

### I2C Disable Procedure (Databook §3.8.1)

The DW_apb_i2c requires a specific sequence to disable cleanly:

1. **Write IC_ENABLE[0] = 0** — Request disable
2. **Poll IC_ENABLE_STATUS[0]** — Wait until it reads `0` (controller acknowledged disable)
3. **If disable doesn't complete** (bus busy / SCL held low):
   - Write **IC_ENABLE[1] = 1** (ABORT) — Flushes TX FIFO and issues STOP
   - Poll **IC_RAW_INTR_STAT[6]** (TX_ABRT) — Wait for abort completion
   - Read **IC_TX_ABRT_SOURCE** to determine cause
   - Read **IC_CLR_TX_ABRT** to clear the abort status
4. **If SDA stuck low** (bus hang):
   - Write **IC_ENABLE[3] = 1** (SDA_STUCK_RECOVERY) — Sends 9 SCL pulses + STOP
   - Poll **IC_ENABLE_STATUS[3]** — Wait until recovery completes
   - Check **IC_TX_ABRT_SOURCE[17]** (ABRT_SDA_STUCK_NOT_RECOVERED) — If set, HW recovery failed

```python
def i2c_safe_disable(port, name="", timeout_ms=100):
    """Safely disable I2C controller per databook §3.8.1.
    Must be called before D3 entry to avoid stale state."""
    import time
    
    # Step 1: Request disable
    ic_enable = port.ic_enable.read()
    port.ic_enable.write(ic_enable & ~0x1)  # Clear ENABLE bit[0]
    
    # Step 2: Poll IC_ENABLE_STATUS[0] until 0
    start = time.time()
    while time.time() - start < timeout_ms / 1000.0:
        status = port.ic_enable_status.read()
        if (status & 0x1) == 0:
            print(f"  ✅ {name}: Disabled cleanly (IC_ENABLE_STATUS=0x{status:X})")
            return True
        time.sleep(0.001)
    
    # Step 3: Disable didn't complete — try ABORT
    print(f"  ⚠️ {name}: Disable timeout, issuing ABORT...")
    port.ic_enable.write(0x2)  # ABORT bit[1]
    
    start = time.time()
    while time.time() - start < timeout_ms / 1000.0:
        raw_intr = port.ic_raw_intr_stat.read()
        if (raw_intr >> 6) & 0x1:  # TX_ABRT
            abrt_src = port.ic_tx_abrt_source.read()
            _ = port.ic_clr_tx_abrt.read()  # Clear abort
            print(f"  ⚠️ {name}: Aborted. TX_ABRT_SOURCE=0x{abrt_src:08X}")
            
            # Check if SDA stuck
            if (abrt_src >> 17) & 0x1:
                print(f"  ❌ {name}: SDA stuck — attempting recovery...")
                port.ic_enable.write(0x8)  # SDA_STUCK_RECOVERY bit[3]
                time.sleep(0.05)
                recovery_status = port.ic_enable_status.read()
                if (recovery_status >> 3) & 0x1:
                    print(f"  ❌ {name}: SDA recovery FAILED — manual intervention needed")
                    return False
                print(f"  ✅ {name}: SDA recovered")
            return True
        time.sleep(0.001)
    
    print(f"  ❌ {name}: ABORT timeout — controller may be hung")
    return False
```

### I3C Disable / Abort / Resume Procedure (Databook §2.5)

The DWC_mipi_i3c has three operations that affect bus state:

| Operation | HC_CONTROL Bit | Effect |
|-----------|---------------|--------|
| **Disable** | BUS_ENABLE[31] = 0 | Graceful shutdown — waits for current transfer, issues STOP |
| **Abort** | ABORT[29] = 1 | Immediate abort — enters HALT state, must be recovered |
| **Resume** | RESUME[30] = 1 | Clears HALT state — resumes normal operation after abort |

#### Disable (Graceful)
1. Write `HC_CONTROL[31] = 0` (clear BUS_ENABLE)
2. Poll `HC_CONTROL[31]` until it reads 0 — controller finishes current transfer then stops
3. If it doesn't clear → the controller is stuck (see HSDES 18044213731 for chicken bit issue)

#### Abort → HALT → Resume
1. Write `HC_CONTROL[29] = 1` (ABORT) — controller enters **HALT** state
2. Detect HALT: Read `PRESENT_STATE_DEBUG(0x14C)`:
   - `CM_TFR_ST_STATUS[21:16] = 0x13` → HALT state
   - `CM_TFR_STATUS[13:8] = 0x0F` → HALTED
3. **Drain responses**: Read all pending responses from RESPONSE_QUEUE until empty
4. **Reset queues**: Write `RESET_CONTROL` to clear CMD/RESP/TX/RX queues
5. Write `HC_CONTROL[30] = 1` (RESUME) — self-clearing bit
6. Verify: `PRESENT_STATE_DEBUG` no longer shows HALT

> ⚠️ **CRITICAL**: If `DMAC_NO_CLEAR_CTRL_Q_ON_ABORT` (chicken bit[1:0]) = 3, the DMA queue is NOT
> cleared on abort, leaving stale state. This causes BUS_ENABLE to get stuck. Set chicken bit = 0
> before using abort. See HSDES 18044213731.

```python
def i3c_safe_disable(port, name="", timeout_ms=500):
    """Safely disable I3C controller per databook §2.5.
    Uses graceful disable (not abort) to avoid HALT state."""
    import time
    
    # Read current HC_CONTROL
    hc_ctrl = port.lpio.hc_control.read()
    bus_enabled = (hc_ctrl >> 31) & 0x1
    
    if not bus_enabled:
        print(f"  ℹ️ {name}: Bus already disabled (HC_CONTROL=0x{hc_ctrl:08X})")
        return True
    
    # Clear BUS_ENABLE (bit 31)
    port.lpio.hc_control.write(hc_ctrl & ~(1 << 31))
    
    # Poll until BUS_ENABLE reads 0
    start = time.time()
    while time.time() - start < timeout_ms / 1000.0:
        hc_ctrl = port.lpio.hc_control.read()
        if not ((hc_ctrl >> 31) & 0x1):
            print(f"  ✅ {name}: Bus disabled gracefully (HC_CONTROL=0x{hc_ctrl:08X})")
            return True
        time.sleep(0.005)
    
    # BUS_ENABLE stuck — likely chicken bit issue
    print(f"  ❌ {name}: BUS_ENABLE stuck! HC_CONTROL=0x{hc_ctrl:08X}")
    print(f"      Check chicken bit gen_pvt_high_regrw4[1:0] — must be 0, not 3")
    print(f"      See HSDES 18044213731")
    return False


def i3c_abort_and_resume(port, name=""):
    """Abort current I3C operation, drain, and resume.
    Use when controller is stuck mid-transfer."""
    import time
    
    # Step 1: Assert ABORT (bit 29)
    hc_ctrl = port.lpio.hc_control.read()
    port.lpio.hc_control.write(hc_ctrl | (1 << 29))
    time.sleep(0.01)
    
    # Step 2: Verify HALT via PRESENT_STATE_DEBUG
    psd = port.lpio.present_state_debug.read()
    cm_tfr_st = (psd >> 16) & 0x3F
    cm_tfr = (psd >> 8) & 0x3F
    print(f"  {name}: PRESENT_STATE_DEBUG=0x{psd:08X} (CM_TFR_ST=0x{cm_tfr_st:02X}, CM_TFR=0x{cm_tfr:02X})")
    
    if cm_tfr_st == 0x13:
        print(f"  ✅ {name}: HALT state confirmed")
    else:
        print(f"  ⚠️ {name}: Not in HALT (CM_TFR_ST=0x{cm_tfr_st:02X}), may not need recovery")
    
    # Step 3: Drain response queue
    drained = 0
    for _ in range(64):
        try:
            resp = port.lpio.response_queue_port.read()
            if resp == 0 or resp == 0xFFFFFFFF:
                break
            drained += 1
        except:
            break
    print(f"  {name}: Drained {drained} responses from queue")
    
    # Step 4: Reset queues
    port.lpio.reset_control.write(0x1E)  # Reset CMD+RESP+TX+RX queues
    time.sleep(0.005)
    
    # Step 5: RESUME (bit 30) — self-clearing
    hc_ctrl = port.lpio.hc_control.read()
    port.lpio.hc_control.write(hc_ctrl | (1 << 30))
    time.sleep(0.01)
    
    # Step 6: Verify no longer in HALT
    psd = port.lpio.present_state_debug.read()
    cm_tfr_st = (psd >> 16) & 0x3F
    if cm_tfr_st != 0x13:
        print(f"  ✅ {name}: Resumed from HALT (CM_TFR_ST=0x{cm_tfr_st:02X})")
        return True
    else:
        print(f"  ❌ {name}: Still in HALT after resume!")
        return False
```

### DMA Idle Requirements

Before D3 entry, any active DMA channels must be quiesced:

1. **Check DMA status**: Ensure no active DMA transfers on the controller's channel
2. **Flush DMA buffers**: Any pending DMA data must be flushed or aborted
3. **Disable DMA**: Clear the DMA enable bits in the controller's configuration
4. **Wait for DMA idle**: Poll DMA channel status until idle

> For I2C: `IC_DMA_CR[1:0]` controls TX/RX DMA enable — clear both before D3
> For I3C: DMA is controlled via the HCI DMA rings — all rings must be empty
> For SPI: `SSCR0` SSE must be 0, and DMA channels must be idle
> For UART: `UDMA_CR` DMA control register must show idle

---

## OS-Side Power State Verification

### Windows

```powershell
# Check device power state
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*I2C*" -or $_.FriendlyName -like "*UART*" -or $_.FriendlyName -like "*SPI*"} | Format-Table FriendlyName, Status

# Check wake-armed devices
powercfg /devicequery wake_armed

# Energy report (10-second trace)
powercfg /energy /duration 10
```

### Linux

```bash
# Check runtime PM status for LPSS devices
for dev in /sys/bus/pci/devices/0000:00:1[5-9].* /sys/bus/pci/devices/0000:00:1e.*; do
    echo "$dev: $(cat $dev/power/runtime_status 2>/dev/null)"
done

# Check autosuspend delay
cat /sys/bus/pci/devices/0000:00:15.0/power/autosuspend_delay_ms
```

---

## Common Issues

### 1. Controller Stuck in D0

**Symptoms:** PMCSR=D0, system can't enter S0ix, high idle power
**Root causes:** Driver holding active ref, pending transaction, clock not gated, BIOS config
**Debug:**
1. Run `diagnose_stuck_active()` above
2. Check OS driver runtime PM logs
3. Use `fv-lpss/config-checkout` to verify register config
4. Check HSDES for known sightings

### 2. D3 Entry Delayed

**Symptoms:** Eventually enters D3 but too slow, intermittent S0ix failures
**Root causes:** Long autosuspend delay, slow transaction completion, interrupt storm
**Debug:** Check driver autosuspend timeout, monitor interrupt rate

### 3. Spurious Wake from D3

**Symptoms:** Enters D3 but immediately exits, PME_Status set, D0/D3 cycling
**Root causes:** Connected device generating wake, EMI, shared interrupt line
**Debug:** Check PME_Status after wake, identify wake source

### 4. Clock Stuck Active (Not Gating)

**Symptoms:** Device idle but D0, higher power than expected
**Root causes:** Pending FIFO data, software override, unserviced interrupt, HW bug
**Debug:** Check FIFO status, interrupt status, controller enable bits

### 5. Clock Gating Too Aggressive

**Symptoms:** Transfers fail, first byte lost after idle, timeout errors
**Root causes:** Clock gated before transaction completes, clock restore too slow

### 6. I3C BUS_ENABLE Stuck After Abort (HSDES 18044213731)

**Symptoms:** HC_CONTROL bit31 (BUS_ENABLE) cannot be cleared after an ABORT operation. I3C controller becomes unrecoverable — cannot disable/re-enable bus, subsequent commands fail or hang.
**Root causes:** Chicken bit register `gen_pvt_high_regrw4` bits[1:0] (`DMAC_NO_CLEAR_CTRL_Q_ON_ABORT`) set to 3 (default on some steppings). This tells the DMA controller NOT to clear its control queue on abort, leaving stale state that blocks bus disable.
**Debug:**
1. Read chicken bit: `lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4`
2. If bits[1:0]=3 → apply workaround: write 0
3. Check HC_CONTROL bit31 — if stuck at 1 after attempting clear, this sighting is confirmed
4. Soft reset the I3C controller (`reset_control` write 0x2) to recover, then re-enable with chicken_bit=0

**Interaction with power states:**
- A stuck BUS_ENABLE can prevent the I3C controller from entering D3 (controller appears active)
- This can cascade to block S0ix entry if the I3C controller is an S0ix prerequisite
- After applying the workaround (chicken_bit=0), verify D3 entry with `fv-lpss/power-state`

**Validated on:** PTL-H B0 (WOS), NVL-PCD-H A0

---

## Verification Checklist

For each LPSS port (I2C0–5, I3C Ctrl#1–2, SPI0–2, HSUART0–2):

**D3 State:**
- [ ] PMCSR PowerState reads correct value (D0 if active, D3 if idle)
- [ ] PME_En matches expected wake configuration
- [ ] PME_Status clear (no spurious wake events)
- [ ] Unused/fused-off controllers show function-disabled in PSF

**Clock Gating:**
- [ ] Active ports: clock running, transactions completing
- [ ] Idle ports: clock gated, device in D3
- [ ] No pending interrupts blocking clock gating
- [ ] Controller enable bits correct (disabled = can gate)
- [ ] FIFO empty before clock gating expected

**System Level:**
- [ ] OS runtime PM shows correct status
- [ ] No LPSS devices blocking S0ix entry
- [ ] Cross-reference with `check_all_lpss_ports_status.py` output

**I3C-Specific:**
- [ ] Chicken bit `gen_pvt_high_regrw4` bits[1:0] = 0 (not 3) — prevents BUS_ENABLE stuck issue
- [ ] HC_CONTROL bit31 (BUS_ENABLE) can be toggled on/off cleanly
- [ ] No stale abort state (HC_CONTROL bit29 = 0)

---

## Related Skills

- **`fv-lpss/config-checkout`** — IP enumeration, registers, and pad mode
- **`fv-lpss/failure-analysis`** — Analyze D3/clock-gating related test failures
- **`pysv`** — General PythonSV usage patterns
