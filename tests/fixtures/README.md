# Test fixtures

Journey files covering each on-disk shape Otripy must keep loading. Locations are public landmarks.

| File | Shape |
|---|---|
| `legacy-list.json` | Pre-1.0.0 format: a bare list of locations, no metadata, no marker/color; the last note is a plain string instead of a `{"markdown": …}` dict |
| `journey-1.0.0.json` | Current format (format 1.0.0, app 1.2.2): markers and colors set or `null`, a title with quotes and a backslash |
| `journey-with-images.json` | Format 1.0.0 saved by app 1.1.4: empty strings for unset marker/color, notes with embedded base64 PNG images referenced as `![image](dropped_image_N)`, one with a display width in `image_widths` |
| `journey-1.1.0.json` | Format 1.1.0 (app 1.4.0): trip notes, two groups (the second collapsed), locations with a `group`, one ungrouped |
