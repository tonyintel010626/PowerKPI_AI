# TTL ISH HECI/IPC Protocol — Extracted from ISH5p9 HAS

> Source: Co-De Sign query against `SIP_ISH5p9_HAS.html` (My Files)
> Date: 2026-03-16

---

## 1. IPC Register Definitions

Each IPC channel has 4 register types:

| Register | Width | Description |
|----------|-------|-------------|
| DB (Doorbell) | 32-bit | Bit[31]=BUSY (sender sets, receiver clears), Bits[30:0]=COMMAND |
| DBM (Doorbell Mirror) | 32-bit | Same format as DB, hardware copies between source/dest |
| CSR (Control & Status) | 32-bit | Out-of-band status/reset/power indications |
| Mailbox Data | Up to 32×32-bit | Per-channel payload registers for long-format messages |

## 2. HECI Message Header Format

```c
struct heci_message_header {
    uint32_t command_id;
    uint32_t reserved_or_status;
    uint32_t size;
    uint8_t  msg_content[0];  // Variable-length payload
};
```

## 3. IPC Doorbell Bit Fields (Standard Long Format)

| Bits | Field | Description |
|------|-------|-------------|
| [31] | BUSY | 1=message pending, sender sets, receiver clears |
| [30:29] | Reserved/IP-specific | Platform-dependent usage |
| [28] | CUSTOM_FORMAT | 0=standard format, 1=custom format |
| [27] | SHORT_FORMAT | 1=short format (no mailbox), 0=long format (uses mailbox) |
| [21] | CMD_ID | Command identifier |
| [15:13] | CLIENT_ID | Client/channel identifier |
| [9] | PAYLOAD_SIZE | Size of mailbox payload |

## 4. Message Flow Sequence (ISH→Host Example)

```
1. Check DBM BUSY=0 (channel idle)
2. Write payload to mailbox data registers
3. Write command + BUSY=1 to DBM
4. HW copies DBM → DB at destination
5. Destination interrupt fires
6. Destination reads payload from mailbox
7. Destination clears BUSY in DB
8. HW copies DB back to DBM at source
9. Source sees BUSY=0 (transfer complete)
```

### Host→ISH Flow (reverse direction):
```
1. Host checks DB BUSY=0
2. Host writes payload to ISH mailbox
3. Host writes command + BUSY=1 to DB
4. HW copies DB → DBM at ISH
5. ISH interrupt fires
6. ISH FW reads payload
7. ISH FW clears BUSY in DBM
8. HW copies DBM back to DB at host
9. Host sees BUSY=0
```

## 5. IPC Command Opcodes

| Opcode | Name | Description |
|--------|------|-------------|
| 0x00 | NOP | No operation |
| 0x01 | PECI | PECI proxy command |

ISH-to-PMC specific: NOP (0x0), PECI (0x1). Additional opcodes defined per client/protocol.

## 6. IPC Channel Register Base Addresses (NVL PCH)

| Channel | DB Offset | DBM Offset | CSR Offset | Data Range |
|---------|-----------|------------|------------|------------|
| ISH↔PMC | 0x10680 | 0x10684 | 0x10688 | 0x17400–0x174FF |
| ISH↔WiFi | 0x10690 | 0x10694 | 0x10698 | 0x17600–0x176FF |
| ISH↔BT | 0x106A0 | 0x106A4 | 0x106A8 | 0x17500–0x175FF |
| ISH↔CSME | Platform-specific | Platform-specific | Platform-specific | Platform-specific |
| ISH↔Host (HECI) | Platform-specific | Platform-specific | Platform-specific | Platform-specific |

## 7. Interrupt Handling

- **Sending**: Hardware triggers interrupt at destination when BUSY=1 is written to doorbell
- **Receiving**: Firmware reads message, clears BUSY bit, triggers interrupt back to sender via DBM
- **Routing**: `client_id` field in doorbell routes interrupts to the correct handler
- **Flow control**: BUSY bit acts as hardware semaphore — sender must wait for BUSY=0 before sending next message

---

## Validation Points

- Verify doorbell BUSY handshake completes for all IPC channels
- Test both short-format (no mailbox) and long-format (with mailbox) messages
- Verify interrupt generation on doorbell write
- Test all IPC channels: ISH↔PMC, ISH↔WiFi, ISH↔BT, ISH↔CSME, ISH↔Host
- Verify CSR register reflects correct power/reset state
- Test mailbox data register read/write for all 32 DW per channel
