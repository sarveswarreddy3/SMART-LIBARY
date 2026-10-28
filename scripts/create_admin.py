import sys
import os
import argparse

# Add parent directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models.user import User

def create_admin_user(username, email, password, full_name="System Administrator", role="admin"):
    app = create_app()
    with app.app_context():
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            print(f"[!] User with username '{username}' or email '{email}' already exists.")
            user.set_password(password)
            user.role = role
            user.full_name = full_name
            user.is_active_account = True
            db.session.commit()
            print(f"[+] Updated password and role for existing user '{user.username}'.")
            return

        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            is_active_account=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"[+] Admin account '{username}' ({role}) created successfully!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create or reset an administrator account.")
    parser.add_argument('--username', default='admin', help="Account username (default: admin)")
    parser.add_argument('--email', default='admin@library.edu', help="Account email (default: admin@library.edu)")
    parser.add_argument('--password', default='Admin@123', help="Account password (default: Admin@123)")
    parser.add_argument('--name', default='Apex Chief Librarian', help="Full name")
    parser.add_argument('--role', default='admin', choices=['admin', 'librarian'], help="Role (default: admin)")

    args = parser.parse_args()
    create_admin_user(args.username, args.email, args.password, args.name, args.role)
