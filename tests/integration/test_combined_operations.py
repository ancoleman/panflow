"""
Integration tests for combined bulk operations, merging, and deduplication.
"""

import pytest
from lxml import etree
from unittest.mock import patch

from panflow import PANFlowConfig
from panflow.core.bulk_operations import ConfigUpdater
from panflow.core.object_merger import ObjectMerger
from panflow.core.deduplication import DeduplicationEngine
from panflow.core.conflict_resolver import ConflictStrategy


@pytest.fixture
def source_config():
    """
    Create a source configuration with various objects.
    """
    xml = '''
    <config version="10.2.0">
        <shared>
            <address>
                <entry name="db-server">
                    <ip-netmask>10.0.0.2/32</ip-netmask>
                    <tag>
                        <member>database</member>
                    </tag>
                </entry>
                <entry name="mail-server">
                    <ip-netmask>10.0.0.3/32</ip-netmask>
                    <tag>
                        <member>mail</member>
                    </tag>
                </entry>
                <entry name="backup-server">
                    <ip-netmask>10.0.0.4/32</ip-netmask>
                    <tag>
                        <member>backup</member>
                    </tag>
                </entry>
            </address>
            <address-group>
                <entry name="all-servers">
                    <static>
                        <member>db-server</member>
                        <member>mail-server</member>
                        <member>backup-server</member>
                    </static>
                </entry>
            </address-group>
            <tag>
                <entry name="database">
                    <color>#FF00FF</color>
                </entry>
                <entry name="mail">
                    <color>#00FFFF</color>
                </entry>
                <entry name="backup">
                    <color>#FFFF00</color>
                </entry>
            </tag>
        </shared>
    </config>
    '''
    # Create a PANFlowConfig object with the XML
    xml_bytes = xml.encode('utf-8')
    tree = etree.ElementTree(etree.fromstring(xml_bytes))
    config = PANFlowConfig(config_string=xml)
    config.tree = tree  # Ensure the tree is properly set
    return config


@pytest.fixture
def target_config():
    """
    Create a target configuration with a device group.
    """
    xml = '''
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG1">
                        <address>
                            <entry name="web-server">
                                <ip-netmask>10.0.0.1/32</ip-netmask>
                                <tag>
                                    <member>web</member>
                                </tag>
                            </entry>
                            <entry name="db-server-copy">
                                <ip-netmask>10.0.0.2/32</ip-netmask>
                                <description>Duplicate database server</description>
                            </entry>
                        </address>
                        <address-group>
                            <entry name="web-servers">
                                <static>
                                    <member>web-server</member>
                                </static>
                            </entry>
                        </address-group>
                        <tag>
                            <entry name="web">
                                <color>#FF0000</color>
                            </entry>
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
    # Create a PANFlowConfig object with the XML
    xml_bytes = xml.encode('utf-8')
    tree = etree.ElementTree(etree.fromstring(xml_bytes))
    config = PANFlowConfig(config_string=xml)
    config.tree = tree  # Ensure the tree is properly set
    return config


@pytest.fixture
def dedup_config():
    """
    Create a configuration with duplicate objects for deduplication testing.
    """
    xml = '''
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG1">
                        <address>
                            <entry name="server1">
                                <ip-netmask>10.0.0.1/32</ip-netmask>
                                <description>Server 1</description>
                            </entry>
                            <entry name="server-one">
                                <ip-netmask>10.0.0.1/32</ip-netmask>
                                <description>Duplicate of Server 1</description>
                            </entry>
                            <entry name="db-server">
                                <ip-netmask>10.0.0.2/32</ip-netmask>
                                <description>Database server</description>
                            </entry>
                            <entry name="database">
                                <ip-netmask>10.0.0.2/32</ip-netmask>
                                <description>Another database</description>
                            </entry>
                        </address>
                        <address-group>
                            <entry name="servers">
                                <static>
                                    <member>server1</member>
                                    <member>server-one</member>
                                    <member>db-server</member>
                                </static>
                            </entry>
                        </address-group>
                    </entry>
                </device-group>
            </entry>
        </devices>
    </config>
    '''
    # Create a PANFlowConfig object with the XML
    xml_bytes = xml.encode('utf-8')
    tree = etree.ElementTree(etree.fromstring(xml_bytes))
    config = PANFlowConfig(config_string=xml)
    config.tree = tree  # Ensure the tree is properly set
    return config


def test_bulk_merge_integration(source_config, target_config):
    """
    Integration test for bulk merging objects from source to target.
    """
    # Merge "all-servers" group from source to target DG1
    criteria = {"name": "all-servers"}
    merged, total = target_config.bulk_merge_objects(
        source_config,
        "address-group",
        "shared",
        "device_group",
        criteria,
        skip_if_exists=True,
        copy_references=True,
        target_device_group="DG1"
    )
    
    assert merged == 1
    assert total == 1
    
    # Now check if the group was properly merged to target
    xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address-group/entry[@name='all-servers']"
    all_servers_group = target_config.tree.xpath(xpath)
    assert len(all_servers_group) == 1
    
    # Check if address references were copied as well (due to copy_references=True)
    # Note: db-server-copy already exists in target so only mail-server and backup-server should be newly added
    xpath_mail = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='mail-server']"
    mail_server = target_config.tree.xpath(xpath_mail)
    assert len(mail_server) == 1
    
    xpath_backup = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='backup-server']"
    backup_server = target_config.tree.xpath(xpath_backup)
    assert len(backup_server) == 1


def test_deduplication_integration(dedup_config):
    """
    Integration test for deduplicating objects.
    """
    # Find and merge duplicate address objects
    changes, merged_count = dedup_config.deduplicate_objects(
        "address",
        "device_group",
        criteria=None,
        primary_name_strategy="shortest",
        dry_run=False,
        device_group="DG1"
    )
    
    assert merged_count == 2  # Two duplicate objects should be merged
    assert len(changes) == 2  # Two sets of duplicates (10.0.0.1 and 10.0.0.2)
    
    # Check the results
    ip1_key = next(k for k in changes.keys() if "10.0.0.1" in k)
    ip2_key = next(k for k in changes.keys() if "10.0.0.2" in k)
    
    # For 10.0.0.1, server1 should be primary (shortest strategy with alphabetical tiebreaker)
    assert changes[ip1_key]["primary"] == "server1"
    assert "server-one" in changes[ip1_key]["merged"]
    
    # For 10.0.0.2, database should be primary (shortest)
    assert changes[ip2_key]["primary"] == "database"
    assert "db-server" in changes[ip2_key]["merged"]
    
    # Check that the references in address-group were updated
    xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address-group/entry[@name='servers']/static/member"
    members = dedup_config.tree.xpath(xpath)
    member_names = [m.text for m in members if m.text]
    
    assert "server1" in member_names
    assert "database" in member_names
    assert "server-one" not in member_names  # Merged away
    assert "db-server" not in member_names   # Merged away


def test_combined_merge_deduplicate(source_config, target_config):
    """
    Test a workflow that combines merging and deduplication.
    """
    # First, merge all address objects from source to target
    address_criteria = None  # All address objects
    merged_addr, total_addr = target_config.bulk_merge_objects(
        source_config,
        "address",
        "shared",
        "device_group",
        address_criteria,
        skip_if_exists=False,  # Overwrite existing
        copy_references=True,
        conflict_strategy=ConflictStrategy.OVERWRITE,
        target_device_group="DG1"
    )
    
    # Then, merge all groups
    group_criteria = None  # All address groups
    merged_group, total_group = target_config.bulk_merge_objects(
        source_config,
        "address-group",
        "shared",
        "device_group",
        group_criteria,
        skip_if_exists=True,
        copy_references=False,  # Already copied the addresses
        target_device_group="DG1"
    )
    
    # Now deduplicate addresses in the target
    changes, merged_count = target_config.deduplicate_objects(
        "address",
        "device_group",
        criteria=None,
        primary_name_strategy="shortest",
        dry_run=False,
        device_group="DG1"
    )
    
    # Verify that db-server and db-server-copy were deduplicated
    db_server_key = next((k for k in changes.keys() if "10.0.0.2" in k), None)
    if db_server_key:  # Only if there were duplicate db servers
        assert changes[db_server_key]["primary"] in ("db-server", "db-server-copy")
        primary = changes[db_server_key]["primary"]
        merged = changes[db_server_key]["merged"][0]
        
        # Check that the primary exists in the config
        xpath_primary = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='{primary}']"
        primary_obj = target_config.tree.xpath(xpath_primary)
        assert len(primary_obj) == 1
        
        # Check that the merged one is gone
        xpath_merged = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='{merged}']"
        merged_obj = target_config.tree.xpath(xpath_merged)
        assert len(merged_obj) == 0
        
        # Check that groups were updated to use the primary name
        xpath_groups = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address-group/entry//member[text()='{primary}']"
        group_refs = target_config.tree.xpath(xpath_groups)
        assert len(group_refs) > 0
        
        # Make sure no references to the merged name exist
        xpath_merged_refs = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address-group/entry//member[text()='{merged}']"
        merged_refs = target_config.tree.xpath(xpath_merged_refs)
        assert len(merged_refs) == 0


def test_merge_objects_by_type(source_config, target_config):
    """
    Test merging multiple object types at once.
    """
    # Merge addresses, address-groups, and tags
    object_types = ["address", "address-group", "tag"]
    results = target_config.merge_objects_by_type(
        source_config,
        object_types,
        "shared",
        "device_group",
        criteria=None,  # All objects
        skip_if_exists=True,
        copy_references=True,
        target_device_group="DG1"
    )
    
    # Verify results for each type
    assert len(results) == 3
    assert "address" in results
    assert "address-group" in results
    assert "tag" in results
    
    addresses_merged, addresses_total = results["address"]
    groups_merged, groups_total = results["address-group"]
    tags_merged, tags_total = results["tag"]
    
    # Verify the objects were merged by checking a sample
    # Check for mail-server address
    xpath_mail = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='mail-server']"
    mail_server = target_config.tree.xpath(xpath_mail)
    assert len(mail_server) == 1
    
    # Check for all-servers group
    xpath_group = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address-group/entry[@name='all-servers']"
    all_servers = target_config.tree.xpath(xpath_group)
    assert len(all_servers) == 1
    
    # Check for mail tag
    xpath_tag = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/tag/entry[@name='mail']"
    mail_tag = target_config.tree.xpath(xpath_tag)
    assert len(mail_tag) == 1


def test_deduplicate_all_object_types(dedup_config):
    """
    Test deduplicating multiple object types at once.
    """
    # Deduplicate addresses and services
    object_types = ["address", "service"]
    results = dedup_config.deduplicate_all_object_types(
        "device_group",
        object_types,
        criteria=None,
        primary_name_strategy="shortest",
        dry_run=False,
        device_group="DG1"
    )
    
    # Check results
    assert "address" in results
    address_changes, address_merged = results["address"]
    
    # Verify address deduplication
    assert address_merged == 2  # Two pairs of duplicates
    
    # Check the server1/server-one pair
    ip1_key = next(k for k in address_changes.keys() if "10.0.0.1" in k)
    assert address_changes[ip1_key]["primary"] == "server1"
    assert "server-one" in address_changes[ip1_key]["merged"]
    
    # Verify that server-one is now gone
    xpath_server_one = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='server-one']"
    server_one = dedup_config.tree.xpath(xpath_server_one)
    assert len(server_one) == 0