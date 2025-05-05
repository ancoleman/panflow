"""
Integration tests for basic PANFlow workflows.
"""

import os
import pytest
import tempfile
from lxml import etree

from panflow.core.config_loader import load_config_from_file
from panflow.core.xml_utils import parse_xml_string, find_element, find_elements

@pytest.fixture
def sample_config_path(fixture_path):
    """Return the path to the sample configuration file."""
    return os.path.join(fixture_path, 'sample_config.xml')

def test_load_config(sample_config_path):
    """Test loading a configuration file."""
    tree, version = load_config_from_file(sample_config_path)
    
    assert tree is not None
    assert version == '10.1'
    
    # Check basic structure
    root = tree.getroot()
    assert root.tag == 'config'
    assert root.get('version') == '10.1.0'
    
    # Check if shared section exists
    shared = find_element(root, './shared')
    assert shared is not None
    
    # Check address objects in shared
    shared_addresses = find_elements(shared, './address/entry')
    assert len(shared_addresses) == 2
    address_names = [addr.get('name') for addr in shared_addresses]
    assert 'shared-address-1' in address_names
    assert 'shared-address-2' in address_names

def test_basic_object_operations(sample_config_path):
    """Test basic operations on objects in configuration."""
    from panflow import PANFlowConfig
    
    # Initialize with the sample config
    config = PANFlowConfig(config_file=sample_config_path)
    
    # Get all address objects in shared context
    addresses = config.get_objects('address', 'shared')
    assert len(addresses) >= 2
    assert 'shared-address-1' in addresses
    assert 'shared-address-2' in addresses
    
    # Get a specific address object
    address = config.get_object('address', 'shared-address-1', 'shared')
    assert address is not None
    assert address.get('name') == 'shared-address-1'
    
    # Test with temporary file for modifications
    with tempfile.NamedTemporaryFile(suffix='.xml') as tmp:
        tmp_path = tmp.name
        
        # Add a new address object
        properties = {'ip-netmask': '192.0.2.1/32', 'description': 'Test object'}
        success = config.add_object('address', 'test-new-address', properties, 'shared')
        assert success is True
        
        # Save the configuration
        config.save(tmp_path)
        
        # Reload and verify
        new_config = PANFlowConfig(config_file=tmp_path)
        new_addresses = new_config.get_objects('address', 'shared')
        assert 'test-new-address' in new_addresses
        
        # Get and check the new object
        new_address = new_config.get_object('address', 'test-new-address', 'shared')
        assert new_address is not None
        assert new_address.find('ip-netmask').text == '192.0.2.1/32'
        assert new_address.find('description').text == 'Test object'

def test_object_merge_workflow(sample_config_path):
    """Test merging objects between configurations."""
    from panflow.core.object_merger import ObjectMerger
    import tempfile
    
    # Load the original config
    tree, version = load_config_from_file(sample_config_path)
    
    # Create a target config with minimal structure
    target_xml = """
    <config version="10.1.0">
      <shared>
      </shared>
    </config>
    """
    target_tree, _ = parse_xml_string(target_xml)
    
    # Create an object merger
    merger = ObjectMerger(
        tree,
        target_tree,
        source_device_type="panorama",
        target_device_type="panorama",
        source_version=version,
        target_version=version
    )
    
    # Merge a single object
    result = merger.copy_object(
        'address',
        'shared-address-1',
        'shared',
        'shared',
        skip_if_exists=True,
        copy_references=True
    )
    
    assert result is True
    
    # Verify the object was copied
    target_root = target_tree.getroot()
    target_address = find_element(target_root, './shared/address/entry[@name="shared-address-1"]')
    assert target_address is not None
    assert target_address.find('ip-netmask').text == '172.16.1.1/32'
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.xml') as tmp:
        tmp_path = tmp.name
        target_tree.write(tmp_path, pretty_print=True)
        
        # Verify the saved file
        verify_tree, _ = load_config_from_file(tmp_path)
        verify_address = find_element(verify_tree, './shared/address/entry[@name="shared-address-1"]')
        assert verify_address is not None
        assert verify_address.find('ip-netmask').text == '172.16.1.1/32'