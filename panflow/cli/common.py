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
    verbose_callback,
    quiet_callback,
    log_level_callback,
    log_file_callback,
)
from panflow.core.conflict_resolver import ConflictStrategy

# Import autocompletion functions from dedicated module
from .completions import (
    complete_config_files,
    complete_object_types,
    complete_policy_types,
    complete_context_types,
    complete_output_formats,
)

# Type variable for callback return type
T = TypeVar("T")


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
            verbose: bool = typer.Option(
                False, "--verbose", "-v", help="Enable verbose output", callback=verbose_callback
            ),
            quiet: bool = typer.Option(
                False, "--quiet", "-q", help="Suppress console output", callback=quiet_callback
            ),
            log_level: str = typer.Option(
                "info",
                "--log-level",
                "-l",
                help="Set log level (debug, info, warning, error, critical)",
                callback=log_level_callback,
            ),
            log_file: Optional[str] = typer.Option(
                None, "--log-file", "-f", help="Log to file", callback=log_file_callback
            ),
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
            ...,
            "--config",
            "-c",
            help="Path to XML configuration file",
            autocompletion=complete_config_files,
        )

    @staticmethod
    def output_file():
        """Option for output file."""
        return typer.Option(
            ...,
            "--output",
            "-o",
            help="Output file for updated configuration",
            autocompletion=complete_config_files,
        )

    @staticmethod
    def device_type():
        """
        Option for device type with auto-detection.

        When not specified, the device type will be automatically detected based on
        the XML structure of the configuration file.
        """
        return typer.Option(
            None,
            "--device-type",
            "-d",
            help="Device type (firewall or panorama, auto-detected if not specified)",
            autocompletion=lambda: ["firewall", "panorama"],
        )

    @staticmethod
    def version():
        """Option for PAN-OS version."""
        return typer.Option(
            None,
            "--version",
            help="PAN-OS version (auto-detected if not specified)",
            autocompletion=lambda: ["10.1", "10.2", "11.0", "11.1", "11.2"],
        )

    @staticmethod
    def dry_run():
        """Option for dry run mode."""
        return typer.Option(
            False, "--dry-run", help="Preview changes without modifying the target configuration"
        )


class ContextOptions:
    """Options for context selection."""

    @staticmethod
    def context_type():
        """Option for context type."""
        return typer.Option(
            "shared",
            "--context",
            help="Context to search in. 'shared' (default) searches the ENTIRE configuration including all device groups/vsys. Use 'device_group' or 'vsys' to limit scope to a specific context.",
            autocompletion=complete_context_types,
        )

    @staticmethod
    def device_group():
        """Option for device group."""
        return typer.Option(
            None,
            "--device-group",
            help="Device group name (for Panorama device_group context)"
            # Note: We could add dynamic completion based on loaded config here
        )

    @staticmethod
    def vsys():
        """Option for vsys."""
        return typer.Option(
            "vsys1",
            "--vsys",
            help="VSYS name (for firewall vsys context)",
            autocompletion=lambda: ["vsys1", "vsys2", "vsys3"],
        )

    @staticmethod
    def template():
        """Option for template."""
        return typer.Option(
            None,
            "--template",
            help="Template name (for Panorama template context)"
            # Note: We could add dynamic completion based on loaded config here
        )

    @staticmethod
    def get_context_kwargs(
        context_type: str, device_group: Optional[str], vsys: str, template: Optional[str]
    ) -> Dict[str, str]:
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
        if isinstance(value, str) and value.startswith("ConflictStrategy."):
            try:
                # Extract the enum name (e.g., 'SKIP' from 'ConflictStrategy.SKIP')
                enum_name = value.split(".")[1]
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
            "skip",
            "--conflict-strategy",
            help="Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source",
            callback=MergeOptions.conflict_strategy_callback,
        )

    @staticmethod
    def copy_references():
        """Option for copying references."""
        return typer.Option(
            True, "--copy-references/--no-copy-references", help="Copy object references"
        )


class ObjectOptions:
    """Options for object operations."""

    @staticmethod
    def object_type():
        """Option for object type."""
        return typer.Option(
            ...,
            "--type",
            "-t",
            help="Type of object (address, service, etc.)",
            autocompletion=complete_object_types,
        )

    @staticmethod
    def object_name():
        """Option for object name."""
        return typer.Option(
            ...,
            "--name",
            "-n",
            help="Name of the object"
            # Dynamic completion based on loaded config and object type
        )


class PolicyOptions:
    """Options for policy operations."""

    @staticmethod
    def policy_type():
        """Option for policy type."""
        return typer.Option(
            ...,
            "--type",
            "-t",
            help="Type of policy (security_pre_rules, nat_rules, etc.)",
            autocompletion=complete_policy_types,
        )

    @staticmethod
    def policy_name():
        """Option for policy name."""
        return typer.Option(
            ...,
            "--name",
            "-n",
            help="Name of the policy"
            # Dynamic completion based on loaded config and policy type
        )

    @staticmethod
    def position():
        """Option for policy position."""
        return typer.Option(
            "bottom",
            "--position",
            help="Position to add policy (top, bottom, before, after)",
            autocompletion=lambda: ["top", "bottom", "before", "after"],
        )

    @staticmethod
    def ref_policy():
        """Option for reference policy."""
        return typer.Option(
            None,
            "--ref-policy",
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
        raise typer.BadParameter(
            f"Output format '{value}' not supported. Valid formats: {formats_str}"
        )
    return value


# Helper function to create a common options decorator
def common_options(f):
    """Decorator to apply common options to a command."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


def format_policy_for_display(policy):
    """
    Create a consistently formatted string representation of a policy for display.

    Args:
        policy: Dictionary containing policy properties

    Returns:
        str: Formatted string for display
    """
    name = policy.get("name", "unnamed")

    # Build a rich info string with key details
    policy_info = []

    # Get action with color-coded indicator
    if "action" in policy:
        action = policy["action"].lower()
        if action == "allow":
            policy_info.append(f"action:allow")
        elif action in ["deny", "drop", "reset-client", "reset-server", "reset-both"]:
            policy_info.append(f"action:{action}")
        else:
            policy_info.append(f"action:{action}")

    # Check if policy is disabled
    if policy.get("disabled") == "yes":
        policy_info.append("DISABLED")

    # Get from/to zones if present
    if "from" in policy and isinstance(policy["from"], list):
        zones_from = ", ".join(policy["from"][:3])
        if len(policy["from"]) > 3:
            zones_from += f"... (+{len(policy['from']) - 3} more)"
        policy_info.append(f"from:[{zones_from}]")

    if "to" in policy and isinstance(policy["to"], list):
        zones_to = ", ".join(policy["to"][:3])
        if len(policy["to"]) > 3:
            zones_to += f"... (+{len(policy['to']) - 3} more)"
        policy_info.append(f"to:[{zones_to}]")

    # Get sources
    if "source" in policy and isinstance(policy["source"], list):
        src_count = len(policy["source"])
        src_preview = ", ".join(policy["source"][:3])
        if src_count > 3:
            src_preview += f"... (+{src_count - 3} more)"
        policy_info.append(f"src:[{src_preview}]")

    # Get destinations
    if "destination" in policy and isinstance(policy["destination"], list):
        dst_count = len(policy["destination"])
        dst_preview = ", ".join(policy["destination"][:3])
        if dst_count > 3:
            dst_preview += f"... (+{dst_count - 3} more)"
        policy_info.append(f"dst:[{dst_preview}]")

    # Get services
    if "service" in policy and isinstance(policy["service"], list):
        svc_count = len(policy["service"])
        svc_preview = ", ".join(policy["service"][:2])
        if svc_count > 2:
            svc_preview += f"... (+{svc_count - 2} more)"
        policy_info.append(f"svc:[{svc_preview}]")

    # Add application info if present
    if "application" in policy and isinstance(policy["application"], list):
        app_count = len(policy["application"])
        app_preview = ", ".join(policy["application"][:2])
        if app_count > 2:
            app_preview += f"... (+{app_count - 2} more)"
        policy_info.append(f"app:[{app_preview}]")

    # Add log settings
    if "log_start" in policy and policy["log_start"] == "yes":
        policy_info.append("log-start")
    if "log_end" in policy and policy["log_end"] == "yes":
        policy_info.append("log-end")

    # Add profile settings if present
    if "profile_setting" in policy:
        profiles = []
        profile_setting = policy["profile_setting"]

        # Extract profile types
        if isinstance(profile_setting, dict):
            for profile_type in [
                "antivirus",
                "vulnerability",
                "spyware",
                "url_filtering",
                "file_blocking",
                "data_filtering",
                "wildfire_analysis",
            ]:
                if profile_type in profile_setting and profile_setting[profile_type]:
                    profiles.append(f"{profile_type.replace('_', '-')}")

        if profiles:
            policy_info.append(f"profiles:[{', '.join(profiles[:2])}]")

    # Add description if present (shortened if too long)
    if "description" in policy and policy["description"]:
        desc = policy["description"]
        if len(desc) > 30:
            desc = desc[:30] + "..."
        policy_info.append(f"desc:'{desc}'")

    # Format for display
    if policy_info:
        return f"{name}: {' | '.join(policy_info)}"
    else:
        return name


def format_object_for_display(obj):
    """
    Create a consistently formatted string representation of an object for display.

    Args:
        obj: Dictionary containing object properties

    Returns:
        str: Formatted string for display
    """
    name = obj.get("name", "unnamed")

    # Build a rich info string with key details
    obj_info = []

    # Address objects
    if "ip-netmask" in obj:
        obj_info.append(f"ip:{obj['ip-netmask']}")
    elif "ip-range" in obj:
        obj_info.append(f"range:{obj['ip-range']}")
    elif "fqdn" in obj:
        obj_info.append(f"fqdn:{obj['fqdn']}")

    # Service objects
    if "protocol" in obj:
        protocol = obj["protocol"]
        if protocol == "tcp" or protocol == "udp":
            ports = []
            if "source-port" in obj:
                ports.append(f"src-port:{obj['source-port']}")
            if "dest-port" in obj:
                ports.append(f"dst-port:{obj['dest-port']}")
            if ports:
                obj_info.append(f"{protocol}:{'/'.join(ports)}")
            else:
                obj_info.append(f"{protocol}")
        else:
            obj_info.append(f"{protocol}")

    # Tags
    if "tag" in obj and isinstance(obj["tag"], list):
        tags = obj["tag"][:3]
        if len(obj["tag"]) > 3:
            tags.append(f"... (+{len(obj['tag']) - 3} more)")
        obj_info.append(f"tags:[{', '.join(tags)}]")

    # Description if present
    if "description" in obj and obj["description"]:
        desc = obj["description"]
        if len(desc) > 25:  # Truncate long descriptions
            desc = desc[:25] + "..."
        obj_info.append(f"desc:'{desc}'")
    
    # Add context information if available
    if "context" in obj:
        obj_info.append(f"context:{obj['context']}")
    elif "context_name" in obj:
        if "context_type" in obj and obj["context_type"] == "device_group":
            obj_info.append(f"context:Device Group: {obj['context_name']}")
        elif "context_type" in obj and obj["context_type"] == "vsys":
            obj_info.append(f"context:VSYS: {obj['context_name']}")
        else:
            obj_info.append(f"context:{obj['context_name']}")

    # Format for display
    if obj_info:
        return f"{name}: {' | '.join(obj_info)}"
    else:
        return name


def format_objects_list(objects, include_header=True, object_type=None, count=None, grouped=False):
    """
    Create a consistently formatted list of objects for display.

    Args:
        objects: List of object dictionaries
        include_header: Whether to include a header line
        object_type: Optional object type for the header
        count: Optional count override
        grouped: Whether objects should be grouped by value (for duplicates)

    Returns:
        list: List of strings for display
    """
    result = []

    # Add header if requested
    if include_header:
        count = count or len(objects)
        object_type_str = f" {object_type}" if object_type else ""
        result.append(f"Found {count}{object_type_str} objects:")

    # Check if we need to group objects (for duplicates)
    if grouped and isinstance(objects, list) and len(objects) > 0:
        # For grouped display, assume objects are already grouped
        for obj in objects:
            formatted = format_object_for_display(obj)
            result.append(f"  - {formatted}")
    elif grouped and isinstance(objects, dict):
        # If objects is a dictionary of duplicate groups
        for value, group_objects in objects.items():
            if value.startswith('_'):  # Skip internal fields
                continue
                
            # Format the value key
            if ':' in value:
                parts = value.split(':', 1)
                value_display = f"{parts[0].capitalize()}: {parts[1]}"
            else:
                value_display = value
                
            result.append(f"Group: {value_display} ({len(group_objects)} objects)")
            
            # Format each object in the group with proper indentation
            for obj in group_objects:
                name = obj.get('name', 'unnamed')
                
                # Add context information if available
                context = ""
                if 'context' in obj:
                    context = f" - {obj['context']}"
                elif 'context_type' in obj:
                    if obj['context_type'] == 'device_group' and 'context_name' in obj:
                        context = f" - Device Group: {obj['context_name']}"
                    elif obj['context_type'] == 'vsys' and 'context_name' in obj:
                        context = f" - VSYS: {obj['context_name']}"
                    elif obj['context_type'] == 'shared':
                        context = " - Shared"
                        
                result.append(f"    * {name}{context}")
            
            # Add an extra line between groups for readability
            result.append("")
    else:
        # Regular non-grouped format
        for obj in objects:
            formatted = format_object_for_display(obj)
            result.append(f"  - {formatted}")

    return result

def format_duplicate_objects_list(duplicates, include_header=True, object_type=None):
    """
    Create a consistently formatted list of duplicate objects for display,
    grouped by their values.

    Args:
        duplicates: Dictionary mapping values to lists of duplicate objects
        include_header: Whether to include a header line
        object_type: Optional object type for the header

    Returns:
        list: List of strings for display
    """
    result = []
    
    # Count total duplicates and unique values
    total_duplicates = sum(len(objects) - 1 for objects in duplicates.values() 
                          if not isinstance(objects, dict) and not str(objects).startswith('_'))
    unique_values = len([k for k in duplicates.keys() if not str(k).startswith('_')])
    
    # Add header if requested
    if include_header:
        object_type_str = f" {object_type}" if object_type else ""
        result.append(f"Found {total_duplicates} duplicate{object_type_str} objects across {unique_values} unique values:")
    
    # Format each group of duplicates
    return result + format_objects_list(duplicates, include_header=False, grouped=True)


def format_policies_list(policies, include_header=True, policy_type=None, count=None):
    """
    Create a consistently formatted list of policies for display.

    Args:
        policies: List of policy dictionaries
        include_header: Whether to include a header line
        policy_type: Optional policy type for the header
        count: Optional count override

    Returns:
        list: List of strings for display
    """
    result = []

    # Add header if requested
    if include_header:
        count = count or len(policies)
        policy_type_str = f" {policy_type}" if policy_type else ""
        result.append(f"Found {count}{policy_type_str} policies:")

    # Format each policy
    for policy in policies:
        formatted = format_policy_for_display(policy)
        result.append(f"  - {formatted}")

    return result
