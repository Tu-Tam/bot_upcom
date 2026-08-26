# =========================================================
# 2. LOGIC SOI ĐỀ v14.0: FREQUENCY BALANCED MATRIX
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán SOI ĐỀ v14.0:
    - Loại bỏ hoàn toàn cộng điểm bệt chạm quá đà.
    - Kết hợp Ma trận Cầu Tổng Đề + Tần suất Đầu Đuôi ngắn hạn (15 ngày).
    - Mở rộng biên độ bao phủ Dàn 36 để quét sạch các nhịp cầu chuyển.
    """
    if not historical_data or len(historical_data) < 5:
        return None

    db_history = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        if nums and len(nums) > 0:
            db_num = str(nums[0])[-2:].zfill(2)
            db_history.append(db_num)

    if not db_history:
        return None

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # Dữ liệu ĐB 3 ngày gần nhất
    last_db = db_history[0]
    h1, t1 = int(last_db[0]), int(last_db[1])
    
    prev_db = db_history[1] if len(db_history) > 1 else last_db
    h2, t2 = int(prev_db[0]), int(prev_db[1])

    # 1. Thống kê tần suất Đầu / Đuôi / Tổng trong 15 ngày gần nhất (Thu hẹp khung để bám sát nhịp chạy)
    recent_15 = db_history[:15]
    head_counts = defaultdict(int)
    tail_counts = defaultdict(int)
    sum_counts = defaultdict(int)

    for num in recent_15:
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        head_counts[h] += 1
        tail_counts[t] += 1
        sum_counts[s] += 1

    # 2. Đếm tần suất chạm xuất hiện trong 5 ngày gần đây để hạ nhiệt (Phạt Bệt)
    recent_5 = db_history[:5]
    recent_chams = []
    for num in recent_5:
        recent_chams.extend([int(num[0]), int(num[1])])
    cham_counter = Counter(recent_chams)

    # 3. Chấm điểm ma trận cân bằng v14.0
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10
        score = 0.0

        # a. Tần suất Đầu / Đuôi ngắn hạn
        score += (head_counts[h] * 2.0) + (tail_counts[t] * 2.0)

        # b. Cầu Tổng Đề (Tổng đang chạy tốt)
        score += (sum_counts[s] * 1.5)

        # c. Cầu Chuyền Đuôi -> Đầu, Đầu -> Đuôi (Nhẹ nhàng 3.0 điểm)
        if h == t1: score += 3.0
        if t == h1: score += 3.0

        # d. Thưởng Cầu Bóng Âm Dương vừa phải
        if h == (t1 + 5) % 10 or t == (h1 + 5) % 10:
            score += 2.0

        # e. Thưởng Kép / Sát Kép
        if h == t:
            score += 2.5
        elif abs(h - t) == 1 or abs(h - t) == 9:
            score += 1.5

        # f. KHẮC PHỤC CHÍNH: Phạt bệt chạm dồn dập (Chống kẹt Chạm 3, 8, 9)
        if cham_counter[h] >= 3:
            score -= (cham_counter[h] * 2.5)
        if cham_counter[t] >= 3:
            score -= (cham_counter[t] * 2.5)

        # g. Trừ nhẹ con đề vừa về ngày hôm qua
        if s_str == last_db:
            score -= 5.0

        scores[s_str] = score

    # Sắp xếp số theo điểm số giảm dần
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    all_ranked = [num_str for num_str, _ in sorted_numbers]

    # --- LẤY DÀN THEO ĐIỂM SỐ THỰC TẾ (Không ép bộ lọc cứng) ---
    top_10_db = sorted(all_ranked[:10])
    top_20_db = sorted(all_ranked[:20])
    top_36_db = sorted(all_ranked[:36])

    return {
        'top_10_db': top_10_db,
        'top_20_db': top_20_db,
        'top_36_db': top_36_db
    }

def test_db_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict_db(historical_data)
    if not pred or not actual_numbers:
        return None

    actual_db = str(actual_numbers[0])[-2:].zfill(2)
    top_10 = pred.get('top_10_db', [])
    top_20 = pred.get('top_20_db', [])
    top_36 = pred.get('top_36_db', [])

    return {
        'predicted_10': top_10,
        'predicted_20': top_20,
        'predicted_36': top_36,
        'actual_db': actual_db,
        'is_hit_10': actual_db in top_10,
        'is_hit_20': actual_db in top_20,
        'is_hit_36': actual_db in top_36,
        'is_hit': actual_db in top_10
    }