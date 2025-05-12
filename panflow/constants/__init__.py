"""
Constants package for PANFlow utilities.

This package exports constants used throughout the PAN-OS XML utilities,
including namespaces, XPath expressions, and default values.
"""

from .common import (
    # XML Namespaces
    NAMESPACES,
    # XPath expressions
    XPATH,
    # Default values
    DEFAULT_VALUES,
    # Error codes and messages
    ERROR_CODES,
    API_RESPONSE_CODES,
    # Configuration file paths
    CONFIG_PATHS,
    # Content types for API requests
    CONTENT_TYPES,
    # Tag and attribute names
    TAG_NAMES,
    # Security action constants
    SECURITY_ACTIONS,
    # Log settings
    LOG_SETTINGS,
    # Validation rules and limits
    VALIDATION_RULES,
    # Device and context types
    DEVICE_TYPES,
    CONTEXT_TYPES,
    # Object and policy types
    OBJECT_TYPES,
    POLICY_TYPES,
    # Report types
    REPORT_TYPES,
    # PAN-OS versions
    PANOS_VERSIONS,
    DEFAULT_PANOS_VERSION,
    # XML formatting settings
    XML_FORMAT,
    # Helper functions
    get_version_constants,
)

# Define the public API
__all__ = [
    "NAMESPACES",
    "XPATH",
    "DEFAULT_VALUES",
    "ERROR_CODES",
    "API_RESPONSE_CODES",
    "CONFIG_PATHS",
    "CONTENT_TYPES",
    "TAG_NAMES",
    "SECURITY_ACTIONS",
    "LOG_SETTINGS",
    "VALIDATION_RULES",
    "DEVICE_TYPES",
    "CONTEXT_TYPES",
    "OBJECT_TYPES",
    "POLICY_TYPES",
    "REPORT_TYPES",
    "PANOS_VERSIONS",
    "DEFAULT_PANOS_VERSION",
    "XML_FORMAT",
    "get_version_constants",
]
