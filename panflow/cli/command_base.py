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
    ) -> None:
        """
        Format and display or save command output.

        Args:
            data: Data to format
            output_format: Output format (json, table, text, csv, yaml)
            output_file: File to save output to
            table_title: Title for table output
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
