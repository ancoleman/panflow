# Changelog

All notable changes to the PANFlow project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Ongoing development and improvements

## [0.2.2] - 2025-05-12

### Added
- CLI Command Pattern Abstraction
  - New CommandBase class for standardizing command implementation
  - Decorator functions for common patterns (error handling, config loading, etc.)
  - Standardized output formatting with support for JSON, Table, CSV, YAML, and more
  - Improved error handling with consistent error messages
  - Parameter injection with clear type annotations
  - Comprehensive test suite for command pattern functionality
  - Detailed migration guide for manual conversions
  - **Docs:** [docs/cli_command_pattern.md](docs/cli_command_pattern.md), [docs/cli_command_migration.md](docs/cli_command_migration.md)
  - **Example:** [panflow/cli/commands/object_commands_refactored.py](panflow/cli/commands/object_commands_refactored.py)
  - **Tests:** [tests/unit/cli/test_command_pattern.py](tests/unit/cli/test_command_pattern.py), [tests/unit/cli/test_command_migration.py](tests/unit/cli/test_command_migration.py)
- Enhanced NLQ Module with Deduplication Support
  - Added duplicate object detection in natural language queries
  - Implemented "cleanup_duplicate_objects" intent with pattern matching
  - Added command mapping for deduplication operations
  - Created formatting utilities for consistently displaying objects
  - Enhanced documentation for deduplication features
  - **Updated Files:** [entity_extractor.py](panflow/nlq/entity_extractor.py), [intent_parser.py](panflow/nlq/intent_parser.py), [command_mapper.py](panflow/nlq/command_mapper.py), [processor.py](panflow/nlq/processor.py)
  - **Docs:** [docs/nlq.md](docs/nlq.md), [docs/deduplication.md](docs/deduplication.md)
- Consistent Object and Policy Formatting
  - Added common formatting utilities in [common.py](panflow/cli/common.py)
  - Standardized output display across CLI commands and NLQ
  - Improved user experience with clear, readable formatting
  - Enhanced documentation for bulk operations
  - Added examples for log forwarding profile operations
  - **Examples:** [examples/policy_cli_usage_examples.md](examples/policy_cli_usage_examples.md)

### Removed
- CLI Command Migration Tools
  - Removed cli_migrate.py script used for automated command migration
  - Removed migrated directory with experimental implementations
  - These files were transitional during the command pattern migration

## [0.2.1] - 2025-05-09

### Added
- Shell completion support for CLI commands
  - Added `completion` command for displaying and installing shell completions
  - Support for Bash, Zsh, and Fish shells
  - Auto-completion for common parameters (file paths, object types, policy types)
  - Dynamic completion for context-aware parameters
  - Updated documentation with installation and usage instructions
  - **Docs:** [CLI_USAGE.md#shell-completion](CLI_USAGE.md#shell-completion)

## [0.2.0] - 2025-05-09

### Added
- Natural Language Query (NLQ) functionality
  - New `nlq` command for processing natural language queries and commands
  - Entity extraction for identifying objects, policies, and actions in natural language
  - Intent parsing to identify user's intentions from natural language
  - Command mapping to translate natural language to CLI commands
  - Optional AI integration for enhanced understanding of complex queries
  - Unit tests for NLQ components
  - **Docs:** [docs/nlq.md](docs/nlq.md)
  - **CLI Reference:** [CLI_USAGE.md#nlq-commands](CLI_USAGE.md#nlq-commands)

- XML functionality consolidation into `panflow.core.xml` package
  - New organized package structure with better separation of concerns
  - Dedicated modules: `base.py`, `builder.py`, `cache.py`, `query.py`, and `diff.py`
  - Backward compatibility through re-export pattern
  - Deprecation warnings for old module imports
  - Migration guide with clear examples
  - Unit tests for the consolidated package structure
  - **Docs:** [docs/xml_package.md](docs/xml_package.md)
  - **Migration Guide:** [docs/package_consolidation_guide.md](docs/package_consolidation_guide.md)

- Reporting functionality consolidation into `panflow.reporting` package
  - New package structure with clear separation between generation and formatting
  - Formatters for different output types (HTML, JSON, CSV) in `formatters/` subpackage
  - Report generators in `reports/` subpackage
  - New `ReportingEngine` class that supersedes `EnhancedReportingEngine`
  - Consistent parameter handling with improved validation
  - Backward compatibility through re-export pattern
  - Deprecation warnings for old module imports
  - **Docs:** [docs/reporting_consolidation.md](docs/reporting_consolidation.md)
  - **Migration Guide:** [docs/package_consolidation_guide.md](docs/package_consolidation_guide.md)

### Changed
- Updated project structure for better modularity and maintainability
  - Reorganized CLI commands for better categorization
  - Enhanced documentation organization
  - **Docs:** [docs/directory_structure.md](docs/directory_structure.md)
- Improved parameter handling in reporting functions
  - Explicit keyword arguments instead of positional arguments
  - Proper validation of parameters like object_type
  - Consistent forwarding of context parameters
  - **Docs:** [docs/reporting_consolidation.md#parameter-handling](docs/reporting_consolidation.md#parameter-handling)
- Added consolidated package migration guide
  - **Docs:** [docs/package_consolidation_guide.md](docs/package_consolidation_guide.md)
- All XML utility imports should now use `panflow.core.xml.*` instead of individual `panflow.core.xml_*` modules
  - **Docs:** [docs/xml_package.md#migration-guide](docs/xml_package.md#migration-guide)
- All reporting functionality imports should now use `panflow.reporting.*` instead of `panflow.modules.reports` or `panflow.core.reporting`
  - **Docs:** [docs/reporting_consolidation.md#backward-compatibility](docs/reporting_consolidation.md#backward-compatibility)
- Updated graph query language documentation
  - **Docs:** [docs/graph_query_language.md](docs/graph_query_language.md), [docs/graph_query_reference.md](docs/graph_query_reference.md)

### Fixed
- Fixed parameter handling in ReportingEngine to correctly process object_type
- Resolved circular dependencies between XML-related modules
- Fixed issues with device_type handling in cleanup_commands.py
- Improved error handling for edge cases in report generation
- Enhanced query syntax documentation to prevent common usage errors

## [0.1.4] - 2025-05-07

### Added
- Cleanup commands for configuration maintenance
  - New `cleanup unused-objects` command to identify and remove unused objects
  - New `cleanup disabled-policies` command to identify and remove disabled policies
  - Support for dry-run mode to preview changes before applying them
  - Report generation for cleanup operations
  - Exclusion list functionality via JSON files
  - Enhanced documentation explaining cleanup detection algorithms
  - Examples for various cleanup workflows
  - **Docs:** [docs/cleanup_detection.md](docs/cleanup_detection.md)
  - **Examples:** [examples/cleanup_examples.md](examples/cleanup_examples.md)
  - **CLI Reference:** [CLI_USAGE.md#cleanup-commands](CLI_USAGE.md#cleanup-commands)
- Enhanced service object support
  - Improved detection of service object usage in policies
  - Added support for service-translation fields in NAT rules
  - Added protocol-specific field checking for service objects
  - Added QoS policy checking for service object references
  - **CLI Reference:** [CLI_USAGE.md#object-commands](CLI_USAGE.md#object-commands)

### Fixed
- Fixed handling of object type naming inconsistencies for address-groups and service-groups
- Enhanced NAT rule parsing to correctly identify service object usage
- Improved policy detection for Panorama pre-rules and post-rules
- Fixed field processing for complex nested fields in policies

## [0.1.3] - 2025-05-06

### Added
- Hierarchical deduplication commands for Panorama device groups
  - New `deduplicate hierarchical find` command to identify duplicates across the device group hierarchy
  - New `deduplicate hierarchical merge` command to merge duplicates with prioritization for parent contexts
  - Support for prioritizing objects in higher-level contexts (shared or parent device groups)
  - Impact reporting and dry-run capabilities for safe operation
  - **Docs:** [docs/deduplication.md](docs/deduplication.md)
  - **CLI Reference:** [CLI_USAGE.md#deduplication](CLI_USAGE.md#deduplication)
- NAT splitting functionality
  - Added support for splitting NAT rules with multiple source/destination addresses
  - New `nat split` command to convert complex NAT rules into simpler individual rules
  - Preservation of rule metadata and attributes during splitting
  - **CLI Reference:** [CLI_USAGE.md#nat-splitting](CLI_USAGE.md#nat-splitting)
- Policy bulk operations
  - Enhanced batch processing capabilities for security and NAT policies
  - Documentation of bulk policy operations and capabilities
  - Examples for policy rename and other bulk operations
  - **Docs:** [docs/policy_bulk_update_capabilities.md](docs/policy_bulk_update_capabilities.md)
  - **Examples:** [examples/policy_rename_examples.md](examples/policy_rename_examples.md)
  - **CLI Reference:** [CLI_USAGE.md#bulk-operations](CLI_USAGE.md#bulk-operations)

### Fixed
- Resolved object type naming inconsistencies in deduplication engine (address-group vs address_group)
- Fixed reference tracking in deduplication to correctly identify object usage across the configuration
- Enhanced XPath mappings for better object resolution across PAN-OS versions

## [0.1.2] - 2025-05-06

### Fixed
- Corrected inconsistent object type names in object_finder.py
- Removed non-existent object types from default search list
- Eliminated warning messages during object search operations

## [0.1.1] - 2025-05-06

### Added
- Performance optimization to only search for specified object types in find-duplicates

### Fixed
- Fixed XPath query construction in object_finder that prevented find-duplicates from working properly
- Removed extraneous warnings when searching for specific object types

## [0.1.0] - 2025-05-06

### Added
- Initial release of PANFlow
- Core functionality for working with PAN-OS XML configurations
- Version-aware XPath resolution supporting PAN-OS 10.1, 10.2, and 11.2
- Context-aware operations (shared, device groups, templates, vsys)
- Object management (address, service, etc.)
- Policy management (security rules, NAT rules)
- Report generation (unused objects, duplicates, rule coverage)
- Bulk operations for configuration modifications
- Deduplication engine for finding and merging duplicate objects
- Graph-based query language for querying configurations
- Command-line interface with comprehensive commands
- GraphService implementation for centralized graph operations
- Unit tests for core functionality
- Documentation including README, CLI usage guide, and API docs
- Build system for creating standalone binaries for all platforms
- Poetry-based package management
- **Overview:** [README.md](README.md)
- **CLI Usage:** [CLI_USAGE.md](CLI_USAGE.md)
- **Getting Started:** [docs/getting_started.md](docs/getting_started.md)
- **API Docs:** [docs/api/index.md](docs/api/index.md)

### Changed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

[Unreleased]: https://code.pan.run/gcs-automation/panflow/compare/v0.2.2...HEAD
[0.2.2]: https://code.pan.run/gcs-automation/panflow/compare/v0.2.1...v0.2.2
[0.2.1]: https://code.pan.run/gcs-automation/panflow/compare/v0.2.0...v0.2.1
[0.2.0]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.4...v0.2.0
[0.1.4]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.3...v0.1.4
[0.1.3]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.2...v0.1.3
[0.1.2]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.1...v0.1.2
[0.1.1]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.0...v0.1.1
[0.1.0]: https://code.pan.run/gcs-automation/panflow/releases/tag/v0.1.0