from collections import Counter, defaultdict
import math

# =========================================================
# 1. LOGIC SOI LÔ (BẠCH THỦ, SONG THỦ, TOP 5, TOP 10) - v10.0 (GIỮ NGUYÊN)
# =========================================================

def analyze_and_predict(historical_data, is_recursive=False):
    """
    Thuật toán SOI LÔ v10.0: Ensemble Multi-Bridge & Adaptive Threshold Matrix
    """
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

    # 1. TÍNH NHỊP VẮNG (GAP ANALYSIS)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)

        if gap == 2 or gap == 3:
            scores[num] += 25.0
        elif gap == 1:
            scores[num] += 10.0
        elif gap == 4:
            scores[num] += 6.0
        elif gap == 0:
            scores[num] -= 10.0
        elif gap > 6:
            scores[num] -= 999.0

    # 2. CẦU VỊ TRÍ ĐẠI DIỆN
    if len(full_results) > 0 and len(full_results[0]) >= 2:
        g0 = full_results[0][0]
        g1 = full_results[0][1]
        
        bridge_num1 = (g0[0] + g1[-1])[-2:].zfill(2)
        bridge_num2 = (g1[0] + g0[-1])[-2:].zfill(2)
        
        scores[bridge_num1] += 15.0
        scores[bridge_num2] += 15.0

    # 3. CHỐNG NEO SỐ TRƯỢT
    if not is_recursive and len(historical_data) >= 6:
        prev_data = historical_data[1:]
        prev_pred = analyze_and_predict(prev_data, is_recursive=True)
        if prev_pred:
            prev_bt = prev_pred['bach_thu']
            if prev_bt not in daily_numbers[0]:
                scores[prev_bt] -= 50.0

    # 4. CHỌN BẠCH THỦ VÀ SONG THỦ
    pair_scores = {}
    for i in range(100):
        num = str(i).zfill(2)
        lon = num[::-1]
        if num <= lon:
            p_score = scores[num] if num == lon else scores[num] + scores[lon]
            pair_scores[(num, lon)] = p_score

    best_pair = sorted(pair_scores.keys(), key=lambda x: pair_scores[x], reverse=True)[0]

    if scores[best_pair[0]] >= scores[best_pair[1]]:
        bach_thu = best_pair[0]
    else:
        bach_thu = best_pair[1]

    if best_pair[0] != best_pair[1]:
        song_thu = (best_pair[0], best_pair[1])
    else:
        ranked_single = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        second = ranked_single[1] if ranked_single[0] == best_pair[0] else ranked_single[0]
        song_thu = (best_pair[0], second)

    # 5. DÀN TOP 5 VÀ TOP 10 PHÂN TÁN ĐẦU SỐ
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    def extract_balanced_top(candidates, limit, max_per_head):
        result = []
        head_tracker = defaultdict(int)
        for n in candidates:
            head = n[0]
            if head_tracker[head] < max_per_head:
                result.append(n)
                head_tracker[head] += 1
            if len(result) == limit:
                break
        return result

    top_5 = extract_balanced_top(ranked_nums, 5, max_per_head=1)
    top_10 = extract_balanced_top(ranked_nums, 10, max_per_head=2)

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }

def test_prediction_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict(historical_data)
    if not pred:
        return None

    actual_2d = [str(n)[-2:].zfill(2) for n in actual_numbers]
    actual_set = set(actual_2d)

    bt = pred['bach_thu']
    st1, st2 = pred['song_thu']
    t5 = pred['top_5']
    t10 = pred['top_10']

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt in actual_set,
        'song_thu': (st1, st2),
        'song_thu_hits': sum(1 for x in (st1, st2) if x in actual_set),
        'top_5': t5,
        'top_5_hits': sum(1 for x in t5 if x in actual_set),
        'top_10': t10,
        'top_10_hits': sum(1 for x in t10 if x in actual_set),
        'actual_count': len(actual_2d),
        'actual_numbers': actual_2d
    }


# =========================================================
# 2. LOGIC SOI ĐỀ v18.0: PURE STATISTICAL DYNAMIC MATRIX
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán SOI ĐỀ v18.0:
    - Loại bỏ điểm số cộng/trừ cảm tính.
    - Sử dụng Tần suất Xuất hiện + Chu kỳ Nhịp vắng (Gap Analysis) chuẩn Thống kê.
    - Lấy trực tiếp Top 36 con có xác suất cao nhất toàn bảng.
    """
    if not historical_data or len(historical_data) < 7:
        return None

    db_history = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        if nums and len(nums) > 0:
            db_num = str(nums[0])[-2:].zfill(2)
            db_history.append(db_num)

    if not db_history:
        return None

    total_days = min(len(db_history), 60)
    recent_db = db_history[:total_days]

    # 1. Tính Khoảng cách Nhịp vắng (Gap) của từng con đề (00-99)
    last_seen_db = {}
    for idx, num in enumerate(recent_db):
        if num not in last_seen_db:
            last_seen_db[num] = idx

    # 2. Thống kê tần suất Đầu, Đuôi, Tổng
    head_freq = defaultdict(int)
    tail_freq = defaultdict(int)
    sum_freq = defaultdict(int)

    for num in recent_db:
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        head_freq[h] += 1
        tail_freq[t] += 1
        sum_freq[s] += 1

    # 3. Tính điểm Xác suất Thống kê cho 100 con số
    probs = {}
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10

        gap = last_seen_db.get(s_str, 99)

        # Trọng số Tần suất Đầu/Đuôi/Tổng trong ngắn hạn (30 ngày)
        h_prob = head_freq[h] / total_days
        t_prob = tail_freq[t] / total_days
        s_prob = sum_freq[s] / total_days

        # Điểm nhịp vắng đề (Nhịp rơi phong độ 2-10 ngày có tỷ lệ nổ cao nhất)
        if 2 <= gap <= 8:
            gap_weight = 2.5
        elif gap == 1:
            gap_weight = 1.2
        elif gap == 0:  # Đề vừa về hôm qua (bệt đề nguyên con cực hiếm)
            gap_weight = 0.1
        elif 9 <= gap <= 15:
            gap_weight = 1.5
        else:  # Đề gan quá 15 ngày
            gap_weight = 0.5

        # Bắt bóng & chạm chuyền từ giải đặc biệt ngày hôm qua
        last_h, last_t = int(recent_db[0][0]), int(recent_db[0][1])
        bridge_bonus = 1.0
        if h == last_t or t == last_h:  # Chạm lộn
            bridge_bonus += 0.5
        if h == (last_h + 5) % 10 or t == (last_t + 5) % 10:  # Bóng dương
            bridge_bonus += 0.4

        # Tổng hợp điểm xác suất
        final_score = (h_prob * 0.35 + t_prob * 0.35 + s_prob * 0.30) * gap_weight * bridge_bonus
        probs[s_str] = final_score

    # 4. Sắp xếp 100 con số theo Xác suất giảm dần
    ranked_db = sorted(probs.keys(), key=lambda x: probs[x], reverse=True)

    # 5. Lấy Dàn 10, 20, 36 thuần túy từ Top Xác suất cao nhất
    top_10_db = sorted(ranked_db[:10])
    top_20_db = sorted(ranked_db[:20])
    top_36_db = sorted(ranked_db[:36])

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