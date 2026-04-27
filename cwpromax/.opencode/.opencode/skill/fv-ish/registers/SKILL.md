# FV-ISH Registers Skill — ISH Register Maps & MMIO Definitions

> **Skill**: `fv-ish/registers`
> **Owner**: Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team**: CVE - ISH Validation
> **Last Updated**: 2026-03-16 (rev2.0 — TTL HAS data integrated)
> **Primary Platform**: NVL (Nova Lake)
> **HAS-Verified Platform**: TTL (Titan Lake) — ISH 5.9

---

## Skill Identity

You are the ISH register map and MMIO definition skill. You provide register offsets, bit field definitions, PCI configuration space details, and register access patterns for ISH validation.

**HAS-First Policy**: TTL register data in this skill is verified against ISH 5.9 OSXML register PDFs (ish_wrapper_host.pdf, ish_mia_bfm_rdl_top.pdf). NVL data remains placeholder — **always load `fv-ish/has` and verify against the ISH NVL HAS before using NVL register definitions in test scripts.**

---

## HAS Verification Reminder

Before providing any register definition:
1. Load `fv-ish/has` skill
2. Search local HAS: `grep -ri "<register_name>" .opencode/skill/fv-ish/has/docs/`
3. If not found locally, query Co-De Sign for the authoritative definition
4. Prefix any unverified value with: `[UNVERIFIED — confirm against HAS]`

---

## PCI Configuration Space

### TTL (Titan Lake) — HAS-Verified (ISH 5.9)

Source: `ish_wrapper_host.pdf`, Section `file_iosf2axi_pci_configreg_CFG`

| Offset | Register | Default | Description |
|--------|----------|---------|-------------|
| 0x00 | DEVVENDID | `0xE4458086` | Device ID=`0xE445`, Vendor ID=`0x8086` |
| 0x04 | STATUSCOMMAND | `0x00100000` | PCI Status/Command |
| 0x08 | REVCLASSCODE | `0x00000000` | Revision/Class Code |
| 0x0C | CLLATHHEADERBIST | `0x00000000` | Cache Line/Latency/Header/BIST |
| 0x10 | BAR | `0x00000000` | Base Address Register (low 32-bit), MMIO 64-bit |
| 0x14 | BAR_HIGH | `0x00000000` | Base Address Register (high 32-bit) |
| 0x18 | BAR1 | `0x00000000` | Base Address Register 1 (low 32-bit) |
| 0x1C | BAR1_HIGH | `0x00000000` | Base Address Register 1 (high 32-bit) |
| 0x2C | SUBSYSTEMID | `0x00000000` | Subsystem ID |
| 0x34 | CAPABILITYPTR | `0x00000080` | Capability Pointer → `0x80` |
| 0x3C | INTERRUPTREG | `0x00000100` | Interrupt Register |
| 0x80 | POWERCAPID | `0x48030001` | Power Management Capability |
| 0x84 | PMECTRLSTATUS | `0x00000008` | PM Control & Status |
| 0x90 | PCIDEVIDLE_CAP_RECORD | `0xF0140009` | PCI Device Idle Vendor Cap |
| 0x94 | DEVID_VEND_SPECIFIC_REG | `0x01400010` | Vendor Specific Extended Cap |
| 0x98 | D0I3_CONTROL_SW_LTR_MMIO_REG | `0x00000000` | SW LTR Update MMIO Location |
| 0x9C | DEVICE_IDLE_POINTER_REG | `0x00000000` | Device Idle Pointer |
| 0xA0 | D0I3_MAX_POW_LAT_PG_CONFIG | `0x00280800` | D0i3 & Power Control Enable |
| 0xC0 | GEN_INPUT_REG | `0x00000000` | General Purpose Input |
| 0xD0 | MSI_CAP_REG | `0x01800005` | MSI Capability |

### NVL (Nova Lake) — Placeholder

| Field | Value | Notes |
|-------|-------|-------|
| Vendor ID | `0x8086` | Intel |
| Device ID | `0x6E78` | Verify per stepping |
| Class Code | `0x112000` | NVL ISH class code |
| BAR0 | MMIO, 64-bit | ISH register space |

### Platform Device ID Reference

| Platform | Device ID | ISH Version | Status |
|----------|-----------|-------------|--------|
| **TTL** | `0xE445` | ISH 5.9 | **HAS-Verified** |
| **NVL** | `0x6E78` | ISH 5.8 | Primary — verify from NVL HAS |
| MTL | `[TODO]` | | |
| LNL | `[TODO]` | | |
| PTL | `[TODO]` | | |
| ARL | `[TODO]` | | |

> **Linux kernel reference**: `drivers/hid/intel-ish-hid/ipc/pci-ish.c` — `ish_pci_tbl[]`

---

## ISH HOST Wrapper Register Map (BAR0 + Offset) — TTL HAS-Verified

Source: `ish_wrapper_host.pdf` (OSXML), `TTL_ISH_Register_Reference.md`

### IPC Channel Architecture

ISH uses an IPC (Inter-Processor Communication) doorbell/mailbox model — **NOT** classic HECI circular buffers. 8 IPC channels with identical per-channel register layouts:

| Channel | Host-Side Base | MIA-Side Base | Bus Type | SAI PolicyGroup | Description |
|---------|---------------|---------------|----------|-----------------|-------------|
| HOST | `0x000` | `0x04100000` | MEM | ISH_IPC_HOST2ISH_GP | Primary host driver interface |
| HOSTSPARE | `0x000` (sep. space) | `0x04101000` | MEM | ISH_IPC_HOST2ISH_GP | Spare host channel |
| CSE | `0x1000` | `0x04102000` | MSG | ISH_IPC_CSME2ISH_GP | CSME/Security Engine |
| PMC | `0x2000` | `0x04103000` | MSG | ISH_IPC_PMC2ISH_GP | Power Management Controller |
| CNVi | `0x3000` | `0x04104000` | MSG | ISH_IPC_CNVI2ISH_GP | Connectivity (WiFi/BT) |
| ACE | `0x4000` | `0x04105000` | MSG | ISH_IPC_ACE2ISH_GP | Audio/Comms Engine |
| ESE | `0x5000` | `0x04106000` | MSG | ISH_IPC_ESE2ISH_GP | Embedded Security Engine |
| AVB | `0x6000` | `0x04107000` | MSG | ISH_IPC_AVB2ISH_GP | Audio/Video Bridge |

### Per-Channel Register Layout (offsets relative to channel base)

| Offset | Register | Default | Access | Description |
|--------|----------|---------|--------|-------------|
| `0x00` | PISR | `0x0` | RO/RW1C | Peripheral Interrupt Status. [27]=H2IBCISC(RW/1C), [0]=INBOUND(RO) |
| `0x04` | PIMR | `0x0` | RW | Peripheral Interrupt Mask. [27]=H2IBCISC_IE, [11]=OUTBOUND_BUSY_CLEAR, [0]=PIMR_INBOUND |
| `0x08` | HOST_PIMR | `0x0` | RW | Peer-accessible Interrupt Mask. [8]=INBOUND_BUSY_CLEAR, [0]=OUTBOUND_IPC |
| `0x0C` | HOST_PISR | `0x0` | RO/RW1C | Peer-accessible Interrupt Status. [8]=INBOUND_BUSY_CLEAR(RW/1C), [0]=OUTBOUND_IPC(RO) |
| `0x10` | CIM | `0x0` | RW | Channel Interrupt Mask. [0]=CH_INTR_MASK (1=masked, 0=enabled) |
| `0x14` | CIS | `0x0` | RO | Channel Interrupt Status. [0]=CH_INTR_STATUS |
| `0x34` | FWSTS | `0x0` | RO/RW | Firmware Status (RO by peer, RW by ISH). Cleared on reset/D3Cold. |
| `0x38` | COMM | `0x0` | RW/RO | Communication Register (RW by peer, RO by ISH). Cleared on reset/D3Cold. |
| `0x48` | INBOUND_DOORBELL | `0x0` | RW | Peer-to-ISH doorbell. **[31]=BUSY**, [30:0]=PAYLOAD |
| `0x54` | OUTBOUND_DOORBELL | `0x0` | RW | ISH-to-peer doorbell. **[31]=BUSY**, [30:0]=PAYLOAD |
| `0x60`–`0xDC` | OUTBOUND_MSG1-32 | `0x0` | RW | Outbound message registers (32×32-bit = 128 bytes) |
| `0xE0`–`0x15C` | INBOUND_MSG1-32 | `0x0` | RO | Inbound message registers (32×32-bit = 128 bytes) |
| `0x360`–`0x374` | REMAP0-5 | varies | RW | Address remap registers (6×32-bit) |
| `0x378` | IPC_BUSY_CLEAR | `0x0` | RW | IPC Busy Clear |
| `0x500`–`0x53C` | D0IX_COUNTERS | `0x0` | RW | D0ix transition counters (see below) |
| `0x6D0` | D0I3C | `0x8` | RW | D0i3 Control Register |

### PISR Bit Fields — Offset `0x00`

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:28] | RESERVED0 | RO | Reserved |
| [27] | PISR_H2IBCISC | RW/1C | Inbound busy clear interrupt status clear |
| [26:1] | RESERVED1 | RO | Reserved |
| [0] | PISR_INBOUND | RO | Inbound IPC request status (BUSY=1 in inbound doorbell) |

### PIMR Bit Fields — Offset `0x04`

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [27] | H2IBCISC_IE | RW | Mask for inbound busy clear interrupt |
| [11] | OUTBOUND_BUSY_CLEAR | RW | Mask for outbound busy clear |
| [0] | PIMR_INBOUND | RW | Mask for inbound IPC interrupt |

### HOST_PIMR Bit Fields — Offset `0x08`

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [8] | INBOUND_BUSY_CLEAR | RW | Inbound busy clear interrupt mask |
| [0] | OUTBOUND_IPC | RW | Outbound IPC request interrupt mask |

### HOST_PISR Bit Fields — Offset `0x0C`

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [8] | INBOUND_BUSY_CLEAR | RW/1C | Inbound busy clear status |
| [0] | OUTBOUND_IPC | RO | Outbound IPC request status |

### INBOUND_DOORBELL / OUTBOUND_DOORBELL Bit Fields

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31] | BUSY | RW | Doorbell active. Sender sets to 1, receiver clears after reading. Level-sensitive interrupt to IOAPIC while BUSY=1. |
| [30:0] | PAYLOAD_31BIT | RW | 31-bit message payload (short format, backward compatible) |

### D0I3C (D0i3 Control) — Offset `0x6D0`

| Bits | Field | Access | Default | Description |
|------|-------|--------|---------|-------------|
| [4] | IRC | RO | 0 | Interrupt Request Capable. Tied to 0 for ISH. |
| [3] | RR | RW/1C | 1 | Restore Required. Set by HW on initial power up. SW clears by writing 1. |
| [2] | D0i3 | RW | 0 | D0i3 State. SW sets 1=D0i3, writes 0=D0i0. |
| [1] | IR | RW | 0 | Interrupt Required. SW sets 1 for interrupt on command completion. |
| [0] | CIP | RO | 0 | Command In Progress. HW sets on D0i3 bit transitions. While set, other bits invalid. |

### D0ix Counter Registers — Offsets `0x500`–`0x53C` (HOST channel)

| Offset | Register | Description |
|--------|----------|-------------|
| `0x500` | MAIN_CLK_CG_LOW | Main Clock CG Counter Low 32-bit |
| `0x504` | MAIN_CLK_CG_HIGH | Main Clock CG Counter High 32-bit |
| `0x508` | FUNC_CLK_CG_LOW | Functional Clock CG Counter Low 32-bit |
| `0x50C` | FUNC_CLK_CG_HIGH | Functional Clock CG Counter High 32-bit |
| `0x510` | AON_CLK_CG_LOW | Always-On Clock CG Counter Low 32-bit |
| `0x514` | AON_CLK_CG_HIGH | Always-On Clock CG Counter High 32-bit |
| `0x518` | IPAPG_COUNT_LOW | IP Active Power Gate Counter Low 32-bit |
| `0x51C` | IPAPG_COUNT_HIGH | IP Active Power Gate Counter High 32-bit |
| `0x520` | CCM_RET_LOW | CCM Retention Counter Low 32-bit |
| `0x524` | CCM_RET_HIGH | CCM Retention Counter High 32-bit |
| `0x528` | L2_RET_LOW | L2 Retention Counter Low 32-bit |
| `0x52C` | L2_RET_HIGH | L2 Retention Counter High 32-bit |
| `0x530` | CCM_PG_LOW | CCM Power Gate Counter Low 32-bit |
| `0x534` | CCM_PG_HIGH | CCM Power Gate Counter High 32-bit |
| `0x538` | L2_PG_LOW | L2 Power Gate Counter Low 32-bit |
| `0x53C` | L2_PG_HIGH | L2 Power Gate Counter High 32-bit |

### Additional Per-Channel Registers

| Channel | Offset | Register | Description |
|---------|--------|----------|-------------|
| CSE | `0x1380` | UMA0_BASE_LOW | UMA Base Address Low |
| CSE | `0x1384` | UMA0_BASE_HIGH | UMA Base Address High |
| CSE | `0x1388` | UMA0_LIMIT_LOW | UMA Limit Low |
| CSE | `0x138C` | UMA0_LIMIT_HIGH | UMA Limit High |
| PMC | `0x26D4` | PMC2ISH_CSR | PMC-to-ISH Control/Status |
| CNVi | `0x36D4` | CNVI2ISH_CSR | CNVi-to-ISH Control/Status |
| ACE | `0x46D4` | ACE2ISH_CSR | ACE-to-ISH Control/Status |
| ESE | `0x56D4` | ESE2ISH_CSR | ESE-to-ISH Control/Status |
| ESE | `0x5380`–`0x539C` | UMA0/UMA1 | Dual UMA registers |
| AVB | `0x66D4` | AVB2ISH_CSR | AVB-to-ISH Control/Status |

---

## ISH MIA Internal Register Map — TTL HAS-Verified

Source: `ish_mia_bfm_rdl_top.pdf` (OSXML), `TTL_ISH_MIA_Register_Reference.md`

### MIA Address Map Summary

| Block | Base Address | Instances | Stride | Description |
|-------|-------------|-----------|--------|-------------|
| I2C | `0x00000000` | 3 | `0x2000` | DW_apb_i2c controller |
| GPIO | `0x00100000` | 1 | — | ISH GPIO controller |
| IPC | `0x04100000` | 8 | `0x1000` | IPC channels (HOST–AVB) |
| PMU | `0x04200000` | 1 | — | Power Management Unit |
| CCU | `0x04300000` | 1 | — | Clock Control Unit |
| Misc | `0x04400000` | 1 | — | Misc config |
| SBEP | `0x04500000` | 1 | — | Sideband Endpoint |
| HPET | `0x04700000` | 1 | — | High Precision Event Timer |
| I3C | `0x04800000` | 2 | `0x2000` | I3C HCI controller |
| WDT | `0x04900000` | 1 | — | Watchdog Timer |
| Security | `0x04A00000` | 1 | — | Security Block |
| SPI | `0x08000000` | 2 | `0x2000` | DW_apb_ssi controller |
| UART | `0x08100000` | 3 | `0x2000` | DW_apb_uart controller |
| DMA Misc | `0x10101000` | 1 (8ch) | — | DMA channel config |
| SRAM Ctrl | `0x10500000` | 1 | — | SRAM controller |
| Fabric | `0x10600000` | 1 | — | Fabric error logging |

### Key MIA Registers (by domain — see domain-specific skills for full details)

#### PMU Registers (Base `0x04200000`) → See `fv-ish/power`

| Offset | Register | Default | Key Function |
|--------|----------|---------|-------------|
| `0x00` | PMU_SRAM_PG_EN | `0x3FFFFFFF` | Per-bank SRAM power gate (30 bits: 15 banks × 2 tiles) |
| `0x08` | PMU_HOST_WAKEUP | `0x0` | Host wake / PME control |
| `0x0C` | PMU_ISH_WAKE_EVENT | `0x0` | Wake event record (RW/1C) |
| `0x10` | PMU_ISH_MASK_EVENT | `0x0` | Wake event mask |
| `0x18` | PMU_ISH_FABRIC_CNT | `0x3A980008` | Fabric idle/timeout config |
| `0x3C` | PMU_VNN_REQ | `0x0` | VNN request assert (32-bit, per-bit RW/1S/1C) |
| `0x40` | PMU_VNN_REQ_ACK | `0x0` | VNN request/acknowledge status |

#### DMA Misc Registers (Base `0x10101000`) → See `fv-ish/dma`

| Offset | Register | Default | Key Function |
|--------|----------|---------|-------------|
| `0x00`–`0x1C` | DMA_CTL_CH0–CH7 | `0x0` | Per-channel DMA control |

Per-channel bits: [10]=LLI_MODE, [9]=WR_NON_SNOOP, [8]=RD_NON_SNOOP, [6:5]=WR_RS, [4:3]=RD_RS, [1:0]=TRANSFER_MODE (0=Int→Int, 1=Int→Ext, 2=Ext→Int, 3=Ext→Ext). RS values: 0=RS0(Host DRAM), 3=RS3(IMR DRAM).

#### SRAM Controller Registers (Base `0x10500000`) → See `fv-ish/debug`

| Offset | Register | Default | Key Function |
|--------|----------|---------|-------------|
| `0x00` | SRAM_CFGR | `0x0` | Config: [4]=ECC_DISABLE, [3]=DISABLE_SPEC_RMW |
| `0x04` | SRAM_INTR_STS | `0x0` | Interrupt status (RW/1C) |
| `0x08` | SRAM_INTR_MASK | `0x74` | Interrupt mask |
| `0x0C` | SRAM_ERASE_CTRL | `0x0` | Erase engine control |
| `0x20` | SRAM_LOG_EN | `0x0` | ECC logging enable |
| `0x24` | SRAM_DOUBLE_ERR_ECC_LOG | `0x0` | Double-bit ECC error log |
| `0x30` | SRAM_SINGLE_ERR_ECC_LOG | `0x0` | Single-bit ECC error log |
| `0x40` | SRAM_LIMIT | `0x0` | [29:20]=CCM_LIMIT, [9:0]=ICCM_LIMIT (4KB units) |

#### CCU Registers (Base `0x04300000`) → See `fv-ish/power`

| Offset | Register | Default | Key Function |
|--------|----------|---------|-------------|
| `0x00` | TRUNK_CG | `0x0` | [0]=Trunk clock gate on Halt |
| `0x08` | UART_BLK_CG | `0x0` | [2:0]=Per-UART instance CG |
| `0x0C` | I2C_BLK_CG | `0x0` | [2:0]=Per-I2C instance CG |
| `0x10` | SPI_BLK_CG | `0x0` | [1:0]=Per-SPI instance CG |
| `0x14` | GPIO_BLK_CG | `0x0` | [0]=GPIO block CG |
| `0x28` | DMA_BLK_CG | `0x0` | [0]=DMA block CG |
| `0x3C` | RST_HIS | `0x0` | Reset history: [4]=ESE_SW, [3]=SRECC, [2]=MIASS, [1]=WD, [0]=CSE_SW |

#### WDT Registers (Base `0x04900000`) → See `fv-ish/driver`

| Offset | Register | Default | Key Function |
|--------|----------|---------|-------------|
| `0x00` | WDTC | `0xA0A0` | [17]=WDT_EN, [15:8]=T2_LOAD, [7:0]=T1_LOAD |
| `0x04` | WDTR | `0x0` | [0]=WDT_RL (write 1 to reload, auto-clears) |
| `0x08` | WDTV | `0xA0A0` | [15:8]=T2_VAL(RO), [7:0]=T1_VAL(RO) |

---

## Common Properties (TTL)

- **Power Domain**: VNNAON (all HOST wrapper and most MIA registers)
- **Reset**: FUNCRST (some also HOSTPRIMRST sync)
- **SAI Access (HOST)**: HOST_UNTRUSTED, HOST_MICROCODE, HOST_SMM, HOSTIA_SUNPASS, HOST_BOOT_BIOS, ISH, DFX_RED2, DFX_RED4, DFX_ORANGE
- **SAI Access (CSE)**: DFX_RED2, ISH, CSE_INTELUNLOCK, DFX_RED4, DFX_ORANGE
- **SAI Access (PMC)**: PMC, ISH, DFX_RED2, DFX_RED4, DFX_ORANGE
- **Message Payload**: 32 × 32-bit registers = **128 bytes per direction per channel**
- **Doorbell Protocol**: Sender writes payload to MSG regs, sets BUSY=1 in doorbell. Receiver reads payload, clears BUSY. Level-sensitive interrupt to IOAPIC while BUSY=1.

---

## Register Access via PythonSV

### Namednode Initialization

```python
# Standard ISH namednode access pattern
import pythonsv

class IshTestBase:
    def setup(self):
        self.target = pythonsv.itp.targets[0]
        self.pch_ish = getattr(self.target, "ish")

    def read_fw_status(self):
        """Read ISH firmware status register (HOST IPC FWSTS at offset 0x34)."""
        return self.pch_ish.mem.ish_fwsts.read()

    def read_doorbell_busy(self):
        """Check if inbound doorbell BUSY bit is set."""
        db = self.pch_ish.mem.ish_inbound_doorbell.read()
        return bool(db & (1 << 31))

    def is_fw_ready(self):
        """Check ISH firmware status for ready state."""
        status = self.read_fw_status()
        return status != 0  # Non-zero FWSTS indicates FW has booted

    def wait_fw_ready(self, timeout_sec=10):
        """Poll ISH firmware ready with timeout."""
        import time
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.is_fw_ready():
                return True
            time.sleep(0.1)
        return False
```

### IPC Register Access Patterns (TTL)

```python
# Read HOST channel registers (BAR0-based)
bar0_base = pch_ish.config.bar0.read() & ~0xF

# HOST IPC registers
PISR_OFF          = 0x00
PIMR_OFF          = 0x04
HOST_PIMR_OFF     = 0x08
HOST_PISR_OFF     = 0x0C
FWSTS_OFF         = 0x34
COMM_OFF          = 0x38
INBOUND_DB_OFF    = 0x48
OUTBOUND_DB_OFF   = 0x54
OUTBOUND_MSG1_OFF = 0x60   # 32 DWORDs: 0x60–0xDC
INBOUND_MSG1_OFF  = 0xE0   # 32 DWORDs: 0xE0–0x15C
D0I3C_OFF         = 0x6D0

# Read firmware status
fwsts = pch_ish.mem.read32(bar0_base + FWSTS_OFF)
print(f"ISH FWSTS: 0x{fwsts:08X}")

# Read inbound doorbell
db = pch_ish.mem.read32(bar0_base + INBOUND_DB_OFF)
busy = (db >> 31) & 1
payload = db & 0x7FFFFFFF
print(f"Inbound DB: BUSY={busy}, PAYLOAD=0x{payload:07X}")

# Send IPC message: write payload to outbound MSG regs, then ring doorbell
def ipc_send(pch_ish, bar0, payload_dwords):
    """Send IPC message via outbound MSG + doorbell."""
    for i, dw in enumerate(payload_dwords):
        pch_ish.mem.write32(bar0 + OUTBOUND_MSG1_OFF + (i * 4), dw)
    # Ring doorbell: set BUSY=1
    pch_ish.mem.write32(bar0 + OUTBOUND_DB_OFF, 0x80000000)

# Read D0i3 control
d0i3c = pch_ish.mem.read32(bar0_base + D0I3C_OFF)
cip = d0i3c & 1              # Command In Progress
ir  = (d0i3c >> 1) & 1       # Interrupt Required
d0i3 = (d0i3c >> 2) & 1      # D0i3 state
rr  = (d0i3c >> 3) & 1       # Restore Required
print(f"D0I3C: CIP={cip} IR={ir} D0i3={d0i3} RR={rr}")

# Request D0i3 entry
def request_d0i3(pch_ish, bar0):
    """Request ISH D0i3 via D0I3C register."""
    import time
    pch_ish.mem.write32(bar0 + D0I3C_OFF, 0x04)  # Set D0i3=1
    for _ in range(100):
        val = pch_ish.mem.read32(bar0 + D0I3C_OFF)
        if not (val & 1):  # CIP cleared = command complete
            return True
        time.sleep(0.001)
    return False

# Unmask HOST outbound IPC interrupt
pch_ish.mem.write32(bar0_base + HOST_PIMR_OFF, 0x01)  # OUTBOUND_IPC mask=1 (enabled)

# Clear HOST_PISR interrupt
pisr = pch_ish.mem.read32(bar0_base + HOST_PISR_OFF)
if pisr & (1 << 8):  # INBOUND_BUSY_CLEAR
    pch_ish.mem.write32(bar0_base + HOST_PISR_OFF, (1 << 8))  # W1C
```

---

## Validation Points

### PCI Enumeration
- [ ] ISH device appears on PCI bus with correct Device ID for platform (TTL: `0xE445`)
- [ ] Vendor ID = `0x8086`
- [ ] BAR0 is 64-bit MMIO, programmed by BIOS
- [ ] Command register has Memory Space Enable bit set
- [ ] Capability Pointer at `0x34` = `0x80` (Power Management Cap)

### Register Reset Values (TTL-verified)
- [ ] `FWSTS` (0x34) = `0x0` immediately after power-on (before FW loads)
- [ ] `D0I3C` (0x6D0) = `0x8` (RR=1, all others 0)
- [ ] `PISR` (0x00) = `0x0`
- [ ] `PIMR` (0x04) = `0x0` (all interrupts initially unmasked)
- [ ] `COMM` (0x38) = `0x0`
- [ ] Reserved bits read as `0`

### IPC Doorbell Handshake
- [ ] Host writes payload to OUTBOUND_MSG1-32, sets BUSY=1 in OUTBOUND_DB
- [ ] ISH receives interrupt, reads INBOUND_MSG1-32, clears BUSY
- [ ] HOST_PISR.OUTBOUND_IPC set when ISH rings outbound doorbell
- [ ] Interrupt cleared correctly (write-1-to-clear)

### Firmware Boot Sequence
- [ ] `FWSTS` changes from `0x0` to non-zero after FW loads
- [ ] `D0I3C.RR` = `1` after initial power-up (Restore Required set by HW)
- [ ] `D0I3C.CIP` = `0` when no D0i3 transition in progress

### D0ix Counter Verification
- [ ] D0ix counters at `0x500`–`0x53C` increment during CG/PG transitions
- [ ] IPAPG_COUNT increments during IP Active Power Gate
- [ ] CCM_PG_COUNT increments during CCM power gating

---

## TTL HAS Reference Documents

| Document | Content | Location |
|----------|---------|----------|
| `TTL_ISH_Register_Reference.md` | HOST wrapper registers (PCI, IPC channels, bit fields) | `.opencode/skill/fv-ish/has/docs/ttl/` |
| `TTL_ISH_MIA_Register_Reference.md` | MIA internal registers (all 16 blocks, full bit fields) | `.opencode/skill/fv-ish/has/docs/ttl/` |
| `ish_wrapper_host_raw.txt` | Raw OSXML text (39,588 lines) | `.opencode/skill/fv-ish/has/docs/ttl/` |
| `ish_mia_bfm_rdl_top_raw.txt` | Raw OSXML text (80,645 lines) | `.opencode/skill/fv-ish/has/docs/ttl/` |

---

## Linux Kernel Reference (Public)

Key files in `drivers/hid/intel-ish-hid/`:

| File | Relevant Definitions |
|------|---------------------|
| `ipc/ipc.h` | Register offset macros (IPC_REG_*), doorbell definitions |
| `ipc/ipc.c` | IPC send/receive, ISR handler, doorbell mechanism |
| `ipc/pci-ish.c` | PCI Device IDs (`ish_pci_tbl`), BAR0 mapping |
| `ishtp/hbm.h` | HBM message format definitions |

> Repo: https://github.com/torvalds/linux/tree/master/drivers/hid/intel-ish-hid
