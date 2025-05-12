"""
Policy commands for PANFlow CLI.

This module provides commands for managing PAN-OS policies.
"""

import json
import logging
import typer
import re
from typing import Optional, Dict, Any, Tuple

from panflow.core.bulk_operations import ConfigUpdater
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor

from ..app import policy_app
from ..common import common_options, ConfigOptions


def create_query_for_action(action: str) -> str:
    """
    Create a simple query for filtering policies by action.

    Args:
        action: The action value (allow, deny, etc.)

    Returns:
        A query string that matches policies by action
    """
    return f"MATCH (r:security_rule) WHERE r.action == '{action}' RETURN r.name"


def create_query_for_log_setting(setting: str, value: str) -> str:
    """
    Create a simple query for filtering policies by log settings.

    Args:
        setting: The log setting (log_start, log_end)
        value: The value (yes, no)

    Returns:
        A query string that matches policies by log setting
    """
    return f"MATCH (r:security_rule) WHERE r.{setting} == '{value}' RETURN r.name"


def execute_policy_query(graph, query_text):
    """
    Execute a policy query with fallback to simple queries if needed.

    Args:
        graph: The graph to query
        query_text: The query text to execute

    Returns:
        List of query results or empty list if the query fails
    """
    try:
        # Try the original query
        query = Query(query_text)
        executor = QueryExecutor(graph)
        return executor.execute(query)
    except Exception as query_error:
        logger.warning(f"Query failed: {query_error}. Trying basic query.")

        # Try basic query for all security rules
        basic_query = "MATCH (r:security_rule) RETURN r.name"
        try:
            query = Query(basic_query)
            return executor.execute(query)
        except Exception as e:
            logger.error(f"Basic query also failed: {e}")
            return []


# Get logger
logger = logging.getLogger("panflow")


@policy_app.command("list")
@common_options
def list_policies(
    policy_type: str = typer.Option(
        ..., "--type", "-t", help="Policy type (security, nat, qos, etc.)"
    ),
    context: str = typer.Option("shared", "--context", help="Context (shared, device-group, vsys)"),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg", help="Device group name (required for device-group context)"
    ),
    vsys: Optional[str] = typer.Option(
        "vsys1", "--vsys", "-v", help="VSYS name (required for vsys context)"
    ),
    config_file: str = ConfigOptions.config_file(),
    query_filter: Optional[str] = typer.Option(
        None,
        "--query-filter",
        "-q",
        help="Graph query filter to select policies (e.g., 'MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.name == \"any\"')",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for results (JSON format)"
    ),
):
    """
    List policies of a specific type with optional graph query filtering.

    Examples:

        # List all security policies
        python cli.py policy list --config config.xml --type security_rules

        # List policies that use HTTP service
        python cli.py policy list --config config.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http'"

        # List policies using a specific source address and save to file
        python cli.py policy list --config config.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.name == 'web-server'" --output web_server_policies.json
    """
    try:
        # Load the configuration
        tree, detected_version = load_config_from_file(config_file)
        device_type = detect_device_type(tree)

        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys

        # Create the updater to use its query capabilities
        updater = ConfigUpdater(tree, device_type, context, detected_version, **context_kwargs)

        # Get policies of the specified type
        logger.info(f"Getting {policy_type} policies...")
        try:
            # Use higher-level function instead of the buggy bulk_operations implementation
            from panflow.modules.policies import get_policies

            # Create a custom wrapper that suppresses logging
            def get_policies_no_logging(*args, **kwargs):
                import logging

                # Temporarily raise the logging level to suppress info messages
                current_level = logging.getLogger("panflow").level
                logging.getLogger("panflow").setLevel(logging.WARNING)
                try:
                    result = get_policies(*args, **kwargs)
                    return result
                finally:
                    # Restore the original logging level
                    logging.getLogger("panflow").setLevel(current_level)

            # Get the policies using the more reliable function with logging suppressed
            policy_dict = get_policies_no_logging(
                tree, policy_type, device_type, context, detected_version, **context_kwargs
            )

            # Convert to the format expected by the rest of the function
            all_policies = []
            for name, properties in policy_dict.items():
                policy = {"name": name}
                policy.update(properties)
                all_policies.append(policy)

        except Exception as e:
            logger.error(f"Error getting policies: {e}")
            raise typer.Exit(1)

        if query_filter:
            logger.info(f"Filtering policies using query: {query_filter}")

            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(tree)

            # Prepare a query that returns policy names
            # If the query doesn't already have a RETURN clause, append one that returns rule names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN r.name"
            else:
                query_text = query_filter

            # Check for common query patterns and use appropriate specialized queries
            if "r.action" in query_text:
                # Extract action value
                match = re.search(r"r\.action\s*==\s*['\"]([^'\"]+)['\"]", query_text)
                if match:
                    action_value = match.group(1)
                    query_text = create_query_for_action(action_value)
                    logger.info(f"Using simplified action query: {query_text}")
            elif "r.log_" in query_text:
                # Extract log setting details
                match = re.search(r"r\.(log_\w+)\s*==\s*['\"]([^'\"]+)['\"]", query_text)
                if match:
                    log_setting = match.group(1)
                    log_value = match.group(2)
                    query_text = create_query_for_log_setting(log_setting, log_value)
                    logger.info(f"Using simplified log query: {query_text}")

            # Execute the query with fallback
            results = execute_policy_query(graph, query_text)

            # Extract policy names from the results
            matching_policies = []
            for row in results:
                if "r.name" in row:
                    matching_policies.append(row["r.name"])
                elif len(row) == 1:  # If there's only one column, use its value
                    matching_policies.append(list(row.values())[0])

            logger.info(f"Query matched {len(matching_policies)} policies")

            # Filter policies to only keep those matching the query
            filtered_policies = []
            for policy in all_policies:
                if policy.get("name") in matching_policies:
                    filtered_policies.append(policy)

            all_policies = filtered_policies

        # Display policy names with details using common formatting
        from ..common import format_policies_list

        formatted_lines = format_policies_list(
            all_policies, include_header=True, policy_type=policy_type
        )
        for line in formatted_lines:
            logger.info(line)

        # Save to output file if requested
        if output:
            # Convert policies to dict with names as keys
            policy_dict = {p.get("name", f"policy_{i}"): p for i, p in enumerate(all_policies)}
            with open(output, "w") as f:
                json.dump(policy_dict, f, indent=2)
            logger.info(f"Saved {len(all_policies)} policies to {output}")

    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise typer.Exit(1)


@policy_app.command("filter")
def filter_policies(
    config_file: str = ConfigOptions.config_file(),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to filter"),
    criteria_file: Optional[str] = typer.Option(
        None, "--criteria", help="JSON file with filter criteria"
    ),
    query_filter: Optional[str] = typer.Option(
        None,
        "--query-filter",
        "-q",
        help="Graph query filter to select policies (e.g., 'MATCH (r:security_rule) WHERE r.action == \"allow\"')",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for results (JSON format)"
    ),
    device_type: str = typer.Option(
        "firewall", "--device-type", "-d", help="Device type (firewall or panorama)"
    ),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg", help="Device group name"
    ),
    vsys: str = typer.Option("vsys1", "--vsys", "-v", help="VSYS name"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
):
    """
    Filter policies based on criteria or graph query.

    Examples:

        # Filter policies using criteria file
        python cli.py policy filter --config config.xml --type security_rules --criteria criteria.json

        # Filter policies using graph query
        python cli.py policy filter --config config.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http'"

        # Combine criteria and query filter
        python cli.py policy filter --config config.xml --type security_rules --criteria criteria.json --query-filter "MATCH (r:security-rule) WHERE r.action == 'allow'"
    """
    try:
        # Ensure at least one filter method is specified
        if not criteria_file and not query_filter:
            logger.error("You must specify either --criteria or --query-filter")
            raise typer.Exit(1)

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

        # Create the updater to use its query capabilities
        updater = ConfigUpdater(tree, device_type, context, version, **context_kwargs)

        # Get all policies of the specified type
        from panflow.modules.policies import get_policies

        # Create a custom wrapper that suppresses logging
        def get_policies_no_logging(*args, **kwargs):
            import logging

            # Temporarily raise the logging level to suppress info messages
            current_level = logging.getLogger("panflow").level
            logging.getLogger("panflow").setLevel(logging.WARNING)
            try:
                result = get_policies(*args, **kwargs)
                return result
            finally:
                # Restore the original logging level
                logging.getLogger("panflow").setLevel(current_level)

        # Get the policies using the more reliable function with logging suppressed
        policy_dict = get_policies_no_logging(
            tree, policy_type, device_type, context, version, **context_kwargs
        )

        # Convert to the format expected by the rest of the function
        all_policies = []
        for name, properties in policy_dict.items():
            policy = {"name": name}
            policy.update(properties)
            all_policies.append(policy)

        logger.info(f"Found {len(all_policies)} {policy_type} policies total")

        # Apply criteria filter if specified
        filtered_policies = all_policies
        if criteria_file:
            # Read criteria from file
            with open(criteria_file, "r") as f:
                criteria = json.load(f)
            logger.info(f"Loaded criteria from {criteria_file}")

            # Apply criteria
            filtered_policies = updater.query.select_policies(policy_type, criteria)
            logger.info(f"Criteria matched {len(filtered_policies)} policies")

        # Apply graph query filter if specified
        if query_filter:
            logger.info(f"Filtering policies using query: {query_filter}")

            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(tree)

            # Prepare a query that returns policy names
            # If the query doesn't already have a RETURN clause, append one that returns rule names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN r.name"
            else:
                query_text = query_filter

            # Check for common query patterns and use appropriate specialized queries
            if "r.action" in query_text:
                # Extract action value
                match = re.search(r"r\.action\s*==\s*['\"]([^'\"]+)['\"]", query_text)
                if match:
                    action_value = match.group(1)
                    query_text = create_query_for_action(action_value)
                    logger.info(f"Using simplified action query: {query_text}")
            elif "r.log_" in query_text:
                # Extract log setting details
                match = re.search(r"r\.(log_\w+)\s*==\s*['\"]([^'\"]+)['\"]", query_text)
                if match:
                    log_setting = match.group(1)
                    log_value = match.group(2)
                    query_text = create_query_for_log_setting(log_setting, log_value)
                    logger.info(f"Using simplified log query: {query_text}")

            # Execute the query with fallback
            results = execute_policy_query(graph, query_text)

            # Extract policy names from the results
            matching_policies = []
            for row in results:
                if "r.name" in row:
                    matching_policies.append(row["r.name"])
                elif len(row) == 1:  # If there's only one column, use its value
                    matching_policies.append(list(row.values())[0])

            logger.info(f"Query matched {len(matching_policies)} policies")

            # Filter policies to only keep those matching the query
            if criteria_file:
                # Further filter the already filtered policies
                query_filtered = []
                for policy in filtered_policies:
                    if policy.get("name") in matching_policies:
                        query_filtered.append(policy)
                filtered_policies = query_filtered
                logger.info(f"Combined filters matched {len(filtered_policies)} policies")
            else:
                # Filter all policies by the query results
                query_filtered = []
                for policy in all_policies:
                    if policy.get("name") in matching_policies:
                        query_filtered.append(policy)
                filtered_policies = query_filtered

        # Display filtered policies with details using common formatting
        from ..common import format_policies_list

        formatted_lines = format_policies_list(
            filtered_policies,
            include_header=True,
            policy_type=policy_type,
            count=len(filtered_policies),
        )
        for line in formatted_lines:
            # Replace the first line to include "Final result:"
            if line.startswith("Found"):
                logger.info(f"Final result: {len(filtered_policies)} {policy_type} policies:")
            else:
                logger.info(line)

        # Save to output file if requested
        if output and filtered_policies:
            # Convert policies to dict with names as keys
            policy_dict = {p.get("name", f"policy_{i}"): p for i, p in enumerate(filtered_policies)}
            with open(output, "w") as f:
                json.dump(policy_dict, f, indent=2)
            logger.info(f"Saved {len(filtered_policies)} policies to {output}")

    except Exception as e:
        logger.error(f"Error filtering policies: {e}")
        raise typer.Exit(1)


@policy_app.command("bulk-update")
def bulk_update_policies(
    config_file: str = ConfigOptions.config_file(),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to update"),
    criteria_file: Optional[str] = typer.Option(
        None, "--criteria", help="JSON file with filter criteria"
    ),
    operations_file: str = typer.Option(
        ..., "--operations", help="JSON file with update operations"
    ),
    query_filter: Optional[str] = typer.Option(
        None,
        "--query-filter",
        "-q",
        help="Graph query filter to select policies (e.g., 'MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.name == \"any\"')",
    ),
    output_file: str = ConfigOptions.output_file(),
    device_type: str = typer.Option(
        "firewall", "--device-type", "-d", help="Device type (firewall or panorama)"
    ),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg", help="Device group name"
    ),
    vsys: str = typer.Option("vsys1", "--vsys", "-v", help="VSYS name"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
    dry_run: bool = ConfigOptions.dry_run(),
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
            with open(criteria_file, "r") as f:
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

            # Try to execute the original query
            try:
                query = Query(query_text)
                executor = QueryExecutor(graph)
                results = executor.execute(query)
            except Exception as query_error:
                # If the query fails, try with a simplified query
                logger.warning(f"Original query failed: {query_error}. Trying simplified query.")
                simplified_query, conditions = simplify_query(query_text)

                # Execute the simplified query
                query = Query(simplified_query)
                executor = QueryExecutor(graph)
                try:
                    results = executor.execute(query)
                    logger.info(
                        f"Using simplified query with post-filtering conditions: {conditions}"
                    )
                except Exception as e:
                    logger.error(f"Simplified query also failed: {e}")
                    raise

            # Extract policy names from the results
            for row in results:
                if "r.name" in row:
                    matching_policies_from_query.append(row["r.name"])

            logger.info(f"Query matched {len(matching_policies_from_query)} policies")

            # If no criteria was provided, create one based on the query results
            if not criteria and matching_policies_from_query:
                criteria = {"name": matching_policies_from_query}
            # If criteria was provided, extend it with query results
            elif criteria and matching_policies_from_query:
                # If criteria already has a 'name' field, append to it
                if "name" in criteria:
                    if isinstance(criteria["name"], list):
                        criteria["name"].extend(matching_policies_from_query)
                    else:
                        criteria["name"] = [criteria["name"]] + matching_policies_from_query
                # Otherwise, add a new 'name' field
                else:
                    criteria["name"] = matching_policies_from_query

        # If no selection method was provided, stop
        if not criteria:
            logger.error("No selection criteria or query filter provided")
            raise typer.Exit(1)

        # Load operations
        with open(operations_file, "r") as f:
            operations = json.load(f)
        logger.info(f"Loaded operations from {operations_file}: {operations}")

        # Perform update
        if dry_run:
            logger.info("Dry run mode: Changes will not be applied")

            # Select matching policies to show what would be updated
            # Use the modules.policies implementation for more reliable results
            from panflow.modules.policies import get_policies

            # Create a custom wrapper that suppresses logging
            def get_policies_no_logging(*args, **kwargs):
                import logging

                # Temporarily raise the logging level to suppress info messages
                current_level = logging.getLogger("panflow").level
                logging.getLogger("panflow").setLevel(logging.WARNING)
                try:
                    result = get_policies(*args, **kwargs)
                    return result
                finally:
                    # Restore the original logging level
                    logging.getLogger("panflow").setLevel(current_level)

            # Get the policies using the more reliable function with logging suppressed
            policy_dict = get_policies_no_logging(
                tree, policy_type, device_type, context, version, **context_kwargs
            )

            # Filter policies based on criteria
            policies = []
            for name, properties in policy_dict.items():
                # Simple criteria matching for name
                if "name" in criteria and name in criteria["name"]:
                    policy = {"name": name}
                    policy.update(properties)
                    policies.append(policy)

            # Display policies that would be updated using common formatting
            from ..common import format_policies_list

            formatted_lines = format_policies_list(
                policies, include_header=True, policy_type=policy_type, count=len(policies)
            )
            for line in formatted_lines:
                # Replace the first line to include "Would update" instead of "Found"
                if line.startswith("Found"):
                    logger.info(f"Would update {len(policies)} {policy_type} policies:")
                else:
                    # Add "Would update policy:" prefix to each policy line
                    if line.startswith("  - "):
                        logger.info(f"  - Would update policy: {line[4:]}")
                    else:
                        logger.info(line)

            # Log the operations that would be applied
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
