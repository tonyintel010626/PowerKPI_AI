# FV-USB Skill Changelog

All notable changes to the FV-USB skill tree are documented in this file.

---

## [2.2.0] — 2026-04-02

### Summary
HSDES-driven improvements: added 3 new known issues sourced from 127 USB sightings analysis, new PM clock request debug playbook, ModPHY PythonSV register patterns, PORTSC hex decode examples, LTSSM state table, and HCIVERSION decode in xhci sub-skill.

### Added — New Known Issues (from HSDES heia_soc.sighting analysis)
- **known_issues.md** — HCIVERSION=0x0100 (HSDES 1304166922): wrong xHCI version blocks Gen2/SSP driver support; tagged `[REGISTER]`
- **known_issues.md** — PM clock request stuck high (`USB3_PRIM_CLKREQ=1`): PM enabling script must clear `USBCMD.RS` and all `PORTSC.PP` bits; tagged `[CONFIG]`
- **known_issues.md** — U1 entry failure / no `phy_status` assertion (HSDES 1404838956): LTSSM=5 (rxdet), PORTSC=0x611; tagged `[INTEG]`

### Added — Debug Enhancements
- **debug/SKILL.md** — §5 PM Clock Request Stuck High: new failure signature with root cause, diagnosis, and fix steps
- **debug/SKILL.md** — §6 U1 Entry Failure / No `phy_status` Assertion: PORTSC hex decode, LTSSM state, WA
- **debug/SKILL.md** — ModPHY register access section (PythonSV, pre-silicon): EB underflow/overflow sticky, bonux code override, DFE CM cal; with silicon vs pre-silicon scope note
- **debug_playbooks.md** — Playbook 6: PM Clock Request Stuck High (6-step flow: PORTSC.PP → USBCMD.RS → ux_ibbs_prim_clkreq → USB3_PRIM_CLKREQ → USB3_SIDE_CLKREQ → P2SB/Rambo path)
- **debug_playbooks.md** — Updated cross-reference table with P6 entry

### Added — Register Quick-Reference
- **cheat_sheet.md** — PORTSC hex decode examples: 0x00000000 (no device), 0x000002B3 (active SS), 0x00001203 (active HS), 0x12B1 (bad state), 0x611 (U1 fail/rxdet)
- **cheat_sheet.md** — HCIVERSION check one-liner in PythonSV section
- **cheat_sheet.md** — LTSSM state quick reference table (0–15)
- **cheat_sheet.md** — PM clock request debug one-liners (USBCMD.RS + PORTSC.PP + ux_ibbs_prim_clkreq)

### Changed — xHCI Register Clarifications
- **xhci/SKILL.md** — Added HCIVERSION value decode: 0x0100 = xHCI 1.0, 0x0110 = xHCI 1.1 (required for Gen2/SSP); drivers check ≥ 0x0110 before enabling SSP
- **xhci/SKILL.md** — Added PM CLKREQ assertion row to Common Issues table (USBCMD.RS + PORTSC.PP clear sequence)

---

## [2.1.0] — 2026-03-20

### Summary
Major skill tree expansion: adopted best patterns from FV-THC, FV-Audio, FV-LPSS, and FV-NVU.
Grew from 10 files / ~2,303 lines to 24+ files with 3 new sub-skills, 5 new docs, 3 self-improvement tools, and expanded eval coverage.

### Added — New Sub-Skills
- **config-checkout/SKILL.md** — PCI enumeration verification, BAR checks, BIOS knob validation (pattern from FV-Audio)
- **debug/etl-decode/SKILL.md** — ETL trace capture, symbol setup, decode workflow, UAOL trace analysis
- **platform/SKILL.md** — Per-platform data matrix for 8 SoCs (NVL, PTL, LNL, MTL, ARL, WCL, RZL, TTL) with PLACEHOLDER annotations

### Added — New Documentation
- **docs/debug_playbooks.md** — 5 detailed playbooks: NDE, Wrong Speed, S0ix Blocker, UAOL Recording Stuck, Compliance Mode Trap
- **docs/usb_has_extraction.md** — HAS extraction template for per-platform register data
- **docs/test_gap_analysis.md** — Test gap analysis framework (platform × category matrix)
- **docs/agent_workflows.md** — 6 agent workflow diagrams (enumeration, debug, power, UAOL, config-checkout, cross-domain)
- **docs/usb_test_template.py** — Python test template with NGA exit codes, logging, cleanup patterns

### Added — Self-Improvement Pipeline
- **tools/usb_self_check.py** — Structural integrity checker (98 checks: file existence, frontmatter, cross-references)
- **tools/usb_self_verify.py** — Content assertion runner (verifies eval/assertions.py)
- **tools/usb_quality_gate.py** — Composite quality gate (runs both checkers, produces pass/fail summary)
- **reports/CHANGELOG.md** — This file

### Added — Eval Expansion
- **eval/opencode.json** — Machine-readable eval configuration
- **eval/usb_skill_eval_tests.md** — 30 structured eval test scenarios across all sub-skills

### Changed — Bug Fixes
- **xhci/SKILL.md** — Fixed USB speed encoding: value 1 = Full Speed (12 Mbps), value 2 = Low Speed (1.5 Mbps). Was previously swapped.
- **docs/cheat_sheet.md** — Fixed platform table: LNL/ARL UAOL-behind-hub changed from "TBD" to "N/A (no UAOL)"; MTL UAOL engine changed from "ACE (gen?)" to "ACE (early gen)"

### Changed — Restructured
- **docs/known_issues.md** — Restructured with classification prefixes (HSDES, RTL, CONFIG, FW, INTEG, DRIVER), grouped into 3 issue tables
- **eval/assertions.py** — Expanded from 42 to 67 test groups (added CFG, ETL, PLAT, new DOCS groups). Fixed DOCS-004 regex for robustness.

### Changed — Cross-References
- **xhci/SKILL.md** — Added "Related Sub-Skills" section referencing debug, config-checkout
- **enumeration/SKILL.md** — Added "Related Sub-Skills" section referencing config-checkout
- **debug/SKILL.md** — Added "Related Sub-Skills" section referencing debug/etl-decode
- **platform/SKILL.md** — Added "Related Sub-Skills" section referencing config-checkout, power

### Changed — Configuration
- **tools/self_improvement_config.json** — Expanded from 4→7 skills, 3→8 docs, added quality_gate section

### Changed — Agent Definition
- **.opencode/agent/FV/FV-USB.md** — Added 3 new sub-skills to SUB-SKILL DELEGATION table, expanded Reference Documents table (3→8), added 3 new loading order scenarios, updated AUDIT TRAIL with v2.1.0 entry, bumped version to 2.1.0

---

## [2.0.0] — 2026-03-18

### Summary
Initial v2 release with frontmatter standardization, Co-Design integration procedures, RTL bug tracking, and expanded architecture documentation.

### Highlights
- YAML frontmatter with `tool:`/`permission:` format across all sub-skills
- Co-Design step-by-step procedure (Playwright + REST) for HAS document access
- HAS document names per platform (NVL, PTL, LNL, MTL, ARL)
- NVL multi-die WARNING (PCH-H vs PCH-S)
- RTL Bugs & Workarounds table (HSDES 16029865294, 18043001729)
- Expanded UAOL/ACE architecture (ACE3 vs ACE4 comparison)
- NGA exit codes, test naming convention, PLS table (all 15 values)

---

## [1.0.0] — 2025-xx-xx

### Summary
Initial release of FV-USB skill tree with 4 sub-skills (debug, xhci, enumeration, power), 3 docs, and basic eval coverage.
