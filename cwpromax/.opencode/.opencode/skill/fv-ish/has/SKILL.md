# FV-ISH HAS Skill — ISH Hardware Architecture Specification Repository

> **Skill**: `fv-ish/has`
> **Owner**: Leem, Yi Jie (`yleem`) — yi.jie.leem@intel.com
> **Team**: CVE - ISH Validation
> **Last Updated**: 2026-03-16 (rev2.0)
> **Purpose**: Centralized ISH HAS document management, local search, and Co-De Sign live query integration

---

## Skill Identity

You are the ISH HAS (Hardware Architecture Specification) knowledge skill. You provide the **primary source of truth** for all ISH IP architecture questions — register maps, protocol specifications, DMA descriptors, power state definitions, and firmware interface details.

**This skill should be loaded FIRST before answering any hardware architecture question.** Other sub-skills (registers, heci, dma, power, etc.) defer to this skill for authoritative hardware details.

---

## CRITICAL — HAS-First Policy

- **ALWAYS** search local HAS documents or query Co-De Sign before providing register offsets, bit field definitions, IPC protocol details, DMA descriptor formats, or firmware interface specifications.
- If you **cannot find the answer** in local HAS docs or Co-De Sign, say: "I could not verify this against the ISH HAS. The following is based on general knowledge and may be inaccurate — please verify against the HAS before use."
- **NEVER** fabricate register addresses, bit field definitions, or protocol details. If unsure, say so and direct the user to the HAS.

---

## Document Index

| Platform | HAS Document | Local Path | Co-De Sign Workspace | Status |
|----------|-------------|------------|----------------------|--------|
| **TTL** | ISH 5.9 HAS (Titan Lake) | `docs/ttl/` | `SIP_ISH5p9_HAS.html` | **HAS-VERIFIED** — 10 reference docs + 2 OSXML register PDFs |
| **NVL** | ISH NVL HAS (Nova Lake) | `docs/nvl/` | `SIP_ISH5p8_HAS` | **PRIMARY FOCUS** — HAS available locally |
| MTL | ISH MTL HAS (Meteor Lake) | `docs/mtl/` | [TODO: workspace_id] | TODO |
| LNL | ISH LNL HAS (Lunar Lake) | `docs/lnl/` | [TODO: workspace_id] | TODO |
| PTL | ISH PTL HAS (Panther Lake) | `docs/ptl/` | [TODO: workspace_id] | TODO |
| ARL | ISH ARL HAS (Arrow Lake) | `docs/arl/` | [TODO: workspace_id] | TODO |

> **To add a new HAS document**: Place the file in the appropriate `docs/<platform>/` folder and update the `README.md` in that folder with document metadata. See [Adding New Documents](#adding-new-documents) below.

---

## TTL HAS — Verified Reference Data (ISH 5.9)

The TTL (Titan Lake) ISH 5.9 data has been extracted from Co-De Sign HAS documents and OSXML register PDFs. This is the most complete reference available and serves as the architectural baseline for ISH 5.9.

### TTL Document Inventory

See `docs/ttl/README.md` for full inventory. Key documents:

| Document | Source | Content |
|----------|--------|---------|
| `TTL_ISH_Architecture_Overview.md` | Co-De Sign | Block diagram, LMT core, IO controllers, IOSF |
| `TTL_ISH_Register_Map.md` | Co-De Sign | MMIO offsets, bit fields, timer registers |
| `TTL_ISH_HECI_IPC_Protocol.md` | Co-De Sign | IPC doorbell/mailbox, channels, command opcodes |
| `TTL_ISH_Sensor_Framework.md` | Co-De Sign | Sensor types, interfaces, virtual sensors, wake events |
| `TTL_ISH_DMA_Architecture.md` | Co-De Sign | DMA channels, transfer modes |
| `TTL_ISH_Power_Management.md` | Co-De Sign | D-states, SRAM gating, PMC sideband, S0ix |
| `TTL_ISH_BIOS_Requirements.md` | Co-De Sign | ACPI, init sequence, BAR config, GPIO muxing |
| `TTL_ISH_Firmware_Boot_Flow.md` | Co-De Sign | Boot ROM, BUP/main FW, CSE, S3 resume |
| `TTL_ISH_Register_Reference.md` | OSXML PDF | HOST wrapper: PCI config, 8 IPC channels, bit fields |
| `TTL_ISH_MIA_Register_Reference.md` | OSXML PDF | MIA internal: PMU, CCU, GPIO, I2C, I3C, SPI, UART, DMA, SRAM, WDT, Fabric |

### TTL Quick Reference

| Property | Value |
|----------|-------|
| **ISH Generation** | ISH 5.9 (SIP_ISH5p9) |
| **CPU Core** | LMT 3.8/3.9 (MinuteIA) |
| **PCI Device ID** | `0xE445` |
| **PCI Vendor ID** | `0x8086` |
| **Memory** | 8KB ROM + 640KB SRAM (20×32KB banks) + 8KB AON RF SRAM |
| **Clocking** | 200/100 MHz |
| **I2C** | 3 instances, 1 Mb/s (DW_apb_i2c) |
| **I3C** | 2 instances, 25 Mb/s HDR-DDR (HCI v1.0) |
| **SPI** | 2 instances, 25 Mb/s (DW_apb_ssi) |
| **UART** | 3 instances, 4 Mb/s (DW_apb_uart) |
| **GPIO** | Up to 12 pins |
| **Host Interface** | IOSF (IPC doorbell/mailbox, NOT PCIe) |
| **IPC Channels** | 8: HOST, HOSTSPARE, CSE, PMC, CNVi, ACE, ESE, AVB |
| **Power States** | D0, D0i1, D0i2, D0i3, D3 with per-bank SRAM gating |
| **Power Domain** | VNNAON (always-on), Reset: FUNCRST |
| **PMC Sideband** | Opcode 0x6Fh, Tag 0x06h |
| **DMA** | 8 channels, 4 transfer modes, RS0/RS3 root-space |
| **Watchdog** | Two-stage (T1→interrupt, T2→reset), default 0xA0A0 |

---

## Directory Structure

```
.opencode/skill/fv-ish/has/
├── SKILL.md                        ← This file (skill instructions)
├── scripts/
│   └── has_search.py               ← Advanced HAS document search utility
├── docs/
│   ├── ttl/                        ← Titan Lake HAS (HAS-VERIFIED)
│   │   ├── README.md               ← Document index and metadata
│   │   ├── TTL_ISH_Architecture_Overview.md
│   │   ├── TTL_ISH_Register_Map.md
│   │   ├── TTL_ISH_HECI_IPC_Protocol.md
│   │   ├── TTL_ISH_Sensor_Framework.md
│   │   ├── TTL_ISH_DMA_Architecture.md
│   │   ├── TTL_ISH_Power_Management.md
│   │   ├── TTL_ISH_BIOS_Requirements.md
│   │   ├── TTL_ISH_Firmware_Boot_Flow.md
│   │   ├── TTL_ISH_Register_Reference.md     ← From ish_wrapper_host.pdf
│   │   ├── TTL_ISH_MIA_Register_Reference.md ← From ish_mia_bfm_rdl_top.pdf
│   │   ├── ish_wrapper_host_raw.txt          ← Raw extracted text (39,588 lines)
│   │   └── ish_mia_bfm_rdl_top_raw.txt      ← Raw extracted text (80,645 lines)
│   ├── nvl/                        ← Nova Lake HAS (PRIMARY FOCUS)
│   │   ├── README.md               ← Document index and metadata
│   │   ├── NVL_ISH_Architecture_Overview.md
│   │   ├── NVL_ISH_Power_Management.md
│   │   ├── NVL_ISH_IPC_Protocol.md
│   │   └── NVL_ISH_DMA_FW_Boot.md
│   ├── mtl/                        ← Meteor Lake HAS
│   │   └── README.md
│   ├── lnl/                        ← Lunar Lake HAS
│   │   └── README.md
│   ├── ptl/                        ← Panther Lake HAS
│   │   └── README.md
│   └── arl/                        ← Arrow Lake HAS
│       └── README.md
```

---

## HAS Query Workflow

When the user asks about ISH registers, protocols, power states, DMA, or any hardware-level detail:

```
1. Load this skill (fv-ish/has)
        ↓
2. Check local HAS docs — TTL docs are comprehensive, check docs/ttl/ first
   (grep search in docs/<platform>/)
        ↓ Found? → Provide answer with source reference
        ↓ Not found?
3. Query Co-De Sign (browsermcp → https://chat.co-design.intel.com/chat)
        ↓ Found? → Provide answer, optionally save locally
        ↓ Not found?
4. Use has_search.py for advanced cross-format search
        ↓ Found? → Provide answer
        ↓ Still not found?
5. Inform user: cannot verify against HAS, provide best-effort answer with disclaimer
```

### TTL-Specific Search Tips

For TTL ISH 5.9 questions, search these files in order:
1. `TTL_ISH_MIA_Register_Reference.md` — Most detailed register data (PMU, CCU, GPIO, I2C, I3C, SPI, UART, DMA, SRAM, WDT)
2. `TTL_ISH_Register_Reference.md` — HOST wrapper registers (PCI config, IPC channels, doorbell)
3. The Co-De Sign extracted `.md` files — Architecture overview, protocol descriptions, boot flow
4. Raw text files (`*_raw.txt`) — For deep searches of specific register names or bit fields not in summaries

---

## Method 1 — Local HAS Document Search

### Quick Search (grep)

Use the `grep` tool to search across all HAS documents:

```bash
# Search for a keyword in TTL HAS docs (most complete)
grep -r "SRAM_PG_EN" .opencode/skill/fv-ish/has/docs/ttl/

# Search for a register in MIA reference
grep -r "0x04200000" .opencode/skill/fv-ish/has/docs/ttl/TTL_ISH_MIA_Register_Reference.md

# Search across all platforms
grep -r "DMA descriptor" .opencode/skill/fv-ish/has/docs/

# Search raw extracted text for deep register details
grep -i "WAKE_EVENT" .opencode/skill/fv-ish/has/docs/ttl/ish_mia_bfm_rdl_top_raw.txt

# Search for power management content
grep -ri "D0i3\|D0i2\|runtime pm" .opencode/skill/fv-ish/has/docs/ttl/
```

### Advanced Search (has_search.py)

Use `scripts/has_search.py` for structured, multi-format search:

```bash
# Search for a specific register
python .opencode/skill/fv-ish/has/scripts/has_search.py --query "ISH firmware status register" --platform ttl

# Extract all register definitions
python .opencode/skill/fv-ish/has/scripts/has_search.py --type registers --platform ttl

# List all available documents
python .opencode/skill/fv-ish/has/scripts/has_search.py --list-docs
```

---

## Method 2 — Co-De Sign Live Query

Use browser tools to query the ISH HAS via Intel Co-De Sign when local docs are unavailable or incomplete.

### Step-by-Step

```
1. Navigate to: https://chat.co-design.intel.com/chat
2. Wait for SSO auto-authentication (15-30 seconds)
3. Select the appropriate workspace for ISH HAS
4. Type your query into the chat textbox → Press Enter
5. Wait 15-25 seconds for response
6. Read the response from the page snapshot
7. (Optional) Save the response to docs/<platform>/ for future offline access
```

### Known Co-De Sign Documents

The user's Co-De Sign workspace contains:
- `iparch/ish/HW/ISH5p9/HAS/SIP_ISH5p9_HAS.html` — ISH 5.9 HAS (primary)
- `iparch/ish/fas/BIOS/ISH Requirement to BIOS.html` — ISH BIOS requirements

### Query Templates

| Topic | Query Template |
|-------|---------------|
| Register map | `What are the ISH [component] register offsets and bit field definitions?` |
| Register detail | `Describe the bit fields of the [REGISTER_NAME] register in the ISH HAS` |
| IPC protocol | `Describe the ISH IPC [doorbell / mailbox / channel] protocol` |
| DMA | `What is the ISH DMA descriptor format? Include all fields and bit definitions.` |
| Power states | `What are the ISH D-state definitions and transition conditions?` |
| Sensor interface | `How does the ISH sensor interface work? What I2C/I3C/SPI controllers are available?` |
| Firmware interface | `Describe the ISH firmware loading protocol — Boot ROM, BUP, main FW` |

### Co-De Sign API (Programmatic)

Load `codesign` skill for API access via `codesign_api.py`:
```
URL:     https://chat.co-design.intel.com/llm/ask_stream
Method:  POST
Auth:    SSO cookie or API key (see codesign skill)
Body:    {
           "query": "<your question>",
           "agent_type": "spec",
           "conversation_id": "<uuid>",
           "workspace_id": "<ISH workspace_id>"
         }
```

---

## Adding New Documents

### Step 1 — Download from Co-De Sign or SharePoint
1. Navigate to Co-De Sign or SharePoint ISH site
2. Download as HTML (preferred), PDF, or Markdown
3. For OSXML register PDFs: download from `intel.sharepoint.com/sites/IPDevISH/.../OSXML/`
4. Use `pdftotext` to extract text: `"C:\Program Files\Git\mingw64\bin\pdftotext.exe" -layout input.pdf output.txt`

### Step 2 — Place in Correct Directory
```
docs/<platform>/ish_<platform>_<topic>.<format>

Examples:
  docs/ttl/TTL_ISH_Architecture_Overview.md
  docs/nvl/ish_nvl_has.html
  docs/nvl/ish_nvl_register_map.pdf
```

### Step 3 — Update README.md
Open `docs/<platform>/README.md` and add an entry to the document table.

### Step 4 — Update Document Index Table
Update the **Document Index** table at the top of this file with the new document's status.

---

## NVL HAS — Primary Reference Content

> **Status**: Awaiting HAS document placement in `docs/nvl/`
> **Action Required**: Place ISH NVL HAS file(s) in `.opencode/skill/fv-ish/has/docs/nvl/` and update `docs/nvl/README.md`
>
> **Note**: Until NVL HAS is available locally, TTL (ISH 5.9) data in `docs/ttl/` provides the closest architectural reference. ISH 5.9 is common across TTL and likely NVL — verify Device ID and platform-specific deltas.

### NVL Quick Reference
| Property | Value |
|----------|-------|
| **ISH Generation** | ISH 5.8 (SIP_ISH5p8) |
| **CPU Core** | LMT 3.9 (MinuteIA) |
| **PCI Device ID** | `0x6E78` |
| **PCI Vendor ID** | `0x8086` |
| **Memory** | 8KB ROM + 640KB SRAM (20×32KB banks) + 8KB AON RF SRAM |
| **Clocking** | 200/100 MHz |
| **I2C** | 3 instances, 1 Mb/s (DW_apb_i2c) |
| **I3C** | 1 instance, 25 Mb/s HDR/DDR (HCI v1.0) |
| **SPI** | 1 instance, 25 Mb/s (DW_apb_ssi) |
| **UART** | 2 instances, 4 Mb/s (DW_apb_uart) |
| **GPIO** | 8-12 pins (PCH-S=12) |
| **IPC Channels** | 8: HOST, HOSTSPARE, CSE, PMC, CNVi, ACE, ESE, AVB |
| **Power States** | D0, D0i1, D0i2, D0i3, D3 with per-bank SRAM gating |
| **PMC Sideband** | Opcode 0x6Fh, Tag 0x06h |
| **DMA** | 8 channels, 4 transfer modes, RS0/RS3 root-space |
| **Watchdog** | Two-stage (T1→interrupt, T2→reset), default 0xA0A0 |

### NVL vs TTL — Expected Differences
> [TODO: Document NVL-specific ISH changes vs TTL after NVL HAS review]
> Key items to verify: PCI Device ID, SRAM bank count, sensor BOM, ACPI device path

---

## Supported Document Formats

| Format | Notes |
|--------|-------|
| `.html` | Preferred — Co-De Sign exports, richest structure for table parsing |
| `.pdf`  | Supported — extract with `pdftotext` for searchability |
| `.md`   | Supported — manually converted or extracted content |
| `.txt`  | Supported — raw extracted text from PDFs |

---

## Integration with Other Sub-Skills

When other FV-ISH sub-skills need hardware-authoritative information, they load this skill first:

| Sub-Skill | Queries This HAS Skill For |
|-----------|---------------------------|
| `fv-ish/registers` | Register offsets, bit fields, reset values, address maps |
| `fv-ish/heci` | IPC doorbell protocol, message registers, channel configuration |
| `fv-ish/sensors` | Sensor bus controllers (I2C/I3C/SPI/UART/GPIO), supported types |
| `fv-ish/dma` | DMA channel registers, transfer modes, root-space selection |
| `fv-ish/power` | PMU/CCU registers, D-state definitions, SRAM gating, wake events |
| `fv-ish/driver` | Firmware boot flow, WDT, CSE interaction, S3 resume |
| `fv-ish/platform` | Platform-specific Device IDs, BDFs, memory map, BOM matrix |
| `fv-ish/debug` | Expected register values, error code definitions, FWSTS decoding |

---

## Quick Reference — Common HAS Queries

| What You Need | Local Search (TTL) |
|---------------|--------------------|
| ISH PCI Device ID | `grep "Device ID\|0xE445" docs/ttl/TTL_ISH_Register_Reference.md` |
| IPC doorbell registers | `grep "INBOUND_DB\|OUTBOUND_DB\|BUSY" docs/ttl/TTL_ISH_Register_Reference.md` |
| PMU SRAM power gating | `grep "SRAM_PG_EN\|PMU" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| Wake event sources | `grep "WAKE_EVENT" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| DMA channel control | `grep "DMA_CTL\|XFER_MODE" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| I2C register base | `grep "I2C.*0x0000" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| I3C HCI registers | `grep "I3C\|HCI" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| WDT configuration | `grep "WDT\|watchdog" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| SRAM controller | `grep "SRAM_CFGR\|SRAM_LIMIT" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| CCU clock gating | `grep "TRUNK_CG\|CCU" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
| Firmware status | `grep "FWSTS\|FW_STATUS" docs/ttl/TTL_ISH_Register_Reference.md` |
| GPIO configuration | `grep "GPLR\|GPDR\|GPIO" docs/ttl/TTL_ISH_MIA_Register_Reference.md` |
