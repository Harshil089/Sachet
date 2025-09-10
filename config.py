import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Only load .env in development
if not os.environ.get('RENDER'):
    load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration - Force SQLite for compatibility
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'missing_children.db')
    print(f"✅ Using SQLite database (compatible storage)")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite doesn't need connection pooling options
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Admin Credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Environment
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'
