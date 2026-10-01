# Usage

## Locations

* **Add a location** by clicking on the map. Otripy looks up the address of the clicked point: the place's name becomes the note's title, followed by its address. To avoid adding locations by mistake, check *Settings* → *Confirm New Locations*: Otripy then shows the address and asks before adding the location.
* **Search** a place by typing its name in the search field and pressing *Enter*; click a result to add it, or press *Escape* to close the list.
* **Select a location** by clicking it in the list or its marker on the map: the map centers on it, and its note opens below the map.
* **Reorder** locations by dragging them in the list. Locations with a custom marker show its icon there.
* **Delete** the selected location with *Delete Location*.

The map stays where you moved it while you edit, and shows all the locations when you open a trip. Drag the separators between the list, the map and the note to resize them; Otripy remembers their sizes.

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
| Save as a new file on Nextcloud | Ctrl+Alt+S |
| Quit | Ctrl+Q |

With *Settings* → *Auto Save* checked, Otripy saves the trip after each action on its locations: adding, deleting, reordering or changing a marker, and selecting another location, which saves the note you were editing. It does not save while you type, nor trips that were never saved, which need a file name first.

*File* → *Open Recent* lists the last trips you opened or saved, on your computer or on Nextcloud.

Otripy asks before closing or opening another trip when there are unsaved changes; the window title starts with `*` while there are. Trips are JSON files, described in [the file format page](file-format.md).

## Nextcloud

In *Settings* → *Configure Otripy*, enter your Nextcloud server's URL, your user name and your password. If you use two-factor authentication, create an *app password* in Nextcloud's security settings and use it here. Otripy stores the password in your system's keyring (GNOME Keyring, KWallet, macOS Keychain or Windows Credential Manager).

*File* → *Open Nextcloud…* then lets you browse your Nextcloud files and open a trip. *Save* writes it back to Nextcloud. If the file was changed or deleted on the server since you opened it, for instance by someone you share it with, Otripy asks whether to save your version under another name or to overwrite the file.

*File* → *Save As Nextcloud…* saves the trip to a new file on Nextcloud: browse to a folder, type a file name (`.json` is added if missing) and click *Save*. Clicking an existing file reuses its name; Otripy asks before replacing it.

