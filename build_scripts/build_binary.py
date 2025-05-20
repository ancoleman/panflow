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

# Root directory of the project (script parent directory)
SCRIPT_DIR = Path(__file__).parent.absolute()
# Project root directory (one level up)
PROJECT_ROOT = SCRIPT_DIR.parent.absolute()


def build_binary():
    """Build the standalone binary for the current platform."""
    print(f"Building PANFlow binary for {platform.system()}...")

    # Change to project root
    os.chdir(PROJECT_ROOT)

    # Check for platform-specific builds
    if platform.system() == "Darwin":  # macOS
        # For macOS, use the spec file to create an app bundle with completion support
        spec_file = os.path.join(PROJECT_ROOT, "panflow.spec")
        if os.path.exists(spec_file):
            # Use the absolute path to the spec file
            cmd = [
                "pyinstaller",
                spec_file,  # Use the absolute path
                "--clean",
                "--workpath", os.path.join(PROJECT_ROOT, "build"),
                "--distpath", os.path.join(PROJECT_ROOT, "dist"),
            ]
            print(f"Building macOS application bundle with completion support using spec: {spec_file}...")
        else:
            # Fall back to standard build if spec file doesn't exist
            print("Spec file not found, falling back to standard build...")
            entry_point = os.path.join(PROJECT_ROOT, "cli.py")
            cmd = [
                "pyinstaller",
                "--name=panflow",
                "--onefile",
                "--clean",
                "--noupx",
                f"--add-data={os.path.join(PROJECT_ROOT, 'panflow/xpath_mappings')}:{os.path.join('panflow', 'xpath_mappings')}",
                f"--add-data={os.path.join(PROJECT_ROOT, 'panflow/templates')}:{os.path.join('panflow', 'templates')}",
                "--hidden-import=typer",
                "--hidden-import=rich",
                "--hidden-import=lxml.etree",
                "--hidden-import=yaml",
                "--hidden-import=networkx",
                "--hidden-import=panflow.cli",
                "--hidden-import=panflow.cli.app",
                "--hidden-import=panflow.cli.common",
                "--hidden-import=panflow.cli.completion",
                "--hidden-import=panflow.cli.completions",
                entry_point,
            ]
    else:
        # Standard build for other platforms
        entry_point = os.path.join(PROJECT_ROOT, "cli.py")
        cmd = [
            "pyinstaller",
            "--name=panflow",
            "--onefile",  # Create a single executable
            "--clean",  # Clean cached data
            "--noupx",  # Don't use UPX for compression (more compatibility)
            f"--add-data={os.path.join(PROJECT_ROOT, 'panflow/xpath_mappings')}:{os.path.join('panflow', 'xpath_mappings')}".replace(
                ":", ";" if platform.system() == "Windows" else ":"
            ),
            f"--add-data={os.path.join(PROJECT_ROOT, 'panflow/templates')}:{os.path.join('panflow', 'templates')}".replace(
                ":", ";" if platform.system() == "Windows" else ":"
            ),
            "--hidden-import=typer",
            "--hidden-import=rich",
            "--hidden-import=lxml.etree",
            "--hidden-import=yaml",
            "--hidden-import=networkx",
            "--hidden-import=panflow.cli",
            "--hidden-import=panflow.cli.app",
            "--hidden-import=panflow.cli.common",
            "--hidden-import=panflow.cli.completion",
            "--hidden-import=panflow.cli.completions",
            entry_point,
        ]

    # Run PyInstaller
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building binary: {e}", file=sys.stderr)
        return None

    # Get the binary name and location based on platform
    if platform.system() == "Darwin":
        # For macOS we build an .app bundle
        app_bundle_path = os.path.join(PROJECT_ROOT, "dist", "PANFlow.app")
        binary_path = os.path.join(app_bundle_path, "Contents", "MacOS", "panflow")
        
        if os.path.exists(app_bundle_path):
            print(f"Successfully created application bundle: {app_bundle_path}")
            # Make sure the binary is executable
            if os.path.exists(binary_path):
                os.chmod(binary_path, 0o755)
            return binary_path
    else:
        # For other platforms we build a standalone binary
        binary_name = "panflow"
        if platform.system() == "Windows":
            binary_name += ".exe"
        
        binary_path = os.path.join(PROJECT_ROOT, "dist", binary_name)
        
        if os.path.exists(binary_path):
            print(f"Successfully created binary: {binary_path}")
            # Make the binary executable on Unix
            if platform.system() != "Windows":
                os.chmod(binary_path, 0o755)
            return binary_path
    
    print("Failed to create binary!", file=sys.stderr)
    return None


def install_dependencies():
    """Install all dependencies required for building."""
    # Change to project root
    os.chdir(PROJECT_ROOT)
    
    # Always ensure PyInstaller is installed first
    print("Installing PyInstaller...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        check=True,
    )
    
    # Check if we can use Poetry
    if shutil.which("poetry"):
        print("Using Poetry to manage dependencies...")
        try:
            # Try to use poetry install first (with --without dev to skip development dependencies)
            print("Installing project with Poetry...")
            subprocess.run(
                ["poetry", "install", "--without", "dev"],
                check=True,
                cwd=PROJECT_ROOT,
            )
            return
        except subprocess.CalledProcessError:
            print("Direct Poetry install failed, trying development mode...")
            try:
                # Install the project in development mode
                print("Installing project in development mode...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", PROJECT_ROOT],
                    check=True,
                )
                return
            except subprocess.CalledProcessError:
                print("Failed to install in development mode")
    
    # Fall back to requirements.txt if available
    req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_path):
        print(f"Installing dependencies from {req_path}...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            check=True,
        )
    else:
        print("Neither Poetry nor requirements.txt found, installing project in development mode...")
        # Install the project in development mode
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", PROJECT_ROOT],
            check=True,
        )


if __name__ == "__main__":
    # Ensure all dependencies are installed
    install_dependencies()
    
    # Build the binary
    binary_path = build_binary()
    
    if binary_path:
        print(f"\nYou can now distribute the standalone application:")
        
        if platform.system() == "Darwin":
            app_bundle = os.path.join(PROJECT_ROOT, "dist", "PANFlow.app")
            print(f"Application bundle: {app_bundle}")
            print("\nTo test shell completion, run:")
            print(f"  {binary_path} completion --install")
            print("\nTo test the completion in your shell:")
            print("  1. Restart your terminal or source your shell's initialization file")
            print("  2. Type 'panflow ' and press Tab twice")
        else:
            print(f"Binary: {binary_path}")
            print("\nTo use it, run:")
            print(f"  {binary_path} --help")
        
        # Run the test_completion.sh script if it exists and we're on macOS
        if platform.system() == "Darwin":
            test_script = os.path.join(PROJECT_ROOT, "test_completion.sh")
            if os.path.exists(test_script):
                print("\nDo you want to run the completion test script? (y/n)")
                response = input().strip().lower()
                if response == 'y':
                    print("\nRunning completion test script...")
                    os.chmod(test_script, 0o755)
                    subprocess.run([test_script], check=False)
    else:
        print("\nFailed to build the application. Please check the error messages above.")
        sys.exit(1)