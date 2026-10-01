# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Linux AppImage; run through build-appimage.sh.
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    # Icons are package data, invisible to PyInstaller's import scanner.
    # keyring discovers its backends through entry points in its package
    # metadata, which frozen builds do not include by default.
    datas=collect_data_files("otripy") + copy_metadata("keyring") + collect_data_files("certifi"),
    hiddenimports=collect_submodules("otripy") + collect_submodules("keyring.backends"),
    excludes=["tkinter"],
)

# Libraries every desktop has and that must match the user's system, as in
# the AppImage project's excludelist:
# - libxkbcommon: Qt's XCB plugin dlopen()s the system libxkbcommon-x11, which
#   must match libxkbcommon exactly, or the first key press crashes.
# - Mesa (gbm, drm, GL, EGL, glapi): loads the system's GPU drivers, which
#   must come from the same Mesa release ("did not find extension DRI_Mesa").
# - fontconfig, freetype: read the system's font configuration.
# - asound: loads the system's ALSA plugins.
SYSTEM_LIBRARIES = ("libxkbcommon", "libgbm.", "libdrm", "libGL", "libEGL", "libglapi",
                    "libfontconfig.", "libfreetype.", "libasound.")
a.binaries = [b for b in a.binaries if not b[0].startswith(SYSTEM_LIBRARIES)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="otripy",
    strip=False,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="otripy", strip=False, upx=False)
