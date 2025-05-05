# PANFlow Project Structure

This document outlines the revised directory structure and organization of the PANFlow project, including the newly added features.

## Directory Structure

```
panflow/
├── __init__.py              # Package exports and PANFlowConfig class
├── core/
│   ├── __init__.py          # Core module exports
│   ├── config_loader.py     # XML configuration loading functions
│   ├── config_saver.py      # XML configuration saving functions
│   ├── xpath_resolver.py    # Version-aware XPath resolution
│   ├── xml_utils.py         # Common XML manipulation utilities
│   ├── logging_utils.py     # Logging configuration utilities
│   ├── bulk_operations.py   # Bulk configuration update operations
│   └── deduplication.py     # Object deduplication engine
├── modules/
│   ├── __init__.py          # Module exports
│   ├── objects.py           # Object-related functions (address, service, etc.)
│   ├── policies.py          # Policy-related functions (security, NAT, etc.)
│   ├── groups.py            # Group-related functions (add/remove members)
│   └── reports.py           # Report generation functions
├── constants/
│   ├── __init__.py          # Constants exports
│   └── common.py            # Common constants
├── xpath_mappings/
│   ├── panos_10.1.yaml      # XPath mappings for PAN-OS 10.1
│   ├── panos_10.2.yaml      # XPath mappings for PAN-OS 10.2
│   ├── panos_11.0.yaml      # XPath mappings for PAN-OS 11.0
│   ├── panos_11.1.yaml      # XPath mappings for PAN-OS 11.1
│   └── panos_11.2.yaml      # XPath mappings for PAN-OS 11.2
└── cli.py                   # Command-line interface
```

## Module Functionality

### Core Modules

- `config_loader.py` - Functions to load and parse PAN-OS XML configurations
- `config_saver.py` - Functions to save and export XML configurations
- `xpath_resolver.py` - Version-aware XPath resolution for different PAN-OS versions
- `xml_utils.py` - General-purpose XML utilities
- `logging_utils.py` - Logging configuration and utilities
- `bulk_operations.py` - Advanced bulk operations for modifying multiple configuration elements
- `deduplication.py` - Engine for finding and merging duplicate objects

### Functional Modules

- `objects.py` - Manage address objects, service objects, etc.
- `policies.py` - Manage security rules, NAT rules, etc.
- `groups.py` - Manage address groups, service groups, etc.
- `reports.py` - Generate reports on configurations

### Constants

- `common.py` - Common constants (XPaths, namespaces, error codes, etc.)

### XPath Mappings

- YAML files containing version-specific XPath mappings for different PAN-OS versions

## New Features

### Bulk Operations

The `bulk_operations.py` module provides a framework for performing operations on multiple configuration elements simultaneously. Key features include:

- **ConfigQuery class**: Selects policies or objects matching specific criteria
- **ConfigUpdater class**: Applies operations to selected elements
- **Bulk update operations**:
  - Adding profile groups
  - Adding security profiles
  - Setting log forwarding profiles
  - Adding tags
  - Modifying rule actions

Example usage in CLI:
```
panflow policy bulk-update --config CONFIG_FILE --type POLICY_TYPE --criteria CRITERIA_FILE --operations OPERATIONS_FILE --output OUTPUT_FILE
```

### Deduplication Engine

The `deduplication.py` module provides tools for identifying and merging duplicate objects. Key features include:

- **DeduplicationEngine class**: Finds duplicate objects based on values
- **Reference tracking**: Identifies and updates all references to duplicate objects
- **Merge strategies**: Different approaches for selecting the primary object

Example usage in CLI:
```
panflow deduplicate --config CONFIG_FILE --type OBJECT_TYPE --output OUTPUT_FILE [--dry-run] [--strategy STRATEGY]
```

## CLI Command Groups

The command-line interface organizes functionality into logical command groups:

1. **Object commands**: List, add, update, delete, and filter objects
2. **Policy commands**: List, add, update, delete, filter, and bulk-update policies
3. **Group commands**: Manage group memberships
4. **Report commands**: Generate various reports (unused objects, duplicates, coverage, references)
5. **Config commands**: Validate and manage configurations
6. **Deduplicate command**: Find and merge duplicate objects

## Class Overview

### PANFlowConfig

The main class that provides an object-oriented interface to the functional core. It handles:

- Loading configurations from files or strings
- Detecting device type and PAN-OS version
- Providing methods for all major operations

### ConfigQuery and ConfigUpdater

Classes that provide bulk operations capabilities:

- `ConfigQuery`: Selects configuration elements based on criteria
- `ConfigUpdater`: Applies operations to selected elements

### DeduplicationEngine

Class that handles identification and merging of duplicate objects:

- Finds objects with identical values
- Tracks references to objects throughout the configuration
- Merges duplicates while updating all references

## Integration Points

The project maintains a clean separation of concerns while ensuring integration between components:

1. **Core to modules**: Core functionality is used by all modules
2. **Modules to CLI**: The CLI uses modules to provide functionality
3. **XPath mappings to core**: XPath mappings are loaded by the core
4. **Constants to all**: Constants are used throughout the project

## Extensibility

The project is designed for extensibility in several ways:

1. **New PAN-OS versions**: Add new YAML files in `xpath_mappings/`
2. **New object types**: Extend existing modules
3. **New bulk operations**: Add methods to `ConfigUpdater`
4. **New report types**: Add functions to `reports.py`
5. **New CLI commands**: Add to appropriate command groups in `cli.py`

## Configuration File Parsing

The project uses a consistent approach to configuration file parsing:

1. Load XML configuration file
2. Auto-detect device type and PAN-OS version
3. Apply version-specific XPath expressions
4. Perform operations on the configuration
5. Save updated configuration