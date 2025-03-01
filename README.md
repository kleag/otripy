# Open Trip Plan

![PyPI Version](https://img.shields.io/pypi/v/opentripplan)
![License](https://img.shields.io/pypi/l/opentripplan)
![Python Versions](https://img.shields.io/pypi/pyversions/opentripplan)
![Build Status](https://img.shields.io/github/actions/workflow/status/kleag/opentripplan/ci.yml)

## Description

Open Trip Plan is a GUI application for trip planning, providing an intuitive user interface for organizing travel visits efficiently. Open Trip Plan allows to plan a trip by adding markers on a map (based on OpenStreetMap) associated with a note.

Open Trip Plan is developed and daily tested on Linux. It should work on any platform. It has already been tested on MacOS.

Open Trip Plan is already usable but would be better with a lot of other features. Some wanted features are listed [here](https://github.com/kleag/opentripplan/issues). Don't hesitate to create a new issue if you think at other features. And contribute them if you can!

### Current features:

* Display OpenStreetMap map
* Zoom and pan the map
* Adding location markers on the map
* List existing location on the left part of the GUI
* Associate a note to a location. The first line of the note is used as the title in the list
* Search location by name, and add a new marker when selecting an entry in the list
* Delete markers
* Open and save local files
* Open and save files on any Nextcloud server you have access to

## Screenshots

![Open Trip Plan GUI snapshot](https://github.com/kleag/opentripplan/blob/main/pics/opentripplan-snapshot.png "Open Trip Plan GUI")

## Installation

### For users familiar with Python

Open Trip Plan is on PyPi. To install it, run:

```sh
pip install opentripplan
```

### For all others

If you are not used to installing Python packages, the simplest method is probably to use [uv](https://docs.astral.sh/uv/). Please [install it](https://docs.astral.sh/uv/getting-started/installation/) first. Then, open a terminal and create an uv virtual environment and activate it:


```sh
uv venv opentripplan
source opentripplan/bin/activate
```

Then install OpenTripPlan and run it:

```sh
uv pip install opentripplan
opentripplan
```

## Usage

To launch the application:
```bash
opentripplan
```

## Building and publishing

OpenTripPlan uses [uv](https://docs.astral.sh/uv/), please [install it](https://docs.astral.sh/uv/getting-started/installation/) if not already available.

If you just cloned this repository, cd to it and then:

```sh
uv venv
uv sync --all-extras
uv pip install -r pyproject.toml --extra build
install -d dist
```

Then, to build and publish:

```sh
rm dist/opentripplan-*
bumpver update --patch
uv build
uv publish
uv sync --all-extras
git add uv.lock
git commit -m "Update lock to new package version"
```


## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature-name`).
3. Commit changes (`git commit -m "Add feature"`).
4. Push to your branch (`git push origin feature-name`).
5. Open a pull request.

## License
This project is licensed under the AGPL License. See the [LICENSE](https://github.com/kleag/opentripplan/blob/main/LICENSE.md) file for details.

## Credits
OpenTripPlan is developed and maintained by [Kleag](https://github.com/kleag). Special thanks to all contributors!

---

For more information, visit the [GitHub repository](https://github.com/kleag/opentripplan) or the [PyPI page](https://pypi.org/project/opentripplan/).

