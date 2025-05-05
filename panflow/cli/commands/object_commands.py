"""
Object management commands for the PANFlow CLI.

This module provides commands for managing PAN-OS objects.
"""

import json
import typer
import logging
from typing import Optional, Dict, Any, List

from panflow import PANFlowConfig
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type

from ..app import object_app
from ..common import (
    ConfigOptions, ContextOptions, ObjectOptions
)

# Get logger
logger = logging.getLogger("panflow")

@object_app.command("list")
def list_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE a.value CONTAINS \"10.0.0\"')"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """List objects of specified type"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        logger.info(f"Listing {object_type} objects in {context} context...")
        
        # Get the raw objects from the API
        objects = xml_config.get_objects(object_type, context, **context_kwargs)
        
        # Filter objects using graph query if specified
        if query_filter:
            logger.info(f"Filtering objects using query: {query_filter}")
            
            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Prepare a query that returns object names
            # If the query doesn't already have a RETURN clause, append one that returns object names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter
            
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            
            # Extract object names from the results
            matching_objects = []
            for row in results:
                if 'a.name' in row:
                    matching_objects.append(row['a.name'])
                elif len(row) == 1:  # If there's only one column, use its value
                    matching_objects.append(list(row.values())[0])
            
            logger.info(f"Query matched {len(matching_objects)} objects")
            
            # Filter the objects to only include the matched names
            filtered_objects = {}
            for name in matching_objects:
                if name in objects:
                    filtered_objects[name] = objects[name]
            
            objects = filtered_objects
            logger.info(f"Filtered to {len(objects)} {object_type} objects matching query")
        
        # Display a list of object names (with a single log line for each object)
        if objects:
            # We've already logged the count from the get_objects function,
            # so we'll just display the details of each object
            for name, data in objects.items():
                # Create a summarized version of the object data
                data_summary = ""
                if object_type == "address":
                    for key in ["ip-netmask", "ip-range", "fqdn"]:
                        if key in data:
                            data_summary = f"{key}: {data[key]}"
                            break
                elif object_type.endswith("_group"):
                    if "static" in data and isinstance(data["static"], list):
                        data_summary = f"static group with {len(data['static'])} members"
                    elif "dynamic" in data:
                        filter_text = data.get("dynamic", {}).get("filter", "")
                        data_summary = f"dynamic group with filter: {filter_text}"
                            
                if data_summary:
                    logger.info(f"  - {name}: {data_summary}")
                else:
                    logger.info(f"  - {name}")
        else:
            logger.info(f"No {object_type} objects found matching criteria")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(objects, f, indent=2)
            logger.info(f"Objects saved to {output}")
            
    except Exception as e:
        logger.error(f"Error listing objects: {e}")
        raise typer.Exit(1)

@object_app.command("add")
def add_object(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with object properties"),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Add a new object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Add the object
        if xml_config.add_object(object_type, name, properties, context, **context_kwargs):
            logger.info(f"Successfully added {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to add {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error adding object: {e}")
        raise typer.Exit(1)

@object_app.command("update")
def update_object(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with updated object properties"),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Update an existing object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Update the object
        if xml_config.update_object(object_type, name, properties, context, **context_kwargs):
            logger.info(f"Successfully updated {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to update {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error updating object: {e}")
        raise typer.Exit(1)

@object_app.command("delete")
def delete_object(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Delete an object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Delete the object
        if xml_config.delete_object(object_type, name, context, **context_kwargs):
            logger.info(f"Successfully deleted {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to delete {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error deleting object: {e}")
        raise typer.Exit(1)

@object_app.command("filter")
def filter_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Filter objects based on criteria or graph query"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Ensure at least one filter method is specified
        if not criteria_file and not query_filter:
            logger.error("You must specify either --criteria or --query-filter")
            raise typer.Exit(1)
        
        # Read criteria from file if specified
        criteria = None
        if criteria_file:
            with open(criteria_file, 'r') as f:
                criteria = json.load(f)
            logger.info(f"Loaded criteria from {criteria_file}")
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Get all objects first
        objects = xml_config.get_objects(object_type, context, **context_kwargs)
        
        # Use criteria to filter objects if specified
        if criteria:
            filtered_objects = xml_config.filter_objects(object_type, criteria, context, **context_kwargs)
            logger.info(f"Found {len(filtered_objects)} {object_type} objects matching criteria")
        else:
            # If no criteria, start with all objects
            filtered_objects = list(objects.keys())
        
        # Further filter using graph query if specified
        if query_filter:
            logger.info(f"Filtering objects using query: {query_filter}")
            
            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Prepare a query that returns object names
            # If the query doesn't already have a RETURN clause, append one that returns object names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter
            
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            
            # Extract object names from the results
            matching_objects = []
            for row in results:
                if 'a.name' in row:
                    matching_objects.append(row['a.name'])
                elif len(row) == 1:  # If there's only one column, use its value
                    matching_objects.append(list(row.values())[0])
            
            logger.info(f"Query matched {len(matching_objects)} objects")
            
            # Combine with criteria results if both were used
            if criteria:
                # Keep only objects that match both filters
                filtered_objects = [name for name in filtered_objects if name in matching_objects]
                logger.info(f"Combined filters matched {len(filtered_objects)} objects")
            else:
                # Use only query results
                filtered_objects = matching_objects
        
        # Get the full object data for the filtered names
        result_objects = {}
        for name in filtered_objects:
            if name in objects:
                result_objects[name] = objects[name]
        
        # Display filtered objects
        logger.info(f"Final result: {len(result_objects)} {object_type} objects")
        for name in result_objects:
            logger.info(f"  - {name}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result_objects, f, indent=2)
            logger.info(f"Filtered objects saved to {output}")
            
    except Exception as e:
        logger.error(f"Error filtering objects: {e}")
        raise typer.Exit(1)

@object_app.command("bulk-delete")
def bulk_delete_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    names_file: Optional[str] = typer.Option(None, "--names-file", help="Text file with object names to delete (one per line)"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')"),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
    dry_run: bool = ConfigOptions.dry_run(),
    force: bool = typer.Option(False, "--force", help="Delete objects without confirmation (USE WITH CAUTION)")
):
    """Delete multiple objects based on a query filter or names file
    
    Examples:
    
        # Delete objects listed in a file
        python cli.py object bulk-delete --config config.xml --type address --names-file objects_to_delete.txt
        
        # Delete unused address objects using query filter
        python cli.py object bulk-delete --config config.xml --type address --query-filter "MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination|contains]->(a))"
        
        # Preview objects that would be deleted without making changes
        python cli.py object bulk-delete --config config.xml --type address --query-filter "MATCH (a:address) WHERE a.value CONTAINS '192.168.1'" --dry-run
    """
    try:
        # Load the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Initialize object names list
        object_names = []
        
        # Load names from file if specified
        if names_file:
            with open(names_file, 'r') as f:
                object_names = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(object_names)} object names from {names_file}")
        
        # Process query filter if specified
        if query_filter:
            logger.info(f"Using graph query filter: {query_filter}")
            
            # Get the configuration tree (needed to build the graph)
            tree = xml_config.tree
            
            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(tree)
            
            # Prepare a query that returns object names
            # If the query doesn't already have a RETURN clause, append one that returns object names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter
            
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            
            # Extract object names from the results
            query_object_names = []
            for row in results:
                if 'a.name' in row:
                    query_object_names.append(row['a.name'])
            
            logger.info(f"Query matched {len(query_object_names)} objects")
            
            # Add query results to object names list
            object_names.extend(query_object_names)
        
        # Remove duplicates
        object_names = list(set(object_names))
        
        # If no objects to delete, stop
        if not object_names:
            logger.error("No objects to delete. Specify either names-file or query-filter")
            raise typer.Exit(1)
            
        # Log the objects to be deleted
        logger.info(f"Found {len(object_names)} {object_type} objects to delete")
        
        # In dry run mode, just show what would be deleted
        if dry_run:
            logger.info("Dry run mode: Changes will not be applied")
            for name in object_names:
                logger.info(f"  - Would delete {object_type} object: {name}")
            return
            
        # Confirm deletion unless force flag is used
        if not force:
            logger.warning(f"About to delete {len(object_names)} {object_type} objects. Proceed? (y/n)")
            confirmation = input().strip().lower()
            if confirmation != 'y':
                logger.info("Operation cancelled by user")
                raise typer.Exit(0)
        
        # Delete the objects
        deleted_count = 0
        failed_count = 0
        
        for name in object_names:
            try:
                if xml_config.delete_object(object_type, name, context, **context_kwargs):
                    logger.info(f"Successfully deleted {object_type} object '{name}'")
                    deleted_count += 1
                else:
                    logger.warning(f"Failed to delete {object_type} object '{name}'")
                    failed_count += 1
            except Exception as e:
                logger.warning(f"Error deleting {object_type} object '{name}': {e}")
                failed_count += 1
        
        # Save the updated configuration if any objects were deleted
        if deleted_count > 0:
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
                
        # Summarize the results
        logger.info(f"Deleted {deleted_count} objects. Failed to delete {failed_count} objects.")
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise typer.Exit(1)