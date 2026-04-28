#!/usr/bin/env python3
"""
Validate Agent and Skill Definition Files

Performs structural validation and reference checks on OpenCode agent (.md)
and skill (SKILL.md) files to ensure they follow project conventions.

Usage:
    python validate_agent.py <file_path> [--project-root <path>]
    python validate_agent.py .opencode/agent/MY-AGENT/MY-AGENT.md
    python validate_agent.py .opencode/skill/my-skill/SKILL.md

Output:
    JSON to stdout with structure:
    {
        "valid": true|false,
        "file": "<path>",
        "file_type": "agent"|"skill",
        "errors": ["..."],
        "warnings": ["..."]
    }
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_AGENT_MODES = {"primary", "subagent", "all"}
VALID_MODEL_PREFIXES = ["github-copilot/"]
VALID_TOOL_NAMES = {
    "list",
    "write",
    "edit",
    "bash",
    "read",
    "grep",
    "glob",
    "webfetch",
    "todowrite",
    "todoread",
    "task",
    "skill",
    "multi_tool_use.parallel",
    "multi_tool_use.sequential",
    "vision",
    "vision_ask",
    "vision_patch",
    # MCP / Playwright / BrowserMCP tool names (dynamically added by plugins)
    "playwright_browser_take_screenshot",
    "playwright_browser_snapshot",
    "playwright_browser_click",
    "playwright_browser_navigate",
    "playwright_browser_type",
    "playwright_browser_fill_form",
    "playwright_browser_evaluate",
    "playwright_browser_press_key",
    "playwright_browser_select_option",
    "playwright_browser_hover",
    "playwright_browser_drag",
    "playwright_browser_file_upload",
    "playwright_browser_handle_dialog",
    "playwright_browser_tabs",
    "playwright_browser_close",
    "playwright_browser_resize",
    "playwright_browser_console_messages",
    "playwright_browser_network_requests",
    "playwright_browser_wait_for",
    "playwright_browser_install",
    "playwright_browser_navigate_back",
    "playwright_browser_run_code",
    "browsermcp_browser_screenshot",
    "browsermcp_browser_snapshot",
    "browsermcp_browser_click",
    "browsermcp_browser_navigate",
    "browsermcp_browser_type",
}
VALID_PERMISSION_NAMES = {
    "write",
    "edit",
    "bash",
    "read",
    "grep",
    "glob",
    "webfetch",
    "mcp-browsermcp",
    "mcp-playwright",
}
VALID_PERMISSION_VALUES = {"allow", "deny"}

AGENT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9\-]+$")
SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9\-]*$")


# ---------------------------------------------------------------------------
# YAML Frontmatter Parser (lightweight, no external dependency)
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """
    Parse YAML-like frontmatter from markdown content.
    Returns (frontmatter_dict, body_text) or (None, content) if no frontmatter.

    This is a simplified parser that handles the subset of YAML used in
    agent/skill definitions. It does NOT handle full YAML spec.
    """
    content = content.strip()
    if not content.startswith("---"):
        return None, content

    # Find closing ---
    end_idx = content.find("\n---", 3)
    if end_idx == -1:
        return None, content

    frontmatter_raw = content[3:end_idx].strip()
    body = content[end_idx + 4 :].strip()

    result = {}
    current_key = None
    current_dict = None
    current_list = None
    indent_stack = []

    for line in frontmatter_raw.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # List item
        if stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            if current_list is not None:
                current_list.append(value)
            continue

        # Key: value pair
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if indent == 0:
                # Top-level key
                current_dict = None
                current_list = None
                if val == "":
                    # Could be a dict or list — peek ahead handled by next iterations
                    result[key] = {}
                    current_key = key
                    current_dict = result[key]
                elif val.lower() in ("true", "false"):
                    result[key] = val.lower() == "true"
                elif val.replace(".", "", 1).isdigit():
                    result[key] = float(val) if "." in val else int(val)
                else:
                    result[key] = val
            elif indent > 0 and current_key:
                if current_dict is not None:
                    if val == "":
                        # Nested dict or start of list
                        current_dict[key] = {}
                    elif val.lower() in ("true", "false"):
                        current_dict[key] = val.lower() == "true"
                    elif val.replace(".", "", 1).isdigit():
                        current_dict[key] = float(val) if "." in val else int(val)
                    else:
                        current_dict[key] = val

        # Check if top-level key starts a list
        if indent == 0 and ":" in stripped:
            key = stripped.partition(":")[0].strip()
            val = stripped.partition(":")[2].strip()
            if val == "":
                # Check if next content is a list
                pass

    # Second pass: detect arrays (instructions field)
    current_key = None
    in_array = False
    for line in frontmatter_raw.split("\n"):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in stripped:
            key = stripped.partition(":")[0].strip()
            val = stripped.partition(":")[2].strip()
            current_key = key
            if val == "" and key == "instructions":
                result[key] = []
                in_array = True
            else:
                in_array = False
        elif in_array and stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            if isinstance(result.get(current_key), list):
                result[current_key].append(value)

    return result, body


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_agent(filepath: str, project_root: str) -> dict:
    """Validate an agent .md file."""
    errors = []
    warnings = []

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        return {
            "valid": False,
            "file": filepath,
            "file_type": "agent",
            "errors": [f"File not found: {filepath}"],
            "warnings": [],
        }

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # --- Parse frontmatter ---
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        errors.append("Missing YAML frontmatter (file must start with --- delimiters)")
        return _result(filepath, "agent", errors, warnings)

    # --- Required fields ---
    if "name" not in frontmatter:
        errors.append("Missing required field: 'name'")
    if "description" not in frontmatter:
        errors.append("Missing required field: 'description'")
    if "mode" not in frontmatter:
        errors.append("Missing required field: 'mode'")

    # --- Name convention ---
    name = frontmatter.get("name", "")
    if name and not AGENT_NAME_PATTERN.match(name):
        warnings.append(
            f"Agent name '{name}' does not follow UPPERCASE-HYPHENATED convention "
            f"(expected pattern: {AGENT_NAME_PATTERN.pattern})"
        )

    # --- Mode validation ---
    mode = frontmatter.get("mode", "")
    if mode and mode not in VALID_AGENT_MODES:
        errors.append(
            f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(VALID_AGENT_MODES))}"
        )

    # --- Model validation ---
    model = frontmatter.get("model", "")
    if model:
        if not any(model.startswith(prefix) for prefix in VALID_MODEL_PREFIXES):
            warnings.append(
                f"Model '{model}' does not start with expected prefix "
                f"({', '.join(VALID_MODEL_PREFIXES)})"
            )

    # --- Temperature validation ---
    temp = frontmatter.get("temperature")
    if temp is not None:
        try:
            t = float(temp)
            if t < 0.0 or t > 2.0:
                errors.append(f"Temperature {t} is out of range [0.0, 2.0]")
        except (ValueError, TypeError):
            errors.append(f"Temperature '{temp}' is not a valid number")

    # --- top_p validation ---
    top_p = frontmatter.get("top_p")
    if top_p is not None:
        try:
            p = float(top_p)
            if p < 0.0 or p > 1.0:
                errors.append(f"top_p {p} is out of range [0.0, 1.0]")
        except (ValueError, TypeError):
            errors.append(f"top_p '{top_p}' is not a valid number")

    # --- Tool validation ---
    tools = frontmatter.get("tool", {})
    if isinstance(tools, dict):
        for tool_name in tools:
            if tool_name not in VALID_TOOL_NAMES:
                warnings.append(f"Unknown tool name in 'tool' section: '{tool_name}'")

    # --- Body validation ---
    if not body or len(body.strip()) < 50:
        errors.append(
            "Agent body (system prompt) is too short or empty. "
            "Must contain meaningful instructions (at least 50 characters)."
        )

    # --- Reference checks ---
    # Check @AGENT-NAME references
    agent_refs = re.findall(r"@([A-Z][A-Z0-9\-]+)", body)
    agent_dir = os.path.join(project_root, ".opencode", "agent")
    for ref in agent_refs:
        # Search for ref.md in agent directory tree
        found = False
        if os.path.isdir(agent_dir):
            for root, dirs, files in os.walk(agent_dir):
                if f"{ref}.md" in files:
                    found = True
                    break
        if not found:
            warnings.append(
                f"Referenced sub-agent @{ref} not found in .opencode/agent/ "
                f"(expected file: {ref}.md)"
            )

    # Check skills_ references
    skill_refs = re.findall(r"skills_([a-z0-9_]+)", body)
    skill_dir = os.path.join(project_root, ".opencode", "skill")
    for ref in skill_refs:
        # Convert underscores to path separators for sub-skills
        skill_path = ref.replace("_", "/")
        # Check if skill directory exists (try exact match first, then parent)
        skill_full = os.path.join(skill_dir, skill_path)
        skill_md = os.path.join(skill_full, "SKILL.md")

        # Also check without sub-path (skills_ttk3_spi -> ttk3/spi or ttk3-spi)
        alt_path = os.path.join(skill_dir, ref.replace("_", "-"))
        alt_md = os.path.join(alt_path, "SKILL.md")

        if not (os.path.isfile(skill_md) or os.path.isfile(alt_md)):
            # Try parent skill (skills_ttk3_spi -> ttk3 skill exists)
            parts = ref.split("_")
            parent_found = False
            for i in range(len(parts), 0, -1):
                parent = "/".join(parts[:i])
                if os.path.isfile(os.path.join(skill_dir, parent, "SKILL.md")):
                    parent_found = True
                    break
                parent_hyphen = "-".join(parts[:i])
                if os.path.isfile(os.path.join(skill_dir, parent_hyphen, "SKILL.md")):
                    parent_found = True
                    break
            if not parent_found:
                warnings.append(
                    f"Referenced skill 'skills_{ref}' not found in .opencode/skill/"
                )

    return _result(filepath, "agent", errors, warnings)


def validate_skill(filepath: str, project_root: str) -> dict:
    """Validate a skill SKILL.md file."""
    errors = []
    warnings = []

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        return {
            "valid": False,
            "file": filepath,
            "file_type": "skill",
            "errors": [f"File not found: {filepath}"],
            "warnings": [],
        }

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # --- Parse frontmatter ---
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        errors.append("Missing YAML frontmatter (file must start with --- delimiters)")
        return _result(filepath, "skill", errors, warnings)

    # --- Required fields ---
    if "name" not in frontmatter:
        errors.append("Missing required field: 'name'")
    if "description" not in frontmatter:
        errors.append("Missing required field: 'description'")

    # --- Name convention ---
    name = frontmatter.get("name", "")
    if name and not SKILL_NAME_PATTERN.match(name):
        warnings.append(
            f"Skill name '{name}' does not follow lowercase-hyphenated convention "
            f"(expected pattern: {SKILL_NAME_PATTERN.pattern})"
        )

    # --- Body validation ---
    if not body or len(body.strip()) < 50:
        errors.append(
            "Skill body is too short or empty. "
            "Must contain meaningful documentation (at least 50 characters)."
        )

    # --- Check for common sections ---
    recommended_sections = ["#"]
    has_heading = bool(re.search(r"^#+\s", body, re.MULTILINE))
    if not has_heading:
        warnings.append(
            "Skill body has no markdown headings. Consider adding structure."
        )

    return _result(filepath, "skill", errors, warnings)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(filepath: str, file_type: str, errors: list, warnings: list) -> dict:
    return {
        "valid": len(errors) == 0,
        "file": filepath,
        "file_type": file_type,
        "errors": errors,
        "warnings": warnings,
    }


def detect_file_type(filepath: str) -> str:
    """Detect if file is an agent or skill definition."""
    basename = os.path.basename(filepath)
    if basename == "SKILL.md":
        return "skill"
    # Check if path contains /agent/
    normalized = filepath.replace("\\", "/")
    if "/agent/" in normalized:
        return "agent"
    if "/skill/" in normalized:
        return "skill"
    # Default: try to parse and detect
    return "agent"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Validate OpenCode agent and skill definition files"
    )
    parser.add_argument(
        "file",
        help="Path to the agent .md or skill SKILL.md file to validate",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root directory (default: auto-detect from file path)",
    )
    parser.add_argument(
        "--type",
        choices=["agent", "skill", "auto"],
        default="auto",
        help="File type to validate as (default: auto-detect)",
    )

    args = parser.parse_args()

    # Auto-detect project root
    project_root = args.project_root
    if project_root is None:
        # Walk up from file to find .opencode directory
        current = os.path.dirname(os.path.abspath(args.file))
        while current != os.path.dirname(current):
            if os.path.isdir(os.path.join(current, ".opencode")):
                project_root = current
                break
            current = os.path.dirname(current)
        if project_root is None:
            project_root = os.getcwd()

    # Detect file type
    file_type = args.type
    if file_type == "auto":
        file_type = detect_file_type(args.file)

    # Validate
    if file_type == "agent":
        result = validate_agent(args.file, project_root)
    else:
        result = validate_skill(args.file, project_root)

    # Output
    print(json.dumps(result, indent=2))

    # Exit code
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
