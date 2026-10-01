# Usage

## Locations

* **Add a location** by clicking on the map. Otripy looks up the address of the clicked point: the place's name becomes the note's title, followed by its address.
* **Search** a place by typing its name in the search field and pressing *Enter*; click a result to add it, or press *Escape* to close the list.
* **Select a location** by clicking it in the list or its marker on the map: the map centers on it, and its note opens below the map.
* **Reorder** locations by dragging them in the list.
* **Delete** the selected location with *Delete Location*.

## Notes

The first line of a note is the location's title, shown in the list and on the map. The toolbar above the note sets headings (H1 to H3), bold, italic, underline and strikethrough. Add images by pasting them, or by dragging image files into the note.

The two last toolbar buttons change the selected location's marker: its icon, chosen among the [Font Awesome](https://fontawesome.com) icons, and its color.

## Files

| Action | Shortcut |
|---|---|
| New trip | Ctrl+N |
| Open a trip file | Ctrl+O |
| Open a trip from Nextcloud | Ctrl+Alt+O |
| Save | Ctrl+S |
| Save as a new file | Ctrl+Shift+S |
| Quit | Ctrl+Q |

Otripy asks before closing or opening another trip when there are unsaved changes; the window title starts with `*` while there are. Trips are JSON files, described in [the file format page](file-format.md).

## Nextcloud

In *Settings* → *Configure Otripy*, enter your Nextcloud server's URL, your user name and your password. If you use two-factor authentication, create an *app password* in Nextcloud's security settings and use it here. Otripy stores the password in your system's keyring (GNOME Keyring, KWallet, macOS Keychain or Windows Credential Manager).

*File* → *Open Nextcloud…* then lets you browse your Nextcloud files and open a trip. *Save* writes it back to Nextcloud. If the file was changed on the server since you opened it, Otripy asks for a new name instead of overwriting it.

Saving a new trip directly to Nextcloud is not available yet ([#28](https://github.com/kleag/otripy/issues/28)).

