from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.books import books_bp
from routes.members import members_bp
from routes.transactions import transactions_bp
from routes.analytics import analytics_bp
from routes.reports import reports_bp
from routes.profile import profile_bp
from routes.settings import settings_bp
from routes.uploads import uploads_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'books_bp',
    'members_bp',
    'transactions_bp',
    'analytics_bp',
    'reports_bp',
    'profile_bp',
    'settings_bp',
    'uploads_bp'
]
