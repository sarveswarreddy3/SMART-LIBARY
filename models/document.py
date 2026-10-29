import os
from datetime import datetime, timezone
from extensions import db

class Document(db.Model):
    """
    Document model for storing uploaded PDF, Word, and reference library files.
    Supports local filesystem, S3 cloud object storage, and database BLOB fallback.
    """
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    file_type = db.Column(db.String(20), nullable=False, index=True)  # pdf, docx, doc, xlsx, xls, csv
    mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=False)  # size in bytes
    file_category = db.Column(db.String(50), default='General', nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Storage abstraction: 'local', 's3', 'database'
    storage_backend = db.Column(db.String(20), default='local', nullable=False)
    storage_key = db.Column(db.String(500), nullable=True)
    file_blob = db.Column(db.LargeBinary, nullable=True)
    
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])

    @property
    def file_size_formatted(self):
        """Format byte size into human-readable string (KB, MB)."""
        bytes_val = self.file_size
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.2f} MB"

    @property
    def file_icon(self):
        """Return corresponding Bootstrap Icon for document type."""
        ext = self.file_type.lower()
        if ext == 'pdf':
            return 'bi-file-earmark-pdf-fill text-danger'
        elif ext in ('docx', 'doc'):
            return 'bi-file-earmark-word-fill text-primary'
        elif ext in ('xlsx', 'xls', 'csv'):
            return 'bi-file-earmark-excel-fill text-success'
        return 'bi-file-earmark-text-fill text-secondary'

    @property
    def category_badge_class(self):
        """Color styling for document category."""
        mapping = {
            'Policy': 'bg-primary-subtle text-primary border border-primary-subtle',
            'Guide': 'bg-info-subtle text-info border border-info-subtle',
            'Report': 'bg-success-subtle text-success border border-success-subtle',
            'Academic': 'bg-warning-subtle text-warning border border-warning-subtle',
            'Catalog': 'bg-secondary-subtle text-secondary border border-secondary-subtle',
            'General': 'bg-light text-dark border'
        }
        return mapping.get(self.file_category, 'bg-light text-dark border')

    def can_delete(self, user):
        """Permissions check: Admins can delete any file; users can delete their own."""
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        return self.uploaded_by_id == user.id

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_size_formatted': self.file_size_formatted,
            'file_category': self.file_category,
            'description': self.description,
            'storage_backend': self.storage_backend,
            'uploaded_by': self.uploaded_by.full_name if self.uploaded_by else 'System',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }
