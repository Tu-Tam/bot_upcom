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

    # 3. CHỐNG NEO SỐ TRƯỢT (Tránh đệ quy vô hạn bằng is_recursive)
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
# 2. LOGIC SOI ĐỀ v12.1: DYNAMIC ADAPTIVE MATRIX & ANTI-OVERFIT
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán SOI ĐỀ v12.1:
    - Cập nhật cơ chế Dynamic Weighting chống trượt chuỗi do 'ngộ độc chạm'
    - Tự động hạ trọng số nếu bệt chạm > 3 lần trong 3 ngày
    - Cân bằng lại cầu chuyền, bóng âm dương và rút dàn trực tiếp theo thực tế
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

    # Dữ liệu ĐB 4 ngày gần nhất
    last_db = db_history[0]
    h1, t1 = int(last_db[0]), int(last_db[1])
    
    prev_db = db_history[1] if len(db_history) > 1 else last_db
    h2, t2 = int(prev_db[0]), int(prev_db[1])

    prev_db_2 = db_history[2] if len(db_history) > 2 else prev_db
    h3, t3 = int(prev_db_2[0]), int(prev_db_2[1])

    prev_db_3 = db_history[3] if len(db_history) > 3 else prev_db_2
    h4, t4 = int(prev_db_3[0]), int(prev_db_3[1])

    # 1. Thống kê tần suất Đầu/Đuôi/Tổng
    recent_30 = db_history[:30]
    recent_60 = db_history[:60] if len(db_history) >= 60 else db_history

    head_counts = defaultdict(int)
    tail_counts = defaultdict(int)
    sum_counts = defaultdict(int)

    for num in recent_30:
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        head_counts[h] += 1
        tail_counts[t] += 1
        sum_counts[s] += 1

    # Kiểm tra nhịp bệt chạm trong 3 ngày gần nhất để phạt Overfit
    recent_chams = [h1, t1, h2, t2, h3, t3]
    cham_counter = Counter(recent_chams)

    # 2. Tập hợp Chạm Hot linh hoạt (Chính + Bóng Dương + Bóng Âm)
    hot_chams = {
        h1, t1, 
        (h1 + 5) % 10, (t1 + 5) % 10,  # Bóng Dương
        (h1 + 7) % 10, (t1 + 7) % 10,  # Bóng Âm
        h2, t2
    }

    # 3. Ma trận chấm điểm đa tầng v12.1
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10
        score = 0.0

        # a. Tần suất xuất hiện chuẩn hóa
        score += (head_counts[h] * 1.2) + (tail_counts[t] * 1.2) + (sum_counts[s] * 1.0)

        # b. Điểm Chạm Trọng Tâm (Cân bằng lại còn 3.5 điểm để tránh thiên vị quá đà)
        if h in hot_chams: score += 3.5
        if t in hot_chams: score += 3.5

        # c. Cầu Chuyền / Ghép Cầu Đa Tầng
        if h == t1: score += 8.0   # Đuôi hôm qua -> Đầu hôm nay
        if t == h1: score += 7.0   # Đầu hôm qua -> Đuôi hôm nay
        if h == h2: score += 5.0   # Cầu cách ngày Đầu
        if t == t2: score += 5.0   # Cầu cách ngày Đuôi

        # d. Cầu Bộ Đề / Bóng Kép / Lộn
        if s_str == f"{t1}{h1}": score += 9.0
        if h == (h1 + 5) % 10 and t == (t1 + 5) % 10: score += 8.0 # Bóng kép
        if h == (t1 + 5) % 10 or t == (h1 + 5) % 10: score += 4.5

        # e. Cơ chế Phạt Bệt Quá Tải (Nếu chạm đã ra > 3 lần trong 3 ngày qua)
        if cham_counter[h] >= 3: score -= 4.0
        if cham_counter[t] >= 3: score -= 4.0

        # f. Thưởng điểm Kép / Sát kép
        if h == t: score += 3.0
        elif abs(h - t) == 1 or abs(h - t) == 9: score += 2.0

        # g. Trừ điểm con đề vừa ra ngày hôm qua
        if s_str == last_db: score -= 12.0

        # h. Trừ điểm Đề Gan (>60 ngày)
        if s_str not in recent_60: score -= 5.0

        scores[s_str] = score

    # Sắp xếp danh sách số theo điểm số giảm dần
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    all_ranked = [num_str for num_str, _ in sorted_numbers]

    # Rút gọn dàn trực tiếp theo xếp hạng điểm số tối ưu
    top_10_db = all_ranked[:10]
    top_20_db = all_ranked[:20]
    top_36_db = all_ranked[:36]

    return {
        'top_10_db': sorted(top_10_db),
        'top_20_db': sorted(top_20_db),
        'top_36_db': sorted(top_36_db)
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
        'is_hit': actual_db in top_10  # Giữ tương thích ngược với bot
    }