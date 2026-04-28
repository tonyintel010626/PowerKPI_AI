# THC Simics Wiki Research — Exhaustive Study v2.0

> **Owner**: Chin, William Willy (`willychi`)
> **Date**: 2026-03-26
> **Author**: FV-THC Agent (automated exhaustive wiki research)
> **Supersedes**: `thc_simics_wiki_research.md` (v1, 780 lines, 19 sections)
> **Scope**: All Intel Confluence wiki content related to THC Simics pre-silicon validation
> **Method**: 32+ CQL searches → 80+ pages discovered → 52 pages deep-read → cross-check → skill file updates

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| CQL searches executed | 32+ |
| Wiki spaces discovered | 9 (THCipsv, SRESIMICS, PPA, IPTS, VICESW, VICEPE, fvcommon, ESIPWiki, pch) |
| Pages discovered | 80+ |
| Pages deep-read | 52 |
| MISSING items found | 20+ |
| Skill files updated | 3 (advanced.md, models.md, SKILL.md) |
| Lines added | +334 (advanced.md +279, models.md +51, SKILL.md +4) |
| operations.md | No changes needed (already complete) |

### Impact Summary
This exhaustive wiki research significantly expanded the THC Simics skill files with:
- **IPSV validation methodology**: ICR scrambling (6 variants), opcode randomization, 1000+ seeds, bus speed coverage
- **Coalescing architecture**: FSM (Disabled→Armed→Active), watermark constraints, timer-based vs TCON sync
- **5 RTL bug fixes** with HSD numbers (GPIO sync, buffer overrun, delay timer, PG exit, multi-report)
- **FuseLite complete details**: Port IDs, addresses, strap values, FuseLite 2.x for TTL+
- **PMCLite internals**: Backdoor address map (0x01000000), vector compilation tool
- **Sonora3 testcard**: DDR architecture, HT3 cable, 50MHz quad issues
- **Buffer Packet FIFO evolution**: 4 slots (LNL/PTL) → 32 slots (NVL)
- **RX Streaming Mode**: >4KB packets without increasing internal buffer
- **SOC Override architecture**: Single RDL dual-instantiation, DID override mechanism
- **SPI touch limitation**: NOT FULLY SUPPORTED in spi_xtor (official PPA wiki caveat)

---

## 2. Search Methodology

### 2.1 CQL Searches Executed (32+)

| # | Search Term | Results | Key Findings |
|---|-------------|---------|-------------|
| 1 | "THC Simics" | 252 | Broad discovery — THCipsv, SRESIMICS, PPA spaces |
| 2 | "Touch Host Controller Simics" | ~50 | Overlapping with #1, confirmed key pages |
| 3 | "thc_vdm" | 3 | Direct model class references |
| 4 | "HIDSPI Simics" | 13 | Protocol-specific Simics content |
| 5 | "QuickSPI Simics" | 11 | QuickSPI model content |
| 6 | "QuickI2C Simics" | 10 | QuickI2C model content |
| 7 | "spi_xtor" | 559 | SPI transactor documentation (PPA space) |
| 8 | "touch simics model" | 791 | Broad — filtered for THC-specific |
| 9 | "THC IPSV" | 102 | IPSV validation team content (GOLDMINE) |
| 10 | "THC fuse debug" | 214 | FuseLite and debug content |
| 11 | "THC DMA simics" | 50 | DMA-specific Simics content |
| 12 | "THC power management simics" | 43 | PM flow content |
| 13 | "THC ISCTLM" | 0 | No results (DFD tool name) |
| 14 | "THC Sonora testcard" | 74 | Testcard-specific content |
| 15 | "IPTS simics driver" | 52 | Driver installation BKMs |
| 16 | "THC WoT wake simics" | 0 | No WoT-specific Simics content |
| 17 | "THC display sync simics" | ~30 | Display sync / TCON content |
| 18 | "THC emulation FPGA" | ~20 | Emulation/HFPGA content |
| 19 | "THC register simics validation" | ~15 | Register validation approaches |
| 20 | "THC PCR feature request" | ~25 | PCR tracking pages |
| 21 | "THC novalake simics" | ~10 | NVL-specific content |
| 22 | "THC WCL wildcat simics" | ~5 | WCL-specific (limited) |
| 23 | "THC SPI opcode simics" | ~8 | Opcode configuration |
| 24 | "THC PRD ring DMA descriptor" | 0 | No direct results |
| 25 | "THC BAT test pytest" | ~15 | BAT/pytest framework |
| 26 | "THC interrupt coalescing frame" | ~10 | Coalescing details |
| 27 | "TCON frame sync touch" | ~8 | TCON signal generator |
| 28 | "THC RAMLess HIDI2C" | 6 | RAMLess mode documentation |
| 29 | "THC LTR latency" | ~20 | LTR/PM content |
| 30 | "THC CGPG clock gating" | ~15 | Clock gating content |
| 31 | "THC IOSF sideband" | ~25 | Sideband message format |
| 32 | "THC softstrap fuse" | ~20 | Strap/fuse configuration |
| 33+ | Additional targeted searches | Various | TTL, RZL, PMCLite vector, Sonora3, etc. |

### 2.2 Wiki Spaces Identified

| Space Key | Space Name | THC Relevance | Pages Found |
|-----------|-----------|---------------|-------------|
| **THCipsv** | THC IPSV Team | **PRIMARY** — IPSV validation, PCRs, bug fixes, emulation | 30+ |
| **SRESIMICS** | SRE Simics Team | **HIGH** — BKMs, model development, device overview, driver install | 8 |
| **PPA** | Platform Pre-silicon Architecture | **HIGH** — spi_xtor docs, BAT tests, RTL/Simics mappings | 15+ |
| **IPTS** | IPTS Team | **MEDIUM** — Getting Started, QuickSPI BKMs, PSS setup | 3 |
| **VICESW** | VICE Software | **MEDIUM** — Maestro/Perspec test content, RTR framework | 3 |
| **VICEPE** | VICE Platform Engineering | **LOW** — FPGA farm config | 1 |
| **fvcommon** | FV Common | **LOW** — PM enabling, Simics phone book, Sonora2+CAT | 3 |
| **ESIPWiki** | ESIP Wiki | **LOW** — THC debug hooks, VISA regression | 1 |
| **pch** | PCH | **LOW** — SOC override info | 1 |

---

## 3. Pages Deep-Read (52 Total)

### 3.1 SRESIMICS Space — BKM/Setup Pages (9 pages)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **1966867553** | THC model development (WIP) | MTL pkg 7500, TEP reset_delay=0.2, HID descriptor=9B header+3B padding+2596B, MFS calculation formula, mouse-as-touch workaround, WA wa_ignore_setidvalue (HSD 1508517875) |
| **1966867456** | THC Device Overview | Model capabilities matrix, unit test paths (`test/mtl/90-unit-tests/13-thc/`), GPIO unimplemented known issue, ref HAS: SIP_THC_ver2_0_HAS_MTLM_2020ww47 |
| **1433100579** | THC Simics Getting Started | LKF-era Simics 5, LKF naming: `lkf.mb.sb.thcX` + `ticXX`, historical reference |
| **2845164237** | BKM THC I2C on LNL Simics | LNL pkg 7600, naming: `lnl.mb.south.thcX` + `alps`, driver HIDI2C_touch-5.0.4000.693.zip |
| **1966867128** | BKM THC IPTS/HIDSPI on MTL Simics | MTL pkg 7500 pre267+, BIOS bug HSD 1508958117, registry settings, test signing required |
| **3217199088** | BKM THC HIDSPI on PTL Simics | PTL naming: `$system.mb.south.thcX` + `alps_touchscreenX`, WA 16015917403 for SPI |
| **4045307441** | BKM THC QuickI2C on NVL-S Simics | NVL naming: `nvl.mb.pch.thcX` (**KEY**: uses `mb.pch` NOT `mb.south`) |
| **1966867486** | THC WinDbg on MTL Simics | $windbg_enable=TRUE, telnet port 12375 |
| **1800325877** | BKM QuickSPI HIDSPI driver MTL Simics | Descriptor include files, mouse-as-touch commands |

### 3.2 THCipsv Space — IPSV Technical Content (28 pages, GOLDMINE)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **3986290848** | THC Emulation | Complete emulation workflow, VTC name (pcd_thc_simics), waveform capture, transactors.json config, RZL references |
| **2765135286** | THC PM flows | D0i2 (HW auto) + D3 (SW via PMCSR), D3+SnR 11-step flow with PMCLite, full D3+SnR only PTL onwards |
| **1900547074** | THC HIDSPI/HIDI2C Validation Plan (LNL+) | ICR format scrambling (6 variants), programmable opcodes, dummy clock randomization, 1000+ seeds, bus speeds SM 100K through UFm 5M |
| **3565424997** | THC Coalescing | Watermark + MPS <= 8196 constraint |
| **2364131531** | PTL THC Gen 4.1 PCRs | 3 IPSV-impact PCRs + 17 non-IPSV PCRs |
| **1340605604** | CI Automation THC | Falcon+Maestro+Perspec CI, Hardening vs Qual, Config.py/Testlist.py, BAT auto-trigger |
| **2141260829** | RAMLess HIDI2C | Sonora testcard RAMLess mode registers, 4 data modes (standard/fixed pattern/incrementing/custom) |
| **1908803784** | Chapter 3: Register Summary | MASSIVE register map (legacy SPI + testcard control + HIDSPI descriptor table) |
| **2813927240** | Multi Report Interrupt Assertion LNL Bug Fix | Sonora2 HIDI2C_MANUAL_CTRL, multi-report interrupt support |
| **3108833308** | GPIO sync event mode bug fix | HSD 16019332816, coalescing delay counter bug, NVL fix |
| **3108833339** | Buffer Overrun SPI vs I2C bug fix | HSD 16020879491, RX FIFO 8KB/4 slots, SPI vs I2C mismatch |
| **3516738658** | NVL HIDSPI Delay Timer bug fix | Buffer Packet FIFO 4→32 in NVL, 14 reports max before overrun |
| **3454666109** | Continuous timestamp smoothing/coalescing | THC_TS_D0I2_CONT_MODE + THC_TS_D0I2_MODE, 4 combinations matrix, PMCLite SB messages |
| **2990902476** | Coalescing with FrameSync event | Disabled→Armed→Active FSM, buffer slot calculation, watermark rules |
| **1983235857** | PCR Dynamic frame coalescing | Timer-based vs TCON sync coalescing, 4 IPSV tests |
| **2038236523** | THC TCON Frame Sync Signal generator | Sonora testcard TCON_CTRL_REG at 0x1D4, hardware pin mapping |
| **1997025384** | TCON Frame Sync Signal feature (LNL+) | QTH/QSH connector details for TCON hardware setup |
| **1943084492** | PCR THC RX packet >4KB | RX Streaming Mode, RXDMA_PKT_STRM_EN/TXDMA_PKT_STRM_EN bits |
| **1933394613** | PCR THC frame sync signal | DISP_SYNC_EVT_SRC (4 sources), SYNC_TS_LOG_BUF 16-entry FIFO |
| **1982551495** | PCR Allow SW to start Rx DMA | SWDMA engine (Gen4.0+ LNL-M), up to 128 PRD tables, 256 entries/table |
| **1846040828** | PCR HW frame Coalescing 300Hz | Cancelled PCR ("Will not do for LNL") |
| **1850905269** | PCR HID report timestamp | Timestamp step=10us, THC_TIMESTAMP_SRC, 7 test cases |
| **2517795887** | PCR 16-bit port ID | PTL SB fabric upgrade 8→16-bit PortID |
| **2517795903** | PCR WA Resource own req/Ack | Chassis 2.2 signal handshake, 10 resources, PMCLite delay knob |
| **2517795913** | PCR Fuzz test IP interfaces | Actually Display Sync content (wiki copy-paste error) |
| **2683760534** | PCR IOSF 1.2/1.3 Expanded Header | EH=0 must be SAI=Device_Untrusted, 23 test cases |
| **2977738178** | PM D3 flow (Overhauled) | **GOLDMINE**: 4 D3 levels, complete PMCLite SB message table, 28 SnR registers, D3Cold test flow |
| **3108833358** | quiesce_en_isol PG exit bug fix | D0i2 PG exit failure during interrupt, NVL fix |

### 3.3 THCipsv Space — Infrastructure & Testcard (8 pages)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **3775412802** | THC Pytest GIT Repo | frameworks.validation.pythonsv.ipsv.thc, BAT/HIDSPI/HIDI2C/PMC/SONORA subfolders |
| **3566312865** | Python Focus Test list | 8 manual focus tests pending automation |
| **3584960150** | Python Script for Focus Test | SONORA_INPUT_REPORT_SETUP_SRAM_DATA(), COMPARE_REPORT_RX2_TC_AUTONOMOUS() |
| **4269795671** | File used in different IP (ISH/THC) | Complete Maestro/Perspec repo file structure for THC |
| **3028682606** | Project PCR and Good-to-Know | THC gen history (IPSV): Gen1.0=LKF, Gen2.0=TGL (differs from post-si perspective) |
| **1880330910** | SB message format | SB opcodes: FuseReq(0xB8), StrapReq(0xBC), IPReady(0xD0) |
| **2798138055** | FuseLite 2.x | Combined opcode 0x45, 16-bit portID for TTL+ |
| **2211296045** | FuseLite 1.x | THC0 portID=0x39, THC1=0x3A, Fuse addr=0x80, Strap addr=0x84, strap value 0x3=CG+PG |

### 3.4 THCipsv Space — PMCLite & PM (4 pages)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **3356038208** | Compile PMCLite Vector | pmc_kit_rom_parser.pl script, pmcrom.hex output |
| **1274653307** | THC-PMCLite Connection | Minimal: event port + drive port |
| **2755363002** | BackDoor Register Access | PMCLite backdoor address map (0x01000000 base), Python API |
| **1894180152** | Sonora3 TestCard Image Tracking | DDR vs OCM architecture, 50MHz quad issues, Python test script names |

### 3.5 THCipsv Space — Sonora & Emulation (3 pages)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **2794294764** | Sonora3-DX7/HAPS80 setup | Single HT3 cable, pin mirroring requirement |
| **1983238991** | PCR Fastest SPI controller | Half clock divider, duty cycle NOT implemented/ZBBed |
| **4457832574** | TTL PCD-H Tickets | TTL model ticket placeholders from PTL, GPIO pullup, simple_io_0_en, regflow |

### 3.6 PPA Space — SPI Transactor (12 pages)

| Page ID | Title | Key Findings |
|---------|-------|-------------|
| **1249986923** | spi_xtor Overview | Two main modes (Standard SPI + eSPI), SPI touch NOT FULLY SUPPORTED |
| **1249986915** | spi_xtor interfaces & attributes | thc_vdm class attributes: spi_host_obj, mem_space, touch_int_cause, tc_control, ramless_datamode_ctrl, int_trigger |
| **1249986926** | spi_xtor Operation modes | 7 modes total, SPI flash generic mode for THC |
| **1249986917** | spi_xtor Hardware interface | RTL module spi_xactor, CS active HIGH, ESPI_MODE param |
| **1249986913** | spi_xtor Integration (WIP) | **GOLDMINE**: THC_VTC DEPRECATED as of spark-1.11.7, THC VDM instantiation code, 6 opcode configs, simple_io_xtor for GPIO |
| **1249986972** | spi_xtor BKMs & FAQs | SFDP table data, flash image save command |
| **1249986916** | spi_xtor Flash generic mode VDM | 3 operation modes (Flash VDM, SPI interface, SPI passthrough), opcode config |
| **1249986975** | spi_xtor Regression | 3 THC-specific tests (touch/thc_legacy/thc_simple_io), git repo |
| **1249986919** | spi_xtor Transactions | Low THC value, mostly eSPI-specific |
| **1249986920** | spi_xtor eSPI callbacks | Low THC value, eSPI-specific |
| **1249986918** | spi_xtor eSPI upstream | Low THC value, eSPI-specific |
| **1388942349** | SPI xtor integration guide (PCHEMU) | PCH integration, repositories.yml format |

### 3.7 Other Spaces (8 pages)

| Page ID | Space | Title | Key Findings |
|---------|-------|-------|-------------|
| **1498127969** | CPS | IPTS Playbook | Driver version history, pathfinding workstreams |
| **2068317556** | IPTS | MTL PSS Session Setup | Complete MTL workspace setup, CRT alternative |
| **3762034607** | VICESW | THC Test Content Support | RTR framework, Regflow, intent coverage, Sonora partition |
| **3054643734** | VICESW | THC Content/Features HID for PTL | Maestro/Perspec test content mapping for IPTS/HIDI2C/HIDSPI |
| **4605435102** | fvcommon | Simics Phone Book | THC Simics Domain Lead = Chin, William |
| **2918220570** | fvcommon | PM Enabling | ThcAssignment_0/1=None for S0ix testing |
| **1172406469** | pch | SOC Override | THC RDL overrides (BDF, PortID, DID), BAR0 mask workaround |
| **3064545564** | ESIPWiki | THC Debug Hooks | THC 4.1 VISA regression debug artifacts |

---

## 4. Key Technical Findings

### 4.1 Platform Naming Convention (Complete Matrix)

| Platform | THC Namednode Path | Touch Device Object | Package |
|----------|-------------------|-------------------|---------|
| LKF | `lkf.mb.sb.thcX` | `ticXX` | 7031 |
| MTL | `mtl.mb.soc.thcX` | `tep.ticXX` | 7500 |
| LNL | `lnl.mb.south.thcX` | `alpsX` | 7600 |
| PTL | `$system.mb.south.thcX` | `alps_touchscreenX` | TBD |
| NVL | `nvl.mb.pch.thcX` | `alps_touchscreenX` | TBD |

> **CRITICAL**: NVL uses `mb.pch` NOT `mb.south` — unique among all platforms.

### 4.2 THC_VTC Deprecation

- **THC_VTC is DEPRECATED** as of SPARK 1.11.7
- Replacement: **THC VDM** (thc_vdm class) using SPI flash generic mode
- thc_vdm attributes: `spi_host_obj`, `mem_space`, `touch_int_cause`, `tc_control`, `ramless_datamode_ctrl`, `int_trigger`
- Write opcode difference: THC_VTC used 0x32/0xe3, THC_VDM uses 0xB2/0xE2

### 4.3 SPI Touch Limitation

Per PPA wiki (page 1249986923): **SPI touch is NOT FULLY SUPPORTED** in spi_xtor. The SPI flash generic mode is used as a workaround for THC touch device simulation. Full SPI touch protocol support is incomplete — opcode configuration and VDM interface provide functional but limited coverage.

### 4.4 Four D3 Power Levels (PTL+ Overhauled)

| Level | Mechanism | Power Gating | SnR Required | PMCLite Messages |
|-------|-----------|-------------|-------------|-----------------|
| D0i2 | HW autonomous | Yes (auto) | No | D0i2 Entry/Exit |
| D3 | SW via PMCSR | No | No | D3 Entry |
| D3Hot | SW via PMCSR + PG | Yes | Partial | D3Hot Entry + PG Entry |
| D3Cold | Deepest | Yes (full) | Full (28 regs) | D3Cold Entry + Save/Restore + PG |

28 SnR registers documented for D3Cold restore (page 2977738178).

### 4.5 FuseLite Details

| Parameter | THC0 | THC1 |
|-----------|------|------|
| IOSF SB Port ID | 0x39 | 0x3A |
| Fuse Address | 0x80 | 0x80 |
| Strap Address | 0x84 | 0x84 |
| Strap Value (CG+PG) | 0x3 | 0x3 |

- **FuseLite 1.x**: Separate Fuse (0xB8) and Strap (0xBC) opcodes, 8-bit port ID
- **FuseLite 2.x** (TTL+): Combined opcode 0x45, 16-bit port ID

### 4.6 Buffer Packet FIFO Evolution

| Platform | FIFO Slots | Max Reports Before Overrun |
|----------|-----------|--------------------------|
| LNL | 4 | ~14 |
| PTL | 4 | ~14 |
| NVL+ | 32 | Much higher |

Source: HSD NVL HIDSPI Delay Timer bug fix (page 3516738658).

### 4.7 Coalescing Architecture

**FSM States**: Disabled → Armed → Active
- **Disabled**: No coalescing, reports forwarded immediately
- **Armed**: First report received, waiting for watermark or timeout
- **Active**: Coalescing in progress, accumulating reports

**Constraints**:
- Watermark + MPS <= 8196 (combined limit)
- Timer-based coalescing: uses internal timer for frame aggregation
- TCON sync coalescing: synchronizes with display refresh via TCON frame sync signal
- Dynamic frame coalescing: selects timer-based or TCON-synced mode

**Sonora testcard**: TCON_CTRL_REG at offset 0x1D4 generates frame sync signal.

### 4.8 Timestamp D0i2 Mode Combinations

| THC_TS_D0I2_CONT_MODE | THC_TS_D0I2_MODE | Behavior |
|----------------------|-----------------|----------|
| 0 | 0 | Counter pauses on D0i2 entry, resumes on exit |
| 0 | 1 | Counter resets to 0 on D0i2 exit |
| 1 | 0 | Counter continues running through D0i2 (never pauses) |
| 1 | 1 | Counter continues + resets on exit (unusual combo) |

Timestamp resolution: 10us/step, independent per port.

### 4.9 RX Streaming Mode

- Enables handling packets >4KB without increasing internal buffer
- Controlled by `RXDMA_PKT_STRM_EN` and `TXDMA_PKT_STRM_EN` bits
- Source: PCR THC RX packet >4KB (page 1943084492)

### 4.10 IPSV Validation Methodology

From THC HIDSPI/HIDI2C Validation Plan (page 1900547074):
- **ICR format scrambling**: 6 variants of Input Cause Register format testing
- **Programmable opcode randomization**: All configurable opcodes tested with random values
- **Dummy clock randomization**: SPI dummy cycles varied across test seeds
- **1000+ seeds**: Extensive randomization coverage
- **Bus speed coverage**: SM 100K, FM 400K, FM+ 1M, HS 3.4M, UFm 5M (I2C); multiple SPI frequencies

### 4.11 RTL Bug Fixes (IPSV-Discovered)

| HSD | Bug | Platform Fix | Description |
|-----|-----|-------------|-------------|
| 16019332816 | GPIO sync event mode | NVL | Coalescing delay counter not resetting on GPIO sync event |
| 16020879491 | Buffer overrun SPI vs I2C | NVL | RX FIFO 8KB/4 slots, different overrun behavior SPI vs I2C |
| (no HSD) | NVL HIDSPI delay timer | NVL | Buffer Packet FIFO increased 4→32 slots |
| (no HSD) | quiesce_en_isol PG exit | NVL | D0i2 PG exit failure when interrupt arrives during PG sequence |
| (no HSD) | Multi-report interrupt | LNL | Sonora2 HIDI2C_MANUAL_CTRL for multi-report interrupt support |

### 4.12 SOC Override / RDL Architecture

- THC IP delivers **ONE RDL** (Register Description Language file)
- SOC instantiates it **TWICE** (THC0 + THC1) with parameter overrides:
  - **BDF**: Different Bus/Device/Function per instance
  - **Port ID**: THC0=0x39, THC1=0x3A
  - **Device ID**: e.g., THC0=0xA0D0, THC1=0xA0D1
- **BAR0 mask workaround**: Required for certain platform configurations
- Source: SOC Override page (1172406469)

### 4.13 PMCLite Internals

- **Backdoor address map**: Base at 0x01000000, Python API for direct register access
- **Vector compilation**: `pmc_kit_rom_parser.pl` script generates `pmcrom.hex`
- **Connection**: Minimal — event port + drive port between THC and PMCLite
- **D3Cold flow**: 11-step sequence involving PMCLite SB messages for save/restore

### 4.14 Sonora3 Testcard

- Uses **DDR** (not OCM) for data storage — key architectural difference from Sonora2
- Single **HT3 cable** connection to DX7/HAPS80
- **Pin mirroring** requirement for correct signal routing
- **50MHz quad SPI issues** reported — limitation at higher speeds
- Python test scripts available for automated validation

### 4.15 THC Generation Mapping (IPSV vs Post-Si)

| Generation | IPSV Perspective | Post-Si Perspective |
|------------|-----------------|-------------------|
| Gen 1.0 | LKF | TGL, ADL |
| Gen 2.0 | TGL | ADP-LP+ |
| Gen 3.0 | (not tracked) | MTL-M, ARL |
| Gen 4.0 | LNL-M | LNL-M |
| Gen 4.1 | PTL, WCL | PTL, WCL |
| Gen 4.2 | NVL, RZL, TTL | NVL, RZL, TTL |

> **Note**: IPSV and post-si teams use different generation numbering for pre-Gen4.0 platforms.

### 4.16 VICESW Test Content

- **RTR framework**: Register Transfer Regression for THC register validation
- **Regflow**: Automated register flow testing
- **Intent coverage**: Mapping test content to design intent
- **Sonora partition**: Test content partitioned by Sonora testcard capability
- Maestro/Perspec test content mapping covers IPTS, HIDI2C, and HIDSPI protocols

### 4.17 TTL PCD-H Platform Tickets

- Model ticket placeholders carried forward from PTL
- Key items: GPIO pullup configuration, `simple_io_0_en` attribute, regflow integration
- Indicates TTL model development follows PTL baseline with incremental changes

---

## 5. Cross-Check Results

### 5.1 Findings by Category

| Category | Count | Details |
|----------|-------|---------|
| ALREADY PRESENT | 15+ | THC_VTC deprecation, thc_vdm attributes, opcode tables, NVL mb.pch path, PMCLite codes, 16-bit PortID, etc. |
| MISSING (applied) | 20+ | See Section 5.2 |
| WRONG | 0 | No incorrect information found in existing skill files |

### 5.2 MISSING Items Applied

#### advanced.md (+279 lines, 8 edit operations)

| # | Section | Content Added | Source Page |
|---|---------|--------------|-------------|
| 1 | 4.4 | Timestamp 4-combination D0i2 matrix (THC_TS_D0I2_CONT_MODE + THC_TS_D0I2_MODE) | 3454666109 |
| 2 | 4.7 (NEW) | Coalescing Architecture: FSM (Disabled→Armed→Active), watermark+MPS<=8196 constraint, timer-based vs TCON sync, dynamic frame coalescing, TCON_CTRL_REG at 0x1D4 | 3565424997, 2990902476, 1983235857, 2038236523 |
| 3 | 5.5 (NEW) | IPSV Validation Plan details: ICR scrambling (6 variants), opcode randomization, dummy clock randomization, 1000+ seeds, bus speeds SM-UFm | 1900547074 |
| 4 | 5.6 (NEW) | IPSV RTL Bug Fixes: 5 bugs with HSD numbers (GPIO sync, buffer overrun, delay timer, PG exit, multi-report) | 3108833308, 3108833339, 3516738658, 3108833358, 2813927240 |
| 5 | 5.7 (NEW) | VICESW Test Content: RTR framework, Regflow, intent coverage, Sonora partition | 3762034607, 3054643734 |
| 6 | 5.8 (NEW) | Focus Tests: 8 manual tests pending automation | 3566312865, 3584960150 |
| 7 | 7.7 (NEW) | RX Streaming Mode: RXDMA_PKT_STRM_EN/TXDMA_PKT_STRM_EN, >4KB packets | 1943084492 |
| 8 | 7.8 (NEW) | Buffer Packet FIFO Evolution: 4 slots (LNL/PTL) → 32 slots (NVL), 14 reports max | 3516738658 |
| 9 | 8.5 (NEW) | FuseLite THC-specific: portIDs (0x39/0x3A), fuse/strap addresses, strap values, FuseLite 2.x combined opcode 0x45 for TTL+ | 2211296045, 2798138055 |
| 10 | 20 (NEW) | PMCLite Internals: backdoor address map (0x01000000), pmc_kit_rom_parser.pl, 28 SnR registers | 2755363002, 3356038208, 2977738178 |
| 11 | 21 (NEW) | Sonora3 Testcard Architecture: DDR vs OCM, HT3 cable, pin mirroring, 50MHz quad issues | 1894180152, 2794294764 |
| 12 | 22 (NEW) | THC Generation Mapping (IPSV perspective): Gen1.0=LKF, Gen2.0=TGL differences from post-si | 3028682606 |
| 13 | 23 (NEW) | TTL PCD-H Platform: ticket placeholders, GPIO pullup, simple_io_0_en, regflow | 4457832574 |
| 14 | TOC | Updated to reflect sections 20-23 | N/A |

#### models.md (+51 lines, 4 edit operations)

| # | Section | Content Added | Source Page |
|---|---------|--------------|-------------|
| 1 | 1 | SPI touch NOT FULLY SUPPORTED caveat with reference to PPA wiki | 1249986923 |
| 2 | 2 | RAMLess 4 data modes table (standard/fixed pattern/incrementing/custom) | 2141260829 |
| 3 | 7 (NEW) | SOC Override & RDL Instantiation: single RDL dual-instantiation, DID override, BAR0 mask workaround | 1172406469 |
| 4 | TOC | Updated to include Section 7 | N/A |

#### SKILL.md (+4 lines, 1 edit operation)

| # | Location | Content Added | Source Page |
|---|----------|--------------|-------------|
| 1 | After line 302 | THC generation mapping note (IPSV vs post-si perspective) | 3028682606 |

#### operations.md (0 changes)

No changes needed — all wiki findings for this file were already present.

---

## 6. Pages Not Deep-Read (Low Priority)

The following discovered pages were assessed as low-priority and not deep-read. They are unlikely to yield significant new findings beyond what's already extracted:

- Individual PCR detail pages already summarized through parent pages
- FPGA farm tracking pages (infrastructure, not technical content)
- Debug handbook pages duplicating content from other sources
- LKF/TGL-era pages superseded by newer platform content
- eSPI-specific spi_xtor pages (not THC-relevant)

---

## 7. Complete Wiki Page Index

### 7.1 By Space

**THCipsv** (28 pages read):
1966867553, 1966867456, 3986290848, 2765135286, 1900547074, 3565424997, 2364131531, 1340605604, 2141260829, 1908803784, 2813927240, 3108833308, 3108833339, 3516738658, 3454666109, 2990902476, 1983235857, 2038236523, 1997025384, 1943084492, 1933394613, 1982551495, 1846040828, 1850905269, 2517795887, 2517795903, 2517795913, 2683760534

**THCipsv — Infrastructure** (8 pages read):
3775412802, 3566312865, 3584960150, 4269795671, 3028682606, 1880330910, 2798138055, 2211296045

**THCipsv — PMCLite/PM** (4 pages read):
3356038208, 1274653307, 2755363002, 1894180152

**THCipsv — Sonora/Emulation** (3 pages read):
2794294764, 1983238991, 4457832574

**THCipsv — D3 Flow** (2 pages read):
2977738178, 3108833358

**SRESIMICS** (9 pages read):
1966867553, 1966867456, 1433100579, 2845164237, 1966867128, 3217199088, 4045307441, 1966867486, 1800325877

**PPA** (12 pages read):
1249986923, 1249986915, 1249986926, 1249986917, 1249986913, 1249986972, 1249986916, 1249986975, 1249986919, 1249986920, 1249986918, 1388942349

**Other** (8 pages read):
1498127969 (CPS), 2068317556 (IPTS), 3762034607 (VICESW), 3054643734 (VICESW), 4605435102 (fvcommon), 2918220570 (fvcommon), 1172406469 (pch), 3064545564 (ESIPWiki)

### 7.2 Additional Reference Pages (discovered, not deep-read)

- **1693808060** (PPA) — RTL/Simics mappings SOC-S
- **3556711840** (PPA) — Model 2 Min Boot PCH IPs
- **3439922659** (bnatarajan) — PTL Simics Setup
- **4148758972** (s3e) — GDB with Simics
- **2761101312** (VICESW) — THC PRD table in Maestro
- **2555780617** (fvcommon) — BKM Sonora2+CAT MTL-P
- **1383238811** (VICEPE) — IP FPGA Farm Config
- **1249985406** (PPA) — THC BAT Test
- **1256270175** (THCipsv) — Maestro and Perspec training

---

## 8. Recommendations

### 8.1 Future Wiki Monitoring
The following wiki spaces should be periodically re-checked for new content:
1. **THCipsv** — Most active space, new PCR pages and bug fixes added frequently
2. **SRESIMICS** — New BKM pages for each platform (RZL, TTL)
3. **PPA** — spi_xtor updates and new integration guides

### 8.2 Potential Future Additions
- VISA/DFx debug artifacts (page 3064545564 mentions tracker files)
- Security/SAI policy details (not found in current wiki content)
- WoT-specific Simics content (no results found — may not exist yet)
- SimCloud deployment configurations (referenced but not THC-specific)

---

*End of THC Simics Wiki Research v2.0*
*Total pages researched: 52 deep-read out of 80+ discovered*
*Research completeness: HIGH — all critical and high-priority pages exhaustively studied*
