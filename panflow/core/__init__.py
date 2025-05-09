"""
Core package for PANFlow for PAN-OS XML utilities.

This package provides the core functionality for working with PANFlow for PAN-OS XML configurations,
including XML parsing, manipulation, saving, and enhanced XML abstractions.

XML Utility Consolidation (2023):
The XML utilities have been consolidated into a dedicated package structure:
- panflow.core.xml: Main package with all XML functionality
- panflow.core.xml.base: Core XML utilities (parsing, manipulation, etc.)
- panflow.core.xml.cache: Caching functionality for XML operations
- panflow.core.xml.builder: High-level XML building abstractions
- panflow.core.xml.diff: XML difference utilities
- panflow.core.xml.query: Advanced XML querying capabilities

Legacy modules (panflow.core.xml_utils, xml_builder, etc.) are maintained for
backward compatibility but will emit deprecation warnings. New code should
import directly from panflow.core.xml.
"""

# Import the xml package
from . import xml

# Import XML utilities for backward compatibility but using the new package
from .xml import (
    # Classes
    XmlNode, XmlBuilder, XPathBuilder, XmlQuery, XmlDiff, DiffItem, DiffType,
    
    # XML parsing
    parse_xml, parse_xml_string,
    
    # XPath operations
    find_elements, find_element, element_exists,
    get_element_text, get_element_attribute,
    
    # Element manipulation
    create_element, set_element_text, delete_element,
    clone_element, merge_elements,
    
    # Conversion functions
    element_to_dict, dict_to_element, prettify_xml,
    
    # Validation
    validate_xml,
    
    # Caching
    cached_xpath, clear_xpath_cache, invalidate_element_cache,
    
    # Utility functions
    load_xml_file, get_xpath_element_value,
    
    # Constants
    HAVE_LXML
)

# Import from exceptions.py
from .exceptions import (
    PANFlowError, ParseError, XPathError, MergeError, ValidationError, CacheError, DiffError, QueryError,
    FileOperationError, SecurityError
)

# Import from config_saver.py
from .config_saver import (
    ConfigSaver, ConfigSaverError
)

# Import from xpath_resolver.py
from .xpath_resolver import (
    get_context_xpath, get_object_xpath, get_policy_xpath,
    load_xpath_mappings, get_all_versions, determine_version_from_config
)

# Import from config_loader.py
from .config_loader import (
    load_config_from_file, load_config_from_string, save_config,
    xpath_search, extract_element_data, detect_device_type
)

from .policy_merger import (
    PolicyMerger
)

from .object_merger import (
    ObjectMerger
)

# Define the public API
__all__ = [
    # XML package
    'xml',
    
    # Enhanced XML abstractions
    'XmlNode', 'XmlBuilder', 'XPathBuilder', 'XmlQuery', 'XmlDiff', 'DiffItem', 'DiffType',
    
    # XML parsing
    'parse_xml', 'parse_xml_string',
    
    # XPath operations
    'find_elements', 'find_element', 'element_exists',
    'get_element_text', 'get_element_attribute',
    
    # Element manipulation
    'create_element', 'set_element_text', 'delete_element',
    'clone_element', 'merge_elements',
    
    # Conversion functions
    'element_to_dict', 'dict_to_element', 'prettify_xml',
    
    # Validation
    'validate_xml',
    
    # Caching
    'cached_xpath', 'clear_xpath_cache', 'invalidate_element_cache',
    
    # Utility functions
    'load_xml_file', 'get_xpath_element_value', 'HAVE_LXML',
    
    # Configuration saving
    'ConfigSaver',
    
    # XPath resolution
    'get_context_xpath', 'get_object_xpath', 'get_policy_xpath',
    'load_xpath_mappings', 'get_all_versions', 'determine_version_from_config',
    
    # Configuration loading
    'load_config_from_file', 'load_config_from_string', 'save_config',
    'xpath_search', 'extract_element_data', 'detect_device_type',
    
    # Exceptions
    'PANFlowError', 'ParseError', 'XPathError', 'MergeError', 'ValidationError', 'CacheError',
    'ConfigSaverError', 'DiffError', 'QueryError', 'FileOperationError', 'SecurityError',

    # Merger classes
    'PolicyMerger',
    'ObjectMerger'
]