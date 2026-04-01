// Toggle forecast
document.addEventListener('DOMContentLoaded', function () {
    const toggleButton = document.getElementById('toggle-forecast');
    const forecastContent = document.getElementById('forecast-content');
    if (toggleButton && forecastContent) {
        forecastContent.classList.remove('open');
        toggleButton.addEventListener('click', function () {
            const isOpen = forecastContent.classList.toggle('open');
            toggleButton.textContent = isOpen ? 'Vis mindre' : 'Vis mer';
        });
    }

    const revealItems = document.querySelectorAll('.reveal');
    revealItems.forEach(function (item, index) {
        window.setTimeout(function () {
            item.classList.add('is-visible');
        }, 90 * (index + 1));
    });
});

var googleMapState = {
    initialized: false,
    map: null,
    userPosition: null,
    userMarker: null,
    markers: [],
    directionsService: null,
    directionsRenderer: null
};

function buildGoogleMapsLink(origin, destination, travelmode) {
    return 'https://www.google.com/maps/dir/?api=1' +
        '&origin=' + origin.lat + ',' + origin.lng +
        '&destination=' + destination.lat + ',' + destination.lng +
        '&travelmode=' + travelmode;
}

function requestDirectionsWithFallback(service, requestBase, travelModes, onSuccess, onFailure) {
    var index = 0;

    function tryNext() {
        if (index >= travelModes.length) {
            onFailure('NO_ROUTE');
            return;
        }

        var mode = travelModes[index++];
        service.route(
            {
                origin: requestBase.origin,
                destination: requestBase.destination,
                travelMode: mode
            },
            function (result, status) {
                if (status === 'OK') {
                    onSuccess(result, mode);
                    return;
                }

                // Hard-stop statuses where retrying with another travel mode won't help.
                if (status === 'REQUEST_DENIED' || status === 'OVER_QUERY_LIMIT' || status === 'INVALID_REQUEST') {
                    onFailure(status);
                    return;
                }

                tryNext();
            }
        );
    }

    tryNext();
}

function initializeTourMap() {
    if (googleMapState.initialized) {
        return;
    }

    if (typeof window.TOURS_DATA === 'undefined' || window.TOURS_DATA.length === 0) {
        return;
    }

    var statusEl = document.getElementById('location-status');
    var tourSelect = document.getElementById('tour-select');
    var showRouteBtn = document.getElementById('show-route-btn');
    var gmapsLink = document.getElementById('gmaps-link');
    var mapElement = document.getElementById('map');
    var tours = window.TOURS_DATA;

    tours.forEach(function (tour, index) {
        var option = document.createElement('option');
        option.value = index;
        option.textContent = tour.name;
        tourSelect.appendChild(option);
    });

    tourSelect.addEventListener('change', function () {
        showRouteBtn.disabled = !googleMapState.userPosition || tourSelect.value === '';
        gmapsLink.style.display = 'none';
    });

    if (!window.GOOGLE_MAPS_ENABLED || typeof google === 'undefined' || !mapElement) {
        statusEl.textContent = 'Google Maps er ikke konfigurert ennå. Legg inn GOOGLE_MAPS_API_KEY i .env.';
        return;
    }

    googleMapState.map = new google.maps.Map(mapElement, {
        center: { lat: 62.5, lng: 8.5 },
        zoom: 6,
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: true
    });

    googleMapState.directionsService = new google.maps.DirectionsService();
    googleMapState.directionsRenderer = new google.maps.DirectionsRenderer({
        map: googleMapState.map,
        suppressMarkers: false
    });

    tours.forEach(function (tour) {
        var marker = new google.maps.Marker({
            position: { lat: tour.lat, lng: tour.lon },
            map: googleMapState.map,
            title: tour.name
        });
        var infoWindow = new google.maps.InfoWindow({ content: '<strong>' + tour.name + '</strong>' });
        marker.addListener('click', function () {
            infoWindow.open({ anchor: marker, map: googleMapState.map });
        });
        googleMapState.markers.push(marker);
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function (position) {
                googleMapState.userPosition = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };

                googleMapState.userMarker = new google.maps.Marker({
                    position: googleMapState.userPosition,
                    map: googleMapState.map,
                    title: 'Din posisjon',
                    icon: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                });

                googleMapState.map.setCenter(googleMapState.userPosition);
                googleMapState.map.setZoom(10);
                statusEl.textContent = 'Posisjon funnet.';
                if (tourSelect.value !== '') {
                    showRouteBtn.disabled = false;
                }
            },
            function () {
                statusEl.textContent = 'Kunne ikke hente posisjon. Tillat posisjon i nettleseren.';
            }
        );
    } else {
        statusEl.textContent = 'Nettleseren støtter ikke posisjonstjenester.';
    }

    showRouteBtn.addEventListener('click', function () {
        if (!googleMapState.userPosition || tourSelect.value === '') {
            return;
        }

        var tour = tours[parseInt(tourSelect.value, 10)];
        var destination = { lat: tour.lat, lng: tour.lon };

        requestDirectionsWithFallback(
            googleMapState.directionsService,
            {
                origin: googleMapState.userPosition,
                destination: destination
            },
            [
                google.maps.TravelMode.WALKING,
                google.maps.TravelMode.DRIVING,
                google.maps.TravelMode.BICYCLING
            ],
            function (result, mode) {
                googleMapState.directionsRenderer.setDirections(result);
                statusEl.textContent = 'Rute klar (' + mode.toLowerCase() + ').';
                gmapsLink.href = buildGoogleMapsLink(googleMapState.userPosition, destination, mode.toLowerCase());
                gmapsLink.style.display = 'inline-block';
            },
            function (status) {
                if (status === 'REQUEST_DENIED') {
                    statusEl.textContent = 'Google avviste ruteforesporselen (REQUEST_DENIED). Sjekk API-restriksjoner for nøkkelen.';
                } else if (status === 'OVER_QUERY_LIMIT') {
                    statusEl.textContent = 'Google-rutegrense nådd (OVER_QUERY_LIMIT). Prøv igjen litt senere.';
                } else {
                    statusEl.textContent = 'Fant ikke rute i Google Maps (' + status + '). Bruker ekstern Google Maps-lenke.';
                }

                gmapsLink.href = buildGoogleMapsLink(googleMapState.userPosition, destination, 'walking');
                gmapsLink.style.display = 'inline-block';
            }
        );
    });

    googleMapState.initialized = true;
}

window.initGoogleMap = function () {
    initializeTourMap();
};

window.addEventListener('load', function () {
    initializeTourMap();
});