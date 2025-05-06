#!/usr/bin/env python3
"""
Build script for creating standalone binaries of the PANFlow application.
Creates executables for the current operating system.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).parent.absolute()

def build_binary():
    """Build the standalone binary for the current platform."""
    print(f"Building PANFlow binary for {platform.system()}...")
    
    # Create the spec file for PyInstaller
    spec_file = os.path.join(ROOT_DIR, "panflow.spec")
    
    # Main script to use as entry point
    entry_point = os.path.join(ROOT_DIR, "cli.py")
    
    # Define PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=panflow",
        "--onefile",  # Create a single executable
        "--clean",    # Clean cached data
        "--noupx",    # Don't use UPX for compression (more compatibility)
        f"--add-data={os.path.join(ROOT_DIR, 'panflow/xpath_mappings')}:{os.path.join('panflow', 'xpath_mappings')}".replace(':', ';' if platform.system() == 'Windows' else ':'),
        "--hidden-import=typer",
        "--hidden-import=rich",
        "--hidden-import=lxml.etree",
        "--hidden-import=yaml",
        "--hidden-import=networkx",
        entry_point
    ]
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)
    
    # Get the binary name
    binary_name = "panflow"
    if platform.system() == "Windows":
        binary_name += ".exe"
    
    # Path to the created binary
    binary_path = os.path.join(ROOT_DIR, "dist", binary_name)
    
    # Check if binary was created successfully
    if os.path.exists(binary_path):
        print(f"Successfully created binary: {binary_path}")
        return binary_path
    else:
        print("Failed to create binary!", file=sys.stderr)
        return None

if __name__ == "__main__":
    # Ensure all dependencies are installed
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", 
        os.path.join(ROOT_DIR, "requirements.txt")
    ], check=True)
    
    # Build the binary
    binary_path = build_binary()
    
    if binary_path:
        print(f"\nYou can now distribute the standalone binary: {binary_path}")
        print("\nTo use it, simply run:")
        if platform.system() == "Windows":
            print(f"    {binary_path} --help")
        else:
            print(f"    {binary_path} --help")