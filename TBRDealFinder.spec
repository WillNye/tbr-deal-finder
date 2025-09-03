# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['tbr_deal_finder/gui/main.py'],
    pathex=[],
    binaries=[],
    datas=[('tbr_deal_finder/queries', 'tbr_deal_finder/queries'), ('tbr_deal_finder/gui/assets', 'tbr_deal_finder/gui/assets')],
    hiddenimports=['flet', 'flet.web', 'flet.core', 'flet_desktop', 'plotly'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TBRDealFinder',
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
    icon=['tbr_deal_finder/gui/assets/logo.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TBRDealFinder',
)
app = BUNDLE(
    coll,
    name='TBRDealFinder.app',
    icon='tbr_deal_finder/gui/assets/logo.png',
    bundle_identifier='com.tbrdeals.finder',
)
