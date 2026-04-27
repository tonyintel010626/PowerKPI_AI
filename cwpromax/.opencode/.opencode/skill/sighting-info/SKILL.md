---
name: sighting-info
description: A skill to find out the test execution status based using python
license: MIT
---

# PTL Test Results Skill

This skill will provide the list of the test results for your analysis.

## Instructions

you will use the step to reply the test results for products.
1. use the right query based on the product needed. 12xe is 15018623948. 4Xe is 15018623981, U is 15018623982. the product name is usually PTL 12Xe, PTL 4Xe or PTL U. PTL is similar to PTL-PCD for this skills.
2. use this as baseline for your script, execute & use the response as output of this skills `YOUR_HSD_ID='15018601544'; from pysvtools import hsdes; import json; ts = hsdes.config_by_id(YOUR_HSD_ID); hsdes.config(ts); data = hsdes.search_id(YOUR_HSD_ID, showFields='subject,forum,id,title,owner,priority,days_open,comments,description,submitted_by,updated_date,updated_by,updated_reason,status,reason,status_reason,test_case.val_teams,test_result.val_teams,family,release_affected,family_affected,submitted_date,closed_date'); print(json.dumps(data[0] if data else {}, indent=2))`

