from collections import Counter, defaultdict

# =========================================================
# 1. LOGIC SOI LÔ (BẠCH THỦ, SONG THỦ, TOP 5, TOP 10) - v10.0 (GIỮ NGUYÊN 100%)
# =========================================================

def analyze_and_predict(historical_data, is_recursive=False):
    """
    Thuật toán SOI LÔ v10.0: Ensemble Multi-Bridge & Adaptive Threshold Matrix
    (Giữ nguyên tuyệt đối không thay đổi)
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
# 2. LOGIC SOI ĐỀ v13.0: HIGH-COVERAGE MULTI-SUM MATRIX (TỐI ƯU MỚI)
# =========================================================

def analyze_and_predict_db(historical_data):
    """
    Thuật toán SOI ĐỀ v13.0:
    - Loại bỏ hoàn toàn bẫy 'Khóa cứng chạm' làm trượt dây
    - Dùng Ma trận Tổng Đề (Sum Frequency) + Chạm Tự Nhận
    - Đảm bảo bao phủ rộng rãi cho Dàn 36 số và độ chính xác cao cho Dàn 20/10 số
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

    # Lấy dữ liệu 5 ngày ĐB gần nhất
    recent_5 = db_history[:5]
    
    # 1. Thống kê tần suất Đầu, Đuôi, Tổng trong 30-45 ngày
    recent_45 = db_history[:45]
    head_counts = defaultdict(int)
    tail_counts = defaultdict(int)
    sum_counts = defaultdict(int)

    for num in recent_45:
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        head_counts[h] += 1
        tail_counts[t] += 1
        sum_counts[s] += 1

    # Tìm các Tổng Đề đang chạy đẹp nhất (Top 4 Tổng)
    top_sums = set(sorted(sum_counts.keys(), key=lambda x: sum_counts[x], reverse=True)[:4])

    # 2. Xác định các Chạm Tiềm Năng (Tập hợp linh hoạt không ép điểm quá lớn)
    last_db = recent_5[0]
    h1, t1 = int(last_db[0]), int(last_db[1])
    
    potential_chams = {
        h1, t1,                     # Chạm ĐB hôm qua
        (h1 + 5) % 10, (t1 + 5) % 10, # Bóng dương
        (h1 + 1) % 10, (t1 + 1) % 10, # Tăng 1 nhịp
        (h1 + 9) % 10, (t1 + 9) % 10  # Giảm 1 nhịp
    }

    # 3. Tính điểm cho 100 con số (Ma trận cân bằng)
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10
        score = 0.0

        # a. Điểm tần suất Đầu/Đuôi (0 - 5 điểm)
        score += (head_counts[h] * 0.4) + (tail_counts[t] * 0.4)

        # b. Điểm Tổng Đề Hot (Cộng 4.0 điểm nếu thuộc Top Tổng)
        if s in top_sums:
            score += 4.0

        # c. Điểm Chạm Linh Hoạt (Cộng vừa phải 2.5 điểm/chạm)
        if h in potential_chams: score += 2.5
        if t in potential_chams: score += 2.5

        # d. Thưởng Cầu Lộn & Bóng Bộ
        if h == (t1 + 5) % 10 or t == (h1 + 5) % 10:
            score += 2.0
        if s_str == f"{t1}{h1}":
            score += 3.0

        # e. Thưởng Kép / Sát Kép
        if h == t:
            score += 2.0
        elif abs(h - t) == 1 or abs(h - t) == 9:
            score += 1.0

        scores[s_str] = score

    # Sắp xếp số theo điểm từ cao xuống thấp
    sorted_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    all_ranked = [num_str for num_str, _ in sorted_numbers]

    # --- RÚT DÀN 10, 20, 36 SỐ LINH HOẠT ---
    # Dàn 10 số: Lấy 10 số điểm cao nhất tuyệt đối
    top_10_db = sorted(all_ranked[:10])

    # Dàn 20 số: Lấy 20 số điểm cao nhất
    top_20_db = sorted(all_ranked[:20])

    # Dàn 36 số: Phân tán đều các Đầu Số (mỗi đầu tối đa 4-5 con) để đảm bảo độ bao phủ cực cao
    top_36_db = []
    head_tracker_36 = defaultdict(int)
    for num_str in all_ranked:
        h = num_str[0]
        if head_tracker_36[h] < 4:  # Phủ đều các đầu
            top_36_db.append(num_str)
            head_tracker_36[h] += 1
        if len(top_36_db) == 36:
            break
            
    # Nối thêm nếu chưa đủ 36
    if len(top_36_db) < 36:
        for num_str in all_ranked:
            if num_str not in top_36_db:
                top_36_db.append(num_str)
            if len(top_36_db) == 36:
                break

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
        'is_hit': actual_db in top_10
    }