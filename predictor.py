from collections import Counter, defaultdict
from datetime import datetime, timedelta

# =========================================================
# 1. LOGIC SOI LÔ v10.0 (GIỮ NGUYÊN)
# =========================================================

def analyze_and_predict(historical_data, is_recursive=False):
    if not historical_data or len(historical_data) < 5:
        return None

    daily_numbers = []
    full_results = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)
        full_results.append([str(n).zfill(2) for n in nums])

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)
        if gap in (2, 3): scores[num] += 25.0
        elif gap == 1: scores[num] += 10.0
        elif gap == 4: scores[num] += 6.0
        elif gap == 0: scores[num] -= 10.0
        elif gap > 6: scores[num] -= 999.0

    if len(full_results) > 0 and len(full_results[0]) >= 2:
        g0, g1 = full_results[0][0], full_results[0][1]
        scores[(g0[0] + g1[-1])[-2:].zfill(2)] += 15.0
        scores[(g1[0] + g0[-1])[-2:].zfill(2)] += 15.0

    if not is_recursive and len(historical_data) >= 6:
        prev_pred = analyze_and_predict(historical_data[1:], is_recursive=True)
        if prev_pred and prev_pred['bach_thu'] not in daily_numbers[0]:
            scores[prev_pred['bach_thu']] -= 50.0

    pair_scores = {}
    for i in range(100):
        num = str(i).zfill(2)
        lon = num[::-1]
        if num <= lon:
            pair_scores[(num, lon)] = scores[num] if num == lon else scores[num] + scores[lon]

    best_pair = sorted(pair_scores.keys(), key=lambda x: pair_scores[x], reverse=True)[0]
    bach_thu = best_pair[0] if scores[best_pair[0]] >= scores[best_pair[1]] else best_pair[1]

    if best_pair[0] != best_pair[1]:
        song_thu = (best_pair[0], best_pair[1])
    else:
        ranked_single = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        second = ranked_single[1] if ranked_single[0] == best_pair[0] else ranked_single[0]
        song_thu = (best_pair[0], second)

    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    def extract_balanced_top(candidates, limit, max_per_head):
        result, head_tracker = [], defaultdict(int)
        for n in candidates:
            if head_tracker[n[0]] < max_per_head:
                result.append(n)
                head_tracker[n[0]] += 1
            if len(result) == limit: break
        return result

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': extract_balanced_top(ranked_nums, 5, 1),
        'top_10': extract_balanced_top(ranked_nums, 10, 2)
    }

def test_prediction_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict(historical_data)
    if not pred: return None
    actual_2d = [str(n)[-2:].zfill(2) for n in actual_numbers]
    actual_set = set(actual_2d)
    return {
        'bach_thu': pred['bach_thu'],
        'bach_thu_hit': pred['bach_thu'] in actual_set,
        'song_thu': pred['song_thu'],
        'song_thu_hits': sum(1 for x in pred['song_thu'] if x in actual_set),
        'top_5': pred['top_5'],
        'top_5_hits': sum(1 for x in pred['top_5'] if x in actual_set),
        'top_10': pred['top_10'],
        'top_10_hits': sum(1 for x in pred['top_10'] if x in actual_set),
        'actual_count': len(actual_2d),
        'actual_numbers': actual_2d
    }


# =========================================================
# 2. LOGIC SOI ĐỀ v19.0: DYNAMIC TOUCH & SUM MATRIX
# =========================================================

def analyze_and_predict_db(historical_data):
    if not historical_data or len(historical_data) < 7:
        return None

    db_history = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        if nums and len(nums) > 0:
            db_history.append(str(nums[0])[-2:].zfill(2))

    if not db_history: return None

    recent_30 = db_history[:30]

    # 1. Thống kê điểm Chạm & Tổng
    cham_scores = defaultdict(float)
    sum_scores = defaultdict(float)

    for idx, num in enumerate(recent_30):
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        weight = 1.0 / (idx + 1)**0.5  # Ưu tiên các ngày gần nhất

        cham_scores[h] += weight * 1.5
        cham_scores[t] += weight * 1.5
        sum_scores[s] += weight * 2.0

    # Phạt nhẹ nếu chạm vừa về 2 ngày liên tiếp
    recent_4_chams = []
    for num in db_history[:2]:
        recent_4_chams.extend([int(num[0]), int(num[1])])
    for c, cnt in Counter(recent_4_chams).items():
        if cnt >= 2:
            cham_scores[c] *= 0.5

    # Lấy Top Chạm và Top Tổng mạnh nhất
    top_chams = [c for c, _ in sorted(cham_scores.items(), key=lambda x: x[1], reverse=True)[:5]]
    top_sums = [s for s, _ in sorted(sum_scores.items(), key=lambda x: x[1], reverse=True)[:5]]

    # 2. Chấm điểm 100 con số
    number_scores = {}
    last_seen_gap = {}
    for idx, num in enumerate(recent_30):
        if num not in last_seen_gap:
            last_seen_gap[num] = idx

    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10

        score = 0.0
        if h in top_chams: score += cham_scores[h]
        if t in top_chams: score += cham_scores[t]
        if s in top_sums: score += sum_scores[s]

        # Nhịp rơi nhịp vắng lý tưởng (2 - 8 ngày)
        gap = last_seen_gap.get(s_str, 99)
        if 2 <= gap <= 8:
            score *= 1.4
        elif gap == 0:
            score *= 0.1  # Né bệt lại nguyên con

        number_scores[s_str] = score

    ranked = sorted(number_scores.keys(), key=lambda x: number_scores[x], reverse=True)

    # Dàn 36: Kết hợp ưu tiên các số thuộc Top Chạm và Top Tổng
    set_36 = set()
    for num_str in ranked:
        h, t = int(num_str[0]), int(num_str[1])
        s = (h + t) % 10
        if (h in top_chams or t in top_chams) and s in top_sums:
            set_36.add(num_str)
        if len(set_36) >= 36: break

    # Bổ sung nếu chưa đủ 36 con
    if len(set_36) < 36:
        for num_str in ranked:
            set_36.add(num_str)
            if len(set_36) == 36: break

    top_36_db = sorted(list(set_36))
    top_20_db = sorted(sorted(top_36_db, key=lambda x: number_scores[x], reverse=True)[:20])
    top_10_db = sorted(sorted(top_20_db, key=lambda x: number_scores[x], reverse=True)[:10])

    return {
        'top_10_db': top_10_db,
        'top_20_db': top_20_db,
        'top_36_db': top_36_db
    }

def test_db_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict_db(historical_data)
    if not pred or not actual_numbers: return None
    actual_db = str(actual_numbers[0])[-2:].zfill(2)
    return {
        'predicted_10': pred['top_10_db'],
        'predicted_20': pred['top_20_db'],
        'predicted_36': pred['top_36_db'],
        'actual_db': actual_db,
        'is_hit_10': actual_db in pred['top_10_db'],
        'is_hit_20': actual_db in pred['top_20_db'],
        'is_hit_36': actual_db in pred['top_36_db'],
        'is_hit': actual_db in pred['top_10_db']
    }