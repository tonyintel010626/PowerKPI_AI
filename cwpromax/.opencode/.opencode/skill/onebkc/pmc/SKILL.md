---
name: pmc
description: PMC skills for onebkc releases.
---
scripts is relative in folder. assume opencode.json is in <cwd>. 
you may need to add "--proxy http://proxy-chain.intel.com:911" to the command

# Projects
adpn -> Alder Point N
adpp -> Alder Point P
adps -> Alder Point S
arlh -> Arrow Lake H
lnlm -> Lunar Lake M
mtlm -> Meteor Lake M
mtlp -> Meteor Lake P
mtls -> Meteor Lake S
mtps -> Meteor Point S
nvlh -> Nova Lake H / Noval Lake Hx
nvls -> Nova Lake S
nvps -> Nova Point S
ptla -> Panther Lake A
ptlp -> Panther Lake P
wcln -> Wildcat Lake N

# Releases
Releases is found PMC releases binary in artifactory is located in https://ubit-artifactory.intel.com/artifactory/owr-repos/Submissions/pmc/<project>

## Release Type
There is Engineering and Production releases.
Engineering releases are for internal testing purpose only, not for production use.

# Release Notes / Change Log
Release notes are available in the released zipped file.
the filename for release notes is CHANGELOG.md.

## Authentication
```python
import keyring
username = keyring.get_password('onebkc', 'username')
password = keyring.get_password('onebkc', username)
```