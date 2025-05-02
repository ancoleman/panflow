# PANFlow

A comprehensive Python library for working with Palo Alto Networks PAN-OS XML configurations, supporting both Panorama and firewall configurations across multiple PAN-OS versions.

## Features

- **Version-aware XML handling**: Automatically adjusts XPath expressions for different PAN-OS versions (10.1, 10.2, 11.0, 11.1, 11.2)
- **Flexible context support**: Works with shared objects, device groups, templates, and virtual systems
- **Comprehensive object support**: Manages all common PAN-OS object types
- **Policy management**: Tools for working with security rules, NAT rules, and more
- **Report generation**: Built-in reports for unused objects, duplicates, and security rule coverage
- **Bulk operations**: Powerful tools for modifying multiple configuration elements at once
- **Deduplication engine**: Find and merge duplicate objects while updating all references
- **Command-line interface**: Feature-rich CLI for configuration management
- **Functional design**: Modular architecture with separation of concerns

## Installation

```bash
pip install panflow
```

## Key Concepts

1. **Externalized XPath mappings**: XPath expressions for different PAN-OS versions are stored in YAML files
2. **Functional core**: Designed with a functional approach for better maintainability
3. **Configuration-first**: All operations work on an XML configuration tree
4. **Context-aware**: Operations apply to the right location in the configuration hierarchy
5. **Bulk operations**: Ability to modify multiple configuration elements with one command
6. **Deduplication**: Intelligent handling of duplicate objects across configurations

## Basic Usage

```python
from panos_xml_utils import PanOsXmlConfig

# Load a configuration file
config = PanOsXmlConfig("firewall.xml")

# Get all address objects in vsys1
address_objects = config.get_objects("address", "vsys", vsys="vsys1")

# Add a new address object
config.add_object(
    "address", 
    "web-server", 
    {"ip-netmask": "10.0.0.5"}, 
    "vsys", 
    vsys="vsys1"
)

# Save the modified configuration
config.save("updated-firewall.xml")
```

## Command-line Usage

The library includes a comprehensive CLI:

```bash
# List all address objects
panflow object list --config firewall.xml --type address --context vsys --vsys vsys1

# Add a new address object
panflow object add --config firewall.xml --type address --name web-server --properties web-server.json --output updated.xml

# Generate a report of unused objects
panflow report unused-objects --config firewall.xml --output unused.json

# Bulk update security policies matching criteria
panflow policy bulk-update --config firewall.xml --type security_rules --criteria criteria.json --operations operations.json --output updated.xml

# Find and merge duplicate objects
panflow deduplicate --config firewall.xml --type address --output deduped.xml
```

## Bulk Operations

The library provides powerful bulk operations for modifying multiple configuration elements at once:

```python
from panos_xml_utils.core.bulk_operations import ConfigUpdater

# Create a configuration updater
updater = ConfigUpdater(config.tree, "firewall", "vsys", config.version, vsys="vsys1")

# Define criteria to select policies
criteria = {
    "source": ["any"],
    "application": ["web-browsing"]
}

# Define operations to apply
operations = {
    "add-profile": {
        "type": "log-forwarding",
        "name": "detailed-logging"
    },
    "add-tag": {
        "name": "audited-2025"
    }
}

# Apply the update
updated_count = updater.bulk_update_policies("security_rules", criteria, operations)
print(f"Updated {updated_count} policies")
```

## Deduplication Engine

The deduplication engine helps identify and merge duplicate objects:

```python
from panos_xml_utils.core.deduplication import DeduplicationEngine

# Create a deduplication engine
engine = DeduplicationEngine(config.tree, "firewall", "vsys", config.version, vsys="vsys1")

# Find duplicate address objects
duplicates, references = engine.find_duplicate_addresses()

# Preview duplicates
for value_key, objects in duplicates.items():
    names = [name for name, _ in objects]
    print(f"Found duplicates with value {value_key}: {', '.join(names)}")

# Merge duplicates and update references
changes = engine.merge_duplicates(duplicates, references, primary_name_strategy="first")
print(f"Merged {len(changes)} duplicate objects")
```

## Module Structure

The library is organized into logical modules:

```
panos_xml_utils/
├── core/                  # Core functionality
│   ├── config_loader.py   # XML loading and parsing
│   ├── config_saver.py    # XML saving and export
│   ├── xpath_resolver.py  # Version-aware XPath handling
│   ├── xml_utils.py       # XML manipulation utilities
│   ├── bulk_operations.py # Bulk configuration operations
│   └── deduplication.py   # Duplicate object handling
├── modules/               # Functional modules
│   ├── objects.py         # Object management
│   ├── policies.py        # Policy management
│   ├── groups.py          # Group operations
│   └── reports.py         # Report generation
├── xpath_mappings/        # XPath definitions by version
│   ├── panos_10.1.yaml
│   ├── panos_10.2.yaml
│   └── panos_11.2.yaml
└── cli.py                 # Command-line interface
```

## XPath Mappings

XPath expressions are stored in version-specific YAML files:

```yaml
# From xpath_mappings/panos_10.1.yaml
contexts:
  panorama:
    shared: "/config/shared"
    device_group: "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']"
  
objects:
  address: "{base_path}/address/entry[@name='{name}']"
  address_group: "{base_path}/address-group/entry[@name='{name}']"
```

This approach makes it easy to support new PAN-OS versions by adding new mapping files without changing code.

## Working with Multiple PAN-OS Versions

The library automatically handles differences between PAN-OS versions:

```python
# Load configuration with explicit version
config = PanOsXmlConfig("firewall.xml", version="10.1")

# Get available versions
from panos_xml_utils.core.xpath_resolver import get_all_versions
versions = get_all_versions()
print(f"Supported PAN-OS versions: {versions}")
```

## Reports

The library includes built-in reports:

```python
# Generate report of unused objects
report = config.generate_unused_objects_report("vsys", vsys="vsys1")

# Generate report of references to an object
refs = config.generate_reference_check_report(
    "web-server", "address", "vsys", vsys="vsys1"
)

# Generate report of security rule coverage
coverage = config.generate_security_rule_coverage_report("vsys", vsys="vsys1")

# Generate report of duplicate objects
duplicates = config.generate_duplicate_objects_report("vsys", vsys="vsys1")
```

## Advanced Usage Examples

### Finding and Merging Duplicate Objects

```python
from panos_xml_utils import PanOsXmlConfig
from panos_xml_utils.core.deduplication import DeduplicationEngine

# Load configuration
config = PanOsXmlConfig("firewall.xml")

# Create deduplication engine
engine = DeduplicationEngine(config.tree, "firewall", "vsys", config.version, vsys="vsys1")

# Find duplicate address objects
duplicates, references = engine.find_duplicate_addresses(reference_tracking=True)

# Merge duplicates
changes = engine.merge_duplicates(duplicates, references, primary_name_strategy="shortest")

# Save updated configuration
config.save("deduped-firewall.xml")
```

### Bulk Updating Security Policies

```python
from panos_xml_utils import PanOsXmlConfig
from panos_xml_utils.core.bulk_operations import ConfigUpdater

# Load configuration
config = PanOsXmlConfig("panorama.xml")

# Create configuration updater
updater = ConfigUpdater(config.tree, "panorama", "device_group", config.version, device_group="DG1")

# Define criteria to select policies with "any" source
criteria = {
    "source": ["any"],
    "action": "allow"
}

# Define operations to apply
operations = {
    "add-profile": {
        "type": "group",
        "name": "default-security-group"
    },
    "add-tag": {
        "name": "reviewed-2025"
    }
}

# Apply the update
updated_count = updater.bulk_update_policies("security_pre_rules", criteria, operations)

# Save the updated configuration
config.save("updated-panorama.xml")
```

## Extending for New PAN-OS Versions

To add support for a new PAN-OS version:

1. Create a new YAML file in `xpath_mappings/` (e.g., `panos_11.3.yaml`)
2. Include any version-specific XPath changes in the `version_specific` section
3. The library will automatically detect and use the new mappings

## Performance Optimization

- XPath mappings are cached for better performance
- Precompiled XPath expressions are used for frequently accessed paths
- Modular design allows for selective imports
- Bulk operations reduce the number of XML tree traversals

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This library is available under the MIT License.