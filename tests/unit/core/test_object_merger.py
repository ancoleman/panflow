"""
Unit tests for the ObjectMerger class.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock, call

from panflow.core.object_merger import ObjectMerger
from panflow.core.conflict_resolver import ConflictStrategy


@pytest.fixture
def simple_source_config():
    """
    Create a simple source configuration with some address objects.
    """
    xml = '''
    <config version="10.2.0">
        <shared>
            <address>
                <entry name="web-server">
                    <ip-netmask>192.168.1.100/32</ip-netmask>
                    <description>Web server</description>
                    <tag>
                        <member>web</member>
                    </tag>
                </entry>
                <entry name="db-server">
                    <ip-netmask>192.168.1.101/32</ip-netmask>
                    <description>Database server</description>
                    <tag>
                        <member>db</member>
                    </tag>
                </entry>
            </address>
            <address-group>
                <entry name="servers">
                    <static>
                        <member>web-server</member>
                        <member>db-server</member>
                    </static>
                    <description>All servers</description>
                </entry>
            </address-group>
            <tag>
                <entry name="web">
                    <color>#FF0000</color>
                </entry>
                <entry name="db">
                    <color>#0000FF</color>
                </entry>
            </tag>
        </shared>
    </config>
    '''
    return etree.ElementTree(etree.fromstring(xml))


@pytest.fixture
def simple_target_config():
    """
    Create a simple target configuration with a device group.
    """
    xml = '''
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG1">
                        <address>
                        </address>
                        <address-group>
                        </address-group>
                        <tag>
                        </tag>
                    </entry>
                </device-group>
            </entry>
        </devices>
        <shared>
            <address>
            </address>
            <tag>
            </tag>
        </shared>
    </config>
    '''
    return etree.ElementTree(etree.fromstring(xml))


def test_init_object_merger():
    """Test ObjectMerger initialization."""
    source_tree = etree.ElementTree(etree.Element("config"))
    target_tree = etree.ElementTree(etree.Element("config"))
    
    merger = ObjectMerger(
        source_tree,
        target_tree,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    assert merger.source_tree == source_tree
    assert merger.target_tree == target_tree
    assert merger.source_device_type == "panorama"
    assert merger.target_device_type == "panorama"
    assert merger.source_version == "10.2"
    assert merger.target_version == "10.2"
    assert merger.merged_objects == []
    assert merger.skipped_objects == []
    assert merger.referenced_objects == []


def test_copy_object_simple(simple_source_config, simple_target_config):
    """Test copying a simple object from source to target."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Copy web-server from shared to DG1
    result = merger.copy_object(
        "address",
        "web-server",
        "shared",
        "device_group",
        skip_if_exists=True,
        copy_references=False,
        target_device_group="DG1"
    )
    
    assert result is True
    assert len(merger.merged_objects) == 1
    assert merger.merged_objects[0] == ("address", "web-server")
    
    # Verify the object was copied to the target
    xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='web-server']"
    elements = simple_target_config.xpath(xpath)
    
    assert len(elements) == 1
    assert elements[0].find('./ip-netmask').text == "192.168.1.100/32"
    assert elements[0].find('./description').text == "Web server"


def test_copy_object_with_references(simple_source_config, simple_target_config):
    """Test copying an object with references from source to target."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Mock the _copy_related_tags method to check if it's called
    with patch.object(merger, '_copy_related_tags') as mock_copy_tags:
        # Copy web-server from shared to DG1 with references
        result = merger.copy_object(
            "address",
            "web-server",
            "shared",
            "device_group",
            skip_if_exists=True,
            copy_references=True,
            target_device_group="DG1"
        )
        
        assert result is True
        assert len(merger.merged_objects) == 1
        assert merger.merged_objects[0] == ("address", "web-server")
        
        # Verify _copy_related_tags was called
        mock_copy_tags.assert_called_once()


def test_copy_address_group_with_members(simple_source_config, simple_target_config):
    """Test copying an address group with its members."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Mock _copy_group_members to track calls
    with patch.object(merger, '_copy_group_members') as mock_copy_members:
        # Copy servers group from shared to DG1 with references
        result = merger.copy_object(
            "address_group",
            "servers",
            "shared",
            "device_group",
            skip_if_exists=True,
            copy_references=True,
            target_device_group="DG1"
        )
        
        assert result is True
        assert len(merger.merged_objects) == 1
        assert merger.merged_objects[0] == ("address_group", "servers")
        
        # Verify _copy_group_members was called
        mock_copy_members.assert_called_once()


def test_copy_object_nonexistent(simple_source_config, simple_target_config):
    """Test trying to copy a nonexistent object."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Try to copy nonexistent object
    result = merger.copy_object(
        "address",
        "nonexistent",
        "shared",
        "device_group",
        skip_if_exists=True,
        copy_references=False,
        target_device_group="DG1"
    )
    
    assert result is False
    assert len(merger.merged_objects) == 0
    assert len(merger.skipped_objects) == 1
    assert merger.skipped_objects[0] == ("address", "nonexistent", "Not found in source")


def test_copy_object_conflict_skip(simple_source_config, simple_target_config):
    """Test copying an object that already exists with skip_if_exists=True."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # First, copy the object successfully
    result1 = merger.copy_object(
        "address",
        "web-server",
        "shared",
        "device_group",
        skip_if_exists=True,
        copy_references=False,
        target_device_group="DG1"
    )
    
    assert result1 is True
    
    # Reset the merger's tracking lists
    merger.merged_objects = []
    merger.skipped_objects = []
    
    # Mock ConflictResolver to track calls
    with patch.object(merger.conflict_resolver, 'resolve_conflict') as mock_resolve:
        mock_resolve.return_value = (False, None, "Skipped due to conflict")
        
        # Try to copy the same object again
        result2 = merger.copy_object(
            "address",
            "web-server",
            "shared",
            "device_group",
            skip_if_exists=True,
            copy_references=False,
            target_device_group="DG1"
        )
        
        assert result2 is False
        assert len(merger.merged_objects) == 0
        assert len(merger.skipped_objects) == 1
        mock_resolve.assert_called_once()


def test_copy_object_conflict_overwrite(simple_source_config, simple_target_config):
    """Test copying an object that already exists with overwrite conflict strategy."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # First, copy the object successfully
    result1 = merger.copy_object(
        "address",
        "web-server",
        "shared",
        "device_group",
        skip_if_exists=True,
        copy_references=False,
        target_device_group="DG1"
    )
    
    assert result1 is True
    
    # Reset the merger's tracking lists
    merger.merged_objects = []
    merger.skipped_objects = []
    
    # Mock ConflictResolver to simulate successful overwrite
    with patch.object(merger.conflict_resolver, 'resolve_conflict') as mock_resolve:
        mock_resolve.return_value = (True, None, "Overwritten successfully")
        
        # Try to copy the same object again with overwrite
        result2 = merger.copy_object(
            "address",
            "web-server",
            "shared",
            "device_group",
            skip_if_exists=False,  # Don't skip
            copy_references=False,
            conflict_strategy=ConflictStrategy.OVERWRITE,
            target_device_group="DG1"
        )
        
        assert result2 is True
        assert len(merger.merged_objects) == 1
        assert len(merger.skipped_objects) == 0
        mock_resolve.assert_called_once()


def test_copy_objects_by_name(simple_source_config, simple_target_config):
    """Test copying multiple objects by name."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Copy both address objects by name
    object_names = ["web-server", "db-server"]
    copied, total = merger.copy_objects(
        "address",
        "shared",
        "device_group",
        object_names=object_names,
        skip_if_exists=True,
        copy_references=False,
        target_device_group="DG1"
    )
    
    assert copied == 2
    assert total == 2
    assert len(merger.merged_objects) == 2


def test_copy_objects_by_criteria(simple_source_config, simple_target_config):
    """Test copying objects that match criteria."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Copy address objects with web tag
    criteria = {"has-tag": "web"}
    
    # Mock _matches_criteria to control which objects match
    with patch.object(merger, '_matches_criteria') as mock_matches:
        # Make only web-server match the criteria
        mock_matches.side_effect = lambda obj, crit: obj.get("name") == "web-server"
        
        copied, total = merger.copy_objects(
            "address",
            "shared",
            "device_group",
            filter_criteria=criteria,
            skip_if_exists=True,
            copy_references=False,
            target_device_group="DG1"
        )
        
        assert copied == 1
        assert total == 1
        assert mock_matches.call_count > 0


def test_merge_all_objects(simple_source_config, simple_target_config):
    """Test merging objects of multiple types."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Merge address, address_group, and tag objects
    object_types = ["address", "address_group", "tag"]
    
    # Mock copy_objects to track calls and return predictable results
    with patch.object(merger, 'copy_objects') as mock_copy:
        mock_copy.side_effect = [
            (2, 2),  # address: 2 copied out of 2
            (1, 1),  # address_group: 1 copied out of 1
            (2, 2),  # tag: 2 copied out of 2
        ]
        
        results = merger.merge_all_objects(
            object_types,
            "shared",
            "device_group",
            skip_if_exists=True,
            copy_references=True,
            target_device_group="DG1"
        )
        
        assert mock_copy.call_count == 3
        assert results == {
            "address": (2, 2),
            "address_group": (1, 1),
            "tag": (2, 2)
        }


def test_copy_object_with_dependencies(simple_source_config, simple_target_config):
    """Test copying an object with all its dependencies."""
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.2",
        "10.2"
    )
    
    # Mock analyze_dependencies and copy_object to track calls
    with patch.object(merger, 'analyze_dependencies') as mock_analyze:
        with patch.object(merger, 'copy_object') as mock_copy:
            # Set up mock dependencies
            mock_analyze.return_value = {
                "depends_on": [("tag", "web")],
                "referenced_by": [("address_group", "servers")]
            }
            mock_copy.return_value = True
            
            # Copy web-server with dependencies
            result, dependencies = merger.copy_object_with_dependencies(
                "address",
                "web-server",
                "shared",
                "device_group",
                include_referenced_by=True,
                skip_if_exists=True,
                target_device_group="DG1"
            )
            
            assert result is True
            assert dependencies == mock_analyze.return_value
            assert mock_copy.call_count == 3  # tag, address, address_group


def test_version_specific_attributes(simple_source_config, simple_target_config):
    """Test handling of version-specific attributes when versions differ."""
    # Create merger with different source and target versions
    merger = ObjectMerger(
        simple_source_config,
        simple_target_config,
        "panorama",
        "panorama",
        "10.1",  # Source version
        "10.2"   # Target version
    )
    
    # Mock _handle_version_specific_attributes to verify it's called
    with patch.object(merger, '_handle_version_specific_attributes') as mock_handle:
        mock_handle.return_value = etree.Element("entry", name="web-server")
        
        result = merger.copy_object(
            "address",
            "web-server",
            "shared",
            "device_group",
            skip_if_exists=True,
            copy_references=False,
            target_device_group="DG1"
        )
        
        assert result is True
        mock_handle.assert_called_once()