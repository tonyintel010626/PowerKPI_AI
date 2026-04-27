name: fv-nvu/firmware
description: NVU firmware architecture, boot ROM, secure boot, IPC mechanism, firmware loading lifecycle, and security controls

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# NVU Firmware Architecture

> **SAFETY**: Do NOT modify firmware boot flow registers, security lock bits, or IPC channels without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.

## Overview

The NVU (Neural Vision/Sensing Unit) firmware subsystem manages the boot lifecycle, secure firmware loading, inter-processor communication (IPC) with host and peer agents, and runtime security enforcement. The VPX2 DSP (with 32 KB I$ instruction cache, 32 KB D$ data cache, and 128 KB VCCM) executes NVU firmware starting from a 16KB Boot ROM (BROM), through a Bring-Up (BUP) phase, to full firmware operation. The firmware is authenticated by ESE (Essential Services Engine) and uses a SHA-384 hardware accelerator for integrity verification.

Key firmware subsystem components:

- **Boot ROM (BROM)** — 16KB read-only boot code at address `0x0000_0000`, executed by VPX2 on reset
- **AONRF (Always-On RF)** — 16KB read/write memory at address `0x0100_0000`, used as alternate code/data store
- **SHA-384 Accelerator** — Hardware hash engine in the SRAM Sub-System for firmware authentication
- **IPC (Inter-Processor Communication)** — Mailbox-based IPC with Doorbell (DB) registers for communication with Host, ISH, ESE, PMC, and other peer agents
- **Boot/IO DMA** — 8-channel Synopsys DW_axi_dmac for firmware download (RS0 DRAM) and authenticated store (RS3 IMR)
- **Security Controls** — Write-once lock bits (RS0_DISABLE, RS3_WR_DISABLE, IPC_DISABLE) enforced by BUP firmware


## FW Architecture and Image Layout (FAS §6, L4130-4559)

### FW Stack Layers

The NVU firmware is organized in a layered architecture (FAS §6.1):

1. **BSP (Board Support Package)** — Hardware abstraction: NVU IP peripherals (I2C, IPC, GPIO, UART, SPI), DMA, and other NVU HW
2. **RTOS (Zephyr Layer)** — Zephyr RTOS running on VPX2 core, providing kernel services including Native library WASM wrapper APIs
3. **Services** — NN Runtime, Configuration Service (IPU/USB camera sensor configuration), Security & Privacy Service (ESE FW authentication), Power Management
4. **WAMR Layer** — WAMR (WebAssembly Micro Runtime) runtime and App Manager — the backbone of NVU FW that connects, organizes, and coordinates various components
5. **Cross-Subsystem Interface** — SMHI (Sensor Management Host Interface), Host IPC, ESE authentication

### FW Image Structure

NVU firmware is composed of two images (FAS §6.2):

| Image | Contents | Identifier |
|-------|----------|------------|
| **Base Image** | VPX FW (zephyr.bin) + NPX FW (npx_core.bin) + Core App (core_wasm_app.wasm) + AON Image (aon_image.bin) | `'NVG0'` |
| **Extension Image** | WASM apps + NN models + PDT binary | `'NVG1'` |

**Image Authentication**: RSA-3K + LMS (Leighton-Micali Signature) hybrid signature scheme (post-quantum safe).

### FW Binary Layout (Source: FAS SVG — FW Layout Diagram)

The FW binary image has the following physical layout structure:

**Base Image (BUP — Bring-Up) Structure:**

| Section | Size | Description |
|---------|------|-------------|
| CPD Header | 0x14C bytes | Code Partition Directory header |
| Manifest (CSS) | Variable | Code Signing Structure — RSA-3K public key + signature |
| PackageInfo | 0x1B0 bytes | Package metadata |
| RSA + LMS Signatures | Variable | Hybrid post-quantum signatures |
| BUP Raw | Variable | Bring-Up firmware raw binary (ROM-executed boot code) |
| 1K Patch | 1 KB | Hot-patchable region for urgent fixes |

**Base Image Structure (continued):**

| Section | Description |
|---------|-------------|
| VPX FW (`zephyr.bin`) | Zephyr RTOS + services for VPX2 DSP core |
| NPX FW (`npx_core.bin`) | Neural engine firmware for NPX6-1K |
| WASM Core App (`core_wasm_app.wasm`) | Intel Core App — face detection/tracking pipeline |
| AON FW (`aon_image.bin`) | Always-ON firmware image |

**Extension Image Structure:**

| Section | Description |
|---------|-------------|
| WASM Apps | Multiple OEM/Intel algorithm apps (Camera App, Algorithm Apps) |
| NN Models | Multiple neural network model binaries (NPX6 format) |
| PDT Binary | Platform Data Table — calibration/tuning parameters |

### Global Manifest (FAS §6.2.2)

Each FW image has a 128-byte Global Manifest header:

| Field | Size | Description |
|-------|------|-------------|
| `ext_id` | 4B | Image identifier: `'NVG0'` (Base) or `'NVG1'` (Extension) |
| `entry_point_addr` | 4B | VPX2 entry point address in SRAM |
| `aon_rf_base` | 4B | AONRF base address (16KB region) |
| `aon_rf_limit` | 4B | Size of AON RF space (16KB) |
| `sram_bit_width` | 4B | SRAM data width: 64-bit |
| `sram_base` | 4B | SRAM base address |
| `sram_limit` | 4B | Size of SRAM space (3.5MB) |

### Module Manifest (FAS §6.2.3)

Each module within an image has a 64-byte Module Manifest:

| Field | Description |
|-------|-------------|
| `ext_id` | `"NVG0"` for Base FW, `"NVG1"` for Extension FW |
| `module_name` | Module identifier (see table below) |
| `load_addr` | SRAM load address |
| `property` | `permanent` (always in SRAM) or `dynamic` (paged in/out) |
| `variant` | Module variant identifier |

### FW Module Names (FAS §6.2.3.1)

| Module Name | Binary File | Description |
|-------------|-------------|-------------|
| `VPX_CORE` | `zephyr.bin` | Zephyr RTOS + BSP + Services |
| `NPX_CORE` | `npx_core.bin` | NPX6-1K neural engine firmware |
| `COREWASM` | `core_wasm_app.wasm` | Core WASM application (Intel-only, system privilege) |
| `AON_IMAG` | `aon_image.bin` | Always-ON image (runs from AONRF during IPAPG) |
| `WASM_APP` | `<app>.wasm` | OEM/Intel WASM algorithm application |
| `NN_MODEL` | `<model>.nnx` | Neural network model (ONNX → .nnx compiled) |
| `PDT_DATA` | `nvu_pdt.bin` | Platform Definition Table (magic=`'NVUT'`) |


## Boot ROM / AONRF (HAS Section 8.9)

### BROM (Boot ROM)

The Boot ROM is a 16KB read-only memory containing the initial boot code executed by VPX2 on reset.

| Parameter | Value | Description |
|-----------|-------|-------------|
| IP | BROM | Boot ROM controller |
| TOTAL_MEM_SIZE | 16KB | ROM size |
| ACCESS_WIDTH | 4 (32-bit) | 32-bit interface |
| TILE_WIDTH | 4 | HIP Tile Width |
| TILE_HEIGHT | 4096 | HIP Tile Height |
| NUM_INSTANCES | 1 | Single tile |
| VPX2 Address | `0x0000_0000` - `0x0000_4000` | Region 0 of VPX2 address space |
| Clock | `nvu_func_clk` @ 200MHz | AONRF/BROM clock domain |

### AONRF (Always-On RF Memory)

AONRF is a 16KB read/write memory used as an alternate code store. In debug mode, reset code can be downloaded to AONRF and the VPX2 reset vector updated to point to AONRF (per HAS Section 8.3).

| Parameter | Value | Description |
|-----------|-------|-------------|
| IP | AONRF | Always-On RF controller |
| TOTAL_MEM_SIZE | 16KB | AONRF size |
| ACCESS_WIDTH | 4 (32-bit) | 32-bit interface |
| TILE_WIDTH | 4 | HIP Tile Width |
| TILE_HEIGHT | 1024 | HIP Tile Height |
| NUM_INSTANCES | 4 | Number of tiles |
| VPX2 Address | `0x0100_0000` - `0x0100_4000` | Region 0 of VPX2 address space |
| Clock | `nvu_func_clk` @ 200MHz | AONRF/BROM clock domain |

### AONRF/BROM Capabilities

Per HAS Section 2.5.1.8:

- Highly scalable light-weight RF controller converting fabric bus cycles to memory cycles
- OCP target interface to NVU Fabric
- Interface to non-ECC memory (read-only for BROM, or write-strobe for AONRF)
- Zero-wait state access from fabric to memories


## SRAM Layout and Memory Architecture (FAS §7.1, L4560-5200)

### SRAM Region Layout

NVU's 3584KB SRAM (7 slices × 512KB) is partitioned into 4 regions, low address → high address (FAS §7.1.1):

| Region | Content | Constraint | Allocation Direction |
|--------|---------|------------|---------------------|
| 1 | NPX FW | NPX FW + CV Shared ≤ 2MB total | Low → High |
| 2 | CV Shared Memory | Managed by CV Service in VPX | Low → High |
| 3 | VPX FW | Starts at **2MB offset** | — |
| 4 | Pre-allocated Memory Pool | High addresses | — |

Within the NPX region:
- DSP buffers + NN Runtime allocate **low → high**
- NN Model data allocates **high → low** (fixed end address for NPX)
- NN Model alignment: **4KB** (required for SMMU PageIn DMA)
- NPX buffer alignment: **64 bytes** (dcache line)

### Memory Access Modes (FAS §7.1.2)

| Mode | Address Range | Translation | Usage |
|------|--------------|-------------|-------|
| **PMEM** (Physical) | Up to 3.5MB | None (direct) | All VPX/NPX code and data |
| **VMEM** (Virtual) | Up to 16MB | SMMU translation | Runtime NN Model loading (PageIn DMA from IMR); also used in debug mode for dumping intermediate model results to IMR |

> **Important**: VMEM is used primarily for NN Model paging from IMR to SRAM; in debug mode, VMEM is also used for writing intermediate model results to IMR (RS3_WR_DISABLE=0). There is **no page swapping** — once a model page is loaded, it stays in SRAM until explicitly freed.

### Pre-allocated Memory Pool Blocks (FAS §7.1.1)

| Block | Description |
|-------|-------------|
| WAMR Heap | WAMR runtime heap for WASM apps |
| VPX FW Heap | Zephyr kernel + services heap |
| CVISP 2A Stats | Auto-exposure/auto-white-balance statistics buffer |
| Face ID Vector | Encrypted face template storage (runtime) |
| Image Reformat Buffer | Frame format conversion workspace |
| CVISP Output Buffer | ISP output buffer |
| NPX Log | NPX core log buffer (aggregated by VPX) |
| IPC | IPC message buffers |

### Memory Protection (FAS §7.1.3)

Two-level protection scheme:

1. **Core-based Access Protection** — core-based access control restricts NPX core to specific allowed regions, preventing access to VPX memory or host-facing registers
2. **MPU-based** — Zephyr user mode partition. WAMR runs in user mode with MPU-enforced memory boundaries. Kernel services run in privileged mode.


## Boot Flow (HAS Section 10.2)

### Cold Reset Boot Sequence (G3 -> S0)

NVU is part of the Host Reset group of IPs. The boot sequence involves:

1. **HW Reset** — PMC asserts/de-asserts NVU reset signals:
   - `pmc_nvu_side_rst_b = 1` (de-assert side reset)
   - IOSF_SB: `IP_Ready = 1`
   - `pmc_nvu_prim_rst_b = 1` (de-assert primary reset)
2. **CRPM SR_IN_PRG** — `APB::CRPM.SR_IN_PRG = 1` set during reset, cleared when ready
3. **PMC IP Wake** — `pmc_nvu_ip_wake = 1` then `= 0` after reset sequence completes
4. **VPX ROM Execution Starts** — VPX core exits HALT state, begins executing Boot ROM
5. **ROM Waits for SR_IN_PRG** — ROM polls `APB::CRPM.SR_IN_PRG` bit to be 0
6. **Softstrap Check** — ROM reads `APB::MISC.SOFTSTRAP.NVU_WAIT_FW_LOAD_VISION_SERVICE` bit:
   - If `= 0`: ROM does not wait for VISION_SERVICE and proceeds to BUP loading
   - If `= 1` (default): ROM waits in IPAPG until `APB::CRPM.VISION_SERVICE = 1` before BUP loading
7. **BUP Loading** — Bring-Up firmware loaded from host via IPC interface
8. **FW Loading** — Full NVU firmware authenticated and loaded (see Firmware Loading section)

### Boot with Lid Closed

When lid is closed (indicated by BIOS to PMC via IPC), the boot flow differs:

- ROM enters shutdown IPAPG state instead of proceeding with BUP loading
- NVU remains in lid-closed state ready for VNN removal (which appears like an IP reset to FW)
- Spurious wakes during IPAPG cause HW to wake VPX, ROM re-executes and returns to IPAPG
- On lid-open indication (`IPC::lid-open=1`), FW reboots from ROM since all SRAM content is lost during lid-closed VNN removal

> **Integration HAS v0.8 (Section 9)**: The full Boot with Lid Closed sequence covers PMC PGCB power-down handshakes, PMC save of NVU HW configuration registers (IPC ESE and ISH IPC Channels, IOSF2AXI PCI Config registers, Bridge Private Registers), VNN removal, wake detection, VNN restore, PMC restore of saved registers, PGCB power-up, and ROM re-execution.

### Boot with Lid Open

- ROM executes normally, checks VISION_SERVICE softstrap
- If VISION_SERVICE = 0, ROM enters D0i2 IPAPG awaiting service enable
- If VISION_SERVICE = 1 (or softstrap bypasses wait), ROM proceeds to BUP/FW loading
- NVU asserts VNN resource own request and begins FW download

> **Integration HAS v0.8 (Section 9)**: The full Boot with Lid Open (G3→S0) sequence is a cold boot flow covering PMC reset de-assertion, CRPM initialization, VPX BROM execution, and firmware loading handshakes.

### NVU FW Boot Sequence (E2E HAS Perspective)

> Source: VISION SS End-To-End HAS v0.1. This describes the boot sequence from the system-level perspective, complementing the IP-level boot flow above.

The NVU firmware boot sequence in the context of the vision subsystem:

1. NVU waits in **IP Accessible Power Gate** (IPAPG) state
2. **Lid Open Indication** received from PMC
3. PMC sends **Sleep_Level_Req** with `VISION_SERVICE=1`
4. **BUP firmware** loaded and authenticated via **ESE** (Embedded Security Engine); host IPC interface disabled after FW download
5. **SRAM scrub** performed to clear any sensitive data (e.g., Face ID vectors) remaining from previous runtime
6. **Security configuration** set up by BUP: **IPC_DISABLE** (cut off IPC communication between NVU and host) and **RS3_WR_DISABLE** (supports only one-way DMA from NVU to host)
7. **Main FW** loaded from **IMR** (Intel-authenticated)
8. NVU FW retrieves platform camera configuration
7. Camera configuration stored; necessary information for FW usage saved with an index of pointer and size values at the top of **AON** memory

#### DSM Call for Camera Configuration

After main FW is loaded, the NVU SW driver queries platform camera configuration from BIOS during OS boot. The configuration includes:

| Parameter | Description |
|-----------|-------------|
| Camera Type | MIPI CSI-2, USB Legacy, or USB RAW |
| PHY Type | C-PHY or D-PHY (for MIPI cameras) |
| Max Resolution | Maximum supported resolution |
| Sensor Type | Sensor model/capability identifier |
| NVU Enabled | Whether NVU vision sensing is enabled |
| I2C/I3C Settings | Bus, slave address, speed, function, and platform-specific pin assignments |
| Shared Camera | Designation of which camera is shared between IPU and NVU |

The retrieved configuration is subsequently passed to NVU FW for runtime reference during camera initialization and ownership arbitration flows.

### Exception/Soft Reset (HAS Section 10.2.6)

NVU supports soft reset of VPX2 core under these conditions:

- **FW-initiated soft reset** — triggered via `CSE2NVU_IPC.RESET_BIT`
- **Exception reset** — triggered by:
  - Watchdog expiry (VPX2 IRQ 47)
  - ECC double-bit error (SRAM `SSCEL.UCERREV`)

On exception reset:
- RW/O bits that were set by ROM/BUP (disabling host communication and DRAM access) are **cleared**, allowing ROM/BUP/FW to re-load and re-communicate with host SW driver
- PME assertion can wake the host SW driver from D3 for FW re-load

> **Note**: Current generation VPX2 core does not support triple-fault/shutdown indication; this is not considered a reset source.

### VPX FW Exception Flow — 35 Steps (from FAS SVG: Flow_for_Exception_VPX_FW_HW)

Full firmware-level exception recovery sequence. Initial state: **Normal Execution**.

**Phase 1 — Camera Shutdown (if NVU owns camera)**
```
[001] Exception Handler entry
[002] Stop + power off camera sensor
[003] PHY shutdown (MIPI) or L2 suspend (USB)
[004] Release shared IO (I2C/I3C) for MIPI camera
[005] De-assert release_ack vGPIO(s)
[006] NVU_claim = 0
```
> If NVU is in Snooping/Offloading mode (not camera owner): skip [002]-[006], go to [008].

**Phase 2 — Exception Dump Collection**
```
[008] Collect exception dump:
      - Faulting address + reason
      - Call stack
      - If NPX caused exception: collect NPX dump too
[009] Print exception dump (debug trace via DTF)
[010] Save exception dump into AONRF (Always-ON Register File)
```

**Phase 3 — HW Exception / VPX Reset**
```
[011] Trigger VPX reset (via CRPM)
[012] Check reset reason register (CRPM_RST_HIS)
      [Exception triggered path]:
[013] Check NPX status
      [If NPX not HALT]:
[014]   Halt NPX, gate NPX CLK, assert NPX reset
[015] Load BUP (Boot-Up Patch) from SRAM
[016] Jump to BUP entry point
[017] [HW Exception triggered — BUP executing]
```

**Phase 4 — PMode / VGPIO Cleanup**
```
[018] Check I2C0~1 / I3C0 PMode
      [If PMode == NVU Native FN]:
[019]   Change I2C0~1 / I3C0 PMode to LPSS (release pins)
[020] Check VGPIO9/11/13/15 PMode
[021] Assert NVU_GP1/3/5/7 = 0 (de-assert output VGPIOs)
[022] Check NVU_claim register
      [If NVU_claim != 0]: OPEN (known HW issue)
[023] Clear reset reason in CRPM_RST_HIS
[024] (continued)
      [If VGPIO9/11/13/15 PMode == NVU Native FN]:
[025]   Register NVU_GP0/2/4/6 interrupt for release_req IRQ
```

**Phase 5 — FW Recovery via RTD3 Cycle**
```
[026] Check D3 state
      [If NVU in D3]:
[027]   RTD3 Exit (restore power, ungate clocks)
[028]   Reset handshake with host
[029]   Download Base FW + App FW (from host via IPC)
[030]   Download BIOS Camera Configs
[031]   Read exception dump from AONRF
[032]   Upload exception dump to host (via IPC)
[033]   RTD3 Enter (return to low-power state)
[034]   Mask BUP IRQs
[035]   Jump to Main FW → normal boot
```

### NPX FW Exception Flow — 8 Steps (from FAS SVG: Flow_for_Exception_NPX_FW)

When NPX (Neural Processing Unit) encounters an exception, it notifies VPX via ARCSYNC:

```
NPX Side:
  [001] NPX Exception Handler entry
  [002] Collect NPX exception dump (registers, state, fault info)
  [003] Write dump to shared SRAM buffer (NPX↔VPX shared region)
  [004] Notify VPX via ARCSYNC message (MsgType = Exception)
  [005] Sleep (NPX halts, awaits reset from VPX)

VPX Side:
  [006] ARCSYNC IRQ1 fires on VPX2
  [007] Check MsgType == Exception
  [008] Execute same sequence as VPX FW-triggered exception (Phase 1-5 above)
```

> **Key**: NPX cannot self-recover — it must notify VPX, which orchestrates the full reset and FW reload cycle. The NPX dump is collected first and merged into the VPX exception dump at step [008].


## Firmware Loading and Lifecycle

### FW Download Flow

Per the security architecture:

1. **SRAM Zeroization** — The first thing after ROM starts is to trigger HW to do SRAM zeroization (scrub), performed as early as possible per security requirements.
2. **FW Download to IMR** — ESE loads NVU firmware image from IFWI into the IMR location allocated by ESE.
2. **ESE Authentication** — ESE carries out authentication of the NVU FW in IMR. Because IMR content is not trusted, ROM also requests ESE to share the HASH value of the BUP image and compares it for integrity verification. Additionally, BUP itself calculates the HASH value of each module and the whole image, and compares HASH values with ESE.
4. **SRAM Loading** — Once authenticated, BUP copies all FW modules except the manifest from IMR into SRAM (the manifest is already copied into SRAM earlier) (page swapping is not allowed; after BUP, IMR is read-only).
4. **VPX Execution** — VPX core executes authenticated firmware from SRAM.

### Boot/IO DMA (HAS Section 8.11)

The Boot/IO DMA is a Synopsys DW_axi_dmac with these key parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| IP | BootDMA (DW_axi_dmac) | Synopsys AXI DMA |
| DMAX_NUM_CHANNELS | 8 | 8 independent DMA channels |
| DMAX_NUM_HS_IF | 26 | 26 hardware handshaking interfaces for NVU peripherals |
| DMAX_M_ADDR_WIDTH | 64 | 64-bit address |
| DMAX_M_DATA_WIDTH | 64 | 64-bit data |
| DMAX_MSTIF_OSR_LMT | 16 | 16 outstanding bursts |
| DMAX_ENDIAN_FORMAT_MSTIF | 0 (Little Endian) | Static little-endian |
| VPX2 Register Address | `0xF380_0000` - `0xF380_1000` | DMA register target |
| DMA_MISC Address | `0xF390_0000` - `0xF390_1000` | DMA MISC register target |

DMA purposes:
- **Boot Service** — Copy boot image from RS0 to RS3 and from RS3 to SRAM
- **IO Service** — Data movement from/to peripherals to SRAM

### Root Space Usage

| Root Space | Name | Usage |
|------------|------|-------|
| RS0 | Host | Data streaming to host DRAM, host MMIO access |
| RS2 | ESE (Sideband) | ESE authentication and management |
| RS3 | IMR | Authenticated FW store, FW read-only source |

### ROM Boot Tasks (FAS §9.2, L11129-11350)

The ROM executes the following tasks in sequence after VPX core is brought out of reset:

1. **SRAM Zeroization** — Triggers HW to do SRAM zeroization to ensure sensitive data (e.g., Face ID vectors) does not persist after reset
2. **ESE loads BUP to IMR** — ESE copies BUP firmware from IFWI to IMR via sideband DMA
3. **Boot mode fuses** — Check `NVU_HVM_MODE_Fuse`, `NVU_Secure_Load_Fuse`, `NVU_Debug_Mode_Fuse` to decide boot mode
4. **ROM compares HASH** — SHA engine computes hash of BUP in SRAM to ensure it is identical to BUP in IMR; ROM also requests ESE to share the hash value of the BUP image for comparison
5. **Jump to BUP** — If hash matches, ROM transfers execution to BUP entry point
6. **Reset Prep** — Handle Reset Prep interrupt (may occur when power button is pressed in S0 state)
7. **PMC save/restore** — Coordinate with PMC for power state save/restore
8. **LTR management** — Set LTR=2ms before DMA operations, set LTR=infinite before ROM exit
9. **IPAPG exit check** — If waking from IPAPG (per CRPM registers), jump to AON task to restore context from AONRF (this check occurs early in ROM flow, right after reset)
10. **Security configuration** — Note: IPC_DISABLE and RS3_WR_DISABLE are set by BUP, not ROM (see BUP security tasks)
11. **DEBUG HOOK** — If debug mode, halt for debugger attach

### BUP Boot Tasks (FAS §9.3, L11350-11513)

After ROM transfers control, BUP executes:

1. **Manifest copy** — BUP copies manifest into SRAM
2. **SRAM range check** — BUP applies a basic range check before doing SRAM partition based on the manifest (partitions must not overlap with existing allocations)
3. **PM setup** — Configure power management for lid-close/open flow (PMC save/restore done status check)
4. **Camera Config Save** — Store camera configuration to SRAM
5. **Crash Dump** — Check for crash dump in AONRF from previous boot, report to host if present
6. **Trace Config** — Configure DTF/logging based on debug policy
7. **SRAM Scrub** — Scrub SRAM to prevent asset leakage of sensitive data (e.g., Face ID vectors) remaining from previous runtime
8. **Face ID Remove** — Handle face enrollment removal requests from previous session
9. **Security Lockdown** — Set write-once lock bits and security configurations in sequence:
   - Set up NPX memory access controls
   - Isolate USB SRAM
   - `IPC_DISABLE` — Disable host IPC (FW must first clear the ATT HOST_IPC valid bit to ensure downstream MMIO accesses from Host are UR'ed by ATT)
   - `RS3_WR_DISABLE` — Restrict to one-way DMA from NVU to host
   - `ATT_WRITE_DISABLE` — Freeze Address Translation Table entries (prevent further ATT modifications)
10. **AON data layout** — Initialize AONRF persistent data, including `SNOW_BALL` at `AON_END - 0x8`

> **AON data layout** (FAS §9.3): An index of pointer and size values is stored at the top of the AON, with detailed data stored at the referenced pointer address occupying the specified size in bytes.


## Secure Boot and Authentication (HAS Section 8.15, Section 14)

### Authentication Architecture

Per the HAS Security Risk Assessment (Section 14.2):

- **NVU FW is downloaded into IMR location allocated by ESE**
- **ESE carries out authentication of the NVU FW in IMR**, only then executed by VPX Core once authenticated
- **FW is authenticated before executing on the controller** (confirmed in security questionnaire Q13.1)
- **FW executes from protected/isolated memory** — authenticated Intel-signed NVU FW sets up access controls
- All FW-initiated traffic carries **NVU_SAI** (Security Agent Identifier)
- MSI during FW loading carries **DEVICE_UNTRUSTED_SAI**

### Secure Boot Flow

Per HAS Section 14.3 (EAIG item 6):

1. **SRAM zeroization** — The first thing after ROM starts is to trigger HW to do SRAM zeroization
2. **Secure boot flow in ROM with SHA engine** — ROM uses the SHA engine to ensure BUP in SRAM is identical to BUP in IMR
2. **Secure boot flow with ESE** — ESE performs SVN check and signature verification of BUP in IMR
3. **ESE debug key** — ESE switches to debug key in SoC unlock debug mode for FW authentication
4. **Runtime integrity** — FW page-in from IMR with hash value check with SHA acceleration
5. **Boot phase comparison** — Because IMR content is not trusted, ROM requests ESE to share the HASH value of the BUP image and compares it with the SRAM image hash. Additionally, BUP itself calculates the HASH value of each module and the whole image, and compares HASH values with ESE

#### Post-Quantum Cryptography (Integration HAS v0.8)

> ESE uses the **PQC/LMS (Leighton-Micali Signature)** algorithm for signature verification of NVU firmware. LMS is a hash-based post-quantum signature scheme resistant to quantum computing attacks. This is part of Intel's transition to quantum-safe firmware authentication across all IP blocks.

### SHA-384 Hardware Accelerator (HAS Section 8.6.4.5)

The SHA engine is a hardware acceleration engine within the SRAM Sub-System for FW authentication. It was re-used from CSME IP with additional glue logic to DMA-read source code for hashing.

| Feature | Detail |
|---------|--------|
| POR Algorithm | SHA-384 |
| Supported Algorithms | SHA-256, SHA-384 (HW implementation; SHA-1/224/512 defined in register but not implemented in HW) |
| Input Block Size | 1024 bits |
| Max Data Length | 2^64 bits |
| Control Register | `SHACTL.EN` — start/stop SHA operation |
| Algorithm Select | `SHACTL.ALGO` — selects SHA algorithm |
| Resume Mode | `SHACTL.HRSM` — resume with saved context via `SHAIVDWx` and `SHAALDWx` |
| Status Register | `SHASTS.BUSY` — indicates operation in progress |
| Result Registers | `SHARDWx` — hash digest output |
| Data Input | `PIBFPI` — write-only register to feed data to SHA engine |
| Clock Gating | SHA engine is clock-gated when `SHACTL.EN = 0`; register block uses separate gated clock |

#### SHA Programming Modes

1. **One-Time HASH Mode** — Set `SHACTL.EN = 1` with `SHACTL.RSM = 0`; feed data via `PIBFPI`; when done, clear `SHACTL.EN` after `SHASTS.BUSY = 0`; read result from `SHARDWx`
2. **HASH Resume Mode (multiple chunks)** — Save context from `SHARDWx` and accumulated length; program into `SHAIVDWx` and `SHAALDWx`; set `SHACTL.EN = 1` with `SHACTL.HRSM = 1`
3. **HASH Resume with Process Switch** — Switch between two HASH tasks by saving/restoring context

> **Important**: FW must ensure message granularity is 1024-bit aligned when suspending, or partial data will be dropped by HW. FW must verify `SHASTS.BUSY = 0` before clearing `SHACTL.EN` (HW clock-gates when EN=0).

### Security Fuses (HAS Section 19)

Key security fuses at sideband address `0x0650`:

| Fuse | Bits | Default | Description |
|------|------|---------|-------------|
| `NVU_VPX_HALT_Fuse` | [0] | 0 | VPX HALT fuse for HVM Testing. Causes ROM to halt NVU CPU |
| `NVU_HVM_MODE_Fuse` | [1] | 0 | HVM mode fuse. See boot method for details |
| `NVU_Secure_Load_Fuse` | [2] | 1 | Secure Load Fuse. `0x1` = Secure Load Mode |
| `NVU_Debug_Mode_Fuse` | [3] | 0 | Debug Mode Fuse. `0x1` = Debug Mode |
| `NVU_Softstrap_select_disable` | [4] | 1 | `0x1`: SECURE/DEBUG mode from fuse; `0x0`: from soft-strap |

Key security soft-straps:

| Soft-Strap | Bits | Default | Description |
|------------|------|---------|-------------|
| `NVU_Secure_Load_softstrap` | SS1[19] | 1 | Secure Load strap (`0x1` = Secure Load Mode) |
| `NVU_Debug_Mode_softstrap` | SS1[20] | 0 | Debug Mode strap (`0x1` = Debug Mode) |
| `NVU_Timeout_softstrap` | SS1[23:21] | 0x3 | Boot/reset-prep auto-ack timeout: `0x1`=8ms, `0x2`=16ms, `0x3`=32ms |
| `NVU_HW_AutoAck_Disable` | SS1[24] | 0 | Disable HW auto-ack for ResetPrep and BootPrep |
| `NVU_WAIT_FW_LOAD_VISION_SERVICE` | SS1[27] | 1 | Forces ROM to wait in IPAPG until VISION_SERVICE=1 before BUP/FW loading |
| `NVU_SRAM_SCRUB_BY_FW` | SS1[28] | 0 | When set, ROM/BUP uses SW writes instead of HW ECC scrub method |
| `NVU_HASH_BY_FW` | SS1[29] | 0 | When set, ROM/BUP computes HASH via SW algorithm instead of SHA HW engine |

#### Soft-Strap Sideband Addresses (Integration HAS v0.8, Section 18)

| Sideband Address | Soft-Strap | Width | Description |
|------------------|------------|-------|-------------|
| `0x065C` | `NVU_Reg_prg_intf` | 8-bit | Programming Interface byte (ClassCode[7:0]) |
| `0x065D` | `NVU_SubClass_code` | 8-bit | SubClass Code byte (ClassCode[15:8]) |
| `0x065E` | `NVU_BaseClass_code` | 8-bit | Base Class Code byte (ClassCode[23:16]) |
| `0x0662` | `NVU_platform_sku` | 2-bit ([1:2]) | Platform SKU selection |
| `0x0664` | Spare SS5 | 32-bit | Reserved spare soft-strap |
| `0x0668` | Spare SS6 | 32-bit | Reserved spare soft-strap |


## FW Security Scope and Principles (FAS §10, L11514-11633)

The NVU security architecture protects image data and face ID templates. Full details are in the NVU Security Architecture Spec (contact: Ke Han).

### Privacy Assets

| Asset | Protection Goals | Description |
|-------|-----------------|-------------|
| Image + derivatives | Confidentiality, Integrity, Availability | Camera frames, ISP output, intermediate buffers |
| Face ID template | Confidentiality, Integrity, Availability | Encrypted enrollment vectors stored and retrieved via ESE |

### Trusted Computing Base (TCB) Classification (FAS §10, L11580-11600)

| FW Component | TCB Status | Notes |
|-------------|-----------|-------|
| VPX FW (zephyr.bin) | **TCB** | Kernel + services — full hardware access |
| NPX FW (npx_core.bin) | **TCB** | Neural engine firmware — direct NNA access |
| WASM App FW | **NOT TCB** | Sandboxed in WAMR; for TTL: only Intel-signed apps allowed |

> **TTL-Specific**: Only 1st-party (Intel) AON vision apps are in scope. 3rd-party WASM apps are **NOT in scope for TTL**.

### Security Threat Model (from FAS SVG diagrams)

#### TCB Boundaries

```
┌─────────────────────────────────────────────────────────┐
│  Base FW — Intel Signed TCB                             │
│  ┌─────────────────────────────────────────────────────┐│
│  │  App FW — Intel/OEM Signed                          ││
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │  WAMR Sandbox (NOT TCB)                         │││
│  │  │  - WASM App isolation via WAMR + Zephyr MPU     │││
│  │  │  - No direct HW register access                 │││
│  │  │  - Native API calls only through verified gates  │││
│  │  └─────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

#### Protected Assets

| Asset | Storage | Protection |
|-------|---------|------------|
| Face ID vectors | ESE (SPI NOR) | Encrypted at rest; decrypted in SRAM at boot; re-encrypted after enrollment |
| Frame buffer | NVU SRAM | Never leaves NVU; cleared on app shutdown (Shared Memory Eraser) |
| Algorithm results | NVU SRAM | Cleared after ISH-IPC delivery |
| NN models | Extension image | Read-only in SRAM; integrity via manifest hash |
| NPX shared heap | NPX L1 MEM | NPX only accessible by VPX; HW-supported NPX memory isolation |
| WAMR shared memory | VPX SRAM | r/w access only through WAMR native APIs |

#### Attack Surfaces (from Threat Model SVG)

| Surface | Interface | Threat | Mitigation |
|---------|-----------|--------|------------|
| Post-TTL 3rd-party apps | WAMR sandbox | Code injection, privilege escalation | WAMR sandbox + Zephyr MPU isolation, Intel-sign-only for TTL |
| I2C/GPIO/SPI sensors | Peripheral bus | Sensor spoofing, data injection | FW validates sensor data; SAI access control on peripheral registers |
| CSI-2/ISP camera | MIPI-IF | Frame injection, timing attack | PHY sharing arbitration, CVISP input validation |
| ISH IPC | IOSF SB | Unauthorized commands, data leaking | Data Leaking Prevention (>3 violations → ISH-IPC shutdown) |
| ESE IPC | IOSF SB | Key extraction, replay | ESE authenticates all FW loads; SVN anti-rollback |
| Host HECI | BAR0 MMIO | Malicious host commands | Host IPC disabled post-boot; RS3_WR_DISABLE restricts to one-way DMA from NVU to host; ATT restricts BAR access |
| NPK/Debug | DTF/JTAG | Data exfiltration via trace | Debug Mode fuse gated; production fuses disable debug interfaces |

#### Face ID Vector Flow (from FAS SVG)

```
Boot → ESE decrypt Face ID vectors → SRAM (plaintext)
  ↓
Detection phase: Intel Core App (within TCB) performs face matching
  → Cosine/L2Norm/DotProduct matching
  → Known vs Unknown classification
  (Face ID algo app cannot access stored face ID vectors)
  ↓
Enrollment: sec_svc_assets_info() → sec_svc_assets_add()
  → sec_svc_assets_store() → ESE encrypt → SPI NOR
  ↓
Shutdown: Shared Memory Eraser clears all Face ID vectors from SRAM
```

Face ID Security APIs (from SVG):
- `sec_svc_assets_info()` — query stored asset count
- `sec_svc_assets_retrieve()` — load encrypted vectors from ESE
- `sec_svc_assets_add()` — add new enrollment vector
- `sec_svc_assets_store()` — persist to ESE (encrypted)
- `sec_svc_assets_delete()` — remove enrollment vector
- `cv_svc_verify_face_id()` — run face matching (Cosine/L2Norm/DotProduct)

### Security Principles

1. **Zephyr user/kernel mode** — WAMR runs in Zephyr user mode with MPU-enforced memory boundaries
2. **WAMR sandbox** — WebAssembly linear memory model prevents out-of-bounds access
3. **MPU hardware protection** — Memory Protection Unit enforces per-region access policies
4. **Host interface disabled after boot** — IPC_DISABLE, RS3_WR_DISABLE lock bits set by BUP


## IOSF-SB Interface and Opcode Restrictions (HAS Section 8.13)

The NVU IOSF-SB sideband endpoint name is **`NVU`** (16-bit Port ID, payload bus width 8). NVU FW can act as an initiator on IOSF-SB to inject upstream messages for IPC communication with peer agents and Hammock Harbor time-sync messages.

### Opcode Masking (HAS Section 8.13.1)

HW enforces a restricted set of opcodes that NVU FW may send upstream on IOSF-SB. If FW attempts a disallowed opcode:

1. HW traps it as an ERROR — the upstream message is **not sent** on the SB network.
2. HW sets `US_STATUS.OPCODE_ERR` (bit 2).
3. HW sends an interrupt for this condition if `US_COMMAND.INT_EN` is set.
4. FW clears `US_STATUS.OPCODE_ERR`, fixes the opcode, and re-sends.

**Allowed FW Opcodes on IOSF-SB:**

| Message Type | Opcode Type | Opcode | Index | Hex Value |
|--------------|-------------|--------|-------|-----------|
| Register Access | Global | MRd | 0 | `0x00` |
| Register Access | Global | MWr | 1 | `0x01` |
| Register Access | Global | CRRd | 6 | `0x06` |
| Register Access | Global | CRWr | 7 | `0x07` |
| Message With Data | Global | SyncStartCMD | 80 | `0x50` |
| Message With Data | Endpoint Specific | QoS_DMD | 88 | `0x58` |

### SBEP Register Block

| Block | Size | Start Address | End Address |
|-------|------|---------------|-------------|
| SBEP | 4KB | `0xF3300000` | `0xF3301000` |

VPX2 Interrupts: IRQ 85 (`irq85_a`, offset `0x154`) = SBEP US IRQ; IRQ 86 (`irq86_a`, offset `0x158`) = SBEP DS IRQ.

### SB Message Flows (HAS Section 8.13.6)

Three message flow types are defined:

1. **Upstream Posted Message Flow** (35 steps) — NVU FW initiates via SBEP registers (`SB_US_STATUS`, `SB_US_ADDRESS_HI`, `SB_US_ADDRESS_LO`, `SB_US_DATA_OUT`). The 35-step sequence covers register setup, message formatting, IOSF sideband arbitration, and completion.
2. **Upstream Non-Posted Message Flow** (41 steps) — Same register set plus `SB_US_ATTRIBUTES`. The additional 6 steps (vs Posted) handle completion response return path.
3. **SBEP Downstream Message Flow** (5 steps) — IOSF2AXI bridge receives downstream messages and presents them to NVU SBEP HW (`SB_DS_CONTROL_STATUS`, `SB_DS_REGISTERS`, `MSG_RCVD_IRQ_STATUS`). The 5-step sequence: receive → decode → write DS registers → assert IRQ → FW reads.

### IOSF-SB Extended Header and Port-ID (HAS Section 8.13)

| Feature | Detail |
|---------|--------|
| Extended Header (EH) = 0 handling | When EH=0, the SAI field defaults to **0x3F** (all-ones, 6-bit). This means messages without extended headers are treated as having maximum SAI privilege. |
| Port-ID addressing | IOSF-SB supports both **16-bit** and **8-bit** Port-ID addressing. The NVU IP Port ID Width is **16-bit** (HAS Table, Port ID Width = 16). The actual width used on a given SoC depends on integration configuration. |

> **Security note**: EH=0 → SAI=0x3F means unauthenticated sideband messages get full access. The security architecture relies on the IOSF fabric to enforce that only trusted agents can send EH=0 messages.


## IPC Mechanism (HAS Section 8.14)

### IPC Overview

The NVU uses a mailbox-based IPC mechanism with dedicated register sets (HOST_IPC / PEER_IPC) for communication between NVU firmware and peer agents (Host, ISH, ESE, PMC, ACE, CNVi, BT). IPC channels are accessed via IOSF sideband for peer agents and via PCI MMIO BAR for host. Each IPC channel has a **DB (Doorbell)** register that FW "presses" to signal a message is ready, a **DBM (Doorbell Mirror)** register, a **CSR (Control/Status Register)**, and **MSG (Message)** payload registers. The HAS refers to the signaling action as "DB pressed" (e.g., HAS Section 8.14.2.5).

### IPC Register Memory Map (VPX2 Internal View)

| Block | Sub Region | Size | Start Address | End Address |
|-------|------------|------|---------------|-------------|
| HOST_IPC | HOST_IPC | 4KB | `0xF100_0000` | `0xF100_1000` |
| HOST_IPC | SPARE_IPC | 4KB | `0xF100_1000` | `0xF100_2000` |
| PEER_IPC | CSE_IPC | 4KB | `0xF110_0000` | `0xF110_1000` |
| PEER_IPC | PMC_IPC | 4KB | `0xF110_1000` | `0xF110_2000` |
| PEER_IPC | CNVI_IPC | 4KB | `0xF110_2000` | `0xF110_3000` |
| PEER_IPC | ACE_IPC | 4KB | `0xF110_3000` | `0xF110_4000` |
| PEER_IPC | ESE_IPC | 4KB | `0xF110_4000` | `0xF110_5000` |
| PEER_IPC | BT_IPC | 4KB | `0xF110_5000` | `0xF110_6000` |
| PEER_IPC | ISH_IPC | 4KB | `0xF110_6000` | `0xF110_7000` |

### Host IPC Access

- Host SW Driver mapped to FN0 of IOSF2AXI Bridge, exposes a 64KB BAR
- BAR remapped at IOSF2AXI BR to address `0x8000_0000` via `strap_axi_remap_address[0]` tie-off
- ATT Entry 0: HOST_IPC at MMIO `0x8000_0000` - `0x8000_1000` (4KB), translated to `0xF100_0000`
- ATT Entry 1: PEER_IPC at PVTCR `0x8001_0000` - `0x8001_7000` (28KB), translated to `0xF110_0000`
- ATT Entry 2: SEC_REG at PVTCR `0x8001_8000` - `0x8001_9000` (4KB), translated to `0xF200_0000`

### IPC Sideband Cycle Details (HAS Section 8.14.1)

| IPC Channel | From | To | SrcID | DstID | Opcode | RS | FID | BARID | DB Address | DBM Address | CSR Address | MSG Range |
|-------------|------|----|-------|-------|--------|-----|-----|-------|------------|-------------|-------------|-----------|
| NVU -> ISH | NVU | ISH | nvu | ishbr | 0x7 | 0x0 | 0x0 | 0x0 | 0x2048 | 0x2054 | 0x26D4 | 0x20E0 - 0x215C |
| ISH -> NVU | ISH | NVU | ish | nvu | 0x7 | 0x0 | 0x0 | 0x0 | 0x7048 | 0x7054 | 0x76D4 | 0x70E0 - 0x715C |
| NVU -> ESE | NVU | ESE | nvu | ese_cse | 0x1 | 0x2 | 0x1 | 0x0 | 0x0 | 0x4 | 0x003C | 0x40 - 0xBC |
| ESE -> NVU | ESE | NVU | ese_cse | nvu | 0x7 | 0x0 | 0x0 | 0x0 | 0x5048 | 0x5054 | 0x56D4 | 0x50E0 - 0x515C |
| PMC -> NVU | PMC | NVU | pmc | nvu | 0x7 | 0x0 | 0x0 | 0x0 | 0x2048 | NA | NA | 0x20E0, 0x20E4 |

**Abbreviations**: DB = Doorbell, DBM = Doorbell Mirror, CSR = Control/Status Register, MSG = Message registers

### IPC Flows

#### Host <-> NVU IPC

Two modes are defined:

1. **Legacy (SB IRQ)** — IPC via IOSF sideband with AssertIRQ/DeAssertIRQ messages
2. **POR (MSI)** — IPC via MSI (Message Signaled Interrupt) — this is the Plan of Record

Host interrupt is delivered via IOSF2AXI Bridge Sideband as either AssertIRQ/DeAssertIRQ messages or MSI.

Host IPC is mapped to PCI Function 0 (NVU SW Driver), source: IPC IRQ.

#### ICP Protocol Headers (Source: FAS SVG — ICP Protocol Diagram)

NVU uses **ICP (Intel Communication Protocol)** for structured messaging over IPC channels. Two header types:

**`icp_logic_hdr_t` (4 bytes)** — Logical header for message routing:

| Bits | Field | Width | Description |
|------|-------|-------|-------------|
| 31:24 | `sequence_num` | 8b | Message sequence number for ordering |
| 23:16 | `capability_id` | 8b | Target capability/service ID |
| 15:9 | `message_type` | 7b | Message type within capability |
| 8 | `is_response` | 1b | 0 = Request, 1 = Response |
| 7:0 | Reserved | 8b | — |

**`icp_ipc_hdr_t` (4 bytes)** — IPC transport header:

| Bits | Field | Width | Description |
|------|-------|-------|-------------|
| 31:22 | `payload_size` | 10b | Payload size in bytes (max 1024) |
| 21:16 | `client_id` | 6b | Client identifier |
| 15:11 | `long_format_ver` | 5b | Long format version |
| 10 | `busy` | 1b | Doorbell busy flag |
| 9:0 | Reserved | 10b | — |

**Version Handshake**: On first IPC connection, host and NVU exchange `supported_formats` bitmask (e.g., `0x0001`) and negotiate `selected_handshake` version.

#### ESE <-> NVU IPC

Used for firmware authentication handshake and security management. NVU->ESE uses opcode `0x1` with RS=`0x2` (ESE root space) and FID=`0x1`.

**IPC Register Details (Source: HAS SVG — ESE↔NVU IPC)**:
- `NVU2ESE_DOORBELL_ESE` — NVU writes via IOSF SB MMIO WR (RS=2)
- `ESE2NVU_DOORBELL_ESE` — ESE writes via IOSF SB PVTCFG WR
- `SBEP_HW` registers: CSR, CSR_CLR, DB, DB_MIRROR
- Handshake: `ROWN_REQ[SBR]` assert/deassert for sideband routing

#### ISH <-> NVU IPC

Used for sensor hub communication. Both directions use opcode `0x7` with RS=`0x0`.

**IPC Reset Protocol**: NVU supports the IPC Reset Protocol via the CSR register. In the ISH↔NVU IPC channel, NVU acts as **Leader** and ISH acts as **Follower** (per FAS). The CSR register bits 0–3 manage the reset handshake; bits 4–31 are unused. Refer to the *Embedded Engines IPC HAS* for CSR register bitfield definitions.

**IPC Register Details (Source: HAS SVG — ISH↔NVU IPC)**:
- `NVU2ISH_DOORBELL_ISH` — NVU writes via IOSF SB PVTCFG WR
- `ISH2NVU_DOORBELL_ISH` — ISH writes via IOSF SB PVTCFG WR
- Same SBEP_HW register pattern: CSR/CSR_CLR/DB/DB_MIRROR

#### Host <-> NVU IPC — Signal-Level Detail (Source: HAS SVG)

**Legacy IRQ Mode**:
- NVU writes `NVU2HOST_DOORBELL_HOST` → triggers `Assert_IRQx#` via IOSF SB
- Host reads `NVU_HOST_FWSTS_HOST` and `NVU_HOST_COMM_HOST` via IOSF Primary MMIO RD
- Host writes `HOST2NVU_DOORBELL_HOST` via IOSF Primary MMIO WR
- Host clears IRQ via `DeAssert_IRQx#` sideband message

**MSI Mode (POR)**:
- Same register flow, but interrupt delivery via `MSI_GEN` block instead of Assert/DeAssert
- MSI_GEN uses `ROWN_REQ[PSF]` (not `[SBR]`) for PSF routing
- MSI_GEN arbiter: per-source REQ/GRANT, FSM states: `ARB_REQ` → `ARB_GNT` → `PENDING`
- Masking: `BMEK * !D3K * MSI_ENK` — masked in D3 or when MSI disabled
- `oob_msi_mask`/`oob_msi_pending` for per-vector masking

### VPX2 IPC Interrupt Map

| IRQ | Source | Description |
|-----|--------|-------------|
| 23 | IPC | HOST IRQ (`irq23_a`, offset `0x5c`) |
| 24 | IPC | VOD_HOST IRQ (`irq24_a`, offset `0x60`) |
| 25 | IPC | CSE IRQ (`irq25_a`, offset `0x64`) |
| 26 | IPC | PMC IRQ (`irq26_a`, offset `0x68`) |
| 27 | IPC | CNVI IRQ (`irq27_a`, offset `0x6c`) |
| 28 | IPC | ACE IRQ (`irq28_a`, offset `0x70`) |
| 29 | IPC | ESE IRQ (`irq29_a`, offset `0x74`) |
| 30 | IPC | BT IRQ (`irq30_a`, offset `0x78`) |
| 31 | IPC | ISH IRQ (`irq31_a`, offset `0x7c`) |
| 32 | IPC | SPARE0 IRQ (`irq32_a`, offset `0x80`) |
| 33 | IPC | SPARE1 IRQ (`irq33_a`, offset `0x84`) |
| 34 | IPC | SPARE2 IRQ (`irq34_a`, offset `0x88`) |

### FW IPC Care-Abouts (HAS Section 8.14.2.5)

- `ROWN_REQ/ack` will be held high throughout when sending NVU2* outbound. `ROWN_RQ` will be set before starting to write to all message registers, the DB pressed and will be cleared in the `busy_clr` handler.
- FW will not try to setup an outbound NVU2* DB again unless the previous outbound flow has completed (DB and busy_clr are reset).
- FW will not initiate any outbound or inbound HOST IPC during D3/BME flow starting from the warn message.
- FW will not send a D3/BME ack for a D3/BME warn unless it sees RS0 quiescence and no NVU2HOST outbound is pending (DB or Busy Clr is set).


## HECI Transport Protocol (FAS §7.2.3.16.1)

The Host-Embedded Controller Interface (HECI) is a transport protocol layered on top of IPC doorbell/mailbox messaging. It provides client-based multiplexing over the NVU↔Host IPC channel.

### Message Format

| Layer | Size | Key Fields |
|-------|------|------------|
| IPC Message Header | 32-bit | core_id, protocol, length (bits 9:0) |
| HECI Message Header | 32-bit | Client address (host + FW), message complete flag, length |

### HECI Bus Messages

| Message | Direction | Description |
|---------|-----------|-------------|
| `VERSION_REQ` | Host → NVU | Request HECI protocol version |
| `VERSION_RESP` | NVU → Host | Return supported HECI version |
| `CONNECT_REQ` | Host → NVU | Connect to a HECI client by GUID |
| `CONNECT_RESP` | NVU → Host | Accept/reject connection |
| `DISCONNECT_REQ` | Either | Disconnect a HECI client session |
| `DISCONNECT_RESP` | Either | Acknowledge disconnect |
| `FLOW_CTRL` | Either | Credit-based flow control token |
| `DMA_XFER_REQ` | Either | DMA-based large data transfer |

### HECI Clients

| Client | Purpose |
|--------|---------|
| **SMHI** (Sensor Management Host Interface) | Supporting dynamic algorithm load flows as well as providing basic NVU information such as FW version |
| **Trace** | FW trace/log streaming to host |

### SMHI Profiling Commands (FAS §7.5)

SMHI exposes profiling commands (debug-unlock only). Known commands include:

| Command | Description |
|---------|-------------|
| `SMHI_GET_FW_VER` | Get firmware version |

> **Note**: SMHI profiling requires debug-unlock fuse state. Not available in post-EOM and debug lock state.


## ARCSync VPX↔NPX IPC (FAS §7.5)

ARCSync provides inter-core communication between VPX2 DSP and NPX6-1K NNA cores. This is distinct from the Host IPC mechanism.

### Mechanism

- **Doorbell + shared memory** — hardware doorbell interrupt with shared SRAM message buffers
- **2 unidirectional lock-free ring buffers** — one VPX→NPX, one NPX→VPX
- **Use cases**: NPX boot/reset control, inference job dispatch, NPX status polling, NPX log aggregation

### VPX↔NPX Message Types (FAS §12, L13700-13800)

| Message ID | Direction | Purpose |
|-----------|-----------|---------|
| Core Boot | VPX → NPX | Initialize NPX core |
| Core Shutdown | VPX → NPX | Shut down NPX core |
| Inference Start | VPX → NPX | Dispatch NN inference job |
| Inference Complete | NPX → VPX | Signal inference completion with status |
| Log Flush | NPX → VPX | NPX log buffer ready for VPX aggregation |

### CoreState Enum (FAS §12, L13750)

| State | Value | Description |
|-------|-------|-------------|
| UNINITIALIZED | 0 | NPX not yet booted |
| READY | 1 | NPX booted, idle |
| BUSY | 2 | NPX executing inference |
| ERROR | 3 | NPX encountered error |


## Security Controls (HAS Section 14.9)

NVU has strict security and privacy goals. OEM-signed firmware components could potentially leak image data to host. To prevent this, HW enforces that the path to RS0 DRAM and Host IPC are disabled post-boot via write-once lock bits.

### RS0_DISABLE (HAS Section 14.9.1)

- **Write-once bit** set by BUP firmware during boot process
- When set: disables all firmware and hardware controlled DMA engines from initiating traffic towards HOST RS0 DRAM
- Boot/IO DMA: if `RS0_DISABLE && (TM[1:0] != 0x0 && (RD_RS || WR_RS) == 0x0)`, DMA_MISC forces `AxADDR[63] = 0` and redirects to reserved address `0xB000_0000`

### RS3_WR_DISABLE (HAS Section 14.9.2)

- **Write-once bit** set by BUP firmware during boot process
- When set: disables all FW/HW DMA engines from initiating RS3 writes to IMR DRAM
- Also blocks SMMU translations via VMEM -> EXTMEM from accessing RS3 for writes
- Paging DMA implements the same RS3_WR_DISABLE enforcement
- SIO DMA has no access to IOSF2AXI target port (connectivity not enabled in fabric)
- In **debug mode**, `RS3_WR_DISABLE` is 0, unlocking the path to IMR from VPX/NPX via SMMU VMEM for intermediate model result dumps

### IPC_DISABLE (HAS Section 14.9.3)

- **Write-once bit** set by BUP firmware during boot process
- When set: cuts off IPC communication between NVU and Host
- **⚠️ Critical ordering requirement** (HAS Feedback [3416]): `IPC_DISABLE` does **NOT** auto-clear the ATT HOST_IPC valid bit. FW must follow this exact sequence:
  1. Clear the ATT HOST_IPC valid bit — disables host MMIO access to HOST_IPC region
  2. **Then** set `IPC_DISABLE` — cuts off IPC communication between NVU and Host
  3. Disable writes to the ATT — prevents further ATT modifications
- Failure to follow this order leaves a window where Host IPC interrupt is masked but the HOST_IPC ATT entry is still valid — host MMIO reads to HOST_IPC would still succeed
- This ensures downstream MMIO accesses from Host are UR'd (Unsupported Request) by ATT

### ATT Write Protection

- When BUP sets the `ATT_WRITE_DISABLE` bit (write-once bit in SEC_REG block), ATT entries are frozen. Note: FW must first clear the valid bit for the ATT entry corresponding to Host IPC before disabling writes to the ATT, to ensure downstream MMIO accesses from Host are UR'ed by ATT
- This prevents malicious firmware code from opening memory/IPC windows to leak assets to Host


## WAMR Framework (FAS §11, L11634-12662)

NVU uses **WAMR (WebAssembly Micro Runtime)** as a lightweight sandbox for AON vision algorithms. This enables isolated execution of OEM-provided WASM apps alongside Intel core apps.

### Runtime Configuration

| Property | Value | Notes |
|----------|-------|-------|
| **POR execution mode** | **AOT (Ahead-of-Time)** | 1.04-1.29× native performance; compiled with `wamrc --target=arc` using MetaWare compiler |
| Thread model | Single Zephyr user-mode thread | All WAMR execution in one thread — no multi-threading within WASM |
| Memory mode | `Alloc_With_Pool` | Shared Heap: WAMR-managed + pre-allocated frame buffer |
| Shared heap location | Extension of WASM linear memory | Maps to pre-allocated pool in SRAM |

### Two-Layer Protection Model (FAS §11, L11680-11720)

| Layer | Mechanism | Enforced By |
|-------|-----------|-------------|
| Layer 1 | WAMR sandbox — WebAssembly linear memory model prevents out-of-bounds | WAMR runtime |
| Layer 2 | Zephyr user/kernel partition — MPU HW-enforced memory boundaries | MPU hardware |

### WAMR Architecture Layers (FAS §11, L11700-11750)

1. **WASM APP Layer** — Individual WASM applications (Core App, Camera App, Algorithm Apps)
2. **WAMR Layer** — App Manager + Runtime engine (AOT executor, memory manager, native API bindings)
3. **Zephyr Layer** — RTOS services, BSP, hardware abstraction

### App Manager Components (FAS §11, L11750-11800)

- **NVU Module** — WASM module loader/unloader
- **Shared Memory** — Inter-app data sharing via shared heap
- **Message Queue** — Inter-app message passing
- **NVU Loader** — Loads WASM apps from FW image or extension image
- **NVU Message Handler** — Routes messages between apps and services

### WAMR Native APIs (Source: FAS SVG — Application Architecture)

Key WAMR runtime APIs used by NVU App Manager:

| API | Purpose |
|-----|---------|
| `wasm_runtime_load()` | Load WASM module from binary |
| `wasm_runtime_instantiate()` | Create module instance with stack/heap |
| `wasm_runtime_create_exec_env()` | Create execution environment for module |
| `wasm_runtime_lookup_function()` | Resolve exported function by name |
| `wasm_runtime_call_wasm()` | Invoke WASM function |
| `wasm_runtime_deinstantiate()` | Destroy module instance |
| `wasm_runtime_unload()` | Unload WASM module |

### WASM Application Entry Points (Source: FAS SVG — app_mgmt_proc_seq)

Each WASM application type defines a standard entry function invoked by the App Manager during startup:

| Entry Function | Application Type | Description |
|---------------|-----------------|-------------|
| `wasm_core_app_entry()` | Core services | Entry point for core NVU services (vision pipeline orchestration, PM coordination) |
| `wasm_fd_app_entry()` | Face Detection | Entry point for face detection application (WoF, FaceID use cases) |
| `wasm_ft_app_entry()` | Face Tracking | Entry point for face tracking application (head orientation, onlooker detection) |

The App Manager startup sequence (FAS SVG — app_mgmt_startup_seq) loads each WASM module via `wasm_runtime_load()`, instantiates it, then calls the corresponding `wasm_*_app_entry()` function to begin execution.

### VPX-NPX FW Architecture Stack (Source: FAS SVG — VPX-NPX FW Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                      VPX2 DSP Core                              │
├─────────────────────────────────────────────────────────────────┤
│  NVU Driver Interface (disabled after FW load)                  │
├────────────────┬────────────────────────────────────────────────┤
│  HECI Service  │  Vision Service  │  Debug Service  │ SMHI Svc │
├────────────────┴────────────────────────────────────────────────┤
│  Config Service  │  Security & Privacy Service                  │
├─────────────────────────────────────────────────────────────────┤
│  CV & DSP Library  │  Pre/Post-Processing  │  Camera uDriver   │
├─────────────────────────────────────────────────────────────────┤
│  WAMR Runtime (AOT)  │  App Manager  │  Cross-Core Comm I/F    │
├─────────────────────────────────────────────────────────────────┤
│  BSP: I2C/I3C/GPIO/SPI Drivers  │  Vision2ISH  │  PM Driver    │
├─────────────────────────────────────────────────────────────────┤
│  Zephyr RTOS                                                    │
├─────────────────────────────────────────────────────────────────┤
│                      NPX6-1K NNA Core                           │
├─────────────────────────────────────────────────────────────────┤
│  NNRT (Neural Network Runtime)  │  IPC (Cross-Core)             │
└─────────────────────────────────────────────────────────────────┘
```

**Key observations from SVG**:
- NVU Driver Interface is **explicitly disabled** after FW load (IPC_DISABLE + RS3_WR_DISABLE)
- Vision2ISH provides integration with ISH virtual sensors
- NNRT (Neural Network Runtime) on NPX handles inference execution, coordinated via cross-core communication
- Cross-Core Comm Interface uses doorbell signaling + shared SRAM ring buffers

### WASM App Categories (FAS §11, L12500-12662)

| Category | Provider | Privilege | Shared Memory | Restartable | Max Count |
|----------|----------|-----------|---------------|-------------|-----------|
| **Core App** | Intel only | System (kernel APIs) | YES | NO (fatal if crashes) | 1 |
| **Camera App** | Intel/OEM | Limited (camera/ISP API only) | **NO** | YES | 1 |
| **Algorithm App** | Intel/3rd party | User mode | YES | YES (periodically after processing) | Multiple |

### Active App Entity Tree (FAS §11, L11850-11900)

WASM apps are organized in a tree structure per frame. Each node has a state:

| State | Color | Meaning |
|-------|-------|---------|
| Not yet executed | White | Pending execution in current frame |
| In progress | Gray | Currently executing |
| Complete | Black | Finished execution for current frame |

### Data Leaking Prevention (FAS §11, L12400-12500)

Data leaking prevention methodologies are applied in the Intel Core App to prevent 3rd party code from leaking data over the legal communication protocol. Key methodologies include:
- **Input validation**: Range check based on data format definition
- **Data correlation**: Cross-check within current frame and across multiple frames, zeroing out invalid data fields
- **Noise addition**: Avoid potential encoding of data from 3rd party apps
- **Attack detection**: Intel signed NVU FW is responsible to report potential attacks from 3rd party apps


## BSP Peripherals and Services (FAS §7.2-7.4, L5000-5800)

### Peripheral POR Status (FAS §7.2, L5100-5300)

| Peripheral | Instances | POR for Production | Speed | FIFO | Notes |
|-----------|-----------|-------------------|-------|------|-------|
| **GPIO** | 1 (16 pins) | **YES** | N/A | N/A | Sensor control, wake, camera mux |
| **I2C** | 3 | **YES** | 100/400 kbps | 64B | Master-only; sensor/camera control |
| **I3C** | 2 | **NOT POR** | Per MIPI I3C v1.0 | — | Synopsys DesignWare; reserved for future |
| **UART** | 3 | **NOT POR** | Up to 6 Mbps | — | Debug only in pre-production |
| **SPI** | 2 | **NOT POR** | Up to 25 Mbps | — | Reserved for future |
| **DMA** | 1 (8 ch) | **YES** | N/A | N/A | Synopsys DW AXI DMAC + SRAM-SS paging DMA + USB offload streaming DMA |

> **Validation Note**: I3C, UART, and SPI are **NOT POR** for production firmware. They exist in silicon but are not exercised by shipping FW. Validation should focus on GPIO, I2C, and DMA.

### Timer and Watchdog (FAS §7.3)

| Component | Type | Usage |
|-----------|------|-------|
| ARC Timer | VPX2 internal | Zephyr system clock (tick source) |
| HPET | 3 instances | AON domain wakeup timers |
| RTC | Counter | Persistent time reference (timestamps; no interrupt) |
| WDT | 1 instance | **1st timeout** = interrupt (FW recovery chance); **2nd timeout** = NVU reset |

### Hammock Harbor (FAS §7.3)

NVU is a **Hammock Harbor agent** with 3 local ART (Always Running Timer) sources:

| ART Source | Frequency | Usage |
|-----------|-----------|-------|
| XTAL | 38.4 MHz | High-resolution timestamps |
| AON clock | 2.56 MHz | Low-power domain timing |
| RTC | 32 KHz | Ultra-low-power persistent timer |

### IPC Channels (FAS §7.4)

| Channel | Peer | MMIO Size | Purpose |
|---------|------|-----------|---------|
| NVU ↔ Host | Host CPU | 4 KB | Driver communication, HECI transport |
| NVU ↔ ESE | ESE (Security Engine) | 4 KB | FW authentication, security services |
| NVU ↔ ISH | Integrated Sensor Hub | 4 KB | Sensor data exchange, face tracking |
| NVU ↔ PMC | Power Management Controller | 4 KB | Power state transitions, telemetry push |

### Security Service (FAS §7.10)

Face ID vector storage service:

| Parameter | Value |
|-----------|-------|
| `MAX_ASSETS_NUM` | 15 |
| `MAX_ENROLLMENT_PER_BOOT` | 10 |
| `MAX_STORAGE_SIZE` | 8192 bytes |

Face ID vectors are encrypted by ESE and stored in SPI NOR flash. At runtime, ESE decrypts vectors into SRAM for matching. After enrollment, ESE re-encrypts and writes back to SPI NOR.

#### Face ID Vector Lifecycle (Source: FAS SVG — Face ID Security Flow)

```
Boot Time:
  ESE decrypt → NVU_SRAM (Face ID Vector 8KB region)
  
Enrollment:
  Camera frame → FaceDetect → FaceTrack → Feature Extract → Enroll Vector
  → sec_svc_assets_add() → ESE encrypt → SPI NOR storage

Runtime Verification:
  Camera frame → FaceDetect → FaceTrack → Feature Extract → Query Vector
  → cv_svc_verify_face_id() → Cosine/L2Norm/DotProduct matching
  → Known (match > threshold) / Unknown (no match)

Session End:
  sec_svc_assets_store() → ESE re-encrypt → SPI NOR writeback
  SRAM region zeroed (Shared Memory Eraser)
```

Face ID Security APIs (from SVG):

| API | Purpose |
|-----|---------|
| `sec_svc_assets_info()` | Query stored asset count/metadata |
| `sec_svc_assets_retrieve()` | Decrypt and load asset from ESE |
| `sec_svc_assets_add()` | Encrypt and store new asset via ESE |
| `sec_svc_assets_store()` | Writeback modified assets to ESE/SPI NOR |
| `sec_svc_assets_delete()` | Remove asset from ESE storage |
| `cv_svc_verify_face_id()` | Run face verification against stored vectors |

#### Camera Config Service APIs (Source: FAS SVG — Camera Config Service)

| API | Purpose |
|-----|---------|
| `cfg_svc_cam_init()` | Initialize camera subsystem (ISP + PHY + sensor) |
| `cfg_svc_cam_cfg()` | Configure camera parameters (resolution, format, frame rate) |
| `cfg_svc_cam_start()` | Start camera streaming |
| `cfg_svc_cam_stop()` | Stop camera streaming |
| `cfg_svc_cam_deinit()` | Deinitialize camera subsystem, release resources |
| `nvu_ae_init()` / `nvu_ae_process()` / `nvu_ae_deinit()` | Auto-Exposure control lifecycle |
| `nvu_awb_init()` / `nvu_awb_process()` / `nvu_awb_deinit()` | Auto-White-Balance control lifecycle |

Camera working modes:
- **Exclusive Mode** — single owner (NVU or IPU) has full camera control
- **Concurrent Mode** — NVU and IPU share camera via PHY sharing arbiter + `cfg_svc_cam_3a_cfg_type_t` enum for 3A coordination

### MJPEG Decoder (FAS §7.12)

- **IP**: Synopsys VC9000NanoD
- **Mode**: Combined (decoder + post-processor integrated)
- **Gating**: Fuse-gated (`NVU_VSI9000NanoD_enable`), default disabled
- **Usage**: USB MJPEG camera decode pipeline


## Firmware Debug (HAS Section 15.3)

### DTF Firmware Tracing

- VPX FW supports DTF (Debug Trace Fabric) for sending FW tracing messages to Northpeak, even in S0ix state
- Supports MIPI Sys-T standard for FW tracing messages
- DTF Source Packetizer: register target that NVU FW can access to push debug messages
- DTF Encoder: sub-IP in NVU, interfaces to external DTF topology of arbiters targeting the trace aggregator
- FW debug messages transferred to trace aggregator in a **loss-less** fashion, in-order from end to end

### Model Debug

- In debug mode, NVU allows usage of IMR for dumping intermediate model results
- `RS3_WR_DISABLE` = 0 in debug mode, unlocking path to IMR from VPX/NPX via SMMU VMEM
- From debugger, reset code can be downloaded to alternate R/W memory such as AONRF
- Reset vector within VPX can be updated to point to AONRF


## FW Debug Services (FAS §7.2.6, L6633-7591)

The NVU FW provides multiple debug service categories beyond hardware debug interfaces (FAS §7.2.6):

### Logging Service

| Backend | Description | Availability |
|---------|-------------|-------------|
| **HECI** | Log streaming to host via SMHI client | Debug-unlock and production (filtered) |
| **UART** | Direct serial output (UART0/1/2) | Debug-unlock only; UART **NOT POR for production** |
| **DTF** | Debug Trace Fabric to Intel Trace Hub / NorthPeak | Always available (base FW); app FW DTF TTL-only in Post-EOM+Lock |

- **Format**: MIPI Sys-T catalog/dictionary mode (structured) + text mode (human-readable)
- **Filtering**: Per-module log level filtering (ERROR/WARN/INFO/DEBUG)
- **NPX logs**: Aggregated via shared SRAM buffer → VPX collects and routes to host

### Probe Service (FAS §7.2.6.3)

5 probe types with 8 commands for runtime inspection:

| Probe Type | Description |
|-----------|-------------|
| Image Dump | Capture ISP/camera frame at pipeline stage |
| Image Tune | Adjust ISP parameters at runtime |
| Image Probe | Read ISP statistics (AE, AWB, histogram) |
| NN Probe | Inspect NN inference intermediate tensors |
| System Probe | Read FW internal state variables |

### PNR (Playback and Record) Service

- **Record**: Capture raw camera frames and save algorithm debug data for deterministic replay and offline analysis
- **Playback**: Replay recorded frames by injecting camera data for offline debugging
- Intended to assist algorithm validation and regression testing

### Debug Policy Table (FAS §16, L19200-19400)

| State | OS SW Debug | FW Trace | DTF | Telemetry |
|-------|-----------|----------|-----|-----------|
| Pre-EOM + Unlock | All | All | All | All |
| Pre-EOM + Lock | All | All | All | All |
| Post-EOM + Unlock | All | All | All | All |
| Post-EOM + Lock | ROM/BUP only | Base FW only | TTL-only for App FW | Always |

> **FW Signature Policy**: Debug Key when debug-unlock, Production Key when debug-lock. Key managed by ESE.


## Crash Dump and Recovery (FAS §7.11)

### Crash Dump Storage

- **Location**: AONRF (Always-ON Register File) — persists through NVU resets but NOT through power removal
- **Content**: VPX core registers, stack trace, exception cause, FW state at crash time
- **No triple-fault**: This VPX core generation does not support triple-fault reset; crash dump is software-managed

### Recovery Flow

1. Watchdog timeout (WDT) 1st stage → NMI interrupt → FW attempts crash dump to AONRF
2. WDT 2nd timeout → NVU hardware reset
3. On next boot, ROM checks AONRF for crash dump marker (`SNOW_BALL` at `AON_END - 0x8`)
4. If crash dump present → BUP extracts and makes available to host via SMHI before normal boot continues

### Validation Care-Abouts

- Verify crash dump written to AONRF survives NVU-only reset (not platform reset)
- Verify SNOW_BALL marker at correct AONRF offset
- Verify crash dump content matches expected format (register snapshot, stack, exception code)
- Verify WDT 1st/2nd timeout intervals match FW configuration


## Telemetry (HAS Section 8.22)

NVU exposes telemetry registers for PMC to configure:

| NVU SB Address | Register | Description |
|----------------|----------|-------------|
| `0x20E0` | NVU_PMC_TELEMETRY_SRAM_REG0_BASE_OFFSET | Telemetry SSRAM base address (region 0) |
| `0x20E4` | NVU_PMC_TELEMETRY_SRAM_REG0_SIZE | Telemetry SSRAM size (region 0) |
| `0x20E8` | NVU_PMC_TELEMETRY_SRAM_REG1_BASE_OFFSET | Telemetry SSRAM base address (region 1) |
| `0x20EC` | NVU_PMC_TELEMETRY_SRAM_REG1_SIZE | Telemetry SSRAM size (region 1) |
| `0x20F0` | NVU_PMC_TELEMETRY_SRAM_FID | Telemetry SSRAM FID |
| `0x20F4` | NVU_PMC_TELEMETRY_GLOBAL_TELEMETRY_STATUS | Global telemetry enable status |

- These registers can be written anytime after NVU is out of reset (FW loading not required)
- Telemetry service enabled via PMC `Sleep_Level_Req[telemetry_service=1]` which sets `CRPM.TELEMETRY_SERVICE=1`
- NVU FW pushes telemetry data over IOSF_SB (SBEP) using MMIO WR SB syntax to PMC SSRAM (DWord by DWord)
- PMC stops telemetry service when CPU enters C10 via `Sleep_Level_Req[telemetry_service=0]`


## Test Scenarios

### Boot ROM Execution Test
1. Assert HW reset (PMC side_rst_b, prim_rst_b sequence)
2. Verify VPX core begins executing at BROM address `0x0000_0000`
3. Verify ROM reads `CRPM.SR_IN_PRG` and waits until 0
4. Verify ROM checks power status in CRPM registers; if exit from IPAPG, execution jumps to AON task
5. Verify SRAM scrub is performed as early as possible per security requirement
6. Verify ROM reads softstrap `NVU_WAIT_FW_LOAD_VISION_SERVICE`
7. If VISION_SERVICE not set, verify ROM enters D0i2 IPAPG

### Secure Boot Validation Test
1. Verify SRAM zeroization is triggered by ROM at boot start
2. Load FW image to RS0 DRAM
3. Trigger Boot DMA to copy from RS0 to RS3 (IMR)
4. Verify ESE authentication of FW in IMR
5. Verify SHA hash comparison (SRAM vs ESE) succeeds
6. Verify VPX begins executing authenticated FW from SRAM
7. Verify `IPC_DISABLE` and `RS3_WR_DISABLE` are set by BUP post-boot
8. Verify host IPC is cut off and RS3 write DMA transactions are blocked after configuration

### SHA-384 Engine Test
1. Program `SHACTL.ALGO` for SHA-384
2. Set `SHACTL.EN = 1` with `SHACTL.RSM = 0` for new hash
3. Feed known data via `PIBFPI` register
4. Wait for `SHASTS.BUSY = 0`
5. Read `SHARDWx` and compare with expected SHA-384 hash
6. Clear `SHACTL.EN = 0`
7. Verify SHA engine is clock-gated (writes to `PIBFPI` have no effect)

### IPC Host Communication Test
1. Verify HOST_IPC is accessible via ATT Entry 0 (MMIO `0x8000_0000`)
2. Send Host -> NVU doorbell message
3. Verify VPX2 IRQ 23 (HOST IRQ) fires
4. FW reads message registers and responds via NVU2HOST doorbell
5. Verify host receives MSI (POR) or SB IRQ (legacy)
6. Verify FW respects ROWN_REQ/ack protocol

### IPC Peer Communication Test (ESE)
1. Verify ESE_IPC accessible at VPX2 address `0xF110_4000`
2. Send ESE -> NVU sideband message (opcode 0x1, DstID=nvu, DB=0x0)
3. Verify VPX2 IRQ 29 (ESE IRQ) fires
4. FW processes message and responds via NVU -> ESE (opcode 0x1, RS=0x2, FID=0x1, DB=0x4, CSR=0x003C, address range 0x40-0xBC)

### Security Lock Bits Test
1. Verify `RS0_DISABLE` is write-once: set to 1, attempt to clear -> should remain 1
2. Verify `RS3_WR_DISABLE`: when set, all FW and HW controlled DMA engines are disabled from initiating RS3 writes to IMR DRAM
3. Verify `IPC_DISABLE` cuts off IPC communication between NVU and host
4. Verify FW clears the valid bit for the ATT entry corresponding to Host IPC before `ATT_WRITE_DISABLE` is set
5. Verify `ATT_WRITE_DISABLE` freezes ATT entries
6. Verify Host MMIO to IPC after disable returns UR (Unsupported Request), as ATT will UR downstream MMIO accesses from Host

### Boot with Lid Closed Test
1. Indicate lid closed to PMC (via IPC)
2. Verify NVU boot flow enters IPAPG after ROM execution
3. Verify NVU is ready for VNN removal in lid-closed state
4. Send lid-open IPC
5. Verify NVU exits IPAPG and proceeds with BUP/FW loading

### Exception Reset Recovery Test
1. Trigger watchdog expiry (VPX2 IRQ 47)
2. Verify VPX2 soft reset occurs
3. Verify RW/O bits (RS0_DISABLE, etc.) are cleared on exception reset
4. Verify ROM re-executes and FW can be re-loaded
5. Verify PME wakes host SW driver from D3 for re-load

### HECI Client Connection Test (FAS §7.2.3.16.1)
1. Open HECI transport channel to NVU via HOST IPC doorbell
2. Send `VERSION_REQ` — verify NVU responds with `VERSION_RESP` containing supported version
3. Send `CONNECT_REQ` with SMHI client GUID — verify `CONNECT_RESP` with success
4. Send SMHI `GET_FW_VER` command — verify FW version string is returned
5. Send `DISCONNECT_REQ` — verify `DISCONNECT_RESP` received
6. Verify `FLOW_CTRL` credit tokens are properly exchanged during transfer

### WAMR App Lifecycle Test (FAS §11)
1. Verify Core App (COREWASM) is loaded as permanent module during BUP
2. Verify WAMR runs in Zephyr user mode (MPU-enforced boundary)
3. Verify AOT compiled WASM app executes (AOT is TTL POR mode)
4. Verify Camera App has NO access to shared memory (isolation)
5. Verify Algorithm App CAN access shared memory
6. Verify Algorithm App can be disabled and de-instantiated without affecting Core App
7. Verify data leaking mitigations: noise addition, input validation (range check), and data correlation checks are applied by Intel Core App and ISH vision udriver

### SRAM Memory Layout Verification Test (FAS §7.1)
1. Verify NPX FW region starts at low SRAM address
2. Verify VPX FW region starts at 2MB SRAM offset
3. Verify total SRAM = 3584KB (7 slices × 512KB)
4. Verify NPX FW + CV Shared Memory ≤ 2MB combined
5. Verify NN Model alignment = 4KB (SMMU PageIn DMA requirement)
6. Verify NPX buffer alignment = 64 bytes
7. Verify Pre-allocated Pool blocks present: WAMR Heap, VPX FW Heap, CVISP buffers, Face ID Vector, NPX Log, IPC

### ARCSync Communication Test (FAS §7.2.3.11.2)
1. Verify VPX→NPX ring buffer is functional: send Core Boot message
2. Verify NPX responds via NPX→VPX ring buffer with READY state
3. Dispatch inference job via VPX→NPX — verify NPX transitions to BUSY
4. Wait for Inference Complete on NPX→VPX — verify status and result
5. Verify lock-free ring buffer semantics (no blocking on full/empty)

### Crash Dump Recovery Test (FAS §7.2.7)
1. Trigger a FW crash (e.g., null pointer dereference in debug mode)
2. Verify crash dump is written to AONRF (persists through NVU resets)
3. Trigger NVU reset — verify AONRF crash dump data survives reset
4. Verify host can read crash dump via SMHI after re-boot
5. Verify SNOW_BALL marker at `AON_END - 0x8` is valid

### BSP Peripheral POR Validation Test (FAS §7.2)
1. Verify I2C0, I2C1, I2C2 are functional (master-only, 100/400kbps, 64B FIFO) — **POR**
2. Verify GPIO instance with 16 pins responds to read/write — **POR**
3. Verify I3C instances (0, 1) are present but **NOT POR for production FW**
4. Verify UART instances (0, 1, 2) are present but **NOT POR for production FW**
5. Verify SPI instances (0, 1) are present but **NOT POR for production FW**


## PythonSV Patterns

Pending PythonSV namespace allocation for NVU IP. Below are tentative patterns based on HAS register descriptions:

```python
# NVU PythonSV namespace not yet allocated
# NVU is a PCI RCiEP on IOSF, sideband endpoint name: "NVU"
#
# === BROM / AONRF Memory Map ===
# BROM: 0x00000000 - 0x00004000 (16KB, read-only)
# AONRF: 0x01000000 - 0x01004000 (16KB, read/write)
#
# === HOST_IPC Memory Map ===
# HOST_IPC: 0xF1000000 - 0xF1001000 (4KB)
# SPARE_IPC: 0xF1001000 - 0xF1002000 (4KB)
#
# === PEER_IPC Memory Map ===
# CSE_IPC:  0xF1100000 - 0xF1101000
# PMC_IPC:  0xF1101000 - 0xF1102000
# CNVI_IPC: 0xF1102000 - 0xF1103000
# ACE_IPC:  0xF1103000 - 0xF1104000
# ESE_IPC:  0xF1104000 - 0xF1105000
# BT_IPC:   0xF1105000 - 0xF1106000
# ISH_IPC:  0xF1106000 - 0xF1107000
#
# === SEC_REG ===
# SEC_REG: 0xF2000000 - 0xF2001000 (4KB)
# Contains: RS0_DISABLE, RS3_WR_DISABLE, IPC_DISABLE, ATT_WRITE_DISABLE
#
# === SHA-384 Engine (within SRAMSS) ===
# SRAMSS_CFG: 0xF5000000 - 0xF5100000 (1MB)
# Key registers:
#   SHACTL.EN - Start/stop SHA operation
#   SHACTL.ALGO - SHA algorithm select
#   SHACTL.RSM / SHACTL.HRSM - Resume mode
#   SHASTS.BUSY - Operation in progress
#   SHARDWx - Hash result (SHA-384 = 384 bits = 12 DWords)
#   SHAIVDWx - Initial value for resume
#   SHAALDWx - Accumulated length for resume
#   PIBFPI - Write-only data input to SHA engine
#
# === Boot/IO DMA ===
# DMA:      0xF3800000 - 0xF3801000 (4KB)
# DMA_MISC: 0xF3900000 - 0xF3901000 (4KB)
#
# === ATT (Address Translation Table) ===
# ATT: 0xF2100000 - 0xF2101000 (4KB)
#
# === CRPM (Clock/Reset/Power Management) ===
# CRPM: 0xF3000000 - 0xF3001000 (4KB)
# Key fields:
#   CRPM.SR_IN_PRG - Save/Restore in progress
#   CRPM.VISION_SERVICE - Vision service enable
#   CRPM.TELEMETRY_SERVICE - Telemetry service enable
#
# === VPX2 IPC IRQ Map ===
# IRQ 23: HOST IPC IRQ
# IRQ 24: VOD_HOST IPC IRQ
# IRQ 25: CSE IPC IRQ
# IRQ 26: PMC IPC IRQ
# IRQ 27: CNVI IPC IRQ
# IRQ 28: ACE IPC IRQ
# IRQ 29: ESE IPC IRQ
# IRQ 30: BT IPC IRQ
# IRQ 31: ISH IPC IRQ
#
# === Security Fuses (SB address 0x0650) ===
# Bit[0]: NVU_VPX_HALT_Fuse (default=0)
# Bit[1]: NVU_HVM_MODE_Fuse (default=0)
# Bit[2]: NVU_Secure_Load_Fuse (default=1)
# Bit[3]: NVU_Debug_Mode_Fuse (default=0)
# Bit[4]: NVU_Softstrap_select_disable (default=1)
```


## See Also

- [registers/SKILL.md](../registers/SKILL.md) — HOST_IPC mailbox, SRAM registers
- [power/SKILL.md](../power/SKILL.md) — FW-driven power sequencing, PMC sideband
- [driver/SKILL.md](../driver/SKILL.md) — Host-FW IPC protocol, FW loading
- [inference/SKILL.md](../inference/SKILL.md) — Model loading, VPX2 boot, NN offload service
- [bios/SKILL.md](../bios/SKILL.md) — IMR allocation (16MB IMR18), BUP 80KB limit, UEFI capsule update (ESE sub-partition), NVU boot flow from BIOS perspective
- [platform/SKILL.md](../platform/SKILL.md) — Fuse/strap configuration
- [camera/SKILL.md](../camera/SKILL.md) — Camera pipeline, ISP, PHY sharing, USB camera offload
- [debug/SKILL.md](../debug/SKILL.md) — DTF trace, telemetry counters, profiling tools

## Reference Documents

| Document | Content | Key Sections |
|----------|---------|--------------|
| NVU HAS v1.0 (SIP_NVU_HAS.html) | Hardware register maps, boot flow, DMA, IPC, security | §8 (sub-IPs), §10 (boot), §13 (PM), §14 (security) |
| NVU FAS v1.0 (Firmware Architecture Specification) | FW stack, RTOS/BSP, WAMR, camera pipeline, security, debug | §6 (FW overview), §7 (RTOS/BSP), §9 (FW loading), §10 (security), §11 (WAMR), §12 (AON apps), §16 (FDK/debug) |
| NVU Security Architecture Spec | Threat model, privacy assets, TCB boundary | Contact: Ke Han |
| NVU BIOS Requirements (Rev 0.8RC) | BIOS init, enable/disable, PM config, camera ACPI | REQ1-REQ20, RTD3, vGPIO |

## Related Sub-Skills

- [fv-nvu/driver](../driver/SKILL.md) — Host driver interface, PCI enumeration, IPC, FW loading
- [fv-nvu/registers](../registers/SKILL.md) — MMIO/PCI register map, bitfields, offsets


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 01:12 | Facts added: 2371


### Additional HAS Details (418 facts)

#### Additional HAS Details

---

### NVU Hardware Overview (§5.1)

- NVU hardware blocks are described briefly below; full details are available in the NVU HAS document.

---

### RTOS and BSP (§7)

#### RTOS — Zephyr Kernel (§7.1)

- NVU firmware is based on **Zephyr RTOS** with NVU SoC/board support added.
- Many Zephyr OS services are adapted to NVU use cases, including: Power Management, Device Management, Logging, and others.
- The Zephyr kernel supports multiple architectures:
  - ARM (Cortex-A, Cortex-R, Cortex-M)
  - Intel x86
  - ARC
  - Nios II
  - Tensilica Xtensa
  - RISC-V
  - SPARC
  - MIPS
  - A large number of supported boards

---

#### Memory Management (§7.1.1)

##### Memory Layout (§7.1.1.1)

- Firmware image is loaded at the **2 MB** boundary.
- **Image Reformat Buffer**: Memory block used to store reformatted (e.g., rotated) image frames.
  - *Note (WIP)*: Assessment is ongoing to determine whether the Image Reformat Buffer can be optimized out via in-place rotation.
- **NPX Log**: Memory block used to store logs printed by NPX firmware.

##### Memory Access (§7.1.1.2)

- **VMEM** allows up to **16 MB** of addressable memory.

---

#### BSP — Zephyr NVU Enabling (§7.2.1)

- **SoC Layer**: Configures link options and SoC-specific settings.

---

#### Peripherals (§7.2.3)

##### SPI Controller (§7.2.3.5)

- NVU includes **2 SPI controllers**.
- SPI controller features:
  - Programmable SPI clock frequency range: **0.1 to 25 Mbits/sec** (NVU maximum rate: **25 Mbits/sec**)
  - Programmable character length: **2 to 16 bits**

##### Watchdog Timer (§7.2.3.8)

- Clock source: `func_clk_clock`

##### Streaming Transfer Unit — STU (§7.2.3.10)

- The **Streaming Transfer Unit (STU)** transfers data among memories inside and outside a multi-core cluster.

##### MJPG Decoder & Post Processing (§7.2.3.14)

- Two main software interfaces are present (see integrated structure diagram).
- **Integrated structure** covers the decoder/PP and its interfaces.
- In **combined mode**, the PP software internally communicates with the appropriate decoder library.
- The post-processor software internal structure and communication with decoder libraries are illustrated in the software internal structure diagram for combined mode.
- Software responsibilities include:
  - Handling input data ready notification
  - Feeding input data and performing decoding and/or down-scaling operations

---

##### HECI (§7.2.3.16)

###### HECI Transport Protocol (§7.2.3.16.1)

- Main data-related traffic between **NVU and HOST** uses the **HECI transport protocol**.

**HECI Transport Header — Bit Field Layout (32-bit word)**

| Bits | Field | Description |
|------|-------|-------------|
| 9:0 | `length` | Payload length (`uint32_t`; bits 9:0 of the lower length field) |
| 13:10 | `protocol` | Type of transport protocol (see Protocol Values table below) |
| 19:14 | `reserved` | Reserved |
| 23:20 | `length1` | Upper bits of length field (bits 23:20) |
| 27:24 | `core_id` | Core ID (bits 27:24) |
| 30:28 | `reserved` | Reserved (bits 30:28) |
| 31 | `B` | Reserved (bit 31) |

**Detailed Bit Assignments**

| Bit | Field |
|-----|-------|
| 31 | B (reserved) |
| 30 | reserved |
| 29 | reserved |
| 28 | reserved |
| 27 | core_id |
| 26 | core_id |
| 25 | core_id |
| 24 | core_id |
| 23 | length1 |
| 22 | length1 |
| 21 | length1 |
| 20 | length1 |
| 19 | reserved |
| 18 | reserved |
| 17 | reserved |
| 16 | reserved |
| 15 | reserved |
| 14 | reserved |
| 13 | protocol |
| 12 | protocol |
| 11 | protocol |
| 10 | protocol |
| 9 | length |
| 8 | length |
| 7 | length |
| 6 | length |
| 5 | length |
| 4 | length |
| 3 | length |
| 2 | length |
| 1 | length |
| 0 | length |

**Protocol Field Values (bits 13:10)**

| Value | Definition |
|-------|------------|
| 0 | `PROTOCOL_BOOT` |
| 1 | `PROTOCOL_HECI` |
| 2 | `PROTOCOL_MCTP` |
| 3 | `PROTOCOL_MNG` |
| 15 | `PROTOCOL_INVAILD` |

> *Note*: Bits 19:14 are reserved. Bits 23:20 carry the upper nibble of the length field (`length1`).


### Boot and Reset Sequences (21 facts)

#### Boot and Reset Sequences

#### NVU Firmware Architecture Overview

(HAS §6.1 NVU Firmware Architecture)

- NVU firmware is composed of two distinct components:
  - **Bring-UP (BUP) firmware** — an early-stage firmware responsible for initialization and firmware loading orchestration
  - **Main firmware** — the primary operational firmware loaded after BUP completes its tasks

---

#### ROM Boot Flow

(HAS §9.2.1 ROM Flow)

- The NVU ROM flow collaborates with **ESE** (Embedded Security Engine) to load BUP firmware from **IFWI** (Integrated Firmware Image).
- Upon successful BUP load and verification, **ROM transfers execution control to BUP** (i.e., jumps to BUP entry point).

---

#### BUP Boot Flow

(HAS §9.2.2 BUP Flow)

- BUP works in conjunction with **host software (SW)** and **ESE** to load NVU Intel/OEM firmware from the host.
- BUP relies on:
  - The **host SW driver** to load the firmware image from host memory to the NVU
  - **ESE** to perform firmware authentication
- The firmware load-from-host flow (from the SW perspective) is documented in **SwAS FW Loading from Host**.
- The host SW driver loads the **NVU application into System DRAM**.

##### Security Considerations During BUP Boot

(HAS §9.2.2 BUP Flow)

- A potential attacker may target the NVU boot flow by **modifying the manifest during boot**.
- NVU boot design includes specific mitigations against manifest tampering (e.g., an attacker modifying the manifest and subsequently reverting it to its original state).
- There is an inherent design trade-off between **boot security** and **boot flow complexity**:
  - Separating the manifest signing from the firmware image could mitigate some attack vectors.
  - However, this approach introduces **complicated signing and boot processes**, as well as potential **manifest/image mismatch issues**.
- The firmware flow enforces that execution continues **only when integrity checks are equal/verified** (HAS §9.2.3 FW Flow).

##### Extra BUP Tasks

(HAS §9.2.2.1 Extra BUP Tasks)

- **Trace Configuration Binary Save**
  - The NVU driver fetches the trace configuration binary from the Registry (if present) and passes it to the NVU for application.
  - BUP is responsible for retrieving and saving this binary.

- **Face ID Remove Indication Save**
  - The NVU driver fetches the Face ID remove indicator from the Registry (if present) and passes it to the NVU for application.
  - BUP is responsible for retrieving and saving this indicator.

---

#### Main Firmware (FW) Boot Flow

(HAS §9.2.3 FW Flow)

- High-level steps in the main FW boot flow include:
  - **Allocate memory space** for model pages.
  - Perform integrity verification; **only when checks are equal, continue execution**.

---

#### NPX Boot Flow

(HAS §13.7 NPX Power Management)

- The NPX (Neural Processing eXecution) boot flow includes a **data section operation** as part of its initialization sequence.

---

#### Reset Sequences

##### HECI Bus Reset

(HAS §7.2.3.16.1 HECI Transport Protocol)

| Message | Command Code | Payload Fields |
|---|---|---|
| `HECI_BUS_MSG_RESET_REQ` (Request) | `0x09` | `uint8_t command; uint8_t fw_addr; uint8_t host_addr; uint8_t reserved1;` |
| `HECI_BUS_MSG_RESET_RESP` (Response) | `0x89` | — |

##### Watchdog Expiry Reset

(HAS §12.1 Errors)

| Error Condition | Action |
|---|---|
| Watchdog Expiry | 1. FW Reset |

- Upon watchdog timer expiry, the system initiates a **firmware reset** as the primary recovery action.

---

#### Cross-References

(HAS §10.3 Quick Links to Related FAS Sections)

- **NVU Boot Flow** → See: *NVU Firmware Boot Flow* (HAS §9.2)


### Camera Interface (412 facts)

### Camera Interface

#### Overview

The NVU firmware Camera Interface provides support for MIPI CSI-2 camera sensors, the CVISP image signal processor, USB camera devices, and SIO peer-to-peer communication. The BSP layer includes device drivers for the MIPI CSI-2 PHY & Host Controller, I/O, CVISP, and IPC (HAS §6.1). The Configuration Service interacts with IPU/USB for camera sensor configuration (HAS §6.1).

---

#### MIPI CSI-2 Camera Interface (HAS §8.1)

##### PHY Sharing (HAS §8.1.1)

- The `IPU_claim` and `NVU_claim` registers are written by IPU FW and NVU FW respectively to negotiate ownership of a specific C/D-PHY.
- The `CDPHY_owner` registers are updated by HW and read by IPU or NVU FW to verify ownership acquisition.
- The `nvu_release_claim_req` signal is asserted to NVU when both `IPU_claim` and `NVU_claim` are asserted for any C/D-PHY. This wakes and interrupts NVU FW, which is expected to release `NVU_claim` so IPU can acquire ownership.
- FW provides the interface (`NVU_CDPHY_A/B/C_owner`) to select lanes to be used for sensing.
- FW listens on `nvu_release_claim_req` and receives an interrupt via `NVU_release_claim_irq` when it is asserted.
- FW monitors `CDPHY_owner` registers and receives an interrupt via `NVU_ownership_release_irq` when they change.
- **FW shall enable the XTAL clock prior to interacting with IPU for PHY sharing.** Refer to XTAL Clock Req/Ack Flows in NVU HAS.
- **FW shall disable the XTAL clock after putting the PHY to shutdown** to allow the Arbitration Logic to enter clock gating (CG).

##### Camera Control Interface Sharing (HAS §8.1.2)

- During system boot, NVU may be unable to provide timely acknowledgment if `release_irq` occurs before NVU FW is loaded.

##### Camera Sensor Control — MIPI Camera MCLK (HAS §8.1.3.1)

- NVU FW is responsible for controlling MCLK enable via the HW-provided register.
- The clock selection from NVU is unused.

##### CSI-2 Host Controller (HAS §8.1.4)

- Zephyr does not have native CSI-2 host controller driver support.
- NVU FW defines custom CSI-2 host controller driver APIs to provide the required functionality. Refer to the NVU CSI-2 Host Controller driver documentation for API details.

---

#### CVISP (Image Signal Processor) (HAS §8.2)

##### Driver Support (HAS §8.2)

- Zephyr does not have native ISP driver support.
- NVU FW defines ISP driver APIs for NVU ISP functionality. Refer to the NVU CVISP Driver documentation for Zephyr API definitions.

##### CVISP Output (HAS §8.2.2)

- CVISP supports image output in the following formats and resolutions:

| Format | Supported Resolutions |
|--------|-----------------------|
| NV12   | 640×480, 640×360, 320×240, 320×180 |
| YUYV   | 640×480, 640×360, 320×240, 320×180 |
| Y8     | 640×480, 640×360, 320×240, 320×180 |
| RGB    | 640×480, 640×360, 320×240, 320×180 |

- **POR configuration** supports Y8 format at 320×240 or 320×180 resolution.

##### CVISP Pipeline Partition (HAS §8.2.3)

- CVISP has two power domains: **Power Domain 1 (PD1)** and **Power Domain 2 (PD2)**. Refer to NVU HAS for further details.
- The **SOP block in PD1** is used for Motion Detection, which serves as the first-level trigger for NVU AON Vision use cases.

**CVISP Pipeline Mode Transitions:**

1. After NVU Main FW is up, NVU FW configures CVISP to **Motion Detection mode**: PD1 is powered up, PD2 is clock-gated.
2. When motion is detected, SOP generates an interrupt and NVU FW switches CVISP to **full pipeline mode**: PD2 clock is ungated.
3. Video frames are processed by the full CVISP pipeline and output.

##### Memory Layout for CVISP (HAS §7.1.1.1)

- **CVISP 2A Statistics Buffer**: Memory block used to store statistics generated by CVISP.
- **CVISP Output Buffer**: Memory block used to store image frames generated by CVISP. The extra 128 bytes at the end store metadata describing the frame buffer format.

---

#### USB Camera SIO (HAS §7.2.3.15)

- The USB Camera SIO driver enables:
  - Streaming of data from the xHCI controller to the IPU
  - Management of camera sensor controls
  - EP-0 programming
  - Configuration of xHCI registers
  - Firmware-level device management

##### USB Camera Enumeration (HAS §7.2.3.15.1.1)

Two types of enumeration flows are supported:

- **xHCI hosted by software**: xHCI detects the device and signals a Port Status Change event.
- **Hardware-assisted enumeration**: refer to the Device Enumeration flow documentation for full details.

---

#### SIO Peer-to-Peer Communication (HAS §8.4)

##### Overview (HAS §8.4)

- SIO is a connection-oriented, message-based communication protocol built on PCIe VDMs (Vendor Defined Messages).
- An SIO message may comprise multiple PCIe Transaction Layer Packets (TLPs).
- SIO messages are categorized into two types:
  - **Notification Messages**: Not flow controlled; do not require space credit for transmission.
  - **Data Messages**: Flow controlled.

##### VDM Header (HAS §8.4.1.1)

- The VDM header is constructed and managed by NVU HW and is **transparent to FW**.

| Bits | Field | Description |
|------|-------|-------------|
| 4:0 | Type | TLP type. Value `0x7F` = Vendor Defined Message |
| 6:5 | Fmt | TLP format. `3'b001` = 4 DW header, no data; `3'b011` = 4 DW header, with data |
| 7 | T | Reserved. Fixed as `1'b0` |
| 8 | TH | Transaction Hint (TH): If set to 1, the TLP includes a transaction processing hint |
| 9 | R | Reserved. Fixed as `1'b0` |
| 10 | Attr | Attributes. Fixed as `1'b0` |
| 11 | R | Reserved. Fixed as `1'b0` |
| 14:12 | TC | Traffic Class (TC): Specifies the traffic class command attribute. Fixed as `3'b000` |
| 15 | R | Reserved. Fixed as `1'b0` |
| 17:16 | Length[9:8] | Upper 2 bits of TLP length. Fixed as `2'b00` |
| 19:18 | AT | Address Translation. Fixed as `2'b00` |
| 21:20 | Attr | Attributes. Fixed as `2'b00` |
| 22 | EP | Error Present (EP): Asserted if the transaction contains poisoned data. Fixed as `1'b0` |
| 23 | TD | TLP Digest (TD): If asserted (=1), indicates presence of an ECRC field. Fixed as `1'b0` |
| 31:24 | Length[7:0] | Length of the TLP. Value of 1 = 1 DW, value of 2 = 2 DWs, value of 0 = 1024 DW |
| 47:32 | Requester ID[15:0] | BDF of the Requester |
| 55:48 | Msg Code | Message Code. Value `0x7F` = Vendor Defined Message |
| 63:56 | Tag | Transaction Tag |
| 71:64 | Target Route ID[15:8] | BDF of the Target (upper byte) |
| 79:72 | Target Route ID[7:0] | BDF of the Target (lower byte) |
| 87:80 | Vendor ID[15:8] | Vendor ID (upper byte). Fixed as `0x86` |
| 95:88 | Vendor ID[7:0] | Vendor ID (lower byte). Fixed as `0x86` |
| 103:96 | SIO Protocol | SIO Protocol identifier |
| 111:104 | SIO Target Pin# | Target SIO Pin number. Bit[7] = End of Message (EOM) flag |
| 119:112 | Dependent | Use of this field depends on the SIO Packet Type |

---

#### MJPEG Decoder & Post Processing (HAS §7.2.3.14)

- NVU firmware includes a DWL implementation for Zephyr, an `mjpeg_dec_pp` device driver, and a camera configuration service that collaborate with hardware to complete MJPEG decode and post-processing tasks.

---

#### Sensor Management Host Interface (SMHI) (HAS §7.2.3.16.1.1)

- SMHI is a set of functionalities and state reports exposed to the host via the HECI client interface.
- Responsibilities include:
  - Supporting dynamic algorithm load flows
  - Providing basic NVU information such as FW version


### Clock and Power Gating (2 facts)

#### NPK Power Gating (HAS 16.2.2)

- On retail devices, NPK is power gated by BIOS by default
- To enable NPK on retail devices, one of the following conditions must be met:
  - A valid debug token is present, **or**
  - The KET bit is enabled in the ECTRL register

#### NPX Clock Gating Telemetry (HAS 16.2.5)

The following telemetry field is exposed for debug and profiling purposes related to NPX clock gating state:

| Field | Type | Unit | QW | Usage | Comment |
|---|---|---|---|---|---|
| NPX Sleep Counter | Counter | RTC Tick | QW5 | Debug & Profiling (FW) | NPX Clock Gated |

- The **NPX Sleep Counter** increments in RTC Tick units while the NPX is in a clock-gated state
- This counter is accessible via telemetry quadword **QW5** and is intended for firmware-level debug and profiling workflows


### DMA Architecture (29 facts)

#### DMA Architecture

#### Overview

The NVU DMA subsystem manages data movement between host memory, IMR (Isolated Memory Region) DRAM, and internal SRAM. DMA engines are hardware-controlled, with a programming interface exposed to NVU firmware. Only NVU FW is permitted to program the DMA engine. (HAS §14 Security and Access Control > 14.2)

---

#### DMA Engine Types

- **Internal DMA (SMMU-managed):** The SMMU logic includes a dedicated DMA engine that manages data movement from virtual to physical memory. The DMA is under HW control; HW provides a programming interface to FW for page management. (HAS §2.5.1.7.3)
- **External DMA (Ext DMA / Host DMA):** The Ext DMA block uses the AXI Target Interface #1 to initiate transactions to the IOSF interface via the IOSF Primary Initiator interface. A second AXI Target Interface (#2) is also present on the IOSF-to-AXI Bridge. (HAS §2.5.1.11)
- **STU DMA:** The STU (Speed Transfer Unit) peripheral exposes an asynchronous DMA copy API (`speed_stu.h`). The driver API fills an STU descriptor with the DMA copy request and issues an async transfer. (HAS §7.2.3.10.1)

---

#### DMA and Memory Management

- Page swapping is **not allowed**. All firmware components (except NN models) are loaded directly into SRAM. (HAS §7.1.1.2)
- After BUP (Bring-Up Phase), IMR can only be accessed in **one direction (read only)**. (HAS §7.1.1.2)
- To support multiple NN models, models are loaded and executed **sequentially** to maximize SRAM utilization:
  - All NN models are initially loaded into NVU IMR.
  - The NN model to be scheduled is then loaded from IMR into SRAM via DMA. (HAS §7.1.1.4)

---

#### Security Controls and One-Way DMA Enforcement

- **Boot Security Requirement:** One-way DMA from IMR to SRAM must be enabled after FW downloading (applicable in EOM production debug-locked case). (HAS §9.1.1)
- **BUP Security Configuration:** During BUP, the following security settings are established:
  - `IPC_DISABLE` — cuts off IPC communication between NVU and host.
  - `RS3_WR_DISABLE` — enforces one-way DMA from IMR (RS3) to SRAM; disables write-back direction. (HAS §9.2.2.1)

#### Global DMA Security Controls

| Control Bit | Behavior |
|---|---|
| `RS0_DISABLE` | When set, disables **all** firmware- and hardware-controlled DMA engines from initiating traffic towards HOST RS0 DRAM. (HAS §14.9.1) |
| `RS3_WR_DISABLE` | When set, disables **all** firmware- and hardware-controlled DMA engines from initiating RS3 **writes** to IMR DRAM. (HAS §14.9.2) |

---

#### HECI DMA Transfer Protocol

The HECI bus supports a dedicated DMA transfer command used for host-to-firmware data movement:

| Command | Command ID | Request Structure |
|---|---|---|
| `HECI_BUS_MSG_DMA_XFER_REQ` | `0x12` | `uint8_t command;` `uint8_t fw_addr;` `uint8_t host_addr;` `uint8_t reserved;` `uint64_t` host memory address (bits 0–11 must be 0) |

(HAS §7.2.3.16.1)

- The host memory address field in `HECI_BUS_MSG_DMA_XFER_REQ` **must have bits 0–11 cleared** (i.e., address must be 4 KB aligned).

---

#### Host DMA Access Control Registers

The following registers configure SAI (Source Attribute ID) based read and write access policies for the Host DMA register block. All registers are reset by `FUNCRST` and reside in the `nvu_sec_reg_top` IOSF Sideband Message space. (HAS §CRIF: nvu_sec_reg_top_IOSF_SideBand_Msg)

| Name | Offset | Size | Reset (SAI_MASK) | Access | Description |
|---|---|---|---|---|---|
| `NVU_HOST_DMA_RAC_LO` | `0x9200` | 32 bits | `0x0100001E` | RW | Read Access Control Policy (low 32 bits). SAI bit-vector determining which agents have read access to Host DMA registers. |
| `NVU_HOST_DMA_RAC_LO.SAI_MASK` | `0x9200` [31:0] | 32 bits | `0x0100001E` | RW | Bit-vector for read access; agent granted access when its SAI bit is set. |
| `NVU_HOST_DMA_RAC_HI` | `0x9204` | 32 bits | `0x00080C00` | RW | Read Access Control Policy (high 32 bits). |
| `NVU_HOST_DMA_RAC_HI.SAI_MASK` | `0x9204` [31:0] | 32 bits | `0x00080C00` | RW | Bit-vector for read access (upper SAI range). |
| `NVU_HOST_DMA_WAC_LO` | `0x9208` | 32 bits | `0x0100001E` | RW | Write Access Control Policy (low 32 bits). SAI bit-vector determining which agents have write access to Host DMA registers. |
| `NVU_HOST_DMA_WAC_LO.SAI_MASK` | `0x9208` [31:0] | 32 bits | `0x0100001E` | RW | Bit-vector for write access; agent granted access when its SAI bit is set. |
| `NVU_HOST_DMA_WAC_HI` | `0x920C` | 32 bits | `0x00080C00` | RW | Write Access Control Policy (high 32 bits). |
| `NVU_HOST_DMA_WAC_HI.SAI_MASK` | `0x920C` [31:0] | 32 bits | `0x00080C00` | RW | Bit-vector for write access (upper SAI range). |

- RAC (Read Access Control) and WAC (Write Access Control) are split into `_LO` and `_HI` halves to cover the full 64-bit SAI space as two 32-bit registers.
- The reset values of `RAC_LO` and `WAC_LO` are identical (`0x0100001E`), as are `RAC_HI` and `WAC_HI` (`0x00080C00`), reflecting a symmetric default read/write access policy.


### DSP Core (VPX2) (75 facts)

#### DSP Core (VPX2)

### Overview

The VPX2 is the DSP/scalar control core of the Intel NVU (Neural Vision Unit). It serves as the primary control processor, running the RTOS, BSP, and services that manage NVU control logic, neural network offload scheduling, and inter-core communication with the NPX core. (6.1, 16.1.1.1)

---

#### RTOS and Firmware Identity

- **RTOS:** Zephyr is selected as the RTOS running on the VPX2 core. (6.1)
- Zephyr includes upstream support for the ARC VPX core; refer to Zephyr ARC processor support status for details. (7.2.1)
- The VPX firmware (`zephyr.bin`) is the control core responsible for managing NVU control logic. (16.1.1.1)
- VPX FW is signed by Intel and is part of the Trusted Computing Base (TCB). (10.2.1)

**Module Manifest Entry** (6.2.3.1.1)

| Module Name | Binary File  | Purpose             |
|-------------|-------------|---------------------|
| VPX_CORE    | zephyr.bin  | VPX core firmware   |

---

#### Firmware Image Structure

The VPX firmware binary is encapsulated within the NVU image with the following layout fields (6.2.1):

| Field           | Size (bytes)   | Description          |
|-----------------|----------------|----------------------|
| VPX FW Manifest | 64             | VPX Module Manifest  |
| VPX FW binary   | VPX FW size    | VPX FW binary        |

- The Base NVU Firmware package includes: VPX core firmware, NPX core firmware, Core WASM App, and AON image. (16.1.1.6)
- The VPX firmware source is located in the `vpxfw` folder, which contains BSP, board definitions, applications, etc. (16.1.1.2)
- The VPX firmware binary is output as `zephyr.bin` (for BASE firmware). (16.1.1.6.8)

---

#### Memory Layout and Management

##### Memory Regions (7.1.1.1)

- **VPX FW:** Loaded at the **2 MB offset of SRAM**, containing text and data sections for BSP device drivers, RTOS, and services executed and accessed by the VPX core.
- **VPX FW Heap:** Runtime memory required by kernel services is dynamically allocated from this region.
- **IPC:** A dedicated memory block used for cross-core communication between VPX and NPX.

##### Memory Protection (7.1.1.3)

- **Core-based access protection:**
  - VPX core has access to the **entire SRAM**.
  - NPX core is restricted to: NPX FW, CV Shared Memory, pre-allocated frame buffer memory blocks, NPX Log, and IPC.
- **MPU-based access protection:**
  - Within VPX, User Space components (App Manager, WAMR, WASM Apps) are restricted to **WASM Heap only**.
  - Memory access control is implemented via Zephyr's Memory Protection Unit (MPU) support.
- Intel VPX FW uses HW mechanisms to limit NPX runtime memory access to WAMR shared memory and NN models. (10.2.2)

##### Dynamic Load Flow (7.1.1.4)

- The Core App in VPX FW schedules WASM Apps (1, 2, 3, …) sequentially into execution.
- For each WASM App execution, the app allocates buffers from CV Shared Memory for:
  - NN Output
  - NN Input
  - Intermediate buffers for CV pre-processing
  - NN Model

---

#### Scheduling (7.1.2)

**Scalar Core Workloads**
- RTOS, BSP, and services run on the VPX2 scalar core with multi-thread support.
- Zephyr RTOS supports interrupts and context switches among multiple threads.

**DSP Workloads**
- The VPX2 DSP core **does not support preemption**.
- All DSP tasks (e.g., pre/post-processing functions) are executed **sequentially** on the DSP.

**Algorithm Scheduling**
- For any algorithm pipeline, the sequence is strictly ordered:
  1. Pre-processing on VPX
  2. NN computation on NPX
  3. Post-processing on VPX
- This sequence is scheduled within a single WASM App in sequential order; WASM App-level scheduling is message-driven.

---

#### VPX2 Interrupt Table (8.1.1)

> **Note:** ISH-specific interrupts are reserved for NVU use (e.g., IPC to ACE, BT, CNVI). Several IRQ entries are under review for removal per open feedback items. (8.1.1)

| Index | Module | IRQ Name    | IRQ Pin  | Address |
|-------|--------|-------------|----------|---------|
| 23    | IPC    | HOST IRQ    | irq23_a  | 0x5C    |
| 24    | IPC    | VOD_HOST IRQ *(under review)* | irq24_a | — |
| 25    | IPC    | CSE IRQ *(under review)*     | irq25_a | 0x64    |
| 26    | IPC    | PMC IRQ     | irq26_a  | 0x68    |
| 27    | IPC    | CNVI IRQ *(under review)*    | irq27_a | 0x6C    |
| 28    | IPC    | ACE IRQ *(under review)*     | irq28_a | 0x70    |
| 29    | IPC    | ESE IRQ     | irq29_a  | 0x74    |
| 30    | IPC    | BT IRQ *(under review)*      | irq30_a | 0x78    |
| 31    | IPC    | ISH IRQ     | irq31_a  | 0x7C    |
| 32    | IPC    | SPARE0 IRQ  | irq32_a  | 0x80    |
| 33    | IPC    | SPARE1 IRQ  | irq33_a  | 0x84    |
| 34    | IPC    | SPARE2 IRQ  | irq34_a  | 0x88    |

---

#### VPX2 Memory Map (8.2.2)

| Block    | Sub Region | Sub Region Size | Start Address | End Address  |
|----------|-----------|-----------------|---------------|--------------|
| ESE_IPC  | ESE_IPC   | 4 KB            | 0xF1104000    | 0xF1105000   |

---

#### Timers (2.5.1.14)

| Timer     | Clock Source | Frequency | Description                                                                 |
|-----------|-------------|-----------|-----------------------------------------------------------------------------|
| VPX Timer | Func Clock  | 400 MHz   | Timer internal to VPX                                                       |
| Local ART (XTAL) | XTAL Clock  | 38.4 MHz  | NVU local ART timer running on XTAL clock, synchronized to global ART in SoC |
| Local ART (PGCB) | PGCB Clock  | 2.56 MHz  | NVU local ART timer running on PGCB clock |
| Local ART (RTC)  | RTC Clock   | 32 KHz    | NVU local ART timer running on RTC clock |

---

#### Cross-Core Communication: VPX ↔ NPX (7.2.3.11.2)

##### Architecture

- VPX and NPX communicate via a **Doorbell + Shared Memory** architecture, eliminating busy-waiting and continuous polling.
- The doorbell leverages the **ARCSync interrupt**, serving as both a wake signal (if the peer core is in sleep) and a notification mechanism.
- ARCSync is the primary mechanism used for VPX ↔ NPX communication in NVU.

##### Ring Buffers (7.2.3.11.2.1)

- Two **unidirectional lock-free ring buffers** are pre-allocated in shared memory:
  - **VPX-to-NPX command ring**: carries commands from VPX to NPX.
  - **NPX-to-VPX response ring**: carries responses from NPX back to VPX.

##### Message Flow

- **VPX → NPX:** VPX writes to the command ring buffer, then signals the **VPX2NPX doorbell** to wake NPX.
- **NPX → VPX:** Upon task completion, NPX writes to the response ring buffer, then signals the **NPX2VPX doorbell** to notify VPX.

##### IPC Manager API (12.9.3)

The following IPC Manager APIs are available on the VPX side:

| API Name                  | Parameters                                        | Description                              |
|---------------------------|---------------------------------------------------|------------------------------------------|
| `IPCManagerInit()`        | `IPCManager* manager, uint32_t ShareMemAddress`   | Initialize IPCManager and set VPX to Ready |
| `IPCManagerIsNPXReady()`  | `IPCManager* manager`                             | Handshake to check if NPX is ready       |
| `IPCManagerEncodeMessage()` | `IPCManager manager, const IPCMessage msg`      | Encode an IPC message                    |
| `IPCManagerDecodeMessage()` | `IPCManager manager, IPCMessage msg`            | Decode an IPC response                   |

**IPC Manager Data Structures** (12.9.3)
```c
CoreContext       Context[NUM_CORES];
IPCMessage        MessageContext[NUM_CORES];
CoreShareMemory*  sharedMemory;
```

---

#### NN Offload Service (12.9.2)

- The NN offload service is decomposed into two components:
  - **Workload Scheduler** — runs on VPX side
  - **Workload Executer** — runs on NPX side
- NVU VPX connects with external modules (e.g., ISH) through IPC. (12.8)

---

#### Power Management (13.5)

##### AON Task (13.5.1)
- The AON task is located in **AONRF memory** (un-gated power domain).
- It handles **D0i2 and IPAPG entry/exit flow**, including saving and restoring VPX core registers and stack contents to/from AON memory.

##### Boot ROM (13.5.2)
- Boot ROM executes when VPX core is brought out of reset.
- It checks power status saved in CRPM registers; if an IPAPG exit is detected, execution jumps to the AON task to continue.

##### Reset Debug (8.3.5.1)
- From a ROM debug perspective, it is possible to bypass ROM in order to debug reset vector code.

---

#### Telemetry and Profiling (16.2.5)

| Usage              | Field            | Type    | Unit     | QW   | Description              |
|--------------------|-----------------|---------|----------|------|--------------------------|
| Debug & Profiling  | D0.200M Counter  | Counter | RTC Tick | QW1  | VPX active at 200 MHz    |
| Debug & Profiling  | D0.400M Counter  | Counter | RTC Tick | QW1  | VPX active at 400 MHz    |
| Debug & Profiling  | D0.Sleep Counter | Counter | RTC Tick | QW2  | VPX Clock Gated          |

---

#### Logging (7.2.6.1.5, 16.1.4)

- VPX and NPX logs are **mixed in output lines**; a header must be added to each line to identify NPX log entries.
- NPX writes logs into a shared buffer with a header; VPX collects and re-encodes them into **Sys-T format** for uniform output.
- The logging tool must include labels identifying which NPX core produced each log entry.

---

#### Security (10.2.1, 10.2.2, 11.6.1)

- VPX FW is **signed by Intel** and is part of the TCB.
- VP


### Debug and Trace (144 facts)

### Debug and Trace

---

#### Overview

The NVU firmware provides a comprehensive set of debug and trace mechanisms to support firmware developers, customers, and production diagnostics. These mechanisms span logging, profiling, probe/playback-record services, DTF hardware trace output, telemetry, and crash dump capabilities. (§7.2.6, §16.2)

---

#### Debug Mechanisms and Policy

### Firmware Debug Mechanisms (§16.2.1)

- **Base FW traces to DTF** — NVU base firmware traces are exposed to DFT and can be routed to multiple destinations (NPK or DDR).
- **App FW traces to DTF** — NVU application firmware traces are exposed to DFT and can be routed to multiple destinations (NPK or DDR).
- **OS debug and log** — Message-based debug logging available across debug lifecycle stages.
- **OS image dump, tuning, probe** — Image capture and pipeline probe capabilities.
- **OS profiling with FW statistics** — Performance statistics collection; available only in debug-unlocked mode.
- **IP telemetry** — Hardware and firmware telemetry counters and snapshots.
- **JTAG debug** — Hardware-level debug interface.
- **NN Algorithm Profiling** — Algorithm-specific test/debug feature supported by specific algorithm test firmware. (§16.2.1)

---

### Firmware Debug Policies (§16.2.2)

The following table describes which debug mechanisms are available across lifecycle and lock-state combinations.

> **Note:** "Post-EOM & Debug Unlock" is functionally identical to "Pre-EOM & Debug Unlock" and "Pre-EOM & Debug Lock" in terms of capability availability, but the actual firmware images running in the NVU differ across these states. (§16.2.2, Notice #3)

| Debug Mechanism | Pre-EOM & Debug Unlock | Pre-EOM & Debug Lock | Post-EOM & Debug Unlock | Post-EOM & Debug Lock |
|---|---|---|---|---|
| OS debug and log | Support | Support | Support | Only ROM/BUP |
| OS image dump, tuning, probe | Support | Support | Support | No Support |
| OS profiling w/ FW statistics | Support | Support | Support | No Support |
| IP telemetry | Support | Support | Support | Support |
| JTAG debug | Support | Support | Support | No Support |
| Base FW traces to DTF | Support | Support | Support | Support ¹ |
| App FW traces to DTF | Support | Support | Support | Support (TTL) ² / No Support (HML+) |
| NN Algorithm Profiling | Support | Support | Support | No Support |

**Notes:**

1. Base FW traces to DTF remain supported in Post-EOM & Debug Lock state. (§16.2.2)
2. In TTL, App FW originates from Intel; therefore App FW traces to DTF may be exposed. In HML and beyond, App FW originates from third parties — traces will **not** be exposed to DTF in the Post-EOM & Debug Lock state. (§16.2.2, Notice #2)
3. Third-party application log to DTF (NPK or DDR) is disabled after EOM in production locked SoC systems. (§10.2.2)
4. The host interface for NVU firmware download is disabled after downloading in the EOM production debug locked case. (§9.1.1)

---

#### DTF Trace Output (§7.2.3)

- NVU HW includes **DTF source packetizer and encoder** peripheral blocks to support firmware instrumentation trace output to the **Intel Trace Hub**.
- DTF trace output supports routing to multiple destinations: **NPK** or **DDR**.
- The DTF peripheral is used by both Base FW and App FW trace paths. (§7.2.3, §16.2.1)

---

#### Logging Service (§7.2.6.1)

- NVU logging is a **message-based debugging mechanism** where debug messages output by firmware can be used by developers or customers for debugging NVU FW.
- Debug messages are embedded into code by the firmware developer. (§7.2.6.1)

### Dictionary-Based Logging (§7.2.6.1.4)

- Dictionary-based logging outputs log messages in **binary format** rather than human-readable text, reducing output bandwidth and storage requirements.

### Log to Host (§7.2.6.1.6)

- The **log configuration client** in firmware receives log-related commands and processes them.
- The **TraceConfig tool** is used on the Host side to configure and collect logs.

### HECI Buffering for Log Transport (§7.2.3.16.1.2)

- The HECI transport layer supports buffering that allows firmware to practically never be waiting for flow control messages from the host.
- The maximum number of packets at the HECI layer is **up to 255** with the current implementation.
- This buffering implies practical limitations on the number of traces that can be logged within a given timeframe.

---

#### Profiling Service (§7.2.6.2)

- The **SMHI client** in firmware manages command handling and processing for requests initiated by the **NVU Profiling tool** on the host side.

### SMHI Commands

| Command Name | Description |
|---|---|
| `SMHI_GET_FW_VER` | Get firmware version |

---

#### Probe Service (§7.2.6.3)

The Probe service provides a protocol-based interface for host-initiated firmware inspection, configuration, and data capture.

### Probe Protocol — Message Header (§7.2.6.3.1)

#### `probe_msg_hdr_t` Fields

| Field | Type / Width | Description |
|---|---|---|
| `command` | `uint8_t:7` | Probe command ID (`probe_cmd_id_t`) |

---

### Probe Protocol — Message Structures (§7.2.6.3.1)

All probe request and response structures carry a common `probe_msg_hdr_t` header as their first field.

| Structure | Command | Field | Type | Description |
|---|---|---|---|---|
| `probe_init_req_t` | `PROBE_CMD_INIT` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_init_res_t` | `PROBE_CMD_INIT` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_query_req_t` | `PROBE_CMD_QUERY` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_query_res_t` | `PROBE_CMD_QUERY` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_enable_req_t` | `PROBE_CMD_ENABLE` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_enable_res_t` | `PROBE_CMD_ENABLE` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_disable_req_t` | `PROBE_CMD_DISABLE` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_disable_res_t` | `PROBE_CMD_DISABLE` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_config_req_t` | `PROBE_CMD_CONFIG` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_config_res_t` | `PROBE_CMD_CONFIG` | `header` | `probe_msg_hdr_t` | Common message header |
| `probe_data_res_t` | `PROBE_CMD_DATA` | `header` | `probe_msg_hdr_t` | Common header (used when response packet is present) |

---

#### Playback and Record (PNR) Service (§7.2.6.4)

- The **Playback and Record (PNR)** service is the implementation of the `PROBE_TYPE_PNR` probe subtype.
- It handles raw frame **ingress/egress** between the host and the frame capturing pipeline in firmware. (§7.2.6.4)

### PNR Service Interfaces (§7.2.6.4.1)

- **Start** requests for Playback or Record operations are always **Host-initiated**.
- **Stop** requests may be initiated by either the **Host** or the **FW**.

---

#### Telemetry Data and Exposure to OS (§16.2.5)

Telemetry data is organized into named fields grouped by usage category. Each field is mapped to a 64-bit Quadword (QW) slot and carries a defined type (Counter or Snapshot) and unit.

### Debug & Profiling (FW) Telemetry Fields

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| IPAPG Main Counter | Counter | RTC Tick | QW3 | Main PD in PG |
| IPAPG USB Counter | Counter | RTC Tick | QW4 | USB PD in PG |
| NPX Active Counter | Counter | RTC Tick | QW5 | NPX active; can be used to represent Max Power |
| Boot Latency Prior HLUP | Counter | RTC Tick | QW10 | — |
| Boot Latency Post HLUP | Counter | RTC Tick | QW10 | — |
| NN Execution Time Max | Counter | RTC Tick | QW11 | — |
| NN Execution Time Avg | Counter | RTC Tick | QW11 | — |
| SRAM Status | Snapshot | Count | QW19 | # of active/retention/shutdown banks |
| Algorithm FPS | Snapshot | Count | QW21 | Avg/Max/Min/Current |
| Reserved | — | — | QW21 | — |

### Data Leaking Threat Report Telemetry Fields

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Violation Counter | Snapshot | Count | QW3 | Number of violations detected from communication protocol validation checks |
| Violator_Top1 | Snapshot | App ID | QW3 | App ID with the highest number of violations |
| Violator_Top2 | Snapshot | App ID | QW4 | App ID with the 2nd-highest number of violations |
| Violator_Top3 | Snapshot | App ID | QW4 | App ID with the 3rd-highest number of violations |

### UX Study (FW) Telemetry Fields

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| Face Height Histogram Header | Snapshot | NA | QW5 | Face Height histogram |
| Face Height Histogram Bin0 | Snapshot | NA | QW5 | Face Height histogram |
| Face Height Histogram Bin1 | Snapshot | NA | QW6 | Face Height histogram |
| Face Height Histogram Bin2 | Snapshot | NA | QW6 | Face Height histogram |
| Face Height Histogram Bin3 | Snapshot | NA | QW7 | Face Height histogram |
| Face Height Histogram Bin4 | Snapshot | NA | QW7 | Face Height histogram |
| Face Height Histogram Bin5 | Snapshot | NA | QW8 | Face Height histogram |
| Face Height Histogram Bin6 | Snapshot | NA | QW8 | Face Height histogram |
| Face Height Histogram Bin7 | Snapshot | NA | QW9 | Face Height histogram |
| Face Yaw Histogram Header | Snapshot | NA | QW9 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin0 | Snapshot | NA | QW10 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin1 | Snapshot | NA | QW10 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin2 | Snapshot | NA | QW11 | Face Yaw orientation histogram |
| Face Yaw Histogram Bin3 | Snapshot | NA | QW11 | Face |


### Error Handling and RAS (11 facts)

#### Error Handling and RAS

---

#### Watchdog Timer (WDT)
(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.8 WDT | 12 RAS > 12.1 Errors)

- The NVU Watchdog Timer (WDT) is used to detect firmware hangs and assist in recovering normal operation.
- The WDT provides protection against firmware runaway conditions, forming a key element of the RAS error-detection strategy.

---

#### Crash Dump Management
(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.7 Crash Dump)

- In addition to generating immediate logs at the time of a fault, crash dumps must be stored for post-hoc analysis.
- Because the CSME storage service is not available for crash dump storage, the **AONRF (Always-On RF)** is used as the alternative persistent storage medium.
- Before transitioning from BUP to the Main FW, **BUP must clear all crash dumps stored in AONRF**.

---

#### HECI Flow Control Buffering
(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.16 HECI > 7.2.3.16.1.2 HECI buffering)

The following field is defined within the HECI Transport Protocol buffering message structure:

| Field | Size (Bytes) | Default | Description |
|---------|--------------|---------|------------------------------------------------|
| command | 1 | `0x08` | Flow Control (`HECI_BUS_MSG_FLOW_CONTROL`) |

---

#### WAMR Sandbox Security and App Isolation
(10 Chapter 6: NVU Security and Privacy > 10.2.2 FW Security Design Principles | 11 Chapter 7: WAMR Framework > 11.1.2 WAMR Sandbox Security Features)

- **Safety by default:** The WAMR framework enforces app safety by default through its built-in sandboxing mechanism.
- **App restart and context erasing:**
  - WAMR allows WASM apps to be built as separate firmware images and distributed independently.
  - WASM apps can be loaded and unloaded repeatedly by WAMR at runtime.
  - WAMR is capable of erasing application context between load cycles, ensuring isolation between app instances.
- **Periodic context reset:** The Intel Core App triggers a periodical restart and context erasing of all other apps running in the WAMR environment, limiting the blast radius of any compromised or runaway application.


### Firmware (61 facts)

#### Firmware

### Overview

#### NVU Firmware Architecture
(6 Chapter 2: NVU Firmware Overview > 6.1 NVU Firmware Architecture)

- The main firmware consists of several layers.

---

### Firmware Layout
(6 Chapter 2: NVU Firmware Overview > 6.2 NVU Firmware Layout)

- The basic partition layout separates the NVU image into a base firmware partition and an extension (APP) firmware partition.

#### Firmware Release Image Generation Flow

The basic firmware release image generation flow proceeds as follows:

1. Build source code to generate all the image submodules.
2. Use **ImageTool** to generate stitched NVU base FW and APP FW, excluding the "CPD + Manifest Header + Package Extension".
3. Use the **MMEU tool** to locally sign the NVU base FW and APP FW.
4. Use the **MMEU tool** to export the image manifest.
5. Submit the manifest to **LTCSS** for production signing.
6. Use the **MMEU tool** to import the production-signed manifest into the release FW image.

---

### NVU Image Structure
(6 Chapter 2: NVU Firmware Overview > 6.2 NVU Firmware Layout > 6.2.1 NVU Image Structure)

An NVU image is composed of the following structural elements:

- **Global Manifest** (128 bytes) — Contains global firmware information.
- **Module Manifests** (64 bytes each) — One manifest per module included in the image.
- **End Marker** — The 4-byte ASCII string `"NVUE"` indicating the end of the manifest section.
- **Module Binaries** — The actual firmware, application, or model data; each binary must be **128-byte aligned**. The tool automatically pads modules with zeros to achieve this alignment.

#### Base Image Layout

| Field | Size (bytes) | Description |
|---|---|---|
| Global Manifest | 128 | Global firmware information |
| VPX FW Manifest | 64 | VPX Module Manifest |
| NPX FW Manifest | 64 | NPX Module Manifest |
| WASM Core App Manifest | 64 | Core WASM Manifest |
| AON FW Manifest | 64 | AON FW Manifest |
| `"NVUE"` | 4 | End Marker |
| VPX FW Binary | VPX FW size | VPX FW binary |
| NPX FW Binary | NPX FW size | NPX FW binary |
| WASM Core App Binary | Core App size | Core App binary |
| AON FW Binary | AON FW size | AON FW binary |

> **Important:** Each module binary must be 128-byte aligned. The tool automatically pads modules with zeros to achieve this alignment.

---

### Global Manifest Structure (128 bytes)
(6 Chapter 2: NVU Firmware Overview > 6.2 NVU Firmware Layout > 6.2.2 Global Manifest Structure)

| Field | Offset | Size (bytes) | Description |
|---|---|---|---|
| `ext_id` | 0 | 4 | `"NVG0"` for Base FW; `"NVG1"` for Extension FW |
| `ext_len` | — | — | Length of the extension structure |
| `header_version` | 8 | 4 | Version of NVU Manifest |
| `nvu_version` | 16 | 8 | Build version of NVU FW |
| `aon_rf_base` | — | — | Base address of AON RF space |
| `aon_rf_limit` | 32 | 4 | Size of AON RF space (16 KB) |
| `iccm_base` | — | — | Base address of ICCM |
| `iccm_limit` | — | — | Limit of ICCM |
| `dccm_base` | — | — | Base address of DCCM |
| `dccm_limit` | — | — | Limit of DCCM |
| `fw_prj_ver` | 76 | 8 | FDK project version |
| `reserved` | — | — | Reserved |

- The AON RF space is **16 KB** in size.

---

### Module Manifest Structure (64 bytes)
(6 Chapter 2: NVU Firmware Overview > 6.2 NVU Firmware Layout > 6.2.3 Module Manifest Structure)

| Field | Offset | Size (bytes) | Description |
|---|---|---|---|
| `ext_id` | 0 | 4 | `"NVG0"` for Base FW, `"NVG1"` for Extension FW |
| `module_name` | — | 8 | Standardized module name (see conventions below) |
| `module_size` | — | — | Size of the module binary |
| `load_offset` | — | — | Offset of the module binary within the image |
| `load_size` | — | — | Size of the loadable region |
| `load_addr` | — | — | Target load address in memory |
| `property` | — | — | Module property flags |
| `variant` | — | — | Module variant identifier |

#### Module Name Conventions
(6 Chapter 2: NVU Firmware Overview > 6.2 NVU Firmware Layout > 6.2.3.1 Module Name Conventions)

The `module_name` field (8 bytes) uses standardized names based on the firmware type and module source.

##### Base Firmware Modules
(6.2.3.1.1 Base Firmware Modules)

| Module Name | Binary File | Purpose |
|---|---|---|
| `NPX_CORE` | `npx_core.bin` | NPX core firmware |
| `COREWASM` | `core_wasm_app.wasm` | Core WASM application |
| `AON_IMAG` | `aon_image.bin` | AON image |

##### Extension Firmware Modules
(6.2.3.1.2 Extension Firmware Modules)

| Module Name | Binary File(s) | Purpose |
|---|---|---|
| `WASM_APP` | `*.wasm` (from PDT) | WASM applications specified in PDT JSON |
| `PDT_DATA` | `nvu_pdt.bin` | PDT binary data |

---

### Boot and Security Design
(9 Chapter 5: NVU Firmware Loading > 9.1 Boot Design Requirements > 9.1.1 Boot Security Design Requirements)

- NVU FW consists of **Intel-signed FW** and **OEM-signed FW**.
- The firmware must **enable WAMR sandbox protection/isolation** before loading any third-party WASM application code.
- NVU will allow OEM-signed firmware components to run; if these components are malicious, they could leak image data to the host. (14 Security and Access Control > 14.9 Global Security Controls)

---

### WAMR Framework Integration
(11 Chapter 7: WAMR Framework > 11.3 WAMR Framework Overview > 11.3.1 WAMR Framework Functionality)

- The **WAMR App Manager** serves as the central orchestrator for all WASM application operations within the NVU firmware.

---

### HECI Transport — Firmware Address Field
(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.16 HECI > 7.2.3.16.1 HECI Transport Protocol)

| Bits | Field | Description |
|---|---|---|
| 7:0 | `fw_addr` | Firmware address |

**`fw_addr` Value Definitions:**

| Value | Definition |
|---|---|
| 0 | HECI bus communication |
| 1–31 | Fixed HECI client communication |
| ≥ 32 | Dynamic HECI client communication |

---

### API Reference

- For detailed API information on the MJPG Decoder & Post Processing peripheral, refer to the **NVU Firmware Zephyr API** document. (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.14 MJPG Decoder & Post Processing)


### GPIO and Pin Mux (11 facts)

#### GPIO Controller Overview
(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.1 GPIO)

The NVU supports a **single instance** of a General Purpose IO (GPIO) controller with the following characteristics:

- Supports up to **16 native GPIO pins**
- Each GPIO pin is individually configurable as **input** or **output**
  - If configured as **output**: the pin can be driven high or low
  - If configured as **input**: the pin can be configured to interrupt MIA on rising or falling edge detection

---

#### GPIO Pin Configuration for PHY Sharing
(8 Chapter 4: Camera and ISP > 8.1 MIPI CSI-2 Camera > 8.1.1 PHY Sharing)

- FW shall configure **GPIO[22]** and **GPIO[23]** for **dual edge detection**
- These pins are used for the *GPIO as Wake from IPU Requesting/Relinquishing PHY* function; refer to the NVU HAS for the corresponding hardware design

---

#### Virtual GPIO (vGPIO) Handshake — Camera Control Interface Sharing
(8 Chapter 4: Camera and ISP > 8.1 MIPI CSI-2 Camera > 8.1.2 Camera Control Interface Sharing)

The Host SW driver implements a **release_req / release_ack** handshake with NVU FW over vGPIOs to manage camera ownership transfers:

- **To take ownership**, the Host SW driver shall:
  1. Verify **VGPIOx1** is cleared
  2. Set **VGPIOx0**
  3. Wait for **VGPIOx1** assertion, indicating NVU has released ownership

---

#### MIPI Camera Sensor Control via GPIO
(8 Chapter 4: Camera and ISP > 8.1 MIPI CSI-2 Camera > 8.1.3 Camera Sensor Control > 8.1.3.3 MIPI Camera Control via GPIO)

Refer to *MIPI Camera GPIO Sharing with IPU* in the NVU HAS for the underlying hardware design. FW implementation notes:

- GPIO-related settings — including **community, group, pad, function, initial value, and active value** — are configured in **BIOS** and queried by the NVU SW driver during **OS boot**, alongside other camera configurations
- When NVU holds **camera sensor ownership**, NVU FW may drive the associated pins' Tx by programming the corresponding **pad register** in the SoC GPIO controller via **IOSF-SB**
- NVU FW shall **not** touch any other pad registers outside of its designated ownership scope

---

#### GPIO Wake Sources Across NVU Power States
(13 Chapter 9: NVU Power Management > 13.4 Power States)

The table below summarizes NVU power states and their associated GPIO-relevant wake source and power saving context:

| Power State | Description | Power Saving Options | Wake Sources |
|---|---|---|---|
| **D0i0** | NVU in DAQ or VPX/NPX execution from SRAM | Block-level CG; SRAM auto retention by HW | — |
| **D0i1** | NVU FW enters IDLE loop; Time to Next Event allows D0i1 entry | MAIN PD: Trunk CG; USB and MIPI PD: PG; SRAM auto retention by HW | GPIO (per NVU HAS) |
| **D0i2** | NVU FW enters IDLE loop; Time to Next Event allows D0i2 entry | MAIN PD: IPAPG; USB and MIPI PD: PG; SRAM in retention by FW; PGCB | GPIO (per NVU HAS) |


### IOSF Bridge (342 facts)

### IOSF Bridge

#### Overview

The IOSF to AXI Bridge provides several access mechanisms via the IOSF Sideband (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.12 SideBand).

---

#### Hammock Harbor Flow

#### Time-Synchronization Protocol (7.2.3.9.1)

The following describes the NVU FW and ARU interaction over the IOSF-SB interface for Hammock Harbor time synchronization:

- NVU FW initiates a **SyncStartCmd** command to ARU via IOSF SB EPHW on the IOSF-SB interface.
- NVU FW performs the `sb_resource_own_req` / `sb_resource_own_ack` **assert** protocol prior to issuing the GO command to IOSF SB EPHW.
- NVU FW **deasserts** `sb_resource_own_req` / `sb_resource_own_ack` after receiving the SyncStartCmd command-sent interrupt from IOSF SB EPHW.
- ARU captures the ART value (to be sent later on IOSF-SB) and simultaneously sends a pulse on the out-of-band **SyncCntr** line.
- ARU sends a non-posted IOSF-SB **LocalSync** packet to NVU containing the captured ART timer value (t1).
- NVU FW issues a **completion packet** on the IOSF SB interface via IOSF SB EPHW.
- ARU sends a **SyncComp** message with OK status on the IOSF-SB interface to complete the time-synchronization flow.

---

#### CSE IPC IOSF Sideband Message Registers

### Interrupt and Channel Control Registers

#### PISR_CSE2NVU — Peripheral Interrupt Status Register (CSE to NVU)

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| AGENT2NVU_DB | [0] | 0x0 | RO/V | AGENT2NVU Inbound Message Interrupt Status. Read by NVU FW only. `1` indicates the DOORBELL BUSY interrupt is active. |
| RESERVED1 | [26:1] | 0x0000000 | RO | Reserved. |
| AGENT2NVU_BCISC | [27] | 0x0 | RW/1C/V | AGENT2NVU Inbound message busy clear interrupt status clear interrupt. Written by NVU FW only to clear the interrupt status. |
| RESERVED0 | [31:28] | 0x0 | RO | Reserved. |

#### CIM_CSE — AGENT Channel Interrupt Mask

**Offset:** `0x000000001010` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> This register is for masking the per-channel interrupt.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_MASK | [0] | 0x0 | RW | Global interrupt enable towards FW for the channel. `0` indicates the interrupt is unmasked. |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved. |

#### CIS_CSE — AGENT Channel Interrupt Status

**Offset:** `0x000000001014` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> This register provides the per-channel interrupt status; set if an interrupt source is enabled and active.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| CH_INTR_STATUS | [0] | 0x0 | RO/V | Global interrupt status for FW interrupts on the channel. Set if any enabled interrupt source is active. |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved. |

---

### Firmware Status and Communication Registers

#### NVU_CSE_FWSTS_CSE — AGENT Firmware Status

**Offset:** `0x000000001034` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> Writeable by NVU, RO by AGENT.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| NVU_AGENT_FWSTS | [31:0] | 0x00000000 | RW | NVU AGENT firmware status. Written by FW and read by AGENT. |

#### NVU_CSE_COMM_CSE — AGENT Communication

**Offset:** `0x000000001038` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> Writeable by AGENT, RO by NVU. Set to `0x0` on reset.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| AGENT_COMM | [31:0] | 0x00000000 | RW | AGENT communication register. Written by AGENT and read by FW. |

---

### Reset Register

#### NVU_RST_CSE — AGENT NVU Reset

**Offset:** `0x000000001044` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> Though writeable by AGENT, this register is reserved for AGENT; AGENT should not write to it under normal operation.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| RESET_BIT | [0] | 0x0 | RW | NVU Reset Register. `1` = Reset active; `0` = Reset inactive. |
| RESERVED0 | [31:1] | 0x00000000 | RO | Reserved. |

---

### Doorbell Registers

#### CSE2NVU_DOORBELL_CSE — Inbound Doorbell (AGENT To NVU)

**Offset:** `0x000000001048` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> Inbound doorbell register from AGENT core to interrupt NVU.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility. |

#### NVU2CSE_DOORBELL_CSE — Outbound Doorbell (NVU To AGENT)

**Offset:** `0x000000001054` | **Size:** 32 bits | **Reset Signal:** FUNCRST

> Outbound doorbell register for NVU to interrupt AGENT.

| Field | Bits | Reset | Access | Description |
|---|---|---|---|---|
| PAYLOAD_31BIT | [30:0] | 0x00000000 | RW | 31-bit message payload for backward compatibility. |
| BUSY | [31] | 0x0 | RW | When cleared, the AGENT CPU is ready to accept a new message. |

---

### Inbound Inter-Processor Message Registers (AGENT To NVU)

All registers in this group carry a single 32-bit `MSG` field (`[31:0]`, Reset: unknown, Access: `RW`) containing the message from AGENT to NVU. Reset signal for all: **FUNCRST**.

| Register | Offset | Size |
|---|---|---|
| CSE2NVU_MSG0_CSE | `0x0000000010E0` | 32 bits |
| CSE2NVU_MSG1_CSE | `0x0000000010E4` | 32 bits |
| CSE2NVU_MSG2_CSE | `0x0000000010E8` | 32 bits |
| CSE2NVU_MSG3_CSE | `0x0000000010EC` | 32 bits |
| CSE2NVU_MSG4_CSE | `0x0000000010F0` | 32 bits |
| CSE2NVU_MSG5_CSE | `0x0000000010F4` | 32 bits |
| CSE2NVU_MSG6_CSE | `0x0000000010F8` | 32 bits |
| CSE2NVU_MSG7_CSE | `0x0000000010FC` | 32 bits |
| CSE2NVU_MSG8_CSE | `0x000000001100` | 32 bits |
| CSE2NVU_MSG9_CSE | `0x000000001104` | 32 bits |
| CSE2NVU_MSG10_CSE | `0x000000001108` | 32 bits |
| CSE2NVU_MSG11_CSE | `0x00000000110C` | 32 bits |
| CSE2NVU_MSG12_CSE | `0x000000001110` | 32 bits |
| CSE2NVU_MSG13_CSE | `0x000000001114` | 32 bits |
| CSE2NVU_MSG14_CSE | `0x000000001118` | 32 bits |
| CSE2NVU_MSG15_CSE | `0x00000000111C` | 32 bits |
| CSE2NVU_MSG16_CSE | `0x000000001120` | 32 bits |
| CSE2NVU_MSG17_CSE | `0x000000001124` | 32 bits |
| CSE2NVU_MSG18_CSE | `0x000000001128` | 32 bits |
| CSE2NVU_MSG19_CSE | `0x00000000112C` | 32 bits |
| CSE2NVU_MSG20_CSE | `0x000000001130` | 32 bits |
| CSE2NVU_MSG21_CSE | `0x000000001134` | 32 bits |
| CSE2NVU_MSG22_CSE | `0x000000001138` | 32 bits |
| CSE2NVU_MSG23_CSE | `0x00000000113C` | 32 bits |
| CSE2NVU_MSG24_CSE | `0x000000001140` | 32 bits |
| CSE2NVU_MSG25_CSE | `0x000000001144` | 32 bits |
| CSE2NVU_MSG26_CSE | `0x000000001148` | 32 bits |
| CSE2NVU_MSG27_CSE | `0x00000000114C` | 32 bits |
| CSE2NVU_MSG28_CSE | `0x000000001150` | 32 bits |
| CSE2NVU_MSG29_CSE | `0x000000001154` | 32 bits |


### IPC Messaging (127 facts)

#### IPC Messaging

### Overview (HAS §5.1, §7.2.3)

The NVU uses Inter Process Communication (IPC) interfaces for cross-subsystem interaction with external agents including the Host processor, Integrated Sensor Hub (ISH), and other embedded engines. The IPC peripheral is the primary transport mechanism for all inter-processor communication.

- Each IPC channel is independently secured with individual SAI-based policy to protect IPC register assets (HAS §7.2.3.11.1)
- The NVU IPC driver implements a subset of the Zephyr IPC driver API (HAS §7.2.3.11.1)
- Refer to the Embedded Engines IPC HAS for detailed interaction flow with each agent (HAS §7.2.3.11.1)

---

#### IPC Channel Security and Lifecycle (HAS §7.2.3.16)

- **Production firmware:** The IPC channel between NVU and the host is primarily used for downloading NVU main FW images from the host during the BUP (Bring-Up) stage. The channel is **disabled** before jumping from BUP to main firmware.
- **Pre-production / debug firmware** (before EOM, or on devices unlocked for debugging): The IPC channel remains enabled and may be used for transferring logs, probe data, and profiling data.

---

#### HECI Transport Protocol (HAS §7.2.3.16)

HECI (Host Embedded Controller Interface) is the transport layer protocol used by NVU, operating over IPC, for communication with the host processor.

##### IPC Message Header Structure

The IPC message header is a 32-bit register with the following field layout:

| Bits | Field | Size (bits) | Description |
|------|-------|-------------|-------------|
| 9:0 | `length` | 10 | Size of the message payload |
| 13:10 | `protocol` | 4 | Protocol identifier |
| 19:14 | `reserved` | 6 | Reserved |
| 23:20 | `length1` | 4 | Extended length field |
| 27:24 | `core_id` | 4 | Core identifier |
| 30:28 | `reserved` | 3 | Reserved |
| 31 | `busy` | 1 | Doorbell busy bit |

The overall message structure layers as follows:

```
[ IPC Message Header ][ HECI Message Header ][ HECI Message Payload ]
```

---

#### NVU–ISH IPC Communication Protocol (HAS §14.3)

The NVU-ISH communication protocol is based on IPC and is designed for **bidirectional, peer-to-peer** communication. It aligns with NVU-ISH communication requirements.

**Key capabilities:**
- Communication of raw data through IPC Doorbell (DB) and Data registers using the Standard Long Format IPC protocol (HAS §14.3.1, §14.3.2)
- Support for the IPC Reset Protocol via the CSR register (HAS §14.3.1, §14.3.2)

---

#### IPC Reset Protocol (HAS §14.3.2.1)

- **NVU** takes the **Leader** role; **ISH** takes the **Follower** role
- The IPC validity protocol is **not supported**; upon an IPC request/interrupt, the IP is expected to exit power-gating (if entered) and guarantee validity of IPC registers (doorbell and data registers)
- The CSR register is used to support the IPC Reset Protocol; bits 4–31 of the CSR register are **not used**
- Refer to the Embedded Engines IPC HAS for full details on the IPC Reset Protocol (guideline, high-level flow, and detail flow)

---

#### IPC Protocol — Standard Long Format Doorbell Header (HAS §14.3.2.2)

The IPC header is placed into the IPC Doorbell register. The doorbell structure follows the **Standard Long Format** as defined in the Embedded Engines IPC HAS.

##### IPC Doorbell Header — Field Definitions

| Bits | Field | Description |
|------|-------|-------------|
| 9:0 | `PAYLOAD_SIZE` | Number of bytes of payload provided in data registers. If size is not a multiple of dwords, data in the last register is placed in Little Endian format (LSB → MSB, i.e., bits 7:0 first). |
| 15:10 | `CLIENT_ID` | ID of the sending and receiving client. **Reserved as 0 for ISH-PeerIP IPC Protocol.** See CLIENT_ID value table below. |
| 18:16 | `BITS_18_16` | IP Pair specific. **Reserved as 0 for ISH-PeerIP IPC Protocol.** |
| 23:19 | `LONG_FORMAT_VER` | Long format version. In this specification version, value is `0x0` (default). |
| 25:24 | `RSVD_25_24` | Reserved. **Reserved as 0 for ISH-PeerIP IPC Protocol.** |
| 26 | `FLOW_CTRL_INFO_REQ` | Flow control request (when flow control is enabled): `0` = Do not send back a flow control message; `1` = Send back a flow control information message. |
| 27 | `SHORT_FORMAT` | Format selector. **Set as 0 for ISH-PeerIP IPC Protocol.** `0` = Standard Long Format; `1` = Standard Short Format. |
| 28 | `CUSTOM_FORMAT` | Custom format flag. **Set as 0 for ISH-PeerIP IPC Protocol.** `0` = Standard Format. |
| 30:29 | `BITS_30_29` | IP Pair specific. **Reserved as 0 for ISH-PeerIP IPC Protocol.** |
| 31 | `BUSY` | Doorbell busy bit. |

##### CLIENT_ID Value Definitions

| Value | Definition |
|-------|------------|
| 0x00–0x2F | Custom defined clients between IP pairs |
| 0x30 (48) | IPC driver |
| 0x31 (49) | MCTP |
| 0x32–0x3F | Reserved for future standard IPC clients |

---

#### Data Leaking Prevention — ISH IPC Service (HAS §11.6.2.1, §11.6.3)

- The IPC protocol between NVU FW and ISH FW is **privately defined by Intel** and not disclosed to third parties
- The protocol is used exclusively between Intel FW components (Intel Core app in NVU FW and corresponding ISH FW)
- In the event of a data leaking threat detection, WAMR will shut down the ISH-IPC service for 1–2 hours (HAS §11.6.3)


### Inference Engine (2 facts)

#### Memory Management — SMMU Page Table Constraints

(HAS §7 Chapter 3: RTOS and BSP › 7.1 RTOS › 7.1.1 Memory Management › 7.1.1.2 Memory Access)

- The SMMU (System Memory Management Unit) does **not** support on-demand paging by hardware design.
- To utilize VMEM, all memory mappings in the page tables **must** be managed by firmware in a predictable, pre-determined manner.
- Firmware is responsible for ensuring that page table entries are populated before access occurs, in order to avoid page faults at runtime.
- This constraint is an intentional design simplicity trade-off imposed at the hardware level and cannot be overridden by firmware policy.

---

#### NN Algorithm Profiling — Model Loading Latency

(HAS §16 Chapter 12: AON Vision FDK and Debug › 16.2 Always-ON Vision Firmware Debug › 16.2.6 NN Algorithm Profiling)

- The inference engine firmware exposes the following profiling metric for model loading:

| Metric | Description |
|---|---|
| **Latency — Average** | Average time to load a model from IMR to SRAM, including model hash verification |
| **Latency — Minimum** | Minimum observed time for the same model load and hash verification operation |
| **Latency — Maximum** | Maximum observed time for the same model load and hash verification operation |

- Model load latency measurement spans the full operation: **IMR → SRAM transfer** plus **hash verification**.
- These metrics are collected and reported as part of the AON Vision firmware debug and profiling infrastructure.


### Interrupt Configuration (12 facts)

#### Timer-Sourced Interrupts

##### Watchdog Timer (WDT) Interrupt

| Timer | Clock Source | Frequency | Interrupt |
|-------|-------------|-----------|-----------|
| WDT | Func Clock | 63.9 Hz | Yes — fires on reload timeout |
| Real Time Clock | RTC Clock | 32 KHz | None |

- The Watchdog Timer generates an interrupt if the NVU code fails to reload the timer within the specified amount of time. (§2.5.1.14, §7.2.3)
- The Real Time Clock (32 KHz) is available to NVU firmware for timestamping only; **no interrupt is associated with this counter**. (§2.5.1.14)
- HPET-style timers can each cause an interrupt at a specific number of clocks in the future (countdown style). (§2.5.1.14)

---

#### Peripheral Interrupt Sources

##### Hammock Harbor LocalSync Interrupt
- NVU SB EPHW receives the LocalSync packet from Hammock Harbor and **interrupts NVU FW** upon receipt. (§7.2.3.9.1)

##### MJPEG Decoder / Post-Processing Interrupt
- NVU firmware is responsible for handling the decoder and post-processing (PP) hardware interrupt. (§7.2.3.14)

---

#### Telemetry Service IRQ

- NVU HW provides a `telemetry_service` IRQ and associated status to NVU FW, operating in a manner analogous to the `vision_service` IRQ. (§16.2.5)

---

#### MSIF2IPI — USB Video Offload Interrupt Path

The MSIF2IPI sub-block (§8.8.2.1.2.8) is responsible for bridging incoming USB video data onto the IPI bus and driving the timing signals used by downstream interrupt logic:

- Receives incoming packets from the MSIF bus; packets are in **CSI format** (CSI headers only — UVC and CCPAL/U headers have already been stripped). (§8.8.2.1.2.8.2)
- CSI format consists of **short packets** and **long packets**:
  - **Short packets** carry synchronization (timing) information; MSIF2IPI parses these and drives timing synchronization signals on IPI. (§8.8.2.1.2.8.5)
  - **Long packets** contain a header and payload; MSIF2IPI parses and reformats them for IPI. (§8.8.2.1.2.8.5)
- Long packet headers contain additional descriptor information used during packet processing. (§8.8.2.1.2.8)


### Neural Network Accelerator (182 facts)

### Neural Network Accelerator

---

#### Overview

The Neural Network Accelerator (NNA) is a sub-component of the Intel NVU (Neural Vision Unit) hardware, supporting neural network model inference as part of the AON (Always-On) vision pipeline. The NVU firmware interacts with the NNA through dedicated firmware modules, memory regions, and runtime services described in this section.

---

#### Hardware Context

(HAS §5.1 NVU Hardware Overview)

- The NVU integrates a **Synopsys ARC VPX2 DSP Processor**, featuring:
  - A high-performance **32-bit scalar pipe**
  - A **128-bit vector unit**
- The ARC VPX2 core is used to drive neural network inference and vision processing workloads on-device.

---

#### Firmware Image Layout and NN Model Packaging

(HAS §6.2 NVU Firmware Layout, §6.2.3.1.2 Extension Firmware Modules)

- The **base image** contains:
  - One VPX firmware (FW)
  - One NPX firmware (FW)
  - One Core App
  - One AON image

- The **extension image** contains:
  - Multiple WASM applications
  - Several neural network models
  - A single PDT (Platform Data Table) binary

##### Extension Firmware Module: Neural Network Models

| Module Name | Binary Files | Purpose |
|---|---|---|
| `NN_MODEL` | `*.nnx` (from PDT) | Neural network models for apps with NN acceleration |

---

#### BSP Integration

(HAS §7.2 BSP)

- The **NVU BSP** integrates NVU IP with the **Zephyr RTOS**, providing:
  - Support for the NVU ARC VPX2 core
  - Enablement of NVU IP peripherals
  - Compatibility with both the NVU FPGA board and the NVU SoC reference board

##### DMA Capability Restrictions

(HAS §7.2.3.6.1 Capabilities)

- For security reasons, the **single-instance DMA controller** capability to transfer data from **SRAM to IMR/DDR** is **disabled in production FW**.
- Debug FW or EOM-disabled configurations may use DMA to transfer data from SRAM to IMR/DDR.

##### SPI Driver

(HAS §7.2.3.5 SPI)

- SPI is **not POR (Plan of Record) for FW**; the SPI driver will **not be enabled** in NVU production FW.

---

#### WAMR Framework and NN Inference Runtime

(HAS §11.1.1 WAMR)

- **WebAssembly Micro Runtime (WAMR)** serves as the lightweight runtime hosting WASM applications that interface with the neural network accelerator.
  - Lightweight, standalone WebAssembly runtime with small footprint
  - High performance and highly configurable features
  - Targets use cases from embedded to IoT

##### WAMR AOT Performance Measurements

(HAS §11.2.1 Risk in WAMR AOT Compiler and Mitigation Plan)

Performance was measured across multiple runs for face tracking applications:

| WASM App | AOT Mode | Interpretation Mode | Native Code |
|---|---|---|---|
| Face tracking app (algorithm running in app) | 29,570 ms | 94,490 ms | 22,840 ms |
| Face tracking app (algorithm offload to service) | 23,930 ms | 26,040 ms | 22,850 ms |

- AOT mode delivers near-native performance; interpretation mode incurs significant overhead.
- When the algorithm is offloaded to a service, the performance gap between AOT and interpretation mode narrows significantly.

---

#### WAMR Memory Management

(HAS §11.5 WAMR Memory Management, §11.5.1.1, §11.5.2)

- Each **WASM app (WASM module instance)** has its own **linear memory**: a vector of raw uninterpreted bytes referenced through unsigned 32-bit memory indices.

##### Memory Categories

| Category | Description |
|---|---|
| WASM module instance memory | Memory used for a WASM module instance; freed when the instance is destroyed. Includes linear memory (and host-managed heap) of the instance. |
| Execution environment memory | Memory used for execution of a WASM function from a module instance; provided by the host caller and released after execution completes. |

##### Shared Heap

- The **shared heap** is an advanced WAMR feature providing the same address mapping across multiple WASM instances.
- Enables flexible data sharing between:
  - Multiple WASM instances
  - WASM instances and host services
- Created via: `wasm_runtime_create_shared_heap(SharedHeapInitArgs *init_args)`
  - Based on `init_args`, a shared heap can be created in WAMR-managed mode.

---

#### App Tree and Execution Sequencing

(HAS §12.2.1 Core App High Level Design, §12.2.3 App Tree)

- The **App Tree** is a fixed data structure that determines the execution sequence of all apps within one frame.
  - Defines allowed input/output messages for each app
  - Is a subtree of the fixed app entity tree (maximum possible app tree from configuration)
  - Can dynamically change to a different subtree between frames

- The **App Guardian** sub-module handles app security and privacy management:
  - **Function 1 — App Lifetime Management:** manages app start, stop, and restart with local memory erase
  - **Function 2 — Shared Memory Management**

---

#### Algorithm App Lifecycle

(HAS §12.4.1 Algorithm App Lifecycle and Enable/Disable Control)

- **Instantiated & Enabled** state:
  - The active app entity tree is created
  - Corresponding WASM Apps are instantiated
  - App Management creates the WAMR module instance and execution environment

---

#### NN Model Inference Data Leaking Prevention

(HAS §11.6.2 WASM App Data Leaking Prevention, §11.6.2.2)

The following data fields are subject to leaking prevention controls for face detection output:

| Data Field | Type | Unit | Typical Range |
|---|---|---|---|
| `confidence_1st` | UINT8 | N/A | [0, 100] |
| `distance_1st` | INT16 | mm | [-1, 5000] |

##### Behavioral Rules for Data Leaking Prevention

- `capability/flag/mode/face_num/confidence` fields indicate which data fields are meaningful; all non-meaningful fields are **rewritten to 0** (e.g., if `face_num` is 1, all data from the 2nd face is zeroed).
- Distance output shall have **approximate mapping** with the 1st face's bounding box size.
- Distance shall **not jump back and forth** beyond a defined threshold.
- If the number of faces and distance or bounding box position/size does not change beyond a threshold, **the sample is not reported** to the upper layer.
- In multiple-face cases, primary/secondary user switching due to inaccurate bounding box size is mitigated using a **face tracking algorithm** with Kalman filtering:
  - Predicts new bounding box size, distance, and head orientation angle between frames
- **Noise addition** is applied to reduce the chance of data encoding into legal samples:
  - Adds a small random perturbation to face detection results (distance, bounding box, angle)
  - Example: distance changed from 1 m to 1.02 m
  - Noise addition must not change the fundamental nature of the sample

---

#### HECI Transport Protocol for NN/FW Communication

(HAS §7.2.3.16.1 HECI Transport Protocol)

##### HECI Message Header Fields

| Bits | Field | Description |
|---|---|---|
| 7:0 | `fw_addr` | Firmware address |
| 31:31 | `last_frg` | Last fragment flag — indicates whether the message being sent is the last in a sequence |

---

#### Firmware Boot Flow — NN-Relevant Tasks

(HAS §9.2.1.1 Extra ROM Tasks, §9.2.2.1 Extra BUP Tasks)

- **PMC save/restore** occurs during lid-close and lid-open flows:
  - During lid-close, VNN is removed; NVU HW configurations are saved before power removal
  - On lid-open, configurations are restored
- **LTR (Latency Tolerance Reporting) to PMC:**
  - ROM sets a **2 ms LTR** to PMC before DMA operations
  - ROM sets an **infinite LTR value** to PMC after DMA operations complete
- **DEBUG HOOK** support:
  - ROM leaves a specific value in the status register (HOST Remap register) at known execution points
  - Used to identify ROM hang locations during debug
- **`VPX_HALT_Fuse` check** is not required in ROM as a result of ROM Bypass PCR `15018614010`
  - The fuse is used by HW to determine VPX core halt behavior
- **Crash dump message transmission (BUP):**
  - If a FW exception occurs, the crash message is saved in AON
  - BUP sends the crash dump data to the host during the subsequent boot

---

#### Reference Documents

(HAS §4 Reference Documents)

| Document | Location |
|---|---|
| NVU Communication Protocol with ESE | Link |
| NVU OED + HECI Driver Design and Firmware Interface | Link |
| NVU Firmware Zephyr API | Link |
| ISH5.9 HAS | Link |
| ISH5.9 TTL FAS | Link |
| ISH5.9 SwAS | Link |
| TTL PCD-H Elemental Security Engine (ESE) Integration HAS | Link |
| AXIBIU Component HAS | Link |
| Third Party Vision Software Architecture Specification | Link |
| MCF Hardware Architecture Specification | Link |
| MCF Software Architecture Specification | Link |
| ECF Firmware Architecture Specification | Link |
| Web Assembly Micro Runtime Open Source Project | Link |
| Nova Lake Telemetry SAS | Link |
| NVL Imaging PAS | Link |
| USB3 Programming Guide | Link |
| ISYS eUSB2v2 path and CCPAL/U support | Link |


### NoC Fabric (14 facts)

#### NoC Fabric Overview

The NVU NoC (Network-on-Chip) fabric interconnects internal subsystems and exposes controlled interfaces for host access, inter-processor communication, and debug instrumentation. The sections below detail the key fabric components relevant to firmware.

---

#### IOSF to AXI Bridge (HAS 2.5.1.11)

| Interface | Description |
|---|---|
| AXI Initiator Interface | The IOSF Bridge uses the AXI Initiator interface to pass data between the IOSF Interface, enabling peer accesses to IPC and other status registers |

---

#### Inter-Processor Communication (IPC) (HAS 2.5.1.12, 7.2.3.11.1)

- Each IPC instance is assigned an **independent, non-overlapping 4 KB host MMIO space** mapped into the appropriate IPC OCP target within NVU.
- The IOSF-to-AXI Bridge facilitates host-side access to these IPC MMIO regions via the AXI Initiator interface.

---

#### Debug Trace Fabric (DTF) (HAS 2.5.1.20, 7.2.3.13)

##### Overview

- NVU hardware includes **DTF source packetizer and encoder blocks** to support firmware instrumentation trace output to **Intel Trace Hub (NorthPeak)**. (HAS 2.5.1.20, 7.2.3.13)
- NVU implements a **DTF-Source-Packetizer** — a register target that NVU firmware can access directly to push debug messages. (HAS 2.5.1.20.1)

##### Data Integrity and Ordering (HAS 2.5.1.20.1)

- FW debug messages from NVU are transferred to the trace aggregator in a **loss-less** fashion.
- FW debug messages are transferred **in-order from end to end** across the DTF fabric.

##### Key Features (HAS 7.2.3.13.1)

- Supports **SyS-T packet types**: `D64TS`, `D64(1..N)`, and `D64M`.
  - SyS-T protocol packets use a `D64-TS` packet as the header, followed by message payload encoded as `D64` packets, and terminated with a `D64M` packet.
- Supports **hardware-inserted timestamps**:
  - The timestamp value is derived from NVU's **local ART (Always Running Timer)**.
  - Enables time-synchronized debugging of NVU firmware alongside other SoC/PCH entities (e.g., CSE, ACE).
- **Zephyr RTOS** does not include native DTF driver support; NVU firmware defines custom **DTF driver APIs** to provide this functionality. Refer to the *NVU DTF Driver* specification for the full API definition. (HAS 7.2.3.13.1)


### PCI Configuration (1 facts)

#### Linear Memory Address Space

- The indexes of a linear memory array can be considered as memory addresses (HAS 11.5 WAMR Memory Management)
- The linear memory is considered a 32-bit abstract address space ranging from `0x00000000` to `0xFFFFFFFF` (HAS 11.5 WAMR Memory Management)


### PMC Integration and Wake (217 facts)

### PMC Integration and Wake

> **Note:** The facts provided do not contain direct content for the 'PMC Integration and Wake' sub-skill section. The available HAS facts cover adjacent topics including IPC communication channels (of which PMC is one peer), SideBand register access, and cross-core communication topology. The following documents all PMC-relevant content found in the provided fact set.

---

#### Cross-Core Communication Overview

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.11 Cross Core Communication)

The NVU firmware supports IPC-based communication with multiple peer agents. PMC is one of the defined IPC communication endpoints:

- NVU ↔ Host (NVU Driver)
- NVU ↔ ESE
- NVU ↔ ISH
- NVU ↔ PMC

---

#### SideBand Access for PMC and Peer Agents

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.12 SideBand)

- The SideBand interface provides access to a subset of registers within the IPC register range.
- This interface is specifically intended for use by peer agents including **CSME** and **PMC**.

---

#### Memory Access Context

(7 Chapter 3: RTOS and BSP > 7.1 RTOS > 7.1.1 Memory Management > 7.1.1.2 Memory Access)

| Access Path | Address Space | Translation Required | Notes |
|---|---|---|---|
| VMEM | Up to 16 MB | Yes — SMMU translates VMEM → PMEM via firmware-managed Page Table | Larger address space |
| PMEM | — | No | Direct physical access, no translation |

---

#### NN Offload Handshake (IPC-Based Core Readiness)

(12 Chapter 8: AON Vision App Development > 12.9 NN Offload Service > 12.9.2 Requirements and Flow)

- An IPC-based protocol is designed to perform **Cores Handshake**, ensuring peer cores (e.g., NPX) are ready before offload operations begin.
- This pattern is consistent with the broader NVU IPC communication model used with PMC and other peer agents.

---

#### Power Management and Resource Ownership

NVU is a **VNN powered**, **Chassis 2.2 compliant** IP. It supports the **Resource ownership** concept and the **resource_own_req/resource_own_ack** mechanism for resource ownership hand-off. Refer to the NVU HAS resources and PMC TTL for further details.

> **Documentation Gap:** Detailed PMC wake sequences, PMC IPC message formats, wake event registers, D-state transitions, and PMC handshake protocol specifics beyond the resource ownership mechanism should be sourced from the dedicated PMC Integration HAS chapter.


### Peripheral Interfaces (67 facts)

#### Peripheral Interfaces

### Overview

The NVU exposes a set of low-speed I/O peripheral interfaces including I2C, SPI, UART, I3C, and GPIO. These interfaces are accessed by the Zephyr kernel, services, and applications via the SEDI (Software-Enabled Device Interface) abstraction layer. (§5.1, §7.2.2)

All interfaces carry SAI (Source Attribute ID) protection; IPC, I2C, GPIO, ISP, and CSI are accessible only by VPX. (§14.3)

---

#### I2C

##### Controller Overview

NVU includes **3 independent I2C controllers** sharing the same general hardware capabilities. (§7.2.3.2)

##### Capabilities

- **Master Mode Only** — all connected peripherals must operate as slave devices (§7.2.3.2)
- Arbitration and clock synchronization supported (§7.2.3.2)
- BUS clear feature for graceful recovery when SDA or SCL lines are stuck LOW (§7.2.3.2)
- Interrupt or polling mode of operation (§7.2.3.2)
- SCL must be programmed for **50% duty cycle** (§8.17.7)
- HCNT must be incremented by **+1 for ALL operational speeds** (§8.17.7)
- `TX_EMPTY_CTRL` bit (`IC_CON[8]`) **must not be set** (§8.17.7)

##### Supported Operating Speeds

| Mode | Speed |
|---|---|
| Standard Mode | 100 kbps |
| Fast Mode | 400 kbps |
| Fast Mode Plus | 1000 kbps |
| High Speed Mode | 3400 kbps |

(§7.2.3.2)

##### Feature Enablement in Production FW

| Feature | Enabled in Production FW |
|---|---|
| DMA Mode | No |
| I2C Async Mode | No |

(§7.2.3.2)

##### I2C / LPSS Multiplexing

- NVU I2C0, I2C1 are multiplexed with LPSS I2C0, I2C1 respectively (§8.1.2)
- NVU FW controls the pad mode (PMode) of these pins between LPSS and NVU based on camera sensor ownership by programming the corresponding pad register in the SoC GPIO controller via IOSF-SB (§8.1.3.2)
- BIOS configures I2C/I3C pins to Grp4 with default pad mode set to LPSS/IPU (§5.1.1.1)
- I2C/I3C-related settings (bus, slave address, speed, function) are configured in BIOS and queried by the NVU SW driver during OS boot (§8.1.3.2)
- When a release request is received (from IPU via PHY Sharing or host software via vGPIO), NVU FW shall close and power off the camera sensor, release I2C/I3C ownership, and acknowledge as soon as possible (§8.1.2)
- If NVU FW hangs when `release_irq` is received, NVU BUP during exception reset shall check current I2C/I3C ownership and release it if still held by NVU (§8.1.2)

---

#### I3C

##### Controller Overview

NVU includes **2 instances** of I3C controller. The I3C controller is a **3rd-party IP from Synopsys**. (§7.2.3.3)

- Clock input (`ic_clk`) is **100 MHz** (§7.2.3.3)

##### Capabilities

- Separate command and data buffers for ease of transfers (§7.2.3.3)
- Supports various data rates: FM, FM+, SDR, DDR (§7.2.3.3)
- Hot-join support (§7.2.3.3)
- SETDASA CCC command supported (§7.2.3.3)
- ENTDAA CCC command **not supported** (§7.2.3.3)

##### Feature Enablement and Modes

| Feature | Supported | Comment |
|---|---|---|
| HDR-DDR Mode | Yes | — |
| HDR-TS Mode | No | — |
| I2C Mode | FM (400 kHz), FM+ (1 MHz) | `ic_clk` = 100 MHz |
| I3C Mode | FM, FM+, SDR (up to 10 Mbps), DDR | — |
| I2C/I3C Mixed Mode | 400 kHz | Mixed fast bus configuration not supported |

(§7.2.3.3)

##### Known Limitations

- **Mixed Fast Bus configuration is not supported** — the minimum SCL high period does not meet the I3C specification requirement (≤ 4 ns) (§7.2.3.3)
- When an I3C sensor operates in I3C mode and requires an interrupt to NVU (e.g., motion detection, data ready), **either IBI or GPIO** may be configured, but **not both simultaneously** (§7.2.3.3)
- NVU I3C0 is multiplexed with LPSS I3C0; pad mode is managed by NVU FW (§8.1.2)

##### Production FW Status

> **I3C is not POR (Plan of Record) for NVU FW.** The I3C driver will **not** be enabled in NVU production firmware. (§7.2.3.3)

---

#### UART

##### Controller Overview

The UART provides a **four-wire, bi-directional point-to-point** connection between the NVU and a peripheral. (§7.2.3.4)

##### Capabilities

- Operating speeds up to **6 Mbps** (§7.2.3.4)
- Strictly compliant **16550 mode** operation (§7.2.3.4)
- Parity modes: odd, even, none (§7.2.3.4)
- Stop bits: 1, 1.5, and 2 (as per standard) (§7.2.3.4)
- Hardware-based and software-based flow control (§7.2.3.4)
- Auto flow control using RTS#/CTS# signals (§7.2.3.4)

##### Debug Usage

- UART is supported as an optional logging backend for NVU firmware bring-up (§16.1.4)
- UART/I2C log debug mechanism availability by lifecycle phase:

| Phase | Availability |
|---|---|
| Pre-EOM & Debug Unlock | Supported |
| Pre-EOM & Debug Lock | Supported |
| Post-EOM & Debug Unlock | Supported |
| Post-EOM & Debug Lock | **Not Supported** |

(§16.2.2)

- If the SoC remains locked post-EOM, UART/I2C log and JTAG are unavailable (§16.2.4)

##### Production FW Status

> **UART is not POR for NVU FW.** The UART driver will **not** be enabled in NVU production firmware. (§7.2.3.4)

---

#### SPI

##### Controller Overview

SPI is a **four-wire, bi-directional serial bus** providing a simple and efficient method of data transmission over short distances between multiple devices. It is typically used for connecting the NVU to external peripherals. (§7.2.3.5)

---

#### GPIO

##### Overview

- Up to **8 GPIOs** can be allocated as ad-hoc functional output pins for sensor reset, power control, and similar purposes (§8.1.2)
- There is **no multiplexer** for GPIO between NVU and LPSS; these pins are dedicated (§8.1.2)
- BIOS places GPIO pins in the Host Group and locks down pad configuration (§5.1.1.1)
- IPC, I2C, GPIO, ISP, and CSI are accessible **only by VPX** within the NVU (§14.3)

##### Shared I2C/GPIO Wake Behavior

- When a sensor driver requests or relinquishes the shared I2C/GPIO, NVU FW is woken up and performs the necessary steps to place I2C/GPIO into a quiescent state (§8.21.5)
- NVU FW then programs a NVU GPIO connected to VGPIO to assert `release_ack` (§8.21.5)

---

#### Telemetry — I2C/I3C Access Counters

The following telemetry fields are exposed for debug and profiling. (§16.2.5)

| Field | Type | Unit | Telemetry QW |
|---|---|---|---|
| I2C/I3C Write Access Counter | Snapshot | Count | QW14 |
| I2C/I3C Write Amount | Snapshot | Byte | QW14 |
| I2C/I3C Read Access Counter | Snapshot | Count | QW15 |
| I2C/I3C Read Amount | Snapshot | Byte | QW15 |

Additionally, the NVU Profiling Tool tracks **I2C Transaction Count** as a BSP profiling metric per component. (§16.1.2)


### Power States (24 facts)

#### Power States

### Overview

NVU Power Management requires close coordination between the AON task, Boot ROM, PM driver, and peripheral drivers to achieve various low-power states and support transaction flows. (§13.5 Firmware Components and Roles)

---

#### PM Driver Role

(§13.5.3 PM Driver)

- The PM driver provides common APIs for other peripheral drivers, OSPM, and service/application layers to manage system and device clock and power.
- Managed flows include:
  - D0ix entry/exit
  - Sx entry/exit

---

#### D0ix Power States

##### D0i1 — Trunk Level Clock Gating

(§13.7.4 D0i1 - Trunk Level Clock Gating)

- D0i1 represents the NVU **Clock Gated** state.
- Entry and exit flows govern trunk-level clock gating for all NVU partitions, including ISP and USB.
- On **D0i1 exit**, the D0i1 Exit Flow is invoked to restore clock state. (§13.7.4.2 D0i1 Exit Flow)

##### D0i2 — Power Gated State

- D0i2 represents the NVU **Power Gated** (IPAPG) state.
- If NVU was in IPAPG state, exiting IPAPG will first call ROM for execution. NVU ROM will check if it is running from an IPAPG exit; if so, it will fetch the IPAPG PC return address and resume execution accordingly. (§9.2.1.1 Extra ROM tasks)
- BUP must check the `SLR_SLP_REQ` interrupt status at startup and transition to IPAPG if a lid-close event has occurred. (§9.2.2.1 Extra BUP tasks)

---

#### Telemetry — Power State Counters and Latency Metrics

(§16.2.5 Telemetry Data and Exposure to OS)

The following telemetry fields are exposed for firmware debug and profiling. All fields are of type **Counter** with unit **RTC Tick**.

##### Residency Counters

| Field | Type | Unit | QW | Description |
|---|---|---|---|---|
| D0i1 Counter | Counter | RTC Tick | QW2 | Time spent in NVU Clock Gated (D0i1) state |
| D0i2 Counter | Counter | RTC Tick | QW3 | Time spent in NVU Power Gated (D0i2) state |

##### Transition Latency Metrics

| Field | Type | Unit | QW | Description |
|---|---|---|---|---|
| D0i1 Enter Max Latency | Counter | RTC Tick | QW6 | Maximum latency observed entering D0i1 |
| D0i1 Enter Avg Latency | Counter | RTC Tick | QW6 | Average latency observed entering D0i1 |
| D0i1 Exit Max Latency | Counter | RTC Tick | QW7 | Maximum latency observed exiting D0i1 |
| D0i1 Exit Avg Latency | Counter | RTC Tick | QW7 | Average latency observed exiting D0i1 |
| D0i2 Enter Max Latency | Counter | RTC Tick | QW8 | Maximum latency observed entering D0i2 |
| D0i2 Enter Avg Latency | Counter | RTC Tick | QW8 | Average latency observed entering D0i2 |
| D0i2 Exit Max Latency | Counter | RTC Tick | QW9 | Maximum latency observed exiting D0i2 |
| D0i2 Exit Avg Latency | Counter | RTC Tick | QW9 | Average latency observed exiting D0i2 |

---

#### VNN Removal in Lid Close State

(§9.1.3 VNN Removal in Lid Close State Requirements)

- Due to aggressive platform-level power management design, NVU is **not expected to be operational** when the lid is closed and must be in its lowest power state.
- This behavior is distinct from the Modern Standby (S0ix) operating model.
- In the **Lid Closed State**, NVU must support **VNN removal**.
- When the lid is opened, NVU becomes operational and retains the VNN resource as requested.
- Boot design must accommodate and correctly handle the lid-close versus lid-open flow transitions.

##### VNN Removal Flow

(§9.2.4 VNN Removal Flow)

- NVU supports the VNN removal flow when the lid is closed, as defined by the HAS lid-close vs. lid-open design.
- Hardware-related flows are documented in the HAS lid-close vs. lid-open design specification.
- The VNN removal **lid-close → lid-open** flow is functionally identical to the standard **cold boot flow**, proceeding through ROM, BUP, and FW in sequence.

##### Boot and ROM Handling

(§9.2.1.1 Extra ROM tasks; §9.2.2.1 Extra BUP tasks)

- ROM must support power management during the lid-close/lid-open flow as part of its extra task responsibilities.
- BUP must handle necessary power management at startup by checking the `SLR_SLP_REQ` interrupt status:
  - If a lid-close event has occurred, BUP must initiate entry into the IPAPG (D0i2 Power Gated) state.


### Register Details (2 facts)

#### MJPG Decoder Control Register Initialization

**Decoding Startup Sequence**
*(HAS §7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.14 MJPG Decoder & Post Processing)*

- JPEG decoder software initiates decoding by parsing the incoming stream headers
- VLC (Variable Length Coding) tables and Quantization tables are written to memory prior to hardware engagement
- Hardware control registers are written following table initialization
- The hardware decoder is enabled as the final step in the startup sequence

---

#### Range Register Configuration and Access Control

*(HAS §14 Security and Access Control > 14.2 Security Objectives and Assets)*

**Authorized Configuration Agents**

| Agent | Authentication Method | Permission |
|---|---|---|
| NVU FW | Authenticated by ESE | Configure range registers |

- Only NVU firmware authenticated by the ESE (Embedded Security Engine) is permitted to configure the range registers
- No other agents are listed as authorized to perform range register configuration


### SRAM and Memory (87 facts)

#### SRAM and Memory

### Overview

The NVU includes an internal SRAM subsystem used for firmware storage, execution, and runtime data. Total usable SRAM space is **3.5 MB** as defined in the Global Manifest (`sram_limit` field, offset 48, size 4 bytes). (§6.2.2)

---

#### SRAM Memory Layout

(§7.1.1.1)

- **NPX FW** resides at the beginning of SRAM, encompassing text and data sections executed and accessed by the NPX core.
- **CV Shared Memory** is located after NPX FW in SRAM.
- All Intel and third-party WASM apps configured in PDT are loaded into SRAM by BUP prior to WAMR initialization, whether initially enabled or not. (§11.4.1)

---

#### SRAM Access Model

(§7.1.1.2)

- NVU FW uses **PMEM** for all SRAM access.
- The **SMMU** provides mapping and translation of virtual address space (IMR) to physical address space (SRAM); this mapping must be programmed by FW — no default mapping is performed by HW. (§2.5.1.7.3)

---

#### Global Manifest — SRAM Fields

(§6.2.2)

| Field | Offset | Size (bytes) | Description |
|---|---|---|---|
| `sram_base` | — | — | Base address of SRAM space |
| `sram_limit` | 48 | 4 | Size of SRAM space (3.5 MB) |

---

#### SRAM Controller / Slice Controller Capabilities

(§2.5.1.7.2)

- **FW Power Management Override:** FW can place any SRAM slice (all banks in a slice) into deep sleep or shut-down state.
- **ECC Scrub:** FW-initiated ECC scrub is supported for initializing SRAM modules.

---

#### SRAM Access Control Registers

(§CRIF: nvu_sec_reg_top_IOSF_SideBand_Msg)

The following registers control read and write access to SRAM regions via SAI (Source Address Identifier) bit-vector masks. All registers reset on `FUNCRST`.

##### Region 0 — Read Access Control

| Register | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| `NVU_SRAM_REGION0_RAC_LO` | 0x00009100 | 32 bits | FUNCRST | Read Access Control Policy (low 32 bits) |
| `NVU_SRAM_REGION0_RAC_HI` | 0x00009104 | 32 bits | FUNCRST | Read Access Control Policy (high 32 bits) |

**Fields:**

| Register | Field | Bits | Reset | Access | Description |
|---|---|---|---|---|---|
| `NVU_SRAM_REGION0_RAC_LO` | `SAI_MASK` | [31:0] | 0x01000000 | RW | Bit-vector of agents allowed read access, based on SAI value |
| `NVU_SRAM_REGION0_RAC_HI` | `SAI_MASK` | [31:0] | 0x00080C00 | RW | Bit-vector of agents allowed read access, based on SAI value |

##### Region 0 — Write Access Control

| Register | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| `NVU_SRAM_REGION0_WAC_LO` | 0x00009108 | 32 bits | FUNCRST | Write Access Control Policy (low 32 bits) |
| `NVU_SRAM_REGION0_WAC_HI` | 0x0000910C | 32 bits | FUNCRST | Write Access Control Policy (high 32 bits) |

**Fields:**

| Register | Field | Bits | Reset | Access | Description |
|---|---|---|---|---|---|
| `NVU_SRAM_REGION0_WAC_LO` | `SAI_MASK` | [31:0] | 0x01000000 | RW | Bit-vector of agents allowed write access, based on SAI value |
| `NVU_SRAM_REGION0_WAC_HI` | `SAI_MASK` | [31:0] | 0x00080C00 | RW | Bit-vector of agents allowed write access, based on SAI value |

##### Region 1 — Read Access Control

| Register | Offset | Size | Reset Signal | Description |
|---|---|---|---|---|
| `NVU_SRAM_REGION1_RAC_LO` | 0x00009120 | 32 bits | FUNCRST | Read Access Control Policy (low 32 bits) |

> **Note:** A requirement to open an NVU SRAM sub-region for ESE access (req. ID 15018281537) was evaluated and **rejected**. (§2.5)

---

#### SRAM Boot Initialization and Security

(§9.2.1, §9.2.1.1, §9.2.2)

- The **first action after ROM starts** is to trigger HW to perform **SRAM zeroization**.
- **SRAM scrub** is performed on every boot to ensure security: sensitive data (e.g., Face ID vectors) may persist in SRAM after reset, creating an asset leakage risk. Scrub mitigates this. (§9.2.1.1)
- ROM relies on ESE to load FW from IFWI into IMR and perform FW authentication checks.
- ROM requests ESE to share the HASH value of the BUP image and compares it independently, because IMR content is not inherently trusted.
- During BUP flow:
  - BUP reads the manifest and uses it to partition SRAM.
  - BUP copies the manifest into SRAM first.
  - A basic range check is applied before SRAM partitioning; partitions must not overlap with existing regions.
  - BUP copies all modules (except manifest, already copied) from IMR into SRAM.
  - Hash generation requires image to be in SRAM; BUP copies image from IMR to SRAM to enable SHA-accelerated hash verification.

---

#### IMR Integrity and SRAM Hash Storage

(§9.1.2)

- BIOS is responsible for IMR configuration but is **not within the NVU TCB**; a known attack vector allows adversaries (Startup Code / SMM Software) to inject code or data into IMR at any time before, during, or after verification.
- This can lead to full NVU FW compromise by bypassing verification.
- Mitigation: one **SHA384 HW accelerator engine** is added to support accelerated hash computation.
- **HASH values of IMR content are generated and stored in SRAM** during boot phases.
- After boot, Intel FW is responsible for runtime FW paging-in with **SHA-accelerated hash verification**. (§9.1.2)

---

#### SRAM Power Management

(§13.1, §2.5.1.7.2, §13.7.5)

- NVU HW provides the following SRAM power-saving capabilities:
  - **SRAM retention** (controlled by FW)
  - **SRAM run-time power management**
  - FW can place any SRAM slice into **deep sleep** or **shut-down**
- In the **D0i2** power state (trunk-level clock gating with IPAPG), SRAMs are placed in **retention**. FW must program the `CRPM_IPAPG_EN` register as part of D0i2 entry flow. (§13.7.5.1)
- FW-initiated **ECC scrub** is supported for SRAM module initialization. (§2.5.1.7.2)

---

#### SRAM Error Handling

(§RAS 12.1)

| Error Condition | Action |
|---|---|
| SRAM DED (Double-bit ECC Error) | FW Reset |

---

#### SRAM Debug and Telemetry

(§16.2.5)

| Field | Type | Unit | QW | Comment |
|---|---|---|---|---|
| SRAM Status | Snapshot | Count | QW19 | Number of active / retention / shutdown banks |
| IMR Read Access | Snapshot | Count | QW18 | — |
| IMR Write Access | Snapshot | Count | QW18 | — |

- Telemetry data are pushed to **PMC Shared SRAM** when permitted by PMC. (§16.2.5)
- NPX FW writes logs to a **pre-allocated shared buffer in SRAM**. (§7.2.6.1.7)

---

#### SRAM and Privacy-Sensitive Assets

(§10.1.3, §12.4.2)

- AON Vision HW/FW maintains **two highly privacy-sensitive security assets** in SRAM that require strict protection (e.g., Face ID vectors). (§10.1.3)
- At boot time, NVU Intel FW communicates with ESE to fetch previously stored Face ID vectors; upon NVU request, ESE reads out the stored vectors for decryption into local SRAM. (§12.4.2)
- During Face ID enrollment, the enrollment algorithm app generates new Face ID vectors in WAMR shared memory; after local SRAM is updated, vectors are encrypted for storage. (§12.4.2)
- Zephyr **user mode / kernel mode** partitioning is used with MPU protection to restrict access to SRAM regions containing sensitive assets; WAMR and all WASM apps run in user mode. (§10.2.2)

---

#### VNN Removal and SRAM State

(§9.2.4)

- The VNN removal flow appears to FW as an **IP reset**.
- When the lid is closed, **all SRAM content is lost**.
- After lid-open, FW reboots from ROM; the full boot sequence (including SRAM zeroization) is re-executed.
- For software, the NVU PCI device is reset and the driver is reloaded and re-enumerated.

---

#### Dynamic Load — SRAM and IMR Interaction

(§7.1.1.4)

- Multiple NN models (e.g., Model 1/2/3, managed by WASM App 1/2/3) are initially loaded into **NVU IMR**.
- Models are paged into **SRAM** on demand during sequential execution.
- Runtime paging-in includes **SHA-accelerated hash verification** to maintain integrity. (§9.1.2)


### Secure Boot (77 facts)

#### Secure Boot

#### Overview (Ch. 5 §9.1.1, Ch. 6 §10.2.2)

According to the NVU Security Architecture Specification, NVU firmware loading design enforces the following security requirements to ensure Intel and OEM firmware integrity:

- Support secure boot flow by ESE with SVN check and signature verification (§9.1.1)
- During boot, configure NPX memory access to NN models and WAMR shared memory (§9.1.1)
- Leverage ESE for secure boot, SVN check, secure debug unlock, Face ID enrollment data storage, and encryption/decryption (§10.2.2)

---

#### Image Authentication Algorithm (Ch. 2 §6.2)

- The image authentication algorithm uses an **RSA3K + LMS** hybrid signature scheme
- For hybrid signature scheme details, refer to the *Intel Cryptography Standards — Intel Crypto Resources* documentation (§6.2)

---

#### Boot Flow — BUP Phase (Ch. 5 §9.2.2)

- The image manifest is used by BUP **before** hash comparison during the NVU boot flow (§9.2.2)
- NVU calculates the HASH of the copied image; the hash value includes the **manifest and all modules** (§9.2.2)
- Hash of each NN model (`hash_model`) is compared against `hash_fw[x]`, where `x` is the ID of the model (§9.2.3)

---

#### Firmware Signing and Asset Decryption Policies (Ch. 12 §16.2.3)

The key used for firmware signing and asset encryption is managed and switched by **ESE**, not by NVU. NVU adopts the SoC debug design policies. The applicable keys per lifecycle state are defined in the table below.

| Firmware Signing / Asset Encryption | Pre-EOM & Debug Unlock | Pre-EOM & Debug Lock | Post-EOM & Debug Unlock | Post-EOM & Debug Lock |
|---|---|---|---|---|
| BUP Signature | Debug Key | Production Key | Debug Key | Production Key |
| Base FW Signature | Debug Key | Production Key | Debug Key | Production Key |
| App FW Signature | Debug Key | Production Key | Debug Key | Production Key |
| Face ID Vector Encryption | Debug Key | Production Key | Debug Key | Production Key |

> **Note:** The actual key is managed/switched by ESE, not by NVU. NVU only adopts and follows SoC debug designs, which results in the policy behaviors shown above. (§16.2.3)

---

#### ROM Code Bypass (§2.5)

- Requirement tracked: **id: 15018614010** | Owner: rchaddha | Title: `[TTL][NVU] NVU ROM code Bypass as survivability feature` | Status: POR (§2.5)

---

#### Memory Access Control at Boot (Ch. 5 §9.2.3, Ch. 7 §11.2)

- During boot, NPX memory access to NN models and WAMR shared memory is explicitly configured (§9.1.1)
- WAMR app memory and shared memory are pre-allocated by Zephyr during the **kernel initialization phase** for user mode; further partitioning is performed by WAMR during its own initialization (§9.2.3)
- All WASM apps are only permitted to access their **own memory** plus **WAMR shared memory**; access to other memory regions is disallowed (§11.2)
- WAMR manages WAMR shared memory for all non-system-privilege apps (§10.2.2)

---

#### WAMR AOT Compiler Security (Ch. 7 §11.2.1)

- To mitigate AOT compiler risk, a dedicated server is established for ISVs to perform AOT compilation with an **Intel signature** (§11.2.1)
- The server provides a ticket-system front end; ISVs submit AOT compile requests **without needing to submit source code** (§11.2.1)

---

#### Data Leakage Prevention (Ch. 7 §11.6.2)

- The Intel Core App **zeros out** the corresponding WAMR shared memory region (image buffer and its derivatives from the last frame) periodically to prevent data leakage (§11.6.2.1)
- Output sanity constraints enforced to prevent indirect data leakage (§11.6.2.2):
  - Bounding box width and height shall not be smaller than **15×15**
  - The 1st detected face shall have the largest bounding box; subsequent faces are ordered by decreasing size
  - `face_id` for the same face shall not change across frames
  - Bounding box location and size shall not jump back and forth beyond a defined threshold


### Sideband Messages (2 facts)

#### Sideband Messages

##### Generic Handshake Port

(7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral > 7.2.3.12 SideBand)

- All posted Sideband (SB) messages not handled by dedicated ports are transmitted over a **generic handshake port**.
- The generic handshake port follows the **avail/get protocol** for message exchange.
- The following opcodes are supported on the generic downstream port:
  - **VirtualWire**

##### Supported Root Spaces

(14 Security and Access Control > 14.2 Security Objectives and Assets)

- The following Root Space (RS) is supported for Sideband access:

| Root Space | Identifier | Interface  |
|------------|------------|------------|
| ESE RS     | RS2        | Sideband   |


### Straps, Fuses, and Security (17 facts)

#### Straps, Fuses, and Security

### SAI (Security Attribute of Initiator) Assignment

(14 Security and Access Control > 14.2 Security Objectives and Assets)

- All interfaces within NVU have SAI protection for I/O isolation: IPC, I2C, GPIO, ISP, and CSI are only accessible by VPX; NPX is only accessible by VPX.
- Security parameters define allowed SAIs per register (e.g., `DFX_INTEL_MANUFACTURING_SAI` for IPC register access) under control policies such as `NVU_CONTROL_POLICY`.

### Security Access Policy Parameters

(14 Security and Access Control > 14.6 Security Parameters)

All security parameters below are of type `uint32`, have a valid range of `0x0`–`0xFFFFFFFFFFFFFFFF`, and are SoC modifiable (SoC Modifiable = yes). The control policy (CP) group and allowed SAIs define which initiators may read or write each policy register.

#### Control Policy Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_CONTROL_POLICY_WRITE_DEFAULT_VALUE` | `0x0000040001210000` | `NVU_CONTROL_POLICY` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) Control Policy Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_CTRL_POLICY_WRITE_DEFAULT` | `0x0000040001210000` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) Fuse Access Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_FUSE_WRITE_DEFAULT` | `0x0000040001210000` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |
| `NVU_BR_FUSE_READ_DEFAULT` | `0x0000040001210000` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) High-Privacy SAI Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_HIGH_PVT_SAI_WRITE_DEFAULT` | `0x00000C000121001E` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |
| `NVU_BR_HIGH_PVT_SAI_READ_DEFAULT` | `0x00000C000121001E` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) Low-Privacy SAI Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_LOW_PVT_SAI_WRITE_DEFAULT` | `0x00000C000121001E` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |
| `NVU_BR_LOW_PVT_SAI_READ_DEFAULT` | `0x00000C000121001E` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) Root Space 0 (RS0) Configuration SAI Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_RS0_CFG_SAI_WRITE_DEFAULT` | `0x00000E000121001F` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |
| `NVU_BR_RS0_CFG_SAI_READ_DEFAULT` | `0x00000E000121001F` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |

#### Boot ROM (BR) Root Space 1 (RS1) Configuration SAI Registers

| Name | Default Value | CP Group | Allowed SAI (partial) |
|------|--------------|----------|-----------------------|
| `NVU_BR_RS1_CFG_SAI_WRITE_DEFAULT` | `0x00000C0001210000` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |
| `NVU_BR_RS1_CFG_SAI_READ_DEFAULT` | `0x00000C0001210000` | `CTRL_POLICY_REGS_GP` | `DFX_INTEL_MANUFACTURING_SAI` |


### Telemetry and Profiling (5 facts)

#### Hammock Harbor Timer Synchronization

**(HAS Ref: Chapter 3 § 7.2.3.9.1 Hammock Harbor Flow)**

- NVU hardware ensures that all three timers (LOCAL ART, AON, and RTC) are running and remain synchronized with the system ART (Always-Running Timer).
- The AON and RTC counters are incremented by the ratio of their respective clock frequencies relative to the XTAL clock frequency.

#### Hammock Harbor Delay Counter

**(HAS Ref: Chapter 3 § 7.2.3.9.1 Hammock Harbor Flow)**

- A delay counter is started with every `SyncCntr` pulse received from the ARU (Audio Reference Unit).
- The delay counter operates in the **XTAL clock domain**.
- The counter will **saturate at its maximum value** upon overflow and will set a status bit to indicate that saturation has occurred.

#### LOCAL ART Timer Update Mechanism

**(HAS Ref: Chapter 3 § 7.2.3.9.1 Hammock Harbor Flow)**

- Firmware writes the ART timer value received in the SB (Sideband) packet to the **LOCAL ART TIMER** register.
- Hammock Harbor hardware logic automatically adds the delay counter value to the firmware-written update value before loading it into the LOCAL ART TIMER.
- The LOCAL ART TIMER also operates in the **XTAL clock domain**.

#### WAMR Framework Profiling

**(HAS Ref: Chapter 7 § 11.3.7 Profiling)**

- Application management must gather statistics on message processing times, including:
  - Time spent in message queues
  - Dispatch times
  - Processing durations
- These statistics are essential for pinpointing performance bottlenecks within WebAssembly applications running on the WAMR framework.
- The profiling approach is designed to be flexible, ensuring that developers have timely access to the diagnostic information needed to refine and optimize their applications effectively.


### Timers (9 facts)

#### Timers

#### Overview (7 Chapter 3: RTOS and BSP > 7.2 BSP > 7.2.3 Peripheral)

The NVU firmware peripheral layer includes a **Timer** peripheral as part of the BSP implementation.

---

#### Hammock Harbor (HH) Timer Support (7.2.3.9)

The NVU implements Hammock Harbor (HH) support as a **Type-D HH agent**. This agent type is characterized by the following properties:

- Implements a **local always-running timer**
- Initiates requests for the current **ART (Always Running Timer)** value from the ARU (Always Running Unit)

##### Local ART Timer Implementations (7.2.3.9.1)

NVU HW implements three variants of the Local ART timer, differentiated by their clock source:

| Timer Type | Clock Source | Frequency |
|---|---|---|
| XTAL-based ART Timer | XTAL clock | — |
| AON-based ART Timer | AON clock | 2.56 MHz |
| RTC-based ART Timer | RTC clock | 32 KHz |

---

#### Hammock Harbor Flow (7.2.3.9.1)

The following describes the NVU firmware and hardware behavior during the Hammock Harbor synchronization flow:

**ART Timer Capture — Arming and Capture:**
- NVU FW arms the **ART Timer Capture Logic** to snapshot the local free-running timer value upon every pulse event on the **SyncCntr** signal from the ARU.
- Upon reception of the `SyncStartCmd` command from NVU, the ARU enqueues a request to provide the ART value. If the ARU is currently serving another HH agent, the `SyncStartCmd` command is enqueued and processed subsequently.
- This ARU queuing behavior may cause the NVU ART Timer Capture Logic to observe **multiple SyncCntr pulses**. The logic is expected to capture the local free-running timer value on **every** SyncCntr pulse received.

**ART Value Reception and Storage:**
- NVU FW parses the received ART packet and stores the ART timer value in **FW-managed memory**.

**ART Timer Capture — Disarming and Update:**
- NVU FW disarms the **ART Timer Capture Logic** after the ART value has been received.
- NVU FW initiates the **Local ART timer update** using the captured and stored ART value.

