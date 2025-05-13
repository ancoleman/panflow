# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Guidelines
- NEVER add Claude co-authoring to commits
- NEVER add any AI attribution or footers in commit messages
- Keep commit messages clean and focused on the changes made

## Build Commands
- Install: `poetry install`
- Run CLI: `poetry run panflow`
- Lint: `poetry run black .`
- Type Check: `poetry run mypy .`
- Tests: `poetry run pytest`
- Single Test: `poetry run pytest tests/path_to_test.py::TestClass::test_method -v`

## Style Guidelines
- Line length: 100 characters max
- Type annotations: All functions require type annotations for parameters and return values
- Use black for formatting and isort for import sorting
- Import order: stdlib → third-party → local modules
- Naming: snake_case for functions/variables, PascalCase for classes, UPPERCASE for constants
- Error handling: Catch specific exceptions and log with appropriate level in logging_utils
- XPath usage: Never hardcode XPaths - use xpath_resolver.py and version mappings
- XML manipulation: Use xml_utils.py helper functions instead of direct lxml operations
- Context aware: Always check context parameters when working with configurations

## Important Patterns
- Functional design: Prefer pure functions with XML as input/output
- Version handling: All operations must use version-aware XPath resolution
- Context routing: Use correct context (shared/vsys/device_group) for operations
- Query integration: All CLI commands that select objects/policies should support the `--query-filter` parameter
- Testing CLI commands: Use CliRunner from typer.testing for CLI tests and ensure proper parameter structure
- Command Pattern: Use standardized command pattern for all CLI commands with proper decorators
- Output formatting: Support multiple output formats (JSON, table, CSV, YAML, HTML, text) via the `--format` parameter

## Consolidated XML Package
As of June 2024, we've consolidated XML-related functionality into a dedicated package:
- Import from `panflow.core.xml` instead of individual modules
- The old modules (`xml_utils.py`, `xml_builder.py`, etc.) are deprecated but maintained for compatibility
- All new XML functionality should be added to the appropriate submodule in `panflow.core.xml/`
- When working with XML in tests, import from the new consolidated package

## Historical Development Notes

### 2024-06 - CLI Command Pattern Migration and Format Standardization
- Migrated all CLI commands to use the standardized command pattern
- Implemented command_base.py with common functionality for all commands:
  - CommandBase class with utility methods for config loading, error handling, output formatting
  - Decorator functions for common patterns (@command_error_handler, @config_loader, etc.)
  - Standard_command decorator combining all common functionality
- Added consistent output formatting with support for multiple formats:
  - JSON (default for most commands)
  - Table (for human-readable display)
  - CSV (for data export and integration)
  - YAML (for structured data viewing)
  - HTML (for web-based visualization)
  - Text (for simple output)
- Standardized format support across all CLI commands (object, policy, deduplicate, query, nlq)
- Ensured all commands properly handle the `--format` parameter with consistent options
- Enhanced error handling with improved error messages
- Developed migration tool (cli_command_migrator.py) for automated command conversion
- Updated CLI reference documentation and usage guide
- Created comprehensive test suite for command pattern functionality
- Eliminated duplicated code patterns across command files

## Enhancement Recommendations

PANFlow has strong technical foundations but would benefit from focused enhancements. See the detailed recommendations in these documents:

- [Project Enhancement Recommendations](docs/project_enhancement_recommendations.md)
- [Code Quality Assessment](docs/code_quality_assessment.md)
- [Feature Roadmap](docs/feature_roadmap.md)

### Priority Areas

1. **Security-Focused Features**
   - Security posture assessment framework
   - Policy validation against compliance standards
   - Configuration drift detection

2. **User Experience Improvements**
   - Interactive CLI mode with guided workflows
   - Advanced visualization tools
   - Enhanced output formats

3. **Integration and Extensibility**
   - RESTful API for all functionality
   - Infrastructure as code integration
   - Multi-vendor support (long term)

### Code Quality Focus

- Reduce duplication in criteria matching logic
- Enhance error handling with transactional operations
- Decompose large classes and functions
- Standardize patterns across similar operations

### Testing Improvements

- Increase CLI command test coverage (currently near 0%)
- Add tests for bulk operations and deduplication
- Implement integration tests for end-to-end workflows

### Known Issues

- **CLI Compatibility Issue**: There is a compatibility issue between the command pattern and Typer's type handling. Custom types like PANFlowConfig are not supported by Typer, which prevents direct execution of migrated commands. See [CLI Compatibility Issue](docs/cli_compatibility_issue.md) for details and planned solutions.

### 2024-06 - XML Functionality Consolidation
- Consolidated XML-related modules into a cohesive package: `panflow.core.xml`
- Organized functions and classes into logical submodules:
  - `base.py`: Core XML parsing and utility functions
  - `cache.py`: XML caching functionality
  - `builder.py`: XML construction classes
  - `query.py`: XML query functionality
  - `diff.py`: XML comparison and diffing tools
- Maintained backward compatibility through re-export pattern
- Added deprecation warnings for old module imports
- Created comprehensive tests to ensure functionality remains intact
- Added documentation on migration between old and new import patterns
- Eliminated circular dependencies between XML-related modules
- Implemented CLI command tests to ensure XML consolidation doesn't break functionality

### 2024-05 - Major Query System Integration, Format Standardization, and Device Type Autodetection
- Implemented graph-based query language for PAN-OS XML configurations
- Added `query` command for interactive exploration using graph patterns
- Refactored CLI commands to support `--query-filter` parameter for direct graph queries
- Integrated query filtering with all core commands:
  - `object list`, `object filter`, `object bulk-delete`
  - `policy list`, `policy filter`, `policy bulk-update`
  - `deduplicate merge`, `deduplicate find`, `deduplicate simulate`, `deduplicate report`
- Implemented dynamic RETURN clause handling for queries
- Added documentation and examples for query-driven workflows
- Standardized output format options in all commands:
  - Added consistent format handling for all object commands
  - Added comprehensive format support to policy commands
  - Ensured all CLI commands handle formatting consistently
  - Enhanced help text to show all supported formats
  - Made all commands support table, CSV, YAML, HTML, and JSON formats
- Enhanced device type detection with confidence scoring:
  - Implemented robust auto-detection between Panorama and Firewall configurations
  - Used weighted scoring system for XML structure recognition
  - Added detailed debug logging for detection process
  - Ensured high-confidence results through multiple detection markers

### 2024-04 - Deduplication Engine Enhancement
- Added multi-strategy support to deduplication engine (first, shortest, longest, alphabetical)
- Implemented detailed impact analysis reports for deduplication operations
- Added dry-run option for safe execution of deduplication
- Added pattern filtering and include/exclude list support

### 2024-03 - Config Merge Framework
- Implemented policy and object merging between configurations
- Added support for conflict resolution strategies
- Created object dependency resolution and reference tracking
- Added multi-context merge operations for Panorama configurations

### 2024-02 - Bulk Operations System
- Created bulk update capability for policies
- Implemented criteria-based selection for objects and policies
- Added operations framework for applying changes at scale
- Developed reference integrity checking for bulk operations

### 2024-01 - Core Framework
- Implemented version-aware XPath resolution system
- Created context-aware configuration navigation
- Developed XML manipulation utility functions
- Added logging and error handling framework
- Built initial CLI command structure and application framework