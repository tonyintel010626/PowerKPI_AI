> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Agent Orchestration Workflows

This document describes 5 common multi-agent workflows for THC functional validation.
Each workflow shows which agents/skills are involved, when to use it, and the expected
inputs and outputs at each step.

---

## 1. THC Device Not Working (Full Triage)

### When to Use
- Touch device is completely non-functional (no enumeration, no input reports)
- User reports "no touch" after a BIOS update, platform change, or cold boot
- Need to systematically isolate HW vs SW vs config issue

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — gather symptoms, pick triage path |
| 2 | **fv-thc/debug** | Load debug playbook — systematic triage flow |
| 3 | **FV_Debugger_V1** | Confluence wiki BKM search + HSDES pattern match |
| 4 | **hsdes** | Sighting lookup — check if issue is already known |
| 5 | **TTK3-COMM** | GPIO probe — verify interrupt line state |
| 6 | **TTK3-POWER** | Power cycle platform if needed to recover |

### ASCII Flowchart

```
  [User: "Touch not working"]
          |
          v
  +---------------+
  |    FV-THC     |  Gather: platform, THC port, protocol, OS,
  | (orchestrator)|  BIOS version, last known-good state
  +-------+-------+
          |
          v
  +-------------------+
  | fv-thc/debug      |  Load debug skill -> run Phase 1-5 triage:
  | (load playbook)   |  PCI enum? -> MMIO accessible? -> INT line?
  +---------+---------+  -> DMA running? -> Protocol error?
            |
            v
  +---------------------+
  | FV_Debugger_V1      |  Search Confluence wiki for matching BKMs
  | (wiki BKM search)   |  (FVCommon, DebugEncyclopedia pages)
  +----------+----------+  Pattern match: BSOD? HW fail? PM timeout?
             |
             v
  +-------------------+
  |      hsdes        |  Query sighting_central.sighting for THC
  | (sighting lookup) |  keywords + platform + stepping
  +--------+----------+  -> Known sighting? Return HSDES ID + WA
           |
           v
  +-------------------+
  |    TTK3-COMM      |  Probe GPIO interrupt pin state:
  |  (GPIO probe)     |  Is INT line stuck LOW? Floating? No toggle?
  +--------+----------+  Probe I2C/SPI bus for device presence
           |
           v
  +-------------------+     Yes: power cycle
  |   TTK3-POWER      | -----------------------> [Retry from FV-THC]
  | (power cycle)     |     No: return diagnosis
  +--------+----------+
           |
           v
  [Diagnosis: root cause + recommended fix]
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | User symptom description | Structured triage context (platform, port, protocol) |
| fv-thc/debug | Triage context | Phase diagnosis (which phase failed: PCI/MMIO/INT/DMA/protocol) |
| FV_Debugger_V1 | Failure pattern keywords | Wiki BKM matches (page IDs, remediation steps) |
| hsdes | THC + platform + symptom keywords | Known sighting IDs + workarounds (or "no match") |
| TTK3-COMM | GPIO pin number, bus type | Pin state (HIGH/LOW/floating), bus ACK/NAK |
| TTK3-POWER | Power cycle command | Platform rebooted, POST code sequence |

---

## 2. THC BIOS Update + Validation

### When to Use
- Flashing a new IFWI/BIOS image that changes THC configuration
- Validating THC functionality after a BIOS update
- Pre-silicon to post-silicon BIOS handoff verification

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — confirm target, IFWI image, THC config |
| 2 | **TTK3-BIOS** | Flash the IFWI image via SPI |
| 3 | **TTK3-BOOT** | Monitor POST codes during boot |
| 4 | **FV-THC** | Run THC enumeration test to validate |

### ASCII Flowchart

```
  [User: "Flash new BIOS and validate THC"]
          |
          v
  +---------------+
  |    FV-THC     |  Confirm: IFWI path, target platform,
  | (orchestrator)|  expected THC port config (SPI/I2C),
  +-------+-------+  backup current IFWI? (recommended)
          |
          v
  +-------------------+
  |    TTK3-BIOS      |  1. Read current IFWI (backup)
  | (flash IFWI)      |  2. Erase flash
  +---------+---------+  3. Program new IFWI
            |            4. Verify write
            v
  +-------------------+
  |    TTK3-BOOT      |  Monitor POST code sequence:
  | (POST codes)      |  - Expect: standard boot POST codes
  +---------+---------+  - Watch for: THC init POST codes
            |            - Fail if: stuck at specific code
            v
  +-------------------+
  |    FV-THC         |  Run THC enumeration test:
  | (enum validation) |  1. PCI device present?
  +---------+---------+  2. BAR0 mapped?
            |            3. HID descriptor readable?
            v            4. Touch input functional?
  [PASS/FAIL report with details]
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | IFWI image path, platform ID | Validated config, go/no-go decision |
| TTK3-BIOS | IFWI binary, SPI flash params | Flash success/fail, backup image path |
| TTK3-BOOT | Boot timeout, expected POST codes | POST code sequence log, boot success/fail |
| FV-THC | Platform handle, THC port | Enum test result: PASS(0)/FAIL(9) + details |

---

## 3. THC Power Management Debug

### When to Use
- Touch fails after S0ix/S3/S4 resume
- THC stuck in wrong power state (D0i2 not entering, D3 not exiting)
- LTR values incorrect — blocking deeper platform sleep
- PMC rejecting THC power gating requests

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — gather PM symptom details |
| 2 | **fv-thc/power** | Load power skill — LTR, D0i2, D3 level details |
| 3 | **FV-PM-SOUTH** | PMC-side debug — sideband messages, power well state |
| 4 | **pysv** | Direct register read via PythonSV namednodes |
| 5 | **FV_Debugger_V1** | PMC firmware version check via `pmc` skill |

### ASCII Flowchart

```
  [User: "Touch broken after resume" / "THC not entering D0i2"]
          |
          v
  +---------------+
  |    FV-THC     |  Gather: which PM transition failed?
  | (orchestrator)|  S0ix? S3? D3? D0i2? Resume or entry?
  +-------+-------+  Which port? Linux or Windows?
          |
          v
  +-------------------+
  | fv-thc/power      |  Load PM knowledge:
  | (load skill)      |  - LTR registers (LP/Active EN, VALUE, SCALE, REQ)
  +---------+---------+  - D3 levels (0-3), D0i2 timer, CGPG
            |            - Known cross-platform differences
            v
  +-------------------+
  |  FV-PM-SOUTH      |  Debug PMC side:
  | (PMC debug)       |  - IOSF SB message trace
  +---------+---------+  - Power well state (THC_PGD on/off?)
            |            - PMCLite request/response
            v
  +-------------------+
  |      pysv         |  Read THC registers directly:
  | (register read)   |  - LTR_CTRL (LP_LTR_EN, ACTIVE_LTR_EN)
  +---------+---------+  - PRT_CONTROL (port_type, quiesce)
            |            - READ_DMA_INT_STS (DMA active?)
            v
  +-------------------+
  | FV_Debugger_V1    |  Check PMC firmware version:
  | (PMC FW check)    |  - Is PMC FW compatible with THC PM?
  +---------+---------+  - Known PMC sightings for THC power?
            |
            v
  [Diagnosis: PM root cause + register dump + fix]
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | User PM symptom | Structured PM debug context |
| fv-thc/power | PM context | Relevant register list, expected values, known issues |
| FV-PM-SOUTH | THC port, PM transition type | PMC power well state, SB message trace |
| pysv | Register paths (namednodes) | Raw register values (hex) |
| FV_Debugger_V1 | Platform, PMC version query | PMC FW version, compatibility status |

---

## 4. THC Test Execution + Failure Triage

### When to Use
- Running THC test suites via NGA automation infrastructure
- Triaging test failures reported by NGA (pass/fail results)
- Filing sightings for new failures

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — select test suite, configure parameters |
| 2 | **nga/testrun** | Execute test run on NGA infrastructure |
| 3 | **nga/results** | Retrieve test execution results |
| 4 | **nga/failure** | Analyze failure buckets (if tests failed) |
| 5 | **hsdes** | File or link to existing sighting |

### ASCII Flowchart

```
  [User: "Run THC enum test suite on PTL BOM52"]
          |
          v
  +---------------+
  |    FV-THC     |  Identify: test suite ID, platform config,
  | (orchestrator)|  station/pool, expected pass criteria
  +-------+-------+
          |
          v
  +-------------------+
  |   nga/testrun     |  Submit test run:
  | (execute test)    |  - Suite ID, configuration
  +---------+---------+  - Station pool assignment
            |            - Wait for completion (poll status)
            v
  +-------------------+
  |   nga/results     |  Retrieve results:
  | (get results)     |  - Per-test PASS/FAIL/SKIP/ERROR
  +---------+---------+  - Execution logs, timestamps
            |
       +----+----+
       |         |
     PASS      FAIL
       |         |
       v         v
  [Report]  +-------------------+
            |   nga/failure     |  Analyze failure:
            | (failure bucket)  |  - Match to known failure buckets
            +---------+---------+  - Get failure signatures
                      |
                      v
            +-------------------+
            |      hsdes        |  Sighting management:
            | (file sighting)   |  - Search existing sightings
            +---------+---------+  - If new: file sighting with logs
                      |            - If known: link to existing HSDES
                      v
            [Sighting ID + triage summary]
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | Test suite name, platform, BOM | Test run configuration |
| nga/testrun | Suite ID, station config | Test run ID, execution status |
| nga/results | Test run ID | Per-test results (PASS/FAIL/SKIP), logs |
| nga/failure | Failed test IDs | Failure bucket IDs, signatures, known matches |
| hsdes | Failure signature, platform info | HSDES sighting ID (new or existing) |

---

## 5. THC Cross-Platform Comparison

### When to Use
- Debugging a failure that only reproduces on one platform but not another
- Validating THC behavior across MTL/LNL/PTL/NVL/ARL/RZL/TTL
- Comparing HIDSPI vs HIDI2C protocol behavior on the same platform
- Checking DMA timeout or power management differences across platforms

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — define comparison scope |
| 2a | **fv-thc/hidspi** | Load HIDSPI protocol details |
| 2b | **fv-thc/hidi2c** | Load HIDI2C protocol details (parallel with 2a) |
| 3 | **fv-thc/dma** | Compare DMA timeouts, PRD configs |
| 4 | **fv-thc/power** | Compare PM differences across platforms |

### ASCII Flowchart

```
  [User: "Compare THC behavior: PTL HIDSPI vs NVL HIDI2C"]
          |
          v
  +---------------+
  |    FV-THC     |  Define comparison:
  | (orchestrator)|  - Platform A vs Platform B
  +-------+-------+  - Protocol A vs Protocol B
          |          - Focus area (DMA? PM? init? all?)
          |
     +----+----+  (parallel load)
     |         |
     v         v
  +---------+ +---------+
  |fv-thc/  | |fv-thc/  |  Load both protocol skills:
  |hidspi   | |hidi2c   |  - SPI: clock, opcodes, ICR, fragments
  |(SPI     | |(I2C     |  - I2C: speed modes, IC_CON, MPS WA
  | details)| | details)|  - Compare: descriptor sizes, report flow
  +----+----+ +----+----+
       |           |
       +-----+-----+
             |
             v
  +-------------------+
  |    fv-thc/dma     |  Compare DMA behavior:
  | (DMA timeouts)    |  - PRD ring sizes (Linux vs Windows)
  +---------+---------+  - Pause timeouts (100us/10ms vs 10us/1s)
            |            - SWDMA save/restore differences
            v            - Streaming mode thresholds
  +-------------------+
  |   fv-thc/power    |  Compare PM behavior:
  | (PM differences)  |  - D3 levels (Gen4.1+ has 4 levels)
  +---------+---------+  - LTR values (Active/LP defaults)
            |            - SET_POWER (fire-and-forget vs sync)
            v            - WoT support (per-platform)
  +--------------------------------------+
  | Cross-Platform Comparison Report     |
  |--------------------------------------|
  | Feature    | Platform A | Platform B |
  | DMA timeout| ...        | ...        |
  | D3 levels  | ...        | ...        |
  | LTR config | ...        | ...        |
  | Protocol   | ...        | ...        |
  +--------------------------------------+
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | Platform pair, protocol pair, focus area | Comparison scope definition |
| fv-thc/hidspi | Platform context | SPI config: clock (125 MHz base), IO modes, opcodes, ICR format |
| fv-thc/hidi2c | Platform context | I2C config: IC_CON (0x663 Linux), speed modes, MPS workaround |
| fv-thc/dma | Both platform contexts | DMA comparison table: timeouts, PRD sizes, SWDMA behavior |
| fv-thc/power | Both platform contexts | PM comparison table: D3 levels, LTR, SET_POWER, WoT |

---

## General Notes

### Multi-Skill Loading
FV-THC can load multiple sub-skills in a single response when a question spans
domains. For example, a power management issue involving DMA stalls would load
both `fv-thc/power` and `fv-thc/dma` simultaneously.

### Agent Availability Caveats
- **FV-PM-NORTH**: Referenced but not yet created; use FV_Debugger_V1 as fallback
- **FV-GenDebugger**: Exists but currently disabled (`disable: true`)
- **logs-keeper**: Exists but not loaded as available subagent; use `minion` directly
- **TTK3-COMM**: GPIO/UART/HID methods are STUBs — confirm capability first

### HAS-First Policy
All workflows that involve register values, bit fields, or DMA descriptor formats
MUST consult the THC IP HAS (via Co-De Sign) before producing final answers.
Sub-skill knowledge is supplementary; the HAS is authoritative.

---

## SwAS-Derived Workflows (Added 2026-03-06)

> Source: QuickSPI SwAS v1.0, QuickI2C SwAS v1.0. These workflows address scenarios documented in the Software Architecture Specifications.

## 6. SwAS Consultation Workflow

### When to Use
- Debugging a Windows-specific THC issue (ISR/DPC, quiesce, buffer throttling)
- Investigating protocol-specific reset timeout differences (1s SPI vs 5s I2C)
- Checking ECO registry key behavior or ACPI DSM encoding
- Cross-referencing kernel behavior against SwAS-documented Windows behavior

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — classify issue as SPI or I2C, Windows or Linux |
| 2 | **fv-thc/hidspi** or **fv-thc/hidi2c** | Load protocol-specific skill |
| 3 | **fv-thc/driver** | Load driver skill for cross-platform comparison |
| 4 | **codesign** | Query Co-De Sign for HAS register details if needed |

### ASCII Flowchart

```
  [User: "Why does SPI reset timeout differ on Windows?"]
          |
          v
  +---------------+
  |    FV-THC     |  Classify: which protocol? Which OS?
  | (orchestrator)|  Load SwAS cross-reference from docs
  +-------+-------+
          |
          v
  +-------------------+
  | fv-thc/hidspi     |  SwAS says: SPI reset timeout = 1s
  | (protocol skill)  |  Kernel says: 5s (conservative)
  +---------+---------+  Diff: Windows follows SwAS; Linux doesn't
            |
            v
  +-------------------+
  | fv-thc/driver     |  Cross-reference:
  | (driver skill)    |  - Windows QuickSPI: 1s timeout
  +---------+---------+  - Linux quickspi: 5s timeout
            |            - QuickI2C: 5s on both
            v
  +-------------------+
  |    codesign       |  If register-level detail needed:
  | (HAS lookup)      |  Query HAS for reset timer registers
  +---------+---------+
            |
            v
  [Answer with SwAS citation + kernel cross-ref]
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | User question about SwAS-documented behavior | Classified query (protocol, OS, SwAS section) |
| fv-thc/hidspi or hidi2c | Protocol context | SwAS-documented value + kernel value + diff analysis |
| fv-thc/driver | Cross-platform context | Side-by-side comparison (Windows SwAS vs Linux kernel) |
| codesign | Register name / offset | HAS register definition (authoritative) |

---

## 7. Wake-on-Touch Debug Workflow

### When to Use
- Touch does not wake system from sleep (S0ix, Connected Standby)
- WoT works on Windows but not Linux (or vice versa)
- vGPIO pad locked — PADCFGLOCK_VGPIO_THC0 ≠ 0x0
- Extension INF missing on Windows (WoT_QuickSpiExtension.inf / WoT_QuickI2cExtension.inf)

### Agents/Skills Involved
| Step | Agent/Skill | Role |
|------|-------------|------|
| 1 | **FV-THC** | Orchestrator — gather WoT symptom, OS, protocol |
| 2 | **fv-thc/power** | Load power skill — WoT architecture details |
| 3 | **fv-thc/platform** | Load platform skill — vGPIO pad, BIOS prereqs |
| 4 | **TTK3-COMM** | GPIO probe — check wake GPIO state |
| 5 | **FV-PM-SOUTH** | PMC debug — verify wake event delivery |

### ASCII Flowchart

```
  [User: "Touch not waking system from sleep"]
          |
          v
  +---------------+
  |    FV-THC     |  Gather: which OS? SPI or I2C?
  | (orchestrator)|  Which sleep state? S0ix? Connected Standby?
  +-------+-------+  Last known-good state?
          |
          v
  +-------------------+
  | fv-thc/power      |  WoT architecture check:
  | (WoT knowledge)   |  - Wake path: GPIO → vGPIO → PMC (NOT THC IP!)
  +---------+---------+  - THC PCI caps: WAKE=No, PME=No
            |            - Linux: dev_pm_set_dedicated_wake_irq()
            |            - Windows: Extension INF required
            v
  +-------------------+
  | fv-thc/platform   |  Platform prerequisites:
  | (BIOS prereqs)    |  - PADCFGLOCK_VGPIO_THC0 must be 0x0
  +---------+---------+  - ACPI GpioInt() wake source configured?
            |            - _S0W return value correct?
            v
  +-------------------+
  | TTK3-COMM         |  Physical GPIO probe:
  | (GPIO state)      |  - Is wake GPIO toggling on touch?
  +---------+---------+  - Is vGPIO pad locked/unlocked?
            |            - Is INT line stuck?
            v
  +-------------------+
  | FV-PM-SOUTH       |  PMC wake event debug:
  | (PMC debug)       |  - Was wake event received by PMC?
  +---------+---------+  - Was platform wake initiated?
            |            - PMCLite SB message trace
            v
  [Diagnosis: WoT root cause]

  Common WoT failure causes:
  1. PADCFGLOCK_VGPIO_THC0 ≠ 0x0 (BIOS lock prevents vGPIO config)
  2. Extension INF not installed (Windows only)
  3. _PRW on ACPI device with GPIO → Windows crash (SWAS-004)
  4. I2C: SET_POWER(SLEEP) not sent on WoT entry
  5. SPI: Device not in active sensing mode during WoT
  6. GPIO pad not configured as wake source in ACPI
```

### Expected Inputs/Outputs

| Step | Input | Output |
|------|-------|--------|
| FV-THC | User WoT symptom | Structured WoT debug context (OS, protocol, sleep state) |
| fv-thc/power | WoT context | WoT architecture details, expected behavior per OS/protocol |
| fv-thc/platform | Platform ID | BIOS prerequisites, vGPIO pad status, ACPI requirements |
| TTK3-COMM | GPIO pin number | GPIO state (HIGH/LOW/toggling), vGPIO lock status |
| FV-PM-SOUTH | Wake event query | PMC wake event log, SB message trace |
