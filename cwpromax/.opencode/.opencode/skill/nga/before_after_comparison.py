"""
Create a Before/After comparison report based on the actual data from NGA
"""

import json
from pysvtools.execution.Lib import NgaAPIUtils

PROJECT = "nvl_fv_or"
NGA_ENV = "https://nga-prod.laas.icloud.intel.com"

# Test lines from the provided list
TEST_LINES = [
    {
        "testline_id": "ee3b157a-5094-49cd-804d-c1cd8926e3f2",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020584158",
        "target_xml": "CC1_30minutes.xml"
    },
    {
        "testline_id": "0c1c7987-6737-4504-9c0d-54f52c7abd1f",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020724863",
        "target_xml": "pkgc_tsc_drift.xml"
    },
    {
        "testline_id": "35a80cb7-7189-4954-ae75-5992798243ba",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023199148",
        "target_xml": "PKGC10p1_only.xml"
    },
    {
        "testline_id": "53f11c23-5409-4348-8a45-ae22e052d68b",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020584103",
        "target_xml": "PKGC10p1_RingC3_only.xml"
    },
    {
        "testline_id": "08583195-e9ad-4622-b4b9-02ce49b1143a",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575846",
        "target_xml": "PKGC10p2_only.xml"
    },
    {
        "testline_id": "75457e67-83e7-4bcc-bbff-45b0c923a2c0",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575850",
        "target_xml": "PKGC10p3_only.xml",
        "pysv_note": "write(15) -> write(0)"
    },
    {
        "testline_id": "48d4ad7c-70b2-4a9e-9fed-0f9b30dcfb20",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024103994",
        "target_xml": "PKGC10p3_only.xml"
    },
    {
        "testline_id": "a80a1c37-e1b6-4d54-8afa-cfd91da2bf51",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104196",
        "target_xml": "PKGC10p3_only.xml"
    },
    {
        "testline_id": "8bb47aff-ed73-453d-91ca-30f91d705c96",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104070",
        "target_xml": "PKGC10p3_only.xml"
    },
    {
        "testline_id": "7d00d501-7c13-4734-950c-d6db4a86ce85",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14024104012",
        "target_xml": "PKGC10p3_only.xml"
    },
    {
        "testline_id": "0d692206-77fd-43a0-a695-2e2c2e537014",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023199158",
        "target_xml": "PKGC6p1_only.xml"
    },
    {
        "testline_id": "f028107b-1606-4a9e-aee0-120f06168b69",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020583941",
        "target_xml": "PKGC6p1_RingC3_only.xml"
    },
    {
        "testline_id": "7fcc7092-a52f-462b-86ef-4b0b05d27932",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/22020575840",
        "target_xml": "PKGC6p2_only.xml"
    },
    {
        "testline_id": "cae273aa-3557-4d09-ba83-19d4734a6dfe",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023763284",
        "target_xml": "PKGCX_Display_On.xml"
    },
    {
        "testline_id": "c49c759e-67a4-4c01-850e-61b28e0a8357",
        "tc_link": "https://hsdes.intel.com/appstore/article/#/14023763302",
        "target_xml": "PKGCX_RingC3_only.xml"
    }
]

# Load previous results to get "before" data
try:
    with open("update_results.json", "r") as f:
        previous_results = json.load(f)
except:
    previous_results = []

# Create a mapping of testline_id to previous data
previous_data = {result["testline_id"]: result for result in previous_results}

print("=" * 140)
print("BEFORE vs AFTER COMPARISON REPORT")
print("=" * 140)
print(f"\nProject: nvl_fv_or")
print(f"Total Test Lines: {len(TEST_LINES)}")
print("\n" + "=" * 140)

for idx, testline in enumerate(TEST_LINES, 1):
    testline_id = testline["testline_id"]
    tc_link = testline["tc_link"]
    tc_num = tc_link.split("/")[-1]
    target_xml = testline["target_xml"]
    
    print(f"\n{idx}. TC {tc_num}")
    print(f"   Test Line ID: {testline_id}")
    print(f"   TC Link: {tc_link}")
    print(f"   NGA Link: https://nga.laas.intel.com/#/nvl_fv_or/planning/testlines/{testline_id}")
    
    # Get previous data if available
    if testline_id in previous_data:
        prev = previous_data[testline_id]
        print(f"\n   BEFORE UPDATE:")
        
        for step in prev.get("steps_updated", []):
            if "old_xml" in step:
                old_xml = step["old_xml"]
                print(f"     XML Path: {old_xml}")
                print(f"     XML File: {old_xml.split(chr(92))[-1]}")  # Get filename
            
            if "old_pysv" in step:
                print(f"     PYSV: {step['old_pysv']}")
        
        print(f"\n   AFTER UPDATE:")
        print(f"     XML Path: C:\\validation\\windows-test-content\\pm\\xml\\nvl\\idle\\{target_xml}")
        print(f"     XML File: {target_xml}")
        
        if testline.get("pysv_note"):
            print(f"     PYSV: {testline['pysv_note']}")
        
        # Check if XML actually changed
        xml_changed = False
        for step in prev.get("steps_updated", []):
            if "old_xml" in step and "new_xml" in step:
                old_file = step["old_xml"].split(chr(92))[-1]
                new_file = step["new_xml"].split(chr(92))[-1]
                if old_file != new_file:
                    xml_changed = True
                    print(f"\n   STATUS: XML CHANGED from {old_file} to {new_file}")
                else:
                    print(f"\n   STATUS: No change needed (already using correct XML)")
    else:
        print(f"\n   STATUS: Not found in previous update results")
    
    print(f"   " + "-" * 136)

print("\n" + "=" * 140)
print("END OF REPORT")
print("=" * 140)
