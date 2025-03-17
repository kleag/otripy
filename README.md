# Otripy - An open trip planning tool


[![PyPI Version](https://img.shields.io/pypi/v/otripy)](https://pypi.org/project/otripy)
[![License](https://img.shields.io/pypi/l/otripy)](https://github.com/kleag/otripy/blob/main/AGPL.md)
[![Downloads](https://static.pepy.tech/badge/otripy/month)](https://pepy.tech/project/otripy)
[![Supported Versions](https://img.shields.io/pypi/pyversions/otripy)](https://pypi.org/project/otripy)
[![Contributors](https://img.shields.io/github/contributors/kleag/otripy)](https://github.com/kleag/otripy/graphs/contributors)

<!--
![Python Versions](https://img.shields.io/pypi/pyversions/otripy)
![Build Status](https://img.shields.io/github/actions/workflow/status/kleag/otripy/ci.yml)
-->

## Description

Otripy is a GUI application for trip planning, providing an intuitive user interface for organizing travel visits efficiently. Otripy allows to plan a trip by adding markers on a map (based on OpenStreetMap) associated with a note.

Otripy is developed and daily tested on Linux. It should work on any platform. It has already been tested on MacOS.

Otripy is already usable but would be better with a lot of other features. Some wanted features are listed [here](https://github.com/kleag/otripy/issues). Don't hesitate to create a new issue if you think at other features. And contribute them if you can!

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
* Note text formatting (heading, bold, …)
* Image insertion (copy paste only currently)
* Change location markers icon and color

## Screenshots

![Otripy GUI snapshot](https://github.com/kleag/otripy/blob/main/pics/otripy-snapshot.png "Otripy GUI")

## Installation

### For users familiar with Python

Otripy is on PyPi. To install it, run:

```sh
pip install otripy
```

### For all others

If you are not used to installing Python packages, the simplest method is probably to use [uv](https://docs.astral.sh/uv/). Please [install it](https://docs.astral.sh/uv/getting-started/installation/) first. Then, open a terminal and create an uv virtual environment and activate it:


```sh
uv venv otripy
source otripy/bin/activate
```

Then install Otripy and run it:

```sh
uv pip install otripy
otripy
```

When you want to restart Otripy later, open your terminal, and run:

```sh
source otripy/bin/activate
otripy
```

Finally, to upgrade Otripy, to a new version, run:

```sh
source otripy/bin/activate
uv pip install otripy --upgrade
```

## Usage

To launch the application:
```bash
otripy
```

## Building and publishing

Otripy uses [uv](https://docs.astral.sh/uv/), please [install it](https://docs.astral.sh/uv/getting-started/installation/) if not already available.

If you just cloned this repository, cd to it and then:

```sh
uv venv
uv sync --all-extras
uv pip install -r pyproject.toml --extra build
install -d dist
```

Then, to build and publish:

```sh
rm dist/otripy-*
bumpver update --patch # or --minor or --major
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
This project is Free Software, licensed under the AGPL License. See the [AGPL](https://github.com/kleag/otripy/blob/main/AGPL.md) file for details. In summary: you can use it, share it, change it, redistribute your changes, but any version you offer, with or without changes must be under the same (or a compatible) license.

## Credits
Otripy is developed and maintained by [Kleag](https://github.com/kleag). Special thanks to all contributors!

---

For more information, visit the [GitHub repository](https://github.com/kleag/otripy) or the [PyPI page](https://pypi.org/project/otripy/).

