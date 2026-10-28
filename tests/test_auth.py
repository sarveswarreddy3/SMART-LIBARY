from models.user import User

def test_password_hashing():
    """Verify Werkzeug password hashing and verification."""
    user = User(username='hash_test', email='hash@test.edu', full_name='Hash Tester')
    user.set_password('SecretPassword@123')
    assert user.password_hash != 'SecretPassword@123'
    assert user.check_password('SecretPassword@123') is True
    assert user.check_password('WrongPassword') is False

def test_login_success(client, admin_user):
    """Test successful login redirects to dashboard."""
    response = client.post('/login', data={
        'username': 'admin_test',
        'password': 'AdminTest@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Library Operations Dashboard" in response.data

def test_login_failure(client, admin_user):
    """Test login failure with bad password."""
    response = client.post('/login', data={
        'username': 'admin_test',
        'password': 'InvalidPassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_logout(auth_client):
    """Test logout clears session."""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Sign In" in response.data

def test_role_based_access_restriction(client, librarian_user):
    """Verify that a librarian is denied access to admin-only settings route (403)."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(librarian_user.id)
        sess['_fresh'] = True

    response = client.get('/settings')
    assert response.status_code == 403
    assert b"403" in response.data
