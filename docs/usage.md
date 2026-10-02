# Usage

## Locations

* **Add a location** by clicking on the map. Otripy looks up the address of the clicked point: the place's name becomes the note's title, followed by its address. To avoid adding locations by mistake, check *Settings* → *Confirm New Locations*: Otripy then shows the address and asks before adding the location.
* **Search** a place by typing its name in the search field and pressing *Enter*; click a result to add it, or press *Escape* to close the list.
* **Select a location** by clicking it in the list or its marker on the map: the map centers on it, and its note opens below the map.
* **Hover** a location in the list to highlight its marker on the map, or a marker to highlight its entry in the list. Their tooltips show the title and the beginning of the note.
* **Reorder** locations by dragging them in the list. Locations with a custom marker show its icon there.
* **Delete** the selected location with *Delete*.

The map stays where you moved it while you edit, and shows all the locations when you open a trip. Drag the separators between the list, the map and the note to resize them; Otripy remembers their sizes.

## Groups

Groups are titled sections of the location list, for instance the days of the trip or the cities you visit.

* **Create a group** with *New Group*: it appears at the end of the list, with its title selected in the note editor, ready to be typed over. Like a location, a group has a note: its first line is the group's title.
* **Add locations to a group** by dragging them under its title, or by adding them while the group, or one of its locations, is selected: new locations then join that group.
* **Reorder groups** by dragging their titles: their locations move with them. Locations outside of any group stay at the top of the list.
* **Collapse or expand a group** by double-clicking its title; its title shows how many locations it has.
* **Select a group** to see its locations on the map, and its note below the map.
* **Delete a group** with *Delete*, after confirmation: its locations are kept, outside of any group.

Routes go through the locations in the list's order, groups included.

## Trip notes

The first entry of the list, *Trip notes*, holds notes about the whole trip rather than one location: travel documents, budget, packing list… Select it to write them in the note editor, with the same formatting, images and links as other notes.

## Distances and routes

* *Tools* → *Distances…* shows the straight-line distance between two locations, the selected one and the next by default. Choose a mode (car, bicycle or foot) and click *Compute Route* for the route's length and duration.
* **Add a route between two places**: select the first place, in the list or on the map, then **Shift-click** the second one, in the list or on the map. Choose how you travel, by car, bicycle or foot, in the menu that appears. The route is drawn on the map, in blue for the car, green for the bicycle, and dashed orange on foot; hover it for its length and duration.
* Each part of the journey has its own route and mode: add one between each pair of places you travel between. Adding a route between two places that already have one replaces it.
* **Click a route** on the map to switch it to another mode, or to remove it. *Tools* → *Remove All Routes* removes them all; deleting a place removes its routes.
* The status bar shows how many routes the trip has, and their total length and duration.

Routes are saved with the trip, so they show again without an Internet connection. Trips with routes use file format 1.2.0, which Otripy 1.4 and earlier cannot open.

Routes are computed by the [FOSSGIS](https://routing.openstreetmap.de/about.html) routing servers behind openstreetmap.org, from OpenStreetMap data: they need an Internet connection. If a route looks wrong, you can [fix the map](https://www.openstreetmap.org/fixthemap). Public transport and electric car charging are not available.

## Notes

The first line of a note is the location's title, shown in the list and on the map. The toolbar above the note sets headings (H1 to H3), bold, italic, underline and strikethrough. Add images by pasting them, or by dragging image files into the note. Right-click an image to change its size: *Image Size* → *Small*, *Medium*, *Large* or *Original Size*. Links and web addresses (`https://…`, `www.…`) open in your browser with Ctrl+click; a plain click just places the cursor.

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
| Export for a map app on a phone (KMZ, GPX) | *File* → *Export for Phone…* |
| Quit | Ctrl+Q |

With *Settings* → *Auto Save* checked, Otripy saves the trip after each action on its locations: adding, deleting, reordering or changing a marker, and selecting another location, which saves the note you were editing. It does not save while you type, nor trips that were never saved, which need a file name first.

To take your trip with you, *File* → *Export for Phone…* saves it for map apps that work offline, such as Organic Maps: see [your trip on your phone](phone.md).

*File* → *Open Recent* lists the last trips you opened or saved, on your computer or on Nextcloud.

Otripy asks before closing or opening another trip when there are unsaved changes; the window title starts with `*` while there are. Trips are JSON files, described in [the file format page](file-format.md).

## Nextcloud

In *Settings* → *Configure Otripy*, enter your Nextcloud server's URL, your user name and your password. If you use two-factor authentication, create an *app password* in Nextcloud's security settings and use it here. Otripy stores the password in your system's keyring (GNOME Keyring, KWallet, macOS Keychain or Windows Credential Manager).

*File* → *Open Nextcloud…* then lets you browse your Nextcloud files and open a trip. *Save* writes it back to Nextcloud. If the file was changed or deleted on the server since you opened it, for instance by someone you share it with, Otripy asks whether to save your version under another name or to overwrite the file.

*File* → *Save As Nextcloud…* saves the trip to a new file on Nextcloud: browse to a folder, type a file name (`.json` is added if missing) and click *Save*. Clicking an existing file reuses its name; Otripy asks before replacing it.

