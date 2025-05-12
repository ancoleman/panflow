"""
Tests for the XML builder functionality.
"""

import pytest
from lxml import etree

from panflow.core import XmlNode, XmlBuilder, XPathBuilder, XPathError


class TestXmlNode:
    """Tests for the XmlNode class."""

    def test_create(self):
        """Test creating a new XmlNode."""
        node = XmlNode.create("test", {"attr": "value"}, "test text")

        assert node.tag == "test"
        assert node.text == "test text"
        assert node.attributes == {"attr": "value"}

    def test_from_string(self):
        """Test creating a node from an XML string."""
        xml_str = "<root><child>test</child></root>"
        node = XmlNode.from_string(xml_str)

        assert node.tag == "root"
        assert len(node.children) == 1
        assert node.children[0].tag == "child"
        assert node.children[0].text == "test"

    def test_properties(self):
        """Test node properties."""
        node = XmlNode.create("test", {"attr1": "value1", "attr2": "value2"}, "test text")

        # Test property getters
        assert node.tag == "test"
        assert node.text == "test text"
        assert node.attributes == {"attr1": "value1", "attr2": "value2"}

        # Test property setters
        node.text = "new text"
        assert node.text == "new text"

        node.tail = "tail text"
        assert node.tail == "tail text"

    def test_attribute_methods(self):
        """Test attribute methods."""
        node = XmlNode.create("test")

        # Test setting attributes
        node.set_attribute("attr1", "value1")
        assert node.get_attribute("attr1") == "value1"

        # Test default value
        assert node.get_attribute("nonexistent", "default") == "default"

        # Test deleting attributes
        node.delete_attribute("attr1")
        assert node.get_attribute("attr1") is None

    def test_child_methods(self, sample_xml_element):
        """Test child node methods."""
        node = XmlNode(sample_xml_element)

        # Test getting children
        children = node.children
        assert len(children) > 0

        # Test getting a specific child
        shared = node.child("shared")
        assert shared is not None
        assert shared.tag == "shared"

        # Test adding a child
        new_child = node.add_child("new-child", {"test": "value"}, "child text")
        assert new_child.tag == "new-child"
        assert new_child.text == "child text"
        assert new_child.get_attribute("test") == "value"

        # Test appending a child
        another_child = XmlNode.create("another-child")
        node.append(another_child)
        assert node.child("another-child") is not None

        # Test removing a child
        node.remove_child(new_child)
        assert node.child("new-child") is None

    def test_find_methods(self, sample_xml_element):
        """Test find methods."""
        node = XmlNode(sample_xml_element)

        # Test find
        address = node.find(".//address/entry")
        assert address is not None
        assert address.get_attribute("name") == "test-address"

        # Test find_all
        members = node.find_all(".//tag/member")
        assert len(members) == 1
        assert members[0].text == "test-tag"

        # Test exists
        assert node.exists(".//address/entry") is True
        assert node.exists(".//nonexistent") is False

    def test_xpath(self, sample_xml_element):
        """Test XPath execution."""
        node = XmlNode(sample_xml_element)

        # Test simple XPath
        results = node.xpath(".//address/entry")
        assert len(results) == 1
        assert isinstance(results[0], XmlNode)

        # Test attribute XPath
        results = node.xpath(".//@name")
        assert "test-address" in results

        # Test invalid XPath
        with pytest.raises(XPathError):
            node.xpath("//[invalid]")

    def test_to_string(self):
        """Test converting a node to a string."""
        node = XmlNode.create("root")
        node.add_child("child", text="test")

        xml_str = node.to_string(pretty_print=False, include_declaration=False)
        assert "<root><child>test</child></root>" == xml_str.strip()

    def test_to_dict(self, sample_xml_element):
        """Test converting a node to a dictionary."""
        node = XmlNode(sample_xml_element)
        address = node.find(".//address/entry")

        result = address.to_dict()

        assert result["@name"] == "test-address"
        assert result["ip-netmask"]["#text"] == "192.168.1.1/32"
        assert result["description"]["#text"] == "Test address object"
        assert result["tag"]["member"]["#text"] == "test-tag"

    def test_equality(self):
        """Test node equality."""
        node1 = XmlNode.create("test", {"attr": "value"}, "text")
        node2 = XmlNode.create("test", {"attr": "value"}, "text")
        node3 = XmlNode.create("different", {"attr": "value"}, "text")

        assert node1 == node2
        assert node1 != node3
        assert node1 != "not a node"


class TestXmlBuilder:
    """Tests for the XmlBuilder class."""

    def test_basic_build(self):
        """Test building a basic XML structure."""
        builder = XmlBuilder("root", {"version": "1.0"})
        builder.add("child1", text="text1")
        builder.add("child2", {"attr": "value"}, "text2")

        root = builder.build()

        assert root.tag == "root"
        assert root.get_attribute("version") == "1.0"
        assert len(root.children) == 2
        assert root.children[0].tag == "child1"
        assert root.children[0].text == "text1"
        assert root.children[1].tag == "child2"
        assert root.children[1].text == "text2"
        assert root.children[1].get_attribute("attr") == "value"

    def test_nested_build(self):
        """Test building a nested XML structure."""
        builder = XmlBuilder("root")

        # Add a nested structure
        builder.into("parent")
        builder.add("child1", text="text1")
        builder.add("child2", text="text2")
        builder.up()
        builder.add("sibling", text="sibling text")

        root = builder.build()

        assert len(root.children) == 2
        parent = root.child("parent")
        assert parent is not None
        assert len(parent.children) == 2
        assert parent.children[0].tag == "child1"
        assert parent.children[1].tag == "child2"
        sibling = root.child("sibling")
        assert sibling is not None
        assert sibling.text == "sibling text"

    def test_attributes_and_text(self):
        """Test setting attributes and text."""
        builder = XmlBuilder("root")

        # Use the with_ methods
        builder.into("element")
        builder.with_text("element text")
        builder.with_attribute("attr1", "value1")
        builder.with_attribute("attr2", "value2")

        root = builder.build()
        element = root.child("element")

        assert element.text == "element text"
        assert element.get_attribute("attr1") == "value1"
        assert element.get_attribute("attr2") == "value2"

    def test_navigation(self):
        """Test builder navigation."""
        builder = XmlBuilder("root")

        # Navigate into multiple levels
        builder.into("level1")
        builder.into("level2")
        builder.into("level3")

        # Navigate up one level
        builder.up()
        builder.add("level3sibling")

        # Navigate to root
        builder.root_up()
        builder.add("rootchild")

        root = builder.build()

        # Verify the structure
        level1 = root.child("level1")
        assert level1 is not None
        level2 = level1.child("level2")
        assert level2 is not None
        level3 = level2.child("level3")
        assert level3 is not None
        level3sibling = level2.child("level3sibling")
        assert level3sibling is not None
        rootchild = root.child("rootchild")
        assert rootchild is not None

    def test_up_at_root(self):
        """Test up() when already at root."""
        builder = XmlBuilder("root")

        with pytest.raises(ValueError):
            builder.up()

    def test_to_string(self):
        """Test converting the builder result to a string."""
        builder = XmlBuilder("root")
        builder.add("child", text="text")

        xml_str = builder.to_string(pretty_print=False, include_declaration=False)
        assert "<root><child>text</child></root>" == xml_str.strip()


class TestXPathBuilder:
    """Tests for the XPathBuilder class."""

    def test_basic_path(self):
        """Test building a basic XPath."""
        builder = XPathBuilder()
        builder.root().element("config").child("devices")

        assert builder.build() == "/config/devices"

    def test_anywhere_path(self):
        """Test building an 'anywhere' XPath."""
        builder = XPathBuilder()
        builder.anywhere().element("entry")

        assert builder.build() == "//entry"

    def test_attributes(self):
        """Test adding attribute selectors."""
        builder = XPathBuilder()
        builder.root().element("config").child("devices").child("entry").with_attribute(
            "name", "localhost"
        )

        assert builder.build() == "/config/devices/entry[@name='localhost']"

        # Test with_name (common in PAN-OS XML)
        builder = XPathBuilder()
        builder.root().element("address").child("entry").with_name("test-address")

        assert builder.build() == "/address/entry[@name='test-address']"

    def test_predicates(self):
        """Test adding predicates."""
        builder = XPathBuilder()
        builder.root().element("config").descendant("entry").with_text("test")

        assert builder.build() == "/config//entry[text()='test']"

        # Test contains_text
        builder = XPathBuilder()
        builder.root().element("config").descendant("description").contains_text("test")

        assert builder.build() == "/config//description[contains(text(),'test')]"

        # Test custom predicate
        builder = XPathBuilder()
        builder.root().element("config").descendant("entry").where("position() = 1")

        assert builder.build() == "/config//entry[position() = 1]"

    def test_navigation(self):
        """Test navigation in XPath."""
        builder = XPathBuilder()
        builder.root().element("config").child("devices").child("entry").parent()

        assert builder.build() == "/config/devices/entry/.."

    def test_or_paths(self):
        """Test building XPath with OR."""
        builder = XPathBuilder()
        builder.root().element("config").child("shared").child("address").or_element("service")

        assert builder.build() == "/config/shared/address|//service"
