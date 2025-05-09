"""
Unit tests for the reporting package.

This module tests the consolidated reporting package functionality.
"""

import os
import pytest
from pathlib import Path
from lxml import etree

from panflow.reporting import (
    generate_unused_objects_report,
    generate_duplicate_objects_report,
    generate_security_rule_coverage_report,
    EnhancedReportingEngine,
    ReportingEngine
)
from panflow.reporting.formatters.html import HTMLFormatter
from panflow.reporting.formatters.json import JSONFormatter
from panflow.reporting.formatters.csv import CSVFormatter
from panflow.reporting.reports.unused_objects import generate_unused_objects_report_data
from panflow.reporting.reports.duplicate_objects import generate_duplicate_objects_report_data
from panflow.reporting.reports.policy_analysis import generate_security_policy_analysis_data

# Get path to fixture file
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
CONFIG_FILE = FIXTURES_DIR / "sample_config.xml"

@pytest.fixture
def xml_tree():
    """Load sample configuration file as XML ElementTree."""
    if not CONFIG_FILE.exists():
        pytest.skip(f"Sample config file not found at {CONFIG_FILE}")
    return etree.parse(str(CONFIG_FILE))

def test_reporting_imports():
    """Test that all reporting modules can be imported correctly."""
    # The imports already happened at the top of the file
    # If they work, the test passes
    assert generate_unused_objects_report is not None
    assert generate_duplicate_objects_report is not None
    assert generate_security_rule_coverage_report is not None
    assert EnhancedReportingEngine is not None
    assert ReportingEngine is not None
    assert HTMLFormatter is not None
    assert JSONFormatter is not None
    assert CSVFormatter is not None
    assert generate_unused_objects_report_data is not None
    assert generate_duplicate_objects_report_data is not None
    assert generate_security_policy_analysis_data is not None

def test_reporting_engine_initialization(xml_tree):
    """Test that the ReportingEngine can be initialized correctly."""
    engine = ReportingEngine(
        xml_tree,
        device_type="firewall",
        context_type="vsys",
        version="10.1.0",
        vsys="vsys1"
    )
    assert engine is not None
    assert engine.tree is xml_tree
    assert engine.device_type == "firewall"
    assert engine.context_type == "vsys"
    assert engine.version == "10.1.0"
    assert engine.context_kwargs == {"vsys": "vsys1"}
    assert engine.html_formatter is not None
    assert engine.json_formatter is not None
    assert engine.csv_formatter is not None

def test_json_formatter():
    """Test that the JSONFormatter works correctly."""
    formatter = JSONFormatter()
    test_data = {"key": "value", "nested": {"sub": "data"}}
    json_str = formatter.format(test_data)
    assert json_str is not None
    assert "key" in json_str
    assert "value" in json_str
    assert "nested" in json_str
    assert "sub" in json_str
    assert "data" in json_str

def test_csv_formatter():
    """Test that the CSVFormatter works correctly."""
    formatter = CSVFormatter()
    test_data = {
        "unused_objects": [
            {"name": "test-object", "properties": {"ip-netmask": "192.168.1.1/24"}}
        ]
    }
    csv_str = formatter.format_unused_objects_report(test_data)
    assert csv_str is not None
    assert "test-object" in csv_str
    assert "IP/Netmask" in csv_str
    assert "192.168.1.1/24" in csv_str

def test_html_formatter(mocker):
    """Test that the HTMLFormatter works correctly."""
    # Mock the template loader to avoid needing actual template files
    mock_template_loader = mocker.patch('panflow.core.template_loader.TemplateLoader')
    mock_template_loader.return_value.render_template.return_value = "<html>Test HTML</html>"
    mock_template_loader.return_value.render_security_policy_analysis.return_value = "<html>Test Policy Analysis</html>"
    
    formatter = HTMLFormatter()
    test_data = {
        "unused_objects": [
            {"name": "test-object", "properties": {"ip-netmask": "192.168.1.1/24"}}
        ]
    }
    html_str = formatter.format_unused_objects_report(test_data)
    assert html_str is not None
    assert "<html>Test HTML</html>" == html_str

def test_backward_compatibility(xml_tree):
    """Test that the original reporting functions still work."""
    # Generate an unused objects report using the original function
    report_data = generate_unused_objects_report(
        xml_tree,
        device_type="firewall",
        context_type="vsys",
        version="10.1.0",
        object_type="address",
        vsys="vsys1"
    )
    
    # The function should return a dictionary with an 'unused_objects' key
    assert isinstance(report_data, dict)
    assert "unused_objects" in report_data