"""
Gateway Service - Frontend and Orchestration Layer
Handles all user-facing routes and coordinates backend microservices
Port: 5000
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from io import BytesIO
import os
import sys
import uuid

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import Config
from shared.models import db, MissingChild, Sighting, User
from routes import api_proxy

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# Initialize database
db.init_app(app)

# In-memory tracking for failed admin login attempts
FAILED_ADMIN_LOGINS = {}

def _get_client_ip():
    """Get client IP address"""
    try:
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
    except Exception:
        pass
    return request.remote_addr or 'unknown'


def _is_locked_out(key: str) -> bool:
    """Check if IP is locked out"""
    record = FAILED_ADMIN_LOGINS.get(key)
    if not record:
        return False
    lock_until = record.get('lock_until')
    if lock_until and datetime.utcnow() < lock_until:
        return True
    if lock_until and datetime.utcnow() >= lock_until:
        FAILED_ADMIN_LOGINS.pop(key, None)
    return False


def _register_failed_attempt(key: str):
    """Register failed login attempt"""
    settings_max = app.config.get('ADMIN_MAX_FAILED_ATTEMPTS', 5)
    lock_minutes = app.config.get('ADMIN_LOCKOUT_MINUTES', 15)
    record = FAILED_ADMIN_LOGINS.get(key, {'count': 0, 'lock_until': None})
    record['count'] = record.get('count', 0) + 1
    if record['count'] >= int(settings_max):
        record['lock_until'] = datetime.utcnow() + timedelta(minutes=int(lock_minutes))
    FAILED_ADMIN_LOGINS[key] = record


def _reset_failed_attempts(key: str):
    """Reset failed attempts"""
    FAILED_ADMIN_LOGINS.pop(key, None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def handle_unauthorized():
    """Return 404 for unauthorized access to hide admin routes"""
    if request.path.startswith('/admin'):
        return render_template('errors/404.html'), 404
    return render_template('errors/404.html'), 404


@app.before_request
def enforce_admin_scope_logout_on_public_pages():
    """Auto-logout when accessing public pages"""
    try:
        path = request.path or ''
        if current_user.is_authenticated:
            if path == '/' or request.endpoint == 'index':
                logout_user()
                return None
    except Exception:
        return None


@app.before_request
def guard_admin_routes():
    """Protect admin routes"""
    try:
        path = request.path or ''
        if path.startswith('/admin'):
            if request.endpoint == 'admin_login':
                return None
            if not current_user.is_authenticated:
                return render_template('errors/404.html'), 404
    except Exception:
        return render_template('errors/404.html'), 404


# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Homepage - show recent missing cases"""
    success, cases, error = api_proxy.get_all_cases({'status': 'missing', 'limit': 5})

    if not success:
        flash(f'Error loading cases: {error}', 'danger')
        cases = []

    return render_template('index.html', recent_cases=cases)


@app.route('/report', methods=['GET', 'POST'])
def report_missing():
    """Report a missing child"""
    if request.method == 'POST':
        # Generate report ID
        report_id = f"MC{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

        # Get form data
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        location = request.form['location']
        location_subcategory = request.form.get('location_subcategory', '').strip() or None
        description = request.form['description']
        emergency_contact = request.form['emergency_contact']

        # Geocode location
        success, lat, lng, error = api_proxy.geocode_location(location)
        if not success:
            flash(f'Warning: Could not geocode location - {error}', 'warning')
            lat, lng = None, None

        photo_url = None
        audio_url = None

        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename:
                success, url, error = api_proxy.upload_photo(photo, photo.filename)
                if success:
                    photo_url = url
                    print(f"✅ Photo uploaded: {photo_url}")
                else:
                    flash(f'Photo upload failed: {error}', 'warning')

        # Handle audio upload
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and audio.filename:
                success, url, error = api_proxy.upload_audio(audio, audio.filename)
                if success:
                    audio_url = url
                    print(f"✅ Audio uploaded: {audio_url}")
                else:
                    flash(f'Audio upload failed: {error}', 'warning')

        # Create case via Case Service
        case_data = {
            'report_id': report_id,
            'name': name,
            'age': int(age),
            'gender': gender,
            'last_seen_location': location,
            'location_subcategory': location_subcategory,
            'last_seen_lat': lat,
            'last_seen_lng': lng,
            'description': description,
            'photo_filename': photo_url,
            'audio_filename': audio_url,
            'emergency_contact': emergency_contact
        }

        success, case, error = api_proxy.create_case(case_data)
        if not success:
            flash(f'Error creating case: {error}', 'danger')
            return redirect(url_for('report_missing'))

        # Send Telegram notification
        report_url = request.url_root + f"found/{report_id}"
        alert_message = f"🚨 MISSING CHILD ALERT 🚨\n\nName: {name}\nAge: {age} years\nGender: {gender}\nLast Seen: {location}\n\nReport sightings: {report_url}"

        api_proxy.send_telegram_notification(alert_message, photo_url=photo_url)

        flash(f'Missing child report created successfully! Report ID: {report_id}', 'success')
        return redirect(url_for('case_detail', report_id=report_id))

    return render_template('report.html')


@app.route('/found/<report_id>', methods=['GET', 'POST'])
def report_found(report_id):
    """Report a sighting of a missing child"""
    # Get case details
    success, case, error = api_proxy.get_case(report_id)
    if not success:
        flash(f'Case not found: {error}', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        location = request.form['location']
        description = request.form.get('description', '')
        reporter_phone = request.form.get('reporter_phone', '')

        # Geocode location
        success_geo, lat, lng, error_geo = api_proxy.geocode_location(location)
        if not success_geo:
            lat, lng = 0, 0

        # Handle sighting photo upload
        sighting_photo_url = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename:
                success_photo, url, error_photo = api_proxy.upload_photo(photo, photo.filename)
                if success_photo:
                    sighting_photo_url = url

        # Face comparison if both photos available
        face_match_score = None
        if sighting_photo_url and case.get('photo_filename'):
            success_face, match_score, error_face = api_proxy.compare_faces(
                case['photo_filename'],
                sighting_photo_url
            )
            if success_face:
                face_match_score = match_score
                print(f"🔍 Face match score: {match_score}%")

        # Create sighting via Case Service
        sighting_data = {
            'report_id': report_id,
            'location': location,
            'latitude': lat,
            'longitude': lng,
            'description': description,
            'reporter_phone': reporter_phone,
            'photo_filename': sighting_photo_url,
            'face_match_score': face_match_score
        }

        success_sighting, sighting, error_sighting = api_proxy.create_sighting(sighting_data)
        if not success_sighting:
            flash(f'Error creating sighting: {error_sighting}', 'danger')
            return redirect(url_for('report_found', report_id=report_id))

        # Send notification
        report_url = request.url_root + f"found/{report_id}"
        alert_message = (
            f"👁️ SIGHTING REPORTED 👁️\n\n"
            f"Child: {case['name']}\n"
            f"Spotted at: {location}\n"
            f"Time: {datetime.now().strftime('%H:%M')}\n"
            f"Report ID: {report_id}\n\n"
            f"Details: {report_url}"
        )

        api_proxy.send_telegram_notification(alert_message, photo_url=sighting_photo_url)

        flash('Thank you for reporting the sighting! Alert sent.', 'success')
        return redirect(url_for('report_found', report_id=report_id))

    return render_template('found.html', child=case)


@app.route('/case/<report_id>')
def case_detail(report_id):
    """Public case detail view"""
    success, case, error = api_proxy.get_case(report_id)
    if not success:
        flash(f'Case not found: {error}', 'danger')
        return redirect(url_for('index'))

    success_sightings, sightings, error_sightings = api_proxy.get_sightings(report_id)
    if not success_sightings:
        sightings = []

    return render_template('case_detail.html', child=case, sightings=sightings)


@app.route('/poster/<report_id>')
def download_poster(report_id):
    """Generate and download missing child poster"""
    success, case, error = api_proxy.get_case(report_id)
    if not success:
        flash(f'Case not found: {error}', 'danger')
        return redirect(url_for('index'))

    # Get poster PDF from Media Service
    success_poster, poster_pdf, error_poster = api_proxy.generate_poster({
        **case,
        'base_url': request.url_root.rstrip('/')
    })

    if not success_poster:
        flash('Error generating poster', 'danger')
        return redirect(url_for('case_detail', report_id=report_id))

    return send_file(
        BytesIO(poster_pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"missing_poster_{report_id}.pdf"
    )


# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login with token-based authentication"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        access_token = request.form.get('access_token', '').strip()

        client_ip = _get_client_ip()

        # Check lockout
        if _is_locked_out(client_ip):
            flash('Too many failed attempts. Please try again later.', 'danger')
            return render_template('admin/login.html'), 429

        # Verify admin credentials
        expected_username = app.config.get('ADMIN_USERNAME')
        expected_password = app.config.get('ADMIN_PASSWORD')
        expected_token = app.config.get('ADMIN_ACCESS_TOKEN')

        if (username == expected_username and
            password == expected_password and
            access_token == expected_token):

            # Get or create admin user
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, password_hash=generate_password_hash(password))
                db.session.add(user)
                db.session.commit()

            login_user(user)
            _reset_failed_attempts(client_ip)
            return redirect(url_for('admin_dashboard'))
        else:
            _register_failed_attempt(client_ip)
            flash('Invalid credentials', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    success, all_cases, error = api_proxy.get_all_cases()

    if not success:
        flash(f'Error loading cases: {error}', 'danger')
        all_cases = []

    # Calculate stats
    missing_cases = [c for c in all_cases if c.get('status') == 'missing']
    found_cases = [c for c in all_cases if c.get('status') == 'found']
    closed_cases = [c for c in all_cases if c.get('status') == 'closed']

    return render_template('admin/dashboard.html',
                         all_cases=all_cases,
                         total_cases=len(all_cases),
                         missing_count=len(missing_cases),
                         found_count=len(found_cases),
                         closed_count=len(closed_cases))


@app.route('/admin/case/<report_id>')
@login_required
def admin_case_detail(report_id):
    """Admin case detail view"""
    success, case, error = api_proxy.get_case(report_id)
    if not success:
        flash(f'Case not found: {error}', 'danger')
        return redirect(url_for('admin_dashboard'))

    success_sightings, sightings, error_sightings = api_proxy.get_sightings(report_id)
    if not success_sightings:
        sightings = []

    return render_template('admin/case_detail.html', child=case, sightings=sightings)


@app.route('/admin/update_status/<report_id>/<status>')
@login_required
def update_case_status(report_id, status):
    """Update case status"""
    if status not in ['missing', 'found', 'closed']:
        flash('Invalid status', 'danger')
        return redirect(url_for('admin_case_detail', report_id=report_id))

    success, updated_case, error = api_proxy.update_case(report_id, {'status': status})

    if success:
        flash(f'Case status updated to: {status}', 'success')

        # Send notification
        if status == 'found':
            alert_message = f"✅ CHILD FOUND! Report ID: {report_id}"
            api_proxy.send_telegram_notification(alert_message)
    else:
        flash(f'Error updating status: {error}', 'danger')

    return redirect(url_for('admin_case_detail', report_id=report_id))


@app.route('/admin/delete_case/<report_id>', methods=['POST'])
@login_required
def delete_case(report_id):
    """Delete a case"""
    success, error = api_proxy.delete_case(report_id)

    if success:
        flash('Case deleted successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash(f'Error deleting case: {error}', 'danger')
        return redirect(url_for('admin_case_detail', report_id=report_id))


@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout"""
    logout_user()
    return redirect(url_for('index'))


@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Admin analytics dashboard"""
    success_demo, demographics, error_demo = api_proxy.get_demographics()
    success_insights, insights, error_insights = api_proxy.get_insights()

    if not success_demo:
        demographics = {}
        flash(f'Error loading demographics: {error_demo}', 'warning')

    if not success_insights:
        insights = []
        flash(f'Error loading insights: {error_insights}', 'warning')

    return render_template('admin/analytics.html',
                         patterns=demographics,
                         insights=insights)


@app.route('/admin/risk-zones')
@login_required
def admin_risk_zones():
    """Admin risk zones view"""
    success, risk_zones, error = api_proxy.get_risk_zones()

    if not success:
        risk_zones = []
        flash(f'Error loading risk zones: {error}', 'warning')

    # Get all cases for map
    success_cases, all_cases, error_cases = api_proxy.get_all_cases()
    if not success_cases:
        all_cases = []

    return render_template('admin/risk_zones.html',
                         risk_zones=risk_zones,
                         all_cases=all_cases)


# ==================== API ROUTES ====================

@app.route('/api/analytics/update', methods=['POST'])
@login_required
def update_analytics():
    """Trigger analytics recalculation"""
    success, error = api_proxy.update_risk_zones()

    if success:
        return jsonify({'success': True, 'message': 'Analytics updated successfully'})
    else:
        return jsonify({'success': False, 'error': error}), 500


# ==================== HEALTH & ERROR HANDLERS ====================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'gateway',
        'version': '2.0.0'
    })


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
