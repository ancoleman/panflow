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
- **Graph-based querying**: Query the configuration using a Cypher-like query language
- **Command-line interface**: Feature-rich CLI for configuration management
- **Functional design**: Modular architecture with separation of concerns

## Documentation

| Category | Description | Link |
|----------|-------------|------|
| **Getting Started** | Quick start guide | [Getting Started](docs/getting_started.md) |
| **CLI Usage** | Comprehensive CLI reference | [CLI Usage Guide](CLI_USAGE.md) |
| **CLI Migration** | Guide for transitioning from legacy to package-based CLI | [CLI Migration Guide](docs/cli_migration.md) |
| **Graph Query Language** | Reference for the graph-based query language | [Graph Query Language](docs/graph_query_language.md) |
| **Query Examples** | Example queries for common tasks | [Query Examples](docs/query_examples.md) |
| **Object Merging** | Documentation on merging objects | [Object Merger](docs/object_merger.md) |
| **Deduplication** | Guide for deduplicating objects | [Deduplication](docs/deduplication.md) |
| **Error Handling** | Error handling and troubleshooting | [Error Handling](docs/error_handling.md) |
| **XPath Handling** | Dynamic XPath resolver documentation | [Dynamic XPath](docs/dynamic_xpath.md) |
| **XML Utilities** | XML manipulation utilities | [XML Utils](docs/xml_utils.md) |

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
from panflow import PanOsXmlConfig

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

The library includes a comprehensive CLI that can be accessed through `panflow_cli.py`:

```bash
# List all address objects
python panflow_cli.py object list --config firewall.xml --type address --context vsys --vsys vsys1

# Add a new address object
python panflow_cli.py object add --config firewall.xml --type address --name web-server --properties web-server.json --output updated.xml

# Generate a report of unused objects
python panflow_cli.py report unused-objects --config firewall.xml --output unused.json

# Bulk update security policies matching criteria
python panflow_cli.py policy bulk-update --config firewall.xml --type security_rules --criteria criteria.json --operations operations.json --output updated.xml

# Find and merge duplicate objects
python panflow_cli.py deduplicate --config firewall.xml --type address --output deduped.xml

# Query the configuration with the graph query language
python panflow_cli.py query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value"

# Merge a policy from one config to another
python panflow_cli.py merge policy --source-config source.xml --target-config target.xml --type security_pre_rules --name "Allow Web" --output merged.xml

# Launch interactive query mode
python panflow_cli.py query interactive --config config.xml
```

> **Note**: All CLI commands can be used with either `panflow_cli.py` (recommended) or `cli.py` (legacy). See the [CLI Migration Guide](docs/cli_migration.md) for details.

For a complete reference of all CLI commands and options, see the [CLI Usage Guide](CLI_USAGE.md).

## Bulk Operations

The library provides powerful bulk operations for modifying multiple configuration elements at once:

```python
from panflow.core.bulk_operations import ConfigUpdater

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
from panflow.core.deduplication import DeduplicationEngine

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
├── panflow/
│   ├── __init__.py
│   ├── constants
│   │   └── common.py
│   ├── core                    # Core functionality
│   │   ├── bulk_operations.py  # Bulk configuration operations
│   │   ├── config_loader.py    # XML loading and parsing
│   │   ├── config_saver.py     # XML saving and export
│   │   ├── deduplication.py    # Duplicate object handling
│   │   ├── logging_utils.py    # Logging and error tracking
│   │   ├── object_merger.py    # Object merging handling
│   │   ├── policy_merger.py    # Policy merging handling
│   │   ├── xml_utils.py        # XML manipulation utilities
│   │   └── xpath_resolver.py   # Version-aware XPath handling
│   ├── modules
│   │   ├── groups.py           # Group operations
│   │   ├── objects.py          # Object management
│   │   ├── policies.py         # Policy management
│   │   └── reports.py          # Report generation
│   └── xpath_mappings          # XPath definitions by version
│       ├── panos_10_1.yaml
│       ├── panos_10_2.yaml
│       └── panos_11_2.yaml
├── pyproject.toml
├── panflow_cli.py # Main command-line interface (recommended)
├── cli.py # Legacy command-line interface (deprecated)
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
from panflow.core.xpath_resolver import get_all_versions
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
from panflow import PanOsXmlConfig
from panflow.core.deduplication import DeduplicationEngine

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

For more information on deduplication options and strategies, see the [Deduplication Guide](docs/deduplication.md).

### Bulk Updating Security Policies

```python
from panflow import PanOsXmlConfig
from panflow.core.bulk_operations import ConfigUpdater

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

### Using the Graph Query API

```python
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow import PanOsXmlConfig

# Load configuration
config = PanOsXmlConfig("config.xml")

# Build the graph
graph = ConfigGraph()
graph.build_from_xml(config.tree)

# Create and execute a query
query = Query("MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.value CONTAINS '10.1.1' RETURN r.name, a.name")
executor = QueryExecutor(graph)
results = executor.execute(query)

# Process the results
for row in results:
    print(f"Rule '{row['r.name']}' uses address '{row['a.name']}'")
```

For more information on the graph query language, see:
- [Graph Query Language Guide](docs/graph_query_language.md)
- [Query Examples](docs/query_examples.md)
- [Graph Query Reference](docs/graph_query_reference.md)

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