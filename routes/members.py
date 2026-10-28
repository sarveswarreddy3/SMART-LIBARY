from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from sqlalchemy import or_
from extensions import db
from models.member import Member
from models.loan import Loan
from services.library_service import LibraryService
from routes.auth import admin_required

members_bp = Blueprint('members', __name__, url_prefix='/members')

@members_bp.route('')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    department_filter = request.args.get('department', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Member.query

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Member.member_id.ilike(search_pattern),
                Member.student_staff_id.ilike(search_pattern),
                Member.full_name.ilike(search_pattern),
                Member.email.ilike(search_pattern),
                Member.phone.ilike(search_pattern),
                Member.department.ilike(search_pattern)
            )
        )

    if department_filter and department_filter != 'all':
        query = query.filter(Member.department == department_filter)

    if status_filter and status_filter != 'all':
        query = query.filter(Member.status == status_filter)

    query = query.order_by(Member.member_id.asc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    members = pagination.items

    departments = [d[0] for d in db.session.query(Member.department).distinct().order_by(Member.department).all()]

    return render_template(
        'members/index.html',
        members=members,
        pagination=pagination,
        departments=departments,
        search_query=search_query,
        department_filter=department_filter,
        status_filter=status_filter
    )

@members_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        success, result = LibraryService.create_member(request.form)
        if success:
            flash(f"Member '{result.full_name}' ({result.member_id}) registered successfully!", "success")
            return redirect(url_for('members.view', member_id=result.id))
        else:
            flash(result, "danger")

    # Suggest next member ID
    count = db.session.query(Member).count()
    suggested_id = f"MEM-{datetime.now().year}-{count + 1:04d}"

    departments = [
        "Computer Science & Engineering",
        "Information Technology",
        "Electronics & Communication",
        "Mechanical Engineering",
        "Civil Engineering",
        "Business Administration (MBA)",
        "Data Science & AI",
        "Physics & Mathematics"
    ]

    return render_template('members/form.html', member=None, suggested_id=suggested_id, departments=departments, title="Register New Member")

@members_bp.route('/<int:member_id>')
@login_required
def view(member_id):
    member = db.session.get(Member, member_id)
    if not member:
        flash("Member not found.", "warning")
        return redirect(url_for('members.index'))

    active_loans = Loan.query.filter_by(member_id=member.id, status='issued').order_by(Loan.due_date.asc()).all()
    past_loans = Loan.query.filter(Loan.member_id == member.id, Loan.status != 'issued').order_by(Loan.return_date.desc()).all()

    can_delete, delete_reason = member.can_be_deleted()

    return render_template(
        'members/view.html',
        member=member,
        active_loans=active_loans,
        past_loans=past_loans,
        can_delete=can_delete,
        delete_reason=delete_reason
    )

@members_bp.route('/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(member_id):
    member = db.session.get(Member, member_id)
    if not member:
        flash("Member not found.", "warning")
        return redirect(url_for('members.index'))

    if request.method == 'POST':
        success, result = LibraryService.update_member(member.id, request.form)
        if success:
            flash(f"Member '{member.full_name}' updated successfully!", "success")
            return redirect(url_for('members.view', member_id=member.id))
        else:
            flash(result, "danger")

    departments = [
        "Computer Science & Engineering",
        "Information Technology",
        "Electronics & Communication",
        "Mechanical Engineering",
        "Civil Engineering",
        "Business Administration (MBA)",
        "Data Science & AI",
        "Physics & Mathematics"
    ]

    return render_template('members/form.html', member=member, suggested_id=member.member_id, departments=departments, title=f"Edit Member: {member.full_name}")

@members_bp.route('/<int:member_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(member_id):
    success, message = LibraryService.delete_member(member_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('members.index'))
