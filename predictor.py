from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán v6.0: Golden Ratio Pattern & Strictly Paired Song Thu
    """
    # Hạ điều kiện xuống 5 ngày để tránh bị thiếu dữ liệu khi backtest ngày cũ
    if not historical_data or len(historical_data) < 5:
        return None

    # Trích xuất dữ liệu lô 2 số cuối (Mới nhất -> Cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # 1. NHỊP VẮNG (GAP SCORE)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)
        
        if gap == 2 or gap == 3:
            scores[num] += 15.0  # Nhịp vàng cực đẹp
        elif gap == 1:
            scores[num] += 8.0   # Ưu tiên Lô rơi
        elif gap == 4 or gap == 5:
            scores[num] += 6.0
        elif gap == 0:
            scores[num] += 3.0   # Lô vừa ra hôm qua
        elif gap > 10:
            scores[num] -= 15.0  # Tránh lô gan

    # 2. TẦN SUẤT 10 NGÀY
    recent_10 = daily_numbers[:min(10, len(daily_numbers))]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)

    for num, count in count_10.items():
        if 1 <= count <= 3:
            scores[num] += count * 4.0
        elif count > 3:
            scores[num] += 2.0

    # 3. CHỐNG NEO SỐ (ANTI-REPEAT)
    # Nếu một số bị dính điểm phạt nhẹ nếu đã làm Bạch thủ hôm trước mà không ra
    yesterday_nums = set(daily_numbers[0])
    
    # 4. CHỌN BẠCH THỦ VÀ SONG THỦ (LUÔN CÓ LỘN)
    # Cộng điểm tương quan cặp lộn (X và X_lộn)
    pair_scores = {}
    for i in range(100):
        num = str(i).zfill(2)
        lon = num[::-1]
        if num <= lon:  # Tránh tính trùng cặp
            p_score = scores[num] + scores[lon]
            pair_scores[(num, lon)] = p_score

    # Sắp xếp các cặp số theo tổng điểm
    best_pair = sorted(pair_scores.keys(), key=lambda x: pair_scores[x], reverse=True)[0]
    
    # Số có điểm đơn cao hơn trong cặp được chọn làm Bạch Thủ
    if scores[best_pair[0]] >= scores[best_pair[1]]:
        bach_thu = best_pair[0]
        song_thu = (best_pair[0], best_pair[1])
    else:
        bach_thu = best_pair[1]
        song_thu = (best_pair[1], best_pair[0])

    # 5. DÀN TOP 5 VÀ TOP 10 (SẮP XẾP THEO ĐIỂM ĐƠN)
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    def extract_top(candidates, limit):
        result = []
        head_tracker = defaultdict(int)
        for n in candidates:
            head = n[0]
            if head_tracker[head] < 2:  # Tối đa 2 con/đầu
                result.append(n)
                head_tracker[head] += 1
            if len(result) == limit:
                break
        return result

    top_5 = extract_top(ranked_nums, 5)
    top_10 = extract_top(ranked_nums, 10)

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