#!/bin/bash
# Simple installation script for PANFlow

# Default installation directory
INSTALL_DIR="/usr/local/bin"

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
fi

# Parse arguments
for arg in "$@"; do
  case $arg in
    --dir=*)
    INSTALL_DIR="${arg#*=}"
    shift
    ;;
    --help)
    echo "PANFlow installation script"
    echo "Usage: ./install.sh [--dir=INSTALLATION_DIRECTORY]"
    echo ""
    echo "Options:"
    echo "  --dir=PATH    Install PANFlow to PATH (default: /usr/local/bin)"
    echo "  --help        Show this help message"
    exit 0
    ;;
  esac
done

# Determine which binary to use based on platform
BINARY_NAME="panflow"
if [[ "$PLATFORM" == "linux" ]]; then
    BINARY_NAME="panflow-linux"
elif [[ "$PLATFORM" == "macos" ]]; then
    BINARY_NAME="panflow-macos"
else
    echo "Unsupported platform: $OSTYPE"
    exit 1
fi

# Check if the binary exists in the current directory
if [[ ! -f "./$BINARY_NAME" ]]; then
    echo "Binary not found: $BINARY_NAME"
    echo "Please download the correct binary for your platform first."
    exit 1
fi

# Check if installation directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Installation directory does not exist: $INSTALL_DIR"
    read -p "Create it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$INSTALL_DIR"
    else
        echo "Installation cancelled."
        exit 1
    fi
fi

# Check if we have write permissions to the installation directory
if [[ ! -w "$INSTALL_DIR" ]]; then
    echo "No write permission to $INSTALL_DIR"
    echo "Try running with sudo:"
    echo "  sudo $0 $*"
    exit 1
fi

# Copy binary to installation directory
cp "./$BINARY_NAME" "$INSTALL_DIR/panflow"
chmod +x "$INSTALL_DIR/panflow"

echo "PANFlow installed successfully to $INSTALL_DIR/panflow"
echo "You can now run 'panflow' from anywhere if $INSTALL_DIR is in your PATH."