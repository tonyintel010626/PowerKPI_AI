# TTL ISH Sensor Framework
## Source: ISH5p9 HAS via Co-De Sign (extracted 2026-03-16)

## 1. Supported Sensor Types

| Sensor Type | Description |
|-------------|-------------|
| Ambient Light Sensor (ALS) | Measures ambient light levels |
| Gyroscope | Angular velocity measurement |
| Accelerometer | Linear acceleration measurement |
| Compass (Magnetometer) | Magnetic field measurement |
| Proximity Sensor | Object proximity detection |
| Barometer | Atmospheric pressure measurement |

## 2. Supported Sensor Interfaces

| Interface | Count | Max Speed | Notes |
|-----------|-------|-----------|-------|
| I2C | Up to 3 controllers | 1 Mb/s | Standard sensor interface |
| I3C | Up to 2 controllers | 25 Mb/s (HDR/DDR) | High-speed sensor interface |
| SPI | Up to 2 controllers | 25 Mb/s | High-throughput sensors |
| UART | Up to 3 controllers | 4 Mb/s | Serial debug/sensor |
| GPIO | Up to 11-12 ISH GPIOs | N/A | Muxed with other GPIOs at product level |

> **Note**: Exact GPIO/interface count varies by SKU (PCD-H, PCD-S, PCH-S)

## 3. Sensor Hub Protocol & Data Formats

- Samples sensor data in **all S0/S0ix states** (always-on, always-sensing)
- Data formats:
  - HID over I2C
  - MCTP (Management Component Transport Protocol)
  - Custom firmware-defined protocols
- **Hammock Harbor** time synchronization for accurate timestamping across ISH and host

## 4. Virtual Sensors & Sensor Fusion

- Combines multiple physical sensors into **virtual sensors**:
  - Orientation detection
  - Activity recognition
  - Context awareness
  - Gesture detection
  - Motion tracking
  - Environmental awareness
- Algorithms run on embedded **LMT 3.9 core**, offloading computation from host CPU
- Reduces host power consumption by processing sensor data locally

## 5. Sensor Enumeration & Discovery

- FW enumerates sensors at boot or hot-plug events
- Exposes sensor list via:
  - ACPI tables
  - HID descriptors
  - Custom IPC messages
- Dynamic enable/disable/reconfigure based on:
  - Platform policy
  - OS requests
  - Power state transitions

## 6. Data Reporting Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| Event-driven | Threshold/event triggered | Motion detection, proximity alerts |
| Periodic | Fixed-rate sampling | Continuous monitoring |
| Buffered/Batched | Collected and sent in batches | Reduce host wakeups in low-power |

- **Rates**: Configurable per sensor
  - High-frequency: Real-time applications
  - Low-frequency: Background monitoring

## 7. Wake-on-Sensor Events

- ISH generates **wake signals** on sensor events:
  - Movement detection
  - Proximity change
  - Gesture recognition
- Active in **deep low-power S0ix states**
- Events routed to:
  - Host (for OS processing)
  - CSME (for security events)
  - PMC (for power state changes)
- Based on platform configuration and wake policy
