"""
HTML formatter for reports.

This module provides functionality for formatting report data as HTML.
"""

import os
import logging
from typing import Dict, Any, Optional

from ...core.template_loader import TemplateLoader

logger = logging.getLogger("panflow")


class HTMLFormatter:
    """
    HTML formatter for reports.

    This class provides methods for formatting report data as HTML.
    """

    def __init__(
        self, template_dir: Optional[str] = None, custom_templates_dir: Optional[str] = None
    ):
        """
        Initialize the HTML formatter.

        Args:
            template_dir: Directory containing the default templates
            custom_templates_dir: Directory containing custom templates that override defaults
        """
        self.template_loader = TemplateLoader(template_dir, custom_templates_dir)

    def format_security_policy_analysis(
        self, analysis_data: Dict[str, Any], include_hit_counts: bool = False
    ) -> str:
        """
        Format security policy analysis data as HTML.

        Args:
            analysis_data: The analysis data to format
            include_hit_counts: Whether hit count data is included

        Returns:
            HTML formatted report
        """
        return self.template_loader.render_security_policy_analysis(
            analysis_data, include_hit_counts
        )

    def format_unused_objects_report(self, report_data: Dict[str, Any]) -> str:
        """
        Format unused objects report data as HTML.

        Args:
            report_data: The report data to format

        Returns:
            HTML formatted report
        """
        return self.template_loader.render_template(
            "object_usage.html",
            {
                "report_title": "Unused Objects Report",
                "unused_objects": report_data.get("unused_objects", []),
                "total_count": len(report_data.get("unused_objects", [])),
            },
        )

    def format_duplicate_objects_report(self, report_data: Dict[str, Any]) -> str:
        """
        Format duplicate objects report data as HTML.

        Args:
            report_data: The report data to format

        Returns:
            HTML formatted report
        """
        duplicates = report_data.get("duplicate_objects", {})
        total_duplicates = sum(len(names) - 1 for names in duplicates.values())

        return self.template_loader.render_template(
            "object_usage.html",
            {
                "report_title": "Duplicate Objects Report",
                "duplicate_objects": duplicates,
                "total_count": total_duplicates,
                "unique_values": len(duplicates),
            },
        )
