# NVL ISH 5.8 Power Management Reference
## Source: Co-De Sign (SIP_ISH5p8_HAS + SIP_ISH_Integration_HAS)

### D-State Hierarchy

| State | VNN | SRAM | Clock | Wake | Exit Latency | Description |
|-------|-----|------|-------|------|-------------|-------------|
| D0 | ON | ON | ON | All | N/A | Fully powered, all SRAM active |
| D0i1 | ON | ON | Gated | All | ~0 | Low-power idle, quick return, sensor paused/reduced |
| D0i2 | ON | PG | Gated | All | ~1.5 ms | Deeper idle, state retention, SRAM per-bank PG, PCE.HAE enables, HW-controlled exit |
| D0i3 | OFF | PG | Gated | All | ~5 ms | Deeper retention, most logic PG, SRAM saved to DRAM, VNN may be removed |
| D3 | OFF | PG | OFF | All | Full restore | Fully power gated, no state retention, all SRAM PG, VNN removed |

### SRAM Power Gating
- **Total**: 640 KB = 20 banks × 32 KB
- **Granularity**: Per-bank independent gating by ISH firmware
- **Reporting**: FW reports active bank count to PMC via IOSF sideband

### PMC Sideband Communication (Energy Reporting)
| Parameter | Value |
|-----------|-------|
| Opcode | 0x6F |
| Tag | 0x06 |
| SAI | 0x34 |
| Destination Port ID | 0xC8 |
| Source Port ID | 0xD0 |
| ER_DATA[7:0] | Number of active SRAM banks (0x00=all gated, 0x14=all 20 active) |

### VNN Power Rail Management
- **D0/D0i1/D0i2**: VNN ON
- **D0i3/D3**: VNN OFF (can be removed)
- VNN request/acknowledge handshake with PMC before fabric/bus transactions
- VNN deasserted only when all internal clock gating enabled and ISH idle

### Wake Event Sources
- Interrupts (ITSS)
- NMI/INIT/AER events
- GPIO events
- Sensor events
- Wake routed to PMC and CCK, PMC restores VNN and clocks

### Clock Gating
- All ISH blocks including SRAMs support clock gating
- HW+SW controlled entry, HW-controlled exit on wake

### S0ix Entry/Exit Flow

**Entry:**
1. PMC checks no active wake events
2. CCK deasserts XTAL CLKACK
3. PMC issues SBMSTRDIS to ITSS (blocks sideband mastering)
4. PMC removes VNN rail
5. ISH enters D0i3/D3, SRAMs PG, state saved if needed

**Exit:**
1. ITSS detects wake event (interrupt)
2. Wake routed to PMC and CCK
3. PMC restores VNN rail and clocks
4. PMC issues SBMSTREN to ITSS (allows sideband mastering)
5. ISH resumes, restores SRAM state from DRAM if needed

### Key Registers
- **PCE.HAE**: D0i2 Feature Enable
- **PCE.D3HE**: D3 High-Level Entry
- **ER_DATA[7:0]**: Active SRAM bank count in PMC sideband message

### NVL vs TTL Power Management Differences
| Feature | NVL (ISH 5.8) | TTL (ISH 5.9) |
|---------|---------------|---------------|
| PMC Sideband Opcode | 0x6F | 0x6F (same) |
| PMC Sideband Tag | 0x06 | 0x06 (same) |
| SAI | 0x34 | Not specified |
| Dest Port ID | 0xC8 | Not specified |
| Source Port ID | 0xD0 | Not specified |
| SRAM Banks | 20 × 32 KB | 20 × 32 KB (same) |
| D0i2 Exit Latency | ~1.5 ms | Not specified |
| D0i3 Exit Latency | ~5 ms | Not specified |
| D-State Hierarchy | Same | Same |
