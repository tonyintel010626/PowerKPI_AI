name: fv-nvu/driver
description: NVU host driver interface, PCI enumeration, IPC mechanism, firmware loading, and power management hooks

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`) — william.willy.chin@intel.com, Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.
>
> **⚠️ NEVER trust AI 100%.** This skill file is a productivity aid, not a replacement for engineering judgment. AI can hallucinate, confuse similar IPs (e.g., NVU vs NVL/NPU6), or present outdated information as current. **When in doubt, verify with the owner/co-owner or check the authoritative HAS document directly.** For CoDeSign-based HAS verification, see the FV-NVU agent definition (`FV-NVU.md`).

# NVU Host Driver Interface

> **SAFETY**: Do NOT modify PCI configuration space, ATT entries, or IPC registers without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.
> **HAS-First Policy**: Never invent register offsets or hardware behavior. If a value is not in the HAS/FAS extraction, mark it as unverified.

## Overview

The NVU (Neural Vision/Sensing Unit) host driver interface provides the mechanism for the host OS to enumerate, configure, load firmware into, and manage power states of the NVU IP block. The NVU exposes **two PCI functions** (FN0: "NVU Host SW Driver", FN1: "Camera/VOD") on IOSF (`NUM_PCI_FUNCTIONS=2`), though NVU is exposed to the host as a **single-function PCI device**. The host driver is primarily active during NVU boot (firmware loading); after FW loading completes, the driver transitions the device to D3.

Key capabilities:
- PCI enumeration and BAR0 (64KB) configuration via IOSF sideband
- Host-visible register regions: HOST_IPC (4KB), PEER_IPC (28KB), SEC_REG (4KB) via Address Translation Table (ATT)
- IPC mechanism for host-to-NVU communication (32 downstream + 32 upstream payloads)
- Firmware loading sequence (NVU boot, FW download via IOSF Primary Initiator)
- Power management: D0i0 (Active), D0i1 (Light Idle/QREQN handshake), D0i2 (Deep Idle/IPAPG+RET), D3 Hot; PME support in D0 and D3
- Interrupt delivery: Legacy IRQ via IOSF sideband AssertIRQ/DeAssertIRQ or MSI via WIRE2MSI


## PCI Enumeration

The NVU appears as a PCI RCiEP (Root Complex integrated Endpoint) on the IOSF fabric with **two PCI functions** (`NUM_PCI_FUNCTIONS=2`): FN0 ("NVU Host SW Driver") and FN1 ("Camera/VOD").

> **Integration HAS v0.8 update**: The Integration HAS identifies a second PCI function, **FN1 (Camera/VOD)**. The IOSF2AXI bridge parameter `NUM_PCI_FUNCTIONS=2` supports both functions. FN0 itself exposes two BARs: an OS-visible BAR0 of 64KB (NVU2HOST IPC registers) and an OS-invisible BAR1 of 4KB (bridge internal registers). FN1 is the second PCI function exposed by the NVU.

### PCI Functions Summary

| PCI Function | Name | BAR Size | Internal Remap | Description |
|-------------|------|----------|----------------|-------------|
| FN0 — BAR0 | NVU Host SW Driver | 64KB | `0x8000_0000` | OS-visible primary host interface (NVU2HOST IPC registers) |
| FN0 — BAR1 | Bridge Internal | 4KB | — | OS-invisible bridge internal registers |

> **HAS note (Section 22 — Opens)**: FN1 (Camera/VOD) is currently **ZBB'ed** (Zero Bug Bounce) — meaning its feature set is frozen and undergoing final validation. FN1 functionality may be constrained or disabled on early steppings.

### PCI Configuration Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Vendor ID (VID) | `0x8086` | Intel standard (implicit from HAS context) |
| Device ID (DID) | Soft-strap: `nvu_br_strap_deviceid` (16-bit) | HAS soft-strap definition |
| Revision ID | `0x00` (default, `RevisionId0` parameter) | HAS parameter default |
| Multi-function | No (`MultiFunctionDevice` = 0) | HAS parameter default |
| Programming Interface | Soft-strap: `NVU_Reg_prg_intf_func1_SoftStrap` | HAS soft-strap definition |
| Sub-Class Code | Soft-strap: `NVU_SubClass_code_func1_SoftStrap` | HAS soft-strap definition |
| Base-Class Code | Soft-strap: `NVU_BaseClass_code_func1_SoftStrap` | HAS soft-strap definition |
| BAR0 Size | 64KB | HAS Section 8.2.6 |
| BAR0 Internal Remap | `0x8000_0000` | HAS Section 8.2.6 |
| Topology | RCiEP on IOSF | HAS host interface description |

### IOSF Sideband PCI Access

The NVU supports 64KB of private configuration space accessible via IOSF sideband messages:

| Message Type | Description |
|-------------|-------------|
| PCI Register MRd | Memory read to NVU MMIO |
| PCI Register MWr | Memory write to NVU MMIO |
| PCI CfgRd | PCI configuration space read |
| PCI CfgWr | PCI configuration space write |
| Assert PME | Power Management Event assertion |
| Deassert PME | Power Management Event de-assertion |

> **Note**: NVU decodes cycles on IOSF sideband even when D3 bit is set. This allows the host to access PCI config space for power state transitions.


## Host-Visible Register Regions

The NVU FN0 BAR0 (64KB) is divided into three host-visible register regions, mapped through the **Address Translation Table (ATT)**. The ATT translates PCI MMIO BAR addresses to NVU internal addresses.

### ATT Entry Map

| ATT Entry | Region | MMIO Offset Range | Size | NVU Internal Address | Access Type |
|-----------|--------|-------------------|------|---------------------|-------------|
| 0 | HOST_IPC | `0x8000_0000` -- `0x8000_1000` | 4KB | `0xF100_0000` | MMIO |
| 1 | PEER_IPC | `0x8001_0000` -- `0x8001_7000` | 28KB | `0xF110_0000` | PVTCR |
| 2 | SEC_REG | `0x8001_8000` -- `0x8001_9000` | 4KB | `0xF200_0000` | PVTCR |
| 3-7 | SPARE | -- | -- | -- | Invalid |

### HOST_IPC Region (ATT Entry 0)

The HOST_IPC region provides the primary host-to-NVU communication channel. Located at MMIO offset `0x0000`--`0x0FFF` within BAR0 (4KB).

Key registers in HOST_IPC:
- IPC command/status registers
- FWSTS (Firmware Status) registers
- COMM (Communication) registers
- 6 remap registers
- D0i3 support registers (IPC_D0i3=1 — register infrastructure exists but D0i3 power state is **not supported**; see Section 13 constraint below)

> HOST_IPC sync reset source: `FUNCRST`

### PEER_IPC Region (ATT Entry 1)

The PEER_IPC region (28KB) hosts IPC channels to other IP blocks. Each peer IPC channel occupies an independent non-overlapping 4KB MMIO space:

| Peer | Description |
|------|-------------|
| CSE | Converged Security Engine IPC |
| PMC | Power Management Controller IPC |
| CNVI | Connectivity (WiFi/BT) IPC |
| ACE | Audio/Compute Engine IPC |
| ESE | Embedded Security Engine IPC |
| BT | Bluetooth IPC |
| ISH | Integrated Sensor Hub IPC |

Each peer IPC channel is independently secured with SAI-based policy.

### Peer IPC Register Architecture (from HAS SVG)

Each peer IPC channel uses a symmetric doorbell + CSR register pair. Register naming follows the pattern `{SRC}2{DST}_{TYPE}_{PEER}`:

#### ESE IPC Registers

| Register | Direction | Description |
|----------|-----------|-------------|
| `NVU2ESE_DOORBELL_ESE` | NVU → ESE | NVU-to-ESE doorbell (write to send message) |
| `ESE2NVU_DOORBELL_ESE` | ESE → NVU | ESE-to-NVU doorbell (read for incoming message) |
| `ESE2NVU_CSR_ESE` | ESE → NVU | ESE-to-NVU control/status register |
| `ESE2NVU_CSR_CLR_ESE` | ESE → NVU | ESE-to-NVU CSR clear (write-to-clear) |
| `NVU2ESE_DB` | NVU → ESE | NVU-to-ESE doorbell (NVU-side mirror) |
| `ESE2NVU_DB_MIRROR` | ESE → NVU | ESE-to-NVU doorbell mirror (NVU-side read) |
| `NVU2ESE_CSR` | NVU → ESE | NVU-to-ESE control/status register |

> **Transport**: NVU→ESE messages use **IOSF SB RS=2 MMIO WR** (ESE Root Space). ESE→NVU messages use **IOSF SB PVTCFG WR** (private config space).

#### ISH IPC Registers

| Register | Direction | Description |
|----------|-----------|-------------|
| `NVU2ISH_DOORBELL_ISH` | NVU → ISH | NVU-to-ISH doorbell |
| `ISH2NVU_DOORBELL_ISH` | ISH → NVU | ISH-to-NVU doorbell |
| `ISH2NVU_CSR_ISH` | ISH → NVU | ISH-to-NVU control/status register |
| `ISH2NVU_CSR_CLR_ISH` | ISH → NVU | ISH-to-NVU CSR clear (write-to-clear) |
| `NVU2ISH_DB` | NVU → ISH | NVU-to-ISH doorbell (NVU-side mirror) |
| `ISH2NVU_DB_MIRROR` | ISH → NVU | ISH-to-NVU doorbell mirror (NVU-side read) |
| `NVU2ISH_CSR` | NVU → ISH | NVU-to-ISH control/status register |

> **Transport**: Both directions use **IOSF SB PVTCFG WR** (no RS=2 distinction for ISH).

#### Host IPC Registers

| Register | Direction | Description |
|----------|-----------|-------------|
| `NVU2HOST_DOORBELL_HOST` | NVU → Host | NVU-to-Host doorbell |
| `HOST2NVU_DOORBELL_HOST` | Host → NVU | Host-to-NVU doorbell |
| `NVU_HOST_FWSTS_HOST` | NVU → Host | Firmware status (read-only from host) |
| `NVU_HOST_COMM_HOST` | Bidirectional | Communication register (host R/W) |

### IPC Message Flow Details (from HAS SVG)

#### NVU → ESE Message Flow (Doorbell)


NVU FW                    NVU2ESE Regs              ESE
  │                           │                       │
  ├─ Write(M1) ──────────────►│ NVU2ESE_DOORBELL_ESE  │
  │  via IOSF SB RS=2 MMIO WR│                       │
  ├─ Assert ROWN_REQ[SBR] ───►│                       │
  │  wait for ACK             │                       │
  │                           ├─ INTR ───────────────►│
  │                           │                       ├─ Read(M1)
  │                           │                       ├─ CLR DB / Ack
  │                           │◄── M1 Ack (DB=0) ────┤
  │                           │  via IOSF SB PVTCFG WR│
  │◄── Read(DB=0) ───────────┤                       │
  ├─ De-Assert ROWN_REQ[SBR] ►│                       │
  │  wait for ACK             │                       │


#### NVU → Host Message Flow (Legacy IRQ)


NVU FW                    HOST IPC Regs        IOSF2AXI BR    Host Driver
  │                           │                    │               │
  ├─ Write(M1) ──────────────►│ NVU2HOST_DOORBELL  │               │
  ├─ Assert ROWN_REQ[SBR] ───►│                    │               │
  │  wait for ACK             │                    │               │
  │                           ├─ Host_Intr=1 ─────►│               │
  │                           │                    ├─ Assert_IRQx# │
  │                           │                    │  via IOSF SB ─►│
  │                           │                    │               ├─ Read(M1)
  │                           │                    │               │  via IOSF Primary MMIO RD
  │                           │                    │               ├─ Write(Clear DB/Mask)
  │                           │                    │               │  via IOSF Primary MMIO WR
  │                           ├─ INTR ────────────►│               │
  │                           ├─ Host_Intr=0 ─────►│               │
  │                           │                    ├─ Deassert_IRQx#│
  │◄── Read(DB=0) ───────────┤                    │               │
  ├─ De-Assert ROWN_REQ[SBR] ►│                    │               │


#### NVU → Host Message Flow (MSI)

Same as Legacy IRQ flow but:
- Uses **MSI_GEN** block instead of `Assert_IRQx#` / `Deassert_IRQx#`
- Uses **ROWN_REQ[PSF]** instead of `ROWN_REQ[SBR]` for resource ownership

#### Host → NVU Message Flow


Host Driver               HOST IPC Regs             NVU FW
  │                           │                       │
  ├─ Read(check DB=0) ───────►│ HOST2NVU_DOORBELL_HOST│
  ├─ Write(M2) ──────────────►│                       │
  │                           ├─ INTR ───────────────►│
  │                           │                       ├─ Read(M2)
  │                           │                       ├─ Write(Clear DB)
  │                           │                       ├─ Read(DB=0 status)
  │                           │                       ├─ Write(Clear DB=0/Mask)
  │◄── Read(DB=0) ───────────┤                       │
  │                           │                       ├─ De-Assert ROWN_REQ[SBR]
  │                           │                       │  wait for ACK


#### FWSTS / COMM Register Access

- **FWSTS Read**: Host reads `NVU_HOST_FWSTS_HOST` via IOSF Primary MMIO RD (firmware status, read-only from host)
- **COMM Write**: Host writes `NVU_HOST_COMM_HOST`, NVU FW reads back (bidirectional communication register)

### SBEP Downstream Message Processing (from HAS SVG)

The IOSF Sideband Endpoint (SBEP) processes incoming sideband messages in a 5-step flow:


IOSF Sideband              SBEP HW Block              NVU FW
  │                           │                          │
  ├─ SB message ─────────────►│ p_inmsg_avail            │
  │                           ├─ MSG_RCVD_IRQ_STATUS=1 ─►│
  │                           │  msg_received_down_intr   │
  │                           │                          ├─[3] Read:
  │                           │                          │  SB_DS_ATTRIBUTES
  │                           │                          │  SB_DS_ADDRESS
  │                           │                          │  SB_DS_SAI
  │                           │                          │  SB_DS_DATA_IN*
  │                           │                          │  Decode opcode + SAI
  │                           │                          ├─[4] Clear MSG_RCVD_IRQ_STATUS
  │                           │◄── p_inmsg_get ──────────┤[5]


| Step | Action | Register / Signal |
|------|--------|-------------------|
| 1 | SB message arrives | `p_inmsg_avail` asserted |
| 2 | Interrupt fires | `MSG_RCVD_IRQ_STATUS` = 1, `msg_received_down_intr` |
| 3 | FW reads message | `SB_DS_ATTRIBUTES`, `SB_DS_ADDRESS`, `SB_DS_SAI`, `SB_DS_DATA_IN*` |
| 4 | FW clears status | Clear `MSG_RCVD_IRQ_STATUS` |
| 5 | FW acknowledges | `p_inmsg_get` asserted → SBEP releases buffer |

> **SBEP registers**: `SB_DS_CONTROL_STATUS` and `SB_DS_REGISTERS` provide the downstream message buffer and control interface.

### SEC_REG Region (ATT Entry 2)

The SEC_REG region (4KB) contains security configuration registers:

| Register Type | Description |
|--------------|-------------|
| Control Policy (CP) | Security policy control |
| RAC | Read Access Control |
| WAC | Write Access Control |

### ATT Security

- **ATT_WRITE_DISABLE** bit: Write-once bit that freezes all ATT entries after BUP (Bring-Up) firmware sets it
- FW must clear the ATT entry for Host IPC before disabling writes to ATT
- Once ATT_WRITE_DISABLE is set, no further ATT modifications are possible until next reset
- SRAM security is enforced during host camera usage
- NVU has **3584 KB on-chip SRAM** (7 slices × 512 KB each) with SECDED ECC — all FW code, model weights, and intermediate tensors reside here; SMMU-based FW paging extends capacity to DRAM (IMR)


## Security Parameters (Integration HAS v0.8, Section 13)

> Source: SIP NVU1.0 Integration HAS v0.8, Section 13 (Security and Access Control). These parameters define the SAI policy, root space access controls, and DMA security enforcement.

### SAI Policy and Root Spaces

| Parameter | Value | Description |
|-----------|-------|-------------|
| RS0 (Host Root Space) | Host access | FW download from host DRAM, host MMIO access |
| RS2 (ESE Root Space) | ESE sideband | ESE authentication and management |
| RS3 (IMR Root Space) | Authenticated FW store | FW paging source, Intel-authenticated |

### Security Lock Bits

| Lock Bit | Type | Default | Description |
|----------|------|---------|-------------|
| `RS0_DISABLE` | Write-once | 0 | Disables FW/HW DMA to Host RS0 DRAM. Set by BUP post-boot. |
| `RS3_WR_DISABLE` | Write-once | 0 | Disables FW/HW DMA writes to RS3 IMR. Set by BUP post-boot. In debug mode = 0 (unlocked). |
| `IPC_DISABLE` | Write-once | 0 | Cuts off IPC communication between NVU and host. Set by BUP post-boot. |
| `ATT_WRITE_DISABLE` | Write-once | 0 | Freezes all ATT entries. Set by BUP after configuring ATT. |

### DMA Security Enforcement

When `RS0_DISABLE` is set:
- Boot/IO DMA: if `RS0_DISABLE && (TM[1:0] != 0x0 && (RD_RS || WR_RS) == 0x0)`, DMA_MISC forces `AxADDR[63] = 0` and redirects to reserved address `0xB000_0000`
- Paging DMA: same RS0_DISABLE enforcement
- SIO DMA: no IOSF2AXI target port connectivity (blocked by design)

### SRAM Firewalls

NVU SRAM has firewall regions to isolate security-critical data from general FW access. Firewall configuration is set by BUP and frozen via lock bits.

#### ID-Based SRAM Firewall Regioning (Integration HAS v0.8, Section 13)

The SRAM firewall uses ID-based regioning with separate configuration for VMEM and PMEM address spaces:

| Register | Purpose |
|----------|---------|
| `VMEM_SRAM_SUB_REGION0_BASE` | Virtual memory firewall region base address |
| `VMEM_SRAM_SUB_REGION0_LIMIT` | Virtual memory firewall region limit address |
| `PMEM_SRAM_SUB_REGION0_BASE` | Physical memory firewall region base address |
| `PMEM_SRAM_SUB_REGION0_LIMIT` | Physical memory firewall region limit address |
| `ACCESS_ID` | Permitted accessor identity (SAI-based) |

**Access Check Logic**: The firewall performs an XOR-based comparison between the requester's SAI and the programmed `ACCESS_ID`. If the XOR result is non-zero, access is denied and the request is terminated with an error response.

**Default State**: Firewalls are **disabled by default** (`LIMIT = 0x0`). BUP firmware configures the firewall regions during secure boot and locks them via write-once lock bits before handing off to runtime FW.

### Key Security Parameters (Hex Defaults)

| Parameter | Default | Description |
|-----------|---------|-------------|
| SAI policy matrix | Platform-specific | Defines which SAI agents can access which address regions |
| NVU_SAI | Platform-assigned | Security Agent Identifier for all FW-initiated traffic |
| DEVICE_UNTRUSTED_SAI | Platform-assigned | SAI for MSI during FW loading (before authentication) |
| RS0_REDIRECT_ADDR | `0xB000_0000` | Redirect target for blocked RS0 DMA accesses |

> **Note**: The full security parameter table (~30 entries with hex defaults) is in Integration HAS v0.8, Section 13. Many parameters are platform-integration-specific and set during SoC build. The key parameters above cover the host driver-visible security controls.

The NVU HOST IPC provides the bidirectional communication channel between the host driver and NVU firmware.

### HOST IPC Configuration

| Parameter | Value |
|-----------|-------|
| IPC Type | HOST |
| Downstream Payloads | 32 |
| Upstream Payloads | 32 |
| FWSTS Registers | Yes |
| COMM Registers | Yes |
| Remap Registers | 6 |
| D0i3 Support | Yes (register only — D0i3 state not used) |

### IPC Flow (Host to NVU)

1. Host writes command + payload to HOST_IPC downstream registers in BAR0
2. NVU firmware receives interrupt, reads command from IPC
3. NVU firmware processes command, writes response to upstream payload registers
4. NVU signals completion to host via interrupt (legacy IRQ or MSI)

> **Note**: Each IPC channel (HOST and all PEERs) has independent non-overlapping 4K host MMIO space and is independently secured with SAI-based access policy.


## Interrupt Delivery

The NVU supports two interrupt delivery mechanisms from NVU to host:

### Legacy IRQ

- Delivered via IOSF2AXI Bridge sideband as `AssertIRQ` / `DeAssertIRQ` messages
- Level-sensitive signaling

### MSI (Message Signaled Interrupts)

- Supported via `WIRE2MSI` method in the IOSF2AXI bridge
- `MSI_GEN` block in NVU initiates MSI requests
- **1 MSI vector only** (`MSI_MULT_MSG_CAP=0`) — all IRQ sources share a single MSI vector; FN1 has higher arbitration priority over FN0
- MSI is qualified by ALL of the following conditions:
  - Device NOT in D3 state (`!D3`)
  - Bus Master Enable set (`BME`)
  - MSI Enable set (`MSI_EN`)
  - Resource ownership request/acknowledge completed (`resource_own_req/ack`)

### IRQ Mode Selection

Selection between MSI and Legacy IRQ is determined during device enumeration based on:
- `PCICMD[INTDIS]` -- Interrupt Disable bit in PCI Command register
- `MSICAP[MSI_EN]` -- MSI Enable bit in MSI Capability structure

| INTDIS | MSI_EN | Mode |
|--------|--------|------|
| 0 | 0 | Legacy IRQ (Sideband AssertIRQ/DeAssertIRQ) |
| 1 | 1 | MSI based interrupt delivery |
| 0 | 1 | MSI (HAS Section 8.1 shows MSI_EN=1 → MSI regardless of INTDIS; SW convention sets INTDIS=1 with MSI_EN=1) |
| 1 | 0 | No interrupt capability (interrupts disabled, MSI off) |


## Firmware Loading Sequence

The NVU SW driver is primarily active during NVU boot for firmware loading. After successful FW load, the driver transitions to D3.

### Boot Flow Overview

| Phase | Description |
|-------|-------------|
| 1. Enumeration | Host enumerates NVU as PCI RCiEP, configures BAR0 |
| 2. FW Download | Host driver loads firmware via DMA to IMR |
| 3. FW Handoff | NVU firmware takes over, driver receives completion via IPC |
| 4. D3 Transition | Host driver transitions NVU to D3 power state |

### FW Download Details

- FW download reads from **RS0 DRAM** via the IOSF Primary Initiator interface
- Maximum bandwidth: up to **1.6 GB/s**
- Detailed firmware loading protocol is defined in the NVU FAS (Firmware Architecture Spec) -- `Not specified in NVU HAS v1.0`

### Boot Flow Variants

| Variant | Description |
|---------|-------------|
| Lid Open Boot | NVU boots and loads FW; remains operational with VNN resource requested; deepest platform state = S0i2.0 |
| Lid Closed Boot | NVU should be in lowest power state; not operational |

### Recovery from Exception Reset

If NVU encounters an exception and resets:
1. NVU signals host via **PME** (Power Management Event)
2. Host driver wakes from D3 via PME
3. Host driver re-loads firmware from scratch
4. Normal boot flow resumes from FW Download phase

> **Note**: HAS Section 21 (Software Considerations) defers detailed SW driver implementation to the NVU FAS. KMDF/WDF driver framework details are `Not specified in NVU HAS v1.0`.


## Driver Power Management

The NVU supports multiple power states managed by the host driver in coordination with PMC.

### Power States

| State | Name | Description |
|-------|------|-------------|
| D0i0 | Active | NVU fully operational, inference running |
| D0i1 | Light Idle | Clock-gated via QREQN/QACCEPTN handshake; NVU idle, clocks off, power on, state retained |
| D0i2 | Deep Idle | IPAPG + Retention; NVU idle, power-gated with SRAM retention |
| D3 Hot | Off | NVU non-functional, lowest power; entered after FW load completes |

> **HAS constraint (Section 13)**: NVU supports **D3 Hot only** — D3 Cold is NOT supported. There is no D0i3 (no FW context save) and no RTD3. The host driver must coordinate D3 Hot entry/exit exclusively through PMC sideband messages.

### Latency Tolerance Reporting (LTR)

NVU supports **LTR (Latency Tolerance Reporting)** via the IOSF2AXI bridge. The driver programs LTR values to inform the platform power controller of NVU's tolerable wake latency, enabling deeper package C-state residency during idle periods. LTR is configured through the IOSF sideband endpoint and is critical for S0ix integration.

### PME Configuration

| Parameter | Value |
|-----------|-------|
| PME Support Strap | `nvu_br_strap_pme_support` = `0x9` (enabled in D0 and D3) |
| PME Destination | `nvu_br_strap_pme_destid` -> PMC PortID |

PME is used for:
- NVU signaling host to wake from D3 (e.g., exception recovery, Wake-on-Face event)
- Assert/Deassert PME delivered via IOSF sideband messages

### D3/BME Flow

When host initiates D3 transition:
1. Host sets D3 bit in PCI PM Control/Status register
2. NVU firmware quiesces all active operations
3. NVU acknowledges D3 entry
4. NVU decodes IOSF SB cycles even with D3 bit set (for wake/config access)

### PGCB Power Domains

The NVU uses PGCB (Power Gate Control Block) interfaces for power gating:

| Power Domain | Description |
|-------------|-------------|
| Main | Primary NVU power domain |
| USB | USB camera interface power domain |
| MIPI | MIPI camera interface power domain |

### Platform Sleep State Behavior

| Platform State | NVU Behavior |
|---------------|-------------|
| S0 (Lid Open) | NVU operational, VNN resource requested, deepest = S0i2.0 |
| S0 (Lid Closed) | NVU in lowest power state, not operational |
| Sx (S3/S4/S5) | NVU non-functional |

> **Chassis 2.2**: NVU sleep state management follows Chassis 2.2 requirements.

### IPU_AON and D3 Camera Teardown (E2E HAS v0.1)

> Source: VISION SS End-To-End HAS v0.1.

The **IPU_AON** (Always-On) logic block remains alive even when IPU enters D3. It is only reset by `prim_rst_b` on PCD (Platform Cold/Dead reset). Key implications for the NVU driver:

- Camera ownership flags (`CDPHY_OWNER`, `USB_CAM_OWNER`) persist through IPU D3 transitions via IPU_AON
- NVU can claim/release camera ownership through IPU_AON without requiring IPU to be in D0
- When NVU driver transitions to D3 after FW load, camera ownership is released — but IPU_AON retains the arbitration state
- On NVU wake (via PME), the driver must re-establish camera ownership through the arbitration protocol, checking IPU_AON state


## UVOL Driver Architecture (from FAS SVG)

The NVU USB Camera Offload is managed by the **UVOL (USB Vision Offload Layer)** driver, a firmware-internal software stack that drives the USB-IF subsystem. The UVOL driver is structured in layers:

### UVOL Software Layer Decomposition


┌─────────────────────────────────────────────────────┐
│                  Camera App                          │
│         (Application-level camera control)           │
├─────────────────────────────────────────────────────┤
│  Configuration Service  │  USB Sharing              │
│  (Camera config from    │  (IPU/NVU ownership       │
│   BIOS _DSM)            │   arbitration)            │
├─────────────────────────────────────────────────────┤
│            Device Enumeration                        │
│  ┌──────────┬──────────────┬───────────────────┐    │
│  │ Enable   │ Address      │ Configure         │    │
│  │ Slot     │ Device       │ Endpoint          │    │
│  ├──────────┼──────────────┼───────────────────┤    │
│  │ Disable  │ Reset        │ Stop              │    │
│  │ Slot     │ EndPoint     │ EndPoint          │    │
│  └──────────┴──────────────┴───────────────────┘    │
├─────────────────────────────────────────────────────┤
│            HOST Reset / Error Recovery               │
│            Reset Device / Pin Remapping               │
│            PortSC Change Event / Frame Sync          │
├─────────────────────┬───────────────────────────────┤
│    HC / HAR / HAT   │   HC ISOCH / DC ISOCH / DC    │
│  (Host Controller   │  (Isochronous/Data Channel    │
│   Async Registers)  │   transfer management)        │
├─────────────────────┴───────────────────────────────┤
│  Set/Get Register Function │ Set/Get Pin EP          │
├─────────────────────────────────────────────────────┤
│              UAL / UDF                               │
│  (USB Abstraction Layer / USB Data Flow)             │
├──────────────┬──────────────────────────────────────┤
│  LinkLogic   │     MSI2IPI     │     MISC           │
├──────────────┴──────────────────────────────────────┤
│              SIO DMA                                 │
│  (Streaming IO DMA for isochronous data)             │
├─────────────────────────────────────────────────────┤
│              SIO HW                                  │
└─────────────────────────────────────────────────────┘


### UVOL xHCI Command Set

The UVOL driver implements a subset of xHCI commands for USB camera management:

| Command | Description |
|---------|-------------|
| `Enable Slot` | Allocate device slot for USB camera |
| `Address Device` | Assign USB address to enumerated camera |
| `Configure Endpoint` | Configure isochronous endpoints for video streaming |
| `Disable Slot` | Release device slot |
| `Reset EndPoint` | Reset stalled or errored endpoint |
| `Stop EndPoint` | Stop active endpoint transfer |
| `Reset Device` | Full device reset and re-enumeration |

### UVOL Key Functions

| Function | Description |
|----------|-------------|
| `Pin Remapping` | Map SIO pins to appropriate camera data channels |
| `PortSC Change Event` | Handle USB port status change (connect/disconnect) |
| `Frame Sync` | Synchronize frame counters (MFINDEX, MCO=7, DRS) |
| `Set/Get Register Function` | Low-level register access to SIO/xHCI registers |
| `Set/Get Pin EP` | Map SIO pins to endpoint associations |


## SIO Interface Architecture (from HAS SVG)

The **SIO (Streaming IO) Component** connects the NVU USB-IF subsystem to the IOSF fabric via the NoC Crux Fabric. It handles all USB camera data movement between the xHCI camera controller and system memory.

### SIO Fabric Connectivity


                         NoC Crux Fabric
                    (200 MHz, 16B Data, Max 3.2 GB/s BW)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         AXI Target      AXI Initiator    SIO Pin Logic
              │               │               │
    ┌─────────┴─────────┐     │        ┌──────┴──────┐
    │ IOSF Primary I/F  │     │        │  Pin-0..10  │
    │ CH0: VC0d(RS0,p2p)│     │        │  (to IPU /  │
    │      VCm (RS3)    │     │        │   XHCI_CAM) │
    │      VCp (rx,RS0) │     │        └─────────────┘
    │ CH1: VCp (tx,RS0) │     │
    └───────────────────┘     │
                              │
                    ┌─────────┴─────────┐
                    │  SIO Sub-Blocks   │
                    │  Host Async Tx ×2 │
                    │  Host Async Rx ×2 │
                    │  Host Async BiDir │
                    │  Frame Counter    │
                    │  Dev CmdResp ×1   │
                    │  Host Isoch Rx ×2 │
                    │  Dev Isoch Rx ×1  │
                    │  Host CmdResp ×2  │
                    │  Register Block   │
                    └───────────────────┘


### IOSF Primary Interface Channels

| Channel | Virtual Channel | Root Space | Direction | Purpose |
|---------|----------------|------------|-----------|---------|
| CH0 | VC0d | RS0, P2P | Bidirectional | Host data (peer-to-peer) |
| CH0 | VCm | RS3 | Bidirectional | IMR data (authenticated FW) |
| CH0 | VCp | RS0 | Receive only | Host data (inbound) |
| CH1 | VCp | RS0 | Transmit only | Host data (outbound) |

### SIO Pin Connections (from HAS SVG)

The SIO has 11 pins (Pin-0 through Pin-10) that connect to IPU and XHCI_CAM subsystems. Pin assignments differ based on the camera ownership mode.

#### IPU-Side Pin Map

| Pin | Function | Description |
|-----|----------|-------------|
| Pin-0 | Config | IPU configuration channel |
| Pin-2 | INTR OUT (RGB) | Interrupt output for RGB camera |
| Pin-3 | INTR OUT (IR) | Interrupt output for IR camera |
| Pin-4 | INTR IN (RGB) | Interrupt input from RGB camera |
| Pin-5 | INTR IN (IR) | Interrupt input from IR camera |
| Pin-6 | EP0 | Endpoint 0 (control) |
| Pin-7 | ISOCH IN (RGB) | Isochronous input for RGB stream |
| Pin-8 | ISOCH IN (IR) | Isochronous input for IR stream |
| Pin-9 | Config (Dev) | Device configuration |
| Pin-10 | ISOCH IN (Dev) | Isochronous input for device |

#### NVU/XHCI_CAM-Side Pin Map

| Pin | Function | Description |
|-----|----------|-------------|
| Pin-1 | EP0 | Endpoint 0 (control) |
| Pin-2 | ISOCH IN (IR) | Isochronous input for IR stream |
| Pin-3 | INTR IN (IR) | Interrupt input from IR camera |
| Pin-4 | INTR OUT (IR) | Interrupt output for IR camera |
| Pin-5 | ISOCH IN (RGB) | Isochronous input for RGB stream |
| Pin-6 | INTR IN (RGB) | Interrupt input from RGB camera |
| Pin-7 | INTR OUT (RGB) | Interrupt output for RGB camera |
| Pin-8 | Config | NVU configuration channel |

#### RAW Camera Pin

| Pin | Function | Description |
|-----|----------|-------------|
| Pin-1 | Config | RAW camera configuration |

### Camera Sharing Modes (from HAS SVG)

The SIO pin routing determines which subsystem owns the camera:

| Mode | Camera Owner | IPU State | NVU State | Description |
|------|-------------|-----------|-----------|-------------|
| **IPU Exclusive** | IPU | Streaming | Disabled | Camera fully owned by IPU; NVU/Low Power Vision disabled |
| **NVU Exclusive** | NVU | Not streaming | Active | Camera fully owned by NVU; Host/IPU not streaming |
| **Concurrent** | IPU (primary) | RGB Streaming | Offloading | Camera owned by IPU; IPU RGB stream offloaded through NVU |

> **Sub-blocks in SIO Pin Logic**: LL (LinkLogic), UDF (USB Data Flow), L (Link), D (Data), F (Frame).


## Windows vs Linux Driver Differences

`Not specified in NVU HAS v1.0`. The HAS does not specify OS-specific driver implementation details. Driver framework information (KMDF, WDF, Linux kernel module) is expected in the NVU FAS (Firmware Architecture Spec) or SW Architecture documents.


## NVU-ISH Communication Protocol (FAS §14, L14281-18048)

The NVU communicates with the Integrated Sensor Hub (ISH) via the PEER_IPC channel using a 3-layer protocol stack that reuses the ISH-CNVi protocol framework. NVU acts as **Leader** in IPC Reset sequences.

### Protocol Stack

| Layer | Name | Description |
|-------|------|-------------|
| 1 | IPC (Transport) | Doorbell + mailbox via PEER_IPC MMIO (4KB) |
| 2 | Logical | Sequencing, capability routing, message type |
| 3 | Application | Capability-specific payloads (face, hand, body, etc.) |

### IPC Header — Standard Long Format (FAS §14, L16800)

| Bits | Field | Description |
|------|-------|-------------|
| `[9:0]` | `payload_size` | Payload size in bytes |
| `[15:10]` | `client_id` | Client identifier (0 = reserved for ISH-PeerIP) |
| `[23:19]` | `long_format_ver` | Always `0` for NVU-ISH |
| `[31]` | `busy` | IPC busy flag |

### Logical Header (FAS §14, L16850)

| Bits | Field | Description |
|------|-------|-------------|
| `[7:0]` | `sequence_num` | Message sequence number |
| `[15:8]` | `capability_id` | See Capability ID table below |
| `[22:16]` | `message_type` | 0=VersionHandshake, 1=CapabilitiesDeclaration, 127=capability-specific |
| `[23]` | `is_response` | 1 = response message |

### Capability ID Encoding (FAS §14, L16870)

The `capability_id[15:8]` field encodes both instance and type:
- Bits `[7:6]` = instance number
- Bits `[5:0]` = capability type

| Type Value | Capability | Description |
|-----------|-----------|-------------|
| 0 | Protocol Control | Version handshake, capability declaration |
| 1 | Face Tracking | Face detect + track + HPD |
| 2 | Face ID Enrollment | Face enrollment management |
| 3 | Light XYZ | Camera-based ambient light sensing |
| 4 | Camera Occlusion | Camera obstruction/smudge detection |
| 5 | Body Posture | Ergonomic posture detection |
| 6 | Hand Gesture | Static hand gesture recognition |
| 7 | Hand Pose | 21-landmark hand skeleton |
| 8 | Camera Calibration | ALS/SDO calibration from ISH |

### Handshake Flow (FAS §14, L17000)

ISH initiates the handshake sequence:

1. **Version Handshake**: ISH sends `message_type=0` (Version Handshake) with `is_response=0` (Request), `capability_id=0` (Protocol Control) → NVU responds with `is_response=1` (Response)
2. **Capabilities Declaration**: ISH sends capabilities declaration → NVU confirms supported capabilities
3. **Capability-Specific Messages**: After handshake, both sides exchange capability-specific messages per capability


## AON Vision Data Interfaces (FAS §14, L14281-18048)

The NVU outputs structured vision data to ISH via the NVU-ISH protocol. These data structures define the application-layer payloads.

### App Topology (FAS §14, L14300)

NVU runs 13 vision apps at 3 FPS (333ms interval, ±15% jitter):

| App | Output | Key Parameters |
|-----|--------|---------------|
| Camera | Raw frame acquisition | Mono/Bayer/RGBIR/Y8 formats |
| Image Reformat | Y8 @ 320×320 (padded) | Pad value = 128 |
| Camera Occlusion | Obstruction/smudge status | Binary status + lighting condition |
| Camera Calibration | ALS+SDO from ISH | On/off, interval, sensitivity |
| Face Detection | Up to 3 faces | Min 24×24px, yaw ±90°, score+BB+angles |
| Face Landmark | 12 landmarks per face | x/y pixel coords on 320×320 |
| Face ID | Recognition result | INT8 vectors, 3 vecs/user × 5 users |
| Face Tracking | Temporal tracking | tracking_id[0-254], distance(mm,[0-5000]) |
| Face ID Enrollment | Enrollment status | enroll_flag codes (1=complete, negatives=failure) |
| Hand Detection | 21 landmarks | Wrist + 4 fingers × 4 joints + thumb × 4 |
| Hand Pose | 29 gesture types | Capability bitfield (Bit0=Palm...Bit28=Five) |
| Body Posture | Ergo/Non-ergo | Min face 60×60px, max 1 person |
| Light XYZ | Ambient light estimate | Camera-based, does NOT meet MSFT HW compat spec |

### camera_frame_data Struct (FAS §14, L14500)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | u64 | Microseconds, Hammock Harbor-synced |
| `frame_index` | u32 | Monotonic frame counter |
| `frame_format` | enum | MONO/Bayer/RGBIR/RGBA/YUY2/NV12/Y8 |
| `validity_flag` | u8 | Frame validity indicator |
| `lux` | float | Ambient light estimate |
| `cct` | float | Correlated Color Temperature |
| `histogram[16]` | u8[16] | 16 non-uniform bins [0-255] → percentage [0-100%] |

### Face ID Data Struct (FAS §14, L15200)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | u64 | Microseconds, HH-synced |
| `flag` | i8 | -1=obstructed, 0=invalid, 1=valid |
| `face_num` | u8 | Number of faces [0-3] |
| `face_ids[3]` | struct | Per-face: `score[0-100]`, `face_id` (-1=not enrolled, 0=unknown, 1=known) |

### Face Tracking Conventions (FAS §14, L15800)

| Convention | NVU Format | ISH Format |
|-----------|-----------|-----------|
| Bounding Box | top-left(x,y) + (w,h) on 320×320 | center(cx,cy) + (w,h) on QVGA 320×240 |
| Tracking ID | [0-254] per tracked face | Same |
| Distance | mm, range [0-5000] | Same |
| Mode | 0=OFF, 1-6=specific, 7=CONCURRENT | Same |
| Roll/Pitch/Yaw | Windows HeadOrientation Class convention | Same |

### Enrollment Flag Codes (FAS §14, L16000)

| Code | Meaning |
|------|---------|
| 1 | Enrollment complete (success) |
| -1 | General failure |
| -31 | Known face already enrolled |
| -32 | Privacy mode active |
| -34 | Too many enrollments per boot (max 10) |
| -36 | Storage full (max 5 users × 3 vectors) |
| -49 | Other failure |

> **Validation note**: `MAX_ASSETS_NUM=15`, `MAX_ENROLLMENT_PER_BOOT=10`, `MAX_STORAGE_SIZE=8192` bytes (from FAS §7.10 Security Service).


## Validation Test Scenarios

### PCI Enumeration Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| NVU PCI Discovery | Verify NVU appears as RCiEP with correct VID/DID | VID=0x8086, DID per soft-strap |
| BAR0 Size | Verify BAR0 is 64KB | BAR0 size = 0x10000 |
| Multi-Function | Verify NVU multi-function per `nvu_br_strap_mulfndev` strap | Multi-function bit = 1 when FN1 enabled (NUM_PCI_FUNCTIONS=2); bit = 0 when FN1 disabled |
| Class Code | Verify PCI class codes match soft-straps | Match `NVU_BaseClass_code_func1_SoftStrap` / `NVU_SubClass_code_func1_SoftStrap` |

### Host Register Access Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| HOST_IPC Read | Read HOST_IPC region at BAR0 + 0x0000 | Valid register data returned |
| PEER_IPC Access | Access PEER_IPC region at BAR0 + 0x10000 | Valid register data (if SAI allows) |
| SEC_REG Access | Access SEC_REG at BAR0 + 0x18000 | Valid security register data |
| ATT Frozen | Verify ATT_WRITE_DISABLE prevents modification | Write to ATT fails after BUP lockdown |

### IPC Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| Host IPC Downstream | Send IPC command from host to NVU | NVU receives and processes command |
| Host IPC Upstream | NVU sends response to host | Host reads valid response payload |
| IPC Interrupt | Verify interrupt delivery after IPC completion | IRQ/MSI fires correctly |
| MSI Qualification | Test MSI with D3=0, BME=1, MSI_EN=1 | MSI delivered |
| MSI Blocked D3 | Test MSI with D3=1 | MSI NOT delivered |

### Power Management Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| D0 to D3 | Transition NVU from D0 to D3 after FW load | NVU enters D3, power gated |
| D3 to D0 via PME | Wake NVU from D3 via PME | NVU wakes, host can re-load FW |
| D0i2 Entry | Idle NVU enters D0i2 (IPAPG+RET) | State retained, lower power |
| PME in D0 | Verify PME assertion works in D0 | PME delivered to PMC |
| PME in D3 | Verify PME assertion works in D3 | PME delivered to PMC |
| Lid Close | Close lid, verify NVU enters lowest power | NVU non-operational |
| Lid Open | Open lid, verify NVU boots and loads FW | NVU operational, VNN requested |

### Firmware Loading Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| FW Load Success | Load FW via host driver, verify completion | FW loaded, NVU operational |
| FW Load Recovery | Trigger NVU exception, verify PME wake + FW reload | Host re-loads FW successfully |
| FW Load Bandwidth | Measure FW download throughput | Up to 1.6 GB/s via IOSF Primary |

### NVU-ISH Communication Tests (FAS §14)

| Test | Description | Expected Result |
|------|-------------|-----------------|
| ISH Version Handshake | Trigger NVU-ISH version handshake via PEER_IPC | `supported_formats` bitmap exchanged, `selected_formats` single-bit returned |
| ISH Capability Declaration | Verify capability declaration after handshake | All 8 capability types reported (Face Tracking through Camera Calibration) |
| Face Detection Data | Request face detection output via ISH protocol | Up to 3 faces with score, BB, roll/pitch/yaw angles on 320×320 |
| Face ID Enrollment | Trigger enrollment, verify enroll_flag codes | Success=1, known face=-31, storage full=-36, max per boot=-34 |
| Face Tracking Format | Verify NVU BB format (top-left x,y + w,h on 320×320) | Correct conversion to ISH format (center cx,cy + w,h on QVGA) |
| Hand Pose Gesture | Request hand pose output | 29 gesture types via capability bitfield |
| Camera Occlusion | Verify occlusion detection output | Binary status + lighting condition reported |
| ISH IPC Reset | Verify NVU acts as Leader in IPC Reset | NVU initiates reset, ISH responds |
| Enrollment Limits | Attempt >10 enrollments per boot | Error code -34 after 10th enrollment |
| Max Users | Attempt >5 user enrollments | Error code -36 when storage full |


## PythonSV Patterns

```python
```
# ============================================================
# NVU Host Driver Interface -- PythonSV Quick Reference
# Source: NVU HAS v1.0 (SIP_NVU_HAS.html)
# ============================================================
#
# === PCI Configuration ===
# VID: 0x8086 (Intel standard)
# DID: from soft-strap nvu_br_strap_deviceid (16-bit)
# RevisionId: 0x00 (default)
# BAR0: 64KB, remapped to internal 0x8000_0000
# Topology: PCI RCiEP on IOSF
#
# === Host Address Map (ATT Entries) ===
# ATT Entry 0: HOST_IPC
#   MMIO: 0x8000_0000 -- 0x8000_1000 (4KB)
#   Internal: 0xF100_0000
#   Access: MMIO
#
# ATT Entry 1: PEER_IPC
#   MMIO: 0x8001_0000 -- 0x8001_7000 (28KB)
#   Internal: 0xF110_0000
#   Access: PVTCR
#
# ATT Entry 2: SEC_REG
#   MMIO: 0x8001_8000 -- 0x8001_9000 (4KB)
#   Internal: 0xF200_0000
#   Access: PVTCR
#
# ATT Entries 3-7: SPARE (invalid)
#
# === HOST IPC Configuration ===
# IPC_TYPE: HOST
# Downstream payloads: 32
# Upstream payloads: 32
# Has FWSTS: Yes
# Has COMM: Yes
# Remap registers: 6
# D0i3 support: Yes
# Sync reset: HOSTPRIMRST
#
# === Peer IPC Channels ===
# CSE, PMC, CNVI, ACE, ESE, BT, ISH
# Each: independent 4KB MMIO, SAI-secured
#
# === Interrupt Delivery ===
# Legacy: IOSF SB AssertIRQ/DeAssertIRQ
# MSI: WIRE2MSI via IOSF2AXI bridge
# MSI qualified: !D3 & BME & MSI_EN & resource_own_req/ack
# Mode select: PCICMD[INTDIS] and MSICAP[MSI_EN]
#
# === Power States ===
# D0i0: Active (inference running)
# D0i2: Deep Idle (IPAPG+RET, state retained)
# D3: Off (non-functional, post FW load)
#
# === PME ===
# Strap: nvu_br_strap_pme_support = 0x9 (D0+D3)
# Dest: nvu_br_strap_pme_destid -> PMC PortID
# Used for: D3 wake, exception recovery, WoF
#
# === PGCB Power Domains ===
# Main: Primary NVU domain
# USB: USB camera interface
# MIPI: MIPI camera interface
#
# === Security ===
# ATT_WRITE_DISABLE: write-once, freezes ATT after BUP
# SEC_REG: CP, RAC, WAC registers
# SAI-based policy per IPC channel
#
# === Firmware Loading ===
# FW download: RS0 DRAM via IOSF Primary Initiator
# Bandwidth: up to 1.6 GB/s
# Post FW load: driver -> D3
# Exception recovery: PME wake -> re-load FW
# Detailed FW protocol: TBD -- see NVU FAS
#
# === IOSF Sideband Messages ===
# PCI Register MRd/MWr
# PCI CfgRd/CfgWr
# Assert/Deassert PME
# NVU decodes SB cycles even with D3 bit set
#
# === Platform Behavior ===
# Lid Open: NVU operational, VNN requested, deepest = S0i2.0
# Lid Closed: NVU lowest power, not operational
# Sx: NVU non-functional
# Chassis 2.2 sleep state management



## See Also

- [power/SKILL.md](../power/SKILL.md) — D-state definitions, PGCB, clock gating
- [firmware/SKILL.md](../firmware/SKILL.md) — FW boot protocol, IPC mailbox, HECI transport, WAMR framework
- [registers/SKILL.md](../registers/SKILL.md) — MMIO register map, BAR layout
- [platform/SKILL.md](../platform/SKILL.md) — PCI enumeration, straps, reset
- [bios/SKILL.md](../bios/SKILL.md) — ACPI scope (_SB.PC00.NVUD), RTD3 ACPI flow, DMA remapping (IOMMU), PEP constraint, _DSM camera config
- [debug/SKILL.md](../debug/SKILL.md) — Driver debug, error handling, trace
- [inference/SKILL.md](../inference/SKILL.md) — NN model loading, NPX6-1K inference engine, ONNX→.nnx compilation
- **NVU FAS** (Firmware Architecture Specification) — §14 AON Vision Interface, §7.5 HECI/ARCSync protocol

## Related Sub-Skills

- [fv-nvu/camera](../camera/SKILL.md) — Camera/sensor interface, MIPI CSI-2, USB camera, ISP
- [fv-nvu/firmware](../firmware/SKILL.md) — FW architecture, boot ROM, secure boot, IPC protocol


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 01:00 | Facts added: 1105


### Additional HAS Details (86 facts)

#### RTOS and BSP Overview (Chapter 3)

##### Zephyr User Mode (7.1.3)

- Please refer to the Zephyr User Mode documentation for details on Zephyr User Mode operation.

##### SEDI — Service Engine Driver Interface (7.2.2)

- SEDI is a RTOS-independent BSP library written in pure C language.
- Zephyr SEDI Shim Layer Drivers are thin drivers that adapt SEDI drivers into Zephyr driver APIs.

---

#### Peripheral Drivers (7.2.3)

##### SPI Driver (7.2.3.5)

- The SPI driver implements a subset of the Zephyr SPI driver API. Refer to the SPI Driver documentation for the full list of supported SPI APIs in Zephyr.

##### WDT Driver (7.2.3.8)

- The NVU WDT driver implements a subset of the Zephyr WDT driver API. Refer to the NVU WDT Driver documentation for the WDT API supported in Zephyr.

##### STU Driver API (7.2.3.10.1)

- The STU driver API includes the following signature element:
  ```c
  speed_Event const link_event);
  ```

##### MJPG Decoder and Post Processing (7.2.3.14)

- Top-level APIs are provided for use by upper-layer applications to perform decoding and/or post-processing.
- The driver provides APIs for users to init/configure the decoder and post-processor (PP).
- Post-processing functions are fully hardware-implemented; the control software part provides an API that translates user parameters to hardware register settings.
- When the PP is operated in combined mode (decoder + PP), internal communication between the decoder and PP is hidden from the API user. The user only needs to configure the PP to work in combined mode.

##### HECI Driver (7.2.3.16)

###### HECI Transport Protocol (7.2.3.16.1)

The HECI transport protocol uses a command/response structure. Fields per message:

| Direction | Field     | Description                          |
|-----------|-----------|--------------------------------------|
| Request   | command   | Command identifier                   |
| Request   | id        | Message ID                           |
| Request   | structure | Payload structure                    |
| Response  | command   | Response command identifier          |
| Response  | id        | Response message ID                  |
| Response  | structure | Response payload structure           |

**Example — Host Enumeration Message:**

| Direction | Command                        | ID     | Structure                                                                 |
|-----------|-------------------------------|--------|---------------------------------------------------------------------------|
| Request   | `HECI_BUS_MSG_HOST_ENUM_REQ`  | `0x04` | `uint8_t command; uint8_t client_req_bits; uint8_t reserved[2];`         |
| Response  | `HECI_BUS_MSG_HOST_ENUM_RESP` | `0x84` | (refer to HAS spec)                                                       |

###### HECI Clients (7.2.3.16.1.1)

- PNR commands: TODO — evaluate whether the same PNR command set used by ISH can be reused for NVU to enable playback and record with the ISH PNR tool.

###### HECI Buffering (7.2.3.16.1.2)

- Flow control for the SW→FW direction is implemented with HECI buffering:
  - The HECI SW driver allocates a large number of buffers for client messages.
  - At the beginning of a connection, the HECI SW driver sends flow control messages to FW to indicate buffer availability.

---

#### Security Service (7.2.5)

The security service provides two sets of APIs:

- **User-space APIs** — used by the Face ID Enrollment App to enroll new face ID vectors or delete existing vectors from storage. User space cannot load or read stored face ID vectors directly, to prevent data leaking.
- **Kernel-space APIs** — used by the CV service in kernel space for Face ID matching. The CV service has privileged access to stored face ID vectors and performs Face ID matching (triggered from kernel space).

**Security Service API List (7.2.5):**

| API | Description | Consumer |
|-----|-------------|----------|
| `int sec_svc_asset_add(uint8_t *asset, uint16_t size)` | Add a new asset to the asset list | Face ID Enrollment App (User Space) |
| `int sec_svc_assets_store(void)` | Store all assets to storage | Face ID Enrollment App (User Space) |
| `int sec_svc_assets_delete(void)` | Delete all assets in storage | Face ID Enrollment App (User Space) |
| `int sec_svc_assets_info(sec_assets_info_t *info)` | Get assets info in storage | Face ID Enrollment App or Face ID App (User Space) |
| `int sec_svc_assets_retrieve(sec_assets_t **assets)` | Retrieve assets buffer address | CV Service (Kernel Space) |

---

#### NVU Windows SW Architecture (Chapter 5)

##### Background — Windows Sensing SW (5.1.3)

- The Windows Sensing SW Architecture is documented separately (refer to source diagram).
- This portion is a common solution across integrated and discrete AON vision solutions and is not NVU-specific.
- Further details can be found in the "ISH SW Architecture Spec".

##### NVU SW Stack Overview (5.2, 5.3)

- All NVU SW stack drivers are owned and developed by the NVU IP FW/SW team from ISCP China, SIG (5.3).
- The NVU SW Stack and IPU Hosted SW stack sections provide detailed per-component descriptions (5.2).

##### PCI Bus Driver (5.3.1)

- The PCI Bus Driver refers to the Windows native PCI Bus driver.
- NVU uses a PCIe host interface; NVU HW is enumerated as two different PDOs (Physical Device Objects).

##### NVU OED Driver (5.3.2)

- OED stands for **Offload Engine Driver**.

##### HECI Bus Driver (5.3.3)

- The HECI Bus Driver operates as a bus driver.
- It exposes a device for each HECI client that has the appropriate device bit set, as defined in the HECI protocol.

---

#### NVU Security and Privacy (Chapter 6)

##### Quick Links (10.3)

- Zephyr User Mode: refer to the Zephyr User Mode section for security-relevant user-mode isolation details.

---

#### WAMR Framework (Chapter 7)

##### Security Features (11.1.2)

- WAMR runtime provides **API isolation**:
  - Controls which APIs are exposed to each WASM app.
  - Allows per-app granular API access control.

##### WAMR Security Design Requirements (11.2)

- WAMR exposes only a minimal set of APIs to WASM apps, with permission control.
- Offload service APIs (CV/NN) are available only to vision algorithm apps.
- Cross-core communication APIs are available only to Intel core apps.

###### Risk: WAMR AOT Compiler (11.2.1)

- Performance comparison depending on calculation offloaded to kernel service:
  - Interpretation mode cycles: **1.1× – 3.2×** of AOT mode.
  - AOT mode cycles: **1.04× – 1.29×** of native code.

###### Risk: Pure SW Sandbox Mitigation (11.2.2)

- Mitigation follows a **"defense in depth"** philosophy with two-layer protection:
  - **First layer:** WAMR sandbox — relies on the WASM compiler and WAMR runtime.
  - **Second layer:** (refer to HAS spec for additional layer details).

##### WAMR Framework APIs (11.3.2)

- WASM APIs are documented in the WASM APIs section (11.8).

##### App Manager — Control Flow (11.3.4.1)

- Configuration updates from ISH (represented by green line in the architecture diagram) follow this flow:
  - ISH service publishes a Zephyr event to notify the App Manager about a new algorithm configuration.

##### App Manager — Active App Entity Tree Metadata (11.3.4.2)

- When the final result is ready to send to ISH:
  - Node state and edge weight are used to check validity.
  - If valid, the result is sent to the ISH service via the ISH communication API.
  - If not valid, the result is not forwarded.

##### WAMR Memory Management (11.5.1)

- The WAMR runtime (inside App Manager) runs in a **user-mode thread** on top of Zephyr RTOS.
- Memory allocation mode is **`Alloc_With_Pool`** — this mode restricts all memory used by WASM apps to a pre-allocated pool.

---

#### WASM Apps (11.6)

##### WASM App Categories (11.6.1)

- **Algorithm App:**
  - Runs vision algorithms.
  - Can be Intel or third-party.
  - Is restarted periodically after each processing cycle.
  - Can only access CV/NN offload APIs exposed by WAMR.

##### WASM App Data Leaking Prevention (11.6.2)

- To prevent privacy- and security-sensitive data from leaking out of TCB (from WASM apps → ISH → host SW), NVU FW design applies a set of data-leaking prevention methodologies.

##### Data Leaking Threat Detection and Report (11.6.3)

- WAMR is responsible for detecting if a third-party app:
  - Attempts to access a forbidden memory region.
  - Attempts to access forbidden WASM APIs.

---

#### WASM APIs (11.8)

##### App Management APIs (11.8.1)

- WASM apps are created by App Management during initialization.
- Key APIs:

  - **`app_mgmt_wasm_runtime_init()`**
    - Calls `wasm_runtime_full_init()` (provided by WAMR) to create a runtime environment for NVU App Management.

  - **`app_mgmt_wasm_create_queue()`**
    - Calls `bh_queue_create()` (provided by WAMR) to create a message queue used by WASM apps to place messages.

  - **`app_mgmt_route_msg_to_wasm_app()`**
    - Obtains source and destination app information from the message header and routes the message accordingly.

##### WASM Common APIs (11.8.2)

- All communication between WASM apps and from WASM apps to App Management is conducted via a **message queue**.
- The destination app receives the message, processes it, and sends out a result message.
- An app will not receive more than one message at a time; it will not receive the next message until it has sent out the result for the previous one.
- An app may receive messages from different source apps and must identify the source app from the message header.
- Result messages should not be assumed to be received in order.
- If an app is waiting for an async operation from a native service and another message arrives, it must be able to process the new message and later handle the async result when it arrives.

###### How to Receive a Message (11.8.2.1)

```c
uint32_t __attribute__((export_name("entry")))
message_handle(uint32_t src_app, uint32_t dst_app,
               uint32_t msg_id, uint32_t data_size,
               uint32_t data_buf);
// src_app:   source app ID
// dst_app:   destination app ID (usually the app itself)
// msg_id:    message ID
// data_size: size of the data buffer
// data_buf:  address of the data buffer in WASM linear memory
// return:    0 for success, otherwise failure
//            Tells App Management whether the message was processed successfully.
```

###### How to Post a Message (11.8.2.2)

```c
uint32_t wasm_app_notify(uint32_t src_app, uint32_t dst_app,
                         uint32_t msg_id,


```
### Boot and Reset Sequences (6 facts)

#### Boot and Reset Sequences

#### NVU Firmware Boot Flow — BUP Flow (HAS §9.2.2)

- The NVU BUP (Bring-Up) flow coordinates with host software (SW) and ESE to load NVU Intel/OEM firmware from the host.
- BUP relies on the **host SW driver** to load the firmware image from host memory into NVU.
- BUP relies on **ESE** to perform firmware authentication.
- The driver loads the NVU application image into **System DRAM**.

#### Extra BUP Tasks (HAS §9.2.2.1)

##### Trace Configuration Binary

- The NVU driver fetches the **trace configuration binary** from the Windows Registry, if present.
- The driver hands the binary over to NVU to apply.
- BUP is responsible for retrieving the binary and saving it in the appropriate location for NVU consumption.

##### Face ID Remove Indication

- The NVU driver fetches the **Face ID remove indicator** from the Windows Registry, if present.
- The driver hands the indicator over to NVU to apply.
- BUP is responsible for retrieving the indicator and saving it in the appropriate location for NVU consumption.

#### NPX Power Management — Resume Flow (HAS §13.7)

- On a `PM_DEVICE_ACTION_RESUME` power management action, the **ARCSync driver** follows the **NPX Reset flow** to boot the NPX core.

#### PC Reset Flag Management (HAS §5.5.1)

- The **NVU HECI driver** is responsible for managing a **PC reset flag**.
- The reset flag logic governs driver behavior across system reset scenarios; refer to HAS §5.5.1 for the full state diagram and flag management conditions.


### Camera Interface (328 facts)

### Camera Interface

#### Overview

The NVU Camera Interface encompasses BSP device drivers for MIPI CSI-2 PHY & Host Controller, USB Camera SIO, and supporting services including the Camera Config Service. These components collaborate with hardware to enable camera streaming, sensor control, and image processing pipelines. (§6.1, §7.2.3)

---

#### MIPI CSI-2 Camera

### PHY Sharing (§8.1.1)

- When the IPU is actively using a MIPI port, NVU can sniff the PPI interface between the C/D-PHY and the IPU's MIPI CSI-2 Host Controller(s).
- In this configuration, NVU has the option to downscale the images if the full resolution is not required.

### CSI-2 Host Controller Driver (§8.1.4)

- Zephyr does not have native CSI-2 host controller driver support.
- NVU FW defines custom CSI-2 host controller driver APIs to fulfill the required functionality.
- For full API details, refer to the NVU CSI-2 Host Controller driver specification.

---

#### Camera Config Service (§7.2.4)

The Camera Config Service is a Zephyr kernel mode service with two primary functions:

- **Hardware abstraction** — provides a unified API layer over underlying camera hardware.
- **Collaboration with hardware** — works in conjunction with the MJPEG decoder/post-processing driver to complete camera tasks. (§7.2.3.14)

### MIPI Camera APIs (§7.2.4.1.1)

The following APIs are provided by the Camera Config Service:

| API | Description |
|-----|-------------|
| `int cfg_svc_cam_init(cfg_svc_cam_init_param_t *cam_init_param)` | Initializes the camera service with the specified parameters |
| `int cfg_svc_cam_cfg(cfg_svc_cam_cfg_t *cfg_param)` | Configures the camera settings using the provided configuration |
| `int cfg_svc_cam_start(void)` | Starts the camera streaming |
| `int cfg_svc_cam_mem_input_start(cfg_svc_mem_in_param_t *mem_in_param)` | Starts to run camera with the input from memory |
| `int cfg_svc_cam_stop(void)` | Stops the camera streaming |
| `int cfg_svc_cam_deinit(void)` | Deinitializes the camera service |
| `int cfg_svc_cam_set_eventflag(event_flag_handle_t event_flag, uint32_t valid_mask)` | Sets event flag handle and the events to the camera service |
| `int cfg_svc_cam_get_result(cfg_svc_cam_result_type_t result_type, void *resut_info, uint32_t size)` | Retrieves the result of a camera operation |
| `int cfg_svc_cam_3a_cfg(cfg_svc_cam_3a_cfg_type_t cfg_type, void *cfg_param, uint32_t size)` | Updates 3A (Auto Exposure, Auto White Balance, Auto Focus) configurations |

> For more detailed information, refer to the Config Service API specification. (§7.2.4.1.1)

---

#### USB Camera SIO Driver (§7.2.3.15)

### Overview

- The USB Camera SIO driver enables the streaming of data from the xHCI controller to the IPU.
- Manages camera sensor controls, handles EP-0 programming, configures xHCI registers, and supports firmware-level operations.

### SIO Driver Interface (§7.2.3.15.1)

- The SIO driver provides software interfaces to send or receive data and notification messages, as defined in the SIO HAS.
- NVU SIO supports two distinct interfaces, each designed to implement specific messages with unique functionalities:
  - **SIO Target** — facilitates communication with the IPU.
  - **SIO Initiator** — facilitates communication with the xHCI.

### USB Camera Driver (§7.2.3.15.1.1)

Based on the SIO driver interface, the USB Camera driver supports:

- USB Camera enumeration
- USB messages
- Camera sensor control
- Camera streaming

#### USB Camera Enumeration

Two types of enumeration flows are supported:

- **xHCI hosted by software** — xHCI detects the device and signals a Port Status Change event.
- **xHCI hosted by NVU** — *(details TBD per HAS annotation)*

#### USB Camera Streaming

> **Note:** Detailed behavioral bullets for USB messages, camera sensor control, and streaming are marked as missing/TBD in the source HAS. (§7.2.3.15.1.1)

---

#### CVISP Driver (§8.2)

- Zephyr does not have native DTF driver support.
- NVU FW defines DTF driver APIs to fulfill the functionality.
- For the APIs defined for Zephyr, refer to the NVU DTF Driver specification.

### CVISP Motion Detection (§8.2.4)

- The Config Builder tool (provided by Altek) can set the threshold of each Bayer pattern channel.
- The CVISP driver uses these configurations to set ISP registers.
- During pipeline execution, if a pixel value exceeds the configured threshold, the motion detection condition is triggered.

---

#### SIO Peer-to-Peer Communication (§8.4)

### Message Format — VDM Header (§8.4.1.1)

- The VDM header is constructed and managed by NVU HW and is transparent to FW.

#### VDM Header Field Definitions

| Bits | Field | Description |
|------|-------|-------------|
| 4:0 | Fmt Type | Format type. `3'b001` = 4 DW header, no data; `3'b011` = 4 DW header, with data |
| 8:8 | TH | Transaction Hint — if set to 1, the TLP includes a transaction processing hint. Fixed as `1'b0` |
| 9:9 | R | Reserved. Fixed as `1'b0` |
| 10:10 | Attr | Attributes. Fixed as `1'b0` |
| 11:11 | R | Reserved. Fixed as `1'b0` |
| 14:12 | TC | Traffic Class — specifies the traffic class command attribute. Fixed as `3'b000` |
| 15:15 | R | Reserved. Fixed as `1'b0` |
| 17:16 | Length[9:8] | Upper 2 bits of TLP length. Fixed as `2'b00` |
| 19:18 | AT | Address Translation. Fixed as `2'b00` |
| 21:20 | Attr | Attributes. Fixed as `2'b00` |
| 22:22 | EP | Error Present — asserted if the transaction contains poisoned data. Fixed as `1'b0` |
| 23:23 | TD | TLP Digest — if asserted (=1), indicates presence of an ECRC field. Fixed as `1'b0` |
| 31:24 | Length[7:0] | Length of the TLP. Value of 1 = 1 DW; value of 2 = 2 DWs; value of 0 = 1024 DWs |
| 39:32 | Requester ID[15:8] | Upper byte of the Requester BDF ID |
| 71:64 | Target Route ID[15:8] | Upper byte of the BDF of the Target |
| 79:72 | Target Route ID[7:0] | Lower byte of the BDF of the Target |
| 87:80 | Vendor ID[15:8] | Upper byte of Vendor ID |
| 95:88 | Vendor ID[7:0] | Lower byte of Vendor ID. Fixed as `0x86` |
| 103:96 | SIO Protocol | SIO Protocol identifier. Fixed as `0x86` |
| 111:104 | SIO Target Pin# | Target SIO Pin number. Bit[7] = End of Message (EOM) flag |
| 119:112 | Dependent | Use of this field depends on the SIO Packet Type |

> **Note:** The Msg Code field value `0x7F` denotes a Vendor Defined Message. (§8.4.1.1)

---

#### Debug Services — PNR and Probe (§7.2.6.3, §7.2.6.4)

### Probe API (§7.2.6.3.2)

- The debug probe API exposes a function pointer `probe_ctrl_cb_t` for enabling, disabling, and configuring the probe via the following commands:
  - `PROBE_CMD_ENABLE`
  - `PROBE_CMD_DISABLE`
  - `PROBE_CMD_CONFIG`
- The "dump raw image in downscaled size" probe capability refers to the down-scaled RAW dump from CVISP — specifically after the Bayer Scaler and before LSC.

### PNR Service (§7.2.6.4)

- The PNR service processes commands and data requests from the host.
- It synchronizes with the Camera Configuration Service and the CVISP driver for camera data dump or injection operations.


### DMA Architecture (10 facts)

#### DMA Architecture

##### DMA Capabilities

(7.2.3.6.1 Capabilities)

- The NVU DMA driver implements a **subset of the Zephyr DMA driver API**; refer to the NVU DMA Driver documentation for the full list of supported Zephyr DMA API calls.
- Supported channel lifecycle operations include:
  - **Channel suspend**
  - **Channel resume / disable**

---

##### STU Async DMA Copy

(7.2.3.10.1 STU Driver API)

- The STU peripheral exposes an asynchronous DMA copy interface declared in `speed_stu.h`.
- The primary function fills an STU descriptor with a DMA copy request and issues an **async DMA copy** operation.
- Async DMA operations initiated from a WASM application post a result message back to the application via the message queue upon completion (11.8.2.2 How to post?).

---

##### HECI Bus Driver DMA Support

(5.3.3 HECI Bus Driver)

- The HECI Bus Driver supports DMA transfers for large inter-component messages.
- Upon driver load, **1 MB** is allocated for DMA usage.
- Messages **larger than 4 KB** (FW → host direction) are routed over DMA rather than the standard HECI messaging path.

---

##### Security Configuration and One-Way DMA

(9.2.2.1 Extra BUP Tasks; 5.5.3 FW Loading from Host)

- During the BUP (Boot Update Process) flow, NVU firmware applies a set of security configurations that directly constrain DMA operation:

| Security Setting | Effect |
|---|---|
| `IPC_DISABLE` | Cuts off IPC communication between NVU and host |
| `RS3_WR_DISABLE` | Enforces **one-way DMA** from NVU to host |

- Additional BUP security tasks relevant to DMA include:
  - Setup of NPX memory access controls
  - Isolation of USB SRAM
  - Configuration of **one-way IMR DMA**
  - Disconnection of the host interface for SW driver access

> **Note:** These security constraints are applied for reasons described in the NVU security architecture. RS3_WR_DISABLE in particular restricts DMA directionality to protect host-side memory regions.


### DSP Core (VPX2) (23 facts)

#### DSP Core (VPX2)

##### VPX2 Core Capabilities
(HAS §2.5.1.1.1)

- **Arithmetic & SIMD:** High-speed multiply, MAC, and vector-arithmetic (SIMD) options
- **Division:** Radix-4 divide option
- **Floating-Point:** Single-precision and double-precision floating-point options
- **Execution Modes:** User and kernel modes with efficient instruction execution
- **Memory Protection Unit (MPU):**
  - Programmable execute permission bits to enable or disable execution of code from specific memory regions
  - Programmable data read and write permission bits per memory region

---

##### Firmware Memory Layout
(HAS §7.1.1.1)

- VPX firmware is loaded at the **2 MB offset of SRAM**, containing text and data sections for BSP device drivers, RTOS, and services
- All VPX FW sections are executed and accessed exclusively by the VPX core
- **CV Shared Memory** is managed by CV Service running on VPX; WASM algorithm Apps or NN Service (as proxy of NPX) may request allocation or deallocation via the CV Service API

---

##### Memory Transfer (STU Driver)
(HAS §7.2.3.10.1)

- The STU driver is adapted from the Synopsys SPEED driver to meet NVU vmlib development requirements
- Used for memory transfers involving NVU SRAM across both NVU clusters: **VPX** and **NPX**

---

##### Cross-Core Communication: VPX ↔ NPX
(HAS §7.2.3.11.2.1)

**Architecture**

- VPX and NPX communicate via a **Doorbell + Shared Memory** architecture, eliminating busy-waiting and continuous polling
- The doorbell leverages the **ARCSync interrupt**, serving dual purposes: waking a sleeping peer core and delivering a notification

**VPX-to-NPX Message Flow**

1. VPX writes the command to the **command ring buffer** in shared memory
2. VPX asserts the **VPX2NPX doorbell** to wake and notify NPX

**NPX-to-VPX Response Flow**

1. NPX writes the response to the **response ring buffer** in shared memory
2. NPX asserts the **NPX2VPX doorbell** to notify VPX of completion

---

##### VPX/NPX IPC Protocol
(HAS §12.9.3)

**IPC Manager Data Structures**

| Field | Type | Description |
|---|---|---|
| `Context` | `CoreContext[NUM_CORES]` | Per-core execution context |
| `MessageContext` | `IPCMessage[NUM_CORES]` | Per-core IPC message state |
| `sharedMemory` | `CoreShareMemory*` | Pointer to inter-core shared memory region |

**IPC Manager API**

| API Name | Parameters | Description |
|---|---|---|
| `IPCManagerInit()` | `IPCManager* manager`, `uint32_t ShareMemAddress` | Initializes the IPCManager and sets VPX state to Ready |
| `IPCManagerCleanup()` | `IPCManager* manager` | De-initializes and cleans up the IPCManager |
| `IPCManagerIsNPXReady()` | `IPCManager* manager` | Performs handshake to check whether NPX is ready |
| `IPCManagerEncodeMessage()` | `IPCManager* manager`, `const IPCMessage* msg` | Encodes an IPC message for transmission to NPX |
| `IPCManagerDecodeMessage()` | `IPCManager* manager`, `IPCMessage* msg` | Decodes an IPC response received from NPX |

---

##### Debug and Logging
(HAS §7.2.6.1.5)

- For components running on the **VPX core**: use the Zephyr standard log API with the DTF Log frontend
- For components running on the **NPX core**: logs are written to a shared buffer; VPX core is then woken to read and forward log data via the Zephyr log API to DTF

---

##### WASM Application Framework on VPX
(HAS §11.6.1)

- The **Intel Core App** is always developed and signed by Intel, and is stitched directly into the Intel VPX FW image
- It is the only **system-privilege** WASM application and is responsible for managing all other WASM applications (Intel or third-party)

##### AOT Compilation for VPX2 Target
(HAS §12.6.2.3.2)

- The `nvu-wamr-sdk` toolchain file must be used in place of the standard `wasi-sdk` toolchain file; this disables unnecessary features such as **atomics** and **SIMD**, keeping applications lean
- AOT cross-compilation targets the VPX2 architecture using the MetaWare compiler with the following representative flags:
  - `WAMRC_LLC_COMPILER`: path to MetaWare `ccac` binary
  - `WAMRC_LLC_FLAGS`: `-Hoff=Emit_init_ad -tcf=vpx2_max -O3 -c`
  - `wamrc` invoked with `--bounds-checks=0 --target=arc`
- The `-Hoff=Emit_init_ad` flag suppresses MetaWare runtime STATUS register initialization; omit this flag only if manual STATUS register setup is not required

---

##### PCI Bus Driver Integration
(HAS §5.3.1)

- One Physical Device Object (PDO) exposed by the NVU PCI bus driver corresponds to the **NVU AON Vision HW logic**, encompassing both the VPX and NPX cores


### Debug and Trace (29 facts)

#### Debug and Trace

### Overview

The NVU debug and trace infrastructure spans multiple layers of the software stack, from host-side tools communicating over HECI, through BSP debug services running on Zephyr RTOS, to WASM application-level debug APIs. (Chapter 3: RTOS and BSP, Chapter 12: AON Vision FDK and Debug)

---

#### Host Interface and Driver Connectivity

- The NVU uses Zephyr as its Real-Time Operating System (RTOS); device drivers in the Board Support Package (BSP) are compiled with the Service Engine Driver Interface (SEDI). (7 Chapter 3: RTOS and BSP)
- Intel supplies a KMDF (Kernel Mode Driver Framework) HECI bus driver that provides the HECI protocol to other SW components in the system. (5 NVU Windows SW Architecture > 5.3.3 HECI Bus Driver)
- The HECI protocol allows software to open multiple bi-directional communication channels to NVU FW; usage of HECI clients in NVU includes FW loading, debug, and tuning. Each FW HECI client can only support one connection at a time. (5 NVU Windows SW Architecture > 5.3.3 HECI Bus Driver)
- NVU tools (profiling, debug, tuning, etc.) rely on the HECI bus driver to communicate with NVU FW in pre-production or debug systems. (5 NVU Windows SW Architecture > 5.3.3 HECI Bus Driver)
- In a production system, after boot, NVU BUP disables the host interface and the OED driver is disconnected correspondingly. (5 NVU Windows SW Architecture > 5.3.2 NVU OED Driver)
- If the SoC is unlocked (via OEM token-based unlock, Intel red unlock, or equivalent mechanisms), only a driver package with debug-signed FW can be used, and the host interface will not be disconnected after boot. (16 Chapter 12: AON Vision FDK and Debug > 16.2.4 Post-Production / Post-EOM Debug Flows)

---

#### Logging Service

##### General Log Usage

- Wasm Apps must not use `printf()` or similar functions directly; instead, they must use the log API. (11 Chapter 7: WAMR Framework > 11.8.6.1 Log API)
- The following log macros are provided for use in WASM applications: (11 Chapter 7: WAMR Framework > 11.8.6.1 Log API)
  - `LOG_DBG(fmt, ...)` — Debug-level messages
  - `LOG_INF(fmt, ...)` — Informational messages *(recommended for general information logging)*
  - `LOG_WRN(fmt, ...)` — Warning messages
  - `LOG_ERR(fmt, ...)` — Error messages

##### Dictionary-Based Logging

- Dictionary-based logging outputs log messages in binary format rather than human-readable text, reducing output bandwidth. (7 Chapter 3: RTOS and BSP > 7.2.6.1.4 Dictionary-based Logging)

##### Log to Host

- The log configuration client receives log-related commands and processes them in firmware. (7 Chapter 3: RTOS and BSP > 7.2.6.1.6 Log to Host)
- The **TraceConfig** tool is used on the host side to issue log-related commands. (7 Chapter 3: RTOS and BSP > 7.2.6.1.6 Log to Host)

---

#### Profiling Service

- The SMHI client in FW manages command handling and processing for requests initiated by the **NVU Profiling tool** on the host side. (7 Chapter 3: RTOS and BSP > 7.2.6.2 Profiling)
- For NN algorithm profiling details, refer to the Synopsys NN SDK User Guide for NPX. (16 Chapter 12: AON Vision FDK and Debug > 16.2.6 NN Algorithm Profiling)

---

#### Probe Service

##### Probe Protocol

The probe message header structure is defined as follows. (7 Chapter 3: RTOS and BSP > 7.2.6.3.1 Probe Protocol)

| Struct | Field | Type / Width | Description |
|---|---|---|---|
| `probe_msg_hdr_t` | `command` | `uint8_t:7` | Probe command ID (`probe_cmd_id_t`) |

##### Probe API (Native / BSP)

- The `ctrl_flag` output parameter provides additional information about the probe status. (7 Chapter 3: RTOS and BSP > 7.2.6.3.2 Probe API)
- **Throughput:** HW maximum supported bandwidth for the probe service is **1.6 GB/s**. Actual achievable throughput is to be evaluated (TODO item). (7 Chapter 3: RTOS and BSP > 7.2.6.3.2 Probe API)

##### WASM Probe API

The WASM probe API is used for image dump and probe data dump, following the design of the native Probe service. (11 Chapter 7: WAMR Framework > 11.8.6.2 Probe API)

**Probe Types:**

| Enum Value | Description |
|---|---|
| `DS_PROBE_TYPE_ALGO` | Algorithm-related debug data |

**WASM Probe API Functions:**

| Function Signature | Import Name | Description |
|---|---|---|
| `int32_t wasm_probe_status(int32_t type)` | `wasm_app_probe_status` | Query the status of a probe channel by type |
| `int32_t wasm_probe_send(int32_t type, int32_t buffer, int32_t length)` | `wasm_app_probe_send` | Send probe data of a given type from a buffer of the specified length |

Both functions are imported from module `"env"` via `__attribute__((__import_module__("env"), __import_name__(...)))`. (11 Chapter 7: WAMR Framework > 11.8.6.2 Probe API)

---

#### Telemetry API (WASM)

- Telemetry API for WASM applications is not yet defined; this is a pending TODO item. (11 Chapter 7: WAMR Framework > 11.8.6.3 Telemetry API)


### Error Handling and RAS (4 facts)

#### Crash Dump Retrieval (HAS §7.2.7)

- During the BUP (Bring-Up Phase), the host driver can retrieve crash dumps stored in AONRF (Always-On Retention Flash/Memory).

---

#### WASM Application Error Handling (HAS §11.8.2)

- If any exception or execution failure occurs during message processing, App Management will post a failure message back to the source application.
- If no failure occurs, the source application will wait for the result message.

#### WASM Message Dispatch and Response (HAS §11.8.2.1)

- Every WASM application must expose an exported function as its message entry point.
- All messages destined for a given app are dispatched to that exported entry function.
- Under normal operation, an app should always send a result message back to the caller upon completion.
- In failure scenarios, the app should return an appropriate failure response.

#### Application Restart on Failure (HAS §11.8.2.3)

- App Management will restart a failed application under either of the following conditions:
  - After the message handler function returns following an error.
  - Upon expiration of a watchdog or processing timeout.


### Firmware (1 facts)

#### MJPG Decoder & Post Processing

- For detailed API information, refer to the NVU Firmware Zephyr API document (7.2.3.14 MJPG Decoder & Post Processing)


### GPIO and Pin Mux (9 facts)

#### GPIO and Pin Mux

##### NVU GPIO Driver API
(Ref: Chapter 3: RTOS and BSP > 7.2.3.1 GPIO)

- The NVU GPIO driver implements a subset of the Zephyr GPIO driver API.
- Refer to the **NVU GPIO Driver** documentation for the full list of GPIO APIs supported in Zephyr.

---

##### Camera Sensor GPIO Configuration
(Ref: Chapter 4: Camera and ISP > 8.1.3.3 MIPI Camera Control via GPIO)

- GPIO-related settings for camera sensors are configured in BIOS and queried by the NVU SW driver during OS boot, alongside other camera configurations.
- The following GPIO parameters are configured per-pad:

| Parameter | Description |
|---|---|
| Community | GPIO community assignment |
| Group | GPIO group within the community |
| Pad | Specific pad identifier |
| Function | Pad mux function selection |
| Initial Value | GPIO output state at initialization |
| Active Value | GPIO logic level representing active state |

---

##### Camera Control Interface Sharing via Virtual GPIO (vGPIO)
(Ref: Chapter 4: Camera and ISP > 8.1.2 Camera Control Interface Sharing)

- Any device SW driver accessing IOs shared with the NVU **must coordinate with NVU** using virtual GPIOs (vGPIOs).
- The host SW driver implements a **release_req / release_ack handshake** with NVU firmware over vGPIOs.
- Requirement details are specified in **PCR16029668165 – [NVU] VGPIOs for IPU Sensor Driver ↔ NVU communication** (see also requirement id: 14027073645, owner: rchaddha, status: POR).

###### vGPIO Ownership Handshake Procedure

To acquire ownership of shared IOs, the host SW driver must:

1. Verify that **VGPIOx1** is cleared (NVU does not currently hold a release-ack pending).
2. Set **VGPIOx0** to assert the release request to NVU.
3. Wait for **VGPIOx1** to be asserted by NVU firmware, indicating NVU has released ownership.

###### vGPIO Resource Limits

| Parameter | Value |
|---|---|
| vGPIOs required per release_req/release_ack pair | 4 |
| Maximum vGPIOs supported by HW | 16 |
| Maximum concurrent device SW drivers supported | 4 |

---

##### GPIO Ownership: IPU vs. NVU
(Ref: IP-Specific Description > 8.7.2.1.7.3 MIPI Camera GPIO Sharing with IPU)

- Camera GPIO pins must be driven by either **IPU** or **NVU** depending on current camera ownership.
- When IPU holds camera ownership:
  - IPU uses the SoC GPIO controller in **GPIO mode** (`PMode = 0`).
  - IPU accesses GPIO registers via a **DDI (Direct Driver Interface)** with the GPIO driver.

---

##### Camera Config Service — Sensor GPIO Operations
(Ref: Chapter 3: RTOS and BSP > 7.2.4.1.1 MIPI Camera)

- The Camera Config Service exposes an API to perform combined sensor register and GPIO operations:

| API | Signature | Description |
|---|---|---|
| `cfg_svc_snsr_op` | `int cfg_svc_snsr_op(cfg_svc_snsr_op_param_t *snsr_op_param, uint32_t op_arr_size)` | Performs sensor register & GPIO operations |


### IOSF Bridge (253 facts)

#### IOSF Bridge

### Overview

The NVU IOSF Bridge provides the primary and sideband (SB) interface between the NVU and the SoC fabric. The NVU Host SW Driver is mapped to FN0 of the IOSF2AXI Bridge, exposing a 64KB BAR remapped to address range `0x8000_0000` via `_strap_axi_remap_address[0]` tie-off. (§8.2.6)

The SB driver should be common to Bringup. (§7.2.3.12.1)

---

#### IOSF Primary Interface Signals (§4.3.7.1)

##### Target (T) Control / Command Signals

| Group | Signal Name | Port Name | Direction | Width | Required | Description |
|---|---|---|---|---|---|---|
| TCONTROL | CREDIT_PUT | `nvu_iosf_prim_credit_put` | output | 1 | required | Credit Update Put: one clock cycle credit increment update pulse |
| TCONTROL | CREDIT_CHID | `nvu_iosf_prim_credit_chid` | output | TNUMCHANL2CREDIT+1 | required | Credit Update Channel ID |
| TCONTROL | CREDIT_RTYPE | `nvu_iosf_prim_credit_rtype` | output | 2 | required | Credit Update Request Type: specifies the request type of the specified channel when `CREDIT_DATA_RTYPE_CHID_ENABLED` is not set |
| TCOMMAND | TIDO | NOT_SUPPORTED | input | 1 | conditional | ID Based Ordering: asserted during command if transaction supports ID Based Ordering. Conditional on `SupportsIdBasedOrdering` |

##### Master (M) Control / Command Signals

| Group | Signal Name | Port Name | Direction | Width | Condition | Description |
|---|---|---|---|---|---|---|
| MCONTROL | GNT_TYPE | `nvu_iosf_prim_gnt_type` | input | 2 | conditional | Grant Type |
| MCONTROL | MCREDIT_PUT | NOT_SUPPORTED | input | 1 | `TTIF_ENABLED` | Master Credit Update Put: one clock cycle credit increment update pulse |
| MCONTROL | MCREDIT_CHID | NOT_SUPPORTED | input | MNUMCHANL2CREDIT+1 | `TTIF_ENABLED` | Master Credit Update Channel ID |
| MCONTROL | MCREDIT_RTYPE | NOT_SUPPORTED | input | 2 | `TTIF_ENABLED` | Master Credit Update Request Type: specifies the request type when `CREDIT_DATA_RTYPE_CHID_ENABLED` is not set |
| MCOMMAND | MIDO | NOT_SUPPORTED | output | 1 | `SupportsIdBasedOrdering` | ID Based Ordering: asserted during command if transaction supports ID Based Ordering |

---

#### IOSF Sideband (SB) Messages (§8.13.5)

| Message Name | Type | Opcode | Direction | Transaction Type | Addressing | Security | IRQ | Notes |
|---|---|---|---|---|---|---|---|---|
| Assert IRQn | Message with Data | 0x54 | out | Posted | Unicast | Check Security Section of HAS | yes (1) | Interrupt widget |
| De-assert IRQn | Message with Data | 0x55 | out | Posted | Unicast | Check Security Section of HAS | yes (1) | Interrupt widget |
| Sync Start Command | Message with Data | 0x50 | out | Posted | Unicast | Check Security Section of HAS | no | `time_sync_agent`; used in Hammock Harbor ART sync flow (§8.23.2.1) |

- Upon reception of `SyncStartCmd` from NVU, the ARU enqueues a request to provide the ART value. If the ARU is currently serving another HH agent, the `SyncStartCmd` is queued until the ARU is free. (§8.23.2.1)

---

#### IPC Register Map — `nvu_HOST_IPC_IOSF_Primary_Mem`

The IPC register block is accessible via the IOSF Primary memory BAR (MEM B?:D?:F?). All registers are 32-bit wide and reset on `FUNCRST`.

##### Interrupt Status Registers

**PISR_HOST2NVU** — Inbound Interrupt Status (read by NVU FW)

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| AGENT2NVU_DB | [0] | 0x0 | RO/V | AGENT2NVU Inbound Message Interrupt Status. `1` = DOORBELL BUSY interrupt is active |
| RESERVED1 | [26:1] | 0x0000000 | RO | Reserved |
| AGENT2NVU_BCISC | [27] | 0x0 | RW/1C/V | AGENT2NVU inbound message busy-clear interrupt status clear. Written by NVU FW to clear the interrupt status |
| RESERVED0 | [31:28] | 0x0 | RO | Reserved |

**PISR_NVU2HOST** — Outbound Interrupt Status (read by AGENT)

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| NVU2AGENT_DB | [0] | 0x0 | RO/V | NVU2AGENT Outbound message interrupt status. `1` = DOORBELL Busy Set interrupt is active |
| RESERVED1 | [7:1] | 0x00 | RO | Reserved |
| AGENT2NVU_BC | [8] | 0x0 | RW/1C/V | AGENT2NVU busy-clear interrupt status. `1` = NVU FW has cleared the AGENT2NVU Doorbell |
| RESERVED0 | [31:9] | 0x000000 | RO | Reserved |

---

##### Channel Interrupt Registers

**CIM_HOST** — AGENT Channel Interrupt Mask @ offset `0x0010` (ResetSignal: FUNCRST)

- Masks per-channel interrupts caused by any interrupt source for the channel.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_MASK | [0] | 0x0 | RW | Global interrupt enable toward FW for the channel. `0` = interrupt unmasked |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved |

**CIS_HOST** — AGENT Channel Interrupt Status @ offset `0x0014` (ResetSignal: FUNCRST)

- Provides per-channel interrupt status; set if any enabled interrupt source for the channel is asserted.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_STATUS | [0] | 0x0 | RO/V | Global interrupt status for FW interrupts on the channel. Set if any enabled interrupt source is active |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved |

---

##### Firmware / Communication Status Registers

**NVU_HOST_FWSTS_HOST** — AGENT Firmware Status @ offset `0x0034` (ResetSignal: FUNCRST)

- Writeable by NVU; read-only by AGENT.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| NVU_AGENT_FWSTS | [31:0] | 0x00000000 | RW | NVU AGENT firmware status. Written by NVU FW and read by AGENT |

**NVU_HOST_COMM_HOST** — AGENT Communication @ offset `0x0038` (ResetSignal: FUNCRST)

- Writeable by AGENT; read-only by NVU.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| AGENT_COMM | [31:0] | 0x00000000 | RW | AGENT communication register. Written by AGENT and read by NVU FW |

---

##### Doorbell Registers

**HOST2NVU_DOORBELL_HOST** — Inbound Doorbell (AGENT → NVU) @ offset `0x0048` (ResetSignal: FUNCRST)

- Inbound doorbell register used by AGENT to interrupt NVU.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |

**NVU2HOST_DOORBELL_HOST** — Outbound Doorbell (NVU → AGENT) @ offset `0x0054` (ResetSignal: FUNCRST)

- Outbound doorbell register used by NVU to interrupt AGENT.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility |
| BUSY | [31] | 0x0 | RW | When cleared, AGENT CPU is ready to accept a new message |

---

##### Outbound Inter-Processor Message Registers (NVU → AGENT)

All message registers are 32-bit, reset on `FUNCRST`, single field `MSG [31:0]` (Reset: `0x00000000`, Access: RW — "Message from NVU to AGENT").

| Register | Offset |
|---|---|
| NVU2HOST_MSG0_HOST | `0x0060` |
| NVU2HOST_MSG1_HOST | `0x0064` |
| NVU2HOST_MSG2_HOST | `0x0068` |
| NVU2HOST_MSG3_HOST | `0x006C` |
| NVU2HOST_MSG4_HOST | `0x0070` |
| NVU2HOST_MSG5_HOST | `0x0074` |
| NVU2HOST_MSG6_HOST | `0x0078` |
| NVU2HOST_MSG7_HOST | `0x007C` |
| NVU2HOST_MSG8_HOST | `0x0080` |
| NVU2HOST_MSG9_HOST | `0x0084` |
| NVU2HOST_MSG10_HOST | `0x0088` |
| NVU2HOST_MSG11_HOST | `0x008C` |
| NVU2HOST_MSG12_HOST | `0x0090` |
| NVU2HOST_MSG13_HOST | `0x0094` |
| NVU2HOST_MSG14_HOST | `0x0098` |
| NVU2HOST_MSG15_HOST | `0x009C` |
| NVU2HOST_MSG16_HOST | `0x00A0` |
| NVU2HOST_MSG17_HOST | `0x00A4` |


### IPC Messaging (84 facts)

#### IPC Messaging

### Overview

(7.2.3.11.1, 14.3.1, 14.3.2)

- The NVU IPC driver implements a subset of the Zephyr IPC driver API; refer to the NVU IPC Driver documentation for the supported API set.
- Raw data communication uses IPC DoorBell (DB) and Data registers based on the IPC protocol.
- The IPC protocol between NVU FW and ISH FW is privately defined by Intel and is not disclosed to third parties; it is used exclusively between Intel FW components.

---

#### NVU–ISH IPC Layer Communication

(14.3.2)

The IPC layer between NVU and ISH supports two sub-protocols:

- **IPC Protocol (Standard Long Format):** Communicates payload from upper layers via IPC DoorBell (DB) and Data registers.
- **IPC Reset Protocol:** Managed via the CSR register.

---

#### IPC Reset Protocol

(14.3.2.1)

- NVU takes the **Leader** role; ISH takes the **Follower** role.
- The IPC validity protocol is **not supported**. Upon an IPC request/interrupt, the IP is expected to exit Power Gating (PG) if entered, and guarantee the validity of IPC registers (doorbell and data registers).
- Refer to the Embedded Engines IPC HAS for full details (guidelines, high-level flow, detailed flow) on the IPC Reset Protocol.
- The CSR register definition is specified in the Embedded Engines IPC HAS. **Note:** bits 4–31 of the CSR register are not used.

---

#### IPC Protocol — Doorbell Header (Standard Long Format)

(14.3.2.2)

- The IPC header is placed into the IPC doorbell register.
- The doorbell structure follows the **Standard Long Format** as defined in the Embedded Engines IPC HAS.
- For ISH–PeerIP IPC Protocol, `SHORT_FORMAT`, `CUSTOM_FORMAT`, `BITS_18_16`, `BITS_30_29`, `RSVD_25_24`, and `CLIENT_ID` must all be set to **0**.

##### IPC Header Field Definitions

| Bits | Field | Reset | Description |
|------|-------|-------|-------------|
| 9:0 | `PAYLOAD_SIZE` | — | Number of bytes of payload provided in the data registers. If size is not a multiple of dwords, data in the last register is placed in Little Endian format (LSB first, i.e., bits 7:0). |
| 15:10 | `CLIENT_ID` | 0 | ID of the sending and receiving client. **Note:** Reserved as 0 for ISH-PeerIP IPC Protocol. See CLIENT_ID value table below. |
| 18:16 | `BITS_18_16` | 0 | IP Pair specific. **Note:** Reserved as 0 for ISH-PeerIP IPC Protocol. |
| 23:19 | `LONG_FORMAT_VER` | 0 | Long format version. In this version of the specification, value is `0x0`. |
| 25:24 | `RSVD_25_24` | 0 | Reserved. **Note:** Reserved as 0 for ISH-PeerIP IPC Protocol. |
| 26:26 | `FLOW_CTRL_INFO_REQ` | 0 | If flow control is enabled between drivers: `0` = Do not send back a flow control message; `1` = Send back a flow control information message. |
| 27:27 | `SHORT_FORMAT` | 0 | `0` = Standard Long Format; `1` = Standard Short Format. **Note:** Set as 0 for ISH-PeerIP IPC Protocol. |
| 28:28 | `CUSTOM_FORMAT` | 0 | `0` = Standard Format. **Note:** Set as 0 for ISH-PeerIP IPC Protocol. |
| 30:29 | `BITS_30_29` | 0 | IP Pair specific. **Note:** Reserved as 0 for ISH-PeerIP IPC Protocol. |
| 31:31 | `BUSY` | — | `1` = IPC message sent for receiver to consume. |

##### CLIENT_ID Value Definitions

(14.3.2.2)

| Value | Definition |
|-------|------------|
| 0x00–0x2F | Custom defined clients between IP pairs |
| 0x30 (48) | IPC driver |
| 0x31 (49) | MCTP |
| 0x32–0x3F | Reserved for future standard IPC clients |

---

#### HECI Transport Protocol — IPC Message Header

(7.2.3.16.1)

The HECI transport layer uses its own IPC message header structure layered above the IPC doorbell.

##### HECI IPC Message Header Fields (C Bitfield Layout)

| Field | Size (bits) | Description |
|-------|-------------|-------------|
| `length` | 10 | Message length |
| `protocol` | 4 | Protocol identifier |
| `reserved` | 6 | Reserved |
| `length1` | 4 | Extended length field |
| `core_id` | 4 | Core identifier |
| `reserved` | 3 | Reserved |
| `busy` | 1 | Doorbell busy bit |


### Inference Engine (1 facts)

#### Memory Management – SMMU and Virtual Memory Access

*(HAS §7 Chapter 3: RTOS and BSP > 7.1 RTOS > 7.1.1 Memory Management > 7.1.1.2 Memory Access)*

- The SMMU (System Memory Management Unit) does **not** support on-demand paging by hardware design.
- To utilize VMEM (Virtual Memory), all memory mappings in the page tables must be managed by firmware (FW) in a **predictable, pre-planned manner**.
- FW is responsible for ensuring that required mappings are established prior to access in order to **avoid page faults** at runtime.
- This constraint is a deliberate **design simplicity** choice — the hardware offloads paging management responsibility entirely to firmware.


### Interrupt Configuration (2 facts)

#### Panic Mode Support

- For error conditions where the scheduler or interrupts do not work, the logging subsystem can be switched to **panic mode** by triggering the `log_panic()` API (7 Chapter 3: RTOS and BSP > 7.2.6.1.3 Key Features)
- Upon entering panic mode, all standard interrupt-dependent logging mechanisms are bypassed to ensure diagnostic output is preserved

#### Host Interrupts — NVU Software Driver

- The **NVU Software Driver** interrupt context is **only active during NVU boot** (8 IP-Specific Description > 8.1 Interrupts > 8.1.3 Host Interrupts)
- Once the NVU boot sequence completes, this interrupt source is deactivated


### Neural Network Accelerator (55 facts)

### Neural Network Accelerator

#### Overview

The following sections describe the programming model and firmware interface for the Intel NVU Neural Network Accelerator, providing guidance for SW and FW driver development based on the HW implementation. (HAS §21.1)

---

#### Reference Documents

| Document | Location |
|---|---|
| NVU OED + HECI Driver Design and Firmware Interface | [Link] |
| NVU Firmware Zephyr API | [Link] |

---

#### Host IPC Doorbell Register

(HAS §CRIF: nvu_HOST_IPC_IOSF_Primary_Mem)

| Name | Offset/Bits | Size | Reset | Access | Description |
|---|---|---|---|---|---|
| HOST2NVU_DOORBELL_HOST.BUSY | [31] | 1 | 0x0 | RW | AGENT sets this bit to indicate a new message has been written in the payload registers. Cleared by FW once it has processed the message. |

---

#### IOSF Primary Host Interface Signals

(HAS §4.3.7.1)

| Name | Consumer | Direction | Width | Presence |
|---|---|---|---|---|
| MCOMMAND | MTD | Output | 1 | Optional-Conditional |
| TCOMMAND | TTD | Input | 1 | Optional-Conditional |

---

#### MSI Interrupt Handling

(HAS §8.1.4.1)

- Upon receiving an MSI interrupt, the host driver **must**:
  1. Set the global mask (within the IP) to clear the interrupt to the MSI_GEN block.
  2. Service the interrupt.
  3. Clear the global mask to enable new interrupts.

---

#### HECI Bus Driver

(HAS §5.3.3)

- Upon HECI reset, the driver removes the exposed device and re-adds it once the reset completes.
- S3/S4 power transitions cause NVU FW reset, resulting in HECI disconnect and reconnect cycles.

---

#### Firmware Loading from Host

(HAS §5.5.3)

- NVU FW has **two images**: base FW and app FW, each of which may be signed by Intel or OEM.
- ISH FW has a single OEM-signed image for the SW driver; the image is stitched.
- In the NVU threat model, third-party BIOS is **not trusted**; therefore, the NVU boot flow includes additional SRAM/IMR copy and SHA value generation/comparison to ensure IMR content integrity for the SW driver.

---

#### SPI Peripheral Driver

(HAS §7.2.3.5)

- SPI is **not POR** (Plan of Record) for NVU firmware.
- The SPI driver will **not** be enabled in NVU production firmware.

---

#### IOSF SideBand Endpoint Transactions

(HAS §7.2.3.12.1)

- VNN **must be ON** before initiating any sideband transaction.
- The driver will **test** that VNN is ON but will **not** turn it on or off per transaction, as toggling VNN for each sent dword may negatively impact performance.

---

#### NN Offload Service

(HAS §12.9.2)

- Computer vision and neural network acceleration services are managed through offload API wrappers, with the Core App orchestrating the execution pipeline and managing data dependencies. (HAS §11.3.1)

**NN Service API**

| API Name | Parameters | Description |
|---|---|---|
| `nn_service_notify_workload_result()` | `model_context* model_ctx` | Notifies the caller that NN inference has completed. |

**NN Offload Behavioral Notes:**

- Face detection performs pre-processing, then requests the NN service to switch the NN model via native APIs through the WASM face detection app entry point. (HAS §12.7.5)
- Face tracking follows the same pattern: pre-processing is performed first, then an NN model switch is requested through the NN service via native APIs. (HAS §12.7.5)
- NN offload callbacks, CV/DSP offload callbacks, and face ID vector management APIs (add/remove/update stored face ID vectors, measure distance with stored face ID vectors) are defined within the WASM Offload Service APIs. (HAS §11.8.5)

---

#### CV Service

(HAS §12.10.1, §12.10.2)

**CV Processing Functions**

| API | Description |
|---|---|
| `int cv_svc_vec_norm_f32(const float *in_vec1, const float *in_vec2, uint16_t vec_len, float *output)` | Calculates the L2 norm of the difference between two float vectors. |

**CV Shared Memory Management**

| API | Called By | Description |
|---|---|---|
| `cv_aligned_alloc` | WASM app | Convenience allocation with `0x40` alignment for NN inputs and outputs. May also be used for pre/post intermediate buffers. |

---

#### Face ID Vectors Protection

(HAS §12.4.2)

- The Face ID app does **not** have direct read/write access to stored face ID vectors in SRAM.
- When performing face ID matching computation, the Face ID app must call corresponding APIs to the DSP offload service.

---

#### WAMR Framework and NN Integration

(HAS §11.3.1, §11.3.4.1, §11.4.2, §11.5.2, §11.8.1, §11.8.2)

**Initialization**

- WAMR runtime initialization creates the WAMR global heap as a Zephyr heap accessible from WAMR user-mode threads; all WAMR dynamic memory allocation occurs within this heap. (HAS §11.4.2)
- The `app_mgmt_wasm_init()` function completes WASM app initialization by calling: `wasm_runtime_load()`, plus three additional WASM APIs. (HAS §11.8.1)
- `wasm_runtime_load()` parses and validates WASM binary modules (raw content format loaded from IMR storage to SRAM by BUP), including comprehensive security checks. (HAS §11.3.1)

**Shared Memory**

- Shared heaps are created in the App Manager via `wasm_runtime_create_shared_heap(SharedHeapInitArgs *init_args)`; the creation mode depends on the supplied `init_args`. (HAS §11.5.2)

**App Lifecycle**

- **Instantiated & Enabled:** The active app entity tree is created and corresponding WASM apps are instantiated. App Management creates the WAMR module instance and execution environment. (HAS §12.4.1)
- **Disabled & De-instantiated:** After a branch in the active app entity tree is deactivated, the corresponding WASM app is de-instantiated, the WAMR instance is destroyed, and the app linear/local memory is released. (HAS §12.4.1)

**Performance and Blocking**

- All apps and App Management run in the **same** Zephyr user-mode thread; an app that takes too long to process a message will block other apps and App Management. Apps should always process messages promptly. (HAS §11.8.2)

---

#### WAMR AOT Compilation

(HAS §12.6.2.1, §12.6.2.2, §12.6.2.3)

- WAMR supports multiple execution modes: **interpreter**, **JIT** (Just-In-Time), and **AOT** (Ahead-of-Time) compilation, to balance performance and resource usage. (HAS §12.6.2.1)
- The WAMR AOT compiler (`wamrc`) compiles a `.wasm` binary into an AOT native module (`.aot` file in WAMR-defined format) for maximum performance. (HAS §12.6.2.1)
- AOT modules maintain full WebAssembly semantics: memory isolation, sandboxed host calls (user-controlled limited API interface), and deterministic behavior. (HAS §12.6.2.2)
- `wamrc` uses LLVM to compile WASM bytecode to AOT; third-party toolchains may be used to take over specific compilation steps where required. (HAS §12.6.2.3.2)
- In the NVU scenario, since Metaware is an LLVM-based toolchain, LLVM PGO (Profile-Guided Optimization) may in theory be used for static profile-guided AOT optimization. Refer to WAMR documentation for usage details. (HAS §12.6.2.3.4)

---

#### NVU WAMR SDK

(HAS §12.6.1)

- The NVU WAMR SDK is a comprehensive toolkit for Wasm application development within the NVU ecosystem. (HAS §12.6.1)
- Provides custom headers and libraries replacing those from `wasi-sdk`, focusing on essential APIs to reduce binary size and optimize performance. (HAS §12.6.1.1)
- Includes a simulation environment enabling thorough application testing, verification of functional outputs, and adherence to the expected application framework; the simulation environment can be integrated into CI systems and other testing environments (e.g., fuzzing tests). (HAS §12.6.1.2)
- Includes performance measurement and tuning tools to assess and optimize key metrics including: **binary size**, **heap memory usage**, and **stack memory usage**. (HAS §12.6.1.3)

---

#### NVU-ISH Communication Protocol

(HAS §14.3.2.1, §14.3.3.1.1)

- ISH and NVU must support the **IPC Reset Protocol** per IPC compliance requirements.
- IPC in-band messages occur **only after** the IPC reset handshake completes. (HAS §14.3.2.1)

**Version Handshake Request** (HAS §14.3.3.1.1)

| IPC Reg | Bits | Field | Value | Comment |
|---|---|---|---|---|
| DATA0 | 7:0 | sequence_num | 0 | — |
| DATA0 | 15:8 | capability_id | 0 | Protocol Control |
| DATA0 | 22:16 | message_type | 0 | Version Handshake |
| DATA0 | 23 | is_response | 0 | Request |
| DATA0 | 31:24 | reserved | — | — |

**Version Handshake Response** (HAS §14.3.3.1.1)

| IPC Reg | Bits | Field | Value | Comment |
|---|---|---|---|---|
| DATA0 | 7:0 | sequence_num | 0 | — |
| DATA0 | 15:8 | capability_id | 0 | Protocol Control |
| DATA0 | 22:16 | message_type | 0 | Version Handshake |
| DATA0 | 23 | is_response | 1 | Response |
| DATA0 | 31:24 | reserved | — | — |

---

#### Debug Services

(HAS §7.2.6.1.2, §7.2.6.3.2)

- The **Default Frontend** is engaged when a logging API is called at the logging source (e.g., `LOG_INF`) and is responsible for filtering messages at compile time and run time, and allocating log buffers. (HAS §7.2.6.1.2)
- Both probe data and log timestamps are **synchronized to the Hammock Harbor timestamp reference**, enabling synchronization between traces and probe data. (HAS §7.2.6.3.2)

**Logging Best Practices** (HAS §11.8.6.1)

- Use appropriate log levels based on message importance to aid log filtering and analysis.
- Avoid excessive logging, especially in performance-critical code sections, to reduce log size and improve performance.
- In production builds, consider disabling all log levels except error-level logs.

---

#### Power Management — Peripheral Drivers

(HAS §13.5.4)

- Peripheral drivers are responsible for managing their own power state transitions, with assistance from APIs provided by PM


### NoC Fabric (19 facts)

#### NoC Fabric

##### Overview

The NVU NoC (Network-on-Chip) Fabric provides the interconnect infrastructure for on-chip communication between IP blocks, managing transaction routing, protocol bridging, and bandwidth allocation across clock domains.

---

#### IOSF Primary Interface Signals (4 IP Configuration > 4.3 Interfaces > 4.3.7 Host Interfaces > 4.3.7.1 IOSF Primary)

The NoC Fabric exposes an IOSF Primary interface with the following command and control signals:

| Group | Signal Name | RTL Port Name | Direction | Width | Requirement | Condition | Description |
|---|---|---|---|---|---|---|---|
| MCONTROL | GNT_TYPE | nvu_iosf_prim_gnt_type | input | 2 | conditional | NA | Grant Type. Asserted by the fabric to indicate the grant type. |
| MCOMMAND | MADDRESS | nvu_iosf_prim_maddress | output | MMAX_ADDR+1 | required | NA | Address. Specifies the Transaction Address. For memory and IO transactions, contains the address. For Completions, see spec. |
| TCOMMAND | CMD_CHID | nvu_iosf_prim_cmd_chid | input | TNUMCHANL2+1 | conditional | (TNUMCHAN!=0) | Command Channel ID. Asserted by the fabric with the command put to identify the targeted channel of the command. |
| TCOMMAND | TADDRESS | nvu_iosf_prim_taddress | input | TMAX_ADDR+1 | required | NA | Address. Specifies the Transaction Address. For memory and IO transactions, contains the address. For Completions, see spec. |
| TCOMMAND | TCPARITY | NOT_SUPPORTED | input | 1 | conditional | PARITY_REQUIRED | Command Parity. Specifies even parity command bus input. Only required on agents implementing the optional command parity feature. |

- **MADDRESS / TADDRESS** carry the full transaction address for both memory/IO transactions and completions.
- **MCMD_CHID / CMD_CHID** are conditionally present, dependent on multi-channel configuration parameters (`MNUMCHAN`, `TNUMCHAN`) and TTIF enablement.
- **TCPARITY** is conditionally supported and is **NOT_SUPPORTED** in the current NVU configuration; it is only instantiated when `PARITY_REQUIRED` is asserted.

---

#### NoC Fabric Targets (8 IP-Specific Description > 8.10 NOC Fabric > 8.10.2 Targets)

The following table lists the registered NoC Fabric targets:

| Target IP | Name | Protocol | Unique Name | Target Group | Clock Domain (MHz) | Max Frequency (MHz) | Data Width (B) | Burst Size (B) | Read BW (GB/s) |
|---|---|---|---|---|---|---|---|---|---|
| IPC | REG | APB | IPC_REG | DUAL | 200 | 200 | 4 | 4 | 0.8 |

- The IPC register target operates over the **APB** protocol.
- The **DUAL** target group designation indicates the target is accessible from two fabric initiator domains.
- Clock domain is fixed at **200 MHz**, with a maximum operating frequency of **200 MHz**.
- Data width is **4 bytes** with a matching burst size of **4 bytes**, yielding a read bandwidth of **0.8 GB/s**.

---

#### IOSF Sideband (SB) Interface (8 IP-Specific Description > 8.13 IOSF-SB interface > 8.13.5 List of SB Messages supported)

The NVU exposes an IOSF Sideband Endpoint (SBEP) as a **source** agent on the SB fabric.

- **MARS Reference:** `ip_sb_messages_client_soc-v1`
- **EP Name:** NVU
- **Payload Bus Width:** 8 bits
- **Port ID Width:** 16 bits
- **Port ID Count:** 1
- **Port Domain / Port Name:** `nvu`


### PMC Integration and Wake (106 facts)

#### PMC Integration and Wake

> **Note:** The facts provided do not contain direct register/field data or behavioral specifications specific to a 'PMC Integration and Wake' sub-section of the NVU driver. The following content is synthesized from the PMC-relevant facts available in the provided HAS fact set.

---

#### IPC Communication Channels (7.2.3.11)

NVU maintains IPC communication with the following entities, including PMC:

- **NVU ↔ Host (NVU Driver)**
- **NVU ↔ ESE**
- **NVU ↔ ISH**
- **NVU ↔ PMC**

These cross-core communication channels are defined as part of the BSP Peripheral layer (7.2.3.11).

---

#### PMC Telemetry and Platform Monitoring Technology (11.6.3)

- PMC telemetry data generated during NVU operation can later be retrieved by the **IPF Platform Monitoring Technology (PMT)** provider.
- PMT exposes this telemetry data to **host software clients**.
- This mechanism enables post-hoc monitoring and analysis of NVU activity as observed by the PMC.

---

#### Cross-Core API Access for PMC Interaction (12.2.2)

The **Core App** requires access to WAMR Cross-Core Communication APIs, which include support for:

- ISH command and response handling
- Result posting
- Threat reporting to ESE

These APIs form the interface layer through which NVU firmware components interact with adjacent cores, including the PMC communication path.

| App Type | PMC/Cross-Core API Access |
|---|---|
| Core App | WAMR Cross-Core Communication APIs (ISH command, response, result post, ESE threat report) |
| Algorithm App | No cross-core or PMC APIs; limited to WAMR Common APIs and WAMR Offload Service APIs |
| 3rd-party App | Defined per privilege level; no direct PMC API access documented |

(12.2.2, 12.4)


### Peripheral Interfaces (36 facts)

#### I2C Controller

##### Driver API (7.2.3.2)

- The NVU I2C driver implements a subset of the Zephyr I2C driver API. Refer to the NVU I2C Driver documentation for the full list of supported Zephyr I2C APIs.
- Driver applications use GPIOs to control camera power/reset and the I2C master to program camera sensor configurations. (7.2.4.1.1)
- I2C/I3C-related settings (bus, slave address, speed, function) are configured in BIOS and queried by the NVU SW driver during OS boot, along with other camera configurations. (8.1.3.2)

##### I2C Controller Configuration (8.17.3)

| Name | Type | Default Value | Description |
|------|------|---------------|-------------|
| SLAVE_INTERFACE_TYPE | uint32 | 0 | APB2 |
| IC_ADD_ENCODED_PARAMS | uint32 | 0x1 | Allows driver re-use across DW components |
| IC_SMBUS_SUSPEND_ALERT | uint32 | 0x0 | No suspend/alert support |

---

#### I3C Controller

##### Driver API and Production Status (7.2.3.3)

- The I3C driver implements a subset of the Zephyr I3C driver API. Refer to the I3C Driver documentation for the full list of supported Zephyr I3C APIs.
- The ENTDAA CCC command is **not supported**. An I3C sensor/device can normally operate in either I3C mode or I2C mode. In I3C mode there are two CCC command methods for the I3C controller to assign a dynamic address; ENTDAA is not among the supported ones.
- Since I3C is not POR (Plan of Record) for FW, the I3C driver will **not** be enabled in NVU production firmware.

##### I3C Controller Parameters (8.20.4)

| Name | Type | Default Value | Description |
|------|------|---------------|-------------|
| IC_DEVICE_ROLE | uint32 | 1 | Master Only |
| IC_HAS_HCI | uint32 | 1 | HCI Compliant |
| IC_DFLT_RX_START_THLD | uint32 | 3'h1 | 4 — set to half of RX Command Buffer depth |
| IC_DFLT_TX_START_THLD | uint32 | 3'h1 | 4 — set to half of TX Command Buffer depth |
| IC_DFLT_RX_BUF_THLD | uint32 | 3'h4 | 32 — set to half of RX buffer depth |

---

#### UART Controller

##### Driver API and Production Status (7.2.3.4)

- The UART driver implements a subset of the Zephyr UART driver API. Refer to the UART Driver documentation for the full list of supported Zephyr UART APIs.
- Since UART is not POR for FW, the UART driver will **not** be enabled in NVU production firmware.
- In post-production/post-EOM debug flows where the SoC is locked, only a driver package with production-signed FW can be used; UART log output is not available in this state. (16.2.4)

##### UART IO Interface Signals (4.3.12.5)

| Signal Name | Direction | Count | Required | Reset Domain | Sync/Async | Drive Edge | Description |
|-------------|-----------|-------|----------|--------------|------------|------------|-------------|
| nvu_uart_cts_n | input | NUM_UART | required | nvu_prim_rst_b | async | rise_edge | UART Clear To Send |
| nvu_uart_sin | input | NUM_UART | required | nvu_prim_rst_b | async | rise_edge | UART Serial Input |
| nvu_uart_de | output | NUM_UART | required | nvu_prim_rst_b | async | rise_edge | UART Driver Enable |

---

#### Camera Control Interface Sharing — I2C/I3C and GPIO

##### Bus Allocation Guidelines (8.1.2)

- The I2C/I3C bus shared with NVU to control the User Facing (UF) RGB camera **must not** be connected to other devices. A dedicated I2C/I3C bus must be allocated for the UF RGB camera used by NVU.
- If the OEM connects multiple cameras or flash devices to a single I2C/I3C bus, an additional virtual GPIO-based handshake (request/acknowledge) mechanism is required because the Camera Sensor SW driver needs sensor access independently of the IPU.
- For HW design details of the GPIO handshake, refer to *GPIO as Wake for sensor driver requesting/relinquishing shared I2C GPIO* in the NVU HAS.

##### I2C/I3C Sharing with IPU (8.7.2.1.7.2)

- The I2C/I3C interface of the camera must be available to both NVU and IPU based on ownership.
- The IPU uses any of the LPSS 6×I2C / 4×I3C interfaces via driver-to-driver communication between the IP SW driver and the LPSS I2C controller.
- The IPU sensor driver controls the I2C and GPIO lines connected to MIPI cameras. (8.21.5)
- The IPU sensor driver does not have a SW interface to communicate with the IPU camera driver; therefore the standard release/claim/owner handshake cannot be used as it is controlled by the IPU camera driver. (8.21.5)

##### Virtual GPIO 4-Way Handshake Sequence (8.21.5)

- 16 virtual GPIOs are allocated on the platform to establish a 4-way handshake interface between the IPU sensor driver and NVU.
- **Step 1 — Request:** When the IPU sensor driver wants to take ownership of the shared I2C bus, it writes to a VGPIO pin to assert `release_req`.
- **Step 2 — NVU Wake:** The SoC routes this VGPIO output to a VGPIO input connected to an NVU GPIO, asserting the NVU GPIO. NVU HW triggers a wake event via this GPIO.
- **Step 3 — Quiesce:** NVU FW wakes and performs the necessary steps to place the I2C/GPIO lines into a quiescent state.
- **Step 4 — Acknowledge:** NVU FW programs another NVU GPIO (connected to a VGPIO) to assert `release_ack`.
- **Step 5 — IPU Receives ACK:** The IPU sensor driver receives `release_ack` as a GPIO toggle IRQ via the corresponding VGPIO input connected to the NVU GPIO output.
- **Step 6 — Handshake Complete:** The IPU sensor driver is notified that it may take the shared I2C resource. It de-asserts `release_req`; NVU in turn de-asserts `release_ack`, completing the handshake.

---

#### IPC D0i3 Control Register — Host Interface (CRIF: nvu_HOST_IPC_IOSF_Primary_Mem)

##### Register: IPC_d0i3C_HOST

| Property | Value |
|----------|-------|
| Offset | 0x0000_06D0 |
| Size | 32 bits |
| Reset Signal | FUNCRST |
| Description | D0i3 Control For AGENT — used for D0i3 SW flow |

##### Fields

| Field Name | Bits | Reset | Access | Description |
|------------|------|-------|--------|-------------|
| CIP | [0] | 0x0 | RW/1C/V | HW sets this bit on a 1→0 or 0→1 transition of the D0i3 bit. While set, all other bits in this register are not valid and writing D0i3 is illegal. |
| IRC | [4] | 0x0 | RO/V | Set to 1 by HW if capable of generating an interrupt on command completion, else 0. For NVU this bit is tied to 0. |
| RESERVED0 | [31:5] | 0x000_0000 | RO | Reserved. |


### Power States (2 facts)

#### Firmware Components and Roles

(HAS: Chapter 9 § 13.5, § 13.5.3)

- NVU Power Management requires close coordination between the following firmware components to achieve various low-power states and support transaction flows:
  - **AON Task** — always-on task responsible for maintaining state across power transitions
  - **Boot ROM** — involved in power state initialization sequences
  - **PM Driver** — provides centralized power and clock management APIs
  - **Peripheral Drivers** — consume PM Driver APIs to manage device-level power states

#### PM Driver Responsibilities

(HAS: Chapter 9 § 13.5.3)

The PM Driver is responsible for providing common APIs to the following consumers:

- Other peripheral drivers
- OSPM (OS Power Management)
- Services and Applications

These APIs manage the following system and device resources:

- **Clock management** — system and device clock control
- **Power management** — system and device power control
- **D0ix entry/exit flow** — device active sub-state transitions
- **Sx entry/exit flow** — system sleep state transitions


### Register Details (1 facts)

#### Native API Registration

- Native API wrappers are registered through `wasm_runtime_register_natives()` to expose controlled system functionality to WASM applications (11.3.1)


### SRAM and Memory (33 facts)

#### SRAM Sub-System Overview

The NVU SRAM sub-system encompasses internal SRAM storage, a SHA384 hardware accelerator, and memory management interfaces used by firmware and application layers. The following sections describe the key sub-blocks and their programming interfaces.

---

#### SHA384 Hardware Accelerator (8.6.4.5)

The SRAM sub-system includes a Secure HASH Algorithm (SHA384) accelerator sub-block accessible to NVU firmware.

##### HASH Context Save and Resume (8.6.4.5.3)

- FW can suspend a SHA operation and save its context for later resumption.
- To resume a saved SHA context, FW must:
  - Program the saved hash result into the **SHAIVDWx** registers.
  - Program the saved accumulated length into the **SHAALDWx** registers.
  - Set **SHACTL.EN** = 1 with **SHACTL.HRSM** asserted to indicate resume mode.
  - Use **SHACTL.HFM** to configure the hash final-message behavior as required.
- Two resume flow variants are supported (8.6.4.5.2):
  - **HASH resume mode (multiple chunks):** Resumes a single HASH operation across multiple data chunks.
  - **HASH resume with process switch:** The HASH engine is switched between two concurrent HASH tasks mid-operation.
- **Note:** The HAS spec text at §8.6.4.5.2.2 contains a known typo — "HAS engine" should read "HASH engine."

##### Key Control Fields Referenced in HASH Resume

| Field | Register | Description |
|---|---|---|
| `EN` | `SHACTL` | Enable bit; set to 1 to start or resume a HASH operation |
| `HRSM` | `SHACTL` | Hash Resume Mode; assert when resuming from a saved context |
| `HFM` | `SHACTL` | Hash Final-Message mode control |

##### IMR Write Protection (8.6.4.5.3)

- **SRAMSS_VMEM_WRITE_SUPPORT:** No action is required from the SRAM sub-system to disable writes to IMR.
- After boot completion, security registers are updated by firmware to block writes to the IMR bridge.

---

#### CV Shared Memory Management (12.10.2)

The CV service layer manages shared SRAM resources between WASM applications and internal NVU services.

##### Memory Alignment Requirement
- All SRAM resource allocations are **4 KiB aligned**.

##### CV Shared Memory APIs

| API | Called By | Description |
|---|---|---|
| `cv_preload_res` | WASM app | Preloads a resource (e.g., NN model) from IMR to SRAM (4 KiB aligned). If already loaded, preloading is skipped. |
| `cv_get_res` | NN Service | Obtains a resource's base address in SRAM (4 KiB aligned) and its actual byte size for execution. |

##### CV Status Codes (12.10.2)

| Value | Symbol | Description |
|---|---|---|
| `0` | `CV_OK` | Success |
| `1` | `CV_EPARAM` | Invalid parameter (e.g., null pointer, size == 0) |
| `2` | `CV_EMEM` | Out of memory |

---

#### NN Offload Service — Model Load API (12.9.2)

| API Name | Parameters | Description |
|---|---|---|
| `nn_service_request_model_load()` | `uint32_t model_id`, `uint32_t* model_addr`, `uint32_t model_size` | Requests the BSP service to load a neural network model from IMR into SRAM. |

---

#### Face ID Vector Protection in SRAM (12.4.2)

- During face ID enrollment, the algorithm application generates new face ID vectors in WAMR shared memory after updating face ID vectors in local SRAM.
- Encryption is applied after enrollment to protect the stored face ID vectors.

---

#### STU Driver — Transfer Wait API (7.2.3.10.1)

- **`speed_stu_WaitE(ev)`** — Blocks until the STU transfer corresponding to the specified event has completed.
  - Header file: `speed_stu.h`
  - Parameter `ev`: the event handle corresponding to the STU transfer request to wait on.

---

#### Security: Zephyr User/Kernel Mode Partition (10.2.2)

- The Zephyr RTOS user mode / kernel mode partition is enabled on the NVU.
- WAMR and all WASM applications execute in **Zephyr user mode**.
- MPU protection is enabled to restrict read, write, and execute access between privilege domains.

---

#### IPC Register Map — `nvu_HOST_IPC_IOSF_Primary_Mem`

These registers govern interrupt signaling between the NVU and the host agent over the IOSF primary memory interface. All registers reset on **FUNCRST**.

##### Register Summary

| Name | Offset | Size | Reset | Description |
|---|---|---|---|---|
| `PISR_HOST2NVU` | `0x0000` | 32 bits | — | Peripheral Interrupt Status — IRQ to NVU; contains inbound interrupt status bits |
| `PIMR_HOST2NVU` | `0x0004` | 32 bits | — | Peripheral Interrupt Mask — IRQ to NVU; enables or disables inbound interrupts from agent |
| `PIMR_NVU2HOST` | `0x0008` | 32 bits | — | Peripheral Interrupt Mask — IRQ to Agent; enables or disables outbound interrupts |
| `PISR_NVU2HOST` | `0x000C` | 32 bits | — | Peripheral Interrupt Status — IRQ to Agent; contains outbound interrupt status bits |

---

##### `PIMR_HOST2NVU` Field Definitions (Offset `0x0004`)

| Field Name | Bits | Reset | Access | Description |
|---|---|---|---|---|
| `AGENT2NVU_DB` | [0] | `0x0` | RW | Mask bit for inbound message (AGENT2NVU Doorbell BUSY) interrupt. Written by NVU FW only. `1` = interrupt unmasked. |
| `RESERVED2` | [10:1] | `0x000` | RO | Reserved. |
| `NVU2AGENT_BC` | [11] | `0x0` | RW | Mask bit for NVU2AGENT doorbell busy clear interrupt. Written by NVU FW only. `1` = interrupt unmasked. |
| `RESERVED1` | [26:12] | `0x0000` | RO | Reserved. |
| `AGENT2NVU_BCISC` | [27] | `0x0` | RW | Mask bit for AGENT2NVU Busy Clear Interrupt Status Clear interrupt. Written by NVU FW only. `1` = interrupt unmasked. |
| `RESERVED0` | [31:28] | `0x0` | RO | Reserved. |

---

##### `PIMR_NVU2HOST` Field Definitions (Offset `0x0008`)

| Field Name | Bits | Reset | Access | Description |
|---|---|---|---|---|
| `NVU2AGENT_DB` | [0] | `0x0` | RW | Mask bit for NVU2AGENT Doorbell BUSY Set. Written by AGENT only. `1` = interrupt unmasked. |
| `RESERVED1` | [7:1] | `0x00` | RO | Reserved. |
| `AGENT2NVU_BC` | [8] | `0x0` | RW | Mask bit for AGENT2NVU Busy Clear Interrupt. Written by AGENT only. `1` = interrupt unmasked. |
| `RESERVED0` | [31:9] | `0x000000` | RO | Reserved. |


### Secure Boot (10 facts)

#### Secure Boot

> **Note:** The 10 HAS facts provided do not contain information pertaining to the NVU Secure Boot sub-skill. The supplied facts cover the following unrelated topics:
>
> - WAMR app memory pre-allocation and partitioning (9.2.3, 11.5.3)
> - WAMR App Manager control flow and tree metadata (11.3.4.1, 11.3.4.2)
> - WASM inter-app data sharing via shared heap (11.5.3)
> - WASM App Management APIs (`app_mgmt_wasm_share_mem`) (11.8.1)
> - WASM message data buffer ownership (11.8.2.4)
> - HECI Bus Driver sharing (5.3.3)
>
> No register definitions, boot authentication sequences, key provisioning details, chain-of-trust descriptions, or any other Secure Boot-relevant data are present in the provided facts.

**No Secure Boot documentation can be generated from these facts without inventing data not present in the source material.** Please supply HAS facts from the Secure Boot section to proceed.


### Telemetry and Profiling (2 facts)

#### Telemetry and Profiling

#### Message Processing Statistics

(HAS §11 Chapter 7: WAMR Framework > 11.3.7 Profiling)

App management is responsible for gathering runtime statistics on message processing. The following metrics must be collected:

- **Queue time** — duration a message spends waiting in the queue before dispatch
- **Dispatch time** — time taken to route and deliver a message to its target handler
- **Processing duration** — time spent executing the message handler itself

These statistics are vital for pinpointing performance bottlenecks in WASM application workloads running on the NVU.

---

#### Telemetry API for WASM Applications

(HAS §17 OPENs and TODOs > 17.2 TODOs)

- A dedicated **telemetry API for WASM Apps** is pending definition and implementation
- This API is currently tracked as an open TODO item and is not yet specified in the HAS

> **Note:** The telemetry API surface for WASM applications is not yet defined. Driver implementors should monitor HAS updates for forthcoming API specifications before exposing telemetry interfaces to WASM-hosted NVU workloads.


### Timers (2 facts)

#### Timer Driver API

- NVU Timer drivers implement a subset of the Zephyr Timer driver API (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.7 Timer)
- For the full list of Timer API functions supported in Zephyr, refer to the **NVU Timer Driver** documentation (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.7 Timer)

#### Hammock Harbor Timer Synchronization

- Upon reception of a `SyncStartCmd` from the NVU, the ARU (Absolute Reference Unit) will enqueue a request to provide the ART (Absolute Reference Time) value (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.9 Hammock Harbor > 7.2.3.9.1 Hammock Harbor Flow)
- If the ARU is currently in the process of providing the ART value to another Hammock Harbor (HH) agent at the time the `SyncStartCmd` is received, the incoming request is queued pending completion of the current transaction (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.9 Hammock Harbor > 7.2.3.9.1 Hammock Harbor Flow)


### USB Camera Interface (2 facts)

#### SIO Frame Counter (HAS 8.8.2.1.2.1.6)

- XHCI schedules commands to the USB device using a frame counter running on the **XTAL clock**
- All isochronous commands that XHCI receives over SIO must be aligned to this frame counter

---

#### DMA Programming for Host Async Tx (HAS 8.8.2.1.2.4.6)

- Host Async Tx is a **one-shot DMA operation**
- **CH1** is used for this transfer
- DMA must be programmed with the following configuration:

| Field | Register | Value | Description |
|---|---|---|---|
| INTEN | DMAC_CFGREG | 1 | Enable interrupt for the transfer |


### Voltage Domains (1 facts)

#### Device Power Management Actions

(HAS §13.6.0.2)

The NVU driver integrates with the Zephyr OSPM (Operating System Power Management) framework via a standardized set of device power management actions. These actions govern the power state transitions of the NVU device within the Zephyr RTOS environment.

**`pm_device_action` Enumeration**

The following enumerated actions are defined for NVU device PM control:

| Action Constant | Description |
|---|---|
| `PM_DEVICE_ACTION_SUSPEND` | Suspend the device, placing it into a low-power state. |
| `PM_DEVICE_ACTION_RESUME` | Resume the device from a suspended state, restoring normal operation. |
| `PM_DEVICE_ACTION_TURN_OFF` | Turn off the device. This action is triggered only by a power domain event. |

**Behavioral Notes**

- `PM_DEVICE_ACTION_SUSPEND` and `PM_DEVICE_ACTION_RESUME` represent the standard low-power entry and exit transitions managed by the Zephyr OSPM subsystem.
- `PM_DEVICE_ACTION_TURN_OFF` is **not** triggered by direct application or driver request; it is exclusively triggered by a **power domain** event, distinguishing it from a standard suspend operation.

