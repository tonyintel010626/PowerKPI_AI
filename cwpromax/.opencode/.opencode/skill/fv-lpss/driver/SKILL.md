---
name: fv-lpss/driver
description: "LPSS driver analysis — Linux i2c-designware/dw-i3c-master/spi-dw/8250_lpss and Windows SerialIO drivers, cross-platform behavioral differences, PCI matching, power management hooks"
version: "rev1.0"
---

# LPSS Driver Sub-Skill

> **Owner:** Kong Jia Wen (kjwen) — Client FV, LPSS/SerialIO
>
> **See also:** `fv-lpss/debug` for triage flows, `fv-lpss/config-checkout` for PCI enumeration, `fv-lpss/power-state` for PM registers

---

## Driver Codebases

| Codebase | Location | Protocol | Version/Branch |
|----------|----------|----------|----------------|
| **Linux i2c-designware** | `drivers/i2c/busses/i2c-designware-*.c` | I2C | Kernel 6.x+ |
| **Linux dw-i3c-master** | `drivers/i3c/master/dw-i3c-master.c` | I3C | Kernel 6.x+ |
| **Linux spi-dw** | `drivers/spi/spi-dw-pci.c`, `spi-dw-core.c` | SPI | Kernel 6.x+ |
| **Linux 8250_lpss** | `drivers/tty/serial/8250/8250_lpss.c` | UART | Kernel 6.x+ |
| **Windows iaLPSS2 I2C** | `iaLPSS2_I2C_PTL.sys` / `.inf` | I2C | v30.100.2510.55 (PTL) |
| **Windows iaLPSS2 I3C** | `iaLPSS2_I3C_PTL.sys` / `.inf` | I3C | v30.100.2510.55 (PTL) |
| **Windows iaLPSS2 SPI** | `iaLPSS2_SPI_PTL.sys` / `.inf` | SPI | v30.100.2510.55 (PTL) |
| **Windows iaLPSS2 UART** | `iaLPSS2_UART2_PTL.sys` / `.inf` | UART | v30.100.2510.55 (PTL) |
| **Windows iaLPSS2 GPIO** | `iaLPSS2_GPIO2_PTL.sys` / `.inf` | GPIO | v30.100.2510.55 (PTL) |

---

## Cross-Driver Architecture Comparison

| Aspect | Linux I2C | Linux I3C | Linux SPI | Linux UART | Windows SerialIO |
|--------|-----------|-----------|-----------|------------|------------------|
| **Framework** | i2c-core + i2c-designware-pcidrv | i3c-core + dw-i3c-master | spi-core + spi-dw-pci | 8250/serial-core + 8250_lpss | WDF KMDF + SpbCx (I2C/SPI) / SerCx (UART) / Standalone (I3C/GPIO) |
| **Probe** | `i2c_dw_pci_probe()` | `dw_i3c_master_probe()` | `dw_spi_pci_probe()` | `lpss8250_probe()` | `EvtDeviceAdd` + `EvtDevicePrepareHardware` |
| **DMA** | Optional (platform DMA) | Ring-based (HCI) | DW-DMA or platform DMA | DW-DMA or PIO | iDMA 64-bit scatter/gather |
| **PM Runtime** | `pm_runtime_*` | `pm_runtime_*` | `pm_runtime_*` | `pm_runtime_*` | WDF idle/wake power policy |
| **D3 Entry** | `dw_i2c_plat_suspend()` | `dw_i3c_master_suspend()` | `spi_dw_suspend()` | `lpss8250_suspend()` | `EvtDeviceD0Exit` |
| **D3 Exit** | `dw_i2c_plat_resume()` | `dw_i3c_master_resume()` | `spi_dw_resume()` | `lpss8250_resume()` | `EvtDeviceD0Entry` |
| **Bus lock** | `i2c_lock_bus()` mutex | `i3c_bus_lock()` | `spi_bus_lock()` | UART port lock (spinlock) | SpbCx serialize |
| **Error recovery** | `i2c_dw_handle_tx_abort()` | `dw_i3c_master_irq_handler()` | SPI abort + FIFO flush | Break detect + FIFO flush | Driver-specific error handler |

---

## Driver Discovery & PCI Enumeration

### PCI Matching Flow

```
PCI Bus Scan
  → Vendor ID = 0x8086 (Intel)
    → Device ID match in pci_device_id table
      → Linux: probe() called
      → Windows: EvtDeviceAdd() called
        → BAR0 mapped for MMIO register access
          → IP version checked (IC_COMP_PARAM_1 / HCI_VERSION)
            → Controller initialized per capabilities
```

### PCI Device ID Tables (NVL)

**NVL PCD-H:**

| Controller | Device ID | BDF | Linux Driver |
|-----------|-----------|-----|--------------|
| I2C0 | 0xD215 | 21:0.0 | i2c-designware-pcidrv |
| I2C1 | 0xD216 | 21:0.1 | i2c-designware-pcidrv |
| I2C2 | 0xD217 | 21:0.2 | i2c-designware-pcidrv |
| I2C3 | 0xD218 | 21:0.3 | i2c-designware-pcidrv |
| I2C4 | 0xD219 | 21:1.0 | i2c-designware-pcidrv |
| I2C5 | 0xD21A | 21:1.1 | i2c-designware-pcidrv |
| SPI0 | 0xD227 | 30:4.0 | spi-dw-pci |
| SPI1 | 0xD228 | 30:4.1 | spi-dw-pci |
| SPI2 | 0xD229 | 30:4.2 | spi-dw-pci |
| UART0 | 0xD22A | 30:3.0 | 8250_lpss |
| UART1 | 0xD22B | 30:3.1 | 8250_lpss |
| UART2 | 0xD22C | 30:3.2 | 8250_lpss |
| I3C Ctrl#1 | 0xD37C | 17:0.0 | dw-i3c-master |
| I3C Ctrl#2 | 0xD36F | 17:2.0 | dw-i3c-master |

> **WARNING:** These Device IDs are from cached reference. Always verify against HAS via Co-Design for your specific stepping.

**PTL (from iaLPSS2 v30.100.2510.55 INF files — verified):**

| Controller | Device ID | Windows Driver | Windows Dependency | ETW Provider GUID |
|-----------|-----------|---------------|-------------------|-------------------|
| I2C0 | 0xE478 | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| I2C1 | 0xE479 | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| I2C2 | 0xE47A | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| I2C3 | 0xE47B | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| I2C4 | 0xE450 | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| I2C5 | 0xE451 | iaLPSS2_I2C_PTL.sys | SpbCx | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` |
| SPI0 | 0xE427 | iaLPSS2_SPI_PTL.sys | SpbCx | `{6E112845-A8C4-4143-A631-256E8A3E7691}` |
| SPI1 | 0xE430 | iaLPSS2_SPI_PTL.sys | SpbCx | `{6E112845-A8C4-4143-A631-256E8A3E7691}` |
| SPI2 | 0xE446 | iaLPSS2_SPI_PTL.sys | SpbCx | `{6E112845-A8C4-4143-A631-256E8A3E7691}` |
| UART0 | 0xE425 | iaLPSS2_UART2_PTL.sys | SerCx | `{B87CAA6F-37A7-4F09-8DC4-D15572C5904E}` |
| UART1 | 0xE426 | iaLPSS2_UART2_PTL.sys | SerCx | `{B87CAA6F-37A7-4F09-8DC4-D15572C5904E}` |
| UART2 | 0xE452 | iaLPSS2_UART2_PTL.sys | SerCx | `{B87CAA6F-37A7-4F09-8DC4-D15572C5904E}` |
| I3C Ctrl#1 | 0xE47C | iaLPSS2_I3C_PTL.sys | None (standalone) | `{46BA0297-8886-4B8B-97C0-02C51A4829C4}` |
| I3C Ctrl#2 | 0xE46F | iaLPSS2_I3C_PTL.sys | None (standalone) | `{46BA0297-8886-4B8B-97C0-02C51A4829C4}` |
| GPIO | ACPI\INTC105F | iaLPSS2_GPIO2_PTL.sys | None (standalone) | `{63848cff-3ec7-4ddf-8072-5f95e8c8eb98}` |

> **Key PTL Observations (from INF analysis):**
> - All drivers enable **WdfDirectedPowerTransitionEnable=1** (Directed Framework / DFx) and **DmaRemappingCompatible=1** (VT-d ready)
> - I2C and SPI depend on **SpbCx**; UART depends on **SerCx**; I3C and GPIO are **standalone** (no bus framework dependency)
> - GPIO is **ACPI-enumerated** (INTC105F), all others are **PCI-enumerated** (VEN_8086)
> - UART uses **Analytic** ETW channel; all others use **Debug + Performance** channels
> - UART and GPIO use **LoadOrderGroup: Extended Base**; I2C/I3C/SPI use **LoadOrderGroup: Base**
> - No explicit IdlePowerState/IdleTimeout registry keys — PM handled internally by driver
> - Min OS: Windows 10 RS5 (build 17763) — `NTamd64.10.0...17763`

---

## Driver Matching Behavior

### Linux

```c
/* i2c-designware-pcidrv.c */
static const struct pci_device_id i2c_designware_pci_ids[] = {
    /* NVL entries */
    { PCI_VDEVICE(INTEL, 0xD215), /* NVL I2C0 */ },
    { PCI_VDEVICE(INTEL, 0xD216), /* NVL I2C1 */ },
    /* ... */
};

/* dw-i3c-master.c */
static const struct pci_device_id dw_i3c_pci_ids[] = {
    { PCI_VDEVICE(INTEL, 0xD37C), /* NVL I3C ctrl#1 */ },
    { PCI_VDEVICE(INTEL, 0xD36F), /* NVL I3C ctrl#2 */ },
};
```

- Linux uses `pci_device_id` table for static matching
- ACPI companion (`_HID`/`_CID`) used for child device enumeration
- `i2c_dw_pci_probe()` detects IP version from `IC_COMP_PARAM_1` register

### Windows (from PTL INF v30.100.2510.55)

```ini
;; iaLPSS2_I2C_PTL.inf — [Intel.NTamd64.10.0...17763]
%I2C0.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E478   ; I2C0
%I2C1.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E479   ; I2C1
%I2C2.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E47A   ; I2C2
%I2C3.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E47B   ; I2C3
%I2C4.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E450   ; I2C4
%I2C5.DeviceDesc% = I2C_Device, PCI\VEN_8086&DEV_E451   ; I2C5

;; iaLPSS2_I3C_PTL.inf
%I3C0.DeviceDesc% = I3C_Device, PCI\VEN_8086&DEV_E47C   ; I3C Ctrl#1
%I3C1.DeviceDesc% = I3C_Device, PCI\VEN_8086&DEV_E46F   ; I3C Ctrl#2

;; iaLPSS2_SPI_PTL.inf
%SPI0.DeviceDesc% = SPI_Device, PCI\VEN_8086&DEV_E427   ; SPI0
%SPI1.DeviceDesc% = SPI_Device, PCI\VEN_8086&DEV_E430   ; SPI1
%SPI2.DeviceDesc% = SPI_Device, PCI\VEN_8086&DEV_E446   ; SPI2

;; iaLPSS2_UART2_PTL.inf
%UART0.DeviceDesc% = UART_Device, PCI\VEN_8086&DEV_E425  ; UART0
%UART1.DeviceDesc% = UART_Device, PCI\VEN_8086&DEV_E426  ; UART1
%UART2.DeviceDesc% = UART_Device, PCI\VEN_8086&DEV_E452  ; UART2

;; iaLPSS2_GPIO2_PTL.inf — ACPI-enumerated (NOT PCI!)
%GPIO.DeviceDesc% = GPIO_Device, ACPI\INTC105F
```

- **Separate INF per protocol**: `iaLPSS2_I2C_PTL.inf`, `iaLPSS2_I3C_PTL.inf`, `iaLPSS2_SPI_PTL.inf`, `iaLPSS2_UART2_PTL.inf`, `iaLPSS2_GPIO2_PTL.inf`
- **Dependencies**: I2C/SPI → SpbCx; UART → SerCx; I3C/GPIO → standalone (no bus framework)
- All drivers enable **WdfDirectedPowerTransitionEnable=1** (DFx / Directed Power Management)
- All drivers enable **DmaRemappingCompatible=1** (VT-d ready)
- `EvtDevicePrepareHardware` maps BAR0 and initializes MMIO access
- ACPI `_DSM` used for platform-specific configuration
- Min OS: Windows 10 RS5 (build 17763)

---

## Register Access Patterns

### Linux (regmap)

```c
/* i2c-designware-core.h */
struct dw_i2c_dev {
    struct regmap *map;       /* regmap for MMIO access */
    void __iomem *base;       /* BAR0 mapped base */
    /* ... */
};

/* Register read/write via regmap */
regmap_read(dev->map, DW_IC_CON, &val);
regmap_write(dev->map, DW_IC_CON, val);

/* Or direct MMIO */
readl(dev->base + DW_IC_CON);
writel(val, dev->base + DW_IC_CON);
```

### Windows (MMIO struct overlay)

```c
/* Typical Windows SerialIO pattern */
typedef struct _I2C_REGS {
    ULONG IC_CON;           /* 0x00 */
    ULONG IC_TAR;           /* 0x04 */
    ULONG IC_SAR;           /* 0x08 */
    /* ... mapped from BAR0 */
} I2C_REGS, *PI2C_REGS;

/* Access via mapped pointer */
ULONG ic_con = READ_REGISTER_ULONG(&pRegs->IC_CON);
WRITE_REGISTER_ULONG(&pRegs->IC_CON, newVal);
```

---

## Power Management Hooks

### Linux PM Runtime

```c
/* i2c-designware-pcidrv.c */
static int i2c_dw_pci_runtime_suspend(struct device *dev) {
    /* Save register state */
    i2c_dw_disable(i_dev);
    /* Controller enters D3 via PCI PM */
    return 0;
}

static int i2c_dw_pci_runtime_resume(struct device *dev) {
    /* Restore register state */
    i2c_dw_init_master(i_dev);
    return 0;
}

static const struct dev_pm_ops i2c_dw_pm_ops = {
    SET_RUNTIME_PM_OPS(
        i2c_dw_pci_runtime_suspend,
        i2c_dw_pci_runtime_resume,
        NULL
    )
};
```

### Windows D-State Transitions

```
D0 (Active) → EvtDeviceD0Exit() → Save MMIO regs → PMCSR.PS=D3 → D3
D3 (Off)    → EvtDeviceD0Entry() → PMCSR.PS=D0 → Restore MMIO regs → D0

Key difference: Windows explicitly manages PMCSR writes
Linux relies on PCI core to handle PMCSR via pci_set_power_state()
```

---

## Interrupt Handling

### Linux I2C Interrupt Handler

```c
/* i2c-designware-master.c */
static irqreturn_t i2c_dw_isr(int irq, void *dev_id) {
    u32 stat = i2c_dw_read_clear_intrbits(dev);
    
    if (stat & DW_IC_INTR_TX_ABRT) {
        dev->cmd_err |= DW_IC_ERR_TX_ABRT;
        dev->abort_source = readl(dev->base + DW_IC_TX_ABRT_SOURCE);
        /* Abort handling — decode 16 source bits */
    }
    if (stat & DW_IC_INTR_RX_FULL) {
        i2c_dw_read(dev);  /* Read from RX FIFO */
    }
    if (stat & DW_IC_INTR_TX_EMPTY) {
        i2c_dw_xfer_msg(dev);  /* Fill TX FIFO */
    }
    return IRQ_HANDLED;
}
```

### Linux I3C Interrupt Handler

```c
/* dw-i3c-master.c */
static irqreturn_t dw_i3c_master_irq_handler(int irq, void *dev_id) {
    /* Read HCI interrupt status */
    u32 status = readl(master->regs + INTR_STATUS);
    
    if (status & INTR_TRANSFER_ERR) {
        /* Read RESPONSE_QUEUE_PORT for error details */
        /* Check for NACK, abort, timeout */
    }
    if (status & INTR_IBI_THLD) {
        /* IBI received — process in-band interrupt */
        dw_i3c_master_ibi_work(master);
    }
    return IRQ_HANDLED;
}
```

---

## I2C Error Recovery (TX Abort)

### Linux: `i2c_dw_handle_tx_abort()`

```c
/* Decode IC_TX_ABRT_SOURCE register (0x80) */
static int i2c_dw_handle_tx_abort(struct dw_i2c_dev *dev) {
    unsigned long abort_source = dev->abort_source;
    
    if (abort_source & DW_IC_TX_ABRT_7B_ADDR_NOACK)
        return -ENODEV;     /* 7-bit address NACK — no device */
    if (abort_source & DW_IC_TX_ABRT_10ADDR1_NOACK)
        return -ENODEV;     /* 10-bit address NACK (first byte) */
    if (abort_source & DW_IC_TX_ABRT_TXDATA_NOACK)
        return -EIO;        /* Data NACK — device rejected data */
    if (abort_source & DW_IC_TX_ABRT_ARB_LOST)
        return -EAGAIN;     /* Arbitration lost — retry */
    
    return -EIO;  /* Generic error */
}
```

### Windows: Error Recovery

- Windows SerialIO driver handles TX abort via `SpbRequestComplete()` with `STATUS_DEVICE_NOT_CONNECTED` or `STATUS_IO_TIMEOUT`
- Recovery typically involves: disable controller → flush FIFOs → re-enable
- Key difference: Windows retries are managed by SpbCx framework, Linux retries by i2c-core `adap->retries`

---

## I3C Dynamic Address Assignment (DAA)

### Linux: ENTDAA Flow

```c
/* dw-i3c-master.c — DAA via ENTDAA CCC */
static int dw_i3c_master_daa(struct i3c_master_controller *m) {
    /* 1. Send ENTDAA broadcast (CCC 0x07) */
    /* 2. Read PID (48-bit) + BCR (8-bit) + DCR (8-bit) from target */
    /* 3. Assign dynamic address */
    /* 4. Repeat for all targets on bus */
}
```

### Key Validation Points (Driver vs Silicon)

| Aspect | Driver Behavior | Silicon/HAS Behavior | Validation Check |
|--------|----------------|---------------------|------------------|
| ENTDAA response | Driver reads PID/BCR/DCR | HCI auto-captures | Verify DAT (Device Address Table) updated |
| IBI ACK/NACK | Driver configures IBI_SIR_REQ_REJECT | HC_CONTROL.IBI_ENABLE | Check both driver config and HCI register |
| DAA retry | i3c-core retry count | HC auto-retry | Verify consistent behavior |
| Hot-Join | Driver HJ handler registered | INTR_STATUS.HJ_THLD | Test with runtime device attachment |

---

## Linux vs Windows Key Behavioral Differences

| Aspect | Linux | Windows | Impact on Validation |
|--------|-------|---------|---------------------|
| **D3 transition** | PCI core handles PMCSR | Driver explicitly writes PMCSR | May see different D3 timing |
| **Register save/restore** | Selective (only modified regs) | Full context save/restore | Check restore completeness after D3 exit |
| **I2C retry count** | `adap->retries` (default 0) | SpbCx retry policy | Linux may fail faster on transient NACKs |
| **I3C IBI handling** | Workqueue (`dw_i3c_master_ibi_work`) | DPC (Deferred Procedure Call) | Different latency characteristics |
| **UART DMA** | DW-DMA driver integration | iDMA driver | Different DMA channel assignment |
| **SPI chip select** | `spi_cs_activate/deactivate` | Driver CS# management | CS# timing may differ |
| **Clock gating** | `pm_runtime_idle` triggers | WDF idle callback | Different idle timeout defaults |
| **ACPI enumeration** | `_HID`/`_CID` on i2c bus scan | INF Hardware ID matching | Different discovery order |
| **Error logging** | `dev_err()` → dmesg/journald | WPP/ETW tracing | Different log formats for triage |
| **Bus speed config** | Device tree / ACPI `_DSD` | INF/Registry override | Speed may differ across OS |

---

## BIOS Programming Requirements

| BIOS Knob | Impact | Driver Dependency |
|-----------|--------|-------------------|
| LPSS I2C Enable | I2C PCI device visible | Both Linux and Windows need PCI device |
| LPSS I3C Enable | I3C PCI device visible | Both drivers check PCI probe |
| LPSS UART Enable | UART PCI device visible | Both drivers check PCI probe |
| LPSS SPI Enable | SPI PCI device visible | Both drivers check PCI probe |
| LPSS D3 Enable | D3 transitions allowed | PM runtime (Linux) / WDF power policy (Windows) |
| LPSS Pad Mode | Native function routing | Both drivers need correct PMode for I/O |
| LPSS DMA Mode | DMA vs PIO selection | Driver initialization path differs |

---

## Tracing & Debug Infrastructure

### Linux

```bash
# Enable i2c-designware trace events
echo 1 > /sys/kernel/tracing/events/i2c/enable

# Enable I3C trace events
echo 1 > /sys/kernel/tracing/events/i3c/enable

# dmesg for driver probe/errors
dmesg | grep -E "i2c_designware|dw-i3c|spi-dw|8250_lpss"

# Check driver binding
ls -la /sys/bus/pci/drivers/i2c_designware/
ls -la /sys/bus/pci/drivers/dw-i3c-master/
ls -la /sys/bus/pci/drivers/spi-dw-pci/
```

### Windows (ETW Tracing — Real PTL GUIDs from INF)

> **Source:** Extracted from `iaLPSS2_*_PTL.inf` v30.100.2510.55

| Driver | ETW Provider GUID | ETW Provider Name | Channels |
|--------|------------------|-------------------|----------|
| I2C | `{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}` | Intel-iaLPSS2-I2C | Debug, Performance |
| I3C | `{46BA0297-8886-4B8B-97C0-02C51A4829C4}` | Intel-iaLPSS2-I3C | Debug, Performance |
| SPI | `{6E112845-A8C4-4143-A631-256E8A3E7691}` | Intel-iaLPSS2-SPI | Debug, Performance |
| UART | `{B87CAA6F-37A7-4F09-8DC4-D15572C5904E}` | Intel-iaLPSS2-UART2 | **Analytic only** |
| GPIO | `{63848cff-3ec7-4ddf-8072-5f95e8c8eb98}` | Intel-iaLPSS2-GPIO2 | Debug, Performance |

```powershell
# Enable I2C ETW tracing
logman create trace LPSS_I2C -p "{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}" 0xFFFFFFFF 0xFF -o lpss_i2c.etl
logman start LPSS_I2C
# ... reproduce issue ...
logman stop LPSS_I2C
tracefmt lpss_i2c.etl -o lpss_i2c.txt

# Enable I3C ETW tracing
logman create trace LPSS_I3C -p "{46BA0297-8886-4B8B-97C0-02C51A4829C4}" 0xFFFFFFFF 0xFF -o lpss_i3c.etl

# Enable ALL LPSS drivers simultaneously
logman create trace LPSS_ALL -p "{C2F86198-03CA-4771-8D4C-CE6E15CBCA56}" 0xFFFFFFFF 0xFF -p "{46BA0297-8886-4B8B-97C0-02C51A4829C4}" 0xFFFFFFFF 0xFF -p "{6E112845-A8C4-4143-A631-256E8A3E7691}" 0xFFFFFFFF 0xFF -p "{B87CAA6F-37A7-4F09-8DC4-D15572C5904E}" 0xFFFFFFFF 0xFF -o lpss_all.etl

# Check device status (use real PTL Device ID)
pnputil /enum-devices /connected /class "{4d36e97d-e325-11ce-bfc1-08002be10318}" | Select-String "I2C|I3C|SPI|UART"
```

> **NOTE:** UART uses **Analytic** channel (not Debug/Performance). This means UART traces require explicit channel enable and may have different buffering behavior.

---

## Key Validation Points for FV

1. **PCI Matching:** Verify all LPSS Device IDs in Linux pci_device_id table match HAS
2. **BAR Mapping:** Verify BAR0 size matches HAS (4K for I2C/SPI/UART, 8K for I3C controller)
3. **Register Restore:** After D3→D0, verify all functional registers restored (IC_CON, IC_TAR, IC_SS/FS/HS_SCL_HCNT/LCNT for I2C)
4. **Interrupt Delivery:** MSI/MSI-X correctly routed after D3 exit
5. **DMA Channel:** iDMA channels correctly assigned per HAS (I2C0-3 DMA, I2C4-5 PIO)
6. **Error Path:** TX abort → correct errno → i2c-core retry → application error
7. **PM Runtime:** `autosuspend_delay_ms` setting affects D3 entry latency
8. **ACPI Companion:** `_HID`/`_CID` for child devices match expected values

---

## See Also

- `fv-lpss/config-checkout` — PCI enumeration, BDF/DID validation
- `fv-lpss/power-state` — D3 transitions, clock gating, CGPG
- `fv-lpss/debug` — Triage flows, failure signatures
- `fv-lpss/failure-analysis` — NGA log parsing, sighting correlation
- `docs/i2c/DW_apb_i2c_validation_reference.md` — I2C IP register reference
- `docs/i3c/DWC_mipi_i3c_validation_reference.md` — I3C HCI register reference
