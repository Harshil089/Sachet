"""
Geocoding Microservice
Handles location name to coordinate conversion using Google Maps API and Nominatim
Port: 5004
"""
from flask import Flask, jsonify, request
from functools import lru_cache
import os
import sys
import time
import threading

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.config import Config
from shared.auth import require_service_api_key

app = Flask(__name__)
app.config.from_object(Config)

# Rate limiting for Nominatim API
_last_geocode_request = 0
_geocode_lock = threading.Lock()


@lru_cache(maxsize=100)  # Cache 100 most recent locations
def geocode_location(location_name):
    """
    Get coordinates from location name using Google Maps (if configured) or Nominatim

    Args:
        location_name: Name of the location to geocode

    Returns:
        tuple: (latitude, longitude) or (None, None) if not found
    """
    if not location_name:
        return None, None

    # Try Google Maps first if API key is configured (more reliable)
    lat, lng = _geocode_with_google_maps(location_name)
    if lat and lng:
        return lat, lng

    # Fallback to Nominatim (free but rate-limited)
    return _geocode_with_nominatim(location_name)


def _geocode_with_google_maps(location_name):
    """Geocode using Google Maps API (optional, requires API key)"""
    import requests

    google_api_key = app.config.get('GOOGLE_MAPS_API_KEY') or os.environ.get('GOOGLE_MAPS_API_KEY')

    if not google_api_key:
        return None, None

    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location_name,
            'key': google_api_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'OK' and data.get('results'):
            location = data['results'][0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            print(f"✅ Geocoded '{location_name}' to: {lat}, {lng} (Google Maps)")
            return lat, lng
        else:
            print(f"⚠️ Google Maps: No results for '{location_name}' (status: {data.get('status')})")
            return None, None

    except Exception as e:
        print(f"❌ Google Maps geocoding error: {str(e)}")
        return None, None


def _geocode_with_nominatim(location_name):
    """Geocode using Nominatim API with rate limiting and retry logic"""
    import requests

    global _last_geocode_request

    try:
        # Rate limiting: ensure at least 1 second between requests
        with _geocode_lock:
            time_since_last = time.time() - _last_geocode_request
            if time_since_last < 1.0:
                time.sleep(1.0 - time_since_last)
            _last_geocode_request = time.time()

        location_encoded = location_name.strip().replace(' ', '+')
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={location_encoded}&limit=1"

        headers = {
            'User-Agent': 'Sachet-ChildSafety/2.0 (https://sachet.onrender.com)'
        }

        # Retry logic with exponential backoff
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                timeout = 15 if attempt == 0 else 20  # Increase timeout on retry
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                data = response.json()

                if data and len(data) > 0:
                    lat = float(data[0]['lat'])
                    lng = float(data[0]['lon'])
                    print(f"✅ Geocoded '{location_name}' to: {lat}, {lng} (Nominatim)")
                    return lat, lng
                else:
                    print(f"⚠️ Nominatim: No results for '{location_name}'")
                    return None, None

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                    print(f"⏱️ Nominatim timeout for '{location_name}', retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Nominatim timeout for '{location_name}' after {max_retries + 1} attempts")
                    return None, None

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"❌ Nominatim rate limit (403) for '{location_name}'")
                    # Wait longer on 403
                    if attempt < max_retries:
                        time.sleep(5)
                        continue
                print(f"❌ Nominatim HTTP error {e.response.status_code} for '{location_name}'")
                return None, None

    except Exception as e:
        print(f"❌ Nominatim error for '{location_name}': {str(e)}")
        return None, None


# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'geocoding-service',
        'version': '2.0.0'
    })


@app.route('/api/geocode', methods=['GET'])
@require_service_api_key
def geocode():
    """
    Geocode a location name to coordinates

    Query Parameters:
        location (str): Location name to geocode

    Returns:
        JSON: {"lat": float, "lng": float, "success": bool, "location": str}
    """
    location = request.args.get('location', '').strip()

    if not location:
        return jsonify({
            'error': 'Location parameter is required',
            'success': False
        }), 400

    lat, lng = geocode_location(location)

    if lat and lng:
        return jsonify({
            'lat': lat,
            'lng': lng,
            'success': True,
            'location': location
        })

    return jsonify({
        'error': 'Location not found',
        'success': False,
        'location': location
    }), 404


@app.route('/api/geocode/batch', methods=['POST'])
@require_service_api_key
def geocode_batch():
    """
    Geocode multiple locations in batch

    Request Body:
        {"locations": ["location1", "location2", ...]}

    Returns:
        JSON: {"results": [{"location": str, "lat": float, "lng": float, "success": bool}, ...]}
    """
    data = request.get_json()

    if not data or 'locations' not in data:
        return jsonify({
            'error': 'Request body must contain "locations" array',
            'success': False
        }), 400

    locations = data['locations']

    if not isinstance(locations, list):
        return jsonify({
            'error': '"locations" must be an array',
            'success': False
        }), 400

    results = []
    for location in locations:
        lat, lng = geocode_location(location)
        results.append({
            'location': location,
            'lat': lat,
            'lng': lng,
            'success': lat is not None and lng is not None
        })

    return jsonify({
        'results': results,
        'success': True
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
