from services.library_service import LibraryService
from models.book import Book
from extensions import db

def test_create_book_success(app):
    """Test valid book creation."""
    form_data = {
        'isbn': '978-1111222233',
        'title': 'Distributed Computing Architecture',
        'author': 'Prof. Distributed',
        'category': 'Computer Science',
        'publisher': 'Tech Press',
        'publication_year': 2023,
        'shelf_location': 'Rack CS-09',
        'total_copies': 5
    }
    success, book = LibraryService.create_book(form_data)
    assert success is True
    assert book.title == 'Distributed Computing Architecture'
    assert book.available_copies == 5
    assert book.total_copies == 5

def test_create_book_duplicate_isbn(app, test_book):
    """Test rejection of duplicate ISBN."""
    form_data = {
        'isbn': test_book.isbn,
        'title': 'Duplicate ISBN Attempt',
        'author': 'Another Author',
        'category': 'Computer Science',
        'total_copies': 2
    }
    success, message = LibraryService.create_book(form_data)
    assert success is False
    assert "already exists" in message

def test_update_book_inventory_consistency(app, test_book):
    """Test updating copies properly recalculates available copies."""
    form_data = {
        'isbn': test_book.isbn,
        'title': test_book.title,
        'author': test_book.author,
        'category': test_book.category,
        'shelf_location': test_book.shelf_location,
        'total_copies': 6
    }
    success, updated = LibraryService.update_book(test_book.id, form_data)
    assert success is True
    assert updated.total_copies == 6
    assert updated.available_copies == 6

def test_safe_delete_book(app, test_book):
    """Test book without loans can be deleted safely."""
    book_id = test_book.id
    success, message = LibraryService.delete_book(book_id)
    assert success is True
    assert db.session.get(Book, book_id) is None
