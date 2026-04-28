"""
system_info_merged.py

Merged from:
  - system_info.py          : PythonSV-based stepping/QDF/VisualID collection → C:\temp\sys_info.csv
  - generate_system_info.py : Hopper JobIdentDUT class for board info, IFWI env, dummy workload
  - commands.txt            : Extended fuse_utils commands (PCH QDF/VID, fuse revisions, full report)
                              + project/target info + product-aware per-die stepping collection

Product-aware die stepping dispatch
-------------------------------------
  MTL (Meteorlake)  : compute0, soc.north, soc.south, ioe, gcd
  PTL (Pantherlake) : compute0, soc, gdie
  Others            : socket0-level stepping only

Usage (standalone / Hopper):
    python system_info_merged.py [hopper args]
"""

import os
import sys
import re
import time
import shlex
import platform
import subprocess
import threading
import random
import winreg
from timeit import default_timer as timer

import pandas as pd

# PythonSV / IPC imports (available in SUT environment)
from debug.domains.fuse import fuse_utils
from debug import core
import debug
import ipccli
from namednodes import sv

# Hopper imports (available in Hopper/NGA environment)
from hopper.pnp.core.dut import JobIdentDUT
from hopper.base.num import unit
import hopper.base.pythonsv.global_var as global_var
import hopper.base.clogging as clogging
from ping3 import ping, verbose_ping

# ---------------------------------------------------------------------------
# Globals expected by system_info.py environment
# ---------------------------------------------------------------------------
globals()['hub'] = hub  # noqa: F821  (hub is injected by the IPC environment)

# ---------------------------------------------------------------------------
# Helper – shared by standalone mode and the Hopper execute() method
# ---------------------------------------------------------------------------

SYSTEM_INFO_PATH = r'C:\temp'


def store_system_info(name, value):
    """Validate and package a single system-info key/value pair."""
    if value is None or value == '' or value == 'None':
        raise Exception("{} has value {}".format(name, value))
    return {'Name': name, 'Value': value}


def _safe_get(label, fn, sys_info_list):
    """Call fn(), append result to sys_info_list, swallow errors gracefully."""
    try:
        value = fn()
        sys_info_list.append(store_system_info(label, str(value)))
    except Exception as exc:
        print("WARNING: could not collect '{}': {}".format(label, exc))


def _collect_die_steppings(product, sys_info_list):
    """
    Collect per-die steppings based on the detected product family.

    Die layout differs by product:
      MTL (Meteorlake)  : compute0, soc.north, soc.south, ioe, gcd
      PTL (Pantherlake) : compute0, soc, gdie
      Other products    : only socket0-level stepping (already collected above)

    The product string is lower-cased for comparison (e.g. 'mtl', 'ptl').
    """
    p = str(product).lower() if product else ''

    if 'mtl' in p:
        # Meteorlake multi-die layout
        _safe_get('Stepping_Compute',  lambda: sv.socket0.compute0.target_info.stepping, sys_info_list)
        _safe_get('Stepping_SOC_North', lambda: sv.socket0.soc.north.target_info.stepping, sys_info_list)
        _safe_get('Stepping_SOC_South', lambda: sv.socket0.soc.south.target_info.stepping, sys_info_list)
        _safe_get('Stepping_IOE',       lambda: sv.socket0.ioe.target_info.stepping,       sys_info_list)
        _safe_get('Stepping_GCD',       lambda: sv.socket0.gcd.target_info.stepping,       sys_info_list)

    elif 'ptl' in p:
        # Pantherlake multi-die layout
        _safe_get('Stepping_Compute',  lambda: sv.socket0.compute0.target_info.stepping, sys_info_list)
        _safe_get('Stepping_SOC',      lambda: sv.socket0.soc.target_info.stepping,      sys_info_list)
        _safe_get('Stepping_GDIE',     lambda: sv.socket0.gdie.target_info.stepping,     sys_info_list)

    else:
        # Single-die / unknown product — no additional per-die steppings needed
        print("INFO: Product '{}' – no additional per-die stepping collection defined.".format(p))


def collect_pythonsv_info():
    """
    Use PythonSV / fuse_utils to collect comprehensive system information
    and write the results to C:\\temp\\sys_info.csv.

    Collected fields
    ----------------
    Fuse / QDF:
      - CPU QDF, PCH QDF
      - CPU Visual ID, PCH Visual ID
      - CPU Fuse Revision, PCH Fuse Revision
      - Full fuse report printed to stdout

    Project / target info:
      - DeviceName  (e.g. MTLS681, PTLH484)
      - Product     (e.g. mtl, ptl, adl, tgl, arl)
      - Variant     (e.g. p, m, s)
      - Stepping    (socket0-level, e.g. a0, b0)
      - PCH Stepping

    Per-die steppings (product-aware):
      - MTL: compute0, soc.north, soc.south, ioe, gcd
      - PTL: compute0, soc, gdie
      - Others: socket0-level only

    Returns the list of collected info dicts.
    """
    if not os.path.exists(SYSTEM_INFO_PATH):
        os.makedirs(SYSTEM_INFO_PATH)

    sysinfo_filename = os.path.join(SYSTEM_INFO_PATH, 'sys_info.csv')

    if os.path.isfile(sysinfo_filename):
        os.remove(sysinfo_filename)

    itp = ipccli.baseaccess()
    itp.unlock()
    sv.refresh()

    sys_info_list = []

    # ------------------------------------------------------------------
    # 1. Full fuse report (printed to stdout only – too verbose for CSV)
    # ------------------------------------------------------------------
    try:
        print("=== fuse_utils.print_report() ===")
        fuse_utils.print_report()
    except Exception as exc:
        print("WARNING: fuse_utils.print_report() failed: {}".format(exc))

    # ------------------------------------------------------------------
    # 2. QDF – CPU and PCH
    # ------------------------------------------------------------------
    _safe_get('CPU_QDF', fuse_utils.qdf,     sys_info_list)
    _safe_get('PCH_QDF', fuse_utils.qdf_pch, sys_info_list)

    # ------------------------------------------------------------------
    # 3. Visual ID – CPU and PCH
    # ------------------------------------------------------------------
    _safe_get('CPU_VisualID', fuse_utils.visual_ID,      sys_info_list)
    _safe_get('PCH_VisualID', fuse_utils.pch_visual_ID,  sys_info_list)

    # ------------------------------------------------------------------
    # 4. Fuse Revision – CPU and PCH
    # ------------------------------------------------------------------
    _safe_get('CPU_FuseRev', fuse_utils.fuserev,     sys_info_list)
    _safe_get('PCH_FuseRev', fuse_utils.pch_fuserev, sys_info_list)

    # ------------------------------------------------------------------
    # 5. Project / target info
    # ------------------------------------------------------------------
    _safe_get('DeviceName',   lambda: sv.socket0.target_info.device_name, sys_info_list)
    _safe_get('Product',      lambda: sv.socket0.target_info.product,     sys_info_list)
    _safe_get('Variant',      lambda: sv.socket0.target_info.variant,     sys_info_list)
    _safe_get('Stepping',     lambda: sv.socket0.target_info.stepping,    sys_info_list)
    _safe_get('PCH_Stepping', lambda: sv.pch0.target_info.stepping,       sys_info_list)

    # ------------------------------------------------------------------
    # 6. Per-die steppings – product-aware dispatch
    # ------------------------------------------------------------------
    try:
        product = sv.socket0.target_info.product
    except Exception:
        product = ''
    _collect_die_steppings(product, sys_info_list)

    # ------------------------------------------------------------------
    # 7. Save to CSV
    # ------------------------------------------------------------------
    print("System info list: {}".format(sys_info_list))

    df = pd.DataFrame(sys_info_list, columns=['Name', 'Value'])
    df.set_index('Name').to_csv(sysinfo_filename)

    print("System info saved to {}".format(sysinfo_filename))
    return sys_info_list


# ---------------------------------------------------------------------------
# Hopper job class (from generate_system_info.py) with PythonSV info merged in
# ---------------------------------------------------------------------------

class SystemInfoGeneration(JobIdentDUT):
    """System Information Generation Job.

    Combines:
      * Board-info / IFWI-env collection (original generate_system_info.py)
      * PythonSV stepping / QDF / VisualID collection (original system_info.py)
    """

    def __init__(self, job='system_information', duration=2 * unit.s,
                 quiesce=1 * unit.s, **kwargs):
        super().__init__(job=job, duration=duration, quiesce=quiesce, **kwargs)

        self.parser.add_argument(
            '-wt_upload_to_cm', '--wait_time_upload_cmlab',
            help='wait time for boardinfo upload into cmlab',
            type=int, default=240)
        self.parser.add_argument(
            '-no_board', '--no_board_info',
            help='No board info', default=False, action='store_true')
        self.parser.add_argument(
            '-ifwi_env', '--ifwi_environment',
            help='IFWI environment variable value', default='')
        self.parser.add_argument(
            '-auto_ifwi', '--auto_ifwi',
            help='Auto retrieve ifwi from environment variable',
            default=False, action='store_true')

        self.module = 'pnpauto.system_info_generation'
        self.wait_time = 0
        self.auto_ifwi = False
        self.no_board_info = False

    # ------------------------------------------------------------------
    # Registry helper (from generate_system_info.py)
    # ------------------------------------------------------------------

    def get_env_from_registry(self, var_name):
        """Read an environment variable from the Windows registry."""
        # User variables
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
                value, _ = winreg.QueryValueEx(key, var_name)
                return value
        except FileNotFoundError:
            pass

        # System variables
        try:
            with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment') as key:
                value, _ = winreg.QueryValueEx(key, var_name)
                return value
        except FileNotFoundError:
            pass

        return None

    # ------------------------------------------------------------------
    # Setup (from generate_system_info.py, unchanged)
    # ------------------------------------------------------------------

    def setup(self):
        self.wait_time = self.args.wait_time_upload_cmlab
        self.no_board_info = True  # self.args.no_board_info
        self.comm_type = self.args.communicator_type
        reg_setup_file = self.pythonsv.args.reg_setup
        self.auto_ifwi = self.args.auto_ifwi

        no_board_info_file = os.path.join(
            os.path.dirname(reg_setup_file), 'no_board_info.txt')
        if os.path.isfile(no_board_info_file):
            self.no_board_info = True
            print("Found no_board_info.txt – skipping board info collection")

        print("reg setup: {}".format(reg_setup_file))

        ifwi_info_filename = os.path.join(SYSTEM_INFO_PATH, 'ifwi_info.txt')

        if os.path.isfile(ifwi_info_filename) and self.args.ifwi_environment != '':
            os.remove(ifwi_info_filename)

        ifwi_info = self.args.ifwi_environment
        if ifwi_info != '':
            with open(ifwi_info_filename, 'w') as fh:
                fh.write("IFWI={}".format(ifwi_info))
        else:
            if self.auto_ifwi:
                try:
                    ifwi_info = self.get_env_from_registry('TTK_LATEST_IMAGE')
                    if ifwi_info:
                        with open(ifwi_info_filename, 'w') as fh:
                            fh.write("IFWI={}".format(ifwi_info))
                except Exception:
                    raise Exception(
                        "Failed to retrieve TTK_LATEST_IMAGE from environment variable")

    # ------------------------------------------------------------------
    # Dummy workload helper (from generate_system_info.py, unchanged)
    # ------------------------------------------------------------------

    def run_dummy_wl(self):
        if self.comm_type != 'efi' and self.no_board_info is False:
            wl_to_run = (
                'start /wait cmd /c python -m '
                'hopper.pnp.workloads.perf.cinebench.cinebench_23 '
                '-mt -dbg --skip_time_sync -forcewlstop -dur 60s '
                '-comm_type {}'.format(self.comm_type)
            )
            output = os.system(wl_to_run)
            clogging.info("Dummy workload exit code: {}".format(output))

    # ------------------------------------------------------------------
    # Execute – merged: board info + PythonSV system info collection
    # ------------------------------------------------------------------

    def execute(self):
        # 1. Start dummy workload in background (original behaviour)
        d = threading.Thread(target=self.run_dummy_wl, args=())
        d.start()
        time.sleep(2)

        # 2. Board info collection (original generate_system_info.py logic)
        if self.no_board_info is False:
            clogging.info("Running BoardInfo")
            command_to_run = r"python C:\\SVSHARE\\BoardInfo\\BoardInfo.py"
            cmd_array = shlex.split(command_to_run)
            output = ""
            try:
                clogging.info(
                    "Start boardinfo with timeout 180s: {}".format(cmd_array))
                output = subprocess.run(cmd_array, timeout=180)
                clogging.info("BoardInfo completed successfully")
            except subprocess.TimeoutExpired:
                print("BoardInfo timed out and was terminated")
            clogging.info(output)
            if output != 0:
                d.join()
            time.sleep(self.wait_time)

        d.join()

        # 3. PythonSV stepping / QDF / VisualID collection (from system_info.py)
        try:
            clogging.info("Collecting PythonSV system info (stepping/QDF/VisualID)…")
            collect_pythonsv_info()
            clogging.info("PythonSV system info collection complete")
        except Exception as exc:
            clogging.info("WARNING: PythonSV system info collection failed: {}".format(exc))

        # 4. Disconnect IPC session
        try:
            ipccli.ipc_env.ipc_baseaccess.py2ipc.IPC_Disconnect()
        except Exception:
            pass  # Not fatal – may already be disconnected


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    SystemInfoGeneration().main(argv)


if __name__ == '__main__':
    main()
