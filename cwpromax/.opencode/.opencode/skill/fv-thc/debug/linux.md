---
name: fv-thc/debug (Linux)
description: Linux-specific THC debug techniques — dmesg signatures, dynamic_debug, ftrace, sysfs/debugfs, /proc/interrupts, kernel module params, common failure patterns
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# THC Debug — Linux-Specific

Linux-specific debug tools and techniques for THC validation. Covers kernel logging, tracing, sysfs inspection, and common failure signatures unique to the Linux QuickSPI/QuickI2C drivers.

> **Driver modules**: `intel-thc-hid` (core), `quickspi` (HIDSPI), `quicki2c` (HIDI2C)
> **Source**: `drivers/hid/intel-thc-hid/` in Linux kernel tree

---

## 1. dmesg Signature Patterns

### 1.1 Probe Success

```
# QuickSPI successful probe
quickspi 0000:00:10.0: QuickSPI started, IC_VERSION: 0x<ver>
quickspi 0000:00:10.0: HID descriptor retrieved, vendor: 0x<vid>, product: 0x<pid>

# QuickI2C successful probe
quicki2c 0000:00:10.0: QuickI2C started, IC_VERSION: 0x<ver>
quicki2c 0000:00:10.0: HID descriptor retrieved, vendor: 0x<vid>, product: 0x<pid>
```

### 1.2 Probe Failure Signatures

| dmesg Pattern | Likely Root Cause | Debug Action |
|---------------|-------------------|-------------|
| `quickspi: probe failed with error -ENODEV` | THC port not enabled in BIOS or wrong port type configured | Check BIOS THC Configuration menu |
| `quickspi: failed to get HID descriptor` | Touch device not responding, SPI bus issue, or wrong clock/IO mode | Check SPI waveform on logic analyzer |
| `quicki2c: failed to get HID descriptor` | Touch device NACK, wrong I2C address, or I2C sub-IP misconfigured | Check I2C bus with logic analyzer, verify target address |
| `thc_dma_configure: DMA configuration failed` | PRD allocation failure, IOMMU issue, or BAR not mapped | Check `dmesg \| grep -i iommu`, verify PCI BAR |
| `thc_interrupt_config: failed to request IRQ` | MSI/MSI-X allocation failure, interrupt conflict | Check `/proc/interrupts`, verify PCI MSI capability |
| `thc_wot_config: unable to get wake-on-touch GPIO IRQ` | ACPI `"wake-on-touch"` GPIO resource missing | Check BIOS WoT knob, dump ACPI tables (`acpidump`) |
| `thc_port_select: unsupported port type` | BIOS configured unknown port type in THC_M_PRT_CONTROL | Dump register via PySV |
| `i2c_subip_init: IC_ENABLE stuck` | Synopsys I2C sub-IP not responding | Check I2C sub-IP clock enable in THC_CFG_PCE |

### 1.3 DMA Error Patterns

```bash
# DMA timeout (critical - touch will stop working)
dmesg | grep -i "dma.*timeout\|dma.*error\|dma.*fail"

# Expected patterns:
# "thc_dma_read: DMA read timeout"     — RXDMA didn't complete within deadline
# "thc_dma_write: DMA write timeout"   — TXDMA didn't complete
# "thc_swdma_read: SWDMA read timeout" — SWDMA debug read timeout
```

| DMA Error Pattern | Root Cause | Fix |
|-------------------|-----------|-----|
| `DMA read timeout` | Touch device stopped responding mid-transfer | Reset device, check bus waveform |
| `DMA write timeout` | TXDMA command not acknowledged by device | Check device state, verify command format |
| `SWDMA read timeout` | Debug read while device busy or DMA paused | Wait for RXDMA completion first |
| `PRD ring full` | Driver not consuming PRD entries fast enough | Check for CPU scheduling issues |

### 1.4 Power Management Patterns

```bash
# PM state transitions
dmesg | grep -i "quickspi\|quicki2c" | grep -i "suspend\|resume\|d3\|d0i2\|ltr\|pm_runtime"

# Expected patterns:
# "quickspi 0000:00:10.0: suspend entered"
# "quickspi 0000:00:10.0: resume entered"
# "pci 0000:00:10.0: power state changed from D0 to D3hot"
# "pci 0000:00:10.0: power state changed from D3hot to D0"
```

### 1.5 WoT Patterns

```bash
# WoT configuration
dmesg | grep -i "wot\|wake-on-touch\|wake_irq\|device_may_wakeup"

# Success: "thc_wot_config: WoT configured, GPIO IRQ <num>"
# Degraded: "thc_wot_config: unable to get wake-on-touch GPIO IRQ, WoT disabled"
#           (this is dev_warn, NOT fatal — touch still works without WoT)
```

---

## 2. dynamic_debug

Linux `dynamic_debug` enables per-module/per-function `dev_dbg()` output at runtime without recompiling.

### 2.1 Enable THC Debug Messages

```bash
# Enable ALL debug messages from THC modules
echo 'module intel_thc_hid +p' > /sys/kernel/debug/dynamic_debug/control
echo 'module quickspi +p' > /sys/kernel/debug/dynamic_debug/control
echo 'module quicki2c +p' > /sys/kernel/debug/dynamic_debug/control

# Enable with function name and line number
echo 'module intel_thc_hid +fpl' > /sys/kernel/debug/dynamic_debug/control

# Enable specific functions only
echo 'func thc_dma_configure +p' > /sys/kernel/debug/dynamic_debug/control
echo 'func thc_interrupt_handler +p' > /sys/kernel/debug/dynamic_debug/control
echo 'func thc_ltr_config +p' > /sys/kernel/debug/dynamic_debug/control
echo 'func i2c_subip_init +p' > /sys/kernel/debug/dynamic_debug/control

# Disable all
echo 'module intel_thc_hid -p' > /sys/kernel/debug/dynamic_debug/control
echo 'module quickspi -p' > /sys/kernel/debug/dynamic_debug/control
echo 'module quicki2c -p' > /sys/kernel/debug/dynamic_debug/control
```

### 2.2 Targeted Debug Scenarios

```bash
# DMA path debug
echo 'func thc_dma_* +p' > /sys/kernel/debug/dynamic_debug/control

# Interrupt debug
echo 'func thc_interrupt_* +p' > /sys/kernel/debug/dynamic_debug/control

# PIO path debug
echo 'func thc_pio_* +p' > /sys/kernel/debug/dynamic_debug/control

# I2C sub-IP debug
echo 'func i2c_subip_* +p' > /sys/kernel/debug/dynamic_debug/control

# WoT debug
echo 'func thc_wot_* +p' > /sys/kernel/debug/dynamic_debug/control
```

### 2.3 Check Available Debug Points

```bash
# List all THC debug points
grep -i "thc\|quickspi\|quicki2c" /sys/kernel/debug/dynamic_debug/control
```

---

## 3. ftrace

ftrace provides kernel function tracing with nanosecond timing. Essential for debugging DMA latency, interrupt response, and PM transition timing.

### 3.1 THC Function Tracing

```bash
# Setup ftrace for THC functions
cd /sys/kernel/tracing

# Clear existing filters
echo > set_ftrace_filter

# Add THC core functions
echo 'thc_*' >> set_ftrace_filter

# Add QuickSPI functions
echo 'quickspi_*' >> set_ftrace_filter

# Add QuickI2C functions
echo 'quicki2c_*' >> set_ftrace_filter

# Add I2C sub-IP functions
echo 'i2c_subip_*' >> set_ftrace_filter

# Enable function tracer
echo function > current_tracer
echo 1 > tracing_on

# ... reproduce issue ...

echo 0 > tracing_on
cat trace > /tmp/thc_ftrace.log
```

### 3.2 Interrupt Latency Tracing

```bash
# Trace interrupt handler entry/exit with timing
echo function_graph > current_tracer
echo 'thc_interrupt_handler' > set_graph_function
echo 1 > tracing_on

# Output shows call graph with execution time:
#  0)               |  thc_interrupt_handler() {
#  0)   0.450 us    |    thc_read_interrupt_status();
#  0)   0.120 us    |    thc_dma_read();
#  0)   1.234 us    |  }
```

### 3.3 PM Transition Tracing

```bash
# Trace suspend/resume with PCI PM
echo function_graph > current_tracer
echo 'quickspi_suspend quickspi_resume quicki2c_suspend quicki2c_resume' > set_graph_function
echo 'pci_set_power_state pci_save_state pci_restore_state' >> set_graph_function
echo 1 > tracing_on

# Trigger suspend/resume cycle, then capture
echo 0 > tracing_on
cat trace > /tmp/thc_pm_trace.log
```

### 3.4 DMA Timing Trace

```bash
# Measure DMA operation latency
echo function_graph > current_tracer
echo 'thc_dma_configure thc_dma_unconfigure thc_dma_read thc_dma_write' > set_graph_function
echo 'thc_rxdma_start thc_txdma_start' >> set_graph_function
echo 1 > tracing_on
```

### 3.5 Trace Events (if available)

```bash
# Check for THC-specific tracepoints
ls /sys/kernel/tracing/events/ | grep -i thc

# If present (kernel may add these in future versions):
echo 1 > /sys/kernel/tracing/events/thc/enable

# Generic PCI PM events (always available)
echo 1 > /sys/kernel/tracing/events/power/pci_set_power_state/enable
echo 1 > /sys/kernel/tracing/events/rpm/rpm_suspend/enable
echo 1 > /sys/kernel/tracing/events/rpm/rpm_resume/enable
```

---

## 4. sysfs Entries

### 4.1 PCI Device Information

```bash
# Find THC PCI device(s)
lspci -nn | grep -i "THC\|Touch\|10.0\|10.1\|16.0\|16.1"

# Typical output:
# 00:10.0 Serial bus controller [0c80]: Intel Corporation Device [8086:a849]
# 00:10.1 Serial bus controller [0c80]: Intel Corporation Device [8086:a84b]

# THC BDF — note: platform-specific, always verify
BDF="0000:00:10.0"  # Example for THC0

# PCI config space
lspci -vvv -s $BDF

# Power state
cat /sys/bus/pci/devices/$BDF/power/runtime_status
# Expected: "active" (D0) or "suspended" (D3)

# Runtime PM control
cat /sys/bus/pci/devices/$BDF/power/control
# "auto" = PM enabled, "on" = PM disabled (always D0)

# Runtime PM timing
cat /sys/bus/pci/devices/$BDF/power/runtime_active_time
cat /sys/bus/pci/devices/$BDF/power/runtime_suspended_time
cat /sys/bus/pci/devices/$BDF/power/autosuspend_delay_ms
# Default: 5000ms for QuickI2C (DEFAULT_AUTO_SUSPEND_DELAY_MS)

# PCI D-state transitions
cat /sys/bus/pci/devices/$BDF/power/runtime_active_kids

# BAR resources
cat /sys/bus/pci/devices/$BDF/resource
# BAR0: 32KB MMIO (0x8000 bytes)
```

### 4.2 HID Device Information

```bash
# Find THC HID device
ls /sys/bus/hid/devices/

# Typical: 0018:056A:WXYZ.0001 (bus 0x18=misc, WACOM VID=0x056A)
# Or:      0018:04F3:WXYZ.0001 (ELAN VID=0x04F3)

HID_DEV="/sys/bus/hid/devices/0018:056A:WXYZ.0001"

# HID report descriptor (hex dump)
xxd $HID_DEV/report_descriptor

# Device info
cat $HID_DEV/uevent
```

### 4.3 Input Device Information

```bash
# Find touch input device
cat /proc/bus/input/devices | grep -A 5 -i "touch\|wacom\|elan\|alps"

# Shows: Bus, Vendor, Product, Version, Name, Phys, Sysfs, Handlers
# Look for "Handlers=... eventX" to find the event node
```

### 4.4 Wake Source Status

```bash
# Check if THC is a wake source
cat /sys/bus/pci/devices/$BDF/power/wakeup
# "enabled" = WoT armed, "disabled" = no WoT

# Wake event count
cat /sys/bus/pci/devices/$BDF/power/wakeup_count

# Check dedicated wake IRQ
cat /proc/interrupts | grep -i "wake\|gpio\|thc"
```

### 4.5 IOMMU/DMA Mapping

```bash
# Check IOMMU group for THC
find /sys/kernel/iommu_groups/*/devices -name "$BDF" 2>/dev/null

# DMA coherent pool usage (if applicable)
cat /sys/kernel/debug/dma-api/driver_filter  # Set to quickspi or quicki2c
cat /sys/kernel/debug/dma-api/dump           # Dump DMA mappings
```

---

## 5. /proc/interrupts Analysis

### 5.1 Finding THC Interrupts

```bash
# Search for THC MSI interrupts
grep -i "quickspi\|quicki2c\|thc" /proc/interrupts

# Expected output:
#  <IRQ>:  <count_per_cpu>  PCI-MSI  <info>  quickspi
# Multiple lines if MSI-X vectors are used (separate for DMA, interrupt, etc.)
```

### 5.2 Interrupt Rate Monitoring

```bash
# Monitor interrupt count over time (every 1 second)
watch -n 1 "grep -i 'quickspi\|quicki2c' /proc/interrupts"

# Expected: count increases ONLY during active touch
# Red flag: count increasing without touch → spurious interrupts

# Calculate interrupt rate
COUNT1=$(grep quickspi /proc/interrupts | awk '{sum=0; for(i=2;i<=NF-3;i++) sum+=$i; print sum}')
sleep 10
COUNT2=$(grep quickspi /proc/interrupts | awk '{sum=0; for(i=2;i<=NF-3;i++) sum+=$i; print sum}')
echo "Interrupts in 10s: $((COUNT2 - COUNT1)), rate: $(( (COUNT2 - COUNT1) / 10 )) /sec"
```

### 5.3 Spurious Interrupt Detection

```bash
# Check for spurious interrupts (WoT vGPIO related — HSD 15019129309)
# After S4 resume, if interrupt count increases without touch:
grep -i "gpio\|vgpio\|thc" /proc/interrupts
# If count is increasing rapidly → stale pad config (RXINV/GPIROUTIOXAPIC)
# See wot/linux.md for S4 vGPIO pad delta investigation
```

### 5.4 Affinity and Distribution

```bash
# Check IRQ affinity
IRQ_NUM=$(grep quickspi /proc/interrupts | awk '{print $1}' | tr -d ':')
cat /proc/irq/$IRQ_NUM/smp_affinity_list
cat /proc/irq/$IRQ_NUM/effective_affinity_list

# Check IRQ actions
cat /proc/irq/$IRQ_NUM/actions
```

---

## 6. Kernel Module Parameters

### 6.1 Runtime PM Control

```bash
BDF="0000:00:10.0"

# Disable runtime PM (keep THC always in D0 — useful for debug)
echo "on" > /sys/bus/pci/devices/$BDF/power/control

# Re-enable runtime PM
echo "auto" > /sys/bus/pci/devices/$BDF/power/control

# Adjust autosuspend delay (default 5000ms for QuickI2C)
echo 60000 > /sys/bus/pci/devices/$BDF/power/autosuspend_delay_ms
```

### 6.2 Module Load/Unload

```bash
# Check loaded THC modules
lsmod | grep -i "thc\|quickspi\|quicki2c"

# Module dependency chain:
#   quickspi → intel_thc_hid → hid
#   quicki2c → intel_thc_hid → hid

# Unload (for testing different config)
rmmod quickspi    # or quicki2c
rmmod intel_thc_hid

# Reload with debug
modprobe intel_thc_hid
modprobe quickspi  # or quicki2c

# Note: modprobe parameters are compiled-in; use dynamic_debug for runtime tuning
```

### 6.3 Module Info

```bash
# Check module version and parameters
modinfo quickspi
modinfo quicki2c
modinfo intel_thc_hid

# Shows: version, description, author, parm (module parameters if any)
```

---

## 7. Common Linux Failure Signatures

### 7.1 THC Not Enumerated (No PCI Device)

**Symptom**: `lspci` does not show THC device at expected BDF.

**Debug steps**:
1. Check BIOS: THC must be enabled in `Intel Advanced Menu → PCH-IO Configuration → THC Configuration`
2. Check THC1 dependency: THC1 requires THC0 enabled (THC1 is PCI Function 1)
3. Check for Function Disable: BIOS may have disabled THC via `FD` register
4. Dump PCI config space: `setpci -s 00:10.0 0x00.l` — if returns `0xFFFFFFFF`, device not present
5. Check BIOS boot log for THC init errors

### 7.2 Touch Not Working (Driver Loaded, No Events)

**Symptom**: `evtest /dev/input/eventX` shows no touch events despite finger on panel.

**Debug steps**:
1. Check driver state: `dmesg | grep -i "quickspi\|quicki2c"` — probe must succeed
2. Check HID descriptor: `cat /sys/bus/hid/devices/*/report_descriptor | xxd` — must be non-empty
3. Check interrupts: `grep quickspi /proc/interrupts` — count should increase on touch
4. Check device power: `cat /sys/bus/pci/devices/$BDF/power/runtime_status` — must be "active"
5. If interrupt count NOT increasing: SPI/I2C bus issue, check with logic analyzer
6. If interrupt count increasing but no events: HID descriptor parse failure or HID subsystem issue
7. Check `evtest` with raw mode to see if any events arrive

### 7.3 Touch Stops After Suspend/Resume

**Symptom**: Touch works before suspend but not after resume.

**Debug steps**:
1. Check resume sequence: `dmesg | grep -i "quickspi.*resume\|quicki2c.*resume"`
2. Check for DMA reconfigure failure: `dmesg | grep -i "dma.*fail\|dma.*error"`
3. Check for I2C sub-IP restore failure (I2C only): `dmesg | grep -i "i2c_subip"`
4. Check PCI state: device must return to D0 after resume
5. Verify SET_POWER(ON) was sent: enable `dynamic_debug` for set_power function
6. **Known issue**: I2C save pointer bug (kernel < 6.20) — `a7fc15e` fix required for D3Cold SnR
7. Try manual unbind/bind to reset driver:
   ```bash
   echo "$BDF" > /sys/bus/pci/drivers/quickspi/unbind
   echo "$BDF" > /sys/bus/pci/drivers/quickspi/bind
   ```

### 7.4 WoT Not Arming

**Symptom**: System does not wake on touch from D3/S0ix.

**Debug steps**:
1. Check WoT config: `dmesg | grep -i wot` — must show successful config
2. Check wake status: `cat /sys/bus/pci/devices/$BDF/power/wakeup` — must be "enabled"
3. Check BIOS knob: `Wake on Touch` must be enabled
4. Check ACPI GPIO: ACPI tables must include `"wake-on-touch"` GpioInt resource
5. Check PADCFGLOCK: vGPIO_THC pad must be unlocked (PADCFGLOCK = 0x0)
6. SPI path: Linux has **NO WoT handling** in SPI suspend — WoT from SPI is not expected to work
7. I2C path: `device_may_wakeup()` must return true for SET_POWER(SLEEP) to be skipped
8. See `fv-thc/wot` sub-skill for detailed WoT architecture and debug

### 7.5 I2C NAK Storm

**Symptom**: Continuous I2C NAK responses; dmesg shows I2C errors.

**Debug steps**:
1. Check I2C target address: driver default is `0x0A` — verify against touch device datasheet
2. Check I2C speed mode: Fast Mode (400K) is typical; verify IC_CON configuration
3. Check I2C sub-IP enable: IC_ENABLE must be set after IC_CON configuration
4. Capture I2C bus waveform with logic analyzer
5. Check SPI_RD_MPS workaround: THC uses `SPI_RD_MPS` even in I2C mode — must be set to 4096
6. Check for I2C bus stuck (SDA held low): Windows has bus clear recovery; **Linux does NOT enable bus clear**

### 7.6 DMA Timeout During Operation

**Symptom**: Touch works initially, then stops. dmesg shows DMA timeout.

**Debug steps**:
1. Check interrupt delivery: `/proc/interrupts` count should still be increasing
2. If interrupts stop: device may have entered a bad state — check SPI/I2C bus
3. If interrupts continue but DMA times out: DMA engine may be stuck
4. Check DMA pause status via PySV: `thc0.port.mem.thc_m_prt_int_sts.read()`
5. Linux DMA pause timeout: **100µs interval, 10ms total** (much shorter than Windows 10µs/1s)
6. Check IOMMU for DMA mapping errors: `dmesg | grep -i "iommu\|dmar"`

---

## 8. Performance Analysis

### 8.1 evtest for Touch Event Rates

```bash
# Install evtest
apt install evtest  # or equivalent

# Run evtest to monitor touch events
evtest /dev/input/eventX

# Look for:
# - Event rate: should match device report rate (typically 100-240 Hz for touch)
# - Event types: EV_ABS for touch coordinates, EV_KEY for buttons
# - Latency: timestamp delta between events should be consistent
```

### 8.2 perf for Interrupt Latency

```bash
# Trace THC interrupt handler with timing
perf trace -e irq:irq_handler_entry,irq:irq_handler_exit --filter 'name=="quickspi"' -a

# Record interrupt latency histogram
perf record -e irq:irq_handler_entry --filter 'name=="quickspi"' -a -- sleep 10
perf script | awk '{print $4}' | sort -n | uniq -c  # timestamp distribution
```

### 8.3 DMA Throughput

```bash
# Monitor PCI bandwidth (rough)
# THC touch data at 240Hz * ~1KB report = ~240KB/s (low bandwidth)
# DMA issues are typically latency, not throughput

# perf stat for cache misses during DMA
perf stat -e cache-misses,cache-references -p $(pgrep -f quickspi) -- sleep 10
```

---

## 9. ACPI Table Inspection

### 9.1 Dump THC ACPI Device

```bash
# Dump all ACPI tables
acpidump > acpi_tables.dat
acpixtract -a acpi_tables.dat
iasl -d *.dat

# Search for THC device in DSDT
grep -n -i "THC\|THCE\|THCF\|QuickSPI\|QuickI2C" dsdt.dsl

# Look for:
# - _HID: device identification
# - _CRS: current resources (GPIO, memory, interrupt)
# - _DSM: device-specific methods (WoT GPIO, SPI config)
# - _PS0/_PS3: power state methods
# - _PRW: power resources for wake
# - _RST: reset method
```

### 9.2 Check WoT ACPI GPIO

```bash
# Find wake-on-touch GPIO in ACPI
grep -n "wake-on-touch\|WakeOnTouch\|GpioInt" dsdt.dsl | head -20

# Verify GPIO resource exists — if absent, WoT will silently degrade
```

---

## 10. Kernel Crash / Panic Debug

### 10.1 THC-Related Panic Signatures

| Panic Pattern | Root Cause | Debug Action |
|---------------|-----------|-------------|
| `BUG: unable to handle page fault ... thc_dma_*` | DMA buffer corrupted or freed while in use | Check IOMMU, verify DMA coherency |
| `rcu_sched self-detected stall ... quickspi` | Interrupt storm, IRQ handler taking too long | Check spurious interrupts, IRQ count |
| `NMI watchdog: hard LOCKUP ... thc_interrupt_handler` | Deadlock in interrupt handler | Check for recursive lock in DMA/PIO path |
| `kernel NULL pointer dereference ... i2c_subip_*` | I2C sub-IP pointer not initialized | Check probe sequence, verify I2C port type selected |
| `WARNING: CPU: X PID: Y at ... thc_dma_configure` | DMA configuration assertion failure | Check PRD ring allocation, IOMMU mapping |

### 10.2 Collecting Crash Data

```bash
# Check for kernel crash dumps
ls /var/crash/ 2>/dev/null
ls /var/log/kern.log* 2>/dev/null

# Enable persistent logging for crash survival
mkdir -p /var/log/journal
systemctl restart systemd-journald

# Serial console capture (most reliable for hard lockups)
# Configure kernel cmdline: console=ttyS0,115200n8
# Capture via UART → TTK3 UART skill
```

---

## 11. GPIO Pad Debug (pinctrl-intel)

### 11.1 Check GPIO Pad Configuration

```bash
# List all GPIO controllers
ls /sys/bus/platform/drivers/intel-pinctrl/

# Find THC-related GPIO pads
# Method 1: Check ACPI GPIO mapping
cat /sys/firmware/acpi/tables/DSDT | iasl -d /dev/stdin 2>/dev/null | grep -i thc

# Method 2: Use gpioinfo (part of libgpiod)
gpioinfo | grep -i "thc\|touch\|wake"
```

### 11.2 vGPIO Pad Status (for WoT debug)

```bash
# vGPIO pad config — requires PySV or direct MMIO access
# Cannot be read from standard sysfs on most platforms
# Use PySV for direct register access:
#   pcd.gpio.com3.sb.gpio_mem_3.pad_cfg_dw0_vgpio_thc0.show()

# Check PADCFGLOCK via PySV:
#   Read GPIO PADCFGLOCK register for vGPIO_THC0 pad
#   Must be 0x0 (unlocked) for WoT to work
```

---

## 12. Linux-Specific Triage Decision Tree

```
Touch not working on Linux?
│
├─ lspci shows THC device?
│  ├─ No → Check BIOS THC enable, Function Disable, PCI enumeration
│  └─ Yes ↓
│
├─ dmesg shows probe success?
│  ├─ No → Check probe failure signature (Section 1.2)
│  └─ Yes ↓
│
├─ /proc/interrupts count increasing on touch?
│  ├─ No → Bus issue: check SPI/I2C waveform with logic analyzer
│  │       Check GPIO interrupt routing, MSI config
│  └─ Yes ↓
│
├─ evtest shows touch events?
│  ├─ No → HID layer issue: check report descriptor, HID subsystem
│  │       Check DMA: dmesg for DMA errors
│  └─ Yes ↓
│
├─ Issue is after suspend/resume?
│  ├─ Yes → Check resume path (Section 7.3)
│  │        Check I2C save pointer fix (kernel < 6.20)
│  │        Check SET_POWER(ON) sent
│  │        Check register restore
│  └─ No ↓
│
├─ Issue is WoT-related?
│  ├─ Yes → See WoT triage (Section 7.4)
│  │        Check PADCFGLOCK, BIOS knob, ACPI GPIO
│  │        SPI: no Linux WoT handling
│  └─ No ↓
│
└─ Intermittent/stress failure?
   ├─ DMA timeout → Section 7.6
   ├─ I2C NAK → Section 7.5
   └─ Kernel panic → Section 10
```

---

## See Also

- **`fv-thc/debug`** (shared SKILL.md) — Common triage flow, HSDES sighting DB, failure signatures, debug playbooks, known errata
- **`fv-thc/debug`** (windows.md) — WPP tracing, ETW, registry keys, telemetry, Windows-specific workarounds
- **`fv-thc/wot`** (linux.md) — WoT Linux implementation, pinctrl-intel architecture, S4 vGPIO investigation
- **`fv-thc/dma`** (linux.md) — DMA pause timeout (100µs/10ms), DMA buffer management
- **`fv-thc/power`** (linux.md) — Linux PM callbacks, LTR config, runtime PM
- **`fv-thc/hidspi`** (linux.md) — QuickSPI Linux probe, SET_POWER fire-and-forget
- **`fv-thc/hidi2c`** (linux.md) — QuickI2C Linux probe, IC_CON 0x663, I2C sub-IP init
- **`fv-thc/driver`** (linux.md) — Full Linux driver source analysis
- **`fv-thc/registers`** — THC register maps, PIO opcodes, MMIO offsets
