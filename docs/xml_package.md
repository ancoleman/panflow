# XML Package Consolidation

This document provides information about the XML package consolidation in PANFlow, including the rationale, structure, and migration guidance for developers.

## Overview

The XML utilities in PANFlow have been consolidated into a dedicated package structure to improve maintainability, reduce code duplication, and provide a more cohesive API for XML operations. The consolidation brings together functionality previously spread across multiple modules:

- `xml_utils.py`: Core XML operations
- `xml_builder.py`: Higher-level XML building abstractions
- `xml_cache.py`: Caching utilities for XML operations
- `xml_diff.py`: XML difference utilities
- `xml_query.py`: Advanced XML querying capabilities

These modules have been reorganized into a package structure that better represents their relationships and dependencies.

## New Package Structure

The consolidated XML utilities are now available in the `panflow.core.xml` package:

- `panflow.core.xml`: Main package with all XML functionality
- `panflow.core.xml.base`: Core XML utilities (parsing, manipulation, etc.)
- `panflow.core.xml.cache`: Caching functionality for XML operations
- `panflow.core.xml.builder`: High-level XML building abstractions
- `panflow.core.xml.diff`: XML difference utilities
- `panflow.core.xml.query`: Advanced XML querying capabilities

## Benefits of Consolidation

The consolidation provides several benefits:

1. **Clearer organization**: The package structure better reflects the relationships between different XML utilities.
2. **Reduced circular dependencies**: The reorganization eliminates circular imports that existed in the old structure.
3. **Improved maintainability**: Related functionality is grouped together, making it easier to understand and maintain.
4. **Enhanced discoverability**: The package structure makes it easier to discover related functionality.
5. **Forward-compatible**: The new structure provides a solid foundation for future enhancements.

## Migration Guide

### For New Code

For new code, you should import directly from the `panflow.core.xml` package:

```python
# Import from the main package
from panflow.core.xml import (
    parse_xml, find_element, XmlNode, XmlBuilder
)

# Or import from specific submodules for more specialized functionality
from panflow.core.xml.diff import XmlDiff
from panflow.core.xml.query import XmlQuery
```

Most common functionality is available directly from the main package, but you can also import from specific submodules if needed.

### For Existing Code

Existing code that imports from the old modules (e.g., `xml_utils`, `xml_builder`) will continue to work through compatibility layers. However, these modules are deprecated and will eventually be removed.

You may see deprecation warnings when importing from the old modules:

```
DeprecationWarning: The panflow.core.xml_utils module is deprecated. Please import from panflow.core.xml instead.
```

### Imports from panflow.core

If your code imports XML utilities from `panflow.core`, those imports will continue to work seamlessly, as the core package has been updated to re-export everything from the new XML package.

```python
# This still works and uses the new implementation
from panflow.core import parse_xml, XmlNode, XmlBuilder
```

## Key Classes and Functions

Here's a summary of the key classes and functions available in the XML package:

### XML Parsing and Manipulation

- `parse_xml`: Parse XML from a file or string
- `parse_xml_string`: Parse XML from a string or bytes
- `find_element`: Find a single element matching an XPath expression
- `find_elements`: Find all elements matching an XPath expression
- `element_exists`: Check if an element exists
- `get_element_text`: Get the text content of an element
- `get_element_attribute`: Get an attribute value from an element
- `create_element`: Create a new XML element
- `set_element_text`: Set the text content of an element
- `delete_element`: Delete elements matching an XPath expression
- `clone_element`: Create a deep copy of an XML element
- `merge_elements`: Merge two XML elements

### XML Abstractions

- `XmlNode`: High-level wrapper for XML elements
- `XmlBuilder`: Builder for creating XML hierarchies
- `XPathBuilder`: Builder for creating XPath expressions
- `XmlQuery`: Query engine for XML data extraction and transformation
- `XmlDiff`: Compare two XML trees and identify differences

### Caching

- `cached_xpath`: Decorator for caching XPath query results
- `clear_xpath_cache`: Clear the XPath result cache
- `invalidate_element_cache`: Invalidate the element cache

## Example: XML Node Usage

Here's an example of using the `XmlNode` class from the new package:

```python
from panflow.core.xml import XmlNode

# Create a node from a string
xml_string = """
<config>
    <settings>
        <option name="test">value</option>
    </settings>
</config>
"""
node = XmlNode.from_string(xml_string)

# Find elements
option = node.find("//option[@name='test']")
print(option.text)  # "value"

# Add a new element
settings = node.find("//settings")
new_option = settings.add_child("option", {"name": "new"}, "new value")

# Convert to string
print(node.to_string())
```

## Example: XML Diff Usage

```python
from panflow.core.xml import XmlNode, XmlDiff

# Create two XML documents
original = XmlNode.from_string("<config><settings><option>old</option></settings></config>")
modified = XmlNode.from_string("<config><settings><option>new</option></settings></config>")

# Compare them
diff = XmlDiff(original.element, modified.element)
diff.compare()

# Get the differences
for change in diff.get_diffs():
    print(f"{change.path}: {change.diff_type.value} - {change.source_value} -> {change.target_value}")
```

## Conclusion

The XML package consolidation improves the organization and maintainability of the PANFlow XML utilities while maintaining backward compatibility for existing code. Developers are encouraged to migrate to the new package structure for new code to benefit from its improved organization and to avoid potential issues when the legacy modules are eventually removed.