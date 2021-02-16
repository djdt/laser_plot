# vim: set ft=python:
from pathlib import Path


block_cipher = None

a = Analysis(
    [Path("pewpew", "__main__.py")],
    binaries=None,
    datas=[('pewpew/resources/pewpew.qch', 'pewpew/resources')],
    hiddenimports=[],
    hookspath=None,
    runtime_hooks=None,
    excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
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
    name="pewpew_debug",
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon="app.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="pewpew_debug",
)
