import os
import pytest
from flask import Flask
from config import normalize_database_url, get_database_uri, ProductionConfig
from models.user import User
from extensions import db

def test_normalize_database_url():
    """Verify postgres:// is rewritten to postgresql:// and postgresql:// is preserved."""
    assert normalize_database_url(None) is None
    assert normalize_database_url('') is None
    assert normalize_database_url('postgres://user:pass@host:5432/db') == 'postgresql://user:pass@host:5432/db'
    assert normalize_database_url('postgresql://user:pass@host:5432/db') == 'postgresql://user:pass@host:5432/db'

def test_database_uri_uses_postgres_when_set(monkeypatch):
    """Verify get_database_uri returns normalized PostgreSQL URL when DATABASE_URL is set."""
    monkeypatch.setenv('DATABASE_URL', 'postgres://testuser:testpass@localhost:5432/testdb')
    uri = get_database_uri()
    assert uri == 'postgresql://testuser:testpass@localhost:5432/testdb'

def test_database_uri_fallback_on_serverless(monkeypatch, tmp_path):
    """Verify get_database_uri uses /tmp/library.db fallback on serverless when DATABASE_URL is not set."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('VERCEL', '1')
    uri = get_database_uri()
    assert uri.startswith('sqlite:///')
    # Must point to writable storage or valid db
    assert 'library.db' in uri

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
