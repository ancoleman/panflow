"""
CLI package for PANFlow.

This module organizes the command-line interface for PANFlow into a modular structure.
"""

from .app import app
from .common import common_options

# Import commands to register them with the CLI
# This must be after importing app to avoid circular imports
from .commands import (
    object_commands,
    merge_commands,
    deduplicate_commands,
    # Import other command modules as they become available
)

# Try to import optional command modules
try:
    from .commands import policy_commands
except ImportError:
    pass
try:
    from .commands import group_commands
except ImportError:
    pass
try:
    from .commands import report_commands
except ImportError:
    pass
try:
    from .commands import config_commands
except ImportError:
    pass
