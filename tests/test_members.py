from services.library_service import LibraryService
from models.member import Member

def test_create_member_success(app):
    """Test creating a new member."""
    form_data = {
        'member_id': 'MEM-2026-9090',
        'student_staff_id': '22CSE9090',
        'full_name': 'Mehul Saxena',
        'email': 'mehul.s@apex.edu',
        'phone': '+91 9988776655',
        'department': 'Computer Science & Engineering',
        'status': 'Active'
    }
    success, member = LibraryService.create_member(form_data)
    assert success is True
    assert member.full_name == 'Mehul Saxena'

def test_duplicate_member_identifiers(app, test_member):
    """Test duplicate member ID, student ID, and email rejections."""
    # Duplicate member ID
    data1 = {
        'member_id': test_member.member_id,
        'student_staff_id': 'UNIQUE-1',
        'full_name': 'Test Unique',
        'email': 'unique1@apex.edu',
        'department': 'Data Science & AI'
    }
    success, msg1 = LibraryService.create_member(data1)
    assert success is False
    assert "Member ID" in msg1

    # Duplicate student ID
    data2 = {
        'member_id': 'MEM-UNIQUE-2',
        'student_staff_id': test_member.student_staff_id,
        'full_name': 'Test Unique 2',
        'email': 'unique2@apex.edu',
        'department': 'Data Science & AI'
    }
    success, msg2 = LibraryService.create_member(data2)
    assert success is False
    assert "Student/Staff ID" in msg2

    # Duplicate email
    data3 = {
        'member_id': 'MEM-UNIQUE-3',
        'student_staff_id': 'UNIQUE-3',
        'full_name': 'Test Unique 3',
        'email': test_member.email,
        'department': 'Data Science & AI'
    }
    success, msg3 = LibraryService.create_member(data3)
    assert success is False
    assert "Email address" in msg3
