"""
CSV formatter for reports.

This module provides functionality for formatting report data as CSV.
"""

import csv
import io
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("panflow")


class CSVFormatter:
    """
    CSV formatter for reports.

    This class provides methods for formatting report data as CSV.
    """

    def format_security_policy_analysis(
        self, analysis_data: Dict[str, Any], include_hit_counts: bool = False
    ) -> str:
        """
        Format security policy analysis data as CSV.

        Args:
            analysis_data: The analysis data to format
            include_hit_counts: Whether hit count data is included

        Returns:
            CSV formatted string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = [
            "Policy Name",
            "Action",
            "Disabled",
            "Source Count",
            "Destination Count",
            "Service Count",
            "Application Count",
            "Has Profile Group",
            "Has Log Forwarding",
        ]
        if include_hit_counts:
            header.append("Hit Count")
        writer.writerow(header)

        # Write rows
        for name, policy_info in analysis_data.get("policies", {}).items():
            row = [
                name,
                policy_info.get("action", ""),
                policy_info.get("disabled", False),
                policy_info.get("source_count", 0),
                policy_info.get("destination_count", 0),
                policy_info.get("service_count", 0),
                policy_info.get("application_count", 0),
                policy_info.get("has_profile_group", False),
                policy_info.get("has_log_forwarding", False),
            ]
            if include_hit_counts:
                row.append(policy_info.get("hit_count", "N/A"))
            writer.writerow(row)

        return output.getvalue()

    def format_unused_objects_report(self, report_data: Dict[str, Any]) -> str:
        """
        Format unused objects report data as CSV.

        Args:
            report_data: The report data to format

        Returns:
            CSV formatted string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Object Name", "Type", "Value"])

        # Write rows
        for obj in report_data.get("unused_objects", []):
            obj_name = obj.get("name", "")
            obj_props = obj.get("properties", {})

            # Determine the object type and value
            obj_type = "Unknown"
            obj_value = ""

            if "ip-netmask" in obj_props:
                obj_type = "IP/Netmask"
                obj_value = obj_props["ip-netmask"]
            elif "ip-range" in obj_props:
                obj_type = "IP Range"
                obj_value = obj_props["ip-range"]
            elif "fqdn" in obj_props:
                obj_type = "FQDN"
                obj_value = obj_props["fqdn"]
            elif "protocol" in obj_props:
                obj_type = "Service"
                obj_value = obj_props["protocol"]

            writer.writerow([obj_name, obj_type, obj_value])

        return output.getvalue()

    def format_duplicate_objects_report(self, report_data: Dict[str, Any]) -> str:
        """
        Format duplicate objects report data as CSV.

        Args:
            report_data: The report data to format

        Returns:
            CSV formatted string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Value", "Object Type", "Duplicate Objects"])

        # Write rows
        for value_key, names in report_data.get("duplicate_objects", {}).items():
            # Parse the value key to get the object type and value
            parts = value_key.split(":") if ":" in value_key else ["unknown", value_key]
            obj_type = parts[0]
            obj_value = parts[1] if len(parts) > 1 else ""

            writer.writerow([obj_value, obj_type, ", ".join(names)])

        return output.getvalue()

    def save(self, data: str, output_file: str) -> bool:
        """
        Save CSV data to a file.

        Args:
            data: The CSV data to save
            output_file: Path to the output file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, "w", newline="") as f:
                f.write(data)
            logger.info(f"Report saved to {output_file} (CSV format)")
            return True
        except Exception as e:
            logger.error(f"Error saving report to {output_file}: {e}")
            return False
