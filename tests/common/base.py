"""
Base test classes for PANFlow tests.

This module provides base classes that encapsulate common test patterns
and utilities, making it easier to write consistent tests.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from unittest.mock import MagicMock, patch

from lxml import etree
from typer.testing import CliRunner

from panflow import PANFlowConfig
from panflow.cli.app import app


class BaseTestCase(unittest.TestCase):
    """Base class for all PANFlow tests."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Common test data
        self.sample_version = "10.2"
        self.sample_device_type = "firewall"
        
    def create_temp_file(self, content: str, suffix: str = ".xml") -> str:
        """Create a temporary file with the given content."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            dir=self.test_dir,
            delete=False
        )
        temp_file.write(content)
        temp_file.close()
        return temp_file.name
    
    def assert_xml_equal(self, xml1: etree._Element, xml2: etree._Element):
        """Assert that two XML elements are equal."""
        # Compare tag names
        self.assertEqual(xml1.tag, xml2.tag)
        
        # Compare attributes
        self.assertEqual(dict(xml1.attrib), dict(xml2.attrib))
        
        # Compare text content
        text1 = (xml1.text or "").strip()
        text2 = (xml2.text or "").strip()
        self.assertEqual(text1, text2)
        
        # Compare children
        children1 = list(xml1)
        children2 = list(xml2)
        self.assertEqual(len(children1), len(children2))
        
        for child1, child2 in zip(children1, children2):
            self.assert_xml_equal(child1, child2)
    
    def assert_xpath_exists(self, tree: etree._ElementTree, xpath: str):
        """Assert that an XPath expression finds at least one element."""
        elements = tree.xpath(xpath)
        self.assertTrue(
            len(elements) > 0,
            f"XPath '{xpath}' did not find any elements"
        )
    
    def assert_xpath_count(self, tree: etree._ElementTree, xpath: str, count: int):
        """Assert that an XPath expression finds exactly 'count' elements."""
        elements = tree.xpath(xpath)
        self.assertEqual(
            len(elements), count,
            f"XPath '{xpath}' found {len(elements)} elements, expected {count}"
        )


class CLITestCase(BaseTestCase):
    """Base class for CLI command tests."""
    
    def setUp(self):
        """Set up CLI test environment."""
        super().setUp()
        self.runner = CliRunner()
        
        # Create sample configuration files
        self.sample_config = self.create_sample_config()
        self.sample_config_file = self.create_temp_file(self.sample_config)
        
    def create_sample_config(self) -> str:
        """Create a sample configuration for testing. Override in subclasses."""
        return """
        <config version="10.2.0">
            <shared>
                <address/>
                <service/>
            </shared>
        </config>
        """
    
    def invoke_command(self, command_args: List[str], **kwargs) -> Any:
        """Invoke a CLI command and return the result."""
        # Ensure config file is included if not specified
        if "--config" not in command_args and "-c" not in command_args:
            command_args.extend(["--config", self.sample_config_file])
        
        result = self.runner.invoke(app, command_args, **kwargs)
        return result
    
    def assert_command_success(self, result):
        """Assert that a command executed successfully."""
        if result.exit_code != 0:
            # Print helpful debugging information
            print(f"Command failed with exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
        
        self.assertEqual(result.exit_code, 0)
    
    def assert_command_error(self, result, expected_error: Optional[str] = None):
        """Assert that a command failed with an error."""
        self.assertNotEqual(result.exit_code, 0)
        
        if expected_error:
            self.assertIn(expected_error, result.output)
    
    def assert_output_contains(self, result, expected: str):
        """Assert that command output contains expected text."""
        self.assertIn(expected, result.output)
    
    def assert_json_output(self, result) -> Dict[str, Any]:
        """Assert that output is valid JSON and return parsed data."""
        import json
        
        try:
            data = json.loads(result.output)
            return data
        except json.JSONDecodeError as e:
            self.fail(f"Output is not valid JSON: {e}\nOutput: {result.output}")


class XMLTestCase(BaseTestCase):
    """Base class for XML manipulation tests."""
    
    def setUp(self):
        """Set up XML test environment."""
        super().setUp()
        
        # Create mock XPath resolver
        self.mock_xpath_resolver = self.create_mock_xpath_resolver()
    
    def create_mock_xpath_resolver(self) -> MagicMock:
        """Create a mock XPath resolver."""
        mock = MagicMock()
        
        # Common XPath patterns
        mock.get_object_xpath = MagicMock(
            side_effect=self._mock_get_object_xpath
        )
        mock.get_policy_xpath = MagicMock(
            side_effect=self._mock_get_policy_xpath
        )
        mock.get_context_xpath = MagicMock(
            side_effect=self._mock_get_context_xpath
        )
        
        return mock
    
    def _mock_get_object_xpath(
        self,
        object_type: str,
        device_type: str,
        context_type: str,
        version: str,
        object_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Mock implementation of get_object_xpath."""
        base_paths = {
            "firewall": {
                "shared": "/config/shared",
                "vsys": "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']"
            },
            "panorama": {
                "shared": "/config/shared",
                "device_group": "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']"
            }
        }
        
        base = base_paths.get(device_type, {}).get(context_type, "/config/shared")
        
        # Format with context parameters
        if context_type == "vsys":
            base = base.format(vsys=kwargs.get("vsys", "vsys1"))
        elif context_type == "device_group":
            base = base.format(device_group=kwargs.get("device_group", "DG1"))
        
        # Add object type
        xpath = f"{base}/{object_type}/entry"
        
        # Add object name if specified
        if object_name:
            xpath += f"[@name='{object_name}']"
        
        return xpath
    
    def _mock_get_policy_xpath(
        self,
        policy_type: str,
        device_type: str,
        context_type: str,
        version: str,
        **kwargs
    ) -> str:
        """Mock implementation of get_policy_xpath."""
        # Similar to object xpath but for policies
        base_paths = {
            "firewall": {
                "shared": "/config/shared/rulebase",
                "vsys": "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']/rulebase"
            },
            "panorama": {
                "shared": "/config/shared/pre-rulebase",
                "device_group": "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/pre-rulebase"
            }
        }
        
        base = base_paths.get(device_type, {}).get(context_type, "/config/shared/rulebase")
        
        # Format with context parameters
        if context_type == "vsys":
            base = base.format(vsys=kwargs.get("vsys", "vsys1"))
        elif context_type == "device_group":
            base = base.format(device_group=kwargs.get("device_group", "DG1"))
        
        # Extract policy category (security, nat, etc.)
        policy_category = policy_type.replace("_rules", "").replace("_pre", "").replace("_post", "")
        
        return f"{base}/{policy_category}/rules/entry"
    
    def _mock_get_context_xpath(
        self,
        device_type: str,
        context_type: str,
        version: str,
        **kwargs
    ) -> str:
        """Mock implementation of get_context_xpath."""
        context_paths = {
            "firewall": {
                "shared": "/config/shared",
                "vsys": "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']"
            },
            "panorama": {
                "shared": "/config/shared",
                "device_group": "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']"
            }
        }
        
        xpath = context_paths.get(device_type, {}).get(context_type, "/config/shared")
        
        # Format with context parameters
        if context_type == "vsys":
            xpath = xpath.format(vsys=kwargs.get("vsys", "vsys1"))
        elif context_type == "device_group":
            xpath = xpath.format(device_group=kwargs.get("device_group", "DG1"))
        
        return xpath
    
    def create_element_at_xpath(
        self,
        tree: etree._ElementTree,
        xpath: str,
        element: etree._Element
    ):
        """Create an element at the specified XPath location."""
        # Parse the XPath to find parent and create if needed
        parts = xpath.split("/")
        current = tree.getroot()
        
        for part in parts[2:]:  # Skip empty string and 'config'
            if not part:
                continue
            
            # Handle attribute predicates
            if "[" in part:
                tag = part.split("[")[0]
                # Extract attribute name and value
                attr_part = part[part.index("[")+1:part.index("]")]
                attr_name = attr_part.split("=")[0].replace("@", "")
                attr_value = attr_part.split("=")[1].strip("'\"")
                
                # Find or create element with attribute
                found = False
                for child in current:
                    if child.tag == tag and child.get(attr_name) == attr_value:
                        current = child
                        found = True
                        break
                
                if not found:
                    new_elem = etree.SubElement(current, tag)
                    new_elem.set(attr_name, attr_value)
                    current = new_elem
            else:
                # Find or create element
                child = current.find(part)
                if child is None:
                    child = etree.SubElement(current, part)
                current = child
        
        # Add the element
        current.append(element)


# Utility class for performance testing
class PerformanceTestCase(BaseTestCase):
    """Base class for performance tests."""
    
    def setUp(self):
        """Set up performance test environment."""
        super().setUp()
        self.performance_results = []
    
    def measure_performance(self, func, *args, **kwargs):
        """Measure the performance of a function."""
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.performance_results.append({
            "function": func.__name__,
            "execution_time": execution_time,
            "args": args,
            "kwargs": kwargs
        })
        
        return result, execution_time
    
    def assert_performance(self, execution_time: float, max_time: float):
        """Assert that execution time is within acceptable limits."""
        self.assertLessEqual(
            execution_time, max_time,
            f"Execution took {execution_time:.3f}s, expected less than {max_time:.3f}s"
        )
    
    def tearDown(self):
        """Clean up and report performance results."""
        super().tearDown()
        
        if self.performance_results:
            print("\nPerformance Results:")
            for result in self.performance_results:
                print(f"  {result['function']}: {result['execution_time']:.3f}s")