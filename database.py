import os
import sqlite3
from datetime import datetime

from config import DATABASE_PATH


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    folder = os.path.dirname(
        DATABASE_PATH
    )

    if folder:
        os.makedirs(
            folder,
            exist_ok=True
        )

    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )

    # Tăng độ an toàn khi nhiều thao tác
    # đọc/ghi xảy ra gần nhau.
    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    conn.execute(
        "PRAGMA foreign_keys=ON"
    )

    return conn


# ============================================================
# INIT DATABASE
# ============================================================

def init_db():

    conn = get_connection()

    try:

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

        print(
            f"[DATABASE] Database ready: "
            f"{DATABASE_PATH}"
        )

    finally:

        conn.close()


# ============================================================
# SAVE RESULT
# ============================================================

def save_result(date, special):

    # --------------------------------------------------------
    # Validate date
    # --------------------------------------------------------

    try:

        dt = datetime.strptime(
            date,
            "%Y-%m-%d"
        )

    except ValueError as e:

        raise ValueError(
            f"Ngày không hợp lệ: {date}"
        ) from e

    # --------------------------------------------------------
    # Normalize special
    # --------------------------------------------------------

    special = str(
        special
    ).strip()

    # Chỉ giữ 5 chữ số.
    #
    # Không tự động biến một chuỗi sai thành dữ liệu hợp lệ.
    if not special.isdigit():

        raise ValueError(
            f"Giải đặc biệt không hợp lệ: "
            f"{special}"
        )

    special = special.zfill(5)

    if len(special) != 5:

        raise ValueError(
            f"Giải đặc biệt phải có 5 chữ số: "
            f"{special}"
        )

    last2 = special[-2:]

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    conn = get_connection()

    try:

        conn.execute("""
            INSERT INTO results
            (
                date,
                special,
                special_last2,
                day_of_week,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(date)
            DO UPDATE SET
                special = excluded.special,
                special_last2 = excluded.special_last2,
                day_of_week = excluded.day_of_week,
                created_at = excluded.created_at
        """, (
            date,
            special,
            last2,
            dt.weekday(),
            now
        ))

        conn.commit()

        print(
            f"[DATABASE] Saved: "
            f"{date} -> {special}"
        )

    finally:

        conn.close()


# ============================================================
# GET RESULTS
# ============================================================

def get_results(limit=None):

    conn = get_connection()

    try:

        if limit is not None:

            limit = int(limit)

            if limit <= 0:
                return []

            rows = conn.execute("""
                SELECT
                    date,
                    special,
                    special_last2,
                    day_of_week
                FROM results
                ORDER BY date DESC
                LIMIT ?
            """, (
                limit,
            )).fetchall()

        else:

            rows = conn.execute("""
                SELECT
                    date,
                    special,
                    special_last2,
                    day_of_week
                FROM results
                ORDER BY date DESC
            """).fetchall()

    finally:

        conn.close()

    return rows


# ============================================================
# GET ONE RESULT
# ============================================================

def get_result(date):

    conn = get_connection()

    try:

        row = conn.execute("""
            SELECT
                date,
                special,
                special_last2,
                day_of_week
            FROM results
            WHERE date = ?
        """, (
            date,
        )).fetchone()

    finally:

        conn.close()

    return row


# ============================================================
# COUNT
# ============================================================

def count_results():

    conn = get_connection()

    try:

        result = conn.execute(
            """
            SELECT COUNT(*)
            FROM results
            """
        ).fetchone()

    finally:

        conn.close()

    return result[0]


# ============================================================
# DATABASE INFO
# ============================================================

def get_date_range():

    conn = get_connection()

    try:

        row = conn.execute("""
            SELECT
                MIN(date),
                MAX(date)
            FROM results
        """).fetchone()

    finally:

        conn.close()

    return row


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "[DATABASE] TEST"
    )

    print(
        "========================================"
    )

    init_db()

    print(
        "Database:",
        DATABASE_PATH
    )

    print(
        "Số bản ghi:",
        count_results()
    )

    print(
        "Khoảng ngày:",
        get_date_range()
    )

    print(
        "5 kết quả mới nhất:"
    )

    for row in get_results(5):

        print(
            row
        )

    print(
        "========================================"
        )
