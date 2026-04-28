---
name: tcd-tc-writer
description: >-
  TCD (Test Case Definition) and TC (Test Case) content authoring templates,
  boundary rules, calibration checklists, and HSDES field mapping based on
  CVE Template v20 (Revision 110). Domain-agnostic — reusable across all FV IP domains.
license: MIT
---

# TCD-TC-Writer: Test Case Definition & Test Case Authoring Skill

> **Owner**: Chin, William Willy (`willychi`)
> **Version**: 1.0
> **Created**: 2026-04-02
> **Applicable To**: All FV IP domains — any HSDES TCD/TC article

## Source & Provenance

| Field | Value |
|-------|-------|
| **Source Template** | `TCTCD new template.docx` — SharePoint (`sites/csve/Shared Documents/FV Domains alignment/Test Plan Methodologies/`). Local HTM derivative: `C:\git\MTP\TCTCD new template.htm` |
| **Template Version** | v20 (Revision 110) — Created by Yaniv Buskila (Oct 2025). HTM file metadata: Created=2026-04-04, LastAuthor=Chin, Willy. SharePoint .docx revision history may differ from local HTM copy. |
| **Template Maturity** | HIGH (110 revisions) — treat all guidance as authoritative and intentional |
| **Support** | Contact owner. Collect **complete session transcript** (AI log dump) before reporting. |

> **Content Disclaimer** —
> **AI can be wrong.** This skill is a productivity tool, not a replacement for engineering judgment.
> Never trust AI 100%. When in doubt, always check with the domain lead or maintainers.
> All template rules are sourced from the authoritative CVE Template v20 (Revision 110, SharePoint).
> If this skill's guidance conflicts with the latest template on SharePoint, **SharePoint wins** — flag the discrepancy to the maintainers.

---

## TABLE OF CONTENTS

1. [Quick Start — Workflow](#1-quick-start--workflow)
2. [Critical Rules](#2-critical-rules)
3. [TCD Template — 10 Sections](#3-tcd-template--10-sections)
4. [TC Template — 11 Sections](#4-tc-template--11-sections)
5. [TCD vs TC Boundary Rules](#5-tcd-vs-tc-boundary-rules)
6. [Formatting Conventions](#6-formatting-conventions)
7. [HSDES Field Mapping](#7-hsdes-field-mapping)
8. [Pipeline Gates (L1–L7)](#8-pipeline-gates-l1l7)
9. [TCD Calibration Checklist](#9-tcd-calibration-checklist)
10. [TC Calibration Checklist](#10-tc-calibration-checklist)

---

## 1. QUICK START — WORKFLOW

### When This Skill Activates
Load this skill when the user asks to:
- Write, draft, or create a TCD or TC
- Review an existing TCD/TC for template compliance
- Check TCD/TC boundary violations
- Prepare test plan content for HSDES submission

### Workflow — Drafting a TCD

```
Step 1: Gather inputs
   - Which feature/flow? (from user or from domain sub-skill)
   - Which HAS/spec sections are relevant?
   - What is the reference TCD style? (ask for example if available)
   - What project deltas exist vs predecessors?

Step 2: Load domain knowledge
   - Load the relevant domain sub-skill (e.g., /skill fv-nvu/power, /skill fv-thc/registers)
   - Extract HW mechanisms, register names, BIOS knobs, power states, etc.

Step 3: Draft all 10 TCD sections
   - Follow Section 3 templates below
   - Address ALL mandatory sub-topics per section
   - Respect the TCD/TC boundary (Section 5)

Step 4: Run compliance gates
   - L1: Template Compliance Gate (all 10 sections present?)
   - L2: Sub-Topic Coverage Gate (all mandatory sub-topics addressed?)
   - L3: TCD-TC Boundary Enforcement (zero tool/method names?)
   - L4: PVT Completeness Gate (all 7 PVT items?)

Step 5: Output for human review
   - NEVER auto-submit to HSDES
   - Output as markdown for user review
   - User manually pastes to HSDES after approval
```

### Workflow — Drafting a TC

```
Step 1: Identify parent TCD
   - Which TCD does this TC implement?
   - What test approach was defined at TCD level?

Step 2: Gather tool/environment specifics
   - Which validation tools? (PythonSV, OSBV, etc.)
   - Which OS? (Linux, Windows, both?)
   - Which platform/stepping?
   - Which BIOS version and knob values?

Step 3: Draft all 11 TC sections
   - Follow Section 4 templates below
   - Include specific tools, versions, paths, commands
   - Define exact pass/fail thresholds and error budgets

Step 4: Run TC compliance gate (Section 10)

Step 5: Output for human review
   - NEVER auto-submit to HSDES
```

---

## 2. CRITICAL RULES

The template begins with 2 rules that **override everything else**:

### Rule 1: Pre-Si / Post-Si Split NOT Mandatory
> **"Split of TCD's between Pre and Post-Silicon is not mandatory (at all)"**

A single TCD can cover both pre-silicon (Simics, emulation) AND post-silicon (real HW). You do NOT need separate TCDs for pre-si vs post-si. The same TCD can spawn TCs for both environments.

### Rule 2: NO Tools/Methods/Content at TCD Level
> **"TCD's should never talk about type of tools, methods (OSbV, Synthetic) or specific content -> This should only start from TC level"**

This rule appears **TWICE** in the original template (top-level AND bottom of Algorithm section). It is the **single most violated rule**.

**BANNED at TCD level**:
- Specific tool names: PythonSV, OSBV, PMON, Perspec, Supercollider, Prime95, lspci, acpidump, iasl, Device Manager
- Method names: OSbV (OS-based Validation), Synthetic testing
- Specific content: script paths, content package names, test binary names
- Tool versions: "PythonSV v3.2", "OSBV 2024.1"

**ALLOWED at TCD level**:
- Generic capability descriptions: "silicon validation register access capability", "PCI configuration space read", "ACPI table extraction"
- Categories of HW mechanisms: "registers", "firmware hooks", "debug interfaces"
- Register names and functional descriptions (per Algorithm "HW mechanisms used")
- BIOS knob names and settings (per Required Config "Software/firmware requirements")
- Fuses, overrides, MSRs as control mechanisms

**Nuance — Section 4 (Required Config) says "Other dependencies: Pre-conditions, tools, environments"**:
This seems to contradict Rule 2. Resolution: you can state the **category of tool dependency** (e.g., "requires register access tool with MMIO read capability") but NOT name the specific tool. The TC level is where specific tools are named.

---

> **Structural Note**: The TCD table uses column headers **"Section | Description"** while the TC table uses **"Section | Details"**. This is an intentional distinction in the source template.

## 3. TCD TEMPLATE — 10 SECTIONS

### Section 1: Description

**Mandatory Sub-Topics** (3):

1. **"What is the feature/flow being tested?"**
   > Provide a high-level overview explaining the purpose and scope of this feature or flow.

2. **"Deltas over past projects:"**
   > Specify what's new or changed in this project. If previously covered, reference the existing test plan.

3. **"References:"**
   > Link to HAS, MAS, SAS, FAS, or other documentation. You can also include a separate "References" section if needed.

**Guidance**:
- This is the "WHAT and WHY" section
- Must answer: What feature? What scope? What's new vs predecessors? Where are the specs?
- Pass/fail criteria are NOT explicitly requested here (they go in Algorithm Section 2) — but including them in Description is an acceptable style variation
- The "Deltas" sub-topic is critical — EVERY TCD must state what changed from previous projects
- "References" can be inline OR a separate section at the end

**Section 1 Checklist**:
- [ ] Feature/flow purpose stated
- [ ] Scope clearly bounded (what's IN, what's OUT)
- [ ] Deltas vs previous project explicitly listed
- [ ] HAS/MAS/SAS/FAS references linked
- [ ] No tool names mentioned

---

### Section 2: Algorithm of Testing

**Mandatory Sub-Topics** (5):

1. **"High-level test logic:"**
   > Describe the main approach for testing this feature or flow.

2. **"Deltas over past projects:"**
   > If not sufficiently covered before, define a full plan; if covered, provide references

3. **"HW mechanisms used:"**
   > Mention registers, firmware hooks, debug interfaces used to verify or control the feature.

4. **"Stress/non-stress areas:"**
   > Describe how different feature areas are stressed or disabled (e.g., via fuses, MSRs, BIOS knobs).

5. **"General pass/fail criteria:"**
   > Define what errors are detected and how correctness is verified. State if this is purely exercising or actual functional verification.

**REPEATED CRITICAL NOTE** (bottom of cell in original template):
> "TCD's should never talk about type of tools, methods (OSbV, Synthetic) or specific content -> This should only start from TC level"

**Guidance**:
- This is the "HOW (high-level)" section — the test strategy, not the test steps
- "HW mechanisms used" ALLOWS mentioning registers BY NAME — this is the one place where hardware details are welcome at TCD level
- "Stress/non-stress areas" — must identify which areas get stress testing vs which are just exercised. Control mechanisms (fuses, MSRs, BIOS knobs) should be named
- "General pass/fail criteria" — explicitly asks for error detection method AND whether this is functional verification vs mere exercising. This is an important distinction!
- The repeated "no tools" note means Algorithm is the section most prone to tool-name violations

**Section 2 Checklist**:
- [ ] High-level test logic/strategy described (phases, approach)
- [ ] Deltas vs previous project test approach stated
- [ ] HW mechanisms named (registers, FW hooks, debug interfaces)
- [ ] Stress vs non-stress areas identified
- [ ] General pass/fail criteria defined
- [ ] "Functional verification" vs "exercising" distinction stated
- [ ] NO tool names, NO method names, NO specific content

---

### Section 3: Randomization

**Template Content** (single paragraph):
> What is being randomized to cover the feature or flow? Specify input parameters, test sequences, configurations, or runtime states that are randomized to increase coverage and robustness.

**4 categories of randomization**:
1. **Input parameters** — data values, sizes, addresses
2. **Test sequences** — order of operations, timing
3. **Configurations** — BIOS knobs, straps, fuses
4. **Runtime states** — power states, concurrency conditions

**Guidance**: Even if randomization is minimal for a feature, state what CAN be randomized. The goal is "coverage and robustness" — randomization is a coverage multiplier.

**Section 3 Checklist**:
- [ ] Input parameters that vary listed
- [ ] Test sequence variations identified
- [ ] Configuration permutations listed (BIOS knobs, straps)
- [ ] Runtime state variations identified
- [ ] Purpose of each randomization stated (what coverage does it add?)

---

### Section 4: Required Configuration and Dependencies

**Mandatory Sub-Topics** (4):

1. **"Hardware requirements:"**
   > List required HW (test cards, sockets, boards, QDF, TDP, thermal solution, RVP hooks).

2. **"Software/firmware requirements:"**
   > BIOS knobs, firmware settings, driver versions, OS configurations. Include possible firmware or driver hooks that detect errors.

3. **"Other dependencies:"**
   > Pre-conditions, tools, environments. Include any fuses or overrides that can be controlled.

4. **"States or modes:"**
   > Indicate if specific modes are required (e.g., SMM, 32/64-bit, VMX, secure mode).

**Guidance**:
- **HW requirements** explicitly asks for: test cards, sockets, boards, QDF (stepping), TDP tier, thermal solution, RVP hooks — be specific about physical setup
- **SW/FW requirements** — BIOS knobs BY NAME are explicitly OK here. Also asks for "firmware or driver hooks that detect errors"
- **Other dependencies** — "tools, environments" means tool CATEGORIES not tool names (per Rule 2). Also list controllable fuses/overrides
- **States or modes** — the template gives examples: SMM, 32/64-bit, VMX, secure mode. Adapt to your IP (e.g., boot modes, secure boot, debug mode, power states)

**Section 4 Checklist**:
- [ ] HW requirements: boards, sockets, TDP, thermal, test cards
- [ ] SW/FW requirements: BIOS knobs (by name+value), FW version requirements, OS config, driver requirements
- [ ] FW/driver error hooks identified
- [ ] Other dependencies: pre-conditions, tool CATEGORIES (not names), environments, controllable fuses/overrides
- [ ] States/modes: required operational modes listed
- [ ] NO specific tool names (only categories)

---

### Section 5: Coverage (optional)

**Template Content**:
> How are you measuring coverage? Describe methods such as functional coverage, code coverage, or event tracking. List tools or mechanisms used (e.g., trace logs, checkers). Clarify if this is for intent verification or coverage measurement.

**Guidance**:
- Marked "(optional)" — but should be filled for any non-trivial feature
- 3 coverage methods named: functional coverage, code coverage, event tracking
- "tools or mechanisms" here refers to COVERAGE INSTRUMENTS (trace logs, checkers), NOT validation tools — this is about how you MEASURE coverage, not how you RUN tests
- Important distinction: "intent verification" (did we test what we intended?) vs "coverage measurement" (how much did we cover?)
- Typical coverage dimensions: register fields verified, power states exercised, error paths tested, config/BIOS requirements validated, protocol sequences covered

**Section 5 Checklist**:
- [ ] Coverage measurement method stated (functional/code/event)
- [ ] Coverage instruments identified (trace logs, checkers)
- [ ] Intent verification vs coverage measurement distinguished
- [ ] Coverage targets/goals stated (what % or what completeness)

---

### Section 6: Cross-Feature Interaction

**Template Content** (introduction + 3 bold categories + conclusion):

> Does this feature interact with other flows or features? List cross-feature or cross-IP dependencies (e.g., Power Management, Security, Concurrency).

Three explicitly named **bold** categories:

1. **"PM:"**
   > How this affects or is affected by power states/flows.

2. **"Concurrency:"**
   > If it must run concurrently or is sensitive to other workloads.

3. **"QoS/ISOCH:"**
   > Interaction with isochronous traffic or QoS features.

> Describe any special interactions (e.g., Cross-Die or Cross-IP). If test plan is owned elsewhere, add links or references here.

**Guidance**:
- Template gives 3 bold categories as examples: PM, Concurrency, QoS/ISOCH (presented as "Examples:" in the template — not mandatory, but strongly recommended as a starting framework)
- The intro paragraph ALSO names **"Security"** as a 4th category (not bold, but explicitly listed in the parenthetical example). Include Security for any IP with security/access control.
- Also consider: Cross-Die, Cross-IP interactions
- If interaction is tested elsewhere, LINK to that test plan — don't duplicate
- Typical examples per category: PM = power controller integration / power gating coordination; Concurrency = PHY sharing / bus arbitration / multi-client access; QoS/ISOCH = streaming latency / isochronous guarantees; Cross-IP = security engine (secure boot), power controller (power gating), shared PHY (resource sharing), host controller (offload paths)

**Section 6 Checklist**:
- [ ] PM interaction stated (power states, power gating)
- [ ] Concurrency interaction stated (multi-workload, resource sharing)
- [ ] Security interaction stated (secure boot, access control, trust boundaries)
- [ ] QoS/ISOCH interaction stated (isochronous traffic, latency)
- [ ] Cross-Die / Cross-IP interactions listed
- [ ] Links to other test plans where interaction is tested elsewhere

---

### Section 7: DFx Requirements

**Template Content**:
> What Design for Debug (DFx) or Validation (DFV) features are needed? List required debug hooks, observability features, or validation registers.

Examples:
- **DFV** (Design for Validation): Error status, stress knobs (e.g., queue or credit reduction).
- **DFD** (Design for Debug): Snapshots, VISA traces, state dumps.

**Guidance**:
- **DFV** = features that help VALIDATE correctness: error status registers, stress knobs that reduce queues/credits to increase corner case probability
- **DFD** = features that help DEBUG failures: state snapshots, VISA signal traces, register dumps, firmware trace logs
- Typical DFV examples: error counters, watchdog timeout status, IPC error flags, completion status registers, stress injection knobs
- Typical DFD examples: firmware trace (DTF/STP/SysT), signal visibility (VISA), core debug (OCD/JTAG), memory dumps, state machine snapshots

**Section 7 Checklist**:
- [ ] DFV features listed: error status, stress knobs, validation registers
- [ ] DFD features listed: snapshots, VISA traces, state dumps
- [ ] Each DFx feature's purpose stated (what does it help validate/debug?)

---

### Section 8: Negative Testing (optional)

**Template Content**:
> Identify potential negative test cases.

Five explicit example categories:
1. **Illegal memory access** (expect error or zeros).
2. **Fuse-off feature access.**
3. **Locked register modification attempts.**
4. **Testing error handling paths deliberately.**
5. **Bios Knobs especially features disable.**

**Guidance**:
- Marked "(optional)" but should ALWAYS be filled for any IP with security/access control
- The 5 examples are a checklist — consider ALL of them for your feature
- **"Bios Knobs especially features disable."** — BIOS knob disable testing is explicitly called out as important. Every BIOS knob that can disable the feature should have a negative test
- State the expected behavior for each negative case (error response, zeros, hang, graceful degradation?)
- Typical negative test categories: fuse-off / feature disable, locked register writes, BIOS knob disable (e.g., `FeatureEnable=0`), memory allocation failure, wrong boot mode, error injection (ECC, parity, timeout), invalid configuration, access control violations

**Section 8 Checklist**:
- [ ] Illegal memory/register access scenarios
- [ ] Fuse-off behavior tested
- [ ] Locked register write attempts tested
- [ ] Error handling paths exercised
- [ ] BIOS knob disable scenarios (every relevant knob)
- [ ] Expected behavior for each negative case stated

---

### Section 9: PVT Aspects (optional)

**Template Content** (7 distinct items — the MOST detailed optional section):

1. > Describe testing across **Process**, **Voltage**, and **Temperature** conditions. Include corner cases (e.g., PPSM) and thermal considerations.

2. > State exactly which thermal solution needs to be used consider all cases and TDP's

3. > Pay special attention to thermal validation as it has historically caused critical issues.

4. > Survivability

5. > TDP: each product can support a few TDP's think of which one is the worst-case scenario and include it in your testing.

6. > Vmin/Max: How is your IP function with POR Min/Max voltage Applied. (this one needs to be physically measured)

7. > Define Silicon parameter for PPSM

**Guidance**:
- **7 distinct items** — demands MORE detail than most people provide
- **Item 2**: "ALL cases and TDPs" — specify thermal solution for EVERY TDP tier
- **Item 3**: Historical warning — the template authors have seen thermal-related escapes. Take this seriously.
- **Item 4**: "Survivability" — what happens if the feature FAILS under PVT stress? Does the platform survive? Graceful degradation?
- **Item 5**: For multi-TDP products, identify which TDP is the WORST case for your feature
- **Item 6**: Vmin/Vmax must be PHYSICALLY MEASURED, not just simulated
- **Item 7**: Define which silicon manufacturing parameter is most relevant for your feature's corner cases

**Section 9 Checklist**:
- [ ] Process corners: PPSM corners identified, silicon parameter defined
- [ ] Voltage: Vmin/Vmax testing plan, physical measurement requirement stated
- [ ] Temperature: temperature range, thermal solution specified for ALL TDPs
- [ ] Historical thermal risk acknowledged
- [ ] Survivability: behavior under PVT failure described
- [ ] TDP worst-case: identified which TDP tier is worst for this feature
- [ ] PPSM silicon parameter: specific parameter defined for process corner binning

---

### Section 10: Performance / Bandwidth Testing (optional)

**Template Content**:
> Describe any performance or bandwidth measurements. Could involve internal (fabric, CCF, D2D) or external interfaces (PCIe, memory). Include different metrics: Peak, Sustained/Average, Minimum, or "Survivability". Explain definitions per interface (e.g., display, core frequency, fabric BW). Include TDP considerations (e.g., differences at 15W vs. 35W vs. 60W).

**Guidance**:
- Two interface categories: internal (fabric, CCF, D2D) and external (PCIe, memory)
- **4 metric tiers**:
  1. **Peak** — maximum theoretical/observed
  2. **Sustained/Average** — steady-state under load
  3. **Minimum** — worst-case under contention
  4. **Survivability** — minimum to avoid failure/hang
- Each interface may define these 4 metrics differently
- Performance varies by TDP tier — state how

**Section 10 Checklist**:
- [ ] Internal interface metrics identified
- [ ] External interface metrics identified
- [ ] All 4 metric tiers defined: Peak, Sustained, Minimum, Survivability
- [ ] Per-interface metric definitions stated
- [ ] TDP-tier impact on performance described

---

## 4. TC TEMPLATE — 11 SECTIONS

> The TC (Test Case) level is where ALL specifics go: tools, steps, versions, HW configs, pass/fail thresholds.

### TC Section 1: TC Description
**What is the test doing? What are the exact steps?**
- Any dependencies should be listed in detailed sub-sections below, but others like silicon current health status or IP bringup/enabling, other dependencies?
- Deploy validation tools (OSBV, PMON, Perspec, etc.).
- Connect measurement equipment (power analysers, oscilloscopes, thermal sensors).
- Collect logs and telemetry.

**Key**: TC level explicitly names tools. Before running the TC, verify the IP is alive and enabled (pre-test dependency check).

### TC Section 2: Test Steps
- What are exact steps to run the test
- Include all pre-work to run the test
- Then the test itself, including any harrassers/checkers
- Then post-test, based on next section
- **Include link the content**

**Key**: 3-phase structure: pre-work -> test execution -> post-test.

### TC Section 3: Pass/Fail Criteria & HW Errors

**Pass Conditions**
- No fatal HW errors or system hangs.
- Thermal and power metrics within spec.
- Frequency stays above defined thresholds.
- No OS-level crashes or app errors.
- Validation automation (SST, Central, Concurrency) reports pass.

**Fail Conditions**
- Any system reset or fatal error.
- Thermal or power violations.
- Hardware error/warning logs beyond acceptable thresholds.
- Incorrect or incomplete output data.
-content Fail

**HW Errors**
- Capture and log all correctable/non-fatal errors.
- Fail if errors exceed budget or indicate bad behavior.

**Key**: The error BUDGET concept — not every HW error is a fail. Define a threshold. Below budget = pass with warnings. Above budget = fail.

### TC Section 4: Intent Verify
- Validate stress matches expectation.
- Monitor PMON counters, power/thermal sensors, VISA traces.
- Check workload scheduling via Windows Task Manager or SVOS Task Monitor.
- Use debug cards or analyzers for PCIe/bus traffic.
- Confirm workload event logs match expected profile.

**Key**: Confirms the TEST ITSELF is doing what it's supposed to — not just pass/fail of the feature, but verification that the test workload is correctly exercising the feature.

### TC Section 5: Validation SW — Tool and Content Requirements

- **Validation Framework**: OSBV (specify version), SVOS build.
- **Supporting Tools**: PMON (version), Prime95 (version/config), Perspec scripts (path), PythonSV, Supercollider.
- **General Tool Mapping**:
  · OS-level: OSBV wrapper, Windows task checker, HW checkers.
  · Synthetic: Perspec for concurrency/burst, PythonSV for register checks, Supercollider for stress patterns.

**Key**: THIS is where all tool names, versions, paths, and configurations go. NOT in the TCD.

### TC Section 6: Ecosystem SW — Test Requirements
- BIOS version and config file.
- Required BIOS knobs (list values).
- OS kernel and scheduler settings.
- Driver versions for key subsystems (PCIe, graphics, storage).
- Registry keys or OS overrides (if any).

### TC Section 7: Test HW Requirements and HW Configuration
- SoC details: stepping, TDP, any specific silicon parametric
- Confirm full topology: sockets, DIMMs, PCIe, power rails
  - DIMM configuration: type, size, rank, vendor.
  - PCIe configuration: lanes, devices.
- Thermal solution: LCTT, boot kit, 1xTDP setup, chamber, etc..
- Debug/measurement cards (PCIe analyzers, logic analyzers).
- Power measurement setup: analyzers on VR rails, onboard sensors.

### TC Section 8: PVT (Optional)
- Monitor voltage rails, thermal sensors, process bins.
- Compare to design guardbands. Check IP functionality in Vmin/max while measuring it.
-stress IP under corners Temp
-check IP survivability
- define relevant silicon parametric for PPSM

### TC Section 9: Performance/BW (Optional)
- Measure min, avg, peak BW per domain (e.g., memory MBps, PCIe throughput).
- Repeat periodically to catch regressions.

### TC Section 10: Validation Automation Global Checkers
- Enable SST, Central, and Concurrency checkers.
- define PVT checkers for specific features
- Should this become a global checker?

### TC Section 11: ISOC Validation (Optional)
- Validate integrated I/O coherence (ISOC): data coherency and correct device interactions.

---

## 5. TCD vs TC BOUNDARY RULES

This is the **single most important concept** in the template.

| Aspect | TCD Level | TC Level |
|--------|-----------|----------|
| **Abstraction** | WHAT to test, WHY, at what scope | HOW to test, exact steps |
| **Tools** | NEVER name specific tools | Name tools + versions + paths |
| **Methods** | NEVER name methods (OSbV, Synthetic) | Specify method + framework |
| **Content** | NEVER reference specific content/scripts | Link to scripts, binaries, configs |
| **Registers** | Name registers as "HW mechanisms" | Specify offsets, bitfields, expected values |
| **BIOS knobs** | Name knobs as config requirements | Specify exact values, sequences |
| **Pass/Fail** | General criteria (what errors, how verified) | Specific thresholds, error budgets |
| **HW Config** | Categories (TDP, thermal, boards) | Specific stepping, DIMM config, topology |
| **Deltas** | Feature deltas AND test approach deltas | Specific implementation differences |
| **Coverage** | Coverage methodology and targets | Coverage metrics, measurement data |
| **Performance** | Metric definitions, TDP impact | Specific measurements, thresholds |

### The Litmus Test
> **"If I remove the tool/method name and the sentence still makes sense as a test STRATEGY statement, it belongs in the TCD. If it only makes sense as a test EXECUTION instruction, it belongs in the TC."**

### Examples

| Statement | Level | Why |
|-----------|-------|-----|
| "Verify PCI BAR0 is allocated correctly" | TCD | Strategy — WHAT to verify |
| "Run `lspci -vvv \| grep BAR` on Linux" | TC | Execution — HOW to verify |
| "Verify power management register enables all clock gates" | TCD | HW mechanism — WHAT register |
| "Read offset 0x1D0 via PythonSV and check bits[5:0]=0x3F" | TC | Specific tool + offset + bits |
| "Boot mode must be randomized across all valid configurations" | TCD | Randomization strategy |
| "Set boot_mode_strap via PythonSV fuse override to 0x3" | TC | Specific tool + value |
| "BIOS must program memory region with correct allocation for IP" | TCD | Config requirement |
| "Set BIOS knob `FeatureMemSize=0x01000000` in Setup menu" | TC | Specific value + location |

---

## 6. FORMATTING CONVENTIONS

Based on forensic extraction of the original template document:

1. **Section headers** (Column A): Plain bold text, single line
2. **Sub-topic labels** within cells: Bold text followed by non-bold description
3. **Bullet points**: List Paragraph style; within table cells, bullet items use standard bullet character
4. **No numbering within cells**: Template uses prose paragraphs and bullet lists, not numbered lists (though TCDs in practice often use numbered phases — this is acceptable)
5. **Optional sections**: Marked with "(optional)" in the header — still include them if relevant
6. **Internal links**: TCD and TC should be in the SAME document (or same HSDES article hierarchy)
7. **Bold sub-topics pattern**: Every multi-part section uses `**Sub-topic:** description` format
8. **No cell shading/colors**: Header rows use bold text only — no background fill, no color coding
9. **PVT key terms**: "Process", "Voltage", and "Temperature" are individually **bold** — emphasizing the 3 PVT axes
10. **HSDES rich text**: Supports bold, bullets, tables — preserve formatting when pasting
11. **Column header difference**: TCD table uses column header "**Description**" (Column B), while TC table uses "**Details**" (Column B) — this is intentional in the template, not an error

---

## 7. HSDES FIELD MAPPING

When writing content for HSDES TCD articles, all 10 TCD sections map to the HSDES `description` field:

| Template Section | HSDES Field | Notes |
|-----------------|-------------|-------|
| 1. Description | `description` (rich text) | Main body of the TCD article |
| 2. Algorithm of Testing | `description` (continued) | Sub-section within description |
| 3. Randomization | `description` (continued) | Sub-section within description |
| 4. Required Config | `description` (continued) | Sub-section within description |
| 5. Coverage | `description` (continued) | Sub-section within description |
| 6. Cross-Feature | `description` (continued) | Sub-section within description |
| 7. DFx Requirements | `description` (continued) | Sub-section within description |
| 8. Negative Testing | `description` (continued) | Sub-section within description |
| 9. PVT Aspects | `description` (continued) | Sub-section within description |
| 10. Performance/BW | `description` (continued) | Sub-section within description |

All 10 sections go into a single structured document with section headers.

---

## 8. PIPELINE GATES (L1–L7)

### L1: Template Compliance Gate
Before any TCD draft is finalized:
1. All 10 sections present? (4 optional may be empty with justification)
2. Zero tool names in entire TCD?
3. Zero method names? (grep for OSbV, Synthetic, etc.)
4. Zero content/script references?
5. All bold sub-topics from template addressed?
6. Deltas stated in BOTH Description AND Algorithm?
7. Pass/fail criteria in Algorithm section?

### L2: Sub-Topic Coverage Gate
Each section has mandatory sub-topics. Verify:
- **Description**: 3 sub-topics (feature overview, deltas, references)
- **Algorithm**: 5 sub-topics (test logic, deltas, HW mechanisms, stress areas, pass/fail)
- **Randomization**: 4 categories (inputs, sequences, configs, runtime states)
- **Required Config**: 4 sub-topics (HW reqs, SW/FW reqs, other deps, states/modes)
- **Coverage**: 3 aspects (measurement method, instruments, intent vs coverage)
- **Cross-Feature**: 4+ categories (PM, Concurrency, Security, QoS/ISOCH + Cross-Die/IP)
- **DFx**: 2 sub-categories (DFV, DFD)
- **Negative Testing**: 5 example categories checked
- **PVT**: 7 items (P/V/T conditions, thermal solution, historical warning, survivability, TDP worst-case, Vmin/Vmax measurement, PPSM parameter)
- **Performance**: 4 metric tiers + TDP considerations

### L3: TCD-TC Boundary Enforcement
Scan TCD for patterns that indicate TC-level content leaking in:
- **Tool names**: PythonSV, OSBV, PMON, Perspec, lspci, acpidump, iasl, Device Manager, Supercollider, Prime95
- **Method names**: OSbV, OS-based Validation, Synthetic
- **Specific offsets** used as test STEPS (vs HW mechanism descriptions)
- **Script paths** or content package names
- **Version numbers** for tools/frameworks

### L4: PVT Completeness Gate
PVT is the most under-filled section. Force-check all 7 items:
1. Process corners + PPSM
2. Voltage Vmin/Vmax + physical measurement note
3. Temperature range + thermal solution per TDP
4. Historical thermal warning acknowledged
5. Survivability behavior stated
6. TDP worst-case identified
7. PPSM silicon parameter defined

### L5: Reference TCD Style Calibration
Before drafting, study the reference TCD (if provided) and extract:
- Writing style (security-first? intent-driven? specification-heavy?)
- Level of detail in each section
- How deltas are presented
- How pass/fail is structured
- Any deviations from template (and whether to follow template or reference)

### L6: Iterative Review Cycle
1. Draft -> Template Compliance Gate -> Fix violations
2. Technical Review -> Cross-check against HAS/sub-skills -> Fix errors
3. Style Calibration -> Compare to reference TCD -> Adjust tone/detail
4. TCD-TC Boundary Check -> Remove tool names -> Generalize
5. PVT Completeness Gate -> Fill all 7 items
6. Final human review -> Domain lead approval

### L7: HSDES Submission Protocol
- **NEVER** auto-submit to HSDES — always require explicit human approval
- Draft locally in markdown -> User reviews -> User manually pastes to HSDES
- Preserve formatting: HSDES rich text supports bold, bullets, tables
- Include author attribution and AI-assisted disclosure

---

## 9. TCD CALIBRATION CHECKLIST

Use this checklist to verify any TCD draft against Template v20:

### Structural Compliance
- [ ] All 10 section headers present and in correct order
- [ ] Optional sections (5, 8, 9, 10) either filled or explicitly marked N/A with justification
- [ ] Bold sub-topic labels used within multi-part sections

### Content Compliance — Description (Sec 1)
- [ ] Feature/flow purpose and scope stated
- [ ] Deltas vs previous project listed
- [ ] HAS/MAS/SAS/FAS references linked
- [ ] Scope boundary (what's IN and what's OUT)

### Content Compliance — Algorithm (Sec 2)
- [ ] High-level test logic (phases/approach)
- [ ] Deltas vs previous test approach
- [ ] HW mechanisms named (registers, FW hooks, debug interfaces)
- [ ] Stress/non-stress areas identified with control mechanisms
- [ ] General pass/fail criteria with verification vs exercising distinction
- [ ] NO tool names, NO method names, NO content references

### Content Compliance — Randomization (Sec 3)
- [ ] Input parameters randomized
- [ ] Test sequences randomized
- [ ] Configurations randomized
- [ ] Runtime states randomized

### Content Compliance — Required Config (Sec 4)
- [ ] HW requirements (boards, TDP, thermal, test cards)
- [ ] SW/FW requirements (BIOS knobs, FW settings, driver reqs, error hooks)
- [ ] Other dependencies (pre-conditions, tool CATEGORIES, fuses/overrides)
- [ ] States/modes (operational modes required)
- [ ] NO specific tool names (only categories)

### Content Compliance — Coverage (Sec 5, optional)
- [ ] Coverage measurement method
- [ ] Coverage instruments
- [ ] Intent verification vs coverage measurement

### Content Compliance — Cross-Feature (Sec 6)
- [ ] PM interaction
- [ ] Concurrency interaction
- [ ] Security interaction
- [ ] QoS/ISOCH interaction
- [ ] Cross-Die / Cross-IP interactions
- [ ] Links to other test plans

### Content Compliance — DFx (Sec 7)
- [ ] DFV features (error status, stress knobs)
- [ ] DFD features (snapshots, VISA, state dumps)

### Content Compliance — Negative Testing (Sec 8, optional)
- [ ] Illegal access scenarios
- [ ] Fuse-off scenarios
- [ ] Locked register scenarios
- [ ] Error handling paths
- [ ] BIOS knob disable scenarios

### Content Compliance — PVT (Sec 9, optional)
- [ ] Process/Voltage/Temperature conditions
- [ ] Thermal solution for ALL TDPs
- [ ] Historical thermal warning
- [ ] Survivability
- [ ] TDP worst-case identified
- [ ] Vmin/Vmax physical measurement
- [ ] PPSM silicon parameter defined

### Content Compliance — Performance/BW (Sec 10, optional)
- [ ] Internal interface metrics
- [ ] External interface metrics
- [ ] 4 metric tiers (Peak, Sustained, Minimum, Survivability)
- [ ] Per-interface definitions
- [ ] TDP-tier impact

### Rule Compliance
- [ ] Zero tool names in entire TCD
- [ ] Zero method names (OSbV, Synthetic, etc.)
- [ ] Zero content/script references
- [ ] Pre-Si / Post-Si NOT split (unless intentionally split)
- [ ] Deltas in BOTH Description AND Algorithm sections

---

## 10. TC CALIBRATION CHECKLIST

Use this checklist to verify any TC draft against Template v20:

### Structural Compliance
- [ ] All 11 section headers present
- [ ] Optional sections (8, 9, 11) either filled or marked N/A

### Content Compliance — TC Description (Sec 1)
- [ ] What the test does stated
- [ ] Dependencies listed (silicon health, IP bringup)
- [ ] Tool deployment steps
- [ ] Measurement equipment setup
- [ ] Log/telemetry collection plan

### Content Compliance — Test Steps (Sec 2)
- [ ] Pre-work steps
- [ ] Test execution steps (with harrassers/checkers)
- [ ] Post-test steps
- [ ] Link to content/scripts

### Content Compliance — Pass/Fail & HW Errors (Sec 3)
- [ ] Pass conditions defined
- [ ] Fail conditions defined
- [ ] HW error capture plan
- [ ] Error budget threshold defined

### Content Compliance — Intent Verify (Sec 4)
- [ ] Stress validation method
- [ ] Counter/sensor monitoring plan
- [ ] Workload scheduling verification
- [ ] Event log confirmation

### Content Compliance — Validation SW (Sec 5)
- [ ] Validation framework + version
- [ ] Supporting tools + versions
- [ ] Tool mapping (OS-level, Synthetic)

### Content Compliance — Ecosystem SW (Sec 6)
- [ ] BIOS version + config
- [ ] BIOS knobs + values
- [ ] OS kernel/scheduler settings
- [ ] Driver versions
- [ ] Registry keys/overrides

### Content Compliance — Test HW (Sec 7)
- [ ] SoC stepping/TDP/parametric
- [ ] Full topology
- [ ] DIMM configuration
- [ ] PCIe configuration
- [ ] Thermal solution details
- [ ] Debug/measurement cards
- [ ] Power measurement setup

### Content Compliance — PVT (Sec 8, optional)
- [ ] Voltage/thermal/process monitoring
- [ ] Guardband comparison
- [ ] Corner temperature stress
- [ ] Survivability check
- [ ] PPSM parametric

### Content Compliance — Performance/BW (Sec 9, optional)
- [ ] Min/avg/peak BW per domain
- [ ] Regression tracking plan

### Content Compliance — Global Checkers (Sec 10)
- [ ] SST/Central/Concurrency checkers
- [ ] PVT checkers
- [ ] Global checker promotion consideration

### Content Compliance — ISOC (Sec 11, optional)
- [ ] I/O coherence validation plan

---

## Cross-References

| Resource | Description |
|----------|-------------|
| **`pvim-mtp` skill** | **HSDES MTP hierarchy traversal — WHERE to create TCDs/TCs in the tree** |
| `hsdes` skill | EQL search and article queries (sighting/test_case lookup) |
| `nga/pvimintegration` skill | NGA↔HSDES mapping for test execution tracking |
| `nga/planning` skill | NGA test planning (suites, steps, actions) |
| `doc-study` skill | Extract HAS/BWG/SwAS content for TCD reference material |
| `driver-diff` skill | Cross-platform driver comparison for cross-feature TCD content |

---

*End of TCD & TC Writer Skill v1.0*
