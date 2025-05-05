"""
XML query utilities for PANFlow.

This module provides a higher-level query interface for XML data,
with features similar to CSS selectors or jQuery, but focused on PAN-OS XML.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set, Callable
from lxml import etree

from .exceptions import PANFlowError, XPathError, ValidationError
from .xml_utils import find_element, find_elements, element_exists
from .xml_builder import XmlNode

# Initialize logger
logger = logging.getLogger("panflow")

class XmlQuery:
    """
    Query interface for XML elements.
    
    Provides a chainable interface for selecting and filtering XML elements.
    """
    
    def __init__(self, elements: List[etree._Element]):
        """
        Initialize with a list of elements.
        
        Args:
            elements: List of XML elements
        """
        self.elements = elements
        
    @classmethod
    def from_node(cls, node: XmlNode) -> 'XmlQuery':
        """
        Create a query from an XmlNode.
        
        Args:
            node: XML node
            
        Returns:
            XmlQuery instance
        """
        return cls([node.element])
    
    @classmethod
    def from_tree(cls, tree: etree._ElementTree) -> 'XmlQuery':
        """
        Create a query from an ElementTree.
        
        Args:
            tree: ElementTree
            
        Returns:
            XmlQuery instance
        """
        return cls([tree.getroot()])
    
    def find(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> 'XmlQuery':
        """
        Find elements using XPath, relative to each element in the current set.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            New XmlQuery with the found elements
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        results = []
        
        for element in self.elements:
            try:
                found = find_elements(element, xpath, namespaces)
                results.extend(found)
            except XPathError as e:
                logger.error(f"XPath error during find operation: {e}")
                raise
        
        return XmlQuery(results)
    
    def filter(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> 'XmlQuery':
        """
        Filter the current elements using an XPath predicate.
        
        Args:
            xpath: XPath predicate (without the square brackets)
            namespaces: Optional namespace mappings
            
        Returns:
            New XmlQuery with the filtered elements
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        predicate = f"[{xpath}]"
        results = []
        
        for element in self.elements:
            try:
                # Apply the predicate to the current element's path
                element_path = self._get_element_path(element)
                full_xpath = f"{element_path}{predicate}"
                
                # Find the element again with the predicate
                root = element.getroottree().getroot()
                filtered = find_elements(root, full_xpath, namespaces)
                
                # If the element matches (is in the filtered set), include it
                if any(e is element for e in filtered):
                    results.append(element)
            except XPathError as e:
                logger.error(f"XPath error during filter operation: {e}")
                raise
            except Exception as e:
                logger.error(f"Error during filter operation: {e}")
                # Continue with other elements
        
        return XmlQuery(results)
    
    def _get_element_path(self, element: etree._Element) -> str:
        """
        Get the absolute XPath to an element.
        
        Args:
            element: XML element
            
        Returns:
            Absolute XPath string
        """
        root = element.getroottree().getroot()
        if element is root:
            return "/"
            
        path = ""
        current = element
        
        while current is not None and current is not root:
            parent = current.getparent()
            if parent is None:
                # Detached element or something went wrong
                break
                
            # Get the position among siblings with the same tag
            siblings = [c for c in parent if c.tag == current.tag]
            position = siblings.index(current) + 1
            
            # Add to path
            if position > 1 or len(siblings) > 1:
                path = f"/{current.tag}[{position}]{path}"
            else:
                path = f"/{current.tag}{path}"
                
            current = parent
            
        return f"/{root.tag}{path}"
    
    def has_text(self, text: str) -> 'XmlQuery':
        """
        Filter elements that have the specified text.
        
        Args:
            text: Text to match
            
        Returns:
            New XmlQuery with the filtered elements
        """
        return self.filter(f"text()='{text}'")
    
    def has_text_containing(self, text: str) -> 'XmlQuery':
        """
        Filter elements that have text containing the specified string.
        
        Args:
            text: Text to search for
            
        Returns:
            New XmlQuery with the filtered elements
        """
        return self.filter(f"contains(text(),'{text}')")
    
    def has_attribute(self, name: str, value: Optional[str] = None) -> 'XmlQuery':
        """
        Filter elements that have the specified attribute.
        
        Args:
            name: Attribute name
            value: Optional attribute value to match
            
        Returns:
            New XmlQuery with the filtered elements
        """
        if value is not None:
            return self.filter(f"@{name}='{value}'")
        else:
            return self.filter(f"@{name}")
    
    def has_name(self, name: str) -> 'XmlQuery':
        """
        Filter elements that have the specified name attribute.
        
        Args:
            name: Name value
            
        Returns:
            New XmlQuery with the filtered elements
        """
        return self.has_attribute("name", name)
    
    def has_child(self, tag: str) -> 'XmlQuery':
        """
        Filter elements that have a child with the specified tag.
        
        Args:
            tag: Child element tag
            
        Returns:
            New XmlQuery with the filtered elements
        """
        return self.filter(f"{tag}")
    
    def has_descendant(self, tag: str) -> 'XmlQuery':
        """
        Filter elements that have a descendant with the specified tag.
        
        Args:
            tag: Descendant element tag
            
        Returns:
            New XmlQuery with the filtered elements
        """
        return self.filter(f"descendant::{tag}")
    
    def first(self) -> Optional[XmlNode]:
        """
        Get the first element in the set.
        
        Returns:
            First element as XmlNode or None if set is empty
        """
        return XmlNode(self.elements[0]) if self.elements else None
    
    def last(self) -> Optional[XmlNode]:
        """
        Get the last element in the set.
        
        Returns:
            Last element as XmlNode or None if set is empty
        """
        return XmlNode(self.elements[-1]) if self.elements else None
    
    def at(self, index: int) -> Optional[XmlNode]:
        """
        Get element at specified index.
        
        Args:
            index: Element index
            
        Returns:
            Element at index as XmlNode or None if index is out of bounds
        """
        if 0 <= index < len(self.elements):
            return XmlNode(self.elements[index])
        return None
    
    def count(self) -> int:
        """
        Get the number of elements in the set.
        
        Returns:
            Number of elements
        """
        return len(self.elements)
    
    def nodes(self) -> List[XmlNode]:
        """
        Get all elements as XmlNode objects.
        
        Returns:
            List of XmlNode objects
        """
        return [XmlNode(element) for element in self.elements]
    
    def text(self) -> List[Optional[str]]:
        """
        Get the text content of all elements.
        
        Returns:
            List of text strings
        """
        return [element.text for element in self.elements]
    
    def attribute(self, name: str) -> List[Optional[str]]:
        """
        Get the specified attribute from all elements.
        
        Args:
            name: Attribute name
            
        Returns:
            List of attribute values
        """
        return [element.get(name) for element in self.elements]
    
    def values(self) -> List[str]:
        """
        Get text content or name attribute of all elements.
        
        Returns:
            List of values (text or name attribute)
        """
        result = []
        for element in self.elements:
            if element.get("name"):
                result.append(element.get("name"))
            elif element.text:
                result.append(element.text.strip())
            else:
                result.append("")
        return result
    
    def each(self, callback: Callable[[XmlNode], None]) -> 'XmlQuery':
        """
        Execute a callback for each element.
        
        Args:
            callback: Function to call with each element
            
        Returns:
            Self for chaining
        """
        for element in self.elements:
            callback(XmlNode(element))
        return self
    
    def map(self, callback: Callable[[XmlNode], Any]) -> List[Any]:
        """
        Transform each element using a callback.
        
        Args:
            callback: Function to transform each element
            
        Returns:
            List of transformed values
        """
        return [callback(XmlNode(element)) for element in self.elements]
    
    def to_dict(self, include_attributes: bool = True) -> List[Dict[str, Any]]:
        """
        Convert all elements to dictionaries.
        
        Args:
            include_attributes: Whether to include attributes
            
        Returns:
            List of dictionaries
        """
        return [XmlNode(element).to_dict(include_attributes) for element in self.elements]
    
    def __iter__(self) -> Iterator[XmlNode]:
        """Iterate over the elements."""
        return (XmlNode(element) for element in self.elements)
    
    def __len__(self) -> int:
        """Get the number of elements."""
        return len(self.elements)
    
    def __bool__(self) -> bool:
        """Check if there are any elements."""
        return bool(self.elements)