# FV-ISH Driver & Firmware Interaction Skill

> **Skill**: `fv-ish/driver`
> **Domain**: ISH Driver Architecture and Firmware Interaction
> **Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
> **Last Updated**: 2026-03-16

---

## IMPORTANT: HAS-First Policy

Before answering any driver/firmware interface question, load `fv-ish/has` skill and verify details against the ISH HAS. Driver behavior, firmware message formats, and interface protocols MUST be verified against the HAS. Information here is based on the ISH 5.9 HAS (SIP_ISH5p9), TTL OSXML register PDFs, and public Linux kernel ISH driver sources.

---

## 1. ISH Driver Stack Overview

### Linux Driver Stack

```
┌─────────────────────────────────────┐
│   HID Core (hid-core.ko)            │  ← OS HID subsystem
├─────────────────────────────────────┤
│   HID Sensor Hub (hid-sensor-hub.ko)│  ← HID sensor class driver
├─────────────────────────────────────┤
│   Individual Sensor Drivers         │  ← e.g. hid-sensor-accel-3d.ko
│   (hid-sensor-*.ko)                 │
├─────────────────────────────────────┤
│   ISH HID Client (ishtp-hid.ko)     │  ← Bridges ISHTP to HID
├─────────────────────────────────────┤
│   ISHTP Bus (ishtp.ko)              │  ← ISH Transport Protocol layer
├─────────────────────────────────────┤
│   ISH IPC (intel_ishtp_loader.ko)   │  ← IPC doorbell/mailbox transport
├─────────────────────────────────────┤
│   PCI / ACPI Bus                    │  ← Hardware enumeration
└─────────────────────────────────────┘
```

**Key Source Files** (Linux kernel — `drivers/hid/intel-ish-hid/`):

| File | Purpose |
|------|---------|
| `ipc/ipc.c` | ISH IPC — doorbell write, MSG register I/O, interrupt handling |
| `ipc/hw-ish.h` | ISH hardware register definitions (doorbell, MSG offsets) |
| `ishtp/bus.c` | ISHTP bus layer — client registration, enumeration |
| `ishtp/client.c` | ISHTP client API — connect, send, receive |
| `ishtp/hbm.c` | Host Bus Message protocol — firmware handshake |
| `ishtp-hid.c` | HID-over-ISHTP client driver |
| `ishtp-hid-client.c` | Sensor report handling, HID input events |
| `ishtp/loader.c` | ISH firmware loader (DMA-based via IMR) |

### Windows Driver Stack

```
┌─────────────────────────────────────┐
│   Windows Sensor Framework (SensorService.dll) │
├─────────────────────────────────────┤
│   HID Sensor Class Driver (HidSensorClassDevice.dll) │
├─────────────────────────────────────┤
│   ISH HID Miniport Driver (IshHid.sys) │  ← Intel proprietary
├─────────────────────────────────────┤
│   ISH Transport Driver (IshTp.sys)  │  ← IPC doorbell/ISHTP abstraction
├─────────────────────────────────────┤
│   ISH PCIe Driver (IshPci.sys)      │  ← PCI enumeration, MMIO setup
└─────────────────────────────────────┘
```

---

## 2. Linux ISH Driver Deep Dive

### 2.1 Driver Initialization Flow

```
pci_driver.probe()
    → Map BAR0 MMIO (PCI DevID 0xE445 / VenID 0x8086 for TTL)
    → ish_init()
        → ish_hw_reset()            # Reset ISH HW
        → ish_wakeup()              # Wake ISH from low-power
            → Clear D0I3C.D0i3 (offset 0x6D0 bit[2])
            → Wait for D0I3C.CIP=0 (bit[0])
        → ishtp_start()             # Start ISHTP layer
            → hbm_start()           # Host Bus Message handshake
                → ENUM_CLIENTS      # Enumerate ISH firmware clients
                → CONNECT_CLIENT    # Connect to HID sensor client
                    → ishtp_hid_probe()
                        → register HID device per sensor
```

### 2.2 IPC Doorbell Low-Level Operations

ISH uses an IPC doorbell/mailbox architecture (NOT circular buffers). Each direction has a doorbell register and 32 × 32-bit message registers (128 bytes payload).

**Doorbell Write** (host → ISH):
```c
/* ipc/ipc.c — Host-to-ISH IPC send */
static void ish_ipc_send_msg(struct ishtp_device *dev, void *msg, int len)
{
    /* Write payload to outbound MSG registers (0x60–0xDC, up to 32 DWORDs) */
    for (i = 0; i < len/4; i++)
        writel(((u32 *)msg)[i], dev->mem_addr + IPC_REG_HOST2ISH_MSG + i*4);

    /* Set doorbell BUSY bit to signal ISH */
    doorbell_val = IPC_DRBL_BUSY_BIT | (len << IPC_DRBL_LEN_OFFS);
    writel(doorbell_val, dev->mem_addr + IPC_REG_HOST2ISH_DRBL);
    /* ISH sees level-sensitive interrupt while BUSY=1 */
}
/* IPC_REG_HOST2ISH_DRBL = INBOUND_DB (0x48): [31]=BUSY, [30:0]=payload/length */
/* IPC_REG_HOST2ISH_MSG  = OUT_MSG (0x60–0xDC): 32 × 32-bit registers */
```

**Interrupt Handler** (ISH → host):
```c
static irqreturn_t ish_irq_handler(int irq, void *dev_id)
{
    /* Read ISH→HOST doorbell (OUTBOUND_DB at 0x54) */
    doorbell = readl(dev->mem_addr + IPC_REG_ISH2HOST_DRBL);
    if (doorbell & IPC_DRBL_BUSY_BIT) {  /* bit[31] = BUSY */
        /* Read payload from inbound MSG registers (0xE0–0x15C) */
        for (i = 0; i < msg_len/4; i++)
            ((u32 *)rx_buf)[i] = readl(dev->mem_addr + IPC_REG_ISH2HOST_MSG + i*4);

        /* Clear BUSY via BUSY_CLEAR register (0x378) */
        writel(1, dev->mem_addr + IPC_REG_BUSY_CLEAR);
        /* Process ISHTP message */
    }
}
```

**IPC Register Summary** (HOST channel at BAR0):

| Register | Offset | Key Bits | Purpose |
|----------|--------|----------|---------|
| PISR | 0x00 | [0]=DB_INT | Peripheral Interrupt Status |
| PIMR | 0x04 | [0]=DB_INT_EN | Peripheral Interrupt Mask |
| HOST_PIMR | 0x08 | [0]=DB_INT_EN | Host-side Interrupt Mask |
| HOST_PISR | 0x0C | [0]=DB_INT | Host-side Interrupt Status |
| FWSTS | 0x34 | [31:0]=FW_STATUS | Firmware Status |
| INBOUND_DB | 0x48 | [31]=BUSY | Host→ISH Doorbell |
| OUTBOUND_DB | 0x54 | [31]=BUSY | ISH→Host Doorbell |
| OUT_MSG[0-31] | 0x60–0xDC | [31:0]=DATA | Outbound Payload (32 DWORDs) |
| IN_MSG[0-31] | 0xE0–0x15C | [31:0]=DATA | Inbound Payload (32 DWORDs) |
| BUSY_CLEAR | 0x378 | [0]=CLR | Clear Outbound BUSY |
| D0I3C | 0x6D0 | [2]=D0i3,[0]=CIP | D0i3 Control |

### 2.3 ISHTP HBM (Host Bus Message) Protocol

The HBM is the first-level handshake between host driver and ISH firmware.

**HBM Sequence**:
```
HOST                            ISH FIRMWARE
 |                                    |
 |── HOST_START_REQ ─────────────────>|
 |<─ HOST_START_RES ──────────────────|
 |── ENUM_REQ ───────────────────────>|  (enumerate clients)
 |<─ ENUM_RES ────────────────────────|  (returns client list)
 |── CLIENT_PROPERTIES_REQ ──────────>|  (per client)
 |<─ CLIENT_PROPERTIES_RES ───────────|
 |── CONNECT_REQ ────────────────────>|  (connect to HID client)
 |<─ CONNECT_RES ─────────────────────|
 |── FLOW_CONTROL ───────────────────>|  (grant credits)
 |             (data exchange starts)  |
```

### 2.4 HID Sensor Client Registration

```c
/* ishtp-hid-client.c */
static int ishtp_hid_recv_msg(struct ishtp_cl *cl, void *buf, size_t len)
{
    struct ishtp_hid_data *data = cl->client_data;

    switch (header->type) {
    case REPORT_TYPE_INPUT:
        /* Deliver sensor data to HID core */
        hid_input_report(data->hid, HID_INPUT_REPORT, buf, len, 1);
        break;
    case REPORT_TYPE_FEATURE:
        /* Handle feature report (sensor properties) */
        break;
    }
}
```

---

## 3. Windows ISH Driver Deep Dive

### 3.1 Driver Entry Points

| Callback | Purpose |
|----------|---------|
| `EvtDeviceAdd()` | PCI device enumeration (DevID 0xE445 for TTL) |
| `EvtDevicePrepareHardware()` | Map MMIO BAR0, request MSI IRQ |
| `EvtDeviceD0Entry()` | Clear D0I3C.D0i3, initialize ISH, load FW |
| `EvtDeviceD0Exit()` | Set D0I3C.D0i3, put ISH in low-power |
| `EvtInterruptIsr()` | Read OUTBOUND_DB[31], check BUSY, queue DPC |
| `EvtInterruptDpc()` | Read IN_MSG[0-31], process ISHTP message |

### 3.2 WPP Trace Levels

| Level | Flag | Usage |
|-------|------|-------|
| `TRACE_LEVEL_CRITICAL` | `DBG_FLAG_IPC` | IPC doorbell errors, BUSY timeout |
| `TRACE_LEVEL_ERROR` | `DBG_FLAG_ISHTP` | ISHTP protocol errors |
| `TRACE_LEVEL_WARNING` | `DBG_FLAG_HID` | HID report issues |
| `TRACE_LEVEL_INFORMATION` | `DBG_FLAG_PM` | D0i3/D3 transitions, D0I3C writes |
| `TRACE_LEVEL_VERBOSE` | `DBG_FLAG_ALL` | Full doorbell/MSG register trace |

### 3.3 ETW Event Collection (Windows)

```powershell
# Start ISH ETW trace
logman create trace ISH_Trace -p {GUID_ISH_PROVIDER} 0xFFFFFFFF 5
logman start ISH_Trace
# ... reproduce issue ...
logman stop ISH_Trace
# Convert to human-readable
tracefmt ISH_Trace.etl -o ISH_Trace.txt -p C:\symbols\ISH
```

---

## 4. Firmware Loading

### 4.1 TTL/ISH 5.9 Boot Flow

ISH 5.9 uses a multi-stage boot process with CSE (Converged Security Engine) involvement:

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Boot ROM (8KB ROM)                                     │
│   - HW reset releases ISH core                                  │
│   - Boot ROM initializes LMT 3.8/3.9 (MinuteIA) core           │
│   - Configures basic SRAM (first banks of 640KB)                │
│   - Signals CSE for BUP loading                                 │
├─────────────────────────────────────────────────────────────────┤
│ STAGE 2: CSE loads BUP (Bring-Up) firmware                      │
│   - BUP max size: 64KB (Intel-signed)                           │
│   - CSE authenticates BUP via secure boot chain                 │
│   - BUP runs on ISH core, initializes HW interfaces             │
│   - BUP signals readiness to host via FWSTS register (0x34)     │
├─────────────────────────────────────────────────────────────────┤
│ STAGE 3: Host driver loads Main FW via IMR (Isolated Memory)    │
│   - Main FW max size: 1.5MB                                     │
│   - Host driver allocates DMA buffer in IMR                     │
│   - Sends FW image via DMA (RS3=IMR DRAM root-space)            │
│   - ISH copies FW from IMR to SRAM (640KB, 20×32KB banks)       │
│   - Main FW starts, enumerates sensors                          │
├─────────────────────────────────────────────────────────────────┤
│ STAGE 4: HBM Handshake                                          │
│   - Host sends HOST_START_REQ via IPC doorbell                  │
│   - ISH FW responds with client enumeration                     │
│   - Sensors begin reporting data                                │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 S3 Resume Optimization

ISH 5.9 includes an S3 resume optimization path through CSE:

```
S3 RESUME (Fast Path):
  1. CSE retains uncompressed ISH main FW in IMR across S3
  2. On resume, CSE computes hash of retained image
  3. Hash compared against known-good value
  4. If match → skip full FW reload, directly start main FW
  5. If mismatch → full reload from host (fallback to Stage 3)

  Benefit: ~200ms faster resume vs full FW reload
```

### 4.3 Firmware Loading Protocol Detail

**DMA-Based Loading** (primary for TTL):
```
HOST DRIVER                     ISH FIRMWARE (BUP)
    |                                |
    |── Read FWSTS (0x34)            |  (wait for BUP ready)
    |── LOADER: START ──────────────>|  (via IPC doorbell 0x48)
    |<─ LOADER: READY ───────────────|  (via IPC doorbell 0x54)
    |── DMA: Setup IMR buffer        |
    |── DMA: FW IMAGE via RS3 ──────>|  (DMA_CTL XFER_MODE=2, RD_RS=RS3)
    |── LOADER: LOAD_AND_START ─────>|  (via IPC doorbell)
    |<─ FWSTS updated ───────────────|  (FW running indicator)
    |── HBM: HOST_START_REQ ────────>|  (begin HBM handshake)
```

**IPC-Based Loading** (fallback — via MSG registers):
```
HOST DRIVER                     ISH FIRMWARE (BUP)
    |── IPC: FW_PAYLOAD (128B max)──>|  (via MSG[0-31] registers)
    |<─ IPC: FW_FRAGMENT_ACK ────────|  (via ISH→HOST doorbell)
    |── IPC: FW_PAYLOAD (next 128B)─>|  (repeat until complete)
    |── IPC: FW_LOAD_COMPLETE ──────>|
    |<─ IPC: FW_LOAD_STATUS ─────────|
```

### 4.4 FWSTS Register Decoding

The FWSTS register (HOST IPC offset 0x34) provides firmware boot status:

```
FWSTS (0x34) — Firmware Status Register:
  Bits [31:28]: Reserved
  Bits [27:24]: FW error code (0=OK, non-zero=error)
  Bits [23:20]: Boot stage (0=ROM, 1=BUP, 2=MainFW, 3=Running)
  Bits [19:16]: Reserved
  Bits [15:0]:  FW-specific status flags
```

> **Note**: Exact FWSTS bit field definitions are FW-version-dependent. Verify against the
> ISH FW ICD (Interface Control Document) for your specific FW build.

### 4.5 Firmware Version Query

```python
# PythonSV example — read ISH FW version via FWSTS and IPC
def get_ish_fw_status(target):
    ish = getattr(target, "pch_ish")

    # Read FWSTS register from HOST IPC channel
    fw_status = ish.mem.read32(0x34)  # FWSTS offset
    boot_stage = (fw_status >> 20) & 0xF
    error_code = (fw_status >> 24) & 0xF

    stages = {0: "ROM", 1: "BUP", 2: "MainFW Loading", 3: "Running"}
    print(f"ISH FW Status: 0x{fw_status:08X}")
    print(f"  Boot Stage: {stages.get(boot_stage, 'Unknown')} ({boot_stage})")
    print(f"  Error Code: {error_code} ({'OK' if error_code == 0 else 'ERROR'})")
    return fw_status
```

### 4.6 Firmware Rollback

- ISH supports firmware rollback protection (Anti-Rollback Version, ARV)
- Downgrading below ARV will be rejected by CSE during BUP authentication
- Check current ARV: query via HECI FW_VERSION message
- Update ARV: done via MEI/HECI provisioning command (requires CSE involvement)

---

## 5. Watchdog Timer (WDT)

ISH 5.9 includes a two-stage watchdog timer for firmware health monitoring.

### 5.1 WDT Registers (MIA base 0x04900000)

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| WDTC | 0x00 | 0xA0A0 | Control — [17]=EN, [15:8]=T2_period, [7:0]=T1_period |
| WDTR | 0x04 | — | Reset — write to restart WDT countdown |
| WDTV | 0x08 | — | Value — current countdown (RO) |

### 5.2 Two-Stage Watchdog Behavior

```
Normal Operation:
  FW periodically writes WDTR → resets countdown → no action

Stage 1 (T1 timeout):
  Countdown reaches T1 threshold → interrupt to ISH core
  FW interrupt handler should restart WDT (write WDTR)
  If FW is hung → proceeds to Stage 2

Stage 2 (T2 timeout):
  Countdown reaches T2 threshold → ISH core reset
  Requires full re-initialization (Boot ROM → BUP → Main FW)
```

### 5.3 WDT Validation Points

```python
# Test: WDT Stage 1 interrupt
# Steps:
#   1. Enable WDT (WDTC[17]=1)
#   2. Set T1 short timeout (WDTC[7:0]=0x01)
#   3. Do NOT service WDT
#   4. Verify ISH interrupt fires at T1
# Expected: ISH core receives WDT interrupt, FWSTS shows WDT event

# Test: WDT Stage 2 reset
# Steps:
#   1. Enable WDT, set both T1 and T2 short
#   2. Do NOT service WDT or T1 interrupt
#   3. Wait for T2 timeout
#   4. Verify ISH core resets (FWSTS returns to ROM/BUP stage)
# Expected: ISH core fully resets, requires FW reload
```

---

## 6. Driver–Firmware Interface (ISHTP Protocol Layer)

### 6.1 ISHTP Client GUID

Each ISH firmware client is identified by a GUID. The HID sensor client has a fixed GUID:

```c
/* HID-over-ISHTP client GUID — from Linux kernel source */
static const guid_t ishtp_hid_guid =
    GUID_INIT(0x33AECD58, 0xB679, 0x4E54,
              0x9B, 0xD9, 0xA0, 0x4D, 0x34, 0xF0, 0xC2, 0x26);
/* Note: Additional client GUIDs (cros_ec, debug) are FW-version specific */
```

### 6.2 ISHTP Flow Control

```
HOST                            ISH FIRMWARE
 |── FLOW_CONTROL (credits=N) ─>|  (host grants N receive slots)
 |<─ FLOW_CONTROL (credits=M) ──|  (FW grants M receive slots)
 |<─ DATA (sensor report) ───────|  (consumes 1 host credit)
 |── FLOW_CONTROL (credits=1) ──>|  (replenish credit)
```

Flow control stalls if credits reach 0. This is a common source of ISH hangs.

**IPC Payload Constraint**: Each IPC doorbell transaction carries up to 128 bytes (32 × 32-bit MSG registers). ISHTP multi-fragment messages split larger payloads across multiple IPC transactions.

### 6.3 ISHTP Maximum Message Size

- **Single IPC transaction**: 128 bytes (32 × 32-bit MSG registers)
- **Multi-fragment ISHTP message**: split into 128-byte IPC fragments, reassembled by ISHTP layer
- Fragment header: 4 bytes (fragment index, total fragments, length)
- Maximum reassembled message: platform-specific (typically 4KB–16KB)

---

## 7. Driver Debugging Techniques

### 7.1 Linux Debug Commands

```bash
# Check ISH PCI device (TTL: DevID 0xE445)
lspci -vvv -d 8086:E445

# Check ISH driver binding
ls /sys/bus/pci/drivers/intel_ish_ipc/

# Check ISH client devices
ls /sys/bus/ishtp/devices/

# Check ISH HID devices
ls /sys/bus/hid/devices/ | grep ISH

# Enable ISH dynamic debug
echo 'module intel_ishtp +p' > /sys/kernel/debug/dynamic_debug/control
echo 'module intel_ish_ipc +p' > /sys/kernel/debug/dynamic_debug/control

# Check ISH interrupt stats
cat /proc/interrupts | grep ish

# Read ISH register via sysfs (if available)
cat /sys/kernel/debug/intel_ish/status

# dmesg filter for ISH
dmesg | grep -i "ish\|ishtp\|ishipc" | head -100
```

### 7.2 Common dmesg Patterns

| Log Pattern | Meaning | Action |
|-------------|---------|--------|
| `ISH: PCI device found` | ISH enumerated (0x8086:0xE445) | Good — continue |
| `ISH: firmware not found` | FW binary missing | Check FW package |
| `ISH: IPC timeout` | Doorbell BUSY not cleared | Check ISH FW, try reset |
| `ISH: HBM start timeout` | HBM handshake failed | Check FW version, FWSTS |
| `ISHTP: flow control timeout` | Credit starvation | Check driver credit mgmt |
| `ISH: DMA error` | DMA transfer failed | Check IMR allocation, RS |
| `ISH: D0i3 transition failed` | D0I3C.CIP stuck | Check power state, PMC |
| `hid-sensor-hub: sensor not found` | Sensor enumeration failed | Check BOM, I2C/I3C bus |

### 7.3 Windows Debug Commands

```powershell
# Check ISH device status (TTL: DevID E445)
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*ISH*" }

# Check ISH device details
devcon status "PCI\VEN_8086&DEV_E445*"

# Collect ISH ETW trace
logman create trace ISH -p "Intel-ISH-Driver" 0xFFFF 5 -o C:\ISH.etl
logman start ISH
# Reproduce issue
logman stop ISH

# Check Windows Event Log for ISH errors
Get-WinEvent -LogName System | Where-Object { $_.Message -like "*ISH*" }

# Check sensor devices
Get-PnpDevice | Where-Object { $_.Class -eq "Sensor" }
```

### 7.4 PythonSV Register Dump for Driver Debug

```python
# Dump ISH diagnostic registers during driver debug
def dump_ish_debug_regs(target):
    ish = getattr(target, "pch_ish")

    # HOST IPC channel registers
    regs = {
        "PISR":         ish.mem.read32(0x00),   # Interrupt status
        "PIMR":         ish.mem.read32(0x04),   # Interrupt mask
        "FWSTS":        ish.mem.read32(0x34),   # FW status
        "INBOUND_DB":   ish.mem.read32(0x48),   # Host→ISH doorbell
        "OUTBOUND_DB":  ish.mem.read32(0x54),   # ISH→Host doorbell
        "D0I3C":        ish.mem.read32(0x6D0),  # D0i3 control
    }

    for name, val in regs.items():
        print(f"  ISH_{name}: 0x{val:08X}")

    # Decode key fields
    fwsts = regs["FWSTS"]
    print(f"  FW Boot Stage: {(fwsts >> 20) & 0xF}")
    print(f"  FW Error Code: {(fwsts >> 24) & 0xF}")
    print(f"  Inbound BUSY:  {(regs['INBOUND_DB'] >> 31) & 1}")
    print(f"  Outbound BUSY: {(regs['OUTBOUND_DB'] >> 31) & 1}")
    print(f"  D0i3 Active:   {(regs['D0I3C'] >> 2) & 1}")
    return regs
```

---

## 8. Known Issues and Workarounds

> **Note**: Populate with actual HSDES sightings as they are filed.
> Use the `hsdes` skill to query for live ISH sightings: `hsdes search "ISH driver" tenant=sighting`

| HSDES ID | Title | Symptom | Platform | Status | Workaround |
|----------|-------|---------|----------|--------|------------|
| TODO | ISH FW load timeout on cold boot | FWSTS stuck at BUP stage | NVL/TTL | TODO | Check IMR allocation |
| TODO | ISHTP flow control stall after S3 | Sensor data stops after resume | NVL/TTL | TODO | Driver credit replenish |
| TODO | WDT reset loop | ISH keeps resetting (FWSTS cycles) | TTL | TODO | Check FW health, WDT config |
| TODO | D0i3 entry fails (CIP stuck) | D0I3C.CIP=1 indefinitely | TTL | TODO | Check PMC sideband |

---

## 9. Validation Points

### 9.1 Driver Load/Unload

```python
# Test: Driver bind/unbind cycle
# Steps:
#   1. Verify ISH PCI device (0x8086:0xE445) enumerates
#   2. Verify FWSTS shows "Running" (stage 3, error 0)
#   3. Unbind driver, verify D0I3C.D0i3 set, ISH enters low-power
#   4. Re-bind driver, verify ISH recovers and sensors re-enumerate
# Expected: No errors, all sensors available after re-bind
```

### 9.2 Firmware Update Flow

```python
# Test: ISH FW update via DMA
# Steps:
#   1. Read FWSTS for current FW status
#   2. Trigger FW update (new binary via IMR DMA, RS3)
#   3. Verify DMA completes (DMA_CTL channel status)
#   4. Verify FWSTS transitions: BUP → MainFW → Running
#   5. Verify sensors functional after FW update
# Expected: FWSTS reaches stage 3, sensors operational
```

### 9.3 Driver Power Management

```python
# Test: D0i3 Suspend/Resume cycle
# Steps:
#   1. Verify sensors active, FWSTS=Running
#   2. Trigger D0i3 entry (write D0I3C.D0i3=1 at 0x6D0)
#   3. Wait for D0I3C.CIP=0 (transition complete)
#   4. Trigger D0i3 exit (write D0I3C.D0i3=0)
#   5. Wait for FWSTS=Running, verify sensors resume
# Expected: Sensors resume within 500ms, no stale data

# Test: S3 resume with CSE fast path
# Steps:
#   1. Enter S3 with sensors active
#   2. Resume from S3
#   3. Verify ISH skips full FW reload (fast path via CSE hash)
#   4. Measure time from S3 resume to first sensor report
# Expected: Faster resume vs cold boot (~200ms savings)
```

### 9.4 Watchdog Timer Tests

```python
# Test: WDT normal operation
# Steps:
#   1. Verify WDTC[17]=1 (WDT enabled by FW)
#   2. Read WDTV periodically, verify countdown resets (FW servicing)
#   3. Verify no WDT interrupts during normal operation
# Expected: WDTV never reaches T1 threshold

# Test: WDT recovery after FW hang
# Steps:
#   1. Inject FW hang (if debug hook available)
#   2. Observe WDT Stage 1 interrupt (T1 timeout)
#   3. Observe WDT Stage 2 reset (T2 timeout)
#   4. Verify ISH resets and recovers (FWSTS cycles back to ROM→Running)
# Expected: Full recovery within T2+boot time
```

### 9.5 Multi-OS Compatibility

| Test | Windows | Linux | Expected |
|------|---------|-------|---------|
| ISH PCI enumeration (0xE445) | Pass/Fail | Pass/Fail | PASS on both |
| FW load via IMR DMA | Pass/Fail | Pass/Fail | PASS on both |
| Sensor enumeration | Pass/Fail | Pass/Fail | All sensors on both |
| IPC doorbell latency | Pass/Fail | Pass/Fail | < 1ms on both |
| D0i3 transition | Pass/Fail | Pass/Fail | PASS on both |
| S3 resume (CSE fast path) | Pass/Fail | Pass/Fail | PASS on both |

### 9.6 Stress Tests

```python
# Test: Driver stress — repeated sensor enable/disable
# Steps:
#   1. Enable all sensors
#   2. Collect data for 30 seconds
#   3. Disable all sensors
#   4. Repeat 100 cycles
# Expected: No crash, no hang, no memory leak, FWSTS stable

# Test: Driver stress — repeated D0i3 transitions
# Steps:
#   1. Enable sensors
#   2. Enter/exit D0i3 50 times (via D0I3C register)
#   3. Verify sensor data valid after each exit
# Expected: 100% transition success, no D0I3C.CIP stuck

# Test: IPC doorbell stress
# Steps:
#   1. Send 1000 IPC messages in rapid succession
#   2. Verify all BUSY bits clear within timeout
#   3. Verify no lost messages (response count matches)
# Expected: Zero message loss, no BUSY stuck
```

---

## 10. TTL-Specific Driver Notes

### 10.1 TTL Driver Characteristics (ISH 5.9)

| Feature | TTL Value |
|---------|-----------|
| PCI Device ID | 0xE445 |
| ISH Core | LMT 3.8/3.9 (MinuteIA) |
| Clock | 200/100 MHz |
| IPC Architecture | Doorbell/mailbox (NOT circular buffers) |
| IPC Payload Size | 128 bytes (32 × 32-bit MSG regs) |
| IPC Channels | 8 (HOST, HOSTSPARE, CSE, PMC, CNVi, ACE, ESE, AVB) |
| FW Boot | ROM → CSE/BUP (64KB) → Host/MainFW (1.5MB via IMR) |
| S3 Optimization | CSE hash-check of retained IMR image |
| WDT | Two-stage (T1=interrupt, T2=reset) |
| Sensor I/O | 3×I2C, 2×I3C, 3×UART, 2×SPI, 12 GPIO |

### 10.2 NVL-Specific Notes (ISH 5.8 NVL data)

NVL (Nova Lake) ISH 5.8 differences and firmware boot flow notes (from Co-De Sign HAS extraction):

- PCI Device ID: `0x6E78` (PCH-S), Vendor ID: `0x8086`
- Firmware Boot Flow:
  1. Boot ROM: On reset ISH executes from internal 8KB Boot ROM. ROM initiates reset sync with CSE. ROM may DMA BUP from IMR to SRAM. ROM advertises LTR=2ms before DMA, then sets to infinite after.
  2. BUP Loading by CSE: CSE locates ISH BUP partition in NVM, authenticates, loads to ISH IMR (offset 0). BUP is Intel-signed, IPL meta format. CSE may also load 'doomsday' ROM patch script. BUP max 64KB.
  3. Main FW Loading by Host Driver via IMR: Host OS driver copies ISH main FW to ISH IMR. CSE receives IPC cmd to authenticate. CSE verifies (Intel or OEM signed). On success, CSE notifies ISH+host. Main FW loaded to SRAM. Max 1.5MB.
  4. S3 Resume Optimization: CSE checks if ISH main FW in IMR matches saved hash. If match, copies from IMR to SRAM (skip NVM reload). If mismatch, reloads from NVM (cold boot).
  5. Capsule Update: CSE supports FW update for ISH code in CSE-managed flash. CSE reads from ISH UMA.

- WDT: Two-stage (T1->interrupt, T2->reset). WDTC register at `0x04900000`.

- MIA Register Base Addresses (NVL layout, fewer instances than TTL):
  - I2C: `0x00000000` (3 instances, 0x2000 stride)
  - GPIO: `0x00100000`
  - I3C: `0x04800000` (1 instance for NVL)
  - SPI: `0x08000000` (1 instance for NVL)
  - UART: `0x08100000` (2 instances, 0x2000 stride)

- Sensor I/O controllers (NVL ISH 5.8):
  - I2C: 3 controllers (up to 1Mb/s)
  - I3C: 1 controller (HDR/DDR 25Mbps) — NVL has 1 vs TTL's 2
  - SPI: 1 controller (25Mbps) — NVL has 1 vs TTL's 2
  - UART: 2 controllers (4Mbps) — NVL has 2 vs TTL's 3
  - GPIO: 8-12 (PCH-S: 12, general: 8, muxed with other GPIO)

Verify these NVL values against the NVL HAS when available; they were populated from the Co-De Sign extraction for ISH 5.8.

---

## Cross-References

- Register details: load `fv-ish/registers`
- IPC protocol details: load `fv-ish/heci`
- Power management flows: load `fv-ish/power`
- DMA architecture: load `fv-ish/dma`
- Platform-specific data: load `fv-ish/platform`
- Debug/triage: load `fv-ish/debug`
- HAS reference: load `fv-ish/has`
