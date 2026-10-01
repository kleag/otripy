import folium
from pathlib import Path
import html
import json

def export_html(trip_data: dict, output_file: Path):
    """
    Export Otripy trip_data to an HTML map using online resources (CDN)
    and add a collapsible marker list for mobile.
    """
    # Initial map center
    if trip_data.get("locations"):
        lat0 = trip_data["locations"][0]["lat"]
        lon0 = trip_data["locations"][0]["lon"]
    else:
        lat0, lon0 = 0, 0

    m = folium.Map(location=[lat0, lon0], zoom_start=6)

    # Build markers
    list_items = []
    for idx, loc in enumerate(trip_data["locations"]):
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

        folium.Marker(
            location=[lat, lon],
            popup=popup,
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(m)

        # First line of markdown as label
        first_line = note.get("markdown", "").strip().splitlines()[0] if "markdown" in note else f"Marker {idx+1}"
        list_items.append((idx, html.escape(first_line or f"Marker {idx+1}")))

    # Save normal Folium HTML
    m.save(output_file)

    # Collapsible list HTML/JS
    extra_html = f"""
<style>
#markerList {{
  position: absolute;
  top: 50px;
  left: 10px;
  background: rgba(255,255,255,0.95);
  padding: 5px;
  border-radius: 8px;
  box-shadow: 0 0 5px rgba(0,0,0,0.4);
  max-height: 50%;
  overflow-y: auto;
  display: none;
  z-index: 1000;
  font-size: 14px;
}}
#markerList button {{
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
}}
#markerListToggle {{
  position: absolute;
  top: 10px;
  left: 10px;
  background: #4285F4;
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  cursor: pointer;
  font-size: 20px;
  z-index: 1001;
}}
</style>
<button id="markerListToggle">☰</button>
<div id="markerList">
  {''.join(f'<button onclick="focusMarker({i})">{label}</button>' for i, label in list_items)}
</div>
<script>
var markerRefs = [];
function registerMarker(idx, marker) {{
    markerRefs[idx] = marker;
}}
function focusMarker(idx) {{
    var marker = markerRefs[idx];
    if (marker) {{
        map.setView(marker.getLatLng(), 12);
        marker.openPopup();
        document.getElementById('markerList').style.display = 'none';
    }}
}}
document.getElementById('markerListToggle').onclick = function() {{
    var list = document.getElementById('markerList');
    list.style.display = (list.style.display === 'none' ? 'block' : 'none');
}};
</script>
"""

    # Inject JS hooks into Folium output
    html_content = output_file.read_text(encoding="utf-8")
    lines = html_content.splitlines()
    lines_out = []
    marker_index = 0
    for line in lines:
        lines_out.append(line)
        if ".addTo(" in line and "marker_" in line:
            marker_name = line.split("=")[0].replace("var", "").strip()
            lines_out.append(f"registerMarker({marker_index}, {marker_name});")
            marker_index += 1

    html_content = "\n".join(lines_out)
    html_content = html_content.replace("</body>", extra_html + "\n</body>")

    output_file.write_text(html_content, encoding="utf-8")
    print(f"✅ HTML map with marker list saved to {output_file}")


if __name__ == "__main__":
    with open("/home/gael/Documents/Perso/Vacances/Vacances 2025/eire_20250616.json", encoding="utf-8") as f:
        trip_data = json.load(f)

    export_html(trip_data, Path("map.html"))
