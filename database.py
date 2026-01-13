import sqlite3
import json
import os
from datetime import datetime

# Make path absolute relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "scans.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  target TEXT, 
                  timestamp DATETIME, 
                  result_json TEXT)''')
    conn.commit()
    conn.close()

def add_scan(target, result_dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO scan_history (target, timestamp, result_json) VALUES (?, ?, ?)",
              (target, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(result_dict)))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, target, timestamp, result_json FROM scan_history ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "target": row[1],
            "timestamp": row[2],
            "results": json.loads(row[3])
        })
    return history

def get_scan_by_id(scan_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, target, timestamp, result_json FROM scan_history WHERE id = ?", (scan_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "target": row[1],
            "timestamp": row[2],
            "results": json.loads(row[3])
        }
    return None

def delete_scan(scan_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM scan_history WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
