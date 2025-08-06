#!/bin/bash

echo "🧹 Deleting old database files..."
rm -f users.db bookings.db slots.db database.db

echo "📁 Creating models directory..."
mkdir -p models

echo "📄 Creating user_model.py..."
cat > models/user_model.py << 'EOF'
import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def check_user(username, password):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = cur.fetchone()
    conn.close()
    return user
EOF

echo "📄 Creating slot_model.py..."
cat > models/slot_model.py << 'EOF'
import sqlite3

def init_slot_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_slot(location, time):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO slots (location, time) VALUES (?, ?)', (location, time))
    conn.commit()
    conn.close()

def get_all_slots():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM slots')
    slots = cur.fetchall()
    conn.close()
    return slots

def delete_slot(slot_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM slots WHERE id = ?', (slot_id,))
    conn.commit()
    conn.close()
EOF

echo "📄 Creating booking_model.py..."
cat > models/booking_model.py << 'EOF'
import sqlite3
from datetime import datetime

def init_booking_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            slot_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            booking_time TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_booking(username, slot_id, vehicle_number):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO bookings (username, slot_id, vehicle_number) VALUES (?, ?, ?)', 
                (username, slot_id, vehicle_number))
    conn.commit()
    conn.close()

def get_user_bookings(username):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE username = ?', (username,))
    bookings = cur.fetchall()
    conn.close()
    return bookings

def release_booking(booking_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
EOF

echo "📄 Creating app.py..."
cat > app.py << 'EOF'
from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
from models.user_model import init_db, add_user, check_user
from models.slot_model import init_slot_db, add_slot, get_all_slots, delete_slot
from models.booking_model import init_booking_db, add_booking, get_user_bookings, release_booking

app = Flask(__name__)
app.secret_key = 'secret123'

# ✅ Seed admin user
def seed_admin():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", ('admin', 'admin123', 1))
        conn.commit()
    conn.close()

# 🏁 Initialize databases and seed admin
init_db()
init_slot_db()
init_booking_db()
seed_admin()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if add_user(username, password):
            flash('Registration successful! Please log in.')
            return redirect('/login')
        else:
            flash('Username already taken.')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = check_user(username, password)
        if user:
            session['username'] = username
            session['is_admin'] = user[3]
            return redirect('/dashboard')
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    if session.get('is_admin'):
        return redirect('/admin/dashboard')
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect('/')

# ---------------- ADMIN ROUTES ----------------

@app.route('/admin/dashboard')
def admin_dashboard():
    slots = get_all_slots()
    return render_template('admin_dashboard.html', slots=slots)

@app.route('/admin/add_slot', methods=['GET', 'POST'])
def admin_add_slot():
    if request.method == 'POST':
        location = request.form['location']
        time = request.form['time']
        add_slot(location, time)
        flash('Slot added!')
        return redirect('/admin/dashboard')
    return render_template('add_slot.html')

@app.route('/admin/delete_slot/<int:slot_id>')
def admin_delete_slot(slot_id):
    delete_slot(slot_id)
    flash('Slot deleted.')
    return redirect('/admin/dashboard')

# ---------------- USER ROUTES ----------------

@app.route('/user/book', methods=['GET', 'POST'])
def book_slot():
    if 'username' not in session:
        flash("Please login first!")
        return redirect('/login')
    slots = get_all_slots()
    if request.method == 'POST':
        slot_id = request.form['slot_id']
        vehicle_number = request.form['vehicle_number']
        add_booking(session['username'], slot_id, vehicle_number)
        flash('Slot booked successfully!')
        return redirect('/user/bookings')
    return render_template('book_slot.html', slots=slots)

@app.route('/user/bookings')
def my_bookings():
    if 'username' not in session:
        flash("Please login first!")
        return redirect('/login')
    bookings = get_user_bookings(session['username'])
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/user/release/<int:booking_id>')
def release_slot(booking_id):
    if 'username' not in session:
        flash("Please login first!")
        return redirect('/login')
    release_booking(booking_id)
    flash('Slot released.')
    return redirect('/user/bookings')

EOF

echo "✅ Installing Flask..."
source env/bin/activate && pip install Flask

echo "✅ All done! Now run the app:"
echo "👉 python3 app.py"
