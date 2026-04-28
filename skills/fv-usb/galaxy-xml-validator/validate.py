#!/usr/bin/env python3
"""Galaxy XML Validator for FV-USB test case standardization and flow validation."""

import os
import sys
import glob
import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict


# ─── Dictionary Rules ────────────────────────────────────────────────────────

DICTIONARY_RULES = {
    "rule1_base_traffic": {
        "name": "Base Traffic",
        "description": "If filename contains 'base_traffic' or 'Base_traffic', the Test FLOW must have all 4 traffic types: bulk, isoch audio, isoch camera, and interrupt.",
        "keywords": ["base_traffic", "Base_traffic"],
        "required_traffic": {
            "bulk": ["CheckSumFT", "FIO", "IOMeter"],
            "isoch_audio": ["Audio"],
            "isoch_camera": ["FFMPEG"],
            "interrupt": ["CheckSumFT", "FIO", "IOMeter"],
        },
    },
    "rule2_sx_sxiy_residency": {
        "name": "Sx + Sxiy Residency",
        "description": "If filename contains Sx keywords (S3/S4/S5/S0ix/Sxiy), must have Sxix residency checking with pre capture.",
        "keywords": ["S3", "S4", "S5", "S0ix", "S3ixy", "S4ixy", "S5ixy", "S0ixy"],
    },
    "rule3_ttk_verify_post_event": {
        "name": "TTK Verify Post Event for Connect/Disconnect in Sx",
        "description": "If Test FLOW contains Sx keywords AND has a connect/disconnect sequence (disconnect then connect, connect then disconnect, or hotplug), must have TTK Verify Post Event HOST-EV.",
        "sx_keywords": ["SleepState", "S3", "S4", "S5", "S0ix"],
        "connect_keywords": ["connect", "disconnect", "hotplug", "Connect", "Disconnect", "Hotplug"],
    },
    "rule4_no_copy_in_desc": {
        "name": "No 'Copy' in Step Names",
        "description": "No step Desc attribute may contain the word 'copy' (case-insensitive).",
    },
    "rule5_sxix_residency_naming": {
        "name": "Sxix Residency Naming Convention",
        "description": "CHECKER Desc attributes for Sxix residency capture must use 'Capture' prefix (NOT 'CaptureEvent') and include 'ix' suffix: 'Capture Sxix Residencies - S{3,4,5}ix' or 'Capture S0ix Residencies - S0ix'.",
        "valid_patterns": [
            "Capture Sxix Residencies - S3ix",
            "Capture Sxix Residencies - S4ix",
            "Capture Sxix Residencies - S5ix",
            "Capture S0ix Residencies - S0ix",
            "Capture Sxix Residencies Flow",
            "Capture S0ix Residencies Flow",
            "Capture Sxix Residencies",
            "Capture S0ix Residencies",
        ],
    },
}


# ─── Standardization Checks ──────────────────────────────────────────────────

VARIABLES_COMMENT_GROUPS = [
    "Device/Platform",
    "Port/Speed",
    "Power Management - TTK3/Timeouts",
    "Power Management - Sx/S0ix Checks",
    "Workload",
    "Performance Counters",
    "Misc",
]


# ─── Validation Result ───────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self, filename):
        self.filename = filename
        self.passes = []
        self.fails = []
        self.skips = []

    def add_pass(self, check_name, detail=""):
        self.passes.append((check_name, detail))

    def add_fail(self, check_name, detail=""):
        self.fails.append((check_name, detail))

    def add_skip(self, check_name, detail=""):
        self.skips.append((check_name, detail))

    def print_report(self):
        print(f"\n{'='*72}")
        print(f"  Validation Report: {self.filename}")
        print(f"{'='*72}")
        if self.passes:
            print(f"\n  PASS ({len(self.passes)}):")
            for name, detail in self.passes:
                print(f"    [PASS] {name}" + (f" - {detail}" if detail else ""))
        if self.fails:
            print(f"\n  FAIL ({len(self.fails)}):")
            for name, detail in self.fails:
                print(f"    [FAIL] {name}" + (f" - {detail}" if detail else ""))
        if self.skips:
            print(f"\n  SKIP ({len(self.skips)}):")
            for name, detail in self.skips:
                print(f"    [SKIP] {name}" + (f" - {detail}" if detail else ""))
        print(f"\n  Summary: {len(self.passes)} PASS, {len(self.fails)} FAIL, {len(self.skips)} SKIP")
        print(f"{'='*72}\n")

    def write_report(self, report_path):
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"Validation Report: {self.filename}\n")
            f.write("=" * 72 + "\n")
            if self.passes:
                f.write(f"\nPASS ({len(self.passes)}):\n")
                for name, detail in self.passes:
                    f.write(f"  [PASS] {name}" + (f" - {detail}" if detail else "") + "\n")
            if self.fails:
                f.write(f"\nFAIL ({len(self.fails)}):\n")
                for name, detail in self.fails:
                    f.write(f"  [FAIL] {name}" + (f" - {detail}" if detail else "") + "\n")
            if self.skips:
                f.write(f"\nSKIP ({len(self.skips)}):\n")
                for name, detail in self.skips:
                    f.write(f"  [SKIP] {name}" + (f" - {detail}" if detail else "") + "\n")
            f.write(f"\nSummary: {len(self.passes)} PASS, {len(self.fails)} FAIL, {len(self.skips)} SKIP\n")


# ─── Helper Functions ────────────────────────────────────────────────────────

def get_test_flow_steps(tree):
    """Get all TEST/HOST-EV/CHECKER/DELAY steps inside <FLOW Desc="Test">, including nested FLOWs."""
    test_steps = []
    for flow in tree.iter("FLOW"):
        desc = flow.get("Desc", "")
        if desc == "Test":
            # Recurse into all descendants, not just direct children
            for step in flow.iter():
                if step.tag in ("TEST", "HOST-EV", "CHECKER", "DELAY", "SleepState", "FLOW"):
                    test_steps.append(step)
    return test_steps


def get_all_flow_steps(tree):
    """Get all steps across all flows."""
    all_steps = []
    for flow in tree.iter("FLOW"):
        for step in flow:
            if step.tag in ("TEST", "HOST-EV", "CHECKER", "DELAY", "SleepState"):
                all_steps.append(step)
    return all_steps


def find_peer_files(xml_path, test_case_dir):
    """Find XML files with similar keywords in the same directory."""
    filename = os.path.basename(xml_path)
    base = os.path.splitext(filename)[0]
    keywords = [kw for kw in ["S0ix", "S3", "S4", "S5", "Base_traffic", "traffic", "Connect", "Disconnect"] if kw.lower() in base.lower()]
    peers = []
    for f in sorted(glob.glob(os.path.join(test_case_dir, "*.xml"))):
        if f != xml_path:
            fname = os.path.basename(f)
            if any(kw.lower() in fname.lower() for kw in keywords):
                peers.append(f)
    return peers[:5]


# ─── Standardization Checks ──────────────────────────────────────────────────

def check_root_structure(tree, text_content, result):
    """Check for <ATTRIBUTES> block after <GALAXY> root."""
    root = tree.getroot()
    if root.tag != "GALAXY":
        result.add_fail("Root structure", "Root element is not <GALAXY>")
        return

    has_attributes = False
    for child in root:
        if child.tag == "ATTRIBUTES":
            has_attributes = True
            break

    if has_attributes:
        result.add_fail("Root structure", "Extra <ATTRIBUTES> block found after <GALAXY>")
    else:
        result.add_pass("Root structure", "No extra <ATTRIBUTES> block")


def check_variables_formatting(tree, text_content, result):
    """Check for XML comment groups in <VARIABLES> section."""
    variables = None
    for elem in tree.iter():
        if elem.tag == "VARIABLES":
            variables = elem
            break
    if variables is None:
        result.add_fail("VARIABLES formatting", "<VARIABLES> section not found")
        return

    missing_groups = []
    for group in VARIABLES_COMMENT_GROUPS:
        if group not in text_content:
            missing_groups.append(group)

    if missing_groups:
        result.add_fail("VARIABLES formatting", f"Missing comment groups: {', '.join(missing_groups)}")
    else:
        result.add_pass("VARIABLES formatting", "All comment groups present")


def check_top_flow_structure(tree, result):
    """Check for Pre Test -> Test -> Post Test FLOW structure."""
    flows = tree.findall(".//FLOW")
    flow_descs = [f.get("Desc", "") for f in flows]

    has_pre = "Pre Test" in flow_descs
    has_test = "Test" in flow_descs
    has_post = "Post Test" in flow_descs

    if has_pre and has_test and has_post:
        result.add_pass("Top-level FLOW structure", "Pre Test -> Test -> Post Test found")
    else:
        missing = []
        if not has_pre:
            missing.append("Pre Test")
        if not has_test:
            missing.append("Test")
        if not has_post:
            missing.append("Post Test")
        result.add_fail("Top-level FLOW structure", f"Missing flows: {', '.join(missing)}")


# ─── Flow Dictionary Checks ──────────────────────────────────────────────────

def check_base_traffic(tree, result, filename=""):
    """Rule 1: Base traffic must have bulk, isoch audio, isoch camera, and interrupt in Test FLOW."""
    is_base = any(kw.lower() in filename.lower() for kw in DICTIONARY_RULES["rule1_base_traffic"]["keywords"])
    if not is_base:
        result.add_skip("Rule 1: Base Traffic", "Not a base traffic file")
        return

    test_steps = get_test_flow_steps(tree)
    descs = [s.get("Desc", "") for s in test_steps]
    cmds = [s.get("Cmd", "") for s in test_steps]
    all_text = " ".join(descs) + " " + " ".join(cmds)

    required = DICTIONARY_RULES["rule1_base_traffic"]["required_traffic"]
    missing = []

    has_bulk = any(kw in all_text for kw in required["bulk"])
    has_isoch_audio = any(kw in all_text for kw in required["isoch_audio"])
    has_isoch_camera = any(kw in all_text for kw in required["isoch_camera"])
    has_interrupt = any(kw in all_text for kw in required["interrupt"])

    if not has_bulk:
        missing.append("bulk")
    if not has_isoch_audio:
        missing.append("isoch audio")
    if not has_isoch_camera:
        missing.append("isoch camera")
    if not has_interrupt:
        missing.append("interrupt")

    if missing:
        result.add_fail("Rule 1: Base Traffic", f"Missing traffic types in Test FLOW: {', '.join(missing)}")
    else:
        result.add_pass("Rule 1: Base Traffic", "All required traffic types present in Test FLOW")


def check_sx_sxiy_residency(tree, result):
    """Rule 2: Sx + Sxiy must have residency checking and pre capture."""
    all_steps = get_all_flow_steps(tree)
    all_descs = [s.get("Desc", "") for s in all_steps]
    all_text = " ".join(all_descs)

    is_sx = any(kw.lower() in all_text.lower() for kw in DICTIONARY_RULES["rule2_sx_sxiy_residency"]["keywords"])
    if not is_sx:
        result.add_skip("Rule 2: Sx + Sxiy Residency", "Not an Sx/Sxiy flow")
        return

    has_residency = any("Capture Sxix Residencies" in d or "Capture S0ix Residencies" in d for d in all_descs)

    # -Capture is an <arg name="-Capture"/> child of CHECKER, not a Desc — scan arg elements directly
    has_capture = any(
        elem.get("name", "") == "-Capture"
        for elem in tree.iter("arg")
    )

    if has_residency and has_capture:
        result.add_pass("Rule 2: Sx + Sxiy Residency", "Sxix residency check with pre capture found")
    else:
        missing = []
        if not has_residency:
            missing.append("Capture Sxix Residencies check")
        if not has_capture:
            missing.append("pre capture (-Capture flag)")
        result.add_fail("Rule 2: Sx + Sxiy Residency", f"Missing: {', '.join(missing)}")


def check_ttk_verify_post_event(tree, result):
    """Rule 3: If connect/disconnect/hotplug sequence in Sx flow, must have TTK Verify Post Event."""
    test_steps = get_test_flow_steps(tree)
    all_descs = [s.get("Desc", "") for s in test_steps]
    all_text = " ".join(all_descs)

    sx_keywords = DICTIONARY_RULES["rule3_ttk_verify_post_event"]["sx_keywords"]
    connect_keywords = DICTIONARY_RULES["rule3_ttk_verify_post_event"]["connect_keywords"]

    has_sx = any(kw.lower() in all_text.lower() for kw in sx_keywords)
    if not has_sx:
        result.add_skip("Rule 3: TTK Verify Post Event", "Not an Sx flow")
        return

    has_connect = any(kw.lower() in all_text.lower() for kw in connect_keywords)

    if has_connect:
        has_ttk_post = any("ttk" in d.lower() and "verify" in d.lower() and "post" in d.lower() for d in all_descs)
        if has_ttk_post:
            result.add_pass("Rule 3: TTK Verify Post Event", "TTK Verify Post Event found for connect/disconnect sequence")
        else:
            result.add_fail("Rule 3: TTK Verify Post Event", "Missing TTK Verify Post Event for connect/disconnect sequence")
    else:
        has_ttk_post = any("ttk" in d.lower() and "verify" in d.lower() and "post" in d.lower() for d in all_descs)
        if has_ttk_post:
            result.add_fail("Rule 3: TTK Verify Post Event", "Unnecessary TTK Verify Post Event (no connect/disconnect/hotplug sequence in Sx flow)")
        else:
            result.add_skip("Rule 3: TTK Verify Post Event", "Not a connect/disconnect sequence in Sx flow")


def check_no_copy_in_desc(tree, result):
    """Rule 4: No step Desc attribute may contain the word 'copy'."""
    found_copy = []
    for flow in tree.iter("FLOW"):
        for step in flow:
            desc = step.get("Desc", "")
            if "copy" in desc.lower():
                found_copy.append(desc)

    if found_copy:
        result.add_fail("Rule 4: No 'Copy' in Desc", f"Found 'copy' in: {', '.join(found_copy)}")
    else:
        result.add_pass("Rule 4: No 'Copy' in Desc", "No 'copy' found in any step Desc")


def check_sxix_residency_naming(tree, result):
    """Rule 5: CHECKER Desc attributes for Sxix residency must follow golden flow naming."""
    valid_patterns = DICTIONARY_RULES["rule5_sxix_residency_naming"]["valid_patterns"]

    invalid = []
    for flow in tree.iter("FLOW"):
        for step in flow:
            if step.tag != "CHECKER":
                continue
            desc = step.get("Desc", "")
            if "Residenc" in desc or "Residency" in desc:
                if desc not in valid_patterns:
                    invalid.append(desc)

    if invalid:
        result.add_fail("Rule 5: Sxix Residency Naming", f"Invalid naming: {', '.join(set(invalid))}")
    else:
        result.add_pass("Rule 5: Sxix Residency Naming", "All residency CHECKER Descs follow golden naming")


# ─── Rule 6: PM Verification Blocks ──────────────────────────────────────────

def detect_sleep_state(filename):
    """Detect the sleep state from a filename."""
    fn = filename.lower()
    if "s0ix" in fn or "s0i" in fn or "cs_" in fn:
        return "S0ix"
    if "s3" in fn:
        return "S3"
    if "s4" in fn:
        return "S4"
    if "s5" in fn and "g3" in fn:
        return "S5-G3"
    if "s5" in fn:
        return "S5"
    if "warm_reset" in fn or "_wr_" in fn or fn.startswith("pm_wr"):
        return "WR"
    if "g3" in fn:
        return "G3"
    return None


def is_pm_file(filename):
    """Check if a file is a PM file (has sleep/wake flows)."""
    fn = filename.lower()
    pm_keywords = ["pm_s3", "pm_s4", "pm_s5", "pm_s0ix", "pm_wr", "pm_g3",
                   "post_s3", "post_s4", "post_s5", "post_s0ix",
                   "warm_reset", "abrupt_wake"]
    return any(kw in fn for kw in pm_keywords)


def check_pm_verification(tree, result, filename=""):
    """Rule 6: PM files must have PM Verification blocks in FLOW."""
    if not is_pm_file(filename):
        result.add_skip("Rule 6: PM Verification", "Not a PM file")
        return

    all_descs = []
    for elem in tree.iter():
        desc = elem.get("Desc", "")
        if desc:
            all_descs.append(desc)

    has_pm_verif = any("PM Verification" in d for d in all_descs)
    if has_pm_verif:
        result.add_pass("Rule 6: PM Verification", "PM Verification block found")
    else:
        result.add_fail("Rule 6: PM Verification", "Missing PM Verification block in PM file")


# ─── Rule 7: TESTCONFIG Matching ─────────────────────────────────────────────

def check_testconfig_matching(tree, result, filename=""):
    """Rule 7: TESTCONFIG CHECKER entries must be referenced by FLOW; no dead weight."""
    testconfig = tree.find(".//TESTCONFIG")
    if testconfig is None:
        result.add_skip("Rule 7: TESTCONFIG matching", "No TESTCONFIG section")
        return

    # Collect all CHECKER Desc values in TESTCONFIG
    checker_descs = set()
    for checker in testconfig.iter("CHECKER"):
        desc = checker.get("Desc", "")
        if desc:
            checker_descs.add(desc)

    if not checker_descs:
        result.add_pass("Rule 7: TESTCONFIG matching", "No CHECKER entries to validate")
        return

    # Collect all Desc references in FLOW section
    flow_refs = set()
    for flow in tree.iter("FLOW"):
        for elem in flow.iter():
            desc = elem.get("Desc", "")
            if desc:
                flow_refs.add(desc)

    # Find unreferenced CHECKERs
    unreferenced = checker_descs - flow_refs
    if unreferenced:
        result.add_fail("Rule 7: TESTCONFIG matching",
                        f"{len(unreferenced)} unreferenced CHECKER(s): {', '.join(sorted(list(unreferenced))[:5])}{'...' if len(unreferenced) > 5 else ''}")
    else:
        result.add_pass("Rule 7: TESTCONFIG matching", f"All {len(checker_descs)} CHECKER(s) referenced by FLOW")


# ─── Bonus Checks ────────────────────────────────────────────────────────────

def check_error_checker_casing(tree, text_content, result):
    """B1: 'Error Checker' must have capital C (not 'Error checker')."""
    count = text_content.count("Error checker")
    if count > 0:
        result.add_fail("B1: Error Checker casing", f"Found {count} 'Error checker' (lowercase c)")
    else:
        result.add_pass("B1: Error Checker casing")


def check_exit1_spacing(tree, text_content, result):
    """B2: 'Exit 1' must have a space (not 'Exit1')."""
    # Match Exit1 but not Exit 1
    count = len(re.findall(r'Exit1(?!\s*")', text_content))
    # More precise: count in Desc attributes
    count = 0
    for elem in tree.iter():
        desc = elem.get("Desc", "")
        if "Exit1" in desc and "Exit 1" not in desc:
            count += 1
    if count > 0:
        result.add_fail("B2: Exit 1 spacing", f"Found {count} 'Exit1' (missing space)")
    else:
        result.add_pass("B2: Exit 1 spacing")


def check_double_spaces(tree, text_content, result):
    """B3: No double spaces in Desc attributes (e.g., 'PMC FW  Error')."""
    count = 0
    for elem in tree.iter():
        desc = elem.get("Desc", "")
        if "  " in desc:
            count += 1
    if count > 0:
        result.add_fail("B3: Double spaces", f"Found {count} Desc attributes with double spaces")
    else:
        result.add_pass("B3: Double spaces")


def check_s0ix_casing(tree, text_content, result):
    """B4: 'S0ix' must use lowercase x (not 'S0iX')."""
    count = 0
    for elem in tree.iter():
        desc = elem.get("Desc", "")
        if "S0iX" in desc:
            count += 1
    if count > 0:
        result.add_fail("B4: S0ix casing", f"Found {count} 'S0iX' (should be 'S0ix')")
    else:
        result.add_pass("B4: S0ix casing")


# ─── Cross-Checks (Informational Only) ───────────────────────────────────────

def check_peer_structure(xml_path, peers):
    """Compare structural tags with peer files (informational only)."""
    if not peers:
        return

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        my_struct = set()
        for child in root:
            my_struct.add(child.tag)
            if child.tag == "GALAXYTEST":
                for sub in child:
                    my_struct.add(f"GALAXYTEST/{sub.tag}")

        peer_mismatches = []
        for peer_path in peers[:5]:
            try:
                peer_tree = ET.parse(peer_path)
                peer_root = peer_tree.getroot()
                peer_struct = set()
                for child in peer_root:
                    peer_struct.add(child.tag)
                    if child.tag == "GALAXYTEST":
                        for sub in child:
                            peer_struct.add(f"GALAXYTEST/{sub.tag}")
                extra = my_struct - peer_struct
                missing = peer_struct - my_struct
                if extra or missing:
                    peer_mismatches.append(f"{os.path.basename(peer_path)}: extra={extra}, missing={missing}")
            except ET.ParseError:
                pass

        if peer_mismatches:
            print(f"\n  [INFO] Peer structure differences: {'; '.join(peer_mismatches[:3])}")
    except ET.ParseError:
        pass


# ─── Auto-Fix Functions ──────────────────────────────────────────────────────

def fix_root_structure(xml_path):
    """Remove ATTRIBUTES block and fix root structure using raw text replacement."""
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "<ATTRIBUTES>" not in content:
        return False

    content = re.sub(r'\s*<ATTRIBUTES>.*?</ATTRIBUTES>\s*', '\n', content, flags=re.DOTALL)

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def fix_variables_formatting(xml_path):
    """Reorganize VARIABLES with proper XML comment groups and golden indentation."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Ensure GALAXYTEST exists
    galaxytest = root.find("GALAXYTEST")
    if galaxytest is None:
        galaxytest = ET.SubElement(root, "GALAXYTEST")

    # Find or create VARIABLES element
    variables = None
    for child in list(galaxytest):
        if child.tag == "VARIABLES":
            variables = child
            break
    if variables is None:
        variables = ET.SubElement(galaxytest, "VARIABLES")

    # Extract existing variables
    existing_vars = []
    for child in list(variables):
        if child.tag == "VAR":
            name = child.get("name", "")
            value = child.get("value", "")
            if name:
                existing_vars.append((name, value))
        elif child.tag != "#comment":
            name = child.tag
            value = child.text.strip() if child.text else ""
            if name and not name.startswith("#"):
                existing_vars.append((name, value))

    if not existing_vars:
        return False

    # Classify into groups
    groups = {
        "Device/Platform": [],
        "Port/Speed": [],
        "Power Management - TTK3/Timeouts": [],
        "Power Management - Sx/S0ix Checks": [],
        "Workload": [],
        "Performance Counters": [],
        "Misc": [],
    }

    platform_keywords = ["Platform", "SKU", "Die", "Stepping", "PCH", "BoardID", "BoardType", "BoardStepping", "MemorySize", "MemoryType", "MemoryStepping", "Processor", "ProcessorType", "ip_mode", "device_list", "connect_port", "disconnect_port", "cswitch"]
    port_speed_keywords = ["Port", "Speed", "Link", "Controller", "portchain", "ignoreport"]
    pm_ttk3_keywords = ["TTK", "Timeout", "PMStateTime", "Delay", "PowerButton", "S0ixSleepTime", "ping_server"]
    pm_sx_keywords = ["Residencies", "S0ix", "S3", "S4", "S5", "Sxiy", "Sxix", "MemorySelfRefresh", "LastPowerFlow", "LastWakeCause", "PMC", "FailOn", "PMLegacy"]
    workload_keywords = ["Traffic", "Bulk", "Isoch", "Interrupt", "CheckSumFT", "FIO", "Audio", "FFMPEG", "IOMeter", "LPM", "RTD3", "bulk_time", "ffmpeg", "audio_time", "player", "playback", "record", "periodic"]
    perf_keywords = ["Counter", "Performance", "Bandwidth", "Throughput"]

    for name, value in existing_vars:
        placed = False
        for kw in platform_keywords:
            if kw.lower() in name.lower():
                groups["Device/Platform"].append((name, value))
                placed = True
                break
        if placed:
            continue
        for kw in port_speed_keywords:
            if kw.lower() in name.lower():
                groups["Port/Speed"].append((name, value))
                placed = True
                break
        if placed:
            continue
        for kw in pm_ttk3_keywords:
            if kw.lower() in name.lower():
                groups["Power Management - TTK3/Timeouts"].append((name, value))
                placed = True
                break
        if placed:
            continue
        for kw in pm_sx_keywords:
            if kw.lower() in name.lower():
                groups["Power Management - Sx/S0ix Checks"].append((name, value))
                placed = True
                break
        if placed:
            continue
        for kw in workload_keywords:
            if kw.lower() in name.lower():
                groups["Workload"].append((name, value))
                placed = True
                break
        if placed:
            continue
        for kw in perf_keywords:
            if kw.lower() in name.lower():
                groups["Performance Counters"].append((name, value))
                placed = True
                break
        if placed:
            continue
        groups["Misc"].append((name, value))

    # Build new VARIABLES XML with golden format (12-space indent, blank lines between groups)
    new_vars_xml = ""
    first_group = True
    for group_name, var_list in groups.items():
        if not first_group:
            new_vars_xml += "\n"
        first_group = False
        new_vars_xml += f"        <!-- {group_name} -->\n"
        for name, value in var_list:
            new_vars_xml += f'            <VAR name="{name}" value="{value}" />\n'

    # Use raw text replacement to replace the VARIABLES section
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match <VARIABLES>...</VARIABLES> block (handles both element-style and VAR-style)
    match = re.search(r'<VARIABLES>.*?</VARIABLES>', content, re.DOTALL)
    if match:
        replacement = f"<VARIABLES>\n{new_vars_xml}        </VARIABLES>"
        new_content = content[:match.start()] + replacement + content[match.end():]
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    return False


def detect_sleep_state(filename):
    """Detect sleep state from filename for TESTCONFIG cleanup."""
    fn = filename.lower()
    if 'pm_s3' in fn or '_s3_' in fn or 's3ix' in fn or 'post_s3' in fn:
        return 'S3'
    elif 'pm_s4' in fn or '_s4_' in fn or 's4ix' in fn or 'post_s4' in fn:
        return 'S4'
    elif 'pm_s5' in fn or '_s5_' in fn or 's5ix' in fn or 'post_s5' in fn:
        if 'g3' in fn or 's5_g3' in fn or 's5-g3' in fn:
            return 'S5-G3'
        return 'S5'
    elif 'pm_s0ix' in fn or 's0ix' in fn or 'post_s0ix' in fn:
        return 'S0ix'
    elif 'warm_reset' in fn or 'pm_wr' in fn or '_wr_' in fn:
        return 'WR'
    elif 'pm_g3' in fn or '_g3_' in fn:
        return 'G3'
    return None


def fix_text_replacements(xml_path):
    """Phase 1: Global text replacements for casing, spacing, prefix, copy removal."""
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    counts = {}

    # B2: Exit1 -> Exit 1
    c = content.count('Exit1')
    if c:
        content = content.replace('Exit1', 'Exit 1')
        counts['Exit1->Exit 1'] = c

    # B1: Error checker -> Error Checker (case-sensitive, not already Error Checker)
    c = len(re.findall(r'Error checker', content))
    if c:
        content = content.replace('Error checker', 'Error Checker')
        counts['Error checker->Error Checker'] = c

    # R5: CaptureEvent -> Capture
    c = content.count('CaptureEvent')
    if c:
        content = content.replace('CaptureEvent', 'Capture')
        counts['CaptureEvent->Capture'] = c

    # R5: Captur (missing e) -> Capture
    c = len(re.findall(r'Captur(?!e)', content))
    if c:
        content = re.sub(r'Captur(?!e)', 'Capture', content)
        counts['Captur->Capture'] = c

    # B3: Double spaces in PMC FW Error
    c = content.count('PMC FW  Error')
    if c:
        content = content.replace('PMC FW  Error', 'PMC FW Error')
        counts['double-space'] = c

    # B4: S0iX -> S0ix
    c = content.count('S0iX')
    if c:
        content = content.replace('S0iX', 'S0ix')
        counts['S0iX->S0ix'] = c

    # R4: Remove 'copy' from Desc attributes
    copy_pattern = re.compile(r'(Desc="[^"]*?)\s*[-—]?\s*[Cc]opy\s*\d*\s*([^"]*")')
    matches = copy_pattern.findall(content)
    if matches:
        new_content = copy_pattern.sub(lambda m: m.group(1).rstrip() + m.group(2) if m.group(2) != '"' else m.group(1).rstrip() + '"', content)
        if new_content != content:
            counts['copy-in-Desc'] = len(matches)
            content = new_content

    if content != original:
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(content)
        return counts
    return {}


def fix_testconfig_cleanup(xml_path):
    """Phase 2: Delete unreferenced CHECKER entries from TESTCONFIG."""
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return 0

    root = tree.getroot()
    flow = root.find('.//FLOW')
    testconfig = root.find('.//TESTCONFIG')

    if flow is None or testconfig is None:
        return 0

    # Collect all Desc values referenced in FLOW
    flow_descs = set()
    for elem in flow.iter():
        desc = elem.get('Desc', '')
        if desc:
            flow_descs.add(desc)

    # Find unreferenced CHECKER entries
    checkers = testconfig.findall('CHECKER')
    unreferenced = []
    for checker in checkers:
        desc = checker.get('Desc', '')
        if desc and desc not in flow_descs:
            unreferenced.append(checker)

    if not unreferenced:
        return 0

    # Remove unreferenced entries
    for checker in unreferenced:
        testconfig.remove(checker)

    # Write back using raw text to preserve formatting better
    # Re-parse and write
    tree.write(xml_path, encoding="unicode", xml_declaration=True)

    return len(unreferenced)


def fix_residency_naming(xml_path):
    """Phase 3: Fix Sxix residency capture naming to match file's sleep state."""
    filename = os.path.basename(xml_path)
    state = detect_sleep_state(filename)
    if not state:
        return 0

    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    count = 0

    if state == 'S0ix':
        target = 'Capture S0ix Residencies - S0ix'
    else:
        target = f'Capture Sxix Residencies - {state}ix'

    # Fix "S0ix Residency Capture" -> correct target
    if 'S0ix Residency Capture' in content:
        c = content.count('S0ix Residency Capture')
        content = content.replace('S0ix Residency Capture', target)
        count += c

    # Fix missing 'ix' suffix: "Capture Sxix Residencies - S3" -> "...S3ix"
    for st in ['S3', 'S4', 'S5']:
        old = f'Capture Sxix Residencies - {st}"'
        new = f'Capture Sxix Residencies - {st}ix"'
        if old in content:
            c = content.count(old)
            content = content.replace(old, new)
            count += c

    if content != original:
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(content)

    return count


def fix_inner_arg_values(xml_path):
    """Phase 3b: Fix hardcoded inner Arg values (LastPowerFlow, MemSelfRefresh) to match file state."""
    filename = os.path.basename(xml_path)
    state = detect_sleep_state(filename)
    if not state or state in ('S0ix', 'WR', 'G3', 'S5-G3'):
        return 0  # These states don't use LastPowerFlow/MemSelfRefresh

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return 0

    root = tree.getroot()
    testconfig = root.find('.//TESTCONFIG')
    if testconfig is None:
        return 0

    count = 0
    for checker in testconfig.findall('CHECKER'):
        desc = checker.get('Desc', '')
        # Only fix entries matching this file's state suffix
        if not desc.endswith(f'- {state}'):
            continue
        for arg in checker.findall('.//Arg'):
            arg_name = arg.get('name', '')
            arg_val = arg.get('val', '')
            if arg_name == '-PowerFlow' and arg_val != state:
                arg.set('val', state)
                count += 1
            elif arg_name == '-State' and arg_val != state:
                arg.set('val', state)
                count += 1

    if count > 0:
        tree.write(xml_path, encoding="unicode", xml_declaration=True)

    return count


# ─── Main Validation ─────────────────────────────────────────────────────────

def validate_file(xml_path, golden_path=None, report_path=None, test_case_dir=None):
    """Validate a single XML file."""
    filename = os.path.basename(xml_path)
    result = ValidationResult(filename)

    # Parse XML
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        result.add_fail("XML parsing", str(e))
        result.print_report()
        if report_path:
            result.write_report(report_path)
        return result

    # Read raw text for root structure check
    with open(xml_path, "r", encoding="utf-8") as f:
        text_content = f.read()

    # Standardization checks
    check_root_structure(tree, text_content, result)
    check_variables_formatting(tree, text_content, result)
    check_top_flow_structure(tree, result)

    # Flow dictionary checks
    check_base_traffic(tree, result, filename=filename)
    check_sx_sxiy_residency(tree, result)
    check_ttk_verify_post_event(tree, result)
    check_no_copy_in_desc(tree, result)
    check_sxix_residency_naming(tree, result)
    check_pm_verification(tree, result, filename=filename)
    check_testconfig_matching(tree, result, filename=filename)

    # Bonus checks
    check_error_checker_casing(tree, text_content, result)
    check_exit1_spacing(tree, text_content, result)
    check_double_spaces(tree, text_content, result)
    check_s0ix_casing(tree, text_content, result)

    # Peer cross-check (informational only)
    if test_case_dir:
        peers = find_peer_files(xml_path, test_case_dir)
        check_peer_structure(xml_path, peers)

    # Golden flow cross-check (informational only, skip from report)
    if golden_path and os.path.exists(golden_path):
        try:
            golden_tree = ET.parse(golden_path)
            golden_elements = set(elem.tag for elem in golden_tree.iter())
            my_elements = set(elem.tag for elem in tree.iter())
            missing_vs_golden = golden_elements - my_elements
            required_missing = [e for e in missing_vs_golden if e in ["CONFIGURATION", "GALAXYTEST", "TESTCONFIG", "VARIABLES"]]
            if required_missing:
                result.add_fail("Golden flow cross-check", f"Missing required elements: {', '.join(required_missing)}")
            else:
                result.add_pass("Golden flow cross-check: All required elements present")
        except ET.ParseError:
            result.add_fail("Golden flow cross-check", "Failed to parse golden flow")

    # Print and save report
    result.print_report()
    if report_path:
        result.write_report(report_path)
        print(f"Report saved to: {report_path}")

    return result


def validate_directory(dir_path, golden_path=None, report_dir=None, test_case_dir=None):
    """Validate all XML files in a directory."""
    xml_files = sorted(glob.glob(os.path.join(dir_path, "*.xml")))
    if not xml_files:
        print(f"No XML files found in {dir_path}")
        return []

    results = []
    for xml_path in xml_files:
        report_path = None
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"report_{os.path.splitext(os.path.basename(xml_path))[0]}.txt")
        result = validate_file(xml_path, golden_path, report_path, test_case_dir)
        results.append(result)

    print(f"\n{'='*72}")
    print(f"  Directory Summary: {dir_path}")
    print(f"{'='*72}")
    total_pass = sum(len(r.passes) for r in results)
    total_fail = sum(len(r.fails) for r in results)
    total_skip = sum(len(r.skips) for r in results)
    for r in results:
        status = "PASS" if not r.fails else "FAIL"
        print(f"  [{status}] {r.filename}: {len(r.passes)}P / {len(r.fails)}F / {len(r.skips)}S")
    print(f"\n  Total: {total_pass} PASS, {total_fail} FAIL, {total_skip} SKIP")
    print(f"{'='*72}\n")

    return results


# ─── Entry Point ─────────────────────────────────────────────────────────────

GOLDEN_FLOW_DIR = r"C:\validation\windows-test-content\usb\Galaxy"

def main():
    parser = argparse.ArgumentParser(description="Galaxy XML Validator for FV-USB")
    parser.add_argument("--file", help="Path to a single XML file to validate")
    parser.add_argument("--dir", help="Path to a directory of XML files to validate")
    parser.add_argument("--golden", help="Path to golden flow XML (auto-detected if not provided)")
    parser.add_argument("--report", help="Path to save a single-file report")
    parser.add_argument("--report-dir", help="Directory to save per-file reports (for --dir mode)")
    parser.add_argument("--test-case-dir", help="Directory containing peer XML files for cross-check")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix all standardization issues (Phase 1: text replacements, "
                             "Phase 2: TESTCONFIG cleanup, Phase 3: residency naming)")
    parser.add_argument("--fix-phase", type=int, choices=[1, 2, 3],
                        help="Run only a specific fix phase (1=text, 2=TESTCONFIG, 3=residency)")
    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)

    # Auto-find golden flow
    golden_path = args.golden
    if golden_path is None:
        golden_matches = glob.glob(os.path.join(GOLDEN_FLOW_DIR, "USB_Golden_Flow_ww*.xml"))
        if golden_matches:
            golden_path = sorted(golden_matches)[-1]  # Latest ww

    if args.fix or args.fix_phase:
        if args.file:
            files = [args.file]
        elif args.dir:
            files = sorted(glob.glob(os.path.join(args.dir, "*.xml")))
        else:
            parser.print_help()
            sys.exit(1)

        phase = args.fix_phase  # None means all phases
        total_fixes = 0

        for xml_path in files:
            fn = os.path.basename(xml_path)
            file_fixes = 0

            if phase is None or phase == 0:
                # Structural fixes (original)
                if fix_root_structure(xml_path):
                    print(f"  [FIX] {fn}: Removed ATTRIBUTES block")
                    file_fixes += 1
                if fix_variables_formatting(xml_path):
                    print(f"  [FIX] {fn}: Reformatted VARIABLES section")
                    file_fixes += 1

            if phase is None or phase == 1:
                counts = fix_text_replacements(xml_path)
                if counts:
                    detail = ", ".join(f"{k}:{v}" for k, v in counts.items())
                    n = sum(counts.values())
                    print(f"  [FIX] {fn}: Phase 1 - {n} text fixes ({detail})")
                    file_fixes += n

            if phase is None or phase == 3:
                n = fix_residency_naming(xml_path)
                if n:
                    print(f"  [FIX] {fn}: Phase 3 - {n} residency naming fixes")
                    file_fixes += n
                n = fix_inner_arg_values(xml_path)
                if n:
                    print(f"  [FIX] {fn}: Phase 3b - {n} inner Arg value fixes")
                    file_fixes += n

            if phase is None or phase == 2:
                n = fix_testconfig_cleanup(xml_path)
                if n:
                    print(f"  [FIX] {fn}: Phase 2 - {n} unreferenced CHECKERs deleted")
                    file_fixes += n

            if file_fixes:
                total_fixes += file_fixes
            else:
                print(f"  [OK]  {fn}: No fixes needed")

        print(f"\n  Total: {total_fixes} fixes applied across {len(files)} files")
        return

    if args.file:
        test_case_dir = args.test_case_dir or os.path.dirname(args.file)
        validate_file(args.file, golden_path, args.report, test_case_dir)

    if args.dir:
        test_case_dir = args.test_case_dir or args.dir
        report_dir = args.report_dir or args.dir
        validate_directory(args.dir, golden_path, report_dir, test_case_dir)


if __name__ == "__main__":
    main()
