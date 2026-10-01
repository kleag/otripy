# Changelog

Notable changes to Otripy. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

## 1.3.1 - 2026-10-01

### Fixed

- The Windows and macOS installers contain the same tested versions of Qt and the other libraries as the other installations; those of 1.3.0 used the latest versions available when they were built.

## 1.3.0 - 2026-10-01

### Added

- French translation; Otripy follows the system's language ([#8](https://github.com/kleag/otripy/issues/8)). A [translators' guide](https://kleag.github.io/otripy/translating/) explains how to add languages.
- Installers for Windows (`.msi`), macOS 13 and later (`.dmg`) and Linux (AppImage), attached to each GitHub release.
- Application icon.
- Opening a trip zooms the map to show all its locations ([#25](https://github.com/kleag/otripy/issues/25)).
- *Tools* → *Distances…* measures the straight-line distance between two locations, and their route length and duration by car, bicycle or foot ([#6](https://github.com/kleag/otripy/issues/6)).
- *Tools* → *Show Route* draws the route through all the locations by car, bicycle or foot, with its length and duration ([#3](https://github.com/kleag/otripy/issues/3)). Routes come from the FOSSGIS servers behind openstreetmap.org.
- Hovering a location in the list highlights its marker on the map, and conversely; tooltips preview the note ([#22](https://github.com/kleag/otripy/issues/22)).
- Images in notes can be resized from their context menu; their size is saved with the trip ([#20](https://github.com/kleag/otripy/issues/20)).
- Ctrl+click opens links and web addresses in notes ([#5](https://github.com/kleag/otripy/issues/5)).
- *Settings* → *Auto Save* saves the trip after each action on its locations, not on each key typed ([#12](https://github.com/kleag/otripy/issues/12)).
- *File* → *Open Recent* reopens the last ten trips, local or on Nextcloud ([#11](https://github.com/kleag/otripy/issues/11)).
- When a Nextcloud file was changed or deleted on the server since it was opened, saving offers to overwrite it, besides saving under another name ([#10](https://github.com/kleag/otripy/issues/10)).
- *File* → *Save As Nextcloud…* (Ctrl+Alt+S) saves a trip to a new file on Nextcloud ([#28](https://github.com/kleag/otripy/issues/28)).
- *Settings* → *Confirm New Locations*: ask, showing the address, before adding a location where the map is clicked ([#30](https://github.com/kleag/otripy/issues/30)).
- The location list shows the icon of custom markers, in their color ([#27](https://github.com/kleag/otripy/issues/27)).
- The location list, the map and the note can be resized by dragging the separators between them; their sizes are kept for the next start ([#29](https://github.com/kleag/otripy/issues/29)).
- The Nextcloud password is stored in the system keyring instead of the settings file; an existing password is moved there on first use.
- `otripy --self-test` checks headless that an installation works.
- User guide at <https://kleag.github.io/otripy/>, with a description of the file format.

### Changed

- Nextcloud files are saved in the current file format, with its version information; Otripy 1.2.2 and earlier refuse to open them.
- *Quit* asks the same question as closing the window: save, discard or cancel.
- The map keeps its position and zoom when locations are added, changed or deleted, instead of jumping to the last location.
- New images in notes are named `image_<identifier>` instead of `dropped_image_<number>`.
- The license is declared as AGPL-3.0-or-later.
- Fewer dependencies: smaller installation.

### Fixed

- Cancelling *Save As*, or a failed save, marked the trip as saved: closing then lost the changes without warning.
- Choosing *Save* when closing quit even when the save failed or was cancelled.
- A file that failed to open replaced the open trip with an empty one.
- Network errors with Nextcloud or the place search are reported instead of being ignored.
- Images deleted from a note came back when the trip was reopened; images moved to another location's note were lost there and stayed in the original note ([#21](https://github.com/kleag/otripy/issues/21)); pasting an image into a note that already had images could be ignored.
- Dropping a location between two others, or below the list, failed: only drops onto another location worked.
- After a failed address lookup, note edits were no longer saved.
- A note title with quotes, a backslash or `</script>` broke the map.
- The title of a location added from the map included its whole address instead of the place's name.
- Titles showed Markdown escape characters such as `\[`.
- Markers without a custom icon lost their color when another location was selected.
- Changing a note's title updates its marker's tooltip and popup at once ([#26](https://github.com/kleag/otripy/issues/26)); they show the title as text, not HTML.
- Changing a marker's icon or color did not mark the trip as modified, so closing could lose it without warning.
- Cancelling the marker color dialog reset the marker to the default color.
- Otripy runs on Python 3.10 again.

## 1.2.3 - 2025-03-17

### Added

- Change the color of location markers.

## 1.2.2 - 2025-03-17

### Fixed

- Loading the marker icons.

## 1.2.1 - 2025-03-17

### Fixed

- Package content.

## 1.2.0 - 2025-03-17

### Added

- Versioned file format (1.0.0), with metadata such as creation and update dates. Files in the previous format still open.
- Change the icon of location markers, among the Font Awesome icons.

## 1.1.4 and earlier

See the [git history](https://github.com/kleag/otripy/commits/1.1.4).
