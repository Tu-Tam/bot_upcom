from collections import Counter, defaultdict

# =========================================================
# 1. LOGIC SOI LÔ (BẠCH THỦ, SONG THỦ, TOP 5, TOP 10) - GIỮ NGUYÊN
# =========================================================

def analyze_and_predict(historical_data):
    """
    Thuật toán v10.0: Ensemble Multi-Bridge & Adaptive Threshold Matrix
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
    if len(historical_data) >= 6:
        prev_data = historical_data[1:]
        prev_pred = analyze_and_predict(prev_data)
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
# 2. LOGIC V9.0: BẮT ĐỀ ĐUÔI DÀN 10 SỐ MA TRẬN BÓNG & BỘ ĐỀ ĐA TẦNG
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán v9.0: Ma Trận Bắt Toàn Diện Cầu Bóng & Chạm Chuyền Đa Tầng
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

    # Phân tích 3 ngày gần nhất
    last_db = db_history[0]
    h1, t1 = int(last_db[0]), int(last_db[1])
    
    prev_db = db_history[1] if len(db_history) > 1 else last_db
    h2, t2 = int(prev_db[0]), int(prev_db[1])

    # Xác định các Chạm Trọng Tâm (Gốc + Bóng Dương + Bóng Âm)
    hot_chams = {
        h1, t1, 
        (h1 + 5) % 10, (t1 + 5) % 10, # Bóng Dương
        h2, t2
    }

    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        score = 0.0

        # 1. Điểm Chạm Trọng Tâm
        if h in hot_chams: score += 7.0
        if t in hot_chams: score += 7.0

        # 2. Cầu Chuyền Nối Đuôi Trực Tiếp
        if h == t1: score += 10.0  # Đuôi hôm qua về Đầu hôm nay
        if t == h1: score += 9.0   # Đầu hôm qua về Đuôi hôm nay
        if h == h1: score += 6.0   # Bệt Đầu
        if t == t1: score += 6.0   # Bệt Đuôi

        # 3. Cầu Bộ Số Đề (Các cặp lộn và bóng của ngày gần nhất)
        if s_str == f"{t1}{h1}": score += 12.0  # Lộn chính xác
        if h == (h1 + 5) % 10 and t == (t1 + 5) % 10: score += 10.0 # Bóng kép toàn phần

        # 4. Trừ điểm nhẹ nếu trùng chính xác con đề hôm qua
        if s_str == last_db:
            score -= 15.0

        scores[s_str] = score

    # Lọc Top 10 linh hoạt (Tối đa 3 số/Đầu để không bỏ sót bộ bóng)
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    top_10_db = []
    head_tracker = defaultdict(int)

    for num_str, score in sorted_numbers:
        h = num_str[0]
        if head_tracker[h] < 3:
            top_10_db.append(num_str)
            head_tracker[h] += 1
        if len(top_10_db) == 10:
            break

    if len(top_10_db) < 10:
        for num_str, score in sorted_numbers:
            if num_str not in top_10_db:
                top_10_db.append(num_str)
            if len(top_10_db) == 10:
                break

    return {
        'top_10_db': sorted(top_10_db)
    }

def test_db_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict_db(historical_data)
    if not pred or not actual_numbers:
        return None

    actual_db = str(actual_numbers[0])[-2:].zfill(2)
    top_10 = pred['top_10_db']

    return {
        'predicted_10': top_10,
        'actual_db': actual_db,
        'is_hit': actual_db in top_10
    }