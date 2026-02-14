"""
API Proxy Helper - Calls backend microservices
Handles inter-service communication with authentication
"""
import requests
import os
from typing import Dict, Any, Optional, List, Tuple


def get_service_headers() -> Dict[str, str]:
    """Get headers for inter-service authentication"""
    return {
        'X-Service-API-Key': os.environ.get('SERVICE_API_KEY', 'dev-service-key-change-in-production'),
        'Content-Type': 'application/json'
    }


# ==================== CASE SERVICE API ====================

def create_case(case_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Create a new missing child case

    Args:
        case_data: Dictionary with case details (name, age, gender, location, etc.)

    Returns:
        Tuple of (success, response_data, error_message)
    """
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.post(
            f'{case_service_url}/api/cases',
            json=case_data,
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code in [200, 201]:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Failed to create case')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


def get_all_cases(filters: Optional[Dict] = None) -> Tuple[bool, Optional[List], Optional[str]]:
    """Get all missing child cases with optional filters"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.get(
            f'{case_service_url}/api/cases',
            params=filters or {},
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json().get('cases', []), None
        else:
            return False, None, response.json().get('error', 'Failed to fetch cases')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


def get_case(report_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Get a specific case by report_id"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.get(
            f'{case_service_url}/api/cases/{report_id}',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Case not found')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


def update_case(report_id: str, update_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Update a case"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.put(
            f'{case_service_url}/api/cases/{report_id}',
            json=update_data,
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Failed to update case')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


def delete_case(report_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a case"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.delete(
            f'{case_service_url}/api/cases/{report_id}',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, None
        else:
            return False, response.json().get('error', 'Failed to delete case')

    except Exception as e:
        return False, f'Case service error: {str(e)}'


def create_sighting(sighting_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Create a new sighting report"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.post(
            f'{case_service_url}/api/sightings',
            json=sighting_data,
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code in [200, 201]:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Failed to create sighting')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


def get_sightings(report_id: str) -> Tuple[bool, Optional[List], Optional[str]]:
    """Get all sightings for a case"""
    try:
        case_service_url = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
        response = requests.get(
            f'{case_service_url}/api/sightings/{report_id}',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json().get('sightings', []), None
        else:
            return False, None, response.json().get('error', 'Failed to fetch sightings')

    except Exception as e:
        return False, None, f'Case service error: {str(e)}'


# ==================== MEDIA SERVICE API ====================

def upload_photo(photo_file, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upload and optimize a photo

    Args:
        photo_file: File object (from request.files)
        filename: Original filename

    Returns:
        Tuple of (success, photo_url, error_message)
    """
    try:
        media_service_url = os.environ.get('MEDIA_SERVICE_URL', 'http://media-service:5002')

        files = {'photo': (filename, photo_file, 'image/jpeg')}
        headers = {'X-Service-API-Key': os.environ.get('SERVICE_API_KEY', '')}

        response = requests.post(
            f'{media_service_url}/api/media/upload-photo',
            files=files,
            headers=headers,
            timeout=60
        )

        if response.status_code == 200:
            return True, response.json().get('url'), None
        else:
            return False, None, response.json().get('error', 'Failed to upload photo')

    except Exception as e:
        return False, None, f'Media service error: {str(e)}'


def upload_audio(audio_file, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Upload an audio file"""
    try:
        media_service_url = os.environ.get('MEDIA_SERVICE_URL', 'http://media-service:5002')

        files = {'audio': (filename, audio_file, 'audio/mpeg')}
        headers = {'X-Service-API-Key': os.environ.get('SERVICE_API_KEY', '')}

        response = requests.post(
            f'{media_service_url}/api/media/upload-audio',
            files=files,
            headers=headers,
            timeout=60
        )

        if response.status_code == 200:
            return True, response.json().get('url'), None
        else:
            return False, None, response.json().get('error', 'Failed to upload audio')

    except Exception as e:
        return False, None, f'Media service error: {str(e)}'


def generate_poster(case_data: Dict[str, Any]) -> Tuple[bool, Optional[bytes], Optional[str]]:
    """Generate a missing child poster PDF"""
    try:
        media_service_url = os.environ.get('MEDIA_SERVICE_URL', 'http://media-service:5002')

        response = requests.post(
            f'{media_service_url}/api/media/generate-poster',
            json=case_data,
            headers=get_service_headers(),
            timeout=60
        )

        if response.status_code == 200:
            return True, response.content, None
        else:
            return False, None, 'Failed to generate poster'

    except Exception as e:
        return False, None, f'Media service error: {str(e)}'


def compare_faces(photo1_url: str, photo2_url: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """Compare two face photos"""
    try:
        media_service_url = os.environ.get('MEDIA_SERVICE_URL', 'http://media-service:5002')

        response = requests.post(
            f'{media_service_url}/api/media/compare-faces',
            json={'photo1_url': photo1_url, 'photo2_url': photo2_url},
            headers=get_service_headers(),
            timeout=60
        )

        if response.status_code == 200:
            return True, response.json().get('match_score'), None
        else:
            return False, None, response.json().get('error', 'Face comparison failed')

    except Exception as e:
        return False, None, f'Media service error: {str(e)}'


# ==================== NOTIFICATION SERVICE API ====================

def send_telegram_notification(message: str, photo_url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Send Telegram notification"""
    try:
        notification_service_url = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:5003')

        response = requests.post(
            f'{notification_service_url}/api/notifications/telegram',
            json={'message': message, 'photo_url': photo_url},
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, None
        else:
            return False, response.json().get('message', 'Telegram notification failed')

    except Exception as e:
        return False, f'Notification service error: {str(e)}'


def send_discord_notification(message: str, photo_url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Send Discord notification"""
    try:
        notification_service_url = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:5003')

        response = requests.post(
            f'{notification_service_url}/api/notifications/discord',
            json={'message': message, 'photo_url': photo_url},
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, None
        else:
            return False, response.json().get('message', 'Discord notification failed')

    except Exception as e:
        return False, f'Notification service error: {str(e)}'


def broadcast_notification(message: str, photo_url: Optional[str] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Broadcast notification to all channels"""
    try:
        notification_service_url = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:5003')

        response = requests.post(
            f'{notification_service_url}/api/notifications/broadcast',
            json={'message': message, 'photo_url': photo_url},
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json().get('results'), None
        else:
            return False, None, response.json().get('error', 'Broadcast failed')

    except Exception as e:
        return False, None, f'Notification service error: {str(e)}'


# ==================== GEOCODING SERVICE API ====================

def geocode_location(location: str) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
    """
    Geocode a location name to coordinates

    Returns:
        Tuple of (success, latitude, longitude, error_message)
    """
    try:
        geocoding_service_url = os.environ.get('GEOCODING_SERVICE_URL', 'http://geocoding-service:5004')

        response = requests.get(
            f'{geocoding_service_url}/api/geocode',
            params={'location': location},
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return True, data.get('lat'), data.get('lng'), None
        else:
            return False, None, None, response.json().get('error', 'Geocoding failed')

    except Exception as e:
        return False, None, None, f'Geocoding service error: {str(e)}'


# ==================== ANALYTICS SERVICE API ====================

def get_risk_zones() -> Tuple[bool, Optional[List], Optional[str]]:
    """Get all risk zones"""
    try:
        analytics_service_url = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5005')

        response = requests.get(
            f'{analytics_service_url}/api/analytics/risk-zones',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json().get('risk_zones', []), None
        else:
            return False, None, response.json().get('error', 'Failed to fetch risk zones')

    except Exception as e:
        return False, None, f'Analytics service error: {str(e)}'


def update_risk_zones() -> Tuple[bool, Optional[str]]:
    """Trigger risk zone recalculation"""
    try:
        analytics_service_url = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5005')

        response = requests.post(
            f'{analytics_service_url}/api/analytics/risk-zones/update',
            headers=get_service_headers(),
            timeout=120  # Longer timeout for heavy computation
        )

        if response.status_code == 200:
            return True, None
        else:
            return False, response.json().get('error', 'Failed to update risk zones')

    except Exception as e:
        return False, f'Analytics service error: {str(e)}'


def get_demographics() -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Get demographic patterns"""
    try:
        analytics_service_url = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5005')

        response = requests.get(
            f'{analytics_service_url}/api/analytics/demographics',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Failed to fetch demographics')

    except Exception as e:
        return False, None, f'Analytics service error: {str(e)}'


def get_insights() -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Get predictive insights"""
    try:
        analytics_service_url = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5005')

        response = requests.get(
            f'{analytics_service_url}/api/analytics/insights',
            headers=get_service_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return True, response.json(), None
        else:
            return False, None, response.json().get('error', 'Failed to fetch insights')

    except Exception as e:
        return False, None, f'Analytics service error: {str(e)}'
