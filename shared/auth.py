"""
Inter-service authentication helpers
"""
from functools import wraps
from flask import request, jsonify
import os


def require_service_api_key(f):
    """
    Decorator to require SERVICE_API_KEY header for inter-service authentication

    Usage:
        @app.route('/api/protected')
        @require_service_api_key
        def protected_route():
            return jsonify({'message': 'Authorized'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Service-API-Key')
        expected_key = os.environ.get('SERVICE_API_KEY')

        if not expected_key:
            # If no API key configured, warn but allow (for development)
            print("⚠️ WARNING: SERVICE_API_KEY not configured!")
        elif api_key != expected_key:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid or missing API key'}), 401

        return f(*args, **kwargs)
    return decorated_function


def get_service_headers():
    """
    Get headers required for inter-service API calls

    Returns:
        dict: Headers with SERVICE_API_KEY
    """
    return {
        'X-Service-API-Key': os.environ.get('SERVICE_API_KEY', ''),
        'Content-Type': 'application/json'
    }
