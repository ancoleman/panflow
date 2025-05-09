# Package Consolidation Migration Guide

This guide explains the changes made to consolidate functionality in PANFlow and how to migrate your code to use the new package structure.

## Overview

As part of our ongoing efforts to improve code organization and maintainability, we've consolidated several related functionalities into dedicated packages:

1. **XML Functionality Consolidation**: Combined XML-related modules into `panflow.core.xml`
2. **Reporting Functionality Consolidation**: Consolidated reporting modules into `panflow.reporting`

These changes improve the organization and maintainability of the codebase while maintaining backward compatibility.

## Deprecation Policy

All original modules have been preserved as compatibility wrappers that re-export functionality from the new packages. These wrappers emit deprecation warnings to encourage migration to the new structure.

Deprecated modules will be maintained for at least two major versions to allow time for migration, after which they may be removed.

## XML Functionality Migration

### Old Import Pattern

```python
# Importing individual XML utilities
from panflow.core.xml_utils import create_element, get_element_text
from panflow.core.xml_builder import XMLBuilder
from panflow.core.xml_cache import XMLCache
from panflow.core.xml_query import XMLQuery
from panflow.core.xml_diff import compare_xml
```

### New Import Pattern

```python
# Using the consolidated package
from panflow.core.xml.base import create_element, get_element_text
from panflow.core.xml.builder import XMLBuilder
from panflow.core.xml.cache import XMLCache
from panflow.core.xml.query import XMLQuery
from panflow.core.xml.diff import compare_xml
```

## Reporting Functionality Migration

### Old Import Pattern

```python
# Importing reporting functions and classes
from panflow.modules.reports import generate_unused_objects_report, generate_duplicate_objects_report
from panflow.core.reporting import EnhancedReportingEngine
```

### New Import Pattern

```python
# Using the consolidated reporting package
from panflow.reporting import ReportingEngine
from panflow.reporting.reports.unused_objects import generate_unused_objects_report_data
from panflow.reporting.reports.duplicate_objects import generate_duplicate_objects_report_data
from panflow.reporting.reports.policy_analysis import generate_security_policy_analysis_data
```

## Detailed Module Mappings

### XML Module Mapping

| Old Module | New Module | Notable Functionality |
|------------|------------|----------------------|
| `panflow.core.xml_utils` | `panflow.core.xml.base` | Core XML utilities like `create_element`, `get_element_text` |
| `panflow.core.xml_builder` | `panflow.core.xml.builder` | `XMLBuilder` class for programmatic XML generation |
| `panflow.core.xml_cache` | `panflow.core.xml.cache` | `XMLCache` for caching XML operations |
| `panflow.core.xml_query` | `panflow.core.xml.query` | `XMLQuery` for structured XML queries |
| `panflow.core.xml_diff` | `panflow.core.xml.diff` | Diff functions like `compare_xml`, `diff_trees` |

### Reporting Module Mapping

| Old Module | New Module | Notable Functionality |
|------------|------------|----------------------|
| `panflow.modules.reports` | `panflow.reporting.reports.*` | Individual report generators |
| `panflow.core.reporting` | `panflow.reporting.engine` | `ReportingEngine` (formerly `EnhancedReportingEngine`) |

## Output Formatters

The reporting package now includes dedicated formatters for different output formats:

```python
from panflow.reporting.formatters.html import HTMLFormatter
from panflow.reporting.formatters.json import JSONFormatter
from panflow.reporting.formatters.csv import CSVFormatter
```

## Benefits of the New Structure

1. **Better Organization**: Related functionality is grouped together logically
2. **Reduced Circular Dependencies**: Package boundaries prevent circular imports
3. **Easier Maintenance**: Changes to one aspect (e.g., formatters) don't require changes to other components
4. **Clearer API**: The new structure makes it clearer what functionality belongs together

## Handling Deprecation Warnings

You may see deprecation warnings when using the old import paths. These are harmless but indicate that you should update your code to use the new import paths:

```
DeprecationWarning: The module panflow.core.xml_utils is deprecated and will be removed in a future version. Please use panflow.core.xml.base instead.
```

To update your code, simply follow the migration paths described above.

## Timeline

- **Current Version**: Deprecated modules emit warnings but continue to work
- **Next Major Version**: Deprecated modules still available but may emit stronger warnings
- **Future Major Version**: Deprecated modules may be removed