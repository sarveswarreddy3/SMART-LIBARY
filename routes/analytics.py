from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from extensions import db
from models.book import Book
from models.setting import Setting
from services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('')
@login_required
def index():
    # Query parameters for initial load
    months = request.args.get('months', 6, type=int)
    category_filter = request.args.get('category', 'all').strip()

    kpis = AnalyticsService.get_dashboard_kpis()
    trends = AnalyticsService.get_monthly_circulation_trends(months=months, category_filter=category_filter)
    categories = AnalyticsService.get_category_distribution()
    top_books = AnalyticsService.get_most_borrowed_books(limit=8)
    top_members = AnalyticsService.get_top_borrowing_members(limit=8)
    departments = AnalyticsService.get_department_distribution()
    overdue_stats = AnalyticsService.get_overdue_breakdown()

    all_categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all()]
    currency = Setting.get_value('currency_symbol', '$')

    return render_template(
        'analytics/index.html',
        kpis=kpis,
        trends=trends,
        categories=categories,
        top_books=top_books,
        top_members=top_members,
        departments=departments,
        overdue_stats=overdue_stats,
        all_categories=all_categories,
        selected_months=months,
        selected_category=category_filter,
        currency=currency
    )

@analytics_bp.route('/api/circulation-trends')
@login_required
def api_circulation_trends():
    """AJAX endpoint for interactive chart filtering without page reload."""
    months = request.args.get('months', 6, type=int)
    category = request.args.get('category', 'all').strip()
    data = AnalyticsService.get_monthly_circulation_trends(months=months, category_filter=category)
    return jsonify(data)
