# TCSS USB4 — USB4 Router and Tunneling Protocol Validation

## Overview

This sub-skill covers USB4 router configuration, tunneling protocols, link management, and bandwidth allocation for Type-C Subsystem validation.

## USB4 Architecture

### USB4 Router

The USB4 router is the central component managing packet routing and tunneling:

```
┌─────────────────────────────────────────┐
│         USB4 Router                     │
│  ┌──────────────────────────────────┐   │
│  │   Configuration Manager          │   │
│  │   (Router ops, adapter config)   │   │
│  └──────────┬───────────────────────┘   │
│             │                           │
│  ┌──────────┴───────────────────────┐   │
│  │   Tunnel Manager                 │   │
│  │   (USB3, DP, PCIe tunnels)       │   │
│  └──────────┬───────────────────────┘   │
│             │                           │
│  ┌──────────┴───────────────────────┐   │
│  │   Path Manager                   │   │
│  │   (Bandwidth allocation)         │   │
│  └──────────┬───────────────────────┘   │
│             │                           │
│  ┌──────────┴───────────────────────┐   │
│  │   Protocol Adapters              │   │
│  │   USB3 | DP-IN | DP-OUT | PCIe   │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Router** | Central switching element — manages packet routing |
| **Adapter** | Protocol-specific endpoint (USB3, DP, PCIe) |
| **Tunnel** | Logical data path between adapters |
| **Path** | Physical link lanes allocated to a tunnel |
| **Bandwidth** | Link capacity allocation (Mb/s) |

## USB4 Tunneling

### Tunnel Types

| Tunnel Type | Description | Use Case |
|-------------|-------------|----------|
| **USB3** | USB 3.x tunneling | External USB devices |
| **DP-IN** | DisplayPort input tunneling | DP source to USB4 host |
| **DP-OUT** | DisplayPort output tunneling | DP sink from USB4 host |
| **PCIe** | PCIe tunneling | External PCIe devices (eGPU, storage) |

### Tunnel Establishment Flow

1. **Adapter Discovery** — Enumerate available adapters
2. **Path Allocation** — Assign physical lanes to tunnel
3. **Bandwidth Negotiation** — Allocate link capacity
4. **Tunnel Setup** — Configure tunnel endpoints
5. **Data Transfer** — Packet routing through tunnel

### Bandwidth Management

USB4 supports dynamic bandwidth allocation:

| Link Speed | Total Bandwidth | Available for Tunneling |
|------------|----------------|-------------------------|
| Gen 2 (USB4 20Gbps) | 20 Gbps | ~16 Gbps (after overhead) |
| Gen 3 (USB4 40Gbps) | 40 Gbps | ~32 Gbps (after overhead) |
| Gen 4 (USB4 80Gbps) | 80 Gbps | ~64 Gbps (after overhead) |

## Router Configuration

### Router Registers (via Config Space)

> **CRITICAL:** Always verify register offsets against platform HAS.

| Register | Offset | Description |
|----------|--------|-------------|
| Router UUID | Query HAS | Unique router identifier |
| Router Operations | Query HAS | Router control operations |
| Adapter Configuration | Query HAS | Per-adapter config registers |
| Path Configuration | Query HAS | Lane assignment and bandwidth |

### Router Operations

| Operation | Description |
|-----------|-------------|
| **ROUTER_READ** | Read router configuration register |
| **ROUTER_WRITE** | Write router configuration register |
| **ADAPTER_READ** | Read adapter-specific register |
| **ADAPTER_WRITE** | Write adapter-specific register |

## Link Training

### USB4 Link States

| State | Description |
|-------|-------------|
| **Disabled** | Link not active |
| **Detect** | Detecting connection |
| **Training** | Link training in progress |
| **Active** | Link operational |
| **Sleep** | Low-power state |

### Link Training Sequence

1. **Cable Detection** — Type-C orientation detection
2. **Lane Discovery** — Determine available lanes (1x, 2x, 4x)
3. **Speed Negotiation** — Agree on Gen 2/3/4 speed
4. **Lane Training** — Per-lane electrical training
5. **Link Active** — Data transfer ready

## Validation Points

### Router Discovery

- [ ] USB4 router enumerated successfully
- [ ] Router UUID readable
- [ ] Adapter count matches platform specification
- [ ] Router firmware version correct

### Link Training

- [ ] Link transitions to Active state
- [ ] Lane count matches cable capability
- [ ] Link speed matches platform support (Gen 2/3/4)
- [ ] No link training errors in logs

### Tunneling

- [ ] USB3 tunnel established for USB devices
- [ ] DP tunnel established for display output
- [ ] PCIe tunnel established for eGPU/storage
- [ ] Bandwidth allocation correct for active tunnels

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| Router not discovered | Link training failure, cable issue | Check cable, orientation, link status |
| Tunnel establishment fails | Insufficient bandwidth, adapter config error | Check bandwidth allocation, adapter registers |
| Data corruption in tunnel | Lane training error, signal integrity | Check BER (Bit Error Rate), cable quality |
| Performance degradation | Incorrect lane count, speed negotiation failure | Verify lane count, link speed, bandwidth |

## Debug Tools

### Linux

```bash
# USB4 router info
cat /sys/bus/thunderbolt/devices/0-0/device_name
cat /sys/bus/thunderbolt/devices/0-0/unique_id

# Tunnel information
ls /sys/bus/thunderbolt/devices/0-0/*/

# Link speed
cat /sys/bus/thunderbolt/devices/0-0/link_speed
```

### Windows

```powershell
# Thunderbolt topology
Get-PnpDevice -Class USB4

# Router information
Get-WmiObject -Namespace root\wmi -Class MSFT_USB4Router
```

### PythonSV

```python
# Router register access (example — verify against HAS)
usb4_router = getattr(target, "usb4_router")
router_uuid = usb4_router.cfg.uuid.read()
adapter_count = usb4_router.cfg.adapter_count.read()

print(f"Router UUID: 0x{router_uuid:016X}")
print(f"Adapter Count: {adapter_count}")
```

## Performance Metrics

### Tunneling Throughput

| Tunnel Type | Expected Throughput | Measurement Method |
|-------------|--------------------|--------------------|
| USB3 | ~3.5 Gbps (USB 3.2 Gen 2) | File transfer, iometer |
| DP | 8.1 Gbps (DP 1.4 HBR3) per lane | Display resolution test |
| PCIe | ~24 Gbps (PCIe 3.0 x4) | NVMe performance test |

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — Router registers, adapter configuration
- **USB4 Spec:** USB4 Specification v2.0 — Router operations, tunneling
- **Thunderbolt Spec:** Thunderbolt 3/4 Specification — Compatibility mode

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
