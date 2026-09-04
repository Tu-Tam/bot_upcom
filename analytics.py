import random
from collections import defaultdict

def predict_power_655_hybrid_10(history_data: list) -> list:
    """
    Thuật toán Hybrid v4 (Cluster Strike):
    Tập trung tìm Cụm số hay ra cùng nhau (Pairing Matrix) + Trọng số Tần suất.
    Mục tiêu: Đột phá trúng cụm 3-5 số trong Dàn 10.
    """
    if len(history_data) < 10:
        return sorted(random.sample(range(1, 56), 10))

    total_draws = len(history_data)
    
    # 1. Tính Tần suất ngắn hạn (15 kỳ gần nhất)
    recent_15 = history_data[-15:]
    freq_score = defaultdict(float)
    for idx, draw in enumerate(recent_15):
        w = 1.0 + (idx * 0.12)
        for num in draw.get("result", []):
            freq_score[num] += w

    # 2. Xây dựng Ma trận Cặp (Tìm các cặp số hay nổ cùng nhau trong 30 kỳ)
    recent_30 = history_data[-30:]
    pair_matrix = defaultdict(lambda: defaultdict(int))
    for draw in recent_30:
        res = sorted(draw.get("result", []))
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[res[i]][res[j]] += 1
                pair_matrix[res[j]][res[i]] += 1

    # 3. Tính điểm Nhịp Gan Rơi (Tối ưu gan 2-6 kỳ)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    base_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        if 2 <= gap <= 6:
            gap_w = 4.5
        elif gap == 1:
            gap_w = 2.0
        elif 7 <= gap <= 10:
            gap_w = 2.5
        else:
            gap_w = 0.5  # Gan quá lâu trừ điểm nặng
            
        base_scores[num] = (freq_score[num] * 2.2) + gap_w

    # 4. Chọn số Hạt nhân (Seed Number) có điểm cao nhất
    sorted_base = sorted(base_scores.keys(), key=lambda x: base_scores[x], reverse=True)
    seed = sorted_base[0]
    selected = [seed]

    # 5. Chọn 9 số còn lại dựa trên Ma trận đi kèm với các số đã chọn
    while len(selected) < 10:
        candidates = {}
        for num in range(1, 56):
            if num in selected:
                continue
            
            # Điểm đi kèm (Co-occurrence Score) với tập đã chọn
            pair_score = sum(pair_matrix[num][sel] for sel in selected)
            
            # Tổng điểm = Điểm nền + Điểm đi kèm
            candidates[num] = base_scores[num] + (pair_score * 1.8)

        # Lấy số có tổng điểm liên kết cao nhất
        best_next = max(candidates.keys(), key=lambda x: candidates[x])
        selected.append(best_next)

    return sorted(selected)