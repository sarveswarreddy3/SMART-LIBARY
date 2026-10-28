def test_export_csv(auth_client, test_book):
    """Test CSV export endpoint returns valid CSV payload."""
    response = auth_client.get('/reports/export/csv/books')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert b"Automated Software Testing Principles" in response.data

def test_export_excel(auth_client, test_book):
    """Test Excel export endpoint returns spreadsheet payload."""
    response = auth_client.get('/reports/export/excel/books')
    assert response.status_code == 200
    assert 'spreadsheetml' in response.mimetype

def test_export_pdf(auth_client, test_book):
    """Test ReportLab PDF export returns valid PDF binary stream."""
    response = auth_client.get('/reports/export/pdf/books')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF')
