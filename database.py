import os, sqlite3, json
from datetime import datetime
from config import DATABASE_PATH


def get_conn():
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    c = sqlite3.connect(DATABASE_PATH, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                special TEXT NOT NULL,
                special_last2 TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                g1 TEXT NOT NULL, g2 TEXT NOT NULL, g3 TEXT NOT NULL,
                g4 TEXT NOT NULL, g5 TEXT NOT NULL, g6 TEXT NOT NULL, g7 TEXT NOT NULL,
                loto_head TEXT NOT NULL,
                all_numbers TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def _tojson(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def save_result(rec):
    sp = rec["special"]
    last2 = sp[-2:]
    def norm(arr): return list(arr) if isinstance(arr,(list,tuple)) else []
    g1,g2,g3,g4,g5,g6,g7 = map(norm,[rec.get(k,[]) for k in "g1 g2 g3 g4 g5 g6 g7".split()])
    tails = [n[-2:] for n in ([sp]+g1+g2+g3+g4+g5+g6+g7) if isinstance(n,str) and len(n)>=2]
    all_dump = _tojson({"full5": [sp]+g1+g2+g3+g4+g5+g6+g7, "tails2": tails})
    dow = rec.get("weekday", datetime.strptime(rec["date"],"%Y-%m-%d").weekday())
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO results
            (date,special,special_last2,day_of_week,g1,g2,g3,g4,g5,g6,g7,loto_head,all_numbers,created_at)
            VALUES (?,?,?,?, ?,?,?,?,?,?,?, ?,?,?)
            ON CONFLICT(date) DO UPDATE SET
                special=excluded.special, special_last2=excluded.special_last2,
                day_of_week=excluded.day_of_week,
                g1=excluded.g1,g2=excluded.g2,g3=excluded.g3,g4=excluded.g4,
                g5=excluded.g5,g6=excluded.g6,g7=excluded.g7,
                loto_head=excluded.loto_head, all_numbers=excluded.all_numbers, created_at=excluded.created_at
        """, (rec["date"], sp, last2, dow,
              _tojson(g1),_tojson(g2),_tojson(g3),_tojson(g4),_tojson(g5),_tojson(g6),_tojson(g7),
              _tojson(rec.get("loto_by_head",{})), all_dump, now))


def get_results(limit=None):
    with get_conn() as c:
        cur = c.cursor()
        sql = "SELECT date,special,special_last2,day_of_week FROM results ORDER BY date DESC"
        if isinstance(limit,int) and limit>0: sql+=" LIMIT ?"; cur.execute(sql,(limit,))
        else: cur.execute(sql)
        return cur.fetchall()


def get_full(date_str):
    with get_conn() as c:
        r = c.execute("""
            SELECT date,special,special_last2,day_of_week,g1,g2,g3,g4,g5,g6,g7,loto_head,all_numbers
            FROM results WHERE date=?
        """,(date_str,)).fetchone()
    if not r: return None
    return {
        "date":r[0],"special":r[1],"special_last2":r[2],"weekday":r[3],
        "g1":json.loads(r[4]),"g2":json.loads(r[5]),"g3":json.loads(r[6]),
        "g4":json.loads(r[7]),"g5":json.loads(r[8]),"g6":json.loads(r[9]),"g7":json.loads(r[10]),
        "loto":json.loads(r[11]),"all":json.loads(r[12])
    }


def count_results():
    with get_conn() as c: return c.execute("SELECT COUNT(*) FROM results").fetchone()[0]
def get_date_range():
    with get_conn() as c: return c.execute("SELECT MIN(date),MAX(date) FROM results").fetchone()


if __name__=="__main__":
    init_db()
    print(f"✅ DB: {DATABASE_PATH} | Tổng: {count_results()} ngày")
