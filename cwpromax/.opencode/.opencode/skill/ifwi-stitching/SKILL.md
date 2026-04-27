# IFWI Stitching Automation Skill

## Overview

IFWI (Integrated Firmware Image) stitching automation for Intel Client SoC platforms (NVL, MTL, LNL, PTL, ARL). This skill provides detailed procedures for automated IFWI generation using mfit.exe, xmlcli, and Excel-driven configuration management.

**Primary Tool**: `IFWI_Auto_Stitch.py`  
**Platforms**: Novalake (NVL), Meteorlake (MTL), Lunarlake (LNL), Pantherlake (PTL), Arrowlake (ARL)  
**RVP Types**: RVP1, RVP2, RVP3, RVP4, RVP5, RVP44M, RVP51

---

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Tool Setup](#tool-setup)
3. [Excel Configuration](#excel-configuration)
4. [Base IFWI Management](#base-ifwi-management)
5. [Ingredient Management](#ingredient-management)
6. [Stitching Procedures](#stitching-procedures)
7. [CE Extract Operation](#ce-extract-operation)
8. [Output Structure](#output-structure)
9. [Common Errors](#common-errors)
10. [Advanced Operations](#advanced-operations)

---

## Workflow Overview

### Three-Step Stitching Pipeline

```
Base IFWI → [MFIT] → [BIOSKnobs] → [UCODE] → Final IFWI
```

#### Step 1: MFIT Stitching
- **Tool**: `mfit.exe`
- **Purpose**: Integrate firmware components into base IFWI
- **Components**: PCODE, DCODE, PMC, SPHY, BIOS, EC, SOCC, ACODE
- **Timeout**: 300 seconds
- **Command Pattern**:
  ```bash
  mfit.exe -d <base_ifwi> --setvalues "<key=value;...>" --build <output>
  ```

**MFIT SetValues Configuration**:
```python
# USB2 DBC (Debug Class) Configuration
if debug_probe == "A-C":
    "DescriptorPlugin:DBC:EnEarlyUsb2DbcCon=Yes"
    "DescriptorPlugin:PMC_SoC:Usb2DbcPortEn=USB2 Port 1"
else:  # XDP
    "DescriptorPlugin:DBC:EnEarlyUsb2DbcCon=No"
    "DescriptorPlugin:PMC_SoC:Usb2DbcPortEn=No USB2 Ports"

# Component Integration
"SystemPlugin:BiosRegion:input_file_path=<bios.rom>"
"SystemPlugin:EcRegion:input_file_path=<ec.bin>"
"ESEPlugin:PUNIT:PUNITBinary_path=<pcode.bin>"
"ESEPlugin:PUNIT:num_of_instance_PUNITBinary_path=1"
"ESEPlugin:DMUP:DMUBinary_path=<dcode.bin>"
"ESEPlugin:DMUP:num_of_instance_DMUBinary_path=1"
"CsePlugin:PMC:PmcBinary_path=<pmc.bin>"
"ESEPlugin:SSPH:SocSphyBinary_path=<sphy.bin>"
"CsePlugin:CSE_SOCC:InputFile_path=<socc.bin>"
"ESEPlugin:AUNIT:AUNITBinary_path=<acode.bin>"
```

#### Step 2: BIOSKnobs Application
- **Tool**: `xmlcli` via Python subprocess
- **Purpose**: Apply BIOS configuration settings from .ini file
- **Python Path**: `C:\Python310\python.exe` (default, configurable)
- **Timeout**: 600 seconds
- **Command Pattern**:
  ```python
  python -c "from xmlcli import XmlCli as cli; \
             cli.clb.KnobsIniFile=r'<biosknobs.ini>'; \
             cli.CvProgKnobs(0, r'<input_ifwi>', BiosOut=r'<output_ifwi>')"
  ```

**Common Issues**:
- XML parsing errors → Auto-sanitization removes invalid control characters
- Output filename may use alternate naming → Search for `*_knobs.bin` pattern

#### Step 3: UCODE Patching
- **Tool**: `xmlcli.ProcessUcode` via Python subprocess
- **Purpose**: Update microcode patches
- **Input**: `.inc` file (microcode patch)
- **Timeout**: 600 seconds
- **Command Pattern**:
  ```python
  python -c "from xmlcli import XmlCli as cli; \
             cli.ProcessUcode(Operation='UPDATE', \
                              BiosBinaryFile=r'<input_ifwi>', \
                              UcodeFile=r'<ucode.inc>', \
                              outPath=r'<output_dir>')"
  ```

**Output Naming**:
- Expected: `<input_name>_UCODE.bin`
- Alternate: `<input_name>_newUc_<stepping>_<hash>_NewFit.bin`
- Auto-cleanup: Remove `_newUc_*_NewFit` suffix from final filename

---

## Tool Setup

### Directory Structure

```
IFWI_Auto_Stitch/
├── IFWI_Auto_Stitch.py          # Main automation script
├── mfit.exe                      # Intel Flash Image Tool
├── NVL_domain readiness.xlsx     # Configuration Excel
├── Ingredients/                  # Firmware components
│   ├── PCODE_NVL_*.bin
│   ├── DCODE_NVL_*.bin
│   ├── m_82_300f30_*.inc        # UCODE
│   ├── PMC_*.bin
│   ├── SPHY_*.bin
│   ├── *.rom                     # BIOS
│   ├── EC_*.bin
│   ├── SOCC_*.bin
│   └── ACODE_*.bin
├── Biosknobs/                    # BIOS configuration files
│   └── *.ini
├── Output/                       # Stitching results
│   ├── RVP1/
│   ├── RVP2/
│   └── ...
└── logs/                         # Execution logs
```

### Prerequisites

1. **Python 3.10+ with pandas**:
   ```bash
   pip install pandas openpyxl
   ```

2. **Python 3.10 with xmlcli** (separate installation):
   ```bash
   # Install pysvtools.xmlcli in C:\Python310
   C:\Python310\python.exe -m pip install pysvtools
   ```

3. **mfit.exe**: Intel Flash Image Tool (obtain from Intel)

4. **Excel Configuration**: `NVL_domain readiness.xlsx`

### Environment Configuration

**Python Paths**:
- Main script: Any Python 3.10+ with pandas
- xmlcli operations: `C:\Python310\python.exe` (configurable in GUI)

**Logging**:
- Location: `logs/ifwi_auto_stitch_<timestamp>.log`
- Format: `[timestamp] LEVEL: message`

---

## Excel Configuration

### Sheet Structure

**Default Sheet**: `'NVL-HX.info for one BKC team'`

**Column Mapping** (C to L, 0-indexed columns 2-11):

| Column | Index | Field | Values | Notes |
|--------|-------|-------|--------|-------|
| C | 2 | RVP Type | RVP1, RVP2, RVP3, RVP4, RVP5 | Platform variant |
| D | 3 | Config Name | String | **Unique identifier** (not forward-filled) |
| E | 4 | Corp/Consumer | consumer, corporate | Market segment |
| F | 5 | Debug Probe Type | XDP, A-C | Debug interface |
| G | 6 | USB2DBC | Varies | USB2 Debug Class |
| H | 7 | System with DTPM? | Yes/No | Dynamic Turbo Power Management |
| I | 8 | System with PD AIC? | Yes/No | Power Delivery AIC |
| J | 9 | Manual WA | Yes/No | Manual workaround flag |
| K | 10 | With PCH / Without | with, without | PCH presence |
| L | 11 | Bootguard (SEP/SED) | SEP0-SEP5, SED0-SED5 | Security level |

### Merged Cell Handling

**Problem**: Excel merged cells cause pandas to read only first row value, leaving subsequent rows as NaN.

**Solution**: Forward-fill (`ffill()`) for columns C, E-L (skip D = Config Name which must be unique per row).

```python
# Columns to forward-fill (exclude D = Config Name)
cols_to_fill = [2, 4, 5, 6, 7, 8, 9, 10, 11]  # C, E-L
for col_idx in cols_to_fill:
    df.iloc[:, col_idx] = df.iloc[:, col_idx].ffill()
```

### Configuration Grouping

**Unique Combinations**: Configs are grouped by:
- RVP Type
- Corp/Consumer
- USB2DBC (normalized: Dis/En)
- PCH Status (with/without)
- Bootguard (SEP level)

**Example**:
- 10 configs with same (RVP1, consumer, Dis, with, SEP0) → 1 combination
- Only **first config** from each combination is stitched (same recipe)

### Boolean Parsing

```python
def parse_bool(val):
    if pd.isna(val):
        return False
    val_str = str(val).lower().strip()
    return val_str in ['yes', 'y', 'true', '1']
```

---

## Base IFWI Management

### Auto-Detection from Filename

**RVP Type Detection** (HR pattern):
```
HR11, HR14 → RVP1
HR21 → RVP2
HR31 → RVP3
HR41, HR45 → RVP4
HR51 → RVP5
```

**Corp/Consumer Detection**:
```
CPRF → consumer
RPRF → corporate
Default → both (matches any)
```

**SEP Level Detection** (regex):
```regex
SEP([0-5]) → SEP0, SEP1, ..., SEP5
SED([0-5]) → SED0, SED1, ..., SED5
Default → ALL (matches any)
```

**PCH Status Detection**:
```
HR11, HR21, HR31, HR41 → with PCH
HR14, HR45 → without PCH
Default → both (matches any)
```

**USB2DBC Detection** (from subfolder or filename):
```
01DD, 11DD → Dis (Disabled)
01DF, 11DF → En (Enabled)
Default → ALL (matches any)
```

### Folder-Based Import

**Expected Structure**:
```
Source/
├── RVP1/
│   ├── USB2DBC_Dis_Dam_En/
│   │   └── *.bin  (01DD, 11DD files)
│   └── USB2DBC_En_Dam_En/
│       └── *.bin  (01DF, 11DF files)
├── RVP2/
│   └── ...
└── RVP4/
    └── ...
```

**Import Logic**:
1. Scan each RVP folder
2. For each USB2DBC subfolder, find .bin files
3. Auto-detect all attributes from filename
4. Add to base IFWI list with metadata

### SED to SEP Conversion

**When**: SED files detected during folder import

**Prompt**: "Found X SED file(s) that can be converted to SEP. Convert?"

**Conversion Method**:
```bash
mfit.exe -d <sed_input.bin> \
  --setvalues "CsePlugin:AutoNvars:TPMTechnology=Intel (R) PTT" \
  --build <sep_output.bin>
```

**Naming**: `SED0` → `SEP0`, `SED5` → `SEP5` (case-insensitive replacement)

**After Conversion**: Auto-add converted SEP files to base IFWI list

---

## Ingredient Management

### Auto-Detection Patterns

**Categorization by Filename**:

| Type | Pattern | Extension | Example |
|------|---------|-----------|---------|
| PCODE | `PCODE` in name | `.bin` | `PCODE_NVL_P_A0_24.3.9.5_*.bin` |
| DCODE | `DCODE` in name | `.bin` | `DCODE_NVL_P_A0_24.3.9.5_*.bin` |
| UCODE | N/A | `.inc` | `m_82_300f30_f256000b.inc` |
| PMC | `PMC` in name | `.bin` | `PMC_NVL_24.3.9.5_*.bin` |
| SPHY | `SPHY` in name | `.bin` | `SPHY_NVL_24.3.9.5_*.bin` |
| BIOS | N/A | `.rom` | `NVL_HR11_*.rom` |
| EC | `EC` in name | `.bin` | `EC_NVL_*.bin` |
| SOCC | `SOCC` in name | `.bin` | `SOCC_NVL_24.3.9.5_*.bin` |
| ACODE | `ACODE` in name | `.bin` | `ACODE_NVL_24.3.9.5_*.bin` |
| IFWI | `IFWI` in name | `.bin` | Base IFWI files |

### Version Extraction

**Purpose**: Build descriptive output filename suffix from ingredient versions

**Extraction Logic**:

```python
# UCODE: Take last underscore-separated segment
m_82_300f30_f256000b.inc → "f256000b"

# Others: Extract dotted version pattern
PCODE_NVL_P_A0_24.3.9.5_*.bin → "pcode_24.3.9.5"
DCODE_NVL_P_A0_24.3.9.5_*.bin → "dcode_24.3.9.5"
PMC_NVL_24.3.9.5_*.bin → "pmc_24.3.9.5"

# Fallback: Look for X.X.X or X.X pattern
```

**Output Filename**:
```
<base_name>_<debug>_<pch>_<bootguard>_<ingredient_versions>.bin

Example:
NVL_HR11_B0A0_XDP_PCH_SEP0_pcode_24.3.9.5_dcode_24.3.9.5_ucode_f256000b.bin
```

### Disabled Ingredients (Default)

**Problem**: Some ingredients cause MFIT errors on many IFWIs

**Default Disabled**:
- PMC
- SPHY
- SOCC
- ACODE

**GUI Control**: Checkbox to enable/disable each ingredient type

**Effect**: When disabled, ingredient path is cleared and not passed to MFIT

---

## Stitching Procedures

### Single Config Stitching

**Prerequisites**:
1. Base IFWI file
2. Configuration from Excel (or manual)
3. Ingredients scanned
4. Optional: BIOSKnobs .ini file
5. Optional: UCODE .inc file

**Process**:

```python
# 1. IFWI-to-Config Matching
if not match_ifwi_to_config(base_ifwi, config):
    skip("No match")

# 2. Auto-Assign Ingredients (if not manually set)
if not config.pcode_path and ingredients['pcode']:
    config.pcode_path = ingredients['pcode'][0]
# ... repeat for all ingredient types

# 3. Step 1: MFIT Stitching
mfit_output = execute_mfit(config)
current_file = mfit_output

# 4. Step 2: BIOSKnobs Application (if specified)
if config.biosknobs_path:
    knobs_output = apply_biosknobs(current_file, config.biosknobs_path)
    current_file = knobs_output

# 5. Step 3: UCODE Patching (if available)
if config.ucode_path:
    ucode_output = apply_ucode_patch(current_file, config.ucode_path)
    current_file = ucode_output

# 6. Copy to Final Output Location
final_output = Output/<RVP>/<USB2DBC_subfolder>/<cleaned_filename>
shutil.copy2(current_file, final_output)
```

### Batch Processing

**Flow**:

```
1. Load configs from Excel → Group into unique combinations
2. Select combinations to process (or process all)
3. For each base IFWI:
   a. For each selected combination:
      i.   Check IFWI-to-config match (RVP, Corp, SEP, PCH, USB2DBC)
      ii.  If match: Process first config from combination
      iii. Copy final output to RVP/USB2DBC folder
4. Cleanup intermediate work files
```

**Matching Rules**:

| Field | Match Logic |
|-------|-------------|
| RVP Type | Exact match or numeric part match (RVP1 ↔ 1) |
| Corp/Consumer | Exact match or "both" in IFWI |
| SEP Level | Exact match or "ALL" in IFWI |
| PCH Status | Exact match or "both" in IFWI |
| USB2DBC | Normalized match (Dis/En) or "ALL" in IFWI |

**USB2DBC Normalization**:
```python
# Config values → Normalized
"Dis", "USB2DBC_Dis_Dam_En", "No", "N", "0" → "Dis"
"En", "USB2DBC_En_Dam_En", "Yes", "Y", "1" → "En"
```

### Progress Tracking

**GUI Mode**:
- Progress bar: `[current/total]` operations
- Status label: Current config name
- Log window: Real-time updates

**CLI Mode**:
- Console output with timestamps
- Log file in `logs/` directory

**Stop Functionality**:
- Red STOP button in GUI
- Sets `stop_requested` flag
- Gracefully completes current operation before halting
- Displays summary: `Completed X/Y operations before stop`

---

## CE Extract Operation

### Purpose

Extract **specific IFWI files** from official Intel release folders and organize into CE (Customer Engineering) folder structure for distribution.

### Source Structure

```
Official_Release/
├── PCH_IOE/              # Entire folder copied as-is
├── RVP1/
│   └── *.bin             # 9 specific files
├── RVP2/
│   └── *.bin             # 1 specific file
├── RVP3/
│   └── *.bin             # 1 specific file
├── RVP4/
│   └── *.bin             # 7 specific files (also source for RVP44M)
└── RVP5/
    └── *.bin             # 8 specific files (source for RVP51)
```

### Target Structure

```
CE/
├── PCH_IOE/              # Full copy from source
├── RVP1/
│   ├── USB2DBC_Dis_Dam_En/    # D-type files (01DD, 11DD)
│   └── USB2DBC_En_Dam_En/     # F-type files (01DF, 11DF)
├── RVP2/
│   └── USB2DBC_En_Dam_En/     # 1 SED0 file
├── RVP3/
│   └── USB2DBC_En_Dam_En/     # 1 SED0 file
├── RVP4/
│   ├── USB2DBC_Dis_Dam_En/    # 3 D-type files
│   └── USB2DBC_En_Dam_En/     # 4 F-type files
├── RVP44M/               # Subset from RVP4 source
│   ├── USB2DBC_Dis_Dam_En/
│   └── USB2DBC_En_Dam_En/
└── RVP51/                # From RVP5 source
    ├── USB2DBC_Dis_Dam_En/
    └── USB2DBC_En_Dam_En/
```

### Specific File Mappings

**RVP1** (9 files: 6 SEP0 + 3 SEP5):
```
NVL_HR11_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR11_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR11_B0A0-ODCA_RPRF_SEP0_11DF0418  [F, SEP0]
NVL_HR14_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR14_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR14_B0A0-ODCA_RPRF_SEP0_11DF0418  [F, SEP0]
NVL_HR11_B0A0-ODCA_RPRF_SEP5_11DF0418  [F, SEP5]
NVL_HR11_B0A0-ODCA_RPRF_SEP5_11DD0418  [D, SEP5]
NVL_HR14_B0A0-ODCA_CPRF_SEP5_01DD0418  [D, SEP5]
```

**RVP2** (1 file: SED0):
```
NVL_HR21_B0A0-ODCA_CPRF_SED0_01DF0418  [F, SED0]
```

**RVP3** (1 file: SED0):
```
NVL_HR31_B0A0-ODCA_CPRF_SED0_01DF0428  [F, SED0]
```

**RVP4** (7 files: 6 SEP0 + 1 SEP5):
```
NVL_HR41_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR41_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR41_B0A0-ODCA_RPRF_SED0_11DF0418  [F, SED0]
NVL_HR41_B0A0-ODCA_RPRF_SEP0_11DF0418  [F, SEP0]
NVL_HR45_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR45_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR45_B0A0-ODCA_RPRF_SEP5_11DD0418  [D, SEP5]
```

**RVP44M** (6 files from RVP4 source):
```
NVL_HR45_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR45_B0A0-ODCA_CPRF_SEP5_01DF0418  [F, SEP5]
NVL_HR45_B0A0-ODCA_RPRF_SEP5_11DF0418  [F, SEP5]
NVL_HR45_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR45_B0A0-ODCA_RPRF_SEP0_11DD0418  [D, SEP0]
NVL_HR45_B0A0-ODCA_RPRF_SEP5_11DD0418  [D, SEP5]
```

**RVP51** (8 files from RVP5 source: 4 SEP0 + 4 SEP5):
```
NVL_HR51_B0A0-ODCA_CPRF_SEP0_01DF0418  [F, SEP0]
NVL_HR51_B0A0-ODCA_CPRF_SEP5_01DF0418  [F, SEP5]
NVL_HR51_B0A0-ODCA_RPRF_SEP0_11DF0418  [F, SEP0]
NVL_HR51_B0A0-ODCA_RPRF_SEP5_11DF0418  [F, SEP5]
NVL_HR51_B0A0-ODCA_CPRF_SEP0_01DD0418  [D, SEP0]
NVL_HR51_B0A0-ODCA_CPRF_SEP5_01DD0418  [D, SEP5]
NVL_HR51_B0A0-ODCA_RPRF_SEP0_11DD0418  [D, SEP0]
NVL_HR51_B0A0-ODCA_RPRF_SEP5_11DD0418  [D, SEP5]
```

### File Classification

**D/F Type** (determines USB2DBC subfolder):
```
01DD, 11DD → D → USB2DBC_Dis_Dam_En
01DF, 11DF → F → USB2DBC_En_Dam_En
```

**SEP/SED Type** (for logging):
```
SEP0, SEP1-5, SED0, SED1-5 → Extracted from filename
```

### Flexible Matching

**Problem**: Official release filenames may have year/week suffixes

**Solution**: Extract base filename ignoring suffixes

```python
# Patterns to remove
_\d{4}WW\d{2}\.\d+\.\d+$   # Year-Week-Version
_\d{4}WW\d{2}$             # Year-Week
_WW\d{2}\.\d+\.\d+$        # Week-Version
_WW\d{2}$                  # Week only
_\d{8}$                    # Date (YYYYMMDD)
_v\d+\.\d+$                # Version

# Example
NVL_HR11_B0A0-ODCA_CPRF_SEP0_01DD0418_2024WW12.1.0.bin
→ Base: NVL_HR11_B0A0-ODCA_CPRF_SEP0_01DD0418
```

### Operations

#### 1. Scan Source Folders
- Verify presence of required RVP folders
- Count .bin files in each folder
- Check for each specific IFWI file (with flexible matching)
- Debug mode: Show all .bin files found
- Output: Summary of found vs. missing files

#### 2. Create CE Structure
- Create `CE/` root folder
- Create RVP subfolders (RVP1-5, RVP44M, RVP51)
- Create USB2DBC subfolders (Dis/En) in each RVP folder
- Create `CE/PCH_IOE/` folder

#### 3. Extract Files
- Copy entire `PCH_IOE/` folder
- For each RVP folder:
  - Find matching .bin files for each specific IFWI
  - Classify as D or F type
  - Copy to appropriate USB2DBC subfolder
- Progress bar updates per RVP folder
- Log each file copied with type classification

---

## Output Structure

### Folder Hierarchy

```
Output/
├── RVP1/
│   ├── USB2DBC_Dis_Dam_En/
│   │   └── <base>_XDP_PCH_SEP0_pcode_x.x.x.x_..._knobs_UCODE.bin
│   └── USB2DBC_En_Dam_En/
│       └── <base>_XDP_PCH_SEP0_pcode_x.x.x.x_..._knobs_UCODE.bin
├── RVP2/
│   └── USB2DBC_En_Dam_En/
│       └── ...
└── ...
```

### Filename Convention

**Pattern**:
```
<base_ifwi_name>_<debug_type>_<pch_status>_<bootguard>_<ingredient_versions>[_knobs][_UCODE].bin
```

**Components**:
- `base_ifwi_name`: Original base IFWI filename (without .bin)
- `debug_type`: `XDP` or `A-C`
- `pch_status`: `PCH` (with) or empty (without)
- `bootguard`: `SEP0`, `SEP5`, etc.
- `ingredient_versions`: `pcode_24.3.9.5_dcode_24.3.9.5_ucode_f256000b`
- `_knobs`: Appended if BIOSKnobs applied
- `_UCODE`: Appended by xmlcli (may be cleaned up)

**Example**:
```
NVL_HR11_B0A0-ODCA_XDP_PCH_SEP0_pcode_24.3.9.5_dcode_24.3.9.5_pmc_24.3.9.5_ucode_f256000b_knobs.bin
```

### Intermediate Files

**Work Directory**: `Output/.work/` (cleaned up after completion)

**Intermediate Files** (not in final output):
- MFIT output: `<base>_<debug>_<pch>_<bootguard>_<versions>.bin`
- BIOSKnobs output: `<base>_..._knobs.bin`
- UCODE output: `<base>_..._UCODE.bin` or `<base>_..._newUc_*_NewFit.bin`

**Cleanup**: After successful stitching, intermediate files are removed, only final output remains

---

## Common Errors

### 1. MFIT Stitching Errors

**Error**: `MFIT stitching failed: [error message]`

**Common Causes**:

| Symptom | Cause | Solution |
|---------|-------|----------|
| PMC integration error | PMC version mismatch | Disable PMC ingredient (default) |
| SPHY integration error | SPHY not compatible | Disable SPHY ingredient (default) |
| SOCC integration error | SOCC version issue | Disable SOCC ingredient (default) |
| ACODE integration error | ACODE conflicts | Disable ACODE ingredient (default) |
| Timeout after 300s | Large IFWI or slow disk | Check disk I/O, increase timeout |
| Invalid setvalues | Syntax error | Check semicolon separation, quotes |

**Debug**:
```bash
# Test MFIT command manually
mfit.exe -d base.bin --setvalues "key=value" --build output.bin

# Check mfit.exe version
mfit.exe --version
```

### 2. BIOSKnobs Application Errors

**Error**: `BIOSKnobs application failed: XML parsing error`

**Cause**: Invalid control characters in XML generated by xmlcli.savexml()

**Auto-Fix**: XML sanitization removes control characters (0x00-0x1F except tab, LF, CR)

**Manual Fix**:
```python
# Clean XML before CvProgKnobs
with open('ifwi.xml', 'rb') as f:
    data = f.read()
cleaned = bytearray(b if b >= 0x20 or b in (0x09, 0x0A, 0x0D) else 0x20 for b in data)
with open('ifwi.xml', 'wb') as f:
    f.write(cleaned)
```

**Error**: `BIOSKnobs output file not created`

**Causes**:
- xmlcli version mismatch
- Incorrect Python path
- BIOSKnobs .ini file corrupt

**Debug**:
```bash
# Test xmlcli manually
C:\Python310\python.exe -c "from xmlcli import XmlCli; print(XmlCli.__version__)"

# Test CvProgKnobs
C:\Python310\python.exe -c "from xmlcli import XmlCli as cli; \
  cli.clb.KnobsIniFile=r'test.ini'; \
  cli.CvProgKnobs(0, r'input.bin', BiosOut=r'output.bin')"
```

### 3. UCODE Patching Errors

**Error**: `UCODE patch error: [message]`

**Causes**:
- UCODE .inc file format invalid
- xmlcli version too old
- BIOS version incompatible with UCODE

**Output Naming Issues**:
- Expected: `<input>_UCODE.bin`
- Actual: `<input>_newUc_82_f256000b_NewFit.bin`
- **Auto-cleanup**: Script removes `_newUc_*_NewFit` pattern

**Manual UCODE Patch**:
```bash
C:\Python310\python.exe -c "from xmlcli import XmlCli as cli; \
  cli.ProcessUcode(Operation='UPDATE', \
                   BiosBinaryFile=r'input.bin', \
                   UcodeFile=r'm_82_300f30_f256000b.inc', \
                   outPath=r'.')"
```

### 4. IFWI-to-Config Matching Issues

**Error**: `No matching configurations found for the provided IFWI files!`

**Cause**: Mismatch between base IFWI attributes and config requirements

**Check Matching**:

| IFWI Attribute | Config Attribute | Match Rule |
|----------------|------------------|------------|
| RVP Type | config.rvp_type | Exact or numeric match |
| Corp/Consumer | config.corp_consumer | Exact or "both" |
| SEP Level | config.bootguard | Exact or "ALL" |
| PCH Status | config.with_pch | Exact or "both" |
| USB2DBC | config.usb2dbc (normalized) | Exact or "ALL" |

**Debug**:
```
# Check base IFWI attributes
RVP: RVP1, Corp: consumer, SEP: SEP0, PCH: with, USB2DBC: No

# Check config attributes
rvp_type: "1", corp_consumer: "consumer", bootguard: "SEP0", 
with_pch: True, usb2dbc: "Dis"

# Normalize and compare
RVP: RVP1 ↔ 1 → MATCH (numeric part)
Corp: consumer ↔ consumer → MATCH
SEP: SEP0 ↔ SEP0 → MATCH
PCH: with ↔ True → MATCH
USB2DBC: No ↔ Dis → MATCH (normalized)
```

**Solution**:
1. Verify base IFWI filename follows naming convention
2. Check Excel config values match IFWI
3. Use "ALL" or "both" for flexible matching

### 5. Excel Configuration Errors

**Error**: `Error reading Excel file: [message]`

**Causes**:

| Issue | Cause | Solution |
|-------|-------|----------|
| File not found | Path incorrect | Check Excel path in GUI |
| Sheet not found | Sheet name changed | Refresh sheet list, select correct sheet |
| Merged cells | Config name merged | Ensure column D (Config Name) is NOT forward-filled |
| NaN values | Empty cells | Use `parse_bool()` with NaN handling |

**Merged Cell Validation**:
```python
# After forward-fill, check for duplicate config names
config_names = df.iloc[:, 3]  # Column D
duplicates = config_names[config_names.duplicated(keep=False)]
if not duplicates.empty:
    print("WARNING: Duplicate config names detected!")
    print(duplicates)
```

### 6. Permission/Path Errors

**Error**: `Permission denied` or `File not found`

**Causes**:
- Output folder read-only
- Long file paths (>260 chars on Windows)
- Network drive disconnected
- Antivirus blocking mfit.exe

**Solutions**:
```bash
# Enable long paths (Windows)
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1

# Run as Administrator
# Right-click IFWI_Auto_Stitch.py → Run as Administrator

# Exclude from antivirus
# Add mfit.exe to antivirus exclusions
```

---

## Advanced Operations

### Custom Ingredient Selection

**Use Case**: Override auto-detected ingredients for specific stitching

**GUI Method**:
1. Go to "Ingredients" tab
2. In "Manual Ingredient Override" section:
   - Uncheck ingredient to disable (e.g., uncheck PMC)
   - Enter custom path to use different version
   - Click "..." to browse for file
3. Overrides apply to ALL subsequent stitching operations

**CLI Method**: Not supported, modify script or use GUI

### Multiple BIOSKnobs

**Scenario**: Apply different BIOSKnobs for different configs

**Current Limitation**: Only one BIOSKnobs file can be selected at a time

**Workaround**:
1. Process configs with BIOSKnobs A selected
2. Change BIOSKnobs selection to B
3. Process configs with BIOSKnobs B

**Future Enhancement**: Per-config BIOSKnobs assignment in Excel

### Batch Processing with Filters

**GUI Filter**:
- Enter text in "Filter" field on Stitching Configs tab
- Matches RVP Type, Corp/Consumer, USB2DBC, PCH, or Bootguard
- Example: "RVP1" shows only RVP1 combinations
- Example: "SEP5" shows only SEP5 combinations

**CLI Filter**:
```bash
# Process specific configs only
python IFWI_Auto_Stitch.py --base-ifwi base.bin \
  --configs "NVL_SEC_NDA" "NVL_HX_Display"
```

### Parallel Processing

**Current**: Sequential processing (one config at a time)

**Limitation**: MFIT and xmlcli may conflict with parallel execution

**Workaround**: Run multiple instances with different base IFWIs

```bash
# Terminal 1
python IFWI_Auto_Stitch.py --base-ifwi base_rvp1.bin

# Terminal 2
python IFWI_Auto_Stitch.py --base-ifwi base_rvp2.bin
```

### Log Analysis

**Log Location**: `logs/ifwi_auto_stitch_<timestamp>.log`

**Key Messages**:

```
[OK]      - Successful operation
[MISS]    - Missing file/folder
[FAILED]  - Operation failed
SUCCESS:  - Stitching completed
ERROR:    - Error occurred
WARNING:  - Potential issue
```

**Extract Failures**:
```bash
# Linux/Mac
grep "FAILED\|ERROR" logs/ifwi_auto_stitch_*.log

# Windows PowerShell
Select-String -Path "logs\ifwi_auto_stitch_*.log" -Pattern "FAILED|ERROR"
```

**Extract Timing**:
```bash
# Get operation durations
grep "Processing:" logs/ifwi_auto_stitch_*.log | \
  awk '{print $1, $2, $NF}'
```

### Ingredient Version Tracking

**Purpose**: Track which ingredient versions were used in each IFWI

**Method**: Parse output filenames

```bash
# Extract ingredient versions from filename
NVL_HR11_..._pcode_24.3.9.5_dcode_24.3.9.5_ucode_f256000b.bin
→ PCODE: 24.3.9.5
→ DCODE: 24.3.9.5
→ UCODE: f256000b
```

**Excel Export** (future enhancement):
```python
# Generate ingredient tracking spreadsheet
import pandas as pd

results = []
for output_file in Path('Output').rglob('*.bin'):
    versions = extract_ingredient_versions(output_file.name)
    results.append({
        'IFWI': output_file.name,
        'RVP': output_file.parent.parent.name,
        'USB2DBC': output_file.parent.name,
        **versions
    })

df = pd.DataFrame(results)
df.to_excel('ingredient_tracking.xlsx', index=False)
```

### Regression Testing

**Scenario**: Verify new ingredient versions produce valid IFWIs

**Method**:
1. Baseline: Stitch with known-good ingredients
2. Test: Stitch with new ingredient versions
3. Compare: Check output file sizes, boot logs

**Validation Checklist**:
- [ ] Output file size reasonable (±5% of baseline)
- [ ] IFWI boots successfully on hardware
- [ ] No new MFIT errors
- [ ] BIOSKnobs applied correctly
- [ ] UCODE version correct in BIOS setup

---

## Reference

### File Extension Reference

| Extension | Type | Tool | Purpose |
|-----------|------|------|---------|
| `.bin` | Binary | mfit.exe | IFWI image, firmware components |
| `.rom` | Binary | mfit.exe | BIOS region |
| `.inc` | Text | xmlcli | UCODE patches |
| `.ini` | Text | xmlcli | BIOSKnobs configuration |
| `.xlsx` | Excel | pandas | Stitching configuration |
| `.log` | Text | logging | Execution logs |

### MFIT Plugin Reference

| Plugin | Component | Example SetValue |
|--------|-----------|------------------|
| SystemPlugin:BiosRegion | BIOS | `input_file_path=<path>` |
| SystemPlugin:EcRegion | EC | `input_file_path=<path>` |
| ESEPlugin:PUNIT | PCODE | `PUNITBinary_path=<path>` |
| ESEPlugin:DMUP | DCODE | `DMUBinary_path=<path>` |
| CsePlugin:PMC | PMC | `PmcBinary_path=<path>` |
| ESEPlugin:SSPH | SPHY | `SocSphyBinary_path=<path>` |
| CsePlugin:CSE_SOCC | SOCC | `InputFile_path=<path>` |
| ESEPlugin:AUNIT | ACODE | `AUNITBinary_path=<path>` |
| DescriptorPlugin:DBC | USB2 DBC | `EnEarlyUsb2DbcCon=Yes/No` |
| DescriptorPlugin:PMC_SoC | USB2 Port | `Usb2DbcPortEn=USB2 Port 1` |
| CsePlugin:AutoNvars | TPM | `TPMTechnology=Intel (R) PTT` |

### xmlcli API Reference

**CvProgKnobs**:
```python
from xmlcli import XmlCli as cli
cli.clb.KnobsIniFile = r'<knobs.ini>'
cli.CvProgKnobs(0, r'<input.bin>', BiosOut=r'<output.bin>')
```

**ProcessUcode**:
```python
from xmlcli import XmlCli as cli
cli.ProcessUcode(
    Operation='UPDATE',
    BiosBinaryFile=r'<input.bin>',
    UcodeFile=r'<ucode.inc>',
    outPath=r'<output_dir>'
)
```

### Platform Code Reference

| Code | Platform | Stepping | Notes |
|------|----------|----------|-------|
| NVL | Novalake | B0, C0 | Primary platform |
| MTL | Meteorlake | A0, B0 | Legacy |
| LNL | Lunarlake | A0, B0 | Future |
| PTL | Pantherlake | A0 | Future |
| ARL | Arrowlake | A0, B0 | Parallel to NVL |

### RVP Configuration Reference

| RVP | HR Code | PCH | SOC Die | Target Segment |
|-----|---------|-----|---------|----------------|
| RVP1 | HR11 | Yes | HX | High-end |
| RVP1 | HR14 | No | HX | Embedded |
| RVP2 | HR21 | Yes | H | Mainstream |
| RVP3 | HR31 | Yes | P | Performance |
| RVP4 | HR41 | Yes | U | Ultrabook |
| RVP4 | HR45 | No | U | Tablet/2-in-1 |
| RVP5 | HR51 | Yes | P (variant) | Custom |

---

## Quick Reference Commands

### GUI Mode
```bash
# Launch GUI
python IFWI_Auto_Stitch.py --gui

# Or just
python IFWI_Auto_Stitch.py
```

### CLI Mode
```bash
# List configurations in Excel
python IFWI_Auto_Stitch.py --list-configs

# Scan ingredients only
python IFWI_Auto_Stitch.py --scan-only

# Process all configs with base IFWI
python IFWI_Auto_Stitch.py --base-ifwi base.bin

# Process specific configs
python IFWI_Auto_Stitch.py --base-ifwi base.bin \
  --configs "Config1" "Config2"

# Use different Excel sheet
python IFWI_Auto_Stitch.py --base-ifwi base.bin \
  --sheet "NVL-P. info for one BKC"
```

### Manual MFIT
```bash
# Basic stitching
mfit.exe -d base.bin \
  --setvalues "SystemPlugin:BiosRegion:input_file_path=bios.rom" \
  --build output.bin

# Multiple components
mfit.exe -d base.bin \
  --setvalues "SystemPlugin:BiosRegion:input_file_path=bios.rom;ESEPlugin:PUNIT:PUNITBinary_path=pcode.bin" \
  --build output.bin
```

### Manual xmlcli
```bash
# BIOSKnobs
C:\Python310\python.exe -c "from xmlcli import XmlCli as cli; cli.clb.KnobsIniFile=r'knobs.ini'; cli.CvProgKnobs(0, r'input.bin', BiosOut=r'output.bin')"

# UCODE
C:\Python310\python.exe -c "from xmlcli import XmlCli as cli; cli.ProcessUcode(Operation='UPDATE', BiosBinaryFile=r'input.bin', UcodeFile=r'ucode.inc', outPath=r'.')"
```

---

## Conclusion

This skill provides comprehensive automation for IFWI stitching operations across Intel Client SoC platforms. The three-step pipeline (MFIT → BIOSKnobs → UCODE) is managed through Excel-driven configuration with automatic ingredient detection and flexible base IFWI matching.

**Key Capabilities**:
- ✅ Batch processing with combination grouping
- ✅ Auto-detection of ingredients and base IFWI attributes
- ✅ Flexible IFWI-to-config matching
- ✅ CE Extract for customer distribution
- ✅ SED to SEP conversion
- ✅ Comprehensive error handling and logging
- ✅ GUI and CLI modes

**For Support**: Refer to log files in `logs/` directory and error messages in this skill document.
