import random
from collections import defaultdict
from itertools import combinations

def predict_power_655_hybrid_10(history_data: list) -> list:
    """Thuật toán dự đoán Power 6/55 (Dải số 1 - 55)"""
    return _predict_hybrid_core(history_data, max_num=55, sum_min=80, sum_max=220)

def predict_mega_645_hybrid_10(history_data: list) -> list:
    """Thuật toán dự đoán Mega 6/45 (Dải số 1 - 45)"""
    return _predict_hybrid_core(history_data, max_num=45, sum_min=70, sum_max=180)

def _predict_hybrid_core(history_data: list, max_num: int, sum_min: int, sum_max: int) -> list:
    if not history_data:
        return list(range(1, 11))

    last_draw_date = history_data[-1].get("date", "2026-01-01")
    random.seed(hash(last_draw_date))

    total_draws = len(history_data)
    recent_12 = history_data[-12:]
    recent_30 = history_data[-30:]
    
    freq_short = defaultdict(float)
    for idx, draw in enumerate(recent_12):
        w = 1.0 + (idx * 0.1)
        for num in draw.get("result", []):
            freq_short[num] += w

    pair_matrix = defaultdict(lambda: defaultdict(int))
    for draw in recent_30:
        res = sorted(draw.get("result", []))
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[res[i]][res[j]] += 1
                pair_matrix[res[j]][res[i]] += 1

    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    base_scores = {}
    for num in range(1, max_num + 1):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        if 1 <= gap <= 5:
            gap_weight = 4.0 - (gap * 0.5)
        elif 6 <= gap <= 10:
            gap_weight = 1.5
        else:
            gap_weight = 0.2
            
        base_scores[num] = (freq_short[num] * 2.0) + gap_weight

    sorted_candidates = sorted(range(1, max_num + 1), key=lambda x: (base_scores[x], -x), reverse=True)
    candidate_pool = sorted_candidates[:14]

    best_dan_10 = []
    max_cluster_score = -9999.0

    for combo in combinations(candidate_pool, 10):
        dan = list(combo)
        pair_sum = sum(pair_matrix[dan[i]][dan[j]] for i in range(len(dan)) for j in range(i + 1, len(dan)))
        
        sum_6 = sum(dan[:6])
        penalty = 5.0 if not (sum_min <= sum_6 <= sum_max) else 0.0
            
        final_score = (pair_sum * 3.0) + sum(base_scores[n] for n in dan) - penalty

        if final_score > max_cluster_score:
            max_cluster_score = final_score
            best_dan_10 = dan

    if not best_dan_10:
        best_dan_10 = sorted(candidate_pool[:10])

    random.seed()
    return sorted(best_dan_10)