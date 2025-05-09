"""
XML query utilities for PANFlow.

This module provides advanced query capabilities for XML elements, allowing
for complex data extraction and transformation operations on PAN-OS XML.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set, Callable
from lxml import etree

from ..exceptions import PANFlowError, XPathError, QueryError
from .base import find_element, find_elements, element_exists
from .builder import XmlNode

# Initialize logger
logger = logging.getLogger("panflow")

class XmlQuery:
    """
    Query engine for XML data extraction and transformation.
    
    Provides a fluent interface for querying XML data and transforming the results.
    """
    
    def __init__(self, root: Union[etree._Element, XmlNode]):
        """
        Initialize with a root XML element.
        
        Args:
            root: Root element for queries
        """
        if isinstance(root, XmlNode):
            self.root = root.element
        else:
            self.root = root
        self.results = []
        self.namespaces = None
    
    @property
    def xml_root(self) -> etree._Element:
        """Get the underlying XML element."""
        return self.root
    
    def find(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> 'XmlQuery':
        """
        Find a single element using XPath.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            Self for chaining
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        self.namespaces = namespaces
        element = find_element(self.root, xpath, namespaces)
        self.results = [element] if element is not None else []
        return self
    
    def find_all(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> 'XmlQuery':
        """
        Find all elements matching an XPath.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            Self for chaining
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        self.namespaces = namespaces
        self.results = find_elements(self.root, xpath, namespaces)
        return self
    
    def exists(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> bool:
        """
        Check if an element exists.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            True if at least one matching element exists
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        return element_exists(self.root, xpath, namespaces)
    
    def filter(self, condition: Callable[[etree._Element], bool]) -> 'XmlQuery':
        """
        Filter results by a custom condition.
        
        Args:
            condition: Function taking an element and returning a boolean
            
        Returns:
            Self for chaining
        """
        self.results = [elem for elem in self.results if condition(elem)]
        return self
    
    def filter_by_attribute(self, name: str, value: str) -> 'XmlQuery':
        """
        Filter results by attribute value.
        
        Args:
            name: Attribute name
            value: Attribute value to match
            
        Returns:
            Self for chaining
        """
        self.results = [elem for elem in self.results if elem.get(name) == value]
        return self
    
    def filter_by_text(self, text: str) -> 'XmlQuery':
        """
        Filter results by text content.
        
        Args:
            text: Text content to match
            
        Returns:
            Self for chaining
        """
        self.results = [elem for elem in self.results if elem.text and elem.text.strip() == text]
        return self
    
    def transform(self, func: Callable[[etree._Element], Any]) -> 'XmlQuery':
        """
        Transform results using a custom function.
        
        Args:
            func: Transformation function taking an element and returning a value
            
        Returns:
            Self for chaining
        """
        self.results = [func(elem) for elem in self.results]
        return self
    
    def get_texts(self) -> List[str]:
        """
        Get text content from all result elements.
        
        Returns:
            List of text strings (None values are filtered out)
        """
        return [elem.text.strip() if isinstance(elem, etree._Element) and elem.text else str(elem) for elem in self.results if elem is not None]
    
    def get_values(self) -> List[Any]:
        """
        Get raw values from results.
        
        Returns:
            List of result values
        """
        return self.results
    
    def get_first(self) -> Optional[etree._Element]:
        """
        Get the first result element.
        
        Returns:
            First result element or None if no results
        """
        return self.results[0] if self.results else None
    
    def get_first_text(self) -> Optional[str]:
        """
        Get text of the first result element.
        
        Returns:
            Text of first result or None if no results
        """
        first = self.get_first()
        if isinstance(first, etree._Element) and first is not None and first.text:
            return first.text.strip()
        elif isinstance(first, str):
            return first
        return None
    
    def get_attributes(self, name: str) -> List[str]:
        """
        Get attribute values from all result elements.
        
        Args:
            name: Attribute name
            
        Returns:
            List of attribute values (None values are filtered out)
        """
        return [
            elem.get(name) for elem in self.results 
            if isinstance(elem, etree._Element) and elem.get(name) is not None
        ]
    
    def get_first_attribute(self, name: str) -> Optional[str]:
        """
        Get attribute value from the first result element.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value or None if no results or attribute doesn't exist
        """
        first = self.get_first()
        if isinstance(first, etree._Element) and first is not None:
            return first.get(name)
        return None
    
    def get_nodes(self) -> List[XmlNode]:
        """
        Get result elements as XmlNode objects.
        
        Returns:
            List of XmlNode objects (non-Element results are filtered out)
        """
        return [
            XmlNode(elem) for elem in self.results 
            if isinstance(elem, etree._Element)
        ]
    
    def get_first_node(self) -> Optional[XmlNode]:
        """
        Get the first result element as an XmlNode.
        
        Returns:
            XmlNode or None if no results
        """
        first = self.get_first()
        if isinstance(first, etree._Element):
            return XmlNode(first)
        return None
    
    def to_dicts(self, include_attributes: bool = True) -> List[Dict[str, Any]]:
        """
        Convert result elements to dictionaries.
        
        Args:
            include_attributes: Whether to include attributes
            
        Returns:
            List of dictionaries
        """
        from .base import element_to_dict
        return [
            element_to_dict(elem) for elem in self.results 
            if isinstance(elem, etree._Element)
        ]
    
    def __iter__(self) -> Iterator[etree._Element]:
        """Iterate through results."""
        return iter(self.results)
    
    def __len__(self) -> int:
        """Get the number of results."""
        return len(self.results)
    
    def __bool__(self) -> bool:
        """Check if there are any results."""
        return bool(self.results)