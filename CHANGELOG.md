# Changelog

All notable changes to the PANFlow project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Enhanced Deduplication Verbose Output (#5)**: Added detailed location information during deduplication
  - New `_format_reference_location()` helper method provides human-readable location descriptions
  - Enhanced logging in `merge_duplicates()` and `merge_hierarchical_duplicates()` methods
  - Shows exactly where object replacements occur (e.g., "Device Group: EDGE-WAN | Address-Group: Private-Subnets")
  - Added comprehensive unit tests for verbose output formatting
  - Created demo script (`examples/deduplication_verbose_demo.py`) showcasing the enhanced output

### Fixed
- **Deduplication NAT Rule References**: Added missing NAT rule source/destination reference checking
  - NAT rules now properly check both regular source/destination fields
  - Ensures all object references are tracked during deduplication
- **Deduplication Unit Tests**: Updated tests to match current implementation
  - Fixed handling of 3-tuple format (name, element, context) in duplicate objects
  - Updated merge methods to work with list of changes instead of dictionary
  - Aligned tests with current method signatures and return values

## [0.4.0] - 2025-06-09

### Added
- **Test Infrastructure Foundation**: Comprehensive test utilities and infrastructure
  - New `tests/common/` module with shared test utilities
  - Factory classes for creating test configurations and objects
  - Base test classes for common functionality
  - Performance benchmarking utilities
  - Duplication analyzer for tracking code reduction
  - Compatibility checker for verifying behavior consistency
- **Enhanced Command Base**: Feature-flagged enhanced command base for future CLI improvements
  - New `EnhancedCommandBase` class with improved output formatting
  - Consistent format handling across all output types
  - Feature flag system for gradual rollout of enhancements
- **Refactoring Documentation**: Comprehensive planning for codebase improvements
  - Detailed refactoring workflow and step-by-step guides
  - Analysis tools for identifying refactoring opportunities
  - Documentation for v0.4.x release series roadmap

### Fixed
- **Stdout Piping Issue (#3)**: Fixed logging output going to stderr instead of stdout
  - Modified `StreamHandler` in `app.py` to explicitly use `sys.stdout`
  - This allows proper piping with tools like `tee` and output redirection
  - All CLI commands now correctly output to stdout for better Unix pipeline compatibility

## [0.3.5] - 2025-05-21

### Added
- **Visualization Implementation Plan**: Comprehensive roadmap for PAN-OS configuration visualization capabilities
  - Business use cases for security compliance, change impact analysis, and troubleshooting
  - Technical architecture with Phase 1-4 implementation plan
  - Integration with existing graph query system for policy flow diagrams and dependency graphs
  - Competitive differentiation through native PAN-OS understanding

### Fixed
- **NLQ HTML Report Formatting**: Resolved issue where NLQ disabled policies queries generated empty HTML reports
  - Added specific template handling for `list_disabled_policies` intent
  - Implemented proper Jinja2 template rendering for disabled security rules
  - Fixed data table generation showing policy name, action, source/destination zones, and status
  - HTML reports now correctly display data while maintaining professional styling

### Enhanced
- **Project Structure Documentation**: Comprehensive update to reflect current codebase state
  - Updated `docs/directory_structure.md` with complete project tree (381 files, 43 directories)
  - Added documentation for template system, CLI infrastructure, and build support
  - Included recent major improvements section highlighting v0.3.3 and v0.3.4 enhancements
  - Synchronized version references across documentation and project files

### Technical Improvements
- Updated pyproject.toml version to match git release tags (0.3.4)
- Enhanced directory structure documentation with accurate module descriptions
- Added comprehensive build and deployment infrastructure documentation
- **Overhauled documentation index**: Complete rewrite of `docs/index.md` with modern structure
  - Added quick start guide with installation and basic usage examples
  - Organized documentation into logical sections (Core, Use Cases, Developer Resources)
  - Added recent major enhancements summary highlighting v0.3.0-v0.3.5 features
  - Enhanced navigation with emojis and clear categorization
  - Added key benefits section showcasing PANFlow's value proposition

## [0.3.4] - 2025-05-21

### Fixed
- Critical graph query system fixes
  - Fixed service port extraction in graph building (was using incorrect XPath patterns)
  - Fixed device group context assignment for all object types (address, service, groups)
  - Fixed security and NAT rule processing in auto-detect mode when context_type is None
  - Fixed query commands to auto-detect device type and pass to graph service
  - Enhanced graph building to properly handle Panorama configurations without specific context

### Enhanced
- Graph query functionality now works correctly with comprehensive test configurations
  - Service queries by port number now return accurate results
  - Device group context information is properly populated in all node types
  - Security and NAT rules are correctly processed across all device groups
  - Query commands automatically detect Panorama vs firewall configurations

### Technical Improvements
- Improved XPath resolution for service protocol extraction (tcp/udp ports)
- Added `_get_device_group_from_element()` helper method for context detection
- Enhanced graph building logic to process all device groups when context_type is None
- Added device type auto-detection to query execute and interactive commands

## [0.3.3] - 2025-05-20

### Added
- Major reporting system enhancements
  - Implemented template-based HTML report generation system
  - Created reusable components for consistent report styling
  - Added CSS-based styling separate from Python code
  - Enhanced UI with responsive design for better mobile/tablet viewing
  
### Changed
- Completely refactored HTML output generation
  - Moved all inline HTML generation to Jinja2 templates
  - Created separate template files for different report types
  - Added proper template inheritance for consistent look and feel
  - Improved HTML structure with semantic elements and better organization

### Enhanced
- Extended context awareness in NLQ duplicate objects reporting
  - Added context tracking for duplicate objects detection
  - Preserved context through NLQ processing pipeline
  - Enhanced HTML, CSV, and JSON outputs to show object context
  - Implemented consistent context formatting across all output formats
- Improved duplicate objects visualization
  - Objects with the same values are now grouped together
  - Added value headers with object counts for each group
  - Enhanced visual presentation with card-like UI for each group
  - Improved table output with per-value grouping and context information

## [0.3.2] - 2025-05-20

### Added
- Added `--report-file` parameter to NLQ commands to separate configuration output and report output
  - Allows saving reports (in various formats) separate from modified configurations
  - Supported in all NLQ output formats (JSON, CSV, YAML, HTML, table, text)
  - Added documentation and examples in help text
  - Compatible with existing `--output` parameter for configuration changes

### Fixed
- Improved HTML output formatting for NLQ commands
  - Fixed duplication of info fields in report headers 
  - Enhanced display of unused objects with proper table formatting
  - Improved formatting of NLQ results with nested tables instead of raw JSON
  - Better organization of data in HTML reports
- Fixed CSV output handling to properly close files and display appropriate messages
- Enhanced intent recognition for "show me unused address objects" query
- Added context information (Shared/Device Group) to object reports in all formats (HTML, Text, Table, CSV, YAML)
  - Added context display to HTML tables with a dedicated column
  - Added context information to text output for each object
  - Added context column to table format for better visibility
  - Added context column to CSV output for data export capabilities
  - Preserved context metadata in YAML format for programmatic access

## [0.3.1] - 2025-05-22

### Fixed
- Fixed bulk update policies with device group context and query filter
  - Enhanced the _get_policies_from_query method in bulk_operations.py to properly handle device group context
  - Added direct XML lookup fallback for finding policies when graph queries fail
  - Implemented graph reuse to avoid building the same graph multiple times
  - Added comprehensive test suite for device group context with queries
  - Fixed query modification to correctly filter by device group
  - Added support for both pre-rulebase and post-rulebase security rules

## [0.3.0] - 2025-05-12

### Added
- Update project to Python 3.12+ compatibility
- Add networkx dependency for graph-based operations
- Implement bulk update operations in NLQ module for policies
  - Support for adding tags to policies via natural language
  - Support for enabling/disabling policies via natural language
  - Support for changing policy actions via natural language
  - Support for enabling/disabling logging for policies via natural language
  - Support for all output formats (table, JSON, CSV, YAML, HTML, text)
  - Context-aware operations for multiple policy types
  - Support for both Firewall and Panorama configurations

### Fixed
- Fix critical issue with NLQ deduplication not actually removing duplicate objects
- Implement proper XML modification for object deduplication in NLQ commands
- Add support for deduplicating multiple object types simultaneously ("all objects")
- Fix type inference for object and policy types to properly handle "all" qualifier
- Add 'table' format to supported output formats for query commands
- Standardize output format options in commands that support formatting (query and nlq)
- Add comprehensive format support for object_commands.py (json, table, text, csv, yaml, html)
- Add comprehensive format support for policy_commands.py (json, table, text, csv, yaml, html)
- Implement complete format support for NLQ commands (json, table, text, csv, yaml, html)
- Improve NLQ duplicate objects display in table format
- Fix bulk operations to correctly handle shared policies in Panorama
- Fix entity extraction to properly prioritize specific operations
- Add clearer user feedback for NLQ cleanup operations when no output file is provided
- Ensure consistent format handling across all command types
- Implement object type inference for NLQ "find all duplicated objects" to check multiple object types
- Add special handling for multi-type duplicate object results in HTML, table, and text formats
- Enhance entity extraction for "all objects" queries in NLQ processor
- Fix missing duplicate objects in HTML output format for NLQ commands
- Improve styling and organization of HTML tables for better data presentation
- Add policy type inference for NLQ "show all disabled policy" to check multiple policy types
- Add support for "show all policy" to display policies of all types (security, NAT, pre-rules, post-rules)
- Enhance policy table display to show more details including action and source/destination
- Implement special handling for "all" policy types with a dedicated policy type column in table format
- Add policy details to table and text display when returning disabled policies
- Improve entity extractor to detect "all" references in both object and policy queries
- Fix error handling when listing all policy types to gracefully handle unsupported types

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
  - Removed tools directory with migration utilities
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

[Unreleased]: https://github.com/ancoleman/panflow/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/ancoleman/panflow/compare/v0.3.5...v0.4.0
[0.3.5]: https://github.com/ancoleman/panflow/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/ancoleman/panflow/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/ancoleman/panflow/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/ancoleman/panflow/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/ancoleman/panflow/compare/v0.3.0...v0.3.1
[0.2.2]: https://github.com/ancoleman/panflow/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ancoleman/panflow/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ancoleman/panflow/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/ancoleman/panflow/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/ancoleman/panflow/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/ancoleman/panflow/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ancoleman/panflow/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ancoleman/panflow/releases/tag/v0.1.0