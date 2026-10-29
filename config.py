import os
import tempfile
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

def normalize_database_url(url: str | None) -> str | None:
    """
    Normalize database connection URL for SQLAlchemy 2.0+ compatibility.
    Cloud providers (e.g., Neon, Supabase, Render, Railway) frequently
    provide postgres:// URLs; SQLAlchemy requires postgresql://.
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-smart-library-academic-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload handling: Use /tmp on serverless (read-only filesystem), local static path otherwise
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(tempfile.gettempdir(), 'uploads', 'covers'))
    else:
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads', 'covers'))

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

    SHOW_DEMO_CREDENTIALS = False
    IS_PRODUCTION = False

    @classmethod
    def init_app(cls, app):
        """Hook for post-instantiation configuration and environment validation."""
        pass

class DevelopmentConfig(Config):
    """Development configuration for local environment with SQLite."""
    DEBUG = True
    SHOW_DEMO_CREDENTIALS = True
    
    raw_db_url = os.environ.get('DATABASE_URL')
    if raw_db_url:
        SQLALCHEMY_DATABASE_URI = normalize_database_url(raw_db_url)
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "library.db")}'

class TestingConfig(Config):
    """Testing configuration with fast in-memory SQLite database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'test_covers')
    SHOW_DEMO_CREDENTIALS = True

class ProductionConfig(Config):
    """Production configuration for deployed environments (e.g. Vercel, Render, Railway)."""
    DEBUG = False
    IS_PRODUCTION = True
    SESSION_COOKIE_SECURE = True
    SHOW_DEMO_CREDENTIALS = os.environ.get('SHOW_DEMO_CREDENTIALS', '0') == '1'

    # Initial class-level defaults (validated and finalized in init_app)
    raw_db_url = os.environ.get('DATABASE_URL')
    if raw_db_url:
        SQLALCHEMY_DATABASE_URI = normalize_database_url(raw_db_url)
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "library.db")}'

    @classmethod
    def init_app(cls, app):
        super().init_app(app)

        # Enforce secure Secret Key in production: prevent fallback to default development secret
        secret = os.environ.get('SECRET_KEY')
        if not secret and (os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production'):
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is not set. "
                "In production (Vercel), a unique, unpredictable SECRET_KEY is required to secure user sessions and CSRF tokens. "
                "Please configure SECRET_KEY in your Vercel Project Settings > Environment Variables."
            )
        if secret:
            app.config['SECRET_KEY'] = secret

        # Enforce valid PostgreSQL DATABASE_URL in Vercel serverless environment
        db_url = os.environ.get('DATABASE_URL')
        if not db_url and os.environ.get('VERCEL'):
            raise ValueError(
                "CRITICAL DATABASE CONFIGURATION ERROR: DATABASE_URL environment variable is not set. "
                "Vercel serverless functions have a read-only filesystem and cannot use local SQLite. "
                "Please configure DATABASE_URL pointing to your hosted PostgreSQL database (e.g. Neon, Supabase, Render) "
                "in Vercel Project Settings > Environment Variables."
            )
        if db_url:
            app.config['SQLALCHEMY_DATABASE_URI'] = normalize_database_url(db_url)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
