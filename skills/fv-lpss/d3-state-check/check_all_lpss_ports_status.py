#!/usr/bin/env python
"""
LPSS Port Status Checker - OPTIMIZED VERSION
Mimics lpss_main.lhc.check_d3() functionality
Shows all LPSS ports with their D-state or function disable status

CRITICAL: Validates 3 criteria before declaring D3/D0:
1. pmc.pmu.pg_ip_d3_sts_0.lpss_d3_sts - LPSS D3 status (PMU)
2. pmc.mmr.lpm_live_ipd3_sts_0.lpss_d3_sts - D3 condition met (MMR)
3. slice_fabric.pmectrlstatus.powerstate - Per-port D-state (0=D0, 3=D3)

OPTIMIZATION: Uses existing sv connection if available, minimal refresh
Based on: C:\\pythonsv\\novalake\\vjt\\lpss\\lpss_main.py and lpss_class.py
Reference: C:\\pythonsv\\novalake\\vjt\\lpss\\nvlh_cltap.py for port configuration
"""

import namednodes
import sys

def check_lpss_all_ports_status(force_refresh=False):
    """
    Check and display status of all LPSS ports (I2C, I3C, SPI, UART)
    Shows: D0, D1, D2, D3, or "function disabled" for each port
    
    VALIDATES 3 CRITERIA:
    1. PSF fundis register - function disable status
    2. PMC PMU/MMR registers - LPSS-level D3 status
    3. Per-port pmectrlstatus.powerstate - individual port D-state
    
    This mimics the lpss_main.lhc.check_d3() functionality from user's working scripts
    """
    
    print("="*80)
    print("LPSS Port Status Check - Validating All 3 Criteria")
    print("="*80)
    
    # OPTIMIZATION: Only refresh if forced or if sv not initialized
    try:
        # Check if sv is already initialized and PCD is accessible
        pcd = namednodes.sv.socket0.pcd
        if force_refresh:
            print("🔄 Force refresh requested, reinitializing...")
            namednodes.sv.refresh()
        else:
            # Quick test to see if PCD is responsive
            try:
                _ = pcd.pmc.pmu.st_dis_mask_0.lpss_st_dis_ind
                print("⚡ Using existing PythonSV session (fast path)")
            except:
                print("🔄 Refreshing PythonSV connection...")
                namednodes.sv.refresh()
    except:
        print("🔄 Initializing PythonSV connection...")
        namednodes.sv.refresh()
        pcd = namednodes.sv.socket0.pcd
    
    # ========================================================================
    # CRITERIA 1: Check if entire LPSS is fuse disabled
    # ========================================================================
    fuse_disabled = False
    try:
        lpss_st_dis_ind = pcd.pmc.pmu.st_dis_mask_0.lpss_st_dis_ind.read()
        if lpss_st_dis_ind == 1:
            print("❌ CRITERIA 1: LPSS is statically disabled by fuse")
            print("   pmc.pmu.st_dis_mask_0.lpss_st_dis_ind = 1")
            fuse_disabled = True
            return
        else:
            print("✅ CRITERIA 1: LPSS fuse status OK")
            print(f"   pmc.pmu.st_dis_mask_0.lpss_st_dis_ind = {lpss_st_dis_ind}")
    except Exception as e:
        print(f"⚠ Warning: Cannot check fuse status: {e}")
    
    # ========================================================================
    # CRITERIA 2: Check LPSS subsystem D3 status (PMU)
    # ========================================================================
    lpss_d3_pmu = None
    try:
        lpss_d3_pmu = pcd.pmc.pmu.pg_ip_d3_sts_0.lpss_d3_sts.read()
        if lpss_d3_pmu == 1:
            print("💤 CRITERIA 2: LPSS subsystem is in D3 (PMU)")
            print(f"   pmc.pmu.pg_ip_d3_sts_0.lpss_d3_sts = {lpss_d3_pmu}")
        else:
            print("✅ CRITERIA 2: LPSS subsystem is in D0 (PMU)")
            print(f"   pmc.pmu.pg_ip_d3_sts_0.lpss_d3_sts = {lpss_d3_pmu}")
    except Exception as e:
        print(f"⚠ Warning: Cannot check LPSS D3 status (PMU): {e}")
    
    # ========================================================================
    # CRITERIA 3: Check LPSS D3 condition (MMR)
    # ========================================================================
    lpss_d3_mmr = None
    try:
        lpss_d3_mmr = pcd.pmc.mmr.lpm_live_ipd3_sts_0.lpss_d3_sts.read()
        if lpss_d3_mmr == 1:
            print("💤 CRITERIA 3: LPSS D3 condition is met (MMR)")
            print(f"   pmc.mmr.lpm_live_ipd3_sts_0.lpss_d3_sts = {lpss_d3_mmr}")
        else:
            print("✅ CRITERIA 3: LPSS D3 condition not met (MMR)")
            print(f"   pmc.mmr.lpm_live_ipd3_sts_0.lpss_d3_sts = {lpss_d3_mmr}")
    except Exception as e:
        print(f"⚠ Warning: Cannot check D3 condition (MMR): {e}")
    
    print()
    print("="*80)
    print("Individual Port Status - Validating Per-Port + Subsystem Criteria")
    print("="*80)
    print(f"{'Controller':<15} {'Port':<12} {'Status':<20} {'Validation Details'}")
    print("-" * 80)
    
    # Port configurations from nvlh_cltap.py
    # Format: (protocol, port_num, controller_name, fabric_idx, fundis_path)
    ports_config = [
        # I2C ports (6 total) - Device 21 (I2C0-3), Device 25 (I2C4-5)
        ("I2C", 0, "i2c0", 0, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d21_f0_offset3.fundis"),
        ("I2C", 1, "i2c1", 1, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d21_f1_offset4.fundis"),
        ("I2C", 2, "i2c2", 2, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d21_f2_offset5.fundis"),
        ("I2C", 3, "i2c3", 3, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d21_f3_offset6.fundis"),
        ("I2C", 4, "i2c4", 4, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d25_f0_offset7.fundis"),
        ("I2C", 5, "i2c5", 5, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d25_f1_offset8.fundis"),
        
        # I3C ports (4 total - 2 dual-port controllers) - Device 17
        ("I3C", 0, "i3c0_0", 12, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d17_f0_offset9.fundis"),
        ("I3C", 1, "i3c0_1", 12, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d17_f0_offset9.fundis"),  # Same function
        ("I3C", 2, "i3c1_0", 13, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d17_f2_offset10.fundis"),
        ("I3C", 3, "i3c1_1", 13, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d17_f2_offset10.fundis"),  # Same function
        
        # SPI ports (3 total) - Device 30 (SPI0-1), Device 18 (SPI2)
        ("SPI", 0, "spi0", 9, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d30_f2_offset11.fundis"),
        ("SPI", 1, "spi1", 10, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d30_f3_offset12.fundis"),
        ("SPI", 2, "spi2", 11, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d18_f6_offset13.fundis"),
        
        # UART ports (3 total) - Device 30 (UART0-1), Device 25 (UART2)
        ("UART", 0, "hsuart0", 6, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d30_f0_offset14.fundis"),
        ("UART", 1, "hsuart1", 7, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d30_f1_offset15.fundis"),
        ("UART", 2, "hsuart2", 8, "pcd.psf.psf8.psf_8_agnt_t0_shdw_pcien_lpss_rs0_d25_f2_offset16.fundis"),
    ]
    
    results = {
        "D0": [],
        "D1": [],
        "D2": [],
        "D3": [],
        "DISABLED": [],
        "ERROR": [],
        "MISMATCH": []
    }
    
    for protocol, port_num, controller_name, fabric_idx, fundis_path in ports_config:
        port_name = f"{protocol}{port_num}"
        
        try:
            # ========================================================================
            # Check 1: PSF Function Disable
            # ========================================================================
            fundis_reg = eval(fundis_path, {"pcd": pcd})
            fundis = fundis_reg.read()
            if fundis == 1:
                results["DISABLED"].append(port_name)
                print(f"{port_name:<15} {controller_name:<12} {'FUNCTION DISABLED':<20} PSF fundis=1")
                continue
            
            # ========================================================================
            # Check 2: Per-Port Power State
            # ========================================================================
            fabric = pcd.lpss.lpss_regs.iosf2axi_env_i
            fabric_top = getattr(fabric, f"file_iosf2axi_pci_pf_top_{fabric_idx}")
            powerstate = fabric_top.pmectrlstatus.powerstate.read()
            
            # ========================================================================
            # VALIDATE ALL 3 CRITERIA TOGETHER
            # ========================================================================
            # Criteria:
            # 1. PSF fundis = 0 (already checked, passed)
            # 2. LPSS subsystem D3 status (PMU + MMR) - optional, informational
            # 3. Per-port powerstate (DEFINITIVE)
            
            validation_details = []
            status_consistent = True
            
            # Primary determination: per-port powerstate
            if powerstate == 0:
                state_str = "D0"
                indicator = "✅"
                status_text = "D0 (Active)"
                validation_details.append(f"powerstate=0")
                
                # Cross-check with subsystem status
                if lpss_d3_pmu == 1:
                    validation_details.append("⚠PMU=D3")
                    status_consistent = False
                if lpss_d3_mmr == 1:
                    validation_details.append("⚠MMR=D3")
                    status_consistent = False
                    
            elif powerstate == 3:
                state_str = "D3"
                indicator = "💤"
                status_text = "D3 (Low Power)"
                validation_details.append(f"powerstate=3")
                
                # Cross-check with subsystem status
                if lpss_d3_pmu == 0:
                    validation_details.append("⚠PMU=D0")
                    status_consistent = False
                if lpss_d3_mmr == 0:
                    validation_details.append("⚠MMR=D0")
                    status_consistent = False
                    
            else:
                state_str = f"D{powerstate}"
                indicator = "⚠"
                status_text = f"D{powerstate}"
                validation_details.append(f"powerstate={powerstate}")
            
            # Track results
            if state_str in results:
                results[state_str].append(port_name)
            else:
                results[state_str] = [port_name]
            
            if not status_consistent:
                results["MISMATCH"].append(port_name)
            
            # Display with validation details
            details_str = ", ".join(validation_details)
            consistency_marker = "" if status_consistent else " ⚠MISMATCH"
            print(f"{port_name:<15} {controller_name:<12} {status_text:<20} {details_str}{consistency_marker}")
            
        except Exception as e:
            results["ERROR"].append(port_name)
            print(f"{port_name:<15} {controller_name:<12} {'ERROR':<20} {str(e)[:40]}")
    
    # Summary
    print("="*80)
    print("Summary:")
    print("-" * 80)
    print(f"✅ D0 (Active):        {len(results.get('D0', []))} ports - {', '.join(results.get('D0', [])) if results.get('D0') else 'None'}")
    print(f"⚠  D1 (Light Sleep):   {len(results.get('D1', []))} ports - {', '.join(results.get('D1', [])) if results.get('D1') else 'None'}")
    print(f"⚠  D2 (Deep Sleep):    {len(results.get('D2', []))} ports - {', '.join(results.get('D2', [])) if results.get('D2') else 'None'}")
    print(f"💤 D3 (Low Power):     {len(results.get('D3', []))} ports - {', '.join(results.get('D3', [])) if results.get('D3') else 'None'}")
    print(f"❌ Function Disabled:  {len(results.get('DISABLED', []))} ports - {', '.join(results.get('DISABLED', [])) if results.get('DISABLED') else 'None'}")
    if results.get('MISMATCH'):
        print(f"⚠️  Criteria Mismatch:  {len(results['MISMATCH'])} ports - {', '.join(results['MISMATCH'])}")
        print("    (Port state inconsistent with subsystem PMU/MMR status)")
    if results.get('ERROR'):
        print(f"⚠️  Errors:             {len(results['ERROR'])} ports - {', '.join(results['ERROR'])}")
    print("="*80)
    
    print("\n📋 Validation Notes:")
    print("  - Primary determination: pmectrlstatus.powerstate (per-port)")
    print("  - Cross-validation: PMU pg_ip_d3_sts_0 + MMR lpm_live_ipd3_sts_0 (subsystem)")
    print("  - Mismatches indicate port state inconsistent with subsystem status")
    
    return results

if __name__ == "__main__":
    # Check for command line arguments
    force_refresh = "--refresh" in sys.argv or "-r" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python check_all_lpss_ports_status.py [OPTIONS]")
        print()
        print("Options:")
        print("  --refresh, -r    Force PythonSV refresh (slower but ensures fresh state)")
        print("  --help, -h       Show this help message")
        print()
        print("Default: Uses existing PythonSV session if available (fast)")
        sys.exit(0)
    
    check_lpss_all_ports_status(force_refresh=force_refresh)
