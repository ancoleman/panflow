"""
Unit tests for the template-based HTML rendering system.
"""

import pytest
import os
import re
from unittest.mock import patch, MagicMock

from panflow.core.template_loader import TemplateLoader


@pytest.fixture
def template_loader():
    """Create a template loader for testing."""
    # Get the package template directory
    package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    template_dir = os.path.join(package_dir, "panflow", "templates")
    
    return TemplateLoader(template_dir=template_dir)


def test_template_loader_initialization():
    """Test that the template loader initializes correctly."""
    loader = TemplateLoader()
    assert loader.env is not None
    assert "json_encode" in loader.env.filters
    assert "format_date" in loader.env.filters
    assert "format_number" in loader.env.filters


def test_render_template_with_timestamp(template_loader):
    """Test that the render_template method adds a timestamp to the context."""
    result = template_loader.render_template("reports/components/base_template.html", {})
    
    # Check for timestamp in output
    assert re.search(r'Report generated on \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', result)


def test_render_unused_objects_report(template_loader):
    """Test rendering an unused objects report."""
    # Create test objects data
    test_objects = [
        {
            "name": "test-address",
            "ip-netmask": "10.0.0.1/24",
            "context_type": "device_group",
            "context_name": "test-dg",
            "context": "Device Group: test-dg"
        },
        {
            "name": "test-service",
            "protocol": {"tcp": {"port": "443"}},
            "context_type": "shared",
            "context": "Shared"
        }
    ]
    
    # Create report info
    report_info = {
        "Query": "show me unused objects",
        "Configuration": "test-config.xml"
    }
    
    # Render the report
    result = template_loader.render_unused_objects_report(
        {"unused_objects": test_objects},
        report_info
    )
    
    # Check that the HTML contains important elements
    assert "<title>Unused Objects Report</title>" in result
    assert "Found 2 Unused Objects" in result
    assert "test-address" in result
    assert "test-service" in result
    assert "10.0.0.1/24" in result
    assert "443" in result
    assert "Device Group: test-dg" in result
    assert "Shared" in result
    assert "IP-Netmask" in result
    assert "TCP Service" in result


def test_render_duplicate_objects_report(template_loader):
    """Test rendering a duplicate objects report."""
    # Create test duplicate objects data
    test_duplicates = {
        "ip-netmask:192.168.1.1": [
            {
                "name": "dup-address1",
                "context_type": "device_group",
                "context_name": "dg1",
                "context": "Device Group: dg1"
            },
            {
                "name": "dup-address2",
                "context_type": "device_group",
                "context_name": "dg2",
                "context": "Device Group: dg2"
            }
        ],
        "fqdn:example.com": [
            {
                "name": "example-fqdn1",
                "context_type": "shared",
                "context": "Shared"
            },
            {
                "name": "example-fqdn2",
                "context_type": "vsys",
                "context_name": "vsys1",
                "context": "VSYS: vsys1"
            }
        ]
    }
    
    # Create report info
    report_info = {
        "Query": "find duplicate objects",
        "Configuration": "test-config.xml"
    }
    
    # Render the report
    result = template_loader.render_duplicate_objects_report(
        {"duplicate_objects": test_duplicates},
        report_info
    )
    
    # Check that the HTML contains important elements
    assert "<title>Duplicate Objects Report</title>" in result
    assert "dup-address1" in result
    assert "dup-address2" in result
    assert "example-fqdn1" in result
    assert "example-fqdn2" in result
    assert "Device Group: dg1" in result
    assert "Device Group: dg2" in result
    assert "Shared" in result
    assert "VSYS: vsys1" in result
    assert "192.168.1.1" in result
    assert "example.com" in result


def test_render_template_error_handling():
    """Test that template rendering errors are handled properly."""
    # Create a template loader with a non-existent template directory
    loader = TemplateLoader(template_dir="/path/does/not/exist")
    
    # Attempt to render a template that doesn't exist
    result = loader.render_template("non_existent_template.html", {})
    
    # Check that an error page is returned
    assert "<title>Error Rendering Report</title>" in result
    assert "Error Rendering Template" in result