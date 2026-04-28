"""
Bulk Update NGA Test Lines Script
Updates multiple test lines with new XML configurations
"""

import json
import re
from pysvtools.execution.Lib import NgaAPIUtils

# Test line configurations
TEST_LINES = [
    {
        "testline_id": "ee3b157a-5094-49cd-804d-c1cd8926e3f2",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020584158",
        "xml_file": "CC1_30minutes.xml",
        "pysv_change": None
    },
    {
        "testline_id": "0c1c7987-6737-4504-9c0d-54f52c7abd1f",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020724863",
        "xml_file": "pkgc_tsc_drift.xml",
        "pysv_change": None
    },
    {
        "testline_id": "35a80cb7-7189-4954-ae75-5992798243ba",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023199148",
        "xml_file": "PKGC10p1_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "53f11c23-5409-4348-8a45-ae22e052d68b",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020584103",
        "xml_file": "PKGC10p1_RingC3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "08583195-e9ad-4622-b4b9-02ce49b1143a",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575846",
        "xml_file": "PKGC10p2_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "48d4ad7c-70b2-4a9e-9fed-0f9b30dcfb20",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024103994",
        "xml_file": "PKGC10p3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "a80a1c37-e1b6-4d54-8afa-cfd91da2bf51",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104196",
        "xml_file": "PKGC10p3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "7d00d501-7c13-4734-950c-d6db4a86ce85",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104012",
        "xml_file": "PKGC10p3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "8bb47aff-ed73-453d-91ca-30f91d705c96",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104070",
        "xml_file": "PKGC10p3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "75457e67-83e7-4bcc-bbff-45b0c923a2c0",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575850",
        "xml_file": "PKGC10p3_only.xml",
        "pysv_change": {
            "old": "hub.punit.punit_gpsb.punit_gpsb.pkgc_dfx_pcode_bypasses.pkgc_disable_mask.write(15)",
            "new": "punit.punit_gpsb.punit_gpsb.pkgc_dfx_pcode_bypasses.pkgc_disable_mask.write(0)"
        }
    },
    {
        "testline_id": "0d692206-77fd-43a0-a695-2e2c2e537014",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023199158",
        "xml_file": "PKGC6p1_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "f028107b-1606-4a9e-aee0-120f06168b69",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020583941",
        "xml_file": "PKGC6p1_RingC3_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "7fcc7092-a52f-462b-86ef-4b0b05d27932",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575840",
        "xml_file": "PKGC6p2_only.xml",
        "pysv_change": None
    },
    {
        "testline_id": "cae273aa-3557-4d09-ba83-19d4734a6dfe",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023763284",
        "xml_file": "PKGCX_Display_On.xml",
        "pysv_change": None
    },
    {
        "testline_id": "c49c759e-67a4-4c01-850e-61b28e0a8357",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023763302",
        "xml_file": "PKGCX_RingC3_only.xml",
        "pysv_change": "Cdie.dcode.telemetry.dmu_normal_telemetry.counters.ring_c3_counter != 0x0"
    }
]

PROJECT = "nvl_fv_or"
NGA_ENV = "https://nga-prod.laas.icloud.intel.com"
XML_BASE_PATH = r"C:\validation\windows-test-content\pm\xml\nvl\idle"


def extract_xml_from_command(command):
    """Extract the XML file path from a command string."""
    match = re.search(r'cfg_xml=([^\s]+)', command)
    if match:
        return match.group(1)
    return None


def replace_xml_in_command(command, new_xml_path):
    """Replace the XML file path in a command string."""
    # Escape backslashes for regex replacement
    escaped_path = new_xml_path.replace('\\', '\\\\')
    return re.sub(r'cfg_xml=([^\s]+)', f'cfg_xml={escaped_path}', command)


def get_testline_info(testline_id):
    """Get test line information including test steps."""
    endpoint = f'/Planning/{PROJECT}/api/TestLine/{testline_id}'
    status, data = NgaAPIUtils.NgaGet(endpoint, nga_env=NGA_ENV)
    
    if status != 200:
        raise Exception(f"Failed to get test line {testline_id}: status {status}")
    
    return data


def get_teststep_info(step_id):
    """Get test step information."""
    endpoint = f'/Planning/{PROJECT}/api/TestStep/{step_id}'
    status, data = NgaAPIUtils.NgaGet(endpoint, nga_env=NGA_ENV)
    
    if status != 200:
        raise Exception(f"Failed to get test step {step_id}: status {status}")
    
    return data


def update_teststep(step_id, updated_data):
    """Update a test step."""
    endpoint = f'/Planning/{PROJECT}/api/TestStep/{step_id}'
    response = NgaAPIUtils.NgaPost(endpoint, updated_data, nga_env=NGA_ENV)
    
    if response.status_code != 200:
        raise Exception(f"Failed to update test step {step_id}: status {response.status_code}")
    
    return True


def process_testline(testline_config):
    """Process a single test line - get info, update, and verify."""
    testline_id = testline_config["testline_id"]
    tc_link = testline_config["tc_link"]
    xml_file = testline_config["xml_file"]
    pysv_change = testline_config["pysv_change"]
    
    new_xml_path = f"{XML_BASE_PATH}\\{xml_file}"
    
    result = {
        "testline_id": testline_id,
        "tc_link": tc_link,
        "xml_file": xml_file,
        "status": "pending",
        "steps_updated": []
    }
    
    try:
        # Get test line info
        print(f"\n{'='*80}")
        print(f"Processing: {testline_id}")
        print(f"TC Link: {tc_link}")
        print(f"Target XML: {xml_file}")
        
        testline = get_testline_info(testline_id)
        result["testline_name"] = testline.get("Name", "Unknown")
        
        step_ids = testline.get("TestStepIds", [])
        print(f"Found {len(step_ids)} test step(s)")
        
        for step_id in step_ids:
            step_info = get_teststep_info(step_id)
            step_name = step_info.get("Name", "Unknown")
            command = step_info.get("Command", "")
            
            step_result = {
                "step_id": step_id,
                "step_name": step_name,
                "old_command": command,
                "new_command": command,
                "updated": False
            }
            
            # Check if this is a SOLAR test step (has cfg_xml)
            old_xml = extract_xml_from_command(command)
            
            if old_xml:
                # This is a SOLAR step - update XML
                new_command = replace_xml_in_command(command, new_xml_path)
                step_result["old_xml"] = old_xml
                step_result["new_xml"] = new_xml_path
                step_result["new_command"] = new_command
                
                print(f"\n  Step: {step_name}")
                print(f"    Old XML: {old_xml}")
                print(f"    New XML: {new_xml_path}")
                
                # Update the step
                step_info["Command"] = new_command
                update_teststep(step_id, step_info)
                step_result["updated"] = True
                print(f"    [OK] Updated successfully")
            
            # Check for PYSV changes
            elif pysv_change and "punit" in command.lower():
                # This is a PYSV step
                if isinstance(pysv_change, dict):
                    old_val = pysv_change["old"]
                    new_val = pysv_change["new"]
                    
                    if old_val in command:
                        new_command = command.replace(old_val, new_val)
                        step_result["old_pysv"] = old_val
                        step_result["new_pysv"] = new_val
                        step_result["new_command"] = new_command
                        
                        print(f"\n  Step: {step_name}")
                        print(f"    Old PYSV: {old_val}")
                        print(f"    New PYSV: {new_val}")
                        
                        step_info["Command"] = new_command
                        update_teststep(step_id, step_info)
                        step_result["updated"] = True
                        print(f"    [OK] Updated successfully")
            
            result["steps_updated"].append(step_result)
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"ERROR: {e}")
    
    return result


def main():
    """Main execution function."""
    print("="*80)
    print("NGA Test Line Bulk Update Script")
    print("="*80)
    print(f"Project: {PROJECT}")
    print(f"Total test lines to update: {len(TEST_LINES)}")
    
    results = []
    
    for testline_config in TEST_LINES:
        result = process_testline(testline_config)
        results.append(result)
    
    # Save results to JSON
    with open("update_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("UPDATE SUMMARY")
    print("="*80)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    
    if failed_count > 0:
        print("\nFailed test lines:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {r['testline_id']}: {r.get('error', 'Unknown error')}")
    
    print("\nResults saved to: update_results.json")
    return results


if __name__ == "__main__":
    results = main()
