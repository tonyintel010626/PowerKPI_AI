# TCSS IOM — I/O Manager Configuration and Mux Control

## Overview

This sub-skill covers I/O Manager (IOM) configuration, Type-C mux control, orientation detection, and port management for Type-C Subsystem validation.

## I/O Manager (IOM) Architecture

### IOM Overview

The I/O Manager (IOM) is the orchestrator of TCSS port configuration:

```
┌──────────────────────────────────────────┐
│           I/O Manager (IOM)              │
│  ┌───────────────────────────────────┐   │
│  │   Port Configuration Manager      │   │
│  │   (USB/DP/TBT mode selection)     │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Mux Controller                  │   │
│  │   (Signal routing, orientation)   │   │
│  └──────────┬────────────────────────┘   │
│             │                            │
│  ┌──────────┴────────────────────────┐   │
│  │   Power Management Interface      │   │
│  │   (D-state coordination)          │   │
│  └───────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### Key Responsibilities

| Function | Description |
|----------|-------------|
| **Port Mode Selection** | Choose between USB2/3, DP Alt Mode, TBT/USB4 |
| **Mux Control** | Route signals to correct protocol (USB/DP/TBT) |
| **Orientation Detection** | Detect Type-C plug orientation (normal/flipped) |
| **Power Delivery Coordination** | Interface with USB-PD controller |
| **HPD Management** | Handle Hot Plug Detect for DisplayPort |
| **Power State Management** | Coordinate port power states with system PM |

## Type-C Mux Architecture

### Signal Routing

Type-C connector has multiple possible signal assignments:

| Mode | Signals Routed |
|------|----------------|
| **USB 3.x** | USB3 TX/RX differential pairs |
| **DP Alt Mode (2-lane)** | 2 DP lanes + USB3 |
| **DP Alt Mode (4-lane)** | 4 DP lanes (no USB3) |
| **Thunderbolt/USB4** | High-speed lanes for TBT/USB4 protocol |

### Mux States

| Mux State | Description |
|-----------|-------------|
| **Safe State** | No high-speed signals (USB 2.0 only) |
| **USB** | USB 3.x mode active |
| **DP** | DisplayPort Alt Mode (2-lane or 4-lane) |
| **TBT/USB4** | Thunderbolt or USB4 mode |

## Orientation Detection

### Type-C Orientation

Type-C connectors are reversible — orientation must be detected:

```
Normal Orientation:
Type-C Plug Pin 1 ────→ Type-C Receptacle Pin 1

Flipped Orientation:
Type-C Plug Pin 1 ────→ Type-C Receptacle Pin 12
```

### CC (Configuration Channel) Detection

The CC pins (CC1, CC2) indicate:
- **Cable orientation** — which CC pin has pull-up/pull-down
- **Cable type** — USB 2.0, USB 3.x, or USB4/TBT capable
- **Power capability** — USB-PD current advertisement

## IOM Register Configuration

> **CRITICAL:** Always verify register offsets and bit fields against platform HAS.

### Key IOM Registers

| Register | Offset | Description |
|----------|--------|-------------|
| IOM_PORT_CONFIG | Query HAS | Port mode and mux state configuration |
| IOM_PORT_STATUS | Query HAS | Port connection status and orientation |
| IOM_MUX_CONTROL | Query HAS | Mux state control |
| IOM_POWER_MGMT | Query HAS | Port power state management |
| IOM_HPD_CONTROL | Query HAS | Hot Plug Detect for DP Alt Mode |

### Port Configuration Flow

1. **Cable Connect** — Type-C cable inserted
2. **CC Detection** — Determine orientation and cable type
3. **Mode Negotiation** — Select port mode (USB/DP/TBT)
4. **Mux Configuration** — Route signals to selected protocol
5. **Controller Enable** — Enable corresponding controller (USB/DP/TBT)
6. **Device Enumeration** — Downstream device enumeration

## Port Modes

### USB Mode

When USB device is connected (no DP/TBT):
- Mux routes USB3 TX/RX to USB controller
- USB 2.0 always available (not muxed)
- USB 3.x speed negotiation

### DP Alt Mode

When DP-capable device is connected:
- **2-lane DP:** 2 DP lanes + USB3 (most common)
- **4-lane DP:** 4 DP lanes (no USB3)
- HPD (Hot Plug Detect) routed to DP controller
- DP link training initiated

### Thunderbolt/USB4 Mode

When TBT/USB4 device is connected:
- All high-speed lanes allocated to TBT/USB4
- USB tunneling over TBT/USB4 (no direct USB3)
- DP tunneling over TBT/USB4 (if DP device attached)
- PCIe tunneling for external devices

## Validation Points

### IOM Configuration

- [ ] IOM enumerated correctly in PCI space
- [ ] IOM registers accessible
- [ ] Port count matches platform specification
- [ ] IOM firmware version correct

### Mux Control

- [ ] Mux state transitions correctly (Safe → USB/DP/TBT)
- [ ] Signal routing matches selected mode
- [ ] Orientation detection accurate (normal/flipped)
- [ ] No signal integrity issues after mux switch

### Port Mode Selection

- [ ] USB mode selected for USB-only devices
- [ ] DP Alt Mode selected for DP devices
- [ ] TBT/USB4 mode selected for TBT devices
- [ ] Mode selection completes within timeout

### HPD Management

- [ ] HPD signal correctly routed to DP controller
- [ ] DP link training triggered on HPD assert
- [ ] HPD toggling handled correctly (cable unplug/replug)

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| Device not detected | CC detection failure, cable defect | Check CC status, try different cable |
| Wrong mode selected | IOM configuration error, FW bug | Verify IOM registers, check FW version |
| Orientation detection wrong | CC pin issue, platform wiring error | Test both orientations, check schematic |
| Mux state stuck | IOM FW hang, register write failure | Reset IOM, check register access |
| DP not working in Alt Mode | Mux routing incorrect, HPD not asserted | Verify mux state, check HPD signal |

## Debug Tools

### Linux

```bash
# Type-C port status
ls /sys/class/typec/port*/

# Port data role
cat /sys/class/typec/port0/data_role

# Port mode (USB/DP/TBT)
cat /sys/class/typec/port0/port_type

# Orientation
cat /sys/class/typec/port0/orientation
```

### Windows

```powershell
# Type-C connector status
Get-PnpDevice -FriendlyName *USB*Type-C*

# USB-PD information (via Device Manager properties)
Get-WmiObject Win32_PnPEntity | Where-Object {$_.Name -like "*Type-C*"}
```

### PythonSV

```python
# IOM register access (example — verify against HAS)
iom = getattr(target, "iom")
port_config = iom.port0.config.read()
mux_state = iom.port0.mux_state.read()
orientation = iom.port0.orientation.read()

print(f"Port Config: 0x{port_config:08X}")
print(f"Mux State: {mux_state}")
print(f"Orientation: {'Flipped' if orientation else 'Normal'}")
```

## Performance Considerations

### Mux Switching Time

| Transition | Typical Time | Max Time |
|------------|--------------|----------|
| Safe → USB | <10 ms | 50 ms |
| Safe → DP | <20 ms | 100 ms |
| Safe → TBT | <50 ms | 200 ms |
| Mode switch | <100 ms | 500 ms |

### Signal Integrity

Mux quality affects:
- **USB 3.x:** Eye diagram margin, BER (Bit Error Rate)
- **DP Alt Mode:** Link training success, max resolution
- **TBT/USB4:** Link speed (Gen 2/3/4 capability)

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — IOM register maps
- **USB Type-C Spec:** USB Type-C Cable and Connector Specification
- **USB-PD Spec:** USB Power Delivery Specification
- **DP Alt Mode Spec:** DisplayPort Alt Mode on USB Type-C Standard

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
