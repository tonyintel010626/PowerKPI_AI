# NVL ISH 5.8 Architecture Overview
## Source: Co-De Sign (SIP_ISH5p8_HAS + SIP_ISH_Integration_HAS)

### IP Overview
- **IP Version**: ISH 5.8
- **Processor Core**: Lakemont (LMT) 3.9 (MinuteIA-based)
- **Platform**: Nova Lake (NVL) PCH-S

### Memory Subsystem
| Component | Size | Notes |
|-----------|------|-------|
| Boot ROM | 8 KB | Boot-loader code |
| SRAM (L2) | 640 KB | 20 banks × 32 KB, pageable, per-bank power gating |
| AON RF SRAM | 8 KB | Code retention in deep D0i2/D0i3 PG states |
| ICache | 16 KB | Instruction cache |
| DCache | 16 KB | Data cache |

### Clock Configuration
- Primary: 200 MHz
- Low-power: 100 MHz

### IO Controllers
| Controller | Count | Max Speed | Notes |
|------------|-------|-----------|-------|
| I2C | 3 | 1 Mb/s | Sensor interfaces |
| I3C | 1 | 25 Mb/s | HDR/DDR mode |
| SPI | 1 | 25 Mb/s | Sensor/external flash |
| UART | 2 | 4 Mb/s | Debug/sensor comm |
| GPIO | 8-12 | N/A | PCH-S=12, general=8, muxed with other GPIO |

### Host Interface
- **Bus**: IOSF 1.2/1.3 (NOT PCIe)
- **Communication**: IPC doorbell/mailbox
- **PCI Device ID**: 0x6E78 (PCH-S)
- **PCI Vendor ID**: 0x8086

### Features
- Clock/power gating (all blocks including SRAMs)
- Always-On/Always-Sensing in S0/S0ix
- Peer communication: eSPI, WiFi, Security, Audio
- DTF with MIP SyS-T trace
- Hammock Harbor time synchronization
- IPC channels: Host, CSME, PMC, ACE, CNVi, WiFi/BT

### NVL vs TTL (ISH 5.9) Differences
| Feature | NVL (ISH 5.8) | TTL (ISH 5.9) |
|---------|---------------|---------------|
| IP Version | 5.8 | 5.9 |
| Core | LMT 3.9 | LMT 3.8/3.9 |
| I3C Controllers | 1 | 2 |
| SPI Controllers | 1 | 2 |
| UART Controllers | 2 | 3 |
| PCI Device ID | 0x6E78 | 0xE445 |
| ICache/DCache | 16 KB each | Not specified in HAS |
| ROM/SRAM/AON | 8KB/640KB/8KB | 8KB/640KB/8KB (same) |
| Clock | 200/100 MHz | 200/100 MHz (same) |
| I2C | 3 | 3 (same) |
