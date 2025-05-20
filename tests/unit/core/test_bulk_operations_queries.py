"""
Unit tests for bulk operations query functionality.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock

from panflow.core.bulk_operations import ConfigUpdater
from panflow.core.graph_utils import ConfigGraph


@pytest.fixture
def panorama_config():
    """Create a sample Panorama configuration for query testing."""
    xml = """
    <config>
      <devices>
        <entry name="localhost.localdomain">
          <device-group>
            <entry name="test-dg-1">
              <pre-rulebase>
                <security>
                  <rules>
                    <entry name="rule1">
                      <action>allow</action>
                      <from><member>any</member></from>
                      <to><member>any</member></to>
                      <source><member>any</member></source>
                      <destination><member>any</member></destination>
                      <application><member>any</member></application>
                      <service><member>application-default</member></service>
                    </entry>
                    <entry name="rule2">
                      <action>deny</action>
                      <from><member>any</member></from>
                      <to><member>any</member></to>
                      <source><member>any</member></source>
                      <destination><member>any</member></destination>
                      <application><member>any</member></application>
                      <service><member>application-default</member></service>
                      <disabled>yes</disabled>
                    </entry>
                  </rules>
                </security>
              </pre-rulebase>
            </entry>
            <entry name="test-dg-2">
              <pre-rulebase>
                <security>
                  <rules>
                    <entry name="rule3">
                      <action>allow</action>
                      <from><member>any</member></from>
                      <to><member>any</member></to>
                      <source><member>any</member></source>
                      <destination><member>any</member></destination>
                      <application><member>any</member></application>
                      <service><member>application-default</member></service>
                    </entry>
                    <entry name="rule4">
                      <action>allow</action>
                      <from><member>any</member></from>
                      <to><member>any</member></to>
                      <source><member>any</member></source>
                      <destination><member>any</member></destination>
                      <application><member>any</member></application>
                      <service><member>application-default</member></service>
                      <disabled>yes</disabled>
                    </entry>
                  </rules>
                </security>
              </pre-rulebase>
              <post-rulebase>
                <security>
                  <rules>
                    <entry name="rule5">
                      <action>allow</action>
                      <from><member>any</member></from>
                      <to><member>any</member></to>
                      <source><member>any</member></source>
                      <destination><member>any</member></destination>
                      <application><member>any</member></application>
                      <service><member>application-default</member></service>
                    </entry>
                  </rules>
                </security>
              </post-rulebase>
            </entry>
          </device-group>
        </entry>
      </devices>
    </config>
    """
    return etree.fromstring(xml)


def test_get_policies_from_query_with_device_group(panorama_config):
    """Test that _get_policies_from_query works with device group context."""
    updater = ConfigUpdater(
        tree=panorama_config,
        device_type="panorama",
        context_type="device_group",
        version="10.2",
        device_group="test-dg-1"
    )
    
    # Build graph to use for the query
    graph = ConfigGraph(
        device_type="panorama",
        context_type="device_group",
        device_group="test-dg-1"
    )
    graph.build_from_xml(panorama_config)
    
    # Test basic query with graph reuse
    query = "MATCH (r:security-rule) RETURN r.name"
    policy_names = updater._get_policies_from_query(
        query_filter=query,
        policy_type="security_pre_rules",
        context_type="device_group",
        device_group="test-dg-1",
        existing_graph=graph
    )
    
    # Should get two policies from test-dg-1
    assert len(policy_names) == 2
    assert "rule1" in policy_names
    assert "rule2" in policy_names


def test_get_policies_from_query_with_action_filter(panorama_config):
    """Test that _get_policies_from_query filters correctly by action."""
    updater = ConfigUpdater(
        tree=panorama_config,
        device_type="panorama",
        context_type="device_group",
        version="10.2",
        device_group="test-dg-1"
    )
    
    # Test query for allow action rules
    query = "MATCH (r:security-rule) WHERE r.action == 'allow' RETURN r.name"
    policy_names = updater._get_policies_from_query(
        query_filter=query,
        policy_type="security_pre_rules",
        context_type="device_group",
        device_group="test-dg-1"
    )
    
    # Should get only the allow policy
    assert len(policy_names) == 1
    assert "rule1" in policy_names


def test_get_policies_from_query_with_disabled_filter(panorama_config):
    """Test that _get_policies_from_query filters correctly by disabled status."""
    updater = ConfigUpdater(
        tree=panorama_config,
        device_type="panorama",
        context_type="device_group",
        version="10.2",
        device_group="test-dg-1"
    )
    
    # Test query for disabled rules
    query = "MATCH (r:security-rule) WHERE r.disabled == 'yes' RETURN r.name"
    policy_names = updater._get_policies_from_query(
        query_filter=query,
        policy_type="security_pre_rules",
        context_type="device_group",
        device_group="test-dg-1"
    )
    
    # Should get only the disabled policy
    assert len(policy_names) == 1
    assert "rule2" in policy_names


def test_get_policies_from_query_with_existing_graph(panorama_config):
    """Test that _get_policies_from_query reuses an existing graph correctly."""
    updater = ConfigUpdater(
        tree=panorama_config,
        device_type="panorama",
        context_type="device_group",
        version="10.2",
        device_group="test-dg-1"
    )
    
    # Create a mock graph
    mock_graph = MagicMock()
    mock_query_results = [{"r.name": "rule1"}, {"r.name": "rule2"}]
    
    # Mock the QueryExecutor
    with patch("panflow.core.bulk_operations.Query") as MockQuery:
        with patch("panflow.core.bulk_operations.QueryExecutor") as MockQueryExecutor:
            mock_executor = MagicMock()
            MockQueryExecutor.return_value = mock_executor
            mock_executor.execute.return_value = mock_query_results
            
            # Test with existing graph
            policy_names = updater._get_policies_from_query(
                query_filter="MATCH (r:security-rule) RETURN r.name",
                existing_graph=mock_graph
            )
            
            # Should use the existing graph
            MockQueryExecutor.assert_called_once_with(mock_graph)
            assert len(policy_names) == 2
            assert "rule1" in policy_names
            assert "rule2" in policy_names


def test_bulk_update_policies_with_existing_graph(panorama_config):
    """Test that bulk_update_policies passes the existing graph to _get_policies_from_query."""
    updater = ConfigUpdater(
        tree=panorama_config,
        device_type="panorama",
        context_type="device_group",
        version="10.2",
        device_group="test-dg-1"
    )
    
    # Create a mock graph
    mock_graph = MagicMock()
    
    # Mock _get_policies_from_query to verify the graph is passed through
    with patch.object(updater, "_get_policies_from_query") as mock_get_policies:
        mock_get_policies.return_value = ["rule1", "rule2"]
        
        # Mock select_policies to avoid actual XML operations
        with patch.object(updater.query, "select_policies") as mock_select:
            mock_select.return_value = [
                etree.Element("entry", name="rule1"),
                etree.Element("entry", name="rule2")
            ]
            
            # Mock _apply_operations to avoid actual XML operations
            with patch.object(updater, "_apply_operations") as mock_apply:
                mock_apply.return_value = True
                
                # Test bulk_update_policies with a query and existing graph
                updater.bulk_update_policies(
                    policy_type="security_pre_rules",
                    criteria=None,
                    operations={"log-setting": "test-log"},
                    query_filter="MATCH (r:security-rule) RETURN r.name",
                    existing_graph=mock_graph
                )
                
                # Verify _get_policies_from_query was called with the existing graph
                mock_get_policies.assert_called_once()
                args, kwargs = mock_get_policies.call_args
                assert kwargs.get("existing_graph") == mock_graph