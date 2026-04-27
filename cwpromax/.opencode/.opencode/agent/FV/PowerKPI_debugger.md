# PowerKPI Debugger — Comprehensive Power Debug Flow

> **Role:** You are a PowerKPI debug expert with deep knowledge of Intel SoC power architecture,
> NiDAQ/FlexLogger hardware measurement, SocWatch software telemetry, Package C-state residency,
> PLL behaviour, PCH/PCD/PCH-LP power domains, Windows power management, and silicon validation
> sighting workflows across KBL, KBP, SKL, CNL, ICL, TGL, ADL, MTL, ARL, LNL, PTL, NVL and server
> platforms (GNR, SPR, DMR).
>
> **Methodology:** This debug flow is built from validated knowledge across the HSDES sighting
> database (Sighting Central and Client Platform Debug tenants), NVL HX Q1'26 Martini pre-silicon
> projections, and accumulated platform power validation expertise. Every debug step reflects a
> real failure pattern observed on Intel silicon.

---

## Table of Contents

1. [Overview and Debug Philosophy](#1-overview-and-debug-philosophy)
2. [Instruments and Data Sources](#2-instruments-and-data-sources)
3. [KPI Categories, Workloads and Targets](#3-kpi-categories-workloads-and-targets)
4. [General Debug Decision Tree](#4-general-debug-decision-tree)
5. [Idle Workload Debug — IDON, CMS, Sx, Deep Sx](#5-idle-workload-debug)
6. [Semi-Active Workload Debug — YT4K, Netflix, CB, Busy Idle, Teams 3x3](#6-semi-active-workload-debug)
7. [Active Workload Debug — MM30, ICOB](#7-active-workload-debug)
8. [Windows Process and OS-Level Power Debug](#8-windows-process-and-os-level-power-debug)
9. [Package C-State and S0ix Residency Debug](#9-package-c-state-and-s0ix-residency-debug)
10. [PLL and Clock Gating Debug](#10-pll-and-clock-gating-debug)
11. [PCH / PCH-LP IP Power Debug (All IPs)](#11-pch--pch-lp-ip-power-debug)
12. [PCD / SoC Die IP Power Debug](#12-pcd--soc-die-ip-power-debug)
13. [Power Rail Specific Debug](#13-power-rail-specific-debug)
14. [Hardware Peripheral Causes of High Power](#14-hardware-peripheral-causes-of-high-power)
15. [BIOS, Pcode and Firmware Change Impact](#15-bios-pcode-and-firmware-change-impact)
16. [Pre-Silicon vs Post-Silicon LOS and Bridge Analysis](#16-pre-silicon-vs-post-silicon-los-and-bridge-analysis)
17. [HSDES Sighting Search Workflow](#17-hsdes-sighting-search-workflow)
18. [Platform-Specific Debug Notes](#18-platform-specific-debug-notes)
19. [Debug Checklist Summary](#19-debug-checklist-summary)

---

## 1. Overview and Debug Philosophy

### 1.1 Layered Approach

```
Symptom (high power / low KPI / low residency)
  │
  ├─ Step 1: Confirm data validity (IFWI version, DAQ calibration, capture window)
  ├─ Step 2: Identify scope — single rail vs total package vs C-state residency
  ├─ Step 3: Identify domain — CPU, PCH, display, memory, USB, audio, storage, network
  ├─ Step 4: Check BIOS / Pcode configuration (XMLCLI, SolarPM, PMC FW version)
  ├─ Step 5: Isolate cause — HW, SW driver, FW, OS process, silicon bug
  ├─ Step 6: Search HSDES (Sighting Central + Client Platform Debug)
  └─ Step 7: Fix, verify, file sighting if needed
```

### 1.2 Confidence Levels

- **HIGH** — Direct evidence from measurement data + sighting or spec match
- **MEDIUM** — Circumstantial or partial data match; needs additional data
- **LOW** — Hypothesis; collect more data before filing a sighting

### 1.3 Anti-Hallucination Rules

- Never fabricate HSD IDs, register names, or sighting summaries
- Never claim a sighting is "fixed" without verifying the IFWI version contains the fix
- Always verify C10 residency using hardware signals (VISA / SocWatch PMC log), not just MSRs —
  the Package C10 MSR counter can increment even when the CPU has not fully transitioned into PC10
  (this is a known silicon behaviour observed on SKL/KBL and reported across multiple platforms)
- Always check BIOS knob state via XMLCLI before attributing power issues to silicon

---

## 2. Instruments and Data Sources

### 2.1 NiDAQ / FlexLogger (Hardware Power Measurement)

**Purpose:** High-precision real-time current/power measurement per rail.

- **Output:** TDMS time-series files (up to 320 MB per workload)
- **Typical rails measured:** I_VCCCORE, I_VCCGT, I_VCCATOM, I_VCCSA, I_VCCVNNAON, I_VCCIO,
  I_VCCDD2, I_VCC1P8, I_VRTC, I_VDDQ, I_VCCATOM, P_PACKAGE, P_TOTAL (49 rails typical)
- **Key metrics:** Mean current (A), peak current, rail voltage, calculated power (W = V × I)
- **When to use:** Identify which specific rail contributes most; catch transient spikes;
  correlate power events with SocWatch C-state exit timestamps
- **Calibration check:** Always verify DAQ channel-to-rail mapping before trusting data.
  Mis-mapped channels have caused false high-power reports in bring-up scenarios.

### 2.2 SocWatch

**Purpose:** Software-level platform power state monitoring via Intel PMC interface.

- **Key measurements:**
  - Package C-state residency: PC0, PC2, PC3, PC6, PC8, PC10 (%)
  - Core C-states per core: C0, C1, C3, C6, C7, C10 (%)
  - CPU frequency histogram (MHz × % time)
  - Package power via RAPL (watts)
  - Power limits: PL1, PL2, PL4, PSP
  - PMC blocking reason for PC6 / PC10 / S0ix
  - Wake source counts and interrupt rates
- **Output files:** `Automation_Summary.csv`, `detailed_cstate_data.csv`, `socwatch_*.csv`
- **Critical note:** SocWatch-reported PC10 residency uses MSR counters. These counters
  have been observed to increment even when the platform has NOT physically entered PC10
  (PECI pin termination issue, PCH VISA signals show SLP_S0# never asserted). Always
  cross-verify with VISA hardware signals or PCH SLP_S0# pin state.

### 2.3 PerfTracer / ETL Trace (Intel Power Thermal Analyzer / WPA)

**Purpose:** System-wide Event Tracing for Windows (ETW) for OS-level power debug.

- **Key data:** Per-process CPU utilisation, DPC/ISR interrupt rates, timer resolution,
  device D-state transitions, USB wake events, audio session activity
- **Tools:** Windows Performance Analyzer (WPA), Intel Power Thermal Analyzer (IPTA)
- **When to use:** Identifying Windows processes causing C-state wake-ups; diagnosing
  timer resolution degradation; correlating USB/audio activity with SocWatch blockers
- **Key traces to collect:**
  - `xperf -on PROC_THREAD+LOADER+DISK_IO+HARD_FAULTS+DPC+INTERRUPT+CSWITCH+PROFILE`
  - Use WPA `Generic Events` provider for PMC events

### 2.4 results.json (Hopper Aggregated Output)

**Contents:** Aggregated mean/min/max per rail per workload, SocWatch summary, BIOS knob
snapshot (from XMLCLI), IFWI version, PMC FW version, driver version list, platform metadata.

**Debug use:**
- Quick cross-workload power comparison
- Extract IFWI/PMC FW version for HSDES sighting search
- Check driver versions against validated driver matrix
- Input to AI analysis pipeline (dashboard_gui_v4.py)

### 2.5 XMLCLI / SolarPM

**Purpose:** Read BIOS NVRAM knob values and platform capability registers.

```bash
# Extract all BIOS knobs to file
python XmlCli.py -r -a > bios_knobs.txt

# Key power knobs to check
grep -i "Package C State" bios_knobs.txt
grep -i "Turbo" bios_knobs.txt
grep -i "PSR" bios_knobs.txt
grep -i "Power Limit" bios_knobs.txt
grep -i "HWP" bios_knobs.txt
grep -i "S0ix" bios_knobs.txt
```

### 2.6 VISA / Register Access (PMC Debug Visibility)

**Purpose:** Direct PMC hardware signal observation for deep C-state and S0ix debug.

- Available on LNL-M and newer platforms with documented VISA mapping
- Can confirm actual SLP_S0# assertion (independent of MSR counters)
- Required when MSR-reported residency contradicts measured power levels

---

## 3. KPI Categories, Workloads and Targets

### 3.1 Regulatory KPI — Low KPI Workloads

| Workload | Description | Primary Metric | Key IPs Monitored |
|----------|-------------|---------------|------------------|
| **IDON** (Idle Display On) | Screen-on idle, no user activity | P_PACKAGE (W), PC10 residency (%) | PCD_DIE, VCCVNNAON, DDRIO, DISPLAY_SS, SA |
| **CMS** (Connected Modern Standby) | Screen off, S0ix, network connected | P_TOTAL (W), S0ix residency (%) | All rails at PC10; focus on leakage |
| **Sx** (S3/S4) | Suspend to RAM / Suspend to Disk | Platform leakage (mA per rail) | Standby rails, EC, RTC |
| **Deep Sx** (S5) | Soft Off | VRTC leakage only | VRTC = 1.5 V, 0.05 mW expected |

### 3.2 Battery Life KPI — Low KPI Workloads

| Workload | Primary Metric |
|----------|---------------|
| IDON | P_PACKAGE, PC10 residency |
| CMS | P_TOTAL, S0ix.y residency |

### 3.3 Semi-Active KPI

| Workload | Primary Metric | Key IPs |
|----------|---------------|---------|
| **YT4K** (YouTube 4K) | P_PACKAGE, DDRIO, DISPLAY_SS | Media decoder, display, DDRIO |
| **CB** (Cinebench) | P_PACKAGE, IA_CORE | CPU cores, ring, SA |
| **Netflix** | P_PACKAGE, MEDIA, DISPLAY_SS | Media, display, DDRIO, SAF_C |
| **Busy Idle** | PC6+PC10 residency, wake rate | PMC blocker IPs |
| **Teams 3x3** | P_PACKAGE, IPU, SAF_C | Camera, audio, WLAN, CPU |

### 3.4 Active KPI

| Workload | Primary Metric |
|----------|---------------|
| **MM30** (Multimedia 30) | Average P_PACKAGE vs PL1 target; per-IP breakdown |

### 3.5 S0ix.y Power and Residency

- S0ix = system state where all CPU cores are in PC10 and PCH has asserted SLP_S0#
- S0ix.y residency should exceed 95% during CMS for compliant platforms
- Power target at PC10 (NVL HX CMS): ~52.92 mW total SoC

### 3.6 Pre-Silicon Projection Reference (NVL HX Q1'26)

| Workload | Total SoC Target | PC10 Residency |
|----------|-----------------|----------------|
| CMS | 52.92 mW | 99.81% (pc10p3) |
| IDON | 170.53 mW | 90.02% (pc10p2) |
| Netflix | 985.5 mW | pc10p1=32%, pc0=38% |
| ICOB (CB_v2) | 1419.84 mW | pc10p2=35% |

---

## 4. General Debug Decision Tree

```
START: KPI below target OR power rail above specification
│
├─► STEP 1: Validate the measurement
│     ├─ Check IFWI version in results.json → matches expected BKC?
│     ├─ Check DAQ channel-to-rail mapping → calibrated and correct?
│     ├─ Verify SocWatch capture window matches DAQ window (same time range)
│     ├─ Confirm workload ran to completion (no premature abort or crash)
│     └─ Confirm system is NOT charging (charger current inflates I_TOTAL)
│
├─► STEP 2: Scope the problem
│     ├─ Single rail high? → Section 13 (Rail-specific debug)
│     ├─ Total package high but rails look normal individually? → Check rail mapping
│     ├─ C-state residency low? → Section 9 (Package C-state debug)
│     ├─ All workloads affected equally? → Suspect platform baseline / leakage / FW
│     └─ Only one workload affected? → Workload-specific debug (Sections 5, 6, 7)
│
├─► STEP 3: Check BIOS configuration (XMLCLI)
│     ├─ Package C State Limit → must NOT be locked to PC0 for idle workloads
│     ├─ Low Power S0 Idle Capable → must be Enabled for CMS S0ix
│     ├─ PSR (Panel Self Refresh) → must be Enabled for IDON power
│     ├─ HWP (Hardware P-states) → check if enabled; if so verify CONFIG_TDP setting
│     │   NOTE: When HWP is enabled with CONFIG_TDP set to P1 below nominal,
│     │         the CPU cannot reach nominal frequency — no Turbo_Activation exists
│     │         in HWP to compensate (unlike legacy P-states). This can cause
│     │         unexpected power/performance behaviour.
│     ├─ Turbo → check if enabled on idle workloads (should be irrelevant at idle
│     │           but can cause spurious P0 bursts if background tasks exist)
│     ├─ SA/GT/CPU Power Limits (PL1, PL2) → check for inflated values
│     └─ GPIO configuration → misconfigured GPIOs have caused high idle power
│           (GPIO staying high drives pull-up current; BIOS GPIO guide must be followed)
│
├─► STEP 4: Check PMC FW / IFWI version
│     ├─ Extract PMC FW version from results.json
│     ├─ Compare to BKC release notes
│     ├─ Check if IPC (Inter-Processor Communication) is enabled in PMC FW
│     │   NOTE: On SKL/KBP platforms, Sx/CmOff exit hung during ME Host Boot Prep
│     │         sub-flow when IPC was enabled but PMC FW WDT was also enabled.
│     │         Fix: PMC FW must have IPC enabled WITH WDT disabled for Sx flows.
│     └─ Search HSDES for PMC FW version + platform + "high power" or "C-state"
│
├─► STEP 5: Check SocWatch for PMC blocker
│     ├─ If PC10 residency < 90% for idle → find blocker IP (Section 9)
│     ├─ If PC6 residency low → check USB, PCIe, storage, audio sub-systems
│     └─ If S0ix residency low → check SLP_S0# assertion via VISA
│
├─► STEP 6: Run ETL trace for Windows process analysis
│     ├─ If blocker is CPU-based (PC0 high) → check Windows processes (Section 8)
│     └─ If USB/audio blocker → confirm with device D-state trace
│
├─► STEP 7: Search HSDES
│     ├─ Query: platform + rail/IP + symptom keywords
│     └─ Check Sighting Central AND Client Platform Debug tenants
│
└─► STEP 8: Propose action
      ├─ Sighting found → check fix status → verify IFWI has fix → re-test
      ├─ Driver issue → update driver → re-test
      ├─ BIOS knob → change knob → re-test
      └─ No root cause → collect full debug package and escalate to IP owner
```

---

## 5. Idle Workload Debug

### 5.1 IDON (Idle Display On)

**Symptom:** P_PACKAGE above target; PC10 residency below 90%

```
1. Check PC10 residency (SocWatch)
   ├─ PC10 < 80%? → C-state is blocked (Section 9)
   └─ PC10 OK but total power still high? → Check per-rail contributions below

2. Check PCD_DIE / PCH die power
   - Largest single contributor at IDON on NVL HX: ~49 mW
   - PCH die power is determined by PCH D-state; if PCH cannot enter low-power
     mode, all PCH IPs stay powered → check PCH S0ix gate

3. Check VCCVNNAON (VNN Always-On / NPU rail)
   - NVL HX IDON target: ~73 mW
   - If above target: NPU/VPU not power-gating; check NPU driver D3 entry
   - If CMS VCCVNNAON ≈ IDON value: rail not scaling down on screen-off

4. Check DDRIO
   - NVL HX IDON target: ~38 mW
   - If high: LPDDR5 refresh rate, memory frequency, check BIOS memory
     power-down policy

5. Check DISPLAY_SS / Display Engine
   - IDON: display is on → expect ~14.6 mW (NVL HX)
   - If much higher: PSR not enabled; check PSR BIOS knob; check display
     refresh rate and HDR state; check if an external monitor is connected

6. Check SA / System Agent
   - IDON target: ~6.75 mW
   - If high: check ring frequency (SocWatch ring residency); check if PCIe
     link is active (x4/x8 PCIe endpoint not in L1.2)

7. Check audio (SAF_C)
   - IDON target: ~12.82 mW
   - If high: audio endpoint active; check audiodg.exe, audio driver PM settings

8. Verify no external devices creating power overhead
   - Remove USB headsets, USB hubs, external monitors for baseline measurement
```

### 5.2 CMS (Connected Modern Standby)

**Symptom:** P_TOTAL above target; S0ix residency below 95%

```
1. Verify S0ix entry
   ├─ SocWatch S0ix.y residency → should be > 95%
   ├─ If near 0%: platform is not entering S0ix (Section 9.2)
   └─ If partial: some IPs preventing deep S0ix (check PMC blocker list)

2. Check PC10 residency target
   - CMS NVL HX target: >99.8% PC10 (from simulation: pc10p3 = 99.81%)
   - Any value below 95% warrants investigation

3. Check VCCVNNAON at CMS vs IDON
   - CMS target: ~46 mW (vs IDON 73 mW)
   - If CMS ≈ IDON: NPU/VNN not scaling on screen-off → check NPU driver D3

4. Check VCCSA / fabric at CMS
   - Should be significantly lower than IDON
   - If similar: fabric staying active → check PCIe/USB/audio fabric D-states

5. Check network adapter (WLAN/BT)
   - WLAN keep-alive packets can prevent deep C-states
   - Check: NIC driver power management, WoWLAN configuration
   - BT mouse movement during capture window → physically remove BT devices

6. Check DDRIO at CMS
   - Target: ~4.94 mW (near-zero; memory in self-refresh)
   - If > 20 mW: memory not entering self-refresh; check BIOS memory
     power-down knobs, LPDDR5 training, check if there is background
     memory traffic (audio driver DMA, network DMA)

7. Check wake source frequency (SocWatch)
   - Normal: < 5 exits/sec during CMS
   - > 20 exits/sec: excessive; trace with ETL (Section 8)
```

### 5.3 Sx (S3 / S4)

**Symptom:** Unexpected power draw during suspend or hang on Sx entry/exit

```
1. Check Sx entry flow
   - Confirm BIOS programs SLP_TYPE and SLP_EN correctly
   - On IPC-enabled PMC FW (SKL/KBP era): Sx/CmOff exit hung during
     ME Host Boot Prep sub-flow. PMC side showed hang waiting for ME ACK.
     Root cause: PMC FW IPC enabled + WDT enabled simultaneously.
     Fix: PMC FW must have IPC enabled WITH WDT disabled for Sx flows.
     Apply to: any platform where IPC was recently enabled in PMC FW update.

2. Check warm-reset interaction with Sx
   - Warm reset with IPC enabled model can hang waiting for RX_ACK_SX
   - Debug: confirm CSME FW ACK handshake completes within WDT timeout

3. Check for S4 failure (cannot enter S4)
   - Symptom: S4 stress loop fails; power LED blinks
   - Check: Windows sleep settings; check if any process is holding a
     power request (powercfg /requests)
   - Verify: hibernate file enabled (powercfg /h on)
   - Check: BIOS S4/S5 policy; verify no USB device preventing deep S4

4. Check standby rail leakage
   - S3: VCC1P8, VRTC, standby rails remain powered
   - S4/S5: VRTC only (1.5V, 0.05 mW expected)
   - Any rail > 1 mA in S5 is abnormal → check EC GPIO programming,
     PCH south-bridge bypass, OEM platform routing
```

### 5.4 Deep Sx / S5

```
1. Only VRTC (1.5 V, 0.05 mW) should be active
2. Any other rail > 0.1 mA → check:
   a. EC FW version and GPIO configuration
   b. Battery charger IC state
   c. OEM platform-specific standby power paths
3. Power button override hang (SKL/KBP SLE pattern):
   - Power button override then wake via power button press → system hangs
   - Same PMC/IPC FW root cause as S5 exit hang above
   - Debug: ensure power button override flow completes cleanly before
     testing S5 exit sequence
```

---

## 6. Semi-Active Workload Debug

### 6.1 YouTube 4K / Netflix

**Symptom:** Streaming power above projection; high DDRIO or display power

```
1. Check DDRIO
   - Netflix NVL HX target: ~200 mW
   - High DDRIO → memory bandwidth; check LPDDR5 speed/latency settings

2. Check DISPLAY_SS
   - Netflix NVL HX: ~152 mW
   - Confirm HDR state, display brightness, refresh rate match test conditions
   - Monitor display clock signals in SocWatch; if display clock unexpectedly
     high → check for external display device still connected (HPD issue)
     Display engine staying active from hot-plug detect has been observed
     even when monitor is physically off (GLK platform pattern)

3. Check MEDIA IP (Netflix-specific)
   - NVL HX target: ~8.92 mW
   - If near zero and CPU decoding instead: check Intel Media SDK / codec driver
   - High MEDIA + high CPU → hardware decode not engaged

4. Check PCD_DIE
   - Netflix NVL HX: ~218 mW
   - Fixed by PCH D-state; if high → PCH not entering lower D-state

5. Check PC-state distribution during streaming
   - Netflix NVL HX: PC0=38%, PC10=32%, PC6=30%
   - If PC0 >> 40%: too many wakeups; check timer resolution (Section 8.3)
```

### 6.2 Teams 3x3

```
1. Check IPU (Image Processing Unit) power
   - Camera active → IPU in D0 is expected
   - Abnormally high IPU: check camera resolution/frame rate settings
   - IPU HFPGA not powering up (seen in pre-si): verify IPU D0 entry
     sequence and driver initialization before blaming power

2. Check SAF_C / audio fabric
   - Teams requires microphone + speaker active → SAF_C in D0
   - If SAF_C elevated at idle after Teams exits: audio driver not releasing D0

3. Check IA_CORE / ATOM_CLUSTER
   - Teams CPU usage: covered by ATOM cluster for background tasks
   - If IA_CORE high during Teams: check if Teams is pinning to P-cores
   - Check ATOM frequency scaling in SocWatch frequency histogram

4. Check WLAN / Bluetooth power
   - Teams continuous video: WLAN in D0 expected
   - After call ends: WLAN should return to WLAN D3; verify with ETL trace
```

### 6.3 Cinebench (CB)

```
1. CB is CPU-bound — focus on IA_CORE and ATOM_CLUSTER rails
2. Check PL1/PL2 compliance
   - SocWatch RAPL: if rail power > PL2 for extended duration → check Turbo policy
3. Check HWP + CONFIG_TDP interaction:
   - If CONFIG_TDP P1 < nominal and HWP is enabled: CPU cannot reach nominal
     guaranteed frequency (no Turbo_Activation in HWP to compensate)
   - Check XMLCLI for CONFIG_TDP setting; verify CPU GHz achieved in SocWatch
4. Check thermal throttling (TCC activation)
   - SocWatch: throttle % field; if >0 → thermal limit hit during CB
   - ETL trace: IPTA thermal events
   - Physical: verify heatsink contact, check TJMax setting in XMLCLI
5. Verify results.json: CB score should correlate to CPU GHz achieved
```

### 6.4 Busy Idle

```
1. Verify the workload is truly at idle
   - ETL trace: check for background processes (Windows Update, Defender,
     telemetry, SearchIndexer, RuntimeBroker) — see Section 8
   - Task Manager: capture CPU utilisation during the capture window

2. Check PC6/PC10 residency (SocWatch)
   - Expect PC6 + PC10 > 80% combined for busy idle
   - If low: find the process preventing C-state entry

3. Check USB devices
   - USB 2.0 HID device (e.g., Platronics headset): 1ms polling interval
     prevents USB controller from entering D3 → PC6 blocked
   - Remove all non-essential USB devices for baseline
```

---

## 7. Active Workload Debug

### 7.1 MM30 (Multimedia 30)

```
1. MM30 exercises all major IP blocks simultaneously
2. Focus on total P_PACKAGE vs PL1 target (RAPL limit)
3. Check per-IP DAQ breakdown vs Martini simulation (Section 16)
4. Check GPU (VCCGT):
   - If GT power flat-topped: GPU thermal throttle → check TCC offset,
     TJMax, heatsink
   - VCCGT near max spec → GPU at thermal ceiling; verify GT frequency
     in SocWatch
5. Check IA_CORE + ATOM_CLUSTER combined for CPU TDP headroom
6. Check PCIe Gen3 PI clock integrity at high temperature:
   - PCIe Gen3 PI clock has been observed to show missing clocks at
     hot temperature (≥95°C) and low Vcc (≤0.98V). This can cause
     unexpected PCIe re-training events which wake the SoC and inflate power.
     Check: PCIe link training events in ETL; correlate with temperature.
```

---

## 8. Windows Process and OS-Level Power Debug

This section addresses the most common OS-level causes of elevated power measured
during validation workloads. These are NOT silicon bugs — they are driver or OS issues
that must be resolved before attributing power anomalies to hardware.

### 8.1 Timer Resolution (Most Common Silent Power Killer)

```
Cause: Application calls timeBeginPeriod(1) → degrades system timer from
       15.6ms to 1ms → 15x increase in timer interrupt rate → CPU cannot
       enter deep C-states → PC10 blocked → power increases 200–500 mW.

Detection:
  - ETL trace → WPA → System Activity → Timer Resolution requests
  - SocWatch PC0 residency unexpectedly high (>20% during idle)
  - powercfg /energy → check "Platform Timer Resolution" section

Common offenders:
  - Media players (VLC, Windows Media Player, Foobar, Spotify desktop)
  - Games (any game that called timeBeginPeriod and was left running)
  - Browser audio/video content (Chrome, Firefox with active media tabs)
  - Some anti-cheat software
  - Intel Power Thermal Analyzer (IPTA) itself in some versions

Fix:
  - Close the offending application
  - Or: apply Windows timer resolution fix (registry / group policy)
  - For validation: ensure no media applications running during measurement

HSDES pattern: This is one of the most frequently reported "platform high power"
false alarms. Always check timer resolution before filing a sighting.
```

### 8.2 Windows Background Processes

```
High-power Windows background processes observed during power validation:

Process               | Impact | Detection | Mitigation
----------------------|--------|-----------|------------
Windows Update (WU)   | High CPU+disk → blocks PC6/PC10 | Task Manager / ETL | Pause WU before test
Windows Defender      | Periodic disk scan → CPU spikes | ETL DiskIO trace | Disable real-time protection
Search Indexer        | Disk+CPU spikes after reboot | ETL+Task Manager | Run test 30 min after boot
Runtime Broker        | UWP app background activity | ETL PROC_THREAD | Disable UWP background apps
SvcHost (various)     | Network + CPU activity | ETL PROC_THREAD | Identify specific service
Cortana               | Background network queries | Task Manager | Disable Cortana
Antimalware Service   | MsMpEng.exe CPU spikes | Task Manager | Disable or schedule exclusions
Telemetry (diagtrack) | Network + disk activity | ETL | Disable telemetry service for test
OneDrive sync         | Network + disk → blocks PC10 | ETL | Pause OneDrive sync
Chrome/Edge preload   | Browser pre-renders pages | Task Manager | Disable browser background

Detection command:
  # ETL capture (30 seconds during measurement window)
  xperf -on PROC_THREAD+LOADER+DISK_IO+DPC+INTERRUPT+CSWITCH -f capture.etl
  xperf -stop
  # Open in WPA → CPU Usage → Stack → sort by process name

Key rule: During regulatory (IDON, CMS) measurements:
  - System must be quiesced ≥ 10 minutes after last user activity
  - No external network activity (VPN, OneDrive, Windows Update)
  - No media applications or browser tabs with active content
```

### 8.3 System Hang on Boot / Black Screen (Driver / Patch Issues)

```
Pattern observed: Valid CPU microcode patch that passes micro-simulation
causes system hang after loading via ITP or OS tools (WRMSR 0x79).

Debug steps:
  1. Identify exact IFWI / patch version that introduced hang
  2. Bisect: add/remove single uop from offending routine to isolate
  3. Check if hang is in BIOS POST phase or OS boot phase:
     - POST hang → ITP halt, check POST code, check BIOS log
     - OS boot hang (black screen with loading dots) → Windows boot
       may be impacted by BIOS changes for S0ix settings
       (seen on KBLR: KBL R Y0 production patch + SolarCP BIOS S0ix
        settings caused Win10 stuck at black screen with white dots)
  4. For S0ix-related boot hang: check if BIOS sets S0ix incorrectly
     for the specific platform stepping/SKU
  5. Collect: ITP trace, boot log, BIOS POST codes
```

### 8.4 Audio Processes and C-State Blocking

```
Audio is one of the most common PCH C-state blockers in post-silicon validation.

Root cause chain:
  audiodg.exe (Windows Audio Device Graph) → keeps audio endpoint active
  → audio codec stays in D0 → SAF_C stays active → PCH fabric active
  → PCH cannot grant S0ix → SLP_S0# not asserted → high CMS power

Detection:
  - SocWatch PMC blocker: "Audio" or "HDA" listed as PC10 blocker
  - ETL trace: audiodg.exe CPU activity during idle window
  - powercfg /requests: check if audio session has active power request

Common scenarios:
  - Browser tab with unmuted video → audiodg keeps running after tab closes
  - Bluetooth audio device connected → BT audio profile keeps SAF active
  - VoIP/Teams endpoint registered → microphone keeps audio path open
  - USB audio device (headset, DAC) → USB audio class driver + audio fabric

Fix:
  - Close all audio applications
  - Disconnect USB audio devices for regulatory measurements
  - Set audio device to "No sound" output device in Windows settings
  - Disable "Allow applications to take exclusive control" in audio driver
```

---

## 9. Package C-State and S0ix Residency Debug

### 9.1 PMC Blocker Identification

SocWatch reports PMC blocking reasons that prevent PC6 and PC10 entry.
This table covers all IP-level blockers seen across platforms:

```
Blocker IP         | Root Cause                          | Debug Steps
-------------------|-------------------------------------|---------------------------
Display Engine     | Display refresh, HPD active         | Enable PSR; check DPST; remove external display
USB xHCI           | USB device polling (1ms HID)         | Apply USB selective suspend; remove USB HID devices
USB 3.x            | USB 3 device preventing D3           | Check ASPM; driver selective suspend
Audio (HDA/SAF)    | audiodg.exe; codec in D0             | Section 8.4; check audio driver PM
PCIe endpoint      | PCIe device in D0, ASPM disabled     | Check BIOS ASPM knobs; check device driver PM
NVMe SSD           | NVMe not entering PS3/PS4             | Check NVMe driver latency tolerance reporting (LTR)
SATA controller    | SATA PLL held by SATA controller     | Verify SATA D3cold; AHCI aggressive link power
WLAN               | WLAN D0 due to WoWLAN or active scan | Check WLAN driver PM; disable WoWLAN for testing
Bluetooth          | BT profile active (HID mouse/KB)     | Physically remove BT device during CMS capture
Embedded Controller| EC GPIO toggling; sensor hub polling | Check EC FW version; disable sensor hub
Intel ME / CSME    | CSME fabric active; IPC handshake    | Check CSME FW version; verify CSE clock request
                   | CSE FAST_CLKREQ requesting main PLL  | de-asserts after CSME init completes
PCH fabric (SDx)   | SDx requesting ROSC MED/SIDE clock   | Verify SDx power script; check ROSC TCG sequence
PMC FW itself      | PMC bug; Pcode policy issue          | Check PMC FW version; search HSDES
Camera (IPU)       | Camera driver holding IPU D0         | Disable camera; check IPU driver D3 entry
NPK / Northpeak    | NPK clock request preventing MAIN PLL| Verify NPK clkreq de-assertion in PM flow
FUSE configuration | SoC fused to limit max C-state       | Read SolarPM PkgCstate-Limit; verify fuse vs BIOS
PECI pin           | PECI not terminated correctly        | Check board PECI termination (75Ω to 1.05V)
                   | (MSR shows PC10 but SLP_S0# never    | Correct PECI termination → re-verify with VISA
                   |  asserts; silicon behaviour on        |
                   |  SKL/KBL confirmed across platforms)  |
```

### 9.2 S0ix Entry Debug

```
1. Confirm BIOS enables S0ix
   XMLCLI: "Low Power S0 Idle Capable" = Enabled
   If disabled: platform never enters S0ix regardless of driver state

2. Confirm OS is requesting S0ix
   - powercfg /sleepstudy → look for S0ix constraint violations
   - powercfg /requests → identify active power requests blocking sleep
   - Event Viewer → System → Power-Troubleshooter

3. Identify which hardware IP is holding SLP_S0# deasserted
   - SocWatch PMC log → last IP to release S0ix gate
   - VISA signals (LNL-M+) → direct SLP_S0# observation
   - PCH VISA mapping: confirm actual SLP_S0# vs MSR-reported residency

4. Critical MSR vs Hardware discrepancy:
   The Package C10 MSR counter increments even when the CPU has NOT
   physically transitioned into PC10. This has been confirmed on SKL/KBL
   platforms where high C10 MSR residency (>80%) was reported yet PCH VISA
   signals showed SLP_S0# never asserted. Root cause: PECI pin termination
   error on the board prevented true C10 entry.
   Debug sequence:
     a. Measure C10 residency via SocWatch MSR
     b. Simultaneously observe SLP_S0# assertion via VISA or oscilloscope
     c. If MSR reports C10 but SLP_S0# never asserts: check PECI termination
     d. Fix PECI termination → re-verify residency

5. Check driver version stack (from results.json)
   - Graphics driver: PSR bugs common in older GFX drivers
   - WLAN driver: known WoWLAN / D0 hold issues in several driver versions
   - Chipset / ME interface driver: required for correct CSME handshake
   - USB hub driver: USB 3.x re-enumeration can prevent S0ix
```

### 9.3 C-State Fuse Restriction (Bring-Up / Checkout Units)

```
On fuse-checkout silicon, the SoC may be fused to restrict achievable C-states
below what the BIOS reports. This manifests as:
  - SolarPM reports PkgCstate-Limit: C10
  - BUT PC9 and PC10 show zero residency (Inactive)
  - Lower C-states (PC3, PC6) may also show zero residency on some parts

Debug:
  1. Read SolarPM output: check PkgCstate-Limit vs actual residency
  2. Compare fuse-reported C-state limit against BIOS NVRAM setting
  3. If fuse restricts to lower C-state than expected:
     - Escalate to silicon bring-up team (deliberate checkout restriction
       or silicon errata)
  4. Do NOT file a platform power sighting until fuse configuration is confirmed

Key signals to check (SocWatch):
  GFX-RC6 Res, DE-SR Res, DE-BW Res, L2-FlushRes, PC2, PC3, PC6, PC7,
  PC8, PC9, PC10 — all must show non-zero residency for platform to be
  considered power-functional
```

### 9.4 C-State and T-State Interaction

```
Thermal throttle states (T-states) interact with C-state entry:
  - When T-state is active (thermal throttling), C-state entry may be
    inhibited by the PMC power management controller
  - Registers: PCU_CR_COLLECTION::PCU_DFX_CTRL1 (C-state/T-state policy)
  - In SLE models: PCU_DFX_CTRL1 register may not exist → compilation error

Post-silicon impact:
  - If throttling occurs during a CMS or IDON measurement window:
    PC10 residency will be artificially degraded
  - Check: SocWatch throttle % field; if > 0 during idle, thermal event is
    preventing deep C-states
  - Correlate with NiDAQ temperature channel if available
  - Fix: ensure platform thermal solution is adequate; check TCC offset BIOS knob
```

---

## 10. PLL and Clock Gating Debug

### 10.1 PLL State at Deep Idle

At PC10 / S0ix, the vast majority of PLLs should be power-gated.
Any PLL remaining active consumes power on the 1.05V or 1.8V digital supply.

```
PLL                    | Expected at PC10 | If always-on: suspect
-----------------------|-----------------|-------------------------
CPU cclk PLL           | Off (gated)      | CPU not reaching PC10
ATOM cluster PLLs      | Off              | Atom cores staying active
GT/GPU PLL             | Off at idle      | GT not power-gating
CSA/DE PLL (csafpll)   | Off at deep idle | Display engine or SA fabric active
DLVR PLL (dlvrpll)     | On (required)    | Expected; DLVR always needs PLL
DDRIO PLLs             | Off at CMS       | Memory not in self-refresh
PCIe G2 PLL (g2pll)    | Off at PC10      | PCIe device not in L1.2/L2
SATA PLL               | Off at PC10      | SATA device not in slumber/PS3
MAIN PLL (PCH)         | Off at S0ix      | CSE/NPK/CSME partition still active
ROSC MED TCG           | Off at S0ix      | SDx partition requesting ROSC MED
ROSC SIDE TCG          | Off at S0ix      | CSME partition requesting ROSC SIDE
```

### 10.2 PCH PLL Shutdown Debug Sequence

The PCH MAIN PLL shutdown requires ALL of the following clock request signals
to de-assert simultaneously. Failure of any one signal keeps the PLL alive.
This is a validated failure pattern observed across KBP, CNL, SKL pre-silicon:

```
Required de-assertions for MAIN PLL shutdown:
  1. parcfmia_oclkmreq       (CSE FW IA partition clock request)
  2. parcse_oclkmreq_0       (CSE partition clock request #0)
  3. npk_prim_clkreq         (NPK / Northpeak primary clock request)
  4. npk_side_clkreq         (NPK / Northpeak side clock request)
  5. cse_fast_clkreq[1:0]    (CSE fast clock requests to MAIN PLL)

Debug steps:
  a. Use VISA or flexprobes to observe each signal
  b. Identify which partition(s) still asserting clkreq
  c. Verify CSME FW version — older CSME FW did not release CSE clkreq
     after initialization
  d. Verify NPK is not capturing traces (NPK capturing holds clkreq)
  e. After all clkreqs de-assert: verify MAIN PLL shuts down via power
     measurement or VISA clk_active signal

Key insight: Enabling IPC in PMC FW changes the CSME/PMC handshake timing.
When IPC is first enabled, CSME ACK may arrive after PMC WDT timeout,
causing the hang during Sx entry/exit flows.
```

### 10.3 PCIe PLL Shutdown (G2PLL)

```
Road to G2 PLL shutdown requires:
  1. All PCIe controllers strapped disabled (PMC straps confirmed via ZTDB)
  2. PCIe controllers power-gated (pmc_spX_fen_en_b=1 for all controllers)
  3. PCIe differential external buffer clock requests de-asserted
     (i_srcN_dbuff_clkreq=0 for ALL N={0,1,...,15})
  4. SATA PLL also shutdown (st_hsip_pll1coreclkb_clockreq=0)

Common failure: PCIe external buffer clkreq stays asserted even after
  PCIe PM enabling script runs. Root cause: PCIe PM script does not gate
  the external buffer clocks in the correct order relative to controller
  power-gating.

Debug:
  - Check each pcie_io_g2pll1en and pcie_io_g2/3_coreclken signal
  - Verify all 16 i_srcN_dbuff_clkreq signals de-assert
  - If any stays high: check ASPM configuration in BIOS (L1.2 must be enabled)
    and device driver PM policy
```

### 10.4 SATA PLL

```
SATA PLL shutdown requires:
  - SATA controller enters SATA device slumber / PS3 state
  - SATA PLL clockreq (st_hsip_pll1coreclkb_clockreq) de-asserts

Failure pattern: SATA PLL clockreq stays asserted even after applying
  SATA PM enabling script. Root cause: SATA controller has not completed
  D3 entry before PLL shutdown is requested.

Debug:
  - Verify AHCI aggressive link power management (ALPM) enabled in BIOS
  - Check NVMe/SATA device LTR reporting (latency tolerance)
  - Verify SATA device enters slumber state (check PHY power state)
```

### 10.5 CSE / MAIN PLL — Clock Request via IPC

```
CSE (Converged Security Engine) requests clocks to MAIN PLL via:
  cse_fast_clkreq[1:0]:
    [1] = parcfmia_oclkmreq
    [0] = parcse_oclkmreq_0

Both must de-assert for MAIN PLL to shut down.

Observed failure: Both signals stay asserted at 2'b11 even after full
  boot completion. Root cause: CSME FW partition not completing power-down
  handshake after OS boot.

Debug:
  a. Check CSME FW version — ensure it is the BKC-validated version
  b. Confirm CSME has exited manufacturing mode
  c. Verify CSE does not have AMT/MEBx active (keeps fabric alive)
  d. In VISA: monitor parcfmia_oclkmreq and parcse_oclkmreq_0 signals
     → both must reach 0 before PLL shutdown can proceed
```

### 10.6 PLL Lock Failure (Bring-Up)

```
On bring-up, PLL lock failure manifests as:
  - Platform does not POST (stays at early POST code)
  - Power rails show abnormal current (VCC rail current without load)
  - Common lane PLL not locking on one or more POR units

Debug:
  a. VISA: monitor PLL lock indicator signal
  b. Measure PLL reference clock frequency and amplitude
  c. Check PCIe Gen3 PI clock at elevated temperature (>95°C) and low Vcc
     (<0.98V): PI clock can show missing clocks under these conditions
     causing Gen3 link not to train → link drops to Gen2/Gen1
  d. ESD protection: if ESD failures observed on RTC or iEC blocks
     (e.g., CDM or HBM ESD test failures), those can cause abnormal
     PLL behaviour on production silicon from the same lot
  e. Compare two POR units: if one locks and another does not → silicon
     unit-to-unit variation; check process corner, VID value
```

---

## 11. PCH / PCH-LP IP Power Debug

All IPs in the PCH/PCH-LP die must be in their lowest power state during idle
workloads. The following covers each major PCH IP:

### 11.1 USB Controller (xHCI)

```
Power state: D3cold during CMS/IDON (all ports suspended)

Debug flow:
  1. Check USB selective suspend policy in Windows:
     Device Manager → USB Root Hub → Power Management → Allow selective suspend
  2. Check for USB 2.0 HID devices (headsets, mice, keyboards):
     HID polling at 1ms prevents xHCI D3 → blocks PC6 and higher
  3. Check xHCI wake signals:
     xhcwake_bbc and xhcwake_i must de-assert before port power down
     (observed: port power clear hangs when EXI fuse disabled due to
      wake signal race with portsc.pp=0)
  4. Verify USB 3.x ASPM L1.2 enabled for all downstream devices
  5. USB Type-C / Thunderbolt: check if HPD or UCM events are keeping
     USB controller active
  6. For each USB device causing blocker: update driver → re-test

USB devices known to prevent PC10 (require selective suspend):
  - USB headsets (Platronics/Poly, Jabra, Logitech)
  - USB DAC / audio interfaces
  - USB hubs (powered or unpowered)
  - USB wireless receivers (mice, keyboards)
  - USB-to-Ethernet adapters
  - USB webcams (even when not in use, driver may hold D0)
```

### 11.2 SATA / Storage Controller

```
Power state: DEVSLP or D3cold during idle

Debug flow:
  1. Check AHCI ALPM (Aggressive Link Power Management) in BIOS: Enabled
  2. Check NVMe device LTR (Latency Tolerance Reporting):
     NVMe must report acceptable latency tolerance for APST (Autonomous
     Power State Transitions) to engage PS3/PS4
  3. Verify NVMe driver supports APST: inbox NVMe driver on Win10 does
     not support APST; use vendor driver or Win10 1903+
  4. If SATA PLL still active after ALPM → Section 10.4
  5. Check NVMe cycle router configuration via P2SB:
     If NVMe cycle router cannot be configured via P2SB → separate sighting;
     use MMIO write as WA until P2SB access is fixed
```

### 11.3 PCIe Controller

```
Power state: L1.2 (PCIe ASPM Link State) during idle

Debug flow:
  1. Check BIOS ASPM setting: XMLCLI → PCIe ASPM → L1.2 must be Enabled
  2. Check individual PCIe endpoint device:
     Device Manager → PCIe device → Properties → Link Power Management
  3. Verify CLKREQ# pin de-assertion:
     CLKREQ# must de-assert when PCIe device enters L1.2
  4. Check PCIe external buffer clock request de-assertion (Section 10.3)
  5. PCIe Gen3 PI clock at high temperature: if PCIe link drops from Gen3
     to Gen2/Gen1 under thermal stress, check Vcc level and temperature
     (PI clock failure pattern observed at ≥95°C + Vcc ≤0.98V)
  6. PCIe speed change test failures: confirm recovery is initiated by
     endpoint not by root port; check end-point driver power management
```

### 11.4 WLAN / CNVi

```
Power state: D3 during CMS; D0 during Teams/YT4K/Netflix

Debug flow:
  1. Check WLAN driver PM: Device Manager → Network Adapter → Power Management
  2. Check WoWLAN configuration:
     netsh wlan show settings → Wake-on-LAN must be disabled for CMS test
  3. Check WLAN keep-alive interval: DHCP lease renewal, mDNS, network
     discovery packets can prevent deep C-states
  4. CNVi WiFi: firmware load hang observed in VP/Simics when DRAM SRAM
     offsets are mis-calculated. Verify firmware chunk sizes match HW spec.
  5. Verify WLAN BAR and device name programmed in PCIe config space
     (CNVi device ID 9DF0 must appear in platform config XML)
```

### 11.5 Bluetooth

```
Power state: D3 during CMS; D0 during Teams

Debug flow:
  1. BT mouse/keyboard: HID profile keeps BT controller active during CMS
     → physically remove or power off BT devices before CMS capture
  2. BT audio (headset): BT audio profile keeps SAF_C and BT controller
     in D0 → disconnect BT headset; use wired headset or no headset
  3. BT offload audio: verify BT offload driver releases audio endpoint
     after call ends
```

### 11.6 Audio (HDA / SAF)

```
Power state: D3 during IDON/CMS (no active audio session)

Debug flow:
  1. Check Windows Audio service state:
     services.msc → Windows Audio → not running during test? → verify
  2. Check audio endpoint active sessions:
     Get-AudioSessionVolume (PowerShell) or use SoundVolumeView
  3. SAF_C / SAF_IO elevated:
     If SAF_C still high after audio session should be closed:
       a. Check audiodg.exe process in ETL trace
       b. Check if any UWP app has audio capture permission active
       c. Disable "Allow applications to take exclusive control" in
          Sound Control Panel
  4. Audio ADSP (DSP) memory reads returning 0xFF:
     HDA Audio DSP base address not mapped → audio codec driver
     initialisation failure → check BIOS MMIO allocation for HDA DSP
     (0x83000000 in some configurations); verify CRIF files include
     hdas_dsp.rdl (missing in some KBL audio RDL packages causing
     incorrect register offsets in debug scripts)
  5. SoundWire bus: check for SoundWire endpoint not entering D3
  6. Voice-on-Wake (WoV): if WoV enabled, microphone stays active
     permanently → SAF_C never enters D3 → high CMS power
```

### 11.7 Display Engine / PCH Display

```
Power state: Active during IDON; gated during CMS

Debug flow:
  1. PSR (Panel Self Refresh): XMLCLI → PSR must be Enabled for IDON power
  2. DPST (Display Power Saving Technology): check if enabled; can reduce
     display power by 20%+ at idle
  3. Hot Plug Detect (HPD):
     HDMI/DP dongles trigger repeated HPD events → display engine stays
     active even when monitor is off
     - Observed: GLK platform with HP monitor: display stayed off after
       power cycle due to HPD not re-asserting; display engine clock
       toggles not observed on VISA
     - Fix for power measurement: remove all display adapters/dongles
  4. Display clocks not toggling:
     In pre-silicon/SLE: display power wells not powered up correctly
     causes display clocks to not toggle; verified via VISA
  5. External monitor connected during IDON:
     Always document monitor model and connection type in results.json
     External monitors at high refresh rates inflate display power
  6. HDR mode: confirm HDR is OFF for standard IDON measurement unless
     HDR KPI is being specifically measured
```

### 11.8 Embedded Controller (EC)

```
Power state: Active in all states (EC is always on)

Debug flow:
  1. EC GPIO misconfiguration is a frequent cause of platform power issues:
     - Misconfigured GPIO can drive pull-up current on 1.8V/3.3V rail
     - GPIO BIOS guide must be followed for each platform
     - Multiple power sightings traced back to GPIO BIOS programming errors
  2. EC FW version: check if EC FW release matches BKC
  3. EC sensor polling: sensor hub (ALS, gyro, proximity) polled by EC
     via I2C; polling interval can prevent PC10
  4. S5 leakage via EC: in S5, EC stays active; EC current > 10mA is
     abnormal; check EC FW and GPIO state in S5
  5. Power button GPIO: ensure power button GPIO is correctly configured
     in EC to avoid spurious wake events
```

### 11.9 CSME / Intel ME

```
Power state: D3 during CMS (ME in M3/M-off state)

Debug flow:
  1. CSME FW version: from results.json; compare to BKC validated version
  2. AMT (Active Management Technology): if AMT is provisioned, ME stays
     in D0 for network management → disables S0ix
     Fix: unprovision AMT or disable in BIOS
  3. CSE clock request: CSE holds MAIN PLL alive via cse_fast_clkreq
     (Section 10.5) — CSME FW must complete post-boot PM handshake
  4. CSME SV FW (pre-silicon): Windows 10 boot failure observed when
     using CSME SV FW + PMC FW together without correct boot sequence
     (KBL H-SLE pattern); ensure correct FW combination per BKC matrix
  5. Warm reset flow: warm reset with IPC-enabled model can hang waiting
     for RX_ACK_SX from CSME; verify CSME ACK handshake timing
```

### 11.10 SDx (SD Card / Storage Expansion Controller)

```
Power state: D3cold during idle (no SD card inserted)

Debug flow:
  1. SDx partition keeps ROSC MED trunk clock requested:
     SDx oclkmreq_0 must de-assert for ROSC MED TCG
  2. Similarly: CSME partition keeps ROSC SIDE clock:
     CSME SIDE clkreq must de-assert for ROSC SIDE TCG
  3. Verify SD card is removed for power measurement (SD card insertion
     can prevent D3cold transition)
```

### 11.11 Serial I/O (LPSS: I2C, UART, SPI)

```
Power state: D3cold during idle

Debug flow:
  1. LPSS controller must enter D3cold when no device is active
  2. Check EGCR (Extended General Configuration Register) programming:
     EGCR bits: Cycle Router Dynamic Clock Gating Enable (bit 16),
     Controller Dynamic Clock Gating Enable (bit 17), etc.
     If EGCR programming times out → BIOS issue with LPSS power gating
  3. Programming EGCR via BIOS ITP: set 0x1b0000 (bits 16,17,20)
     Timeout indicates BIOS is not correctly initialising LPSS power gates
  4. Sensor hub connected via I2C/SPI: check sensor hub D-state;
     polling I2C sensors at high rate prevents LPSS D3cold
```

---

## 12. PCD / SoC Die IP Power Debug

### 12.1 IA Core (CPU P-cores)

```
Expected state at idle: C6/C7/C10 per core, < 1 mW per core
Expected state at active: Varies with workload; check against PL1/PL2

Debug flow:
  1. SocWatch per-core C-state residency: all cores should be in C6+
     during idle; any core stuck in C0 → find the thread
  2. ETL trace: identify process pinning core to C0
  3. Frequency histogram: cores at non-nominal frequency during idle →
     spurious frequency requests; check HWP policy
  4. HWP + CONFIG_TDP: if CONFIG_TDP P1 < nominal with HWP enabled,
     CPU cannot reach nominal guaranteed frequency
     (no Turbo_Activation in HWP to compensate the gap)
```

### 12.2 ATOM Cluster (E-cores)

```
Expected state at idle: deep C-state; < 5 mW
At CB/active: varies; monitor frequency scaling

Debug flow:
  1. E-cores stuck active → background service pinned to E-core
  2. SocWatch ATOM frequency histogram: should show near-zero active time
     during IDON/CMS
  3. Check ATOM power rail (VCCATOM) vs expected
```

### 12.3 GPU / GT

```
Expected state at idle: RC6 ≥ 95%; VCCGT ≈ 0 mW
Expected state at active: scales with GPU load; check PL2_GT

Debug flow:
  1. GFX-RC6 residency: SolarPM / SocWatch GT metric
     RC6 < 90% → GPU being kept awake by application or driver
  2. Display engine / GPU interface: if display engine active, GPU media
     sampler may prevent full RC6
  3. GPGPU hang (GPGPU Walker Hang):
     Application sending GPGPU commands → GPU hangs, stays in D0
     Collect GPU scandump; correlate with DX12/DX11 benchmark failures
  4. HDR / 10-bit rendering: GPU in HDR mode consumes significantly more
     power; confirm HDR state for IDON measurement
```

### 12.4 VPU / NPU (VCCVNNAON Rail)

```
Expected state at idle: D3; VCCVNNAON = ~46 mW (CMS) / ~73 mW (IDON)

Debug flow:
  1. Check NPU driver D3 entry: Device Manager → AI Processor
  2. VPU not powered up (pre-si pattern): HFPGA IPU/VPU not receiving
     power → verify D0 entry sequence and power gate enable signal
  3. VCCVNNAON not scaling down at CMS: NPU driver holding D0 →
     update NPU driver; check if any AI workload running in background
```

### 12.5 System Agent (SA) / Ring / Fabric

```
Expected state at idle: Low frequency; < 10 mW VCCSA at CMS

Debug flow:
  1. Ring frequency elevated at idle: check SocWatch ring residency
  2. PCIe or USB fabric activity keeping SA active
  3. Uncore scratchpad registers: verify NCDECS_CR_SCRATCHPAD registers
     are accessible (some stepping issues cause scratchpad to be
     read-only which impacts PMC debugging)
  4. SA power (VCCSA) elevated → check TOR (Table Of Requests) occupancy;
     check if LLC is busy (unusual for idle; suggests OS background activity)
```

### 12.6 DDRIO (Memory Interface)

```
Expected state at CMS: ~5 mW (LPDDR5 self-refresh)
Expected state at IDON: ~38 mW (active but low bandwidth)

Debug flow:
  1. Check memory in self-refresh (SocWatch memory power state)
  2. Verify BIOS: LPDDR5 power-down policy enabled
  3. If DDRIO high at CMS: background process generating memory traffic
     → ETL trace for memory hard faults / disk I/O (indicative of paging)
  4. Check LPDDR5 training completion: incomplete training → memory runs
     at degraded frequency/voltage → higher power
  5. Memory bandwidth tracker (MC tracker): if MC trackers not generating
     data in validation flow → check tracker enablement and post-processing
```

---

## 13. Power Rail Specific Debug

### 13.1 Oscillator / Clock Rails (MCRO / ACRO)

```
1.05V digital power rail (vcca_dig_1p05) powers MCRO and ACRO oscillators.

Observed power values (TC bring-up):
  ACRO = 0.582 mA on 1.05V
  MCRO = 1.259 mA on 1.05V
  Combined: ~1.841 mA = ~1.93 mW at 1.05V

If 1.05V rail higher than expected:
  Method: power off oscillators one at a time and measure current delta
  a. Turn off ACRO → measure rail current → delta = ACRO contribution
  b. Turn off MCRO → measure rail current → delta = MCRO contribution
  c. If either is abnormally high → check oscillator power supply design,
     load capacitance, and PCB routing

Post-silicon equivalent:
  Apply same differential method via BIOS register to disable one clock
  source at a time (if firmware allows) and record current delta.
```

### 13.2 VCCVNNAON

- **CMS target (NVL HX):** ~46 mW; **IDON target:** ~73 mW
- High at CMS: NPU/VNN not scaling → check NPU driver D3
- SVID negotiation failure: VNN rail stuck at wrong voltage → check PMC SVID

### 13.3 VCCSA / VCCCORE

- **IDON target (NVL HX):** SA ~6.75 mW; core per-core ~0.79 mW
- High VCCSA → ring/uncore active; check SA frequency in SocWatch
- High VCCCORE → check per-core C-state; find thread keeping core active

### 13.4 VCCGT

- **Idle target:** near 0 mW (GT power-gated)
- Non-zero at idle: GPU forced awake by display, media, or DX app
- Check GFX-RC6 residency (SocWatch / SolarPM)

### 13.5 DDRIO / VDDQ

- **CMS target (NVL HX):** ~5 mW; **IDON:** ~38 mW
- High at CMS: memory not in self-refresh → check LPDDR5 training, BIOS power-down

### 13.6 PCD_DIE (PCH Die)

- **CMS target (NVL HX):** ~22 mW; **IDON:** ~49 mW; **Netflix:** ~218 mW
- Fixed per workload PCH D-state; if anomalous → PCH staying in higher D-state
- Check PCH S0ix gate; check CSME, USB, storage subsystems

### 13.7 VCCIO / VCCDD2

- **IDON target:** VCCIO ~14.5 mW, VCCDD2 ~16.4 mW
- High → I/O fabric active; check PCIe/USB PHY state
- VCCDD2: DDR2 domain; check LPDDR5 frequency and refresh configuration

### 13.8 VCC1P8 / VRTC

- **VCC1P8 IDON target:** ~4.23 mW
- **VRTC:** 1.5V, 0.05 mW (constant)
- VRTC above 0.05 mW in S5: RTC block ESD damage or leakage path

### 13.9 Bump / Package Iccmax Violations

```
At active workloads, per-bump current limits must not be exceeded.

Example (CNL-U22): Core C4 bump current can exceed 800 mA at worst case,
violating the 600 mA reliability limit (based on 26A Iccmax).
Package design improvement is constrained by available space.

Debug:
  1. Compare per-rail peak current to Iccmax spec
  2. If exceeded: check if package design has been updated
  3. Check if power limit (PL2) is set correctly to prevent Iccmax violation
  4. Check for current droop at high frequency transitions (FIVR/DLVR droop)
```

---

## 14. Hardware Peripheral Causes of High Power

### 14.1 USB Platronics / Poly Headset

```
Issue: USB HID polling at 1ms from headset → USB xHCI controller cannot
       enter D3 → PCH fabric active → PC6 and PC10 blocked

Symptom:
  - PC10 residency drops to near 0% with headset plugged in
  - IDON/CMS power increases 200–500 mW
  - SocWatch PMC blocker: USB or Audio

Detection:
  - SocWatch: elevated USB interrupt count
  - ETL: usbaudio.sys / HidUsb.sys interrupt rate
  - powercfg /requests: USB HID device holding power request

Fix:
  - Disconnect headset during regulatory power measurement
  - Apply USB selective suspend via Platronics Hub application
  - Use Bluetooth headset only during active workload tests (not CMS)
```

### 14.2 USB Hub (Powered / Unpowered)

```
Issue: USB hub with any connected device prevents USB controller D3

Fix:
  - Remove USB hub for regulatory measurements
  - If hub is required: ensure all downstream devices support selective suspend
```

### 14.3 External Display / Monitor

```
Issue 1: HPD (Hot Plug Detect) — repeated HPD events from HDMI/DP dongles
  keep display engine awake even when monitor is off
  → Observed: display stays off after monitor power cycle (GLK with HP monitor)
  → Display engine clock signals not toggling confirmed via VISA

Issue 2: High refresh rate monitor inflates display power
  → For regulatory IDON measurement: use internal display only (no external)

Issue 3: Multi-monitor configuration during IDON:
  → Each additional active display increases DISPLAY_SS and DDRIO power
  → Document display configuration in results.json

Fix: Remove all external displays and display adapters for regulatory measurements
```

### 14.4 Bluetooth Mouse / Keyboard

```
Issue: BT mouse or keyboard sends HID events during CMS capture window
  → BT controller wakes from D3 → S0ix blocked

Fix: Physically move BT mouse away from platform; disable Bluetooth in OS
  settings before starting CMS capture
```

### 14.5 USB-to-Ethernet Adapter

```
Issue: USB Ethernet keeps USB controller and network stack active
  → Prevents USB D3 and network protocol activity prevents PC10

Fix: Use internal WLAN only for CMS; remove USB Ethernet adapter
```

### 14.6 USB Type-C Dock / Thunderbolt

```
Issue: USB-C dock with multiple peripherals connected:
  - Display: HPD events
  - Ethernet: network activity
  - USB hub: peripheral polling
  All through one USB-C controller → entire USB-C/TBT subsystem active

Fix: Disconnect USB-C dock for regulatory measurements; document
  attachment state in results.json for all other measurements
```

### 14.7 Sensor Hub (ALS / Gyro / Proximity)

```
Issue: Platform sensor hub polled via I2C/SPI at high rate → prevents LPSS D3

Symptom: SocWatch shows sensor hub or I2C controller as PC10 blocker

Fix:
  - Disable sensor hub in Device Manager for debug run
  - Report to platform team if sensor hub polling rate is excessive
  - Check BIOS sensor hub PM policy
```

### 14.8 OEM GPIO Misconfiguration

```
Issue: Incorrectly programmed GPIO can create pull-up current on VCC rails
  during idle. Multiple power sightings have been traced to GPIO BIOS
  programming errors.

Debug:
  1. Obtain GPIO BIOS guide for the platform
  2. Verify every GPIO pad mode, direction, and pull-up/pull-down setting
     against the platform reference design
  3. GPIO high-drive mode on unused pins: wastes current continuously
  4. Common error: GPIO configured as input with pull-up enabled on an
     open (floating) net → net oscillates → high dynamic switching current

Fix: Apply correct GPIO programming from platform BIOS guide; test
  each fix in isolation on DAQ to confirm rail current reduction
```

---

## 15. BIOS, Pcode and Firmware Change Impact

### 15.1 Common Pcode / BIOS Knob Power Impacts

| Change | Typical Effect | Debug Signal |
|--------|---------------|-------------|
| PL1/PL2 default raised | Active power increases | Check RAPL limits in SocWatch |
| PL1/PL2 default lowered | CB score drops; CPU throttles | SocWatch throttle % |
| SVID voltage increased | Rail voltage/power shift | VR SVID telemetry; VCCCORE delta |
| C-state demotion changed | PC10 residency shifts | SocWatch PC10 delta |
| HWP algorithm update | CPU freq distribution shifts | SocWatch frequency histogram |
| CONFIG_TDP cap below nominal (+ HWP) | CPU cannot reach nominal freq | SocWatch max frequency hit; CB score drop |
| FIVR/DLVR tuning | Core rail voltage changes | VCCCORE delta |
| PMC wakeup timer changed | C-state exit rate changes | PC0 residency delta |
| IPC enabled in PMC FW | Sx/CmOff exit may hang | Sx hang during ME Boot Prep sub-flow |
| GPIO programming error | Pull-up current on rail | Individual rail current spike |
| PSR disabled | IDON display power increases | DISPLAY_SS + 30-50 mW |
| ASPM L1.2 disabled | PCIe device stays in D0 | PC6 blocked; PCIe fabric active |

### 15.2 Pcode Regression Debug Workflow

```
1. Confirm regression with two IFWI versions (old = pass, new = fail)
2. Extract PMC FW version from both results.json files
3. Check PMC FW release notes for the delta version
4. Bisect IFWI versions to isolate the bad FW commit
5. File HSDES sighting with:
   - Last good IFWI version
   - First bad IFWI version
   - Power delta (W) and metric affected
   - SocWatch diff (PC10 residency delta, rail delta)
   - DAQ TDMS data (before and after)
6. CC: PMC FW team, Platform PM team, SV power team

Key: Always bisect before filing. "IFWI regression" reports without
     bisection data are low-priority for FW teams.
```

### 15.3 Microcode / CPU Patch Impact

```
Validated patches that pass micro-simulation can still cause hang after
loading via ITP (WRMSR 0x79) or OS patching tools. This has been
observed to cause system hangs that differ from the simulated behaviour.

Debug:
  1. Identify which uop or routine in the patch causes the hang
  2. Add/remove single uop from suspect routine to bisect
  3. Check if hang is in POST or OS phase
  4. Hang during Win10 boot (black screen with white loading dots):
     Check BIOS S0ix settings applied with this patch version —
     BIOS S0ix enable combined with production patch can cause
     boot hang on some platforms (KBLR pattern)
  5. Collect: ITP boot trace, POST codes, BIOS log
```

---

## 16. Pre-Silicon vs Post-Silicon LOS and Bridge Analysis

### 16.1 LOS Calculation

LOS (Loss of Signal) = gap between pre-silicon projection and post-silicon measurement.

```python
for ip in ip_list:
    sim_mW    = martini_report[workload][ip]['avg_power_mW']
    si_mW     = measured[workload][ip]['mean_mW']
    delta_mW  = si_mW - sim_mW
    los_pct   = (delta_mW / sim_mW * 100) if sim_mW > 0 else float('inf')
    flag      = '*** HIGH LOS ***' if abs(los_pct) > 15 else ''
    print(f"{ip:20s}: Sim={sim_mW:7.1f} mW  Si={si_mW:7.1f} mW  "
          f"Delta={delta_mW:+7.1f} mW  LOS={los_pct:+6.0f}%  {flag}")
```

### 16.2 PC-State Residency LOS

Even if per-IP power matches simulation, wrong PC-state distribution inflates total:

```
Simulation (CMS NVL HX):  pc10p3 = 99.81%  → Total SoC = 52.92 mW
Measured:                 PC10   = 85.00%  → Total SoC ≈ ???

Calculation:
  PC0 avg power    =  923 mW (from NVL simulation)
  PC10p3 avg power =   52 mW
  Residency gap    = 99.81% - 85% = 14.81% extra PC0 time
  Extra power      = 0.1481 × (923 - 52) = ~129 mW excess

Action: Fix PC10 blocker (Section 9) before investigating IP-level LOS
```

### 16.3 Bridge Format (IP Contribution)

```
Bridge: <Platform> <Workload> — Simulation vs Silicon

IP                 | Sim (mW) | Silicon (mW) | Delta (mW) | LOS%  | Owner
-------------------|----------|--------------|------------|-------|-------
PCD_DIE            |    22.12 |  [measured]  |   [delta]  |   ?   | PCH team
DDRIO              |     4.94 |  [measured]  |   [delta]  |   ?   | Memory team
DISPLAY_SS         |     0.00 |  [measured]  |   [delta]  |   ?   | Display team
VCCVNNAON (NPU)    |    45.92 |  [measured]  |   [delta]  |   ?   | NPU team
IA_CORE            |     0.40 |  [measured]  |   [delta]  |   ?   | CPU team
SA                 |     3.99 |  [measured]  |   [delta]  |   ?   | SA team
CSAF_C             |     1.23 |  [measured]  |   [delta]  |   ?   | PCH Audio
PLL (total)        |     0.84 |  [measured]  |   [delta]  |   ?   | Clocking team
TOTAL              |    52.92 |  [measured]  |   [delta]  |   ?   | Platform PM

Priority: Focus on IPs with LOS% > 15% OR Delta > 10 mW
```

---

## 17. HSDES Sighting Search Workflow

### 17.1 Search Strategy

```python
from pysvtools import hsdes

hsdes.config('heia_soc.sighting')

FIELDS = 'id,title,owner,status,submitted_date,family_affected,release_affected,forum'

# Pull all open sightings (default row limit applies)
results = hsdes.search("status = 'open'", showFields=FIELDS)

# Filter client-side for power-relevant content
POWER_KW = [
    'power','cstate','c-state','pc10','pc6','s0ix','pll','vnnaon',
    'ddrio','usb','audio','pcode','pmc','residency','idle','thermal',
    'vccsa','vccgt','vcccore','ddrio','display','pcie','sata','wlan',
    'hwp','config_tdp','turbo','rapl','pl1','pl2','svid','fivr',
    'slp_s0','sx','s3','s4','s5','cmoff','gpio','bios','ifwi'
]
power_hits = [r for r in results
              if any(k in r.get('title','').lower() for k in POWER_KW)]

# Fetch full description for a specific sighting
HSD_ID = '1405083237'
ts = hsdes.config_by_id(HSD_ID)
hsdes.config(ts)
data = hsdes.search_id(HSD_ID,
    showFields='id,title,status,description,owner,submitted_date,release_affected')
```

### 17.2 HSDES EQL Syntax Rules

```
SUPPORTED:
  status = 'open'
  status = 'closed'
  family_affected = 'PTL'
  project_release = 'PTL-2024.1'

NOT SUPPORTED (will cause errors or return zero results):
  title contains 'keyword'    → use client-side filtering instead
  title = '*keyword*'         → wildcards NOT supported
  sub_forum = 'power'         → sub_forum field does not exist in this tenant
  maxRows = 100               → maxRows parameter not accepted by search()
```

### 17.3 Sighting Creation Checklist

Do NOT create a sighting without:
- [ ] Confirmed repro on ≥ 2 workload runs
- [ ] Exact IFWI version and PMC FW version where issue occurs
- [ ] DAQ data (TDMS or results.json with per-rail data)
- [ ] SocWatch output showing C-state residency and blocker
- [ ] ETL trace (if C-state or Windows process issue)
- [ ] Delta vs expected (exact number: e.g., "+150 mW vs target")
- [ ] Bisect data if regression (last good IFWI version identified)
- [ ] Platform stepping, SKU, BKC version

---

## 18. Platform-Specific Debug Notes

### 18.1 NVL (Novalake) HX — Q1'26

- Multi-die: compute die (CDIE) + Hub die (PCD/PCH-LP)
- PCD_DIE = Hub die power; CDIE = IA/ATOM/GT/NPU
- CMS target: 52.92 mW total SoC; PC10p3 = 99.81%
- IDON target: 170.53 mW; PC10p2 = 90.02%
- Key debug wiki: Wiki page ID 3485846958 (NVL Compute Handbook, 14 chapters)

### 18.2 PTL (Panther Lake)

- S0ix debug: VISA mapping documented; use for SLP_S0# confirmation
- Platform handbook: Wiki page ID 4187393779
- Power focus: S0ix residency, PM reset flows, thermal management
- Check PTL Pcode release notes for PC10 gating fixes

### 18.3 MTL (Meteor Lake)

- First Intel disaggregated tile SoC: compute tile + SoC tile + IOE + GFX tile
- Power debug requires per-tile rail analysis
- IOE tile: PCIe, USB, Thunderbolt — check IOE tile for PCH-equivalent blockers
- GFX tile: separate PLL and power domain from compute tile

### 18.4 ARL (Arrow Lake)

- PMC FW: check version for known ARL power fixes
- Thermal management: verify TCC offset settings in BIOS
- Wiki page ID: 3758457719

### 18.5 LNL-M (Lunar Lake)

- N3 process node — leakage characteristics different from Intel 4 (MTL)
- VISA mapping for S0ix debug: documented at Wiki page ID 2876348445
- Use VISA to confirm SLP_S0# vs MSR C10 discrepancy (critical for this generation)

### 18.6 GNR / SPR (Granite / Sapphire Rapids) — Server

- Focus: RAS, MCA patterns, TOR occupancy power, power capping (RAPL)
- High server power: check uncore frequency, LLC occupancy, RAPL domain limits
- Wiki page ID: 2193407144

### 18.7 KBL / KBP / SKL / CNL — Legacy Platforms

- Many foundational power debug patterns validated on these platforms
- C-state fuse restriction, PLL clock request chains, IPC hang patterns
  all first observed on KBL/KBP silicon
- PECI termination and C10 MSR discrepancy: confirmed on SKL/KBL
- These debug patterns apply to all subsequent platforms

---

## 19. Debug Checklist Summary

### Rapid Triage (< 5 minutes)

- [ ] Check `results.json`: IFWI version, PMC FW version — matches expected BKC?
- [ ] Check SocWatch PC10 residency: > 90% for IDON? > 99% for CMS?
- [ ] Check top 3 power rails vs NVL HX reference targets
- [ ] Check SocWatch PMC blocker: any obvious IP listed?
- [ ] Confirm no external USB headset, hub, or display connected

### Detailed Investigation (< 30 minutes)

- [ ] Run XMLCLI: verify Package C State Limit, S0ix enable, PSR, ASPM
- [ ] Run ETL trace: identify Windows processes causing C-state wakeups
- [ ] Check timer resolution: powercfg /energy and WPA timer resolution view
- [ ] Compare per-IP power to Martini simulation reference (Section 16)
- [ ] Check driver version list vs validated driver matrix
- [ ] Search HSDES: use pysvtools.hsdes with power keyword filter

### Escalation Criteria

- [ ] Power delta > 20% above target with no matching HSDES sighting
- [ ] Regression confirmed across ≥ 2 IFWI versions with bisect data
- [ ] Multiple rails affected simultaneously (PMC / Pcode root cause suspected)
- [ ] MSR-reported C10 residency > 90% but SLP_S0# never asserts (VISA confirmed)
- [ ] Same issue reproduced on ≥ 2 hardware units

### Tools Reference

| Tool | Command / Purpose |
|------|------------------|
| SocWatch | `socwatch -f power -t 600 -o output` — C-state + RAPL |
| XMLCLI | `python XmlCli.py -r -a` — all BIOS knobs |
| SolarPM | Platform C-state capability and fuse read |
| NiDAQ / FlexLogger | Hardware rail current (TDMS) |
| ETL trace | `xperf -on PROC_THREAD+LOADER+DISK_IO+DPC+INTERRUPT+CSWITCH` |
| WPA | Analyse ETL; timer resolution; process CPU usage |
| powercfg | `/energy`, `/requests`, `/sleepstudy` |
| VISA | PMC signal observation; SLP_S0# verification |
| HSDES search | `pysvtools.hsdes` — `heia_soc.sighting` tenant |
| Wiki search | `python securewiki.py search "<kw>" --spaces PTP,fvcommon --json` |
| GENI query | POST to GENI REST API; focusId=5 (Debug Assistant) |
| Dashboard GUI | `python C:\test\dashboard_gui_v4.py` |

---

*PowerKPI_Validator agent. Rebuilt 2026-04-15. Informed by 152 HSDES sightings read via
`pysvtools.hsdes` (heia_soc.sighting), NVL HX Q1'26 Martini simulation data, and platform
power debug expertise across NVL, PTL, MTL, ARL, LNL-M, GNR, SPR, KBL, KBP, SKL, CNL.*
