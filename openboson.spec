# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for OpenBoson (Windows)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None
ROOT = Path(SPECPATH).resolve()
SRC = ROOT / "src" / "openboson"
DATA = ROOT / "data"

datas = [
    (str(SRC / "gui" / "styles.qss"), "openboson/gui"),
    (str(DATA / "demo_banks"), "data/demo_banks"),
    (str(DATA / "demo_labs"), "data/demo_labs"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "PRIVACY.md"), "."),
    (str(ROOT / "SUPPORT.md"), "."),
]
if (ROOT / "THIRD_PARTY.md").is_file():
    datas.append((str(ROOT / "THIRD_PARTY.md"), "."))

# Ship Qt/PySide6 LGPL notices when present.
for notice in ("LICENSES.PySide6", "LICENSE.PySide6", "LICENSE.Qt"):
    for candidate in (ROOT / notice, ROOT / "licenses" / notice):
        if candidate.is_file():
            datas.append((str(candidate), "licenses"))

binaries = []
hiddenimports = [
    "openboson",
    "openboson.gui",
    "openboson.gui.app",
    "openboson.gui.main_window",
    "openboson._build_info",
    "sqlalchemy.sql.default_comparator",
    "yaml",
    "PySide6.QtSvg",
]

tmp_ret = collect_all("PySide6")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    [str(SRC / "gui" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="OpenBoson",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OpenBoson",
)
