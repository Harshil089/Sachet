#!/usr/bin/env python3
"""
Database initialization script for Missing Child Alert System
This script creates the database tables and initializes the database
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, MissingChild, Sighting, RiskZone, Analytics

def init_database():
    """Initialize the database with tables and default data"""
    with app.app_context():
        try:
            print("🔄 Initializing database...")
            
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                # Create default admin user
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                admin_user = User(
                    username='admin',
                    password_hash=generate_password_hash(admin_password)
                )
                db.session.add(admin_user)
                print("✅ Default admin user created")
            else:
                print("ℹ️  Admin user already exists")
            
            # Check if we have any existing data
            case_count = MissingChild.query.count()
            print(f"📊 Database initialized with {case_count} existing cases")
            
            # Commit all changes
            db.session.commit()
            print("✅ Database initialization completed successfully")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            db.session.rollback()
            raise e

def add_sample_data():
    """Add sample data for testing (optional)"""
    with app.app_context():
        try:
            # Check if we already have sample data
            if MissingChild.query.count() > 0:
                print("ℹ️  Sample data already exists, skipping...")
                return
            
            print("🔄 Adding sample data...")
            
            # Add a sample missing child case
            sample_case = MissingChild(
                report_id='SAMPLE001',
                name='Sample Child',
                age=8,
                gender='Male',
                last_seen_location='Sample Location',
                last_seen_lat=40.7128,
                last_seen_lng=-74.0060,
                description='This is a sample case for testing purposes',
                status='missing'
            )
            db.session.add(sample_case)
            
            # Add a sample sighting
            sample_sighting = Sighting(
                report_id='SAMPLE001',
                location='Sample Sighting Location',
                latitude=40.7589,
                longitude=-73.9851,
                description='Sample sighting report',
                reporter_phone='+1234567890'
            )
            db.session.add(sample_sighting)
            
            db.session.commit()
            print("✅ Sample data added successfully")
            
        except Exception as e:
            print(f"❌ Failed to add sample data: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("🚀 Missing Child Alert System - Database Initialization")
    print("=" * 60)
    
    # Initialize database
    init_database()
    
    # Add sample data if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--with-sample-data':
        add_sample_data()
    
    print("=" * 60)
    print("✅ Database setup completed!")
    print("\nNext steps:")
    print("1. Deploy your application")
    print("2. Access the admin panel at /admin/login")
    print("3. Use the credentials from your environment variables")
