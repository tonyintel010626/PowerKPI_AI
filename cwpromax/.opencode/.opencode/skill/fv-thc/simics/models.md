# THC Simics Models & Transactors

> **Owner**: Chin, William Willy (`willychi`)
> **Domain**: FV-THC / Pre-Silicon Simics
> **Version**: 1.4
> **Parent**: `fv-thc/simics/SKILL.md`
>
> THC model architecture: SPI transactor, thc_vdm, TEP, alps_touchscreen, SPARK releases, Feature Model Overrides.

---

## Table of Contents

1. [SPI Transactor & Virtual Test Cards](#1-spi-transactor--virtual-test-cards)
2. [Existing THC Model: thc_vdm](#2-existing-thc-model-thc_vdm)
3. [Feature Model Overrides (Fmod)](#3-feature-model-overrides-fmod)
4. [Touch Device Model Architectures](#4-touch-device-model-architectures)
5. [SPARK Transactor THC Support History](#5-spark-transactor-thc-support-history)
6. [OSAL2DML Code Generation for THC Models](#6-osal2dml-code-generation-for-thc-models)
7. [SOC Override & RDL Instantiation](#7-soc-override--rdl-instantiation)

---

## 1. SPI Transactor & Virtual Test Cards

### SPI Transactor (spi_xtor)

The **SPI transactor** bridges Simics VDM (Virtual Device Model) and the DUT's SPI controller. It operates as:

```
DUT (THC SPI Controller) --> xtor RTL --> xtor SW (clock stops)
                                              |
                                              v
                                         Process opcode
                                              |
                                              v
                                    Get command length
                                              |
                                              v
                                    Receive full command
                                              |
                                              v
                                    Send to device VDM
                                              |
                                              v
                                    VDM responds (thc_vdm)
                                              |
                                              v
                                         xtor RTL --> DUT
```

### SPI Transactor Modes

| Mode | Class | Description | THC Relevant? |
|------|-------|-------------|---------------|
| UART | `spi_xactor_uart` | UART over SPI | No |
| NOR flash | `spi_xactor_nor` | NOR flash interface | No |
| TPM | `spi_xactor_tpm` | TPM over SPI | No |
| GSD AOH | `spi_xactor_gsd_aoh` | GSD AOH mode | No |
| **SPI flash generic** | `spi_xactor_flash` + `spi_xtor_flash_vdm` | **Generic SPI device** | **YES — connects to thc_vdm** |
| eSPI | `spi_xactor_espi` | eSPI mode | No |
| eSPI passthrough | `spi_xactor_espi_pt` | eSPI passthrough | No |

### Critical Quote from Wiki

> *"SPI flash generic mode is currently used to connect an SPI controller in the DUT with a Touch Host Controller (THC) Virtual Test Card (VTC)."*

This confirms that the `spi_xactor_flash` mode is the established connection path for THC in Simics.

> **⚠️ SPI Touch Limitation**: Per the PPA wiki (page 1249986923), SPI touch is **NOT FULLY SUPPORTED** in spi_xtor. The flash generic mode is used as a workaround to bridge the SPI controller to the thc_vdm, but native SPI touch protocol handling has known gaps. This is why the thc_vdm C++ model handles HIDSPI protocol framing rather than the transactor itself.

> For thc_vdm instantiation code, SPI opcode tables, and interrupt pin connection details, see [Section 2 — thc_vdm](#2-existing-thc-model-thc_vdm).

### Integration Setup (SPARK Repositories)

Add to `cfg/repositories.yml`:
- **spi-xtor** repo with `REPO_TAG=develop`
- **thc-vtc** repo with `REPO_TAG=develop`
- SPARK 1.12.x supports Direct Clocking mode for SPI transactor

> **VTC DEPRECATED**: As of SPARK 1.11.7, the original THC VTC component is deprecated due to lack of support. The replacement is **thc_vdm** (C++ device model). All new integrations should use thc_vdm directly.

---

## 2. Existing THC Model: thc_vdm

### Overview

The **`thc_vdm`** is an existing C++ device model implementing the **THC Virtual Test Card (VTC)** — the simulated touch device that connects to the THC SPI controller via the SPI transactor.

### Connection Architecture

```
+---------------------+     +------------------+     +-------------+
|  THC SPI Controller  |---->| spi_xactor_flash |---->|  thc_vdm    |
|  (DUT model in VP)   |     |   (SPI bridge)   |     | (Touch VTC) |
|                      |<----|                  |<----|             |
+---------------------+     +------------------+     +-------------+
```

### thc_vdm Attributes

#### Required Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `spi_host_obj` | SimicsObjectPortRef | Reference to `spi_xtor` object. Must implement `serial_peripheral_interface_master_interface` |
| `mem_space` | SimicsObjectPortRef | Reference to `memory_space` for reads/writes |

#### Optional Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `touch_int_cause` | uint32 | 0 | Interrupt cause register — maps to ICR (Input Cause Register) in HIDSPI |
| `tc_control` | uint32 | 0 | Test card control — configures VTC behavior |
| `ramless_datamode_ctrl` | uint32 | 0 | RAMLess datamode control — selects one of 4 data modes (see below) |
| `int_trigger` | uint32 | 0 | Interrupt trigger — simulates touch events |

#### RAMLess Data Modes

> **Source**: Wiki page 2141260829 (RAMLess HIDI2C)

The `ramless_datamode_ctrl` attribute selects the Sonora testcard RAMLess operating mode. Four data modes are supported:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Mode 0** | Standard RAM-backed | Normal operation with SRAM buffer |
| **Mode 1** | RAMLess with fixed pattern | Returns fixed test pattern data |
| **Mode 2** | RAMLess with incrementing | Returns incrementing byte pattern |
| **Mode 3** | RAMLess with custom | Returns user-configured data pattern |

RAMLess mode is primarily used for HIDI2C validation where the Sonora testcard operates without dedicated SRAM, relying on the THC DMA engine to manage data flow directly.

> **⚠️ RAMLess Mode Descriptions Differ**: The mode descriptions above (fixed pattern / incrementing / custom) come from wiki page 2141260829. An alternative description exists in `advanced.md` Section 21.2 (Sonora3 Testcard Details) which describes the modes as: on-the-fly / coalescing / streaming. Both descriptions are valid — they originate from different wiki sources documenting different Sonora testcard generations. Cross-reference both when writing RAMLess tests.

### spi_xactor_flash Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `flash_vdm` | SimicsObjectPortRef | Reference to `spi_xtor_flash_vdm` for opcode information |
| `check_upstream_timer_max` | uint32 | Max timer for upstream check (default: `0xFFFFFFFF`) |
| `dummy_bits` | uint32 | Number of dummy bits in SPI frames (default: `8`) |
| `fixed_dummy_bits` | uint32 | Fixed dummy bits (default: `0`) |
| `use_inband_alert` | bool | Enable in-band alert mechanism (default: `FALSE`) |
| `disable_sfdp_dummy_byte` | bool | Disable SFDP dummy byte (default: `FALSE`) |
| `send_sfdp_as_fast_read` | bool | Send SFDP as fast read (default: `FALSE`) |

### Mouse-as-Touch Testing

The thc_vdm supports a **mouse-as-touch** mode for interactive testing, where host mouse events are translated to touch input reports. This is useful for manual validation without a physical touch device. Commands:
```
thc_vdm.mouse_as_touch_enable = TRUE   # Enable mouse-as-touch
thc_vdm.mouse_as_touch_enable = FALSE  # Disable
```
*(Source: wiki page 1966867553 — THC model development, reference HAS: SIP_THC_ver2_0_HAS_MTLM_2020ww47)*

### SPI Transactor Regression Tests

The spi_xtor includes 3 THC-specific regression tests (source: wiki page 1249986975):

| Test | Path | Description |
|------|------|-------------|
| `touch` | `test/touch/` | Full touch flow test |
| `thc_legacy` | `test/thc_legacy/` | Legacy THC mode test |
| `thc_simple_io` | `test/thc_simple_io/` | Simple IO transactor test |

Unit test paths follow platform naming: `test/mtl/90-unit-tests/13-thc/` (MTL), similar pattern for LNL/PTL/NVL.

### Implications for THC FV

- **thc_vdm already exists** — we do NOT need to create a touch device VDM from scratch
- We need to understand its current **fidelity level** (does it support all HIDSPI report types? HID descriptors? Power states?)
- The THC **controller model** (the DUT side) is what needs to be created/enhanced
- The `int_trigger` attribute allows **programmatic touch event injection** — essential for automated testing

### VTC Deprecation Notice

> **Source**: Wiki page 1249986913 (spi_xtor Integration WIP) + 1249990578 (TC Getting Started)

- **THC VTC was DEPRECATED as of SPARK 1.11.7** due to lack of support — replaced by `thc_vdm`
- THC VTC status in TC Getting Started: "Migrated to Simics 6/Python 3. **Occasional support.**"
- All new THC Simics work should use `thc_vdm` (C++ device), NOT the legacy VTC
- SPARK repo for spi_xtor: `github.com/intel-innersource/frameworks.validation.spark.spi-xtor`

### thc_vdm Instantiation Code (from spi_xtor Integration)

```python
# thc_vdm instantiation (from wiki page 1249986913)
pre_conf_object('test_thc', 'thc_vdm')
# Set spi_host_obj -> spi_xtor object
# Set mem_space -> memory_space object
# Connect via spi_slave_obj + flash_vdm
```

### SPI Opcode Configuration per IO Mode

| IO Mode | Read Cmd | Write Cmd | Cmd Bits | Addr Bits | Dummy Bits |
|---------|----------|-----------|----------|-----------|------------|
| Single (1-1-1) | `0x0B` | `0x02` | 40 | 24 | 8 |
| Dual (1-2-2) | `0xBB` | `0xB2` | 40 | 24 | 8 |
| Quad (1-4-4) | `0xEB` | `0xE2` | 40 | 24 | 8 |

> These opcodes match the SPI EV reference data from wiki page 3466824139.

> **Write Opcode Discrepancy (Legacy VTC vs thc_vdm)**: The legacy VTC used different write opcodes for Dual and Quad modes: WR_1_2_2=`0x32` and WR_1_4_4=`0xe3`. The current thc_vdm uses WR_1_2_2=`0xB2` and WR_1_4_4=`0xE2` (matching the HIDSPI protocol spec). If referencing old VTC code or wiki pages, be aware of this difference. *(Source: wiki page 1249986913)*

### Interrupt Pin Connection (simple_io_xtor)

```
# simple_io_xtor for interrupt pin
thc -> thc_int = io_xtor
outputs_reset_value = 1    # Active-low interrupt
```

---

## 3. Feature Model Overrides (Fmod)

**Fmod** (Feature Model) replaces a Simics functional model with an **RTL-derived model** for higher fidelity. This uses **HFPGA** (Hybrid FPGA) technology.

### How It Works

```
Normal: CPU --> Simics DML Model --> Simics Memory
Fmod:   CPU --> Simics Stub --> FPGA --> RTL Model --> FPGA --> Simics Stub --> Simics Memory
```

### When to Use Fmod

- When **timing-sensitive behavior** must be verified
- When the **functional model has known gaps** that RTL can fill
- When **HW bug reproduction** requires RTL fidelity
- Typically for complex IPs: GPU, NPU, PCIe

### THC Fmod Consideration

- THC is a **medium-complexity IP** — functional model likely sufficient for most FV content
- Fmod may be useful if specific **SPI timing issues** or **DMA race conditions** need RTL-level debug
- Decision: Start with Register Functional Model, add Fmod if needed for specific issues

---

## 4. Touch Device Model Architectures

> **Source**: Wiki pages 1966867553, 4045307441, 3217199088, 1249986915

Two completely different touch device model types exist depending on protocol:

### 4.1 SPI Mode: TEP (Touch EndPoint) Model

Used for HIDSPI/QuickSPI protocol simulation.

**Platforms**: MTL, PTL (SPI mode)

**Object path**: `<platform>.tep.tep00` (THC0) / `<platform>.tep.tep10` (THC1)

**Key attributes**:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `reset_delay` | float | 0.2 | Reset delay in seconds (200ms) |
| `bulk_addr_read` | uint32 | 0x1000 | HID report bulk read address |
| `bulk_addr_write` | uint32 | 0x1000 | HID report bulk write address |
| `hid_report_descriptor_data` | tuple | — | 9-byte header + 3-byte padding + 2596-byte descriptor |
| `doze_enable` | bool | FALSE | If FALSE, doze enter/exit interrupts are ignored |
| `test_mfs` | uint32 | 0x9b1 | Max Frame Size (wiki source value; description "8 + descriptor_size(2600) + ReadDataHdr(64)" = 2672 != 0x9B1=2481 — discrepancy in original wiki, value likely correct) |
| `trigger_input_report` | bool | — | Set TRUE to trigger touch data delivery via DMA |
| `wa_ignore_setidvalue` | bool | FALSE | WA for HSDES 1508517875 SetIDValue assertion |

**Architecture**: TEP handles HIDSPI protocol framing internally. Connected to THC via spi_xtor transactor.

**Mouse simulation**: Supported via `connect <platform>.recorder.tablet_out <platform>.tep.tic00_as_abs_mouse`

### 4.2 I2C Mode: alps_touchscreen Model

Used for HIDI2C/QuickI2C protocol simulation.

**Platforms**: LNL, PTL (I2C mode), NVL-S

**Object path**: `<platform>.alps_touchscreen0` (THC0) / `<platform>.alps_touchscreen1` (THC1)

**Key attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `trigger_input_report` | bool | Set TRUE to trigger touch data delivery |

**Data injection**: Via include files that define raw report bytes:
- `alps0_input_report.include` — touch coordinate data
- `alps0_hid_report_descriptor.include` — HID report descriptor
- `alps0_hid_device_descriptor.include` — HID device descriptor

**Architecture**: Connected to THC via i3c_xtor with I2C compatibility mode. Does NOT use spi_xtor.

**Mouse simulation**: NOT supported. Must manually edit X/Y coordinates in include files.

### 4.3 Model Architecture Comparison

```
SPI Path:  [THC Model] <-> [spi_xtor] <-> [TEP / thc_vdm]
I2C Path:  [THC Model] <-> [i3c_xtor] <-> [alps_touchscreen]
```

| Feature | TEP (SPI) | alps_touchscreen (I2C) |
|---------|-----------|----------------------|
| Mouse simulation | Yes | No |
| Protocol framing | Internal | Via include files |
| Reset delay config | Configurable | Not documented |
| HID descriptor | Attribute-based | Include file |
| MFS configuration | `test_mfs` attribute | Not documented |
| Doze support | `doze_enable` attribute | Not documented |

**TTL Impact**: Since TTL targets I2C mode, the `alps_touchscreen` model is the relevant architecture. No mouse simulation — all touch testing requires manual coordinate injection via include files.

---

## 5. SPARK Transactor THC Support History

> **Source**: SPARK 1.11.x release notes (page 1620643113)

SPARK (Simics Platform Architecture Kit) provides the I/O-level transactors that connect THC device models to touch VDMs.

### 5.1 THC-Related SPARK Releases

| SPARK Version | HSDES | Type | Xtor | Description | Platform |
|---------------|-------|------|------|-------------|----------|
| **1.11.5** | 1508628560 | Bug Fix | spi_xtor | **Infinite loop in THC module when paired to spi_xactor_flash device** | MTL-S |
| **1.11.8** | 14015253601 | New Feature | i3c_xtor | **Enhanced device xtor to support THC using I2C** | General |
| **1.11.11** | 16018039801 | New Feature | i3c_xtor | **I2C xtor requirement aligned with THC HAS** | General |
| **1.11.11** | 16018045412 | New Feature | spi_xtor | **Touch device VDM + HIDSPI support per THC HAS** | General |

### 5.2 Evolution Phases

- **Phase 1 (SPARK 1.11.5)**: Bug fix for existing SPI-mode THC on MTL-S — critical infinite loop resolved
- **Phase 2 (SPARK 1.11.8)**: I2C support added to i3c_xtor — HIDI2C protocol enablement
- **Phase 3 (SPARK 1.11.11)**: Both I2C and SPI xtors formally aligned to THC HAS — full protocol compliance

### 5.3 Key Architecture Notes

- **SPI path**: `spi_xtor` -> `thc_vdm` (C++ class)
- **I2C path**: `i3c_xtor` with I2C compatibility mode -> `alps_touchscreen`
- `thc_vdm` attributes: `spi_host_obj`, `mem_space`, `touch_int_cause`, `tc_control`, `ramless_datamode_ctrl`, `int_trigger`
- **NOT in SPARK**: `TEP`, `alps_touchscreen`, `tic00` — these are in **platform-specific model repos**, not in SPARK
- SPARK 1.11.x was EOL'd; newer platforms (NVL, TTL) likely use SPARK 1.12.x or later

### 5.4 Minimum SPARK Version for THC

| Protocol | Minimum SPARK | Reason |
|----------|---------------|--------|
| HIDSPI (SPI) | >= 1.11.11 | VDM + HIDSPI support per HAS (16018045412) |
| HIDI2C (I2C) | >= 1.11.8 (basic), >= 1.11.11 (HAS-aligned, recommended) | 1.11.8 first added I2C support (16018039801); 1.11.11 aligned both xtors with HAS |
| Any (basic) | >= 1.11.5 | Infinite loop fix (1508628560) |

---

## 6. OSAL2DML Code Generation for THC Models

> **Source**: Wiki page 3937898817 (SRESIMICS); see also `advanced.md` Section 13

THC register models can potentially be **auto-generated** from OneSource via the OSAL2DML pipeline:

```
OneSource XML (THC HAS) → OSAL Parser → Mako Templates → DML 1.4 Register Banks
```

- **OSAL2DML** = OneSource Abstraction Layer to DML 1.4 code generator (Simics package **9804**)
- **OSDML** = older pipeline (package **9803**)
- Repo: `intel-innersource/applications.simulators.isim.vp.osdml`
- Config file per chip: e.g., `spr-osdml.cfg` — would need a THC-specific config
- Output: DML register bank files with correct offsets, bit fields, reset values from HAS
- **THC applicability**: If THC HAS registers are in OSXML format, the entire register model could be auto-generated rather than hand-coded in DML

> For full OSAL2DML details, see `fv-thc/simics/advanced.md` Section 13.

---

## 7. SOC Override & RDL Instantiation

> **Source**: Wiki page 1172406469 (SOC Override, pch space)

### THC RDL Architecture

THC delivers a **single RDL** (Register Description Language) model. The SOC instantiates it **twice** to create THC0 and THC1:

- **THC0**: PCI Function 0 — primary port
- **THC1**: PCI Function 1 — secondary port (requires THC0 enabled)

### SOC Override Parameters

The SOC override mechanism allows platform-specific customization of THC instances:

| Override | THC0 Example | THC1 Example | Description |
|----------|-------------|-------------|-------------|
| **BDF** | Platform-specific | Platform-specific | Bus/Device/Function assignment |
| **PortID** | `0x39` | `0x3A` | IOSF Sideband port identifier |
| **DID** | `0xA0D0` | `0xA0D1` | PCI Device ID (platform-dependent) |

### BAR0 Mask Workaround

> The SOC override includes a **BAR0 mask workaround** — the THC RDL BAR0 mask may need platform-specific adjustment to correctly report the 32KB MMIO range. Verify BAR0 size reporting (`0x7FFF` mask for 32KB) after SOC integration.

### Implications for Simics Models

- When creating a Simics functional model, only ONE DML model is needed — instantiate it twice with different BDF/DID/PortID parameters
- The `cfg/overrides/` directory in platform repos typically contains THC override files
- Platform-specific DID values MUST match the SOC override, not the THC RDL default

---

## See Also

- **`fv-thc/simics/SKILL.md`** — Core concepts, FV strategy, gap analysis
- **`fv-thc/simics/operations.md`** — Per-platform setup, BIOS config, driver install
- **`fv-thc/simics/advanced.md`** — SW-CI, emulation/HFPGA, IPSV, DFD, OSAL2DML, SimCloud
- Post-silicon HIDSPI protocol: `fv-thc/hidspi`
- Post-silicon HIDI2C protocol: `fv-thc/hidi2c`

---

*End of THC Simics Models & Transactors — models.md*
