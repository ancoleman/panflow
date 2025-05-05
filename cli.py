
#!/usr/bin/env python3
"""
PANFlow for PAN-OS XML CLI

A comprehensive command-line interface for working with PAN-OS XML configurations
using the dynamic PAN-OS XML utilities.

DEPRECATION NOTICE: This script is being deprecated in favor of panflow_cli.py.
Some functionality is only available here, but all functionality will eventually 
be migrated to the package-based CLI accessed via panflow_cli.py.
"""

import warnings
warnings.warn(
    "cli.py is deprecated and will be removed in a future version. "
    "Please use panflow_cli.py instead.", 
    DeprecationWarning, 
    stacklevel=2
)

import os
import sys
import json
from typing import Optional, Dict, List
import typer
import logging
from lxml import etree

# Import the core modules
from panflow import (
    PANFlowConfig, configure_logging, get_all_versions
)
from panflow.core.logging_utils import (
    verbose_callback, quiet_callback, log_level_callback, log_file_callback
)

from panflow.core.deduplication import DeduplicationEngine
from panflow.core.policy_merger import PolicyMerger
from panflow.core.object_merger import ObjectMerger
from panflow.core.conflict_resolver import ConflictStrategy
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow.core.object_finder import ObjectLocation
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, TypeVar
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
from panflow.core.bulk_operations import ConfigUpdater
# Create main Typer app
app = typer.Typer(help="PANFlow CLI")
object_app = typer.Typer(help="Object management commands")
policy_app = typer.Typer(help="Policy management commands")
group_app = typer.Typer(help="Group management commands")
report_app = typer.Typer(help="Report generation commands")
config_app = typer.Typer(help="Configuration management commands")
merge_app = typer.Typer(help="Policy and Object merge commands")
query_app = typer.Typer(help="Graph query commands")


# Add sub-apps to main app
app.add_typer(object_app, name="object")
app.add_typer(policy_app, name="policy")
app.add_typer(group_app, name="group")
app.add_typer(report_app, name="report")
app.add_typer(config_app, name="config")
app.add_typer(merge_app, name="merge")
app.add_typer(query_app, name="query")

# Get logger
logger = logging.getLogger("panflow")

# Type variable for callback return type
T = TypeVar('T')

# Helper functions for CLI parameter validation and conversion
def conflict_strategy_callback(value: str) -> Optional[ConflictStrategy]:
    """
    Validates and converts the conflict strategy string to the appropriate enum value.
    
    Args:
        value: The string representation of the conflict strategy
        
    Returns:
        The corresponding ConflictStrategy enum value
        
    Raises:
        typer.BadParameter: If the provided value is not a valid conflict strategy
    """
    if not value:
        return None
        
    valid_strategies = [s.value for s in ConflictStrategy]
    
    if value not in valid_strategies:
        strategies_str = ", ".join(valid_strategies)
        raise typer.BadParameter(
            f"Invalid conflict strategy: '{value}'. Valid options are: {strategies_str}"
        )
    
    return ConflictStrategy(value)

# Main CLI command callback
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output", callback=verbose_callback),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress console output", callback=quiet_callback),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Set log level (debug, info, warning, error, critical)", callback=log_level_callback),
    log_file: Optional[str] = typer.Option(None, "--log-file", "-f", help="Log to file", callback=log_file_callback),
):
    """
    PANFlow Utilities CLI

    A comprehensive command-line interface for working with PAN-OS XML configurations
    using the PANFlow utilities.
    """
    # Ensure logging is configured properly with the right level for console output
    from panflow.core.logging_utils import configure_logging
    
    try:
        # Log level will already be set by callbacks, but we need to ensure a console handler exists
        configure_logging(level=log_level, log_file=log_file, quiet=quiet, verbose=verbose)
        logger.info("PANFLow CLI initialized")
    except Exception as e:
        # Fallback to basic print if logging configuration fails
        print(f"Error configuring logging: {e}")
        print("Continuing with default logging configuration")
        
    # Display version and device information
    import sys
    import platform
    
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {platform.platform()}")
    logger.debug(f"lxml version: {etree.LXML_VERSION}")
    
    # Set up exception handling for the CLI
    sys.excepthook = _global_exception_handler

# ===== Exception Handler =====
def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for unhandled exceptions.
    Provides more user-friendly error messages for common issues.
    """
    if isinstance(exc_value, FileNotFoundError):
        logger.error(f"File not found: {exc_value}")
        sys.exit(1)
    elif isinstance(exc_value, etree.XMLSyntaxError):
        logger.error(f"XML syntax error: {exc_value}")
        sys.exit(1)
    elif isinstance(exc_value, ValueError):
        logger.error(f"Value error: {exc_value}")
        sys.exit(1)
    elif isinstance(exc_value, KeyError):
        logger.error(f"Missing key in configuration: {exc_value}")
        sys.exit(1)
    elif isinstance(exc_value, PermissionError):
        logger.error(f"Permission denied: {exc_value}")
        sys.exit(1)
    else:
        # For other exceptions, show the full traceback in debug mode
        logger.error(f"Unexpected error: {exc_type.__name__}: {exc_value}")
        if logger.getEffectiveLevel() <= logging.DEBUG:
            import traceback
            logger.debug("Traceback:")
            for line in traceback.format_tb(exc_traceback):
                logger.debug(line.rstrip())
        sys.exit(1)

# ===== Object Commands =====

@object_app.command("list")
def list_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to list (address, service, etc.)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """List objects of specified type"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        logger.info(f"Listing {object_type} objects in {context} context...")
        
        # Get objects (the get_objects function will log details about what it finds)
        objects = xml_config.get_objects(object_type, context, **context_kwargs)
        
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
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to add (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with object properties"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Add a new object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
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
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to update (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with updated object properties"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Update an existing object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
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
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to delete (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Delete an object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
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
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to filter (address, service, etc.)"),
    criteria_file: str = typer.Option(..., "--criteria", help="JSON file with filter criteria"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Filter objects based on criteria"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read criteria from file
        with open(criteria_file, 'r') as f:
            criteria = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Filter objects
        filtered_objects = xml_config.filter_objects(object_type, criteria, context, **context_kwargs)
        logger.info(f"Found {len(filtered_objects)} {object_type} objects matching criteria")
        
        # Display filtered objects
        for name in filtered_objects:
            logger.info(f"  - {name}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(filtered_objects, f, indent=2)
            logger.info(f"Filtered objects saved to {output}")
            
    except Exception as e:
        logger.error(f"Error filtering objects: {e}")
        raise typer.Exit(1)

@object_app.command("find")
def find_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to find (address, service, etc.)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the object to find"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Regex pattern to match object names"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with value criteria"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Simple value to filter objects by (supports wildcards with *)"),
    ip_contains: Optional[str] = typer.Option(None, "--ip-contains", help="Filter address objects by IP/subnet containing this value"),
    port_equals: Optional[str] = typer.Option(None, "--port-equals", help="Filter service objects by exact port match"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Advanced graph query filter for complex filtering"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """
    Find objects throughout the configuration regardless of context.
    
    This command searches across all contexts (shared, device groups, vsys, templates)
    to find objects with a specific name or matching specific value criteria.
    
    Examples:
        # Find all instances of an object by exact name throughout the configuration
        python cli.py object find --config panorama.xml --type address --name web-server
        
        # Find all objects with names matching a pattern (using regex)
        python cli.py object find --config panorama.xml --type address --pattern "web-.*"
        
        # Find address objects containing a specific IP (simple filtering)
        python cli.py object find --config panorama.xml --type address --ip-contains "10.88.0"
        
        # Find service objects with a specific port
        python cli.py object find --config panorama.xml --type service --port-equals "8080"
        
        # Find objects containing a value (with wildcard support)
        python cli.py object find --config panorama.xml --type address --value "10.*.0.0"
        
        # Combine name pattern and value filtering
        python cli.py object find --config panorama.xml --type address --pattern "web-.*" --ip-contains "10.0.0"
        
        # Use advanced graph query filtering for complex cases
        python cli.py object find --config panorama.xml --type address --pattern "web-.*" 
            --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"
        
        # Traditional method using criteria file
        python cli.py object find --config panorama.xml --type address --criteria ip-criteria.json
        
        # Example criteria file (ip-criteria.json) for finding address objects with a specific value:
        # {"ip-netmask": "10.0.0.0/24"}
        
        # Example criteria file for finding service objects with specific ports:
        # {"port": "8080"}
    """
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
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
                
                # Convert the simple IP string to a proper regex pattern for address objects
                ip_pattern = ip_contains.replace(".", "\\.")  # Escape dots for regex
                
                # Generate a graph query to find address objects containing this IP
                query_text = f"MATCH (a:address) WHERE a.value =~ '.*{ip_pattern}.*' RETURN a.name"
                
                # Use the graph query system with our simplified syntax
                graph = ConfigGraph()
                graph.build_from_xml(xml_config.tree)
                query = Query(query_text)
                executor = QueryExecutor(graph)
                query_results = executor.execute(query)
                
                # Get all matching object names
                matching_names = [row['a.name'] for row in query_results if 'a.name' in row]
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
                
            elif object_type == "service" and port_equals:
                logger.info(f"Finding service objects with port '{port_equals}' throughout the configuration...")
                
                # Generate a graph query to find service objects with this port
                query_text = f"MATCH (s:service) WHERE s.dst_port == '{port_equals}' RETURN s.name"
                
                # Use the graph query system with our simplified syntax
                graph = ConfigGraph()
                graph.build_from_xml(xml_config.tree)
                query = Query(query_text)
                executor = QueryExecutor(graph)
                query_results = executor.execute(query)
                
                # Get all matching object names
                matching_names = [row['s.name'] for row in query_results if 's.name' in row]
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
                
            elif value:
                logger.info(f"Finding {object_type} objects with value containing '{value}' throughout the configuration...")
                
                # Convert wildcards to regex pattern
                regex_pattern = value.replace(".", "\\.").replace("*", ".*")
                
                # Generate a graph query to find objects with values matching this pattern
                query_text = f"MATCH (a:{object_type}) WHERE a.value =~ '.*{regex_pattern}.*' RETURN a.name"
                
                # Use the graph query system with our simplified syntax
                graph = ConfigGraph()
                graph.build_from_xml(xml_config.tree)
                query = Query(query_text)
                executor = QueryExecutor(graph)
                query_results = executor.execute(query)
                
                # Get all matching object names
                matching_names = [row['a.name'] for row in query_results if 'a.name' in row]
                
                # Find the full object information across all contexts
                for obj_name in matching_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
            
            if not results:
                # If no search method was provided, perform a search for all objects
                logger.info(f"Finding all {object_type} objects throughout the configuration...")
                
                # First find all objects of this type using the graph
                graph = ConfigGraph()
                graph.build_from_xml(xml_config.tree)
                query = Query(f"MATCH (a:{object_type}) RETURN a.name")
                executor = QueryExecutor(graph)
                query_results = executor.execute(query)
                
                # Get all object names
                all_obj_names = [row['a.name'] for row in query_results if 'a.name' in row]
                
                # Find the full object information across all contexts
                for obj_name in all_obj_names:
                    locations = xml_config.find_objects_by_name(object_type, obj_name, use_regex=False)
                    results.extend(locations)
            
        # Apply graph query filter if specified
        if query_filter and results:
            logger.info(f"Applying graph query filter: {query_filter}")
            
            # Build a graph from the configuration
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Prepare a query that returns object names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter
                
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            query_results = executor.execute(query)
            
            # Extract object names from the query results
            matching_names = []
            for row in query_results:
                if 'a.name' in row:
                    matching_names.append(row['a.name'])
                elif len(row) == 1:  # If there's only one column, use its value
                    matching_names.append(list(row.values())[0])
                    
            # Filter the object finder results by the names that also matched the query
            filtered_results = [loc for loc in results if loc.object_name in matching_names]
            
            logger.info(f"Graph query matched {len(filtered_results)} of {len(results)} objects")
            results = filtered_results
        
        # Display results
        logger.info(f"Found {len(results)} matching {object_type} objects:")
        
        for loc in results:
            logger.info(f"  - {loc}")
        
        # Save to file if requested
        if output:
            output_data = [loc.to_dict() for loc in results]
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results saved to {output}")
            
    except Exception as e:
        logger.error(f"Error finding objects: {e}")
        raise typer.Exit(1)

@object_app.command("find-duplicates")
def find_duplicate_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    by_name: bool = typer.Option(False, "--by-name", help="Find objects with the same name in different contexts"),
    by_value: bool = typer.Option(False, "--by-value", help="Find objects with the same value but different names"),
    object_type: Optional[str] = typer.Option(None, "--type", "-t", help="Type of object for by-value search (address, service, tag)"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Simple value to filter objects by (supports wildcards with *)"),
    ip_contains: Optional[str] = typer.Option(None, "--ip-contains", help="Filter address objects by IP/subnet containing this value"),
    port_equals: Optional[str] = typer.Option(None, "--port-equals", help="Filter service objects by exact port match"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Advanced graph query filter for complex filtering"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """
    Find duplicate objects throughout the configuration.
    
    This command searches across all contexts (shared, device groups, vsys, templates)
    to find objects with the same name or the same value but different names.
    
    Examples:
        # Find objects with the same name in different contexts
        python cli.py object find-duplicates --config panorama.xml --by-name --output duplicate-names.json
        
        # Find address objects with the same IP value but different names
        python cli.py object find-duplicates --config panorama.xml --by-value --type address --output duplicate-values.json
        
        # Find service objects with the same port but different names
        python cli.py object find-duplicates --config panorama.xml --by-value --type service --output duplicate-services.json
        
        # Find duplicate address objects containing a specific IP
        python cli.py object find-duplicates --config panorama.xml --by-value --type address --ip-contains "10.88.0"
        
        # Find duplicate service objects with a specific port
        python cli.py object find-duplicates --config panorama.xml --by-value --type service --port-equals "8080"
        
        # Use advanced graph query filtering for complex cases
        python cli.py object find-duplicates --config panorama.xml --by-value --type address 
            --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"
    """
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
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
                
                # Filter duplicates by IP pattern
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Check if the value contains the specified IP
                    if ip_contains in value_key:
                        filtered_duplicates[value_key] = locations
                        
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching IP filter")
                
            elif object_type == "service" and port_equals:
                logger.info(f"Filtering by port equal to '{port_equals}'...")
                filtering_applied = True
                
                # Find all duplicate service objects
                all_duplicates = xml_config.find_duplicate_object_values(object_type)
                
                # Filter duplicates by port
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Check if the value contains the specified port
                    if f"port:{port_equals}" in value_key:
                        filtered_duplicates[value_key] = locations
                        
                logger.info(f"Found {len(filtered_duplicates)} values with duplicates matching port filter")
                
            elif value:
                logger.info(f"Filtering by value containing '{value}'...")
                filtering_applied = True
                
                # Convert wildcards to regex pattern
                import re
                pattern_str = value.replace(".", "\\.").replace("*", ".*")
                pattern = re.compile(pattern_str)
                
                # Find all duplicate objects
                all_duplicates = xml_config.find_duplicate_object_values(object_type)
                
                # Filter duplicates by value pattern
                filtered_duplicates = {}
                for value_key, locations in all_duplicates.items():
                    # Check if the value matches the pattern
                    if pattern.search(value_key):
                        filtered_duplicates[value_key] = locations
                        
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
                
                # Build a graph from the configuration
                graph = ConfigGraph()
                graph.build_from_xml(xml_config.tree)
                
                # Prepare a query that returns object names
                if "RETURN" not in query_filter.upper():
                    query_text = f"{query_filter} RETURN a.name"
                else:
                    query_text = query_filter
                    
                # Execute the query
                query = Query(query_text)
                executor = QueryExecutor(graph)
                query_results = executor.execute(query)
                
                # Extract object names from the query results
                matching_names = []
                for row in query_results:
                    if 'a.name' in row:
                        matching_names.append(row['a.name'])
                    elif len(row) == 1:  # If there's only one column, use its value
                        matching_names.append(list(row.values())[0])
                
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
        if output:
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

# ===== Policy Commands =====

@policy_app.command("list")
def list_policies(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to list (security_pre_rules, nat_rules, etc.)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """List policies of specified type"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Get policies
        policies = xml_config.get_policies(policy_type, context, **context_kwargs)
        logger.info(f"Found {len(policies)} {policy_type} policies")
        
        # Display policies
        for name in policies:
            logger.info(f"  - {name}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(policies, f, indent=2)
            logger.info(f"Policies saved to {output}")
            
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise typer.Exit(1)

# Implement remaining policy commands similar to object commands

# ===== Group Commands =====

@group_app.command("add-member")
def add_group_member(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    group_type: str = typer.Option(..., "--type", "-t", help="Type of group (address_group, service_group, etc.)"),
    group_name: str = typer.Option(..., "--group", "-g", help="Name of the group"),
    member_name: str = typer.Option(..., "--member", "-m", help="Name of the member to add"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Add a member to a group"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Add member to group
        if xml_config.add_member_to_group(group_type, group_name, member_name, context, **context_kwargs):
            logger.info(f"Successfully added member '{member_name}' to {group_type} '{group_name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to add member '{member_name}' to {group_type} '{group_name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error adding member to group: {e}")
        raise typer.Exit(1)

# Implement remaining group commands

# ===== Report Commands =====

@report_app.command("unused-objects")
def report_unused_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for report (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Generate report of unused objects"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Generate report
        report = xml_config.generate_unused_objects_report(context, output, **context_kwargs)
        
        # Print summary
        if "unused_objects" in report:
            unused_objects = report["unused_objects"]
            logger.info(f"Found {len(unused_objects)} unused address objects")
            
            # Display unused objects
            for obj in unused_objects:
                logger.info(f"  - {obj['name']}")
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise typer.Exit(1)

# Implement remaining report commands

# ===== Configuration Commands =====

@config_app.command("validate")
def validate_config(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Validate XML configuration structure"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Basic validation is performed during loading
        logger.info(f"Configuration file loaded and validated successfully")
        logger.info(f"Detected PAN-OS version: {xml_config.version}")
        logger.info(f"Detected device type: {xml_config.device_type}")
        
        # Additional validation could be implemented here
        
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise typer.Exit(1)

# Implement remaining config commands (merge, compare, etc.)

@policy_app.command("bulk-update")
def bulk_update_policies(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to update"),
    criteria_file: str = typer.Option(..., "--criteria", help="JSON file with filter criteria"),
    operations_file: str = typer.Option(..., "--operations", help="JSON file with update operations"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
):
    """Bulk update policies matching criteria with specified operations"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Read criteria and operations from files
        with open(criteria_file, 'r') as f:
            criteria = json.load(f)
        
        with open(operations_file, 'r') as f:
            operations = json.load(f)
        
        # Create updater and perform bulk update
        updater = ConfigUpdater(xml_config.tree, device_type, context, xml_config.version, **context_kwargs)
        updated_count = updater.bulk_update_policies(policy_type, criteria, operations)
        
        logger.info(f"Updated {updated_count} policies")
        
        # Save the updated configuration
        if xml_config.save(output):
            logger.info(f"Configuration saved to {output}")
        else:
            logger.error(f"Failed to save configuration to {output}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise typer.Exit(1)

@app.command("deduplicate")
def deduplicate_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to deduplicate"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type"),
    context: str = typer.Option("shared", "--context", help="Context"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    strategy: str = typer.Option("first", "--strategy", help="Strategy for choosing primary object"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
):
    """Find and merge duplicate objects"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Create deduplication engine
        engine = DeduplicationEngine(xml_config.tree, device_type, context, xml_config.version, **context_kwargs)
        
        # Find duplicates and references
        duplicates, references = engine.find_duplicate_addresses()
        
        if not duplicates:
            logger.info("No duplicate objects found")
            return
        
        # Log the duplicates found
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            logger.info(f"Found duplicates with value {value_key}: {', '.join(names)}")
        
        if dry_run:
            logger.info("Dry run - no changes made")
            return
        
        # Merge duplicates
        changes = engine.merge_duplicates(duplicates, references, strategy)
        
        # Apply the changes
        for change_type, name, obj in changes:
            if change_type == 'delete':
                # Delete the object
                parent = obj.getparent()
                if parent is not None:
                    parent.remove(obj)
                    logger.info(f"Deleted duplicate object: {name}")
        
        # Save the updated configuration
        if xml_config.save(output):
            logger.info(f"Configuration saved to {output}")
        else:
            logger.error(f"Failed to save configuration to {output}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error in deduplication: {e}")
        raise typer.Exit(1)

@merge_app.command("policy")
def merge_policy(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to merge (security_pre_rules, nat_rules, etc.)"),
    policy_name: str = typer.Option(..., "--name", "-n", help="Name of the policy to merge"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    position: str = typer.Option("bottom", "--position", help="Position to add policy (top, bottom, before, after)"),
    ref_policy: Optional[str] = typer.Option(None, "--ref-policy", help="Reference policy for before/after position"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge a policy from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Merge the policy
        result = merger.copy_policy(
            policy_type,
            policy_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            position,
            ref_policy,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if result:
            logger.info(f"Successfully merged policy '{policy_name}'")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - Policy '{policy_name}' would be added to {target_context}")
                if copy_references and merger.copied_objects:
                    logger.info(f"  - {len(merger.copied_objects)} referenced objects would be copied")
        else:
            logger.error(f"Failed to merge policy '{policy_name}'")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies:
                    logger.warning(f"  - {name}: {reason}")
                    
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging policy: {e}")
        raise typer.Exit(1)

@merge_app.command("policies")
def merge_policies(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to merge (security_pre_rules, nat_rules, etc.)"),
    policy_names_file: Optional[str] = typer.Option(None, "--names-file", help="File containing policy names to merge (one per line)"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge multiple policies from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Get policy names or criteria
        policy_names = None
        filter_criteria = None
        
        if policy_names_file:
            with open(policy_names_file, 'r') as f:
                policy_names = [line.strip() for line in f if line.strip()]
        
        if criteria_file:
            with open(criteria_file, 'r') as f:
                import json
                filter_criteria = json.load(f)
        
        if not policy_names and not filter_criteria:
            logger.error("Either policy names file or criteria file must be provided")
            raise typer.Exit(1)
        
        # Merge the policies
        copied, total = merger.copy_policies(
            policy_type,
            source_context,
            target_context,
            policy_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} policies")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects[:10]:  # Show first 10
                    logger.debug(f"  - {obj_type}: {obj_name}")
                
                if len(merger.copied_objects) > 10:
                    logger.debug(f"  ... and {len(merger.copied_objects) - 10} more")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - {copied} policies of type {policy_type} would be added to {target_context}")
                if copy_references and merger.copied_objects:
                    logger.info(f"  - {len(merger.copied_objects)} referenced objects would be copied")
        else:
            logger.warning(f"No policies were merged (attempted {total})")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")
                
                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging policies: {e}")
        raise typer.Exit(1)

@merge_app.command("all")
def merge_all_policies(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge all policy types from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Determine policy types based on device type
        from panflow.constants import POLICY_TYPES
        
        policy_types = POLICY_TYPES.get(source_device_type.lower(), [])
        
        if not policy_types:
            logger.error(f"Unknown device type: {source_device_type}")
            raise typer.Exit(1)
        
        # Merge all policy types
        results = merger.merge_all_policies(
            policy_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        # Calculate total policies merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())
        
        if total_copied > 0:
            logger.info(f"Successfully merged {total_copied} of {total_attempted} policies across all policy types")
            
            # Log details per policy type
            for policy_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {policy_type}: {copied} of {total} policies merged")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                
                # Count by type
                object_counts = {}
                for obj_type, _ in merger.copied_objects:
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
                
                for obj_type, count in object_counts.items():
                    logger.info(f"  - {obj_type}: {count} objects copied")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - {total_copied} policies would be added to {target_context} across all policy types")
                for policy_type, (copied, total) in results.items():
                    if total > 0:
                        logger.info(f"    - {policy_type}: {copied} of {total} policies would be merged")
                if copy_references and merger.copied_objects:
                    logger.info(f"  - {len(merger.copied_objects)} referenced objects would be copied")
        else:
            logger.warning(f"No policies were merged (attempted {total_attempted})")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")
                
                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging all policies: {e}")
        raise typer.Exit(1)

# Add to the imports in cli.py
from panflow.core.object_merger import ObjectMerger

# Add these commands to the merge_app group in cli.py

@merge_app.command("object")
def merge_object(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to merge (address, service, etc.)"),
    object_name: str = typer.Option(..., "--name", "-n", help="Name of the object to merge"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge a single object from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Merge the object
        result = merger.copy_object(
            object_type,
            object_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if result:
            logger.info(f"Successfully merged object '{object_name}'")
            
            # Log referenced/copied objects
            if copy_references and merger.referenced_objects:
                logger.info(f"Referenced {len(merger.referenced_objects)} objects")
                for obj_type, obj_name in merger.referenced_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - Object '{object_name}' of type {object_type} would be added to {target_context}")
                if copy_references and merger.referenced_objects:
                    logger.info(f"  - {len(merger.referenced_objects)} referenced objects would be copied")
        else:
            logger.error(f"Failed to merge object '{object_name}'")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects:
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                    
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging object: {e}")
        raise typer.Exit(1)

@merge_app.command("objects")
def merge_objects(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to merge (address, service, etc.)"),
    names_file: Optional[str] = typer.Option(None, "--names-file", help="File containing object names to merge (one per line)"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge multiple objects from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Get object names or criteria
        object_names = None
        filter_criteria = None
        
        if names_file:
            with open(names_file, 'r') as f:
                object_names = [line.strip() for line in f if line.strip()]
        
        if criteria_file:
            with open(criteria_file, 'r') as f:
                import json
                filter_criteria = json.load(f)
        
        if not object_names and not filter_criteria:
            logger.error("Either object names file or criteria file must be provided")
            raise typer.Exit(1)
        
        # Merge the objects
        copied, total = merger.copy_objects(
            object_type,
            source_context,
            target_context,
            object_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} {object_type} objects")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - {copied} {object_type} objects would be added to {target_context}")
        else:
            logger.warning(f"No {object_type} objects were merged (attempted {total})")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                
                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging objects: {e}")
        raise typer.Exit(1)

@merge_app.command("all-objects")
def merge_all_objects(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists (deprecated, use conflict_strategy instead)"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    conflict_strategy: Optional[ConflictStrategy] = typer.Option("skip", "--conflict-strategy", 
                                                              help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source", 
                                                              callback=conflict_strategy_callback),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without modifying the target configuration"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge all object types from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Determine object types to merge
        from panflow.constants import OBJECT_TYPES
        object_types = ["address", "address_group", "service", "service_group", 
                        "application_group", "tag"]
        
        # Merge all object types
        results = merger.merge_all_objects(
            object_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        # Calculate total objects merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())
        
        if total_copied > 0:
            logger.info(f"Successfully merged {total_copied} of {total_attempted} objects across all types")
            
            # Log details per object type
            for object_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {object_type}: {copied} of {total} objects merged")
            
            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(f"If this was not a dry run, the following changes would have been made:")
                logger.info(f"  - {total_copied} objects would be added to {target_context} across all object types")
                for object_type, (copied, total) in results.items():
                    if total > 0:
                        logger.info(f"    - {object_type}: {copied} of {total} objects would be merged")
        else:
            logger.warning(f"No objects were merged (attempted {total_attempted})")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                
                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging all objects: {e}")
        raise typer.Exit(1)
# Add the query commands
@query_app.command("execute")
def execute_query(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    query: str = typer.Option(..., "--query", "-q", help="Graph query to execute"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, csv)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """
    Execute a graph query on a PAN-OS configuration.
    
    Example:
        panflow query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value"
    """
    try:
        # Load the XML configuration
        from panflow.core.xml_utils import load_xml_file
        from panflow.core.graph_utils import ConfigGraph
        from panflow.core.query_language import Query
        from panflow.core.query_engine import QueryExecutor
        from rich.console import Console
        from rich.table import Table
        from rich.syntax import Syntax
        
        xml_root = load_xml_file(config)
        
        # Build the graph
        graph = ConfigGraph()
        graph.build_from_xml(xml_root)
        
        # Parse and execute the query
        parsed_query = Query(query)
        executor = QueryExecutor(graph)
        results = executor.execute(parsed_query)
        
        # Setup console
        console = Console()
        
        # Display the results
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
            
        if output_format == "json":
            output_data = json.dumps(results, indent=2)
            if output:
                with open(output, "w") as f:
                    f.write(output_data)
                logger.info(f"Results saved to {output}")
            else:
                syntax = Syntax(output_data, "json", theme="monokai", line_numbers=True)
                console.print(syntax)
                
        elif output_format == "csv":
            if not output:
                logger.warning("CSV format requires an output file")
                return
                
            # Get header from first result
            headers = list(results[0].keys())
            
            # Write CSV file
            with open(output, "w") as f:
                # Write header
                f.write(",".join([f'"{h}"' for h in headers]) + "\n")
                
                # Write rows
                for row in results:
                    values = []
                    for header in headers:
                        value = row.get(header, "")
                        if isinstance(value, str):
                            # Escape quotes and wrap in quotes
                            escaped_value = value.replace('"', '\\"')
                            value = f'"{escaped_value}"'
                        else:
                            value = str(value)
                        values.append(value)
                    f.write(",".join(values) + "\n")
                    
            logger.info(f"Results saved to {output}")
            
        else:  # table format
            # Get columns from first result
            columns = list(results[0].keys())
            
            table = Table()
            for column in columns:
                table.add_column(column, style="cyan")
                
            # Add rows
            for row in results:
                table.add_row(*[str(row.get(col, "")) for col in columns])
                
            if output:
                # Save table as text
                with open(output, "w") as f:
                    # Write header
                    header = " | ".join(columns)
                    f.write(header + "\n")
                    f.write("-" * len(header) + "\n")
                    
                    # Write rows
                    for row in results:
                        f.write(" | ".join([str(row.get(col, "")) for col in columns]) + "\n")
                        
                logger.info(f"Results saved to {output}")
            else:
                console.print(table)
                
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise typer.Exit(1)

@query_app.command("verify")
def verify_query(
    query: str = typer.Option(..., "--query", "-q", help="Graph query to verify"),
):
    """
    Verify a graph query syntax without executing it.
    
    Example:
        panflow query verify -q "MATCH (a:address) RETURN a.name"
    """
    try:
        from panflow.core.query_language import Lexer, Query
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        # Parse the query to verify syntax
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        
        # Display tokens
        table = Table(title="Query Tokens")
        table.add_column("Type", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Position", style="blue")
        
        for token in tokens:
            if token.type.name == "EOF":
                continue
            table.add_row(token.type.name, token.value, str(token.position))
            
        console.print(table)
        
        # Try to parse the query
        parsed_query = Query(query)
        
        # Display success message
        console.print("[bold green]Query syntax is valid[/bold green]")
        
    except Exception as e:
        logger.error(f"Syntax Error: {str(e)}")
        raise typer.Exit(1)

@query_app.command("example")
def example_queries():
    """
    Show example graph queries.
    
    Example:
        panflow query example
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    examples = [
        {
            "name": "Find all address objects",
            "query": "MATCH (a:address) RETURN a.name, a.value, a.addr_type",
            "description": "This query returns all address objects with their names, values, and types."
        },
        {
            "name": "Find all address groups and their members",
            "query": "MATCH (g:address-group)-[:contains]->(a:address) RETURN g.name, a.name",
            "description": "This query returns all address groups and their member addresses."
        },
        {
            "name": "Find all security rules using a specific address",
            "query": "MATCH (r:security-rule)-[:uses-source|uses-destination]->(a:address) WHERE a.name == 'web-server' RETURN r.name",
            "description": "This query returns all security rules that use 'web-server' as a source or destination."
        },
        {
            "name": "Find all unused address objects",
            "query": "MATCH (a:address) WHERE NOT ((:security-rule)-[:uses-source|uses-destination]->(a)) AND NOT ((:address-group)-[:contains]->(a)) RETURN a.name",
            "description": "This query returns all address objects that are not used in any security rule or address group."
        },
        {
            "name": "Find rules allowing specific services",
            "query": "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http' OR s.name == 'https' RETURN r.name",
            "description": "This query returns all security rules that allow HTTP or HTTPS services."
        }
    ]
    
    table = Table(title="Example Graph Queries")
    table.add_column("Name", style="cyan")
    table.add_column("Query", style="green")
    table.add_column("Description", style="blue")
    
    for example in examples:
        table.add_row(example["name"], example["query"], example["description"])
        
    console.print(table)

# Run the CLI
if __name__ == "__main__":
    app()