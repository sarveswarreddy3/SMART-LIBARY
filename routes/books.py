import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from extensions import db
from models.book import Book
from models.loan import Loan
from services.library_service import LibraryService
from routes.auth import admin_required

books_bp = Blueprint('books', __name__, url_prefix='/books')

def save_cover_image(file):
    """Safely validate and save an uploaded book cover image."""
    if not file or file.filename == '':
        return None
    
    filename = secure_filename(file.filename)
    if not '.' in filename:
        return None
        
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return None

    unique_filename = f"cover_{uuid.uuid4().hex[:10]}.{ext}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    try:
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)
        return unique_filename
    except OSError as err:
        current_app.logger.warning(f"Could not persist cover image to disk ({err}). Falling back to default cover.")
        return None

@books_bp.route('')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    availability_filter = request.args.get('availability', '').strip()
    sort_by = request.args.get('sort_by', 'title').strip()

    query = Book.query

    # Search filter
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_pattern),
                Book.author.ilike(search_pattern),
                Book.isbn.ilike(search_pattern),
                Book.category.ilike(search_pattern),
                Book.shelf_location.ilike(search_pattern)
            )
        )

    # Category filter
    if category_filter and category_filter != 'all':
        query = query.filter(Book.category == category_filter)

    # Availability filter
    if availability_filter == 'available':
        query = query.filter(Book.available_copies > 0)
    elif availability_filter == 'unavailable':
        query = query.filter(Book.available_copies == 0)

    # Sorting
    if sort_by == 'author':
        query = query.order_by(Book.author.asc())
    elif sort_by == 'copies':
        query = query.order_by(Book.total_copies.desc())
    elif sort_by == 'available':
        query = query.order_by(Book.available_copies.desc())
    elif sort_by == 'recent':
        query = query.order_by(Book.created_at.desc())
    else:
        query = query.order_by(Book.title.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    books = pagination.items

    # Fetch unique categories for filter dropdown
    categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all()]

    return render_template(
        'books/index.html',
        books=books,
        pagination=pagination,
        categories=categories,
        search_query=search_query,
        category_filter=category_filter,
        availability_filter=availability_filter,
        sort_by=sort_by
    )

@books_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        cover_file = request.files.get('cover_image')
        cover_filename = save_cover_image(cover_file)

        success, result = LibraryService.create_book(request.form, cover_filename)
        if success:
            flash(f"Book '{result.title}' added successfully to inventory!", "success")
            return redirect(url_for('books.view', book_id=result.id))
        else:
            flash(result, "danger")

    # Categories list for autocomplete / selector
    existing_categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all()]
    return render_template('books/form.html', book=None, categories=existing_categories, title="Add New Book")

@books_bp.route('/<int:book_id>')
@login_required
def view(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "warning")
        return redirect(url_for('books.index'))

    # Active and past loans for this book
    active_loans = Loan.query.filter_by(book_id=book.id, status='issued').all()
    past_loans = Loan.query.filter(Loan.book_id == book.id, Loan.status != 'issued').order_by(Loan.return_date.desc()).limit(10).all()

    can_delete, delete_reason = book.can_be_deleted()

    return render_template(
        'books/view.html',
        book=book,
        active_loans=active_loans,
        past_loans=past_loans,
        can_delete=can_delete,
        delete_reason=delete_reason
    )

@books_bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash("Book not found.", "warning")
        return redirect(url_for('books.index'))

    if request.method == 'POST':
        cover_file = request.files.get('cover_image')
        cover_filename = save_cover_image(cover_file)

        success, result = LibraryService.update_book(book.id, request.form, cover_filename)
        if success:
            flash(f"Book '{book.title}' updated successfully!", "success")
            return redirect(url_for('books.view', book_id=book.id))
        else:
            flash(result, "danger")

    existing_categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all()]
    return render_template('books/form.html', book=book, categories=existing_categories, title=f"Edit Book: {book.title}")

@books_bp.route('/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(book_id):
    success, message = LibraryService.delete_book(book_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('books.index'))
