# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["Tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
    )

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
    )

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="HawkEye",
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    noconsole=True,
    onefile=True,
    windowed=True
    )

app = BUNDLE(
    exe,
    name="HawkEye.app",
    bundle_identifier=None
    )