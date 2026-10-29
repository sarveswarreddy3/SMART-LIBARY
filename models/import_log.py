import json
from datetime import datetime, timezone
from extensions import db

class ImportLog(db.Model):
    """
    Tracks tabular data imports (CSV/Excel) for books, members, and transactions.
    Records success counts, duplicate skips, row errors, and operator audit trail.
    """
    __tablename__ = 'import_logs'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    target_entity = db.Column(db.String(50), nullable=False, index=True)  # 'books', 'members', 'transactions'
    total_rows = db.Column(db.Integer, default=0, nullable=False)
    successful_imports = db.Column(db.Integer, default=0, nullable=False)
    skipped_duplicates = db.Column(db.Integer, default=0, nullable=False)
    failed_rows = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='completed', nullable=False, index=True)  # 'completed', 'partial', 'failed'
    summary_json = db.Column(db.Text, nullable=True)  # JSON-encoded array of row errors/details
    
    imported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    imported_by = db.relationship('User', foreign_keys=[imported_by_id])

    @property
    def error_details(self):
        """Parse summary_json into structured list of error objects."""
        if not self.summary_json:
            return []
        try:
            return json.loads(self.summary_json)
        except Exception:
            return []

    @property
    def status_badge_class(self):
        if self.status == 'completed' and self.failed_rows == 0:
            return 'bg-success-subtle text-success border border-success-subtle'
        elif self.status == 'failed' or self.successful_imports == 0:
            return 'bg-danger-subtle text-danger border border-danger-subtle'
        return 'bg-warning-subtle text-warning border border-warning-subtle'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'target_entity': self.target_entity,
            'total_rows': self.total_rows,
            'successful_imports': self.successful_imports,
            'skipped_duplicates': self.skipped_duplicates,
            'failed_rows': self.failed_rows,
            'status': self.status,
            'imported_by': self.imported_by.full_name if self.imported_by else 'System',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'errors': self.error_details
        }
