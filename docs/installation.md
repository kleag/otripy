# Installation

Ready-to-use installers are attached to each [release](https://github.com/kleag/otripy/releases/latest).

## Windows

Download and run `Otripy-<version>.msi`. The installer is not signed, so Windows SmartScreen may warn about an unknown publisher: choose *More info*, then *Run anyway*.

## macOS

Requires macOS 13 (Ventura) or later.

Download `Otripy-<version>.dmg`, open it and drag Otripy to your Applications folder.

The app is not notarized by Apple, so macOS blocks it the first time: open it once, then go to *System Settings* → *Privacy & Security* and click *Open Anyway* next to the message about Otripy.

## Linux

Download `Otripy-<version>-x86_64.AppImage`, make it executable and run it:

```sh
chmod +x Otripy-*-x86_64.AppImage
./Otripy-*-x86_64.AppImage
```

It runs on Ubuntu 22.04, Debian 12, Fedora, RHEL 9 and other distributions of the same age or newer. To add it to your applications menu, you can use a tool such as [Gear Lever](https://flathub.org/apps/it.mijorus.gearlever).

## From PyPI (all platforms)

Otripy is on [PyPI](https://pypi.org/project/otripy). The simplest way to install it as an application is with [uv](https://docs.astral.sh/uv/) ([installation instructions](https://docs.astral.sh/uv/getting-started/installation/)):

```sh
uv tool install otripy
otripy
```

Upgrade it later with `uv tool upgrade otripy`. With [pipx](https://pipx.pypa.io), the commands are `pipx install otripy` and `pipx upgrade otripy`.

