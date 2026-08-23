import sqlite3
import os
from datetime import datetime

from config import DATABASE_PATH


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    return sqlite3.connect(DATABASE_PATH)


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            special TEXT NOT NULL,
            special_last2 TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_result(date, special):
    special = str(special).zfill(5)
    last2 = special[-2:]

    dt = datetime.strptime(date, "%Y-%m-%d")

    conn = get_connection()

    conn.execute("""
        INSERT OR REPLACE INTO results
        (date, special, special_last2, day_of_week, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        date,
        special,
        last2,
        dt.weekday(),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_results(limit=None):
    conn = get_connection()

    if limit:
        rows = conn.execute("""
            SELECT date, special, special_last2, day_of_week
            FROM results
            ORDER BY date DESC
            LIMIT ?
        """, (limit,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT date, special, special_last2, day_of_week
            FROM results
            ORDER BY date DESC
        """).fetchall()

    conn.close()

    return rows


def get_result(date):
    conn = get_connection()

    row = conn.execute("""
        SELECT date, special, special_last2, day_of_week
        FROM results
        WHERE date = ?
    """, (date,)).fetchone()

    conn.close()

    return row


def count_results():
    conn = get_connection()

    result = conn.execute(
        "SELECT COUNT(*) FROM results"
    ).fetchone()[0]

    conn.close()

    return result
