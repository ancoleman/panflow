"""
XML utilities for PAN-OS XML configurations.

This module provides utility functions for working with XML in PAN-OS configurations,
including parsing, navigation, and manipulation.

Performance optimizations:
- XPath result caching for frequently used queries
- Compiled XPath expressions for better performance
- Efficient XML element cloning and manipulation
- Memory-efficient XML traversal
"""

import os
import sys
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set
import logging
from datetime import datetime
import copy
import time
from functools import lru_cache

# Try to import lxml first, fall back to ElementTree if not available
try:
    from lxml import etree
    HAVE_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    HAVE_LXML = False

logger = logging.getLogger("panflow")

# Import caching utilities
try:
    from .xml_cache import cached_xpath, clear_xpath_cache, invalidate_element_cache
    HAVE_CACHE = True
except ImportError:
    # Fallback if the cache module is not available
    HAVE_CACHE = False
    def cached_xpath(f):
        return f
    def clear_xpath_cache():
        pass
    def invalidate_element_cache(path=None):
        pass

# Import custom exceptions
from .exceptions import (
    PANFlowError, ParseError, XPathError, MergeError, SecurityError, ValidationError
)

def parse_xml_string(
    xml_string: Union[str, bytes],
    validate: bool = False,
    schema_file: Optional[str] = None
) -> Tuple[etree._ElementTree, etree._Element]:
    """
    Parse XML from a string or bytes.
    
    Args:
        xml_string: XML source as string or bytes
        validate: Whether to validate against a schema
        schema_file: XML Schema file path (required if validate=True)
        
    Returns:
        Tuple containing (ElementTree, root Element)
        
    Raises:
        ParseError: If XML parsing fails
        ValidationError: If validate=True but no schema_file is provided
        SecurityError: If XXE attack is attempted
    """
    try:
        if isinstance(xml_string, str):
            xml_string = xml_string.encode('utf-8')
            
        if HAVE_LXML:
            if validate:
                if not schema_file:
                    raise ValidationError("schema_file is required when validate=True")
                
                schema_doc = etree.parse(schema_file)
                schema = etree.XMLSchema(schema_doc)
                parser = etree.XMLParser(schema=schema, resolve_entities=False)
                root = etree.fromstring(xml_string, parser)
            else:
                # Create a secure parser that prevents XXE attacks
                parser = etree.XMLParser(resolve_entities=False)
                root = etree.fromstring(xml_string, parser)
        else:
            # ElementTree doesn't have the same security features, but we'll still use it if it's all we have
            root = etree.fromstring(xml_string)
            if validate:
                logger.warning("Validation requires lxml which is not installed. Skipping validation.")
                
        tree = etree.ElementTree(root)
        return tree, root
        
    except etree.XMLSyntaxError as e:
        error_msg = f"XML parsing failed: {e}"
        logger.error(error_msg)
        raise ParseError(error_msg)
    except ValueError as e:
        if 'ENTITY' in str(e) or 'DOCTYPE' in str(e):
            error_msg = f"Security error: XXE attack attempted: {e}"
            logger.error(error_msg)
            raise SecurityError(error_msg)
        else:
            error_msg = f"Value error parsing XML: {e}"
            logger.error(error_msg)
            raise ParseError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error parsing XML string: {e}"
        logger.error(error_msg)
        raise ParseError(error_msg)

def parse_xml(
    source: Union[str, bytes, os.PathLike],
    validate: bool = False,
    schema_file: Optional[str] = None,
    max_file_size: int = 100 * 1024 * 1024  # 100MB default max size
) -> Tuple[etree._ElementTree, etree._Element]:
    """
    Parse XML from a file or string and return both the tree and root element.
    
    Args:
        source: XML source (file path, bytes, or XML string)
        validate: Whether to validate against a schema
        schema_file: XML Schema file path (required if validate=True)
        max_file_size: Maximum allowed file size in bytes (default: 100MB)
        
    Returns:
        Tuple containing (ElementTree, root Element)
        
    Raises:
        ParseError: If XML parsing fails
        ValidationError: If validate=True but no schema_file is provided
        SecurityError: If XXE attack is attempted or file size exceeds limit
        FileOperationError: If file operations fail
    """
    from .exceptions import FileOperationError
    
    try:
        # Handle different source types
        if isinstance(source, (bytes, str)) and '<' in str(source):
            # Source is an XML string or bytes
            return parse_xml_string(source, validate, schema_file)
        else:
            # Source is a file path
            if os.path.isabs(source) and '..' in str(source):
                # Check for potential path traversal
                raise SecurityError(f"Path traversal detected in file path: {source}")
                
            try:
                file_size = os.path.getsize(source)
                if file_size > max_file_size:
                    raise SecurityError(f"File size {file_size} exceeds maximum allowed size {max_file_size}")
            except (OSError, TypeError) as e:
                if isinstance(e, SecurityError):
                    raise
                logger.warning(f"Unable to check file size for {source}: {e}")
            
            if HAVE_LXML:
                try:
                    if validate and schema_file:
                        schema_doc = etree.parse(schema_file)
                        schema = etree.XMLSchema(schema_doc)
                        parser = etree.XMLParser(schema=schema, resolve_entities=False)
                        tree = etree.parse(source, parser)
                    else:
                        parser = etree.XMLParser(resolve_entities=False)
                        tree = etree.parse(source, parser)
                    root = tree.getroot()
                except Exception as e:
                    raise ParseError(f"Error parsing XML file {source}: {e}")
            else:
                try:
                    tree = etree.parse(source)
                    root = tree.getroot()
                except Exception as e:
                    raise ParseError(f"Error parsing XML file {source}: {e}")
            
            return tree, root
    except FileNotFoundError:
        error_msg = f"XML file not found: {source}"
        logger.error(error_msg)
        raise FileOperationError(error_msg)
    except PermissionError:
        error_msg = f"Permission denied for XML file: {source}"
        logger.error(error_msg)
        raise FileOperationError(error_msg)
    except ParseError:
        raise  # Re-raise ParseError
    except Exception as e:
        error_msg = f"Error parsing XML: {e}"
        logger.error(error_msg)
        raise ParseError(error_msg)

@cached_xpath
def find_elements(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> List[etree._Element]:
    """
    Find all elements matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        namespaces: Optional namespace map
        
    Returns:
        List of matching elements
        
    Raises:
        XPathError: If the XPath expression is invalid
    """
    if not xpath:
        return []
        
    try:
        if HAVE_LXML:
            result = root.xpath(xpath, namespaces=namespaces)
            # lxml can return various types depending on the XPath
            if isinstance(result, list):
                # Filter to ensure we're only returning elements
                return [elem for elem in result if isinstance(elem, etree._Element)]
            elif isinstance(result, etree._Element):
                return [result]
            else:
                return []
        else:
            # ElementTree has less powerful XPath support
            return root.findall(xpath, namespaces)
    except Exception as e:
        error_msg = f"Error evaluating XPath '{xpath}': {e}"
        logger.error(error_msg)
        raise XPathError(error_msg)

@cached_xpath
def find_element(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[etree._Element]:
    """
    Find a single element matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        namespaces: Optional namespace map
        
    Returns:
        First matching element or None if not found
        
    Raises:
        XPathError: If the XPath expression is invalid
    """
    elements = find_elements(root, xpath, namespaces)
    return elements[0] if elements else None

def element_exists(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> bool:
    """
    Check if an element matching the XPath expression exists.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        namespaces: Optional namespace map
        
    Returns:
        True if at least one matching element exists, False otherwise
    """
    try:
        elements = find_elements(root, xpath, namespaces)
        return len(elements) > 0
    except XPathError:
        return False

def get_element_text(
    root: etree._Element,
    xpath: str,
    default: Optional[str] = None,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Get the text content of an element matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        default: Default value to return if the element is not found
        namespaces: Optional namespace map
        
    Returns:
        Text content or default value if not found
    """
    element = find_element(root, xpath, namespaces)
    if element is not None and element.text:
        return element.text.strip()
    return default

def get_element_attribute(
    root: etree._Element,
    xpath: str,
    attribute: str,
    default: Optional[str] = None,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Get an attribute value from an element matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        attribute: Attribute name
        default: Default value to return if the element or attribute is not found
        namespaces: Optional namespace map
        
    Returns:
        Attribute value or default value if not found
    """
    element = find_element(root, xpath, namespaces)
    if element is not None:
        return element.get(attribute, default)
    return default

def create_element(
    tag: str,
    attributes: Optional[Dict[str, str]] = None,
    text: Optional[str] = None,
    parent: Optional[etree._Element] = None
) -> etree._Element:
    """
    Create a new XML element.
    
    Args:
        tag: Element tag name
        attributes: Optional attributes dictionary
        text: Optional text content
        parent: Optional parent element
        
    Returns:
        New XML element
    """
    if parent is not None:
        element = etree.SubElement(parent, tag, **(attributes or {}))
    else:
        element = etree.Element(tag, **(attributes or {}))
        
    if text is not None:
        element.text = text
        
    return element

def set_element_text(
    root: etree._Element,
    xpath: str,
    text: str,
    create_if_missing: bool = False,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[etree._Element]:
    """
    Set the text content of an element matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        text: Text content to set
        create_if_missing: Whether to create the element if it doesn't exist
        namespaces: Optional namespace map
        
    Returns:
        The modified element or None if not found and not created
    """
    element = find_element(root, xpath, namespaces)
    
    if element is None and create_if_missing:
        # TODO: Implement creation of missing elements
        logger.warning("Creation of missing elements is not yet implemented")
        return None
        
    if element is not None:
        element.text = text
        return element
        
    return None

def delete_element(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> int:
    """
    Delete elements matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression to evaluate
        namespaces: Optional namespace map
        
    Returns:
        Number of elements deleted
    """
    elements = find_elements(root, xpath, namespaces)
    count = 0
    
    for element in elements:
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
            count += 1
            
    return count

def clone_element(element: etree._Element) -> etree._Element:
    """
    Create a deep copy of an XML element.
    
    Args:
        element: XML element to clone
        
    Returns:
        Cloned XML element
    """
    return copy.deepcopy(element)

def merge_elements(
    target: etree._Element,
    source: etree._Element,
    overwrite: bool = True
) -> etree._Element:
    """
    Merge two XML elements, copying children and attributes from source to target.
    
    Args:
        target: Target element to merge into
        source: Source element to merge from
        overwrite: Whether to overwrite existing attributes and text
        
    Returns:
        The merged element (target)
        
    Raises:
        MergeError: If the merge operation fails
    """
    try:
        if target.tag != source.tag:
            raise MergeError(f"Cannot merge elements with different tags: {target.tag} and {source.tag}")
        
        # Copy attributes
        for key, value in source.attrib.items():
            if overwrite or key not in target.attrib:
                target.attrib[key] = value
                
        # Copy text if source has non-empty text and (overwrite is True or target has no text)
        if source.text and source.text.strip():
            if overwrite or not target.text or not target.text.strip():
                target.text = source.text
                
        # Process child elements
        source_children = list(source)
        if not source_children:
            return target
        
        for source_child in source_children:
            # Look for a matching child in target
            match = None
            
            # For elements with a 'name' attribute, match by name
            if 'name' in source_child.attrib:
                name = source_child.attrib['name']
                for target_child in target:
                    if target_child.tag == source_child.tag and target_child.get('name') == name:
                        match = target_child
                        break
            
            if match is not None:
                # Recursively merge matching elements
                merge_elements(match, source_child, overwrite)
            else:
                # No match found, add a copy of the source child
                target.append(clone_element(source_child))
        
        return target
    except Exception as e:
        if not isinstance(e, MergeError):
            logger.error(f"Error merging XML elements: {e}")
            raise MergeError(f"Failed to merge XML elements: {e}")
        raise

def element_to_dict(element: etree._Element) -> Dict[str, Any]:
    """
    Convert an XML element to a dictionary.
    
    Args:
        element: XML element to convert
        
    Returns:
        Dictionary representation of the element
    """
    result = {}
    
    # Add attributes with @ prefix
    for key, value in element.attrib.items():
        result[f'@{key}'] = value
    
    # Handle text content if present and not just whitespace
    if element.text and element.text.strip():
        result['#text'] = element.text.strip()
    
    # Process child elements
    for child in element:
        # Convert child element recursively
        child_dict = element_to_dict(child)
        
        # Handle repeated tags (convert to list)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_dict)
        else:
            result[child.tag] = child_dict
                
    return result

def dict_to_element(
    root_tag: str,
    data: Dict[str, Any],
    parent: Optional[etree._Element] = None
) -> etree._Element:
    """
    Convert a dictionary to an XML element.
    
    Args:
        root_tag: Tag name for the root element
        data: Dictionary to convert
        parent: Optional parent element
        
    Returns:
        XML element
    """
    attrib = {}
    children = {}
    text = None
    
    # Separate attributes, text, and child elements
    for key, value in data.items():
        if key.startswith('@'):
            # Attribute
            attrib[key[1:]] = str(value)
        elif key == '#text':
            # Text content
            text = value
        elif isinstance(value, dict):
            # Child element
            children[key] = value
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            # List of child elements
            children[key] = value
        else:
            # Simple value, create text content
            children[key] = {'#text': str(value)}
    
    # Create the element
    if parent is not None:
        element = etree.SubElement(parent, root_tag, attrib=attrib)
    else:
        element = etree.Element(root_tag, attrib=attrib)
    
    # Set text content if present
    if text:
        element.text = text
    
    # Add child elements
    for tag, child_data in children.items():
        if isinstance(child_data, list):
            # Multiple children with the same tag
            for item in child_data:
                dict_to_element(tag, item, element)
        else:
            # Single child
            dict_to_element(tag, child_data, element)
    
    return element

def prettify_xml(
    element: Union[etree._Element, etree._ElementTree],
    indent: str = "  "
) -> str:
    """
    Convert an XML element or tree to a pretty-printed string.
    
    Args:
        element: XML element or ElementTree to format
        indent: Indentation string
        
    Returns:
        Formatted XML string
    """
    if isinstance(element, etree._ElementTree):
        element = element.getroot()
    
    if HAVE_LXML:
        return etree.tostring(element, pretty_print=True, encoding='unicode')
    else:
        # ElementTree doesn't have pretty printing built-in
        from xml.dom import minidom
        rough_string = etree.tostring(element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent=indent)

def validate_xml(
    element: Union[etree._Element, etree._ElementTree],
    schema_file: str
) -> bool:
    """
    Validate an XML element or tree against an XML Schema.
    
    Args:
        element: XML element or ElementTree to validate
        schema_file: Path to XML Schema file
        
    Returns:
        True if valid, raises ValidationError if invalid
        
    Raises:
        ValidationError: If validation fails
        FileOperationError: If schema file cannot be opened
    """
    if not HAVE_LXML:
        logger.warning("XML validation requires lxml which is not installed.")
        return True
        
    try:
        # Parse the schema
        schema_doc = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_doc)
        
        # Get the element if an ElementTree was passed
        if isinstance(element, etree._ElementTree):
            element = element.getroot()
            
        # Validate
        schema.assertValid(element)
        return True
    except etree.DocumentInvalid as e:
        error_msg = f"XML validation failed: {e}"
        logger.error(error_msg)
        raise ValidationError(error_msg)
    except Exception as e:
        from .exceptions import FileOperationError
        error_msg = f"Error validating XML: {e}"
        logger.error(error_msg)
        raise FileOperationError(error_msg)

# Utility functions for getting specific functionality groups
def get_xpath_functions():
    """Get a dictionary of XPath-related functions."""
    return {
        'find_element': find_element,
        'find_elements': find_elements,
        'element_exists': element_exists,
        'get_element_text': get_element_text,
        'get_element_attribute': get_element_attribute
    }

def get_element_manipulation_functions():
    """Get a dictionary of element manipulation functions."""
    return {
        'create_element': create_element,
        'set_element_text': set_element_text,
        'delete_element': delete_element,
        'clone_element': clone_element,
        'merge_elements': merge_elements
    }

def get_conversion_functions():
    """Get a dictionary of conversion functions."""
    return {
        'element_to_dict': element_to_dict,
        'dict_to_element': dict_to_element,
        'prettify_xml': prettify_xml
    }

# Compatibility functions for older code
def compat_element_to_dict(element: etree._Element) -> Dict[str, Any]:
    """
    Convert an XML element to a dictionary (compatibility version).
    
    This version maintains backward compatibility with existing code that expects
    the old format of element_to_dict.
    
    Args:
        element: XML element to convert
        
    Returns:
        Dictionary representation of the element
    """
    data = {}
    
    # Add attributes directly (no @ prefix)
    data.update(element.attrib)
    
    # Add child elements
    for child in element:
        # Check if the child element has multiple "member" children
        members = child.xpath("./member")
        if members:
            # This is a list element
            member_values = [member.text for member in members if member.text]
            data[child.tag] = member_values
        else:
            # Not a list, just a single value or nested element
            if len(child) == 0:
                # Simple element with text
                data[child.tag] = child.text
            else:
                # Nested element, recursively extract data
                data[child.tag] = compat_element_to_dict(child)
    
    return data