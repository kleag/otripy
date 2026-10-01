import folium
from pathlib import Path
import html
import json

def export_html(trip_data: dict, output_file: Path):
    """
    Export trip_data to an HTML map with a collapsible marker list.
    List is in JSON order, with labels from the first markdown line.
    Clicking list <-> marker is synced both ways.
    """
    # Determine initial map center
    if trip_data.get("locations"):
        lat0 = trip_data["locations"][0]["lat"]
        lon0 = trip_data["locations"][0]["lon"]
    else:
        lat0, lon0 = 0, 0

    m = folium.Map(location=[lat0, lon0], zoom_start=6)

    # Marker label list
    list_items = []
    for idx, loc in enumerate(trip_data["locations"]):
        lat, lon = loc["lat"], loc["lon"]
        color = loc.get("color", "blue")
        icon_name = loc.get("marker", "info-sign")

        note_md = loc.get("note", {}).get("markdown", "")
        note_html = f'<div class="popup-markdown" data-idx="{idx}">{html.escape(note_md)}</div>'

        popup = folium.Popup(note_html, max_width=300)
        folium.Marker(
            location=[lat, lon],
            popup=popup,
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(m)

        # First line of markdown (or fallback)
        first_line = note_md.strip().splitlines()[0] if note_md.strip() else f"Marker {idx+1}"
        list_items.append((idx, html.escape(first_line)))

    # Save initial HTML from Folium
    m.save(output_file)

    # Collapsible list HTML & JS
    extra_html = f"""
<!-- Load marked.js for Markdown rendering -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
#markerList {{
  position: absolute;
  top: 50px;
  right: 10px;
  background: rgba(255,255,255,0.95);
  padding: 5px;
  border-radius: 8px;
  box-shadow: 0 0 5px rgba(0,0,0,0.4);
  max-height: 50%;
  overflow-y: auto;
  display: none;
  z-index: 1000;
  font-size: 14px;
  min-width: 140px;
}}
#markerList button {{
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
#markerList button.active {{
  background: #4285F4;
  color: white;
}}
#markerListToggle {{
  position: absolute;
  top: 10px;
  right: 10px;
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
  {''.join(f'<button onclick="focusMarker({i})" id="list-item-{i}">{label}</button>' for i, label in list_items)}
</div>
<script>
var markerRefs = [];
function registerMarker(idx, marker) {{
    markerRefs[idx] = marker;
    marker.on('click', function() {{
        highlightListItem(idx);
    }});
}}
function highlightListItem(idx) {{
    document.querySelectorAll('#markerList button').forEach(b => b.classList.remove('active'));
    var btn = document.getElementById('list-item-' + idx);
    if (btn) btn.classList.add('active');
}}
function focusMarker(idx) {{
    var marker = markerRefs[idx];
    if (marker) {{
        map.setView(marker.getLatLng(), 12);
        marker.openPopup();
        highlightListItem(idx);
        document.getElementById('markerList').style.display = 'none';
    }}
}}
// Toggle list visibility
document.getElementById('markerListToggle').onclick = function() {{
    var list = document.getElementById('markerList');
    list.style.display = (list.style.display === 'none' ? 'block' : 'none');
}};
// Render markdown in popups after map load
document.addEventListener("DOMContentLoaded", function() {{
    document.querySelectorAll('.popup-markdown').forEach(function(div) {{
        div.innerHTML = marked.parse(div.textContent);
    }});
}});
</script>
"""

    # Inject registerMarker calls after marker creation
    html_content = output_file.read_text(encoding="utf-8")
    lines_out = []
    marker_index = 0
    for line in html_content.splitlines():
        lines_out.append(line)
        if ".addTo(" in line and "marker_" in line:
            marker_name = line.split("=")[0].replace("var", "").strip()
            lines_out.append(f"registerMarker({marker_index}, {marker_name});")
            marker_index += 1

    # Insert extra HTML before </body>
    html_content = "\n".join(lines_out).replace("</body>", extra_html + "\n</body>")
    output_file.write_text(html_content, encoding="utf-8")
    print(f"✅ HTML map with synced marker list saved to {output_file}")


if __name__ == "__main__":
    with open("/home/gael/Documents/Perso/Vacances/Vacances 2025/eire_20250616.json", encoding="utf-8") as f:
        trip_data = json.load(f)

    export_html(trip_data, Path("map.html"))
