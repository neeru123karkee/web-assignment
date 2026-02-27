from flask import Flask, render_template, redirect, url_for, flash, session, request
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Doctor, Appointment
from datetime import datetime
from config import Config
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ---------------- Create Tables ----------------
with app.app_context():
    db.create_all()

# ---------------- Decorators ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Admins only!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Home ----------------
@app.route('/')
def home():
    doctors = Doctor.query.all()
    return render_template('index.html', doctors=doctors)

# ---------------- Register ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        user = User(name=name, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------------- Login ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard') if session.get('is_admin') else url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Role check
            if role == 'admin' and not user.is_admin:
                flash("This account is not an admin.", "danger")
                return redirect(url_for('login'))
            if role == 'user' and user.is_admin:
                flash("Please select Admin login for this account.", "warning")
                return redirect(url_for('login'))

            # Set session
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin

            flash(f"Welcome, {user.name}!", "success")
            return redirect(url_for('admin_dashboard') if user.is_admin else url_for('dashboard'))

        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# ---------------- User Dashboard ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    doctors = Doctor.query.all()
    return render_template('dashboard.html', doctors=doctors)

# ---------------- Admin Dashboard ----------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_doctors = Doctor.query.count()
    total_patients = User.query.filter_by(is_admin=False).count()
    total_appointments = Appointment.query.count()
    upcoming_appointments = Appointment.query.order_by(Appointment.date, Appointment.time).limit(5).all()

    return render_template(
        'admin_dashboard.html',
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        upcoming_appointments=upcoming_appointments
    )

# ---------------- Admin: View Doctors ----------------
@app.route('/admin/doctors')
@admin_required
def admin_doctors():
    doctors = Doctor.query.all()
    return render_template('admin_doctors.html', doctors=doctors)

# ---------------- Admin: View Patients ----------------
@app.route('/admin/patients')
@admin_required
def admin_patients():
    patients = User.query.filter_by(is_admin=False).all()
    return render_template('admin_patients.html', patients=patients)

# ---------------- Admin: View Appointments ----------------
@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    appointments = Appointment.query.order_by(Appointment.date, Appointment.time).all()
    return render_template('admin_appointments.html', appointments=appointments)

# ---------------- Book Appointment ----------------
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    doctors = Doctor.query.all()
    preselected_doctor_id = request.args.get('doctor_id', type=int)

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')

        if not doctor_id or not date_str or not time_str:
            flash("Please fill all fields.", "danger")
            return redirect(request.url)

        # Convert date and time strings to Python objects
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%I:%M %p').time()

        # Check if slot already booked
        if Appointment.query.filter_by(doctor_id=doctor_id, date=date_obj, time=time_obj).first():
            flash("This time slot is already booked. Please choose another.", "danger")
            return redirect(request.url)

        appointment = Appointment(
            user_id=session['user_id'],
            doctor_id=doctor_id,
            date=date_obj,
            time=time_obj
        )
        db.session.add(appointment)
        db.session.commit()
        flash("Appointment booked successfully!", "success")
        return redirect(url_for('appointments'))

    return render_template('book_appointment.html', doctors=doctors, preselected_doctor_id=preselected_doctor_id)

# ---------------- View Appointments ----------------
@app.route('/appointments')
@login_required
def appointments():
    user_appts = Appointment.query.filter_by(user_id=session['user_id']).order_by(Appointment.date, Appointment.time).all()
    return render_template('appointments.html', appointments=user_appts)

# ---------------- Edit Appointment ----------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_appointment(id):
    appt = Appointment.query.get_or_404(id)
    if appt.user_id != session['user_id']:
        flash("You cannot edit this appointment.", "danger")
        return redirect(url_for('appointments'))

    if request.method == 'POST':
        date_str = request.form['date']
        time_str = request.form['time']

        # Convert date and time
        appt.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appt.time = datetime.strptime(time_str, '%I:%M %p').time()

        db.session.commit()
        flash('Appointment updated successfully!', 'success')
        return redirect(url_for('appointments'))

    return render_template('edit_appointment.html', appt=appt)

# ---------------- Delete Appointment ----------------
@app.route('/delete/<int:id>')
@login_required
def delete_appointment(id):
    appt = Appointment.query.get_or_404(id)
    if appt.user_id != session['user_id']:
        flash("You cannot delete this appointment.", "danger")
        return redirect(url_for('appointments'))

    db.session.delete(appt)
    db.session.commit()
    flash('Appointment deleted successfully!', 'success')
    return redirect(url_for('appointments'))

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)