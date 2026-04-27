---
name: fv-lpss/clock-gating
description: Check clock gating status for LPSS IPs
---

# LPSS Clock Gating Check

This skill provides procedures to verify clock gating status for LPSS (Low Power Subsystem) controllers.

---

## Overview

Clock gating is a power management technique that stops clock signals to idle functional units, reducing dynamic power consumption. For LPSS devices to enter low power states (D3), their clocks must be properly gated.

### Clock Gating Types for LPSS

1. **Trunk Clock Gating** — Main clock to the LPSS IP block
2. **Functional Clock Gating** — Clocks to specific functional units within the IP
3. **Side Clock Gating** — Peripheral/interface clocks

---

## Clock Gating and D3 Relationship

**Critical:** For an LPSS device to successfully enter D3 power state, its functional clocks must be gated. If clocks remain active while the device attempts D3 entry, the transition will fail.

**Verification flow:**
1. Check if device is idle (no active transactions)
2. Verify functional clocks are gated
3. Confirm device can enter D3

---

## PythonSV Procedure

### Initialization

```python
import namednodes
import baseaccess

# Initialize ITP and PythonSV
itp.unlock()
sv.refresh()
```

### Clock Gating Register Search

**TODO:** Replace with actual LPSS clock gating register paths for your platform.

```python
# Search for LPSS clock gating related registers
clock_gate_regs = namednodes.sv.socket0.pcd.search(
    regexpression="lpss.*clk.*gate|lpss.*clk.*ctrl|lpss.*pwr.*gate",
    searchType="registers"
)

for reg in clock_gate_regs:
    print(f"Register: {reg}")
    print(f"  Path: {reg.path}")
    print(f"  Current Value: {reg.read()}")
    print(f"  Specification: {reg.getspec()}")
```

---

## Per-Port Clock Gating Verification

### I2C Controllers

**TODO:** Add actual I2C clock gating register paths.

```python
# Example structure (replace with actual register paths)
# i2c0_clk_gate = namednodes.sv.socket0.uncore.lpss.i2c0.clock_gate_ctrl

# Expected behavior:
# - When I2C controller is idle → clock should be gated (bit = 1)
# - When I2C controller is active → clock running (bit = 0)
```

**Checks:**
- Read clock gate control register for each I2C controller
- Verify clock is gated when controller is idle
- Verify clock is ungated during active transfers

---

### I3C Controllers

**TODO:** Add actual I3C clock gating register paths.

```python
# Example structure (replace with actual register paths)
# i3c0_clk_gate = namednodes.sv.socket0.uncore.lpss.i3c0.clock_gate_ctrl
```

**Checks:**
- Same as I2C: verify clock gating status matches controller activity state

---

### SPI Controllers

**TODO:** Add actual SPI clock gating register paths.

```python
# Example structure (replace with actual register paths)
# spi0_clk_gate = namednodes.sv.socket0.uncore.lpss.spi0.clock_gate_ctrl
```

**Checks:**
- Verify SPI functional clock gating when idle
- Check if CS (Chip Select) activity prevents clock gating

---

### UART Controllers

**TODO:** Add actual UART clock gating register paths.

```python
# Example structure (replace with actual register paths)
# uart0_clk_gate = namednodes.sv.socket0.uncore.lpss.uart0.clock_gate_ctrl
```

**Checks:**
- Verify UART clock gating when no TX/RX activity
- Check if FIFO non-empty prevents clock gating

---

### GPIO Controllers

**TODO:** Add actual GPIO clock gating register paths.

```python
# Example structure (replace with actual register paths)
# gpio_clk_gate = namednodes.sv.socket0.uncore.lpss.gpio.clock_gate_ctrl
```

**Checks:**
- Verify GPIO block clock gating
- Check if interrupt pending prevents clock gating

---

## Common Clock Gating Issues

### Issue: Clock Stuck Active (Not Gating)

**Symptoms:**
- Clock gating register shows clock not gated when device is idle
- Device unable to enter D3
- Higher than expected idle power consumption

**Root Causes:**
1. **Pending Transaction** — Controller thinks it has work to do
   - Check FIFO status registers
   - Check transfer-in-progress status bits
   
2. **Software Control Override** — OS/driver preventing clock gating
   - Check software clock gate enable bits
   - Verify driver has released clock gate override
   
3. **Hardware Bug** — Clock gating logic malfunction
   - Check for known hardware errata
   - Verify hardware clock gating enable fuses

**Debug Steps:**
```python
# 1. Read controller status register
# TODO: Replace with actual status register path
# status = namednodes.sv.socket0.uncore.lpss.i2c0.status.read()

# 2. Check for active transactions
# Look for bits indicating: TX in progress, RX in progress, FIFO not empty

# 3. Check software override
# Look for software clock gate disable bits

# 4. Check hardware enable
# Verify hardware clock gating is not fused off
```

---

### Issue: Clock Gating Too Aggressive

**Symptoms:**
- Transfers fail or timeout
- Device malfunction after idle period

**Root Causes:**
1. **Incorrect Clock Gate Timing** — Clock gated before transaction complete
2. **Missing Clock Ungating** — Clock not properly restored when needed

---

## Verification Checklist

For each LPSS port (I2C, I3C, SPI, UART, GPIO):

- [ ] Identify clock gating control registers
- [ ] Verify clock is running during active transfers
- [ ] Verify clock is gated when device is idle
- [ ] Check software clock gate enable bits are set correctly
- [ ] Verify hardware clock gating is enabled (not fused off)
- [ ] Confirm clock gating status before D3 entry attempt
- [ ] Check for clock gating related error status bits

---

## Related Skills

- **`fv-lpss/d3-state-check`** — Verify D3 entry (requires clock gating first)
- **`fv-lpss/register-checkout`** — General register value verification
- **`fv-lpss/ip-config`** — IP configuration and enumeration

---

## TODO Summary

**Platform-Specific Information Needed:**

1. **Clock Gating Register Paths** — Actual PythonSV paths for clock gating control registers for each LPSS port
2. **Expected Values** — Clock gated vs not gated bit encodings
3. **Status Register Paths** — Registers indicating controller activity state
4. **Software Override Register Paths** — OS/driver controlled clock gate enable bits
5. **Hardware Fuse Paths** — Registers indicating if clock gating is hardware-enabled

Once this information is available, update the TODO sections with actual register paths and expected values.
