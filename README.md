# Smart Library Management and Book Analytics System

A production-grade, full-stack academic library management and circulation intelligence web application built from scratch with **Python 3**, **Flask**, **SQLite / PostgreSQL**, **Flask-SQLAlchemy**, **Flask-Login**, **Bootstrap 5**, **Chart.js**, **Pandas**, **NumPy**, **ReportLab**, and **OpenPyXL**.

> **Note on Architecture & Design Integrity:**
> In accordance with project specifications, all chatbot widgets, AI assistants, and conversational buttons have been **completely eliminated**. The application focuses on dependable transactional integrity, inventory consistency, role-based security, empirical data analytics, and multi-format reporting.

---

## 1. Key Features & Capabilities

###  Intuitive Administration & Navigation
- Academic navy blue (`#0f172a`), clean white, and tech teal (`#0d9488`) theme.
- Responsive sidebar navigation with dynamic live counters (e.g. overdue badge notification).
- Sticky top navigation bar with user profile dropdown, quick-issue shortcut, and mobile toggle.

### 📚 Complete Book Inventory Management (CRUD)
- Track **ISBN**, **Title**, **Author**, **Category / Discipline**, **Publisher**, **Publication Year**, **Shelf / Stack Location**, **Total Copies**, **Available Copies**, and **Cover Image**.
- Real-time inventory calculation: `Issued Copies = Total Copies - Available Copies`.
- Validation safeguards preventing total copies from being reduced below currently issued copies.
- Unique ISBN enforcement with duplicate detection.
- Book cover image uploads with client-side image preview and server-side file type / size restrictions (max 2MB, `png`, `jpg`, `jpeg`, `webp`).
- **Transactional Deletion Safeguard**: Prevents deletion of books if active loans exist or if historical transactions are tied to the record.

### 👥 Member Directory & Quota Management
- Manage students and faculty across academic departments (CSE, IT, ECE, Mechanical, MBA, Data Science, Physics, etc.).
- Track **Member ID** (e.g., `MEM-2026-0001`), **College / Roll ID**, **Name**, **Email**, **Phone**, and **Membership Status** (`Active`, `Suspended`, `Expired`).
- Member Profile view detailing active borrowings, due dates, and full borrowing history.
- Enforces configurable maximum loan limits per member (default: 4 books).

### 🔄 Book Circulation: Issue & Return Workflows
- **Issue Book**:
  - Validates active member status and borrowing quota.
  - Verifies available copy count (`available_copies > 0`).
  - Rejects duplicate active loans (prevents borrowing multiple copies of the exact same title).
  - Automatically calculates due date from system loan period setting (default: 14 days).
  - Atomically decrements shelf copies in a single database transaction.
- **Return Book**:
  - Fast search by Transaction ID, Member Name, or Book Title.
  - Automatically compares return date with due date.
  - Calculates overdue duration and configurable late fee fine (`overdue_days * fine_rate_per_day`).
  - Atomically restores available inventory count and records settlement status.
  - Strictly prevents duplicate return submissions.

### 📊 Empirical Analytics Hub (Pandas & NumPy)
- **Monthly Circulation Trends**: Multi-series line chart comparing book borrowings and returns across 3, 6, or 12 month time horizons.
- **Category Breakdown**: Doughnut chart illustrating copy distribution across academic subjects.
- **Most Borrowed Titles**: Horizontal bar chart identifying high-demand literature.
- **Top Active Borrowers**: Member circulation ranking by volume.
- **Department Distribution**: Borrowing volume grouped by academic discipline.
- **Overdue Aging Analysis (NumPy)**: Binned duration brackets (1–7 days, 8–14 days, 15–30 days, 30+ days).

### 📑 Multi-Format Reports & Exports
- **Formats Supported**:
  - **PDF Reports**: Generated with **ReportLab** featuring academic letterhead, structured data tables, and generation timestamps.
  - **Excel Spreadsheets**: Formatted `.xlsx` workbooks using **Pandas** and **OpenPyXL** with styled navy headers, auto-fit column widths, and cell borders.
  - **CSV Data**: Raw export for external data pipelines.
- **Report Modules**:
  1. Book Inventory Catalog
  2. Member Directory
  3. Active Issued Loans
  4. Overdue Books & Fines
  5. Returned Books Archive
  6. Complete Transaction Audit Trail

### 🔒 Authentication & Role-Based Access Control (RBAC)
- Password security powered by Werkzeug PBKDF2-SHA256 password hashing.
- Role-based separation: `admin` vs `librarian`.
- Protected administration routes (`/settings`, book/member deletions).
- CSRF protection across all forms via Flask-WTF.
- User profile management for updating display credentials and changing passwords.

---

## 2. Technology Stack & Dependencies

| Layer | Technologies |
|---|---|
| **Backend Framework** | Python 3.10+ / Python 3.13, Flask 3.1 |
| **Database & ORM** | SQLite (Development) / PostgreSQL (Production), Flask-SQLAlchemy, SQLAlchemy 2.0 |
| **Authentication & Session** | Flask-Login 0.6, Werkzeug 3.1 |
| **Security & Forms** | Flask-WTF 1.3, WTForms 3.3, email-validator |
| **Data Analytics** | Pandas 2.2+, NumPy 1.26+ |
| **Visualizations** | Chart.js 4.4 |
| **PDF Generation** | ReportLab 5.1 |
| **Excel Export** | OpenPyXL 3.1, Pandas |
| **Frontend UI** | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons 1.11 |
| **Testing** | Pytest 9.1 |

---

## 3. Project Directory Structure

```text
SMART LIBARY/
├── app.py                      # Application factory and route registration
├── config.py                   # Development, testing, and production configuration
├── extensions.py               # Flask-SQLAlchemy, Flask-Login, Flask-WTF CSRF init
├── requirements.txt            # Python package dependencies
├── .env.example                # Sample environment variables
├── .gitignore                  # Git ignore definitions
├── README.md                   # Complete documentation and viva guide
├── models/                     # SQLAlchemy database models
│   ├── __init__.py
│   ├── user.py                 # Staff accounts, roles, password hashing
│   ├── book.py                 # Book catalog, inventory, and deletion checks
│   ├── member.py               # Student and faculty records and quotas
│   ├── loan.py                 # Loan transactions, overdue logic, fines
│   └── setting.py              # Dynamic system configuration & policies
├── routes/                     # Modular Flask Blueprints
│   ├── __init__.py
│   ├── auth.py                 # Login, logout, role checking decorator
│   ├── dashboard.py            # Main operational metrics and charts
│   ├── books.py                # Book CRUD, search, filter, uploads
│   ├── members.py              # Member directory, profiles, search
│   ├── transactions.py         # Issue, return, history, overdue tracker
│   ├── analytics.py            # Analytics Hub and AJAX endpoints
│   ├── reports.py              # PDF, Excel, and CSV export handlers
│   ├── profile.py              # Password change and personal details
│   └── settings.py             # Library policies and staff user creation
├── services/                   # Decoupled domain service layer
│   ├── __init__.py
│   ├── library_service.py      # Core transaction consistency and validation
│   ├── analytics_service.py    # Pandas & NumPy aggregation logic
│   └── report_service.py       # ReportLab and OpenPyXL file generators
├── templates/                  # Jinja2 templates (Zero chatbot widgets)
│   ├── base.html               # Responsive shell, sidebar, topbar, footer
│   ├── login.html              # Clean login portal with credentials hint
│   ├── dashboard.html          # Operational dashboard with KPI cards & Chart.js
│   ├── profile.html            # Profile edit & change password forms
│   ├── settings.html           # Settings and staff provisioning portal
│   ├── books/                  # Book catalog, form, and view templates
│   ├── members/                # Member directory, form, and profile templates
│   ├── transactions/           # Issue, return, history, and overdue templates
│   ├── analytics/              # Analytics hub with 5 interactive charts
│   ├── reports/                # Report download cards & date filters
│   └── errors/                 # Custom 403, 404, 500 error pages
├── static/                     # Static web assets
│   ├── css/style.css           # Custom academic Navy, Teal & White stylesheet
│   ├── js/main.js              # Sidebar toggle, image preview, tooltips
│   ├── images/default-cover.svg# High-resolution vector book cover graphic
│   └── uploads/covers/         # Uploaded cover images storage
├── scripts/                    # Utilities and automation
│   ├── seed_data.py            # Idempotent realistic academic seed dataset
│   ├── create_admin.py         # CLI admin account creation utility
│   └── verify_app.py           # 11-point end-to-end integration check
└── tests/                      # Automated test suite (20 test cases)
    ├── conftest.py             # In-memory SQLite fixtures and test clients
    ├── test_auth.py            # Authentication, hashing, and RBAC tests
    ├── test_books.py           # Book inventory, copy limits, duplicate checks
    ├── test_members.py         # Member registration and uniqueness tests
    ├── test_transactions.py     # Circulation, return, fines, and duplicate tests
    └── test_reports.py         # PDF, Excel, and CSV export verification
```

---

## 4. Quick Start & Local Setup Instructions

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed.
- Git (optional).

### Step 1: Clone or Navigate to Project
```powershell
cd "c:\Users\sarve\OneDrive\Desktop\SMART LIBARY"
```

### Step 2: Create and Activate Virtual Environment (Recommended)
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(Default settings work out-of-the-box with local SQLite).*

### Step 5: Seed Sample Academic Data
Run the seeding script to populate the database with realistic books, members, and 6-month historical loan records:
```powershell
python scripts/seed_data.py
```

### Step 6: Run the Flask Application
```powershell
python app.py
```
The server will boot at: **`http://127.0.0.1:5000`**

### Step 7: Sign In with Demo Credentials
Open your web browser and navigate to `http://127.0.0.1:5000/login`:

| Role | Username | Password | Access Level |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | Full access (Circulation, Inventory, Staff Accounts, Policies, Safe Delete) |
| **Librarian** | `librarian` | `Librarian@123` | Operational access (Issue, Return, Catalog, Directory, Analytics, Reports) |

---

## 5. Running Automated Tests

A comprehensive test suite with 20 unit and integration tests is located in `tests/`. Tests execute against an isolated in-memory SQLite database:

```powershell
pytest -v
```

**Test Coverage Summary:**
- ✅ Password hashing & PBKDF2 verification
- ✅ Login success and credential rejection
- ✅ Role-based access control (preventing librarians from accessing admin settings)
- ✅ Book creation and duplicate ISBN validation
- ✅ Total copies consistency against currently issued copies
- ✅ Safe book deletion constraint verification
- ✅ Member creation and unique identifier validation (member ID, student ID, email)
- ✅ Atomic inventory decrement when issuing books
- ✅ Prevention of duplicate active issues for the same title
- ✅ Rejection of loans when copies are exhausted (0 available)
- ✅ Atomic inventory restoration on book return
- ✅ Prevention of duplicate returns
- ✅ Overdue duration and fine calculation
- ✅ ReportLab PDF generation verification
- ✅ OpenPyXL Excel spreadsheet generation verification
- ✅ Pandas CSV export generation verification

---

## 6. Cloud Deployment Architecture & Guidelines

### Evaluating Vercel vs. Persistent Hosts

The reference project was hosted on Vercel. However, **Vercel is a serverless frontend hosting platform** designed for stateless functions (Node.js, Next.js, static sites):
1. **Ephemeral Filesystem**: Any SQLite database (`.db`) or uploaded cover images saved to disk on Vercel will be **wiped out** as soon as the serverless function spins down or redeploys.
2. **Serverless Lifespan**: Flask background tasks and report generation can timeout on serverless invocation limits.

### Recommended Production Deployment Stack

To maintain data persistence, consistent inventory, and reliable PDF/Excel generation, deploy to one of the following recommended platforms:

#### Option A: Render / Railway / Fly.io (Recommended)
1. **Web Service**: Deploy Flask using Gunicorn:
   ```bash
   gunicorn "app:create_app('production')" --bind 0.0.0.0:$PORT --workers 3
   ```
2. **Database**: Attach a managed PostgreSQL database instance.
3. **Environment Variable**: Set `DATABASE_URL=postgresql://user:password@host:port/dbname`.
   *(The application automatically converts `postgres://` to `postgresql://` in `config.py`).*
4. **Persistent File Storage**: Use AWS S3, Cloudinary, or Render persistent disks for user uploads.

#### Option B: DigitalOcean Droplet / AWS EC2 / VPS
1. Run Ubuntu 22.04 or 24.04 LTS.
2. Configure **Nginx** as reverse proxy.
3. Configure **Gunicorn** managed by **Systemd**.
4. Use standard SQLite (with regular automated backups) or PostgreSQL.

---

## 7. Viva & Academic Presentation Guide

When demonstrating this project for academic evaluations, viva examinations, or faculty reviews, emphasize these core design highlights:

1. **Transactional Consistency & Acid Compliance**:
   - The issue and return workflows use database transactions. If any check fails, the transaction rolls back cleanly, ensuring that physical inventory counts never drift from transaction records.
2. **Historical Referential Integrity**:
   - Deleting a book or member is guarded by `can_be_deleted()`. If a record has historical or active loans, deletion is blocked to prevent orphaned transaction records.
3. **Pure Empirical Analytics**:
   - Unlike projects with hardcoded numbers, every chart on the Dashboard and Analytics Hub is calculated dynamically using SQL queries, Pandas grouping, and NumPy date bracket calculations.
4. **Zero Unnecessary Bloat**:
   - The application does not contain fake AI or chatbot widgets, adhering to clean software engineering principles.
