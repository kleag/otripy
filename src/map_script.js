function waitForLeaflet(callback) {
    if (typeof L !== "undefined") {
        callback();  // Run the main script when Leaflet is available
    } else {
        setTimeout(function() { waitForLeaflet(callback); }, 100);  // Retry every 100ms
    }
}

waitForLeaflet(function() {
    console.log("Leaflet.js is loaded!");

    document.addEventListener("DOMContentLoaded", function() {
        console.info(`DOMContentLoaded`)

        pywebchannel = new QWebChannel(qt.webChannelTransport, function(channel) {
            window.pyObj = channel.objects.pyObj || console.error("pyObj is not available.");
            window.markerHandler = channel.objects.markerHandler || console.error("markerHandler is not available.");
        });

        window.markerMap = {};

        let mapElement = document.querySelector("div[id^='map_']");
        console.info(`mapElement: ${mapElement}`)
        if (mapElement) {
            let mapId = mapElement.id;
            let map = window[mapId];

            map.on("click", function(event) {
                let lat = event.latlng.lat;
                let lon = event.latlng.lng;
                if (window.pyObj) {
                    window.pyObj.receiveData({"lat": lat, "lon": lon});
                }
            });

            // Inject markers dynamically (Python will replace `__LOCATIONS__`)
            let locations = __LOCATIONS__;
            console.info(`using locations: ${locations}`)
            locations.forEach(function(loc) {
                let marker = L.marker([loc.lat, loc.lon]).addTo(map)
                    .bindTooltip(loc.tooltip, { permanent: false })
                    .bindPopup(loc.popup);
                window.markerMap[loc.id] = marker;

                marker.on("click", function() {
                    if (window.markerHandler) {
                        window.markerHandler.on_marker_clicked(loc.id);
                    }
                });
            });
        }
    });
});
