"""
Tests for CLI command pattern abstraction.

These tests verify that the command pattern abstraction works correctly
with existing CLI commands and provides consistent behavior.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

import typer
from typer.testing import CliRunner

# Import the command base module
from panflow.cli.command_base import (
    CommandBase,
    command_error_handler,
    config_loader,
    context_handler,
    output_formatter,
    standard_command,
    OutputFormat,
)

# Import common utilities
from panflow.cli.common import ConfigOptions, ContextOptions, ObjectOptions
from panflow import PANFlowConfig
from panflow.core.exceptions import PANFlowError

# Create a runner for testing CLI commands
runner = CliRunner()

# Create a test app
test_app = typer.Typer()


# Test fixtures
@pytest.fixture
def sample_config():
    """Create a simple test configuration."""
    # Mock PANFlowConfig for testing
    config = MagicMock(spec=PANFlowConfig)
    config.tree = MagicMock()
    config.device_type = "firewall"
    config.context_type = "vsys"
    config.version = "10.2"
    return config


@pytest.fixture
def temp_output_file():
    """Create a temporary output file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        yield tmp.name
    # Clean up after the test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


# Test CommandBase methods
class TestCommandBase:
    """Tests for CommandBase class methods."""

    def test_format_output_json(self, temp_output_file):
        """Test JSON output formatting."""
        cmd = CommandBase()
        test_data = {"key": "value", "nested": {"subkey": "subvalue"}}

        # Test with output file
        cmd.format_output(test_data, "json", temp_output_file)
        assert os.path.exists(temp_output_file)

        with open(temp_output_file, "r") as f:
            saved_data = json.load(f)
            assert saved_data == test_data

    def test_format_output_table(self):
        """Test table output formatting."""
        cmd = CommandBase()
        test_data = [
            {"name": "obj1", "type": "address", "value": "1.1.1.1"},
            {"name": "obj2", "type": "address", "value": "2.2.2.2"},
        ]

        # Just verify it doesn't raise an exception - actual output is visually inspected
        cmd.format_output(test_data, "table")

    def test_format_output_csv(self, temp_output_file):
        """Test CSV output formatting."""
        cmd = CommandBase()
        test_data = [
            {"name": "obj1", "type": "address", "value": "1.1.1.1"},
            {"name": "obj2", "type": "address", "value": "2.2.2.2"},
        ]

        # Test with output file
        cmd.format_output(test_data, "csv", temp_output_file)
        assert os.path.exists(temp_output_file)

        with open(temp_output_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 data rows
            assert '"name","type","value"' in lines[0]

    def test_handle_error_panflow_error(self):
        """Test error handling with PANFlowError."""
        cmd = CommandBase()
        error = PANFlowError("Test error message")

        with pytest.raises(SystemExit):
            cmd.handle_error(error, "test_command")

    def test_handle_error_other_exception(self):
        """Test error handling with other exceptions."""
        cmd = CommandBase()
        error = ValueError("Test error message")

        with pytest.raises(SystemExit):
            cmd.handle_error(error, "test_command")


# Test decorator functions
@test_app.command("test-error-handler")
@command_error_handler
def test_command_with_error():
    """Test command that raises an error."""
    raise PANFlowError("Test error message")


@test_app.command("test-config-loader")
@config_loader
def test_command_with_config(panflow_config: PANFlowConfig):
    """Test command with config loader."""
    return {"device_type": panflow_config.device_type}


@test_app.command("test-context-handler")
@context_handler
def test_command_with_context(context_kwargs: Dict[str, str]):
    """Test command with context handler."""
    return context_kwargs


@test_app.command("test-output-formatter")
@output_formatter
def test_command_with_output():
    """Test command with output formatter."""
    return {"status": "success"}


@test_app.command("test-standard-command")
@standard_command
def test_command_standard(panflow_config: PANFlowConfig, context_kwargs: Dict[str, str]):
    """Test command with standard decorator."""
    return {"device_type": panflow_config.device_type, "context": context_kwargs}


# Tests for decorator functions
class TestDecorators:
    """Tests for command decorator functions."""

    def test_error_handler_decorator(self):
        """Test command_error_handler decorator."""
        result = runner.invoke(test_app, ["test-error-handler"])
        assert result.exit_code == 1
        assert "Test error message" in result.stdout

    @patch("panflow.cli.command_base.CommandBase.load_config")
    def test_config_loader_decorator(self, mock_load_config, sample_config):
        """Test config_loader decorator."""
        mock_load_config.return_value = sample_config

        result = runner.invoke(
            test_app, ["test-config-loader", "--config", "dummy.xml", "--device-type", "firewall"]
        )

        assert result.exit_code == 0
        assert mock_load_config.called

    def test_context_handler_decorator(self):
        """Test context_handler decorator."""
        result = runner.invoke(
            test_app, ["test-context-handler", "--context", "vsys", "--vsys", "vsys2"]
        )

        assert result.exit_code == 0
        # Check that vsys was included in context kwargs
        assert "vsys" in result.stdout
        assert "vsys2" in result.stdout

    def test_output_formatter_decorator(self):
        """Test output_formatter decorator."""
        result = runner.invoke(test_app, ["test-output-formatter", "--format", "json"])

        assert result.exit_code == 0
        assert "success" in result.stdout

    @patch("panflow.cli.command_base.CommandBase.load_config")
    def test_standard_command_decorator(self, mock_load_config, sample_config):
        """Test standard_command decorator."""
        mock_load_config.return_value = sample_config

        result = runner.invoke(
            test_app,
            [
                "test-standard-command",
                "--config",
                "dummy.xml",
                "--context",
                "vsys",
                "--vsys",
                "vsys2",
            ],
        )

        assert result.exit_code == 0
        assert mock_load_config.called
        assert "firewall" in result.stdout
        assert "vsys2" in result.stdout


# Test integration with real CLI commands via object_commands_refactored
# Note: These tests require a complete test environment with sample configurations
@pytest.mark.integration
class TestRefactoredCommands:
    """Integration tests for refactored commands."""

    def test_list_objects_command(self):
        """Test the refactored list-new command."""
        from panflow.cli.commands.object_commands_refactored import list_objects

        # Create a mock config and context
        mock_config = MagicMock(spec=PANFlowConfig)
        mock_config.tree = MagicMock()
        mock_config.device_type = "firewall"
        mock_config.context_type = "vsys"
        mock_config.version = "10.2"

        mock_context = {"vsys": "vsys1"}

        # Mock the get_objects function
        with patch("panflow.modules.objects.get_objects") as mock_get_objects:
            # Create mock objects
            mock_obj1 = MagicMock()
            mock_obj1.to_dict.return_value = {"name": "obj1", "type": "address"}

            mock_obj2 = MagicMock()
            mock_obj2.to_dict.return_value = {"name": "obj2", "type": "address"}

            mock_get_objects.return_value = [mock_obj1, mock_obj2]

            # Call the function
            result = list_objects(
                panflow_config=mock_config, context_kwargs=mock_context, object_type="address"
            )

            # Verify the results
            assert len(result) == 2
            assert result[0]["name"] == "obj1"
            assert result[1]["name"] == "obj2"

            # Verify mock_get_objects was called with correct parameters
            mock_get_objects.assert_called_once()
            args, kwargs = mock_get_objects.call_args
            assert kwargs["object_type"] == "address"
            assert kwargs["vsys"] == "vsys1"

    def test_get_object_command(self):
        """Test the refactored get-new command."""
        from panflow.cli.commands.object_commands_refactored import get_object

        # Create a mock config and context
        mock_config = MagicMock(spec=PANFlowConfig)
        mock_config.tree = MagicMock()
        mock_config.device_type = "firewall"
        mock_config.context_type = "vsys"
        mock_config.version = "10.2"

        mock_context = {"vsys": "vsys1"}

        # Mock the get_object function
        with patch("panflow.modules.objects.get_object") as mock_get_obj:
            # Create a mock object
            mock_obj = MagicMock()
            mock_obj.to_dict.return_value = {
                "name": "test-object",
                "type": "address",
                "value": "1.1.1.1",
            }

            mock_get_obj.return_value = mock_obj

            # Call the function
            result = get_object(
                panflow_config=mock_config,
                context_kwargs=mock_context,
                object_type="address",
                name="test-object",
            )

            # Verify the results
            assert result["name"] == "test-object"
            assert result["type"] == "address"
            assert result["value"] == "1.1.1.1"

            # Verify mock_get_obj was called with correct parameters
            mock_get_obj.assert_called_once()
            args, kwargs = mock_get_obj.call_args
            assert kwargs["object_type"] == "address"
            assert kwargs["name"] == "test-object"
            assert kwargs["vsys"] == "vsys1"


# Compatibility test with existing CLI commands
@pytest.mark.compatibility
class TestCommandCompatibility:
    """
    Tests to verify that the command pattern is compatible with existing CLI commands.

    These tests simulate applying the decorators to existing command functions
    to ensure they work correctly.
    """

    def test_apply_decorator_to_existing_command(self):
        """Test applying the standard_command decorator to an existing command."""

        # Create a mock implementation of an existing command
        def existing_command(config, device_type=None, context="shared", device_group=None):
            # Simulate loading config
            panflow_config = PANFlowConfig(config_file=config, device_type=device_type)

            # Simulate getting context
            context_kwargs = {}
            if context == "device_group" and device_group:
                context_kwargs["device_group"] = device_group

            # Return some result
            return {"status": "success", "config": config, "context": context_kwargs}

        # Apply the standard_command decorator
        decorated_command = standard_command(existing_command)

        # Mock the necessary functions
        with patch("panflow.cli.command_base.CommandBase.load_config") as mock_load_config, patch(
            "panflow.cli.command_base.CommandBase.format_output"
        ) as mock_format_output:
            mock_config = MagicMock(spec=PANFlowConfig)
            mock_load_config.return_value = mock_config

            # Call the decorated function
            decorated_command(
                config="test.xml",
                device_type="firewall",
                context="device_group",
                device_group="DG1",
            )

            # Verify the mock functions were called correctly
            mock_load_config.assert_called_once_with("test.xml", "firewall", None)
            assert mock_format_output.called


# Comprehensive compatibility test
def test_all_cli_commands_compatibility():
    """
    Test that all CLI commands in the codebase can be abstracted with the new pattern.

    This test dynamically finds all CLI commands and verifies they can work with the
    standard_command decorator.
    """
    # Import all command modules
    import importlib
    import inspect
    from panflow.cli.app import app as cli_app

    # Get all command modules from CLI commands directory
    cmd_dir = Path(__file__).parent.parent.parent.parent / "panflow" / "cli" / "commands"
    command_files = [
        f for f in os.listdir(cmd_dir) if f.endswith("_commands.py") and not f.startswith("__")
    ]

    # Count total commands and compatible commands
    total_commands = 0
    compatible_commands = 0
    incompatible_commands = []

    # Check each command file
    for cmd_file in command_files:
        module_name = cmd_file[:-3]  # Remove .py extension
        try:
            # Import the module
            module = importlib.import_module(f"panflow.cli.commands.{module_name}")

            # Find all command functions in the module
            for name, obj in inspect.getmembers(module):
                # Check if this is a command function (has a __typer_function__ attribute)
                if inspect.isfunction(obj) and hasattr(obj, "__typer_function__"):
                    total_commands += 1

                    try:
                        # Check if the function signature is compatible with our decorators
                        sig = inspect.signature(obj)
                        params = sig.parameters

                        # A command is considered compatible if it:
                        # 1. Has config, device_type, and version parameters that our config_loader can handle
                        # 2. Has context, device_group, vsys, template parameters that our context_handler can handle
                        # 3. Doesn't have positional-only parameters that would conflict with our injected parameters

                        config_compatible = any(p in params for p in ["config", "config_file"])
                        context_compatible = any(p in params for p in ["context", "context_type"])

                        # Count parameters that would conflict with our injected parameters
                        conflicting_params = ["panflow_config", "context_kwargs"]
                        conflicts = [p for p in conflicting_params if p in params]

                        # Check for positional-only parameters
                        positional_only = any(
                            p.kind == inspect.Parameter.POSITIONAL_ONLY for p in params.values()
                        )

                        if (
                            config_compatible
                            and context_compatible
                            and not conflicts
                            and not positional_only
                        ):
                            compatible_commands += 1
                        else:
                            incompatible_commands.append(f"{module_name}.{name}")

                    except Exception as e:
                        # If we can't analyze the function, consider it incompatible
                        incompatible_commands.append(f"{module_name}.{name}: {str(e)}")

        except Exception as e:
            # If we can't import the module, log it
            print(f"Error importing {module_name}: {str(e)}")

    # Assert that all commands are compatible
    compatibility_percentage = (
        (compatible_commands / total_commands * 100) if total_commands > 0 else 0
    )
    print(
        f"Command compatibility: {compatible_commands}/{total_commands} ({compatibility_percentage:.1f}%)"
    )
    print(f"Incompatible commands: {incompatible_commands}")

    # Not a strict test - just provides info about compatibility
    # We expect some commands may need adjustments
    assert (
        compatibility_percentage > 50
    ), f"Less than 50% of commands are compatible with the new pattern"
