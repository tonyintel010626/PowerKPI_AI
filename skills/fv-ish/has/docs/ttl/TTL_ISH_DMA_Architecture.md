# TTL ISH DMA Architecture
## Source: Co-De Sign ISH5p9 HAS Document

## 1. DMA Channels

- Multiple channels (typically 4+), platform-dependent
- Each independently configurable for different transfer types and priorities
- Supports memory-to-memory and peripheral-to-memory transfers

## 2. PRD Table (Descriptor Format)

Each PRD entry is 16 bytes (128 bits):

```
Bit Field Layout:
[127:91] Reserved
[90:89]  HW Status: 0=Reset, 1=Success, 2=Error, 3=Rx Buffer Overflow
[88]     EOP: Last entry in table
[87:64]  Length: Transfer length (1-based, max 16MB-1, must be 4KB aligned except last)
[63]     IOC: Triggers interrupt on PRD completion
[62:54]  Reserved
[53:0]   Destination Address: 64-bit, minimum 1KB alignment
```

- Ring Buffer: PRD entries in table, HW processes sequentially with wrap-around

## 3. Address Spaces

- System memory (DRAM)
- ISH SRAM
- Peripheral FIFOs
- Linear and fixed addressing modes
- Minimum 1KB alignment, 4KB aligned sizes except last PRD

## 4. Transfer Modes

- Memory-to-Memory
- Peripheral-to-Memory
- Memory-to-Peripheral
- Chaining (multiple ops linked via descriptors)

## 5. DMA Channel Registers (Per Channel)

| Offset | Register | Description |
|--------|----------|-------------|
| 0x400 | DMA Channel 0 Control | Start/stop, status, interrupt enable, error status |
| 0x404 | DMA Channel 0 Src | Source address (64-bit) |
| 0x408 | DMA Channel 0 Dst | Destination address (64-bit) |
| 0x40C | DMA Channel 0 Size | Transfer size (bytes) |
| 0x410 | DMA Channel 0 Mode | Mode configuration (see bit fields below) |

### DMA_MODE Register Bit Fields

| Bit | Field | Description |
|-----|-------|-------------|
| [31] | ACTIVE | 1=DMA active, 0=idle |
| [30] | SRC_NON_SNOOP | 1=Non-snoop, 0=Snoop |
| [29] | DST_NON_SNOOP | 1=Non-snoop, 0=Snoop |
| [17] | SRC_ADDR_MODE | 0=Linear, 1=Fixed |
| [16] | DST_ADDR_MODE | 0=Linear, 1=Fixed |
| [13] | FIRST_IN_CHAIN | 1=First DMA in chain |
| [12] | LAST_IN_CHAIN | 1=Last DMA in chain |
| [6:4] | MAX_OUT_REQ | Maximum outstanding requests |

## 6. Interrupt Handling

- IOC bit[63] in PRD triggers interrupt on completion
- DMA generates interrupt to ISH core on transfer/chain completion or error
- Status bits in control register and PRD indicate completion/error/overflow
- SW clears status and prepares next transfer
