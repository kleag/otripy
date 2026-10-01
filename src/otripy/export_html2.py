# otripy/export_html.py
import folium
from pathlib import Path
import json

def export_html(trip_data: dict, output_file: Path):
    """
    Export Otripy trip_data to an HTML map using online resources (CDN).
    This file can be copied to a phone and opened in Firefox, but
    requires internet access for map tiles and icons.
    """
    if trip_data["locations"]:
        lat0 = trip_data["locations"][0]["lat"]
        lon0 = trip_data["locations"][0]["lon"]
    else:
        lat0, lon0 = 0, 0

    m = folium.Map(location=[lat0, lon0], zoom_start=6)

    for loc in trip_data["locations"]:
        lat, lon = loc["lat"], loc["lon"]
        color = loc.get("color", "blue")
        icon_name = loc.get("marker", "info-sign")

        # Popup HTML
        note_html = ""
        note = loc.get("note", {})
        if "markdown" in note:
            note_html += note["markdown"].replace("\n", "<br>")

        for img_id, img_b64 in note.get("images", {}).items():
            note_html += f'<br><img src="data:image/png;base64,{img_b64}" style="max-width:200px;">'

        popup = folium.Popup(note_html, max_width=300)

        # Font Awesome icon support
        folium.Marker(
            location=[lat, lon],
            popup=popup,
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(m)

    m.save(output_file)
    print(f"✅ HTML map saved to {output_file}")


if __name__ == "__main__":
    with open("/home/gael/Documents/Perso/Vacances/Vacances 2025/eire_20250616.json", encoding="utf-8") as f:
        trip_data = json.load(f)

    export_html(trip_data, Path("map.html"))
