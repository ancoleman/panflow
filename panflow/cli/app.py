"""
Main CLI application for PANFlow.

This module provides the main Typer application and command group registration.
"""

import sys
import platform
import logging
import os
from pathlib import Path
from lxml import etree
import typer
from typing import List, Optional

from panflow.core.logging_utils import configure_logging

# Import completions from the dedicated module
from .completions import (
    complete_config_files,
    complete_object_types,
    complete_policy_types,
    complete_context_types,
    complete_output_formats,
)
from .common import CommonOptions

# Create main Typer app with auto-completion support
app = typer.Typer(
    help="PANFlow CLI",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Create command groups with auto-completion
object_app = typer.Typer(
    help="Object management commands",
    add_completion=True,
    no_args_is_help=True,
)
policy_app = typer.Typer(
    help="Policy management commands",
    add_completion=True,
    no_args_is_help=True,
)
group_app = typer.Typer(
    help="Group management commands",
    add_completion=True,
    no_args_is_help=True,
)
report_app = typer.Typer(
    help="Report generation commands",
    add_completion=True,
    no_args_is_help=True,
)
config_app = typer.Typer(
    help="Configuration management commands",
    add_completion=True,
    no_args_is_help=True,
)
merge_app = typer.Typer(
    help="Policy and Object merge commands",
    add_completion=True,
    no_args_is_help=True,
)

# Import the query commands app directly
from panflow.cli.commands.query_commands import app as query_app

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

# Apply common options to the app
CommonOptions.apply_to_app(app)

# Let's use a clean approach to logging
# We'll set up logging once in the main file
import logging

# Clear all existing handlers to avoid duplication
panflow_logger = logging.getLogger("panflow")
for handler in panflow_logger.handlers[:]:
    panflow_logger.removeHandler(handler)

# Set up a single handler for the panflow logger
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
panflow_logger.addHandler(handler)
panflow_logger.setLevel(logging.INFO)


# ===== Exception Handler =====
def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for unhandled exceptions.
    Provides more user-friendly error messages for common issues.
    """
    from panflow import (
        PANFlowError,
        ConfigError,
        ValidationError,
        ParseError,
        XPathError,
        ContextError,
        ObjectError,
        ObjectNotFoundError,
        ObjectExistsError,
        PolicyError,
        PolicyNotFoundError,
        PolicyExistsError,
        MergeError,
        ConflictError,
        VersionError,
        FileOperationError,
        BulkOperationError,
        SecurityError,
    )

    # Handle PANFlow exceptions
    if isinstance(exc_value, PANFlowError):
        if isinstance(exc_value, ObjectNotFoundError):
            logger.error(f"Object not found: {exc_value}")
        elif isinstance(exc_value, PolicyNotFoundError):
            logger.error(f"Policy not found: {exc_value}")
        elif isinstance(exc_value, ValidationError):
            logger.error(f"Validation error: {exc_value}")
        elif isinstance(exc_value, ParseError):
            logger.error(f"XML parsing error: {exc_value}")
        elif isinstance(exc_value, SecurityError):
            logger.error(f"Security error: {exc_value}")
        elif isinstance(exc_value, ConflictError):
            logger.error(f"Conflict error: {exc_value}")
        else:
            logger.error(f"{exc_type.__name__}: {exc_value}")
        sys.exit(1)
    # Handle other common exceptions
    elif isinstance(exc_value, FileNotFoundError):
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


# Set up the global exception handler
sys.excepthook = _global_exception_handler

# Note: Individual command modules will register themselves
# Do not import all commands here to avoid circular imports

# The query commands app is already imported above
# No additional imports needed here
