import uuid
from datetime import date, datetime, timedelta
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting

class LibraryService:
    """Core domain service for library circulation, inventory consistency, and validation."""

    @staticmethod
    def generate_transaction_id():
        """Generate human-readable unique transaction ID."""
        now = datetime.now()
        prefix = f"TXN-{now.strftime('%Y%m')}"
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{random_suffix}"

    @classmethod
    def issue_book(cls, member_id, book_id, issued_by_user_id=None, loan_days=None, custom_due_date=None, notes=None):
        """
        Atomically issue a book to a member with complete business rules validation.
        """
        member = db.session.get(Member, member_id)
        if not member:
            return False, "Selected member not found."

        if member.status != 'Active':
            return False, f"Member account is {member.status}. Only 'Active' members can borrow books."

        # Check maximum allowed books limit
        max_allowed = Setting.get_int('max_books_per_member', 4)
        if member.active_loans_count >= max_allowed:
            return False, f"Member has reached the maximum borrowing limit of {max_allowed} active books."

        book = db.session.get(Book, book_id)
        if not book:
            return False, "Selected book not found."

        if book.available_copies <= 0:
            return False, f"Book '{book.title}' has no copies currently available for issue."

        # Check if member already has an active copy of this exact book
        existing_active = Loan.query.filter_by(
            member_id=member.id,
            book_id=book.id,
            status='issued'
        ).first()
        if existing_active:
            return False, f"Member already has an active issued copy of '{book.title}' (Txn: {existing_active.transaction_id})."

        # Calculate due date
        today = date.today()
        if custom_due_date:
            due_date = custom_due_date
        else:
            default_days = loan_days or Setting.get_int('default_loan_days', 14)
            due_date = today + timedelta(days=default_days)

        if due_date <= today:
            return False, "Due date must be in the future."

        # Atomic transaction
        try:
            # Decrement book available copies
            book.available_copies -= 1

            # Create loan record
            loan = Loan(
                transaction_id=cls.generate_transaction_id(),
                book_id=book.id,
                member_id=member.id,
                issued_by_id=issued_by_user_id,
                issue_date=today,
                due_date=due_date,
                status='issued',
                fine_amount=0.0,
                fine_paid=False,
                notes=notes
            )
            db.session.add(loan)
            db.session.commit()
            return True, loan
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to issue book: {str(e)}"

    @classmethod
    def return_book(cls, loan_id, returned_by_user_id=None, return_date=None, fine_paid=None, notes=None):
        """
        Atomically process a book return, recalculate late fine, and increment inventory.
        """
        loan = db.session.get(Loan, loan_id)
        if not loan:
            return False, "Transaction record not found."

        if loan.status == 'returned':
            return False, f"Book has already been returned on {loan.return_date.strftime('%Y-%m-%d')}."

        actual_return_date = return_date or date.today()
        if actual_return_date < loan.issue_date:
            return False, "Return date cannot be prior to the issue date."

        book = loan.book
        if not book:
            return False, "Associated book record missing."

        # Calculate late fine
        fine_rate = Setting.get_float('fine_rate_per_day', 1.0)
        overdue_days = max(0, (actual_return_date - loan.due_date).days)
        calculated_fine = round(overdue_days * fine_rate, 2)

        try:
            # Increment book available copies exactly once
            if book.available_copies < book.total_copies:
                book.available_copies += 1

            loan.return_date = actual_return_date
            loan.status = 'returned'
            loan.returned_by_id = returned_by_user_id
            loan.fine_amount = calculated_fine
            
            if fine_paid is not None:
                loan.fine_paid = fine_paid
            elif calculated_fine == 0.0:
                loan.fine_paid = True

            if notes:
                loan.notes = (loan.notes + " | " + notes) if loan.notes else notes

            db.session.commit()
            return True, loan
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to process return: {str(e)}"

    @classmethod
    def create_book(cls, form_data, cover_filename=None):
        """Validate and create a new book with copy checks."""
        isbn = form_data.get('isbn', '').strip() or None
        title = form_data.get('title', '').strip()
        author = form_data.get('author', '').strip()
        category = form_data.get('category', '').strip()
        publisher = form_data.get('publisher', '').strip() or None
        year = form_data.get('publication_year')
        description = form_data.get('description', '').strip() or None
        shelf = form_data.get('shelf_location', '').strip() or 'General Stack'
        total_copies = int(form_data.get('total_copies', 1))

        if not title or not author or not category:
            return False, "Title, author, and category are mandatory."

        if total_copies < 1:
            return False, "Total copies must be at least 1."

        if isbn:
            existing = Book.query.filter_by(isbn=isbn).first()
            if existing:
                return False, f"A book with ISBN '{isbn}' already exists ({existing.title})."

        try:
            pub_year = int(year) if year else None
        except ValueError:
            pub_year = None

        book = Book(
            isbn=isbn,
            title=title,
            author=author,
            category=category,
            publisher=publisher,
            publication_year=pub_year,
            description=description,
            shelf_location=shelf,
            total_copies=total_copies,
            available_copies=total_copies,  # Initially all copies are available
            cover_image=cover_filename
        )
        try:
            db.session.add(book)
            db.session.commit()
            return True, book
        except Exception as e:
            db.session.rollback()
            return False, f"Database error creating book: {str(e)}"

    @classmethod
    def update_book(cls, book_id, form_data, cover_filename=None):
        """Update existing book details while strictly maintaining copy consistency."""
        book = db.session.get(Book, book_id)
        if not book:
            return False, "Book not found."

        isbn = form_data.get('isbn', '').strip() or None
        title = form_data.get('title', '').strip()
        author = form_data.get('author', '').strip()
        category = form_data.get('category', '').strip()
        publisher = form_data.get('publisher', '').strip() or None
        year = form_data.get('publication_year')
        description = form_data.get('description', '').strip() or None
        shelf = form_data.get('shelf_location', '').strip() or book.shelf_location
        new_total_copies = int(form_data.get('total_copies', book.total_copies))

        if not title or not author or not category:
            return False, "Title, author, and category are required."

        if isbn and isbn != book.isbn:
            conflict = Book.query.filter_by(isbn=isbn).first()
            if conflict and conflict.id != book.id:
                return False, f"ISBN '{isbn}' is already used by another book."

        # Validate total copies against current issued copies
        currently_issued = book.issued_copies
        if new_total_copies < currently_issued:
            return False, f"Cannot reduce total copies to {new_total_copies}: {currently_issued} copies are currently issued to members."

        # Calculate new available copies based on total difference
        copy_delta = new_total_copies - book.total_copies
        new_available = book.available_copies + copy_delta
        if new_available < 0 or new_available > new_total_copies:
            return False, "Invalid copy count calculation."

        try:
            pub_year = int(year) if year else None
        except ValueError:
            pub_year = None

        book.isbn = isbn
        book.title = title
        book.author = author
        book.category = category
        book.publisher = publisher
        book.publication_year = pub_year
        book.description = description
        book.shelf_location = shelf
        book.total_copies = new_total_copies
        book.available_copies = new_available
        if cover_filename:
            book.cover_image = cover_filename

        try:
            db.session.commit()
            return True, book
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update book: {str(e)}"

    @classmethod
    def delete_book(cls, book_id):
        """Safely delete book only if no active or historical loans exist."""
        book = db.session.get(Book, book_id)
        if not book:
            return False, "Book not found."

        can_delete, reason = book.can_be_deleted()
        if not can_delete:
            return False, reason

        try:
            db.session.delete(book)
            db.session.commit()
            return True, "Book deleted successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete book: {str(e)}"

    @classmethod
    def create_member(cls, form_data):
        """Validate and create a new library member."""
        member_id = form_data.get('member_id', '').strip()
        student_staff_id = form_data.get('student_staff_id', '').strip()
        full_name = form_data.get('full_name', '').strip()
        email = form_data.get('email', '').strip().lower()
        phone = form_data.get('phone', '').strip() or None
        department = form_data.get('department', '').strip()
        status = form_data.get('status', 'Active').strip()

        if not member_id or not student_staff_id or not full_name or not email or not department:
            return False, "Member ID, Student/Staff ID, Name, Email, and Department are required."

        # Unique checks
        if Member.query.filter_by(member_id=member_id).first():
            return False, f"Member ID '{member_id}' is already registered."
        if Member.query.filter_by(student_staff_id=student_staff_id).first():
            return False, f"Student/Staff ID '{student_staff_id}' is already registered."
        if Member.query.filter_by(email=email).first():
            return False, f"Email address '{email}' is already registered to a member."

        member = Member(
            member_id=member_id,
            student_staff_id=student_staff_id,
            full_name=full_name,
            email=email,
            phone=phone,
            department=department,
            status=status,
            membership_date=date.today()
        )
        try:
            db.session.add(member)
            db.session.commit()
            return True, member
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to register member: {str(e)}"

    @classmethod
    def update_member(cls, member_id, form_data):
        """Update member details with uniqueness safeguards."""
        member = db.session.get(Member, member_id)
        if not member:
            return False, "Member not found."

        student_staff_id = form_data.get('student_staff_id', '').strip()
        full_name = form_data.get('full_name', '').strip()
        email = form_data.get('email', '').strip().lower()
        phone = form_data.get('phone', '').strip() or None
        department = form_data.get('department', '').strip()
        status = form_data.get('status', member.status).strip()

        if not student_staff_id or not full_name or not email or not department:
            return False, "Required fields cannot be empty."

        # Check unique student_staff_id
        if student_staff_id != member.student_staff_id:
            conflict = Member.query.filter_by(student_staff_id=student_staff_id).first()
            if conflict and conflict.id != member.id:
                return False, f"Student/Staff ID '{student_staff_id}' belongs to another member."

        # Check unique email
        if email != member.email:
            conflict = Member.query.filter_by(email=email).first()
            if conflict and conflict.id != member.id:
                return False, f"Email '{email}' is already registered to another member."

        member.student_staff_id = student_staff_id
        member.full_name = full_name
        member.email = email
        member.phone = phone
        member.department = department
        member.status = status

        try:
            db.session.commit()
            return True, member
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update member: {str(e)}"

    @classmethod
    def delete_member(cls, member_id):
        """Safely delete member only if no loans or transactions are tied to them."""
        member = db.session.get(Member, member_id)
        if not member:
            return False, "Member not found."

        can_delete, reason = member.can_be_deleted()
        if not can_delete:
            return False, reason

        try:
            db.session.delete(member)
            db.session.commit()
            return True, "Member deleted successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete member: {str(e)}"
