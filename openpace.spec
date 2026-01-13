# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for OpenPace Windows build

This spec file creates a standalone Windows executable with all dependencies bundled.
"""

import sys
from pathlib import Path

block_cipher = None

# Application metadata
APP_NAME = 'OpenPace'
APP_VERSION = '1.0.0'
APP_AUTHOR = 'OpenPace Team'
APP_DESCRIPTION = 'Pacemaker Data Analysis Platform'

# Build configuration
DEBUG = False
CONSOLE = False  # Set to True for debugging

# Collect all data files
datas = [
    # Include configuration files
    ('.env.example', '.'),
    ('README.md', '.'),
    ('LICENSE', '.'),

    # Include docs
    ('docs', 'docs'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.sql.default_comparator',
    'scipy.special.cython_special',
    'scipy._lib.messagestream',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.skiplist',
    'hl7',
    'hl7apy',
    'reportlab.graphics',
    'reportlab.pdfgen',
    'matplotlib.backends.backend_qt5agg',
    'pyqtgraph',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
]

# Binaries to exclude (optional, to reduce size)
excludes = [
    'tkinter',
    'test',
    'unittest',
    'distutils',
    'setuptools',
    'pip',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=DEBUG,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='openpace/gui/resources/icon.ico' if Path('openpace/gui/resources/icon.ico').exists() else None,
    version_file='version_info.txt' if Path('version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
