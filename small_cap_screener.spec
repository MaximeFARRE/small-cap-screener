# -*- mode: python ; coding: utf-8 -*-


datas = [
    ("assets", "assets"),
    ("data", "data"),
]

hiddenimports = [
    "src.models.company",
    "src.models.dividend",
    "src.models.financial_statement",
    "src.models.kpi_snapshot",
    "src.models.price_history",
    "src.models.screening_snapshot",
    "src.models.split",
    "src.models.watchlist_entry",
]

a = Analysis(
    ["src/ui/app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="small-cap-screener",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="small-cap-screener",
)
