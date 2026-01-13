#!/bin/bash
# OpenPace Windows Build Script (Linux/WSL)
# This script builds the Windows installer for OpenPace from Linux/WSL
# Requires: Python 3.9+, PyInstaller, wine (for Inno Setup on Linux)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="OpenPace"
APP_VERSION="1.0.0"
PYTHON_VERSION="3.9"
DIST_DIR="dist"
BUILD_DIR="build"
INSTALLER_OUTPUT="installer_output"

# Parse command line arguments
CLEAN=false
SKIP_TESTS=false
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}========================================"
echo -e "OpenPace Windows Build Script"
echo -e "========================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
fi

PYTHON_VERSION_STR=$($PYTHON_CMD --version 2>&1)
if [[ $PYTHON_VERSION_STR =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    if [ $MAJOR -lt 3 ] || [ $MAJOR -eq 3 -a $MINOR -lt 9 ]; then
        echo -e "${RED}Error: Python 3.9 or higher is required. Found: $PYTHON_VERSION_STR${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python version: $PYTHON_VERSION_STR${NC}"
else
    echo -e "${RED}Error: Python not found or version could not be determined${NC}"
    exit 1
fi

# Clean previous builds
if [ "$CLEAN" = true ]; then
    echo ""
    echo -e "${YELLOW}Cleaning previous builds...${NC}"
    rm -rf "$DIST_DIR" "$BUILD_DIR" "$INSTALLER_OUTPUT" "__pycache__"
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    echo -e "${GREEN}✓ Cleaned build directories${NC}"
fi

# Check if virtual environment exists
echo ""
echo -e "${YELLOW}Checking virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install/upgrade dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install pyinstaller
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run tests (optional)
if [ "$SKIP_TESTS" = false ]; then
    echo ""
    echo -e "${YELLOW}Running tests...${NC}"
    if [ -d "tests" ]; then
        if python -m pytest tests/ -v; then
            echo -e "${GREEN}✓ All tests passed${NC}"
        else
            echo -e "${YELLOW}Warning: Some tests failed${NC}"
            read -p "Continue with build? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${RED}Build cancelled${NC}"
                exit 1
            fi
        fi
    else
        echo -e "${YELLOW}⚠ No tests directory found, skipping tests${NC}"
    fi
fi

# Build executable with PyInstaller
echo ""
echo -e "${YELLOW}Building executable with PyInstaller...${NC}"
pyinstaller openpace.spec --clean --noconfirm
echo -e "${GREEN}✓ Executable built successfully${NC}"

# Verify executable exists
if [ ! -f "$DIST_DIR/$APP_NAME/$APP_NAME.exe" ]; then
    echo -e "${RED}Error: Executable not found at expected location${NC}"
    exit 1
fi

# Stop here if BuildOnly flag is set
if [ "$BUILD_ONLY" = true ]; then
    echo ""
    echo -e "${CYAN}========================================"
    echo -e "Build complete (executable only)"
    echo -e "${GREEN}Executable location: $DIST_DIR/$APP_NAME/$APP_NAME.exe${NC}"
    echo -e "${CYAN}========================================${NC}"
    exit 0
fi

# Create installer with Inno Setup (requires wine on Linux)
echo ""
echo -e "${YELLOW}Creating installer with Inno Setup...${NC}"

# Check if wine is installed (for running Inno Setup on Linux)
if command -v wine &> /dev/null; then
    INNO_SETUP="$HOME/.wine/drive_c/Program Files (x86)/Inno Setup 6/ISCC.exe"
    if [ -f "$INNO_SETUP" ]; then
        wine "$INNO_SETUP" installer.iss
        echo -e "${GREEN}✓ Installer created successfully${NC}"
    else
        echo -e "${YELLOW}Warning: Inno Setup not found in wine${NC}"
        echo -e "${YELLOW}Install Inno Setup in wine or run this script on Windows${NC}"
        echo -e "${YELLOW}Download from: https://jrsoftware.org/isdl.php${NC}"
        echo ""
        echo -e "${GREEN}Build complete (executable only)${NC}"
        echo -e "${GREEN}Executable location: $DIST_DIR/$APP_NAME/$APP_NAME.exe${NC}"
        exit 0
    fi
else
    echo -e "${YELLOW}Warning: wine not installed (needed for Inno Setup on Linux)${NC}"
    echo -e "${YELLOW}Run this script on Windows to create the installer${NC}"
    echo ""
    echo -e "${GREEN}Build complete (executable only)${NC}"
    echo -e "${GREEN}Executable location: $DIST_DIR/$APP_NAME/$APP_NAME.exe${NC}"
    exit 0
fi

# Summary
echo ""
echo -e "${CYAN}========================================"
echo -e "Build Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${GREEN}Executable: $DIST_DIR/$APP_NAME/$APP_NAME.exe${NC}"
echo -e "${GREEN}Installer:  $INSTALLER_OUTPUT/$APP_NAME-Setup-$APP_VERSION.exe${NC}"
echo ""
echo -e "${CYAN}You can now distribute the installer to Windows users.${NC}"
echo ""
