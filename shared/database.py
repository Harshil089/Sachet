"""
Database initialization and helper functions
"""
from shared.models import db
from flask import Flask


def init_database(app: Flask):
    """
    Initialize database with the Flask app

    Args:
        app: Flask application instance
    """
    db.init_app(app)

    with app.app_context():
        try:
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            print("✅ Database connection successful")

            # Create tables if they don't exist
            db.create_all()
            print("✅ Database tables created/verified")

        except Exception as e:
            print(f"❌ Database connection error: {str(e)}")
            raise


def migrate_database(app: Flask):
    """
    Add missing columns to existing tables (migration helper)

    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)

            # Check if sighting table exists
            if 'sighting' not in inspector.get_table_names():
                print("⚠️ Sighting table doesn't exist yet, skipping migration")
                return

            columns = [col['name'] for col in inspector.get_columns('sighting')]

            if 'face_match_score' not in columns:
                print("⚙️ Adding face_match_score column to sighting table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE sighting ADD COLUMN face_match_score FLOAT'))
                    conn.commit()
                print("✅ face_match_score column added")
            else:
                print("✅ face_match_score column already exists")
        except Exception as e:
            print(f"⚠️ Migration error: {str(e)}")
            print("⚠️ If this persists, run migrate_db.py manually")
