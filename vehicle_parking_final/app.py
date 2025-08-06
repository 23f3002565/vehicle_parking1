from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
from models.user_model import init_db, add_user, check_user
from models.slot_model import init_slot_db, add_slot, get_all_slots, delete_slot, get_lot_slot_counts, get_lot_slot_summary
from models.booking_model import init_booking_db, add_booking, get_user_bookings, release_booking

app = Flask(__name__)
app.secret_key = 'secret123'

#  Seed admin user
def seed_admin():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("SELECT * FROM users WHERE username = ?", ('admin',))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", ('admin', 'admin123', 1))
            conn.commit()
    conn.close()

#  Initialize databases and seed admin
init_db()
init_slot_db()
init_booking_db()
seed_admin()

# ---------------- PUBLIC ROUTES ----------------

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
            session['is_admin'] = user[3] if len(user) > 3 else 0
            if session['is_admin']:
                return redirect('/admin/dashboard')
            else:
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
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, l.name, s.location, s.status,
               b.vehicle_number, u.username, b.start_time
        FROM slots s
        JOIN parking_lots l ON s.lot_id = l.id
        LEFT JOIN bookings b ON s.id = b.slot_id AND b.end_time IS NULL
        LEFT JOIN users u ON b.user_email = u.username
    ''')
    slots = cur.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', slots=slots)

@app.route('/admin/add_slot', methods=['GET', 'POST'])
def admin_add_slot():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    if request.method == 'POST':
        lot_id = request.form['lot_id']
        location = request.form['location']
        time = request.form['time']
        cur.execute("INSERT INTO slots (lot_id, location, time) VALUES (?, ?, ?)", (lot_id, location, time))
        conn.commit()
        conn.close()
        flash('Slot added!')
        return redirect('/admin/dashboard')

    cur.execute("SELECT * FROM parking_lots")
    lots = cur.fetchall()
    conn.close()
    return render_template('add_slot.html', lots=lots)

@app.route('/admin/delete_slot/<int:slot_id>')
def admin_delete_slot(slot_id):
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    delete_slot(slot_id)
    flash('Slot deleted.')
    return redirect('/admin/dashboard')

@app.route('/admin/all_bookings')
def all_bookings():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT b.id, u.username, b.slot_id, b.vehicle_number, b.start_time, b.end_time, b.cost
        FROM bookings b
        JOIN users u ON b.user_email = u.username
        ORDER BY b.id DESC
    ''')
    all_bookings = cur.fetchall()
    conn.close()
    return render_template('all_bookings.html', bookings=all_bookings)

@app.route('/admin/users')
def view_users():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT id, username, is_admin FROM users')
    users = cur.fetchall()
    conn.close()
    return render_template('view_users.html', users=users)

@app.route('/admin/lots', methods=['GET', 'POST'])
def manage_lots():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if request.method == 'POST':
        lot_name = request.form['lot_name']
        price = request.form['price']
        num_spots = int(request.form['num_spots'])
        cur.execute("INSERT INTO parking_lots (name, price) VALUES (?, ?)", (lot_name, price))
        lot_id = cur.lastrowid
        for i in range(num_spots):
            cur.execute("INSERT INTO slots (lot_id, location, time, status) VALUES (?, ?, ?, 'A')", (lot_id, f"Spot {i+1}", "",))
        conn.commit()

    conn.close()

    lot_data = get_lot_slot_counts()
    return render_template('manage_lots.html', lot_data=lot_data)

@app.route('/admin/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM slots WHERE lot_id = ? AND status = 'O'", (lot_id,))
    occupied_count = cur.fetchone()[0]
    if occupied_count > 0:
        conn.close()
        flash('Cannot delete lot: Some slots are occupied!')
        return redirect('/admin/lots')

    cur.execute("DELETE FROM slots WHERE lot_id = ?", (lot_id,))
    cur.execute("DELETE FROM parking_lots WHERE id = ?", (lot_id,))
    conn.commit()
    conn.close()

    flash('Parking lot and its slots deleted.')
    return redirect('/admin/lots')

@app.route('/admin/lot_summary')
def lot_summary():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    summary = get_lot_slot_summary()
    return render_template('lot_summary.html', summary=summary)

@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    if request.method == 'POST':
        lot_name = request.form['lot_name']
        price = request.form['price']
        cur.execute("UPDATE parking_lots SET name = ?, price = ? WHERE id = ?", (lot_name, price, lot_id))
        conn.commit()
        conn.close()
        flash('Lot updated!')
        return redirect('/admin/lots')
    cur.execute("SELECT name, price FROM parking_lots WHERE id = ?", (lot_id,))
    lot = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM slots WHERE lot_id = ?", (lot_id,))
    spot_count = cur.fetchone()[0]
    conn.close()
    return render_template('edit_lot.html', lot=lot, lot_id=lot_id, spot_count=spot_count)

@app.route('/admin/edit_lot/<int:lot_id>/spots', methods=['POST'])
def edit_lot_spots(lot_id):
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    new_spots = int(request.form['new_spots'])
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM slots WHERE lot_id = ?", (lot_id,))
    current_spots = cur.fetchone()[0]
    if new_spots > current_spots:
        # Add new slots
        for i in range(current_spots + 1, new_spots + 1):
            cur.execute("INSERT INTO slots (lot_id, location, time, status) VALUES (?, ?, ?, 'A')", (lot_id, f"Spot {i}", "",))
    elif new_spots < current_spots:
        # Remove slots (only those that are available)
        cur.execute("SELECT id FROM slots WHERE lot_id = ? AND status = 'A' ORDER BY id DESC LIMIT ?", (lot_id, current_spots - new_spots))
        slots_to_delete = cur.fetchall()
        for slot in slots_to_delete:
            cur.execute("DELETE FROM slots WHERE id = ?", (slot[0],))
    conn.commit()
    conn.close()
    flash('Number of spots updated!')
    return redirect(f'/admin/edit_lot/{lot_id}')

# ---------------- USER ROUTES ----------------

@app.route('/user/book', methods=['GET', 'POST'])
def book_slot():
    if 'username' not in session:
        flash("Please login first!")
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM parking_lots")
    lots = cur.fetchall()
    if request.method == 'POST':
        lot_id = request.form['lot_id']
        vehicle_number = request.form['vehicle_number']
        # Find first available slot in the selected lot
        cur.execute("SELECT id FROM slots WHERE lot_id = ? AND status = 'A' ORDER BY id ASC LIMIT 1", (lot_id,))
        slot = cur.fetchone()
        if not slot:
            conn.close()
            flash('No available slots in this lot!')
            return redirect('/user/book')
        slot_id = slot[0]
        conn.close()
        add_booking(session['username'], slot_id, vehicle_number)
        flash('Slot booked successfully!')
        return redirect('/user/bookings')
    conn.close()
    return render_template('book_slot.html', lots=lots)

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

@app.route('/check')
def check():
    return f"SESSION = {dict(session)}"

# ---------------- RUN ----------------

if __name__ == '__main__':
    app.run(debug=True)
