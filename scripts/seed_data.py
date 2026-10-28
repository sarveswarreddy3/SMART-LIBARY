import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models.user import User
from models.book import Book
from models.member import Member
from models.loan import Loan
from models.setting import Setting

def seed_database(reset=False):
    """Populate database with rich fictional sample data for academic demonstration."""
    app = create_app()

    with app.app_context():
        print("[*] Initializing database tables...")
        db.create_all()

        if reset:
            print("[*] Clearing existing tables...")
            Loan.query.delete()
            Member.query.delete()
            Book.query.delete()
            User.query.delete()
            Setting.query.delete()
            db.session.commit()

        # 1. Initialize Settings
        print("[*] Configuring library settings...")
        Setting.init_defaults()
        Setting.set_value('library_name', 'Apex Smart Library & Analytics System')
        Setting.set_value('default_loan_days', '14')
        Setting.set_value('fine_rate_per_day', '1.00')
        Setting.set_value('max_books_per_member', '4')
        Setting.set_value('currency_symbol', '$')

        # 2. Staff Accounts
        print("[*] Creating staff user accounts...")
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@library.edu',
                full_name='Dr. Rajiv Sen (Chief Administrator)',
                role='admin',
                is_active_account=True,
                created_at=datetime.now(timezone.utc) - timedelta(days=180)
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
        else:
            admin.set_password('Admin@123')

        librarian = User.query.filter_by(username='librarian').first()
        if not librarian:
            librarian = User(
                username='librarian',
                email='librarian@library.edu',
                full_name='Priya Nair (Senior Librarian)',
                role='librarian',
                is_active_account=True,
                created_at=datetime.now(timezone.utc) - timedelta(days=120)
            )
            librarian.set_password('Librarian@123')
            db.session.add(librarian)
        else:
            librarian.set_password('Librarian@123')

        db.session.commit()

        # 3. Sample Books
        print("[*] Adding catalog books...")
        books_data = [
            {
                "isbn": "978-0262033848",
                "title": "Introduction to Algorithms (4th Edition)",
                "author": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest",
                "category": "Computer Science",
                "publisher": "MIT Press",
                "publication_year": 2022,
                "description": "Comprehensive reference work on algorithms, data structures, complexity theory, and dynamic programming.",
                "shelf_location": "Rack CS-01",
                "total_copies": 8
            },
            {
                "isbn": "978-0134610993",
                "title": "Artificial Intelligence: A Modern Approach",
                "author": "Stuart Russell, Peter Norvig",
                "category": "Data Science & AI",
                "publisher": "Pearson",
                "publication_year": 2020,
                "description": "Authoritative standard text on intelligent agents, neural networks, machine learning, and probabilistic reasoning.",
                "shelf_location": "Rack AI-02",
                "total_copies": 7
            },
            {
                "isbn": "978-0132350884",
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "author": "Robert C. Martin",
                "category": "Computer Science",
                "publisher": "Prentice Hall",
                "publication_year": 2008,
                "description": "Best practices for writing readable, maintainable, and bug-resistant software.",
                "shelf_location": "Rack CS-03",
                "total_copies": 6
            },
            {
                "isbn": "978-0262035613",
                "title": "Deep Learning",
                "author": "Ian Goodfellow, Yoshua Bengio, Aaron Courville",
                "category": "Data Science & AI",
                "publisher": "MIT Press",
                "publication_year": 2016,
                "description": "Essential textbook on mathematical foundations, deep feedforward networks, convolution, and sequence models.",
                "shelf_location": "Rack AI-04",
                "total_copies": 5
            },
            {
                "isbn": "978-1449373320",
                "title": "Designing Data-Intensive Applications",
                "author": "Martin Kleppmann",
                "category": "Computer Science",
                "publisher": "O'Reilly Media",
                "publication_year": 2017,
                "description": "The definitive guide to storage engines, distributed consensus, stream processing, and replication.",
                "shelf_location": "Rack CS-02",
                "total_copies": 7
            },
            {
                "isbn": "978-1098104030",
                "title": "Python for Data Analysis (3rd Edition)",
                "author": "Wes McKinney",
                "category": "Data Science & AI",
                "publisher": "O'Reilly Media",
                "publication_year": 2022,
                "description": "Practical manipulation, processing, and cleaning of structured data using NumPy, Pandas, and Jupyter.",
                "shelf_location": "Rack DS-01",
                "total_copies": 6
            },
            {
                "isbn": "978-1098125974",
                "title": "Hands-On Machine Learning with Scikit-Learn and TensorFlow",
                "author": "Aurélien Géron",
                "category": "Data Science & AI",
                "publisher": "O'Reilly Media",
                "publication_year": 2022,
                "description": "Applied guide from linear regression to generative adversarial networks and transformer architectures.",
                "shelf_location": "Rack AI-01",
                "total_copies": 6
            },
            {
                "isbn": "978-0078022159",
                "title": "Database System Concepts (7th Edition)",
                "author": "Abraham Silberschatz, Henry F. Korth",
                "category": "Computer Science",
                "publisher": "McGraw-Hill",
                "publication_year": 2019,
                "description": "Foundational text covering relational models, SQL, indexing, transaction processing, and concurrency control.",
                "shelf_location": "Rack CS-05",
                "total_copies": 6
            },
            {
                "isbn": "978-0136681557",
                "title": "Computer Networking: A Top-Down Approach",
                "author": "James Kurose, Keith Ross",
                "category": "Computer Science",
                "publisher": "Pearson",
                "publication_year": 2021,
                "description": "Layer-by-layer exploration of protocols from HTTP/DNS to transport, routing, and SDN.",
                "shelf_location": "Rack CS-06",
                "total_copies": 5
            },
            {
                "isbn": "978-1119800361",
                "title": "Operating System Concepts (10th Edition)",
                "author": "Abraham Silberschatz, Peter B. Galvin",
                "category": "Computer Science",
                "publisher": "Wiley",
                "publication_year": 2018,
                "description": "Classic textbook on processes, memory virtualization, threading, scheduling, and file systems.",
                "shelf_location": "Rack CS-04",
                "total_copies": 5
            },
            {
                "isbn": "978-0980232776",
                "title": "Linear Algebra and Its Applications (5th Edition)",
                "author": "Gilbert Strang",
                "category": "Mathematics",
                "publisher": "Wellesley-Cambridge Press",
                "publication_year": 2016,
                "description": "Vector spaces, eigenvalues, singular value decomposition, and computational linear algebra.",
                "shelf_location": "Rack MATH-01",
                "total_copies": 5
            },
            {
                "isbn": "978-1285741550",
                "title": "Calculus: Early Transcendentals",
                "author": "James Stewart",
                "category": "Mathematics",
                "publisher": "Cengage Learning",
                "publication_year": 2015,
                "description": "Differential and integral calculus, multivariable vector fields, and series expansions.",
                "shelf_location": "Rack MATH-02",
                "total_copies": 4
            },
            {
                "isbn": "978-0135159552",
                "title": "University Physics with Modern Physics",
                "author": "Hugh D. Young, Roger A. Freedman",
                "category": "Physics",
                "publisher": "Pearson",
                "publication_year": 2019,
                "description": "Comprehensive physics reference covering mechanics, thermodynamics, electromagnetism, and optics.",
                "shelf_location": "Rack PHY-01",
                "total_copies": 4
            },
            {
                "isbn": "978-0521809269",
                "title": "The Art of Electronics (3rd Edition)",
                "author": "Paul Horowitz, Winfield Hill",
                "category": "Electronics Engineering",
                "publisher": "Cambridge University Press",
                "publication_year": 2015,
                "description": "Indispensable circuitry handbook on analog design, op-amps, microcontrollers, and RF techniques.",
                "shelf_location": "Rack EC-01",
                "total_copies": 4
            },
            {
                "isbn": "978-0307887894",
                "title": "The Lean Startup",
                "author": "Eric Ries",
                "category": "Business & Management",
                "publisher": "Crown Business",
                "publication_year": 2011,
                "description": "Modern entrepreneurial framework based on validated learning, rapid prototyping, and pivot mechanics.",
                "shelf_location": "Rack MBA-01",
                "total_copies": 4
            },
            {
                "isbn": "978-0743260985",
                "title": "Competitive Strategy: Analyzing Industries",
                "author": "Michael E. Porter",
                "category": "Business & Management",
                "publisher": "Free Press",
                "publication_year": 2004,
                "description": "Landmark framework introducing five forces, cost leadership, differentiation, and competitive positioning.",
                "shelf_location": "Rack MBA-02",
                "total_copies": 4
            },
            {
                "isbn": "978-0262510875",
                "title": "Structure and Interpretation of Computer Programs",
                "author": "Harold Abelson, Gerald Jay Sussman",
                "category": "Computer Science",
                "publisher": "MIT Press",
                "publication_year": 1996,
                "description": "Legendary computational abstraction text exploring meta-linguistic abstraction and interpreters.",
                "shelf_location": "Rack CS-07",
                "total_copies": 4
            },
            {
                "isbn": "978-0060935467",
                "title": "To Kill a Mockingbird",
                "author": "Harper Lee",
                "category": "Literature & Arts",
                "publisher": "Harper Perennial",
                "publication_year": 2002,
                "description": "Pulitzer Prize-winning classic on empathy, civil rights, and moral courage in southern America.",
                "shelf_location": "Rack LIT-01",
                "total_copies": 3
            }
        ]

        created_books = []
        for b in books_data:
            book = Book.query.filter_by(isbn=b['isbn']).first()
            if not book:
                book = Book(
                    isbn=b['isbn'],
                    title=b['title'],
                    author=b['author'],
                    category=b['category'],
                    publisher=b['publisher'],
                    publication_year=b['publication_year'],
                    description=b['description'],
                    shelf_location=b['shelf_location'],
                    total_copies=b['total_copies'],
                    available_copies=b['total_copies']
                )
                db.session.add(book)
            created_books.append(book)
        db.session.commit()

        # 4. Sample Members
        print("[*] Adding student and faculty members...")
        members_data = [
            ("MEM-2026-0001", "21CSE1042", "Aarav Sharma", "aarav.sharma@apex.edu", "+91 9876543210", "Computer Science & Engineering", "Active"),
            ("MEM-2026-0002", "21CSE1089", "Ananya Iyer", "ananya.iyer@apex.edu", "+91 9876543211", "Computer Science & Engineering", "Active"),
            ("MEM-2026-0003", "22DS0201", "Rohan Verma", "rohan.verma@apex.edu", "+91 9876543212", "Data Science & AI", "Active"),
            ("MEM-2026-0004", "22DS0245", "Sneha Kulkarni", "sneha.k@apex.edu", "+91 9876543213", "Data Science & AI", "Active"),
            ("MEM-2026-0005", "20ECE1014", "Vikram Malhotra", "vikram.m@apex.edu", "+91 9876543214", "Electronics & Communication", "Active"),
            ("MEM-2026-0006", "20MECH105", "Tanvi Joshi", "tanvi.j@apex.edu", "+91 9876543215", "Mechanical Engineering", "Active"),
            ("MEM-2026-0007", "23MBA0012", "Karan Singhania", "karan.s@apex.edu", "+91 9876543216", "Business Administration (MBA)", "Active"),
            ("MEM-2026-0008", "23MBA0034", "Meera Nambiar", "meera.n@apex.edu", "+91 9876543217", "Business Administration (MBA)", "Active"),
            ("MEM-2026-0009", "FAC-CSE-01", "Prof. Aris Thorne", "thorne.faculty@apex.edu", "+91 9876543218", "Computer Science & Engineering", "Active"),
            ("MEM-2026-0010", "FAC-MATH-02", "Dr. Elena Rostova", "rostova.faculty@apex.edu", "+91 9876543219", "Physics & Mathematics", "Active"),
            ("MEM-2026-0011", "21CIVIL044", "Deepak Patwardhan", "deepak.p@apex.edu", "+91 9876543220", "Civil Engineering", "Suspended"),
            ("MEM-2026-0012", "22IT1078", "Ritika Sengupta", "ritika.s@apex.edu", "+91 9876543221", "Information Technology", "Active")
        ]

        created_members = []
        for code, roll, name, email, phone, dept, status in members_data:
            mem = Member.query.filter_by(member_id=code).first()
            if not mem:
                mem = Member(
                    member_id=code,
                    student_staff_id=roll,
                    full_name=name,
                    email=email,
                    phone=phone,
                    department=dept,
                    status=status,
                    membership_date=date.today() - timedelta(days=200)
                )
                db.session.add(mem)
            created_members.append(mem)
        db.session.commit()

        # 5. Sample Transactions Across Past 6 Months
        print("[*] Generating realistic circulation transactions & history...")
        today = date.today()

        # Historical returned loans (spanning months so trends look great)
        historical_loans = [
            # 5 months ago (May)
            (created_books[0], created_members[0], today - timedelta(days=160), today - timedelta(days=146), today - timedelta(days=148), 0.0, True),
            (created_books[1], created_members[1], today - timedelta(days=155), today - timedelta(days=141), today - timedelta(days=140), 0.0, True),
            (created_books[2], created_members[2], today - timedelta(days=150), today - timedelta(days=136), today - timedelta(days=132), 0.0, True),
            (created_books[4], created_members[3], today - timedelta(days=148), today - timedelta(days=134), today - timedelta(days=130), 0.0, True),
            
            # 4 months ago (June)
            (created_books[0], created_members[4], today - timedelta(days=125), today - timedelta(days=111), today - timedelta(days=108), 0.0, True),
            (created_books[5], created_members[2], today - timedelta(days=120), today - timedelta(days=106), today - timedelta(days=103), 0.0, True),
            (created_books[6], created_members[3], today - timedelta(days=118), today - timedelta(days=104), today - timedelta(days=100), 0.0, True),
            (created_books[7], created_members[0], today - timedelta(days=115), today - timedelta(days=101), today - timedelta(days=97), 0.0, True),
            (created_books[14], created_members[6], today - timedelta(days=110), today - timedelta(days=96), today - timedelta(days=94), 0.0, True),

            # 3 months ago (July)
            (created_books[1], created_members[8], today - timedelta(days=90), today - timedelta(days=76), today - timedelta(days=75), 0.0, True),
            (created_books[3], created_members[2], today - timedelta(days=88), today - timedelta(days=74), today - timedelta(days=70), 0.0, True),
            (created_books[4], created_members[1], today - timedelta(days=85), today - timedelta(days=71), today - timedelta(days=68), 0.0, True),
            (created_books[8], created_members[5], today - timedelta(days=82), today - timedelta(days=68), today - timedelta(days=65), 0.0, True),
            (created_books[10], created_members[9], today - timedelta(days=80), today - timedelta(days=66), today - timedelta(days=64), 0.0, True),
            (created_books[15], created_members[7], today - timedelta(days=78), today - timedelta(days=64), today - timedelta(days=60), 0.0, True),
            # Returned with a 4 day fine ($4.00)
            (created_books[0], created_members[5], today - timedelta(days=75), today - timedelta(days=61), today - timedelta(days=57), 4.0, True),

            # 2 months ago (August)
            (created_books[2], created_members[0], today - timedelta(days=60), today - timedelta(days=46), today - timedelta(days=44), 0.0, True),
            (created_books[5], created_members[3], today - timedelta(days=58), today - timedelta(days=44), today - timedelta(days=42), 0.0, True),
            (created_books[6], created_members[1], today - timedelta(days=55), today - timedelta(days=41), today - timedelta(days=40), 0.0, True),
            (created_books[9], created_members[4], today - timedelta(days=52), today - timedelta(days=38), today - timedelta(days=36), 0.0, True),
            (created_books[13], created_members[4], today - timedelta(days=50), today - timedelta(days=36), today - timedelta(days=33), 0.0, True),
            # Returned with a 6 day fine ($6.00)
            (created_books[1], created_members[7], today - timedelta(days=48), today - timedelta(days=34), today - timedelta(days=28), 6.0, True),

            # Last month (September)
            (created_books[0], created_members[2], today - timedelta(days=30), today - timedelta(days=16), today - timedelta(days=15), 0.0, True),
            (created_books[4], created_members[0], today - timedelta(days=28), today - timedelta(days=14), today - timedelta(days=12), 0.0, True),
            (created_books[7], created_members[11], today - timedelta(days=25), today - timedelta(days=11), today - timedelta(days=9), 0.0, True),
            (created_books[11], created_members[9], today - timedelta(days=22), today - timedelta(days=8), today - timedelta(days=7), 0.0, True),
            (created_books[16], created_members[1], today - timedelta(days=20), today - timedelta(days=6), today - timedelta(days=5), 0.0, True),
            # Returned with a 3 day fine ($3.00)
            (created_books[3], created_members[6], today - timedelta(days=24), today - timedelta(days=10), today - timedelta(days=7), 3.0, True)
        ]

        for b, m, iss_date, due_d, ret_d, fine, fine_p in historical_loans:
            txn_code = f"TXN-{iss_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
            if not Loan.query.filter_by(transaction_id=txn_code).first():
                loan = Loan(
                    transaction_id=txn_code,
                    book_id=b.id,
                    member_id=m.id,
                    issued_by_id=admin.id,
                    returned_by_id=librarian.id,
                    issue_date=iss_date,
                    due_date=due_d,
                    return_date=ret_d,
                    status='returned',
                    fine_amount=fine,
                    fine_paid=fine_p,
                    notes="Completed loan return."
                )
                db.session.add(loan)

        # 6. Currently Issued (Active, not overdue)
        active_loans = [
            (created_books[0], created_members[1], today - timedelta(days=4), today + timedelta(days=10)),
            (created_books[1], created_members[2], today - timedelta(days=6), today + timedelta(days=8)),
            (created_books[3], created_members[3], today - timedelta(days=2), today + timedelta(days=12)),
            (created_books[4], created_members[8], today - timedelta(days=5), today + timedelta(days=9)),
            (created_books[5], created_members[11], today - timedelta(days=1), today + timedelta(days=13)),
            (created_books[6], created_members[0], today - timedelta(days=3), today + timedelta(days=11)),
            (created_books[14], created_members[7], today - timedelta(days=7), today + timedelta(days=7))
        ]

        for b, m, iss_date, due_d in active_loans:
            # Check if active loan already exists
            existing = Loan.query.filter_by(book_id=b.id, member_id=m.id, status='issued').first()
            if not existing:
                txn_code = f"TXN-{iss_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
                loan = Loan(
                    transaction_id=txn_code,
                    book_id=b.id,
                    member_id=m.id,
                    issued_by_id=librarian.id,
                    issue_date=iss_date,
                    due_date=due_d,
                    status='issued',
                    fine_amount=0.0,
                    fine_paid=False,
                    notes="Standard semester loan."
                )
                db.session.add(loan)

        # 7. Currently Overdue Loans (Actionable)
        overdue_loans = [
            # 5 days overdue
            (created_books[2], created_members[4], today - timedelta(days=19), today - timedelta(days=5)),
            # 12 days overdue
            (created_books[7], created_members[5], today - timedelta(days=26), today - timedelta(days=12)),
            # 3 days overdue
            (created_books[8], created_members[6], today - timedelta(days=17), today - timedelta(days=3)),
            # 18 days overdue
            (created_books[12], created_members[9], today - timedelta(days=32), today - timedelta(days=18))
        ]

        for b, m, iss_date, due_d in overdue_loans:
            existing = Loan.query.filter_by(book_id=b.id, member_id=m.id, status='issued').first()
            if not existing:
                txn_code = f"TXN-{iss_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
                loan = Loan(
                    transaction_id=txn_code,
                    book_id=b.id,
                    member_id=m.id,
                    issued_by_id=admin.id,
                    issue_date=iss_date,
                    due_date=due_d,
                    status='issued',
                    fine_amount=0.0,
                    fine_paid=False,
                    notes="Past due notice generated."
                )
                db.session.add(loan)

        db.session.commit()

        # 8. Reconcile Book Available Inventory Copies with Exact Truth
        print("[*] Reconciling book inventory copy counts with live loan state...")
        for book in Book.query.all():
            active_count = Loan.query.filter_by(book_id=book.id, status='issued').count()
            book.available_copies = max(0, book.total_copies - active_count)
        db.session.commit()

        print("[+] Seed completed successfully!")
        print("    Admin credentials:     username='admin'     password='Admin@123'")
        print("    Librarian credentials: username='librarian' password='Librarian@123'")

if __name__ == '__main__':
    seed_database(reset=True)
