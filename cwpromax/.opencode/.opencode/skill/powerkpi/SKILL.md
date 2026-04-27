---
name: PowerKPIagent
description: This agent will help to run power KPI related workloads
license: MIT
---

# PowerKPI Agent - Power Validation Automation and Analysis

## Overview

The **PowerKPI Agent** is an AI-powered assistant for Intel platform power validation engineers. It automates the execution, analysis, and visualization of Battery Life KPI and Regulatory KPI workloads, providing comprehensive power trend analysis with actionable insights.

## Core Capabilities

### 1. Automated Workload Execution (Hopper Framework)

Execute power validation workloads through the **Hopper Automation Framework** on Intel client platforms:

**Supported Workloads:**
- **IDON (Idle Display On)**: Screen-on idle power measurement
- **CMS (Connected Modern Standby)**: Screen-off modern standby with network connectivity
- **ICOB (Intel Custom Offline Browsing)**: Offline web browsing power consumption
- **Busy Idle**: Active system with background tasks
- **YouTube Streaming**: Video playback power measurement
- **Netflix Playback**: Streaming video power consumption
- **MobileMark30 (MM30)**: MobileMark 30 battery life and application responsiveness power measurement
- **Microsoft Teams**: Video conferencing power measurement
- **S5 (Soft Off)**: System shutdown power measurement

**Execution Features:**
- Single workload or batch execution
- Configurable quiesce and capture time
- Multiple instrumentation options (DAQ, SocWatch, PerfTracer, IntelPowerThermalAnalyzer)
- Automatic IFWI flashing and platform setup
- Proxy configuration and Windows optimization
- BIOS knob extraction and validation

### 2. Multi-Instrumentation Support

#### DAQ (Data Acquisition)
- **Purpose**: High-precision power rail measurements via hardware instrumentation (FlexLogger)
- **Measurements**: Individual power rails (I_VCCCORE, I_VCCGT, I_VDDQ, etc.)
- **Resolution**: Sub-millisecond sampling
- **Output**: TDMS files with time-series power data (up to 49 power rails)
- **Use Case**: Detailed power rail analysis, correlating power spikes with platform events

#### SocWatch
- **Purpose**: Software-based platform power state monitoring
- **Measurements**:
  - Package/Core C-state residency (PC2, PC3, PC6, PC10, C0, C6, C7)
  - CPU frequency and utilization
  - Power limits and throttling
  - PMC (Power Management Controller) events
  - Wake sources and interrupts
- **Output**: CSV files with aggregated statistics (Automation_Summary.csv)
- **Use Case**: C-state residency validation, wake event analysis, power state debugging

#### PerfTracer (Intel Power/Thermal Analyzer)
- **Purpose**: System-wide power and thermal tracing
- **Measurements**: Package power, CPU power, GPU power, memory power, thermal data
- **Resolution**: High-frequency sampling with ETW (Event Tracing for Windows)
- **Output**: ETL trace files for offline analysis
- **Use Case**: Thermal correlation, power domain breakdown, performance analysis
- **Note**: NOT used in Regulatory KPI workloads (YouTube, Netflix). Battery Life KPI only.

#### IntelPowerThermalAnalyzer (IPTA)
- **Purpose**: Intel-specific power and thermal telemetry
- **Measurements**: Platform power, SoC power, DRAM power, package temperature
- **Integration**: Works with SocWatch for combined analysis
- **Use Case**: Platform-level power validation, thermal management verification

#### Intec (Temperature Controller)
- **Purpose**: Control the DUT (Device Under Test) junction/ambient temperature during power measurement using an Intec thermal controller
- **When to use**: When temperature-controlled testing is required — especially for regulatory KPI workloads and thermal sensitivity analysis
- **Hardware requirement**: Intec unit must be physically connected to the station and the DUT. If not present, skip `-intc` flag entirely.

**Intec Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-intc` | Yes (to enable) | Invokes the Intec instrument |
| `-intec_sp <°C>` | Yes | Sets the target temperature setpoint in °C |
| `--intec_disarm` | Optional | Keeps Intec temperature active even after the testline completes (does not reset to ambient) |
| `-intec_cfg <file>` | Optional | Path to a TDAU configuration XML file for advanced Intec setup |
| `-intec_acc <±°C>` | Optional | Intec accuracy tolerance. Default is ±0.5°C. Increase (e.g. `5`) for older Intec units that cannot reach tight accuracy |

**Temperature Setpoints by Workload:**

| Workload | Temperature |
|----------|------------|
| IDON | 25°C |
| CMS | 25°C |
| BusyIdle | 25°C |
| YouTube | 40°C |
| Netflix | 40°C |
| MobileMark30 (MM30) | 40°C |
| Catapult / ICOB | 40°C |
| S5 | 25°C |

**Sample Intec command fragments:**
```bash
# Basic: set to 25°C
-intc -intec_sp 25

# Keep temperature after test completes
-intc -intec_sp 40 --intec_disarm

# With TDAU config and relaxed accuracy (for older units)
-intc -intec_sp 40 -intec_cfg MTLP_Intec.xml -intec_acc 5
```

> **Note:** `-intc` flags are appended to the **end** of the workload command, after all other instrumentation flags.

### 3. Post-Processing and Visualization

#### Interactive Dashboard Generator (GUI)
**Current Version:** v3.2 with GENI AI-Powered Trend Analysis

**Features:**
- **5-Tab Workflow**:
  1. **Folder Selection**: Browse and scan `C:\_hopper_results` for workload data
  2. **Power Rails Selection**: Filter and select power rails (DAQ/FlexLogger data)
  3. **SocWatch Metrics Selection**: Filter and select C-states, frequencies, residencies
  4. **Workload Selection**: Select workloads by full folder names (with timestamps)
  5. **Graph Type & Generate**: Choose visualization, enable AI analysis, export options

- **6 Graph Types**:
  - **Bar Chart**: Compare metrics across workloads
  - **Grouped Bar Chart**: Side-by-side metric comparison
  - **Line Graph**: Trend analysis and patterns
  - **Scatter Plot**: Distribution and correlation analysis
  - **Heatmap/Matrix**: All metrics vs all workloads
  - **Box Plot**: Statistical distribution (min/max/quartiles)

- **Data Source Selection**:
  - **results.json**: Aggregated data (FlexLogger + SocWatch combined)
  - **TDMS Raw Files**: Time-series power rail data from FlexLogger

- **Export Options**:
  - **Excel (.xlsx)**: Tabular data with workload names and metrics
  - **HTML (Static)**: Standalone interactive Plotly dashboards

#### Command-Line Tools
- `parse_results_to_excel.py`: Batch convert results.json to Excel reports
- `generate_interactive_html_report.py`: CLI dashboard generator
- `plot_tdms_power_rails.py`: TDMS time-series plotter (supports 49 power rails)

### 4. AI-Powered Trend Analysis (GENI Integration)

**NEW in v3.2:** Integration with Intel GENI (Generative Engine for Intel) for automated power trend analysis.

**Capabilities:**
- **Per-Workload Summaries**: Detailed analysis for each workload with trend overview
- **Cross-Workload Comparison**: Automatic ranking and efficiency comparison
- **Separated Analysis**: Power rails analyzed separately from SocWatch metrics
- **5-Section Structured Output**:
  1. **Executive Summary**: High-level findings across all workloads
  2. **Per-Workload Analysis**: Individual workload behavior, trends, health assessment
  3. **Cross-Workload Comparison**: Power efficiency ranking, delta analysis
  4. **Anomaly Detection**: Outliers, unexpected values, inconsistencies
  5. **Actionable Recommendations**: Debug steps, BIOS knobs, configuration changes

**Two Operating Modes:**
- **Mode 1 (Manual)**: GUI generates dashboard → User asks agent to process GENI analysis
- **Mode 2 (Automatic)**: User asks agent directly → Agent generates dashboard with GENI insights

**Benefits:**
- 93% time savings (45 min → 2 min per analysis)
- 100% metric coverage
- Standardized reporting format
- Leverages GENI's Intel platform knowledge
- No separate authentication (uses MCP)

### 5. Software Package Management (Chocolatey)

#### SUT Configuration
- **IP Address**: 192.168.137.5
- **Credentials**: Administrator / (empty password)
- **Chocolatey Path**: `C:\ProgramData\chocolatey\bin\choco.exe` (not in system PATH — use full path)
- **Chocolatey Version**: 0.10.15
- **Source**: https://ubit-artifactory-or.intel.com/artifactory/api/nuget/occ-nuget-repo

> **Always use PsExec for Chocolatey operations** (PowerShell remoting not available on this SUT).

#### Chocolatey Setup Commands

##### Configure Chocolatey Source
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe source add -n=occ-nuget-repo -s=https://ubit-artifactory-or.intel.com/artifactory/api/nuget/occ-nuget-repo"
```

##### Configure IP Address (if needed)
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "netsh interface ipv4 set address name=\"Ethernet\" static 192.168.137.5 255.255.255.0 192.168.137.1"
```

##### Disable Proxy in Registry (HKCU)
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "reg add \"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\" /v ProxyEnable /t REG_DWORD /d 0 /f"
```

##### Disable Proxy in Registry (HKLM)
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "reg add \"HKLM\Software\Microsoft\Windows\CurrentVersion\Internet Settings\" /v ProxyEnable /t REG_DWORD /d 0 /f"
```

#### Install Python 3.13.3 (Prerequisite — MUST be first)

```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install python313 --version 3.13.3 --force -y"
```

#### Install Python Packages

```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-future --version 1.0.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-lxml --version 5.3.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-numpy --version 2.2.2 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-pandas --version 2.2.3 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-prettytable --version 3.14.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-psutil --version 6.1.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-pywin32 --version 308.0.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-pywinauto --version 0.6.9 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-selenium --version 4.28.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-setuptools --version 75.8.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-six --version 1.17.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-typing-extensions --version 4.12.2 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-urllib3 --version 2.3.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-wheel --version 0.45.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-wmi --version 1.5.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install py3-xmlcli --version 2.2.2 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install python310-defusedxml --version 0.7.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install python310-websocket_client --version 1.8.0.20241129 --force -y"
```

#### Install Workload Tools and Applications

```bash
# Validation and monitoring tools
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install socwatch --version 2025.7.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install wdtf --version 10.0.19041.20200728 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install wmic --version 10.0.26100 --force -y"

# Workload-specific packages
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install icob --version 2.24.03.13 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install IDC_PNP_Busy_idle_templates --version 0.0.4 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install IDC_PNP_Office_365_Offline --version 16.0.18730.20168 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install IDC_PNP_Spotify_install --version 0.0.4 --force -y"

# PTP (Power Test Platform) packages
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install ptpAutomationSettings --version 1.6.4 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install ptpConcurrencyContent --version 1.1.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install ptpVpb --version 1.1.1 --force -y"

# Remote access and communication
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install realvncserver --version 5.2.3.20211228 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install teamsOfflineInstaller --version 24074.2323.2827.4974 --force -y"

# Windows ADK and OS settings
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install web_ADK --version 2.0.5 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install OS_settings --version 0.6.0 --force -y"

# Utilities
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install notepadplusplus --version 8.9.2.1 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install 7zip --version 24.9.0 --force -y"

# Media codecs and browsers
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install AV1_youtube4k --version 1.1.60961.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install chrome-standalone --version 134.0.6998.89 --force -y"

# Development tools
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install git.install --version 2.49.0 --force -y"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install msedgedriver --version 111.0.1661.43 --force -y"
```

#### Retrieve Chocolatey Installation Logs

After installation, retrieve the log file to verify installation status:

```powershell
Copy-Item "\\192.168.137.5\C$\ProgramData\chocolatey\logs\chocolatey.log" -Destination "C:\MEP_Agent\chocolatey.log" -Force
```

#### Common Chocolatey Commands

```bash
# Install a specific package
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe install <package> --version <version> --force -y"

# Check if package installed
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe list --local-only <package>"

# List all installed packages
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe list --local-only"

# Upgrade package
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "C:\ProgramData\chocolatey\bin\choco.exe upgrade <package> -y"
```

**Installation Priority:**
1. **First**: Install `python313` (prerequisite for all py3-* packages)
2. **Second**: Python libraries (py3-*)
3. **Third**: Workload tools, browsers, and system tools
4. **Last**: Optional utilities

### 6. Platform Configuration Management

#### BIOS Knob Management via XMLCLI

XMLCLI allows reading, programming, and dumping BIOS knobs from Python. Each operation below is **independent** — use whichever you need.

> **Note:** The Python version in output paths may change (e.g., `Python310`, `Python313`). Adjust accordingly.

##### Check / Install XMLCLI (HOST — only if not present)

```bash
# Check if installed
pip show pysvtools.xmlcli

# If missing, install (upgrade setuptools first)
python -m pip install --upgrade setuptools
pip install pysvtools.xmlcli --force

# Alternative installs
python -m pip install xmlcli --proxy <proxy-url> --index-url <self-hosted-pypi-index>
python -m pip install <xmlcli-x.x.x.whl> --proxy <proxy-url>
python -m pip install <repo-url> --proxy <proxy-url>
```

##### Common Setup (run once per session)

```python
from pysvtools.xmlcli import XmlCli as x

# Set interface type for live SUT access
from xmlcli import XmlCli as cli
cli.clb._setCliAccess("winrwe")

# Verify XMLCLI is supported on the SUT (should return 0)
cli.clb.ConfXmlCli()
```

##### Save Platform XML (dump all BIOS knob values)

```python
from xmlcli import XmlCli as cli

# Save to default location: C:\Python3xx\Lib\site-packages\pysvtools\xmlcli\out\PlatformConfig.xml
cli.savexml()

# Save to a specific path
cli.savexml(r"path/to/file.xml")

# Offline: extract from a BIOS/IFWI binary → saved to default out/ folder
cli.savexml(0, r"path/to/ifwi-or-bios.bin")

# Offline: extract from binary → save to specific path
cli.savexml(r"path/to/file.xml", r"path/to/ifwi-or-bios.bin")
```

After running, open the output XML at:
`C:\Python310\Lib\site-packages\pysvtools\xmlcli\out\` *(adjust Python version)*

##### Read BIOS Knobs

```python
from xmlcli import XmlCli as cli

# Read and verify specific knobs against expected values
cli.CvReadKnobs("Knob_A=Val_1, Knobs_B=Val_2")

# Read all knobs from default config file (BiosKnobs.ini)
cli.CvReadKnobs()

# Offline: read knobs from a BIOS/IFWI binary
cli.CvReadKnobs("Knob_A=Val_1, Knobs_B=Val_2", r"path/to/ifwi-or-bios.bin")
cli.CvReadKnobs(0, r"path/to/ifwi-or-bios.bin")  # use default config file

# Use a custom config file instead of BiosKnobs.ini
cli.clb.KnobsIniFile = r"path/to/bios-config.ini"
```

Default config file: `<XmlCliRefScripts>/cfg/BiosKnobs.ini`

##### Program BIOS Knobs

```python
from xmlcli import XmlCli as cli

# Program specific knobs on the live SUT
cli.CvProgKnobs("Knob_A=Val_1, Knobs_B=Val_2")

# Program from default config file (BiosKnobs.ini)
cli.CvProgKnobs()

# Restore all knobs to factory defaults (live SUT only)
cli.CvLoadDefaults()

# Offline: patch a BIOS/IFWI binary (generates new binary with new defaults)
cli.CvProgKnobs(0, r"path/to/ifwi-or-bios.bin")
cli.CvProgKnobs("Knob_A=Val_1, Knobs_B=Val_2", r"path/to/ifwi-or-bios.bin")

# Use a custom config file
cli.clb.KnobsIniFile = r"path/to/bios-config.ini"
```

##### Patch Microcode into a BIOS Binary (Offline)

```python
import pysvtools.xmlcli.XmlCli as cli

BiosBin  = r'\\gar\ec\proj\sve\Local\PG\PTP\Users\anthony\mtls Ifwi\MTL_SS02_A0A0-MTPS_CPRF_SES0_0073001A_DBC_EN_2023WW7.5.00_With_WA_Pcode_Dcode.bin'
BiosOut  = r'\\gar\ec\proj\sve\Local\PG\PTP\Users\anthony\mtls Ifwi\MTL_SS02_A0A0-MTPS_CPRF_SES0_0073001A_DBC_EN_2023WW7.5.00_With_WA_Pcode_Dcode_Ucode.bin'
patchFile = r"\\pgcv04a-cifs.png.intel.com\mve_fvpg_001\MTLS_A0\cchiam\ucode\80000009\m_c6_a06c0_80000009.inc"

cli.ProcessUcode(Operation="UPDATE", BiosBinaryFile=BiosBin, UcodeFile=patchFile, outPath=BiosOut)
```

#### IFWI Flashing (via Hopper TTK Prestep)

> **IMPORTANT:** Always get explicit user approval before running any TTK command.

Flash IFWI and optionally clear CMOS using the Hopper TTK prestep:

```bash
python -m hopper.pnp.core.prestep.ttk --flash_ifwi <IFWI_PATH.bin> --flash_ifwi_offset <offset> --clear_cmos
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--flash_ifwi <path>` | Optional | Path to the IFWI binary to flash |
| `--flash_ifwi_offset <offset>` | Optional | Flash offset (omit to use default) |
| `--clear_cmos` | Optional | Clear CMOS after flashing |

**Examples:**

```bash
# Flash IFWI only
python -m hopper.pnp.core.prestep.ttk --flash_ifwi C:\ifwi\platform.bin

# Flash IFWI and clear CMOS
python -m hopper.pnp.core.prestep.ttk --flash_ifwi C:\ifwi\platform.bin --clear_cmos

# Clear CMOS only (no flash)
python -m hopper.pnp.core.prestep.ttk --clear_cmos

# Flash with a specific offset
python -m hopper.pnp.core.prestep.ttk --flash_ifwi C:\ifwi\platform.bin --flash_ifwi_offset <offset>
```

#### Power Plan Configuration
- **6 Presets**: Balanced, Power Saver, High Performance, Ultimate Performance, Panel Dim, Panel DIM Advanced
- **Custom**: Apply specific power settings via `powercfg`
- **Validation**: Verify active power plan before workload execution

### 7. Target Retrieval and Validation

#### High-Level Architecture Specifications (HAS)
- Query Co-DeSign for platform power targets
- Extract expected values for validation comparison
- Document: Package power, SoC power, specific rail targets

#### PVIM (Platform Validation Integration Management)
- Query HSDES Test Case workload parameters via GENI MCP
- Retrieve validation targets and acceptance criteria
- Map NGA test runs to PVIM test cycles

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Setup and Preparation Layer                │
│  Chocolatey Package Management (via PsExec)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SUT: 192.168.137.5 (Administrator / no password)     │   │
│  │ - Python 3.13.3 (core runtime)                       │   │
│  │ - Python packages: pandas, numpy, selenium, etc.     │   │
│  │ - Workload tools: socwatch, icob, ptp*, etc.         │   │
│  │ - Proxy configuration (enable/disable)               │   │
│  │ - BIOS knob extraction via XMLCLI                    │   │
│  │ - IFWI flashing via TTK3 (optional)                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Workload Execution Layer                   │
│  Hopper Framework → SUT (192.168.137.5)                     │
│  - IDON, CMS, ICOB, Busy Idle, YouTube, Netflix, MM30, Teams, S5  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Instrumentation Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   DAQ    │  │ SocWatch │  │PerfTracer│  │   IPTA   │   │
│  │FlexLogger│  │  (CSV)   │  │  (ETL)   │  │  (CSV)   │   │
│  │  (TDMS)  │  └──────────┘  └──────────┘  └──────────┘   │
│  └──────────┘                                                │
│     ↓ 49 power rails                                         │
│     ↓ Time-series @ ms resolution                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Results Aggregation Layer                  │
│  - results.json: Aggregated metrics (FlexLogger + SocWatch) │
│  - Raw TDMS: Time-series power rail data                    │
│  - CSV files: SocWatch C-state/frequency data               │
│  - ETL traces: PerfTracer/IPTA telemetry                    │
│  - All stored in: C:\_hopper_results\<workload_timestamp>\  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Post-Processing and Analysis Layer             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Dashboard GUI v3.2                                   │   │
│  │ - Parse results.json or TDMS                         │   │
│  │ - Filter power rails and SocWatch metrics            │   │
│  │ - Generate 6 graph types                             │   │
│  │ - Export to Excel/HTML                               │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ CLI Tools                                            │   │
│  │ - parse_results_to_excel.py                          │   │
│  │ - generate_interactive_html_report.py                │   │
│  │ - plot_tdms_power_rails.py                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   AI Trend Analysis Layer                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GENI MCP Integration                                 │   │
│  │ 1. Prepare enhanced data summary                     │   │
│  │    - Categorize: Power Rails vs SocWatch metrics     │   │
│  │    - Per-workload statistics                         │   │
│  │    - Cross-workload ranking                          │   │
│  │ 2. Query GENI via MCP (Focus Mode 12: VE Wiki)       │   │
│  │ 3. Receive 5-section structured analysis             │   │
│  │ 4. Inject insights into HTML dashboard               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Output Layer                            │
│  Interactive HTML Dashboard                                  │
│     - GENI Trend Analysis (above graph)                     │
│       • Executive Summary                                    │
│       • Per-Workload Analysis                                │
│       • Cross-Workload Comparison                            │
│       • Anomaly Detection                                    │
│       • Recommendations                                      │
│     - Plotly Interactive Graph (bar/line/scatter/heatmap)   │
│  Excel Report                                                │
│     - Workload names in column A                            │
│     - Metrics in subsequent columns                          │
│     - (Optional) Trend Analysis sheet                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Terminology

### Workloads
- **IDON**: Idle Display On - screen-on idle power
- **CMS**: Connected Modern Standby - screen-off idle with network
- **ICOB**: Intel Custom Offline Browsing - offline web browsing
- **Busy Idle**: System active with background tasks
- **MM30 (MobileMark30)**: MobileMark 30 battery life and responsiveness workload
- **S5**: Soft off - system shutdown state

### Power Rails (DAQ/FlexLogger)
- **I_VCCCORE**: Core domain current (compute cores)
- **I_VCCGT**: Graphics domain current (GPU)
- **I_VDDQ**: Memory I/O current
- **I_VNN**: System agent/uncore current
- **I_VCCINPUT**: Platform input current
- **V_BAT**: Battery voltage

### SocWatch Metrics
- **Package_C_State_PCx_Residency**: Percentage of time in package C-state (PC2, PC3, PC6, PC10)
- **Core_C_State_Cx_Residency**: Percentage of time cores spend in C-state (C0, C6, C7)
- **CPU_Frequency_Average**: Average CPU frequency across all cores
- **Wake_Source**: Hardware/software component causing wake from C-state
- **Interrupt_Count**: Number of interrupts during measurement period

### Power Metrics
- **Mean**: Average power consumption over measurement period
- **Min**: Minimum instantaneous power
- **Max**: Maximum instantaneous power (peak)
- **Std**: Standard deviation (stability indicator)

### Chocolatey Terms
- **Package**: Software application managed by Chocolatey (e.g., `python313`, `chrome-standalone`)
- **Version**: Specific release of a package
- **Source**: Repository URL for downloading packages (Intel Artifactory)
- **Force Install**: `--force` flag to reinstall even if already present
- **Silent Install**: `-y` flag for unattended installation
- **PsExec**: Remote command execution tool for running Chocolatey on SUT
- **Local-Only**: Check only installed packages (not available packages)

---

# Prerequisites

## Check and Install Hopper Packages (on HOST)

Do not run unless requested by the user.

```bash
# Check installation
pip show hopper.pnp.workloads

# Install / upgrade
pip install hopper.pnp.workloads -U
```

## Hopper Results Output Path

**Default Output Location:** `C:\_hopper_results`

All Hopper workload execution results are stored here. Each workload run creates a subdirectory based on the job name and timestamp.

```
C:\_hopper_results\
├── IDON_<timestamp>\
│   ├── results.json
│   ├── logs\
│   ├── power_data\
│   └── screenshots\
├── CMS_<timestamp>\
│   └── ...
└── ...
```

---

# Proxy Configuration

**IMPORTANT:** Proxy settings must be configured correctly **before** running workloads.

Two methods are available:
- **Method 1: PsExec** (from HOST — remote execution via PsExec to 192.168.137.5)
- **Method 2: PowerShell Remoting** (from HOST using `Invoke-Command` to 192.168.137.5)

If PsExec proxy configuration fails, use PowerShell Remoting.

### Proxy Requirements by Workload

| Workload | Auto Proxy | Manual Proxy | Notes |
|----------|------------|--------------|-------|
| **IDON** | Disable | Disable | Both proxies must be disabled |
| **CMS** | Disable | Disable | Both proxies must be disabled |
| **ICOB** | Disable | Disable | Both proxies must be disabled |
| **Busy Idle** | Enable | Disable | Auto proxy ON, Manual proxy OFF |
| **YouTube** | Disable | Enable | Manual proxy ON, Auto proxy OFF |
| **Netflix** | Disable | Enable | Manual proxy ON, Auto proxy OFF |
| **S5** | Disable | Disable | Both proxies must be disabled |

### Auto Proxy Disable

**Method 1: PsExec**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
```

**Method 2: PowerShell Remoting**
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Write-Host "Auto Proxy Disabled (HKCU and HKLM)"
}
```

### Auto Proxy Enable

**Method 1: PsExec**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force; Write-Host 'Auto Proxy Enabled (HKCU and HKLM)'"
```

**Method 2: PowerShell Remoting**
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force
    Write-Host "Auto Proxy Enabled with WPAD (HKCU and HKLM)"
}
```

### Manual Proxy Disable

**Method 1: PsExec**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

**Method 2: PowerShell Remoting**
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force
    Write-Host "Manual Proxy Disabled (HKCU and HKLM)"
}
```

### Manual Proxy Enable

**Method 1: PsExec**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Write-Host 'Manual Proxy Enabled (HKCU and HKLM)'"
```

**Method 2: PowerShell Remoting**
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force
    Write-Host "Manual Proxy Enabled with proxy.png.intel.com:911 (HKCU and HKLM)"
}
```

---

# Optional Presteps

> **IMPORTANT:** All presteps are OPTIONAL. Only run them when explicitly requested by the user.

## System Reboot Prestep

Reboots the SUT before running workloads to ensure a clean system state.

```bash
python -m hopper.pnp.core.prestep.reboot
```

**Example — Reboot then run IDON:**
```bash
python -m hopper.pnp.core.prestep.reboot
python -m hopper.pnp.workloads.oorja_idle -job "IDON" -rep 1 -comm_type ps_exec -dbg -qui 180s -dur 180s
```

## Windows Optimization Prestep

Configures Windows OS settings for optimal power measurement conditions.

```bash
python -m hopper.pnp.core.prestep.os_settings -pcn MTL -cm power -comm_type ps_exec
```

| Parameter | Description | Values |
|-----------|-------------|--------|
| `-pcn` | Platform code name | MTL, ARL, LNL, PTL, NVL |
| `-cm` | Configuration mode | `power` |
| `-comm_type` | Communicator | `ps_exec`, `efi`, `xml` |

## Virtualization Settings Prestep

Configures VBS (Virtualization-Based Security) and Hyper-V on the SUT. Typically disable before power testing for accurate baseline measurements.

```bash
# Disable both (recommended before power testing)
python -m hopper.pnp.core.prestep.virtualization_settings -vsm disable -hyperv disable

# Enable both
python -m hopper.pnp.core.prestep.virtualization_settings -vsm enable -hyperv enable

# Mixed
python -m hopper.pnp.core.prestep.virtualization_settings -vsm disable -hyperv enable
```

**Check VBS Status:**

*Method 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard | Select-Object -Property VirtualizationBasedSecurityStatus"
```

*Method 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard | Select-Object -Property VirtualizationBasedSecurityStatus
}
```

| VBS Value | Meaning |
|-----------|---------|
| 0 | Not enabled |
| 1 | Enabled but not running |
| 2 | Enabled and running |

**Check Hyper-V Status:**

*Method 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Get-ComputerInfo | Select-Object -Property HyperVisorPresent"
```

*Method 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Get-ComputerInfo | Select-Object -Property HyperVisorPresent
}
```

> After changing virtualization settings, use the reboot prestep: `python -m hopper.pnp.core.prestep.reboot`

## Hardware Acceleration (Edge)

**Disable:**

*Method 1: PsExec*
```bash
psexec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Force; Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Name 'HardwareAccelerationModeEnabled' -Type DWord -Value 0; Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue"
```

*Method 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Name 'HardwareAccelerationModeEnabled' -Type DWord -Value 0
    Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue
    Write-Host "Edge Hardware Acceleration Disabled"
}
```

**Enable (restore default):**

*Method 1: PsExec*
```bash
psexec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Name 'HardwareAccelerationModeEnabled' -ErrorAction SilentlyContinue; Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue"
```

*Method 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -Name 'HardwareAccelerationModeEnabled' -ErrorAction SilentlyContinue
    Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue
    Write-Host "Edge Hardware Acceleration Enabled (Default)"
}
```

---

# Usage

## Common Parameters

All workloads support the following common parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-comm_type` | Communication type: `ps_exec` (default), `efi`, `xml` | `-comm_type ps_exec` |
| `-dbg` | Enable debug mode for detailed logging | `-dbg` |
| `--quiesce` / `-qui` | System stabilization time before measurement | `-qui 180s` |
| `--duration` / `-dur` | Actual measurement capture window | `-dur 180s` |
| `-soc` | Enable SocWatch instrumentation | `-soc` |
| `--flexlogger` | Enable DAQ FlexLogger instrumentation | `--flexlogger` |
| `-job` | Custom job name for result organization | `-job IDON` |
| `-rep` | Number of repetitions (default: 1) | `-rep 3` |
| `-pysv` | Enable PythonSV instrument (required for PerfTracer) | `-pysv` |
| `-ptrc` | Enable PerfTracer register collection | `-ptrc` |
| `-ptc` | PerfTracer CSV configuration file path | `-ptc C:\path\to\config.csv` |

### Communicator Type

| Type | Description | When to Use |
|------|-------------|-------------|
| `ps_exec` | PsExec remote execution (default) | Standard Windows remote execution |
| `efi` | EFI communicator | UEFI/BIOS level communication |
| `xml` | Maple communicator (XMLCLI-based) | BIOS configuration via XMLCLI |

**Default**: Always use `ps_exec` unless the user explicitly requests otherwise.

### Instrumentation Combinations

Each workload (except S5) supports 4 instrumentation configurations:
1. **No instrumentation** (baseline)
2. **DAQ only**
3. **SocWatch only**
4. **DAQ + SocWatch**

S5 supports only 2 combinations: no instrumentation, or DAQ only (no SocWatch).

## SocWatch Feature Flags

When using `-soc`, the following feature flags are commonly used:

| Flag | Description |
|------|-------------|
| `--option pch-count-always` | Always count PCH events |
| `-f pcd-ip-active` | PCD IP active monitoring |
| `-f chipset-all` | All chipset monitoring |
| `-f s0ix-subs-res` | S0ix subsystem residency |
| `-f s0ix-subs-req` | S0ix subsystem requests |
| `-f cpu-hw` | CPU hardware monitoring |
| `-f cpu-pstate` | CPU P-state monitoring |
| `-f acpi-sstate` | ACPI S-state monitoring |
| `-f hw-cpu-hwp` | Hardware P-state (HWP) monitoring |
| `-f hw-cpu-cstate` | Hardware C-state monitoring |
| `-f os-cpu-cstate` | OS C-state monitoring |
| `-f sstate` | System S-state monitoring |
| `-f cpu` | General CPU monitoring |
| `-f dgfx-pkg-cstate` | Discrete graphics package C-state |
| `-f pmc-ip-status` | PMC IP status monitoring |
| `-f pch-slps0` | PCH SLP_S0 monitoring |
| `-f cpu-pkgc-cfg` | CPU package C-state configuration |
| `-f cpu-pkgc-dbg` | CPU package C-state debug |
| `-f soc-core-cstate-res` | SoC core C-state residency |
| `-f display` | Display monitoring |
| `-f tcss` | Type-C subsystem monitoring |
| `-f pcie-lpm` | PCIe link power management |
| `-f xhci` | xHCI (USB) monitoring |
| `-f device` | Device monitoring |
| `-r auto` | Auto-report generation |

## DAQ FlexLogger Parameters

When using `--flexlogger`:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-flex_cfg` | Path to FlexLogger project file | `-flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\...\project.flxproj` |
| `--flexlogger_sampling_rate` | Sampling rate in Hz | `--flexlogger_sampling_rate 1000` |
| `--flexlogger_keep_open` | Keep FlexLogger open after test | `--flexlogger_keep_open` |
| `--flexlogger_keep_raw` | Keep raw FlexLogger data | `--flexlogger_keep_raw` |
| `-flex_dis_down` | Disable FlexLogger download | `-flex_dis_down` |

## PerfTracer Parameters

> **Note:** PerfTracer is NOT used for Regulatory KPI workloads (YouTube, Netflix). Battery Life KPI only.
> All three flags must be used together: `-pysv -ptrc -ptc <config_file>`

| Parameter | Description |
|-----------|-------------|
| `-pysv` | Enable PythonSV instrument (required) |
| `-ptrc` | Enable PerfTracer register collection |
| `-ptc <file>` | Path to PerfTracer CSV configuration |

**Example — IDON with PerfTracer:**
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_perftracer" -rep 1 -pysv -ptrc -ptc C:\pythonsv\meteorlake\users\ptp\mtlp_perftracer_registers_pcie.csv -comm_type ps_exec -dbg -qui 180s -dur 180s
```

**Combined DAQ + SocWatch + PerfTracer:**
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_daq_soc_perf" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -pysv -ptrc -ptc C:\pythonsv\meteorlake\users\ptp\mtlp_perftracer_registers_pcie.csv -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -comm_type ps_exec -dbg -qui 180s -dur 180s
```

## Getting Help for Workloads

```bash
python -m hopper.pnp.workloads.oorja_idle -h
python -m hopper.pnp.workloads.kpi.connected_modern_standby -h
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -h
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -h
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -h
python -m hopper.pnp.workloads.kpi.netflix -h
python -m hopper.pnp.workloads.power.mobile_mark.mobilemark_30 -h
python -m hopper.pnp.workloads.S5 -h
```

## Power Plan Configuration

### Hopper Power Plan Switches

| Parameter | Description | Values |
|-----------|-------------|--------|
| `--target_power_mode` | AC or DC | `ac`, `dc` |
| `--target_power_plan` | Windows power plan | `balanced`, `high_performance`, `power_saver` |
| `--target_powerslider` | Slider position | `battery`, `balanced`, `performance` |

### Recommended Configurations

| Workload | Recommended Config | Switches |
|----------|--------------------|----------|
| IDON | AC Best Performance | `--target_power_mode ac --target_power_plan balanced --target_powerslider performance` |
| CMS | DC Best Battery | `--target_power_mode dc --target_power_plan balanced --target_powerslider battery` |
| ICOB | AC Best Balance | `--target_power_mode ac --target_power_plan balanced --target_powerslider balanced` |
| Busy Idle | AC Best Balance | `--target_power_mode ac --target_power_plan balanced --target_powerslider balanced` |
| YouTube | AC Best Performance | `--target_power_mode ac --target_power_plan balanced --target_powerslider performance` |
| Netflix | AC Best Performance | `--target_power_mode ac --target_power_plan balanced --target_powerslider performance` |
| S5 | AC Best Performance | `--target_power_mode ac --target_power_plan balanced --target_powerslider performance` |

### Manual Power Plan (powercfg)

**Check current plan:**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "powercfg /getactivescheme"
```

**List all plans:**
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "powercfg /list"
```

**Set by GUID:**

| Plan | GUID |
|------|------|
| Balanced | `381b4222-f694-41f0-9685-ff5bb260df2e` |
| High Performance | `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` |
| Power Saver | `a1841308-3541-4fab-bc81-f71556f20b4a` |

```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" cmd /c "powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e"
```

---

# Workload Commands

## 1. IDON (Idle Display On)

**Module:** `hopper.pnp.workloads.oorja_idle`
**Default Quiesce:** 180s | **Default Capture:** 180s
**Proxy:** Auto Proxy DISABLED, Manual Proxy DISABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
}
```

### 1.1 IDON Only
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON" -rep 1 -comm_type ps_exec -dbg -qui 180s -dur 180s
```

### 1.2 IDON + DAQ
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg -qui 180s -dur 180s
```

### 1.3 IDON + SocWatch
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_soc" -rep 1 -comm_type ps_exec -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg -qui 180s -dur 180s
```

### 1.4 IDON + DAQ + SocWatch
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -comm_type ps_exec -dbg -qui 180s -dur 180s
```

### 1.5 IDON + Intec (25°C)
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_intec" -rep 1 -comm_type ps_exec -dbg -qui 180s -dur 180s -intc -intec_sp 25
```

### 1.6 IDON + Intec + DAQ (25°C)
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg -qui 180s -dur 180s -intc -intec_sp 25
```

### 1.7 IDON + Intec + SocWatch (25°C)
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_intec_soc" -rep 1 -comm_type ps_exec -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg -qui 180s -dur 180s -intc -intec_sp 25
```

### 1.8 IDON + Intec + DAQ + SocWatch (25°C)
```bash
python -m hopper.pnp.workloads.oorja_idle -job "IDON_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -comm_type ps_exec -dbg -qui 180s -dur 180s -intc -intec_sp 25
```

---

## 2. CMS (Connected Modern Standby)

**Module:** `hopper.pnp.workloads.kpi.connected_modern_standby` (DAQ) / `pnpauto.connected_modern_standby_socwatch` (SocWatch)
**Default Quiesce:** 180s (120s screen-on) | **Default Capture:** 180s
**Proxy:** Auto Proxy DISABLED, Manual Proxy DISABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
}
```

### 2.1 CMS Only
```bash
python -m hopper.pnp.workloads.kpi.connected_modern_standby -job "CMS" -rep 1 -comm_type ps_exec -dbg -qui 180s --quiesce_screen_on 120s
```

### 2.2 CMS + DAQ
```bash
python -m hopper.pnp.workloads.kpi.connected_modern_standby -job "CMS_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg -qui 180s --quiesce_screen_on 120s
```

### 2.3 CMS + SocWatch
```bash
python -m pnpauto.connected_modern_standby_socwatch -job "CMS_soc" -rep 1 -comm_type ps_exec -dbg --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --auto_connected_standby --quiesce 120s -soc_dur 180s
```

### 2.4 CMS + DAQ + SocWatch
```bash
python -m pnpauto.connected_modern_standby_socwatch -job "CMS_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --auto_connected_standby --quiesce 180s -soc_dur 180s
```

### 2.5 CMS + Intec (25°C)
```bash
python -m hopper.pnp.workloads.kpi.connected_modern_standby -job "CMS_intec" -rep 1 -comm_type ps_exec -dbg -qui 180s --quiesce_screen_on 120s -intc -intec_sp 25
```

### 2.6 CMS + Intec + SocWatch (25°C)
```bash
python -m pnpauto.connected_modern_standby_socwatch -job "CMS_intec_soc" -rep 1 -comm_type ps_exec -dbg --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --auto_connected_standby --quiesce 120s -soc_dur 180s -intc -intec_sp 25
```

### 2.7 CMS + Intec + DAQ (25°C)
```bash
python -m hopper.pnp.workloads.kpi.connected_modern_standby -job "CMS_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg -qui 180s --quiesce_screen_on 120s -intc -intec_sp 25
```

### 2.8 CMS + Intec + DAQ + SocWatch (25°C)
```bash
python -m pnpauto.connected_modern_standby_socwatch -job "CMS_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -comm_type ps_exec -dbg --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --auto_connected_standby --quiesce 180s -soc_dur 180s -intc -intec_sp 25
```

**Key CMS Parameters:**
- `--quiesce_screen_on`: Screen-on quiesce duration
- `--auto_connected_standby`: Enable auto-connected standby mode
- `-soc_dur`: SocWatch capture duration

---

## 3. ICOB (Intel Custom Offline Browsing)

**Module:** `hopper.pnp.workloads.power.icob_catapult.icob_catapult`
**Default Quiesce:** 30s | **Default Capture:** 720s
**Proxy:** Auto Proxy DISABLED, Manual Proxy DISABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
}
```

### 3.1 ICOB Only
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB" -rep 1 --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s
```

### 3.2 ICOB + DAQ
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s
```

### 3.3 ICOB + SocWatch
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s
```

### 3.4 ICOB + DAQ + SocWatch
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s
```

### 3.5 ICOB + Intec (40°C)
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_intec" -rep 1 --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s -intc -intec_sp 40
```

### 3.6 ICOB + Intec + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_intec_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s -intc -intec_sp 40
```

### 3.7 ICOB + Intec + DAQ (40°C)
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s -intc -intec_sp 40
```

### 3.8 ICOB + Intec + DAQ + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.power.icob_catapult.icob_catapult -job "ICOB_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --icob_responsiveness --ip_server 172.22.21.116 --icob_version V2 --browser edge --icob_path "C:/Applications/ICOB_DUT/ICOB.exe" -comm_type ps_exec -dbg --quiesce 30s -intc -intec_sp 40
```

**Key ICOB Parameters:**
- `--icob_responsiveness`: Enable responsiveness measurements
- `--ip_server`: ICOB server IP address
- `--icob_version`: ICOB version (V2)
- `--browser`: Browser to use (`edge`, `chrome`)
- `--icob_path`: Path to ICOB executable on SUT

---

## 4. Busy Idle

**Module:** `hopper.pnp.workloads.power.busy_idle.busy_idle`
**Default Quiesce:** 180s | **Default Capture:** 180s
**Proxy:** Auto Proxy ENABLED, Manual Proxy DISABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat' -Force; Write-Host 'Auto Proxy Enabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value 'http://wpad.intel.com/wpad.dat'
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
}
```

**Common Credentials Parameters:**
```
--skip_spotify_uninstall --skip_login_logout
--gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234"
--spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345"
--office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234"
--drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714"
--spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe"
```

### 4.1 Busy Idle Only
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE" -rep 1 --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s
```

### 4.2 Busy Idle + DAQ
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s
```

### 4.3 Busy Idle + SocWatch
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s
```

### 4.4 Busy Idle + DAQ + SocWatch
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s
```

### 4.5 Busy Idle + Intec (25°C)
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_intec" -rep 1 --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s -intc -intec_sp 25
```

### 4.6 Busy Idle + Intec + SocWatch (25°C)
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_intec_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s -intc -intec_sp 25
```

### 4.7 Busy Idle + Intec + DAQ (25°C)
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s -intc -intec_sp 25
```

### 4.8 Busy Idle + Intec + DAQ + SocWatch (25°C)
```bash
python -m hopper.pnp.workloads.power.busy_idle.busy_idle -job "BUSY_IDLE_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --skip_spotify_uninstall --skip_login_logout --gmail_username "ptp.pg.powerkpi@gmail.com" --gmail_password "ptp_pg_powerkpi_1234" --spotify_username "ptp.pg.powerkpi@gmail.com" --spotify_password "ptp_pg_powerkpi_12345" --office_username "ptp_powerkpi@14qrl3.onmicrosoft.com" --office_password "ptp_pg_powerkpi_1234" --drive_excel_path "https://docs.google.com/spreadsheets/d/1zdO1Z6whQ5dAuCP81fs5hBDCukNDPdpszEIgDHkARRY/edit?gid=1642539714#gid=1642539714" -comm_type ps_exec -dbg --spotify_path "C:/Users/Administrator/AppData/Local/Microsoft/WindowsApps/Spotify.exe" --quiesce 180s --duration 180s -intc -intec_sp 25
```

---

## 5. YouTube Streaming

**Module:** `hopper.pnp.workloads.power.youtube_4k.youtube_powershell`
**Default Quiesce:** 180s | **Default Capture:** 180s
**Proxy:** Auto Proxy DISABLED, Manual Proxy ENABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Write-Host 'Manual Proxy Enabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911'
}
```

**Credentials:** `--youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234"`

### 5.1 YouTube Only
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE" -rep 1 --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s
```

### 5.2 YouTube + DAQ
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s
```

### 5.3 YouTube + SocWatch
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s
```

### 5.4 YouTube + DAQ + SocWatch
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s
```

### 5.5 YouTube + Intec (40°C)
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_intec" -rep 1 --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 5.6 YouTube + Intec + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_intec_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 5.7 YouTube + Intec + DAQ (40°C)
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 5.8 YouTube + Intec + DAQ + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.power.youtube_4k.youtube_powershell -job "YOUTUBE_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto --youtube_username "ptp.pg.powerkpi@gmail.com" --youtube_password "ptp_pg_powerkpi_1234" -comm_type ps_exec -dbg --quiesce 180s --duration 180s -intc -intec_sp 40
```

---

## 6. Netflix Streaming

**Module:** `hopper.pnp.workloads.kpi.netflix`
**Default Quiesce:** 180s | **Default Capture:** 180s
**Proxy:** Auto Proxy DISABLED, Manual Proxy ENABLED

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911' -Force; Write-Host 'Manual Proxy Enabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'http://proxy.png.intel.com:911'
}
```

**Credentials:** `--netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8`

### 6.1 Netflix Only
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX" -rep 1 -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s
```

### 6.2 Netflix + DAQ
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s
```

### 6.3 Netflix + SocWatch
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s
```

### 6.4 Netflix + DAQ + SocWatch
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s
```

### 6.5 Netflix + Intec (40°C)
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_intec" -rep 1 -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 6.6 Netflix + Intec + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_intec_soc" -rep 1 -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 6.7 Netflix + Intec + DAQ (40°C)
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_intec_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s -intc -intec_sp 40
```

### 6.8 Netflix + Intec + DAQ + SocWatch (40°C)
```bash
python -m hopper.pnp.workloads.kpi.netflix -job "NETFLIX_intec_daq_soc" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -soc --option pch-count-always -f pcd-ip-active -f chipset-all -f s0ix-subs-res -f s0ix-subs-req -f cpu-hw -f cpu-pstate -f acpi-sstate -f hw-cpu-hwp -f hw-cpu-cstate -f os-cpu-cstate -f sstate -f cpu -f dgfx-pkg-cstate -f pmc-ip-status -f pch-slps0 -f cpu-pkgc-cfg -f cpu-pkgc-dbg -f soc-core-cstate-res -f display -f tcss -f pcie-lpm -f xhci -f device -r auto -dbg --netflix_username tester_intc_IVE_CAVE_PNP_FM_1@netflix.com --netflix_password 0mn4N*G*e8 -comm_type ps_exec --quiesce 180s --duration 180s -intc -intec_sp 40
```

---

## 7. S5 (Shutdown State)

**Module:** `hopper.pnp.workloads.S5`
**Default Quiesce:** 180s | **Default Capture:** 180s
**Proxy:** Auto Proxy DISABLED, Manual Proxy DISABLED
**Note:** S5 supports only 2 combinations — no instrumentation or DAQ only (no SocWatch).

**Pre-run Setup:**

*Option 1: PsExec*
```bash
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue; Write-Host 'Auto Proxy Disabled (HKCU and HKLM)'"
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" powershell -c "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Set-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -Force; Write-Host 'Manual Proxy Disabled (HKCU and HKLM)'"
```

*Option 2: PowerShell Remoting*
```powershell
$cred = New-Object System.Management.Automation.PSCredential("Administrator", (new-object System.Security.SecureString))
Invoke-Command -ComputerName 192.168.137.5 -Credential $cred -ScriptBlock {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
}
```

### 7.1 S5 Only
```bash
python -m hopper.pnp.workloads.S5 -job "S5" -rep 1 -dbg -qui 180s -dur 180s -comm_type ps_exec
```

### 7.2 S5 + DAQ
```bash
python -m hopper.pnp.workloads.S5 -job "S5_daq" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -dbg -qui 180s -dur 180s -comm_type ps_exec
```

### 7.3 S5 + Intec (25°C)
```bash
python -m hopper.pnp.workloads.S5 -job "S5_intec" -rep 1 -dbg -qui 180s -dur 180s -comm_type ps_exec -intc -intec_sp 25
```

### 7.4 S5 + DAQ + Intec (25°C)
```bash
python -m hopper.pnp.workloads.S5 -job "S5_daq_intec" -rep 1 --flexlogger -flex_cfg C:\Users\pgsvlab\Documents\Flexlogger\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1\4309_NVL_S_DDR5_FAB1_CPU_PCH_Rev1_LowPower1.flxproj --flexlogger_sampling_rate 1000 --flexlogger_keep_open --flexlogger_keep_raw -flex_dis_down -dbg -qui 180s -dur 180s -comm_type ps_exec -intc -intec_sp 25
```

---

## 8. MobileMark30 (MM30)

**Module:** `hopper.pnp.workloads.power.mobile_mark.mobilemark_30`
**Intec Temperature:** 40°C

### 8.1 MM30 + DAQ
```bash
python -m hopper.pnp.workloads.power.mobile_mark.mobilemark_30 -mm30_cli -mm30_est -mm30_i 2 -mm30_nv -dbg --flexlogger -flex_cfg "flexlogger_path_here" --flexlogger_sampling_rate 1000 -comm_type ps_exec -job "FullRun_ww13p4_MM30_R1"
```

### 8.2 MM30 + DAQ + Intec (40°C)
```bash
python -m hopper.pnp.workloads.power.mobile_mark.mobilemark_30 -mm30_cli -mm30_est -mm30_i 2 -mm30_nv -dbg --flexlogger -flex_cfg "flexlogger_path_here" --flexlogger_sampling_rate 1000 -comm_type ps_exec -job "FullRun_ww13p4_MM30_R1" -intc -intec_sp 40
```

---

# Workload Summary Table

| Workload | Module Path | Default Quiesce | Default Capture | Combinations | Auto Proxy | Manual Proxy | Intec Temp | Key Requirements |
|----------|-------------|-----------------|-----------------|--------------|------------|--------------|------------|------------------|
| IDON | `hopper.pnp.workloads.oorja_idle` | 180s | 180s | 8 | Disable | Disable | 25°C | None |
| CMS | `hopper.pnp.workloads.kpi.connected_modern_standby` / `pnpauto.connected_modern_standby_socwatch` | 180s | 180s | 8 | Disable | Disable | 25°C | None |
| ICOB | `hopper.pnp.workloads.power.icob_catapult.icob_catapult` | 30s | 720s | 8 | Disable | Disable | 40°C | Server IP, ICOB path |
| Busy Idle | `hopper.pnp.workloads.power.busy_idle.busy_idle` | 180s | 180s | 8 | Enable | Disable | 25°C | Gmail, Spotify, Office365 |
| YouTube | `hopper.pnp.workloads.power.youtube_4k.youtube_powershell` | 180s | 180s | 8 | Disable | Enable | 40°C | YouTube/Gmail |
| Netflix | `hopper.pnp.workloads.kpi.netflix` | 180s | 180s | 8 | Disable | Enable | 40°C | Netflix credentials |
| MobileMark30 (MM30) | `hopper.pnp.workloads.power.mobile_mark.mobilemark_30` | N/A | N/A | 2 | Disable | Disable | 40°C | `-mm30_cli -mm30_est -mm30_i 2 -mm30_nv` |
| S5 | `hopper.pnp.workloads.S5` | 180s | 180s | 4 | Disable | Disable | 25°C | None (no SocWatch) |

> **Combinations count**: 8 = {baseline, DAQ, SocWatch, DAQ+SocWatch} × {no Intec, +Intec}. S5 = 4 (no SocWatch support).

---

# Common Decision Frameworks

### Which Instrumentation to Use?

| Use Case | Instrumentation | Rationale |
|----------|----------------|-----------|
| Power rail debugging | DAQ (FlexLogger) | Sub-millisecond time-series on 49 rails |
| C-state validation | SocWatch | Package/Core C-state residency |
| Thermal correlation | PerfTracer + IPTA | ETW tracing with thermal data |
| Battery life KPI | DAQ + SocWatch | Combined power + C-state metrics |
| Regulatory KPI | DAQ + SocWatch | Meet validation requirements |

### Which Graph Type to Use?

| Goal | Graph Type | Use When |
|------|-----------|----------|
| Compare power across workloads | Bar Chart | Simple comparison of 2-5 workloads |
| See all metrics at once | Heatmap | Overview of 10+ metrics × workloads |
| Analyze trends over time | Line Graph | Time-series or sequential data |
| Find correlations | Scatter Plot | Identify relationships between metrics |
| Statistical distribution | Box Plot | Understand min/max/quartiles |

### When to Enable GENI Analysis?

**Enable GENI When:**
- Comparing multiple workloads (2+)
- Need actionable recommendations
- Investigating anomalies
- Want per-workload trend summaries
- Preparing reports for stakeholders

**Skip GENI When:**
- Single workload, quick check
- Raw data exploration only
- GENI not available (offline)

### Typical Workflow

1. **Configure Proxy Settings** — Set auto/manual proxy per workload requirements (PsExec or PowerShell Remoting)
2. **Apply Optional Presteps (if requested)** — Reboot, Windows optimization, virtualization, hardware acceleration
3. **Verify Prerequisites** — Hopper packages installed on HOST; Chocolatey packages on SUT
4. **Run Workload** — Execute appropriate workload command with desired instrumentation
5. **Analyze Results** — Review generated reports, logs, and measurements in `C:\_hopper_results\`
6. **Reset Proxy (if needed)** — Configure proxy settings for next workload if different

---

# File Locations

### Results Directory
```
C:\_hopper_results\
├── 20260409T025419_IDON_daq\
│   ├── IDON-results.json           # Aggregated metrics
│   ├── FlexLogger_Data.tdms        # Power rail time-series (320 MB)
│   ├── Automation_Summary.csv      # SocWatch aggregated
│   ├── detailed_cstate_data.csv    # SocWatch C-state details
│   └── logs\
├── 20260409T030304_CMS_soc\
│   └── ...
└── power_kpi_dashboard.html        # Generated dashboard
```

### PowerKPI Skill Directory
```
.opencode\skill\powerkpi\
├── dashboard_gui_v3.py              # Main GUI (v3.2)
├── parse_results_to_excel.py        # Excel exporter
├── generate_interactive_html_report.py  # CLI dashboard
├── plot_tdms_power_rails.py         # TDMS plotter
├── test_geni_prep.py                # Test scripts
├── SKILL.md                         # This file (complete reference)
├── README.md                        # User guide
├── GENI_INTEGRATION.md              # GENI integration guide
├── GENI_ENHANCEMENTS.md             # v3.2 enhancements
└── COMPREHENSIVE_SESSION_SUMMARY.md # Complete session record
```

---

# Troubleshooting

- **"Cannot perform reduction 'mean' with string dtype"**: Fixed in v3.2 (numeric conversion added)
- **GENI authentication error**: Use agent-driven mode (Mode 2) — no separate auth needed
- **Chocolatey not found**: Use full path `C:\ProgramData\chocolatey\bin\choco.exe`
- **PsExec connection fails**: Verify SUT IP (192.168.137.5) and credentials (Administrator / empty password)
- **Package install fails**:
  - Check proxy is disabled: `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable`
  - Verify Chocolatey source: `choco source list`
  - Check package exists: `choco search <package> --source occ-nuget-repo`
- **Chrome not found during ICOB**: Install `chrome-standalone` package via Chocolatey
- **Python import errors**: Verify Python 3.13.3 installed first, then py3-* packages
- **PsExec "Access Denied"**: Ensure Administrator account has no password (empty password "")
- **PsExec proxy config fails**: Switch to PowerShell Remoting (`Invoke-Command`) method
- **PowerShell Remoting fails**: Ensure WinRM is enabled on SUT (192.168.137.5)
- **Virtualization settings not applied**: Reboot SUT after changes: `python -m hopper.pnp.core.prestep.reboot`

---

# Version History

- **v3.2 (2026-04-09)**: GENI AI-powered trend analysis integration
  - Per-workload summaries, cross-workload comparison with ranking
  - 5-section structured analysis, MCP-based (no separate authentication)
- **v3.1 (2026-04-09)**: Full folder names, export buttons
- **v3.0 (2026-04-09)**: Data source selection, 6 graph types
- **v2.0 (2026-04-08)**: Enhanced GUI with multiple graph types
- **v1.0 (2026-04-07)**: Initial GUI release

---

**PowerKPI Agent** — Automating Intel Platform Power Validation with AI-Powered Insights
