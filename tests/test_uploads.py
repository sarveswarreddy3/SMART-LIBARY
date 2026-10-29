import io
import json
import pytest
from werkzeug.datastructures import FileStorage
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.document import Document
from models.import_log import ImportLog
from services.file_validator import (
    validate_uploaded_file,
    FileValidationError,
    generate_stored_filename
)
from services.import_service import ImportService
from services.storage_service import StorageService

def test_upload_page_requires_login(client):
    """Verify unauthenticated requests to /uploads are redirected to /login."""
    response = client.get('/uploads/')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')

def test_upload_page_renders_for_authenticated_user(auth_client):
    """Verify authenticated user can view the Upload & Import Center."""
    response = auth_client.get('/uploads/')
    assert response.status_code == 200
    assert b'Upload &amp; Import Center' in response.data or b'Upload & Import Center' in response.data
    assert b'Data Import (Excel / CSV)' in response.data
    assert b'Library Documents' in response.data

def test_download_sample_templates(auth_client):
    """Verify sample CSV templates can be downloaded for all target entities."""
    for entity in ['books', 'members', 'transactions']:
        res = auth_client.get(f'/uploads/template/{entity}')
        assert res.status_code == 200
        assert res.headers['Content-Type'].startswith('text/csv')
        assert f'{entity}_import_template.csv' in res.headers.get('Content-Disposition', '')
        assert len(res.data) > 0

def test_file_validator_rules():
    """Verify extension whitelisting and rejection of dangerous extensions."""
    # Valid CSV
    valid_csv = FileStorage(stream=io.BytesIO(b"title,author\nTest,Author"), filename="data.csv")
    ext, size = validate_uploaded_file(valid_csv)
    assert ext == 'csv'
    assert size > 0

    # Disallowed executable extension
    bad_file = FileStorage(stream=io.BytesIO(b"malicious executable"), filename="payload.exe")
    with pytest.raises(FileValidationError, match="Invalid file type"):
        validate_uploaded_file(bad_file)

    # Empty 0-byte file
    empty_file = FileStorage(stream=io.BytesIO(b""), filename="empty.csv")
    with pytest.raises(FileValidationError, match="empty"):
        validate_uploaded_file(empty_file)

    # Magic byte mismatch (e.g. .pdf extension but fake text content)
    fake_pdf = FileStorage(stream=io.BytesIO(b"Not a real pdf header"), filename="fake.pdf")
    with pytest.raises(FileValidationError, match="does not match genuine"):
        validate_uploaded_file(fake_pdf)

    # Genuine PDF signature
    real_pdf = FileStorage(stream=io.BytesIO(b"%PDF-1.4 sample pdf content"), filename="doc.pdf")
    ext_pdf, size_pdf = validate_uploaded_file(real_pdf)
    assert ext_pdf == 'pdf'

def test_file_validator_oversized(monkeypatch):
    """Verify files exceeding size limit are rejected."""
    large_stream = io.BytesIO(b"A" * 1000)
    file_storage = FileStorage(stream=large_stream, filename="test.csv")
    
    with pytest.raises(FileValidationError, match="exceeds maximum allowed limit"):
        validate_uploaded_file(file_storage, max_bytes=500)

def test_tabular_preview_route(auth_client):
    """Verify POST /uploads/preview parses headers and returns sample rows."""
    csv_data = (
        "Book Title,Author Name,Genre,ISBN Number\n"
        "Domain-Driven Design,Eric Evans,Software Architecture,978-0321125217\n"
        "Refactoring,Martin Fowler,Programming,978-0201485677\n"
    ).encode('utf-8')

    data = {
        'file': (io.BytesIO(csv_data), 'test_books.csv'),
        'target_entity': 'books'
    }
    response = auth_client.post('/uploads/preview', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    res_json = response.get_json()
    assert res_json['status'] == 'success'
    preview = res_json['data']
    assert preview['total_rows'] == 2
    assert 'Book Title' in preview['headers']
    assert len(preview['sample_rows']) == 2
    assert preview['preview_token'] != ''

def test_execute_import_books_with_duplicates_skip(app, auth_client):
    """
    Verify books import executes cleanly, detects duplicate ISBNs,
    skips duplicates when strategy is 'skip', and creates an ImportLog.
    """
    with app.app_context():
        # Seed an existing book
        existing = Book(
            title="Existing Book",
            author="Existing Author",
            category="Programming",
            isbn="978-0000000001",
            total_copies=2,
            available_copies=2
        )
        db.session.add(existing)
        db.session.commit()

        csv_content = (
            "title,author,category,isbn,copies\n"
            "New Book Alpha,Author Alpha,Science,978-0000000002,3\n"
            "Conflict Book,Conflict Author,Programming,978-0000000001,5\n" # Duplicate of existing
            "New Book Beta,Author Beta,Science,978-0000000003,4\n"
        ).encode('utf-8')

        mapping = {
            'title': 'title',
            'author': 'author',
            'category': 'category',
            'isbn': 'isbn',
            'copies': 'total_copies'
        }

        data = {
            'file': (io.BytesIO(csv_content), 'import_test.csv'),
            'target_entity': 'books',
            'duplicate_strategy': 'skip',
            'column_mapping': json.dumps(mapping)
        }

        response = auth_client.post('/uploads/import-execute', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = response.get_json()
        assert result['status'] == 'success'
        summary = result['summary']
        assert summary['total_rows'] == 3
        assert summary['successful_imports'] == 2
        assert summary['skipped_duplicates'] == 1

        # Check database records
        assert Book.query.filter_by(isbn="978-0000000002").first() is not None
        assert Book.query.filter_by(isbn="978-0000000003").first() is not None
        assert ImportLog.query.count() >= 1

def test_execute_import_books_abort_strategy_rollback(app, auth_client):
    """
    Verify duplicate_strategy='abort' safely rolls back the entire batch
    when a collision is detected, preserving database integrity.
    """
    with app.app_context():
        # Pre-existing book
        db.session.add(Book(
            title="Base Book",
            author="Base Author",
            category="History",
            isbn="978-1111111111",
            total_copies=1,
            available_copies=1
        ))
        db.session.commit()
        initial_book_count = Book.query.count()

        # Batch contains one new book and one colliding book
        csv_content = (
            "title,author,category,isbn\n"
            "Fresh Book,Fresh Author,Literature,978-2222222222\n"
            "Colliding Book,Colliding Author,History,978-1111111111\n"
        ).encode('utf-8')

        mapping = {'title': 'title', 'author': 'author', 'category': 'category', 'isbn': 'isbn'}

        data = {
            'file': (io.BytesIO(csv_content), 'abort_batch.csv'),
            'target_entity': 'books',
            'duplicate_strategy': 'abort',
            'column_mapping': json.dumps(mapping)
        }

        response = auth_client.post('/uploads/import-execute', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        summary = response.get_json()['summary']
        assert summary['status'] == 'failed'
        assert summary['successful_imports'] == 0

        # Verify transaction rollback: Fresh Book must NOT be in database
        assert Book.query.filter_by(isbn="978-2222222222").first() is None
        assert Book.query.count() == initial_book_count

def test_import_members_flow(app, auth_client):
    """Verify importing members directory records with student ID and email validation."""
    with app.app_context():
        csv_data = (
            "full_name,email,student_staff_id,department\n"
            "Alex Mercer,alex.mercer@apex.edu,STU-5001,Biotechnology\n"
            "Dana Scully,dana.scully@apex.edu,STU-5002,Forensics\n"
        ).encode('utf-8')

        mapping = {
            'full_name': 'full_name',
            'email': 'email',
            'student_staff_id': 'student_staff_id',
            'department': 'department'
        }

        data = {
            'file': (io.BytesIO(csv_data), 'members.csv'),
            'target_entity': 'members',
            'duplicate_strategy': 'skip',
            'column_mapping': json.dumps(mapping)
        }

        res = auth_client.post('/uploads/import-execute', data=data, content_type='multipart/form-data')
        assert res.status_code == 200
        summary = res.get_json()['summary']
        assert summary['successful_imports'] == 2
        assert Member.query.filter_by(student_staff_id='STU-5001').first() is not None

def test_document_upload_and_download(app, auth_client):
    """
    Verify PDF document upload, metadata persistence in Document model,
    and secure authenticated download with proper headers.
    """
    with app.app_context():
        # Valid PDF header + dummy body
        pdf_bytes = b"%PDF-1.4\n%Smart Library Academic Document Test Payload\n%%EOF"

        data = {
            'file': (io.BytesIO(pdf_bytes), 'Campus_Library_Policy_2026.pdf'),
            'title': 'Campus Library Policy 2026',
            'file_category': 'Policy',
            'description': 'Official institutional borrowing rules'
        }

        upload_res = auth_client.post('/uploads/document', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert upload_res.status_code == 200

        # Query Document from database
        doc = Document.query.filter_by(title='Campus Library Policy 2026').first()
        assert doc is not None
        assert doc.file_type == 'pdf'
        assert doc.file_category == 'Policy'
        assert doc.file_size == len(pdf_bytes)

        # Download Document
        download_res = auth_client.get(f'/uploads/documents/{doc.id}/download')
        assert download_res.status_code == 200
        assert download_res.headers['Content-Disposition'].startswith('attachment')
        assert 'Campus_Library_Policy_2026.pdf' in download_res.headers['Content-Disposition']
        assert download_res.data == pdf_bytes

def test_document_deletion_permissions(app, auth_client, librarian_user):
    """Verify document deletion permissions: creator or admin can delete."""
    with app.app_context():
        # Create document uploaded by admin
        admin_doc = Document(
            title="Admin Policy Document",
            original_filename="policy.pdf",
            stored_filename="policy_1234.pdf",
            file_type="pdf",
            file_size=100,
            file_category="Policy",
            storage_backend="local",
            storage_key="test_path.pdf"
        )
        db.session.add(admin_doc)
        db.session.commit()
        doc_id = admin_doc.id

        # Delete as authenticated admin
        del_res = auth_client.post(f'/uploads/documents/{doc_id}/delete', follow_redirects=True)
        assert del_res.status_code == 200
        assert Document.query.get(doc_id) is None
