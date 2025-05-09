"""
XML package for PANFlow.

This package provides utilities for working with XML in PAN-OS configurations,
including parsing, caching, building, querying, and diffing XML elements.

The package is organized into several modules:
- base: Core XML utilities and functions
- cache: Caching utilities for XPath queries and elements
- builder: Classes for building and manipulating XML
- query: Utilities for querying XML
- diff: Utilities for comparing XML trees

Most common functionality is available from the package directly.
"""

# Import core XML utilities
from .base import (
    parse_xml,
    parse_xml_string,
    find_element,
    find_elements,
    element_exists,
    get_element_text,
    get_element_attribute,
    create_element,
    set_element_text,
    delete_element,
    clone_element,
    merge_elements,
    element_to_dict,
    dict_to_element,
    prettify_xml,
    validate_xml,
    load_xml_file,
    get_xpath_element_value,
    compat_element_to_dict
)

# Import XML builder classes
from .builder import (
    XmlNode,
    XmlBuilder, 
    XPathBuilder
)

# Import XML query class
from .query import XmlQuery

# Import XML diff classes
from .diff import XmlDiff, DiffItem, DiffType

# Import caching utilities
from .cache import (
    cached_xpath,
    clear_xpath_cache,
    invalidate_element_cache,
    LRUCache
)

# Import compatibility with lxml/ElementTree
from .base import HAVE_LXML

# Explicitly define the public API
__all__ = [
    # Base module exports
    'parse_xml',
    'parse_xml_string',
    'find_element',
    'find_elements',
    'element_exists',
    'get_element_text',
    'get_element_attribute',
    'create_element',
    'set_element_text',
    'delete_element',
    'clone_element',
    'merge_elements',
    'element_to_dict',
    'dict_to_element',
    'prettify_xml',
    'validate_xml',
    'load_xml_file',
    'get_xpath_element_value',
    'compat_element_to_dict',
    
    # XML builder exports
    'XmlNode',
    'XmlBuilder',
    'XPathBuilder',
    
    # XML query exports
    'XmlQuery',
    
    # XML diff exports
    'XmlDiff',
    'DiffItem',
    'DiffType',
    
    # Cache exports
    'cached_xpath',
    'clear_xpath_cache',
    'invalidate_element_cache',
    'LRUCache',
    
    # Compatibility exports
    'HAVE_LXML'
]