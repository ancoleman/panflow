"""
Unit tests for the object finder functionality.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock

from panflow.core.object_finder import (
    ObjectLocation,
    find_objects_by_name,
    find_objects_by_value,
    find_all_locations,
    find_duplicate_names,
    find_duplicate_values,
)


class TestObjectLocation:
    """Tests for the ObjectLocation class."""

    def test_init(self):
        """Test initialization of ObjectLocation."""
        # Create a mock element
        element = etree.Element("entry", name="test-object")
        etree.SubElement(element, "ip-netmask").text = "10.0.0.0/24"
        
        # Create ObjectLocation instance
        obj_loc = ObjectLocation(
            "address",
            "test-object",
            "device_group",
            element,
            device_group="DG1"
        )
        
        # Verify attributes
        assert obj_loc.object_type == "address"
        assert obj_loc.object_name == "test-object"
        assert obj_loc.context_type == "device_group"
        assert obj_loc.element == element
        assert obj_loc.context_params == {"device_group": "DG1"}
        
        # Verify properties were extracted
        assert "ip-netmask" in obj_loc.properties
        assert obj_loc.properties["ip-netmask"] == "10.0.0.0/24"
    
    def test_get_context_display(self):
        """Test get_context_display method."""
        element = etree.Element("entry", name="test-object")
        
        # Test shared context
        obj_loc = ObjectLocation("address", "test-object", "shared", element)
        assert obj_loc.get_context_display() == "shared"
        
        # Test device_group context
        obj_loc = ObjectLocation("address", "test-object", "device_group", element, device_group="DG1")
        assert obj_loc.get_context_display() == "device group 'DG1'"
        
        # Test vsys context
        obj_loc = ObjectLocation("address", "test-object", "vsys", element, vsys="vsys1")
        assert obj_loc.get_context_display() == "vsys 'vsys1'"
        
        # Test template context
        obj_loc = ObjectLocation("address", "test-object", "template", element, template="T1")
        assert obj_loc.get_context_display() == "template 'T1'"
        
        # Test unknown context
        obj_loc = ObjectLocation("address", "test-object", "unknown", element)
        assert obj_loc.get_context_display() == "unknown"
    
    def test_str(self):
        """Test string representation."""
        element = etree.Element("entry", name="test-object")
        obj_loc = ObjectLocation("address", "test-object", "device_group", element, device_group="DG1")
        assert str(obj_loc) == "address 'test-object' in device group 'DG1'"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        # Create a mock element
        element = etree.Element("entry", name="test-object")
        etree.SubElement(element, "ip-netmask").text = "10.0.0.0/24"
        
        obj_loc = ObjectLocation("address", "test-object", "device_group", element, device_group="DG1")
        
        # Mock get_xpath to return a predictable path
        obj_loc.get_xpath = lambda: "/path/to/element"
        
        # Test to_dict
        result = obj_loc.to_dict()
        
        assert result["object_type"] == "address"
        assert result["object_name"] == "test-object"
        assert result["context_type"] == "device_group"
        assert result["context_params"] == {"device_group": "DG1"}
        assert result["xpath"] == "/path/to/element"
        assert "ip-netmask" in result["properties"]
        assert result["properties"]["ip-netmask"] == "10.0.0.0/24"


@patch("panflow.core.object_finder.xpath_search")
@patch("panflow.core.object_finder.get_object_xpath")
class TestFindObjectsByName:
    """Tests for find_objects_by_name function."""
    
    def test_find_objects_by_name_panorama(self, mock_get_xpath, mock_xpath_search):
        """Test finding objects by name in a Panorama configuration."""
        # Mock the XML tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Mock device groups
        mock_xpath_search.side_effect = lambda tree, xpath: (
            [etree.Element("entry", name="DG1"), etree.Element("entry", name="DG2")]
            if "device-group" in xpath
            else [etree.Element("entry", name="T1")]
            if "template" in xpath
            else [etree.Element("entry", name="test-object")]
        )
        
        # Mock get_object_xpath to return a path
        mock_get_xpath.return_value = "/path/to/object"
        
        # Call the function
        results = find_objects_by_name(tree, "address", "test-object", "panorama", "10.1.0")
        
        # Expect calls for shared, device groups, and templates
        assert mock_get_xpath.call_count == 4  # shared + 2 device groups + 1 template
        assert len(results) == 4  # One result for each context
        
        # Check contexts
        contexts = {result.context_type for result in results}
        assert "shared" in contexts
        assert "device_group" in contexts
        assert "template" in contexts
    
    def test_find_objects_by_name_firewall(self, mock_get_xpath, mock_xpath_search):
        """Test finding objects by name in a firewall configuration."""
        # Mock the XML tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Mock vsys
        mock_xpath_search.side_effect = lambda tree, xpath: (
            [etree.Element("entry", name="vsys1"), etree.Element("entry", name="vsys2")]
            if "vsys" in xpath
            else [etree.Element("entry", name="test-object")]
        )
        
        # Mock get_object_xpath to return a path
        mock_get_xpath.return_value = "/path/to/object"
        
        # Call the function
        results = find_objects_by_name(tree, "address", "test-object", "firewall", "10.1.0")
        
        # Expect calls for each vsys
        assert mock_get_xpath.call_count == 2  # 2 vsys
        assert len(results) == 2  # One result for each vsys
        
        # Check contexts
        contexts = {result.context_type for result in results}
        assert "vsys" in contexts


@patch("panflow.core.object_finder.xpath_search")
@patch("panflow.core.object_finder.get_object_xpath")
class TestFindObjectsByValue:
    """Tests for find_objects_by_value function."""
    
    def test_find_objects_by_value(self, mock_get_xpath, mock_xpath_search):
        """Test finding objects by value criteria."""
        # Mock the XML tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Create mock elements that will match criteria
        element1 = etree.Element("entry", name="obj1")
        etree.SubElement(element1, "ip-netmask").text = "10.0.0.0/24"
        
        element2 = etree.Element("entry", name="obj2")
        etree.SubElement(element2, "ip-netmask").text = "10.0.0.0/24"
        
        # Create mock element that won't match criteria
        element3 = etree.Element("entry", name="obj3")
        etree.SubElement(element3, "ip-netmask").text = "192.168.1.0/24"
        
        # Mock xpath_search to return elements
        mock_xpath_search.side_effect = lambda tree, xpath: (
            [etree.Element("entry", name="DG1")]
            if "device-group" in xpath
            else [element1, element2, element3]
            if "/entry" in xpath
            else []
        )
        
        # Mock get_object_xpath to return a path
        mock_get_xpath.return_value = "/path/to/objects"
        
        # Set up the criteria
        value_criteria = {"ip-netmask": "10.0.0.0/24"}
        
        # Call the function
        results = find_objects_by_value(tree, "address", value_criteria, "panorama", "10.1.0")
        
        # We should get matches for the first two elements
        assert len(results) == 2
        
        # Check the names of the matching objects
        names = {result.object_name for result in results}
        assert "obj1" in names
        assert "obj2" in names
        assert "obj3" not in names


@patch("panflow.core.object_finder.xpath_search")
@patch("panflow.core.object_finder.get_object_xpath")
class TestFindAllLocations:
    """Tests for find_all_locations function."""
    
    def test_find_all_locations(self, mock_get_xpath, mock_xpath_search):
        """Test finding all object locations."""
        # Mock the XML tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Create mock elements
        address1 = etree.Element("entry", name="web-server")
        address2 = etree.Element("entry", name="db-server")
        service1 = etree.Element("entry", name="http")
        
        # Mock xpath_search to return contexts and elements
        mock_xpath_search.side_effect = lambda tree, xpath: (
            [etree.Element("entry", name="DG1")]
            if "device-group" in xpath and not "/entry" in xpath
            else [address1, address2]
            if "address" in xpath and "/entry" in xpath
            else [service1]
            if "service" in xpath and "/entry" in xpath
            else []
        )
        
        # Mock get_object_xpath to return a path
        mock_get_xpath.return_value = "/path/to/objects"
        
        # Call the function
        results = find_all_locations(tree, "panorama", "10.1.0")
        
        # Verify that we have results for different object types
        assert "address" in results
        assert "service" in results
        
        # Verify object names are correct
        assert "web-server" in results["address"]
        assert "db-server" in results["address"]
        assert "http" in results["service"]


@patch("panflow.core.object_finder.find_all_locations")
class TestFindDuplicateNames:
    """Tests for find_duplicate_names function."""
    
    def test_find_duplicate_names(self, mock_find_all_locations):
        """Test finding objects with duplicate names across contexts."""
        # Mock the tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Create ObjectLocation instances for objects with the same name in different contexts
        element1 = etree.Element("entry", name="web-server")
        element2 = etree.Element("entry", name="web-server")
        
        loc1 = ObjectLocation("address", "web-server", "shared", element1)
        loc2 = ObjectLocation("address", "web-server", "device_group", element2, device_group="DG1")
        
        # Create locations for non-duplicate objects
        element3 = etree.Element("entry", name="unique-server")
        loc3 = ObjectLocation("address", "unique-server", "shared", element3)
        
        # Mock find_all_locations to return our test data
        mock_find_all_locations.return_value = {
            "address": {
                "web-server": [loc1, loc2],
                "unique-server": [loc3]
            },
            "service": {}
        }
        
        # Call the function
        results = find_duplicate_names(tree, "panorama", "10.1.0")
        
        # Verify that we found the duplicate
        assert "address" in results
        assert "web-server" in results["address"]
        assert len(results["address"]["web-server"]) == 2
        
        # The unique object should not be in the results
        assert "unique-server" not in results["address"]


@patch("panflow.core.object_finder.find_all_locations")
class TestFindDuplicateValues:
    """Tests for find_duplicate_values function."""
    
    def test_find_duplicate_values_address(self, mock_find_all_locations):
        """Test finding address objects with duplicate values but different names."""
        # Mock the tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Create elements with the same value but different names
        element1 = etree.Element("entry", name="web-server-1")
        etree.SubElement(element1, "ip-netmask").text = "10.0.0.10"
        
        element2 = etree.Element("entry", name="web-server-2")
        etree.SubElement(element2, "ip-netmask").text = "10.0.0.10"
        
        # Create element with a unique value
        element3 = etree.Element("entry", name="db-server")
        etree.SubElement(element3, "ip-netmask").text = "10.0.0.20"
        
        # Create ObjectLocation instances
        loc1 = ObjectLocation("address", "web-server-1", "shared", element1)
        loc2 = ObjectLocation("address", "web-server-2", "shared", element2)
        loc3 = ObjectLocation("address", "db-server", "shared", element3)
        
        # Set up the ObjectLocation instances with properties
        loc1.properties["ip-netmask"] = "10.0.0.10"
        loc2.properties["ip-netmask"] = "10.0.0.10"
        loc3.properties["ip-netmask"] = "10.0.0.20"
        
        # Mock find_all_locations to return our test data
        mock_find_all_locations.return_value = {
            "address": {
                "web-server-1": [loc1],
                "web-server-2": [loc2],
                "db-server": [loc3]
            }
        }
        
        # Call the function
        results = find_duplicate_values(tree, "address", "panorama", "10.1.0")
        
        # Verify that we found the duplicate value
        assert "ip-netmask:10.0.0.10" in results
        assert len(results["ip-netmask:10.0.0.10"]) == 2
        
        # Verify the object names are correct
        names = {loc.object_name for loc in results["ip-netmask:10.0.0.10"]}
        assert "web-server-1" in names
        assert "web-server-2" in names
        
        # The unique value should not be in the results
        assert not any("10.0.0.20" in key for key in results.keys())
    
    def test_find_duplicate_values_service(self, mock_find_all_locations):
        """Test finding service objects with duplicate values but different names."""
        # Mock the tree
        tree = etree.ElementTree(etree.Element("config"))
        
        # Create elements with the same port but different names
        element1 = etree.Element("entry", name="web-http")
        tcp1 = etree.SubElement(element1, "tcp")
        etree.SubElement(tcp1, "port").text = "80"
        
        element2 = etree.Element("entry", name="web-alt")
        tcp2 = etree.SubElement(element2, "tcp")
        etree.SubElement(tcp2, "port").text = "80"
        
        # Create ObjectLocation instances
        loc1 = ObjectLocation("service", "web-http", "shared", element1)
        loc2 = ObjectLocation("service", "web-alt", "shared", element2)
        
        # Set up the ObjectLocation instances with properties
        loc1.properties["tcp"] = tcp1
        loc2.properties["tcp"] = tcp2
        
        # Mock find_all_locations to return our test data
        mock_find_all_locations.return_value = {
            "service": {
                "web-http": [loc1],
                "web-alt": [loc2]
            }
        }
        
        # Call the function
        results = find_duplicate_values(tree, "service", "panorama", "10.1.0")
        
        # Since we're mocking property extraction, we need to check if any results
        # were found rather than specific values
        assert len(results) > 0