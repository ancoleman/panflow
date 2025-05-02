# Object Merge Documentation

This documentation covers the object merge functionality added to the PAN-OS XML Utilities package, allowing you to copy and merge objects between different configurations, device groups, or virtual systems.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Using Object Merger](#using-object-merger)
  - [ObjectMerger Class](#objectmerger-class)
  - [PanOsXmlConfig Helper Methods](#panosxmlconfig-helper-methods)
  - [Command-Line Interface](#command-line-interface)
- [Use Cases](#use-cases)
- [Code Examples](#code-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The object merge functionality allows you to:

- Copy objects from one configuration to another
- Merge objects between different device groups or VSYSes
- Automatically copy referenced objects (e.g., address group members)
- Select objects by name or using filter criteria

This is particularly useful for:

- Migrating objects from one device group to another
- Consolidating objects from multiple device groups
- Copying objects from development to production environments
- Creating templates from existing objects

## Key Features

- **Selective Merging**: Copy individual objects, multiple objects matching criteria, or all objects
- **Reference Handling**: Automatically identify and copy referenced objects (for groups)
- **Conflict Resolution**: Options to skip or replace existing objects
- **Context-Aware**: Support for different contexts (shared, device_group, vsys, template)
- **Version-Aware**: Handle differences between PAN-OS versions

## Using Object Merger

There are three ways to use the object merge functionality:

### ObjectMerger Class

The `ObjectMerger` class provides direct access to object merge capabilities:

```python
from panos_xml_utils.core.object_merger import ObjectMerger

# Initialize with source and target configurations
merger = ObjectMerger(
    source_tree,  # lxml ElementTree for source configuration
    target_tree,  # lxml ElementTree for target configuration
    source_device_type="panorama",  # panorama or firewall
    target_device_type="panorama", 
    source_version="10.2", 
    target_version="10.2"
)

# Copy a single object
success = merger.copy_object(
    "address",  # Object type
    "dns-server",   # Object name
    "shared",        # Source context
    "device_group",  # Target context
    True,           # Skip if exists
    True,           # Copy references
    target_device_group="DG2"  # Target context parameter
)

# Copy multiple objects matching criteria
criteria = {
    "type": "ip-netmask",
    "value": "8.8.8.8"
}

copied, total = merger.copy_objects(
    "address",
    "shared",
    "device_group",
    None,           # No specific object names
    criteria,       # Filter criteria
    True,           # Skip if exists
    True,           # Copy references
    target_device_group="DG2"
)

# Merge all objects of specified types
results = merger.merge_all_objects(
    ["address", "address_group", "service", "service_group"],
    "shared",
    "device_group",
    True,           # Skip if exists
    True,           # Copy references
    target_device_group="DG2"
)
```

### PanOsXmlConfig Helper Methods

The `PanOsXmlConfig` class provides a simplified interface:

```python
from panos_xml_utils import PanOsXmlConfig

# Load source and target configurations
source_config = PanOsXmlConfig("panorama.xml")
target_config = PanOsXmlConfig("panorama_target.xml")

# Merge an object
success = source_config.merge_object(
    target_config,
    "address",
    "dns-server",
    "shared",
    "device_group",
    target_device_group="DG2"
)

# Save the updated configuration
if success:
    target_config.save("updated.xml")
```

### Command-Line Interface

The CLI provides commands for object merging:

#### Merge a Single Object

```bash
python cli.py merge object \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --type address \
  --name "dns-server" \
  --source-context shared \
  --target-context device_group \
  --target-dg DG2 \
  --output updated.xml
```

#### Merge Multiple Objects

```bash
# Using a list of object names
python cli.py merge objects \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --type address \
  --names-file object_names.txt \
  --source-context shared \
  --target-context device_group \
  --target-dg DG2 \
  --output updated.xml

# Using filter criteria
python cli.py merge objects \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --type address \
  --criteria criteria.json \
  --source-context shared \
  --target-context device_group \
  --target-dg DG2 \
  --output updated.xml
```

Example criteria file (criteria.json):
```json
{
  "type": "ip-netmask",
  "value": "8.8.8.8"
}
```

#### Merge All Objects

```bash
python cli.py merge all-objects \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --source-context shared \
  --target-context device_group \
  --target-dg DG2 \
  --output updated.xml
```

## Use Cases

### Migrating Objects Between Device Groups

When restructuring your Panorama device groups, you may need to migrate objects from one device group to another:

```bash
python cli.py merge all-objects \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --source-context device_group \
  --target-context device_group \
  --source-dg "Old-DG" \
  --target-dg "New-DG" \
  --output updated.xml
```

### Promoting Shared Objects from Firewall to Panorama

When migrating from a standalone firewall to a Panorama-managed deployment:

```bash
python cli.py merge all-objects \
  --source-config firewall.xml \
  --target-config panorama.xml \
  --source-context vsys \
  --target-context device_group \
  --source-vsys "vsys1" \
  --target-dg "Migration-DG" \
  --output panorama_updated.xml
```

### Creating Object Templates

You can create templates from existing objects by copying them to a new configuration:

```bash
python cli.py merge objects \
  --source-config prod-panorama.xml \
  --target-config template-panorama.xml \
  --type address \
  --criteria template-criteria.json \
  --source-context device_group \
  --target-context device_group \
  --source-dg "Production" \
  --target-dg "Templates" \
  --output template-updated.xml
```

### Consolidating Shared Objects

You can move device group-specific objects to the shared context for better object management:

```bash
python cli.py merge objects \
  --source-config panorama.xml \
  --target-config panorama.xml \
  --type address \
  --criteria common-objects.json \
  --source-context device_group \
  --target-context shared \
  --source-dg "DG1" \
  --output updated.xml
```

## Code Examples

### Example 1: Merge a Single Address Object

```python
from panos_xml_utils import PanOsXmlConfig

# Load configurations
source_config = PanOsXmlConfig("panorama.xml")
target_config = PanOsXmlConfig("panorama.xml")  # Same file for in-place update

# Merge an address object from shared to a device group
success = source_config.merge_object(
    target_config,
    "address",
    "dns-server",
    "shared",
    "device_group",
    skip_if_exists=False,  # Replace if exists
    copy_references=False,  # Not needed for simple address objects
    target_device_group="DG2"
)

if success:
    target_config.save("panorama_updated.xml")
    print("Object merged successfully")
else:
    print("Failed to merge object")
```

### Example 2: Merge an Address Group with All Members

```python
from panos_xml_utils import PanOsXmlConfig
from panos_xml_utils.core.object_merger import ObjectMerger

# Load configurations
source_config = PanOsXmlConfig("panorama.xml")
target_config = PanOsXmlConfig("panorama.xml")

# Create merger
merger = ObjectMerger(
    source_config.tree,
    target_config.tree,
    source_config.device_type,
    target_config.device_type
)

# Copy an address group with all its members
success = merger.copy_object(
    "address_group",
    "Internal-Networks",
    "shared",
    "device_group",
    True,  # Skip if exists
    True,  # Copy references - important for groups
    target_device_group="DG2"
)

print(f"Merged address group: {success}")

# Show referenced/copied objects
if success and merger.referenced_objects:
    print(f"Referenced {len(merger.referenced_objects)} objects:")
    for obj_type, obj_name in merger.referenced_objects:
        print(f"  - {obj_type}: {obj_name}")

if success:
    target_config.save("panorama_updated.xml")
```

### Example 3: Merge Objects Matching Criteria

```python
from panos_xml_utils import PanOsXmlConfig
from panos_xml_utils.core.object_merger import ObjectMerger

# Load configurations
source_config = PanOsXmlConfig("panorama.xml")
target_config = PanOsXmlConfig("panorama_target.xml")

# Create merger
merger = ObjectMerger(
    source_config.tree,
    target_config.tree,
    source_config.device_type,
    target_config.device_type
)

# Define criteria for selecting objects
criteria = {
    "type": "ip-netmask",  # Match objects with ip-netmask type
    "value": "10.0.0.0/8"  # Match this specific value
}

# Copy matching objects
copied, total = merger.copy_objects(
    "address",
    "device_group",
    "device_group",
    None,  # No specific names
    criteria,
    True,  # Skip if exists
    True,  # Copy references
    source_device_group="DG1",
    target_device_group="DG2"
)

print(f"Copied {copied} of {total} address objects")

if copied > 0:
    target_config.save("panorama_target_updated.xml")
```

### Example 4: Merge All Object Types

```python
from panos_xml_utils import PanOsXmlConfig
from panos_xml_utils.core.object_merger import ObjectMerger

# Load configurations
source_config = PanOsXmlConfig("panorama.xml")
target_config = PanOsXmlConfig("panorama_target.xml")

# Create merger
merger = ObjectMerger(
    source_config.tree,
    target_config.tree,
    source_config.device_type,
    target_config.device_type
)

# Define object types to merge
object_types = [
    "address",
    "address_group",
    "service",
    "service_group",
    "tag"
]

# Merge all objects
results = merger.merge_all_objects(
    object_types,
    "shared",
    "device_group",
    True,  # Skip if exists
    True,  # Copy references
    target_device_group="DG2"
)

# Print results
for object_type, (copied, total) in results.items():
    print(f"{object_type}: Copied {copied} of {total} objects")

# Save the updated configuration
target_config.save("panorama_target_updated.xml")
```

## Best Practices

1. **Always Backup Configurations**: Create backups before merging objects
2. **Test in Non-Production**: Test object merges in a test environment first
3. **Handle Groups Carefully**: Always use `copy_references=True` when merging groups
4. **Use Validation**: Validate configurations after merging
5. **Consider Dependencies**: Be aware of object dependencies and references
6. **Use Filtering**: Use criteria to select only the objects you need
7. **Review Logs**: Check logs for warnings and errors
8. **Start Small**: Begin with a few objects before merging many
9. **Verify After Merge**: Check that objects were correctly merged and are functional

## Troubleshooting

### Common Issues

1. **Object Not Found**: Check that the object name is correct and exists in the source
2. **Missing Group Members**: Ensure you're using `copy_references=True` when merging groups
3. **Element Not Found**: The target context may not exist or have the right structure
4. **Duplicate Names**: Objects with the same name but different values can cause conflicts
5. **Recursive Dependencies**: Complex group hierarchies might need multiple passes

### Troubleshooting Steps

1. **Enable Verbose Logging**: Use `--verbose` to see more details
2. **Check Skipped Objects**: The merger keeps track of skipped objects and reasons
3. **Verify Object Names**: Ensure object names match exactly (case-sensitive)
4. **Check XML Structure**: Ensure the target XML has the correct structure for objects
5. **Validate Criteria**: Check that filter criteria are correctly formatted
6. **Review Referenced Objects**: Check the `referenced_objects` list after merging