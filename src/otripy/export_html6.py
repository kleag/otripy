import folium
from pathlib import Path
import html
import json
import re

def export_html(trip_data: dict, output_file: Path):
    """
    Export trip_data to an HTML map with a collapsible marker list.
    Clicking list <-> marker is synced both ways.
    Markdown in popups is rendered with marked.js when the popup opens.
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
    for idx, loc in enumerate(trip_data.get("locations", [])):
        lat, lon = loc["lat"], loc["lon"]
        color = loc.get("color", "blue")
        icon_name = loc.get("marker", "info-sign")

        note_md = loc.get("note", {}).get("markdown", "")
        # Keep markdown as escaped text inside a div so JS can parse it safely client-side
        note_html = f'<div class="popup-markdown" data-idx="{idx}">{html.escape(note_md)}</div>'

        # Use folium.Html(script=True) so Folium will not wrap content in an iframe
        html_elem = folium.Html(note_html, script=True)
        popup = folium.Popup(html_elem, max_width=300)

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

    # Read generated HTML
    html_content = output_file.read_text(encoding="utf-8")

    # Extract actual map variable name (folium names it like map_12345)
    map_var_match = re.search(r"var (map_\w+) = L\.map", html_content)
    map_var_name = map_var_match.group(1) if map_var_match else "map"

    # Build extra HTML + JS (marked.js + marker list + registerMarker)
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

    // When marker clicked highlight the list
    marker.on('click', function() {{
        highlightListItem(idx);
    }});

    // When popup opens, render markdown inside the popup (uses marked.js)
    marker.on('popupopen', function(e) {{
        // Look up the popup-markdown element with the matching data-idx
        var sel = '.leaflet-popup-content .popup-markdown[data-idx=\"' + idx + '\"]';
        var el = document.querySelector(sel);
        if (!el) {{
            // fallback: find by data-idx anywhere in the document
            el = document.querySelector('.popup-markdown[data-idx=\"' + idx + '\"]');
        }}
        if (el) {{
            // convert escaped text (textContent) from Markdown to HTML
            try {{
                el.innerHTML = marked.parse(el.textContent || '');
            }} catch (ex) {{
                console.error('Marked parse error', ex);
            }}
        }}
    }});
}}
function highlightListItem(idx) {{
    document.querySelectorAll('#markerList button').forEach(b => b.classList.remove('active'));
    var btn = document.getElementById('list-item-' + idx);
    if (btn) {{
        btn.classList.add('active');
        // ensure visible if list is scrollable
        btn.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
    }}
}}
function focusMarker(idx) {{
    var marker = markerRefs[idx];
    if (marker) {{
        {map_var_name}.setView(marker.getLatLng(), 12);
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
// Render any popup-markdown nodes already present in the DOM (not inside newly opened popups)
document.addEventListener("DOMContentLoaded", function() {{
    document.querySelectorAll('.popup-markdown').forEach(function(div) {{
        // If it's not inside a leaflet popup content right now, render it
        if (!div.closest('.leaflet-popup-content')) {{
            try {{
                div.innerHTML = marked.parse(div.textContent || '');
            }} catch (ex) {{
                console.error('Marked parse error', ex);
            }}
        }}
    }});
}});
</script>
"""

    # Inject registerMarker calls *after* the marker statement finishes (.addTo(...);)
    lines_out = []
    marker_index = 0
    pending_marker_name = None

    for line in html_content.splitlines():
        lines_out.append(line)

        # Detect beginning of marker variable creation
        start_match = re.match(r"^\s*var (marker_[0-9a-f]+) = L\.marker", line)
        if start_match:
            pending_marker_name = start_match.group(1)
            continue

        # Wait until the line that contains .addTo( ... ) to insert the register call
        if pending_marker_name and ".addTo(" in line:
            lines_out.append(f"registerMarker({marker_index}, {pending_marker_name});")
            marker_index += 1
            pending_marker_name = None

    # Insert extra HTML/JS before </body>
    final_html = "\n".join(lines_out).replace("</body>", extra_html + "\n</body>")
    output_file.write_text(final_html, encoding="utf-8")
    print(f"✅ HTML map with synced marker list and markdown popups saved to {output_file}")


if __name__ == "__main__":
    with open("/home/gael/Documents/Perso/Vacances/Vacances 2025/eire_20250616.json", encoding="utf-8") as f:
        trip_data = json.load(f)

    export_html(trip_data, Path("map.html"))
