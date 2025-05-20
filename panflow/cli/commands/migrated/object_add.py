"""
Object add command using the new command pattern.

This is a migrated version of the object add command using the command pattern abstraction.
"""

import json
import typer
from typing import Dict, Any, Optional

from panflow import PANFlowConfig, OBJECT_TYPE_ALIASES
from panflow.core.config_loader import save_config

from ...app import object_app
from ...common import ConfigOptions, ContextOptions, ObjectOptions
from ...command_base import standard_command, OutputFormat


@object_app.command("add-new")
@standard_command
def add_object(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties: str = typer.Option(
        ..., "--properties", "-p", help="JSON file with object properties"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", help="Output format"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for updated configuration"
    ),
):
    """
    Add a new object to the configuration.

    This command adds a new object of the specified type with the given properties.
    The properties should be provided in a JSON file.
    """
    # Check if object_type is an alias and convert it
    actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)

    # Load properties from file
    try:
        with open(properties, "r") as f:
            props = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load properties file: {str(e)}")

    # Add the object
    from panflow.modules.objects import add_object as add_object_func

    updated_tree = add_object_func(
        tree=panflow_config.tree,
        device_type=panflow_config.device_type,
        context_type=panflow_config.context_type,
        object_type=actual_object_type,
        name=name,
        properties=props,
        version=panflow_config.version,
        **context_kwargs,
    )

    # Save the updated configuration
    if output_file:
        save_config(updated_tree, output_file)
        return {
            "status": "success",
            "message": f"Object {name} added successfully",
            "output_file": output_file,
        }
    else:
        return {
            "status": "success",
            "message": f"Object {name} added successfully, but not saved to a file",
            "warning": "The configuration was not saved. Use --output to save the changes.",
        }
