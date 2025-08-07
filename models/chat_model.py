import sqlite3
from datetime import datetime

def init_chat_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    # Create chat messages table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def add_message(username, message, is_admin=0):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO chat_messages (username, message, is_admin)
        VALUES (?, ?, ?)
    ''', (username, message, is_admin))
    
    conn.commit()
    message_id = cur.lastrowid
    conn.close()
    return message_id

def get_recent_messages(limit=50):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    cur.execute('''
        SELECT username, message, timestamp, is_admin
        FROM chat_messages
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    messages = cur.fetchall()
    conn.close()
    return list(reversed(messages))

def get_online_users():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    cur.execute('''
        SELECT DISTINCT username, is_admin
        FROM chat_messages
        WHERE timestamp >= datetime('now', '-1 hour')
        ORDER BY username
    ''')
    
    users = cur.fetchall()
    conn.close()
    return users