import random
from collections import defaultdict
from itertools import combinations

def predict_power_655_hybrid_10(history_data: list) -> list:
    """
    Dự đoán Dàn 10 số dựa trên Ma trận Cặp & Nhịp rơi ngắn hạn.
    Cố định Seed ngẫu nhiên theo ngày quay gần nhất để backtest nhất quán.
    """
    if not history_data:
        return [3, 8, 15, 22, 31, 38, 42, 45, 50, 54]

    # Cố định Seed ngẫu nhiên theo ngày của kỳ cuối cùng trong tập backtest
    last_draw_date = history_data[-1].get("date", "2026-01-01")
    random.seed(hash(last_draw_date))

    total_draws = len(history_data)
    
    # 1. Tần suất ngắn hạn (12 kỳ) & Trung hạn (30 kỳ)
    recent_12 = history_data[-12:]
    recent_30 = history_data[-30:]
    
    freq_short = defaultdict(float)
    for idx, draw in enumerate(recent_12):
        w = 1.0 + (idx * 0.1)
        for num in draw.get("result", []):
            freq_short[num] += w

    # 2. Ma trận Cặp Co-occurrence (Mật độ đi cùng nhau)
    pair_matrix = defaultdict(lambda: defaultdict(int))
    for draw in recent_30:
        res = sorted(draw.get("result", []))
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[res[i]][res[j]] += 1
                pair_matrix[res[j]][res[i]] += 1

    # 3. Tính Điểm Cơ bản + Nhịp Gan
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    base_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        if 1 <= gap <= 5:
            gap_weight = 4.0 - (gap * 0.5)
        elif 6 <= gap <= 10:
            gap_weight = 1.5
        else:
            gap_weight = 0.2
            
        base_scores[num] = (freq_short[num] * 2.0) + gap_weight

    # 4. Lấy Top 14 số xuất sắc nhất vào Pool
    sorted_candidates = sorted(range(1, 56), key=lambda x: (base_scores[x], -x), reverse=True)
    candidate_pool = sorted_candidates[:14]

    # 5. Phủ Dàn Wheel 10 số có mật độ liên kết cặp cao nhất
    best_dan_10 = []
    max_cluster_score = -1.0

    for combo in combinations(candidate_pool, 10):
        dan = list(combo)
        
        pair_sum = 0
        for i in range(len(dan)):
            for j in range(i + 1, len(dan)):
                pair_sum += pair_matrix[dan[i]][dan[j]]

        sum_6 = sum(dan[:6])
        penalty = 0.0
        if not (100 <= sum_6 <= 220):
            penalty += 5.0
            
        final_score = (pair_sum * 3.0) + sum(base_scores[n] for n in dan) - penalty

        if final_score > max_cluster_score:
            max_cluster_score = final_score
            best_dan_10 = dan

    if not best_dan_10:
        best_dan_10 = sorted(candidate_pool[:10])

    random.seed()
    return sorted(best_dan_10)