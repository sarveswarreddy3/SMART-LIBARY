import sys
import os

# Add project root directory to sys.path so app, config, models, and services resolve
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app as flask_app

class VercelWSGIMiddleware:
    """
    WSGI Middleware for Vercel Serverless Routing:
    When Vercel uses rewrite rules to send traffic to /api/index,
    Vercel sets PATH_INFO='/api/index' while passing the original request URL
    (e.g. '/login', '/dashboard', '/static/css/style.css') in HTTP_X_MATCHED_PATH
    or HTTP_X_FORWARDED_URI.
    
    This middleware restores PATH_INFO from HTTP_X_MATCHED_PATH so that
    Flask matches routes, blueprints, and static files accurately.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
        if matched_path:
            # Strip query string if embedded in matched path
            pure_path = matched_path.split('?')[0]
            environ['PATH_INFO'] = pure_path
            environ['SCRIPT_NAME'] = ''

        return self.wsgi_app(environ, start_response)

app = VercelWSGIMiddleware(flask_app)
