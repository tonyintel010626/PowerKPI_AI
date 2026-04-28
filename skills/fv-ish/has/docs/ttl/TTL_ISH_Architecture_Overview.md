# ISH5p9 Architecture Overview (TTL/NVL)

> Source: Co-De Sign query of `SIP_ISH5p9_HAS.html` from My Files

## 1. ISH IP Version & Supported Platforms

- **IP Version**: ISH 5.9 (also referenced as ISH 5.8, functionally equivalent for NVL, aligns with LNL ISH)
- **Supported Platforms**: All NVL SKUs
  - **Mobile**: PCD-H die
  - **Desktop NVL-S**: PCH-S die
  - Also present when PCH-S used as IOE die

## 2. Top-Level Block Diagram — Major Components

### LMT 3.8/3.9 (MinuteIA) Core
- Embedded DSP/AI subsystem
- **16KB I-cache**
- **16KB D-cache**
- **8KB ROM** (bootloader)
- **640KB pageable SRAM** (per-bank power gating)
- **8KB AON RF SRAM** (always-on retention)

### Dedicated IO Controllers
| Interface | Count | Speed |
|-----------|-------|-------|
| I2C       | 3     | 1 Mb/s |
| I3C       | 2     | HDR/DDR 25 Mb/s |
| UART      | 3     | 4 Mb/s |
| SPI       | 2     | 25 Mb/s |
| ISH GPIO  | up to 3 | — |

### Other Components
- **IOSF Interface** for host communication
- **DTF** with MIP SyS-T support, connects to NPK
- **Peer Communication** with eSPI, WiFi, Security, Audio
- **Clocking**: 200/100 MHz
- **Power Management**: Clock and power gating

## 3. Host Interfaces

- **Primary Interface**: IOSF (NOT PCIe — ISH is not a direct PCIe endpoint)
- **MMIO BARs**: Mapped via IOSF, base addresses set by BIOS/FW
- **Interrupts**: ISH generates interrupts to host for sensor events and IPC

## 4. Internal Bus Architecture

- **IOSF-Primary** and **IOSF-Sideband** buses
- Internal fabric connects core, SRAM, IO controllers
- **IPC (Inter-Processor Communication)** with:
  - Host
  - CSME
  - PMC
  - ACE
  - CNVi
- Fine-grained power gating, per-bank SRAM gating, AON retention

## 5. Key Features & Capabilities

- **Always-On Always-Sensing** in S0/S0ix
- Sensor data aggregation (virtual sensors)
- Aggressive clock/power gating
- **Supported OS**: Windows, Android, Linux, Chromium OS
- Data sharing with CSME, Connectivity, Audio
- **Hammock Harbor** time sync
- **DTF** debug/trace
- Peer communication with CSME, ESE, OSSE
