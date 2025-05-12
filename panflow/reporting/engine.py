"""
Reporting engine for PANFlow.

This module provides the main reporting engine for PAN-OS XML configurations.
"""

import os
import datetime
import logging
from typing import Dict, Any, Optional, List, Union
from lxml import etree

from ..core.config_loader import xpath_search, extract_element_data
from ..core.xpath_resolver import get_object_xpath, get_policy_xpath
from ..core.logging_utils import logger, log, log_structured
from ..modules.objects import get_objects
from ..modules.policies import get_policies
from ..core.bulk_operations import ConfigQuery

from .formatters.html import HTMLFormatter
from .formatters.json import JSONFormatter
from .formatters.csv import CSVFormatter
from .reports.unused_objects import generate_unused_objects_report_data
from .reports.duplicate_objects import generate_duplicate_objects_report_data
from .reports.policy_analysis import generate_security_policy_analysis_data


class ReportingEngine:
    """
    Unified reporting engine for PAN-OS configurations.

    This class provides a consolidated interface for all reporting functionality,
    including policy analysis, object usage reports, and visualization.
    """

    def __init__(
        self,
        tree: etree._ElementTree,
        device_type: str,
        context_type: str,
        version: str,
        template_dir: Optional[str] = None,
        custom_templates_dir: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the reporting engine.

        Args:
            tree: ElementTree containing the configuration
            device_type: Device type (firewall or panorama)
            context_type: Context type (shared, device_group, vsys)
            version: PAN-OS version
            template_dir: Directory containing the default templates
            custom_templates_dir: Directory containing custom templates that override defaults
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        self.query = ConfigQuery(tree, device_type, context_type, version, **kwargs)

        # Initialize formatters
        self.html_formatter = HTMLFormatter(template_dir, custom_templates_dir)
        self.json_formatter = JSONFormatter()
        self.csv_formatter = CSVFormatter()

        # Log initialization
        log_structured(
            "Initialized ReportingEngine",
            "debug",
            device_type=device_type,
            context_type=context_type,
            version=version,
            has_template_dir=bool(template_dir),
            has_custom_templates=bool(custom_templates_dir),
        )

    def generate_unused_objects_report(
        self,
        object_type: str = "address",
        output_file: Optional[str] = None,
        output_format: str = "json",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a report of unused objects.

        Args:
            object_type: Type of object to check (address, service, etc.)
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            **kwargs: Additional parameters (context-specific)

        Returns:
            Dictionary containing the analysis results
        """
        # Generate the report data
        report_data = generate_unused_objects_report_data(
            self.tree,
            self.device_type,
            self.context_type,
            self.version,
            object_type=object_type,
            **{**self.context_kwargs, **kwargs},
        )

        # Save the report to a file if requested
        if output_file:
            self._save_report(report_data, output_file, output_format, "unused_objects")

        return report_data

    def generate_duplicate_objects_report(
        self,
        object_type: str = "address",
        output_file: Optional[str] = None,
        output_format: str = "json",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a report of duplicate objects.

        Args:
            object_type: Type of object to check (address, service, etc.)
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            **kwargs: Additional parameters (context-specific)

        Returns:
            Dictionary containing the analysis results
        """
        # Generate the report data
        report_data = generate_duplicate_objects_report_data(
            self.tree,
            self.device_type,
            self.context_type,
            self.version,
            object_type=object_type,
            **{**self.context_kwargs, **kwargs},
        )

        # Save the report to a file if requested
        if output_file:
            self._save_report(report_data, output_file, output_format, "duplicate_objects")

        return report_data

    def generate_security_policy_analysis(
        self,
        policy_type: Optional[str] = None,
        include_hit_counts: bool = False,
        hit_count_data: Optional[Dict[str, Dict[str, int]]] = None,
        output_file: Optional[str] = None,
        output_format: str = "json",
        include_visualization: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis of security policies.

        Args:
            policy_type: Type of security policy to analyze (if None, determine based on device type)
            include_hit_counts: Whether to include hit count analysis
            hit_count_data: Dictionary of hit count data (if available)
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            include_visualization: Whether to include visualization data
            **kwargs: Additional parameters (context-specific)

        Returns:
            Dictionary containing the analysis results
        """
        # Generate the report data
        analysis = generate_security_policy_analysis_data(
            self.tree,
            self.device_type,
            self.context_type,
            self.version,
            policy_type=policy_type,
            include_hit_counts=include_hit_counts,
            hit_count_data=hit_count_data,
            include_visualization=include_visualization,
            **{**self.context_kwargs, **kwargs},
        )

        # Save the report to a file if requested
        if output_file:
            self._save_report(
                analysis, output_file, output_format, "security_policy_analysis", include_hit_counts
            )

        return analysis

    def _save_report(
        self,
        data: Dict[str, Any],
        output_file: str,
        output_format: str,
        report_type: str,
        include_hit_counts: bool = False,
    ) -> bool:
        """
        Save a report to a file.

        Args:
            data: The report data to save
            output_file: Path to the output file
            output_format: Output format ('json', 'csv', 'html')
            report_type: Type of report ('unused_objects', 'duplicate_objects', 'security_policy_analysis')
            include_hit_counts: Whether hit count data is included (only for security policy analysis)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

            # Format and save the report based on the output format
            if output_format.lower() == "json":
                return self.json_formatter.save(data, output_file)

            elif output_format.lower() == "csv":
                # Format the report as CSV
                csv_data = ""
                if report_type == "unused_objects":
                    csv_data = self.csv_formatter.format_unused_objects_report(data)
                elif report_type == "duplicate_objects":
                    csv_data = self.csv_formatter.format_duplicate_objects_report(data)
                elif report_type == "security_policy_analysis":
                    csv_data = self.csv_formatter.format_security_policy_analysis(
                        data, include_hit_counts
                    )

                # Save the CSV data
                return self.csv_formatter.save(csv_data, output_file)

            elif output_format.lower() == "html":
                # Format the report as HTML
                html_data = ""
                if report_type == "unused_objects":
                    html_data = self.html_formatter.format_unused_objects_report(data)
                elif report_type == "duplicate_objects":
                    html_data = self.html_formatter.format_duplicate_objects_report(data)
                elif report_type == "security_policy_analysis":
                    html_data = self.html_formatter.format_security_policy_analysis(
                        data, include_hit_counts
                    )

                # Save the HTML data
                with open(output_file, "w") as f:
                    f.write(html_data)
                logger.info(f"Report saved to {output_file} (HTML format)")
                return True

            else:
                logger.error(f"Unsupported output format: {output_format}")
                return False

        except Exception as e:
            log_structured(
                f"Error saving report to file",
                "error",
                file_path=output_file,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False
