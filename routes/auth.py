from functools import wraps
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models.user import User

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash("Administrator privileges are required to access this resource.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    show_demo = current_app.config.get('SHOW_DEMO_CREDENTIALS', current_app.config.get('DEBUG', False))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return render_template('login.html', show_demo_credentials=show_demo)

        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("This account has been deactivated. Please contact the administrator.", "danger")
                return render_template('login.html', show_demo_credentials=show_demo)

            login_user(user, remember=remember)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('http'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template('login.html', show_demo_credentials=show_demo)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))
