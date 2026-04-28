---
name: fv-thc/platform
description: Per-platform THC data (MTL/LNL/PTL/NVL/ARL/RZL/TTL), BOM device matrix, BIOS prerequisites, PMC addresses, registry overrides
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Platform-Specific Data

Per-platform Device IDs, BDFs, reset GPIOs, BOM device configurations, and BIOS prerequisites.

## Die Type Mapping

| Die Type | Target Namednode | Platforms |
|----------|-----------------|-----------|
| `SOC_SOUTH` | `socket0.soc.south` | MTL-P |
| `PCH` | `pch0` | MTL-S |
| `SOC` | `socket0.soc` | LNL, PTL |
| `PCD` | `socket0.pcd` | NVL |

### SOC_SOUTH Device Name List (from test scripts)
The test framework matches these device name strings for platform detection:
- `mtps` → MTL-S (PCH die)
- `lnl_cltap`, `lnlm` → Lunar Lake
- `ptl_cltap`, `pcdp`, `pcdh` → Panther Lake
- `nvlh`, `nvlhx`, `nvl` → Nova Lake

## Project Detection (ThcBase)
Auto-detects by trying namednode attributes:
1. `pch0.target_info['device_name']`
2. `socket0.target_info['device_name']`
3. `socket0.soc.target_info['sku']`
4. `socket0.pcd.target_info['sku']`

Match patterns: MTP=`['mtps']`, LNL=`['lnl_cltap','lnlm']`, PTL=`['ptl_cltap','pcdp','pcdh']`, NVL=`['nvlh','nvlhx','nvl']`

## Meteor Lake (MTL) — Gen3.0

### MTL-S (PCH die)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0x7F58`–`0x7F5B` | Same |
| BDF | Bus=128, Dev=16, Fun=0 | Bus=128, Dev=16, Fun=1 |
| Reset GPIO | `gpp_e_19` | `gpp_d_22` |

### MTL-P (SOC_SOUTH die)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0x7E48`–`0x7E4B` | Same |
| BDF | Bus=0, Dev=16, Fun=0 | Bus=0, Dev=16, Fun=1 |
| Reset GPIO | `xxgpp_e_6` | `xxgpp_f_16` |

## Lunar Lake (LNL) — Gen4.0

### LNL-M (SOC die)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0xA848`–`0xA84B` | Same |
| BDF | Bus=0, Dev=16, Fun=0 | Bus=0, Dev=16, Fun=1 |
| Reset GPIO | `xxgpp_e_16` | `xxgpp_f_16` |

- LNL-P: Architecturally has THC but never produced
- LNL-S: Does NOT have THC
- **I2C MPS workaround required** (`I2C_MPS_WA = 4096`)

## Panther Lake (PTL) — Gen4.1

> **PTL SKU/Die Clarification:**
> - **PTL-U** and **PTL-P** (a.k.a. **PTL-H12Xe**) both use the **PCD-P** die → **same Device IDs** (`0xE448`–`0xE44B`)
> - **PTL-H** (a.k.a. **PTL-H4Xe**) uses the **PCD-H** die → **own Device IDs** (`0xE348`–`0xE34B`)
> - **PTL-Px** was **NOT POR** and was never productized — do not test or reference

### PTL-PCD-P — PTL-U & PTL-P (PTL-H12Xe)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0xE448`–`0xE44B` | Same |
| BDF | Bus=0, Dev=16, Fun=0 | Bus=0, Dev=16, Fun=1 |
| Reset GPIO | `xxgpp_e_16` | `xxgpp_f_16` |

### PTL-PCD-H — PTL-H (PTL-H4Xe)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0xE348`–`0xE34B` | Same |
| BDF | Bus=0, Dev=16, Fun=0 | Bus=0, Dev=16, Fun=1 |
| Reset GPIO | `xxgpp_e_16` | `xxgpp_f_16` |

- **Telemetry support**: Yes
- **I2C MPS workaround required** (same as LNL)
- **RVP Connectors**: THC0=J6B2, THC1=J5B2
- **THC1 requires THC0 enabled**

### PTL BOM Configs
| BOM | Protocol | Rework | Key Settings |
|-----|----------|--------|-------------|
| BOM36 (ELAN SPI) | HIDSPI | THC1: XF-16 | Body=0x1100, Header=0x1000, Output=0x2000. DSYNC on ONE port only |
| BOM37 (ELAN I2C) | HIDI2C | THC0: XF-14, THC1: XF-15 | SM: Hcnt=0x267/Lcnt=0x271; FM: 0x92/0x9C; FMP: 0x34/0x3E |
| THAT-131T | HIDI2C | None | THC1 only (J9H1/J9B2). FM 400K only. No DSYNC |

## Nova Lake (NVL) — Gen4.2

### NVL Product SKUs
| SKU | Segment | Die | THC |
|-----|---------|-----|-----|
| NVL-U/P/H/HX | Mobile | PCD-H | 2 ports (THC0+THC1) |
| NVL-S/Sk | Desktop | PCD-S+PCH-S | THC fuse-disabled, **ZBB'ed** |

### NVL-PCD-H (PCD die — Mobile)
| Parameter | THC0 | THC1 |
|-----------|------|------|
| Device IDs | `0xD348`–`0xD34B` | Same |
| BDF | Bus=0, Dev=16, Fun=0 | **Bus=0, Dev=8, Fun=0** ⚠️ |
| Reset GPIO | `xxgpp_e_16` | `xxgpp_f_16` |

**⚠️ CRITICAL**: THC1 BDF changed to `B:0 D:8 F:0` (was D:16 F:1 on all prior platforms).

- **I2C MPS workaround NOT needed** (fixed in NVL)
- **Signal renaming** (bus-agnostic): `thc0_spi_`, `thc1_i2c_`, `thc0_rst_b`, `thc0_int_b`
- **Telemetry**: Yes (counters: `tx_frm_cnt`, `txdma_pkt_cnt`, `devint_cnt`, etc.)
- **Linux POR**: Ubuntu 24.04.3
- **QuickSPI Non-POR from PTL+**, **QuickI2C Non-POR from NVL+** (HSD#16028137599)

### CCB 16028137599: Windows QuickI2C Driver Drop Decision

> **Status**: iVE (now CVE) **rejected removal for NVL** (Sep 2025). Will evaluate Linux/Chrome transition for future programs.

**Background**: CCB proposed dropping the Windows THC QuickI2C driver from NVL and all future platforms. CVE's entire post-silicon validation infrastructure (framework, test scripts, coverage plans) relies on Windows drivers as the primary vehicle.

**Impact if dropped**:
- PM cycling (S0ix, Sx, Reset) with THC enabled: **ZERO Linux/Chrome coverage** — only 15 manual cycles vs 50 automated Windows cycles (3.3x reduction)
- IP PM states (D3, D0i2): synthetic scripts only, no Linux/Chrome equivalent
- THC telemetry: no Linux/Chrome coverage
- All NVL MBL PCD-H products affected (NVL U/H/P/Ax/Am) + RZL MBL
- Additional risk: TSMC→Intel process change (eSPI bug discovered)

**Key stakeholders**: Bee Koon Lee (risk assessment), Norazirah Aqilah Azlan/Zirah (iVE lead), Anton Cheng (VE gaps), William Chin (gap analysis documentation), Fred Zhou (THC IP COE)

**Reference docs**: `fv-thc/docs/nvl_thc_windows_driver_drop_briefing.md`, `fv-thc/docs/nvl_thc_windows_driver_drop_gap_analysis.md`, `fv-thc/docs/nvl_thc_validation_coverage_matrix.md`

### NVL RVP Connectors
| Port | Panel | Touchpad |
|------|-------|----------|
| THC0 | J2B1 | — |
| THC1 | J2A1 | J2J3 |

### NVL BOM Configs
| BOM | Protocol | Notes |
|-----|----------|-------|
| BOM52 (WACOM SPI) | HIDSPI | SPI 17MHz, Write=0x02, Read=0x0B |
| BOM52 (WACOM I2C) | HIDI2C | QuickI2C Non-POR. See BOM52 I2C detail below |
| BOM36 (ELAN SPI) | HIDSPI | Body=0x1100, Header=0x1000, Output=0x2000 |
| BOM37 (ELAN I2C) | HIDI2C | FMP BIOS knobs changed post PTL-H12Xe Pre-QS |
| THAT-131T | HIDI2C | THC1 only (J2J3). FM 400K only. No DSYNC |

### BOM52 I2C Detailed Configuration (NVL)

> **Source**: Confluence wiki page 4501129290 ("BOM52 I2C Touch Panel")

| Parameter | Value | Notes |
|-----------|-------|-------|
| **THC0 Connector** | J2B1 | Touch panel port |
| **THC1 Connector** | J2A1 | Touch panel port (THC1 BDF: B:0 D:8 F:0 on NVL) |
| **I2C Device Address** | `0x0A` | WACOM touchscreen slave address |
| **HID Descriptor Address** | `0x01` | Standard HIDI2C descriptor register |
| **Speed Modes** | SM / FM / FMP | All three validated; see hex values below |

#### BOM52 I2C Speed Mode Hex Values

| Mode | Connection Speed Hex | HCNT | LCNT | Frequency |
|------|---------------------|------|------|-----------|
| **Standard (SM)** | `0x186A0` (100,000) | `0x267` (615) | `0x271` (625) | 100 KHz |
| **Fast (FM)** | `0x61A80` (400,000) | `0x92` (146) | `0x9C` (156) | 400 KHz |
| **Fast Mode Plus (FMP)** | `0xF4240` (1,000,000) | `0x34` (52) | `0x3E` (62) | 1 MHz |

> **Note**: These HCNT/LCNT values match the **Linux kernel** defaults (not Windows). Windows uses significantly different FS_HCNT/LCNT defaults (500/588). The connection speed hex values are the ACPI `connection_speed` field in Hz. BIOS/ACPI programs these via the ICRS method.

### NVL BIOS Prerequisites
1. **Disable conflicting IPs**: I2C4, I2C5, SPI, I3C, ISH must all be disabled in BIOS setup to avoid GPIO/pad conflicts with THC ports. These IPs share GPIO pads with THC SPI/I2C signals — leaving them enabled causes pin muxing conflicts and THC communication failures.
2. LTR = `0xFFFFFFFF` (infinite LTR on boot — prevents premature S0ix entry before driver configures proper LTR values)
3. IFWI ≥ ww50.1.01
4. THC1 requires THC0 enabled

### PMC Address Constants
| Constant | Value |
|----------|-------|
| `PMC_SSRAM_BASE_ADDR` | `0xFE010000` |
| `PMC_PWRM_BASE_ADDR` | `0xFF113000` |
| `PMC_PWRM_BASE_ADDR_EXTENDED` | `0xFF114000` |

## Arrow Lake (ARL) — Gen3.0
- Same THC IP as MTL (user-confirmed)
- ARL Device IDs added to Linux kernel 6.18
- Desktop platform — verify THC port availability

## Alder Lake / Raptor Lake (ADL/RPL) — Gen2.x (Windows Only)

- **A1 stepping detection**: Registry key `ADLA1Platf=1` enables ADL A1 stepping detection in the Windows driver. When set, the driver applies A1-specific register overlay workarounds (e.g., ICRRD aliased to DMARD@0x14, WR_OPCODE shifted to 0x18).
- **Filter levels**: ADL/RPL Windows drivers use three filter levels: `WakeLevel` + `GpuLevel` + `HidLevel`. Starting from MTL+, `WakeLevel` is removed (only `GpuLevel` + `HidLevel` remain).

## Razor Lake (RZL) — Gen4.2
- Reuses NVL-PCD-H die (THC IP identical)
- **Device IDs** (Co-De Sign verified from RZL PCD register maps):
  - THC0: DID1=`0x6C48`, DID2=`0x6C49`
  - THC1: DID1=`0x6C4A`, DID2=`0x6C4B`
  - BDF: THC0 Bus=16 Dev=0 Fun=0, THC1 Bus=8 Dev=0 Fun=0 (same as NVL)
- Not yet in `thc_project_data.py` or upstream Linux kernel (as of v6.20)
- GPIO docs: `docs.intel.com/.../RZL/RZLPCDH/HAS/Chap18_RZL_GPIO/`

## Titan Lake (TTL) — Gen4.2
- THC IP "1.0 (no change)" from NVL per HAS title page
- **Device IDs** (Co-De Sign verified from TTL platform firmware arch spec):
  - THC0: DID1=`0x9334`, DID2=`0x9335`
  - THC1: DID1=`0x9339`, DID2=`0x933A`
  - BDF: THC0 Bus=16 Dev=0 Fun=0, THC1 Bus=8 Dev=0 Fun=0 (same as NVL)
  - **WARNING**: TTL breaks the standard `x8/x9/xA/xB` DID pattern used by all other platforms!
- Not yet in `thc_project_data.py` or upstream Linux kernel (as of v6.20)

## Per-Platform I2C Speed Mode Summary

| Platform | Validated Speed Modes | Notes |
|----------|----------------------|-------|
| LNL | SM (100K), FM (400K), FMP (1M) | First QuickI2C platform; all three modes validated in kernel |
| PTL | SM (100K), FM (400K), FMP (1M) | BOM37 provides explicit SM/FM/FMP HCNT/LCNT ACPI values |
| NVL | SM (100K), FM (400K), FMP (1M) | BOM52 I2C validates all three modes (see hex values above). THAT-131T: FM 400K only |
| WCL | FM (400K), FMP (1M) | ⚠️ FMP (1MHz) has known instability — see HSDES `16027559981`. Lower to SM/FM recommended |
| ARL | FM (400K) | Desktop — limited I2C touch use cases |
| RZL | FM (400K) | Reuses NVL die — same speed support expected |
| TTL | FM (400K) | Reuses NVL IP — same speed support expected |

### I2C Speed Mode Hex Values (ACPI connection_speed)

| Mode | Hex Value | Decimal (Hz) | HCNT | LCNT | Notes |
|------|-----------|-------------|------|------|-------|
| **Standard (SM)** | `0x186A0` | 100,000 | `0x267` (615) | `0x271` (625) | Linux kernel defaults |
| **Fast (FM)** | `0x61A80` | 400,000 | `0x92` (146) | `0x9C` (156) | Linux kernel defaults |
| **Fast Mode Plus (FMP)** | `0xF4240` | 1,000,000 | `0x34` (52) | `0x3E` (62) | Linux kernel defaults |

> **Source**: BOM52 I2C Touch Panel wiki (page 4501129290) + Linux kernel `pci-quicki2c.c` defaults.
> **Key contrast**: PTL is the only platform with explicit ACPI HCNT/LCNT values for all three speed modes (SM/FM/FMP). NVL BOM52 I2C also validates all three modes with the hex values above. THAT-131T validates FM 400K only. High-speed mode (3.4 MHz) is architecturally supported by the Synopsys sub-IP but NOT validated on any current platform.
> **Windows vs Linux**: Windows uses significantly different FS timing defaults (HCNT=500/LCNT=588 vs Linux 146/156). See `fv-thc/hidi2c` for cross-platform timing comparison.

## Linux PCI Device IDs

### QuickSPI
| Platform | DID 1 | DID 2 | Max Packet |
|----------|-------|-------|-----------|
| MTL | 0x7E49 | 0x7E4B | 128 (2048B) |
| ARL-H | 0x7749 | 0x774B | 128 (2048B) |
| ARL-U | 0x7F49 | 0x7F4B | 128 (2048B) |

⚠️ ARL-U DIDs (0x7F49/0x7F4B) are NOT present in upstream Linux kernel source code — only 0x7749/0x774B (ARL-H) are confirmed in driver source. Treat ARL-U DIDs as **unverified/preliminary** until confirmed in kernel or INF.

⚠️ NVL / RZL / TTL have NO upstream Linux kernel driver support as of kernel 6.20. NVL DIDs (`0xD348`–`0xD34B`) verified via Co-De Sign (novalake platform firmware arch spec). RZL DIDs (`0x6C48`–`0x6C4B`) verified via Co-De Sign (razorlake PCD). TTL DIDs (`0x9334`/`0x9335`/`0x9339`/`0x933A`) verified via Co-De Sign (titanlake platform firmware arch spec) — **TTL breaks the standard x8/x9/xA/xB DID pattern**.

### QuickI2C
| Platform | DID 1 | DID 2 | Max Packet |
|----------|-------|-------|-----------|
| LNL | 0xA848 | 0xA84A | 256 (4096B) |
| PTL-H | 0xE348 | 0xE34A | 256 (4096B) |
| PTL-U | 0xE448 | 0xE44A | 256 (4096B) |
| WCL | 0x4D48 | 0x4D4A | 256 (4096B) |

DID pattern: even (x8/xA) = I2C, odd (x9/xB) = SPI. Two DIDs per platform = THC0/THC1.

### Windows-Only PCI Device IDs (Phase 6)

> **Source**: Windows HIDSPI driver v4.0.0.9000, HIDI2C driver v3.0.0.9000

These Device IDs appear in the Windows INF files but are **NOT** in the Linux kernel driver:

**HIDSPI (Windows INF)**:
| Platform | DID 1 | DID 2 | Notes |
|----------|-------|-------|-------|
| RPL-S | 0x7A50 | 0x7A51 | Raptor Lake-S |
| RPL-H | 0x7A58 | 0x7A59 | Raptor Lake-H |
| ADL-P | 0x51D0 | 0x51D1 | Alder Lake-P |
| ADL-N | 0x54D0 | 0x54D1 | Alder Lake-N |
| MTL-P | 0x7E49 | 0x7E4B | Also in Linux |
| MTL-S | 0x7F59 | 0x7F5B | MTL-S only in Windows |

**HIDI2C (Windows INF)**:
| Platform | DID 1 | DID 2 | Notes |
|----------|-------|-------|-------|
| ADL-LP | 0x7A50 | 0x7A51 | Same DIDs as RPL-S HIDSPI — INF determines protocol |

> **⚠️ DID overlap**: ADL-LP HIDI2C uses the same 7A50/7A51 DIDs as RPL-S HIDSPI. The Windows INF file determines which driver (HIDSPI vs HIDI2C) binds to these devices. Linux does not have this ambiguity because ADL/RPL Device IDs are not present in the Linux driver.

### Windows INF Registry Settings (Phase 6)

The Windows driver INF files configure these registry keys under `HKLM\SYSTEM\CurrentControlSet\Enum\PCI\<DeviceID>\Device Parameters\`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `UseWriteInterrupts` | DWORD | 0 | Disable write interrupts (polling WA — HSD 14016760177) |
| `HeartbeatEnabled` | DWORD | 1 | Enable heartbeat health check |
| `DozeTimerMs` | DWORD | 1000 | Doze timer in milliseconds |
| `IdleTimerMs` | DWORD | 1000 | Idle timer in milliseconds |
| `ActiveLtrUs` | DWORD | 5 | Active LTR in microseconds |
| `LpLtrUs` | DWORD | 500 | Low-power LTR in microseconds |

## BOM Device Matrix

### HIDSPI Devices
| BOM | Vendor | Input Body | Input Head | Output | VID:PID |
|-----|--------|-----------|-----------|--------|---------|
| BOM6 | WACOM | `0x1000` | `0x0` | `0x4` | — |
| BOM22 | WACOM | `0x1000` | `0x0` | `0x1000` | — |
| BOM52 | WACOM | `0x1000` | `0x0` | `0x1000` | `056A:541C` |
| BOM36 | ELAN | `0x1100` | `0x1000` | `0x2000` | — |
| BOM37 | ELAN | `0x1100` | `0x1000` | `0x2000` | — |

> **WACOM_REPORT_DESCRIPTOR_MAX_PACKET_SIZE** = 256 (translates to 4096 bytes max report descriptor). Used when reading HID report descriptors from WACOM devices.

### BOM Device Matrix - Additional Entries
| Device | Protocol | Notes |
|--------|----------|-------|
| WACOM W9025 | HIDSPI | SPI device, common on PTL RVP (typical SPI up to 17MHz) |
| ELAN eKTH6915 | HIDI2C | I2C device, common on LNL/PTL (supports standard/fast modes) |
| ALPS T2C | HIDSPI | SPI trackpad reference design |
| Goodix GT7986 | HIDI2C | I2C touchscreen/trackpad used on newer platforms |

### HIDI2C Devices
| BOM | Vendor/Type | I2C Addr | Desc Addr |
|-----|------------|---------|-----------|
| BOM5/22/52 | WACOM (touchscreen) | `0x0A` | `0x01` |
| BOM36/37 | ELAN (touchscreen) | `0x16` | `0x01` |
| BOMTHAT | THAT trackpad (VID=`0x911`, PID=`0x5288`, VerID=`0x1`) | `0x2C` | `0x20` |
| BOMALPS | ALPS (trackpad) | `0x2C` | `0x20` |
| BOMSENSEL | Sensel (trackpad) | `0x2C` | `0x01` |

## Windows Registry Overrides
Path: `HKLM\SYSTEM\CurrentControlSet\Services\IntelQuickSPI\Parameters\`

> **Note**: The production HIDSPI service name is `IntelQuickSPI`. `IntelTHCBase` is the test filter driver service name only — do not confuse with the production driver service.

| Key | Values | Purpose |
|-----|--------|---------|
| `SPI_Frequency_Override` | 3-A (dividers) | Override SPI clock |
| `IO_Mode_Override` | 0=Single, 1=Dual, 2=Quad | Override SPI IO mode |
| `DefaultSpiReadMaxPacketSize` | 64–2048 | Override SPI read MPS |
| `BusSpeed` | bps (e.g., 400000) | Override I2C speed |
| `Lcnt` / `Hcnt` | I2C SCL counts | Override I2C timing |
| `EnableFWFlashWABOM36` | 0/1 | Enable FW flash workaround for BOM36 Elan devices |

## Interface Signal Lists (from HAS)

### IOSF Primary Interface
- Chassis-compliant single root space
- Port 0, Address Width 63:0, Data Width 63:0, Frequency 125 MHz
- Detailed signals documented in `assets/SIP_THC_4x_HAS.xlsx`

### SPI Clock and Device Ranges
- SPI base clock: 125 MHz (NOT 128 MHz)
- Clock formula: SPI_CLK = 125MHz / divider (high freq); SPI_CLK = 125MHz / (divider × 8) (low freq, SPI_LOW_FREQ_EN=1)
- With half-divider (Gen4.1+): SPI_CLK = 125MHz / (2 * (divider + 0.5))
- Typical device-supported ranges: 1-17 MHz (WACOM), 1-12 MHz (ELAN)
- Maximum THC SPI clock depends on board SI (signal integrity) — typically 20-25 MHz max
- **SPI_LOW_FREQ_EN threshold**: Windows driver = 17MHz; Linux driver = 17.857MHz (cross-platform difference — may cause different divider selection near threshold)

### HIDSPI Version Constant (Naming Confusion)
- `HIDSPI_VERSION_2_0 = 0x0300` — **naming is misleading**: the constant is named "VERSION_2_0" but the `bcdVersion` value is `0x0300` (which encodes version 3.0 in BCD). This is a known source of confusion in driver source code. Always use the hex value `0x0300` when comparing.

### IOSF Sideband Interface
- Chassis-compliant sideband
- EP Name: 'thc', Payload Bus Width: 8 bits
- Port Domain: 8b (pre-PTL) / 16b (PTL+ per HSDES 15010734105)
- Detailed signals documented in `assets/SIP_THC_4x_HAS.xlsx`

### PM Interface
- Chassis PGCB/CDC spec based
- PGCB clock: ~5MHz (1-100MHz range)

### DFT Signal List
- Chassis DFT compliant
- Detailed in Integration Guide

### DPHY Signal List (TSI Only — N/A for SPI/I2C)
| Signal | Direction | Description |
|--------|-----------|-------------|
| THC_dphy_reset_b | Output | Async reset to DPHY |
| Dphy_ready | Input | Common lane PHY ready |

### Clock Lane PPI (per Port, TSI Only)
| Signal | Direction | Description |
|--------|-----------|-------------|
| dphy_THC_cl_RxClkActiveHS | Input | HS clock active |
| RxByteClkHS | Input | Byte clock |
| RxDDRClkHS | Input | DDR clock |
| Stopstate | Input | Lane stop state |
| Enable | Output | Lane enable |
| RxClkEsc | Input | Escape mode clock |
| RxUlpsClkNot | Input | ULPS clock (active low) |
| UlpsActiveNot | Input | ULPS active (active low) |
| ErrControl | Input | Clock lane error |

### Data Lane PPI (per Port, TSI Only)
**HS Mode:**
| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| RxDataHS | 8 bits | Input | HS receive data |
| RxValidHS | 1 | Input | HS data valid |
| RxActiveHS | 1 | Input | HS reception active |
| RxSyncHS | 1 | Input | HS sync pulse |

**Escape Mode TX:**
TxClkEsc, TxRequestEsc, TxLpdtEsc, TxUlpsExit, TxUlpsEsc, TxTriggerEsc[3:0], TxDataEsc[7:0], TxValidEsc, TxReadyEsc

**Escape Mode RX:**
RxClkEsc, RxLpdtEsc, RxUlpsEsc, RxTriggerEsc[3:0], RxDataEsc[7:0], RxValidEsc

**Control:**
TurnRequest, Direction, TurnDisable, ForceRxmode, ForceTxStopmode, Stopstate, Enable

### Platform Signal / Pin List (common)

- THC_SPI_CLK — SPI clock output
- THC_SPI_MOSI — SPI MOSI
- THC_SPI_MISO — SPI MISO
- THC_SPI_CS# — SPI chip select (per port)
- THC_SPI_IO2, THC_SPI_IO3 — SPI IO2/IO3 for dual/quad modes
- THC_I2C_SCL — I2C clock
- THC_I2C_SDA — I2C data
- THC_INT# — Interrupt from THC to host (GPIO/ITSS routed)
- THC_RESET# — Device reset (optional GPIO on some platforms)

## Area and Gate Count (from HAS)

| Metric | Value |
|--------|-------|
| Gate Count | 300K per THC instance (with two ports) |
| RF (Register File) | 2 x 8KB (TSI DPHY Only) |

## IOSF SB Messages

### PTL+ Requirement
PTL+ requires 16-bit SB port ID (HSDES 15010734105). Earlier platforms use 8-bit.

### Key SB Message Types
| Message | Opcode | Direction | Target | Description |
|---------|--------|-----------|--------|-------------|
| Assert INTA-D | 0x80-0x87 | THC→ITSS | ITSS | Legacy interrupt assertion |
| Deassert INTA-D | 0x80-0x87 | THC→ITSS | ITSS | Legacy interrupt deassertion |
| DoSERR | 0x88 | THC→ITSS | ITSS | System error |
| Cpl/CplD | Various | PMC→THC | THC | Fuse/strap pull completion |
| MRd/MWr | Various | Various | THC | Register access |
| CfgRd/CfgWr | Various | Various | THC | Config space access |
| FORCEPWRPOK | - | PMC→THC | THC | Force power OK |
| LTR | - | THC→PMC | PMC | Latency tolerance report |
| SetIDValue | - | PMC→THC | THC | Set PCI ID values |
| ResetPrep | - | PMC→THC | THC | Reset preparation |
| ResetAck | - | THC→PMC | PMC | Reset acknowledgment |

### SAI Policy
- INDEX41 controls SAI checking for MRd/MWr/CfgRd/CfgWr
- Allowed SAIs: ESE_SAI, HOSTIA_POSTBOOT_SAI, HOSTIA_BOOT_SAI, HOSTIA_SMM_SAI, DFX_INTEL_MANUFACTURING_SAI, DFX_INTEL_PRODUCTION_SAI, DFX_THIRDPARTY_SAI, PM_IOSS_SAI, HOSTIA_UCODE_SAI, HOSTIA_SUNPASS_SAI, CSE_INTEL_SAI
- CRRd/CRWr: CSE_INTEL_SAI + subset only

## PCI/PCIe Configuration Summary

### BAR Configuration
| BAR | Type | Range | Target | Status |
|-----|------|-------|--------|--------|
| BAR0 | Type 0 | 32KB | Channel 0 | Active |
| BAR1-5 | - | - | - | Unused |
| ROMBAR | - | - | - | Unused |

### PCI Capabilities
| Capability | Supported |
|-----------|-----------|
| Memory Enable | Yes |
| IO Enable | No |
| MSI | Yes |
| MSI-X | No |
| LTR | Yes |
| D3-Hot | Yes |
| D3-Cold | No |
| PME | No |
| WAKE | No |
| PCI SERR | Yes |
| INTx | Yes |
| MBAR | Yes (64-bit), Min 32KB |
| PCIeCAP | If thc_pci_or_pciemode=1 (MTL-S+) |
| AER | No |
| FLR | No |
| PTM | No |

## BIOS Programming Requirements (BWG)

> **Source**: `Chap69_BIOS_WG_THC.docx` (Rev 0.5, March 2017; last modified 2024-09-24 by Kevin Zhenyu Zhu). TGP-era document with later MTL+ additions.
> **Full reference**: `fv-thc/docs/thc_bwg_extraction.md`

### BIOS Policy Knobs (Setup Options)

| Knob | Description | Notes |
|------|-------------|-------|
| Touch Port Config Options | Port mapping: 2-port dual driver, 2-port single driver, 1-port, disabled | See Port Configuration Scenarios below |
| THC0/THC1 Enable | Per-port enable/disable | Controls whether individual THC ports are exposed to OS (BIOS may keep function disabled)
| Port Type Selection | SPI / I2C / None | Selects protocol for each port based on BOM/board routing
| SPI Clock Frequency | SPI clock divider or frequency selection | Exposed as SPI Frequency (dividers) and/or direct MHz value
| I2C Speed Mode | Standard/Fast/Fast+/High | Maps to I2C timing (Lcnt/Hcnt) settings
| Touch Panel Connection Type | Panel/Trackpad mapping | Determines HID descriptors and routing
| Wake-on-Touch (WoT) | Enable/Disable | Platform policy for waking system from Sx on touch events
| LTR Values | Active/LP LTR value and scale | ACT_LTR_VAL, ACT_LTR_SCALE, LP_LTR_VAL, LP_LTR_SCALE, ACTIVE_LTR_EN, LP_LTR_EN (see THC_M_PRT_LTR_CTRL_REG for enable/request fields)
| D0i3 Enable/Disable | TGP POR = not supported; if needed, set NXTP bit | Future use — verify per platform |
| Function Disable | Per-THC function disable | Sets THC_CFG_UR_STS_CTL.FD = 1 (requires power cycle to recover) |
| PM Enable/Disable | Power management enable | Controls clock/power gating behavior |
| Min Device Reset Time | Minimum DEVRST assertion time | BIOS→driver communication only (no physical register) |
| SPI Frequency | SPI clock divider | Via TCWF/TCRF fields (see SPI Clock and Device Ranges) |
| SPI IO Mode | Single/Dual/Quad | Via TCWF/TCRF fields |
| D0i2 Entry Timer | D0I2_ENTRY_TIMER default=100ms | Tune per SoC (e.g., TGL-LP=10us) |
| D0i2 RXDMA Policy | D0I2_RXDMA_POLICY | Controls D0i2 interaction with RXDMA |
| LTR Enable | ACTIVE_LTR_EN / LP_LTR_EN | Master LTR enable bits (THC_M_PRT_LTR_CTRL_REG: ACTIVE_LTR_EN, LP_LTR_EN, ACTIVE_LTR_REQ, LP_LTR_REQ) |
| MTL+ DID bit[16] | RWOnce: 0=Intel PTSP, 1=HIDSPI | MTL+ only — selects device type |
| BIOS Dual-DID Menu | HIDSPI vs HIDI2C DID selection | BIOS menu selects which Device ID to expose per THC port. For platforms with both SPI and I2C support (LNL+), BIOS programs the appropriate DID based on PORT_TYPE selection. **QuickSPI SwAS**: BIOS switches between HIDSPI DID (odd: x9/xB) and HIDI2C DID (even: x8/xA) based on port config. |

### Port Configuration Scenarios

| Scenario | GPIO Routing | THC0 Config | THC1 Config |
|----------|-------------|-------------|-------------|
| **2 ports, dual driver** | SPI1 GPIO→THC0 port0, 2nd SPI GPIO→THC1 port0 | Clear PORT_SUPPORTED for port1 | Clear PORT_SUPPORTED for port1 |
| **2 ports, single driver** (ZBBed) | SPI1 GPIO→THC0 port0, 2nd SPI GPIO→THC0 port1 | Both ports active | Function Disable THC1 |
| **1 port only** | SPI1 GPIO→THC0 port0 | Clear PORT_SUPPORTED for port1 | Function Disable THC1 |
| **Both disabled** | SPI1 GPIO→SPI Touch port (not THC) | Function Disable THC0 | Function Disable THC1 |

### PCI Init & Enumeration Checklist (BIOS Boot Flow)

1. **DEVVENDID check** — Read and validate Device/Vendor ID register
2. **BAR assignment** — Assign BAR0 (32KB MMIO range, 64-bit addressing)
3. **SSID/SSVID/Class codes** — Assign Subsystem ID, Subsystem Vendor ID, Base Class, Sub-Class
4. **MSI configuration** — Program MSI capability registers to enable MSI
5. **Legacy interrupt** — Configure THC_CFG_INT.IPIN
6. **MSFT G5 panel bit** — Set bit 31 of THC MMIO offset `0x1128` to `1` (required for Microsoft G5 touch panels)
7. **THC_CFG_PCE** — Enable HAE (bit 5) and D3HE (bit 2) for power gating
8. **SAI policy** — Configure SAI access control via IOSF SB regs P39h:20h–3Ch (if non-default required)
9. **Clock gating** — Set all clock enable bits in IOSF SB private regs
10. **Power gating** — Set appropriate bits in THC_CFG_PCE
11. **LTR programming** — Set ACT_LTR_VAL, ACT_LTR_SCALE, LP_LTR_VAL, LP_LTR_SCALE, ACTIVE_LTR_EN / LP_LTR_EN (use THC_M_PRT_LTR_CTRL_REG fields ACTIVE_LTR_EN, LP_LTR_EN, ACTIVE_LTR_REQ, LP_LTR_REQ)
12. **BIOS_LOCK_EN** — Set THC_BIOS_LOCK_EN to lock BIOS-configured registers before OS handoff

## Platform Init Checklist

1. BIOS detects THC PCI device during enumeration
2. BIOS reads fuses/straps for THC configuration
3. BIOS programs PORT_TYPE based on platform BOM
4. BIOS enables PCI command register (Memory Space, Bus Master)
5. BIOS assigns BAR0 from MMIO space
6. BIOS programs SAI/CDC security registers
7. OS driver loads, takes over from BIOS configuration
8. Driver performs protocol-specific init (SPI config or I2C Synopsys sub-IP init)
9. Driver sends RESET to device
10. Driver configures DMA and interrupts
11. Driver retrieves HID descriptors
12. Driver registers with HID subsystem

### Function Disable Flow (BWG)

1. Enable all clock gating controls (CDC regs: CCC0→CCC3)
2. Set HAE bit in THC_CFG_PCE to `1`
3. Set function into D3 state (PMCSR[1:0] = `11`)
4. Set `THC_CFG_UR_STS_CTL.FD = 1`

> **⚠️ Warning**: No SW or device wake supported after Function Disable. PSF programmed by BIOS to UR all cycles. Requires power cycle to recover.

### GPIO IOSTANDBY Requirement

BIOS must program THC-SPI GPIOs to **retain last driven values on Vnn removal** (IOSTANDBY configuration). BIOS must also route native functions to the correct THC/SPI controller based on platform configuration.

### ICC SSC Dependency

SSC (Spread Spectrum Clocking) on the SPI clock can be disabled via ICC PLL SSC disable bit. This is an open item from the BWG — BIOS may not have direct access to this setting on all platforms.

## Platform-Specific Initialization Sequences

### Generic THC Boot-Time Init Flow (BIOS → Driver)

The THC initialization proceeds in three phases: BIOS/Pre-OS hardware setup, OS driver probe, and protocol-specific device configuration. Each phase must complete fully before the next begins.

#### Phase 1: BIOS/Pre-OS (from BWG — Chap69_BIOS_WG_THC.docx)

BIOS performs the following ordered initialization before handing off to the OS:

| Step | Action | Register/Mechanism | Details |
|------|--------|--------------------|---------|
| 1 | **PCH strap/fuse check** | `THC_FUSES` (SB `0x80`), `THC_SOFTSTRAPS` (SB `0x84`) | Read `THC_RESERVED_FUSE` (8-bit, addr `0x3980`). Check `PowerGateEnable`, `ClockGateEnable`, `PORT_TYPE` (00=SPI, 01=I2C) straps. |
| 2 | **PCI enumeration — DEVVENDID check** | PCI Config `0x00` (`THC_CFG_DID_VID`) | Verify THC device present: Vendor ID = `0x8086`. Device IDs are platform-specific (see per-platform tables above). |
| 3 | **BAR0 assignment** | PCI Config `0x10`/`0x14` (`THC_CFG_BAR0_LOW/HI`) | Assign 32KB MMIO range, 64-bit Type 0 addressing. BAR0 maps all THC registers: common (`+0x0000`), port0 (`+0x1000`), port1 (`+0x2000`). |
| 4 | **SSID/SSVID/Class codes** | PCI Config `0x08` (`THC_CFG_CC_RID`), `0x2C` | Program Subsystem ID, Subsystem Vendor ID, Base Class (`0x09`), Sub-Class. |
| 5 | **MSI configuration** | PCI Config `0x50`–`0x5C` | Program MSI Capability ID, MSI Message Address/Data registers. |
| 6 | **Legacy interrupt** | PCI Config `0x3C` (`INT_LN/INT_PIN`) | Set `THC_CFG_INT.IPIN`. For MSFT G5 panels: set **bit 31 of THC MMIO offset `0x1128`** = `1`. |
| 7 | **Port configuration** | `THC_M_PRT_CONTROL` (MMIO `0x1008`) | Set `PORT_TYPE` (bits 31:30): `00`=SPI, `01`=I2C. Clear `PORT_SUPPORTED` (bit 28) for unused ports. |
| 8 | **SAI/CDC register setup** | IOSF SB Port P39h: `0x20`–`0x3C` (SAI), `0x00`–`0x0C` (CDC) | Configure INDEX41 SAI policy for MRd/MWr/CfgRd/CfgWr. CDC defaults: `THC_SB_PR_CDC_CFG` = `0x0000_CCC0`, `THC_SB_SD_CDC_CFG` = `0x0000_CCC0`. |
| 9 | **Clock gating enable** | IOSF SB private registers, `THC_SB_DCGE_CFG` (SB `0x10`) | Set all clock enable bits. Uses soft straps `ClockGateEnable` for production; SB regs for debug override only. |
| 10 | **Power gating enable** | PCI Config `0xA2` (`THC_CFG_PCE`) | Set `HAE` (bit 5) = 1, `D3HE` (bit 2) = 1. `SE` (bit 3) defaults to 1. |
| 11 | **LTR programming** | MMIO `0x0014` (`THC_M_CMN_LTR_CTRL`) | Program `ACT_LTR_VAL` (bits 29:20), `ACT_LTR_SCALE` (bits 19:17), `LP_LTR_VAL` (bits 16:7), `LP_LTR_SCALE` (bits 6:4). Set `ACTIVE_LTR_EN` (bit 1), `LP_LTR_EN` (bit 3). |
| 12 | **BIOS policy knobs** | Various | Apply platform BOM settings: SPI frequency (via `SPI_TCRF`/`SPI_TCWF` in `SPI_CFG`), I2C speed mode, D0i2 entry timer, WoT enable, MTL+ DID bit[16]. |
| 13 | **BIOS_LOCK_EN** | `THC_M_PRT_CONTROL` bit 27 | Set `THC_BIOS_LOCK_EN` — locks BIOS-configured registers before OS handoff. Sticky until reset. |
| 14 | **THC left in D0** | PCI Config `0x74` (`PMCSR`) | BIOS leaves THC in D0 state (`PMCSR[1:0]` = `00`) for OS driver pickup. |

> **Function Disable path** (if THC not needed): CDC regs CCC0→CCC3 → `HAE`=1 → `PMCSR`=D3 → `THC_CFG_UR_STS_CTL.FD`=1. Requires power cycle to recover.

#### Phase 2: OS Driver Probe — QuickSPI (14-Step Sequence)

Source: Linux kernel `pci-quickspi.c` → `quickspi_probe()`:

### TCTL_COMMAND Enum (Touch Controller Commands)

| Command | Value | Description |
|---------|-------|-------------|
| `TCTL_GET_HID_REPORT_DESCRIPTOR` | `0` | Get HID report descriptor from Touch IC |

> The TCTL_COMMAND enum is used for FPGA/LCBE workaround flow (see `FPGA_LCBE` registry key). When `FPGA_LCBE=1`, the driver blocks Get Descriptor TCTL commands.

| Step | Function | Register/Action | Details |
|------|----------|-----------------|---------|
| 1 | `pcim_enable_device` | PCI Command Register | Enable PCI device, set bus master and memory space bits. |
| 2 | `pcim_iomap_regions` | BAR0 | Map 32KB MMIO region into kernel virtual address space. |
| 3 | `pci_alloc_irq_vectors` | MSI/MSI-X/INTx | Allocate interrupt vector (`PCI_IRQ_ALL_TYPES` — prefers MSI). |
| 4 | `thc_dev_init` | Regmap init + state clear | Allocate `thc_device` struct. Init regmap (ranges: `0x10–0x14`, `0x1000–0x1320`, stride=4, no cache). `thc_clear_state()`: clear `ERR_CAUSE` (offset `0x1028`), clear DMA STALL bits, clear `INT_STATUS` TXN_ERR/FATAL_ERR, reset all 16 counter registers to 0, enable error reporting interrupts. |
| 5 | `quickspi_acpi_get_properties` | ACPI DSM | Parse ACPI `_DSD`/DSM for SPI config: clock frequency, IO mode (Single/Dual/Quad), read/write opcodes, MPS, DEVINT_CFG parameters. |
| 6 | `thc_port_select` | `THC_M_PRT_CONTROL` (offset `0x1008`) | Set `PORT_TYPE` = `00` (SPI). Enable `SPI_CSA_CK_DELAY_EN` (bit 25) with default delay = 4 in `SPI_DUTYC_CFG` (offset `0x1300`). |
| 7 | `thc_spi_configure` | `THC_M_PRT_SPI_CFG` (offset `0x1010`) | Program `SPI_TCRF`/`SPI_TCWF` (frequency dividers), `SPI_TRMODE`/`SPI_TWMODE` (IO mode), `SPI_RD_MPS`/`SPI_WR_MPS`. Program `SPI_ICRRD_OPCODE` (offset `0x1014`), `SPI_DMARD_OPCODE` (offset `0x1018`), `SPI_WR_OPCODE` (offset `0x101C`). Configure `DEVINT_CFG_1` (offset `0x10EC`) and `DEVINT_CFG_2` (offset `0x10F0`). |
| 8 | `quickspi_hid_send_report` | PIO RESET via `SW_SEQ_CNTRL` (offset `0x1040`) | Send RESET command to Touch IC via PIO: set opcode=`0x6` (SPI Write), target address, byte count. Trigger `TSSGO` (bit 0). Uses ACPI `_RST` method with `'TSR_'` signature for device reset. Set `INT_EDG_DET_EN` (bit 31 of `TSEQ_CNTRL_1`, offset `0x1128`) = 1 for edge-triggered interrupt. |
| 9 | Wait for reset response | `READ_DMA_INT_STS_1` bit 4 (`NONDMA_INT_STS`) | Wait up to 5 seconds for NONDMA interrupt indicating reset response. Validate response type = `RESET_RESPONSE` (`0x03`). Re-assert `INT_EDG_DET_EN` = 1 (kernel 6.17 fix `8fe2cd8`). |
| 10 | `thc_dma_init` + `thc_dma_configure` | PRD base addresses, DMA control regs | Allocate PRD rings. Program `RPRD_BA_LOW/HI_1` (offset `0x1100`/`0x1104`), `RPRD_BA_LOW/HI_2` (offset `0x1200`/`0x1204`), `WPRD_BA_LOW/HI` (offset `0x1090`/`0x1094`). Set `RPRD_CNTRL` PCD/PTEC/WM fields. All PRD entries must be 4KB-aligned (RTL bug 15014172472). |
| 11 | `thc_interrupt_config` | `THC_M_PRT_INT_EN` (offset `0x1020`) | Set `GBL_INT_EN` (bit 31) = 1. Enable per-channel DMA interrupts via `READ_DMA_CNTRL_x` IE bits (IE_EOF, IE_ERROR, IE_STALL). Enable `TXN_ERR_INT_EN` (bit 29), `FATAL_ERR_INT_EN` (bit 16), `BUF_OVRRUN_ERR_INT_EN` (bit 12). |
| 12 | `quickspi_hid_parse` | PIO reads to Touch IC | Read 24-byte HIDSPI device descriptor from TIC register `0x14` (ID = `0x43495424` = `"$TIC"`). Parse VID, PID, max input/output/feature report lengths. Read HID report descriptor from TIC bulk window (`0x1000`). |
| 13 | `hid_add_device` | Linux HID subsystem | Register with HID core as `BUS_PCI` (`0x19`) device. HID subsystem creates `/dev/hidraw*` and input event nodes. |
| 14 | Driver sets `DRV_LOCK_EN` | `THC_M_PRT_CONTROL` bit 13 | Lock driver-configured registers. Both `BIOS_LOCK_EN` and `DRV_LOCK_EN` are sticky until reset. |

> **State transition**: `QUICKSPI_NONE` → (step 4) → `QUICKSPI_INITED` → (step 9) → `QUICKSPI_RESETED` → (step 13) → `QUICKSPI_STARTED`

#### Phase 3: OS Driver Probe — QuickI2C (Differences from QuickSPI)

Source: Linux kernel `pci-quicki2c.c` → `quicki2c_probe()`:

| Step | QuickSPI | QuickI2C Difference |
|------|----------|---------------------|
| 5 | `quickspi_acpi_get_properties` (SPI DSM) | `quicki2c_acpi_get_properties` — parses I2C config: bus speed (Standard 100K / Fast 400K / Fast+ 1M), slave address, HCNT/LCNT timing, ACPI ICRS/ISUB data. |
| 6 | `thc_port_select` → PORT_TYPE=`00` (SPI) | `thc_port_select` → PORT_TYPE=`01` (I2C). **No** `SPI_CSA_CK_DELAY_EN` programming. |
| 7 | `thc_spi_configure` (SPI opcodes, freq) | `thc_i2c_configure` — **12-step Synopsys DW I2C Sub-IP Init**: (1) `IC_ENABLE` (`0x6C`)=0 disable; (2) `IC_CON` (`0x00`)=`0x0663` (Master, Fast, 7-bit, Restart EN, Slave DIS, RX_FIFO_FULL_HLD, STOP_DET_IF_MASTER); (3) `IC_TAR` (`0x04`)=device addr (e.g., `0x0A` WACOM, `0x16` ELAN, `0x2C` trackpad); (4) `IC_FS_SCL_HCNT/LCNT` (`0x1C`/`0x20`) or `IC_SS_SCL_HCNT/LCNT` (`0x14`/`0x18`); (5) `IC_INTR_MASK` (`0x30`)=`0x7FFF`; (6) `IC_RX_TL` (`0x38`)=62; (7) `IC_TX_TL` (`0x3C`)=0; (8) `IC_DMA_CR` (`0x88`)=`0x03`; (9) `IC_DMA_TDLR` (`0x8C`)=7; (10) `IC_DMA_RDLR` (`0x90`)=7; (11) `IC_SDA_HOLD` (`0x7C`)=configured value; (12) `IC_ENABLE` (`0x6C`)=1 enable. Then set `ARB_POLICY`=`FRAME_BOUNDARY`. **Also**: program `SPI_RD_MPS` = 4096 even in I2C mode (RTL bug workaround). |
| 8 | RESET via ACPI `_RST` (SPI PIO) | RESET via I2C PIO: send `SET_POWER(ON)` + `RESET` command via I2C PIO opcode `0x18` (I2C Device Write). Uses GPIO DEVRST toggle (not ACPI `_RST`). **Note**: Windows HIDI2C driver uses GPIO DEVRST for reset — the ACPI `_RST` method is commented out in the HIDI2C code path and NOT used. Only HIDSPI uses ACPI `_RST`. |
| 9 | Edge-triggered NONDMA wait | Same 5s timeout. QuickI2C uses TXDMA for `SET_POWER` + `RESET` (not PIO on some paths). Enhanced reset flow since kernel 6.18 (`73f3a74`). |
| 10 | DMA init (RXDMA1/2 + TXDMA) | DMA init includes **SWDMA** channel: `RPRD_BA_LOW/HI_SW` (offset `0x12C0`/`0x12C4`), `RPRD_CNTRL_SW` (offset `0x12C8`) with I2C-specific fields `THC_SWDMA_I2C_RX_DLEN_EN` (bit 23), `THC_SWDMA_I2C_WBC` (bits 31:26). |
| 11 | Interrupt config (SPI error set) | Additionally enables I2C sub-IP interrupts: `I2C_IC_TX_ABRT_INT_EN` (bit 22), `I2C_IC_SCL_STUCK_AT_LOW_DET_INT_EN` (bit 24), etc. in `INT_EN` (offset `0x1020`). |
| 12 | 24-byte HIDSPI descriptor | 30-byte HIDI2C descriptor (HID-over-I2C spec). Read via I2C Write+Read PIO opcode `0x1C` (repeated START). |
| 13–14 | Same | Same — `hid_add_device` + `DRV_LOCK_EN`. |

> **State transition**: `QUICKI2C_NONE` → `QUICKI2C_INITED` → `QUICKI2C_RESETED` → `QUICKI2C_STARTED`

### Per-Platform Init Differences

| Platform | THC Gen | BDF (THC0 / THC1) | Key Init Differences |
|----------|---------|---------------------|---------------------|
| **MTL-P** | 3.0 | B:0 D:16 F:0 / B:0 D:16 F:1 | HIDSPI only (no HIDI2C support). 128-byte SPI MPS max (2048B). Reset GPIOs: `xxgpp_e_6` / `xxgpp_f_16`. MTL+ DID bit[16] RWOnce for PTSP vs HIDSPI selection. 8-bit SB port ID. |
| **MTL-S** | 3.0 | B:128 D:16 F:0 / B:128 D:16 F:1 | PCH die (not SOC). `thc_pci_or_pciemode` strap enables PCIe capability at offset `0xB0`. DIDs: `0x7F58`–`0x7F5B`. Reset GPIOs: `gpp_e_19` / `gpp_d_22`. |
| **LNL-M** | 4.0 | B:0 D:16 F:0 / B:0 D:16 F:1 | **First platform with HIDI2C + SWDMA engine**. 256-byte SPI MPS max (4096B). **I2C MPS workaround required**: `SPI_RD_MPS` must be set to 4096 even in I2C mode (`I2C_MPS_WA = 4096`). DIDs: `0xA848`–`0xA84B`. 8-bit SB port ID. `GBL_INT_EN` default=1 (new for Gen4.0). |
| **PTL-U & PTL-P (PTL-H12Xe, PCD-P)** | 4.1 | B:0 D:16 F:0 / B:0 D:16 F:1 | **D3 4-level power management** (D0/D0i2/D3-Hot/D3-Cold). **Half-divider SPI clock** via DCG (formula: `125MHz / (2 × (divider + 0.5))`). **16-bit SB port ID** required (HSDES 15010734105). DIDs: `0xE448`–`0xE44B`. I2C MPS workaround still required. Telemetry counters available. THC1 requires THC0 enabled. RVP connectors: J6B2 (THC0), J5B2 (THC1). PTL-U and PTL-P share the same PCD-P die → identical DIDs. |
| **PTL-H (PTL-H4Xe, PCD-H)** | 4.1 | B:0 D:16 F:0 / B:0 D:16 F:1 | Same THC IP gen as PTL-U/P but uses PCD-H die → **own DIDs**: `0xE348`–`0xE34B`. Same 16-bit SB port ID, half-divider clock, D3 4-level. |
| **NVL-H** | 4.2 | B:0 D:16 F:0 / **B:0 D:8 F:0** ⚠️ | **THC1 BDF changed**: Dev=8 Fun=0 (was Dev=16 Fun=1 on all prior platforms). DIDs: `0xD348`–`0xD34B`. **I2C MPS workaround NOT needed** (fixed in silicon). Unified HAS (`sip_thc_4x_has.html`). Configurable PI via `thc_pi_def[7:0]` soft strap. Signal renaming: `thc0_spi_`, `thc1_i2c_`, `thc0_rst_b`. PMC addresses: `PMC_SSRAM_BASE_ADDR`=`0xFE010000`, `PMC_PWRM_BASE_ADDR`=`0xFF113000`. Desktop NVL-S has THC **fuse-disabled** (ZBB'ed). |
| **WCL** | 4.1 | B:0 D:16 F:0 / B:0 D:16 F:1 | Same PTL silicon gen. DIDs: `0x4D48`–`0x4D4B` (confirmed in Linux kernel `quickspi-dev.h` and `quicki2c-dev.h` on master). SwAS and kernel BOTH use `0x4D48`–`0x4D4B`. Same init sequence as PTL. |
| **ARL** | 3.0 | Varies | Same THC IP as MTL (Gen3.0). ARL-H DIDs: `0x7749`/`0x774B`, ARL-U DIDs: `0x7F49`/`0x7F4B`. Added to Linux kernel 6.19. Desktop — verify THC port availability per SKU. |
| **RZL** | 4.2 | Same as NVL (THC0 Bus16/Fun0, THC1 Bus8/Fun0) | Reuses NVL-PCD-H die — THC IP identical to NVL. DIDs: `0x6C48`–`0x6C4B` (Co-De Sign verified from razorlake PCD). Follows standard even/odd DID pattern. Not yet in `thc_project_data.py` or upstream Linux kernel. |
| **TTL** | 4.2 | Same as NVL (THC0 Bus16/Fun0, THC1 Bus8/Fun0) | THC IP "1.0 (no change)" from NVL. DIDs: THC0 `0x9334`/`0x9335`, THC1 `0x9339`/`0x933A` (Co-De Sign verified from titanlake platform firmware arch spec). **WARNING: TTL breaks the standard x8/x9/xA/xB DID pattern used by all other platforms.** Not yet in `thc_project_data.py` or upstream Linux kernel. |

### BIOS Prerequisite Checklist (Per Platform)

Consolidated from BWG, HAS, and platform-specific validation data:

#### All Platforms (Common)
- [ ] THC PCI device detected during enumeration (DEVVENDID valid)
- [ ] BAR0 assigned (32KB MMIO, 64-bit)
- [ ] MSI configured and enabled
- [ ] `THC_CFG_PCE`: `HAE`=1 (bit 5), `D3HE`=1 (bit 2)
- [ ] LTR programmed: `ACT_LTR_VAL`, `ACT_LTR_SCALE`, `LP_LTR_VAL`, `LP_LTR_SCALE`, enables set
- [ ] SAI policy registers configured (P39h: `0x20`–`0x3C`)
- [ ] CDC registers at default (`0x0000_CCC0`) for normal operation
- [ ] Clock gating enabled via soft straps (`ClockGateEnable`)
- [ ] `PORT_TYPE` set correctly for BOM (SPI=`00`, I2C=`01`)
- [ ] `BIOS_LOCK_EN` set before OS handoff
- [ ] **vGPIO pad unlocked for WoT**: `PADCFGLOCK_VGPIO_THC0` = `0x0` (if WoT enabled in BIOS). BIOS "Force unlock on all GPIO pads" = Disable can lock this pad → WoT fails silently. See HSDES 15018635096 (NVL), 16028429994 (WCL BIOS fix).
- [ ] GPIO IOSTANDBY configured to retain last driven values on Vnn removal
- [ ] THC left in D0 state for OS driver

#### MTL-Specific
- [ ] MTL+ DID bit[16] set: `0`=Intel PTSP, `1`=HIDSPI (RWOnce)
- [ ] MTL-S only: `thc_pci_or_pciemode` strap configured (PCIe cap at `0xB0` if enabled)
- [ ] HIDSPI only — no I2C port type allowed
- [ ] SPI MPS ≤ 2048B (128 packets)

#### LNL-Specific
- [ ] I2C MPS workaround: if I2C mode, program `SPI_RD_MPS` = 4096 in `SPI_CFG` (offset `0x1010`)
- [ ] HIDI2C: verify Synopsys DW I2C sub-IP init sequence completes (12 steps)
- [ ] `GBL_INT_EN` (bit 31 of `INT_EN`) defaults to 1 — verify not cleared
- [ ] SPI MPS up to 4096B (256 packets) now supported

#### PTL-Specific
- [ ] **16-bit SB port ID** — ensure all sideband port ID writes use 16-bit width (HSDES 15010734105)
- [ ] I2C MPS workaround still required (same as LNL)
- [ ] THC1 requires THC0 enabled — cannot enable THC1 alone
- [ ] Verify half-divider SPI clock if using non-standard frequencies
- [ ] Telemetry: counters `tx_frm_cnt`, `txdma_pkt_cnt`, `devint_cnt` available for monitoring
- [ ] RVP rework: BOM36 needs XF-16 (THC1), BOM37 needs XF-14/XF-15

#### NVL-Specific
- [ ] **THC1 BDF is B:0 D:8 F:0** — update any hardcoded BDF references
- [ ] I2C MPS workaround **NOT needed** (silicon fix)
- [ ] Disable I2C4, I2C5, SPI, I3C, ISH in BIOS before enabling THC
- [ ] LTR initial value: `0xFFFFFFFF` (infinite LTR on boot)
- [ ] IFWI ≥ ww50.1.01 required
- [ ] THC1 requires THC0 enabled
- [ ] PI register configurable via `thc_pi_def[7:0]` soft strap (per-port vs shared PCI header)
- [ ] Desktop NVL-S: THC is **fuse-disabled** — do not attempt init
- [ ] QuickSPI Non-POR from PTL+, QuickI2C Non-POR from NVL+ (HSD#16028137599)

### G3 Exit / Cold Boot Reset Sequence (from HAS)

The hardware-level reset sequence before BIOS runs:

| Step | Action | Mechanism |
|------|--------|-----------|
| 1 | PGCB reset → PGD enable | Power gating control block initializes power domains |
| 2 | Sideband reset / credit init | IOSF SB credit initialization between THC and PMC |
| 3 | Fuses / straps loaded | `THC_RESERVED_FUSE` (addr `0x3980`) and soft straps loaded via SB `Cpl/CplD` messages from PMC |
| 4 | `IP_RDY` asserted | THC signals readiness to PMC |
| 5 | `SETIDVALUES` SB message | PMC sends Device ID programming via sideband — upper 9 bits of DID overridable |
| 6 | Primary reset deassert (`thc_core_rst_b`) | Main logic exits reset. All MMIO/config registers at default values. THC ready for PCI enumeration. |

### S3 Resume Init Behavior

Per BWG Section 6.2: **BIOS must reinitialize THC using the same boot init flow** (full re-init from scratch). All registers are lost during S3 — no partial restore path. The BIOS repeats Phase 1 steps 1–14 identically to cold boot.

The OS driver then re-runs the full probe sequence. For runtime D3 (RTD3) resume, the driver performs a lighter restore using the D3 Save/Restore register list (see `fv-thc/power` for register restore order groups: Phase 1.xx SAI policies → Phase 2.xx PCI config → Phase 3.xx MMIO+sideband → Phase 5.xx PCE/CONTROL).

### ACPI _RST Method Implementation (from QuickSPI SwAS)

The ACPI `_RST` method performs device reset via GPIO toggle. Key implementation details from the sample ASL (QuickSPI SwAS v1.0 §P0810–P1021):

| Element | Detail |
|---------|--------|
| **Signature** | `'TSR_'` (reversed `_RST`) — driver validates this before invoking |
| **SW Lock** | `RSTL` (Reset Lock) field — prevents concurrent reset from multiple callers |
| **GPIO toggle** | Polarity-aware: reads `RPOL` (Reset Polarity) to determine active-low vs active-high assertion |
| **Assert duration** | **300ms sleep** (`Sleep(300)`) after GPIO assertion — ensures TIC sees a clean reset pulse |
| **Deassert** | GPIO toggled back to inactive state after sleep |
| **Return** | No return value — reset is fire-and-forget from ACPI perspective |

> **⚠️ Validation point**: Verify BIOS ASL implements polarity-aware GPIO toggle matching the board schematic. Incorrect polarity = reset never reaches TIC = probe hangs at step 9 (5s timeout). Also verify `RSTL` lock is released on error paths — a stuck lock blocks all subsequent resets.

## Validation Points

| # | Check | Expected | Notes |
|---|-------|----------|-------|
| 1 | **PCI Device ID** matches platform | DID from quick-reference table per SKU | ARL-U DIDs are UNVERIFIED — flag if encountered |
| 2 | **BDF assignment** matches platform spec | THC0/THC1 BDFs per platform (NVL THC1 changed to Bus=0 Dev=8 Fun=0) | THC1 requires THC0 enabled (Fun 0 must be active) |
| 3 | **BIOS knobs** correctly applied | THC ports enabled, correct PORT_TYPE (SPI/I2C), correct BOM selection | Check soft straps: PowerGateEnable, ClockGateEnable, thc_pi_def |
| 4 | **BOM device detection** | Touch device responds after reset with correct VID/PID | Cross-reference BOM config table — WACOM/ELAN/ALPS/Synaptics |
| 5 | **GPIO pad mode** routing correct | THC interrupt GPIO in native mode, reset GPIO in GPIO mode | Incorrect PMode = no interrupts or stuck reset |
| 6 | **Platform-specific workarounds** applied | SPI_RD_MPS=4096 for I2C, 16-bit SB port ID for PTL+ | Missing workarounds = silent data corruption or PM failures |

## See Also
- **`fv-thc/simics`** — Per-platform Simics object paths, boot commands, touch device models, BIOS setup values, HSDES sightings, SPARK transactors, unit tests
- **`fv-thc/registers`** — Register map offsets, PCI config space, BAR layout
- **`fv-thc/hidspi`** — HIDSPI BOM device configurations, SPI clock per platform
- **`fv-thc/hidi2c`** — HIDI2C BOM device configurations, I2C speed per platform
- **`fv-thc/power`** — Per-platform PMC addresses, power gate configuration
- **`fv-thc/dma`** — DMA buffer sizing, PRD alignment requirements, per-platform DMA performance targets
- **`fv-thc/debug`** — Platform-specific sightings (esp. NVL)
- **`fv-thc/driver`** — Per-platform registry overrides, BIOS prerequisites
- **`fv-thc/wot`** — Per-platform WoT configuration, GPIO wake pin mapping, PMC WoT sideband
- **Reference**: `fv-thc/docs/thc_test_coverage_matrix.md` — Full test matrix with platform coverage
- **Reference**: `fv-thc/docs/thc_bwg_extraction.md` — Full BWG reference document
- **Reference**: QuickSPI SwAS v1.0 §P0810–P1021 — **Complete sample ASL** with _DSM (3 GUIDs: HidSpi `6E2AC436-...`, THC `300D35B7-...`, LTR `84005682-...`), _RST, _INI, _CRS, _S0W methods. Use as ACPI reference for platform BIOS validation.

## Kernel Version Feature Matrix

| Kernel | Features Added |
|--------|----------------|
| 6.17 | WoT support, PTL QuickI2C, edge detection fix |
| 6.18 | WCL Device IDs, ACPI config enhancements |
| 6.19 | ARL Device IDs, DMA safety improvements |
| 6.20 | QuickI2C output reports, I2C regs save fix (a7fc15e — critical for D3Cold SnR) |
