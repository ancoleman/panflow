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
│   ├── xml_utils.py         # Common XML manipulation utilities (deprecated, use xml package)
│   ├── xml_builder.py       # XML builder utilities (deprecated, use xml package)
│   ├── xml_cache.py         # XML caching (deprecated, use xml package)
│   ├── xml_diff.py          # XML diffing (deprecated, use xml package)
│   ├── xml_query.py         # XML querying (deprecated, use xml package)
│   ├── xml/                 # Consolidated XML package (recommended)
│   │   ├── __init__.py      # XML package exports
│   │   ├── base.py          # Core XML parsing and utility functions
│   │   ├── builder.py       # XML construction classes
│   │   ├── cache.py         # XML caching functionality
│   │   ├── diff.py          # XML comparison and diffing tools
│   │   └── query.py         # XML query functionality
│   ├── logging_utils.py     # Logging configuration utilities
│   ├── bulk_operations.py   # Bulk configuration update operations
│   ├── graph_service.py     # Graph representation of configurations
│   ├── graph_utils.py       # Graph query utilities
│   ├── query_engine.py      # Query execution engine
│   ├── query_language.py    # Query language parser
│   └── deduplication.py     # Object deduplication engine
├── modules/
│   ├── __init__.py          # Module exports
│   ├── objects.py           # Object-related functions (address, service, etc.)
│   ├── policies.py          # Policy-related functions (security, NAT, etc.)
│   ├── groups.py            # Group-related functions (add/remove members)
│   └── reports.py           # Report generation functions (deprecated, use reporting package)
├── reporting/               # Consolidated reporting package (recommended)
│   ├── __init__.py          # Reporting package exports with backward compatibility
│   ├── engine.py            # Core reporting engine (ReportingEngine class)
│   ├── reports/             # Report generators
│   │   ├── __init__.py      # Reports package exports
│   │   ├── unused_objects.py # Unused objects report generator
│   │   ├── duplicate_objects.py # Duplicate objects report generator
│   │   └── policy_analysis.py # Security policy analysis report generator
│   └── formatters/          # Output formatters
│       ├── __init__.py      # Formatters package exports
│       ├── html.py          # HTML output formatter
│       ├── json.py          # JSON output formatter
│       └── csv.py           # CSV output formatter
├── nlq/                     # Natural Language Query capabilities
│   ├── __init__.py          # NLQ package exports
│   ├── processor.py         # Main NLQ processor
│   ├── entity_extractor.py  # Entity extraction from natural language
│   ├── intent_parser.py     # Intent parsing from natural language
│   ├── command_mapper.py    # Maps NLQ intents to CLI commands
│   └── ai_processor.py      # AI-powered NLQ processing (optional)
├── constants/
│   ├── __init__.py          # Constants exports
│   └── common.py            # Common constants
├── xpath_mappings/
│   ├── panos_10.1.yaml      # XPath mappings for PAN-OS 10.1
│   ├── panos_10.2.yaml      # XPath mappings for PAN-OS 10.2
│   ├── panos_11.0.yaml      # XPath mappings for PAN-OS 11.0
│   ├── panos_11.1.yaml      # XPath mappings for PAN-OS 11.1
│   └── panos_11.2.yaml      # XPath mappings for PAN-OS 11.2
├── cli/                     # Command Line Interface
│   ├── __init__.py          # CLI package exports
│   ├── app.py               # Main CLI application
│   ├── common.py            # Common CLI utilities
│   └── commands/            # CLI command groups
│       ├── __init__.py      # Command exports
│       ├── object_commands.py # Object-related commands
│       ├── policy_commands.py # Policy-related commands
│       ├── merge_commands.py  # Configuration merge commands
│       ├── query_commands.py  # Graph query commands
│       ├── cleanup_commands.py # Cleanup and analysis commands
│       ├── nat_commands.py    # NAT-related commands
│       ├── nlq_commands.py    # Natural language query commands
│       └── deduplicate_commands.py # Deduplication commands
└── cli.py                   # CLI entry point
```

## Module Functionality

### Core Modules

- `config_loader.py` - Functions to load and parse PAN-OS XML configurations
- `config_saver.py` - Functions to save and export XML configurations
- `xpath_resolver.py` - Version-aware XPath resolution for different PAN-OS versions
- `xml/*.py` - Consolidated package for XML manipulation (recommended)
  - `base.py` - Core XML parsing and utility functions
  - `builder.py` - XML construction and manipulation
  - `cache.py` - Caching layer for efficient XML operations
  - `diff.py` - XML comparison and diffing
  - `query.py` - XML query capabilities
- `xml_utils.py` - General-purpose XML utilities (deprecated, use xml package)
- `xml_builder.py` - XML builder utilities (deprecated, use xml package)
- `xml_cache.py` - XML caching (deprecated, use xml package)
- `xml_diff.py` - XML diffing (deprecated, use xml package)
- `xml_query.py` - XML querying (deprecated, use xml package)
- `logging_utils.py` - Logging configuration and utilities
- `bulk_operations.py` - Advanced bulk operations for modifying multiple configuration elements
- `graph_service.py` - Graph representation of configurations
- `query_engine.py` - Query execution engine for graph-based queries
- `query_language.py` - Parser for the graph query language
- `deduplication.py` - Engine for finding and merging duplicate objects

### Functional Modules

- `objects.py` - Manage address objects, service objects, etc.
- `policies.py` - Manage security rules, NAT rules, etc.
- `groups.py` - Manage address groups, service groups, etc.
- `reports.py` - Generate reports on configurations (deprecated, use reporting package)

### Reporting Package

- `reporting/engine.py` - Core reporting engine (ReportingEngine class)
- `reporting/reports/` - Individual report generators:
  - `unused_objects.py` - Unused objects report generator
  - `duplicate_objects.py` - Duplicate objects report generator
  - `policy_analysis.py` - Security policy analysis report generator
- `reporting/formatters/` - Output formatters:
  - `html.py` - HTML output formatter
  - `json.py` - JSON output formatter
  - `csv.py` - CSV output formatter

### Natural Language Query (NLQ) Package

- `nlq/processor.py` - Main NLQ processor
- `nlq/entity_extractor.py` - Extracts entities from natural language
- `nlq/intent_parser.py` - Parses intents from natural language
- `nlq/command_mapper.py` - Maps NLQ intents to CLI commands
- `nlq/ai_processor.py` - AI-powered NLQ processing (optional)

### Constants

- `common.py` - Common constants (XPaths, namespaces, error codes, etc.)

### XPath Mappings

- YAML files containing version-specific XPath mappings for different PAN-OS versions

## Key Features

### Consolidated XML Package

The `panflow.core.xml` package provides a centralized and organized approach to XML manipulation:

- **Organized functionality**: Clear separation of XML operations into logical modules
- **Backward compatibility**: Maintains compatibility with legacy code
- **Reduced circular dependencies**: Resolves circular import issues in the old structure
- **Enhanced maintainability**: Makes it easier to understand and extend XML functionality

Example usage:
```python
# Recommended import pattern
from panflow.core.xml import base as xml_base
from panflow.core.xml import query as xml_query
from panflow.core.xml import builder as xml_builder

# Instead of (deprecated):
# from panflow.core.xml_utils import ...
# from panflow.core.xml_query import ...
```

### Consolidated Reporting Package

The `panflow.reporting` package provides a unified framework for generating reports:

- **ReportingEngine class**: Provides a single interface for all report types
- **Modular report generators**: Separate modules for each report type
- **Multiple output formats**: Support for HTML, JSON, and CSV output
- **Built-in formatters**: Consistent formatting across report types

Example usage:
```python
from panflow.reporting import ReportingEngine

engine = ReportingEngine(
    tree=xml_tree,
    device_type="firewall",
    context_type="vsys",
    version="10.1.0"
)

# Generate an unused objects report
report = engine.generate_unused_objects_report(
    object_type="address",
    output_file="unused_objects.json"
)
```

### Graph Query Language

The graph query system provides a powerful way to query configurations:

- **Cypher-like syntax**: Familiar to users of graph databases
- **Flexible matching**: Match objects and policies based on complex criteria
- **Integration with CLI**: Use queries in CLI commands via `--query-filter`
- **Query engine**: Efficient query execution and result processing

Example usage:
```
panflow query execute --config CONFIG_FILE --query 'MATCH (o:address) WHERE o.name CONTAINS "web" RETURN o.name, o.value'
```

### Natural Language Query (NLQ)

The NLQ system provides a user-friendly way to interact with the tool:

- **Natural language processing**: Parse commands in plain English
- **Entity extraction**: Identify objects, policies, and actions
- **Command mapping**: Map natural language to CLI commands
- **AI integration**: Optional AI-powered understanding for complex queries

Example usage:
```
panflow nlq "Show me all address objects that contain 'web' in their name"
```

### Bulk Operations

The `bulk_operations.py` module provides a framework for performing operations on multiple configuration elements simultaneously:

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

The `deduplication.py` module provides tools for identifying and merging duplicate objects:

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
6. **Deduplicate commands**: Find and merge duplicate objects
7. **Query commands**: Execute graph queries against configurations
8. **Cleanup commands**: Identify and clean up unused objects and disabled policies
9. **NAT commands**: Manage NAT rules and configurations
10. **NLQ commands**: Process natural language queries and commands

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
2. **Consolidated packages**: XML and reporting packages provide cohesive functionality
3. **Modules to CLI**: The CLI uses modules to provide functionality
4. **XPath mappings to core**: XPath mappings are loaded by the core
5. **Query engine to modules**: Graph queries provide filtering across object and policy operations
6. **NLQ to CLI**: Natural language queries map to CLI commands
7. **Constants to all**: Constants are used throughout the project

## Extensibility

The project is designed for extensibility in several ways:

1. **New PAN-OS versions**: Add new YAML files in `xpath_mappings/`
2. **New object types**: Extend existing modules
3. **New bulk operations**: Add methods to `ConfigUpdater`
4. **New report types**: Add modules to `reporting/reports/`
5. **New formatters**: Add modules to `reporting/formatters/`
6. **New XML functionality**: Add to the appropriate module in `core/xml/`
7. **New query capabilities**: Extend `query_engine.py` and `query_language.py`
8. **New NLQ capabilities**: Extend the NLQ module
9. **New CLI commands**: Add to appropriate command groups in `cli/commands/`

## Configuration File Parsing

The project uses a consistent approach to configuration file parsing:

1. Load XML configuration file
2. Auto-detect device type and PAN-OS version
3. Apply version-specific XPath expressions
4. Perform operations on the configuration
5. Save updated configuration