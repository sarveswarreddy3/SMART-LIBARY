from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models.user import User

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()

            if not full_name or not email:
                flash("Full name and email cannot be empty.", "danger")
                return redirect(url_for('profile.index'))

            # Check email uniqueness
            if email != current_user.email:
                existing = User.query.filter_by(email=email).first()
                if existing and existing.id != current_user.id:
                    flash(f"Email '{email}' is already in use by another user.", "danger")
                    return redirect(url_for('profile.index'))

            current_user.full_name = full_name
            current_user.email = email
            db.session.commit()
            flash("Profile information updated successfully!", "success")
            return redirect(url_for('profile.index'))

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for('profile.index'))

            if len(new_pw) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('profile.index'))

            if new_pw != confirm_pw:
                flash("New password and confirmation do not match.", "danger")
                return redirect(url_for('profile.index'))

            current_user.set_password(new_pw)
            db.session.commit()
            flash("Your password has been changed successfully!", "success")
            return redirect(url_for('profile.index'))

    return render_template('profile.html', user=current_user)
