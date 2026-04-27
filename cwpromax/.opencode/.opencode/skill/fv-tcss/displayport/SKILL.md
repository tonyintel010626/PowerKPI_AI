# TCSS DisplayPort — DisplayPort Alt Mode and Tunneling Validation

## Overview

This sub-skill covers DisplayPort Alt Mode over Type-C, DP tunneling over USB4/Thunderbolt, link training, and stream management for Type-C Subsystem validation.

## DisplayPort Alt Mode Architecture

### DP Alt Mode Overview

DisplayPort Alt Mode allows DP video output over Type-C connector:

```
┌────────────────────────────────────────────┐
│         DisplayPort Source                 │
│         (GPU / Display Engine)             │
└──────────────┬─────────────────────────────┘
               │
               │ DP Lanes (1, 2, or 4 lanes)
               ↓
┌──────────────┴─────────────────────────────┐
│         Type-C Mux (via IOM)               │
│  ┌──────────────────────────────────────┐  │
│  │  DP Alt Mode Configuration           │  │
│  │  • 2-lane DP + USB3 (common)         │  │
│  │  • 4-lane DP (full bandwidth)        │  │
│  └──────────────────────────────────────┘  │
└──────────────┬─────────────────────────────┘
               │
               │ Type-C Physical Connector
               ↓
      ┌────────┴────────┐
      │  DP-capable     │
      │  Type-C Device  │
      │  (Monitor, Dock)│
      └─────────────────┘
```

### DP Alt Mode Configurations

| Configuration | DP Lanes | USB3 | Bandwidth per Lane |
|---------------|----------|------|--------------------|
| **2-lane DP** | 2 | Yes | HBR3: 8.1 Gbps/lane |
| **4-lane DP** | 4 | No | HBR3: 8.1 Gbps/lane |

**Resolution Support:**
- **2-lane DP (HBR3):** 4K @60Hz (8 bpc)
- **4-lane DP (HBR3):** 8K @30Hz or 4K @120Hz (8 bpc)

## DisplayPort Tunneling (over USB4/TBT)

### DP-IN Tunnel

DisplayPort input tunneling (DP-IN) — device sends DP to host:

```
Device (DP Source) → USB4/TBT Tunnel → Host (DP Sink)
```

**Use Case:** Laptop as display for external device

### DP-OUT Tunnel

DisplayPort output tunneling (DP-OUT) — host sends DP to device:

```
Host (DP Source) → USB4/TBT Tunnel → Device (DP Sink)
```

**Use Case:** External monitor via Thunderbolt dock

### Tunnel Bandwidth Allocation

DP tunneling shares USB4/TBT link bandwidth:

| Link Speed | Total Bandwidth | DP Allocation (example) |
|------------|----------------|-------------------------|
| USB4 40Gbps | 40 Gbps | Up to 32 Gbps for DP |
| USB4 80Gbps | 80 Gbps | Up to 64 Gbps for DP |

**Bandwidth Negotiation:**
- Host allocates bandwidth to DP tunnel based on resolution/refresh rate
- Remaining bandwidth available for USB/PCIe tunnels

## DP Link Training

### Link Training States

| State | Description |
|-------|-------------|
| **Clock Recovery** | RX locks to TX clock signal |
| **Equalization** | Optimize signal quality (DP 1.4+) |
| **Symbol Lock** | RX achieves symbol-level synchronization |
| **Inter-lane Alignment** | Multi-lane alignment |
| **Link Training Success** | All lanes trained, ready for video |

### Link Rate Negotiation

| Link Rate | Bandwidth per Lane | Total Bandwidth (4 lanes) |
|-----------|--------------------|---------------------------|
| **RBR (1.62 Gbps)** | 1.62 Gbps | 6.48 Gbps |
| **HBR (2.7 Gbps)** | 2.7 Gbps | 10.8 Gbps |
| **HBR2 (5.4 Gbps)** | 5.4 Gbps | 21.6 Gbps |
| **HBR3 (8.1 Gbps)** | 8.1 Gbps | 32.4 Gbps |

**Fallback Behavior:**
- Link training starts at highest rate (HBR3)
- If training fails, fallback to lower rate (HBR2 → HBR → RBR)
- If still failing, reduce lane count (4 → 2 → 1)

## Hot Plug Detect (HPD)

### HPD Signal

Hot Plug Detect (HPD) indicates display connection status:

| HPD State | Meaning |
|-----------|---------|
| **Low** | No display connected (or display powered off) |
| **High** | Display connected and ready |
| **Pulse** | Display state change (resolution change, etc.) |

### HPD Flow

1. **Display Connect** — Type-C cable plugged in
2. **HPD Assert** — Display asserts HPD signal
3. **EDID Read** — Host reads display capabilities (EDID)
4. **Link Training** — DP link training initiated
5. **Video Stream** — Video output starts

## EDID (Extended Display Identification Data)

### EDID Reading

EDID contains display capabilities:
- **Supported resolutions** — e.g., 1920x1080, 3840x2160
- **Refresh rates** — e.g., 60Hz, 120Hz
- **Color depth** — e.g., 8 bpc, 10 bpc
- **Audio support** — Supported audio formats

### EDID Read Process

1. **HPD Asserted** — Display connected
2. **I2C/AUX Read** — Host reads EDID via I2C or DP AUX channel
3. **Parse EDID** — Extract display capabilities
4. **Mode Selection** — Choose resolution/refresh rate
5. **Link Training** — Train to required bandwidth

## Validation Points

### DP Alt Mode

- [ ] DP Alt Mode negotiated correctly (2-lane or 4-lane)
- [ ] HPD signal detected and handled
- [ ] EDID read successfully
- [ ] Link training completes at expected rate (HBR3/HBR2/HBR)
- [ ] Video output visible on display

### DP Tunneling

- [ ] DP tunnel established over USB4/TBT
- [ ] Bandwidth allocated correctly
- [ ] Link training succeeds within tunnel
- [ ] Video output stable (no flicker, artifacts)
- [ ] Audio over DP functional (if supported)

### Resolution Support

- [ ] 4K @60Hz works on 2-lane DP Alt Mode
- [ ] 8K @30Hz works on 4-lane DP Alt Mode
- [ ] Highest EDID-advertised resolution works
- [ ] Refresh rate matches display capability

### Multi-Display

- [ ] Dual 4K @60Hz via Thunderbolt dock
- [ ] MST (Multi-Stream Transport) if supported
- [ ] Daisy-chained displays work correctly

## Common Failures

| Symptom | Possible Causes | Debug Steps |
|---------|----------------|-------------|
| No video output | HPD not detected, link training failure | Check HPD status, DP link training logs |
| Low resolution only | Link training fallback, cable issue | Verify link rate, check cable spec |
| Flickering / artifacts | Signal integrity, bandwidth insufficient | Check BER, verify bandwidth allocation |
| Audio not working | Audio tunnel not established, EDID issue | Verify audio in EDID, check audio tunnel |
| Display not detected | EDID read failure, I2C/AUX issue | Retry EDID read, check AUX channel |

## Debug Tools

### Linux

```bash
# DP connector status
cat /sys/class/drm/card0-DP-*/status

# EDID dump
cat /sys/class/drm/card0-DP-*/edid | edid-decode

# DP link info
cat /sys/kernel/debug/dri/0/DP-*/i915_dp_link_info

# DP AUX channel
ls /dev/drm_dp_aux*
```

### Windows

```powershell
# Display configuration
Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBasicDisplayParams

# Display EDID
Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorDescriptorMethods

# Event logs for DP
Get-WinEvent -LogName "Microsoft-Windows-DisplayDeviceAdapter/Operational"
```

### PythonSV

```python
# DP controller registers (example — verify against HAS)
dp_ctrl = getattr(target, "displayport")
hpd_status = dp_ctrl.hpd.status.read()
link_rate = dp_ctrl.link.rate.read()
lane_count = dp_ctrl.link.lane_count.read()

print(f"HPD Status: {hpd_status}")
print(f"Link Rate: {link_rate} (0=RBR, 1=HBR, 2=HBR2, 3=HBR3)")
print(f"Lane Count: {lane_count}")
```

## Performance Metrics

### Link Training Time

| Configuration | Typical Time | Max Time |
|---------------|--------------|----------|
| Single display (4K @60Hz) | <500 ms | 2 seconds |
| Dual display (2x 4K @60Hz) | <1 second | 3 seconds |

### Supported Resolutions

| Configuration | Resolution | Refresh Rate | Color Depth |
|---------------|------------|--------------|-------------|
| 2-lane DP (HBR3) | 4K (3840x2160) | 60Hz | 8 bpc |
| 4-lane DP (HBR3) | 4K (3840x2160) | 120Hz | 8 bpc |
| 4-lane DP (HBR3) | 8K (7680x4320) | 30Hz | 8 bpc |
| 4-lane DP (HBR3) + DSC | 8K (7680x4320) | 60Hz | 8 bpc |

## Reference Documents

- **HAS:** `<PLATFORM>_TCSS_HAS` — DP controller registers
- **DP Alt Mode Spec:** DisplayPort Alt Mode on USB Type-C Standard
- **DP Spec:** VESA DisplayPort Standard (v1.4, v2.0)
- **USB4 Spec:** USB4 Specification v2.0 — DP tunneling

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
