# TTL ISH Firmware Boot Flow & Memory Map
## Source: Co-De Sign AI Query of ISH5p9 HAS + ISH BIOS Requirements (My Files)

---

## 1. Boot ROM Sequence

1. **Power-on/Reset**: LMT core begins execution from 8KB ROM
2. **ROM Bootloader**: Initiates reset sync handshake with CSE/CSME, waits for CSE to authenticate and load ISH BUP from NVM (SPI flash)
3. **ISH BUP Loading**: CSE locates, authenticates, loads ISH BUP (Intel-signed, max 64KB) into ISH IMR. BUP may include 'doomsday' ROM patch script
4. **Transition to BUP**: Control passes from ROM to BUP for further HW/memory init
5. **Main FW Loading**: ISH main FW (up to 1.5MB, Intel or OEM signed) loaded into IMR by host OS driver, authenticated by CSE upon ISH request

## 2. Memory Layout

| Region | Size | Address Range | Description |
|--------|------|---------------|-------------|
| ROM | 8KB | Boot ROM | Bootloader code |
| L2 SRAM | 640KB | 0x00000000-0x0009FFFF | 20 x 32KB banks, independently power-gatable |
| AON RF SRAM | 8KB | 0x000A0000-0x000A1FFF | Always-on retention during deep power states |
| IMR (BUP) | 64KB max | IMR offset 0 | ISH BUP image (Intel-signed, IPL meta format) |
| IMR (Main FW) | 1.5MB max | IMR base + 0x10000 | Main FW image (Intel or OEM signed) |

### Firmware Image Formats
- **BUP**: Intel-signed, IPL meta format, loaded at IMR offset 0
- **Main FW**: Intel or OEM signed, loaded by host driver, authenticated by CSE

## 3. FW Loading via CSE

### BUP Loading (Boot-Up Phase)
1. ROM bootloader initiates reset sync handshake with CSE
2. CSE locates ISH BUP in SPI flash NVM
3. CSE authenticates BUP image
4. CSE loads BUP into ISH IMR
5. Control transfers from ROM to BUP

### Main FW Loading (Host Driver Phase)
1. Host OS driver loads ISH main FW into IMR
2. ISH requests CSE to authenticate the main FW
3. CSE authenticates and enables execution via IPC
4. ISH transitions to operational state

### CSE Responsibilities
- Authenticates both BUP and main FW
- Provides debug status
- Maintains IMR location across resets
- BIOS allocates IMR region and communicates location to CSE

## 4. Reset Sequence

### Cold Boot / Global Reset
```
ROM Start → Reset Sync with CSE → CSE loads BUP → BUP runs →
Host driver loads Main FW → CSE authenticates → Operational
```

### Warm Reset / Power Gating Exit
- BUP and main FW preserved in IMR (no reload needed)
- Resume from saved state
- Fast resume path

### Reset Sync Protocol
- CSE and ISH coordinate to detect resets
- Re-initiate loading if needed
- Ensures proper sequencing between CSE and ISH

## 5. S3/S4 Resume Flow

### S3 Resume (Optimized)
1. **S3 Entry**: CSE saves uncompressed ISH main FW in IMR
2. **S3 Exit**: CSE compares hash of saved image
3. **Hash Match**: Direct copy from IMR → fast resume (no NVM reload)
4. **Hash Mismatch**: Full reload from NVM (fallback path)
5. **Max Main FW Size for S3 Optimization**: 1.5MB

### S4 / Global Reset
- Full reload of BUP and main FW from NVM
- Complete re-authentication by CSE
- Full initialization sequence

## 6. Capsule Update Mechanism

1. BIOS provides capsule with new FW image to CSE
2. CSE authenticates the capsule
3. CSE writes authenticated image to NVM (SPI flash)
4. ISH PDT (Platform Data Table) region updated via CSE
5. BIOS-ISH data pass feature supports PDT unlock and update

---

## Key Points for Validation

- **Boot ROM is fixed 8KB** - cannot be updated, only patched via BUP 'doomsday' script
- **SRAM is banked (20 x 32KB)** - per-bank power gating for fine-grained power management
- **AON RF SRAM (8KB)** provides state retention during D0i2/D0i3
- **CSE is the trust anchor** for all ISH firmware authentication
- **S3 optimization** avoids full FW reload if image hash matches
- **IMR region** must be allocated by BIOS and communicated to CSE
- **8MB reserved before CSE UMA** for ISH FW shadowing (from BIOS Requirements doc)
