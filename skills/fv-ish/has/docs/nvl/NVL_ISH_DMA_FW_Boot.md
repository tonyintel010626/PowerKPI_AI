# NVL ISH 5.8 DMA Architecture & Firmware Boot Flow
## Source: Co-De Sign (SIP_ISH5p8_HAS + SIP_ISH_Integration_HAS)

## DMA Architecture

### Channel Configuration
- Multiple DMA channels (typically 4–8 for ISH-class IP)
- Each channel independently configurable for transfer mode, root-space, and snoop

### Transfer Modes
| Mode | Description |
|------|-------------|
| Int → Int | SRAM to SRAM (internal) |
| Int → Ext | SRAM to Host DRAM or IMR |
| Ext → Int | Host DRAM or IMR to SRAM |
| Ext → Ext | Both endpoints via DMA fabric |

### DMA_DMA_MODE Register Key Fields
| Bit(s) | Field | Description |
|--------|-------|-------------|
| 31 | ACTIVE | DMA channel active |
| 30 | SRC_NON_SNOOP | 1=non-snoop, 0=snoop (IMR must be non-snooped) |
| 29 | DST_NON_SNOOP | 1=non-snoop, 0=snoop |
| 27 | SRC_DEST_ID | Source: fabric vs implicit decode |
| 26 | DST_DEST_ID | Destination: fabric vs implicit decode |
| 17 | SRC_ADDR_MODE | 0=Linear, 1=Fixed |
| 16 | DST_ADDR_MODE | 0=Linear, 1=Fixed |
| 13 | FIRST_IN_CHAIN | First descriptor in linked list |
| 12 | LAST_IN_CHAIN | Last descriptor in linked list |
| 11:8 | PRIOR_DMA | Priority of DMA channel |
| 6:4 | MAX_OUT_REQ | Max outstanding requests (up to 4) |
| — | DMA_ROOTSPACE | 0=Host (DRAM), 1=CSE (IMR) |

### Linked-List (Scatter-Gather) Mode
- Supported via FIRST_IN_CHAIN and LAST_IN_CHAIN bits
- Allows chained DMA descriptors for non-contiguous transfers
- PRIOR_DMA[11:8] sets priority ordering

### Root-Space Selection
| Value | Target | Use Case |
|-------|--------|----------|
| 0 (Host) | DRAM | Normal host memory access |
| 1 (CSE) | IMR | Firmware loading, secure transfers |

### Snoop Control
- **IMR access MUST be non-snooped** (SRC_NON_SNOOP/DST_NON_SNOOP = 1)
- Host DRAM access typically snooped for cache coherency

### Performance
- Max payload size: 64 bytes (SoC PSF fabric limitation)
- Max outstanding requests: 4
- Endian swap: Supported for 32-bit words
- OBFF support: For opportunistic DMA transfers
- MSI-X vectors: Up to 4

### NVL vs TTL DMA Differences
| Feature | NVL (ISH 5.8) | TTL (ISH 5.9) |
|---------|---------------|---------------|
| Control Register | DMA_DMA_MODE | DMA_CTL_CH0–CH7 at 0x10101000 |
| Root-Space | DMA_ROOTSPACE: 0=Host, 1=CSE | RD_RS/WR_RS bits [4:3]/[6:5]: RS0=Host, RS3=IMR |
| Snoop bits | Bits 30/29 | Bits 9/8 (RD_NON_SNOOP/WR_NON_SNOOP) |
| Chaining | FIRST_IN_CHAIN/LAST_IN_CHAIN (13/12) | LLI_MODE bit 10 |
| Transfer mode | Implied by SRC/DST addressing | TRANSFER_MODE bits [1:0] |

---

## Firmware Boot Flow

### Stage 1: Boot ROM
1. On reset, ISH executes from internal 8 KB Boot ROM
2. ROM initiates reset synchronization with CSE
3. ROM may DMA BUP from IMR to SRAM
4. ROM advertises LTR = 2 ms before DMA, then sets to infinite after
5. ROM size: 8 KB maximum

### Stage 2: BUP Loading (by CSE)
1. CSE locates ISH BUP partition in NVM flash
2. CSE authenticates BUP (Intel-signed, IPL meta format)
3. CSE loads BUP to ISH IMR (offset 0)
4. BUP maximum size: 64 KB
5. CSE may also load "doomsday" ROM patch script

### Stage 3: Main FW Loading (by Host Driver)
1. Host OS ISH driver copies main firmware to ISH IMR
2. CSE receives IPC command to authenticate firmware
3. CSE verifies signature (Intel or OEM signed)
4. On success, CSE notifies ISH and host driver
5. Main firmware loaded from IMR to SRAM for execution
6. Main FW maximum size: 1.5 MB

### Stage 4: S3 Resume Optimization
1. On S3 resume, CSE checks if ISH main FW in IMR matches saved hash
2. If hash match: copies directly from IMR to SRAM (skip NVM reload) — fast resume
3. If hash mismatch: reloads from NVM (cold boot path)
4. CSE saves uncompressed ISH main FW in IMR for this optimization

### Capsule Update
- CSE supports firmware update for ISH code in CSE-managed flash
- CSE reads update from ISH UMA
- CSE forwards configuration/debug info to ISH

### Boot Flow Summary
```
Power-On Reset
    │
    ▼
Boot ROM (8KB)
    │ LTR=2ms, DMA BUP from IMR
    ▼
BUP (64KB max, Intel-signed)
    │ CSE authenticates, loads to IMR offset 0
    ▼
Main FW (1.5MB max, Intel/OEM-signed)
    │ Host driver copies to IMR, CSE verifies
    ▼
ISH Operational
    │
    ▼ (S3 suspend)
S3 Resume
    │ CSE hash check: match=fast resume, mismatch=cold boot
    ▼
ISH Operational
```
