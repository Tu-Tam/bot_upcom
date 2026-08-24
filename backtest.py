from datetime import datetime, timedelta

from database import get_results
from predictor import predict


# ============================================================
# GET AVAILABLE DATES
# ============================================================

def get_dates():

    rows = get_results()

    dates = sorted(
        set(row[0] for row in rows)
    )

    return dates


# ============================================================
# TEST SINGLE DATE
# ============================================================

def test_single_date(
    prediction_date
):

    target = datetime.strptime(
        prediction_date,
        "%Y-%m-%d"
    )

    target_date = (
        target + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    rows = get_results()

    actual_row = None

    for row in rows:

        if row[0] == target_date:

            actual_row = row
            break

    # Chưa có kết quả ngày hôm sau
    if actual_row is None:

        return {
            "prediction_date": prediction_date,
            "target_date": target_date,
            "status": "NO_RESULT"
        }

    # ========================================================
    # DATABASE:
    #
    # row[0] = date
    # row[1] = special
    # row[2] = special_last2
    # row[3] = day_of_week
    #
    # Chúng ta chỉ đánh giá 2 số cuối
    # ========================================================

    actual = str(
        actual_row[2]
    ).zfill(2)

    # ========================================================
    # PREDICT
    #
    # predictor.py phải tự đảm bảo rằng chỉ sử dụng
    # dữ liệu trước target_date.
    # ========================================================

    predictions = predict(
        target_date,
        top_n=10
    )

    numbers = [
        str(number).zfill(2)
        for number, score in predictions
    ]

    # ========================================================
    # CHECK HIT
    # ========================================================

    hit = actual in numbers

    rank = None

    if hit:

        rank = (
            numbers.index(actual)
            + 1
        )

    return {
        "prediction_date": prediction_date,
        "target_date": target_date,
        "actual": actual,
        "predictions": predictions,
        "hit": hit,
        "rank": rank
    }


# ============================================================
# RUN BACKTEST
# ============================================================

def run_backtest(
    days=30
):

    dates = get_dates()

    if not dates:

        return []

    available_dates = set(
        dates
    )

    # ========================================================
    # Chỉ chọn những ngày mà NGÀY HÔM SAU cũng có dữ liệu.
    #
    # Ví dụ:
    #
    # 22/08 -> 23/08 có dữ liệu
    # => được test
    #
    # 24/08 -> 25/08 chưa có dữ liệu
    # => không test
    # ========================================================

    test_dates = []

    for date in dates:

        try:

            dt = datetime.strptime(
                date,
                "%Y-%m-%d"
            )

        except ValueError:

            continue

        next_date = (
            dt + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        if next_date in available_dates:

            test_dates.append(
                date
            )

    # Không có ngày nào đủ dữ liệu
    if not test_dates:

        return []

    # ========================================================
    # Lấy N ngày gần nhất
    # ========================================================

    test_dates.sort(
        reverse=True
    )

    test_dates = test_dates[:days]

    # ========================================================
    # Chạy theo thứ tự thời gian
    # để log/backtest dễ kiểm tra
    # ========================================================

    test_dates.sort()

    results = []

    for date in test_dates:

        try:

            result = test_single_date(
                date
            )

            if result.get(
                "status"
            ) != "NO_RESULT":

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"BACKTEST ERROR {date}: "
                f"{repr(e)}"
            )

    return results


# ============================================================
# SUMMARY
# ============================================================

def summarize(
    results
):

    if not results:

        return {}

    total = len(
        results
    )

    hits = sum(
        1
        for result in results
        if result["hit"]
    )

    top1 = 0
    top3 = 0
    top5 = 0
    top10 = 0

    for result in results:

        rank = result["rank"]

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

    return {

        "days": total,

        "hits": hits,

        "hit_rate":
            hits / total,

        "top1":
            top1 / total,

        "top3":
            top3 / total,

        "top5":
            top5 / total,

        "top10":
            top10 / total
    }
