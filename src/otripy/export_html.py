import json
import folium
import base64
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup

# 1. Load the Otripy JSON file
data_file = Path("/home/gael/Documents/Perso/Vacances/Vacances 2025/eire_20250616.json")  # replace with your file
with open(data_file, encoding="utf-8") as f:
    trip_data = json.load(f)

# 2. Create Folium map centered at first location
if trip_data["locations"]:
    lat0 = trip_data["locations"][0]["lat"]
    lon0 = trip_data["locations"][0]["lon"]
else:
    lat0, lon0 = 0, 0

m = folium.Map(location=[lat0, lon0], zoom_start=6)

# 3. Add locations as markers
for loc in trip_data["locations"]:
    lat, lon = loc["lat"], loc["lon"]
    color = loc.get("color", "blue")
    icon = loc.get("marker", "info-sign")

    # Build popup HTML
    note_html = ""
    if "note" in loc and "markdown" in loc["note"]:
        # Very basic markdown-to-HTML (no external lib)
        note_html = loc["note"]["markdown"].replace("\n", "<br>")

    # Add inline images from base64
    images = loc.get("note", {}).get("images", {})
    for img_id, img_b64 in images.items():
        img_tag = f'<br><img src="data:image/png;base64,{img_b64}" style="max-width:200px;">'
        note_html += img_tag

    popup = folium.Popup(note_html, max_width=300)

    folium.Marker(
        location=[lat, lon],
        popup=popup,
        icon=folium.Icon(color=color, icon=icon, prefix='fa')
    ).add_to(m)

# 4. Save HTML (will use CDN by default)
tmpfile = Path(tempfile.gettempdir()) / "map_tmp.html"
m.save(tmpfile)

# 5. Embed Leaflet JS/CSS inline for full offline use
html = tmpfile.read_text(encoding="utf-8")

# Download assets once manually and embed
# Here: quick hack using BeautifulSoup to inline <link> and <script> tags from CDN
soup = BeautifulSoup(html, "html.parser")

def inline_asset(tag, attr):
    url = tag[attr]
    import requests
    resp = requests.get(url)
    if resp.status_code == 200:
        if tag.name == "link":
            style_tag = soup.new_tag("style")
            style_tag.string = resp.text
            tag.replace_with(style_tag)
        elif tag.name == "script":
            script_tag = soup.new_tag("script")
            script_tag.string = resp.text
            tag.replace_with(script_tag)

for link in soup.find_all("link", href=True):
    inline_asset(link, "href")

for script in soup.find_all("script", src=True):
    inline_asset(script, "src")

# 6. Save final offline map.html
final_html = Path("map.html")
final_html.write_text(str(soup), encoding="utf-8")
print(f"Offline map saved to {final_html}")

