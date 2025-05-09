"""
XML builder utility for PANFlow.

This module provides higher-level abstractions for XML operations,
making it easier to create, modify, and query XML elements.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set, Callable
from lxml import etree

from ..exceptions import PANFlowError, XPathError, ValidationError
from .base import parse_xml, find_element, find_elements, element_exists
from .cache import cached_xpath, clear_xpath_cache

# Initialize logger
logger = logging.getLogger("panflow")

class XmlNode:
    """
    A high-level wrapper for XML elements.
    
    Provides a more Pythonic interface for working with XML elements,
    with methods for navigating, querying, and modifying the element.
    """
    
    def __init__(self, element: etree._Element):
        """
        Initialize with an XML element.
        
        Args:
            element: The XML element to wrap
        """
        self.element = element
        
    @classmethod
    def create(cls, tag: str, attributes: Optional[Dict[str, str]] = None, text: Optional[str] = None) -> 'XmlNode':
        """
        Create a new XML node.
        
        Args:
            tag: Element tag name
            attributes: Optional element attributes
            text: Optional element text
            
        Returns:
            XmlNode: A new XmlNode instance
        """
        element = etree.Element(tag, **(attributes or {}))
        if text is not None:
            element.text = text
        return cls(element)
    
    @classmethod
    def from_string(cls, xml_string: str) -> 'XmlNode':
        """
        Create a node from an XML string.
        
        Args:
            xml_string: XML string to parse
            
        Returns:
            XmlNode: A new XmlNode instance
            
        Raises:
            ParseError: If the XML string cannot be parsed
        """
        tree, root = parse_xml(xml_string)
        return cls(root)
    
    @property
    def tag(self) -> str:
        """Get the element tag name."""
        return self.element.tag
    
    @property
    def text(self) -> Optional[str]:
        """Get the element text."""
        return self.element.text
    
    @text.setter
    def text(self, value: Optional[str]):
        """Set the element text."""
        self.element.text = value
    
    @property
    def tail(self) -> Optional[str]:
        """Get the element tail text."""
        return self.element.tail
    
    @tail.setter
    def tail(self, value: Optional[str]):
        """Set the element tail text."""
        self.element.tail = value
    
    @property
    def attributes(self) -> Dict[str, str]:
        """Get all element attributes."""
        return dict(self.element.attrib)
    
    def get_attribute(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an attribute value.
        
        Args:
            name: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            Attribute value or default
        """
        return self.element.get(name, default)
    
    def set_attribute(self, name: str, value: str) -> 'XmlNode':
        """
        Set an attribute value.
        
        Args:
            name: Attribute name
            value: Attribute value
            
        Returns:
            Self for chaining
        """
        self.element.set(name, value)
        return self
    
    def delete_attribute(self, name: str) -> 'XmlNode':
        """
        Delete an attribute.
        
        Args:
            name: Attribute name
            
        Returns:
            Self for chaining
        """
        if name in self.element.attrib:
            del self.element.attrib[name]
        return self
    
    @property
    def parent(self) -> Optional['XmlNode']:
        """
        Get the parent node.
        
        Returns:
            Parent node or None if no parent
        """
        parent = self.element.getparent()
        return XmlNode(parent) if parent is not None else None
    
    @property
    def children(self) -> List['XmlNode']:
        """
        Get all child nodes.
        
        Returns:
            List of child nodes
        """
        return [XmlNode(child) for child in self.element]
    
    def child(self, tag: Optional[str] = None, index: int = 0) -> Optional['XmlNode']:
        """
        Get a specific child node.
        
        Args:
            tag: Optional tag name to filter by
            index: Index of the child (if multiple match)
            
        Returns:
            Child node or None if not found
        """
        matching_children = [child for child in self.element if tag is None or child.tag == tag]
        return XmlNode(matching_children[index]) if 0 <= index < len(matching_children) else None
    
    def add_child(self, tag: str, attributes: Optional[Dict[str, str]] = None, text: Optional[str] = None) -> 'XmlNode':
        """
        Add a child node.
        
        Args:
            tag: Element tag name
            attributes: Optional element attributes
            text: Optional element text
            
        Returns:
            The newly created child node
        """
        child = etree.SubElement(self.element, tag, **(attributes or {}))
        if text is not None:
            child.text = text
        return XmlNode(child)
    
    def append(self, node: 'XmlNode') -> 'XmlNode':
        """
        Append a node as a child.
        
        Args:
            node: Node to append
            
        Returns:
            Self for chaining
        """
        self.element.append(node.element)
        return self
    
    def remove_child(self, child: 'XmlNode') -> 'XmlNode':
        """
        Remove a child node.
        
        Args:
            child: Child node to remove
            
        Returns:
            Self for chaining
        """
        self.element.remove(child.element)
        return self
    
    def clear(self) -> 'XmlNode':
        """
        Remove all children and text.
        
        Returns:
            Self for chaining
        """
        self.element.clear()
        return self
    
    def find(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> Optional['XmlNode']:
        """
        Find a single element using XPath.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            Matching node or None if not found
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        element = find_element(self.element, xpath, namespaces)
        return XmlNode(element) if element is not None else None
    
    def find_all(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List['XmlNode']:
        """
        Find all elements matching an XPath.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            List of matching nodes
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        elements = find_elements(self.element, xpath, namespaces)
        return [XmlNode(element) for element in elements]
    
    def exists(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> bool:
        """
        Check if an element exists.
        
        Args:
            xpath: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            True if an element matching the XPath exists
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        return element_exists(self.element, xpath, namespaces)
    
    def to_string(self, pretty_print: bool = True, include_declaration: bool = True) -> str:
        """
        Convert the node to an XML string.
        
        Args:
            pretty_print: Whether to format the XML with indentation
            include_declaration: Whether to include the XML declaration
            
        Returns:
            XML string representation
        """
        xml_declaration = include_declaration
        encoding = 'utf-8'
        
        xml_bytes = etree.tostring(
            self.element, 
            pretty_print=pretty_print,
            xml_declaration=xml_declaration,
            encoding=encoding
        )
        
        return xml_bytes.decode(encoding)
    
    def to_dict(self, include_attributes: bool = True) -> Dict[str, Any]:
        """
        Convert the node to a dictionary.
        
        Args:
            include_attributes: Whether to include attributes
            
        Returns:
            Dictionary representation
        """
        result = {}
        
        # Add attributes
        if include_attributes and self.element.attrib:
            for key, value in self.element.attrib.items():
                result[f"@{key}"] = value
        
        # Add text content if present
        if self.element.text and self.element.text.strip():
            if len(self.element) == 0:  # If no children
                result["#text"] = self.element.text.strip()
            else:
                result["#text"] = self.element.text.strip()
        
        # Process child elements
        for child in self.element:
            child_dict = XmlNode(child).to_dict(include_attributes)
            
            # Handle multiple children with the same tag
            if child.tag in result:
                # Convert to list if not already
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
        
        return result
    
    def xpath(self, expression: str, namespaces: Optional[Dict[str, str]] = None) -> List[Any]:
        """
        Execute an XPath expression.
        
        This provides direct access to lxml's xpath method.
        
        Args:
            expression: XPath expression
            namespaces: Optional namespace mappings
            
        Returns:
            List of results (could be nodes, strings, numbers, etc.)
            
        Raises:
            XPathError: If the XPath expression is invalid
        """
        try:
            results = self.element.xpath(expression, namespaces=namespaces)
            
            # Convert element results to XmlNode objects
            processed_results = []
            for result in results:
                if isinstance(result, etree._Element):
                    processed_results.append(XmlNode(result))
                else:
                    processed_results.append(result)
                    
            return processed_results
        except Exception as e:
            logger.error(f"Error evaluating XPath '{expression}': {e}")
            raise XPathError(f"Failed to evaluate XPath '{expression}': {e}")
    
    def __eq__(self, other: object) -> bool:
        """Compare equality with another node."""
        if not isinstance(other, XmlNode):
            return False
        return etree.tostring(self.element) == etree.tostring(other.element)
    
    def __repr__(self) -> str:
        """String representation."""
        attributes = ' '.join(f'{k}="{v}"' for k, v in self.element.attrib.items())
        return f"<XmlNode {self.element.tag} {attributes}>"


class XmlBuilder:
    """
    Builder for creating XML hierarchies.
    
    Provides a fluent interface for creating and manipulating XML elements.
    """
    
    def __init__(self, root_tag: str, attributes: Optional[Dict[str, str]] = None):
        """
        Initialize with a root tag.
        
        Args:
            root_tag: Root element tag name
            attributes: Optional root element attributes
        """
        self.root = XmlNode.create(root_tag, attributes)
        self.current = self.root
        self._path_stack = []
    
    def add(self, tag: str, attributes: Optional[Dict[str, str]] = None, text: Optional[str] = None) -> 'XmlBuilder':
        """
        Add a child element to the current element.
        
        Args:
            tag: Element tag name
            attributes: Optional element attributes
            text: Optional element text
            
        Returns:
            Self for chaining
        """
        self.current.add_child(tag, attributes, text)
        return self
    
    def into(self, tag: str, attributes: Optional[Dict[str, str]] = None, text: Optional[str] = None) -> 'XmlBuilder':
        """
        Add a child element and navigate into it.
        
        Args:
            tag: Element tag name
            attributes: Optional element attributes
            text: Optional element text
            
        Returns:
            Self for chaining
        """
        self._path_stack.append(self.current)
        self.current = self.current.add_child(tag, attributes, text)
        return self
    
    def up(self) -> 'XmlBuilder':
        """
        Navigate up to the parent element.
        
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If already at the root element
        """
        if not self._path_stack:
            raise ValueError("Already at root element")
            
        self.current = self._path_stack.pop()
        return self
    
    def root_up(self) -> 'XmlBuilder':
        """
        Navigate back to the root element.
        
        Returns:
            Self for chaining
        """
        self.current = self.root
        self._path_stack = []
        return self
    
    def with_text(self, text: str) -> 'XmlBuilder':
        """
        Set text of the current element.
        
        Args:
            text: Element text
            
        Returns:
            Self for chaining
        """
        self.current.text = text
        return self
    
    def with_attribute(self, name: str, value: str) -> 'XmlBuilder':
        """
        Set an attribute of the current element.
        
        Args:
            name: Attribute name
            value: Attribute value
            
        Returns:
            Self for chaining
        """
        self.current.set_attribute(name, value)
        return self
    
    def build(self) -> XmlNode:
        """
        Build and return the XML tree.
        
        Returns:
            Root XML node
        """
        return self.root
    
    def to_string(self, pretty_print: bool = True, include_declaration: bool = True) -> str:
        """
        Build and return the XML tree as a string.
        
        Args:
            pretty_print: Whether to format the XML with indentation
            include_declaration: Whether to include the XML declaration
            
        Returns:
            XML string
        """
        return self.root.to_string(pretty_print, include_declaration)


class XPathBuilder:
    """
    Builder for creating XPath expressions.
    
    Provides a fluent interface for building XPath expressions.
    """
    
    def __init__(self, initial_path: Optional[str] = None):
        """
        Initialize with an optional initial path.
        
        Args:
            initial_path: Optional initial XPath
        """
        self.path = initial_path or ""
    
    def root(self) -> 'XPathBuilder':
        """
        Start at the root element.
        
        Returns:
            Self for chaining
        """
        self.path = "/"
        return self
    
    def anywhere(self) -> 'XPathBuilder':
        """
        Match elements anywhere in the document.
        
        Returns:
            Self for chaining
        """
        self.path = "//"
        return self
    
    def element(self, tag: str) -> 'XPathBuilder':
        """
        Add an element to the path.
        
        Args:
            tag: Element tag name
            
        Returns:
            Self for chaining
        """
        if self.path and not self.path.endswith("/"):
            self.path += "/"
        self.path += tag
        return self
    
    def with_attribute(self, name: str, value: Optional[str] = None) -> 'XPathBuilder':
        """
        Add an attribute selector.
        
        Args:
            name: Attribute name
            value: Optional attribute value
            
        Returns:
            Self for chaining
        """
        if value is not None:
            self.path += f"[@{name}='{value}']"
        else:
            self.path += f"[@{name}]"
        return self
    
    def with_name(self, name: str) -> 'XPathBuilder':
        """
        Add a name attribute selector (common in PAN-OS XML).
        
        Args:
            name: Name value
            
        Returns:
            Self for chaining
        """
        return self.with_attribute("name", name)
    
    def child(self, tag: str) -> 'XPathBuilder':
        """
        Add a child element.
        
        Args:
            tag: Child element tag name
            
        Returns:
            Self for chaining
        """
        self.path += f"/{tag}"
        return self
    
    def descendant(self, tag: str) -> 'XPathBuilder':
        """
        Add a descendant element (any level below).
        
        Args:
            tag: Descendant element tag name
            
        Returns:
            Self for chaining
        """
        self.path += f"//{tag}"
        return self
    
    def with_text(self, text: str) -> 'XPathBuilder':
        """
        Add a text content filter.
        
        Args:
            text: Text to match
            
        Returns:
            Self for chaining
        """
        self.path += f"[text()='{text}']"
        return self
    
    def contains_text(self, text: str) -> 'XPathBuilder':
        """
        Add a text content contains filter.
        
        Args:
            text: Text to search for
            
        Returns:
            Self for chaining
        """
        self.path += f"[contains(text(),'{text}')]"
        return self
    
    def where(self, expression: str) -> 'XPathBuilder':
        """
        Add a custom predicate.
        
        Args:
            expression: Predicate expression
            
        Returns:
            Self for chaining
        """
        self.path += f"[{expression}]"
        return self
    
    def parent(self) -> 'XPathBuilder':
        """
        Navigate to the parent element.
        
        Returns:
            Self for chaining
        """
        self.path += "/.."
        return self
    
    def or_element(self, tag: str) -> 'XPathBuilder':
        """
        Add an alternative element (logical OR).
        
        Args:
            tag: Element tag name
            
        Returns:
            Self for chaining
        """
        self.path += f"|//{tag}"
        return self
    
    def build(self) -> str:
        """
        Build and return the XPath expression.
        
        Returns:
            XPath string
        """
        return self.path