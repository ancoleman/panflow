"""
Tests for migrating existing CLI commands to the command pattern.

These tests demonstrate how to migrate an existing CLI command to the
command pattern abstraction and verify it still functions correctly.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock

import typer
from typer.testing import CliRunner

from panflow import PANFlowConfig
from panflow.cli.command_base import CommandBase, standard_command, OutputFormat

# Create a runner for testing CLI commands
runner = CliRunner()

# Test app for migration tests
migration_app = typer.Typer()


# Sample original command (simulated)
def original_object_get(
    config: str,
    object_type: str,
    name: str,
    device_type: str = None,
    context: str = "shared",
    device_group: str = None,
    vsys: str = "vsys1",
    template: str = None,
    version: str = None,
    output_format: str = "json",
    output_file: str = None,
):
    """
    Original version of the object get command.

    This is a simplified version that simulates the behavior
    of an existing CLI command.
    """
    try:
        # Load configuration
        config_obj = PANFlowConfig(config_file=config, device_type=device_type, version=version)

        # Get context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template

        # Get the object
        from panflow.modules.objects import get_object as get_object_func

        obj = get_object_func(
            tree=config_obj.tree,
            device_type=config_obj.device_type,
            context_type=config_obj.context_type,
            object_type=object_type,
            name=name,
            version=config_obj.version,
            **context_kwargs,
        )

        # Format and return the result
        if obj:
            result = obj.to_dict()
        else:
            result = {"error": f"Object not found: {name} (type: {object_type})"}

        # Handle output
        if output_file:
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Output saved to {output_file}")
        else:
            print(json.dumps(result, indent=2))

        return result

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


# Register the original command
@migration_app.command("get-original")
def get_object_original(
    config: str = typer.Option(..., "--config", "-c", help="Configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Object type"),
    name: str = typer.Option(..., "--name", "-n", help="Object name"),
    device_type: str = typer.Option(None, "--device-type", "-d", help="Device type"),
    context: str = typer.Option("shared", "--context", help="Context type"),
    device_group: str = typer.Option(None, "--device-group", help="Device group"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS"),
    template: str = typer.Option(None, "--template", help="Template"),
    version: str = typer.Option(None, "--version", help="PAN-OS version"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Get an object by name and type (original version)."""
    return original_object_get(
        config,
        object_type,
        name,
        device_type,
        context,
        device_group,
        vsys,
        template,
        version,
        output_format,
        output_file,
    )


# Migrated command using the command pattern
@migration_app.command("get-migrated")
@standard_command
def get_object_migrated(
    panflow_config: PANFlowConfig,
    context_kwargs: dict,
    object_type: str = typer.Option(..., "--type", "-t", help="Object type"),
    name: str = typer.Option(..., "--name", "-n", help="Object name"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", help="Output format"
    ),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Get an object by name and type (migrated version)."""
    # Get the object
    from panflow.modules.objects import get_object as get_object_func

    obj = get_object_func(
        tree=panflow_config.tree,
        device_type=panflow_config.device_type,
        context_type=panflow_config.context_type,
        object_type=object_type,
        name=name,
        version=panflow_config.version,
        **context_kwargs,
    )

    if obj:
        return obj.to_dict()
    else:
        return {"error": f"Object not found: {name} (type: {object_type})"}


# Tests for command migration
class TestCommandMigration:
    """Tests for migrating commands to the new pattern."""

    @pytest.fixture
    def mock_get_object(self):
        """Mock the get_object function."""
        with patch("panflow.modules.objects.get_object") as mock:
            mock_obj = MagicMock()
            mock_obj.to_dict.return_value = {
                "name": "test-obj",
                "type": "address",
                "value": "1.1.1.1",
            }
            mock.return_value = mock_obj
            yield mock

    @pytest.fixture
    def mock_load_config(self):
        """Mock PANFlowConfig."""
        with patch("panflow.PANFlowConfig") as mock:
            mock_config = MagicMock(spec=PANFlowConfig)
            mock_config.tree = MagicMock()
            mock_config.device_type = "firewall"
            mock_config.context_type = "vsys"
            mock_config.version = "10.2"
            mock.return_value = mock_config
            yield mock

    @pytest.fixture
    def temp_output_file(self):
        """Create a temporary output file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            yield tmp.name
        # Clean up after the test
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    def test_original_command(self, mock_get_object, mock_load_config, temp_output_file):
        """Test the original command."""
        # Run the command
        result = runner.invoke(
            migration_app,
            [
                "get-original",
                "--config",
                "test.xml",
                "--type",
                "address",
                "--name",
                "test-obj",
                "--context",
                "vsys",
                "--vsys",
                "vsys1",
                "--output",
                temp_output_file,
            ],
        )

        # Check the result
        assert result.exit_code == 0

        # Verify the call to get_object
        mock_get_object.assert_called_once()

        # Verify the file was created
        assert os.path.exists(temp_output_file)

        # Load and verify the content
        with open(temp_output_file, "r") as f:
            data = json.load(f)
            assert data["name"] == "test-obj"
            assert data["type"] == "address"

    def test_migrated_command(self, mock_get_object, mock_load_config, temp_output_file):
        """Test the migrated command."""
        with patch(
            "panflow.cli.command_base.CommandBase.load_config",
            return_value=mock_load_config.return_value,
        ):
            # Run the command
            result = runner.invoke(
                migration_app,
                [
                    "get-migrated",
                    "--config",
                    "test.xml",
                    "--type",
                    "address",
                    "--name",
                    "test-obj",
                    "--context",
                    "vsys",
                    "--vsys",
                    "vsys1",
                    "--format",
                    "json",
                    "--output",
                    temp_output_file,
                ],
            )

            # Check the result
            assert result.exit_code == 0

            # Verify the call to get_object
            mock_get_object.assert_called_once()

            # Verify the file was created
            assert os.path.exists(temp_output_file)

            # Load and verify the content
            with open(temp_output_file, "r") as f:
                data = json.load(f)
                assert data["name"] == "test-obj"
                assert data["type"] == "address"

    def test_behavior_equivalence(self, mock_get_object, mock_load_config):
        """Test that both commands behave equivalently."""
        # Run both commands and compare outputs
        with patch(
            "panflow.cli.command_base.CommandBase.load_config",
            return_value=mock_load_config.return_value,
        ):
            result_original = runner.invoke(
                migration_app,
                [
                    "get-original",
                    "--config",
                    "test.xml",
                    "--type",
                    "address",
                    "--name",
                    "test-obj",
                    "--context",
                    "vsys",
                    "--vsys",
                    "vsys1",
                ],
            )

            result_migrated = runner.invoke(
                migration_app,
                [
                    "get-migrated",
                    "--config",
                    "test.xml",
                    "--type",
                    "address",
                    "--name",
                    "test-obj",
                    "--context",
                    "vsys",
                    "--vsys",
                    "vsys1",
                ],
            )

            # Both should succeed
            assert result_original.exit_code == 0
            assert result_migrated.exit_code == 0

            # Extract the JSON output from both (commands print JSON)
            import re

            original_json_match = re.search(r"(\{.*\})", result_original.stdout, re.DOTALL)
            migrated_json_match = re.search(r"(\{.*\})", result_migrated.stdout, re.DOTALL)

            if original_json_match and migrated_json_match:
                original_json = json.loads(original_json_match.group(1))
                migrated_json = json.loads(migrated_json_match.group(1))

                # Compare the core data (ignoring formatting differences)
                assert original_json["name"] == migrated_json["name"]
                assert original_json["type"] == migrated_json["type"]
                assert original_json["value"] == migrated_json["value"]

    def test_error_handling_equivalence(self, mock_load_config):
        """Test that error handling is equivalent between original and migrated commands."""
        # Mock get_object to raise an exception
        with patch("panflow.modules.objects.get_object", side_effect=ValueError("Test error")):
            # Run both commands
            result_original = runner.invoke(
                migration_app,
                ["get-original", "--config", "test.xml", "--type", "address", "--name", "test-obj"],
            )

            with patch(
                "panflow.cli.command_base.CommandBase.load_config",
                return_value=mock_load_config.return_value,
            ):
                result_migrated = runner.invoke(
                    migration_app,
                    [
                        "get-migrated",
                        "--config",
                        "test.xml",
                        "--type",
                        "address",
                        "--name",
                        "test-obj",
                    ],
                )

            # Both should fail with non-zero exit code
            assert result_original.exit_code != 0
            assert result_migrated.exit_code != 0

            # Both should include the error message
            assert "Test error" in result_original.stdout or "Test error" in result_original.stderr
            assert "Test error" in result_migrated.stdout or "Test error" in result_migrated.stderr
