"""
Core package for PANFlow for PAN-OS XML utilities.

This package provides the core functionality for working with PANFlow for PAN-OS XML configurations,
including XML parsing, manipulation, and saving.
"""

# Import from xml_utils.py
from .xml_utils import (
    # XML parsing
    parse_xml,
    
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
    
    # Helper functions
    get_xpath_functions, get_element_manipulation_functions,
    get_conversion_functions,
    
    # Custom exceptions
    XmlError, XmlParseError, XmlXPathError, XmlMergeError
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
    # XML parsing
    'parse_xml',
    
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
    
    # Helper functions
    'get_xpath_functions', 'get_element_manipulation_functions',
    'get_conversion_functions',
    
    # Configuration saving
    'ConfigSaver',
    
    # XPath resolution
    'get_context_xpath', 'get_object_xpath', 'get_policy_xpath',
    'load_xpath_mappings', 'get_all_versions', 'determine_version_from_config',
    
    # Configuration loading
    'load_config_from_file', 'load_config_from_string', 'save_config',
    'xpath_search', 'extract_element_data', 'detect_device_type',
    
    # Exceptions
    'XmlError', 'XmlParseError', 'XmlXPathError', 'XmlMergeError',
    'ConfigSaverError',

    'PolicyMerger',
    'ObjectMerger'
]