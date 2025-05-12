"""
Common constants for PAN-OS XML utilities.

This module defines constants used throughout the PAN-OS XML utilities,
including namespaces, XPath expressions, default values, and error codes.
"""

from typing import Dict, List, Any, Tuple

# XML Namespaces
NAMESPACES = {
    "xlink": "http://www.w3.org/1999/xlink",
    "pan": "http://paloaltonetworks.com/ns/config",
    "pango": "http://paloaltonetworks.com/ns/config/general",
    "admin": "http://paloaltonetworks.com/ns/config/admin",
    "log": "http://paloaltonetworks.com/ns/log",
    "report": "http://paloaltonetworks.com/ns/report",
}

# Common XPath expressions
XPATH = {
    # Base paths
    "CONFIG_ROOT": "/config",
    "SHARED": "/config/shared",
    "DEVICES": "/config/devices",
    "LOCALHOST": "/config/devices/entry[@name='localhost.localdomain']",
    # Device type paths
    "PANORAMA_DEVICE_GROUPS": "/config/devices/entry[@name='localhost.localdomain']/device-group",
    "PANORAMA_TEMPLATES": "/config/devices/entry[@name='localhost.localdomain']/template",
    "FIREWALL_VSYS": "/config/devices/entry[@name='localhost.localdomain']/vsys",
    # Common object paths - these need to be combined with a base path
    "ADDRESS_OBJECTS": "{base_path}/address/entry",
    "ADDRESS_GROUPS": "{base_path}/address-group/entry",
    "SERVICE_OBJECTS": "{base_path}/service/entry",
    "SERVICE_GROUPS": "{base_path}/service-group/entry",
    "SECURITY_PROFILES": "{base_path}/profiles",
    # Policy paths - these need to be combined with a base path
    "SECURITY_RULES": "{base_path}/rulebase/security/rules/entry",
    "NAT_RULES": "{base_path}/rulebase/nat/rules/entry",
    "PRE_SECURITY_RULES": "{base_path}/pre-rulebase/security/rules/entry",
    "POST_SECURITY_RULES": "{base_path}/post-rulebase/security/rules/entry",
    "PRE_NAT_RULES": "{base_path}/pre-rulebase/nat/rules/entry",
    "POST_NAT_RULES": "{base_path}/post-rulebase/nat/rules/entry",
    # System settings
    "HOSTNAME": "/config/devices/entry[@name='localhost.localdomain']/deviceconfig/system/hostname",
    "INTERFACES": "/config/devices/entry[@name='localhost.localdomain']/network/interface",
}

# Default values
DEFAULT_VALUES = {
    "VSYS": "vsys1",
    "DEVICE_GROUP": "shared",
    "TEMPLATE": "default",
    "SECURITY_RULE_ACTION": "allow",
    "NAT_RULE_TYPE": "ipv4",
    "LOG_SETTING": "default",
    "PROFILE_SETTING": "default",
}

# Error codes and messages
ERROR_CODES = {
    # Parse errors
    1001: "Failed to parse XML file",
    1002: "Invalid XML structure",
    1003: "XML validation failed",
    # XPath errors
    2001: "Invalid XPath expression",
    2002: "XPath evaluation failed",
    2003: "Element not found",
    # Object errors
    3001: "Object already exists",
    3002: "Object not found",
    3003: "Invalid object type",
    3004: "Invalid object properties",
    # Policy errors
    4001: "Policy already exists",
    4002: "Policy not found",
    4003: "Invalid policy type",
    4004: "Invalid policy properties",
    # Configuration errors
    5001: "Failed to save configuration",
    5002: "Failed to backup configuration",
    5003: "Failed to merge configurations",
    # Validation errors
    6001: "Invalid device type",
    6002: "Invalid context type",
    6003: "Missing required parameter",
    # System errors
    9001: "Input/output error",
    9002: "Permission denied",
    9003: "Unexpected error",
}

# API response codes from Palo Alto Networks
API_RESPONSE_CODES = {
    "1": "Unknown command",
    "2": "Internal error",
    "3": "Authentication failed - Invalid credentials or API key",
    "4": "Invalid port number",
    "5": "Invalid parameter value",
    "6": "Parameter not found",
    "7": "Object not present",
    "8": "Object already exists",
    "9": "Unknown operation",
    "10": "Operation not possible in this context",
    "11": "Operation failed",
    "12": "Device not registered with Panorama",
    "13": "A Panorama device package has not been installed",
    "14": "An operation failed due to an API error",
    "15": "Insufficient permissions to perform the operation",
    "16": "Device is not connected to Panorama",
    "17": "Feature is not licensed",
    "18": "Failed to import a file",
    "19": "A commit is in progress",
    "20": "A multi-job is cancelled",
    "21": "An operation is pending on the device",
    "22": "A commit is scheduled",
    "23": "Invalid target IP address",
}

# Configuration file paths
CONFIG_PATHS = {
    "DEFAULT_CONFIG_DIR": "configs",
    "DEFAULT_BACKUP_DIR": "configs/backups",
    "DEFAULT_LOG_DIR": "logs",
    "DEFAULT_SCHEMA_DIR": "schemas",
}

# Content types for API requests
CONTENT_TYPES = {
    "XML": "application/xml",
    "JSON": "application/json",
    "URL_ENCODED": "application/x-www-form-urlencoded",
    "TEXT": "text/plain",
}

# Tag and attribute names
TAG_NAMES = {
    "ENTRY": "entry",
    "MEMBER": "member",
    "NAME": "name",
    "IP_NETMASK": "ip-netmask",
    "IP_RANGE": "ip-range",
    "FQDN": "fqdn",
    "SOURCE": "source",
    "DESTINATION": "destination",
    "SERVICE": "service",
    "ACTION": "action",
    "DESCRIPTION": "description",
    "DISABLED": "disabled",
    "FROM": "from",
    "TO": "to",
    "PROFILE_SETTING": "profile-setting",
}

# Security action constants
SECURITY_ACTIONS = {
    "ALLOW": "allow",
    "DENY": "deny",
    "DROP": "drop",
    "RESET_CLIENT": "reset-client",
    "RESET_SERVER": "reset-server",
    "RESET_BOTH": "reset-both",
}

# Log settings
LOG_SETTINGS = {
    "LOG_START": "log-start",
    "LOG_END": "log-end",
    "LOG_BOTH": "log-both",
    "LOG_NONE": "log-none",
}

# Validation rules and limits
VALIDATION_RULES = {
    "MAX_NAME_LENGTH": 63,
    "MAX_DESCRIPTION_LENGTH": 255,
    "ALLOWED_NAME_CHARS": r"^[a-zA-Z0-9._-]+$",
    "HOSTNAME_FORMAT": r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$",
    "IP_ADDRESS_FORMAT": r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",
    "CIDR_FORMAT": r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(/([0-9]|[1-2][0-9]|3[0-2]))$",
    "FQDN_FORMAT": r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]$",
}

# Device types
DEVICE_TYPES = ["firewall", "panorama"]

# Context types
CONTEXT_TYPES = {"firewall": ["shared", "vsys"], "panorama": ["shared", "device_group", "template"]}

# Object types
OBJECT_TYPES = [
    "address",
    "address_group",
    "service",
    "service_group",
    "application_group",
    "security_profile_group",
    "antivirus_profile",
    "antispyware_profile",
    "vulnerability_profile",
    "wildfire_profile",
    "url_filtering_profile",
    "dns_security_profile",
    "log_forwarding_profile",
    "management_profile",
]

# Policy types by device type
POLICY_TYPES = {
    "firewall": ["security_rules", "nat_rules", "decryption_rules", "authentication_rules"],
    "panorama": [
        "security_pre_rules",
        "security_post_rules",
        "nat_pre_rules",
        "nat_post_rules",
        "decryption_pre_rules",
        "decryption_post_rules",
        "authentication_pre_rules",
        "authentication_post_rules",
    ],
}

# Report types
REPORT_TYPES = ["unused-objects", "duplicate-objects", "security-rule-coverage", "reference-check"]

# PAN-OS versions
PANOS_VERSIONS = ["10.1", "10.2", "11.0", "11.1", "11.2"]

# Default PAN-OS version
DEFAULT_PANOS_VERSION = "11.2"

# XML formatting settings
XML_FORMAT = {"DEFAULT_INDENT": "  ", "PRETTY_PRINT": True, "INCLUDE_XML_DECLARATION": True}


# Function to get PAN-OS version-specific constants
def get_version_constants(version: str) -> Dict[str, Any]:
    """
    Get constants specific to a PAN-OS version.

    Args:
        version: PAN-OS version string (e.g., "10.1")

    Returns:
        Dictionary of version-specific constants
    """
    # Default to using latest version constants
    if version not in PANOS_VERSIONS:
        version = DEFAULT_PANOS_VERSION

    # Version-specific constants would be defined here
    # For now, we'll return an empty dictionary as a placeholder
    return {}
