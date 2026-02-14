"""
Database models for Sachet Missing Child Alert System
All SQLAlchemy models shared across microservices
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class MissingChild(db.Model):
    """Missing child case model"""
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    last_seen_location = db.Column(db.String(200), nullable=False)
    location_subcategory = db.Column(db.String(200))
    last_seen_lat = db.Column(db.Float)
    last_seen_lng = db.Column(db.Float)
    description = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(500))  # Increased length for URLs
    audio_filename = db.Column(db.String(500))  # Increased length for URLs
    emergency_contact = db.Column(db.String(100))  # Emergency contact phone/email
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='missing')
    sightings = db.relationship('Sighting', backref='missing_child', lazy=True)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'last_seen_location': self.last_seen_location,
            'location_subcategory': self.location_subcategory,
            'last_seen_lat': self.last_seen_lat,
            'last_seen_lng': self.last_seen_lng,
            'description': self.description,
            'photo_filename': self.photo_filename,
            'audio_filename': self.audio_filename,
            'emergency_contact': self.emergency_contact,
            'date_reported': self.date_reported.isoformat() if self.date_reported else None,
            'status': self.status
        }


class Sighting(db.Model):
    """Sighting report model"""
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('missing_child.report_id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    reporter_phone = db.Column(db.String(20))
    photo_filename = db.Column(db.String(500))  # Optional photo proof for sighting
    face_match_score = db.Column(db.Float, nullable=True)  # AI face comparison score (0-100)
    sighting_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'description': self.description,
            'reporter_phone': self.reporter_phone,
            'photo_filename': self.photo_filename,
            'face_match_score': self.face_match_score,
            'sighting_time': self.sighting_time.isoformat() if self.sighting_time else None
        }


class User(UserMixin, db.Model):
    """Admin user model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


class RiskZone(db.Model):
    """Risk zone model for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_km = db.Column(db.Float, default=1.0)
    risk_score = db.Column(db.Float, default=0.0)
    incident_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'zone_name': self.zone_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_km': self.radius_km,
            'risk_score': self.risk_score,
            'incident_count': self.incident_count,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active
        }


class Analytics(db.Model):
    """Analytics model for storing analysis results"""
    id = db.Column(db.Integer, primary_key=True)
    analysis_type = db.Column(db.String(50), nullable=False)
    analysis_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    insights = db.Column(db.Text)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'analysis_type': self.analysis_type,
            'analysis_data': self.analysis_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'insights': self.insights
        }
