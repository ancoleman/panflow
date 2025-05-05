"""
Tests for the XML query functionality.
"""

import pytest
from lxml import etree

from panflow.core import XmlQuery, XmlNode, XPathError


class TestXmlQuery:
    """Tests for the XmlQuery class."""
    
    def test_from_node(self):
        """Test creating a query from an XmlNode."""
        node = XmlNode.create('root')
        query = XmlQuery.from_node(node)
        
        assert query.count() == 1
        assert isinstance(query.first(), XmlNode)
        assert query.first().tag == 'root'
        
    def test_from_tree(self, sample_xml_tree):
        """Test creating a query from an ElementTree."""
        query = XmlQuery.from_tree(sample_xml_tree)
        
        assert query.count() == 1
        assert isinstance(query.first(), XmlNode)
        assert query.first().tag == 'config'
        
    def test_find(self, sample_xml_element):
        """Test finding elements using XPath."""
        # Create a query with the root element
        query = XmlQuery([sample_xml_element])
        
        # Find address entries
        result = query.find('.//address/entry')
        
        assert result.count() == 1
        assert result.first().get_attribute('name') == 'test-address'
        
        # Find tag members
        result = query.find('.//tag/member')
        
        assert result.count() == 1
        assert result.first().text == 'test-tag'
        
        # Find non-existent elements
        result = query.find('.//nonexistent')
        
        assert result.count() == 0
        assert result.first() is None
        
    def test_filter(self, panorama_xml_tree):
        """Test filtering elements using XPath predicates."""
        # Create a query with all address entries
        query = XmlQuery.from_tree(panorama_xml_tree).find('.//address/entry')
        
        assert query.count() == 2  # Should find both addresses
        
        # Filter by name attribute
        result = query.filter('@name="test-address"')
        
        assert result.count() == 1
        assert result.first().get_attribute('name') == 'test-address'
        
        # Filter by element content
        result = query.filter('ip-netmask="10.0.0.1/32"')
        
        assert result.count() == 1
        assert result.first().get_attribute('name') == 'shared-address'
        
    def test_helper_filters(self, sample_xml_element):
        """Test helper filter methods."""
        query = XmlQuery([sample_xml_element])
        
        # Test has_attribute
        result = query.find('.//entry').has_attribute('name', 'test-address')
        assert result.count() == 1
        
        # Test has_text
        result = query.find('.//ip-netmask').has_text('192.168.1.1/32')
        assert result.count() == 1
        
        # Test has_text_containing
        result = query.find('.//ip-netmask').has_text_containing('192.168')
        assert result.count() == 1
        
        # Test has_name (special case for PAN-OS XML)
        result = query.find('.//entry').has_name('test-address')
        assert result.count() == 1
        
        # Test has_child
        result = query.find('.//entry').has_child('ip-netmask')
        assert result.count() == 1
        
        # Test has_descendant
        result = query.find('.//entry').has_descendant('member')
        assert result.count() == 1
        
    def test_accessors(self, sample_xml_element):
        """Test accessor methods."""
        query = XmlQuery([sample_xml_element]).find('.//address/entry')
        
        # Test first
        assert query.first().tag == 'entry'
        
        # Test last (same as first in this case)
        assert query.last().tag == 'entry'
        
        # Test at
        assert query.at(0).tag == 'entry'
        assert query.at(999) is None  # Out of bounds
        
        # Test count
        assert query.count() == 1
        
        # Test nodes
        assert len(query.nodes()) == 1
        assert all(isinstance(node, XmlNode) for node in query.nodes())
        
        # Test text (gets all text values)
        text_values = query.find('.//description').text()
        assert len(text_values) == 1
        assert text_values[0] == 'Test address object'
        
        # Test attribute (gets all attribute values)
        attr_values = query.attribute('name')
        assert len(attr_values) == 1
        assert attr_values[0] == 'test-address'
        
        # Create a simple test for values method
        test_el1 = etree.Element('test', {'name': 'test-name'})
        test_el2 = etree.Element('test')
        test_el2.text = 'test-text'
        test_el3 = etree.Element('test')  # No name or text
        
        query_test = XmlQuery([test_el1, test_el2, test_el3])
        values = query_test.values()
        
        assert 'test-name' in values  # Should include name attribute
        assert 'test-text' in values  # Should include text
        assert '' in values  # Should include empty string for elements with no name or text
        
    def test_iteration(self, sample_xml_element):
        """Test iteration over query results."""
        query = XmlQuery([sample_xml_element]).find('.//entry|.//description')
        
        # Test __iter__
        nodes = list(query)
        assert len(nodes) == 2
        assert all(isinstance(node, XmlNode) for node in nodes)
        
        # Test __len__
        assert len(query) == 2
        
        # Test __bool__
        assert bool(query) is True
        assert bool(XmlQuery([])) is False
        
    def test_each(self, sample_xml_element):
        """Test each method for iteration with a callback."""
        query = XmlQuery([sample_xml_element]).find('.//ip-netmask|.//description')
        
        collected = []
        def collect_text(node):
            collected.append(node.text)
            
        query.each(collect_text)
        
        assert len(collected) == 2
        assert '192.168.1.1/32' in collected
        assert 'Test address object' in collected
        
    def test_map(self, sample_xml_element):
        """Test map method for transforming elements."""
        query = XmlQuery([sample_xml_element]).find('.//ip-netmask|.//description')
        
        # Map to get the text of each element
        result = query.map(lambda node: node.text)
        
        assert len(result) == 2
        assert '192.168.1.1/32' in result
        assert 'Test address object' in result
        
    def test_to_dict(self, sample_xml_element):
        """Test to_dict method for converting elements to dictionaries."""
        query = XmlQuery([sample_xml_element]).find('.//entry')
        
        result = query.to_dict()
        
        assert len(result) == 1
        assert result[0]['@name'] == 'test-address'
        assert result[0]['ip-netmask']['#text'] == '192.168.1.1/32'
        assert result[0]['description']['#text'] == 'Test address object'
        assert result[0]['tag']['member']['#text'] == 'test-tag'