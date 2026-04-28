# THC IP HAS v4.x — Complete Extraction

> **Owner**: Chin, William Willy (`willychi`)

> **Source Document:** `SIP_THC_4x_HAS` / `sip_thc_4x_has.html`
> **Document Date:** September 02, 2025
> **Coverage:** LNL-M/P/S HAS 1.0 | PTL-PCD-M/P/H HAS 1.0 | WCL 1.0 | NVL 1.0 | RZL/TTL 1.0 (no change)
> **Extracted By:** FV-THC Agent (automated extraction via BrowserMCP)
> **Extraction Date:** 2026-03-04
> **Purpose:** Complete reference for post-silicon Functional Validation of THC IP
> **HAS URL:** https://docs.intel.com/documents/iparch/thc/THC_IP/4.x/IP%20Specs/HAS/SIP_THC_4x_HAS/SIP_THC_4x_HAS.html
> **Onesource Registers:** https://onesource.intel.com/Predator/Home/Index/22384

---

## Table of Contents

1. [Document Metadata & Contacts](#1-document-metadata--contacts)
2. [THC Introduction & Landing Zone](#2-thc-introduction--landing-zone)
3. [Feature POR Matrix](#3-feature-por-matrix)
4. [Feature Parameters](#4-feature-parameters)
5. [IP Clock Frequencies](#5-ip-clock-frequencies)
6. [SPI Touch Interface](#6-spi-touch-interface)
7. [I2C Touch Interface (LNL+)](#7-i2c-touch-interface-lnl)
8. [DMA Access](#8-dma-access)
9. [THC Register Access & Bus Arbitration](#9-thc-register-access--bus-arbitration)
10. [Touch Device Interrupt & GPIO Reset/Power](#10-touch-device-interrupt--gpio-resetpower)
11. [Host SW Interrupts](#11-host-sw-interrupts)
12. [Clocking](#12-clocking)
13. [Reset Transactions](#13-reset-transactions)
14. [Power Wells & States](#14-power-wells--states)
15. [Isolation Gates & Power Gating](#15-isolation-gates--power-gating)
16. [LTR (Latency Tolerance Reporting)](#16-ltr-latency-tolerance-reporting)
17. [Sleep States & Chassis 2.2](#17-sleep-states--chassis-22)
18. [Touch IC Power Management](#18-touch-ic-power-management)
19. [Transaction Flows](#19-transaction-flows)
20. [IOSF Sideband Messages](#20-iosf-sideband-messages)
21. [PCIe Capabilities](#21-pcie-capabilities)
22. [Decoding & Channel Mapping](#22-decoding--channel-mapping)
23. [Transaction Attributes](#23-transaction-attributes)
24. [Ordering & Coherency Rules](#24-ordering--coherency-rules)
25. [Interfaces & Signal Lists](#25-interfaces--signal-lists)
26. [Security](#26-security)
27. [Debug Requirements](#27-debug-requirements)
28. [Fuses & Soft Straps](#28-fuses--soft-straps)
29. [Performance Goals](#29-performance-goals)
30. [Area & Gate Count Goals](#30-area--gate-count-goals)
31. [Power Goals](#31-power-goals)
32. [Functional & Performance Monitoring](#32-functional--performance-monitoring)
33. [Test Requirements (DFT)](#33-test-requirements-dft)
34. [Validation Guidance](#34-validation-guidance)
35. [Programming Requirements / BIOS](#35-programming-requirements--bios)
36. [Safety](#36-safety)
37. [RAS](#37-ras)
38. [Appendix A — Register Maps](#38-appendix-a--register-maps)

---

## 1. Document Metadata & Contacts

| Role | Name |
|------|------|
| HW Architect | Kevin Zhenyu Zhu |
| Micro-architect | Kunj Rana |
| SW Architect | Even Xu |
| Platform Architect | Anton Cheng |

- Source tables from: `assets/SIP_THC_4x_HAS.xlsx`
- Onesource register reference: https://onesource.intel.com/Predator/Home/Index/22384

---

## 2. THC Introduction & Landing Zone

Touch Host Controller (THC) is an integrated IP in Intel Client SoCs providing host-side interface for touch input devices over serial protocols (SPI, I2C).

### Key Components
- **Dual-Port Design**: THC0 and THC1, each connecting to a separate touch device
- **DMA Engine**: RXDMA (2 channels per port) + TXDMA + SWDMA (Gen4.0+)
- **Interrupt Controller**: GPIO-based device interrupts → PCI MSI/MSI-X
- **Protocol Layer**: HIDSPI, HIDI2C, QuickSPI host-side engines
- **PIO Interface**: Register-based low-speed command/control transactions
- **MMIO Register Space**: BAR0-mapped configuration, control, and status

### Supported Protocols
1. **HID over SPI (HIDSPI)**: Half-duplex SPI, Single/Dual/Quad modes, falling-edge GPIO interrupt
2. **HID over I2C (HIDI2C)**: I2C 100K/400K/1M, level-triggered GPIO interrupt (Gen4.0+ / LNL+)
3. **QuickSPI**: Enhanced SPI with improved throughput (Non-POR from PTL+)

### THC IP Generation History

| Generation | Platform | Key Features |
|------------|----------|-------------|
| Gen1.0 | TGL, ADL | IPTS proprietary mode via CSME/GPU |
| Gen2.0 | ADP-LP+ | HIDSPI introduced, programmable opcodes |
| Gen3.0 | MTL-M, ARL | HIDSPI support |
| Gen4.0 | LNL-M | HIDI2C added, SWDMA engine |
| Gen4.1 | PTL, WCL | D3 flow overhauled (4 levels), half-divider clock |
| Gen4.2 | NVL, RZL, TTL | Unified HAS `sip_thc_4x_has.html` |

---

## 3. Feature POR Matrix

| Feature | Gen1 (TGL/LKF) | Gen2 (ADP/MTL) | Gen4 (LNL/PTL/NVL) | TSI |
|---------|-----------------|-----------------|---------------------|-----|
| HIDSPI | No | POR | POR | N/A |
| HIDI2C | No | No | SDV (Gen4+) | N/A |
| QuickSPI | No | No | Non-POR (PTL+) | N/A |
| SPI RX MPS | 64B | 64-4096B | 64-4096B | N/A |
| uFrame Streaming | No | TX-only | TX/RX | N/A |
| PRD Pages | 1KB/4KB | 1KB/4KB | 1KB/4KB | N/A |
| Max Frame | 1MB | 1MB | 1MB | N/A |
| Max Buffers/Frame | 256 | 256 | 256 | N/A |
| Max Buffer Size | 4KB | 4KB | 4KB | N/A |

---

## 4. Feature Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| THC_INSTANCE_INDEX | — | Instance identifier |
| THC_SPI_NUM_PORTS | 2 | Number of SPI ports |
| THC_PCI_DEVNUM | 17 | PCI device number |
| THC_PCI_MFD | — | Multi-function device config |
| THC_PCI_OR_PCIEMODE | — | PCI vs PCIe mode selection |

---

## 5. IP Clock Frequencies

| Clock | Frequency | Purpose |
|-------|-----------|---------|
| IOSF Primary | 125 MHz | Main data path |
| IOSF Sideband | 100 MHz | Register/config access |
| PGCB | 1-100 MHz | Power gating control |
| SPI SSC | ~125 MHz | SPI I/O clock source |

---

## 6. SPI Touch Interface

### Ports per Instance
- SPI_CS# (chip select, active low)
- SPI_CLK (clock)
- IO[3:0] (quad data lines)
- DEV_PWR_RESET# (device power/reset GPIO)
- INTERRUPT# (device interrupt GPIO)

### Frequency Configuration
- **Max platform frequency**: 40 MHz (SI limited)
- **Source clock**: TGL/LKF = 125 MHz SSC, ADP/MTL = 128 MHz
- **Divider**: 3-bit (values 001-111)
- **SPI_LOW_FREQ_EN**: 0 or 1 for two frequency ranges

### LNL+ DCG (Digital Clock Generator)
- Half-cycle fractional divider
- Programmable duty cycle (ZBBed)
- CS-to-CK delay, configurable
- RX clock selection (loopback or internal)

### IO Modes

| Mode | Read | Write (Gen1) | Write (Gen2+) |
|------|------|-------------|---------------|
| Single | ✅ | ✅ | ✅ |
| Dual | ✅ | ❌ | ✅ |
| Quad | ✅ | ❌ | ✅ |

### SPI Instruction Mapping

| Operation | Opcode |
|-----------|--------|
| PIO register read | 0x4 / 0x2 |
| PIO register write | 0x6 |
| Bulk read | 0x4 |
| Bulk write | 0x8 |

### SPI Timings
- CS# Setup: 30 ns minimum
- CS# Hold: 30 ns minimum

### SPI Loopback Clocks
- Dummy pad per port compensates on-chip routing delay

---

## 7. I2C Touch Interface (LNL+)

### Overview
- Supported from Gen4.0 (LNL) onwards
- Uses Synopsys DW_apb_i2c sub-IP
- IC_MAX_SPEED_MODE = 0x2 = Fast Mode Plus
- Default I2C address: 0x086
- PORT_TYPE register: 00 = SPI, 01 = I2C

### HIDI2C Commands
- Dedicated SWDMA, TXDMA, RXDMA registers for I2C mode
- Command table defined in HAS

### RTL Bug (Critical)
- **THC uses SPI_RD_MPS in I2C mode** — this is a known RTL bug
- **SW workaround**: Program SPI_RD_MPS to 4KB when using I2C mode

### Legacy Panel Support (PTL/WCL/NVL+)
- Elan panel workarounds required on certain platforms

---

## 8. DMA Access

### Architecture Overview

| Mode | Description | POR Status |
|------|-------------|------------|
| Store-and-Forward | Complete frame buffered before DMA | POR |
| Streaming | DMA starts before frame complete | Not POR (6.5% better perf) |

### PRD Descriptor Caching
- Configurable depth
- Prefetches across PRD table boundaries

### DMA Channels per Port

| Channel | Purpose | Routing |
|---------|---------|---------|
| RXDMA1 | Read DMA channel 1 | Frame Type 0 |
| RXDMA2 | Read DMA channel 2 | Frame Type 1 |
| SWDMA | Software-triggered DMA (LNL+) | SW-triggered, ignores INT_CAUSE |
| TXDMA | Write DMA | Single PRD table, ping-pong buffer |

- HIDSPI mode: Frame Type ignored (all → RXDMA1)
- Circular Buffer: Up to 128 PRD tables per RXDMA

### PRD Entry Format (16 bytes / 128 bits)

| Bits | Field | Description |
|------|-------|-------------|
| 90:89 | HW Status | Hardware status flags |
| 88 | EOP | End of Packet marker |
| 87:64 | Length | Buffer length (4KB-aligned except last) |
| 63 | IOC | Interrupt on Completion |
| 53:0 | DestAddr | Destination address (1KB min alignment) |

**⚠️ RTL Bug 15014172472**: Last PRD entry also requires 4KB alignment (HAS says only non-last need alignment)

### E2E Flow
1. Device INT → ICR read
2. ICR qualify → Bulk Data Read
3. PRD walk → DMA transfer
4. MSI → EOF
5. GuC doorbell

### SPI DMA Opcodes

| Operation | Opcodes |
|-----------|---------|
| ICR Read | 0B / BB / EB / FB |
| DMA Read | 0B / BB / EB / FB |
| Dummy Clocks | 0 / 2 / 4 / 8 |

### Error Handling
- RXDMA Stop-on-Error
- I2C TX Abort
- PRD Table Overflow → STALL_STS

### SGX Trusted I/O
- Channel ID for DMA encryption support

---

## 9. THC Register Access & Bus Arbitration

### Register Read/Write
- SPI: 24-bit address space
- TSI: 32-bit address space
- Normal: 1 DW (4 bytes)
- Maximum: min(MPS, 64B)

### PIO (Programmed I/O)
- 7-step flow using:
  - `THC_M_PRT_SW_SEQ_CNTRL` — control register
  - `THC_M_PRT_SW_SEQ_STS` — status register
  - `THC_M_PRT_SW_SEQ_DATA[16:0]` — 17 data DWORDs

### Bus Arbitration Priority
1. **PIO** (highest)
2. **Write DMA**
3. **HW Sequencer** (lowest)

- Round-robin chicken bit available for alternate arbitration

### ⚠️ Important
When RXDMA is running, SW must **NOT** read the Touch IC's interrupt cause register directly.

---

## 10. Touch Device Interrupt & GPIO Reset/Power

### Device Interrupt
- **TSI**: Inband (HS clock toggle)
- **SPI**: GPIO (active low, level-based)

### GPIO Reset/Power
- 1 GPIO per port
- 1 = deassert reset / power-on
- 0 = assert reset / power-off
- Voltage: 1.8V

### Wake on Gesture (WoG)
- **Not POR** — many open issues remain

### Boot Behavior
- Always use level-trigger during init
- Switch to edge-trigger after device reset

---

## 11. Host SW Interrupts

### Global Interrupt Enable
- `GBL_INT_EN` (bit 31, default 1, LNL+)

### Interrupt Sources

| Source | Register/Bit | Description |
|--------|-------------|-------------|
| vGPIO | SWGPIO_INT (bit 4) | Virtual GPIO interrupt |
| Device Reset | DEVRST (bit 3) | Device reset completion |
| DMA RX | THC_M_PRT_DMA_READ_INT_STS | RX DMA completion |
| DMA TX | THC_M_PRT_DMA_WRITE_INT_STS | TX DMA completion |

### Error Categories
- **Fatal**: TSI only
- **Transaction**: TXN_ERR
- **DPHY Bus**: TSI only

---

## 12. Clocking

### Clock Requirements

| Clock | Frequency | Purpose |
|-------|-----------|---------|
| IOSF Primary | ~125 MHz | Main datapath |
| IOSF Sideband | ~100 MHz | Register access |
| PGCB | ~5 MHz | Power gating control |
| SPI SSC | 125 MHz | SPI I/O source |
| Non-SSC ROSC | ~120/100 MHz | Alternative clock source |
| DFT SPI IO | — | Test mode clock |

### Clock Gating
- Chassis-compliant for 6 clock types + TSI PHY clocks
- Efficiency target: >98%

### Clock Domains
- 7 domains + TSI-specific (HS, LP rx, LP tx)

### SPI Loopback Clocks
- Dummy pad per port
- Compensates on-chip routing delay

---

## 13. Reset Transactions

### G3 Exit Sequence
1. PGCB reset → PGD enable
2. SB reset / credit init
3. Fuses / straps loaded
4. IP_RDY asserted
5. SETIDVALUES (SB message)
6. Primary reset deassert

### Controller Init (Post-Reset)
1. PCI enumeration
2. Two driver models:
   - **Per-port**: 1 PCI function per port, separate MBARs
   - **Shared**: 1 PCI function, multiple ports in same BAR

### Touch Link Config
1. SPI_IO_RDY wait
2. THC_M_PRT_SPI_CFG programming
3. MPS configuration
4. Device init state polling (4 states: 0→1→2→3→4)

### Soft Reset (ADP+)
- PSRST + DEVRST + TSFTRST sequence
- Used for error recovery and debug

### Cold/Warm Reset
- Full reset with reset_warn + FORCEPGPWROK
- GPIO reset asserted during reset_warn phase

### Global Reset
- Same as cold boot exit sequence

---

## 14. Power Wells & States

### Power Domains

| Domain | Type | Description |
|--------|------|-------------|
| THC_PGD | Power-gateable | Main logic, can be power gated |
| THC_UGD | Un-gated | Always-on logic |

### Power States

| State | Description | Entry Condition |
|-------|-------------|----------------|
| D0 Active | Fully operational | Normal operation |
| D0 Idle | Clock gated, awaiting work | No pending transactions |
| D0i2 | HW autonomous PG with state retention | Programmable entry timer ≤1s |
| D3/D0i3 | Software-initiated deep sleep | OS/driver request |
| S0i3 | System idle | Connected standby |
| S3/4/5 | System sleep/hibernate/off | OS request |

---

## 15. Isolation Gates & Power Gating

- Isolation required: PGD → UGD direction
- Isolation NOT required: UGD → PGD direction
- 10-bit `thc_res_own_req/ack` for Chassis 2.2 Sleep States

---

## 16. LTR (Latency Tolerance Reporting)

### Overview
- Controller-level via IOSF Sideband
- Two LTR states: Active + Low Power
- Programmed by BIOS via `ACTIVE/LP_LTR_VAL/SCALE` registers
- Infinite LTR sent on: cold boot, Vnn removal, reset exit

### LTR Scale Values

| Scale | Unit |
|-------|------|
| 0 | 1 ns |
| 1 | 32 ns |
| 2 | 1,024 ns |
| 3 | 32,768 ns |
| 4 | 1,048,576 ns |
| 5 | 33,554,432 ns |

---

## 17. Sleep States & Chassis 2.2

### Resource Mapping (10 bits)

| Bit | Resource |
|-----|----------|
| 0 | Memory |
| 1 | IOSF Primary |
| 2 | IOSF Sideband |
| 3 | THC CORE clock |
| 4 | THC SB clock |
| 5 | PGCB clock |
| 6 | Vcc_Main (Vnn) |
| 7 | ROSC clock |
| 8 | SS clock |
| 9 | THC GPIO |

### Chassis 2.2 Interfaces
- `resource_own_req/ack` — wires, 10-bit
- `sleep_level_req/rsp` — IOSF SB
- `immediate_sleep_level_rsp` — wire
- `QoS_DMD/Rsp` — IOSF SB
- OBFF — not supported

### QOS_DMD Types
- **RLTR**: Memory only, replaces THC LTR
- **RTALTR**: Memory only, SOC → IP direction
- **RALTR**: IP → SOC direction

### Known Issues
- **HSDES 16014286225**: THC not fully Chassis 2.2 compliant
- PTL: POR keeps same behavior as LNL/MTL; `*RES_EN` bits default to 0 (disabled)

---

## 18. Touch IC Power Management

### Touch IC Power States

| State | Power | Description | Exit Latency |
|-------|-------|-------------|-------------|
| Off | 0 mW | D3-Cold | — |
| Sleep | ≤1 mW | D3/D0i3 | 5 ms |
| Doze | ≤5 mW | Reduced sampling | — |
| Armed | ≤10 mW | Ready for touch | — |
| Sensing | ≤50 mW | Active scanning | — |

### State Transitions
- Sensing → Armed: no finger detected
- Armed → Doze: 300s inactivity
- Armed/Doze → Sleep: connected standby entry

---

## 19. Transaction Flows

### HCI Address Map
- 3 interface spaces: PCI Config, MMIO, Host Memory

### Driver Models
1. **Per-port**: 1 PCI function per port, separate MBARs
2. **Shared**: 1 PCI function, multiple ports in same BAR

### MMIO Space Groups
- PIO Registers
- Read DMA Engine (2 per port, Frame Type routing)
- Write DMA Engine
- Touch Sequencer / Graphics Communication

### Read DMA Circular Buffer
- Up to 128 PRD tables
- Max 256 PRD entries per table
- CB read/write pointer coordination

### SWDMA (LNL+)
- 3rd RXDMA engine
- SW-triggered (ignores INT_CAUSE)
- No GuC doorbell, no counter

### PRD Entry Detail (16 bytes)

| Bits | Field | Max/Notes |
|------|-------|-----------|
| 90:89 | HW Status | Set by HW |
| 88 | EOP | End of Packet |
| 87:64 | Length | Max 16MB-1 |
| 63 | IOC | Interrupt on Completion |
| 53:0 | DestAddr | 1KB min alignment |

### Device Interrupt Quiesce
- `THC_DEVINT_QUIESCE_EN` register controls quiesce behavior

### Write DMA
- Single PRD table (not CB-based)
- Ping-pong buffer support

### GuC Interface
- VDM or Doorbell mechanism
- Doorbell cookie increments, skips 0
- TailOffset = (TailOffset + WorkQueueItemSize) % WorkQueueSize

### Touch Sequencer E2E Flow
1. Device INT received
2. ICR read (Input Cause Register)
3. Qualify interrupt cause
4. Bulk data read
5. PRD walk (DMA transfer)
6. EOF detection
7. GuC doorbell notification

### Frame Coalescing
- Configurable frame count
- FCD (First Contact Detect) for first-touch latency bypass
- Timeout: 10-100 ms

### Timing-based Coalescing (LNL+)

| Parameter | Granularity | Range | Typical |
|-----------|-------------|-------|---------|
| C_Start_Threshold | — | — | — |
| C_Duration | 0.1 ms | 1-50 ms | 16.7 ms |
| C_Timer_Override | — | VSYNC | — |
| C_Idle_Threshold | — | — | — |

---

## 20. IOSF Sideband Messages

### ⚠️ PTL+ Requirement
- 16-bit SB port ID required (HSDES 15010734105)

### Message Table

| Message | Opcode | Direction | Purpose |
|---------|--------|-----------|---------|
| Assert INTA-D | 0x80-0x83 | THC→ITSS | Legacy interrupt assert |
| Deassert INTA-D | 0x84-0x87 | THC→ITSS | Legacy interrupt deassert |
| DoSERR | 0x88 | THC→ITSS | System error |
| Cpl/CplD | — | PMC→THC | Fuse/strap pull completion |
| MRd/MWr | — | Host→THC | Register access |
| CfgRd/CfgWr | — | Host→THC | PCI config access |
| FORCEPWRPOK | — | PMC→THC | Force power OK |
| LTR | — | THC→PMC | Latency tolerance report |
| SetIDValue | — | PMC→THC | Device ID programming |
| ResetPrep | — | PMC→THC | Reset preparation |
| ResetAck | — | THC→PMC | Reset acknowledgment |

### SAI Checking (INDEX41 for MRd/MWr/CfgRd/CfgWr)
Allowed SAIs:
- ESE_SAI
- HOSTIA_POSTBOOT_SAI
- HOSTIA_BOOT_SAI
- HOSTIA_SMM_SAI
- DFX_INTEL_MANUFACTURING_SAI
- DFX_INTEL_PRODUCTION_SAI
- DFX_THIRDPARTY_SAI
- PM_IOSS_SAI
- HOSTIA_UCODE_SAI
- HOSTIA_SUNPASS_SAI
- CSE_INTEL_SAI

### CRRd/CRWr SAI Access
- CSE_INTEL_SAI + subset of above

### Endpoint Configuration
- EP Name: `thc`
- Payload Bus Width: 8
- Port Domain: 8b/16b

---

## 21. PCIe Capabilities

### Bus/Device Number
- Must NOT hard-code Device Number
- `thc_pci_or_pciemode` controls capture behavior
- `pin_scr_funcnum[2:0]` strap sets PCI Function Number

### PCI PM Capability (Offset 0x70)
- NXTP → 0xB0 when PCIe mode

### PCIe Capability Structure (Offset 0xB0)
- Cap ID = 0x10
- Version = 2h
- Type = PCIe Endpoint

### PCIe Device Capability (Offset 0xB4)
- Max_Payload = 128B
- FLR = 0 (not supported)
- Extended Tag = 8-bit
- L0s/L1 Latency = No limit

### PCIe Device Control/Status (Offset 0xB8)
- Max_Read_Request_Size: ignored (always 64B)
- No Snoop: ignored (always 0)
- Transactions Pending: implemented

---

## 22. Decoding & Channel Mapping

### PCI BAR Configuration

| BAR | Type | Range | Target Channel |
|-----|------|-------|----------------|
| BAR0 | Type 0 | 32KB | CH 0 |
| BAR1-5 | — | Unused | — |
| ROMBAR | — | Unused | — |

### Enable Bits
- Memory Enable = Yes
- IO Enable = No
- Power State Address = PMCR @ 0x34
- BDF = TBD (platform-specific)

### DID Configuration
- Bits 31:16 RO/V (upper 9 bits overridable via SetIDValue SB message)
- Bit 16 RWOnce for MTL+

### NVL+ PI Configuration
- Configurable via `thc_pi_def[7:0]` softstrap

### MMIO Layout

| Offset | Region |
|--------|--------|
| 0x0000 | Common registers |
| 0x1000 | Port 0 registers |
| 0x2000 | Port 1 registers |

### Reset Domains
- All MMIO/config regs: primary reset
- SB regs: SB reset

### PCIe Endpoint (MTL-S+)
- `thc_pci_or_pciemode` softstrap controls PCI vs PCIe mode

### Supported Capabilities

| Capability | Supported |
|-----------|-----------|
| PMCS | Yes |
| PCIe CAP | If pciemode |
| LTR | Yes |
| PTM | No |
| FLR | No |
| MSI | Yes |
| MSI-X | No |
| AER | No |
| D3-Cold | No |
| D3-Hot | Yes |
| PME | No |
| WAKE | No |
| ERR Msg | No |
| PCI SERR | Yes |
| INTx | Yes |
| MBAR | Yes, 64-bit |
| Min MBAR | 32KB |

---

## 23. Transaction Attributes

### Supported Transactions (Port 0)

| Transaction | Upstream | Downstream |
|------------|----------|------------|
| MRd32 | ✅ | ✅ |
| MRd64 | ✅ | ✅ |
| MWr32 | ✅ | ✅ |
| MWr64 | ✅ | ✅ |
| CfgRd0 | ❌ | ✅ |
| CfgWr0 | ❌ | ✅ |
| MsgD | ✅ | ❌ |
| Cpl | ✅ | ✅ |
| CplD | ✅ | ✅ |

### NOT Supported
LTMRd/LTMWr, MRdLk, IORd/IOWr, CfgRd1/CfgWr1, Msg, CplLk/CplDLk, FetchAdd, Swap, CAS

### Transaction Sizes

| Property | Value |
|----------|-------|
| Port | 0 |
| Channels | 1 |
| Peak BW (UP) | 1 GBps (125 MHz × 8B) |
| Peak BW (DN) | 1 GBps (125 MHz × 8B) |

### Max Payload by Type

| Type | Direction | Max Size |
|------|-----------|----------|
| Posted | Upstream | 64B |
| Posted | Downstream | 8B |
| Non-Posted | Upstream | 0 |
| Non-Posted | Downstream | 1 DW |
| Completion | Upstream | 8B |
| Completion | Downstream | 64B |

---

## 24. Ordering & Coherency Rules

- THC follows standard IOSF ordering on both downstream and upstream paths
- IOSF Primary Physical Attributes:
  - Port: 0
  - Address Width: 63:0
  - Data Width: 63:0
  - Frequency: 125 MHz

---

## 25. Interfaces & Signal Lists

### IOSF Primary Interface
- Chassis-compliant single root space
- Detailed signals in external Excel file

### IOSF Sideband Interface
- Chassis-compliant
- Detailed signals in external Excel file

### PM Interface
- Chassis PGCB/CDC spec based

### DFT Signal List
- Chassis DFT compliant

### DPHY Signal List
- **N/A for TGP/LKF SPI mode**
- `THC_dphy_reset_b` — Output, async reset
- `Dphy_ready` — Input, common lane PHY ready

### Clock Lane PPI (per Port)

| Signal | Direction | Description |
|--------|-----------|-------------|
| dphy_THC_cl_RxClkActiveHS | Input | HS clock active |
| RxByteClkHS | Input | Byte clock |
| RxDDRClkHS | Input | DDR clock |
| Stopstate | Input | Lane stop state |
| Enable | Output | Lane enable |
| RxClkEsc | Input | Escape mode clock |
| RxUlpsClkNot | Input | ULPS clock indicator |
| UlpsActiveNot | Input | ULPS active indicator |
| ErrControl | Input | Clock lane error |

### Data Lane PPI (per Port)

#### High-Speed RX

| Signal | Width | Description |
|--------|-------|-------------|
| RxDataHS | 8 bits | HS receive data |
| RxValidHS | 1 | HS data valid |
| RxActiveHS | 1 | HS reception active |
| RxSyncHS | 1 | HS sync detected |

#### Escape Mode TX

| Signal | Width | Description |
|--------|-------|-------------|
| TxClkEsc | 1 | Escape TX clock |
| TxRequestEsc | 1 | Escape TX request |
| TxLpdtEsc | 1 | Low-power data TX |
| TxUlpsExit | 1 | ULPS exit |
| TxUlpsEsc | 1 | ULPS escape |
| TxTriggerEsc | 4 bits | Trigger escape |
| TxDataEsc | 8 bits | Escape TX data |
| TxValidEsc | 1 | Escape TX valid |
| TxReadyEsc | 1 | Escape TX ready |

#### Escape Mode RX

| Signal | Width | Description |
|--------|-------|-------------|
| RxClkEsc | 1 | Escape RX clock |
| RxLpdtEsc | 1 | Low-power data RX |
| RxUlpsEsc | 1 | ULPS RX |
| RxTriggerEsc | 4 bits | RX trigger |
| RxDataEsc | 8 bits | Escape RX data |
| RxValidEsc | 1 | Escape RX valid |

#### Control Signals

| Signal | Description |
|--------|-------------|
| TurnRequest | Lane turnaround request |
| Direction | Data direction |
| TurnDisable | Disable turnaround |
| ForceRxmode | Force receive mode |
| ForceTxStopmode | Force TX stop |
| Stopstate | Lane stop state |
| Enable | Lane enable |

---

## 26. Security

### Threat Points
1. **Sensor PIO** — Touch device register access
2. **VTd** — DMA address translation
3. **GPIO** — Interrupt/reset pin access

### Access Control
- **SAI-based** access checking on all SB transactions
- **BIOS_LOCK_EN** — locks BIOS-configured registers
- **DRV_LOCK_EN** — locks driver-configured registers

### Security Properties
- No secrets stored in THC IP
- No peer-to-peer transactions
- Host root space only
- DMA controlled by Host IA/OS
- Traffic class hardcoded
- Outbound SAI immutable
- VTd compliant (SAI on CFG+MMIO)
- No TAP connection
- No microprocessor / FW authentication needed

---

## 27. Debug Requirements

### VISA Configuration
- 2 lanes × 8 bits
- 100-130 MHz
- 5-level tree

### Not Applicable
- No FW engine
- No trigger events
- No DTF (Design-for-Test Fabric)
- No North Peak connection

---

## 28. Fuses & Soft Straps

### Fuse
- `THC_RESERVED_FUSE`: 8-bit, address 0x3980

### Soft Straps

| Strap | Purpose |
|-------|---------|
| PowerGateEnable | Enable/disable power gating |
| ClockGateEnable | Enable/disable clock gating |
| TSI timing params | TSI-specific timing configuration |
| PORT_TYPE | SPI (00) or I2C (01) selection |

---

## 29. Performance Goals

### Throughput

| Interface | Bandwidth |
|-----------|-----------|
| TSI Read | 125 MBps × 2 ports |
| SPI Read | 12 MBps (20 MBps Gen2) × 2 ports |

### Latency Targets

| Metric | Target |
|--------|--------|
| INT → CS# assert | 400 ns |
| Frame end → MSI | 800 ns |
| PG exit | 10 μs |

---

## 30. Area & Gate Count Goals

| Metric | Target |
|--------|--------|
| Gate Count | 300K per THC instance (with two ports) |
| RF (Register File) | 2 × 8KB (TSI DPHY only) |

---

## 31. Power Goals

| Metric | Target |
|--------|--------|
| Max Dynamic (PIO+TXDMA+RXDMA Quad/30MHz+IOSF) | 4 mW |
| Max PIO | <4 mW |
| Max RXDMA | 4 mW |
| Max TXDMA | 4 mW |
| Max IOSF | 4 mW |
| Leakage (idle, not PG) | 150 μW |
| Power Gated (D0i2/D3) | <5 μW |

---

## 32. Functional & Performance Monitoring

### Counters

| Counter | Description |
|---------|-------------|
| RXDMA Doorbells | Number of GuC doorbell notifications |
| TX DMA Frames | Transmitted DMA frames |
| RX DMA Frames | Received DMA frames |
| uFrames | Micro-frame count |
| Dropped Frames | Frames dropped due to errors |
| TX/RX Touch Packets | Touch data packet count |
| Device Interrupts | Device interrupt count |
| SW Interrupts | Software interrupt count |

---

## 33. Test Requirements (DFT)

### DFT Coverage
- Refer to SPI Integration Guide for:
  - MBIST/PBIST
  - Scan configuration
  - Array Freeze: N/A
  - MISR: N/A

### DFT Security
- THC supports DFT security plugin for VISA

### HVM Tooling
- `dft_spi_clk` used when `dfx_ovrd.SBDCE` (0xC000[2]) set
- `dft_espi_clk` used when `dfx_ovrd.EBDCE` (0xC000[3]) set
- No determinism support

### DFx Chassis Requirements

| Requirement | Status |
|-------------|--------|
| sTAP/wTAP | Not Supported |
| Memory co-location | Mandatory |
| Scan hooks | Mandatory (95% stuck-at, 85% at-speed) |
| LBIST DRC | Optional |
| VISA ULM | Mandatory (v2.13+) |
| DFX Security Plugin | Conditional |
| VISA Security | Conditional |
| All debug hooks in SB | Mandatory |
| Fuse-Puller-Endpoint | Required |
| IOSF-DFX compliance | Mandatory |

### Coverage Goals
- 99% stuck-at
- 95% at-speed

### TSI Device Emulation Mode
- Triggered by `DFX_Mode_En`
- `TSI_Port_sel` (2-bit) selects port
- Supports HS/LP data generation: PRBS, constant, alternating patterns

### Device Emulation Registers

| Register | Purpose |
|----------|---------|
| DFX_HS_DATA_GEN | HS data pattern generator |
| DFX_MODE_CTL | Emulation mode control |
| DFX_HS_HDR | HS header config |
| DFX_HS_CRC | HS CRC config |
| DFX_TXESC_STATUS | TX escape status |
| DFX_LP_DATA_GEN | LP data pattern generator |
| DFX_TX_LP_HDR/PAYLOAD/CRC | LP TX header/payload/CRC |
| DFX_RX_LP_HDR/PAYLOAD/CRC | LP RX header/payload/CRC |

### 9-Step Device Emulation Flow
1. Configure DFX_Mode_En
2. Select port via TSI_Port_sel
3. Configure data pattern generator
4. Set HS/LP header
5. Configure CRC
6. Enable data generation
7. Monitor TX status
8. Verify RX data
9. Compare TX vs RX

---

## 34. Validation Guidance

### Frame Size Limits

| Parameter | Validation Limit | EDS Limit |
|-----------|-----------------|-----------|
| Frame Size | 64B — 1MB | 1B — 16MB |
| uFrame Size | Multiple of 16B | — |
| Max uFrames/Frame | 64 | — |
| PRD Table (RX) | Max 1MB | — |
| PRD Table (TX) | Max 64KB | — |

### PRD Entry Alignment
- Non-last entries: must be 4KB-aligned
- Last entry: can be 1B — 1MB

---

## 35. Programming Requirements / BIOS

### External Reference
- BIOS programming guide: `Chap69_BIOS_WG_THC.docx`

### NVL+ Specific
- Configurable PCI Programming Interface (PI) via softstrap `thc_pi_def[7:0]`

---

## 36. Safety

- THC has **NO safety requirements** for current generation
- All safety subsections: "Not applicable to this IP/IPSS"

---

## 37. RAS

- **Not applicable** to this IP

---

## 38. Appendix A — Register Maps

### PCI Config Space (23 Registers)

| Offset | Register | Restore Order |
|--------|----------|---------------|
| 0x00 | DID/VID | — |
| 0x04 | STS/CMD | 2.01 |
| 0x08 | CC/RID | — |
| 0x0C | CLS/MLT/HT | — |
| 0x10 | BAR0 (Lower) | 2.02 |
| 0x14 | BAR0 (Upper) | 2.03 |
| 0x2C | SVID/SID | — |
| 0x34 | CAP_PTR | — |
| 0x3C | INT_LN/INT_PIN | 2.04 |
| 0x70 | PCI PM Capability | — |
| 0x74 | PMCS | 2.05 |
| 0x80 | MSI Capability | 2.06 |
| 0x84 | MSI Address Low | 2.07 |
| 0x88 | MSI Address High | 2.08 |
| 0x8C | MSI Data | 2.09 |
| 0xA0 | Device Idle | 2.10 |
| 0xA4 | LTR Capability | — |
| 0xA8 | LTR Value | 2.11 |
| 0xB0 | PCIe Capability | — |
| 0xB4 | PCIe Device Cap | — |
| 0xB8 | PCIe Device Ctrl/Sts | 2.12 |
| 0xD0 | MANID | — |
| 0xF8 | — | 2.17 |

### MMIO Common Registers (2 Registers)

| Offset | Register | Restore Order |
|--------|----------|---------------|
| 0x0000 | Device Idle Control | 3.00 |
| 0x0004 | LTR Control | 3.01 |

### MMIO Port Registers (per-port, ~80 Registers)

Key registers with restore orders (3.102 — 3.146, 5.1):
- THC_M_PRT_CONTROL — Port control
- THC_M_PRT_SPI_CFG — SPI configuration
- THC_M_PRT_INT_EN — Interrupt enable
- THC_M_PRT_INT_STATUS — Interrupt status
- THC_M_PRT_SW_SEQ_CNTRL — PIO control
- THC_M_PRT_SW_SEQ_STS — PIO status
- THC_M_PRT_SW_SEQ_DATA[16:0] — 17 PIO data DWORDs
- WPRD/RPRD base addresses — DMA descriptor bases
- DMA control/status/error (TX + dual RX)
- GuC doorbell/offset registers
- Bulk address registers
- Counter registers
- Coalesce timer registers

**Note**: DMA-related registers are "Driver reinitialize" — they are re-programmed by the driver rather than restored from save state.

### IOSF Sideband Registers (Port 0x39, 20 Registers)

| Offset | Register | Restore Order |
|--------|----------|---------------|
| P39h:00h | CDC Config | 3.20 |
| P39h:04h | Clock Config | 3.21 |
| P39h:08h-24h | SAI Policy (8 regs) | 1.00-1.07 |
| P39h:28h | SPI Control | 3.22 |
| P39h:2Ch | PM Control | 3.23 |
| P39h:30h | Lock Bits | 2.17 |
| P39h:34h | Arbitration | 3.24 |
| P39h:80h | Fuses | — |
| P39h:84h | Soft Straps | 3.36 |

### Reset and Power Domains

| Block | Reset Domain | Power Domain | Power Well |
|-------|-------------|-------------|------------|
| Most registers | thc_core_rst_b | pd_pwell_dummy_thcss_pd | VNN |
| THC_CFG_PCE.HAE | thc_sb_rst | — | VNN |
| THC_SB_SSC_CLK_CFG | thc_sb_rst | — | VNN |
| THC_SB_ROSC_CLK_CFG | thc_sb_rst | — | VNN |
| THC_SB_DCGE_CFG | thc_sb_rst | — | VNN |
| THC_BUS_NUM | thc_sb_rst | — | VNN |

### ⚠️ Reviewer Note
- SnR (Save and Restore) register list is outdated and needs update

---

## Appendix — Known RTL Bugs and HSDES References

| HSDES | Description |
|-------|-------------|
| 15014172472 | Last PRD entry requires 4KB alignment (RTL bug) |
| 16014286225 | THC not fully Chassis 2.2 compliant |
| 15010734105 | PTL+ requires 16-bit SB port ID |
| — | THC uses SPI_RD_MPS in I2C mode (RTL bug, workaround: program to 4KB) |

---

*End of extraction. All content sourced from SIP_THC_4x_HAS v4.x (September 02, 2025).*
