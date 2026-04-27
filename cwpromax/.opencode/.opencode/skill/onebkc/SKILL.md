---
name: onebkc
description: OneBKC steps of using it.
---
scripts is relative in folder. assume opencode.json is in <cwd>. 
source code for pip: https://github.com/intel-innersource/frameworks.devops.intel-devops-framework.applications.py-onebkc
you may need to add "--proxy http://proxy-chain.intel.com:911" to the command

# Python Script
Use `onebkc_get_kits.py` in the onebkc skill folder for fetching kits with filters.
This script handles authentication from keyring and API calls without requiring manual code.

Example usage:
```bash
# Get kits promoted to BKC from PTL CONSUMER for December 2025
python .opencode/skills/onebkc/onebkc_get_kits.py --platformconfigs "PTL-UPH-25H2-CONS" --colors "BKC" --promotiondate "12/2025"

# Get all kits
python .opencode/skills/onebkc/onebkc_get_kits.py

# Filter with multiple criteria
python .opencode/skills/onebkc/onebkc_get_kits.py --platformconfigs "PTL-UPH-25H2-CONS" --colors "BKC" --buildstatuses "passed"
```

# subskills
subskills realted to ifwicomponent PMC can be refered as skills_onebkc_pmc

# Environment URL
OneKit Prod	"https://onekitapi.intel.com/api/v1/"

# General Usage
Software Devops Center (SDC) hold informations of software releases. this skill help you to interact with SDC OneBKC API to fetch.
Definition: 
kits - a combination of several ingridients under it attributes.
ingridients - software components such as firmwares(fw), drivers, os, applications (app).
ifwi - intel Firmware Interface/Image. consists of several ifwi components (ifwicomponent). such as ACE,CNVi, CSME, ESE, GBE, IOM, ISH, IUnit, NPHY, PMC, Punit, SOCC, SPHY, TBT)
versions - version of ingridients.

## Kits Filtering
each Kit have few attiributes, such as platformconfigs, quality(colors), buildstatuses.
You can filter kits by those attributes.
platformconfigs options: 
Novalake HX Consumer: "NVL-Hx-Cons"
Novalake HX Corporate: "NVL-Hx-Corp"
Panther Lake Consumer: "PTL-UPH-25H2-CONS"
Panther Lake Corporate: "PTL-UPH-25H2-CORP"

## quality (colors) options:
All Kit will go with the flow of 
Created, Promoted to Bronze, Promoted to Silver, Promoted to Gold, promoted to BKC

# API Example

## Authentication
```python
import keyring
from onebkc.client import OneBkcClient
username = keyring.get_password('onebkc', 'username')
password = keyring.get_password('onebkc', username)
client = OneBkcClient('https://onebkc.intel.com', username=username, password=password)
```

## fetching & filtering kits
```python
result = client.get_kits() # Query all kits without filter. 
result["kits"] is not None # True

#Example filtering kits by platformconfigs
result = client.get_kits(platformconfigs="NVL-Hx-Cons") # Filter only NVL-HX Consumer ALL kits

#Example filtering kits by promoted date, colors and buildstatuses is 'passed'
result = client.get_kits(promotiondate='12/24/2025', colors='BKC',buildstatuses='passed', platformconfigs='PTL-UPH-25H2-CONS')
```

