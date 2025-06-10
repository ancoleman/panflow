"""
Enhanced command base for PANFlow CLI v0.4.1.

This module provides an enhanced command base that consolidates common patterns
found in CLI commands, specifically addressing the duplication patterns identified
in the refactoring analysis:

- CLI parameter handling (269 typer.Option occurrences)
- Config loading patterns (33 occurrences)
- Context handling (15 context_kwargs patterns)
- Error handling standardization
- Output formatting consolidation

Key improvements over the base CommandBase:
1. Standard parameter decorators for common typer.Option patterns
2. Automatic config loading and context resolution
3. Unified error handling with structured logging
4. Query filtering integration
5. Comprehensive output formatting with all supported formats
"""

import json
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import typer
from rich.console import Console
from rich.table import Table

from panflow import PANFlowConfig, OBJECT_TYPE_ALIASES
from panflow.core.exceptions import PANFlowError
from panflow.core.feature_flags import is_enabled, dual_path
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow.core.logging_utils import logger, log_structured

from .common import ConfigOptions, ContextOptions, ObjectOptions
from .command_base import CommandBase, OutputFormat

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Rich console for output
console = Console()


class EnhancedCommandBase(CommandBase):
    """
    Enhanced command base that consolidates common CLI patterns.
    
    This class addresses the major duplication patterns identified in the analysis:
    - Standardized parameter handling
    - Automatic config loading and context resolution
    - Unified error handling and logging
    - Query filtering integration
    - Comprehensive output formatting
    """

    @staticmethod
    def standard_config_params() -> Dict[str, typer.Option]:
        """Return standard configuration parameters as a dictionary."""
        return {
            "config": ConfigOptions.config_file(),
            "device_type": ConfigOptions.device_type(),
            "version": ConfigOptions.version(),
            "output_file": typer.Option(None, "--output", "-o", help="Output file for results"),
        }

    @staticmethod
    def standard_context_params() -> Dict[str, typer.Option]:
        """Return standard context parameters as a dictionary."""
        return {
            "context": ContextOptions.context_type(),
            "device_group": ContextOptions.device_group(),
            "vsys": ContextOptions.vsys(),
            "template": ContextOptions.template(),
        }

    @staticmethod
    def standard_output_params() -> Dict[str, typer.Option]:
        """Return standard output parameters as a dictionary."""
        return {
            "format": typer.Option(
                "json", "--format", "-f", 
                help="Output format (json, table, text, csv, yaml, html)"
            ),
            "query_filter": typer.Option(
                None, "--query-filter", "-q",
                help="Graph query filter to select objects"
            ),
        }

    @staticmethod
    def load_config_and_context(
        config: str,
        device_type: Optional[str] = None,
        version: Optional[str] = None,
        context: str = "shared",
        device_group: Optional[str] = None,
        vsys: str = "vsys1",
        template: Optional[str] = None,
    ) -> tuple[PANFlowConfig, Dict[str, str]]:
        """
        Load configuration and resolve context parameters.
        
        This consolidates the config loading and context resolution patterns
        found in every command.
        
        Returns:
            Tuple of (PANFlowConfig, context_kwargs)
        """
        try:
            # Load configuration
            xml_config = PANFlowConfig(
                config_file=config, 
                device_type=device_type, 
                version=version
            )
            
            # Resolve context parameters
            context_kwargs = ContextOptions.get_context_kwargs(
                context, device_group, vsys, template
            )
            
            log_structured(
                "Configuration and context loaded successfully",
                "info",
                config_file=config,
                device_type=device_type or "auto-detect",
                context=context,
                context_kwargs=context_kwargs,
            )
            
            return xml_config, context_kwargs
            
        except Exception as e:
            log_structured(
                f"Failed to load configuration or context: {str(e)}",
                "error",
                config_file=config,
                device_type=device_type,
                version=version,
                context=context,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            raise PANFlowError(f"Configuration/context loading failed: {str(e)}")

    @staticmethod
    def apply_query_filter(
        objects: Dict[str, Any],
        query_filter: str,
        xml_config: PANFlowConfig,
        object_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply query filtering to objects.
        
        This consolidates the query filtering pattern used across multiple commands.
        """
        try:
            logger.info(f"Applying query filter: {query_filter}")
            
            # Build the graph
            graph = ConfigGraph()
            graph.build_from_xml(xml_config.tree)
            
            # Prepare query with RETURN clause if not present
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter
            
            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)
            
            # Extract matching object names
            matching_objects = []
            for row in results:
                if "a.name" in row:
                    matching_objects.append(row["a.name"])
                elif len(row) == 1:
                    matching_objects.append(list(row.values())[0])
            
            # Filter objects
            filtered_objects = {}
            for name in matching_objects:
                if name in objects:
                    filtered_objects[name] = objects[name]
            
            logger.info(f"Query matched {len(filtered_objects)} out of {len(objects)} objects")
            return filtered_objects
            
        except Exception as e:
            log_structured(
                f"Query filtering failed: {str(e)}",
                "error",
                query=query_filter,
                object_type=object_type,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            raise PANFlowError(f"Query filtering failed: {str(e)}")

    @staticmethod
    def format_objects_output(
        objects: Union[Dict[str, Any], List[Dict[str, Any]]],
        output_format: str = "json",
        output_file: Optional[str] = None,
        object_type: Optional[str] = None,
        table_title: Optional[str] = None,
    ) -> None:
        """
        Format and output objects with enhanced formatting options.
        
        This consolidates the output formatting patterns and supports all formats
        consistently across commands.
        """
        # Convert dict to list format if needed
        if isinstance(objects, dict):
            object_list = []
            for name, properties in objects.items():
                obj = {"name": name}
                if isinstance(properties, dict):
                    obj.update(properties)
                else:
                    obj["properties"] = properties
                object_list.append(obj)
        else:
            object_list = objects

        # Use the enhanced formatting
        if output_format.lower() == "table":
            EnhancedCommandBase._format_table_output(
                object_list, object_type, table_title, output_file
            )
        elif output_format.lower() == "csv":
            EnhancedCommandBase._format_csv_output(object_list, output_file)
        elif output_format.lower() == "yaml":
            EnhancedCommandBase._format_yaml_output(object_list, output_file)
        elif output_format.lower() == "html":
            EnhancedCommandBase._format_html_output(
                object_list, object_type, table_title, output_file
            )
        elif output_format.lower() in ["text", "txt"]:
            EnhancedCommandBase._format_text_output(object_list, object_type, output_file)
        else:  # Default to JSON
            EnhancedCommandBase._format_json_output(object_list, output_file)

    @staticmethod
    def _format_table_output(
        object_list: List[Dict[str, Any]],
        object_type: Optional[str],
        table_title: Optional[str],
        output_file: Optional[str],
    ) -> None:
        """Format objects as a rich table."""
        if not object_list:
            console.print(f"No {object_type or 'objects'} found")
            return

        title = table_title or f"{(object_type or 'Objects').capitalize()}"
        table = Table(title=title)

        # Add name column first
        table.add_column("name", style="bold")

        # Add type-specific columns
        if object_type == "address":
            for key in ["ip-netmask", "ip-range", "fqdn", "description"]:
                if any(key in obj for obj in object_list):
                    table.add_column(key)
        elif object_type == "service":
            for key in ["protocol", "port", "source-port", "dest-port", "description"]:
                if any(key in obj for obj in object_list):
                    table.add_column(key)
        elif object_type and "group" in object_type:
            table.add_column("members")
            table.add_column("description")
        else:
            # Auto-detect columns from data
            all_keys = set()
            for obj in object_list:
                all_keys.update(obj.keys())
            all_keys.discard("name")  # Already added
            for key in sorted(all_keys):
                table.add_column(key)

        # Add rows
        for obj in object_list:
            values = []
            for column in table.columns:
                header = column.header
                if header == "members" and "static" in obj:
                    # Special handling for group members
                    if isinstance(obj["static"], list):
                        values.append(str(len(obj["static"])))
                    else:
                        values.append(str(obj.get("static", "")))
                else:
                    values.append(str(obj.get(header, "")))
            table.add_row(*values)

        if output_file:
            # For file output, convert to plain text
            with open(output_file, "w") as f:
                # Simple text table format for file output
                headers = [col.header for col in table.columns]
                f.write(" | ".join(headers) + "\n")
                f.write("-" * (len(" | ".join(headers))) + "\n")
                for obj in object_list:
                    values = [str(obj.get(h, "")) for h in headers]
                    f.write(" | ".join(values) + "\n")
            console.print(f"Table output saved to [blue]{output_file}[/blue]")
        else:
            console.print(table)

    @staticmethod
    def _format_csv_output(object_list: List[Dict[str, Any]], output_file: Optional[str]) -> None:
        """Format objects as CSV."""
        if not object_list:
            if output_file:
                with open(output_file, "w") as f:
                    f.write("No data\n")
            else:
                console.print("No data")
            return

        import csv
        import io

        output_stream = io.StringIO()
        
        # Get all fields for headers
        fields = set(["name"])
        for obj in object_list:
            fields.update(obj.keys())

        writer = csv.DictWriter(output_stream, fieldnames=sorted(list(fields)))
        writer.writeheader()
        for obj in object_list:
            writer.writerow(obj)

        csv_output = output_stream.getvalue()

        if output_file:
            with open(output_file, "w") as f:
                f.write(csv_output)
            console.print(f"CSV output saved to [blue]{output_file}[/blue]")
        else:
            console.print(csv_output)

    @staticmethod
    def _format_yaml_output(object_list: List[Dict[str, Any]], output_file: Optional[str]) -> None:
        """Format objects as YAML."""
        try:
            import yaml
            yaml_output = yaml.dump(object_list, sort_keys=False, default_flow_style=False)
            
            if output_file:
                with open(output_file, "w") as f:
                    f.write(yaml_output)
                console.print(f"YAML output saved to [blue]{output_file}[/blue]")
            else:
                console.print(yaml_output)
        except ImportError:
            console.print("[red]YAML output requires PyYAML package[/red]")

    @staticmethod
    def _format_html_output(
        object_list: List[Dict[str, Any]],
        object_type: Optional[str],
        table_title: Optional[str],
        output_file: Optional[str],
    ) -> None:
        """Format objects as HTML table."""
        if not object_list:
            html_output = "<p>No data found</p>"
        else:
            title = table_title or f"{(object_type or 'Objects').capitalize()}"
            
            # Build HTML table
            html_parts = [
                f"<h2>{title}</h2>",
                "<table border='1' cellpadding='5' cellspacing='0'>",
                "<thead><tr>",
            ]
            
            # Headers
            headers = ["name"] + [k for k in object_list[0].keys() if k != "name"]
            for header in headers:
                html_parts.append(f"<th>{header}</th>")
            html_parts.append("</tr></thead><tbody>")
            
            # Rows
            for obj in object_list:
                html_parts.append("<tr>")
                for header in headers:
                    value = str(obj.get(header, ""))
                    html_parts.append(f"<td>{value}</td>")
                html_parts.append("</tr>")
            
            html_parts.extend(["</tbody></table>"])
            html_output = "\n".join(html_parts)

        if output_file:
            with open(output_file, "w") as f:
                f.write(html_output)
            console.print(f"HTML output saved to [blue]{output_file}[/blue]")
        else:
            console.print(html_output)

    @staticmethod
    def _format_text_output(
        object_list: List[Dict[str, Any]], 
        object_type: Optional[str], 
        output_file: Optional[str]
    ) -> None:
        """Format objects as plain text."""
        if not object_list:
            text_output = f"No {object_type or 'objects'} found"
        else:
            lines = []
            for obj in object_list:
                lines.append(f"Name: {obj.get('name', 'Unknown')}")
                for key, value in obj.items():
                    if key != "name":
                        lines.append(f"  {key}: {value}")
                lines.append("")  # Empty line between objects
            text_output = "\n".join(lines)

        if output_file:
            with open(output_file, "w") as f:
                f.write(text_output)
            console.print(f"Text output saved to [blue]{output_file}[/blue]")
        else:
            console.print(text_output)

    @staticmethod
    def _format_json_output(object_list: List[Dict[str, Any]], output_file: Optional[str]) -> None:
        """Format objects as JSON."""
        json_output = json.dumps(object_list, indent=2)
        
        if output_file:
            with open(output_file, "w") as f:
                f.write(json_output)
            console.print(f"JSON output saved to [blue]{output_file}[/blue]")
        else:
            console.print(json_output)


def enhanced_command_handler(func: F) -> F:
    """
    Decorator that provides enhanced command handling with standardized patterns.
    
    This decorator consolidates the common error handling, logging, and 
    feature flag patterns found across CLI commands.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if enhanced command base is enabled
            if is_enabled("use_enhanced_command_base"):
                logger.info(f"Using enhanced command base for {func.__name__}")
                return func(*args, **kwargs)
            else:
                # Fallback to original implementation
                logger.info(f"Using legacy implementation for {func.__name__}")
                # This would call the original function
                # For now, we'll use the enhanced version as the implementation
                return func(*args, **kwargs)
                
        except PANFlowError as e:
            # Structured error logging
            log_structured(
                f"Command failed: {str(e)}",
                "error",
                command=func.__name__,
                error=str(e),
            )
            console.print(f"[red]Error: {str(e)}[/red]")
            raise typer.Exit(1)
            
        except Exception as e:
            # Unexpected error logging
            log_structured(
                f"Unexpected error in command: {str(e)}",
                "error",
                command=func.__name__,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            if logger.level <= logging.DEBUG:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1)
    
    return wrapper


def object_command_handler(func: F) -> F:
    """
    Specialized decorator for object commands that handles object type aliases
    and provides object-specific functionality.
    """
    @enhanced_command_handler
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Handle object type aliases if present
        if "object_type" in kwargs:
            object_type = kwargs["object_type"]
            actual_object_type = OBJECT_TYPE_ALIASES.get(object_type, object_type)
            if actual_object_type != object_type:
                logger.info(f"Resolved object type alias '{object_type}' to '{actual_object_type}'")
                kwargs["object_type"] = actual_object_type
        
        return func(*args, **kwargs)
    
    return wrapper