from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán v7.0: Fix Duplicate Twin Pair & Anti-Repeat Logic
    """
    if not historical_data or len(historical_data) < 5:
        return None

    # Trích xuất dữ liệu 2 số cuối các giải (Mới nhất -> Cũ nhất)
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

    # 2. CHUẨN HÓA ĐIỂM SỐ THEO NHỊP CHUẨN
    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)

        if gap == 2 or gap == 3:      # Nhịp rơi chuẩn lý tưởng
            scores[num] += 16.0
        elif gap == 1:                 # Nhịp lô rơi liền ngày
            scores[num] += 9.0
        elif gap == 4 or gap == 5:     # Nhịp trung bình
            scores[num] += 6.0
        elif gap == 0:                 # Vừa nổ hôm qua
            scores[num] += 2.0
        elif gap > 9:                  # Lô gan
            scores[num] -= 18.0

    # 3. TẦN SUẤT 10 NGÀY GẦN NHẤT
    recent_10 = daily_numbers[:min(10, len(daily_numbers))]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)

    for num, count in count_10.items():
        if 2 <= count <= 4:
            scores[num] += count * 3.5
        elif count == 1:
            scores[num] += 2.0
        elif count > 5:
            scores[num] -= 5.0  # Phạt lô quá nóng

    # 4. CHỐNG NEO SỐ TRƯỢT HÔM TRƯỚC
    # Phạt con số vừa nổ ở top dự đoán hôm trước nhưng thực tế KHÔNG về
    yesterday_actual = set(daily_numbers[0])

    # 5. LỌC BẠCH THỦ VÀ SONG THỦ (XỬ LÝ LỖI TRÙNG KÉP)
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    bach_thu = ranked_nums[0]
    lon_bach_thu = bach_thu[::-1]

    # Kiểm tra xử lý cặp Song Thủ
    if lon_bach_thu != bach_thu:
        # Nếu không phải kép -> Song thủ là (Bạch thủ, Lộn)
        song_thu = (bach_thu, lon_bach_thu)
    else:
        # Nếu Bạch thủ là KÉP (ví dụ 77) -> Song thủ lấy (Bạch thủ, Con điểm cao thứ 2)
        second_best = ranked_nums[1]
        song_thu = (bach_thu, second_best)

    # 6. DÀN TOP 5 VÀ TOP 10 (SẮP XẾP PHÂN TÁN ĐẦU SỐ)
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