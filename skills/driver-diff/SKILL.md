---
name: driver-diff
description: Cross-platform driver source comparison methodology — systematically compare Windows vs Linux (or other OS) driver implementations to find platform-specific behaviors, workarounds, and undocumented features
disable: false
license: MIT
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# Driver Diff Methodology

## Purpose

This skill codifies the methodology for systematically comparing driver implementations across operating systems (typically Windows vs Linux) for the same hardware IP. The goal is to identify:

- **Platform-specific workarounds** not documented in any spec
- **Behavioral differences** between OS implementations
- **Undocumented features** present in one driver but not the other
- **Bug fixes / errata mitigations** applied differently per OS
- **Missing documentation** — features implemented in code but absent from skill files

This methodology was developed during the Intel THC driver audit, comparing the Windows HIDSPI/HIDI2C drivers against the Linux kernel `intel-thc-hid` driver.

## When to Use This Skill

- After completing a spec-based audit (via `skill-audit`), to catch implementation-only knowledge
- When onboarding a new driver to a skill tree
- When a sighting/bug is found in one OS and you need to check if the other OS is affected
- When updating skill files to cover platform-specific behaviors

## Prerequisites

- Access to both driver source trees (local clones or remote API access)
- Completed spec-based audit (Priority 1 documents already studied)
- Understanding of the hardware IP being driven (register map, protocols)

## The Comparison Pipeline

### Phase 1: INVENTORY

Enumerate both driver source trees and build a structural comparison.

**Steps:**
1. List all source files in both drivers (`.c`, `.h`, `.py`, `.inf`, `.sys`, etc.)
2. Categorize by function:
   - Core driver logic (init, probe, remove)
   - Hardware abstraction (register access, DMA, interrupts)
   - Protocol implementation (SPI, I2C, HID, etc.)
   - Power management (suspend, resume, D-states)
   - Error handling and recovery
   - Platform/ACPI integration
   - OS-specific glue (WDF, IOCTLs, sysfs, etc.)
3. Build a file mapping: which files in Driver A correspond to which in Driver B?
4. Identify files with no counterpart (platform-specific)

**Output:** `driver_inventory.json`
```json
{
  "driver_a": {
    "name": "Linux intel-thc-hid",
    "path": "drivers/hid/intel-thc-hid/",
    "files": [
      {"path": "intel-thc/intel-thc-dev.c", "category": "core", "lines": 850},
      {"path": "intel-thc/intel-thc-dma.c", "category": "dma", "lines": 620}
    ]
  },
  "driver_b": {
    "name": "Windows HIDSPI",
    "path": "THCBase/IntelTHCBase/",
    "files": [
      {"path": "thc_dev.c", "category": "core", "lines": 920},
      {"path": "thc_dma.c", "category": "dma", "lines": 700}
    ]
  },
  "file_mapping": [
    {"a": "intel-thc-dev.c", "b": "thc_dev.c", "category": "core"},
    {"a": "intel-thc-dma.c", "b": "thc_dma.c", "category": "dma"}
  ],
  "unmatched_a": ["intel-thc-wot.c"],
  "unmatched_b": ["thc_pnp.c", "thc_ioctl.c"]
}
```

**Quality Gate G1:** All files categorized, mapping complete, unmatched files identified.

### Phase 2: STRUCTURAL DIFF

Compare the high-level structure of matched file pairs.

**For each matched pair:**
1. Extract function/method signatures from both files
2. Compare function names — identify common functions and unique-to-one-OS functions
3. Compare data structures (structs, enums, defines)
4. Compare register constant definitions
5. Compare error code handling

**Key questions:**
- Does Driver B have functions that Driver A lacks? (potential undocumented features)
- Does Driver A handle error cases that Driver B ignores? (potential robustness gaps)
- Do both drivers use the same register constants? (potential spec compliance issues)

**Output:** `structural_diff.md` — per-category comparison tables

### Phase 3: SEMANTIC DIFF

Deep comparison of implementation logic for matched functions.

**For each important function pair:**
1. Read the full implementation in both drivers
2. Compare the algorithm / flow:
   - Same steps in same order? 
   - Different error handling?
   - Different timing/delays?
   - Different register access patterns?
3. Identify workarounds (code with comments like "workaround", "errata", "quirk", "WAR", "hack")
4. Identify hardcoded magic values not from the spec
5. Identify conditional logic based on platform/stepping/revision

**Categorize each difference:**

| Category | Description | Action |
|----------|-------------|--------|
| **WORKAROUND** | Errata mitigation in one driver | Document in skill files, check if other OS needs it |
| **PLATFORM_SPECIFIC** | OS-specific implementation (WDF vs Linux subsystem) | Document if it affects behavior |
| **BEHAVIORAL_DIFF** | Same function, different behavior | Investigate which is correct per spec |
| **MISSING_IN_A** | Feature in B not in A | Document, assess if A should add it |
| **MISSING_IN_B** | Feature in A not in B | Document, assess if B should add it |
| **COSMETIC** | Naming/style differences only | Ignore |

**Output:** `semantic_diff.json` — structured findings per function pair

### Phase 4: FINDINGS ANALYSIS

Analyze all differences against the spec and skill files.

**For each non-COSMETIC finding:**
1. Check if the behavior is documented in any Priority 1 spec
2. Check if the behavior is already captured in skill files
3. Determine the correct behavior (spec wins, unless HW proves otherwise)
4. Generate an ECO (Engineering Change Order) if skill files need updating

**ECO format:**
```
ECO-001: [WORKAROUND] THC_PERFORMANCE_LIMITATION delay
  Source: Windows thc_quickspi.c:234
  Finding: Windows driver adds 100µs delay after write-to-read transitions
  Spec says: THC_PERFORMANCE_LIMITATION register, 10µs multiples (QuickSPI SwAS §4.3)
  Skill file: hidspi/SKILL.md — already documented
  Action: CONFIRMED — no change needed
```

**Output:** `eco_report.md` — all ECOs with disposition

### Phase 5: APPLY & VALIDATE

Apply approved ECOs to skill files.

1. Group ECOs by target skill file
2. Apply changes (MISSING items added, WRONG items corrected)
3. Run self-check and self-verify
4. Run cross-check against both driver sources
5. Update the driver diff report with final status

**Quality Gate G5:** All ECOs resolved (applied, deferred, or rejected with justification). Self-check PASS.

## Source Access Patterns

### Local Source Trees
```bash
# Direct file access
cat /path/to/driver_a/file.c
cat /path/to/driver_b/file.c
```

### Remote Source (GitHub API)
```python
import requests, base64

def fetch_github_file(repo, path, branch="main"):
    """Fetch a file from GitHub via API."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    resp = requests.get(url)
    if resp.status_code == 200:
        content = resp.json()
        if content.get('encoding') == 'base64':
            return base64.b64decode(content['content']).decode('utf-8')
    return None

# For large files, use the git blob API:
def fetch_github_blob(repo, path, branch="main"):
    """Fetch via directory listing + blob URL for large files."""
    dir_path = '/'.join(path.split('/')[:-1])
    filename = path.split('/')[-1]
    url = f"https://api.github.com/repos/{repo}/contents/{dir_path}?ref={branch}"
    entries = requests.get(url).json()
    for entry in entries:
        if entry['name'] == filename:
            blob = requests.get(entry['git_url']).json()
            return base64.b64decode(blob['content']).decode('utf-8')
    return None
```

### Windows Driver Source (local)
```
# Typical Intel driver layout
THCBase/IntelTHCBase/
├── thc_dev.c / thc_dev.h        # Core device management
├── thc_dma.c / thc_dma.h        # DMA engine control
├── thc_pio.c / thc_pio.h        # PIO (Programmed I/O)
├── thc_quickspi.c               # HIDSPI protocol
├── thc_quicki2c.c               # HIDI2C protocol
├── thc_pm.c                     # Power management
├── thc_interrupt.c              # Interrupt handling
└── *.inf, *.rc                  # OS packaging
```

## Comparison Heuristics

### Function Matching
When function names differ between OS implementations, use these heuristics:
1. **Name similarity**: `thc_dma_init` ↔ `ThcDmaInitialize` (strip prefix, case-normalize)
2. **Register access**: Functions touching the same registers likely correspond
3. **Call position**: Functions called in the same sequence (probe/init, ISR, suspend/resume)
4. **Comment/doc overlap**: Similar comments often indicate corresponding functions

### Workaround Detection
Search for these patterns in source code:
```
workaround, WORKAROUND, WAR, errata, ERRATA, quirk, QUIRK,
hack, HACK, TODO, FIXME, BUG, "known issue", "silicon bug",
"stepping", "revision", "platform specific", HSD, HSDES
```

### Magic Value Detection
Flag hardcoded values that don't match known register definitions:
```python
# Suspicious: magic delays
udelay(100)          # Why 100µs? Is this spec'd?
msleep(300)          # Reset hold time — check spec

# Suspicious: magic masks
val & 0x3F           # What are these bits?
reg |= (1 << 17)    # Bit 17 of what register?
```

## Common Pitfalls

| # | Pitfall | Prevention |
|---|---------|------------|
| 1 | Comparing OS glue code (WDF vs Linux subsystem) | Focus on HW interaction, not OS abstraction |
| 2 | Assuming one OS is "correct" and the other is "wrong" | Both may be correct for their platform; check the spec |
| 3 | Ignoring #ifdef / conditional compilation | These often hide platform-specific workarounds |
| 4 | Missing workarounds in comments vs code | Search comments AND code patterns |
| 5 | Not checking driver version / date | Ensure you're comparing similar-era code |
| 6 | Treating all differences as findings | Many differences are OS-specific and expected |
| 7 | Context overflow from reading both drivers simultaneously | Read one driver at a time, extract findings, then compare |

## Example: THC Driver Diff Results

From the actual THC audit:

```
Windows HIDSPI driver: 29 files, ~15K lines
Windows HIDI2C driver: 28 files, ~14K lines  
Linux intel-thc-hid:   12 files, ~8K lines

Results:
  28 ECOs generated
  9 behavioral discrepancies found
  12 items missing from skill files (added)
  4 workarounds unique to Windows driver
  2 workarounds unique to Linux driver
  
Key findings:
  - Windows uses different DMA buffer sizes (platform tuning)
  - Linux has WoT (Wake-on-Touch) via vGPIO; Windows uses different wake path
  - Both drivers implement THC_PERFORMANCE_LIMITATION but with different defaults
  - Windows has additional IOCTL for firmware update not in Linux
```

## Integration with Other Skills

### Recommended Workflow
```
1. skill-audit (spec-based audit first)
     └── doc-study (per spec document)
2. driver-diff (implementation audit second)
     └── Compare OS A vs OS B drivers
3. self-improve (regression validation)
     └── self-check + self-verify after all changes
```

The driver diff should always come AFTER the spec-based audit, because:
- Spec knowledge helps you interpret driver code correctly
- You can immediately tell if a driver behavior matches or contradicts the spec
- Skill files already have a solid foundation to diff against


