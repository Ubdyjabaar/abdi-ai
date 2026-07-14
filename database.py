import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "abdi_ai.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            event_date TEXT,
            event_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_task(user_id: int, title: str, description: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
        (user_id, title, description)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def get_tasks(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, description, completed FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def delete_task(task_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def complete_task(task_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def add_event(user_id: int, title: str, event_date: str = None, event_time: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (user_id, title, event_date, event_time) VALUES (?, ?, ?, ?)",
        (user_id, title, event_date, event_time)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id

def get_events(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, event_date, event_time FROM events WHERE user_id = ? ORDER BY event_date ASC",
        (user_id,)
    )
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events
