"""
JSON formatter for reports.

This module provides functionality for formatting report data as JSON.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("panflow")


class JSONFormatter:
    """
    JSON formatter for reports.

    This class provides methods for formatting report data as JSON.
    """

    def __init__(self, indent: int = 2):
        """
        Initialize the JSON formatter.

        Args:
            indent: Number of spaces for indentation in the JSON output
        """
        self.indent = indent

    def format(self, data: Dict[str, Any]) -> str:
        """
        Format data as JSON.

        Args:
            data: The data to format

        Returns:
            JSON formatted string
        """
        return json.dumps(data, indent=self.indent)

    def save(self, data: Dict[str, Any], output_file: str) -> bool:
        """
        Save data as JSON to a file.

        Args:
            data: The data to save
            output_file: Path to the output file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, "w") as f:
                json.dump(data, f, indent=self.indent)
            logger.info(f"Report saved to {output_file} (JSON format)")
            return True
        except Exception as e:
            logger.error(f"Error saving report to {output_file}: {e}")
            return False
