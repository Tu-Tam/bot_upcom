import random
from collections import defaultdict

def predict_power_655_hybrid_10(history_data: list) -> list:
    """
    Thuật toán Hybrid Deterministic (Cố định kết quả 100% cho từng ngày).
    Tối ưu Tần suất + Nhịp Gan + Ma trận Cặp.
    """
    if not history_data:
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # 1. Cố định Seed ngẫu nhiên theo Ngày của kỳ quay mới nhất trong lịch sử
    # Đảm bảo cứ cùng ngày quá khứ là thuật toán ra đúng 1 kết quả duy nhất
    last_draw_date = history_data[-1].get("date", "2026-01-01")
    random.seed(hash(last_draw_date))

    total_draws = len(history_data)
    
    # 2. Tính Tần suất ngắn hạn (15 kỳ gần nhất)
    recent_15 = history_data[-15:]
    freq_score = defaultdict(float)
    for idx, draw in enumerate(recent_15):
        w = 1.0 + (idx * 0.1)
        for num in draw.get("result", []):
            freq_score[num] += w

    # 3. Ma trận Cặp đi kèm (Co-occurrence) trong 30 kỳ
    recent_30 = history_data[-30:]
    pair_matrix = defaultdict(lambda: defaultdict(int))
    for draw in recent_30:
        res = sorted(draw.get("result", []))
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                pair_matrix[res[i]][res[j]] += 1
                pair_matrix[res[j]][res[i]] += 1

    # 4. Nhịp Gan Rơi (Gap Analysis)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    base_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        if 2 <= gap <= 6:
            gap_w = 4.0
        elif gap == 1:
            gap_w = 2.0
        elif 7 <= gap <= 10:
            gap_w = 2.5
        else:
            gap_w = 0.5
            
        base_scores[num] = (freq_score[num] * 2.0) + gap_w

    # Sắp xếp danh sách số theo Điểm cao xuống thấp + Ưu tiên Số nhỏ hơn khi bằng điểm (Tiêu chuẩn hóa)
    sorted_candidates = sorted(range(1, 56), key=lambda x: (base_scores[x], -x), reverse=True)
    
    # Lấy số Hạt nhân có điểm cao nhất
    seed = sorted_candidates[0]
    selected = [seed]

    # 5. Lựa chọn 9 số còn lại dựa trên điểm liên kết ma trận cặp
    while len(selected) < 10:
        candidates = {}
        for num in range(1, 56):
            if num in selected:
                continue
            pair_score = sum(pair_matrix[num][sel] for sel in selected)
            candidates[num] = base_scores[num] + (pair_score * 1.5)

        # Sắp xếp các ứng viên theo Điểm -> nếu bằng điểm thì ưu tiên số nhỏ hơn
        best_next = sorted(candidates.keys(), key=lambda x: (candidates[x], -x), reverse=True)[0]
        selected.append(best_next)

    # Đặt lại seed về mặc định sau khi tính xong
    random.seed()

    return sorted(selected)