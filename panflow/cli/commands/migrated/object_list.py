"""
Object listing command using the new command pattern.

This is a migrated version of the object list command using the command pattern abstraction.
"""

import typer
from typing import Dict, Any, Optional, List

from panflow import PANFlowConfig, OBJECT_TYPE_ALIASES
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor

from ...app import object_app
from ...common import ConfigOptions, ContextOptions, ObjectOptions
from ...command_base import (
    command_error_handler,
    config_loader,
    context_handler,
    output_formatter,
    OutputFormat,
)


@object_app.command("list-new")
@command_error_handler
@config_loader
@context_handler
@output_formatter
def list_objects(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str = ObjectOptions.object_type(),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", help="Output format (json, table, csv, yaml, text)"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for results"
    ),
    query_filter: Optional[str] = typer.Option(
        None, "--query-filter", "-q", help="Graph query filter to select objects"
    ),
    table_title: Optional[str] = typer.Option(None, "--title", help="Title for table output"),
):
    """
    List objects of specified type.

    This command lists objects of the specified type, with optional filtering
    using the graph query language.
    """
    # Check if object_type is an alias and convert it
    actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)

    # Get the objects
    if query_filter:
        # Use the query engine to filter objects
        graph = ConfigGraph(panflow_config.tree, panflow_config.device_type, panflow_config.version)
        query = Query(query_filter)
        executor = QueryExecutor(graph)

        # Execute the query
        results = executor.execute_query(query)

        # Filter objects based on type
        filtered_objects = []
        for result in results.results:
            for node in result.values():
                if hasattr(node, "type") and node.type.replace(
                    "-", "_"
                ) == actual_object_type.replace("-", "_"):
                    filtered_objects.append(node.to_dict())

        # Set table title if not specified
        if table_title is None:
            table_title = f"Filtered {object_type} objects"

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
            **context_kwargs,
        )

        # Convert to list of dictionaries
        object_list = [obj.to_dict() for obj in objects]

        # Set table title if not specified
        if table_title is None:
            table_title = f"{object_type} objects"

        return object_list
