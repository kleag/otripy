# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Otripy is a PySide6 desktop GUI for trip planning: locations are markers on an OpenStreetMap map (rendered with folium/Leaflet inside a `QWebEngineView`), each with a rich-text note. Journeys are saved as JSON locally or on a Nextcloud server. Licensed AGPL. Python >= 3.10: avoid 3.12-only syntax (e.g. reusing the same quote type inside f-strings) and take `override` from `typing_extensions`.

## Commands

The project uses [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                   # set up the dev environment (dev group: pytest, pytest-qt, ruff)
uv run otripy                             # launch the app (entry point: otripy.main:main)
uv run pytest                             # run the tests (headless: conftest sets QT_QPA_PLATFORM=offscreen)
uv run pytest tests/test_journey.py::test_load_legacy_list   # a single test
uv run ruff check src tests               # lint (rules in [tool.ruff.lint])
```

Documentation: the user guide is an MkDocs Material site in `docs/` (`mkdocs.yml`), published to https://kleag.github.io/otripy/ by `.github/workflows/docs.yml` (GitHub Pages, Actions source). Preview with `uv run --group docs mkdocs serve`; CI builds with `mkdocs build --strict`, which fails on broken links. Installation and usage are documented only there (README links to them). `docs/contributing.md` and `docs/changelog.md` include the root `CONTRIBUTING.md` and `CHANGELOG.md` (pymdownx.snippets), so links in those root files must be absolute URLs. Add user-visible changes to the *Unreleased* section of `CHANGELOG.md`; describe file format changes in `docs/file-format.md`.

Testing notes:
- Journey fixtures for each supported file shape are in `tests/fixtures/` (see its README); use the `fixture_text` fixture.
- Tests that build a `MapApp` must stub modal dialogs (`QMessageBox.question`, `critical`, `QFileDialog.*`) via `monkeypatch` on `otripy.main`, or the run hangs, including at teardown when the journey is modified. They also stub `map_page.setHtml`/`runJavaScript`. See `tests/test_file_handling.py` for scripted dialogs and an in-memory Nextcloud fake.
- Geocoding goes through `MapApp.geolocator`; replace it with a fake object, never hit Nominatim.
- JavaScript generated in `map_view.py` is syntax-checked with `node --check` (tests skip if node is missing).

CI (`.github/workflows/ci.yml`) runs ruff and pytest on Linux, Windows and macOS with Python 3.10 and 3.13.

Release:

```sh
bumpver update --patch     # bumps the version in pyproject.toml ([project] and [tool.briefcase]) and src/otripy/__init__.py, commits, tags (MAJOR.MINOR.PATCH, no "v") and pushes
```

The tag triggers `.github/workflows/release.yml`: it checks the tag matches the version, builds the sdist and wheel, publishes them to PyPI (trusted publishing, `pypi` environment), builds a Windows MSI and an ad-hoc signed (not notarized) macOS DMG with Briefcase, and attaches everything to a GitHub release. Running the workflow by hand only builds. The Linux AppImage is built differently, with PyInstaller (`packaging/linux/otripy.spec`) and appimagetool, by `packaging/linux/build-appimage.sh` on Ubuntu 22.04 (the oldest base current PySide6 wheels support); locally: `docker run --rm -v "$PWD:/src" -w /src -e HOST_UID="$(id -u):$(id -g)" ubuntu:22.04 packaging/linux/build-appimage.sh` → `dist/Otripy-<version>-x86_64.AppImage`. It uses the locked versions (`appimage` dependency group for PyInstaller). Frozen builds have no `.py` sources and no package metadata unless the spec collects them: never read package files as source, and add data files or entry-point metadata to the spec. `otripy --self-test` (`self_test.py`) checks a build headless; the build script runs it on the frozen app.

Briefcase starts the app with `python -m otripy` (`__main__.py`) and installs `[tool.briefcase.app.otripy] requires`, which must be kept in sync with `[project] dependencies`.

## Architecture

- **`main.py` — `MapApp(QMainWindow)`** owns the UI: menus, search bar, map view, lat/lon fields, formatting toolbar, note editor, location list, and file handling (`set_journey`, `confirm_discard`, `load_file`/`load_nc_file`, `save_*` methods returning whether the journey was saved; a failed or cancelled save must leave the journey dirty).
- **Map rendering is regenerated wholesale.** `map_view.build_map_html(locations)` builds a fresh `folium.Map` with one `L.AwesomeMarkers` marker per location (stored in `window.markerMap[lid]`); `MapApp.update_map()` passes it to `setHtml`. Any change to a location's position/icon/color calls `update_map()`. Highlighting/moving runs snippets from `map_view` (`highlight_marker_js`, `downplay_marker_js`, `move_map_js`) with `runJavaScript`. Every value interpolated into JavaScript must go through `map_view.js_string`.
- **JS ↔ Python bridge** is a `QWebChannel` with one registered object, `mapBridge` (`map_view.MapBridge`): its `on_map_clicked(lat, lon)` and `on_marker_clicked(id)` slots re-emit `mapClicked`/`markerClicked`, connected to `MapApp.add_location_at` (reverse-geocode → new location) and `MapApp.handle_marker_click`. Methods called from JS must be `@Slot`s.
- **Data model:** `Location` (`location.py`: `lid` UUID, `lat`, `lon`, `note` dict with a `"markdown"` key, optional `marker` FontAwesome icon name and `color`). The first line of the note markdown, with heading marks and markdown escapes removed, is the location's label (`Location.label()`); `to_html()` is that label HTML-escaped, for popups. `Journey` (`journey.py`) is a `QObject` list of `Location`s that emits a `dirty` signal on mutation. That signal drives the `*` in the window title. `LocationListModel`/`LocationListView` (`location_list_view.py`) wrap a `Journey`. After replacing the journey (`setLocations`), `main.py` reconnects `dirty` to `set_window_title`.
- **File format** (`Journey.save`/`to_json_str`/`write_to_file`, `from_file`/`from_json_str`): an object with `format: "otripy"`, `format_version` (`CURRENT_FORMAT_VERSION`), `app_version`, timestamps, and `locations`. A bare JSON list is accepted as the legacy pre-1.0.0 format. Loading refuses files whose app or format version is newer than the running one. Invalid files raise `ValueError`. The app version is read at runtime by parsing `__version__` in `src/otripy/__init__.py`. Changing the format requires updating `docs/file-format.md` and adding a fixture; bump `CURRENT_FORMAT_VERSION` unless the change is an optional field older versions can ignore (older Otripy refuses newer format versions).
- **Notes:** `NoteWidget` (`note_widget.py`, a `QTextEdit`) converts to and from the note dict via `toMarkdown`/`setMarkdown`. A single `NoteWidget` is reused for every location. Images are document resources, referenced in the markdown as `![image](name)` and saved in `note["images"]` as base64 PNG; `to_note()` saves exactly the referenced images. New images get unique `image_<uuid>` names. Cut/copy adds the selected images' data in an `application/x-otripy-images` clipboard format so they survive a paste into another note.
- **Nextcloud:** URL and username are stored in `QSettings("Kleag", "Otripy")` under `nextcloud/*`; the password goes in the system keyring via `config.load_nextcloud_password`/`save_nextcloud_password`, which migrate an old plaintext `nextcloud/password` setting and fall back to it when no keyring backend is available. Settings are edited via `config.py` `ConfigDialog`. `nextcloud_with_api.py` (`nc_py_api`) is the file picker in use.
- **Icons:** SVGs in `src/otripy/resources/icons/` (FontAwesome names) are loaded via `importlib.resources.files("otripy.resources.icons")`. The `__init__.py` files there are required. The wheel ships every non-gitignored file under `src/otripy`, but the sdist only ships what its `include` list in `pyproject.toml` names, so add new asset types there.
- **App icon:** `src/otripy/resources/icon-<size>.png` (set as window icon in `main()`), `icon.ico` and `icon.icns` (Briefcase, via `[tool.briefcase.app.otripy] icon`). All are generated from the 1024px master `design/otripy-icon.png` with Pillow.
- **`export_html2.py`** is an unused experiment for exporting a standalone HTML map (its menu action in `main.py` is commented out).

## Conventions

- User-visible texts must be translatable (issue #8): `self.tr("…")` in Qt classes, `QCoreApplication.translate("Context", "…")` elsewhere, `QT_TRANSLATE_NOOP` for module constants; never f-strings, use `.format()` with named placeholders. Then run `uv run python scripts/translations.py` and translate the new texts in `src/otripy/i18n/otripy_fr.ts` (tests fail on missing, unfinished or stale translations). `translations.install_translators()` loads Otripy's and Qt's `.qm` for the system language or `OTRIPY_LANGUAGE`. See `docs/translating.md`.

- Every intra-package import uses a `try: from .x import ...` / `except ImportError: from x import ...` pair so modules run both as a package and as scripts. Keep this pattern when adding imports.
- Logging goes through `logging.getLogger(__name__)`. Many debug log calls are left commented out rather than removed.

## Roadmap

Planned work (stabilization, tests, CI/deployment, docs, features) is tracked as a checklist in `ROADMAP.md`. Tick items there when completing them.
