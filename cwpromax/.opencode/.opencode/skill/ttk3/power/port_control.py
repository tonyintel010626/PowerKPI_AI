#!/usr/bin/env python3
"""Control individual power ports via TTK3 PowerControl.

Usage:
    python port_control.py --action on --port 1
    python port_control.py --action off --port 2
    python port_control.py --action status --port 1
    python port_control.py --action on --port 1,2,3
    python port_control.py --action all-off
    python port_control.py --action all-on
    python port_control.py --source atx --action on --port 1

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
"""

import argparse
import json
import sys

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def port_control(action, ports=None, source="splitter"):
    """Control power ports.

    Args:
        action: "on", "off", "status", "all-on", "all-off".
        ports: List of port numbers (required for on/off/status).
        source: Power source - "splitter" or "atx".

    Returns:
        dict with results per port.
    """
    from PowerControl import PowerControl

    result = {
        "status": "unknown",
        "source": source,
        "action": action,
        "ports": {},
    }

    power = PowerControl()
    try:
        if source == "splitter":
            power.OpenPowerSplitter()
        elif source == "atx":
            power.OpenATX()
        else:
            result["status"] = "error"
            result["error"] = f"Unknown source: {source}"
            return result

        if action == "all-on":
            power.AllPortsOn()
            result["status"] = "success"
            result["result"] = "all_ports_on"

        elif action == "all-off":
            power.AllPortsOff()
            result["status"] = "success"
            result["result"] = "all_ports_off"

        elif action in ("on", "off", "status"):
            if not ports:
                result["status"] = "error"
                result["error"] = "Port number(s) required for on/off/status"
                return result

            for port_num in ports:
                try:
                    if action == "on":
                        power.PortOn(port_num)
                        result["ports"][str(port_num)] = "turned_on"
                    elif action == "off":
                        power.PortOff(port_num)
                        result["ports"][str(port_num)] = "turned_off"
                    elif action == "status":
                        state = power.GetPortState(port_num)
                        result["ports"][str(port_num)] = str(state)
                except Exception as e:
                    result["ports"][str(port_num)] = f"error: {e}"

            result["status"] = "success"

        else:
            result["status"] = "error"
            result["error"] = f"Unknown action: {action}"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        try:
            power.Close()
        except Exception:
            pass

    return result


def main():
    parser = argparse.ArgumentParser(description="Control TTK3 power ports")
    parser.add_argument("--action", required=True,
                        choices=["on", "off", "status", "all-on", "all-off"],
                        help="Action to perform")
    parser.add_argument("--port", help="Port number(s), comma-separated (e.g., 1 or 1,2,3)")
    parser.add_argument("--source", choices=["splitter", "atx"], default="splitter",
                        help="Power source (default: splitter)")

    args = parser.parse_args()

    ports = None
    if args.port:
        ports = [int(p.strip()) for p in args.port.split(",")]

    result = port_control(
        action=args.action,
        ports=ports,
        source=args.source,
    )

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
