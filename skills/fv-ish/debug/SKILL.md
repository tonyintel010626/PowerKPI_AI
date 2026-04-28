# FV-ISH Debug & Triage Skill

**Skill**: `fv-ish/debug`
**Domain**: ISH Functional Validation — Debug Flows, Triage Procedures, Failure Signatures
**Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
**Primary Platform**: NVL (Nova Lake) — others: MTL, LNL, PTL, ARL, TTL
**Last Updated**: 2026-03-16

---

## CRITICAL REMINDER

> Before concluding a root cause, **always verify register values, protocol behavior, and power state definitions against the ISH IP HAS**.
> Load `fv-ish/has` skill to query local HAS docs or Co-De Sign.
> Do NOT fabricate root causes or workarounds — if uncertain, say so and escalate.

---

## ISH Triage Decision Tree

Use this top-down flow to systematically narrow ISH failures. Start from Level 1 and proceed until root cause is identified.

```
Level 1: Does ISH enumerate on PCI bus?
  ├─ NO  → [L1-FAIL] PCI/BIOS issue — see Section: PCI Enumeration Failures
  └─ YES → proceed to Level 2

Level 2: Does ISH firmware boot successfully?
  ├─ NO  → [L2-FAIL] Firmware boot failure — see Section: Firmware Boot Failures
  └─ YES → proceed to Level 3

Level 3: Does IPC/HECI connection establish?
  ├─ NO  → [L3-FAIL] IPC transport failure — see Section: IPC/HECI Failures
  └─ YES → proceed to Level 4

Level 4: Do sensors enumerate via ISHTP?
  ├─ NO  → [L4-FAIL] Sensor enumeration failure — see Section: Sensor Failures
  └─ YES → proceed to Level 5

Level 5: Is sensor data valid and within expected range?
  ├─ NO  → [L5-FAIL] Data path failure — see Section: Sensor Data Failures
  └─ YES → proceed to Level 6

Level 6: Does ISH power management work correctly?
  ├─ NO  → [L6-FAIL] Power management failure — see Section: Power Management Failures
  └─ YES → proceed to Level 7

Level 7: Does ISH DMA data transfer work correctly?
  ├─ NO  → [L7-FAIL] DMA failure — see Section: DMA Failures
  └─ YES → ISH appears functional — check test script/environment issues
```

---

## Section: PCI Enumeration Failures [L1-FAIL]

### Symptoms
- ISH device not visible in `lspci` / Device Manager
- PCI Device ID not matching expected value
- BAR0 not programmed / zero value

### TTL PCI Device ID Reference

| Platform | Vendor ID | Device ID | ISH Generation |
|----------|-----------|-----------|----------------|
| **TTL**  | `0x8086`  | `0xE445`  | ISH 5.9        |
| NVL      | `0x8086`  | `0x6E78`  | ISH 5.8        |

### Immediate Debug Steps

**Linux:**
```bash
# Check if ISH PCI device is present
lspci -nn | grep -i "Intel.*ISH\|8086:e445"

# Check ISH device details (TTL)
lspci -vvv -d 8086:e445

# Check BAR0 mapping
lspci -s [BDF] -vvv | grep "Memory at"

# Check if driver is loaded
lsmod | grep intel_ish
dmesg | grep -i ish | tail -50
```

**Windows:**
```powershell
# Check in Device Manager
devcon status *8086*

# Check via PnP
pnputil /enum-devices /class "Sensor"
```

**PythonSV:**
```python
# Verify PCI enumeration
sv.socket0.uncore.pci_device_list  # check for ISH BDF

# TTL: Read PCI Vendor/Device ID directly
ish = sv.socket0.pch.ish
vid = ish.cfg.vid.read()    # Expect 0x8086
did = ish.cfg.did.read()    # Expect 0xE445 for TTL
print(f"Vendor ID: 0x{vid:04X}, Device ID: 0x{did:04X}")
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| ISH disabled in BIOS | Check BIOS ISH enable knob | Enable ISH in BIOS setup |
| Wrong BIOS image | Check BIOS version | Flash correct BIOS with ISH support |
| ISH power rail not enabled | Measure ISH VCC rail | Check PMC configuration |
| ACPI table missing ISH entry | Dump ACPI tables (`acpidump`) | Update BIOS/ACPI |
| Platform not supported | Verify Device ID vs HAS | Check platform stepping support |
| PCH strap misconfiguration | Check strap values | Contact ISH IP team |

### TTL-Specific Notes
- **TTL PCI Device ID**: `0xE445`, Vendor ID: `0x8086`
- **TTL ISH Generation**: ISH 5.9 with LMT 3.8/3.9 (MinuteIA) core
- **Power Domain**: VNNAON (always-on), Reset Domain: FUNCRST
- **PCI Class**: `0x118000` (Signal Processing Controller)
- **TTL ISH BIOS prerequisite**: ISH must be enabled under PCH Configuration → ISH Configuration

---

## Section: Firmware Boot Failures [L2-FAIL]

### Symptoms
- ISH PCI device enumerated but firmware status register shows error
- IPC connection attempt fails immediately
- dmesg shows "ISH: firmware not ready" or similar

### Key Register: ISH Firmware Status (FWSTS)

The FWSTS register is located at offset `0x34` within each IPC channel block. The HOST IPC channel FWSTS is the primary one to check.

**HOST IPC FWSTS**: BAR0 + `0x034` (NVL uses the same offset)

```python
# PythonSV: Read ISH FW Status Register (NVL/TTL)
ish = sv.socket0.pch.ish
fw_status = ish.mem.read(0x034)  # HOST IPC FWSTS (offset same for NVL)
print(f"FW Status: 0x{fw_status:08X}")

# Decode key fields (verify bit definitions against HAS):
fw_init = (fw_status >> 0) & 0x1   # FW_INIT_COMPLETE
fw_error = (fw_status >> 2) & 0x1  # FW_ERROR
fw_state = (fw_status >> 4) & 0xF  # FW_STATE
print(f"  FW Init Complete: {fw_init}")
print(f"  FW Error: {fw_error}")
print(f"  FW State: 0x{fw_state:X}")
```

### Firmware State Decoding

| FW_STATE Value | Meaning | Action |
|---------------|---------|--------|
| `0x0` | Reset / Not started | Check power rails, ISH reset |
| `0x1` | ROM running (Boot ROM) | Wait — CSE loading BUP (64KB max) |
| `0x2` | BUP running | Wait — Host loading Main FW (1.5MB max) |
| `0x3` | Main FW running | Normal — proceed to IPC check |
| `0x4` | Firmware error / panic | Capture FW panic dump (see below) |
| `0xF` | Fatal error | ISH reset required |

### TTL Firmware Boot Flow Reference

```
Power-On → Boot ROM (8KB ROM)
    ↓
CSE loads BUP firmware (Intel-signed, 64KB max)
    ↓
BUP initializes ISH core, SRAM (640KB = 20×32KB banks)
    ↓
Host driver loads Main FW (1.5MB max) via IPC/IMR
    ↓
Main FW starts — sensors initialize, IPC HOST channel ready
```

**S3 Resume Optimization (TTL)**:
- CSE saves uncompressed ISH main FW in IMR before S3 entry
- On resume: CSE does hash comparison, skips re-download if hash matches
- Result: significantly faster ISH resume from S3

### Watchdog Timer Debug (TTL)

If firmware hangs during boot, the WDT may trigger:

| Register | Offset (MIA) | Description |
|----------|-------------|-------------|
| `WDTC`   | `0x04900000` | Control: [17]=Enable, [15:8]=T2 timeout, [7:0]=T1 timeout, default=`0xA0A0` |
| `WDTR`   | `0x04900004` | Restart (write to kick watchdog) |
| `WDTV`   | `0x04900008` | Current value (countdown) |

- **Two-stage watchdog**: T1 timeout → interrupt (FW can recover), T2 timeout → hard reset
- Default `0xA0A0`: T1=160 ticks, T2=160 ticks

### Firmware Panic Dump

```bash
# Linux: ISH firmware trace buffer
cat /sys/kernel/debug/intel-ishtp/dump  # if debugfs is mounted
dmesg | grep -i "ish.*panic\|ish.*crash\|ish.*error"

# Windows: Check WPP trace logs
# Enable ISH driver tracing via registry:
# HKLM\SYSTEM\CurrentControlSet\Services\IntelIshHid\Parameters
# Add "VerboseOn" = DWORD 1
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| ISH FW binary missing/corrupt | FWSTS stuck at 0x0/0x1 | Re-flash correct BIOS |
| BUP signature verification failure | CSE error log, stuck at state 0x1 | Flash BIOS with valid BUP |
| Main FW too large for IMR | FW > 1.5MB, load failure | Reduce FW size or increase IMR allocation |
| ISH clock not enabled | Check CCU TRUNK_CG register | PMC configuration issue |
| ISH SRAM initialization failure | PMU SRAM_PG_EN stuck | Check SRAM power gating |
| Watchdog timeout during FW load | WDT reset in CCU RST_HIS | Check FW load timeout settings |
| S3 resume hash mismatch | Slow resume (full FW reload) | Check IMR contents, CSE logs |

---

## Section: IPC/HECI Failures [L3-FAIL]

### Symptoms
- `intel-ishtp` driver loaded but no IPC clients appear
- IPC doorbell timeout in driver logs
- No sensor devices appear after ISH firmware boot

### TTL IPC Architecture

ISH uses **IPC doorbell/mailbox** protocol (NOT circular buffers). Each IPC channel has dedicated doorbell and 32×32-bit message registers.

**8 IPC Channels:**

| Channel | HOST Wrapper Offset | Type | Purpose |
|---------|-------------------|------|---------|
| HOST       | `0x000`  | MEM  | Primary host communication |
| HOSTSPARE  | `0x000`  | MEM  | Spare host channel |
| CSE        | `0x1000` | MSG  | CSME communication |
| PMC        | `0x2000` | MSG  | Power Management Controller |
| CNVi       | `0x3000` | MSG  | Connectivity (WiFi/BT) |
| ACE        | `0x4000` | MSG  | Audio DSP |
| ESE        | `0x5000` | MSG  | Embedded Security Engine |
| AVB        | `0x6000` | MSG  | Audio/Video Bridging |

### Key IPC Debug Registers (per channel)

| Register | Offset | Description |
|----------|--------|-------------|
| `PISR`           | `+0x00`  | Peripheral Interrupt Status |
| `PIMR`           | `+0x04`  | Peripheral Interrupt Mask |
| `FWSTS`          | `+0x34`  | Firmware Status |
| `INBOUND_DB`     | `+0x48`  | Inbound Doorbell: [31]=BUSY |
| `OUTBOUND_DB`    | `+0x54`  | Outbound Doorbell: [31]=BUSY |
| `OUT_MSG[0-31]`  | `+0x60`  | Outbound message payload (128 bytes) |
| `IN_MSG[0-31]`   | `+0xE0`  | Inbound message payload (128 bytes) |
| `BUSY_CLEAR`     | `+0x378` | Doorbell busy clear |
| `D0I3C`          | `+0x6D0` | D0i3 Control: [2]=D0i3 enable |

### Debug Steps

```bash
# Linux: Check ISHTP clients
ls /sys/bus/ishtp/devices/

# Check IPC doorbell state via driver logs
echo 8 > /proc/sys/kernel/printk
modprobe -r intel_ish_ipc intel-ishtp intel-ishtp-hid
modprobe intel_ish_ipc
dmesg | grep -i "ish\|ishtp\|ipc\|doorbell" | tail -100
```

```python
# PythonSV: Dump IPC HOST channel registers (TTL)
ish = sv.socket0.pch.ish
base = 0x000  # HOST IPC channel

pisr       = ish.mem.read(base + 0x00)
pimr       = ish.mem.read(base + 0x04)
fwsts      = ish.mem.read(base + 0x34)
inbound_db = ish.mem.read(base + 0x48)
outbound_db= ish.mem.read(base + 0x54)
d0i3c      = ish.mem.read(base + 0x6D0)

print(f"PISR:        0x{pisr:08X}")
print(f"PIMR:        0x{pimr:08X}")
print(f"FWSTS:       0x{fwsts:08X}")
print(f"INBOUND_DB:  0x{inbound_db:08X}  BUSY={inbound_db >> 31}")
print(f"OUTBOUND_DB: 0x{outbound_db:08X}  BUSY={outbound_db >> 31}")
print(f"D0I3C:       0x{d0i3c:08X}  D0i3={(d0i3c >> 2) & 1}")
```

### Doorbell Protocol Debug

```
Normal IPC message exchange:
  1. Sender writes payload to OUT_MSG[0-31] registers
  2. Sender sets OUTBOUND_DB[31] = 1 (BUSY)
  3. Level-sensitive interrupt asserted to receiver while BUSY=1
  4. Receiver reads payload from IN_MSG[0-31]
  5. Receiver clears BUSY via BUSY_CLEAR register
  6. Interrupt deasserts

Failure modes:
  - BUSY stuck at 1: Receiver not clearing doorbell → FW hang or driver bug
  - BUSY never set: Sender not initiating → check FW state or driver init
  - Payload corrupt: Message registers have unexpected values → DMA/bus error
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| ISH FW not ready for IPC | FWSTS state ≠ 0x3 | Wait for FW boot to complete |
| Doorbell stuck BUSY | INBOUND_DB[31]=1 persistent | FW not clearing doorbell — FW bug or hang |
| Host driver not sending doorbell | OUTBOUND_DB[31] never set | Driver initialization bug |
| IPC timeout | Driver log shows timeout | Check FW IPC handler, increase timeout |
| Wrong client GUID | Client enumeration fails | Verify FW ISHTP client GUIDs vs driver |
| Interrupt not reaching host | PISR=0 despite doorbell | Check interrupt routing, PIMR mask |
| D0i3 blocking IPC | D0I3C[2]=1 during IPC attempt | Clear D0i3 before sending message |

---

## Section: Sensor Enumeration Failures [L4-FAIL]

### Symptoms
- IPC works but no HID sensor devices appear in OS
- `/sys/bus/hid/devices/` shows no ISH sensor entries (Linux)
- Windows Device Manager shows no sensor devices under ISH

### TTL Sensor Bus Configuration

| Bus | MIA Base Address | Instances | Max Speed | Typical Sensors |
|-----|-----------------|-----------|-----------|-----------------|
| I2C | `0x00000000` | 3 (0x2000 stride) | 1 Mb/s | Accel, Gyro, Mag |
| I3C | `0x04800000` | 2 (0x2000 stride) | 25 Mb/s HDR-DDR | Next-gen sensors |
| SPI | `0x08000000` | 2 instances | 25 Mb/s | High-rate sensors |
| UART| `0x08100000` | 3 (0x2000 stride) | 4 Mb/s | Debug, custom sensors |
| GPIO| `0x00100000` | 1 (up to 12 pins) | N/A | Interrupts, wake |

### Debug Steps

```bash
# Linux: Check HID sensor devices
ls /sys/bus/hid/devices/ | grep -i ish
cat /sys/bus/hid/devices/*/name

# Check ISHTP HID client
ls /sys/bus/ishtp/devices/
dmesg | grep -i "sensor\|hid.*ish\|ish.*hid" | tail -50

# Verify report descriptor loading
cat /sys/kernel/debug/hid/*/rdesc 2>/dev/null | head -100
```

```python
# PythonSV: Check sensor I2C bus status (TTL)
ish = sv.socket0.pch.ish
# I2C0 status register (DW_apb_i2c)
i2c0_status = ish.mem.read(0x00000070)  # IC_STATUS offset 0x70
i2c0_enable = ish.mem.read(0x0000006C)  # IC_ENABLE offset 0x6C
print(f"I2C0 Status: 0x{i2c0_status:08X}")
print(f"I2C0 Enable: 0x{i2c0_enable:08X}")

# GPIO status for sensor interrupts
gpio_level = ish.mem.read(0x00100000)  # GPLR
gpio_irq   = ish.mem.read(0x00100020)  # GISR
print(f"GPIO Level: 0x{gpio_level:08X}")
print(f"GPIO IRQ:   0x{gpio_irq:08X}")
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| Sensor not physically present | Check BOM; probe sensor I2C address | Verify hardware BOM |
| Sensor I2C address conflict | I2C bus scan, check ACK | Check platform I2C routing |
| ISH FW sensor config missing | FW missing sensor BOM config | Flash FW with correct BOM config |
| Report descriptor invalid | HID parser error in dmesg | Fix descriptor in FW |
| ACPI ISH node missing | Check ACPI tables | Update BIOS ACPI tables |
| Driver GUID mismatch | ISHTP client not matched | Verify GUID in FW and driver |
| I2C clock gating blocking bus | Check CCU I2C CG reg (0x0430000C) | Ensure clock enabled |
| GPIO interrupt not configured | Check GRER/GFER for edge detect | Configure GPIO rising/falling edge |

---

## Section: Sensor Data Failures [L5-FAIL]

### Symptoms
- Sensors enumerate but data values are wrong (stuck, out-of-range, NaN)
- Accelerometer reports gravity in wrong axis
- Gyroscope drifts when stationary
- ALS reports 0 lux always

### Debug Steps

```bash
# Linux: Read sensor data
cat /sys/bus/iio/devices/iio:device*/in_accel_x_raw
cat /sys/bus/iio/devices/iio:device*/in_anglvel_z_raw
cat /sys/bus/iio/devices/iio:device*/in_illuminance_raw

# Monitor sensor events
evtest /dev/input/eventX   # find ISH sensor input device
```

### Sensor Data Sanity Checks

| Sensor | Expected at Rest | Out-of-Range Threshold |
|--------|-----------------|----------------------|
| Accelerometer | ~1g on vertical axis, ~0g on others | > 2g on any axis at rest |
| Gyroscope | ~0 rad/s on all axes | > 0.1 rad/s drift at rest |
| Magnetometer | Local magnetic field (~25-65 µT) | < 10 µT or > 100 µT |
| ALS | Ambient light (varies) | 0 lux in lit room |
| Proximity | Far (1) when no obstruction | Near (0) when no object |

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| Sensor mounted in wrong orientation | Check physical layout vs firmware config | Update orientation matrix in FW |
| Missing/wrong calibration data | Factory cal data = 0 or missing | Load factory calibration |
| Sensor I2C communication errors | Check I2C error counters | Debug I2C signal integrity |
| Data scale/unit wrong | Compare raw vs scaled value | Fix scale factor in FW or driver |
| Report descriptor units wrong | HID usage table mismatch | Fix descriptor units |
| SRAM ECC error corrupting data | Check SRAM_INTR_STS (0x10500004) | Check ECC logging, may be HW issue |

---

## Section: Power Management Failures [L6-FAIL]

### Symptoms
- ISH blocks S0ix entry
- System wakes unexpectedly from sensor events
- Sensor data stops after system resumes from sleep
- ISH D-state transitions fail

### TTL Power Debug Registers

| Register | Address | Key Fields |
|----------|---------|------------|
| `D0I3C` (HOST IPC) | BAR0+`0x6D0` | [2]=D0i3 enable, [3]=RR (restore required), [0]=CIP |
| `PMU SRAM_PG_EN` | MIA `0x04200000` | 30-bit mask, each bit gates one SRAM bank/tile |
| `PMU WAKE_EVENT` | MIA `0x0420000C` | Wake source status — see bit map below |
| `PMU MASK_EVENT` | MIA `0x04200010` | Wake source mask |
| `PMU VNN_REQ` | MIA `0x0420003C` | Voltage rail request (32 bits) |
| `PMU VNN_REQ_ACK` | MIA `0x04200040` | Voltage rail acknowledgment |
| `CCU TRUNK_CG` | MIA `0x04300000` | Trunk clock gating control |
| `CCU RST_HIS` | MIA `0x0430003C` | Reset history (shows last reset cause) |

### TTL Wake Event Sources (PMU WAKE_EVENT bits 16-31)

| Bit | Source | Description |
|-----|--------|-------------|
| 16 | VNN_ACK | Voltage rail acknowledgment |
| 17 | D0i3 | D0i3 state transition |
| 18 | SPI | SPI controller event |
| 19 | I2C | I2C controller event |
| 20 | DMA | DMA completion or error |
| 21 | UART | UART receive event |
| 22-27 | IPC[0-5] | IPC channel doorbell events |
| 28 | HPET_TMR | HPET timer expiration |
| 29-31 | Reserved | — |

### Debug Steps

```bash
# Linux: Check S0ix residency
cat /sys/kernel/debug/pmc_core/slp_s0_residency_usec

# Check ISH runtime PM status
cat /sys/bus/pci/devices/0000:[ISH_BDF]/power/runtime_status
cat /sys/bus/pci/devices/0000:[ISH_BDF]/power/runtime_active_time

# Force runtime suspend for testing
echo auto > /sys/bus/pci/devices/0000:[ISH_BDF]/power/control
echo 0 > /sys/bus/pci/devices/0000:[ISH_BDF]/power/autosuspend_delay_ms
```

```python
# PythonSV: Full power state dump (TTL)
ish = sv.socket0.pch.ish

# PCI PM state
pmcsr = ish.cfg.pmcsr.read()
d_state = pmcsr & 0x3
print(f"ISH D-state: D{d_state}")

# IPC D0i3 state
d0i3c = ish.mem.read(0x6D0)
print(f"D0I3C: 0x{d0i3c:08X}  D0i3={(d0i3c >> 2) & 1}  RR={(d0i3c >> 3) & 1}")

    # PMU registers (MIA internal — may need special access path)
    # SRAM power gating
    sram_pg = ish.mem.read(0x04200000)  # PMU_SRAM_PG_EN
    wake_evt = ish.mem.read(0x0420000C)  # PMU WAKE_EVENT (NVL: 0x0420000C)
    mask_evt = ish.mem.read(0x04200010)  # MASK_EVENT
    vnn_req  = ish.mem.read(0x0420003C)  # VNN_REQ
    rst_his  = ish.mem.read(0x0430003C)  # CCU RST_HIS

    print(f"SRAM_PG_EN: 0x{sram_pg:08X} ({bin(sram_pg).count('1')} banks gated)")
    print(f"WAKE_EVENT: 0x{wake_evt:08X} (PMU WAKE_EVENT @ 0x0420000C)")
    print(f"MASK_EVENT: 0x{mask_evt:08X}")
    print(f"VNN_REQ:    0x{vnn_req:08X}")
    print(f"RST_HIS:    0x{rst_his:08X}")
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| ISH runtime PM disabled | runtime_status = "active" always | Enable runtime PM in driver |
| IPC connection keeping ISH awake | INBOUND_DB[31]=1 persistent | Close idle IPC connections |
| Sensor polling preventing D-state | D0I3C[2] never set | Use interrupt mode, not polling |
| SRAM banks not power gated | SRAM_PG_EN = 0x00000000 | FW not enabling SRAM gating |
| Spurious wake events | WAKE_EVENT has unexpected bits | Check MASK_EVENT configuration |
| VNN rail stuck requested | VNN_REQ ≠ 0 when idle | FW not releasing VNN |
| ISH blocking S0ix | PMC LPM latch shows ISH | Check D0I3C, ensure D0i3 entry |

### Resume After Sleep Failures

```bash
# Linux: Check ISH driver resume
dmesg | grep -i "ish.*resume\|ish.*suspend" | tail -20

# TTL S3 resume: check if FW hash comparison succeeded
# (Fast path = hash match, slow path = full FW reload)
dmesg | grep -i "ish.*fw.*load\|ish.*hash\|ish.*imr" | tail -10
```

---

## Section: DMA Failures [L7-FAIL]

### Symptoms
- High-rate sensor data drops/corrupts
- DMA timeout errors in driver logs
- System hang during sustained sensor streaming

### TTL DMA Debug Registers

| Register | MIA Address | Key Fields |
|----------|-------------|------------|
| `DMA_CTL_CH0` | `0x10101000` | [10]=LLI_MODE, [9]=WR_NOSNOOP, [8]=RD_NOSNOOP, [6:5]=WR_RS, [4:3]=RD_RS, [1:0]=XFER_MODE |
| `DMA_CTL_CH1` | `0x10101004` | Same bit fields |
| `DMA_CTL_CH2-CH7` | `0x10101008-0x1010101C` | Same bit fields, 8 channels total |

**Transfer Modes** ([1:0]):
- `00` = Internal→Internal
- `01` = Internal→External (ISH SRAM → Host DRAM)
- `10` = External→Internal (Host DRAM → ISH SRAM)
- `11` = External→External

**Root Space** ([4:3] RD_RS, [6:5] WR_RS):
- `00` = RS0 (Host DRAM, visible to OS)
- `11` = RS3 (IMR DRAM, secure region)

### Debug Steps

```bash
# Linux: Check DMA error counters
cat /sys/kernel/debug/intel-ishtp/dma_stats 2>/dev/null

# Check for DMA-related kernel errors
dmesg | grep -i "ish.*dma\|dma.*ish\|iommu.*ish" | tail -30
```

```python
# PythonSV: Check DMA channel status (TTL)
ish = sv.socket0.pch.ish
for ch in range(8):
    ctl = ish.mem.read(0x10101000 + ch * 4)
    xfer_mode = ctl & 0x3
    rd_rs = (ctl >> 3) & 0x3
    wr_rs = (ctl >> 5) & 0x3
    lli = (ctl >> 10) & 0x1
    modes = {0: "Int→Int", 1: "Int→Ext", 2: "Ext→Int", 3: "Ext→Ext"}
    print(f"CH{ch}: CTL=0x{ctl:08X} Mode={modes[xfer_mode]} RD_RS={rd_rs} WR_RS={wr_rs} LLI={lli}")
```

### Root Causes & Fixes

| Root Cause | How to Confirm | Fix |
|------------|---------------|-----|
| Wrong transfer mode | DMA_CTL XFER_MODE incorrect for direction | Set correct mode (01=ISH→Host, 10=Host→ISH) |
| Wrong root space | Data going to IMR instead of host DRAM | Set RS=00 for host-visible, RS=11 for IMR |
| Snoop control wrong | Cache coherency issues | Set/clear NOSNOOP based on target |
| IOMMU blocking DMA | IOMMU fault in dmesg | Add ISH DMA mapping |
| LLI mode misconfigured | Multi-block transfer fails | Check linked-list descriptor chain |
| DMA timeout | Transfer never completes | Check FW DMA handler, channel enable |

---

## Debug Tools Reference

### Linux Tools

| Tool | Purpose | Key Command |
|------|---------|-------------|
| `lspci` | PCI device enumeration | `lspci -vvv -d 8086:e445` (TTL) |
| `dmesg` | Kernel log | `dmesg \| grep -i ish` |
| `iio-sensor-proxy` | Read IIO sensors | `monitor-sensor` |
| `evtest` | HID input events | `evtest /dev/input/eventX` |
| `i2cdetect` | Scan I2C bus | `i2cdetect -y [BUS]` |
| `acpidump` | ACPI tables | `acpidump > acpi.bin` |
| `debugfs` | ISH debug nodes | `ls /sys/kernel/debug/intel-ishtp/` |

### Windows Tools

| Tool | Purpose |
|------|---------|
| Device Manager | PCI/sensor device status |
| `devcon` | Command-line device management |
| `pnputil` | PnP driver management |
| WPP Tracing | ISH driver verbose logging |
| ETW (Event Tracing) | System-wide ISH events |
| `windbg` | Kernel debug, driver crash analysis |
| Sensor Diagnostic Tool | ISH sensor data validation |

### PythonSV / PySV

| Task | Method |
|------|--------|
| Read MMIO register | `ish.mem.read(offset)` |
| Write MMIO register | `ish.mem.write(offset, value)` |
| Read PCI config | `ish.cfg.[reg_name].read()` |
| Check power state | `ish.cfg.pmcsr.read() & 0x3` |
| Read IPC doorbell | `ish.mem.read(0x48)` → bit[31] = BUSY |
| Read FWSTS | `ish.mem.read(0x34)` |
| Read PMU SRAM PG | `ish.mem.read(0x04200000)` |
| Read wake events | `ish.mem.read(0x0420000C)` |

### TTK3 Hardware Debug

| Task | TTK3 Sub-Agent | When to Use |
|------|---------------|------------|
| Probe sensor I2C bus | TTK3-COMM | Verify sensor presence, read sensor registers |
| Monitor ISH GPIO signals | TTK3-COMM | Check ISH reset, interrupt signals |
| Measure ISH power rails | TTK3-COMM (ADC) | Verify VCC for ISH (VNNAON domain) |
| Flash new BIOS for ISH FW update | TTK3-BIOS | Update ISH firmware via BIOS |
| Power cycle platform | TTK3-POWER | Hard reset for stuck ISH |
| Monitor POST codes during ISH init | TTK3-BOOT | Track ISH initialization in boot sequence |

---

## TTL-Specific Debug Quick Reference

### Critical Register Dump Script (TTL)

```python
# Complete TTL ISH debug snapshot via PythonSV
ish = sv.socket0.pch.ish

print("=== TTL ISH DEBUG SNAPSHOT ===")
print()

# PCI identification
vid = ish.cfg.vid.read()
did = ish.cfg.did.read()
pmcsr = ish.cfg.pmcsr.read()
print(f"PCI: VID=0x{vid:04X} DID=0x{did:04X} D-state=D{pmcsr & 0x3}")
print()

# IPC HOST channel
print("=== IPC HOST Channel ===")
print(f"  PISR:        0x{ish.mem.read(0x00):08X}")
print(f"  PIMR:        0x{ish.mem.read(0x04):08X}")
print(f"  FWSTS:       0x{ish.mem.read(0x34):08X}")
print(f"  INBOUND_DB:  0x{ish.mem.read(0x48):08X}")
print(f"  OUTBOUND_DB: 0x{ish.mem.read(0x54):08X}")
print(f"  D0I3C:       0x{ish.mem.read(0x6D0):08X}")
print()

# Power state
print("=== Power Management ===")
print(f"  PMU SRAM_PG_EN:  0x{ish.mem.read(0x04200000):08X}")
print(f"  PMU WAKE_EVENT:  0x{ish.mem.read(0x0420000C):08X}")
print(f"  PMU MASK_EVENT:  0x{ish.mem.read(0x04200010):08X}")
print(f"  PMU VNN_REQ:     0x{ish.mem.read(0x0420003C):08X}")
print(f"  PMU VNN_REQ_ACK: 0x{ish.mem.read(0x04200040):08X}")
print()

# Clock and reset
print("=== Clock / Reset ===")
print(f"  CCU TRUNK_CG:  0x{ish.mem.read(0x04300000):08X}")
print(f"  CCU RST_HIS:   0x{ish.mem.read(0x0430003C):08X}")
print()

# SRAM health
print("=== SRAM ===")
print(f"  SRAM_CFGR:     0x{ish.mem.read(0x10500000):08X}")
print(f"  SRAM_INTR_STS: 0x{ish.mem.read(0x10500004):08X}")
print(f"  SRAM_LIMIT:    0x{ish.mem.read(0x10500040):08X}")
print()

# DMA channels
print("=== DMA Channels ===")
for ch in range(8):
    ctl = ish.mem.read(0x10101000 + ch * 4)
    print(f"  CH{ch}: DMA_CTL=0x{ctl:08X}")
print()

# Watchdog
print("=== Watchdog ===")
print(f"  WDTC: 0x{ish.mem.read(0x04900000):08X}")
print(f"  WDTV: 0x{ish.mem.read(0x04900008):08X}")
```

### CCU Reset History Decoding (RST_HIS at 0x0430003C)

Check this register to determine what caused the last ISH reset:
- Bit 0: Power-on reset
- Bit 1: Watchdog T2 reset
- Bit 2: Software reset
- Bit 3: Host-initiated reset (FUNCRST)

### SRAM ECC Error Checking

```python
# Check for SRAM ECC errors (NVL)
sram_sts = ish.mem.read(0x10500004)  # SRAM_INTR_STS (SRAM ECC registers base 0x10500000)
if sram_sts != 0:
    print(f"WARNING: SRAM interrupt status = 0x{sram_sts:08X}")
    print("  Check ECC error logging registers at 0x10500008+")
```

---

## HSDES Sighting Database

> Load `hsdes` skill to query live sightings: `hsdes search tenant=sighting "ISH [platform]"`

### How to File a New Sighting

1. Load `hsdes` skill
2. Use tenant: `sighting`
3. Required fields:
   - **Title**: `[PLATFORM][ISH] <brief description>` (e.g., `[TTL][ISH] IPC doorbell stuck BUSY after D0i3 exit`)
   - **Component**: `ISH`
   - **Platform**: `NVL` / `TTL` / etc.
   - **Symptom**: Detailed failure description
   - **Steps to Reproduce**: Exact test steps
   - **Logs**: Attach dmesg / ETW / PythonSV register dumps (use TTL debug snapshot script above)
   - **Frequency**: Always / Sometimes / Rarely
   - **Impact**: Blocking / Non-blocking

---

## Escalation Criteria

### Escalate to ISH IP Architect When:
- ISH PCI device never enumerates despite correct BIOS settings
- ISH firmware status register stuck in error state with no clear cause
- IPC registers show unexpected reset values (vs HAS)
- Register behavior does not match HAS specification
- SRAM ECC errors indicate hardware defect

### Escalate to ISH Firmware Team When:
- ISH firmware panic dump captured
- Firmware state machine stuck in unexpected state
- IPC doorbell protocol violation from firmware side
- Sensor enumeration failing despite correct HW configuration
- Watchdog T2 reset occurring during normal operation

### Escalate to Platform/PCH Team When:
- ISH power rails not enabled correctly (VNNAON domain)
- ISH interrupt routing missing in ACPI
- ISH DMA IOMMU faults at system level
- S0ix blocked by ISH despite correct ISH D0i3 configuration
- PMC sideband communication failure (opcode 0x6Fh, tag 0x06h)

### Escalate to Driver Team When:
- ISH driver crash/BSOD during normal operation
- Driver not implementing correct suspend/resume callbacks
- Driver IPC message format mismatch vs FW expectation
- Doorbell BUSY not being cleared by driver
