from datetime import datetime, timezone
from extensions import db

class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(32), unique=True, nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    publisher = db.Column(db.String(255), nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    shelf_location = db.Column(db.String(64), nullable=True)
    total_copies = db.Column(db.Integer, default=1, nullable=False)
    available_copies = db.Column(db.Integer, default=1, nullable=False)
    cover_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships: do not cascade delete to protect historical audit trails
    loans = db.relationship('Loan', back_populates='book', lazy='select')

    @property
    def issued_copies(self):
        return max(0, self.total_copies - self.available_copies)

    @property
    def is_available(self):
        return self.available_copies > 0

    @property
    def active_loans_count(self):
        return sum(1 for loan in self.loans if loan.status == 'issued')

    def can_be_deleted(self):
        """Check if book can be safely removed without breaking active loans or transaction records."""
        if self.active_loans_count > 0:
            return False, f"Cannot delete book: {self.active_loans_count} copy/copies are currently issued."
        if len(self.loans) > 0:
            return False, f"Cannot delete book: Book has {len(self.loans)} historical loan record(s). Deleting it would break historical integrity."
        return True, "Safe to delete."

    def to_dict(self):
        return {
            'id': self.id,
            'isbn': self.isbn or 'N/A',
            'title': self.title,
            'author': self.author,
            'category': self.category,
            'publisher': self.publisher or '',
            'publication_year': self.publication_year,
            'description': self.description or '',
            'shelf_location': self.shelf_location or 'General Stack',
            'total_copies': self.total_copies,
            'available_copies': self.available_copies,
            'issued_copies': self.issued_copies,
            'is_available': self.is_available,
            'cover_image': self.cover_image or 'default-cover.svg',
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }

    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'
