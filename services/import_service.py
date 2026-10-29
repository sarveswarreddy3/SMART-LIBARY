import io
import csv
import json
import uuid
from datetime import datetime, date, timezone
import pandas as pd
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.user import User
from models.import_log import ImportLog
from services.file_validator import validate_uploaded_file, TABULAR_EXTENSIONS, FileValidationError

# Field definitions for entity mapping and validation
ENTITY_FIELDS = {
    'books': [
        {'name': 'title', 'label': 'Book Title', 'required': True, 'aliases': ['title', 'book_title', 'book title', 'name']},
        {'name': 'author', 'label': 'Author', 'required': True, 'aliases': ['author', 'author_name', 'author name', 'writer']},
        {'name': 'category', 'label': 'Category / Genre', 'required': True, 'aliases': ['category', 'genre', 'subject', 'department']},
        {'name': 'isbn', 'label': 'ISBN', 'required': False, 'aliases': ['isbn', 'isbn_13', 'isbn-13', 'isbn13', 'isbn10']},
        {'name': 'publisher', 'label': 'Publisher', 'required': False, 'aliases': ['publisher', 'publishing_house']},
        {'name': 'publication_year', 'label': 'Publication Year', 'required': False, 'aliases': ['publication_year', 'year', 'pub_year', 'published_year']},
        {'name': 'description', 'label': 'Description', 'required': False, 'aliases': ['description', 'summary', 'synopsis']},
        {'name': 'shelf_location', 'label': 'Shelf / Location', 'required': False, 'aliases': ['shelf_location', 'shelf', 'location', 'rack']},
        {'name': 'total_copies', 'label': 'Total Copies', 'required': False, 'aliases': ['total_copies', 'copies', 'total copies', 'quantity', 'qty']},
        {'name': 'available_copies', 'label': 'Available Copies', 'required': False, 'aliases': ['available_copies', 'available', 'available copies']}
    ],
    'members': [
        {'name': 'full_name', 'label': 'Full Name', 'required': True, 'aliases': ['full_name', 'name', 'member_name', 'student_name']},
        {'name': 'email', 'label': 'Email Address', 'required': True, 'aliases': ['email', 'email_address', 'mail']},
        {'name': 'student_staff_id', 'label': 'Student/Staff ID', 'required': True, 'aliases': ['student_staff_id', 'student_id', 'staff_id', 'roll_no', 'id_number']},
        {'name': 'department', 'label': 'Department', 'required': True, 'aliases': ['department', 'dept', 'branch', 'faculty']},
        {'name': 'phone', 'label': 'Phone Number', 'required': False, 'aliases': ['phone', 'phone_number', 'mobile', 'contact']},
        {'name': 'member_id', 'label': 'Member Code', 'required': False, 'aliases': ['member_id', 'member_code', 'membership_id']},
        {'name': 'membership_date', 'label': 'Membership Date', 'required': False, 'aliases': ['membership_date', 'joined_date', 'join_date', 'date']},
        {'name': 'status', 'label': 'Membership Status', 'required': False, 'aliases': ['status', 'state', 'membership_status']}
    ],
    'transactions': [
        {'name': 'book_identifier', 'label': 'Book ISBN or Title', 'required': True, 'aliases': ['book_identifier', 'isbn', 'book_isbn', 'book_title', 'book']},
        {'name': 'member_identifier', 'label': 'Member ID or Email', 'required': True, 'aliases': ['member_identifier', 'member_id', 'student_id', 'email', 'member']},
        {'name': 'issue_date', 'label': 'Issue Date', 'required': True, 'aliases': ['issue_date', 'issued_date', 'loan_date', 'date_issued']},
        {'name': 'due_date', 'label': 'Due Date', 'required': True, 'aliases': ['due_date', 'return_due', 'expected_return']},
        {'name': 'return_date', 'label': 'Return Date (Optional)', 'required': False, 'aliases': ['return_date', 'returned_date', 'actual_return']},
        {'name': 'status', 'label': 'Status', 'required': False, 'aliases': ['status', 'loan_status']},
        {'name': 'fine_amount', 'label': 'Fine Amount', 'required': False, 'aliases': ['fine_amount', 'fine', 'penalty']},
        {'name': 'notes', 'label': 'Notes / Remarks', 'required': False, 'aliases': ['notes', 'remarks', 'comment']}
    ]
}

class ImportService:
    """
    Handles CSV and Excel data extraction, column auto-mapping, schema validation,
    duplicate collision detection, and transactional atomic batch insertion.
    """

    @classmethod
    def get_template_csv(cls, target_entity: str) -> str:
        """Generate sample CSV template headers and example rows for download."""
        fields = ENTITY_FIELDS.get(target_entity, [])
        if not fields:
            raise ValueError(f"Unknown entity '{target_entity}'")

        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [f['name'] for f in fields]
        writer.writerow(headers)

        # Write sample row
        if target_entity == 'books':
            writer.writerow([
                'Designing Distributed Systems', 'Brendan Burns', 'Cloud Computing',
                '978-1491983645', "O'Reilly Media", '2018',
                'Patterns and Paradigms for Scalable Microservices', 'Rack D-12', '5', '5'
            ])
        elif target_entity == 'members':
            writer.writerow([
                'Sarah Connor', 'sconnor@university.edu', 'STU-9921',
                'Computer Science', '+1-555-0199', 'MEM-2026-0042', '2026-01-15', 'Active'
            ])
        elif target_entity == 'transactions':
            writer.writerow([
                '978-0132350884', 'MEM-2026-0042', '2026-03-01',
                '2026-03-15', '', 'issued', '0.0', 'Standard 14-day checkout'
            ])

        return output.getvalue()

    @classmethod
    def read_dataframe(cls, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parse raw file bytes into pandas DataFrame supporting CSV, XLSX, and XLS."""
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        buffer = io.BytesIO(file_bytes)

        if ext == 'csv':
            try:
                df = pd.read_csv(buffer, dtype=str, skipinitialspace=True)
            except UnicodeDecodeError:
                buffer.seek(0)
                df = pd.read_csv(buffer, dtype=str, encoding='latin-1', skipinitialspace=True)
        elif ext in ('xlsx', 'xls'):
            df = pd.read_excel(buffer, dtype=str, engine='openpyxl' if ext == 'xlsx' else None)
        else:
            raise FileValidationError(f"Unsupported tabular file format '.{ext}'")

        # Strip whitespace from column names and string cells
        df.columns = [str(c).strip() for c in df.columns]
        df = df.map(lambda x: str(x).strip() if pd.notna(x) else '')
        # Drop rows where all columns are empty
        df = df.dropna(how='all')
        df = df[df.apply(lambda row: any(str(v).strip() != '' for v in row), axis=1)]
        return df

    @classmethod
    def preview_file(cls, file_storage, target_entity: str) -> dict:
        """
        Extract preview metadata, table headers, and suggest best column mappings.
        """
        if target_entity not in ENTITY_FIELDS:
            raise FileValidationError(f"Invalid target entity '{target_entity}'. Must be books, members, or transactions.")

        validate_uploaded_file(file_storage, allowed_extensions=TABULAR_EXTENSIONS)
        
        file_storage.stream.seek(0)
        file_bytes = file_storage.read()
        file_storage.stream.seek(0)

        df = cls.read_dataframe(file_bytes, file_storage.filename)
        headers = list(df.columns)
        total_rows = len(df)

        if total_rows == 0:
            raise FileValidationError("The uploaded tabular file contains no data rows.")

        sample_rows = df.head(5).to_dict(orient='records')
        available_fields = ENTITY_FIELDS[target_entity]

        # Auto-match headers to entity fields
        suggested_mappings = {}
        for header in headers:
            normalized_header = header.lower().replace('-', '_').replace(' ', '_')
            matched_field = None
            for field in available_fields:
                if normalized_header == field['name'] or normalized_header in [a.lower() for a in field['aliases']]:
                    matched_field = field['name']
                    break
            suggested_mappings[header] = matched_field or ''

        return {
            'filename': file_storage.filename,
            'target_entity': target_entity,
            'headers': headers,
            'total_rows': total_rows,
            'sample_rows': sample_rows,
            'suggested_mappings': suggested_mappings,
            'available_fields': available_fields
        }

    @classmethod
    def execute_import(cls, file_bytes: bytes, filename: str, target_entity: str,
                       column_mapping: dict, duplicate_strategy: str = 'skip', user=None) -> ImportLog:
        """
        Execute atomic database import with row-level validation, duplicate collision check,
        and full transaction rollback safety.
        """
        if target_entity not in ENTITY_FIELDS:
            raise ValueError(f"Invalid target entity '{target_entity}'")

        df = cls.read_dataframe(file_bytes, filename)
        total_rows = len(df)

        # Invert column_mapping: field_name -> dataframe column name
        field_to_col = {}
        for col_name, field_name in column_mapping.items():
            if field_name:
                field_to_col[field_name] = col_name

        # Verify all required entity fields are mapped
        entity_defs = {f['name']: f for f in ENTITY_FIELDS[target_entity]}
        missing_required = []
        for f in ENTITY_FIELDS[target_entity]:
            if f['required'] and f['name'] not in field_to_col:
                missing_required.append(f['label'])

        if missing_required:
            raise FileValidationError(f"Missing required field mappings: {', '.join(missing_required)}")

        successful_count = 0
        skipped_count = 0
        failed_count = 0
        row_errors = []

        # Track batch-level unique values to prevent intra-batch duplicates
        batch_isbns = set()
        batch_member_ids = set()
        batch_staff_ids = set()
        batch_emails = set()

        # Execute inside nested database transaction
        savepoint = db.session.begin_nested()
        try:
            for idx, (_, row) in enumerate(df.iterrows(), start=1):
                row_data = {}
                for field_name, col_name in field_to_col.items():
                    val = row.get(col_name, '')
                    row_data[field_name] = str(val).strip() if pd.notna(val) else ''

                # Check required fields for non-emptiness
                row_missing = [f_name for f_name, f_def in entity_defs.items() if f_def['required'] and not row_data.get(f_name)]
                if row_missing:
                    failed_count += 1
                    labels = [entity_defs[m]['label'] for m in row_missing]
                    row_errors.append({
                        'row': idx,
                        'status': 'error',
                        'message': f"Required field(s) empty: {', '.join(labels)}"
                    })
                    if duplicate_strategy == 'abort':
                        raise ValueError(f"Row {idx}: Missing required fields {', '.join(labels)}")
                    continue

                # Entity-specific validation and instantiation
                if target_entity == 'books':
                    isbn = row_data.get('isbn')
                    if isbn:
                        # Check duplicate in database
                        existing_book = Book.query.filter_by(isbn=isbn).first()
                        if existing_book or isbn in batch_isbns:
                            if duplicate_strategy == 'abort':
                                raise ValueError(f"Row {idx}: Duplicate ISBN '{isbn}' detected in database or file batch.")
                            skipped_count += 1
                            row_errors.append({
                                'row': idx,
                                'status': 'skipped',
                                'message': f"Skipped duplicate ISBN '{isbn}' ({row_data.get('title')})"
                            })
                            continue
                        batch_isbns.add(isbn)

                    # Validate copies
                    try:
                        total_copies = int(row_data.get('total_copies') or 1)
                        if total_copies < 1:
                            total_copies = 1
                    except ValueError:
                        total_copies = 1

                    try:
                        avail_copies = int(row_data.get('available_copies') or total_copies)
                        if avail_copies > total_copies:
                            avail_copies = total_copies
                    except ValueError:
                        avail_copies = total_copies

                    pub_year = None
                    if row_data.get('publication_year'):
                        try:
                            pub_year = int(row_data['publication_year'])
                        except ValueError:
                            pass

                    new_book = Book(
                        title=row_data['title'],
                        author=row_data['author'],
                        category=row_data['category'],
                        isbn=isbn or None,
                        publisher=row_data.get('publisher') or None,
                        publication_year=pub_year,
                        description=row_data.get('description') or None,
                        shelf_location=row_data.get('shelf_location') or 'General Stacks',
                        total_copies=total_copies,
                        available_copies=avail_copies
                    )
                    db.session.add(new_book)
                    successful_count += 1

                elif target_entity == 'members':
                    staff_id = row_data['student_staff_id']
                    email = row_data['email'].lower()

                    # Check duplicate staff ID or email
                    existing_staff = Member.query.filter_by(student_staff_id=staff_id).first()
                    existing_email = Member.query.filter_by(email=email).first()

                    if existing_staff or existing_email or staff_id in batch_staff_ids or email in batch_emails:
                        conflict_field = "Student/Staff ID" if (existing_staff or staff_id in batch_staff_ids) else "Email"
                        conflict_val = staff_id if conflict_field == "Student/Staff ID" else email
                        if duplicate_strategy == 'abort':
                            raise ValueError(f"Row {idx}: Duplicate {conflict_field} '{conflict_val}' detected.")
                        skipped_count += 1
                        row_errors.append({
                            'row': idx,
                            'status': 'skipped',
                            'message': f"Skipped duplicate {conflict_field} '{conflict_val}' for member '{row_data['full_name']}'"
                        })
                        continue

                    batch_staff_ids.add(staff_id)
                    batch_emails.add(email)

                    mem_id = row_data.get('member_id')
                    if not mem_id:
                        mem_id = f"MEM-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"

                    status = row_data.get('status', 'Active')
                    if status not in ('Active', 'Suspended', 'Expired'):
                        status = 'Active'

                    mem_date = date.today()
                    if row_data.get('membership_date'):
                        try:
                            mem_date = date.fromisoformat(row_data['membership_date'][:10])
                        except ValueError:
                            pass

                    new_member = Member(
                        member_id=mem_id,
                        student_staff_id=staff_id,
                        full_name=row_data['full_name'],
                        email=email,
                        phone=row_data.get('phone') or None,
                        department=row_data['department'],
                        membership_date=mem_date,
                        status=status
                    )
                    db.session.add(new_member)
                    successful_count += 1

                elif target_entity == 'transactions':
                    book_query = row_data['book_identifier']
                    book = Book.query.filter((Book.isbn == book_query) | (Book.title == book_query)).first()
                    if not book:
                        failed_count += 1
                        row_errors.append({
                            'row': idx,
                            'status': 'error',
                            'message': f"Book not found matching identifier '{book_query}'"
                        })
                        if duplicate_strategy == 'abort':
                            raise ValueError(f"Row {idx}: Book identifier '{book_query}' does not exist.")
                        continue

                    member_query = row_data['member_identifier']
                    member = Member.query.filter(
                        (Member.member_id == member_query) |
                        (Member.student_staff_id == member_query) |
                        (Member.email == member_query)
                    ).first()
                    if not member:
                        failed_count += 1
                        row_errors.append({
                            'row': idx,
                            'status': 'error',
                            'message': f"Member not found matching identifier '{member_query}'"
                        })
                        if duplicate_strategy == 'abort':
                            raise ValueError(f"Row {idx}: Member identifier '{member_query}' does not exist.")
                        continue

                    # Dates
                    try:
                        issue_dt = date.fromisoformat(row_data['issue_date'][:10])
                        due_dt = date.fromisoformat(row_data['due_date'][:10])
                    except Exception:
                        failed_count += 1
                        row_errors.append({
                            'row': idx,
                            'status': 'error',
                            'message': f"Invalid date format. Expected YYYY-MM-DD (got issue: {row_data.get('issue_date')}, due: {row_data.get('due_date')})"
                        })
                        if duplicate_strategy == 'abort':
                            raise ValueError(f"Row {idx}: Invalid date format.")
                        continue

                    ret_dt = None
                    if row_data.get('return_date'):
                        try:
                            ret_dt = date.fromisoformat(row_data['return_date'][:10])
                        except ValueError:
                            pass

                    status = row_data.get('status', 'issued').lower()
                    if status not in ('issued', 'returned', 'overdue'):
                        status = 'issued'

                    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

                    new_loan = Loan(
                        transaction_id=txn_id,
                        book_id=book.id,
                        member_id=member.id,
                        issue_date=issue_dt,
                        due_date=due_dt,
                        return_date=ret_dt,
                        status=status,
                        notes=row_data.get('notes') or None
                    )
                    db.session.add(new_loan)

                    # Update available copies if issued
                    if status == 'issued' and book.available_copies > 0:
                        book.available_copies -= 1

                    successful_count += 1

            # Commit nested transaction
            savepoint.commit()
            db.session.commit()

            import_status = 'completed' if failed_count == 0 else ('partial' if successful_count > 0 else 'failed')

        except Exception as e:
            savepoint.rollback()
            db.session.rollback()
            import_status = 'failed'
            failed_count = total_rows
            successful_count = 0
            row_errors.append({
                'row': 0,
                'status': 'error',
                'message': f"Batch transaction aborted and rolled back: {str(e)}"
            })

        # Save import log
        log_entry = ImportLog(
            filename=filename,
            target_entity=target_entity,
            total_rows=total_rows,
            successful_imports=successful_count,
            skipped_duplicates=skipped_count,
            failed_rows=failed_count,
            status=import_status,
            summary_json=json.dumps(row_errors[:100]),  # Store up to 100 row error entries
            imported_by_id=user.id if user and user.is_authenticated else None
        )
        db.session.add(log_entry)
        db.session.commit()

        return log_entry
