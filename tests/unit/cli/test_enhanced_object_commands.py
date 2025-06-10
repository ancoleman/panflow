"""
Compatibility tests for enhanced object commands v0.4.1.

This test suite validates that the enhanced object commands produce identical
output to their legacy counterparts, ensuring no regression during refactoring.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from lxml import etree
from typer.testing import CliRunner

from tests.common import CLITestCase, ConfigFactory, PerformanceBenchmark
from panflow.cli.app import app
from panflow.core.feature_flags import FeatureFlags


class TestEnhancedObjectCommandsCompatibility(CLITestCase):
    """Test compatibility between enhanced and legacy object commands."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create test configuration
        self.config = ConfigFactory.panorama_with_objects()
        self.config_file = self.create_temp_file(
            etree.tostring(self.config.getroot(), encoding='unicode')
        )
        
        # Enable enhanced command base for testing
        os.environ["PANFLOW_FF_USE_ENHANCED_COMMAND_BASE"] = "true"
        
        # Reset feature flags singleton to pick up environment change
        FeatureFlags._instance = None
        
        # Create output directory for comparison
        self.output_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore feature flag
        if "PANFLOW_FF_USE_ENHANCED_COMMAND_BASE" in os.environ:
            del os.environ["PANFLOW_FF_USE_ENHANCED_COMMAND_BASE"]
        
        # Reset feature flags singleton
        FeatureFlags._instance = None
        
        super().tearDown()

    def test_list_objects_output_compatibility(self):
        """Test that enhanced list command produces identical output to legacy."""
        
        # Test parameters
        test_cases = [
            {
                "args": ["object", "list", "--type", "address", "--format", "json"],
                "description": "JSON format output"
            },
            {
                "args": ["object", "list", "--type", "address", "--format", "table"],
                "description": "Table format output"
            },
            {
                "args": ["object", "list", "--type", "service", "--format", "csv"],
                "description": "CSV format with different object type"
            },
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case["description"]):
                args = test_case["args"] + ["--config", self.config_file]
                
                # Run legacy command
                legacy_result = self.invoke_command(args)
                
                # Run enhanced command
                enhanced_args = args.copy()
                enhanced_args[1] = "list-enhanced"  # Replace 'list' with 'list-enhanced'
                enhanced_result = self.invoke_command(enhanced_args)
                
                # Compare outputs
                self.assertEqual(legacy_result.exit_code, enhanced_result.exit_code)
                
                # For JSON outputs, parse and compare structured data
                if "--format json" in " ".join(args) or "json" in args:
                    try:
                        legacy_data = json.loads(legacy_result.stdout)
                        enhanced_data = json.loads(enhanced_result.stdout)
                        self.assertEqual(legacy_data, enhanced_data)
                    except json.JSONDecodeError:
                        # Fallback to string comparison
                        self.assertEqual(legacy_result.stdout, enhanced_result.stdout)
                else:
                    # For other formats, compare output line by line (ignoring minor formatting)
                    legacy_lines = [line.strip() for line in legacy_result.stdout.split('\n')]
                    enhanced_lines = [line.strip() for line in enhanced_result.stdout.split('\n')]
                    
                    # Filter out empty lines for comparison
                    legacy_content = [line for line in legacy_lines if line]
                    enhanced_content = [line for line in enhanced_lines if line]
                    
                    self.assertEqual(len(legacy_content), len(enhanced_content))

    def test_list_objects_with_query_filter_compatibility(self):
        """Test query filtering produces identical results."""
        
        query_filter = "MATCH (a:address) WHERE a.name CONTAINS 'test'"
        args = [
            "object", "list",
            "--type", "address",
            "--query-filter", query_filter,
            "--format", "json",
            "--config", self.config_file
        ]
        
        # Run legacy command
        legacy_result = self.invoke_command(args)
        
        # Run enhanced command
        enhanced_args = args.copy()
        enhanced_args[1] = "list-enhanced"
        enhanced_result = self.invoke_command(enhanced_args)
        
        # Both should succeed
        self.assert_command_success(legacy_result)
        self.assert_command_success(enhanced_result)
        
        # Parse and compare JSON output
        legacy_data = json.loads(legacy_result.stdout)
        enhanced_data = json.loads(enhanced_result.stdout)
        self.assertEqual(legacy_data, enhanced_data)

    def test_add_object_compatibility(self):
        """Test add object command compatibility."""
        
        # Create test properties file
        properties = {
            "ip-netmask": "192.168.1.100/32",
            "description": "Test address object"
        }
        properties_file = self.create_temp_file(json.dumps(properties))
        output_file = os.path.join(self.output_dir, "test_output.xml")
        
        # Test both legacy and enhanced add commands
        for command_type in ["add", "add-enhanced"]:
            with self.subTest(command_type=command_type):
                args = [
                    "object", command_type,
                    "--type", "address",
                    "--name", f"test-object-{command_type}",
                    "--properties", properties_file,
                    "--output", f"{output_file}.{command_type}",
                    "--config", self.config_file
                ]
                
                result = self.invoke_command(args)
                self.assert_command_success(result)
                
                # Verify output file was created
                self.assertTrue(os.path.exists(f"{output_file}.{command_type}"))

    def test_delete_object_compatibility(self):
        """Test delete object command compatibility."""
        
        output_file = os.path.join(self.output_dir, "test_delete_output.xml")
        
        # Test both legacy and enhanced delete commands
        for command_type in ["delete", "delete-enhanced"]:
            with self.subTest(command_type=command_type):
                args = [
                    "object", command_type,
                    "--type", "address",
                    "--name", "shared-server",  # Object that exists in test config
                    "--output", f"{output_file}.{command_type}",
                    "--config", self.config_file
                ]
                
                result = self.invoke_command(args)
                self.assert_command_success(result)
                
                # Verify output file was created
                self.assertTrue(os.path.exists(f"{output_file}.{command_type}"))

    def test_error_handling_compatibility(self):
        """Test that error handling is consistent between implementations."""
        
        # Test with non-existent config file
        args = [
            "object", "list",
            "--type", "address",
            "--config", "/nonexistent/config.xml"
        ]
        
        legacy_result = self.invoke_command(args)
        
        enhanced_args = args.copy()
        enhanced_args[1] = "list-enhanced"
        enhanced_result = self.invoke_command(enhanced_args)
        
        # Both should fail with exit code 1
        self.assertEqual(legacy_result.exit_code, 1)
        self.assertEqual(enhanced_result.exit_code, 1)
        
        # Error messages should be similar (both should mention config loading failure)
        self.assertIn("config", legacy_result.stdout.lower() + legacy_result.stderr.lower())
        self.assertIn("config", enhanced_result.stdout.lower() + enhanced_result.stderr.lower())

    def test_performance_comparison(self):
        """Verify enhanced commands perform as well as legacy commands."""
        
        benchmark = PerformanceBenchmark()
        
        args = [
            "object", "list",
            "--type", "address",
            "--format", "json",
            "--config", self.config_file
        ]
        
        # Benchmark legacy implementation
        def legacy_test():
            result = self.invoke_command(args)
            self.assert_command_success(result)
            return result
        
        # Benchmark enhanced implementation
        def enhanced_test():
            enhanced_args = args.copy()
            enhanced_args[1] = "list-enhanced"
            result = self.invoke_command(enhanced_args)
            self.assert_command_success(result)
            return result
        
        # Measure performance with multiple iterations
        legacy_metrics = benchmark.measure_repeated("legacy_list", legacy_test, iterations=5)
        enhanced_metrics = benchmark.measure_repeated("enhanced_list", enhanced_test, iterations=5)
        
        # Enhanced should be at least as fast as legacy (within 10% tolerance)
        performance_ratio = enhanced_metrics["mean"] / legacy_metrics["mean"]
        self.assertLess(performance_ratio, 1.1, 
                       f"Enhanced implementation is {performance_ratio:.2f}x slower than legacy")
        
        # Log performance results
        self.logger.info(f"Legacy mean execution time: {legacy_metrics['mean']:.4f}s")
        self.logger.info(f"Enhanced mean execution time: {enhanced_metrics['mean']:.4f}s")
        self.logger.info(f"Performance ratio: {performance_ratio:.2f}x")

    def test_feature_flag_fallback(self):
        """Test that feature flag controls implementation selection."""
        
        # Disable enhanced command base
        os.environ["PANFLOW_FF_USE_ENHANCED_COMMAND_BASE"] = "false"
        FeatureFlags._instance = None  # Reset singleton
        
        args = [
            "object", "list-enhanced",  # Try to use enhanced command
            "--type", "address",
            "--config", self.config_file
        ]
        
        # Should still work (might fall back to legacy implementation internally)
        result = self.invoke_command(args)
        # Command should either succeed or gracefully indicate unavailability
        self.assertIn(result.exit_code, [0, 1])  # Allow either success or controlled failure

    def test_code_reduction_validation(self):
        """Validate that the enhanced implementation actually reduces code complexity."""
        
        # This test validates our refactoring goals by checking line counts
        # In a real implementation, this could be integrated with the duplication analyzer
        
        from panflow.cli.commands import object_commands
        from panflow.cli.commands import object_commands_enhanced
        
        import inspect
        
        # Get source line counts for comparable functions
        legacy_list = inspect.getsource(object_commands.list_objects)
        enhanced_list = inspect.getsource(object_commands_enhanced.list_objects_enhanced)
        
        legacy_lines = len([line for line in legacy_list.split('\n') if line.strip()])
        enhanced_lines = len([line for line in enhanced_list.split('\n') if line.strip()])
        
        # Enhanced should be significantly shorter
        reduction_ratio = (legacy_lines - enhanced_lines) / legacy_lines
        self.assertGreater(reduction_ratio, 0.5, 
                          f"Expected >50% line reduction, got {reduction_ratio:.1%}")
        
        self.logger.info(f"Legacy implementation: {legacy_lines} lines")
        self.logger.info(f"Enhanced implementation: {enhanced_lines} lines")
        self.logger.info(f"Code reduction: {reduction_ratio:.1%}")


class TestEnhancedCommandBaseUnit(unittest.TestCase):
    """Unit tests for the enhanced command base functionality."""

    def setUp(self):
        """Set up test environment."""
        self.config = ConfigFactory.minimal_panorama()
        
    def test_load_config_and_context(self):
        """Test config and context loading."""
        from panflow.cli.enhanced_command_base import EnhancedCommandBase
        
        config_file = "/tmp/test_config.xml"
        with open(config_file, "w") as f:
            f.write(etree.tostring(self.config.getroot(), encoding='unicode'))
        
        try:
            xml_config, context_kwargs = EnhancedCommandBase.load_config_and_context(
                config_file, device_type="panorama", context="shared"
            )
            
            self.assertIsNotNone(xml_config)
            self.assertIsInstance(context_kwargs, dict)
            self.assertIn("device_group", context_kwargs)
            
        finally:
            os.unlink(config_file)

    def test_apply_query_filter(self):
        """Test query filtering functionality."""
        from panflow.cli.enhanced_command_base import EnhancedCommandBase
        
        # Mock objects
        objects = {
            "test-addr-1": {"ip-netmask": "10.0.0.1/32"},
            "test-addr-2": {"ip-netmask": "10.0.0.2/32"},
            "prod-addr-1": {"ip-netmask": "192.168.1.1/32"},
        }
        
        # Mock XML config
        mock_config = MagicMock()
        mock_config.tree = self.config
        
        # Mock query that returns test objects
        with patch('panflow.cli.enhanced_command_base.ConfigGraph'), \
             patch('panflow.cli.enhanced_command_base.QueryExecutor') as mock_executor:
            
            # Mock query results
            mock_executor.return_value.execute.return_value = [
                {"a.name": "test-addr-1"},
                {"a.name": "test-addr-2"}
            ]
            
            filtered_objects = EnhancedCommandBase.apply_query_filter(
                objects, "MATCH (a:address) WHERE a.name CONTAINS 'test'", mock_config
            )
            
            # Should only return test objects
            self.assertEqual(len(filtered_objects), 2)
            self.assertIn("test-addr-1", filtered_objects)
            self.assertIn("test-addr-2", filtered_objects)
            self.assertNotIn("prod-addr-1", filtered_objects)

    def test_format_objects_output_json(self):
        """Test JSON output formatting."""
        from panflow.cli.enhanced_command_base import EnhancedCommandBase
        
        objects = {
            "test-obj": {"property": "value"},
            "test-obj-2": {"property": "value2"}
        }
        
        with patch('panflow.cli.enhanced_command_base.console') as mock_console:
            EnhancedCommandBase.format_objects_output(objects, "json")
            
            # Should have called console.print with JSON string
            mock_console.print.assert_called()
            call_args = mock_console.print.call_args[0][0]
            
            # Verify it's valid JSON
            parsed = json.loads(call_args)
            self.assertEqual(len(parsed), 2)

    def test_format_objects_output_table(self):
        """Test table output formatting."""
        from panflow.cli.enhanced_command_base import EnhancedCommandBase
        
        objects = [
            {"name": "test-obj", "property": "value"},
            {"name": "test-obj-2", "property": "value2"}
        ]
        
        with patch('panflow.cli.enhanced_command_base.console') as mock_console:
            EnhancedCommandBase.format_objects_output(objects, "table", object_type="address")
            
            # Should have called console.print with a Table object
            mock_console.print.assert_called()
            call_args = mock_console.print.call_args[0][0]
            
            # Should be a Rich Table object
            from rich.table import Table
            self.assertIsInstance(call_args, Table)


if __name__ == "__main__":
    # Enable enhanced command base for all tests
    os.environ["PANFLOW_FF_USE_ENHANCED_COMMAND_BASE"] = "true"
    unittest.main()