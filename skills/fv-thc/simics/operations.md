# THC Simics Operations — Setup, Debug & Per-Platform Guide

> **Parent**: [`fv-thc/simics/SKILL.md`](./SKILL.md)
> **Scope**: Practical Simics setup, launch, debugging, driver installation, per-platform operational details, and S0ix PM procedures
> **Source Sections**: KB S13 (Setup), S14 (Debug), S19 (Per-Platform), S21 (Driver Install), S22 (THC Debug), S29 (S0ix PM)
> **Version**: 1.4

---

## Table of Contents

1. [Practical Setup & Launch](#1-practical-setup--launch)
2. [General Simics Debug Techniques](#2-general-simics-debug-techniques)
3. [Per-Platform THC Simics Guide](#3-per-platform-thc-simics-guide)
4. [Driver Installation & Workarounds](#4-driver-installation--workarounds)
5. [THC-Specific Simics Debugging](#5-thc-specific-simics-debugging)
6. [S0ix PM Enabling & THC Disable](#6-s0ix-pm-enabling--thc-disable)
7. [FLEXCON Simics Presets](#7-flexcon-simics-presets)
8. [Record/Replay Debugging](#8-recordreplay-debugging)

---

## 1. Practical Setup & Launch

> **Source**: KB S13 (wiki page 4639109312 — RZL VP Execution)

### 1.1 SimLauncher Installation

```bash
pip install simlauncher --index-url https://af02p-or.devtools.intel.com/artifactory/api/pypi/simics-pypi-or-local/simple
```

### 1.2 Running a VP

```bash
# Setup configuration
dtconfig setup

# Launch VP (example for RazorLake, adapt for TTL)
simlauncher run razorlake-desktop-7 <version> \
    --cores 4 \
    --memory 128 \
    --disk 64 \
    --mode vnc
```

### 1.3 Working Directory

```
/nfs/site/disks/simcloud_<user>_001/projects/<platform>-7/<version>/
```

### 1.4 Launch Scripts

```bash
# Default boot (Windows with blessed IFWI)
./simics svos_simics.py

# Custom launch script
./simics my_thc_test.py
```

### 1.5 Target Documentation

```
https://docs.intel.com/documents/vp_simulation/vp_release/7/<platform>/
```

### 1.6 VP Package Installation via ISPM

> **Source**: Wiki page 3828353592 (VP packages installation/setup)

**ISPM (Intel Simics Package Manager)** is the standard tool for VP package installation and management.

```bash
# ISPM stable path (SLES12)
/nfs/site/disks/central_tools_tree/sles12/simics_package_manager/stable/ispm

# List available VP versions for NVL
ispm platforms --list-versions novalake-pmsbx-6.0

# Install a specific VP release
ispm platforms install novalake-pmsbx-6.0 --version <release_version>
```

**Artifactory URL** for VP release manifests:
```
https://af-simics.devtools.intel.com/ui/native/simics-local/vp-release-its/platforms
```

**Steps**:
1. Find the release manifest version from Artifactory or `ispm platforms --list-versions`
2. Install using `ispm platforms install <platform-package> --version <version>`
3. Verify installation via `ispm platforms list`

---

## 2. General Simics Debug Techniques

> **Source**: KB S14 (wiki pages 2710449321, 1966867486, 1249985406)

### 2.1 Logging

```simics
# Set verbosity for a device
log-setup thc0 -verbose

# Set global log level (1=error, 2=warn, 3=info, 4=debug)
log-level 4

# Set component-specific log level with hierarchy propagation
thc0.log-level 4

# Break on specific log message
break-log thc0 "DMA transfer complete"

# Redirect logs to file
log-setup -overwrite simics.log

# Eclipse console integration
log-setup -eclipse-console
```

### 2.2 Register Access

```simics
# PCI config space read
pci-read bus=16 dev=0 func=0 offset=0x00 size=4

# MMIO read (with SID/CID/TID)
mem-read <thc0.bar0> 0x008 4

# Break on device register access
break-io thc0.regs.PRT_CONTROL -w
```

### 2.2a Address Translation & Register Inspection

> **Source**: Wiki page 2117879707 (PSG Simics Debug Commands)

```simics
# ★ probe-address — trace MMIO address through FULL translation chain
# Shows: CPU → bus → device → register with offset
probe-address 0xFED40008
$a = (probe-address 0xFED40008)    # Save result to variable

# ★ Dump ALL registers with offsets for a device bank
print-device-regs thc0.bank.regs

# ★ Inspect single register: bits, offset, value, bitfields
print-device-reg-info thc0.bank.regs.PRT_CONTROL

# ★ Break on specific register offset range (e.g., offset 0x0 to 0x4)
break-io thc0 port=regs offset=0x0 0x4

# ★ Break on ALL IO to a device
break-io thc0

# List and remove breakpoints
unbreak-io -list
unbreak-io thc0
```

**THC Debug Use Cases**:
- `probe-address` on a THC BAR0 address verifies it hits the correct THC register bank
- `print-device-regs` dumps all THC registers at once for state comparison
- `break-io` with offset range catches unexpected register accesses during DMA/PIO

### 2.2b Checkpoints & State Comparison

```simics
# Save checkpoint (full simulation state)
write-configuration ckpt_before_dma

# ... perform operation ...

# Save another checkpoint
write-configuration ckpt_after_dma

# Restore to earlier state
read-configuration ckpt_before_dma

# ★ State comparison technique: diff the two checkpoint directories
# to find exactly what changed (registers, memory, device state)
```

### 2.2c Console Capture

```simics
# Find all console objects
list-objects class=textcon -all

# Start capturing console output to file
$system.serconsole.con.capture-start thc_boot_log.txt

# Break on specific console string (e.g., THC driver load message)
$system.serconsole.con.break "THC"
```

### 2.2d CPU Debug

```simics
# Select core context for register inspection
psel "core[0]"

# Dump CPU registers
pregs

# Disable specific cores (useful for reducing noise)
<core>.externally_disabled = 1
```

### 2.3 PIO Synthetic Test (from LNL vjt/thc)

```simics
# Read 8 bytes from device address 0x0
PIO_Read(0x0, 8)

# Write 4 bytes (0x12345678) to device address 0x0
PIO_Write(0x0, 4, 0x12345678)
```

### 2.4 DML Source Debugging

```bash
# Build with debug symbols
gmake DEBUG=yes

# Use Eclipse + GDB attach
# Set breakpoints in DML source files
# Inspect DML variables
```

### 2.5 BIOS Boot Phases

| Phase | Description | THC Relevance |
|-------|-------------|---------------|
| **SEC** | Security/reset vector | N/A |
| **PEI** | Pre-EFI Initialization | THC softstraps read |
| **DXE** | Driver Execution Environment | **THC PCI enumeration happens here** |
| **BDS** | Boot Device Selection | THC driver loading |

### 2.6 VP Farm Access

```bash
# Developer debug with source code in farm
crt <session_name>
```

### 2.7 Scripting

```python
# Python preferred for complex test logic
import simics

# Read THC register
val = simics.SIM_read_phys_memory(cpu, thc_bar0 + 0x008, 4)

# Write THC register
simics.SIM_write_phys_memory(cpu, thc_bar0 + 0x008, value, 4)

# Wait for condition
simics.SIM_run_command("wait-for-log thc0 'ready'")
```

---

## 3. Per-Platform THC Simics Guide

> **Source**: KB S19 (wiki pages 2845164237, 4045307441, 3217199088, 1966867128, 1966867553, 1433100579, 4639109312, 4175342280, 4501129290)

### 3.1 THC Simics Object Path Evolution

The THC model object path **changes per platform**. This is critical for PythonSV namednode resolution.

| Platform | Gen | THC Object Path | Die Hierarchy | Source Page |
|----------|-----|----------------|---------------|-------------|
| **LKF** | 1.0 | `lkf.mb.sb.thc0` / `thc1` | `mb.sb` (southbridge) | 1433100579 |
| **MTL** | 3.0 | `mtl.mb.soc.thc0` / `thc1` | `mb.soc` (SoC) | 1966867553 |
| **LNL** | 4.0 | `lnl.mb.south.thc0` / `thc1` | `mb.south` (south complex) | 2845164237 |
| **PTL** | 4.1 | `$system.mb.south.thc0` / `thc1` | `mb.south` (south complex) | 3217199088 |
| **NVL-S** | 4.2 | `nvl.mb.pch.thc0` / `thc1` | `mb.pch` (PCH) | 4045307441 |
| **RZL** | 4.2 | `razorlake.mb.pch.thc0` / `thc1` (inferred) | `mb.pch` (PCH) | 4639109312 |
| **TTL** | 4.2 | **UNKNOWN — must determine** | Likely `mb.pch` (same as NVL) | — |

**Key observation**: Hierarchy evolved `sb` -> `soc` -> `south` -> `pch`. TTL must be verified before writing scripts.

#### RZL Platform Details (from page 4639109312)

- **SimLauncher**: `pip install devtools_launchers` -> `simlauncher run razorlake-desktop-7 2026ww06.2.22_47 --cores 4 --memory 128 --disk 64 --mode vnc`
- **Boot**: `load-target razorlake-desktop/platform` (defaults to Windows + latest IFWI + 0F config)
- **Custom launch**: Python script (e.g., `svos_simics.py`) for SVOS or custom IFWI
- **Target guide**: `https://docs.intel.com/documents/vp_simulation/vp_release/7/razorlake-desktop/`
- **Working dir**: `/nfs/site/disks/simcloud_bjlagers_001/projects/razorlake-desktop-7/`
- **Gen4.2 THC**: Same as NVL/TTL — unified HAS `sip_thc_4x_has.html`

### 3.2 Platform Boot Commands (load-target)

| Platform | Protocol | Boot Command |
|----------|----------|-------------|
| **NVL-S** | I2C | `load-target nvl-s/platform touchscreen:enable=TRUE touchscreen:component=i2c` |
| **PTL** | I2C | `load-target ptl/ptl-p touchscreen:enable=TRUE touchscreen:component=i2c sw:disk:enabled=TRUE` |
| **PTL** | SPI | `$wa_16015917403_enable=TRUE` then `load-target ptl/ptl-p touchscreen:enable=TRUE touchscreen:component=ipts sw:disk:enabled=TRUE` |
| **MTL** | SPI | Simics pkg 7500 + base 1000 (no load-target, older launch method) |
| **LNL** | I2C | Simics pkg 7600 + base 1000, IFWI-based boot (HSDES 15012829359) |
| **TTL** | I2C | **UNKNOWN** — likely `load-target ttl/platform touchscreen:enable=TRUE touchscreen:component=i2c` |

**Key patterns**:
- `touchscreen:enable=TRUE` — enables the touch device model
- `touchscreen:component=i2c` — I2C mode (alps_touchscreen model)
- `touchscreen:component=ipts` — SPI mode (TEP model)
- `sw:disk:enabled=TRUE` — enables disk image for OS boot
- PTL SPI requires explicit WA: `$wa_16015917403_enable=TRUE` (HSDES 16015917403)
- PTL target script also available as `ptl-m.chromeos.simics` for ChromeOS, with `handle_outside_memory=TRUE` (source: wiki 3439922659)
- **ISH/THC1 GPIO mux conflict**: THC1 GPIO pins are shared with ISH — **ISH must be disabled** (`PchIshEnable=0x0`) when THC1 is active (source: BOM52 wiki 4501129290)

### 3.3 BIOS Setup for THC in Simics

All platforms use the same BIOS setup path:

**Navigation**: Boot -> **F2** -> Intel Advanced -> PCH-IO Configuration -> **THC Configuration**

#### I2C Mode BIOS Values (NVL-S reference)

| Field | NVL-S Value | Notes |
|-------|------------|-------|
| Mode | HID over I2C | Protocol selection |
| Device Address | `A` | 0x0A (ALPS touchscreen) |
| Connection Speed | `18A60` | 100,960 decimal (~101KHz) |
| Descriptor Address | `1` | HID descriptor register offset |
| SM SCL HIGH | `267` | Standard Mode I2C clock high period |
| SM SCL LOW | `271` | Standard Mode I2C clock low period |
| FM SCL HIGH | `0x5C` (92) | Fast Mode (400KHz) I2C clock high period (source: BOM52 wiki 4501129290) |
| FM SCL LOW | `0x9C` (156) | Fast Mode I2C clock low period |
| FMP SCL HIGH | `0x22` (34) | Fast-Plus (1MHz) I2C clock high period (source: BOM52 wiki 4501129290) |
| FMP SCL LOW | `0x26` (38) | Fast-Plus I2C clock low period |
| Addressing Mode | `1` | 7-bit I2C addressing (PTL BKM) |
| Remaining fields | `FFFF` | Leave as default (PTL BKM) |

> **Speed Mode Mapping**: SM Connection Speed = `0x18A60` (100,960), FM = `0x61A80` (400,000), FMP = `0xF4240` (1,000,000). Source: BOM52 wiki 4501129290.

#### SPI Mode BIOS Values (PTL reference)

| Field | PTL Value | Notes |
|-------|----------|-------|
| Mode | HIDSPI | Protocol selection |
| Input Report Body Address | `0x1000` | HIDSPI input report body read address |
| Input Report Header Address | `0x0` | HIDSPI input report header address |
| Output Report Address | `0x1000` | HIDSPI output report write address |
| Write Opcode | `0x2` | SPI write command opcode |
| Read Opcode | `0xB` | SPI read command opcode |
| Limit Packet Size | `1` | Enable packet size limiting |

#### GPIO Unlock (Required for all modes)

Intel Advanced -> PCH-IO -> Security Configuration -> **Force unlock on all GPIO pads -> Enabled**

### 3.4 Touch Data Injection

#### SPI Mode (TEP model)

```
# Mouse-to-touch simulation (MTL):
connect mtl.recorder.tablet_out mtl.tep.tic00_as_abs_mouse
mtl.console.con->abs_pointer_enabled = TRUE
# Now mouse movements generate touch events
```

#### I2C Mode (alps_touchscreen model)

```
# Load include files first:
run-command-file alps0_input_report.include
run-command-file alps0_hid_report_descriptor.include
run-command-file alps0_hid_device_descriptor.include

# Trigger touch event:
<platform>.mb.<die>.thc0->trigger_input_report = TRUE
# Change coordinates in include file for different positions
# X=0x1795, Y=0x1537 (little-endian 16-bit format)
```

**I2C LIMITATION**: Mouse cursor simulation does NOT work for I2C mode (only SPI). Must manually set X/Y coordinates in the include file and trigger each report individually.

### 3.5 File Transfer to Simics Guest

Two methods available:
1. **FTP**: `ftp://192.168.1.1` from within the Simics guest OS
2. **Simics Agent**: `$matic0.upload <host_path> <guest_path>` / `$matic0.download <guest_path> <host_path>`

### 3.6 WCL-Specific BIOS Configuration

> **Source**: Wiki page 4175342280

- **BIOS path**: Intel Advanced -> Serial IO Configuration -> THC0/THC1
- **Virtual Keyboard**: Boot Maintenance Manager -> Boot Configuration -> Enable Virtual Keyboard = **Enabled**
- **Key Learning**: WCL requires explicit Virtual Keyboard enable for pre-OS touch input

---

## 4. Driver Installation & Workarounds

> **Source**: KB S21 (wiki pages 1966867128, 1800325877, 2845164237, 4045307441, 3217199088, 1498127969, 4501129290, 1355098344)

### 4.1 Common Prerequisites

1. **Test signing**: Required for unsigned drivers in Simics
   ```cmd
   bcdedit /set testsigning on
   bcdedit /set nointegritychecks on
   ```
2. **File transfer**: Copy driver package via FTP (`ftp://192.168.1.1`) or Simics agent (`$matic0.upload`)
3. **Install**: Device Manager -> Update Driver -> Browse -> Select .inf file

### 4.2 Protocol-Specific Registry Workarounds

| Driver | Registry Path | Key | Value | Purpose | Source |
|--------|-------------|-----|-------|---------|--------|
| IPTS | `HKLM\SOFTWARE\Intel\IPTS` | `ResetIntrDelayUs` | `0` (DWORD) | Disable reset interrupt delay | 1966867128 |
| HIDSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `FPGA_LCBE` | `1` (DWORD) | FPGA/Simics workaround | 1966867128, 1800325877 |
| HIDSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `ReadReportDescriptorOnReset` | `1` (DWORD) | Force descriptor re-read after reset | 1966867128 |
| QuickSPI | `HKLM\SOFTWARE\Intel\HIDSPI` | `FPGA_LCBE` | `1` (DWORD) | Same as HIDSPI | 1800325877 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `ResetDelayMs` | configurable (DWORD) | Override reset delay | 1966867553 |
| QuickI2C | — | — | — | No registry WAs documented | 4045307441 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `TxDMA_Override` | `1` (DWORD) | Force PIO instead of TxDMA for output reports | 1355098344 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `IO_Mode_Override` | `0/1/2` (DWORD) | Override SPI IO mode: 0=Single, 1=Dual, 2=Quad | 1355098344 |
| THC (general) | `HKLM\SOFTWARE\Intel\THC` | `SPI_Frequency_Override` | (DWORD) | Override SPI clock frequency | 1355098344 |

### 4.3 Known Simics-Specific HSDES Sightings

| HSDES | Description | Workaround | Platform |
|-------|-------------|------------|----------|
| **1508517875** | SetIDValue assertion in THC model | `thc0->wa_ignore_setidvalue = TRUE` | MTL |
| **1508958117** | PEI_ASSERT with default BIOS on Simics | Use updated IFWI | MTL |
| **16015917403** | SPI mode broken on PTL Simics without WA | `$wa_16015917403_enable = TRUE` before load-target | PTL |
| **15012829359** | LNL Simics IFWI version tracking | Use `IFWI_LNL_M_Internal_2074.00_Dispatch_VS_DEBUG_PreProd_Simics.bin` | LNL |
| **16028137599** | Windows QuickI2C driver DROPPED from NVL+ | Use Ubuntu with built-in QuickI2C kernel driver (POR). WinOS requires manual INF install | NVL+ |
| **1307012183** | GPIO of THC device not configured correctly | Simics GPIO model limitation (ADL-era, may persist) | ADL |

### 4.4 Driver Versions Used in Simics (Historical)

| Platform | Driver | Version | Source |
|----------|--------|---------|--------|
| MTL | IPTS | v3.0.0.252 | 1966867128 |
| MTL | HIDSPI | v1.0.0.41 | 1966867128 |
| MTL | QuickSPI (HIDSPI) | Debug_MSI version | 1800325877 |
| LNL | HIDI2C Touch | v5.0.4000.693 | 2845164237 |
| NVL-S | IntelQuickI2C | v5.5.0.7 or v5.5.0.10 | 4045307441, 4501129290 |
| NVL-Hx | WoT_QuickI2cExtension | (separate INF for WoT) | 4501129290 |
| PTL | HIDSPI + HIDI2C | (version not specified) | 3217199088 |

### 4.5 Simics-Specific Driver Installation Notes

- **Do NOT enable verbose logging during touch test** — causes timing delays that result in touch data loss (source: 1800325877)
- **Log level for debug**: `.log-level 4 -r` enables full debug logging on Simics model (source: 4045307441)
- After driver install, **reboot may be required** before touch device appears in Device Manager
- Touch validation tool: **DigiInfo** from Microsoft — shows real-time touch packets (source: 2845164237)
- MS Paint test: Inject 3x `trigger_input_report=TRUE`, then change packet byte `0x05->0x04` for finger-up event

### 4.6 IPTS Program History (Design Wins & Milestones)

> **Source**: Wiki page 1498127969 (IPTS Playbook, v43)

- **Driver version evolution**: THCBase 2.1.0.65 -> 3.0.100.230, Filter 3.1.0.50 -> 3.1.0.57, HSPI 4.0.x.x
- **Platforms covered**: TGL-H/R, ADL-P/M/SBGA, RPL, MTL-P/M
- **Design wins**: MSFT Surface, Lenovo Lark, HP Solaris, ASUS
- **Team transition**: IDC -> ISH (Intel Shanghai)
- **Pathfinding**: HIDSPI convergence, Test Endpoint, Remote Execution, Touch over LCH, E2E Latency

---

## 5. THC-Specific Simics Debugging

> **Source**: KB S22 (wiki pages 1966867486, 1249985406, 1800325877)

### 5.1 WinDbg Kernel Debugging over Telnet

From MTL Simics BKM (page 1966867486):

1. **Enable WinDbg in Simics script**: `$windbg_enable = TRUE`
2. **Default telnet port**: 12375
3. **Get target IP**: `sim->host_ipv4` in Simics console
4. **Host setup**: Create `C:\WinSymbols` folder for symbol cache
5. **Launch proxy**: Use `kdcom-proxy.exe` from Simics base package
6. **Boot**: Select **'Debug enabled'** in Windows boot menu — do NOT start Windows normally
7. **Connect WinDbg**: Standard kernel debugging session over telnet->kdcom proxy

### 5.2 Simics Model Debug Commands

| Command | Purpose |
|---------|---------|
| `.log-level 4 -r` | Enable full debug logging (level 4) recursively |
| `<thc_obj>->trigger_input_report = TRUE` | Manually trigger a touch input report |
| `<thc_obj>->wa_ignore_setidvalue = TRUE` | Enable SetIDValue workaround |
| `<tep>->doze_enable = FALSE` | Disable doze interrupts |
| `<tep>->reset_delay = 0.2` | Set reset delay (seconds) |
| `run-command-file <path>.include` | Load touch data/descriptor include file |
| `connect <recorder> <tep_mouse>` | Enable mouse-to-touch simulation (SPI only) |

### 5.3 ETL/WPP Trace Capture

From THC BAT Test BKM (page 1249985406):
- Use `ThcTrace.cmd` for WPP trace capture
- Captures driver-level trace events during touch operations
- For WPP GUIDs, see `fv-thc/debug` sub-skill: HIDSPI `{A891081A...}`, HIDI2C `{C47236A7...}`

### 5.4 PIO Validation in Simics

From THC BAT Test (LKF FPGA era, page 1249985406):

PIO register offsets from BAR0 base (per-port):

| Register | Offset | Purpose |
|----------|--------|---------|
| `THC_SS_CMD` | +0x1040 | PIO command register |
| `THC_SS_BC` | +0x1044 | PIO byte count |
| `THC_SS_DIN` | +0x1048 | PIO data in (read data) |
| `THC_SS_CD` | +0x104C | PIO command data (write data) |

PIO Write sequence: BAR setup (0x91400000) -> cmd enable (0x6) -> write data to +0x104C -> trigger PIO via +0x1040/+0x1044/+0x1048

**Note**: LKF-era offsets. Current platforms use offset base +0x1000 for port 0 registers. Verify against HAS for TTL.

---

## 6. S0ix PM Enabling & THC Disable

> **Source**: KB S29 (wiki pages 2918220570, 4200761602)

### 6.1 THC Disable for S0ix Testing

**BIOS Method**: Intel Advanced -> THC Configuration -> THC Port Configuration -> `<None>` (disable both ports)

**xmlcli Method**:
```
ThcAssignment_0=0x0    # None (disable THC0)
ThcAssignment_1=0x0    # None (disable THC1)
```

### 6.2 S0ix Failure: THC0 Primary Function Dependency

> **Source**: Wiki page 4200761602 (WCL THC BKM, v12)

**CRITICAL**: THC0 is the PCI bus **primary function** (Function 0). If only THC1 (e.g., trackpad) is configured:
- THC0 remains enabled without a driver binding
- THC0's PCI power state becomes **uncontrollable** (stuck in D0)
- This **blocks S0ix entry** for the entire platform

**Implication**: During validation, **both THC ports must be configured** (or both disabled) for S0ix testing. Never configure THC1 alone.

**OEM Note**: OEM designs may reverse the RVP assignment (THC0=touchpad, THC1=touchscreen). Validate per-platform BOM.

### 6.3 Full S0ix Disable List (for clean baseline)

All of these IPs must be disabled for a clean S0ix baseline test:
- iGFX, VMD, GNA, NPU, SATA, HDAudio, **THC**, all SerialIO, ISH, LAN

### 6.4 SVOS Sleep Commands

```bash
echo s2idle > /sys/power/mem_sleep
echo mem > /sys/power/state
```

### 6.5 MTL vs PTL Simics Parity

| Feature | MTL Simics | PTL Simics |
|---------|-----------|-----------|
| Debug | XDP, USB2 DBC | No debug connection |
| Network | GbE available | `network:enable_gbe=FALSE` |
| Display | VGA available | No display (VGA) |

---

## 7. FLEXCON Simics Presets

> **Source**: Wiki page 1150208468 (FLEXCON space, v112)

FLEXCON (Flexible Configuration) can generate Simics-specific platform presets for VP runs.

### 7.1 FLEXCON for THC Config

```
pysvext/<PROJECT>_flexcon/
├── plugins/      # Dynamic callback checkers
├── lib/          # Helper libraries
├── cfg/          # Configuration files
└── simics/       # Simics platform presets
```

Key modules:
- `flexcon_simics.py` — Simics platform preset generation
- `simics_helper.py` — Building Simics platform configurations
- `simics_platform_config_yml_file` — YAML format for Simics configs

### 7.2 THC BIOS Knob Presets via FLEXCON

FLEXCON can configure THC BIOS knobs automatically in VP runs:
- Port enable/disable (`ThcAssignment_0`, `ThcAssignment_1`)
- Protocol selection (HIDSPI, HIDI2C)
- GPIO routing and pad mode
- I2C speed mode and clock parameters

BIOS integration via XmlCli (`pysvtools.xmlcli`) — GBT-XML parsing, NVRAM mailbox interface.

### 7.3 Four Execution Phases

| Phase | Content | THC Relevance |
|-------|---------|---------------|
| Phase 1 | HW + Fuse + BIOS overrides | THC port enable, protocol select |
| Phase 2 | Register workarounds | THC register WAs (e.g., SPI_RD_MPS for I2C) |
| Phase 3A/3B | Config-dependent + env-based checking | THC config verification |
| Phase 4 | Post-check overrides | THC post-boot validation |

---

## 8. Record/Replay Debugging

> **Source**: Wiki page 4387353026 (suihaich, v18)

### 8.1 Recording Simics Sessions

Deterministic record/replay enables root-cause analysis of intermittent THC model failures (e.g., timing-sensitive DMA/interrupt issues).

**Tools**:
| Tool | Cost | Method |
|------|------|--------|
| **GDB record** | Free (built-in) | Basic process recording; limited to simple replay |
| **rr** (Mozilla) | Free | Intel PT + ptrace. Needs `kernel.perf_event_paranoid=1` |
| **Undo LiveRecorder** | $7,900/user/yr (udb) or $75,000/yr/product-group (live-record) | Snapshots + re-execution + event log |

### 8.2 Simics-Specific Recording Setup

```bash
# Simics binary is a shell script wrapper — add /bin/bash for live-record
# Main process: <simics_base>/linux64/bin/mini-python

# For long sessions (IWPS+Simics):
live-record --max-event-log-size 20G ./simics my_thc_test.py

# Security: run without networking
sudo unshare -n live-record ./simics my_thc_test.py
```

**Known limitation**: rr replay of IWPS may crash with tick count assertion.

---

## See Also

- [`SKILL.md`](./SKILL.md) — Core Simics concepts, strategy, gap analysis
- [`models.md`](./models.md) — THC models, transactors, touch device architectures
- [`advanced.md`](./advanced.md) — SW-CI, emulation, IPSV, display sync, advanced topics
- [`fv-thc/debug`](../debug/SKILL.md) — Post-silicon THC debug & triage (WPP GUIDs, sighting DB)
- [`fv-thc/platform`](../platform/SKILL.md) — Per-platform THC data (Device IDs, BDFs, BOM)
- [`fv-thc/power`](../power/SKILL.md) — THC power management (LTR, D0i2, CGPG, D3, S0ix)
- [`fv-thc/registers`](../registers/SKILL.md) — THC register maps, PIO flows
- [`docs/thc_simics_wiki_research_v2.md`](../docs/thc_simics_wiki_research_v2.md) — Full wiki research compilation (52 pages, 32+ searches)

---

*Source: THC SIMICS Pre-Silicon Knowledge Base v2.4 (thc_simics_presi_knowledge.md), sections S13-14, S19, S21-22, S29. Wiki research findings from 52 Intel Confluence pages.*
