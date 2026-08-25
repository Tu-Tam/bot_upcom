from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán Đa Trọng Số v2.0: Tối ưu nhịp rơi, tần suất & ma trận đi cùng nhau
    """
    if not historical_data or len(historical_data) < 10:
        return None

    # 1. Trích xuất dữ liệu lô 2 số cuối
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # Factor A: Tần suất ngắn hạn (10 ngày gần nhất)
    recent_10 = daily_numbers[:10]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)
    for num, count in count_10.items():
        if 1 <= count <= 3:
            scores[num] += count * 5.0
        elif count > 3:
            scores[num] += 3.0  # Giảm điểm lô nổ quá nhiều

    # Factor B: Nhịp rơi chuẩn (2 - 5 ngày chưa ra)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for num in scores:
        gap = last_seen.get(num, 999)
        if 2 <= gap <= 4:
            scores[num] += 18.0  # Điểm rơi vàng
        elif gap == 5 or gap == 6:
            scores[num] += 10.0
        elif gap == 1:
            scores[num] += 4.0   # Lô rơi vừa phải
        elif gap > 12:
            scores[num] -= 15.0  # Tránh xa lô gan

    # Factor C: Thống kê tổng quan 365 ngày
    flat_all = [num for day in daily_numbers for num in day]
    count_all = Counter(flat_all)
    avg_count = len(flat_all) / 100.0 if flat_all else 1
    for num in scores:
        scores[num] += (count_all[num] / avg_count) * 4.0

    # 2. Sắp xếp danh sách điểm số
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_numbers = [item[0] for item in sorted_scores]

    # 3. Chọn Bạch Thủ & Song Thủ Lộn
    bach_thu = top_numbers[0]
    lon_bach_thu = bach_thu[::-1]
    
    if lon_bach_thu != bach_thu:
        song_thu = (bach_thu, lon_bach_thu)
    else:
        song_thu = (top_numbers[0], top_numbers[1])

    # 4. Lọc Top 5 & Top 10 (Tránh dồn quá 3 số cùng 1 đầu)
    top_5 = []
    head_count_5 = Counter()
    for num in top_numbers:
        head = num[0]
        if head_count_5[head] < 2:
            top_5.append(num)
            head_count_5[head] += 1
        if len(top_5) == 5:
            break

    top_10 = top_numbers[:10]

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