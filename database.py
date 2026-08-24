import os
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", "data.db")


def _tojson(obj):
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return json.dumps(str(obj))


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        yield conn
n    finally:
        conn.commit()
        conn.close()


def init_db():
    """Create the results table if it doesn't exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                date TEXT PRIMARY KEY,
                special TEXT,
                special_last2 TEXT,
                day_of_week INTEGER,
                g1 TEXT,
                g2 TEXT,
                g3 TEXT,
                g4 TEXT,
                g5 TEXT,
                g6 TEXT,
                g7 TEXT,
                loto_head TEXT,
                all_numbers TEXT,
                created_at TEXT
            )
        """)


def get_results(date=None):
    """Return one result dict if date provided, otherwise list of all results (as dicts)."""
    with get_conn() as conn:
        cur = conn.cursor()
        if date:
            cur.execute("SELECT * FROM results WHERE date = ?", (date,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return _row_to_dict(row, cols)
        else:
            cur.execute("SELECT * FROM results ORDER BY date ASC")
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [_row_to_dict(r, cols) for r in rows]


def _row_to_dict(row, cols):
    data = dict(zip(cols, row))
    # try to decode JSON fields
    for k in ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "loto_head", "all_numbers"):
        if data.get(k) is not None:
            try:
                data[k] = json.loads(data[k])
            except Exception:
                pass
    return data


def get_date_range():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(date), MAX(date) FROM results")
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)


def count_results():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM results")
        return cur.fetchone()[0]


# --- Existing save_result kept but adapted to rely on helpers above ---
def save_result(rec):
    sp = str(rec.get("special", "")).strip()
    last2 = sp[-2:] if len(sp) >= 2 else ""

    def norm(arr):
        return list(arr) if isinstance(arr, (list, tuple)) else []

    g1, g2, g3, g4, g5, g6, g7 = map(
        norm,
        [rec.get(k, []) for k in "g1 g2 g3 g4 g5 g6 g7".split()]
    )

    tails = [
        n[-2:]
        for n in ([sp] + g1 + g2 + g3 + g4 + g5 + g6 + g7)
        if isinstance(n, str) and len(n) >= 2
    ]

    all_dump = _tojson({
        "full5": [sp] + g1 + g2 + g3 + g4 + g5 + g6 + g7,
        "tails2": tails
    })

    dow = rec.get(
        "weekday",
        datetime.strptime(rec["date"], "%Y-%m-%d").weekday()
    )

    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO results
            (
                date,
                special,
                special_last2,
                day_of_week,
                g1,g2,g3,g4,g5,g6,g7,
                loto_head,
                all_numbers,
                created_at
            )
            VALUES (
                ?,?,?,?,
                ?,?,?,?,?,?,?,?,
                ?,?,
                ?
            )
            ON CONFLICT(date) DO UPDATE SET
                special=excluded.special,
                special_last2=excluded.special_last2,
                day_of_week=excluded.day_of_week,
                g1=excluded.g1,
                g2=excluded.g2,
                g3=excluded.g3,
                g4=excluded.g4,
                g5=excluded.g5,
                g6=excluded.g6,
                g7=excluded.g7,
                loto_head=excluded.loto_head,
                all_numbers=excluded.all_numbers,
                created_at=excluded.created_at
        """, (
            rec["date"],
            sp,
            last2,
            dow,
            _tojson(g1),
            _tojson(g2),
            _tojson(g3),
            _tojson(g4),
            _tojson(g5),
            _tojson(g6),
            _tojson(g7),
            _tojson(rec.get("loto_by_head", {})),
            all_dump,
            now
        ))

    return True
