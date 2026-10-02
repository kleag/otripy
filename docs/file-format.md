# Otripy journey file format

A journey (a trip) is saved as a UTF-8 JSON file, usually with the `.json` extension. This describes format version **1.1.0**, written by Otripy 1.4.0 and later, and the 1.0.0 format it extends.

Otripy writes the oldest format that can hold a journey: **1.0.0** for journeys without groups nor trip notes, **1.1.0** otherwise. Format 1.1.0 adds:

* `notes` at the top level: the trip's general notes ([#19](https://github.com/kleag/otripy/issues/19));
* `groups` at the top level, and `group` in locations: titled sections of the location list ([#18](https://github.com/kleag/otripy/issues/18)).

## Top level

```json
{
    "format": "otripy",
    "description": "A Journey with Otripy",
    "format_version": "1.0.0",
    "app_version": "1.2.3",
    "app_name": "Otripy",
    "created_at": "2025-03-16T14:20:41.146103+00:00",
    "updated_at": "2025-03-17T18:43:54.281403+00:00",
    "encoding": "UTF-8",
    "settings": {},
    "locations": [ ... ]
}
```

| Key | Type | Meaning |
|---|---|---|
| `format` | string | Always `"otripy"`. Files without it are not journeys (see [legacy format](#legacy-format)). |
| `description` | string | Free text, currently always `"A Journey with Otripy"`. |
| `format_version` | string | Version of this file format, `MAJOR.MINOR.PATCH`. |
| `app_version` | string | Version of the Otripy that saved the file. |
| `app_name` | string | Always `"Otripy"`. |
| `created_at` | string | When the journey was first saved, ISO 8601 with time zone. Kept on later saves. |
| `updated_at` | string | When the journey was last saved, ISO 8601 with time zone. |
| `encoding` | string | Always `"UTF-8"`. |
| `settings` | object | Reserved for journey settings, currently empty. |
| `locations` | array | The locations, in the order shown in the list: ungrouped locations first, then those of each group, in group order. |
| `notes` | object | Format 1.1.0. The trip's general notes, a [note](#notes) like those of locations. |
| `groups` | array | Format 1.1.0. The [groups](#groups), in the order shown in the list. |

## Locations

```json
{
    "id": "0b1e6a52-6f1c-4c55-9a7e-2f0d1c3a4b01",
    "lat": 48.8584,
    "lon": 2.2945,
    "note": {
        "markdown": "# Tour Eiffel\n\nChamp de Mars, 5 Avenue Anatole France, 75007 Paris, France\n\n![image](image_5f0c2e8e9a7b4c1d8e2f3a4b5c6d7e8f)\n\n",
        "images": {
            "image_5f0c2e8e9a7b4c1d8e2f3a4b5c6d7e8f": "iVBORw0KGgoAAAANSUhEUgAA..."
        }
    },
    "marker": "star",
    "color": "purple"
}
```

| Key | Type | Meaning |
|---|---|---|
| `id` | string | Unique identifier, a UUID. |
| `lat`, `lon` | number | Latitude and longitude, in degrees (WGS 84). |
| `note` | object | The location's note, see below. |
| `marker` | string or `null` | Name of the [Font Awesome](https://fontawesome.com/icons) icon shown in the marker, without the `fa-` prefix (e.g. `"star"`, `"bed"`). `null` shows a circle. |
| `group` | string | Optional, format 1.1.0. The `id` of the location's [group](#groups). |
| `color` | string or `null` | Marker color, a [Leaflet.awesome-markers](https://github.com/lennardv2/Leaflet.awesome-markers) color. Otripy's color picker offers `red`, `darkred`, `lightred`, `orange`, `green`, `darkgreen`, `lightgreen`, `blue`, `darkblue`, `lightblue`, `cadetblue`, `purple`, `pink`, `white`, `gray` and `black`. `null` means blue. |

### Groups

Format 1.1.0. A group is a titled section of the location list, such as a day of the trip.

```json
{
    "id": "9d2a1c3e-0000-4000-8000-000000000001",
    "note": {"markdown": "# Day 1: Left bank\n\nMostly on foot.\n\n", "images": {}},
    "collapsed": false
}
```

| Key | Type | Meaning |
|---|---|---|
| `id` | string | Unique identifier, a UUID. |
| `note` | object | The group's [note](#notes); its first line is the group's title. |
| `collapsed` | boolean | Whether the group's locations are hidden in the list. |

A location belongs to a group through its optional `group` key, the group's `id`; locations without it are not in any group.

### Notes

| Key | Type | Meaning |
|---|---|---|
| `markdown` | string | The note's text, in Markdown as written by Qt (`QTextDocument::toMarkdown`). Its first line, without heading marks, is the location's title. |
| `images` | object | The images the note shows, by name: base64-encoded PNG data. |
| `image_widths` | object | Optional. The display width, in pixels, of resized images, by name. Images not listed are shown at their original size. Written by Otripy 1.3 and later. |

An image appears in the text as `![image](name)`, where `name` is a key of `images`. Otripy saves exactly the images the text references. Names are `image_` followed by a random hexadecimal identifier; files saved by Otripy 1.2.3 and earlier use `dropped_image_1`, `dropped_image_2`, and so on.

## Reading rules

When opening a file, Otripy:

* refuses files without `"format": "otripy"`, unless they use the legacy format below;
* refuses files whose `format_version` is newer than the one it knows, asking to update Otripy; the `app_version` does not matter, since newer versions write older formats when they can;
* treats a location whose `group` matches no group as ungrouped;
* accepts missing location fields: `lat` and `lon` default to `0`, `note` to an empty note, `id` to a new UUID; empty strings for `marker` and `color` (written by Otripy 1.1) mean `null`;
* accepts a `note` that is a plain string instead of an object, as its Markdown text.

## Legacy format

Before format 1.0.0 (Otripy 1.1 and earlier), a file is a bare JSON array of locations, without the top-level object. Otripy still opens these files and saves them in the current format.

## Changing the format

Otripy refuses files whose `format_version` is newer than the one it knows, and writes the oldest format that can hold a journey (`BASE_FORMAT_VERSION` or `CURRENT_FORMAT_VERSION` in `src/otripy/journey.py`). So:

* A new **optional** field that older versions can ignore without losing meaning (like `image_widths`: they just show images at their original size) keeps the version.
* A field older versions cannot ignore, because they would lose or misread data when saving the file again (like groups and trip notes), bumps `CURRENT_FORMAT_VERSION`. Journeys that do not use it keep being written in the previous format.

In both cases, update this document and add a file showing the new shape to `tests/fixtures/`.

Otripy 1.3.1 and earlier also refuse any file saved by a newer Otripy version, whatever its format: they check `app_version` too. Only versions from 1.4.0 on follow the rules above.
