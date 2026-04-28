# TTL ISH Wrapper Host Register Reference
## Source: ish_wrapper_host.pdf (849 pages, OSXML export)
## Platform: Titan Lake (TTL)
## IP: ISH 5.9
## PCI Device ID: 0xE445, Vendor ID: 0x8086

---

## PCI Configuration Space (file_iosf2axi_pci_configreg_CFG)

| Offset | Register | Default | Description |
|--------|----------|---------|-------------|
| 0x00 | DEVVENDID | 0xE4458086 | Device ID=0xE445, Vendor ID=0x8086 |
| 0x04 | STATUSCOMMAND | 0x100000 | PCI Status/Command |
| 0x08 | REVCLASSCODE | 0x0 | Revision/Class Code |
| 0x0C | CLLATHHEADERBIST | 0x0 | Cache Line/Latency/Header/BIST |
| 0x10 | BAR | 0x0 | Base Address Register (low 32-bit) |
| 0x14 | BAR_HIGH | 0x0 | Base Address Register (high 32-bit) |
| 0x18 | BAR1 | 0x0 | Base Address Register 1 (low 32-bit) |
| 0x1C | BAR1_HIGH | 0x0 | Base Address Register 1 (high 32-bit) |
| 0x2C | SUBSYSTEMID | 0x0 | Subsystem ID |
| 0x34 | CAPABILITYPTR | 0x80 | Capability Pointer |
| 0x3C | INTERRUPTREG | 0x100 | Interrupt Register |
| 0x80 | POWERCAPID | 0x48030001 | Power Management Capability |
| 0x84 | PMECTRLSTATUS | 0x8 | PM Control & Status |
| 0x90 | PCIDEVIDLE_CAP_RECORD | 0xF0140009 | PCI Device Idle Vendor Cap |
| 0x94 | DEVID_VEND_SPECIFIC_REG | 0x1400010 | Vendor Specific Extended Cap |
| 0x98 | D0I3_CONTROL_SW_LTR_MMIO_REG | 0x0 | SW LTR Update MMIO Location |
| 0x9C | DEVICE_IDLE_POINTER_REG | 0x0 | Device Idle Pointer |
| 0xA0 | D0I3_MAX_POW_LAT_PG_CONFIG | 0x280800 | D0i3 & Power Control Enable |
| 0xC0 | GEN_INPUT_REG | 0x0 | General Purpose Input |
| 0xD0 | MSI_CAP_REG | 0x1800005 | MSI Capability |

---

## IPC Channel Architecture

All IPC channels follow an identical register layout pattern. Each channel has its own
register space with the same offsets relative to the channel base.

### Channel Base Addresses

| Channel | Base Offset | Type | SAI PolicyGroup | Description |
|---------|------------|------|-----------------|-------------|
| HOST | 0x000 | MEM | ISH_IPC_HOST2ISH_GP | Primary host interface |
| HOSTSPARE | 0x000 | MEM | ISH_IPC_HOST2ISH_GP | Spare host interface (separate space) |
| CSE | 0x1000 | MSG | ISH_IPC_CSME2ISH_GP | CSME/Security Engine |
| PMC | 0x2000 | MSG | ISH_IPC_PMC2ISH_GP | Power Management Controller |
| CNVi | 0x3000 | MSG | ISH_IPC_CNVI2ISH_GP | Connectivity (WiFi/BT) |
| ACE | 0x4000 | MSG | ISH_IPC_ACE2ISH_GP | Audio/ACE |
| ESE | 0x5000 | MSG | ISH_IPC_ESE2ISH_GP | Embedded Security Engine |
| AVB | 0x6000 | MSG | ISH_IPC_AVB2ISH_GP | Audio/Video Bridge |

### Per-Channel Register Layout (offsets relative to channel base)

| Offset | Register | Default | Description |
|--------|----------|---------|-------------|
| 0x00 | PISR | 0x0 | Peripheral Interrupt Status |
| 0x04 | PIMR | 0x0 | Peripheral Interrupt Mask (ISH-side only) |
| 0x08 | HOST_PIMR | 0x0 | Peer-accessible Interrupt Mask |
| 0x0C | HOST_PISR | 0x0 | Peer-accessible Interrupt Status |
| 0x10 | CIM | 0x0 | Channel Interrupt Mask |
| 0x14 | CIS | 0x0 | Channel Interrupt Status |
| 0x34 | FWSTS | 0x0 | Firmware Status (RO by peer, RW by ISH) |
| 0x38 | COMM | 0x0 | Communication Register (RW by peer, RO by ISH) |
| 0x48 | INBOUND_DOORBELL | 0x0 | Inbound Doorbell (peer-to-ISH) |
| 0x54 | OUTBOUND_DOORBELL | 0x0 | Outbound Doorbell (ISH-to-peer) |
| 0x60-0xDC | OUTBOUND_MSG1-32 | 0x0 | Outbound Message Registers (ISH-to-peer, 32x32-bit) |
| 0xE0-0x15C | INBOUND_MSG1-32 | 0x0 | Inbound Message Registers (peer-to-ISH, 32x32-bit) |
| 0x360-0x374 | REMAP0-5 | 0x0 | Address Remap Registers |
| 0x378 | IPC_BUSY_CLEAR | 0x0 | IPC Busy Clear |
| 0x6D0 | D0I3C | 0x8 | D0i3 Control Register |

### Additional Per-Channel Registers

| Channel | Offset | Register | Description |
|---------|--------|----------|-------------|
| CSE | 0x1380 | UMA0_BASE_LOW | UMA Base Address Low |
| CSE | 0x1384 | UMA0_BASE_HIGH | UMA Base Address High |
| CSE | 0x1388 | UMA0_LIMIT_LOW | UMA Limit Low |
| CSE | 0x138C | UMA0_LIMIT_HIGH | UMA Limit High |
| PMC | 0x26D4 | PMC2ISH_CSR | PMC-to-ISH Control/Status |
| CNVi | 0x36D4 | CNVI2ISH_CSR | CNVi-to-ISH Control/Status |
| ACE | 0x46D4 | ACE2ISH_CSR | ACE-to-ISH Control/Status |
| ESE | 0x56D4 | ESE2ISH_CSR | ESE-to-ISH Control/Status |
| ESE | 0x5380-0x539C | UMA0/UMA1 | Dual UMA registers |
| AVB | 0x66D4 | AVB2ISH_CSR | AVB-to-ISH Control/Status |

---

## Detailed Register Bit Fields

### PISR (Peripheral Interrupt Status) - Offset 0x00
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:28] | RESERVED0 | RO | Reserved |
| [27] | PISR_H2IBCISC | RW/1C | Inbound busy clear interrupt status clear |
| [26:1] | RESERVED1 | RO | Reserved |
| [0] | PISR_INBOUND | RO | Inbound IPC request status |

### PIMR (Peripheral Interrupt Mask) - Offset 0x04
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:28] | RESERVED0 | RO | Reserved |
| [27] | H2IBCISC_IE | RW | Mask for inbound busy clear interrupt |
| [26:12] | RESERVED1 | RO | Reserved |
| [11] | OUTBOUND_BUSY_CLEAR | RW | Mask for outbound busy clear |
| [10:1] | RESERVED2 | RO | Reserved |
| [0] | PIMR_INBOUND | RW | Reserved |

### HOST_PIMR (Peer-Accessible Interrupt Mask) - Offset 0x08
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:9] | RESERVED0 | RO | Reserved |
| [8] | INBOUND_BUSY_CLEAR | RW | Inbound busy clear interrupt mask |
| [7:1] | RESERVED1 | RO | Reserved |
| [0] | OUTBOUND_IPC | RW | Outbound IPC request interrupt mask |

### HOST_PISR (Peer-Accessible Interrupt Status) - Offset 0x0C
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:9] | RESERVED0 | RO | Reserved |
| [8] | INBOUND_BUSY_CLEAR | RW/1C | Inbound busy clear status |
| [7:1] | RESERVED1 | RO | Reserved |
| [0] | OUTBOUND_IPC | RO | Outbound IPC request status |

### CIM (Channel Interrupt Mask) - Offset 0x10
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:1] | RESERVED0 | RO | Reserved |
| [0] | CH_INTR_MASK | RW | 1=masked, 0=enabled |

### CIS (Channel Interrupt Status) - Offset 0x14
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:1] | RESERVED0 | RO | Reserved |
| [0] | CH_INTR_STATUS | RO | Set if any enabled interrupt sources active |

### ISH_HOST_FWSTS (Firmware Status) - Offset 0x34
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:0] | ISH_HOST_FWSTS | RO/RW | FW status (RO by peer, RW by ISH). Set to 0x0 on system reset or D3Cold wakeup. |

### HOST_COMM (Communication Register) - Offset 0x38
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:0] | HOST_COMM | RW/RO | Host communication (RW by peer, RO by ISH). Set to 0x0 on system reset or D3Cold wakeup. |

### INBOUND_DOORBELL (Peer-to-ISH Doorbell) - Offset 0x48
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31] | BUSY | RW | When cleared, ISH CPU ready for new message. Peer sets to 1 to ring doorbell. ISH asserts level-sensitive interrupt to IOAPIC while BUSY=1. ISH clears BUSY after reading. |
| [30:0] | PAYLOAD_31BIT | RW | 31-bit message payload (backward compatible short format) |

### OUTBOUND_DOORBELL (ISH-to-Peer Doorbell) - Offset 0x54
| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31] | BUSY | RW | When cleared, peer CPU ready for new message. ISH sets to 1 to ring doorbell. Setting bit 31 causes peer to receive interrupt. Peer clears BUSY after reading. |
| [30:0] | PAYLOAD_31BIT | RW | 31-bit message payload (backward compatible short format) |

### IPC_D0I3C (D0i3 Control) - Offset 0x6D0
| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [31:5] | RESERVED0 | RO | 0 | Reserved |
| [4] | IRC | RO | 0 | Interrupt Request Capable. Tied to 0 for ISH. |
| [3] | RR | RW/1C | 1 | Restore Required. Set by HW on initial power up. SW clears by writing 1. |
| [2] | D0i3 | RW | 0 | D0i3 State. SW sets to 1 for D0i3, writes 0 for D0i0. |
| [1] | IR | RW | 0 | Interrupt Required. SW sets to 1 for interrupt on command completion. |
| [0] | CIP | RO | 0 | Command In Progress. HW sets on D0i3 bit transitions. While set, other bits invalid. |

---

## D0ix Counter Registers (HOST channel)

| Offset | Register | Description |
|--------|----------|-------------|
| 0x500 | MAIN_CLK_CG_LOW | Main Clock CG Counter Low 32-bit |
| 0x504 | MAIN_CLK_CG_HIGH | Main Clock CG Counter High 32-bit |
| 0x508 | FUNC_CLK_CG_LOW | Functional Clock CG Counter Low 32-bit |
| 0x50C | FUNC_CLK_CG_HIGH | Functional Clock CG Counter High 32-bit |
| 0x510 | AON_CLK_CG_LOW | Always-On Clock CG Counter Low 32-bit |
| 0x514 | AON_CLK_CG_HIGH | Always-On Clock CG Counter High 32-bit |
| 0x518 | IPAPG_COUNT_LOW | IP Active Power Gate Counter Low 32-bit |
| 0x51C | IPAPG_COUNT_HIGH | IP Active Power Gate Counter High 32-bit |
| 0x520 | CCM_RET_LOW | CCM Retention Counter Low 32-bit |
| 0x524 | CCM_RET_HIGH | CCM Retention Counter High 32-bit |
| 0x528 | L2_RET_LOW | L2 Retention Counter Low 32-bit |
| 0x52C | L2_RET_HIGH | L2 Retention Counter High 32-bit |
| 0x530 | CCM_PG_LOW | CCM Power Gate Counter Low 32-bit |
| 0x534 | CCM_PG_HIGH | CCM Power Gate Counter High 32-bit |
| 0x538 | L2_PG_LOW | L2 Power Gate Counter Low 32-bit |
| 0x53C | L2_PG_HIGH | L2 Power Gate Counter High 32-bit |

---

## Common Properties

- **Power Domain**: VNNAON (all registers)
- **Reset**: FUNCRST (some also HOSTPRIMRST sync)
- **SAI Access (HOST)**: HOST_UNTRUSTED, HOST_MICROCODE, HOST_SMM, HOSTIA_SUNPASS, HOST_BOOT_BIOS, ISH, DFX_RED2, DFX_RED4, DFX_ORANGE
- **SAI Access (CSE)**: DFX_RED2, ISH, CSE_INTELUNLOCK, DFX_RED4, DFX_ORANGE
- **SAI Access (PMC)**: PMC, ISH, DFX_RED2, DFX_RED4, DFX_ORANGE
- **Message Payload**: 32 x 32-bit registers = 128 bytes per direction per channel
- **Doorbell Protocol**: Sender writes payload to MSG regs, sets BUSY=1 in doorbell. Receiver reads payload, clears BUSY.

---

## Section Index (from PDF TOC)

1. ish_ipc_host_mmio_sub_MEM - HOST IPC registers (MMIO)
2. ish_ipc_hostspare_mmio_sub_MEM - HOST Spare IPC registers (MMIO)
3. file_iosf2axi_pci_configreg_CFG - PCI Configuration Space
4. ish_ipc_host_mmio_sub_MSG - HOST IPC registers (Sideband)
5. ish_ipc_hostspare_mmio_sub_MSG - HOST Spare IPC registers (Sideband)
6. ish_ipc_cse_pvtcr_sub_MSG - CSE IPC registers (Sideband)
7. ish_ipc_pmc_pvtcr_sub_MSG - PMC IPC registers (Sideband)
8. ish_ipc_cnvi_pvtcr_sub_MSG - CNVi IPC registers (Sideband)
9. ish_ipc_ace_pvtcr_sub_MSG - ACE IPC registers (Sideband)
10. ish_ipc_ese_pvtcr_sub_MSG - ESE IPC registers (Sideband)
11. ish_ipc_avb_pvtcr_sub_MSG - AVB IPC registers (Sideband)
12. ish_security_block_pvtcr_sub_MSG - Security Block registers
13. ish_dashboard_block_pvtcr_sub_MSG - Dashboard Block registers
14. file_iosf2axi_private_configreg - IOSF2AXI Private Config
15. file_iosf2axi_pci_configreg_MSG - IOSF2AXI PCI Config (Sideband)

**Raw text file**: ish_wrapper_host_raw.txt (39,588 lines) retained for further extraction.
