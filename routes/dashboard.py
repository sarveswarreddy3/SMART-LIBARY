from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from models.loan import Loan
from models.setting import Setting
from services.analytics_service import AnalyticsService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/dashboard')
@login_required
def index():
    kpis = AnalyticsService.get_dashboard_kpis()
    trends = AnalyticsService.get_monthly_circulation_trends(months=6)
    categories = AnalyticsService.get_category_distribution()
    top_books = AnalyticsService.get_most_borrowed_books(limit=5)
    
    # Recent 5 issued books
    recent_issued = Loan.query.filter_by(status='issued').order_by(Loan.created_at.desc()).limit(5).all()
    # Recent 5 returned books
    recent_returned = Loan.query.filter_by(status='returned').order_by(Loan.return_date.desc()).limit(5).all()

    currency = Setting.get_value('currency_symbol', '$')

    return render_template(
        'dashboard.html',
        kpis=kpis,
        trends=trends,
        categories=categories,
        top_books=top_books,
        recent_issued=recent_issued,
        recent_returned=recent_returned,
        currency=currency
    )
