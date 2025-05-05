# PANFlow API Reference

This section provides detailed documentation for the PANFlow API.

## Core Modules

- **[config_loader](config_loader.md)**: Functions for loading and saving PAN-OS XML configurations
- **[xpath_resolver](xpath_resolver.md)**: Version-aware XPath resolution for PAN-OS configurations
- **[xml_utils](xml_utils.md)**: XML manipulation utilities
- **[object_merger](object_merger.md)**: Functions for merging objects between configurations
- **[policy_merger](policy_merger.md)**: Functions for merging policies between configurations
- **[conflict_resolver](conflict_resolver.md)**: Strategies for resolving conflicts during merges
- **[bulk_operations](bulk_operations.md)**: Tools for performing operations on multiple elements
- **[deduplication](deduplication.md)**: Tools for finding and merging duplicate objects

## Functional Modules

- **[objects](objects.md)**: High-level functions for working with PAN-OS objects
- **[policies](policies.md)**: High-level functions for working with PAN-OS policies
- **[groups](groups.md)**: Functions for working with group objects
- **[reports](reports.md)**: Functions for generating reports

## Classes

- **[PANFlowConfig](panflow_config.md)**: Main class for working with PAN-OS configurations
- **[DeduplicationEngine](deduplication_engine.md)**: Engine for finding and merging duplicates
- **[ObjectMerger](object_merger_class.md)**: Class for merging objects between configurations
- **[PolicyMerger](policy_merger_class.md)**: Class for merging policies between configurations
- **[ConflictResolver](conflict_resolver_class.md)**: Class for resolving merge conflicts

## Constants and Enums

- **[ConflictStrategy](conflict_strategy.md)**: Enum defining strategies for conflict resolution

## Exception Types

PANFlow provides a hierarchy of exception types for specific error conditions:

- **PANFlowError**: Base exception for all PANFlow errors
  - **ConfigError**: Base class for configuration-related errors
  - **ValidationError**: Exception raised when validation fails
  - **ParseError**: Exception raised when parsing XML fails
  - **XPathError**: Exception raised when an XPath operation fails
  - **ContextError**: Exception raised when an operation fails due to invalid context
  - **ObjectError**: Base class for object-related errors
    - **ObjectNotFoundError**: Exception raised when an object is not found
    - **ObjectExistsError**: Exception raised when an object already exists but shouldn't
  - **PolicyError**: Base class for policy-related errors
    - **PolicyNotFoundError**: Exception raised when a policy is not found
    - **PolicyExistsError**: Exception raised when a policy already exists but shouldn't
  - **MergeError**: Exception raised when merging objects or policies fails
    - **ConflictError**: Exception raised when there's a conflict during a merge operation
  - **VersionError**: Exception raised when there's a version compatibility issue
  - **FileOperationError**: Exception raised when a file operation fails
  - **BulkOperationError**: Exception raised when a bulk operation fails
  - **SecurityError**: Exception raised for security-related issues