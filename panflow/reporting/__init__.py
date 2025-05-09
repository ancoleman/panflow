"""
Reporting package for PANFlow.

This package provides reporting functionality for PAN-OS XML configurations,
including policy analysis, object usage reports, and visualization.
"""

import warnings
from typing import Dict, Any, Optional, List, Union
from lxml import etree

# Import the new recommended interfaces first to avoid circular references
from .engine import ReportingEngine

# Define exports from the new implementation for backward compatibility
from .reports.unused_objects import generate_unused_objects_report_data
from .reports.duplicate_objects import generate_duplicate_objects_report_data
from .reports.policy_analysis import generate_security_policy_analysis_data

# Define warning function
def _warn_deprecated_import():
    warnings.warn(
        "Importing directly from panflow.modules.reports or panflow.core.reporting is deprecated. "
        "Use panflow.reporting instead.",
        DeprecationWarning,
        stacklevel=2
    )

# Function definitions for backward compatibility
def generate_unused_objects_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    object_type: str = "address",
    **kwargs
) -> Dict[str, Any]:
    """
    DEPRECATED: Use ReportingEngine instead.
    Generate a report of unused objects in the configuration.
    """
    _warn_deprecated_import()
    engine = ReportingEngine(tree, device_type, context_type, version)
    return engine.generate_unused_objects_report(
        object_type=object_type, output_file=output_file, **kwargs
    )

def generate_duplicate_objects_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    DEPRECATED: Use ReportingEngine instead.
    Generate a report of duplicate objects in the configuration.
    """
    _warn_deprecated_import()
    engine = ReportingEngine(tree, device_type, context_type, version)
    return engine.generate_duplicate_objects_report(
        output_file=output_file, **kwargs
    )

def generate_security_rule_coverage_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    DEPRECATED: Use ReportingEngine instead.
    Generate a report of security rule coverage.
    """
    _warn_deprecated_import()
    engine = ReportingEngine(tree, device_type, context_type, version)
    return engine.generate_security_rule_coverage_report(
        output_file=output_file, **kwargs
    )

def generate_reference_check_report(
    tree: etree._ElementTree,
    object_name: str,
    object_type: str,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    DEPRECATED: Use ReportingEngine instead.
    Generate a report of references to an object.
    """
    _warn_deprecated_import()
    engine = ReportingEngine(tree, device_type, context_type, version)
    return engine.generate_reference_check_report(
        object_name=object_name, object_type=object_type, output_file=output_file, **kwargs
    )

def generate_rule_hit_count_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    DEPRECATED: Use ReportingEngine instead.
    Generate a report of rule hit counts.
    """
    _warn_deprecated_import()
    engine = ReportingEngine(tree, device_type, context_type, version)
    return engine.generate_rule_hit_count_report(
        output_file=output_file, **kwargs
    )

# Re-export the EnhancedReportingEngine for backward compatibility
class EnhancedReportingEngine(ReportingEngine):
    """
    Engine for generating enhanced reports on PAN-OS configurations.

    DEPRECATED: This class is maintained for backward compatibility.
    Please use ReportingEngine directly.
    """
    def __init__(self, *args, **kwargs):
        _warn_deprecated_import()
        super().__init__(*args, **kwargs)