"""
Case Service - Handles CRUD operations for cases and sightings
Port: 5001
"""
import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
from sqlalchemy import desc

# Import shared components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.config import Config
from shared.models import db, MissingChild, Sighting


app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)


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


# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.select(MissingChild).limit(1))
        return jsonify({
            'status': 'healthy',
            'service': 'case-service',
            'port': 5001,
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'case-service',
            'error': str(e)
        }), 503


# ==================== CASE ENDPOINTS ====================

@app.route('/api/cases', methods=['POST'])
@require_api_key
def create_case():
    """
    Create a new missing child case

    Expected JSON body:
    {
        "name": "Child Name",
        "age": 7,
        "gender": "Male",
        "location": "Location Name",
        "lat": 18.5167,
        "lng": 73.9282,
        "photo_filename": "https://...",
        "audio_filename": "https://...",  (optional)
        "description": "Description",
        "contact_info": "Contact details",
        "last_seen": "2024-01-15T10:30:00Z"  (optional)
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'age', 'gender', 'location', 'photo_filename', 'description', 'contact_info']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'success': False
            }), 400

        # Parse last_seen datetime if provided
        last_seen = None
        if 'last_seen' in data and data['last_seen']:
            try:
                last_seen = datetime.fromisoformat(data['last_seen'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'error': 'Invalid last_seen datetime format. Use ISO 8601 format.',
                    'success': False
                }), 400

        # Create new case
        new_case = MissingChild(
            name=data['name'],
            age=int(data['age']),
            gender=data['gender'],
            location=data['location'],
            lat=data.get('lat'),
            lng=data.get('lng'),
            photo_filename=data['photo_filename'],
            audio_filename=data.get('audio_filename'),
            description=data['description'],
            contact_info=data['contact_info'],
            last_seen=last_seen or datetime.utcnow(),
            status='missing'
        )

        db.session.add(new_case)
        db.session.commit()

        return jsonify({
            'success': True,
            'report_id': new_case.report_id,
            'message': 'Case created successfully',
            'case': {
                'report_id': new_case.report_id,
                'name': new_case.name,
                'age': new_case.age,
                'gender': new_case.gender,
                'location': new_case.location,
                'status': new_case.status,
                'created_at': new_case.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to create case: {str(e)}',
            'success': False
        }), 500


@app.route('/api/cases', methods=['GET'])
@require_api_key
def get_all_cases():
    """
    Get all cases with optional filters

    Query parameters:
    - status: Filter by status (missing, found, closed)
    - limit: Limit number of results (default: all)
    - order_by: Sort field (created_at, last_seen) - default: created_at
    - order: Sort direction (asc, desc) - default: desc
    """
    try:
        # Get filter parameters
        status_filter = request.args.get('status')
        limit = request.args.get('limit', type=int)
        order_by = request.args.get('order_by', 'created_at')
        order_dir = request.args.get('order', 'desc')

        # Build query
        query = db.select(MissingChild)

        # Apply status filter
        if status_filter:
            query = query.where(MissingChild.status == status_filter)

        # Apply ordering
        order_column = getattr(MissingChild, order_by, MissingChild.created_at)
        if order_dir == 'desc':
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Apply limit
        if limit:
            query = query.limit(limit)

        # Execute query
        cases = db.session.execute(query).scalars().all()

        # Format response
        cases_list = [{
            'report_id': case.report_id,
            'name': case.name,
            'age': case.age,
            'gender': case.gender,
            'location': case.location,
            'lat': case.lat,
            'lng': case.lng,
            'photo_filename': case.photo_filename,
            'audio_filename': case.audio_filename,
            'description': case.description,
            'contact_info': case.contact_info,
            'last_seen': case.last_seen.isoformat(),
            'status': case.status,
            'created_at': case.created_at.isoformat()
        } for case in cases]

        return jsonify({
            'success': True,
            'cases': cases_list,
            'count': len(cases_list)
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to fetch cases: {str(e)}',
            'success': False
        }), 500


@app.route('/api/cases/<report_id>', methods=['GET'])
@require_api_key
def get_case(report_id):
    """Get a specific case by report_id"""
    try:
        case = db.session.execute(
            db.select(MissingChild).where(MissingChild.report_id == report_id)
        ).scalar_one_or_none()

        if not case:
            return jsonify({
                'error': 'Case not found',
                'success': False
            }), 404

        return jsonify({
            'success': True,
            'report_id': case.report_id,
            'name': case.name,
            'age': case.age,
            'gender': case.gender,
            'location': case.location,
            'lat': case.lat,
            'lng': case.lng,
            'photo_filename': case.photo_filename,
            'audio_filename': case.audio_filename,
            'description': case.description,
            'contact_info': case.contact_info,
            'last_seen': case.last_seen.isoformat(),
            'status': case.status,
            'created_at': case.created_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to fetch case: {str(e)}',
            'success': False
        }), 500


@app.route('/api/cases/<report_id>', methods=['PUT'])
@require_api_key
def update_case(report_id):
    """
    Update a case

    Expected JSON body (all fields optional):
    {
        "name": "Updated Name",
        "age": 8,
        "description": "Updated description",
        "status": "found",
        ...
    }
    """
    try:
        case = db.session.execute(
            db.select(MissingChild).where(MissingChild.report_id == report_id)
        ).scalar_one_or_none()

        if not case:
            return jsonify({
                'error': 'Case not found',
                'success': False
            }), 404

        data = request.get_json()

        # Update allowed fields
        allowed_fields = [
            'name', 'age', 'gender', 'location', 'lat', 'lng',
            'photo_filename', 'audio_filename', 'description',
            'contact_info', 'status'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(case, field, data[field])

        # Update last_seen if provided
        if 'last_seen' in data and data['last_seen']:
            try:
                case.last_seen = datetime.fromisoformat(data['last_seen'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'error': 'Invalid last_seen datetime format',
                    'success': False
                }), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Case updated successfully',
            'report_id': case.report_id,
            'status': case.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to update case: {str(e)}',
            'success': False
        }), 500


@app.route('/api/cases/<report_id>', methods=['DELETE'])
@require_api_key
def delete_case(report_id):
    """Delete a case and all associated sightings"""
    try:
        case = db.session.execute(
            db.select(MissingChild).where(MissingChild.report_id == report_id)
        ).scalar_one_or_none()

        if not case:
            return jsonify({
                'error': 'Case not found',
                'success': False
            }), 404

        # Delete associated sightings first (due to foreign key constraint)
        db.session.execute(
            db.delete(Sighting).where(Sighting.report_id == report_id)
        )

        # Delete the case
        db.session.delete(case)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Case deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to delete case: {str(e)}',
            'success': False
        }), 500


@app.route('/api/cases/bulk-delete', methods=['POST'])
@require_api_key
def bulk_delete_cases():
    """
    Bulk delete multiple cases

    Expected JSON body:
    {
        "report_ids": ["MC202602140A1B2C3D", "MC202602140E5F6G7H"]
    }
    """
    try:
        data = request.get_json()
        report_ids = data.get('report_ids', [])

        if not report_ids:
            return jsonify({
                'error': 'No report_ids provided',
                'success': False
            }), 400

        # Delete sightings first
        db.session.execute(
            db.delete(Sighting).where(Sighting.report_id.in_(report_ids))
        )

        # Delete cases
        result = db.session.execute(
            db.delete(MissingChild).where(MissingChild.report_id.in_(report_ids))
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Deleted {result.rowcount} cases',
            'deleted_count': result.rowcount
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to bulk delete: {str(e)}',
            'success': False
        }), 500


# ==================== SIGHTING ENDPOINTS ====================

@app.route('/api/sightings', methods=['POST'])
@require_api_key
def create_sighting():
    """
    Create a new sighting report

    Expected JSON body:
    {
        "report_id": "MC202602140A1B2C3D",
        "location": "Sighting Location",
        "lat": 18.5167,
        "lng": 73.9282,
        "sighting_photo": "https://...",
        "description": "Sighting description",
        "contact_info": "Reporter contact",
        "match_score": 0.92  (optional, from face comparison)
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['report_id', 'location', 'sighting_photo', 'description', 'contact_info']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'success': False
            }), 400

        # Verify case exists
        case = db.session.execute(
            db.select(MissingChild).where(MissingChild.report_id == data['report_id'])
        ).scalar_one_or_none()

        if not case:
            return jsonify({
                'error': 'Case not found',
                'success': False
            }), 404

        # Create sighting
        new_sighting = Sighting(
            report_id=data['report_id'],
            location=data['location'],
            lat=data.get('lat'),
            lng=data.get('lng'),
            sighting_photo=data['sighting_photo'],
            description=data['description'],
            contact_info=data['contact_info'],
            match_score=data.get('match_score')
        )

        db.session.add(new_sighting)
        db.session.commit()

        return jsonify({
            'success': True,
            'sighting_id': new_sighting.id,
            'message': 'Sighting created successfully',
            'sighting': {
                'id': new_sighting.id,
                'report_id': new_sighting.report_id,
                'location': new_sighting.location,
                'match_score': new_sighting.match_score,
                'created_at': new_sighting.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to create sighting: {str(e)}',
            'success': False
        }), 500


@app.route('/api/sightings/<report_id>', methods=['GET'])
@require_api_key
def get_sightings(report_id):
    """Get all sightings for a specific case"""
    try:
        # Verify case exists
        case = db.session.execute(
            db.select(MissingChild).where(MissingChild.report_id == report_id)
        ).scalar_one_or_none()

        if not case:
            return jsonify({
                'error': 'Case not found',
                'success': False
            }), 404

        # Get sightings
        sightings = db.session.execute(
            db.select(Sighting)
            .where(Sighting.report_id == report_id)
            .order_by(desc(Sighting.created_at))
        ).scalars().all()

        sightings_list = [{
            'id': s.id,
            'report_id': s.report_id,
            'location': s.location,
            'lat': s.lat,
            'lng': s.lng,
            'sighting_photo': s.sighting_photo,
            'description': s.description,
            'contact_info': s.contact_info,
            'match_score': s.match_score,
            'created_at': s.created_at.isoformat()
        } for s in sightings]

        return jsonify({
            'success': True,
            'sightings': sightings_list,
            'count': len(sightings_list)
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to fetch sightings: {str(e)}',
            'success': False
        }), 500


# ==================== STATS ENDPOINT ====================

@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get case statistics"""
    try:
        total_cases = db.session.execute(
            db.select(db.func.count(MissingChild.id))
        ).scalar()

        missing_count = db.session.execute(
            db.select(db.func.count(MissingChild.id))
            .where(MissingChild.status == 'missing')
        ).scalar()

        found_count = db.session.execute(
            db.select(db.func.count(MissingChild.id))
            .where(MissingChild.status == 'found')
        ).scalar()

        closed_count = db.session.execute(
            db.select(db.func.count(MissingChild.id))
            .where(MissingChild.status == 'closed')
        ).scalar()

        return jsonify({
            'success': True,
            'stats': {
                'total': total_cases,
                'missing': missing_count,
                'found': found_count,
                'closed': closed_count
            }
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to fetch stats: {str(e)}',
            'success': False
        }), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'success': False}), 404


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({'error': 'Internal server error', 'success': False}), 500


# ==================== RUN SERVER ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
