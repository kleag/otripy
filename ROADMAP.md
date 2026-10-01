# Otripy Roadmap

Otripy was first written in one go. This roadmap organizes the work to make it maintainable: stabilization, tests, deployment, documentation, then features. Phases are roughly ordered; items within a phase are independent unless noted.

Feature requests and bugs are tracked as [GitHub issues](https://github.com/kleag/otripy/issues); they are referenced here as `#N`.

## Phase 0 — Stabilize

- [ ] Nextcloud save writes the legacy bare-list format instead of the versioned format (`MapApp.save_file`); unify local and Nextcloud saving through `Journey.write_to_file`
- [ ] Escape note labels/popups injected into the generated map JavaScript (quotes or newlines in a note break the map; possibly related to #26)
- [ ] Fix Python version mismatch: `typing.override` (in `note_widget.py`) requires 3.12 but `requires-python = ">=3.10"`
- [ ] Store the Nextcloud password in the system keyring instead of plaintext `QSettings`
- [ ] Remove unused modules: `nextcloud.py`, `nextcloud_uuid.py`, `export_html.py`, `export_html3.py`–`export_html6.py`, `src/color_picker_demo.py`, `src/map_script.js`
- [ ] Add `[tool.briefcase] version` to `bumpver` file patterns

## Phase 1 — Tests

- [ ] Add `pytest`, `pytest-qt` and a `ruff` configuration; run Qt tests headless (`QT_QPA_PLATFORM=offscreen`)
- [ ] Unit tests for `Location` and `Journey`: JSON round-trip, legacy list format, rejection of newer app/format versions, `dirty` signal emission
- [ ] Extract map HTML/JS generation from `MapApp.update_map` into a pure function and test it (including escaping)
- [ ] Extract load/save logic from `MapApp` so it can be tested without the GUI
- [ ] `pytest-qt` tests for `LocationListModel` and `NoteWidget` note round-trip (markdown + images, see #21)
- [ ] Mock Nominatim geocoding and Nextcloud in tests

## Phase 2 — CI and deployment

- [ ] CI workflow on push/PR: ruff + pytest on Linux/macOS/Windows and supported Python versions
- [ ] Publish to PyPI on version tag using trusted publishing (replace manual `uv publish`)
- [ ] Fix macOS release job: notarize and attach a zip/DMG rather than a bare `.app` directory
- [ ] Add a Linux bundle (AppImage or Flatpak via Briefcase)
- [ ] Verify the Windows `.msi` build end to end

## Phase 3 — Documentation

- [ ] README: user guide with screenshots; fix the build/publish section
- [ ] `docs/file-format.md`: the `.json` journey format and its versioning rules
- [ ] `CONTRIBUTING.md`: dev setup, running tests, release procedure
- [ ] `CHANGELOG.md`
- [ ] Docstrings for the model classes (`Location`, `Journey`, list model)

## Phase 4 — Features

### Bugs
- [ ] #21 Moved (cut and paste) images are duplicated
- [ ] #26 Text popup over markers is not always updated

### Quick wins
- [ ] #25 Fit map to all markers when opening a file
- [ ] #27 Show the location icon in the list entry
- [ ] #28 "Save as…" to Nextcloud
- [ ] #29 Resizable side panels
- [ ] #30 Confirm/validate button for location addition
- [ ] #31 Create and add an application icon

### File handling
- [ ] #10 Improve handling of changed file check
- [ ] #11 Recent Files menu
- [ ] #12 Auto-save option

### Notes
- [ ] #5 Clickable links in notes
- [ ] #20 Resizable images in notes
- [ ] #19 General notes page not linked to a location (file format change)

### Map and organization
- [ ] #22 Highlight marker on hover
- [ ] #18 Group locations under a common title (file format change)
- [ ] #6 Distance measurement tool
- [ ] #3 Route calculation between locations

### Cross-cutting
- [ ] #8 Make the GUI translatable

Items marked *file format change* should wait until the format is documented and covered by tests, and must bump `CURRENT_FORMAT_VERSION` in `journey.py`.
