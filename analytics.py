import random
from collections import defaultdict
from itertools import combinations

def calculate_soft_score(dan: list) -> float:
    """
    Tính điểm thưởng/phạt mềm (Soft Penalty) thay vì loại bỏ cứng.
    - Phạt nhẹ nếu Tổng quá lệch (<100 hoặc >220).
    - Phạt nhẹ nếu phân bổ Chẵn/Lẻ hoặc Đầu số quá dồn.
    """
    penalty = 0.0
    sample_6 = dan[:6]
    total_sum = sum(sample_6)
    
    # 1. Điểm tổng
    if not (110 <= total_sum <= 210):
        penalty += 3.0
        
    # 2. Điểm Chẵn / Lẻ
    evens = sum(1 for x in sample_6 if x % 2 == 0)
    if evens == 0 or evens == 6:
        penalty += 5.0
        
    # 3. Phân bổ đầu số (Không nên dồn >3 số cùng một đầu 0x, 1x, 2x...)
    head_count = defaultdict(int)
    for n in dan:
        head_count[n // 10] += 1
    for count in head_count.values():
        if count > 3:
            penalty += (count - 3) * 2.0
            
    return penalty

def predict_power_655_hybrid_10(history_data: list) -> list:
    """
    Thuật toán Tối ưu Cụm Đi Cùng Nhau + Chấm Điểm Mềm (High Accuracy Focus).
    """
    if not history_data:
        return [3, 8, 15, 22, 31, 38, 42, 45, 50, 54]

    # Cố định Seed theo ngày kỳ quay gần nhất để backtest nhất quán
    last_draw_date = history_data[-1].get("date", "2026-01-01")
    random.seed(hash(last_draw_date))

    total_draws = len(history_data)
    
    # 1. Tần suất ngắn hạn & Ma trận Cặp đi cùng nhau (Co-occurrence)
    recent_30 = history_data[-30:]
    freq_score = defaultdict(float)
    pair_matrix = defaultdict(lambda: defaultdict(int))
    
    for idx, draw in enumerate(recent_30):
        res = sorted(draw.get("result", []))
        w = 1.0 + (idx * 0.05)
        for num in res:
            freq_score[num] += w
            
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[res[i]][res[j]] += 1
                pair_matrix[res[j]][res[i]] += 1

    # 2. Xây dựng Pool 16 số có điểm tổng hợp cao nhất (Tần suất + Nhịp Gan)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    base_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        gap_w = 3.0 if (2 <= gap <= 7) else 1.0
        base_scores[num] = freq_score[num] + gap_w

    # Chọn Top 16 ứng viên mạnh nhất làm Candidate Pool
    pool = sorted(range(1, 56), key=lambda x: (base_scores[x], -x), reverse=True)[:16]

    # 3. Phủ Dàn Wheel & Chấm Điểm Mềm
    best_dan_10 = []
    max_final_score = -999999.0

    comb_count = 0
    for combo in combinations(pool, 10):
        comb_count += 1
        if comb_count > 400:
            break
            
        dan = list(combo)
        
        # Tính điểm Ma trận Cặp đi kèm
        pair_link_sum = 0
        for i in range(len(dan)):
            for j in range(i + 1, len(dan)):
                pair_link_sum += pair_matrix[dan[i]][dan[j]]

        # Trừ điểm phạt mềm thay vì loại bỏ hoàn toàn
        soft_penalty = calculate_soft_score(dan)
        final_score = (pair_link_sum * 2.0) - soft_penalty

        if final_score > max_final_score:
            max_final_score = final_score
            best_dan_10 = dan

    if not best_dan_10:
        best_dan_10 = sorted(pool[:10])

    random.seed()
    return sorted(best_dan_10)