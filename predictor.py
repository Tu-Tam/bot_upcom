from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán Đa Trọng Số v3.0: Cân bằng Tần suất, Lô rơi, Nhịp vàng & Ma trận Cặp lộn
    """
    if not historical_data or len(historical_data) < 10:
        return None

    # 1. Trích xuất dữ liệu lô 2 số cuối (Sắp xếp từ mới nhất -> cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # --- TIÊU CHÍ 1: LÔ RƠI TỪ NGÀY GẦN NHẤT (Ngày hôm qua) ---
    yesterday_nums = set(daily_numbers[0])
    for num in yesterday_nums:
        scores[num] += 8.0  # Cộng điểm cho lô rơi từ hôm qua

    # --- TIÊU CHÍ 2: TẦN SUẤT 10 NGÀY GẦN NHẤT ---
    recent_10 = daily_numbers[:10]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)
    for num, count in count_10.items():
        if count == 1:
            scores[num] += 3.0
        elif count == 2:
            scores[num] += 7.0
        elif count == 3:
            scores[num] += 10.0  # Tần suất lý tưởng
        elif count > 3:
            scores[num] += 4.0   # Giảm nhẹ vì rủi ro lô gan ngắn hạn

    # --- TIÊU CHÍ 3: NHỊP RƠI CHUẨN (GAP SCORE) ---
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for num in scores:
        gap = last_seen.get(num, 999)
        if gap == 1:
            scores[num] += 5.0   # Nhịp 1 ngày
        elif gap == 2 or gap == 3:
            scores[num] += 15.0  # NHỊP VÀNG: 2-3 ngày chưa ra
        elif gap == 4 or gap == 5:
            scores[num] += 10.0  # Nhịp đẹp
        elif gap == 6 or gap == 7:
            scores[num] += 4.0
        elif gap > 10:
            scores[num] -= 12.0  # Lô khan / Lô gan

    # --- TIÊU CHÍ 4: THỐNG KÊ TỔNG QUAN 365 NGÀY ---
    flat_all = [num for day in daily_numbers for num in day]
    count_all = Counter(flat_all)
    avg_count = len(flat_all) / 100.0 if flat_all else 1
    for num in scores:
        scores[num] += (count_all[num] / avg_count) * 3.0

    # --- TIÊU CHÍ 5: ĐIỂM CỘNG CẶP LỘN (PAIR SYNERGY) ---
    # Nếu cả X và X_lộn đều có điểm cao -> Cộng thêm thưởng cho cả 2
    temp_scores = scores.copy()
    for num in temp_scores:
        lon = num[::-1]
        if lon != num and temp_scores[lon] > 15.0:
            scores[num] += 4.0

    # 2. Sắp xếp danh sách theo tổng điểm từ cao xuống thấp
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_numbers = [item[0] for item in sorted_scores]

    # 3. Chọn Bạch Thủ & Song Thủ
    bach_thu = top_numbers[0]
    lon_bach_thu = bach_thu[::-1]

    if lon_bach_thu != bach_thu:
        song_thu = (bach_thu, lon_bach_thu)
    else:
        song_thu = (top_numbers[0], top_numbers[1])

    # 4. Chọn Top 5 (Khống chế tối đa 2 con/đầu số để phân tán rủi ro)
    top_5 = []
    head_count_5 = Counter()
    for num in top_numbers:
        head = num[0]
        if head_count_5[head] < 2:
            top_5.append(num)
            head_count_5[head] += 1
        if len(top_5) == 5:
            break

    # 5. Chọn Top 10 (Khống chế tối đa 3 con/đầu số)
    top_10 = []
    head_count_10 = Counter()
    for num in top_numbers:
        head = num[0]
        if head_count_10[head] < 3:
            top_10.append(num)
            head_count_10[head] += 1
        if len(top_10) == 10:
            break

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