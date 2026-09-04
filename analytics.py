import random
import numpy as np
from collections import defaultdict

def validate_filters(numbers: list) -> bool:
    """Loại bỏ các bộ số vi phạm quy luật xác suất (Tổng & Chẵn/Lẻ)."""
    if len(numbers) < 6:
        return True
    sample_6 = numbers[:6]
    total_sum = sum(sample_6)
    
    # Khống chế Tổng dải 6 số trong khoảng 120 - 220
    if not (120 <= total_sum <= 220):
        return False
    
    # Khống chế tỷ lệ Chẵn / Lẻ
    evens = sum(1 for n in sample_6 if n % 2 == 0)
    if evens < 1 or evens > 5:
        return False
        
    return True

def predict_power_655_hybrid_10(history_data: list) -> list:
    """Thuật toán Hybrid 10: Phân tích Nhịp Gan & Ma trận Cặp."""
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), 10))

    total_draws = len(history_data)
    
    # 1. Nhịp gan (Gap Analysis)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    gap_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        if 1 <= gap <= 5:
            gap_scores[num] = 2.5
        elif 6 <= gap <= 10:
            gap_scores[num] = 1.8
        else:
            gap_scores[num] = 1.0

    # 2. Trọng số ma trận liên kết cặp
    pair_matrix = defaultdict(float)
    weights = np.exp(np.linspace(-1.5, 0, total_draws))
    
    for idx, draw in enumerate(history_data):
        w = weights[idx]
        res = draw.get("result", [])
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                n1, n2 = res[i], res[j]
                pair_matrix[(n1, n2)] += w
                pair_matrix[(n2, n1)] += w

    # 3. Chấm điểm tổng hợp
    scores = {}
    for num in range(1, 56):
        link_score = sum(pair_matrix.get((num, other), 0) for other in range(1, 56) if other != num)
        scores[num] = link_score * 0.7 + gap_scores[num] * 2.2

    sorted_candidates = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # 4. Chọn 10 số trải đều dải đầu số (0x - 5x)
    selected = []
    head_count = defaultdict(int)

    for cand in sorted_candidates:
        head = cand // 10
        if head_count[head] < 3:
            if validate_filters(selected + [cand]):
                selected.append(cand)
                head_count[head] += 1
        if len(selected) == 10:
            break

    if len(selected) < 10:
        for cand in sorted_candidates:
            if cand not in selected:
                selected.append(cand)
                if len(selected) == 10:
                    break

    return sorted(selected)