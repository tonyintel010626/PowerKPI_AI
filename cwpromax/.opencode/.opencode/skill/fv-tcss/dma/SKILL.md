# TCSS DMA — DMA Engine and Data Path Management

## Overview

This sub-skill covers TCSS DMA engine architecture, data path management, tunneling performance, and DMA-related validation for Type-C Subsystem.

## DMA Architecture

### TCSS DMA Engine

The DMA engine handles high-throughput data transfers for tunneled protocols:

```
┌──────────────────────────────────────────┐
│         TCSS DMA Controller              │
│  ┌───────────────────────────────────┐   │
│  │   DMA Scheduler                   │   │
│  │   (Arbitration, QoS)              │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Transfer Engines                │   │
│  │   • USB3 DMA                      │   │
│  │   • PCIe DMA                      │   │
│  │   • DP DMA                        │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Memory Interface                │   │
│  │   (System memory access)          │   │
│  └───────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### DMA Components

| Component | Description |
|-----------|-------------|
| **DMA Scheduler** | Arbitrates between multiple DMA channels |
| **Transfer Engines** | Protocol-specific DMA engines (USB/PCIe/DP) |
| **Memory Interface** | Interface to system memory (via PCIe/fabric) |
| **Descriptor Management** | DMA descriptor fetching and processing |
| **Interrupt Controller** | DMA completion interrupts |

## DMA Descriptor Format

> **CRITICAL:** Always verify descriptor format against platform HAS.

### Descriptor Structure

DMA descriptors define transfer parameters:

| Field | Description |
|-------|-------------|
| **Source Address** | Physical address of source buffer |
| **Destination Address** | Physical address of destination buffer |
| **Transfer Size** | Number of bytes to transfer |
| **Control Flags** | DMA control bits (interrupt, chaining, etc.) |
| **Next Descriptor** | Pointer to next descriptor (for chaining) |

### Descriptor Chaining

Multiple descriptors can be chained for large transfers:

```
Descriptor 1 → Descriptor 2 → Descriptor 3 → ... → NULL
```

**Benefits:**
- Support transfers larger than single descriptor limit
- Pre-program multiple transfers for efficiency
- Reduce CPU intervention during data transfer

## Data Path Management

### USB3 Tunneling Data Path

```
USB Device → USB4/TBT Tunnel → DMA Engine → System Memory
```

**Flow:**
1. USB device sends data over tunneled connection
2. USB4/TBT router receives packets
3. DMA engine fetches descriptor from memory
4. DMA transfers data to system memory buffer
5. DMA interrupt signals completion

### PCIe Tunneling Data Path

```
PCIe Device → USB4/TBT Tunnel → DMA Engine → System Memory
```

**Flow:**
1. PCIe TLP (Transaction Layer Packet) over tunnel
2. PCIe adapter reconstructs TLP
3. DMA engine handles memory read/write requests
4. Data transferred to/from system memory

### DP Tunneling Data Path

```
GPU Framebuffer → DMA Engine → USB4/TBT Tunnel → Display
```

**Flow:**
1. GPU writes framebuffer to system memory
2. DMA engine reads framebuffer
3. DP adapter encodes video stream
4. Stream tunneled over USB4/TBT to display

## DMA Performance

### DMA Throughput

| Transfer Type | Expected Throughput |
|---------------|---------------------|
| USB3 Bulk (SuperSpeed) | ~3.5 Gbps (~440 MB/s) |
| PCIe 3.0 x4 | ~28 Gbps (~3.5 GB/s) |
| DP HBR3 (4-lane) | ~32 Gbps (~4 GB/s) |

### Latency

| Metric | Typical Value |
|--------|---------------|
| Descriptor fetch | <1 µs |
| DMA setup | <10 µs |
| First data transfer | <100 µs |
| Interrupt latency | <50 µs |

## DMA Configuration

### DMA Registers

> **CRITICAL:** Always verify register offsets against platform HAS.

| Register | Offset | Description |
|----------|--------|-------------|
| DMA_CONTROL | Query HAS | DMA engine enable/disable |
| DMA_STATUS | Query HAS | DMA transfer status |
| DMA_DESC_BASE | Query HAS | Descriptor base address |
| DMA_DESC_COUNT | Query HAS | Number of descriptors |
| DMA_INT_STATUS | Query HAS | Interrupt status |
| DMA_INT_ENABLE | Query HAS | Interrupt enable mask |

### DMA Initialization Flow

1. **Allocate Descriptors** — Allocate memory for DMA descriptors
2. **Program Base Address** — Write descriptor base to DMA_DESC_BASE
3. **Configure Control** — Set DMA control parameters
4. **Enable Interrupts** — Enable completion interrupts
5. **Enable DMA** — Set DMA_CONTROL enable bit
6. **Submit Descriptors** — Write descriptor count to trigger transfer

## QoS and Prioritization

### DMA Channel Priority

TCSS DMA supports multiple priority levels:

| Priority | Use Case |
|----------|----------|
| **High** | Time-critical (isochronous audio, video streaming) |
| **Medium** | Bulk data transfers |
| **Low** | Background transfers |

### Bandwidth Allocation

DMA scheduler allocates bandwidth based on:
- **Channel priority** — High priority channels get preference
- **QoS requirements** — Guaranteed minimum bandwidth
- **Fairness** — Prevent starvation of low-priority channels

## Validation Points

### DMA Functionality

- [ ] DMA engine enumerates correctly
- [ ] DMA descriptors can be allocated and programmed
- [ ] Single descriptor transfer works
- [ ] Descriptor chaining works for large transfers
- [ ] DMA completion interrupts fire correctly

### DMA Performance

- [ ] USB3 DMA achieves expected throughput (~440 MB/s)
- [ ] PCIe DMA achieves expected throughput (~3.5 GB/s)
- [ ] DP DMA supports 4K @60Hz without frame drops
- [ ] Latency within acceptable range (<100 µs)

### Error Handling

- [ ] DMA timeout detection works
- [ ] Invalid descriptor handling correct
- [ ] Memory access errors reported
- [ ] DMA can be reset and reinitialized after error

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| DMA not starting | Descriptor address invalid, DMA not enabled | Check descriptor base, verify DMA_CONTROL |
| Transfer incomplete | Descriptor size incorrect, timeout | Verify descriptor fields, check status |
| Completion interrupt not firing | Interrupt enable not set, MSI misconfiguration | Check interrupt enable, verify MSI setup |
| Low throughput | Descriptor chaining inefficient, memory bandwidth bottleneck | Optimize descriptor count, check memory bandwidth |
| Data corruption | Buffer alignment issue, cache coherency problem | Verify buffer alignment, check cache settings |

## Debug Tools

### Linux

```bash
# DMA controller info
ls /sys/class/dma/

# Check DMA statistics
cat /sys/kernel/debug/dma_buf/bufinfo
```

### Windows

```powershell
# DMA controller enumeration
Get-WmiObject Win32_DMAChannel

# Performance counters
Get-Counter "\Memory\*"
```

### PythonSV

```python
# DMA register access (example — verify against HAS)
dma = getattr(target, "tcss_dma")
dma_status = dma.status.read()
desc_base = dma.descriptor_base.read()
int_status = dma.interrupt_status.read()

print(f"DMA Status: 0x{dma_status:08X}")
print(f"Descriptor Base: 0x{desc_base:016X}")
print(f"Interrupt Status: 0x{int_status:08X}")
```

## Performance Optimization

### Best Practices

| Technique | Benefit |
|-----------|---------|
| **Descriptor chaining** | Reduces CPU overhead, improves throughput |
| **Buffer alignment** | Enables efficient DMA, avoids partial transfers |
| **Interrupt coalescing** | Reduces interrupt overhead for bulk transfers |
| **Prefetching** | Overlaps descriptor fetch with data transfer |
| **Large buffers** | Reduces descriptor overhead, improves efficiency |

### Buffer Alignment

Optimal buffer alignment:
- **Start address:** Page-aligned (4KB boundary)
- **Size:** Multiple of cache line (64 bytes)
- **End address:** Avoid crossing page boundary when possible

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — DMA engine registers, descriptor format
- **USB4 Spec:** USB4 Specification v2.0 — DMA tunneling
- **PCIe Spec:** PCI Express Base Specification — TLP format

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
