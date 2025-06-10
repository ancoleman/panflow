"""
Test the common test utilities to ensure they work correctly.
"""

import pytest
import tempfile
import os
from lxml import etree

from tests.common import (
    # Fixtures
    firewall_config,
    panorama_config,
    panorama_with_objects,
    sample_address_objects,
    # Factories
    ConfigFactory,
    MockFactory,
    ObjectFactory,
    PolicyFactory,
    # Base classes
    BaseTestCase,
    CLITestCase,
    XMLTestCase,
    # Benchmarks
    PerformanceBenchmark,
    benchmark,
)


def test_config_factory():
    """Test ConfigFactory creates valid configurations."""
    # Test minimal firewall
    fw_config = ConfigFactory.minimal_firewall()
    assert fw_config is not None
    assert fw_config.getroot().tag == "config"
    assert fw_config.xpath("//vsys")
    
    # Test minimal panorama
    pan_config = ConfigFactory.minimal_panorama()
    assert pan_config is not None
    assert pan_config.xpath("//device-group") is not None
    
    # Test panorama with hierarchy
    hier_config = ConfigFactory.panorama_with_hierarchy()
    assert hier_config.xpath("//device-group/entry[@name='Parent-DG']")
    assert hier_config.xpath("//device-group/entry[@name='Child-DG-1']")


def test_mock_factory():
    """Test MockFactory creates proper mocks."""
    # Test xpath_search mock
    mock_xpath = MockFactory.xpath_search([1, 2, 3])
    assert mock_xpath() == [1, 2, 3]
    
    # Test panflow_config mock
    mock_config = MockFactory.panflow_config(device_type="panorama")
    assert mock_config.device_type == "panorama"
    assert mock_config.version == "10.2"
    
    # Test CLI runner result mock
    mock_result = MockFactory.cli_runner_result(exit_code=0, output="Success")
    assert mock_result.exit_code == 0
    assert mock_result.output == "Success"


def test_object_factory():
    """Test ObjectFactory creates valid XML elements."""
    # Test address element
    addr = ObjectFactory.address_element(
        name="test-addr",
        ip_netmask="10.0.0.1/32",
        description="Test address",
        tags=["test", "production"]
    )
    assert addr.get("name") == "test-addr"
    assert addr.find("ip-netmask").text == "10.0.0.1/32"
    assert addr.find("description").text == "Test address"
    assert len(addr.findall(".//tag/member")) == 2
    
    # Test service element
    svc = ObjectFactory.service_element(
        name="test-svc",
        protocol="tcp",
        port="8080"
    )
    assert svc.get("name") == "test-svc"
    assert svc.find(".//tcp/port").text == "8080"


def test_policy_factory():
    """Test PolicyFactory creates valid policy elements."""
    # Test security rule
    rule = PolicyFactory.security_rule_element(
        name="test-rule",
        action="allow",
        from_zones=["trust"],
        to_zones=["untrust"],
        source=["10.0.0.0/8"],
        destination=["any"],
        service=["tcp-80", "tcp-443"],
        application=["web-browsing", "ssl"]
    )
    
    assert rule.get("name") == "test-rule"
    assert rule.find("action").text == "allow"
    assert len(rule.findall(".//from/member")) == 1
    assert len(rule.findall(".//service/member")) == 2


def test_fixtures(firewall_config, panorama_config, sample_address_objects):
    """Test that fixtures work correctly."""
    # Test firewall config
    assert firewall_config is not None
    assert firewall_config.getroot().tag == "config"
    
    # Test panorama config
    assert panorama_config is not None
    assert panorama_config.getroot().tag == "config"
    
    # Test sample objects
    assert len(sample_address_objects) == 4
    assert sample_address_objects[0]["name"] == "web-server-1"


class TestBaseTestCase(BaseTestCase):
    """Test the BaseTestCase functionality."""
    
    def test_create_temp_file(self):
        """Test temporary file creation."""
        content = "<test>data</test>"
        temp_file = self.create_temp_file(content)
        
        with open(temp_file, 'r') as f:
            assert f.read() == content
    
    def test_assert_xml_equal(self):
        """Test XML comparison."""
        xml1 = etree.fromstring('<root><child attr="value">text</child></root>')
        xml2 = etree.fromstring('<root><child attr="value">text</child></root>')
        
        self.assert_xml_equal(xml1, xml2)
        
        # Test with different XML
        xml3 = etree.fromstring('<root><child attr="different">text</child></root>')
        with pytest.raises(AssertionError):
            self.assert_xml_equal(xml1, xml3)
    
    def test_assert_xpath_exists(self):
        """Test XPath existence assertion."""
        tree = etree.ElementTree(etree.fromstring('<root><child/></root>'))
        
        self.assert_xpath_exists(tree, "//child")
        
        with pytest.raises(AssertionError):
            self.assert_xpath_exists(tree, "//nonexistent")


def test_performance_benchmark():
    """Test performance benchmarking utilities."""
    bench = PerformanceBenchmark("test_bench")
    
    # Test single measurement
    def slow_function():
        import time
        time.sleep(0.01)
        return "result"
    
    result, exec_time = bench.measure("slow_test", slow_function)
    assert result == "result"
    assert exec_time > 0.01
    
    # Test repeated measurements
    stats = bench.measure_repeated("repeated_test", slow_function, iterations=3, warmup=1)
    assert stats["iterations"] == 3
    assert stats["mean"] > 0.01
    assert "median" in stats
    assert "min" in stats
    assert "max" in stats


@benchmark(name="decorated_function", iterations=3)
def test_benchmark_decorator():
    """Test the benchmark decorator."""
    # This function will be automatically benchmarked
    total = sum(range(1000))
    return total


def test_feature_flags():
    """Test feature flags functionality."""
    from panflow.core.feature_flags import FeatureFlags, is_enabled, enable, disable
    
    # Test singleton
    ff1 = FeatureFlags()
    ff2 = FeatureFlags()
    assert ff1 is ff2
    
    # Test enable/disable
    enable("test_feature")
    assert is_enabled("test_feature")
    
    disable("test_feature")
    assert not is_enabled("test_feature")
    
    # Test default flags
    assert isinstance(is_enabled("use_test_utilities"), bool)


def test_duplication_analyzer():
    """Test code duplication analyzer."""
    from tests.common.duplication_analyzer import CodeBlock, DuplicationAnalyzer
    
    # Test code block
    block1 = CodeBlock("test.py", 1, 10, "def test():\n    pass")
    block2 = CodeBlock("test.py", 20, 30, "def test():\n    pass")
    
    assert block1.hash == block2.hash
    assert block1.similarity(block2) == 1.0
    
    # Test analyzer
    analyzer = DuplicationAnalyzer(min_lines=2)
    
    # Create temp file with duplicate code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def function1():
    x = 1
    y = 2
    z = x + y
    return z

def function2():
    x = 1
    y = 2
    z = x + y
    return z
""")
        temp_file = f.name
    
    from pathlib import Path
    analyzer.analyze_file(Path(temp_file))
    analyzer.find_duplicates()
    
    stats = analyzer.get_duplication_stats()
    assert stats["duplicate_groups"] > 0
    
    # Clean up temp file
    os.unlink(temp_file)


def test_compatibility_checker():
    """Test backwards compatibility checker."""
    from tests.common.compatibility_checker import APISignature, CompatibilityChecker
    
    # Test API signature
    sig1 = APISignature("test_func", "function", ["arg1", "arg2"], {"arg2": "default"})
    sig2 = APISignature("test_func", "function", ["arg1", "arg2"], {"arg2": "default"})
    sig3 = APISignature("test_func", "function", ["arg1", "arg2", "arg3"], {"arg2": "default", "arg3": None})
    
    assert sig1 == sig2  # Same signature
    assert sig1 == sig3  # Compatible (added optional param)
    
    # Test with incompatible change
    sig4 = APISignature("test_func", "function", ["arg1"], {})
    assert sig1 != sig4  # Removed parameter