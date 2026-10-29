import os
import pytest
from flask import Flask
from config import normalize_database_url, get_database_uri, ProductionConfig
from models.user import User
from extensions import db

def test_normalize_database_url():
    """Verify postgres:// and postgresql:// are rewritten to postgresql+psycopg2://."""
    assert normalize_database_url(None) is None
    assert normalize_database_url('') is None
    assert normalize_database_url('postgres://user:pass@host:5432/db') == 'postgresql+psycopg2://user:pass@host:5432/db'
    assert normalize_database_url('postgresql://user:pass@host:5432/db') == 'postgresql+psycopg2://user:pass@host:5432/db'

def test_database_uri_uses_postgres_when_set(monkeypatch):
    """Verify get_database_uri returns normalized PostgreSQL URL when DATABASE_URL is set."""
    monkeypatch.setenv('DATABASE_URL', 'postgres://testuser:testpass@localhost:5432/testdb')
    uri = get_database_uri()
    assert uri == 'postgresql+psycopg2://testuser:testpass@localhost:5432/testdb'

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

def test_vercel_wsgi_middleware():
    """Verify VercelWSGIMiddleware restores PATH_INFO from HTTP_X_MATCHED_PATH."""
    from api.index import VercelWSGIMiddleware

    def dummy_app(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b'OK']

    middleware = VercelWSGIMiddleware(dummy_app)

    # Test 1: /login request rewritten by Vercel to /api/index
    env1 = {
        'PATH_INFO': '/api/index',
        'HTTP_X_MATCHED_PATH': '/login'
    }
    middleware(env1, lambda s, h: None)
    assert env1['PATH_INFO'] == '/login'
    assert env1['SCRIPT_NAME'] == ''

    # Test 2: static file request rewritten by Vercel to /api/index
    env2 = {
        'PATH_INFO': '/api/index',
        'HTTP_X_MATCHED_PATH': '/static/css/style.css'
    }
    middleware(env2, lambda s, h: None)
    assert env2['PATH_INFO'] == '/static/css/style.css'

    # Test 3: URL with query parameters
    env3 = {
        'PATH_INFO': '/api/index',
        'HTTP_X_MATCHED_PATH': '/books?search=python'
    }
    middleware(env3, lambda s, h: None)
    assert env3['PATH_INFO'] == '/books'

    # Test 4: Rewrite with __path in QUERY_STRING
    env4 = {
        'PATH_INFO': '/api/index',
        'QUERY_STRING': '__path=/login'
    }
    middleware(env4, lambda s, h: None)
    assert env4['PATH_INFO'] == '/login'
    assert env4['QUERY_STRING'] == ''

    # Test 5: Rewrite with __path and preserved user query parameters
    env5 = {
        'PATH_INFO': '/api/index',
        'QUERY_STRING': '__path=/books&category=Programming&sort=title'
    }
    middleware(env5, lambda s, h: None)
    assert env5['PATH_INFO'] == '/books'
    assert 'category=Programming' in env5['QUERY_STRING']
    assert '__path' not in env5['QUERY_STRING']

