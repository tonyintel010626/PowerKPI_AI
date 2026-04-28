#!/usr/bin/env python3
"""Power cycle a platform via TTK3 PowerControl.

Usage:
    python power_cycle.py
    python power_cycle.py --source atx
    python power_cycle.py --source pdu --pdu-ip 10.0.0.1 --pdu-user admin --pdu-password pass --pdu-ports 1,2
    python power_cycle.py --delay 5

Steps:
    1. Open power source (PowerSplitter, ATX, or PDU)
    2. AllPortsOff
    3. Wait --delay seconds
    4. AllPortsOn
    5. Close

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected (for PowerSplitter/ATX)
    - Network access (for PDU)
"""

import argparse
import json
import sys
import time

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def power_cycle(source="splitter", delay=3, pdu_ip=None, pdu_user=None, pdu_password=None, pdu_ports=None):
    """Power cycle platform: off → wait → on.

    Args:
        source: Power source type - "splitter", "atx", or "pdu".
        delay: Seconds to wait between off and on.
        pdu_ip: PDU IP address (required if source="pdu").
        pdu_user: PDU username (required if source="pdu").
        pdu_password: PDU password (required if source="pdu").
        pdu_ports: Comma-separated PDU port numbers (required if source="pdu").

    Returns:
        dict with cycle results.
    """
    from PowerControl import PowerControl

    result = {
        "status": "unknown",
        "source": source,
        "delay_seconds": delay,
        "steps": [],
    }

    power = PowerControl()
    try:
        # Open the appropriate power source
        if source == "splitter":
            power.OpenPowerSplitter()
            result["steps"].append("power_splitter_opened")
        elif source == "atx":
            power.OpenATX()
            result["steps"].append("atx_opened")
        elif source == "pdu":
            if not all([pdu_ip, pdu_user, pdu_password, pdu_ports]):
                result["status"] = "error"
                result["error"] = "PDU requires --pdu-ip, --pdu-user, --pdu-password, --pdu-ports"
                return result
            power.OpenPdu(pdu_ip, pdu_user, pdu_password, pdu_ports)
            result["steps"].append("pdu_opened")
        else:
            result["status"] = "error"
            result["error"] = f"Unknown power source: {source}"
            return result

        # Power off
        power.AllPortsOff()
        result["steps"].append("all_ports_off")

        # Wait
        time.sleep(delay)
        result["steps"].append(f"waited_{delay}s")

        # Power on
        power.AllPortsOn()
        result["steps"].append("all_ports_on")

        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        try:
            power.Close()
            result["steps"].append("power_closed")
        except Exception as e:
            result["power_close_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Power cycle platform via TTK3")
    parser.add_argument("--source", choices=["splitter", "atx", "pdu"], default="splitter",
                        help="Power source type (default: splitter)")
    parser.add_argument("--delay", type=int, default=3, help="Seconds between off and on (default: 3)")
    parser.add_argument("--pdu-ip", help="PDU IP address (for --source pdu)")
    parser.add_argument("--pdu-user", help="PDU username (for --source pdu)")
    parser.add_argument("--pdu-password", help="PDU password (for --source pdu)")
    parser.add_argument("--pdu-ports", help="PDU ports, comma-separated (for --source pdu)")

    args = parser.parse_args()

    result = power_cycle(
        source=args.source,
        delay=args.delay,
        pdu_ip=args.pdu_ip,
        pdu_user=args.pdu_user,
        pdu_password=args.pdu_password,
        pdu_ports=args.pdu_ports,
    )

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
