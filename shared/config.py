import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Only load .env in development
if not os.environ.get('RENDER'):
    # Load .env from parent directory (project root)
    env_path = os.path.join(os.path.dirname(basedir), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database Configuration - Use persistent storage
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Use provided database URL (for production)
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print(f"✅ Using persistent database (production)")
    else:
        # Fallback to SQLite for local development
        db_path = os.path.join(os.path.dirname(basedir), 'missing_children.db')
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
        print(f"⚠️  Using SQLite database (development only - data will reset on deployment)")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    } if DATABASE_URL else {}

    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

    # Google Maps API (optional - for better geocoding)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

    # Telegram Bot (optional - for free alerts)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

    # Discord Webhook (optional - for free alerts)
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(basedir), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Admin Credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    # Admin security
    ADMIN_ACCESS_TOKEN = os.environ.get('ADMIN_ACCESS_TOKEN')  # optional secret to reach login
    ADMIN_MAX_FAILED_ATTEMPTS = int(os.environ.get('ADMIN_MAX_FAILED_ATTEMPTS', '5'))
    ADMIN_LOCKOUT_MINUTES = int(os.environ.get('ADMIN_LOCKOUT_MINUTES', '15'))

    # Microservices Configuration
    SERVICE_API_KEY = os.environ.get('SERVICE_API_KEY', 'dev-service-key-change-in-production')

    # Service URLs (for inter-service communication)
    CASE_SERVICE_URL = os.environ.get('CASE_SERVICE_URL', 'http://case-service:5001')
    MEDIA_SERVICE_URL = os.environ.get('MEDIA_SERVICE_URL', 'http://media-service:5002')
    NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:5003')
    GEOCODING_SERVICE_URL = os.environ.get('GEOCODING_SERVICE_URL', 'http://geocoding-service:5004')
    ANALYTICS_SERVICE_URL = os.environ.get('ANALYTICS_SERVICE_URL', 'http://analytics-service:5005')

    # Environment
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'
