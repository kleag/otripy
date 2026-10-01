# Contributing to Otripy

Contributions are welcome: bug reports and ideas in the [issues](https://github.com/kleag/otripy/issues), code through pull requests. The planned work is in the [roadmap](https://github.com/kleag/otripy/blob/main/ROADMAP.md).

## Development setup

Otripy uses [uv](https://docs.astral.sh/uv/) ([installation](https://docs.astral.sh/uv/getting-started/installation/)). From a clone of the repository:

```sh
uv sync          # creates .venv with Otripy and the development tools
uv run otripy    # runs Otripy from the sources
```

Otripy supports Python 3.10 and later: avoid syntax and standard library features of newer versions.

## Tests and lint

```sh
uv run pytest                                      # all tests
uv run pytest tests/test_journey.py                # one file
uv run pytest tests/test_journey.py::test_load_legacy_list   # one test
uv run ruff check src tests                        # lint
```

The tests run without a display (Qt's offscreen platform) and without network access to Nominatim or Nextcloud, which are replaced by fakes. A few notes for writing tests:

* Journey files of each supported shape are in `tests/fixtures/`; use the `fixture_text` fixture to read them.
* Tests that create the main window must replace modal dialogs (`QMessageBox`, `QFileDialog`) with `monkeypatch`, or the run blocks: see `tests/test_file_handling.py`.
* The JavaScript generated for the map is syntax-checked with Node.js when it is installed.

GitHub Actions runs the lint and the tests on Linux, Windows and macOS, with Python 3.10 and 3.13, for every pull request.

## Pull requests

1. Fork the repository and create a branch (`git checkout -b feature-name`).
2. Make your changes, with tests for new behavior and bug fixes.
3. Check that `uv run pytest` and `uv run ruff check src tests` pass.
4. Add a line to the *Unreleased* section of [CHANGELOG.md](https://github.com/kleag/otripy/blob/main/CHANGELOG.md) for user-visible changes.
5. Push your branch and open a pull request.

Changes to the journey file format must follow the rules at the end of [the file format description](https://kleag.github.io/otripy/file-format/).

## Documentation

The user guide is published at <https://kleag.github.io/otripy/> from the `docs/` directory with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). To preview it:

```sh
uv run --group docs mkdocs serve
```

It is published by GitHub Actions on every push to `main` that changes it.

## Releases

Versions are managed with [bumpver](https://github.com/mbarkhau/bumpver), which updates the version in `pyproject.toml` and `src/otripy/__init__.py`, then commits, tags and pushes:

```sh
uv run --with bumpver bumpver update --patch   # or --minor, --major
```

Before, move the *Unreleased* entries of the changelog under the new version.

The tag (`MAJOR.MINOR.PATCH`) starts the release workflow, which:

* publishes the sdist and wheel to [PyPI](https://pypi.org/project/otripy) (trusted publishing, no token);
* builds the Windows installer (`.msi`) and the macOS disk image (`.dmg`) with [Briefcase](https://briefcase.readthedocs.io);
* builds the Linux AppImage with PyInstaller and appimagetool;
* attaches all of them to a GitHub release.

Run the *Release* workflow by hand (*Actions* → *Release* → *Run workflow*) to build everything without publishing.

### Building the AppImage locally

The AppImage is built on Ubuntu 22.04, the oldest base that current PySide6 versions support. With Docker, from the repository root:

```sh
docker run --rm -v "$PWD:/src" -w /src -e HOST_UID="$(id -u):$(id -g)" \
    ubuntu:22.04 packaging/linux/build-appimage.sh
```

The result is `dist/Otripy-<version>-x86_64.AppImage`. The build runs `otripy --self-test` on the packaged application, which checks headless that it has everything it needs; you can run it on any installed Otripy too.
