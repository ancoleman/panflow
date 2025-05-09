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
- **Natural language processing**: Interact with PANFlow using plain English queries and commands
- **AI integration**: Optional AI-powered natural language understanding for complex queries
- **Command-line interface**: Feature-rich CLI for configuration management
- **Device type auto-detection**: Automatically detects if a configuration is from a Panorama or firewall
- **Query-based filtering**: Select objects and policies using graph queries
- **Conflict resolution**: Multiple strategies for handling merging conflicts
- **HTML report templates**: Customizable HTML reports for configuration analysis
- **Functional design**: Modular architecture with separation of concerns

## Documentation

| Category | Description | Link |
|----------|-------------|------|
| **Getting Started** | Quick start guide | [Getting Started](docs/getting_started.md) |
| **CLI Usage** | Comprehensive CLI reference | [CLI Usage Guide](CLI_USAGE.md) |
| **Natural Language Query** | Using natural language with PANFlow | [Natural Language Query](docs/nlq.md) |
| **Graph Query Language** | Reference for the graph-based query language | [Graph Query Language](docs/graph_query_language.md) |
| **Query Examples** | Example queries for common tasks | [Query Examples](docs/query_examples.md) |
| **Object Merging** | Documentation on merging objects | [Object Merger](docs/object_merger.md) |
| **Deduplication** | Guide for deduplicating objects | [Deduplication](docs/deduplication.md) |
| **Cleanup Detection** | How unused objects and disabled policies are detected | [Cleanup Detection](docs/cleanup_detection.md) |
| **Cleanup Examples** | Examples of cleanup commands | [Cleanup Examples](examples/cleanup_examples.md) |
| **Error Handling** | Error handling and troubleshooting | [Error Handling](docs/error_handling.md) |
| **XPath Handling** | Dynamic XPath resolver documentation | [Dynamic XPath](docs/dynamic_xpath.md) |
| **XML Utilities** | XML manipulation utilities | [XML Utils](docs/xml_utils.md) |
| **XML Package** | Consolidated XML package documentation | [XML Package](docs/xml_package.md) |
| **Reporting Package** | Consolidated reporting package documentation | [Reporting Consolidation](docs/reporting_consolidation.md) |
| **CLI Command Pattern** | Command pattern abstraction for CLI | [CLI Command Pattern](docs/cli_command_pattern.md) |

## Installation

### Using Poetry (Recommended for Developers)

[Poetry](https://python-poetry.org/) is a modern dependency management and packaging tool for Python. It's the recommended way to install PANFlow for development.

1. **Install Poetry** (if not already installed):

   ```bash
   # On Linux, macOS, WSL
   curl -sSL https://install.python-poetry.org | python3 -

   # On Windows PowerShell
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

   See the [Poetry documentation](https://python-poetry.org/docs/#installation) for more installation options.

2. **Install PANFlow using Poetry**:

   ```bash
   # Clone the repository
   git clone https://code.pan.run/gcs-automation/panflow.git
   cd panflow

   # Install the package and all dependencies
   poetry install
   
   # Activate the virtual environment
   poetry shell
   ```

3. **Run PANFlow**:

   ```bash
   # Inside the Poetry shell, you can run PANFlow directly
   panflow --help
   
   # Or without activating the shell
   poetry run panflow --help
   ```

### Using pip

If you prefer pip, you can install PANFlow with:

```bash
pip install panflow
```

After installation, you can run it with:

```bash
panflow --help
```

### Standalone Binaries

For users who prefer a standalone executable without installing Python or any dependencies, we provide pre-built binaries for Windows, macOS, and Linux.

1. Download the appropriate binary for your platform from the [Releases page](https://code.pan.run/gcs-automation/panflow/-/releases):
   - `panflow-windows.exe` - For Windows users
   - `panflow-macos` - For macOS users
   - `panflow-linux` - For Linux users

2. Make the binary executable (Linux/macOS):
   ```bash
   chmod +x panflow-linux  # or panflow-macos
   ```

3. Install to your system (optional):

   **Linux/macOS**:
   ```bash
   # Using the included install script
   ./build_scripts/install.sh
   
   # Or install manually
   sudo cp panflow-linux /usr/local/bin/panflow  # or panflow-macos
   ```

   **Windows**:
   ```
   # Using the included install script
   build_scripts\install.bat
   
   # Or install manually by moving the executable to a location in your PATH
   ```

   **Building from source**:
   ```bash
   # Build for your current platform
   ./build_scripts/build.sh
   
   # You'll find the binary in the dist/ directory
   ```

4. Run PANFlow:
   ```bash
   panflow --help  # If installed in your PATH
   # Or run directly
   ./panflow-linux --help  # or panflow-macos or panflow-windows.exe
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
from panflow import PANFlowConfig

# Load a configuration file
config = PANFlowConfig(config_file="firewall.xml")

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

The library includes a comprehensive CLI that can be accessed through the command line:

```bash
# List all address objects
python cli.py object list --config firewall.xml --type address --context vsys --vsys vsys1

# Add a new address object
python cli.py object add --config firewall.xml --type address --name web-server --properties web-server.json --output updated.xml

# Generate a report of unused objects
python cli.py report unused-objects --config firewall.xml --output unused.json

# Bulk update security policies matching criteria
python cli.py policy bulk-update --config firewall.xml --type security_rules --criteria criteria.json --operations operations.json --output updated.xml

# Find and merge duplicate objects
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml

# Find and clean up unused objects
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --dry-run

# Find and remove disabled policies
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --report-file report.json

# Query the configuration with the graph query language
python cli.py query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value"

# Filter objects using a graph query
python cli.py object list --config config.xml --type address --query-filter "MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))"

# Filter policies using a graph query
python cli.py policy filter --config config.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.port = '80'"

# Use natural language to clean up unused objects
python cli.py nlq query "show me all unused address objects"
python cli.py nlq query "cleanup unused service objects but don't make any changes"

# Use an interactive natural language session
python cli.py nlq interactive

# Merge a policy from one config to another
python cli.py merge policy --source-config source.xml --target-config target.xml --type security_pre_rules --name "Allow Web" --output merged.xml

# Run commands with auto-detected device type
python cli.py object list --config config.xml --type address  # Device type will be auto-detected
```

> **Note**: When installed as a package, you can also run commands using simply `panflow` followed by the command.

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
│   ├── cli/                     # CLI command framework
│   │   ├── __init__.py
│   │   ├── app.py              # CLI app definition
│   │   ├── common.py           # Shared CLI options
│   │   ├── command_base.py     # Command pattern abstraction
│   │   └── commands/           # CLI command modules
│   │       ├── __init__.py
│   │       ├── cleanup_commands.py
│   │       ├── deduplicate_commands.py
│   │       ├── merge_commands.py
│   │       ├── nat_commands.py
│   │       ├── nlq_commands.py   # Natural language query commands
│   │       ├── object_commands.py
│   │       ├── object_commands_refactored.py # New command pattern example
│   │       ├── policy_commands.py
│   │       └── query_commands.py
│   ├── constants/
│   │   ├── __init__.py
│   │   └── common.py           # Global constants
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── bulk_operations.py  # Bulk configuration operations
│   │   ├── config_loader.py    # XML loading and parsing
│   │   ├── config_saver.py     # XML saving and export
│   │   ├── conflict_resolver.py # Conflict resolution strategies
│   │   ├── deduplication.py    # Duplicate object handling
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── graph_service.py    # Graph service
│   │   ├── graph_utils.py      # Configuration graph builder
│   │   ├── logging_utils.py    # Logging and error tracking
│   │   ├── nat_splitter.py     # NAT rule splitting
│   │   ├── object_finder.py    # Object finding
│   │   ├── object_merger.py    # Object merging handling
│   │   ├── object_validator.py # Object validation
│   │   ├── policy_merger.py    # Policy merging handling
│   │   ├── query_engine.py     # Graph query execution engine
│   │   ├── query_language.py   # Graph query language parser
│   │   ├── template_loader.py  # HTML template loader
│   │   ├── xml/                # Consolidated XML Package
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # Core XML utilities
│   │   │   ├── builder.py     # XML construction classes
│   │   │   ├── cache.py       # XML caching functionality
│   │   │   ├── diff.py        # XML comparison utilities
│   │   │   └── query.py       # XML query functionality
│   │   └── xpath_resolver.py   # Version-aware XPath handling
│   ├── modules/                # Functional modules
│   │   ├── __init__.py
│   │   ├── groups.py           # Group operations
│   │   ├── objects.py          # Object management
│   │   ├── policies.py         # Policy management
│   │   └── reports.py          # Report generation
│   ├── nlq/                    # Natural Language Query Module
│   │   ├── __init__.py
│   │   ├── ai_processor.py     # AI-powered processing
│   │   ├── command_mapper.py   # Maps intents to commands
│   │   ├── entity_extractor.py # Extracts entities from queries
│   │   ├── intent_parser.py    # Parses intents from queries
│   │   └── processor.py        # Main NLQ processor
│   ├── reporting/              # Consolidated Reporting Package
│   │   ├── __init__.py
│   │   ├── engine.py           # Reporting engine
│   │   └── reports/            # Report implementation modules
│   │       ├── __init__.py
│   │       ├── duplicate_objects.py
│   │       ├── policy_analysis.py
│   │       └── unused_objects.py
│   ├── templates/              # HTML report templates
│   │   └── reports/
│   │       ├── base.html
│   │       ├── custom_report.html
│   │       ├── object_usage.html
│   │       ├── sections/
│   │       │   ├── object_section.html
│   │       │   └── policy_section.html
│   │       └── security_policy_analysis.html
│   └── xpath_mappings/         # XPath definitions by version
│       ├── panos_10_1.yaml
│       ├── panos_10_2.yaml
│       ├── panos_11_0.yaml
│       ├── panos_11_1.yaml
│       └── panos_11_2.yaml
├── docs/                       # Documentation
├── pyproject.toml              # Project metadata
├── pytest.ini                  # Test configuration
├── cli.py                      # Main command-line interface
├── tests/                      # Test suite
│   ├── fixtures/               # Test fixtures
│   ├── integration/            # Integration tests
│   └── unit/                   # Unit tests
└── test_files/                 # Test data files
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
config = PANFlowConfig("firewall.xml", version="10.1")

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
from panflow import PANFlowConfig
from panflow.core.deduplication import DeduplicationEngine

# Load configuration
config = PANFlowConfig("firewall.xml")

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
from panflow import PANFlowConfig
from panflow.core.bulk_operations import ConfigUpdater

# Load configuration
config = PANFlowConfig("panorama.xml")

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
from panflow import PANFlowConfig

# Load configuration
config = PANFlowConfig("config.xml")

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

### Development Setup

1. **Set up the development environment**:

   ```bash
   # Clone the repository
   git clone https://code.pan.run/gcs-automation/panflow.git
   cd panflow
   
   # Install with Poetry for development
   poetry install
   
   # Activate the virtual environment
   poetry shell
   ```

2. **Run tests**:

   ```bash
   # Run the full test suite
   pytest
   
   # Run with coverage
   pytest --cov=panflow
   ```

3. **Code formatting and linting**:

   ```bash
   # Format code with Black
   black .
   
   # Sort imports with isort
   isort .
   
   # Run type checking with mypy
   mypy panflow
   
   # Run flake8 for linting
   flake8 panflow
   ```

### Project Structure

The project uses Poetry for dependency management and packaging. The main configuration is in `pyproject.toml`:

```toml
[tool.poetry.scripts]
panflow = "panflow.cli:app"
```

This creates the `panflow` command-line entry point, which points to the `app` object in the `panflow.cli` module. When you install the package using Poetry or pip, this entry point allows you to run the application with the `panflow` command.

### Continuous Integration and Deployment

The project uses GitLab CI/CD for continuous integration and deployment. The configuration is in `.gitlab-ci.yml`:

- **Test Stage**: Runs tests and linting
- **Build Stage**: Creates Python packages and standalone binaries for all platforms
- **Release Stage**: Creates a GitLab Release with all artifacts

To create a new release:

1. Tag a commit:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

2. The CI/CD pipeline will automatically build the packages and binaries and create a release

You can find all releases at: https://code.pan.run/gcs-automation/panflow/-/releases

For a detailed list of changes between versions, please see the [CHANGELOG.md](CHANGELOG.md) file.

## License

This library is available under the MIT License.