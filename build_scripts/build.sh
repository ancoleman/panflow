#!/bin/bash
# Script to build a binary for the current platform

# Set up colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Determine platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
fi

echo -e "${GREEN}Building PANFlow binary for ${PLATFORM}...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not found.${NC}"
    exit 1
fi

# Ensure we're in the project root directory
cd "$(dirname "$0")"

# Create dist directory if it doesn't exist
mkdir -p dist

# Install PyInstaller if not already installed
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo -e "${YELLOW}Installing PyInstaller...${NC}"
    python3 -m pip install pyinstaller
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
python3 -m pip install -r requirements.txt

# Build the binary
echo -e "${YELLOW}Building binary...${NC}"

# Set output file name based on platform
OUTPUT_NAME="panflow"
if [[ "$PLATFORM" == "windows" ]]; then
    OUTPUT_NAME="panflow.exe"
fi

# Build with PyInstaller
python3 -m PyInstaller --name="$OUTPUT_NAME" --onefile --clean --noupx \
    --add-data="panflow/xpath_mappings:panflow/xpath_mappings" \
    --hidden-import=typer \
    --hidden-import=rich \
    --hidden-import=lxml.etree \
    --hidden-import=yaml \
    --hidden-import=networkx \
    panflow_cli.py

# Check if build was successful
if [[ -f "dist/$OUTPUT_NAME" ]]; then
    # Rename the binary with platform suffix
    PLATFORM_BINARY="panflow-$PLATFORM"
    if [[ "$PLATFORM" == "windows" ]]; then
        PLATFORM_BINARY="panflow-windows.exe"
        mv "dist/$OUTPUT_NAME" "dist/$PLATFORM_BINARY"
    else
        mv "dist/$OUTPUT_NAME" "dist/$PLATFORM_BINARY"
        chmod +x "dist/$PLATFORM_BINARY"
    fi
    
    echo -e "${GREEN}Successfully built PANFlow binary: dist/$PLATFORM_BINARY${NC}"
    echo -e "${YELLOW}You can now run: ./dist/$PLATFORM_BINARY --help${NC}"
else
    echo -e "${RED}Failed to build binary!${NC}"
    exit 1
fi