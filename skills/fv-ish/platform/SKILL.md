# FV-ISH Platform-Specific Configurations Skill

> **Skill**: `fv-ish/platform`
> **Domain**: Per-Platform ISH Hardware Configurations
> **Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
> **Last Updated**: 2026-03-16
> **Primary Focus**: NVL (Nova Lake)

---

## IMPORTANT: HAS-First Policy

All PCI Device IDs, BDFs, register offsets, and BOM data MUST be verified against the platform-specific ISH HAS before use. Load `fv-ish/has` and query Co-De Sign for the target platform. Never assume values carry over between platforms. TTL data is populated from the ISH 5.9 HAS and TTL OSXML register PDFs.

---

## 1. Platform Overview

| Platform | Codename | ISH IP Version | Core | Status | Primary Validation |
|----------|----------|---------------|------|--------|-------------------|
| **NVL** | Nova Lake | ISH 5.8 | LMT 3.9 | **PRIMARY FOCUS** | Active |
| **TTL** | Titan Lake | ISH 5.9 | LMT 3.8/3.9 | HAS Available | Reference Data |
| **PTL** | Panther Lake | [TODO] | [TODO] | Active | Active |
| **ARL** | Arrow Lake | [TODO] | [TODO] | Active | Active |
| **LNL** | Lunar Lake | [TODO] | [TODO] | Previous | Reference |
| **MTL** | Meteor Lake | [TODO] | [TODO] | Previous | Reference |

---

## 2. TTL (Titan Lake) — Reference Platform with HAS Data

> TTL ISH data is sourced from the ISH 5.9 HAS (SIP_ISH5p9) via Co-De Sign and
> TTL OSXML register PDFs (ish_wrapper_host.pdf, ish_mia_bfm_rdl_top.pdf).
> See `fv-ish/has/docs/ttl/` for full reference documents.

### 2.1 TTL ISH PCI Configuration

| Field | Value | Source |
|-------|-------|--------|
| **PCI Vendor ID** | `0x8086` (Intel) | OSXML ish_wrapper_host.pdf |
| **PCI Device ID** | `0xE445` | OSXML ish_wrapper_host.pdf |
| **PCI Class Code** | `0x118000` (Signal Processing Controller) | Standard |
| **BAR0** | MMIO (64-bit) — ISH HOST wrapper register space | OSXML |
| **IRQ** | MSI/MSI-X | OSXML |
| **Power** | VNNAON power well, FUNCRST reset | OSXML |

```python
# TTL ISH PCI Device ID — verified from OSXML register PDF
TTL_ISH_DEVICE_ID = 0xE445
TTL_ISH_VENDOR_ID = 0x8086

# Detect ISH BDF programmatically (Linux)
# lspci -d 8086:E445 -n | awk '{print $1}'

# Detect ISH in PythonSV
# target.pch_ish   (verify namednode name from PythonSV metadata)
```

### 2.2 TTL ISH Architecture Summary

| Feature | TTL Value | Source |
|---------|-----------|--------|
| ISH IP Version | ISH 5.9 (SIP_ISH5p9) | Co-De Sign HAS |
| Core | LMT 3.8/3.9 (MinuteIA) | Co-De Sign HAS |
| Clock Frequency | 200/100 MHz | Co-De Sign HAS |
| ROM | 8 KB | Co-De Sign HAS |
| SRAM | 640 KB (20 × 32KB banks) | Co-De Sign HAS |
| AON RF SRAM | 8 KB | Co-De Sign HAS |
| I2C Controllers | 3 (DW_apb_i2c, 1 Mb/s) | OSXML MIA PDF |
| I3C Controllers | 2 (HCI v1.0, 25 Mb/s HDR/DDR) | OSXML MIA PDF |
| UART Controllers | 3 (DW_apb_uart, 4 Mb/s) | OSXML MIA PDF |
| SPI Controllers | 2 (DW_apb_ssi, 25 Mb/s) | OSXML MIA PDF |
| GPIO Pins | Up to 12 | Co-De Sign HAS |
| DMA Channels | 8 (configurable) | OSXML MIA PDF |
| IPC Channels | 8 (HOST, HOSTSPARE, CSE, PMC, CNVi, ACE, ESE, AVB) | OSXML |
| IPC Payload | 128 bytes per direction (32 × 32-bit MSG regs) | OSXML |
| Host Interface | IOSF (NOT PCIe) | Co-De Sign HAS |
| FW Boot | ROM → CSE/BUP (64KB) → Host/MainFW (1.5MB via IMR) | Co-De Sign HAS |
| WDT | Two-stage (T1=interrupt, T2=reset) | OSXML MIA PDF |
| Power States | D0, D0i1, D0i2, D0i3, D3 | Co-De Sign HAS |
| SRAM Gating | Per-bank (30 bank/tile bits, PMU_SRAM_PG_EN) | OSXML MIA PDF |
| PMC Sideband | Opcode 0x6Fh, Tag 0x06h | Co-De Sign HAS |

### 2.3 TTL MIA Internal Address Map

| Block | Base Address | Instances | Stride | IP |
|-------|-------------|-----------|--------|-----|
| I2C | 0x00000000 | 3 | 0x2000 | DW_apb_i2c |
| GPIO | 0x00100000 | 1 | — | Custom |
| IPC Config | 0x04100000 | 8 channels | 0x1000 | Custom |
| PMU | 0x04200000 | 1 | — | Custom |
| CCU | 0x04300000 | 1 | — | Custom |
| I3C | 0x04800000 | 2 | 0x2000 | HCI v1.0 |
| WDT | 0x04900000 | 1 | — | Custom |
| SPI | 0x08000000 | 2 | 0x2000 | DW_apb_ssi |
| UART | 0x08100000 | 3 | 0x2000 | DW_apb_uart |
| DMA Misc | 0x10101000 | 1 (8 ch) | — | Custom |
| SRAM Ctrl | 0x10500000 | 1 | — | Custom |
| Fabric | 0x10600000 | 1 | — | Custom |

### 2.4 TTL HOST Wrapper IPC Channel Map

| Channel | Base Offset | Transport | Purpose |
|---------|------------|-----------|---------|
| HOST | 0x000 (MEM) | Memory-mapped | Primary host communication |
| HOSTSPARE | 0x000 (MEM, separate) | Memory-mapped | Spare host channel |
| CSE | 0x1000 (MSG) | Sideband message | Security engine |
| PMC | 0x2000 (MSG) | Sideband message | Power management controller |
| CNVi | 0x3000 (MSG) | Sideband message | Connectivity |
| ACE | 0x4000 (MSG) | Sideband message | Audio/compute engine |
| ESE | 0x5000 (MSG) | Sideband message | Embedded security |
| AVB | 0x6000 (MSG) | Sideband message | Audio/video bridge |

### 2.5 TTL BIOS Prerequisites

| BIOS Setting | Required Value | Purpose |
|-------------|---------------|---------|
| ISH Enable | Enabled | Enables ISH PCI device (0xE445) |
| ISH BAR0 | Allocated (64-bit MMIO) | ISH HOST wrapper register space |
| ISH Sensor Routing | Configured per BOM | Routes I2C/I3C/SPI to sensors |
| ISH Firmware | Latest TTL FW binary | ISH firmware provisioned via IMR |
| ACPI ISH Scope | Present in DSDT | ISH ACPI enumeration |
| ISH S0ix Support | Enabled | Allows ISH during S0ix |
| IMR Allocation | Sufficient for 1.5MB FW | ISH DMA firmware loading |

### 2.6 TTL Validation Focus Areas

1. **IPC Doorbell Protocol**: Verify doorbell BUSY handshake, 128-byte payload transfers
2. **8-Channel IPC**: Validate HOST, CSE, PMC channels functional; test sideband channels
3. **FW Boot Flow**: Verify ROM → BUP (64KB via CSE) → Main FW (1.5MB via IMR/DMA)
4. **S3 Resume Fast Path**: Verify CSE hash-check optimization saves ~200ms
5. **SRAM Power Gating**: Validate per-bank gating via PMU_SRAM_PG_EN (30 bits)
6. **WDT**: Verify two-stage watchdog (T1 interrupt, T2 reset)
7. **I3C Support**: Validate I3C HCI v1.0 with HDR-DDR mode, IBI, dynamic addressing
8. **D0i3 Transitions**: Verify D0I3C register protocol (CIP/D0i3 handshake)

### 2.7 TTL Known Issues

> Populate from validation findings and HSDES sightings.
> Use `hsdes` skill: `hsdes search "ISH TTL" tenant=sighting`

| Issue | Symptom | Workaround | HSDES |
|-------|---------|------------|-------|
| [TODO] | [TODO] | [TODO] | [TODO] |

---

## 3. NVL (Nova Lake) — PRIMARY FOCUS

> NVL is the primary validation target. NVL ISH HAS data (ISH 5.8) is available in `fv-ish/has/docs/nvl/`.
> NVL uses ISH 5.8 with platform-specific deltas vs TTL; load `fv-ish/has` or Co-De Sign for authoritative values.

### 3.1 NVL ISH PCI Configuration

| Field | Value | Source |
|-------|-------|--------|
| **PCI Vendor ID** | `0x8086` (Intel) | Fixed |
 | **PCI Device ID** | `0x6E78` | HAS |
| **PCI Subsystem ID** | `[TODO]` | HAS |
| **PCI Class Code** | `0x118000` (Signal Processing Controller) | Standard |
| **BAR0** | MMIO (64-bit) — ISH register space | HAS |
| **BAR0 Size** | `[TODO: from HAS]` | HAS |
| **IRQ** | MSI/MSI-X (platform dependent) | HAS |
| **Typical BDF** | `[TODO: verify per board]` | Board |

```python
# NVL ISH PCI Device ID — NVL (Nova Lake) ISH 5.8
NVL_ISH_DEVICE_ID = 0x6E78

# Detect ISH BDF programmatically (Linux)
# lspci -d 8086:{NVL_ISH_DEVICE_ID} -n | awk '{print $1}'
```

### 3.2 NVL Key Features (Estimated from TTL Baseline)

Based on TTL ISH 5.9, NVL is expected to have similar or enhanced capabilities:

| Feature | TTL Baseline | NVL Expected | NVL Verified |
|---------|-------------|-------------|-------------|
| ISH Core | LMT 3.8/3.9 | LMT 3.9 | LMT 3.9 |
| SRAM | 640KB (20×32KB) | 640KB (20×32KB) | 640KB (20×32KB) |
| I2C | 3 controllers | 3 controllers | 3 controllers |
| I3C | 2 controllers | 1 controller | 1 controller |
| SPI | 2 controllers | 1 controller | 1 controller |
| UART | 3 controllers | 2 controllers | 2 controllers |
| GPIO | 12 pins | 8-12 pins (PCH-S=12) | up to 12 pins |
| DMA | 8 channels | 8 channels | 8 channels |
| IPC Channels | 8 | 8 channels | 8 channels |
| FW Boot | ROM→BUP→MainFW | ROM→BUP→MainFW | ROM→BUP→MainFW |

### 3.3 NVL Sensor BOM Matrix

> NVL sensor BOMs vary by board SKU. Typical sensor interfaces reflect the ISH IO controller counts below. Fill exact vendor/model per board HAS/BOM.

| Sensor Type | Vendor | Model | Interface | Address | GPIO | Notes |
|-------------|--------|-------|-----------|---------|------|-------|
| Accelerometer | [TBD per SKU] | [TBD] | I2C/I3C | [TBD] | [TBD] | Verify per BOM |
| Gyroscope | [TBD per SKU] | [TBD] | I2C/I3C | [TBD] | [TBD] | Verify per BOM |
| Magnetometer | [TBD per SKU] | [TBD] | I2C | [TBD] | [TBD] | Verify per BOM |
| ALS | [TBD per SKU] | [TBD] | I2C | [TBD] | [TBD] | Verify per BOM |
| Proximity | [TBD per SKU] | [TBD] | I2C | [TBD] | [TBD] | Verify per BOM |

**Common Sensor Vendors** (for reference — verify BOM per board):
- Accelerometer/Gyro: Bosch (BMI260, BMI323), STMicro (LSM6DSO), Invensense (ICM-42688)
- Magnetometer: AKM (AK09916), Bosch (BMM150)
- ALS/Proximity: AMS (TSL2591, APDS-9960), Vishay (VCNL4200)

### 3.4 NVL Known Issues

> TODO: Populate from NVL bring-up findings and HSDES sightings.
> Use `hsdes` skill: `hsdes search "ISH NVL" tenant=sighting`

| Issue | Symptom | Workaround | HSDES |
|-------|---------|------------|-------|
| [TODO] | [TODO] | [TODO] | [TODO] |

# NVL specific config entries in PLATFORM_CONFIG

```python
# NVL platform detection in PythonSV test
NVL_CPUID_FAMILY   = 0x6
NVL_CPUID_MODEL    = 0x00   # TODO: Fill from NVL platform spec

def is_nvl_platform(target):
    """Detect if running on NVL platform."""
    try:
        cpuid = target.uncore.cpuid.read()
        family = (cpuid >> 8) & 0xF
        model  = (cpuid >> 4) & 0xF | ((cpuid >> 16) & 0xF) << 4
        return family == NVL_CPUID_FAMILY and model == NVL_CPUID_MODEL
    except Exception:
        return False
```

---

## 4. PTL (Panther Lake)

### 4.1 PTL ISH PCI Configuration

| Field | Value |
|-------|-------|
| **PCI Device ID** | `[TODO: From PTL ISH HAS]` |
| **BAR0 Size** | `[TODO]` |
| **Typical BDF** | `[TODO]` |

### 4.2 PTL Sensor BOM

> TODO: Fill in from PTL board documentation.

| Sensor Type | Vendor | Model | I2C Addr |
|-------------|--------|-------|----------|
| Accelerometer | [TODO] | [TODO] | [TODO] |
| Gyroscope | [TODO] | [TODO] | [TODO] |
| Magnetometer | [TODO] | [TODO] | [TODO] |
| ALS | [TODO] | [TODO] | [TODO] |

### 4.3 PTL vs TTL Differences

> TODO: Document PTL-specific ISH changes vs TTL after HAS review.

---

## 5. ARL (Arrow Lake)

### 5.1 ARL ISH PCI Configuration

| Field | Value |
|-------|-------|
| **PCI Device ID** | `[TODO: From ARL ISH HAS]` |
| **BAR0 Size** | `[TODO]` |
| **Typical BDF** | `[TODO]` |

### 5.2 ARL Sensor BOM

> TODO: Fill in from ARL board documentation.

| Sensor Type | Vendor | Model | I2C Addr |
|-------------|--------|-------|----------|
| Accelerometer | [TODO] | [TODO] | [TODO] |
| Gyroscope | [TODO] | [TODO] | [TODO] |
| Magnetometer | [TODO] | [TODO] | [TODO] |
| ALS | [TODO] | [TODO] | [TODO] |

### 5.3 ARL Known Issues

> Use `hsdes` skill: `hsdes search "ISH ARL" tenant=sighting`

| Issue | HSDES | Status |
|-------|-------|--------|
| [TODO] | [TODO] | [TODO] |

---

## 6. LNL (Lunar Lake)

### 6.1 LNL ISH PCI Configuration

| Field | Value |
|-------|-------|
| **PCI Device ID** | `[TODO: From LNL ISH HAS]` |
| **BAR0 Size** | `[TODO]` |
| **Typical BDF** | `[TODO]` |

### 6.2 LNL Sensor BOM

| Sensor Type | Vendor | Model | I2C Addr |
|-------------|--------|-------|----------|
| Accelerometer | [TODO] | [TODO] | [TODO] |
| Gyroscope | [TODO] | [TODO] | [TODO] |
| Magnetometer | [TODO] | [TODO] | [TODO] |
| ALS | [TODO] | [TODO] | [TODO] |

---

## 7. MTL (Meteor Lake)

### 7.1 MTL ISH PCI Configuration

| Field | Value |
|-------|-------|
| **PCI Device ID** | `[TODO: From MTL ISH HAS]` |
| **BAR0 Size** | `[TODO]` |
| **Typical BDF** | `[TODO]` |

### 7.2 MTL Sensor BOM

| Sensor Type | Vendor | Model | I2C Addr |
|-------------|--------|-------|----------|
| Accelerometer | [TODO] | [TODO] | [TODO] |
| Gyroscope | [TODO] | [TODO] | [TODO] |
| Magnetometer | [TODO] | [TODO] | [TODO] |
| ALS | [TODO] | [TODO] | [TODO] |

---

## 8. Cross-Platform Comparison

### 8.1 Feature Matrix

| Feature | MTL | LNL | ARL | PTL | TTL | NVL |
|---------|-----|-----|-----|-----|-----|-----|
| ISH IP Version | TODO | TODO | TODO | TODO | **ISH 5.9** | **ISH 5.8** |
| Core | TODO | TODO | TODO | TODO | **LMT 3.8/3.9** | **LMT 3.9** |
| PCI Device ID | TODO | TODO | TODO | TODO | **0xE445** | **0x6E78** |
| Clock (MHz) | TODO | TODO | TODO | TODO | **200/100** | **200/100** |
| SRAM (KB) | TODO | TODO | TODO | TODO | **640** | **640** |
| I2C Controllers | TODO | TODO | TODO | TODO | **3** | **3** |
| I3C Controllers | TODO | TODO | TODO | TODO | **2** | **1** |
| SPI Controllers | TODO | TODO | TODO | TODO | **2** | **1** |
| UART Controllers | TODO | TODO | TODO | TODO | **3** | **2** |
| GPIO Pins | TODO | TODO | TODO | TODO | **12** | **8-12** |
| DMA Channels | TODO | TODO | TODO | TODO | **8** | **8** |
| IPC Channels | TODO | TODO | TODO | TODO | **8** | **8** |
| D0i3 Support | TODO | TODO | TODO | TODO | **Yes** | **Yes** |
| WDT (2-stage) | TODO | TODO | TODO | TODO | **Yes** | **Yes** |
| I3C HDR-DDR | TODO | TODO | TODO | TODO | **Yes** | **Yes (25 Mb/s HDR/DDR)** |
| SRAM Per-Bank PG | TODO | TODO | TODO | TODO | **Yes (30 bits)** | **Yes (30 bits)** |

### 8.2 IPC Channel Comparison

All platforms based on ISH 5.9 are expected to have the same 8-channel IPC architecture:

| Channel | HOST | HOSTSPARE | CSE | PMC | CNVi | ACE | ESE | AVB |
|---------|------|-----------|-----|-----|------|-----|-----|-----|
| TTL | MEM | MEM | MSG | MSG | MSG | MSG | MSG | MSG |
| NVL | MEM | MEM | MSG | MSG | MSG | MSG | MSG | MSG |

---

## 9. Platform-Specific Test Metadata

```python
# metadata/ish_project_data.py — Platform configuration registry

PLATFORM_CONFIG = {
    "ttl": {
        "pci_device_id":  0xE445,
        "pci_vendor_id":  0x8086,
        "ish_version":    "ISH 5.9 (SIP_ISH5p9)",
        "core":           "LMT 3.8/3.9 (MinuteIA)",
        "clock_mhz":      200,
        "sram_kb":         640,
        "sram_banks":      20,
        "namednode":      "pch_ish",      # Verify from PythonSV metadata
        "io_controllers": {
            "i2c":  {"count": 3, "base": 0x00000000, "stride": 0x2000, "speed": "1 Mb/s"},
            "i3c":  {"count": 2, "base": 0x04800000, "stride": 0x2000, "speed": "25 Mb/s"},
            "spi":  {"count": 2, "base": 0x08000000, "stride": 0x2000, "speed": "25 Mb/s"},
            "uart": {"count": 3, "base": 0x08100000, "stride": 0x2000, "speed": "4 Mb/s"},
            "gpio": {"count": 1, "base": 0x00100000, "pins": 12},
        },
        "ipc_channels": ["HOST", "HOSTSPARE", "CSE", "PMC", "CNVi", "ACE", "ESE", "AVB"],
        "dma_channels":   8,
        "fw_boot": {
            "bup_max_kb": 64,
            "main_fw_max_mb": 1.5,
            "method": "DMA via IMR (RS3)",
        },
        "wdt": {
            "stages": 2,
            "t1_action": "interrupt",
            "t2_action": "core_reset",
        },
        "sensors": {
            # TODO: Fill from TTL board BOM
        },
    },
    "nvl": {
        "pci_device_id":  0x6E78,
        "pci_vendor_id":  0x8086,
        "ish_version":    "ISH 5.8 (SIP_ISH5p8)",
        "core":           "LMT 3.9 (MinuteIA)",
        "clock_mhz":      200,
        "sram_kb":         640,
        "sram_banks":      20,
        "namednode":      "pch_ish",
        "io_controllers": {
            "i2c":  {"count": 3, "base": 0x00000000, "stride": 0x2000, "speed": "1 Mb/s"},
            "i3c":  {"count": 1, "base": 0x04800000, "stride": 0x2000, "speed": "25 Mb/s"},
            "spi":  {"count": 1, "base": 0x08000000, "stride": 0x2000, "speed": "25 Mb/s"},
            "uart": {"count": 2, "base": 0x08100000, "stride": 0x2000, "speed": "4 Mb/s"},
            "gpio": {"count": 1, "base": 0x00100000, "pins": 12},
        },
        "ipc_channels": ["HOST", "HOSTSPARE", "CSE", "PMC", "CNVi", "ACE", "ESE", "AVB"],
        "dma_channels":   8,
        "fw_boot": {
            "bup_max_kb": 64,
            "main_fw_max_mb": 1.5,
            "method": "DMA via IMR (RS3)",
        },
        "wdt": {
            "stages": 2,
            "t1_action": "interrupt",
            "t2_action": "core_reset",
        },
        "sensors": {
            # Populate per-board BOM
        },
    },
    "ptl": {
        # TODO: Fill after PTL HAS review
    },
    "arl": {
        # TODO: Fill after ARL HAS review
    },
    "lnl": {
        # TODO: Fill after LNL HAS review
    },
    "mtl": {
        # TODO: Fill after MTL HAS review
    },
}

def get_platform_config(platform: str) -> dict:
    """Get ISH platform configuration for the given platform name."""
    config = PLATFORM_CONFIG.get(platform.lower())
    if not config:
        raise ValueError(f"Unknown platform: {platform}. "
                         f"Supported: {list(PLATFORM_CONFIG.keys())}")
    return config

def get_ish_namednode(target, platform_name: str):
    """Get ISH namednode for the given platform."""
    config = get_platform_config(platform_name)
    node_name = config.get("namednode", "pch_ish")
    return getattr(target, node_name, None)
```

---

## 10. How to Update This Skill

When new platform data becomes available:

1. **Load the HAS**: Place new platform HAS in `.opencode/skill/fv-ish/has/docs/[platform]/`
2. **Search HAS**: Use `has_search.py --platform [platform] --topic pci` to extract Device ID, BDF, BAR info
3. **Update platform section**: Fill in the `[TODO]` placeholders in this skill
4. **Update BOM**: Get sensor BOM from board documentation or NGA test setup info
5. **Update test metadata**: Update `PLATFORM_CONFIG` dict above
6. **Update cross-platform table**: Add new platform column to Section 8
7. **Run smoke tests**: Execute basic enumeration tests on the new platform to validate

---

## Cross-References

- HAS document access: load `fv-ish/has`
- Register maps: load `fv-ish/registers`
- Debug/triage: load `fv-ish/debug`
- Power management: load `fv-ish/power`
- DMA architecture: load `fv-ish/dma`
- Sensor interfaces: load `fv-ish/sensors`
- Driver/firmware: load `fv-ish/driver`
