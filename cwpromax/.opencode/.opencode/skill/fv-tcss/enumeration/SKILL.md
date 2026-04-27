# TCSS Enumeration — PCI Discovery and Device Tree Validation

## Overview

This sub-skill covers TCSS device enumeration, PCI configuration space setup, BDF/BAR allocation, and device tree validation for Type-C Subsystem components.

## PCI Configuration

### TCSS PCI Topology

TCSS devices appear as PCI endpoints in the system topology:

```
PCIe Root Complex
└── TCSS Controller (iTBT)
    ├── USB4 Router (Function 0)
    ├── Thunderbolt DMA Controller (Function 1)
    └── Additional Functions (platform-specific)
```

### BDF Assignment

> **CRITICAL:** BDF (Bus:Device:Function) assignments are **platform-specific**. Always verify via HAS or runtime enumeration.

| Platform | TCSS Controller BDF | Notes |
|----------|---------------------|-------|
| MTL      | Query HAS           | Platform-specific |
| NVL      | Query HAS           | Platform-specific |
| TTL      | Query HAS           | Platform-specific |

### Device ID / Vendor ID

| Platform | Device ID (DID) | Vendor ID (VID) | Notes |
|----------|-----------------|-----------------|-------|
| MTL      | Query HAS       | 0x8086          | Intel vendor ID |
| NVL      | Query HAS       | 0x8086          | Intel vendor ID |
| TTL      | Query HAS       | 0x8086          | Intel vendor ID |

## BAR Configuration

### BAR0 — MMIO Register Space

TCSS devices use BAR0 for memory-mapped I/O register access:

- **Size:** Platform-specific (typically 64KB - 256KB)
- **Type:** 64-bit addressing, prefetchable
- **Access:** Memory-mapped register read/write

### Register Access Pattern

```python
# PythonSV example
tcss = getattr(target, "tcss")  # or platform-specific namednode
device_id = tcss.cfg.device_id.read()
bar0_addr = tcss.cfg.bar0.read()
```

## Enumeration Flow

### BIOS Enumeration (Pre-OS)

1. **PCI Bus Scan** — BIOS discovers TCSS devices
2. **BAR Allocation** — BIOS assigns memory ranges
3. **Capability Setup** — PCIe capabilities configured
4. **TCSS Initialization** — Basic TCSS controller init
5. **IOM Configuration** — I/O Manager setup for port routing

### OS Enumeration (Runtime)

1. **Driver Load** — Thunderbolt/USB4 driver initialization
2. **Device Binding** — Driver binds to TCSS PCI device
3. **Router Discovery** — USB4 router enumeration
4. **Adapter Enumeration** — Protocol adapters discovered (USB3, DP, PCIe)
5. **Topology Mapping** — Device tree construction

## Validation Points

### Pre-OS Checks

- [ ] TCSS device appears in PCI configuration space
- [ ] Device ID matches platform specification
- [ ] BAR0 is allocated and accessible
- [ ] PCIe capabilities are properly configured
- [ ] BIOS initialization completes without errors

### OS Runtime Checks

- [ ] Thunderbolt/USB4 driver loads successfully
- [ ] USB4 router is discovered
- [ ] Protocol adapters enumerate correctly
- [ ] Device tree topology is correct
- [ ] No yellow-bang (driver failure) in Device Manager

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| TCSS device not found | BIOS disabled, straps incorrect, silicon issue | Check BIOS settings, verify BDF via lspci/devmgmt |
| BAR0 not allocated | Resource conflict, BIOS bug | Check PCI resource allocation, BIOS logs |
| Driver fails to load | Incorrect DID, missing FW, OS incompatibility | Verify DID, check driver version, review OS logs |
| Router not discovered | Link training failure, IOM misconfiguration | Check link status, IOM registers, cable connection |

## Debug Tools

### Linux

```bash
# List PCI devices
lspci -vv | grep -i thunderbolt

# Check USB4 router
cat /sys/bus/thunderbolt/devices/*/device

# Kernel messages
dmesg | grep -i thunderbolt
```

### Windows

```powershell
# Device Manager
devmgmt.msc

# PCI device enumeration
pnputil /enum-devices /class USB4
```

### PythonSV

```python
# Direct register access
tcss = getattr(target, "tcss")
did = tcss.cfg.device_id.read()
vid = tcss.cfg.vendor_id.read()
bar0 = tcss.cfg.bar0.read()

print(f"DID: 0x{did:04X}, VID: 0x{vid:04X}, BAR0: 0x{bar0:016X}")
```

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — Device IDs, BDF, BAR configuration
- **PCIe Spec:** PCI Express Base Specification
- **USB4 Spec:** USB4 Specification — Router discovery

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
