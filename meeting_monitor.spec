# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Meeting Monitor desktop launcher.

Build with:  pyinstaller meeting_monitor.spec --noconfirm

config.yaml, data/, logs/, models/ are intentionally NOT bundled here -
they live next to the built .exe (see src/utils/config.py's frozen-mode
path resolution) so users can edit settings and the app can write session
data without touching the read-only PyInstaller bundle.
"""
from PyInstaller.utils.hooks import collect_all

datas = [
    ("app.ico", "."),
    ("dashboard/dist", "dashboard_dist"),
]
binaries = []
hiddenimports = []

for pkg in (
    "mediapipe", "cv2", "uvicorn", "fastapi", "starlette", "pystray", "PIL",
    "pymongo", "bson", "dns", "passlib", "jwt", "dotenv", "email_validator", "bcrypt",
):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Sawala",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="app.ico",
)
