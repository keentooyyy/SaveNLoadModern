# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SaveNLoad Client Worker
This creates a standalone executable with all dependencies bundled
"""

import os
from pathlib import Path

# Get the directory where this spec file is located
SPEC_DIR = Path(SPECPATH).absolute() if 'SPECPATH' in locals() else Path(__file__).parent.absolute()
CLIENT_WORKER_DIR = SPEC_DIR

block_cipher = None

a = Analysis(
    [str(CLIENT_WORKER_DIR / 'client_service_rclone.py')],
    pathex=[str(CLIENT_WORKER_DIR)],
    binaries=[
        (str(CLIENT_WORKER_DIR / 'rclone' / 'rclone.exe'), 'rclone'),  # Include rclone executable
    ],
    datas=[
        (str(CLIENT_WORKER_DIR / 'requirements.txt'), '.'),
        (str(CLIENT_WORKER_DIR / 'rclone' / 'rclone.conf'), 'rclone'),  # Include rclone config
    ],
    hiddenimports=[
        'client_worker',
        'client_worker.client_service_rclone',
        'client_worker.rclone_client',
        'requests',
        'requests.packages.urllib3',
        'requests.packages.urllib3.util',
        'dotenv',
        'python-dotenv',
        'threading',
        'concurrent.futures',
        'queue',
        'webbrowser',
        'platform',
        'uuid',
        'subprocess',
        'json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'venv',  # Exclude venv directory
        'client_worker.venv',  # Exclude client_worker venv
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SaveNLoadClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
    uac_admin=True,  # Request admin privileges
)

