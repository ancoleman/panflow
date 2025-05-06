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
from panflow.core.graph_service import GraphService
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

@object_app.command("find")
def find_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the object to find"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Regex pattern to match object names"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with value criteria"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Simple value to filter objects by (supports wildcards with *)"),
    ip_contains: Optional[str] = typer.Option(None, "--ip-contains", help="Filter address objects by IP/subnet containing this value"),
    port_equals: Optional[str] = typer.Option(None, "--port-equals", help="Filter service objects by exact port match"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Advanced graph query filter for complex filtering"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    version: Optional[str] = ConfigOptions.version(),
):
    """
    Find objects throughout the configuration regardless of context.
    
    This command searches across all contexts (shared, device groups, vsys, templates)
    to find objects with a specific name or matching specific value criteria.
    
    Examples:
    
        # Find all instances of an object by exact name throughout the configuration
        python panflow_cli.py object find --config panorama.xml --type address --name web-server
        
        # Find all objects with names matching a pattern (using regex)
        python panflow_cli.py object find --config panorama.xml --type address --pattern "web-.*"
        
        # Find address objects containing a specific IP (simple filtering)
        python panflow_cli.py object find --config panorama.xml --type address --ip-contains "10.88.0"
        
        # Find service objects with a specific port
        python panflow_cli.py object find --config panorama.xml --type service --port-equals "8080"
        
        # Find objects containing a value (with wildcard support)
        python panflow_cli.py object find --config panorama.xml --type address --value "10.*.0.0"
        
        # Combine name pattern and value filtering
        python panflow_cli.py object find --config panorama.xml --type address --pattern "web-.*" --ip-contains "10.0.0"
        
        # Use advanced graph query filtering for complex cases
        python panflow_cli.py object find --config panorama.xml --type address --pattern "web-.*" 
            --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"
        
        # Traditional method using criteria file
        python panflow_cli.py object find --config panorama.xml --type address --criteria ip-criteria.json
        
        # Example criteria file (ip-criteria.json) for finding address objects with a specific value:
        # {"ip-netmask": "10.0.0.0/24"}
        
        # Example criteria file for finding service objects with specific ports:
        # {"port": "8080"}
    """
    try:
        # Initialize the configuration and graph service
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        graph_service = GraphService()
        
        results = []
        
        # Find objects by name, pattern, or criteria
        if name:
            # Find by exact name
            logger.info(f"Finding {object_type} objects named '{name}' throughout the configuration...")
            locations = xml_config.find_objects_by_name(object_type, name, use_regex=False)
            results = locations
            
        elif pattern:
            # Find by regex pattern
            logger.info(f"Finding {object_type} objects with names matching pattern '{pattern}' throughout the configuration...")
            locations = xml_config.find_objects_by_name(object_type, pattern, use_regex=True)
            results = locations
            
        elif criteria_file:
            # Find by criteria
            with open(criteria_file, 'r') as f:
                value_criteria = json.load(f)
                
            logger.info(f"Finding {object_type} objects matching criteria {value_criteria} throughout the configuration...")
            locations = xml_config.find_objects_by_value(object_type, value_criteria)
            results = locations
            
        else:
            # Check if any of the user-friendly filter options were provided
            if not any([value, ip_contains, port_equals]):
                logger.error("Either --name, --pattern, --criteria, --value, --ip-contains, or --port-equals must be specified")
                raise typer.Exit(1)
            
            # If no name search was specified, search for all objects of the specified type
            if object_type == "address" and ip_contains:
                logger.info(f"Finding address objects containing IP '{ip_contains}' throughout the configuration...")
                
                # Use the graph service to find address objects containing the IP
                matching_names = graph_service.find_address_objects_containing_ip(
                    xml_config.tree, 
                    ip_contains
                )
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
                
            elif object_type == "service" and port_equals:
                logger.info(f"Finding service objects with port '{port_equals}' throughout the configuration...")
                
                # Use the graph service to find service objects with the port
                matching_names = graph_service.find_service_objects_with_port(
                    xml_config.tree, 
                    port_equals
                )
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
                
            elif value:
                logger.info(f"Finding {object_type} objects with value containing '{value}' throughout the configuration...")
                
                # Use the graph service to find objects with values matching the pattern
                matching_names = graph_service.find_objects_by_value_pattern(
                    xml_config.tree, 
                    object_type, 
                    value,
                    wildcard_support=True
                )
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
            
            if not results:
                # If no search method was provided, perform a search for all objects
                logger.info(f"Finding all {object_type} objects throughout the configuration...")
                
                # Use the graph service to execute a simple query for all objects of this type
                query_results = graph_service.execute_custom_query(
                    xml_config.tree,
                    f"MATCH (a:{object_type}) RETURN a.name"
                )
                
                # Extract names from the results
                all_obj_names = [row['a.name'] for row in query_results if 'a.name' in row]
                
                # Find the full object information across all contexts
                for obj_name in all_obj_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
            
        # Apply graph query filter if specified
        if query_filter and results:
            logger.info(f"Applying graph query filter: {query_filter}")
            
            # Use the graph service to filter the results
            filtered_results = graph_service.filter_objects_by_query(
                xml_config.tree,
                results,
                object_type,
                query_filter
            )
            
            logger.info(f"Graph query matched {len(filtered_results)} of {len(results)} objects")
            results = filtered_results
        
        # Display results
        logger.info(f"Found {len(results)} matching {object_type} objects:")
        
        for loc in results:
            logger.info(f"  - {loc}")
        
        # Save to file if requested
        if output and results:
            output_data = [loc.to_dict() for loc in results]
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results saved to {output}")
            
    except Exception as e:
        logger.error(f"Error finding objects: {e}")
        raise typer.Exit(1)

@object_app.command("find-duplicates")
def find_duplicate_objects(
    config: str = ConfigOptions.config_file(),
    by_name: bool = typer.Option(False, "--by-name", help="Find objects with the same name in different contexts"),
    by_value: bool = typer.Option(False, "--by-value", help="Find objects with the same value but different names"),
    object_type: Optional[str] = typer.Option(None, "--type", "-t", help="Type of object for by-value search (address, service, tag)"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Simple value to filter objects by (supports wildcards with *)"),
    ip_contains: Optional[str] = typer.Option(None, "--ip-contains", help="Filter address objects by IP/subnet containing this value"),
    port_equals: Optional[str] = typer.Option(None, "--port-equals", help="Filter service objects by exact port match"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Advanced graph query filter for complex filtering"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    version: Optional[str] = ConfigOptions.version(),
):
    """
    Find duplicate objects throughout the configuration.
    
    This command searches across all contexts (shared, device groups, vsys, templates)
    to find objects with the same name or the same value but different names.
    
    Examples:
    
        # Find objects with the same name in different contexts
        python panflow_cli.py object find-duplicates --config panorama.xml --by-name --output duplicate-names.json
        
        # Find address objects with the same IP value but different names
        python panflow_cli.py object find-duplicates --config panorama.xml --by-value --type address --output duplicate-values.json
        
        # Find service objects with the same port but different names
        python panflow_cli.py object find-duplicates --config panorama.xml --by-value --type service --output duplicate-services.json
        
        # Find duplicate address objects containing a specific IP
        python panflow_cli.py object find-duplicates --config panorama.xml --by-value --type address --ip-contains "10.88.0"
        
        # Find duplicate service objects with a specific port
        python panflow_cli.py object find-duplicates --config panorama.xml --by-value --type service --port-equals "8080"
        
        # Use advanced graph query filtering for complex cases
        python panflow_cli.py object find-duplicates --config panorama.xml --by-value --type address 
            --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"
    """
    try:
        # Initialize the configuration and graph service
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        graph_service = GraphService()
        
        results = {}
        
        # Validate options
        if not by_name and not by_value:
            logger.error("Either --by-name or --by-value must be specified")
            raise typer.Exit(1)
            
        if by_value and not object_type:
            logger.error("--type is required when using --by-value")
            raise typer.Exit(1)
        
        # Find duplicates
        if by_name:
            logger.info("Finding objects with duplicate names across different contexts...")
            duplicates = xml_config.find_duplicate_object_names()
            
            # Count total duplicates
            total_duplicates = sum(len(dup_dict) for dup_dict in duplicates.values())
            logger.info(f"Found {total_duplicates} object names with duplicates across different contexts")
            
            # Display results
            for obj_type, dups in duplicates.items():
                if dups:
                    logger.info(f"  {obj_type}: {len(dups)} duplicate names found")
                    for name, locations in dups.items():
                        logger.info(f"    - '{name}' found in {len(locations)} locations:")
                        for loc in locations:
                            logger.info(f"      * {loc.get_context_display()}")
            
            results = duplicates
            
        if by_value:
            logger.info(f"Finding {object_type} objects with the same value but different names...")
            
            # Check if any user-friendly filtering options were specified
            filtering_applied = False
            
            # Apply user-friendly filtering if specified
            filtered_duplicates = None
            
            if object_type == "address" and ip_contains:
                logger.info(f"Filtering by IP containing '{ip_contains}'...")
                filtering_applied = True
                
                # Find all duplicate address objects
                all_duplicates = xml_config.find_duplicate_object_values(object_type)
                
                # Get all address objects matching the IP pattern
                matching_names = set(graph_service.find_address_objects_containing_ip(
                    xml_config.tree, 
                    ip_contains
                ))
                
                # Filter duplicates by IP pattern using the matching names
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Keep only location objects whose names are in the matching_names set
                    matching_locations = [loc for loc in locations if loc.object_name in matching_names]
                    # Only include if we have multiple matching locations (duplicates)
                    if len(matching_locations) > 1:
                        filtered_duplicates[value_key] = matching_locations
                        
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching IP filter")
                
            elif object_type == "service" and port_equals:
                logger.info(f"Filtering by port equal to '{port_equals}'...")
                filtering_applied = True
                
                # Find all duplicate service objects
                all_duplicates = xml_config.find_duplicate_object_values(object_type)
                
                # Get all service objects matching the port
                matching_names = set(graph_service.find_service_objects_with_port(
                    xml_config.tree, 
                    port_equals
                ))
                
                # Filter duplicates by port using the matching names
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Keep only location objects whose names are in the matching_names set
                    matching_locations = [loc for loc in locations if loc.object_name in matching_names]
                    # Only include if we have multiple matching locations (duplicates)
                    if len(matching_locations) > 1:
                        filtered_duplicates[value_key] = matching_locations
                        
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching port filter")
                
            elif value:
                logger.info(f"Filtering by value containing '{value}'...")
                filtering_applied = True
                
                # Find all duplicate objects
                all_duplicates = xml_config.find_duplicate_object_values(object_type)
                
                # Get all objects matching the value pattern
                matching_names = set(graph_service.find_objects_by_value_pattern(
                    xml_config.tree, 
                    object_type, 
                    value,
                    wildcard_support=True
                ))
                
                # Filter duplicates by value pattern using the matching names
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Keep only location objects whose names are in the matching_names set
                    matching_locations = [loc for loc in locations if loc.object_name in matching_names]
                    # Only include if we have multiple matching locations (duplicates)
                    if len(matching_locations) > 1:
                        filtered_duplicates[value_key] = matching_locations
                        
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching value filter")
                
            # Apply graph query filter if specified
            if query_filter:
                logger.info(f"Applying graph query filter: {query_filter}")
                filtering_applied = True
                
                # Find all duplicate objects first
                if filtered_duplicates is None:
                    all_duplicates = xml_config.find_duplicate_object_values(object_type)
                else:
                    all_duplicates = filtered_duplicates
                
                # Execute the query to get matching object names
                query_results = graph_service.execute_custom_query(
                    xml_config.tree,
                    query_filter if "RETURN" in query_filter.upper() else f"{query_filter} RETURN a.name"
                )
                
                # Extract object names from the query results
                matching_names = set()
                for row in query_results:
                    if 'a.name' in row:
                        matching_names.add(row['a.name'])
                    elif len(row) == 1:  # If there's only one column, assume it's the name
                        matching_names.add(list(row.values())[0])
                
                # Filter duplicates by names matching the query
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Filter locations to those with matching names
                    matching_locations = [loc for loc in locations if loc.object_name in matching_names]
                    if len(matching_locations) > 1:  # Only include if we have multiple matching locations
                        filtered_duplicates[value_key] = matching_locations
                
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching graph query")
            
            # Use filtered results if any filtering was applied
            if filtering_applied:
                duplicates = filtered_duplicates
            else:
                duplicates = xml_config.find_duplicate_object_values(object_type)
            
            # Count total duplicate values
            logger.info(f"Found {len(duplicates)} unique values with multiple {object_type} objects")
            
            # Display results
            for value, locations in duplicates.items():
                names = set(loc.object_name for loc in locations)
                logger.info(f"  - Value '{value}' has {len(names)} different objects:")
                for name in names:
                    logger.info(f"    * {name}")
            
            results = duplicates
        
        # Save to file if requested
        if output and results:
            # Convert results to serializable format
            if by_name:
                output_data = {}
                for obj_type, dups in results.items():
                    output_data[obj_type] = {}
                    for name, locations in dups.items():
                        output_data[obj_type][name] = [loc.to_dict() for loc in locations]
            else:  # by_value
                output_data = {}
                for value, locations in results.items():
                    output_data[value] = [loc.to_dict() for loc in locations]
            
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results saved to {output}")
            
    except Exception as e:
        logger.error(f"Error finding duplicate objects: {e}")
        raise typer.Exit(1)