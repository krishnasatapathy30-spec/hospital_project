import os
import sqlite3
import csv
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

DATABASE = 'hospital.db'
COUNT_DOCTORS_QUERY = 'SELECT COUNT(*) FROM doctors'

# Flask-Login setup + simple User wrapper
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = str(id)
        self.username = username
        self.role = role

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2])
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, 'role', None) != role:
                flash('Permission denied', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    created = not os.path.exists(DATABASE)
    conn = get_db_connection()
    cursor = conn.cursor()

    # users table (include role)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'staff'
        )
    ''')

    # ensure 'role' column exists for older DBs
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if 'role' not in existing_cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'staff'")
        except Exception:
            pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            disease TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT,
            phone TEXT,
            email TEXT,
            fee REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            date TEXT,
            time TEXT,
            status TEXT DEFAULT 'Scheduled',
            notes TEXT
        )
    ''')

    # invoices table: used by billing/report routes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'Unpaid',
            description TEXT,
            created_at TEXT,
            due_date TEXT
        )
    ''')

    # Seed users (with role)
    users = [
        ('admin', 'password', 'admin'),
        ('ramesh', '12345', 'staff'),
        ('krishna', 'krishna123', 'staff'),
    ]
    for username, pwd, role in users:
        hashed = generate_password_hash(pwd)
        try:
            cursor.execute('INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed, role))
        except sqlite3.IntegrityError:
            pass

    # Seed a sample patient if DB newly created
    if created:
        try:
            cursor.execute("INSERT INTO patients (name, age, gender, disease) VALUES (?, ?, ?, ?)",
                           ('John Doe', 30, 'Male', 'Flu'))
        except Exception:
            pass

    # Seed sample doctors if empty
    cursor.execute(COUNT_DOCTORS_QUERY)
    try:
        doc_count = cursor.fetchone()[0]
    except Exception:
        doc_count = 0
    if doc_count == 0:
        doctors_seed = [
            ('Dr. Alice', 'Cardiology', '1234567890', 'alice@example.com', 200.0),
            ('Dr. Bob', 'Orthopedics', '0987654321', 'bob@example.com', 150.0),
        ]
        for d in doctors_seed:
            cursor.execute('INSERT INTO doctors (name, specialty, phone, email, fee) VALUES (?, ?, ?, ?, ?)', d)

    conn.commit()
    conn.close()


@app.route('/', methods=['GET'])
@login_required
def index():
    # basic search + pagination for patients
    q = request.args.get('q', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    if q:
        cursor.execute('SELECT COUNT(*) FROM patients WHERE name LIKE ?', (f'%{q}%',))
        total = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM patients WHERE name LIKE ? LIMIT ? OFFSET ?', (f'%{q}%', per_page, offset))
    else:
        cursor.execute('SELECT COUNT(*) FROM patients')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM patients LIMIT ? OFFSET ?', (per_page, offset))

    patients = cursor.fetchall()

    # quick dashboard stats
    cursor.execute(COUNT_DOCTORS_QUERY)
    total_doctors = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM appointments')
    total_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM invoices WHERE status='Paid'")
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM invoices WHERE status!='Paid'")
    total_unpaid = cursor.fetchone()[0] or 0

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('index.html', patients=patients, q=q, page=page, total_pages=total_pages, total=total, per_page=per_page, totals={
        'patients': total,
        'doctors': total_doctors,
        'appointments': total_appointments,
        'revenue': total_revenue,
        'unpaid': total_unpaid
    })


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password, role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[1], password):
            user_obj = User(row[0], username, row[2] or 'staff')
            login_user(user_obj)
            session['user'] = username
            session['role'] = user_obj.role
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Properly log out user from flask-login and clear session
    try:
        logout_user()
    except Exception:
        pass
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/add_patient', methods=['POST'])
@login_required
def add_patient():
    if 'user' not in session:
        return redirect(url_for('login'))
    name = request.form.get('name', '').strip()
    age = request.form.get('age')
    gender = request.form.get('gender', '').strip()
    disease = request.form.get('disease', '').strip()
    if not name:
        flash('Patient name is required', 'danger')
        return redirect(url_for('index'))
    try:
        age_val = int(age) if age else None
    except ValueError:
        flash('Invalid age', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO patients (name, age, gender, disease) VALUES (?, ?, ?, ?)',
                   (name, age_val, gender, disease))
    conn.commit()
    conn.close()
    flash('Patient added', 'success')
    return redirect(url_for('index'))


@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_patient(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM patients WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Patient deleted', 'success')
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_patient(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age')
        gender = request.form.get('gender', '').strip()
        disease = request.form.get('disease', '').strip()
        try:
            age_val = int(age) if age else None
        except ValueError:
            flash('Invalid age', 'danger')
            return redirect(url_for('edit_patient', id=id))
        cursor.execute('UPDATE patients SET name=?, age=?, gender=?, disease=? WHERE id = ?',
                       (name, age_val, gender, disease, id))
        conn.commit()
        conn.close()
        flash('Patient updated', 'success')
        return redirect(url_for('index'))

    cursor.execute('SELECT * FROM patients WHERE id = ?', (id,))
    patient = cursor.fetchone()
    conn.close()
    if not patient:
        flash('Patient not found', 'danger')
        return redirect(url_for('index'))
    return render_template('edit.html', patient=patient)


# ---------- Doctors routes ----------
@app.route('/doctors', methods=['GET', 'POST'])
@login_required
def doctors():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        specialty = request.form.get('specialty', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        fee = request.form.get('fee')
        try:
            fee_val = float(fee) if fee else None
        except ValueError:
            flash('Invalid fee', 'danger')
            return redirect(url_for('doctors'))
        if not name:
            flash('Doctor name is required', 'danger')
            return redirect(url_for('doctors'))
        cursor.execute('INSERT INTO doctors (name, specialty, phone, email, fee) VALUES (?, ?, ?, ?, ?)',
                       (name, specialty, phone, email, fee_val))
        conn.commit()
        conn.close()
        flash('Doctor added', 'success')
        return redirect(url_for('doctors'))

    cursor.execute('SELECT * FROM doctors')
    doctors_list = cursor.fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors_list)


@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        specialty = request.form.get('specialty', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        fee = request.form.get('fee')
        try:
            fee_val = float(fee) if fee else None
        except ValueError:
            flash('Invalid fee', 'danger')
            return redirect(url_for('edit_doctor', id=id))
        cursor.execute('UPDATE doctors SET name=?, specialty=?, phone=?, email=?, fee=? WHERE id=?',
                       (name, specialty, phone, email, fee_val, id))
        conn.commit()
        conn.close()
        flash('Doctor updated', 'success')
        return redirect(url_for('doctors'))

    cursor.execute('SELECT * FROM doctors WHERE id = ?', (id,))
    doctor = cursor.fetchone()
    conn.close()
    if not doctor:
        flash('Doctor not found', 'danger')
        return redirect(url_for('doctors'))
    return render_template('edit_doctor.html', doctor=doctor)


@app.route('/delete_doctor/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_doctor(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM doctors WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Doctor deleted', 'success')
    return redirect(url_for('doctors'))


# ---------- Appointments routes ----------
@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')
        if not patient_id or not doctor_id or not date or not time:
            flash('All fields are required', 'danger')
            return redirect(url_for('appointments'))
        cursor.execute('INSERT INTO appointments (patient_id, doctor_id, date, time) VALUES (?, ?, ?, ?)',
                       (patient_id, doctor_id, date, time))
        conn.commit()
        conn.close()
        flash('Appointment scheduled', 'success')
        return redirect(url_for('appointments'))

    cursor.execute('''
        SELECT a.id, p.name, d.name, a.date, a.time, a.status
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.id
        LEFT JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.date DESC, a.time DESC
    ''')
    appointments_list = cursor.fetchall()
    cursor.execute('SELECT * FROM patients')
    patients = cursor.fetchall()
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    conn.close()
    return render_template('appointments.html', appointments=appointments_list, patients=patients, doctors=doctors)


@app.route('/cancel_appointment/<int:id>', methods=['POST'])
@login_required
def cancel_appointment(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status='Cancelled' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Appointment cancelled', 'success')
    return redirect(url_for('appointments'))


# ---------- Billing / Reports (new) ----------
@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        due_date = request.form.get('due_date') or None
        try:
            amount_val = float(amount)
        except (ValueError, TypeError):
            flash('Invalid amount', 'danger')
            return redirect(url_for('billing'))
        cursor.execute('INSERT INTO invoices (patient_id, amount, status, description, created_at, due_date) VALUES (?, ?, ?, ?, datetime("now"), ?)',
                       (patient_id, amount_val, 'Unpaid', description, due_date))
        conn.commit()
        conn.close()
        flash('Invoice added', 'success')
        return redirect(url_for('billing'))

    cursor.execute('''
        SELECT i.id, p.name, i.amount, i.status, i.created_at, i.due_date, i.description
        FROM invoices i
        LEFT JOIN patients p ON i.patient_id = p.id
        ORDER BY i.created_at DESC
    ''')
    invoices = cursor.fetchall()
    cursor.execute('SELECT * FROM patients')
    patients = cursor.fetchall()
    conn.close()
    return render_template('billing.html', invoices=invoices, patients=patients)


@app.route('/invoice/<int:id>', methods=['GET'])
@login_required
def invoice(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT i.id, p.name, i.amount, i.status, i.created_at, i.due_date, i.description FROM invoices i LEFT JOIN patients p ON i.patient_id = p.id WHERE i.id = ?', (id,))
    inv = cursor.fetchone()
    conn.close()
    if not inv:
        flash('Invoice not found', 'danger')
        return redirect(url_for('billing'))
    return render_template('invoice.html', invoice=inv)


@app.route('/pay_invoice/<int:id>', methods=['POST'])
@login_required
def pay_invoice(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE invoices SET status='Paid' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Invoice marked as paid', 'success')
    return redirect(url_for('billing'))


@app.route('/export_invoices', methods=['GET'])
@login_required
def export_invoices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT i.id, p.name, i.amount, i.status, i.created_at, i.due_date, i.description FROM invoices i LEFT JOIN patients p ON i.patient_id = p.id')
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'patient', 'amount', 'status', 'created_at', 'due_date', 'description'])
    for r in rows:
        cw.writerow(r)
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=invoices.csv"})


@app.route('/delete_invoice/<int:id>', methods=['POST'])
@login_required
def delete_invoice(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM invoices WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Invoice deleted', 'success')
    return redirect(url_for('billing'))


@app.route('/report', methods=['GET'])
@login_required
def report():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM patients')
    total_patients = cursor.fetchone()[0]
    cursor.execute(COUNT_DOCTORS_QUERY)
    total_doctors = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM appointments')
    total_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM invoices WHERE status='Paid'")
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM invoices WHERE status!='Paid'")
    total_unpaid = cursor.fetchone()[0] or 0
    conn.close()
    return render_template('report.html', totals={
        'patients': total_patients,
        'doctors': total_doctors,
        'appointments': total_appointments,
        'revenue': total_revenue,
        'unpaid': total_unpaid
    })


@app.route('/export_patients', methods=['GET'])
@login_required
def export_patients():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, age, gender, disease FROM patients')
    rows = cursor.fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'name', 'age', 'gender', 'disease'])
    for r in rows:
        cw.writerow(r)
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=patients.csv"})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
