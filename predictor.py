from collections import Counter, defaultdict

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
# 2. LOGIC SOI ĐỀ v16.0: ADAPTIVE BALANCE MATRIX & HEAD SPREADING
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán SOI ĐỀ v16.0:
    - Giải quyết dứt điểm tình trạng kẹt bệt Chạm 3, 8, 9.
    - Cân bằng tự động Dàn 36 số bằng cách phân bổ đều trên cả 10 đầu số.
    - Kết hợp Ma trận Cầu Tổng Đề + Tần suất Đầu/Đuôi linh hoạt.
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

    last_db = db_history[0]
    h1, t1 = int(last_db[0]), int(last_db[1])

    prev_db = db_history[1] if len(db_history) > 1 else last_db
    h2, t2 = int(prev_db[0]), int(prev_db[1])

    # 1. Thống kê tần suất Đầu / Đuôi / Tổng trong 20 ngày
    recent_20 = db_history[:20]
    head_counts = defaultdict(int)
    tail_counts = defaultdict(int)
    sum_counts = defaultdict(int)

    for num in recent_20:
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        head_counts[h] += 1
        tail_counts[t] += 1
        sum_counts[s] += 1

    # 2. Kiểm tra tần suất chạm 4 ngày gần nhất để phạt bệt linh hoạt
    recent_4 = db_history[:4]
    recent_chams = []
    for num in recent_4:
        recent_chams.extend([int(num[0]), int(num[1])])
    cham_counter = Counter(recent_chams)

    # 3. Chấm điểm ma trận cân bằng
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10
        score = 0.0

        # Điểm tần suất nhẹ nhàng (tránh ngộ độc điểm)
        score += (head_counts[h] * 1.2) + (tail_counts[t] * 1.2) + (sum_counts[s] * 1.0)

        # Cầu Chuyền & Bóng (Tăng điểm cho cầu mới)
        if h == t1 or t == h1: score += 4.0
        if h == (t1 + 5) % 10 or t == (h1 + 5) % 10: score += 3.0
        if h == (h1 + 5) % 10 and t == (t1 + 5) % 10: score += 4.0

        # Kép / Sát Kép
        if h == t: score += 2.0
        elif abs(h - t) == 1 or abs(h - t) == 9: score += 1.5

        # Phạt bệt chạm nếu đã ra hơn 2 lần trong 4 ngày
        if cham_counter[h] >= 2:
            score -= (cham_counter[h] * 3.0)
        if cham_counter[t] >= 2:
            score -= (cham_counter[t] * 3.0)

        # Trừ nhẹ con vừa về ngày hôm qua
        if s_str == last_db:
            score -= 6.0

        scores[s_str] = score

    # Sắp xếp danh sách điểm số từ cao xuống thấp
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    all_ranked = [num_str for num_str, _ in sorted_numbers]

    # --- LỰA CHỌN DÀN 10 & 20 THEO ĐIỂM SỐ XANH CHÍN ---
    top_10_db = sorted(all_ranked[:10])
    top_20_db = sorted(all_ranked[:20])

    # --- LỰA CHỌN DÀN 36 SỐ: PHÂN BỔ ĐỀU 10 ĐẦU SỐ (Bao phủ tuyệt đối) ---
    head_buckets = defaultdict(list)
    for num_str, sc in sorted_numbers:
        head_buckets[num_str[0]].append(num_str)

    top_36_set = set()
    # Bước 1: Mỗi đầu bắt buộc lấy 3 con điểm cao nhất (30 con)
    for h_digit in range(10):
        h_str = str(h_digit)
        top_36_set.update(head_buckets[h_str][:3])

    # Bước 2: Bổ sung 6 con điểm cao nhất còn lại trên toàn bảng để đủ 36 số
    for num_str in all_ranked:
        if num_str not in top_36_set:
            top_36_set.add(num_str)
        if len(top_36_set) == 36:
            break

    top_36_db = sorted(list(top_36_set))

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