#!/bin/sh
# Build dist/Otripy-<version>-x86_64.AppImage with PyInstaller and appimagetool.
#
# Meant to run on Ubuntu 22.04 (glibc 2.35, the oldest base current PySide6
# wheels support): the AppImage then runs on that release and newer
# distributions. CI runs it on the ubuntu-22.04 runner; locally, run it in a
# container from the repository root:
#
#   docker run --rm -v "$PWD:/src" -w /src -e HOST_UID="$(id -u):$(id -g)" \
#       ubuntu:22.04 packaging/linux/build-appimage.sh
set -eu
cd "$(dirname "$0")/../.."

SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"
export DEBIAN_FRONTEND=noninteractive

# Build tools, plus the desktop libraries the frozen app expects from the
# system (PyInstaller does not bundle graphics and windowing libraries),
# needed here to run the self-test.
$SUDO apt-get update -q
$SUDO apt-get install -y -q --no-install-recommends \
    ca-certificates curl binutils file desktop-file-utils \
    libegl1 libgl1 libglib2.0-0 libfontconfig1 libdbus-1-3 libxkbcommon0 libxkbcommon-x11-0 \
    libnss3 libxcomposite1 libxdamage1 libxrandr2 libxtst6 libxkbfile1 libasound2 libatomic1 libxi6 \
    libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0

if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
fi

# Same Python everywhere, and a virtual environment of our own: never touch
# the developer's .venv when run in a container on a mounted checkout.
export UV_PYTHON=3.12 UV_PYTHON_PREFERENCE=only-managed
export UV_PROJECT_ENVIRONMENT=build/appimage/venv
uv sync --frozen --no-dev --group appimage
VERSION=$(uv version --short)

uv run --frozen --no-dev --group appimage pyinstaller --noconfirm --clean \
    --distpath build/appimage/dist --workpath build/appimage/work packaging/linux/otripy.spec

# Chromium refuses to run its sandbox as root or without user namespaces,
# both common on build machines; this only affects the self-test.
QTWEBENGINE_DISABLE_SANDBOX=1 build/appimage/dist/otripy/otripy --self-test build/appimage/self-test.txt

APPDIR=build/appimage/Otripy.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a build/appimage/dist/otripy "$APPDIR/usr/lib/otripy"
cp src/otripy/resources/icon-256.png "$APPDIR/otripy.png"
ln -s otripy.png "$APPDIR/.DirIcon"
cat > "$APPDIR/otripy.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Otripy
Comment=Plan your trips on an OpenStreetMap map
Exec=otripy
Icon=otripy
Categories=Utility;Maps;
DESKTOP
desktop-file-validate "$APPDIR/otripy.desktop"
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/otripy/otripy" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

curl -LsSf -o build/appimage/appimagetool \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x build/appimage/appimagetool
mkdir -p dist
ARCH=x86_64 build/appimage/appimagetool --appimage-extract-and-run "$APPDIR" "dist/Otripy-$VERSION-x86_64.AppImage"

if [ -n "${HOST_UID:-}" ]; then
    chown -R "$HOST_UID" build dist
fi
