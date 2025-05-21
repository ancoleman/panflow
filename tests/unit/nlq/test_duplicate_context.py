"""
Unit tests for the context-aware duplicate object reporting in NLQ.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock

from panflow.nlq.processor import NLQProcessor
from panflow.core.deduplication import DeduplicationEngine


@pytest.fixture
def sample_config_with_context_duplicates():
    """
    Create a sample configuration with duplicate objects across different contexts.
    """
    xml = """
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="dg1">
                        <address>
                            <entry name="address1">
                                <ip-netmask>10.1.1.1</ip-netmask>
                            </entry>
                            <entry name="duplicated-address">
                                <ip-netmask>192.168.1.1</ip-netmask>
                            </entry>
                        </address>
                    </entry>
                    <entry name="dg2">
                        <address>
                            <entry name="address2">
                                <ip-netmask>10.1.1.2</ip-netmask>
                            </entry>
                            <entry name="duplicated-address-2">
                                <ip-netmask>192.168.1.1</ip-netmask>
                            </entry>
                        </address>
                    </entry>
                </device-group>
                <vsys>
                    <entry name="vsys1">
                        <address>
                            <entry name="address3">
                                <ip-netmask>10.1.1.3</ip-netmask>
                            </entry>
                        </address>
                    </entry>
                </vsys>
            </entry>
        </devices>
        <shared>
            <address>
                <entry name="shared-address">
                    <ip-netmask>10.1.1.10</ip-netmask>
                </entry>
                <entry name="shared-duplicated-address">
                    <ip-netmask>192.168.1.1</ip-netmask>
                </entry>
            </address>
        </shared>
    </config>
    """
    return etree.fromstring(xml)


def test_duplicate_objects_with_context_in_deduplication_engine(sample_config_with_context_duplicates):
    """
    Test that the DeduplicationEngine correctly tracks context information for duplicate objects.
    """
    # Create a DeduplicationEngine instance for Panorama with device_group context
    engine = DeduplicationEngine(
        etree.ElementTree(sample_config_with_context_duplicates),
        "panorama",
        "device_group",
        "10.2.0",
        device_group="dg1"
    )
    
    # Find duplicate addresses
    duplicates, _ = engine.find_duplicate_addresses()
    
    # Verify duplicates were found
    assert duplicates
    
    # Check for the duplicated IP address 192.168.1.1
    duplicated_ip_key = None
    for key in duplicates.keys():
        if "192.168.1.1" in key:
            duplicated_ip_key = key
            break
    
    assert duplicated_ip_key is not None
    
    # Check that we have at least one object with context information
    has_context = False
    for obj_tuple in duplicates[duplicated_ip_key]:
        # Verify tuple structure (name, elem, context_dict)
        assert len(obj_tuple) >= 3
        assert isinstance(obj_tuple[0], str)  # name
        assert isinstance(obj_tuple[2], dict)  # context dict
        
        # Verify context information
        context_dict = obj_tuple[2]
        assert "type" in context_dict
        
        if context_dict["type"] == "device_group":
            assert "device_group" in context_dict
            has_context = True
        elif context_dict["type"] == "shared":
            has_context = True
    
    assert has_context, "No objects found with proper context information"


@patch("panflow.core.deduplication.DeduplicationEngine")
def test_nlq_processor_preserves_context(mock_deduplication_engine, sample_config_with_context_duplicates):
    """
    Test that the NLQProcessor preserves context information when finding duplicates.
    """
    # Set up mocks
    mock_engine_instance = MagicMock()
    mock_deduplication_engine.return_value = mock_engine_instance
    
    # Mock find_duplicate_addresses to return sample duplicates with context
    sample_duplicates = {
        "ip-netmask:192.168.1.1": [
            ("duplicated-address", MagicMock(), {"type": "device_group", "device_group": "dg1"}),
            ("duplicated-address-2", MagicMock(), {"type": "device_group", "device_group": "dg2"}),
            ("shared-duplicated-address", MagicMock(), {"type": "shared"})
        ]
    }
    mock_engine_instance.find_duplicate_addresses.return_value = (sample_duplicates, {})
    
    # Create a mocked PANFlowConfig
    with patch("panflow.PANFlowConfig") as mock_config_class:
        mock_config = MagicMock()
        mock_config.tree = etree.ElementTree(sample_config_with_context_duplicates)
        mock_config.device_type = "panorama"
        mock_config.version = "10.2.0"
        mock_config_class.return_value = mock_config
        
        # Initialize processor
        processor = NLQProcessor(use_ai=False)
        
        # Execute the NLQ query to find duplicates
        result = processor.process("find duplicate address objects", "mock_config.xml")
        
        # Verify the result contains formatted duplicates with context
        assert result["success"] is True
        assert "result" in result
        
        # Check for formatted_duplicates
        assert "formatted_duplicates" in result["result"]
        formatted_dups = result["result"]["formatted_duplicates"]
        
        # Verify the structure of formatted duplicates
        assert formatted_dups
        assert "ip-netmask:192.168.1.1" in formatted_dups
        
        # Check that context information is preserved
        objects = formatted_dups["ip-netmask:192.168.1.1"]
        
        # Verify we have objects with context information
        device_group_objects = [obj for obj in objects if obj.get("context_type") == "device_group"]
        shared_objects = [obj for obj in objects if obj.get("context_type") == "shared"]
        
        assert len(device_group_objects) == 2
        assert len(shared_objects) == 1
        
        # Check the context fields
        for obj in device_group_objects:
            assert "context_name" in obj
            assert "context" in obj
            assert "Device Group:" in obj["context"]
        
        for obj in shared_objects:
            assert "context" in obj
            assert obj["context"] == "Shared"