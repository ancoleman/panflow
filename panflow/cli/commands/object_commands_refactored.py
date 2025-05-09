"""
Object management commands for the PANFlow CLI.

This module provides commands for managing PAN-OS objects,
using the new command base pattern for standardization.
"""

import json
import typer
import logging
from typing import Optional, Dict, Any, List

from panflow import PANFlowConfig, OBJECT_TYPE_ALIASES
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow.core.graph_service import GraphService
from panflow.core.config_loader import save_config

from ..app import object_app
from ..common import (
    ConfigOptions, ContextOptions, ObjectOptions
)
from ..command_base import (
    CommandBase, command_error_handler, config_loader, 
    context_handler, output_formatter, standard_command,
    OutputFormat
)

# Get logger
logger = logging.getLogger("panflow")

# Using the new pattern with standard_command decorator
@object_app.command("list-new")
@standard_command
def list_objects(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str = ObjectOptions.object_type(),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", 
                                             help="Graph query filter to select objects"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", 
        help="Output format (json, table, text, csv, yaml)"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", 
        help="Output file for results"
    ),
    table_title: Optional[str] = typer.Option(
        None, "--title", "-t",
        help="Title for table output (only used with table format)"
    ),
):
    """
    List objects of specified type.
    
    This is a refactored version of the list command that uses the command base pattern.
    """
    # Check if object_type is an alias and convert it
    actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)
    
    # Get the objects
    if query_filter:
        # Use the query engine
        graph = ConfigGraph(panflow_config.tree, panflow_config.device_type, panflow_config.version)
        query = Query(query_filter)
        executor = QueryExecutor(graph)
        
        # Execute the query
        results = executor.execute_query(query)
        
        # Filter objects based on type
        filtered_objects = []
        for result in results.results:
            for node in result.values():
                if hasattr(node, 'type') and node.type.replace('-', '_') == actual_object_type.replace('-', '_'):
                    filtered_objects.append(node.to_dict())
                    
        return filtered_objects
    else:
        # Use direct object lookup
        from panflow.modules.objects import get_objects
        
        objects = get_objects(
            tree=panflow_config.tree,
            device_type=panflow_config.device_type,
            context_type=panflow_config.context_type,
            object_type=actual_object_type,
            version=panflow_config.version,
            **context_kwargs
        )
        
        # Convert to list of dictionaries
        return [obj.to_dict() for obj in objects]

# Using individual decorators for more control
@object_app.command("get-new")
@command_error_handler
@config_loader
@context_handler
@output_formatter
def get_object(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", 
        help="Output format (json, table, text, csv, yaml)"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", 
        help="Output file for results"
    ),
):
    """
    Get a specific object by name and type.
    
    This is a refactored version of the get command that uses the command base pattern.
    """
    # Check if object_type is an alias and convert it
    actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)
    
    # Use the object module to get the object
    from panflow.modules.objects import get_object as get_object_func
    
    obj = get_object_func(
        tree=panflow_config.tree,
        device_type=panflow_config.device_type,
        context_type=panflow_config.context_type,
        object_type=actual_object_type,
        name=name,
        version=panflow_config.version,
        **context_kwargs
    )
    
    if obj:
        return obj.to_dict()
    else:
        return {"error": f"Object not found: {name} (type: {object_type})"}

# Example of using the CommandBase class directly
@object_app.command("add-new")
def add_object(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties: str = typer.Option(..., "--properties", "-p", help="JSON file with object properties"),
    output: str = ConfigOptions.output_file(),
    device_type: Optional[str] = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """
    Add a new object.
    
    This is a refactored version of the add command that uses the CommandBase class directly.
    """
    cmd = CommandBase()
    
    try:
        # Load the configuration
        panflow_config = cmd.load_config(config, device_type, version)
        
        # Get context parameters
        context_kwargs = cmd.get_context_params(context, device_group, vsys, template)
        
        # Check if object_type is an alias and convert it
        actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)
        
        # Load properties from file
        try:
            with open(properties, 'r') as f:
                props = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load properties file: {str(e)}")
        
        # Use the object module to add the object
        from panflow.modules.objects import add_object as add_object_func
        
        updated_tree = add_object_func(
            tree=panflow_config.tree,
            device_type=panflow_config.device_type,
            context_type=panflow_config.context_type,
            object_type=actual_object_type,
            name=name,
            properties=props,
            version=panflow_config.version,
            **context_kwargs
        )
        
        # Save the updated configuration
        save_config(updated_tree, output)
        
        # Format the output
        result = {"status": "success", "message": f"Object {name} added successfully", "output_file": output}
        cmd.format_output(result, "json")
        
    except Exception as e:
        # Handle the error
        cmd.handle_error(e, "add_object")