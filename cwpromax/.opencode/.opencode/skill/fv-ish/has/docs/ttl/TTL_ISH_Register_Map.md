# TTL ISH5p9 Register Map & MMIO Definitions

> **Source**: ISH5p9 HAS (SIP_ISH5p9_HAS.html) via Co-De Sign
> **Extracted**: 2026-03-16

---

## 1. MMIO Register Map

All registers are in the Primary power well and reset by PLTRST#.

| Offset Range | Name | Access | Description |
|-------------|------|--------|-------------|
| 0x000-0x007 | General Capabilities and ID | RO | ISH capabilities and identification |
| 0x008-0x00F | Reserved | - | - |
| 0x010-0x017 | General Config | RW | General configuration |
| 0x018-0x01F | Reserved | - | - |
| 0x020-0x027 | General Interrupt Status | RW1C | Interrupt status, write to clear |
| 0x028-0x0EF | Reserved | - | - |
| 0x0F0-0x0F7 | Main Counter Value | RW | Main timer counter |
| 0x0F8-0x0FF | Reserved | - | - |
| 0x100-0x107 | Timer 0 Config and Capabilities | RW | Timer 0 configuration |
| 0x108-0x10F | Timer 0 Comparator Value | RW | Timer 0 comparator |
| 0x110-0x11F | Timer 0 FSB Interrupt Route | RW | Timer 0 interrupt routing |
| 0x120-0x127 | Timer 1 Config and Capabilities | RW | Timer 1 configuration |
| 0x128-0x12F | Timer 1 Comparator Value | RW | Timer 1 comparator |
| 0x130-0x13F | Timer 1 FSB Interrupt Route | RW | Timer 1 interrupt routing |
| ... | Timer 2-6 | RW | Follow same pattern at +0x40 each |
| 0x1E0-0x1E7 | Timer 7 Config and Capabilities | RW | Timer 7 configuration |
| 0x1E8-0x1EF | Timer 7 Comparator Value | RW | Timer 7 comparator |
| 0x1F0-0x1FF | Timer 7 FSB Interrupt Route | RW | Timer 7 interrupt routing |
| 0x200-0x3FF | Reserved | - | Reserved for Timers 8-31 |

**Timer Register Stride**: Each timer uses 0x40 bytes. Timer N base = 0x100 + (N * 0x40)

---

## 2. Bit Field Definitions

### General Capabilities (Offset 0x000)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 31:16 | Device ID | RO | Platform-specific | ISH Device Identification |
| 15:0 | Capability Bits | RO | Platform-specific | ISH capability flags |

### General Config (Offset 0x010)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 0 | Enable | RW | 0 | Global ISH enable |
| 1 | Interrupt Enable | RW | 0 | Global interrupt enable |
| 31:2 | Reserved | - | 0 | - |

### General Interrupt Status (Offset 0x020)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 7:0 | Timer Interrupts | RW1C | 0 | Timer interrupt status (1 bit per timer) |
| 31:8 | Reserved | - | 0 | - |

### Timer N Config (Offset 0x100 + N*0x40)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 0 | Timer Enable | RW | 0 | Enable this timer |
| 1 | Periodic Mode | RW | 0 | 0=One-shot, 1=Periodic |
| 31:2 | Reserved | - | 0 | - |

### Timer N Comparator (Offset 0x108 + N*0x40)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 31:0 | Comparator Value | RW | 0 | Timer comparator value |

### Timer N FSB Interrupt (Offset 0x110 + N*0x40)

| Bits | Name | Access | Reset | Description |
|------|------|--------|-------|-------------|
| 7:0 | Interrupt Vector | RW | 0 | Interrupt vector number |
| 31:8 | Reserved | - | 0 | - |

---

## 3. IPC Doorbell and Mailbox Registers

Per channel (ISH<->CSME, ISH<->PMC, ISH<->Host):

| Offset | Name | Access | Description |
|--------|------|--------|-------------|
| 0x0000 | Doorbell | RW | Source writes to signal message. Bit 31=BUSY, Bits 30:0=Command |
| 0x0004 | Doorbell Mirror | RW | Destination writes to acknowledge |
| 0x003C | Control & Status | RW | Out-of-band status/control |
| 0x0040-0x00BC | Data Registers | RW | Mailbox data payload (32 DW) |

### Doorbell Register Bit Fields

| Bits | Name | Description |
|------|------|-------------|
| 31 | BUSY | Set by source, cleared by destination when message processed |
| 30:0 | Command | IPC command code |

### Communication Flow

- **Host-to-ISH**: Host writes to ISH Doorbell and Mailbox registers
- **ISH-to-Host**: ISH writes to Host Doorbell Mirror and Mailbox registers

---

## 4. DMA Channel Registers

| Offset | Name | Access | Description |
|--------|------|--------|-------------|
| 0x400 | DMA Channel 0 Control | RW | DMA channel control |
| 0x404 | DMA Channel 0 Src | RW | Source address |
| 0x408 | DMA Channel 0 Dst | RW | Destination address |
| 0x40C | DMA Channel 0 Size | RW | Transfer size |

### DMA Control Bit Fields

| Bits | Name | Description |
|------|------|-------------|
| 0 | Enable | Enable DMA channel |
| 1 | Interrupt | Enable transfer complete interrupt |
| 15:2 | Transfer Size | Transfer size configuration |

---

## 5. Power Management Registers

| Offset | Name | Access | Description |
|--------|------|--------|-------------|
| 0x500 | Power Control | RW | Power gating, clock gating control |
| 0x504 | Power Status | RO | Current power state |
| 0x508 | Wake Event | RW | Wake event configuration |

### Power Control Bit Fields

| Bits | Name | Description |
|------|------|-------------|
| 0 | Enable | Power management enable |
| 1 | Clock Gate | Enable clock gating |
| 2 | Power Gate | Enable power gating |

### Power Status Bit Fields

| Bits | Name | Description |
|------|------|-------------|
| 1:0 | Current State | Current power state |
| 2 | Wake Pending | Wake event pending |

### Wake Event Bit Fields

| Bits | Name | Description |
|------|------|-------------|
| 7:0 | Wake Sources | Wake source enable mask |

---

## Notes

- All registers are in the Primary power well, reset by PLTRST#
- Timer registers follow a stride of 0x40 per timer (up to 8 timers: Timer 0-7)
- IPC channels exist per communication peer (Host, CSME, PMC)
- DMA and Power Management register offsets are relative to ISH MMIO base
- TODO: Cross-reference with actual ISH register header files from PythonSV/validation repo
