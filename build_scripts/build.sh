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
cd "$(dirname "$0")/.."

# Create or clean dist directory
if [ -d "dist" ]; then
    echo -e "${YELLOW}Cleaning existing dist directory...${NC}"
    # Remove the dist directory but first check if PANFlow.app exists
    if [ -d "dist/PANFlow.app" ]; then
        echo -e "${YELLOW}Removing existing PANFlow.app...${NC}"
        rm -rf "dist/PANFlow.app"
    fi
else
    mkdir -p dist
fi

# Install PyInstaller if not already installed
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo -e "${YELLOW}Installing PyInstaller...${NC}"
    python3 -m pip install pyinstaller
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}Using Poetry to manage dependencies${NC}"
    # Try to install directly with Poetry first - use --without dev to skip dev dependencies
    if poetry install --without dev; then
        echo -e "${GREEN}Dependencies installed successfully with Poetry${NC}"
    else
        # If direct installation fails, try exporting to requirements file
        echo -e "${YELLOW}Direct Poetry install failed, trying with requirements.txt...${NC}"
        # Try to install the package directly in development mode
        if python3 -m pip install -e .; then
            echo -e "${GREEN}Dependencies installed in development mode${NC}"
        else
            echo -e "${RED}Failed to install dependencies${NC}"
            exit 1
        fi
    fi
else
    # Fall back to requirements.txt if available
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -r requirements.txt
    else
        echo -e "${RED}Warning: Neither Poetry nor requirements.txt found${NC}"
        echo -e "${YELLOW}Installing project in development mode...${NC}"
        # Install the current project in development mode
        python3 -m pip install -e .
    fi
fi

# Build the binary
echo -e "${YELLOW}Building binary...${NC}"

# Set output file name based on platform
OUTPUT_NAME="panflow"
if [[ "$PLATFORM" == "windows" ]]; then
    OUTPUT_NAME="panflow.exe"
fi

# Build with PyInstaller
if [[ "$PLATFORM" == "macos" ]]; then
    # For macOS, use the existing spec file to create an application bundle
    echo -e "${YELLOW}Building macOS application bundle with completion support...${NC}"
    
    # Check if spec file exists
    if [ -f "panflow.spec" ]; then
        python3 -m PyInstaller panflow.spec --clean --workpath=build --distpath=dist -y
    else
        echo -e "${RED}Spec file 'panflow.spec' not found. Cannot build macOS application bundle.${NC}"
        exit 1
    fi
    
    # Check if build was successful
    if [ -d "dist/PANFlow.app" ]; then
        echo -e "${GREEN}Successfully built PANFlow.app bundle${NC}"
        # Make the binary executable
        chmod +x "dist/PANFlow.app/Contents/MacOS/panflow"
        
        # Run the test script if it exists
        if [ -f "test_completion.sh" ]; then
            echo -e "\n${YELLOW}Do you want to run the completion test script? (y/n)${NC}"
            read -r response
            if [[ "$response" == "y" ]]; then
                echo -e "${YELLOW}Running completion test script...${NC}"
                chmod +x "test_completion.sh"
                ./test_completion.sh
            fi
        fi
        
        echo -e "${GREEN}You can now use the application bundle: dist/PANFlow.app${NC}"
        echo -e "${YELLOW}To test shell completion, run:${NC}"
        echo -e "  dist/PANFlow.app/Contents/MacOS/panflow completion --install"
    else
        echo -e "${RED}Failed to build application bundle!${NC}"
        exit 1
    fi
else
    # For other platforms, use standard PyInstaller configuration
    python3 -m PyInstaller --name="$OUTPUT_NAME" --onefile --clean --noupx \
        --add-data="panflow/xpath_mappings:panflow/xpath_mappings" \
        --add-data="panflow/templates:panflow/templates" \
        --hidden-import=typer \
        --hidden-import=rich \
        --hidden-import=lxml.etree \
        --hidden-import=yaml \
        --hidden-import=networkx \
        --hidden-import=panflow.cli \
        --hidden-import=panflow.cli.app \
        --hidden-import=panflow.cli.commands \
        --hidden-import=panflow.cli.completion \
        --hidden-import=panflow.cli.completions \
        cli.py
        
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
fi