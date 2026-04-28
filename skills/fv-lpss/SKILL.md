---
name: fv-lpss
description: "LPSS (Low Power Subsystem) debugging skills for I2C, I3C, SPI, and UART validation"
version: "rev2.0"
---

# LPSS (Low Power Subsystem) Debugging Skills

LPSS (Low Power Subsystem) is a collection of serial IO controllers integrated into Intel SoCs, providing essential connectivity for platform peripherals.

## Documentation & Reference Files

| Document | Location | Description |
|----------|----------|-------------|
| **HAS Digest** | `docs/has_digest.md` | **Complete LPSS HAS v5.2 digest** — Landing Zone, IOSF bridge, address maps, iDMA, I2C/SPI/UART/I3C slices, clocking, power management, reset domains |
| **I3C HCI Reference** | `docs/has_i3c_hci_reference.md` | I3C HCI-focused reference — ring architecture, HCI deviations (51 items), abort flows, DAA/IBI, combo transfers |
| **Known Issues Tracker** | `docs/lpss_known_issues.md` | Structured HSDES sightings, RTL bugs, driver issues, and open items |
| **Reference Sheets** | `docs/lpss_reference_sheets.md` | Step-by-step bring-up, debug triage trees, and quick-reference procedures |
| **BIOS XML Knob Dump** | `docs/bios_xml_dump.md` | How to dump all BIOS knobs on NVL/PTL — XmlCli Lite workaround, knob search, knob modification |
| **I2C Validation Reference** | `docs/i2c/DW_apb_i2c_validation_reference.md` | DW_apb_i2c v2.02a IP databook extract — 64+ registers, speed modes, abort sources |
| **I3C Validation Reference** | `docs/i3c/DWC_mipi_i3c_validation_reference.md` | DWC_mipi_i3c v1.00a-lca03 IP databook extract — HCI mode, commands, HALT recovery |

> **Load `docs/lpss_known_issues.md` first** when triaging any LPSS failure — it may already be a known issue with a documented workaround.

## ⚠️ CRITICAL: NEVER HARD-CODE PORT COUNTS - ALWAYS QUERY CO-DESIGN

**MANDATORY WORKFLOW FOR ANY PROJECT/PLATFORM:**

When asked about LPSS port counts (I2C, I3C, SPI, UART) for ANY project:

1. **DO NOT assume or hard-code numbers** - Different projects have different configurations
2. **ALWAYS query Co-design** using the specific HAS document pattern: `{PROJECT}_{DIE}_LPSS_Integration_HAS.html`
3. **Example query format:**
   ```
   Please reference the NVL_PCD_H_LPSS_Integration_HAS.html document and tell me: 
   How many I2C, I3C, SPI, and UART controllers are available in LPSS for Novalake PCD-H?
   ```
4. **Trust the HAS document response** as the authoritative source

**Example - Novalake PCD-H (from LPSS_HAS.html NVL_PCD_H_LPSS section):**
- I2C controllers: 6 (I2C0-I2C5) — I2C0-3 DMA, I2C4-5 PIO
- I3C controllers: 4 instances / 2 PCI controllers (I3C0/1 share ctrl #1, I3C2/3 share ctrl #2)
- SPI controllers: 3 (SPI0-SPI2) — all DMA
- UART controllers: 3 (UART0-UART2) — UART0-1 DMA, UART2 PIO

**All MTL/LNL/PTL/WCL/NVL platforms share the same LPSS IP slice configuration (HAS Table: Slice Configuraton):**
- I2C controllers: 6 (I2C0-I2C5) — I2C0-3 DMA, I2C4-5 PIO
- I3C controllers: 4 instances / 2 PCI controllers (I3C0/1 share ctrl #1, I3C2/3 share ctrl #2)
- SPI controllers: 3 (SPI0-SPI2) — all DMA
- UART controllers: 3 (UART0-UART2) — UART0-1 DMA, UART2 PIO

**Exception — MTP-S (Meteor Lake-S) has different counts:**
- UART: 4 (adds UART3 DMA) | SPI: 4 (adds SPI3 DMA) | I3C: 2 instances / 1 controller (I3C0/1 only, no I3C2/3)

> **Rule:** MTL/LNL/PTL/WCL/NVL all have identical LPSS port counts per HAS v5.2 rev 1.02. Only MTP-S differs. NVL additionally changes I3C core clock from 100 MHz to 200 MHz. Always verify with the HAS "Table: Slice Configuraton" for any new project.

---

## Safety Warnings

> These rules apply to ALL sub-skills and any PythonSV commands executed for LPSS.

| Rule | Details |
|------|---------|
| **DO NOT** write to fuse registers | LPSS fuse overrides are permanent — irreversible silicon damage |
| **DO NOT** modify clock source registers without confirmation | Wrong clock config can brick the controller until platform reset |
| **DO NOT** force-write PMCSR to D0 during S0ix entry | Can cause PMC firmware hang — requires cold boot to recover |
| **DO NOT** disable LPSS controllers in BIOS without recording the change | Other tests may depend on the controller being enumerated |
| **DO NOT** assume port counts across platforms | Always query Co-Design HAS for the specific project/die |
| **DO NOT** run I3C DAA commands without verifying target device presence | Can leave bus in undefined state |
| **ALWAYS** confirm target platform (NVL PCD-H vs PCH-S vs PTL) before register access | Wrong base path = wrong silicon, wrong results |
| **ALWAYS** read a register before writing it | Preserve other bit fields — don't blindly overwrite |

---

## CRITICAL: MANDATORY HAS Document Lookup Workflow

**Before answering ANY LPSS question for ANY project/platform, you MUST first look up the project-specific LPSS Integration HAS document from Codesign.**

### Mandatory Steps for Every New Project/Platform Query:

1. **Identify the project name** (e.g., NVL, PTL, LNL, WCL, ARL, etc.) and the die type (PCD-H, PCH-S, etc.)
2. **Search Codesign** (https://chat.co-design.intel.com/chat) for the project's LPSS Integration HAS using this naming pattern:
   - `{PROJECT}_{DIE}_LPSS_Integration_HAS.html`
   - Examples:
     - `NVL_PCD_H_LPSS_Integration_HAS.html`
     - `NVL_PCH_S_LPSS_Integration_HAS.html`
     - `PTL_PCD_P_LPSS_Integration_HAS.html`
     - `LNL_PCH_LPSS_Integration_HAS.html`
3. **Ask Codesign to reference that specific HAS document** when querying port counts, BDF assignments, controller groupings, feature lists, etc.
4. **NEVER assume port counts or configurations** from one project apply to another — each project's HAS is the single source of truth.

### Why This Matters:
- Generic Codesign responses may give incomplete or incorrect information (e.g., reporting 3 I3C ports when the HAS confirms 4)
- Each project may have different numbers of I2C, I3C, SPI, and UART controllers
- Controller groupings (e.g., I3C0/I3C1 paired under one controller) vary by project
- BDF assignments, DMA modes, and port ID widths are project-specific

> **Rule:** When Codesign general responses conflict with the specific LPSS Integration HAS document, **ALWAYS trust the HAS document**.

### Known HAS Documents (Reference):

| Project | Die | HAS Document |
|---------|-----|-------------|
| Nova Lake (NVL) | PCD-H | `NVL_PCD_H_LPSS_Integration_HAS.html` |
| Nova Lake (NVL) | PCH-S | `NVL_PCH_S_LPSS_Integration_HAS.html` |
| Panther Lake (PTL) | PCD-P | `PTL_PCD_P_LPSS_Integration_HAS.html` |

> **Note:** The LPSS HAS is a single document (`LPSS_HAS.html`, IP v5.2, rev 1.02, April 2025) covering MTL, MTP-S, LNL, PTL, WCL, and NVL. Platform-specific sections (e.g., `NVL_PCD_H_LPSS`, `PTL_PCD_P_LPSS`) are **sections within** this document, not separate files. For any new project, search for the `{PROJECT}_{DIE}_LPSS` section within `LPSS_HAS.html` on Co-Design.

## CRITICAL: Port Mapping Reference

**ALWAYS check the actual VJT LPSS configuration script before answering port mapping questions!**

**Source of Truth:** `C:\pythonsv\novalake\vjt\lpss\nvlh_cltap.py`

When asked which port a register path belongs to:
1. **READ nvlh_cltap.py first** - Do NOT assume or guess
2. **SEARCH for the fabric identifier** (e.g., `file_iosf2axi_pci_pf_top_12`)
3. **FIND which port definition uses it** - Check the 'fabric' field in each port config
4. **VERIFY line numbers** and provide evidence from the script
5. **NEVER assume sequential PCI function mapping** - The actual mapping is NOT sequential!

**Correct LPSS Fabric Mapping (from nvlh_cltap.py):**
- `pf_top_0` → I2C0
- `pf_top_1` → I2C1
- `pf_top_2` → I2C2
- `pf_top_3` → I2C3
- `pf_top_4` → I2C4
- `pf_top_5` → I2C5
- `pf_top_6` → UART0
- `pf_top_7` → UART1
- `pf_top_8` → UART2
- `pf_top_9` → SPI0
- `pf_top_10` → SPI1
- `pf_top_11` → SPI2
- `pf_top_12` → I3C0 & I3C1 (shared - same controller cluster)
- `pf_top_13` → I3C2 & I3C3 (shared - same controller cluster)

**Why I3C ports share fabric registers:**
I3C ports are paired on the same physical controller hardware:
- I3C0 and I3C1 share Controller 0 → Use `pf_top_12`
- I3C2 and I3C3 share Controller 1 → Use `pf_top_13`

## LPSS Landing Zone (HAS v5.2 Quick Reference)

> **Source:** LPSS_HAS.html — IP Version 5.2, Doc revision 1.02 (April 14, 2025)

### Controller Capabilities Summary

| Feature | I3C | I2C | SPI | UART |
|---------|-----|-----|-----|------|
| **Protocol** | SDR+DDR FM/FM+ | HS/FM+/FM/SS | Motorola SSP | RS232/16550/16750 |
| **Master** | Yes | Multi-master | Yes | Yes |
| **Slave** | No | No (host-only) | No | Yes (UART only) |
| **IBI (In-Band Interrupt)** | Yes | No | No | No |
| **Max Baud (kbps)** | 12,900 | 3,400 | 33,000 | 6,300 |
| **Validated Baud (kbps)** | 12,500 | 3,400 | 25,000 | 6,300 |
| **Signals** | 2 (SDA/SCL) | 2 (SDA/SCL) | 5 (CLK/MISO/MOSI/CS0/CS1) | 4 (TX/RX/RTS/CTS) |
| **HC FIFO Depth** | 64 DW | 64 B | 256 B (64×4B) | 64 B |
| **iDMA FIFO Depth** | 32 DW | 64 B | 128 B | 64 B |
| **Max DMA Burst** | 64 B | 32 B | 64 B | 32 B |
| **Voltage** | 1.8V only | 1.8/3.3V | 1.8/3.3V | 1.8/3.3V |

### IP Versions

| IP | Version | Notes |
|----|---------|-------|
| **I3C** | DWC_mipi_i3c v1.00a-ea51 (pre-PTL), v1.00a-LCA03 (PTL+) | Synopsys MIPI I3C |
| **I2C** | DW_apb_i2c v2.00a | Synopsys DesignWare APB I2C |
| **SPI** | Intel Penwell SSP v1.71 | Intel proprietary |
| **UART** | DW_apb_uart v3.14b (MTL), v4.02a (LNL+) | Synopsys DesignWare APB UART |

### HCI Versions

| Platform | HCI Version | Bridge Type |
|----------|-------------|-------------|
| MTL/MTP-S/LNL | HCI v0.8_r01 | IOSF2OCP |
| PTL/WCL/NVL | **HCI v1.0** | **IOSF2AXI** |

### Standards Compliance

- I2C: NXP UM10204 Rev.6
- I3C: MIPI I3C v1.0
- HCI: MIPI HCI v0.8_r01 (MTL/LNL) / v1.0 (PTL/WCL/NVL)

### Critical Limitations (per HAS)

| Controller | Limitation |
|-----------|-----------|
| **I3C** | No secondary master, no TSL/TSP, PIO for debug only (enable via GPPRVRW8.bit0), 1.8V only, min core_clk 133 MHz |
| **I2C** | Host-only (no slave/multi-host/generic call), 400 pF max load, FM+ simultaneous not supported |
| **SPI** | RWOT half-duplex, NO DMA burst (M-Size must be 1), only CS0/CS1 used (CS2/CS3 unused, 2nd CS deprecated since ADP-P), no slave mode |
| **UART** | No SIR/IrDA, no 9-bit/RS485/fractional baud, no in-band wake, max 6.25 Mbps |

> **Full details:** See `docs/has_digest.md` for the complete HAS digest with all register maps, timing formulas, and protocol details.

---

## LPSS Architecture Overview

LPSS includes the following controller types:

### I2C (Inter-Integrated Circuit) — DW_apb_i2c v2.02a
- Low-speed serial communication bus (Synopsys DesignWare APB I2C IP)
- Typical uses: Sensors, TPMs, ECs, touchscreens, audio codecs
- Master/slave modes, Standard (100K), Fast (400K), Fast+ (1M), High-Speed (3.4M) modes
- **Port counts vary by project** - Always query the project-specific HAS document via Co-design
- **Key Registers:** IC_CON (0x00), IC_TAR (0x04), IC_DATA_CMD (0x10), IC_STATUS (0x70), IC_ENABLE (0x6C), IC_TX_ABRT_SOURCE (0x80), IC_COMP_PARAM_1 (0xF4)
- **Validation Reference:** `docs/i2c/DW_apb_i2c_validation_reference.md`

### I3C (Improved Inter-Integrated Circuit) — DWC_mipi_i3c v1.00a
- Next-generation I2C with backward compatibility (Synopsys DWC MIPI I3C IP)
- Higher speed: SDR0 (12.5 MHz), SDR1-4 (8/6/4/2 MHz), HDR-DDR, HDR-TSP/TSL
- In-band interrupts (IBI), dynamic addressing (DAA via ENTDAA/SETDASA/SETAASA), Hot-Join
- Typical uses: Advanced sensors, camera modules
- **Two register sets:** HCI mode (Intel uses this) and Non-HCI/APB mode
- **HCI Key Registers:** HC_CONTROL (0x04), RESET_CONTROL (0x10), PRESENT_STATE (0x14), COMMAND_QUEUE_PORT (0x300), RESPONSE_QUEUE_PORT (0x304), PIO_INTR_STATUS (0x320)
- **Port counts vary by project** - Always query the project-specific HAS document via Co-design
- **Validation Reference:** `docs/i3c/DWC_mipi_i3c_validation_reference.md`

### SPI (Serial Peripheral Interface)
- High-speed synchronous serial communication
- Typical uses: Flash memory, displays, high-speed sensors
- Full-duplex communication
- Multiple chip select support
- **Port counts vary by project** - Always query the project-specific HAS document via Co-design

### UART (Universal Asynchronous Receiver/Transmitter)
- Asynchronous serial communication
- Typical uses: Debug consoles, Bluetooth modules, GPS
- Standard baud rates (9600, 115200, etc.)
- **Port counts vary by project** - Always query the project-specific HAS document via Co-design
- **Note:** May appear as HSUART (High-Speed UART) in PythonSV

---

## Sub-Skills

The fv-lpss skill provides 5 specialized sub-skills for debugging LPSS controllers:

### 1. fv-lpss/config-checkout
**Purpose:** Verify LPSS hardware configuration — PCI enumeration, register values, and pad routing

**When to use:**
- Checking PCI device presence (DIDs, BDFs, BARs)
- Validating register reset values and configuration against HAS
- Verifying pad mode (PMode) for correct native function routing
- Debugging "device not found", "register reads 0x0", or "pad stuck in GPIO mode" issues

**Covers:** PCI enumeration, Vendor/Device ID, BAR allocation, per-IP register maps (I2C IC_CON, I3C DEV_CTRL, SPI SCTRL, UART LCR), pad mode verification, pad ownership and lock checks

---

### 2. fv-lpss/power-state
**Purpose:** Verify LPSS power management — D-state transitions and clock gating

**When to use:**
- Debugging D3 entry/exit failures
- Verifying clocks are gated when controllers are idle
- Investigating S0ix blockers caused by LPSS
- Validating CGPG (Clock Gate / Power Gate) behavior

**Covers:** PMCSR D-state control, D0i2/D0i3/D3hot/D3cold transitions, trunk/functional/side clock gating, PMC PGCB registers, LTR values, S0ix blocker detection

**Important:** Clock gating is a prerequisite for D3 entry

---

### 3. fv-lpss/failure-analysis
**Purpose:** Analyze LPSS-related test failures from NGA test results

**When to use:**
- Investigating I2C/I3C/SPI/UART test failures
- Parsing logs for LPSS-specific error patterns
- Cross-referencing failures with known sightings
- Identifying failure trends across test runs

**Covers:** NGA integration, log parsing, sighting correlation

---

### 4. fv-lpss/driver
**Purpose:** Cross-platform driver analysis for LPSS controllers — Linux kernel and Windows SerialIO drivers

**When to use:**
- Comparing Linux vs Windows driver behavior for I2C/I3C/SPI/UART controllers
- Understanding driver probe sequences, interrupt handling, or DMA setup
- Debugging driver-level failures (probe failure, resource conflict, power management mismatch)
- Identifying driver-specific workarounds or HSDES references
- Understanding PCI Device ID matching and driver loading

**Covers:** Linux kernel drivers (i2c-designware, dw-i3c-master, spi-dw, 8250_lpss), Windows Intel SerialIO drivers, cross-driver architecture comparison, PCI Device ID tables, register access patterns, interrupt handling, power management differences, HSDES workaround references

---

### 5. fv-lpss/debug
**Purpose:** Systematic LPSS debug and triage — hardware-level failure analysis

**When to use:**
- Running structured triage (4-phase: Identify → Check Health → Protocol Debug → Root Cause)
- Matching failure symptoms to known signatures
- Using ITP/DCI, logic analyzers, or bus analyzers for LPSS debug
- Following debug playbooks for common failure scenarios
- Searching HSDES for existing sightings before filing new ones

**Covers:** 4-phase triage flow, 12+ common failure signatures, debug tools (ITP/DCI, Saleae, Total Phase), 5 debug playbooks (device not enumerating, I3C abort recovery, power state stuck, UART traffic failure, S0ix blocked), HSDES sighting database integration, cross-platform recurring patterns, performance monitoring counters

---

### 6. FV-GenDebugger (General Debug + Wiki Knowledge)
**Purpose:** Leverage Confluence wiki knowledge bases and structured NGA failure triage for LPSS debugging

**When to use:**
- Searching for LPSS BKMs (Best Known Methods) and debug procedures in Confluence wikis
- Running full NGA failure triage on LPSS test suite failures (8-phase workflow)
- Analyzing BSOD/crash dumps, MCA errors, or platform-level failures affecting LPSS
- Cross-referencing LPSS failures with known issues documented in FVCommon or DebugEncyclopedia

**How to invoke:** Use the `FV-GenDebugger` sub-agent (agent type: `FV-GenDebugger`) via the Task tool.

**Key Capabilities for LPSS:**

#### a. Wiki Knowledge Search (Confluence)
Search FVCommon and DebugEncyclopedia wiki spaces for LPSS-related BKMs:
```bash
# Search for LPSS debug procedures
python <cwd>/.opencode/skill/securewiki/securewiki.py search "LPSS I2C debug" --spaces fvcommon,DebugEncyclopedia --user twai --json

# Search for S0ix LPSS blocker BKMs
python <cwd>/.opencode/skill/securewiki/securewiki.py search "S0ix LPSS blocker" --spaces fvcommon,DebugEncyclopedia --user twai --json

# Read a specific wiki page by ID
python <cwd>/.opencode/skill/securewiki/securewiki.py read <page_id> --user twai --json
```

**LPSS-relevant wiki search terms:**
- `LPSS I2C timeout`, `LPSS UART traffic failure`, `LPSS SPI FIFO underrun`
- `LPSS D3 entry failure`, `S0ix LPSS blocker`, `LPSS clock gating`
- `I3C abort recovery`, `I3C DAA failure`, `I3C chicken bit`
- `SerialIO enumeration`, `LPSS pad mode`, `LPSS power management`

> **IMPORTANT:** Never fabricate wiki content. Always cite the source page ID, title, and URL.

#### b. 8-Phase NGA Failure Triage (LPSS-adapted)

When triaging LPSS test failures from NGA, GenDebugger follows this structured workflow:

| Phase | Action | LPSS Focus |
|-------|--------|------------|
| 1. Identify | Get test scope (suite, station, project) | Filter for LPSS test groups |
| 2. Filter | Extract failed tests, get LogsPath/AxonId | Look for I2C/I3C/SPI/UART test names |
| 3A. Check links | Query NGA failure API for existing sighting links | Check if LPSS sighting already filed |
| 3B. Get logs | Retrieve via Axon API → UNC path → fallback | Prioritize LPSS register dumps in logs |
| 4. Analyze | Map fail step to log lines, scan with patterns | Apply LPSS-specific issue patterns (below) |
| 5. Scope | Summarize status across all tests | Group by controller type (I2C/I3C/SPI/UART) |
| 6. PMC check | Verify PMC firmware version | Critical for LPSS power gating issues |
| 7. MCA | Analyze Machine Check Architecture errors | Rare for LPSS but check for bus errors |
| 8. Resolution | Failure flags + wiki search + next steps | Search wiki for LPSS-specific workarounds |

#### c. LPSS-Specific Issue Detection Patterns

When scanning logs during Phase 4, look for these LPSS patterns in addition to the generic GenDebugger patterns:

| Pattern | Severity | Indicates |
|---------|----------|-----------|
| `IC_TX_ABRT_SOURCE.*0x[0-9a-fA-F]+` | HIGH | I2C transfer abort — decode the 16 abort reason bits |
| `NACK.*I2C\|I2C.*NACK` | HIGH | I2C address or data NACK |
| `D3.*timeout\|timeout.*D3\|PMCSR.*stuck` | HIGH | LPSS power state transition failure |
| `S0ix.*block\|block.*S0ix\|LPSS.*S0ix` | HIGH | LPSS preventing platform idle |
| `clock.*gate\|gate.*clock\|CGPG.*fail` | MEDIUM | Clock gating not working |
| `BUS_ENABLE.*stuck\|HC_CONTROL.*0x8` | HIGH | I3C controller stuck after abort |
| `TID.*mismatch\|response.*mismatch` | HIGH | I3C DMA queue corruption |
| `FIFO.*overflow\|FIFO.*underrun` | HIGH | SPI/UART FIFO error |
| `baud.*mismatch\|LCR.*wrong` | MEDIUM | UART configuration error |
| `pad.*mode\|PMode.*0\|GPIO.*native` | MEDIUM | Pad routing misconfiguration |
| `BAR.*0x0\|BAR.*not.*assign` | HIGH | PCI resource allocation failure |
| `Device.*ID.*0xFFFF\|not.*enumerat` | CRITICAL | Device not visible on PCI bus |

#### d. Log Analysis Priority for LPSS

When analyzing LPSS failures, check logs in this order:
1. **BSOD/crash dump** — check if LPSS driver (IntelLpss.sys, SerialIO) is in the stack
2. **Event Logs** — look for SerialIO/LPSS driver errors
3. **Test execution logs** — LPSS register dumps, traffic results
4. **PythonSV output** — Register read/write results, traffic pass/fail
5. **Framework logs** — VJT LPSS init errors, port discovery failures

---

## Common PythonSV Initialization for LPSS

When using PythonSV for LPSS register access:

```python
# Initialize PythonSV environment
import namednodes
from namednodes import *
import baseaccess

# Unlock ITP (Intel Trace Hub)
itp.unlock()

# Refresh silicon view
sv.refresh()

# Search for LPSS-related registers
lpss_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss",
    searchType="registers"
)

# Search for serial IO registers (alternative naming)
serial_io_regs = namednodes.sv.socket0.pcd.search(
    regexpression="serial.*io|serialio",
    searchType="registers"
)

# Print register paths
for reg in lpss_regs:
    print(reg)
```

### Platform-Specific LPSS Access Paths

**Example - Novalake Platform (verify actual port counts from HAS document):**

LPSS controllers are typically located in the die hierarchy (e.g., `socket0.pcd.lpss` for Novalake):

```python
# I2C Controllers - number varies by project
i2c0 = namednodes.sv.socket0.pcd.lpss.i2c0
i2c1 = namednodes.sv.socket0.pcd.lpss.i2c1
# Continue with i2c2, i2c3, etc. based on actual port count from HAS

# I3C Controllers - number varies by project
# Note: I3C naming convention may differ - verify on platform
i3c0 = namednodes.sv.socket0.pcd.lpss.i3c0  # May not be enumerated by default
# Continue with i3c1, i3c2, etc. based on actual port count from HAS

# SPI Controllers - number varies by project
spi0 = namednodes.sv.socket0.pcd.lpss.spi0
spi1 = namednodes.sv.socket0.pcd.lpss.spi1
# Continue with spi2, spi3, etc. based on actual port count from HAS

# UART Controllers - number varies by project
# Important: UARTs may appear as HSUART (High-Speed UART) in PythonSV
hsuart0 = namednodes.sv.socket0.pcd.lpss.hsuart0
hsuart1 = namednodes.sv.socket0.pcd.lpss.hsuart1
# Continue with hsuart2, hsuart3, etc. based on actual port count from HAS

# Each controller has a 'cfg' component for configuration space
i2c0_cfg = namednodes.sv.socket0.pcd.lpss.i2c0.cfg
# Access registers like: i2c0_cfg.cfg_hi0.read()
```

## General LPSS Debugging Workflow

> **TIP:** Load `docs/lpss_reference_sheets.md` for step-by-step triage decision trees and bring-up checklists.

1. **Identify the affected port** from failure symptoms or test results
2. **Check known issues first** — load `docs/lpss_known_issues.md` and search for matching symptoms
3. **Check hardware config** using `fv-lpss/config-checkout` — enumeration, registers, pad routing
4. **Analyze power states** using `fv-lpss/power-state` — D3, clock gating, S0ix blockers
5. **Cross-reference failures** using `fv-lpss/failure-analysis` with NGA/sightings
6. **Deep triage with GenDebugger** using `FV-GenDebugger` sub-agent — when steps 2-5 don't resolve the issue:
   - Search Confluence wikis (FVCommon, DebugEncyclopedia) for LPSS BKMs and known workarounds
   - Run the full 8-phase NGA triage workflow for structured failure analysis
   - Analyze BSOD/crash dumps if the failure involves a system crash with LPSS driver in the stack
   - Check PMC firmware version (critical for LPSS power gating / CGPG issues)
   - Scan MCA errors for bus-level faults affecting LPSS controllers

### Common Failure Signatures (Quick Reference)

| Symptom | Likely Root Cause | First Action |
|---------|-------------------|--------------|
| Device ID = 0xFFFF | Not enumerated, in D3, or fuse-disabled | `fv-lpss/config-checkout` → check BDF + PMCSR |
| Register reads 0x00000000 | BAR not assigned or wrong address | `fv-lpss/config-checkout` → check BAR allocation |
| I2C NACK | Wrong address, pad mode, or device absent | `fv-lpss/config-checkout` → check IC_TAR + pad |
| I2C TX_ABRT (IC_TX_ABRT_SOURCE) | Decode 16 abort reason bits | Read 0x80, check `docs/i2c/` validation ref |
| I3C BUS_ENABLE stuck at 1 | Abort with chicken_bit=3 | Check gen_pvt_high_regrw4 bits[1:0], see BUG-001 in known_issues |
| I3C TID mismatch | DMA control queue not cleared | Same chicken bit issue — BUG-001 |
| I3C DAA failure | Target not responding to ENTDAA | Check HC_CONTROL, IBI regs, bus pullups |
| I3C HALT state | Broadcast NACK, abort, or HDR error | Check PRESENT_STATE_DEBUG(0x14C) bits[21:16] |
| SPI FIFO underrun | Clock too fast or DMA misconfigured | Check SCTRL + DMA regs |
| UART TX timeout | Baud mismatch or flow control stuck | Check LCR + MCR registers |
| D3 entry timeout | Outstanding DMA or pending interrupt | `fv-lpss/power-state` → check pending IRQs |
| S0ix blocked by LPSS | Controller not in D3 | `fv-lpss/power-state` → PMCSR all controllers |
| Clock not gated in idle | CGPG not enabled or PMC misconfigured | `fv-lpss/power-state` → PMC CLK_GATE regs |
| PMode=0 on native pin | Pad stuck in GPIO mode | `fv-lpss/config-checkout` → pad ownership |

> **See also:** `docs/lpss_known_issues.md` for HSDES sightings with full reproduction steps and workarounds.

Always correlate hardware state (registers, power, clocks) with software state (driver status, ACPI, BIOS) and test results. Use GenDebugger's wiki search to find BKMs before filing new sightings.

---

## VJT LPSS Traffic Scripts

**Location:** `C:\pythonsv\novalake\vjt\lpss`

**IMPORTANT:** Always show the complete printout when running UART traffic tests or any LPSS validation scripts. Users need to see the detailed output including:
- Configuration summary (port, size, mode, loopback, speed)
- Byte-by-byte sent data (in hex format)
- Byte-by-byte received data (in hex format)
- Traffic completion status and return code

The VJT (Validation and Joint Test) LPSS scripts provide comprehensive traffic testing capabilities for all LPSS controllers:

### Available Scripts:
- **lpss_uart.py**: UART traffic generation (PIO and DMA modes, internal/external loopback)
- **lpss_i2c.py**: I2C traffic generation (master/slave modes, speed configurations)
- **lpss_i3c.py**: I3C traffic generation (SDR/HDR modes, dynamic addressing)
- **lpss_spi.py**: SPI traffic generation (full-duplex, multiple chip selects)
- **lpss_main.py**: Entry point that initializes all LPSS ports in `lhc.ports` list
- **lpss_class.py**: Base classes for LPSS port objects

### Using VJT LPSS Scripts:

**Quick UART Traffic Test:**
```bash
python C:\git\applications.ai.ocode.market.skills\.opencode\skill\fv-lpss\run_uart_traffic.py <port> <size>
```

**Command Format:**
- **Syntax:** `python run_uart_traffic.py <port> <size> [options]`
- **Required Arguments:**
  - `<port>`: UART port number (0, 1, 2 for UART0, UART1, UART2)
  - `<size>`: Number of bytes to transfer (e.g., 8, 32, 100, 1024)
- **Optional Arguments:**
  - `--dma`: Enable DMA mode (default: PIO mode)
  - `--channel N`: DMA channel number (default: 0)
  - `--dma-intr`: Enable DMA interrupt checking
  - `--speed N`: Baud rate (default: 115200)
  - `--external`: Use external loopback (default: internal)

**Tested Examples:**
```bash
# UART0, 32 bytes - TESTED ✓
python run_uart_traffic.py 0 32

# UART1, 32 bytes - TESTED ✓
python run_uart_traffic.py 1 32

# UART2, 8 bytes - TESTED ✓
python run_uart_traffic.py 2 8

# UART0, 1KB with DMA
python run_uart_traffic.py 0 1024 --dma

# UART1, 100 bytes, external loopback
python run_uart_traffic.py 1 100 --external
```

**EXECUTION PROTOCOL:**
When user provides variables (e.g., "run uart1 with 32 bytes" or "test uart2 8 bytes"):
1. Parse port number and size from user input
2. Execute: `python run_uart_traffic.py <port> <size>`
3. **ALWAYS show the complete printout** with all sections:
   - Test configuration
   - PythonSV initialization status
   - Port discovery confirmation
   - Traffic details (mode, baudrate, parity, etc.)
   - Sent bytes (in hex format)
   - Received bytes (in hex format)
   - Traffic completion status
   - Success/failure interpretation
4. Validate: Check that sent bytes match received bytes

**Direct Usage (from vjt.lpss):**
```python
import sys
sys.path.insert(0, r'C:\pythonsv\novalake')

from vjt.lpss import lpss_main as lmain

# Find UART0 port
uart0 = next(p for p in lmain.lhc.ports if p.protocol == 'uart' and p.port_number == 0)

# Run internal loopback traffic: mode=3, size=100 bytes, speed=115200, PIO mode
result = uart0.ioctl(mode=3, size=100, internal=1, speed=115200, dma=False)

if result == 0:
    print("✅ UART traffic test passed!")
else:
    print(f"❌ UART traffic test failed with code: {result}")
```

**Traffic Modes:**
- **Mode 3 (TRAFFIC_LOOPBACK)**: Internal loopback - TX data is looped back to RX internally
- **Internal=1**: Hardware internal loopback via MCR register
- **Internal=0**: External loopback (requires physical TX-RX connection)

---

## BIOS XML Knob Dump (NVL/PTL)

> **Full reference:** `docs/bios_xml_dump.md` | **Script:** `dump_bios_xml.py`

NVL and PTL use `XmlCliType="Lite"` BIOS — standard `cli.savexml()` fails. Use the dedicated script instead:

```bash
# Dump all BIOS knobs (~4,800 knobs) to XML + JSON:
C:\Python310\python.exe <skill_root>\fv-lpss\dump_bios_xml.py

# Output: C:\temp\NVL_BIOS_knobs.xml and C:\temp\NVL_BIOS_knobs.json
```

**Key LPSS knobs to check:** `PchSerialIoI2cMode[0-5]`, `PchSerialIoSpiMode[0-2]`, `PchSerialIoUartMode[0-2]`, `PchSerialIoI3cMode[0-3]` (0=Disabled, 1=PCI, 2=ACPI)

**To change BIOS knobs** (requires OS-booted PythonSV session):
```python
import pysvtools.xmlcli.nvram as nvram
ram = nvram.getNVRAM()
ram.pull()
ram.PchSerialIoI2cMode0 = 1   # Enable I2C0 in PCI mode
ram.push()                      # Apply on next reboot
```

> **NOTE:** `CurrentVal` in dump may show 0x00 due to SMI timeout in DCI halt mode. Default values are accurate. See `docs/bios_xml_dump.md` for full details and troubleshooting.

---

## GitHub Sync Workflow

The FV-LPSS skill files and agent definition are version-controlled in GitHub. Use this workflow to commit and push changes.

### Repository Information

| Property | Value |
|----------|-------|
| **Upstream Repo** | `intel-innersource/applications.ai.ocode.market.skills` |
| **Fork Repo** | `KongJiaWen/applications.ai.ocode.market.skills` |
| **Local Clone** | `C:\git\applications.ai.ocode.market.skills` |
| **Working Dir** | `.opencode/` (agent/, skill/ subdirectories) |
| **Branch Convention** | `fv-lpss-push` for LPSS changes |

### Quick Sync (Commit + Push + PR)

```bash
# 1. Stage FV-LPSS files
git add agent/FV/FV-LPSS.md skill/fv-lpss/ skill/codesign/SKILL.md

# 2. Commit with descriptive message
git commit -m "Update FV-LPSS agent/skill: <brief description>"

# 3. Push to fork (NOT origin — user lacks write access to intel-innersource)
git push fork fv-lpss-push

# 4. Create cross-fork PR via GitHub API (see agent file for PowerShell script)
```

### Key Files to Sync

| File/Directory | Purpose |
|----------------|---------|
| `agent/FV/FV-LPSS.md` | Main FV-LPSS agent definition |
| `skill/fv-lpss/SKILL.md` | Root LPSS debugging skill |
| `skill/fv-lpss/config-checkout/SKILL.md` | Config checkout sub-skill |
| `skill/fv-lpss/power-state/SKILL.md` | Power state sub-skill |
| `skill/fv-lpss/failure-analysis/SKILL.md` | Failure analysis sub-skill |
| `skill/fv-lpss/run_uart_traffic.py` | UART traffic test script |
| `skill/fv-lpss/reset_target.py` | Target reset utility |
| `skill/fv-lpss/auto_reset_target.py` | Auto reset with state check |
| `skill/fv-lpss/check_port_mapping.py` | Port-to-pad validation |
| `skill/fv-lpss/dump_bios_xml.py` | BIOS XML knob dump (NVL/PTL) |
| `skill/codesign/SKILL.md` | Co-Design access skill |

### Authentication Notes

- **PAT token** (`ghp_OZY...`) has `repo` scope but NO write access to `intel-innersource` org
- **Workaround**: Push to **fork** (`KongJiaWen/...`) then create **cross-fork PR**
- **Remote setup**: `origin` = upstream (read-only), `fork` = user's fork (read-write)
- If `fork` remote doesn't exist, add it:
  ```bash
  git remote add fork https://<PAT>@github.com/KongJiaWen/applications.ai.ocode.market.skills.git
  ```
- If fork doesn't exist on GitHub, create via API (see agent file for PowerShell script)

### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Push 403 to origin | No write access to intel-innersource | Push to `fork` remote instead |
| Push 404 | Fork doesn't exist yet | Create fork via GitHub API first |
| gh CLI not found | Not installed on lab machine | Download from GitHub releases (see agent file) |
| PAT token expired | Token revoked or rotated | Generate new PAT with `repo` scope, authorize for SSO |
| PR creation 422 | PR already exists for this branch | Check existing PRs or use a new branch name |

---

---

## Cross-Platform PythonSV Access Paths

LPSS validation spans multiple Intel platforms. Each platform has different PythonSV base paths and naming conventions.

### Platform Path Reference

| Platform | Die | PythonSV Base | LPSS Root | Python Executable |
|----------|-----|---------------|-----------|-------------------|
| **Novalake (NVL)** | PCD-H | `nn.sv.socket0.pcd` | `socket0.pcd.lpss` | Local PythonSV |
| **Novalake (NVL)** | PCH-S | `nn.sv.socket0.pch` | `socket0.pch.lpss` | Local PythonSV |
| **Panther Lake (PTL)** | PTL-H | `nn.sv.socket0.soc` | `socket0.soc.lpss` | `C:\Python310\python.exe` |

> **CRITICAL:** PTL uses `socket0.soc` — NOT `socket0.pcd` (NVL) or `socket0.pch` (NVL PCH-S). Using the wrong base path will give "attribute not found" errors.

### PTL I3C Register Access

PTL I3C controllers have a **different register hierarchy** than NVL:

```python
# PTL I3C — HCI registers are under .lpio (no .cfg sub-node)
i3c0 = nn.sv.socket0.soc.lpss.i3c0_0.lpio

# Key HCI registers (directly under .lpio):
i3c0.hc_control        # HC_CONTROL — bit31=BUS_ENABLE, bit29=ABORT
i3c0.present_state     # Bus state
i3c0.reset_control     # Soft reset
i3c0.hci_version       # HCI version (expect 0x00000100 for v1.0)
i3c0.intr_status       # Interrupt status
i3c0.command_queue_port  # Write commands here
i3c0.response_queue_port # Read responses here

# PTL I3C DMA controller
dma = nn.sv.socket0.soc.lpss.i3c0cl_dma
```

> **NOTE:** PTL I3C has **no `.cfg` sub-node** for PCI config space at the I3C register level. PCI config is accessed differently than NVL.

### PTL I3C Controller Mapping

| Controller | Ports | BDF | PythonSV HCI Path |
|-----------|-------|-----|-------------------|
| I3C Controller #1 | I3C0 + I3C1 | dev17:func0 | `soc.lpss.i3c0_0.lpio` |
| I3C Controller #2 | I3C2 + I3C3 | dev17:func1 | `soc.lpss.i3c1_0.lpio` |

> **HAS-verified (LPSS_HAS.html "Table: Slice Configuraton"):** PTL has **4 I3C instances under 2 controllers** — identical to NVL. Each controller hosts 2 I3C instances sharing an 8K MMIO BAR. The only difference is I3C core clock: PTL=100 MHz, NVL=200 MHz.

### Remote PythonSV Execution (PowerShell Remoting)

For running PythonSV on remote lab hosts (e.g., PTL boards):

```powershell
# Simple register read on remote host
powershell -Command "Invoke-Command -ComputerName <HOSTNAME> -ScriptBlock {
    & 'C:\Python310\python.exe' -c @'
import namednodes as nn
nn.sv.refresh()
val = nn.sv.socket0.soc.lpss.i3c0_0.lpio.hc_control.read()
print('HC_CONTROL = 0x%08X' % val)
'@
}"
```

> **CRITICAL RULE:** When running PythonSV remotely via PowerShell:
> - **NEVER use Python f-strings** (`f"..."` with `{var}`) — PowerShell strips the curly braces
> - **ALWAYS use `%` formatting** (`'0x%08X' % val`) or `.format()` with escaped braces
> - For multi-line scripts, use PowerShell `@' ... '@` here-strings
> - For file transfer to remote hosts, use `Invoke-Command` with `$using:` or PSSession + `Set-Content`

### Transferring Test Scripts to Remote Hosts

When a test script is too complex for inline execution:

```powershell
# Method: Create PSSession, write file via Set-Content, then execute
$session = New-PSSession -ComputerName <HOSTNAME>
$scriptContent = Get-Content -Path "C:\temp\local_script.py" -Raw
Invoke-Command -Session $session -ScriptBlock {
    param($content)
    Set-Content -Path "C:\temp\remote_script.py" -Value $content
} -ArgumentList $scriptContent
Invoke-Command -Session $session -ScriptBlock {
    & 'C:\Python310\python.exe' 'C:\temp\remote_script.py'
}
Remove-PSSession $session
```

---

## I3C Chicken Bit Register (gen_pvt_high_regrw4)

### Overview

The I3C DMA controller has a **chicken bit register** that controls abort recovery behavior. This register is critical for debugging I3C abort-related failures.

### Register Details

| Property | Value |
|----------|-------|
| **Formal name** | GEN_REGRW8 (XML), gen_pvt_high_regrw4 (PythonSV) |
| **Offset** | 0x61C in IOSF2AXI private config space |
| **Size** | 32 bits, RW |
| **HW Default** | 0x00000000 |
| **Mechanism** | Output as OOB signal `oob_gen_prv_high_rw_reg4` to DWC I3C DMA controller IP |

### PythonSV Access Paths

```python
# NVL (PCD-H)
cb_nvl = nn.sv.socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4

# PTL (PTL-H)
cb_ptl = nn.sv.socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
```

### Key Bit Fields

| Bits | Field | Description |
|------|-------|-------------|
| [1:0] | DMAC_NO_CLEAR_CTRL_Q_ON_ABORT | Controls whether DMA controller clears control queue on abort |

| Value | Behavior |
|-------|----------|
| **0** | Clear control queue on abort (**working/workaround**) — abort recovery works correctly |
| **3** | Don't clear control queue on abort (**buggy default in some steppings**) — causes I3C abort recovery failures |

> **IMPORTANT:** The bit-level mapping is defined in the **Synopsys DWC MIPI I3C IP Databook** (vendor-confidential), NOT in the Intel HAS. Co-Design cannot provide bit-field details for this register.

### VJT Framework Usage

The VJT LPSS framework sets this register during I3C initialization:
- **DMA mode**: Sets register to **0** (clear queue on abort — safe)
- **PIO mode**: Sets register to **5**

```python
# From vjt/lpss/lpss_i3c.py (both NVL and PTL):
# Line ~136-150: During I3C port init for DMA mode
chicken_bit_reg.write(0)  # Enable clear-queue-on-abort for DMA mode
```

### Known Sighting: HSDES 18044213731

**Title:** "I3C fails to recover after ABORT with DMAC_NO_CLEAR_CTRL_Q_ON_ABORT=3 (the default)"

**3 symptoms when chicken_bit[1:0]=3:**
1. Subsequent commands/transfers abort after the first abort
2. TID (Transaction ID) mismatch on responses
3. BUS_ENABLE bit (HC_CONTROL bit31) gets stuck at 1 — cannot be cleared

**Workaround:** Set chicken_bit[1:0] to 0

**Reproduction confirmed on:**
- PTL-H B0, WOS (Windows OS), PythonSV via IPC
- Symptom 3 (BUS_ENABLE stuck) confirmed; Symptoms 1 & 2 require I3C target device on bus

See `fv-lpss/failure-analysis` skill for detailed reproduction methodology.

### Quick Diagnostic Script

```python
# Read chicken bit on any platform
import namednodes as nn
nn.sv.refresh()

# Choose path based on platform:
# NVL: socket0.pcd.lpss...
# PTL: socket0.soc.lpss...
cb = nn.sv.socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
val = cb.read()
print('Chicken bit = 0x%08X' % val)
print('DMAC_NO_CLEAR_CTRL_Q_ON_ABORT = %d' % (val & 3))
if (val & 3) == 3:
    print('WARNING: Buggy value! I3C abort recovery will fail.')
    print('Apply workaround: cb.write(0)')
elif (val & 3) == 0:
    print('OK: Workaround applied or HW default is safe.')
```

---

## Related Skills

- **FV-GenDebugger**: General debug agent with Confluence wiki knowledge — search FVCommon & DebugEncyclopedia for LPSS BKMs, run 8-phase NGA failure triage, analyze BSOD/MCA errors, check PMC firmware
- **pysv**: PythonSV register access and silicon validation
- **nga**: NGA test automation and failure tracking
- **sighting-info**: HSDES sighting lookup
- **hsdes**: Direct HSDES query
- **onebkc**: BKC/firmware version information
- **securewiki**: Confluence wiki access (used by FV-GenDebugger for wiki searches)
- **github-copilot-token**: GitHub authentication token info (auth.json at `~/.local/share/opencode/auth.json`)
