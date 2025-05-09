"""
Common CLI options and callbacks for PANFlow.

This module provides reusable option classes and callbacks for CLI commands.
"""

import os
import typer
from typing import Optional, Callable, TypeVar, Any, List, Dict
from functools import wraps
from pathlib import Path

from panflow.core.logging_utils import (
    verbose_callback, quiet_callback, log_level_callback, log_file_callback
)
from panflow.core.conflict_resolver import ConflictStrategy

# Import autocompletion functions
from .app import (
    complete_config_files,
    complete_object_types,
    complete_policy_types,
    complete_context_types,
    complete_output_formats
)

# Type variable for callback return type
T = TypeVar('T')

class CommonOptions:
    """Base class for common command options."""
    
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.log_level = "info"
        self.log_file = None
        
    @staticmethod
    def apply_to_app(app: typer.Typer):
        """Apply common options to the application."""
        @app.callback()
        def callback(
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output", callback=verbose_callback),
            quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress console output", callback=quiet_callback),
            log_level: str = typer.Option("info", "--log-level", "-l", help="Set log level (debug, info, warning, error, critical)", callback=log_level_callback),
            log_file: Optional[str] = typer.Option(None, "--log-file", "-f", help="Log to file", callback=log_file_callback),
        ):
            """PANFlow Utilities CLI"""
            # Configure logging (done by callbacks)
            pass

class ConfigOptions:
    """Options for configuration file operations."""
    
    @staticmethod
    def config_file():
        """Option for configuration file."""
        return typer.Option(
            ..., "--config", "-c",
            help="Path to XML configuration file",
            autocompletion=complete_config_files
        )

    @staticmethod
    def output_file():
        """Option for output file."""
        return typer.Option(
            ..., "--output", "-o",
            help="Output file for updated configuration",
            autocompletion=complete_config_files
        )

    @staticmethod
    def device_type():
        """
        Option for device type with auto-detection.

        When not specified, the device type will be automatically detected based on
        the XML structure of the configuration file.
        """
        return typer.Option(
            None, "--device-type", "-d",
            help="Device type (firewall or panorama, auto-detected if not specified)",
            autocompletion=lambda: ["firewall", "panorama"]
        )

    @staticmethod
    def version():
        """Option for PAN-OS version."""
        return typer.Option(
            None, "--version",
            help="PAN-OS version (auto-detected if not specified)",
            autocompletion=lambda: ["10.1", "10.2", "11.0", "11.1", "11.2"]
        )

    @staticmethod
    def dry_run():
        """Option for dry run mode."""
        return typer.Option(
            False, "--dry-run",
            help="Preview changes without modifying the target configuration"
        )

class ContextOptions:
    """Options for context selection."""

    @staticmethod
    def context_type():
        """Option for context type."""
        return typer.Option(
            "shared", "--context",
            help="Context (shared, device_group, vsys, template)",
            autocompletion=complete_context_types
        )

    @staticmethod
    def device_group():
        """Option for device group."""
        return typer.Option(
            None, "--device-group",
            help="Device group name (for Panorama device_group context)"
            # Note: We could add dynamic completion based on loaded config here
        )

    @staticmethod
    def vsys():
        """Option for vsys."""
        return typer.Option(
            "vsys1", "--vsys",
            help="VSYS name (for firewall vsys context)",
            autocompletion=lambda: ["vsys1", "vsys2", "vsys3"]
        )

    @staticmethod
    def template():
        """Option for template."""
        return typer.Option(
            None, "--template",
            help="Template name (for Panorama template context)"
            # Note: We could add dynamic completion based on loaded config here
        )
    
    @staticmethod
    def get_context_kwargs(context_type: str, device_group: Optional[str], vsys: str, template: Optional[str]) -> Dict[str, str]:
        """
        Get context keyword arguments based on context type.
        
        Args:
            context_type: Type of context (shared, device_group, vsys, template)
            device_group: Device group name
            vsys: VSYS name
            template: Template name
            
        Returns:
            Dictionary of context keyword arguments
        """
        context_kwargs = {}
        
        if context_type == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context_type == "vsys":
            context_kwargs["vsys"] = vsys
        elif context_type == "template" and template:
            context_kwargs["template"] = template
            
        return context_kwargs

class MergeOptions:
    """Options for merge operations."""
    
    @staticmethod
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
            
        # If value is already a ConflictStrategy enum, just return it
        if isinstance(value, ConflictStrategy):
            return value
            
        # Handle case where the input is a ConflictStrategy enum string
        if isinstance(value, str) and value.startswith('ConflictStrategy.'):
            try:
                # Extract the enum name (e.g., 'SKIP' from 'ConflictStrategy.SKIP')
                enum_name = value.split('.')[1]
                # Convert to lowercase to match the enum values
                value = enum_name.lower()
            except Exception:
                pass
            
        valid_strategies = [s.value for s in ConflictStrategy]
        
        # Try case-insensitive match first
        if isinstance(value, str):
            value_lower = value.lower()
            for strategy in valid_strategies:
                if strategy.lower() == value_lower:
                    return ConflictStrategy(strategy)
                
        # If no match found, raise error
        strategies_str = ", ".join(valid_strategies)
        raise typer.BadParameter(
            f"Invalid conflict strategy: '{value}'. Valid options are: {strategies_str}"
        )
    
    @staticmethod
    def conflict_strategy():
        """Option for conflict strategy."""
        return typer.Option(
            "skip", "--conflict-strategy", 
            help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source",
            callback=MergeOptions.conflict_strategy_callback
        )
    
    @staticmethod
    def copy_references():
        """Option for copying references."""
        return typer.Option(
            True, "--copy-references/--no-copy-references", 
            help="Copy object references"
        )

class ObjectOptions:
    """Options for object operations."""

    @staticmethod
    def object_type():
        """Option for object type."""
        return typer.Option(
            ..., "--type", "-t",
            help="Type of object (address, service, etc.)",
            autocompletion=complete_object_types
        )

    @staticmethod
    def object_name():
        """Option for object name."""
        return typer.Option(
            ..., "--name", "-n",
            help="Name of the object"
            # Dynamic completion based on loaded config and object type
        )

class PolicyOptions:
    """Options for policy operations."""

    @staticmethod
    def policy_type():
        """Option for policy type."""
        return typer.Option(
            ..., "--type", "-t",
            help="Type of policy (security_pre_rules, nat_rules, etc.)",
            autocompletion=complete_policy_types
        )

    @staticmethod
    def policy_name():
        """Option for policy name."""
        return typer.Option(
            ..., "--name", "-n",
            help="Name of the policy"
            # Dynamic completion based on loaded config and policy type
        )

    @staticmethod
    def position():
        """Option for policy position."""
        return typer.Option(
            "bottom", "--position",
            help="Position to add policy (top, bottom, before, after)",
            autocompletion=lambda: ["top", "bottom", "before", "after"]
        )

    @staticmethod
    def ref_policy():
        """Option for reference policy."""
        return typer.Option(
            None, "--ref-policy",
            help="Reference policy for before/after position"
            # Dynamic completion based on loaded config and policy type
        )

# File and output related callbacks
def file_callback(value: str) -> str:
    """
    Validate that the specified file exists.
    
    Args:
        value: The file path
        
    Returns:
        The validated file path
        
    Raises:
        typer.BadParameter: If the file does not exist
    """
    if not os.path.exists(value):
        raise typer.BadParameter(f"File does not exist: {value}")
    return value


def output_callback(value: str) -> str:
    """
    Validate that the output format is supported.

    Args:
        value: The output format

    Returns:
        The validated output format

    Raises:
        typer.BadParameter: If the output format is not supported
    """
    supported_formats = complete_output_formats()
    if value not in supported_formats:
        formats_str = ", ".join(supported_formats)
        raise typer.BadParameter(f"Output format '{value}' not supported. Valid formats: {formats_str}")
    return value


# Helper function to create a common options decorator
def common_options(f):
    """Decorator to apply common options to a command."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    
    return wrapper