import os
import tempfile
from datetime import date
from flask import Flask, render_template, send_from_directory, redirect, url_for
from config import config
from extensions import db, login_manager, csrf

def create_app(config_name=None):
    """Application factory for Smart Library Management and Book Analytics System."""
    if config_name is None:
        if os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production':
            config_name = 'production'
        else:
            config_name = os.environ.get('FLASK_ENV', 'development')

    # Ensure an absolute, writable instance path across Linux, Windows, and Vercel serverless
    instance_path = os.path.abspath(os.path.join(tempfile.gettempdir(), 'smart_library_instance'))
    
    try:
        os.makedirs(instance_path, exist_ok=True)
    except OSError:
        pass

    app = Flask(__name__, instance_path=instance_path)
    cfg_class = config.get(config_name, config['default'])
    app.config.from_object(cfg_class)
    cfg_class.init_app(app)

    # Ensure upload directory exists safely without crashing if read-only
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        if app.config.get('DOCUMENTS_FOLDER'):
            os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
    except OSError as ex:
        app.logger.warning(f"Upload directory notice: {ex}")

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.books import books_bp
    from routes.members import members_bp
    from routes.transactions import transactions_bp
    from routes.analytics import analytics_bp
    from routes.reports import reports_bp
    from routes.profile import profile_bp
    from routes.settings import settings_bp
    from routes.chatbot import chatbot_bp
    from routes.uploads import uploads_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(uploads_bp)

    # Global template context
    @app.context_processor
    def inject_global_data():
        from models.setting import Setting
        from models.loan import Loan
        try:
            today = date.today()
            overdue_count = Loan.query.filter(Loan.status == 'issued', Loan.due_date < today).count()
            active_loans_count = Loan.query.filter_by(status='issued').count()
            library_name = Setting.get_value('library_name', 'Apex Smart Library')
            currency = Setting.get_value('currency_symbol', '$')
        except Exception:
            overdue_count = 0
            active_loans_count = 0
            library_name = 'Apex Smart Library'
            currency = '$'

        return {
            'library_name': library_name,
            'currency_symbol': currency,
            'global_overdue_count': overdue_count,
            'global_active_loans_count': active_loans_count,
            'current_year': date.today().year
        }

    # Vercel entrypoint direct request fallback
    @app.route('/api/index')
    def vercel_entry_fallback():
        return redirect(url_for('auth.login'))

    # Diagnostic Health Check Endpoint
    @app.route('/api/health-check')
    def health_check():
        from models.user import User
        from config import basedir, is_serverless_environment
        try:
            user_count = User.query.count()
            admin = User.query.filter_by(username='admin').first()
            admin_ok = admin is not None
            admin_pass_ok = admin.check_password('Admin@123') if admin else False
            librarian = User.query.filter_by(username='librarian').first()
            lib_ok = librarian is not None
            db_err = None
        except Exception as e:
            user_count = -1
            admin_ok = False
            admin_pass_ok = False
            lib_ok = False
            db_err = str(e)

        raw_uri = str(app.config.get('SQLALCHEMY_DATABASE_URI', ''))
        if '@' in raw_uri:
            creds, host_part = raw_uri.split('@', 1)
            scheme = creds.split('://')[0]
            masked_uri = f"{scheme}://****:****@{host_part}"
        else:
            masked_uri = raw_uri

        return {
            'status': 'ok',
            'is_serverless': is_serverless_environment(),
            'db_uri': masked_uri,
            'bundled_db_exists': os.path.exists(os.path.join(basedir, 'library.db')),
            'tmp_db_exists': os.path.exists('/tmp/library.db'),
            'user_count': user_count,
            'admin_exists': admin_ok,
            'admin_pass_valid': admin_pass_ok,
            'librarian_exists': lib_ok,
            'db_error': db_err
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Auto-initialize database tables and seed initial admin account if missing
    with app.app_context():
        try:
            db.create_all()
            from models.setting import Setting
            Setting.init_defaults()

            # Ensure an administrator user exists (safe, idempotent, never overwrites existing passwords)
            from models.user import User
            admin_user = User.query.filter_by(role='admin').first()
            if not admin_user:
                admin_username = os.environ.get('INITIAL_ADMIN_USERNAME', 'admin').strip()
                admin_email = os.environ.get('INITIAL_ADMIN_EMAIL', 'admin@library.edu').strip()
                admin_password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'Admin@123')
                admin_name = os.environ.get('INITIAL_ADMIN_NAME', 'Apex Chief Librarian').strip()

                new_admin = User(
                    username=admin_username,
                    email=admin_email,
                    full_name=admin_name,
                    role='admin',
                    is_active_account=True
                )
                new_admin.set_password(admin_password)
                db.session.add(new_admin)
                db.session.commit()
                app.logger.info(f"Initial administrator account '{admin_username}' provisioned.")

            # In development or when explicitly requested, provision demo librarian
            librarian_user = User.query.filter_by(role='librarian').first()
            if not librarian_user and (app.config.get('DEBUG') or app.config.get('SHOW_DEMO_CREDENTIALS') or os.environ.get('SEED_DEMO_USERS') == '1'):
                demo_lib = User(
                    username='librarian',
                    email='librarian@library.edu',
                    full_name='Demo Librarian',
                    role='librarian',
                    is_active_account=True
                )
                demo_lib.set_password('Librarian@123')
                db.session.add(demo_lib)
                db.session.commit()
                app.logger.info("Demo librarian account provisioned.")
        except Exception as ex:
            app.logger.error(f"Database initialization notice: {ex}")
            if app.config.get('IS_PRODUCTION'):
                app.logger.exception("Production database initialization error:")

    return app

# WSGI application entry point for Vercel and production WSGI servers
try:
    app = create_app()
except Exception as startup_err:
    # If production startup fails due to missing environment variables,
    # log critical message and provide clear diagnostic in development fallback
    import logging
    logging.critical(f"FATAL APPLICATION STARTUP ERROR: {startup_err}")
    raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
