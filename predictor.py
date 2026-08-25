import math
from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán v5.0: Ma Trận Nhịp Động & Khóa Lô Trượt Lặp
    """
    if not historical_data or len(historical_data) < 15:
        return None

    # Trích xuất dữ liệu lô 2 số cuối (Mới nhất -> Cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # 1. TÍNH NHỊP RƠI VÀ THỜI GIAN VẮNG (GAP)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    # 2. TÍNH TẦN SUẤT 15 NGÀY GẦN NHẤT
    recent_15 = daily_numbers[:15]
    flat_15 = [num for day in recent_15 for num in day]
    count_15 = Counter(flat_15)

    # 3. CHUẨN HÓA ĐIỂM SỐ THEO NHỊP ĐỘNG
    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)
        freq = count_15[num]

        # Điểm tần suất điểm rơi chuẩn (2-4 lần / 15 ngày)
        if 2 <= freq <= 4:
            scores[num] += freq * 4.0
        elif freq == 1:
            scores[num] += 2.0
        elif freq > 5:
            scores[num] -= 2.0  # Phạt lô quá nóng

        # Điểm nhịp vàng (Gap = 2 hoặc 3 ngày)
        if gap == 2 or gap == 3:
            scores[num] += 12.0
        elif gap == 1:
            scores[num] += 5.0
        elif gap == 4 or gap == 5:
            scores[num] += 6.0
        elif gap > 8:
            scores[num] -= 10.0  # Phạt mạnh lô gan

    # 4. CHỐNG NEO SỐ (ANTI-REPEAT PENALTY)
    # Giảm điểm mạnh nếu con số đã xuất hiện ở nhịp đoán trước nhưng bị trượt
    yesterday_set = set(daily_numbers[0])
    day_before_set = set(daily_numbers[1]) if len(daily_numbers) > 1 else set()

    for num in scores:
        # Nếu lô rơi liên tiếp 2 ngày -> Tạm ngưng bắt lại ngay ngày thứ 3
        if num in yesterday_set and num in day_before_set:
            scores[num] -= 8.0

    # 5. LỌC BẠCH THỦ VÀ SONG THỦ
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    bach_thu = ranked_nums[0]
    lon_bach_thu = bach_thu[::-1]

    # Chọn Song Thủ: Nếu lộn của Bạch Thủ nằm trong Top 30 thì chọn cặp lộn, ngược lại chọn Top 2
    if lon_bach_thu != bach_thu and lon_bach_thu in ranked_nums[:30]:
        song_thu = (bach_thu, lon_bach_thu)
    else:
        song_thu = (ranked_nums[0], ranked_nums[1])

    # 6. PHÂN TÁN ĐẦU SỐ CHO TOP 5 VÀ TOP 10
    def build_balanced_top(candidates, limit, max_per_head):
        result = []
        head_count = defaultdict(int)
        for n in candidates:
            head = n[0]
            if head_count[head] < max_per_head:
                result.append(n)
                head_count[head] += 1
            if len(result) == limit:
                break
        return result

    top_5 = build_balanced_top(ranked_nums, 5, max_per_head=1)   # Top 5: Mỗi đầu chỉ lấy 1 con
    top_10 = build_balanced_top(ranked_nums, 10, max_per_head=2) # Top 10: Mỗi đầu tối đa 2 con

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