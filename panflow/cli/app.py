"""
Main CLI application for PANFlow.

This module provides the main Typer application and command group registration.
"""

import sys
import platform
import logging
from lxml import etree
import typer

from panflow.core.logging_utils import configure_logging
from .common import CommonOptions

# Create main Typer app
app = typer.Typer(help="PANFlow CLI")

# Create command groups
object_app = typer.Typer(help="Object management commands")
policy_app = typer.Typer(help="Policy management commands")
group_app = typer.Typer(help="Group management commands")
report_app = typer.Typer(help="Report generation commands")
config_app = typer.Typer(help="Configuration management commands")
merge_app = typer.Typer(help="Policy and Object merge commands")

# Add sub-apps to main app
app.add_typer(object_app, name="object")
app.add_typer(policy_app, name="policy")
app.add_typer(group_app, name="group")
app.add_typer(report_app, name="report")
app.add_typer(config_app, name="config")
app.add_typer(merge_app, name="merge")

# Get logger
logger = logging.getLogger("panflow")

# Apply common options to the app
CommonOptions.apply_to_app(app)

# ===== Exception Handler =====
def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for unhandled exceptions.
    Provides more user-friendly error messages for common issues.
    """
    from panflow import (
        PANFlowError, ConfigError, ValidationError, ParseError, 
        XPathError, ContextError, ObjectError, ObjectNotFoundError,
        ObjectExistsError, PolicyError, PolicyNotFoundError,
        PolicyExistsError, MergeError, ConflictError, VersionError,
        FileOperationError, BulkOperationError, SecurityError
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