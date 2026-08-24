import sqlite3
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE_PATH

_db_lock = threading.Lock()


def _tojson(obj):
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return json.dumps({})


def _fromjson(s):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


@contextmanager
def get_conn():
    # check_same_thread=False to allow use from different threads
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        # Improve concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
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
        int(datetime.strptime(rec["date"], "%Y-%m-%d").weekday()) if rec.get("date") else 0
    )

    now = datetime.now().isoformat(timespec="seconds")

    with _db_lock:  # serialize writes to avoid SQLITE_BUSY
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
                rec.get("date"),
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


def get_results(limit=100, offset=0):
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM results ORDER BY date DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            # parse json fields
            for k in ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "loto_head", "all_numbers"):
                if r.get(k) and isinstance(r[k], str):
                    r[k] = _fromjson(r[k])
        return rows


def get_date_range():
    with get_conn() as conn:
        cur = conn.execute("SELECT MIN(date) as min_d, MAX(date) as max_d FROM results")
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)


def count_results():
    with get_conn() as conn:
        cur = conn.execute("SELECT COUNT(1) FROM results")
        return cur.fetchone()[0]
