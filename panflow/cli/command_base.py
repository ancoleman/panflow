"""
Command base classes and utilities for PANFlow CLI.

This module provides abstract base classes and decorators for standardizing
CLI command implementation, error handling, and output formatting.
"""

import json
import os
import sys
import logging
import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast
from functools import wraps

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from panflow import PANFlowConfig
from panflow.core.exceptions import PANFlowError
from panflow.core.logging_utils import logger, log_structured
from .common import ContextOptions

# Type variable for command functions
F = TypeVar("F", bound=Callable[..., Any])

# Rich console for output formatting
console = Console()


class OutputFormat(str, Enum):
    """Standardized output formats."""

    JSON = "json"
    TABLE = "table"
    TEXT = "text"
    CSV = "csv"
    YAML = "yaml"
    HTML = "html"


class CommandBase:
    """
    Base class for PANFlow CLI commands.

    This class provides common functionality for CLI commands, including
    configuration loading, error handling, and output formatting.
    """

    def __init__(self):
        """Initialize the command base."""
        pass

    @staticmethod
    def load_config(
        config_file: str, device_type: Optional[str] = None, version: Optional[str] = None
    ) -> PANFlowConfig:
        """
        Load a PANFlowConfig from a file.

        Args:
            config_file: Path to the configuration file
            device_type: Device type (firewall or panorama)
            version: PAN-OS version

        Returns:
            PANFlowConfig object

        Raises:
            PANFlowError: If the configuration file cannot be loaded
        """
        try:
            return PANFlowConfig(config_file=config_file, device_type=device_type, version=version)
        except Exception as e:
            # Log the error
            log_structured(
                f"Error loading configuration: {str(e)}",
                "error",
                config_file=config_file,
                device_type=device_type,
                version=version,
                error=str(e),
            )
            # Re-raise as PANFlowError
            raise PANFlowError(f"Failed to load configuration: {str(e)}")

    @staticmethod
    def get_context_params(
        context: str,
        device_group: Optional[str] = None,
        vsys: str = "vsys1",
        template: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get context parameters for the command.

        Args:
            context: Context type (shared, device_group, vsys, template)
            device_group: Device group name
            vsys: VSYS name
            template: Template name

        Returns:
            Dictionary of context parameters
        """
        return ContextOptions.get_context_kwargs(context, device_group, vsys, template)

    @staticmethod
    def format_output(
        data: Any,
        output_format: str = "json",
        output_file: Optional[str] = None,
        table_title: Optional[str] = None,
        report_type: Optional[str] = None,
        query_text: Optional[str] = None,
        config_file: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Format and display or save command output.

        Args:
            data: Data to format
            output_format: Output format (json, table, text, csv, yaml, html)
            output_file: File to save output to
            table_title: Title for table output
            report_type: Type of report (e.g., "Address Objects", "Unused Objects", "Query Results")
            query_text: Original query text if applicable
            config_file: Path to the configuration file used
            additional_info: Additional information to include in the output (e.g., context, device type)
        """
        # Handle None or empty data
        if data is None:
            console.print("[yellow]No data returned[/yellow]")
            return

        # Format the output
        if output_format.lower() == "json":
            formatted_output = json.dumps(data, indent=2)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(formatted_output)
                console.print(f"Output saved to [blue]{output_file}[/blue]")
            else:
                console.print(formatted_output)

        elif output_format.lower() == "table":
            # Create a table from the data
            if isinstance(data, list) and data:
                table = Table(title=table_title or "Results")

                # Add columns from the first item
                if isinstance(data[0], dict):
                    for key in data[0].keys():
                        table.add_column(str(key))

                    # Add rows
                    for item in data:
                        table.add_row(*[str(item.get(k, "")) for k in data[0].keys()])

                    if output_file:
                        with open(output_file, "w") as f:
                            f.write(table.__str__())
                        console.print(f"Output saved to [blue]{output_file}[/blue]")
                    else:
                        console.print(table)
                else:
                    # Handle non-dict list items
                    table.add_column("Value")
                    for item in data:
                        table.add_row(str(item))

                    if output_file:
                        with open(output_file, "w") as f:
                            f.write(table.__str__())
                        console.print(f"Output saved to [blue]{output_file}[/blue]")
                    else:
                        console.print(table)
            elif isinstance(data, dict):
                # Create a table from dictionary
                table = Table(title=table_title or "Results")
                table.add_column("Key")
                table.add_column("Value")

                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    table.add_row(str(key), str(value))

                if output_file:
                    with open(output_file, "w") as f:
                        f.write(table.__str__())
                    console.print(f"Output saved to [blue]{output_file}[/blue]")
                else:
                    console.print(table)
            else:
                # Just print the data directly
                console.print(data)

        elif output_format.lower() == "csv":
            # Create CSV output
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    # Create header
                    header = ",".join([f'"{str(k)}"' for k in data[0].keys()])
                    rows = [header]

                    # Create rows
                    for item in data:
                        row = ",".join([f'"{str(item.get(k, ""))}"' for k in data[0].keys()])
                        rows.append(row)

                    csv_output = "\n".join(rows)
                    if output_file:
                        with open(output_file, "w") as f:
                            f.write(csv_output)
                        console.print(f"Output saved to [blue]{output_file}[/blue]")
                    else:
                        console.print(csv_output)
                else:
                    # Create simple CSV for non-dict lists
                    csv_output = "\n".join([f'"{str(item)}"' for item in data])
                    if output_file:
                        with open(output_file, "w") as f:
                            f.write(csv_output)
                        console.print(f"Output saved to [blue]{output_file}[/blue]")
                    else:
                        console.print(csv_output)
            elif isinstance(data, dict):
                # Create two-column CSV from dictionary
                rows = ['"Key","Value"']
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    rows.append(f'"{str(key)}","{str(value)}"')

                csv_output = "\n".join(rows)
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(csv_output)
                    console.print(f"Output saved to [blue]{output_file}[/blue]")
                else:
                    console.print(csv_output)
            else:
                # Just print the data directly
                console.print(data)

        elif output_format.lower() == "yaml":
            try:
                import yaml

                yaml_output = yaml.dump(data, sort_keys=False, default_flow_style=False)
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(yaml_output)
                    console.print(f"Output saved to [blue]{output_file}[/blue]")
                else:
                    console.print(yaml_output)
            except ImportError:
                console.print(
                    "[red]PyYAML is not installed. Please install it with pip install pyyaml[/red]"
                )
                
        elif output_format.lower() == "html":
            try:
                # Generate a properly formatted HTML report with styling
                import datetime
                
                # Get timestamp for the report
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Determine title and subtitle
                if report_type:
                    main_title = f"PANFlow {report_type}"
                else:
                    main_title = table_title or 'PANFlow Report'
                
                # Build additional information section
                info_section = ""
                if query_text or config_file or additional_info:
                    info_section = """<div class="report-info">
    <h2>Report Information</h2>
    <table class="info-table">
"""
                    # Add query information if available (but skip if it's already in additional_info)
                    query_added = False
                    if additional_info and "Query" in additional_info:
                        query_added = True
                    
                    if query_text and not query_added:
                        info_section += f"""        <tr>
            <td class="info-key">Query</td>
            <td class="info-value"><pre>{query_text}</pre></td>
        </tr>
"""
                    
                    # Add config file information if available (but skip if it's already in additional_info)
                    config_added = False
                    if additional_info and "Configuration" in additional_info:
                        config_added = True
                    
                    if config_file and not config_added:
                        info_section += f"""        <tr>
            <td class="info-key">Configuration</td>
            <td class="info-value">{config_file}</td>
        </tr>
"""
                    
                    # Add any additional information but skip Query/Configuration that we've already added
                    if additional_info:
                        for key, value in additional_info.items():
                            # Skip query and config if already added
                            if (key == "Query" and query_added) or (key == "Configuration" and config_added):
                                continue
                            info_section += f"""        <tr>
            <td class="info-key">{key}</td>
            <td class="info-value">{value}</td>
        </tr>
"""
                    
                    info_section += """    </table>
</div>"""
                
                # Start building HTML content with consistent styling
                html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{main_title}</title>
    <style>
        body {{\n            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            margin-top: 20px;
            padding-bottom: 5px;
            border-bottom: 1px solid #ddd;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        tr:hover {{
            background-color: #f1f7fa;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-style: italic;
            margin-top: 40px;
            text-align: center;
        }}
        .key {{
            font-weight: bold;
        }}
        .value-col {{
            color: #2980b9;
            font-weight: bold;
        }}
        .details-col {{
            max-width: 300px;
            word-wrap: break-word;
        }}
        .container {{
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 30px;
        }}
        .note {{
            background-color: #fef9e7;
            padding: 10px;
            border-left: 4px solid #f39c12;
            margin: 10px 0;
        }}
        .report-info {{
            background-color: #edf7ff;
            border-radius: 8px;
            padding: 10px 20px;
            margin-bottom: 20px;
        }}
        .info-table {{
            border: none;
            box-shadow: none;
        }}
        .info-table td {{
            padding: 5px 10px;
        }}
        .info-key {{
            font-weight: bold;
            width: 150px;
        }}
        .info-value {{
            font-family: monospace;
        }}
        .info-value pre {{
            margin: 0;
            background-color: #f5f5f5;
            padding: 5px 10px;
            border-radius: 3px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>{main_title}</h1>
    {info_section}
    <div class="container">
"""
                
                # Format the content based on data type
                if isinstance(data, list) and data:
                    # Table for list data
                    if isinstance(data[0], dict):
                        # Get columns from the first item
                        columns = list(data[0].keys())
                        
                        # Create table with headers
                        html_content += "<table>\n<thead>\n<tr>\n"
                        for column in columns:
                            html_content += f"<th>{column}</th>\n"
                        html_content += "</tr>\n</thead>\n<tbody>\n"
                        
                        # Add rows
                        for item in data:
                            html_content += "<tr>\n"
                            for column in columns:
                                value = item.get(column, "")
                                html_content += f"<td>{value}</td>\n"
                            html_content += "</tr>\n"
                        
                        html_content += "</tbody>\n</table>\n"
                    else:
                        # Simple list
                        html_content += "<table>\n<thead>\n<tr>\n<th>Value</th>\n</tr>\n</thead>\n<tbody>\n"
                        for item in data:
                            html_content += f"<tr>\n<td>{item}</td>\n</tr>\n"
                        html_content += "</tbody>\n</table>\n"
                
                elif isinstance(data, dict):
                    # Table for dictionary data
                    html_content += "<table>\n<thead>\n<tr>\n"
                    html_content += "<th>Key</th>\n<th>Value</th>\n"
                    html_content += "</tr>\n</thead>\n<tbody>\n"
                    
                    for key, value in data.items():
                        html_content += "<tr>\n"
                        html_content += f"<td class='key'>{key}</td>\n"
                        
                        # Special handling for better HTML formatting
                        if key == "nlq_info" and isinstance(value, dict):
                            # Format NLQ info in a more readable way
                            nlq_html = "<table class='info-table'>\n"
                            for info_key, info_val in value.items():
                                nlq_html += f"<tr><td class='info-key'>{info_key}</td><td class='info-value'>{info_val}</td></tr>\n"
                            nlq_html += "</table>"
                            html_content += f"<td>{nlq_html}</td>\n"
                        elif key == "unused_address_objects" and isinstance(value, list):
                            # Format unused objects as a nice table
                            if value:
                                obj_html = "<table class='info-table'>\n"
                                obj_html += "<tr><th>Name</th><th>IP Address</th><th>Context</th></tr>\n"
                                for obj in value:
                                    name = obj.get("name", "")
                                    ip = obj.get("ip-netmask", obj.get("ip-range", obj.get("fqdn", "")))
                                    context = obj.get("context", "Unknown")
                                    obj_html += f"<tr><td>{name}</td><td>{ip}</td><td>{context}</td></tr>\n"
                                obj_html += "</table>"
                                html_content += f"<td>{obj_html}</td>\n"
                            else:
                                html_content += "<td>No unused objects found</td>\n"
                        elif key == "duplicates" and isinstance(value, dict):
                            # Format duplicates as a nice table
                            items = value.get("items", [])
                            if items:
                                dup_html = f"<p>Found {value.get('count', 0)} duplicate {value.get('object_type', '')} objects</p>\n"
                                dup_html += "<table class='info-table'>\n"
                                if "object_type" in items[0]:
                                    dup_html += "<tr><th>Object Type</th><th>Value</th><th>Objects</th></tr>\n"
                                    for item in items:
                                        obj_type = item.get("object_type", "")
                                        val = item.get("value", "")
                                        objects = ", ".join(item.get("objects", []))
                                        dup_html += f"<tr><td>{obj_type}</td><td>{val}</td><td>{objects}</td></tr>\n"
                                else:
                                    dup_html += "<tr><th>Value</th><th>Objects</th></tr>\n"
                                    for item in items:
                                        val = item.get("value", "")
                                        objects = ", ".join(item.get("objects", []))
                                        dup_html += f"<tr><td>{val}</td><td>{objects}</td></tr>\n"
                                dup_html += "</table>"
                                html_content += f"<td>{dup_html}</td>\n"
                            else:
                                html_content += "<td>No duplicates found</td>\n"
                        # Format other nested structures
                        elif isinstance(value, (dict, list)):
                            # Check if we can render this better
                            if isinstance(value, list) and value and isinstance(value[0], dict):
                                # It's a list of objects, make a table
                                list_html = "<table class='info-table'>\n"
                                # Get headers from first item
                                headers = list(value[0].keys())
                                list_html += "<tr>"
                                for header in headers:
                                    list_html += f"<th>{header}</th>"
                                list_html += "</tr>\n"
                                # Add rows
                                for item in value:
                                    list_html += "<tr>"
                                    for header in headers:
                                        list_html += f"<td>{item.get(header, '')}</td>"
                                    list_html += "</tr>\n"
                                list_html += "</table>"
                                html_content += f"<td>{list_html}</td>\n"
                            else:
                                # Just use JSON format
                                json_value = json.dumps(value, indent=2)
                                html_content += f"<td><pre>{json_value}</pre></td>\n"
                        else:
                            html_content += f"<td>{value}</td>\n"
                        
                        html_content += "</tr>\n"
                    
                    html_content += "</tbody>\n</table>\n"
                
                else:
                    # Simple string or other value
                    html_content += f"<p>{data}</p>\n"
                
                # Add timestamp and close tags
                html_content += f"""    </div>
    <div class="timestamp">
        Report generated on {timestamp}
    </div>
</body>
</html>
"""
                
                # Save to file or display
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(html_content)
                    console.print(f"Output saved to [blue]{output_file}[/blue]")
                else:
                    console.print(html_content)
                    
            except Exception as e:
                logger.error(f"Error generating HTML: {str(e)}")
                console.print(f"[red]Error generating HTML:[/red] {str(e)}")
                
                # Fall back to text format
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(str(data))
                    console.print(f"Output saved to [blue]{output_file}[/blue] (text format)")
                else:
                    console.print(str(data))

        else:
            # Default to text output
            if output_file:
                with open(output_file, "w") as f:
                    f.write(str(data))
                console.print(f"Output saved to [blue]{output_file}[/blue]")
            else:
                console.print(str(data))

    @staticmethod
    def handle_error(error: Exception, command_name: str) -> None:
        """
        Handle command errors consistently.

        Args:
            error: The exception to handle
            command_name: Name of the command for logging
        """
        if isinstance(error, PANFlowError):
            log_structured(
                f"Command error in {command_name}: {str(error)}",
                "error",
                command=command_name,
                error_type=type(error).__name__,
                error_message=str(error),
            )
            console.print(f"[red]Error:[/red] {str(error)}")
            sys.exit(1)
        else:
            log_structured(
                f"Unexpected error in {command_name}: {str(error)}",
                "error",
                command=command_name,
                error_type=type(error).__name__,
                error_message=str(error),
                traceback=traceback.format_exc(),
            )
            console.print(f"[red]Unexpected error:[/red] {str(error)}")

            # Print traceback in debug mode
            if logger.getEffectiveLevel() <= logging.DEBUG:
                console.print("[red]Traceback:[/red]")
                console.print(traceback.format_exc())
            sys.exit(1)


# Command decorators
def command_error_handler(f: F) -> F:
    """
    Decorator to standardize error handling for commands.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with error handling
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            CommandBase.handle_error(e, f.__name__)

    return cast(F, wrapper)


def config_loader(f: F) -> F:
    """
    Decorator to load and inject PANFlowConfig into command function.

    This decorator extracts config_file, device_type, and version arguments,
    loads the configuration, and adds it as a 'config' parameter to the function.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with config loading
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        # Extract relevant parameters
        config_file = kwargs.pop("config", None)
        device_type = kwargs.pop("device_type", None)
        version = kwargs.pop("version", None)

        if config_file:
            # Load the configuration
            panflow_config = CommandBase.load_config(config_file, device_type, version)

            # Add the config to kwargs
            kwargs["panflow_config"] = panflow_config

        return f(*args, **kwargs)

    return cast(F, wrapper)


def context_handler(f: F) -> F:
    """
    Decorator to extract and process context parameters.

    This decorator extracts context, device_group, vsys, and template arguments,
    and adds a 'context_kwargs' parameter to the function.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with context handling
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        # Extract context parameters
        context = kwargs.pop("context", "shared")
        device_group = kwargs.pop("device_group", None)
        vsys = kwargs.pop("vsys", "vsys1")
        template = kwargs.pop("template", None)

        # Get context kwargs
        context_kwargs = CommandBase.get_context_params(context, device_group, vsys, template)

        # Add context_kwargs to kwargs
        kwargs["context_kwargs"] = context_kwargs

        return f(*args, **kwargs)

    return cast(F, wrapper)


def output_formatter(f: F) -> F:
    """
    Decorator to format command output.

    This decorator formats the return value of the function based on the
    output_format and output_file parameters.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with output formatting
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        # Extract output parameters
        output_format = kwargs.pop("output_format", "json")
        output_file = kwargs.pop("output_file", None)
        table_title = kwargs.pop("table_title", None)

        # Call the function
        result = f(*args, **kwargs)

        # Format the output
        if result is not None:
            CommandBase.format_output(result, output_format, output_file, table_title)

        return result

    return cast(F, wrapper)


def standard_command(f: F) -> F:
    """
    Combined decorator that applies all standard command processing.

    This decorator applies error_handler, config_loader, context_handler,
    and output_formatter in a single decorator.

    Args:
        f: Command function to decorate

    Returns:
        Fully decorated command function
    """

    @wraps(f)
    @command_error_handler
    @config_loader
    @context_handler
    @output_formatter
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return cast(F, wrapper)
