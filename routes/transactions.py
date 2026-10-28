from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting
from services.library_service import LibraryService

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@transactions_bp.route('/issue', methods=['GET', 'POST'])
@login_required
def issue():
    if request.method == 'POST':
        member_id = request.form.get('member_id', type=int)
        book_id = request.form.get('book_id', type=int)
        due_date_str = request.form.get('due_date', '').strip()
        notes = request.form.get('notes', '').strip()

        custom_due = None
        if due_date_str:
            try:
                custom_due = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid due date format. Please use YYYY-MM-DD.", "danger")
                return redirect(url_for('transactions.issue'))

        success, result = LibraryService.issue_book(
            member_id=member_id,
            book_id=book_id,
            issued_by_user_id=current_user.id,
            custom_due_date=custom_due,
            notes=notes
        )

        if success:
            flash(f"Book '{result.book.title}' successfully issued to {result.member.full_name} (Txn: {result.transaction_id})!", "success")
            return redirect(url_for('transactions.history'))
        else:
            flash(result, "danger")

    # Pre-selection support
    pre_book_id = request.args.get('book_id', type=int)
    pre_member_id = request.args.get('member_id', type=int)

    # Fetch active members & books with copies available
    members = Member.query.filter_by(status='Active').order_by(Member.full_name).all()
    books = Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()

    default_days = Setting.get_int('default_loan_days', 14)
    suggested_due_date = date.today() + timedelta(days=default_days)

    return render_template(
        'transactions/issue.html',
        members=members,
        books=books,
        pre_book_id=pre_book_id,
        pre_member_id=pre_member_id,
        suggested_due_date=suggested_due_date.strftime('%Y-%m-%d'),
        default_days=default_days
    )

@transactions_bp.route('/return', methods=['GET', 'POST'])
@login_required
def return_book():
    today = date.today()
    fine_rate = Setting.get_float('fine_rate_per_day', 1.0)
    currency = Setting.get_value('currency_symbol', '$')

    if request.method == 'POST':
        loan_id = request.form.get('loan_id', type=int)
        fine_paid = bool(request.form.get('fine_paid'))
        notes = request.form.get('notes', '').strip()

        success, result = LibraryService.return_book(
            loan_id=loan_id,
            returned_by_user_id=current_user.id,
            return_date=today,
            fine_paid=fine_paid,
            notes=notes
        )

        if success:
            fine_msg = f" Fine of {currency}{result.fine_amount:.2f} recorded." if result.fine_amount > 0 else ""
            flash(f"Book '{result.book.title}' returned successfully!{fine_msg}", "success")
            return redirect(url_for('transactions.history'))
        else:
            flash(result, "danger")

    # Selected loan to process
    loan_id = request.args.get('loan_id', type=int)
    selected_loan = db.session.get(Loan, loan_id) if loan_id else None

    # Search for active loans
    search_query = request.args.get('q', '').strip()
    active_loans_query = Loan.query.filter_by(status='issued')

    if search_query:
        search_pattern = f"%{search_query}%"
        active_loans_query = active_loans_query.join(Book).join(Member).filter(
            or_(
                Loan.transaction_id.ilike(search_pattern),
                Book.title.ilike(search_pattern),
                Book.isbn.ilike(search_pattern),
                Member.full_name.ilike(search_pattern),
                Member.member_id.ilike(search_pattern)
            )
        )

    active_loans = active_loans_query.order_by(Loan.due_date.asc()).limit(20).all()

    return render_template(
        'transactions/return.html',
        selected_loan=selected_loan,
        active_loans=active_loans,
        search_query=search_query,
        today=today,
        fine_rate=fine_rate,
        currency=currency
    )

@transactions_bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all').strip()
    search_query = request.args.get('q', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()

    today = date.today()
    query = Loan.query.join(Book).join(Member)

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Loan.transaction_id.ilike(search_pattern),
                Book.title.ilike(search_pattern),
                Member.full_name.ilike(search_pattern),
                Member.member_id.ilike(search_pattern)
            )
        )

    if status_filter == 'issued':
        query = query.filter(Loan.status == 'issued', Loan.due_date >= today)
    elif status_filter == 'overdue':
        query = query.filter(Loan.status == 'issued', Loan.due_date < today)
    elif status_filter == 'returned':
        query = query.filter(Loan.status == 'returned')

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Loan.issue_date >= start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(Loan.issue_date <= end_date)
        except ValueError:
            pass

    query = query.order_by(Loan.created_at.desc())
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    loans = pagination.items

    currency = Setting.get_value('currency_symbol', '$')
    fine_rate = Setting.get_float('fine_rate_per_day', 1.0)

    return render_template(
        'transactions/history.html',
        loans=loans,
        pagination=pagination,
        status_filter=status_filter,
        search_query=search_query,
        start_date=start_date_str,
        end_date=end_date_str,
        currency=currency,
        fine_rate=fine_rate
    )

@transactions_bp.route('/overdue')
@login_required
def overdue():
    today = date.today()
    fine_rate = Setting.get_float('fine_rate_per_day', 1.0)
    currency = Setting.get_value('currency_symbol', '$')

    overdue_loans = Loan.query.filter(
        Loan.status == 'issued',
        Loan.due_date < today
    ).order_by(Loan.due_date.asc()).all()

    total_projected_fines = sum(loan.calculate_projected_fine(fine_rate) for loan in overdue_loans)

    return render_template(
        'transactions/overdue.html',
        overdue_loans=overdue_loans,
        total_projected_fines=round(total_projected_fines, 2),
        fine_rate=fine_rate,
        currency=currency
    )

@transactions_bp.route('/<int:loan_id>/pay-fine', methods=['POST'])
@login_required
def pay_fine(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        flash("Transaction record not found.", "warning")
        return redirect(url_for('transactions.history'))

    loan.fine_paid = True
    db.session.commit()
    flash(f"Fine for transaction {loan.transaction_id} marked as PAID.", "success")
    return redirect(request.referrer or url_for('transactions.history'))
