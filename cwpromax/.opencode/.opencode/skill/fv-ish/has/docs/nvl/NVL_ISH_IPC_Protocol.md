# NVL ISH 5.8 IPC/HECI Protocol Reference
## Source: Co-De Sign (SIP_ISH5p8_HAS + SIP_ISH_Integration_HAS + Embedded Engines IPC Arch Spec)

### IPC Channel Architecture
ISH 5.8 uses IPC (Inter-Processor Communication) doorbell/mailbox protocol — NOT classic HECI circular buffers.

#### IPC Channels
| Channel | Peer | Type | Description |
|---------|------|------|-------------|
| HOST | Main CPU | MEM-mapped | Primary host communication |
| CSE/CSME | Security Engine | MSG-based | Firmware loading, authentication |
| PMC | Power Mgmt Controller | MSG-based | Power state coordination |
| ACE | Audio subsystem | MSG-based | Audio sensor data |
| CNVi | Connectivity | MSG-based | WiFi/BT coordination |
| WiFi | WiFi subsystem | MSG-based | Direct wireless peer comm |
| BT | Bluetooth subsystem | MSG-based | Direct BT peer comm |

### NVL IPC Register Addresses

#### Peer Communication Channels (WiFi/BT)
| Channel | Doorbell | DB Mirror | CSR | Data Registers |
|---------|----------|-----------|-----|----------------|
| PMC/WiFi | 0x10680 | 0x10684 | 0x10688 | 0x17400–0x174FF |
| ISH/WiFi | 0x10690 | 0x10694 | 0x10698 | 0x17600–0x176FF |
| ISH/BT | 0x106A0 | 0x106A4 | 0x106A8 | 0x17500–0x175FF |

#### CSE ↔ ISH Channel
| Direction | Doorbell | DB Mirror | CSR/Data Range |
|-----------|----------|-----------|----------------|
| CSE → ISH | 0x003C | 0x0000 | — |
| ISH → CSE | 0x1050 | 0x105C | 0x0040–0x00BC (ISH→CSE), 0x11E0–0x125C (CSE→ISH) |

### Doorbell Register Format
```
Bit [31]    = BUSY (1=message pending, 0=idle)
Bits [30:0] = COMMAND field (channel-specific)
```

### Doorbell Protocol (BUSY Bit Handshake)
1. **Sender** checks DBM (Doorbell Mirror) BUSY = 0
2. **Sender** writes command/data to MSG registers, sets BUSY = 1 in DBM
3. **HW** copies DBM to DB in peer
4. **Receiver** gets interrupt on BUSY 0→1 transition
5. **Receiver** reads payload from MSG registers, processes message
6. **Receiver** clears BUSY in DB
7. **HW** copies DB back to DBM in sender
8. **Sender** gets interrupt on BUSY 1→0 transition, can send next

### Message Payload
- **Data Registers**: Up to 32 registers × 32 bits = 128 bytes per channel per direction
- **Short Format**: Entire message encoded in Doorbell register [30:0]
- **Long Format**: Command in Doorbell, data payload in Data Registers

### Interrupt Routing
- BUSY set (0→1): Interrupt to receiver firmware
- BUSY cleared (1→0): Interrupt to sender firmware
- Level-sensitive to IOAPIC while BUSY = 1

### D0I3C Register
- Control/status for D0i3 entry/exit coordination
- Out-of-band signaling between ISH and peer (e.g., PMC)
- Bit fields: D0I3 Entry/Exit Request, Status/Acknowledge

### ISHTP/HBM Protocol Stack
```
┌─────────────────────┐
│   Sensor Clients    │  Application layer (SENS, cust_senscol)
├─────────────────────┤
│     ISHTP           │  ISH Transport Protocol (framing, flow control)
├─────────────────────┤
│     HBM             │  Host Bus Message (connection management)
├─────────────────────┤
│   IPC Doorbell      │  Hardware transport (doorbell + MSG registers)
└─────────────────────┘
```
- Multiple clients per channel via Client ID
- HBM handles connection setup, flow control, client enumeration

### NVL vs TTL IPC Differences
| Feature | NVL (ISH 5.8) | TTL (ISH 5.9) |
|---------|---------------|---------------|
| Doorbell mechanism | Same BUSY bit [31] | Same |
| Payload size | 128 bytes (32×32-bit) | 128 bytes (same) |
| HOST channel | MEM-mapped | MEM-mapped (same) |
| WiFi/BT channels | Explicit peer channels with addresses | Present (similar) |
| CSE↔ISH offsets | DB: 0x003C/0x1050 | Different (wrapper-based) |
| ISHTP/HBM | Same protocol stack | Same |
