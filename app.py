import os
from datetime import date
from flask import Flask, render_template
from config import config
from extensions import db, login_manager, csrf

def create_app(config_name=None):
    """Application factory for Smart Library Management and Book Analytics System."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, instance_path='/tmp/instance')
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    # Auto-initialize database tables and default configuration
    with app.app_context():
        try:
            db.create_all()
            from models.setting import Setting
            Setting.init_defaults()
        except Exception as ex:
            app.logger.warning(f"Database init check: {ex}")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
