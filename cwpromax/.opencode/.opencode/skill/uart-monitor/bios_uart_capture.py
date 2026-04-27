#!/usr/bin/env python3
"""
BIOS UART Capture Tool — Multi-backend serial port monitor and sender.

Backends (in auto-selection priority order):
  1. RealTerm COM/ActiveX   — win32com.client.Dispatch('realterm.realtermintf')
  2. RealTerm Native CLI    — native realterm.exe /port /baud /capture (1st fallback)
  3. RealTerm CLI + FIRST   — subprocess with realterm.exe for send operations
  4. PySerial               — pure Python serial.Serial() (2nd / ultimate fallback)

Usage:
  python bios_uart_capture.py --port COM8 --baud 115200 --duration 120 --output boot.log
  python bios_uart_capture.py --port COM8 --baud 115200 --live --duration 60 --output boot.log
  python bios_uart_capture.py --port COM8 --baud 115200 --until "Shell>" --output boot.log
  python bios_uart_capture.py --port COM8 --baud 115200 --continuous --output uart.log
  python bios_uart_capture.py --port COM8 --baud 115200 --backend realterm-native --output boot.log
  python bios_uart_capture.py --port COM8 --baud 115200 --send "\\r\\n"
  python bios_uart_capture.py --port COM8,COM9 --baud 115200 --duration 120 --output bios.log,ec.log
  python bios_uart_capture.py --list-ports
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REALTERM_EXE = r"C:\Program Files (x86)\BEL\Realterm\realterm.exe"
REALTERM_PROGID = "realterm.realtermintf"
DEFAULT_BAUD = 115200
DEFAULT_FLOW = 0  # No handshaking (RealTerm default)
CAPTURE_POLL_INTERVAL = 0.1  # seconds — for file tailing in live mode
MAX_DURATION = 86400  # 24 hours safety cap

# ---------------------------------------------------------------------------
# Backend: RealTerm COM/ActiveX (Primary)
# ---------------------------------------------------------------------------


class RealTermCOMBackend:
    """Primary backend — full COM/ActiveX automation via win32com.

    ProgID: 'realterm.realtermintf'
    Requires: pywin32 (pip install pywin32)

    Capabilities: hidden mode, StartCapture/StopCapture, PutString,
    DataTriggerSet, charcount verification, event callbacks.
    """

    def __init__(self):
        self.rt = None
        self._port_open = False

    @staticmethod
    def is_available():
        """Check if COM automation is available."""
        try:
            import win32com.client  # noqa: F401
            return True
        except ImportError:
            return False

    def open_port(self, port_num, baud, flow=DEFAULT_FLOW, visible=False):
        """Open a COM port via RealTerm COM object.

        Args:
            port_num: Integer port number (e.g. 8 for COM8)
            baud: Baud rate (e.g. 115200)
            flow: Flow control (0=none, 2=RTS/CTS, 3=RS485)
            visible: If True, show the RealTerm GUI window
        """
        if self._port_open and self.rt:
            # Port already open — update baud/flow if needed, skip re-open
            try:
                self.rt.baud = baud
                self.rt.FlowControl = flow
            except Exception:
                pass
            return

        import win32com.client

        self.rt = win32com.client.Dispatch(REALTERM_PROGID)
        self.rt.Visible = 1 if visible else 0
        if not visible:
            self.rt.windowstate = 1  # minimized
        self.rt.baud = baud
        self.rt.Port = port_num
        self.rt.FlowControl = flow
        self.rt.LinefeedIsNewline = 1  # Treat LF as newline for BIOS logs
        self.rt.PortOpen = 1
        self._port_open = True

    def start_capture(self, output_file):
        """Begin capturing UART data to a file."""
        if not self.rt:
            raise RuntimeError("Port not open — call open_port() first")
        self.rt.CaptureFile = str(output_file)
        self.rt.StartCapture()

    def stop_capture(self):
        """Stop the active capture."""
        if self.rt:
            try:
                self.rt.StopCapture()
            except Exception:
                pass

    def send(self, text):
        """Send a string over the UART port.

        Args:
            text: String to send. Use \\r\\n for Enter.

        Returns:
            dict with charcount before/after for verification.
        """
        if not self.rt:
            raise RuntimeError("Port not open — call open_port() first")
        before = self.rt.charcount
        self.rt.PutString(text)
        time.sleep(0.05)  # brief settle
        after = self.rt.charcount
        return {"chars_before": before, "chars_after": after, "delta": after - before}

    def send_file(self, filepath, char_delay=3, line_delay=50):
        """Send contents of a file over the UART port.

        Args:
            filepath: Path to the file containing commands to send.
            char_delay: Delay in ms between characters.
            line_delay: Delay in ms between lines.
        """
        if not self.rt:
            raise RuntimeError("Port not open — call open_port() first")
        with open(filepath, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                self.rt.PutString(line + "\r\n")
                time.sleep(line_delay / 1000.0)

    def set_data_trigger(self, pattern):
        """Set a hardware-level data trigger to stop capture on pattern match.

        Args:
            pattern: String pattern to trigger on (e.g. "Shell>").
        """
        if not self.rt:
            raise RuntimeError("Port not open — call open_port() first")
        try:
            # DataTriggerSet(index, prefix, trigger_string, suffix, flags,
            #                enable, stop_capture, send_response)
            self.rt.DataTriggerSet(1, "", pattern, 0, 0, True, True, False)
        except Exception as e:
            _print_stderr(f"[WARN] DataTriggerSet failed: {e}")
        try:
            self.rt.EnableDataTrigger = 1
        except (AttributeError, Exception) as e:
            _print_stderr(f"[WARN] EnableDataTrigger not supported by this RealTerm version: {e}")
            _print_stderr("[INFO] Falling back to software pattern matching.")

    def get_charcount(self):
        """Return the number of characters received since port open."""
        if self.rt:
            return self.rt.charcount
        return 0

    def close(self):
        """Stop capture, close port, and release the COM object."""
        if self.rt:
            try:
                self.rt.StopCapture()
            except Exception:
                pass
            try:
                if self._port_open:
                    self.rt.PortOpen = 0
                    self._port_open = False
            except Exception:
                pass
            try:
                self.rt.Close()
            except Exception:
                pass
            self.rt = None


# ---------------------------------------------------------------------------
# Backend: RealTerm CLI + FIRST param (Fallback)
# ---------------------------------------------------------------------------


class RealTermCLIBackend:
    """Fallback backend — subprocess with realterm.exe and FIRST param.

    Launches a RealTerm instance with capture parameters included in the
    initial command to avoid unreliable FIRST param routing for capture
    setup.  Post-launch commands (stop, send, quit) still use FIRST.
    """

    def __init__(self):
        self._process = None
        self._caption = None
        self._port_open = False
        # Deferred launch config — stored by open_port, used by start_capture
        self._port_num = None
        self._baud = None
        self._flow = DEFAULT_FLOW
        self._visible = True

    @staticmethod
    def is_available():
        """Check if realterm.exe exists on disk."""
        return os.path.isfile(REALTERM_EXE)

    def open_port(self, port_num, baud, flow=DEFAULT_FLOW, visible=True):
        """Store port configuration for deferred launch.

        The actual RealTerm process is launched by start_capture() so that
        capture parameters (capfile, capture=1) are included in the initial
        command line.  This avoids the unreliable FIRST-param routing that
        previously caused 0-byte capture files.

        Args:
            port_num: Integer port number (e.g. 8 for COM8)
            baud: Baud rate
            flow: Flow control
            visible: If False, launch minimized (WINDOWSTATE=1)
        """
        self._caption = f"UARTMonitor_COM{port_num}"
        self._port_num = port_num
        self._baud = baud
        self._flow = flow
        self._visible = visible
        self._port_open = True

    def _send_command(self, *params):
        """Send a command to the running RealTerm instance via FIRST param."""
        cmd = [REALTERM_EXE, "first"] + list(params)
        subprocess.run(cmd, timeout=10, capture_output=True)

    def start_capture(self, output_file):
        """Launch RealTerm with port and capture params in a single command.

        Includes capfile= and capture=1 in the initial launch so that file
        capture begins immediately when the port opens — no FIRST routing
        needed for the critical capture-start step.
        """
        cmd = [
            REALTERM_EXE,
            f"baud={self._baud}",
            f"port={self._port_num}",
            f"flow={self._flow}",
            f"caption={self._caption}",
            f"capfile={output_file}",
            "capture=1",
        ]
        if not self._visible:
            cmd.append("WINDOWSTATE=1")
        self._process = subprocess.Popen(cmd)
        time.sleep(2.0)  # wait for RealTerm to start and begin capture

    def stop_capture(self):
        """Stop the active capture."""
        try:
            self._send_command("capture=0")
        except Exception:
            pass

    def _ensure_process(self):
        """Launch RealTerm (port-only, no capture) if not already running.

        This is needed when send() or send_file() is called without a prior
        start_capture().  The process is launched with port/baud/flow so that
        FIRST-param routing can reach it.
        """
        if self._process is None and self._port_open:
            cmd = [
                REALTERM_EXE,
                f"baud={self._baud}",
                f"port={self._port_num}",
                f"flow={self._flow}",
                f"caption={self._caption}",
            ]
            if not self._visible:
                cmd.append("WINDOWSTATE=1")
            self._process = subprocess.Popen(cmd)
            time.sleep(2.0)

    def send(self, text):
        """Send a string via the running instance."""
        self._ensure_process()
        # Escape special chars for CLI
        escaped = text.replace("\r", "\\r").replace("\n", "\\n")
        self._send_command(f"sendstr={escaped}")
        return {"sent": text}

    def send_file(self, filepath, char_delay=3, line_delay=50):
        """Send file contents via the running instance."""
        self._ensure_process()
        self._send_command(
            f"sendfile={filepath}",
            f"senddly={char_delay}",
        )

    def set_data_trigger(self, pattern):
        """CLI backend does not support data triggers — use capture timeout instead."""
        _print_stderr(f"[WARN] CLI backend does not support DataTrigger. Pattern '{pattern}' ignored.")

    def get_charcount(self):
        """CLI backend cannot read charcount."""
        return -1

    def close(self):
        """Quit the running RealTerm instance."""
        if self._port_open:
            try:
                self._send_command("quit")
            except Exception:
                pass
            self._port_open = False
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None


# ---------------------------------------------------------------------------
# Backend: RealTerm Native CLI (First fallback — standalone capture)
# ---------------------------------------------------------------------------


class RealTermNativeBackend:
    """First fallback backend — native realterm.exe CLI for standalone capture.

    Launches realterm.exe with /port, /baud, /capture parameters directly.
    Unlike RealTermCLIBackend (which sends commands to an existing instance),
    this backend manages a dedicated RealTerm process for capture operations.

    Command format:
        realterm.exe port=N baud=B capture=FILE capfile=FILE flow=F

    Best for: Simple standalone capture, validation engineer workflows,
    environments without pywin32 but with RealTerm installed.

    Limitations:
        - Capture-only (no send operations during capture)
        - No hardware DataTrigger (software pattern matching via wrapper)
        - No charcount verification
    """

    def __init__(self):
        self._process = None
        self._caption = None
        self._port_open = False
        self._capture_file = None

    @staticmethod
    def is_available():
        """Check if realterm.exe exists on disk."""
        return os.path.isfile(REALTERM_EXE)

    def open_port(self, port_num, baud, flow=DEFAULT_FLOW, visible=False):
        """Launch RealTerm with the given port configuration and begin listening.

        Args:
            port_num: Integer port number (e.g. 8 for COM8)
            baud: Baud rate (e.g. 115200)
            flow: Flow control (0=none, 2=RTS/CTS, 3=RS485)
            visible: If True, show the RealTerm GUI window
        """
        self._caption = f"UARTNative_COM{port_num}"
        self._port_num = port_num
        self._baud = baud
        self._flow = flow
        self._visible = visible
        self._port_open = True

    def start_capture(self, output_file):
        """Start capture by launching realterm.exe with capture parameters.

        This launches the RealTerm process with port, baud, and capture file
        configured in a single command. The process runs until stop_capture()
        or close() is called.

        Args:
            output_file: Path to the capture output file.
        """
        if not self._port_open:
            raise RuntimeError("Port not configured — call open_port() first")

        self._capture_file = str(Path(output_file).resolve())

        # Build the native RealTerm CLI command
        cmd = [
            REALTERM_EXE,
            f"baud={self._baud}",
            f"port={self._port_num}",
            f"flow={self._flow}",
            f"capture={self._capture_file}",
            f"capfile={self._capture_file}",
            f"caption={self._caption}",
        ]
        if not self._visible:
            cmd.append("WINDOWSTATE=1")  # minimized

        _print_stderr(f"[INFO] RealTerm Native CLI: {' '.join(cmd)}")
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for RealTerm to initialize and open the port
        time.sleep(2.0)

        # Verify the process is still running (didn't crash on startup)
        if self._process.poll() is not None:
            rc = self._process.returncode
            raise RuntimeError(
                f"RealTerm Native exited immediately with code {rc}. "
                f"Check that COM{self._port_num} is available and not locked."
            )

    def stop_capture(self):
        """Stop the active capture by sending capture=0 via FIRST param."""
        if self._process and self._process.poll() is None:
            try:
                cmd = [REALTERM_EXE, "first", "capture=0"]
                subprocess.run(cmd, timeout=10, capture_output=True)
            except Exception:
                pass

    def send(self, text):
        """Send is not supported by the native capture backend.

        Use realterm-cli or pyserial backend for send operations.
        """
        raise RuntimeError(
            "RealTerm Native backend is capture-only. "
            "Use --backend realterm-cli or --backend pyserial for send operations."
        )

    def send_file(self, filepath, char_delay=3, line_delay=50):
        """Send file is not supported by the native capture backend."""
        raise RuntimeError(
            "RealTerm Native backend is capture-only. "
            "Use --backend realterm-cli or --backend pyserial for send operations."
        )

    def set_data_trigger(self, pattern):
        """Native CLI backend does not support hardware DataTrigger.

        Software pattern matching is handled by the capture wrapper function.
        """
        _print_stderr(
            f"[WARN] Native CLI backend does not support hardware DataTrigger. "
            f"Pattern '{pattern}' will be matched in software by the capture wrapper."
        )

    def get_charcount(self):
        """Native CLI backend cannot read charcount."""
        return -1

    def close(self):
        """Quit the running RealTerm instance and clean up."""
        if self._process and self._process.poll() is None:
            try:
                # Try graceful quit via FIRST param
                cmd = [REALTERM_EXE, "first", "quit"]
                subprocess.run(cmd, timeout=5, capture_output=True)
                # Give it a moment to exit
                time.sleep(0.5)
            except Exception:
                pass
            # Force terminate if still running
            if self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
        self._process = None
        self._port_open = False


# ---------------------------------------------------------------------------
# Backend: PySerial (Live view / ultimate fallback)
# ---------------------------------------------------------------------------


class PySerialBackend:
    """PySerial backend — pure Python serial.Serial() for live monitoring.

    Best for: live console streaming (immediate byte-level output),
    port discovery, and environments without RealTerm.
    """

    def __init__(self):
        self._serial = None
        self._port_open = False

    @staticmethod
    def is_available():
        """Check if pyserial is installed."""
        try:
            import serial  # noqa: F401
            return True
        except ImportError:
            return False

    def open_port(self, port_name, baud, flow=DEFAULT_FLOW, **kwargs):
        """Open a COM port via PySerial.

        Args:
            port_name: Port name string (e.g. 'COM8')
            baud: Baud rate
            flow: Flow control (0=none, 2=RTS/CTS)
        """
        import serial

        rtscts = flow == 2
        self._serial = serial.Serial(
            port=port_name,
            baudrate=baud,
            timeout=0.5,
            rtscts=rtscts,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        self._port_open = True

    def read_line(self, timeout=1.0):
        """Read a single line from the serial port.

        Returns:
            Decoded string or None if timeout.
        """
        if not self._serial:
            return None
        try:
            line = self._serial.readline()
            if line:
                return line.decode("utf-8", errors="replace").rstrip("\r\n")
        except Exception:
            pass
        return None

    def read_bytes(self, count=4096):
        """Read available bytes from the serial port.

        Returns:
            bytes object (may be empty).
        """
        if not self._serial:
            return b""
        try:
            waiting = self._serial.in_waiting
            if waiting > 0:
                return self._serial.read(min(waiting, count))
        except Exception:
            pass
        return b""

    def send(self, text):
        """Send a string over the serial port."""
        if not self._serial:
            raise RuntimeError("Port not open — call open_port() first")
        data = text.encode("utf-8")
        written = self._serial.write(data)
        self._serial.flush()
        return {"bytes_sent": written}

    def send_file(self, filepath, line_delay=50):
        """Send file contents line-by-line."""
        if not self._serial:
            raise RuntimeError("Port not open — call open_port() first")
        with open(filepath, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                self._serial.write((line + "\r\n").encode("utf-8"))
                self._serial.flush()
                time.sleep(line_delay / 1000.0)

    def close(self):
        """Close the serial port."""
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
            self._port_open = False

    # --- Utility ---

    @staticmethod
    def list_ports():
        """List available COM ports with descriptions.

        Returns:
            list of dicts: [{port, description, hwid}, ...]
        """
        import serial.tools.list_ports

        ports = []
        for p in sorted(serial.tools.list_ports.comports(), key=lambda x: x.device):
            ports.append({
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid,
            })
        return ports


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_stop_event = threading.Event()


def _print_stderr(msg):
    """Print a message to stderr (not captured in JSON output)."""
    print(msg, file=sys.stderr, flush=True)


def _timestamp():
    """Return a timestamp string [HH:MM:SS.mmm]."""
    now = datetime.now()
    return now.strftime("[%H:%M:%S.") + f"{now.microsecond // 1000:03d}]"


def _parse_port_number(port_str):
    """Extract integer port number from 'COM8' or '8'."""
    m = re.match(r"(?i)com(\d+)", port_str.strip())
    if m:
        return int(m.group(1))
    try:
        return int(port_str.strip())
    except ValueError:
        raise ValueError(f"Invalid port: {port_str}. Expected 'COM8' or '8'.")


def _parse_escape_sequences(text):
    """Convert escaped \\r \\n \\t sequences to actual characters."""
    return text.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")


def _select_backend(requested=None, live=False):
    """Auto-select the best available backend.

    Priority: RealTerm COM > RealTerm Native CLI > RealTerm CLI > PySerial
    Exception: --live forces PySerial for direct byte reads.

    Args:
        requested: Explicit backend name ('realterm-com', 'realterm-native',
                   'realterm-cli', 'pyserial')
        live: If True, prefer PySerial for immediate console streaming

    Returns:
        Backend instance and its name string.
    """
    if requested:
        requested = requested.lower().strip()
        if requested in ("realterm-com", "com"):
            if RealTermCOMBackend.is_available():
                return RealTermCOMBackend(), "realterm-com"
            raise RuntimeError("RealTerm COM backend requested but pywin32 is not installed.")
        elif requested in ("realterm-native", "native"):
            if RealTermNativeBackend.is_available():
                return RealTermNativeBackend(), "realterm-native"
            raise RuntimeError(
                f"RealTerm Native backend requested but {REALTERM_EXE} not found."
            )
        elif requested in ("realterm-cli", "cli"):
            if RealTermCLIBackend.is_available():
                return RealTermCLIBackend(), "realterm-cli"
            raise RuntimeError(f"RealTerm CLI backend requested but {REALTERM_EXE} not found.")
        elif requested in ("pyserial", "serial"):
            if PySerialBackend.is_available():
                return PySerialBackend(), "pyserial"
            raise RuntimeError("PySerial backend requested but pyserial is not installed.")
        else:
            raise ValueError(f"Unknown backend: {requested}")

    # Live mode prefers PySerial for direct byte reads
    if live and PySerialBackend.is_available():
        return PySerialBackend(), "pyserial"

    # Auto-detect: COM > Native CLI > CLI > PySerial
    if RealTermCOMBackend.is_available():
        return RealTermCOMBackend(), "realterm-com"
    if RealTermNativeBackend.is_available():
        return RealTermNativeBackend(), "realterm-native"
    if RealTermCLIBackend.is_available():
        return RealTermCLIBackend(), "realterm-cli"
    if PySerialBackend.is_available():
        return PySerialBackend(), "pyserial"

    raise RuntimeError(
        "No backend available. Install pywin32 (for RealTerm COM), "
        "ensure realterm.exe exists (for Native/CLI), or pip install pyserial."
    )


def _setup_signal_handler():
    """Set up graceful Ctrl+C handling."""
    def handler(sig, frame):
        _stop_event.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


# ---------------------------------------------------------------------------
# Capture operations
# ---------------------------------------------------------------------------


def capture_realterm(backend, port_num, baud, output_file, duration=None,
                     until_pattern=None, continuous=False, live=False):
    """Capture UART data using a RealTerm backend (COM or CLI).

    For live mode, tails the capture file and prints new lines to console.

    Args:
        backend: RealTermCOMBackend or RealTermCLIBackend instance
        port_num: Integer port number
        baud: Baud rate
        output_file: Path to capture file
        duration: Capture duration in seconds (None for until_pattern or continuous)
        until_pattern: Regex pattern to stop on (None to ignore)
        continuous: If True, run until Ctrl+C
        live: If True, tail the capture file to console
    """
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Touch the file so tailing can start immediately
    output_path.touch()

    backend.open_port(port_num, baud, visible=False)
    backend.start_capture(str(output_path))

    if until_pattern and isinstance(backend, RealTermCOMBackend):
        backend.set_data_trigger(until_pattern)

    start_time = time.time()
    compiled_pattern = re.compile(until_pattern) if until_pattern else None
    file_pos = 0

    _print_stderr(f"[INFO] Capturing on COM{port_num} at {baud} baud -> {output_path}")
    if duration:
        _print_stderr(f"[INFO] Duration: {duration}s")
    if until_pattern:
        _print_stderr(f"[INFO] Stop pattern: {until_pattern}")
    if continuous:
        _print_stderr("[INFO] Continuous mode — press Ctrl+C to stop")

    try:
        while not _stop_event.is_set():
            elapsed = time.time() - start_time

            # Duration check
            if duration and elapsed >= duration:
                _print_stderr(f"[INFO] Duration {duration}s reached. Stopping capture.")
                break

            # Live tailing
            if live and output_path.exists():
                try:
                    with open(output_path, "r", errors="replace") as f:
                        f.seek(file_pos)
                        new_data = f.read()
                        if new_data:
                            file_pos = f.tell()
                            for line in new_data.splitlines():
                                print(f"{_timestamp()} {line}", flush=True)

                            # Pattern check on new data
                            if compiled_pattern and compiled_pattern.search(new_data):
                                _print_stderr(f"[INFO] Pattern '{until_pattern}' matched. Stopping.")
                                break
                except (IOError, OSError):
                    pass

            # Non-live pattern check (periodically read the file)
            elif compiled_pattern and not live:
                try:
                    with open(output_path, "r", errors="replace") as f:
                        f.seek(file_pos)
                        new_data = f.read()
                        if new_data:
                            file_pos = f.tell()
                            if compiled_pattern.search(new_data):
                                _print_stderr(f"[INFO] Pattern '{until_pattern}' matched. Stopping.")
                                break
                except (IOError, OSError):
                    pass

            time.sleep(CAPTURE_POLL_INTERVAL)

    finally:
        backend.stop_capture()
        backend.close()

    # Return capture summary
    file_size = output_path.stat().st_size if output_path.exists() else 0
    line_count = 0
    if output_path.exists():
        with open(output_path, "r", errors="replace") as f:
            line_count = sum(1 for _ in f)

    return {
        "status": "ok",
        "backend": "realterm-com" if isinstance(backend, RealTermCOMBackend) else "realterm-cli",
        "port": f"COM{port_num}",
        "baud": baud,
        "output_file": str(output_path),
        "duration_sec": round(time.time() - start_time, 2),
        "file_size_bytes": file_size,
        "lines_captured": line_count,
    }


def capture_realterm_native(port_num, baud, output_file, duration=None,
                            until_pattern=None, continuous=False, live=False,
                            flow=DEFAULT_FLOW):
    """Capture UART data using RealTerm native CLI (first fallback).

    Launches realterm.exe with port/baud/capture parameters directly as a
    standalone process. Monitors the capture file for duration, pattern match,
    or continuous operation. Supports live tailing of the capture file.

    This is the first fallback when RealTerm COM/ActiveX is not available
    (e.g. pywin32 not installed), but realterm.exe is present on the system.

    Args:
        port_num: Integer port number (e.g. 8 for COM8)
        baud: Baud rate (e.g. 115200)
        output_file: Path to capture output file
        duration: Capture duration in seconds (None for until_pattern or continuous)
        until_pattern: Regex pattern to stop on (None to ignore)
        continuous: If True, run until Ctrl+C
        live: If True, tail the capture file and print to console in real-time
        flow: Flow control (0=none, 2=RTS/CTS, 3=RS485)

    Returns:
        dict with capture summary including status, backend, port, baud,
        output_file, duration_sec, file_size_bytes, lines_captured.
    """
    backend = RealTermNativeBackend()
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Touch the file so tailing can start immediately
    output_path.touch()

    backend.open_port(port_num, baud, flow=flow)
    backend.start_capture(str(output_path))

    start_time = time.time()
    compiled_pattern = re.compile(until_pattern) if until_pattern else None
    file_pos = 0

    _print_stderr(f"[INFO] Capturing on COM{port_num} at {baud} baud -> {output_path}")
    _print_stderr(f"[INFO] Backend: realterm-native (RealTerm CLI)")
    if duration:
        _print_stderr(f"[INFO] Duration: {duration}s")
    if until_pattern:
        _print_stderr(f"[INFO] Stop pattern: {until_pattern}")
    if continuous:
        _print_stderr("[INFO] Continuous mode — press Ctrl+C to stop")

    try:
        while not _stop_event.is_set():
            elapsed = time.time() - start_time

            # Duration check
            if duration and elapsed >= duration:
                _print_stderr(f"[INFO] Duration {duration}s reached. Stopping capture.")
                break

            # Check if RealTerm process is still alive
            if backend._process and backend._process.poll() is not None:
                rc = backend._process.returncode
                _print_stderr(
                    f"[WARN] RealTerm Native process exited unexpectedly (code {rc})."
                )
                break

            # Live tailing of capture file
            if live and output_path.exists():
                try:
                    with open(output_path, "r", errors="replace") as f:
                        f.seek(file_pos)
                        new_data = f.read()
                        if new_data:
                            file_pos = f.tell()
                            for line in new_data.splitlines():
                                print(f"{_timestamp()} {line}", flush=True)

                            # Pattern check on new data
                            if compiled_pattern and compiled_pattern.search(new_data):
                                _print_stderr(f"[INFO] Pattern '{until_pattern}' matched. Stopping.")
                                break
                except (IOError, OSError):
                    pass

            # Non-live pattern check (periodically read the file)
            elif compiled_pattern and not live:
                try:
                    with open(output_path, "r", errors="replace") as f:
                        f.seek(file_pos)
                        new_data = f.read()
                        if new_data:
                            file_pos = f.tell()
                            if compiled_pattern.search(new_data):
                                _print_stderr(f"[INFO] Pattern '{until_pattern}' matched. Stopping.")
                                break
                except (IOError, OSError):
                    pass

            time.sleep(CAPTURE_POLL_INTERVAL)

    finally:
        backend.stop_capture()
        backend.close()

    # Return capture summary
    file_size = output_path.stat().st_size if output_path.exists() else 0
    line_count = 0
    if output_path.exists():
        with open(output_path, "r", errors="replace") as f:
            line_count = sum(1 for _ in f)

    return {
        "status": "ok",
        "backend": "realterm-native",
        "port": f"COM{port_num}",
        "baud": baud,
        "output_file": str(output_path),
        "duration_sec": round(time.time() - start_time, 2),
        "file_size_bytes": file_size,
        "lines_captured": line_count,
    }


def capture_pyserial(port_name, baud, output_file, duration=None,
                     until_pattern=None, continuous=False, live=False):
    """Capture UART data using PySerial with direct byte reads.

    Reads bytes from the serial port, timestamps them, writes to file,
    and optionally prints to console in real-time.

    Args:
        port_name: Port name string (e.g. 'COM8')
        baud: Baud rate
        output_file: Path to output file
        duration: Capture duration in seconds
        until_pattern: Regex pattern to stop on
        continuous: If True, run until Ctrl+C
        live: If True, print to console in real-time
    """
    backend = PySerialBackend()
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    backend.open_port(port_name, baud)
    compiled_pattern = re.compile(until_pattern) if until_pattern else None
    start_time = time.time()
    line_count = 0
    buffer = ""

    _print_stderr(f"[INFO] Capturing on {port_name} at {baud} baud -> {output_path}")
    if duration:
        _print_stderr(f"[INFO] Duration: {duration}s")
    if until_pattern:
        _print_stderr(f"[INFO] Stop pattern: {until_pattern}")
    if continuous:
        _print_stderr("[INFO] Continuous mode — press Ctrl+C to stop")

    try:
        with open(output_path, "w", encoding="utf-8") as fout:
            while not _stop_event.is_set():
                elapsed = time.time() - start_time

                # Duration check
                if duration and elapsed >= duration:
                    _print_stderr(f"[INFO] Duration {duration}s reached. Stopping capture.")
                    break

                # Read available bytes
                raw = backend.read_bytes()
                if raw:
                    text = raw.decode("utf-8", errors="replace")
                    buffer += text

                    # Process complete lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.rstrip("\r")
                        ts = _timestamp()
                        timestamped = f"{ts} {line}"

                        fout.write(timestamped + "\n")
                        fout.flush()
                        line_count += 1

                        if live:
                            print(timestamped, flush=True)

                        # Pattern check
                        if compiled_pattern and compiled_pattern.search(line):
                            _print_stderr(f"[INFO] Pattern '{until_pattern}' matched. Stopping.")
                            _stop_event.set()
                            break

                else:
                    time.sleep(0.01)  # small sleep when no data

            # Flush remaining buffer
            if buffer.strip():
                ts = _timestamp()
                timestamped = f"{ts} {buffer.rstrip()}"
                fout.write(timestamped + "\n")
                line_count += 1
                if live:
                    print(timestamped, flush=True)

    finally:
        backend.close()

    file_size = output_path.stat().st_size if output_path.exists() else 0
    return {
        "status": "ok",
        "backend": "pyserial",
        "port": port_name,
        "baud": baud,
        "output_file": str(output_path),
        "duration_sec": round(time.time() - start_time, 2),
        "file_size_bytes": file_size,
        "lines_captured": line_count,
    }


# ---------------------------------------------------------------------------
# Multi-port capture
# ---------------------------------------------------------------------------


def capture_multi_port(ports, bauds, output_files, duration=None,
                       until_pattern=None, continuous=False, live=False,
                       backend_name=None):
    """Capture from multiple COM ports simultaneously.

    Launches a capture thread per port with synchronized timestamps.

    Args:
        ports: List of port strings (e.g. ['COM8', 'COM9'])
        bauds: List of baud rates (same length as ports, or single value applied to all)
        output_files: List of output file paths (same length as ports)
        duration: Duration per capture
        until_pattern: Pattern to stop on (applied to all ports)
        continuous: Continuous mode
        live: Live console output (prefixed with port name)
        backend_name: Force a specific backend

    Returns:
        List of capture results.
    """
    if len(ports) != len(output_files):
        raise ValueError(f"Port count ({len(ports)}) must match output file count ({len(output_files)})")

    # Expand baud to match port count if single value
    if isinstance(bauds, int):
        bauds = [bauds] * len(ports)
    elif len(bauds) == 1:
        bauds = bauds * len(ports)

    results: list = [None] * len(ports)
    threads = []

    def _capture_thread(idx, port, baud, outfile):
        try:
            backend, name = _select_backend(requested=backend_name, live=live)

            if isinstance(backend, PySerialBackend):
                results[idx] = capture_pyserial(
                    port, baud, outfile,
                    duration=duration, until_pattern=until_pattern,
                    continuous=continuous, live=live,
                )
            elif isinstance(backend, RealTermNativeBackend):
                port_num = _parse_port_number(port)
                results[idx] = capture_realterm_native(
                    port_num, baud, outfile,
                    duration=duration, until_pattern=until_pattern,
                    continuous=continuous, live=live,
                )
            else:
                port_num = _parse_port_number(port)
                results[idx] = capture_realterm(
                    backend, port_num, baud, outfile,
                    duration=duration, until_pattern=until_pattern,
                    continuous=continuous, live=live,
                )
        except Exception as e:
            results[idx] = {"status": "error", "port": port, "error": str(e)}

    for i, (port, baud, outfile) in enumerate(zip(ports, bauds, output_files)):
        t = threading.Thread(target=_capture_thread, args=(i, port, baud, outfile), daemon=True)
        threads.append(t)

    # Start all threads simultaneously for synchronized timestamps
    for t in threads:
        t.start()

    # Wait for all threads (respects Ctrl+C via _stop_event)
    try:
        for t in threads:
            while t.is_alive():
                t.join(timeout=0.5)
                if _stop_event.is_set():
                    break
    except KeyboardInterrupt:
        _stop_event.set()

    return results


# ---------------------------------------------------------------------------
# Send operations
# ---------------------------------------------------------------------------


def send_string(port_name, baud, text, backend_name=None):
    """Send a string over the UART port.

    Args:
        port_name: Port name string (e.g. 'COM8')
        baud: Baud rate
        text: String to send (escape sequences processed)
        backend_name: Force a specific backend

    Returns:
        dict with send result.
    """
    backend, name = _select_backend(requested=backend_name)
    text = _parse_escape_sequences(text)

    try:
        if isinstance(backend, PySerialBackend):
            backend.open_port(port_name, baud)
        else:
            port_num = _parse_port_number(port_name)
            backend.open_port(port_num, baud)

        send_result = backend.send(text)
        return {
            **send_result,
            "backend": name,
            "port": port_name,
            "status": "ok",
        }
    finally:
        backend.close()


def send_file_contents(port_name, baud, filepath, backend_name=None):
    """Send file contents over the UART port.

    Args:
        port_name: Port name string
        baud: Baud rate
        filepath: Path to file with commands
        backend_name: Force a specific backend

    Returns:
        dict with send result.
    """
    if not os.path.isfile(filepath):
        return {"status": "error", "error": f"File not found: {filepath}"}

    backend, name = _select_backend(requested=backend_name)

    try:
        if isinstance(backend, PySerialBackend):
            backend.open_port(port_name, baud)
        else:
            port_num = _parse_port_number(port_name)
            backend.open_port(port_num, baud)

        backend.send_file(filepath)
        return {"status": "ok", "backend": name, "port": port_name, "file_sent": filepath}
    finally:
        backend.close()


# ---------------------------------------------------------------------------
# Port listing
# ---------------------------------------------------------------------------


def list_ports():
    """List available COM ports.

    Returns:
        dict with port list.
    """
    if not PySerialBackend.is_available():
        return {"status": "error", "error": "pyserial not installed — cannot enumerate ports"}

    ports = PySerialBackend.list_ports()
    return {
        "status": "ok",
        "port_count": len(ports),
        "ports": ports,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser():
    """Build the argparse CLI parser."""
    parser = argparse.ArgumentParser(
        description="BIOS UART Capture Tool — multi-backend serial monitor and sender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-ports
  %(prog)s --port COM8 --baud 115200 --duration 120 --output boot.log
  %(prog)s --port COM8 --baud 115200 --live --duration 60 --output boot.log
  %(prog)s --port COM8 --baud 115200 --until "Shell>" --output boot.log
  %(prog)s --port COM8 --baud 115200 --continuous --output uart.log --live
  %(prog)s --port COM8 --baud 115200 --send "\\r\\n"
  %(prog)s --port COM8 --baud 115200 --sendfile commands.txt
  %(prog)s --port COM8,COM9 --baud 115200 --duration 120 --output bios.log,ec.log
        """,
    )

    # Port config
    parser.add_argument("--port", type=str, help="COM port(s), comma-separated for multi-port (e.g. COM8 or COM8,COM9)")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--flow", type=int, default=DEFAULT_FLOW, choices=[0, 2, 3],
                        help="Flow control: 0=none, 2=RTS/CTS, 3=RS485 (default: 0)")

    # Capture options
    parser.add_argument("--output", "-o", type=str, help="Output file path(s), comma-separated for multi-port")
    parser.add_argument("--duration", "-d", type=float, help="Capture duration in seconds")
    parser.add_argument("--until", type=str, help="Stop capture when this regex pattern is matched")
    parser.add_argument("--continuous", action="store_true", help="Continuous capture until Ctrl+C")
    parser.add_argument("--live", action="store_true", help="Print captured data to console in real-time")

    # Send options
    parser.add_argument("--send", type=str, help="Send a string over UART (supports \\\\r \\\\n escapes)")
    parser.add_argument("--sendfile", type=str, help="Send contents of a file over UART")

    # Backend selection
    parser.add_argument("--backend", type=str,
                        choices=["realterm-com", "realterm-native", "realterm-cli", "pyserial"],
                        help="Force a specific backend (default: auto-detect). "
                             "Priority: realterm-com > realterm-native > realterm-cli > pyserial")

    # Utility
    parser.add_argument("--list-ports", action="store_true", help="List available COM ports and exit")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout")

    return parser


def main():
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    _setup_signal_handler()

    # --- List ports ---
    if args.list_ports:
        result = list_ports()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "ok":
                print(f"Found {result['port_count']} COM port(s):\n")
                ports = result["ports"]  # type: ignore[index]
                for port_info in ports:
                    pi: Dict[str, Any] = dict(port_info)  # type: ignore[arg-type]
                    print(f"  {pi['port']:8s}  {pi['description']}")
                    if pi.get("hwid"):
                        print(f"            HWID: {pi['hwid']}")
            else:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
        return

    # --- Send string ---
    if args.send and not args.output:
        if not args.port:
            parser.error("--port is required for --send")
        try:
            result = send_string(args.port, args.baud, args.send, backend_name=args.backend)
            print(json.dumps(result, indent=2))
        except Exception as e:
            err_name = type(e).__name__
            if 'serial' in err_name.lower() or 'com_error' in err_name.lower() or 'port' in str(e).lower():
                _print_stderr(f"Serial port error: {e}")
            else:
                _print_stderr(f"Send failed: {e}")
            sys.exit(1)
        return

    # --- Send file ---
    if args.sendfile and not args.output:
        if not args.port:
            parser.error("--port is required for --sendfile")
        try:
            result = send_file_contents(args.port, args.baud, args.sendfile, backend_name=args.backend)
            print(json.dumps(result, indent=2))
        except Exception as e:
            err_name = type(e).__name__
            if 'serial' in err_name.lower() or 'com_error' in err_name.lower() or 'port' in str(e).lower():
                _print_stderr(f"Serial port error: {e}")
            else:
                _print_stderr(f"Send file failed: {e}")
            sys.exit(1)
        return

    # --- Capture ---
    if not args.port:
        parser.error("--port is required for capture operations")
    if not args.output:
        parser.error("--output is required for capture operations")
    if not args.duration and not args.until and not args.continuous:
        parser.error("Specify --duration, --until, or --continuous for capture")

    # Clamp duration
    if args.duration and args.duration > MAX_DURATION:
        _print_stderr(f"[WARN] Duration clamped to {MAX_DURATION}s (24h safety cap)")
        args.duration = MAX_DURATION

    ports = [p.strip() for p in args.port.split(",")]
    outputs = [o.strip() for o in args.output.split(",")]

    # Multi-port capture
    if len(ports) > 1:
        results = capture_multi_port(
            ports=ports,
            bauds=args.baud,
            output_files=outputs,
            duration=args.duration,
            until_pattern=args.until,
            continuous=args.continuous,
            live=args.live,
            backend_name=args.backend,
        )
        # If --send is combined with capture, send after starting
        # (handled inside capture logic already via pre-send)
        print(json.dumps(results, indent=2))
        return

    # Single-port capture
    port = ports[0]
    output = outputs[0]

    backend, backend_name = _select_backend(requested=args.backend, live=args.live)

    # Handle combined capture + send: send after opening port
    pre_send = args.send
    pre_send_file = args.sendfile

    try:
        if isinstance(backend, PySerialBackend):
            # For PySerial live capture, if there's a pre-send, we wrap it
            if pre_send or pre_send_file:
                # Open port, send, then capture
                backend.open_port(port, args.baud)
                if pre_send:
                    backend.send(_parse_escape_sequences(pre_send))
                    _print_stderr(f"[INFO] Sent: {repr(pre_send)}")
                if pre_send_file:
                    backend.send_file(pre_send_file)
                    _print_stderr(f"[INFO] Sent file: {pre_send_file}")
                backend.close()
                time.sleep(0.1)

            result = capture_pyserial(
                port, args.baud, output,
                duration=args.duration,
                until_pattern=args.until,
                continuous=args.continuous,
                live=args.live,
            )
        elif isinstance(backend, RealTermNativeBackend):
            # RealTerm Native CLI is capture-only; send not supported.
            if pre_send or pre_send_file:
                _print_stderr(
                    "[WARN] RealTerm Native backend does not support send operations. "
                    "Ignoring --send / --sendfile. Use --backend realterm-com or "
                    "--backend realterm-cli for combined send+capture."
                )
            port_num = _parse_port_number(port)
            result = capture_realterm_native(
                port_num, args.baud, output,
                duration=args.duration,
                until_pattern=args.until,
                continuous=args.continuous,
                live=args.live,
            )
        else:
            port_num = _parse_port_number(port)

            # For RealTerm, we can send after opening port but before/during capture
            if pre_send or pre_send_file:
                output_path = Path(output).resolve()
                backend.open_port(port_num, args.baud, visible=False)
                backend.start_capture(str(output_path))
                time.sleep(0.2)
                if pre_send:
                    backend.send(_parse_escape_sequences(pre_send))
                    _print_stderr(f"[INFO] Sent: {repr(pre_send)}")
                if pre_send_file:
                    backend.send_file(pre_send_file)
                    _print_stderr(f"[INFO] Sent file: {pre_send_file}")

                # Continue capturing for remaining duration
                start_time = time.time()
                compiled_pattern = re.compile(args.until) if args.until else None
                file_pos = 0

                try:
                    while not _stop_event.is_set():
                        elapsed = time.time() - start_time
                        if args.duration and elapsed >= args.duration:
                            break
                        if args.live and output_path.exists():
                            try:
                                with open(output_path, "r", errors="replace") as f:
                                    f.seek(file_pos)
                                    new_data = f.read()
                                    if new_data:
                                        file_pos = f.tell()
                                        for line in new_data.splitlines():
                                            print(f"{_timestamp()} {line}", flush=True)
                                        if compiled_pattern and compiled_pattern.search(new_data):
                                            break
                            except (IOError, OSError):
                                pass
                        time.sleep(CAPTURE_POLL_INTERVAL)
                finally:
                    backend.stop_capture()
                    backend.close()

                file_size = output_path.stat().st_size if output_path.exists() else 0
                line_count = 0
                if output_path.exists():
                    with open(output_path, "r", errors="replace") as f:
                        line_count = sum(1 for _ in f)

                result = {
                    "status": "ok",
                    "backend": backend_name,
                    "port": f"COM{port_num}",
                    "baud": args.baud,
                    "output_file": str(output_path),
                    "duration_sec": round(time.time() - start_time, 2),
                    "file_size_bytes": file_size,
                    "lines_captured": line_count,
                    "pre_send": pre_send,
                    "pre_send_file": pre_send_file,
                }
            else:
                result = capture_realterm(
                    backend, port_num, args.baud, output,
                    duration=args.duration,
                    until_pattern=args.until,
                    continuous=args.continuous,
                    live=args.live,
                )
    except Exception as exc:
        exc_name = type(exc).__name__
        if "Serial" in exc_name or "COM" in str(exc).upper() or "port" in str(exc).lower():
            _print_stderr(f"[ERROR] Serial port error: {exc}")
        else:
            _print_stderr(f"[ERROR] Capture failed: {exc}")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
