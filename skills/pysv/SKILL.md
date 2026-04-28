---
name: pysv
description: skill Reference for PythonSV usage
---
# general
pythonsv is structured in namednodes.
Attribute is refering to FieldValue access type. it can be read only, write only, readwrite, read clear, write clear, 
FieldValue is an object of type namednodes.registers.FieldValue that hold the physical value of field in register attribute is readable.
Register is an object with namednodes.registers.RegisterValue 
registerComponent is object with type namednodes.registers.RegisterComponent and consist of multiple RegisterComponent or RegisterValue
registerComponent will be able to be searched using this skill. 

# Register Specification
each namednodes.registers.RegisterValue (Register)  will have the following function 
<Register>.getspec() # returns the specification of the register including fields, access type, reset value, description etc.


# Accesing PythonSV
The following is the metod to initalize pythonSV. example is generic usage. 

## Intiialization
```python
import namednodes # this is the primary interaction with pythonsv / openipc
from svtools.common import baseaccess as _baseaccess
_base = _baseaccess.getglobalbase()
_access = _baseaccess.getaccess()

proj_cltap = itp.devicelist[0].devicetype
namednodes.sv.initialize(refresh=True)
namednodes.settings.PROJECT = namednodes.sv.project        
namednodes.sv.refresh()

if _access == 'ipc':
    itp = _base.getapi()
else:
    itp = _base

proj_cltap = itp.devicelist[0].devicetype
namednodes.sv.initialize(refresh=True)
namednodes.settings.PROJECT = namednodes.sv.project        
itp.unlock() # very important to unlock for access all of SoC IP frmo JTAG Chain
namednodes.sv.refresh() # Refresh to scan all the nodes & update
```

# Sub Skills
All Sub Skill require the above initialization before using them.

##  Register Search
# search function (from python help) 
search(
    regexpression,
    searchType='registers',
    recursive=True,
    getobj=False,
    expand_arrays=True,
    **kwargs
) method of namednodes.registers.RegisterComponent instance
    Look through the register (or field) list for any registers/fields
    that match the given regular expression and return a list of the
    matching registers.

    Args:
        regexpresion (type): Regular expression to use when searching OR
            offset (number) to use when searching by offset.
        searchType (string, optional):  What to search for, options are:

                - registers or **r**: Search register names (default).
                - fields or **f**: Search field names.
                - description or **d**: Search register and field
                    descriptions.
                - path or **p**: Search register names, including
                    subcomponent paths.
                - register_paths or **rp**: Search by path and
                    return only registers
                - field_paths or **fp**: Search by path and
                    return only fields
                - component_paths or **cp**: Search by path and
                    return only components, expression can be
                    regexpression or a list of regexpressions that will be
                    processed at each level
                - comp or **c**: Search subcomponents.
                - **rf**: Search for [register,field], requires
                    regexpression to be a list.
                - offset or **o**: Search all registers for some sort
                    of offset that matches the one specified for more
                    accurate address search use the searchaddress function.

        recursive (bool, optional): Set to False to disable the recursive
            search. This is supported to provide some functionality used by
            coders. Defaults to True.
        getobj (bool, optional): Set to True to return path to objects and
            actual register/field objects. This one is supported to provide
            some functionality used by coders. Defaults to False.
        expand_arrays (bool): (default: True) whether to expand arrays when searching for fields


example of product is novalake
folder of project is available as default to location c:\pythonsv\<project>
---


# PythonSV Search skills examples
```python
# After initialization
namednodes.sv.socket0.pcd.search(regexpression="\sblock\s",searchType="description") #searching using regular expression in description field is best practice since reigster/field names is less descriptive.
```
