import pytest
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models.user import User
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting

@pytest.fixture
def app():
    """Create and configure a clean testing app instance with in-memory SQLite."""
    test_app = create_app('testing')
    
    with test_app.app_context():
        db.create_all()
        Setting.init_defaults()
        yield test_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()

@pytest.fixture
def admin_user(app):
    """Create test administrator."""
    user = User(
        username='admin_test',
        email='admin_test@library.edu',
        full_name='Test Administrator',
        role='admin'
    )
    user.set_password('AdminTest@123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def librarian_user(app):
    """Create test librarian."""
    user = User(
        username='librarian_test',
        email='librarian_test@library.edu',
        full_name='Test Librarian',
        role='librarian'
    )
    user.set_password('LibrarianTest@123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_client(client, admin_user):
    """Client authenticated as administrator."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client

@pytest.fixture
def test_book(app):
    """Create sample book in database."""
    book = Book(
        isbn='978-0111222333',
        title='Automated Software Testing Principles',
        author='Dr. Quality',
        category='Computer Science',
        publisher='Academic Press',
        publication_year=2024,
        shelf_location='Rack T-1',
        total_copies=3,
        available_copies=3
    )
    db.session.add(book)
    db.session.commit()
    return book

@pytest.fixture
def test_member(app):
    """Create sample member in database."""
    member = Member(
        member_id='MEM-TEST-001',
        student_staff_id='STU-9999',
        full_name='Jordan Tester',
        email='jordan.tester@apex.edu',
        phone='+1 555-0199',
        department='Computer Science & Engineering',
        status='Active'
    )
    db.session.add(member)
    db.session.commit()
    return member
