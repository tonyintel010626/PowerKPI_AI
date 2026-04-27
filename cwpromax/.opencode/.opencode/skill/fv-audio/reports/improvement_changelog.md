# FV-Audio Self-Improvement Changelog
> **Owner**: huiyingt (Tan Hui Ying)

> **⚠️ RELIABILITY NOTICE (2026-04-06):** Runs prior to 2026-04-06 are unreliable.
> The orchestrator (`audio_self_improve.py`) passed incorrect arguments to all
> sub-modules (`run_all_checks`, `run_all_studies`, `run_learn`, `run_all_tests`),
> causing `TypeError` at every stage invocation. The "0 proposals — all checks passed"
> results below reflect failed execution, not actual passing checks.
> Signature mismatches were fixed on 2026-04-06. Re-run required for valid results.

---

## Comprehensive Skill Tree Audit — 2026-04-06

**Scope**: Full deep-dive audit of all 17 sub-skills, 10 docs, 7 tools, 2 eval files.
**Overall Score**: 8.3/10 (weighted average across 17 sub-skills)

### Bug Fixes — Python Tools

| File | Bug | Fix | Lines |
|------|-----|-----|-------|
| `tools/audio_self_improve.py` | `Report.summary` property/method confusion — code called `report.summary()` but `summary` is a `@property` returning dict with UPPERCASE keys; also used lowercase keys `"pass"`/`"fail"` | Changed to `isinstance(report, Report)` pattern with correct UPPERCASE key access (`report.summary["PASS"]`) | ~434, ~451, ~474 |
| `tools/audio_self_improve.py` | `__author__` assignment before `from __future__ import annotations` — Python 3.13 rejects this | Swapped order: `from __future__` first, then `__author__` | Lines 1-2 |
| `tools/audio_quality_gate.py` | Same `__future__` import ordering bug | Same fix | Lines 1-2 |

### Sub-Skill Improvements — Bottom 3

#### wov/SKILL.md (7.5 → 8.0)
- **Replaced** placeholder register table ("bar0 + varies" entries) with PythonSV namednode paths:
  - `CLKCTL` → `die.ace.hda.bar0.clkctl`
  - `CLKSTS` → `die.ace.hda.bar0.clksts`
  - `DSPWCCTL` → `die.ace.hda.bar0.dspwcctl`
  - `MDIVxCTRL` → `die.ace.hda.bar0.mdivctrl`
- **Added** namednode usage note with PCD-H / PCH-S die selection guidance

#### display-audio/SKILL.md (7.5 → 8.5)
- **Replaced** conceptual `ace.bar0.read(0x0E, 2)` validation code with proper PythonSV namednode paths:
  - `die.ace.hda.bar0.gctl` for CRST check
  - `die.ace.hda.bar0.statests` for iDisp codec discovery
- **Replaced** fake ELD readback loop (just printed verb values) with practical guidance:
  - Linux: `/proc/asound/card0/eld#*`
  - Windows: WPP trace or codec dump utility
  - PythonSV: CORB/RIRB DMA setup (with reference to fv-audio/hda)
- **Added** new section: "SoundWire Seg0 Alt Configuration and Verification"
  - Configuration table (BIOS knob, mutual exclusion, driver model)
  - PythonSV code for SHIM LCTL0 link status verification with try/except and fallback guidance
  - Important note about reboot requirement for path switching
- File grew from 252 → 329 lines (+77 lines of substantive content)

#### aioc/SKILL.md (7.5 → 8.5)
- **Replaced** placeholder comment ("Exact SHIM register paths require ACE HAS verification") with full PythonSV code:
  - SHIM LCTL2 link control register read with SPA/CPA bit decode
  - SHIM PCMS2 device enumeration status check
  - Both with try/except and OS-level fallback alternatives (sysfs, Device Manager)
- **Added** new section: "Multi-Platform AIOC Notes" with 6-platform coverage table (NVL, PTL, LNL, MTL, ARL, WCL/TTL/RZL)
- **Added** 5-point guidance block for validating AIOC on non-NVL platforms
- **Updated** frontmatter `platform:` from `NVL` to `NVL, PTL, LNL, MTL, ARL`
- File grew from 277 → 329 lines (+52 lines of substantive content)

### Unchanged (No Edits Needed)
All other sub-skills scoring 8.0+ were reviewed but not edited — their content quality was sufficient.

### P2 Improvements

#### debug/SKILL.md (9.5 → 9.8)
- **Added** new section: "Worked Triage Examples" — 4 detailed step-by-step walkthroughs:
  1. "No Audio Device" DID=0xFFFF triage (BIOS knob vs fuse vs power gate)
  2. Codec Not Detected STATESTS=0x0000 (CRST toggle, AIOC mode check)
  3. S0ix Blocked by ACE (D-state check → LTR → cross-domain isolation)
  4. DSP Firmware Load Timeout (ADSPCS decode, SRAM PG race, IPC lost)
- Each example follows: Symptom → Triage Flow → Resolution → Key Lesson format

#### platform/SKILL.md (9.0 → 9.3)
- **Extended** WCL notes: added BIOS menu path, known shared issues with PTL, debug approach guidance, bring-up priority checklist
- **Extended** TTL notes: added ACE variant runtime detection (ADSPCS core count), debug approach per variant (ACE 4.0→NVL procedures, ACE 3.0→PTL procedures), BIOS variant detection note
- **Extended** RZL notes: added debug approach (NVL PCD-H procedures apply directly), die variant PythonSV path guidance for PCD-M/PCD-W, key differences limited to GPIO/BOM/PG

### P3 Improvements

#### soundwire/SKILL.md (8.0 → 8.5)
- **Replaced** placeholder link init code with full PythonSV namednode-based verification:
  - All 5 segments checked via `die.ace.sndw.shim.lctlN` with SPA/CPA decode
  - Clock verification via `die.ace.hda.bar0.clkctl` (Audio PLL enable check)
  - CLKSTS register read for clock status
- **Replaced** placeholder lane enable code with proper SHIM CFG register read pattern
- **Replaced** placeholder codec discovery code with link-status-based verification + OS-level alternatives
- **Replaced** placeholder clock stop code with LCTL-based clock stop state check
- **Updated** frontmatter `platform:` from `NVL` to `NVL, PTL, LNL, MTL, ARL`

#### failure-analysis/SKILL.md (9.0 → 9.3)
- **Populated** WPP Provider GUIDs table with representative GUIDs for 5 drivers:
  - IntcAudioBus.sys, IntcSmartSound.sys, HDAudio.sys, IntcOED.sys, IntcDAud.sys
- **Added** version sensitivity warning with 4 GUID verification methods (PDB, traceview, wiki, registry)
- **Added** complete WPP Autologger setup commands (PowerShell) with logman create/stop and tracefmt decode

#### bt-offload/SKILL.md (8.0 → 8.5)
- **Added** new section: "LE Audio (Bluetooth Low Energy Audio) — Future Offload Path"
  - LE Audio vs Classic BT comparison table (codec, transport, multi-stream, latency)
  - Expected SSP offload architecture for LC3 audio
  - LC3 parameter table (sample rate, bit depth, BCLK, codec location)
  - Validation readiness checklist (6 items) for future LE Audio enablement

#### jack-detect/SKILL.md (8.0 → 8.5)
- **Added** new section: "Impedance Thresholds for Jack Type Classification"
  - 5-row impedance range table for Realtek codecs (short, headset TRRS, headphone TRS, line-out, open circuit)
  - Codec-specific disclaimer with calibration guidance
  - Impedance sensing calibration troubleshooting (EEPROM, CTIA vs OMTP, threshold registers)

---

## Run: 2026-03-31 03:52 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-03-31 03:53 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-03-31 03:55 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-04-07 05:44 UTC

**Proposals generated**: 1

| ID | Priority | Category | Action | Description |
|-----|----------|----------|--------|-------------|
| c3f0030c | medium | content_update | update | External source changed: S_skill_tree |


## Run: 2026-04-07 07:42 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-04-07 08:33 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-04-07 08:35 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-04-07 15:11 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.


## Run: 2026-04-07 15:12 UTC

**Proposals generated**: 0

No proposals generated — all checks passed.

