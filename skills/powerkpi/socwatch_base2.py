#!/usr/bin/python
"""socwatch_base2.py — standalone SocWatch CSV post-processor.

Parses a SocWatch CSV file and merges the results into an existing results.json.
This script replicates the parse_csv_log_output / update_socwatch_result logic
from socwatch_base.py but runs entirely standalone (no hopper runtime required).

Usage:
    python socwatch_base2.py --csv <path_to_socwatch.csv> --results <path_to_results.json>

Output:
    Writes updated results.json in-place with socwatch data merged under:
      - results["socwatch"]                          : flat {table: {row: {col: value}}} dict
      - results["hopper"]["subtests"][N]["result_groups"][M]["results"]  : list of result entries
        (where result_group name == "socwatch")
      - results["socwatch_timing"]                   : timing metadata from the CSV header
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import glob
import os

# ---------------------------------------------------------------------------
# Unit helpers (lightweight — no pint dependency)
# ---------------------------------------------------------------------------

UNIT_SUFFIXES = {
    "(mW)":      "mW",
    "(per sec)": "cps",
    "(ms)":      "ms",
    "(msec)":    "ms",
    "(%)":       "%",
    "(us)":      "us",
    "(ns)":      "ns",
    "(oC)":      "degC",
}


def _extract_unit(col_header: str) -> Optional[str]:
    """Return unit string from a column header like 'Residency (%)' → '%'."""
    m = re.search(r"\(([^)]+)\)", col_header)
    if m:
        key = f"({m.group(1)})"
        return UNIT_SUFFIXES.get(key)
    return None


def _cast(value: str) -> Any:
    """Try to cast a string to int or float; return original string if not possible."""
    stripped = value.strip()
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return stripped


# ---------------------------------------------------------------------------
# CSV parser  (mirrors parse_csv_log_output from socwatch_base.py)
# ---------------------------------------------------------------------------

def parse_csv(csv_path: str, output_str: str = "default") -> Dict[str, Any]:
    """Parse a SocWatch CSV file into a nested dict.

    Returns:
        {
          "parsed": {output_str: {table_name: {row_label: {col_header: value}}}},
          "meta":   {collection_start, duration_sec, clock_freq_mhz, ...}
        }
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [line.rstrip("\n") for line in f]

    meta: Dict[str, Any] = {}
    all_tables: list = []          # list of [header_line, col_line, *data_lines]

    i = 0
    while i < len(lines):
        line = lines[i]

        # ---- extract metadata from the file header ----
        ll = line.lower()
        if "data collection started:" in ll:
            m = re.search(r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})", line)
            if m:
                meta["collection_start"] = m.group(1)
                meta["collection_start_tz"] = "UTC" if "gmt" in ll else "unknown"

        elif "qpc clock frequency" in ll:
            m = re.search(r"([\d.]+)", line)
            if m:
                unit_m = re.search(r"\(([^)]+)\)", line)
                meta["clock_freq"] = float(m.group(1))
                meta["clock_freq_unit"] = unit_m.group(1) if unit_m else "MHz"

        elif "collection duration (sec):" in ll:
            m = re.search(r"([\d.]+)", line)
            if m:
                meta["duration_sec"] = float(m.group(1))

        elif "collection begin timestamp:" in ll:
            m = re.search(r"(\d+)", line)
            if m:
                meta["collection_begin_ts"] = int(m.group(1))

        elif "collection end timestamp:" in ll:
            m = re.search(r"(\d+)", line)
            if m:
                meta["collection_end_ts"] = int(m.group(1))

        # ---- detect table start: previous line blank, current non-blank,
        #      line i+2 is dashes (contains comma + dash) ----
        if (i > 0
                and lines[i - 1] == ""
                and line != ""
                and i + 2 < len(lines)
                and "," in lines[i + 2]
                and "-" in lines[i + 2]):

            table_rows = []
            j = i
            while j < len(lines):
                if lines[j] == "":
                    break
                # skip the dashes row (i+2 relative to table start)
                if j != i + 2:
                    table_rows.append(lines[j])
                j += 1

            if len(table_rows) >= 2:          # must have at least header + col_keys
                all_tables.append(table_rows)
            i = j
            continue

        i += 1

    # ---- build result dict from tables ----
    results: Dict[str, Any] = {}

    for table_rows in all_tables:
        header_name = table_rows[0].strip()
        col_keys_raw = [x.strip() for x in table_rows[1].split(",")]
        # first column is always the row-label column — remove from keys
        col_keys_raw.pop(0)
        col_units = [_extract_unit(k) for k in col_keys_raw]

        table_dict: Dict[str, Any] = {}
        empty_first_col_detected = False
        empty_col_shift = False

        for row_line in table_rows[2:]:
            parts = [x.strip() for x in row_line.split(",")]

            # handle tables with an empty first column
            if parts[0] == "":
                if len(parts) > 1 and parts[1] == "Overall Platform Activity":
                    row_label = "Overall Platform Activity"
                    parts.pop(0)
                else:
                    empty_first_col_detected = True
                    parts.pop(0)
                    row_label = parts.pop(0) if parts else ""
            else:
                if parts[0] == "Total" and empty_col_shift:
                    row_label = parts.pop(0)
                    parts.pop(0)   # remove extra empty col
                else:
                    row_label = parts.pop(0)

            if empty_first_col_detected and not empty_col_shift:
                if col_keys_raw:
                    col_keys_raw.pop(0)
                    col_units.pop(0)
                empty_col_shift = True

            # cast values
            cast_parts = [_cast(p) for p in parts]

            # apply units as suffix strings (keep numeric value separate)
            row_data: Dict[str, Any] = {}
            for idx, col_key in enumerate(col_keys_raw):
                if idx >= len(cast_parts):
                    break
                val = cast_parts[idx]
                u = col_units[idx] if idx < len(col_units) else None
                if u and isinstance(val, (int, float)):
                    row_data[col_key] = {"value": val, "unit": u}
                else:
                    row_data[col_key] = val

            # deduplicate row labels
            if row_label in table_dict:
                n = 0
                while f"{row_label}_{n}" in table_dict:
                    n += 1
                row_label = f"{row_label}_{n}"

            table_dict[row_label] = row_data

        results[header_name] = table_dict

    return {"parsed": {output_str: results}, "meta": meta}


# ---------------------------------------------------------------------------
# Flatten parsed results into a list of result entries (hopper schema)
# ---------------------------------------------------------------------------

def build_result_entries(parsed_tables: Dict[str, Any]) -> list:
    """Convert nested parsed dict into a flat list of result dicts.

    Each entry follows the hopper results.json schema:
        {"name": <str>, "value": <num_or_str>, "unit": <str>, "type": <str>}
    """
    entries = []
    for table_name, table_dict in parsed_tables.items():
        for row_label, row_data in table_dict.items():
            if not isinstance(row_data, dict):
                continue
            for col_key, col_val in row_data.items():
                name = f"{table_name} : {row_label} : {col_key}"
                if isinstance(col_val, dict) and "value" in col_val:
                    entries.append({
                        "name": name,
                        "value": col_val["value"],
                        "unit": col_val.get("unit", ""),
                        "type": "socwatch",
                    })
                elif isinstance(col_val, (int, float)):
                    entries.append({
                        "name": name,
                        "value": col_val,
                        "unit": "",
                        "type": "socwatch",
                    })
                else:
                    entries.append({
                        "name": name,
                        "value": str(col_val),
                        "unit": "",
                        "type": "socwatch",
                    })
    return entries


# ---------------------------------------------------------------------------
# Merge into results.json
# ---------------------------------------------------------------------------

def merge_into_results(results_path: str, parsed: Dict[str, Any], output_str: str):
    """Read results.json, merge socwatch data, write back in-place."""
    rp = Path(results_path)
    if not rp.exists():
        raise FileNotFoundError(f"results.json not found: {results_path}")

    with open(rp, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables = parsed["parsed"][output_str]
    meta = parsed["meta"]
    result_entries = build_result_entries(tables)

    # 1. Top-level "socwatch" key — flat parsed tables
    data["socwatch"] = tables

    # 2. Top-level "socwatch_timing" key — metadata from CSV header
    data["socwatch_timing"] = meta

    # 3. Inject into hopper subtests result_group named "socwatch"
    #    Walk hopper -> subtests -> result_groups to find the socwatch group
    hopper = data.get("hopper", {})
    subtests = hopper.get("subtests", [])
    injected = False
    for subtest in subtests:
        rgs = subtest.get("result_groups", [])
        for rg in rgs:
            if rg.get("name") == "socwatch":
                rg["results"] = result_entries
                # also update configuration with metadata
                cfg = rg.get("configuration", {})
                cfg.update({
                    "collection_start": meta.get("collection_start"),
                    "duration_sec": meta.get("duration_sec"),
                    "clock_freq_mhz": meta.get("clock_freq"),
                })
                rg["configuration"] = cfg
                injected = True

    if not injected:
        print(
            "WARNING: No 'socwatch' result_group found under hopper.subtests. "
            "Socwatch data only written to top-level 'socwatch' key.",
            file=sys.stderr,
        )

    with open(rp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"OK: Merged {len(result_entries)} socwatch result entries into {rp}")
    print(f"    Tables parsed: {len(tables)}")
    print(f"    Collection start: {meta.get('collection_start')} {meta.get('collection_start_tz', '')}")
    print(f"    Duration: {meta.get('duration_sec')} sec")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse a SocWatch CSV and merge results into results.json"
    )
    parser.add_argument(
        "--csv", 
        default = None,
        help="Path to the SocWatch .csv file (e.g. 20260409T022143-socwatch-default.csv)"
    )
    parser.add_argument(
        "--results", 
        default = None,
        help="Path to the results.json file to update"
    )
    parser.add_argument(
        "--output-str", default="default",
        help="Output string identifier (default: 'default', matches the socwatch capture label)"
    )
    args = parser.parse_args()


    args_csv_pattern = glob.glob('*socwatch-default.csv')[0]
    args_results_pattern = glob.glob('*results.json')[0]
    
    # Base folder (current folder)
    folder = os.getcwd()

    # Build full search paths
    csv_search_path = os.path.join(folder, args_csv_pattern)
    results_search_path = os.path.join(folder, args_results_pattern)

    print("CSV files found:",  csv_search_path)
    print("Results files found:", results_search_path)

    # List all matching files
    if args.csv is None:    
        args.csv = glob.glob(csv_search_path)[0]
    
    if args.results is None:   
        args.results = glob.glob(results_search_path)[0]




    print(f"Parsing CSV: {args.csv}")
    parsed = parse_csv(args.csv, output_str=args.output_str)

    print(f"Merging into: {args.results}")
    merge_into_results(args.results, parsed, output_str=args.output_str)


if __name__ == "__main__":
    main()
