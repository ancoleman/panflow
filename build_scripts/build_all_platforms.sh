#!/bin/bash
# Script to build binaries for multiple platforms using Docker

# Ensure we're in the project root directory
cd "$(dirname "$0")"

# Create build directory
mkdir -p dist

echo "=== Building PANFlow Binaries for Multiple Platforms ==="

# Build for Linux (using Docker)
echo "Building Linux binary..."
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
    pip install -r requirements.txt pyinstaller &&
    pyinstaller --name=panflow --onefile --clean --noupx \
    --add-data=panflow/xpath_mappings:panflow/xpath_mappings \
    --hidden-import=typer \
    --hidden-import=rich \
    --hidden-import=lxml.etree \
    --hidden-import=yaml \
    --hidden-import=networkx \
    cli.py
"

# Rename the Linux binary
mv dist/panflow dist/panflow-linux
echo "Linux binary built: dist/panflow-linux"

# For Windows and macOS, provide instructions as these usually need to be built on their native OS
echo ""
echo "=== Instructions for building on other platforms ==="
echo ""
echo "Windows:"
echo "1. On a Windows machine, install Python 3.7+ and required packages:"
echo "   pip install -r requirements.txt pyinstaller"
echo "2. Build the binary:"
echo "   pyinstaller --name=panflow --onefile --clean --noupx ^"
echo "   --add-data=panflow/xpath_mappings;panflow/xpath_mappings ^"
echo "   --hidden-import=typer ^"
echo "   --hidden-import=rich ^"
echo "   --hidden-import=lxml.etree ^"
echo "   --hidden-import=yaml ^"
echo "   --hidden-import=networkx ^"
echo "   cli.py"
echo ""
echo "macOS:"
echo "1. On a macOS machine, install Python 3.7+ and required packages:"
echo "   pip install -r requirements.txt pyinstaller"
echo "2. Build the binary:"
echo "   pyinstaller --name=panflow --onefile --clean --noupx \\"
echo "   --add-data=panflow/xpath_mappings:panflow/xpath_mappings \\"
echo "   --hidden-import=typer \\"
echo "   --hidden-import=rich \\"
echo "   --hidden-import=lxml.etree \\"
echo "   --hidden-import=yaml \\"
echo "   --hidden-import=networkx \\"
echo "   cli.py"
echo ""
echo "=== Option for cross-platform builds ==="
echo "For a more automated cross-platform build process, consider using:"
echo "- GitHub Actions (workflows for each platform)"
echo "- PyInstaller with PyOxidizer (https://pyoxidizer.readthedocs.io/)"
echo "- Nuitka (https://nuitka.net/) as an alternative to PyInstaller"

echo ""
echo "=== Completed ==="