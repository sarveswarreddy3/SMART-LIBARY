from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from extensions import db
from models.setting import Setting
from models.user import User
from routes.auth import admin_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('', methods=['GET', 'POST'])
@login_required
@admin_required
def index():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_settings':
            library_name = request.form.get('library_name', '').strip()
            loan_days = request.form.get('default_loan_days', '14').strip()
            fine_rate = request.form.get('fine_rate_per_day', '1.00').strip()
            max_books = request.form.get('max_books_per_member', '4').strip()
            currency = request.form.get('currency_symbol', '$').strip()

            if library_name:
                Setting.set_value('library_name', library_name, 'Official library portal name')

            try:
                days_int = int(loan_days)
                if days_int > 0:
                    Setting.set_value('default_loan_days', str(days_int), 'Standard borrowing duration in days')
            except ValueError:
                pass

            try:
                rate_flt = float(fine_rate)
                if rate_flt >= 0:
                    Setting.set_value('fine_rate_per_day', f"{rate_flt:.2f}", 'Late fine charged per day overdue')
            except ValueError:
                pass

            try:
                max_int = int(max_books)
                if max_int > 0:
                    Setting.set_value('max_books_per_member', str(max_int), 'Maximum concurrent active loans per member')
            except ValueError:
                pass

            if currency:
                Setting.set_value('currency_symbol', currency, 'Currency symbol for fines and transactions')

            flash("System settings saved successfully!", "success")
            return redirect(url_for('settings.index'))

        elif action == 'create_user':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            full_name = request.form.get('full_name', '').strip()
            role = request.form.get('role', 'librarian').strip()
            password = request.form.get('password', '')

            if not username or not email or not full_name or not password:
                flash("All user fields are required.", "danger")
                return redirect(url_for('settings.index'))

            if User.query.filter_by(username=username).first():
                flash(f"Username '{username}' already exists.", "danger")
                return redirect(url_for('settings.index'))

            if User.query.filter_by(email=email).first():
                flash(f"Email '{email}' is already registered.", "danger")
                return redirect(url_for('settings.index'))

            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                is_active_account=True
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash(f"Staff account for {full_name} ({role}) created successfully!", "success")
            return redirect(url_for('settings.index'))

    # Load current values
    settings_dict = {
        'library_name': Setting.get_value('library_name', 'Apex Smart Library & Analytics System'),
        'default_loan_days': Setting.get_int('default_loan_days', 14),
        'fine_rate_per_day': Setting.get_float('fine_rate_per_day', 1.00),
        'max_books_per_member': Setting.get_int('max_books_per_member', 4),
        'currency_symbol': Setting.get_value('currency_symbol', '$')
    }

    staff_users = User.query.order_by(User.role.asc(), User.username.asc()).all()

    return render_template('settings.html', settings=settings_dict, staff_users=staff_users)
