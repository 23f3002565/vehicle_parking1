import sqlite3

def init_slot_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Create parking_lots table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL DEFAULT 20
        )
    ''')

    # Create slots table linked to parking_lots
    cur.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER,
            location TEXT,
            time TEXT,
            FOREIGN KEY (lot_id) REFERENCES parking_lots(id)
        )
    ''')

    conn.commit()
    conn.close()

# Add a new parking lot
def add_parking_lot(name):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO parking_lots (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

# Get all parking lots
def get_all_lots():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM parking_lots')
    lots = cur.fetchall()
    conn.close()
    return lots

# Add a slot under a specific lot
def add_slot(lot_id, location, time):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO slots (lot_id, location, time) VALUES (?, ?, ?)', (lot_id, location, time))
    conn.commit()
    conn.close()

# Get all slots with lot info
def get_all_slots():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT slots.id, parking_lots.name, slots.location, slots.time
        FROM slots
        JOIN parking_lots ON slots.lot_id = parking_lots.id
        ORDER BY slots.id DESC
    ''')
    slots = cur.fetchall()
    conn.close()
    return slots

# Delete slot
def delete_slot(slot_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM slots WHERE id = ?', (slot_id,))
    conn.commit()
    conn.close()

def get_lot_slot_counts():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT parking_lots.id, parking_lots.name, parking_lots.price, COUNT(slots.id) as slot_count
        FROM parking_lots
        LEFT JOIN slots ON parking_lots.id = slots.lot_id
        GROUP BY parking_lots.id
    ''')
    result = cur.fetchall()
    conn.close()
    return result

def get_lot_slot_summary():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT parking_lots.name, COUNT(slots.id) as slot_count, parking_lots.price
        FROM parking_lots
        LEFT JOIN slots ON slots.lot_id = parking_lots.id
        GROUP BY parking_lots.id
    ''')
    data = cur.fetchall()
    conn.close()
    return data