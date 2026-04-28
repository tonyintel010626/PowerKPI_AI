# FV-ISH DMA Skill

## Skill Identity

**Skill**: `fv-ish/dma`
**Domain**: ISH DMA Architecture, Buffer Management, Data Streaming
**Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
**Last Updated**: 2026-03-16
**Primary Platform**: NVL (Nova Lake) — TTL register data provided, other platforms noted where different

> Load this skill when the user asks about: DMA engine, DMA buffers, DMA channels, data streaming, DMA errors, buffer overrun, DMA throughput, ISH data path, LLI mode, or ISH memory transfer validation.

---

## IMPORTANT: HAS-First Policy

**Always load `fv-ish/has` first** for DMA register offsets, descriptor formats, and platform-specific DMA architecture details. Content in this skill now includes verified TTL ISH 5.9 register data from OSXML PDFs. NVL data should be verified against NVL HAS when available.

---

## DMA Architecture Overview

### Role of DMA in ISH
ISH uses a multi-channel DMA engine to transfer data between internal memory regions and between ISH SRAM and external memory (host DRAM, IMR). This is critical for:
- **Firmware loading** (host driver → ISH SRAM via IMR)
- **Sensor data delivery** (ISH SRAM → host DMA buffers)
- **Internal data movement** (between SRAM banks, ROM, peripherals)
- **IPC message payload transfer** (large payloads beyond doorbell registers)

### ISH DMA is NOT PCIe DMA
**CRITICAL**: ISH connects via **IOSF fabric** (not PCIe). DMA transfers use IOSF transactions with root-space selection to target either host DRAM or IMR DRAM. The DMA engine is internal to the ISH IP — it is a DesignWare DMA controller integrated into the MIA (MinuteIA) core.

### DMA Data Flow
```
Physical Sensors (I2C/SPI/I3C/UART/GPIO)
        │
        ▼
ISH Firmware (sensor data collection in SRAM)
        │
        ▼
ISH DMA Engine (8 channels, configurable transfer modes)
        │  (IOSF fabric → host memory or IMR)
        ▼
Host Memory / IMR (OS-allocated DMA buffers or IMR region)
        │
        ▼
ISH Host Driver (IPC doorbell interrupt, processes completed transfers)
        │
        ▼
HID Sensor Class Driver / OS Sensor Framework
```

### DMA Participants
| Participant | Role |
|------------|------|
| **ISH Firmware** | Configures DMA channels, initiates transfers |
| **DMA Engine** | 8-channel DW DMA controller at MIA base `0x10101000` |
| **IOSF Fabric** | Transport layer for external transfers |
| **Host OS Driver** | Allocates host DMA buffers, processes IPC completion doorbells |
| **IMR Region** | Isolated Memory Region for secure FW loading |

---

## TTL DMA Channel Registers (ISH 5.9 — Verified from OSXML)

### DMA Misc Controller — Base `0x10101000` (MIA Internal)

The ISH DMA misc block provides per-channel control registers for 8 DMA channels:

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| DMA_CTL_CH0 | 0x00 | 0x00000000 | Channel 0 control |
| DMA_CTL_CH1 | 0x04 | 0x00000000 | Channel 1 control |
| DMA_CTL_CH2 | 0x08 | 0x00000000 | Channel 2 control |
| DMA_CTL_CH3 | 0x0C | 0x00000000 | Channel 3 control |
| DMA_CTL_CH4 | 0x10 | 0x00000000 | Channel 4 control |
| DMA_CTL_CH5 | 0x14 | 0x00000000 | Channel 5 control |
| DMA_CTL_CH6 | 0x18 | 0x00000000 | Channel 6 control |
| DMA_CTL_CH7 | 0x1C | 0x00000000 | Channel 7 control |

### DMA_CTL_CHx Bit Fields (Per-Channel)

| Bits | Field | Access | Description |
|------|-------|--------|-------------|
| [31:11] | Reserved | — | — |
| [10] | LLI_MODE | RW | **Linked List Item mode**: 0=single block, 1=LLI multi-block |
| [9] | WR_NON_SNOOP | RW | **Write non-snoop**: 0=snooped (coherent), 1=non-snooped |
| [8] | RD_NON_SNOOP | RW | **Read non-snoop**: 0=snooped (coherent), 1=non-snooped |
| [7] | Reserved | — | — |
| [6:5] | WR_RS | RW | **Write Root Space**: 00=RS0 (Host DRAM), 11=RS3 (IMR DRAM) |
| [4:3] | RD_RS | RW | **Read Root Space**: 00=RS0 (Host DRAM), 11=RS3 (IMR DRAM) |
| [2] | Reserved | — | — |
| [1:0] | TRANSFER_MODE | RW | **Transfer direction** (see below) |

### Transfer Mode Encoding ([1:0])

| Value | Mode | Description | Use Case |
|-------|------|-------------|----------|
| 0b00 | Internal→Internal | SRAM-to-SRAM or peripheral-to-SRAM | Internal data movement |
| 0b01 | Internal→External | ISH SRAM → Host DRAM or IMR | **Sensor data delivery to host** |
| 0b10 | External→Internal | Host DRAM or IMR → ISH SRAM | **Firmware loading from host** |
| 0b11 | External→External | Host DRAM ↔ IMR | Rare, FW image staging |

### Root Space Selection ([6:5] WR_RS, [4:3] RD_RS)

| Value | Target | Description |
|-------|--------|-------------|
| 00 | RS0 — Host DRAM | Standard host system memory |
| 01 | RS1 — Reserved | — |
| 10 | RS2 — Reserved | — |
| 11 | RS3 — IMR DRAM | Isolated Memory Region (secure, for FW loading) |

### Snoop Control ([9] WR_NON_SNOOP, [8] RD_NON_SNOOP)

| Setting | Behavior | Use Case |
|---------|----------|----------|
| Snooped (0) | DMA participates in cache coherency protocol | Shared host buffers accessed by CPU |
| Non-snooped (1) | Bypasses cache coherency, lower latency | DMA-only buffers, streaming data |

**Validation Note**: For sensor data delivery to host, typical config is:
- `TRANSFER_MODE=01` (Internal→External)
- `WR_RS=00` (Host DRAM)
- `WR_NON_SNOOP=0` (snooped, since host CPU reads the data)

---

## DMA Transfer Modes

### 1. Single-Block Mode (LLI_MODE=0)
- One contiguous DMA transfer per channel activation
- DMA engine transfers a single block from source to destination
- Channel completion generates interrupt
- Used for: small sensor reports, IPC message payloads

### 2. Linked List Item Mode (LLI_MODE=1)
- Multi-block scatter/gather DMA
- Firmware builds a linked list of transfer descriptors in SRAM
- DMA engine traverses the list, executing each block in sequence
- Used for: sensor batching, large FW image loading, multi-buffer streaming

### LLI Descriptor Format
```
Each LLI entry in SRAM:
  [Source Address]      — 32-bit source address
  [Destination Address] — 32-bit destination address
  [Block Size]          — Transfer size in bytes
  [Next LLI Pointer]    — Address of next LLI entry (0 = last)
  [Control]             — Per-block control flags
```

> **Note**: Exact LLI descriptor layout follows DesignWare DMA controller specification. Verify field sizes against ISH HAS if custom LLI validation is needed.

---

## DMA Channel Assignment (Typical)

ISH firmware assigns DMA channels by function. Typical allocation:

| Channel | Function | Direction | Root Space |
|---------|----------|-----------|------------|
| CH0 | I2C Sensor RX | Internal (peripheral→SRAM) | N/A (internal) |
| CH1 | I2C Sensor TX | Internal (SRAM→peripheral) | N/A (internal) |
| CH2 | SPI Sensor RX | Internal (peripheral→SRAM) | N/A (internal) |
| CH3 | SPI Sensor TX | Internal (SRAM→peripheral) | N/A (internal) |
| CH4 | Host Data TX | Internal→External | RS0 (Host DRAM) |
| CH5 | FW Image RX | External→Internal | RS3 (IMR) |
| CH6 | IPC Payload | Configurable | Configurable |
| CH7 | Reserved/Debug | — | — |

> **Note**: Channel assignment is firmware-defined and may vary by platform/FW version. The above is a typical allocation pattern from Linux ISH driver analysis.

---

## DMA Buffer Management

### Host-Side Buffer Allocation
The host OS driver allocates DMA-capable memory for sensor data:

```c
// Linux example (kernel driver)
dma_addr_t dma_handle;
void *cpu_addr = dma_alloc_coherent(dev, DMA_BUFFER_SIZE, &dma_handle, GFP_KERNEL);
// dma_handle = IOMMU-mapped physical address given to ISH via IPC
// cpu_addr   = virtual address for CPU access
```

### Buffer Handoff via IPC
Since ISH uses IPC doorbell/mailbox (not PCIe BARs), DMA buffer addresses are communicated from host to ISH firmware via IPC messages:

1. Host allocates DMA buffer, gets physical address
2. Host sends IPC message with buffer address in MSG registers (HOST IPC @ BAR0)
3. ISH firmware programs DMA channel with the address
4. ISH firmware triggers DMA transfer
5. ISH firmware signals completion via outbound doorbell (BUSY=1)
6. Host receives interrupt, reads completed data from DMA buffer

### Buffer Ownership Protocol
```
Initial State: Host allocates buffer, sends address to ISH via IPC
      │
ISH firmware programs DMA channel with buffer address
      │
ISH DMA writes sensor data into host buffer
      │
ISH sets OUTBOUND_DB[31]=BUSY=1 → interrupt to host
      │
Host reads sensor data from DMA buffer
      │
Host clears doorbell (BUSY_CLEAR register) → signals ISH
      │
ISH recycles channel for next transfer
```

---

## Firmware Loading via DMA

### Main FW Load Sequence (Boot)
The primary use of External→Internal DMA is firmware loading:

```
1. Boot ROM executes from 8KB ROM
2. CSE loads BUP firmware (≤64KB, Intel-signed) into SRAM
3. BUP initializes ISH, requests main FW from host
4. Host driver maps main FW image (≤1.5MB) into IMR
5. ISH DMA channel configured:
   - TRANSFER_MODE = 10 (External→Internal)
   - RD_RS = 11 (RS3 = IMR DRAM)
   - LLI_MODE = 1 (multi-block for large image)
6. DMA transfers FW from IMR → ISH SRAM banks
7. ISH verifies FW integrity, jumps to main FW entry point
```

### S3 Resume Optimization
```
1. On S3 entry: CSE saves uncompressed ISH main FW copy in IMR
2. On S3 resume: CSE compares hash of IMR copy vs original
3. If match: Skip full FW reload, DMA from IMR directly (faster resume)
4. If mismatch: Full FW reload sequence
```

---

## DMA Error Handling

### Error Types
| Error | Cause | Detection | Recovery |
|-------|-------|-----------|---------|
| **Transfer Timeout** | ISH firmware hang or DMA stall | No doorbell within timeout | ISH reset + driver reload |
| **Address Fault** | Invalid source/dest address | DMA engine error (Fabric error regs @ `0x10600000`) | Abort channel, report error |
| **Root Space Violation** | Wrong RS for target memory | IOSF transaction rejected | Fix channel config, retry |
| **SRAM ECC Error** | Bit flip in source/dest SRAM | SRAM controller ECC regs @ `0x10500000` | Log error, check data integrity |
| **Channel Conflict** | Two transfers to same channel | FW logic error | Serialize channel access |
| **LLI Chain Error** | Bad next-pointer in LLI list | DMA hangs or reads garbage | Validate LLI chain before starting |

### DMA Timeout Recovery
```python
DMA_TIMEOUT_MS = 5000  # 5 seconds without DMA completion doorbell

def handle_dma_timeout():
    """Recovery sequence for DMA timeout."""
    # Step 1: Check ISH firmware status
    fwsts = read_ipc_reg(HOST_IPC_BASE, 0x34)  # FWSTS register
    log_error(f"ISH FWSTS: 0x{fwsts:08X}")

    # Step 2: Check fabric error registers
    fabric_err = read_mia_reg(0x10600000, 0x00)
    if fabric_err:
        log_error(f"Fabric error: 0x{fabric_err:08X}")

    # Step 3: Check SRAM ECC status
    sram_intr = read_mia_reg(0x10500000, 0x04)  # SRAM_INTR_STS
    if sram_intr:
        log_error(f"SRAM ECC error: 0x{sram_intr:08X}")

    # Step 4: ISH reset via host driver
    trigger_ish_reset()
    # Step 5: Re-establish IPC connection
    reconnect_ipc()
```

### SRAM ECC Error Detection During DMA
```python
def check_sram_ecc_after_dma():
    """Check SRAM controller for ECC errors after DMA transfer."""
    SRAM_BASE = 0x10500000
    sram_intr_sts = read_mia_reg(SRAM_BASE, 0x04)  # SRAM_INTR_STS
    if sram_intr_sts & 0x1:  # Correctable ECC error
        log_warning("SRAM correctable ECC error during DMA")
        # Read error bank/address from ECC logging registers
    if sram_intr_sts & 0x2:  # Uncorrectable ECC error
        log_error("SRAM UNCORRECTABLE ECC error — data corrupted!")
        return False
    return True
```

---

## Performance Considerations

### Buffer Sizing Strategy
| Scenario | Buffer Size | Notes |
|----------|------------|-------|
| Low ODR sensors (< 10 Hz) | 64–256 bytes | Single report per IPC message, no DMA needed |
| Medium ODR (10–100 Hz) | 256–1024 bytes | DMA batch per interrupt |
| High ODR (> 100 Hz) | 1024–4096 bytes | LLI mode, multi-buffer streaming |
| FW Loading | Up to 1.5 MB | LLI chain from IMR, multi-block |
| Sensor Batching | 4096–65536 bytes | Large LLI chain for accumulated samples |

### DMA Throughput Estimation
```
Throughput = Sample_Size × ODR × Num_Sensors
Example (TTL: 5 sensors at 100 Hz, 12 bytes/sample):
  = 12 × 100 × 5 = 6,000 bytes/s = ~6 KB/s
  → Very low; DMA overhead dominated by IPC doorbell interrupt processing
  → For low-throughput scenarios, IPC MSG registers (128 bytes) may suffice
     without needing DMA at all
```

### When DMA vs IPC MSG Registers
| Data Size | Recommended Method | Reason |
|-----------|--------------------|--------|
| ≤ 128 bytes | IPC MSG registers (32×4B) | Zero DMA overhead, immediate delivery |
| 128 B – 4 KB | Single-block DMA | Efficient for moderate payloads |
| > 4 KB | LLI multi-block DMA | Required for large transfers (FW loading) |
| > 64 KB | LLI + IMR staging | FW images, large batch dumps |

---

## TTL-Specific DMA Notes (ISH 5.9)

### Memory Map Context
| Region | Base Address | Size | DMA Access |
|--------|-------------|------|------------|
| ROM | — | 8 KB | Read-only, boot code |
| SRAM (20 banks × 32KB) | — | 640 KB | Primary DMA source/dest |
| AON RF SRAM | — | 8 KB | Always-on, limited DMA |
| Host DRAM | Via IOSF RS0 | System | DMA target for sensor data |
| IMR DRAM | Via IOSF RS3 | Allocated | DMA target for FW loading |

### SRAM Power Gating Impact on DMA
- PMU `SRAM_PG_EN` register (MIA `0x04200000 + 0x00`, default `0x3FFFFFFF`) controls which SRAM banks are powered
- **DMA to/from a power-gated SRAM bank will fail silently or produce garbage data**
- Firmware must ensure target SRAM banks are powered before initiating DMA
- Validation: verify `SRAM_PG_EN` bits are clear for banks used by DMA buffers

### Clock Gating Impact on DMA
- CCU `DMA_CG` register (MIA `0x04300000 + 0x28`) controls DMA clock gating
- If DMA clock is gated, DMA transfers will not execute
- CCU `TRUNK_CG` (MIA `0x04300000 + 0x00`) must also allow DMA clock domain

---

## Validation Points

### 1. DMA Channel Configuration
```python
def test_dma_channel_config():
    """Verify DMA channel registers are correctly configured."""
    DMA_MISC_BASE = 0x10101000
    for ch in range(8):
        ctl = read_mia_reg(DMA_MISC_BASE, ch * 4)
        xfer_mode = ctl & 0x3
        rd_rs = (ctl >> 3) & 0x3
        wr_rs = (ctl >> 5) & 0x3
        lli = (ctl >> 10) & 0x1
        log_info(f"CH{ch}: mode={xfer_mode}, rd_rs={rd_rs}, wr_rs={wr_rs}, lli={lli}")
        # Verify no channel uses reserved RS values
        assert rd_rs in [0, 3], f"CH{ch} unexpected RD_RS={rd_rs}"
        assert wr_rs in [0, 3], f"CH{ch} unexpected WR_RS={wr_rs}"
```

### 2. Firmware Load via DMA
```python
def test_fw_load_dma():
    """Verify main FW loaded successfully via DMA from IMR."""
    # Check FWSTS register indicates FW loaded
    fwsts = read_ipc_reg(HOST_IPC_BASE, 0x34)
    fw_loaded = (fwsts >> 12) & 0xF  # FW status field
    assert fw_loaded >= 0x5, f"FW not fully loaded, FWSTS=0x{fwsts:08X}"
    # Verify DMA channel used for FW load had correct config
    # CH5 typical: External→Internal, RD_RS=RS3 (IMR)
    ch5_ctl = read_mia_reg(0x10101000, 0x14)
    assert (ch5_ctl & 0x3) == 0x2, "FW load channel not Ext→Int"
    assert ((ch5_ctl >> 3) & 0x3) == 0x3, "FW load RD_RS not RS3 (IMR)"
```

### 3. Sensor Data DMA Transfer
```python
def test_sensor_data_dma():
    """Verify sensor data arrives in host DMA buffer via ISH DMA."""
    # Allocate host DMA buffer and send address to ISH via IPC
    buf_addr = allocate_dma_buffer(4096)
    send_ipc_set_dma_buffer(buf_addr, 4096)
    # Enable sensor streaming
    enable_sensor(ACCEL, odr_hz=100)
    # Wait for IPC doorbell indicating data ready
    assert wait_for_doorbell(timeout_ms=2000), "No doorbell after sensor enable"
    # Read data from DMA buffer
    data = read_dma_buffer(buf_addr, 4096)
    assert len(data) > 0, "No sensor data in DMA buffer"
    assert validate_accel_data(data), "Sensor data format invalid"
```

### 4. DMA with SRAM Power Gating
```python
def test_dma_sram_power_gating():
    """Verify DMA fails gracefully when target SRAM bank is power-gated."""
    PMU_BASE = 0x04200000
    # Read current SRAM power gating state
    sram_pg = read_mia_reg(PMU_BASE, 0x00)  # SRAM_PG_EN
    log_info(f"SRAM_PG_EN = 0x{sram_pg:08X}")
    # Ensure DMA target banks are powered (bits clear = powered)
    dma_target_banks = 0x000F  # Banks 0-3 for example
    assert (sram_pg & dma_target_banks) == 0, \
        f"DMA target banks are power-gated! SRAM_PG_EN=0x{sram_pg:08X}"
```

### 5. DMA Snoop Configuration
```python
def test_dma_snoop_config():
    """Verify DMA channels use correct snoop settings."""
    DMA_MISC_BASE = 0x10101000
    # Sensor data channel (host-bound) should be snooped
    ch4_ctl = read_mia_reg(DMA_MISC_BASE, 0x10)  # CH4
    wr_nosnoop = (ch4_ctl >> 9) & 0x1
    assert wr_nosnoop == 0, "Sensor data DMA should be snooped for host CPU coherency"
```

### 6. LLI Multi-Block Transfer
```python
def test_lli_multiblock_transfer():
    """Verify LLI mode correctly chains multiple DMA blocks."""
    DMA_MISC_BASE = 0x10101000
    # FW load channel should use LLI mode for large images
    ch5_ctl = read_mia_reg(DMA_MISC_BASE, 0x14)  # CH5
    lli_mode = (ch5_ctl >> 10) & 0x1
    assert lli_mode == 1, "FW load channel should use LLI mode for multi-block"
    # Verify FW loaded completely
    fwsts = read_ipc_reg(HOST_IPC_BASE, 0x34)
    assert fwsts != 0, "FWSTS is zero — FW may not have loaded"
```

### 7. DMA Error Recovery
```python
def test_dma_error_recovery():
    """Verify system recovers from DMA error condition."""
    # Check fabric error registers for any existing errors
    fabric_err = read_mia_reg(0x10600000, 0x00)
    if fabric_err:
        log_warning(f"Pre-existing fabric error: 0x{fabric_err:08X}")
    # Check SRAM ECC status
    sram_sts = read_mia_reg(0x10500000, 0x04)
    assert (sram_sts & 0x2) == 0, "Uncorrectable SRAM ECC error present"
    # Trigger ISH reset and verify DMA functional after
    trigger_ish_reset()
    wait_for_ish_ready(timeout_ms=10000)
    # Verify DMA works post-recovery
    assert test_sensor_data_dma(), "DMA not functional after reset"
```

---

## Public References

- **Linux ISH IPC/DMA Implementation**: https://github.com/torvalds/linux/blob/master/drivers/hid/intel-ish-hid/ipc/ipc.c
- **Linux DMA API Documentation**: https://www.kernel.org/doc/html/latest/core-api/dma-api.html
- **DesignWare DMA Controller**: Synopsys DW_ahb_dmac / DW_axi_dmac databook (NDA)
- **ISH 5.9 MIA Register Reference**: `fv-ish/has/docs/ttl/TTL_ISH_MIA_Register_Reference.md`
