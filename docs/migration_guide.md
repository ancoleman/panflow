# Migration Guide: PANFlow

This guide will help you transition from the old monolithic `PanOsXmlUtils` class to the new modular, functional design of the PANFlow tool.

## Key Changes

1. **Modular Organization**: Code has been split into focused modules
2. **Functional Design**: Adopting a more functional approach over a class-based design
3. **Version-Aware XPaths**: XPath expressions externalized in version-specific YAML files
4. **Cleaner Interface**: More consistent function signatures and parameter names
5. **Improved Error Handling**: Better logging and error reporting

## Quick Reference

Here's a quick reference for migrating common patterns:

| Old (Monolithic) | New (Modular) |
|------------------|---------------|
| `utils = PanOsXmlUtils("config.xml", "firewall")` | `config = PANFlowConfig("config.xml", device_type="firewall")` |
| `objects = utils.get_objects("address", "vsys", vsys="vsys1")` | `objects = config.get_objects("address", "vsys", vsys="vsys1")` |
| `utils.add_object("address", "vsys", "web-server", {...})` | `config.add_object("address", "web-server", {...}, "vsys")` |
| `utils.save_config("output.xml")` | `config.save("output.xml")` |

## Detailed Migration Steps

### 1. Initialization

**Old:**
```python
from panos_xml_utils import PanOsXmlUtils

# Initialize the utility
utils = PanOsXmlUtils("config.xml", "firewall")
```

**New:**
```python
from panflow import PANFlowConfig

# Initialize the configuration
config = PANFlowConfig(config_file="config.xml", device_type="firewall")

# With version specification (optional)
config = PANFlowConfig(config_file="config.xml", device_type="firewall", version="11.0")
```

### 2. Getting Objects

**Old:**
```python
# Get address objects in a device group
addresses = utils.get_objects("address", "device_group", device_group="DG1")
```

**New:**
```python
# Note the consistent parameter order
addresses = config.get_objects("address", "device_group", device_group="DG1")
```

### 3. Adding Objects

**Old:**
```python
utils.add_object("address", "vsys", "web-server", {
    "ip-netmask": "10.0.0.5"
}, vsys="vsys1")
```

**New:**
```python
# Note that name comes before properties, and context comes after
config.add_object(
    "address", 
    "web-server", 
    {"ip-netmask": "10.0.0.5"}, 
    "vsys", 
    vsys="vsys1"
)
```

### 4. Working with Policies

**Old:**
```python
policies = utils.get_policies("security_pre_rules", "device_group", device_group="DG1")
```

**New:**
```python
policies = config.get_policies("security_pre_rules", "device_group", device_group="DG1")
```

### 5. Group Operations

**Old:**
```python
utils.add_member_to_group("address_group", "web-servers", "new-server", "vsys", vsys="vsys1")
```

**New:**
```python
config.add_member_to_group("address_group", "web-servers", "new-server", "vsys", vsys="vsys1")
```

### 6. Report Generation

**Old:**
```python
report = utils.generate_report("unused-objects", "vsys", "report.json", vsys="vsys1")
```

**New:**
```python
# More specific function for report types
report = config.generate_unused_objects_report("vsys", "report.json", vsys="vsys1")
```

### 7. Direct XPath Search

**Old:**
```python
elements = utils.xpath_search("//address/entry")
```

**New:**
```python
elements = config.xpath_search("//address/entry")
```

### 8. Configuration Saving

**Old:**
```python
utils.save_config("output.xml")
```

**New:**
```python
config.save("output.xml")
```

## CLI Migration Guide

If you're using the command-line interface, the changes are minimal:

**Old:**
```bash
python cli.py object list --config firewall.xml --type address
```

**New:**
```bash
panflow object list --config firewall.xml --type address
```

The parameter structure remains mostly the same, with the addition of a new `--version` parameter to explicitly specify a PAN-OS version.

## Using Low-Level Functions

If you need more control, you can use the low-level functions directly:

```python
from lxml import etree
from panflow.core.config_loader import load_config_from_file
from panflow.core.xpath_resolver import get_object_xpath
from panflow.modules.objects import get_objects

# Load a configuration
tree, version = load_config_from_file("config.xml")

# Get the XPath for an object type
xpath = get_object_xpath("address", "firewall", "vsys", version, vsys="vsys1")

# Get objects using the tree directly
objects = get_objects(tree, "address", "firewall", "vsys", version, vsys="vsys1")
```

## Handling Multiple PAN-OS Versions

The new library makes it easy to work with different PAN-OS versions:

```python
from panflow import PANFlowConfig
from panflow.core.xpath_resolver import get_all_versions

# Get all supported versions
versions = get_all_versions()
print(f"Supported versions: {versions}")

# Explicitly specify version
config_101 = PANFlowConfig("firewall_10.1.xml", version="10.1")
config_112 = PANFlowConfig("firewall_11.2.xml", version="11.2")

# Let the library auto-detect version
config_auto = PANFlowConfig("firewall.xml")
print(f"Detected version: {config_auto.version}")
```

## Common Issues and Solutions

1. **Parameter Order Changed**: The most common migration issue is parameter order in function calls. Double-check argument order, particularly for `add_object` and similar functions.

2. **Report Functions**: Report generation has been split into separate functions for each report type.

3. **Error Handling**: The new library provides more detailed error messages. Check logs for helpful information.

4. **Configuration Context**: Be explicit about context to avoid confusion (shared vs. device_group vs. vsys).

## When to Use PANFlowConfig vs. Direct Functions

- **Use PANFlowConfig**: For most cases, especially when working with a single configuration file and performing multiple operations.

- **Use Direct Functions**: When you need more control, are processing multiple files, or want to minimize dependencies.

## Need Help?

If you encounter issues during migration, consult the full documentation or submit an issue on the project's repository.
