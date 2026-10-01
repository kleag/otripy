# Otripy Roadmap

Otripy was first written in one go. This roadmap organizes the work to make it maintainable: stabilization, tests, deployment, documentation, then features. Phases are roughly ordered; items within a phase are independent unless noted.

Feature requests and bugs are tracked as [GitHub issues](https://github.com/kleag/otripy/issues); they are referenced here as `#N`.

## Phase 0 — Stabilize

- [x] Nextcloud save writes the legacy bare-list format instead of the versioned format (`MapApp.save_file`); unify local and Nextcloud saving through `Journey.write_to_file`
- [x] Escape note labels/popups injected into the generated map JavaScript (quotes or newlines in a note break the map; possibly related to #26)
- [x] Fix Python version mismatch: `typing.override` (in `note_widget.py`) requires 3.12 but `requires-python = ">=3.10"`
- [x] Store the Nextcloud password in the system keyring instead of plaintext `QSettings`
- [x] Remove unused modules: `nextcloud.py`, `nextcloud_uuid.py`, `export_html.py`, `export_html3.py`–`export_html6.py`, `src/color_picker_demo.py`, `src/map_script.js`

## Phase 1 — Tests

- [x] Add `pytest`, `pytest-qt` and a `ruff` configuration (error and bugbear rules; style rules to add later); run Qt tests headless (`QT_QPA_PLATFORM=offscreen`)
- [x] Unit tests for `Location` and `Journey` using `tests/fixtures/`: JSON round-trip, legacy list format, rejection of newer app/format versions, `dirty` signal emission
- [x] Extract map HTML/JS generation from `MapApp.update_map` into a pure function and test it (including escaping)
- [x] Replace the `pyObj` web channel registration of the whole `MapApp` window with a small bridge object exposing only `receiveData` (registering the window floods the log with "has no notify signal" warnings)
- [x] Extract load/save logic from `MapApp` so it can be tested without the GUI
- [x] `pytest-qt` tests for `LocationListModel` and `NoteWidget` note round-trip (markdown + images, see #21)
- [x] Mock Nominatim geocoding and Nextcloud in tests

## Phase 2 — CI and deployment

- [x] Commit a rewritten `.github/workflows/release.yml` (never committed so far; its `v*.*.*` trigger does not match bumpver's `1.2.3` tags)
- [x] CI workflow on push/PR: ruff + pytest on Linux/macOS/Windows and supported Python versions
- [x] Publish to PyPI on version tag using trusted publishing (replace manual `uv publish`); needs the trusted publisher configured on pypi.org
- [x] Fix macOS release job: ad-hoc signed DMG (no Apple Developer ID, so no notarization), macOS 13+ as required by PySide6
- [ ] Run the release workflow by hand (workflow_dispatch) and test the Windows `.msi` and macOS `.dmg` on real machines
- [x] Add a Linux bundle: AppImage built with PyInstaller on Ubuntu 22.04 (Briefcase's AppImage support is unreliable for PySide6); Flatpak only if publishing on Flathub
- [ ] Pin Briefcase `requires` to the locked versions, so all platforms ship the tested PySide6
- [x] Declare the license as an SPDX expression (PEP 639): AGPL-3.0-or-later

## Phase 3 — Documentation

- [x] README and user guide site (GitHub Pages, MkDocs Material): installation per platform, usage; build/publish moved to CONTRIBUTING.md
- [x] Update the screenshot
- [x] `docs/file-format.md`: the `.json` journey format and its versioning rules
- [x] `CONTRIBUTING.md`: dev setup, running tests, release procedure
- [x] `CHANGELOG.md`
- [x] Credit Font Awesome Free (icons are CC BY 4.0, attribution required) in the README and next to `resources/icons/`
- [x] Include the full MIT notice for `toolbar.py` (borrowed from Notolog Editor)
- [x] Docstrings for the model classes (`Location`, `Journey`, list model)

## Phase 4 — Features

### Bugs
- [x] #21 Moved (cut and paste) images are duplicated
- [x] #26 Text popup over markers is not always updated

### Quick wins
- [x] #25 Fit map to all markers when opening a file
- [x] #27 Show the location icon in the list entry
- [x] #28 "Save as…" to Nextcloud
- [x] #29 Resizable side panels
- [x] #30 Confirm/validate button for location addition
- [x] #31 Create and add an application icon

### File handling
- [x] #10 Improve handling of changed file check (merging changes left for later)
- [x] #11 Recent Files menu
- [x] #12 Auto-save option

### Notes
- [x] #5 Clickable links in notes
- [x] #20 Resizable images in notes
- [ ] #19 General notes page not linked to a location (file format change)

### Map and organization
- [x] #22 Highlight marker on hover
- [ ] #18 Group locations under a common title (file format change)
- [x] #6 Distance measurement tool
- [x] #3 Route calculation between locations: car, bicycle, foot (FOSSGIS OSRM)
- [ ] #3 Public transport routes and electric car charging stops (no free service found)

### Cross-cutting
- [x] #8 Make the GUI translatable (English, French)

Items marked *file format change* should wait until the format is documented and covered by tests, and must bump `CURRENT_FORMAT_VERSION` in `journey.py`.
