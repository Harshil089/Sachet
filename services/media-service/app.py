"""
Media Service - Handles photo/audio uploads, poster generation, face comparison
Port: 5002
"""
import os
import io
import cloudinary
import cloudinary.uploader
from functools import wraps
from flask import Flask, request, jsonify, send_file
from PIL import Image
from werkzeug.utils import secure_filename

# Import utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.config import Config

# Import poster generator
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from poster_generator import generate_poster_pdf


app = Flask(__name__)
app.config.from_object(Config)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# Allowed file extensions
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac'}


# ==================== AUTHENTICATION MIDDLEWARE ====================

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Service-API-Key')
        expected_key = os.environ.get('SERVICE_API_KEY', 'dev-service-key-change-in-production')

        if not api_key or api_key != expected_key:
            return jsonify({'error': 'Unauthorized', 'success': False}), 401

        return f(*args, **kwargs)
    return decorated_function


# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def optimize_image(image_file):
    """
    Optimize image for web display
    - Resize to max 800x800 (maintain aspect ratio)
    - Convert to JPEG
    - Compress quality to 85%
    """
    try:
        # Open image
        img = Image.open(image_file)

        # Convert RGBA to RGB if necessary (for PNG transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if too large (maintain aspect ratio)
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        return buffer

    except Exception as e:
        raise ValueError(f'Image optimization failed: {str(e)}')


# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check Cloudinary configuration
    cloudinary_configured = all([
        os.environ.get('CLOUDINARY_CLOUD_NAME'),
        os.environ.get('CLOUDINARY_API_KEY'),
        os.environ.get('CLOUDINARY_API_SECRET')
    ])

    return jsonify({
        'status': 'healthy',
        'service': 'media-service',
        'port': 5002,
        'cloudinary': 'configured' if cloudinary_configured else 'not_configured'
    }), 200


# ==================== PHOTO UPLOAD ====================

@app.route('/api/media/upload-photo', methods=['POST'])
@require_api_key
def upload_photo():
    """
    Upload and optimize a photo

    Form data:
    - photo: File upload (required)

    Returns:
    {
        "success": true,
        "url": "https://res.cloudinary.com/...",
        "public_id": "sachet/..."
    }
    """
    try:
        # Check if file was uploaded
        if 'photo' not in request.files:
            return jsonify({
                'error': 'No photo file provided',
                'success': False
            }), 400

        file = request.files['photo']

        # Check if file is empty
        if file.filename == '':
            return jsonify({
                'error': 'Empty filename',
                'success': False
            }), 400

        # Validate file extension
        if not allowed_file(file.filename, ALLOWED_PHOTO_EXTENSIONS):
            return jsonify({
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_PHOTO_EXTENSIONS)}',
                'success': False
            }), 400

        # Optimize image
        try:
            optimized_image = optimize_image(file)
        except ValueError as e:
            return jsonify({
                'error': str(e),
                'success': False
            }), 400

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            optimized_image,
            folder='sachet/missing_children',
            resource_type='image',
            allowed_formats=['jpg', 'jpeg', 'png'],
            transformation=[
                {'width': 800, 'height': 800, 'crop': 'limit'},
                {'quality': 'auto:good'}
            ]
        )

        return jsonify({
            'success': True,
            'url': upload_result['secure_url'],
            'public_id': upload_result['public_id']
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Photo upload failed: {str(e)}',
            'success': False
        }), 500


# ==================== AUDIO UPLOAD ====================

@app.route('/api/media/upload-audio', methods=['POST'])
@require_api_key
def upload_audio():
    """
    Upload an audio file

    Form data:
    - audio: File upload (required)

    Returns:
    {
        "success": true,
        "url": "https://res.cloudinary.com/...",
        "public_id": "sachet/..."
    }
    """
    try:
        # Check if file was uploaded
        if 'audio' not in request.files:
            return jsonify({
                'error': 'No audio file provided',
                'success': False
            }), 400

        file = request.files['audio']

        # Check if file is empty
        if file.filename == '':
            return jsonify({
                'error': 'Empty filename',
                'success': False
            }), 400

        # Validate file extension
        if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
            return jsonify({
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_AUDIO_EXTENSIONS)}',
                'success': False
            }), 400

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder='sachet/audio',
            resource_type='video',  # Cloudinary uses 'video' for audio files
            allowed_formats=list(ALLOWED_AUDIO_EXTENSIONS)
        )

        return jsonify({
            'success': True,
            'url': upload_result['secure_url'],
            'public_id': upload_result['public_id']
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Audio upload failed: {str(e)}',
            'success': False
        }), 500


# ==================== POSTER GENERATION ====================

@app.route('/api/media/generate-poster', methods=['POST'])
@require_api_key
def generate_poster():
    """
    Generate a missing child poster PDF

    Expected JSON body:
    {
        "report_id": "MC202602140A1B2C3D",
        "name": "Child Name",
        "age": 7,
        "gender": "Male",
        "location": "Last seen location",
        "last_seen": "2024-01-15",
        "description": "Description",
        "contact_info": "Contact details",
        "photo_url": "https://..."
    }

    Returns: PDF file (application/pdf)
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['report_id', 'name', 'age', 'gender', 'location', 'contact_info', 'photo_url']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'success': False
            }), 400

        # Generate poster PDF
        pdf_buffer = generate_poster_pdf(
            report_id=data['report_id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            location=data['location'],
            last_seen=data.get('last_seen', ''),
            description=data.get('description', ''),
            contact_info=data['contact_info'],
            photo_url=data['photo_url']
        )

        # Return PDF file
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'missing_child_poster_{data["report_id"]}.pdf'
        )

    except Exception as e:
        return jsonify({
            'error': f'Poster generation failed: {str(e)}',
            'success': False
        }), 500


# ==================== FACE COMPARISON ====================

@app.route('/api/media/compare-faces', methods=['POST'])
@require_api_key
def compare_faces():
    """
    Compare two face photos (DISABLED - face_recognition not available)

    Expected JSON body:
    {
        "photo1_url": "https://...",
        "photo2_url": "https://..."
    }

    Returns:
    {
        "success": true,
        "match_score": 0.0,
        "message": "Face comparison disabled"
    }
    """
    # Face recognition is disabled to avoid Render deployment issues
    # Always return match_score=0.0
    return jsonify({
        'success': True,
        'match_score': 0.0,
        'message': 'Face comparison feature is currently disabled'
    }), 200


# ==================== FILE DELETION ====================

@app.route('/api/media/delete-file', methods=['DELETE'])
@require_api_key
def delete_file():
    """
    Delete a file from Cloudinary

    Expected JSON body:
    {
        "public_id": "sachet/missing_children/abc123",
        "resource_type": "image"  (optional, default: image)
    }
    """
    try:
        data = request.get_json()

        if 'public_id' not in data:
            return jsonify({
                'error': 'Missing public_id',
                'success': False
            }), 400

        public_id = data['public_id']
        resource_type = data.get('resource_type', 'image')

        # Delete from Cloudinary
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type
        )

        if result.get('result') == 'ok':
            return jsonify({
                'success': True,
                'message': 'File deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'File not found or already deleted'
            }), 404

    except Exception as e:
        return jsonify({
            'error': f'File deletion failed: {str(e)}',
            'success': False
        }), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'success': False}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error', 'success': False}), 500


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'error': 'File too large. Maximum file size is 10MB.', 'success': False}), 413


# ==================== RUN SERVER ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
