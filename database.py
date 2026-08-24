def save_result(rec):
    sp = str(rec["special"]).strip()
    last2 = sp[-2:]

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
