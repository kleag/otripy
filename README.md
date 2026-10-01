# Otripy - An open trip planning tool

[![PyPI Version](https://img.shields.io/pypi/v/otripy)](https://pypi.org/project/otripy)
[![License](https://img.shields.io/pypi/l/otripy)](https://github.com/kleag/otripy/blob/main/AGPL.md)
[![Downloads](https://static.pepy.tech/badge/otripy/month)](https://pepy.tech/project/otripy)
[![Supported Versions](https://img.shields.io/pypi/pyversions/otripy)](https://pypi.org/project/otripy)
[![CI](https://img.shields.io/github/actions/workflow/status/kleag/otripy/ci.yml?branch=main&label=CI)](https://github.com/kleag/otripy/actions/workflows/ci.yml)
[![Contributors](https://img.shields.io/github/contributors/kleag/otripy)](https://github.com/kleag/otripy/graphs/contributors)

## Description

Otripy is a desktop application for trip planning. You plan a trip by adding locations on an [OpenStreetMap](https://www.openstreetmap.org) map, each with a note: text with formatting and images. Trips are saved as files on your computer or on a [Nextcloud](https://nextcloud.com) server.

Otripy is developed and used daily on Linux, and packaged for Windows and macOS too.

Otripy is already usable but would be better with a lot of other features. Some wanted features are listed [in the issues](https://github.com/kleag/otripy/issues). Don't hesitate to open a new issue with your ideas, and to contribute them if you can!

### Features

* OpenStreetMap map, with zoom and pan
* Add a location by clicking on the map: its note starts with the place's name and address
* Search places by name and add them from the results
* List of locations, reorderable by drag and drop; the first line of a note is the location's title
* Notes with formatting (headings, bold, italic, underline, strikethrough) and images
* Marker icon and color for each location
* Open and save trips as local files
* Open and save trips on any Nextcloud server you have access to
* Distances and routes between locations, by car, bicycle or foot

## Screenshots

![Otripy GUI snapshot](https://raw.githubusercontent.com/kleag/otripy/main/docs/assets/screenshot.png "Otripy GUI")

## Installation

Ready-to-use installers for Windows, macOS (13 or later) and Linux (AppImage) are attached to each [release](https://github.com/kleag/otripy/releases/latest). Otripy is also on [PyPI](https://pypi.org/project/otripy); with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install otripy
otripy
```

See the [installation guide](https://kleag.github.io/otripy/installation/) for each platform's details.

## Documentation

The [user guide](https://kleag.github.io/otripy/) explains how to [use Otripy](https://kleag.github.io/otripy/usage/), including Nextcloud, and describes its [file format](https://kleag.github.io/otripy/file-format/).

## Contributing

Contributions are welcome! Translations into new languages are welcome too: see the [translators' guide](https://kleag.github.io/otripy/translating/). See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, the tests and the release process, and [ROADMAP.md](ROADMAP.md) for the planned work. Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

Otripy is Free Software, licensed under the GNU Affero General Public License, version 3 or later. See the [AGPL](AGPL.md) file for details. In summary: you can use it, share it, change it, redistribute your changes, but any version you offer, with or without changes, must be under the same (or a compatible) license.

## Credits

Otripy is developed and maintained by [Kleag](https://github.com/kleag). Special thanks to all contributors!

Otripy builds on:

* Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the Open Database License. Place search and addresses come from OpenStreetMap's [Nominatim](https://nominatim.org) service, used under its [usage policy](https://operations.osmfoundation.org/policies/nominatim/).
* Routes are computed by the [FOSSGIS OSRM servers](https://routing.openstreetmap.de/about.html) behind openstreetmap.org, used under their usage policy.
* Maps are displayed with [Leaflet](https://leafletjs.com), through [folium](https://python-visualization.github.io/folium/), with markers from [Leaflet.awesome-markers](https://github.com/lennardv2/Leaflet.awesome-markers).
* Marker and toolbar icons are [Font Awesome Free](https://fontawesome.com) icons by Fonticons, Inc., licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [the icons' license notice](src/otripy/resources/icons/LICENSE.md)).
* The toolbar code comes from [Notolog Editor](https://github.com/notolog/notolog-editor) by Vadim Bakhrenkov, under the MIT License (see the notice in [toolbar.py](src/otripy/toolbar.py)).
* The user interface uses [Qt](https://www.qt.io) through [PySide6](https://doc.qt.io/qtforpython-6/).

---

For more information, visit the [GitHub repository](https://github.com/kleag/otripy) or the [PyPI page](https://pypi.org/project/otripy/).
