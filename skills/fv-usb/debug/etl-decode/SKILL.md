---
name: fv-usb/debug/etl-decode
version: 2.0.0
owner: kvejaya
description: USB/UAOL ETL trace decode — always asks where the ETL log is and which system to fetch symbols from before proceeding. Automatically fetches ETL and USB symbol files from SUT via hostname (NGA) or IP address, then decodes and analyzes the trace.
---

# FV-USB — ETL Trace Decode Sub-Skill

## Purpose
Guide the capture, symbol setup, decoding, and analysis of USB/UAOL ETL (Event Trace Logging) traces on Windows. ETL traces are the **primary debug artifact** for USB driver-level issues, UAOL audio glitches, and xHCI command/transfer ring failures.

---

## Critical Agent Behavior Rules

> These rules are **non-negotiable**. Violating any of them degrades the user experience.

1. **USB perspective only** — ETL analysis is ALWAYS from a USB perspective. Never analyze non-USB content (TBT, Audio, Storage, etc.). If the ETL contains no USB events, say so and stop.

2. **Never assume ETL content from filename or folder name** — Do NOT infer what an ETL trace is about based on the file name, folder name, or surrounding files. Only determine content from the **actual decoded trace events**. A file called `tbtLog.etl` might contain USB events; a file called `USBTrace.etl` might be empty. Decode first, then assess.

3. **Be direct** — If there is no ETL on the SUT, say: *"There is no USB ETL file on this SUT."* and stop. Do not ramble, suggest alternatives, or reference unrelated previous work.

4. **If PDBs cannot be obtained, say so immediately** — PDB symbols are the **only way** to decode WPP ETL traces. There is no fallback method. If `symchk` fails to download the PDBs, tell the user: *"Cannot obtain PDB symbols for this SUT. ETL decode is not possible without them."* and stop. Do not spend time searching multiple locations.

5. **Stay on topic** — Never reference previous tasks, other ETL files, other platforms, or other analyses unless the user explicitly asks. Each decode request is independent.

---

## Bundled Tools

The ETL decode toolkit is bundled with this skill at:

```
.opencode/skill/fv-usb/debug/etl-decode/tools/
```

**Contents:**

| File | Purpose |
|------|---------|
| `tracepdb.exe` | Extracts TMF format files from PDB symbols |
| `tracefmt.exe` | Decodes ETL using TMF files → readable text |
| `parseEtl.cmd` | Orchestrates tracepdb + tracefmt pipeline (3 params: ETL_FILE, PDB_DIR, MODE) |
| `parseLocal.cmd` | Shortcut — calls parseEtl.cmd with current dir as PDB dir, detailed mode |
| `wpp.guids` | USB4 WPP provider GUIDs for trace capture |
| `filever.exe` | Extracts file version info from .sys binaries |
| `StartTrace.bat` | Start runtime ETL capture |
| `StopTrace.bat` | Stop runtime ETL capture |
| `Trace.bat` | Interactive capture — start, wait for keypress, stop |
| `StartSingleBootTrace.bat` | Start trace that survives one reboot |
| `StartContinuousBootTrace.bat` | Start trace that survives multiple reboots (append mode) |
| `StopBootTrace.bat` | Stop and finalize boot trace |
| `GetVersions.bat` | Collect USB4 driver version info |
| `CollectEnvironmentInfo.bat` | Copy decode tools + collect versions alongside ETL |
| `Elevate.bat` | UAC elevation helper |

**Agent deployment:** When the SUT does not have the trace toolkit, push these files to the SUT via the EVTAR communicator before starting capture or decode:

```python
TOOLS_DIR = os.path.join(os.path.dirname(__file__), 'tools')
# Or resolve from skill root:
# TOOLS_DIR = r'.opencode\skill\fv-usb\debug\etl-decode\tools'

SUT_DEST = r'C:\temp\Usb4Trace'
comm.ExecuteCommandOnTarget(f'mkdir {SUT_DEST}', 10)
for f in os.listdir(TOOLS_DIR):
    comm.PutFileOnTarget(os.path.join(TOOLS_DIR, f), os.path.join(SUT_DEST, f))
```

---

## USB ETL Tracing — WPP Architecture

USB drivers on Windows use **WPP (Windows software trace Preprocessor)** tracing, NOT standard ETW manifested providers. This fundamentally changes the decode workflow:

| Aspect | Standard ETW | WPP (USB drivers) |
|--------|-------------|-------------------|
| Format strings | Embedded in ETW manifest | Stored in **PDB symbol files** |
| Decode without symbols | Works (manifest is registered) | **Does NOT work** — produces "Unknown" events |
| Symbol requirement | Optional (improves stack traces) | **Mandatory** — no PDB = no decode |
| Decode tool | `tracerpt`, `netsh trace convert` | `tracepdb` (PDB → TMF) then `tracefmt` (ETL + TMF → text) |

**Key implication:** Without PDB files, USB ETL traces decode as 100% "Unknown" / "No Format Information found" events. This is expected behavior, not an error — it means PDBs are missing.

---

## When to Use ETL Traces

| Scenario | Why ETL Helps |
|----------|---------------|
| USB device intermittently disconnects | Shows exact PORTSC transitions and driver responses |
| UAOL audio glitch/stuck | Shows xHCI ↔ ACE handoff, endpoint purge, FIFO state |
| S3/S4 resume device loss | Shows suspend/resume sequence and port power transitions |
| Transfer errors (bulk/isoch) | Shows TRB completions, error codes, retry behavior |
| USB driver crash/BSOD | Shows last commands before failure |
| USB blocking S0ix | Shows which device/port prevented power transition |

---

## ETL Capture Workflow

### Step 1 — Start USB ETL Capture

**Option A: WPP GUID-based capture using logman (RECOMMENDED)**

This is the standard method used by the USB4 trace toolkit. Create a `wpp.guids` file with the USB4/WPP provider GUIDs, then start a trace session using that file.

```powershell
# Start trace using WPP GUID file
logman start USBLogSession -o C:\USBTrace.etl -ets -pf wpp.guids
```

**Option B: Manifested ETW provider capture using logman**

```powershell
logman create trace USBTrace -ow -o C:\USBTrace.etl -p "Microsoft-Windows-USB-USBXHCI" 0xFFFFFFFF 0xFF
logman create trace USBTrace -ow -o C:\USBTrace.etl -p "Microsoft-Windows-USB-USBHUB3" 0xFFFFFFFF 0xFF
logman start USBTrace
```

**Option C: Using xperf (Windows Performance Toolkit)**

```powershell
xperf -start USBTrace -on Microsoft-Windows-USB-USBXHCI+Microsoft-Windows-USB-USBHUB3 -f C:\USBTrace.etl
```

**Option D: Using wpr (Windows Performance Recorder) with custom profile**

```powershell
wpr -start USBTrace.wprp -filemode
```

**USB4 WPP Provider GUIDs (`wpp.guids` file format):**

Each line: `GUID FLAGS LEVEL` — use `0xffffffff 0xff` for all events at all levels.

```
505A6797-49B9-4A7B-AB6D-9B7F4ECAD9CC 0xffffffff 0xff
1B502FCB-4EC8-4E0F-B362-E18B70E3EFED 0xffffffff 0xff
47711976-08C5-4102-B10F-1BBA7B58F1A4 0xffffffff 0xff
9F7711DD-29AD-37CA-257A-4D553440D635 0xffffffff 0xff
6E6CC2C5-234F-47CC-99E2-5B5DA80DACA0 0xffffffff 0xff
6FB6E467-9ED4-4B73-8C22-70B97E22B23F 0xffffffff 0xff
ef201d1b-1b2a-41a2-828a-4a4bbc582e9e 0xffffffff 0xff
2430d0ce-e3e6-4dcb-a541-8f80eb7c7be5 0xffffffff 0xff
EAD1EE75-90F5-497C-8331-1075EFA22C1A 0xffffffff 0xff
C500C63A-E2FA-4814-B889-E97D055B1747 0xffffffff 0xff
EDEF8E04-B498-4F99-B790-5164E89BB206 0xffffffff 0xff
03906A40-B8AC-4F31-9F05-A5B483CAEFC4 0xffffffff 0xff
c42bbfdb-0c88-4bfd-8a8c-52da3825041f 0xffffffff 0xff
```

> **TIP:** Save this as `wpp.guids` in the same directory you run logman from.

**Manifested ETW Providers (for Option B):**

| Provider GUID / Name | What it captures |
|----------------------|------------------|
| `Microsoft-Windows-USB-USBXHCI` | xHCI host controller events — commands, transfers, port status |
| `Microsoft-Windows-USB-USBHUB3` | USB hub driver events — enumeration, port changes, device add/remove |
| `Microsoft-Windows-USB-USBHUB` | Legacy USB 2.0 hub events |
| `Microsoft-Windows-USB-UCX` | USB Core Extensions — device management, endpoint lifecycle |
| `Microsoft-Windows-USB-USBPORT` | USB port driver events |
| `Microsoft-Windows-USB-UAOL` | UAOL audio offload events — ACE handoff, FIFO state, glitch events |

### Step 2 — Reproduce the Issue

```
1. Start ETL capture (Step 1)
2. Reproduce the USB failure scenario
3. Wait for symptom to manifest
4. Stop capture immediately after failure
```

### Step 3 — Stop ETL Capture

```powershell
# Matching the start method:
logman stop USBTrace
# or
xperf -stop USBTrace
# or
wpr -stop C:\USBTrace.etl
```

### Step 3b — Boot Trace Capture (Across Reboots)

For issues that occur during boot (e.g., USB enumeration failures at POST, S4 resume device loss), use boot trace sessions that persist across reboots.

**Single Boot Trace** — capture across one reboot:

```powershell
# BEFORE reboot: start a persistent boot trace session
logman create trace autosession\USBBootLogSession -o C:\USBBootTrace.etl -nb 16 256 -bs 1000 -ets -pf wpp.guids

# Reboot the system...

# AFTER reboot: stop and finalize the trace
logman stop USBBootLogSession -ets
logman delete autosession\USBBootLogSession -ets -fd
```

**Continuous Boot Trace** — capture across multiple reboots (append mode):

```powershell
# BEFORE first reboot: start with -a (append) flag
logman create trace autosession\USBBootLogSession -o C:\USBBootTrace.etl -ets -pf wpp.guids -a

# Reboot as many times as needed...

# AFTER final reboot: stop and finalize
logman stop USBBootLogSession -ets
logman delete autosession\USBBootLogSession -ets -fd
```

> **Key:** The `autosession\` prefix tells Windows to auto-start the trace session on every boot. The `-nb 16 256` sets min/max buffers, `-bs 1000` sets buffer size (bytes). The `-a` flag appends across reboots instead of overwriting.

---

### Step 3c — Collect Environment Info Alongside ETL

When capturing an ETL, also collect driver version information for reference. This helps match PDBs to the exact driver build later.

```powershell
# Collect USB driver versions on the SUT
powershell -command "Get-Item C:\Windows\System32\drivers\usbxhci.sys, C:\Windows\System32\drivers\usbhub3.sys, C:\Windows\System32\drivers\ucx01000.sys | ForEach-Object { $_.Name + ' ' + $_.VersionInfo.FileVersion }"
```

> **Best practice:** Always capture driver versions at the same time as the ETL. If the SUT gets updated between capture and decode, the PDBs won't match.

---

### Step 4 — Fetch ETL File and Obtain PDB Symbols

> **CRITICAL:** PDB symbol files do NOT exist on the SUT by default. Only `.sys` driver binaries are present in `C:\Windows\System32\drivers\`. You MUST use `symchk` on the SUT to download matching PDBs from a symbol server. The PDBs must exactly match the driver versions installed on the SUT where the ETL was captured.

#### Agent Behavior When ETL Path or SUT is Provided

When the user provides:
- An **ETL file path on a SUT** (e.g. `C:\Users\Administrator\Desktop\USBTrace.etl`)
- A **hostname** (e.g. `PG16WVAW2048`) or **IP address** (e.g. `172.22.8.141`)

The agent MUST ask (if not already provided):

> "Which hostname or SUT IP address should I fetch the USB symbol files from?"

Then automatically:
1. Resolve the SUT (via NGA if hostname given, or connect directly if IP given)
2. Fetch the ETL file from the SUT
3. Fetch the required USB PDB symbol files from the SUT
4. Set up `_NT_SYMBOL_PATH` pointing to the locally fetched symbols
5. Decode the ETL

#### Step 4a — Resolve SUT from Hostname via NGA

When a **hostname** is given (e.g. `PG16WVAW2048`), the hostname is the **host machine** — the SUT (target) is associated with it via NGA station record:

```python
import sys, socket
sys.path.insert(0, r'C:\SVShare\NGA\ClientScripts')
from NgaGateway import NgaGateway
from evtar.services.communicator.ux import GetCommunicator

def get_sut_communicator(hostname):
    # Step 1: resolve project from NGA
    gw = NgaGateway('StationAutomation', None, hostname)
    project = gw.get_project_name_by_system_name(hostname)

    # Step 2: find Target role system in station
    gw2 = NgaGateway('StationAutomation', project, hostname)
    system = gw2.get_system_by_name(hostname)
    station = gw2.get_station_by_id(system['StationId'])
    sut = next(s for s in station['Systems'] if s['Role'] == 'Target')

    print(f"SUT: {sut['Name']} @ {sut['Ip']}")
    return GetCommunicator(sut['Ip'], nPortNum=8001)
```

When an **IP address** is given directly, skip NGA lookup:

```python
def get_sut_communicator_by_ip(ip):
    return GetCommunicator(ip, nPortNum=8001)
```

#### Step 4b — Fetch ETL File from SUT

```python
comm = get_sut_communicator('PG16WVAW2048')  # or get_sut_communicator_by_ip('172.22.8.141')

sut_etl_path = r'C:\Users\Administrator\Desktop\USBTrace.etl'
local_etl_path = r'C:\ETLDecode\USBTrace.etl'

import os
os.makedirs(r'C:\ETLDecode', exist_ok=True)
comm.GetFileFromTarget(sut_etl_path, local_etl_path)
print(f'ETL fetched to {local_etl_path}')
```

#### Step 4c — Obtain USB PDB Symbols via symchk on SUT

PDB files do **NOT** exist on the SUT by default — only `.sys` driver binaries are present. Use `symchk.exe` on the SUT to download the matching PDBs from the Microsoft public symbol server.

**USB driver .sys files that need matching PDBs:**

| SYS File | Driver | Coverage |
|---|---|---|
| `usbxhci.sys` | xHCI host controller | Commands, transfers, port status |
| `usbhub3.sys` | USB 3.x Hub driver | SS hub enumeration, port management |
| `ucx01000.sys` | USB Core Extensions | UCX device/endpoint lifecycle |
| `usbhub.sys` | USB 2.0 Hub driver | Legacy hub enumeration |
| `usbport.sys` | USB port driver | EHCI/OHCI port events |
| `usbstor.sys` | USB storage driver | Mass storage transfers |
| `winusb.sys` | WinUSB generic driver | WinUSB device events |
| `pci.sys` | PCI bus driver | PCI device enumeration events |
| `ucx01000.sys` | USB Core Extensions | UCX device/endpoint lifecycle |
| `ufx01000.sys` | USB Function Extension | USB function (device-mode) events |
| `ufxsynopsys.sys` | Synopsys UFX controller | UFX controller events |

**Run symchk on the SUT to download PDBs:**

```python
import os

USB_DRIVERS = [
    'usbxhci.sys', 'usbhub3.sys', 'ucx01000.sys', 'usbhub.sys',
    'usbport.sys', 'usbstor.sys', 'winusb.sys', 'pci.sys',
    'ufx01000.sys', 'ufxsynopsys.sys',
]

SUT_SYMBOL_DIR = r'C:\symbols'
SYS_DIR = r'C:\Windows\System32\drivers'

# Run symchk on the SUT via communicator for each USB driver
for drv in USB_DRIVERS:
    sys_path = rf'{SYS_DIR}\{drv}'
    cmd = f'symchk "{sys_path}" /s srv*{SUT_SYMBOL_DIR}*https://msdl.microsoft.com/download/symbols'
    try:
        result = comm.ExecuteCommandOnTarget(cmd, 60)
        print(f'  [OK]   {drv}: {result.strip()}')
    except Exception as e:
        print(f'  [FAIL] {drv}: {e}')
```

**Then fetch the downloaded PDBs from SUT to local machine:**

```python
local_symbol_dir = r'C:\ETLDecode\symbols'
os.makedirs(local_symbol_dir, exist_ok=True)

# symchk stores PDBs in subdirectories: C:\symbols\<name>.pdb\<guid>\<name>.pdb
# Fetch the entire symbols folder from the SUT
comm.GetFolderFromTarget(SUT_SYMBOL_DIR, local_symbol_dir)
print(f'Symbols fetched to {local_symbol_dir}')
```

> **If symchk fails** to download PDBs (e.g., symbol server unreachable, driver not indexed), tell the user immediately: *"Cannot obtain PDB symbols for this SUT. ETL decode is not possible without them."* and stop. There is no fallback — PDBs are the only way to decode WPP ETL traces.

#### Step 4d — Set Up Symbol Path

```powershell
# Point to locally fetched SUT symbols first, then fall back to MS public symbol server
set _NT_SYMBOL_PATH=C:\ETLDecode\symbols;srv*C:\symbols*https://msdl.microsoft.com/download/symbols
```

Or from Python before launching decode:

```python
import os
os.environ['_NT_SYMBOL_PATH'] = r'C:\ETLDecode\symbols;srv*C:\symbols*https://msdl.microsoft.com/download/symbols'
```

### Step 5 — Decode ETL Trace (Complete End-to-End Script)

The agent should run this full workflow automatically when a hostname/IP and ETL path are provided:

```python
import os, sys, glob
sys.path.insert(0, r'C:\SVShare\NGA\ClientScripts')
from evtar.services.communicator.ux import GetCommunicator

USB_DRIVERS = [
    'usbxhci.sys', 'usbhub3.sys', 'ucx01000.sys', 'usbhub.sys',
    'usbport.sys', 'usbstor.sys', 'winusb.sys', 'pci.sys',
    'ufx01000.sys', 'ufxsynopsys.sys',
]

def get_comm_from_hostname(hostname):
    from NgaGateway import NgaGateway
    gw = NgaGateway('StationAutomation', None, hostname)
    project = gw.get_project_name_by_system_name(hostname)
    gw2 = NgaGateway('StationAutomation', project, hostname)
    system = gw2.get_system_by_name(hostname)
    station = gw2.get_station_by_id(system['StationId'])
    sut = next(s for s in station['Systems'] if s['Role'] == 'Target')
    print(f"SUT resolved: {sut['Name']} @ {sut['Ip']}")
    return GetCommunicator(sut['Ip'], nPortNum=8001)

def get_comm_from_ip(ip):
    return GetCommunicator(ip, nPortNum=8001)

def fetch_etl(comm, sut_etl_path, local_dir=r'C:\ETLDecode'):
    os.makedirs(local_dir, exist_ok=True)
    etl_name = os.path.basename(sut_etl_path)
    local_etl = os.path.join(local_dir, etl_name)
    comm.GetFileFromTarget(sut_etl_path, local_etl)
    print(f'ETL fetched -> {local_etl}')
    return local_etl

def obtain_pdbs_via_symchk(comm, local_dir=r'C:\ETLDecode'):
    """Run symchk on the SUT to download matching PDBs from symbol server."""
    sut_sym_dir = r'C:\symbols'
    local_sym_dir = os.path.join(local_dir, 'symbols')
    os.makedirs(local_sym_dir, exist_ok=True)

    found = 0
    for drv in USB_DRIVERS:
        sys_path = rf'C:\Windows\System32\drivers\{drv}'
        cmd = f'symchk "{sys_path}" /s srv*{sut_sym_dir}*https://msdl.microsoft.com/download/symbols'
        try:
            result = comm.ExecuteCommandOnTarget(cmd, 60)
            if 'FAILED' not in result.upper():
                print(f'  [OK]   {drv}')
                found += 1
            else:
                print(f'  [FAIL] {drv}: {result.strip()}')
        except Exception as e:
            print(f'  [FAIL] {drv}: {e}')

    if found == 0:
        print('ERROR: No PDBs obtained. ETL decode is not possible.')
        return None

    # Fetch downloaded PDBs from SUT to local machine
    comm.GetFolderFromTarget(sut_sym_dir, local_sym_dir)
    print(f'Symbols fetched -> {local_sym_dir} ({found} PDBs)')
    return local_sym_dir

def decode_etl(local_etl, sym_dir, output_txt=None):
    if output_txt is None:
        output_txt = local_etl.replace('.etl', '_decoded.txt')
    os.environ['_NT_SYMBOL_PATH'] = (
        f'{sym_dir};srv*C:\\symbols*https://msdl.microsoft.com/download/symbols'
    )
    # USB drivers use WPP tracing — must generate TMFs from PDBs first, then decode
    # Step 1: Run tracepdb on each PDB to generate .tmf files
    tmf_dir = os.path.join(os.path.dirname(local_etl), 'tmf')
    os.makedirs(tmf_dir, exist_ok=True)
    for pdb_file in glob.glob(os.path.join(sym_dir, '**', '*.pdb'), recursive=True):
        cmd = f'tracepdb.exe -f "{pdb_file}" -p "{tmf_dir}"'
        print(f'  tracepdb: {os.path.basename(pdb_file)}')
        os.system(cmd)

    # Step 2: Run tracefmt to decode ETL using generated TMFs
    # Detailed mode: PID, TID, function, flags, level
    os.environ['TRACE_FORMAT_PREFIX'] = (
        '[%9!d!]%8!04X!.%3!04X! %!FUNC! [%!FLAGS!] [%!LEVEL!]'
    )
    cmd = f'tracefmt.exe "{local_etl}" -tmf "{tmf_dir}" -o "{output_txt}"'
    print(f'Decoding: {cmd}')
    os.system(cmd)
    print(f'Decoded  -> {output_txt}')
    return output_txt

# --- Usage ---
# From hostname:
# comm = get_comm_from_hostname('PG16WVAW2048')
#
# From IP:
# comm = get_comm_from_ip('172.22.8.141')
#
# comm.IsConnected()  # verify
# etl = fetch_etl(comm, r'C:\Users\Administrator\Desktop\USBTrace.etl')
# syms = obtain_pdbs_via_symchk(comm)
# if syms:
#     decoded = decode_etl(etl, syms)
```

---

### Step 5b — Decode ETL Trace (tool options)

> **USB drivers use WPP (Windows software trace PreProcessor) tracing.**
> WPP format strings are stored in the PDB, NOT in the .sys binary or ETW manifest.
> You MUST generate TMF files from PDBs first, then use tracefmt to decode.
> Without TMFs, all WPP events will show as "Unknown( )" with "No Format Information found."

**Option A: tracepdb + tracefmt (PRIMARY — required for WPP decode)**

```powershell
# Step 1: Generate TMF files from each PDB
tracepdb.exe -f C:\ETLDecode\symbols\usbxhci.pdb -p C:\ETLDecode\tmf
tracepdb.exe -f C:\ETLDecode\symbols\ucx01000.pdb -p C:\ETLDecode\tmf
tracepdb.exe -f C:\ETLDecode\symbols\usbhub3.pdb -p C:\ETLDecode\tmf
# ... repeat for all USB PDBs

# Step 2: Set TRACE_FORMAT_PREFIX (controls output format)
# Detailed mode (recommended for debug — includes PID, TID, CPU, source file, line, function):
set TRACE_FORMAT_PREFIX=[%9!d!]%8!04X!.%3!04X! %!FUNC! [%!FLAGS!] [%!LEVEL!]

# Simple mode (timestamp + flags + level only):
set TRACE_FORMAT_PREFIX=[%9!d!] [%!FLAGS!] [%!LEVEL!]

# Step 3: Decode ETL using generated TMFs
tracefmt.exe C:\ETLDecode\USBTrace.etl -tmf C:\ETLDecode\tmf -o C:\ETLDecode\USBTrace_decoded.txt
```

**TRACE_FORMAT_PREFIX format specifiers:**

| Specifier | Meaning |
|-----------|---------|
| `%9!d!` | Timestamp (CPU tick count) |
| `%8!04X!` | Process ID (hex) |
| `%3!04X!` | Thread ID (hex) |
| `%4!s!` | Source file name |
| `%!FUNC!` | Function name |
| `%!FLAGS!` | Trace flags |
| `%!LEVEL!` | Trace level |

> **Note:** `tracepdb.exe` and `tracefmt.exe` are part of the Windows Driver Kit (WDK).
> They may also be found in trace toolkit folders on the SUT (e.g., `ParseTraceFiles\` directories).

**Option B: netsh trace convert (basic — will NOT decode WPP events)**
```powershell
# Only useful for manifested ETW providers. WPP events will show as "Unknown".
netsh trace convert input=C:\ETLDecode\USBTrace.etl output=C:\ETLDecode\USBTrace.txt
```

**Option C: Windows Performance Analyzer (WPA)**
```powershell
# Open in WPA GUI — symbols must be set first (see Step 4d)
wpa C:\ETLDecode\USBTrace.etl
# Navigate to: System Activity → Generic Events → Microsoft-Windows-USB-*
```

**Option D: tracerpt (CSV output)**
```powershell
set _NT_SYMBOL_PATH=C:\ETLDecode\symbols;srv*C:\symbols*https://msdl.microsoft.com/download/symbols
tracerpt C:\ETLDecode\USBTrace.etl -o C:\ETLDecode\USBTrace.csv -of CSV -y
```

---

## ETL Analysis Patterns

### Pattern 1: Device Disconnect Root-Cause

**What to look for:**
1. Search for `PORTSC` change events — look for `CCS` transition from 1→0
2. Check preceding events — was there a transfer error? link state change?
3. Check if disconnect was driver-initiated (PORTSC write) or hardware-detected

```
Timeline analysis:
  [T0] Normal operation — CCS=1, PED=1, PLS=U0
  [T1] First anomaly — look for transfer completion error, link state change
  [T2] Port status change — CCS=0 or PLS=Disabled
  [T3] Driver response — hub driver removes device, re-enumeration attempt
```

### Pattern 2: UAOL Audio Glitch Analysis

**What to look for:**
1. Search for UAOL provider events
2. Look for `EndpointPurge` events — this is the xHCI→ACE handoff
3. Check for `MissedServiceInterval` events
4. Look for FIFO underrun/overrun indicators

> **CRITICAL:** When UAOL is active, isochronous endpoint traffic is offloaded from xHCI to ACE. **xHCI traces have NO visibility** into offloaded transfers. You need the UAOL-specific provider.

**ACE3 vs ACE4 timing:**
- ACE3 (PTL): ~1ms feedback FIFO — any gap >1ms can cause stream loss
- ACE4 (NVL): up to 10ms feedback FIFO — more tolerant of scheduling jitter

### Pattern 3: S0ix Blocker Identification

**What to look for:**
1. Search for `D3` transition events — which devices entered D3?
2. Look for `LPM` events — are ports transitioning to U2/U3?
3. Check for `LTR` (Latency Tolerance Reporting) values — aggressive LTR blocks deep sleep
4. Identify the **last device** that didn't enter low-power state

### Pattern 4: Transfer Error Analysis

**What to look for:**
1. Search for `TransferComplete` events with non-zero completion codes
2. Map completion codes to xHCI TRB completion codes:

| Code | Meaning | Common Cause |
|------|---------|-------------|
| 1    | Success | Normal |
| 4    | USB Transaction Error | Protocol error, device timeout |
| 6    | Stall | Device endpoint halted |
| 13   | Short Packet | Less data than expected (may be OK for some transfers) |
| 21   | Split Transaction Error | USB 2.0 behind hub timing issue |
| 26   | Missed Service Error | Isochronous interval missed |
| 28   | Event Ring Full | Software too slow to process events |

### Pattern 5: Enumeration Failure Analysis

**What to look for:**
1. Search for `SetAddress` command completion
2. Search for `GetDescriptor` requests and responses
3. Check for `PortReset` events and outcomes
4. Look for `DeviceSlotEnable` / `AddressDevice` command failures

---

## ETL Capture Best Practices

1. **Start capture BEFORE reproducing** — don't miss the initial trigger
2. **Minimize capture duration** — long traces are hard to analyze and can fill disk
3. **Capture on both Host and SUT** if using host-target setup
4. **Include all USB providers** for comprehensive analysis (not just USBXHCI)
5. **Save the .etl file** — text conversions lose some information
6. **Note the exact timestamp** when the failure occurs — helps narrow analysis window
7. **Collect simultaneously** with `allchecker.py` output for correlated analysis
8. **Collect environment info alongside the ETL** — capture driver versions at trace time so you know exactly which binaries produced the trace. The Usb4Trace toolkit does this automatically via `CollectEnvironmentInfo.bat` (copies `filever.exe`, runs it on USB4*.sys / KmglDriver.sys, saves `.info.txt` files next to the ETL). Adopt this practice: always record driver versions when capturing a trace.
9. **Bundle decode tools with the ETL** — copy `tracepdb.exe`, `tracefmt.exe`, and `parseEtl.cmd` into the ETL output directory so the trace is self-contained and can be decoded on any machine

---

## ETL + Debug Bundle Correlation

For comprehensive failure analysis, collect ETL traces alongside the standard debug bundle:

```bash
# Start ETL capture
powershell -Command "logman start USBTrace ..."

# Reproduce failure...

# Stop ETL and collect debug bundle
powershell -Command "logman stop USBTrace"
python allchecker.py > debug_bundle.txt 2>&1
python treeview.py >> debug_bundle.txt 2>&1
python yellowbang_usb.py >> debug_bundle.txt 2>&1
python NDE_checker.py >> debug_bundle.txt 2>&1

# Package together
# ETL trace + debug bundle + test log = complete failure package
```

---

## Agent Decision Tree — ETL Decode Request

### MANDATORY FIRST STEP — Ask Before Doing Anything

When the user asks to decode an ETL trace (regardless of how much info they provide), the agent MUST ask these two questions **before proceeding with any action**:

1. **"Where is the ETL log file? Please provide the full path and the machine it is on (hostname, IP address, or local)."**
2. **"Which system (hostname or IP address) should I fetch the USB symbol files from?"**

> These two questions MUST always be asked first — even if the user already provided a path or system name. Confirm both explicitly before starting any fetch or decode operation. Never assume or skip these questions.

---

### Decision Flow (After Both Answers Are Collected)

```
Q1: Where is the ETL file?
    ├─ Local path on this host
    │       └─ Verify file exists. If NOT found → say "No ETL file found at <path>." and STOP.
    │       └─ If found → skip to Q2
    └─ Path on remote SUT (hostname or IP given)
            └─ Connect to SUT → search for ETL file
            └─ If NOT found → say "No USB ETL file found on this SUT." and STOP.
            └─ If found → fetch ETL from SUT → Step 4b

Q2: Which system to fetch USB symbols from?
    ├─ Hostname given (e.g. PG16WVAW2048)
    │       └─ NGA resolve → find Role=Target SUT → Step 4a
    └─ IP address given (e.g. 172.22.8.141)
            └─ Connect directly
    └─ Run symchk on SUT to obtain PDBs → Step 4c
       ├─ symchk succeeds → fetch PDBs to local → Step 4d → Decode (Step 5)
       └─ symchk fails → say "Cannot obtain PDB symbols. ETL decode not possible." and STOP.

After decode:
    └─ Analyze from USB perspective ONLY (ETL Analysis Patterns section)
    └─ Do NOT infer content from filename — only from decoded events
```

**Key rules:**
- If no ETL exists, say so and stop. Do not suggest alternatives or reference other work.
- If PDBs cannot be obtained via symchk, say so and stop. There is no fallback.
- Always analyze decoded content from **USB perspective only**.
- **Never assume what an ETL contains based on its filename or folder name.**
- Stay on topic. Do not reference previous tasks or unrelated analyses.

---

## Cross-References

| Topic | Resource |
|-------|----------|
| USB failure triage flowcharts | `fv-usb/debug` sub-skill |
| xHCI TRB completion codes | `fv-usb/xhci` sub-skill |
| UAOL architecture & ACE timing | `fv-usb/power` sub-skill (UAOL section) |
| NGA station/system resolution | `nga/stationautomation` sub-skill |
| SUT communication via evtar | `NgaGateway.py`, `StationCommand.py` in `C:\SVShare\NGA\ClientScripts\` |
| Known issues / HSDES sightings | `fv-usb/docs/known_issues.md` |
| PythonSV register access | `pysv` skill |
| Debug playbooks | `fv-usb/docs/debug_playbooks.md` |
| **USB ETL Standalone Tool** | `usb_debug_standalone_v8.py` — see below |

---

## Standalone ETL Analysis (No NGA Required)

When a full NGA setup is unavailable, use the standalone USB ETL analyzer tool to decode and analyze traces offline.

### Tool: `usb_debug_standalone_v8.py`

**Wiki page:** Confluence page ID `1956226078` (USB ETL Analyzer)

**Workflow:**

```batch
:: Step 1 — Generate symbol files from PDB
tracepdb.exe /f <symbols_path> /p <output_dir>

:: Step 2 — Convert ETL to text format
convert.bat <etl_file> <output_dir>

:: Step 3 — Run standalone analyzer
python usb_debug_standalone_v8.py --src <output_dir>
```

**Common options:**

| Option | Description |
|--------|-------------|
| `--src <path>` | Directory containing converted ETL output |
| `--filter usb` | Filter to USB-specific events only |
| `--filter uaol` | Filter to UAOL/ACE events |
| `--out <file>` | Save decoded output to file |

**Prerequisites:**
- `tracepdb.exe` — available in Windows Driver Kit (WDK) or as standalone tool
- `convert.bat` — provided alongside `usb_debug_standalone_v8.py` in the USB debug toolkit
- Python 3.8+ on the analysis machine

> **Generic debug BKM:** Confluence page ID `2678716070` — 4-step debug procedure applicable to most USB ETL analysis workflows.
