from datetime import datetime, date
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required
from extensions import db
from models.book import Book
from services.report_service import ReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('')
@login_required
def index():
    categories = [c[0] for c in db.session.query(Book.category).distinct().order_by(Book.category).all()]
    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('reports/index.html', categories=categories, today=today_str)

@reports_bp.route('/export/<string:fmt>/<string:report_type>')
@login_required
def export(fmt, report_type):
    valid_types = {'books', 'members', 'issued_books', 'returned_books', 'overdue_books', 'transactions'}
    if report_type not in valid_types:
        flash("Invalid report type specified.", "danger")
        return redirect(url_for('reports.index'))

    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    category = request.args.get('category', '').strip()

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    title, headers, rows = ReportService.get_report_data(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        category=category
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    clean_type = report_type.replace('_', '-')

    if fmt == 'csv':
        buffer = ReportService.export_csv(headers, rows)
        filename = f"{clean_type}_{timestamp}.csv"
        return send_file(
            buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    elif fmt == 'excel':
        buffer = ReportService.export_excel(title, headers, rows)
        filename = f"{clean_type}_{timestamp}.xlsx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    elif fmt == 'pdf':
        buffer = ReportService.export_pdf(title, headers, rows)
        filename = f"{clean_type}_{timestamp}.pdf"
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    else:
        flash("Unsupported export format.", "warning")
        return redirect(url_for('reports.index'))
