# FV-USB Self-Improvement Content Assertions
# Domain: USB Functional Validation
# Owner: kvejaya
# Version: 1.0.0
#
# Assertion types:
#   ("contains",     skill, regex, desc)          -- PASS if regex matches skill content
#   ("not_contains", skill, regex, desc)           -- PASS if regex does NOT match
#   ("value_match",  skill, field_regex, expected, desc) -- find field, check nearby value
#
# Skill names map to .opencode/skill/fv-usb/<skill>/SKILL.md
# Use "root" for .opencode/skill/fv-usb/SKILL.md
# Use "agent" for .opencode/agent/FV/FV-USB.md

EVAL_TESTS = {

    # ─── ROOT SKILL ──────────────────────────────────────────────────────────

    "ROOT-001": {
        "name": "Root skill has owner tag",
        "assertions": [
            ("contains", "root", r"kvejaya", "owner IDSID present"),
            ("contains", "root", r"kvejaya|kalaivanan", "owner identity present"),
        ]
    },
    "ROOT-002": {
        "name": "Root skill declares target platforms",
        "assertions": [
            ("contains", "root", r"NVL|Nova\s*Lake", "NVL platform listed"),
            ("contains", "root", r"PTL|Panther\s*Lake", "PTL platform listed"),
            ("contains", "root", r"LNL|Lunar\s*Lake", "LNL platform listed"),
            ("contains", "root", r"MTL|Meteor\s*Lake", "MTL platform listed"),
            ("contains", "root", r"ARL|Arrow\s*Lake", "ARL platform listed"),
        ]
    },
    "ROOT-003": {
        "name": "Root skill lists all four sub-skills",
        "assertions": [
            ("contains", "root", r"enumeration", "enumeration sub-skill listed"),
            ("contains", "root", r"xhci", "xhci sub-skill listed"),
            ("contains", "root", r"power", "power sub-skill listed"),
            ("contains", "root", r"debug", "debug sub-skill listed"),
        ]
    },
    "ROOT-004": {
        "name": "Root skill documents HAS per platform",
        "assertions": [
            ("contains", "root", r"HAS|Hardware\s*Architecture\s*Spec", "HAS reference present"),
            ("contains", "root", r"NVL.*USB.*HAS|USB.*NVL.*HAS", "NVL HAS doc name"),
            ("contains", "root", r"PTL.*USB.*HAS|USB.*PTL.*HAS", "PTL HAS doc name"),
        ]
    },
    "ROOT-005": {
        "name": "Root skill documents NGA exit codes",
        "assertions": [
            ("contains", "root", r"[Ee]xit.*[Cc]ode|NGA.*[Ee]xit|PASS.*0|0.*PASS", "exit code 0 pass"),
            ("contains", "root", r"[Ee]xit.*1|1.*[Ff]ail|FAIL.*1|1.*FAIL", "exit code 1 fail"),
        ]
    },
    "ROOT-006": {
        "name": "Root skill documents test naming convention",
        "assertions": [
            ("contains", "root", r"USB_[A-Z]+_[A-Z]+_\d+|test.*naming|naming.*conven", "test naming convention present"),
        ]
    },
    "ROOT-007": {
        "name": "Root skill has Co-Design reference",
        "assertions": [
            ("contains", "root", r"Co-?Design|codesign", "Co-Design reference present"),
        ]
    },
    "ROOT-008": {
        "name": "Root skill has NVL multi-die warning",
        "assertions": [
            ("contains", "root", r"PCH-H|PCH-S|multi.?die|die\s+variant", "NVL multi-die variant noted"),
        ]
    },

    # ─── XHCI SKILL ──────────────────────────────────────────────────────────

    "XHCI-001": {
        "name": "xHCI skill covers PORTSC register",
        "assertions": [
            ("contains", "xhci", r"PORTSC", "PORTSC register documented"),
            ("contains", "xhci", r"PLS|Port\s*Link\s*State", "PLS field documented"),
            ("contains", "xhci", r"CCS|Current\s*Connect\s*Status", "CCS bit documented"),
        ]
    },
    "XHCI-002": {
        "name": "xHCI skill covers USB speed encoding",
        "assertions": [
            ("contains", "xhci", r"SuperSpeed|Gen\s*[12]|USB\s*3|USB3|5\s*Gbps|10\s*Gbps", "USB3 speed present"),
            ("contains", "xhci", r"HighSpeed|USB\s*2\.0|480\s*Mb", "USB2 HS present"),
            ("contains", "xhci", r"FullSpeed|12\s*Mb|Full.?Speed", "USB FS present"),
        ]
    },
    "XHCI-003": {
        "name": "xHCI skill documents BAR0 register access",
        "assertions": [
            ("contains", "xhci", r"BAR0|BAR\s*0|MMIO\s*base|xHCI\s*base", "BAR0 access documented"),
        ]
    },
    "XHCI-004": {
        "name": "xHCI skill has PythonSV register access",
        "assertions": [
            ("contains", "xhci", r"pythonsv|pysv|sv\.", "PythonSV access documented"),
            ("contains", "xhci", r"xhci\.mmio|xhci_mmio|portsc", "PythonSV PORTSC example"),
        ]
    },
    "XHCI-005": {
        "name": "xHCI skill has per-platform BAR notes",
        "assertions": [
            ("contains", "xhci", r"NVL|PTL|LNL", "platform-specific BAR notes present"),
        ]
    },
    "XHCI-006": {
        "name": "xHCI skill warns against PTL f-string usage",
        "assertions": [
            ("contains", "xhci", r"f-string|f_string|\.format\(\)|no.*f.*string|avoid.*f.*string", "PTL f-string prohibition documented"),
        ]
    },

    # ─── POWER SKILL ─────────────────────────────────────────────────────────

    "PWR-001": {
        "name": "Power skill covers U-state LPM",
        "assertions": [
            ("contains", "power", r"U0|U1|U2|U3", "U-states documented"),
            ("contains", "power", r"LPM|Link\s*Power\s*Management", "LPM term present"),
        ]
    },
    "PWR-002": {
        "name": "Power skill covers device D-states",
        "assertions": [
            ("contains", "power", r"D0|D3|device\s*power\s*state", "D-states documented"),
        ]
    },
    "PWR-003": {
        "name": "Power skill covers runtime suspend",
        "assertions": [
            ("contains", "power", r"runtime\s*suspend|autosuspend|selective\s*suspend", "runtime suspend documented"),
        ]
    },
    "PWR-004": {
        "name": "Power skill covers UAOL",
        "assertions": [
            ("contains", "power", r"UAOL|USB\s*Audio\s*Offload", "UAOL documented"),
            ("contains", "power", r"ACE3|ACE4", "ACE3/ACE4 variants documented"),
            ("contains", "power", r"Feedback\s*FIFO|FIFO.*ms|ms.*FIFO", "Feedback FIFO timing documented"),
        ]
    },
    "PWR-005": {
        "name": "Power skill has per-platform LPM matrix",
        "assertions": [
            ("contains", "power", r"LPM.*[Mm]atrix|[Mm]atrix.*LPM|platform.*LPM|LPM.*platform", "LPM matrix present"),
            ("contains", "power", r"NVL|PTL|LNL|MTL|ARL", "platform rows in power skill"),
        ]
    },
    "PWR-006": {
        "name": "Power skill has UAOL validation checklist",
        "assertions": [
            ("contains", "power", r"UAOL.*[Cc]hecklist|[Cc]hecklist.*UAOL|UAOL.*[Vv]alidat", "UAOL checklist present"),
        ]
    },

    # ─── ENUMERATION SKILL ───────────────────────────────────────────────────

    "ENUM-001": {
        "name": "Enumeration skill covers USB descriptor set",
        "assertions": [
            ("contains", "enumeration", r"Device\s*Descriptor|Configuration\s*Descriptor|Interface\s*Descriptor|Endpoint\s*Descriptor", "USB descriptors documented"),
        ]
    },
    "ENUM-002": {
        "name": "Enumeration skill covers USB3 link training",
        "assertions": [
            ("contains", "enumeration", r"LTSSM|Polling|U0.*state|RxDetect", "USB3 LTSSM states documented"),
        ]
    },
    "ENUM-003": {
        "name": "Enumeration skill covers USB2 reset sequence",
        "assertions": [
            ("contains", "enumeration", r"Reset|SE0|FS.*HS|chirp|handshake", "USB2 reset/chirp documented"),
        ]
    },
    "ENUM-004": {
        "name": "Enumeration skill documents SET_ADDRESS",
        "assertions": [
            ("contains", "enumeration", r"SET_ADDRESS|set_address|address\s*assignment", "SET_ADDRESS documented"),
        ]
    },
    "ENUM-005": {
        "name": "Enumeration skill covers hub enumeration",
        "assertions": [
            ("contains", "enumeration", r"hub|Hub|HUB", "hub enumeration documented"),
        ]
    },

    # ─── DEBUG SKILL ─────────────────────────────────────────────────────────

    "DBG-001": {
        "name": "Debug skill references known HSDES sightings",
        "assertions": [
            ("contains", "debug", r"16029865294|HSDES.*1602|1602.*HSDES", "PTL UAOL HSDES sighting"),
            ("contains", "debug", r"18043001729|HSDES.*1804|1804.*HSDES", "NVL ACE4 HSDES sighting"),
        ]
    },
    "DBG-002": {
        "name": "Debug skill has NGA exit code table",
        "assertions": [
            ("contains", "debug", r"exit.*code|NGA.*exit|0.*PASS|PASS.*0", "NGA exit codes in debug skill"),
        ]
    },
    "DBG-003": {
        "name": "Debug skill has platform-specific notes",
        "assertions": [
            ("contains", "debug", r"NVL|PTL|LNL|MTL|ARL", "platform-specific debug notes"),
            ("contains", "debug", r"[Pp]latform.*[Ss]pecific|per.platform", "platform-specific section header"),
        ]
    },
    "DBG-004": {
        "name": "Debug skill covers WinUSB and USBView tools",
        "assertions": [
            ("contains", "debug", r"USBView|usbview|WinUSB|winusb|USB\s*trace|usbhcdiag", "USB debug tools documented"),
        ]
    },
    "DBG-005": {
        "name": "Debug skill covers USB analyzer / capture",
        "assertions": [
            ("contains", "debug", r"LeCroy|Beagle|USB\s*analyzer|protocol\s*analyzer|capture", "USB analyzer documented"),
        ]
    },
    "DBG-006": {
        "name": "Debug skill points to known_issues.md",
        "assertions": [
            ("contains", "debug", r"known_issues|known.issues", "pointer to known_issues.md"),
        ]
    },

    # ─── AGENT DEFINITION ────────────────────────────────────────────────────

    "AGENT-001": {
        "name": "Agent frontmatter uses correct key names",
        "assertions": [
            ("contains", "agent", r"\btool:", "correct 'tool:' frontmatter key"),
            ("not_contains", "agent", r"\btools:", "no incorrect 'tools:' key"),
            ("contains", "agent", r"\bpermission:", "correct 'permission:' frontmatter key"),
            ("not_contains", "agent", r"\bpermissions:", "no incorrect 'permissions:' key"),
        ]
    },
    "AGENT-002": {
        "name": "Agent has version 2.0.0",
        "assertions": [
            ("contains", "agent", r"v2\.0\.0|version.*2\.0\.0|2\.0\.0", "version 2.0.0 present"),
        ]
    },
    "AGENT-003": {
        "name": "Agent has Co-Design 5-step procedure",
        "assertions": [
            ("contains", "agent", r"Co-?Design|codesign", "Co-Design section present"),
            ("contains", "agent", r"Step\s*[12345]|STEP\s*[12345]|playwright|browser_navigate", "step-by-step Co-Design procedure"),
        ]
    },
    "AGENT-004": {
        "name": "Agent documents HAS per platform",
        "assertions": [
            ("contains", "agent", r"NVL.*HAS|HAS.*NVL", "NVL HAS in agent"),
            ("contains", "agent", r"PTL.*HAS|HAS.*PTL", "PTL HAS in agent"),
            ("contains", "agent", r"LNL.*HAS|HAS.*LNL", "LNL HAS in agent"),
        ]
    },
    "AGENT-005": {
        "name": "Agent has NVL multi-die critical warning",
        "assertions": [
            ("contains", "agent", r"PCH-H|PCH-S|multi.?die", "NVL multi-die WARNING in agent"),
        ]
    },
    "AGENT-006": {
        "name": "Agent documents RTL bug table",
        "assertions": [
            ("contains", "agent", r"RTL\s*[Bb]ug|silicon\s*bug|errata", "RTL bug table present"),
            ("contains", "agent", r"16029865294", "HSDES PTL UAOL sighting in RTL bugs"),
        ]
    },
    "AGENT-007": {
        "name": "Agent has sub-agent delegation with disabled/unregistered flags",
        "assertions": [
            ("contains", "agent", r"DISABLED|UNREGISTERED|disabled|unregistered", "disabled/unregistered flags present"),
        ]
    },
    "AGENT-008": {
        "name": "Agent has SKILL OPERATIONAL NOTES section",
        "assertions": [
            ("contains", "agent", r"SKILL\s*OPERATIONAL\s*NOTES|Operational\s*Notes", "SKILL OPERATIONAL NOTES present"),
            ("contains", "agent", r"securewiki|pysv|nga|onebkc|ttk3", "per-skill gotchas present"),
        ]
    },
    "AGENT-009": {
        "name": "Agent documents PLS table (all 15 values)",
        "assertions": [
            ("contains", "agent", r"PLS|Port\s*Link\s*State", "PLS table present"),
            ("contains", "agent", r"0x0.*U0|U0.*0x0|\b0\b.*U0|U0.*\b0\b", "U0 = 0 entry"),
            ("contains", "agent", r"0xF|0x[Ff]|Compliance|RxDetect|Rx\.Detect", "U3/Compliance/RxDetect entries"),
        ]
    },
    "AGENT-010": {
        "name": "Agent documents USB speed mapping",
        "assertions": [
            ("contains", "agent", r"[Ss]peed.*[Mm]ap|[Ss]peed.*[Mm]apping|PORTSC.*[Ss]peed|[Ss]peed.*PORTSC", "speed mapping present"),
            ("contains", "agent", r"Gen\s*2x2|20\s*Gb|SuperSpeed\+", "USB 20G speed documented"),
        ]
    },
    "AGENT-011": {
        "name": "Agent has todowrite and multi_tool_use tools",
        "assertions": [
            ("contains", "agent", r"todowrite", "todowrite tool present"),
            ("contains", "agent", r"multi_tool_use", "multi_tool_use tool present"),
        ]
    },
    "AGENT-012": {
        "name": "Agent UAOL section has ACE timing details",
        "assertions": [
            ("contains", "agent", r"1\s*ms|~?1ms", "ACE3 1ms FIFO timing"),
            ("contains", "agent", r"10\s*ms|~?10ms", "ACE4 10ms FIFO timing"),
        ]
    },

    # ─── DOCS ────────────────────────────────────────────────────────────────

    "DOCS-001": {
        "name": "known_issues.md has HSDES entries",
        "assertions": [
            ("contains", "known_issues", r"16029865294|HSDES", "HSDES sighting ID in known_issues"),
            ("contains", "known_issues", r"workaround|Workaround|WORKAROUND", "workarounds documented"),
            ("contains", "known_issues", r"severity|Severity|CRITICAL|HIGH|MEDIUM", "severity ratings present"),
        ]
    },
    "DOCS-002": {
        "name": "cheat_sheet.md has key reference tables",
        "assertions": [
            ("contains", "cheat_sheet", r"PORTSC|portsc", "PORTSC bits in cheat sheet"),
            ("contains", "cheat_sheet", r"PLS|Port\s*Link\s*State", "PLS table in cheat sheet"),
            ("contains", "cheat_sheet", r"NGA|exit\s*code|exit.*0|0.*PASS", "NGA codes in cheat sheet"),
            ("contains", "cheat_sheet", r"Co-?Design|codesign", "Co-Design in cheat sheet"),
        ]
    },
    "DOCS-003": {
        "name": "test_coverage_matrix.md has platform columns and test rows",
        "assertions": [
            ("contains", "test_coverage_matrix", r"NVL|PTL|LNL|MTL|ARL", "platform columns present"),
            ("contains", "test_coverage_matrix", r"enumerat|xHCI|power|UAOL", "test category rows present"),
            ("contains", "test_coverage_matrix", r"✓|○|✗|—|\?", "matrix symbols present"),
        ]
    },
}
