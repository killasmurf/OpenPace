# OpenPace Windows Build Script
# This script builds the Windows installer for OpenPace
# Requires: Python 3.9+, PyInstaller, Inno Setup

param(
    [switch]$Clean = $false,
    [switch]$SkipTests = $false,
    [switch]$BuildOnly = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpenPace Windows Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$APP_NAME = "OpenPace"
$APP_VERSION = "1.0.0"
$PYTHON_VERSION = "3.9"
$DIST_DIR = "dist"
$BUILD_DIR = "build"
$INSTALLER_OUTPUT = "installer_output"

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        Write-Host "Error: Python 3.9 or higher is required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Python version: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "Error: Python not found or version could not be determined" -ForegroundColor Red
    exit 1
}

# Clean previous builds
if ($Clean) {
    Write-Host ""
    Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path $DIST_DIR) { Remove-Item -Recurse -Force $DIST_DIR }
    if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
    if (Test-Path $INSTALLER_OUTPUT) { Remove-Item -Recurse -Force $INSTALLER_OUTPUT }
    if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
    Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
    Write-Host "✓ Cleaned build directories" -ForegroundColor Green
}

# Check if virtual environment exists
Write-Host ""
Write-Host "Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install/upgrade dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to upgrade pip" -ForegroundColor Red
    exit 1
}

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install requirements" -ForegroundColor Red
    exit 1
}

pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install PyInstaller" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Run tests (optional)
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Running tests..." -ForegroundColor Yellow
    if (Test-Path "tests") {
        python -m pytest tests/ -v
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Warning: Some tests failed" -ForegroundColor Yellow
            $response = Read-Host "Continue with build? (y/n)"
            if ($response -ne "y" -and $response -ne "Y") {
                Write-Host "Build cancelled" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "✓ All tests passed" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠ No tests directory found, skipping tests" -ForegroundColor Yellow
    }
}

# Build executable with PyInstaller
Write-Host ""
Write-Host "Building executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller openpace.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: PyInstaller build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Executable built successfully" -ForegroundColor Green

# Verify executable exists
if (-not (Test-Path "$DIST_DIR\$APP_NAME\$APP_NAME.exe")) {
    Write-Host "Error: Executable not found at expected location" -ForegroundColor Red
    exit 1
}

# Stop here if BuildOnly flag is set
if ($BuildOnly) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Build complete (executable only)" -ForegroundColor Cyan
    Write-Host "Executable location: $DIST_DIR\$APP_NAME\$APP_NAME.exe" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
}

# Create installer with Inno Setup
Write-Host ""
Write-Host "Creating installer with Inno Setup..." -ForegroundColor Yellow

# Check if Inno Setup is installed
$innoSetupPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $innoSetupPath)) {
    Write-Host "Warning: Inno Setup not found at default location" -ForegroundColor Yellow
    Write-Host "Please install Inno Setup from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Build complete (executable only)" -ForegroundColor Green
    Write-Host "Executable location: $DIST_DIR\$APP_NAME\$APP_NAME.exe" -ForegroundColor Green
    exit 0
}

# Run Inno Setup compiler
& $innoSetupPath "installer.iss"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Inno Setup compilation failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Installer created successfully" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Executable: $DIST_DIR\$APP_NAME\$APP_NAME.exe" -ForegroundColor Green
Write-Host "Installer:  $INSTALLER_OUTPUT\$APP_NAME-Setup-$APP_VERSION.exe" -ForegroundColor Green
Write-Host ""
Write-Host "You can now distribute the installer to Windows users." -ForegroundColor Cyan
Write-Host ""
