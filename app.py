from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta
from models.user_model import init_db, add_user, check_user
from models.slot_model import init_slot_db, add_slot, get_all_slots, delete_slot, get_lot_slot_counts, get_lot_slot_summary
from models.booking_model import init_booking_db, add_booking, get_user_bookings, release_booking
from flask_socketio import SocketIO, emit, join_room, leave_room
from models.chat_model import init_chat_db, add_message, get_recent_messages, get_online_users
import json

app = Flask(__name__)
app.secret_key = 'secret123'
socketio = SocketIO(app, cors_allowed_origins="*")

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
init_chat_db()
seed_admin()

# ---------------- PUBLIC ROUTES ----------------

# Add new route for home page with statistics
@app.route('/')
def home():
    # Get statistics for the home page
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    # Get total lots
    cur.execute("SELECT COUNT(*) FROM parking_lots")
    total_lots = cur.fetchone()[0]
    
    # Get total slots
    cur.execute("SELECT COUNT(*) FROM slots")
    total_slots = cur.fetchone()[0]
    
    # Get total users (excluding admin)
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    total_users = cur.fetchone()[0]
    
    # Get total bookings
    cur.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cur.fetchone()[0]
    
    conn.close()
    
    stats = {
        'total_lots': total_lots,
        'total_slots': total_slots,
        'total_users': total_users,
        'total_bookings': total_bookings
    }
    
    return render_template('home.html', stats=stats)

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
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    # Get user's active bookings
    cur.execute('''
        SELECT b.id, l.name, s.location, b.vehicle_number, b.start_time, b.cost
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN parking_lots l ON s.lot_id = l.id
        WHERE b.user_email = ? AND b.end_time IS NULL
    ''', (session['username'],))
    active_bookings = cur.fetchall()
    
    # Get available slots count
    cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'A'")
    available_slots = cur.fetchone()[0]
    
    # Get user's total bookings
    cur.execute("SELECT COUNT(*) FROM bookings WHERE user_email = ?", (session['username'],))
    total_bookings = cur.fetchone()[0]
    
    # Get recent parking lots
    cur.execute("SELECT id, name, price FROM parking_lots LIMIT 5")
    recent_lots = cur.fetchall()
    
    conn.close()
    
    # Change this line to use your existing template
    return render_template('dashboard.html', 
                         username=session['username'],
                         active_bookings=active_bookings,
                         available_slots=available_slots,
                         total_bookings=total_bookings,
                         recent_lots=recent_lots)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect('/')

# ---------------- ADMIN ROUTES ----------------

# Enhanced admin dashboard with more statistics
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    # Get all slots with detailed information
    cur.execute('''
        SELECT s.id, l.name, s.location, s.status,
               b.vehicle_number, u.username, b.start_time, b.cost
        FROM slots s
        JOIN parking_lots l ON s.lot_id = l.id
        LEFT JOIN bookings b ON s.id = b.slot_id AND b.end_time IS NULL
        LEFT JOIN users u ON b.user_email = u.username
        ORDER BY l.name, s.location
    ''')
    slots = cur.fetchall()
    
    # Get dashboard statistics
    cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'A'")
    available_slots = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'O'")
    occupied_slots = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM bookings WHERE end_time IS NULL")
    active_bookings = cur.fetchone()[0]
    
    cur.execute("SELECT SUM(cost) FROM bookings WHERE DATE(start_time) = DATE('now')")
    today_revenue = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    total_users = cur.fetchone()[0]
    
    conn.close()
    
    stats = {
        'available_slots': available_slots,
        'occupied_slots': occupied_slots,
        'active_bookings': active_bookings,
        'today_revenue': today_revenue,
        'total_users': total_users
    }
    
    # Change this line to use your existing template
    return render_template('admin_dashboard.html', slots=slots, stats=stats)

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

# Add profile route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash("Please login first!")
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    if request.method == 'POST':
        # Update user profile
        new_password = request.form.get('new_password')
        if new_password:
            cur.execute("UPDATE users SET password = ? WHERE username = ?", 
                       (new_password, session['username']))
            conn.commit()
            flash('Profile updated successfully!')
    
    # Get user info
    cur.execute("SELECT * FROM users WHERE username = ?", (session['username'],))
    user = cur.fetchone()
    
    # Get user statistics
    cur.execute("SELECT COUNT(*) FROM bookings WHERE user_email = ?", (session['username'],))
    total_bookings = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM bookings WHERE user_email = ? AND end_time IS NULL", 
               (session['username'],))
    active_bookings = cur.fetchone()[0]
    
    conn.close()
    
    user_stats = {
        'total_bookings': total_bookings,
        'active_bookings': active_bookings
    }
    
    return render_template('profile.html', user=user, stats=user_stats)

# Add API endpoint for real-time updates
@app.route('/api/dashboard-stats')
def dashboard_stats():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    if session.get('is_admin'):
        # Admin stats
        cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'A'")
        available_slots = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'O'")
        occupied_slots = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM bookings WHERE end_time IS NULL")
        active_bookings = cur.fetchone()[0]
        
        cur.execute("SELECT SUM(cost) FROM bookings WHERE DATE(start_time) = DATE('now')")
        today_revenue = cur.fetchone()[0] or 0
        
        stats = {
            'available_slots': available_slots,
            'occupied_slots': occupied_slots,
            'active_bookings': active_bookings,
            'today_revenue': today_revenue
        }
    else:
        # User stats
        cur.execute("SELECT COUNT(*) FROM bookings WHERE user_email = ? AND end_time IS NULL", 
                   (session['username'],))
        active_bookings = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM slots WHERE status = 'A'")
        available_slots = cur.fetchone()[0]
        
        stats = {
            'active_bookings': active_bookings,
            'available_slots': available_slots
        }
    
    conn.close()
    return jsonify(stats)

# Add notification system
@app.route('/api/notifications')
def get_notifications():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    notifications = []
    
    if session.get('is_admin'):
        # Admin notifications
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        
        # Check for overdue bookings (example: more than 24 hours)
        cur.execute('''
            SELECT COUNT(*) FROM bookings 
            WHERE end_time IS NULL AND 
            datetime('now') > datetime(start_time, '+24 hours')
        ''')
        overdue_count = cur.fetchone()[0]
        
        if overdue_count > 0:
            notifications.append({
                'type': 'warning',
                'message': f'{overdue_count} overdue booking(s) found',
                'action': '/admin/all_bookings'
            })
        
        conn.close()
    
    return jsonify(notifications)

# ---------------- CHAT ROUTES ----------------

@app.route('/chat')
def chat():
    if 'username' not in session:
        flash("Please login to access chat!")
        return redirect('/login')
    
    messages = get_recent_messages()
    online_users = get_online_users()
    
    return render_template('chat.html', 
                         messages=messages, 
                         online_users=online_users,
                         current_user=session['username'],
                         is_admin=session.get('is_admin', 0))

@app.route('/api/chat/messages')
def get_chat_messages():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    messages = get_recent_messages()
    return jsonify([{
        'username': msg[0],
        'message': msg[1],
        'timestamp': msg[2],
        'is_admin': msg[3]
    } for msg in messages])

# SocketIO Events
@socketio.on('connect')
def on_connect():
    if 'username' in session:
        join_room('general_chat')
        emit('status', {
            'msg': f"{session['username']} has entered the chat.",
            'username': session['username'],
            'is_admin': session.get('is_admin', 0)
        }, room='general_chat')

@socketio.on('disconnect')
def on_disconnect():
    if 'username' in session:
        leave_room('general_chat')
        emit('status', {
            'msg': f"{session['username']} has left the chat.",
            'username': session['username']
        }, room='general_chat')

@socketio.on('message')
def handle_message(data):
    if 'username' not in session:
        return
    
    username = session['username']
    message = data['message']
    is_admin = session.get('is_admin', 0)
    
    # Save to database
    add_message(username, message, is_admin)
    
    # Broadcast to all users
    emit('message', {
        'username': username,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'is_admin': is_admin
    }, room='general_chat')

# ---------------- RUN ----------------

# Replace the existing if __name__ == '__main__': section with this
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)