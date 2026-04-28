# FV-USB — USB Functional Validation Skill

USB domain validation skill for Intel xHCI controllers across client platforms (NVL, PTL, LNL, MTL, ARL, and upcoming).

**Owner:** Vejaya, Kalaivanan (`kvejaya`) | kalaivanan.vejaya@intel.com

---

## Quick Start

| Goal | Where to go |
|------|-------------|
| **New to USB validation?** | [docs/quick_start_guides.md](docs/quick_start_guides.md) |
| **Looking for a specific sub-skill?** | [SKILL.md](SKILL.md) § Sub-Skills |
| **Debugging a failure?** | [docs/debug_playbooks.md](docs/debug_playbooks.md) |
| **Need register/command help?** | [docs/cheat_sheet.md](docs/cheat_sheet.md) |
| **Checking known bugs?** | [docs/known_issues.md](docs/known_issues.md) |
| **Writing a new test?** | [docs/usb_test_template.py](docs/usb_test_template.py) |

## Skill Tree

```
fv-usb/                          ← Base skill (SKILL.md)
├── enumeration/                 ← PCI enumeration, DID/VID, BDF, device tree, eUSB2
├── xhci/                        ← xHCI register maps, capabilities, command ring
├── power/                       ← D-states, LPM U1/U2/U3, LTR, S0ix, UAOL power
├── debug/                       ← Failure triage, HSDES sightings, UAOL debug
│   └── etl-decode/              ← USB/UAOL ETL trace capture, decode, analysis
├── config-checkout/             ← PCI config validation, BAR, BIOS knobs
├── platform/                    ← Per-platform data (DID, BDF, port counts, die variants)
├── dbc/                         ← USB Debug Capability (USB3DbC/USB2DBC) setup
├── docs/                        ← Reference documents, playbooks, templates
│   ├── cheat_sheet.md           ← Quick command reference
│   ├── debug_playbooks.md       ← 5 step-by-step debug playbooks
│   ├── known_issues.md          ← RTL bugs, HSDES IDs, workarounds
│   ├── test_coverage_matrix.md  ← Test × platform coverage
│   ├── test_gap_analysis.md     ← Uncovered test scenarios
│   ├── agent_workflows.md       ← 6 standard agent workflows
│   ├── usb_has_extraction.md    ← HAS data extraction template
│   ├── quick_start_guides.md    ← Fast-track 5-7 step guides
│   └── usb_test_template.py     ← Python test template (NGA exit codes)
├── eval/                        ← Evaluation tests
└── tools/                       ← Self-check and quality gate scripts
```

## Agent

This skill is used by the **FV-USB** agent (`.opencode/agent/FV/FV-USB.md`).

Invoke via: `@FV-USB <your question>` in Copilot Chat.
