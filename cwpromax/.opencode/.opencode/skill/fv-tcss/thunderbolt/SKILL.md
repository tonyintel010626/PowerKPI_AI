# TCSS Thunderbolt — Thunderbolt 4/3 Authentication and Link Management

## Overview

This sub-skill covers Thunderbolt 4/3 authentication, link training, security features, and daisy-chaining validation for Type-C Subsystem.

## Thunderbolt Architecture

### Thunderbolt Controller

```
┌──────────────────────────────────────────┐
│     Thunderbolt Controller (iTBT)        │
│  ┌───────────────────────────────────┐   │
│  │   Security Manager                │   │
│  │   (Authentication, authorization) │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Connection Manager              │   │
│  │   (Link training, topology)       │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Port Manager                    │   │
│  │   (Per-port state, hotplug)       │   │
│  └───────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

## Thunderbolt Security

### Security Levels

| Security Level | Description | User Action Required |
|----------------|-------------|----------------------|
| **None (SL0)** | No authentication | None — auto-connect |
| **User Authorization (SL1)** | User approves new devices | Manual approval via OS |
| **Secure Connect (SL2)** | Challenge-response authentication | Pairing on first connect |
| **Display Port Only (SL3)** | Only DP allowed, USB/PCIe blocked | N/A for USB4 mode |

> **NOTE:** Thunderbolt 4 requires minimum SL1 (User Authorization) by specification.

### Authentication Flow

1. **Device Connect** — Cable plugged in, electrical connection established
2. **Device Discovery** — Controller reads device UUID
3. **Security Check** — Verify device against policy
4. **Challenge-Response** (SL2) — Cryptographic authentication
5. **Authorization Grant** — Device authorized to access system
6. **Enumeration** — Device services (USB, DP, PCIe) available

## Thunderbolt Link Training

### Link States

| State | Description |
|-------|-------------|
| **Disconnected** | No cable detected |
| **Connected** | Cable detected, link inactive |
| **Training** | Link training in progress |
| **Authenticated** | Security passed, not yet operational |
| **Authorized** | Device authorized, enumeration active |
| **Active** | Fully operational, data transfer ready |

### Link Training Sequence

1. **Cable Detection** — Type-C plug orientation detection
2. **Power Delivery** — USB-PD negotiation
3. **Sideband Discovery** — Read device capabilities
4. **Link Training** — Electrical training (Gen 2/3/4)
5. **Authentication** — Security challenge-response
6. **Enumeration** — Expose device services

## Thunderbolt Topology

### Daisy-Chaining

Thunderbolt supports up to **6 devices** in a daisy-chain:

```
Host ─── Device 1 ─── Device 2 ─── Device 3 ─── ... ─── Device 6
```

**Bandwidth Sharing:**
- Total bandwidth shared across all daisy-chained devices
- Downstream devices limited by upstream link speed
- Dynamic allocation based on active traffic

### Topology Discovery

Thunderbolt controller builds a topology map:

```
Domain 0 (Host)
├── Port 0
│   └── Device 1 (Router)
│       ├── Port 1 (upstream to host)
│       ├── Port 3 (USB adapter)
│       ├── Port 4 (DP adapter)
│       └── Port 5 (PCIe adapter)
└── Port 1
    └── Device 2 (Router)
```

## Thunderbolt 4 vs Thunderbolt 3

| Feature | Thunderbolt 3 | Thunderbolt 4 |
|---------|---------------|---------------|
| **Max Speed** | 40 Gbps | 40 Gbps |
| **PCIe Requirement** | 16 Gbps | 32 Gbps |
| **DisplayPort** | DP 1.2 (2 streams) | DP 1.4 (2 streams) |
| **USB Requirement** | USB 3.1 Gen 2 | USB 3.2 Gen 2 (10 Gbps) |
| **Daisy-Chain** | 6 devices | 6 devices |
| **Security** | Optional | Minimum SL1 required |
| **Wake from S4** | Optional | Required |
| **Cable Length** | 0.5m (40 Gbps passive) | 2m (40 Gbps active) |

## Validation Points

### Authentication

- [ ] Device authentication completes within timeout (typically 2-3 seconds)
- [ ] Security level enforced correctly (SL0/SL1/SL2)
- [ ] Unauthorized devices rejected appropriately
- [ ] Re-authentication after cable unplug/replug works

### Link Training

- [ ] Link trains to maximum supported speed (20/40/80 Gbps)
- [ ] Lane count matches cable capability
- [ ] No link training errors in controller logs
- [ ] Link remains stable under load

### Daisy-Chaining

- [ ] All devices in chain enumerated correctly
- [ ] Topology map accurate
- [ ] Bandwidth allocation correct
- [ ] Hot-plug/unplug of intermediate devices handled gracefully

### Thunderbolt 4 Compliance

- [ ] PCIe minimum 32 Gbps enforced
- [ ] DP 1.4 with 2 streams supported
- [ ] USB 3.2 Gen 2 (10 Gbps) minimum
- [ ] Security level SL1 or higher
- [ ] Wake from S4 functional
- [ ] 2m active cable support

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| Authentication timeout | Device firmware issue, security policy misconfiguration | Check device UUID, security level, firmware version |
| Link training failure | Cable defect, signal integrity issue | Try different cable, check link speed negotiation |
| Device not authorized | Security level too restrictive, user denied access | Verify security policy, check OS authorization UI |
| Daisy-chain fails | Bandwidth exhausted, topology limit reached | Check device count, total bandwidth usage |
| Performance degradation | Lane degradation, cable length exceeded | Verify lane count, cable specification |

## Debug Tools

### Linux

```bash
# Thunderbolt domain and devices
ls /sys/bus/thunderbolt/devices/

# Device authorization status
cat /sys/bus/thunderbolt/devices/0-1/authorized

# Security level
cat /sys/bus/thunderbolt/devices/domain0/security

# Authorize device manually
echo 1 > /sys/bus/thunderbolt/devices/0-1/authorized
```

### Windows

```powershell
# Thunderbolt devices
Get-PnpDevice -FriendlyName *Thunderbolt*

# Device authorization (via Thunderbolt Control Center)
# GUI: System Settings > Privacy & Security > Thunderbolt

# Event logs
Get-WinEvent -LogName "Microsoft-Windows-Thunderbolt/Operational"
```

### PythonSV

```python
# Thunderbolt controller registers (example — verify against HAS)
tbt_ctrl = getattr(target, "thunderbolt_controller")
security_level = tbt_ctrl.security.level.read()
link_status = tbt_ctrl.link.status.read()

print(f"Security Level: {security_level}")
print(f"Link Status: 0x{link_status:08X}")
```

## Performance Benchmarks

### PCIe Tunneling

| Configuration | Expected Throughput |
|---------------|---------------------|
| PCIe 3.0 x4 (32 Gbps) | ~3.5 GB/s (28 Gbps effective) |
| NVMe SSD over TBT4 | ~2.8 GB/s read, ~2.5 GB/s write |

### DisplayPort Tunneling

| Configuration | Max Resolution |
|---------------|----------------|
| DP 1.4 HBR3 (single stream) | 8K @30Hz or 4K @120Hz |
| DP 1.4 HBR3 (dual stream) | Dual 4K @60Hz |

## Reference Documents

- **HAS:** `iTBT80G_HAS` — Thunderbolt controller registers
- **Thunderbolt 4 Spec:** Thunderbolt 4 Specification — Requirements and compliance
- **Thunderbolt 3 Spec:** Thunderbolt 3 Specification — Legacy compatibility
- **USB4 Spec:** USB4 Specification v2.0 — Thunderbolt compatibility mode

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
