from datetime import datetime, timedelta

from database import get_results
from predictor import predict


def get_dates():

    rows = get_results()

    dates = sorted(
        set(row[0] for row in rows)
    )

    return dates


def test_single_date(
    prediction_date
):

    target = datetime.strptime(
        prediction_date,
        "%Y-%m-%d"
    )

    next_day = target + timedelta(
        days=1
    )

    next_date = next_day.strftime(
        "%Y-%m-%d"
    )

    actual_rows = [
        row for row in get_results()
        if row[0] == next_date
    ]

    if not actual_rows:

        return {
            "prediction_date": prediction_date,
            "target_date": next_date,
            "status": "NO_RESULT"
        }

    actual = actual_rows[0][2]

    predictions = predict(
        next_date,
        top_n=10
    )

    numbers = [
        x[0] for x in predictions
    ]

    hit = actual in numbers

    return {
        "prediction_date": prediction_date,
        "target_date": next_date,
        "actual": actual,
        "predictions": predictions,
        "hit": hit,
        "rank": (
            numbers.index(actual) + 1
            if hit
            else None
        )
    }


def run_backtest(
    days=30
):

    dates = get_dates()

    dates = dates[-days:]

    results = []

    for date in dates:

        try:

            result = test_single_date(
                date
            )

            if result.get("status") != "NO_RESULT":

                results.append(result)

        except Exception as e:

            print(
                f"Lỗi {date}: {e}"
            )

    return results


def summarize(results):

    if not results:

        return {}

    total = len(results)

    hits = sum(
        1
        for r in results
        if r["hit"]
    )

    top1 = 0
    top3 = 0
    top5 = 0

    for r in results:

        if not r["hit"]:
            continue

        rank = r["rank"]

        if rank <= 1:
            top1 += 1

        if rank <= 3:
            top3 += 1

        if rank <= 5:
            top5 += 1

    return {
        "days": total,
        "hits": hits,
        "hit_rate": hits / total,
        "top1": top1 / total,
        "top3": top3 / total,
        "top5": top5 / total
    }
