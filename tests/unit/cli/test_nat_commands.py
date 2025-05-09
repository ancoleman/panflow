"""
Tests for NAT CLI commands.

This module tests that the CLI commands for NAT functionality
continue to work after the consolidation of NAT modules.
"""

import pytest
import os
from lxml import etree
from io import StringIO
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, mock_open

from panflow.cli.app import app

# Use isolated=False to allow mocking filesystem operations
runner = CliRunner(mix_stderr=False)

# Sample XML content for mocking file reads
SAMPLE_XML = """
<config version="10.1.0">
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <rulebase>
            <nat>
              <rules>
                <entry name="test-rule">
                  <bi-directional>yes</bi-directional>
                  <from><member>trust</member></from>
                  <to><member>untrust</member></to>
                </entry>
              </rules>
            </nat>
          </rulebase>
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
"""

# Mock the proper return value for load_config_from_file
@patch('panflow.modules.nat_splitter.split_bidirectional_nat_rule')
@patch('panflow.core.config_loader.load_config_from_file')
@patch('panflow.core.config_loader.detect_device_type')
@patch('panflow.core.config_loader.save_config')
@patch('os.path.exists')
@patch('lxml.etree.parse')
def test_split_bidirectional_command(mock_parse, mock_exists, mock_save, mock_detect_type, mock_load_config, mock_split):
    """Test the split-bidirectional CLI command."""
    # Setup mocks
    xml_tree = etree.parse(StringIO(SAMPLE_XML))
    mock_parse.return_value = xml_tree
    mock_config = xml_tree
    mock_load_config.return_value = (mock_config, "10.1")  # Return tuple of (tree, version)
    mock_detect_type.return_value = "firewall"
    mock_save.return_value = True
    # Make file existence check pass
    mock_exists.return_value = True
    
    mock_split.return_value = {
        "success": True,
        "original_rule": "test-rule",
        "reverse_rule": "test-rule-reverse"
    }
    
    # Run the command
    result = runner.invoke(
        app, 
        [
            "policy", "nat", "split-bidirectional",
            "--config", "test.xml",
            "--rule-name", "test-rule",
            "--output", "output.xml"
        ]
    )
    
    # Check the result
    assert result.exit_code == 0, f"Command failed with error: {result.stdout}"
    assert "Successfully split bidirectional NAT rule" in result.stdout
    
    # Verify mocks were called correctly
    mock_load_config.assert_called_once_with("test.xml")
    mock_split.assert_called_once()
    args, kwargs = mock_split.call_args
    assert kwargs["rule_name"] == "test-rule"
    assert kwargs["tree"] == mock_config

@patch('panflow.modules.nat_splitter.split_all_bidirectional_nat_rules')
@patch('panflow.core.config_loader.load_config_from_file')
@patch('panflow.core.config_loader.detect_device_type')
@patch('panflow.core.config_loader.save_config')
@patch('os.path.exists')
@patch('lxml.etree.parse')
def test_split_all_bidirectional_command(mock_parse, mock_exists, mock_save, mock_detect_type, mock_load_config, mock_split_all):
    """Test the split-all-bidirectional CLI command."""
    # Setup mocks
    xml_tree = etree.parse(StringIO(SAMPLE_XML))
    mock_parse.return_value = xml_tree
    mock_config = xml_tree
    mock_load_config.return_value = (mock_config, "10.1")  # Return tuple of (tree, version)
    mock_detect_type.return_value = "firewall"
    mock_save.return_value = True
    # Make file existence check pass
    mock_exists.return_value = True
    
    mock_split_all.return_value = {
        "success": True,
        "processed": 2,
        "succeeded": 2,
        "failed": 0,
        "details": []
    }
    
    # Run the command
    result = runner.invoke(
        app, 
        [
            "policy", "nat", "split-all-bidirectional",
            "--config", "test.xml",
            "--output", "output.xml"
        ]
    )
    
    # Check the result
    assert result.exit_code == 0, f"Command failed with error: {result.stdout}"
    assert "Successfully split" in result.stdout
    assert "bidirectional NAT rules" in result.stdout
    
    # Verify mocks were called correctly
    mock_load_config.assert_called_once_with("test.xml")
    mock_split_all.assert_called_once()
    args, kwargs = mock_split_all.call_args
    assert kwargs["tree"] == mock_config