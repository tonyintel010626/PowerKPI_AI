# FV-ISH Sensors Skill

## Skill Identity

**Skill**: `fv-ish/sensors`
**Domain**: ISH Sensor Integration, HID Sensor Class Compliance, Report Descriptors
**Owner**: Leem, Yi Jie (`yleem`) — CVE - ISH Validation
**Last Updated**: 2026-03-16
**Primary Platform**: NVL (Nova Lake) — TTL interface data provided, other platforms noted where different

> Load this skill when the user asks about: sensor enumeration, HID sensor reports, sensor data formats, calibration, sampling rates, multi-sensor coordination, sensor BOM, I2C/I3C/SPI/UART interfaces, GPIO, or HID compliance validation.

---

## IMPORTANT: HAS-First Policy

**Always load `fv-ish/has` first** for any question involving sensor-specific register addresses, firmware message formats, or platform-specific sensor configurations. Content in this skill now includes verified TTL ISH 5.9 interface data from OSXML PDFs. NVL-specific sensor BOM should be verified against NVL HAS when available.

---

## TTL Sensor IO Interfaces (ISH 5.9 — Verified from OSXML)

### Interface Summary
| Interface | Count | Max Speed | MIA Base Address | Stride | Controller IP |
|-----------|-------|-----------|------------------|--------|---------------|
| **I2C** | 3 | 1 Mb/s (Fast Mode+) | `0x00000000` | `0x2000` | DW_apb_i2c |
| **I3C** | 2 | 25 Mb/s (HDR-DDR) | `0x04800000` | `0x2000` | HCI v1.0 |
| **SPI** | 2 | 25 Mb/s | `0x08000000` | `0x2000` | DW_apb_ssi |
| **UART** | 3 | 4 Mb/s | `0x08100000` | `0x2000` | DW_apb_uart |
| **GPIO** | up to 12 | N/A | `0x00100000` | — | Custom ISH GPIO |

### I2C Controller Registers (DW_apb_i2c)
Each I2C instance provides a full DesignWare I2C register set:

| Register | Offset | Description |
|----------|--------|-------------|
| IC_CON | 0x00 | Control: master/slave mode, speed, addressing |
| IC_TAR | 0x04 | Target address for master mode |
| IC_SAR | 0x08 | Slave address |
| IC_DATA_CMD | 0x10 | Read/write data + command bits |
| IC_SS_SCL_HCNT | 0x14 | Standard speed SCL high count |
| IC_SS_SCL_LCNT | 0x18 | Standard speed SCL low count |
| IC_FS_SCL_HCNT | 0x1C | Fast mode SCL high count |
| IC_FS_SCL_LCNT | 0x20 | Fast mode SCL low count |
| IC_INTR_STAT | 0x2C | Interrupt status |
| IC_INTR_MASK | 0x30 | Interrupt mask |
| IC_RAW_INTR_STAT | 0x34 | Raw interrupt status |
| IC_CLR_INTR | 0x40 | Clear all interrupts |
| IC_ENABLE | 0x6C | Enable/disable controller |
| IC_STATUS | 0x70 | Controller status (activity, TX/RX FIFO) |
| IC_TXFLR | 0x74 | TX FIFO level |
| IC_RXFLR | 0x78 | RX FIFO level |

**Instance Addresses**: I2C0 = `0x00000000`, I2C1 = `0x00002000`, I2C2 = `0x00004000`

### I3C Controller Registers (HCI v1.0)
Each I3C instance provides MIPI I3C HCI-compliant registers:

| Register | Offset | Description |
|----------|--------|-------------|
| HCI_VERSION | 0x00 | HCI version (v1.0) |
| HC_CONTROL | 0x04 | Host controller control |
| MASTER_DEVICE_ADDR | 0x08 | Controller dynamic address |
| HC_CAPABILITIES | 0x0C | Capability flags (HDR-DDR, HDR-TS, IBI) |
| RESET_CTRL | 0x10 | Soft reset control |
| PRESENT_STATE | 0x14 | Bus state, activity |
| INTR_STATUS | 0x20 | Interrupt status |
| INTR_ENABLE | 0x24 | Interrupt enable |
| DAT_SECTION | 0x30 | Device Address Table section offset |
| DCT_SECTION | 0x34 | Device Characteristic Table offset |
| RING_HEADERS_SECTION | 0x38 | Ring/queue header section |
| PIO_SECTION | 0x3C | PIO section offset |
| COMMAND_QUEUE_PORT | 0x100 | Command queue FIFO |
| RESPONSE_QUEUE_PORT | 0x104 | Response queue FIFO |
| TX_DATA_PORT | 0x108 | TX data FIFO |
| RX_DATA_PORT | 0x10C | RX data FIFO |
| IBI_PORT | 0x110 | In-Band Interrupt data |

**I3C Capabilities**: HDR-DDR (25 Mb/s), HDR-TS, IBI (In-Band Interrupt), Dynamic Address Assignment

**Instance Addresses**: I3C0 = `0x04800000`, I3C1 = `0x04802000`

### SPI Controller Registers (DW_apb_ssi)

| Register | Offset | Default | Description |
|----------|--------|---------|-------------|
| CTRLR0 | 0x00 | — | Frame format, data size, clock polarity/phase |
| CTRLR1 | 0x04 | — | Number of data frames (receive-only mode) |
| SSIENR | 0x08 | 0x0 | SSI enable: [0]=enable |
| MWCR | 0x0C | — | Microwire control |
| SER | 0x10 | — | Slave select enable |
| BAUDR | 0x14 | — | Baud rate divisor (SPI clock = source / BAUDR) |
| TXFTLR | 0x18 | — | TX FIFO threshold level |
| RXFTLR | 0x1C | — | RX FIFO threshold level |
| TXFLR | 0x20 | — | TX FIFO level (number of entries) |
| RXFLR | 0x24 | — | RX FIFO level (number of entries) |
| SR | 0x28 | — | Status: [0]=BUSY, [1]=TFNF, [2]=TFE, [3]=RFNE, [4]=RFF |
| IMR | 0x2C | — | Interrupt mask |
| ISR | 0x30 | — | Interrupt status |
| RISR | 0x34 | — | Raw interrupt status |
| ICR | 0x48 | — | Clear all interrupts |
| DR0 | 0x60 | — | Data register (TX/RX FIFO access) |

**Instance Addresses**: SPI0 = `0x08000000`, SPI1 = `0x08002000`

### UART Controller Registers (DW_apb_uart)

| Register | Offset | Description |
|----------|--------|-------------|
| RBR/THR/DLL | 0x00 | Receive Buffer / Transmit Holding / Divisor Latch Low |
| IER/DLH | 0x04 | Interrupt Enable / Divisor Latch High |
| IIR/FCR | 0x08 | Interrupt ID / FIFO Control |
| LCR | 0x0C | Line Control (data bits, stop bits, parity) |
| MCR | 0x10 | Modem Control |
| LSR | 0x14 | Line Status ([0]=DR, [5]=THRE, [6]=TEMT) |
| MSR | 0x18 | Modem Status |
| USR | 0x1F | UART Status ([0]=BUSY, [1]=TFNF, [2]=TFE, [3]=RFNE, [4]=RFF) |

**Max Baud Rate**: 4 Mb/s
**Instance Addresses**: UART0 = `0x08100000`, UART1 = `0x08102000`, UART2 = `0x08104000`

### GPIO Controller Registers

ISH provides up to 12 GPIO pins for sensor interrupt lines, wake signals, and control:

| Register | Offset | Description |
|----------|--------|-------------|
| GPLR | 0x00 | GPIO Pin Level Read (current state of all pins) |
| GPDR | 0x04 | GPIO Direction: 0=input, 1=output |
| GPSR | 0x08 | GPIO Set: write 1 to set output high |
| GPCR | 0x0C | GPIO Clear: write 1 to set output low |
| GRER | 0x10 | GPIO Rising Edge detect Enable |
| GFER | 0x14 | GPIO Falling Edge detect Enable |
| GIMR | 0x18 | GPIO Interrupt Mask: 1=masked (disabled) |
| GISR | 0x1C | GPIO Interrupt Status (W1C) |
| GWMR | 0x20 | GPIO Wake Mask: 1=wake enabled |
| GWSR | 0x24 | GPIO Wake Status (W1C) |

**Base Address**: `0x00100000`

**Common GPIO Assignments**:
| GPIO Pin | Typical Function | Direction |
|----------|-----------------|-----------|
| GPIO0–GPIO2 | Sensor interrupt lines (accel, gyro, mag) | Input |
| GPIO3 | ALS interrupt | Input |
| GPIO4–GPIO5 | I3C IBI (In-Band Interrupt) routing | Input |
| GPIO6–GPIO7 | Sensor power enable | Output |
| GPIO8–GPIO11 | Platform-specific / spare | Configurable |

---

## Supported Sensor Types

### 1. Accelerometer (3-Axis)
- **Function**: Measures linear acceleration (X/Y/Z axes), orientation, tilt detection, free-fall detection
- **HID Usage Page**: `0x0020` (Sensor)
- **HID Usage ID**: `0x0073` (Motion — Accelerometer 3D)
- **Typical Range**: ±2g / ±4g / ±8g / ±16g (configurable)
- **Output Rate**: 1 Hz – 400 Hz
- **Units**: g (gravity) or m/s²
- **ISH Interface**: I2C or I3C (preferred for higher ODR)
- **Common Vendors (NVL BOM)**: Bosch (BMI series), STMicroelectronics (LSM series), InvenSense (ICM series)

### 2. Gyroscope (3-Axis)
- **Function**: Measures angular velocity (roll, pitch, yaw)
- **HID Usage Page**: `0x0020`
- **HID Usage ID**: `0x0076` (Motion — Gyrometer 3D)
- **Typical Range**: ±125 dps / ±250 dps / ±500 dps / ±2000 dps
- **Output Rate**: 1 Hz – 400 Hz
- **Units**: degrees/second (dps) or radians/second
- **ISH Interface**: I2C or I3C (often combo sensor with accelerometer)
- **Common Vendors**: Bosch (BMI series), STMicro (LSM series), InvenSense (ICM series)

### 3. Magnetometer (3-Axis)
- **Function**: Measures magnetic field strength for compass/heading
- **HID Usage Page**: `0x0020`
- **HID Usage ID**: `0x0083` (Orientation — Compass 3D)
- **Typical Range**: ±4900 µT
- **Output Rate**: 1 Hz – 100 Hz
- **Units**: microtesla (µT) or gauss
- **ISH Interface**: I2C
- **Common Vendors**: Bosch (BMM series), AKM (AK series), PNI (RM series)

### 4. Ambient Light Sensor (ALS)
- **Function**: Measures ambient illuminance for display brightness control
- **HID Usage Page**: `0x0020`
- **HID Usage ID**: `0x0041` (Light — Ambient Light)
- **Typical Range**: 0 – 100,000 lux
- **Output Rate**: 1 Hz – 50 Hz
- **Units**: lux (lx)
- **ISH Interface**: I2C
- **Common Vendors**: Vishay (VCNL series), AMS (TSL/TCS series), STMicro (VD6283)

### 5. Proximity Sensor
- **Function**: Detects presence/absence of nearby objects (typically for lid/palm detection)
- **HID Usage Page**: `0x0020`
- **HID Usage ID**: `0x011A` (Presence — Human Proximity)
- **Detection Range**: 0 – 200 mm (typical)
- **Output**: Binary (near/far) or raw ADC count
- **ISH Interface**: I2C
- **Common Vendors**: Vishay (VCNL series), AMS (TMD series)

### 6. Custom / Vendor-Specific Sensors
- **Function**: Platform-specific sensors not covered by standard HID usage tables
- **HID Usage Page**: `0xFF00`–`0xFFFF` (vendor-defined)
- **Examples**: Hinge angle sensor (I3C), ambient temperature, UV sensor
- **ISH Interface**: Any (I2C, I3C, SPI, UART)
- **NVL Note**: Check platform BOM in `fv-ish/platform` for NVL-specific custom sensors

---

## Sensor Interface Selection Guide

### I2C vs I3C vs SPI Decision Matrix

| Factor | I2C (FM+) | I3C (HDR-DDR) | SPI |
|--------|-----------|---------------|-----|
| **Max Speed** | 1 Mb/s | 25 Mb/s | 25 Mb/s |
| **Pin Count** | 2 (SDA, SCL) | 2 (SDA, SCL) | 4+ (MOSI, MISO, CLK, CS) |
| **Multi-device** | Yes (address) | Yes (dynamic addr) | Yes (per-CS) |
| **In-Band Interrupt** | No (needs GPIO) | Yes (IBI) | No (needs GPIO) |
| **Power** | Low | Low-medium | Medium |
| **Best For** | Low-ODR sensors | High-ODR sensors, IBI | High-throughput, display sensors |
| **TTL Instances** | 3 | 2 | 2 |

### I3C Advantages for ISH 5.9
- **IBI (In-Band Interrupt)**: Sensor can signal data-ready on the bus without a dedicated GPIO pin
- **HDR-DDR mode**: 25 Mb/s for high-throughput sensors
- **Dynamic Address Assignment**: No hardcoded I2C addresses, reduces BOM conflicts
- **Backward Compatible**: I3C bus can host legacy I2C devices in mixed mode

---

## HID Sensor Class Overview

### Architecture
```
Windows/Linux OS
      │
      ▼
HID Sensor Class Driver  (Windows: SensorsCx.sys / Linux: hid-sensor-hub)
      │
      ▼
ISH HID Transport Driver (Windows: IshHid.sys / Linux: ishtp-hid-client)
      │
      ▼
ISHTP/IPC Layer           (Linux: intel-ish-hid modules, IPC doorbell/mailbox)
      │
      ▼
ISH Firmware              (Sensor enumeration, data collection, fusion)
      │
      ▼
Physical Sensors          (I2C / I3C / SPI / UART connected to ISH)
```

### HID Report Types
| Report Type | Direction | Purpose |
|-------------|-----------|---------|
| **Input Report** | ISH → Host | Sensor data (periodic or on-change) |
| **Feature Report (Get)** | Host → ISH | Read sensor property (e.g., current interval) |
| **Feature Report (Set)** | Host → ISH | Write sensor property (e.g., set interval) |
| **Output Report** | Host → ISH | Rarely used for sensors |

---

## Sensor Report Descriptors

### Standard Descriptor Structure
```c
// Example: Accelerometer 3D descriptor (abbreviated)
Usage Page (Sensor),                    // 0x0020
Usage (Accelerometer 3D),               // 0x0073
Collection (Physical),
  // Report ID
  Report ID (1),

  // Sensor State
  Usage Page (Sensor),
  Usage (Sensor State),                 // 0x0201
  Logical Minimum (0),
  Logical Maximum (6),
  Report Size (8),
  Report Count (1),
  Feature (Data, Variable, Absolute),

  // Reporting Interval (ms)
  Usage (Sensor Property Reporting Interval), // 0x020E
  Logical Minimum (0),
  Logical Maximum (0x7FFFFFFF),
  Unit Exponent (-3),                   // ms
  Report Size (32),
  Report Count (1),
  Feature (Data, Variable, Absolute),

  // Sensitivity
  Usage (Sensor Property Sensitivity ABS),    // 0x0214
  Logical Minimum (0),
  Logical Maximum (0x7FFF),
  Report Size (16),
  Report Count (1),
  Feature (Data, Variable, Absolute),

  // Acceleration X/Y/Z (Input Data)
  Usage (Sensor Data Motion Acceleration X Axis), // 0x0453
  Usage (Sensor Data Motion Acceleration Y Axis), // 0x0454
  Usage (Sensor Data Motion Acceleration Z Axis), // 0x0455
  Logical Minimum (-32767),
  Logical Maximum (32767),
  Unit Exponent (-2),                   // 0.01 g per LSB
  Report Size (16),
  Report Count (3),
  Input (Data, Variable, Absolute),
End Collection,
```

### Key Descriptor Fields
| Field | Description | Example |
|-------|-------------|---------|
| **Usage Page** | Sensor category | `0x0020` = Sensors |
| **Usage ID** | Specific sensor type | `0x0073` = Accelerometer 3D |
| **Report ID** | Unique report identifier | `0x01` |
| **Logical Min/Max** | Raw data range | -32767 to 32767 |
| **Unit Exponent** | Scaling factor (power of 10) | `-2` = ×0.01 |
| **Report Size** | Bits per field | `16` = 2 bytes |
| **Report Count** | Number of fields | `3` = X, Y, Z |

---

## Sensor Properties

### Standard Properties (Feature Reports)

| Property Usage ID | Name | Description | Typical Values |
|-------------------|------|-------------|----------------|
| `0x0201` | Sensor State | Current operational state | 0=Not Available, 1=Ready, 2=Not Available, 3=Error, 4=Initializing, 5=Access Denied, 6=No Data |
| `0x0202` | Sensor Event Type | Type of event triggering report | 0=Unknown, 1=State Changed, 2=Property Changed, 3=Data Updated, 4=Poll Response, 5=Change Sensitivity |
| `0x020E` | Reporting Interval | Time between reports (ms) | 10–65535 ms |
| `0x0214` | Sensitivity ABS | Min change to trigger report | Sensor-specific |
| `0x0215` | Sensitivity REL PCT | Relative sensitivity (%) | 0–100% |
| `0x0216` | Maximum | Max reported value | Sensor-specific |
| `0x0217` | Minimum | Min reported value | Sensor-specific |
| `0x021C` | Connection Type | How sensor connects to ISH | 1=PC Integrated, 2=PC Attached, 3=PC External |
| `0x0222` | Power State | Desired power state | 0=Undefined, 1=D0 Full Power, 2=D1 Low Power, 3=D2 Standby with Wake, 4=D3 Sleep with Wake, 5=D4 Power Off |

### Power State Values
```
0: Sensor Power State Undefined
1: Sensor Power State D0 Full Power       → Active sensing, full ODR
2: Sensor Power State D1 Low Power        → Reduced ODR, lower power
3: Sensor Power State D2 Standby With Wake → Low power, wake on threshold
4: Sensor Power State D3 Sleep With Wake   → Minimal power, wake on significant motion
5: Sensor Power State D4 Power Off         → No sensing, no wake
```

---

## Sensor Data Format

### Fixed-Point Encoding
Sensor data is encoded as fixed-point integers using `Unit Exponent` for scaling:

```
Actual Value = Raw Integer × 10^(Unit Exponent)

Example (Accelerometer, Unit Exponent = -2):
  Raw = 981  →  Actual = 981 × 10^(-2) = 9.81 m/s²  (≈ 1g)
  Raw = -200 →  Actual = -200 × 10^(-2) = -2.00 m/s²
```

### Timestamp
- ISH firmware timestamps sensor data using internal HPET timer (MIA @ `0x04700000`)
- Host driver converts ISH timestamp to system time
- Timestamp resolution: typically 1 ms (HPET dependent on clock source)

### Sample Batching Data Format
When batching is enabled, ISH delivers a batch of N samples in a single IPC/DMA transfer:
```
[Batch Header: timestamp_base, sample_count, sensor_id]
[Sample 0: delta_t, x, y, z]
[Sample 1: delta_t, x, y, z]
...
[Sample N-1: delta_t, x, y, z]
```

---

## Sensor Enumeration Flow

### Startup Sequence
```
Host Boot
    │
    ▼
ISH Firmware Loads (ROM → BUP → Main FW via DMA)
    │
    ▼
ISH FW initializes I2C/I3C/SPI controllers, probes sensors
    │
    ▼
Host Driver Establishes IPC Connection (doorbell handshake)
    │
    ▼
Host Sends: ENUM_SENSOR_REQUEST (via IPC MSG registers)
    │
    ▼
ISH Responds: ENUM_SENSOR_RESPONSE (via IPC MSG + doorbell)
    │
    ▼ (for each sensor)
Host Parses HID Descriptor
    │
    ▼
Host Registers HID Sensor Device
    │
    ▼
OS Sensor Framework Activates Sensor
    │
    ▼
Host Sends: SET_FEATURE (Power State = D0, Reporting Interval = X ms)
    │
    ▼
ISH Begins Delivering Input Reports (via IPC MSG or DMA)
```

### ISHTP Sensor Enumeration Messages
| Message Type | Direction | Description |
|-------------|-----------|-------------|
| `ENUM_SENSOR_REQUEST` | Host→ISH | Request list of available sensors |
| `ENUM_SENSOR_RESPONSE` | ISH→Host | List of sensor IDs |
| `GET_SENSOR_DESCRIPTOR` | Host→ISH | Request HID descriptor for sensor ID |
| `SENSOR_DESCRIPTOR_RESPONSE` | ISH→Host | HID descriptor bytes |
| `SET_FEATURE` | Host→ISH | Set sensor property (power state, interval, sensitivity) |
| `GET_FEATURE` | Host→ISH | Read sensor property |
| `FEATURE_RESPONSE` | ISH→Host | Response to GET_FEATURE |
| `INPUT_REPORT` | ISH→Host | Sensor data |

---

## Sensor Calibration

### Factory Calibration
- Stored in ISH firmware or dedicated EEPROM/NVRAM
- Offset (bias) and scale (gain) correction per axis
- Applied by ISH firmware before data delivery

### Runtime Calibration
- Windows: Sensor Calibration Assistant (built-in)
- Linux: Manual via sysfs or vendor utility
- Calibration data typically stored in platform NVRAM or ISH FW persistent storage

### Calibration Check in Tests
```python
# Verify accelerometer reports ~1g on Z-axis (flat surface)
accel_z = read_sensor_input_z()
GRAVITY_MS2 = 9.81
tolerance = 0.5  # m/s²
assert abs(accel_z - GRAVITY_MS2) < tolerance, \
    f"Accel Z out of range: {accel_z:.2f} m/s² (expected ~{GRAVITY_MS2})"
```

---

## Multi-Sensor Coordination

### Sensor Fusion Concepts
ISH firmware can produce composite/virtual sensors from physical sensor data:
- **Rotation Vector** = Accelerometer + Gyroscope + Magnetometer
- **Game Rotation Vector** = Accelerometer + Gyroscope (no magnetometer)
- **Linear Acceleration** = Accelerometer − Gravity component
- **Gravity** = Gravity component from accelerometer
- **Step Counter / Detector** = Accelerometer pattern analysis

### Synchronization
- ISH firmware timestamps all sensor data at acquisition time via HPET
- Fusion algorithms use these timestamps for time alignment
- Host driver preserves timestamps through to the OS sensor framework

### Composite Report Descriptors
Fusion sensors have their own HID usage IDs:
| Fusion Sensor | HID Usage ID |
|--------------|-------------|
| Rotation Vector | `0x008A` |
| Linear Acceleration | `0x007C` |
| Gravity | `0x007D` |
| Step Counter | `0x00C0` |
| Step Detector | `0x00C1` |

---

## NVL-Specific Sensor Notes

> **Note**: NVL sensor BOM details pending. Load `fv-ish/has` and query Co-De Sign for NVL-specific sensor BOM.

### NVL Sensor BOM (NVL ISH 5.8 data)
| Sensor Type | Vendor | Model | Interface | Bus Base (MIA) | ODR Range |
|------------|--------|-------|-----------|----------------|-----------|
| Accelerometer | platform BOM | platform BOM | I3C0 (HDR-DDR, IBI preferred) | I3C: 0x04800000 (dynamic I3C addressing) | 1–400 Hz |
| Gyroscope | platform BOM | platform BOM | I3C0 (shared with accelerometer) | I3C: 0x04800000 | 1–400 Hz |
| Magnetometer | platform BOM | platform BOM | I2C0 | I2C: 0x00000000 (I2C instances stride 0x2000) | 1–100 Hz |
| ALS | platform BOM | platform BOM | I2C1 | I2C: 0x00002000 | 1–50 Hz |
| Proximity | platform BOM | platform BOM | I2C1 | I2C: 0x00002000 | Binary / raw ADC (platform-defined) |

### TTL Sensor Interface Availability (ISH 5.9)
| Sensor Type | Recommended Interface | TTL Instance | Wake Capable |
|-------------|----------------------|-------------|-------------|
| Accelerometer | I3C0 (HDR-DDR, IBI) | `0x04800000` | Yes (GPIO + IBI) |
| Gyroscope | I3C0 (shared bus with accel) | `0x04800000` | Yes (IBI) |
| Magnetometer | I2C0 | `0x00000000` | Yes (GPIO interrupt) |
| ALS | I2C1 | `0x00002000` | Yes (GPIO interrupt) |
| Proximity | I2C1 (shared bus with ALS) | `0x00002000` | Yes (GPIO interrupt) |
| Custom (hinge) | I3C1 | `0x04802000` | Configurable |

---

## Validation Points

### 1. Sensor Enumeration
```python
def test_sensor_enumeration():
    """Verify all expected sensors are enumerated by ISH."""
    expected_sensors = ["accelerometer", "gyroscope", "magnetometer", "als"]
    enumerated = ish_get_enumerated_sensors()
    for sensor in expected_sensors:
        assert sensor in enumerated, f"Sensor not enumerated: {sensor}"
```

### 2. Report Descriptor Compliance
```python
def test_report_descriptor_compliance():
    """Parse HID descriptor and verify required fields are present."""
    descriptor = ish_get_sensor_descriptor(SENSOR_ID_ACCEL)
    parsed = hid_parse_descriptor(descriptor)
    assert parsed.usage_page == 0x0020, "Wrong usage page"
    assert parsed.usage_id == 0x0073, "Wrong usage ID (expected Accel 3D)"
    assert "reporting_interval" in parsed.feature_usages
    assert "power_state" in parsed.feature_usages
    assert "accel_x" in parsed.input_usages
    assert "accel_y" in parsed.input_usages
    assert "accel_z" in parsed.input_usages
```

### 3. Data Accuracy
```python
def test_accelerometer_data_accuracy():
    """Verify accelerometer reports valid static gravity reading."""
    samples = collect_sensor_samples(SENSOR_ID_ACCEL, count=100, interval_ms=10)
    z_values = [s.z for s in samples]
    z_mean = sum(z_values) / len(z_values)
    assert 9.31 < z_mean < 10.31, f"Accel Z mean {z_mean:.2f} out of 1g ± 0.5 range"
```

### 4. Sampling Rate Verification
```python
def test_sampling_rate():
    """Verify sensor delivers data at configured ODR."""
    target_odr_hz = 50
    interval_ms = int(1000 / target_odr_hz)
    ish_set_sensor_interval(SENSOR_ID_ACCEL, interval_ms)
    samples, elapsed_ms = collect_timed_samples(SENSOR_ID_ACCEL, duration_ms=1000)
    actual_odr = len(samples) / (elapsed_ms / 1000.0)
    assert abs(actual_odr - target_odr_hz) < 5, \
        f"ODR mismatch: expected {target_odr_hz}, got {actual_odr:.1f} Hz"
```

### 5. I2C Controller Functional
```python
def test_i2c_controller_functional():
    """Verify ISH I2C controllers are accessible and functional."""
    I2C_BASES = [0x00000000, 0x00002000, 0x00004000]
    for idx, base in enumerate(I2C_BASES):
        # Check IC_ENABLE register
        enable = read_mia_reg(base, 0x6C)
        status = read_mia_reg(base, 0x70)
        log_info(f"I2C{idx}: ENABLE=0x{enable:08X}, STATUS=0x{status:08X}")
        # If enabled, verify not stuck in TX abort
        if enable & 0x1:
            raw_intr = read_mia_reg(base, 0x34)
            assert (raw_intr & (1 << 6)) == 0, f"I2C{idx} TX_ABRT active"
```

### 6. I3C Controller and IBI
```python
def test_i3c_controller_ibi():
    """Verify I3C controller supports IBI (In-Band Interrupt)."""
    I3C_BASES = [0x04800000, 0x04802000]
    for idx, base in enumerate(I3C_BASES):
        caps = read_mia_reg(base, 0x0C)  # HC_CAPABILITIES
        ibi_capable = caps & (1 << 0)  # IBI capability bit
        hdr_ddr = caps & (1 << 3)      # HDR-DDR capability
        log_info(f"I3C{idx}: caps=0x{caps:08X}, IBI={bool(ibi_capable)}, HDR-DDR={bool(hdr_ddr)}")
        assert ibi_capable, f"I3C{idx} does not support IBI"
```

### 7. GPIO Interrupt for Sensor Wake
```python
def test_gpio_sensor_interrupt():
    """Verify GPIO interrupt routing from sensor to ISH."""
    GPIO_BASE = 0x00100000
    # Check GPIO direction (sensor interrupt pins should be inputs)
    gpdr = read_mia_reg(GPIO_BASE, 0x04)  # GPDR
    for pin in [0, 1, 2, 3]:  # Sensor interrupt pins
        assert (gpdr & (1 << pin)) == 0, f"GPIO{pin} not configured as input"
    # Check edge detect enabled
    grer = read_mia_reg(GPIO_BASE, 0x10)  # GRER (rising edge)
    gfer = read_mia_reg(GPIO_BASE, 0x14)  # GFER (falling edge)
    for pin in [0, 1, 2, 3]:
        edge_enabled = (grer & (1 << pin)) or (gfer & (1 << pin))
        assert edge_enabled, f"GPIO{pin} no edge detect enabled for sensor interrupt"
    # Check wake mask for sensor pins
    gwmr = read_mia_reg(GPIO_BASE, 0x20)  # GWMR
    for pin in [0, 1, 2, 3]:
        wake_enabled = not (gwmr & (1 << pin))  # 1=masked, 0=wake enabled
        log_info(f"GPIO{pin} wake: {'enabled' if wake_enabled else 'masked'}")
```

### 8. Property Set/Get Round-Trip
```python
def test_property_round_trip():
    """Verify sensor properties can be set and read back."""
    new_interval = 40  # ms
    ish_set_feature(SENSOR_ID_ACCEL, PROP_REPORTING_INTERVAL, new_interval)
    readback = ish_get_feature(SENSOR_ID_ACCEL, PROP_REPORTING_INTERVAL)
    assert readback == new_interval, \
        f"Interval round-trip failed: set {new_interval}, got {readback}"
```

### 9. Multi-Sensor Simultaneous Operation
```python
def test_multi_sensor_simultaneous():
    """Verify multiple sensors can operate concurrently across different interfaces."""
    sensors = [SENSOR_ID_ACCEL, SENSOR_ID_GYRO, SENSOR_ID_MAG]
    for sid in sensors:
        ish_set_sensor_power_state(sid, POWER_STATE_D0)
        ish_set_sensor_interval(sid, 20)  # 50 Hz each
    samples = {sid: [] for sid in sensors}
    time.sleep(1)
    for sid in sensors:
        samples[sid] = ish_collect_buffered_samples(sid)
        assert len(samples[sid]) > 40, f"Sensor {sid}: too few samples in 1s"
```

---

## Public References

- **HID Usage Tables for Sensor Class**: https://www.usb.org/document-library/hid-sensor-usage-tables
- **Microsoft HID Sensors Documentation**: https://learn.microsoft.com/en-us/windows-hardware/design/whitepapers/hid-sensors-usages
- **Linux ISHTP HID Client Driver**: https://github.com/torvalds/linux/blob/master/drivers/hid/intel-ish-hid/ishtp-hid-client.c
- **Linux HID Sensor Hub**: https://github.com/torvalds/linux/tree/master/drivers/iio/common/hid-sensors
- **MIPI I3C HCI Specification**: https://www.mipi.org/specifications/i3c-hci
- **ISH 5.9 MIA Register Reference**: `fv-ish/has/docs/ttl/TTL_ISH_MIA_Register_Reference.md`
