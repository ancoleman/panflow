"""
XML utilities for PAN-OS XML configurations.

This module provides utility functions for working with XML in PAN-OS configurations,
including parsing, navigation, and manipulation.
"""

import os
import sys
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set
import logging
from datetime import datetime
import copy

# Try to import lxml first, fall back to ElementTree if not available
try:
    from lxml import etree
    HAVE_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    HAVE_LXML = False

logger = logging.getLogger("panflow")

# Custom exceptions for XML operations
class XmlError(Exception):
    """Base exception for XML operations."""
    pass

class XmlParseError(XmlError):
    """Exception raised when XML parsing fails."""
    pass

class XmlXPathError(XmlError):
    """Exception raised when XPath evaluation fails."""
    pass

class XmlMergeError(XmlError):
    """Exception raised when merging XML elements fails."""
    pass

def parse_xml(
    source: Union[str, bytes, os.PathLike],
    validate: bool = False,
    schema_file: Optional[str] = None
) -> Tuple[etree._ElementTree, etree._Element]:
    """
    Parse XML from a file or string and return both the tree and root element.
    
    Args:
        source: XML source (file path, bytes, or XML string)
        validate: Whether to validate against a schema
        schema_file: XML Schema file path (required if validate=True)
        
    Returns:
        Tuple containing (ElementTree, root Element)
        
    Raises:
        XmlParseError: If XML parsing fails
        ValueError: If validate=True but no schema_file is provided
    """
    try:
        # Handle different source types
        if isinstance(source, (bytes, str)) and '<' in str(source):
            # Source is an XML string or bytes
            if isinstance(source, str):
                source = source.encode('utf-8')
            
            if HAVE_LXML:
                if validate:
                    if not schema_file:
                        raise ValueError("schema_file is required when validate=True")
                    
                    schema_doc = etree.parse(schema_file)
                    schema = etree.XMLSchema(schema_doc)
                    parser = etree.XMLParser(schema=schema)
                    root = etree.fromstring(source, parser)
                    tree = etree.ElementTree(root)
                else:
                    root = etree.fromstring(source)
                    tree = etree.ElementTree(root)
            else:
                root = etree.fromstring(source)
                tree = etree.ElementTree(root)
                
                if validate:
                    logger.warning("Validation requires lxml which is not installed. Skipping validation.")
        else:
            # Source is a file path
            if HAVE_LXML:
                if validate:
                    if not schema_file:
                        raise ValueError("schema_file is required when validate=True")
                    
                    schema_doc = etree.parse(schema_file)
                    schema = etree.XMLSchema(schema_doc)
                    parser = etree.XMLParser(schema=schema)
                    tree = etree.parse(source, parser)
                else:
                    tree = etree.parse(source)
            else:
                tree = etree.parse(source)
                
                if validate:
                    logger.warning("Validation requires lxml which is not installed. Skipping validation.")
            
            root = tree.getroot()
        
        logger.debug(f"Successfully parsed XML{'(validated)' if validate else ''}")
        return tree, root
    except Exception as e:
        logger.error(f"Error parsing XML: {e}")
        raise XmlParseError(f"Failed to parse XML: {e}")

def find_elements(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> List[etree._Element]:
    """
    Find elements using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Optional namespace mappings
        
    Returns:
        List of matching elements
        
    Raises:
        XmlXPathError: If XPath evaluation fails
    """
    try:
        if HAVE_LXML:
            elements = root.xpath(xpath, namespaces=namespaces)
        else:
            # Limited XPath support with ElementTree
            # Remove namespace prefixes if ElementTree is used
            if namespaces:
                for prefix, uri in namespaces.items():
                    xpath = xpath.replace(f"{prefix}:", "")
            
            # ElementTree's find/findall don't support the full XPath spec
            # This is a limited implementation
            if xpath.startswith('//'):
                elements = root.findall(f".{xpath}")
            else:
                elements = root.findall(xpath)
        
        logger.debug(f"XPath '{xpath}' found {len(elements)} elements")
        return elements
    except Exception as e:
        logger.error(f"Error evaluating XPath '{xpath}': {e}")
        raise XmlXPathError(f"Failed to evaluate XPath '{xpath}': {e}")

def find_element(
    root: etree._Element, 
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[etree._Element]:
    """
    Find a single element using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Optional namespace mappings
        
    Returns:
        Matching element or None if not found
        
    Raises:
        XmlXPathError: If XPath evaluation fails
    """
    elements = find_elements(root, xpath, namespaces)
    return elements[0] if elements else None

def element_exists(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> bool:
    """
    Check if an element exists using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Optional namespace mappings
        
    Returns:
        True if element exists, False otherwise
    """
    try:
        elements = find_elements(root, xpath, namespaces)
        return len(elements) > 0
    except XmlXPathError:
        return False

def get_element_text(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None,
    default: str = ""
) -> str:
    """
    Get the text content of an element using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Optional namespace mappings
        default: Default value if element not found or has no text
        
    Returns:
        Text content of the element or default value
    """
    element = find_element(root, xpath, namespaces)
    if element is not None and element.text:
        return element.text
    return default

def get_element_attribute(
    root: etree._Element,
    xpath: str,
    attribute: str,
    namespaces: Optional[Dict[str, str]] = None,
    default: str = ""
) -> str:
    """
    Get an attribute value of an element using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        attribute: Attribute name
        namespaces: Optional namespace mappings
        default: Default value if element not found or attribute not present
        
    Returns:
        Attribute value or default
    """
    element = find_element(root, xpath, namespaces)
    if element is not None:
        return element.get(attribute, default)
    return default

def create_element(
    tag: str,
    parent: Optional[etree._Element] = None,
    text: Optional[str] = None,
    attributes: Optional[Dict[str, str]] = None
) -> etree._Element:
    """
    Create a new XML element with optional parent, text, and attributes.
    
    Args:
        tag: Element tag name
        parent: Optional parent element to attach to
        text: Optional text content
        attributes: Optional dictionary of attributes
        
    Returns:
        The created element
    """
    if parent is not None:
        element = etree.SubElement(parent, tag, attrib=attributes or {})
    else:
        element = etree.Element(tag, attrib=attributes or {})
    
    if text is not None:
        element.text = text
    
    return element

def set_element_text(
    root: etree._Element,
    xpath: str,
    text: str,
    namespaces: Optional[Dict[str, str]] = None,
    create_if_missing: bool = False
) -> Optional[etree._Element]:
    """
    Set the text content of an element identified by XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        text: Text content to set
        namespaces: Optional namespace mappings
        create_if_missing: Whether to create the element if it doesn't exist
        
    Returns:
        The modified element or None if not found and not created
    """
    element = find_element(root, xpath, namespaces)
    
    if element is None and create_if_missing:
        # This is a simplified implementation that works for basic cases
        # For more complex XPath expressions, a more sophisticated approach would be needed
        parts = xpath.strip('/').split('/')
        current = root
        
        for i, part in enumerate(parts[:-1]):  # Navigate to parent
            # Handle predicates (simplified approach)
            tag = part.split('[')[0] if '[' in part else part
            child = find_element(current, f'./{tag}')
            
            if child is None:
                child = create_element(tag, current)
            
            current = child
        
        # Create the final element
        last_part = parts[-1]
        tag = last_part.split('[')[0] if '[' in last_part else last_part
        element = create_element(tag, current, text)
    elif element is not None:
        element.text = text
    
    return element

def delete_element(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> int:
    """
    Delete elements matching an XPath expression.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Optional namespace mappings
        
    Returns:
        Number of elements deleted
    """
    elements = find_elements(root, xpath, namespaces)
    count = 0
    
    for element in elements:
        parent = element.getparent() if HAVE_LXML else None
        
        if parent is not None:
            parent.remove(element)
            count += 1
        else:
            # If using ElementTree (no getparent), we need a different approach
            # This is a limitation of ElementTree and might not work in all cases
            if not HAVE_LXML:
                # Try to find parent by scanning the tree
                for potential_parent in root.iter():
                    for child in list(potential_parent):
                        if child is element:
                            potential_parent.remove(child)
                            count += 1
                            break
    
    return count

def clone_element(element: etree._Element) -> etree._Element:
    """
    Create a deep copy of an XML element.
    
    Args:
        element: Element to clone
        
    Returns:
        Cloned element
    """
    if HAVE_LXML:
        return copy.deepcopy(element)
    else:
        # Manual deep copy for ElementTree
        attrib = element.attrib.copy()
        new_element = etree.Element(element.tag, attrib=attrib)
        
        if element.text:
            new_element.text = element.text
        
        if element.tail:
            new_element.tail = element.tail
        
        for child in element:
            new_child = clone_element(child)
            new_element.append(new_child)
        
        return new_element

def merge_elements(
    target: etree._Element,
    source: etree._Element,
    overwrite: bool = True
) -> etree._Element:
    """
    Merge two XML elements, adding children from source to target.
    
    Args:
        target: Target element to merge into
        source: Source element to merge from
        overwrite: Whether to overwrite existing elements
        
    Returns:
        The merged element (target)
        
    Raises:
        XmlMergeError: If the merge operation fails
    """
    try:
        if target.tag != source.tag:
            raise XmlMergeError(f"Cannot merge elements with different tags: {target.tag} and {source.tag}")
        
        # Copy attributes
        for key, value in source.attrib.items():
            if overwrite or key not in target.attrib:
                target.attrib[key] = value
        
        # Set text if source has text and (overwrite or target has no text)
        if source.text and (overwrite or not target.text):
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
        if not isinstance(e, XmlMergeError):
            logger.error(f"Error merging XML elements: {e}")
            raise XmlMergeError(f"Failed to merge XML elements: {e}")
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
    
    # Add attributes
    result.update(element.attrib)
    
    # Handle text content if present and not just whitespace
    if element.text and element.text.strip():
        result['_text'] = element.text.strip()
    
    # Process child elements
    for child in element:
        # Special handling for <member> tags which are typically used for lists in PAN-OS
        if child.tag == 'member' and child.text:
            if '_members' not in result:
                result['_members'] = []
            result['_members'].append(child.text)
        else:
            # Convert child element recursively
            child_dict = element_to_dict(child)
            
            if child.tag in result:
                # If this tag already exists, convert to a list
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
    
    return result

def dict_to_element(
    data: Dict[str, Any],
    root_tag: str,
    parent: Optional[etree._Element] = None
) -> etree._Element:
    """
    Convert a dictionary to an XML element.
    
    Args:
        data: Dictionary to convert
        root_tag: Tag name for the root element
        parent: Optional parent element
        
    Returns:
        XML element
    """
    attrib = {}
    children = {}
    text = None
    members = []
    
    # Separate attributes, text, members, and child elements
    for key, value in data.items():
        if key == '_text':
            text = value
        elif key == '_members':
            members = value
        elif isinstance(value, dict):
            children[key] = value
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            children[key] = value
        else:
            attrib[key] = str(value)
    
    # Create the element
    if parent is not None:
        element = etree.SubElement(parent, root_tag, attrib=attrib)
    else:
        element = etree.Element(root_tag, attrib=attrib)
    
    # Set text content if present
    if text:
        element.text = text
    
    # Add member elements
    for member in members:
        member_elem = etree.SubElement(element, 'member')
        member_elem.text = member
    
    # Add child elements
    for tag, child_data in children.items():
        if isinstance(child_data, list):
            # Multiple children with the same tag
            for item in child_data:
                dict_to_element(item, tag, element)
        else:
            # Single child
            dict_to_element(child_data, tag, element)
    
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
        return etree.tostring(
            element,
            pretty_print=True,
            encoding='unicode',
            xml_declaration=True
        )
    else:
        # Basic pretty printing for ElementTree
        from xml.dom import minidom
        rough_string = etree.tostring(element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent=indent)

def validate_xml(
    tree: etree._ElementTree,
    schema_file: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate an XML document against an XML Schema.
    
    Args:
        tree: XML ElementTree to validate
        schema_file: Path to XML Schema file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not HAVE_LXML:
        error = "XML validation requires lxml which is not installed"
        logger.warning(error)
        return False, error
    
    try:
        schema_doc = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_doc)
        result = schema.validate(tree)
        
        if not result:
            error = schema.error_log.last_error
            return False, str(error)
        
        return True, None
    except Exception as e:
        error = f"Error validating XML: {e}"
        logger.error(error)
        return False, error

def get_xpath_functions() -> Dict[str, callable]:
    """
    Get a dictionary of XPath helper functions.
    
    Returns:
        Dictionary mapping function names to callables
    """
    return {
        'find_elements': find_elements,
        'find_element': find_element,
        'element_exists': element_exists,
        'get_element_text': get_element_text,
        'get_element_attribute': get_element_attribute
    }

def get_element_manipulation_functions() -> Dict[str, callable]:
    """
    Get a dictionary of element manipulation functions.
    
    Returns:
        Dictionary mapping function names to callables
    """
    return {
        'create_element': create_element,
        'set_element_text': set_element_text,
        'delete_element': delete_element,
        'clone_element': clone_element,
        'merge_elements': merge_elements
    }

def get_conversion_functions() -> Dict[str, callable]:
    """
    Get a dictionary of conversion functions.
    
    Returns:
        Dictionary mapping function names to callables
    """
    return {
        'element_to_dict': element_to_dict,
        'dict_to_element': dict_to_element,
        'prettify_xml': prettify_xml
    }