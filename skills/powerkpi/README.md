# Power KPI Post-Processing Scripts

This directory contains Python scripts for post-processing Hopper Power KPI workload results. These scripts help analyze test data, generate reports, and visualize power measurements.

---

## Scripts Overview

### 0. `dashboard_gui_v3.py` ⭐⭐⭐ **LATEST VERSION v3.2 - HIGHLY RECOMMENDED**
**Purpose**: **AI-Powered GUI Dashboard Generator** with GENI trend analysis, multiple graph types, full folder names, and data source selection.

**NEW in v3.2** (2026-04-09):
- 🤖 **AI-Powered Trend Analysis**: Integrated with Intel GENI for automated insights
  - **Per-Workload Summaries**: Detailed analysis for each workload with trend overview
  - **Cross-Workload Comparison**: Automatic ranking and delta analysis
  - **Separated Metrics**: Power rails vs SocWatch metrics analyzed separately
  - **Structured Analysis**: 5-section format (Executive Summary, Per-Workload, Comparison, Anomalies, Recommendations)
  - **Actionable Insights**: Specific debug steps, BIOS knobs, and configuration recommendations
  - Leverages GENI's knowledge of Intel platforms via MCP (no separate authentication!)
  - Single checkbox to enable/disable
  - Appears above graph in HTML dashboard
- 📊 **GENI Focus Modes**: Uses VE Wiki or Debug Assistant focus
- ⚡ **Automated Insights**: No manual analysis needed!

**NEW in v3.1** (2026-04-09):
- 📁 **Full Folder Names with Timestamps**: Display complete folder names (e.g., "20260409T025419_IDON_daq") to differentiate multiple runs of same workload
- 📊 **Data Source Selection**: Choose between `results.json` (aggregated) or TDMS raw files (time-series)
- 📤 **Export Buttons**: 
  - Export to Excel (.xlsx) with folder names in first column
  - Export to HTML (static) for sharing
- 🔧 **Better Folder Management**: Map workload names to full folder paths internally

**NEW in v3.0**:
- 🎨 **6 Graph Types**: Choose how to visualize your data
  - **Bar Chart**: Standard comparison across workloads
  - **Grouped Bar Chart**: Side-by-side metric comparison
  - **Line Graph**: Trend analysis and patterns
  - **Scatter Plot**: Distribution and correlation
  - **Heatmap/Matrix**: All metrics vs all workloads
  - **Box Plot**: Statistical distribution (min/max/quartiles)
- 📊 **Data Aggregation Options**: Show Mean, Min, Max, or All
- 🔄 **True Comparison**: Compares ALL selected workloads in a single view

**Features**:
- ✅ **Full GUI with Tkinter** - No command-line needed!
- ✅ **5-Tab Workflow**:
  1. Select folders
  2. Filter & select power rails (with checkboxes)
  3. Filter & select SocWatch metrics (with checkboxes)
  4. Filter & select workloads (with FULL FOLDER NAMES)
  5. Select graph type + data source + AI analysis + export + generate
- ✅ **Keyword Filtering**: Type keywords to instantly filter rails/metrics/workloads
- ✅ **Checkbox Selection**: Click to select/deselect individual items
- ✅ **Bulk Actions**: Select All Visible, Deselect All buttons
- ✅ **Progress Tracking**: Visual progress bar during generation
- ✅ **Auto-Scan**: Automatically discovers all power rails, metrics, and workload folders

**Dependencies**:
```bash
pip install plotly pandas numpy openpyxl nptdms requests keyring msal
```

**GENI Authentication** (Required for AI Trend Analysis):
```bash
# Check authentication status
python .opencode/skill/geni/geni_auth_manager.py --status

# Authenticate (if needed)
python .opencode/skill/geni/geni_auth_manager.py --refresh
```

**Usage**:
```bash
# Launch GUI v3.2 (RECOMMENDED)
python dashboard_gui_v3.py

# Launch with pre-selected folder
python dashboard_gui_v3.py --folder C:\_hopper_results
```

**Enhanced Tab 5 - Graph, Data Source, AI Analysis**:
```
Graph Type Selection:
  ● Bar Chart          - Compare metrics across workloads with bars  [SELECTED]
  ○ Grouped Bar Chart  - Side-by-side comparison of multiple metrics
  ○ Line Graph         - Trend analysis across workloads
  ○ Scatter Plot       - Distribution and correlation analysis
  ○ Heatmap/Matrix     - All metrics vs all workloads in a matrix
  ○ Box Plot           - Statistical distribution with min/max/quartiles

Data Aggregation:
  ● Mean (Average) Values  [SELECTED]
  ○ Minimum Values
  ○ Maximum Values
  ○ All (Min, Mean, Max)

Data Source:  [NEW v3.1]
  ● results.json (Aggregated data from FlexLogger + SocWatch)  [SELECTED]
  ○ TDMS Raw Files (Time-series data from FlexLogger only)

AI Analysis (GENI):  [NEW v3.2]
  ☑ Include GENI Trend Analysis (Requires GENI authentication)
  ↳ GENI will analyze power trends, identify anomalies, and provide recommendations.

Export Options:  [NEW v3.1]
  [Export to Excel (.xlsx)]  [Export to HTML (Static)]
```

**GUI Workflow**:
1. **Tab 1 - Select Folders**: Browse to `C:\_hopper_results`, click "Scan Folders"
2. **Tab 2 - Power Rails**: 
   - Type "VCCCORE" in keyword filter → shows I_VCCCORE_PH1, I_VCCCORE_PH_TOTAL, etc.
   - Click "Select All Visible" to select all filtered rails
3. **Tab 3 - SocWatch Metrics** (optional):
   - Filter by keyword (e.g., "cstate", "frequency")
   - Select desired metrics
4. **Tab 4 - Workloads**: 
   - See FULL folder names with timestamps: "20260409T025419_IDON_daq"
   - Filter "IDON" → Select IDON runs by timestamp
   - Or filter "CMS" → Select CMS workloads
   - Compare multiple workload types!
5. **Tab 5 - Graph Type, Data Source, AI Analysis & Generate**: 
   - Select graph type (e.g., "Heatmap/Matrix" for full comparison)
   - Choose data source: results.json (default) or TDMS raw files
   - **Enable GENI Trend Analysis** (checkbox) for AI-powered insights
   - Choose data aggregation (e.g., "Mean")
   - Review summary
   - Click "Generate Interactive Dashboard"
   - OR click "Export to Excel" / "Export to HTML"

**AI Trend Analysis Features** (v3.2):
- **Power Efficiency Trends**: Identifies best/worst workloads
- **Anomaly Detection**: Flags unusual patterns or outliers
- **Cross-Workload Comparison**: Compares relative performance
- **Actionable Recommendations**: Suggests next debug steps
- **Intel Platform Context**: GENI knows Intel validation best practices
- **HTML Integration**: Insights appear above the graph in dashboard

**Example Use Cases**:

| Goal | Graph Type | Data Source | AI Analysis | Settings |
|------|------------|-------------|-------------|----------|
| Compare IDON vs CMS core power with insights | **Bar Chart** | results.json | ✅ Enabled | Rails: "VCCCORE", Workloads: IDON + CMS, Data: Mean |
| Analyze power trends with recommendations | **Line Graph** | results.json | ✅ Enabled | Rails: All, Workloads: Multiple, Data: Mean |
| Time-series raw power data | **Line Graph** | TDMS | ❌ Disabled | Rails: Selected, Workloads: Single, Data: All |
| Full comparison matrix with AI summary | **Heatmap** | results.json | ✅ Enabled | Rails: All, Workloads: All, Data: Mean |
| Excel export for offline analysis | N/A | results.json | ✅ Optional | Click "Export to Excel" button |

**Output Dashboard Features**:
- **AI Trend Analysis Section** (v3.2): Appears at top of HTML dashboard with GENI-powered insights
- **Interactive Plotly Graphs**: Hover, zoom, pan, export
- **Cross-Workload Comparison**: Multiple workloads overlaid/grouped
- **Hover Tooltips**: Exact values, metric names, workload names
- **Full Folder Names**: Workload labels show complete folder names with timestamps
- **Export Options**: Excel with folder names + metrics, or static HTML

**See also**: `GENI_INTEGRATION.md` for detailed documentation on AI trend analysis

---

### 1. `dashboard_gui_v2.py` ⭐⭐ **PREVIOUS VERSION**
**Purpose**: **Enhanced GUI-based dashboard generator** with multiple graph types, filtering, and cross-workload comparison.

**NEW in v2.0**:
- 🎨 **6 Graph Types**: Choose how to visualize your data
  - **Bar Chart**: Standard comparison across workloads
  - **Grouped Bar Chart**: Side-by-side metric comparison
  - **Line Graph**: Trend analysis and patterns
  - **Scatter Plot**: Distribution and correlation
  - **Heatmap/Matrix**: All metrics vs all workloads
  - **Box Plot**: Statistical distribution (min/max/quartiles)
- 📊 **Data Aggregation Options**: Show Mean, Min, Max, or All
- 🔄 **True Comparison**: Compares ALL selected workloads in a single view
- 📈 **Separate Graph Generation**: Each graph type creates a focused visualization

**Features** (inherited from v1):
- ✅ **Full GUI with Tkinter** - No command-line needed!
- ✅ **5-Tab Workflow with Enhanced Tab 5**:
  1. Select folders
  2. Filter & select power rails (with checkboxes)
  3. Filter & select SocWatch metrics (with checkboxes)
  4. Filter & select workloads (with checkboxes)
  5. **NEW**: Select graph type + data aggregation + generate
- ✅ **Keyword Filtering**: Type keywords to instantly filter rails/metrics
- ✅ **Checkbox Selection**: Click to select/deselect individual items
- ✅ **Bulk Actions**: Select All Visible, Deselect All buttons
- ✅ **Progress Tracking**: Visual progress bar during generation
- ✅ **Auto-Scan**: Automatically discovers all power rails and metrics

**Dependencies**:
```bash
pip install plotly pandas numpy
```

**Usage**:
```bash
# Launch GUI v2 (RECOMMENDED)
python dashboard_gui_v2.py

# Launch with pre-selected folder
python dashboard_gui_v2.py --folder C:\_hopper_results
```

**Enhanced Tab 5 - Graph Selection**:
```
Graph Type Selection:
  ○ Bar Chart          - Compare metrics across workloads with bars
  ● Grouped Bar Chart  - Side-by-side comparison of multiple metrics  [SELECTED]
  ○ Line Graph         - Trend analysis across workloads
  ○ Scatter Plot       - Distribution and correlation analysis
  ○ Heatmap/Matrix     - All metrics vs all workloads in a matrix
  ○ Box Plot           - Statistical distribution with min/max/quartiles

Data Aggregation:
  ● Mean (Average) Values  [SELECTED]
  ○ Minimum Values
  ○ Maximum Values
  ○ All (Min, Mean, Max)
```

**GUI Workflow**:
1. **Tab 1 - Select Folders**: Browse to `C:\_hopper_results`, click "Scan Folders"
2. **Tab 2 - Power Rails**: 
   - Type "VCCCORE" in keyword filter → shows I_VCCCORE_PH1, I_VCCCORE_PH_TOTAL, etc.
   - Click "Select All Visible" to select all filtered rails
3. **Tab 3 - SocWatch Metrics** (optional):
   - Filter by keyword (e.g., "cstate", "frequency")
   - Select desired metrics
4. **Tab 4 - Workloads**: 
   - Filter "IDON" → Select IDON_daq and IDON_soc
   - Or filter "CMS" → Select CMS workloads
   - Compare multiple workload types!
5. **Tab 5 - Graph Type & Generate**: 
   - Select graph type (e.g., "Heatmap/Matrix" for full comparison)
   - Choose data aggregation (e.g., "Mean")
   - Review summary
   - Click "🚀 Generate Dashboard"

**Example Use Cases**:

| Goal | Graph Type | Settings |
|------|------------|----------|
| Compare IDON vs CMS core power | **Bar Chart** | Rails: "VCCCORE", Workloads: IDON + CMS, Data: Mean |
| See power trends across all rails | **Line Graph** | Rails: All, Workloads: Single workload, Data: Mean |
| Find correlations between metrics | **Scatter Plot** | Rails: Multiple, Workloads: Single, Data: All |
| Overview of all metrics & workloads | **Heatmap** | Rails: All, Workloads: All, Data: Mean |
| Statistical distribution analysis | **Box Plot** | Rails: Selected, Workloads: Multiple, Data: All |

**Output Dashboard Features**:
- **Interactive Plotly Graphs**: Hover, zoom, pan, export
- **Cross-Workload Comparison**: Multiple workloads overlaid/grouped
- **Hover Tooltips**: Exact values, metric names, workload names
- **Export to PNG**: High-resolution (1600x1000 @ 2x scale)
- **Responsive Layout**: Auto-adjusts to data size

---

### 0b. `dashboard_gui.py` (v1 - Legacy)
**Purpose**: Original GUI dashboard generator (single graph type).

**Note**: Use `dashboard_gui_v2.py` instead for enhanced features. V1 is kept for backward compatibility.

---

### 1. `parse_results_to_excel.py`
**Purpose**: Parse `results.json` files from Hopper workload runs and generate Excel reports with power and SocWatch data.

**Features**:
- Extracts power dictionary from FlexLogger DAQ measurements
- Extracts socwatch dictionary from SocWatch instrumentation
- Unrolls nested JSON structures into Excel columns
- Adds metadata (workload name, path, IFWI, BKC)
- Supports single or batch processing of multiple runs

**Dependencies**:
```bash
pip install openpyxl
```

**Usage**:
```bash
# Single workload run
python parse_results_to_excel.py C:\_hopper_results\20260409T025419_IDON_daq

# Batch processing all runs in a parent folder
python parse_results_to_excel.py --batch C:\_hopper_results --output power_kpi_report.xlsx

# Custom output path
python parse_results_to_excel.py C:\_hopper_results\20260409T030304_IDON_soc --output idon_soc.xlsx
```

**Excel Output Structure**:
```
Row 1, Column 1: Workload name
Row 2, Column 1: Path to results.json
Row 3, Column 1: IFWI version (if available)
Row 4, Column 1: BKC name (if available)
Row 5, Column 1: "Metric" header
Row 5, Column 2: "Value" header
Row 6+: Power and SocWatch data (unrolled dictionaries)
```

---

### 2. `generate_interactive_html_report.py`
**Purpose**: Generate interactive HTML dashboards with selectable visualizations (bar charts, line graphs, scatter plots) for comparing Power KPI workload results.

**Features**:
- Interactive Plotly-based dashboards
- Multiple visualization types (bar, scatter, line, error bars)
- Hover tooltips with detailed measurements
- Cross-workload comparison
- Exportable to PNG with built-in controls

**Dependencies**:
```bash
pip install plotly pandas openpyxl
```

**Usage**:
```bash
# From single results.json folder
python generate_interactive_html_report.py --from-json C:\_hopper_results\20260409T025419_IDON_daq

# From batch of results folders
python generate_interactive_html_report.py --batch-json C:\_hopper_results --output dashboard.html

# From Excel report (not yet fully implemented)
# python generate_interactive_html_report.py C:\_hopper_results\power_kpi_combined_report.xlsx
```

**Dashboard Features**:
- **Plot 1**: Power measurements by workload (bar chart)
- **Plot 2**: Power rail comparison (grouped bar chart)
- **Plot 3**: Mean current values (line graph)
- **Plot 4**: Min/Max current ranges (error bars)
- **Plot 5**: Workload metrics overview (bar chart)
- **Plot 6**: Detailed metric breakdown (scatter plot)

---

### 3. `plot_tdms_power_rails.py`
**Purpose**: Plot TDMS power rail data from FlexLogger DAQ measurements with time-series visualization.

**Features**:
- Loads TDMS files from FlexLogger output
- Parses power rail current measurements
- Supports multi-folder comparison
- Overlay multiple power rails vs. time
- Output formats: HTML (interactive), PNG, PDF, SVG (static)
- List available power rails without plotting

**Dependencies**:
```bash
pip install npTDMS matplotlib plotly pandas numpy
```

**Usage**:
```bash
# List available power rails
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq --list-rails

# Single TDMS file/folder with selected rails
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq \
    --rails "I_V0P85A,I_V1P8A_PCH,I_VCCCORE_PH_TOTAL"

# Batch mode with multiple folders
python plot_tdms_power_rails.py --batch C:\_hopper_results \
    --rails "I_V0P85A,I_VCCCORE_PH_TOTAL" \
    --output power_rails_comparison.html

# Overlay multiple runs (comparison mode)
python plot_tdms_power_rails.py --batch C:\_hopper_results \
    --rails "I_V0P85A" \
    --overlay \
    --output overlay_comparison.png

# Static PNG output with Matplotlib
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq \
    --rails "I_V0P85A,I_V1P25,I_V3P3A_PCH" \
    --format png \
    --output power_rails.png
```

**Available Power Rails** (example from NVL platform):
```
I_V0P85A               - Core voltage 0.85V
I_VCCCORE_PH_TOTAL     - Total core power (all phases)
I_VCCSA_PH_TOTAL       - Total system agent power
I_VCCGT                - GT (graphics) voltage
I_V1P8A_PCH            - PCH 1.8V
I_V3P3A_PCH            - PCH 3.3V
I_V5DUAL_DDR5          - DDR5 memory 5V
... and 42 more rails
```

---

## Complete Workflow Example

### Step 1: Run Workloads
```bash
# Run IDON with DAQ
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" ^
    python C:\_automation\hopper\pnp\workloads\oorja_idle.py ^
    --use_ps_exec ^
    --flexlogger ^
    --output_dir C:\_hopper_results ^
    --output_name IDON_daq

# Run IDON with SocWatch
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" ^
    python C:\_automation\hopper\pnp\workloads\oorja_idle.py ^
    --use_ps_exec ^
    --socwatch ^
    --output_dir C:\_hopper_results ^
    --output_name IDON_soc
```

### Step 2: Parse Results to Excel
```bash
# Process all runs
python parse_results_to_excel.py --batch C:\_hopper_results --output power_kpi_report.xlsx
```

### Step 3: Generate Interactive Dashboard
```bash
# Create HTML dashboard from all results
python generate_interactive_html_report.py --batch-json C:\_hopper_results --output dashboard.html
```

### Step 4: Plot TDMS Power Rails
```bash
# First, list available rails
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq --list-rails

# Plot selected rails
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq \
    --rails "I_V0P85A,I_VCCCORE_PH_TOTAL,I_VCCSA_PH_TOTAL" \
    --output power_rails.html

# Compare multiple workloads with overlay
python plot_tdms_power_rails.py --batch C:\_hopper_results \
    --rails "I_V0P85A" \
    --overlay \
    --output comparison.html
```

---

## Output Files

### Excel Report (`power_kpi_report.xlsx`)
- **Location**: `C:\_hopper_results\power_kpi_report.xlsx`
- **Contains**: 
  - Workload metadata (name, path, IFWI, BKC)
  - Power measurements from FlexLogger
  - SocWatch data and timing
  - Configuration parameters
- **Use for**: Data export, further analysis in Excel, record keeping

### Interactive HTML Dashboard (`dashboard.html`)
- **Location**: `C:\_hopper_results\power_kpi_dashboard.html`
- **Contains**:
  - 6 interactive plots with different visualizations
  - Hover tooltips with detailed data
  - Export to PNG capability
  - Cross-workload comparison
- **Use for**: Interactive exploration, presentations, sharing results

### Power Rail Plots (`power_rails.html` or `.png`)
- **Location**: `C:\_hopper_results\power_rails.html`
- **Contains**:
  - Time-series plots of power rail currents
  - Multiple rails overlaid or in separate subplots
  - Zoom, pan, and hover capabilities (HTML)
  - High-resolution static images (PNG/PDF/SVG)
- **Use for**: Detailed power analysis, debugging, publications

---

## Common Power Rails Reference

| Rail Name | Description | Typical Range |
|-----------|-------------|---------------|
| `I_V0P85A` | Core voltage 0.85V | 0.3 - 2.5 A |
| `I_VCCCORE_PH_TOTAL` | Total CPU core power (all phases) | 1 - 100 A |
| `I_VCCSA_PH_TOTAL` | Total system agent power | 0.5 - 10 A |
| `I_VCCGT` | Graphics voltage | 0.1 - 20 A |
| `I_V1P8A_PCH` | PCH 1.8V rail | 0.04 - 0.06 A |
| `I_V3P3A_PCH` | PCH 3.3V rail | 0.005 - 0.01 A |
| `I_V5DUAL_DDR5` | DDR5 memory 5V | 1 - 10 A |
| `I_VCCIO` | I/O voltage | 0.5 - 5 A |
| `I_V1P25` | 1.25V rail | 0.07 - 0.5 A |

---

## GUI Dashboard Generator - Quick Reference

### Launching the GUI
```bash
python dashboard_gui.py
```

### GUI Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  Power KPI Dashboard Generator                                  │
├─────────────────────────────────────────────────────────────────┤
│  [1. Select Folders] [2. Power Rails] [3. SocWatch] [4. Workloads] [5. Generate]
├─────────────────────────────────────────────────────────────────┤
│  TAB 1: Folder Selection                                        │
│    Folder Path: [C:\_hopper_results        ] [Browse...]        │
│                        [Scan Folders]                           │
│    ✓ Found Results Folders:                                     │
│      ✓ 20260409T025419_IDON_daq                                │
│      ✓ 20260409T030304_IDON_soc                                │
│      ✓ 20260205T100050_IDON                                    │
│      ... (and more)                                             │
├─────────────────────────────────────────────────────────────────┤
│  TAB 2: Power Rails Selection                                   │
│    Keyword Filter: [VCCCORE        ] [Clear] [Select All] [Deselect All]
│                                                                  │
│    Available Power Rails:                                       │
│      ☑ I_V0P85A                                                │
│      ☑ I_VCCCORE_PH1                                           │
│      ☑ I_VCCCORE_PH2                                           │
│      ☑ I_VCCCORE_PH_TOTAL  ← Select this for total core power │
│      ☑ I_VCCSA_PH_TOTAL    ← Select this for SA power         │
│      ☐ I_V1P8A_PCH                                             │
│      ... (49 total rails with scrollbar)                        │
├─────────────────────────────────────────────────────────────────┤
│  TAB 3: SocWatch Metrics                                        │
│    Keyword Filter: [cstate         ] [Clear] [Select All] [Deselect All]
│                                                                  │
│    ☑ CPU_C_STATE                                               │
│    ☑ PACKAGE_C_STATE                                           │
│    ☐ FREQUENCY                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TAB 4: Workload Selection                                      │
│    Keyword Filter: [IDON           ] [Clear] [Select All] [Deselect All]
│                                                                  │
│    ☑ IDON_daq                                                  │
│    ☑ IDON_soc                                                  │
│    ☐ CMS                                                       │
│    ☐ NETFLIX                                                   │
├─────────────────────────────────────────────────────────────────┤
│  TAB 5: Generate Dashboard                                      │
│    Output File: [power_kpi_dashboard.html] [Browse...]         │
│                                                                  │
│    Selection Summary:                                           │
│    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        │
│    📁 Results Folder: C:\_hopper_results                        │
│    ✓ Selected Workloads: 2 / 8                                 │
│    ⚡ Selected Power Rails: 5 / 49                              │
│    📈 Selected SocWatch Metrics: 2 / 15                         │
│    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        │
│                                                                  │
│                    [Generate Dashboard]                         │
│                                                                  │
│    Status: Generating dashboard... [████████░░] 80%             │
├─────────────────────────────────────────────────────────────────┤
│  Status: Dashboard saved to: C:\_hopper_results\dashboard.html  │
└─────────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts & Tips
- **Tab Navigation**: Use `Ctrl+Tab` / `Ctrl+Shift+Tab` to move between tabs
- **Keyword Filter**: Type to instantly filter (case-insensitive)
- **Select All Visible**: Selects only items matching current filter
- **Space Bar**: Toggle checkbox on focused item
- **Filter Examples**:
  - Type "CORE" → shows I_VCCCORE_PH1, I_VCCCORE_PH2, etc.
  - Type "PCH" → shows all PCH-related rails
  - Type "IDON" → shows all IDON workload runs

### Common Workflow Patterns

#### Pattern 1: Quick Core Power Analysis
1. Tab 1: Scan `C:\_hopper_results`
2. Tab 2: Type "VCCCORE" → Select All Visible
3. Tab 4: Select all IDON workloads
4. Tab 5: Generate

#### Pattern 2: Compare IDON vs CMS
1. Tab 1: Scan folders
2. Tab 2: Select top 10 power rails
3. Tab 4: Filter "IDON" → Select All, then filter "CMS" → Select All
4. Tab 5: Generate

#### Pattern 3: SocWatch-Only Analysis
1. Tab 1: Scan folders
2. Tab 2: Deselect All (no power rails)
3. Tab 3: Select desired SocWatch metrics
4. Tab 4: Select workloads
5. Tab 5: Generate

---

## Troubleshooting

### Issue: "No results.json file found"
**Solution**: Ensure the workload run completed successfully. Check the folder for timestamped files like `20260409T025419-results.json`.

### Issue: "No TDMS files found"
**Solution**: Make sure FlexLogger DAQ was enabled during the workload run (`--flexlogger` flag). TDMS files are only generated with DAQ instrumentation.

### Issue: "Module not found: openpyxl"
**Solution**: Install dependencies:
```bash
pip install openpyxl plotly pandas npTDMS matplotlib numpy
```

### Issue: "Value error: No data extracted from results files"
**Solution**: Check that results.json contains valid power or socwatch data. Some workload runs may have incomplete instrumentation data.

### Issue: Large TDMS files take long to load
**Solution**: The TDMS files can be 300+ MB. Loading is normal and may take 10-30 seconds. Use `--rails` to select specific rails instead of plotting all 49 rails.

### Issue: GUI doesn't launch or crashes
**Solution**: 
1. Check tkinter is installed: `python -m tkinter` (should open a test window)
2. Update tkinter: `pip install --upgrade tk`
3. Check Python version: GUI requires Python 3.7+

### Issue: "Please select at least one workload" in GUI
**Solution**: Go to Tab 4 (Workloads) and check at least one workload checkbox. If no workloads appear, go back to Tab 1 and click "Scan Folders".

### Issue: Generated dashboard is empty or shows "No data"
**Solution**: 
1. Verify you selected at least one workload AND one metric (power rail or SocWatch)
2. Check the selection summary in Tab 5 before generating
3. Ensure the results.json files contain actual measurement data

### Issue: Dashboard dropdown filter doesn't show all rails
**Solution**: The dropdown only shows rails that have data in the selected workloads. If a rail is missing, it may not have been measured in those specific runs.

---

## Advanced Usage

### Filter Specific Workloads in Batch Mode
```python
# Modify parse_results_to_excel.py or generate_interactive_html_report.py
# to filter folders by name pattern
folders_to_process = [f for f in parent_folder.iterdir() 
                      if f.is_dir() and 'IDON' in f.name]
```

### Export Dashboard as PNG Programmatically
```python
import plotly.io as pio
fig = ... # your Plotly figure
pio.write_image(fig, 'dashboard.png', width=1800, height=1400, scale=2)
```

### Combine Excel Reports
```python
import pandas as pd
from openpyxl import load_workbook

# Load multiple Excel files and combine
wb1 = load_workbook('report1.xlsx')
wb2 = load_workbook('report2.xlsx')
# ... merge logic
```

---

## File Locations Summary

| File | Path | Purpose |
|------|------|---------|
| `dashboard_gui.py` ⭐ **NEW** | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | **GUI dashboard generator (RECOMMENDED)** |
| `parse_results_to_excel.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Results parser |
| `generate_interactive_html_report.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Dashboard generator (CLI) |
| `plot_tdms_power_rails.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | TDMS plotter |
| `SKILLS2.md` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Workload documentation |
| `README.md` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | This file |
| Hopper results | `C:\_hopper_results\` | All workload outputs |

---

## Quick Start (Recommended Workflow)

### For First-Time Users (GUI v2 Method) 🚀🎨
```bash
# 1. Run workloads (see SKILLS2.md for commands)
# Example: Run IDON with DAQ and SocWatch
psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" ^
    python C:\_automation\hopper\pnp\workloads\oorja_idle.py ^
    --use_ps_exec --flexlogger --output_dir C:\_hopper_results --output_name IDON_daq

psExec \\192.168.137.5 -i -accepteula -u Administrator -p "" ^
    python C:\_automation\hopper\pnp\workloads\oorja_idle.py ^
    --use_ps_exec --socwatch --output_dir C:\_hopper_results --output_name IDON_soc

# 2. Launch GUI v2 dashboard generator
python dashboard_gui_v2.py

# 3. In GUI:
#    - Tab 1: Browse to C:\_hopper_results, click "Scan Folders"
#    - Tab 2: Type "VCCCORE" in filter → Click "Select All Visible"
#    - Tab 4: Select IDON_daq and IDON_soc (to compare both runs)
#    - Tab 5: Select "Heatmap/Matrix" graph type, click "🚀 Generate Dashboard"

# 4. Open the generated HTML file in your browser!
#    → See all metrics vs all workloads in an interactive heatmap
```

### Example: Compare IDON vs CMS Core Power 📊
```bash
# 1. Ensure you have IDON and CMS results in C:\_hopper_results

# 2. Launch GUI v2
python dashboard_gui_v2.py --folder C:\_hopper_results

# 3. In GUI:
#    Tab 1: Click "Scan Folders" (auto-loads C:\_hopper_results)
#    Tab 2: Filter "VCCCORE" → Select "I_VCCCORE_PH_TOTAL"
#    Tab 4: Filter "IDON" → Select All, then filter "CMS" → Select All
#    Tab 5: Select "Bar Chart", Data: "Mean", click "Generate"

# 4. Result: Bar chart comparing IDON vs CMS core power consumption
```

### Example: Statistical Distribution Analysis 📈
```bash
# Launch GUI v2
python dashboard_gui_v2.py

# In GUI:
#    Tab 1: Scan C:\_hopper_results
#    Tab 2: Select 5-10 key power rails
#    Tab 4: Select all IDON runs (e.g., IDON_daq, IDON_soc, IDON_20260205, etc.)
#    Tab 5: Select "Box Plot", Data: "All (Min, Mean, Max)", Generate

# Result: Box plot showing min/max/quartiles for each workload run
```

### For Advanced Users (Command-Line Method)
```bash
# 1. Parse to Excel
python parse_results_to_excel.py --batch C:\_hopper_results --output report.xlsx

# 2. Generate dashboard (CLI - less flexible than GUI v2)
python generate_interactive_html_report.py --batch-json C:\_hopper_results --output dashboard.html

# 3. Plot specific TDMS rails
python plot_tdms_power_rails.py C:\_hopper_results\20260409T025419_IDON_daq \
    --rails "I_VCCCORE_PH_TOTAL,I_VCCSA_PH_TOTAL" --output rails.html
```

---

## Next Steps

1. **Run workloads** using commands from `SKILLS2.md`
2. **Parse results** to Excel for data export
3. **Generate dashboard** for interactive visualization
4. **Plot TDMS** for detailed power rail analysis
5. **Compare across runs** to identify trends and regressions

For questions or issues, contact the Power KPI Validators team.

---

## File Locations Summary

| File | Path | Purpose |
|------|------|---------|
| `dashboard_gui_v2.py` ⭐⭐ **LATEST** | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | **GUI dashboard with 6 graph types (RECOMMENDED)** |
| `dashboard_gui.py` (v1) | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Original GUI (legacy, use v2 instead) |
| `parse_results_to_excel.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Results parser to Excel |
| `generate_interactive_html_report.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | CLI dashboard generator |
| `plot_tdms_power_rails.py` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | TDMS time-series plotter |
| `SKILLS2.md` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | Workload documentation |
| `README.md` | `C:\git\applications.ai.ocode.market.skills\.opencode\skill\powerkpi\` | This file |
| Hopper results | `C:\_hopper_results\` | All workload outputs |

---

## Graph Type Comparison Guide

| Graph Type | Best For | When to Use |
|------------|----------|-------------|
| **Bar Chart** | Simple comparison across workloads | Comparing mean values of 3-10 metrics across 2-5 workloads |
| **Grouped Bar** | Side-by-side metric comparison | Comparing multiple related metrics (e.g., core phases) |
| **Line Graph** | Trend analysis | Showing progression or patterns across metrics |
| **Scatter Plot** | Distribution analysis | Finding outliers, correlations, or clustering |
| **Heatmap/Matrix** | Complete overview | Comparing ALL metrics vs ALL workloads at once |
| **Box Plot** | Statistical distribution | Analyzing min/max/quartiles, finding anomalies |

---

## Next Steps

1. **Run workloads** using commands from `SKILLS2.md`
2. **Launch GUI v2** with `python dashboard_gui_v2.py`
3. **Select graph type** based on your analysis goal (see table above)
4. **Generate dashboard** for interactive visualization
5. **Plot TDMS** for detailed time-series power rail analysis
6. **Compare across runs** to identify trends and regressions

For questions or issues, contact the Power KPI Validators team.

---

**Last Updated**: 2026-04-09  
**Author**: PowerKPI_Validator Agent  
**Version**: 2.0 - Multi-Graph Type Support
