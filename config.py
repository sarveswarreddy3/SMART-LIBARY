import os
import shutil
import tempfile
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

def normalize_database_url(url: str | None) -> str | None:
    """
    Normalize database connection URL for SQLAlchemy 2.0+ compatibility.
    Cloud providers (e.g., Neon, Supabase, Render, Railway) frequently
    provide postgres:// or postgresql:// URLs; SQLAlchemy 2.0 requires
    specifying the driver (postgresql+psycopg2://) when psycopg2 is used.
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith('postgres://'):
        return 'postgresql+psycopg2://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url

def is_serverless_environment() -> bool:
    """Detect if running in serverless environment (Vercel, AWS Lambda) or read-only filesystem."""
    return bool(
        os.environ.get('VERCEL') or
        os.environ.get('VERCEL_ENV') or
        os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or
        os.environ.get('LAMBDA_TASK_ROOT') or
        basedir.startswith('/var/task') or
        (os.name != 'nt' and not os.access(basedir, os.W_OK))
    )

def get_database_uri() -> str:
    """
    Determine the database connection URI:
    1. If DATABASE_URL is configured (e.g. hosted PostgreSQL), use it.
    2. If running in a serverless environment (Vercel) without DATABASE_URL:
       Copy the bundled library.db to writable /tmp/library.db so login,
       transactions, and queries work immediately out of the box.
    3. Otherwise use local SQLite library.db.
    """
    raw_db_url = os.environ.get('DATABASE_URL')
    if raw_db_url:
        return normalize_database_url(raw_db_url)

    if is_serverless_environment():
        tmp_dir = tempfile.gettempdir()
        tmp_db = os.path.abspath(os.path.join(tmp_dir, 'library.db'))
        bundled_db = os.path.abspath(os.path.join(basedir, 'library.db'))
        
        try:
            os.makedirs(tmp_dir, exist_ok=True)
            if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) == 0:
                if os.path.exists(bundled_db):
                    shutil.copy2(bundled_db, tmp_db)
        except Exception:
            pass

        return f'sqlite:///{tmp_db}'

    return f'sqlite:///{os.path.join(basedir, "library.db")}'

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-smart-library-academic-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload handling: Use /tmp on serverless (read-only filesystem), local static path otherwise
    if is_serverless_environment():
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

    SHOW_DEMO_CREDENTIALS = os.environ.get('SHOW_DEMO_CREDENTIALS', '1') == '1'
    IS_PRODUCTION = False

    @classmethod
    def init_app(cls, app):
        """Hook for post-instantiation configuration and environment validation."""
        pass

class DevelopmentConfig(Config):
    """Development configuration for local environment with SQLite."""
    DEBUG = True
    SHOW_DEMO_CREDENTIALS = True
    SQLALCHEMY_DATABASE_URI = get_database_uri()

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
    SHOW_DEMO_CREDENTIALS = os.environ.get('SHOW_DEMO_CREDENTIALS', '1') == '1'
    SQLALCHEMY_DATABASE_URI = get_database_uri()

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
        secret = os.environ.get('SECRET_KEY')
        if secret:
            app.config['SECRET_KEY'] = secret
        else:
            app.logger.warning("Notice: SECRET_KEY not explicitly configured in environment. Using default key.")

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
