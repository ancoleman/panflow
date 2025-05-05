"""
Deduplication commands for PANFlow CLI.

This module provides commands for finding and merging duplicate objects in PAN-OS configurations.
"""

import logging
import typer
from typing import Optional, List
import json

from ..app import app
from ..common import (
    ConfigOptions, ContextOptions, ObjectOptions,
    common_options
)

# Import core modules
from panflow import PANFlowConfig
from panflow.core.deduplication import DeduplicationEngine
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor

# Get logger
logger = logging.getLogger("panflow")

# Create deduplicate app
deduplicate_app = typer.Typer(help="Find and merge duplicate objects")

# Register with main app
app.add_typer(deduplicate_app, name="deduplicate")

# Define supported object types
SUPPORTED_OBJECT_TYPES = ["address", "service", "tag"]

def object_type_callback(value: str) -> str:
    """Validate object type is supported for deduplication."""
    normalized = value.lower()
    if normalized not in SUPPORTED_OBJECT_TYPES and normalized not in [f"{t}s" for t in SUPPORTED_OBJECT_TYPES]:
        supported_str = ", ".join(SUPPORTED_OBJECT_TYPES)
        raise typer.BadParameter(f"Object type '{value}' not supported. Supported types: {supported_str}")
    return value

@deduplicate_app.command("find")
def find_duplicates(
    config: str = ConfigOptions.config_file(),
    object_type: str = typer.Option(
        ..., "--type", "-t", 
        help="Type of object to deduplicate (address, service, tag)",
        callback=object_type_callback
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Pattern to filter objects (e.g. '10.0.0' for addresses)"),
    include_file: Optional[str] = typer.Option(None, "--include-file", help="JSON file with list of object names to include in results"),
    exclude_file: Optional[str] = typer.Option(None, "--exclude-file", help="JSON file with list of object names to exclude from results"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')"),
    min_group_size: int = typer.Option(2, "--min-group-size", "-g", help="Minimum number of objects in a duplicate group to include in results"),
    version: Optional[str] = ConfigOptions.version(),
):
    """Find duplicate objects of specified type"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Create deduplication engine
        engine = DeduplicationEngine(
            xml_config.tree, 
            device_type, 
            context, 
            xml_config.version, 
            **context_kwargs
        )
        
        # Find duplicates and references
        duplicates, references = engine.find_duplicates(object_type)
            
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found")
            return
        
        # Load include/exclude lists
        include_list = []
        exclude_list = []
        
        # Process query filter if provided
        if query_filter:
            logger.info(f"Processing graph query filter: {query_filter}")
            # Build graph from the configuration
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Create a query executor
            executor = QueryExecutor(graph)
            
            # Parse the query and ensure it has a RETURN clause
            query = Query(query_filter)
            if not query.has_return_clause():
                # Add a return clause based on object type
                node_type = object_type.rstrip('s')  # Strip trailing 's' if present
                query.add_return(f"a.name as name")
                logger.info(f"Added return clause to query: {query.query}")
            
            # Execute the query
            results = executor.execute(query.query)
            
            # Extract object names from results
            query_objects = []
            for result in results:
                if 'name' in result:
                    query_objects.append(result['name'])
                elif len(result) == 1:
                    # If there's only one field, use it
                    query_objects.append(list(result.values())[0])
            
            if query_objects:
                # Add query results to include list
                include_list = query_objects
                logger.info(f"Using query results for include list: {len(include_list)} objects")
            else:
                logger.info("Query returned no results")
        
        if include_file:
            try:
                with open(include_file, 'r') as f:
                    include_data = json.load(f)
                    file_include_list = []
                    if isinstance(include_data, list):
                        file_include_list = include_data
                    else:
                        file_include_list = include_data.get('objects', [])
                
                # Combine with existing include_list if it exists from query_filter
                if include_list and query_filter:
                    # Find the intersection (only objects that are in both lists)
                    include_list = [obj for obj in include_list if obj in file_include_list]
                    logger.info(f"Combined query results with include file: {len(include_list)} objects remain after intersection")
                else:
                    # Otherwise, use file list directly
                    include_list = file_include_list
                    logger.info(f"Loaded {len(include_list)} objects to include from {include_file}")
            except Exception as e:
                logger.error(f"Error loading include file {include_file}: {e}")
                raise typer.Exit(1)
                
        if exclude_file:
            try:
                with open(exclude_file, 'r') as f:
                    exclude_data = json.load(f)
                    if isinstance(exclude_data, list):
                        exclude_list = exclude_data
                    else:
                        exclude_list = exclude_data.get('objects', [])
                logger.info(f"Loaded {len(exclude_list)} objects to exclude from {exclude_file}")
            except Exception as e:
                logger.error(f"Error loading exclude file {exclude_file}: {e}")
                raise typer.Exit(1)
        
        # Filter duplicates based on pattern, include, and exclude lists
        filtered_duplicates = {}
        for value_key, objects in duplicates.items():
            # Filter objects based on the pattern
            if pattern:
                # Check if any object in this group matches the pattern
                matches_pattern = False
                for name, _ in objects:
                    if pattern.lower() in name.lower() or pattern.lower() in value_key.lower():
                        matches_pattern = True
                        break
                        
                # Skip if no matches
                if not matches_pattern:
                    continue
            
            # Filter objects based on include/exclude lists
            if include_list:
                # Only keep objects explicitly included in the list
                filtered_objects = [(name, obj) for name, obj in objects if name in include_list]
                objects = filtered_objects
            
            if exclude_list:
                # Remove objects in the exclude list
                filtered_objects = [(name, obj) for name, obj in objects if name not in exclude_list]
                objects = filtered_objects
            
            # Apply minimum group size filter
            if len(objects) >= min_group_size:
                filtered_duplicates[value_key] = objects
        
        # Update duplicates with filtered list
        duplicates = filtered_duplicates
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found after applying filters")
            return
        
        # Log duplicate counts
        duplicate_sets = len(duplicates)
        duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
        logger.info(f"Found {duplicate_count} duplicate {object_type} objects across {duplicate_sets} unique values after filtering")
        
        # Log the duplicates found
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            logger.info(f"Found duplicates with value {value_key}: {', '.join(names)}")
        
        # Save to output file if provided
        if output:
            # Convert to serializable format
            result = {
                "summary": {
                    "object_type": object_type,
                    "duplicate_sets": duplicate_sets,
                    "duplicate_count": duplicate_count,
                    "filters": {
                        "pattern": pattern,
                        "min_group_size": min_group_size,
                        "include_count": len(include_list) if include_list else 0,
                        "exclude_count": len(exclude_list) if exclude_list else 0
                    }
                },
                "duplicates": {}
            }
            
            for value_key, objects in duplicates.items():
                result["duplicates"][value_key] = [name for name, _ in objects]
            
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Duplicate analysis saved to {output}")
            
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        raise typer.Exit(1)

@deduplicate_app.command("merge")
def deduplicate_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = typer.Option(
        ..., "--type", "-t", 
        help="Type of object to deduplicate (address, service, tag)",
        callback=object_type_callback
    ),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    strategy: str = typer.Option("first", "--strategy", "-s", help="Strategy for choosing primary object (first, shortest, longest, alphabetical)"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Pattern to filter objects (e.g. '10.0.0' for addresses)"),
    include_file: Optional[str] = typer.Option(None, "--include-file", help="JSON file with list of object names to include in deduplication"),
    exclude_file: Optional[str] = typer.Option(None, "--exclude-file", help="JSON file with list of object names to exclude from deduplication"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')"),
    dry_run: bool = ConfigOptions.dry_run(),
    impact_report: Optional[str] = typer.Option(None, "--impact-report", "-i", help="Generate a detailed impact report and save to this file"),
    version: Optional[str] = ConfigOptions.version(),
):
    """Find and merge duplicate objects"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Create deduplication engine
        engine = DeduplicationEngine(
            xml_config.tree, 
            device_type, 
            context, 
            xml_config.version, 
            **context_kwargs
        )
        
        # Find duplicates and references
        duplicates, references = engine.find_duplicates(object_type)
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found")
            return
        
        # Load include/exclude lists
        include_list = []
        exclude_list = []
        
        # Process query filter if provided
        if query_filter:
            logger.info(f"Processing graph query filter: {query_filter}")
            # Build graph from the configuration
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Create a query executor
            executor = QueryExecutor(graph)
            
            # Parse the query and ensure it has a RETURN clause
            query = Query(query_filter)
            if not query.has_return_clause():
                # Add a return clause based on object type
                node_type = object_type.rstrip('s')  # Strip trailing 's' if present
                query.add_return(f"a.name as name")
                logger.info(f"Added return clause to query: {query.query}")
            
            # Execute the query
            results = executor.execute(query.query)
            
            # Extract object names from results
            query_objects = []
            for result in results:
                if 'name' in result:
                    query_objects.append(result['name'])
                elif len(result) == 1:
                    # If there's only one field, use it
                    query_objects.append(list(result.values())[0])
            
            if query_objects:
                # Add query results to include list
                include_list = query_objects
                logger.info(f"Using query results for include list: {len(include_list)} objects")
            else:
                logger.info("Query returned no results")
        
        if include_file:
            try:
                with open(include_file, 'r') as f:
                    include_data = json.load(f)
                    file_include_list = []
                    if isinstance(include_data, list):
                        file_include_list = include_data
                    else:
                        file_include_list = include_data.get('objects', [])
                
                # Combine with existing include_list if it exists from query_filter
                if include_list and query_filter:
                    # Find the intersection (only objects that are in both lists)
                    include_list = [obj for obj in include_list if obj in file_include_list]
                    logger.info(f"Combined query results with include file: {len(include_list)} objects remain after intersection")
                else:
                    # Otherwise, use file list directly
                    include_list = file_include_list
                    logger.info(f"Loaded {len(include_list)} objects to include from {include_file}")
            except Exception as e:
                logger.error(f"Error loading include file {include_file}: {e}")
                raise typer.Exit(1)
                
        if exclude_file:
            try:
                with open(exclude_file, 'r') as f:
                    exclude_data = json.load(f)
                    if isinstance(exclude_data, list):
                        exclude_list = exclude_data
                    else:
                        exclude_list = exclude_data.get('objects', [])
                logger.info(f"Loaded {len(exclude_list)} objects to exclude from {exclude_file}")
            except Exception as e:
                logger.error(f"Error loading exclude file {exclude_file}: {e}")
                raise typer.Exit(1)
        
        # Filter duplicates based on pattern, include, and exclude lists
        filtered_duplicates = {}
        for value_key, objects in duplicates.items():
            # Filter objects based on the pattern
            if pattern:
                # Check if any object in this group matches the pattern
                matches_pattern = False
                for name, _ in objects:
                    if pattern.lower() in name.lower() or pattern.lower() in value_key.lower():
                        matches_pattern = True
                        break
                        
                # Skip if no matches
                if not matches_pattern:
                    continue
            
            # Filter objects based on include/exclude lists
            if include_list:
                # Only keep objects explicitly included in the list
                filtered_objects = [(name, obj) for name, obj in objects if name in include_list]
                # If we don't have at least 2 objects after filtering, skip this group
                if len(filtered_objects) < 2:
                    continue
                objects = filtered_objects
            
            if exclude_list:
                # Remove objects in the exclude list
                filtered_objects = [(name, obj) for name, obj in objects if name not in exclude_list]
                # If we don't have at least 2 objects after filtering, skip this group
                if len(filtered_objects) < 2:
                    continue
                objects = filtered_objects
            
            # Add to filtered duplicates if we have at least 2 objects
            if len(objects) >= 2:
                filtered_duplicates[value_key] = objects
        
        # Update duplicates with filtered list
        duplicates = filtered_duplicates
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found after applying filters")
            return
        
        # Log the duplicates found
        duplicate_sets = len(duplicates)
        duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
        logger.info(f"Found {duplicate_count} duplicate {object_type} objects across {duplicate_sets} unique values after filtering")
        
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            logger.info(f"Found duplicates with value {value_key}: {', '.join(names)}")
        
        # Merge duplicates (simulation)
        changes = engine.merge_duplicates(duplicates, references, strategy)
        
        # Log change summary
        delete_count = sum(1 for op, _, _ in changes if op == 'delete')
        ref_update_count = sum(1 for op, _, _ in changes if op == 'update_reference')
        logger.info(f"Changes to make: {delete_count} objects to delete, {ref_update_count} references to update")
        
        # Generate impact report if requested
        if impact_report:
            # Prepare impact analysis report
            impact_data = {
                "summary": {
                    "object_type": object_type,
                    "duplicate_sets": duplicate_sets,
                    "duplicate_count": duplicate_count,
                    "objects_to_delete": delete_count,
                    "references_to_update": ref_update_count,
                    "strategy": strategy,
                    "filters": {
                        "pattern": pattern,
                        "include_count": len(include_list) if include_list else 0,
                        "exclude_count": len(exclude_list) if exclude_list else 0
                    }
                },
                "duplicate_sets": {},
                "to_be_kept": [],
                "to_be_deleted": [],
                "reference_changes": [],
                "policy_impacts": {
                    "security": [],
                    "nat": []
                },
                "group_impacts": []
            }
            
            # Collect details on each duplicate set
            for value_key, objects in duplicates.items():
                object_names = [name for name, _ in objects]
                impact_data["duplicate_sets"][value_key] = object_names
                
                # Figure out which object will be kept based on strategy
                kept_name = None
                if strategy == "first":
                    kept_name = object_names[0]
                elif strategy == "shortest":
                    kept_name = min(object_names, key=len)
                elif strategy == "longest":
                    kept_name = max(object_names, key=len)
                elif strategy == "alphabetical":
                    kept_name = min(object_names)
                else:
                    kept_name = object_names[0]  # Default to first
                
                # Record kept object
                impact_data["to_be_kept"].append({
                    "name": kept_name,
                    "value": value_key
                })
                
                # Record objects to be deleted
                for name in object_names:
                    if name != kept_name:
                        impact_data["to_be_deleted"].append({
                            "name": name,
                            "replaced_by": kept_name,
                            "value": value_key
                        })
            
            # Analyze reference changes
            ref_by_policy = {}
            ref_by_group = {}
            
            for change_type, change_desc, element in changes:
                if change_type == 'update_reference':
                    # Extract information from change description
                    # Format is typically: "rulebase:name:field: oldval -> newval"
                    parts = change_desc.split(':')
                    if len(parts) >= 2:
                        ref_type = parts[0]
                        ref_name = parts[1]
                        
                        # Format details based on reference type
                        if 'security' in ref_type or 'nat' in ref_type:
                            # This is a policy reference
                            policy_type = 'security' if 'security' in ref_type else 'nat'
                            field = parts[2] if len(parts) > 2 else 'unknown'
                            old_new = parts[-1].split(' -> ')
                            old_val = old_new[0].strip() if len(old_new) > 0 else ''
                            new_val = old_new[1].strip() if len(old_new) > 1 else ''
                            
                            # Create impact entry
                            impact_entry = {
                                "policy_name": ref_name,
                                "policy_type": policy_type,
                                "field": field,
                                "old_value": old_val,
                                "new_value": new_val
                            }
                            
                            if ref_name not in ref_by_policy:
                                ref_by_policy[ref_name] = []
                            ref_by_policy[ref_name].append(impact_entry)
                            
                            impact_data["policy_impacts"][policy_type].append(impact_entry)
                            
                        elif 'group' in ref_type:
                            # This is a group reference
                            group_type = ref_type
                            old_new = parts[-1].split(' -> ')
                            old_val = old_new[0].strip() if len(old_new) > 0 else ''
                            new_val = old_new[1].strip() if len(old_new) > 1 else ''
                            
                            # Create impact entry
                            impact_entry = {
                                "group_name": ref_name,
                                "group_type": group_type,
                                "old_member": old_val,
                                "new_member": new_val
                            }
                            
                            if ref_name not in ref_by_group:
                                ref_by_group[ref_name] = []
                            ref_by_group[ref_name].append(impact_entry)
                            
                            impact_data["group_impacts"].append(impact_entry)
                        
                        # Add to general reference changes
                        impact_data["reference_changes"].append({
                            "type": ref_type,
                            "name": ref_name,
                            "details": change_desc
                        })
            
            # Save impact report
            with open(impact_report, 'w') as f:
                json.dump(impact_data, f, indent=2)
            logger.info(f"Impact analysis report saved to {impact_report}")
        
        # If dry run, stop here
        if dry_run:
            logger.info("Dry run - no changes made")
            return
        
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

@deduplicate_app.command("simulate")
def simulate_deduplication(
    config: str = ConfigOptions.config_file(),
    object_type: str = typer.Option(
        ..., "--type", "-t", 
        help="Type of object to deduplicate (address, service, tag)",
        callback=object_type_callback
    ),
    output: str = typer.Option(..., "--output", "-o", help="Output file for impact report (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    strategy: str = typer.Option("first", "--strategy", "-s", help="Strategy for choosing primary object (first, shortest, longest, alphabetical)"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Pattern to filter objects (e.g. '10.0.0' for addresses)"),
    include_file: Optional[str] = typer.Option(None, "--include-file", help="JSON file with list of object names to include in deduplication"),
    exclude_file: Optional[str] = typer.Option(None, "--exclude-file", help="JSON file with list of object names to exclude from deduplication"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Include detailed policy and reference information"),
    version: Optional[str] = ConfigOptions.version(),
):
    """Simulate deduplication and generate impact analysis without making changes"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Create deduplication engine
        engine = DeduplicationEngine(
            xml_config.tree, 
            device_type, 
            context, 
            xml_config.version, 
            **context_kwargs
        )
        
        # Find duplicates and references
        duplicates, references = engine.find_duplicates(object_type)
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found")
            return
        
        # Load include/exclude lists
        include_list = []
        exclude_list = []
        
        # Process query filter if provided
        if query_filter:
            logger.info(f"Processing graph query filter: {query_filter}")
            # Build graph from the configuration
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Create a query executor
            executor = QueryExecutor(graph)
            
            # Parse the query and ensure it has a RETURN clause
            query = Query(query_filter)
            if not query.has_return_clause():
                # Add a return clause based on object type
                node_type = object_type.rstrip('s')  # Strip trailing 's' if present
                query.add_return(f"a.name as name")
                logger.info(f"Added return clause to query: {query.query}")
            
            # Execute the query
            results = executor.execute(query.query)
            
            # Extract object names from results
            query_objects = []
            for result in results:
                if 'name' in result:
                    query_objects.append(result['name'])
                elif len(result) == 1:
                    # If there's only one field, use it
                    query_objects.append(list(result.values())[0])
            
            if query_objects:
                # Add query results to include list
                include_list = query_objects
                logger.info(f"Using query results for include list: {len(include_list)} objects")
            else:
                logger.info("Query returned no results")
        
        if include_file:
            try:
                with open(include_file, 'r') as f:
                    include_data = json.load(f)
                    file_include_list = []
                    if isinstance(include_data, list):
                        file_include_list = include_data
                    else:
                        file_include_list = include_data.get('objects', [])
                
                # Combine with existing include_list if it exists from query_filter
                if include_list and query_filter:
                    # Find the intersection (only objects that are in both lists)
                    include_list = [obj for obj in include_list if obj in file_include_list]
                    logger.info(f"Combined query results with include file: {len(include_list)} objects remain after intersection")
                else:
                    # Otherwise, use file list directly
                    include_list = file_include_list
                    logger.info(f"Loaded {len(include_list)} objects to include from {include_file}")
            except Exception as e:
                logger.error(f"Error loading include file {include_file}: {e}")
                raise typer.Exit(1)
                
        if exclude_file:
            try:
                with open(exclude_file, 'r') as f:
                    exclude_data = json.load(f)
                    if isinstance(exclude_data, list):
                        exclude_list = exclude_data
                    else:
                        exclude_list = exclude_data.get('objects', [])
                logger.info(f"Loaded {len(exclude_list)} objects to exclude from {exclude_file}")
            except Exception as e:
                logger.error(f"Error loading exclude file {exclude_file}: {e}")
                raise typer.Exit(1)
        
        # Filter duplicates based on pattern, include, and exclude lists
        filtered_duplicates = {}
        for value_key, objects in duplicates.items():
            # Filter objects based on the pattern
            if pattern:
                # Check if any object in this group matches the pattern
                matches_pattern = False
                for name, _ in objects:
                    if pattern.lower() in name.lower() or pattern.lower() in value_key.lower():
                        matches_pattern = True
                        break
                        
                # Skip if no matches
                if not matches_pattern:
                    continue
            
            # Filter objects based on include/exclude lists
            if include_list:
                # Only keep objects explicitly included in the list
                filtered_objects = [(name, obj) for name, obj in objects if name in include_list]
                # If we don't have at least 2 objects after filtering, skip this group
                if len(filtered_objects) < 2:
                    continue
                objects = filtered_objects
            
            if exclude_list:
                # Remove objects in the exclude list
                filtered_objects = [(name, obj) for name, obj in objects if name not in exclude_list]
                # If we don't have at least 2 objects after filtering, skip this group
                if len(filtered_objects) < 2:
                    continue
                objects = filtered_objects
            
            # Add to filtered duplicates if we have at least 2 objects
            if len(objects) >= 2:
                filtered_duplicates[value_key] = objects
        
        # Update duplicates with filtered list
        duplicates = filtered_duplicates
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found after applying filters")
            return
        
        # Log the duplicates found
        duplicate_sets = len(duplicates)
        duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
        logger.info(f"Found {duplicate_count} duplicate {object_type} objects across {duplicate_sets} unique values after filtering")
        
        # Merge duplicates (simulation)
        changes = engine.merge_duplicates(duplicates, references, strategy)
        
        # Log change summary
        delete_count = sum(1 for op, _, _ in changes if op == 'delete')
        ref_update_count = sum(1 for op, _, _ in changes if op == 'update_reference')
        logger.info(f"Simulation summary: {delete_count} objects would be deleted, {ref_update_count} references would be updated")
        
        # Prepare impact analysis report
        impact_data = {
            "summary": {
                "object_type": object_type,
                "duplicate_sets": duplicate_sets,
                "duplicate_count": duplicate_count,
                "objects_to_delete": delete_count,
                "references_to_update": ref_update_count,
                "strategy": strategy,
                "filters": {
                    "pattern": pattern,
                    "include_count": len(include_list) if include_list else 0,
                    "exclude_count": len(exclude_list) if exclude_list else 0
                }
            },
            "duplicate_sets": {},
            "to_be_kept": [],
            "to_be_deleted": []
        }
        
        # Add detailed information if requested
        if detailed:
            impact_data["reference_changes"] = []
            impact_data["policy_impacts"] = {
                "security": [],
                "nat": []
            }
            impact_data["group_impacts"] = []
        
        # Collect details on each duplicate set
        for value_key, objects in duplicates.items():
            object_names = [name for name, _ in objects]
            impact_data["duplicate_sets"][value_key] = object_names
            
            # Figure out which object will be kept based on strategy
            kept_name = None
            if strategy == "first":
                kept_name = object_names[0]
            elif strategy == "shortest":
                kept_name = min(object_names, key=len)
            elif strategy == "longest":
                kept_name = max(object_names, key=len)
            elif strategy == "alphabetical":
                kept_name = min(object_names)
            else:
                kept_name = object_names[0]  # Default to first
            
            # Record kept object
            impact_data["to_be_kept"].append({
                "name": kept_name,
                "value": value_key
            })
            
            # Record objects to be deleted
            for name in object_names:
                if name != kept_name:
                    impact_data["to_be_deleted"].append({
                        "name": name,
                        "replaced_by": kept_name,
                        "value": value_key
                    })
        
        # Add detailed analysis if requested
        if detailed:
            ref_by_policy = {}
            ref_by_group = {}
            
            for change_type, change_desc, element in changes:
                if change_type == 'update_reference':
                    # Extract information from change description
                    # Format is typically: "rulebase:name:field: oldval -> newval"
                    parts = change_desc.split(':')
                    if len(parts) >= 2:
                        ref_type = parts[0]
                        ref_name = parts[1]
                        
                        # Format details based on reference type
                        if 'security' in ref_type or 'nat' in ref_type:
                            # This is a policy reference
                            policy_type = 'security' if 'security' in ref_type else 'nat'
                            field = parts[2] if len(parts) > 2 else 'unknown'
                            old_new = parts[-1].split(' -> ')
                            old_val = old_new[0].strip() if len(old_new) > 0 else ''
                            new_val = old_new[1].strip() if len(old_new) > 1 else ''
                            
                            # Create impact entry
                            impact_entry = {
                                "policy_name": ref_name,
                                "policy_type": policy_type,
                                "field": field,
                                "old_value": old_val,
                                "new_value": new_val
                            }
                            
                            if ref_name not in ref_by_policy:
                                ref_by_policy[ref_name] = []
                            ref_by_policy[ref_name].append(impact_entry)
                            
                            impact_data["policy_impacts"][policy_type].append(impact_entry)
                            
                        elif 'group' in ref_type:
                            # This is a group reference
                            group_type = ref_type
                            old_new = parts[-1].split(' -> ')
                            old_val = old_new[0].strip() if len(old_new) > 0 else ''
                            new_val = old_new[1].strip() if len(old_new) > 1 else ''
                            
                            # Create impact entry
                            impact_entry = {
                                "group_name": ref_name,
                                "group_type": group_type,
                                "old_member": old_val,
                                "new_member": new_val
                            }
                            
                            if ref_name not in ref_by_group:
                                ref_by_group[ref_name] = []
                            ref_by_group[ref_name].append(impact_entry)
                            
                            impact_data["group_impacts"].append(impact_entry)
                        
                        # Add to general reference changes
                        impact_data["reference_changes"].append({
                            "type": ref_type,
                            "name": ref_name,
                            "details": change_desc
                        })
        
        # Save impact report
        with open(output, 'w') as f:
            json.dump(impact_data, f, indent=2)
        logger.info(f"Simulation and impact analysis saved to {output}")
        
        # Print summary
        logger.info(f"Deduplication would result in:")
        logger.info(f"  - {delete_count} objects deleted")
        logger.info(f"  - {ref_update_count} references updated")
        if detailed:
            policy_count = len(set(entry["policy_name"] for entry in impact_data["policy_impacts"]["security"] + impact_data["policy_impacts"]["nat"]))
            group_count = len(set(entry["group_name"] for entry in impact_data["group_impacts"]))
            logger.info(f"  - {policy_count} policies affected")
            logger.info(f"  - {group_count} groups affected")
        
    except Exception as e:
        logger.error(f"Error in deduplication simulation: {e}")
        raise typer.Exit(1)

@deduplicate_app.command("report")
def generate_deduplication_report(
    config: str = ConfigOptions.config_file(),
    output: str = typer.Option(..., "--output", "-o", help="Output file for report (JSON format)"),
    object_types: Optional[List[str]] = typer.Option(
        None, "--types", "-t",
        help="Types of objects to analyze (address, service, tag). If not specified, all types are analyzed."
    ),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select objects to include in the report"),
    version: Optional[str] = ConfigOptions.version(),
):
    """Generate a comprehensive deduplication report for the configuration"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Create deduplication engine
        engine = DeduplicationEngine(
            xml_config.tree, 
            device_type, 
            context, 
            xml_config.version, 
            **context_kwargs
        )
        
        # Process query filter if provided to get object names to include
        query_objects_by_type = {}
        if query_filter:
            logger.info(f"Processing graph query filter: {query_filter}")
            # Build graph from the configuration
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Create a query executor
            executor = QueryExecutor(graph)
            
            # Parse the query
            query = Query(query_filter)
            if not query.has_return_clause():
                # Add a general return clause for objects
                query.add_return("a.name as name, labels(a) as types")
                logger.info(f"Added return clause to query: {query.query}")
            
            # Execute the query
            results = executor.execute(query.query)
            
            # Extract object names from results and organize by type
            for result in results:
                obj_name = None
                obj_type = None
                
                # Try to get the name
                if 'name' in result:
                    obj_name = result['name']
                elif len(result) == 1:
                    # If there's only one field, use it as the name
                    obj_name = list(result.values())[0]
                
                # Try to determine object type
                if 'types' in result and result['types']:
                    # Convert from label to type (e.g., 'address' from 'address')
                    for label in result['types']:
                        if label.lower() in SUPPORTED_OBJECT_TYPES:
                            obj_type = label.lower()
                            break
                
                # If we have a name but no determined type, we'll apply this object to all types
                if obj_name and not obj_type:
                    for t in SUPPORTED_OBJECT_TYPES:
                        if t not in query_objects_by_type:
                            query_objects_by_type[t] = []
                        query_objects_by_type[t].append(obj_name)
                elif obj_name and obj_type:
                    if obj_type not in query_objects_by_type:
                        query_objects_by_type[obj_type] = []
                    query_objects_by_type[obj_type].append(obj_name)
            
            if any(query_objects_by_type.values()):
                logger.info(f"Query returned objects for filtering: {', '.join([f'{t}: {len(objs)}' for t, objs in query_objects_by_type.items() if objs])}")
            else:
                logger.info("Query returned no results for filtering")
        
        # If no object types specified, use all supported types
        if not object_types:
            object_types = SUPPORTED_OBJECT_TYPES
        else:
            # Validate object types
            for obj_type in object_types:
                if obj_type.lower() not in SUPPORTED_OBJECT_TYPES and obj_type.lower() not in [f"{t}s" for t in SUPPORTED_OBJECT_TYPES]:
                    supported_str = ", ".join(SUPPORTED_OBJECT_TYPES)
                    logger.error(f"Object type '{obj_type}' not supported. Supported types: {supported_str}")
                    raise typer.Exit(1)
        
        # Initialize report
        report = {
            "summary": {
                "total_duplicate_sets": 0,
                "total_duplicate_objects": 0,
                "query_filter": query_filter if query_filter else None,
                "query_filtered": True if query_filter else False
            },
            "object_types": {}
        }
        
        # Analyze each object type
        for obj_type in object_types:
            logger.info(f"Analyzing {obj_type} objects for duplicates")
            
            # Find duplicates and references
            duplicates, references = engine.find_duplicates(obj_type)
            
            # Filter duplicates based on query results if available
            if query_filter and obj_type in query_objects_by_type and query_objects_by_type[obj_type]:
                filtered_duplicates = {}
                query_object_names = set(query_objects_by_type[obj_type])
                
                for value_key, objects in duplicates.items():
                    # Keep only objects that match the query
                    filtered_objects = [(name, obj) for name, obj in objects if name in query_object_names]
                    
                    # Only include groups with at least 2 objects
                    if len(filtered_objects) >= 2:
                        filtered_duplicates[value_key] = filtered_objects
                
                if filtered_duplicates:
                    logger.info(f"Filtered {obj_type} duplicates using query results: {len(duplicates)} groups → {len(filtered_duplicates)} groups")
                    duplicates = filtered_duplicates
                else:
                    logger.info(f"No {obj_type} duplicates match the query filter")
            
            # Calculate statistics
            duplicate_sets = len(duplicates)
            duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
            
            # Update totals
            report["summary"]["total_duplicate_sets"] += duplicate_sets
            report["summary"]["total_duplicate_objects"] += duplicate_count
            
            # Add to report
            report["object_types"][obj_type] = {
                "duplicate_sets": duplicate_sets,
                "duplicate_count": duplicate_count,
                "query_filtered": True if query_filter and obj_type in query_objects_by_type and query_objects_by_type[obj_type] else False,
                "query_matched_objects": len(query_objects_by_type.get(obj_type, [])) if query_filter else 0,
                "duplicates": {}
            }
            
            # Log the duplicates found
            if duplicate_count > 0:
                logger.info(f"Found {duplicate_count} duplicate {obj_type} objects across {duplicate_sets} unique values")
                
                # Add details to report
                for value_key, objects in duplicates.items():
                    names = [name for name, _ in objects]
                    report["object_types"][obj_type]["duplicates"][value_key] = names
                    logger.debug(f"Found duplicates with value {value_key}: {', '.join(names)}")
            else:
                logger.info(f"No duplicate {obj_type} objects found")
        
        # Save report to file
        with open(output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Deduplication report saved to {output}")
        
        # Print summary
        if query_filter:
            logger.info(f"Summary: Found {report['summary']['total_duplicate_objects']} duplicate objects across {report['summary']['total_duplicate_sets']} unique values (filtered by query)")
        else:
            logger.info(f"Summary: Found {report['summary']['total_duplicate_objects']} duplicate objects across {report['summary']['total_duplicate_sets']} unique values")
            
        for obj_type, data in report["object_types"].items():
            if data["duplicate_count"] > 0:
                if data["query_filtered"]:
                    logger.info(f"  - {obj_type}: {data['duplicate_count']} duplicate objects in {data['duplicate_sets']} sets (filtered from {data['query_matched_objects']} query matches)")
                else:
                    logger.info(f"  - {obj_type}: {data['duplicate_count']} duplicate objects in {data['duplicate_sets']} sets")
            
    except Exception as e:
        logger.error(f"Error generating deduplication report: {e}")
        raise typer.Exit(1)