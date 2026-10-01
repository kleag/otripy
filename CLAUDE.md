# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Otripy is a PySide6 desktop GUI for trip planning: locations are markers on an OpenStreetMap map (rendered with folium/Leaflet inside a `QWebEngineView`), each with a rich-text note. Journeys are saved as JSON locally or on a Nextcloud server. Licensed AGPL. Python >= 3.10: avoid 3.12-only syntax (e.g. reusing the same quote type inside f-strings) and take `override` from `typing_extensions`.

## Commands

The project uses [uv](https://docs.astral.sh/uv/).

```sh
uv venv && uv sync --all-extras          # set up dev environment
uv run otripy                             # launch the app (entry point: otripy.main:main)
python src/otripy/main.py                 # also works: modules fall back to non-relative imports
```

There is no test suite. Dev extras declare `pytest`, `black`, `ruff`, `mypy`, but no config for them exists in the repo.

Release (from README):

```sh
rm dist/otripy-*
bumpver update --patch     # bumps pyproject.toml + src/otripy/__init__.py, commits, tags, pushes
uv build && uv publish
uv sync --all-extras && git add uv.lock && git commit -m "Update lock to new package version"
```

Pushing a `v*.*.*` tag triggers `.github/workflows/release.yml`, which builds Windows (.msi) and macOS (.app, notarized) bundles with Briefcase (`[tool.briefcase]` in `pyproject.toml`) and attaches them to a GitHub release. bumpver's `version = "{version}"` pattern updates both the `[project]` and `[tool.briefcase]` versions.

## Architecture

- **`main.py` — `MapApp(QMainWindow)`** owns everything: menus, search bar, map view, lat/lon fields, formatting toolbar, note editor, location list. Most app logic lives here.
- **Map rendering is regenerated wholesale.** `MapApp.update_map()` builds a fresh `folium.Map`, injects a hand-written JS string (one `L.AwesomeMarkers` marker per location, stored in `window.markerMap[lid]`), and calls `setHtml` on the page. Any change to a location's position/icon/color calls `update_map()`. Highlighting/moving uses `runJavaScript` (`highlight_marker`, `downplay_marker`, `moveMap`).
- **JS ↔ Python bridge** is a `QWebChannel` registering two objects: `pyObj` (the `MapApp`; JS calls its `receiveData` slot on map click → reverse-geocode → `add_location`) and `markerHandler` (`MarkerHandler.on_marker_clicked` → select the location in the list). Methods called from JS must be `@Slot`s.
- **Data model:** `Location` (`location.py`: `lid` UUID, `lat`, `lon`, `note` dict with a `"markdown"` key, optional `marker` FontAwesome icon name and `color`). The first line of the note markdown is the location's label. `Journey` (`journey.py`) is a `QObject` list of `Location`s that emits a `dirty` signal on mutation. That signal drives the `*` in the window title. `LocationListModel`/`LocationListView` (`location_list_view.py`) wrap a `Journey`. After replacing the journey (`setLocations`), `main.py` reconnects `dirty` to `set_window_title`.
- **File format** (`Journey.write_to_file` / `load_from_json`): an object with `format: "otripy"`, `format_version` (`CURRENT_FORMAT_VERSION`), `app_version`, timestamps, and `locations`. A bare JSON list is accepted as the legacy pre-1.0.0 format. Loading refuses files whose app or format version is newer than the running one. The app version is read at runtime by parsing `__version__` in `src/otripy/__init__.py`. Caveat: `MapApp.save_file` for Nextcloud files still uploads the legacy bare-list format.
- **Notes:** `NoteWidget` (`note_widget.py`, a `QTextEdit`) converts to and from the note dict via `toMarkdown`/`setMarkdown`. Pasted images are handled in `insertFromMimeData`.
- **Nextcloud:** URL and username are stored in `QSettings("Kleag", "Otripy")` under `nextcloud/*`; the password goes in the system keyring via `config.load_nextcloud_password`/`save_nextcloud_password`, which migrate an old plaintext `nextcloud/password` setting and fall back to it when no keyring backend is available. Settings are edited via `config.py` `ConfigDialog`. `nextcloud_with_api.py` (`nc_py_api`) is the file picker in use.
- **Icons:** SVGs in `src/otripy/resources/icons/` (FontAwesome names) are loaded via `importlib.resources.files("otripy.resources.icons")`. The `__init__.py` files there are required. The wheel ships every non-gitignored file under `src/otripy`, but the sdist only ships what its `include` list in `pyproject.toml` names, so add new asset types there.
- **App icon:** `src/otripy/resources/icon-<size>.png` (set as window icon in `main()`), `icon.ico` and `icon.icns` (Briefcase, via `[tool.briefcase.app.otripy] icon`). All are generated from the 1024px master `design/otripy-icon.png` with Pillow.
- **`export_html2.py`** is an experiment for exporting a standalone HTML map. It is imported, but its menu action is commented out. Root-level untracked files (`map.html`, `index.html`, `script.js`, `test*.json`, …) are scratch artifacts, not part of the package.

## Conventions

- Every intra-package import uses a `try: from .x import ...` / `except ImportError: from x import ...` pair so modules run both as a package and as scripts. Keep this pattern when adding imports.
- Logging goes through `logging.getLogger(__name__)`. Many debug log calls are left commented out rather than removed.

## Roadmap

Planned work (stabilization, tests, CI/deployment, docs, features) is tracked as a checklist in `ROADMAP.md`. Tick items there when completing them.
