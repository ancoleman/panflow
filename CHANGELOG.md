# Changelog

All notable changes to the PANFlow project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Ongoing development and improvements

## [0.1.3] - 2025-05-06

### Added
- Hierarchical deduplication commands for Panorama device groups
  - New `deduplicate hierarchical find` command to identify duplicates across the device group hierarchy
  - New `deduplicate hierarchical merge` command to merge duplicates with prioritization for parent contexts
  - Support for prioritizing objects in higher-level contexts (shared or parent device groups)
  - Impact reporting and dry-run capabilities for safe operation

### Fixed
- Resolved object type naming inconsistencies in deduplication engine (address-group vs address_group)
- Fixed reference tracking in deduplication to correctly identify object usage across the configuration

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

### Changed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

[Unreleased]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.3...HEAD
[0.1.3]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.2...v0.1.3
[0.1.2]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.1...v0.1.2
[0.1.1]: https://code.pan.run/gcs-automation/panflow/compare/v0.1.0...v0.1.1
[0.1.0]: https://code.pan.run/gcs-automation/panflow/releases/tag/v0.1.0