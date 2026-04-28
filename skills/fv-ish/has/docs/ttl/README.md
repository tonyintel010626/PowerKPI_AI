# TTL (Titan Lake) ISH HAS Documents

## Source
- **Platform**: Titan Lake (TTL)
- **IP Version**: ISH 5.9 (SIP_ISH5p9)
- **Extracted From**: Intel Co-De Sign (chat.co-design.intel.com)
- **Source Documents**: 
  - `iparch/ish/HW/ISH5p9/HAS/SIP_ISH5p9_HAS.html` — ISH 5.9 Hardware Architecture Specification
  - `iparch/ish/fas/BIOS/ISH Requirement to BIOS.html` — ISH BIOS Requirements
  - `ish_wrapper_host.pdf` — HOST wrapper OSXML register spec (849 pages, from SharePoint IPDevISH/TTL/OSXML)
  - `ish_mia_bfm_rdl_top.pdf` — MIA internal OSXML register spec (30 sections, from SharePoint IPDevISH/TTL/OSXML)

## Document Inventory

| File | Topic | Source Doc | Key Content |
|------|-------|-----------|-------------|
| `TTL_ISH_Architecture_Overview.md` | Architecture Overview | ISH5p9 HAS | IP version, block diagram, LMT core, IO controllers, IOSF interface, clocking |
| `TTL_ISH_Register_Map.md` | Register Maps & MMIO | ISH5p9 HAS | MMIO offsets, bit fields, timer registers, IPC registers, DMA registers |
| `TTL_ISH_HECI_IPC_Protocol.md` | HECI/IPC Protocol | ISH5p9 HAS | Doorbell/mailbox registers, message formats, IPC channels, command opcodes |
| `TTL_ISH_Sensor_Framework.md` | Sensor Framework | ISH5p9 HAS | Sensor types, I2C/I3C/SPI/UART/GPIO interfaces, virtual sensors, wake events |
| `TTL_ISH_DMA_Architecture.md` | DMA Architecture | ISH5p9 HAS | DMA channels, PRD table format, transfer modes, channel registers |
| `TTL_ISH_Power_Management.md` | Power Management | ISH5p9 HAS | D-states (D0/D0i1/D0i2/D0i3/D3), SRAM gating, PMC sideband, S0ix behavior |
| `TTL_ISH_BIOS_Requirements.md` | BIOS Requirements | ISH BIOS Req | ACPI tables, init sequence, BAR config, BIOS knobs, GPIO pin muxing |
| `TTL_ISH_Firmware_Boot_Flow.md` | Firmware & Boot Flow | ISH5p9 HAS + BIOS Req | Boot ROM, BUP/main FW loading via CSE, memory layout, S3 resume, capsule update |
| `TTL_ISH_Register_Reference.md` | HOST Wrapper Registers | ish_wrapper_host.pdf (OSXML) | PCI config (DevID 0xE445), 8 IPC channel register maps, doorbell bit fields, D0ix counters, SAI policy |
| `TTL_ISH_MIA_Register_Reference.md` | MIA Internal Registers | ish_mia_bfm_rdl_top.pdf (OSXML) | I2C, GPIO, IPC (MIA-side), PMU, CCU, I3C HCI, WDT, SPI, UART, DMA misc, SRAM controller, Fabric — full address map |

## Key Architecture Summary

- **Core**: LMT 3.8/3.9 (MinuteIA) embedded processor
- **Memory**: 8KB ROM + 640KB SRAM (20x32KB banks) + 8KB AON RF SRAM
- **IO**: 3x I2C, 2x I3C, 3x UART, 2x SPI, up to 12 GPIOs
- **Host Interface**: IOSF (not PCIe), IPC doorbell/mailbox communication
- **Clocking**: 200/100 MHz
- **Power States**: D0, D0i1, D0i2, D0i3, D3 with per-bank SRAM gating
- **FW Loading**: Boot ROM → CSE loads BUP (64KB) → Host driver loads Main FW (1.5MB) via IMR
- **Platforms**: NVL (PCD-H, PCD-S, PCH-S), TTL

## Notes
- Data extracted via Co-De Sign AI agent queries against uploaded HAS documents
- Some register offsets and addresses may need cross-referencing with actual HAS PDFs
- Raw OSXML register text extracted: `ish_wrapper_host_raw.txt` (39,588 lines), `ish_mia_bfm_rdl_top_raw.txt` (80,645 lines)
- Structured register references: `TTL_ISH_Register_Reference.md` (HOST wrapper), `TTL_ISH_MIA_Register_Reference.md` (MIA internal)
