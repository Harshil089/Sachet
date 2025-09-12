from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from datetime import datetime, timedelta
import requests
from PIL import Image
import json
import math
from collections import defaultdict, Counter
import statistics
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url

from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Get the base directory
basedir = os.path.abspath(os.path.dirname(__file__))

# Ensure upload directories exist for local development
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)

# Create error templates directory
os.makedirs(os.path.join(basedir, 'templates', 'errors'), exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Initialize Cloudinary
def init_cloudinary():
    if app.config.get('CLOUDINARY_CLOUD_NAME'):
        cloudinary.config(
            cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=app.config['CLOUDINARY_API_KEY'],
            api_secret=app.config['CLOUDINARY_API_SECRET'],
            secure=True
        )
        print("✅ Cloudinary configured successfully")
        return True
    else:
        print("⚠️ Cloudinary not configured - using local storage")
        return False

CLOUDINARY_ENABLED = init_cloudinary()

# PREDEFINED DEMO PHONE NUMBERS (Replace with your verified Twilio numbers)
DEMO_PHONE_NUMBERS = [
    '+919960846194',    # Replace with your verified number 1
    # Replace with your verified number 2
    # Add more verified numbers as needed
]

# Initialize Twilio - only when needed
def get_twilio_client():
    try:
        from twilio.rest import Client
        return Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])
    except Exception as e:
        print(f"Error creating Twilio client: {str(e)}")
        return None

# Database Models
class MissingChild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    last_seen_location = db.Column(db.String(200), nullable=False)
    last_seen_lat = db.Column(db.Float)
    last_seen_lng = db.Column(db.Float)
    description = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(500))  # Increased length for URLs
    audio_filename = db.Column(db.String(500))  # Increased length for URLs
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='missing')
    sightings = db.relationship('Sighting', backref='missing_child', lazy=True)

class Sighting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('missing_child.report_id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    reporter_phone = db.Column(db.String(20))
    sighting_time = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class RiskZone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_km = db.Column(db.Float, default=1.0)
    risk_score = db.Column(db.Float, default=0.0)
    incident_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_type = db.Column(db.String(50), nullable=False)
    analysis_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    insights = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility Functions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def upload_to_cloudinary(file, folder, public_id):
    """Upload file to Cloudinary"""
    try:
        if not CLOUDINARY_ENABLED:
            return None
            
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type="auto",
            transformation=[
                {'width': 800, 'height': 800, 'crop': 'limit', 'quality': 'auto:good'}
            ] if folder == 'missing_children/photos' else None
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {str(e)}")
        return None

def save_file_locally(file, folder, filename):
    """Save file to local storage with proper organization"""
    try:
        # Create folder if it doesn't exist
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Generate unique filename
        file_path = os.path.join(folder_path, filename)
        
        # Save file
        file.save(file_path)
        
        # For images, optimize them
        if folder == 'photos' and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize if too large
                    img.thumbnail((800, 800), Image.Resampling.LANCZOS)

                    # Save as optimized JPEG and update filename to .jpg
                    base_name, _ext = os.path.splitext(filename)
                    optimized_filename = base_name + '.jpg'
                    optimized_path = os.path.join(folder_path, optimized_filename)
                    img.save(optimized_path, 'JPEG', quality=85, optimize=True)

                    # Remove original if different
                    if optimized_path != file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass

                    filename = optimized_filename
            except Exception as img_error:
                print(f"Image optimization error: {str(img_error)}")
        
        # Return just the filename for static file access
        return filename
    except Exception as e:
        print(f"Local file save error: {str(e)}")
        return None

def upload_audio_to_cloudinary(file, public_id):
    """Upload audio file to Cloudinary"""
    try:
        if not CLOUDINARY_ENABLED:
            return None
            
        result = cloudinary.uploader.upload(
            file,
            folder='missing_children/audio',
            public_id=public_id,
            overwrite=True,
            resource_type="video"  # Cloudinary uses 'video' for audio files
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary audio upload error: {str(e)}")
        return None

def get_location_coordinates(location_name):
    """Get coordinates from location name using Nominatim API"""
    if not location_name:
        return None, None
    
    try:
        location_encoded = location_name.strip().replace(' ', '+')
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={location_encoded}&limit=1"
        
        headers = {
            'User-Agent': 'ChildAbductionSystem/1.0 (contact@example.com)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            if not app.config['DEBUG']:
                print(f"Geocoded '{location_name}' to: {lat}, {lng}")
            return lat, lng
        else:
            if not app.config['DEBUG']:
                print(f"No results found for location: {location_name}")
            return None, None
            
    except Exception as e:
        if not app.config['DEBUG']:
            print(f"Geocoding error for '{location_name}': {str(e)}")
        return None, None

def send_sms_alert(message):
    """Send SMS alerts to predefined demo phone numbers"""
    if app.config['DEBUG']:
        print(f"\n=== SMS DEBUG MODE ===")
        print(f"Message: {message}")
        print(f"Would send to: {DEMO_PHONE_NUMBERS}")
        print("=== END SMS DEBUG ===\n")
        return len(DEMO_PHONE_NUMBERS)
    
    sent_count = 0
    failed_numbers = []
    
    if not app.config.get('TWILIO_ACCOUNT_SID') or not app.config.get('TWILIO_AUTH_TOKEN'):
        print("❌ Twilio credentials not configured")
        return 0
    
    if not app.config.get('TWILIO_PHONE_NUMBER'):
        print("❌ Twilio phone number not configured")
        return 0
    
    if not DEMO_PHONE_NUMBERS:
        print("❌ No demo phone numbers configured")
        return 0
    
    try:
        twilio_client = get_twilio_client()
        if not twilio_client:
            print("❌ Failed to create Twilio client")
            return 0
        
        for i, phone_number in enumerate(DEMO_PHONE_NUMBERS, 1):
            try:
                message_obj = twilio_client.messages.create(
                    body=message,
                    from_=app.config['TWILIO_PHONE_NUMBER'],
                    to=phone_number
                )
                sent_count += 1
                
            except Exception as e:
                print(f"❌ Failed to send SMS to {phone_number}: {str(e)}")
                failed_numbers.append(phone_number)
                
    except Exception as e:
        print(f"❌ Twilio client error: {str(e)}")
    
    return sent_count

# Analytics Functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def analyze_risk_zones():
    """Analyze historical data to identify high-risk zones"""
    cases = MissingChild.query.filter(
        MissingChild.last_seen_lat.isnot(None),
        MissingChild.last_seen_lng.isnot(None)
    ).all()
    
    if len(cases) < 2:
        return []
    
    zones = []
    processed = set()
    
    for i, case in enumerate(cases):
        if i in processed:
            continue
            
        zone_cases = [case]
        processed.add(i)
        
        for j, other_case in enumerate(cases[i+1:], i+1):
            if j in processed:
                continue
                
            distance = calculate_distance(
                case.last_seen_lat, case.last_seen_lng,
                other_case.last_seen_lat, other_case.last_seen_lng
            )
            
            if distance <= 2.0:
                zone_cases.append(other_case)
                processed.add(j)
        
        if len(zone_cases) >= 2:
            avg_lat = sum(c.last_seen_lat for c in zone_cases) / len(zone_cases)
            avg_lng = sum(c.last_seen_lng for c in zone_cases) / len(zone_cases)
            risk_score = calculate_risk_score(zone_cases)
            zone_name = f"Zone_{len(zones)+1}"
            
            zones.append({
                'name': zone_name,
                'lat': avg_lat,
                'lng': avg_lng,
                'cases': zone_cases,
                'risk_score': risk_score,
                'incident_count': len(zone_cases)
            })
    
    # Save to database
    RiskZone.query.delete()
    
    for zone in zones:
        risk_zone = RiskZone(
            zone_name=zone['name'],
            latitude=zone['lat'],
            longitude=zone['lng'],
            risk_score=zone['risk_score'],
            incident_count=zone['incident_count'],
            radius_km=2.0
        )
        db.session.add(risk_zone)
    
    db.session.commit()
    return zones

def calculate_risk_score(cases):
    """Calculate risk score for a zone based on multiple factors"""
    if not cases:
        return 0
    
    incident_score = min(len(cases) * 10, 50)
    
    now = datetime.utcnow()
    recency_scores = []
    
    for case in cases:
        days_ago = (now - case.date_reported).days
        if days_ago <= 30:
            recency_scores.append(20)
        elif days_ago <= 90:
            recency_scores.append(15)
        elif days_ago <= 365:
            recency_scores.append(10)
        else:
            recency_scores.append(5)
    
    recency_score = sum(recency_scores) / len(recency_scores) if recency_scores else 0
    
    age_scores = []
    for case in cases:
        if case.age <= 5:
            age_scores.append(15)
        elif case.age <= 10:
            age_scores.append(12)
        elif case.age <= 15:
            age_scores.append(8)
        else:
            age_scores.append(5)
    
    age_score = sum(age_scores) / len(age_scores) if age_scores else 0
    
    total_score = incident_score + recency_score + age_score
    return min(total_score, 100)

def analyze_demographic_patterns():
    """Analyze patterns in demographics"""
    cases = MissingChild.query.all()
    
    if not cases:
        return {}
    
    patterns = {
        'age_groups': Counter(),
        'gender_distribution': Counter(),
        'time_patterns': Counter(),
        'location_types': Counter(),
        'recovery_rates': {}
    }
    
    for case in cases:
        if case.age <= 5:
            patterns['age_groups']['0-5 years'] += 1
        elif case.age <= 10:
            patterns['age_groups']['6-10 years'] += 1
        elif case.age <= 15:
            patterns['age_groups']['11-15 years'] += 1
        else:
            patterns['age_groups']['16+ years'] += 1
        
        patterns['gender_distribution'][case.gender] += 1
        
        hour = case.date_reported.hour
        if 6 <= hour < 12:
            patterns['time_patterns']['Morning (6-12)'] += 1
        elif 12 <= hour < 18:
            patterns['time_patterns']['Afternoon (12-18)'] += 1
        elif 18 <= hour < 24:
            patterns['time_patterns']['Evening (18-24)'] += 1
        else:
            patterns['time_patterns']['Night (0-6)'] += 1
        
        location = case.last_seen_location.lower()
        if any(word in location for word in ['park', 'playground']):
            patterns['location_types']['Parks/Playgrounds'] += 1
        elif any(word in location for word in ['school', 'university']):
            patterns['location_types']['Educational'] += 1
        elif any(word in location for word in ['mall', 'store', 'shop']):
            patterns['location_types']['Commercial'] += 1
        elif any(word in location for word in ['home', 'house', 'residence']):
            patterns['location_types']['Residential'] += 1
        else:
            patterns['location_types']['Other'] += 1
    
    found_cases = [c for c in cases if c.status == 'found']
    total_cases = len(cases)
    
    if total_cases > 0:
        patterns['recovery_rates']['overall'] = (len(found_cases) / total_cases) * 100
        
        age_recovery = {}
        for age_group in patterns['age_groups']:
            age_cases = [c for c in cases if get_age_group(c.age) == age_group]
            age_found = [c for c in age_cases if c.status == 'found']
            if age_cases:
                age_recovery[age_group] = (len(age_found) / len(age_cases)) * 100
        
        patterns['recovery_rates']['by_age'] = age_recovery
    
    return patterns

def get_age_group(age):
    """Helper function to get age group"""
    if age <= 5:
        return '0-5 years'
    elif age <= 10:
        return '6-10 years'
    elif age <= 15:
        return '11-15 years'
    else:
        return '16+ years'

def generate_predictive_insights():
    """Generate human-readable insights from analytics"""
    zones = analyze_risk_zones()
    patterns = analyze_demographic_patterns()
    
    insights = []
    
    if zones:
        high_risk_zones = [z for z in zones if z['risk_score'] > 70]
        medium_risk_zones = [z for z in zones if 40 <= z['risk_score'] <= 70]
        
        if high_risk_zones:
            insights.append(f"🔴 HIGH RISK: {len(high_risk_zones)} zones identified with elevated risk (score >70)")
        if medium_risk_zones:
            insights.append(f"🟡 MEDIUM RISK: {len(medium_risk_zones)} zones require monitoring (score 40-70)")
    
    if patterns.get('age_groups'):
        most_vulnerable = max(patterns['age_groups'].items(), key=lambda x: x[1])
        insights.append(f"👶 DEMOGRAPHICS: {most_vulnerable[0]} age group has highest incident rate ({most_vulnerable[1]} cases)")
    
    if patterns.get('time_patterns'):
        peak_time = max(patterns['time_patterns'].items(), key=lambda x: x[1])
        insights.append(f"⏰ TIMING: Most incidents occur during {peak_time[0]} ({peak_time[1]} cases)")
    
    if patterns.get('location_types'):
        common_location = max(patterns['location_types'].items(), key=lambda x: x[1])
        insights.append(f"📍 LOCATIONS: {common_location[0]} areas account for most incidents ({common_location[1]} cases)")
    
    if patterns.get('recovery_rates', {}).get('overall'):
        recovery_rate = patterns['recovery_rates']['overall']
        if recovery_rate > 80:
            insights.append(f"✅ POSITIVE: High recovery rate of {recovery_rate:.1f}%")
        elif recovery_rate < 50:
            insights.append(f"⚠️ CONCERN: Low recovery rate of {recovery_rate:.1f}% - review response protocols")
    
    return insights

# Routes

@app.route('/admin/delete_case/<report_id>', methods=['POST'])
@login_required
def delete_case(report_id):
    """Delete a missing child case and all associated data"""
    try:
        missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
        
        # Store child name for flash message
        child_name = missing_child.name
        
        # Delete associated sightings first (foreign key constraint)
        sightings = Sighting.query.filter_by(report_id=report_id).all()
        for sighting in sightings:
            db.session.delete(sighting)
        
        # Delete files from Cloudinary if they exist
        if CLOUDINARY_ENABLED:
            try:
                # Delete photo from Cloudinary
                if missing_child.photo_filename and missing_child.photo_filename.startswith('http'):
                    photo_public_id = f"missing_children/photos/{report_id}_photo"
                    cloudinary.uploader.destroy(photo_public_id)
                    print(f"✅ Deleted photo from Cloudinary: {photo_public_id}")
                
                # Delete audio from Cloudinary
                if missing_child.audio_filename and missing_child.audio_filename.startswith('http'):
                    audio_public_id = f"missing_children/audio/{report_id}_audio"
                    cloudinary.uploader.destroy(audio_public_id, resource_type="video")
                    print(f"✅ Deleted audio from Cloudinary: {audio_public_id}")
                    
            except Exception as cloudinary_error:
                print(f"⚠️ Cloudinary deletion error: {str(cloudinary_error)}")
        else:
            # Delete local files if they exist
            try:
                if missing_child.photo_filename and not missing_child.photo_filename.startswith('http'):
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', missing_child.photo_filename.split('/')[-1])
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                        print(f"✅ Deleted local photo: {photo_path}")
                
                if missing_child.audio_filename and not missing_child.audio_filename.startswith('http'):
                    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', missing_child.audio_filename.split('/')[-1])
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                        print(f"✅ Deleted local audio: {audio_path}")
                        
            except Exception as file_error:
                print(f"⚠️ Local file deletion error: {str(file_error)}")
        
        # Delete the missing child record
        db.session.delete(missing_child)
        db.session.commit()
        
        # Send notification SMS about case deletion
        if not app.config['DEBUG']:
            deletion_message = f"CASE DELETED: {child_name} case (ID: {report_id}) has been permanently deleted by admin. Time: {datetime.now().strftime('%H:%M')}"
            sent_count = send_sms_alert(deletion_message)
            print(f"Deletion alert sent to {sent_count} numbers")
        
        flash(f'Case for {child_name} (ID: {report_id}) has been permanently deleted along with all associated data.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error deleting case: {str(e)}")
        flash(f'Error deleting case: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_cases():
    """Delete multiple cases at once"""
    try:
        case_ids = request.form.getlist('case_ids')
        
        if not case_ids:
            flash('No cases selected for deletion.', 'warning')
            return redirect(url_for('admin_dashboard'))
        
        deleted_count = 0
        deleted_names = []
        
        for report_id in case_ids:
            missing_child = MissingChild.query.filter_by(report_id=report_id).first()
            if missing_child:
                deleted_names.append(missing_child.name)
                
                # Delete associated sightings
                sightings = Sighting.query.filter_by(report_id=report_id).all()
                for sighting in sightings:
                    db.session.delete(sighting)
                
                # Delete files (same logic as single delete)
                if CLOUDINARY_ENABLED:
                    try:
                        if missing_child.photo_filename and missing_child.photo_filename.startswith('http'):
                            photo_public_id = f"missing_children/photos/{report_id}_photo"
                            cloudinary.uploader.destroy(photo_public_id)
                        
                        if missing_child.audio_filename and missing_child.audio_filename.startswith('http'):
                            audio_public_id = f"missing_children/audio/{report_id}_audio"
                            cloudinary.uploader.destroy(audio_public_id, resource_type="video")
                    except:
                        pass
                
                # Delete the record
                db.session.delete(missing_child)
                deleted_count += 1
        
        db.session.commit()
        
        # Send bulk deletion notification
        if deleted_count > 0 and not app.config['DEBUG']:
            bulk_message = f"BULK DELETION: {deleted_count} cases deleted by admin. Time: {datetime.now().strftime('%H:%M')}"
            send_sms_alert(bulk_message)
        
        flash(f'Successfully deleted {deleted_count} cases: {", ".join(deleted_names)}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during bulk deletion: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/')
def index():
    recent_cases = MissingChild.query.filter_by(status='missing').order_by(MissingChild.date_reported.desc()).limit(5).all()
    return render_template('index.html', recent_cases=recent_cases)

@app.route('/report', methods=['GET', 'POST'])
def report_missing():
    if request.method == 'POST':
        report_id = f"MC{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        location = request.form['location']
        description = request.form['description']
        
        lat, lng = get_location_coordinates(location)
        
        photo_url = None
        audio_url = None
        
        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                if CLOUDINARY_ENABLED:
                    # Upload to Cloudinary
                    photo_url = upload_to_cloudinary(
                        photo,
                        'missing_children/photos',
                        f"{report_id}_photo"
                    )
                    if photo_url:
                        print(f"✅ Photo uploaded to Cloudinary: {photo_url}")
                    else:
                        flash('Photo upload failed, but report was created successfully', 'warning')
                else:
                    # Use improved local storage
                    photo_filename = secure_filename(f"{report_id}_{photo.filename}")
                    photo_url = save_file_locally(photo, 'photos', photo_filename)
                    if photo_url:
                        print(f"✅ Photo saved locally: {photo_url}")
                    else:
                        flash('Photo upload failed, but report was created successfully', 'warning')
        
        # Handle audio upload
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and audio.filename and allowed_file(audio.filename, {'mp3', 'wav', 'ogg', 'm4a'}):
                if CLOUDINARY_ENABLED:
                    # Upload to Cloudinary
                    audio_url = upload_audio_to_cloudinary(
                        audio,
                        f"{report_id}_audio"
                    )
                    if audio_url:
                        print(f"✅ Audio uploaded to Cloudinary: {audio_url}")
                    else:
                        flash('Audio upload failed, but report was created successfully', 'warning')
                else:
                    # Use improved local storage
                    audio_filename = secure_filename(f"{report_id}_{audio.filename}")
                    audio_url = save_file_locally(audio, 'audio', audio_filename)
                    if audio_url:
                        print(f"✅ Audio saved locally: {audio_url}")
                    else:
                        flash('Audio upload failed, but report was created successfully', 'warning')
        
        # Create missing child record with URLs instead of filenames
        missing_child = MissingChild(
            report_id=report_id,
            name=name,
            age=age,
            gender=gender,
            last_seen_location=location,
            last_seen_lat=lat,
            last_seen_lng=lng,
            description=description,
            photo_filename=photo_url,
            audio_filename=audio_url
        )
        
        db.session.add(missing_child)
        db.session.commit()
        
        # Send SMS alert
        report_url = request.url_root + f"found/{report_id}"
        sms_message = f"MISSING: {name}, {age}yrs, {gender}, {location}. Report sightings: {report_url}"
        
        sent_count = send_sms_alert(sms_message)
        
        if sent_count > 0:
            flash(f'Missing child report created successfully! Report ID: {report_id}. Alert sent to {sent_count} subscribers.', 'success')
        else:
            flash(f'Missing child report created successfully! Report ID: {report_id}. However, SMS alerts could not be sent.', 'warning')
        
        return redirect(url_for('case_detail', report_id=report_id))
    
    return render_template('report.html')

@app.route('/found/<report_id>', methods=['GET', 'POST'])
def report_found(report_id):
    missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
    
    if request.method == 'POST':
        location = request.form['location']
        description = request.form.get('description', '')
        reporter_phone = request.form.get('reporter_phone', '')
        
        lat, lng = get_location_coordinates(location)
        
        sighting = Sighting(
            report_id=report_id,
            location=location,
            latitude=lat or 0,
            longitude=lng or 0,
            description=description,
            reporter_phone=reporter_phone
        )
        
        db.session.add(sighting)
        db.session.commit()
        
        sms_message = f"SIGHTING: {missing_child.name} spotted at {location}. Time: {datetime.now().strftime('%H:%M')}. ID: {report_id}"
        
        sent_count = send_sms_alert(sms_message)
        
        flash('Thank you for reporting the sighting! Alert sent to authorities and subscribers.', 'success')
        return redirect(url_for('report_found', report_id=report_id))
    
    return render_template('found.html', child=missing_child)

@app.route('/case/<report_id>')
def case_detail(report_id):
    missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
    sightings = Sighting.query.filter_by(report_id=report_id).order_by(Sighting.sighting_time.desc()).all()
    return render_template('case_detail.html', child=missing_child, sightings=sightings)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, password_hash=generate_password_hash(password))
                db.session.add(user)
                db.session.commit()
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    cases = MissingChild.query.order_by(MissingChild.date_reported.desc()).all()
    total_cases = len(cases)
    active_cases = len([c for c in cases if c.status == 'missing'])
    found_cases = len([c for c in cases if c.status == 'found'])
    
    return render_template('admin/dashboard.html', 
                         cases=cases, 
                         total_cases=total_cases,
                         active_cases=active_cases,
                         found_cases=found_cases)

@app.route('/admin/case/<report_id>')
@login_required
def admin_case_detail(report_id):
    missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
    sightings = Sighting.query.filter_by(report_id=report_id).order_by(Sighting.sighting_time.desc()).all()
    
    heat_data = []
    for sighting in sightings:
        if sighting.latitude and sighting.longitude:
            hours_ago = (datetime.utcnow() - sighting.sighting_time).total_seconds() / 3600
            intensity = max(0.1, 1.0 - (hours_ago / 168))
            heat_data.append([sighting.latitude, sighting.longitude, intensity])
    
    return render_template('admin/case_detail.html', 
                         child=missing_child, 
                         sightings=sightings,
                         heat_data=json.dumps(heat_data))

@app.route('/admin/update_status/<report_id>/<status>')
@login_required
def update_case_status(report_id, status):
    missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
    old_status = missing_child.status
    missing_child.status = status
    db.session.commit()
    
    if status == 'found' and old_status == 'missing':
        sms_message = f"FOUND: {missing_child.name} ({missing_child.age}yrs) found safe! ID: {report_id}. Thank you for helping!"
        sent_count = send_sms_alert(sms_message)
        flash(f'Case marked as FOUND! Alert sent to {sent_count} subscribers.', 'success')
    elif status == 'missing' and old_status == 'found':
        sms_message = f"URGENT: {missing_child.name} missing again! {missing_child.last_seen_location}. ID: {report_id}"
        sent_count = send_sms_alert(sms_message)
        flash(f'Case marked as MISSING again! Alert sent to {sent_count} subscribers.', 'warning')
    elif status == 'closed':
        sms_message = f"CLOSED: {missing_child.name} case closed. ID: {report_id}"
        sent_count = send_sms_alert(sms_message)
        flash(f'Case closed! Alert sent to {sent_count} subscribers.', 'info')
    else:
        flash(f'Case status updated to {status}', 'success')
    
    return redirect(url_for('admin_case_detail', report_id=report_id))

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    zones = analyze_risk_zones()
    patterns = analyze_demographic_patterns()
    insights = generate_predictive_insights()
    
    analytics_data = {
        'zones': len(zones),
        'patterns': patterns,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    analytics_record = Analytics(
        analysis_type='comprehensive',
        analysis_data=json.dumps(analytics_data),
        insights='; '.join(insights)
    )
    db.session.add(analytics_record)
    db.session.commit()
    
    return render_template('admin/analytics.html', 
                         zones=zones, 
                         patterns=patterns, 
                         insights=insights)

@app.route('/admin/risk-zones')
@login_required
def admin_risk_zones():
    risk_zones = RiskZone.query.filter_by(is_active=True).all()
    cases = MissingChild.query.filter(
        MissingChild.last_seen_lat.isnot(None),
        MissingChild.last_seen_lng.isnot(None)
    ).all()
    
    return render_template('admin/risk_zones.html', 
                         risk_zones=risk_zones, 
                         cases=cases)

@app.route('/api/geocode')
def geocode():
    location = request.args.get('location', '').strip()
    if not location:
        return jsonify({'error': 'Location parameter is required'}), 400
    
    lat, lng = get_location_coordinates(location)
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

@app.route('/api/analytics/update')
@login_required
def update_analytics():
    try:
        zones = analyze_risk_zones()
        patterns = analyze_demographic_patterns()
        insights = generate_predictive_insights()
        
        return jsonify({
            'success': True,
            'zones': len(zones),
            'insights': insights
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-sms')
def test_sms():
    """Test route to send a sample SMS - remove in production"""
    if not app.config['DEBUG'] and not current_user.is_authenticated:
        return "Unauthorized", 401
    
    test_message = f"TEST: Child Alert System working. Time: {datetime.now().strftime('%H:%M')}"
    sent_count = send_sms_alert(test_message)
    
    if sent_count > 0:
        return f"✅ Test SMS sent to {sent_count} numbers successfully!"
    else:
        return "❌ Test SMS failed. Check server logs for details."

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Health check endpoint for Render
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# ... (keep everything above as is until the create_tables function)

# Initialize database
def create_tables():
    """Create database tables if they don't exist"""
    try:
        with app.app_context():
            # Check if we can connect to database (using newer SQLAlchemy syntax)
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            print("✅ Database connection successful")
            
            # Create tables if they don't exist
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Create admin user if it doesn't exist
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                from werkzeug.security import generate_password_hash
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                admin_user = User(
                    username='admin',
                    password_hash=generate_password_hash(admin_password)
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Default admin user created")
            
            # Check if we have any existing data
            try:
                case_count = MissingChild.query.count()
                user_count = User.query.count()
                print(f"📊 Database ready with {case_count} cases, {user_count} users")
            except Exception as count_error:
                print(f"⚠️ Could not count existing data: {str(count_error)}")
            
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        # If connection fails, try to create tables anyway
        try:
            print("🔄 Attempting to create tables...")
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as create_error:
            print(f"❌ Failed to create tables: {str(create_error)}")
            # Don't raise error in production - let the app start anyway
            if not app.config.get('DEBUG', False):
                print("⚠️ Continuing without database verification (production mode)")
            else:
                raise create_error
            
# Add this route for debugging image URLs
@app.route('/debug/case/<report_id>')
def debug_case(report_id):
    if not app.config['DEBUG'] and not current_user.is_authenticated:
        return "Unauthorized", 401
    
    missing_child = MissingChild.query.filter_by(report_id=report_id).first_or_404()
    
    debug_info = {
        'report_id': missing_child.report_id,
        'name': missing_child.name,
        'photo_filename': missing_child.photo_filename,
        'photo_is_url': missing_child.photo_filename.startswith('http') if missing_child.photo_filename else False,
        'audio_filename': missing_child.audio_filename,
        'audio_is_url': missing_child.audio_filename.startswith('http') if missing_child.audio_filename else False,
        'cloudinary_enabled': CLOUDINARY_ENABLED
    }
    
    return jsonify(debug_info)

if __name__ == '__main__':
    create_tables()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
else:
    # This runs in production with Gunicorn
    create_tables()
