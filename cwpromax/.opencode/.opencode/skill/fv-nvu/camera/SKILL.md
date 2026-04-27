name: fv-nvu/camera
description: NVU camera/sensor interface architecture — MIPI CSI-2, USB camera, Altek ISP, PHY sharing, and MJPEG decoder

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`) — william.willy.chin@intel.com, Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.
>
> **⚠️ NEVER trust AI 100%.** This skill file is a productivity aid, not a replacement for engineering judgment. AI can hallucinate, confuse similar IPs (e.g., NVU vs NVL/NPU6), or present outdated information as current. **When in doubt, verify with the owner/co-owner or check the authoritative HAS document directly.** For CoDeSign-based HAS verification, see the FV-NVU agent definition (`FV-NVU.md`).

# NVU Camera / Sensor Interfaces

> **SAFETY**: Do NOT modify PHY ownership registers or camera clock configuration without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html), the VISION SS End-To-End HAS v0.1, and the NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revisions.

## Overview

The NVU (Neural Vision/Sensing Unit) interfaces with external cameras and sensors through two independent subsystems:

- **MIPI Interface Sub-System** (Section 8.7) — MIPI CSI-2 Host Controller, Altek Image Signal Processor (CVISP), and PHY Sharing/Control Logic for 3 shared CDPHY instances
- **USB Interface Sub-System** (Section 8.8) — USB Video Offload Logic (UVOL), MJPEG Decoder/Post-Processing, SIO component for peer-to-peer NVU-XHCI-IPU data transfer

Key capabilities:
- MIPI CSI-2 reception via Synopsys DWC_mipi_csi2 host controller (D-PHY up to 2.5Gbps/lane, C-PHY up to 2.5GSps/trio)
- Altek CVISP for on-die image signal processing (AE/AWB/AFD, motion detection, frame rate control)
- PHY sharing arbitration between NVU and IPU for 3 CDPHY instances (CDPHY_A/B/C)
- USB camera video offload with UVC/CCPAL/SEP de-packetization
- Verisilicon VC9000NanoD MJPEG decoder for 4K@30fps MJPEG decoding
- Separate power domains: PAR_MIPI (MIPI_SS) and PAR_USB (USB_SS) with independent PGCB power gating


## Vision Subsystem End-to-End Architecture (E2E HAS v0.1)

> Source: VISION SS End-To-End HAS v0.1 (Alok Anand, Aug 2025). This section covers system-level flows between IPU, NVU, and XHCI_CAM. The E2E HAS is complementary to the NVU IP HAS v1.0 — it covers inter-IP coordination, not internal NVU register details.

### Three-IP Vision Subsystem

The vision subsystem consists of three IP blocks connected via **SIO** over the NoC fabric:

- **IPU** (Image Processing Unit) — primary camera host, has priority for PHY ownership
- **NVU** (Neural Vision Sensing Unit) — always-on visual sensing, shares PHY with IPU; configures 11 SIO Pins (9 host-mode toward XHCI_CAM, 2 device-mode toward IPU)
- **XHCI_CAM** — XHCI Controller, camera-optimized, for USB camera support

```
  ┌─────┐     SIO 2.0      ┌─────┐     SIO 2.0      ┌───────────┐
  │ IPU │ ◄──────────────► │ NVU │ ◄──────────────► │ XHCI_CAM  │
  └──┬──┘   (over           └──┬──┘   (over     └─────┬─────┘
     │       NoC fabric)       │       NoC fabric)         │
     │                         │                           │
     ▼                         ▼                           ▼
  MIPI CSI-2 PHY ◄─── shared CDPHY ───► MIPI CSI-2 PHY   USB Camera
  (IPU side)              (NVU side)              (USB RAW/Legacy)
```

Fabric interconnect: **CRUX NoC + Arteris NoC**

### SIO 2.0 Protocol

SIO 2.0 extends the peer-to-peer technology from **SIO 1.0** (the base spec used for audio offload) to add **camera-specific enhancements** for the vision subsystem.

SIO 2.0 uses **Vendor Defined Messages (VDMs)** with **route-by-id** using BDF (Bus/Device/Function) addressing. Supported transaction types:

| Transaction Type | Direction | Purpose |
|-----------------|-----------|---------|
| Config/Register | Bi-directional | Register read/write between IPs (Set_Register / Get_Register) |
| Async Tx | Unidirectional | Asynchronous transmit (control messages) |
| Async Rx | Unidirectional | Asynchronous receive (control messages) |
| Async Bi-Di | Bi-directional | Asynchronous bidirectional (FW2FW communication) |
| ISOCH Rx | Unidirectional | Isochronous receive (camera streaming data) |
| ISOCH Tx | Unidirectional | Isochronous transmit (camera streaming data) |

### SIO Pin Mappings (USB RAW — IPU Hosted)

> Source: E2E HAS v0.1, Page 9, Figure "IPU Hosted RAW". Pin assignments are for USB RAW (CCPAL-U) camera datapath. IPU and NVU share the same pin-function mapping; XHCI_CAM uses a different mapping due to its device-side role.

Each IP has 11 SIO pins (Pin-0 through Pin-10). The table below shows the **USB RAW** pin assignments:

| Pin | IPU Function | NVU Function | XHCI_CAM Function |
|-----|-------------|-------------|-------------------|
| Pin-0 | Config | Config | — |
| Pin-1 | Config | Config | EP0 |
| Pin-2 | INTR OUT (RGB) | INTR OUT (RGB) | ISOCH IN (IR) |
| Pin-3 | INTR OUT (IR) | INTR OUT (IR) | INTR IN (IR) |
| Pin-4 | INTR IN (RGB) | INTR IN (RGB) | INTR OUT (IR) |
| Pin-5 | INTR IN (IR) | INTR IN (IR) | ISOCH IN (RGB) |
| Pin-6 | EP0 | EP0 | INTR IN (RGB) |
| Pin-7 | ISOCH IN (RGB) | ISOCH IN (RGB) | INTR OUT (RGB) |
| Pin-8 | ISOCH IN (IR) | ISOCH IN (IR) | Config |
| Pin-9 | Config (Dev) | Config (Dev) | Config |
| Pin-10 | ISOCH IN (Dev) | ISOCH IN (Dev) | — |

> **Note**: IPU acts as SIO Host Controller (SIO_HC), NVU acts as SIO Device Controller (SIO_DC) in the IPU-NVU SIO link. The XHCI_CAM pin ordering differs because it operates as the device-side SIO endpoint. Pin-0 and Pin-10 are not used by XHCI_CAM in this configuration.
>
> **Open Review (E2E HAS v0.1)**: Reviewer [ningyan] noted that these pin definitions differ from the Camera Offload End-to-End HAS. Reconciliation is pending.

### IPU_AON (Always-On) Logic

The **IPU_AON** block remains alive even when IPU is in D3 power state. This means:

- IPU_AON handles PHY ownership arbitration even when IPU main logic is powered down
- Camera ownership state persists through IPU D3 transitions
- PHY ownership arbitration continues to function through IPU_AON even when IPU main logic is powered down

### Camera Types

Three camera types are supported in the E2E architecture:

| Camera Type | Interface | PHY | Ownership Arbitration |
|------------|-----------|-----|----------------------|
| **MIPI CSI-2** | C-PHY or D-PHY | Shared CDPHY between IPU and NVU | SIO communication between IPU and NVU |
| **USB RAW** | USB (via XHCI_CAM) | Dedicated USB PHY | SIO communication between IPU and NVU |
| **USB Legacy** | USB (via XHCI_CAM) | Dedicated USB PHY | Offloaded via IPU hosted stack |

### Camera Ownership Arbitration Protocol

Ownership arbitration uses the following signals/registers:

| Signal/Register | Description |
|----------------|-------------|
| `CDPHY_OWNER` | PHY ownership flag: indicates which IP currently owns the MIPI CDPHY |
| `USB_CAM_OWNER` | USB camera ownership flag: indicates which IP currently owns USB camera |
| `ipu_claim` | IPU's claim request for camera ownership |
| `nvu_claim` | NVU's claim request for camera ownership |
| `nvu_release_claim_irq` | IRQ to NVU indicating it must release ownership |

#### MIPI Ownership — Case 1: IPU Boots First

1. IPU boots and claims CDPHY via `ipu_claim`
2. IPU_AON sets `CDPHY_OWNER = IPU`
3. NVU boots later, sends `nvu_claim`
4. IPU_AON sees both claims, IPU has priority → NVU snoops PPI bus
5. IPU releases claim → `CDPHY_OWNER` transitions to NVU
6. NVU receives `nvu_ownership_change_irq`, takes direct PHY control

#### MIPI Ownership — Case 2: NVU Boots First

1. NVU boots and claims CDPHY via `nvu_claim`
2. IPU_AON sets `CDPHY_OWNER = NVU`
3. NVU configures PHY and starts camera streaming
4. IPU boots later, sends `ipu_claim`
5. IPU_AON sends `nvu_release_claim_irq` to NVU
6. NVU releases claim → `CDPHY_OWNER` transitions to IPU
7. NVU transitions to PPI snoop mode (passive data reception)

#### USB Ownership Arbitration

USB camera ownership follows the same pattern using `USB_CAM_OWNER` flag, with the additional XHCI_CAM involvement:

| Register | Description |
|----------|-------------|
| `XHCI.ENUM_STATE` | USB device enumeration state: `0x0` = not enumerated, `0x1` = enumerated |

USB camera initialization requires XHCI_CAM to enumerate the USB device first (`XHCI.ENUM_STATE = 0x1`) before NVU or IPU can claim streaming ownership.

#### USB Enumeration Sub-Steps (E2E HAS v0.1)

USB device enumeration (performed by either IPU or NVU via XHCI_CAM) includes the following sub-steps:

1. **Read port connection status change** — detect USB camera attachment
2. **Assign port number** — allocate a port for the device
3. **Assign address** — assign USB device address
4. **Set EP Mapping Table** — configure endpoint routing
5. **Set SIO Pin Mapping** — configure SIO pin assignments for streaming

> **NVU Can Enumerate USB Devices (E2E HAS v0.1, Case 2)**: When NVU boots before IPU, NVU FW can independently enumerate USB devices via XHCI_CAM using the same `Get Register` / `Set Register` SIO commands. NVU reads `XHCI.ENUM_STATE`, and if `= 0x0` (not enumerated), NVU initiates enumeration through XHCI_CAM. This enables NVU to start sensing without waiting for IPU to boot.

### FW2FW Communication over SIO

IPU and NVU firmware communicate over SIO using camera configuration commands (e.g., Set MIPI Camera Config, Set USB Raw Camera Config) sent from IPU to NVU. Parameters exchanged include:

| Parameter | Description |
|-----------|-------------|
| Camera Resolution | Width x Height |
| Bit Depth | Bits per pixel |
| Frame Rate | Frames per second |
| Virtual Channel (VC) | MIPI CSI-2 virtual channel ID |
| CCPAL/Bypass Mode | UVC payload processing mode |
| SIO HIR Pin Config | MPS (SIO Credit Packet Size), PM (SIO Credit Packets per Service Interval), DPS (Data Payload Size per Service Interval) |

### MIPI Streaming and Handoff Flow

When camera ownership is handed from IPU to NVU (or vice versa):

1. Owning IP signals intent to release via ownership protocol
2. Camera sensor streaming is paused (or kept running in snoop mode)
3. PHY ownership transitions via SIO communication between IPU and NVU
4. New owner configures CSI-2 HC for active reception
5. FW2FW communication establishes camera parameters (resolution, format, frame rate)
6. New owner starts active streaming

> **PMode Switch**: For MIPI Camera, NVU and IPU share I2C/I3C pins for controlling the camera sensor. NVU FW is responsible for switching the PADMODE to select between IPU or NVU.

> **Open Review**: The state of "IPU is busy and NVU cannot acquire ownership" might last for a long duration, during which NVU sensing might be disabled (reviewer comment [hhan10]).

### USB Streaming and Handoff Flow

USB camera streaming involves SIO Link Logic and XHCI_CAM coordination:

| Flag/Register | Purpose |
|--------------|---------|
| `SEN` | Stream Enable — enables isochronous streaming |
| `SBUSY` | Stream Busy — indicates active streaming in progress |
| `LLEN` | Link Logic Enable — enables SIO link logic for data routing |

USB streaming handoff sequence:
1. XHCI_CAM enumerates USB camera (`XHCI.ENUM_STATE = 0x1`)
2. Owning IP issues **ConfigureEndpoint** to set up isochronous endpoints
3. **InterfaceRequest** with Alt Settings selects the ISOCH EP configuration
4. **Space Credits** are allocated for streaming buffer management
5. `SEN` is set to start isochronous data flow
6. Data routes through SIO Link Logic (`LLEN` enabled) via HIR→DIR path
7. For handoff: `SEN` cleared, ownership transferred, new owner re-configures endpoints

#### SIO HIR/DIR Pin Routing Details (E2E HAS v0.1)

The SIO data routing within NVU uses **HIR (Host Isochronous Receive)** and **DIR (Device Isochronous Receive)** pins:

- **Link Logic** processes **Space Credit** requests from IPU (the stream consumer)
- **Link Logic** feeds forward data received from XHCI over the **Host Rx SIO pin** to IPU via the **Device Rx SIO pin**
- NVU HW also consumes the streaming data for sensing while forwarding to IPU
- `SEN=1` on the DIR pin enables it to receive Space Credit requests from IPU
- `SEN=1` on the HIR pin to XHCI starts the actual ISOCH streaming

#### Optional Stream-Ready Check (E2E HAS v0.1)

Before starting a stream, the IPU can optionally verify that NVU is ready by issuing a **Get Register** command:

1. IPU sends `Get Register` to query NVU stream-ready status
2. NVU FW responds with stream-ready indication
3. Only then does IPU set `SEN=1` on its SIO_HIR pin to start streaming

This step is marked **optional** in the E2E HAS but is recommended to avoid race conditions during stream setup.

#### Stream Teardown Sequence (E2E HAS v0.1)

When tearing down a USB camera stream, the following sequence ensures clean shutdown:

1. IPU sets `SEN=0` for HIR pin, polls `SBUSY=0` to confirm stream completion
2. IPU sends FW2FW stream-stop command via SIO_HC → SIO_DC to NVU
3. NVU sets `SEN=0` for DIR pin — **when SC (Space Credits) = 0**, the device ISOCH pin stops issuing `dma_req` to NVU HW
4. NVU polls `SBUSY=0` on DIR pin to confirm stream completion
5. NVU sets **`LLEN=0`** to disable link logic — this **breaks the path between HIR and DIR** inside NVU, allowing each pin to be terminated independently
6. NVU sets `SEN=0` for HIR pin, polls `SBUSY=0`
7. NVU sets Alt Setting 0 to terminate ISOCH stream in camera

USB camera also uses **L2 suspend / U0 transitions** during ownership handoff:
- Camera enters L2 suspend when no IP is actively streaming
- Camera transitions to U0 (active) when new owner claims and starts streaming

### FLR Recovery Flows

Function-Level Reset (FLR) recovery is required when an IP block encounters a fatal error:

#### MIPI Camera FLR Recovery
1. Failing IP triggers FLR
2. SIO component receives **ResetPrep** signal
3. SIO sends **ResetPrepAck** when quiesced
4. PHY ownership returns to default (no owner)
5. Surviving IP can re-claim camera ownership
6. Camera sensor may need re-initialization depending on PHY state

> **FLR Detection Heuristic (E2E HAS v0.1)**: NVU FW detects an IPU FLR by observing a `CDPHY_OWNER` change (to NONE) **without** a prior FW2FW stream-close message from IPU. Specifically: HW sends an IRQ to FW on `CDPHY_OWNER` change without `nvu_claim = 1`. NVU FW interprets this as an IPU FLR because it occurred without IPU properly closing the camera stream via FW2FW message. NVU FW then cleans up the MIPI camera pipe by resetting CSI2-HC, ISP, and other pipeline blocks.

#### USB Camera FLR Recovery
1. Failing IP triggers FLR
2. SIO component receives **ResetPrep** / **ResetPrepAck**
3. XHCI_CAM performs **HC Reset** for USB host controller re-initialization
4. USB camera re-enumerates (`XHCI.ENUM_STATE` transitions 0x0 → 0x1)
5. Surviving IP issues **ConfigureEndpoint** + **InterfaceRequest** to restore streaming

> **ResetPrep/Ack Caveat (E2E HAS v0.1)**: `ResetPrepReq/Ack` does **NOT** guarantee that the SIO components connected to IPU are in a clean state — specifically in NVU and XHCI. The surviving IP (NVU) must perform its own SIO cleanup (ResetPrep to its SIO component, then HC Reset to XHCI) before re-establishing the camera streaming path.

> **Open Review**: The E2E HAS v0.1 notes that the NVU FLR/Exception Reset flow is **missing** and needs to be added in a future revision.

### E2E HAS Reference Documents

> Source: VISION SS End-To-End HAS v0.1, Section 2 (Reference Documents). These documents provide supporting detail for the vision subsystem architecture.

| Reference Document | Version | Notes |
|-------------------|---------|-------|
| TitanLake AON DRD | v0.2 | Always-On Design Reference Document |
| Novalake Imaging Requirements | v1 | NVL Imaging PAS |
| Synopsys MIPI C/D PHY Databook | 8.00a_pre3 | MIPI PHY Databook |
| SIO Component HAS | v0.5 | SIO Component architecture |
| SIO Protocol Spec 2.0 | v2.0 | SIO Protocol specification |
| AXIBIU HAS | — | AXI Bus Interface Unit |
| SIP USB GenX xHCI Camera | — | XHCI Camera HAS |
| Camera Offload End-to-End HAS | — | Camera offload E2E flows |
| IPU9 Input System | — | IPU9 input system architecture |
| IPU9 Input System eUSB2V2 and CCPAL/U | — | IPU9 CCPALU and SIO |
| IPU9 Input System MIPI PHY Sharing | — | IPU9 CDPHY sharing |


## MIPI Interface Sub-System

The MIPI subsystem consists of three components: the PHY Sharing/Control Logic, the MIPI CSI-2 Host Controller, and the Altek CVISP. Together they receive camera data from external MIPI sensors, process it through the ISP, and deliver frames to the NVU SRAM for inference.

### PHY Sharing Architecture

The NVU shares 3 CDPHY instances (CDPHY_A, CDPHY_B, CDPHY_C) with the IPU. PHY ownership is arbitrated through dedicated registers in the NVU PHY sharing block.

**Ownership Model**: IPU has priority. When IPU is not actively using a MIPI port, NVU can take control of the C/D-PHY IP for that port. When IPU is active on a PHY, the NVU snoops the PPI (PHY-Protocol Interface) bus. Note that the state of "IPU is busy and NVU cannot acquire ownership" might last for a long duration, during which NVU sensing might be disabled. The XTAL clock to the IPU partition must be requested before any PHY sharing interaction.

#### PHY Sharing Registers

| Register | Description |
|----------|-------------|
| `NVU_claim` | `nvu_claim_A`, `nvu_claim_B`, `nvu_claim_C`: separate claim request outputs for CDPHY_A/B/C respectively. NVU asserts to request ownership. |
| `CDPHY_owner` | 2-bit per PHY: `0`=none, `1`=NVU, `2`=IPU, `3`=both NVU+IPU requesting. Read-only status. |
| `NVU_release_claim_irq` | IRQ when NVU is requested to release a claimed PHY |
| `NVU_ownership_change_irq` | IRQ when PHY ownership changes |
| `NVU_CDPHY_SEL` | Selects which CDPHY is routed to the CSI-2 Host Controller |
| `NVU_PHY_P_CTRL_STS` | Primary PHY control/status |
| `NVU_PHY_S_CTRL_STS` | Secondary PHY control/status |
| `NVU_CLK_CTRL` | Camera clock control: CAM1/2/3_CLK_SEL (source select) and CAM1/2/3_CLK_EN (enable) |
| `NVU_PHY_BG_TRIM` | PHY bandgap trim: `nvu_cdphy_A_bg_trim` (4-bit), `nvu_cdphy_B_bg_trim` (4-bit), `nvu_cdphy_C_bg_trim` (4-bit) — per-PHY bandgap trim codes |

#### PHY Sharing State Machine (Source: HAS SVG — MIPI_SS.vsdx_VGPIO)

The PHY ownership arbitration follows a hardware state machine with the following `CDPHY_owner` encodings:

| `CDPHY_owner` Value | Meaning | Notes |
|---------------------|---------|-------|
| `0x0` | **None** — PHY unclaimed | Both NVU and IPU inactive on this PHY |
| `0x1` | **NVU owns** | NVU has exclusive PHY access |
| `0x2` | **IPU owns** | IPU has exclusive PHY access; NVU can snoop PPI bus |
| `0x3` | **Both requesting** | Contention — IPU has priority; NVU must wait or snoop |

**Claim/Release Handshake Signals (HAS SVG)**:
- `IPU_claim` / `NVU_claim` — ownership request assertions
- `release_claim_irq` — interrupt fired when current owner must release PHY
- `NVU_ownership_change_irq` — interrupt fired on any ownership transition

> **D0ix Exit Latency**: PHY re-acquisition after D0i2 exit takes **~1 ms** (Source: HAS SVG MIPI_SS.vsdx). This latency must be accounted for in camera startup timing.

#### PHY Lane Muxing (Source: HAS SVG — MIPI_SS.vsdx)

The `nvu_cdphy_port_sel[2:0]` register controls which CDPHY instance is routed to the CSI-2 Host Controller:

| `nvu_cdphy_port_sel` | PHY Routed | Configuration |
|----------------------|------------|---------------|
| `0b000` | CDPHY_A | Single port — CSI2_A |
| `0b001` | CDPHY_B | Single port — CSI2_B |
| `0b010` | CDPHY_C | Single port — CSI2_C |
| `0b100` | CDPHY_A + B | **X4 Aggregated mode** — 4 D-PHY lanes across 2 instances |
| `0b101` | CDPHY_A + B + C | **T3 Aggregated mode** — 3 C-PHY trios across 3 instances |

> **Aggregated modes** allow higher bandwidth by combining lanes/trios across multiple CDPHY instances for high-resolution sensors (5MP+).

#### Camera Clock Sources

The `NVU_CLK_CTRL` register controls camera reference clocks via CAM1/2/3_CLK_SEL and CAM1/2/3_CLK_EN:

| Source | Frequency | Notes |
|--------|-----------|-------|
| XTAL | 19.2 MHz | Default camera reference clock. Note: if IPU driver changes this to any other source, it will remain sticky even for NVU operation |
| IMGPLL (19.2 MHz) | 19.2 MHz | Image PLL output |
| RTCPLL (19.2 MHz) | 19.2 MHz | RTC PLL output |
| IMGPLL (24 MHz) | 24 MHz | Image PLL alternate output |

#### PHY APB Clock

The PHY APB interface runs at **50 MHz** (`nvu_func_clk / 8`, where `nvu_func_clk` = 400 MHz).

### Camera Control Interface Sharing (FAS §8, L7800-7950)

NVU's I2C and I3C controllers are multiplexed with platform LPSS controllers for camera sensor control:

| NVU Peripheral | Shared With | Multiplexing | Usage |
|---------------|-------------|--------------|-------|
| I2C0 | LPSS I2C0 | PADMODE switch by NVU FW | Camera sensor 0 control |
| I2C1 | LPSS I2C1 | PADMODE switch by NVU FW | Camera sensor 1 control |
| I3C0 | LPSS I3C0 | PADMODE switch by NVU FW | Camera sensor (I3C mode) |

> **PMode Switching**: When camera ownership transfers between IPU and NVU, the GPIO pad mode (PADMODE) must be switched to route I2C/I3C signals to the correct IP. NVU FW is responsible for switching the PADMODE to select between IPU or NVU. **Tx must be disabled before PMode switch** to prevent electrical glitches on the bus.

### Wake GPIOs for PHY Sharing (FAS §8, L7850)

Three dedicated claim signals support PHY sharing:

| Signal | Direction | Description |
|--------|-----------|-------------|
| nvu_claim_A | output | NVU claiming ownership for PHY_A |
| nvu_claim_B | output | NVU claiming ownership for PHY_B |
| nvu_claim_C | output | NVU claiming ownership for PHY_C |

These signals allow NVU to claim control of the corresponding C/D-PHY instance when IPU is not actively using a MIPI port.

### MIPI CSI-2 Host Controller

The NVU integrates a **Synopsys DWC_mipi_csi2** host controller supporting combo C-PHY + D-PHY operation.

| Parameter | Value | Notes |
|-----------|-------|-------|
| IP | CSI2HC (Synopsys DWC_mipi_csi2) | Combo PHY host controller |
| D-PHY Lanes | Up to 4 lanes | Per CDPHY instance |
| D-PHY Max Rate | 2.5 Gbps/lane | Per-lane data rate |
| C-PHY Trios | Up to 3 trios | Per CDPHY instance |
| C-PHY Max Rate | 2.5 GSps/trio | Per-trio symbol rate |
| IPI FIFO Depth | 4096 | Internal data buffering (unconfirmed) |
| Data Formats | RAW8, RAW10, RAW12, RAW14 | Bayer/RGBIR/Mono sensor data |
| D-PHY Virtual Channels | Up to 16 VCs | Per CSI-2 link (Integration HAS v0.8) |
| C-PHY Virtual Channels | Up to 16 VCs | Per CSI-2 link (Integration HAS v0.8) |

#### CSI2 HC Internal Architecture (Source: HAS SVG — MIPI_SS.vsdx)

The CSI-2 Host Controller contains the following sub-blocks in the receive pipeline:

```
  C/D-PHY (PPI Bus)
       │
       ▼
  ┌──────────────────┐
  │ PPI Adaptation   │  PHY-Protocol Interface — lane alignment, word boundary
  │ + Pattern Gen    │  Built-in pattern generator for BIST (bypass PHY)
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ De-Skew          │  Lane-to-lane skew compensation for multi-lane configs
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Descrambler      │  CSI-2 v2.0+ scrambling removal (C-PHY mandatory)
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Packet Analyzer  │  CSI-2 packet header parsing, VC/DT extraction, ECC check
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ IDI              │  Internal Data Interface — protocol-to-data conversion
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ IPI              │  Internal Pixel Interface — pixel-level output to Altek ISP
  │ (FIFO=4096)      │  4096-deep FIFO for buffering
  └──────────────────┘
```

> **Signal names (HAS SVG)**: `pixclk`, `ipi_hsync`, `ipi_vsync`, `ipi_pixen`, `ipi_pixdata`, `ipi_data_end`, `ipi_data_valid` — these are the IPI interface signals from the CSI2 HC to the CVISP.

#### VPX2 Interrupts (MIPI)

| VPX2 IRQ | Vector Offset | Description |
|-----------|--------------|-------------|
| IRQ 93 | `0x174` | ALTEK ISP IRQ |
| IRQ 94 | `0x178` | PHY SHARING IRQ |
| IRQ 95 | `0x17C` | CSI2 HC IRQ |

### Altek CVISP (Image Signal Processor)

The Altek CVISP provides on-die ISP capabilities for camera frame processing before inference:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Input Format | 10-bit RAW | RGBIR, Bayer, or Mono |
| Output Formats | Y8, NV12, YUYV, RGB | Configurable output |
| Max Resolution (RGB) | 16MP @ 30fps | Sensing + Host mode |
| Max Resolution (RGB-IR) | 5MP @ 30fps | Sensing + Host mode |
| Max Output Resolution | VGA | Output to NVU SRAM |
| Processing Pipeline | 3 PPC @ 200 MHz | 3 pixels per clock |
| Statistics | AE, AWB, AFD | Auto-exposure, auto-white-balance, flicker detection |
| Motion Detection | SOP (Sum of Pixel) | Firmware-triggered |
| Frame Rate Control | Yes | Configurable frame skip |

#### CVISP Pipeline Partition (FAS §8, L8200-8400)

The CVISP is partitioned into two processing domains:

| Partition | Function | Use Case |
|-----------|----------|----------|
| **PD1** | Sum-of-Pixel (SoP) | Motion detection only — minimal power, runs before full pipeline |
| **PD2** | Full ISP pipeline | Complete image processing: Bayer Re-mosaic → Bayer Scaling → LSC → BLC → Demosaic → AE/AWB/AFD → Gamma → Output |

#### CVISP Processing Blocks (FAS §8, L8250-8350)

| Block | Description |
|-------|-------------|
| **SoP** | Motion detection — separates R/Gr/Gb/B channels, accumulates pixel values, and compares current vs. previous frame summary values; raises an interrupt to trigger PD2 wakeup |
| **Bayer Scaler** | Downscales Bayer input (up to 16MP → output resolution) |
| **RGB-IR Remosaic** | 4×4 pattern remosaic for RGBIR sensors — separates IR channel from RGB |
| **BLC** | Black Level Correction — removes sensor dark current offset |
| **LSC** | Lens Shading Correction — compensates for vignetting |
| **AE** | Auto-Exposure statistics — histogram and region-based metering |
| **AWB** | Auto-White Balance statistics — color temperature estimation |
| **AFD** | Anti-Flicker Detection — detects 50/60Hz light flicker |
| **Gamma** | Gamma correction — 32 LUT tables configurable by FW |
| **RAW Dump** | Raw frame capture to SRAM — bypasses ISP for debug/calibration |
| **DMA Arbiter** | Arbitrates SRAM write access between CVISP output, RAW dump, and stats DMA |
| **SIF** | Sensor Input Formatter — aligns incoming Bayer data from CSI2 HC IPI interface |
| **PGGEN** | Pattern Generator — generates test patterns (color bars, ramps) for CVISP BIST |
| **Frame Rate Control** | Configurable frame skip — processes every Nth frame to reduce power |
| **RLB** | Row Line Buffer — line-based buffering for 2D ISP operations (demosaic, LSC) |
| **HWIRPLite** | Hardware IR Processing Lite — lightweight IR channel separation for RGBIR sensors |

#### Camera Configuration Service API (FAS SVG — Camera_Configuration_Service)

The FW Camera Configuration Service exposes APIs for host-side camera initialization and ISP tuning:

| API Function | Description |
|-------------|-------------|
| `nvu_ae_init()` | Initialize Auto-Exposure engine — sets metering mode, target brightness, convergence speed |
| `nvu_awb_init()` | Initialize Auto-White Balance — sets color temperature range, grey-world coefficients |
| `nvu_afd_init()` | Initialize Anti-Flicker Detection — configures 50/60 Hz detection threshold |
| `nvu_isp_config()` | Configure full ISP pipeline — resolution, Bayer order, output format (Y8/RGB) |
| `nvu_sensor_config()` | Configure sensor parameters — exposure time, gain, frame rate, test pattern |

> **Source**: FAS Camera Configuration Service diagram. API parameters use `uint32_t` types for register-width alignment. Note: Altek provides a SW library that uses the statistics data to run algorithms that fine-tune the exposure, white balance, and anti-flicker operation.

#### CVISP Full Pipeline (Source: HAS SVG — MIPI_SS.vsdx_cvisp)

```
  CSI2 HC IPI Output
       │
       ▼
  ┌─────────┐   ┌─────────┐   ┌──────────────┐   ┌────────────┐
  │  SIF    │──▶│ PGGEN   │──▶│ Frame Rate   │──▶│ SoP (PD1)  │
  │ (Input) │   │ (BIST)  │   │ Control      │   │ Motion Det │
  └─────────┘   └─────────┘   └──────────────┘   └─────┬──────┘
                                                        │ (PD2 wakeup trigger)
       ┌────────────────────────────────────────────────┘
       ▼
  ┌──────────┐   ┌─────────┐   ┌──────────────┐   ┌─────────┐
  │ RGB-IR   │──▶│ Bayer   │──▶│ LSC + BLC    │──▶│  RLB    │
  │ Remosaic │   │ Scaler  │   │ (Correction) │   │ (Lines) │
  └──────────┘   └─────────┘   └──────────────┘   └────┬────┘
                                                        │
       ┌────────────────────────────────────────────────┘
       ▼
  ┌──────────┐   ┌─────────┐   ┌──────────────┐   ┌──────────┐
  │HWIRPLite │──▶│ AE/AWB/ │──▶│   Gamma      │──▶│ DMA      │
  │ (IR Sep) │   │ AFD     │   │ (32 LUTs)    │   │ Arbiter  │──▶ SRAM
  └──────────┘   │ (Stats) │   └──────────────┘   └──────────┘
                 └─────────┘
```

#### ISP Bayer Pattern Support (Source: HAS SVG — MIPI_SS.vsdx)

| Pattern Type | Layout | Sensor Examples |
|-------------|--------|-----------------|
| **RGGB** | R-G / G-B | Most common Bayer pattern |
| **BGGR** | B-G / G-R | OmniVision sensors |
| **GBRG** | G-B / R-G | Some Sony sensors |
| **GRBG** | G-R / B-G | Some Samsung sensors |
| **RGB-IR (BGRG_GIGI)** | B-G-R-G / G-I-G-I | 4×4 RGBIR pattern with IR pixels |
| **RGB-IR (variants)** | Multiple 4×4 patterns | RGBIR sensor-specific layouts |

> **Extended RGB-IR Bayer Patterns** (Source: HAS SVG — `isp_input_pattern`): RGBIR sensors use 4×4 super-pixel repeat patterns. Three documented variants:
> - `BGRG_GIGI_RGBG_GIGI` — B-G-R-G / G-I-G-I / R-G-B-G / G-I-G-I (default RGBIR layout)
> - `GRGB_IGIG_GBGR_IGIG` — G-R-G-B / I-G-I-G / G-B-G-R / I-G-I-G (row-shifted variant)
> - `RGBG_GIGI_BGRG_GIGI` — R-G-B-G / G-I-G-I / B-G-R-G / G-I-G-I (column-shifted variant)
>
> Each pattern determines how the HWIRPLite block separates IR pixels from visible RGB pixels during de-mosaicing.

> **RGB-IR Processing**: RGBIR sensors embed IR pixels in a 4×4 repeat pattern. The **HWIRPLite** block separates IR from visible channels, and the **RGB-IR Remosaic** block reconstructs a standard Bayer pattern from the remaining RGB pixels.

#### CVISP Output POR (FAS §8, L8400-8450)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Output format (POR) | **Y8** (8-bit grayscale) | Optimized for NN inference input |
| Output resolution (POR) | **320×240** or **320×180** | QVGA or 16:9 variant |
| Square conversion | Pad to **320×320** | Padding value = **128** (mid-gray) |

> **Square Conversion**: Face detection models require square input. CVISP pads the shorter dimension with value 128 to create a 320×320 frame. The padding region is excluded from inference ROI.

### MIPI Camera Resolution Support

| Resolution | Pixels | D-PHY Lanes | C-PHY Trios | Formats |
|------------|--------|-------------|-------------|---------|
| QVGA | 320x240 | 1 | 1 | RAW8-14 |
| VGA | 640x480 | 1 | 1 | RAW8-14 |
| 720p | 1280x720 | 1-2 | 1 | RAW8-14 |
| 1080p | 1920x1080 | 2 | 1-2 | RAW8-14 |
| 2MP | 1200x1600 | 1 | 1 | RAW8(1L/1T), RAW10(1L/1T), RAW12(1L/1T), RAW14(1L/1T) |
| 3MP | 2048x1536 | 1 | 1 | RAW8(1L/1T), RAW10(1L/1T), RAW12(1L/1T), RAW14(1L/1T) |
| 5MP | 2592x1944 | 2-4 | 2-3 | RAW8-14 |
| 8MP | 3840x2160 | 1-2 | 1 | RAW8(1L/1T), RAW10(2L/1T), RAW12(2L/1T), RAW14(2L/1T) |
| 12MP | 4000x3000 | 2-3 | 1-2 | RAW8(2L/1T), RAW10(2L/1T), RAW12(2L/1T), RAW14(3L/2T) |
| 16MP | 4904x3263 | 2-4 | 1-2 | RAW8(2L/1T), RAW10(3L/1T), RAW12(3L/2T), RAW14(4L/2T) |

### MIPI Power Targets

| Use Case | Target Power | Frame Rate | Notes |
|----------|-------------|------------|-------|
| User Presence / Face Detection | 5 mW | 3 fps | Sensing-only mode, VGA 640x480 RAW |
| Sensing + Host (16MP RGB) | Not specified in NVU HAS v1.0 | 30 fps | Full pipeline |
| Sensing + Host (5MP RGB-IR) | Not specified in NVU HAS v1.0 | 30 fps | Full pipeline |


## Camera Working Modes (FAS §8, L8500-8600)

NVU supports three camera working modes that define how IPU and NVU share camera resources:

| Mode | IPU State | NVU State | S0ix Limit | Description |
|------|-----------|-----------|------------|-------------|
| **IPU Exclusive** | Active (owns PHY) | Inactive or snooping | No limit | IPU has full camera control; NVU is either disabled or enabled but not actively using the camera |
| **NVU Exclusive** | Not using camera | Active (owns PHY) | **S0i2.0 max** | NVU has full camera control; platform cannot enter deeper than S0i2.0 |
| **Concurrent** | Active (owns PHY) | Active (snooping) | **S0** | Both IPs active; IPU owns camera sensor, RGB stream is tunneled to NVU |

> **S0ix Constraint**: When NVU is actively sensing (NVU Exclusive or Concurrent mode), the platform is limited to **S0i2.0** — it cannot enter S0i2.1 or S0i2.2 because NVU requires VNN power and camera clocks.


## USB Interface Sub-System

The USB subsystem provides a separate camera input path for USB cameras (UVC class devices). It consists of the USB Video Offload Logic (UVOL), MJPEG decoder/post-processing, and SIO component for peer-to-peer data transfer between NVU, XHCI, and IPU.

> **USB Isochronous Bandwidth (Integration HAS v0.8)**: The USB camera path supports up to **52 KB per 125 μs** microframe (USB 2.0 high-speed isochronous bandwidth limit). This translates to **416,000 KB/s** (52 KB × 8000 microframes/sec) = **416 MB/s** (decimal, 10^6) or **~397 MiB/s** (binary, 2^20) for camera streaming via the SIO peer-to-peer interface.

### USB Video Offload Logic (UVOL)

The UVOL processes USB video data through a multi-stage pipeline:

```
  USB Camera (UVC)
       │
       ▼
 ┌─────────────┐
 │ SIO (7 pins) │  Peer-to-peer NVU ↔ XHCI ↔ IPU
 └──────┬──────┘
        │
        ▼
 ┌──────────────┐
 │ USB           │  Strips USB transport headers
 │ De-packetizer │
 └──────┬───────┘
        │
        ▼
 ┌──────────────┐
 │ RAW Link     │  Raw video data handling
 │ Logic        │
 └──────┬───────┘
        │
        ▼
 ┌──────────────┐
 │ DMA          │  4-channel DMA controller
 │ (SNPS based) │  Moves data between SIO FIFO and NVU SRAM
 └──────┬───────┘
        │
        ▼
  NVU SRAM (for inference)
```

### USB Ownership Arbitration

Unlike MIPI PHY sharing which uses hardware claim registers (nvu_claim_A/B/C), the USB camera interface handles ownership arbitration between NVU and IPU at the firmware level via SIO communication:

- For USB RAW cameras, IPU and NVU communicate over SIO and perform ownership switching directly in FW.
- For USB Legacy cameras, when offloaded to NVU, IPU and NVU communicate over SIO for ownership management.
- When the camera is exclusively used by IPU, NVU must wait until IPU relinquishes ownership.

### MJPEG Decoder

The NVU integrates a **Verisilicon VC9000NanoD** MJPEG decoder for hardware-accelerated JPEG decompression of USB camera streams:

| Parameter | Value | Notes |
|-----------|-------|-------|
| IP | Verisilicon VC9000NanoD | Hardware MJPEG decoder |
| Clock Frequency | 562.5 MHz | Engine clock to meet 4K@30fps decode requirement |
| Max Decode | 4K MJPEG @ 30fps | At 562.5 MHz pixel clock |
| Input | MJPEG compressed stream | From USB UVC camera |
| Output | Decompressed YUV frame data | Post-processing (typically down-scaling) |

#### MJPEG Decoder Pipeline (Source: HAS SVG — USB_SS.vsdx)

```
  MJPEG Compressed Stream
         │
         ▼
  ┌─────────────────┐   ┌───────────────┐   ┌────────────────┐
  │ Entropy Decode   │──▶│ RLC Decode    │──▶│ AC/DC          │
  │ (Huffman tables) │   │ (Run-Length)  │   │ Prediction     │
  └─────────────────┘   └───────────────┘   └───────┬────────┘
                                                     │
         ┌───────────────────────────────────────────┘
         ▼
  ┌─────────────────┐                                          
  │ Inverse         │                                          
  │ Transform (DCT) │                                          
  └────────┬────────┘                                          
           │                                                   
           ▼                                                   
  ┌─────────────────┐        ┌─────────────────────────────────┐
  │ YUV Reconstruct │──▶     │ Post-Processor (PP Engine)      │
  │                 │        │  ┌─────────┐  ┌──────────────┐  │
  └─────────────────┘        │  │ Scaling  │─▶│ RGB Convert  │  │
                             │  └─────────┘  └──────┬───────┘  │
                             │  ┌──────────┐  ┌─────▼────────┐ │
                             │  │ Dithering│◀─│ De-Interlace │ │
                             │  └────┬─────┘  └──────────────┘ │
                             │  ┌────▼─────────┐  ┌──────────┐ │
                             │  │Alpha Blending│─▶│ Rotation │ │
                             │  └──────────────┘  └──────────┘ │
                             └─────────────────────────────────┘
```

> **Post-Processor**: After JPEG decompression, the PP Engine performs optional scaling, colorspace conversion (YUV→RGB), de-interlacing, alpha blending, dithering, and rotation. These are configured per-frame via PP registers.

### SIO Component

The SIO (Sideband I/O) component enables peer-to-peer data transfer:

| Parameter | Value | Notes |
|-----------|-------|-------|
| SIO Pins | 11 | Dedicated SIO interface |
| Data Path | NVU ↔ XHCI ↔ IPU | Peer-to-peer, bypasses main NoC |
| USB Line Rate | Up to 5 Gb/s | eUSB2V2 line rate |

#### SIO Internal Architecture (HAS Section 8.8)

The SIO subsystem consists of several sub-blocks that process USB camera data:

| Sub-Block | Function |
|-----------|----------|
| **Frame Counter** | Tracks USB frame boundaries and maintains frame numbering for isochronous transfers |
| **FIFO** | Buffering between SIO pin interface and internal logic; absorbs clock domain crossing jitter |
| **De-Packetizer (DPTZR)** | Extracts camera payload from USB packets; strips USB protocol headers |
| **Circular Buffer (CBUF)** | Ring buffer for camera frame data staging before DMA to SRAM/DRAM |
| **Link Logic (LL)** | Manages SIO link-level handshake and flow control with XHCI |
| **MSIF2IPI** | Media SIO Interface to IPI bridge — converts SIO protocol to internal pixel interface |
| **SIODMA** | Dedicated 4-channel DMA engine for SIO data movement (registers at `0xF412_0000`, 4KB) |

> **Data flow**: SIO Pins → FIFO → De-Packetizer → Circular Buffer → SIODMA → SRAM/DRAM. The Frame Counter provides timing reference for isochronous scheduling.

##### SIO Configuration Registers (Source: HAS SVGs — `SIO_Host_Config_Flow`, `SIO_Device_Config_Flow`, `SIO_Host_ISOCH_Rx_Flow`)

Host and device configuration flows use these key SIO control/status registers:

| Register / Abbreviation | Context | Function |
|--------------------------|---------|----------|
| **NVU_SIO** | Host Config | Top-level SIO controller — master enable, mode select, clock config |
| **SIOC** | ISOCH Rx | SIO Controller — manages isochronous receive scheduling and handshake |
| **SIO_ICP** | Host Config | SIO Interrupt Control/Pending — interrupt enable and status for SIO events |
| **SIO_IC_DC** | Device Config | SIO IC Device Configuration — device-side I2C/control interface config for USB camera |
| **SIO_SCTL_HIR** | ISOCH Rx | SIO Stream Control Host ISOCH Rx — configures host-side isochronous receive stream parameters (packet size, interval, endpoint) |

> **Configuration sequence**: NVU FW first configures `NVU_SIO` (master enable + clock), then sets `SIO_IC_DC` for device-side control, then programs `SIO_SCTL_HIR` for isochronous stream parameters, and finally enables `SIOC` to start streaming. `SIO_ICP` provides interrupt feedback throughout.

##### De-Packetizer (DPKTZR) Internal Architecture (Source: HAS SVG `USB_SS.vsdx_SIO_BLOCK_DIAGRAM`)

The DPKTZR extracts camera payload from USB packets through a multi-stage pipeline:

```
SIO Pin Data → PackingFSM → Header Removal → Burst Buffers → DMA FSM → CBUF
                    ↓              ↓              ↓
              Error Checker   SOSI Detect    Frame Counter
                    ↓              ↓
              EOF Detection   Signal Gen
```

| Sub-Block | Function |
|-----------|----------|
| **PackingFSM** | Packs incoming SIO pin data into aligned words for downstream processing |
| **Header Removal** | Strips USB protocol headers (setup/data/status TRB overhead) |
| **Burst Buffers** | Absorbs burst-mode data from SIO pins; provides steady output to DMA |
| **DMA FSM** | Controls DMA requests to write de-packetized data to Circular Buffer |
| **Error Checker** | Validates packet CRC, sequence numbers; flags corrupted frames |
| **SOSI Detect** | Start-of-Stream / Start-of-Image detection for frame boundary identification |
| **EOF Detection** | End-of-Frame detection — triggers frame-complete interrupt |
| **Frame Counter** | Maintains per-stream frame count for isochronous scheduling |

**Stopping the Streams (Sensing Mode)**: In sensing mode, DMA channels 3/4 (DPKTZR to SIO DMA, multi-block transfer with `DMAX_CH3/4_MULTI_BLK_EN = 1`) are terminated by signalling `dma_last`. |

**Key signals** (Source: HAS SVG):
- `hst_rx_dma_req` / `hst_rx_dma_ack` / `hst_rx_dma_rdata` — Host Rx DMA handshake
- `fifo_dma_req` / `fifo_dma_ack` — FIFO-to-DPKTZR DMA handshake
- `dpktzr_dma_rdata` — De-packetized data output to CBUF

##### Circular Buffer (CBUF) Registers (Source: HAS SVG `USB_SS.vsdx_CBUF`)

The CBUF provides ring-buffer staging for camera frame data between DPKTZR output and SIODMA:

| Register | Function |
|----------|----------|
| **CBUF_CTRL** | Circular Buffer Control Register — includes CBUF_EN (bit 0, enable/disable) |
| **CBUF_BASE_ADDR** | Base address of the circular buffer in SRAM |
| **CBUF_SIZE** | Size of the circular buffer (must be power-of-2 aligned) |
| **CBUF_THRESHOLD** | Threshold for DMA trigger — when fill level exceeds threshold, SIODMA is requested |
| **CBUF_WR_PTR** | Write pointer — updated by DPKTZR on each write |
| **CBUF_RD_PTR** | Read pointer — updated by SIODMA on each read |
| **CBUF_WRAP** | Wrap counter — incremented when WR_PTR wraps around |

```
DPKTZR → [BUF-0][BUF-1][BUF-2][BUF-3] → SIODMA
          ↑ WR_PTR              ↑ RD_PTR
          ←────── CBUF_SIZE ──────→
```

> **Buffer overrun**: If `CBUF_WR_PTR` catches `CBUF_RD_PTR` (write overtakes read), frame data is lost. The CBUF IRQ (IRQ 105) fires on overrun condition.

##### Link Logic (LL) Details (Source: HAS SVG `USB_SS.vsdx_Link_Logic`)

Link Logic manages the SIO data path routing between NVU, IPU, and XHCI_CAM:

| Signal/Control | Function |
|----------------|----------|
| **LL_EN** | Link Logic master enable — gates all SIO data routing |
| **SETCLR** | Set/Clear control for link state transitions |
| **Last** | Indicates last data beat in a transfer |
| **Fin** | Indicates final transfer in a sequence (stream teardown) |
| **USB_RAW** | Selects RAW camera path (bypass MJPEG, route via MSIF2IPI to CVISP) |

Data routing based on `USB_RAW` mode:
- `USB_RAW=0` (non-RAW/MJPEG): UDF ← DPKTZR data → MJPEG Decoder → PP Engine → output
- `USB_RAW=1` (RAW camera): UDF ← DPKTZR data → MSIF2IPI → CVISP ISP pipeline

##### MSIF2IPI Bridge Internal Architecture (Source: HAS SVG `USB_SS.vsdx_MSIF2IPI`)

The MSIF2IPI (Media SIO Interface to IPI) converts SIO protocol data to the internal pixel interface used by CVISP:

```
SIO Data → VC Filter → Timing Block → DataFormatter → Pixel Buffer → IPI Output
                         (HSA/HBP/HSD)
```

| Sub-Block | Function |
|-----------|----------|
| **VC Filter** | Filters data by Virtual Channel ID — selects which VC to pass through |
| **Timing Block** | Generates MIPI-compatible timing signals (HSA = Horizontal Sync Active, HBP = Horizontal Back Porch, HSD = Horizontal Sync Data) |
| **DataFormatter** | Reformats SIO data words into pixel-aligned format matching CVISP input requirements |
| **Pixel Buffer** | Buffers formatted pixels to smooth data delivery to IPI interface |

**IPI Output signals**: `ipi_hsync`, `ipi_vsync`, `ipi_pixen`, `ipi_pixdata[47:0]`, `ipi_data_valid[2:0]`

##### UVOL Pin Mapping (Source: HAS SVG `USB_SS.vsdx_UVOL_PIN_MAP`)

The UVOL module maps SIO pins to specific USB camera functions:

| Pin # | Function | Direction | Description |
|-------|----------|-----------|-------------|
| PIN#0 | Host Config | Bidirectional | ICP configuration channel between NVU and XHCI_CAM |
| PIN#1 | Host INTR | NVU ← XHCI_CAM | Interrupt notification from XHCI_CAM to NVU |
| PIN#2 | Host EP0 Tx | NVU → XHCI_CAM | Control endpoint Tx (USB EP0 OUT) |
| PIN#3 | Host EP0 Rx | NVU ← XHCI_CAM | Control endpoint Rx (USB EP0 IN) |
| PIN#4 | Host ISOCH Rx | NVU ← XHCI_CAM | Isochronous camera data Rx (primary stream) |
| PIN#5 | Host ISOCH Rx2 | NVU ← XHCI_CAM | Isochronous camera data Rx (secondary stream) |
| PIN#6 | Host ISOCH Rx3 | NVU ← XHCI_CAM | Isochronous camera data Rx (tertiary stream) |
| PIN#7 | Device Config | Bidirectional | Device-side configuration (for IPU-hosted mode) |
| PIN#8 | Device ISOCH | Bidirectional | Device-side isochronous data (IPU-hosted mode) |
| PIN#9 | Device ISOCH2 | Bidirectional | Device-side isochronous data (IPU-hosted mode) |
| PIN#10 | Device ISOCH3 | Bidirectional | Device-side isochronous data (IPU-hosted mode) |

**SIO DMA Channel Mapping** (Source: HAS SVG):

| DMA Channel | Assigned Pins | Direction | Usage |
|-------------|--------------|-----------|-------|
| CH1 | Pin#2, Pin#6 | Tx | Host EP0 Tx + ISOCH Rx3 |
| CH2 | Pin#4, Pin#5, Pin#6 | Rx | Host ISOCH Rx streams |
| CH3 | Pin#7 | Bidirectional | Device Config |
| CH4 | Spare | — | Reserved for future use |

**UVOL Internal Signal Names** (Source: HAS SVG):
- Host path: `hst_rxff_rdata/wdata`, `hst_tx_dp_*` — Host Rx FIFO and Tx datapath
- Device path: `dev_rxff_rdata/wdata`, `dev_rx_dp_*` — Device Rx FIFO and datapath
- AXI masters: `AXI-M1` (Host data path), `AXI-M2` (Device data path)
- Config: `UVOL_INIT` → IOSF2AXI S1 Port, `UVOL_CFG` → APB configuration

##### MFINDEX Counter & Frame Sync (Source: HAS SVG `USB_SS.vsdx_Frame_Sync`)

The MFINDEX (Microframe Index) counter provides frame-level synchronization between NVU and XHCI_CAM:

- NVU reads MFINDEX via SIO `Get XHC HH Timestamp (0x82)` command
- Counter runs at USB SOF rate (125μs microframes for USB 2.0, 1ms frames for USB 1.1)
- **ISOCH scheduling**: Frame Counter uses MFINDEX to determine correct Service Interval boundaries
- **DRS (Data Rate Selection)**: Configurable MCO (Max Concurrent Outstanding) = 7 per default, with adjustable SI (Service Interval) and packet size

##### USB-IF Power Flow (Source: HAS SVG `USB_SS.vsdx_USB_Power`)

USB camera power management flow for NVU USB-IF subsystem:

| Step | Actor | Action |
|------|-------|--------|
| 1 | FW | Initiates L2 suspend on USB-IF power domain |
| 2 | NVU HW | Asserts `PEER_OWN_REQ` to XHCI_CAM |
| 3 | XHCI_CAM | Responds with `PEER_OWN_ACK` |
| 4 | NVU HW | Reads `TCG` and `IPAPG` register status |
| 5 | NVU HW | Deasserts `usb_func_clk_req` → USB functional clock stops |
| 6 | NVU HW | USB-IF enters clock-gated state |
| — | — | **Wake path** (no HW wake for USB_IF PD — HPET timer only): |
| 7 | HPET Timer | Fires at programmed interval |
| 8 | NVU HW | Asserts `usb_func_clk_req` → USB functional clock resumes |
| 9 | NVU HW | Deasserts `PEER_OWN_REQ` → ownership returned |

> **⚠️ No HW wake for USB-IF**: Unlike MIPI-IF (which has GPIO wake), the USB-IF power domain has **no hardware wake source**. Wake is only via **HPET timer**. This means USB camera cannot wake NVU from deep sleep — FW must pre-program HPET for periodic wake intervals.

#### SIO P2P Communication Protocol (FAS §8, L9500-10200)

SIO uses **PCIe Vendor-Defined Messages (VDMs)** for peer-to-peer command/control between NVU, IPU, and XHCI_CAM:

| Parameter | Value |
|-----------|-------|
| Transport | PCIe VDMs (Vendor-Defined Messages) |
| VendorID | `0x8086` (Intel) |
| VendorMsgCode | `0x46` |

##### IPU → NVU SIO Commands

| Code | Command | Description |
|------|---------|-------------|
| `0x01` | Set MIPI Camera Config | Configure MIPI camera parameters (resolution, format, lanes) |
| `0x02` | Set USB Raw Camera Config | Configure USB RAW camera parameters |
| `0x03` | Set FPS Config | Configure target frame rate |
| `0x04` | Set Exposure Config | Configure camera exposure settings |
| `0x05` | Stop Camera Stream | Halt camera streaming |

##### NVU → XHCI_CAM SIO Commands

| Code | Command | Description |
|------|---------|-------------|
| `0x80` | Get Pin EP Table Entry | Read endpoint pin table entry from XHCI_CAM |
| `0x81` | Set Pin EP Table Entry | Write endpoint pin table entry to XHCI_CAM |
| `0x82` | Get XHC HH Timestamp | Read Hammock Harbor timestamp from XHCI_CAM |
| `0x83` | XHC Command | Issue xHCI command TRB to XHCI_CAM |
| `0x84` | Set Register | Write XHCI_CAM register |
| `0x85` | Get Register | Read XHCI_CAM register |

##### XHC Command TRBs via SIO (FAS §8, L10800-11000)

The `XHC Command (0x83)` SIO message wraps standard xHCI command TRBs:

| TRB Type | Code | Description |
|----------|------|-------------|
| Enable Slot | 9 | Allocate device slot in XHCI_CAM |
| Disable Slot | 10 | Free device slot |
| Address Device | 11 | Assign USB address to camera device |
| Configure Endpoint | 12 | Configure isochronous endpoint for streaming |
| Reset Endpoint | 14 | Reset stalled endpoint |
| Stop Endpoint | 15 | Stop endpoint for power management |
| Reset Device | 17 | Full USB device reset |

##### Frame Counter Synchronization (FAS §8, L10500-10600)

> **⚠️ Clock Mismatch**: XHCI_CAM uses **XTAL = 19.2 MHz** while NVU uses **XTAL = 38.4 MHz**. Frame counter synchronization must account for this 2:1 clock ratio. The Hammock Harbor timestamp (`Get XHC HH Timestamp` command `0x82`) provides a common time reference.

#### UVOL Fabric Architecture (HAS Section 8.8)

The **UVOL (USB Video Offload Logic)** fabric sits between the SIO subsystem and the NVU main NoC:

| Parameter | Value |
|-----------|-------|
| Register Base | `0xF410_0000` (1MB) |
| Initiator ID on NoC | 0x6 (UVOL) |
| Function | Routes USB camera data from SIO De-Packetizer/CBUF to SRAM or DRAM via NoC |
| Data Width | 16 bytes |
| Max BW | 3.2 GB/s |
| Outstanding Transactions | 4 |

The UVOL fabric provides address translation and arbitration for USB camera data, ensuring ordered delivery to the target memory (SRAM for real-time processing or DRAM for buffered streaming). It operates as a NOC initiator alongside the main DMA engine.

#### VPX2 Interrupts (USB)

| VPX2 IRQ | Vector Offset | Description |
|-----------|--------------|-------------|
| IRQ 99 | `0x18C` | SIO IRQ |
| IRQ 100 | `0x190` | DPTZR (De-packetizer) IRQ |
| IRQ 101 | `0x194` | SIODMA IRQ |
| IRQ 102 | `0x198` | UDF_UAL IRQ |
| IRQ 103 | `0x19C` | MSIF2IPI IRQ |
| IRQ 104 | `0x1A0` | MJPEG IRQ |
| IRQ 105 | `0x1A4` | CBUF (Circular Buffer) IRQ |
| IRQ 106 | `0x1A8` | LL (Link Logic) IRQ |

### USB Camera Format Support

| Use Case | Formats | Resolution | Frame Rate | Notes |
|----------|---------|------------|------------|-------|
| Sensing Only | RAW | VGA / QVGA | 3 fps | Low-power always-on |
| Sensing + Host | MJPEG, YUY2 | Up to 4K / 1080p | 30 fps | Full pipeline |

### USB Power Targets

| Use Case | Target Power | Frame Rate | Notes |
|----------|-------------|------------|-------|
| User Presence / Face Detection | 8 mW | 3 fps | Sensing-only mode, VGA/QVGA |
| Sensing + Host (4K MJPEG) | Not specified in NVU HAS v1.0 | 30 fps | Full pipeline with MJPEG decode |


## Memory Map

Camera/sensor interface blocks occupy the following address ranges within the NVU memory map:

### MIPI Sub-System

| Block | Base Address | End Address | Size | Description |
|-------|-------------|-------------|------|-------------|
| ALTEK_ISP | `0xF7000000` | `0xF7080000` | 512 KB | Altek CVISP registers |
| PHY_CFG | `0xF7100000` | `0xF7101000` | 4 KB | PHY sharing/configuration registers |
| EXT_PHY | `0xF7200000` | `0xF7210000` | 64 KB | External PHY (CDPHY) registers |
| CSI2_HC | `0xF7300000` | `0xF7301000` | 4 KB | CSI-2 Host Controller registers |

### USB Sub-System

| Block | Base Address | End Address | Size | Description |
|-------|-------------|-------------|------|-------------|
| MJPEG_DEC | `0xF4000000` | `0xF4001000` | 4 KB | MJPEG Decoder registers |
| UVOL_CFG | `0xF4100000` | `0xF4104000` | 64 KB | USB Video Offload Logic registers |


## Power Domains

The camera subsystems are in separate power domains with independent PGCB (Power Gate Control Block) power gating:

| Power Domain | Subsystem | Contents |
|-------------|-----------|----------|
| PAR_MIPI | MIPI_SS | PHY sharing logic, CSI-2 HC, Altek CVISP |
| PAR_USB | USB_SS | UVOL, MJPEG decoder, SIO, circular buffer |

Each domain can be independently power-gated when not in use. The VPX2 firmware manages power domain transitions via PMC sideband messaging.

> **Privacy LED (Integration HAS v0.8)**: NVU does **not** control the privacy LED. Privacy LED control is outside the NVU IP scope and is handled by the SoC platform (e.g., GPIO-driven by host driver or EC).


## Use Case Power and Frame Rate Targets (Integration HAS v0.8, Section 7)

> Source: SIP NVU1.0 Integration HAS v0.8, Section 7 (Functional Description). These are system-level use case targets; actual power depends on camera type, resolution, and datapath.

| Use Case | Target Power | Frame Rate | Notes |
|----------|-------------|------------|-------|
| Wake on Approach | 5 mW | 3 fps | Low-power proximity detection |
| Walk Away Lock | — | — | Presence timeout detection |
| Adaptive Dimming | 5 mW | — | Display brightness adjustment based on user presence |
| Face ID | 15 mW | 5 fps | Face authentication |
| Face Orientation | 5 mW | 3 fps | Head pose / orientation detection (Integration HAS v0.8) |
| Multiple Face Detection | 10 mW | 3 fps | Multi-face detection in frame (Integration HAS v0.8) |
| cALS (Camera Ambient Light Sensing) | 5 mW | 5 fps | Camera-based ambient light measurement (Integration HAS v0.8) |
| Face Enrollment | 15 mW | 5 fps | New face registration for authentication (Integration HAS v0.8) |
| Gesture | 5–50 mW | 15–30 fps | Hand/body gesture recognition (power varies with algorithm complexity) |
| Depth Sensing | 20 mW | 30 fps | Active IR depth mapping |


## PCI Functions (Integration HAS v0.8, Section 7)

> Source: SIP NVU1.0 Integration HAS v0.8, Section 7. NVU exposes two PCI functions for host interaction.

| PCI Function | BAR Size | Internal Remap Address | Description |
|-------------|----------|----------------------|-------------|
| FN0 (NVU Host SW Driver) | 64KB | `0x8000_0000` | Primary host driver interface (HOST_IPC, PEER_IPC, SEC_REG) |
| FN1 | TBD | TBD | Second PCI function — BAR size and purpose not defined in HAS v1.0; BAR1 disable supported (HSD 15018335923) |

> **Note**: The IOSF2AXI bridge strap `nvu_br_strap_mulfndev` is set to 1, indicating a multi-function device configuration. The IOSF2AXI bridge parameter `NUM_PCI_FUNCTIONS=2` and `NUM_BARS=2` supports both functions. FN1 BAR details are not specified in HAS v1.0 — refer to SoC integration documentation.


## Test Scenarios

### MIPI PHY Ownership Claim/Release Test
1. Ensure IPU is inactive (not claiming any CDPHY)
2. Write `NVU_claim` bit 0 = 1 to claim CDPHY_A
3. Read `CDPHY_owner` — verify bits [1:0] = `01` (NVU owns CDPHY_A)
4. Verify `NVU_ownership_change_irq` fires (VPX2 IRQ 94)
5. Release claim by clearing `NVU_claim` bit 0
6. Verify `CDPHY_owner` bits [1:0] = `00` (no owner)

### MIPI PHY Contention Test (IPU Priority)
1. Configure IPU to claim CDPHY_A
2. NVU asserts `nvu_claim_A` output = 1 to also request CDPHY_A
3. Read PHY ownership status — verify IPU retains ownership (IPU has priority)
4. Verify NVU cannot acquire CDPHY_A ownership while IPU is actively using it (NVU ownership request remains pending)
5. IPU releases CDPHY_A
6. Verify NVU acquires ownership of CDPHY_A after IPU releases it

### Camera Clock Configuration Test
1. Write `NVU_CLK_CTRL.CAM1_CLK_SEL` to select XTAL (19.2 MHz)
2. Write `NVU_CLK_CTRL.CAM1_CLK_SEL` to enable the selected clock source
3. Verify camera sensor receives reference clock
4. Switch to IMGPLL 24 MHz source, verify sensor PLL re-locks
5. Set `NVU_CLK_CTRL.CAM1_CLK_SEL` = 0 (XTAL default), verify sensor enters standby

### CSI-2 Frame Reception Test
1. Claim CDPHY_A, configure for D-PHY 2-lane operation
2. Configure CSI-2 HC for RAW10 data reception at VGA resolution
3. Start camera sensor streaming at 3 fps (sensing mode)
4. Wait for CSI-2 HC IRQ (VPX2 IRQ 95) indicating frame reception
5. Verify frame data in NVU SRAM: correct resolution, format, no corruption
6. Check IPI FIFO did not overflow (FIFO depth 4096)

### Altek ISP Pipeline Test
1. Configure CVISP input for 10-bit RAW Bayer
2. Set output format to Y8 (grayscale for inference)
3. Set output resolution to 320x240 or 320x180 (POR configuration for Y8)
4. Stream camera data through CSI-2 HC → CVISP pipeline
5. Verify ISP IRQ fires (VPX2 IRQ 93) per frame
6. Read ISP statistics (AE, AWB, AFD) and verify reasonable values
7. Verify output frame in SRAM matches expected Y8 conversion

### Altek ISP Motion Detection (SOP) Test
1. Configure CVISP with motion detection enabled
2. Stream static scene — verify no motion detection event
3. Introduce scene change (simulated or physical)
4. Verify motion detection interrupt is raised
5. Read motion statistics from ISP

### USB Camera Claim/Release Test
1. Write `NVU_CLAIM` bit 0 = 1 to claim USB camera
2. Read `NVU_USB_CAM_OWNER` — verify = `01` (NVU owns)
3. Verify `NVU_OWNERSHIP_RELEASE_IRQ` fires
4. Release claim, verify owner returns to `00`

### USB MJPEG Decode Test
1. Claim USB camera ownership
2. Configure UVOL pipeline for MJPEG stream reception
3. Send MJPEG VGA @ 3fps stream via USB UVC
4. Verify SIO IRQ (IRQ 99) and DPKTZR IRQ (IRQ 100) for data arrival
5. Verify UDF_UAL strips UVC/CCPAL headers (IRQ 102)
6. Verify MJPEG decoder produces decompressed frame (IRQ 104)
7. Read decompressed frame from SRAM, verify against reference

### USB 4K MJPEG Stress Test
1. Configure for Sensing + Host mode
2. Stream 4K MJPEG @ 30fps via USB
3. Verify MJPEG decoder keeps up at 562.5 MHz pixel clock
4. Monitor circular buffer (IRQ) for overflow
5. Verify decoded frames are correct over sustained period

### MIPI Sensing-Only Power Test
1. Configure MIPI for VGA 640x480 RAW @ 3fps
2. Claim single CDPHY, minimal ISP pipeline
3. Measure NVU MIPI subsystem power consumption
4. Verify NVU MIPI subsystem power consumption (target value not specified in source facts)

### USB Sensing-Only Power Test
1. Configure USB for VGA RAW @ 3fps
2. Claim USB camera, minimal UVOL pipeline
3. Measure NVU USB subsystem power consumption
4. Verify against 8 mW target for user presence detection

### MIPI-to-Inference End-to-End Test
1. Claim CDPHY, configure CSI-2 HC for RAW10 VGA @ 3fps
2. Configure Altek CVISP: RAW10 input → Y8 output → QVGA
3. Verify frames arrive in SRAM via ISP pipeline
4. VPX2 dispatches frame to NPX6-1K for inference (see inference sub-skill)
5. Verify inference result is produced for each camera frame
6. Verify full pipeline latency and frame drop behavior

### USB-to-Inference End-to-End Test
1. Claim USB camera, configure UVOL for MJPEG VGA @ 3fps
2. Verify MJPEG decode → SRAM pipeline
3. VPX2 dispatches decoded frame for inference
4. Verify inference result per frame
5. Measure end-to-end latency: USB reception → decode → inference → result

### Camera Working Mode Transitions (FAS §8)

1. Start in IPU Exclusive mode (IPU owns PHY + I2C)
2. Trigger NVU camera request via SIO Set MIPI Camera Config (0x01)
3. Verify vGPIO handshake completes (release_req → release_ack)
4. Confirm NVU Exclusive mode: NVU_claim=1, IPU_claim=0
5. Verify camera frames arrive at CVISP pipeline
6. Trigger Concurrent mode request
7. Verify both IPU and NVU receive frames simultaneously
8. Return to IPU Exclusive mode via Stop Camera Stream

### SIO Command Protocol Test (FAS §8)

1. Send each IPU→NVU SIO command and verify NVU response
2. Send each NVU→XHCI_CAM command and verify response
3. Verify VDM format per PCIe VDM (Vendor Defined Message) specification
4. Test error handling for invalid command codes
5. Verify Frame Counter Sync between XHCI_CAM and NVU, accounting for different XTAL reference clocks (NVU xtal_clk = 38.4MHz)

### CVISP Pipeline Partition Test (FAS §8)

1. Configure PD1 (SoP only) and verify motion detection output
2. Configure PD2 (full pipeline) and verify complete ISP output
3. Verify output POR format: Y8 @ 320×240 or 320×180
4. Verify square conversion: 320×240 padded to 320×320 (padding value=128)
5. Test RGB-IR Remosaic with 4×4 pattern sensor
6. Verify max supported resolutions: 16MP RGB, 5MP RGBIR


## PythonSV Patterns

Pending PythonSV namespace allocation for NVU IP. The NVU is exposed as a PCI RCiEP (Root Complex Integrated Endpoint) on IOSF. Below are tentative patterns based on HAS register descriptions:

```python
# NVU PythonSV namespace not yet allocated
# NVU is a PCI RCiEP on IOSF, sideband endpoint name: "NVU"
#
# Example patterns (replace with actual paths when available):
#
# import pysvtools.pciedecode as pcie
# nvu = pcie.get_device(bus=0, dev=TBD, func=0)  # PCI function 0: NVU SW Driver
#
# === MIPI PHY Sharing Registers (PHY_CFG @ 0xF7100000) ===
# NVU_claim:                 Bits 0-2 = CDPHY_A/B/C claim request
# CDPHY_owner:               2-bit per PHY (0=none, 1=NVU, 2=IPU, 3=both)
# NVU_release_claim_irq:     PHY release request IRQ
# NVU_ownership_change_irq:  PHY ownership change IRQ
# NVU_CDPHY_SEL:             CDPHY-to-CSI2HC routing select
# NVU_CLK_CTRL:              CAM1/2/3_CLK_SEL, CAM1/2/3_CLK_EN
#   Clock sources: XTAL 19.2MHz, IMGPLL 19.2MHz, RTCPLL 19.2MHz, IMGPLL 24MHz
#
# === CSI-2 Host Controller (CSI2_HC @ 0xF7300000) ===
# Synopsys DWC_mipi_csi2 register set
# IPI FIFO depth: 4096
# Supports RAW8/10/12/14, up to 4 D-PHY lanes or 3 C-PHY trios
#
# === Altek CVISP (ALTEK_ISP @ 0xF7000000) ===
# 10-bit RAW input (RGBIR/Bayer/Mono)
# Output: Y8, NV12, YUYV, RGB
# 3 PPC @ 200 MHz
# Statistics: AE, AWB, AFD
# Motion detection (SOP)
#
# === External PHY (EXT_PHY @ 0xF7200000) ===
# CDPHY_A/B/C configuration
# PHY APB clock: 50 MHz (nvu_func_clk / 8)
#
# === USB Video Offload Logic (UVOL_CFG @ 0xF4100000) ===
# NVU_CLAIM:                   Bit 0 = USB_CAM claim
# NVU_USB_CAM_OWNER:           2-bit (0=none, 1=NVU, 2=IPU, 3=both)
# NVU_RELEASE_CLAIM_IRQ:       USB release request IRQ
# NVU_OWNERSHIP_RELEASE_IRQ:   USB ownership change IRQ
#
# === MJPEG Decoder (MJPEG_DEC @ 0xF4000000) ===
# Verisilicon VC9000NanoD
# 562.5 MHz pixel clock, 4K MJPEG @ 30fps
#
# === VPX2 Interrupt Map (Camera/Sensor) ===
# IRQ 93:  ALTEK ISP IRQ        (0x174)
# IRQ 94:  PHY SHARING IRQ      (0x178)
# IRQ 95:  CSI2 HC IRQ          (0x17C)
# IRQ 99:  SIO IRQ              (0x18C)
# IRQ 100: DPTZR IRQ            (0x190)
# IRQ 101: SIODMA IRQ           (0x194)
# IRQ 102: UDF_UAL IRQ          (0x198)
# IRQ 103: MSIF2IPI IRQ         (0x19C)
# IRQ 104: MJPEG IRQ            (0x1A0)
# IRQ 105: CBUF IRQ             (0x1A4)
# IRQ 106: LL IRQ               (0x1A8)
```


## See Also

- [dma/SKILL.md](../dma/SKILL.md) — SIODMA channels, camera data path
- [inference/SKILL.md](../inference/SKILL.md) — NPX6/VPX2 processing of camera frames
- [registers/SKILL.md](../registers/SKILL.md) — SIO register block, FN1 BAR
- [driver/SKILL.md](../driver/SKILL.md) — Camera driver model, USB enumeration
- [firmware/SKILL.md](../firmware/SKILL.md) — MJPEG Decoder (VC9000NanoD), USB Camera SIO protocol
- [bios/SKILL.md](../bios/SKILL.md) — BIOS camera config tables (ConfigGeneral, MipiConfig, UsbRawConfig), VGPIO handshake, I2C/GPIO BIOS setup, ACPI _DSM
- [platform/SKILL.md](../platform/SKILL.md) — MIPI/USB pin mux, CSI2 config

### Reference Documents

- NVU HAS v1.0 (SIP_NVU_HAS.html) — Sections 5.3, 5.4 (MIPI-IF, USB-IF sub-systems)
- NVU FAS v1.0 §8 (L7617-11128) — Camera/ISP pipeline, PHY sharing, SIO commands, working modes
- Synopsys DW MIPI CSI2 HC v1.54a Databook — CSI-2 host controller details
- Altek CV-ISP Specification — CVISP pipeline blocks, PD1/PD2 partition

## Related Sub-Skills

- [fv-nvu/driver](../driver/SKILL.md) — Host driver interface, PCI enumeration, IPC, FW loading
- [fv-nvu/platform](../platform/SKILL.md) — Platform integration, reset sequences, straps, fuses, BDF


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:23 | Facts added: 560


### Additional HAS Details (2 facts)

#### Clock and Signal Requirements

- **CDPHY Crystal Clock Request/Acknowledge** — The NVU CDPHY interface requires a crystal clock req/ack handshake mechanism. (2 Introduction > 2.5 Requirements, id: 14025520684)

#### Image Signal Processing Integration

- **ISP RAW Format Handling** — The NVU must integrate an Image Signal Processor (ISP) to support handling of RAW image formats. (2 Introduction > 2.5 Requirements, id: 16027428819)


### Camera Interface (367 facts)

### Camera Interface

#### Overview

The Intel NVU (Neural Vision Sensing Unit) provides Always-On (AON) visual sensing functionality associated with MIPI and USB cameras on the platform. (HAS 2.1)

The NVU camera pipeline consists of two primary input paths:

- **MIPI CSI-2 Camera Pipeline**: Shared MIPI CSI-2 Combo (C/D) PHY from the Image Processing Unit (IPU), a MIPI CSI-2 Host Controller, and the CVISP low-power computer vision ISP pipeline (HAS 5.1)
- **USB Camera Pipeline**: USB Depacketizer to depacketize USB packets from a USB camera, an M-JPEG Decoder to decompress Motion JPEG format streams to YUV, and post-processing stages (HAS 5.1)

Standards compliance: MIPI CSI protocols as specified in the CSI-2 Host Controller component document. (HAS 2.3)

---

#### MIPI CSI-2 Camera Interface

### PHY Architecture

The NVU does not include any on-die MIPI CSI-2 D-PHY, C-PHY, or Combo-PHY. Instead, it shares the MIPI CSI-2 C/D-PHY owned by the Image Processing Unit (IPU) in the SoC to connect with MIPI CSI-2 camera sensors. This requires NVU to interact with the IPU Subsystem. (HAS 8.1.1)

The MIPI-IF block includes PHY sharing logic that communicates with the IPU in the SoC to share the MIPI C/D-PHY. The sharing supports the following usage models: (HAS 2.2)

- **IPU owning the camera** — NVU may sniff the PPI interface
- **NVU owning the camera** — NVU takes full control of the C/D-PHY

---

#### PHY Sharing

##### Ownership Modes

- When IPU is **not** actively using a MIPI port, NVU can take control of the C/D-PHY IP for that port and acquire images from the camera sensor to support AON Vision use cases. NVU has a dedicated MIPI CSI-2 Host Controller for this mode. (HAS 8.1.1)
- When IPU is **actively** using a MIPI port, NVU can sniff the PPI interface between the C/D-PHY and IPU's MIPI CSI-2 Host Controller(s). In this case, NVU has the option to downscale images. (HAS 8.1.1)

##### Arbitration Logic

- The Arbitration Logic resides in the IPU power un-gated domain and is shared with NVU. It arbitrates between requests from IPU and NVU to own a specific C/D-PHY. (HAS 8.1.1)
- The Arbitration Logic operates in the **XTAL clock domain**. IPU or NVU shall enable the XTAL clock via the `xtal_clkreq`/`xtal_clkack` handshake with PCG prior to interacting with the Arbitration Logic. (HAS 8.1.1)
- The Arbitration Logic is reset using `host_prim_rst_b`. (HAS 8.1.1)
- The `Soft_reset` register resets the Arbitration Logic and all registers in the power-gated domain; it should be used **only** for unexpected errors. (HAS 8.1.1)

##### Ownership Registers

| Register | Direction | Description |
|---|---|---|
| `IPU_claim` | Written by IPU FW | Asserts IPU's request to own a specific C/D-PHY |
| `NVU_claim` | Written by NVU FW | Asserts NVU's request to own a specific C/D-PHY |
| `CDPHY_owner` | Updated by HW, read by IPU/NVU FW | Indicates current ownership of each C/D-PHY |
| `CDPHY_force_ownership` | TAP override source | `TAP_override` routed to final MUX that determines C/D-PHY assignment |
| `NVU_CDPHY_A/B/C_owner` | Read/written by NVU FW | Interface for FW to select lanes to be used for sensing |

(HAS 8.1.1)

##### Interrupts and Signals

| Signal / Interrupt | Trigger Condition | Description |
|---|---|---|
| `nvu_release_claim_req` | Both `IPU_claim` and `NVU_claim` asserted for the same C/D-PHY | Sent to NVU to request release of NVU_claim so IPU can acquire ownership; wakes and interrupts NVU FW |
| `NVU_release_claim_irq` | `nvu_release_claim_req` asserted | Interrupt delivered to NVU FW |
| `NVU_ownership_release_irq` | `CDPHY_owner` registers change | Interrupt delivered to NVU FW |

(HAS 8.1.1)

##### NVU FW PHY Sharing Responsibilities

- Provide interface (`NVU_CDPHY_A/B/C_owner`) for FW to select lanes to be used for sensing. (HAS 8.1.1)
- Listen on `nvu_release_claim_req` and interrupt FW through `NVU_release_claim_irq` when it is asserted. (HAS 8.1.1)
- Monitor `CDPHY_owner` registers and interrupt FW through `NVU_ownership_release_irq` when they change. (HAS 8.1.1)
- FW shall **enable** the XTAL clock prior to interacting with IPU for PHY sharing. Refer to *XTAL Clock Req/Ack Flows* in NVU HAS. (HAS 8.1.1)
- FW shall **disable** the XTAL clock after putting the PHY to shutdown to allow the Arbitration Logic to enter clock gating. (HAS 8.1.1)

##### PHY Sharing Flows

The following flows are defined in PHY Sharing Flows in NAU HAS: (HAS 8.1.1)

- Flow for IPU to acquire ownership of CDPHY
- Flow for NVU to acquire ownership of CDPHY
- Flow for IPU to relinquish ownership of CDPHY
- Flow for NVU to relinquish ownership of CDPHY

---

#### Camera Control Interface Sharing

- By initial design, camera sensor ownership is based on the PHY sharing handshake between IPU and NVU. (HAS 8.1.2)
- During system boot, NVU may be unable to provide timely acknowledgment if `release_irq` occurs before NVU FW is loaded. (HAS 8.1.2)

---

#### Camera Sensor Control

##### MIPI Camera MCLK (HAS 8.1.3.1)

- MIPI camera sensors require a reference clock (MCLK) for their internal PLL.
- MCLK can be sourced from the SoC or externally.

**SoC-sourced MCLK:**

- Refer to *MIPI Camera MCLK* in NVU HAS for the HW design.
- NVU FW is responsible for controlling the MCLK enable via the HW-provided register. The clock selection from NVU is unused.
- **IMGPLL MCLK Source Constraint**: The SoC defaults to XTAL 19.2 MHz for MCLK. If IPU switches to a different source, the configuration persists during NVU operation. If IMGPLL is selected (to meet jitter requirements), this must be considered during NVU operation.

**Externally-sourced MCLK:**

- If MCLK is sourced from SoC-external, it is up to the OEM to decide the clock source.
- Clock enable control is TBD. *(TODO: To be determined whether NVU will need to control the external MCLK enable and the mechanism if required.)* (HAS 8.1.3.1)

---

#### CSI-2 Host Controller (HAS 8.1.4)

- NVU integrates a MIPI CSI-2 Host Controller from Synopsys: **DesignWare MIPI CSI-2 Host Controller version 1.54a**.
- The module receives image data on the PPI interface from a CSI-2 compliant camera sensor.
- Refer to *MIPI CSI-2 Host Controller Capabilities* in NVU HAS for the full list of HW-supported capabilities.
- Zephyr does not have native CSI-2 host controller driver support. NVU FW defines custom CSI-2 host controller driver APIs to fulfill the functionality. Refer to *NVU CSI-2 Host Controller* documentation for API details.

---

#### Pre-OS MIPI CSI-2 Camera Access (HAS 9.3.1)

- MIPI CSI-2 camera Pre-OS access is straightforward.
- The SoC is configured by default to map MIPI to IPU; therefore, no specific action is required in the NVU boot flow.

---

#### USB Camera Interface

The USB-IF block includes USB Camera Offload Logic to obtain the camera stream from the USB XHCI controller in the SoC. An SIO component allows FW to stream data from XHCI, stream data to IPU, and interact with camera sensor control interfaces. (HAS 2.2)

The USB camera pipeline includes: (HAS 5.1)

- **USB Depacketizer**: Depacketizes USB packets from the USB camera
- **M-JPEG Decoder**: Decompresses Motion JPEG format streams from the USB camera to YUV
- **Post-Processing**: Additional processing stages following decode

---

#### Power KPIs

The following Always-On Vision KPIs are defined for camera use cases. The target is defined as SoC power adder excluding external components such as camera sensors. (HAS 15.1)

| Use Case | Camera Type | KPI Target |
|---|---|---|
| Face Detect on NVU (3 fps) | MIPI Camera | 5 mW (SoC Power Adder to MCS) |
| Face Detect on NVU (3 fps) | USB Camera | 10 mW (SoC Power Adder to MCS) |

**SoC power contributors by pipeline:** (HAS 15.1)

- **MIPI camera pipeline**: C/D PHY, NOC Crux, NVU, and SoC infrastructure
- **USB raw camera pipeline**: eUSB2V1/V2 PHY, XHCI_Cam, NOC Crux, NVU, and SoC infrastructure

Reference: PCR16027080495 — *[TTL][NVU] Always On Camera KPI Requirement* (HAS 15.1)

**Frame Rate Jitter Requirement:** Face detection in NVU runs at 3 FPS with a target jitter range of **< 15%**, meaning the sampling interval shall be within 333 × 0.85 ~ 333 × 1.15 ms (**283 ms ~ 383 ms**). (HAS 15.3)

---

#### Firmware and Software Architecture

### BSP and Drivers

- BSP device drivers are provided for the MIPI CSI-2 PHY and Host Controller, I/O, CVISP, IPC, and other peripherals. (HAS 6.1)
- The **Configuration Service** interacts with IPU/USB for camera sensor configuration. (HAS 6.1)
- The **AON Vision Framework** uses a WAMR framework to manage Camera and Algorithm applications. (HAS 6.1)

### Camera Application (WASM)

The Camera App is a WASM application with the following characteristics: (HAS 11.6.1, 11.8.3)

- Non-system privilege app that runs as a camera driver
- Can be Intel or third-party
- Can only access camera/ISP APIs exposed from WAMR
- Its output is posted as


### DSP Core (VPX2) (10 facts)

#### 8.1 Interrupts

##### 8.1.1 VPX2 Interrupts

- For ISH, NVU-related unique interrupts are reserved (e.g., ISP, USB related). (HAS 8.1.1)

The following table lists the VPX2 interrupt assignments for ISP and USB modules:

| Index | Module | IRQ Name | IRQ Pin | Address |
|-------|--------|--------------|-----------|---------|
| 94 | ISP | PHY SHARING IRQ | irq94_a | 0x178 |
| 96 | ISP | SPARE0 IRQ | irq96_a | 0x180 |
| 97 | ISP | SPARE1 IRQ | irq97_a | 0x184 |
| 98 | ISP | SPARE2 IRQ | irq98_a | 0x188 |
| 99 | USB | SIO IRQ | irq99_a | 0x18C |
| 101 | USB | SIODMA IRQ | irq101_a | 0x194 |

#### 8.2 Memory Maps

##### 8.2.2 VPX2 Memory Map

The following table describes the VPX2 memory map sub-regions:

| Block | Sub Region | Sub Region Size (KB) | Start Address | End Address |
|-----------|------------|---------------------|---------------|-------------|
| SIO_TARG | SIO_TARG | 1024 | 0xA0000000 | 0xA0100000 |


### GPIO and Pin Mux (21 facts)

#### GPIO and Pin Mux

### Overview

This section describes the GPIO assignments, virtual GPIO (vGPIO) handshake mechanism, and pin mux configuration used by the NVU camera sub-skill for PHY sharing and camera sensor control coordination with the IPU.

---

#### PHY Sharing — Physical GPIO Wake Sources
*(HAS §8.1.1 PHY Sharing)*

The following internal GPIOs are assigned to monitor PHY ownership signals from the IPU and serve as wake sources for the NVU:

| GPIO Pin | Signal | Direction | Purpose |
|----------|--------|-----------|---------|
| GPIO[21] | `nvu_release_claim_req` | Input from IPU | Wake source for NVU release/claim request |
| GPIO[22] | `CDPHY_owner[0]` | Input from IPU | Toggle detect on CDPHY owner bit 0 |
| GPIO[23] | `CDPHY_owner[1]` | Input from IPU | Toggle detect on CDPHY owner bit 1 |

- Connect `nvu_release_claim_req` to an internal GPIO as a wake source; GPIO[21] is assigned to this signal from the IPU. (§8.1.1)
- Connect `CDPHY_owner` bits to internal GPIOs as wake sources; GPIO[22] and GPIO[23] are assigned to `CDPHY_owner[0]` and `CDPHY_owner[1]` respectively from the IPU. (§8.1.1)
- **FW Requirement:** FW shall configure GPIO[22] and GPIO[23] for **dual edge detection**. Refer to *GPIO as Wake from IPU Requesting/Relinquishing PHY* in the NVU HAS for full details. (§8.1.1)

---

#### Camera Control Interface Sharing — Virtual GPIO (vGPIO) Handshake
*(HAS §8.1.2 Camera Control Interface Sharing)*

##### Virtual GPIO Concept

- A **virtual GPIO (vGPIO)** is a logical GPIO implemented entirely on-die, with no corresponding package pin. (§8.1.2)
- The **GPIO Chassis** abstracts the distinction between on-die (virtual) and off-die (physical) GPIOs; the software interface is identical regardless of the underlying implementation. (§8.1.2)
- An **OR gate** is implemented at the SoC level on the NVU input, enabling flexible NVU GPIO connectivity to physical GPIO, virtual GPIO, or both through input signal multiplexing. (§8.1.2)
- Any device SW driver accessing IOs shared with NVU **must coordinate with NVU using virtual GPIO**. (§8.1.2)
- For full requirement details, refer to *PCR16029668165 — [NVU] VGPIOs for IPU Sensor Driver ↔ NVU communication*. (§8.1.2)

##### release_req / release_ack Handshake Protocol

The vGPIO-based handshake provides additional input for camera sensor ownership coordination, supplementing the PHY Sharing handshake. (§8.1.2)

- The Host SW driver implements a `release_req` / `release_ack` handshake with NVU FW over vGPIOs. (§8.1.2)
- **To take ownership**, the Host SW driver shall:
  1. Verify **VGPIOx1 is cleared**
  2. **Set VGPIOx0**
  3. **Wait for VGPIOx1 assertion**, indicating NVU has released the resource (§8.1.2)
- Each `release_req` / `release_ack` pair requires **four vGPIOs**. (§8.1.2)
- HW supports up to **16 vGPIOs**, allowing handshaking with up to **4 device SW drivers** simultaneously. (§8.1.2)

##### vGPIO Pin Set Assignments

For each device, the vGPIOs used for the `release_req` / `release_ack` handshake shall be selected from one of the following sets. (§8.1.2)

| Set | GPIO Mode Pins | Native Function Mode Pins |
|-----|----------------|--------------------------|
| Set 0 | vGPIOx0, vGPIOx1 | vGPIOx8, vGPIOx9 |
| Set 1 | vGPIOx2, vGPIOx3 | vGPIOx10, vGPIOx11 |
| Set 2 | vGPIOx4, vGPIOx5 | vGPIOx12, vGPIOx13 |
| Set 3 | vGPIOx6, vGPIOx7 | vGPIOx14, vGPIOx15 |

---

#### MIPI Camera Sensor Control via GPIO
*(HAS §8.1.3.3 MIPI Camera Control via GPIO)*

- GPIO pins used for camera sensor control are **not controlled by the NVU GPIO controller**; they are driven by the **SoC GPIO controller**. (§8.1.3.3)
- GPIO-related settings — including community, group, pad, function, initial value, and active value — are **configured in BIOS** and queried by the NVU SW driver during OS boot, along with other camera configurations. (§8.1.3.3)
- When NVU holds camera sensor ownership, **NVU FW may drive the Tx of these pins** by programming the corresponding pad register in the SoC GPIO controller via **IOSF-SB**. (§8.1.3.3)
- **NVU FW shall not modify any other pad registers** beyond those required for the specific camera sensor control pins it owns. (§8.1.3.3)
- For HW design details, refer to *MIPI Camera GPIO Sharing with IPU* in the NVU HAS. (§8.1.3.3)


### IOSF Bridge (89 facts)

#### IOSF Bridge — `nvu_VOD_IPC_IOSF_SideBand_Mem` Register Reference

(CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem, MSG B?:D?:F?)

All registers are 32-bit wide and reset via **FUNCRST**.

---

#### Interrupt Control Registers

##### `CIM_VOD` — AGENT Channel Interrupt Mask

**Offset:** `0x0000_0000_1010` | **Size:** 32 bits | **Reset:** FUNCRST

- Controls global interrupt masking for the VOD IPC channel toward NVU firmware.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_MASK | [0] | 0x0 | RW | Global interrupt enable toward FW for the channel. 0 = interrupt unmasked |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved |

---

##### `CIS_VOD` — AGENT Channel Interrupt Status

**Offset:** `0x0000_0000_1014` | **Size:** 32 bits | **Reset:** FUNCRST

- Provides per-channel interrupt status; set when any enabled interrupt source becomes active.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_STATUS | [0] | 0x0 | RO/V | Global interrupt status for FW interrupts on this channel. Set if any enabled interrupt source is active |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved |

---

##### `PISR_VOD2NVU` — Inbound Per-Channel Interrupt Status (AGENT → NVU)

- Interrupt status register for the inbound (VOD-to-NVU) IPC channel.
- To be read by NVU FW only.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| AGENT2NVU_DB | [0] | 0x0 | RO/V | AGENT2NVU Inbound Message Interrupt Status. 1 = DOORBELL BUSY interrupt is active |
| RESERVED1 | [26:1] | 0x0000000 | RO | Reserved |
| AGENT2NVU_BCISC | [27] | 0x0 | RW/1C/V | AGENT2NVU inbound message busy clear interrupt status. Write 1 to clear the interrupt status |
| RESERVED0 | [31:28] | 0x0 | RO | Reserved |

---

##### `PISR_NVU2VOD` — Outbound Per-Channel Interrupt Status (NVU → AGENT)

- Interrupt status register for the outbound (NVU-to-VOD) IPC channel.
- To be read by AGENT only.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| NVU2AGENT_DB | [0] | 0x0 | RO/V | NVU2AGENT Outbound message interrupt status. 1 = DOORBELL Busy Set interrupt is active |
| RESERVED1 | [7:1] | 0x00 | RO | Reserved |
| AGENT2NVU_BC | [8] | 0x0 | RW/1C/V | AGENT2NVU busy clear interrupt status bit. 1 = NVU FW has cleared the AGENT2NVU Doorbell |
| RESERVED0 | [31:9] | 0x000000 | RO | Reserved |

---

#### Doorbell Registers

##### `VOD2NVU_DOORBELL_VOD` — Inbound Doorbell (AGENT → NVU)

**Offset:** `0x0000_0000_1048` | **Size:** 32 bits | **Reset:** FUNCRST

- Inbound doorbell register used by the AGENT core to interrupt NVU.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |

---

##### `NVU2VOD_DOORBELL_VOD` — Outbound Doorbell (NVU → AGENT)

**Offset:** `0x0000_0000_1054` | **Size:** 32 bits | **Reset:** FUNCRST

- Outbound doorbell register used by NVU to interrupt AGENT.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |
| BUSY | [31] | 0x0 | RW | When cleared, the AGENT CPU is ready to accept a new message |

---

#### Inter-Processor Message Registers

##### `NVU2VOD_MSG0_VOD` — Outbound IPC Message (NVU → AGENT)

**Offset:** `0x0000_0000_1060` | **Size:** 32 bits | **Reset:** FUNCRST

- Inter-process message register for NVU core to AGENT communication.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| MSG | [31:0] | 0x00000000 | RW | Message from NVU to AGENT |

---

##### `VOD2NVU_MSGn_VOD` — Inbound IPC Messages (AGENT → NVU), MSG0–MSG29

**Reset:** FUNCRST (all registers) | **Size:** 32 bits each

- Inter-process message registers for AGENT to NVU communication.
- All registers contain a single 32-bit `MSG` field `[31:0]`, Access: RW, Reset: `0x00000000`.
- Message from AGENT to NVU.

| Register | Offset |
|---|---|
| VOD2NVU_MSG0_VOD | `0x0000_0000_10E0` |
| VOD2NVU_MSG1_VOD | `0x0000_0000_10E4` |
| VOD2NVU_MSG2_VOD | `0x0000_0000_10E8` |
| VOD2NVU_MSG3_VOD | `0x0000_0000_10EC` |
| VOD2NVU_MSG4_VOD | `0x0000_0000_10F0` |
| VOD2NVU_MSG5_VOD | `0x0000_0000_10F4` |
| VOD2NVU_MSG6_VOD | `0x0000_0000_10F8` |
| VOD2NVU_MSG7_VOD | `0x0000_0000_10FC` |
| VOD2NVU_MSG8_VOD | `0x0000_0000_1100` |
| VOD2NVU_MSG9_VOD | `0x0000_0000_1104` |
| VOD2NVU_MSG10_VOD | `0x0000_0000_1108` |
| VOD2NVU_MSG11_VOD | `0x0000_0000_110C` |
| VOD2NVU_MSG12_VOD | `0x0000_0000_1110` |
| VOD2NVU_MSG13_VOD | `0x0000_0000_1114` |
| VOD2NVU_MSG14_VOD | `0x0000_0000_1118` |
| VOD2NVU_MSG15_VOD | `0x0000_0000_111C` |
| VOD2NVU_MSG16_VOD | `0x0000_0000_1120` |
| VOD2NVU_MSG17_VOD | `0x0000_0000_1124` |
| VOD2NVU_MSG18_VOD | `0x0000_0000_1128` |
| VOD2NVU_MSG19_VOD | `0x0000_0000_112C` |
| VOD2NVU_MSG20_VOD | `0x0000_0000_1130` |
| VOD2NVU_MSG21_VOD | `0x0000_0000_1134` |
| VOD2NVU_MSG22_VOD | `0x0000_0000_1138` |
| VOD2NVU_MSG23_VOD | `0x0000_0000_113C` |
| VOD2NVU_MSG24_VOD | `0x0000_0000_1140` |
| VOD2NVU_MSG25_VOD | `0x0000_0000_1144` |
| VOD2NVU_MSG26_VOD | `0x0000_0000_1148` |
| VOD2NVU_MSG27_VOD | `0x0000_0000_114C` |
| VOD2NVU_MSG28_VOD | `0x0000_0000_1150` |
| VOD2NVU_MSG29_VOD | `0x0000_0000_1154` |


### Interrupt Configuration (6 facts)

#### RAW Data Type Codes — MSIF2IPI

(HAS §8.8.2.1.2.8 MSIF2IPI)

The MSIF2IPI sub-block recognizes the following RAW data type encodings within the range `0x26`–`0x2F`:

| Data Type Code | Format |
|---------------|--------|
| `0x2A` | RAW8 |
| `0x2B` | RAW10 |
| `0x2C` | RAW12 |
| `0x2D` | RAW14 |

- The MSIF2IPI block maps incoming USB video payload data type fields in the range **`0x26`–`0x2F`** to the RAW data category (HAS §8.8.2.1.2.8).
- Individual sub-codes within this range identify specific RAW bit-depth formats: **RAW8** (`0x2A`), **RAW10** (`0x2B`), **RAW12** (`0x2C`), and **RAW14** (`0x2D`) (HAS §8.8.2.1.2.8).

> **Note:** Only the codes explicitly listed above are defined in the HAS. Codes within the `0x26`–`0x2F` range not enumerated here are not described in the available specification facts and should not be assumed to carry defined behavior.


### Neural Network Accelerator (10 facts)

#### Reference Documents

(HAS §2 Reference Documents)

| Reference Document | Version | Link |
|---|---|---|
| TitanLake AON DRD | 0.2 | TTL AON DRD |
| Novalake Imaging Requirements | 1 | NVL Imaging PAS |
| SIO Protocol Spec | 2.0 | SIO Protocol Spec 2.0 |
| AXIBIU Spec | — | AXIBIU HAS |
| IPU9 Input System eUSB2V2 and CCPAL/U | — | IPU9 CCPALU and SIO |
| *(unnamed document)* | 8.00a_pre3 | — |

---

#### Performance – Bandwidth

##### IOSF Primary Interface

(HAS §11.2.1 IOSF Primary Interface)

| Usage | P2P | Ingress/Egress | Direction | Transaction Types | IOSF Channel | Performance Requirement |
|---|---|---|---|---|---|---|
| 2a / 2b / 3a / 3b | Peer Cmd/Bulk to xHCI-cam | Egress | Peer | MWr32 or MsgD | 1 | 0.1 GB/s (Data Streaming) |

##### Fabrics

(HAS §11.2.2 Fabrics)

| Initiator | Usage | Max Bandwidth |
|---|---|---|
| SIODMA | DPKTZR → SRAM | 1.6 GB/s |

---

#### Register: VOD2NVU_DOORBELL_VOD

(HAS §CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem — MSG B?:D?:F?)

##### Field Definitions

| Name | Bit(s) | Reset | Access | Description |
|---|---|---|---|---|
| BUSY | [31] | 0x0 | RW | AGENT will set this bit to indicate a new message has been written in the payload registers. This bit will be cleared by FW once it has processed the message. |

- The `BUSY` bit acts as a handshake mechanism between the VOD agent and NVU firmware.
- The agent (VOD) sets `BUSY = 1` upon writing a new message into the associated payload registers.
- NVU firmware is responsible for clearing `BUSY` to `0` after consuming the message.


### Peripheral Interfaces (28 facts)

#### 8.1.2 Camera Control Interface Sharing

##### Overview

For MIPI camera sensor operation, control interfaces including I2C/I3C and GPIO are used for camera sensor control. (HAS 8.1.2)

NVU includes I2C/I3C for camera control as part of its MIPI camera pipeline capabilities. (HAS 2.5.1.4)

---

##### I2C/I3C Interface Multiplexing

- NVU I2C0/I2C1/I3C0 is multiplexed with LPSS I2C0/I2C1/I3C0 respectively. (HAS 8.1.2)
- NVU FW controls the pad mode (PMode) of these pins between LPSS and NVU based on camera sensor ownership. (HAS 8.1.2)
- FW switches PMode between NVU and LPSS by programming the corresponding pad register in the SoC GPIO controller through IOSF-SB. (HAS 8.1.3.2)
- MIPI cameras support I2C target interface for programming; some modern cameras use I3C instead of I2C. (HAS 8.7.2.1.7.2)
- The I2C/I3C interface of the camera must be available to both NVU and IPU based on ownership. IPU uses any of the LPSS 6×I2C/4×I3C via driver-to-driver communication between the IPU SW driver and the LPSS I2C driver. (HAS 8.7.2.1.7.2)
- I2C/I3C related settings (bus, slave address, speed, function) are configured in BIOS and queried by the NVU SW driver during OS boot, along with other camera configurations. These settings are subsequently used by NVU FW at runtime. (HAS 8.1.3.2)

> **RVP/OEM HW Design Notice:** For TTL-H, to enable NVU-based lower power vision sensing, the MIPI UF RGB camera sensor shall be connected to LPSS I2C0/I2C1/I3C0, which is multiplexed with NVU I2C0/I2C1/I3C0. (HAS 8.1.2)

---

##### I2C/I3C Bus Allocation Guidelines and Limitations

- The I2C/I3C bus shared with NVU to control the User Facing (UF) RGB camera **should not** be connected to other devices. (HAS 8.1.2)
- A dedicated I2C/I3C bus shall be allocated for the UF RGB camera that NVU uses. (HAS 8.1.2)

**Known limitations when other cameras/devices share the same I2C/I3C bus with NVU:**

- Any I2C/I3C access by SW shall communicate with NVU to coordinate ownership of the shared IOs. (HAS 8.1.2)
- Since Camera Sensor SW driver needs sensor access without IPU, and OEM might connect multiple cameras/flash devices to a single I2C/I3C bus, an additional virtual GPIO-based handshake (req/ack) mechanism is required. (HAS 8.1.2)
- The IPU sensor driver controls the I2C and GPIO connected to MIPI cameras, but does not have a SW interface to talk to the IPU camera driver; therefore the release/claim/owner handshake cannot be used as this handshake is controlled by the IPU camera driver. (HAS 8.21.5)

---

##### Virtual GPIO-Based I2C/I3C Ownership Handshake

- A virtual GPIO-based I2C/I3C ownership handshake mechanism is defined to coordinate bus ownership between NVU FW and host software. (HAS 8.1.2)
- Since there is a fixed connection in SoC HW for vGPIO in GPIO mode and vGPIO in Native FN mode, for each device sharing the I2C/I3C with NVU, BIOS only needs to configure the vGPIOs in GPIO mode. (HAS 8.1.2)
- When a release request is received from either IPU (via PHY Sharing) or host software (via vGPIO), NVU FW shall: (HAS 8.1.2)
  - Close and power off the UF RGB camera sensor
  - Release I2C/I3C ownership
  - Assert acknowledgment as soon as possible
- To handle cases where NVU FW does not respond, the Camera Sensor driver can implement a timer mechanism: after asserting `release_req`, the driver may proceed with direct I2C access upon timeout. The default I2C ownership post-boot is LPSS. (HAS 8.1.2)
- During runtime operation (post-NVU FW loading), if NVU FW hangs when `release_irq` arrives, NVU BUP during the exception reset shall check the current I2C/I3C ownership and release it if still held by NVU. (HAS 8.1.2)

> For full HW design details refer to: *GPIO as Wake for sensor driver requesting/relinquishing shared I2C GPIO* in the NVU HAS. (HAS 8.1.2, 8.21.5)

---

##### GPIO Interface

- Up to 8 GPIOs can be allocated as ad-hoc functional output pins for sensor reset, power control, and similar functions. (HAS 8.1.2)
- There is no multiplexer for GPIO between NVU and LPSS; these pins are directly managed. (HAS 8.1.2)
- BIOS shall put GPIO pins into the Host Group and lock down the pad configuration. I2C/I3C pins shall be configured to Grp4 with the default pad mode set to LPSS/IPU. (HAS 5.1.1.1)

---

##### NVU FW PMode Switching Flow

- NVU FW is responsible for changing the GPIO PMode to switch I2C/I3C ownership between NVU and LPSS by programming the SoC GPIO controller via IOSF-SB. (HAS 8.7.2.1.7.2, 8.1.3.2)
- An open review item exists regarding whether the pad mode of camera I2C on initialization step-12 should be switched by NVU FW rather than IPU FW. (HAS 5.1.1.1)

> **Note:** The requirement to support I3C Secondary master interface for sensing per MIPI I3C 1.1 specification (id: 15017822588) has been **rejected**. (HAS 2.5)


### Power States (2 facts)

#### D0i1 – Trunk Level Clock Gating

*(HAS: 13 Power Management > 13.7 Power Management Flows > 13.7.4 D0i1 - Trunk Level Clock Gating > 13.7.4.2 D0i1 Exit Flow)*

- D0i1 is the trunk-level clock gating power state applicable to the MAIN PD and USB and MIPI PD.
- This state defines the D0i1 entry and exit flow for the MAIN PD and USB and MIPI PD.


### SRAM and Memory (15 facts)

#### IPC IOSF Sideband Memory Registers (`nvu_VOD_IPC_IOSF_SideBand_Mem`)

All registers in this block are reset by `FUNCRST` and are 32 bits wide.

---

#### Peripheral Interrupt Status — Inbound (PISR_VOD2NVU)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PISR_VOD2NVU | 0x1000 | 32 bits | — | Peripheral Interrupt Status – IRQ to NVU. Contains inbound interrupt status bits. (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem > PISR_VOD2NVU) |

---

#### Peripheral Interrupt Mask — Inbound (PIMR_VOD2NVU)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PIMR_VOD2NVU | 0x1004 | 32 bits | — | Peripheral Interrupt Mask – IRQ to NVU. Enables or disables inbound interrupts from AGENT. (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem > PIMR_VOD2NVU) |

**Fields:**

| Field Name | Bits | Reset | Access | Description |
|------------|------|-------|--------|-------------|
| AGENT2NVU_DB | [0] | 0x0 | RW | Mask bit for inbound message (AGENT2NVU Doorbell BUSY) interrupt. To be written by NVU FW only. `1` = interrupt unmasked. (CRIF: > PIMR_VOD2NVU > AGENT2NVU_DB) |
| RESERVED2 | [10:1] | 0x000 | RO | Reserved. (CRIF: > PIMR_VOD2NVU > RESERVED2) |
| NVU2AGENT_BC | [11] | 0x0 | RW | Mask bit for NVU2AGENT doorbell busy clear interrupt. To be written by NVU FW only. `1` = interrupt unmasked. (CRIF: > PIMR_VOD2NVU > NVU2AGENT_BC) |
| RESERVED1 | [26:12] | 0x0000 | RO | Reserved. (CRIF: > PIMR_VOD2NVU > RESERVED1) |
| AGENT2NVU_BCISC | [27] | 0x0 | RW | Mask bit for AGENT2NVU Busy Clear Interrupt Status Clear interrupt. To be written by NVU FW only. `1` = interrupt unmasked. (CRIF: > PIMR_VOD2NVU > AGENT2NVU_BCISC) |
| RESERVED0 | [31:28] | 0x0 | RO | Reserved. (CRIF: > PIMR_VOD2NVU > RESERVED0) |

- All RW fields are to be written by NVU firmware only.
- A value of `1` in any RW mask field indicates the corresponding interrupt is unmasked (enabled).

---

#### Peripheral Interrupt Mask — Outbound (PIMR_NVU2VOD)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PIMR_NVU2VOD | 0x1008 | 32 bits | — | Peripheral Interrupt Mask – IRQ to AGENT. Enables or disables outbound interrupts from NVU. (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem > PIMR_NVU2VOD) |

**Fields:**

| Field Name | Bits | Reset | Access | Description |
|------------|------|-------|--------|-------------|
| NVU2AGENT_DB | [0] | 0x0 | RW | Mask bit for NVU2AGENT Doorbell BUSY Set. To be written by AGENT only. `1` = interrupt unmasked. (CRIF: > PIMR_NVU2VOD > NVU2AGENT_DB) |
| RESERVED1 | [7:1] | 0x00 | RO | Reserved. (CRIF: > PIMR_NVU2VOD > RESERVED1) |
| AGENT2NVU_BC | [8] | 0x0 | RW | Mask bit for AGENT2NVU Busy Clear Interrupt. To be written by AGENT only. `1` = interrupt unmasked. (CRIF: > PIMR_NVU2VOD > AGENT2NVU_BC) |
| RESERVED0 | [31:9] | 0x000000 | RO | Reserved. (CRIF: > PIMR_NVU2VOD > RESERVED0) |

- All RW fields in this register are to be written by AGENT only.
- A value of `1` in any RW mask field indicates the corresponding interrupt is unmasked (enabled).

---

#### Peripheral Interrupt Status — Outbound (PISR_NVU2VOD)

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| PISR_NVU2VOD | 0x100C | 32 bits | — | Peripheral Interrupt Status – IRQ to AGENT. Contains outbound interrupt status bits. (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem > PISR_NVU2VOD) |

---

#### IPC Message Field (VOD2NVU_MSG6_VOD)

| Field Name | Bits | Reset | Access | Description |
|------------|------|-------|--------|-------------|
| MSG | [31:0] | 0x00000000 | RW | Message payload from AGENT to NVU. (CRIF: nvu_VOD_IPC_IOSF_SideBand_Mem > VOD2NVU_MSG6_VOD > MSG) |


### Secure Boot (3 facts)

#### Secure Boot — Requirements

> **Note:** The following entries are sourced from HAS section (2 Introduction > 2.5 Requirements).

| ID | Title | Owner | Status |
|---|---|---|---|
| 14025213486 | [TTL][NVU] Support C/D PHY Sharing between NVU and IPU | rchaddha | Rejected |
| 14025520601 | [TTL][IPU][NVU] CDPHY bandgap code sharing to NVU | rchaddha | POR |
| 15017703183 | [TTL][IPU9] CDPHY Sharing with NVU | rchaddha | Rejected |

- **14025213486** — C/D PHY sharing between NVU and IPU is **not planned** (status: rejected) (2 Introduction > 2.5 Requirements)
- **14025520601** — CDPHY bandgap code sharing to NVU is **planned on record** (status: por) (2 Introduction > 2.5 Requirements)
- **15017703183** — CDPHY sharing with NVU in the IPU9 context is **not planned** (status: rejected) (2 Introduction > 2.5 Requirements)


### USB Camera Interface (7 facts)

#### USB Camera Interface

##### Overview

The NVU USB Camera Interface supports streaming video input from USB-attached cameras, including MJPEG and YUV encoded streams, with integrated decode and post-processing capabilities.

- MJPEG and YUV decode and post-processing support is planned as a future capability (2 Introduction > 2.5 Requirements, id: 16027428785)

---

##### Performance Requirements

- The NVU must be capable of processing **4K resolution MJPEG at 30fps**, which translates to an operating frequency of **562.5 MHz** on the VC9000NanoD (2 Introduction > 2.6 Performance)

---

##### Memory Map

The MJPEG decoder is mapped within the VPX2 memory space as follows (8 IP-Specific Description > 8.2 Memory Maps > 8.2.2 VPX2 Memory Map):

| Block | Sub Region | Size (KB) | Start Address | End Address |
|---|---|---|---|---|
| MJPEG_DEC | MJPEG_DEC | 4 | 0xF4000000 | 0xF4001000 |

---

##### Interrupt Interface

The MJPEG decoder exposes a dedicated interrupt line within the VPX2 interrupt map (8 IP-Specific Description > 8.1 Interrupts > 8.1.1 VPX2 Interrupts):

| Index | Module | IRQ Name | IRQ Pin | Address |
|---|---|---|---|---|
| 104 | USB | MJPEG IRQ | irq104_a | 0x1a0 |

- The **MJPEG IRQ** (`irq104_a`) is asserted by the USB module upon completion of MJPEG-related decode events

---

##### Bandwidth

The USB isochronous data path is managed through the SIO Component fabric (11 Performance > 11.2 Bandwidth > 11.2.2 Fabrics):

| Initiator | Usage | Maximum Bandwidth |
|---|---|---|
| SIO Component | Host ISOCH Rx → Device ISOCH Rx | 1.6 GB/s |

---

##### Reference Documents

The following external document is referenced for the SIO Component specification (2 Reference Documents):

| Document | Version | Reference |
|---|---|---|
| SIO Component HAS | 0.5 | SIO Component HAS |

