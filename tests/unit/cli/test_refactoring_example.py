"""
Example test showing how to use the test suite for refactoring.

This demonstrates refactoring the 'object get' command to reduce duplication
while ensuring backwards compatibility.
"""

import json
from unittest.mock import patch
from lxml import etree

from tests.common import (
    CLITestCase,
    ConfigFactory,
    ObjectFactory,
    MockFactory,
    PerformanceBenchmark,
)
from panflow.core.feature_flags import FeatureFlagContext


class TestObjectGetRefactoring(CLITestCase):
    """
    Test suite to ensure the refactored 'object get' command maintains
    exact compatibility with the original implementation.
    """
    
    def setUp(self):
        """Set up test environment with known objects."""
        super().setUp()
        
        # Create a test configuration with various object types
        self.config_file = self.create_test_config()
        
        # Initialize performance tracking
        self.benchmark = PerformanceBenchmark("object_get_refactoring")
    
    def create_test_config(self):
        """Create a comprehensive test configuration."""
        # Start with base Panorama config
        config = ConfigFactory.minimal_panorama()
        root = config.getroot()
        
        # Add test objects to shared context
        shared = root.find(".//shared")
        
        # Add addresses
        addresses = etree.SubElement(shared, "address")
        addresses.append(ObjectFactory.address_element(
            name="web-server",
            ip_netmask="192.168.1.10/32",
            description="Production web server",
            tags=["production", "web"]
        ))
        addresses.append(ObjectFactory.address_element(
            name="db-server",
            ip_netmask="192.168.2.50/32",
            description="Database server"
        ))
        
        # Add services
        services = etree.SubElement(shared, "service")
        services.append(ObjectFactory.service_element(
            name="custom-https",
            protocol="tcp",
            port="8443",
            description="Custom HTTPS port"
        ))
        
        # Add to device group
        dg = root.find(".//device-group/entry[@name='test-dg']")
        if dg is None:
            device_group = root.find(".//device-group")
            if device_group is None:
                devices = root.find(".//devices/entry[@name='localhost.localdomain']")
                device_group = etree.SubElement(devices, "device-group")
            dg = etree.SubElement(device_group, "entry", name="test-dg")
        
        dg_addresses = etree.SubElement(dg, "address")
        dg_addresses.append(ObjectFactory.address_element(
            name="local-server",
            ip_netmask="10.0.0.1/32"
        ))
        
        # Save to temp file
        return self.create_temp_file(etree.tostring(root, pretty_print=True).decode())
    
    def test_get_object_output_compatibility(self):
        """Ensure output format remains identical after refactoring."""
        test_cases = [
            # (object_type, name, context, expected_in_output)
            ("address", "web-server", "shared", "192.168.1.10/32"),
            ("address", "local-server", "device_group", "10.0.0.1/32"),
            ("service", "custom-https", "shared", "8443"),
        ]
        
        for obj_type, name, context, expected in test_cases:
            with self.subTest(type=obj_type, name=name, context=context):
                # Test with original implementation
                with FeatureFlagContext(use_enhanced_command_base=False):
                    old_result = self.invoke_command([
                        "object", "get",
                        "--type", obj_type,
                        "--name", name,
                        "--context", context,
                        "--device-group", "test-dg" if context == "device_group" else None,
                    ])
                
                # Test with refactored implementation
                with FeatureFlagContext(use_enhanced_command_base=True):
                    new_result = self.invoke_command([
                        "object", "get",
                        "--type", obj_type,
                        "--name", name,
                        "--context", context,
                        "--device-group", "test-dg" if context == "device_group" else None,
                    ])
                
                # Both should succeed
                self.assert_command_success(old_result)
                self.assert_command_success(new_result)
                
                # Output should be identical
                self.assertEqual(old_result.output, new_result.output)
                
                # Verify expected content
                self.assertIn(expected, new_result.output)
    
    def test_error_handling_compatibility(self):
        """Ensure error cases are handled identically."""
        error_cases = [
            # (object_type, name, error_message)
            ("address", "nonexistent", "not found"),
            ("invalid_type", "any", "Invalid object type"),
            ("service", "", "Name is required"),
        ]
        
        for obj_type, name, expected_error in error_cases:
            with self.subTest(type=obj_type, name=name):
                # Test old implementation
                with FeatureFlagContext(use_enhanced_command_base=False):
                    old_result = self.invoke_command([
                        "object", "get",
                        "--type", obj_type,
                        "--name", name,
                    ])
                
                # Test new implementation
                with FeatureFlagContext(use_enhanced_command_base=True):
                    new_result = self.invoke_command([
                        "object", "get",
                        "--type", obj_type,
                        "--name", name,
                    ])
                
                # Both should fail
                self.assert_command_error(old_result)
                self.assert_command_error(new_result)
                
                # Error messages should be similar
                self.assertIn(expected_error.lower(), old_result.output.lower())
                self.assertIn(expected_error.lower(), new_result.output.lower())
    
    def test_all_output_formats(self):
        """Test all output formats work correctly."""
        formats = ["json", "yaml", "table", "csv", "text"]
        
        for format_type in formats:
            with self.subTest(format=format_type):
                # Run with new implementation
                with FeatureFlagContext(use_enhanced_command_base=True):
                    result = self.invoke_command([
                        "object", "get",
                        "--type", "address",
                        "--name", "web-server",
                        "--format", format_type,
                    ])
                
                self.assert_command_success(result)
                
                # Verify format-specific output
                if format_type == "json":
                    data = json.loads(result.output)
                    self.assertEqual(data["name"], "web-server")
                elif format_type == "table":
                    self.assertIn("│", result.output)  # Table borders
                elif format_type == "csv":
                    self.assertIn(",", result.output)  # CSV delimiter
    
    def test_performance_comparison(self):
        """Compare performance between old and new implementations."""
        # Create a larger config for performance testing
        large_config = self.create_large_test_config(object_count=100)
        
        # Measure old implementation
        with FeatureFlagContext(use_enhanced_command_base=False):
            old_result, old_time = self.benchmark.measure(
                "get_object_old",
                lambda: self.invoke_command([
                    "object", "get",
                    "--config", large_config,
                    "--type", "address", 
                    "--name", "addr-50",
                ])
            )
        
        # Measure new implementation
        with FeatureFlagContext(use_enhanced_command_base=True):
            new_result, new_time = self.benchmark.measure(
                "get_object_new",
                lambda: self.invoke_command([
                    "object", "get",
                    "--config", large_config,
                    "--type", "address",
                    "--name", "addr-50",
                ])
            )
        
        # New implementation should not be significantly slower
        self.assertLess(new_time, old_time * 1.1, 
                       f"New implementation is >10% slower: {new_time:.3f}s vs {old_time:.3f}s")
        
        # Print performance comparison
        print(f"\nPerformance Comparison:")
        print(f"  Old implementation: {old_time:.3f}s")
        print(f"  New implementation: {new_time:.3f}s")
        print(f"  Difference: {((new_time - old_time) / old_time * 100):+.1f}%")
    
    def create_large_test_config(self, object_count: int):
        """Create a config with many objects for performance testing."""
        config = ConfigFactory.minimal_panorama()
        root = config.getroot()
        shared = root.find(".//shared")
        addresses = etree.SubElement(shared, "address")
        
        # Add many address objects
        for i in range(object_count):
            addresses.append(ObjectFactory.address_element(
                name=f"addr-{i}",
                ip_netmask=f"10.{i // 256}.{i % 256}.1/32",
                description=f"Test address {i}"
            ))
        
        return self.create_temp_file(etree.tostring(root, pretty_print=True).decode())
    
    def test_context_handling(self):
        """Test that context parameters are handled correctly."""
        contexts = [
            ("shared", {}),
            ("device_group", {"device_group": "test-dg"}),
            ("vsys", {"vsys": "vsys1"}),
        ]
        
        for context_type, context_params in contexts:
            with self.subTest(context=context_type):
                # Create appropriate config
                if context_type == "vsys":
                    config = ConfigFactory.firewall_with_vsys()
                else:
                    config = ConfigFactory.minimal_panorama()
                
                config_file = self.create_temp_file(
                    etree.tostring(config.getroot()).decode()
                )
                
                # Build command args
                args = [
                    "object", "get",
                    "--config", config_file,
                    "--type", "address",
                    "--name", "test-obj",
                    "--context", context_type,
                ]
                
                # Add context-specific parameters
                for param, value in context_params.items():
                    args.extend([f"--{param.replace('_', '-')}", value])
                
                # Test both implementations handle context correctly
                with FeatureFlagContext(use_enhanced_command_base=False):
                    old_result = self.invoke_command(args)
                
                with FeatureFlagContext(use_enhanced_command_base=True):
                    new_result = self.invoke_command(args)
                
                # Both should handle missing object the same way
                self.assertEqual(old_result.exit_code, new_result.exit_code)


class TestRefactoringMetrics(CLITestCase):
    """Track metrics to measure refactoring success."""
    
    def test_code_reduction_metrics(self):
        """Measure code reduction achieved by refactoring."""
        # This would analyze actual source files
        # For now, we'll use mock data to show the concept
        
        original_lines = 150  # Lines in original get command
        refactored_lines = 25  # Lines in refactored version
        shared_base_lines = 200  # Lines in shared base class
        
        # Calculate metrics
        commands_refactored = 12  # Number of commands
        reduction_per_command = original_lines - refactored_lines
        total_reduction = (reduction_per_command * commands_refactored) - shared_base_lines
        
        print(f"\nRefactoring Metrics:")
        print(f"  Original lines per command: {original_lines}")
        print(f"  Refactored lines per command: {refactored_lines}")
        print(f"  Reduction per command: {reduction_per_command} ({reduction_per_command/original_lines*100:.1f}%)")
        print(f"  Total commands refactored: {commands_refactored}")
        print(f"  Shared base class lines: {shared_base_lines}")
        print(f"  Net reduction: {total_reduction} lines")
        print(f"  Overall reduction: {total_reduction/(original_lines*commands_refactored)*100:.1f}%")
        
        # Assert we're meeting our targets
        self.assertGreater(reduction_per_command/original_lines, 0.6, 
                          "Should achieve >60% reduction per command")


if __name__ == "__main__":
    # Run specific test with verbose output
    import pytest
    pytest.main([__file__, "-v", "-s"])