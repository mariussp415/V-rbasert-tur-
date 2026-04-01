from flask import Flask, render_template, request
import requests
from openai import OpenAI
import os
import math
from datetime import datetime, timezone
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# Set your Groq API key
_api_key = (os.getenv('GROQ_API_KEY') or '').strip()
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=_api_key)

def get_google_maps_api_key():
    return (os.getenv('GOOGLE_MAPS_API_KEY') or '').strip()

def get_oslo_timezone():
    try:
        return ZoneInfo('Europe/Oslo')
    except ZoneInfoNotFoundError:
        # Fallback to local system timezone if tzdata is unavailable.
        return datetime.now().astimezone().tzinfo or timezone.utc

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.route('/')
def index():
    return render_template('index.html', google_maps_api_key=get_google_maps_api_key())

@app.route('/recommend', methods=['POST'])
def recommend():
    location = request.form['location']
    # Get lat lon from location name
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
    geocode_response = requests.get(geocode_url, headers={'User-Agent': 'AI App/1.0'})
    geocode_data = geocode_response.json()
    if geocode_data:
        lat = float(geocode_data[0]['lat'])
        lon = float(geocode_data[0]['lon'])
    else:
        # Fallback to Oslo
        lat, lon = 59.9139, 10.7522

    # Fetch weather from yr.no
    weather_url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {'User-Agent': 'AI App/1.0'}
    weather_response = requests.get(weather_url, headers=headers)
    weather_data = weather_response.json()

    # Extract current weather and forecast (only future hours)
    now = datetime.now(timezone.utc)
    timeseries = [
        ts for ts in weather_data['properties']['timeseries']
        if datetime.fromisoformat(ts['time'].replace('Z', '+00:00')) >= now
    ]
    oslo_tz = get_oslo_timezone()
    today_oslo = now.astimezone(oslo_tz).date()

    # Keep only today's forecast in local time.
    day_timeseries = [
        ts for ts in timeseries
        if datetime.fromisoformat(ts['time'].replace('Z', '+00:00')).astimezone(oslo_tz).date() == today_oslo
    ]

    def format_forecast_rows(series):
        rows = []
        for i, ts in enumerate(series):
            ts_dt_utc = datetime.fromisoformat(ts['time'].replace('Z', '+00:00'))
            ts_dt_local = ts_dt_utc.astimezone(oslo_tz)
            time = ts['time']
            details = ts['data']['instant']['details']
            temp = details['air_temperature']
            wind = details['wind_speed']
            precip = ts['data'].get('next_1_hours', {}).get('details', {}).get('precipitation_amount', 0) if i < len(series)-1 else 0
            hour = f"{ts_dt_local.hour:02d}"
            emoji_temp = "🌡️" if temp > 10 else "❄️" if temp < 0 else "🌤️"
            emoji_wind = "💨" if wind > 5 else "🌬️"
            emoji_precip = "🌧️" if precip > 0 else "☀️"
            rows.append(f"- Kl {hour}: {temp}°C {emoji_temp}, {wind} m/s {emoji_wind}, {precip} mm {emoji_precip}")
        return rows

    rows_full_day = format_forecast_rows(day_timeseries)
    rows_06_12 = [
        row for ts, row in zip(day_timeseries, rows_full_day)
        if 6 <= datetime.fromisoformat(ts['time'].replace('Z', '+00:00')).astimezone(oslo_tz).hour <= 12
    ]

    # Fallback if 06-12 is outside remaining hours.
    if not rows_06_12:
        rows_06_12 = rows_full_day[:7]

    weather_06_12 = "Værvarsel kl. 06-12:\n" + "\n".join(rows_06_12) if rows_06_12 else "Ingen værdata tilgjengelig for kl. 06-12."
    weather_full_day = "Hele værmeldingen for dagen:\n" + "\n".join(rows_full_day) if rows_full_day else "Ingen værdata tilgjengelig for resten av dagen."

    # Use full day forecast for AI recommendation.
    weather_summary = weather_full_day

    # Tours based on ut.no data with locations
    all_tours = [
        {"name": "Besseggen", "description": "Klassisk ryggvandring i Jotunheimen med fantastisk utsikt over Gjende og Bessvatnet", "difficulty": "Hard", "lat": 61.45, "lon": 8.3, "image": "https://via.placeholder.com/400x300?text=Besseggen"},
        {"name": "Trolltunga", "description": "Ikonisk fjellformasjon som stikker ut over Ringedalsvatnet", "difficulty": "Medium", "lat": 60.12, "lon": 6.75, "image": "https://via.placeholder.com/400x300?text=Trolltunga"},
        {"name": "Preikestolen", "description": "Platå med 600 meter stup ned til Lysefjorden", "difficulty": "Medium", "lat": 58.98, "lon": 6.18, "image": "https://via.placeholder.com/400x300?text=Preikestolen"},
        {"name": "Galdhøpiggen", "description": "Norges høyeste fjell, 2469 moh", "difficulty": "Hard", "lat": 61.63, "lon": 8.31, "image": "https://via.placeholder.com/400x300?text=Galdhopiggen"},
        {"name": "Kjeragbolten", "description": "Stein fastklemt mellom to fjellvegger 1000 meter over Lysefjorden", "difficulty": "Medium", "lat": 59.03, "lon": 6.58, "image": "https://via.placeholder.com/400x300?text=Kjeragbolten"},
        {"name": "Aurlandsdalen", "description": "Vakker dalvandring med fossefall og fjellandskap", "difficulty": "Easy", "lat": 60.9, "lon": 7.2, "image": "https://via.placeholder.com/400x300?text=Aurlandsdalen"},
        {"name": "Aksla", "description": "Tur til toppen av Aksla med panoramautsikt over Ålesund", "difficulty": "Medium", "lat": 62.47, "lon": 6.15, "image": "https://via.placeholder.com/400x300?text=Aksla"},
        {"name": "Sukkertoppen", "description": "Vandring til Sukkertoppen med utsikt over byen", "difficulty": "Easy", "lat": 62.47, "lon": 6.15, "image": "https://via.placeholder.com/400x300?text=Sukkertoppen"},
        {"name": "Kletten", "description": "Første toppen i Sandsøya 7-toppstur, 130 moh", "difficulty": "Easy", "lat": 62.2413675, "lon": 5.4874972, "image": "https://via.placeholder.com/400x300?text=Kletten"},
        {"name": "Kulen", "description": "Andre toppen i Sandsøya 7-toppstur, 112 moh", "difficulty": "Easy", "lat": 62.24132, "lon": 5.48059, "image": "https://via.placeholder.com/400x300?text=Kulen"},
        {"name": "Rinden", "description": "Tredje og høyeste toppen på Sandsøya, 369 moh", "difficulty": "Hard", "lat": 62.25042, "lon": 5.42945, "image": "https://via.placeholder.com/400x300?text=Rinden"},
        {"name": "Signalen", "description": "Fjerde toppen i Sandsøya 7-toppstur, 359 moh", "difficulty": "Hard", "lat": 62.25543, "lon": 5.41925, "image": "https://via.placeholder.com/400x300?text=Signalen"},
        {"name": "Hellandsfjellet", "description": "Femte toppen i Sandsøya 7-toppstur, 122 moh", "difficulty": "Easy", "lat": 62.26304, "lon": 5.42319, "image": "https://via.placeholder.com/400x300?text=Hellandsfjellet"},
        {"name": "Hornet", "description": "Sjette toppen i Sandsøya 7-toppstur, 215 moh", "difficulty": "Medium", "lat": 62.26218, "lon": 5.47268, "image": "https://via.placeholder.com/400x300?text=Hornet"},
        {"name": "Grøntua", "description": "Syvende toppen i Sandsøya 7-toppstur, 250 moh", "difficulty": "Medium", "lat": 62.26228, "lon": 5.46614, "image": "https://via.placeholder.com/400x300?text=Gronntua"},
        {"name": "Sandsøya 7-toppstur", "description": "Komplett 7-toppstur på Sandsøya: Kletten (130m), Kulen (112m), Rinden (369m), Signalen (359m), Hellandsfjellet (122m), Hornet (215m), Grøntua (250m)", "difficulty": "Hard", "lat": 62.2413675, "lon": 5.4874972, "image": "https://via.placeholder.com/400x300?text=7-Toppstur"},
        {"name": "Frognerseteren", "description": "Tur til Frognerseteren i Nordmarka med muligheter for videre vandring. Tid: 1-2 timer, Vanskelighetsgrad: Lett", "difficulty": "Easy", "lat": 59.98, "lon": 10.67, "image": "https://via.placeholder.com/400x300?text=Frognerseteren"},
        {"name": "Kikutstua", "description": "Tur til Kikutstua i Nordmarka, populært utgangspunkt for turer. Tid: 2-3 timer, Vanskelighetsgrad: Middels", "difficulty": "Medium", "lat": 60.05, "lon": 10.67, "image": "https://via.placeholder.com/400x300?text=Kikutstua"},
        {"name": "Sognsvann", "description": "Vandring rundt Sognsvann i Nordmarka. Tid: 1-2 timer, Vanskelighetsgrad: Lett", "difficulty": "Easy", "lat": 59.97, "lon": 10.73, "image": "https://via.placeholder.com/400x300?text=Sognsvann"},
        {"name": "Østmarka - Bøler", "description": "Turer i Østmarka rundt Bølerområdet. Tid: 1-3 timer, Vanskelighetsgrad: Lett", "difficulty": "Easy", "lat": 59.88, "lon": 10.85, "image": "https://via.placeholder.com/400x300?text=Ostmarka-Boler"},
        {"name": "Nordmarka skogstur", "description": "Vakker skogstur i Nordmarka med stier og natur. Tid: 2-4 timer, Vanskelighetsgrad: Lett", "difficulty": "Easy", "lat": 59.98, "lon": 10.67, "image": "https://via.placeholder.com/400x300?text=Nordmarka-Skogstur"}
    ]
    # Filter tours within 10 km
    tours = [tour for tour in all_tours if haversine(lat, lon, tour['lat'], tour['lon']) < 10]
    if not tours:
        tours = all_tours  # Fallback to all if none nearby

    # Use AI to recommend
    tour_names = [t['name'] for t in tours]
    current_time = now.strftime('%H:%M UTC')
    prompt = f"The current time is {current_time}. Based on the forecast: {weather_summary}, recommend the best tour from these options: {tour_names}, and the best time to go on it. Only recommend times that are in the future (after {current_time}). Return in format: Tour: [name], Time: [time], Reason: [reason]"
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    ai_response = response.choices[0].message.content.strip()
    recommendation = ai_response

    tours_json = json.dumps([{"name": t["name"], "lat": t["lat"], "lon": t["lon"]} for t in tours])
    return render_template(
        'index.html',
        weather_06_12=weather_06_12,
        weather_full_day=weather_full_day,
        recommendation=recommendation,
        tours_json=tours_json,
        google_maps_api_key=get_google_maps_api_key(),
    )

if __name__ == '__main__':
    app.run(debug=True)