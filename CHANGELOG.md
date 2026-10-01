# Changelog

Notable changes to Otripy. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

- Installers for Windows (`.msi`), macOS 13 and later (`.dmg`) and Linux (AppImage), attached to each GitHub release.
- Application icon.
- Opening a trip zooms the map to show all its locations ([#25](https://github.com/kleag/otripy/issues/25)).
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
