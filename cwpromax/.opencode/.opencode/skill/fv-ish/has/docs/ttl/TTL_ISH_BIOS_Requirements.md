# TTL ISH BIOS Requirements
## Source: Co-De Sign HAS - "ISH Requirement to BIOS" Document

### 1. ACPI Table Definitions

| Method | Purpose |
|--------|---------|
| `_STA` | Device presence/operational status, must reflect ISH enable/disable (fuse/softstrap) |
| `_CRS` | Current Resource Settings - MMIO, IRQ, BARs, interrupts |
| `_DSM` | Device Specific Method - platform-specific data (SAR sensor support), notify WiFi driver |

### 2. ISH Device Initialization Sequence (Boot)

1. Detect ISH enablement (fuse/softstrap/BIOS knob)
2. Enumerate ISH as PCI device, configure BARs
3. Reserve **8MB** before CSE UMA Memory for ISH FW shadowing
4. Set ISH to PCI mode
5. Enable clock and power gating
6. Load ISH firmware
7. Support wake from ISH
8. **If disabled**: put device into D3, no FW loaded

### 3. Memory Map & BAR Configuration

- Standard PCI enumeration, program BARs
- BARs mapped to system memory and MMIO space
- **8MB reserved** for ISH FW shadowing adjacent to CSE UMA
- S3 optimization: BIOS/CSME may save uncompressed ISH main in IMR for faster resume

### 4. BIOS Knobs & Setup Options

| Knob | Description |
|------|-------------|
| ISH Enable/Disable | Enable or disable ISH device |
| Greyed out condition | If fuse/softstrap disabled, knob is greyed out |
| Disable behavior | Must disable ISH before BUP/FW loading; put ISH into D3 |
| FPAK enable/disable | Optional FPAK configuration |

### 5. Firmware Loading Requirements

- **Capsule update**: ISH PDT region via CSE
- Pass ISH PDT to CSE for capsule update
- BIOS-ISH data pass feature (PDT unlock, update)
- ISH FW loading coordinated with CSE/CSME
- ISH FW shadowing in reserved memory
- **S3 optimization**: BIOS/CSME may save uncompressed ISH main in IMR for faster resume

### 6. GPIO & Pin Muxing Configuration

- Program GPIO pin muxing for ISH sensor interfaces
- Options to switch ISH UART 0/1, SPI, I3C ports to ISH (multiplexed with SoC interfaces)
- Platform-specific pin assignments per SKU

### 7. Platform-Specific Differences

| SKU | Notes |
|-----|-------|
| PCD-H (Mobile) | Primary ISH location on PCD-H die |
| PCD-S (Desktop) | ISH on PCD-S die |
| PCH-S | ISH on PCH-S die |
| IOE die | ISH present when PCH-S used as IOE die |

- SAR sensor support notification via ISH `_DSM` to WiFi driver
- Wake from ISH supported on all platforms

### Sources
- novalake platform firmware architecture specification.0.5.html
- nvl_xse_iploadingfas.html
