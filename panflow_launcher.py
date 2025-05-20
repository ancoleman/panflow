#!/usr/bin/env python3
"""
PANFlow Launcher Script.

This is the entry point for the standalone PANFlow application.
"""

import sys
import os

# Make sure we can import from the panflow package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import main CLI app
from panflow.cli import app

if __name__ == "__main__":
    # Run the CLI app
    app()