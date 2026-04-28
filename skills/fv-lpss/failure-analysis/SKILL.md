---
name: fv-lpss/failure-analysis
description: Analyze LPSS-related failures from NGA test results
---

# LPSS Failure Analysis

This skill provides procedures to identify, analyze, and triage LPSS (Low Power Subsystem) failures from NGA test execution results on the **Novalake (NVL)** platform.

---

## Overview

LPSS failures can manifest in various ways across I2C, I3C, SPI, and UART controllers. This skill helps you:

1. Identify LPSS-related test failures in NGA
2. Extract and analyze relevant logs
3. Classify failure types
4. Cross-reference with known issues (sightings)
5. Recommend next debug steps

---

## NVL Platform Context

### Controller Inventory

| Die | I2C | I3C | SPI | UART | Total PCI Functions |
|-----|-----|-----|-----|------|---------------------|
| PCH-S | I2C0–5 | I3C0–3 (2 controllers) | SPI0–2 | UART0–2 | 14 |
| PCD-H | I2C0–5 | I3C0–3 (2 controllers) | SPI0–2 | UART0–2 | 14 |

### NGA Test Name Patterns for LPSS

When filtering NGA results, use these keywords:
```python
LPSS_TEST_KEYWORDS = [
    'lpss', 'serialio', 'serial_io',
    'i2c', 'i3c', 'spi', 'uart', 'hsuart',
    'd3_lpss', 'lpss_d3', 'lpss_power',
    'lpss_traffic', 'lpss_enum', 'lpss_config',
]
```

---

## LPSS Failure Patterns

### I2C Controller Failures

**Common patterns in logs:**
```python
I2C_PATTERNS = [
    r'I2C.*Error',
    r'I2C.*Timeout',
    r'I2C.*NAK',           # No acknowledge
    r'I2C.*NACK',
    r'I2C.*Arbitration.*Lost',
    r'I2C.*Bus.*Busy',
    r'I2C.*Clock.*Stretch',
    r'I2C.*Transfer.*Fail',
]
```

**Typical failure modes:**
- **Timeout** — Slave not responding, clock stretching timeout
- **NAK/NACK** — Slave not acknowledging address or data
- **Arbitration Lost** — Multi-master collision
- **Bus Busy** — SDA/SCL stuck low

---

### I3C Controller Failures

**Common patterns in logs:**
```python
I3C_PATTERNS = [
    r'I3C.*Error',
    r'I3C.*Timeout',
    r'I3C.*CRC',           # CRC error
    r'I3C.*Parity',
    r'I3C.*Hot.*Join.*Fail',
    r'I3C.*DAA.*Fail',     # Dynamic Address Assignment
    r'I3C.*IBI.*Error',    # In-Band Interrupt
    r'I3C.*HDR.*Error',    # High Data Rate mode
]
```

**Typical failure modes:**
- **CRC Error** — Data integrity issue
- **DAA Failure** — Dynamic address assignment failed
- **IBI Error** — In-band interrupt mechanism failure
- **HDR Mode Error** — High data rate transition failure

**NVL-specific:** I3C operates in DMA mode. All 4 I3C interfaces (I3C0–3) are active. I3C0/I3C1 share Controller #1, I3C2/I3C3 share Controller #2.

#### I3C Abort Recovery Failure (HSDES 18044213731)

**Sighting:** `[PTL][LPSS] I3C fails to recover after ABORT with DMAC_NO_CLEAR_CTRL_Q_ON_ABORT=3 (the default)`

**Root Cause:** The DWC MIPI I3C DMA controller chicken bit register `gen_pvt_high_regrw4` (offset 0x61C) controls abort queue clearing behavior via bits[1:0] (`DMAC_NO_CLEAR_CTRL_Q_ON_ABORT`). When set to 3 (don't clear control queue on abort), the I3C controller fails to recover after any ABORT operation.

**Three Symptoms when chicken_bit[1:0]=3:**
1. **Subsequent commands/transfers abort** — Any command sent after an ABORT also aborts
2. **TID mismatch on responses** — Response TID does not match the command TID
3. **BUS_ENABLE bit stuck at 1** — HC_CONTROL bit31 cannot be cleared after abort (confirmed on PTL-H B0 WOS)

**Workaround:** Set chicken bit to 0 (`gen_pvt_high_regrw4 = 0x00000000`). The VJT framework already applies this for DMA mode (value=0) and PIO mode (value=5).

**Diagnostic pattern:**
```python
I3C_ABORT_PATTERNS = [
    r'I3C.*Abort.*Fail',
    r'I3C.*Abort.*Recovery',
    r'I3C.*BUS_ENABLE.*stuck',
    r'I3C.*TID.*mismatch',
    r'I3C.*HC_CONTROL.*abort',
    r'I3C.*DMAC_NO_CLEAR',
    r'I3C.*chicken.*bit',
]
```

**Diagnostic script:**
```python
# Check chicken bit state when I3C abort issues occur
import namednodes as nn
nn.sv.refresh()

# NVL: nn.sv.socket0.pcd.lpss.lpss_regs...
# PTL: nn.sv.socket0.soc.lpss.lpss_regs...
base = nn.sv.socket0.soc  # Change to socket0.pcd for NVL

cb = base.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
val = cb.read()
dmac_bits = val & 0x3
print("Chicken bit = 0x%08X, DMAC_NO_CLEAR_CTRL_Q_ON_ABORT = %d" % (val, dmac_bits))
if dmac_bits == 3:
    print("WARNING: Buggy default! I3C abort recovery will fail. Apply W/A: write 0")
elif dmac_bits == 0:
    print("OK: Workaround applied (DMA mode)")
elif dmac_bits == 5:
    print("OK: PIO mode setting")
```

**Reproduction methodology (validated on PTL-H B0 WOS):**
1. Enable I3C controller (BUS_ENABLE=1 in HC_CONTROL)
2. Set chicken bit to 3: `gen_pvt_high_regrw4.write(3)`
3. Send any I3C command (e.g., ENTDAA)
4. Trigger ABORT: set HC_CONTROL bit29
5. Attempt to clear BUS_ENABLE (write HC_CONTROL with bit31=0)
6. Read HC_CONTROL — BUS_ENABLE will be stuck at 1

**Cross-platform notes:**
- **PTL-H B0:** HW default is 0 (or BIOS applies W/A at boot). Symptom 3 confirmed reproducible.
- **NVL-PCD-H A0:** HW default is 0. VJT framework sets to 0 for DMA mode.
- **Bit-level mapping is NOT in Intel HAS** — it is in the Synopsys DWC MIPI I3C IP Databook (vendor-confidential).

**Affected platforms:** PTL-H, NVL (any platform using DWC MIPI I3C with DMA controller)

---

### I2C TX Abort Source Decoding (IC_TX_ABRT_SOURCE — Offset 0x80)

> **Source:** DW_apb_i2c Databook v2.02a — Register `IC_TX_ABRT_SOURCE`
> When an I2C transfer aborts, read this register to determine the exact cause. Multiple bits can be set simultaneously. The upper bits [31:16] contain `TX_FLUSH_CNT` — the number of TX FIFO entries flushed on abort.

| Bit | Name | Meaning | Recovery Action |
|-----|------|---------|-----------------|
| 0 | 7B_ADDR_NOACK | 7-bit address not ACKed | Check slave address, verify slave powered/present |
| 1 | 10ADDR1_NOACK | 10-bit addr byte1 not ACKed | Check slave address, verify 10-bit mode support |
| 2 | 10ADDR2_NOACK | 10-bit addr byte2 not ACKed | Check slave supports 10-bit addressing |
| 3 | TXDATA_NOACK | TX data not ACKed by slave | Slave NACK'd data — check slave FIFO/state |
| 4 | GCALL_NOACK | General Call not ACKed | No slave accepts general call on bus |
| 5 | GCALL_READ | General Call + read (illegal) | Fix software — GC is write-only |
| 6 | HS_ACKDET | High-speed master code ACKed (shouldn't be) | Bus contention in HS mode |
| 7 | SBYTE_ACKDET | START byte ACKed (shouldn't be) | Bus contention during START |
| 8 | HS_NORSTRT | HS mode but RESTART disabled | Enable IC_CON.IC_RESTART_EN |
| 9 | SBYTE_NORSTRT | START byte sent but RESTART disabled | Enable IC_CON.IC_RESTART_EN |
| 10 | 10B_RD_NORSTRT | 10-bit read but RESTART disabled | Enable IC_CON.IC_RESTART_EN |
| 11 | MASTER_DIS | Master op attempted with master disabled | Set IC_CON[0]=1 (master enable) |
| 12 | ARB_LOST | Arbitration lost (multi-master) | Retry transfer — another master won |
| 13 | SLVFLUSH_TXFIFO | Slave flushed TX FIFO (req while TX active) | Check slave-mode TX timing |
| 14 | SLV_ARBLOST | Slave lost bus during TX | Re-queue slave TX data |
| 15 | SLVRD_INTX | Slave read cmd received during write | Check master/slave role coordination |

**Diagnostic script:**
```python
def decode_i2c_tx_abrt_source(port_path, name="I2C"):
    """Read and decode IC_TX_ABRT_SOURCE after a transfer failure."""
    port = eval(port_path)
    abrt = port.ic_tx_abrt_source.read()
    tx_flush_cnt = (abrt >> 16) & 0xFFFF
    print("%s IC_TX_ABRT_SOURCE = 0x%08X (TX_FLUSH_CNT=%d)" % (name, abrt, tx_flush_cnt))
    
    ABRT_BITS = {
        0: "7B_ADDR_NOACK", 1: "10ADDR1_NOACK", 2: "10ADDR2_NOACK",
        3: "TXDATA_NOACK", 4: "GCALL_NOACK", 5: "GCALL_READ",
        6: "HS_ACKDET", 7: "SBYTE_ACKDET", 8: "HS_NORSTRT",
        9: "SBYTE_NORSTRT", 10: "10B_RD_NORSTRT", 11: "MASTER_DIS",
        12: "ARB_LOST", 13: "SLVFLUSH_TXFIFO", 14: "SLV_ARBLOST",
        15: "SLVRD_INTX"
    }
    for bit, label in ABRT_BITS.items():
        if abrt & (1 << bit):
            print("  [%d] %s — SET" % (bit, label))
    if abrt & 0xFFFF == 0:
        print("  No abort bits set")
```

---

### I2C Bus Recovery (SDA Stuck Low)

> **Source:** DW_apb_i2c Databook v2.02a — `IC_ENABLE[3]` SDA_STUCK_RECOVERY

When the I2C bus is stuck (SDA held low by a slave), the controller can attempt recovery:

```python
def i2c_bus_recovery(port_path, name="I2C"):
    """Attempt I2C bus recovery when SDA is stuck low."""
    port = eval(port_path)
    
    # Check if bus is stuck
    ic_status = port.ic_status.read()
    activity = ic_status & 0x1
    slv_activity = (ic_status >> 6) & 0x1
    print("%s IC_STATUS=0x%08X Activity=%d SlvActivity=%d" % (name, ic_status, activity, slv_activity))
    
    # Check for SDA stuck condition via IC_ENABLE_STATUS
    enable_status = port.ic_enable_status.read()
    sda_stuck = (enable_status >> 2) & 0x1  # Bit 2: SDA_STUCK_NOT_RECOVERED
    print("%s IC_ENABLE_STATUS=0x%08X SDA_Stuck_Not_Recovered=%d" % (name, enable_status, sda_stuck))
    
    if sda_stuck or (activity and not slv_activity):
        print("%s Bus appears stuck. Initiating SDA recovery..." % name)
        # Write IC_ENABLE[3]=1 to trigger SDA stuck recovery
        ic_enable = port.ic_enable.read()
        port.ic_enable.write(ic_enable | (1 << 3))
        
        import time
        time.sleep(0.01)  # Wait for recovery (sends up to 9 SCL clocks)
        
        # Check result
        enable_status = port.ic_enable_status.read()
        sda_recovered = not ((enable_status >> 2) & 0x1)
        print("%s SDA recovery %s" % (name, "SUCCEEDED" if sda_recovered else "FAILED"))
        return sda_recovered
    else:
        print("%s Bus appears OK — no recovery needed" % name)
        return True
```

**SDA stuck recovery sequence (from databook):**
1. Controller sends 9 SCL clock pulses
2. If SDA released → sends STOP condition → bus recovered
3. If SDA still low after 9 clocks → `IC_ENABLE_STATUS[2]` (SDA_STUCK_NOT_RECOVERED) = 1
4. If SDA_STUCK_NOT_RECOVERED=1 → hardware issue, check pull-ups and slave device

---

### I3C ERR_STATUS Response Code Decoding

> **Source:** DWC MIPI I3C Databook v1.00a — Response Descriptor `ERR_STATUS[31:28]`
> Every I3C command returns a response. The `ERR_STATUS` field in the response descriptor indicates the outcome. Some errors cause the controller to enter **HALT state**, requiring explicit recovery.

| ERR_STATUS | Name | Description | Causes HALT? | Recovery |
|------------|------|-------------|-------------|----------|
| 0x0 | NO_ERROR | Command completed successfully | No | — |
| 0x1 | CRC_ERROR | CRC check failed on received data | No | Retry transfer |
| 0x2 | PARITY_ERROR | Parity error in HDR mode | No | Retry, check signal integrity |
| 0x3 | FRAME_ERROR | Framing error detected | No | Retry, check bus timing |
| 0x4 | ADDR_HEADER_NACK | Address header NACK'd (broadcast) | **YES** | HALT recovery (see below) |
| 0x5 | ADDR_NACK | Target address NACK'd (direct) | No | Check target address/presence |
| 0x6 | OVERFLOW_UNDERFLOW | TX underflow or RX overflow in HDR | **YES** | HALT recovery; pre-load TX FIFO |
| 0x8 | ABORTED | Command was aborted (by master) | **YES** | HALT recovery |
| 0x9 | I2C_WR_DATA_NACK | I2C legacy write — data NACK'd | No | Check I2C slave state |
| 0xA | NOT_SUPPORTED | Command not supported by target | No | Check CCC support in target |

**Diagnostic script:**
```python
def decode_i3c_err_status(err_status_value):
    """Decode I3C response ERR_STATUS field."""
    ERR_CODES = {
        0x0: ("NO_ERROR", False),
        0x1: ("CRC_ERROR", False),
        0x2: ("PARITY_ERROR", False),
        0x3: ("FRAME_ERROR", False),
        0x4: ("ADDR_HEADER_NACK", True),
        0x5: ("ADDR_NACK", False),
        0x6: ("OVERFLOW_UNDERFLOW", True),
        0x8: ("ABORTED", True),
        0x9: ("I2C_WR_DATA_NACK", False),
        0xA: ("NOT_SUPPORTED", False),
    }
    name, halts = ERR_CODES.get(err_status_value, ("UNKNOWN_0x%X" % err_status_value, False))
    print("ERR_STATUS=0x%X: %s%s" % (err_status_value, name, " [HALTS CONTROLLER]" if halts else ""))
    return name, halts
```

---

### I3C HALT State Detection & Recovery

> **Source:** DWC MIPI I3C Databook v1.00a — Section 2.8.2 "Stall/Halt"
> The I3C controller enters **HALT** state when it encounters certain unrecoverable errors (broadcast NACK, abort, HDR overflow/underflow). In HALT, no new commands are dispatched until software performs explicit recovery.

**Detecting HALT state:**
```python
def check_i3c_halt_state(port_path, name="I3C"):
    """Check if I3C controller is in HALT state via PRESENT_STATE_DEBUG."""
    port = eval(port_path)
    
    # Read PRESENT_STATE_DEBUG (HCI offset 0x14C)
    psd = port.lpio.present_state_debug.read()
    cm_tfr_st = (psd >> 16) & 0x3F   # CM_TFR_ST_STATUS[21:16]
    cm_tfr = (psd >> 8) & 0x3F       # CM_TFR_STATUS[13:8]
    
    is_halted = (cm_tfr_st == 0x13) or (cm_tfr == 0x0F)
    print("%s PRESENT_STATE_DEBUG=0x%08X" % (name, psd))
    print("  CM_TFR_ST_STATUS=0x%02X %s" % (cm_tfr_st, "(HALT)" if cm_tfr_st == 0x13 else ""))
    print("  CM_TFR_STATUS=0x%02X %s" % (cm_tfr, "(HALTED)" if cm_tfr == 0x0F else ""))
    
    if is_halted:
        print("  >>> CONTROLLER IS IN HALT STATE — recovery required")
    return is_halted
```

**HALT recovery procedure (from databook):**
```python
def recover_i3c_from_halt(port_path, name="I3C"):
    """Recover I3C controller from HALT state.
    Procedure per DWC MIPI I3C Databook:
      1. Read all pending responses (drain RESPONSE_QUEUE)
      2. Reset command/TX/RX queues via RESET_CTRL
      3. Set HC_CONTROL.RESUME (bit 30) to exit HALT
      4. Verify controller resumes normal operation
    """
    import time
    port = eval(port_path)
    
    # Step 1: Drain pending responses
    print("%s Step 1: Draining response queue..." % name)
    for i in range(32):  # Max 32 responses
        try:
            resp = port.lpio.response_queue_port.read()
            err = (resp >> 28) & 0xF
            tid = (resp >> 24) & 0x7
            print("  Response[%d]: 0x%08X (ERR=0x%X, TID=%d)" % (i, resp, err, tid))
            if resp == 0 or resp == 0xFFFFFFFF:
                break
        except:
            break
    
    # Step 2: Reset queues via RESET_CTRL (HCI offset 0x01C)
    print("%s Step 2: Resetting queues..." % name)
    # Bit 0=SOFT_RST, Bit 1=CMD_QUEUE_RST, Bit 2=RESP_QUEUE_RST,
    # Bit 3=TX_FIFO_RST, Bit 4=RX_FIFO_RST, Bit 5=IBI_QUEUE_RST
    QUEUE_RESET_BITS = 0x3E  # Reset CMD + RESP + TX + RX + IBI queues (bits[5:1])
    port.lpio.reset_ctrl.write(QUEUE_RESET_BITS)
    time.sleep(0.001)
    
    # Step 3: Set RESUME bit (HC_CONTROL bit 30)
    print("%s Step 3: Setting RESUME bit..." % name)
    hc_ctrl = port.lpio.hc_control.read()
    port.lpio.hc_control.write(hc_ctrl | (1 << 30))  # Set RESUME
    time.sleep(0.001)
    
    # Step 4: Verify recovery
    print("%s Step 4: Verifying recovery..." % name)
    is_still_halted = check_i3c_halt_state(port_path, name)
    
    if not is_still_halted:
        print("%s HALT recovery SUCCEEDED" % name)
    else:
        print("%s HALT recovery FAILED — may need controller reset" % name)
        print("  Try: reset_ctrl.write(0x01) for full soft reset")
    
    return not is_still_halted
```

**Common HALT triggers and prevention:**

| Trigger | Prevention | Notes |
|---------|------------|-------|
| Broadcast NACK (ADDR_HEADER_NACK) | Ensure at least one target on bus before broadcast CCCs | ENTDAA with no targets will HALT |
| Abort with chicken_bit=3 | Set `gen_pvt_high_regrw4[1:0]=0` (see HSDES 18044213731) | Affects DMA mode abort recovery |
| HDR TX underflow | Pre-load TX data via `TX_START_THLD` before HDR transfer | No clock stalling in HDR modes |
| HDR RX overflow | Ensure RX buffer has room before HDR read | DMA must be configured before transfer |

---

### SPI Controller Failures

**Common patterns in logs:**
```python
SPI_PATTERNS = [
    r'SPI.*Error',
    r'SPI.*Timeout',
    r'SPI.*Overflow',
    r'SPI.*Underrun',
    r'SPI.*FIFO',
    r'SPI.*Clock.*Error',
    r'SPI.*Mode.*Error',
    r'SPI.*CS.*Error',     # Chip Select
]
```

**Typical failure modes:**
- **FIFO Overflow/Underrun** — Data rate mismatch
- **Timeout** — Slave not responding
- **Clock Error** — Incorrect SPI clock frequency
- **CS Error** — Chip select timing issue

---

### UART Controller Failures

**Common patterns in logs:**
```python
UART_PATTERNS = [
    r'UART.*Error',
    r'UART.*Timeout',
    r'UART.*Overrun',
    r'UART.*Framing.*Error',
    r'UART.*Parity.*Error',
    r'UART.*Break.*Error',
    r'UART.*FIFO',
    r'UART.*Baud.*Rate',
    r'HSUART.*Error',      # NVL uses HSUART naming in PythonSV
    r'HSUART.*Timeout',
]
```

**Typical failure modes:**
- **Framing Error** — Stop bit not detected (baud rate mismatch)
- **Parity Error** — Data corruption
- **Overrun** — FIFO overflow (data not read fast enough)
- **Timeout** — No data received

**NVL-specific:** UARTs appear as `hsuart0`, `hsuart1`, `hsuart2` (High-Speed UART) in PythonSV.

---

### General LPSS Failures

**Common patterns in logs:**
```python
LPSS_GENERAL_PATTERNS = [
    r'LPSS.*Fail',
    r'SerialIO.*Error',
    r'PCI.*D3.*Fail.*LPSS',
    r'D3.*Entry.*Fail',
    r'Clock.*Gate.*Fail.*LPSS',
    r'LPSS.*Enumeration.*Fail',
    r'LPSS.*BAR.*Error',
]
```

**Typical failure modes:**
- **D3 Entry Failure** — Device unable to enter D3 power state
- **Clock Gating Failure** — Clocks not gating properly
- **Enumeration Failure** — Device not appearing on PCI bus
- **BAR Assignment Error** — Incorrect or missing base address register

---

## Using NGA Skills for Failure Analysis

### Step 1: Identify Failed Tests

Use the `nga/results` skill to query test execution results:

```python
from nga_api_utils import NgaAPIUtils

# Initialize NGA API
nga = NgaAPIUtils()

# Get failed tests from a test run
testrun_id = "12345"
failed_tests = nga.get_failed_tests(testrun_id)

# Filter for LPSS-related tests
lpss_failed = [
    test for test in failed_tests 
    if any(keyword in test['name'].lower() for keyword in LPSS_TEST_KEYWORDS)
]

for test in lpss_failed:
    print(f"Failed Test: {test['name']}")
    print(f"  Status: {test['status']}")
    print(f"  Step: {test['failed_step']}")
```

---

### Step 2: Retrieve Failure Logs

Use the `nga/failure` skill to get failure details and log paths:

```python
# Get failure details
failure_id = lpss_failed[0]['failure_id']
failure_info = nga.get_failure_by_id(failure_id)

# Extract log path
log_path = failure_info['log_path']
print(f"Log Path: {log_path}")

# Common LPSS log locations:
# - <LogsPath>/lpss/
# - <LogsPath>/serial_io/
# - <LogsPath>/i2c/
# - <LogsPath>/i3c/
# - <LogsPath>/spi/
# - <LogsPath>/uart/
```

---

### Step 3: Analyze Logs for LPSS Patterns

Scan logs for LPSS-specific error patterns:

```python
import re

# Read log file (actual log retrieval varies by NGA config)
log_content = read_log_file(log_path)

ALL_PATTERNS = I2C_PATTERNS + I3C_PATTERNS + SPI_PATTERNS + UART_PATTERNS + LPSS_GENERAL_PATTERNS

for pattern in ALL_PATTERNS:
    matches = re.findall(pattern, log_content, re.IGNORECASE)
    if matches:
        print(f"Pattern Match: {pattern}")
        print(f"  Matches: {matches}")
```

---

### Step 4: Cross-Reference with Sightings

Use the `sighting-info` and `hsdes` skills to check for known issues:

```python
# Check if failure is already linked to a sighting
if failure_info.get('sighting_id'):
    print(f"Linked Sighting: {failure_info['sighting_id']}")
    # Use sighting-info skill to get sighting details
else:
    # Search HSDES for similar failures
    # Use hsdes skill to query by keywords extracted from logs
    keywords = extract_keywords(log_content)  # Extract key error terms
    # Example: ["I2C", "Timeout", "NAK"]
```

---

### Step 5: Check Failure Bucket

Use the `nga/failure` skill to check if this failure is part of a known bucket:

```python
# Get failure bucket information
bucket_id = failure_info.get('bucket_id')
if bucket_id:
    bucket_info = nga.get_failure_bucket(bucket_id)
    print(f"Failure Bucket: {bucket_info['name']}")
    print(f"  Total Occurrences: {bucket_info['count']}")
    print(f"  Linked Sighting: {bucket_info.get('sighting_id')}")
```

---

## LPSS-Specific Debug Workflows

### I2C Failure Debug Flow

1. **Identify failure type** (Timeout, NAK, Arbitration Lost, etc.)
2. **Check I2C bus electrical health**
   - Use `fv-lpss/config-checkout` to verify pad configuration
   - Check pull-up resistors, signal integrity
3. **Verify I2C controller configuration**
   - Use `fv-lpss/config-checkout` for control registers
   - Check clock speed, timing parameters
4. **Check slave device status**
   - Is slave powered?
   - Is slave address correct?
5. **Review power state**
   - Use `fv-lpss/power-state` — was device in D3? Were clocks gated?

---

### SPI Failure Debug Flow

1. **Identify failure type** (Timeout, FIFO overflow, etc.)
2. **Check SPI configuration**
   - Clock polarity (CPOL) and phase (CPHA) settings
   - Chip select timing and polarity
3. **Verify pad configuration**
   - Use `fv-lpss/config-checkout` for MOSI/MISO/SCK/CS pads
4. **Check FIFO status**
   - Was FIFO overflow/underrun the root cause?
   - Check DMA configuration if used
5. **Review slave device**
   - Is slave responding?
   - Check slave data sheet timing requirements

---

### UART Failure Debug Flow

1. **Identify failure type** (Framing error, overrun, etc.)
2. **Verify baud rate**
   - Framing errors often indicate baud rate mismatch
3. **Check FIFO and flow control**
   - Overrun indicates data not consumed fast enough
   - Verify RTS/CTS flow control if used
4. **Verify pad configuration**
   - Use `fv-lpss/config-checkout` for TX/RX pads
5. **Check electrical connections**
   - TX/RX not swapped?
   - Ground connection good?

---

### D3 Entry Failure Debug Flow

1. **Check prerequisites for D3 entry**
   - Use `fv-lpss/power-state` — are clocks gated?
   - Are all transactions complete?
2. **Check PMCSR register**
   - Use `fv-lpss/power-state` to read power state
3. **Check for blockers**
   - Software override preventing D3?
   - Hardware condition preventing D3?
4. **Review recent activity**
   - Was device truly idle before D3 attempt?

---

## Triage Summary Template

When analyzing an LPSS failure, provide a structured summary:

```
**LPSS Failure Triage Summary**

Test: [Test Name]
Test Run ID: [ID]
Failure ID: [ID]
Platform: Novalake [PCH-S / PCD-H]

**Failure Classification:**
- Domain: [I2C / I3C / SPI / UART / General LPSS]
- Type: [Timeout / Error / Config Issue / Power State Issue]
- Port: [e.g., I2C0, UART2, I3C Ctrl#1]

**Log Analysis:**
- Pattern Matches: [List matching patterns]
- Key Error Messages: [Extract key lines from log]

**Known Issue Check:**
- Sighting Linked: [Yes/No - ID if yes]
- Failure Bucket: [ID and occurrence count if exists]

**Recommended Next Steps:**
1. [First debug step based on failure type]
2. [Second debug step]
3. [Consider delegation to specific fv-lpss sub-skill]

**Skills to Use:**
- [List relevant fv-lpss sub-skills]
```

---

## Examples

### Example 1: I2C Timeout Failure on NVL PCD-H

```python
# Scenario: Test "LPSS_I2C_Transaction_Test" failed with timeout on I2C0

# Step 1: Get failure details
failure_info = nga.get_failure_by_id(failure_id)
# Result: Failed step = "i2c_transfer", log shows "I2C Timeout on bus 0"

# Step 2: Check enumeration first
# I2C0 on PCD-H: B:0 D:21 F:0, DID=0xD378
# Use fv-lpss/config-checkout to confirm device present

# Step 3: Check for known issue
# Search sighting-info for "I2C timeout Novalake"

# Step 4: Recommended debug
# - Use fv-lpss/config-checkout to verify I2C0 pad config + control registers
#   Path: namednodes.sv.socket0.pcd.lpss.i2c0.cfg
# - Check if slave device is present and powered
```

### Example 2: D3 Entry Failure on NVL PCH-S

```python
# Scenario: Test "LPSS_D3_Entry_Test" failed for UART1

# Step 1: Get failure details
# Result: Failed step = "verify_d3_entry", log shows "PCI D3 Entry Fail LPSS UART1"

# Step 2: UART1 on PCH-S: B:0 D:30 F:1, DID=0x6E29
# Fabric: pf_top_7

# Step 3: Recommended debug
# - Use fv-lpss/power-state to verify D3 state and clock gating (pf_top_7)
#   Path: namednodes.sv.socket0.pch.lpss.hsuart1.cfg
# - Check for active transactions blocking D3 entry
```

---

## Related Skills

- **`nga/results`** — Query test execution results
- **`nga/failure`** — Get failure details and buckets
- **`sighting-info`** — Look up sighting information
- **`hsdes`** — Query HSDES for bugs and test cases
- **`fv-lpss/config-checkout`** — Verify IP enumeration, registers, and pad configuration
- **`fv-lpss/power-state`** — Check D3 power states and clock gating

---

## IOAPIC Interrupt Delivery Failure Patterns (HSDES 14023171649)

> **Context:** Race condition between GPIO `DEASSERT_IRQ` (opcode 0x55) and ITSS `MSI_CMPL` causes IOAPIC RTE entries to become permanently stuck, resulting in GPIO-connected peripherals (touchpads, clickpads, sensors) losing interrupt delivery. Originally reported on LNL-MX but affects any platform with the same ITSS architecture (NVL, PTL, TTL).
>
> **Full report:** [HSDES 14023171649 HTML Report](https://htmlpreview.github.io/?https://github.com/KongJiaWen/applications.ai.ocode.market.skills/blob/hsdes-14023171649-report/HSDES_14023171649_IOAPIC_Report.html)

### IOAPIC Failure Signature

**Definitive stuck condition (read via IOAPIC MMIO or ITSS internal registers):**
```
RTE_DS[N] == 1  AND  RTE_Rirr[N] == 1  AND  RTE_Mask[N] == 0
```
While the GPIO line is deasserted (`gpiorxstate=0` in `PAD_CFG_DW0`).

This means:
- `RTE_DS=1`: ITSS delivery status still pending (MSI never completed)
- `RTE_Rirr=1`: Remote IRR still set (EOI never received because MSI was stuck)
- `RTE_Mask=0`: The IRQ is NOT masked, so this is a true stuck condition
- No further interrupts will be delivered on IRQ N until reboot or manual recovery

### Log Patterns for IOAPIC Race Condition

```python
IOAPIC_RACE_PATTERNS = [
    r'GPIO.*interrupt.*lost',
    r'clickpad.*lost.*function',
    r'touchpad.*not.*responding.*reboot',
    r'IOAPIC.*RTE.*stuck',
    r'RTE_DS.*1.*RTE_Rirr.*1',
    r'DEASSERT_IRQ.*before.*MSI_CMPL',
    r'GPI_IS.*clear.*race',
    r'interrupt.*delivery.*failed.*GPIO',
    r'ITSS.*CurrentState.*stuck',
    r'gpio.*int.*mode.*lost',
]
```

### IOAPIC Failure Classification

| Failure Type | Signature | Root Cause | Recovery |
|-------------|-----------|------------|----------|
| **RTE Stuck (race)** | ds=1, rirr=1, msk=0, GPIO deasserted | DEASSERT_IRQ arrived before MSI_CMPL | EOI write to 0xFEC00040, or reboot |
| **RTE Stuck (OS bug)** | Upper 32 bits written before lower 32 bits | Windows OS writes RTE_High before RTE_Low (HSD 22019075886) | Patch OS driver, rewrite RTE atomically |
| **Spurious mask** | msk=1, no SW masked | S0i2.2 transition glitched pad (iosstate≠0xF) | Set iosstate=0xF, unmask RTE |
| **Wrong trigger mode** | tm=0 (edge) for GPIO | BIOS misconfigured, GPIO needs level-triggered | Set tm=1 in RTE |

### Diagnostic Script for IOAPIC Failures

```python
def diagnose_ioapic_gpio_failure(irq_num, gpio_pad_dw0_path, gpio_pad_dw1_path):
    """Full diagnostic for GPIO interrupt delivery failure (HSDES 14023171649).
    
    Args:
        irq_num: IOAPIC IRQ number (e.g., 14 for GPP community)
        gpio_pad_dw0_path: PythonSV path to PAD_CFG_DW0 for the affected pad
        gpio_pad_dw1_path: PythonSV path to PAD_CFG_DW1 for the affected pad
    """
    import namednodes as nn
    nn.sv.refresh()
    
    print("=== IOAPIC GPIO Interrupt Diagnostic (HSDES 14023171649) ===")
    print("IRQ: %d\n" % irq_num)
    
    # 1. Read IOAPIC RTE
    ioapic_base = 0xFEC00000
    ioregsel = ioapic_base + 0x00
    iowin    = ioapic_base + 0x10
    
    nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq_num, 4)
    rte_low = nn.sv.socket0.pcd.io.mem.read(iowin, 4)
    nn.sv.socket0.pcd.io.mem.write(ioregsel, 0x10 + 2 * irq_num + 1, 4)
    rte_high = nn.sv.socket0.pcd.io.mem.read(iowin, 4)
    
    msk  = (rte_low >> 16) & 1
    tm   = (rte_low >> 15) & 1
    rirr = (rte_low >> 14) & 1
    ds   = (rte_low >> 12) & 1
    vct  = rte_low & 0xFF
    
    print("1. IOAPIC RTE[%d]:" % irq_num)
    print("   Low=0x%08X High=0x%08X" % (rte_low, rte_high))
    print("   msk=%d tm=%d rirr=%d ds=%d vct=0x%02X" % (msk, tm, rirr, ds, vct))
    
    is_stuck = (ds == 1 and rirr == 1 and msk == 0)
    if is_stuck:
        print("   >>> STUCK! IOAPIC race condition confirmed")
    
    # 2. Read GPIO pad config
    pad_dw0 = eval(gpio_pad_dw0_path).read()
    pad_dw1 = eval(gpio_pad_dw1_path).read()
    
    rxevcfg        = (pad_dw0 >> 25) & 0x3
    gpiroutioxapic = (pad_dw0 >> 20) & 0x1
    gpiorxstate    = pad_dw0 & 0x1
    pmode          = (pad_dw0 >> 10) & 0xF
    iosstate       = (pad_dw1 >> 14) & 0xF
    intsel         = pad_dw1 & 0xFF
    
    print("\n2. GPIO Pad Config:")
    print("   DW0=0x%08X DW1=0x%08X" % (pad_dw0, pad_dw1))
    print("   rxevcfg=%d gpiroutioxapic=%d gpiorxstate=%d pmode=%d" 
          % (rxevcfg, gpiroutioxapic, gpiorxstate, pmode))
    print("   iosstate=0x%X intsel=%d" % (iosstate, intsel))
    
    # 3. Vulnerability assessment
    print("\n3. Vulnerability Assessment:")
    vulns = []
    if rxevcfg == 0x0:
        vulns.append("rxevcfg=0x0 (level-triggered, vulnerable to race)")
    if iosstate != 0xF:
        vulns.append("iosstate=0x%X (should be 0xF, S0i2.2 glitch risk)" % iosstate)
    if gpiroutioxapic == 0:
        vulns.append("GPIO interrupt mode (not IOAPIC direct, wider race window)")
    if tm == 0:
        vulns.append("Edge-triggered RTE (should be level for GPIO)")
    
    if vulns:
        for v in vulns:
            print("   WARNING: %s" % v)
    else:
        print("   OK: Pad configuration looks correct")
    
    # 4. Summary
    print("\n4. Summary:")
    if is_stuck:
        print("   DIAGNOSIS: IOAPIC RTE STUCK — HSDES 14023171649 race condition")
        print("   RECOVERY: Write EOI to 0xFEC00040, or toggle RTE mask, or reboot")
        print("   PREVENTION: Set rxevcfg=0x2 during BIOS, iosstate=0xF, gpiroutioxapic=1")
    elif vulns:
        print("   DIAGNOSIS: Pad configuration is VULNERABLE to race condition")
        print("   ACTION: Apply BIOS mitigations before production")
    else:
        print("   DIAGNOSIS: No IOAPIC race condition detected")
    
    return is_stuck, vulns
```

### IOAPIC Failure Triage in NGA

When triaging NGA test failures that match IOAPIC race condition patterns:

1. **Check test name and log** — look for `IOAPIC_RACE_PATTERNS` matches above
2. **Identify affected IRQ** — from log messages or `MISCCFG.gpdmintsel` value
3. **Run diagnostic script** — `diagnose_ioapic_gpio_failure(irq_num, dw0_path, dw1_path)`
4. **Cross-reference sightings:**
   - HSDES 14023171649 — GPIO/ITSS race condition (LNL-MX, P1-Showstopper, Root-Caused)
   - HSDES 22019075886 — Windows OS IOAPIC RTE write ordering bug
5. **Check BIOS mitigations** — verify `rxevcfg`, `iosstate`, `gpiroutioxapic` settings
6. **File new sighting** if failure occurs on a platform not yet tracked (NVL, PTL, TTL)

### Triage Summary Template — IOAPIC Race Condition

```
**LPSS/GPIO Interrupt Failure Triage Summary**

Test: [Test Name]
Test Run ID: [ID]
Platform: [NVL PCD-H / NVL PCH-S / PTL / TTL]
IRQ Number: [N]

**IOAPIC RTE State:**
- RTE_Low: 0x[value]  RTE_High: 0x[value]
- ds=[0/1]  rirr=[0/1]  msk=[0/1]  tm=[0/1]  vct=0x[XX]

**GPIO Pad State:**
- PAD_CFG_DW0: 0x[value]  PAD_CFG_DW1: 0x[value]
- rxevcfg=[0-3]  gpiroutioxapic=[0/1]  iosstate=0x[X]  pmode=[0-F]

**Diagnosis:**
- [ ] RTE stuck (ds=1 AND rirr=1) → Confirmed HSDES 14023171649
- [ ] Pad vulnerable (rxevcfg≠0x2 or iosstate≠0xF)
- [ ] OS write ordering bug → Confirmed HSDES 22019075886
- [ ] Other root cause: [describe]

**Mitigations Applied:**
- [ ] BIOS: rxevcfg=0x2 during init
- [ ] BIOS: iosstate=0xF on interrupt pads
- [ ] OS: gpiroutioxapic=1 (IOAPIC direct mode)
- [ ] OS: GPI_IS clear ordering fix

**Cross-References:**
- HSDES 14023171649 (GPIO/ITSS race, LNL-MX)
- HSDES 22019075886 (Windows IOAPIC RTE ordering)
- docs/lpss_known_issues.md → HSDES-004
- debug/SKILL.md → Playbook 6
- config-checkout/SKILL.md → Part 4 (GPIO Interrupt Pad Checks)
```
