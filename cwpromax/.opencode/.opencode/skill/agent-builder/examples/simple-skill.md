---
name: silicon-validation-knowledge
description: "Domain knowledge for silicon validation workflows, covering common procedures, terminology, and decision criteria for platform validation engineers"
disable: false
license: MIT
---

# Silicon Validation Knowledge Base

## Overview

This skill provides domain knowledge for silicon validation engineers working on Intel platforms. It covers common validation procedures, terminology, decision frameworks, and troubleshooting guides.

## Domain Knowledge

### Platform Validation Lifecycle

The validation lifecycle follows these stages:

1. **Pre-Silicon:** Simulation and emulation-based validation before silicon arrives
2. **Power-On (A0):** First silicon power-on, basic functionality checks
3. **Post-Silicon (B0+):** Feature validation on production-intent silicon steppings
4. **Production Validation (PV):** Final validation before mass production release

### Key Terminology

| Term | Definition |
|------|-----------|
| **BKC** | Best Known Configuration — validated combination of BIOS, drivers, and OS |
| **Stepping** | Silicon revision (A0, B0, C0, etc.) — each fixes bugs from previous |
| **Sighting** | A bug or issue found during validation, tracked in HSDES |
| **NGA** | Next Generation Automation — Intel's test automation platform |
| **PySV** | PythonSV — Python-based silicon validation framework for register access |
| **POST Code** | Power-On Self Test code — indicates boot progress stage |
| **S-State** | System power state (S0=active, S3=sleep, S4=hibernate, S5=off) |
| **C-State** | CPU power state (C0=active, C1=halt, C6=deep sleep, C10=deepest) |

### Common Validation Domains

| Domain | What It Covers | Key Tools |
|--------|---------------|-----------|
| Power Management | S-states, C-states, thermal, power sequencing | PySV, PMC, power analyzers |
| IO Connectivity | USB, PCIe, Thunderbolt, SATA, NVMe | TTK3, protocol analyzers |
| Memory/Storage | DDR, eMMC, UFS, NAND | Memory test tools, TTK3 |
| Security | Boot Guard, fTPM, secure boot, CSME | SPI flash tools, CSME tools |
| Graphics/Display | GPU, display output, media decode | GFX test suites |
| Platform Stability | Stress testing, long-duration runs, cycling | Automation frameworks |

## Common Scenarios

### Scenario: New BKC Validation

**Trigger:** A new BKC kit is released via OneBKC

**Process:**
1. Download the BKC package using OneBKC tools
2. Flash the new BIOS/IFWI to the platform using TTK3 SPI tools
3. Install the corresponding OS image and drivers
4. Run the standard validation test suite via NGA
5. Triage any failures — compare against previous BKC results
6. Report pass rate and new sightings to the validation team

**Expected Outcome:** Pass rate documented, new failures triaged, sightings filed for genuine issues

### Scenario: Boot Failure Investigation

**Trigger:** Platform fails to reach OS after BIOS flash

**Process:**
1. Check POST codes using TTK3 post code monitoring
2. If POST codes stop early (before 0xA0), the issue is likely in BIOS/firmware
3. If POST codes reach OS hand-off but OS doesn't load, check boot device
4. Capture UART serial logs during boot for detailed failure information
5. Compare POST code sequence against known-good reference
6. If BIOS is suspected, try a known-good BIOS image

**Expected Outcome:** Root cause identified (BIOS, boot device, or hardware issue)

### Scenario: Intermittent Test Failure

**Trigger:** A test passes on some runs but fails on others

**Process:**
1. Gather failure rate data — run the test 10-20 times to establish percentage
2. Check if the failure correlates with specific conditions (time of day, temperature, preceding tests)
3. Review test logs for timing-sensitive operations
4. Check if the failure exists in HSDES as a known sighting
5. If new, file a sighting with reproduction rate and relevant logs
6. Classify: silicon issue (consistent across platforms) vs. platform issue (specific to one setup)

**Expected Outcome:** Failure classified, sighting filed with reproduction data

## Reference Tables

### POST Code Quick Reference

| POST Code Range | Boot Stage |
|----------------|------------|
| 0x00 - 0x0F | SEC (Security Phase) |
| 0x10 - 0x2F | PEI (Pre-EFI Initialization) |
| 0x30 - 0x4F | DXE (Driver Execution Environment) |
| 0x50 - 0x8F | BDS (Boot Device Selection) |
| 0x90 - 0x9F | OS Boot |
| 0xA0+ | OS Running |

### Sighting Priority Guide

| Priority | Criteria | Response Time |
|----------|----------|--------------|
| P1 - Critical | Platform cannot boot, blocks all validation | Same day |
| P2 - High | Feature completely broken, blocks feature validation | 1-2 days |
| P3 - Medium | Feature partially working, workaround exists | 1 week |
| P4 - Low | Minor issue, cosmetic, or rare edge case | Next milestone |

## Troubleshooting

### Platform Won't Power On
**Symptom:** No POST codes, no fan spin, no LED activity
**Cause:** Power supply issue, power sequencing failure, or dead silicon
**Solution:** Check PSU connections, verify PDU power output with TTK3 power tools, try a known-good PSU

### Platform Hangs at POST Code
**Symptom:** POST code output stops at a specific value and doesn't progress
**Cause:** Depends on the POST code — usually initialization failure of the component that stage is testing
**Solution:** Look up the specific POST code in the BIOS POST code table, check related hardware/firmware

### Test Runs Show 100% Failure
**Symptom:** Every test in a suite fails
**Cause:** Usually infrastructure issue (station misconfiguration, DUT offline, network problem) rather than actual test failures
**Solution:** Check station status in NGA, verify DUT connectivity, check if other stations pass the same suite

## Limitations

- This knowledge base covers general validation procedures; specific product details require loading product-specific skills
- POST code tables vary by BIOS vendor and platform — always cross-reference with the specific BIOS release notes
- Sighting priority guidelines are general — individual teams may have different escalation criteria
