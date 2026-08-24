from datetime import datetime, timedelta

from database import get_results
from predictor import predict


# ============================================================
# LẤY DANH SÁCH NGÀY CÓ DỮ LIỆU
# ============================================================

def get_dates():

    rows = get_results()

    dates = sorted(
        set(row[0] for row in rows)
    )

    return dates


# ============================================================
# TEST 1 NGÀY
# ============================================================

def test_single_date(prediction_date):

    try:
        target = datetime.strptime(
            prediction_date,
            "%Y-%m-%d"
        )
    except ValueError:
        raise ValueError(
            f"Ngày không hợp lệ: {prediction_date}"
        )

    target_date = (
        target + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    print("")
    print("=" * 60)
    print("BACKTEST")
    print(f"Ngày dự đoán : {prediction_date}")
    print(f"Ngày kiểm tra: {target_date}")

    # ========================================================
    # LẤY DATABASE
    # ========================================================

    rows = get_results()

    print(
        f"Database có {len(rows)} dòng."
    )

    # ========================================================
    # TÌM KẾT QUẢ THỰC TẾ
    # ========================================================

    actual_row = None

    for row in rows:

        if row[0] == target_date:

            actual_row = row
            break

    # ========================================================
    # CHƯA CÓ KẾT QUẢ
    # ========================================================

    if actual_row is None:

        print(
            f"NO_RESULT: chưa có dữ liệu {target_date}"
        )

        return {
            "prediction_date": prediction_date,
            "target_date": target_date,
            "status": "NO_RESULT"
        }

    # ========================================================
    # DATABASE STRUCTURE
    #
    # row[0] = date
    # row[1] = special
    # row[2] = special_last2
    # row[3] = day_of_week
    # ========================================================

    special = str(
        actual_row[1]
    ).zfill(5)

    actual = str(
        actual_row[2]
    ).zfill(2)

    print(
        f"Actual ĐB     : {special}"
    )

    print(
        f"Actual 2 số   : {actual}"
    )

    # ========================================================
    # DỰ ĐOÁN
    # ========================================================

    predictions = predict(
        target_date,
        top_n=10
    )

    if not predictions:

        raise ValueError(
            "predict() không trả về kết quả."
        )

    numbers = [
        str(number).zfill(2)
        for number, score in predictions
    ]

    print(
        "Predictions    : "
        + ", ".join(numbers)
    )

    # ========================================================
    # SO SÁNH
    # ========================================================

    hit = actual in numbers

    rank = None

    if hit:

        rank = numbers.index(actual) + 1

    print(
        f"Hit            : {hit}"
    )

    print(
        f"Rank           : {rank}"
    )

    # ========================================================
    # IN CHI TIẾT TOP 10
    # ========================================================

    print("")
    print("TOP 10:")

    for index, (number, score) in enumerate(
        predictions,
        start=1
    ):

        print(
            f"{index:2d}. "
            f"{str(number).zfill(2)} "
            f"| score={score:.4f}"
        )

    print("=" * 60)

    return {
        "prediction_date": prediction_date,
        "target_date": target_date,
        "status": "OK",
        "actual": actual,
        "special": special,
        "predictions": predictions,
        "hit": hit,
        "rank": rank
    }


# ============================================================
# BACKTEST N NGÀY
# ============================================================

def run_backtest(days=30):

    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30

    if days <= 0:
        days = 30

    dates = get_dates()

    if not dates:

        print(
            "BACKTEST: database không có dữ liệu."
        )

        return []

    # ========================================================
    # CHỈ TEST NHỮNG NGÀY MÀ NGÀY SAU CÓ KẾT QUẢ
    # ========================================================

    available_dates = set(dates)

    valid_dates = []

    for date in dates:

        try:

            dt = datetime.strptime(
                date,
                "%Y-%m-%d"
            )

        except ValueError:

            print(
                f"BACKTEST: bỏ qua ngày lỗi {date}"
            )

            continue

        next_date = (
            dt + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        if next_date in available_dates:

            valid_dates.append(date)

    if not valid_dates:

        print(
            "BACKTEST: không có cặp ngày hợp lệ."
        )

        return []

    # ========================================================
    # LẤY N NGÀY GẦN NHẤT
    # ========================================================

    valid_dates.sort(
        reverse=True
    )

    test_dates = valid_dates[:days]

    # Chạy từ cũ -> mới
    test_dates.sort()

    print("")
    print("#" * 60)
    print(
        f"BACKTEST BẮT ĐẦU: {len(test_dates)} ngày"
    )
    print("#" * 60)

    results = []

    for date in test_dates:

        try:

            result = test_single_date(
                date
            )

            if result.get("status") == "OK":

                results.append(result)

        except Exception as e:

            print("")
            print(
                f"BACKTEST ERROR {date}: "
                f"{repr(e)}"
            )

    print("")
    print("#" * 60)
    print(
        f"BACKTEST KẾT THÚC: {len(results)} ngày"
    )
    print("#" * 60)

    return results


# ============================================================
# SUMMARY
# ============================================================

def summarize(results):

    if not results:

        return {}

    total = len(results)

    hits = sum(
        1
        for result in results
        if result.get("hit") is True
    )

    top1 = 0
    top3 = 0
    top5 = 0
    top10 = 0

    for result in results:

        rank = result.get("rank")

        if rank is None:
            continue

        if rank <= 1:
            top1 += 1

        if rank <= 3:
            top3 += 1

        if rank <= 5:
            top5 += 1

        if rank <= 10:
            top10 += 1

    summary = {
        "days": total,
        "hits": hits,
        "hit_rate": hits / total,
        "top1": top1 / total,
        "top3": top3 / total,
        "top5": top5 / total,
        "top10": top10 / total
    }

    print("")
    print("=" * 60)
    print("BACKTEST SUMMARY")
    print("=" * 60)
    print(f"Days   : {total}")
    print(f"Hits   : {hits}")
    print(
        f"Hit    : {summary['hit_rate'] * 100:.2f}%"
    )
    print(
        f"Top 1  : {summary['top1'] * 100:.2f}%"
    )
    print(
        f"Top 3  : {summary['top3'] * 100:.2f}%"
    )
    print(
        f"Top 5  : {summary['top5'] * 100:.2f}%"
    )
    print(
        f"Top 10 : {summary['top10'] * 100:.2f}%"
    )
    print("=" * 60)

    return summary
