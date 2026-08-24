from collections import Counter
from datetime import datetime
import math

from database import get_results


# ============================================================
# CONFIG
# ============================================================

MIN_HISTORY = 10

SHORT_WINDOW = 7
MEDIUM_WINDOW = 30
LONG_WINDOW = 90

# Trọng số các nhóm feature
WEIGHT_SHORT = 0.30
WEIGHT_MEDIUM = 0.25
WEIGHT_LONG = 0.15
WEIGHT_WEEKDAY = 0.15
WEIGHT_GAP = 0.15


# ============================================================
# UTIL
# ============================================================

def normalize_number(number):
    return str(number).zfill(2)


def parse_date(date):
    return datetime.strptime(
        date,
        "%Y-%m-%d"
    )


# ============================================================
# HISTORY
# ============================================================

def get_history_before(target_date):

    target = parse_date(target_date)

    rows = get_results()

    history = []

    for row in rows:

        try:
            date = parse_date(row[0])
        except (ValueError, TypeError):
            continue

        # QUAN TRỌNG:
        # chỉ lấy dữ liệu trước ngày dự đoán
        if date < target:

            history.append(row)

    history.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return history


# ============================================================
# COUNTER SCORE
# ============================================================

def build_frequency(history, window):

    recent = history[:window]

    counter = Counter(
        normalize_number(row[2])
        for row in recent
    )

    return {
        normalize_number(number):
            counter.get(
                normalize_number(number),
                0
            )
        for number in range(100)
    }


# ============================================================
# NORMALIZE
# ============================================================

def normalize_scores(scores):

    if not scores:
        return scores

    values = list(scores.values())

    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:

        return {
            key: 0.0
            for key in scores
        }

    return {
        key:
        (value - minimum)
        / (maximum - minimum)

        for key, value in scores.items()
    }


# ============================================================
# RECENCY WEIGHTED SCORE
# ============================================================

def recency_score(history, window):

    recent = history[:window]

    scores = {
        normalize_number(number): 0.0
        for number in range(100)
    }

    if not recent:
        return scores

    # Ngày càng gần hiện tại → trọng số càng cao
    for index, row in enumerate(recent):

        number = normalize_number(row[2])

        weight = math.exp(
            -index / max(window / 3, 1)
        )

        scores[number] += weight

    return scores


# ============================================================
# WEEKDAY
# ============================================================

def weekday_score(history, target_date):

    target = parse_date(target_date)

    weekday = target.weekday()

    filtered = [
        row
        for row in history
        if row[3] == weekday
    ]

    counter = Counter(
        normalize_number(row[2])
        for row in filtered
    )

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        scores[n] = counter.get(
            n,
            0
        )

    return normalize_scores(scores)


# ============================================================
# GAP
# ============================================================

def gap_score(history):

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        gap = None

        for index, row in enumerate(history):

            if normalize_number(row[2]) == n:

                gap = index

                break

        if gap is None:

            gap = len(history)

        scores[n] = gap

    # Không dùng "gap càng lớn càng tốt" tuyến tính.
    # Dùng log để tránh số quá lâu không xuất hiện
    # chiếm ưu thế tuyệt đối.

    scores = {
        key: math.log1p(value)
        for key, value in scores.items()
    }

    return normalize_scores(scores)


# ============================================================
# MAIN SCORE
# ============================================================

def calculate_scores(target_date):

    history = get_history_before(
        target_date
    )

    if not history:

        raise ValueError(
            "Database chưa có dữ liệu. "
            "Hãy chạy /update trước."
        )

    if len(history) < MIN_HISTORY:

        raise ValueError(
            f"Chỉ có {len(history)} ngày dữ liệu. "
            f"Cần ít nhất {MIN_HISTORY} ngày."
        )

    # --------------------------------------------------------
    # FEATURE 1: ngắn hạn
    # --------------------------------------------------------

    short_raw = recency_score(
        history,
        SHORT_WINDOW
    )

    short = normalize_scores(
        short_raw
    )

    # --------------------------------------------------------
    # FEATURE 2: trung hạn
    # --------------------------------------------------------

    medium_raw = recency_score(
        history,
        MEDIUM_WINDOW
    )

    medium = normalize_scores(
        medium_raw
    )

    # --------------------------------------------------------
    # FEATURE 3: dài hạn
    # --------------------------------------------------------

    long_raw = build_frequency(
        history,
        LONG_WINDOW
    )

    long = normalize_scores(
        long_raw
    )

    # --------------------------------------------------------
    # FEATURE 4: thứ trong tuần
    # --------------------------------------------------------

    weekday = weekday_score(
        history,
        target_date
    )

    # --------------------------------------------------------
    # FEATURE 5: gap
    # --------------------------------------------------------

    gap = gap_score(
        history
    )

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    scores = {}

    for number in range(100):

        n = normalize_number(number)

        score = (

            short[n]
            * WEIGHT_SHORT

            +

            medium[n]
            * WEIGHT_MEDIUM

            +

            long[n]
            * WEIGHT_LONG

            +

            weekday[n]
            * WEIGHT_WEEKDAY

            +

            gap[n]
            * WEIGHT_GAP

        )

        scores[n] = score

    return scores


# ============================================================
# PREDICT
# ============================================================

def predict(
    target_date,
    top_n=10
):

    if top_n <= 0:

        raise ValueError(
            "top_n phải lớn hơn 0."
        )

    if top_n > 100:

        top_n = 100

    scores = calculate_scores(
        target_date
    )

    ranked = sorted(
        scores.items(),
        key=lambda x: (
            -x[1],
            x[0]
        )
    )

    return ranked[:top_n]
