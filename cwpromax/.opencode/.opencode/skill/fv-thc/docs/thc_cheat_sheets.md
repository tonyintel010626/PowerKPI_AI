# THC FV Quick-Reference Cheat Sheets

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

> Concise reference cards for common THC validation tasks.
> Source: THC IP HAS v4.x + FV experience + Driver Source Code Audit + SwAS v1.0 | Last updated: 2026-03-06

---

## Cheat Sheet 1: THC Platform Bring-Up

### Pre-Requisites Checklist
- [ ] BIOS has THC enabled (check BIOS setup menu or soft straps)
- [ ] Correct PORT_TYPE set (00=SPI, 01=I2C)
- [ ] Touch device physically connected to correct port
- [ ] GPIO interrupt line connected and configured
- [ ] Device power rail enabled (GPIO reset deasserted = 1)

### Step-by-Step Bring-Up
```
1. Verify PCI Enumeration
   - Check THC0: `lspci | grep "Touch"` or PythonSV namednode read
   - Check THC1: THC0 MUST be enabled first (THC1 = Function 1)
   - NVL THC1 BDF: Bus=0 Dev=8 Fun=0 (NOT Dev=16 Fun=1!)

2. Verify BAR0 Mapped
   - BAR0 = 32KB MMIO range
   - Read THC_M_PRT_CONTROL to confirm access

3. Check Port Type
   - Read THC_M_PRT_CONTROL.PORT_TYPE
   - 00 = SPI mode, 01 = I2C mode

4. For SPI: Configure SPI_CFG
   - Base clock = 125 MHz (NOT 128 MHz!) [DOC-001]
   - Formula: SPI_freq = 125 MHz / divider (NOT /(divider×2)) [DOC-001]
   - Set IO mode (Single/Dual/Quad)
   - Set MPS (Max Payload Size)
   - Wait for SPI_IO_RDY

5. For I2C: Configure I2C Sub-IP
   - Set PORT_TYPE = 01
   - Program SPI_RD_MPS = 4096 (CRITICAL RTL bug workaround!)
   - Init Synopsys DW_apb_i2c (12-step sequence in registers skill)
   - IC_CON default: Linux=0x663 (NOT 0x665!) [DOC-005]
   - Default I2C target address = 0x0A (NOT 0x086!) [DOC-006]
   - Set I2C speed mode (100K/400K/1M)
   - I2C RXDMA2 is primary input path (RXDMA1 size=0, unused) [DOC-008]

6. Read Device Descriptor
   - SPI: PIO read of device descriptor (24 bytes)
   - I2C: I2C read of HID descriptor (30 bytes)
   - Verify wVendorID, wProductID, wVersionID
   - PIO timeout = 1 second [DOC-011]
   - I2C Host Reset / SET_POWER sent via TXDMA, NOT PIO [DOC-007]

7. Enable DMA (AFTER device reset, not before!) [DOC-012]
   - Configure RPRD base address
   - Set up PRD tables (all buffers 4KB aligned!)
   - Enable RXDMA interrupt
   - Touch device → verify input reports received

8. Verify Interrupts
   - Device GPIO → THC → MSI → Host
   - Check GBL_INT_EN (bit 31, LNL+)
   - Verify DMA read interrupt status
```

### Common Bring-Up Failures
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| THC1 not in lspci | THC0 disabled | Enable THC0 first |
| BAR0 reads all 0xFF | PCI not enumerated | Check BIOS, re-scan |
| No device descriptor | Wrong PORT_TYPE | Set correct SPI/I2C mode |
| I2C reads truncated | SPI_RD_MPS not set | Set SPI_RD_MPS = 4096 |
| DMA hang | PRD not 4KB aligned | Align ALL PRD buffers to 4KB |
| No interrupts | GPIO not configured | Check GPIO interrupt line |
| NVL THC1 wrong BDF | Using old Dev=16 Fun=1 | Use Dev=8 Fun=0 for NVL |

---

## Cheat Sheet 2: THC Debug Triage

### 4-Phase Systematic Debug
```
Phase 1: PCI Level
  ├── Is THC enumerated? (lspci / namednode)
  ├── Is BAR0 mapped? (read BAR0 register)
  ├── Is Device ID correct? (check platform skill)
  └── MSI configured? (check MSI cap)

Phase 2: MMIO Level
  ├── Can read/write registers? (THC_M_PRT_CONTROL)
  ├── PORT_TYPE correct? (00=SPI, 01=I2C)
  ├── Lock bits set? (BIOS_LOCK_EN, DRV_LOCK_EN)
  └── Interrupt enable? (GBL_INT_EN, per-DMA INT_EN)

Phase 3: Protocol Level
  ├── SPI: Clock frequency correct? (125 MHz / divider, SPI_LOW_FREQ_EN) [DOC-001]
  ├── SPI: IO mode correct? (Single/Dual/Quad)
  ├── I2C: Speed mode correct? (100K/400K/1M)
  ├── I2C: SPI_RD_MPS = 4096? (RTL bug workaround)
  ├── PIO working? (7-step SPI / I2C opcode; timeout=1s) [DOC-011]
  └── Device responding? (descriptor read succeeds)

Phase 4: DMA Level
  ├── PRD base address set? (RPRD base register)
  ├── PRD tables 4KB aligned? (all entries, including last!)
  ├── CB pointers advancing? (read/write pointer)
  ├── STALL_STS? (PRD exhausted)
  ├── DMA error register? (Stop-on-Error)
  └── Frame data valid? (check PRD buffer contents)
```

### Quick Register Checks
| What to Check | Register | Expected |
|---------------|----------|----------|
| Port type | THC_M_PRT_CONTROL.PORT_TYPE | 00=SPI, 01=I2C |
| SPI frequency | THC_M_PRT_SPI_CFG | Base=125MHz / divider [DOC-001] |
| MPS | THC_M_PRT_SPI_CFG.SPI_RD_MPS | 4096 for I2C! |
| DMA RX status | THC_M_PRT_DMA_READ_INT_STS | Check error bits |
| DMA TX status | THC_M_PRT_DMA_WRITE_INT_STS | Check error bits |
| DMA pause status | READ_DMA_INT_STS (NOT DMA_CNTRL!) | Poll this for pause [DOC-010] |
| Global INT | GBL_INT_EN (bit 31) | 1 = enabled |
| Device INT | GPIO interrupt status | Check active low |
| Power state | PCI PMCSR | D0/D3 |
| DEVINT_CFG_1 | MMIO offset 0x0EC | Interrupt config [DOC-004] |
| DEVINT_CFG_2 | MMIO offset 0x0F0 | Interrupt config [DOC-004] |

### Key Error Signatures
| Error | Register/Signal | Meaning |
|-------|----------------|---------|
| STALL_STS | DMA status | PRD table exhausted |
| TXN_ERR | Error interrupt | Transaction error on bus |
| Stop-on-Error | RXDMA status | DMA halted due to error |
| TX Abort | I2C TX status | Device NAK'd I2C write |
| No MSI | MSI cap status | Interrupt routing broken |

---

## Cheat Sheet 3: THC Power State Transitions

### Power State Map
```
                    ┌──────────┐
                    │ D0 Active│ ← Normal operation
                    └────┬─────┘
                         │ Idle timer expires
                    ┌────▼─────┐
                    │  D0i2    │ ← HW autonomous PG (state retained)
                    │ (<5uW)   │   Max timer: 1 second
                    └────┬─────┘
                         │ SW-initiated or Connected Standby
                    ┌────▼─────┐
                    │  D3-Hot  │ ← SW save/restore (28 registers)
                    └────┬─────┘
                         │ Platform sleep
                    ┌────▼─────┐
                    │  S0ix    │ ← System low-power
                    └──────────┘
```

### D3 Save/Restore Quick Reference
```
SAVE (before D3 entry):
  1. Quiesce interrupts (THC_DEVINT_QUIESCE_EN)
  2. Stop DMA engines
  3. Wait for DMA idle
  4. Save 28 registers (see power skill for full list)
  5. Set PCI PMCSR to D3

RESTORE (after D3 exit):
  1. Set PCI PMCSR to D0
  2. Wait for power stable
  3. Restore registers in ORDER:
     - Group 1 (1.00-1.07): IOSF SB SAI policy
     - Group 2 (2.01-2.17): PCI config + SB locks
     - Group 3 (3.00-3.146): MMIO common + port regs
     - Group 5 (5.1): GuC doorbell (LAST)
  4. Re-init DMA engines
  5. Re-enable interrupts
  6. Resume touch operation
```

### LTR Quick Reference
| State | LTR Value | When |
|-------|-----------|------|
| Active | ACTIVE_LTR_VAL/SCALE | During touch operation |
| Low Power | LP_LTR_VAL/SCALE | During D0i2 |
| Infinite | Max value | Cold boot, reset exit, Vnn removal |

**LTR Unconfigure** [DOC-002]: Clears 4 bits — LP_LTR_EN, ACTIVE_LTR_EN, LP_LTR_REQ, ACTIVE_LTR_REQ. There is NO toggle pattern and NO field named "THC_LTR_EN".

### Wake-on-Touch (WoT)
- Linux 6.17+ required (`intel-thc-wot.c` — dedicated WoT module)
- Device must support Armed/Sensing states
- GPIO interrupt must be configured as wake source via ACPI GpioInt()
- **Wake path**: Touch device → GPIO pad → vGPIO → GPIO IP → PMC → Platform wake (NOT through THC IP)
- **THC PCI caps**: WAKE=No, PME=No — THC cannot generate platform wake
- **PADCFGLOCK_VGPIO_THC0** must be `0x0` (unlocked) — BIOS dependency
- **Linux**: `thc_wot_config()` → `dev_pm_set_dedicated_wake_irq()` — zero THC register writes
- **Windows**: Extension INF required (`WoT_QuickSpiExtension.inf` / `WoT_QuickI2cExtension.inf`)
- See `fv-thc/wot` for full WoT architecture and debug playbook

---

## Cheat Sheet 4: PythonSV Register Access

### Basic Setup
```python
# In test script inheriting from ThcBase
pch_thc0 = getattr(self.target, "thc0")  # Port 0
pch_thc1 = getattr(self.target, "thc1")  # Port 1

# Read register
port_type = pch_thc0.port.mem.thc_m_prt_control.port_type.read()

# Write register
pch_thc0.port.mem.thc_m_prt_spi_cfg.spi_rd_mps.write(0x1000)  # 4KB
```

### Common Register Reads
```python
# Check port type
port_type = pch_thc.port.mem.thc_m_prt_control.port_type.read()
# 0 = SPI, 1 = I2C

# Check DMA status
rx_int_sts = pch_thc.port.mem.thc_m_prt_dma_read_int_sts.read()

# Check device interrupt
dev_int = pch_thc.port.mem.thc_m_prt_int_sts.read()

# Read performance counter
rx_frames = pch_thc.port.mem.thc_m_prt_rx_dma_frame_cnt.read()
```

### PIO Register Read (SPI, 7-step)
```python
# 1. Write target address to SW_SEQ_DATA0
pch_thc.port.mem.thc_m_prt_sw_seq_data0.write(target_addr)
# 2. Configure SW_SEQ_CNTRL (opcode, length, direction)
pch_thc.port.mem.thc_m_prt_sw_seq_cntrl.write(config)
# 3. Trigger PIO
pch_thc.port.mem.thc_m_prt_sw_seq_cntrl.go.write(1)
# 4. Poll SW_SEQ_STS for completion
while not pch_thc.port.mem.thc_m_prt_sw_seq_sts.done.read():
    pass
# 5. Read result from SW_SEQ_DATA[1:]
result = pch_thc.port.mem.thc_m_prt_sw_seq_data1.read()
```

### NGA Exit Codes
```python
PASS = 0
FAIL = 9
```

---

## Cheat Sheet 5: Platform Quick Lookup

### Device ID Lookup
| Platform | THC0 DID | THC1 DID | Protocol |
|----------|----------|----------|----------|
| MTL | Check platform skill | Check platform skill | HIDSPI |
| LNL | Check platform skill | Check platform skill | HIDSPI/HIDI2C |
| PTL | Check platform skill | Check platform skill | HIDSPI/HIDI2C |
| NVL | Check platform skill | Check platform skill | HIDSPI/HIDI2C |
| WCL | Check platform skill | Check platform skill | HIDSPI/HIDI2C |
| ARL | Check platform skill | Check platform skill | HIDSPI |

> **Always** check `fv-thc/platform` skill for exact Device IDs — they change per stepping!

### BDF Quick Reference
| Platform | THC0 BDF | THC1 BDF | Notes |
|----------|----------|----------|-------|
| Most | B:0 D:16 F:0 | B:0 D:16 F:1 | Standard |
| NVL THC1 | B:0 D:16 F:0 | **B:0 D:8 F:0** | **CHANGED!** |

### Key Differences by Generation
| Feature | Gen2 (ADP/MTL) | Gen4.0 (LNL) | Gen4.1 (PTL/WCL) | Gen4.2 (NVL) |
|---------|----------------|---------------|-------------------|--------------|
| HIDSPI | Yes | Yes | Yes | Yes |
| HIDI2C | No | Yes (SDV) | Yes | Yes |
| SWDMA | No | Yes | Yes | Yes |
| D3 Levels | 1 | 1 | 4 | 4 |
| Half-divider | No | Yes | Yes | Yes |
| SB Port ID | 8-bit | 8-bit | 16-bit | 16-bit |

---

## Cheat Sheet 6: BIOS Prerequisite Validation (BWG-Derived)

> Source: Chap69_BIOS_WG_THC.docx (Rev 0.5, TGP-era). ⚠️ Verify register defaults on PTL+/NVL.
> Reference: `fv-thc/docs/thc_bwg_extraction.md`

### BIOS Config Register Check Table
```
Register / Location              Expected Value     What It Means
─────────────────────────────────────────────────────────────────
THC_CFG_PCE.HAE (config 0xA2)   1                  HW autonomous PG enabled
THC_CFG_PCE.D3HE (config 0xA2)  0 or 1             D3-Hot PG (platform-dep)
THC_CFG_PCE.SE (config 0xA2)    1                  Sleep enable during PG
BIOS_LOCK_EN                     1 (sticky)         BIOS regs locked
PORT_SUPPORTED (per port)        1=connected port   Matches physical BOM
THC_CFG_UR_STS_CTL.FD            0 (enabled)        1 = function disabled
P39h:20h-3Ch (SAI policy)        Non-zero           SAI access control set
P39h:0h (THC_SB_PR_CDC_CFG)      0x0000CCC0         Normal (CCC3 if CG/FD)
P39h:4h (THC_SB_SD_CDC_CFG)      0x0000CCC0         Normal (CCC3 if CG/FD)
LTR (ACT_LTR_VAL/LP_LTR_VAL)    Non-default        BIOS programmed LTR
MMIO 0x1128 bit31                 1 if G5 panel      MSFT G5 panel support
GPIO IOSTANDBY                    Retain last val    Survives Vnn removal
```

### BIOS Port Configuration Decision Flow
```
Q: How many touch ports are connected?
│
├── 2 ports, 2 drivers (standard)
│   → SPI1 GPIO → THC0 port0, SPI2 GPIO → THC1 port0
│   → THC0 clears PORT_SUPPORTED for port1
│   → THC1 clears PORT_SUPPORTED for port1
│
├── 2 ports, 1 driver (single-driver / ZBB)
│   → SPI1 GPIO → THC0 port0, SPI2 GPIO → THC0 port1
│   → Function Disable THC1
│
├── 1 port only
│   → SPI1 GPIO → THC0 port0
│   → THC0 clears PORT_SUPPORTED port1
│   → Function Disable THC1
│
└── 0 ports (no touch)
    → SPI1 GPIO → legacy SPI Touch port
    → Function Disable THC0 AND THC1
```

### Function Disable Sequence (4-step, ordered)
```
1. Enable all clock gating controls (CDC regs → CCC3)
2. Set HAE bit in THC_CFG_PCE to 1
3. Set device into D3 state (PMCSR = D3)
4. Set THC_CFG_UR_STS_CTL.FD = 1
⚠️ No SW or device wake in this state. PSF returns UR for all cycles.
```

### BIOS Power Transition Checklist
```
S3/S4/S5 ENTRY:
  ☐ SW asserts DEVRST bit
  ☐ Complete D3 entry (PMCSR → D3)
  ☐ THEN initiate Sx entry
  ⚠️ DEVRST must be BEFORE D3 — not after!

S3 RESUME:
  ☐ BIOS re-runs FULL boot init flow (same as cold boot)
  ☐ All THC registers re-initialized from scratch
  ☐ No partial restore — complete re-init

RTD3 ENTRY:
  ☐ SW asserts DEVRST before D3 entry
  ☐ Same DEVRST-first sequencing as Sx entry

CONNECTED STANDBY:
  ☐ S0 active: D0 or D0i2 (HW autonomous)
  ☐ S0ix entry: DEVRST → D3 → S0ix
  ☐ Touch wake: ONLY in D0i2 (not D3!)
```

### Common BIOS Misconfigurations
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No D0i2 entry | HAE=0 in THC_CFG_PCE | Set HAE=1 |
| Driver gets UR on register access | SAI regs all-zero (P39h:20h–3Ch) | Program SAI policy |
| THC not power-gated in D3 | D3HE=0 in THC_CFG_PCE | Set D3HE=1 |
| Touch doesn't wake from sleep | Expecting wake from D3 | Touch wake only in D0i2 |
| Registers scrambled after S3 resume | Partial restore attempted | BIOS must do full re-init |
| Port 1 enumerated but no device | PORT_SUPPORTED=1 but nothing connected | Clear PORT_SUPPORTED |
| Function disable incomplete | Steps done out of order | Must be: CG → HAE → D3 → FD |
| GPIO values lost on Vnn removal | IOSTANDBY not configured | Set GPIO IOSTANDBY to retain |

---

## Cheat Sheet 7: SPI PIO Opcodes & Timing Quick Reference [DOC-003, DOC-011]

### SPI PIO Opcodes (Corrected)
| Operation | Opcode | Notes |
|-----------|--------|-------|
| Read | 0x4 | Device descriptor, report descriptor |
| Write | 0x6 | Output reports via PIO |
| Bulk Write | 0x8 | NOT 0x2 — was wrong in earlier docs |

### PIO Timing
| Parameter | Value | Source |
|-----------|-------|--------|
| PIO timeout | **1 second** (NOT 3s!) | Linux `THC_PIO_TIMEOUT_US` [DOC-011] |
| PIO poll interval | Implementation-dependent | Check driver source |

### SPI Clock Quick Reference [DOC-001]
| Parameter | Value |
|-----------|-------|
| Base clock | **125 MHz** (NOT 128 MHz!) |
| Formula | `SPI_freq = 125 MHz / divider` (NOT `/ (divider × 2)`) |
| Source | Linux `intel-thc-hw.h` THC_SPI_DEFAULT_CLOCK_HZ = 125000000 |

---

## Cheat Sheet 8: DMA Cross-Platform Quick Reference [DOC-009, DOC-010]

### DMA Pause Timeout (Cross-Platform)
| OS | Poll Interval | Total Timeout | Source |
|----|--------------|---------------|--------|
| Linux | 100 µs | 10 ms | `intel-thc-dma.c` |
| Windows | 10 µs | 1 s | `Dma.h` DEFAULT_QUIESCE_POLLING_* |

> ⚠️ DMA pause polls **READ_DMA_INT_STS** register (aka INT_STS), NOT DMA_CNTRL! [DOC-010]

### I2C RXDMA Channel Assignment [DOC-008]
| Channel | I2C Usage | Size |
|---------|-----------|------|
| RXDMA1 | **NOT used** | size=0 |
| RXDMA2 | **Primary input path** | Configured by driver |

> ⚠️ RXDMA1 is NOT used for I2C — RXDMA2 is the primary input path.

### I2C Command Transport [DOC-007]
| Command | Transport | Notes |
|---------|-----------|-------|
| Host Reset | **TXDMA** (`write_cmd_to_txdma`) | NOT PIO opcode 0x18! |
| SET_POWER | **TXDMA** (`write_cmd_to_txdma`) | NOT PIO opcode 0x18! |
| Output reports | TXDMA | ⚠️ No PM runtime handling [DOC-015] |

---

## Cheat Sheet 9: Driver Probe & Reset Quick Reference [DOC-012, DOC-013, DOC-014]

### QuickSPI Probe Sequence (14 steps, corrected order) [DOC-012]
```
 1. PCI probe / resource allocation
 2. Map BAR0 MMIO
 3. Read ACPI _DSM for device config
 4. Configure SPI parameters (clock, IO mode, MPS)
 5. ACPI _RST device reset [DOC-013]
 6. Wait for device ready (edge-triggered interrupt)
 7. PIO: Read device descriptor
 8. PIO: Read report descriptor
 9. DMA init (AFTER reset, not before!) ← KEY ORDERING
10. Configure PRD tables
11. Enable RXDMA interrupts
12. Register HID device
13. Enable touch reporting
14. Complete probe
```
> ⚠️ DMA init is step 9 — AFTER device reset (step 5). Earlier docs had DMA init BEFORE reset.

### QuickSPI Reset Flow (Corrected) [DOC-013]
| Aspect | Wrong (old) | Correct |
|--------|-------------|---------|
| Reset method | GPIO LOW/HIGH | **ACPI `_RST` method** |
| Interrupt type | Level-triggered | **Edge-triggered** |
| Source | — | Linux `pci-quickspi.c` quickspi_reset() |

### Windows Driver Versions [DOC-014]
| Driver | Version | Source |
|--------|---------|--------|
| Windows HIDSPI | **v4.0.0.9000** | `Ver.h` |
| Windows HIDI2C | **v3.0.0.9000** | `Ver.h` |

### Known Driver Bug [DOC-015]
- `output_report()` (QuickSPI) has **NO `pm_runtime_get/put`** calls
- Device could be in D3 when output report is sent → potential data loss
- Source: Linux `quickspi-hid.c` quickspi_hid_output_report()
- Status: Potential bug — not yet fixed upstream

---

## Cheat Sheet 10: I2C Sub-IP Quick Reference [DOC-005, DOC-006]

### IC_CON Default Values (Cross-Platform) [DOC-005]
| OS | IC_CON Value | Method |
|----|-------------|--------|
| Linux | **0x663** (NOT 0x665!) | Single register write |
| Windows | Varies | Builds field-by-field |

### Default I2C Target Address [DOC-006]
| Parameter | Value | Notes |
|-----------|-------|-------|
| Default target addr | **0x0A** | NOT 0x086! |
| Source | Linux `pci-quicki2c.c` DEFAULT_HIDI2C_TGT_ADDR |

### DEVINT_CFG Register Offsets [DOC-004]
| Register | MMIO Offset | Notes |
|----------|-------------|-------|
| DEVINT_CFG_1 | **0x0EC** | Interrupt configuration |
| DEVINT_CFG_2 | **0x0F0** | Interrupt configuration |

---

## SwAS-Derived Cheat Sheets (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0 and QuickI2C SwAS v1.0.

## Cheat Sheet 11: Quiesce Scenarios Quick Reference (SwAS)

### When to Quiesce
| Scenario | When | Protocol | SwAS Reference |
|----------|------|----------|---------------|
| Host-initiated reset | Before sending reset command | Both | QuickSPI P0574 |
| Buffer threshold | Free buffers drop to 8 (half of 16) | Windows only | QuickSPI P0627 |
| D0Exit before D3 | Before D3 transition | Both | QuickSPI P0578 |
| **NEVER in ISR/DPC** | — | Both | QuickSPI P0580 |

### Quiesce Flow (Windows ISR/DPC Pattern)
```
ISR (Interrupt Service Routine):
  1. Read RAW_INT_STS
  2. Mask via GBL_INT_EN = 0
  3. Queue DPC
  4. Return

DPC (Deferred Procedure Call):
  1. Process interrupt cause
  2. Handle data (DMA read, etc.)
  3. Unmask GBL_INT_EN = 1
  4. Return

⚠️ NEVER call quiesce() from within ISR or DPC!
⚠️ LNL RTL bug: RAW_INT_STS MSI blocked when QUIESCE_EN set (SWAS-002)
```

### Buffer Throttling (Windows)
```
Total PRD tables: 16
Throttle threshold: 8 free (50%)

  Touch data flowing → Free buffers decreasing
  ...
  Free buffers = 8 → QUIESCE (throttle)
  ...
  All buffers freed → UNQUIESCE (resume)
```

---

## Cheat Sheet 12: Reset Timeout Quick Reference (SwAS)

### Protocol-Specific Reset Timeouts
| Protocol | SwAS Timeout | Linux Kernel | Windows Driver |
|----------|-------------|--------------|----------------|
| SPI (QuickSPI) | **1 second** | 5 seconds | 1 second |
| I2C (QuickI2C) | **5 seconds** | 5 seconds | 5 seconds |

> ⚠️ Linux uses 5s for BOTH protocols (conservative). Windows follows SwAS exactly.

### Reset Flow Quick Reference
```
SPI Reset:
  1. Quiesce device interrupts
  2. Set edge-trigger (first time)
  3. ACPI _RST method
  4. Unquiesce
  5. Wait for RESET_RESPONSE (1s SwAS / 5s Linux)
  6. Validate: len == 0, type == RESET_RESPONSE
  7. Re-arm edge trigger (second time)
  8. Get device descriptor

I2C Reset:
  1. Send RESET via TXDMA to cmd_reg
  2. Wait for reset_ack (5s)
  3. If no ack: PIO read from input_reg
  4. Valid reset: length == 0x0000
  5. Device in ON state after reset
  ⚠️ No reset on WoT exit (both protocols)
```

---

## Cheat Sheet 13: ECO Registry Keys Quick Reference (SwAS)

### QuickSPI ECO Keys
| Registry Key | Type | Purpose | SwAS Ref |
|-------------|------|---------|----------|
| `IO_Mode_Override` | DWORD | Override SPI IO mode | P0790 |
| `SPI_Frequency_Override` | DWORD | Override SPI clock frequency | P0791 |
| `TxDMA_Override` | DWORD | Override TX DMA behavior | P0793 |

### QuickI2C ECO Keys
| Registry Key | Type | Default | Purpose | SwAS Ref |
|-------------|------|---------|---------|----------|
| `I2C_Max_Frame_Size_Enable` | DWORD | 0 | Enable max frame size cap | P0857 |
| `I2C_Max_Frame_Size` | DWORD | 128–255 | Max frame size value | P0858 |
| `I2C_Int_Delay_Enable` | DWORD | 0 | Enable interrupt delay | P0870 |
| `I2C_Int_Delay` | DWORD | 1ms PTL/WCL | Interrupt delay value | P0871 |
| `EnEdgeTriggeredINT` | DWORD | 0 | Edge-triggered INT mode | T7 |
| `TimeStampEnable` | DWORD | 0 | Enable DMA timestamps | T7 |
| `ResetRequiredByDriver` | DWORD | — | Driver controls reset | T7 |
| `ISRDPCProfilingEn` | DWORD | 0 | ISR/DPC profiling | T7 |
| `EnResetPollingWA` | DWORD | 0 | Reset polling WA | T7 |
| `EnableFWFlashWABOM36` | DWORD | 0 | BOM36 FW flash WA | T7 |
| `DoNotWaitForResetResponse` | DWORD | 0 | Skip reset wait | T7 |

---

## Cheat Sheet 14: ACPI Frequency & Packet Encoding (SwAS)

### SPI Frequency from ACPI DSM (QuickSPI SwAS P0900-P0912)
```
connection_speed bits [2:0]:
  011 = 40 MHz
  100 = 30 MHz
  101 = 24 MHz
  110 = 20 MHz
  111 = 17 MHz

LimitPacketSize encoding:
  Also in connection_speed DSM return value
  true → DEFAULT_MIN = 4 (64 bytes)
  false → platform-dependent MAX
```

### Platform Packet Size Limits (from kernel + SwAS)
| Platform | Max Packet Size | Min Packet Size |
|----------|----------------|-----------------|
| MTL / ARL | 128 (2KB) | 4 (64B) |
| LNL / PTL / WCL | 256 (4KB) | 4 (64B) |

---

## Cheat Sheet 15: WoT Quick Reference (SwAS + Kernel)

### WoT Architecture
```
Touch device → GPIO pad → vGPIO → GPIO IP → PMC → Platform wake
                                    ↑
                              NOT through THC IP!
                              THC PCI caps: WAKE=No, PME=No
```

### WoT Entry/Exit by Protocol and OS
| Step | SPI (Linux) | SPI (Windows) | I2C (Linux) | I2C (Windows) |
|------|------------|---------------|-------------|----------------|
| Entry | No SET_POWER | WaitWake IRP | Skip SET_POWER if wakeup | SET_POWER(SLEEP) |
| Wake path | vGPIO→PMC | vGPIO→PMC | vGPIO→PMC | vGPIO→PMC |
| Exit | No reset | No reset | SET_POWER(ON) if !wakeup | SET_POWER(ON) |
| THC regs | Zero writes | Zero writes | Save I2C subip | Save I2C subip |

### WoT Prerequisites
```
☐ PADCFGLOCK_VGPIO_THC0 = 0x0 (unlocked)
☐ ACPI GpioInt() configured as wake source
☐ Linux 6.17+ (intel-thc-wot.c module)
☐ Windows: Extension INF installed
    - SPI: WoT_QuickSpiExtension.inf
    - I2C: WoT_QuickI2cExtension.inf
☐ DO NOT use _PRW with GPIO on ACPI device (Windows crash!)
☐ _S0W returns 3 for wake-capable devices
☐ _PS0/_PS3/_DSW used instead of Power Resource
```
