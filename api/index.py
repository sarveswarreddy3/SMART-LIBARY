import sys
import os
import traceback

# Add project root directory to sys.path so app, config, models, and services resolve
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import_error = None
try:
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
            query = environ.get('QUERY_STRING', '')
            matched_path = None
            if '__path=' in query:
                from urllib.parse import parse_qs, urlencode
                qs = parse_qs(query, keep_blank_values=True)
                if '__path' in qs:
                    matched_path = qs.pop('__path')[0]
                    environ['QUERY_STRING'] = urlencode(qs, doseq=True)

            if not matched_path:
                matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')

            if matched_path:
                pure_path = matched_path.split('?')[0]
                if not pure_path.startswith('/'):
                    pure_path = '/' + pure_path
                if pure_path == '/api/index':
                    pure_path = '/'
                environ['PATH_INFO'] = pure_path
                environ['SCRIPT_NAME'] = ''
            elif environ.get('PATH_INFO') == '/api/index':
                environ['PATH_INFO'] = '/'

            return self.wsgi_app(environ, start_response)

    flask_app.wsgi_app = VercelWSGIMiddleware(flask_app.wsgi_app)
    inner_app = flask_app
except Exception:
    import_error = traceback.format_exc()
    inner_app = None

def app(environ, start_response):
    if import_error:
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Startup/Import Error:\n{import_error}".encode('utf-8')]
    try:
        return inner_app(environ, start_response)
    except Exception:
        err = traceback.format_exc()
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Runtime Invocation Error:\n{err}".encode('utf-8')]
