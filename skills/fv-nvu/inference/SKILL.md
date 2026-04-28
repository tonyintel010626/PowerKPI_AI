name: fv-nvu/inference
description: NVU inference engine architecture, model loading, tensor operations, and execution flows

> **Domain Lead**: Lee, Bee Koon (`blee9`) — bee.koon.lee@intel.com
> **Maintainers**: Chin, William Willy (`willychi`), Leem, Yi Jie (`yleem`)
> **Team/Org**: Client Validation Engineering (CVE)
> **Support**: For any issues, contact the domain lead or maintainers above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# NVU Inference Engine

> **SAFETY**: Do NOT trigger inference operations or modify model memory without explicit user confirmation.
> Architecture details below are populated from the NVU HAS v1.0 (SIP_NVU_HAS.html) and NVU FAS v1.0 (Firmware Architecture Specification).
> HAS-sourced content is cited as `(HAS Section X.Y)`. FAS-sourced content is cited as `(FAS §X, LNNNN)` with line numbers.
> Any detail marked `TBD` has not been verified or is not present in the current document revision.

## Overview

The NVU (Neural Vision Sensing Unit) provides always-on visual sensing functionality for MIPI and USB cameras. It executes neural network models for low-power usages such as Wake-on-Face (WoF), FaceID, static hand gestures, head-orientation, onlooker detection, and 3D gestures. The NVU contains **two compute engines** that work cooperatively:

- **NPX6-1K NNA** (Synopsys ARC NPX6-1K Neural Network Accelerator) — the primary neural inference engine with 1024 MACs, optimized for CNN, RNN, Transformer, and other deep learning models
- **VPX2 DSP** (Synopsys ARC VPX2 DSP) — a high-performance VLIW/SIMD DSP for scalar/vector processing, pre/post-processing, CV algorithms, and orchestrating NPX6 execution
- **ARCSYNC** — inter-processor communication module synchronizing VPX2 and NPX6-1K via interrupts, semaphores, and run/halt control

Key capabilities:
- Inference engine architecture and dual-engine execution model (NPX6-1K + VPX2)
- Model loading via firmware-managed DMA and SRAM subsystem with SMMU paging
- Tensor format and data type support (INT8 convolution, INT8/16/32 tensor ops)
- Inference execution flows (VPX2 orchestrates NPX6 submit, monitor, complete)
- Error handling and recovery (watchdog, ECC, NPX exception reset)
- Performance monitoring (VPX2 performance counters, NPX L1 controller)


## Inference Engine Architecture

The NVU uses a dual-engine architecture where the **VPX2 DSP** acts as the supervisory processor and the **NPX6-1K NNA** is the dedicated neural inference accelerator. VPX2 firmware orchestrates all operations: camera data pre-processing, NPX6 task dispatch, and post-processing of inference results.

### NPX6-1K Neural Network Accelerator

The ARC NPX6-1K is a single-slice NPU with 1024 MACs per clock, designed for deep learning inference including CNN, RNN/LSTM, and Transformer models. Each NPX slice contains:

- **L1 Controller**: ARC HS3x-based controller managing accelerator tasks and data flow between L1 memories
- **Convolution Accelerator**: Supports basic convolution, depth-wise convolution, and input/output channel group convolution with varying stride/dilation, plus matrix-matrix multiplication. Capable of INT8 1024 MAC operations per clock. Tuned for modern networks (EfficientNet, MobileNet, DeepLabv3).
- **Tensor Accelerator**: Optimized for CNN, RNN, and Transformer networks. Supports the "baseline inference" profile of Tensor Operations with activation functions including ReLU variants (ReLU, Leaky ReLU, PReLU, ReLU1, ReLU6), approximation functions (tanh, sigmoid, swish, mish, gelu, exp, 1/x, 1/sqrt(x)), and element-wise operations (add, maxout, multiplication).
- **L1 Streaming Transfer Unit (STU)**: iDMA/oDMA accelerators for data transfers between L1 memories and external memory. Supports flexible 2D/3D transfers with unaligned and circular access, VM planar-mode, VM compress, and VM initialize modes.
- **L1 Memories**:
  - Vector Memory (VM): stores activation/weight values across 32 vector banks
  - Accumulator Memory (AM): stores accumulator values across 2 vector banks
  - L1 Memory total: 32KB AM + 128KB VM per slice

#### NPX6 Internal Bus Architecture (Source: HAS SVG `NPX6_arch`)

The NPX6 slice internal data movement uses 5 dedicated buses:

| Bus | Width | Function |
|-----|-------|----------|
| **VM Bus** | 128-bit | Vector Memory read/write — connects oDMA/iDMA, Conv, and L1 ARC to VM banks |
| **AM Bus** | 128-bit | Accumulator Memory read/write — Conv output accumulation, tensor accelerator access |
| **DM Bus** | 64-bit | Data Memory — L1 ARC scalar data access to local scratchpad |
| **CTRL Bus** | 32-bit | Control register access — L1 ARC programs Conv/oDMA/iDMA/GTOA configurations |
| **Data Bus** | 128-bit | External AXI data path — connects to NOC fabric via AXI-M/AXI-S interfaces |

**Key NPX6 sub-blocks** (from SVG):
- **oDMA** (Output DMA): Transfers results from L1 VM/AM to external SRAM via AXI-M. Supports 2D/3D descriptor-based transfers.
- **iDMA** (Input DMA): Transfers input data from external SRAM to L1 VM. Supports flexible addressing with circular/unaligned access.
- **GTOA** (Global Tensor Operations Accelerator): Performs element-wise tensor operations (activation functions, add, multiply) on data in VM/AM without going through Conv.
- **Conv** (Convolution Engine): 1024 INT8 MACs/clock. Reads weights/activations from VM, writes accumulation results to AM. Supports grouped convolution, depthwise, and matrix-matrix multiply.
- **L1 ARC** (HS3x Controller): Contains **CBU** (Code Bus Unit), **LBU** (Load Bus Unit for DM access), **DMI** (Debug Memory Interface — external debug access to NPX internals). Manages task scheduling and data flow coordination.
- **FIFO**: Bridges between Conv output and AM write port for accumulation pipeline
- **AXI-M / AXI-S**: AXI Master (initiator) and AXI Slave (target) interfaces to NOC fabric

### VPX2 DSP Processor

The ARC VPX2 is a high-performance VLIW/SIMD DSP processor integrating a 32-bit scalar pipe and 128-bit vector processing unit with vector floating point units. It serves as the supervisory CPU for the NVU, running firmware that:

- Pre-processes camera frames (down-sampling, format conversion)
- Dispatches inference tasks to NPX6-1K via ARCSYNC
- Runs CV/vision algorithms that don't require the NNA
- Post-processes NPX6 inference outputs
- Manages power states, IPC with host/PMC/CSME, and sensor control

Key VPX2 features:
- Quad-issue super vector architecture (1 scalar + 3 vector instructions per 128-bit bundle)
- 128-bit wide Vector DSP unit with MAC performance: 4 MACs/clock (32x32), 8 MACs/clock (16x16), 16 MACs/clock (8x8)
- 128KB Vector CCM (VCCM)
- Streaming Transfer Unit (STU) / 2DDMA for VCCM ↔ external memory DMA
- 32KB I-cache, 32KB D-cache
- MMU with TLB (up to 1024 normal-page entries) + 16 super-page entries
- 16 MPU regions
- 96 maskable external interrupts, up to 16 priority levels
- Single/double-precision floating point unit
- Performance monitor with 16 counters

#### VPX2 Execution Unit Microarchitecture (Source: HAS SVG `VPX2_arch`)

The VPX2 VLIW pipeline contains these execution units:

| Unit | Function |
|------|----------|
| **ScalarUnit** | 32-bit ALU, branch, load/store, CSR access |
| **ScalarFPU** | Single/double-precision IEEE-754 floating-point (FADD, FMUL, FDIV, FSQRT, FCVT) |
| **MPY** | Dedicated scalar multiply unit (32×32→64-bit result) |
| **VALU1** | Vector ALU #1 — 128-bit SIMD integer arithmetic, shifts, logical, permute |
| **VALU2** | Vector ALU #2 — 128-bit SIMD integer arithmetic (parallel with VALU1) |
| **VALU3** | Vector ALU #3 — 128-bit SIMD (additional execution slot for 3-wide vector issue) |
| **VFPUA** | Vector FPU A — 128-bit vector floating-point add/sub/compare |
| **VFPUB** | Vector FPU B — 128-bit vector floating-point multiply/FMA |
| **VFFC** | Vector FP Format Converter — float↔int conversion, pack/unpack |
| **Vector LD/ST** | 128-bit vector load/store with **gather/scatter** support for non-contiguous access patterns |
| **2DDMA** | 2D DMA engine for VCCM ↔ external memory block transfers (stride, 2D rectangular regions) |

**VPX2 HOR (Halt/Run) State Machine** (Source: HAS SVG `VPX2_HOR`):


                    arc_halt_req_a
    ┌──────────┐  ────────────────►  ┌──────────┐
    │ In Reset │                     │  Halted  │
    └──────┬───┘  ◄────────────────  └────┬─────┘
           │        (reset asserted)       │
           │                               │ arc_run_req_a
           │                               ▼
           │                         ┌──────────┐
           └────────────────────────►│ Running  │
                 (reset deasserted   └──────────┘
                  + run_req```
- **In Reset**: VPX2 core held in reset (`nvu_pgcb_rst_b` asserted). All state lost.
- **Halted**: Reset deasserted but VPX2 not executing. PC frozen. CRPM or ARCSYNC can halt.
- **Running**: VPX2 actively executing instructions. `arc_run_req_a` asserted by CRPM via ARCSYNC.
- CRPM asserts `arc_run_req_a` after reset deassert to boot VPX2 from ROM entry point.

### ARCSYNC (Cross-Core Synchronization)

ARCSYNC provides inter-core communication between VPX2 and NPX6-1K:

- **Interrupt dispatch**: Level-sensitive interrupts between cores (VPX2 IRQ 107/108 from ARCSYNC)
- **Run/halt/reset control**: VPX2 firmware controls NPX6 lifecycle via ARCSYNC registers (CORE_RUN_C1, CORE_HALT_C1, CORE_RESET_C1, CORE_CLK_EN_C1)
- **Run control signals (arc_halt / arc_run)**: ARCSYNC coordinates VPX2 and NPX6 via dedicated run control handshake signals between Debug Run Control and ARCSYNC:
  - VPX2 → ARCSYNC: `arc_halt_req_a` (halt request), `arc_halt_ack` (halt acknowledge), `arc_run_req_a` (run request), `arc_run_ack` (run acknowledge)
  - **NPX6 external halt/run**: Tied off — `sl0nl1arc_ext_arc_halt_req_a` tied to 0, `sl0nl1arc_ext_arc_run_req_a` tied to 0; ack outputs (`sl0nl1arc_ext_arc_halt_ack`, `sl0nl1arc_ext_arc_run_ack`) left open
  - **VPX2 external halt/run**: Connected to CRPM — `v0c0ext_arc_halt_req_a` (in, from CRPM), `v0c0ext_arc_halt_ack` (out, to CRPM), `v0c0ext_arc_run_req_a` (in, from CRPM), `v0c0ext_arc_run_ack` (out, to CRPM)
  - **VPX2 internal halt/run** (ARCSYNC ↔ VPX2 core): `v0c0arc_halt_req` (out to VPX2), `v0c0arc_halt_ack_a` (in from VPX2), `v0c0arc_run_req` (out to VPX2), `v0c0arc_run_ack_a` (in from VPX2)
  - CRPM asserts `run_req` to bring VPX2 out of HALT after reset de-assertion
- **Semaphores and barriers**: Counting semaphores for shared resources, barrier semaphores for synchronization
- **MMIO registers**: AXI target interface accessible from system NoC
- **Core IDs**: VPX2 = core_id 8 (cluster 1, arcnum 0), NPX6 = core_id 1 (cluster 0, arcnum 1)

### Block Diagram (Conceptual)


 System Memory (DRAM/IMR)         NVU On-Die
 ┌──────────────────┐             ┌─────────────────────────────────────────────┐
 │                  │   IOSF/DMA  │                                             │
 │ FW Image         ├────────────►│  SRAM Sub-System (3.5MB PMEM + 16MB VMEM)   │
 │ Model Weights    │   SMMU      │  ┌──────────┐  ┌─────────────────────────┐  │
 │ Input Frames     │   Page-IN   │  │ 7 Slices │  │ SMMU (FW-managed paging)│  │
 │                  │◄───────────►│  │ w/ ECC   │  │ 4KB pages, IMR backing  │  │
 │                  │             │  └────┬─────┘  └─────────────────────────┘  │
 │                  │             │       │ Arteris FlexNoC Fabric               │
 │                  │             │  ┌────┴────────────────┬───────────────┐     │
 │                  │             │  │                     │               │     │
 │                  │             │  ▼                     ▼               │     │
 │                  │             │ ┌──────────────┐  ┌──────────────┐    │     │
 │                  │             │ │   VPX2 DSP   │  │  NPX6-1K NNA │    │     │
 │                  │             │ │ 128b VLIW/   │  │ 1024 MACs    │    │     │
 │                  │             │ │ SIMD + FPU   │  │ Conv + Tensor│    │     │
 │                  │             │ │ 128KB VCCM   │  │ 32KB AM +    │    │     │
 │                  │             │ │ 32KB I$/D$   │  │ 128KB VM     │    │     │
 │                  │             │ └──────┬───────┘  └──────┬───────┘    │     │
 │                  │             │        │   ARCSYNC        │           │     │
 │                  │             │        └──────┬───────────┘           │     │
 │                  │             │               │ IRQ, Run/Halt,        │     │
 │                  │             │               │ Semaphores             │     │
 └──────────────────┘             └─────────────────────────────────────────────┘


### Key Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| NPX6-1K MAC Units | 1024 MACs/clock (INT8) | Single NPU slice, convolution accelerator |
| VPX2 Vector MACs | 4 (32x32), 8 (16x16), 16 (8x8) MACs/clock | 128-bit SIMD vector DSP |
| SRAM Size (PMEM) | 3.5MB (3584KB) | 7 × 512KB slices, each slice = 4 × 128KB banks; 128-bit data path, SECDED ECC (9b/8b Hamming for 128b/64b). di/dt manager ensures only ONE slice exits deep-sleep at a time (600mA inrush per slice). |
| SRAM Size (VMEM) | 16MB virtual | FW-managed memory mapping via SMMU to DRAM (IMR); no on-demand paging or page swapping |
| NPX6 L1 Memory | 160KB total: 32KB AM + 128KB VM | Per-slice L1 memory (no ECC: NPU_MEM_ECC=0) |
| VPX2 Cache | 32KB I-cache + 32KB D-cache | Plus 128KB VCCM |
| NPX6 Data Types | INT8 (convolution), INT8/16/32 (tensor ops) | NPU_HAS_FLOAT=false, no FP16/BF16 on NPX6 |
| VPX2 Data Types | INT8/16/32, FP32, FP64 | Single & double precision FPU, 128-bit SIMD |
| Max Batch Size | Not specified in NVU HAS v1.0 | Firmware-managed scheduling |
| Tensor Dimensions | Not specified in NVU HAS v1.0 | Flexible 2D via STU with unaligned access |
| Clock Frequency | 400MHz (default), 200MHz (low-power) | VPX2, NPX6, and SRAM all at 400/200MHz |
| Peak TOPS (NPX6) | 0.8 TOPS | NPX6-1K at 400MHz (1024 MACs × 2 ops × 400MHz) |


## Model Loading

### Model Format

The NVU firmware runs on VPX2 and manages model loading to NPX6-1K. Per the HAS, the NVU accepts pre-compiled model binaries loaded through a firmware-managed boot and paging process:

- **FW Download**: Host driver downloads authenticated NVU firmware image from RS0 DRAM (up to 1.6 GB/s) through the IOSF primary interface
- **Authenticated FW Store**: FW is authenticated and written to RS3 DRAM (up to 1.6 GB/s)
- **SRAM Loading**: FW/model data is paged into the 3.5MB PMEM SRAM via the SMMU Page-IN DMA (up to 3.2 GB/s from DRAM)
- **NPX6 Model Data**: Loaded into NPX6 L1 memories (VM/AM) via the NPX iDMA/oDMA STU from SRAM (up to 3.2 GB/s)

| Section | Description |
|---------|-------------|
| NVU Firmware Image | Authenticated FW binary loaded by host driver at boot |
| Model Weights | Quantized weights (INT8 for NPX convolution) initially loaded into NVU IMR, then sequentially paged from IMR to SRAM to maximize SRAM utilization |
| Network Graph / Task Descriptors | Layer definitions stored in NPX6 L1 controller DCCM |
| Execution Plan | Managed by VPX2 firmware, tasks dispatched to NPX L1 controller |

### Model Format and Compilation (FAS §12, L13500-13600)

NVU neural network models follow a specific compilation pipeline:

| Stage | Tool | Input → Output | Notes |
|-------|------|----------------|-------|
| Training | Standard ML frameworks | Dataset → ONNX model | PyTorch, TensorFlow, etc. |
| Compilation | Synopsys NN SDK | ONNX → `.nnx` Execution Plan | INT8 quantization, layer fusion, memory mapping |
| Packaging | ImageTool | `.nnx` → NVU Extension Image | Wrapped with Module Manifest (`NN_MODEL`) |
| Loading | NVU FW (NNRT) | Extension Image → SRAM | Paged from IMR via SMMU PageIn DMA |

- **Model binary format**: `.nnx` — Synopsys proprietary execution plan compiled from ONNX
- **Quantization**: INT8 quantization for NPX convolution accelerator
- **Memory budget per NN algorithm**: Models are loaded sequentially to maximize SRAM utilization (FAS §12)
- **NN Model alignment**: Address and size must align to **page size (4KB)** for SMMU Page DMA loading (FAS §12, L13750)
- **Variant ID format** (64-bit): `model_index` is extracted as `variant & 0xFF` (lowest 8 bits, 0-255)

### Load Sequence

Per the HAS, the NVU boot and model load sequence involves:

1. **SRAM Zeroization & ECC Scrub** — The first thing after ROM starts is to trigger HW to do SRAM zeroization. Then FW scrubs all SRAM slices before use: for each slice, clear `cr_shutdown_en`, set `cr_ecc_scrub=1`, poll `ECCSCRUB` bit until cleared by HW, then configure DS override (`cr_deepsleep_override_val=0`, `cr_deepsleep_override_en=1`)
2. **VPX2 Boot** — VPX2 starts in HALT state after reset; CRPM asserts `run_req` to bring VPX2 out of halt; VPX2 begins executing ROM/FW from configured reset vector
3. **NPX6-1K Reset & Boot** — VPX2 firmware controls NPX6 lifecycle via ARCSYNC:
   1. De-assert NPX NoC reset (`npu_noc_rst_a`) and ARCSYNC resets
   2. Program `ARCSYNC.CORE_BOOT_IVB_LO` to set NPX reset vector
   3. Enable ARCSYNC/NoC clocks
   4. Enable NPX group clocks: write `0x1` to `ARCSYNC.CL0_GRP_CLK_EN.CLK_EN_L1_GRP0`
   5. Enable NPX slice clocks: write `0x1` to `ARCSYNC.CORE_CLK_EN_C1`
   6. De-assert NPX slice reset: write `(0xA5A5 << 16 | 0x1)` to `ARCSYNC.CORE_RESET_C1`
   7. Load boot code into SRAM/DCCM
   8. Unhalt NPX: write `ARCSYNC.CORE_RUN_C1`, poll until bit is 0
4. **Model Paging** — SMMU pages model data from DRAM (IMR) into SRAM. SMMU supports mapping/translation of virtual address space (IMR) to physical address space (SRAM).
5. **NPX6 L1 Load** — NPX6 L1 STU (iDMA/oDMA) transfers model weights/activations between L1 memories


## Inference Execution

### Submit Flow

Inference execution is firmware-driven with VPX2 as the orchestrator:

1. **Camera frame acquisition** — VPX2 FW receives camera data (MIPI CSI2 or USB) into SRAM via DMA
2. **Pre-processing (VPX2)** — VPX2 performs frame pre-processing: down-sampling (to QVGA for sensing), format conversion, normalization using its 128-bit SIMD vector unit
3. **NPX6 task dispatch** — VPX2 prepares task descriptors in NPX6 L1 controller DCCM via ARCSYNC DMI interface. Programs input tensor address and output buffer address in NPX6 memory space.
4. **NPX6 inference execution** — NPX6 L1 controller orchestrates:
   - iDMA loads input activations from SRAM into VM
   - Convolution accelerator processes layers (1024 INT8 MACs/clock)
   - Tensor accelerator applies activation functions (ReLU, sigmoid, etc.)
   - oDMA writes output tensors back to SRAM
5. **Completion notification** — NPX6 signals completion to VPX2 via ARCSYNC interrupt dispatch (VPX2 IRQ 107/108)
6. **Post-processing (VPX2)** — VPX2 reads inference results from SRAM, performs post-processing (e.g., NMS, classification)
7. **Result delivery** — VPX2 sends results to host/ISH via IPC (Host IPC IRQ 23, ISH IPC IRQ 31)

### Status Monitoring

Status is monitored through multiple mechanisms:

| Status | Mechanism | Details |
|--------|-----------|---------|
| VPX2 Idle/Running | CRPM signals | `sys_halt_r` (halted), `sys_sleep_r`/`sys_sleep_mode_r[2:0]` (sleep state), `cc_idle` (cluster idle) |
| NPX6 Run/Halt | ARCSYNC registers | `ARCSYNC.CORE_RUN_C1` (run request), `ARCSYNC.CORE_HALT_C1` (halt request/ack) |
| NPX6 Exceptions | VPX2 monitoring | NPX execution tightly monitored by VPX2; if NPX hits exception, VPX2 FW resets NPX |
| SRAM Errors | Slice Controller | `SSCEL.CERREV` (correctable ECC error), `SSCEL.UCERREV` (uncorrectable), `SSCEL.CNT` (error count) |
| DMA Completion | VPX2 IRQ 55 | DMA IRQ to VPX2 |
| ARCSYNC Events | VPX2 IRQ 107/108 | ARCSYNC IRQ0/IRQ1 for cross-core signaling |
| Watchdog Expiry | VPX2 IRQ 47 | WDT IRQ — triggers FW reset |
| SRAM Fabric | VPX2 IRQ 87 | SRAM_FABRIC IRQ for fabric errors |
| SMMU Events | VPX2 IRQ 88 | SMMU IRQ for page faults/translations |


## Supported Data Types

Per the HAS, the NPX6-1K is configured with `NPU_HAS_FLOAT=false` (no FP16/BF16 support on the NNA). The VPX2 DSP supports floating point.

### NPX6-1K NNA Data Types

| Type | Size | Use Case |
|------|------|----------|
| INT8 | 8-bit | Primary convolution inference (1024 MACs/clock), quantized models |
| INT16 | 16-bit | Tensor accelerator operations, accumulation |
| INT32 | 32-bit | Accumulator memory values |

### VPX2 DSP Data Types

| Type | Size | Use Case |
|------|------|----------|
| INT8/16/32 | 8/16/32-bit | SIMD integer vector operations (16/8/4 MACs/clock) |
| FP32 | 32-bit | Single-precision floating point (vector FPU) |
| FP64 | 64-bit | Double-precision floating point (scalar FPU) |

> **Note**: FP16/BF16 are **not supported** on either NPX6-1K (NPU_HAS_FLOAT=false) or VPX2 (fpu_hp_option=FALSE in VPX2 config). All neural inference on NPX6 uses INT8 quantized models.


## Error Handling

### Error Types

Per the HAS, the NVU provides the following error handling mechanisms:

| Error | Source | Detection | Recovery |
|-------|--------|-----------|----------|
| Watchdog Expiry | VPX2 WDT or NPX6 WDT | VPX2 IRQ 47 (WDT IRQ) | FW forced reboot — HW resets the CPU |
| SRAM Double-bit Error (DED) | SRAM Slice ECC | `SSCEL.UCERREV` bit set | FW forced reboot — HW resets the CPU |
| SRAM Single-bit Error (SEC) | SRAM Slice ECC | `SSCEL.CERREV` bit set, `SSCEL.CNT` incremented | Corrected by HW SECDED; FW monitors count (saturates at 0xFFFF) |
| NPX6 Exception | NPX6 core fault | VPX2 monitors NPX via ARCSYNC | VPX2 FW resets NPX6 (halt → clock gate → reset → ungate → de-assert → run) |
| VPX2 Triple Fault | VPX2 double-fault | `sys_tf_halt_r` signal to CRPM | Note: VPX2 only supports double-faults handled by machine check handler |
| VPX2 Memory Error | I-cache/D-cache/MMU fault | VPX2 IRQ 1 (MemoryError), IRQ 2 (InstructionError) | Exception handler in FW |
| DMA Error | Fabric DMA fault | VPX2 IRQ 55 (DMA), IRQ 59 (MAIN_FABRIC) | FW error handler, reset DMA |
| SMMU Page Fault | Virtual memory translation | VPX2 IRQ 88 (SMMU IRQ) | FW-managed page-in from DRAM |
| STU Error | VPX2 STU or NPX6 STU | VPX2 IRQ 21 (STU error), IRQ 22 (STU done) | FW error handler |

### NPX6 Exception Recovery Sequence (VPX2 FW-driven)

Per HAS Section 8.4.6:

1. **Halt NPX**: Write to `ARCSYNC.CORE_HALT_C1` — ARCSYNC issues halt request to NPX
2. **Wait for halt**: Poll `ARCSYNC.CORE_HALT_C1` until cleared (NPX in halt state)
3. **Gate clock**: Write `0x0` to `ARCSYNC.CORE_CLK_EN_C1`
4. **Assert reset**: Write `(0x5A5A << 16 | 0x1)` to `ARCSYNC.CORE_RESET_C1`
5. **Wait**: 100μs minimum
6. **Ungate clock**: Write `0x1` to `ARCSYNC.CORE_CLK_EN_C1`
7. **De-assert reset**: Write `(0xA5A5 << 16 | 0x1)` to `ARCSYNC.CORE_RESET_C1`
8. **Unhalt**: Write `ARCSYNC.CORE_RUN_C1`, poll until bit is 0

### SRAM Error Monitoring

The SRAM Slice Controller provides per-slice ECC logging via the `SSCEL` register:

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| `CNT` (CerrCnt) | 15:0 | ROVP | Correctable error count (saturates at 0xFFFF, reset only on powergood_rst_b) |
| `CERREV` | 16 | ROVP | Correctable error event flag (reset only on powergood_rst_b / Sx/G3) |
| `UCERREV` | 31 | ROVP | Uncorrectable error event flag (reset only on powergood_rst_b / Sx/G3) |

On watchdog expiry or SRAM DED, NVU FW is forced to re-boot (HW resets the CPU).


## Performance Counters

### VPX2 Performance Monitor

The VPX2 DSP includes a hardware performance monitor:
- **16 programmable performance counters** (`pct_counters=16`)
- Performance monitor interrupt supported (`pct_interrupt=TRUE`)
- VPX2 IRQ 20 (Performance Monitor interrupt)

Specific counter events are defined by the Synopsys ARC VPX2 architecture. TBD -- detailed event list not in HAS v1.0, refer to Synopsys ARC VPX2 Databook (6370-014).

### NPX6-1K Monitoring

NPX6 performance is monitored indirectly through VPX2 firmware via:
- ARCSYNC interrupt latency and dispatch timing
- NPX6 L1 controller status (task completion via ARCSYNC IRQ)
- STU transfer completion (iDMA/oDMA done signals)

TBD -- NPX6 internal performance counter details not in HAS v1.0, refer to Synopsys ARC NPX6-1K Databook (6442-016).

### System-Level Bandwidth Monitoring

Per HAS Section 11.2:

| Interface | Max Bandwidth | Usage |
|-----------|--------------|-------|
| VPX STU | 3.2 GB/s | VCCM ↔ SRAM |
| NPX iDMA/oDMA | 3.2 GB/s | AM/VM ↔ SRAM |
| Boot DMA | 1.6 GB/s | D2D, D2S transfers |
| SMMU Page-IN | 3.2 GB/s | DRAM → SRAM |
| IOSF Primary (FW download) | 1.6 GB/s | DRAM → NVU |
| IOSF Primary (paging) | 3.2 GB/s | RS3 DRAM → SRAM |

### Latency

| Metric | Value | Notes |
|--------|-------|-------|
| IOSF downstream turnaround | 3 clocks (fastest) | Request to credit return |
| IOSF upstream turnaround | 2 clocks (fastest) | Credit received to request |
| L1 cache miss (critical word) | 10 CPU clocks | VPX2 @ 400MHz, L2 @ 400MHz |
| L1 cache miss (full line) | 18 CPU clocks | VPX2 @ 400MHz, L2 @ 400MHz |
| SRAM deep-sleep exit | ~75ns (~30 clocks @ 400MHz) | Per 128KB bank |


## NN Offload Service (FAS §12, L13500-13800)

The NN Offload Service is the FW layer that manages neural network inference execution. It consists of two components running on separate cores:

### Architecture

| Component | Core | Role |
|-----------|------|------|
| **VPX Scheduler** | VPX2 DSP | Receives inference requests from WASM apps, manages model paging, dispatches jobs to NPX |
| **NPX Executer** | NPX6-1K | Receives execution plans, runs inference layers, returns results |

### NNRT (Neural Network Runtime) (FAS §12, L13650-13750)

The NNRT is a C++ runtime library running on VPX2 that provides the inference API to WASM applications:

- **Model loading**: Parses `.nnx` execution plan, allocates SRAM buffers, pages model from IMR
- **Job dispatch**: Prepares NPX task descriptors, sends via ARCSync to NPX Executer
- **Result collection**: Waits for NPX completion interrupt, reads output tensors
- **Memory management**: ~1.5MB budget per algorithm, allocator aligned to 0x40 (64B dcache line)

### VPX↔NPX IPC for Inference (FAS §12, L13700-13800)

The VPX Scheduler and NPX Executer communicate via ARCSync shared memory using these data structures:

| Structure | Description |
|-----------|-------------|
| `CoreState` enum | NPX state: UNINITIALIZED(0), READY(1), BUSY(2), ERROR(3) |
| `MessageId` enum | Job dispatch message types (inference start, abort, status query) |
| `CoreStatus` enum | NPX health: OK, ERROR, TIMEOUT |
| `CoreShareMemory` struct | Shared memory region for job descriptors and result pointers |

### Model Paging Flow (FAS §12, L13600-13650)

When an inference request requires a model not currently in SRAM:

1. VPX Scheduler checks if model pages are resident in SRAM
2. If not, triggers SMMU-managed DMA from IMR to SRAM (4KB page granularity, FW-managed page table mappings — no on-demand paging)
3. NNRT allocates NPX-accessible buffers (low → high for runtime, high → low for model data)
4. Model weights loaded into NPX L1 VM/AM via iDMA STU
5. Inference proceeds

> **Note**: There is **no page swapping** — once model pages are loaded, they remain in SRAM until explicitly freed. New model loads may require evicting a previous model entirely.


## AON Vision App Integration (FAS §12, L12663-13400)

Neural inference is consumed by AON Vision applications running in the WAMR sandbox. The App Manager, the backbone of NVU FW, connects and coordinates these applications. Key app types interact with the inference engine differently:

| App Type | Inference Access | Shared Memory | Restart Policy |
|----------|-----------------|---------------|----------------|
| **Core App** | Orchestrates execution pipeline, schedules WASM apps | YES | NOT restarted on failure |
| **Camera App** | Camera/ISP API only, no direct NN | NO | Restartable |
| **Algorithm App** | CV/NN offload API wrappers via sandbox | YES | Periodically restarted (security) |

### Face ID Vector Protection (FAS §12, L13200-13300)

Face recognition models require special handling for biometric template security. The Face ID algorithm app is not allowed to access stored face ID vectors directly, because face ID related algorithm apps could come from 3rd party sources:

| Phase | Action | Security Mechanism |
|-------|--------|-------------------|
| Boot-time | ESE fetches and decrypts previously stored Face ID vectors → SRAM | ESE hardware crypto, encrypted at rest |
| Runtime | Face ID app calls DSP offload APIs for matching | App has no read/write access to stored vectors in SRAM |
| Post-enrollment | ESE encrypts new vectors → SPI NOR storage | ESE hardware crypto, encrypted at rest |

### Algorithm App Lifecycle (FAS §12, L13100-13200)


Loaded → Instantiated & Enabled → [Running inference cycles] → Disabled & De-instantiated
                                         ↑                              |
                                         └── Optional periodic restart ─┘
                                             (security: clear sandbox state)



## Test Scenarios

### Basic NPX6 Inference Test
1. Boot NVU: VPX2 ROM → SRAM ECC scrub → FW load
2. Boot NPX6 via ARCSYNC (full reset flow per Section 8.4.5)
3. Load a small reference model (e.g., MobileNet quantized INT8) into SRAM, page to NPX6 L1 via iDMA
4. Submit a known input tensor (e.g., QVGA 640×480 frame)
5. Wait for ARCSYNC IRQ (VPX2 IRQ 107/108) signaling NPX6 completion
6. Read output tensor from SRAM and verify against golden reference
7. Check no error flags: `SSCEL.UCERREV`=0, `SSCEL.CERREV`=0, no watchdog expiry

### VPX2 Vector Processing Test
1. Load a CV processing workload on VPX2 (image pre-processing, down-sampling)
2. Execute using VPX2 128-bit SIMD vector unit
3. Verify output correctness
4. Monitor VPX2 performance counters

### Model Reload Test
1. Load model A via SMMU paging + NPX6 iDMA, run inference, verify output
2. Load model B (different weights), run inference, verify different output
3. Ensure no stale data from model A leaks into model B results (verify SRAM overwrite)

### Concurrent VPX2 + NPX6 Execution Test

The NVU supports concurrent execution on VPX2 (vector/scalar processing) and NPX6 (neural inference) simultaneously, coordinated via the uniform ARC core control scheme:

1. Start NPX6 inference on a neural model
2. Concurrently run VPX2 pre-processing on the next camera frame
3. Verify both outputs are correct (no cross-contamination via SRAM)
4. Measure throughput vs sequential execution

### NPX6 Exception Recovery Test
1. Induce an NPX6 exception (e.g., invalid memory access)
2. Verify VPX2 FW detects the exception
3. Execute NPX6 recovery sequence (reference NPX reset flow; VPX task dispatcher monitors NPX task completion status)
4. Verify NPX6 returns to functional state, re-submit inference
5. Verify correct output after recovery

### SRAM ECC Error Test
1. Inject a single-bit error in SRAM
2. Verify `SSCEL.CERREV` is set and `SSCEL.CNT` increments
3. Verify data is corrected by SECDED hardware
4. Inject a double-bit error
5. Verify `SSCEL.UCERREV` is set
6. Verify FW reset is triggered (watchdog/DED path)

### Watchdog Expiry Test
1. Configure WDT with short timeout
2. Submit workload that exceeds timeout
3. Verify VPX2 IRQ 47 (WDT) fires
4. Verify FW reboot is triggered

### NN Model Paging Test (FAS §12)
1. Load a model larger than available SRAM (requires IMR paging)
2. Trigger inference — verify SMMU DMA loads model pages from IMR to SRAM (4KB granularity, FW-managed page table mappings, no on-demand paging)
3. Verify inference produces correct output
4. Load a second model sequentially — verify first model execution is complete and second model is loaded from IMR to SRAM (page swapping/eviction is not supported)
5. Run inference on second model — verify correct output

### NNRT Memory Budget Test (FAS §12)
1. Load a model that consumes exactly 1.5MB (budget limit)
2. Verify allocation succeeds with 4 KiB alignment
3. Attempt to load a model exceeding 1.5MB budget
4. Verify graceful failure (NNRT returns error, no crash)

### Model Hot-Swap Test (FAS §12)
1. Run inference on Model A at 3 FPS
2. Trigger model swap to Model B (different architecture)
3. Verify Model A is fully evicted from SRAM and NPX L1
4. Verify Model B loads and produces correct output
5. Verify no data leakage between models (security: sandbox state cleared)

### Face ID Vector Security Test (FAS §12)
1. Boot NVU — verify NVU FW communicates with ESE to fetch previously stored Face ID vectors to SRAM
2. Run face matching inference — verify Face ID algo app cannot directly access stored vectors and must use DSP offload APIs
3. Enroll a new face — verify ESE encrypts and stores to SPI NOR
4. Verify MAX_ASSETS_NUM=15 limit is enforced
5. Verify MAX_ENROLLMENT_PER_BOOT=10 limit is enforced


## PythonSV Patterns

Pending PythonSV namespace allocation for NVU IP. The NVU is exposed as a PCI RCiEP (Root Complex Integrated Endpoint) on IOSF. Below are tentative patterns based on HAS register descriptions:

```python
```
# NVU PythonSV namespace not yet allocated
# NVU is a PCI RCiEP on IOSF, sideband endpoint name: "NVU"
#
# Example patterns (replace with actual paths when available):
#
# import pysvtools.pciedecode as pcie
# nvu = pcie.get_device(bus=0, dev=TBD, func=0)  # PCI function 0: NVU SW Driver
#
# === SRAM Slice Controller Registers ===
# Per-slice SSCR (Slice Controller Control Register):
#   Bit 0: RMWPIPESTG (RW, default=1) - RMW pipe stage enable
#   Bit 1: ECCENB (RW, default=0) - ECC enable (active low)
#   Bit 2: DSOVREN (RW, default=1) - Deep-sleep override enable
#   Bit 3: DSOVRVAL (RW, default=0) - Deep-sleep override value
#   Bit 4: SDEN (RW, default=1) - Shutdown enable
#   Bit 5: MEMPIPEN (RW, default=1) - Memory pipeline enable
#   Bits 11:8: DSMINDUR (RW, default=0x4) - Deep-sleep min duration
#   Bit 12: ECCSCRUB (RW1SV, default=0) - Trigger ECC scrub
#
# Per-slice SSCEL (ECC Log Register):
#   Bits 15:0: CNT (ROVP) - Correctable error count
#   Bit 16: CERREV (ROVP) - Correctable error event
#   Bit 31: UCERREV (ROVP) - Uncorrectable error event
#
# === ARCSYNC NPX6 Control ===
# ARCSYNC.CORE_BOOT_IVB_LO - NPX reset vector
# ARCSYNC.CL0_GRP_CLK_EN.CLK_EN_L1_GRP0 - NPX group clock enable
# ARCSYNC.CORE_CLK_EN_C1 - NPX slice clock enable
# ARCSYNC.CORE_RESET_C1 - NPX slice reset (0xA5A5<<16 | 0x1 to de-assert)
# ARCSYNC.CORE_RUN_C1 - NPX run request
# ARCSYNC.CORE_HALT_C1 - NPX halt request
#
# === VPX2 Interrupt Map (key entries) ===
# IRQ 20: Performance Monitor
# IRQ 21: STU Error
# IRQ 22: STU Done
# IRQ 23: HOST IPC IRQ
# IRQ 47: Watchdog Timer
# IRQ 55: DMA IRQ
# IRQ 87: SRAM Fabric IRQ
# IRQ 88: SMMU IRQ
# IRQ 107-108: ARCSYNC IRQ0/IRQ1 (NPX6 <-> VPX2)



## See Also

- [registers/SKILL.md](../registers/SKILL.md) — Full register map, MMIO layout
- [dma/SKILL.md](../dma/SKILL.md) — DMA channels feeding NPX6/VPX2
- [firmware/SKILL.md](../firmware/SKILL.md) — FW boot, model loading, IPC protocol, WAMR framework
- [camera/SKILL.md](../camera/SKILL.md) — SIO camera pipeline feeding inference
- [debug/SKILL.md](../debug/SKILL.md) — Performance counters, trace, VISA
- [driver/SKILL.md](../driver/SKILL.md) — AON Vision data interfaces (face/hand/body detection structs)
- **NVU FAS** — Firmware Architecture Specification (FAS §12: NN Offload Service, NNRT, Model Compilation)

## Related Sub-Skills

- [fv-nvu/dma](../dma/SKILL.md) — DMA architecture, buffer descriptors, data movement


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:19 | Facts added: 183


### Additional HAS Details (3 facts)

#### NVU Security and Privacy

##### Security Scope and Third-Party Customization
(HAS Ref: Chapter 6, Section 10.1.5 – Challenge in 3rd Party Customization)

- For TTL security and threat model analysis, **3rd party customization is not considered in scope**.
- However, for NVU IP HW/FW design, development must continue to be conducted with this consideration in mind.

##### NVU Firmware Security Design Overview
(HAS Ref: Chapter 6, Section 10.2.1 – NVU FW Security Design Overview)

- OEM code like BIOS is not within the TCB (trusted compute base) in NVU Threat Modeling Analysis.
- As a result, **OEM code like BIOS is not considered part of the Trusted Computing Base (TCB)** within the NVU threat model.

---

#### AON Vision Interface

##### Face Tracking Application – Known Limitations
(HAS Ref: Chapter 10, Section 14.2.8 – Face Tracking App)

- Face detection can fail under the following conditions:
  - **Temporal occlusion** — e.g., the user's face is partially or fully obscured by a hand, book, or similar object.
  - **Unstable lighting conditions** — variations in ambient lighting may cause unreliable detection results.
- These failure modes can potentially lead to **false activation of the Lock on Leave** feature.


### Camera Interface (8 facts)

#### Camera Interface Overview

The Neural Vision Sensing Unit (NVU) provides always-on (AON) visual sensing functionality associated with MIPI and USB cameras on the platform. (2 Introduction > 2.1 IP Description)

---

#### MIPI Camera Interface

- The NVU includes a **MIPI-IF Block** containing PHY sharing logic that interfaces with the IPU in the SoC to share the MIPI C/D-PHY. (2 Introduction > 2.2 Block Diagram)
- PHY sharing supports the following usage models:
  - **IPU owning the camera** — the IPU holds primary control of the MIPI C/D-PHY

---

#### USB Camera Interface

- The NVU includes a **USB-IF Block** containing USB Camera Offload Logic to receive the camera stream from the USB XHCI controller in the SoC. (2 Introduction > 2.2 Block Diagram)
- A **SIO Component** allows firmware to:
  - Stream data from XHCI
  - Stream data to the IPU
  - Interact with camera sensor control paths (2 Introduction > 2.2 Block Diagram)
- NVU supports IPU-hosted RAW/legacy cameras; in this mode, the streaming data is sent to IPU via SIO and LINK_LOGIC without needing to buffer it in SRAM.

##### USB Camera Pipeline (2 Introduction > 2.5.1.6)

- **DMA Engines** — NVU has two DMA engines within the USB offload logic for data streaming to SRAM/DRAM. (2 Introduction > 2.5.1.6)

###### SIO Component (2 Introduction > 2.5.1.6.1)

- The UVOL logic includes a **4 channel DMA controller**. The main function of the DMA is to move data from/to the SIO FIFO to the NVU SRAM. The DMA controller is based on the SNPS DW_axi_dmac IP.

###### USB De-packetizer (2 Introduction > 2.5.1.6.2)

- Implements a **FIFO** to buffer incoming USB packet data.
- Streams buffered data to SRAM.
- Depacketizer flows include: Input Flow (SIO DPKTZR Input Flow), Output Flow (SIO DPKTZR Output Flow), and procedures for Stopping the Streams.

---

#### Firmware Services for Camera Configuration

The NVU firmware architecture includes dedicated services that interact with camera interfaces at the platform level. (6 Chapter 2: NVU Firmware Overview > 6.1 NVU Firmware Architecture)

- **Configuration Service** — interfaces with the IPU and USB subsystems for camera sensor configuration.
- **Security & Privacy Service** — interfaces with the Embedded Security Engine (ESE) for firmware authentication.


### DMA Architecture (11 facts)

#### DMA Architecture Overview

(§2.5.1.10 DMA Controller)

The NVU incorporates multiple DMA engines serving distinct functions:

- A **4-channel DMA controller within the UVOL logic**, based on the SNPS DW_axi_dmac IP, whose main function is to move data from/to the SIO FIFO to the NVU SRAM (§2.5.1.10)
- A **dedicated DMA engine within the SRAM Sub-system (SRAM-SS)** for paging, with an additional dedicated DMA engine managed under HW control within the SMMU logic for virtual-to-physical memory data movement, with a programming interface exposed to FW for page management (§2.5.1.7.3 SMMU Capabilities)
- **Two additional DMA engines within the USB offload logic** for data streaming to SRAM/DRAM (§2.5.1.10)

---

#### DMA Controller Capabilities

(§2.5.1.10.1 Capabilities)

The following table defines the supported transfer modes for each SRC/DST memory region combination. Transfer modes are: **Direct**, **LLI** (Linked List Item), and **HW HS** (Hardware Handshake).

| SRC \ DST | PER Direct | PER LLI | PER HW HS | SRAM Direct | SRAM LLI | SRAM HW HS | DRAM:RS0 Direct | DRAM:RS0 LLI | DRAM:RS0 HW HS | DRAM:RS3 Direct | DRAM:RS3 LLI | DRAM:RS3 HW HS |
|------------|------------|---------|-----------|-------------|----------|------------|-----------------|--------------|----------------|-----------------|--------------|----------------|
| **PER** | N | N | N | Y | Y | Y | Y | Y | Y | N | N | N |
| **SRAM** | Y | Y | Y | Y | Y | N | Y | Y | N | Y | Y | N |
| **DRAM:RS0** | Y | Y | Y | Y | Y | N | Y | Y | N | Y | Y | N |
| **DRAM:RS3** | N | N | N | Y | Y | N | Y | Y | N | Y | Y | N |

---

#### DMA Capability Notes

(§2.5.1.10.1 Capabilities)

- When **SRC or DST** resides in **DRAM:RS3** and **LLI mode** is enabled, the LLI descriptors **must** be located in SRAM (`LLI_MODE = 0`).


### DSP Core (VPX2) (24 facts)

#### DSP Core (VPX2)

### Overview

The VPX2 is an ARC VPX2 DSP core integrated within the NVU, providing high-performance signal and neural network processing capabilities.

---

#### VPX2 Capabilities

(HAS §2.5.1.1.1)

- High-speed multiply, MAC, and vector-arithmetic (SIMD) instructions
- Radix-4 divide option
- Single-precision and double-precision floating-point options
- User and kernel operating modes
- Efficient instruction execution pipeline

---

#### VPX2 Components

(HAS §8.3.2)

| Component   | Version                                        |
|-------------|------------------------------------------------|
| SRAMCtrl    | com.arc.hardware.ARCv2MSS.SRAMCtrl.1_0         |

---

#### VPX2 Configuration Options

(HAS §8.3.3)

| Component   | Option                    | Value         |
|-------------|---------------------------|---------------|
| *(core)*    | infer_alu_adder           | instantiate   |
| *(core)*    | infer_mpy_wtree           | instantiate   |
| SRAMCtrl    | alb_mss_mem_region_num    | 1             |

---

#### VPX2 Integration Notes

(HAS §8.3.4)

- The `sys_tf_halt_r` signal is connected to CRPM; however, VPX2 does **not** support assertion of this signal — this connectivity exists for future usage only.
- VPX2 only supports double-faults, which is expected behavior for this configuration.

---

#### VPX2 Interrupts — SRAMSS

(HAS §8.1.1)

| Index | Module  | IRQ Name       | IRQ Pin   | Address |
|-------|---------|----------------|-----------|---------|
| 87    | SRAMSS  | SRAM_FABRIC IRQ | irq87_a  | 0x15C   |
| 88    | SRAMSS  | TLU IRQ         | irq88_a  | 0x160   |
| 89    | SRAMSS  | SHA IRQ         | irq89_a  | 0x164   |
| 90    | SRAMSS  | SPARE0 IRQ      | irq90_a  | 0x168   |
| 91    | SRAMSS  | SPARE1 IRQ      | irq91_a  | 0x16C   |
| 92    | SRAMSS  | SPARE2 IRQ      | irq92_a  | 0x170   |

**SRAM IRQ Behavior:**

- SRAMSS exposes only **2 active interrupts**: one mapped to `SRAM_FABRIC IRQ` and one to `TLU IRQ`.
- There is no other interrupt from SRAMSS to connect to the remaining IRQ lines.

---

#### VPX2 Addressable Memory Map

(HAS §8.2.1)

| Region | Size   | Address Range                   | Memory Type              | Target |
|--------|--------|---------------------------------|--------------------------|--------|
| 6      | 256 MB | 0x6000_0000 – 0x7000_0000       | Non-Volatile (Cacheable) | SRAM   |

---

#### VPX2 Detailed Memory Map — SRAMSS Regions

(HAS §8.2.2)

| Block          | Sub Region     | Size (KB) | Start Address | End Address  |
|----------------|----------------|-----------|---------------|--------------|
| SRAMSS_VMEMP   | SRAMSS_VMEMP   | 16,384    | 0x60000000    | 0x61000000   |
| SRAMSS_PMEM    | SRAMSS_PMEM    | 3,584     | 0x68000000    | 0x68380000   |
| SRAMSS_CFG     | SRAMSS_CFG     | 1,024     | 0xF5000000    | 0xF5100000   |

> `SRAMSS_CFG` resides in the **Register Targets** region of the VPX2 memory map.

---

#### NPX FW Memory Access Restrictions

(HAS §10.2.2)

- NVU hardware supports a **memory isolation mechanism** to restrict NPX runtime memory access exclusively to:
  - WAMR (WebAssembly Micro Runtime) shared memory
  - NN (Neural Network) model memory regions
- NPX is only accessible by VPX.
- This restriction enforces the security design principle of limiting NPX FW memory access to only authorized regions.


### Debug and Trace (1 facts)

#### RS3 Write Access via SMMU VMEM for NPX Model Debug

- RS3 writes via SMMU VMEM are enabled to support NPX model debug functionality (2.5 Requirements, id: 16029351904)

> **Note:** This requirement is currently in Plan of Record (POR) status.


### Firmware (1 facts)

#### Module Binaries

(HAS 6.2.1 NVU Image Structure)

- Module binaries contain the actual firmware, application, and model data within the NVU image structure
- Module binary data must be aligned to a **4 KiB boundary**


### IOSF Bridge (1 facts)

#### IOSF to AXI Bridge

- The sideband interface initiates a limited set of transactions under state machine control (2.5.1.11)
- Generic cycles initiated by the MinuteIA are **not** supported through this interface (2.5.1.11)


### Neural Network Accelerator (103 facts)

#### Neural Network Accelerator

### Overview (§2 Introduction, §5.1, §8.4 NPX6-1K)

The NVU1p0 integrates a **Synopsys ARC NPX6-1K Neural Processing Unit (NPU)** as its Neural Network Accelerator. The NPX6-1K is capable of **1024 Multiply-Accumulate (MAC) operations per clock cycle** and is designed for deep learning algorithm coverage across both computer vision and broader AI tasks.

- Supported model architectures include CNNs, RNN/LSTM, Transformers, and Recommender Networks (§2.2 Block Diagram)
- Target application domains include object detection, image quality improvement, and scene segmentation (§2.5.1.2)
- Compared to the previous-generation AVB architecture used in MCF(ULPV)/LNL(AVB), the NPX6-1K provides increased compute throughput (§2.4)
- Integration requirement tracked under HAS ID **16027428757** (§2.5)

---

#### Performance Targets (§2.6 Performance, §8.4 NPX6-1K)

- The NVU must operate the Neural Network Accelerator at **1K MAC/clock at 400 MHz**
- For the NPX6-1K configuration running at 400 MHz, the expected performance is **0.8 TOPS**
- The VPX compute cluster and SRAM subsystem operate at **400 MHz**
- The NPX6 architecture is scalable from 1K MACs to 96K MACs; NVU uses the minimum single-slice 1K MAC configuration

---

#### NPX6-1K Architecture (§8.4.3 NPX-1K Architecture)

- **L1 Controller:** Fixed-configuration ARC HS3x (ARCv2HS) processor that controls tasks performed by accelerators and manages data flow between L1 memories; includes an extension to handle asynchronous events
- **NPU Slice:** Contains the convolution accelerator and MAC array (1024 MACs per slice)
- **L1 Streaming Transfer Unit (STU):**
  - Contains NPU iDMA and oDMA accelerators
  - Performs data transfers between L1 memories
  - Supports flexible 2D data transfer
- **L1 Memory (per slice):**
  - **Vector Memory (VM):** Stores activation/weight values; spread over 32 vector banks (NPU-4K configuration reference)
  - **Activation Memory (AM):** Auxiliary memory for the slice
  - The ARC HS DCCM is also considered an L1 memory of the slice

For NVU, **a single slice with L1 memory** is instantiated to run vision neural network models. (§8.4 NPX6-1K)

---

#### NPX6-1K Configuration Parameters (§8.4.2 NPX6-1K Configuration)

| Option Name | NVU Value | Description |
|---|---|---|
| NPU_SLICE_NUM | 1 | Number of accelerator slices |
| NPU_SLICE_MEM | 32 KB + 128 KB | AM + VM memory size per slice (L1 Memory) |
| NPU_SLICE_MAC | 1024 | Number of MACs per slice |
| NPU_HAS_FLOAT | false | No support for FP16/BF16 |
| NPU_CSM_SIZE | 0 | No cluster shared memory |
| NPU_SAFETY_LEVEL | 0 | No safety mechanisms support |
| NPU_HAS_MMU | 1 | NPU supports MMU with physical address extension (PAE) |
| NPU_MEM_ECC | 0 | No ECC support on L1 memory |
| NPU_HAS_POWERDOMAINS | 0 | No per-slice power domain |
| NPU_ARC_TRACE | CoreSight | ARC Trace — not supported on NVU |

---

#### NPX6-1K Integration — CORE_ARCHIPELAGO (§8.4.4 NPX6-1K Integration)

##### Clock Interfaces

| Port Name | Connectivity | Description |
|---|---|---|
| npu_core_clk | CRPM | Core Clock — connect to NPX Functional Clock (unused internally) |
| npu_noc_clk | CRPM | NoC Clock — connect to NPX Functional Clock |
| sl0_clk | CRPM | Slice Clock — connect to NPX Functional Clock |
| sl0_wdt_clk | CRPM | Watchdog Clock — connect to FUNC_CLK/16 |
| arcsync_axi_clk | CRPM | ARCSYNC AXI Clock — connect to NPX Functional Clock |
| arcsync_clk | CRPM | ARCSYNC Clock — connect to NPX Functional Clock |
| pclkdbg | CRPM | Debug Clock — connect to NPX Functional Clock / 2 |

##### Reset Interfaces

| Port Name | Connectivity | Description |
|---|---|---|
| npu_core_rst_a | CRPM | Core Reset — connect to NPX Functional Reset (unused internally) |
| npu_noc_rst_a | CRPM | NoC Reset — connect to NPX Domain Functional Reset |
| arcsync_axi_rst_a | CRPM | ARCSYNC AXI Reset — connect to NPX Domain Functional Reset |
| arcsync_rst_a | CRPM | ARCSYNC Reset — connect to NPX Domain Functional Reset |

##### Bus and Debug Interfaces

| Interface | Port Name | Connectivity | Description |
|---|---|---|---|
| AXI-M | npu_mst0_axi* | Fabric | AXI Master port; clocked on npu_noc_clk (async to npu_core_clk) |
| AXI-S | npu_dmi0_axi* | Fabric | AXI Slave port; clocked on npu_noc_clk (async to npu_core_clk) |
| APB Debug | arct0_p* | Fabric | Debug APB port |
| Trace ATB | at* | Open/Tie-Off | Unused |
| Cross-Trigger | syncreq, cti* | Tie-off | Unused |
| Debug Security | sl0nl1arc_niden, sl0nl1_dbgen | DFX | Connect to DFX Secure Plugin (Slice DBGEN, NIDEN) |
| Debug Security | arct0_niden, arct0_dbgen | DFX | Connect to DFX Secure Plugin (ARC Trace DBGEN, NIDEN) |

---

#### NPX6 Debug Register Map — ARCTrace and L1 Core Registers (§8.2.3.2.2)

| Register | Address | Mode | Description |
|---|---|---|---|
| DB_STAT | 0x000 | — | Debug Status register |
| DB_CMD | 0x004 | — | Debug Command register |
| DB_ADDR | 0x008 | — | Debug Address register |
| DB_DATA | 0x00C | — | Debug Data register |
| DB_RESET | 0x010 | — | Debug Reset register |
| ITCTRL | 0xF00 | — | Integration Mode Control register — not used, RAZ |
| CLAIMSET | 0xFA0 | R/W | Claim Tag Set register |
| CLAIMCLR | 0xFA4 | R/W | Claim Tag Clear register |

---

#### NPX6 Addressable Memory Map (§8.2.3)

- **0x6000_0000 – 0x7000_0000** — 256 MB address region (ARCSYNC region)

---

#### Firmware and Neural Network Model Support (§6.2 NVU Firmware Layout, §6.2.3.1.2)

- The NVU firmware **base image** includes one NPX FW binary alongside one VPX FW, one Core App, and one AON image (§6.2)
- The **extension image** includes multiple WASM applications, several neural network models (packaged as `*.nnx` files produced by the PDT toolchain), and a single PDT binary (§6.2.3.1.2)

| Module Name | Binary Files | Purpose |
|---|---|---|
| NN_MODEL | *.nnx (from PDT) | Neural network models for apps with NN acceleration |

---

#### SRAM Subsystem (§2 Introduction, §2.4)

- The NVU includes a **scalable high-performance SRAM subsystem** with SRAM Slice Controllers (§2.2 Block Diagram)
  - Supports scalable tile configurations
  - In-line SECDED ECC support
  - Run-time retention capability
- Total SRAM size: **3584 KB** (compared to 8 MB / 5 MB on MCF(ULPV)/LNL(AVB) platforms) (§2.4)
- L1 NPU per-slice memory: 32 KB (AM) + 128 KB (VM) — no ECC on L1 memory (§8.4.2)


### Peripheral Interfaces (1 facts)

#### VPX2 Memory Map

*(HAS 8.2.2 – VPX2 Memory Map)*

The VPX2 memory map defines the addressable regions accessible from the VPX2 processor, including boot ROM, always-on retention fabric, and SRAM subsystem targets.

| Region | Block | Sub Region | Size (KB) | Start Address | End Address |
|--------|-------|------------|-----------|---------------|-------------|
| BROM | BROM | BROM | 16 | `0x00000000` | `0x00004000` |
| AONRF | AONRF | AONRF | 16 | `0x01000000` | `0x01004000` |
| SRAMSS_VMEMP | SRAMSS_VMEMP | — | — | — | — |

> **Note:** The SRAMSS\_VMEMP region start/end addresses and size were not fully specified in the available HAS source data. Refer to the complete HAS 8.2.2 table for the full region listing.

- **BROM** (`0x00000000`–`0x00004000`): 16 KB boot ROM region, mapped at the base of the VPX2 address space; used for initial boot code execution.
- **AONRF** (`0x01000000`–`0x01004000`): 16 KB always-on retention fabric region; accessible during low-power states.
- **SRAMSS\_VMEMP**: SRAM subsystem virtual memory port target region; full address range to be confirmed against the complete HAS source.


### SRAM and Memory (30 facts)

#### SRAM and Memory

### Overview

The NVU instantiates a scalable SRAM sub-system with a total physical capacity of **3584 KB (3.5 MB)**. (§2.5.1.7, §2.8.1)

---

#### SRAM Sub-system Composition

(§2.5.1.7)

- NVU instantiates a scalable SRAM sub-system comprising multiple configurable slices.
- Total physical SRAM: **3584 KB**.
- Area target for 3.5 MB SRAM: **< 3.5 mm²** (at 55% Std Cell Utilization, 90% EBB Utilization, and 20% StdCell Area Overhead). (§2.7.1)

---

#### SRAM Usage Modes

(§2.5.1.7.1)

The physical SRAM in NVU (3584 KB) can be mapped in the following ways:

- **Page-able memory**: To use SRAM as page-able memory, the page-able address range (VMEMP) in the memory map must be used. Pages are mapped at **4 KB granularity** (configurable).

---

#### SRAM Controller / Slice Controller Capabilities

(§2.5.1.7.2)

- **Slice configuration**:
  - Supports an arbitrary number of slices; dictated by physical placement of SRAM modules and frequency of operation.
  - Configurable slice size; typical slice size is **512 KB**.
  - Supports configurable data width.

- **Technology support**:
  - Supports arbitrary SRAM technology.
  - Restriction: the same SRAM technology modules must be used within a given slice.

- **ECC protection**:
  - Hamming code ECC: **9b/8b** for a **128b/64b** data path.
  - Reports single-bit correctable errors (SBE) and multi-bit uncorrectable errors (MBE).
  - Supports FW-initiated ECC scrub for initializing SRAM modules.

- **Timing path support**:
  - Supports configurable pipeline hooks to meet timing paths at high frequency.
  - Configurable pipe stage on read data path.
  - Configurable pipe stage for read-merge-write data path.

- **Power management**:
  - FW override for SRAM power management.
  - FW can place any SRAM slice (all banks within a slice) into **deep sleep** or **shut down** state.

---

#### SMMU Capabilities

(§2.5.1.7.3)

- SMMU logic supports mapping and translation of virtual address space (IMR) to physical address space (SRAM).
- Mapping is supported at the granularity of the configured page size (typical: 4 KB).
- The mapping is typically virtual-to-physical of the same memory region.
- **FW responsibility**: HW performs no default mapping; it is the responsibility of FW to program all SMMU mappings.

---

#### AONRF / BROM Controller Capabilities

(§2.5.1.8.1)

- Highly scalable, lightweight RF controller module.
- Supports OCP target interface to the NVU Fabric.
- Interfaces to non-ECC memory and memory that is either read-only or supports write strobes.

---

#### Global Manifest Structure — SRAM Fields

(§6.2.2)

The Global Manifest Structure (128 bytes) includes the following SRAM-related fields:

| Name | Offset | Size | Reset | Description |
|------|--------|------|-------|-------------|
| `sram_base` | — | — | — | Base address of NVU SRAM space |
| `sram_limit` | 48 | 4 B | — | Size of SRAM space (3.5 MB) |

---

#### Firmware Loading into SRAM

(§6.1)

- **Bring-UP (BUP) firmware** is stored in the platform IFWI.
- It is loaded and authenticated by ESE before BUP is placed into NVU SRAM and begins execution.

---

#### Security and Privacy — SRAM Assets

(§10.1.3)

- AON Vision HW/FW contains **two highly privacy-sensitive security assets** resident in SRAM that require strict protection beyond standard security requirements.

---

#### Requirements Tracking

(§2.5)

| Requirement ID | Owner | Title | Status |
|----------------|-------|-------|--------|
| 16027428758 | rchaddha | NVU - SRAM | Complete |
| 15018281537 | rchaddha | [TTL][NVU] Open up NVU SRAM Sub-region for ESE Access | Rejected |

