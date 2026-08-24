from collections import Counter
from datetime import datetime

from database import get_results


def normalize_number(number):
    return str(number).zfill(2)


def get_history_before(target_date):

    rows = get_results()

    target = datetime.strptime(
        target_date,
        "%Y-%m-%d"
    )

    result = []

    for row in rows:

        date = datetime.strptime(
            row[0],
            "%Y-%m-%d"
        )

        if date < target:
            result.append(row)

    result.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return result


def frequency_score(history, window):

    recent = history[:window]

    counter = Counter(
        row[2]
        for row in recent
    )

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        scores[n] = counter.get(n, 0)

    return scores


def gap_score(history):

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        gap = len(history) + 1

        for index, row in enumerate(history):

            if row[2] == n:

                gap = index

                break

        scores[n] = gap

    return scores


def day_of_week_score(history, target_date):

    target = datetime.strptime(
        target_date,
        "%Y-%m-%d"
    )

    weekday = target.weekday()

    filtered = [
        row for row in history
        if row[3] == weekday
    ]

    counter = Counter(
        row[2]
        for row in filtered
    )

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        scores[n] = counter.get(n, 0)

    return scores


def recent_trend_score(history):

    recent = history[:10]

    counter = Counter(
        row[2]
        for row in recent
    )

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        scores[n] = counter.get(n, 0)

    return scores


def calculate_scores(target_date):

    history = get_history_before(
        target_date
    )

    if len(history) == 0:
        raise ValueError(
            "Database chưa có dữ liệu. "
            "Hãy chạy /update trước."
        )

    if len(history) < 10:
        raise ValueError(
            f"Chỉ có {len(history)} ngày dữ liệu. "
            "Cần ít nhất 10 ngày để dự đoán."
        )

    freq7 = frequency_score(
        history,
        7
    )

    freq30 = frequency_score(
        history,
        30
    )

    freq90 = frequency_score(
        history,
        90
    )

    gap = gap_score(history)

    weekday = day_of_week_score(
        history,
        target_date
    )

    trend = recent_trend_score(
        history
    )

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        score = (
            freq7[n] * 1.5
            + freq30[n] * 1.0
            + freq90[n] * 0.4
            + weekday[n] * 1.2
            + trend[n] * 1.0
        )

        score += min(
            gap[n],
            20
        ) * 0.05

        scores[n] = score

    return scores


def predict(target_date, top_n=10):

    scores = calculate_scores(
        target_date
    )

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_n]
