"""
Tests for the consolidated XML package.

This module tests that the new XML package structure works correctly
and that the compatibility layer functions as expected.
"""

import pytest
import warnings
from lxml import etree

# Test importing from the new package
def test_import_xml_package():
    """Test importing from the new XML package."""
    from panflow.core import xml
    
    # Check that we can access the main modules
    assert hasattr(xml, 'base')
    assert hasattr(xml, 'cache')
    assert hasattr(xml, 'builder')
    assert hasattr(xml, 'diff')
    assert hasattr(xml, 'query')
    
    # Check that we can access key classes and functions directly
    assert hasattr(xml, 'XmlNode')
    assert hasattr(xml, 'XmlBuilder')
    assert hasattr(xml, 'XPathBuilder')
    assert hasattr(xml, 'XmlQuery')
    assert hasattr(xml, 'XmlDiff')
    assert hasattr(xml, 'parse_xml')
    assert hasattr(xml, 'find_element')
    assert hasattr(xml, 'cached_xpath')

# Test compatibility layer
def test_xml_compatibility_layer():
    """Test that the consolidated XML package works properly."""
    # Now that we've fully migrated to the consolidated module, test it directly
    from panflow.core.xml import base, builder, cache, diff, query

    # Check that we can access key functions and classes from submodules
    assert hasattr(base, 'parse_xml')
    assert hasattr(base, 'find_element')

    assert hasattr(builder, 'XmlNode')
    assert hasattr(builder, 'XmlBuilder')

    assert hasattr(cache, 'cached_xpath')
    assert hasattr(cache, 'clear_xpath_cache')

    assert hasattr(diff, 'XmlDiff')
    assert hasattr(diff, 'DiffItem')

    assert hasattr(query, 'XmlQuery')

# Test basic XML functionality
def test_xml_functionality():
    """Test that basic XML functionality works correctly."""
    from panflow.core.xml import parse_xml_string, find_element, XmlNode
    
    # Create a simple XML document
    xml_string = """
    <config>
        <settings>
            <option name="test">value</option>
        </settings>
    </config>
    """
    
    # Parse the XML
    tree, root = parse_xml_string(xml_string)
    
    # Find an element
    option = find_element(root, "//option[@name='test']")
    assert option is not None
    assert option.tag == "option"
    assert option.get("name") == "test"
    assert option.text == "value"
    
    # Test XmlNode
    node = XmlNode(root)
    assert node.tag == "config"
    
    option_node = node.find("//option[@name='test']")
    assert option_node is not None
    assert option_node.get_attribute("name") == "test"
    assert option_node.text == "value"

# Test that imports from core still work
def test_core_imports():
    """Test that imports from the core package still work."""
    from panflow.core import (
        parse_xml, find_element, XmlNode, XmlBuilder, XmlQuery, XmlDiff
    )
    
    # Check that these objects exist
    assert callable(parse_xml)
    assert callable(find_element)
    assert hasattr(XmlNode, 'from_string')
    assert hasattr(XmlBuilder, 'build')
    assert hasattr(XmlQuery, 'find')
    assert hasattr(XmlDiff, 'compare')