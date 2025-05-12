"""
Auto-completion functions for PANFlow CLI.

This module provides common auto-completion functions used across the CLI.
"""

import os
from pathlib import Path
from typing import List


# Autocompletion functions for common parameters
def complete_config_files() -> List[Path]:
    """
    Auto-complete configuration file paths.
    Returns XML files in the current directory.
    """
    return [Path(f) for f in os.listdir(".") if f.endswith((".xml", ".XML")) and os.path.isfile(f)]


def complete_object_types() -> List[str]:
    """
    Auto-complete object types.
    """
    return [
        "address",
        "service",
        "address-group",
        "service-group",
        "tag",
        "application",
        "application-group",
        "profile-group",
    ]


def complete_policy_types() -> List[str]:
    """
    Auto-complete policy types.
    """
    return [
        "security_rules",
        "nat_rules",
        "security_pre_rules",
        "security_post_rules",
        "nat_pre_rules",
        "nat_post_rules",
        "qos_rules",
        "decryption_rules",
        "authentication_rules",
        "dos_rules",
        "tunnel_inspection_rules",
        "application_override_rules",
    ]


def complete_context_types() -> List[str]:
    """
    Auto-complete context types.
    """
    return ["shared", "vsys", "device_group", "template"]


def complete_output_formats() -> List[str]:
    """
    Auto-complete output formats.
    """
    return ["json", "yaml", "xml", "html", "csv", "text"]
