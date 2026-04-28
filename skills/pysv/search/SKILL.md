---
name: pysv
description: PythonSV usage skill
---

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
namednodes.sv.socket0.pcd.search(regexpression="\sblock\s",searchType="description") #searching using regular expression in description field
```
