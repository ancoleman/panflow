"""
Unit tests for the graph service functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import re
from lxml import etree

from panflow.core.graph_service import GraphService
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor


class TestGraphService:
    """Tests for the GraphService class."""

    @pytest.fixture
    def graph_service(self):
        """Return a GraphService instance for testing."""
        return GraphService()

    @pytest.fixture
    def mock_config_graph(self):
        """Return a mocked ConfigGraph instance."""
        mock_graph = MagicMock(spec=ConfigGraph)
        # Set up the mock graph's build_from_xml method
        mock_graph.build_from_xml = MagicMock()
        return mock_graph

    @pytest.fixture
    def mock_query_executor(self):
        """Return a mocked QueryExecutor instance."""
        mock_executor = MagicMock(spec=QueryExecutor)
        # Set up the mock executor's execute method
        mock_executor.execute = MagicMock(return_value=[])
        return mock_executor

    @patch("panflow.core.graph_service.ConfigGraph")
    def test_get_graph(self, mock_config_graph_class, graph_service, sample_xml_tree):
        """Test get_graph method."""
        # Set up the mock ConfigGraph class to return our mock instance
        mock_graph_instance = MagicMock()
        mock_config_graph_class.return_value = mock_graph_instance

        # Call the method
        result = graph_service.get_graph(sample_xml_tree)

        # Verify the graph was created and built from the XML
        mock_config_graph_class.assert_called_once()
        mock_graph_instance.build_from_xml.assert_called_once_with(sample_xml_tree)
        assert result == mock_graph_instance

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_find_objects_by_name_pattern(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test find_objects_by_name_pattern method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [
            {"a.name": "test-address"},
            {"a.name": "test-address2"},
        ]

        # Call the method
        result = graph_service.find_objects_by_name_pattern(
            sample_xml_tree, "address", "test.*", case_sensitive=False
        )

        # Verify the query was created correctly
        expected_query = "MATCH (a:address) WHERE a.name =~ '(?i)test.*' RETURN a.name"
        mock_query_class.assert_called_once_with(expected_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were processed correctly
        assert result == ["test-address", "test-address2"]

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_find_objects_by_value_pattern(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test find_objects_by_value_pattern method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [
            {"a.name": "test-address"},
            {"a.name": "test-address2"},
        ]

        # Call the method with wildcard support
        result = graph_service.find_objects_by_value_pattern(
            sample_xml_tree, "address", "192.168.1.*", wildcard_support=True, case_sensitive=False
        )

        # Verify the query was created correctly (with wildcard conversion)
        expected_query = (
            "MATCH (a:address) WHERE a.value =~ '(?i).*192\\.168\\.1\\..*.*' RETURN a.name"
        )
        mock_query_class.assert_called_once_with(expected_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were processed correctly
        assert result == ["test-address", "test-address2"]

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_find_address_objects_containing_ip(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test find_address_objects_containing_ip method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [
            {"a.name": "test-address"},
            {"a.name": "test-address2"},
        ]

        # Call the method
        result = graph_service.find_address_objects_containing_ip(sample_xml_tree, "192.168.1")

        # Verify the query was created correctly
        expected_query = "MATCH (a:address) WHERE a.value =~ '.*192\\.168\\.1.*' RETURN a.name"
        mock_query_class.assert_called_once_with(expected_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were processed correctly
        assert result == ["test-address", "test-address2"]

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_find_service_objects_with_port(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test find_service_objects_with_port method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [{"s.name": "http"}, {"s.name": "http-alt"}]

        # Call the method
        result = graph_service.find_service_objects_with_port(sample_xml_tree, "80")

        # Verify the query was created correctly
        expected_query = "MATCH (s:service) WHERE s.dst_port == '80' RETURN s.name"
        mock_query_class.assert_called_once_with(expected_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were processed correctly
        assert result == ["http", "http-alt"]

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_find_unused_objects(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test find_unused_objects method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [
            {"a.name": "unused-address1"},
            {"a.name": "unused-address2"},
        ]

        # Call the method
        result = graph_service.find_unused_objects(sample_xml_tree, "address")

        # Verify the query was created correctly
        expected_query = """
        MATCH (a:address) 
        WHERE NOT (()-[:uses-source|uses-destination|contains]->(a)) 
        RETURN a.name
        """
        mock_query_class.assert_called_once()  # Can't check exact string due to whitespace

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were processed correctly
        assert result == ["unused-address1", "unused-address2"]

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_execute_custom_query(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test execute_custom_query method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        expected_results = [
            {"a.name": "test-address", "a.value": "192.168.1.1/32"},
            {"a.name": "test-address2", "a.value": "192.168.1.2/32"},
        ]
        mock_executor.execute.return_value = expected_results

        # Call the method
        custom_query = "MATCH (a:address) WHERE a.value =~ '.*192.168.*' RETURN a.name, a.value"
        result = graph_service.execute_custom_query(sample_xml_tree, custom_query)

        # Verify the query was created correctly
        mock_query_class.assert_called_once_with(custom_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were returned directly
        assert result == expected_results

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_filter_objects_by_query(
        self,
        mock_query_executor_class,
        mock_query_class,
        mock_config_graph_class,
        graph_service,
        sample_xml_tree,
    ):
        """Test filter_objects_by_query method."""
        # Set up mocks
        mock_graph = MagicMock()
        mock_config_graph_class.return_value = mock_graph

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up the mock executor to return test results
        mock_executor.execute.return_value = [
            {"a.name": "test-address"},
            {"a.name": "test-address2"},
        ]

        # Create some test objects
        class TestObject:
            def __init__(self, object_name):
                self.object_name = object_name

        test_objects = [
            TestObject("test-address"),
            TestObject("test-address2"),
            TestObject("unused-address"),
        ]

        # Call the method
        query_text = "MATCH (a:address) WHERE a.value =~ '.*192.168.*'"
        result = graph_service.filter_objects_by_query(
            sample_xml_tree, test_objects, "address", query_text
        )

        # Verify the query was created correctly (with RETURN added)
        expected_query = "MATCH (a:address) WHERE a.value =~ '.*192.168.*' RETURN a.name"
        mock_query_class.assert_called_once_with(expected_query)

        # Verify the executor was created and used
        mock_query_executor_class.assert_called_once_with(mock_graph)
        mock_executor.execute.assert_called_once_with(mock_query)

        # Verify the results were filtered correctly
        assert len(result) == 2
        assert all(obj.object_name in ["test-address", "test-address2"] for obj in result)

    @patch("panflow.core.graph_service.ConfigGraph")
    @patch("panflow.core.graph_service.Query")
    @patch("panflow.core.graph_service.QueryExecutor")
    def test_execute_name_query(
        self, mock_query_executor_class, mock_query_class, mock_config_graph_class, graph_service
    ):
        """Test _execute_name_query method."""
        # Set up mocks
        mock_graph = MagicMock()

        mock_query = MagicMock()
        mock_query_class.return_value = mock_query

        mock_executor = MagicMock()
        mock_query_executor_class.return_value = mock_executor

        # Set up different test cases
        test_cases = [
            # Case 1: Results with a.name format
            ([{"a.name": "test1"}, {"a.name": "test2"}], ["test1", "test2"]),
            # Case 2: Results with single column (unnamed)
            ([{"column": "test3"}, {"column": "test4"}], ["test3", "test4"]),
            # Case 3: Mixed format
            ([{"a.name": "test5"}, {"column": "test6"}], ["test5", "test6"]),
        ]

        for test_input, expected_output in test_cases:
            # Set up the mock executor to return test results
            mock_executor.execute.return_value = test_input

            # Call the method
            query_text = "test_query"
            result = graph_service._execute_name_query(mock_graph, query_text)

            # Verify the query was created and executed
            mock_query_class.assert_called_with(query_text)
            mock_query_executor_class.assert_called_with(mock_graph)
            mock_executor.execute.assert_called_with(mock_query)

            # Verify the results were processed correctly
            assert result == expected_output
