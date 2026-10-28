import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-smart-library-academic-2026')
    
    # Database config: Support SQLite locally and PostgreSQL for persistent cloud hosts
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "library.db")}')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'covers')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB max upload
    
    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application defaults
    LIBRARY_NAME = "Apex Smart Library System"
    DEFAULT_LOAN_DAYS = 14
    DEFAULT_FINE_PER_DAY = 1.00
    MAX_BOOKS_PER_MEMBER = 4
    CURRENCY_SYMBOL = "$"

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration with in-memory database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'test_covers')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
