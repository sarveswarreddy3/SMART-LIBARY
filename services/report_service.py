import io
from datetime import datetime, date
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from extensions import db
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting

class ReportService:
    """Service to export library data to CSV, Excel, and PDF formats."""

    @classmethod
    def get_report_data(cls, report_type, start_date=None, end_date=None, category=None):
        """Fetch records and columns based on report type and optional filters."""
        today = date.today()
        fine_rate = Setting.get_float('fine_rate_per_day', 1.0)
        
        if report_type == 'books':
            query = Book.query
            if category and category != 'all':
                query = query.filter_by(category=category)
            books = query.order_by(Book.title).all()
            
            headers = ["Book ID", "ISBN", "Title", "Author", "Category", "Shelf", "Total", "Available", "Issued"]
            rows = []
            for b in books:
                rows.append([
                    f"BK-{b.id:04d}",
                    b.isbn or "N/A",
                    b.title,
                    b.author,
                    b.category,
                    b.shelf_location or "General Stack",
                    b.total_copies,
                    b.available_copies,
                    b.issued_copies
                ])
            title = "Book Inventory Report"

        elif report_type == 'members':
            members = Member.query.order_by(Member.member_id).all()
            headers = ["Member ID", "Student/Staff ID", "Full Name", "Email", "Phone", "Department", "Status", "Active Loans"]
            rows = []
            for m in members:
                rows.append([
                    m.member_id,
                    m.student_staff_id,
                    m.full_name,
                    m.email,
                    m.phone or "N/A",
                    m.department,
                    m.status,
                    m.active_loans_count
                ])
            title = "Library Members Directory"

        elif report_type == 'issued_books':
            query = Loan.query.filter_by(status='issued')
            if start_date:
                query = query.filter(Loan.issue_date >= start_date)
            if end_date:
                query = query.filter(Loan.issue_date <= end_date)
            loans = query.order_by(Loan.due_date).all()
            
            headers = ["Txn ID", "Book Title", "Member Name", "Member ID", "Issue Date", "Due Date", "Days Rem./Overdue"]
            rows = []
            for l in loans:
                diff = (l.due_date - today).days
                diff_str = f"{abs(diff)}d overdue" if diff < 0 else f"{diff}d left"
                rows.append([
                    l.transaction_id,
                    l.book.title if l.book else "N/A",
                    l.member.full_name if l.member else "N/A",
                    l.member.member_id if l.member else "N/A",
                    l.issue_date.strftime('%Y-%m-%d'),
                    l.due_date.strftime('%Y-%m-%d'),
                    diff_str
                ])
            title = "Active Issued Books Report"

        elif report_type == 'returned_books':
            query = Loan.query.filter_by(status='returned')
            if start_date:
                query = query.filter(Loan.return_date >= start_date)
            if end_date:
                query = query.filter(Loan.return_date <= end_date)
            loans = query.order_by(Loan.return_date.desc()).all()
            
            headers = ["Txn ID", "Book Title", "Member Name", "Issue Date", "Return Date", "Fine ($)", "Fine Paid"]
            rows = []
            for l in loans:
                rows.append([
                    l.transaction_id,
                    l.book.title if l.book else "N/A",
                    l.member.full_name if l.member else "N/A",
                    l.issue_date.strftime('%Y-%m-%d'),
                    l.return_date.strftime('%Y-%m-%d') if l.return_date else "N/A",
                    f"${l.fine_amount:.2f}",
                    "Yes" if l.fine_paid else "No"
                ])
            title = "Returned Books History"

        elif report_type == 'overdue_books':
            query = Loan.query.filter(Loan.status == 'issued', Loan.due_date < today)
            loans = query.order_by(Loan.due_date).all()
            
            headers = ["Txn ID", "Book Title", "Member Name", "Department", "Contact", "Due Date", "Overdue (Days)", "Late Fine ($)"]
            rows = []
            for l in loans:
                rows.append([
                    l.transaction_id,
                    l.book.title if l.book else "N/A",
                    l.member.full_name if l.member else "N/A",
                    l.member.department if l.member else "N/A",
                    l.member.phone or l.member.email,
                    l.due_date.strftime('%Y-%m-%d'),
                    l.overdue_days,
                    f"${l.calculate_projected_fine(fine_rate):.2f}"
                ])
            title = "Overdue Books & Fines Report"

        else:  # 'transactions' (all)
            query = Loan.query
            if start_date:
                query = query.filter(Loan.issue_date >= start_date)
            if end_date:
                query = query.filter(Loan.issue_date <= end_date)
            loans = query.order_by(Loan.created_at.desc()).all()
            
            headers = ["Txn ID", "Book Title", "Member Name", "Issue Date", "Due Date", "Return Date", "Status", "Fine ($)"]
            rows = []
            for l in loans:
                rows.append([
                    l.transaction_id,
                    l.book.title if l.book else "N/A",
                    l.member.full_name if l.member else "N/A",
                    l.issue_date.strftime('%Y-%m-%d'),
                    l.due_date.strftime('%Y-%m-%d'),
                    l.return_date.strftime('%Y-%m-%d') if l.return_date else "-",
                    l.effective_status.capitalize(),
                    f"${l.fine_amount:.2f}"
                ])
            title = "Library Transaction Audit Trail"

        return title, headers, rows

    @classmethod
    def export_csv(cls, headers, rows):
        """Export dataset to CSV in-memory buffer."""
        df = pd.DataFrame(rows, columns=headers)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return io.BytesIO(buffer.getvalue().encode('utf-8'))

    @classmethod
    def export_excel(cls, report_title, headers, rows):
        """Export dataset to styled Excel spreadsheet using Pandas and OpenPyXL."""
        df = pd.DataFrame(rows, columns=headers)
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Leave top 2 rows for title header
            df.to_excel(writer, sheet_name='Report', startrow=3, index=False)
            workbook = writer.book
            worksheet = writer.sheets['Report']

            # Report Title Block
            worksheet['A1'] = report_title.upper()
            worksheet['A1'].font = Font(size=14, bold=True, color='0F172A')
            worksheet['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Records: {len(rows)}"
            worksheet['A2'].font = Font(size=10, italic=True, color='64748B')

            # Style Table Headers (Row 4)
            header_fill = PatternFill(start_color='0F172A', end_color='0F172A', fill_type='solid')
            header_font = Font(color='FFFFFF', bold=True)
            border_thin = Border(
                left=Side(style='thin', color='E2E8F0'),
                right=Side(style='thin', color='E2E8F0'),
                top=Side(style='thin', color='E2E8F0'),
                bottom=Side(style='thin', color='E2E8F0')
            )

            for col_idx in range(1, len(headers) + 1):
                cell = worksheet.cell(row=4, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Auto-fit column widths
            for col in worksheet.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.row >= 4 and cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output.seek(0)
        return output

    @classmethod
    def export_pdf(cls, report_title, headers, rows):
        """Export dataset to professional academic PDF using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=15,
            fontName='Helvetica'
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#1e293b'),
            fontName='Helvetica'
        )
        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=1
        )

        elements = []
        library_name = Setting.get_value('library_name', 'Smart Library Management System')

        elements.append(Paragraph(f"{library_name} &bull; {report_title}", title_style))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Total Records: {len(rows)}", subtitle_style))
        elements.append(Spacer(1, 10))

        # Format table data with Paragraphs to auto-wrap long text
        table_data = []
        table_data.append([Paragraph(str(h), header_cell_style) for h in headers])

        for row in rows:
            table_data.append([Paragraph(str(c), cell_style) for c in row])

        pdf_table = Table(table_data, repeatRows=1)
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))

        elements.append(pdf_table)
        doc.build(elements)

        buffer.seek(0)
        return buffer
