"""
Policy commands for PANFlow CLI.

This module provides commands for managing PAN-OS policies.
"""

import json
import logging
import typer
import re
from typing import Optional, Dict, Any, Tuple, List, Union

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


def simplify_query(query_text: str) -> tuple[str, list[str]]:
    """
    Simplify a complex query to basic matching. Used as fallback.
    
    Args:
        query_text: The original query text
        
    Returns:
        Tuple of (simplified_query, conditions)
    """
    # Extract any pattern about action, log settings, etc.
    conditions = []
    simplified = "MATCH (r:security_rule) "
    
    # Look for common patterns
    if "r.action" in query_text:
        import re
        match = re.search(r"r\.action\s*==\s*['\"]([^'\"]+)['\"]", query_text)
        if match:
            action = match.group(1)
            simplified += f"WHERE r.action == '{action}' "
            conditions.append(f"action={action}")
    
    if "RETURN" not in simplified:
        simplified += "RETURN r.name"
        
    return simplified, conditions

def execute_policy_query(graph, query_text: str, context_type: Optional[str] = None, device_group: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Execute a policy query with fallback to simple queries if needed.

    Args:
        graph: The graph to query
        query_text: The query text to execute
        context_type: The type of context (shared, device_group, vsys)
        device_group: The device group name (for device_group context)

    Returns:
        List of query results or empty list if the query fails
    """
    try:
        # Check if we need to modify the query for device group context
        if context_type == "device_group" and device_group and "security-rule" in query_text:
            # Only modify if the query doesn't already filter by device group
            if "device_group" not in query_text and "RETURN" in query_text.upper():
                # Add device group condition to WHERE clause if one exists
                if "WHERE" in query_text:
                    query_text = query_text.replace("WHERE", f"WHERE r.device_group == '{device_group}' AND ")
                    logger.debug(f"Modified query with WHERE condition: {query_text}")
                else:
                    # Insert WHERE clause before RETURN
                    return_idx = query_text.upper().find("RETURN")
                    query_text = f"{query_text[:return_idx]} WHERE r.device_group == '{device_group}' {query_text[return_idx:]}"
                    logger.debug(f"Modified query with new WHERE clause: {query_text}")
        
        # Try the original (or modified) query
        query = Query(query_text)
        executor = QueryExecutor(graph)
        results = executor.execute(query)
        
        # Log the number of results for debugging
        logger.debug(f"Query returned {len(results)} results")
        return results
    except Exception as query_error:
        logger.warning(f"Query failed: {query_error}. Trying basic query.")

        # Try basic query for all security rules, adding device_group filter if needed
        basic_query = "MATCH (r:security_rule) "
        if context_type == "device_group" and device_group:
            basic_query += f"WHERE r.device_group == '{device_group}' "
        basic_query += "RETURN r.name"
        
        logger.debug(f"Using fallback query: {basic_query}")
        
        try:
            query = Query(basic_query)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            logger.debug(f"Fallback query returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Basic query also failed: {e}")
            
            # This is a last resort: scan all nodes in the graph for security rules
            try:
                # Collect all security rule nodes manually
                manual_results = []
                for node_id, attrs in graph.graph.nodes(data=True):
                    if attrs.get("type") == "security-rule":
                        # Skip if we're looking for a specific device group and this doesn't match
                        if context_type == "device_group" and device_group:
                            node_dg = attrs.get("device_group", "")
                            if node_dg != device_group:
                                continue
                                
                        # Create a result row with the rule name
                        if "name" in attrs:
                            manual_results.append({"r.name": attrs["name"]})
                
                logger.debug(f"Manual graph scan found {len(manual_results)} security rules")
                return manual_results
            except Exception as manual_error:
                logger.error(f"Manual graph scan also failed: {manual_error}")
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
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results"),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format (json, table, text, csv, yaml, html)"
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

            # Build the graph with context parameters
            graph = ConfigGraph(
                device_type=device_type,
                context_type=context,
                **context_kwargs
            )
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

            # Execute the query with fallback, passing context information
            results = execute_policy_query(
                graph=graph, 
                query_text=query_text,
                context_type=context,
                device_group=device_group if context == "device_group" else None
            )

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

        # Format and display the policies based on format option
        if format.lower() == "table":
            # Table format using rich
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title=f"{policy_type.capitalize()} Policies")

            # Add columns based on the data
            if all_policies:
                # Always include name column
                table.add_column("name")

                # Add columns for common fields based on policy type
                common_fields = ["action", "disabled", "description"]

                # Add additional fields based on policy type
                if "security" in policy_type:
                    additional_fields = ["log_start", "log_end", "profile_setting"]
                    common_fields.extend(additional_fields)

                for key in common_fields:
                    if any(key in policy for policy in all_policies):
                        table.add_column(key)

                # Add rows
                for policy in all_policies:
                    values = []
                    for column in table.columns:
                        header = column.header
                        if header == "profile_setting" and "profile_setting" in policy:
                            if isinstance(policy["profile_setting"], dict):
                                profile_types = []
                                for profile_type in [
                                    "antivirus",
                                    "vulnerability",
                                    "spyware",
                                    "url_filtering",
                                ]:
                                    if (
                                        profile_type in policy["profile_setting"]
                                        and policy["profile_setting"][profile_type]
                                    ):
                                        profile_types.append(profile_type)
                                values.append(", ".join(profile_types) if profile_types else "")
                            else:
                                values.append(str(policy.get(header, "")))
                        else:
                            values.append(str(policy.get(header, "")))

                    table.add_row(*values)

                # Display the table
                console.print(table)
            else:
                typer.echo(f"No {policy_type} policies found matching criteria")

        elif format.lower() in ["text", "txt"]:
            # Text format using common formatter
            from ..common import format_policies_list

            formatted_lines = format_policies_list(
                all_policies, include_header=True, policy_type=policy_type
            )
            for line in formatted_lines:
                typer.echo(line)

        elif format.lower() == "csv":
            # CSV format
            if all_policies:
                import csv
                import io

                output_stream = io.StringIO()

                # Find all fields for headers
                fields = set(["name"])
                for policy in all_policies:
                    fields.update(policy.keys())

                writer = csv.DictWriter(output_stream, fieldnames=sorted(list(fields)))
                writer.writeheader()
                for policy in all_policies:
                    # Create a simplified version of the policy for CSV output
                    simplified_policy = {}
                    for key, value in policy.items():
                        if isinstance(value, (list, dict)):
                            simplified_policy[key] = json.dumps(value)
                        else:
                            simplified_policy[key] = value
                    writer.writerow(simplified_policy)

                csv_output = output_stream.getvalue()

                if output:
                    with open(output, "w") as f:
                        f.write(csv_output)
                    logger.info(f"Saved {len(all_policies)} policies to {output} in CSV format")
                else:
                    typer.echo(csv_output)
            else:
                typer.echo(f"No {policy_type} policies found matching criteria")

        elif format.lower() == "yaml":
            # YAML format
            try:
                import yaml

                # Create a function to handle non-serializable objects
                def yaml_safe_dump(obj):
                    if isinstance(obj, dict):
                        return {k: yaml_safe_dump(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [yaml_safe_dump(item) for item in obj]
                    else:
                        return obj

                safe_policies = yaml_safe_dump(all_policies)
                yaml_output = yaml.dump(safe_policies, sort_keys=False, default_flow_style=False)

                if output:
                    with open(output, "w") as f:
                        f.write(yaml_output)
                    logger.info(f"Saved {len(all_policies)} policies to {output} in YAML format")
                else:
                    typer.echo(yaml_output)
            except ImportError:
                typer.echo("Error: PyYAML not installed. Install with 'pip install pyyaml'")
                raise typer.Exit(1)

        elif format.lower() == "html":
            # HTML format
            html = "<html><head><style>"
            html += "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border:1px solid #ddd}"
            html += "tr:nth-child(even){background-color:#f2f2f2}th{background-color:#4CAF50;color:white}"
            html += "</style></head><body>"

            html += f"<h2>{policy_type.capitalize()} Policies</h2>"

            if all_policies:
                html += "<table><tr>"

                # Find all fields for headers
                fields = set(["name"])
                for policy in all_policies:
                    fields.update(policy.keys())

                # Add headers
                for field in sorted(list(fields)):
                    html += f"<th>{field}</th>"

                html += "</tr>"

                # Add rows
                for policy in all_policies:
                    html += "<tr>"
                    for field in sorted(list(fields)):
                        value = policy.get(field, "")
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        html += f"<td>{value}</td>"
                    html += "</tr>"

                html += "</table>"
            else:
                html += f"<p>No {policy_type} policies found matching criteria</p>"

            html += "</body></html>"

            if output:
                with open(output, "w") as f:
                    f.write(html)
                logger.info(f"Saved {len(all_policies)} policies to {output} in HTML format")
            else:
                typer.echo(html)

        else:
            # Default JSON format
            if output:
                # Convert policies to dict with names as keys for cleaner JSON output
                policy_dict = {p.get("name", f"policy_{i}"): p for i, p in enumerate(all_policies)}
                with open(output, "w") as f:
                    json.dump(policy_dict, f, indent=2)
                logger.info(f"Saved {len(all_policies)} policies to {output} in JSON format")
            else:
                # If no output file specified, display in text format for console readability
                from ..common import format_policies_list

                formatted_lines = format_policies_list(
                    all_policies, include_header=True, policy_type=policy_type
                )
                for line in formatted_lines:
                    typer.echo(line)

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
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results"),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format (json, table, text, csv, yaml, html)"
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

            # Build the graph with context parameters
            graph = ConfigGraph(
                device_type=device_type,
                context_type=context,
                **context_kwargs
            )
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

            # Execute the query with fallback, passing context information
            results = execute_policy_query(
                graph=graph, 
                query_text=query_text,
                context_type=context,
                device_group=device_group if context == "device_group" else None
            )

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

        # Format and display the filtered policies based on format option
        if format.lower() == "table":
            # Table format using rich
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title=f"Filtered {policy_type.capitalize()} Policies")

            # Add columns based on the data
            if filtered_policies:
                # Always include name column
                table.add_column("name")

                # Add columns for common fields based on policy type
                common_fields = ["action", "disabled", "description"]

                # Add additional fields based on policy type
                if "security" in policy_type:
                    additional_fields = ["log_start", "log_end", "profile_setting"]
                    common_fields.extend(additional_fields)

                for key in common_fields:
                    if any(key in policy for policy in filtered_policies):
                        table.add_column(key)

                # Add rows
                for policy in filtered_policies:
                    values = []
                    for column in table.columns:
                        header = column.header
                        if header == "profile_setting" and "profile_setting" in policy:
                            if isinstance(policy["profile_setting"], dict):
                                profile_types = []
                                for profile_type in [
                                    "antivirus",
                                    "vulnerability",
                                    "spyware",
                                    "url_filtering",
                                ]:
                                    if (
                                        profile_type in policy["profile_setting"]
                                        and policy["profile_setting"][profile_type]
                                    ):
                                        profile_types.append(profile_type)
                                values.append(", ".join(profile_types) if profile_types else "")
                            else:
                                values.append(str(policy.get(header, "")))
                        else:
                            values.append(str(policy.get(header, "")))

                    table.add_row(*values)

                # Display the table
                console.print(table)
            else:
                typer.echo(f"No {policy_type} policies found matching criteria")

        elif format.lower() in ["text", "txt"]:
            # Text format using common formatter
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
                    typer.echo(f"Final result: {len(filtered_policies)} {policy_type} policies:")
                else:
                    typer.echo(line)

        elif format.lower() == "csv":
            # CSV format
            if filtered_policies:
                import csv
                import io

                output_stream = io.StringIO()

                # Find all fields for headers
                fields = set(["name"])
                for policy in filtered_policies:
                    fields.update(policy.keys())

                writer = csv.DictWriter(output_stream, fieldnames=sorted(list(fields)))
                writer.writeheader()
                for policy in filtered_policies:
                    # Create a simplified version of the policy for CSV output
                    simplified_policy = {}
                    for key, value in policy.items():
                        if isinstance(value, (list, dict)):
                            simplified_policy[key] = json.dumps(value)
                        else:
                            simplified_policy[key] = value
                    writer.writerow(simplified_policy)

                csv_output = output_stream.getvalue()

                if output:
                    with open(output, "w") as f:
                        f.write(csv_output)
                    logger.info(
                        f"Saved {len(filtered_policies)} policies to {output} in CSV format"
                    )
                else:
                    typer.echo(csv_output)
            else:
                typer.echo(f"No {policy_type} policies found matching criteria")

        elif format.lower() == "yaml":
            # YAML format
            try:
                import yaml

                # Create a function to handle non-serializable objects
                def yaml_safe_dump(obj):
                    if isinstance(obj, dict):
                        return {k: yaml_safe_dump(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [yaml_safe_dump(item) for item in obj]
                    else:
                        return obj

                safe_policies = yaml_safe_dump(filtered_policies)
                yaml_output = yaml.dump(safe_policies, sort_keys=False, default_flow_style=False)

                if output:
                    with open(output, "w") as f:
                        f.write(yaml_output)
                    logger.info(
                        f"Saved {len(filtered_policies)} policies to {output} in YAML format"
                    )
                else:
                    typer.echo(yaml_output)
            except ImportError:
                typer.echo("Error: PyYAML not installed. Install with 'pip install pyyaml'")
                raise typer.Exit(1)

        elif format.lower() == "html":
            # HTML format
            html = "<html><head><style>"
            html += "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border:1px solid #ddd}"
            html += "tr:nth-child(even){background-color:#f2f2f2}th{background-color:#4CAF50;color:white}"
            html += "</style></head><body>"

            html += f"<h2>Filtered {policy_type.capitalize()} Policies</h2>"
            html += f"<p>Total: {len(filtered_policies)} policies</p>"

            if filtered_policies:
                html += "<table><tr>"

                # Find all fields for headers
                fields = set(["name"])
                for policy in filtered_policies:
                    fields.update(policy.keys())

                # Add headers
                for field in sorted(list(fields)):
                    html += f"<th>{field}</th>"

                html += "</tr>"

                # Add rows
                for policy in filtered_policies:
                    html += "<tr>"
                    for field in sorted(list(fields)):
                        value = policy.get(field, "")
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        html += f"<td>{value}</td>"
                    html += "</tr>"

                html += "</table>"
            else:
                html += f"<p>No {policy_type} policies found matching criteria</p>"

            html += "</body></html>"

            if output:
                with open(output, "w") as f:
                    f.write(html)
                logger.info(f"Saved {len(filtered_policies)} policies to {output} in HTML format")
            else:
                typer.echo(html)

        else:
            # Default JSON format
            if filtered_policies:
                if output:
                    # Convert policies to dict with names as keys for cleaner JSON output
                    policy_dict = {
                        p.get("name", f"policy_{i}"): p for i, p in enumerate(filtered_policies)
                    }
                    with open(output, "w") as f:
                        json.dump(policy_dict, f, indent=2)
                    logger.info(
                        f"Saved {len(filtered_policies)} policies to {output} in JSON format"
                    )
                else:
                    # If no output file specified, display in text format for console readability
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
                            typer.echo(
                                f"Final result: {len(filtered_policies)} {policy_type} policies:"
                            )
                        else:
                            typer.echo(line)
            else:
                typer.echo(f"No {policy_type} policies found matching criteria")

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
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format for dry run (json, table, text, csv, yaml, html)",
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

            # Build the graph with context parameters
            graph = ConfigGraph(
                device_type=device_type,
                context_type=context,
                **context_kwargs
            )
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

            # Process query filter if specified to collect matching policy names
            matching_policies_from_query = []
            graph = None  # Initialize graph for reuse
            if query_filter:
                logger.info(f"Using graph query filter: {query_filter}")

                # Build the graph with context parameters - we'll store it to avoid rebuilding later
                graph = ConfigGraph(
                    device_type=device_type,
                    context_type=context,
                    **context_kwargs
                )
                graph.build_from_xml(tree)

                # Prepare a query that returns policy names
                if "RETURN" not in query_filter.upper():
                    query_text = f"{query_filter} RETURN r.name"
                else:
                    query_text = query_filter

                # Execute the query with fallback
                results = execute_policy_query(
                    graph=graph, 
                    query_text=query_text,
                    context_type=context,
                    device_group=device_group if context == "device_group" else None
                )

                # Extract policy names from the results
                for row in results:
                    if "r.name" in row:
                        matching_policies_from_query.append(row["r.name"])
                    elif len(row) == 1:  # If there's only one column, use its value
                        matching_policies_from_query.append(list(row.values())[0])

                logger.info(f"Query matched {len(matching_policies_from_query)} policies")

                # If criteria was provided, extend it with query results
                if criteria and matching_policies_from_query:
                    # If criteria already has a 'name' field, append to it
                    if "name" in criteria:
                        if isinstance(criteria["name"], list):
                            criteria["name"].extend(matching_policies_from_query)
                        else:
                            criteria["name"] = [criteria["name"]] + matching_policies_from_query
                    # Otherwise, add a new 'name' field
                    else:
                        criteria["name"] = matching_policies_from_query
                # If no criteria, create one based on query results
                elif matching_policies_from_query:
                    criteria = {"name": matching_policies_from_query}

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

            # Format and display the policies that would be updated based on format option
            if format.lower() == "table":
                # Table format using rich
                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(title=f"Policies That Would Be Updated ({policy_type})")

                # Add columns based on the data
                if policies:
                    # Always include name column
                    table.add_column("name")

                    # Add columns for common fields based on policy type
                    common_fields = ["action", "disabled", "description"]

                    # Add additional fields based on policy type
                    if "security" in policy_type:
                        additional_fields = ["log_start", "log_end", "profile_setting"]
                        common_fields.extend(additional_fields)

                    for key in common_fields:
                        if any(key in policy for policy in policies):
                            table.add_column(key)

                    # Add rows
                    for policy in policies:
                        values = []
                        for column in table.columns:
                            header = column.header
                            if header == "profile_setting" and "profile_setting" in policy:
                                if isinstance(policy["profile_setting"], dict):
                                    profile_types = []
                                    for profile_type in [
                                        "antivirus",
                                        "vulnerability",
                                        "spyware",
                                        "url_filtering",
                                    ]:
                                        if (
                                            profile_type in policy["profile_setting"]
                                            and policy["profile_setting"][profile_type]
                                        ):
                                            profile_types.append(profile_type)
                                    values.append(", ".join(profile_types) if profile_types else "")
                                else:
                                    values.append(str(policy.get(header, "")))
                            else:
                                values.append(str(policy.get(header, "")))

                        table.add_row(*values)

                    # Display the table
                    console.print(table)
                else:
                    typer.echo(f"No {policy_type} policies found matching criteria")

                # Show operations
                ops_table = Table(title="Operations That Would Be Applied")
                ops_table.add_column("Operation")
                ops_table.add_column("Value")

                for op_key, op_value in operations.items():
                    ops_table.add_row(op_key, str(op_value))

                console.print(ops_table)

            elif format.lower() in ["text", "txt"]:
                # Text format using common formatter
                from ..common import format_policies_list

                formatted_lines = format_policies_list(
                    policies, include_header=True, policy_type=policy_type, count=len(policies)
                )
                for line in formatted_lines:
                    # Replace the first line to include "Would update" instead of "Found"
                    if line.startswith("Found"):
                        typer.echo(f"Would update {len(policies)} {policy_type} policies:")
                    else:
                        # Add "Would update policy:" prefix to each policy line
                        if line.startswith("  - "):
                            typer.echo(f"  - Would update policy: {line[4:]}")
                        else:
                            typer.echo(line)

                # Show operations
                typer.echo("\nWould apply these operations:")
                for op_key, op_value in operations.items():
                    typer.echo(f"  - {op_key}: {op_value}")

            elif format.lower() == "csv":
                # CSV format
                if policies:
                    import csv
                    import io

                    # Policy CSV
                    output_stream = io.StringIO()
                    output_stream.write("# POLICIES THAT WOULD BE UPDATED\n")

                    # Find all fields for headers
                    fields = set(["name"])
                    for policy in policies:
                        fields.update(policy.keys())

                    writer = csv.DictWriter(output_stream, fieldnames=sorted(list(fields)))
                    writer.writeheader()
                    for policy in policies:
                        # Create a simplified version of the policy for CSV output
                        simplified_policy = {}
                        for key, value in policy.items():
                            if isinstance(value, (list, dict)):
                                simplified_policy[key] = json.dumps(value)
                            else:
                                simplified_policy[key] = value
                        writer.writerow(simplified_policy)

                    # Operations CSV
                    output_stream.write("\n# OPERATIONS THAT WOULD BE APPLIED\n")
                    ops_writer = csv.writer(output_stream)
                    ops_writer.writerow(["Operation", "Value"])
                    for op_key, op_value in operations.items():
                        ops_writer.writerow([op_key, str(op_value)])

                    csv_output = output_stream.getvalue()
                    typer.echo(csv_output)
                else:
                    typer.echo(f"No {policy_type} policies found matching criteria")

            elif format.lower() == "yaml":
                # YAML format
                try:
                    import yaml

                    # Create a function to handle non-serializable objects
                    def yaml_safe_dump(obj):
                        if isinstance(obj, dict):
                            return {k: yaml_safe_dump(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [yaml_safe_dump(item) for item in obj]
                        else:
                            return obj

                    # Prepare output data
                    output_data = {
                        "dry_run": True,
                        "policies_to_update": yaml_safe_dump(policies),
                        "operations_to_apply": yaml_safe_dump(operations),
                    }

                    yaml_output = yaml.dump(output_data, sort_keys=False, default_flow_style=False)
                    typer.echo(yaml_output)
                except ImportError:
                    typer.echo("Error: PyYAML not installed. Install with 'pip install pyyaml'")
                    raise typer.Exit(1)

            elif format.lower() == "html":
                # HTML format
                html = "<html><head><style>"
                html += "table{border-collapse:collapse;width:100%;margin-bottom:20px}th,td{text-align:left;padding:8px;border:1px solid #ddd}"
                html += "tr:nth-child(even){background-color:#f2f2f2}th{background-color:#4CAF50;color:white}"
                html += "h2{color:#333}h3{color:#555}.operations{margin-top:30px}"
                html += "</style></head><body>"

                html += f"<h2>Bulk Update Dry Run - {policy_type} Policies</h2>"

                # Policies table
                html += f"<h3>Policies That Would Be Updated ({len(policies)})</h3>"

                if policies:
                    html += "<table><tr>"

                    # Find all fields for headers
                    fields = set(["name"])
                    for policy in policies:
                        fields.update(policy.keys())

                    # Add headers
                    for field in sorted(list(fields)):
                        html += f"<th>{field}</th>"

                    html += "</tr>"

                    # Add rows
                    for policy in policies:
                        html += "<tr>"
                        for field in sorted(list(fields)):
                            value = policy.get(field, "")
                            if isinstance(value, (dict, list)):
                                value = json.dumps(value)
                            html += f"<td>{value}</td>"
                        html += "</tr>"

                    html += "</table>"
                else:
                    html += f"<p>No {policy_type} policies found matching criteria</p>"

                # Operations table
                html += "<div class='operations'>"
                html += "<h3>Operations That Would Be Applied</h3>"
                html += "<table><tr><th>Operation</th><th>Value</th></tr>"

                for op_key, op_value in operations.items():
                    html += f"<tr><td>{op_key}</td><td>{op_value}</td></tr>"

                html += "</table></div>"
                html += "</body></html>"

                typer.echo(html)

            else:
                # Default JSON format
                output_data = {
                    "dry_run": True,
                    "policy_type": policy_type,
                    "policies_to_update": policies,
                    "operations_to_apply": operations,
                    "count": len(policies),
                }
                typer.echo(json.dumps(output_data, indent=2))

            # Log a summary of what would happen
            logger.info(f"Would update {len(policies)} policies with {len(operations)} operations")
        else:
            # Handle potential issues with device group context by adding debug logging
            if device_group and query_filter:
                logger.info(f"Processing query filter with device group context: {device_group}")
                
                # Add debugging info about the device group policies
                try:
                    dg_xpath = f"/config/devices/entry/device-group/entry[@name='{device_group}']/pre-rulebase/security/rules/entry"
                    dg_policies = [rule.get("name") for rule in tree.xpath(dg_xpath)]
                    logger.debug(f"Device group {device_group} pre-rulebase policies: {dg_policies}")
                    
                    dg_post_xpath = f"/config/devices/entry/device-group/entry[@name='{device_group}']/post-rulebase/security/rules/entry"
                    dg_post_policies = [rule.get("name") for rule in tree.xpath(dg_post_xpath)]
                    logger.debug(f"Device group {device_group} post-rulebase policies: {dg_post_policies}")
                    
                    if not dg_policies and not dg_post_policies:
                        logger.warning(f"No security policies found in device group: {device_group}")
                    
                    # If graph query returns no policies but we found policies using XPath, use those directly
                    if criteria is None or "name" not in criteria or not criteria["name"]:
                        all_policies = dg_policies + dg_post_policies
                        if all_policies:
                            criteria = {"name": all_policies}
                            logger.info(f"Using policies found via XPath: {all_policies}")
                except Exception as e:
                    logger.error(f"Error querying device group policies: {e}")
            
            # If we created a graph for the query filter, pass it to bulk_update_policies
            graph = None
            if query_filter:
                # Create the graph once so we can reuse it
                logger.info("Creating graph for bulk update operations")
                graph = ConfigGraph(
                    device_type=device_type,
                    context_type=context,
                    **context_kwargs
                )
                graph.build_from_xml(tree)
                
            # Perform the bulk update, passing both criteria and query_filter
            updated_count = updater.bulk_update_policies(
                policy_type, 
                criteria=criteria, 
                operations=operations,
                query_filter=query_filter,
                existing_graph=graph
            )

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
