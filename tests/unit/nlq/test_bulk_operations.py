"""
Unit tests for bulk operation functionality in the NLQ module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import tempfile
import shutil
from pathlib import Path
import lxml.etree as ET

from panflow.nlq.processor import NLQProcessor
from panflow.nlq.intent_parser import IntentParser
from panflow.nlq.entity_extractor import EntityExtractor
from panflow.nlq.command_mapper import CommandMapper

# Sample XML configuration for testing
SAMPLE_CONFIG = """
<config>
  <devices>
    <entry name="localhost.localdomain">
      <device-group>
        <entry name="test-dg">
          <pre-rulebase>
            <security>
              <rules>
                <entry name="test-policy-1">
                  <action>allow</action>
                  <from>
                    <member>any</member>
                  </from>
                  <to>
                    <member>any</member>
                  </to>
                  <source>
                    <member>any</member>
                  </source>
                  <destination>
                    <member>any</member>
                  </destination>
                  <service>
                    <member>any</member>
                  </service>
                  <application>
                    <member>any</member>
                  </application>
                </entry>
                <entry name="test-policy-2">
                  <action>deny</action>
                  <from>
                    <member>any</member>
                  </from>
                  <to>
                    <member>any</member>
                  </to>
                  <source>
                    <member>any</member>
                  </source>
                  <destination>
                    <member>any</member>
                  </destination>
                  <service>
                    <member>any</member>
                  </service>
                  <application>
                    <member>any</member>
                  </application>
                  <disabled>yes</disabled>
                </entry>
              </rules>
            </security>
          </pre-rulebase>
        </entry>
      </device-group>
    </entry>
  </devices>
  <shared>
    <pre-rulebase>
      <security>
        <rules>
          <entry name="shared-policy-1">
            <action>allow</action>
            <from>
              <member>any</member>
            </from>
            <to>
              <member>any</member>
            </to>
            <source>
              <member>any</member>
            </source>
            <destination>
              <member>any</member>
            </destination>
            <service>
              <member>any</member>
            </service>
            <application>
              <member>any</member>
            </application>
          </entry>
        </rules>
      </security>
    </pre-rulebase>
  </shared>
</config>
"""


class TestBulkOperations(unittest.TestCase):
    """Test cases for bulk operations in NLQ module."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create sample config file
        self.config_file = os.path.join(self.test_dir, "test_config.xml")
        with open(self.config_file, "w") as f:
            f.write(SAMPLE_CONFIG)
        
        # Output file
        self.output_file = os.path.join(self.test_dir, "output.xml")
        
        # Initialize processor
        self.processor = NLQProcessor(use_ai=False)  # Use pattern-based for consistent testing
        
        # Instead of mocking properties, we'll mock the entire class and its methods
        self.panflow_config_patcher = patch('panflow.nlq.processor.PANFlowConfig')
        self.mock_panflow_config = self.panflow_config_patcher.start()

        # Create a mock instance that will be returned when PANFlowConfig is instantiated
        self.mock_config_instance = Mock()
        self.mock_config_instance.device_type = "panorama"
        self.mock_config_instance.version = "10.2.0"

        # Make the mock class return our mock instance when instantiated
        self.mock_panflow_config.return_value = self.mock_config_instance

        # Create mock XML elements for testing
        self.mock_config_instance.tree = Mock()
        mock_policy_element = Mock()
        mock_tag_element = Mock()
        mock_tag_element.text = "test-tag"
        mock_policy_element.find.return_value = mock_tag_element
        self.mock_config_instance.tree.xpath.return_value = [mock_policy_element]

    def tearDown(self):
        """Clean up after tests."""
        # Remove the test directory
        shutil.rmtree(self.test_dir)

        # Stop patchers
        self.panflow_config_patcher.stop()

    def test_add_tag_operation(self):
        """Test adding a tag to policies."""
        # Mock the tree.write operation to prevent actual file writing
        self.mock_config_instance.tree.write = Mock()

        # Setup mock for get_policies method to return some test policies
        self.mock_config_instance.get_policies = Mock(return_value={
            "test-policy-1": {"action": "allow"},
            "test-policy-2": {"action": "deny", "disabled": "yes"},
            "shared-policy-1": {"action": "allow"},
        })

        # Setup ConfigQuery mock to return policy names
        with patch('panflow.nlq.processor.ConfigQuery') as mock_config_query:
            # Create mock instance with select_policies that returns policy names
            mock_query_instance = Mock()
            mock_query_instance.select_policies.return_value = [
                {"name": "test-policy-1"},
                {"name": "test-policy-2"},
                {"name": "shared-policy-1"}
            ]
            mock_config_query.return_value = mock_query_instance

            # Process the query
            result = self.processor.process(
                "add tag 'test-tag' to all security policies",
                self.config_file,
                self.output_file
            )

        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")

        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)

        # Verify operation type and value
        self.assertEqual(result_data.get("operation"), "add_tag")
        self.assertEqual(result_data.get("value"), "test-tag")

        # Verify the tree.write method was called with the output file
        self.mock_config_instance.tree.write.assert_called_once_with(
            self.output_file, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )

    def test_enable_operation(self):
        """Test enabling policies."""
        # Process the query
        result = self.processor.process(
            "enable all security policies",
            self.config_file,
            self.output_file
        )
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")
        
        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)
        
        # Verify operation type
        self.assertEqual(result_data.get("operation"), "enable")
        
        # Check output file was created
        self.assertTrue(os.path.exists(self.output_file))
        
        # Verify XML content - test-policy-2 should no longer have disabled element
        tree = ET.parse(self.output_file)
        policies = tree.xpath('//entry[@name="test-policy-2"]/disabled')
        self.assertEqual(len(policies), 0, "Disabled element was not removed from test-policy-2")

    def test_disable_operation(self):
        """Test disabling policies."""
        # Process the query
        result = self.processor.process(
            "disable all security policies",
            self.config_file,
            self.output_file
        )
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")
        
        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)
        
        # Verify operation type
        self.assertEqual(result_data.get("operation"), "disable")
        
        # Check output file was created
        self.assertTrue(os.path.exists(self.output_file))
        
        # Verify XML content - all policies should have disabled element
        tree = ET.parse(self.output_file)
        
        policies = tree.xpath('//entry[@name="test-policy-1"]/disabled')
        self.assertGreaterEqual(len(policies), 1, "Disabled element was not added to test-policy-1")
        self.assertEqual(policies[0].text, "yes")
        
        policies = tree.xpath('//entry[@name="shared-policy-1"]/disabled')
        self.assertGreaterEqual(len(policies), 1, "Disabled element was not added to shared-policy-1")
        self.assertEqual(policies[0].text, "yes")

    def test_set_action_operation(self):
        """Test setting policy actions."""
        # Process the query
        result = self.processor.process(
            "set action to deny for all security policies",
            self.config_file,
            self.output_file
        )
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")
        
        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)
        
        # Verify operation type and value
        self.assertEqual(result_data.get("operation"), "set_action")
        self.assertEqual(result_data.get("value"), "deny")
        
        # Check output file was created
        self.assertTrue(os.path.exists(self.output_file))
        
        # Verify XML content - policies should have action set to deny
        tree = ET.parse(self.output_file)
        
        policies = tree.xpath('//entry[@name="test-policy-1"]/action')
        self.assertGreaterEqual(len(policies), 1, "Action element not found in test-policy-1")
        self.assertEqual(policies[0].text, "deny", "Action not set to deny for test-policy-1")
        
        policies = tree.xpath('//entry[@name="shared-policy-1"]/action')
        self.assertGreaterEqual(len(policies), 1, "Action element not found in shared-policy-1")
        self.assertEqual(policies[0].text, "deny", "Action not set to deny for shared-policy-1")

    def test_enable_logging_operation(self):
        """Test enabling logging for policies."""
        # Process the query
        result = self.processor.process(
            "enable logging for all security policies",
            self.config_file,
            self.output_file
        )
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")
        
        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)
        
        # Verify operation type
        self.assertEqual(result_data.get("operation"), "enable_logging")
        
        # Check output file was created
        self.assertTrue(os.path.exists(self.output_file))
        
        # Verify XML content - policies should have log-start and log-end elements
        tree = ET.parse(self.output_file)
        
        for policy_name in ["test-policy-1", "test-policy-2", "shared-policy-1"]:
            for log_type in ["log-start", "log-end"]:
                elements = tree.xpath(f'//entry[@name="{policy_name}"]/{log_type}')
                self.assertGreaterEqual(len(elements), 1, f"{log_type} element not added to {policy_name}")
                self.assertEqual(elements[0].text, "yes", f"{log_type} not set properly for {policy_name}")

    def test_disable_logging_operation(self):
        """Test disabling logging for policies."""
        # First enable logging to ensure we have log elements
        self.processor.process(
            "enable logging for all security policies",
            self.config_file,
            self.output_file
        )
        
        # Then disable logging
        result = self.processor.process(
            "disable logging for all security policies",
            self.output_file,  # Use the output from previous command as input
            self.output_file   # Overwrite the same file
        )
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["intent"], "bulk_update_policies")
        
        # Check result data
        self.assertIn("result", result)
        result_data = result["result"]
        self.assertIn("updated_policies", result_data)
        
        # Verify operation type
        self.assertEqual(result_data.get("operation"), "disable_logging")
        
        # Verify XML content - log elements should have "no" value
        tree = ET.parse(self.output_file)
        
        for policy_name in ["test-policy-1", "test-policy-2", "shared-policy-1"]:
            for log_type in ["log-start", "log-end"]:
                elements = tree.xpath(f'//entry[@name="{policy_name}"]/{log_type}')
                if elements:  # If the element exists
                    self.assertEqual(elements[0].text, "no", f"{log_type} not set to 'no' for {policy_name}")

    def test_entity_extraction_for_bulk_operations(self):
        """Test entity extraction for bulk operations."""
        # This test doesn't need any mocking since we're directly testing the EntityExtractor class
        try:
            extractor = EntityExtractor()

            # Test add_tag operation
            entities = extractor.extract("add tag 'test-tag' to all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "add_tag")
            self.assertEqual(entities["bulk_operation"]["value"], "test-tag")

            # Test set_action operation
            entities = extractor.extract("set action to deny for all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "set_action")
            self.assertEqual(entities["bulk_operation"]["value"], "deny")

            # Test enable operation
            entities = extractor.extract("enable all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "enable")

            # Test disable operation
            entities = extractor.extract("disable all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "disable")

            # Test enable_logging operation
            entities = extractor.extract("enable logging for all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "enable_logging")

            # Test disable_logging operation
            entities = extractor.extract("disable logging for all security policies")
            self.assertIn("bulk_operation", entities)
            self.assertEqual(entities["bulk_operation"]["operation"], "disable_logging")
        except ImportError:
            self.skipTest("EntityExtractor could not be imported")
        
    def test_command_mapping_for_bulk_operations(self):
        """Test command mapping for bulk operations."""
        # This test also doesn't need mocking as we're testing the CommandMapper directly
        try:
            mapper = CommandMapper()

            # Test mapping for bulk update operations
            command_args = mapper.map(
                "bulk_update_policies",
                {
                    "bulk_operation": {
                        "operation": "add_tag",
                        "value": "test-tag"
                    },
                    "policy_type": "security_rules"
                },
                self.config_file,
                self.output_file
            )

            self.assertEqual(command_args["command"], "bulk_update_policies")
            self.assertEqual(command_args["operation"], "add_tag")
            self.assertEqual(command_args["value"], "test-tag")
            self.assertEqual(command_args["policy_type"], "security_rules")
            self.assertEqual(command_args["config"], self.config_file)
            self.assertEqual(command_args["output"], self.output_file)
        except ImportError:
            self.skipTest("CommandMapper could not be imported")


if __name__ == "__main__":
    unittest.main()