from datetime import date, timedelta
from services.library_service import LibraryService
from extensions import db
from models.loan import Loan

def test_issue_book_success(app, test_book, test_member):
    """Test issuing a copy decrements available inventory and creates loan."""
    initial_available = test_book.available_copies
    success, loan = LibraryService.issue_book(
        member_id=test_member.id,
        book_id=test_book.id
    )
    assert success is True
    assert loan.status == 'issued'
    assert test_book.available_copies == initial_available - 1
    assert loan.book_id == test_book.id
    assert loan.member_id == test_member.id

def test_reject_duplicate_active_issue(app, test_book, test_member):
    """Prevent member from issuing multiple active copies of the exact same title."""
    success1, _ = LibraryService.issue_book(test_member.id, test_book.id)
    assert success1 is True

    success2, message = LibraryService.issue_book(test_member.id, test_book.id)
    assert success2 is False
    assert "already has an active issued copy" in message

def test_reject_issue_when_zero_copies(app, test_book, test_member):
    """Prevent issuing when available copies are exhausted."""
    test_book.available_copies = 0
    db.session.commit()

    success, message = LibraryService.issue_book(test_member.id, test_book.id)
    assert success is False
    assert "no copies currently available" in message

def test_return_book_success(app, test_book, test_member):
    """Test returning restores available inventory count and sets status to returned."""
    # First issue
    success, loan = LibraryService.issue_book(test_member.id, test_book.id)
    assert success is True
    avail_after_issue = test_book.available_copies

    # Process return
    ret_success, ret_loan = LibraryService.return_book(loan.id)
    assert ret_success is True
    assert ret_loan.status == 'returned'
    assert ret_loan.return_date == date.today()
    assert test_book.available_copies == avail_after_issue + 1

def test_prevent_duplicate_returns(app, test_book, test_member):
    """Prevent returning an already returned loan."""
    success, loan = LibraryService.issue_book(test_member.id, test_book.id)
    LibraryService.return_book(loan.id)

    # Second return attempt
    dup_success, dup_msg = LibraryService.return_book(loan.id)
    assert dup_success is False
    assert "already been returned" in dup_msg

def test_overdue_fine_calculation(app, test_book, test_member):
    """Verify late fine is calculated correctly when returned after due date."""
    # Issue a loan normally
    success, loan = LibraryService.issue_book(
        test_member.id,
        test_book.id
    )
    assert success is True

    # Simulate loan becoming overdue by 5 days
    loan.due_date = date.today() - timedelta(days=5)
    db.session.commit()

    # Return today (5 days late at $1.00/day = $5.00)
    ret_success, ret_loan = LibraryService.return_book(loan.id)
    assert ret_success is True
    assert ret_loan.fine_amount == 5.00
