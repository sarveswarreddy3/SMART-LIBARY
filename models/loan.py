from datetime import datetime, date, timezone
from extensions import db

class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False, index=True)
    issued_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    returned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    issue_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    return_date = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(20), default='issued', nullable=False, index=True)  # 'issued', 'returned', 'overdue'
    
    fine_amount = db.Column(db.Float, default=0.0, nullable=False)
    fine_paid = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    book = db.relationship('Book', back_populates='loans')
    member = db.relationship('Member', back_populates='loans')
    issued_by = db.relationship('User', foreign_keys=[issued_by_id])
    returned_by = db.relationship('User', foreign_keys=[returned_by_id])

    @property
    def is_overdue(self):
        """Check if loan is currently overdue."""
        if self.status == 'returned':
            return False
        return date.today() > self.due_date

    @property
    def overdue_days(self):
        """Calculate number of days overdue."""
        if self.status == 'returned':
            if self.return_date and self.return_date > self.due_date:
                return (self.return_date - self.due_date).days
            return 0
        if date.today() > self.due_date:
            return (date.today() - self.due_date).days
        return 0

    @property
    def effective_status(self):
        """Return dynamic status reflecting current date if issued and past due date."""
        if self.status == 'returned':
            return 'returned'
        if self.is_overdue:
            return 'overdue'
        return 'issued'

    def calculate_projected_fine(self, fine_rate_per_day):
        """Calculate fine based on current overdue days and given rate."""
        days = self.overdue_days
        return round(days * fine_rate_per_day, 2) if days > 0 else 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else 'Unknown',
            'book_isbn': self.book.isbn if self.book else 'N/A',
            'member_id': self.member_id,
            'member_code': self.member.member_id if self.member else 'Unknown',
            'member_name': self.member.full_name if self.member else 'Unknown',
            'issue_date': self.issue_date.strftime('%Y-%m-%d') if self.issue_date else None,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'return_date': self.return_date.strftime('%Y-%m-%d') if self.return_date else None,
            'status': self.effective_status,
            'overdue_days': self.overdue_days,
            'fine_amount': self.fine_amount,
            'fine_paid': self.fine_paid,
            'notes': self.notes or ''
        }

    def __repr__(self):
        return f'<Loan {self.transaction_id}: Book {self.book_id} -> Member {self.member_id} ({self.status})>'
