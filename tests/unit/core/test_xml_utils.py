"""
Tests for the XML utilities functionality.
"""

import pytest
from lxml import etree

from panflow.core.xml_utils import (
    parse_xml_string,
    find_element,
    find_elements,
    element_exists,
    clone_element,
    merge_elements,
    element_to_dict,
    dict_to_element,
)


def test_parse_xml_string():
    """Test parsing XML string."""
    xml_str = "<root><child>test</child></root>"
    tree, root = parse_xml_string(xml_str)

    assert tree is not None
    assert root is not None
    assert root.tag == "root"
    assert len(root) == 1
    assert root[0].tag == "child"
    assert root[0].text == "test"


def test_find_element_exists(sample_xml_element):
    """Test finding an element that exists."""
    element = find_element(sample_xml_element, ".//address/entry")

    assert element is not None
    assert element.get("name") == "test-address"
    assert element.find("ip-netmask").text == "192.168.1.1/32"


def test_find_element_not_exists(sample_xml_element):
    """Test finding an element that doesn't exist."""
    element = find_element(sample_xml_element, ".//nonexistent")
    assert element is None


def test_find_elements(sample_xml_element):
    """Test finding multiple elements."""
    elements = find_elements(sample_xml_element, ".//tag/member")

    assert elements is not None
    assert len(elements) == 1
    assert elements[0].text == "test-tag"


def test_find_elements_not_exists(sample_xml_element):
    """Test finding elements that don't exist."""
    elements = find_elements(sample_xml_element, ".//nonexistent")
    assert elements == []


def test_element_exists(sample_xml_element):
    """Test checking if an element exists."""
    assert element_exists(sample_xml_element, ".//address/entry") is True
    assert element_exists(sample_xml_element, ".//nonexistent") is False


def test_clone_element(sample_xml_element):
    """Test cloning an XML element."""
    address = find_element(sample_xml_element, ".//address/entry")
    clone = clone_element(address)

    # Should be equal but not the same object
    assert etree.tostring(clone) == etree.tostring(address)
    assert clone is not address


def test_merge_elements():
    """Test merging XML elements."""
    # Create source and target elements
    source_str = """
    <entry name="test">
      <field1>value1</field1>
      <field2>source-value</field2>
    </entry>
    """
    target_str = """
    <entry name="test">
      <field2>target-value</field2>
      <field3>value3</field3>
    </entry>
    """
    source = etree.fromstring(source_str)
    target = etree.fromstring(target_str)

    # Merge source into target
    result = merge_elements(source, target)

    # Check the result
    assert result.get("name") == "test"
    assert find_element(result, "./field1").text == "value1"
    assert find_element(result, "./field2").text == "source-value"  # Source overwrites
    assert find_element(result, "./field3").text == "value3"


def test_element_to_dict(sample_xml_element):
    """Test converting an XML element to a dictionary."""
    address = find_element(sample_xml_element, ".//address/entry")
    result = element_to_dict(address)

    assert result["@name"] == "test-address"
    assert "ip-netmask" in result
    assert "description" in result
    assert "tag" in result
    assert "member" in result["tag"]


def test_dict_to_element():
    """Test converting a dictionary to an XML element."""
    data = {
        "@name": "test-address",
        "ip-netmask": {"#text": "192.168.1.1/32"},
        "description": {"#text": "Test address object"},
        "tag": {"member": {"#text": "test-tag"}},
    }

    element = dict_to_element("entry", data)

    assert element.tag == "entry"
    assert element.get("name") == "test-address"
    assert element.find("ip-netmask").text == "192.168.1.1/32"
    assert element.find("description").text == "Test address object"
    assert element.find("tag/member").text == "test-tag"
