import sqlite3
from datetime import datetime

def init_booking_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            slot_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            cost REAL
        )
    ''')
    conn.commit()
    conn.close()

def add_booking(user_email, slot_id, vehicle_number):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('''
        INSERT INTO bookings (user_email, slot_id, vehicle_number, start_time)
        VALUES (?, ?, ?, ?)
    ''', (user_email, slot_id, vehicle_number, start_time))
    cur.execute("UPDATE slots SET status = 'O' WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()

def release_booking(booking_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Step 1: Get slot_id and start_time from bookings
    cur.execute("SELECT slot_id, start_time FROM bookings WHERE id = ?", (booking_id,))
    result = cur.fetchone()
    if not result:
        print(f"⚠️ Booking ID {booking_id} not found.")
        conn.close()
        return

    slot_id, start_time = result

    # Step 2: Mark slot as available
    cur.execute("UPDATE slots SET status = 'A' WHERE id = ?", (slot_id,))

    # Step 3: Get lot_id from slots
    cur.execute("SELECT lot_id FROM slots WHERE id = ?", (slot_id,))
    lot_result = cur.fetchone()
    if not lot_result:
        print(f"⚠️ Slot ID {slot_id} not found.")
        conn.close()
        return
    lot_id = lot_result[0]

    # Step 4: Get price from parking_lots
    cur.execute("SELECT price FROM parking_lots WHERE id = ?", (lot_id,))
    price_result = cur.fetchone()
    if not price_result:
        print(f"⚠️ Lot ID {lot_id} not found.")
        conn.close()
        return
    price = price_result[0]

    # Step 5: Compute cost
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    hours = max(1, int((end_dt - start_dt).total_seconds() // 3600))
    cost = price * hours

    # Step 6: Update booking record
    cur.execute("UPDATE bookings SET end_time = ?, cost = ? WHERE id = ?", (end_time, cost, booking_id))

    conn.commit()
    conn.close()

def get_user_bookings(user_email):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT id, slot_id, vehicle_number, start_time, end_time, cost
        FROM bookings
        WHERE user_email = ?
        ORDER BY id DESC
    ''', (user_email,))
    bookings = cur.fetchall()
    conn.close()
    return bookings

