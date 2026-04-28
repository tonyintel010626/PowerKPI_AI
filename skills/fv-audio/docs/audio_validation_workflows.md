# Audio Validation Workflows — Detailed Reference
> **Owner**: huiyingt (Tan Hui Ying)

> **Companion to**: FV-AUDIO agent `COMMON VALIDATION WORKFLOWS` section
> **Platform**: NVL (Novalake) — Windows only
> **Last Updated**: 2026-03-30

---

## 1. Audio Device Enumeration Checkout

**Goal**: Verify ACE audio PCI device is enumerated with correct DID/VID and BAR allocation.

### Steps

1. **Check PCI config space**:
   ```
   # Windows Device Manager → Sound, video and game controllers
   # Look for "Intel Smart Sound Technology" or "Intel Audio Controller"

   # PythonSV (if probe connected):
   pci_read(0, 31, 3, 0x00)   # Should return DID:VID
   # PCD-H: 0xD3288086  (DID=0xD328, VID=0x8086)
   # PCH-S: 0xD2288086  (DID=0xD228, VID=0x8086)
   ```

2. **Verify BAR0 (MMIO base)**:
   ```
   pci_read(0, 31, 3, 0x10)   # BAR0 — 64-bit MMIO base address
   # Should be non-zero, 64KB aligned
   ```

3. **Verify PCI Command register**:
   ```
   pci_read(0, 31, 3, 0x04)   # Command register
   # Bit 1 (Memory Space Enable) = 1
   # Bit 2 (Bus Master Enable) = 1
   ```

4. **Check MMIO accessibility**:
   ```
   # Read GCAP (Global Capabilities) at BAR0+0x00
   # Should show codec count, stream counts
   ```

### Pass Criteria
- DID matches expected platform (0xD328 for PCD-H, 0xD228 for PCH-S)
- VID = 0x8086
- BAR0 is non-zero and 64KB aligned
- Memory Space and Bus Master enabled
- GCAP readable and showing expected capabilities

### Common Failures
- DID = 0xFFFF → Device not enumerated (check BIOS audio enable knob)
- BAR0 = 0 → BAR not assigned (check BIOS resource allocation)
- Bus Master not set → Driver not loaded or initialization failed

---

## 2. HDA Codec Discovery

**Goal**: Verify HDA codecs are discovered on SDI pins and respond to verb commands.

### Steps

1. **Check STATESTS (Status Change Status)**:
   ```
   # Read BAR0+0x0E (STATESTS)
   # Bit 0 = SDI0 codec present
   # Bit 1 = SDI1 codec present
   # NVL expects: SDI0 = Realtek HDA codec, SDI1 = iDisp (display audio)
   ```

2. **Send codec identification verb**:
   ```
   # Via CORB/RIRB or Immediate Command:
   # Verb: Root Node (NID=0), Get Parameter (verb=0xF00), Vendor ID (param=0x00)
   # Command word: 0x000F0000
   # Expected responses:
   #   Realtek ALC-series: VID starts with 0x10EC
   #   Intel iDisp: VID = 0x8086XXXX
   ```

3. **Enumerate function groups**:
   ```
   # Get Subordinate Node Count: NID=0, verb=0xF00, param=0x04
   # Walk all nodes to discover AFGs (Audio Function Groups)
   ```

4. **Verify CORB/RIRB DMA**:
   ```
   # CORBCTL (BAR0+0x4C): bit 1 (CORBRUN) = 1
   # RIRBCTL (BAR0+0x5C): bit 1 (RIRBDMAEN) = 1
   # CORBRP/CORBWP should advance when verbs are sent
   ```

### Pass Criteria
- At least one SDI pin shows codec present in STATESTS
- Codec VID matches expected hardware BOM
- CORB/RIRB DMA running (CORBRUN=1, RIRBDMAEN=1)
- Verb responses received (RIRBWP advances)

### Known Issue
- **BUG-001**: CORB/RIRB DMA stall on first command after D3→D0 transition. Workaround: toggle CORBRUN bit. See `audio_known_issues.md`.

---

## 3. SoundWire Link Bring-Up

**Goal**: Verify SoundWire controller links enumerate and discover attached slaves.

### Steps

1. **Check link status for each segment**:
   ```
   # SoundWire MMIO region within ACE BAR
   # For each segment (0-4 on PCD-H, 0-2 on PCH-S):
   #   Read link status register
   #   Check: Clock running, Frame shape configured, Slave(s) attached
   ```

2. **Verify slave enumeration**:
   ```
   # Each SoundWire slave has a 48-bit Device ID
   # Slave status should show ATTACHED state
   # NVL PCD-H typical:
   #   Seg0: HDA alt path (or Realtek SoundWire codec)
   #   Seg2: AIOC ALC1320 (multilane segment)
   #   Seg4: Additional peripherals
   ```

3. **Check clock stop capability**:
   ```
   # Verify slaves support clock stop mode for power management
   # Read slave's Clock Stop Status register
   ```

### Pass Criteria
- All expected segments show clock running
- Slave devices enumerated with correct Device IDs
- Frame shape matches expected configuration
- AIOC on Seg2 (if present) shows multilane active

### Common Failures
- No slaves detected → Check physical connections, BIOS SoundWire enable knob
- Clock not running → Check ACE power state (must be in D0)
- Seg2 multilane not active → Verify BIOS AIOC configuration

---

## 4. DSP Firmware Load Verification

**Goal**: Verify DSP cores load firmware successfully and reach operational state.

### Steps

1. **Check DSP power state**:
   ```
   # PPCTL (BAR0+0x1004): DSP core power gate control
   # GPROCEN (bit 30): Global Processing Enable
   # Must be set to 1 before firmware load
   ```

2. **Verify firmware load sequence**:
   ```
   # 1. DSP cores powered on (check PPCTL)
   # 2. ROM boot completes (check ROM status register)
   # 3. FW image loaded via DMA (host initiates code load)
   # 4. FW reports RUNNING state via IPC register
   ```

3. **Check IPC (Inter-Processor Communication)**:
   ```
   # IPC registers at BAR0 offset (platform-specific)
   # Host-to-DSP doorbell, DSP-to-Host doorbell
   # FW version query via IPC message
   ```

4. **Verify core count**:
   ```
   # PCD-H: 4 HP cores + 1 ULP core
   # PCH-S: 2 HP cores + 1 ULP core
   # Check which cores are active via PPCTL
   ```

### Pass Criteria
- GPROCEN = 1
- All expected DSP cores powered on
- Firmware load completes without timeout
- IPC communication functional (FW responds to version query)
- FW version matches expected release

### Known Issue
- **BUG-003**: DSP Core 3/4 may fail to exit clock gate on PCD-H after S3 resume. See `audio_known_issues.md`.

---

## 5. S0ix Audio Power Management

**Goal**: Verify audio subsystem does not block platform S0ix entry.

### Steps

1. **Verify audio device in D3**:
   ```
   # All audio devices must be in D3 for S0ix
   # Check PCI PM capability: PMCSR (offset in PCI capabilities)
   # Bits [1:0] = 11b (D3hot)
   ```

2. **Check LTR (Latency Tolerance Reporting)**:
   ```
   # Audio LTR must not block S0ix
   # LTR value should be non-zero and within acceptable range
   # Check via: PMC Doctor script print_LTRs
   ```

3. **Verify clock stop on SoundWire links**:
   ```
   # All SoundWire links must be in clock-stop mode
   # If any slave rejects clock stop → S0ix blocked
   ```

4. **Run S0ix residency check**:
   ```
   # Use sleepstudy or PMC Doctor scripts:
   #   print_s0ix_y_blocking_conditions
   #   print_soc_s0ix_res
   # Audio should NOT appear in blocker list
   ```

5. **Test S0ix cycle**:
   ```
   # 1. Close all audio applications
   # 2. Wait for idle timeout (device enters D3)
   # 3. Trigger Modern Standby entry
   # 4. Wait 30+ seconds
   # 5. Wake and check S0ix residency counters
   ```

### Pass Criteria
- ACE device reaches D3hot when idle
- LTR values allow S0ix
- All SoundWire links enter clock stop
- S0ix residency > 0 (platform actually entered S0ix)
- Audio not listed as S0ix blocker

### Known Issues
- **HSDES sighting**: S0ix blocked by ACE when SoundWire clock stop aborts. See `audio_known_issues.md`.
- GPROCEN (PPCTL bit 30) must be de-asserted for DSP power gate — if stuck high, blocks S0ix.

---

## 6. DMIC Capture Test

**Goal**: Verify digital microphone capture works correctly.

### Steps

1. **Verify DMIC pad mode**:
   ```
   # GPIO pads for DMIC CLK and DATA must be in native function mode
   # Check pad configuration registers
   # PCD-H: 2 DMIC interfaces (DMIC0, DMIC1)
   # PCH-S: 2 DMIC interfaces
   ```

2. **Check PDMCTRL register**:
   ```
   # PDMCTRL.ClkDiv[3:1]: Power-of-2 encoding
   #   000=div1, 001=div2, 010=div4, 011=div8
   #   100(0x4)=div16, 101=div32, 110=div64, 111=div128
   # Typical: div8 (3.072MHz from 24.576MHz XTAL) for 48kHz capture
   ```

3. **Start capture stream**:
   ```
   # Windows: Sound Settings → Input → select DMIC
   # Or: use Windows Voice Recorder app
   # Or: PowerShell audio capture test script
   ```

4. **Verify audio data**:
   ```
   # Check captured samples are non-zero (not silence)
   # Check for DC offset, excessive noise, or digital clipping
   # SNR should be > 60dB for functional validation
   ```

### Pass Criteria
- DMIC CLK and DATA pads in correct pad mode
- PDMCTRL ClkDiv set to expected divisor
- Audio capture produces non-zero samples
- No excessive noise or distortion

### Common Failures
- All zeros → Check GPIO pad mode (must be native function, not GPIO)
- Very noisy → Check clock divisor (wrong divisor = wrong sample rate)
- One channel silent → Check DATA line pad mode for that DMIC

---

## 7. BT Audio Offload (SSP) Test

**Goal**: Verify Bluetooth SCO/eSCO audio offload via SSP port.

### Steps

1. **Verify SSP configuration**:
   ```
   # SSCR0.FRF = 11b (I2S/PCM format for BT audio)
   # SSP BCLK: configured for 8kHz/16kHz SCO
   # SSP port: typically SSP1 for BT offload
   ```

2. **Check CNVi BT connection**:
   ```
   # BT adapter must be connected and paired with audio device
   # HFP (Hands-Free Profile) or A2DP must be active
   # Device Manager: check BT audio device under "Sound"
   ```

3. **Start BT audio stream**:
   ```
   # Make/receive a BT HFP call (for SCO/eSCO)
   # Or: play music to BT speaker (for A2DP)
   # Route audio output to BT device in Sound Settings
   ```

4. **Verify offload path**:
   ```
   # SSP data should flow directly between ACE and CNVi
   # CPU should NOT be in the audio data path (offload = no CPU copy)
   # Check SSP active status in ACE registers
   ```

### Pass Criteria
- SSCR0.FRF = 11b (I2S/PCM mode)
- SSP port active during BT audio
- Audio plays/records correctly via BT
- CPU utilization low (confirming hardware offload)

### Known Issue
- **HSDES sighting**: SSP BCLK inversion state lost after clock gate. See `audio_known_issues.md`.

---

## 8. UAOL (USB Audio Offload) Test

**Goal**: Verify USB Audio Offload engine processes USB audio without CPU involvement.

### Steps

1. **Connect USB audio device**:
   ```
   # USB headset or DAC supporting USB Audio Class 1.0 or 2.0
   # Device should enumerate under "Sound" in Device Manager
   ```

2. **Verify UAOL engine activation**:
   ```
   # ACE UAOL registers should show offload engine active
   # xHCI endpoint should be configured for isochronous transfer
   # Check UAOL FIFO status registers
   ```

3. **Start USB audio playback/capture**:
   ```
   # Play audio to USB headset
   # Record from USB microphone
   # Both paths should use UAOL offload (not host CPU)
   ```

4. **Verify offload efficiency**:
   ```
   # CPU utilization should be minimal during USB audio
   # Audio should be glitch-free
   # Check for FIFO underrun/overrun errors in UAOL status
   ```

5. **Test behind-hub scenario** (if applicable):
   ```
   # Connect USB audio device through a USB hub
   # UAOL behind-hub support should still function
   # Verify same offload behavior as direct connection
   ```

### Pass Criteria
- USB audio device enumerated
- UAOL engine active during audio streaming
- Audio plays/records without glitches
- CPU utilization minimal (confirming offload)
- No FIFO underrun/overrun errors

---

## Quick Reference: Workflow Selection Guide

| Symptom / Task | Start With Workflow |
|-----------------|-------------------|
| No audio device in Device Manager | #1 (Enumeration) |
| Audio device present but no sound | #2 (HDA Codec) → #4 (DSP FW) |
| SoundWire device not detected | #3 (SoundWire) |
| DSP firmware load timeout | #4 (DSP FW) |
| Platform won't enter S0ix with audio | #5 (S0ix PM) |
| Microphone not working | #6 (DMIC) |
| Bluetooth audio issues | #7 (BT Offload) |
| USB headset audio issues | #8 (UAOL) |
| Audio corruption / noise | #2 (HDA) → check sample rate, clock config |
| Audio after S3/S4 resume broken | #4 (DSP FW) → check BUG-003 |
