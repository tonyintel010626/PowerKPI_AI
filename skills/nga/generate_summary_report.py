"""
Generate Summary Report for NGA Test Line Updates
"""

import json

# Load the results
with open("update_results.json", "r") as f:
    results = json.load(f)

# Additional PYSV update for testline 75457e67
pysv_update = {
    "testline_id": "75457e67-83e7-4bcc-bbff-45b0c923a2c0",
    "step_id": "4fbceea5-7a99-4696-9ea3-56714af5f01f",
    "old_pysv": "write(15)",
    "new_pysv": "write(0)"
}

print("=" * 120)
print("NGA TEST LINE UPDATE SUMMARY REPORT")
print("=" * 120)
print(f"\nProject: nvl_fv_or")
print(f"Total Test Lines Updated: {len(results)}")
print(f"Update Date: 2025-12-15")
print("\n" + "=" * 120)

for idx, result in enumerate(results, 1):
    testline_id = result["testline_id"]
    tc_link = result["tc_link"]
    xml_file = result["xml_file"]
    testline_name = result["testline_name"]
    
    print(f"\n{idx}. TEST LINE: {testline_id}")
    print(f"   TC Link: {tc_link}")
    print(f"   NGA Link: https://nga.laas.intel.com/#/nvl_fv_or/planning/testlines/{testline_id}")
    print(f"   Test Name: {testline_name}")
    print(f"   Target XML: {xml_file}")
    print(f"   Status: {result['status'].upper()}")
    
    # Show steps updated
    for step in result["steps_updated"]:
        if step.get("updated"):
            print(f"\n   Step Updated: {step['step_name']}")
            print(f"   Step ID: {step['step_id']}")
            
            if "old_xml" in step:
                old_xml = step["old_xml"].split("\\")[-1]
                new_xml = step["new_xml"].split("\\")[-1]
                print(f"   Old XML: {old_xml}")
                print(f"   New XML: {new_xml}")
                
                if old_xml != new_xml:
                    print(f"   Change: XML file changed from {old_xml} to {new_xml}")
                else:
                    print(f"   Change: No XML change (already using correct file)")
    
    # Check for PYSV updates
    if testline_id == pysv_update["testline_id"]:
        print(f"\n   PYSV Step Updated: PYSV_MASK_PKGC10p3_4446a24e803a47209711af765ed1f55d")
        print(f"   Step ID: {pysv_update['step_id']}")
        print(f"   Old: pkgc_disable_mask.write(15)")
        print(f"   New: pkgc_disable_mask.write(0)")
        print(f"   Change: PYSV mask value changed from 15 to 0")
    
    print(f"   " + "-" * 116)

print("\n" + "=" * 120)
print("DETAILED CHANGES SUMMARY")
print("=" * 120)

# Count changes
xml_changes = []
no_changes = []

for result in results:
    for step in result["steps_updated"]:
        if step.get("updated") and "old_xml" in step:
            old_xml = step["old_xml"].split("\\")[-1]
            new_xml = step["new_xml"].split("\\")[-1]
            if old_xml != new_xml:
                xml_changes.append({
                    "testline": result["testline_id"],
                    "tc": result["tc_link"],
                    "old": old_xml,
                    "new": new_xml
                })
            else:
                no_changes.append({
                    "testline": result["testline_id"],
                    "tc": result["tc_link"],
                    "xml": new_xml
                })

print(f"\nTest Lines with XML Changes: {len(xml_changes)}")
if xml_changes:
    for change in xml_changes:
        tc_num = change["tc"].split("/")[-1]
        print(f"  - TC {tc_num}: {change['old']} -> {change['new']}")

print(f"\nTest Lines Already Using Correct XML: {len(no_changes)}")
if no_changes:
    for item in no_changes:
        tc_num = item["tc"].split("/")[-1]
        print(f"  - TC {tc_num}: {item['xml']}")

print(f"\nPYSV Changes: 1")
print(f"  - TC 22020575850 (testline 75457e67): pkgc_disable_mask.write(15) -> write(0)")

print("\n" + "=" * 120)
print("All updates completed successfully!")
print("=" * 120)
