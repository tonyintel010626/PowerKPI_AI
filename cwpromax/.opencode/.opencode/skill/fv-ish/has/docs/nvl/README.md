# ISH NVL HAS — Nova Lake Document Index

> **Platform**: Nova Lake (NVL)
> **Domain**: Integrated Sensor Hub (ISH)
> **Maintained by**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
> **Last Updated**: 2026-03-16
> **Status**: Populated from Co-De Sign HAS extraction (SIP_ISH5p8_HAS + SIP_ISH_Integration_HAS)

---

## Source Documents

| Source | Document Name | Access Method |
|--------|--------------|---------------|
| Co-De Sign (My Files) | `SIP_ISH5p8_HAS` | ISH 5.8 IP-level HAS |
| Co-De Sign (My Files) | `SIP_ISH_Integration_HAS` | NVL ISH integration HAS |
| docs.intel.com | `SIP_ISH5p8_Registers.html` | ISH 5.8 register spec (requires auth) |
| Co-De Sign (Projects) | `sip_ish_integration_has.html` | NVL integration HAS (project doc) |
| Co-De Sign (Projects) | `nvl_overview.html` | NVL platform overview |
| Co-De Sign (Projects) | `novalake platform firmware architecture specification.html` | NVL FW arch spec |
| Co-De Sign (Projects) | `nvl-pch-s_performance_has.html` | NVL PCH-S performance HAS |
| Co-De Sign (Projects) | `Chap44_1_NVL_PCH_PerIP_Clocks.html` | NVL per-IP clocking spec |
| Co-De Sign (Projects) | `nvl_xse_iploadingfas.html` | NVL XSE IP loading FAS |
| Co-De Sign (Projects) | `embedded engines ipc architecture spec.html` | IPC architecture spec |
| Co-De Sign (Projects) | `NVL_PCD_Energy_Reporting_HAS.html` | NVL energy reporting HAS |
| Co-De Sign (Projects) | `pmc_has.html` | PMC HAS |
| Co-De Sign (Projects) | `soc_s0ix_substates_has.html` | SoC S0ix substates HAS |

## Extracted Reference Documents

| Filename | Description | Source |
|----------|-------------|--------|
| `NVL_ISH_Architecture_Overview.md` | ISH 5.8 architecture, core, memory, IO, host interface | Co-De Sign query |
| `NVL_ISH_Power_Management.md` | D-states, SRAM PG, PMC sideband, VNN, wake events, S0ix | Co-De Sign query |
| `NVL_ISH_IPC_HECI_Protocol.md` | IPC channels, doorbell mechanism, ISHTP/HBM, register offsets | Co-De Sign query |
| `NVL_ISH_DMA_FW_Boot.md` | DMA architecture, firmware boot flow, S3 resume, capsule update | Co-De Sign query |

---

## NVL ISH Key Architecture Summary

### ISH Generation
- **ISH IP Version**: ISH 5.8
- **Processor Core**: Lakemont (LMT) 3.9 — MinuteIA-based embedded DSP/AI subsystem
- **Key differences from TTL (ISH 5.9)**: Fewer I3C (1 vs 2), SPI (1 vs 2), UART (2 vs 3) controllers

### Memory Subsystem
| Component | Size | Notes |
|-----------|------|-------|
| Boot ROM | 8 KB | Boot-loader code |
| SRAM (L2) | 640 KB | 20 banks × 32 KB, per-bank power gating |
| AON SRAM | 8 KB | Always-on RF space for deep D0i2/D0i3 PG states |
| ICache | 16 KB | Instruction cache |
| DCache | 16 KB | Data cache |

### IO Controllers
| Controller | Count | Speed | Notes |
|------------|-------|-------|-------|
| I2C | 3 | 1 Mb/s | Standard/Fast/Fast-Mode Plus |
| I3C | 1 | 25 Mb/s | HDR/DDR mode |
| SPI | 1 | 25 Mb/s | DW_apb_ssi |
| UART | 2 | 4 Mb/s | DW_apb_uart |
| GPIO | 8–12 | — | PCH-S: 12, general: 8 (muxed with other functions) |

### PCI Configuration
- **Vendor ID**: `0x8086` (Intel)
- **Device ID**: `0x6E78` (PCH-S)
- **Host Interface**: IOSF 1.2/1.3

### Clock Frequencies
- **Core Clock**: 200 MHz
- **Peripheral Clock**: 100 MHz

### IPC Channels
| Channel | Peer | Transport |
|---------|------|-----------|
| HOST | Main CPU | Memory-mapped |
| CSE/CSME | Security Engine | IOSF sideband |
| PMC | Power Management Controller | IOSF sideband |
| ACE | Audio subsystem | IOSF sideband |
| CNVi | Connectivity subsystem | IOSF sideband |
| Wi-Fi | Wireless LAN | IOSF sideband |
| BT | Bluetooth | IOSF sideband |

### NVL IPC Channel Register Addresses
| Channel | Doorbell | DB Mirror | CSR | Data Registers |
|---------|----------|-----------|-----|----------------|
| PMC/Wi-Fi | 0x10680 | 0x10684 | 0x10688 | 0x17400–0x174FF |
| ISH/Wi-Fi | 0x10690 | 0x10694 | 0x10698 | 0x17600–0x176FF |
| ISH/BT | 0x106A0 | 0x106A4 | 0x106A8 | 0x17500–0x175FF |
| CSE→ISH | 0x003C | 0x0000 | — | 0x0040–0x00BC |
| ISH→CSE | 0x1050 | 0x105C | — | 0x11E0–0x125C |

### Power States
| State | VNN | SRAM | Clock | Exit Latency | Notes |
|-------|-----|------|-------|-------------|-------|
| D0 | ON | ON | ON | — | Full power |
| D0i1 | ON | ON | Gated | ~µs | Quick idle |
| D0i2 | ON | PG | Gated | ~1.5 ms | PCE.HAE enables, HW-controlled exit |
| D0i3 | OFF | PG (saved to DRAM) | Gated | ~5 ms | VNN may be removed |
| D3 | OFF | PG (no retention) | OFF | ~ms | Full power gate |

### PMC Sideband Energy Reporting
- **Opcode**: `0x6F`
- **Tag**: `0x06`
- **SAI**: `0x34`
- **Destination Port ID**: `0xC8`
- **Source Port ID**: `0xD0`
- **ER_DATA[7:0]**: Number of active SRAM banks (`0x00` = all gated, `0x14` = all 20 active)

---

## NVL-Specific Validation Focus Areas

1. **ISH 5.8 IO controller count reduction** — Verify I3C (1), SPI (1), UART (2) enumeration and functionality vs TTL's higher counts
2. **PCH-S integration** — Validate NVL PCH-S specific GPIO muxing (12 GPIO in PCH-S config)
3. **IPC peer channels** — Validate Wi-Fi/BT IPC channels (NVL adds explicit Wi-Fi and BT as ISH peers)
4. **D0i2 exit latency** — Validate ~1.5ms exit latency meets sensor acquisition deadlines
5. **D0i3 exit latency** — Validate ~5ms exit latency and SRAM restore from DRAM
6. **Energy reporting accuracy** — Verify PMC sideband (Opcode 0x6F, Tag 0x06, SAI 0x34) reports correct active bank count
7. **S3 resume optimization** — Validate CSE hash comparison and IMR-to-SRAM fast resume path
8. **DMA root-space switching** — Validate Host DRAM vs CSE/IMR access with correct snoop settings

---

## NVL Known Issues

> Populate with NVL ISH errata and known issues as discovered during validation

| Issue | Description | Workaround | HSDES |
|-------|-------------|-----------|-------|
| *(none documented yet)* | | | |

---

## Quick Search Commands

Once HAS documents are placed in this directory, use these search commands:

```bash
# Search for HECI registers in NVL HAS
python .opencode/skill/fv-ish/has/scripts/has_search.py --query "HECI" --platform nvl

# Extract all register definitions
python .opencode/skill/fv-ish/has/scripts/has_search.py --type registers --platform nvl

# Find power management content
python .opencode/skill/fv-ish/has/scripts/has_search.py --topic power --platform nvl

# Export all DMA content to markdown
python .opencode/skill/fv-ish/has/scripts/has_search.py --topic dma --platform nvl --export-md
```
