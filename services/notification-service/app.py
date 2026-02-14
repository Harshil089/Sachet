"""
Notification Microservice
Handles all alerts: Telegram, Discord, SMS
Port: 5003
"""
from flask import Flask, jsonify, request
import os
import sys

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.config import Config
from shared.auth import require_service_api_key
from utils.messaging import send_telegram_alert, send_discord_alert, broadcast_alert

app = Flask(__name__)
app.config.from_object(Config)


# API Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'notification-service',
        'version': '2.0.0'
    })


@app.route('/api/notifications/telegram', methods=['POST'])
@require_service_api_key
def send_telegram():
    """
    Send Telegram notification

    Request Body:
        {
            "message": str (required),
            "photo_url": str (optional)
        }

    Returns:
        JSON: {"success": bool, "message": str}
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({
            'error': 'Request body must contain "message"',
            'success': False
        }), 400

    message = data['message']
    photo_url = data.get('photo_url')

    success = send_telegram_alert(message, photo_url)

    return jsonify({
        'success': success,
        'message': 'Telegram alert sent' if success else 'Telegram alert failed'
    })


@app.route('/api/notifications/discord', methods=['POST'])
@require_service_api_key
def send_discord():
    """
    Send Discord notification

    Request Body:
        {
            "message": str (required),
            "photo_url": str (optional)
        }

    Returns:
        JSON: {"success": bool, "message": str}
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({
            'error': 'Request body must contain "message"',
            'success': False
        }), 400

    message = data['message']
    photo_url = data.get('photo_url')

    success = send_discord_alert(message, photo_url)

    return jsonify({
        'success': success,
        'message': 'Discord alert sent' if success else 'Discord alert failed'
    })


@app.route('/api/notifications/sms', methods=['POST'])
@require_service_api_key
def send_sms():
    """
    Send SMS notification (currently mocked)

    Request Body:
        {
            "message": str (required),
            "phone_numbers": list (optional, defaults to demo numbers)
        }

    Returns:
        JSON: {"success": bool, "message": str}
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({
            'error': 'Request body must contain "message"',
            'success': False
        }), 400

    message = data['message']

    # SMS is currently in debug mode (mocked)
    if app.config['DEBUG']:
        print(f"\n=== SMS DEBUG MODE ===")
        print(f"Message: {message}")
        print("=== END SMS DEBUG ===\n")

    return jsonify({
        'success': True,
        'message': 'SMS sent (debug mode)'
    })


@app.route('/api/notifications/broadcast', methods=['POST'])
@require_service_api_key
def broadcast():
    """
    Broadcast notification to all channels

    Request Body:
        {
            "message": str (required),
            "photo_url": str (optional)
        }

    Returns:
        JSON: {"success": bool, "results": dict, "message": str}
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({
            'error': 'Request body must contain "message"',
            'success': False
        }), 400

    message = data['message']
    photo_url = data.get('photo_url')

    results = broadcast_alert(message, photo_url)

    successful = sum(1 for v in results.values() if v)
    total = len(results)

    return jsonify({
        'success': successful > 0,
        'results': results,
        'message': f'Broadcast sent to {successful}/{total} channels'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
