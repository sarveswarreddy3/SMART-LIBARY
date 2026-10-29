"""
Database Migration Script: SQLite (library.db) -> PostgreSQL
Usage:
    python scripts/migrate_to_postgres.py --target-url "postgresql://user:password@host:port/dbname?sslmode=require"

Or set DATABASE_URL in your .env or environment and run:
    python scripts/migrate_to_postgres.py
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from extensions import db
from models.user import User
from models.setting import Setting
from models.book import Book
from models.member import Member
from models.loan import Loan
from config import normalize_database_url

TABLES_ORDER = ['users', 'settings', 'books', 'members', 'loans']

def migrate(source_sqlite_path, target_postgres_url):
    print(f"[*] Starting migration...")
    print(f"[*] Source SQLite: {source_sqlite_path}")

    if not os.path.exists(source_sqlite_path):
        print(f"[!] Error: Source database '{source_sqlite_path}' does not exist.")
        sys.exit(1)

    target_postgres_url = normalize_database_url(target_postgres_url)
    if not target_postgres_url:
        print("[!] Error: No target PostgreSQL URL provided. Pass --target-url or set DATABASE_URL.")
        sys.exit(1)

    # Obfuscate credentials for safe console logging
    safe_target = target_postgres_url
    if '@' in safe_target:
        creds, host = safe_target.split('@', 1)
        scheme = creds.split('://')[0]
        safe_target = f"{scheme}://****:****@{host}"
    print(f"[*] Target PostgreSQL: {safe_target}")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(source_sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to PostgreSQL
    try:
        pg_engine = create_engine(target_postgres_url)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[+] Successfully connected to PostgreSQL database!")
    except Exception as e:
        print(f"[!] Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    # Create tables in PostgreSQL using SQLAlchemy metadata
    print("[*] Creating database schema in PostgreSQL if not already present...")
    from app import create_app
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = target_postgres_url
    with app.app_context():
        db.create_all()
    print("[+] Database schema is ready.")

    total_migrated = {}

    with pg_engine.begin() as pg_conn:
        for table_name in TABLES_ORDER:
            # Check source rows
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            source_rows = sqlite_cursor.fetchall()
            if not source_rows:
                print(f"[-] {table_name}: No records in source SQLite database.")
                total_migrated[table_name] = 0
                continue

            columns = source_rows[0].keys()
            col_names = ", ".join(columns)
            placeholders = ", ".join([f":{col}" for col in columns])

            # Use ON CONFLICT DO NOTHING to ensure idempotence
            insert_stmt = text(
                f"INSERT INTO {table_name} ({col_names}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING"
            )

            migrated_count = 0
            for row in source_rows:
                row_dict = dict(row)
                pg_conn.execute(insert_stmt, row_dict)
                migrated_count += 1

            total_migrated[table_name] = migrated_count
            print(f"[+] {table_name}: Migrated {migrated_count} records.")

            # Update PostgreSQL sequence to match MAX(id)
            try:
                seq_query = text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name}")
                pg_conn.execute(seq_query)
            except Exception as seq_err:
                # Some tables may not use serial id or sequence name differs
                pass

    sqlite_conn.close()
    print("\n[+] ==========================================")
    print("[+] Migration completed successfully!")
    print("[+] Records transferred:")
    for tbl, cnt in total_migrated.items():
        print(f"    - {tbl}: {cnt}")
    print("[+] ==========================================\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL.")
    parser.add_argument(
        '--source-db',
        default=os.path.join(os.path.dirname(__file__), '..', 'library.db'),
        help="Path to source SQLite database file (default: library.db)"
    )
    parser.add_argument(
        '--target-url',
        default=os.environ.get('DATABASE_URL'),
        help="Target PostgreSQL database URL (default: DATABASE_URL environment variable)"
    )
    args = parser.parse_args()

    if not args.target_url:
        print("[!] Error: Target PostgreSQL URL is required.")
        print("    Usage: python scripts/migrate_to_postgres.py --target-url 'postgresql://user:pass@host:port/dbname?sslmode=require'")
        print("    Or set DATABASE_URL environment variable in your .env file.")
        sys.exit(1)

    migrate(os.path.abspath(args.source_db), args.target_url)
