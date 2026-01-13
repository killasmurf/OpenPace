# OpenPace Windows Installation Guide

This guide covers everything you need to install, build, and distribute OpenPace on Windows.

## Table of Contents

1. [For End Users](#for-end-users)
2. [For Developers](#for-developers)
3. [Building the Installer](#building-the-installer)
4. [Troubleshooting](#troubleshooting)

---

## For End Users

### System Requirements

**Minimum Requirements:**
- Windows 10 (64-bit) or later
- 4 GB RAM
- 500 MB free disk space
- Display resolution: 1024x768 or higher

**Recommended:**
- Windows 11 (64-bit)
- 8 GB RAM or more
- 1 GB free disk space
- Display resolution: 1920x1080 or higher

### Installation Steps

1. **Download the Installer**
   - Download `OpenPace-Setup-1.0.0.exe` from the [releases page](https://github.com/killasmurf/OpenPace/releases)
   - The file size is approximately 150-200 MB

2. **Run the Installer**
   - Double-click `OpenPace-Setup-1.0.0.exe`
   - If Windows SmartScreen appears, click "More info" then "Run anyway"
   - You may need administrator privileges

3. **Follow Installation Wizard**
   - **License Agreement**: Read and accept the license
   - **Installation Location**: Default is `C:\Program Files\OpenPace`
     - You can change this, but default is recommended
   - **Data Storage**: Choose where patient data will be stored
     - Default: `C:\Users\[YourName]\AppData\Roaming\OpenPace`
     - Custom: Specify a custom location (advanced users)
   - **Start Menu**: Create shortcuts in Start Menu
   - **Desktop Icon**: Optionally create desktop shortcut

4. **Complete Installation**
   - Click "Install" to begin installation
   - Wait for files to be copied (may take 1-2 minutes)
   - Click "Finish" to complete

5. **First Launch**
   - Launch OpenPace from Start Menu or desktop icon
   - On first run, OpenPace will:
     - Create configuration file
     - Initialize database
     - Set up logging directories
   - Default configuration file: `%APPDATA%\OpenPace\config.json`

### Default Directories

After installation, OpenPace uses these directories:

- **Application**: `C:\Program Files\OpenPace\`
- **User Data**: `%APPDATA%\OpenPace\` (typically `C:\Users\[YourName]\AppData\Roaming\OpenPace`)
- **Database**: `%APPDATA%\OpenPace\openpace.db`
- **Logs**: `%APPDATA%\OpenPace\logs\`
- **Exports**: `%APPDATA%\OpenPace\exports\`

### Uninstallation

To uninstall OpenPace:

1. **Via Control Panel:**
   - Open Control Panel → Programs → Programs and Features
   - Find "OpenPace" in the list
   - Click "Uninstall"

2. **Via Start Menu:**
   - Right-click OpenPace in Start Menu
   - Select "Uninstall"

3. **Via Settings (Windows 11):**
   - Settings → Apps → Installed apps
   - Find "OpenPace"
   - Click three dots → Uninstall

**Note**: During uninstallation, you'll be asked if you want to keep patient data:
- **Keep Data**: Database and logs are preserved (allows reinstallation without data loss)
- **Remove All**: Complete removal including all patient data

---

## For Developers

### Development Setup

1. **Prerequisites**
   - Windows 10/11 (64-bit)
   - Python 3.9 or later ([Download](https://www.python.org/downloads/))
   - Git for Windows ([Download](https://git-scm.com/download/win))
   - Visual Studio Code (recommended) or your preferred IDE

2. **Clone Repository**
   ```powershell
   git clone https://github.com/killasmurf/OpenPace.git
   cd OpenPace
   ```

3. **Create Virtual Environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

4. **Install Dependencies**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Run from Source**
   ```powershell
   python main.py
   ```

### Development Tools

**Code Quality:**
```powershell
# Format code with black
black openpace/

# Lint with flake8
flake8 openpace/ --max-line-length=100

# Type checking with mypy
mypy openpace/
```

**Testing:**
```powershell
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=openpace --cov-report=html tests/

# Run specific test file
pytest tests/test_hl7_parser.py -v
```

---

## Building the Installer

### Prerequisites for Building

1. **Python 3.9+** installed and in PATH
2. **PyInstaller** (installed via requirements.txt)
3. **Inno Setup 6** ([Download](https://jrsoftware.org/isdl.php))
   - Install to default location: `C:\Program Files (x86)\Inno Setup 6\`

### Build Process

#### Option 1: Automated Build (Recommended)

Use the PowerShell build script:

```powershell
# Full build (tests + executable + installer)
.\build_windows.ps1

# Clean build (remove previous builds first)
.\build_windows.ps1 -Clean

# Skip tests
.\build_windows.ps1 -SkipTests

# Build executable only (no installer)
.\build_windows.ps1 -BuildOnly

# Combination
.\build_windows.ps1 -Clean -SkipTests
```

#### Option 2: Manual Build

**Step 1: Build Executable with PyInstaller**
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller openpace.spec --clean --noconfirm
```

Output: `dist\OpenPace\OpenPace.exe`

**Step 2: Create Installer with Inno Setup**
```powershell
# Using Inno Setup compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `installer_output\OpenPace-Setup-1.0.0.exe`

### Build Configuration

#### PyInstaller Configuration (`openpace.spec`)

Key settings:
- **Console Mode**: `CONSOLE = False` (no console window)
- **Debug Mode**: `DEBUG = False` (production build)
- **Icon**: `openpace/gui/resources/icon.ico`
- **Hidden Imports**: Modules not auto-detected by PyInstaller
- **Excludes**: Unused modules to reduce size

To modify:
1. Edit `openpace.spec`
2. Rebuild: `pyinstaller openpace.spec --clean`

#### Inno Setup Configuration (`installer.iss`)

Key settings:
- **App Version**: `#define MyAppVersion "1.0.0"`
- **Install Directory**: `DefaultDirName={autopf}\OpenPace`
- **Compression**: `Compression=lzma2/ultra64`
- **Minimum Windows**: `MinVersion=10.0` (Windows 10+)

To modify:
1. Edit `installer.iss`
2. Rebuild: `ISCC.exe installer.iss`

### Build Output

After successful build:
```
OpenPace/
├── dist/
│   └── OpenPace/
│       ├── OpenPace.exe          # Main executable
│       ├── *.dll                 # Dependencies
│       └── ...                   # Other runtime files
│
└── installer_output/
    └── OpenPace-Setup-1.0.0.exe  # Distributable installer (~150-200 MB)
```

### Distribution

**For Beta Testing:**
- Share `dist\OpenPace\` folder (portable version)
- Users can run `OpenPace.exe` directly

**For Release:**
- Distribute `OpenPace-Setup-1.0.0.exe`
- Upload to GitHub Releases
- Include release notes

---

## Troubleshooting

### Installation Issues

**Problem: "Windows protected your PC" SmartScreen warning**
- **Solution**: Click "More info" → "Run anyway"
- **Why**: Unsigned executable (digital signature requires paid certificate)

**Problem: Installation fails with permission error**
- **Solution**: Run installer as administrator (right-click → Run as administrator)

**Problem: Installation hangs at "Extracting files"**
- **Solution**:
  - Check antivirus isn't blocking installation
  - Try disabling antivirus temporarily
  - Install to different directory

### Runtime Issues

**Problem: Application won't start / crashes immediately**
- **Solutions**:
  1. Check Windows Event Viewer for error details
  2. Try running from Command Prompt to see error messages:
     ```
     cd "C:\Program Files\OpenPace"
     .\OpenPace.exe
     ```
  3. Check logs: `%APPDATA%\OpenPace\logs\openpace.log`

**Problem: "MSVCP140.dll is missing" error**
- **Solution**: Install Microsoft Visual C++ Redistributable:
  - [Download vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)
  - Run and install

**Problem: Database locked error**
- **Solution**:
  - Close all OpenPace instances
  - Check Task Manager for lingering `OpenPace.exe` processes
  - Restart computer if issue persists

**Problem: High DPI scaling issues (blurry text)**
- **Solution**:
  1. Right-click `OpenPace.exe`
  2. Properties → Compatibility
  3. Change high DPI settings
  4. Check "Override high DPI scaling behavior"
  5. Select "Application"

### Build Issues

**Problem: PyInstaller fails with "module not found"**
- **Solutions**:
  1. Add missing module to `hiddenimports` in `openpace.spec`
  2. Reinstall dependencies: `pip install -r requirements.txt`
  3. Check virtual environment is activated

**Problem: Inno Setup compiler not found**
- **Solution**:
  - Install Inno Setup to default location
  - Or update path in `build_windows.ps1` line 97

**Problem: Executable size is too large (>300 MB)**
- **Solutions**:
  1. Add more modules to `excludes` in `openpace.spec`
  2. Enable UPX compression: `upx=True`
  3. Remove unused dependencies

**Problem: Built executable crashes but source code works**
- **Solutions**:
  1. Enable console: Set `CONSOLE = True` in `openpace.spec`
  2. Rebuild and check console output
  3. Add missing data files to `datas` in spec file
  4. Check for hardcoded paths (use relative paths instead)

---

## Advanced Topics

### Creating Portable Version

To create a portable (no-install) version:

1. Build with PyInstaller
2. Copy `dist\OpenPace\` folder
3. Add `portable.txt` file (empty) to folder
4. OpenPace will use folder for data instead of AppData

### Custom Branding

To customize installer:

1. **Replace Icon**:
   - Create 256x256 ICO file
   - Replace `openpace/gui/resources/icon.ico`
   - Rebuild

2. **Customize Installer Text**:
   - Edit `installer.iss`
   - Modify `AppName`, `AppPublisher`, etc.

3. **Custom Installation Pages**:
   - Add to `[Code]` section in `installer.iss`
   - See Inno Setup documentation

### Code Signing (Optional)

For production release, consider code signing:

1. Purchase code signing certificate (~$100-500/year)
2. Install certificate on build machine
3. Sign executable:
   ```powershell
   signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com OpenPace.exe
   ```
4. Sign installer similarly

Benefits:
- Removes SmartScreen warning
- Builds user trust
- Required for enterprise deployment

---

## Support

**For Installation Help:**
- GitHub Issues: https://github.com/killasmurf/OpenPace/issues
- Documentation: https://github.com/killasmurf/OpenPace/wiki

**For Development Questions:**
- Contributing Guide: CONTRIBUTING.md
- Developer Chat: [Link to Discord/Slack if available]

---

## Version History

- **v1.0.0** (2024-01-12): Initial release
  - Windows 10/11 support
  - PyQt6-based GUI
  - SQLite database
  - HL7 ORU^R01 parsing
  - Security fixes implemented

---

*Last Updated: 2024-01-12*
