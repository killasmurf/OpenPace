# OpenPace Windows Build Quick Start

This document provides a quick reference for building the Windows installer.

## Quick Build

```powershell
# On Windows (PowerShell)
.\build_windows.ps1

# On Linux/WSL
./build_windows.sh
```

## Prerequisites

### Required
- Python 3.9 or later
- Git

### For Creating Installer
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (Windows only)

## Build Files

| File | Purpose |
|------|---------|
| `openpace.spec` | PyInstaller configuration |
| `installer.iss` | Inno Setup installer script |
| `build_windows.ps1` | Automated build script (PowerShell) |
| `build_windows.sh` | Automated build script (Bash) |
| `version_info.txt` | Windows executable metadata |

## Build Options

```powershell
# Clean build (removes previous builds)
.\build_windows.ps1 -Clean

# Skip running tests
.\build_windows.ps1 -SkipTests

# Build executable only (no installer)
.\build_windows.ps1 -BuildOnly

# Combine options
.\build_windows.ps1 -Clean -SkipTests
```

## Output

After successful build:

```
dist/OpenPace/OpenPace.exe              # Portable executable
installer_output/OpenPace-Setup-1.0.0.exe  # Windows installer
```

## File Sizes

- **Executable folder**: ~150 MB
- **Installer**: ~150-200 MB (compressed)

## Common Issues

### PyInstaller Errors

**"Module not found" error**
- Add module to `hiddenimports` in `openpace.spec`

**"Failed to execute script" error**
- Enable console mode: Set `CONSOLE = True` in `openpace.spec`
- Rebuild and check console output

### Inno Setup Errors

**Compiler not found**
- Install Inno Setup to default location
- Or update path in build script

**"Source file not found"**
- Ensure PyInstaller build completed successfully
- Check `dist/OpenPace/` folder exists

## Testing the Build

### Test Executable
```powershell
cd dist\OpenPace
.\OpenPace.exe
```

### Test Installer
1. Run `OpenPace-Setup-1.0.0.exe`
2. Follow installation wizard
3. Launch from Start Menu
4. Verify all features work

## Modifying the Build

### Change Version Number

Update in these files:
1. `openpace.spec` (line 14): `APP_VERSION = '1.0.0'`
2. `installer.iss` (line 7): `#define MyAppVersion "1.0.0"`
3. `version_info.txt` (lines 11-12, 25, 31)
4. `build_windows.ps1` (line 15): `$APP_VERSION = "1.0.0"`
5. `build_windows.sh` (line 18): `APP_VERSION="1.0.0"`

### Change App Name

Update in these files:
1. `openpace.spec` (line 13): `APP_NAME = 'OpenPace'`
2. `installer.iss` (line 6): `#define MyAppName "OpenPace"`
3. `build_windows.ps1` (line 14): `$APP_NAME = "OpenPace"`
4. `build_windows.sh` (line 17): `APP_NAME="OpenPace"`

### Add/Remove Dependencies

1. Update `requirements.txt`
2. Add to `hiddenimports` in `openpace.spec` if needed
3. Rebuild

### Customize Installer

Edit `installer.iss`:
- **Icon**: Line 21 - `SetupIconFile=...`
- **License**: Line 19 - `LicenseFile=...`
- **Install Directory**: Line 15 - `DefaultDirName=...`
- **Compression**: Line 23 - `Compression=...`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Windows Installer

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build with PyInstaller
        run: pyinstaller openpace.spec --clean --noconfirm

      - name: Install Inno Setup
        run: |
          choco install innosetup

      - name: Create Installer
        run: |
          iscc installer.iss

      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: OpenPace-Installer
          path: installer_output/OpenPace-Setup-*.exe
```

## Distribution Checklist

Before distributing:

- [ ] All tests pass
- [ ] Version number updated in all files
- [ ] CHANGELOG.md updated
- [ ] README.md reviewed
- [ ] License file included
- [ ] Documentation up to date
- [ ] Installer tested on clean Windows installation
- [ ] Executable signed (optional, but recommended)
- [ ] Release notes written

## Support

For detailed documentation, see [WINDOWS_INSTALLATION.md](WINDOWS_INSTALLATION.md)

For issues, visit: https://github.com/killasmurf/OpenPace/issues

---

*Last Updated: 2024-01-12*
