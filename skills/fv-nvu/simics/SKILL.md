# NVU Simics Sub-Skill — Skeleton

> **Status**: SKELETON — awaiting NVU Simics model availability
> **Version**: rev0.1 (skeleton)
> **Last Updated**: 2026-03-28
> **Owner**: William Willy Chin (`willychi`) | Co-owner: Yi Jie Leem (`yleem`)

## Overview

This sub-skill will contain **Simics virtual platform** knowledge for NVU pre-silicon and post-silicon co-validation. It is modeled after the [FV-THC Simics sub-skill](../../fv-thc/simics/SKILL.md) which provides register-level Simics model documentation for the Touch Host Controller.

### What This Will Cover (When Populated)

1. **NVU Simics Model Architecture**
   - Device model structure (DML modules, register banks)
   - Memory-mapped register simulation
   - PCI configuration space emulation
   - Interrupt delivery (MSI via WIRE2MSI)

2. **Register Bank Mapping**
   - BAR0 (64KB) — Host IPC registers
   - BAR1 (if enabled) — Camera/VOD registers
   - PCI Config Space (Type 0 header + capabilities)
   - IOSF Sideband private config (64KB)

3. **Sub-IP Models**
   - VPX2 DSP core model
   - NPX6-1K NNA model
   - DesignWare AXI DMA controller
   - MIPI-IF / USB-IF subsystem stubs
   - DesignWare I2C/I3C/SPI/UART peripheral models
   - SRAM subsystem (7 slices × 512KB)

4. **Simulation Scenarios**
   - FW boot ROM execution
   - Host IPC message exchange
   - DMA transfer simulation
   - Power state transitions (D0i0 → D0i1 → D0i2 → Lid-Closed)
   - Camera frame injection (MIPI / USB)

5. **Validation Integration**
   - PythonSV ↔ Simics bridge for register access
   - Test script compatibility (same scripts on silicon and Simics)
   - Known Simics model limitations vs real silicon behavior

## Blocking Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| NVU Simics model creation | ❌ Not started | No NVU Simics model exists yet |
| NVU HAS register map extraction | ✅ Done | Available in [fv-nvu/registers](../registers/SKILL.md) |
| NVU DMA architecture extraction | ✅ Done | Available in [fv-nvu/dma](../dma/SKILL.md) |
| NVU power state extraction | ✅ Done | Available in [fv-nvu/power](../power/SKILL.md) |
| NVU PCI config extraction | ✅ Done | Available in [fv-nvu/platform](../platform/SKILL.md) |

## THC Simics Reference

The THC Simics sub-skill (v1.4, 4 files, ~3,500 lines) provides a proven template:

| THC File | NVU Equivalent (Future) | Purpose |
|----------|------------------------|---------|
| `SKILL.md` | `simics/SKILL.md` (this file) | Core register maps, PCI config, Simics model architecture |
| `advanced.md` | `simics/advanced.md` | DMA model, interrupt simulation, power state machine |
| `validation.md` | `simics/validation.md` | Test scripts, scenarios, known limitations |
| `development.md` | `simics/development.md` | DML development guide, debugging Simics models |

## Cross-References

- [fv-nvu/registers](../registers/SKILL.md) — Register map (source for Simics register banks)
- [fv-nvu/dma](../dma/SKILL.md) — DMA architecture (source for DMA model)
- [fv-nvu/power](../power/SKILL.md) — Power states (source for PM state machine)
- [fv-nvu/platform](../platform/SKILL.md) — PCI config, straps, fuses
- [fv-nvu/firmware](../firmware/SKILL.md) — Boot ROM, FW loading (source for boot simulation)
- [fv-nvu/driver](../driver/SKILL.md) — Host driver IPC (source for host-side simulation)
- [fv-thc/simics](../../fv-thc/simics/SKILL.md) — THC Simics reference implementation

## Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-28 | rev0.1 | Initial skeleton — awaiting NVU Simics model |


---

## HAS-Sourced Enrichment

> Auto-generated from NVU HAS facts not previously covered in this skill file.

> Generated: 2026-04-06 00:06 | Facts added: 14


### Camera Interface (1 facts)

#### Simulation Environment

*(HAS Ref: Chapter 8: AON Vision App Development > 12.6 3rd Party App Development > 12.6.1 NVU WAMR SDK > 12.6.1.2 Simulation Environment)*

- The simulation environment is tailored to test single-algorithm Wasm applications without the need for the core app and camera app.


### DSP Core (VPX2) (1 facts)

#### Development Toolchain Support

(HAS 8 IP-Specific Description > 8.3 VPX2)

- The ARC VPX2 DSP processor family is supported by Synopsys' **ARC MetaWare Development Toolkit**
- The toolkit provides a comprehensive software programming environment to accelerate application software development


### Neural Network Accelerator (4 facts)

#### Neural Network Accelerator

##### Tensor Operation Accelerator — Activation Functions

(HAS Ref: 8 IP-Specific Description > 8.4 NPX6-1K > 8.4.3 NXP-1K Architecture)

- The NPU includes a Generic Tensor Operation accelerator supporting the following activation function types:
  - **ReLU type**: The typical activation function supporting different scaling factors for positive and negative inputs

---

#### Simulation Environment

(HAS Ref: 12 Chapter 8: AON Vision App Development > 12.6 3rd party App Development > 12.6.1 NVU WAMR SDK > 12.6.1.2 Simulation Environment)

- The simulation environment enables developers to thoroughly test their applications, verifying:
  - Functional outputs
  - Adherence to the expected application framework
- Once the simulation environment is ready, it can be integrated into:
  - **CI systems** for automated continuous integration testing
  - **Fuzzing test environments** and other testing pipelines

---

#### Downstream Transaction Ordering

(HAS Ref: 9 Transaction Flows > 9.2 Ordering/Coherency Rules > 9.2.1 Ordering Model > 9.2.1.1 Transaction Ordering > 9.2.1.1.1 Downstream Transaction Ordering)

- **DS CPL push DS P** is a PCI ordering requirement governing ordering between downstream completions (DS CPL) and downstream posted writes (DS P)
- This ordering is implemented based on the **RO (Relaxed Ordering) attribute** of the DS CPL requests:
  - If the DS CPL request has the **RO bit set**, ordering behavior is determined accordingly per PCI specification requirements


### NoC Fabric (1 facts)

#### Debug Trace Fabric — NVU Usage Model and Requirements

(HAS §15.5.1.3)

- NVU HW VISA does **not** use the DTF packetizer/encoder interface.
- In this generation, the NVU FW validation team will have the capability of **time-synchronized debugging** of NVU FW with another entity in the SoC.


### PMC Integration and Wake (7 facts)

#### NVU WAMR SDK Simulation Environment

*(HAS: Chapter 8 § 12.6.1.2 Simulation Environment)*

#### Overview

- The NVU WAMR SDK includes a standalone simulation environment that operates on **x86 Linux** (HAS: 12.6.1.2)
- Parallel implementations are employed to simulate the behavior of CV/NN services; these implementations are minimized to ensure efficient testing (HAS: 12.6.1.2)

#### Verification Capabilities

- The simulator verifies the **output image** produced by the Wasm application (HAS: 12.6.1.2)
- The simulator checks whether the Wasm application adheres to the correct framework by processing various types of incoming messages (HAS: 12.6.1.2)
- Application responses across different scenarios are validated, supporting robust testing of complex applications (HAS: 12.6.1.2)

#### Framework Requirements

- The simulation environment requires **message looping** and **native functions** from the app management framework (HAS: 12.6.1.2)
- These components must be reused **without modification** to ensure consistency and reliability in the testing process (HAS: 12.6.1.2)

#### Simulator Invocation

The simulator is invoked using the following command syntax (HAS: 12.6.1.2):

```
simulator algo.wasm <event_type> <input_data>
```

| Argument | Description |
|---|---|
| `algo.wasm` | The compiled Wasm application under test |
| `<event_type>` | The type of incoming message/event to simulate |
| `<input_data>` | The input data payload supplied to the application |

