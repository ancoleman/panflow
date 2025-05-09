"""
Command modules for PANFlow CLI.

This package contains CLI command modules for PANFlow.
Each module registers commands with the main Typer app.
"""

# Import available command modules
# Keep these imports to avoid unused import warnings when importing from parent
from . import object_commands
from . import merge_commands
from . import deduplicate_commands
from . import query_commands
from . import policy_commands
from . import nat_commands
from . import cleanup_commands
from . import nlq_commands

# Optional modules - these may not exist yet
# Will be imported by the parent package as needed
__all__ = [
    "object_commands",
    "merge_commands",
    "deduplicate_commands",
    "policy_commands",
    "nat_commands",
    "cleanup_commands",
    "group_commands",
    "report_commands",
    "config_commands",
    "query_commands",
    "nlq_commands"
]