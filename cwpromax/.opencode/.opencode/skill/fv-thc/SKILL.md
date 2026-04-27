---
name: fv-thc
description: >-
  Touch Host Controller (THC) IP domain knowledge for post-silicon functional validation.
  Covers registers, HIDSPI/HIDI2C protocols, DMA architecture, power management, driver
  internals, platform data, debug/triage, and Wake-on-Touch across Intel Client SoC platforms
  (MTL, ARL, LNL, PTL, WCL, NVL, RZL, TTL).
disable: false
license: MIT
---

# FV-THC Skill Tree

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

Domain knowledge skill tree for **Touch Host Controller (THC)** post-silicon functional validation.
This is a lean orchestrator model -- the top-level skill provides an index and routing guide;
all detailed domain content lives in 9 on-demand sub-skills loaded individually.

---

## Sub-Skills (9) — 3-Tier File Structure

Each sub-skill uses a **3-tier file structure** to cleanly separate shared HW/protocol knowledge from platform-specific driver implementations:

| File | Content | When to Read |
|------|---------|-------------|
| `SKILL.md` | Shared HW behavior, protocol specs, register definitions | Always (platform-independent truth) |
| `linux.md` | Linux kernel driver implementation details | Linux-specific questions |
| `windows.md` | Windows driver implementation details | Windows-specific questions |

> **⚠️ Cross-platform safety**: Linux agents should read `SKILL.md` + `linux.md` only. Windows agents should read `SKILL.md` + `windows.md` only. This prevents mixing up platform-specific behaviors.

| Sub-Skill | Name | SKILL.md (shared) | linux.md | windows.md |
|-----------|------|-------------------|----------|------------|
| `fv-thc/registers` | Registers & PIO | Register maps, PIO flows, MMIO offsets, I2C APB sub-IP | — | — |
| `fv-thc/hidspi` | HIDSPI Protocol | Wire protocol, report types, ACPI DSM, SPI clock | QuickSPI states, probe, suspend/resume | HidSpiCx, DeviceState, filter driver |
| `fv-thc/hidi2c` | HIDI2C Protocol | Wire protocol, class requests, I2C sub-IP regs | QuickI2C states, IC_CON=0x663, 9/11 ints | 13-step init, 7/11 ints, SmartFilter |
| `fv-thc/dma` | DMA Architecture | PRD ring, channels, buffer alignment, HW behavior | Linux timeouts, SWDMA selective save | Windows timeouts, full unconfigure/reconfigure |
| `fv-thc/power` | Power Management | LTR HW regs, D3 levels, power domains, PMCLite | LTR defaults (5/500), runtime PM | LTR clamping (0x3FF), D0Exit flows |
| `fv-thc/driver` | Driver Source | Cross-platform index, shared concepts | State machines, probe sequences, pm_runtime | DeviceState, WDF callbacks, error recovery |
| `fv-thc/platform` | Platform Data | Device IDs, BDFs, BOM configs, BIOS prereqs | — | — |
| `fv-thc/debug` | Debug & Triage | Triage flows, failure signatures, errata, DFT | — | WPP GUIDs, registry keys, telemetry |
| `fv-thc/wot` | Wake-on-Touch | WoT architecture, UGD/PGD, GPIO wake config | — | — |

## Agent

This skill tree is consumed by the **FV-THC** agent (`FV-THC.md`), which serves as the
orchestrator for THC functional validation tasks including test script writing, execution,
debugging, and test plan improvement.

## Reference Documents

Key reference documents are in the `docs/` directory:

| File | Content |
|------|---------|
| `thc_has_4x_extraction.md` | Complete HAS extraction (37 sections) |
| `thc_bwg_extraction.md` | BIOS Writer Guide extraction |
| `thc_hidspi_hidi2c_kernel_study.md` | Deep Linux kernel source analysis |
| `thc_known_issues.md` | RTL bugs, HSDES sightings, audit findings |
| `thc_test_coverage_matrix.md` | 125 test IDs across 12 categories |
| `thc_cheat_sheets.md` | Quick-reference for common operations |
| `thc_test_gap_analysis.md` | Test script gap analysis |
| `thc_windows_driver_diff.md` | Windows HIDSPI vs HIDI2C comparison |
| `thc_agent_workflows.md` | Multi-agent orchestration workflows |
| `thc_vgpio_wot_architecture.md` | vGPIO WoT wake path synthesis |

## Self-Improvement Tools

Automated quality maintenance tools are in the `tools/` directory:

| Script | Purpose |
|--------|---------|
| `thc_self_check.py` | Structural integrity (10 checks) |
| `thc_self_verify.py` | Content correctness (114 assertions) |
| `thc_self_study.py` | Change monitoring (6 sources) |
| `thc_self_learn.py` | Knowledge gap detection |
| `thc_self_improve.py` | Full pipeline orchestrator |
| `thc_quality_gate.py` | CI/CD quality gate (self-check + self-verify) |
| `pre-commit-thc` | Git pre-commit hook for THC file changes |
| `self_improvement_config.json` | Shared configuration |
| `thc_self_common.py` | Shared utilities |

## Eval Tests

Skill evaluation tests are in the `eval/` directory:
- `thc_skill_eval_tests.md` — 97 eval tests across 11 categories


