from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import func
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting

class AnalyticsService:
    """Analytics and data processing service utilizing Pandas and NumPy over database records."""

    @classmethod
    def get_dashboard_kpis(cls):
        """Calculate high-level KPI cards for the main admin dashboard."""
        today = date.today()

        total_titles = db.session.query(func.count(Book.id)).scalar() or 0
        total_copies = db.session.query(func.sum(Book.total_copies)).scalar() or 0
        available_copies = db.session.query(func.sum(Book.available_copies)).scalar() or 0
        issued_copies = max(0, total_copies - available_copies)

        total_members = db.session.query(func.count(Member.id)).scalar() or 0
        active_loans = Loan.query.filter_by(status='issued').count()
        overdue_loans = Loan.query.filter(Loan.status == 'issued', Loan.due_date < today).count()

        fines_collected = db.session.query(func.sum(Loan.fine_amount)).filter(Loan.fine_paid == True).scalar() or 0.0

        fine_rate = Setting.get_float('fine_rate_per_day', 1.0)
        # Calculate pending fines on current overdue loans
        pending_fines = 0.0
        overdue_active_loans = Loan.query.filter(Loan.status == 'issued', Loan.due_date < today).all()
        for loan in overdue_active_loans:
            pending_fines += loan.calculate_projected_fine(fine_rate)

        utilization_rate = round((issued_copies / total_copies * 100), 1) if total_copies > 0 else 0.0

        return {
            'total_titles': total_titles,
            'total_copies': total_copies,
            'available_copies': available_copies,
            'issued_copies': issued_copies,
            'total_members': total_members,
            'active_loans': active_loans,
            'overdue_loans': overdue_loans,
            'fines_collected': round(fines_collected, 2),
            'pending_fines': round(pending_fines, 2),
            'utilization_rate': utilization_rate
        }

    @classmethod
    def get_monthly_circulation_trends(cls, months=6, category_filter=None):
        """
        Generate monthly borrowing and return counts using Pandas.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 31)

        query = db.session.query(
            Loan.id,
            Loan.issue_date,
            Loan.return_date,
            Loan.status,
            Book.category
        ).join(Book, Loan.book_id == Book.id).filter(Loan.issue_date >= start_date)

        if category_filter and category_filter != 'all':
            query = query.filter(Book.category == category_filter)

        loans_data = query.all()

        if not loans_data:
            # Return empty skeleton with chronological month labels
            date_range = pd.date_range(end=pd.Timestamp.now(), periods=months, freq='ME')
            labels = [d.strftime('%b %Y') for d in date_range]
            return {
                'labels': labels,
                'borrowed': [0] * len(labels),
                'returned': [0] * len(labels)
            }

        df = pd.DataFrame([{
            'id': row[0],
            'issue_date': pd.to_datetime(row[1]),
            'return_date': pd.to_datetime(row[2]) if row[2] else None,
            'status': row[3],
            'category': row[4]
        } for row in loans_data])

        # Generate continuous monthly periods
        date_range = pd.date_range(end=pd.Timestamp.now(), periods=months, freq='ME')
        month_labels = [d.strftime('%b %Y') for d in date_range]
        month_keys = [d.strftime('%Y-%m') for d in date_range]

        df['issue_month'] = df['issue_date'].dt.strftime('%Y-%m')
        borrow_counts = df.groupby('issue_month').size().to_dict()

        df_returned = df.dropna(subset=['return_date']).copy()
        if not df_returned.empty:
            df_returned['return_month'] = df_returned['return_date'].dt.strftime('%Y-%m')
            return_counts = df_returned.groupby('return_month').size().to_dict()
        else:
            return_counts = {}

        borrowed_series = [int(borrow_counts.get(m, 0)) for m in month_keys]
        returned_series = [int(return_counts.get(m, 0)) for m in month_keys]

        return {
            'labels': month_labels,
            'borrowed': borrowed_series,
            'returned': returned_series
        }

    @classmethod
    def get_category_distribution(cls):
        """Return category distribution for books inventory and loans."""
        books = Book.query.all()
        if not books:
            return {'labels': [], 'book_counts': [], 'copy_counts': []}

        df_books = pd.DataFrame([{
            'category': b.category,
            'total_copies': b.total_copies,
            'available_copies': b.available_copies
        } for b in books])

        cat_summary = df_books.groupby('category').agg({
            'category': 'count',
            'total_copies': 'sum'
        }).rename(columns={'category': 'title_count'}).sort_values(by='total_copies', ascending=False)

        labels = cat_summary.index.tolist()
        title_counts = [int(x) for x in cat_summary['title_count'].values]
        copy_counts = [int(x) for x in cat_summary['total_copies'].values]

        return {
            'labels': labels,
            'title_counts': title_counts,
            'copy_counts': copy_counts
        }

    @classmethod
    def get_most_borrowed_books(cls, limit=8):
        """Top borrowed books using frequency aggregation."""
        query = db.session.query(
            Book.title,
            Book.author,
            Book.category,
            func.count(Loan.id).label('borrow_count')
        ).join(Loan, Book.id == Loan.book_id).group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(limit)

        results = query.all()
        if not results:
            return {'titles': [], 'counts': [], 'categories': []}

        return {
            'titles': [r[0][:28] + ('...' if len(r[0]) > 28 else '') for r in results],
            'full_titles': [r[0] for r in results],
            'authors': [r[1] for r in results],
            'categories': [r[2] for r in results],
            'counts': [int(r[3]) for r in results]
        }

    @classmethod
    def get_top_borrowing_members(cls, limit=8):
        """Top active members by circulation volume."""
        query = db.session.query(
            Member.full_name,
            Member.department,
            func.count(Loan.id).label('loan_count')
        ).join(Loan, Member.id == Loan.member_id).group_by(Member.id).order_by(func.count(Loan.id).desc()).limit(limit)

        results = query.all()
        if not results:
            return {'names': [], 'counts': [], 'departments': []}

        return {
            'names': [r[0] for r in results],
            'departments': [r[1] for r in results],
            'counts': [int(r[2]) for r in results]
        }

    @classmethod
    def get_department_distribution(cls):
        """Distribution of loans grouped by member department."""
        query = db.session.query(
            Member.department,
            func.count(Loan.id).label('borrow_count')
        ).join(Loan, Member.id == Loan.member_id).group_by(Member.department).order_by(func.count(Loan.id).desc())

        results = query.all()
        if not results:
            return {'departments': [], 'counts': []}

        return {
            'departments': [r[0] for r in results],
            'counts': [int(r[1]) for r in results]
        }

    @classmethod
    def get_overdue_breakdown(cls):
        """Detailed overdue metrics and duration brackets using NumPy."""
        today = date.today()
        fine_rate = Setting.get_float('fine_rate_per_day', 1.0)

        overdue_loans = Loan.query.filter(Loan.status == 'issued', Loan.due_date < today).all()
        if not overdue_loans:
            return {
                'total_overdue': 0,
                'total_projected_fines': 0.0,
                'brackets': {'1-7 Days': 0, '8-14 Days': 0, '15-30 Days': 0, '30+ Days': 0},
                'items': []
            }

        days_list = [loan.overdue_days for loan in overdue_loans]
        fines_list = [loan.calculate_projected_fine(fine_rate) for loan in overdue_loans]

        # Use NumPy to categorize into duration brackets
        days_arr = np.array(days_list)
        b1 = int(np.sum((days_arr >= 1) & (days_arr <= 7)))
        b2 = int(np.sum((days_arr >= 8) & (days_arr <= 14)))
        b3 = int(np.sum((days_arr >= 15) & (days_arr <= 30)))
        b4 = int(np.sum(days_arr > 30))

        items = [{
            'transaction_id': l.transaction_id,
            'book_title': l.book.title,
            'member_name': l.member.full_name,
            'member_id': l.member.member_id,
            'department': l.member.department,
            'email': l.member.email,
            'phone': l.member.phone,
            'due_date': l.due_date.strftime('%Y-%m-%d'),
            'overdue_days': l.overdue_days,
            'fine': l.calculate_projected_fine(fine_rate)
        } for l in overdue_loans]

        # Sort by most overdue first
        items.sort(key=lambda x: x['overdue_days'], reverse=True)

        return {
            'total_overdue': len(overdue_loans),
            'total_projected_fines': round(float(np.sum(fines_list)), 2),
            'brackets': {
                '1-7 Days': b1,
                '8-14 Days': b2,
                '15-30 Days': b3,
                '30+ Days': b4
            },
            'items': items
        }
