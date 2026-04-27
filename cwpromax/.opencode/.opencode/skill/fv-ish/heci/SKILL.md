# FV-ISH HECI Skill — IPC Doorbell/Mailbox & ISHTP Transport Layer

> **Skill**: `fv-ish/heci`
> **Owner**: Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team**: CVE - ISH Validation
> **Last Updated**: 2026-03-16 (rev2.0 — updated with TTL IPC register data)
> **Primary Platform**: NVL (Nova Lake)

---

## Skill Identity

You are the ISH HECI (Host Embedded Controller Interface) / IPC protocol skill. You provide detailed knowledge of the IPC doorbell/mailbox transport, ISHTP (ISH Transport Protocol), message formats, flow control, connection management, and the multi-channel IPC architecture used for host-to-ISH communication.

**HAS-First Policy**: Always load `fv-ish/has` and verify IPC register definitions, doorbell protocols, and message formats against the NVL ISH HAS before use in test scripts.

**IMPORTANT**: ISH does **NOT** use classic HECI circular buffers. ISH uses an **IPC doorbell/mailbox** architecture with dedicated MSG registers. Do not confuse ISH IPC with MEI/CSME HECI circular buffer transport.

---

## IPC Architecture Overview

```
  ┌─────────────────────────────────────────┐
  │           Host (OS/Driver)              │
  │  ┌───────────────────────────────────┐  │
  │  │   HID Sensor Class Driver         │  │
  │  └─────────────┬─────────────────────┘  │
  │  ┌─────────────▼─────────────────────┐  │
  │  │   ISHTP Client (ishtp-hid-client) │  │
  │  └─────────────┬─────────────────────┘  │
  │  ┌─────────────▼─────────────────────┐  │
  │  │   ISHTP Bus Layer (ishtp/bus.c)   │  │  ← Higher-level transport
  │  └─────────────┬─────────────────────┘  │
  │  ┌─────────────▼─────────────────────┐  │
  │  │   IPC Layer (ipc/ipc.c)           │  │  ← Doorbell/Mailbox transport
  │  └─────────────┬─────────────────────┘  │
  └────────────────┼────────────────────────┘
                   │  IOSF / MMIO (BAR0)
  ┌────────────────▼────────────────────────┐
  │           ISH Firmware                  │
  │  ┌───────────────────────────────────┐  │
  │  │   ISHTP Server (sensor clients)   │  │
  │  └─────────────┬─────────────────────┘  │
  │  ┌─────────────▼─────────────────────┐  │
  │  │   IPC Transport (ISH side)        │  │
  │  └───────────────────────────────────┘  │
  └─────────────────────────────────────────┘
```

### IPC vs ISHTP

| Layer | Name | Role |
|-------|------|------|
| Lower | **IPC** | Doorbell/mailbox transport via MSG registers and doorbell bits. 128-byte payload per direction per channel. |
| Upper | **ISHTP** | Higher-level protocol over IPC. Adds multi-client support, flow control credits, fragmentation, HBM enumeration. |

**Key difference from MEI/CSME HECI**: ISH does NOT use circular buffers with read/write pointers. ISH uses a **doorbell register** with BUSY bit [31] and **32 dedicated MSG registers** (128 bytes) per direction per channel.

---

## IPC Channel Architecture (TTL — ISH 5.9)

ISH has **8 IPC channels**, each connecting ISH to a different SoC endpoint:

### HOST-Facing Channels (Wrapper Registers)

| Channel | Base Offset | Bus Type | Purpose |
|---------|-------------|----------|---------|
| **HOST** | `0x0000` | MEM (BAR0) | Primary host↔ISH communication (sensor data, ISHTP) |
| **HOSTSPARE** | `0x0000` (separate space) | MEM | Reserved/spare host channel |
| **CSE** | `0x1000` | MSG (sideband) | ISH↔CSME communication (FW loading, security) |
| **PMC** | `0x2000` | MSG (sideband) | ISH↔PMC power management coordination |
| **CNVi** | `0x3000` | MSG (sideband) | ISH↔CNVi connectivity offload |
| **ACE** | `0x4000` | MSG (sideband) | ISH↔Audio/Camera Engine |
| **ESE** | `0x5000` | MSG (sideband) | ISH↔Embedded Security Engine |
| **AVB** | `0x6000` | MSG (sideband) | ISH↔Audio/Video Bridge |

> The **HOST** channel is the primary channel used by the ISH host driver for all ISHTP/sensor communication. Other channels are used for internal SoC coordination.

### MIA-Side IPC Registers (Internal to ISH)

All 8 IPC channels are also visible from the MIA (MinuteIA) core side at base `0x04100000` with `0x1000` stride per channel. The ISH firmware uses these registers to send/receive messages.

NVL (ISH 5.8) specific IPC channel register addresses and data windows (fabric/MIA mapped):

- PMC/WiFi: DB = 0x10680, DBM = 0x10684, CSR = 0x10688, Data window = 0x17400 - 0x174FF
- ISH/WiFi: DB = 0x10690, DBM = 0x10694, CSR = 0x10698, Data window = 0x17600 - 0x176FF
- ISH/BT:   DB = 0x106A0, DBM = 0x106A4, CSR = 0x106A8, Data window = 0x17500 - 0x175FF
- CSE <-> ISH sideband registers: DB = 0x003C (CSE->ISH) / 0x1050 (ISH->CSE), DBM = 0x0000 / 0x105C

Notes:
- Doorbell layout: bit [31] = BUSY, bits [30:0] = COMMAND/PAYLOAD.
- BUSY handshake: check DBM BUSY==0 -> write cmd + BUSY=1 -> HW copies to peer -> peer interrupt -> peer processes and clears BUSY -> HW copies back.
- Payload per channel: 32 × 32-bit registers = 128 bytes (per direction).


---

## Per-Channel IPC Register Map (TTL)

Each IPC channel has the following register layout relative to the channel base:

| Offset | Register | R/W | Description |
|--------|----------|-----|-------------|
| `0x000` | `PISR` | R/W1C | Peripheral Interrupt Status Register |
| `0x004` | `PIMR` | R/W | Peripheral Interrupt Mask Register |
| `0x008` | `HOST_PIMR` | R/W | Host-side Peripheral Interrupt Mask |
| `0x00C` | `HOST_PISR` | R/W1C | Host-side Peripheral Interrupt Status |
| `0x010` | `CIM` | R/W | Channel Interrupt Mask |
| `0x014` | `CIS` | R/W1C | Channel Interrupt Status |
| `0x034` | `FWSTS` | RO | Firmware Status (written by ISH FW) |
| `0x038` | `COMM` | R/W | Communication register |
| `0x048` | `INBOUND_DB` | R/W | Inbound Doorbell (sender→receiver) |
| `0x054` | `OUTBOUND_DB` | R/W | Outbound Doorbell (receiver→sender) |
| `0x060`–`0x0DC` | `OUT_MSG1`–`OUT_MSG32` | R/W | Outbound message payload (32×32-bit = 128 bytes) |
| `0x0E0`–`0x15C` | `IN_MSG1`–`IN_MSG32` | RO | Inbound message payload (32×32-bit = 128 bytes) |
| `0x360`–`0x374` | `REMAP0`–`REMAP5` | R/W | Address remap registers |
| `0x378` | `BUSY_CLEAR` | R/W | Busy clear register |
| `0x6D0` | `D0I3C` | R/W | D0i3 Control register (default=0x8) |

### Doorbell Register Bit Fields

```
INBOUND_DB / OUTBOUND_DB (32-bit):
 31      30                                    0
 ┌───────┬─────────────────────────────────────┐
 │ BUSY  │          PAYLOAD                    │
 │  [31] │          [30:0]                     │
 └───────┴─────────────────────────────────────┘
```

| Bit | Field | Description |
|-----|-------|-------------|
| [31] | `BUSY` | Message pending. Set by sender, cleared by receiver after reading payload. Level-sensitive interrupt asserted while BUSY=1. |
| [30:0] | `PAYLOAD` | Doorbell payload — used for short messages or IPC protocol commands |

### D0I3C Register Bit Fields

```
D0I3C @ 0x6D0 (32-bit, default = 0x8):
  4      3      2      1      0
 ┌──────┬──────┬──────┬──────┬──────┐
 │ IRC  │  RR  │ D0i3 │  IR  │ CIP  │
 │ [4]  │ [3]  │ [2]  │ [1]  │ [0]  │
 └──────┴──────┴──────┴──────┴──────┘
```

| Bit | Field | Access | Default | Description |
|-----|-------|--------|---------|-------------|
| [4] | `IRC` | RO | 0 | Interrupt Request Capability |
| [3] | `RR` | RW/1C | 1 | Restore Required (default=1 → 0x8) |
| [2] | `D0i3` | RW | 0 | D0i3 state request (1=enter D0i3) |
| [1] | `IR` | RW | 0 | Interrupt Request enable |
| [0] | `CIP` | RO | 0 | Command In Progress |

---

## IPC Doorbell Protocol

### Host → ISH Message Send

```
Host                                ISH Firmware
  │                                       │
  │  1. Write payload to OUT_MSG1-32      │
  │     (up to 128 bytes)                 │
  │                                       │
  │  2. Write INBOUND_DB with BUSY=1      │
  │     [31]=1, [30:0]=protocol cmd       │
  │──────────────────────────────────────►│
  │                                       │  3. ISH sees BUSY=1 (level interrupt)
  │                                       │  4. ISH reads IN_MSG1-32
  │                                       │  5. ISH clears BUSY via BUSY_CLEAR
  │◄──────────────────────────────────────│
  │  6. Host sees BUSY cleared            │
```

### ISH → Host Message Send

```
ISH Firmware                        Host
  │                                       │
  │  1. Write payload to OUT_MSG1-32      │
  │     (ISH-side output registers)       │
  │                                       │
  │  2. Write OUTBOUND_DB with BUSY=1     │
  │──────────────────────────────────────►│
  │                                       │  3. Host interrupt fires (PISR)
  │                                       │  4. Host reads IN_MSG1-32
  │                                       │  5. Host writes BUSY_CLEAR
  │◄──────────────────────────────────────│
  │  6. ISH sees BUSY cleared             │
```

### Interrupt Flow

The doorbell BUSY bit generates a **level-sensitive** interrupt to the IOAPIC. The interrupt remains asserted as long as BUSY=1. The receiver must:
1. Read the message payload from IN_MSG registers
2. Clear BUSY via the BUSY_CLEAR register
3. The interrupt de-asserts automatically

---

## HECI/ISHTP Message Format

### ISHTP Message Header (32-bit, over IPC payload)

```
 31      24 23     16 15       9 8      0
 ┌─────────┬─────────┬──────────┬────────┐
 │  Length  │ ME Addr │ Host Addr│  Resv  │
 │ [31:24] │ [23:16] │ [15:9]   │  [8:0] │
 └─────────┴─────────┴──────────┴────────┘
        +
 Bit [31]: Message Complete flag (MC)
```

| Bits | Field | Description |
|------|-------|-------------|
| [31] | `MC` | Message Complete — `1` = last fragment of this message |
| [30:24] | `Length` | Payload length in bytes (0–127) |
| [23:16] | `ME_Address` | ISH firmware client address |
| [15:9] | `Host_Address` | Host client address |
| [8:0] | Reserved | Must be `0` |

### Message Constraints

| Parameter | Value | Notes |
|-----------|-------|-------|
| Max IPC payload | 128 bytes | 32 × 32-bit MSG registers per direction |
| Max ISHTP single-fragment payload | 124 bytes | 128-byte IPC payload minus 4-byte ISHTP header |
| Max multi-fragment message | Platform-specific | ISHTP fragmentation across multiple IPC transactions |
| IPC channels | 8 | HOST, HOSTSPARE, CSE, PMC, CNVi, ACE, ESE, AVB |

---

## IPC Message Send/Receive (PythonSV Test Pattern)

```python
import struct
import time

# === TTL IPC Register Offsets (HOST channel, BAR0-relative) ===
IPC_PISR         = 0x000   # Peripheral Interrupt Status
IPC_PIMR         = 0x004   # Peripheral Interrupt Mask
IPC_HOST_PISR    = 0x00C   # Host-side Interrupt Status
IPC_FWSTS        = 0x034   # Firmware Status
IPC_INBOUND_DB   = 0x048   # Inbound Doorbell (host→ISH)
IPC_OUTBOUND_DB  = 0x054   # Outbound Doorbell (ISH→host)
IPC_OUT_MSG_BASE = 0x060   # Outbound MSG1 (host writes payload here)
IPC_IN_MSG_BASE  = 0x0E0   # Inbound MSG1 (host reads ISH payload here)
IPC_BUSY_CLEAR   = 0x378   # Busy Clear register
IPC_D0I3C        = 0x6D0   # D0i3 Control

IPC_DB_BUSY      = (1 << 31)  # Doorbell BUSY bit

ISHTP_HEADER_MC  = (1 << 31)  # Message Complete bit in ISHTP header

def build_ishtp_header(host_addr, me_addr, length, is_complete=True):
    """Build a 32-bit ISHTP message header."""
    header = 0
    header |= (length    & 0x7F) << 24
    header |= (me_addr   & 0xFF) << 16
    header |= (host_addr & 0x7F) << 9
    if is_complete:
        header |= ISHTP_HEADER_MC
    return header

def ipc_send_message(pch_ish, host_addr, me_addr, payload: bytes):
    """Send an ISHTP message via IPC doorbell/mailbox (HOST channel)."""
    assert len(payload) <= 124, "Max 124 bytes (128 - 4 byte ISHTP header)"

    # Build ISHTP header
    header = build_ishtp_header(host_addr, me_addr, len(payload), is_complete=True)

    # Wait for doorbell not busy
    deadline = time.time() + 2.0
    while time.time() < deadline:
        db = pch_ish.mem.read32(IPC_INBOUND_DB)
        if not (db & IPC_DB_BUSY):
            break
        time.sleep(0.001)
    else:
        raise TimeoutError("IPC doorbell still BUSY — previous message not consumed")

    # Write ISHTP header to OUT_MSG1
    pch_ish.mem.write32(IPC_OUT_MSG_BASE, header)

    # Write payload to OUT_MSG2..OUT_MSG32 (offset 0x064, 0x068, ...)
    for i in range(0, len(payload), 4):
        chunk = payload[i:i+4].ljust(4, b'\x00')
        pch_ish.mem.write32(IPC_OUT_MSG_BASE + 4 + i, struct.unpack("<I", chunk)[0])

    # Ring doorbell: set BUSY=1
    pch_ish.mem.write32(IPC_INBOUND_DB, IPC_DB_BUSY)

def ipc_recv_message(pch_ish, timeout_sec=2.0):
    """Receive an ISHTP message from ISH via IPC doorbell."""
    deadline = time.time() + timeout_sec

    # Wait for ISH to ring outbound doorbell (BUSY=1)
    while time.time() < deadline:
        db = pch_ish.mem.read32(IPC_OUTBOUND_DB)
        if db & IPC_DB_BUSY:
            break
        time.sleep(0.01)
    else:
        raise TimeoutError("IPC receive timeout — no message from ISH")

    # Read ISHTP header from IN_MSG1
    header = pch_ish.mem.read32(IPC_IN_MSG_BASE)
    length = (header >> 24) & 0x7F
    is_mc  = bool(header & ISHTP_HEADER_MC)

    # Read payload from IN_MSG2..IN_MSGn
    dwords = (length + 3) // 4
    payload_dwords = []
    for i in range(dwords):
        payload_dwords.append(pch_ish.mem.read32(IPC_IN_MSG_BASE + 4 + (i * 4)))
    payload = b"".join(struct.pack("<I", d) for d in payload_dwords)[:length]

    # Clear BUSY via BUSY_CLEAR register
    pch_ish.mem.write32(IPC_BUSY_CLEAR, 1)

    return header, payload

def ipc_check_fw_status(pch_ish):
    """Read ISH firmware status register."""
    fwsts = pch_ish.mem.read32(IPC_FWSTS)
    return {
        "raw": hex(fwsts),
        "fw_ready": bool(fwsts & 0x1),
    }
```

---

## HECI Connection Management

### Client Enumeration (Host Bus Message Protocol — HBM)

```
Host                                    ISH Firmware
  │                                           │
  │──── HOST_START_REQ ──────────────────────►│  Host signals ready
  │◄─── HOST_START_RES ───────────────────────│  ISH acknowledges
  │                                           │
  │──── ENUM_CLIENTS_REQ ────────────────────►│  Request client list
  │◄─── ENUM_CLIENTS_RES ─────────────────────│  Returns bitmap of client IDs
  │                                           │
  │──── CLIENT_PROPERTIES_REQ (ID=N) ────────►│  Get properties for client N
  │◄─── CLIENT_PROPERTIES_RES ────────────────│  Returns UUID, max_msg_len, etc.
  │  (repeat for each client)                 │
  │                                           │
  │──── CONNECT_CLIENT_REQ (ID=N) ───────────►│  Connect to client N
  │◄─── CONNECT_CLIENT_RES ───────────────────│  Returns assigned host address
  │                                           │
  │  ← Normal message exchange begins →       │
```

All HBM messages are sent as ISHTP messages over the IPC doorbell/mailbox (HOST channel). The HBM uses address 0 (ME_Address=0, Host_Address=0).

### HBM Message Types

| Command | Value | Direction | Description |
|---------|-------|-----------|-------------|
| `HOST_START_REQ` | `0x01` | H→ISH | Host driver ready |
| `HOST_START_RES` | `0x81` | ISH→H | ISH acknowledges |
| `ENUM_CLIENTS_REQ` | `0x04` | H→ISH | Request client enumeration |
| `ENUM_CLIENTS_RES` | `0x84` | ISH→H | Client list response |
| `CLIENT_PROPERTIES_REQ` | `0x05` | H→ISH | Request client properties |
| `CLIENT_PROPERTIES_RES` | `0x85` | ISH→H | Client properties response |
| `CONNECT_CLIENT_REQ` | `0x06` | H→ISH | Connect to client |
| `CONNECT_CLIENT_RES` | `0x86` | ISH→H | Connection response |
| `DISCONNECT_CLIENT_REQ` | `0x07` | H→ISH | Disconnect from client |
| `DISCONNECT_CLIENT_RES` | `0x87` | ISH→H | Disconnect response |
| `FLOW_CONTROL` | `0x08` | Both | Flow control credit |

### Client Properties Structure

```c
struct ish_client_properties {
    uint8_t  client_id;
    uint8_t  reserved[3];
    uint8_t  protocol_name[16]; /* UUID */
    uint8_t  protocol_version;
    uint8_t  max_number_of_connections;
    uint8_t  fixed_address;
    uint8_t  single_recv_buf;
    uint32_t max_msg_length;
};
```

---

## ISHTP Flow Control

ISHTP uses a credit-based flow control mechanism to prevent buffer overflow.

### Flow Control Messages

```
Host                                    ISH Firmware
  │                                           │
  │  After connection established:            │
  │◄─── FLOW_CONTROL (credits=N) ─────────────│  ISH grants N send credits to host
  │                                           │
  │──── DATA_MESSAGE (payload) ──────────────►│  Host sends (uses 1 credit)
  │──── DATA_MESSAGE (payload) ──────────────►│  Host sends (uses 1 credit)
  │  ... (repeat N times) ...                 │
  │                                           │
  │◄─── FLOW_CONTROL (credits=M) ─────────────│  ISH refreshes credits
  │                                           │
  │──── FLOW_CONTROL (credits=K) ────────────►│  Host grants credits to ISH
  │◄─── DATA_MESSAGE (sensor data) ───────────│  ISH sends sensor data
```

### Flow Control Rules
- A sender **must not** send a message unless it has at least 1 credit
- Credits are non-accumulating per grant (each FLOW_CONTROL message sets the credit count, not adds)
- Initial credit grant happens after CONNECT_CLIENT handshake
- Separate credits for each direction (host→ISH and ISH→host)

---

## IPC Protocol Timing

### Doorbell Transaction Timing (TTL)

| Phase | Typical Duration | Maximum | Notes |
|-------|-----------------|---------|-------|
| Payload write (32 DWORDs) | ~1 µs | 5 µs | MMIO writes to MSG registers |
| Doorbell assert → ISH interrupt | ~1 µs | 10 µs | Level-sensitive via IOAPIC |
| ISH FW processing | 10–100 µs | 1 ms | Depends on FW load |
| ISH BUSY_CLEAR | ~1 µs | 5 µs | Single register write |
| Total round-trip (host→ISH→host) | ~50 µs | 2 ms | Including ISH response |

### Back-to-Back Message Rate
- Maximum sustained: ~10,000 msg/sec (limited by ISH FW processing)
- Sensor data typical: 100–2000 msg/sec depending on ODR and sensor count

---

## Error Conditions & Recovery

| Error | Symptom | Root Cause | Recovery |
|-------|---------|------------|----------|
| `IPC_TIMEOUT` | Doorbell BUSY not cleared | ISH FW hang, D0i3 without drain | Check `FWSTS` at 0x034, trigger ISH reset |
| `DOORBELL_STUCK` | BUSY=1 persists > 2 seconds | ISH not consuming messages | Write BUSY_CLEAR register; if persists, full ISH reset |
| `INVALID_CLIENT_ID` | `CONNECT_CLIENT_RES` error | Wrong ME address or client not registered | Re-enumerate clients, verify UUID |
| `CONNECTION_REFUSED` | `CONNECT_CLIENT_RES` = rejected | Max connections reached or client busy | Disconnect existing connections |
| `MESSAGE_TRUNCATED` | Incomplete payload | MC bit set prematurely | Check length field in ISHTP header |
| `D0I3_STALL` | D0I3C.CIP stuck at 1 | D0i3 transition hung | Check PMC sideband, timeout and reset |

### IPC Reset Procedure

```python
def ipc_reset(pch_ish):
    """Perform an ISH IPC reset and re-initialize."""
    import time

    # Step 1: Check current firmware status
    fwsts = pch_ish.mem.read32(IPC_FWSTS)
    print(f"FWSTS before reset: {hex(fwsts)}")

    # Step 2: Force clear any stuck doorbell
    pch_ish.mem.write32(IPC_BUSY_CLEAR, 1)
    time.sleep(0.01)

    # Step 3: Clear interrupt status
    pisr = pch_ish.mem.read32(IPC_PISR)
    pch_ish.mem.write32(IPC_PISR, pisr)  # W1C

    host_pisr = pch_ish.mem.read32(IPC_HOST_PISR)
    pch_ish.mem.write32(IPC_HOST_PISR, host_pisr)  # W1C

    # Step 4: If ISH is in D0i3, bring it out first
    d0i3c = pch_ish.mem.read32(IPC_D0I3C)
    if d0i3c & (1 << 2):  # D0i3 bit set
        d0i3c &= ~(1 << 2)  # Clear D0i3
        pch_ish.mem.write32(IPC_D0I3C, d0i3c)
        # Wait for CIP to clear
        deadline = time.time() + 1.0
        while time.time() < deadline:
            if not (pch_ish.mem.read32(IPC_D0I3C) & 0x1):  # CIP=0
                break
            time.sleep(0.01)

    # Step 5: Wait for FW ready
    deadline = time.time() + 5.0
    while time.time() < deadline:
        fwsts = pch_ish.mem.read32(IPC_FWSTS)
        if fwsts & 0x1:  # FW ready
            print(f"ISH FW ready after reset: FWSTS={hex(fwsts)}")
            return True
        time.sleep(0.1)

    print("ISH FW did not recover after reset")
    return False
```

---

## Validation Points

### IPC Doorbell Transport
- [ ] Doorbell BUSY bit [31] correctly toggles: set by sender, cleared by receiver
- [ ] All 32 MSG registers (128 bytes) accessible for payload read/write
- [ ] Level-sensitive interrupt asserts while BUSY=1 and de-asserts when cleared
- [ ] Back-to-back doorbell transactions complete without BUSY stuck
- [ ] BUSY_CLEAR register properly clears the doorbell BUSY bit
- [ ] FWSTS register (0x034) reports correct firmware status at each boot phase

### IPC Channel Isolation
- [ ] HOST channel (0x000) operates independently from sideband channels
- [ ] CSE channel (0x1000) IPC does not interfere with HOST channel
- [ ] PMC channel (0x2000) IPC does not interfere with HOST channel
- [ ] Each channel's PISR/PIMR correctly masks/reports per-channel interrupts

### Client Enumeration
- [ ] `ENUM_CLIENTS_RES` returns non-zero client bitmap
- [ ] All expected sensor clients present (HID sensor client UUID found)
- [ ] `CLIENT_PROPERTIES_RES` returns valid `max_msg_length`
- [ ] Connection succeeds with assigned host address

### Flow Control
- [ ] ISH sends initial `FLOW_CONTROL` after connection
- [ ] Host cannot overflow ISH buffer (credits properly enforced)
- [ ] Credits refresh after ISH processes messages
- [ ] Bidirectional flow control works correctly

### D0i3 Transitions via D0I3C
- [ ] Writing D0I3C[2]=1 initiates D0i3 entry, CIP[0] goes high during transition
- [ ] CIP[0] returns to 0 after transition completes
- [ ] RR[3] is set after D0i3 exit indicating restore required
- [ ] Pending IPC messages are drained before D0i3 entry completes

### Error Recovery
- [ ] BUSY_CLEAR recovers stuck doorbell within 10 ms
- [ ] ISH reset restores FW ready state (FWSTS bit 0 = 1)
- [ ] Communication resumes normally after reset
- [ ] D0i3 stall (CIP stuck) recoverable via timeout + reset

---

## Linux Kernel Reference (Public)

| File | Content |
|------|---------|
| `ipc/ipc.c` | IPC doorbell send/receive, interrupt handler, BUSY/BUSY_CLEAR |
| `ipc/ipc.h` | IPC register offset definitions, doorbell bit masks |
| `ishtp/hbm.c` | HBM (Host Bus Message) protocol implementation |
| `ishtp/hbm.h` | HBM message type definitions, client properties struct |
| `ishtp/client.c` | ISHTP client connection management, flow control |
| `ishtp/transport.h` | ISHTP message header format |

> Repo: https://github.com/torvalds/linux/tree/master/drivers/hid/intel-ish-hid
