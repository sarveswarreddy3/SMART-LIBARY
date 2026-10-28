from datetime import datetime, date, timezone
from extensions import db

class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    student_staff_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=False, index=True)
    membership_date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(20), default='Active', nullable=False)  # 'Active', 'Suspended', 'Expired'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    loans = db.relationship('Loan', back_populates='member', lazy='select')

    @property
    def active_loans(self):
        return [loan for loan in self.loans if loan.status == 'issued']

    @property
    def active_loans_count(self):
        return len(self.active_loans)

    @property
    def overdue_loans(self):
        today = date.today()
        return [loan for loan in self.loans if loan.status == 'issued' and loan.due_date < today]

    @property
    def overdue_loans_count(self):
        return len(self.overdue_loans)

    @property
    def total_borrowed_count(self):
        return len(self.loans)

    def can_be_deleted(self):
        """Check if member can be safely removed without breaking transaction records."""
        if self.active_loans_count > 0:
            return False, f"Cannot delete member: Currently has {self.active_loans_count} active loan(s)."
        if len(self.loans) > 0:
            return False, f"Cannot delete member: Member has {len(self.loans)} historical loan record(s)."
        return True, "Safe to delete."

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'student_staff_id': self.student_staff_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone or 'N/A',
            'department': self.department,
            'membership_date': self.membership_date.strftime('%Y-%m-%d') if self.membership_date else None,
            'status': self.status,
            'active_loans_count': self.active_loans_count,
            'overdue_loans_count': self.overdue_loans_count,
            'total_borrowed_count': self.total_borrowed_count
        }

    def __repr__(self):
        return f'<Member {self.member_id} - {self.full_name}>'
