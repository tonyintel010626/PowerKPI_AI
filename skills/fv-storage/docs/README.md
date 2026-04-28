# Storage Reference Documents

## SATA Controller HAS

| Field | Value |
|-------|-------|
| **File** | `SATA 3.0 Controller.pdf` |
| **Text Dump** | `SATA_3.0_Controller_dump.txt` (115,611 words, 13,524 lines) |
| **Revision** | 1.09 (July 2024) |
| **Pages** | 242 |
| **Platforms** | ADP-S, MTL-SOC-M/P, MTP-S, LNL-SOC-P, NVP-S |
| **Compliance** | AHCI 1.3.1, SATA 3.2 |
| **Source** | Downloaded from local machine |

### Key Sections
- **Section 6**: Clocking and Resets (platform-specific clock configs, reset hierarchy)
- **Section 10.1**: PCI Configuration Registers (00h-FFh)
- **Section 10.2**: I/O Registers (AHCI Index/Data pair)
- **Section 10.3**: Memory-Mapped AHCI Registers (Generic Host Control, Port DMA, Port Interface, Vendor Specific, SIR)
- **Section 10.4**: MSI-X Registers
- **Section 15**: Security (SAI policy, REGLOCK, DFx)
- **Section 24**: Theory of Operation (AHCI/RAID modes, error handling, NCQ, power management, LTR, DEVSLP, thermal throttling, enclosure management, FLR, NVM remapping, lane muxing)
- **Section 25**: Microarchitecture (VRUNIT, VSAUNIT, PLPUNIT, PLUNIT, sideband, fabric decode)
