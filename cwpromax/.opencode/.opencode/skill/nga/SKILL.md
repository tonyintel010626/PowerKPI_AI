---
name: nga
description: use rest API via scripts provided
---
scripts is relative in folder. assume opencode.json is in <cwd>. 

# [NGA-GET] API using http get
script location is at -> <cwd>/.opencode/skills/nga/nga_get.py
use nga_get.py to fetch HTTP GET NGA data.
the command format is: python <cwd>/.opencode/skills/nga/nga_get.py "<endpoint>"

# [NGA-Failure] Failure by test-run-id
script location is at -> <cwd>/.opencode/skills/nga/nga_failure_by_testrun_id.py
use nga_failure_by_testrun_id.py to get failure info using test run id, 
the command format is: python <cwd>/.opencode/skills/nga/nga_failure_by_testrun_id.py "<nga-project>" "<test-run-id>"
