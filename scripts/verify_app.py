import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

def verify():
    app = create_app('development')
    client = app.test_client()

    # 1. Fetch Login Page and CSRF Token
    resp_get = client.get('/login')
    assert resp_get.status_code == 200, f"Login GET failed: {resp_get.status_code}"
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp_get.text)
    assert match, "CSRF token not found on login page"
    csrf_token = match.group(1)

    # 2. Authenticate
    resp_post = client.post('/login', data={
        'username': 'admin',
        'password': 'Admin@123',
        'csrf_token': csrf_token
    }, follow_redirects=True)
    assert resp_post.status_code == 200, f"Login POST failed: {resp_post.status_code}"
    assert "Library Operations Dashboard" in resp_post.text, "Dashboard heading missing"
    print("[PASS] User login and dashboard access verified!")

    # 3. Verify Books Page
    resp_books = client.get('/books')
    assert resp_books.status_code == 200
    assert "Books Inventory Management" in resp_books.text
    print("[PASS] Books catalog route verified!")

    # 4. Verify Members Page
    resp_members = client.get('/members')
    assert resp_members.status_code == 200
    assert "Library Members Directory" in resp_members.text
    print("[PASS] Members directory route verified!")

    # 5. Verify Circulation History
    resp_history = client.get('/transactions/history')
    assert resp_history.status_code == 200
    assert "Circulation Transactions Audit Trail" in resp_history.text
    print("[PASS] Transaction history route verified!")

    # 6. Verify Overdue Page
    resp_overdue = client.get('/transactions/overdue')
    assert resp_overdue.status_code == 200
    assert "Overdue Circulation Monitor" in resp_overdue.text
    print("[PASS] Overdue monitor route verified!")

    # 7. Verify Analytics Page
    resp_analytics = client.get('/analytics')
    assert resp_analytics.status_code == 200
    assert "Library Circulation Intelligence" in resp_analytics.text
    print("[PASS] Analytics hub verified!")

    # 8. Verify Reports PDF Export
    resp_pdf = client.get('/reports/export/pdf/books')
    assert resp_pdf.status_code == 200
    assert resp_pdf.mimetype == 'application/pdf'
    assert resp_pdf.data.startswith(b'%PDF')
    print(f"[PASS] ReportLab PDF generation verified ({len(resp_pdf.data)} bytes)!")

    # 9. Verify Reports Excel Export
    resp_excel = client.get('/reports/export/excel/books')
    assert resp_excel.status_code == 200
    assert 'spreadsheetml' in resp_excel.mimetype
    print(f"[PASS] OpenPyXL Excel generation verified ({len(resp_excel.data)} bytes)!")

    # 10. Verify Reports CSV Export
    resp_csv = client.get('/reports/export/csv/books')
    assert resp_csv.status_code == 200
    assert resp_csv.mimetype == 'text/csv'
    print(f"[PASS] Pandas CSV generation verified ({len(resp_csv.data)} bytes)!")

    # 11. Verify Settings Page (Admin Only)
    resp_settings = client.get('/settings')
    assert resp_settings.status_code == 200
    assert "System Administration" in resp_settings.text
    print("[PASS] Admin settings route verified!")

    print("\n[ALL 11 END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    verify()
