import os
import pytest
from flask import Flask
from config import normalize_database_url, ProductionConfig
from app import create_app
from models.user import User
from extensions import db

def test_normalize_database_url():
    """Verify postgres:// is rewritten to postgresql:// and postgresql:// is preserved."""
    assert normalize_database_url(None) is None
    assert normalize_database_url('') is None
    assert normalize_database_url('postgres://user:pass@host:5432/db') == 'postgresql://user:pass@host:5432/db'
    assert normalize_database_url('postgresql://user:pass@host:5432/db') == 'postgresql://user:pass@host:5432/db'

def test_production_config_requires_database_url_on_vercel(monkeypatch):
    """Verify create_app('production') raises ValueError if DATABASE_URL is missing on Vercel."""
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('SECRET_KEY', 'valid-test-secret-key-1234567890')
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL environment variable is not set"):
        dummy_app = Flask(__name__)
        ProductionConfig.init_app(dummy_app)

def test_production_config_requires_secret_key_on_vercel(monkeypatch):
    """Verify create_app('production') raises ValueError if SECRET_KEY is missing on Vercel."""
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host:5432/db')
    monkeypatch.delenv('SECRET_KEY', raising=False)

    with pytest.raises(ValueError, match="SECRET_KEY environment variable is not set"):
        dummy_app = Flask(__name__)
        ProductionConfig.init_app(dummy_app)

def test_admin_idempotence(app):
    """Verify existing admin accounts are never overwritten or reset."""
    with app.app_context():
        # First ensure admin exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@library.edu',
                full_name='Apex Chief Librarian',
                role='admin',
                is_active_account=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()

        # Admin changes their password
        admin.set_password('CustomSecret@456')
        db.session.commit()
        original_hash = admin.password_hash

        # Run startup check again (simulating subsequent request / warm start)
        existing_admin = User.query.filter_by(role='admin').first()
        assert existing_admin is not None
        assert existing_admin.password_hash == original_hash
        assert existing_admin.check_password('CustomSecret@456') is True
        assert existing_admin.check_password('Admin@123') is False
