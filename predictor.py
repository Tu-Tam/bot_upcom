from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán v8.0: Strict Anti-Repeat Penalty & Cross-Position Matching
    """
    if not historical_data or len(historical_data) < 5:
        return None

    # Trích xuất dữ liệu 2 số cuối (Mới nhất -> Cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # 1. TÍNH LẦN XUẤT HIỆN GẦN NHẤT (GAP / NHỊP)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    # 2. CHUẨN HÓA ĐIỂM THEO NHỊP LÔ
    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)

        if gap == 3:                   # Điểm rơi đẹp nhất
            scores[num] += 18.0
        elif gap == 2:
            scores[num] += 14.0
        elif gap == 1:                 # Lô rơi
            scores[num] += 8.0
        elif gap == 4 or gap == 5:
            scores[num] += 5.0
        elif gap == 0:
            scores[num] += 1.0
        elif gap > 8:                  # Lô gan
            scores[num] -= 20.0

    # 3. TẦN SUẤT 10 NGÀY GẦN NHẤT
    recent_10 = daily_numbers[:min(10, len(daily_numbers))]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)

    for num, count in count_10.items():
        if 2 <= count <= 4:
            scores[num] += count * 3.0
        elif count > 5:
            scores[num] -= 6.0

    # 4. CHỐNG NEO SỐ DỰ ĐOÁN TRƯỢT HÔM TRƯỚC (ANTI-REPEAT PENALTY)
    # Lấy lại dự đoán của ngày hôm qua nếu có đủ dữ liệu
    if len(historical_data) >= 6:
        prev_data = historical_data[1:]  # Dữ liệu tính từ ngày D-1 trở về trước
        prev_pred = analyze_and_predict(prev_data)
        if prev_pred:
            prev_bt = prev_pred['bach_thu']
            actual_yesterday = daily_numbers[0]
            # Nếu Bạch thủ hôm qua dự đoán mà KHÔNG VỀ -> Phạt nặng ngày hôm nay
            if prev_bt not in actual_yesterday:
                scores[prev_bt] -= 25.0

    # 5. CHỌN BẠCH THỦ VÀ SONG THỦ
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    bach_thu = ranked_nums[0]
    lon_bach_thu = bach_thu[::-1]

    if lon_bach_thu != bach_thu:
        song_thu = (bach_thu, lon_bach_thu)
    else:
        # Nếu Bạch thủ là KÉP (ví dụ 11, 77) -> Song thủ lấy Bạch thủ + Con xếp thứ 2
        second_best = ranked_nums[1]
        song_thu = (bach_thu, second_best)

    # 6. DÀN TOP 5 VÀ TOP 10 (PHÂN TÁN ĐẦU SỐ)
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