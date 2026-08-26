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
            scores[num] += 25.0  # Điểm nhịp vàng
        elif gap == 1:
            scores[num] += 10.0  # Lô rơi nhịp nhẹ
        elif gap == 4:
            scores[num] += 6.0
        elif gap == 0:
            scores[num] -= 10.0  # Vừa về hôm qua, hạ ưu tiên
        elif gap > 6:
            scores[num] -= 999.0 # LÔ GAN - KHÓA TẬN GỐC

    # 2. CẦU VỊ TRÍ ĐẠI DIỆN (BRIDGE MATCHING)
    if len(full_results) > 0 and len(full_results[0]) >= 2:
        g0 = full_results[0][0] # Giải Đặc biệt
        g1 = full_results[0][1] # Giải Nhất
        
        bridge_num1 = (g0[0] + g1[-1])[-2:].zfill(2)
        bridge_num2 = (g1[0] + g0[-1])[-2:].zfill(2)
        
        scores[bridge_num1] += 15.0
        scores[bridge_num2] += 15.0

    # 3. CHỐNG NEO SỐ TRƯỢT (ANTI-REPEAT LOGIC)
    if len(historical_data) >= 6:
        prev_data = historical_data[1:]
        prev_pred = analyze_and_predict(prev_data)
        if prev_pred:
            prev_bt = prev_pred['bach_thu']
            if prev_bt not in daily_numbers[0]:
                scores[prev_bt] -= 50.0  # Trừ điểm nặng nếu đã đoán trượt ngày trước

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
# 2. LOGIC V8.0: SOI ĐỀ TỪ LÔ CỰC TẦN VÀ CẦU GHÉP VỊ TRÍ G0-G1
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán v8.0: Dự đoán Giải Đặc Biệt dựa trên Lô Cực Tần & Cầu Vị Trí
    """
    if not historical_data or len(historical_data) < 5:
        return None

    # Lấy dữ liệu giải đặc biệt và toàn bộ kết quả lô ngày gần nhất
    latest_row = historical_data[0]
    nums = latest_row['numbers'] if isinstance(latest_row, dict) else latest_row[1]
    
    if not nums:
        return None

    full_nums = [str(n).zfill(2) for n in nums]
    last_db = full_nums[0][-2:].zfill(2)
    last_g1 = full_nums[1][-2:].zfill(2) if len(full_nums) > 1 else "00"

    # Thống kê Đầu/Đuôi xuất hiện nhiều nhất trong 27 giải ngày hôm qua
    head_counter = Counter()
    tail_counter = Counter()
    for num in full_nums:
        2d = num[-2:].zfill(2)
        head_counter[2d[0]] += 1
        tail_counter[2d[1]] += 1

    top_heads = [h for h, _ in head_counter.most_common(3)]
    top_tails = [t for t, _ in tail_counter.most_common(3)]

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # 1. CẦU VỊ TRÍ CỐ ĐỊNH (GĐB & GIẢI NHẤT)
    # Ghép Đầu GĐB + Đuôi GĐB / Đuôi G1
    bridge_1 = (last_db[0] + last_g1[-1]).zfill(2)
    bridge_2 = (last_g1[0] + last_db[-1]).zfill(2)
    bridge_3 = (last_db[1] + last_db[0]).zfill(2) # Số lộn ĐB
    
    scores[bridge_1] += 20.0
    scores[bridge_2] += 20.0
    scores[bridge_3] += 15.0

    # 2. TÍNH ĐIỂM THEO LÔ CỰC TẦN
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = s_str[0], s_str[1]

        if h in top_heads: scores[s_str] += 8.0
        if t in top_tails: scores[s_str] += 8.0

        # Cầu Chuyền Đuôi ĐB hôm qua sang Đầu/Đuôi hôm nay
        if h == last_db[1]: scores[s_str] += 10.0
        if t == last_db[1]: scores[s_str] += 7.0

        # Cầu Bóng Dương Đuôi ĐB
        bong_tail = str((int(last_db[1]) + 5) % 10)
        if t == bong_tail or h == bong_tail:
            scores[s_str] += 6.0

        # Phạt chính con đề vừa ra hôm qua
        if s_str == last_db:
            scores[s_str] -= 40.0

    # 3. CHỌN TOP 10 PHÂN TÁN (Mỗi Đầu max 2 số)
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    top_10_db = []
    head_tracker = defaultdict(int)

    for num_str, score in sorted_numbers:
        h = num_str[0]
        if head_tracker[h] < 2:
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
    """
    Hàm test kiểm tra độ chính xác dự đoán Giải Đặc Biệt cho lệnh /testdb
    """
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