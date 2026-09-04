# analytics.py
import numpy as np
from collections import defaultdict

def validate_filters(numbers: list) -> bool:
    """Loại bỏ các bộ số vi phạm quy luật xác suất tự nhiên."""
    total_sum = sum(numbers)
    # 1. Khống chế Tổng dải số trong khoảng vàng 130 - 210
    if not (130 <= total_sum <= 210):
        return False
    
    # 2. Khống chế tỷ lệ Chẵn / Lẻ
    evens = sum(1 for n in numbers if n % 2 == 0)
    if evens < 2 or evens > 4:
        return False
        
    return True

def get_hybrid_10_advanced(dataset: list) -> list:
    if len(dataset) < 10:
        return list(range(1, 11))
        
    total_draws = len(dataset)
    weights = np.exp(np.linspace(-2.0, 0, total_draws))
    
    freq = defaultdict(float)
    pair_matrix = defaultdict(float)
    
    for idx, draw in enumerate(dataset):
        w = weights[idx]
        res = draw.get("result", [])
        for n in res:
            freq[n] += w
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[(res[i], res[j])] += w
                pair_matrix[(res[j], res[i])] += w

    # Chấm điểm 55 con số
    scores = {}
    for num in range(1, 56):
        link_score = sum(pair_matrix.get((num, other), 0) for other in range(1, 56) if other != num)
        scores[num] = freq[num] * 1.2 + link_score * 2.5

    sorted_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # Chọn ra dàn 10 số đã qua bộ lọc Toán học
    selected = []
    for num in sorted_nums:
        temp_set = selected + [num]
        if len(temp_set) <= 6 or validate_filters(temp_set[:6]):
            selected.append(num)
        if len(selected) == 10:
            break
            
    return sorted(selected)