import random
import numpy as np
from collections import defaultdict

def validate_filters(numbers: list) -> bool:
    """Nới lỏng bộ lọc để không bỏ sót các kết quả đặc biệt."""
    if len(numbers) < 6:
        return True
    sample_6 = numbers[:6]
    total_sum = sum(sample_6)
    
    # Nới dải tổng rộng hơn (100 - 240)
    if not (100 <= total_sum <= 240):
        return False
        
    return True

def predict_power_655_hybrid_10(history_data: list) -> list:
    """Thuật toán Hybrid v2: Cân bằng giữa Số Nóng (Hot) & Số Gan (Cold)."""
    if len(history_data) < 5:
        return sorted(random.sample(range(1, 56), 10))

    total_draws = len(history_data)
    
    # 1. Đếm tần suất xuất hiện (Tần suất 20 kỳ gần nhất)
    recent_draws = history_data[-20:]
    freq = defaultdict(int)
    for draw in recent_draws:
        for num in draw.get("result", []):
            freq[num] += 1

    # 2. Phân tích Nhịp Gan (Gap Analysis)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    # 3. Tính điểm kết hợp
    scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        
        # Điểm tần suất (Số xuất hiện vừa phải)
        f_score = freq[num] * 1.5
        
        # Điểm nhịp gan (Ưu tiên nhịp gan từ 3 - 8 kỳ)
        if 3 <= gap <= 8:
            g_score = 3.0
        elif 1 <= gap <= 2:
            g_score = 1.0
        else:
            g_score = 1.5
            
        scores[num] = f_score + g_score

    # Sắp xếp số theo điểm từ cao xuống thấp
    sorted_candidates = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # 4. Lựa chọn dàn 10 số trải đều dải (Tránh dồn vào 1 đầu số)
    selected = []
    head_count = defaultdict(int)

    for cand in sorted_candidates:
        head = cand // 10
        if head_count[head] < 3: # Mỗi đầu (0x, 1x, 2x, 3x, 4x, 5x) lấy tối đa 3 số
            selected.append(cand)
            head_count[head] += 1
        if len(selected) == 10:
            break

    # Nếu chưa đủ 10 số thì lấy tiếp từ danh sách
    if len(selected) < 10:
        for cand in sorted_candidates:
            if cand not in selected:
                selected.append(cand)
                if len(selected) == 10:
                    break

    return sorted(selected)