# FV-ISH Power Management Skill

## Skill Identity

**Skill**: `fv-ish/power`
**Domain**: ISH Power Management, D-States, SRAM Power Gating, Runtime PM, Sensor Batching, S0ix
**Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
**Last Updated**: 2026-03-16 (rev2.0 — updated with TTL PMU/CCU register data)
**Primary Platform**: NVL (Nova Lake) — other platforms noted where different

> Load this skill when the user asks about: ISH power states, D0/D0i2/D0i3/D3, runtime PM, SRAM power gating, VNN requests, clock gating, sensor batching, wake-on-sensor, S0ix, ISH as S0ix blocker, or power consumption measurement.

---

## IMPORTANT: HAS-First Policy

**Always load `fv-ish/has` first** for power state register definitions, PMC sideband messages, and NVL-specific power architecture. Content in this skill is based on public sources (Linux kernel ISH driver, Intel power management documentation) and TTL ISH OSXML register data. All register addresses and PMC message formats MUST be verified against the platform-specific ISH HAS.

---

## ISH Power Architecture Overview

### ISH as an Always-On Subsystem
ISH is designed as a low-power always-on subsystem within the Intel Client SoC. Key characteristics:
- **Powered from VNNAON rail** (remains powered during S0ix system low-power states)
- **Can operate independently** while the rest of the SoC is in deep sleep
- **Wake source**: ISH can wake the host from low-power states on sensor events
- **PMC integration**: ISH power state is coordinated with the Power Management Controller (PMC) via IPC sideband channel at offset `0x2000`
- **Per-bank SRAM gating**: 20 SRAM banks (32KB each, 640KB total) can be individually power-gated

### Integration with PCH/SoC Power Management
```
Host CPU + OS
    │
    ▼
Runtime PM Framework (Windows: PnP/WDM / Linux: rpm_suspend/resume)
    │
    ▼
ISH Host Driver (coordinates D-state transitions)
    │── IPC doorbell: "Host going to sleep, ISH transition to D0i3"
    ▼
ISH Firmware (manages sensor power, PMU, CCU)
    │
    ├── PMU (0x04200000) — SRAM power gating, wake events, VNN control
    ├── CCU (0x04300000) — Clock gating per-block
    ▼
PMC (Power Management Controller) — via IPC sideband (opcode 0x6F, tag 0x06)
    │── Manages ISH power rail, voltage, S0ix coordination
    ▼
ISH Hardware (clock/power gated based on D-state)
```

---

## D-States (Device Power States)

### Overview Table
| State | Power Level | ISH Activity | Sensor Activity | Wake Capable | Latency to D0 |
|-------|------------|-------------|----------------|-------------|---------------|
| **D0** | Full Power | Fully active, 200/100 MHz | All sensors active at full ODR | N/A | 0 ms |
| **D0i1** | Light Idle | Core idle, clocks active | Sensors active | Yes | < 1 ms |
| **D0i2** | Clock Gated | Per-block clock gating via CCU | Sensors at reduced ODR | Yes | < 10 ms |
| **D0i3** | Power Gated | SRAM banks gated, VNN released | Batch mode or AON-only | Yes (SMD) | 10–100 ms |
| **D3cold** | Off | ISH fully off | No sensor activity | No | > 500 ms |

### D0 — Full Power
- ISH LMT 3.8/3.9 processor running at 200 MHz (or 100 MHz reduced)
- All 20 SRAM banks active (640 KB), 8 KB ROM, 8 KB AON RF SRAM
- All IO controllers active: 3× I2C, 2× I3C, 3× UART, 2× SPI
- DMA engine active, IPC doorbell active
- **PMU.SRAM_PG_EN** = `0x3FFFFFFF` (all 30 bank/tile bits enabled for gating when entering low power)

### D0i1 — Light Idle
- LMT core enters idle (WFI/HLT), clocks still running
- Peripheral clocks remain active
- Wake on any interrupt (sensor, timer, IPC doorbell)
- Minimal power savings but instant wake

### D0i2 — Clock Gating
- CCU gates clocks to idle peripherals
- Per-block clock gating via CCU registers at `0x04300000`
- SRAM remains powered, context preserved
- Wake latency: < 10 ms

### D0i3 — Power Gating (Deep Sleep)
- SRAM banks selectively power-gated via PMU (`SRAM_PG_EN`)
- VNN power rail released (`VNN_REQ` register)
- AON RF SRAM (8 KB) retains critical context
- ISH wakes on configured wake events (PMU `WAKE_EVENT`)
- ISH→PMC sideband: reports SRAM gating energy (opcode 0x6F, tag 0x06)
- **Entry**: Host requests via D0I3C register, or ISH FW self-initiated
- **Exit**: Wake event, host doorbell, timer

### D3cold — Device Off
- ISH completely powered off, all state lost
- Requires full re-initialization: Boot ROM → CSE → BUP → Main FW
- FW reload: CSE loads BUP (64 KB max), host loads Main FW (1.5 MB max) via IMR
- **Entry**: System S3/S4/S5, or device disabled
- **Exit**: System resume (S3 optimized: CSE saves uncompressed FW in IMR, hash compare on resume)

---

## PMU Registers (TTL — Base 0x04200000)

The Power Management Unit controls SRAM power gating, wake events, VNN rail, and power sequencing.

### PMU Register Map

| Offset | Register | Default | Description |
|--------|----------|---------|-------------|
| `0x00` | `SRAM_PG_EN` | `0x3FFFFFFF` | SRAM Power Gate Enable — 30 bits for bank/tile gating |
| `0x04` | `SRAM_PG_STS` | `0x00000000` | SRAM Power Gate Status (RO) |
| `0x08` | `HOST_WAKEUP` | `0x00000000` | Host wakeup control |
| `0x0C` | `WAKE_EVENT` | `0x00000000` | Wake event status (R/W1C) |
| `0x10` | `MASK_EVENT` | `0xFFFFFFFF` | Wake event mask (1=masked) |
| `0x14` | `D0I3_RESIDENCY` | `0x00000000` | D0i3 residency counter |
| `0x18` | `FABRIC_CNT` | `0x3A980008` | Fabric power timing counter |
| `0x1C` | `PG_TIMING_0` | varies | Power gate FSM timing (T_PG_ASSERT) |
| `0x20` | `PG_TIMING_1` | varies | Power gate FSM timing (T_PG_DEASSERT) |
| `0x24` | `PG_TIMING_2` | varies | Power gate FSM timing (T_ISO_ASSERT) |
| `0x28` | `PG_TIMING_3` | varies | Power gate FSM timing (T_ISO_DEASSERT) |
| `0x2C` | `PG_FSM_STS` | `0x00000000` | Power gate FSM status (RO) |
| `0x30` | `RF_ROM_PWR_CTRL` | varies | RF SRAM and ROM power control |
| `0x34` | `SRAM_PWR_CTRL` | `0x0F0F0F02` | SRAM power control (retention, isolation) |
| `0x38` | `PMU_SPARE` | `0x00000000` | Spare register |
| `0x3C` | `VNN_REQ` | `0x00000000` | VNN rail request (32-bit, each bit = 1 requester) |
| `0x40` | `VNN_REQ_ACK` | `0x00000000` | VNN rail request acknowledge (RO) |

### SRAM_PG_EN (0x00) — SRAM Power Gate Enable

```
 31  30  29                                           1   0
 ┌───┬───┬───┬───┬───┬───┬───┬───┬── ... ──┬───┬───┬───┬───┐
 │RSV│RSV│T29│T28│T27│T26│T25│T24│         │ T1│ T0│B1 │B0 │
 └───┴───┴───┴───┴───┴───┴───┴───┴── ... ──┴───┴───┴───┴───┘
```

- Bits [29:0]: Each bit enables power gating for one SRAM bank/tile
- Default `0x3FFFFFFF`: All 30 bits set = all banks eligible for gating when ISH enters low power
- Write `0` to a bit to keep that bank always powered (pinned for AON data)
- **20 SRAM banks × 32 KB = 640 KB total**; extra tile bits for sub-bank granularity

### WAKE_EVENT (0x0C) — Wake Event Sources

| Bit | Source | Description |
|-----|--------|-------------|
| [31] | `VNN_ACK` | VNN acknowledge wake |
| [30] | `D0i3_EXIT` | D0i3 exit request |
| [29] | `SPI1` | SPI controller 1 activity |
| [28] | `SPI0` | SPI controller 0 activity |
| [27] | `I2C2` | I2C controller 2 activity |
| [26] | `I2C1` | I2C controller 1 activity |
| [25] | `I2C0` | I2C controller 0 activity |
| [24] | `DMA` | DMA engine completion |
| [23] | `UART2` | UART 2 activity |
| [22] | `UART1` | UART 1 activity |
| [21] | `UART0` | UART 0 activity |
| [20] | `IPC_HOST` | IPC HOST channel doorbell |
| [19] | `IPC_CSE` | IPC CSE channel doorbell |
| [18] | `IPC_PMC` | IPC PMC channel doorbell |
| [17] | `HPET_T1` | HPET Timer 1 expiry |
| [16] | `HPET_T0` | HPET Timer 0 expiry |
| [15:2] | Reserved | — |
| [1] | `GPIO` | GPIO wake event |
| [0] | `WDT` | Watchdog timer wake |

### VNN_REQ (0x3C) — VNN Rail Request

```
 31                                                    0
 ┌────────────────────────────────────────────────────────┐
 │  Each bit = one requester needing VNN rail active      │
 │  Write 1 to request, 0 to release                     │
 │  VNN remains on as long as any bit is set             │
 └────────────────────────────────────────────────────────┘
```

- ISH FW sets bits when peripherals need VNN rail (DRAM access, external sensor IO)
- All bits must be 0 before ISH can fully enter D0i3 with VNN released
- `VNN_REQ_ACK` (0x40) reflects PMC acknowledgment

### SRAM_PWR_CTRL (0x34) — Default `0x0F0F0F02`

Controls retention and isolation modes for SRAM power domains:
- Byte 0 `[7:0]` = `0x02`: Global power control mode
- Byte 1 `[15:8]` = `0x0F`: Retention voltage settings
- Byte 2 `[23:16]` = `0x0F`: Isolation control
- Byte 3 `[31:24]` = `0x0F`: Power switch timing

---

## CCU Registers (TTL — Base 0x04300000)

The Clock Control Unit manages per-block clock gating for power savings.

### CCU Register Map

| Offset | Register | Default | Description |
|--------|----------|---------|-------------|
| `0x00` | `TRUNK_CG` | varies | Trunk (global) clock gate control |
| `0x04` | `I3C_CG` | varies | I3C controller clock gate |
| `0x08` | `UART_CG` | varies | UART clock gate (all 3 instances) |
| `0x0C` | `I2C_CG` | varies | I2C clock gate (all 3 instances) |
| `0x10` | `SPI_CG` | varies | SPI clock gate (both instances) |
| `0x14` | `GPIO_CG` | varies | GPIO clock gate |
| `0x18` | `HPET_CG` | varies | HPET timer clock gate |
| `0x1C` | `IPC_CG` | varies | IPC channels clock gate |
| `0x20` | `SRAM_CG` | varies | SRAM controller clock gate |
| `0x24` | `PMU_CG` | varies | PMU clock gate |
| `0x28` | `DMA_CG` | varies | DMA engine clock gate |
| `0x2C` | `WDT_CG` | varies | Watchdog timer clock gate |
| `0x30` | `FABRIC_CG` | varies | Fabric clock gate |
| `0x34` | `DTF_CG` | varies | DTF (debug trace fabric) clock gate |
| `0x3C` | `RST_HIS` | `0x00000000` | Reset History — records reset sources |

### CCU Clock Gate Control Bits (per block)

Each CG register typically uses:
- Bit [0]: `CG_EN` — 1=enable automatic clock gating for this block
- Bit [1]: `CG_FORCE` — 1=force clock gated (override)
- Bit [2]: `CG_STATUS` (RO) — 1=clock is currently gated

### RST_HIS (0x3C) — Reset History

Records what caused the last ISH reset:
- Bit [0]: Power-on reset
- Bit [1]: Watchdog reset (WDT T2 expired)
- Bit [2]: Software reset
- Bit [3]: PMC-initiated reset
- W1C to clear after reading

---

## D0i3 Transition via D0I3C Register

The D0I3C register in the IPC HOST channel (offset `0x6D0` from BAR0) controls D0i3 entry/exit:

```python
# === TTL D0i3 Transition ===
IPC_D0I3C = 0x6D0  # In HOST IPC channel (BAR0-relative)

# D0I3C bit fields:
D0I3C_CIP  = (1 << 0)   # Command In Progress (RO)
D0I3C_IR   = (1 << 1)   # Interrupt Request enable
D0I3C_D0I3 = (1 << 2)   # D0i3 state request
D0I3C_RR   = (1 << 3)   # Restore Required (RW/1C, default=1)
D0I3C_IRC  = (1 << 4)   # Interrupt Request Capability (RO)

def request_d0i3(pch_ish):
    """Request ISH to enter D0i3 via D0I3C register."""
    # Read current D0I3C
    d0i3c = pch_ish.mem.read32(IPC_D0I3C)
    print(f"D0I3C before: {hex(d0i3c)}")

    # Set D0i3 request bit
    d0i3c |= D0I3C_D0I3
    pch_ish.mem.write32(IPC_D0I3C, d0i3c)

    # Wait for CIP to go high then low (transition complete)
    import time
    deadline = time.time() + 1.0
    saw_cip = False
    while time.time() < deadline:
        val = pch_ish.mem.read32(IPC_D0I3C)
        if val & D0I3C_CIP:
            saw_cip = True
        elif saw_cip:
            # CIP went high then low = transition complete
            print(f"D0I3C after: {hex(val)}, D0i3 entered successfully")
            return True
        time.sleep(0.001)

    print("D0i3 entry timeout")
    return False

def request_d0_exit(pch_ish):
    """Request ISH to exit D0i3 back to D0."""
    d0i3c = pch_ish.mem.read32(IPC_D0I3C)
    # Clear D0i3 bit
    d0i3c &= ~D0I3C_D0I3
    pch_ish.mem.write32(IPC_D0I3C, d0i3c)

    import time
    deadline = time.time() + 1.0
    while time.time() < deadline:
        val = pch_ish.mem.read32(IPC_D0I3C)
        if not (val & D0I3C_CIP):
            rr = bool(val & D0I3C_RR)
            print(f"D0 restored. Restore Required={rr}")
            return True
        time.sleep(0.001)

    print("D0 exit timeout")
    return False

def read_pmu_wake_events(pch_ish):
    """Read PMU wake event register to see what woke ISH from D0i3."""
    # Note: PMU registers at 0x04200000 are MIA-internal, accessed via ISH FW
    # or via IOSF sideband from host debug tools
    wake = pch_ish.iosf.read32(0x04200000 + 0x0C)  # WAKE_EVENT
    sources = []
    wake_map = {
        31: "VNN_ACK", 30: "D0i3_EXIT", 29: "SPI1", 28: "SPI0",
        27: "I2C2", 26: "I2C1", 25: "I2C0", 24: "DMA",
        23: "UART2", 22: "UART1", 21: "UART0", 20: "IPC_HOST",
        19: "IPC_CSE", 18: "IPC_PMC", 17: "HPET_T1", 16: "HPET_T0",
        1: "GPIO", 0: "WDT"
    }
    for bit, name in wake_map.items():
        if wake & (1 << bit):
            sources.append(name)
    print(f"Wake events: {hex(wake)} → {', '.join(sources) or 'none'}")
    return wake, sources
```

---

## D-State Transition Flows

### D0 → D0i3 (Runtime Suspend)
```
Host Runtime PM: rpm_suspend() called
    │
    ▼
ISH Driver: IPC doorbell → ISH FW: "SUSPEND: going to D0i3"
    │
    ▼
ISH FW: completes pending DMA transfers, drains IPC messages
    │
    ▼
ISH FW: configures sensor batching (if wake-on-sensor desired)
    │
    ▼
ISH FW: configures PMU.MASK_EVENT (unmask desired wake sources)
    │
    ▼
ISH FW: releases VNN (clears all VNN_REQ bits)
    │
    ▼
ISH FW: ACKs suspend via IPC doorbell
    │
    ▼
ISH Driver: writes D0I3C[2]=1 to enter D0i3
    │
    ▼
PMU: gates SRAM banks per SRAM_PG_EN, CCU gates clocks
    │
    ▼
ISH in D0i3 (AON RF SRAM retains critical context)
```

### D0i3 → D0 (Runtime Resume)
```
Trigger: wake event (sensor, timer, host doorbell) → PMU.WAKE_EVENT
    │
    ▼
PMU: restores SRAM banks, CCU restores clocks
    │
    ▼
ISH FW: resumes from AON context, re-requests VNN (VNN_REQ bits)
    │
    ▼
ISH FW: IPC doorbell → Host: "RESUME: ISH back in D0"
    │
    ▼
Host Driver: reads D0I3C, sees RR=1 (Restore Required), clears RR
    │
    ▼
Host Driver: resumes DMA, re-enables sensor streaming
    │
    ▼
ISH in D0
```

---

## Runtime Power Management (Runtime PM)

### Linux Runtime PM Integration
ISH driver uses Linux runtime PM framework:

```c
// Driver probe:
pm_runtime_set_autosuspend_delay(dev, 2000);  // 2s idle before autosuspend
pm_runtime_use_autosuspend(dev);
pm_runtime_enable(dev);

// On sensor activity:
pm_runtime_get_sync(dev);   // Ensure D0 before sending IPC
// ... sensor operation ...
pm_runtime_put_autosuspend(dev);  // Allow suspend after idle

// Callbacks:
static int ish_pm_suspend(struct device *dev) { /* D0→D0i3 via D0I3C */ }
static int ish_pm_resume(struct device *dev)  { /* D0i3→D0, check RR bit */ }
```

### Windows Runtime PM Integration
- WDF (KMDF) framework handles D-state transitions via PnP callbacks
- `EvtDeviceD0Entry` / `EvtDeviceD0Exit` for D-state transitions
- Idle timeout configured via `WdfDeviceAssignS0IdleSettings`

### Idle Timeout Configuration
| Platform | Default Idle Timeout | Configuration Location |
|----------|--------------------|-----------------------|
| Linux | 2000 ms | `pm_runtime_set_autosuspend_delay()` |
| Windows | Platform-specific | Registry: `IdleTimeout` under device key |

---

## Sensor Batching

### Concept
Sensor batching accumulates sensor samples in ISH SRAM while the host is in a low-power state, then bulk-delivers them when the host wakes.

```
Without Batching:
  Sample 1 → DMA → Host (host wakes)
  Sample 2 → DMA → Host (host wakes)
  ... 100x per second (100 Hz ODR)

With Batching (1s batch window):
  Samples 1-100 accumulated in ISH SRAM (up to 640KB buffer)
  ─────────────── 1 second ───────────────
  Samples 1-100 → DMA → Host (host wakes once)
```

### Batching & SRAM Power Gating Interaction
- During batching in D0i3, only banks holding batch data remain powered
- PMU.SRAM_PG_EN controls which banks are gated
- ISH FW must keep banks with batch FIFO un-gated (clear corresponding bits in SRAM_PG_EN)
- Remaining banks can be fully gated for maximum power savings

### Batch Configuration
| Parameter | Description | Typical Values |
|-----------|-------------|---------------|
| **Max Batch Latency** | Maximum time to hold samples before delivery | 100 ms – 60 s |
| **FIFO Reserved Events** | Number of samples ISH can buffer | 50 – 10000 |
| **Wake-on-FIFO-full** | Wake host when FIFO reaches capacity | Enable/Disable |

### Batching API (Linux)
```bash
# Check if batching is supported
cat /sys/bus/iio/devices/iio:device0/buffer/hwfifo_enabled

# Set max batch latency (ns)
echo 1000000000 > /sys/bus/iio/devices/iio:device0/buffer/hwfifo_timeout
```

---

## Wake-on-Sensor

### Wake Sources (from PMU.WAKE_EVENT register)
| Wake Source | PMU Bit | Sensor Use Case |
|-------------|---------|----------------|
| GPIO | [1] | Sensor interrupt line (motion detect, proximity) |
| I2C0/1/2 | [25:27] | Sensor data ready on I2C bus |
| I3C (via I2C) | [25:26] | I3C IBI (In-Band Interrupt) wake |
| SPI0/1 | [28:29] | SPI sensor data ready |
| HPET_T0/T1 | [16:17] | Periodic batch timer expiry |
| IPC_HOST | [20] | Host doorbell wake (resume request) |
| WDT | [0] | Watchdog timer (safety wake) |

### Wake Mask Configuration
```python
def configure_wake_sources(pch_ish, wake_mask):
    """Configure which events can wake ISH from D0i3.
    
    Args:
        wake_mask: bitmask of PMU.MASK_EVENT — 1=masked (blocked), 0=unmasked (allowed)
    
    Example: Allow I2C0, GPIO, and HPET_T0 wakes:
        mask = 0xFFFFFFFF  # Start with all masked
        mask &= ~(1 << 25)  # Unmask I2C0
        mask &= ~(1 << 1)   # Unmask GPIO
        mask &= ~(1 << 16)  # Unmask HPET_T0
        configure_wake_sources(pch_ish, mask)
    """
    # PMU.MASK_EVENT at 0x04200000 + 0x10 (MIA-internal, via ISH FW or IOSF)
    pch_ish.iosf.write32(0x04200000 + 0x10, wake_mask)
```

### Wake Latency Requirements
- **S0ix → D0**: Target < 300 ms (platform-wide constraint)
- **ISH D0i3 → D0**: < 100 ms (SRAM restore + clock enable)
- **ISH contribution to wake**: ISH must detect and signal within < 10 ms of threshold crossing
- **Wake signal path**: Sensor → ISH GPIO/I2C → PMU.WAKE_EVENT → IPC_HOST doorbell → Host CPU interrupt

---

## S0ix (System Low-Power Idle)

### ISH Role in S0ix
S0ix is the system-level low-power idle state where the CPU is off but the system appears "on". ISH is one of the last subsystems to enter S0ix and one of the first to exit.

### S0ix Entry Requirements for ISH
For the platform to achieve S0ix (PC10), ISH must:
1. Complete all pending DMA transfers
2. Drain IPC HOST channel (doorbell BUSY=0)
3. Transition to D0i3 (D0I3C[2]=1, CIP=0)
4. Release VNN rail (all VNN_REQ bits = 0)
5. PMU acknowledges ready for S0ix

### ISH as S0ix Blocker
ISH can **block S0ix entry** if any of the following are true:
- IPC HOST channel has pending doorbell (BUSY=1)
- DMA transfer in progress
- VNN_REQ has any bit set (ISH requesting VNN rail)
- D0I3C.CIP stuck at 1 (D0i3 transition not completing)
- ISH firmware in error state (FWSTS not ready)

### Debugging ISH S0ix Blockage
```python
def check_ish_s0ix_blocker(pch_ish):
    """Diagnose why ISH may be blocking S0ix."""
    issues = []

    # Check D0I3C state
    d0i3c = pch_ish.mem.read32(0x6D0)  # IPC HOST D0I3C
    if not (d0i3c & (1 << 2)):
        issues.append(f"ISH NOT in D0i3: D0I3C={hex(d0i3c)}")
    if d0i3c & (1 << 0):
        issues.append(f"D0i3 CIP stuck: D0I3C={hex(d0i3c)}")

    # Check IPC doorbell
    inbound_db = pch_ish.mem.read32(0x048)
    if inbound_db & (1 << 31):
        issues.append(f"Inbound doorbell BUSY: DB={hex(inbound_db)}")
    outbound_db = pch_ish.mem.read32(0x054)
    if outbound_db & (1 << 31):
        issues.append(f"Outbound doorbell BUSY: DB={hex(outbound_db)}")

    # Check FWSTS
    fwsts = pch_ish.mem.read32(0x034)
    issues.append(f"FWSTS={hex(fwsts)}")

    if issues:
        for issue in issues:
            print(f"  S0ix blocker: {issue}")
    else:
        print("  ISH appears S0ix-ready (D0i3, no pending IPC)")

    return issues

# Additional tools:
# Linux: cat /sys/kernel/debug/pmc_core/lpm_requirements
# Windows: powercfg /sleepstudy /output sleepstudy.html
```

### S0ix Residency Measurement
```bash
# Linux: Check S0ix residency
cat /sys/kernel/debug/pmc_core/slp_s0_residency_usec

# Windows: SleepStudy or powercfg
powercfg /sleepstudy /output sleepstudy.html
```

---

## PMC Sideband Communication

ISH communicates with PMC via IPC sideband channel (base offset `0x2000`):

| Parameter | Value |
|-----------|-------|
| PMC IPC Channel | Offset `0x2000` from IPC base |
| Sideband Opcode | `0x6F` |
| Sideband Tag | `0x06` |
| Purpose | SRAM gating energy reporting, power state coordination |

The ISH FW sends periodic SRAM gating status to PMC so the platform power management can account for ISH power consumption in S0ix residency calculations.

---

## Power Measurement

### ISH Power Rails
| Rail | Description | Notes |
|------|-------------|-------|
| **VNNAON** | Always-on rail (ISH core, AON SRAM) | Remains on in D0i3/S0ix |
| **VNN** | Main SRAM/IO rail | Gated in D0i3 when all VNN_REQ bits clear |

### Power Profiling Methodology
1. Set up power measurement on ISH rails (PMIC register read or current probe)
2. Run sensor scenario (baseline D0): all sensors at max ODR
3. Enable runtime PM, measure D0i2 residency (CCU clock gating active)
4. Enable sensor batching, measure D0i3 residency (SRAM gating active)
5. Verify VNN released in D0i3 (VNN_REQ = 0, VNN_REQ_ACK = 0)
6. Compare power vs baseline

---

## Validation Points

### 1. D0 → D0i3 Transition
```python
def test_d0_to_d0i3():
    """Verify ISH transitions to D0i3 when idle."""
    # Disable all sensor consumers
    disable_all_sensor_apps()
    # Wait for runtime PM autosuspend (2s default)
    time.sleep(5)
    # Verify D0i3 via D0I3C register
    d0i3c = pch_ish.mem.read32(0x6D0)
    assert d0i3c & (1 << 2), f"ISH not in D0i3: D0I3C={hex(d0i3c)}"
    assert not (d0i3c & (1 << 0)), f"CIP still set: D0I3C={hex(d0i3c)}"
```

### 2. D0i3 → D0 Wake Latency
```python
def test_d0i3_wake_latency():
    """Verify ISH wakes from D0i3 within latency budget."""
    ensure_ish_in_d0i3()
    t_start = time.monotonic()
    trigger_sensor_wake()  # Assert GPIO to trigger PMU.WAKE_EVENT[1]
    wait_for_ipc_ready()   # Wait for doorbell available
    latency_ms = (time.monotonic() - t_start) * 1000
    assert latency_ms < 100, f"D0i3 wake latency too high: {latency_ms:.1f} ms"
    # Verify RR bit is set
    d0i3c = pch_ish.mem.read32(0x6D0)
    assert d0i3c & (1 << 3), "Restore Required bit should be set after D0i3 exit"
```

### 3. SRAM Power Gating Verification
```python
def test_sram_power_gating():
    """Verify SRAM banks are gated in D0i3."""
    # Configure all banks eligible for gating
    # (PMU.SRAM_PG_EN default = 0x3FFFFFFF)
    ensure_ish_in_d0i3()
    # Read PMU.SRAM_PG_STS to verify gating applied
    pg_sts = pch_ish.iosf.read32(0x04200000 + 0x04)
    assert pg_sts != 0, f"No SRAM banks gated in D0i3: PG_STS={hex(pg_sts)}"
```

### 4. VNN Release Verification
```python
def test_vnn_release_in_d0i3():
    """Verify ISH releases VNN rail when entering D0i3."""
    ensure_ish_in_d0i3()
    vnn_req = pch_ish.iosf.read32(0x04200000 + 0x3C)
    assert vnn_req == 0, f"VNN_REQ not released in D0i3: {hex(vnn_req)}"
```

### 5. Sensor Batching Functional Test
```python
def test_sensor_batching():
    """Verify sensor batching accumulates and delivers correct samples."""
    batch_window_ms = 1000
    odr_hz = 50
    expected_samples = (batch_window_ms / 1000) * odr_hz  # ~50 samples
    configure_sensor_batching(SENSOR_ID_ACCEL, max_latency_ms=batch_window_ms)
    ensure_ish_in_d0i3()
    time.sleep(batch_window_ms / 1000 + 0.5)
    batch = collect_batched_samples(SENSOR_ID_ACCEL)
    assert len(batch) >= expected_samples * 0.9, \
        f"Batch too small: {len(batch)} (expected ~{expected_samples})"
```

### 6. Clock Gating Verification
```python
def test_ccu_clock_gating():
    """Verify CCU gates clocks to idle peripherals."""
    # Ensure no active I2C/SPI/UART traffic
    disable_all_sensors()
    time.sleep(1)
    # Read CCU per-block CG status registers
    ccu_base = 0x04300000
    blocks = {"UART": 0x08, "I2C": 0x0C, "SPI": 0x10, "GPIO": 0x14, "DMA": 0x28}
    for name, offset in blocks.items():
        cg = pch_ish.iosf.read32(ccu_base + offset)
        is_gated = bool(cg & (1 << 2))  # CG_STATUS bit
        print(f"  CCU {name}: CG={hex(cg)}, gated={is_gated}")
```

### 7. Runtime PM Suspend/Resume Stress
```python
def test_runtime_pm_stress():
    """Verify ISH survives 100 runtime PM suspend/resume cycles."""
    for cycle in range(100):
        request_d0i3(pch_ish)
        assert wait_for_d0i3(timeout_ms=3000), f"D0i3 not reached at cycle {cycle}"
        request_d0_exit(pch_ish)
        assert wait_for_d0(timeout_ms=3000), f"D0 not reached at cycle {cycle}"
        assert verify_sensors_functional(), f"Sensors not functional at cycle {cycle}"
```

### 8. S0ix Entry with ISH
```python
def test_s0ix_entry():
    """Verify ISH does not block S0ix entry."""
    disable_all_sensor_apps()
    enter_system_s0ix()
    s0ix_achieved = check_s0ix_residency(min_duration_s=10)
    assert s0ix_achieved, "System failed to achieve S0ix — check ISH S0ix blockers"
```

### 9. Wake-on-Sensor
```python
def test_wake_on_sensor():
    """Verify accelerometer SMD wakes system from S0ix."""
    configure_smd_threshold(accel_threshold_g=0.5)
    enter_system_s0ix()
    assert not is_system_awake(), "System should be in S0ix"
    simulate_motion(accel_g=1.0)
    time.sleep(0.5)
    assert is_system_awake(), "System did not wake on SMD"
    latency = measure_wake_latency_ms()
    assert latency < 300, f"Wake latency too high: {latency} ms"
```

---

## Public References

- **Linux ISH Runtime PM**: https://github.com/torvalds/linux/blob/master/drivers/hid/intel-ish-hid/ipc/ipc.c
- **Linux Runtime PM Documentation**: https://www.kernel.org/doc/html/latest/power/runtime_pm.html
- **Intel S0ix Architecture**: https://www.intel.com/content/www/us/en/developer/articles/technical/power-management-states-p-states-c-states-and-package-c-states.html
