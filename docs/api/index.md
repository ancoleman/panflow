# PANFlow API Reference

This section provides detailed documentation for the PANFlow API.

## Core Modules

- **config_loader**: Functions for loading and saving PAN-OS XML configurations
- **xpath_resolver**: Version-aware XPath resolution for PAN-OS configurations
- **[object_merger](../object_merger.md)**: Functions for merging objects between configurations
- **policy_merger**: Functions for merging policies between configurations
- **conflict_resolver**: Strategies for resolving conflicts during merges
- **[bulk_operations](../bulk_policy_ops.md)**: Tools for performing operations on multiple elements
- **[deduplication](../deduplication.md)**: Tools for finding and merging duplicate objects
- **[xml_abstractions](xml_abstractions.md)**: High-level abstractions for working with XML

## XML Package

The XML utilities in PANFlow have been consolidated into a dedicated package structure to improve maintainability, reduce code duplication, and provide a more cohesive API for XML operations:

- **[xml_package](../xml_package.md)**: Overview of the XML package consolidation
- **`panflow.core.xml`**: Main package with all XML functionality
- **`panflow.core.xml.base`**: Core XML utilities (parsing, manipulation, etc.)
- **`panflow.core.xml.builder`**: High-level XML building abstractions
- **`panflow.core.xml.cache`**: Caching functionality for XML operations
- **`panflow.core.xml.diff`**: XML difference utilities
- **`panflow.core.xml.query`**: Advanced XML querying capabilities

## Functional Modules

- **objects**: High-level functions for working with PAN-OS objects
- **[policies](../policy_bulk_update_capabilities.md)**: High-level functions for working with PAN-OS policies
- **groups**: Functions for working with group objects
- **reports**: Functions for generating reports

## Classes

### Core Classes

- **PANFlowConfig**: Main class for working with PAN-OS configurations
- **[DeduplicationEngine](../deduplication.md#api)**: Engine for finding and merging duplicates
- **[ObjectMerger](../object_merger.md#objectmerger-class)**: Class for merging objects between configurations
- **PolicyMerger**: Class for merging policies between configurations
- **ConflictResolver**: Class for resolving merge conflicts

### XML-Specific Classes

- **[XmlNode](xml_abstractions.md#xmlnode)**: High-level wrapper for XML elements
- **[XmlBuilder](xml_abstractions.md#xmlbuilder)**: Builder for creating XML hierarchies
- **[XPathBuilder](xml_abstractions.md#xpathbuilder)**: Builder for creating XPath expressions
- **[XmlQuery](xml_abstractions.md#xmlquery)**: Query engine for XML data extraction
- **[XmlDiff](xml_abstractions.md#xmldiff)**: Compare two XML trees and identify differences

## Constants and Enums

- **ConflictStrategy**: Enum defining strategies for conflict resolution
- **[DiffType](xml_abstractions.md#xmldiff)**: Enum defining types of XML differences (ADDED, REMOVED, CHANGED)

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