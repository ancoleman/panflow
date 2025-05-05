"""
Policy commands for PANFlow CLI.

This module provides commands for managing PAN-OS policies.
"""

import json
import logging
import typer
from typing import Optional, Dict, Any

from panflow.core.bulk_operations import ConfigUpdater
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor

from ..app import policy_app
from ..common import common_options, ConfigOptions

# Get logger
logger = logging.getLogger("panflow")

@policy_app.command("list")
@common_options
def list_policies(
    policy_type: str = typer.Option(
        ..., "--type", "-t",
        help="Policy type (security, nat, qos, etc.)"
    ),
    context: str = typer.Option(
        "shared", "--context", "-c",
        help="Context (shared, device-group, vsys)"
    ),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg",
        help="Device group name (required for device-group context)"
    ),
    vsys: Optional[str] = typer.Option(
        "vsys1", "--vsys", "-v",
        help="VSYS name (required for vsys context)"
    ),
    config_file: str = typer.Option(
        ..., "--config", "-f",
        help="Path to configuration file"
    )
):
    """
    List policies of a specific type.
    """
    logger.info(f"Listing {policy_type} policies in {context}")
    
    # TODO: Implement policy listing functionality
    typer.echo("Policy listing not yet implemented")
    
@policy_app.command("bulk-update")
def bulk_update_policies(
    config_file: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to update"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    operations_file: str = typer.Option(..., "--operations", help="JSON file with update operations"),
    query_filter: Optional[str] = typer.Option(None, "--query-filter", "-q", help="Graph query filter to select policies (e.g., 'MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.name == \"any\"')"),
    output_file: str = ConfigOptions.output_file(),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", "--dg", help="Device group name"),
    vsys: str = typer.Option("vsys1", "--vsys", "-v", help="VSYS name"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
    dry_run: bool = ConfigOptions.dry_run()
):
    """
    Bulk update policies matching criteria or query filter with specified operations.
    
    You can select policies using either a criteria file or a graph query filter.
    If both are provided, the policies matching either will be updated.
    
    Examples:
    
        # Update policies matching criteria in a JSON file
        python cli.py policy bulk-update --config config.xml --type security_rules --criteria criteria.json --operations operations.json
        
        # Update policies matching a graph query
        python cli.py policy bulk-update --config config.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.dst_port == '3389'" --operations operations.json
        
        # Perform a dry run to see what would be updated without making changes
        python cli.py policy bulk-update --config config.xml --type security_rules --criteria criteria.json --operations operations.json --dry-run
    """
    try:
        # Load the configuration
        tree, detected_version = load_config_from_file(config_file)
        version = version or detected_version
        device_type = device_type or detect_device_type(tree)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
            
        # Create the updater
        updater = ConfigUpdater(tree, device_type, context, version, **context_kwargs)
        
        # Load criteria if specified
        criteria = None
        if criteria_file:
            with open(criteria_file, 'r') as f:
                criteria = json.load(f)
            logger.info(f"Loaded criteria from {criteria_file}: {criteria}")
        
        # Process query filter if specified
        matching_policies_from_query = []
        if query_filter:
            logger.info(f"Using graph query filter: {query_filter}")
            
            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(tree)
            
            # Prepare a query that returns policy names
            # If the query doesn't already have a RETURN clause, append one that returns rule names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN r.name"
            else:
                query_text = query_filter
            
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            
            # Extract policy names from the results
            for row in results:
                if 'r.name' in row:
                    matching_policies_from_query.append(row['r.name'])
            
            logger.info(f"Query matched {len(matching_policies_from_query)} policies")
            
            # If no criteria was provided, create one based on the query results
            if not criteria and matching_policies_from_query:
                criteria = {"name": matching_policies_from_query}
            # If criteria was provided, extend it with query results
            elif criteria and matching_policies_from_query:
                # If criteria already has a 'name' field, append to it
                if 'name' in criteria:
                    if isinstance(criteria['name'], list):
                        criteria['name'].extend(matching_policies_from_query)
                    else:
                        criteria['name'] = [criteria['name']] + matching_policies_from_query
                # Otherwise, add a new 'name' field
                else:
                    criteria['name'] = matching_policies_from_query
        
        # If no selection method was provided, stop
        if not criteria:
            logger.error("No selection criteria or query filter provided")
            raise typer.Exit(1)
            
        # Load operations
        with open(operations_file, 'r') as f:
            operations = json.load(f)
        logger.info(f"Loaded operations from {operations_file}: {operations}")
        
        # Perform update
        if dry_run:
            logger.info("Dry run mode: Changes will not be applied")
            
            # Select matching policies to show what would be updated
            policies = updater.query.select_policies(policy_type, criteria)
            logger.info(f"Would update {len(policies)} policies")
            for policy in policies:
                logger.info(f"  - Would update policy: {policy.get('name', 'unknown')}")
                
            logger.info(f"Would apply these operations: {operations}")
        else:
            # Perform the bulk update
            updated_count = updater.bulk_update_policies(policy_type, criteria, operations)
            
            if updated_count > 0:
                logger.info(f"Successfully updated {updated_count} policies")
                
                # Save the updated configuration
                if save_config(tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.warning("No policies were updated")
    
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise typer.Exit(1)