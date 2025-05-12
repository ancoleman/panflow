"""
Unit tests for bulk operations modules.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock, call

from panflow.core.bulk_operations import ConfigQuery, ConfigUpdater
from panflow.core.conflict_resolver import ConflictStrategy


@pytest.fixture
def sample_config():
    """
    Create a sample configuration with various objects and policies.
    """
    xml = """
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG1">
                        <address>
                            <entry name="internal-server">
                                <ip-netmask>10.0.0.1/32</ip-netmask>
                                <tag>
                                    <member>internal</member>
                                </tag>
                            </entry>
                            <entry name="web-server">
                                <ip-netmask>192.168.1.100/32</ip-netmask>
                                <tag>
                                    <member>web</member>
                                    <member>dmz</member>
                                </tag>
                            </entry>
                            <entry name="backup-server">
                                <ip-netmask>192.168.1.200/32</ip-netmask>
                                <tag>
                                    <member>backup</member>
                                </tag>
                            </entry>
                        </address>
                        <address-group>
                            <entry name="all-servers">
                                <static>
                                    <member>internal-server</member>
                                    <member>web-server</member>
                                    <member>backup-server</member>
                                </static>
                            </entry>
                            <entry name="dmz-servers">
                                <static>
                                    <member>web-server</member>
                                </static>
                            </entry>
                        </address-group>
                        <security>
                            <rules>
                                <entry name="allow-web">
                                    <from>
                                        <member>any</member>
                                    </from>
                                    <to>
                                        <member>dmz</member>
                                    </to>
                                    <source>
                                        <member>any</member>
                                    </source>
                                    <destination>
                                        <member>web-server</member>
                                    </destination>
                                    <service>
                                        <member>web-browsing</member>
                                    </service>
                                    <action>allow</action>
                                </entry>
                                <entry name="block-internal">
                                    <from>
                                        <member>external</member>
                                    </from>
                                    <to>
                                        <member>internal</member>
                                    </to>
                                    <source>
                                        <member>any</member>
                                    </source>
                                    <destination>
                                        <member>internal-server</member>
                                    </destination>
                                    <service>
                                        <member>any</member>
                                    </service>
                                    <action>deny</action>
                                </entry>
                            </rules>
                        </security>
                    </entry>
                </device-group>
            </entry>
        </devices>
        <shared>
            <tag>
                <entry name="web">
                    <color>#FF0000</color>
                </entry>
                <entry name="internal">
                    <color>#00FF00</color>
                </entry>
                <entry name="dmz">
                    <color>#0000FF</color>
                </entry>
                <entry name="backup">
                    <color>#FFFF00</color>
                </entry>
            </tag>
        </shared>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml))


@pytest.fixture
def sample_source_config():
    """
    Create a source configuration for merging tests.
    """
    xml = """
    <config version="10.2.0">
        <shared>
            <address>
                <entry name="database-server">
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
            </address>
            <tag>
                <entry name="database">
                    <color>#FF00FF</color>
                </entry>
                <entry name="mail">
                    <color>#00FFFF</color>
                </entry>
            </tag>
        </shared>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml))


def test_init_config_query(sample_config):
    """Test ConfigQuery initialization."""
    query = ConfigQuery(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    assert query.tree == sample_config
    assert query.device_type == "panorama"
    assert query.context_type == "device_group"
    assert query.version == "10.2"
    assert query.context_kwargs == {"device_group": "DG1"}


def test_select_objects_no_criteria(sample_config):
    """Test selecting objects without criteria."""
    query = ConfigQuery(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    with patch("panflow.core.bulk_operations.get_object_xpath") as mock_xpath:
        with patch("panflow.core.bulk_operations.xpath_search") as mock_search:
            # Set up mocks
            mock_xpath.return_value = "/mocked/xpath"
            mock_search.return_value = [
                etree.Element("entry", name="obj1"),
                etree.Element("entry", name="obj2"),
            ]

            # Select address objects
            objects = query.select_objects("address")

            assert len(objects) == 2
            mock_xpath.assert_called_once_with(
                "address", "panorama", "device_group", "10.2", device_group="DG1"
            )
            mock_search.assert_called_once_with(sample_config, "/mocked/xpath")


def test_select_objects_with_criteria(sample_config):
    """Test selecting objects with criteria."""
    query = ConfigQuery(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Mock the base XPath and search results
    with patch("panflow.core.bulk_operations.get_object_xpath") as mock_xpath:
        with patch("panflow.core.bulk_operations.xpath_search") as mock_search:
            with patch.object(query, "_matches_criteria") as mock_matches:
                # Set up mocks
                mock_xpath.return_value = "/mocked/xpath"

                obj1 = etree.Element("entry", name="web-server")
                obj2 = etree.Element("entry", name="internal-server")
                mock_search.return_value = [obj1, obj2]

                # Make only web-server match
                mock_matches.side_effect = lambda obj, criteria: obj.get("name") == "web-server"

                # Select address objects with criteria
                criteria = {"has-tag": "web"}
                objects = query.select_objects("address", criteria)

                assert len(objects) == 1
                assert objects[0].get("name") == "web-server"
                mock_matches.assert_any_call(obj1, criteria)
                mock_matches.assert_any_call(obj2, criteria)


def test_select_policies_no_criteria(sample_config):
    """Test selecting policies without criteria."""
    query = ConfigQuery(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    with patch("panflow.core.bulk_operations.get_policy_xpath") as mock_xpath:
        with patch("panflow.core.bulk_operations.xpath_search") as mock_search:
            # Set up mocks
            mock_xpath.return_value = "/mocked/policy/xpath"
            mock_search.return_value = [
                etree.Element("entry", name="allow-web"),
                etree.Element("entry", name="block-internal"),
            ]

            # Select security policies
            policies = query.select_policies("security_pre_rules")

            assert len(policies) == 2
            mock_xpath.assert_called_once_with(
                "security_pre_rules", "panorama", "device_group", "10.2", device_group="DG1"
            )
            mock_search.assert_called_once_with(sample_config, "/mocked/policy/xpath")


def test_select_policies_with_criteria(sample_config):
    """Test selecting policies with criteria."""
    query = ConfigQuery(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Mock the base XPath and search results
    with patch("panflow.core.bulk_operations.get_policy_xpath") as mock_xpath:
        with patch("panflow.core.bulk_operations.xpath_search") as mock_search:
            with patch.object(query, "_matches_enhanced_criteria") as mock_matches:
                # Set up mocks
                mock_xpath.return_value = "/mocked/policy/xpath"

                policy1 = etree.Element("entry", name="allow-web")
                policy2 = etree.Element("entry", name="block-internal")
                mock_search.return_value = [policy1, policy2]

                # Make only allow-web match
                mock_matches.side_effect = lambda obj, criteria: obj.get("name") == "allow-web"

                # Select security policies with criteria
                criteria = {"action": "allow"}
                policies = query.select_policies("security_pre_rules", criteria)

                assert len(policies) == 1
                assert policies[0].get("name") == "allow-web"
                mock_matches.assert_any_call(policy1, criteria)
                mock_matches.assert_any_call(policy2, criteria)


def test_matches_criteria():
    """Test the criteria matching logic."""
    query = ConfigQuery(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Create a test element
    element = etree.Element("entry", name="web-server")
    etree.SubElement(element, "ip-netmask").text = "192.168.1.100"

    tag_elem = etree.SubElement(element, "tag")
    member1 = etree.SubElement(tag_elem, "member")
    member1.text = "web"
    member2 = etree.SubElement(tag_elem, "member")
    member2.text = "dmz"

    # Test exact name match
    assert query._matches_criteria(element, {"name": "web-server"}) is True
    assert query._matches_criteria(element, {"name": "other-server"}) is False

    # Test has-tag
    assert query._matches_criteria(element, {"has-tag": "web"}) is True
    assert query._matches_criteria(element, {"has-tag": "nonexistent"}) is False

    # Test child element value
    assert query._matches_criteria(element, {"ip-netmask": "192.168.1.100"}) is True
    assert query._matches_criteria(element, {"ip-netmask": "10.0.0.1"}) is False

    # Test nonexistent field
    assert query._matches_criteria(element, {"nonexistent": "value"}) is False


def test_init_config_updater(sample_config):
    """Test ConfigUpdater initialization."""
    updater = ConfigUpdater(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    assert updater.tree == sample_config
    assert updater.device_type == "panorama"
    assert updater.context_type == "device_group"
    assert updater.version == "10.2"
    assert updater.context_kwargs == {"device_group": "DG1"}
    assert isinstance(updater.query, ConfigQuery)


def test_bulk_update_policies(sample_config):
    """Test bulk updating policies."""
    updater = ConfigUpdater(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Mock policy selection and updates
    with patch.object(updater.query, "select_policies") as mock_select:
        with patch.object(updater, "_apply_updates") as mock_apply:
            # Set up mocks
            policy1 = etree.Element("entry", name="allow-web")
            policy2 = etree.Element("entry", name="block-internal")
            mock_select.return_value = [policy1, policy2]

            # Mock successful updates
            mock_apply.return_value = True

            # Perform bulk update
            criteria = {"to": "dmz"}
            operations = {"add-tag": {"name": "updated"}}
            updated = updater.bulk_update_policies("security_pre_rules", criteria, operations)

            assert updated == 2
            mock_select.assert_called_once_with("security_pre_rules", criteria)
            assert mock_apply.call_count == 2


def test_bulk_update_objects(sample_config):
    """Test bulk updating objects."""
    updater = ConfigUpdater(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Mock object selection and updates
    with patch.object(updater.query, "select_objects") as mock_select:
        with patch.object(updater, "_apply_updates") as mock_apply:
            # Set up mocks
            obj1 = etree.Element("entry", name="web-server")
            obj2 = etree.Element("entry", name="backup-server")
            mock_select.return_value = [obj1, obj2]

            # First update succeeds, second fails
            mock_apply.side_effect = [True, False]

            # Perform bulk update
            criteria = {"has-tag": "dmz"}
            operations = {"add-tag": {"name": "updated"}}
            updated = updater.bulk_update_objects("address", criteria, operations)

            assert updated == 1
            mock_select.assert_called_once_with("address", criteria)
            assert mock_apply.call_count == 2


def test_bulk_delete_objects(sample_config):
    """Test bulk deleting objects."""
    updater = ConfigUpdater(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Create parent elements for testing removal
    parent = etree.Element("address")
    obj1 = etree.SubElement(parent, "entry", name="web-server")
    obj2 = etree.SubElement(parent, "entry", name="backup-server")

    # Mock object selection
    with patch.object(updater.query, "select_objects") as mock_select:
        mock_select.return_value = [obj1, obj2]

        # Perform bulk delete
        criteria = {"has-tag": "dmz"}
        deleted = updater.bulk_delete_objects("address", criteria)

        assert deleted == 2
        mock_select.assert_called_once_with("address", criteria)
        assert len(parent.findall("./entry")) == 0


def test_apply_updates_add_tag():
    """Test applying the add-tag operation."""
    updater = ConfigUpdater(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Create a test element
    element = etree.Element("entry", name="web-server")

    # Operations to apply
    operations = {"add-tag": {"name": "new-tag"}}

    # Mock the _add_tag method
    with patch.object(updater, "_add_tag") as mock_add_tag:
        mock_add_tag.return_value = True

        # Apply the operations
        modified = updater._apply_updates(element, operations)

        assert modified is True
        mock_add_tag.assert_called_once_with(element, {"name": "new-tag"})


def test_add_tag():
    """Test adding a tag to an element."""
    updater = ConfigUpdater(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Test with an element that doesn't have any tags yet
    element = etree.Element("entry", name="web-server")

    # Add a tag
    result = updater._add_tag(element, {"name": "new-tag"})

    assert result is True
    assert element.find("./tag/member").text == "new-tag"

    # Test adding a second tag
    result = updater._add_tag(element, {"name": "another-tag"})

    assert result is True
    assert len(element.findall("./tag/member")) == 2

    # Test adding a duplicate tag (should be skipped)
    result = updater._add_tag(element, {"name": "new-tag"})

    assert result is False
    assert len(element.findall("./tag/member")) == 2


def test_bulk_merge_objects(sample_config, sample_source_config):
    """Test bulk merging objects from source to target."""
    updater = ConfigUpdater(
        sample_config, "panorama", "device_group", "10.2", device_group="DG1"  # Target
    )

    # Mock ConfigQuery, ObjectMerger for controlled testing
    with patch("panflow.core.bulk_operations.ConfigQuery") as MockQuery:
        with patch("panflow.core.bulk_operations.ObjectMerger") as MockMerger:
            # Set up mock query results
            mock_query_instance = MagicMock()
            MockQuery.return_value = mock_query_instance

            obj1 = etree.Element("entry", name="database-server")
            obj2 = etree.Element("entry", name="mail-server")
            mock_query_instance.select_objects.return_value = [obj1, obj2]

            # Set up mock merger
            mock_merger_instance = MagicMock()
            MockMerger.return_value = mock_merger_instance

            # First merge succeeds, second fails
            mock_merger_instance.copy_object.side_effect = [True, False]

            # Perform bulk merge
            criteria = {"has-tag": "database"}
            merged, total = updater.bulk_merge_objects(
                sample_source_config,  # Source
                "address",
                criteria,
                "shared",
                "device_group",
                "panorama",
                "10.2",
                True,
                True,
                None,
            )

            assert merged == 1
            assert total == 2
            mock_query_instance.select_objects.assert_called_once_with("address", criteria)
            assert mock_merger_instance.copy_object.call_count == 2


def test_bulk_deduplicate_objects(sample_config):
    """Test bulk deduplication of objects."""
    updater = ConfigUpdater(sample_config, "panorama", "device_group", "10.2", device_group="DG1")

    # Mock DeduplicationEngine for controlled testing
    with patch("panflow.core.bulk_operations.DeduplicationEngine") as MockDedup:
        # Set up mock deduplication engine
        mock_dedup_instance = MagicMock()
        MockDedup.return_value = mock_dedup_instance

        # Mock duplicate findings
        duplicates = {
            "ip-netmask:192.168.1.100": [
                ("web-server", etree.Element("entry", name="web-server")),
                ("web-server-copy", etree.Element("entry", name="web-server-copy")),
            ]
        }
        references = {
            "web-server": [("group", "all-servers"), ("rule", "allow-web")],
            "web-server-copy": [],
        }
        mock_dedup_instance.find_duplicates.return_value = (duplicates, references)

        # Mock merge results
        changes = {
            "ip-netmask:192.168.1.100": {
                "primary": "web-server",
                "merged": ["web-server-copy"],
                "references_updated": [("group", "all-servers")],
            }
        }
        mock_dedup_instance.merge_duplicates.return_value = changes

        # Perform deduplication
        result_changes, merged_count = updater.bulk_deduplicate_objects(
            "address", None, "shortest", False
        )

        assert merged_count == 1
        assert result_changes == changes
        mock_dedup_instance.find_duplicates.assert_called_once_with("address")
        mock_dedup_instance.merge_duplicates.assert_called_once_with(
            duplicates, references, "shortest"
        )
